"""SpikingBrain satellite (task T205).

Bridges Q-SPEACE (numpy core, Windows) with SpikingBrain-7B W8ASpike
(vLLM server, WSL2 + CUDA). The package exposes a single interface
(:class:`SpikingBrainCortex`) with two interchangeable backends:

- :class:`StubSpikingBrain` / :class:`StubSpikingBrainV2` — pure
  numpy, deterministic, offline. Used for tests, CI and smoke runs.
  ``V2`` mimics the SpikingBrain 2.0 (DSSA/MoBA) flavour.
- :class:`HTTPSpikingBrainClient` — async httpx client talking to the
  FastAPI sidecar in ``spiking_brain_server/``.

The factory :func:`make_spiking_brain` selects the backend via
environment variables:

- ``Q_SPEACE_BRAIN_ENDPOINT`` empty/unset ⇒ stub; otherwise the URL of
  the sidecar (an :class:`HTTPSpikingBrainClient` is returned).
- ``Q_SPEACE_BRAIN_MODEL=v1`` (default) or ``v2`` selects which stub
  flavour to return when no endpoint is set. The HTTP backend ignores
  this env var — the sidecar itself decides which model to load.

The cortex converts language-model output into three SPEACE-native
representations:

- ``ThinkResult.belief``        — ILF belief vector (over the ILF classes)
- ``ThinkResult.spikes``        — ``SpikeEncodingResult`` (T202 dynamic spikes)
- ``ThinkResult.plasticity``    — ``np.ndarray`` in [0,1] for downstream
                                  modulators (entanglement fidelity, ILF weight)

BCEL: the firing of biological neurons is *accidental*; only the integer
quantization rule survives in silicon. The ``SpikingBrainCortex`` is the
*functional* binding layer between language output and ILF — not a
conscious entity.
"""

from __future__ import annotations

from .client import HTTPSpikingBrainClient
from .cortex import CortexReport, SpikingBrainCortex
from .evaluation import CalibrationReport, calibration_report
from .factory import make_spiking_brain
from .interface import (
    LifecycleState,
    SpikingBrainCognitiveInterface,
    SpikingBrainError,
    SpikingBrainMemoryError,
    SpikingBrainQualityError,
    SpikingBrainTimeoutError,
    SpikingBrainUnavailableError,
)
from .memory import (
    EpisodicMemory,
    Memory,
    SemanticEpisodicMemory,
    WorkingMemory,
    embed_text_hashed,
)
from .myelination import (
    BatchRoleDeliberationCodec,
    HystereticLoadBalancer,
    LoadSnapshot,
    MyelinatedPath,
    MyelinationRegistry,
)
from .stub import StubSpikingBrain, StubSpikingBrainV2
from .truth_engine import (
    ActionDegradationGate,
    ActionMode,
    CycleObservation,
    CyclePrediction,
    CycleSurprise,
    EpistemicAssessment,
    EpistemicClass,
    ObservationDigest,
    StructuralPredictiveCoder,
    TruthEngine,
)
from .types import ThinkResult

__all__ = [
    "SpikingBrainCortex",
    "CortexReport",
    "CalibrationReport",
    "calibration_report",
    "ThinkResult",
    "StubSpikingBrain",
    "StubSpikingBrainV2",
    "HTTPSpikingBrainClient",
    "make_spiking_brain",
    # T-SPB-4 protocol surface
    "SpikingBrainCognitiveInterface",
    "LifecycleState",
    "SpikingBrainError",
    "SpikingBrainUnavailableError",
    "SpikingBrainTimeoutError",
    "SpikingBrainQualityError",
    "SpikingBrainMemoryError",
    # T-SPB-4 memory subsystem
    "Memory",
    "WorkingMemory",
    "EpisodicMemory",
    "SemanticEpisodicMemory",
    "embed_text_hashed",
    # T249-03 epistemic provenance & predictive cycle coding
    "ActionDegradationGate",
    "ActionMode",
    "CycleObservation",
    "CyclePrediction",
    "CycleSurprise",
    "EpistemicAssessment",
    "EpistemicClass",
    "ObservationDigest",
    "StructuralPredictiveCoder",
    "TruthEngine",
    # T256-06 myelination, load balancing & batch role codec
    "MyelinatedPath",
    "MyelinationRegistry",
    "LoadSnapshot",
    "HystereticLoadBalancer",
    "BatchRoleDeliberationCodec",
]
