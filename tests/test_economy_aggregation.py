"""Tests for the q_speace_economy aggregation module (T6.3)."""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.economy.aggregation import aggregate, kl, lossless_check


def test_kl_zero_for_identical() -> None:
    p = np.array([0.5, 0.3, 0.2])
    assert kl(p, p) == pytest.approx(0.0, abs=1e-12)


def test_kl_positive_for_different() -> None:
    p = np.array([0.9, 0.1])
    q = np.array([0.5, 0.5])
    assert kl(p, q) > 0.0


def test_kl_rejects_negative() -> None:
    with pytest.raises(ValueError):
        kl(np.array([-0.1, 1.1]), np.array([0.5, 0.5]))


def test_kl_rejects_multidim() -> None:
    with pytest.raises(ValueError):
        kl(np.array([[0.5, 0.5]]), np.array([0.5, 0.5]))


def test_aggregate_two_identical_distributions_returns_same() -> None:
    p = np.array([0.7, 0.2, 0.1])
    out = aggregate([p, p])
    np.testing.assert_allclose(out, p, atol=1e-6)


def test_aggregate_uniform_weights_orthogonal_spikes() -> None:
    # Bregman projection of two orthogonal spikes puts ~equal mass on the
    # shared components (here: indices 0 and 1); the unshared index gets
    # a numerical floor (exp(log(eps))) ≈ eps.
    p1 = np.array([1.0, 0.0, 0.0])
    p2 = np.array([0.0, 1.0, 0.0])
    out = aggregate([p1, p2])
    assert out[0] == pytest.approx(0.5, abs=1e-6)
    assert out[1] == pytest.approx(0.5, abs=1e-6)
    assert out[2] < 1e-6
    assert np.isclose(float(np.sum(out)), 1.0, atol=1e-9)


def test_aggregate_weighted_5_distributions() -> None:
    rng = np.random.default_rng(42)
    dists = [rng.dirichlet(np.ones(4)) for _ in range(5)]
    w = np.array([0.5, 0.2, 0.1, 0.1, 0.1])
    out = aggregate(dists, weights=w)
    assert out.shape == (4,)
    assert np.all(out >= 0.0)
    assert np.isclose(float(np.sum(out)), 1.0)


def test_aggregate_imbalanced_weights_skew_toward_heavier() -> None:
    p1 = np.array([0.99, 0.005, 0.005])
    p2 = np.array([0.005, 0.99, 0.005])
    out = aggregate([p1, p2], weights=[0.9, 0.1])
    # Weighted barycentre should lean toward p1 (heavier).
    assert out[0] > out[1]


def test_aggregate_rejects_too_few() -> None:
    with pytest.raises(ValueError):
        aggregate([np.array([0.5, 0.5])])


def test_aggregate_rejects_mismatched_dims() -> None:
    with pytest.raises(ValueError):
        aggregate([np.array([0.5, 0.5]), np.array([0.3, 0.3, 0.4])])


def test_aggregate_rejects_negative_weights() -> None:
    with pytest.raises(ValueError):
        aggregate([np.array([0.5, 0.5]), np.array([0.5, 0.5])], weights=[1.0, -0.5])


def test_aggregate_respects_max_iter() -> None:
    p = np.array([0.6, 0.3, 0.1])
    # max_iter=1 forces a partial projection; result may not be exact but
    # must still be a valid probability vector.
    out = aggregate([p, p[::-1]], max_iter=1)
    assert out.shape == (3,)
    assert np.isclose(float(np.sum(out)), 1.0)


def test_lossless_check_uniform_input() -> None:
    p = np.array([1 / 3, 1 / 3, 1 / 3])
    bary = aggregate([p, p, p])
    assert lossless_check(bary, [p, p, p])


def test_lossless_check_two_distributions() -> None:
    p1 = np.array([0.7, 0.2, 0.1])
    p2 = np.array([0.1, 0.2, 0.7])
    bary = aggregate([p1, p2])
    assert lossless_check(bary, [p1, p2])
