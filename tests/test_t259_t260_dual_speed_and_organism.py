"""Tests for T259 Adaptive Dual-Speed NL Grounding & T260 Unified 7-Axis Organism Profile."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.bridge.dual_speed import DualSpeedCognitiveLoop
from q_speace.bridge.grounding import SymbolicGroundingAdapter, SymbolRegistry
from q_speace.bridge.simulated_sensor import run_coro_isolated
from q_speace.bridge.typed_nl_pipeline import _strip_echoed_gloss
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.edd_cvt.ilf import InformationalLogicalField
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.spiking.encoder import dynamic_spikes
from q_speace.spiking_brain.cortex import SpikingBrainCortex
from q_speace.spiking_brain.truth_engine import TruthEngine
from q_speace.spiking_brain.types import ThinkResult
from q_speace.vertical_slice.t251_benchmark import build_agi_capability_profile
from q_speace.vertical_slice.t259_dual_speed_nl_benchmark import run_t259_dual_speed_nl_benchmark


class _ScriptedNLBackend:
    """Deterministic backend returning scripted Fast vs Slow responses."""

    def __init__(self, fast_reply: str, slow_reply: str, *, fast_conf: float = 0.88) -> None:
        self.fast_reply = fast_reply
        self.slow_reply = slow_reply
        self.fast_conf = fast_conf
        self.calls: list[str] = []

    async def load(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 80,
        history: object = None,
    ) -> ThinkResult:
        _ = (coherence_phi, history)
        is_slow = "--- EXTRACTOR ---" in prompt
        self.calls.append("slow" if is_slow else "fast")
        txt = self.slow_reply if is_slow else self.fast_reply
        conf = 0.91 if is_slow else self.fast_conf
        vec = np.array([0.25, 0.25, 0.25, 0.25], dtype=float)
        return ThinkResult(
            text=txt,
            confidence=conf,
            belief=vec,
            spikes=dynamic_spikes(vec),
            plasticity=np.array([0.1, 0.1, 0.1, 0.1], dtype=float),
            n_tokens=min(n_tokens, max(8, len(txt) // 4)),
            latency_s=0.001,
            metadata={"backend": "scripted-test"},
        )


def test_t259_t260_bcel_catalog_entries() -> None:
    cat = BCELCatalog()
    assert cat.is_functional(
        "Surprise- and cue-gated dual-speed natural-language belief revision (T259)"
    )
    assert cat.is_functional(
        "Multi-axis non-compensable cognitive and systemic organism radar (T260)"
    )
    acc = cat.get("Single scalar Organism IQ or Consciousness Quotient headline index (T260)")
    assert acc.classification == "accidental"


def test_t259_t260_mcp_surface_invariance_and_zero_eval() -> None:
    assert len(HTTP_TOOL_SCOPES) == 12
    assert len(TOOL_REGISTRY) == 14

    repo_root = Path(__file__).resolve().parents[1]
    targets = [
        repo_root / "q_speace" / "bridge" / "dual_speed.py",
        repo_root / "q_speace" / "bridge" / "typed_nl_pipeline.py",
        repo_root / "q_speace" / "vertical_slice" / "t259_dual_speed_nl_benchmark.py",
        repo_root / "q_speace" / "vertical_slice" / "t251_benchmark.py",
    ]
    for path in targets:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}, f"Forbidden {node.func.id} in {path}"


def test_strip_echoed_gloss_canonicalizer() -> None:
    assert (
        _strip_echoed_gloss("- channel_intact(b52_n1): portello primario integro su b52_n1")
        == "channel_intact(b52_n1)"
    )
    assert _strip_echoed_gloss("doppler_alert(b50_n0)") == "doppler_alert(b50_n0)"


def test_dual_speed_nl_fast_path_and_fail_closed_escalation() -> None:
    reg = SymbolRegistry(
        predicates=[
            "pressure_delta(b52_n0)",
            "channel_intact(b52_n1)",
            "terminal_fault(b52_n1)",
            "pressure_delta(b52_d0)",
        ],
        causal_nodes=["b52_n0", "b52_n1"],
        actions=(),
        mutex_pairs=(("terminal_fault(b52_n1)", "channel_intact(b52_n1)"),),
    )
    glosses = {
        "pressure_delta(b52_n0)": "differenziale di pressione attivo su b52_n0",
        "channel_intact(b52_n1)": "portello primario integro su b52_n1",
        "terminal_fault(b52_n1)": "guasto terminale irreversibile su b52_n1",
        "pressure_delta(b52_d0)": "sensore test su boccaporto b52_d0 isolato (distrattore)",
    }

    # 1. Affirmative routine report with echoed ': gloss' stays on fast path
    b_fast = _ScriptedNLBackend(
        fast_reply=json.dumps(
            {
                "observed_facts": [
                    "pressure_delta(b52_n0): differenziale di pressione attivo su b52_n0",
                    "channel_intact(b52_n1): portello primario integro su b52_n1",
                ]
            }
        ),
        slow_reply="",
    )
    loop1 = DualSpeedCognitiveLoop(
        cortex=SpikingBrainCortex(
            backend=b_fast,  # type: ignore[arg-type]
            ilf=InformationalLogicalField(
                coherence_phi=0.85, q_star_ema=0.85, coherence_phi_ema=0.85
            ),
            truth_engine=TruthEngine(),
        ),
        grounding=SymbolicGroundingAdapter(reg, tau_ground=0.70),
        tau_conf=0.55,
    )
    rec1 = run_coro_isolated(
        lambda: loop1.step_nl_belief_revision(
            operator_message=(
                "Dispaccio regolare: differenziale di pressione attivo su b52_n0 "
                "e portello primario su b52_n1 integro (b52_d0 chiuso per test)."
            ),
            prior_state=frozenset(),
            predicate_glosses=glosses,
        )
    )
    assert rec1.tier_selected == "fast"
    assert not rec1.escalated_after_fast
    assert rec1.revised_belief_state == frozenset(
        {"pressure_delta(b52_n0)", "channel_intact(b52_n1)"}
    )
    assert b_fast.calls == ["fast"]

    # 2. Empty/ambiguous fast response escalates fail-closed to slow path
    b_esc = _ScriptedNLBackend(
        fast_reply='{"observed_facts": []}',
        slow_reply=(
            '--- EXTRACTOR ---\n{"observed_facts": ["pressure_delta(b52_n0)", '
            '"channel_intact(b52_n1)"], "retracted_facts": []}\n'
            '--- CRITIC ---\n{"observed_facts": ["pressure_delta(b52_n0)", '
            '"channel_intact(b52_n1)"], "retracted_facts": []}'
        ),
    )
    loop2 = DualSpeedCognitiveLoop(
        cortex=SpikingBrainCortex(
            backend=b_esc,  # type: ignore[arg-type]
            ilf=InformationalLogicalField(
                coherence_phi=0.85, q_star_ema=0.85, coherence_phi_ema=0.85
            ),
            truth_engine=TruthEngine(),
        ),
        grounding=SymbolicGroundingAdapter(reg, tau_ground=0.70),
        tau_conf=0.55,
    )
    rec2 = run_coro_isolated(
        lambda: loop2.step_nl_belief_revision(
            operator_message=(
                "Dispaccio regolare: differenziale di pressione attivo su b52_n0 "
                "e portello primario su b52_n1 integro."
            ),
            prior_state=frozenset(),
            predicate_glosses=glosses,
        )
    )
    assert rec2.tier_selected == "slow"
    assert rec2.escalated_after_fast is True
    assert "fast_pass_incomplete_or_ambiguous" in rec2.escalation_reasons
    assert b_esc.calls == ["fast", "slow"]

    # 3. Mid-episode correction pre-routes directly to slow path (mutex retracts channel_intact)
    b_rev = _ScriptedNLBackend(
        fast_reply="",
        slow_reply=(
            '--- EXTRACTOR ---\n{"observed_facts": ["terminal_fault(b52_n1)"], "retracted_facts": []}\n'
            '--- CRITIC ---\n{"observed_facts": ["terminal_fault(b52_n1)"], "retracted_facts": []}'
        ),
    )
    loop3 = DualSpeedCognitiveLoop(
        cortex=SpikingBrainCortex(
            backend=b_rev,  # type: ignore[arg-type]
            ilf=InformationalLogicalField(
                coherence_phi=0.85, q_star_ema=0.85, coherence_phi_ema=0.85
            ),
            truth_engine=TruthEngine(),
        ),
        grounding=SymbolicGroundingAdapter(reg, tau_ground=0.70),
        tau_conf=0.55,
    )
    rec3 = run_coro_isolated(
        lambda: loop3.step_nl_belief_revision(
            operator_message=(
                "Rettifica urgente: il portello primario su b52_n1 non è più integro; "
                "è in guasto terminale irreversibile su b52_n1."
            ),
            prior_state=frozenset({"channel_intact(b52_n1)"}),
            predicate_glosses=glosses,
        )
    )
    assert rec3.tier_selected == "slow"
    assert rec3.escalated_after_fast is False
    assert "non_monotonic_linguistic_cue" in rec3.escalation_reasons
    assert "channel_intact(b52_n1)" in rec3.effective_retracted_facts
    assert "channel_intact(b52_n1)" not in rec3.revised_belief_state
    assert b_rev.calls == ["slow"]


def test_t259_offline_benchmark_passes_all_gates() -> None:
    rep = run_t259_dual_speed_nl_benchmark(live_brain=False, n_resamples=200)
    assert rep["all_gates_passed"] is True
    adap = rep["conditions"]["ADAPTIVE_DUAL_SPEED_T259"]
    assert adap["safe_end_to_end_success_rate"] == 1.0
    assert adap["total_invalid_actions"] == 0
    assert adap["fast_turns"] == 9
    assert adap["slow_turns"] == 9
    assert rep["comparisons"]["token_reduction_adaptive_vs_always_slow"] >= 0.25


def test_t260_backward_compatible_v1_and_unified_7_axis_v2(tmp_path: Path) -> None:
    # 1. Default remains 5-axis agi_profile.v1
    prof_v1 = build_agi_capability_profile(n_resamples=200)
    assert prof_v1["schema_version"] == "agi_profile.v1"
    assert prof_v1["active_axes_summary"]["total_axes"] == 5
    assert prof_v1["overall_verdict"] == "PASS_ALL_5_AXES"
    assert len(prof_v1["axes"]) == 5

    # 2. Full organism emits 7-axis agi_organism_profile.v2 (deterministic fallback when missing file)
    prof_v2 = build_agi_capability_profile(
        n_resamples=200,
        include_systemic_and_nl_axes=True,
        t259_artifact_path=tmp_path / "absent_t259.json",
    )
    assert prof_v2["schema_version"] == "agi_organism_profile.v2"
    assert prof_v2["active_axes_summary"]["total_axes"] == 7
    assert prof_v2["active_axes_summary"]["active_count"] == 7
    assert prof_v2["anti_goodhart_invariants"]["headline_single_iq_suppressed"] is True
    assert prof_v2["overall_verdict"] == "PASS_ALL_7_ORGANISM_AXES"
    assert prof_v2["axes"]["6_linguistic_belief_revision_and_dual_speed"]["gate_passed"] is True
    assert prof_v2["axes"]["7_federated_glial_gossip_resilience"]["gate_passed"] is True

    # 3. CLI smoke test for organism-profile
    runner = CliRunner()
    out_file = tmp_path / "org_v2.json"
    res = runner.invoke(
        app, ["eval", "organism-profile", "--resamples", "200", "-o", str(out_file)]
    )
    assert res.exit_code == 0, res.output
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved["overall_verdict"] == "PASS_ALL_7_ORGANISM_AXES"
