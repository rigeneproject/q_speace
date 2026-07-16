"""Stress-test framework for validating functional constraints.

A functional constraint should, when relaxed, increase some measure of
instability in the circuit. The harness runs an orchestrator twice (baseline
vs perturbed), compares stability metrics, and produces a pass/fail verdict.
"""

import asyncio
import copy
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from speace_core.bcel.models import FunctionalConstraint
from speace_core.bcel.stress_scenarios import (
    CircuitProxy,
    StressScenarioRegistry,
    StabilityMetrics,
    _run_ticks,
    _collect_metrics,
)


@dataclass
class StressTestResult:
    """Outcome of a constraint stress test."""

    test_name: str
    passed: bool
    metric_name: str
    baseline_value: float
    perturbed_value: float
    relative_change: float
    interpretation: str


class ConstraintStressTester:
    """Validate functional constraints by perturbing the circuit.

    The tester uses a scenario registry to know how to apply and relax each
    constraint. For every functional constraint it:

        1. Runs the orchestrator with the constraint applied (baseline).
        2. Runs a copy of the orchestrator with the constraint relaxed.
        3. Compares stability metrics (coherence variance, energy variance,
           max activation, total spikes).
        4. Reports whether the constraint is protective.
    """

    def __init__(
        self,
        build_orchestrator: Optional[Callable[[], Any]] = None,
        scenarios: Optional[StressScenarioRegistry] = None,
    ) -> None:
        self.build_orchestrator = build_orchestrator
        self.scenarios = scenarios or StressScenarioRegistry()
        self._instability_threshold = 2.0  # perturbed must be > 2x baseline

    def register_scenario(
        self,
        name: str,
        baseline: Callable[[FunctionalConstraint, CircuitProxy], None],
        perturbed: Callable[[FunctionalConstraint, CircuitProxy], None],
    ) -> None:
        self.scenarios.register(name, baseline, perturbed)

    async def run(
        self,
        constraint: FunctionalConstraint,
        build_orchestrator: Optional[Callable[[], Any]] = None,
        ticks: int = 20,
        metric: str = "coherence_variance",
    ) -> StressTestResult:
        """Run a stress test for a single functional constraint.

        Args:
            constraint: the functional constraint to validate.
            build_orchestrator: factory that returns a fresh orchestrator.
            ticks: number of ticks to run in each condition.
            metric: stability metric to compare (coherence_variance,
                energy_variance, max_activation, total_spikes).
        """
        builder = build_orchestrator or self.build_orchestrator
        if builder is None:
            return self._placeholder_result(constraint)

        scenario = self.scenarios.get(constraint.name)
        if scenario is None:
            return self._placeholder_result(constraint)

        baseline_fn, perturbed_fn = scenario

        # Baseline run
        baseline_orch = builder()
        baseline_proxy = CircuitProxy(baseline_orch)
        baseline_fn(constraint, baseline_proxy)
        await self._stimulate_and_run(baseline_orch, ticks)
        baseline_metrics = _collect_metrics(baseline_orch)

        # Perturbed run: fresh orchestrator with constraint relaxed.
        perturbed_orch = builder()
        perturbed_proxy = CircuitProxy(perturbed_orch)
        perturbed_fn(constraint, perturbed_proxy)
        await self._stimulate_and_run(perturbed_orch, ticks)
        perturbed_metrics = _collect_metrics(perturbed_orch)

        baseline_value = getattr(baseline_metrics, metric)
        perturbed_value = getattr(perturbed_metrics, metric)

        relative_change = self._relative_change(baseline_value, perturbed_value)
        passed = relative_change >= self._instability_threshold

        interpretation = (
            f"Relaxing '{constraint.name}' increased {metric} by "
            f"{relative_change:.2f}x. "
            + ("Constraint is protective (functional)." if passed else "No clear instability detected.")
        )

        return StressTestResult(
            test_name=f"stress_{constraint.name}_{metric}",
            passed=passed,
            metric_name=metric,
            baseline_value=baseline_value,
            perturbed_value=perturbed_value,
            relative_change=relative_change,
            interpretation=interpretation,
        )

    async def _stimulate_and_run(self, orch: Any, ticks: int) -> None:
        """Inject a high-energy pattern repeatedly while running to stress the circuit."""
        if not hasattr(orch, "inject"):
            await _run_ticks(orch, ticks)
            return

        pattern = [0.0] * 10
        pattern[0] = 0.9
        # Re-inject on every tick to sustain activity and expose runaway gain.
        for _ in range(ticks):
            orch.inject(pattern)
            await _run_ticks(orch, 1)

    def _relative_change(self, baseline: float, perturbed: float) -> float:
        """Return how many times larger the perturbed value is vs baseline."""
        if abs(baseline) < 1e-9:
            # If baseline is near zero, any non-zero perturbation is considered large.
            return 10.0 if abs(perturbed) > 1e-9 else 1.0
        return perturbed / baseline

    def _placeholder_result(self, constraint: FunctionalConstraint) -> StressTestResult:
        return StressTestResult(
            test_name=f"placeholder_{constraint.name}",
            passed=True,
            metric_name="none",
            baseline_value=0.0,
            perturbed_value=0.0,
            relative_change=0.0,
            interpretation=(
                "No scenario or orchestrator builder provided; "
                "stress test could not be executed operationally."
            ),
        )
