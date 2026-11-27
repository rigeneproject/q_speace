"""Pseudo-spiking layer for Q-SPEACE (task T202).

Selective adaptation of SpikingBrain-7B (arXiv:2509.05276) dynamic spike
encoding to the quantum layer: sparse integer spike representation,
event-driven energy, plasticity coefficients, classical spike-correlation
binding and spike-entropy gradients. Pseudo-spiking at tensor level only;
numpy-only, no torch, no neuromorphic hardware.
"""

from __future__ import annotations

from .bridge import SpikeQuantumBridge
from .causal import CausalEdge, StructuralCausalDAG, spike_temporal_asymmetry
from .correlation import (
    entangle_by_correlation,
    spike_correlation,
    spike_entropy_gradient,
)
from .criticality import CriticalityController, CriticalityRegime, CriticalityState
from .encoder import SpikeEncodingResult, dynamic_spikes, sparsity, spike_count, spike_rate
from .linear import SpikeEncodedLinear
from .morphogenesis import (
    CognitiveRegime,
    HomeodynaBalanceController,
    HomeodynaEvaluation,
    KineticaRegimeController,
    RegimeConfig,
    RegimeTransition,
)
from .ncm_calibration import (
    CalibrationConfig,
    CalibrationDataset,
    CalibrationResult,
    make_calibration_dataset,
    max_abs_cohens_d,
    run_calibration,
)
from .ncm_codec import CodecCodes, CodecConfig, ResidualCodec
from .plasticity import SpikePlasticity
from .prereg_lock import (
    canonical_json,
    compute_lock_sha256,
    lock_section,
    verify_lock,
)
from .reasoning import (
    RelationEdge,
    SymbolicGraphReasoner,
    TDMMaintenanceScheduler,
    TDMOperatingMode,
    TDMPhase,
    TDMScheduleTick,
)

__all__ = [
    "SpikeEncodingResult",
    "dynamic_spikes",
    "spike_count",
    "spike_rate",
    "sparsity",
    "SpikeEncodedLinear",
    "SpikePlasticity",
    "spike_correlation",
    "entangle_by_correlation",
    "spike_entropy_gradient",
    "SpikeQuantumBridge",
    "CodecConfig",
    "CodecCodes",
    "ResidualCodec",
    "CalibrationConfig",
    "CalibrationDataset",
    "CalibrationResult",
    "make_calibration_dataset",
    "max_abs_cohens_d",
    "run_calibration",
    "canonical_json",
    "compute_lock_sha256",
    "lock_section",
    "verify_lock",
    "CriticalityController",
    "CriticalityRegime",
    "CriticalityState",
    "CausalEdge",
    "StructuralCausalDAG",
    "spike_temporal_asymmetry",
    "RelationEdge",
    "SymbolicGraphReasoner",
    "TDMMaintenanceScheduler",
    "TDMOperatingMode",
    "TDMPhase",
    "TDMScheduleTick",
    "CognitiveRegime",
    "RegimeConfig",
    "RegimeTransition",
    "KineticaRegimeController",
    "HomeodynaEvaluation",
    "HomeodynaBalanceController",
]
