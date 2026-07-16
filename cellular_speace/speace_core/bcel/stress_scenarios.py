"""Operational stress-test scenarios for functional biological constraints.

Each scenario maps a functional constraint to a concrete circuit manipulation
and a stability metric. The harness runs the orchestrator twice:

- baseline: constraint applied normally
- perturbed: constraint relaxed or removed

If relaxing the constraint increases instability, the constraint is validated.
"""

import asyncio
import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from speace_core.bcel.models import FunctionalConstraint


@dataclass
class StabilityMetrics:
    """Simple stability fingerprint of a circuit run."""

    coherence_mean: float
    coherence_variance: float
    energy_mean: float
    energy_variance: float
    max_activation: float
    total_spikes: int


ScenarioFn = Callable[["FunctionalConstraint", "CircuitProxy"], None]


class CircuitProxy:
    """Minimal proxy to read/write circuit parameters for stress testing.

    This avoids coupling the BCEL directly to the full orchestrator internals.
    """

    def __init__(self, orchestrator: Any) -> None:
        self.orch = orchestrator
        self.circuit = getattr(orchestrator, "circuit", None)

    @property
    def neurons(self) -> List[Any]:
        if self.circuit is None:
            return []
        return (
            getattr(self.circuit, "input_neurons", [])
            + getattr(self.circuit, "hidden_neurons", [])
            + getattr(self.circuit, "output_neurons", [])
        )

    @property
    def synapses(self) -> List[Any]:
        if self.circuit is None:
            return []
        return getattr(self.circuit, "synapses", [])

    def set_refractory_period(self, value: int) -> None:
        for n in self.neurons:
            if hasattr(n, "refractory_period"):
                n.refractory_period = value

    def set_trust(self, value: float) -> None:
        for s in self.synapses:
            if hasattr(s, "trust"):
                s.trust = max(0.0, min(1.0, value))

    def set_weight(self, value: float) -> None:
        for s in self.synapses:
            if hasattr(s, "weight"):
                s.weight = max(0.0, min(1.0, value))

    def inject(self, pattern: List[float]) -> None:
        if hasattr(self.orch, "inject"):
            self.orch.inject(pattern)


async def _run_ticks(orch: Any, n: int) -> None:
    """Run ticks in a way compatible with sync and async orchestrators."""
    if hasattr(orch, "run_ticks"):
        # run_ticks is async
        await orch.run_ticks(n)
    else:
        for _ in range(n):
            tick_fn = getattr(orch, "_tick", None)
            if tick_fn is None:
                break
            result = tick_fn()
            if asyncio.isawaitable(result):
                await result


def _collect_metrics(orch: Any) -> StabilityMetrics:
    """Collect stability metrics from the orchestrator metrics log."""
    log = getattr(orch, "metrics_log", [])
    if not log:
        # Try to read current metrics directly
        latest = getattr(orch, "latest_metrics", None) or getattr(orch, "_last_metrics", None)
        if latest is not None:
            log = [latest]

    coherence = [getattr(m, "coherence_phi", 0.5) for m in log]
    energy = [getattr(m, "mean_energy", 0.5) for m in log]

    # If the orchestrator records per-tick spike counts / peak activations,
    # aggregate them for a much more sensitive signal than a single snapshot.
    total_spikes = 0
    max_activation = 0.0
    if log and hasattr(log[0], "spike_count"):
        total_spikes = sum(getattr(m, "spike_count", 0) for m in log)
        max_activation = max((getattr(m, "max_activation", 0.0) for m in log), default=0.0)

    # Fallback: read the live circuit state when per-tick history is unavailable.
    circuit = getattr(orch, "circuit", None)
    if circuit is not None and (total_spikes == 0 or max_activation == 0.0):
        neurons = (
            getattr(circuit, "input_neurons", [])
            + getattr(circuit, "hidden_neurons", [])
            + getattr(circuit, "output_neurons", [])
        )
        activations: List[float] = []
        for n in neurons:
            act = getattr(n, "activation", 0.0)
            activations.append(act)
            if getattr(n, "fired", False) or act > 0.9:
                total_spikes += 1
        if activations:
            max_activation = max(max_activation, max(activations))

    def mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def variance(values: List[float]) -> float:
        if len(values) < 2:
            return 0.0
        m = mean(values)
        return sum((x - m) ** 2 for x in values) / len(values)

    return StabilityMetrics(
        coherence_mean=mean(coherence),
        coherence_variance=variance(coherence),
        energy_mean=mean(energy),
        energy_variance=variance(energy),
        max_activation=max_activation,
        total_spikes=total_spikes,
    )


def _default_baseline() -> ScenarioFn:
    def apply(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        # No perturbation: leave circuit as built.
        pass
    return apply


def _rate_limiter_scenario() -> tuple[ScenarioFn, ScenarioFn]:
    """Refractory period: removing it should let firing rates explode."""

    def baseline(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        params = constraint.parameters
        tau = params.get("min_inter_spike_ticks", 2)
        proxy.set_refractory_period(int(tau))

    def perturbed(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        proxy.set_refractory_period(0)

    return baseline, perturbed


def _synaptic_gain_scenario() -> tuple[ScenarioFn, ScenarioFn]:
    """Short-term depression / gain control: high trust removes attenuation."""

    def baseline(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        # Leave default weights and trust as built.
        pass

    def perturbed(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        # Remove attenuation by maximizing trust and setting weights high.
        proxy.set_trust(1.0)
        proxy.set_weight(0.95)

    return baseline, perturbed


def _delay_lowpass_scenario() -> tuple[ScenarioFn, ScenarioFn]:
    """Low-pass filter delay: high-frequency input without filtering."""

    def baseline(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        # Baseline keeps whatever smoothing the circuit already has.
        pass

    def perturbed(constraint: FunctionalConstraint, proxy: CircuitProxy) -> None:
        # Amplify gain and trust so any high-frequency input propagates fast.
        proxy.set_trust(1.0)
        proxy.set_weight(0.95)

    return baseline, perturbed


class StressScenarioRegistry:
    """Maps functional-constraint names to baseline/perturbation scenario pairs."""

    def __init__(self) -> None:
        self._scenarios: Dict[str, tuple[ScenarioFn, ScenarioFn]] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register("rate_limiter", *_rate_limiter_scenario())
        self.register("short_term_depression", *_synaptic_gain_scenario())
        self.register("synaptic_delay_lowpass", *_delay_lowpass_scenario())
        self.register("delay_as_lowpass_filter", *_delay_lowpass_scenario())

    def register(
        self,
        name: str,
        baseline: ScenarioFn,
        perturbed: ScenarioFn,
    ) -> None:
        self._scenarios[name] = (baseline, perturbed)

    def get(self, name: str) -> tuple[ScenarioFn, ScenarioFn] | None:
        return self._scenarios.get(name)

    def list(self) -> List[str]:
        return sorted(self._scenarios.keys())
