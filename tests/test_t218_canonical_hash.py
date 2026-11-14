"""T218 refinement R1 — IEEE 754 canonical parameter hashing.

Acceptance: identical vectors hash identically across ±0.0, below-grid
ULP noise and platform byte order; genuine differences still hash
differently; serialization is big-endian '>f8' by construction.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from q_speace.bridge.protocol import canonical_param_hash


def test_minus_zero_and_plus_zero_hash_identically() -> None:
    p = np.array([0.0, 0.5, -0.25])
    q = np.array([-0.0, 0.5, -0.25])
    assert canonical_param_hash(p) == canonical_param_hash(q)


def test_sub_grid_ulp_noise_is_quantised_away() -> None:
    p = np.array([0.1234567890123, 1.0])
    noisy = p + np.array([1e-12, -1e-12])  # below the 1e-9 quantisation grid
    assert canonical_param_hash(p) == canonical_param_hash(noisy)


def test_genuine_differences_still_change_the_hash() -> None:
    p = np.array([0.123456789, 1.0])
    q = np.array([0.123456790, 1.0])  # differs at the 9th decimal
    assert canonical_param_hash(p) != canonical_param_hash(q)


def test_big_endian_serialisation_is_canonical() -> None:
    """The hash equals SHA-256 over explicit big-endian '>f8' bytes."""
    p = np.array([1.5, -2.25, 0.0])
    q = np.round(p, 9)
    q = np.where(np.abs(q) == 0.0, 0.0, q)
    expected = hashlib.sha256(np.asarray(q, dtype=">f8").tobytes()).hexdigest()
    assert canonical_param_hash(p) == expected


def test_quantised_projection_output_is_stable() -> None:
    """A projected candidate recomputed on another run (float noise) keeps
    the same hash — the idempotency key survives reproducibility checks."""
    from q_speace.bridge.screening import screen_candidate

    kwargs = {
        "lower": np.array([0.0, 0.0]),
        "upper": np.array([10.0, 10.0]),
        "scale": np.array([1.0, 1.0]),
        "budget": 1.0,
    }
    r1 = screen_candidate(np.array([10.0, 10.0]), np.array([0.0, 0.0]), **kwargs)
    # second run: identical inputs recomputed after a ULP perturbation of
    # the proposal (simulating cross-run float drift)
    r2 = screen_candidate(np.array([10.0, 10.0]) + 1e-15, np.array([0.0, 0.0]), **kwargs)
    assert r1.candidate is not None and r2.candidate is not None
    assert canonical_param_hash(r1.candidate) == canonical_param_hash(r2.candidate)


def test_rejects_non_1d_vectors() -> None:
    with pytest.raises(ValueError):
        canonical_param_hash(np.zeros((2, 2)))
