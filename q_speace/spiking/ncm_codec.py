"""Multiscale residual codec for T222 Phase 0 (codec only).

This is a small numpy implementation of the *representation* half of
Next-Concept Modeling (arXiv:2610.14162): a hierarchy of residual codebooks
that reconstructs a signal coarse-to-fine. It is **not** the NCM generator:
there is no learned transformer, no parallel level prediction, and no NFE
claim. Phase 0 measures codec properties only (see
``docs/T222_NCM_CODEC_SPEC.md``).

Naming note: a "code" here is a learned discrete index that can preserve
global structure. It is not a human concept, idea, or semantic unit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CodecConfig:
    """Configuration for :class:`ResidualCodec`."""

    levels: int = 4
    codebook_size: int = 8
    seed: int = 0
    kmeans_iters: int = 25

    def validate(self) -> None:
        if self.levels < 1:
            raise ValueError("levels must be >= 1")
        if self.codebook_size < 2:
            raise ValueError("codebook_size must be >= 2")
        if self.kmeans_iters < 1:
            raise ValueError("kmeans_iters must be >= 1")


@dataclass(frozen=True)
class CodecCodes:
    """Discrete indices per level plus the original input shape."""

    indices: tuple[np.ndarray, ...]
    input_shape: tuple[int, ...]


class ResidualCodec:
    """Deterministic multiscale residual quantizer (numpy only).

    ``fit`` builds one codebook per level on the residual left by the
    previous level. ``encode`` returns one index array per level and
    ``decode`` reconstructs by summing the selected centroids. ``decode``
    with ``levels=l`` gives the coarse-to-fine ablation used by calibration.
    """

    def __init__(self, config: CodecConfig | None = None) -> None:
        self.config = config or CodecConfig()
        self.config.validate()
        self._mean: np.ndarray | None = None
        self._codebooks: list[np.ndarray] = []

    @property
    def is_fitted(self) -> bool:
        return self._mean is not None

    @property
    def codebooks(self) -> tuple[np.ndarray, ...]:
        return tuple(self._codebooks)

    def fit(self, x: np.ndarray) -> ResidualCodec:
        """Fit the residual hierarchy on a 1-D or 2-D array."""
        data, _ = _as_2d(x, name="x")
        if data.shape[0] < 1:
            raise ValueError("x must contain at least one sample")

        self._mean = data.mean(axis=0)
        residual = data - self._mean
        rng = np.random.default_rng(self.config.seed)
        self._codebooks = []
        for _ in range(self.config.levels):
            book = _kmeans(residual, self.config.codebook_size, rng, self.config.kmeans_iters)
            self._codebooks.append(book)
            labels = _nearest(residual, book)
            residual = residual - book[labels]
        return self

    def encode(self, x: np.ndarray) -> CodecCodes:
        """Encode a 1-D or 2-D array into one index array per level."""
        data, shape = _as_2d(x, name="x")
        mean = self._fitted_mean()
        if data.shape[1] != mean.shape[0]:
            raise ValueError("x feature dimension does not match fitted codec")

        residual = data - mean
        indices: list[np.ndarray] = []
        for book in self._codebooks:
            labels = _nearest(residual, book)
            indices.append(labels)
            residual = residual - book[labels]
        return CodecCodes(indices=tuple(indices), input_shape=shape)

    def decode(self, codes: CodecCodes, levels: int | None = None) -> np.ndarray:
        """Decode using all levels or the first ``levels`` levels."""
        mean = self._fitted_mean()
        if len(codes.indices) != len(self._codebooks):
            raise ValueError("codes do not match the fitted number of levels")
        n_levels = len(self._codebooks) if levels is None else levels
        if not (0 <= n_levels <= len(self._codebooks)):
            raise ValueError("levels must be in [0, len(codebooks)]")

        n_samples = codes.indices[0].shape[0] if codes.indices else 0
        if n_samples < 1:
            raise ValueError("codes must contain at least one sample")
        reconstruction = np.repeat(mean[None, :], n_samples, axis=0)
        for book, labels in zip(self._codebooks[:n_levels], codes.indices[:n_levels], strict=True):
            if labels.shape[0] != n_samples:
                raise ValueError("codes have inconsistent sample counts across levels")
            if np.any(labels < 0) or np.any(labels >= book.shape[0]):
                raise ValueError("code index out of range for its level")
            reconstruction = reconstruction + book[labels]
        return _restore_shape(reconstruction, codes.input_shape)

    def reconstruction_errors(self, x: np.ndarray) -> dict[str, object]:
        """Return per-level and total mean squared errors on ``x``."""
        data, _ = _as_2d(x, name="x")
        mean = self._fitted_mean()
        codes = self.encode(x)
        reconstruction = np.repeat(mean[None, :], data.shape[0], axis=0)
        per_level: list[float] = []
        for book, labels in zip(self._codebooks, codes.indices, strict=True):
            reconstruction = reconstruction + book[labels]
            per_level.append(float(np.mean((data - reconstruction) ** 2)))
        return {"mse_per_level": per_level, "mse_total": per_level[-1] if per_level else 0.0}

    def ablate(self, codes: CodecCodes, levels: int) -> np.ndarray:
        """Decode using only the first ``levels`` levels."""
        return self.decode(codes, levels=levels)

    def corrupt(
        self,
        codes: CodecCodes,
        level: int,
        fraction: float,
        seed: int,
    ) -> CodecCodes:
        """Replace a fraction of the codes at ``level`` with other indices.

        This measures codec sensitivity to corrupted codes. It is **not** the
        NCM training-time robustness mechanism, which is future work.
        """
        if not (0.0 <= fraction <= 1.0):
            raise ValueError("fraction must be in [0, 1]")
        if not (0 <= level < len(codes.indices)):
            raise ValueError("level out of range")
        book = self._codebooks[level]
        labels = codes.indices[level].copy()
        n = labels.shape[0]
        count = int(round(fraction * n))
        if count == 0 or book.shape[0] < 2:
            return CodecCodes(
                indices=tuple(index.copy() for index in codes.indices),
                input_shape=codes.input_shape,
            )

        rng = np.random.default_rng(seed)
        chosen = rng.choice(n, size=count, replace=False)
        replacement = rng.integers(0, book.shape[0], size=count)
        same = replacement == labels[chosen]
        replacement[same] = (replacement[same] + 1) % book.shape[0]
        labels[chosen] = replacement
        updated = list(codes.indices)
        updated[level] = labels
        return CodecCodes(indices=tuple(updated), input_shape=codes.input_shape)

    def _fitted_mean(self) -> np.ndarray:
        if self._mean is None:
            raise RuntimeError("codec must be fitted before encode/decode")
        return self._mean


def _as_2d(x: np.ndarray, *, name: str) -> tuple[np.ndarray, tuple[int, ...]]:
    array = np.asarray(x, dtype=float)
    if array.ndim == 0:
        raise ValueError(f"{name} must be at least 1-D")
    if array.ndim > 2:
        raise ValueError(f"{name} must be 1-D or 2-D")
    data = array.reshape(1, -1) if array.ndim == 1 else array
    if data.shape[1] < 1:
        raise ValueError(f"{name} must have at least one feature")
    return data, array.shape


def _restore_shape(data: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    if len(shape) == 1:
        return np.asarray(data[0])
    return np.asarray(data)


def _nearest(data: np.ndarray, centers: np.ndarray) -> np.ndarray:
    differences = data[:, None, :] - centers[None, :, :]
    distances = np.sum(differences * differences, axis=-1)
    return np.asarray(np.argmin(distances, axis=1), dtype=int)


def _kmeans(
    data: np.ndarray,
    requested_k: int,
    rng: np.random.Generator,
    iters: int,
) -> np.ndarray:
    n_samples = data.shape[0]
    k = min(requested_k, n_samples)
    if k == 1:
        return np.asarray(np.mean(data, axis=0, keepdims=True))

    order = rng.permutation(n_samples)
    centers = data[order[:k]].copy()
    for _ in range(iters):
        labels = _nearest(data, centers)
        updated = centers.copy()
        empty: list[int] = []
        for cluster in range(k):
            mask = labels == cluster
            if np.any(mask):
                updated[cluster] = data[mask].mean(axis=0)
            else:
                empty.append(cluster)
        if empty:
            distances = np.sum((data - centers[labels]) ** 2, axis=1)
            farthest = np.argsort(distances)[::-1]
            for offset, cluster in enumerate(empty):
                updated[cluster] = data[farthest[offset % n_samples]]
        if np.allclose(updated, centers):
            break
        centers = updated
    return centers
