"""TBD-Causal — Causal Model Engine per SPEACE.

Livello 3 della memoria cognitiva: modelli esplicativi del mondo.

Questo modulo NON è un database di cause programmate.
È un sistema che costruisce teorie interne dalle osservazioni,
le testa predittivamente, e le aggiorna quando vengono falsificate.

Il salto chiave:
  pattern osservati → modelli esplicativi del mondo

Architettura emergente:
  Cell Assemblies (L2)
      ↓ rileva co-attivazione ricorrente
  Pattern ricorrenti confermati
      ↓ inferenza causale候选
  Ipotesi causali (confidence iniziale bassa)
      ↓ test predittivo su nuovi eventi
  Conferma → confidence sale | Falsificazione → confidence scende
      ↓ generalizzazione
  Causal Graph maturo (alta confidence, molte conferme)

Un CausalModel non è "la verità" — è un'ipotesi con confidenza.
Ogni link ha un livello di confidenza aggiornabile empiricamente.
"""

import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    HIGH = "high"       # ≥0.8 — confermato da molte evidenze
    MEDIUM = "medium"   # 0.5–0.8 — testato alcune volte
    LOW = "low"        # 0.2–0.5 — ipotesi iniziale
    SPECULATIVE = "speculative"  # <0.2 — derivato da pochi eventi


# ── Core Models ─────────────────────────────────────────────────────────

class CausalLink(BaseModel):
    """Una singola relazione causa → effetto.

    NON è un dato di fatto — è un'ipotesi con confidenza misurata.
    Se la confidenza scende sotto soglia, il link viene deprioritizzato
    ma mai deletato (può essere ripescato se nuove evidenze emergono).
    """
    link_id: str = Field(default_factory=lambda: f"cl-{uuid.uuid4().hex[:8]}")
    cause_entity: str = ""
    effect_entity: str = ""
    # Tipi di relazione — non solo "causal":
    relation_type: str = "causal"  # causal | enables | inhibits | correlates | implies | temporal
    description: str = ""

    # Confidenza: aggiornata empiricamente ad ogni conferma/falsificazione
    confidence: float = 0.3
    confidence_level: ConfidenceLevel = ConfidenceLevel.SPECULATIVE

    # Evidenze raccolte
    confirmation_count: int = 0   # quante volte è stata confermata
    falsification_count: int = 0   # quante volte è stata falsificata
    evidence_episodes: List[str] = Field(default_factory=list)  # episode_id che supportano
    failure_episodes: List[str] = Field(default_factory=list)   # episode_id che contraddicono

    # Controfattuali: cosa sarebbe successo se...
    counterfactual_prompts: List[str] = Field(default_factory=list)

    # Metadati evolutivi
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_tested_at: Optional[str] = None
    reversed_link_id: Optional[str] = None  # link_id del legame inverso (se scoperto)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CausalModel(BaseModel):
    """Un modello causale completo: teorie compresse del fenomeno.

    Non è una registrazione di eventi — è una teoria.
    La differenza fondamentale:
      - EpisodicMemory dice: "è successo A poi B"
      - CausalModel dice: "A causa B, con confidenza X"

    Un modello maturo può fare previsioni, diagnosi, trasferimento.
    """
    model_id: str = Field(default_factory=lambda: f"cm-{uuid.uuid4().hex[:8]}")
    name: str = ""
    description: str = ""

    # Entità e relazioni
    entities: List[str] = Field(default_factory=list)
    relations: List[CausalLink] = Field(default_factory=list)

    # Struttura del grafo (derivata, non manuale)
    root_causes: List[str] = Field(default_factory=list)   # nodi senza cause nel grafo
    terminal_effects: List[str] = Field(default_factory=list)  # nodi senza effetti

    # Meta-informazioni
    confidence: float = 0.3
    confidence_level: ConfidenceLevel = ConfidenceLevel.SPECULATIVE

    # Evidenze aggregate
    source_episodes: List[str] = Field(default_factory=list)
    linked_assemblies: List[str] = Field(default_factory=list)  # cell assembly ID che hanno generato questo modello
    tags: List[str] = Field(default_factory=list)

    # Lifecycle
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activated_at: Optional[str] = None
    activation_count: int = 0

    # Emergenza: come è stato costruito
    emergence_type: str = "observed"  # observed | inferred | generalized | hypothetical
    generalization_count: int = 0  # quanti modelli sono stati generalizzati da questo

    metadata: Dict[str, Any] = Field(default_factory=dict)
    active: bool = True


class CausalInferenceResult(BaseModel):
    """Risultato di un'inferenza causale — NON una predizione certa."""
    model_id: str
    query: str
    inference_type: str = ""  # forward | backward | counterfactual | diagnosis

    predicted_entities: List[str] = Field(default_factory=list)
    chain: List[str] = Field(default_factory=list)  # catena logica seguita
    chain_confidence: float = 0.0  # confidenza del cammino

    confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.SPECULATIVE

    # Per diagnostica: nodi che potrebbero essere la causa del fallimento
    candidate_culprits: List[Dict[str, Any]] = Field(default_factory=list)

    # Controfattuali: cosa sarebbe successo se...
    counterfactual_scenarios: List[Dict[str, Any]] = Field(default_factory=list)

    metadata: Dict[str, Any] = Field(default_factory=dict)


class HypothesisRevision(BaseModel):
    """Registro di una revisione causale — per tracciare l'evoluzione del modello."""
    revision_id: str = Field(default_factory=lambda: f"rev-{uuid.uuid4().hex[:8]}")
    model_id: str
    link_id: Optional[str] = None  # link specifico modificato, o None per modifica modello

    trigger: str = ""  # "confirmation" | "falsification" | "generalization" | "merge"
    episode_id: Optional[str] = None

    old_confidence: float = 0.0
    new_confidence: float = 0.0

    description: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── CausalGraph — il grafo causale emergente ───────────────────────────

class CausalGraph:
    """Grafo causale emergente: nodi = entità, archi = relazioni con confidenza.

    NON è costruito manualmente. Emerge dall'analisi di:
    - Cell assemblies (pattern co-attivati)
    - Episodi (sequenze di eventi)
    - Predizioni confermate/falsificate

    Il grafo supporta:
    - propagazione di confidenza
    - ricerca cammini
    - diagnostica (nodeguilty)
    - trasferimento a contesti nuovi
    """

    def __init__(self):
        # Adjacency: entity -> list of (target_entity, link_id)
        self._out: Dict[str, List[tuple]] = defaultdict(list)
        self._in: Dict[str, List[tuple]] = defaultdict(list)
        self._links: Dict[str, CausalLink] = {}
        self._models: Dict[str, CausalModel] = {}

    def add_link(self, link: CausalLink) -> None:
        self._links[link.link_id] = link
        self._out[link.cause_entity].append((link.effect_entity, link.link_id))
        self._in[link.effect_entity].append((link.cause_entity, link.link_id))

    def get_link(self, link_id: str) -> Optional[CausalLink]:
        return self._links.get(link_id)

    def get_outgoing(self, entity: str) -> List[CausalLink]:
        return [self._links[lid] for tid, lid in self._out.get(entity, []) if lid in self._links]

    def get_incoming(self, entity: str) -> List[CausalLink]:
        return [self._links[lid] for cid, lid in self._in.get(entity, []) if lid in self._links]

    def get_all_entities(self) -> Set[str]:
        return set(self._out.keys()) | set(self._in.keys())

    def update_link_confidence(self, link_id: str, confirmed: bool) -> None:
        """Aggiorna confidenza di un link dopo test predittivo."""
        link = self._links.get(link_id)
        if not link:
            return

        if confirmed:
            link.confirmation_count += 1
            # Bayesian-inspired update: confidence increases, asymptotically to 1.0
            link.confidence = min(0.99, link.confidence + (1.0 - link.confidence) * 0.15)
        else:
            link.falsification_count += 1
            # Confidence decreases, floor at 0.05
            link.confidence = max(0.05, link.confidence * 0.7)

        link.last_tested_at = datetime.now(timezone.utc).isoformat()
        link.confidence_level = _to_confidence_level(link.confidence)

    def find_path(self, start: str, end: str, max_depth: int = 6) -> List[str]:
        """BFS: cammino più breve/confidente tra due entità."""
        from collections import deque

        best_path: List[str] = []
        best_score = -1.0

        queue: deque = deque([(start, [start], 1.0)])
        visited = {start}

        while queue:
            entity, path, score = queue.popleft()
            if len(path) > max_depth + 1:
                continue
            if entity == end and len(path) > 1:
                if score > best_score:
                    best_score = score
                    best_path = path
                continue
            for target, link_id in self._out.get(entity, []):
                if target not in visited:
                    link = self._links.get(link_id)
                    if link:
                        new_score = score * link.confidence
                        visited.add(target)
                        queue.append((target, path + [target], new_score))

        return best_path

    def find_all_paths(self, start: str, end: str, max_depth: int = 4) -> List[tuple]:
        """Trova tutti i cammini fino a max_depth. Ritorna (path, confidence_score)."""
        from collections import deque
        results: List[tuple] = []

        queue: deque = deque([(start, [start], 1.0)])
        while queue:
            entity, path, score = queue.popleft()
            if len(path) > max_depth + 1:
                continue
            if entity == end and len(path) > 1:
                results.append((path, score))
                continue
            for target, link_id in self._out.get(entity, []):
                link = self._links.get(link_id)
                if link and target not in path:
                    queue.append((target, path + [target], score * link.confidence))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def diagnose(
        self,
        expected_effect: str,
        observed_absence: str,
        known_entities: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Diagnosi: quale nodo intermedio è probabilmente guasto?

        Input: mi aspettavo che A → B → C → effetto
               ma l'effetto non si è verificato
        Output: candidati ordinati per probabilità di guasto
        """
        candidates: List[Dict[str, Any]] = []

        # Tutti i cammini noti che portano all'effetto atteso
        all_entities = known_entities or list(self.get_all_entities())

        for entity in all_entities:
            if entity == observed_absence:
                continue
            paths = self.find_all_paths(entity, expected_effect, max_depth=5)
            if not paths:
                continue
            best_path, path_conf = max(paths, key=lambda x: x[1])

            # Calcola "colpevolezza": quanto del cammino era attivo vs quanto manca
            incoming = self.get_incoming(entity)
            outgoing = self.get_outgoing(entity)

            guilt_score = path_conf * (
                0.4 * sum(l.confidence for l in incoming) / max(1, len(incoming)) +
                0.6 * sum(l.confidence for l in outgoing) / max(1, len(outgoing))
            )

            candidates.append({
                "entity": entity,
                "guilt_score": round(guilt_score, 3),
                "path_to_failure": best_path,
                "path_confidence": round(path_conf, 3),
                "incoming_links": len(incoming),
                "outgoing_links": len(outgoing),
            })

        candidates.sort(key=lambda x: x["guilt_score"], reverse=True)
        return candidates[:5]  # top 5 candidati

    def counterfactual_what_if(
        self,
        entity: str,
        new_confidence: float,
        effect_to_check: str,
    ) -> Dict[str, Any]:
        """Controfattuale: cosa succede se questa entità avesse confidenza X?

        Simula l'effetto di modificare la confidenza di un link sulla predizione finale.
        """
        original_link = None
        for link in self.get_outgoing(entity):
            if link.effect_entity == effect_to_check:
                original_link = link
                break

        if not original_link:
            return {"feasible": False, "reason": "no direct path"}

        # Calcola catena di propagazione
        chain = [entity]
        current = entity
        chain_conf = 1.0

        visited = {entity}
        while current != effect_to_check:
            best_next = None
            best_next_conf = 0.0
            for link in self.get_outgoing(current):
                if link.effect_entity not in visited:
                    conf = link.confidence if link.link_id != original_link.link_id else new_confidence
                    if conf > best_next_conf:
                        best_next_conf = conf
                        best_next = link.effect_entity

            if not best_next:
                break
            visited.add(best_next)
            conf = new_confidence if current == entity else chain_conf
            chain_conf *= best_next_conf
            chain.append(best_next)
            current = best_next

        return {
            "feasible": current == effect_to_check,
            "what_if_entity": entity,
            "what_if_confidence": new_confidence,
            "effect_predicted": effect_to_check,
            "chain": chain,
            "resulting_confidence": round(chain_conf, 3),
            "note": "confidenza del cammino se il link avesse confidenza X",
        }

    def propagate_confidence(self) -> Dict[str, float]:
        """Propaga confidenze lungo il grafo — entità con alta confidenza
        in uscita aumentano la confidenza dei nodi a valle."""
        entity_conf: Dict[str, float] = {}

        # Root causes: confidenza iniziale dalla media dei link in uscita
        all_entities = self.get_all_entities()
        for entity in all_entities:
            outgoing = self.get_outgoing(entity)
            incoming = self.get_incoming(entity)
            if not incoming:  # root cause
                entity_conf[entity] = sum(l.confidence for l in outgoing) / max(1, len(outgoing))
            elif not outgoing:  # terminal effect
                entity_conf[entity] = sum(l.confidence for l in incoming) / max(1, len(incoming))
            else:
                entity_conf[entity] = 0.3  # default

        # Propaga avanti
        changed = True
        iterations = 0
        while changed and iterations < 10:
            changed = False
            iterations += 1
            new_conf = dict(entity_conf)
            for entity in all_entities:
                incoming = self.get_incoming(entity)
                if incoming:
                    avg_in = sum(entity_conf.get(cid, 0.0) * link.confidence
                                 for cid, link_id in incoming
                                 for link in [self._links.get(link_id)]
                                 if link) / max(1, len(incoming))
                    propagated = avg_in * 0.5 + entity_conf[entity] * 0.5
                    if abs(propagated - entity_conf[entity]) > 0.01:
                        new_conf[entity] = propagated
                        changed = True
            entity_conf = new_conf

        return entity_conf

    def get_statistics(self) -> Dict[str, Any]:
        all_entities = self.get_all_entities()
        links = list(self._links.values())
        active = [l for l in links if l.confidence > 0.1]
        return {
            "total_entities": len(all_entities),
            "total_links": len(links),
            "active_links": len(active),
            "high_confidence_links": sum(1 for l in active if l.confidence >= 0.8),
            "avg_confidence": sum(l.confidence for l in active) / max(1, len(active)),
            "models_count": len(self._models),
            "root_causes": [e for e in all_entities if not self._in.get(e)],
            "terminal_effects": [e for e in all_entities if not self._out.get(e)],
        }


# ── CausalModelStore ────────────────────────────────────────────────────

class CausalModelStore:
    """Storage persistente per modelli causali."""

    def __init__(self, storage_path: str = "data/agi_team/causal_models.jsonl"):
        from pathlib import Path
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, CausalModel] = {}
        self._load()

    def _load(self):
        if not self._storage_path.exists():
            return
        import json
        for line in self._storage_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                model = CausalModel(**data)
                self._models[model.model_id] = model
            except Exception:
                continue

    def _persist(self):
        import json
        lines = [m.model_dump_json() for m in self._models.values()]
        self._storage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def save(self, model: CausalModel):
        self._models[model.model_id] = model
        self._persist()

    def get(self, model_id: str) -> Optional[CausalModel]:
        return self._models.get(model_id)

    def list_active(self) -> List[CausalModel]:
        return [m for m in self._models.values() if m.active]

    def find_by_entity(self, entity: str) -> List[CausalModel]:
        return [m for m in self.list_active() if entity in m.entities]

    def find_by_tag(self, tag: str) -> List[CausalModel]:
        return [m for m in self.list_active() if tag in m.tags]


# ── CausalModelEngine ───────────────────────────────────────────────────

class CausalModelEngine:
    """TBD — Causal Model Engine: costruisce, testa e aggiorna modelli causali.

    IL PUNTO FONDAMENTALE: il grafo NON è programmato a mano.
    Emerge dal ciclo:
      Cell Assembly (L2) → pattern ricorrenti → ipotesi causali →
      test predittivo → conferma/falsificazione → Causal Graph maturo

    Responsabilità:
    1. Inferire relazioni causali da pattern di cell assembly
    2. Testare predittivamente le ipotesi (confrontando con episodi nuovi)
    3. Aggiornare confidenze dopo ogni test
    4. Generare modelli generalizzati da modelli specifici
    5. Diagnosticare fallimenti (quale nodo è guasto?)
    6. Ragionamento controfattuale (cosa se...?)
    7. Trasferire conoscenza a contesti nuovi
    """

    def __init__(self, store: Optional[CausalModelStore] = None):
        self.store = store or CausalModelStore()
        self.graph = CausalGraph()
        self._revision_log: List[HypothesisRevision] = []
        self._load_graph_from_store()

        # ── Task 1: Meta-Causal Space ─────────────────────────────────
        self.causal_space = CausalSpace(self)

        # ── Task 2: Gap Detection ──────────────────────────────────────
        self.gap_detector = GapDetector(self)

        # ── Task 7: Causal Prediction Validator ───────────────────────
        self.validator = CausalPredictionValidator(self)

        # ── Task 3: Cross-Domain Pattern Detector ─────────────────────
        self.cross_domain_detector = CrossDomainPatternDetector(self)

        # ── Task 5: Concept Atomic Number ─────────────────────────────
        self.concept_atomic_number = ConceptAtomicNumber()

        # ── Task 6: L4/L5/L6 — Principi e Meta-principi ──────────────
        self.principle_store = PrincipleStore()
        self.principle_generator = PrincipleGenerator(self, self.principle_store)
        self.meta_principle_engine = MetaPrincipleEngine(self.principle_generator, self.principle_store)

        # ── Task 4: Cognitive Compression Pipeline ─────────────────────
        self.compression_pipeline = CognitiveCompressionPipeline(self)

    def _load_graph_from_store(self):
        """Ricostruisce il grafo dai modelli memorizzati."""
        for model in self.store.list_active():
            self.graph._models[model.model_id] = model
            for link in model.relations:
                self.graph.add_link(link)

    # ── Building: da osservazione a teoria ────────────────────────────

    def infer_from_cell_assemblies(
        self,
        assemblies: List[Dict[str, Any]],
        min_recurrence: int = 3,
    ) -> List[CausalModel]:
        """Inferisce modelli causali da cell assemblies co-attivati.

        Cell assemblies che si attivano insieme ripetutamente suggeriscono
        una relazione causale sottostante.

        Args:
            assemblies: list di dict con keys: assembly_id, neuron_ids,
                       activation_signature, recurrence_count, stability
            min_recurrence: quante volte deve essere stato confermato prima
                           di creare un'ipotesi causale
        """
        models = []

        # Analizza coppie di assemblies: se A e B co-attivano sempre,
        # potrebbe esserci una relazione A → B o B → A
        for i, asm_a in enumerate(assemblies):
            for asm_b in assemblies[i+1:]:
                recurrence = min(
                    asm_a.get("recurrence_count", 1),
                    asm_b.get("recurrence_count", 1),
                )
                if recurrence < min_recurrence:
                    continue

                # Co-attivazione ricorrente → candidate causal relation
                # Determiniamo direzione dalla media delle attivazioni
                # (se A attiva prima di B temporalmente, A → B)
                # Per ora creiamo un modello speculativo bidirezionale

                link_a_to_b = CausalLink(
                    cause_entity=f"asm:{asm_a.get('assembly_id', asm_a.get('assembly_id', 'unknown'))}",
                    effect_entity=f"asm:{asm_b.get('assembly_id', 'unknown')}",
                    relation_type="correlates",
                    description=f"Co-attivazione ricorrente ({recurrence} volte)",
                    confidence=min(0.5, 0.1 + recurrence * 0.05),  # sale con ricorrenza
                    confidence_level=_to_confidence_level(
                        min(0.5, 0.1 + recurrence * 0.05)
                    ),
                )

                link_b_to_a = CausalLink(
                    cause_entity=f"asm:{asm_b.get('assembly_id', 'unknown')}",
                    effect_entity=f"asm:{asm_a.get('assembly_id', 'unknown')}",
                    relation_type="correlates",
                    description=f"Co-attivazione ricorrente ({recurrence} volte)",
                    confidence=min(0.5, 0.1 + recurrence * 0.05),
                    confidence_level=_to_confidence_level(
                        min(0.5, 0.1 + recurrence * 0.05)
                    ),
                    reversed_link_id=link_a_to_b.link_id,
                )

                link_a_to_b.reversed_link_id = link_b_to_a.link_id

                model = CausalModel(
                    name=f"assembly-relation-{asm_a.get('assembly_id', 'A')}-{asm_b.get('assembly_id', 'B')}",
                    description="Relazione inferita da co-attivazione ricorrente di cell assemblies",
                    entities=[
                        f"asm:{asm_a.get('assembly_id', 'unknown')}",
                        f"asm:{asm_b.get('assembly_id', 'unknown')}",
                    ],
                    relations=[link_a_to_b, link_b_to_a],
                    confidence=min(0.5, 0.1 + recurrence * 0.05),
                    confidence_level=_to_confidence_level(
                        min(0.5, 0.1 + recurrence * 0.05)
                    ),
                    linked_assemblies=[
                        asm_a.get("assembly_id", ""),
                        asm_b.get("assembly_id", ""),
                    ],
                    tags=["cell-assembly", "inferred", "speculative"],
                    emergence_type="inferred",
                )

                self._add_model_to_graph(model)
                models.append(model)

        return models

    def infer_from_episode(
        self,
        events: List[Dict[str, Any]],
        episode_id: str = "",
    ) -> Optional[CausalModel]:
        """Costruisce un modello causale da una sequenza di eventi episodici.

        La sequenza A → B → C suggerisce catene causali.
        Se lo stesso pattern emerge in più episodi, la confidenza sale.
        """
        if len(events) < 2:
            return None

        links: List[CausalLink] = []
        entities: Set[str] = set()
        all_causes: Set[str] = set()
        all_effects: Set[str] = set()

        for i in range(len(events) - 1):
            cause_event = events[i]
            effect_event = events[i + 1]

            cause_id = cause_event.get("event_type", f"evt-{i}")
            effect_id = effect_event.get("event_type", f"evt-{i+1}")

            entities.add(cause_id)
            entities.add(effect_id)
            all_causes.add(cause_id)
            all_effects.add(effect_id)

            # Check se questa relazione esiste già con alta confidenza
            existing = self._find_existing_link(cause_id, effect_id)

            link = CausalLink(
                cause_entity=cause_id,
                effect_entity=effect_id,
                relation_type="enables",
                description=f"{cause_id} → {effect_id}",
                confidence=existing.confidence * 1.1 if existing else 0.3,
                confidence_level=_to_confidence_level(
                    existing.confidence * 1.1 if existing else 0.3
                ),
                evidence_episodes=[episode_id] if episode_id else [],
            )
            if existing:
                link.link_id = existing.link_id
                link.confirmation_count = existing.confirmation_count + 1
                link.evidence_episodes = existing.evidence_episodes + ([episode_id] if episode_id else [])

            links.append(link)

        root_causes = list(all_causes - all_effects)
        terminal_effects = list(all_effects - all_causes)

        model = CausalModel(
            name=f"episode-model-{episode_id or uuid.uuid4().hex[:6]}",
            description=f"Modello causale derivato da {len(events)} eventi consecutivi",
            entities=list(entities),
            relations=links,
            root_causes=root_causes,
            terminal_effects=terminal_effects,
            confidence=sum(l.confidence for l in links) / len(links) if links else 0.3,
            confidence_level=_to_confidence_level(
                sum(l.confidence for l in links) / len(links) if links else 0.3
            ),
            source_episodes=[episode_id] if episode_id else [],
            tags=["episodic", "derived"],
            emergence_type="observed",
        )

        self._add_model_to_graph(model)
        self.store.save(model)
        return model

    def build_explicit_model(
        self,
        name: str,
        description: str,
        entities: List[str],
        relations: List[Dict[str, Any]],
        confidence: float = 0.5,
        tags: Optional[List[str]] = None,
        evidence_ids: Optional[List[str]] = None,
    ) -> CausalModel:
        """Costruisce un modello causale esplicito da relazioni strutturate.

        Usato per modelli derivati da conoscenza esterna o da ragionamento diretto.
        """
        links = []
        all_causes: Set[str] = set()
        all_effects: Set[str] = set()

        for rel in relations:
            cause = rel["cause_entity"]
            effect = rel["effect_entity"]
            all_causes.add(cause)
            all_effects.add(effect)

            link = CausalLink(
                cause_entity=cause,
                effect_entity=effect,
                relation_type=rel.get("relation_type", "causal"),
                description=rel.get("description", f"{cause} → {effect}"),
                confidence=rel.get("confidence", confidence),
                confidence_level=_to_confidence_level(rel.get("confidence", confidence)),
                evidence_ids=rel.get("evidence_ids", []),
                failure_conditions=rel.get("failure_conditions", []),
            )
            links.append(link)

        root_causes = list(all_causes - all_effects)
        terminal_effects = list(all_effects - all_causes)

        model = CausalModel(
            name=name,
            description=description,
            entities=entities,
            relations=links,
            root_causes=root_causes,
            terminal_effects=terminal_effects,
            confidence=confidence,
            confidence_level=_to_confidence_level(confidence),
            evidence_ids=evidence_ids or [],
            tags=tags or [],
            emergence_type="explicit",
        )

        self._add_model_to_graph(model)
        self.store.save(model)
        return model

    # ── Predictive Testing ────────────────────────────────────────────

    def test_prediction(
        self,
        model_id: str,
        new_episode_events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Test predittivo: un nuovo episodio conferma o falsifica il modello?

        Dato un modello, verifica se le predizioni che farebbe
        sono coerenti con i nuovi eventi osservati.

        Returns dict con:
          - confirmed: bool
          - predicted: cosa si prediceva
          - observed: cosa si è osservato
          - delta_confidence: quanto è cambiata la confidenza
        """
        model = self.store.get(model_id)
        if not model:
            return {"error": "model not found"}

        confirmed_links = 0
        falsified_links = 0
        tested_entities: Set[str] = set()

        for event in new_episode_events:
            event_type = event.get("event_type", "")
            if not event_type:
                continue

            tested_entities.add(event_type)

            # Cerca link che predicono questo evento come effetto
            for link in model.relations:
                if link.effect_entity == event_type:
                    # Trovato un link che predice questo evento
                    # Controlla se la causa era presente
                    cause_present = any(
                        e.get("event_type") == link.cause_entity
                        for e in new_episode_events
                    )
                    if cause_present:
                        confirmed_links += 1
                        self.graph.update_link_confidence(link.link_id, confirmed=True)
                        self._log_revision(model_id, link.link_id, "confirmation")
                    else:
                        # La causa non era presente ma l'effetto sì → potenziale falsificazione
                        # (oppure il modello era incompleto)
                        pass

        # Calcola variazione confidenza
        old_conf = model.confidence
        n = len(model.relations)
        avg_conf = sum(l.confidence for l in model.relations) / max(1, n)

        if confirmed_links > 0 and falsified_links == 0:
            new_conf = min(0.99, avg_conf + 0.05)
        elif falsified_links > 0:
            new_conf = max(0.1, avg_conf - 0.1 * (falsified_links / max(1, confirmed_links + falsified_links)))
        else:
            new_conf = avg_conf

        model.confidence = new_conf
        model.confidence_level = _to_confidence_level(new_conf)
        model.activation_count += 1
        model.last_activated_at = datetime.now(timezone.utc).isoformat()
        self.store.save(model)

        return {
            "confirmed": confirmed_links > 0 and falsified_links == 0,
            "confirmed_links": confirmed_links,
            "falsified_links": falsified_links,
            "tested_entities": list(tested_entities),
            "old_confidence": round(old_conf, 3),
            "new_confidence": round(new_conf, 3),
            "delta": round(new_conf - old_conf, 3),
        }

    # ── Inference ────────────────────────────────────────────────────

    def infer_effects(
        self,
        model_id: str,
        given_cause: str,
        max_depth: int = 5,
    ) -> CausalInferenceResult:
        """Forward inference: data una causa, prevedi gli effetti a cascata."""
        model = self.store.get(model_id)
        if not model:
            return CausalInferenceResult(model_id=model_id, query=given_cause)

        predicted: List[str] = []
        chain: List[str] = [given_cause]
        current = {given_cause}
        depth = 0
        chain_conf = 1.0

        while depth < max_depth:
            next_entities: Set[str] = set()
            for entity in current:
                for link in model.relations:
                    if link.cause_entity == entity and link.confidence > 0.1:
                        predicted.append(link.effect_entity)
                        chain.append(f"{link.cause_entity} → {link.effect_entity}")
                        chain_conf *= link.confidence
                        next_entities.add(link.effect_entity)
            if not next_entities:
                break
            current = next_entities
            depth += 1

        return CausalInferenceResult(
            model_id=model_id,
            query=given_cause,
            inference_type="forward",
            predicted_entities=list(set(predicted)),
            chain=chain,
            chain_confidence=chain_conf,
            confidence=chain_conf,
            confidence_level=_to_confidence_level(chain_conf),
        )

    def infer_causes(
        self,
        model_id: str,
        given_effect: str,
        max_depth: int = 5,
    ) -> CausalInferenceResult:
        """Backward inference: data un effetto, trova le cause a monte."""
        model = self.store.get(model_id)
        if not model:
            return CausalInferenceResult(model_id=model_id, query=given_effect)

        causes: List[str] = []
        chain: List[str] = [given_effect]
        current = {given_effect}
        depth = 0
        chain_conf = 1.0

        while depth < max_depth:
            next_entities: Set[str] = set()
            for entity in current:
                for link in model.relations:
                    if link.effect_entity == entity and link.confidence > 0.1:
                        causes.append(link.cause_entity)
                        chain.append(f"{link.cause_entity} ← {link.effect_entity}")
                        chain_conf *= link.confidence
                        next_entities.add(link.cause_entity)
            if not next_entities:
                break
            current = next_entities
            depth += 1

        return CausalInferenceResult(
            model_id=model_id,
            query=given_effect,
            inference_type="backward",
            predicted_entities=list(set(causes)),
            chain=chain,
            chain_confidence=chain_conf,
            confidence=chain_conf,
            confidence_level=_to_confidence_level(chain_conf),
        )

    def diagnose_failure(
        self,
        expected_effect: str,
        observed_failure: str,
        context_entities: Optional[List[str]] = None,
    ) -> CausalInferenceResult:
        """Diagnosi: quale nodo nel grafo ha probabilmente causato il fallimento?

        Metodo chiave per il ragionamento diagnostico.
        """
        candidates = self.graph.diagnose(
            expected_effect=expected_effect,
            observed_absence=observed_failure,
            known_entities=context_entities,
        )

        return CausalInferenceResult(
            model_id="",
            query=f"Daignosi: mi aspettavo {expected_effect} ma è fallito {observed_failure}",
            inference_type="diagnosis",
            predicted_entities=[c["entity"] for c in candidates],
            candidate_culprits=candidates,
            confidence=max(c["guilt_score"] for c in candidates) if candidates else 0.0,
            confidence_level=_to_confidence_level(
                max(c["guilt_score"] for c in candidates) if candidates else 0.0
            ),
        )

    def counterfactual(
        self,
        entity: str,
        hypothetical_confidence: float,
        effect_to_predict: str,
    ) -> CausalInferenceResult:
        """Ragionamento controfattuale: cosa succederebbe se questo link avesse confidenza X?"""
        result = self.graph.counterfactual_what_if(
            entity=entity,
            new_confidence=hypothetical_confidence,
            effect_to_check=effect_to_predict,
        )

        return CausalInferenceResult(
            model_id="",
            query=f"Cosa se {entity} avesse confidenza {hypothetical_confidence}?",
            inference_type="counterfactual",
            predicted_entities=[effect_to_predict] if result.get("feasible") else [],
            chain=result.get("chain", []),
            chain_confidence=result.get("resulting_confidence", 0.0),
            confidence=result.get("resulting_confidence", 0.0),
            counterfactual_scenarios=[result],
        )

    # ── Generalization ───────────────────────────────────────────────

    def generalize(
        self,
        model_ids: List[str],
        new_name: str,
        new_tags: Optional[List[str]] = None,
    ) -> Optional[CausalModel]:
        """Generalizza più modelli in un modello di livello superiore.

        I modelli che condividono strutture simili vengono fusi in uno astratto.
        """
        models = [self.store.get(mid) for mid in model_ids if self.store.get(mid)]
        if len(models) < 2:
            return None

        # Merge entities comuni
        common_entities = set(models[0].entities)
        for m in models[1:]:
            common_entities &= set(m.entities)

        # Merge relations (media delle confidenze per relazioni identiche)
        merged: Dict[tuple, CausalLink] = {}
        for m in models:
            for link in m.relations:
                key = (link.cause_entity, link.effect_entity, link.relation_type)
                if key not in merged:
                    merged[key] = link
                else:
                    old = merged[key]
                    new_conf = (old.confidence + link.confidence) / 2
                    merged[key] = CausalLink(
                        link_id=f"cl-{uuid.uuid4().hex[:8]}",
                        cause_entity=old.cause_entity,
                        effect_entity=old.effect_entity,
                        relation_type=old.relation_type,
                        description=old.description,
                        confidence=new_conf,
                        confidence_level=_to_confidence_level(new_conf),
                        confirmation_count=old.confirmation_count + link.confirmation_count,
                        evidence_ids=old.evidence_ids + link.evidence_ids,
                    )

        all_causes = {l.cause_entity for l in merged.values()}
        all_effects = {l.effect_entity for l in merged.values()}
        root_causes = list(all_causes - all_effects)
        terminal_effects = list(all_effects - all_causes)

        avg_conf = sum(m.confidence for m in models) / len(models)

        generalized = CausalModel(
            name=new_name,
            description=f"Generalizzato da {len(models)} modelli: {[m.name for m in models]}",
            entities=list(common_entities) if common_entities else [],
            relations=list(merged.values()),
            root_causes=root_causes,
            terminal_effects=terminal_effects,
            confidence=avg_conf * 0.9,
            confidence_level=_to_confidence_level(avg_conf * 0.9),
            tags=(new_tags or []) + ["generalized"],
            generalization_count=len(models),
            emergence_type="generalized",
        )

        for m in models:
            m.generalization_count += 1

        self._add_model_to_graph(generalized)
        self.store.save(generalized)
        return generalized

    # ── Transfer ─────────────────────────────────────────────────────

    def transfer_to_new_context(
        self,
        model_id: str,
        entity_mapping: Dict[str, str],
    ) -> Optional[CausalModel]:
        """Trasferisce un modello a un contesto nuovo.

        Esempio: se ho un modello "freddo → ipotermia → morte pianta"
        e vedo che il concetto "calore eccessivo" è analogo a "freddo",
        posso trasferire il modello sostituendo le entità.
        """
        model = self.store.get(model_id)
        if not model:
            return None

        new_entities: List[str] = []
        new_links: List[CausalLink] = []
        all_causes = set()
        all_effects = set()

        for link in model.relations:
            new_cause = entity_mapping.get(link.cause_entity, link.cause_entity)
            new_effect = entity_mapping.get(link.effect_entity, link.effect_entity)
            new_entities.extend([new_cause, new_effect])
            all_causes.add(new_cause)
            all_effects.add(new_effect)

            new_link = CausalLink(
                cause_entity=new_cause,
                effect_entity=new_effect,
                relation_type=link.relation_type,
                description=f"[trasferito] {link.description}",
                confidence=link.confidence * 0.7,  # confidenza ridotta: trasferimento
                confidence_level=_to_confidence_level(link.confidence * 0.7),
            )
            new_links.append(new_link)

        transferred = CausalModel(
            name=f"[trasferito] {model.name}",
            description=f"Trasferimento di '{model.name}' a nuovo contesto. Mapping: {entity_mapping}",
            entities=list(set(new_entities)),
            relations=new_links,
            root_causes=list(all_causes - all_effects),
            terminal_effects=list(all_effects - all_causes),
            confidence=model.confidence * 0.7,
            confidence_level=_to_confidence_level(model.confidence * 0.7),
            linked_assemblies=model.linked_assemblies[:],
            tags=["transferred", "cross-context"],
            metadata={"original_model_id": model_id, "entity_mapping": entity_mapping},
            emergence_type="transferred",
        )

        self._add_model_to_graph(transferred)
        self.store.save(transferred)
        return transferred

    # ── Revision Tracking ────────────────────────────────────────────

    def _log_revision(
        self,
        model_id: str,
        link_id: Optional[str],
        trigger: str,
        old_conf: float = 0.0,
        new_conf: float = 0.0,
    ):
        rev = HypothesisRevision(
            model_id=model_id,
            link_id=link_id,
            trigger=trigger,
            old_confidence=old_conf,
            new_confidence=new_conf,
        )
        self._revision_log.append(rev)

    def get_revision_log(self, model_id: Optional[str] = None) -> List[HypothesisRevision]:
        if model_id:
            return [r for r in self._revision_log if r.model_id == model_id]
        return self._revision_log[-50:]

    # ── Graph Integration ────────────────────────────────────────────

    def _add_model_to_graph(self, model: CausalModel) -> None:
        self.graph._models[model.model_id] = model
        for link in model.relations:
            self.graph.add_link(link)

    def _find_existing_link(self, cause: str, effect: str) -> Optional[CausalLink]:
        for model in self.store.list_active():
            for link in model.relations:
                if link.cause_entity == cause and link.effect_entity == effect:
                    return link
        return None

    # ── Statistics ───────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        models = list(self.store._models.values())
        active = [m for m in models if m.active]
        links = list(self.graph._links.values())
        active_links = [l for l in links if l.confidence > 0.1]

        return {
            "models_total": len(models),
            "models_active": len(active),
            "links_total": len(links),
            "links_high_confidence": sum(1 for l in active_links if l.confidence >= 0.8),
            "avg_link_confidence": sum(l.confidence for l in active_links) / max(1, len(active_links)),
            "graph_entities": len(self.graph.get_all_entities()),
            "emergence_types": list(set(m.emergence_type for m in active)),
            "generalized_models": sum(1 for m in active if m.generalization_count > 0),
            "transferred_models": sum(1 for m in active if "transferred" in m.tags),
            "revisions_logged": len(self._revision_log),
            "by_tag": {
                tag: sum(1 for m in active if tag in m.tags)
                for tag in {"cell-assembly", "episodic", "generalized", "transferred", "explicit", "inferred"}
            },
        }


# ══════════════════════════════════════════════════════════════════════════
# TASK 1: Meta-Causal Space
# Posizione = Significato. I modelli vicini nello spazio condividono struttura.
# ══════════════════════════════════════════════════════════════════════════

class CausalSpace:
    """Spazio n-dimensionale dove ogni CausalModel ha coordinate.

    Le coordinate sono calcolate da:
    - struttura relazionale (numero nodi, archi, profondità)
    - tipo di dominio (biologico, economico, ecologico, sociale)
    - livello di astrazione

    Due modelli vicini nello spazio condividono struttura causale.
    """

    DIMENSION_NAMES = [
        "structural_complexity",   # 0: num_entities + num_relations
        "causal_depth",           # 1: lunghezza cammino più lungo
        "connectivity",           # 2: rapporto archi/nodi
        "abstraction_level",       # 3: generalization_count + avg_confidence
        "predictive_power",       # 4: quanti effetti può predire
        "cross_domain_signature",  # 5: hash della struttura (senza entità)
    ]
    N_DIMS = len(DIMENSION_NAMES)

    def __init__(self, engine: "CausalModelEngine"):
        self.engine = engine
        self._model_coords: Dict[str, List[float]] = {}
        self._initialized = False

    # ── Coordinate Calculation ───────────────────────────────────────

    def compute_coordinates(self, model: CausalModel) -> List[float]:
        """Calcola coordinate n-dimensionali per un modello."""
        n = len(model.entities)
        m = len(model.relations)

        # Dimensione 0: structural_complexity
        structural = min(1.0, (n + m) / 20.0)

        # Dimensione 1: causal_depth (cammino più lungo)
        deepest = self._find_deepest_path(model)
        depth = min(1.0, deepest / 6.0)

        # Dimensione 2: connectivity (archi / nodi)
        connectivity = m / max(1, n)

        # Dimensione 3: abstraction_level
        abstraction = min(1.0, (
            model.generalization_count * 0.3 +
            model.confidence * 0.7
        ))

        # Dimensione 4: predictive_power (effetti predibili / totali)
        if model.terminal_effects:
            pred_power = len(model.terminal_effects) / max(1, n)
        else:
            pred_power = m / max(1, n)
        pred_power = min(1.0, pred_power)

        # Dimensione 5: cross_domain_signature (hash della struttura relazionale)
        signature = self._structural_signature(model)

        return [structural, depth, connectivity, abstraction, pred_power, signature]

    def _find_deepest_path(self, model: CausalModel) -> int:
        """Trova la profondità del cammino più lungo nel modello."""
        if not model.relations:
            return 0

        adj: Dict[str, List[str]] = defaultdict(list)
        for link in model.relations:
            adj[link.cause_entity].append(link.effect_entity)

        max_depth = 0
        for start in model.entities:
            visited: Set[str] = {start}
            stack: List[tuple] = [(start, 1)]
            while stack:
                entity, depth = stack.pop()
                max_depth = max(max_depth, depth)
                for next_e in adj.get(entity, []):
                    if next_e not in visited:
                        visited.add(next_e)
                        stack.append((next_e, depth + 1))

        return max_depth

    def _structural_signature(self, model: CausalModel) -> float:
        """Hash normalizzato della struttura relazionale (senza entità).

        Due modelli con struttura identica ma entità diverse avranno
        signature simile. Esempio: A→B→C e X→Y→Z hanno signature identica.
        """
        if not model.relations:
            return 0.0

        # Calcola distribuzione dei tipi di relazione
        rel_type_counts: Dict[str, int] = {}
        for link in model.relations:
            rel_type_counts[link.relation_type] = rel_type_counts.get(link.relation_type, 0) + 1

        # Calcola pattern di connettività (in-degree / out-degree per nodo)
        in_deg: Dict[str, int] = defaultdict(int)
        out_deg: Dict[str, int] = defaultdict(int)
        for link in model.relations:
            out_deg[link.cause_entity] += 1
            in_deg[link.effect_entity] += 1

        # Normalizza in un singolo float [0, 1]
        all_degs = list(in_deg.values()) + list(out_deg.values())
        avg_deg = sum(all_degs) / max(1, len(all_degs)) if all_degs else 0
        num_types = len(rel_type_counts)

        # Combina: signature = (avg_degree_normalized * 0.6) + (type_diversity * 0.4)
        sig = min(1.0, avg_deg / 5.0) * 0.6 + min(1.0, num_types / 5.0) * 0.4
        return sig

    def build_space(self) -> None:
        """Ricostruisce le coordinate di tutti i modelli attivi."""
        self._model_coords.clear()
        for model in self.engine.store.list_active():
            coords = self.compute_coordinates(model)
            self._model_coords[model.model_id] = coords
        self._initialized = True

    def ensure_built(self):
        if not self._initialized:
            self.build_space()

    # ── Spatial Queries ────────────────────────────────────────────────

    def get_coordinates(self, model_id: str) -> Optional[List[float]]:
        """Restituisce coordinate di un modello."""
        self.ensure_built()
        return self._model_coords.get(model_id)

    def euclidean_distance(self, a: List[float], b: List[float]) -> float:
        """Distanza euclidea tra due coordinate."""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Similarità coseno tra due coordinate."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def find_nearby(
        self,
        model_id: str,
        max_distance: float = 0.3,
        top_k: int = 5,
    ) -> List[tuple]:
        """Trova i modelli più vicini nello spazio causale.

        Args:
            model_id: modello di riferimento
            max_distance: distanza massima euclidea (0-1 normalizzato)
            top_k: numero massimo di risultati

        Returns:
            List of (model_id, distance, similarity) sorted by distance
        """
        self.ensure_built()
        target_coords = self._model_coords.get(model_id)
        if not target_coords:
            return []

        results: List[tuple] = []
        for mid, coords in self._model_coords.items():
            if mid == model_id:
                continue
            dist = self.euclidean_distance(target_coords, coords)
            if dist <= max_distance:
                sim = self.cosine_similarity(target_coords, coords)
                results.append((mid, round(dist, 4), round(sim, 4)))

        results.sort(key=lambda x: x[1])  # sort by distance
        return results[:top_k]

    def find_structurally_similar(
        self,
        model_id: str,
        signature_tolerance: float = 0.1,
        top_k: int = 5,
    ) -> List[tuple]:
        """Trova modelli con signature strutturale identica (indipendentemente dal dominio).

        Esempio: "luce→fotosintesi→crescita" e "capitale→investimento→crescita"
        hanno signature identica pur avendo entità diverse.
        """
        self.ensure_built()
        target_coords = self._model_coords.get(model_id)
        if not target_coords:
            return []

        sig_dim = 5  # index of cross_domain_signature dimension
        target_sig = target_coords[sig_dim]

        results: List[tuple] = []
        for mid, coords in self._model_coords.items():
            if mid == model_id:
                continue
            sig_dist = abs(coords[sig_dim] - target_sig)
            if sig_dist <= signature_tolerance:
                sim = self.cosine_similarity(target_coords, coords)
                results.append((mid, round(sig_dist, 4), round(sim, 4)))

        results.sort(key=lambda x: x[1])
        return results[:top_k]

    # ── Gap Detection ─────────────────────────────────────────────────

    def get_gap_regions(self) -> List[Dict[str, Any]]:
        """Trova regioni vuote dello spazio causale (dove mancano modelli).

        Una gap region è una zona dove non ci sono modelli ma
        ci sono modelli vicini — suggerisce un tipo di modello mancante.
        """
        self.ensure_built()

        if len(self._model_coords) < 3:
            return []

        # Cluster i modelli esistenti
        all_coords = list(self._model_coords.values())
        centroids = self._cluster_simple(all_coords, n_clusters=min(5, len(all_coords)))

        gaps: List[Dict[str, Any]] = []
        for i, c1 in enumerate(centroids):
            for c2 in centroids[i+1:]:
                dist = self.euclidean_distance(c1, c2)
                if dist > 0.5:  # regione grande tra due cluster
                    # Verifica se c'è un modello "ponte" tra loro
                    has_bridge = any(
                        self.euclidean_distance(c1, coords) < 0.3 or
                        self.euclidean_distance(c2, coords) < 0.3
                        for coords in all_coords
                    )
                    if not has_bridge:
                        gaps.append({
                            "region_center_1": c1,
                            "region_center_2": c2,
                            "distance": round(dist, 3),
                            "gap_type": "missing_bridge",
                            "suggested_structure": self._infer_bridge_structure(c1, c2),
                        })

        return gaps

    def _cluster_simple(self, coords: List[List[float]], n_clusters: int) -> List[List[float]]:
        """K-means semplificato per clustering di coordinate."""
        if len(coords) <= n_clusters:
            return coords

        # Scelgo centroidi iniziali come punti equidistanti
        step = len(coords) // n_clusters
        centroids = [coords[i * step] for i in range(n_clusters)]

        for _ in range(5):  # 5 iterazioni
            clusters: List[List[List[float]]] = [[] for _ in range(n_clusters)]
            for c in coords:
                distances = [self.euclidean_distance(c, cent) for cent in centroids]
                nearest = distances.index(min(distances))
                clusters[nearest].append(c)

            new_centroids = []
            for cluster in clusters:
                if cluster:
                    avg = [sum(x[i] for x in cluster) / len(cluster) for i in range(self.N_DIMS)]
                    new_centroids.append(avg)
                else:
                    new_centroids.append(centroids[clusters.index(cluster)])

            if new_centroids == centroids:
                break
            centroids = new_centroids

        return centroids

    def _infer_bridge_structure(self, c1: List[float], c2: List[float]) -> Dict[str, Any]:
        """Deduce la struttura che dovrebbe avere un modello ponte tra due cluster."""
        midpoint = [(a + b) / 2 for a, b in zip(c1, c2)]
        return {
            "midpoint_coords": [round(v, 3) for v in midpoint],
            "suggested_complexity": round((c1[0] + c2[0]) / 2, 2),
            "suggested_depth": round((c1[1] + c2[1]) / 2, 2),
            "suggested_abstraction": round((c1[3] + c2[3]) / 2, 2),
        }

    def get_model_position_description(self, model_id: str) -> str:
        """Descrizione testuale della posizione di un modello nello spazio."""
        coords = self.get_coordinates(model_id)
        if not coords:
            return "unknown"
        parts = []
        for i, (name, val) in enumerate(zip(self.DIMENSION_NAMES, coords)):
            level = "bassa" if val < 0.33 else "media" if val < 0.66 else "alta"
            parts.append(f"{name}={level}({val:.2f})")
        return " | ".join(parts)


# ══════════════════════════════════════════════════════════════════════════
# TASK 2: Gap Detection — Scoprire il Mancante
# ══════════════════════════════════════════════════════════════════════════

class GapDetector:
    """Rileva catene causali incomplete: A → B → ? oppure ? → A → B.

    Il sistema non descrive solo il noto — predice l'ignoto.
    """

    def __init__(self, engine: "CausalModelEngine"):
        self.engine = engine

    def detect_incomplete_chains(self, model_id: str) -> List[Dict[str, Any]]:
        """Trova catene dove manca un nodo intermedio.

        Esempio: "luce → ? → crescita" → candidate: fotosintesi
        """
        model = self.engine.store.get(model_id)
        if not model:
            return []

        gaps: List[Dict[str, Any]] = []
        adj: Dict[str, List[tuple]] = defaultdict(list)  # entity -> [(effect, link_id)]

        for link in model.relations:
            adj[link.cause_entity].append((link.effect_entity, link.link_id))

        # Trova catene lineari: causa -> effetto -> ?
        for cause, links in adj.items():
            for effect, link_id in links:
                # L'effetto ha altri outgoing? Se no, potrebbe mancare un passaggio
                effect_out = adj.get(effect, [])
                cause_in = [(c, lid) for c, lid_list in adj.items() for _, lid in lid_list if lid == link_id]

                # Se effect è un terminal_effect ma non dovrebbe esserlo (alto grado di uscita atteso)
                # oppure se effect ha molti incoming ma pochi outgoing → gap
                in_count = sum(1 for c, lst in adj.items() for e, _ in lst if e == effect)
                out_count = len(effect_out)

                if out_count == 0 and in_count >= 2:
                    # Effect ha multiple cause ma nessun effetto → catena incompleta
                    # suggerisce un nodo mancante TRA causa ed effect
                    candidate = self._suggest_intermediate_node(cause, effect, model)
                    gaps.append({
                        "type": "terminal_gap",
                        "chain": [cause, "?", effect],
                        "cause": cause,
                        "missing_node": candidate.get("name", "?"),
                        "candidate_entities": candidate.get("candidates", []),
                        "gap_confidence": round(
                            self.engine.graph._links.get(link_id, None) and
                            self.engine.graph._links[link_id].confidence or 0.3,
                            3),
                        "suggestion": f"Manca un nodo tra '{cause}' e '{effect}'",
                    })

        return gaps

    def _suggest_intermediate_node(self, cause: str, effect: str, model: CausalModel) -> Dict:
        """Suggerisce possibili entità per il nodo mancante."""
        # Cerca in altri modelli esistenti entità che:
        # 1. Sono spesso tra cause simili e effetti simili
        # 2. Sono correlate a entrambe le entità note

        candidates: Set[str] = set()
        for other_model in self.engine.store.list_active():
            if other_model.model_id == model.model_id:
                continue
            # Se questo modello ha link che vanno da cause simili a effetti simili
            for link in other_model.relations:
                # Entità compatibili semanticamente
                if self._semantic_compatibility(link.cause_entity, cause) > 0.3:
                    if self._semantic_compatibility(link.effect_entity, effect) > 0.3:
                        candidates.add(link.cause_entity)
                        candidates.add(link.effect_entity)

        # Proponi il candidato con più alta compatibilità media
        scored = []
        for c in candidates:
            score = (self._semantic_compatibility(c, cause) +
                     self._semantic_compatibility(c, effect)) / 2
            scored.append((score, c))
        scored.sort(reverse=True)

        return {
            "name": scored[0][1] if scored else "UNKNOWN",
            "candidates": [c for _, c in scored[:3]],
        }

    def _semantic_compatibility(self, entity: str, target: str) -> float:
        """Stima quanto due entità sono semanticamente compatibili.

        Implementazione semplificata: verifica se condividono caratteristiche
        (prefix comune, radice condivisa, entrambi in modelli con struttura simile).
        """
        if entity == target:
            return 1.0

        # Prefix comune
        prefix_len = 0
        for a, b in zip(entity, target):
            if a == b:
                prefix_len += 1
            else:
                break
        prefix_score = prefix_len / max(len(entity), len(target), 1)

        return min(1.0, prefix_score + 0.1)

    def detect_all_gaps(self) -> Dict[str, List[Dict[str, Any]]]:
        """Analizza tutti i modelli e restituisce i gap per ciascuno."""
        result = {}
        for model in self.engine.store.list_active():
            gaps = self.detect_incomplete_chains(model.model_id)
            if gaps:
                result[model.model_id] = gaps
        return result

    def suggest_new_model_from_gap(
        self,
        model_id: str,
        gap: Dict[str, Any],
    ) -> Optional[CausalModel]:
        """Suggerisce e crea un nuovo modello填补 un gap."""
        if gap.get("type") != "terminal_gap":
            return None

        missing = gap.get("missing_node", "X")
        chain = gap.get("chain", [])

        # Costruisci un modello con il nodo mancante
        links = []
        for i, node in enumerate(chain):
            if node == "?":
                continue
            if i < len(chain) - 1:
                next_node = chain[i + 1] if chain[i + 1] != "?" else missing
                links.append({
                    "cause_entity": node,
                    "effect_entity": next_node,
                    "confidence": gap.get("gap_confidence", 0.3) * 0.8,  # ridotta: ipotesi
                    "relation_type": "inferred_gap",
                })

        model = self.engine.build_explicit_model(
            name=f"gap-fill-{model_id[:8]}",
            description=f"Modello creato per colmare gap: {' -> '.join(chain)}",
            entities=[n for n in chain if n != "?"] + ([missing] if missing != "?" else []),
            relations=links,
            confidence=gap.get("gap_confidence", 0.3) * 0.8,
            tags=["gap-fill", "inferred"],
        )
        return model


# ══════════════════════════════════════════════════════════════════════════
# TASK 7: Causal Prediction Validator — Test Predittivo Automatico
# ══════════════════════════════════════════════════════════════════════════

class Prediction(BaseModel):
    prediction_id: str = Field(default_factory=lambda: f"pred-{uuid.uuid4().hex[:8]}")
    model_id: str
    from_entity: str
    to_entity: str
    predicted_confidence: float
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validated: bool = False
    validated_against_episode: Optional[str] = None
    validation_result: Optional[str] = None  # "confirmed" | "falsified" | "inconclusive"


class CausalPredictionValidator:
    """Ogni modello genera predizioni non testate. Le valida contro nuovi episodi.

    Come la tavola periodica: non descrive solo il passato, predice l'ignoto.
    """

    def __init__(self, engine: "CausalModelEngine"):
        self.engine = engine
        self._predictions: Dict[str, Prediction] = {}

    def generate_predictions(
        self,
        model_id: str,
        max_predictions: int = 3,
    ) -> List[Prediction]:
        """Genera predizioni non ancora validate per un modello.

        Una predizione è: dato A, predico B con confidenza X.
        """
        model = self.engine.store.get(model_id)
        if not model:
            return []

        predictions: List[Prediction] = []

        # Trova link ad alta confidenza che potrebbero predire qualcosa di nuovo
        for link in model.relations:
            if link.confidence < 0.5:
                continue

            # Cerca se l'effetto di questo link ha a sua volta effetti non predetti
            for downstream in model.relations:
                if downstream.cause_entity == link.effect_entity:
                    pred = Prediction(
                        model_id=model_id,
                        from_entity=link.cause_entity,
                        to_entity=downstream.effect_entity,
                        predicted_confidence=link.confidence * downstream.confidence,
                    )
                    predictions.append(pred)
                    if len(predictions) >= max_predictions:
                        return predictions

        # Se nessuna predizione trovata, genera una predizione diretta ad alta confidenza
        for link in sorted(model.relations, key=lambda l: l.confidence, reverse=True)[:max_predictions]:
            pred = Prediction(
                model_id=model_id,
                from_entity=link.cause_entity,
                to_entity=link.effect_entity,
                predicted_confidence=link.confidence,
            )
            predictions.append(pred)

        for pred in predictions:
            self._predictions[pred.prediction_id] = pred

        return predictions

    def validate_against_new_episode(
        self,
        prediction: Prediction,
        episode_events: List[Dict[str, Any]],
    ) -> str:
        """Valida una predizione contro un nuovo episodio.

        Returns: "confirmed" | "falsified" | "inconclusive"
        """
        event_types = {e.get("event_type", "") for e in episode_events}

        # Predizione confermata: sia from_entity che to_entity sono presenti
        # nell'ordine corretto (from prima di to)
        from_present = prediction.from_entity in event_types
        to_present = prediction.to_entity in event_types

        # Verifica ordine
        from_idx = next((i for i, e in enumerate(episode_events)
                         if e.get("event_type") == prediction.from_entity), -1)
        to_idx = next((i for i, e in enumerate(episode_events)
                       if e.get("event_type") == prediction.to_entity), -1)

        if from_present and to_present:
            if 0 < from_idx < to_idx:
                result = "confirmed"
                # Aggiorna confidenza del link
                self._update_link_confidence(prediction, confirmed=True)
            elif from_idx >= 0 and to_idx >= 0:
                result = "confirmed"  # stesso tick, comunque confermato
                self._update_link_confidence(prediction, confirmed=True)
            else:
                result = "inconclusive"
        elif from_present and not to_present:
            # from presente ma to assente → potenziale falsificazione
            result = "falsified"
            self._update_link_confidence(prediction, confirmed=False)
        else:
            result = "inconclusive"

        prediction.validated = True
        prediction.validated_against_episode = f"ep-{uuid.uuid4().hex[:6]}"
        prediction.validation_result = result

        return result

    def _update_link_confidence(self, prediction: Prediction, confirmed: bool) -> None:
        """Aggiorna la confidenza del link associato alla predizione."""
        model = self.engine.store.get(prediction.model_id)
        if not model:
            return

        for link in model.relations:
            if link.cause_entity == prediction.from_entity and link.effect_entity == prediction.to_entity:
                if confirmed:
                    link.confirmation_count += 1
                    link.confidence = min(0.99, link.confidence + (1 - link.confidence) * 0.15)
                else:
                    link.falsification_count += 1
                    link.confidence = max(0.05, link.confidence * 0.7)
                link.last_tested_at = datetime.now(timezone.utc).isoformat()
                link.confidence_level = _to_confidence_level(link.confidence)
                self.engine.store.save(model)
                break

    def get_unvalidated_predictions(self, model_id: Optional[str] = None) -> List[Prediction]:
        """Restituisce predizioni non ancora validate."""
        unvalidated = [p for p in self._predictions.values() if not p.validated]
        if model_id:
            unvalidated = [p for p in unvalidated if p.model_id == model_id]
        return unvalidated

    def get_prediction_statistics(self) -> Dict[str, Any]:
        all_preds = list(self._predictions.values())
        validated = [p for p in all_preds if p.validated]
        confirmed = [p for p in validated if p.validation_result == "confirmed"]
        falsified = [p for p in validated if p.validation_result == "falsified"]

        return {
            "total_predictions": len(all_preds),
            "validated": len(validated),
            "unvalidated": len(all_preds) - len(validated),
            "confirmed": len(confirmed),
            "falsified": len(falsified),
            "confirmation_rate": len(confirmed) / len(validated) if validated else 0.0,
        }


# ══════════════════════════════════════════════════════════════════════════
# TASK 3: Cross-Domain Pattern Detector — Periodicità Cognitiva
# ══════════════════════════════════════════════════════════════════════════

class CrossDomainPatternDetector:
    """Cerca pattern strutturali identici in domini completamente diversi.

    Esempio: Risorsa→Trasformazione→Energia→Crescita
    appare in biologia, economia, ecologia, reti neurali, organizzazioni sociali.

    Quando SPEACE identifica queste periodicità, sta costruendo astrazioni profonde.
    """

    def __init__(self, engine: "CausalModelEngine"):
        self.engine = engine

    def extract_structural_signature(self, model: CausalModel) -> str:
        """Estrae la signature strutturale SENZA guardare le entità.

        Due modelli con signature identica hanno la stessa struttura relazionale
        pur avendo entità completamente diverse.
        """
        if not model.relations:
            return "empty"

        # Sequence di relation_types: e.g. "causal->enables->causal"
        rel_sequence = "->".join(sorted(
            link.relation_type for link in model.relations
        ))

        # Connectivity pattern: in/out degree sequence
        in_deg: Dict[str, int] = defaultdict(int)
        out_deg: Dict[str, int] = defaultdict(int)
        for link in model.relations:
            out_deg[link.cause_entity] += 1
            in_deg[link.effect_entity] += 1

        # Normalizza entity names a placeholder per comparabilità
        # (usa solo gradi di connettività)
        in_seq = "-".join(str(in_deg.get(k, 0)) for k in sorted(in_deg))
        out_seq = "-".join(str(out_deg.get(k, 0)) for k in sorted(out_deg))

        # Shape: linear | branched | cycle | hub
        shape = self._detect_shape(model)

        return f"{rel_sequence}|{in_seq}|{out_seq}|{shape}"

    def _detect_shape(self, model: CausalModel) -> str:
        """Rileva la forma topologica del modello."""
        in_deg: Dict[str, int] = defaultdict(int)
        out_deg: Dict[str, int] = defaultdict(int)
        for link in model.relations:
            out_deg[link.cause_entity] += 1
            in_deg[link.effect_entity] += 1

        max_in = max(in_deg.values()) if in_deg else 0
        max_out = max(out_deg.values()) if out_deg else 0

        if max_in > 2 or max_out > 2:
            return "hub"
        if len(model.relations) > len(model.entities):
            return "branched"
        if self._has_cycle(model):
            return "cycle"
        return "linear"

    def _has_cycle(self, model: CausalModel) -> bool:
        """Check se il modello ha un ciclo."""
        adj: Dict[str, List[str]] = defaultdict(list)
        for link in model.relations:
            adj[link.cause_entity].append(link.effect_entity)

        for start in model.entities:
            visited: Set[str] = set()
            stack = [start]
            while stack:
                node = stack.pop()
                if node in visited:
                    return True
                visited.add(node)
                stack.extend(adj.get(node, []))
        return False

    def find_periodicities(self, min_models: int = 2) -> List[Dict[str, Any]]:
        """Trova pattern strutturali che si ripetono in domini diversi.

        Returns: pattern con almeno min_models modelli che condividono la stessa signature.
        """
        # Group models by signature
        signature_groups: Dict[str, List[CausalModel]] = defaultdict(list)
        for model in self.engine.store.list_active():
            sig = self.extract_structural_signature(model)
            signature_groups[sig].append(model)

        periodicities: List[Dict[str, Any]] = []
        for sig, models in signature_groups.items():
            if len(models) < min_models:
                continue

            domains = list(set(model.tags for model in models) & {"biologia", "economia", "ecologia", "sociale", "neurale", "fisica"})
            if not domains:
                domains = ["cross-domain"]

            periodicities.append({
                "signature": sig,
                "pattern_shape": sig.split("|")[-1],
                "count": len(models),
                "models": [m.model_id for m in models],
                "model_names": [m.name for m in models],
                "domains": domains,
                "abstraction_level": round(sum(m.confidence for m in models) / len(models), 3),
            })

        periodicities.sort(key=lambda p: p["count"], reverse=True)
        return periodicities

    def generalize_to_abstraction(
        self,
        pattern_id: str,
        periodic_models: List[CausalModel],
    ) -> Optional[CausalModel]:
        """Da modelli con signature identica → principio generativo astratto.

        Esempio: tutti i pattern "risorsa→trasformazione→energia→crescita"
        diventano un principio: "RisorsaStrutturale → TrasformazioneStrutturale →
        OutputStrutturale"
        """
        if len(periodic_models) < 2:
            return None

        # Unisci le strutture relazionali (media delle confidenze)
        all_links: Dict[str, CausalLink] = {}
        for model in periodic_models:
            for link in model.relations:
                key = f"{link.cause_entity}_{link.effect_entity}"
                if key not in all_links:
                    all_links[key] = link
                else:
                    old = all_links[key]
                    new_conf = (old.confidence + link.confidence) / 2
                    all_links[key] = CausalLink(
                        link_id=f"cl-{uuid.uuid4().hex[:8]}",
                        cause_entity=f"[ABS]{link.cause_entity[:20]}",
                        effect_entity=f"[ABS]{link.effect_entity[:20]}",
                        relation_type=link.relation_type,
                        description=f"Principio generico da {len(periodic_models)} modelli",
                        confidence=new_conf,
                        confidence_level=_to_confidence_level(new_conf),
                        confirmation_count=old.confirmation_count + link.confirmation_count,
                    )

        all_causes = {l.cause_entity for l in all_links.values()}
        all_effects = {l.effect_entity for l in all_links.values()}

        abstract_model = CausalModel(
            name=f"Abstraction-{pattern_id[:8]}",
            description=f"Principio generativo derivato da {len(periodic_models)} modelli con signature identica",
            entities=[f"[ABS]{e[:20]}" for e in list(all_causes | all_effects)],
            relations=list(all_links.values()),
            root_causes=list(all_causes - all_effects),
            terminal_effects=list(all_effects - all_causes),
            confidence=sum(m.confidence for m in periodic_models) / len(periodic_models),
            confidence_level=_to_confidence_level(
                sum(m.confidence for m in periodic_models) / len(periodic_models)
            ),
            tags=["abstracted", "cross-domain", "periodic"],
            emergence_type="generalized",
        )

        self.engine._add_model_to_graph(abstract_model)
        self.engine.store.save(abstract_model)
        return abstract_model


# ══════════════════════════════════════════════════════════════════════════
# TASK 5: Concept Atomic Number — Complessità Minima di un Concetto
# ══════════════════════════════════════════════════════════════════════════

class ConceptAtomicNumber:
    """Assegna un 'peso atomico' a ogni CausalModel.

    Basato su:
    - num nodi essenziali
    - profondità del cammino più lungo
    - connettività (in/out degree)
    - potere predittivo (quante cose può predire)

    Simile al numero atomico nella tavola periodica: più alto = più complesso.
    """

    def compute(self, model_id: str, engine: "CausalModelEngine") -> float:
        """Calcola il peso atomico di un concetto [0, 100]."""
        model = engine.store.get(model_id)
        if not model:
            return 0.0

        n = len(model.entities)
        m = len(model.relations)

        # Componente 1: base complexity (num nodi + archi)
        base = (n * 0.5 + m * 0.5)

        # Componente 2: profondità del cammino più lungo
        deepest = 0
        adj: Dict[str, List[str]] = defaultdict(list)
        for link in model.relations:
            adj[link.cause_entity].append(link.effect_entity)
        for start in model.entities:
            visited: Set[str] = {start}
            stack: List[tuple] = [(start, 1)]
            while stack:
                entity, depth = stack.pop()
                deepest = max(deepest, depth)
                for next_e in adj.get(entity, []):
                    if next_e not in visited:
                        visited.add(next_e)
                        stack.append((next_e, depth + 1))

        # Componente 3: connettività media
        in_deg: Dict[str, int] = defaultdict(int)
        out_deg: Dict[str, int] = defaultdict(int)
        for link in model.relations:
            out_deg[link.cause_entity] += 1
            in_deg[link.effect_entity] += 1
        all_deg = list(in_deg.values()) + list(out_deg.values())
        avg_conn = sum(all_deg) / max(1, len(all_deg)) if all_deg else 0

        # Componente 4: potere predittivo (effetti diretti + indiretti)
        pred_effects = engine.infer_effects(model_id, list(model.root_causes)[0] if model.root_causes else model.entities[0], max_depth=3)
        predictive_power = len(pred_effects.predicted_entities)

        # Formula pesata
        atomic = (
            base * 0.20 +
            deepest * 0.30 +
            avg_conn * 0.20 +
            predictive_power * 0.30
        )

        return round(min(100.0, atomic), 2)

    def rank_all(self, engine: "CausalModelEngine") -> List[tuple]:
        """Classifica tutti i modelli per peso atomico."""
        ranked = []
        for model in engine.store.list_active():
            weight = self.compute(model.model_id, engine)
            ranked.append((model.model_id, model.name, weight))
        ranked.sort(key=lambda x: x[2], reverse=True)
        return ranked


# ══════════════════════════════════════════════════════════════════════════
# TASK 6: PrincipleGenerator + MetaPrincipleEngine — L4, L5, L6
# ══════════════════════════════════════════════════════════════════════════

class Principle(BaseModel):
    """L4 — Principio generativo: astrazione da modelli simili."""
    principle_id: str = Field(default_factory=lambda: f"princ-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    source_model_ids: List[str] = Field(default_factory=list)
    abstraction_level: int = 4  # L4
    entities: List[str] = Field(default_factory=list)  # entità astratte
    structural_template: str = ""  # forma generica
    confidence: float = 0.5
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    activation_count: int = 0


class MetaPrinciple(BaseModel):
    """L5-L6 — Meta-principio: principio che governa altri principi."""
    meta_id: str = Field(default_factory=lambda: f"meta-{uuid.uuid4().hex[:8]}")
    name: str
    description: str = ""
    governed_principle_ids: List[str] = Field(default_factory=list)
    governing_rules: List[str] = Field(default_factory=list)  # regole di trasformazione
    abstraction_level: int = 5  # L5 o L6
    meta_pattern: str = ""  # pattern di secondo livello
    confidence: float = 0.4
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    activation_count: int = 0


class PrincipleStore:
    """Storage per principi e meta-principi."""
    def __init__(self, path: str = "data/agi_team/principles.jsonl"):
        from pathlib import Path
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._principles: Dict[str, Principle] = {}
        self._meta_principles: Dict[str, MetaPrinciple] = {}
        self._load()

    def _load(self):
        if not self._path.exists():
            return
        import json
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("abstraction_level", 0) >= 5:
                    self._meta_principles[data["meta_id"]] = MetaPrinciple(**data)
                else:
                    self._principles[data["principle_id"]] = Principle(**data)
            except Exception:
                continue

    def _persist(self):
        import json
        lines = []
        for p in list(self._principles.values()) + list(self._meta_principles.values()):
            lines.append(p.model_dump_json())
        self._path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def save_principle(self, p: Principle):
        self._principles[p.principle_id] = p
        self._persist()

    def save_meta(self, m: MetaPrinciple):
        self._meta_principles[m.meta_id] = m
        self._persist()

    def list_principles(self) -> List[Principle]:
        return list(self._principles.values())

    def list_meta(self) -> List[MetaPrinciple]:
        return list(self._meta_principles.values())


class PrincipleGenerator:
    """L4: Genera principi generativi da modelli causali simili.

    Passo: Cell Assemblies → Modelli causali → Principi generativi
    """

    def __init__(self, engine: "CausalModelEngine", store: Optional[PrincipleStore] = None):
        self.engine = engine
        self.store = store or PrincipleStore()

    def generate_from_models(
        self,
        model_ids: List[str],
        name: str,
        description: str = "",
    ) -> Optional[Principle]:
        """Genera un principio da un gruppo di modelli causalmente simili."""
        models = [self.engine.store.get(mid) for mid in model_ids if self.engine.store.get(mid)]
        if len(models) < 2:
            return None

        # Estrai template strutturale comune
        rel_types = set()
        for m in models:
            rel_types.update(l.relation_type for l in m.relations)

        # Entities astratte: mantieni solo la struttura (nomi generici)
        abstract_entities = [f"[E{i}]" for i in range(max(len(m.entities) for m in models))]

        # Structural template
        template = "+".join(sorted(rel_types))

        principle = Principle(
            name=name,
            description=description or f"Principio generativo da {len(models)} modelli",
            source_model_ids=model_ids,
            abstraction_level=4,
            entities=abstract_entities,
            structural_template=template,
            confidence=sum(m.confidence for m in models) / len(models) * 0.95,
            tags=["principle", "L4", "generated"],
        )

        self.store.save_principle(principle)
        return principle

    def generate_from_cross_domain_pattern(
        self,
        pattern: Dict[str, Any],
    ) -> Optional[Principle]:
        """Genera un principio da un pattern cross-dominio rilevato."""
        model_ids = pattern.get("models", [])
        if len(model_ids) < 2:
            return None

        return self.generate_from_models(
            model_ids=model_ids,
            name=f"PeriodicPrinciple-{pattern.get('pattern_shape', 'unknown')}",
            description=f"Pattern periodico: {pattern.get('signature', '')}",
        )


class MetaPrincipleEngine:
    """L5-L6: Meta-principi che governano altri principi.

    Rileva pattern di secondo livello tra principi.
    """

    def __init__(self, generator: PrincipleGenerator, store: Optional[PrincipleStore] = None):
        self.generator = generator
        self.store = store or PrincipleStore()

    def find_meta_patterns(self, min_principles: int = 3) -> List[Dict[str, Any]]:
        """Trova pattern tra principi (L5): principi che governano altri principi."""
        principles = self.store.list_principles()
        if len(principles) < min_principles:
            return []

        meta_patterns: List[Dict[str, Any]] = []

        # Cerca principi che condividono la stessa struttura di template
        template_groups: Dict[str, List[Principle]] = defaultdict(list)
        for p in principles:
            template_groups[p.structural_template].append(p)

        for template, group in template_groups.items():
            if len(group) >= 2:
                meta_patterns.append({
                    "type": "same_template",
                    "governed_principle_ids": [p.principle_id for p in group],
                    "template": template,
                    "count": len(group),
                    "abstraction_level": 5,
                    "description": f"{len(group)} principi condividono lo stesso template strutturale: {template}",
                })

        # Cerca principi con stesso tags pattern
        tag_groups: Dict[str, List[Principle]] = defaultdict(list)
        for p in principles:
            key = "+".join(sorted(p.tags))
            tag_groups[key].append(p)

        for tag_key, group in tag_groups.items():
            if len(group) >= 3:
                meta_patterns.append({
                    "type": "same_tags",
                    "governed_principle_ids": [p.principle_id for p in group],
                    "tags": tag_key.split("+"),
                    "count": len(group),
                    "abstraction_level": 6,
                    "description": f"{len(group)} principi condividono lo stesso pattern di tags",
                })

        return meta_patterns

    def generate_meta_principle(
        self,
        meta_pattern: Dict[str, Any],
        name: str,
    ) -> Optional[MetaPrinciple]:
        """Genera un meta-principio da un pattern rilevato."""
        meta = MetaPrinciple(
            name=name,
            description=meta_pattern.get("description", ""),
            governed_principle_ids=meta_pattern.get("governed_principle_ids", []),
            governing_rules=[meta_pattern.get("type", "unknown")],
            abstraction_level=meta_pattern.get("abstraction_level", 5),
            meta_pattern=meta_pattern.get("template", meta_pattern.get("tags", [])),
            confidence=0.5,
            tags=["meta-principle", f"L{meta_pattern.get('abstraction_level', 5)}"],
        )

        self.store.save_meta(meta)
        return meta

    def get_hierarchy(self) -> Dict[str, Any]:
        """Restituisce la gerarchia completa L1-L6."""
        principles = self.store.list_principles()
        metas = self.store.list_meta()

        return {
            "L4_principles": {
                "count": len(principles),
                "items": [
                    {"id": p.principle_id, "name": p.name, "confidence": p.confidence,
                     "template": p.structural_template}
                    for p in principles
                ],
            },
            "L5_L6_meta_principles": {
                "count": len(metas),
                "items": [
                    {"id": m.meta_id, "name": m.name, "governed": len(m.governed_principle_ids),
                     "abstraction": m.abstraction_level}
                    for m in metas
                ],
            },
        }


# ══════════════════════════════════════════════════════════════════════════
# TASK 4: Cognitive Compression Pipeline — dalla memoria al principio
# ══════════════════════════════════════════════════════════════════════════

class CognitiveCompressionPipeline:
    """Pipeline completa: Episodi → CausalModels → Principi → Meta-principi.

    L'obiettivo non è accumulare conoscenza, ma comprimerla.
    Questa pipeline implementa il passaggio da "memorizzare eventi"
    a "scoprire la struttura organizzatrice che rende inevitabili quegli eventi".
    """

    def __init__(self, engine: "CausalModelEngine"):
        self.engine = engine
        self.gap_detector = GapDetector(engine)
        self.cross_domain = CrossDomainPatternDetector(engine)
        self.validator = CausalPredictionValidator(engine)
        self.principle_gen = PrincipleGenerator(engine)
        self.meta_engine = MetaPrincipleEngine(self.principle_gen)

    def compress_episodes(
        self,
        episode_ids: List[str],
        from_episodic_memory: Optional[Any] = None,
    ) -> List[CausalModel]:
        """L1→L2→L3: Episodi → CausalModels.

        Args:
            episode_ids: IDs degli episodi da comprimere
            from_episodic_memory: istanza EpisodicMemory per leggere i dati
        """
        models = []
        for ep_id in episode_ids:
            if from_episodic_memory:
                ep = from_episodic_memory.get_episode(ep_id)
                if ep:
                    events = [
                        {"event_type": e.event_type, "source_module": e.source_module}
                        for e in ep.events
                    ]
                    model = self.engine.infer_from_episode(events, ep_id)
                    if model:
                        models.append(model)

            # Genera predizioni non testate
            for model in models:
                self.validator.generate_predictions(model.model_id)

        return models

    def build_periodic_table(self) -> Dict[str, Any]:
        """L3→L4: Costruisce la tavola periodica cognitiva.

        Dopo aver compresso episodi e generato modelli:
        1. Trova periodicità cross-dominio
        2. Genera principi generativi
        3. Genera meta-principi
        """
        # 1. Trova periodicità
        periodicities = self.cross_domain.find_periodicities()
        abstracted = []
        for p in periodicities:
            model_ids = p.get("models", [])
            if len(model_ids) >= 2:
                principle = self.principle_gen.generate_from_cross_domain_pattern(p)
                if principle:
                    abstracted.append(principle.principle_id)

        # 2. Trova meta-patterns
        meta_patterns = self.meta_engine.find_meta_patterns()

        # 3. Genera meta-principi
        meta_principles = []
        for mp in meta_patterns:
            meta = self.meta_engine.generate_meta_principle(mp, name=f"Meta-{mp['type']}")
            if meta:
                meta_principles.append(meta.meta_id)

        hierarchy = self.meta_engine.get_hierarchy()

        return {
            "periodicities_found": len(periodicities),
            "principles_generated": len(abstracted),
            "meta_principles_generated": len(meta_principles),
            "hierarchy": hierarchy,
            "next_recommendation": self._recommend_next_action(),
        }

    def _recommend_next_action(self) -> str:
        """Suggerisce la prossima azione nella pipeline."""
        stats = self.engine.get_statistics()
        gaps = self.gap_detector.detect_all_gaps()

        if stats["models_active"] < 5:
            return "Insufficient models. Continue compressing episodes."
        elif gaps:
            return f"Found {sum(len(g) for g in gaps.values())} gaps. Consider building gap-filling models."
        elif stats["links_high_confidence"] < 3:
            return "Low confidence links. Run prediction validation."
        else:
            return "Ready for abstraction: generate principles from high-confidence models."

    def run_full_pipeline(
        self,
        episode_ids: List[str],
        from_episodic_memory: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Esegue la pipeline completa L1→L6.

        Args:
            episode_ids: episodi da processare
            from_episodic_memory: accesso a EpisodicMemory

        Returns:
            Report completo della compressione
        """
        # Step 1: Compress episodes → models
        models = self.compress_episodes(episode_ids, from_episodic_memory)

        # Step 2: Detect gaps
        all_gaps = self.gap_detector.detect_all_gaps()

        # Step 3: Build periodic table
        periodic_result = self.build_periodic_table()

        return {
            "episodes_processed": len(episode_ids),
            "models_created": len(models),
            "gaps_detected": sum(len(g) for g in all_gaps.values()),
            "periodicities": periodic_result.get("periodicities_found", 0),
            "principles": periodic_result.get("principles_generated", 0),
            "meta_principles": periodic_result.get("meta_principles_generated", 0),
            "hierarchy": periodic_result.get("hierarchy", {}),
            "recommendation": periodic_result.get("next_recommendation", ""),
        }


# ── Helper ─────────────────────────────────────────────────────────────

def _to_confidence_level(confidence: float) -> ConfidenceLevel:
    if confidence >= 0.8:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.5:
        return ConfidenceLevel.MEDIUM
    elif confidence >= 0.2:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.SPECULATIVE