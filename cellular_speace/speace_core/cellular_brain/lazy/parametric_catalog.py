"""ParametricCatalog — compact key -> function spec.

The catalog maps (region, function, subfunction) tuples to parametric
FunctionSpec records. Each record encodes:
  - the cell type to instantiate
  - default parameter values
  - a math function description for the role
  - lazy activation criteria
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class FunctionSpec:
    """A single functional role within SPEACE.

    This is the *parametric* form of a neuron: instead of materializing
    billions of them, we keep one FunctionSpec per distinct function.
    """
    key: str
    region: str
    function: str
    cell_type: str = "generic_neuron"
    threshold: float = 0.5
    plasticity_rate: float = 0.05
    tau_ms: float = 10.0
    refractory_ms: float = 2.0
    resting: float = 0.0
    reset: float = 0.0
    weight_default: float = 0.5
    delay_ms: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    math_function: Optional[str] = None
    # math_function is a free-form description of the underlying
    # mathematical model (e.g. "LIF: dv/dt = (v_rest - v + I)/tau")
    lazy_criterion: Optional[Callable[[Dict[str, Any]], bool]] = None

    def matches_signal(self, signal: "SignalKey") -> bool:  # noqa: F821
        return self.key == signal.key or (
            self.region == signal.region and self.function == signal.function
        )


class ParametricCatalog:
    """A small, ordered catalog of functional neuron specs.

    The catalog is intentionally compact: typically < 100 entries
    even for very rich brains, because each function is a parametric
    description rather than a per-neuron instance.
    """

    def __init__(self) -> None:
        self._specs: Dict[str, FunctionSpec] = {}
        self._by_region: Dict[str, List[str]] = {}
        self._order: List[str] = []

    def add(self, spec: FunctionSpec) -> None:
        if spec.key in self._specs:
            return  # idempotent
        self._specs[spec.key] = spec
        self._by_region.setdefault(spec.region, []).append(spec.key)
        self._order.append(spec.key)

    def get(self, key: str) -> Optional[FunctionSpec]:
        return self._specs.get(key)

    def find(
        self,
        region: Optional[str] = None,
        function: Optional[str] = None,
    ) -> List[FunctionSpec]:
        out: List[FunctionSpec] = []
        keys = self._by_region.get(region, []) if region else self._order
        for k in keys:
            spec = self._specs[k]
            if function is None or spec.function == function:
                out.append(spec)
        return out

    def find_one(
        self,
        region: str,
        function: str,
    ) -> Optional[FunctionSpec]:
        for k in self._by_region.get(region, []):
            spec = self._specs[k]
            if spec.function == function:
                return spec
        return None

    def all_keys(self) -> List[str]:
        return list(self._order)

    def count(self) -> int:
        return len(self._specs)

    def clear(self) -> None:
        self._specs.clear()
        self._by_region.clear()
        self._order.clear()


# ----------------------------------------------------------------------
# Default catalog — covers all major brain regions with parametric specs
# ----------------------------------------------------------------------

def default_catalog() -> ParametricCatalog:
    """Build a default parametric catalog with all major brain regions."""
    cat = ParametricCatalog()
    # SENSORY
    cat.add(FunctionSpec(
        key="sensory.visual",
        region="sensory",
        function="visual",
        cell_type="sensory_neuron",
        threshold=0.3, plasticity_rate=0.04, tau_ms=8.0,
        math_function="LIF + lateral_inhibition",
    ))
    cat.add(FunctionSpec(
        key="sensory.auditory",
        region="sensory",
        function="auditory",
        cell_type="auditory_neuron",
        threshold=0.35, plasticity_rate=0.05, tau_ms=10.0,
        math_function="LIF + frequency_tuning",
    ))
    cat.add(FunctionSpec(
        key="sensory.somatosensory",
        region="sensory",
        function="somatosensory",
        cell_type="sensory_neuron",
        threshold=0.4, plasticity_rate=0.04, tau_ms=8.0,
        math_function="LIF + receptive_field",
    ))
    # HIPPOCAMPUS / MEMORY
    cat.add(FunctionSpec(
        key="hippocampus.encoding",
        region="hippocampus",
        function="encoding",
        cell_type="hippocampal_neuron",
        threshold=0.45, plasticity_rate=0.08, tau_ms=15.0,
        math_function="LIF + STDP + pattern_separation",
    ))
    cat.add(FunctionSpec(
        key="hippocampus.retrieval",
        region="hippocampus",
        function="retrieval",
        cell_type="hippocampal_neuron",
        threshold=0.4, plasticity_rate=0.06, tau_ms=12.0,
        math_function="LIF + pattern_completion",
    ))
    # PREFRONTAL / EXECUTIVE
    cat.add(FunctionSpec(
        key="prefrontal.working_memory",
        region="prefrontal",
        function="working_memory",
        cell_type="prefrontal_neuron",
        threshold=0.5, plasticity_rate=0.05, tau_ms=20.0,
        math_function="LIF + persistent_activity",
    ))
    cat.add(FunctionSpec(
        key="prefrontal.decision",
        region="prefrontal",
        function="decision",
        cell_type="prefrontal_neuron",
        threshold=0.5, plasticity_rate=0.05, tau_ms=15.0,
        math_function="LIF + accumulation_to_bound",
    ))
    # LANGUAGE
    cat.add(FunctionSpec(
        key="language.comprehension",
        region="language",
        function="comprehension",
        cell_type="wernicke_neuron",
        threshold=0.45, plasticity_rate=0.08, tau_ms=12.0,
        math_function="LIF + sequence_buffer",
    ))
    cat.add(FunctionSpec(
        key="language.production",
        region="language",
        function="production",
        cell_type="broca_neuron",
        threshold=0.5, plasticity_rate=0.07, tau_ms=12.0,
        math_function="LIF + motor_sequence",
    ))
    cat.add(FunctionSpec(
        key="language.semantic_grounding",
        region="language",
        function="semantic_grounding",
        cell_type="semantic_pointer_neuron",
        threshold=0.3, plasticity_rate=0.1, tau_ms=10.0,
        math_function="LIF + HRR_binding",
    ))
    # MOTOR
    cat.add(FunctionSpec(
        key="motor.execution",
        region="motor",
        function="execution",
        cell_type="motor_neuron",
        threshold=0.45, plasticity_rate=0.04, tau_ms=8.0,
        math_function="LIF + population_vector",
    ))
    # CEREBELLAR
    cat.add(FunctionSpec(
        key="cerebellar.error_correction",
        region="cerebellar",
        function="error_correction",
        cell_type="cerebellar_neuron",
        threshold=0.5, plasticity_rate=0.05, tau_ms=10.0,
        math_function="LIF + LTD_correction",
    ))
    # LIMBIC
    cat.add(FunctionSpec(
        key="limbic.valence",
        region="limbic",
        function="valence",
        cell_type="limbic_neuron",
        threshold=0.5, plasticity_rate=0.06, tau_ms=15.0,
        math_function="LIF + dopamine_modulation",
    ))
    # DEFAULT MODE
    cat.add(FunctionSpec(
        key="default_mode.consolidation",
        region="default_mode",
        function="consolidation",
        cell_type="default_mode_neuron",
        threshold=0.4, plasticity_rate=0.07, tau_ms=18.0,
        math_function="LIF + replay_during_offline",
    ))
    # BRAINSTEM
    cat.add(FunctionSpec(
        key="brainstem.homeostasis",
        region="brainstem",
        function="homeostasis",
        cell_type="brainstem_neuron",
        threshold=0.3, plasticity_rate=0.02, tau_ms=5.0,
        math_function="LIF + setpoint_control",
    ))
    # GENERIC (fallback)
    cat.add(FunctionSpec(
        key="generic.processing",
        region="generic",
        function="processing",
        cell_type="generic_neuron",
        threshold=0.5, plasticity_rate=0.05, tau_ms=10.0,
        math_function="LIF (default)",
    ))
    return cat
