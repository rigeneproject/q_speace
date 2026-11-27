"""Q-SPEACE command-line interface (task T16).

Groups:
  - ``qspace quantum ...`` — quantum experiments and tools
  - ``qspace sia ...`` — self-improvement cortex controls
  - ``qspace brain ...`` — SpikingBrain satellite (T205)
  - ``qspace economy ...`` — q_speace_economy primitives (T6.*)
  - ``qspace eval ...`` — vertical-slice policy evaluation (T208/T231)
  - ``qspace singularity ...`` — phase-transition & genetic-epigenetic framework (T234)
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from pathlib import Path
from typing import Annotated, Any

import typer

from .bcel import BCELCatalog
from .earth_feed import EarthFeed
from .fractal_qca_cascade import experiment_cross_scale, qi_bridge_cqasm
from .genome import QuantumGeneSet
from .orchestrator import QuantumOrchestrator
from .quantum.backends import to_cqasm
from .schumann import run_schumann, schumann_circuit
from .self_improvement_cortex import SelfImprovementCortex
from .spiking_brain import CortexReport, SpikingBrainCortex, ThinkResult

_VALID_ECONOMY_SCHEMAS: tuple[str, ...] = ("j_c", "v", "cme", "dat")

app = typer.Typer(help="Q-SPEACE quantum layer CLI")
quantum_app = typer.Typer(help="Quantum experiments and tools")
sia_app = typer.Typer(help="Self-Improvement Cortex (SIA)")
brain_app = typer.Typer(help="SpikingBrain satellite (T205)")
economy_app = typer.Typer(help="q_speace_economy primitives (T6.*)")
eval_app = typer.Typer(help="Vertical-slice policy evaluation (T208/T231)")
singularity_app = typer.Typer(help="Phase-transition & genetic-epigenetic framework (T234)")
micro_node_app = typer.Typer(help="Self-hosted SPEACE Micro Node & compliance evidence (T239)")
app.add_typer(quantum_app, name="quantum")
app.add_typer(sia_app, name="sia")
app.add_typer(brain_app, name="brain")
app.add_typer(economy_app, name="economy")
app.add_typer(eval_app, name="eval")
app.add_typer(singularity_app, name="singularity")
app.add_typer(micro_node_app, name="micro-node")


@quantum_app.command("run")
def quantum_run(
    ticks: int = typer.Option(10, "--ticks", "-t", min=0),
    neurons: int = typer.Option(4, "--neurons", "-n", min=1),
    earth: bool = typer.Option(False, "--earth/--no-earth"),
    radio: bool = typer.Option(False, "--radio/--no-radio"),
    metasurface: bool = typer.Option(False, "--metasurface/--no-metasurface"),
) -> None:
    """Run the quantum orchestrator for N ticks."""
    genome = QuantumGeneSet(enabled=True, qubits_per_neuron=1)
    orch = QuantumOrchestrator(
        genome=genome,
        neurons=[f"neuron_{i}" for i in range(neurons)],
        enable_earth=earth,
        enable_radio=radio,
        enable_metasurface=metasurface,
    )
    orch.enable_qca(num_cells=min(max(neurons, 2), 16))
    report = orch.run(ticks=ticks)
    typer.echo(f"Ran {len(report)} ticks")
    typer.echo(str(orch.report()))
    if radio and report:
        last = report[-1]
        typer.echo(f"Last TX: {last.tx_report}")
        spectrum = last.spectrum
        snr_db = float(getattr(spectrum, "snr_db", float("nan")))
        rssi_dbm = float(getattr(spectrum, "rssi_dbm", float("nan")))
        typer.echo(f"Spectrum: snr={snr_db:.1f} dB rssi={rssi_dbm:.1f} dBm")


@quantum_app.command("benchmark")
def quantum_benchmark(
    qubits: int = typer.Option(4, "--qubits", "-q", min=1),
    ticks: int = typer.Option(10, "--ticks", "-t", min=1),
    backend: str = typer.Option("numpy", "--backend", "-b"),
) -> None:
    """Run the Schumann-resonance benchmark experiment."""
    from .quantum.backends import build

    selected = build(backend)  # validates backend selection / fallback
    result = run_schumann(num_qubits=qubits, ticks=ticks)
    if selected.name != backend:
        typer.echo(f"Backend: {selected.name} (fallback from {backend})")
    else:
        typer.echo(f"Backend: {selected.name}")
    typer.echo(f"Mean coherence: {result['mean_coherence']:.4f}")
    typer.echo(f"Coherence trace: {result['coherence_trace']}")


@quantum_app.command("synthesize")
def quantum_synthesize() -> None:
    """List BCEL quantum equivalences (biological->cybernetic)."""
    catalog = BCELCatalog()
    for eq in catalog.all():
        typer.echo(f"{eq.concept} -> {eq.classification}")
        typer.echo(f"  {eq.digital_rule}")


@quantum_app.command("cqasm")
def quantum_cqasm(
    qubits: int = typer.Option(4, "--qubits", "-q", min=1),
    tick: int = typer.Option(0, "--tick", "-t"),
    version: str = typer.Option("3.0", "--version", "-v"),
    use_network: bool = typer.Option(False, "--earth/--no-earth"),
) -> None:
    """Print a cQASM program ready to paste into Quantum Inspire.

    Angles are derived from real Earth signals (Kp, sunspot, tide) at the
    given tick: rx=Kp_norm*pi, ry=sun*pi, rz=tide*2*pi.
    """
    feed = EarthFeed(use_network=use_network)
    angles = feed.fetch(tick).rotation_angles()
    circ = schumann_circuit(qubits, angles)
    typer.echo(to_cqasm(circ, version=version), nl=False)


@quantum_app.command("bridge")
def quantum_bridge(
    atom_coherence: float = typer.Option(0.5, "--atom", "-a"),
    brain_seed: float = typer.Option(0.5, "--brain", "-b"),
    version: str = typer.Option("3.0", "--version", "-v"),
) -> None:
    """Print a 5-qubit QI bridge circuit (phi_bridge + cross-scale coupling)."""
    typer.echo(qi_bridge_cqasm(atom_coherence, brain_seed, version=version), nl=False)


@quantum_app.command("cross-scale")
def quantum_cross_scale(
    ticks: int = typer.Option(20, "--ticks", "-t", min=1),
    atom_noise: float = typer.Option(0.2, "--noise", "-n"),
) -> None:
    """Run the cross-scale emergence experiment (bottom-up noise proof)."""
    base, noisy = experiment_cross_scale(ticks=ticks, atom_noise=atom_noise)
    typer.echo(f"brain sigma (baseline): {base:.4f}")
    typer.echo(f"brain sigma (atom-noise): {noisy:.4f}")
    typer.echo(f"cross-scale emergence: {'YES' if noisy > base else 'NO'}")


@quantum_app.command("memory-audit")
def quantum_memory_audit(
    ticks: int = typer.Option(16, "--ticks", "-t", min=2),
) -> None:
    """Run T249-06 GC object-growth & bounded-history audit on QuantumOrchestrator + SIA."""
    from .vertical_slice.diagnostics import MemoryLeakAuditor

    auditor = MemoryLeakAuditor()
    auditor.capture_baseline()
    orch = QuantumOrchestrator(
        genome=QuantumGeneSet(enabled=True),
        neurons=["n0", "n1", "n2", "n3"],
        seed=0,
        enable_spikes=True,
        enable_criticality=True,
        enable_homeostasis=True,
        max_history=32,
    )
    orch.enable_qca(num_cells=4)
    orch.run(ticks=ticks)
    sia = SelfImprovementCortex(max_history=32)
    for _ in range(min(ticks, 8)):
        sia.tick({"coherence_phi": 0.6})
    audit_res = auditor.audit({"orchestrator": orch, "sia": sia})
    payload = {
        "passed": audit_res.passed,
        "temporal_liveness": orch.temporal_liveness(),
        "unbounded_containers": list(audit_res.unbounded_containers),
        "suspected_type_growth": audit_res.suspected_type_growth,
    }
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    if not audit_res.passed:
        raise typer.Exit(3)


@sia_app.command("run")
def sia_run(
    ticks: int = typer.Option(10, "--ticks", "-t", min=0),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the Self-Improvement Cortex for N ticks."""
    cortex = SelfImprovementCortex()
    for i in range(ticks):
        report = cortex.tick({"coherence_phi": 0.7, "plasticity_index": 0.5})
        if verbose:
            typer.echo(
                f"tick={i}: proposals={report.proposals} selected={report.selected} "
                f"mutations={report.mutations_applied} rollbacks={report.rollbacks}"
            )
    typer.echo(str(cortex.report()))


@sia_app.command("status")
def sia_status() -> None:
    """Print current SIA status summary."""
    cortex = SelfImprovementCortex()
    report = cortex.report()
    for k, v in report.items():
        typer.echo(f"  {k}: {v}")


@sia_app.command("dna")
def sia_dna(
    limit: int = typer.Option(10, "--limit", "-l", min=1),
) -> None:
    """List recent DNA mutation records."""
    cortex = SelfImprovementCortex()
    records = cortex.dna.recent(limit)
    typer.echo(f"DNA mutation records (last {len(records)}):")
    for r in records:
        typer.echo(
            f"  [{r.mutation_id}] level={r.level} target={r.target} "
            f"confidence={r.confidence:.2f} active={r.active}"
        )


@sia_app.command("benchmark")
def sia_benchmark(
    min_qubits: int = typer.Option(4, "--min-qubits", "-q", min=1),
    max_qubits: int = typer.Option(20, "--max-qubits", "-Q", min=1),
    trials: int = typer.Option(2, "--trials", "-t", min=1),
) -> None:
    """Benchmark QEE entanglement simulation (GPU if available)."""
    from .self_improvement_cortex.benchmark import benchmark_gpu, print_report

    res = benchmark_gpu(min_qubits=min_qubits, max_qubits=max_qubits, trials=trials)
    print_report(res)


@quantum_app.command("qee")
def quantum_qee(
    strategies: str = typer.Option(
        '[{"id":"a","expected_impact":0.8,"risk":0.2,"confidence":0.7,"energy_cost":0.1,"novelty":0.3},{"id":"b","expected_impact":0.5,"risk":0.5,"confidence":0.6,"energy_cost":0.3,"novelty":0.1}]',
        "--strategies",
        "-s",
    ),
) -> None:
    """Test the Quantum Evolution Engine with sample strategies."""
    from .self_improvement_cortex import QuantumEvolutionEngine

    parsed = json.loads(strategies)
    engine = QuantumEvolutionEngine()
    results = engine.propose_candidates(parsed, {})
    typer.echo(f"QEE proposed {len(results)} candidates:")
    for r in results:
        typer.echo(
            f"  [{r.method}] id={r.candidate_id} score={r.score:.3f} confidence={r.confidence:.3f}"
        )


@app.command()
def version() -> None:
    """Print package version."""
    from importlib.metadata import version as _v

    typer.echo(_v("q-speace"))


# ----------------------------------------------------------------------
# SpikingBrain satellite (T205)
# ----------------------------------------------------------------------


def _run_coro[T](coro: Coroutine[Any, Any, T]) -> T:  # pragma: no cover — trivial wrapper
    return asyncio.run(coro)


@brain_app.command("think")
def brain_think(
    prompt: str = typer.Argument(..., help="Prompt for the SpikingBrain area."),
    tokens: int = typer.Option(32, "--tokens", "-n", min=1, help="Max new tokens."),
    coherence: float = typer.Option(1.0, "--coherence", "-c", help="Initial ILF coherence_phi."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty text."),
) -> None:
    """Send one prompt to the SpikingBrain satellite and print the result.

    Uses the stub backend unless ``Q_SPEACE_BRAIN_ENDPOINT`` is set.
    """
    from .edd_cvt.ilf import InformationalLogicalField

    ilf = InformationalLogicalField(coherence_phi=coherence)
    cortex = SpikingBrainCortex(ilf=ilf)

    async def run() -> ThinkResult:
        return await cortex.think(prompt, n_tokens=tokens)

    result = _run_coro(run())
    if json_out:
        typer.echo(
            json.dumps(
                {
                    "text": result.text,
                    "confidence": result.confidence,
                    "belief": result.belief.tolist(),
                    "spikes": {
                        "num_spikes": result.spikes.num_spikes,
                        "sparsity": result.spikes.sparsity,
                    },
                    "plasticity": result.plasticity.tolist(),
                    "backend": cortex.backend_name,
                },
                indent=2,
            )
        )
    else:
        typer.echo(f"backend: {cortex.backend_name}")
        typer.echo(f"text: {result.text}")
        typer.echo(f"belief: {[round(float(x), 3) for x in result.belief]}")
        typer.echo(f"confidence: {result.confidence:.3f}")
        typer.echo(
            f"spikes: num={result.spikes.num_spikes} " f"sparsity={result.spikes.sparsity:.2f}"
        )
        typer.echo(f"plasticity: {[round(float(x), 3) for x in result.plasticity]}")


@brain_app.command("tick")
def brain_tick(
    prompt: str = typer.Argument(..., help="Prompt for the cognitive step."),
    tokens: int = typer.Option(32, "--tokens", "-n", min=1),
    coherence: float = typer.Option(1.0, "--coherence", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run one full sense-decide-act step (think + cost + gate + ILF apply)."""
    from .edd_cvt.ilf import InformationalLogicalField

    ilf = InformationalLogicalField(coherence_phi=coherence)
    cortex = SpikingBrainCortex(ilf=ilf)

    async def run() -> CortexReport:
        return await cortex.tick(prompt, n_tokens=tokens)

    report = _run_coro(run())
    typer.echo(f"backend: {report.backend}")
    typer.echo(f"approved: {report.approved}")
    typer.echo(f"reason: {report.reason}")
    typer.echo(f"sevo: {report.sevo:.3f}")
    typer.echo(f"energy_w: {report.energy_w:.3f}")
    typer.echo(f"confidence: {report.confidence:.3f}")
    if verbose and report.result is not None:
        typer.echo(f"text: {report.result.text}")


@brain_app.command("health")
def brain_health() -> None:
    """Check the SpikingBrain satellite health."""
    cortex = SpikingBrainCortex()

    async def run() -> dict[str, Any]:
        return await cortex.health()

    h = _run_coro(run())
    typer.echo(json.dumps(h, indent=2))


@brain_app.command("ab-benchmark")
def brain_ab_benchmark(
    seed: int = typer.Option(2026, "--seed", "-s", help="Deterministic PRNG seed."),
) -> None:
    """Run T250 A/B complex benchmark (SPEACE Neural Agent vs Classical Baseline)."""
    from .neural_agent import run_ab_neural_benchmark

    comparison = run_ab_neural_benchmark(seed=seed)
    typer.echo(json.dumps(comparison.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    if not comparison.speace_outperforms_baseline:
        raise typer.Exit(3)


@brain_app.command("chat")
def brain_chat(
    coherence: float = typer.Option(1.0, "--coherence", "-c", help="Initial ILF coherence_phi."),
    max_turns: int = typer.Option(
        16, "--turns", "-t", min=1, help="Max turns before the REPL auto-quits."
    ),
    backend: str = typer.Option(
        "auto",
        "--backend",
        "-b",
        help="Force backend: 'stub' or 'auto' (uses HTTP if Q_SPEACE_BRAIN_ENDPOINT is set).",
    ),
) -> None:
    """Interactive REPL chat with the SpikingBrain area, history preserved.

    Each turn the prompt is sent through the same pipeline as ``brain think``
    (backend -> ThinkResult -> optional ILF belief injection via the
    cortex ``tick()`` gate). The cortex retains the rolling history
    across turns so the model receives short multi-turn context.

    Type ``q``, ``quit`` or ``exit`` (empty input) to end the REPL.
    """
    from .edd_cvt.ilf import InformationalLogicalField
    from .spiking_brain import StubSpikingBrain, make_spiking_brain

    ilf = InformationalLogicalField(coherence_phi=coherence)
    chosen: object = StubSpikingBrain() if backend == "stub" else make_spiking_brain()
    cortex = SpikingBrainCortex(ilf=ilf, backend=chosen)

    typer.echo(f"[brain] backend={cortex.backend_name} coherence={coherence:.2f}")
    typer.echo("[brain] type 'q' to quit, empty enter to end")
    for i in range(max_turns):
        try:
            prompt = typer.prompt(f"[turn {i + 1}/{max_turns}] you")
        except (EOFError, KeyboardInterrupt, typer.Abort):
            typer.echo("")
            break
        if prompt.strip().lower() in {"q", "quit", "exit"}:
            break
        if not prompt.strip():
            break

        try:
            report = _run_coro(cortex.tick(prompt, history=cortex.history or None))
        except Exception as exc:  # noqa: BLE001 — REPL should not crash
            typer.echo(f"[brain] error: {exc.__class__.__name__}: {exc}")
            continue

        if report.result is None:
            typer.echo(f"[brain] output rejected: {report.reason}")
            continue
        result = report.result
        typer.echo(f"[brain] {result.text}")
        typer.echo(
            f"        conf={result.confidence:.2f} "
            f"belief={[round(float(x), 2) for x in result.belief]} "
            f"backend={cortex.backend_name}"
        )
    rep = cortex.report()
    typer.echo("")
    typer.echo("[brain] final stats:")
    typer.echo(json.dumps(rep, indent=2))


def main() -> None:
    app()


# ----------------------------------------------------------------------
# q_speace_economy primitives (T6.*)
# ----------------------------------------------------------------------


@economy_app.command("validate-schema")
def economy_validate_schema(
    schema: str = typer.Argument("all", help="Schema name (j_c/v/cme/dat) or 'all'."),
) -> None:
    """Validate the q_speace_economy JSON schemas against Draft 2020-12."""
    from jsonschema import Draft202012Validator

    if schema != "all" and schema not in _VALID_ECONOMY_SCHEMAS:
        raise typer.BadParameter(
            f"unknown schema {schema!r}; choose 'all' or one of {list(_VALID_ECONOMY_SCHEMAS)}"
        )

    base = Path(__file__).parent / "economy" / "schemas"
    targets = list(_VALID_ECONOMY_SCHEMAS) if schema == "all" else [schema]
    for name in targets:
        path = base / f"{name}.schema.json"
        with path.open(encoding="utf-8") as f:
            doc = json.load(f)
        Draft202012Validator.check_schema(doc)
        typer.echo(f"{name} OK")


@economy_app.command("jc-from-telemetry")
def economy_jc_from_telemetry(
    j: float = typer.Option(..., "--J", help="Useful exergy (J)."),
    delta_s: float = typer.Option(..., "--delta-S", help="Entropy produced (<=0)."),
    delta_i_c: float = typer.Option(..., "--delta-I-c", help="Catalytic info flux (bits)."),
    r_b: float = typer.Option(..., "--R-b", help="Regenerative budget in [0,1]."),
    delta_c: float = typer.Option(..., "--delta-C", help="Net capacity change in [-1,1]."),
    measured: int = typer.Option(5, "--measured", help="Components actually measured."),
    total: int = typer.Option(5, "--total", help="Total components."),
) -> None:
    """Build a J_c 5-tuple from telemetry and print it as JSON."""
    from .economy.primitives import J_c

    jc = J_c.from_telemetry(
        J=j,
        delta_S=delta_s,
        delta_I_c=delta_i_c,
        R_b=r_b,
        delta_C=delta_c,
        measured_components=measured,
        total_components=total,
    )
    typer.echo(json.dumps(jc.to_dict(), indent=2))


@economy_app.command("mcp-self-test")
def economy_mcp_self_test() -> None:
    """Run the MCP server self-test (all 10 tools)."""
    from .economy.mcp_server import main as mcp_main

    rc = mcp_main(["--self-test"])
    raise typer.Exit(rc)


# ----------------------------------------------------------------------
# Vertical-slice evaluation (T208 Group B / T231)
# ----------------------------------------------------------------------


@eval_app.command("run")
def eval_run(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for traces+manifest."),
    ],
    policy: str = typer.Option(
        "always_answer",
        "--policy",
        "-p",
        help="Policy kind: always_answer | confidence_gate | energy_gate | combined_gate.",
    ),
    seed: int = typer.Option(0, "--seed", "-s", help="Deterministic RNG seed."),
    min_confidence: float = typer.Option(0.60, "--min-confidence", help="Confidence threshold."),
    max_energy_j: float = typer.Option(80.0, "--max-energy-j", help="Energy budget (J)."),
    sevo_threshold: float = typer.Option(1.5, "--sevo-threshold", help="Sevo threshold."),
    include_raw_text: bool = typer.Option(
        False,
        "--include-raw-text/--redact-raw-text",
        help="Opt-in raw prompt/response capture (redacted by default per T208 §4.3).",
    ),
    live_brain: bool = typer.Option(
        False,
        "--live-brain",
        help="Use make_spiking_brain() (honors Q_SPEACE_BRAIN_ENDPOINT) instead of offline stub.",
    ),
    timeout_s: float = typer.Option(10.0, "--timeout-s", help="Per-case backend timeout (s)."),
) -> None:
    """Execute one vertical-slice policy run and write privacy-safe JSONL + manifest."""
    from .spiking_brain import make_spiking_brain
    from .vertical_slice import (
        VALID_POLICY_KINDS,
        PolicyConfig,
        VerticalSliceRunner,
        default_fixture_dataset,
        evaluate_traces,
        write_manifest,
        write_traces_jsonl,
    )

    if policy not in VALID_POLICY_KINDS:
        typer.echo(f"error: unknown policy {policy!r}; expected one of {list(VALID_POLICY_KINDS)}")
        raise typer.Exit(2)

    try:
        cfg = PolicyConfig(
            policy_id=f"t209-{policy}",
            kind=policy,  # type: ignore[arg-type]
            min_confidence=min_confidence,
            max_energy_j=max_energy_j,
            sevo_threshold=sevo_threshold,
        )
    except ValueError as exc:
        typer.echo(f"error: invalid policy configuration: {exc}")
        raise typer.Exit(2) from None

    dataset = default_fixture_dataset()
    cortex = (
        SpikingBrainCortex(backend=make_spiking_brain(seed=seed, timeout_s=timeout_s))
        if live_brain
        else None
    )
    runner = VerticalSliceRunner(
        cortex=cortex,
        policy=cfg,
        seed=seed,
        timeout_s=timeout_s,
        include_raw_text=include_raw_text,
    )
    traces, manifest = runner.run_dataset(dataset)
    evaluation = evaluate_traces(traces, dataset)
    write_traces_jsonl(output / "traces.jsonl", traces)
    write_manifest(output / "manifest.json", manifest)
    (output / "evaluation.json").write_text(
        json.dumps(evaluation.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    typer.echo(json.dumps(evaluation.to_dict(), indent=2))
    if evaluation.failed > 0:
        raise typer.Exit(1)


@eval_app.command("compare")
def eval_compare(
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory for comparison."),
    ],
    candidate: str = typer.Option(
        "combined_gate",
        "--candidate",
        "-c",
        help="Candidate policy to compare against always_answer baseline.",
    ),
    seed: int = typer.Option(0, "--seed", "-s", help="Deterministic seed."),
    min_confidence: float = typer.Option(0.60, "--min-confidence"),
    max_energy_j: float = typer.Option(80.0, "--max-energy-j"),
    live_brain: bool = typer.Option(
        False,
        "--live-brain",
        help="Use make_spiking_brain() (honors Q_SPEACE_BRAIN_ENDPOINT) instead of offline stub.",
    ),
    timeout_s: float = typer.Option(10.0, "--timeout-s", help="Per-case backend timeout (s)."),
) -> None:
    """Compare a candidate policy against always_answer baseline with paired bootstrap CIs."""
    from .spiking_brain import make_spiking_brain
    from .vertical_slice import (
        VALID_POLICY_KINDS,
        PolicyConfig,
        VerticalSliceRunner,
        compare_policies,
        default_fixture_dataset,
        write_manifest,
        write_traces_jsonl,
    )

    if candidate not in VALID_POLICY_KINDS:
        typer.echo(f"error: unknown candidate policy {candidate!r}")
        raise typer.Exit(2)

    dataset = default_fixture_dataset()
    base_cfg = PolicyConfig(policy_id="t209-always_answer", kind="always_answer")
    cand_cfg = PolicyConfig(
        policy_id=f"t209-{candidate}",
        kind=candidate,  # type: ignore[arg-type]
        min_confidence=min_confidence,
        max_energy_j=max_energy_j,
    )
    base_cortex = (
        SpikingBrainCortex(backend=make_spiking_brain(seed=seed, timeout_s=timeout_s))
        if live_brain
        else None
    )
    cand_cortex = (
        SpikingBrainCortex(backend=make_spiking_brain(seed=seed, timeout_s=timeout_s))
        if live_brain
        else None
    )
    base_traces, base_manifest = VerticalSliceRunner(
        cortex=base_cortex, policy=base_cfg, seed=seed, timeout_s=timeout_s
    ).run_dataset(dataset)
    cand_traces, cand_manifest = VerticalSliceRunner(
        cortex=cand_cortex, policy=cand_cfg, seed=seed, timeout_s=timeout_s
    ).run_dataset(dataset)
    comparison = compare_policies(base_traces, cand_traces, dataset, seed=seed)

    output.mkdir(parents=True, exist_ok=True)
    write_traces_jsonl(output / "baseline_traces.jsonl", base_traces)
    write_manifest(output / "baseline_manifest.json", base_manifest)
    write_traces_jsonl(output / "candidate_traces.jsonl", cand_traces)
    write_manifest(output / "candidate_manifest.json", cand_manifest)
    (output / "comparison.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    typer.echo(json.dumps(comparison, indent=2))


@eval_app.command("t210-campaign")
def eval_t210_campaign(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional directory for calibration/held-out traces, manifests, and decision report.",
        ),
    ] = None,
    seed: Annotated[int, typer.Option("--seed")] = 0,
    max_unsafe_answer_rate: Annotated[float, typer.Option("--max-unsafe-answer-rate")] = 0.10,
    live_brain: Annotated[
        bool,
        typer.Option(
            "--live-brain",
            help="Use configured SpikingBrain sidecar (Q_SPEACE_BRAIN_ENDPOINT) instead of stub.",
        ),
    ] = False,
    timeout_s: Annotated[float, typer.Option("--timeout-s")] = 10.0,
) -> None:
    """Run T208 Group C / T244 80-case disjoint calibration -> held-out decision campaign."""
    from .spiking_brain import SpikingBrainCortex, make_spiking_brain
    from .vertical_slice import run_t210_calibration_and_decision_campaign

    factory = (
        (lambda: SpikingBrainCortex(backend=make_spiking_brain(seed=seed, timeout_s=timeout_s)))
        if live_brain
        else None
    )
    report = run_t210_calibration_and_decision_campaign(
        cortex_factory=factory,
        seed=seed,
        timeout_s=timeout_s,
        max_unsafe_answer_rate=max_unsafe_answer_rate,
        output_dir=output,
    )
    summary = {
        "spec": report["spec"],
        "calibration_size": report["calibration_size"],
        "held_out_size": report["held_out_size"],
        "calibrated_thresholds": report["calibrated_thresholds"],
        "t210_10_decisions": report["t210_10_decisions"],
    }
    typer.echo(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))


@eval_app.command("stratify")
def eval_stratify(
    policy: Annotated[str, typer.Option("--policy", "-p")] = "combined_gate",
    seed: Annotated[int, typer.Option("--seed")] = 0,
) -> None:
    """Run T249-06 regime-stratified failure taxonomy on the vertical-slice fixture dataset."""
    from .spiking_brain import StubSpikingBrain
    from .vertical_slice import (
        PolicyKind,
        StratifiedFailureAnalyzer,
        VerticalSliceRunner,
        default_fixture_dataset,
        default_policy,
    )

    dataset = default_fixture_dataset()
    cfg = default_policy(policy)  # type: ignore[arg-type]
    _ = PolicyKind  # keep typing explicit
    cortex = SpikingBrainCortex(backend=StubSpikingBrain(seed=seed))
    traces, _manifest = VerticalSliceRunner(cortex=cortex, policy=cfg, seed=seed).run_dataset(
        dataset
    )
    labels = {c.case_id: c.should_answer for c in dataset.cases}
    diag = StratifiedFailureAnalyzer().analyze(traces, labels)
    typer.echo(json.dumps(diag.to_dict(), indent=2, sort_keys=True, allow_nan=False))


@eval_app.command("t251-benchmark")
def eval_t251_benchmark(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional directory to write t251_benchmark_report.json.",
        ),
    ] = None,
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    resamples: Annotated[int, typer.Option("--resamples", min=100)] = 1000,
) -> None:
    """Run T251 80-case disjoint Calibration/Held-Out Grounded Dual-Speed A/B/C benchmark."""
    from .vertical_slice import run_t251_benchmark_campaign

    report = run_t251_benchmark_campaign(
        seed=seed,
        n_resamples=resamples,
        output_dir=output,
    )
    public_report = {k: v for k, v in report.items() if not k.startswith("_")}
    typer.echo(json.dumps(public_report, indent=2, sort_keys=True, allow_nan=False))
    if not report["all_gates_passed"]:
        raise typer.Exit(3)


@eval_app.command("t252-benchmark")
def eval_t252_benchmark(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional directory to write t252_t253_benchmark_report.json.",
        ),
    ] = None,
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    resamples: Annotated[int, typer.Option("--resamples", min=100)] = 1000,
) -> None:
    """Run T252–T253 preregistered Experiential Transfer & Selective Repair benchmark."""
    from .vertical_slice import run_t252_t253_campaign

    report = run_t252_t253_campaign(
        seed=seed,
        n_resamples=resamples,
        output_dir=output,
    )
    typer.echo(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    if not report["all_gates_passed"]:
        raise typer.Exit(3)


@eval_app.command("t255-nl-benchmark")
def eval_t255_nl_benchmark(
    live_brain: Annotated[
        bool,
        typer.Option(
            "--live-brain",
            help="Connect to live HTTP generative sidecar (Q_SPEACE_BRAIN_ENDPOINT / localhost:8002).",
        ),
    ] = False,
    endpoint: Annotated[
        str | None,
        typer.Option("--endpoint", help="Explicit HTTP sidecar base URL override."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output", "-o", help="Optional JSON output path for full T255 trace report."
        ),
    ] = None,
    timeout_s: Annotated[float, typer.Option("--timeout-s", min=1.0)] = 45.0,
    max_tokens: Annotated[int, typer.Option("--max-tokens", min=32)] = 160,
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    resamples: Annotated[int, typer.Option("--resamples", min=100)] = 1000,
) -> None:
    """Run T255 3-arm Natural-Language Belief Revision & Selective Repair benchmark."""
    from .vertical_slice import run_t255_nl_benchmark

    report = run_t255_nl_benchmark(
        live_brain=live_brain,
        endpoint=endpoint,
        timeout_s=timeout_s,
        max_tokens=max_tokens,
        seed=seed,
        n_resamples=resamples,
        output_path=output,
    )
    compact = {k: v for k, v in report.items() if k != "all_traces"}
    typer.echo(json.dumps(compact, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False))


@eval_app.command("agi-profile")
def eval_agi_profile(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional JSON file path to persist the 5-axis agi_profile.v1 report.",
        ),
    ] = None,
    ratchet_file: Annotated[
        Path | None,
        typer.Option(
            "--ratchet-file",
            help="Optional DifferentialErrorRatchet JSON baseline path.",
        ),
    ] = None,
    save_ratchet: Annotated[
        bool,
        typer.Option(
            "--save-ratchet",
            help="Write current failed held-out case IDs as the ratchet baseline.",
        ),
    ] = False,
    phase1_only: Annotated[
        bool,
        typer.Option(
            "--phase1-only",
            help="Evaluate only T251 Phase-1 axes (Axes 1, 2, 5), leaving Axes 3–4 inactive.",
        ),
    ] = False,
    seed: Annotated[int, typer.Option("--seed")] = 2026,
    resamples: Annotated[int, typer.Option("--resamples", min=100)] = 1000,
) -> None:
    """Generate the 5-axis anti-Goodhart Cognitive Capability Profile (agi_profile.v1)."""
    from .vertical_slice import build_agi_capability_profile

    profile = build_agi_capability_profile(
        seed=seed,
        n_resamples=resamples,
        ratchet_path=ratchet_file,
        save_ratchet_baseline=save_ratchet,
        include_experiential_phases=not phase1_only,
    )
    formatted = json.dumps(profile, indent=2, sort_keys=True, allow_nan=False)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(formatted + "\n", encoding="utf-8")
    typer.echo(formatted)
    if profile["overall_verdict"] in (
        "BLOCKED_SAFETY",
        "REGRESSION_RATCHET_FAILED",
        "EXPERIENTIAL_GATE_FAILED",
    ):
        raise typer.Exit(3)


@singularity_app.command("manifest")
def singularity_manifest(
    section: str | None = typer.Option(
        None, "--section", "-s", help="Optional manifest section filter."
    ),
) -> None:
    """Print the canonical T234 v1.1 Singularity phase-transition & epigenetic manifest."""
    from .singularity import build_singularity_framework_manifest

    try:
        data = build_singularity_framework_manifest(section=section)
    except ValueError as exc:
        typer.echo(f"error: {exc}")
        raise typer.Exit(2) from None
    typer.echo(json.dumps(data, indent=2, sort_keys=True, allow_nan=False))


@singularity_app.command("drills")
def singularity_drills() -> None:
    """Run all 6 T234 Pillar-5 adversarial & rollback verification drills."""
    from .singularity import run_t234_verification_drills

    report = run_t234_verification_drills()
    typer.echo(json.dumps(report.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    if not report.all_passed or report.rollback_pass_rate < 1.0:
        raise typer.Exit(3)


@singularity_app.command("assess")
def singularity_assess(
    telemetry_file: Annotated[
        Path,
        typer.Option(
            "--telemetry",
            "-f",
            help="Path to JSON file matching PhaseTelemetry / phase_transition_assess schema.",
        ),
    ],
) -> None:
    """Assess informational phase-transition stage and physical brakes from telemetry JSON."""
    from .singularity import handle_phase_transition_assess

    if not telemetry_file.exists():
        typer.echo(f"error: telemetry file not found: {telemetry_file}")
        raise typer.Exit(2)
    try:
        raw = json.loads(telemetry_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("telemetry JSON must be an object")
        verdict = handle_phase_transition_assess(raw)
    except (ValueError, KeyError, TypeError) as exc:
        typer.echo(f"error: invalid telemetry payload: {exc}")
        raise typer.Exit(2) from None
    typer.echo(json.dumps(verdict, indent=2, sort_keys=True, allow_nan=False))


@singularity_app.command("iont-assess")
def singularity_iont_assess(
    profile_file: Annotated[
        Path,
        typer.Option(
            "--profile",
            "-p",
            help="Path to JSON file matching IoNTNodeProfile / iont_node_assess schema.",
        ),
    ],
) -> None:
    """Assess an external IoNT/Micro-IoT cellular node against T236 4-layer safety bounds."""
    from .singularity import handle_iont_node_assess

    if not profile_file.exists():
        typer.echo(f"error: profile file not found: {profile_file}")
        raise typer.Exit(2)
    try:
        raw = json.loads(profile_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("profile JSON must be an object")
        assessment = handle_iont_node_assess(raw)
    except (ValueError, KeyError, TypeError) as exc:
        typer.echo(f"error: invalid IoNT profile payload: {exc}")
        raise typer.Exit(2) from None
    typer.echo(json.dumps(assessment, indent=2, sort_keys=True, allow_nan=False))
    if not assessment["admitted_for_mcp_advisory"]:
        raise typer.Exit(3)


@singularity_app.command("federation-benchmark")
def singularity_federation_benchmark(
    seeds: Annotated[
        str,
        typer.Option(
            "--seeds",
            help="Comma-separated deterministic integer seeds (e.g. '11,23,37,53').",
        ),
    ] = "11,23,37,53",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path to write the full JSON benchmark report.",
        ),
    ] = None,
) -> None:
    """Run T237 4-configuration IoNT cellular node federation & ablation benchmark."""
    from .singularity import run_iont_federation_benchmark

    try:
        parsed_seeds = tuple(int(s.strip()) for s in seeds.split(",") if s.strip())
        if not parsed_seeds:
            raise ValueError("at least one integer seed is required")
    except ValueError as exc:
        typer.echo(f"error: invalid --seeds value: {exc}")
        raise typer.Exit(2) from None

    report = run_iont_federation_benchmark(seeds=parsed_seeds)
    payload = report.to_dict()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    summary = {
        "spec": report.spec,
        "sandboxed": report.sandboxed,
        "mcp_actuation_permitted": report.mcp_actuation_permitted,
        "layer0_independence_verified": report.layer0_independence_verified,
        "consensus_quorum_slow_plane_only": report.consensus_quorum_slow_plane_only,
        "federation_benefit_verified": report.federation_benefit_verified,
        "singularity_ablation_verified": report.singularity_ablation_verified,
        "calibration_summary": payload["calibration_summary"],
        "held_out_summary": payload["held_out_summary"],
    }
    typer.echo(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    if not report.federation_benefit_verified or not report.singularity_ablation_verified:
        raise typer.Exit(3)


@singularity_app.command("resilience-benchmark")
def singularity_resilience_benchmark(
    seeds: Annotated[
        str,
        typer.Option(
            "--seeds",
            help="Comma-separated deterministic integer seeds (e.g. '11,23,37,53').",
        ),
    ] = "11,23,37,53",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path to write the full T238 JSON resilience report.",
        ),
    ] = None,
) -> None:
    """Run T238 adversarial Byzantine & coordinator-blackout resilience benchmark."""
    from .singularity import run_t238_adversarial_resilience_benchmark

    try:
        parsed_seeds = tuple(int(s.strip()) for s in seeds.split(",") if s.strip())
        if not parsed_seeds:
            raise ValueError("at least one integer seed is required")
    except ValueError as exc:
        typer.echo(f"error: invalid --seeds value: {exc}")
        raise typer.Exit(2) from None

    report = run_t238_adversarial_resilience_benchmark(seeds=parsed_seeds)
    payload = report.to_dict()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    summary = {
        "spec": report.spec,
        "sandboxed": report.sandboxed,
        "mcp_actuation_permitted": report.mcp_actuation_permitted,
        "layer0_independence_verified": report.layer0_independence_verified,
        "consensus_quorum_slow_plane_only": report.consensus_quorum_slow_plane_only,
        "byzantine_detection_rate": report.byzantine_detection_rate,
        "malicious_proposals_attempted": report.malicious_proposals_attempted,
        "malicious_proposals_blocked": report.malicious_proposals_blocked,
        "blackout_episodes_reconciled": report.blackout_episodes_reconciled,
        "blackout_episodes_total": report.blackout_episodes_total,
        "blackout_failover_verified": report.blackout_failover_verified,
        "byzantine_resilience_verified": report.byzantine_resilience_verified,
        "overall_resilience_verified": report.overall_resilience_verified,
        "held_out_summary": payload["held_out_summary"],
    }
    typer.echo(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    if not report.overall_resilience_verified:
        raise typer.Exit(3)


@singularity_app.command("triadic-safeguard")
def singularity_triadic_safeguard(
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path to write the full T254 JSON safeguard benchmark report.",
        ),
    ] = None,
) -> None:
    """Run T254 Triadic Substrate Safeguard & Anti-Polycrisis comparative evaluation."""
    from .singularity import run_t254_polycrisis_safeguard_benchmark

    report = run_t254_polycrisis_safeguard_benchmark()
    payload = report.to_dict()
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    if not report.strictly_beats_baselines:
        raise typer.Exit(3)


@micro_node_app.command("certify")
def micro_node_certify(
    node_id: Annotated[
        str,
        typer.Option("--node-id", help="Operator identifier for this SPEACE Micro Node."),
    ] = "speace-micro-local",
    seeds: Annotated[
        str,
        typer.Option(
            "--seeds",
            help="Comma-separated deterministic integer seeds for T237/T238.",
        ),
    ] = "11,23,37,53",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Optional path to write the hashed T239 JSON evidence bundle.",
        ),
    ] = None,
) -> None:
    """Generate a SHA-256 verifiable compliance evidence bundle for a SPEACE Micro Node (T239)."""
    from .singularity import certify_micro_node

    try:
        parsed_seeds = tuple(int(s.strip()) for s in seeds.split(",") if s.strip())
        if not parsed_seeds:
            raise ValueError("at least one integer seed is required")
    except ValueError as exc:
        typer.echo(f"error: invalid --seeds value: {exc}")
        raise typer.Exit(2) from None

    bundle = certify_micro_node(node_id=node_id, seeds=parsed_seeds, output_path=output)
    typer.echo(json.dumps(bundle.to_dict(), indent=2, sort_keys=True, allow_nan=False))
    if not bundle.overall_compliant:
        raise typer.Exit(3)


@micro_node_app.command("verify-bundle")
def micro_node_verify_bundle(
    bundle_file: Annotated[
        Path,
        typer.Option("--bundle", "-b", help="Path to a T239 JSON evidence bundle to verify."),
    ],
) -> None:
    """Independently verify SHA-256 integrity and safety invariants of a T239 evidence bundle."""
    from .singularity import verify_evidence_bundle_integrity

    if not bundle_file.exists():
        typer.echo(f"error: bundle file not found: {bundle_file}")
        raise typer.Exit(2)
    try:
        data = json.loads(bundle_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("bundle JSON must be an object")
    except (ValueError, OSError) as exc:
        typer.echo(f"error: invalid bundle JSON: {exc}")
        raise typer.Exit(2) from None

    ok = verify_evidence_bundle_integrity(data)
    typer.echo(
        json.dumps(
            {
                "bundle_valid": ok,
                "overall_compliant": bool(data.get("overall_compliant", False)),
                "bundle_sha256": data.get("bundle_sha256"),
                "node_id": data.get("node_id"),
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    if not ok or not data.get("overall_compliant", False):
        raise typer.Exit(3)


@micro_node_app.command("compliance-pack")
def micro_node_compliance_pack(
    node_id: Annotated[
        str,
        typer.Option("--node-id", help="Operator identifier for this SPEACE Micro Node."),
    ] = "speace-micro-local",
    seeds: Annotated[
        str,
        typer.Option("--seeds", help="Comma-separated deterministic integer seeds."),
    ] = "11,23,37,53",
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Optional path to write the T240 Annex IV JSON pack."),
    ] = None,
) -> None:
    """Export a SHA-256 verifiable T240 Annex IV / NIST / ISO 42001 compliance readiness pack."""
    from .singularity import build_annex_iv_compliance_pack

    try:
        parsed_seeds = tuple(int(s.strip()) for s in seeds.split(",") if s.strip())
        if not parsed_seeds:
            raise ValueError("at least one integer seed is required")
    except ValueError as exc:
        typer.echo(f"error: invalid --seeds value: {exc}")
        raise typer.Exit(2) from None

    pack = build_annex_iv_compliance_pack(node_id=node_id, seeds=parsed_seeds, output_path=output)
    summary = {
        "spec": pack.spec,
        "schema_version": pack.schema_version,
        "node_id": pack.node_id,
        "genome_sha256": pack.genome_sha256,
        "pack_sha256": pack.pack_sha256,
        "overall_technical_readiness": pack.overall_technical_readiness,
        "legal_certification_granted": pack.legal_certification_granted,
        "ce_marking_granted": pack.ce_marking_granted,
        "self_approval_permitted": pack.self_approval_permitted,
        "mcp_actuation_permitted": pack.mcp_actuation_permitted,
        "control_count": len(pack.regulatory_control_matrix),
        "risk_count": len(pack.risk_register),
        "privacy_by_default_check": pack.privacy_by_default_check,
        "sbom_summary": pack.sbom_summary,
    }
    typer.echo(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    if not pack.overall_technical_readiness:
        raise typer.Exit(3)


if __name__ == "__main__":
    main()
