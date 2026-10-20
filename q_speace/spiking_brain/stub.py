"""Offline stub for the SpikingBrain satellite (T205).

Implements :class:`SpikingBrainCortex` with a deterministic, numpy-only
stand-in for the real W8ASpike-7B model. The stub is **not** a language
model: it derives its outputs from the current ILF state and a small
hash of the prompt. This is enough for:

- unit tests (deterministic given seed);
- CI smoke runs (no GPU, no download);
- development of the SIA/ILF/cortex integration without waiting for the
  model server to come up.

The numerical interface (belief vector, spike pattern, plasticity
coefficients, confidence) is identical to the real client, so callers do
not need to know which backend is in use.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Sequence

import numpy as np

from ..spiking import SpikePlasticity, dynamic_spikes
from ..spiking.encoder import SpikeEncodingResult
from .interface import LifecycleState, SpikingBrainUnavailableError
from .types import ThinkResult

# Default ILF classes: index 0 = "agree with current belief",
# index 1 = "revise", index 2 = "explore". The stub maps a hash of the
# prompt + coherence_phi into a soft distribution over these classes.
DEFAULT_N_CLASSES = 3


def _stable_unit_hash(text: str, n: int, seed: int = 0) -> np.ndarray:
    """Deterministic vector in [0,1] derived from ``text``.

    Uses SHAKE-style repeated SHA-256 to fill ``n`` slots. The output is
    L2-normalised so callers can use it as a softmax-temperature-free
    probability prior.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    chunks: list[float] = []
    counter = 0
    while len(chunks) < n:
        h = hashlib.sha256(f"{seed}:{counter}:{text}".encode()).digest()
        # 4 bytes per float, big-endian.
        for i in range(0, len(h), 4):
            if len(chunks) >= n:
                break
            v = int.from_bytes(h[i : i + 4], "big") / 0xFFFFFFFF
            chunks.append(v)
        counter += 1
    arr = np.asarray(chunks, dtype=float)
    arr = arr / max(float(np.linalg.norm(arr)), 1e-12)
    return arr


class StubSpikingBrain:
    """Numpy-only stub implementing the SpikingBrainCortex contract.

    Args:
        n_classes: dimension of the ILF belief vector (default 3).
        spike_k: dynamic-spike threshold divisor (W8ASpike default 3.0).
        spike_beta: ILF modulation coefficient of the spike threshold.
        plasticity_decay: EMA decay for the SpikePlasticity coefficients.
        seed: RNG seed for the rare random branch (mixed-in tiny noise).
    """

    def __init__(
        self,
        n_classes: int = DEFAULT_N_CLASSES,
        spike_k: float = 3.0,
        spike_beta: float = 0.1,
        plasticity_decay: float = 0.9,
        seed: int | None = None,
    ) -> None:
        self.n_classes = n_classes
        self.spike_k = spike_k
        self.spike_beta = spike_beta
        self.plasticity = SpikePlasticity(num_units=n_classes, decay=plasticity_decay, seed=seed)
        self._rng = np.random.default_rng(seed)
        self._call_count = 0
        # T-SPB-4 lifecycle state. Stubs default to READY (no I/O).
        self._lifecycle: LifecycleState = LifecycleState.READY

    # --- T-SPB-4: protocol surface ---

    backend_name: str = "stub"
    supports_async: bool = False
    supports_streaming: bool = False
    supports_tool: bool = False
    supports_retrieval: bool = False

    def lifecycle_state(self) -> LifecycleState:
        return self._lifecycle

    async def load(self) -> None:
        """Stubs are stateless — load is a no-op."""
        self._lifecycle = LifecycleState.READY

    async def shutdown(self) -> None:
        """Stubs have no resources to release."""
        self._lifecycle = LifecycleState.SHUTDOWN

    @property
    def memory(self) -> None:  # type: ignore[override]
        return None  # stubs are intentionally stateless for tests.

    # --- legacy aliases ---

    @property
    def backend(self) -> str:
        """Backward-compatible alias for ``backend_name``."""
        return self.backend_name

    def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        """Produce a deterministic ThinkResult derived from ``prompt`` + ILF.

        The stub does not generate natural language. It produces a short
        templated ``text`` summary so logging and tests can see the
        prompt/effect link without needing a real LM.
        """
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a str")
        if self._lifecycle == LifecycleState.SHUTDOWN:
            raise SpikingBrainUnavailableError("StubSpikingBrain is shut down")

        # 1. ILF belief: deterministic prior mixed with coherence_phi.
        prior = _stable_unit_hash(prompt, self.n_classes, seed=self._call_count)
        # Map prior onto a softmax with temperature 1/coherence_phi so that
        # higher coherence -> sharper belief.
        temp = max(1.0 - coherence_phi, 0.05)
        logits = np.log(np.maximum(prior, 1e-12)) / temp
        logits = logits - float(np.max(logits))
        belief = np.exp(logits)
        belief = belief / float(np.sum(belief))

        # 2. Spike pattern: dynamic_spikes on the belief with ILF gating.
        spikes: SpikeEncodingResult = dynamic_spikes(
            belief, k=self.spike_k, coherence_phi=coherence_phi, beta=self.spike_beta
        )

        # 3. Plasticity coefficients: SpikePlasticity EMA.
        self.plasticity.update(spikes.spikes)
        plasticity_coeffs = self.plasticity.coefficients()

        # 4. Confidence: entropy of belief rescaled into [0,1].
        entropy = float(-np.sum(belief * np.log(np.maximum(belief, 1e-12))))
        max_entropy = math.log(max(self.n_classes, 2))
        confidence = float(1.0 - entropy / max_entropy)
        # ILF coupling: low coherence pulls confidence down.
        confidence = float(confidence * (0.5 + 0.5 * coherence_phi))

        # 5. Text summary (templated, deterministic).
        summary = (
            f"[stub think #{self._call_count}] "
            f"classes={list(np.round(belief, 3).tolist())} "
            f"sparsity={spikes.sparsity:.2f} "
            f"conf={confidence:.2f}"
        )

        # 6. Latency: tiny synthetic value, bounded so tests stay fast.
        latency = 0.001 * (1 + n_tokens // 32)

        self._call_count += 1
        return ThinkResult(
            text=summary,
            confidence=confidence,
            belief=belief,
            spikes=spikes,
            plasticity=plasticity_coeffs,
            n_tokens=n_tokens,
            latency_s=latency,
            metadata={
                "backend": self.backend,
                "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16],
                "coherence_phi": float(coherence_phi),
            },
        )

    def health(self) -> dict:
        """Return a fake-but-honest health snapshot."""
        return {
            "backend": self.backend,
            "ready": True,
            "model": "stub-w8aspike-equivalent",
            "vram_mb": 0,
            "calls": self._call_count,
        }


class StubSpikingBrainV2:
    """Offline stub for the SpikingBrain 2.0 family (DSSA / MoBA).

    The numerical contract (ThinkResult) is identical to
    :class:`StubSpikingBrain`, but the *distribution* of the belief and
    the plasticity dynamics differ in two ways to mimic the V2 paper's
    Dual-Space Sparse Attention behaviour:

    - **Belief is flatter**: V2's MoBA top-k attention spreads mass
      across more classes; we map the prompt prior onto a softer
      softmax (``temp = 1.0`` regardless of coherence).
    - **Plasticity decays faster**: V2's Gated DeltaNet + sparse state
      expansion has shorter memory; we use ``decay=0.7`` instead of 0.9.

    This is enough to demonstrate that the factory can swap between
    backends without callers caring. When a real V2 checkpoint becomes
    available on HuggingFace (no public V2 model exists yet — checked
    August 2026), replace this class with a thin shim around
    ``AutoModelForCausalLM.from_pretrained(<v2-repo>, ...)`` exactly
    like ``StubSpikingBrain`` -> real HF client.
    """

    def __init__(
        self,
        n_classes: int = DEFAULT_N_CLASSES,
        spike_k: float = 2.5,
        spike_beta: float = 0.2,
        plasticity_decay: float = 0.7,
        seed: int | None = None,
    ) -> None:
        self.n_classes = n_classes
        self.spike_k = spike_k
        self.spike_beta = spike_beta
        self.plasticity = SpikePlasticity(num_units=n_classes, decay=plasticity_decay, seed=seed)
        self._rng = np.random.default_rng(seed)
        self._call_count = 0
        # T-SPB-4 lifecycle state. Stubs default to READY (no I/O).
        self._lifecycle: LifecycleState = LifecycleState.READY

    # --- T-SPB-4: protocol surface (V2) ---

    backend_name: str = "stub-v2"
    supports_async: bool = False
    supports_streaming: bool = False
    supports_tool: bool = False
    supports_retrieval: bool = False

    def lifecycle_state(self) -> LifecycleState:
        return self._lifecycle

    async def load(self) -> None:
        self._lifecycle = LifecycleState.READY

    async def shutdown(self) -> None:
        self._lifecycle = LifecycleState.SHUTDOWN

    @property
    def memory(self) -> None:  # type: ignore[override]
        return None

    @property
    def backend(self) -> str:
        """Backward-compatible alias for ``backend_name``."""
        return self.backend_name

    def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        if not isinstance(prompt, str):
            raise TypeError("prompt must be a str")
        if self._lifecycle == LifecycleState.SHUTDOWN:
            raise SpikingBrainUnavailableError("StubSpikingBrainV2 is shut down")

        prior = _stable_unit_hash(prompt, self.n_classes, seed=self._call_count)
        # V2: temperature is always 1.0 (softer than v1's 1-coherence mapping).
        logits = np.log(np.maximum(prior, 1e-12))
        logits = logits - float(np.max(logits))
        belief = np.exp(logits)
        belief = belief / float(np.sum(belief))

        spikes = dynamic_spikes(
            belief, k=self.spike_k, coherence_phi=coherence_phi, beta=self.spike_beta
        )
        self.plasticity.update(spikes.spikes)
        plasticity_coeffs = self.plasticity.coefficients()

        entropy = float(-np.sum(belief * np.log(np.maximum(belief, 1e-12))))
        max_entropy = math.log(max(self.n_classes, 2))
        confidence = float(1.0 - entropy / max_entropy)
        confidence = float(confidence * (0.5 + 0.5 * coherence_phi))

        summary = (
            f"[stub-v2 think #{self._call_count}] "
            f"classes={list(np.round(belief, 3).tolist())} "
            f"sparsity={spikes.sparsity:.2f} "
            f"conf={confidence:.2f}"
        )

        latency = 0.002 * (1 + n_tokens // 32)  # V2 is "slower" in our stub
        self._call_count += 1
        return ThinkResult(
            text=summary,
            confidence=confidence,
            belief=belief,
            spikes=spikes,
            plasticity=plasticity_coeffs,
            n_tokens=n_tokens,
            latency_s=latency,
            metadata={
                "backend": self.backend,
                "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16],
                "coherence_phi": float(coherence_phi),
                "variant": "DSSA/MoBA (stub)",
            },
        )

    def health(self) -> dict:
        return {
            "backend": self.backend,
            "ready": True,
            "model": "stub-dssa-moba-equivalent",
            "vram_mb": 0,
            "calls": self._call_count,
        }
