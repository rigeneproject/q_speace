# SPEACE Cognitive Self Observatory

**Document ID:** SPEACE-ARCH-COGNITIVE-OBSERVATORY-001  
**Version:** 1.0  
**Status:** Draft  
**Date:** 2026-06-21  
**Area:** Meta-Cognition / Cognitive Omni-RAG  

---

## 1. Purpose and Scope

SPEACE possesses memory, genome, agents, metrics, and ILF — but lacks a
**unified representation** of:

- *who I am* (current identity state)
- *what I am doing* (active goals and decisions)
- *why I am doing it* (motivation and reasoning chains)
- *what has changed* (evolution trajectory)
- *what consequences my actions had* (causal outcome tracking)

The **Cognitive Self Observatory** is a new organ that provides:

- **Cognitive State Graph** — persistent graph of thoughts, decisions, goals
- **Self Model** — live self-representation updated from all subsystems
- **Narrative Memory** — causally-linked timeline of significant events
- **Cognitive Coherence Index** — composite metric of internal consistency
- **Metacognitive Engine** — decision quality assessment
- **Causal Evolution Graph** — genome-to-behavior causal chains
- **Self Interpretation Engine** — structured explanations of internal events
- **Omni-RAG Integration** — all contexts available in single queries

### 1.1 Design Principle

> This system does NOT simulate consciousness. It provides verifiable,
> auditable self-observation. Every conclusion is traceable to observable
> evidence. The SCI framework is used as a cognitive self-assessment
> methodology, not as a consciousness claim.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COGNITIVE SELF OBSERVATORY                       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SELF MODEL (L2)                          │   │
│  │  identity | goals | constraints | capabilities | weaknesses │   │
│  └─────────────────────────┬───────────────────────────────────┘   │
│                            │                                       │
│  ┌──────────┐ ┌──────────┐┼┌──────────┐ ┌──────────┐ ┌──────────┐│
│  │Cognitive │ │Narrative │││Coherence │ │Meta-    │ │Causal    ││
│  │State     │ │Memory    │││Engine    │ │cognitive │ │Evolution ││
│  │Graph(L1) │ │(L3)      │││(L4)      │ │Engine(L5)│ │Graph(L6) ││
│  └─────┬────┘ └─────┬────┘│└────┬─────┘ └─────┬────┘ └─────┬────┘│
│        │            │     │     │             │            │     │
│        └────────────┴─────┼─────┴─────────────┴────────────┘     │
│                           │                                       │
│              ┌────────────▼────────────┐                         │
│              │ Self Interpretation (L7)│                         │
│              └────────────┬────────────┘                         │
│                           │                                       │
│              ┌────────────▼────────────┐                         │
│              │ Omni-RAG Integration(L8)│                         │
│              └─────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Data Flow

```
External Stimulus / Internal Tick
    │
    ▼
Cognitive State Graph ──▶ Node created (Thought/Decision/Goal/Error)
    │
    ├──▶ Self Model ──────▶ Updated with new state
    │
    ├──▶ Narrative Memory ──▶ If significant, linked event recorded
    │
    ├──▶ Coherence Engine ──▶ Recalculate CCI
    │
    ├──▶ Metacognitive Engine ──▶ Score last decision
    │
    ├──▶ Causal Evolution Graph ──▶ Link to genome/mutation if applicable
    │
    └──▶ Self Interpretation Engine ──▶ Generate structured explanation
    │
    ▼
Omni-RAG Indexer ──▶ All contexts available for query
```

---

## 3. Data Models

### 3.1 Cognitive Node Types (L1)

| NodeType | Description | Created by |
|----------|-------------|-----------|
| `THOUGHT` | Internal cognitive representation | Orchestrator tick |
| `DECISION` | A choice made by the system | Any subsystem |
| `GOAL` | Active objective | Self Model |
| `MEMORY_STATE` | Snapshot of memory system | Memory subsystem |
| `BELIEF` | Internal conviction about state | Inference engine |
| `HYPOTHESIS` | Testable proposition | COR / metacognitive |
| `MUTATION_EVENT` | Evolutionary mutation | Evolution engine |
| `ACTION` | External or internal action | Actuators |
| `ERROR` | Failure or anomaly | Error handlers |
| `LEARNING_EVENT` | Knowledge acquisition | Any learning system |

### 3.2 Cognitive Edge Types (L1)

| Relation | Meaning |
|----------|---------|
| `GENERATED` | Node produced another |
| `CAUSED` | Direct causation |
| `INFLUENCED` | Partial influence |
| `CONTRADICTED` | Evidence against |
| `SUPPORTED` | Evidence for |
| `CORRECTED` | Error correction |
| `LEARNED_FROM` | Learning source |
| `PRECEDED` | Temporal ordering |

### 3.3 Self Model (L2)

```python
class SelfModel:
    identity: dict           # From DNA identity
    active_goals: list       # Current objectives
    active_constraints: list # Active invariants
    capabilities: dict       # Available capabilities with confidence
    known_weaknesses: list   # Recurring error patterns
    known_errors: list       # Recent errors
    blind_spots: list        # Areas not yet explored
    genome_state: dict       # Current genome expression
    ilf_state: dict          # Current ILF metrics
    bcel_coverage: dict      # BCEL translation completeness
    last_updated: float      # Timestamp
```

### 3.4 Narrative Event (L3)

```python
class NarrativeEvent:
    id: str
    timestamp: float
    event_type: str           # "mutation", "decision", "error", "learning", etc.
    description: str          # Human-readable summary
    interpretation: str       # Why it happened
    consequence: str          # What resulted
    learning: str             # What was learned
    causal_parents: list[str] # IDs of preceding events
    evidence_refs: list[str]  # References to evidence nodes
    ilf_delta: float          # Change in ILF after event
    cci_delta: float          # Change in CCI after event
```

### 3.5 Cognitive Coherence Index — CCI (L4)

```python
CCI = w1 * C_memory + w2 * C_identity + w3 * C_reasoning
    + w4 * C_learning + w5 * C_prediction + w6 * C_traceability
```

| Component | Meaning | Data Source |
|-----------|---------|-------------|
| `C_memory` | Coherence between memories and events | Narrative Memory |
| `C_identity` | Coherence with Species Orientation | DNA + Self Model |
| `C_reasoning` | Coherence between decisions and goals | Cognitive State Graph |
| `C_learning` | Ability to learn from errors | Metacognitive Engine |
| `C_prediction` | Prediction accuracy (belief vs outcome) | Metacognitive Engine |
| `C_traceability` | Explainability of decisions | Self Interpretation Engine |

### 3.6 Metacognitive Score (L5)

```python
class MetacognitiveScore:
    decision_id: str
    confidence: float         # 0..1
    accuracy: float            # 0..1 (if outcome known)
    context_completeness: float # 0..1
    evidence_quality: float    # 0..1
    hypotheses_considered: int
    subsequent_errors: int
    prediction_outcome_diff: float  # |predicted - actual|
    timestamp: float
```

### 3.7 Causal Evolution Edge Types (L6)

| Relation | Meaning |
|----------|---------|
| `EXPRESSED_AS` | Gene → RNA |
| `LED_TO` | Decision → Action |
| `PRODUCED` | Action → Outcome |
| `CHANGED_ILF` | Outcome → ILF delta |
| `TRIGGERED_LEARNING` | Outcome → Learning Event |
| `RESULTED_IN_MUTATION` | Learning → Genome change |

### 3.8 Self Interpretation (L7)

```python
class SelfInterpretation:
    event_id: str
    what: str                  # What happened
    why: str                   # Why it happened
    contributing_factors: list # What contributed
    supporting_evidence: list  # Evidence references
    learning: str              # What emerged from this
    coherence_impact: float    # Effect on CCI
    recommendation: str        # What to do next time
```

---

## 4. Module Structure

```
speace_core/cognitive_observatory/
├── __init__.py
├── models.py                        # All data models
├── cognitive_state_graph.py         # L1 — Cognitive State Graph
├── self_model.py                    # L2 — Self Model
├── narrative_memory.py              # L3 — Narrative Memory
├── coherence_engine.py              # L4 — CCI Calculator
├── metacognitive_engine.py          # L5 — Decision Quality
├── causal_evolution_graph.py        # L6 — Causal Chains
├── self_interpretation_engine.py    # L7 — Self Explanations
├── observatory.py                   # Ties all levels together
├── cli_commands.py                  # CLI for this organ
└── persistence/
    ├── __init__.py
    └── observatory_store.py         # JSONL persistence
```

---

## 5. CLI Commands

```
speace self-model                Show current self model
speace cognitive-audit           Run cognitive coherence audit
speace metacognitive-audit       Run metacognitive quality audit
speace narrative-timeline        Show narrative event timeline
speace causal-trace NODE_ID      Causal trace from a node
speace coherence-report          Full CCI report with time series
```

---

## 6. Omni-RAG Integration

### 6.1 New Collectors

```python
speace_core/omni_rag/collectors/
├── cognitive_state_collector.py  # Reads CognitiveStateGraph
├── narrative_collector.py        # Reads NarrativeMemory
├── self_model_collector.py       # Reads SelfModel
└── metacognitive_collector.py    # Reads MetacognitiveEngine
```

### 6.2 New Node Types in Omni-RAG

- `THOUGHT`, `DECISION`, `GOAL`, `BELIEF`, `HYPOTHESIS`, `ERROR`
- `LEARNING_EVENT`, `NARRATIVE_EVENT`

### 6.3 Extended Query Contexts

Every Omni-RAG query can now retrieve:

- `cognitive_state_context` — cognitive state graph matches
- `narrative_context` — narrative timeline events
- `self_model_context` — current self model snapshot
- `metacognitive_context` — decision quality scores

---

## 7. BCEL Equivalence

| Phase | Value |
|-------|-------|
| Biological structure | Prefrontal cortex — executive control, self-monitoring, metacognition |
| Preserved function | Internal self-observation, error detection, behavioral regulation |
| Accidental (removed) | Slow neural conduction, limited working memory capacity, emotional interference |
| Functional (kept) | Recursive self-evaluation, prediction-outcome comparison, causal learning |
| Digital synthesis | Cognitive State Graph + Self Model + Narrative Memory + Coherence/ Metacognitive Engines |
| Integration | Registered in BCEL catalog as `cognitive_self_observatory` |

---

## 8. Acceptance Criteria

1. Every important decision is explainable via Self Interpretation Engine
2. Every mutation has causal traceability (genome → effect → learning)
3. Every learning event is recorded in Narrative Memory
4. Every error generates actionable knowledge
5. Self Model updates automatically on each orchestration tick
6. System produces verifiable self-assessments (CCI, Metacognitive Score)
7. System identifies internal contradictions (e.g., belief vs evidence mismatch)
8. Integration with DNA, BCEL, ILF, and Omni-RAG is functional
9. CLI commands return structured, auditable output
10. No metaphysical claims — all output references observable evidence

---

## 9. Roadmap

### Phase 1 — Foundation
- [x] Architecture specification
- [ ] Data models (all 8 levels)
- [ ] CognitiveStateGraph with persistence
- [ ] SelfModel with auto-update
- [ ] NarrativeMemory with causal linking

### Phase 2 — Intelligence
- [ ] CoherenceEngine (CCI computation)
- [ ] MetacognitiveEngine (decision scoring)
- [ ] CausalEvolutionGraph (genome→behavior chains)
- [ ] SelfInterpretationEngine (structured explanations)

### Phase 3 — Integration
- [ ] CLI commands (7 commands)
- [ ] Omni-RAG collectors (4 new collectors)
- [ ] Extended query engine
- [ ] BCEL registration

### Phase 4 — Hardening
- [ ] Full test suite
- [ ] Longitudinal tracking (30-day evolution reports)
- [ ] Performance optimization
- [ ] Integration tests with real orchestrator ticks

---

*End of specification — SPEACE Cognitive Self Observatory v1.0*
