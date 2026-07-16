"""T172 — Information Value Collector for the Omni-RAG.

Bridges the new ``speace_core.cellular_brain.information_value`` package
into the cognitive graph. It exposes:

- :class:`InformationValueCollector` — produces nodes for H_local, V, π(a|s,V)
- An audit helper :func:`motivation_audit` that runs a structural audit
  against the produced graph and reports coverage gaps.

Mapping to DNA
--------------
The collector does NOT modify the genome. It produces PRINCIPLE nodes
pointing at the *informational principles* of ``species_orientation.yaml``
that the Information Value module operationalizes, and DRIVE / POLICY
nodes that mirror the runtime behaviour.

Mapping to BCEL
---------------
- The collector emits ``BCEL_MAPPING`` nodes for the four new equivalences:
  motivational_dopaminergic_loop, curiosity_rnd_signal,
  free_energy_active_inference, inverted_u_value_function.

Safety
------
This is a read-only observer. It does not execute the policy, only
records its proposals.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional, Tuple

import structlog

from speace_core.cellular_brain.information_value import (
    InformationalValueFunction,
    PerceivedEntropyModule,
    ExplorationPolicy,
)
from speace_core.cellular_brain.information_value.exploration_policy import (
    ActionProposal,
)
from speace_core.cellular_brain.information_value.value_function import (
    ValueBreakdown,
)
from speace_core.omni_rag.models import (
    CognitiveEdge,
    CognitiveNode,
    NodeType,
    RelationType,
)

logger = structlog.get_logger(__name__)


class InformationValueCollector:
    """Builds the Information Value subgraph of the cognitive graph."""

    # Mapping of new BCEL equivalences that this module introduces.
    BCEL_EQUIVALENCES = (
        {
            "name": "motivational_dopaminergic_loop",
            "biological_form": "dopaminergic reward prediction error",
            "kept_constraints": ("value_based_action_selection",),
            "digital_implementation": "ExplorationPolicy",
        },
        {
            "name": "curiosity_rnd_signal",
            "biological_form": "Random Network Distillation novelty signal",
            "kept_constraints": ("pseudo_count_bonus", "rnd_bonus"),
            "digital_implementation": "EndogenousExplorationBonus",
        },
        {
            "name": "free_energy_active_inference",
            "biological_form": "Friston free-energy principle",
            "kept_constraints": ("minimize_expected_free_energy",),
            "digital_implementation": "ActiveInferenceEngine + ActiveInferenceEmbodiedLoop",
        },
        {
            "name": "inverted_u_value_function",
            "biological_form": "Yerkes-Dodson inverted-U arousal-performance curve",
            "kept_constraints": ("sweet_spot_at_boundary",),
            "digital_implementation": "InformationalValueFunction",
        },
    )

    def __init__(
        self,
        entropy_module: Optional[PerceivedEntropyModule] = None,
        value_function: Optional[InformationalValueFunction] = None,
        exploration_policy: Optional[ExplorationPolicy] = None,
    ) -> None:
        self.entropy_module = entropy_module or PerceivedEntropyModule()
        self.value_function = value_function or InformationalValueFunction()
        self.exploration_policy = exploration_policy or ExplorationPolicy()

    # ------------------------------------------------------------------ #
    # Snapshot collection
    # ------------------------------------------------------------------ #

    def collect_snapshot(
        self,
        signals: Dict[str, float],
        state: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        """Collect one snapshot: H_local → V → π."""
        snap = self.entropy_module.observe(signals)
        # Derive phase-space components from signals
        novelty = signals.get("novelty", 0.5)
        predictability = 1.0 - signals.get("prediction_error", 0.5)
        compressibility = 1.0 - signals.get("informational_entropy", 0.5)
        V, bd = self.value_function.evaluate(novelty, predictability, compressibility)
        proposal = self.exploration_policy.propose(state or {}, V)

        return self._materialize(snap, bd, proposal)

    # ------------------------------------------------------------------ #
    # Graph materialization
    # ------------------------------------------------------------------ #

    def _materialize(
        self,
        snap,
        bd: ValueBreakdown,
        proposal: ActionProposal,
    ) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        ts = time.time()
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        # 1) PerceivedEntropy node
        ent_id = f"iv.perceived_entropy.{int(ts * 1000)}"
        nodes.append(
            CognitiveNode(
                id=ent_id,
                node_type=NodeType.METRIC,
                name="perceived_entropy",
                description="Aggregated perceived entropy H_local(t)",
                source_path="speace_core/cellular_brain/information_value/perceived_entropy.py",
                metadata={
                    "H_local": round(snap.H_local, 6),
                    "components": {k: round(v, 6) for k, v in snap.components.items()},
                    "module": "PerceivedEntropyModule",
                },
                tags=("iv_module", "T172", "perceived_entropy"),
                created_at=ts,
                updated_at=ts,
            )
        )

        # 2) Value breakdown node
        val_id = f"iv.value_function.{int(ts * 1000)}"
        nodes.append(
            CognitiveNode(
                id=val_id,
                node_type=NodeType.METRIC,
                name="informational_value",
                description="Inverted-U informational value V(novelty, predictability, compressibility)",
                source_path="speace_core/cellular_brain/information_value/value_function.py",
                metadata=bd.to_dict(),
                tags=("iv_module", "T172", "informational_value"),
                created_at=ts,
                updated_at=ts,
            )
        )

        # 3) Proposal / decision node
        prop_id = f"iv.action_proposal.{int(ts * 1000)}"
        nodes.append(
            CognitiveNode(
                id=prop_id,
                node_type=NodeType.DECISION,
                name=f"proposal:{proposal.kind.value}",
                description=f"π(a|s,V) proposal with rationale: {proposal.rationale}",
                source_path="speace_core/cellular_brain/information_value/exploration_policy.py",
                metadata=proposal.to_dict(),
                tags=("iv_module", "T172", "exploration_policy"),
                created_at=ts,
                updated_at=ts,
            )
        )

        # 4) BCEL mapping nodes
        for eq in self.BCEL_EQUIVALENCES:
            bcel_id = f"bcel.{eq['name']}"
            nodes.append(
                CognitiveNode(
                    id=bcel_id,
                    node_type=NodeType.BCEL_MAPPING,
                    name=eq["name"],
                    description=f"{eq['biological_form']} → {eq['digital_implementation']}",
                    source_path="speace_core/omni_rag/collectors/information_value_collector.py",
                    metadata={
                        "biological_form": eq["biological_form"],
                        "kept_constraints": list(eq["kept_constraints"]),
                        "digital_implementation": eq["digital_implementation"],
                    },
                    tags=("bcel", "iv_module", "T172"),
                    created_at=ts,
                    updated_at=ts,
                )
            )

        # Edges
        edges.append(
            CognitiveEdge(
                source_id=ent_id,
                target_id=val_id,
                relation=RelationType.TRIGGERS,
                metadata={"mapping": "H_local → V input component"},
            )
        )
        edges.append(
            CognitiveEdge(
                source_id=val_id,
                target_id=prop_id,
                relation=RelationType.REGULATES,
                metadata={"mapping": "V → π(a|s,V) input"},
            )
        )
        for eq in self.BCEL_EQUIVALENCES:
            bcel_id = f"bcel.{eq['name']}"
            edges.append(
                CognitiveEdge(
                    source_id=bcel_id,
                    target_id=prop_id,
                    relation=RelationType.IMPLEMENTS,
                    metadata={"equivalence": eq["name"]},
                )
            )

        return nodes, edges


# ---------------------------------------------------------------------- #
# Audit
# ---------------------------------------------------------------------- #


def motivation_audit(graph) -> Dict[str, object]:
    """Run a structural audit of the motivation subsystem against the graph.

    Checks:
      - At least one PRINCIPLE node referencing ``informational_principles``
        from species_orientation.yaml.
      - At least one METRIC node of ``perceived_entropy`` or ``H_local``.
      - At least one METRIC node of ``informational_value``.
      - At least one DECISION node of ``proposal:``.
      - At least one BCEL_MAPPING node for each of the 4 new equivalences.
      - At least one REGULATES edge from a value node to a decision node.

    Returns a structured report.
    """
    required_bcel = {eq["name"] for eq in InformationValueCollector.BCEL_EQUIVALENCES}

    # The CognitiveGraph exposes ``get_nodes_by_type`` and ``all_nodes``.
    # We use the by-type accessor where possible because it is faster and
    # works for both freshly-built and on-disk-loaded graphs.
    def _nodes_of(nt):
        getter = getattr(graph, "get_nodes_by_type", None)
        if callable(getter):
            try:
                return getter(nt) or []
            except Exception:
                return list(getattr(graph, "all_nodes", lambda: [])())
        return list(getattr(graph, "nodes", {}).values())

    principles = _nodes_of(NodeType.PRINCIPLE)
    metrics = _nodes_of(NodeType.METRIC)
    decisions = _nodes_of(NodeType.DECISION)
    bcels = _nodes_of(NodeType.BCEL_MAPPING)

    def _has_tag(n: CognitiveNode, tag: str) -> bool:
        if tag in (n.name or ""):
            return True
        # Strict tag match — use " in tags" boundaries to avoid the
        # "informational_value" ⊂ "information_value" collision.
        return tag in (n.tags or [])

    perceived_present = any(
        _has_tag(n, "perceived_entropy") or _has_tag(n, "H_local")
        for n in metrics
    )
    value_present = any(_has_tag(n, "informational_value") for n in metrics)
    decision_present = any(_has_tag(n, "proposal:") for n in decisions)

    bcel_present = {
        eq.name: any(_has_tag(n, eq.name) for n in bcels)
        for eq in (
            type("E", (), {"name": n}) for n in required_bcel
        )
    }

    regulates_edges = list(getattr(graph, "all_edges", lambda: [])())
    regulates_edges = [e for e in regulates_edges if e.relation == RelationType.REGULATES]
    v_to_decision = any(
        (e.source_id or "").startswith("iv.value_function.")
        and (e.target_id or "").startswith("iv.action_proposal.")
        for e in regulates_edges
    )

    report = {
        "principles_count": len(principles),
        "metrics_count": len(metrics),
        "decisions_count": len(decisions),
        "bcels_count": len(bcels),
        "perceived_entropy_present": perceived_present,
        "informational_value_present": value_present,
        "proposal_present": decision_present,
        "bcel_coverage": bcel_present,
        "v_to_decision_edge_present": v_to_decision,
        "missing_bcel": [k for k, v in bcel_present.items() if not v],
    }
    report["pass"] = (
        perceived_present
        and value_present
        and decision_present
        and all(bcel_present.values())
        and v_to_decision
    )
    return report
