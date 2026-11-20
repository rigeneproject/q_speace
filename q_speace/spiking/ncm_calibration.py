"""Calibration-only harness for T222 Phase 0.

This harness uses only a train partition and a calibration partition. It never
accepts, loads, or evaluates held-out data. It does **not** decide whether the
DoD is met: it reports calibration observations that a human uses to write and
lock the thresholds in ``docs/T222_PREREG.json -> pre_evaluation`` before the
separate evaluation run.

The probe is a deterministic effect-size statistic (maximum absolute Cohen's d
across features) between a perturbed and an unperturbed class. It is not a
trained classifier and not a quality claim.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from ..metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from .encoder import dynamic_spikes
from .ncm_codec import CodecCodes, CodecConfig, ResidualCodec


@dataclass(frozen=True)
class CalibrationConfig:
    """Inputs fixed before the calibration run (T222_PREREG.json)."""

    n_train: int = 256
    n_calibration: int = 64
    n_features: int = 8
    positive_offset: float = 1.0
    spike_k: float = 3.0
    corruption_fraction: float = 0.2
    seed_split: int = 0
    seed_codebook: int = 0
    seed_corruption: int = 0
    codec: CodecConfig = field(default_factory=CodecConfig)

    def validate(self) -> None:
        if self.n_train < 8:
            raise ValueError("n_train must be >= 8")
        if self.n_calibration < 8:
            raise ValueError("n_calibration must be >= 8")
        if self.n_features < 2:
            raise ValueError("n_features must be >= 2")
        if self.positive_offset <= 0.0:
            raise ValueError("positive_offset must be > 0")
        if self.spike_k <= 0.0:
            raise ValueError("spike_k must be > 0")
        if not (0.0 <= self.corruption_fraction <= 1.0):
            raise ValueError("corruption_fraction must be in [0, 1]")
        self.codec.validate()


@dataclass(frozen=True)
class CalibrationDataset:
    """Train/calibration partitions only; no held-out field exists."""

    x_train: np.ndarray
    x_calibration: np.ndarray
    y_calibration: np.ndarray


@dataclass(frozen=True)
class CalibrationResult:
    """Calibration report. ``dod_eligible`` is always False."""

    report: dict[str, Any]


def make_calibration_dataset(config: CalibrationConfig) -> CalibrationDataset:
    """Build the synthetic perturbation dataset for calibration only.

    Class 1 has a positive offset on the first half of the features. The split
    is deterministic from ``seed_split``. No held-out samples are produced.
    """
    config.validate()
    n_total = config.n_train + config.n_calibration
    rng = np.random.default_rng(config.seed_split)
    x = rng.normal(size=(n_total, config.n_features))
    labels = (rng.random(n_total) < 0.5).astype(int)
    half = max(1, config.n_features // 2)
    x[labels == 1, :half] += config.positive_offset

    order = rng.permutation(n_total)
    x = x[order]
    labels = labels[order]
    return CalibrationDataset(
        x_train=x[: config.n_train].copy(),
        x_calibration=x[config.n_train :].copy(),
        y_calibration=labels[config.n_train :].copy(),
    )


def spike_readout(x: np.ndarray, k: float) -> np.ndarray:
    """Per-sample, per-feature absolute spike counts (fixed readout shape)."""
    return np.asarray(np.abs(dynamic_spikes(x, k=k).spikes))


def codec_readout(codec: ResidualCodec, x: np.ndarray) -> np.ndarray:
    """Decoded representation, same feature shape as ``x``."""
    return codec.decode(codec.encode(x))


def max_abs_cohens_d(readout: np.ndarray, labels: np.ndarray) -> float:
    """Maximum absolute Cohen's d across features (deterministic probe)."""
    values = np.asarray(readout, dtype=float)
    y = np.asarray(labels).astype(int)
    if values.ndim != 2:
        raise ValueError("readout must be 2-D (samples x features)")
    if values.shape[0] != y.shape[0]:
        raise ValueError("readout and labels must have the same number of samples")
    positive = values[y == 1]
    negative = values[y == 0]
    if positive.shape[0] < 2 or negative.shape[0] < 2:
        raise ValueError("both classes need at least two samples")

    difference = positive.mean(axis=0) - negative.mean(axis=0)
    pooled = np.sqrt((positive.var(axis=0, ddof=1) + negative.var(axis=0, ddof=1)) / 2.0)
    pooled = np.maximum(pooled, 1e-12)
    return float(np.max(np.abs(difference) / pooled))


def run_calibration(
    config: CalibrationConfig | None = None,
    *,
    run_id: str | None = None,
) -> CalibrationResult:
    """Run Phase 0 calibration and return a reproducible report.

    Guarantees on the returned report:
    - ``dod_eligible`` is False;
    - ``heldout_used`` is False;
    - no evaluation partition is used;
    - Sevo and measured joules are reported as unavailable, not fabricated.
    """
    cfg = config or CalibrationConfig()
    cfg.validate()
    dataset = make_calibration_dataset(cfg)

    started = time.perf_counter()
    codec = ResidualCodec(cfg.codec).fit(dataset.x_train)
    reconstruction = codec.reconstruction_errors(dataset.x_calibration)
    codes = codec.encode(dataset.x_calibration)

    spikes = dynamic_spikes(dataset.x_calibration, k=cfg.spike_k)
    readouts: dict[str, np.ndarray] = {
        "spike": np.abs(spikes.spikes),
        "codec": codec_readout(codec, dataset.x_calibration),
        "spike+codec": codec.decode(codec.encode(spikes.spikes)),
    }
    probe = {
        name: max_abs_cohens_d(values, dataset.y_calibration) for name, values in readouts.items()
    }

    degradation = _degradation_curve(codec, codes, dataset)
    corruption = _corruption_curve(codec, codes, dataset, cfg)
    elapsed = time.perf_counter() - started

    spike_count = int(spikes.num_spikes)
    cost_model = QuantumCostModel()
    spike_operation = QuantumOperation(num_qubits=0, num_gates=0, num_spikes=spike_count)
    spike_joules = float(cost_model.energy_joules(spike_operation, duration_s=elapsed))

    report: dict[str, Any] = {
        "report_version": "T222-P0-calibration-v0",
        "run_id": run_id,
        "status": "calibration_only",
        "dod_eligible": False,
        "heldout_used": False,
        "partitions": {
            "train_samples": int(dataset.x_train.shape[0]),
            "calibration_samples": int(dataset.x_calibration.shape[0]),
            "evaluation_samples": 0,
        },
        "config": {
            "n_train": cfg.n_train,
            "n_calibration": cfg.n_calibration,
            "n_features": cfg.n_features,
            "positive_offset": cfg.positive_offset,
            "spike_k": cfg.spike_k,
            "corruption_fraction": cfg.corruption_fraction,
            "seed_split": cfg.seed_split,
            "seed_codebook": cfg.seed_codebook,
            "seed_corruption": cfg.seed_corruption,
            "codec": asdict(cfg.codec),
        },
        "observations": {
            "reconstruction": reconstruction,
            "probe_effect_size": probe,
            "degradation": degradation,
            "corruption": corruption,
        },
        "cost_registers": {
            "wall_time_s": float(elapsed),
            "operations_estimate": _operations_estimate(cfg, dataset),
            "sevo": None,
            "sevo_reason": (
                "No approved utility/entropy mapping for this calibration; "
                "Sevo is not fabricated."
            ),
            "delta_s_epsilon": 1e-12,
            "delta_s_nonpositive_cases": None,
            "estimated_joules": {
                "spike": spike_joules,
                "codec": None,
                "spike+codec": spike_joules,
                "method": (
                    "QuantumCostModel with num_qubits=0, num_gates=0, "
                    "num_spikes=observed; classical codec has no mapping."
                ),
                "label": "estimated, not measured",
            },
            "measured_joules": "non misurati",
            "measured_joules_reason": "No physical energy measurement is available.",
        },
        "threshold_rule": (
            "A human derives thresholds from these calibration observations, writes "
            "them in pre_evaluation, and locks that section before the evaluation run."
        ),
        "thresholds_locked": False,
    }
    return CalibrationResult(report=report)


def _degradation_curve(
    codec: ResidualCodec,
    codes: CodecCodes,
    dataset: CalibrationDataset,
) -> list[dict[str, float | int]]:
    curve: list[dict[str, float | int]] = []
    for levels in range(1, len(codec.codebooks) + 1):
        reconstruction = codec.ablate(codes, levels=levels)
        curve.append(
            {
                "levels": levels,
                "mse": _mse(dataset.x_calibration, reconstruction),
                "probe_effect_size": max_abs_cohens_d(reconstruction, dataset.y_calibration),
            }
        )
    return curve


def _corruption_curve(
    codec: ResidualCodec,
    codes: CodecCodes,
    dataset: CalibrationDataset,
    config: CalibrationConfig,
) -> list[dict[str, float | int]]:
    curve: list[dict[str, float | int]] = []
    for level in range(len(codec.codebooks)):
        corrupted = codec.corrupt(
            codes,
            level=level,
            fraction=config.corruption_fraction,
            seed=config.seed_corruption + level,
        )
        reconstruction = codec.decode(corrupted)
        curve.append(
            {
                "level": level,
                "mse": _mse(dataset.x_calibration, reconstruction),
                "probe_effect_size": max_abs_cohens_d(reconstruction, dataset.y_calibration),
            }
        )
    return curve


def _mse(reference: np.ndarray, reconstruction: np.ndarray) -> float:
    return float(np.mean((np.asarray(reference) - np.asarray(reconstruction)) ** 2))


def _operations_estimate(config: CalibrationConfig, dataset: CalibrationDataset) -> dict[str, int]:
    samples = int(dataset.x_calibration.shape[0])
    features = int(dataset.x_calibration.shape[1])
    per_level = samples * features * config.codec.codebook_size
    return {
        "distance_ops_per_level": per_level,
        "distance_ops_total": per_level * config.codec.levels,
    }
