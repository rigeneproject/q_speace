# SPEACE Cognitive Omni-RAG Architecture

**Document ID:** SPEACE-ARCH-OMNI-RAG-001  
**Version:** 1.0  
**Status:** Draft  
**Date:** 2026-06-21  
**Area:** Knowledge Infrastructure / Cognitive Retrieval Layer  

---

## 1. Purpose and Scope

SPEACE Cognitive Omni-RAG is an internal knowledge infrastructure that provides
cognitive agents (Codex, Claude, GPT, Gemini, and SPEACE's own cognitive
modules) with a **unified, interrogable view of the entire SPEACE organism**.

The system goes beyond vector retrieval. It integrates five distinct cognitive
planes into a single queryable graph:

| # | Layer | Source Types |
|---|-------|--------------|
| 1 | Semantic Layer | Documentation, Markdown, YAML, code comments, audits, diagnoses |
| 2 | Architectural Graph | Python modules, classes, functions, imports, dependencies |
| 3 | DNA Graph | Genes, RNA transcripts, phenotype rules, ILF metrics |
| 4 | BCEL Graph | Biological principles, BCEL translations, digital mechanisms, tests |
| 5 | Runtime Graph | Events, mutations, errors, decisions, audit trails |

### 1.1 Problem Statement

Current agent context is fragmented:

- Documentation is separate from code
- Code is separate from configuration
- Configuration is separate from runtime state
- Runtime state is separate from BCEL mappings
- BCEL is separate from test coverage

This produces:
- Incomplete context in agent prompts
- Incoherent architectural reasoning
- False positives in automated audits
- High dependency on prompt engineering quality
- Difficulty tracing mutation effects across subsystems

### 1.2 Solution

**Context becomes an infrastructure property, not a prompt property.**

The Omni-RAG represents every entity in SPEACE as a **Cognitive Node** with
typed relationships to other nodes. The fundamental unit is not the file — it
is the **cognitive entity** (gene, RNA, circuit, memory, agent, constraint,
BCEL mapping, ILF metric, mutation, test, runtime event).

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     OMNI QUERY ENGINE                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Semantic  │  │Arch Graph│  │DNA Graph │  │BCEL Graph│  ...   │
│  │Retrieval │  │Retrieval │  │Retrieval │  │Retrieval │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       └──────────────┴──────────────┴──────────────┘           │
│                            │                                    │
│                     ┌──────▼──────┐                            │
│                     │  CORRELATOR │                            │
│                     │  (merge +   │                            │
│                     │   rank)     │                            │
│                     └──────┬──────┘                            │
│                            ▼                                    │
│                    Unified OmniResult                          │
└─────────────────────────────────────────────────────────────────┘
         ▲                      ▲                      ▲
         │                      │                      │
  ┌──────┴──────┐      ┌────────┴────────┐    ┌───────┴───────┐
  │  INDEXER    │      │  COGNITIVE GRAPH │    │ RUNTIME       │
  │ (crawls     │─────▶│  (nodes + edges, │◀───│ COLLECTOR     │
  │  filesystem │      │   persisted as   │    │ (subscribes   │
  │  + genome)  │      │   JSONL, load-   │    │  to EventBus) │
  └─────────────┘      │   into memory)   │    └───────────────┘
                       └──────────────────┘
```

### 2.1 Core Data Flow

1. **Indexing phase** (`speace omni-index`): Crawl codebase, parse structure,
   build cognitive graph, persist to JSONL.
2. **Runtime collection** (continuous): Subscribe to EventBus, capture
   runtime events as graph-annotated nodes.
3. **Query phase** (`speace omni-query`): Accept natural language or
   structured queries, traverse graph across all layers, return unified
   result.
4. **Audit phase** (`speace omni-audit`): Run structural audits against the
   graph (architecture, BCEL coverage, DNA completeness, runtime health).

---

## 3. Data Models

### 3.1 Cognitive Node

The fundamental unit. Every entity in SPEACE is a node.

```python
class CognitiveNode:
    id: str                  # Unique identifier (e.g., "module.orchestrator")
    node_type: NodeType      # Enum: MODULE, CLASS, FUNCTION, GENE, RNA, ...
    name: str                # Human-readable name
    description: str = ""    # Description or docstring
    source_path: str = ""    # File path (if file-backed)
    source_line: int = 0     # Line number in source
    metadata: dict           # Type-specific metadata
    tags: list[str]          # Free-form tags
    created_at: float        # Timestamp
    updated_at: float        # Last update timestamp
```

#### Node Types

| NodeType | Description | Examples |
|----------|-------------|---------|
| `MODULE` | Python module | `speace_core.orchestrator` |
| `CLASS` | Python class | `CellularBrainOrchestrator` |
| `FUNCTION` | Python function | `build_mvp` |
| `GENE` | DNA gene | `memory_consolidation_gene` |
| `RNA` | RNA transcript | `transcriptome.default` |
| `CIRCUIT` | Neural circuit | `default_circuit` |
| `MEMORY` | Memory system | `SemanticMemoryStore` |
| `AGENT` | Cognitive agent | `self_improvement_loop` |
| `CONSTRAINT` | Functional constraint | `synaptic_delay_lowpass` |
| `BCEL_MAPPING` | BCEL equivalence | `DNA-RNA expression` |
| `ILF_METRIC` | ILF metric | `coherence_phi` |
| `MUTATION` | Evolutionary mutation | `mut_001` |
| `TEST` | Test case | `test_orchestrator` |
| `RUNTIME_EVENT` | Runtime event | `tick_1000` |
| `DOCUMENT` | Documentation | `SPEACE_BCEL_DESIGN.md` |
| `CONFIG` | Configuration | `default_genome.yaml` |
| `PRINCIPLE` | Design principle | `species_orientation` |
| `BEHAVIOR` | Emergent behavior | `sleep_consolidation` |
| `METRIC` | Metric/measure | `systemic_entropy` |

### 3.2 Cognitive Edge

Every relationship between nodes is a directed, typed edge.

```python
class CognitiveEdge:
    source_id: str           # Source node ID
    target_id: str           # Target node ID
    relation: RelationType   # Type of relationship
    metadata: dict = {}      # Edge-specific metadata
    weight: float = 1.0      # Relationship strength/confidence
```

#### Relation Types

| RelationType | Meaning | Example |
|-------------|---------|---------|
| `IMPORTS` | Module imports another | `orchestrator IMPORTS dna.parser` |
| `DEPENDS_ON` | Depends on another entity | `GlobalWorkspace DEPENDS_ON Transcriptome` |
| `IMPLEMENTS` | Implements a concept | `BCELMapping IMPLEMENTS BiologicalFunction` |
| `EXTENDS` | Inherits from | `CellularBrainOrchestrator EXTENDS BaseModel` |
| `USES` | Uses at runtime | `Orchestrator USES EventBus` |
| `GENERATES` | Produces output | `Gene EXPRESSES RNA` |
| `VALIDATES` | Validates entity | `Constraint VALIDATES Mutation` |
| `MUTATES` | Mutates entity | `Evolution MUTATES Genome` |
| `EXPRESSES` | Gene expression | `Gene EXPRESSES RNA` |
| `REGULATES` | Regulation | `Epigenome REGULATES Gene` |
| `DEFINES` | Defines concept | `Doc DEFINES Principle` |
| `REFERENCES` | References entity | `Doc REFERENCES Class` |
| `CONTAINS` | Container relationship | `Module CONTAINS Class` |
| `TRIGGERS` | Causation | `Mutation TRIGGERS Behavior` |
| `CORRELATES_WITH` | Correlation | `ILFMetric CORRELATES_WITH Behavior` |
| `TRANSLATED_TO` | BCEL translation | `BiologicalPrinciple TRANSLATED_TO DigitalMechanism` |
| `BELONGS_TO` | Membership | `Class BELONGS_TO Module` |
| `AUDITS` | Auditing | `OmniAudit AUDITS Module` |

### 3.3 OmniQuery

A query that can span all five layers.

```python
class OmniQuery:
    text: str                          # Natural language query
    layers: list[LayerFilter]          # Which layers to search
    node_filters: dict = {}            # Filter by node properties
    relation_filters: list = []        # Filter by relation paths
    max_depth: int = 3                 # Graph traversal depth
    limit: int = 50                    # Max results
    semantic_weight: float = 0.3       # Weight for semantic results
    graph_weight: float = 0.5          # Weight for graph results
    runtime_weight: float = 0.2        # Weight for runtime results
```

### 3.4 OmniResult

Unified result from the query engine.

```python
class OmniResult:
    query: OmniQuery
    nodes: list[CognitiveNode]          # Matched nodes
    paths: list[list[CognitiveEdge]]    # Paths between matched nodes
    semantic_scores: dict[str, float]   # Node ID -> relevance score
    graph_scores: dict[str, float]      # Node ID -> graph centrality
    runtime_evidence: list               # Runtime events for context
    audit_summary: dict | None          # Audit results (if audit query)
    explanation: str                    # Human-readable explanation
```

---

## 4. Layer Specifications

### 4.1 Layer 1 — Semantic Layer

**Purpose:** Full-text indexing of all SPEACE textual resources.

**Data sources:**
- All `.md` files in `docs/`, `reports/`
- All `.py` files in `speace_core/` (docstrings and comments)
- All `.yaml` / `.yml` files in `speace_core/dna/genome/`
- All `.json` / `.jsonl` audit trail files in `data/`
- `diagnosi_speace.md` and other diagnostic documents

**Index structure:**
```
semantic_index/
├── documents/           # Per-file document records
│   └── {doc_id}.json   # Metadata + content hash
├── chunks/              # Text chunks with embeddings
│   └── {chunk_id}.json
└── keyword_index.json   # Inverted keyword index
```

**Retrieval strategy:**
1. Tokenize query into keywords
2. Rank documents by TF-IDF relevance
3. Return top-K document chunks with scores
4. Link to graph nodes via `REFERENCES` edges

**Output:** `semantic_context` — ranked list of relevant text passages with
source provenance and graph node links.

### 4.2 Layer 2 — Architectural Graph

**Purpose:** Represent the full structural dependency graph of SPEACE.

**Data sources (indexing):**
- Python AST parsing of all `speace_core/` modules
- Import statements → `IMPORTS` edges
- Class definitions → `CLASS`, `CONTAINS`, `EXTENDS`, `BELONGS_TO`
- Function definitions → `FUNCTION`, `BELONGS_TO`
- Pydantic model inspections (field types reference other models)
- Call chain analysis (optional, depth-limited)

**Graph invariants:**
- Every Python module is a node with `IMPORTS` edges to its dependencies
- Every class is a node with `BELONGS_TO` its module
- Every function is a node with `BELONGS_TO` its class/module
- Every Pydantic model has `REFERENCES` edges to its field types

**Output:** `architectural_context` — subgraph of modules/classes/functions
relevant to the query.

### 4.3 Layer 3 — DNA Graph

**Purpose:** Trace the path from digital DNA through RNA to expressed
phenotype and behavior.

**Data sources:**
- `speace_core/dna/genome/core/species_orientation.yaml` → PRINCIPLE nodes
- `speace_core/dna/genome/default_genome.yaml` → GENE nodes
- `speace_core/dna/models.py` → gene structure definitions
- `speace_core/dna/cognitive_genome.py` → regulatory network, epigenetics
- `speace_core/digital_rna/` → RNA expression profiles
- `speace_core/orchestrator.py` → how RNA is expressed in phenotype

**Key relations:**
```
Gene ──EXPRESSES──> RNA
RNA ──REGULATES──> Phenotype (Behavior, Circuit, Memory)
Phenotype ──CHANGES──> ILF Metric
ILF Metric ──TRIGGERS──> Adaptation
Adaptation ──MUTATES──> Gene (feedback loop)
```

**Output:** `genetic_context` — gene-to-phenotype trace for any gene or
phenotype referenced in the query.

### 4.4 Layer 4 — BCEL Graph

**Purpose:** Map biological principles through the BCEL translation pipeline
to their digital implementations and runtime evidence.

**Data sources:**
- `speace_core/bcel/catalog.py` → BCEL_MAPPING nodes
- `speace_core/bcel/models.py` → equivalence model structure
- `speace_core/bcel/classifier.py` → constraint classification
- `speace_core/cellular_brain/neuroperiodic/functional_constraint_law.py` → implemented constraints
- Test files for BCEL-annotated tests
- Orchestrator code where constraints are applied

**Key relations:**
```
BiologicalPrinciple ──TRANSLATED_TO──> BCELMapping
BCELMapping ──IMPLEMENTS──> DigitalMechanism
DigitalMechanism ──VALIDATED_BY──> Test
Test ──PRODUCES──> RuntimeEvidence
```

**Gap detection:**
The BCEL graph enables automated gap analysis:
- Biological principles without BCEL mapping
- BCEL mappings without digital implementation
- Digital implementations without tests
- Tests without runtime evidence

**Output:** `bcel_context` — the BCEL translation chain for any biological
concept referenced in the query.

### 4.5 Layer 5 — Runtime Graph

**Purpose:** Capture live and historical runtime events as graph-annotated
nodes with causal relationships.

**Data sources (collection):**
- `EventBus` subscription → capture all `DigitalSignal` events
- ILF field state snapshots → ILF_METRIC + BEHAVIOR nodes
- Mutation records → MUTATION nodes
- Error/exception logs → RUNTIME_EVENT nodes
- Audit trails from `data/logs/`, `data/persistence/`
- Orchestrator tick metrics → METRIC nodes

**Key relations:**
```
Mutation ──PRODUCED──> Behavior
Behavior ──CHANGED──> ILF Metric
ILF Metric ──TRIGGERED──> Adaptation
RuntimeEvent ──AFFECTS──> Module
Metric ──CORRELATES_WITH──> Behavior
```

**Time-window queries:**
The runtime graph supports temporal queries:
- "What changed in the last 100 ticks?"
- "Which mutations preceded the ILF dip at tick 5000?"
- "Show error events clustered around module X in the last hour."

**Output:** `runtime_context` — temporally ordered event sequence with causal
graph annotations.

### 4.6 Layer 6 — Omni Query Engine

**Purpose:** Combine all five layers into a single query operation.

**Query decomposition:**
```
User Query
    │
    ▼
OmniQuery.parse(query_text)
    │
    ├──▶ Semantic Layer ──────▶ semantic_context
    ├──▶ Architectural Graph ──▶ architectural_context
    ├──▶ DNA Graph ────────────▶ genetic_context
    ├──▶ BCEL Graph ───────────▶ bcel_context
    └──▶ Runtime Graph ───────▶ runtime_context
    │
    ▼
Correlator.merge(all_contexts)
    │
    ├── Remove duplicates (by node ID)
    ├── Boost nodes that appear in multiple layers
    ├── Rank by combined score (semantic + graph + runtime)
    └── Build explanation path
    │
    ▼
OmniResult
```

**Example queries:**

| Query | Layers traversed |
|-------|-----------------|
| "Quali geni influenzano il sistema di memoria?" | DNA + Architectural |
| "Mostra costrutti biologici senza BCEL" | BCEL + Semantic |
| "Quali mutazioni hanno causato il calo di coerenza?" | Runtime + DNA |
| "Dipendenza tra orchestrator e sistema immunitario" | Architectural |
| "Traduci il concetto di omeostasi in codice" | BCEL + Semantic + Architectural |
| "Impatto del gene X sulle performance runtime" | DNA + Runtime |

---

## 5. CLI Commands

### 5.1 `speace omni-index`

Build or refresh the cognitive graph from all data sources.

```bash
speace omni-index [--force] [--no-semantic] [--no-arch]
                   [--no-runtime] [--output PATH]
```

Options:
- `--force`: Rebuild from scratch (default: incremental)
- `--no-semantic`: Skip semantic indexing
- `--no-arch`: Skip architectural graph
- `--no-runtime`: Skip runtime event collection
- `--output`: Output directory for index files (default: `data/omni_rag/`)

### 5.2 `speace omni-query`

Query the cognitive graph across all layers.

```bash
speace omni-query "text query" [--layers semantic,arch,dna,bcel,runtime]
                [--depth 3] [--limit 50] [--format text|json|dot]
```

Options:
- `--layers`: Comma-separated layer filter
- `--depth`: Graph traversal depth (default: 3)
- `--limit`: Max results (default: 50)
- `--format`: Output format (default: text)

### 5.3 `speace omni-audit`

Run structural audits against the cognitive graph.

```bash
speace omni-audit [--type arch|bcel|dna|runtime|all]
                  [--output PATH]
```

Audit types:
- `arch`: Architectural audit — circular deps, orphan modules, god objects
- `bcel`: BCEL audit — untranslated principles, missing implementations
- `dna`: DNA audit — orphan genes, unexpressed genes, broken regulatory paths
- `runtime`: Runtime audit — error clusters, anomaly detection, health trends
- `all`: Run all audits

### 5.4 `speace omni-graph`

Export the cognitive graph in various formats for visualization.

```bash
speace omni-graph [--format dot|json|graphml]
                  [--subgraph "query"]
                  [--output graph.dot]
```

---

## 6. Implementation Architecture

### 6.1 Module Structure

```
speace_core/omni_rag/
├── __init__.py              # Public API exports
├── models.py                # CognitiveNode, CognitiveEdge, NodeType, RelationType
├── graph.py                 # CognitiveGraph — in-memory graph with adjacency lists
├── indexer.py               # OmniIndexer — crawls codebase, builds graph
├── query_engine.py          # OmniQueryEngine — multi-layer query engine
├── auditor.py               # OmniAuditor — structural audits
├── collectors/
│   ├── __init__.py
│   ├── semantic_collector.py    # Text/document indexing
│   ├── arch_collector.py        # Python AST crawling
│   ├── dna_collector.py         # Genome YAML parsing
│   ├── bcel_collector.py        # BCEL catalog parsing
│   └── runtime_collector.py     # EventBus subscription
└── persistence/
    ├── __init__.py
    └── graph_store.py           # JSONL persistence for graph
```

### 6.2 Dependencies

No new external dependencies. Uses:
- `ast` (stdlib) — Python source parsing
- `pathlib` (stdlib) — File system crawling
- `json` / `jsonl` (stdlib) — Persistence
- `collections` (stdlib) — Graph data structures
- `pydantic` (existing dep) — Data models
- `typer` (existing dep) — CLI commands
- `structlog` (existing dep) — Structured logging

### 6.3 Integration Points

| Integration | Mechanism |
|-------------|-----------|
| EventBus | `runtime_collector.py` subscribes to all channels |
| ILF Field | Reads FieldState snapshots from persistence |
| BCEL Catalog | Reads catalog entries directly |
| DNA Genome | Parses genome YAML files |
| Digital RNA | Reads Transcriptome models |
| PersistentStore | Existing persistence layer for audit trails |
| CLI | New commands registered in `cli.py` |

---

## 7. Acceptance Criteria

1. **Node interrogation:** Every cognitive node is queryable by ID, type,
   name, or tag.

2. **Edge traceability:** Every relationship is traversable in both
   directions. Path queries (A → ... → B) work for depth up to 5.

3. **Mutation traceability:** Every mutation node is linked to its
   behavioral effects and the audit trail that authorized it.

4. **Gene navigation:** Every gene node is navigable to its RNA expression,
   phenotypic effects, and ILF metric changes (max 3 hops).

5. **BCEL completeness:** Every BCEL mapping node is linked to its digital
   implementation AND its test verification. Gap detection identifies
   incomplete translations.

6. **Single-query multi-layer:** An agent can retrieve semantic context,
   architectural dependencies, DNA trace, BCEL chain, and runtime evidence
   in a single `omni-query` call.

7. **CLI commands:**
   - `speace omni-index` builds/refreshes the graph
   - `speace omni-query` returns unified results
   - `speace omni-audit` runs all audit types
   - `speace omni-graph` exports visualization

8. **Documentation:** Architecture document (this file) reflects the
   current implementation state.

---

## 8. Roadmap

### Phase 1 — Foundation (current)
- [x] Architecture specification
- [ ] Data models (CognitiveNode, CognitiveEdge, NodeType, RelationType)
- [ ] In-memory CognitiveGraph with adjacency lists
- [ ] JSONL persistence (GraphStore)
- [ ] CLI scaffold (omni-index, omni-query, omni-audit, omni-graph)

### Phase 2 — Indexers
- [ ] Semantic Collector (file crawling + keyword indexing)
- [ ] Architecture Collector (AST parsing)
- [ ] DNA Collector (genome YAML parsing)
- [ ] BCEL Collector (catalog parsing)
- [ ] Runtime Collector (EventBus subscription)
- [ ] Omni Indexer (orchestrates all collectors)

### Phase 3 — Query Engine
- [ ] Layer-specific retrievers
- [ ] Multi-layer correlator (merge + rank)
- [ ] Explanation path builder
- [ ] Natural language query parsing

### Phase 4 — Audits
- [ ] Architectural audit (circular deps, orphans)
- [ ] BCEL audit (gap analysis)
- [ ] DNA audit (expression completeness)
- [ ] Runtime audit (anomaly detection)
- [ ] Cross-layer audit reports

### Phase 5 — Integration
- [ ] Continuous runtime collection
- [ ] Integration with `speace_core/orchestrator.py`
- [ ] Agent-friendly output format
- [ ] Documentation sync

---

## 9. Diagrams

### 9.1 Cognitive Graph — Core Schema

```
┌──────────────┐     EXPRESSES     ┌──────────────┐
│    GENE      │──────────────────▶│     RNA       │
└──────┬───────┘                   └──────┬───────┘
       │                                  │
       │ REGULATES                        │ REGULATES
       ▼                                  ▼
┌──────────────┐     CHANGES     ┌──────────────────┐
│  PHENOTYPE   │────────────────▶│    ILF METRIC     │
│ (Circuit/    │                 │ (coherence_phi,   │
│  Memory/)    │                 │  systemic_entropy)│
└──────────────┘                 └────────┬─────────┘
                                          │
                                          │ TRIGGERS
                                          ▼
                                   ┌──────────────┐
                                   │  ADAPTATION   │─────▶ MUTATES ──▶ GENE
                                   └──────────────┘
```

### 9.2 BCEL Translation Pipeline

```
┌──────────────────┐    TRANSLATED_TO    ┌──────────────────┐
│  BIOLOGICAL      │────────────────────▶│  BCEL MAPPING    │
│  PRINCIPLE       │                     │  (Functional     │
│  (e.g.,          │                     │   Abstraction)   │
│   homeostasis)   │                     └────────┬─────────┘
└──────────────────┘                              │
                                                  │ IMPLEMENTS
                                                  ▼
┌──────────────────┐    VALIDATED_BY    ┌──────────────────┐
│  DIGITAL         │◀───────────────────│  TEST            │
│  MECHANISM       │                    │  (unit/integ/    │
│  (e.g., PID      │                    │   stress)        │
│   controller)    │                    └────────┬─────────┘
└──────────────────┘                             │
                                                  │ PRODUCES
                                                  ▼
                                          ┌──────────────────┐
                                          │  RUNTIME         │
                                          │  EVIDENCE        │
                                          │  (audit trail)   │
                                          └──────────────────┘
```

### 9.3 Multi-Layer Query Flow

```
User: "Quali geni influenzano il sistema di memoria e non hanno BCEL?"

    ▼
┌──────────────────────────────────────────────────────────────────┐
│ OmniQuery.parse()                                                │
│   entities: ["gene", "memory system"]                           │
│   relations: ["influence"]                                       │
│   constraints: ["no BCEL mapping"]                               │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ├── DNA Graph ──▶ find all GENEs with REGULATES→MEMORY edges
       │                      ──▶ 4 genes found
       │
       ├── BCEL Graph ──▶ for each gene, check TRANSLATED_TO edge exists
       │                      ──▶ 2 genes have BCEL, 2 do not
       │
       ├── Arch Graph ──▶ show memory system architecture for context
       │
       └── Semantic ───▶ show relevant doc passages about those genes
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│ Result:                                                          │
│   - Gene `memory_consolidation_gene` NO BCEL: expr RNA, reg     │
│     memory, no BCEL mapping found                                │
│   - Gene `cell_assembly_gene` NO BCEL: expressed, no BCEL       │
│   - Gene `synaptic_plasticity_gene` HAS BCEL: (DNA-RNA)         │
│   - Gene `homeostasis_gene` HAS BCEL: (homeostasis mapping)     │
│   - Memory system arch: SemanticMemoryStore ← EpisodicMemory    │
│     ← ConsolidationEngine                                       │
│   - Docs: see speace_core/dna/genome, speace_core/bcel/         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 10. Invariants and Constraints

1. **No modification of existing subsystems.** The Omni-RAG is a read-heavy
   observer. It reads from other subsystems but never writes to them.

2. **No new external dependencies.** All functionality uses stdlib +
   existing project dependencies.

3. **Auditability preserved.** Every indexing operation, query, and audit
   is logged with timestamps and source provenance.

4. **Reversible indexing.** `speace omni-index --force` rebuilds from
   scratch. No data is permanently lost — old index is archived.

5. **BCEL compliance.** The Omni-RAG itself must pass through the BCEL.
   See section 11.

6. **Performance.** Indexing a cold codebase must complete in <30s.
   Queries must return in <500ms for graphs with <10,000 nodes.

---

## 11. BCEL Equivalence

The Omni-RAG is a cognitive infrastructure component. In biological terms,
it is analogous to the **corpus callosum** — the bundle of neural fibers
that integrates information between the two cerebral hemispheres.

| Phase | Value |
|-------|-------|
| Biological structure | Corpus callosum — white matter tract connecting brain hemispheres |
| Preserved function | Unified information integration across distributed cognitive modules |
| Accidental constraints (removed) | Slow axonal conduction, limited bandwidth (~200M fibers), physical space constraints, myelination delay |
| Functional constraints (kept) | Bidirectional information flow, coherence-preserving integration, modulatory gating (what crosses depends on context) |
| Digital synthesis | Omni-RAG cognitive graph with typed edges, layer-specific collectors, and multi-layer query engine |
| Integration | Registered in BCEL catalog as `omni_rag_corpus_callosum` |

---

*End of specification — SPEACE Cognitive Omni-RAG Architecture v1.0*
