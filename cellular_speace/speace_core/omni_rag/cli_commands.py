"""CLI commands for the SPEACE Cognitive Omni-RAG system.

These commands are registered into the main 'speace' CLI app from cli.py.
"""

import json
import pathlib
import time
from typing import Optional

import typer

from speace_core.omni_rag import (
    CognitiveGraph,
    OmniIndexer,
    OmniQueryEngine,
    OmniAuditor,
    OmniQuery,
    LayerFilter,
    AuditType,
)

omni_app = typer.Typer(
    name="omni",
    help="SPEACE Cognitive Omni-RAG — unified knowledge infrastructure",
    no_args_is_help=True,
)


def _get_indexer() -> OmniIndexer:
    graph = CognitiveGraph()
    return OmniIndexer(graph=graph)


def _get_engine(indexer: Optional[OmniIndexer] = None) -> OmniQueryEngine:
    if indexer is None:
        graph = CognitiveGraph()
    else:
        graph = indexer.graph
    return OmniQueryEngine(graph=graph)


# ------------------------------------------------------------------ #
# speace omni-index
# ------------------------------------------------------------------ #


@omni_app.command()
def index(
    force: bool = typer.Option(False, "--force", "-f", help="Rebuild index from scratch"),
    no_semantic: bool = typer.Option(False, "--no-semantic", help="Skip semantic indexing"),
    no_arch: bool = typer.Option(False, "--no-arch", help="Skip architectural graph"),
    no_dna: bool = typer.Option(False, "--no-dna", help="Skip DNA graph"),
    no_bcel: bool = typer.Option(False, "--no-bcel", help="Skip BCEL graph"),
    no_runtime: bool = typer.Option(False, "--no-runtime", help="Skip runtime collection"),
    no_infant: bool = typer.Option(
        False, "--no-infant",
        help="Skip Cognitive Infant SensorBus (T173) — observation-only nodes",
    ),
    output: Optional[pathlib.Path] = typer.Option(
        None, "--output", "-o", help="Output directory for index",
    ),
) -> None:
    """Build or refresh the cognitive graph from all data sources."""
    indexer = _get_indexer()

    typer.echo("Building SPEACE Cognitive Omni-RAG index...")
    start = time.perf_counter()

    stats = indexer.index_all(
        semantic=not no_semantic,
        arch=not no_arch,
        dna=not no_dna,
        bcel=not no_bcel,
        runtime=not no_runtime,
        infant=not no_infant,
        force=force,
    )

    elapsed = time.perf_counter() - start
    typer.echo(f"\n=== Index Complete ===")
    typer.echo(f"  Nodes:     {stats['total_nodes']}")
    typer.echo(f"  Edges:     {stats['total_edges']}")
    typer.echo(f"  New nodes: {stats['new_nodes']}")
    typer.echo(f"  New edges: {stats['new_edges']}")
    typer.echo(f"  Time:      {stats['elapsed_seconds']:.2f}s")
    typer.echo(f"  Layers:    {', '.join(k for k, v in stats['layers'].items() if v)}")


# ------------------------------------------------------------------ #
# speace omni-query
# ------------------------------------------------------------------ #


@omni_app.command()
def query(
    text: str = typer.Argument("", help="Search query text"),
    layers: str = typer.Option(
        "semantic,arch,dna,bcel,runtime",
        "--layers", "-l",
        help="Comma-separated layers: semantic,arch,dna,bcel,runtime",
    ),
    node_type: Optional[str] = typer.Option(
        None, "--node-type", "-t",
        help="Filter by node type",
    ),
    depth: int = typer.Option(3, "--depth", "-d", help="Graph traversal depth"),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results"),
    output_format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Query the cognitive graph across all layers."""
    layer_map = {
        "semantic": LayerFilter.SEMANTIC,
        "arch": LayerFilter.ARCH,
        "dna": LayerFilter.DNA,
        "bcel": LayerFilter.BCEL,
        "runtime": LayerFilter.RUNTIME,
    }

    selected = []
    for name in layers.split(","):
        name = name.strip().lower()
        if name in layer_map:
            selected.append(layer_map[name])

    if not selected:
        typer.echo("No valid layers specified. Use: semantic, arch, dna, bcel, runtime")
        raise typer.Exit(1)

    engine = _get_engine()

    q = OmniQuery(
        text=text,
        layers=selected,
        max_depth=depth,
        limit=limit,
    )

    if node_type:
        try:
            from speace_core.omni_rag.models import NodeType
            q.node_types = [NodeType(node_type)]
        except ValueError:
            typer.echo(f"Invalid node type: {node_type}")
            raise typer.Exit(1)

    result = engine.query(q)

    if output_format == "json":
        typer.echo(result.model_dump_json(indent=2))
        return

    # Text output
    typer.echo(f"\n=== Query Results: {text or '(all)'} ===")
    typer.echo(f"  Total: {result.total_count} nodes, {len(result.edges)} edges")
    typer.echo(f"  Latency: {result.latency_ms}ms")
    typer.echo(f"  Layers: {', '.join(l.value for l in selected)}")
    typer.echo(f"  Depth: {depth}")
    typer.echo("")

    if result.explanation:
        typer.echo(f"  {result.explanation}")
        typer.echo("")

    if result.nodes:
        typer.echo("  Nodes:")
        for i, node in enumerate(result.nodes[:limit]):
            tags = f" [{', '.join(node.tags[:3])}]" if node.tags else ""
            loc = f" @ {node.source_path}" if node.source_path else ""
            typer.echo(f"    {i+1:3d}. [{node.node_type.value:16s}] {node.name}{tags}{loc}")
    else:
        typer.echo("  No matching nodes found.")

    if result.paths:
        typer.echo(f"\n  Connection paths: {len(result.paths)}")
        for i, path in enumerate(result.paths[:5]):
            path_desc = " -> ".join(e.relation.value for e in path)
            typer.echo(f"    Path {i+1}: {path_desc}")


# ------------------------------------------------------------------ #
# speace omni-audit
# ------------------------------------------------------------------ #


@omni_app.command()
def audit(
    audit_type: str = typer.Option(
        "all", "--type", "-t",
        help="Audit type: arch, bcel, dna, runtime, cognitive_factors, all",
    ),
    output: Optional[pathlib.Path] = typer.Option(
        None, "--output", "-o", help="Output file path for JSON report",
    ),
) -> None:
    """Run structural audits against the cognitive graph."""
    type_map = {
        "arch": AuditType.ARCH,
        "bcel": AuditType.BCEL,
        "dna": AuditType.DNA,
        "runtime": AuditType.RUNTIME,
        "cognitive_factors": AuditType.COGNITIVE_FACTORS,
        "all": AuditType.ALL,
    }

    at = type_map.get(audit_type.lower())
    if at is None:
        typer.echo(f"Invalid audit type: {audit_type}. Use: arch, bcel, dna, runtime, cognitive_factors, all")
        raise typer.Exit(1)

    engine = _get_engine()
    auditor = OmniAuditor(engine._graph)
    result = auditor.audit(audit_type=at)

    typer.echo(f"\n=== Audit: {audit_type.upper()} ===")
    typer.echo(f"  Passed:    {result.passed}")
    typer.echo(f"  Findings:  {len(result.findings)}")
    typer.echo(f"  Critical:  {result.summary.get('critical', 0)}")
    typer.echo(f"  Warning:   {result.summary.get('warning', 0)}")
    typer.echo(f"  Info:      {result.summary.get('info', 0)}")
    typer.echo(f"  Duration:  {result.duration_ms:.1f}ms")
    typer.echo("")

    if result.findings:
        typer.echo("  Findings:")
        severities = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
        for i, finding in enumerate(result.findings):
            icon = severities.get(finding.severity, "  ")
            loc = f" [{finding.node_id}]" if finding.node_id else ""
            typer.echo(f"    {i+1:3d}. {icon} [{finding.severity:8s}] {finding.category:30s} {finding.message}{loc}")

    if output:
        output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        typer.echo(f"\n  Report written to: {output}")


# ------------------------------------------------------------------ #
# speace omni-graph
# ------------------------------------------------------------------ #


@omni_app.command()
def graph(
    output_format: str = typer.Option(
        "text", "--format", "-f",
        help="Output format: text, json, or dot",
    ),
    subgraph_query: Optional[str] = typer.Option(
        None, "--subgraph", "-s",
        help="Subgraph filter: node type or ID prefix",
    ),
    output_path: Optional[pathlib.Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path",
    ),
) -> None:
    """Export the cognitive graph for visualization."""
    engine = _get_engine()
    g = engine._graph

    if subgraph_query:
        # Filter by node type or ID prefix
        from speace_core.omni_rag.models import NodeType
        try:
            nt = NodeType(subgraph_query.lower())
            nodes = g.get_nodes_by_type(nt)
            node_ids = {n.id for n in nodes}
            sub = g.get_subgraph(node_ids, depth=1)
        except ValueError:
            # Treat as ID prefix
            node_ids = {n.id for n in g.all_nodes() if subgraph_query.lower() in n.id.lower()}
            sub = g.get_subgraph(node_ids, depth=1)
        g = sub

    all_nodes = g.all_nodes()
    all_edges = g.all_edges()

    if output_format == "json":
        data = {
            "nodes": [n.model_dump() for n in all_nodes],
            "edges": [e.model_dump() for e in all_edges],
            "stats": {"nodes": len(all_nodes), "edges": len(all_edges)},
        }
        output = json.dumps(data, indent=2)
        if output_path:
            output_path.write_text(output, encoding="utf-8")
            typer.echo(f"Graph exported to: {output_path}")
        else:
            typer.echo(output)

    elif output_format == "dot":
        lines = ["digraph SPEACE_Cognitive_Graph {"]
        lines.append("  rankdir=LR;")
        lines.append('  node [shape=box, style=rounded];')

        type_colors = {
            "module": "#4A90D9",
            "class": "#50C878",
            "function": "#FFD700",
            "gene": "#FF6B6B",
            "bcel_mapping": "#9B59B6",
            "constraint": "#E67E22",
            "principle": "#1ABC9C",
            "runtime_event": "#95A5A6",
        }
        for node in all_nodes:
            color = type_colors.get(node.node_type.value, "#CCCCCC")
            label = f"{node.name}\\n({node.node_type.value})"
            lines.append(f'  "{node.id}" [label="{label}", fillcolor="{color}", style="filled,rounded"];')

        for edge in all_edges:
            lines.append(f'  "{edge.source_id}" -> "{edge.target_id}" [label="{edge.relation.value}"];')

        lines.append("}")
        output = "\n".join(lines)

        if output_path:
            output_path.write_text(output, encoding="utf-8")
            typer.echo(f"DOT graph exported to: {output_path}")
        else:
            typer.echo(output)

    else:
        # Text summary
        node_types = {}
        for n in all_nodes:
            node_types[n.node_type.value] = node_types.get(n.node_type.value, 0) + 1

        relation_types = {}
        for e in all_edges:
            relation_types[e.relation.value] = relation_types.get(e.relation.value, 0) + 1

        typer.echo(f"\n=== Cognitive Graph ===")
        typer.echo(f"  Total nodes: {len(all_nodes)}")
        typer.echo(f"  Total edges: {len(all_edges)}")
        typer.echo("")
        typer.echo("  Nodes by type:")
        for nt_name, count in sorted(node_types.items(), key=lambda x: -x[1]):
            typer.echo(f"    {nt_name:20s}: {count:4d}")
        typer.echo("")
        typer.echo("  Edges by relation:")
        for rt_name, count in sorted(relation_types.items(), key=lambda x: -x[1])[:10]:
            typer.echo(f"    {rt_name:20s}: {count:4d}")


# ------------------------------------------------------------------ #
# speace omni-impact
# ------------------------------------------------------------------ #


@omni_app.command()
def impact(
    node_id: str = typer.Argument(..., help="Node ID to analyze"),
    depth: int = typer.Option(3, "--depth", "-d", help="Traversal depth"),
) -> None:
    """Analyze impact of changing a node (forward trace)."""
    engine = _get_engine()
    result = engine.get_impact_analysis(node_id, depth=depth)

    typer.echo(f"\n=== Impact Analysis: {node_id} ===")
    typer.echo(f"  {result.explanation}")
    typer.echo(f"  Latency: {result.latency_ms}ms")
    typer.echo("")

    if result.nodes:
        typer.echo("  Affected nodes:")
        for i, node in enumerate(result.nodes):
            typer.echo(f"    {i+1:3d}. [{node.node_type.value:16s}] {node.name}")
    else:
        typer.echo("  No impact paths found.")


# ------------------------------------------------------------------ #
# speace omni-root-cause
# ------------------------------------------------------------------ #


@omni_app.command()
def root_cause(
    node_id: str = typer.Argument(..., help="Node ID to trace"),
    depth: int = typer.Option(5, "--depth", "-d", help="Traversal depth"),
) -> None:
    """Trace backward from a node to find root causes."""
    engine = _get_engine()
    result = engine.get_root_cause_analysis(node_id, depth=depth)

    typer.echo(f"\n=== Root Cause Analysis: {node_id} ===")
    typer.echo(f"  {result.explanation}")
    typer.echo(f"  Latency: {result.latency_ms}ms")
    typer.echo("")

    if result.nodes:
        typer.echo("  Upstream nodes:")
        for i, node in enumerate(result.nodes):
            typer.echo(f"    {i+1:3d}. [{node.node_type.value:16s}] {node.name}")
    else:
        typer.echo("  No upstream nodes found.")


# ------------------------------------------------------------------ #
# speace omni-status
# ------------------------------------------------------------------ #


@omni_app.command()
def status() -> None:
    """Show Omni-RAG indexing status and graph statistics."""
    engine = _get_engine()
    g = engine._graph

    node_counts = {}
    for node in g.all_nodes():
        nt = node.node_type.value
        node_counts[nt] = node_counts.get(nt, 0) + 1

    edge_counts = {}
    for edge in g.all_edges():
        rt = edge.relation.value
        edge_counts[rt] = edge_counts.get(rt, 0) + 1

    typer.echo(f"\n=== Omni-RAG Status ===")
    typer.echo(f"  Total nodes: {g.node_count()}")
    typer.echo(f"  Total edges: {g.edge_count()}")
    typer.echo("")
    typer.echo("  Nodes by type:")
    for nt, count in sorted(node_counts.items(), key=lambda x: -x[1])[:15]:
        typer.echo(f"    {nt:20s}: {count:4d}")
    typer.echo("")
    typer.echo("  Edges by relation (top 10):")
    for rt, count in sorted(edge_counts.items(), key=lambda x: -x[1])[:10]:
        typer.echo(f"    {rt:20s}: {count:4d}")


# ------------------------------------------------------------------ #
# speace omni-telescope
# ------------------------------------------------------------------ #


@omni_app.command()
def telescope(
    output_format: str = typer.Option(
        "text", "--format", "-f",
        help="Output format: text or json",
    ),
    output: Optional[pathlib.Path] = typer.Option(
        None, "--output", "-o",
        help="Write JSON snapshot to this file",
    ),
) -> None:
    """Print the Cognitive Factors Telescope (10 read-only probes).

    Wraps `scripts/print_cognitive_telescope.py` so the same probes
    exercised by `tests/cognitive_factors/test_telescope_units.py` are
    reachable from the SPEACE CLI.
    """
    import subprocess
    import sys

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "print_cognitive_telescope.py"

    if not script.exists():
        typer.echo(f"Telescope script not found at: {script}")
        raise typer.Exit(1)

    cmd = [sys.executable, str(script), "--format", "json"]
    completed = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    if completed.returncode != 0:
        typer.echo(f"Telescope script failed:\n{completed.stderr}")
        raise typer.Exit(1)

    payload = json.loads(completed.stdout)

    if output_format == "json":
        typer.echo(json.dumps(payload, indent=2))
        if output:
            output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            typer.echo(f"  Snapshot written to: {output}")
        return

    # Text output — mirror the script's layout for operator parity.
    factors = payload.get("factors", {})
    typer.echo("\n=== Cognitive Factors Telescope ===")
    typer.echo(f"  Timestamp: {payload.get('timestamp')}")
    typer.echo("")
    for name in sorted(factors.keys()):
        f = factors[name]
        lo, hi = f.get("healthy_range", [0, 0])
        typer.echo(
            f"  {name:14s} = {f.get('value'):>10}  healthy [{lo}, {hi}]  [{f.get('tag')}]"
        )
