"""T172 — Tests for the Information Value triad.

Covers:
- PerceivedEntropyModule: aggregation, missing signals, derivatives.
- InformationalValueFunction: inverted-U sweet spot, regime classification.
- ExplorationPolicy: regime selection, action mapping, governance boundaries.
- End-to-end loop: signals → H → V → π (proposal only).
"""

import pytest

from speace_core.cellular_brain.information_value import (
    ExplorationPolicy,
    InformationalValueFunction,
    PerceivedEntropyModule,
)
from speace_core.cellular_brain.information_value.exploration_policy import (
    ProposalKind,
)
from speace_core.cellular_brain.information_value.value_function import (
    ValueBreakdown,
)


# ---------------------------------------------------------------------- #
# PerceivedEntropyModule
# ---------------------------------------------------------------------- #


class TestPerceivedEntropyModule:
    def test_empty_signals_yields_zero(self):
        m = PerceivedEntropyModule()
        snap = m.observe({})
        assert snap.H_local == 0.0
        # All components are 0, no missing ones should error
        assert all(v == 0.0 for v in snap.components.values())

    def test_full_signals_aggregate(self):
        m = PerceivedEntropyModule()
        snap = m.observe(
            {
                "prediction_error": 0.5,
                "novelty": 0.5,
                "informational_entropy": 0.5,
                "signal_diversity": 0.5,
                "surprise": 0.5,
            }
        )
        # Weighted average of 0.5 with default weights = 0.5
        assert snap.H_local == pytest.approx(0.5, abs=1e-6)

    def test_clipping_outside_unit_interval(self):
        m = PerceivedEntropyModule()
        snap = m.observe(
            {
                "prediction_error": 2.0,
                "novelty": -0.5,
                "informational_entropy": 0.4,
                "signal_diversity": 0.6,
                "surprise": 0.3,
            }
        )
        # Out-of-range values are clipped
        assert snap.components["prediction_error"] == 1.0
        assert snap.components["novelty"] == 0.0

    def test_history_and_derivative(self):
        m = PerceivedEntropyModule()
        m.observe({"prediction_error": 0.1, "novelty": 0.1,
                   "informational_entropy": 0.1, "signal_diversity": 0.1,
                   "surprise": 0.1})
        m.observe({"prediction_error": 0.9, "novelty": 0.9,
                   "informational_entropy": 0.9, "signal_diversity": 0.9,
                   "surprise": 0.9})
        assert m.derivative() > 0.0
        assert m.mean() == pytest.approx(0.5, abs=1e-6)

    def test_shannon_normalised(self):
        v = PerceivedEntropyModule.shannon_normalised([0.0, 0.0, 0.0, 0.0])
        assert v == 0.0
        v = PerceivedEntropyModule.shannon_normalised([1.0, 1.0, 1.0, 1.0])
        assert 0.0 <= v <= 1.0


# ---------------------------------------------------------------------- #
# InformationalValueFunction
# ---------------------------------------------------------------------- #


class TestInformationalValueFunction:
    def test_sweet_spot_is_maximum(self):
        vf = InformationalValueFunction()
        v_ss, bd_ss = vf.evaluate(0.5, 0.5, 0.5)
        v_edge, bd_edge = vf.evaluate(0.0, 0.0, 0.0)
        assert v_ss > v_edge
        # Normalised sweet spot should be in the sweet_spot regime
        assert bd_ss.regime == "sweet_spot"

    def test_pure_order_low_value(self):
        vf = InformationalValueFunction()
        v, bd = vf.evaluate(1.0, 1.0, 1.0)
        # Far from sweet spot → V near 0 → normalised negative
        assert v < 0.0
        assert bd.regime in ("ordered", "suboptimal", "anti_preferred")

    def test_pure_chaos_low_value(self):
        vf = InformationalValueFunction()
        v, bd = vf.evaluate(0.0, 0.0, 0.0)
        # Far edge ⇒ V ≈ 0
        assert v < 0.0
        assert bd.regime in ("chaotic", "anti_preferred", "suboptimal")

    def test_breakdown_is_complete(self):
        vf = InformationalValueFunction()
        _, bd = vf.evaluate(0.6, 0.4, 0.5)
        assert isinstance(bd, ValueBreakdown)
        d = bd.to_dict()
        for k in ("novelty", "predictability", "compressibility",
                  "V_raw", "V_normalised", "regime"):
            assert k in d

    def test_invalid_sigma(self):
        with pytest.raises(ValueError):
            InformationalValueFunction(sigma=0.0)

    def test_functional_law_dict(self):
        vf = InformationalValueFunction()
        law = vf.as_functional_law()
        assert law["name"] == "inverted_u_information_value"
        assert law["invariant"] == "generative_variability_preservation"
        assert "parameters" in law


# ---------------------------------------------------------------------- #
# ExplorationPolicy
# ---------------------------------------------------------------------- #


class TestExplorationPolicy:
    def test_sweet_spot_yields_observe(self):
        p = ExplorationPolicy()
        v = 0.3  # inside sweet band
        prop = p.propose({"energy": 0.8, "coherence": 0.8, "novelty": 0.5}, v)
        assert prop.kind == ProposalKind.OBSERVE
        assert prop.regime == "sweet_spot"

    def test_starvation_yields_actuate(self):
        p = ExplorationPolicy()
        v = -0.5  # below starvation
        prop = p.propose({"energy": 0.8, "coherence": 0.8, "novelty": 0.2}, v)
        assert prop.kind == ProposalKind.ACTUATE
        assert prop.regime == "starvation"

    def test_satiation_yields_gc(self):
        p = ExplorationPolicy()
        v = 0.9  # well above satiation threshold (0.4)
        prop = p.propose({"energy": 0.8, "coherence": 0.8, "novelty": 0.9}, v)
        assert prop.kind == ProposalKind.GARBAGE_COLLECT
        assert prop.regime == "satiation"

    def test_energy_crisis_yields_sleep(self):
        p = ExplorationPolicy()
        v = 0.3
        prop = p.propose({"energy": 0.1, "coherence": 0.8, "novelty": 0.5}, v)
        assert prop.kind == ProposalKind.REQUEST_SLEEP
        assert prop.regime == "energy_crisis"

    def test_coherence_crisis_yields_checkpoint(self):
        p = ExplorationPolicy()
        v = 0.3
        prop = p.propose({"energy": 0.8, "coherence": 0.1, "novelty": 0.5}, v)
        assert prop.kind == ProposalKind.CHECKPOINT
        assert prop.regime == "coherence_crisis"

    def test_policy_does_not_execute_actions(self):
        # Critical safety property: ExplorationPolicy.propose must never
        # trigger any direct mutation. It only returns a proposal object.
        p = ExplorationPolicy()
        prop = p.propose({"energy": 0.8, "coherence": 0.8, "novelty": 0.5}, 0.3)
        d = prop.to_dict()
        assert d["kind"] in {k.value for k in ProposalKind}
        # No 'execute' / 'apply' verb appears in any field
        for k, v in d.items():
            if isinstance(v, str):
                assert v not in ("execute", "apply", "run")
        assert "execute_action" not in d
        assert "apply_mutation" not in d

    def test_invalid_weights(self):
        with pytest.raises(ValueError):
            ExplorationPolicy(novelty_weight=0, energy_weight=0,
                              coherence_weight=0, value_weight=0)

    def test_summary(self):
        p = ExplorationPolicy()
        p.propose({"energy": 0.8, "coherence": 0.8, "novelty": 0.5}, 0.3)
        s = p.summary()
        assert s["n_proposals"] == 1
        assert "sweet_spot" in s["regime_counts"]


# ---------------------------------------------------------------------- #
# End-to-end
# ---------------------------------------------------------------------- #


class TestEndToEnd:
    def test_h_to_v_to_pi_loop(self):
        ent = PerceivedEntropyModule()
        vf = InformationalValueFunction()
        pol = ExplorationPolicy()

        signals = {
            "prediction_error": 0.45,
            "novelty": 0.6,
            "informational_entropy": 0.5,
            "signal_diversity": 0.6,
            "surprise": 0.4,
        }
        state = {
            "energy": 0.7,
            "coherence": 0.6,
            "novelty": 0.6,
        }

        snap = ent.observe(signals)
        assert 0.0 <= snap.H_local <= 1.0
        novelty = signals["novelty"]
        predictability = 1.0 - signals["prediction_error"]
        compressibility = 1.0 - signals["informational_entropy"]
        v, bd = vf.evaluate(novelty, predictability, compressibility)
        assert -1.0 <= v <= 1.0
        prop = pol.propose(state, v)
        assert prop.V == pytest.approx(v, abs=1e-6)
        # Mapping value.regime → policy.regime: the policy uses a
        # coarser label set; we assert both are valid regimes.
        assert prop.regime in (
            "energy_crisis", "coherence_crisis", "starvation",
            "sweet_spot", "satiation", "suboptimal",
        )
        assert bd.regime in (
            "ordered", "sweet_spot", "chaotic", "saturated",
            "anti_preferred", "suboptimal",
        )
