import asyncio
import datetime
import pathlib
from typing import Optional

import typer

from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator

app = typer.Typer(name="speace", help="SPEACE Cellular Brain CLI")

SPEACE_VERSION = "0.9.0"


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


@app.command()
def dashboard() -> None:
    """Launch the SPEACE organismic web dashboard."""
    try:
        from speace_core.dashboard.server import run_server
    except ImportError as exc:
        typer.echo("Error: Flask is not installed.")
        typer.echo("Install it with: pip install \"speace-core[dashboard]\"")
        raise typer.Exit(1) from exc
    typer.echo("Starting SPEACE dashboard at http://127.0.0.1:8080")
    run_server(host="127.0.0.1", port=8080)


@app.command()
def monitor(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
) -> None:
    """Launch the SPEACE Local Organism Monitor (T101)."""
    try:
        import uvicorn
    except ImportError as exc:
        typer.echo("Error: uvicorn is not installed.")
        typer.echo('Install with: pip install "speace-core[monitoring]"')
        raise typer.Exit(1) from exc

    host = "127.0.0.1"
    port = 8787

    if genome_path is None:
        genome_path = (
            pathlib.Path(__file__).resolve().parent
            / "dna"
            / "genome"
            / "monitoring_dashboard.yaml"
        )
    if genome_path.exists():
        try:
            genome = load_genome(genome_path)
            md = getattr(genome, "monitoring_dashboard", {}) or {}
            host = md.get("host", host)
            port = md.get("port", port)
        except Exception:
            pass

    typer.echo(f"Starting SPEACE monitor at http://{host}:{port}")
    uvicorn.run(
        "speace_core.monitoring.dashboard_api:app",
        host=host,
        port=port,
        log_level="info",
    )


@app.command()
def run(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
    tick_interval: float = typer.Option(1.0, "--tick-interval", "-t", help="Seconds between ticks"),
    duration: Optional[float] = typer.Option(
        None, "--duration", "-d", help="Optional runtime duration in seconds (for testing)"
    ),
) -> None:
    """Launch SPEACE controlled continuous runtime + monitor (T109)."""
    try:
        import uvicorn
    except ImportError as exc:
        typer.echo("Error: uvicorn is not installed.")
        typer.echo('Install with: pip install "speace-core[monitoring]"')
        raise typer.Exit(1) from exc

    # Resolve genome
    if genome_path is None:
        genome_path = pathlib.Path(__file__).resolve().parent / "dna" / "genome" / "default_genome.yaml"
    genome = load_genome(genome_path)

    # Build orchestrator and runtime engine
    from speace_core.orchestrator import CellularBrainOrchestrator
    from speace_core.runtime.continuous_runtime_engine import ContinuousRuntimeEngine
    import speace_core.monitoring.dashboard_api as dashboard_module

    orchestrator = CellularBrainOrchestrator.build_mvp(genome)
    runtime = ContinuousRuntimeEngine(
        orchestrator=orchestrator,
        tick_interval=tick_interval,
    )
    dashboard_module._runtime_engine = runtime  # type: ignore[attr-defined]

    async def _start_runtime() -> None:
        result = await runtime.start()
        typer.echo(f"Runtime started: {result['state']} | recovery: {result['recovery']['status']}")
        typer.echo(result.get("resume_narrative", ""))
        if duration is not None:
            typer.echo(f"Running for {duration} seconds...")
            await asyncio.sleep(duration)
            typer.echo("Duration reached. Halting runtime...")
            await runtime.halt()
            await runtime.stop()
            typer.echo("Runtime stopped.")

    # Launch runtime in background and then uvicorn
    async def _main() -> None:
        runtime_task = asyncio.create_task(_start_runtime())
        host = "127.0.0.1"
        port = 8787
        config = uvicorn.Config(
            "speace_core.monitoring.dashboard_api:app",
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())
        await asyncio.wait([runtime_task, server_task], return_when=asyncio.FIRST_COMPLETED)
        server.should_exit = True
        await server_task

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        typer.echo("Interrupted by user.")


@app.command()
def seed(
    repo: Optional[str] = typer.Option(
        None, "--repo", help="GitHub repo URL"
    ),
    branch: str = typer.Option("main", "--branch", help="Git branch"),
    target_dir: Optional[pathlib.Path] = typer.Option(
        None, "--target", help="Installation directory"
    ),
    pairing_token: Optional[str] = typer.Option(
        None, "--pairing-token", help="Token to pair with existing node"
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Skip confirmation prompts"
    ),
) -> None:
    """Bootstrap a new SPEACE node (authorized installation only — T115)."""
    from speace_core.bootstrap import SeedEngine

    engine = SeedEngine(
        repo=repo,
        branch=branch,
        target_dir=target_dir,
        pairing_token=pairing_token,
    )
    result = engine.bootstrap(skip_confirm=yes)
    if result["status"] == "success":
        typer.echo(f"Bootstrap complete. Node ID: {result['node_id']}")
        typer.echo(f"Clone path: {result['clone_path']}")
        typer.echo("Run 'speace monitor' to start in safe mode.")
    elif result["status"] == "aborted":
        typer.echo("Bootstrap aborted by user.")
    else:
        typer.echo(f"Bootstrap failed: {result.get('reason', 'unknown')}")
        for err in result.get("errors", []):
            typer.echo(f"  Error: {err}")


@app.command()
def report(
    lookback: int = typer.Option(24, "--lookback", "-l", help="Hours to look back"),
    output_dir: pathlib.Path = typer.Option(
        "reports/observer", "--output", "-o", help="Output directory"
    ),
    format: str = typer.Option(
        "both", "--format", "-f", help="Output format: json, md, or both"
    ),
) -> None:
    """Generate a T103 observer report from organismic state and history."""
    from speace_core.monitoring.observer_report_generator import ObserverReportGenerator

    generator = ObserverReportGenerator()
    rep = generator.generate(lookback_hours=lookback)

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")

    if format in ("json", "both"):
        json_path = output_dir / f"observer_report_{ts}.json"
        json_path.write_text(rep.model_dump_json(indent=2), encoding="utf-8")
        typer.echo(f"JSON report written to: {json_path}")

    if format in ("md", "both"):
        md_path = output_dir / f"observer_report_{ts}.md"
        md_path.write_text(rep.to_markdown(), encoding="utf-8")
        typer.echo(f"Markdown report written to: {md_path}")

    typer.echo(f"Verdict: {rep.verdict}")
    typer.echo(f"Health Score: {rep.alert_summary.health_score_current:.4f}")
    typer.echo(f"Alerts (critical/warning): {rep.alert_summary.critical_count}/{rep.alert_summary.warning_count}")
    if rep.recommendations:
        typer.echo("Recommendations:")
        for rec in rep.recommendations:
            typer.echo(f"  - [{rec.category}] {rec.message}")


if __name__ == "__main__":
    app()
