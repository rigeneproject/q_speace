import asyncio
import pathlib
from typing import Optional

import typer

from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator

app = typer.Typer(name="speace", help="SPEACE Cellular Brain CLI")

SPEACE_VERSION = "0.1.0"


def _default_genome_path() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent / "dna" / "genome" / "default_genome.yaml"


@app.command()
def version() -> None:
    """Show SPEACE version."""
    typer.echo(f"speace-core {SPEACE_VERSION}")


@app.command()
def status(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
) -> None:
    """Show SPEACE system status."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    identity = getattr(genome, "identity", {}) or {}
    species = getattr(identity, "species_name", "SPEACE")
    stage = getattr(identity, "developmental_stage", "unknown")
    typer.echo(f"System: {species}")
    typer.echo(f"Version: {SPEACE_VERSION}")
    typer.echo(f"Stage: {stage}")
    typer.echo(f"Genome: {genome_path.name}")
    typer.echo("Status: ready")


@app.command()
def audit(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
    ticks: int = typer.Option(10, "--ticks", "-t", help="Number of audit ticks"),
) -> None:
    """Run a quick system audit."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    orchestrator = CellularBrainOrchestrator.build_mvp(genome)

    async def _run() -> None:
        typer.echo("Starting audit...")
        await orchestrator.run_ticks(ticks)
        metrics = orchestrator.latest_metrics
        if metrics:
            typer.echo(f"Tick: {metrics.tick}")
            typer.echo(f"Coherence Phi: {metrics.coherence_phi:.4f}")
            typer.echo(f"Mean Energy: {metrics.mean_energy:.4f}")
            typer.echo(f"Active Neurons: {metrics.active_neurons}")
            typer.echo(f"Pruned Synapses: {metrics.pruned_synapses}")
        typer.echo("Audit complete.")

    asyncio.run(_run())


@app.command()
def run_mvp(
    ticks: int = typer.Option(1000, "--ticks", "-t", help="Number of ticks to run"),
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
    patterns: int = typer.Option(100, "--patterns", "-p", help="Training patterns"),
) -> None:
    """Run the SPEACE MVP cellular brain."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    orchestrator = CellularBrainOrchestrator.build_mvp(genome)

    async def _run() -> None:
        typer.echo(f"Starting SPEACE MVP for {ticks} ticks...")
        for i in range(patterns):
            pattern = [0.0] * 10
            pattern[i % 10] = 1.0
            orchestrator.inject(pattern)
            await orchestrator.run_ticks(1)
            score = 1.0 if i % 2 == 0 else -0.2
            orchestrator.feedback(score)
            if i % 10 == 0:
                orchestrator.run_immune()
            metrics = orchestrator.latest_metrics
            if metrics:
                typer.echo(
                    f"Tick {metrics.tick:04d} | "
                    f"Phi={metrics.coherence_phi:.3f} | "
                    f"Energy={metrics.mean_energy:.3f} | "
                    f"Active={metrics.active_neurons} | "
                    f"Pruned={metrics.pruned_synapses}"
                )
        # final burn-in
        await orchestrator.run_ticks(ticks - patterns)
        final = orchestrator.latest_metrics
        if final:
            typer.echo("\n=== Final Metrics ===")
            typer.echo(f"Tick: {final.tick}")
            typer.echo(f"Coherence Phi: {final.coherence_phi:.4f}")
            typer.echo(f"Mean Energy: {final.mean_energy:.4f}")
            typer.echo(f"Active Neurons: {final.active_neurons}")
            typer.echo(f"Pruned Synapses: {final.pruned_synapses}")

    asyncio.run(_run())


if __name__ == "__main__":
    app()
