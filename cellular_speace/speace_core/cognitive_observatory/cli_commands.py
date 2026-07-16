"""CLI commands for the SPEACE Cognitive Self Observatory.

These commands are registered into the main 'speace' CLI app from cli.py.
"""

import json
import time
from typing import Optional

import typer

from speace_core.cognitive_observatory.observatory import CognitiveObservatory

obs_app = typer.Typer(
    name="cognitive",
    help="SPEACE Cognitive Self Observatory — meta-cognition layer",
    no_args_is_help=True,
)


def _get_observatory() -> CognitiveObservatory:
    return CognitiveObservatory()


# ------------------------------------------------------------------ #
# speace cognitive self-model
# ------------------------------------------------------------------ #


@obs_app.command()
def self_model(
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Show the current self-model (identity, goals, capabilities)."""
    obs = _get_observatory()
    summary = obs.self_model.get_self_summary()

    if format == "json":
        typer.echo(json.dumps(summary, indent=2, default=str))
        return

    typer.echo("\n=== Self Model ===")
    typer.echo(f"  Identity:   {summary.get('identity_name', 'unknown')}")
    typer.echo(f"  Consistency: {summary.get('consistency', 0.5):.3f}")
    typer.echo(f"  Goals:      {', '.join(summary.get('active_goals', [])) or 'none'}")
    typer.echo(f"  Constraints: {', '.join(summary.get('active_constraints', [])) or 'none'}")
    typer.echo(f"  Capabilities:")
    for name, conf in summary.get("capabilities", {}).items():
        typer.echo(f"    {name:30s}: {conf:.3f}")
    typer.echo(f"  Weaknesses: {', '.join(summary.get('known_weaknesses', [])) or 'none'}")
    typer.echo(f"  Blind spots: {', '.join(summary.get('blind_spots', [])) or 'none'}")
    typer.echo(f"  Recent errors: {summary.get('recent_errors', 0)}")
    if summary.get("ilf_summary"):
        typer.echo(f"  ILF: {summary['ilf_summary']}")


# ------------------------------------------------------------------ #
# speace cognitive cognitive-audit
# ------------------------------------------------------------------ #


@obs_app.command()
def cognitive_audit(
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Run a comprehensive cognitive audit across all observatory levels."""
    obs = _get_observatory()
    audit = obs.get_full_cognitive_audit()

    if format == "json":
        typer.echo(json.dumps(audit, indent=2, default=str))
        return

    typer.echo("\n=== Cognitive Audit ===")
    typer.echo(f"  CCI:          {audit.get('cci', 0.0):.4f}")
    typer.echo(f"  CCI Trend:    {audit.get('cci_trend', 0.0):+.4f}")

    cci_comp = audit.get("cci_components", {})
    if cci_comp:
        typer.echo("  CCI Components:")
        for key in ["c_memory", "c_identity", "c_reasoning", "c_learning", "c_prediction", "c_traceability"]:
            val = cci_comp.get(key, 0.0)
            typer.echo(f"    {key:20s}: {val:.4f}")

    self_sum = audit.get("self_summary", {})
    typer.echo(f"  Self:        {self_sum.get('identity_name', 'unknown')} / goals: {len(self_sum.get('active_goals', []))}")

    meta = audit.get("metacognitive", {})
    if meta:
        typer.echo(f"  Metacognitive:")
        typer.echo(f"    Confidence:    {meta.get('average_confidence', 0):.4f}")
        typer.echo(f"    Accuracy:      {meta.get('average_accuracy', 0):.4f}")
        typer.echo(f"    Calibration:   {meta.get('calibration_error', 0):.4f}")

    sg = audit.get("state_graph", {})
    if sg:
        typer.echo(f"  State Graph:  {sg.get('nodes', 0)} nodes, {sg.get('edges', 0)} edges, error rate {sg.get('error_rate', 0):.3f}")

    narr = audit.get("narrative_events", {})
    if narr:
        typer.echo(f"  Narrative:    {sum(narr.values())} total events")
        for etype, count in narr.items():
            typer.echo(f"    {etype}: {count}")

    understanding = audit.get("self_understanding", {})
    if understanding:
        typer.echo(f"  Self Understanding:")
        typer.echo(f"    Interpretations:  {understanding.get('recent_interpretations', 0)}")
        typer.echo(f"    Learning rate:    {understanding.get('learning_extracted', 0)}")
        typer.echo(f"    Avg CCI impact:   {understanding.get('avg_coherence_impact', 0):.4f}")


# ------------------------------------------------------------------ #
# speace cognitive metacognitive-audit
# ------------------------------------------------------------------ #


@obs_app.command()
def metacognitive_audit(
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Show detailed metacognitive metrics (calibration, accuracy)."""
    obs = _get_observatory()
    report = obs.metacognitive.get_comprehensive_metacognitive_report()

    if format == "json":
        typer.echo(json.dumps(report, indent=2, default=str))
        return

    typer.echo("\n=== Metacognitive Audit ===")
    typer.echo(f"  Average confidence:      {report.get('average_confidence', 0):.4f}")
    typer.echo(f"  Average accuracy:        {report.get('average_accuracy', 0):.4f}")
    typer.echo(f"  Calibration error:       {report.get('calibration_error', 0):.4f}")
    typer.echo(f"  Context completeness:    {report.get('average_context_completeness', 0):.4f}")
    typer.echo(f"  Recent decisions scored: {report.get('recent_decisions', 0)}")

    patterns = report.get("recurring_error_patterns", [])
    if patterns:
        typer.echo("  Recurring error patterns:")
        for p in patterns:
            typer.echo(f"    {p.get('subsystem', '?'):20s}: {p.get('error_count', 0)} errors")


# ------------------------------------------------------------------ #
# speace cognitive narrative-timeline
# ------------------------------------------------------------------ #


@obs_app.command()
def narrative_timeline(
    limit: int = typer.Option(20, "--limit", "-n", help="Max events to show"),
    event_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by event type (mutation, decision, error, learning, adaptation)",
    ),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Show the narrative timeline of significant events."""
    obs = _get_observatory()
    events = obs.get_narrative_timeline(limit=limit, event_type=event_type)

    if format == "json":
        typer.echo(json.dumps(events, indent=2, default=str))
        return

    typer.echo(f"\n=== Narrative Timeline ({len(events)} events) ===")
    for i, ev in enumerate(events):
        ts = time.strftime("%H:%M:%S", time.localtime(ev.get("timestamp", 0)))
        typer.echo(f"  {i+1:3d}. [{ts}] [{ev.get('type', '?'):12s}] {ev.get('description', '')[:80]}")
        if ev.get("interpretation"):
            typer.echo(f"       Why: {ev['interpretation'][:80]}")
        if ev.get("learning"):
            typer.echo(f"       Learned: {ev['learning'][:80]}")


# ------------------------------------------------------------------ #
# speace cognitive causal-trace
# ------------------------------------------------------------------ #


@obs_app.command()
def causal_trace(
    node_id: str = typer.Argument(..., help="Node ID to trace"),
    direction: str = typer.Option(
        "upstream", "--direction", "-d",
        help="Direction: upstream (causes) or downstream (effects)",
    ),
    depth: int = typer.Option(5, "--depth", help="Max trace depth"),
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Trace causal chains upstream (causes) or downstream (effects)."""
    obs = _get_observatory()
    result = obs.causal_trace(node_id, direction=direction, depth=depth)

    if format == "json":
        typer.echo(json.dumps(result, indent=2, default=str))
        return

    typer.echo(f"\n=== Causal Trace: {direction} from {node_id} ===")
    typer.echo(f"  {result.get('description', '')}")
    typer.echo("")
    for node in result.get("nodes", []):
        typer.echo(f"  [{node.get('type', '?'):16s}] {node.get('name', '')}")
    if result.get("edges"):
        typer.echo(f"\n  Relations ({len(result['edges'])}):")
        for e in result["edges"]:
            typer.echo(f"    {e.get('source', '')} --[{e.get('relation', '')}]--> {e.get('target', '')}")


# ------------------------------------------------------------------ #
# speace cognitive coherence-report
# ------------------------------------------------------------------ #


@obs_app.command()
def coherence_report(
    format: str = typer.Option(
        "text", "--format", "-f", help="Output format: text or json",
    ),
) -> None:
    """Show detailed CCI coherence report with trend."""
    obs = _get_observatory()
    report = obs.get_coherence_report()

    if format == "json":
        typer.echo(json.dumps(report, indent=2, default=str))
        return

    typer.echo("\n=== Coherence Report ===")
    typer.echo(f"  Current CCI:       {report.get('current_cci', 0.0):.4f}")
    typer.echo(f"  Trend (last 20):   {report.get('cci_trend_20', 0.0):+.4f}")
    typer.echo(f"  Trend (last 50):   {report.get('cci_trend_50', 0.0):+.4f}")

    history = report.get("cci_history", [])
    if history:
        typer.echo(f"\n  CCI History (last {len(history)} snapshots):")
        for entry in history[-10:]:
            ts = time.strftime("%H:%M:%S", time.localtime(entry.get("timestamp", 0)))
            comp = entry.get("components", {})
            typer.echo(
                f"    [{ts}] value={entry.get('value', 0):.4f} "
                f"mem={comp.get('memory', 0):.3f} "
                f"id={comp.get('identity', 0):.3f} "
                f"reas={comp.get('reasoning', 0):.3f} "
                f"learn={comp.get('learning', 0):.3f} "
                f"pred={comp.get('prediction', 0):.3f} "
                f"trace={comp.get('traceability', 0):.3f}"
            )
