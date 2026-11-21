"""T229 bounded sensor episodes and paired branches of the T228 software cortex."""

from __future__ import annotations

import copy
import hashlib
import math
import pickle
import random
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from q_speace.spiking_brain.cortex import SpikingBrainCortex

from .error_memory import BenchConfig, SyntheticBackend, reference_q
from .error_memory_verifier import verify

RUNTIME_PROTOCOL = {
    "horizon": 48,
    "prefix_ticks": 8,
    "prefix_decay": 0.9,
    "initial_ema": [1.0, 0.5],
    "baseline": 0.5,
    "sensor_noise_uniform_half_width": {"precise": 0.02, "noisy": 0.40},
    "amplitude_uniform": {"precise": [0.30, 0.45], "noisy": [0.005, 0.025]},
    "duration_uniform_integers": [12, 24],
    "context": "population std of second sensor during prefix divided by 0.25",
    "target": "stationary T228 ILF q_star for noiseless latent rates",
    "recovery_band_tv": 0.01,
    "recovery_consecutive": 3,
}
_CONFIG = BenchConfig(snapshot=(1.0, 0.5), horizon=48)
_PREFIX = 8


@dataclass
class Prepared:
    """Private evaluator state. The selector receives only context."""

    context: float
    prefix: list[dict[str, Any]]
    snapshot_id: str
    description: dict[str, Any]
    cortex: SpikingBrainCortex
    references: list[np.ndarray]


def _scenario(seed: int, family: str) -> dict[str, Any]:
    if family not in ("rectangle", "triangle"):
        raise ValueError(f"unknown family {family!r}")

    def stream(label: str) -> random.Random:
        return random.Random(f"t229:{label}:{seed}")

    precise = stream("regime").random() < 0.5
    width = 0.02 if precise else 0.40
    amplitude_rng = stream("amplitude")
    amplitude = (
        amplitude_rng.uniform(0.30, 0.45) if precise else amplitude_rng.uniform(0.005, 0.025)
    )
    amplitude *= amplitude_rng.choice((-1, 1))
    duration = stream("duration").randint(12, 24)
    pulse = [1.0] * duration
    if family == "triangle":
        pulse = [min(i + 1, duration - i) / math.ceil(duration / 2) for i in range(duration)]
    latent = (
        [0.5] * _PREFIX
        + [0.5 + amplitude * scale for scale in pulse]
        + [0.5] * (_CONFIG.horizon - _PREFIX - duration)
    )
    noise = stream("sensor")
    observed = [u + noise.uniform(-width, width) for u in latent]
    return {
        "family": family,
        "regime": "precise" if precise else "noisy",
        "duration": duration,
        "signed_amplitude": amplitude,
        "latent": latent,
        "observed": observed,
    }


async def _tick(
    cortex: SpikingBrainCortex,
    scenario: dict[str, Any],
    references: list[np.ndarray],
    index: int,
    phase: str,
) -> dict[str, Any]:
    backend = cast(SyntheticBackend, cortex.backend)
    observed = scenario["observed"][index]
    backend.rates = np.array([1.0, observed])
    report = await cortex.tick("T229 bounded sensor", n_tokens=0)
    if report.reason.startswith("backend error:"):
        raise RuntimeError(report.reason)
    q_star = cortex.ilf.q_star
    ref = references[index]
    return {
        "tick": index + 1,
        "phase": phase,
        "input": [1.0, observed],
        "latent": [1.0, scenario["latent"][index]],
        "ema": backend.kernel._ema.tolist(),
        "decay": backend.kernel.decay,
        "q_star": q_star.tolist(),
        "reference": ref.tolist(),
        "tv": float(np.abs(q_star - ref).sum() / 2),
        "approved": report.approved,
        "reason": report.reason,
    }


async def prepare(seed: int, family: str) -> Prepared:
    """Generate evaluator data and execute the common observation prefix."""
    scenario = _scenario(seed, family)
    backend = SyntheticBackend(_CONFIG.default_decay, _CONFIG)
    cortex = SpikingBrainCortex(backend=backend)
    # Reference uses the latent signal independently of both choice and sensor noise.
    targets = {u: reference_q(np.array([1.0, u]), _CONFIG) for u in set(scenario["latent"])}
    refs = [targets[u] for u in scenario["latent"]]
    prefix = [await _tick(cortex, scenario, refs, i, "prefix") for i in range(_PREFIX)]
    context = float(np.std([tick["input"][1] for tick in prefix])) / 0.25
    # Only hash a local object. No pickle is loaded and no future evaluator data
    # resides in the backend or cortex.
    snapshot_id = hashlib.sha256(pickle.dumps(cortex, protocol=5)).hexdigest()
    return Prepared(context, prefix, snapshot_id, scenario, cortex, refs)


async def measure(prepared: Prepared, decay: float) -> dict[str, Any]:
    """Apply a single certified choice to an independent full-state branch."""
    if verify(decay).status != "VALIDA":
        raise ValueError("A certified T228 decay is required")
    cortex = copy.deepcopy(prepared.cortex)
    backend = cast(SyntheticBackend, cortex.backend)
    backend.kernel.decay = decay
    ticks = list(prepared.prefix)
    return_start = _PREFIX + prepared.description["duration"]
    streak = 0
    recovery: int | None = None
    for i in range(_PREFIX, _CONFIG.horizon):
        phase = "perturbation" if i < return_start else "return"
        tick = await _tick(cortex, prepared.description, prepared.references, i, phase)
        ticks.append(tick)
        if phase == "return":
            streak = streak + 1 if tick["tv"] <= _CONFIG.band_tv else 0
            if streak == _CONFIG.consecutive and recovery is None:
                recovery = i - return_start + 1
    pre = math.fsum(t["tv"] for t in ticks[:_PREFIX])
    perturb = math.fsum(t["tv"] for t in ticks[_PREFIX:return_start])
    after = math.fsum(t["tv"] for t in ticks[return_start:])
    return {
        "loss": pre + perturb + after,
        "prefix_loss": pre,
        "perturbation_loss": perturb,
        "return_loss": after,
        "recovery_ticks": recovery,
        "recovered": recovery is not None,
        "censored_ticks": recovery if recovery is not None else _CONFIG.horizon - return_start + 1,
        "ticks": ticks,
    }
