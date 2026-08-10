"""Q-SPEACE command-line interface (task T16).

Groups:
  - ``qspace quantum ...`` — quantum experiments and tools
  - ``qspace sia ...`` — self-improvement cortex controls
  - ``qspace brain ...`` — SpikingBrain satellite (T205)
"""

from __future__ import annotations

import asyncio
import json

import typer

from .bcel import BCELCatalog
from .earth_feed import EarthFeed
from .fractal_qca_cascade import experiment_cross_scale, qi_bridge_cqasm
from .genome import QuantumGeneSet
from .orchestrator import QuantumOrchestrator
from .quantum.backends import to_cqasm
from .schumann import run_schumann, schumann_circuit
from .self_improvement_cortex import SelfImprovementCortex
from .spiking_brain import SpikingBrainCortex

app = typer.Typer(help="Q-SPEACE quantum layer CLI")
quantum_app = typer.Typer(help="Quantum experiments and tools")
sia_app = typer.Typer(help="Self-Improvement Cortex (SIA)")
brain_app = typer.Typer(help="SpikingBrain satellite (T205)")
app.add_typer(quantum_app, name="quantum")
app.add_typer(sia_app, name="sia")
app.add_typer(brain_app, name="brain")


@quantum_app.command("run")
def quantum_run(
    ticks: int = typer.Option(10, "--ticks", "-t"),
    neurons: int = typer.Option(4, "--neurons", "-n"),
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
    orch.enable_qca(num_cells=neurons)
    report = orch.run(ticks=ticks)
    print(f"[green]Ran {len(report)} ticks[/green]")
    print(orch.report())
    if radio:
        last = report[-1]
        print(f"[cyan]Last TX:[/cyan] {last.tx_report}")
        print(
            f"[cyan]Spectrum:[/cyan] snr={last.spectrum.snr_db:.1f} dB rssi={last.spectrum.rssi_dbm:.1f} dBm"
        )


@quantum_app.command("benchmark")
def quantum_benchmark(
    qubits: int = typer.Option(4, "--qubits", "-q"),
    ticks: int = typer.Option(10, "--ticks", "-t"),
    backend: str = typer.Option("numpy", "--backend", "-b"),
) -> None:
    """Run the Schumann-resonance benchmark experiment."""
    from .quantum.backends import build

    build(backend)  # validates backend selection / fallback
    result = run_schumann(num_qubits=qubits, ticks=ticks)
    print(f"[cyan]Backend:[/cyan] {backend}")
    print(f"[cyan]Mean coherence:[/cyan] {result['mean_coherence']:.4f}")
    print(f"[cyan]Coherence trace:[/cyan] {result['coherence_trace']}")


@quantum_app.command("synthesize")
def quantum_synthesize() -> None:
    """List BCEL quantum equivalences (biological->cybernetic)."""
    catalog = BCELCatalog()
    for eq in catalog.all():
        print(f"[yellow]{eq.concept}[/yellow] -> {eq.classification}")
        print(f"  {eq.digital_rule}")


@quantum_app.command("cqasm")
def quantum_cqasm(
    qubits: int = typer.Option(4, "--qubits", "-q"),
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
    print(to_cqasm(circ, version=version))


@quantum_app.command("bridge")
def quantum_bridge(
    atom_coherence: float = typer.Option(0.5, "--atom", "-a"),
    brain_seed: float = typer.Option(0.5, "--brain", "-b"),
    version: str = typer.Option("3.0", "--version", "-v"),
) -> None:
    """Print a 5-qubit QI bridge circuit (phi_bridge + cross-scale coupling)."""
    print(qi_bridge_cqasm(atom_coherence, brain_seed, version=version))


@quantum_app.command("cross-scale")
def quantum_cross_scale(
    ticks: int = typer.Option(20, "--ticks", "-t"),
    atom_noise: float = typer.Option(0.2, "--noise", "-n"),
) -> None:
    """Run the cross-scale emergence experiment (bottom-up noise proof)."""
    base, noisy = experiment_cross_scale(ticks=ticks, atom_noise=atom_noise)
    print(f"[cyan]brain sigma (baseline):[/cyan] {base:.4f}")
    print(f"[cyan]brain sigma (atom-noise):[/cyan] {noisy:.4f}")
    print("[green]cross-scale emergence:[/green]" f" {'YES' if noisy > base else 'NO'}")


@sia_app.command("run")
def sia_run(
    ticks: int = typer.Option(10, "--ticks", "-t"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run the Self-Improvement Cortex for N ticks."""
    cortex = SelfImprovementCortex()
    for i in range(ticks):
        report = cortex.tick({"coherence_phi": 0.7, "plasticity_index": 0.5})
        if verbose:
            print(
                f"tick={i}: proposals={report.proposals} selected={report.selected} "
                f"mutations={report.mutations_applied} rollbacks={report.rollbacks}"
            )
    print(cortex.report())


@sia_app.command("status")
def sia_status() -> None:
    """Print current SIA status summary."""
    cortex = SelfImprovementCortex()
    report = cortex.report()
    for k, v in report.items():
        print(f"  {k}: {v}")


@sia_app.command("dna")
def sia_dna(
    limit: int = typer.Option(10, "--limit", "-l"),
) -> None:
    """List recent DNA mutation records."""
    cortex = SelfImprovementCortex()
    records = cortex.dna.recent(limit)
    print(f"DNA mutation records (last {len(records)}):")
    for r in records:
        print(
            f"  [{r.mutation_id}] level={r.level} target={r.target} "
            f"confidence={r.confidence:.2f} active={r.active}"
        )


@sia_app.command("benchmark")
def sia_benchmark(
    min_qubits: int = typer.Option(4, "--min-qubits", "-q"),
    max_qubits: int = typer.Option(20, "--max-qubits", "-Q"),
    trials: int = typer.Option(2, "--trials", "-t"),
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
    print(f"QEE proposed {len(results)} candidates:")
    for r in results:
        print(
            f"  [{r.method}] id={r.candidate_id} score={r.score:.3f} confidence={r.confidence:.3f}"
        )


@app.command()
def version() -> None:
    """Print package version."""
    from importlib.metadata import version as _v

    print(_v("q-speace"))


# ----------------------------------------------------------------------
# SpikingBrain satellite (T205)
# ----------------------------------------------------------------------


def _run_coro(coro):  # pragma: no cover — trivial wrapper
    return asyncio.run(coro)


@brain_app.command("think")
def brain_think(
    prompt: str = typer.Argument(..., help="Prompt for the SpikingBrain area."),
    tokens: int = typer.Option(32, "--tokens", "-n", help="Max new tokens."),
    coherence: float = typer.Option(1.0, "--coherence", "-c", help="Initial ILF coherence_phi."),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty text."),
) -> None:
    """Send one prompt to the SpikingBrain satellite and print the result.

    Uses the stub backend unless ``Q_SPEACE_BRAIN_ENDPOINT`` is set.
    """
    from .edd_cvt.ilf import InformationalLogicalField

    ilf = InformationalLogicalField(coherence_phi=coherence)
    cortex = SpikingBrainCortex(ilf=ilf)

    async def run() -> object:
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
        typer.echo(f"[green]backend:[/green] {cortex.backend_name}")
        typer.echo(f"[cyan]text:[/cyan] {result.text}")
        typer.echo(f"[cyan]belief:[/cyan] {[round(float(x), 3) for x in result.belief]}")
        typer.echo(f"[cyan]confidence:[/cyan] {result.confidence:.3f}")
        typer.echo(
            f"[cyan]spikes:[/cyan] num={result.spikes.num_spikes} "
            f"sparsity={result.spikes.sparsity:.2f}"
        )
        typer.echo(f"[cyan]plasticity:[/cyan] {[round(float(x), 3) for x in result.plasticity]}")


@brain_app.command("tick")
def brain_tick(
    prompt: str = typer.Argument(..., help="Prompt for the cognitive step."),
    tokens: int = typer.Option(32, "--tokens", "-n"),
    coherence: float = typer.Option(1.0, "--coherence", "-c"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Run one full sense-decide-act step (think + cost + gate + ILF apply)."""
    from .edd_cvt.ilf import InformationalLogicalField

    ilf = InformationalLogicalField(coherence_phi=coherence)
    cortex = SpikingBrainCortex(ilf=ilf)

    async def run() -> object:
        return await cortex.tick(prompt, n_tokens=tokens)

    report = _run_coro(run())
    typer.echo(f"[green]backend:[/green] {report.backend}")
    typer.echo(f"[cyan]approved:[/cyan] {report.approved}")
    typer.echo(f"[cyan]reason:[/cyan] {report.reason}")
    typer.echo(f"[cyan]sevo:[/cyan] {report.sevo:.3f}")
    typer.echo(f"[cyan]energy_w:[/cyan] {report.energy_w:.3f}")
    typer.echo(f"[cyan]confidence:[/cyan] {report.confidence:.3f}")
    if verbose and report.result is not None:
        typer.echo(f"[cyan]text:[/cyan] {report.result.text}")


@brain_app.command("health")
def brain_health() -> None:
    """Check the SpikingBrain satellite health."""
    cortex = SpikingBrainCortex()

    async def run() -> dict:
        return await cortex.health()

    h = _run_coro(run())
    typer.echo(json.dumps(h, indent=2))


@brain_app.command("chat")
def brain_chat(
    coherence: float = typer.Option(1.0, "--coherence", "-c", help="Initial ILF coherence_phi."),
    max_turns: int = typer.Option(
        16, "--turns", "-t", help="Max turns before the REPL auto-quits."
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
    from .spiking_brain import make_spiking_brain

    ilf = InformationalLogicalField(coherence_phi=coherence)
    if backend == "stub":
        from .spiking_brain import StubSpikingBrain

        chosen = StubSpikingBrain()
    else:
        chosen = make_spiking_brain()
    cortex = SpikingBrainCortex(ilf=ilf, backend=chosen)

    typer.echo(f"[brain] backend={cortex.backend_name} coherence={coherence:.2f}")
    typer.echo("[brain] type 'q' to quit, empty enter to end")
    for i in range(max_turns):
        try:
            prompt = typer.prompt(f"[turn {i + 1}/{max_turns}] you")
        except (EOFError, KeyboardInterrupt):
            typer.echo("")
            break
        if prompt.strip().lower() in {"q", "quit", "exit"}:
            break
        if not prompt.strip():
            break

        try:
            report = _run_coro(cortex.tick(prompt, history=cortex._history or None))
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


if __name__ == "__main__":
    main()
