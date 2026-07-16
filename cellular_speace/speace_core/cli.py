import asyncio
import datetime
import pathlib
from typing import Optional

import typer

from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.bcel import BCELCatalog, CyberneticSynthesizer, BiologicalComponent
from speace_core.bcel import ConstraintStressTester
from speace_core.digital_rna.transcriptor import DigitalTranscriptor
from speace_core.epigenetics.epigenetic_tags import EpigeneticTagsManager
from speace_core.omni_rag.cli_commands import omni_app
from speace_core.cognitive_observatory.cli_commands import obs_app


app = typer.Typer(name="speace", help="SPEACE Cellular Brain CLI")
app.add_typer(omni_app, name="omni", help="Cognitive Omni-RAG — unified knowledge infrastructure")
app.add_typer(obs_app, name="cognitive", help="Cognitive Self Observatory — meta-cognition layer")

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
    species = getattr(identity, "entity_name", "SPEACE")
    stage = getattr(identity, "nature", "unknown")
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
def ignite(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
    warmup: int = typer.Option(60, "--warmup", "-w", help="Warmup stimulation patterns"),
    sustain: int = typer.Option(200, "--sustain", "-s", help="Sustain ticks (keep-alive)"),
) -> None:
    """Accende e avvia cervello + organismo (ILF integrato, sblocco stallo)."""
    from speace_core.bootstrap.ignition import OrganismIgnition

    igniter = OrganismIgnition(
        genome_path=genome_path,
        warmup_patterns=warmup,
        sustain_ticks=sustain,
    )
    rep = igniter.ignite()
    for line in rep["log"]:
        typer.echo(line)
    typer.echo("\n=== Stato Organismo ===")
    typer.echo(f"Vivo: {rep['alive']}")
    typer.echo(f"Tick: {rep['tick']}")
    phi = rep["coherence_phi"]
    typer.echo(f"Coherence Phi: {phi:.4f}" if phi is not None else "Coherence Phi: n/a")
    en = rep["mean_energy"]
    typer.echo(f"Mean Energy: {en:.4f}" if en is not None else "Mean Energy: n/a")
    typer.echo(f"Active Neurons: {rep['active_neurons']}")
    typer.echo(f"Systemic Coherence Index: {rep['systemic_coherence_index']:.4f}")
    ilf = rep["ilf_value"]
    typer.echo(f"ILF Value: {ilf:.4f}" if ilf is not None else "ILF Value: n/a")
    typer.echo(f"Sottosistemi nel campo: {', '.join(rep['field_subsystems'])}")
    typer.echo(f"Snapshot persistiti: {rep['snapshots_persisted']}")


@app.command()
def live(
    cycle_interval: float = typer.Option(
        300.0, "--cycle-interval", "-c", help="Secondi tra i cicli del team non-LLM"
    ),
    tick_interval: float = typer.Option(
        1.0, "--tick-interval", "-t", help="Secondi tra i tick del cervello"
    ),
    dashboards: bool = typer.Option(
        False, "--dashboards", help="Avvia anche le dashboard web del daemon"
    ),
) -> None:
    """Avvia cervello/organismo 24/7 + team agentico NON-LLM (auto-miglioramento)."""
    from evolution_daemon.launcher import LiveOrganism
    import asyncio as _asyncio

    organism = LiveOrganism(
        cycle_interval_sec=cycle_interval,
        tick_interval=tick_interval,
        start_dashboards=dashboards,
    )
    try:
        _asyncio.run(organism.run())
    except KeyboardInterrupt:
        typer.echo("Interrotto da tastiera.")


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
        except Exception as exc:
            import logging
            logging.getLogger("speace.cli").warning(
                "Failed to load monitoring_dashboard genome config: %s", exc, exc_info=True
            )

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


@app.command()
def assimilate(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
) -> None:
    """Assimila il sistema Windows (processi, servizi, dispositivi, storage)."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    from speace_core.cellular_brain.system_assimilation import WindowsSystemAssimilator
    from speace_core.cellular_brain.system_assimilation.assimilation_models import SystemAssimilationConfig
    assimilator = WindowsSystemAssimilator(config=SystemAssimilationConfig(
        enable_assimilation=True, allow_wmi_queries=True,
    ))
    report = assimilator.assimilate()
    typer.echo(f"System: {report.system_info.hostname}")
    typer.echo(f"OS: {report.system_info.os_platform} {report.system_info.os_release}")
    typer.echo(f"Arch: {report.system_info.architecture}")
    typer.echo(f"Admin: {report.system_info.is_admin}")
    typer.echo(f"Processes: {report.process_count}")
    typer.echo(f"Services: {report.service_count}")
    typer.echo(f"Devices: {report.device_count}")
    typer.echo("Storage:")
    for d in report.storage_devices:
        size_gb = d.get("size_bytes", 0) / (1024**3)
        free_gb = d.get("free_bytes", 0) / (1024**3)
        typer.echo(f"  {d.get('device_id', '?')}: {free_gb:.1f} GB free / {size_gb:.1f} GB total")
    typer.echo("Assimilation complete.")


@app.command()
def vfs_index(
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
) -> None:
    """Indicizza la root del computer via VFS (senza duplicare file)."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    genome_sa = getattr(genome, "system_assimilation", None)
    if genome_sa is None or not getattr(genome_sa, "enable_vfs", False):
        typer.echo("VFS not enabled in genome. Set system_assimilation.enable_vfs: true")
        raise typer.Exit(1)
    from speace_core.cellular_brain.virtual_file_system import VirtualFileSystemEngine
    from speace_core.cellular_brain.virtual_file_system.vfs_models import VFSConfig, AccessRule, VFSPermission
    rules = []
    for r in getattr(genome_sa, "access_rules", []):
        perms = []
        for p in r.allowed_permissions:
            try:
                perms.append(VFSPermission[p.upper()])
            except KeyError:
                pass
        rules.append(AccessRule(
            rule_id=f"dna_{r.path_prefix}",
            path_prefix=r.path_prefix,
            allowed_permissions=perms,
            allowed=not r.requires_approval or r.approved,
            requires_approval=r.requires_approval,
            approved=r.approved,
        ))
    vfs_config = VFSConfig(
        root_mount_point=getattr(genome_sa, "root_mount_point", "C:\\"),
        speace_install_path=str(pathlib.Path(__file__).parent.parent.resolve()),
        access_rules=rules,
        enable_vfs=True,
    )
    engine = VirtualFileSystemEngine(config=vfs_config)
    result = engine.index_root()
    typer.echo(f"Root: {result['root']}")
    typer.echo(f"Indexed: {result['indexed']} entries")
    typer.echo(f"Errors: {result['errors']}")
    typer.echo(f"Total in index: {result['total_indexed']}")
    typer.echo("VFS index created. Files are NOT duplicated — only metadata mapped.")


@app.command()
def vfs_ls(
    path: str = typer.Argument(".", help="Virtual path to list"),
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
) -> None:
    """Elenca una directory della root via VFS."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    genome_sa = getattr(genome, "system_assimilation", None)
    if genome_sa is None or not getattr(genome_sa, "enable_vfs", False):
        typer.echo("VFS not enabled in genome.")
        raise typer.Exit(1)
    from speace_core.cellular_brain.virtual_file_system import VirtualFileSystemEngine
    from speace_core.cellular_brain.virtual_file_system.vfs_models import VFSConfig, AccessRule, VFSPermission
    rules = []
    for r in getattr(genome_sa, "access_rules", []):
        perms = []
        for p in r.allowed_permissions:
            try:
                perms.append(VFSPermission[p.upper()])
            except KeyError:
                pass
        rules.append(AccessRule(
            rule_id=f"dna_{r.path_prefix}", path_prefix=r.path_prefix,
            allowed_permissions=perms, allowed=not r.requires_approval or r.approved,
            requires_approval=r.requires_approval, approved=r.approved,
        ))
    vfs_config = VFSConfig(
        root_mount_point=getattr(genome_sa, "root_mount_point", "C:\\"),
        speace_install_path=str(pathlib.Path(__file__).parent.parent.resolve()),
        access_rules=rules, enable_vfs=True,
    )
    engine = VirtualFileSystemEngine(config=vfs_config)
    entries = engine.list_directory(path)
    if entries is None:
        typer.echo(f"Permission denied or path not found: {path}")
        raise typer.Exit(1)
    for e in entries:
        kind = "D" if e.get("is_dir") else "F"
        size = e.get("size_bytes", 0)
        name = e.get("name", "?")
        err = e.get("error", "")
        if err:
            typer.echo(f"[{kind}] {name}  ({err})")
        else:
            typer.echo(f"[{kind}] {name}  {size} bytes")


@app.command()
def observe(
    output: str = typer.Option(
        "data/organism_observer/report.json",
        "--output", "-o",
        help="Percorso del file JSON di output",
    ),
    history: Optional[str] = typer.Option(
        None, "--history", "-H",
        help="Carica eventi da un file JSONL storico",
    ),
    live: bool = typer.Option(
        False, "--live", "-l",
        help="Modalità live: resta in ascolto per N secondi",
    ),
    seconds: int = typer.Option(
        60, "--seconds", "-s",
        help="Secondi di ascolto in modalità live",
    ),
) -> None:
    """Analizza la geometria funzionale dell'organismo (OFG).

    Costruisce l'Operational Functional Graph dagli eventi intercettati
    e calcola le metriche topologiche (degree, betweenness, modularità,
    small-world, hub).
    """
    import json
    import time
    from speace_core.organism_observer.event_collector import EventCollector
    from speace_core.organism_observer.functional_graph import FunctionalGraph
    from speace_core.organism_observer.topology_metrics import TopologyMetrics

    collector = EventCollector(persist_path=output.replace(".json", ".jsonl"))

    if history:
        n = collector.load_history(history)
        typer.echo(f"Caricati {n} eventi da {history}")

    if live:
        try:
            # Tenta di agganciarsi all'organismo in esecuzione
            from speace_core.orchestrator import CellularBrainOrchestrator

            from speace_core.cellular_brain.organism.organism_bus import OrganismBus

            typer.echo(f"Ascolto live per {seconds}s...")
            bus = OrganismBus()
            collector.wrap(bus)
            # Simula qualche evento per test
            import uuid
            from datetime import datetime, timezone
            from speace_core.cellular_brain.organism.organism_models import OrganismBusMessage

            start = time.time()
            while time.time() - start < seconds:
                # Poll the event bus state if available
                time.sleep(1)
            typer.echo("Raccolta completata.")
        except ImportError as exc:
            typer.echo(f"Errore: {exc}")
            raise typer.Exit(1) from exc

    collector.flush()
    typer.echo(f"Eventi raccolti: {collector.count()}")

    graph = FunctionalGraph(collector)
    graph.build()
    typer.echo(f"Grafo: {graph.node_count} nodi, {graph.edge_count} archi")

    metrics = TopologyMetrics(graph)
    report = metrics.compute_all()

    report["collector"] = collector.summary()
    report["graph"] = graph.summary()

    dst = output
    pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(dst).write_text(json.dumps(report, indent=2), encoding="utf-8")
    typer.echo(f"Report salvato in {dst}")

    # Stampa riepilogo a schermo
    typer.echo("")
    typer.echo("=== RIEPILOGO GEOMETRIA COGNITIVA ===")
    typer.echo(f"  Nodi:           {report['node_count']}")
    typer.echo(f"  Archi:          {report['edge_count']}")
    typer.echo(f"  Densità:        {report['density']:.4f}")
    typer.echo(f"  Clustering:     {report['avg_clustering']:.4f}")
    typer.echo(f"  Efficienza:     {report['global_efficiency']:.4f}")
    typer.echo(f"  Small-world sigma:  {report['small_world']['sigma']:.4f}")
    typer.echo(f"  Modularità Q:   {report['modularity']['Q']:.4f}")
    typer.echo(f"  Comunità:       {report['modularity']['n_communities']}")
    typer.echo("  Hub (top):")
    for h in report.get("hubs", {}).get("broadcasters", [])[:3]:
        typer.echo(f"    > {h['node']}: out={h['score']:.3f}")



@app.command()
def bcel_catalog() -> None:
    """List known biological-digital equivalences."""
    catalog = BCELCatalog()
    typer.echo("=== BCEL Catalog ===")
    for name in catalog.list_components():
        eq = catalog.get(name)
        if eq is None:
            continue
        typer.echo(f"  {name}")
        typer.echo(f"    function: {eq.preserved_function}")
        typer.echo(f"    digital:  {eq.digital_implementation}")
        kept = [c.name for c in eq.kept_constraints]
        removed = eq.removed_constraints
        typer.echo(f"    kept constraints:    {', '.join(kept) if kept else 'none'}")
        typer.echo(f"    removed constraints: {', '.join(removed) if removed else 'none'}")


@app.command()
def bcel_synthesize(
    component_name: str = typer.Argument(..., help="Biological component name to analyze"),
    function: str = typer.Option("", "--function", "-f", help="Functional description"),
    constraints: list[str] = typer.Option([], "--constraint", "-c", help="Biological constraints"),
) -> None:
    """Run the BCEL synthesizer on a biological component."""
    catalog = BCELCatalog()
    synthesizer = CyberneticSynthesizer(catalog=catalog)
    component = BiologicalComponent(
        name=component_name,
        function=function or "unknown",
        biological_constraints=constraints,
    )
    eq = synthesizer.synthesize(component)
    typer.echo(f"Component: {eq.component_name}")
    typer.echo(f"Preserved function: {eq.preserved_function}")
    typer.echo(f"Digital implementation: {eq.digital_implementation}")
    for c in eq.kept_constraints:
        typer.echo(f"  KEEP (functional): {c.name} -> {c.mathematical_form}")
    for c in eq.removed_constraints:
        typer.echo(f"  DROP (accidental): {c}")


@app.command()
def transcriptome(
    context: str = typer.Option("default", "--context", "-c", help="Operational context key"),
    stress: float = typer.Option(0.5, "--stress", "-s", help="Stress/noise level"),
    energy: float = typer.Option(0.5, "--energy", "-e", help="Energy level"),
    coherence: float = typer.Option(0.5, "--coherence", "-p", help="Coherence phi"),
    genome_path: Optional[pathlib.Path] = typer.Option(None, "--genome", "-g", help="Path to genome YAML"),
) -> None:
    """Generate and display the volatile Digital RNA transcriptome."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)
    tags = EpigeneticTagsManager()
    transcriptor = DigitalTranscriptor(genome, tags)
    context_state = {"stress": stress, "energy": energy, "coherence": coherence}
    t = transcriptor.transcribe(context, context_state)
    typer.echo("=== Digital RNA Transcriptome ===")
    typer.echo(f"Context: {t.context_key}")
    typer.echo(f"Lambda (coherence vs entropy): {t.lambda_coherence_entropy:.3f}")
    typer.echo("Expressed genes:")
    for profile in t.expression_profiles.values():
        typer.echo(f"  {profile.gene_name}: {profile.expression:.3f} ({profile.source})")
    if t.functional_constraints:
        typer.echo("Functional constraints carried:")
        for fc in t.functional_constraints:
            typer.echo(f"  {fc.get('name', 'unknown')}: {fc.get('mathematical_form', 'n/a')}")



@app.command()
def bcel_stress_test(
    constraint_name: str = typer.Argument(..., help="Name of the functional constraint to stress test"),
    metric: str = typer.Option("coherence_variance", "--metric", "-m", help="Metric to compare"),
    ticks: int = typer.Option(20, "--ticks", "-t", help="Ticks per condition"),
    genome_path: Optional[pathlib.Path] = typer.Option(None, "--genome", "-g", help="Path to genome YAML"),
) -> None:
    """Stress-test a functional constraint by relaxing it in the circuit."""
    if genome_path is None:
        genome_path = _default_genome_path()
    genome = load_genome(genome_path)

    from speace_core.bcel.catalog import BCELCatalog
    catalog = BCELCatalog()
    constraint = None
    for eq in [catalog.get(n) for n in catalog.list_components()]:
        if eq is None:
            continue
        for fc in eq.kept_constraints:
            if fc.name == constraint_name:
                constraint = fc
                break
        if constraint is not None:
            break

    if constraint is None:
        typer.echo(f"Constraint '{constraint_name}' not found in BCEL catalog.")
        raise typer.Exit(1)

    from speace_core.bcel.stress_circuit import make_minimal_builder

    known_circuit_constraints = {
        "rate_limiter",
        "short_term_depression",
        "delay_as_lowpass_filter",
        "synaptic_delay_lowpass",
    }
    if constraint.name in known_circuit_constraints:
        builder = make_minimal_builder(constraint.name)
    else:
        def builder():
            return CellularBrainOrchestrator.build_mvp(genome)

    tester = ConstraintStressTester(build_orchestrator=builder)
    result = asyncio.run(tester.run(constraint, metric=metric, ticks=ticks))

    typer.echo(f"=== Stress Test: {constraint_name} ===")
    typer.echo(f"Metric: {result.metric_name}")
    typer.echo(f"Baseline:   {result.baseline_value:.6f}")
    typer.echo(f"Perturbed:  {result.perturbed_value:.6f}")
    typer.echo(f"Change:     {result.relative_change:.2f}x")
    typer.echo(f"Passed:     {result.passed}")
    typer.echo(f"Interpretation: {result.interpretation}")


# ---------------------------------------------------------------------------
# TFTpsp — 33 Problem-Solving Parameters from the Rigene Project
# ---------------------------------------------------------------------------


def _load_tftpsp_library(catalog_path: Optional[pathlib.Path]):
    """Load the TFTpsp catalogue; defaulting to the on-disk one."""
    from speace_core.dna.tftpsp_library import TFTPspGeneLibrary

    if catalog_path is None:
        return TFTPspGeneLibrary.default()
    return TFTPspGeneLibrary.from_file(catalog_path)


@app.command()
def tftpsp_list(
    domain: Optional[str] = typer.Option(
        None, "--domain", "-d", help="Filter by domain tag (e.g. crisis, innovation)"
    ),
    with_bcel: bool = typer.Option(
        False, "--with-bcel", help="Only genes with a BCEL mapping"
    ),
    catalog_path: Optional[pathlib.Path] = typer.Option(
        None, "--catalog", help="Path to a TFTpsp YAML catalogue"
    ),
) -> None:
    """List the 33 TFTpsp genes (optionally filtered)."""
    lib = _load_tftpsp_library(catalog_path)
    if not lib.enabled:
        typer.echo("TFTpsp catalogue is DISABLED in this genome.")
        raise typer.Exit(1)

    genes = lib.all()
    if domain:
        genes = lib.by_domain_tag(domain)
    if with_bcel:
        genes = [g for g in genes if g.bcel_equivalent]

    typer.echo(f"=== TFTpsp Catalogue ({len(genes)} / {len(lib)}) ===")
    for g in genes:
        bcel = f" -> {g.bcel_equivalent}" if g.bcel_equivalent else ""
        typer.echo(
            f"  TFT-{g.tft_index:02d}  {g.short_label:14s}  "
            f"priority={g.priority:.2f}  tags={','.join(g.domain_tags)}{bcel}"
        )


@app.command()
def tftpsp_show(
    gene_id: str = typer.Argument(..., help="Gene id (e.g. tftpsp_023_epshcpe)"),
    catalog_path: Optional[pathlib.Path] = typer.Option(
        None, "--catalog", help="Path to a TFTpsp YAML catalogue"
    ),
) -> None:
    """Show the full record of a TFTpsp gene."""
    lib = _load_tftpsp_library(catalog_path)
    gene = lib.get(gene_id)
    if gene is None:
        typer.echo(f"Gene '{gene_id}' not found in TFTpsp catalogue.")
        raise typer.Exit(1)

    typer.echo(f"=== {gene.short_label} (TFT-{gene.tft_index:02d}) ===")
    typer.echo(f"  id:          {gene.gene_id}")
    typer.echo(f"  full_name:   {gene.name}")
    typer.echo(f"  priority:    {gene.priority:.2f}")
    typer.echo(f"  domain_tags: {', '.join(gene.domain_tags)}")
    typer.echo(f"  bcel:        {gene.bcel_equivalent or 'none'}")
    typer.echo(f"  function:    {gene.function.strip()}")
    typer.echo(f"  mutation_policy.allowed: {gene.mutation_policy.allowed}")
    typer.echo(
        f"  mutation_policy.requires_governance: "
        f"{gene.mutation_policy.requires_governance}"
    )

    if gene.activation_conditions:
        typer.echo("  activation_conditions:")
        for ac in gene.activation_conditions:
            typer.echo(
                f"    - tag={ac.trigger_tag} boost={ac.boost} "
                f"min_signal={ac.min_signal}"
            )
    if gene.epigenetic_mechanisms:
        typer.echo("  epigenetic_mechanisms:")
        for rule in gene.epigenetic_mechanisms:
            typer.echo(
                f"    - tag={rule.tag} effect={rule.effect} "
                f"modifier={rule.modifier}"
            )
    if gene.interactions:
        typer.echo("  interactions:")
        for inter in gene.interactions:
            typer.echo(
                f"    - {inter.relation} {inter.target_gene_id} "
                f"(weight={inter.weight})"
            )
    if gene.constraints:
        typer.echo("  constraints:")
        for c in gene.constraints:
            typer.echo(
                f"    - {c.name}: invariant={c.invariant}"
            )


@app.command()
def tftpsp_express(
    state: list[str] = typer.Option(
        [],
        "--state",
        "-s",
        help="tag=value pairs (e.g. crisis=1.0). May be passed multiple times.",
    ),
    genome_path: Optional[pathlib.Path] = typer.Option(
        None, "--genome", "-g", help="Path to genome YAML"
    ),
    top: int = typer.Option(10, "--top", help="Number of top expressed genes"),
    catalog_path: Optional[pathlib.Path] = typer.Option(
        None, "--catalog", help="Path to a TFTpsp YAML catalogue"
    ),
) -> None:
    """Compute TFTpsp expression levels for a given context state."""
    from speace_core.digital_rna.tftpsp_engine import build_tftpsp_transcriptome

    # Parse --state key=value pairs
    context_state: dict[str, float] = {}
    for pair in state:
        if "=" not in pair:
            typer.echo(f"Invalid --state '{pair}' (expected tag=value)")
            raise typer.Exit(1)
        key, _, raw = pair.partition("=")
        try:
            value = float(raw)
        except ValueError:
            typer.echo(f"Invalid numeric value for --state '{pair}'")
            raise typer.Exit(1) from None
        # Reject NaN/inf to keep the context state well-formed.
        if value != value or value in (float("inf"), float("-inf")):
            typer.echo(f"Invalid numeric value for --state '{pair}' (NaN/inf)")
            raise typer.Exit(1)
        context_state[key.strip()] = value

    lib = _load_tftpsp_library(catalog_path)
    tr = build_tftpsp_transcriptome(lib, context_state)

    typer.echo(f"=== TFTpsp Expression (context={context_state or '{}'}) ===")
    ranked = sorted(
        tr.expression_profiles.values(), key=lambda p: p.expression, reverse=True
    )
    for profile in ranked[:top]:
        typer.echo(
            f"  {profile.gene_name:34s} {profile.expression:.3f}  "
            f"tags={','.join(profile.context_tags)}"
        )
    typer.echo(
        f"  ... ({len(ranked)} total profiles; metadata keys: "
        f"{','.join(tr.metadata.keys())})"
    )


@app.command()
def tftpsp_audit(
    catalog_path: Optional[pathlib.Path] = typer.Option(
        None, "--catalog", help="Path to a TFTpsp YAML catalogue"
    ),
) -> None:
    """Audit the TFTpsp catalogue: gene count, BCEL mappings, mutation policies."""
    lib = _load_tftpsp_library(catalog_path)
    typer.echo("=== TFTpsp Audit ===")
    typer.echo(f"  enabled:           {lib.enabled}")
    typer.echo(f"  gene_count:        {len(lib)}")
    typer.echo(f"  with_bcel:         {len(lib.with_bcel())}")
    typer.echo(f"  emergency_genes:   {[g.gene_id for g in lib.emergency_genes()]}")
    typer.echo(f"  bcel_resolvable:   {len(lib.bcel_resolvable())}")
    locked = [
        g.gene_id for g in lib.all() if not g.mutation_policy.allowed
    ]
    typer.echo(f"  locked_mutations:  {locked}")
    by_priority = lib.by_priority(descending=True)[:3]
    typer.echo(
        "  top_priority:      "
        + ", ".join(f"{g.gene_id}({g.priority})" for g in by_priority)
    )

if __name__ == "__main__":
    app()
