"""Q-SPEACE command-line interface (task T16).

Groups:
  - ``qspace quantum ...`` — quantum experiments and tools
  - ``qspace sia ...`` — self-improvement cortex controls
"""
from __future__ import annotations

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

app = typer.Typer(help="Q-SPEACE quantum layer CLI")
quantum_app = typer.Typer(help="Quantum experiments and tools")
sia_app = typer.Typer(help="Self-Improvement Cortex (SIA)")
app.add_typer(quantum_app, name="quantum")
app.add_typer(sia_app, name="sia")


@quantum_app.command("run")
def quantum_run(
    ticks: int = typer.Option(10, "--ticks", "-t"),
    neurons: int = typer.Option(4, "--neurons", "-n"),
    earth: bool = typer.Option(False, "--earth/--no-earth"),
) -> None:
    """Run the quantum orchestrator for N ticks."""
    genome = QuantumGeneSet(enabled=True, qubits_per_neuron=1)
    orch = QuantumOrchestrator(
        genome=genome,
        neurons=[f"neuron_{i}" for i in range(neurons)],
        enable_earth=earth,
    )
    orch.enable_qca(num_cells=neurons)
    report = orch.run(ticks=ticks)
    print(f"[green]Ran {len(report)} ticks[/green]")
    print(orch.report())


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
    print(
        "[green]cross-scale emergence:[/green]"
        f" {'YES' if noisy > base else 'NO'}"
    )


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
            print(f"tick={i}: proposals={report.proposals} selected={report.selected} "
                  f"mutations={report.mutations_applied} rollbacks={report.rollbacks}")
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
        print(f"  [{r.mutation_id}] level={r.level} target={r.target} "
              f"confidence={r.confidence:.2f} active={r.active}")


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
        "--strategies", "-s",
    ),
) -> None:
    """Test the Quantum Evolution Engine with sample strategies."""
    from .self_improvement_cortex import QuantumEvolutionEngine

    parsed = json.loads(strategies)
    engine = QuantumEvolutionEngine()
    results = engine.propose_candidates(parsed, {})
    print(f"QEE proposed {len(results)} candidates:")
    for r in results:
        print(f"  [{r.method}] id={r.candidate_id} score={r.score:.3f} confidence={r.confidence:.3f}")


@app.command()
def version() -> None:
    """Print package version."""
    from importlib.metadata import version as _v

    print(_v("q-speace"))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
