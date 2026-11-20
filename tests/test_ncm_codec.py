"""Tests for the T222 Phase 0 multiscale residual codec."""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.spiking import CodecConfig, ResidualCodec


def _data(seed: int = 0, n: int = 64, d: int = 6) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, d))
    x[:, 0] *= 3.0
    return x


def _codec(levels: int = 3, codebook_size: int = 8, seed: int = 0) -> ResidualCodec:
    return ResidualCodec(CodecConfig(levels=levels, codebook_size=codebook_size, seed=seed))


def test_fit_encode_decode_shapes_and_error_keys() -> None:
    x = _data()
    codec = _codec().fit(x)
    codes = codec.encode(x)
    reconstruction = codec.decode(codes)
    assert len(codes.indices) == 3
    assert reconstruction.shape == x.shape
    errors = codec.reconstruction_errors(x)
    assert len(errors["mse_per_level"]) == 3
    assert errors["mse_total"] == pytest.approx(errors["mse_per_level"][-1])


def test_full_levels_not_worse_than_mean_on_training_data() -> None:
    x = _data()
    codec = _codec().fit(x)
    codes = codec.encode(x)
    mean_reconstruction = codec.decode(codes, levels=0)
    full_reconstruction = codec.decode(codes)
    mean_mse = float(np.mean((x - mean_reconstruction) ** 2))
    full_mse = float(np.mean((x - full_reconstruction) ** 2))
    assert full_mse <= mean_mse + 1e-12


def test_zero_level_ablation_returns_fitted_mean() -> None:
    x = _data()
    codec = _codec().fit(x)
    codes = codec.encode(x)
    mean_reconstruction = codec.decode(codes, levels=0)
    assert np.allclose(mean_reconstruction[0], x.mean(axis=0))


def test_corruption_changes_codes_and_reconstruction() -> None:
    x = _data()
    codec = _codec().fit(x)
    codes = codec.encode(x)
    corrupted = codec.corrupt(codes, level=0, fraction=0.5, seed=1)
    assert not np.array_equal(corrupted.indices[0], codes.indices[0])
    assert not np.allclose(codec.decode(corrupted), codec.decode(codes))


def test_corruption_zero_fraction_is_identity() -> None:
    x = _data()
    codec = _codec().fit(x)
    codes = codec.encode(x)
    corrupted = codec.corrupt(codes, level=1, fraction=0.0, seed=2)
    for original, changed in zip(codes.indices, corrupted.indices, strict=True):
        np.testing.assert_array_equal(original, changed)


def test_same_seed_is_deterministic() -> None:
    x = _data(seed=3)
    first = _codec(seed=7).fit(x)
    second = _codec(seed=7).fit(x)
    np.testing.assert_allclose(first.codebooks[0], second.codebooks[0])
    np.testing.assert_array_equal(first.encode(x).indices[0], second.encode(x).indices[0])


def test_one_dimensional_input_roundtrip() -> None:
    x = _data()[0]
    codec = _codec().fit(x)
    reconstruction = codec.decode(codec.encode(x))
    assert reconstruction.shape == x.shape


def test_dimension_mismatch_raises() -> None:
    codec = _codec().fit(_data())
    with pytest.raises(ValueError):
        codec.encode(np.zeros((2, 99)))


def test_invalid_config_raises() -> None:
    with pytest.raises(ValueError):
        CodecConfig(levels=0).validate()
    with pytest.raises(ValueError):
        CodecConfig(codebook_size=1).validate()
    with pytest.raises(ValueError):
        CodecConfig(kmeans_iters=0).validate()
