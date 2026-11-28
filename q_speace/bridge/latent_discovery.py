"""Stage-1 Autonomous Latent State Discovery & Cold-Boot Persistence (T261–T262).

Implements domain-agnostic discovery of undeclared latent states and dynamic
precondition-clobbering (mutex) constraints from prediction errors inside an
asynchronous Global Workspace, backed by SQLite + Epigenetic consolidation
verified across real OS process restarts.

Safety & Scope (AGENTS.md §2, T208, T217):
- Zero domain-specific string heuristics in the learner or specialists.
- ``SymbolRegistry`` initialized with ``mutex_pairs=()`` and zero latent symbols.
- Strictly sandboxed in-memory ``LatentSandboxTwin`` (``mcp_actuation_permitted=False``).
- CPU-only execution under ``< 250 MB`` RSS enforced by ``MemoryBudgetGuard``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..routing import GOAPAction, GOAPPlanner
from ..self_improvement_cortex.epigenetics import EpigeneticEngine
from ..singularity.codec import resolve_runtime_controls
from ..singularity.schema import ConstitutionalGenome, EpigeneticProfile
from ..spiking.encoder import dynamic_spikes
from ..spiking_brain.memory import SemanticEpisodicMemory, embed_text_hashed
from ..spiking_brain.types import ThinkResult
from .grounding import SymbolRegistry
from .stage1_workspace import (
    AsyncGlobalWorkspace,
    CoalitionProposal,
    WorkspaceBlackboard,
    WorkspaceTelemetrySummary,
    read_process_rss_mb,
)


@dataclass
class DiscoveredLatentRule:
    """Candidate or consolidated latent distinction discovered from discrepancy."""

    latent_id: str
    surface_facts: frozenset[str]
    probe_name: str
    probe_token: str
    blocked_action: str
    clobbered_fluent: str | None
    remediation_action: str | None
    discriminative_score: float
    promotion_count: int = 0
    suppression_count: int = 0
    consolidated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "latent_id": self.latent_id,
            "surface_facts": sorted(self.surface_facts),
            "probe_name": self.probe_name,
            "probe_token": self.probe_token,
            "blocked_action": self.blocked_action,
            "clobbered_fluent": self.clobbered_fluent,
            "remediation_action": self.remediation_action,
            "discriminative_score": round(self.discriminative_score, 4),
            "promotion_count": self.promotion_count,
            "suppression_count": self.suppression_count,
            "consolidated": self.consolidated,
        }


@dataclass(frozen=True)
class EpisodeTransitionSample:
    """Empirical observation of one attempted primary action on a surface state."""

    surface_facts: frozenset[str]
    probe_readings: dict[str, str]
    attempted_action: str
    succeeded: bool
    clobbered_fluents: frozenset[str]
    recovery_action: str | None


class EpistemicSymbolSandbox:
    """Isolated registry of runtime-discovered latent predicates and dynamic mutexes.

    Strictly separated from immutable ``ConstitutionalGenome`` / ``SeedGenome``.
    """

    def __init__(self) -> None:
        self._rules: dict[str, DiscoveredLatentRule] = {}

    @property
    def rules(self) -> Mapping[str, DiscoveredLatentRule]:
        return self._rules

    def upsert(self, rule: DiscoveredLatentRule) -> None:
        self._rules[rule.latent_id] = rule

    def retract(self, latent_id: str) -> DiscoveredLatentRule | None:
        """Remove a falsified candidate rule (T263 belief retraction)."""
        return self._rules.pop(latent_id, None)

    def consolidated_rules(self) -> tuple[DiscoveredLatentRule, ...]:
        return tuple(r for r in self._rules.values() if r.consolidated)

    def rules_for_surface(
        self,
        surface_facts: frozenset[str],
        *,
        require_consolidated: bool = False,
    ) -> tuple[DiscoveredLatentRule, ...]:
        matches = [
            r
            for r in self._rules.values()
            if r.surface_facts == surface_facts and (not require_consolidated or r.consolidated)
        ]
        return tuple(sorted(matches, key=lambda r: r.latent_id))


class LatentDistinctionLearner:
    """Domain-agnostic discrepancy detector and contrastive probe-rule inducer."""

    def __init__(
        self,
        *,
        epigenetics: EpigeneticEngine | None = None,
        sandbox: EpistemicSymbolSandbox | None = None,
        min_discriminative_score: float = 0.80,
        enable_discovery: bool = True,
    ) -> None:
        self.epigenetics = epigenetics or EpigeneticEngine(
            min_promotions=3, stability_threshold=0.70
        )
        self.sandbox = sandbox or EpistemicSymbolSandbox()
        self.min_discriminative_score = float(min_discriminative_score)
        self.enable_discovery = bool(enable_discovery)
        self.ambiguous_surfaces: set[frozenset[str]] = set()
        self._samples: list[EpisodeTransitionSample] = []
        self._mint_counter = 0
        # T263: falsified (surface, action, probe_name, probe_token) hypotheses are never re-minted
        self.retracted_signatures: set[tuple[frozenset[str], str, str, str]] = set()
        self.retraction_suppression_threshold = 2

    def flag_discrepancy(self, surface_facts: frozenset[str]) -> None:
        if self.enable_discovery:
            self.ambiguous_surfaces.add(surface_facts)

    def record_episode_sample(self, sample: EpisodeTransitionSample) -> DiscoveredLatentRule | None:
        """Record an episode transition and induce a latent rule if contrast emerges."""
        if not self.enable_discovery:
            return None
        self._samples.append(sample)
        if not sample.succeeded:
            self.ambiguous_surfaces.add(sample.surface_facts)
        return self._try_induce_rule(sample.surface_facts, sample.attempted_action)

    def _try_induce_rule(
        self, surface_facts: frozenset[str], action_name: str
    ) -> DiscoveredLatentRule | None:
        existing = [
            r
            for r in self.sandbox.rules.values()
            if r.surface_facts == surface_facts and r.blocked_action == action_name
        ]
        if existing:
            return existing[0]

        relevant = [
            s
            for s in self._samples
            if s.surface_facts == surface_facts
            and s.attempted_action == action_name
            and s.probe_readings
        ]
        failures = [s for s in relevant if not s.succeeded]
        successes = [s for s in relevant if s.succeeded]
        if not failures or not successes:
            return None

        candidate_pairs: set[tuple[str, str]] = set()
        for f in failures:
            for p_name, p_tok in f.probe_readings.items():
                candidate_pairs.add((p_name, p_tok))

        best_pair: tuple[str, str] | None = None
        best_score = 0.0
        for p_name, p_tok in sorted(candidate_pairs):
            if (surface_facts, action_name, p_name, p_tok) in self.retracted_signatures:
                continue
            # Contrast only over episodes where this probe was actually measured:
            # an unmeasured probe is missing evidence, not a negative reading.
            meas_fail = [f for f in failures if p_name in f.probe_readings]
            meas_succ = [s for s in successes if p_name in s.probe_readings]
            if not meas_fail or not meas_succ:
                continue
            tp = sum(1 for f in meas_fail if f.probe_readings[p_name] == p_tok)
            fp = sum(1 for s in meas_succ if s.probe_readings[p_name] == p_tok)
            recall = tp / len(meas_fail)
            precision = tp / max(tp + fp, 1)
            specificity = 1.0 - (fp / len(meas_succ))
            score = recall * precision * specificity
            if score > best_score:
                best_score = score
                best_pair = (p_name, p_tok)

        if best_pair is None or best_score < self.min_discriminative_score:
            return None

        while f"latent_state_{self._mint_counter}" in self.sandbox.rules:
            self._mint_counter += 1
        latent_id = f"latent_state_{self._mint_counter}"
        self._mint_counter += 1

        clobbered_counts: dict[str, int] = {}
        recovery_counts: dict[str, int] = {}
        for f in failures:
            for cf in f.clobbered_fluents:
                clobbered_counts[cf] = clobbered_counts.get(cf, 0) + 1
            if f.recovery_action:
                recovery_counts[f.recovery_action] = recovery_counts.get(f.recovery_action, 0) + 1

        clobbered_fluent = (
            max(clobbered_counts.items(), key=lambda kv: kv[1])[0] if clobbered_counts else None
        )
        remediation_action = (
            max(recovery_counts.items(), key=lambda kv: kv[1])[0] if recovery_counts else None
        )

        self.epigenetics.register(latent_id)
        rule = DiscoveredLatentRule(
            latent_id=latent_id,
            surface_facts=surface_facts,
            probe_name=best_pair[0],
            probe_token=best_pair[1],
            blocked_action=action_name,
            clobbered_fluent=clobbered_fluent,
            remediation_action=remediation_action,
            discriminative_score=best_score,
        )
        self.sandbox.upsert(rule)
        return rule

    def record_rule_validation(self, latent_id: str, *, verified: bool) -> bool:
        """Promote or suppress a candidate latent rule via ``EpigeneticEngine``."""
        rule = self.sandbox.rules.get(latent_id)
        if rule is None:
            return False
        if verified:
            self.epigenetics.promote(
                latent_id, confidence=0.95, source="empirical_latent_prediction"
            )
        else:
            self.epigenetics.suppress(
                latent_id, confidence=0.90, source="empirical_latent_falsification"
            )
        state = self.epigenetics.state_of(latent_id)
        if state is not None:
            rule.promotion_count = state.promotion_count
            rule.suppression_count = state.suppression_count
            rule.consolidated = state.consolidated
            if self.epigenetics.should_rollback(latent_id):
                rule.consolidated = False
            # T263 retraction: a non-consolidated candidate that keeps being falsified and
            # cannot meet the consolidation stability bar is withdrawn, freeing the
            # (surface, action) slot so a better-supported hypothesis can be induced.
            # Applies to consolidated rules too: a rule whose stability has fallen below the
            # consolidation bar no longer satisfies the criterion that made it permanent.
            if (
                state.suppression_count >= self.retraction_suppression_threshold
                and state.stability_ratio < self.epigenetics._stability_threshold
            ):
                self.retracted_signatures.add(
                    (rule.surface_facts, rule.blocked_action, rule.probe_name, rule.probe_token)
                )
                state.consolidated = False
                rule.consolidated = False
                self.sandbox.retract(latent_id)
                return False
        return rule.consolidated


class Stage1PersistenceStore:
    """SQLite persistence combining ``SemanticEpisodicMemory``, rules & epigenome."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.episodic_memory = SemanticEpisodicMemory(self.db_path, max_entries=2048, dim=64)
        self._conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        self._init_tables()

    def _init_tables(self) -> None:
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stage1_consolidated_rules (
                latent_id TEXT PRIMARY KEY,
                surface_facts_json TEXT NOT NULL,
                probe_name TEXT NOT NULL,
                probe_token TEXT NOT NULL,
                blocked_action TEXT NOT NULL,
                clobbered_fluent TEXT,
                remediation_action TEXT,
                discriminative_score REAL NOT NULL,
                promotion_count INTEGER NOT NULL,
                suppression_count INTEGER NOT NULL,
                consolidated INTEGER NOT NULL,
                updated_ts REAL NOT NULL
            )
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stage1_epigenome_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                genome_sha256 TEXT NOT NULL,
                values_json TEXT NOT NULL,
                generation INTEGER NOT NULL,
                updated_ts REAL NOT NULL
            )
            """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stage1_retracted_signatures (
                surface_facts_json TEXT NOT NULL,
                blocked_action TEXT NOT NULL,
                probe_name TEXT NOT NULL,
                probe_token TEXT NOT NULL,
                PRIMARY KEY (surface_facts_json, blocked_action, probe_name, probe_token)
            )
            """)
        self._conn.commit()

    async def save_state(
        self,
        learner: LatentDistinctionLearner,
        profile: EpigeneticProfile,
        *,
        freeze_epigenome: bool = False,
    ) -> int:
        """Persist rules and updated ``EpigeneticProfile``; return consolidated count."""
        cur = self._conn.cursor()
        consolidated_saved = 0
        now = time.time()
        episodic_entries: list[ThinkResult] = []
        for rule in learner.sandbox.rules.values():
            effective_consolidated = bool(rule.consolidated and not freeze_epigenome)
            if effective_consolidated:
                consolidated_saved += 1
            cur.execute(
                """
                INSERT INTO stage1_consolidated_rules (
                    latent_id, surface_facts_json, probe_name, probe_token,
                    blocked_action, clobbered_fluent, remediation_action,
                    discriminative_score, promotion_count, suppression_count,
                    consolidated, updated_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(latent_id) DO UPDATE SET
                    discriminative_score=excluded.discriminative_score,
                    promotion_count=excluded.promotion_count,
                    suppression_count=excluded.suppression_count,
                    consolidated=excluded.consolidated,
                    updated_ts=excluded.updated_ts
                """,
                (
                    rule.latent_id,
                    json.dumps(sorted(rule.surface_facts)),
                    rule.probe_name,
                    rule.probe_token,
                    rule.blocked_action,
                    rule.clobbered_fluent,
                    rule.remediation_action,
                    rule.discriminative_score,
                    rule.promotion_count,
                    rule.suppression_count,
                    1 if effective_consolidated else 0,
                    now,
                ),
            )
            if effective_consolidated:
                summary_txt = (
                    f"consolidated:{rule.latent_id}|probe={rule.probe_name}:{rule.probe_token}|"
                    f"block={rule.blocked_action}|remediate={rule.remediation_action}"
                )
                emb = embed_text_hashed(summary_txt, dim=8)
                belief = np.abs(emb) / max(float(np.sum(np.abs(emb))), 1e-9)
                episodic_entries.append(
                    ThinkResult(
                        text=summary_txt,
                        confidence=min(1.0, rule.discriminative_score),
                        belief=belief,
                        spikes=dynamic_spikes(belief),
                        plasticity=np.ones_like(belief),
                        n_tokens=16,
                        latency_s=0.001,
                    )
                )

        new_values = dict(profile.values)
        if consolidated_saved > 0 and not freeze_epigenome:
            new_values["memory_retention"] = min(
                0.98, round(new_values.get("memory_retention", 0.75) + 0.12, 4)
            )
            new_values["verification_depth"] = min(
                1.00, round(new_values.get("verification_depth", 0.60) + 0.10, 4)
            )
            new_values["exploration_rate"] = max(
                0.02, round(new_values.get("exploration_rate", 0.15) - 0.05, 4)
            )
        gen = profile.generation + (1 if consolidated_saved > 0 and not freeze_epigenome else 0)
        cur.execute(
            """
            INSERT INTO stage1_epigenome_state (id, genome_sha256, values_json, generation, updated_ts)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                genome_sha256=excluded.genome_sha256,
                values_json=excluded.values_json,
                generation=excluded.generation,
                updated_ts=excluded.updated_ts
            """,
            (
                profile.genome.genome_sha256(),
                json.dumps(new_values, sort_keys=True),
                gen,
                now,
            ),
        )
        # T266-06: falsified hypotheses are negative knowledge and survive cold boot.
        if not freeze_epigenome:
            for surf, act, p_name, p_tok in sorted(
                learner.retracted_signatures, key=lambda t: (sorted(t[0]), t[1], t[2], t[3])
            ):
                cur.execute(
                    "INSERT OR IGNORE INTO stage1_retracted_signatures VALUES (?, ?, ?, ?)",
                    (json.dumps(sorted(surf)), act, p_name, p_tok),
                )
        self._conn.commit()
        for entry in episodic_entries:
            await self.episodic_memory.put(entry)
        return consolidated_saved

    def load_consolidated_into(
        self,
        learner: LatentDistinctionLearner,
        *,
        expected_genome: ConstitutionalGenome | None = None,
        allow_consolidated: bool = True,
    ) -> tuple[int, EpigeneticProfile]:
        """Load consolidated rules & ``EpigeneticProfile`` on cold-boot."""
        genome = expected_genome or ConstitutionalGenome()
        cur = self._conn.cursor()
        row = cur.execute(
            "SELECT genome_sha256, values_json, generation FROM stage1_epigenome_state WHERE id = 1"
        ).fetchone()
        if row is not None:
            saved_sha, values_json, gen = row
            if saved_sha != genome.genome_sha256():
                raise RuntimeError("Constitutional genome hash mismatch on cold-boot")
            loaded_values = json.loads(str(values_json))
            profile = EpigeneticProfile(
                genome=genome,
                values={str(k): float(v) for k, v in loaded_values.items()},
                generation=int(gen),
            )
        else:
            profile = EpigeneticProfile(genome=genome)

        if not allow_consolidated:
            return 0, profile

        for r_surf, r_act, r_probe, r_tok in cur.execute(
            "SELECT surface_facts_json, blocked_action, probe_name, probe_token "
            "FROM stage1_retracted_signatures"
        ).fetchall():
            learner.retracted_signatures.add(
                (
                    frozenset(str(x) for x in json.loads(str(r_surf))),
                    str(r_act),
                    str(r_probe),
                    str(r_tok),
                )
            )

        rows = cur.execute("""
            SELECT latent_id, surface_facts_json, probe_name, probe_token,
                   blocked_action, clobbered_fluent, remediation_action,
                   discriminative_score, promotion_count, suppression_count, consolidated
            FROM stage1_consolidated_rules
            WHERE consolidated = 1
            ORDER BY latent_id ASC
            """).fetchall()
        count = 0
        for r in rows:
            surface = frozenset(str(x) for x in json.loads(str(r[1])))
            rule = DiscoveredLatentRule(
                latent_id=str(r[0]),
                surface_facts=surface,
                probe_name=str(r[2]),
                probe_token=str(r[3]),
                blocked_action=str(r[4]),
                clobbered_fluent=str(r[5]) if r[5] is not None else None,
                remediation_action=str(r[6]) if r[6] is not None else None,
                discriminative_score=float(r[7]),
                promotion_count=int(r[8]),
                suppression_count=int(r[9]),
                consolidated=bool(r[10]),
            )
            learner.sandbox.upsert(rule)
            # T263 fix: restore the EpigeneticEngine lifecycle state as well, otherwise the
            # first post-boot validation re-creates a fresh state (promotion_count=1) and
            # silently de-consolidates the rule after a single use.
            state = learner.epigenetics.register(rule.latent_id)
            state.promotion_count = rule.promotion_count
            state.suppression_count = rule.suppression_count
            state.consolidated = rule.consolidated
            count += 1
        return count, profile

    def close(self) -> None:
        self.episodic_memory.close()
        self._conn.close()


# ----------------------------------------------------------------------
# Sandboxed Multi-Mechanism Environment Twin (T217 simulate_only)
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class TwinActionOutcome:
    """Result of executing one simulated probe or actuation on ``LatentSandboxTwin``."""

    action_name: str
    is_probe: bool
    succeeded: bool
    surface_facts: frozenset[str]
    clobbered_facts: frozenset[str]
    probe_token: str | None = None


class LatentSandboxTwin:
    """In-memory sandboxed twin with nominal Task A + 2 undeclared latent mechanisms."""

    mcp_actuation_permitted: bool = False

    def __init__(
        self,
        unit_id: str,
        *,
        subsystem: str,
        hidden_variant: str,
        distractor_seed: int = 0,
        shuffle_probes: bool = False,
    ) -> None:
        self.unit_id = unit_id
        self.subsystem = subsystem  # "relay_a" | "bus_h1" | "cryo_h2"
        self.hidden_variant = hidden_variant  # "nominal" | "latent_inverted" | "latent_frosted"
        self._distractor_seed = distractor_seed
        self._shuffle_probes = shuffle_probes

        if subsystem == "relay_a":
            self.surface_facts: frozenset[str] = frozenset({"relay_online", "grid_synced"})
            self.goal_facts: frozenset[str] = frozenset({"load_energized"})
            self._frost_active = False
            self._inverted = False
        elif subsystem == "bus_h1":
            # Identical surface facts regardless of hidden_variant!
            self.surface_facts = frozenset({"panel_online", "bus_ready"})
            self.goal_facts = frozenset({"bus_locked"})
            self._inverted = hidden_variant == "latent_inverted"
            self._frost_active = False
        elif subsystem == "cryo_h2":
            # Identical surface facts regardless of hidden_variant!
            self.surface_facts = frozenset({"manifold_cooled", "seal_seated"})
            self.goal_facts = frozenset({"chamber_pressurized"})
            self._inverted = False
            self._frost_active = hidden_variant == "latent_frosted"
        else:
            raise ValueError(f"unknown subsystem: {subsystem!r}")

    def execute_probe(self, probe_name: str) -> TwinActionOutcome:
        """Execute a non-destructive diagnostic probe."""
        if self._shuffle_probes:
            # Anti-Goodhart permutation control: probe tokens uncorrelated with hidden state
            parity = self._distractor_seed % 2
            fake_map = {
                "probe_phase_angle": "phase_180deg" if parity == 0 else "phase_0deg",
                "probe_acoustic_damping": ("damping_high_frost" if parity == 1 else "damping_low"),
                "probe_ambient_hum": f"hum_{40 + parity}pct",
            }
            tok = fake_map.get(probe_name, "probe_unknown")
            return TwinActionOutcome(
                action_name=probe_name,
                is_probe=True,
                succeeded=True,
                surface_facts=self.surface_facts,
                clobbered_facts=frozenset(),
                probe_token=tok,
            )

        if probe_name == "probe_phase_angle":
            tok = "phase_180deg" if self._inverted else "phase_0deg"
        elif probe_name == "probe_acoustic_damping":
            tok = "damping_high_frost" if self._frost_active else "damping_low"
        elif probe_name == "probe_ambient_hum":
            tok = f"hum_{40 + (self._distractor_seed % 2)}pct"
        else:
            raise ValueError(f"unknown probe: {probe_name!r}")

        return TwinActionOutcome(
            action_name=probe_name,
            is_probe=True,
            succeeded=True,
            surface_facts=self.surface_facts,
            clobbered_facts=frozenset(),
            probe_token=tok,
        )

    def execute_actuation(self, action_name: str) -> TwinActionOutcome:
        """Execute a simulated actuation against hidden twin physics."""
        prior = self.surface_facts
        if action_name == "close_breaker":
            if {"relay_online", "grid_synced"}.issubset(prior):
                self.surface_facts = prior | {"load_energized"}
                return TwinActionOutcome(action_name, False, True, self.surface_facts, frozenset())
            return TwinActionOutcome(action_name, False, False, prior, frozenset())

        if action_name == "engage_primary_bus":
            if not {"panel_online", "bus_ready"}.issubset(prior):
                return TwinActionOutcome(action_name, False, False, prior, frozenset())
            if self._inverted:
                # Hidden polarity inversion blocks primary bus lock!
                return TwinActionOutcome(action_name, False, False, prior, frozenset())
            self.surface_facts = prior | {"bus_locked"}
            return TwinActionOutcome(action_name, False, True, self.surface_facts, frozenset())

        if action_name == "engage_inverted_bypass":
            if not {"panel_online", "bus_ready"}.issubset(prior):
                return TwinActionOutcome(action_name, False, False, prior, frozenset())
            if not self._inverted:
                return TwinActionOutcome(action_name, False, False, prior, frozenset())
            self.surface_facts = prior | {"bus_locked"}
            return TwinActionOutcome(action_name, False, True, self.surface_facts, frozenset())

        if action_name == "pressurize_chamber":
            if not {"manifold_cooled", "seal_seated"}.issubset(prior):
                return TwinActionOutcome(action_name, False, False, prior, frozenset())
            if self._frost_active:
                # Hidden micro-frost fails AND clobbers seal_seated!
                self.surface_facts = prior - {"seal_seated"}
                return TwinActionOutcome(
                    action_name,
                    False,
                    False,
                    self.surface_facts,
                    frozenset({"seal_seated"}),
                )
            self.surface_facts = prior | {"chamber_pressurized"}
            return TwinActionOutcome(action_name, False, True, self.surface_facts, frozenset())

        if action_name == "thermal_purge_seal":
            if "manifold_cooled" not in prior:
                return TwinActionOutcome(action_name, False, False, prior, frozenset())
            self._frost_active = False
            self.surface_facts = prior | {"seal_seated"}
            return TwinActionOutcome(action_name, False, True, self.surface_facts, frozenset())

        raise ValueError(f"unknown actuation: {action_name!r}")


def build_stage1_base_ontology() -> tuple[SymbolRegistry, tuple[GOAPAction, ...], tuple[str, ...]]:
    """Construct base closed-world ontology with ``mutex_pairs=()`` and zero latent symbols."""
    actions = (
        GOAPAction(
            name="close_breaker",
            preconditions=frozenset({"relay_online", "grid_synced"}),
            add_effects=frozenset({"load_energized"}),
            cost=1.0,
        ),
        GOAPAction(
            name="engage_primary_bus",
            preconditions=frozenset({"panel_online", "bus_ready"}),
            add_effects=frozenset({"bus_locked"}),
            cost=1.0,
        ),
        GOAPAction(
            name="engage_inverted_bypass",
            preconditions=frozenset({"panel_online", "bus_ready"}),
            add_effects=frozenset({"bus_locked"}),
            cost=1.8,
        ),
        GOAPAction(
            name="pressurize_chamber",
            preconditions=frozenset({"manifold_cooled", "seal_seated"}),
            add_effects=frozenset({"chamber_pressurized"}),
            cost=1.0,
        ),
        GOAPAction(
            name="thermal_purge_seal",
            preconditions=frozenset({"manifold_cooled"}),
            add_effects=frozenset({"seal_seated"}),
            cost=1.2,
        ),
    )
    predicates = (
        "relay_online",
        "grid_synced",
        "load_energized",
        "panel_online",
        "bus_ready",
        "bus_locked",
        "manifold_cooled",
        "seal_seated",
        "chamber_pressurized",
    )
    probes = ("probe_phase_angle", "probe_acoustic_damping", "probe_ambient_hum")
    registry = SymbolRegistry(
        predicates=predicates,
        causal_nodes=(*predicates, *probes),
        actions=actions,
        mutex_pairs=(),  # Strictly empty: all mutex/latent exclusions must be discovered!
    )
    return registry, actions, probes


# ----------------------------------------------------------------------
# Concurrent Asynchronous Specialists for Stage-1 Global Workspace
# ----------------------------------------------------------------------


class SensoryDiscrepancySpecialist:
    """Assimilates surface observations and spikes on unexpected action/fluent discrepancy."""

    name = "sensory_discrepancy"

    async def propose(self, board: WorkspaceBlackboard) -> CoalitionProposal:
        await asyncio.sleep(0)
        needs_sync = (not board.active_beliefs) or (board.surprise >= 0.45)
        if needs_sync:
            return CoalitionProposal(
                specialist_name=self.name,
                intent="assimilate_surface_and_discrepancy",
                salience_channels=(0.96, 0.58, 0.24),
                confidence=0.98,
                payload={"surprise": board.surprise},
            )
        return CoalitionProposal(
            specialist_name=self.name,
            intent="sensory_idle_monitor",
            salience_channels=(0.11, 0.05, 0.02),
            confidence=0.60,
        )


class EpisodicConsolidationSpecialist:
    """Applies consolidated SQLite/epigenetic rules via targeted single-probe recall."""

    name = "episodic_consolidation"

    def __init__(
        self,
        learner: LatentDistinctionLearner,
        *,
        require_consolidated: bool = False,
    ) -> None:
        self._learner = learner
        self._require_consolidated = require_consolidated

    async def propose(self, board: WorkspaceBlackboard) -> CoalitionProposal:
        await asyncio.sleep(0)
        rules = self._learner.sandbox.rules_for_surface(
            board.episode_surface or board.surface_facts,
            require_consolidated=self._require_consolidated,
        )
        for rule in rules:
            if rule.probe_name not in board.probe_readings:
                return CoalitionProposal(
                    specialist_name=self.name,
                    intent="targeted_rule_probe",
                    salience_channels=(0.94, 0.54, 0.19),
                    confidence=min(1.0, rule.discriminative_score),
                    payload={"probe_name": rule.probe_name, "latent_id": rule.latent_id},
                )
        return CoalitionProposal(
            specialist_name=self.name,
            intent="consolidation_standby",
            salience_channels=(0.09, 0.04, 0.02),
            confidence=0.55,
        )


class EpistemicProbeSpecialist:
    """Executes exploratory diagnostic probes when surface states exhibit ambiguity."""

    name = "epistemic_probe"

    def __init__(
        self,
        learner: LatentDistinctionLearner,
        probes: Sequence[str],
        *,
        require_consolidated: bool = False,
    ) -> None:
        self._learner = learner
        self._probes = tuple(probes)
        self._require_consolidated = require_consolidated

    async def propose(self, board: WorkspaceBlackboard) -> CoalitionProposal:
        await asyncio.sleep(0)
        if not self._learner.enable_discovery:
            return CoalitionProposal(
                specialist_name=self.name,
                intent="probe_disabled",
                salience_channels=(0.08, 0.03, 0.01),
                confidence=0.40,
            )

        # Skip broad exploration if an applicable rule already exists for this surface
        known_rules = self._learner.sandbox.rules_for_surface(
            board.episode_surface or board.surface_facts,
            require_consolidated=self._require_consolidated,
        )
        is_ambiguous = (
            board.episode_surface or board.surface_facts
        ) in self._learner.ambiguous_surfaces or bool(board.failed_actions_in_state)
        if is_ambiguous and not known_rules:
            remaining = [p for p in self._probes if p not in board.probe_readings]
            if remaining:
                return CoalitionProposal(
                    specialist_name=self.name,
                    intent="exploratory_diagnostic_probe",
                    salience_channels=(0.90, 0.49, 0.28),
                    confidence=0.88,
                    payload={"probe_name": remaining[0]},
                )
        return CoalitionProposal(
            specialist_name=self.name,
            intent="probe_standby",
            salience_channels=(0.10, 0.05, 0.03),
            confidence=0.50,
        )


class CausalPlannerSpecialist:
    """Plans over active beliefs while respecting dynamically discovered blocks/mutexes."""

    name = "causal_planner"

    def __init__(
        self,
        actions: Sequence[GOAPAction],
        *,
        learner: LatentDistinctionLearner | None = None,
        probes: Sequence[str] = (),
        require_consolidated: bool = False,
    ) -> None:
        self._actions = tuple(actions)
        self._learner = learner
        self._probes = tuple(probes)
        self._require_consolidated = require_consolidated

    def _unresolved_uncertainty(self, board: WorkspaceBlackboard) -> bool:
        """True when the surface is ambiguous, no rule explains it and probes remain."""
        if self._learner is None or not self._learner.enable_discovery:
            return False
        ambiguous = (
            board.episode_surface or board.surface_facts
        ) in self._learner.ambiguous_surfaces or bool(board.failed_actions_in_state)
        if not ambiguous:
            return False
        if self._learner.sandbox.rules_for_surface(
            board.episode_surface or board.surface_facts,
            require_consolidated=self._require_consolidated,
        ):
            return False
        return any(p not in board.probe_readings for p in self._probes)

    async def propose(self, board: WorkspaceBlackboard) -> CoalitionProposal:
        await asyncio.sleep(0)
        if not board.active_beliefs or board.goal_facts.issubset(board.active_beliefs):
            return CoalitionProposal(
                specialist_name=self.name,
                intent="planner_idle",
                salience_channels=(0.07, 0.03, 0.01),
                confidence=0.50,
            )

        allowed = [a for a in self._actions if a.name not in board.failed_actions_in_state]
        if not allowed:
            return CoalitionProposal(
                specialist_name=self.name,
                intent="planner_exhausted",
                salience_channels=(0.15, 0.06, 0.04),
                confidence=0.20,
            )

        planner = GOAPPlanner(allowed, simulate_only=True, max_expansions=64)
        plan, expansions = planner.plan_with_stats(board.active_beliefs, board.goal_facts)
        if plan:
            # Information gating: acting under unresolved ambiguity is down-weighted
            # so that cheap non-destructive probes can win the workspace first.
            act_sal = 0.35 if self._unresolved_uncertainty(board) else 0.80
            return CoalitionProposal(
                specialist_name=self.name,
                intent="execute_planned_step",
                salience_channels=(act_sal, 0.44, 0.15),
                confidence=0.92,
                payload={
                    "action_name": plan[0].name,
                    "plan_len": len(plan),
                    "expansions": expansions,
                },
            )
        return CoalitionProposal(
            specialist_name=self.name,
            intent="planner_no_path",
            salience_channels=(0.14, 0.06, 0.03),
            confidence=0.30,
        )


# ----------------------------------------------------------------------
# Unified Stage-1 Prototype Runner
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class EpisodeRunMetrics:
    """Telemetry and behavioral outcome for one sandbox episode."""

    unit_id: str
    subsystem: str
    hidden_variant: str
    goal_reached: bool
    ticks_used: int
    failed_actuations: int
    probes_executed: tuple[str, ...]
    actuations_executed: tuple[str, ...]
    activated_latent_ids: tuple[str, ...]
    newly_minted_latent_id: str | None


class Stage1CognitivePrototype:
    """CPU-only asynchronous cognitive prototype with discovery & cold-boot SQLite."""

    def __init__(
        self,
        *,
        db_path: str | Path | None = None,
        cold_boot_require_consolidated: bool = False,
        allow_consolidated_load: bool = True,
        enable_discovery: bool = True,
        max_rss_mb: float = 250.0,
    ) -> None:
        self.registry, self.actions, self.probes = build_stage1_base_ontology()
        self.genome = ConstitutionalGenome()
        self.learner = LatentDistinctionLearner(enable_discovery=enable_discovery)
        self.store: Stage1PersistenceStore | None = (
            Stage1PersistenceStore(db_path) if db_path is not None else None
        )
        self.loaded_consolidated_count = 0
        if self.store is not None:
            self.loaded_consolidated_count, self.epigenetic_profile = (
                self.store.load_consolidated_into(
                    self.learner,
                    expected_genome=self.genome,
                    allow_consolidated=allow_consolidated_load,
                )
            )
        else:
            self.epigenetic_profile = EpigeneticProfile(genome=self.genome)

        self.runtime_controls = resolve_runtime_controls(self.epigenetic_profile)
        self._require_consolidated = cold_boot_require_consolidated
        specialists = (
            SensoryDiscrepancySpecialist(),
            EpisodicConsolidationSpecialist(
                self.learner, require_consolidated=cold_boot_require_consolidated
            ),
            EpistemicProbeSpecialist(
                self.learner,
                self.probes,
                require_consolidated=cold_boot_require_consolidated,
            ),
            CausalPlannerSpecialist(
                self.actions,
                learner=self.learner,
                probes=self.probes,
                require_consolidated=cold_boot_require_consolidated,
            ),
        )
        self.workspace = AsyncGlobalWorkspace(specialists, max_rss_mb=max_rss_mb)

    async def run_episode(
        self, twin: LatentSandboxTwin, *, max_ticks: int = 20
    ) -> EpisodeRunMetrics:
        """Run asynchronous Global Workspace loop on ``twin`` until goal or ``max_ticks``."""
        initial_surface = twin.surface_facts
        board = WorkspaceBlackboard(
            tick=0,
            surface_facts=twin.surface_facts,
            episode_surface=twin.surface_facts,
            active_beliefs=frozenset(),
            goal_facts=twin.goal_facts,
        )
        start_ticks = len(self.workspace.history)
        failed_actuations = 0
        probes_run: list[str] = []
        actuations_run: list[str] = []
        activated_latents: list[str] = []
        cleared_latents: set[str] = set()
        first_primary_attempt: str | None = None
        first_primary_succeeded: bool | None = None
        first_clobbered: frozenset[str] = frozenset()
        recovery_used: str | None = None

        for _ in range(max_ticks):
            if twin.goal_facts.issubset(twin.surface_facts):
                board.goal_achieved = True
                break

            winner, _tel = await self.workspace.step(board)
            intent = winner.intent

            if intent == "assimilate_surface_and_discrepancy":
                beliefs = set(twin.surface_facts)
                # Apply any active discovered latent blocks / dynamic mutex retractions
                for rule in self.learner.sandbox.rules_for_surface(
                    initial_surface, require_consolidated=self._require_consolidated
                ):
                    if (
                        rule.latent_id not in cleared_latents
                        and board.probe_readings.get(rule.probe_name) == rule.probe_token
                    ):
                        if rule.latent_id not in activated_latents:
                            activated_latents.append(rule.latent_id)
                        if rule.clobbered_fluent and rule.clobbered_fluent in beliefs:
                            beliefs.discard(rule.clobbered_fluent)
                        else:
                            board.failed_actions_in_state.add(rule.blocked_action)
                board.surface_facts = twin.surface_facts
                board.active_beliefs = frozenset(beliefs)
                board.surprise = 0.0

            elif intent in ("targeted_rule_probe", "exploratory_diagnostic_probe"):
                p_name = str(winner.payload["probe_name"])
                out = twin.execute_probe(p_name)
                probes_run.append(p_name)
                if out.probe_token is not None:
                    board.probe_readings[p_name] = out.probe_token
                # Immediately project any matched latent rule onto active beliefs
                beliefs = set(board.active_beliefs or twin.surface_facts)
                for rule in self.learner.sandbox.rules_for_surface(
                    initial_surface, require_consolidated=self._require_consolidated
                ):
                    if (
                        rule.latent_id not in cleared_latents
                        and board.probe_readings.get(rule.probe_name) == rule.probe_token
                    ):
                        if rule.latent_id not in activated_latents:
                            activated_latents.append(rule.latent_id)
                        if rule.clobbered_fluent and rule.clobbered_fluent in beliefs:
                            beliefs.discard(rule.clobbered_fluent)
                        else:
                            board.failed_actions_in_state.add(rule.blocked_action)
                board.active_beliefs = frozenset(beliefs)

            elif intent == "execute_planned_step":
                act_name = str(winner.payload["action_name"])
                out = twin.execute_actuation(act_name)
                actuations_run.append(act_name)
                if first_primary_attempt is None and not activated_latents:
                    first_primary_attempt = act_name
                    first_primary_succeeded = out.succeeded
                    first_clobbered = out.clobbered_facts

                if not out.succeeded:
                    failed_actuations += 1
                    if out.clobbered_facts:
                        # State changed (fluent clobbered): the action may become viable
                        # again after repair, so expose the new state to the planner.
                        board.active_beliefs = out.surface_facts
                    else:
                        board.failed_actions_in_state.add(act_name)
                    board.clobbered_facts_last_step = out.clobbered_facts
                    board.surface_facts = out.surface_facts
                    board.surprise = 1.0
                    self.learner.flag_discrepancy(initial_surface)
                else:
                    if first_primary_succeeded is False and recovery_used is None:
                        recovery_used = act_name
                    # Check if a remediation action cleared an active clobbering latent state
                    for rule in self.learner.sandbox.rules_for_surface(
                        initial_surface, require_consolidated=self._require_consolidated
                    ):
                        if rule.remediation_action == act_name:
                            cleared_latents.add(rule.latent_id)
                    board.surface_facts = out.surface_facts
                    board.active_beliefs = out.surface_facts
                    board.surprise = 0.0

        goal_ok = twin.goal_facts.issubset(twin.surface_facts)
        ticks_used = len(self.workspace.history) - start_ticks

        # Validate any activated candidate/consolidated rules via EpigeneticEngine
        for lid in activated_latents:
            self.learner.record_rule_validation(lid, verified=(goal_ok and failed_actuations == 0))

        minted_id: str | None = None
        if first_primary_attempt is not None and first_primary_succeeded is not None:
            minted = self.learner.record_episode_sample(
                EpisodeTransitionSample(
                    surface_facts=initial_surface,
                    probe_readings=dict(board.probe_readings),
                    attempted_action=first_primary_attempt,
                    succeeded=first_primary_succeeded,
                    clobbered_fluents=first_clobbered,
                    recovery_action=recovery_used,
                )
            )
            if minted is not None:
                minted_id = minted.latent_id

        return EpisodeRunMetrics(
            unit_id=twin.unit_id,
            subsystem=twin.subsystem,
            hidden_variant=twin.hidden_variant,
            goal_reached=goal_ok,
            ticks_used=ticks_used,
            failed_actuations=failed_actuations,
            probes_executed=tuple(probes_run),
            actuations_executed=tuple(actuations_run),
            activated_latent_ids=tuple(activated_latents),
            newly_minted_latent_id=minted_id,
        )

    async def persist_and_close(self, *, freeze_epigenome: bool = False) -> int:
        """Save consolidated rules & epigenetic profile to SQLite and close handles."""
        if self.store is None:
            return 0
        saved = await self.store.save_state(
            self.learner, self.epigenetic_profile, freeze_epigenome=freeze_epigenome
        )
        self.store.close()
        return saved


# ----------------------------------------------------------------------
# Subprocess Cold-Boot Campaign Orchestration (T261–T262)
# ----------------------------------------------------------------------


def _training_curriculum(*, shuffle_probes: bool = False) -> list[LatentSandboxTwin]:
    return [
        # Baseline nominal Task A (retention anchor)
        LatentSandboxTwin("relay_nom_0", subsystem="relay_a", hidden_variant="nominal"),
        # Hidden Mechanism 1: Indistinguishable bus polarity inversion (discovery + 3 validations)
        LatentSandboxTwin(
            "bus_inv_1",
            subsystem="bus_h1",
            hidden_variant="latent_inverted",
            distractor_seed=0,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "bus_nom_1",
            subsystem="bus_h1",
            hidden_variant="nominal",
            distractor_seed=0,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "bus_inv_2",
            subsystem="bus_h1",
            hidden_variant="latent_inverted",
            distractor_seed=1,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "bus_inv_3",
            subsystem="bus_h1",
            hidden_variant="latent_inverted",
            distractor_seed=2,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "bus_inv_4",
            subsystem="bus_h1",
            hidden_variant="latent_inverted",
            distractor_seed=3,
            shuffle_probes=shuffle_probes,
        ),
        # Hidden Mechanism 2: Cryo seal micro-frost clobbering (discovery + 3 validations)
        LatentSandboxTwin(
            "cryo_frost_1",
            subsystem="cryo_h2",
            hidden_variant="latent_frosted",
            distractor_seed=0,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "cryo_clean_1",
            subsystem="cryo_h2",
            hidden_variant="nominal",
            distractor_seed=0,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "cryo_frost_2",
            subsystem="cryo_h2",
            hidden_variant="latent_frosted",
            distractor_seed=1,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "cryo_frost_3",
            subsystem="cryo_h2",
            hidden_variant="latent_frosted",
            distractor_seed=2,
            shuffle_probes=shuffle_probes,
        ),
        LatentSandboxTwin(
            "cryo_frost_4",
            subsystem="cryo_h2",
            hidden_variant="latent_frosted",
            distractor_seed=3,
            shuffle_probes=shuffle_probes,
        ),
    ]


def _heldout_cold_boot_variants() -> list[LatentSandboxTwin]:
    return [
        LatentSandboxTwin("relay_nom_heldout", subsystem="relay_a", hidden_variant="nominal"),
        LatentSandboxTwin(
            "bus_omega_heldout",
            subsystem="bus_h1",
            hidden_variant="latent_inverted",
            distractor_seed=9,
        ),
        LatentSandboxTwin(
            "cryo_omega_heldout",
            subsystem="cryo_h2",
            hidden_variant="latent_frosted",
            distractor_seed=9,
        ),
    ]


def run_phase1_discovery_process(
    db_path: Path,
    *,
    freeze_epigenome: bool = False,
    shuffle_probes: bool = False,
    max_rss_mb: float = 250.0,
) -> dict[str, Any]:
    """Execute Phase-1 discovery & consolidation inside the current process."""

    async def _run() -> dict[str, Any]:
        proto = Stage1CognitivePrototype(
            db_path=db_path,
            cold_boot_require_consolidated=False,
            allow_consolidated_load=False,
            enable_discovery=True,
            max_rss_mb=max_rss_mb,
        )
        episodes: list[EpisodeRunMetrics] = []
        for twin in _training_curriculum(shuffle_probes=shuffle_probes):
            episodes.append(await proto.run_episode(twin))

        ws_summary: WorkspaceTelemetrySummary = proto.workspace.summarize_telemetry()
        rules_snapshot = [r.to_dict() for r in proto.learner.sandbox.rules.values()]
        saved_count = await proto.persist_and_close(freeze_epigenome=freeze_epigenome)

        # Pre-consolidation naive ticks on the two first latent encounters (bus_inv_1 + cryo_frost_1)
        naive_pair = [e for e in episodes if e.unit_id in ("bus_inv_1", "cryo_frost_1")]
        pre_consolidation_latent_ticks = sum(e.ticks_used for e in naive_pair)
        pre_consolidation_failed_actuations = sum(e.failed_actuations for e in naive_pair)

        return {
            "phase": "phase1_discovery_and_consolidation",
            "consolidated_rules_saved": saved_count,
            "discovered_rules": rules_snapshot,
            "pre_consolidation_latent_ticks": pre_consolidation_latent_ticks,
            "pre_consolidation_failed_actuations": pre_consolidation_failed_actuations,
            "workspace_telemetry": ws_summary.to_dict(),
            "episodes": [asdict(e) for e in episodes],
            "final_rss_mb": round(read_process_rss_mb(), 3),
        }

    return asyncio.run(_run())


def run_phase2_cold_boot_process(
    db_path: Path | None,
    *,
    allow_consolidated_load: bool = True,
    enable_discovery: bool = True,
    max_rss_mb: float = 250.0,
) -> dict[str, Any]:
    """Execute Phase-2 cold-boot evaluation on unseen variants in a fresh process."""

    async def _run() -> dict[str, Any]:
        proto = Stage1CognitivePrototype(
            db_path=db_path,
            cold_boot_require_consolidated=True,
            allow_consolidated_load=allow_consolidated_load,
            enable_discovery=enable_discovery,
            max_rss_mb=max_rss_mb,
        )
        episodes: list[EpisodeRunMetrics] = []
        for twin in _heldout_cold_boot_variants():
            episodes.append(await proto.run_episode(twin))

        ws_summary = proto.workspace.summarize_telemetry()
        epigenetic_gen = proto.epigenetic_profile.generation
        epigenetic_vals = dict(proto.epigenetic_profile.values)
        runtime_ctrl = proto.runtime_controls.to_dict()
        if proto.store is not None:
            proto.store.close()

        latent_heldout = [
            e for e in episodes if e.unit_id in ("bus_omega_heldout", "cryo_omega_heldout")
        ]
        task_a_ep = next(e for e in episodes if e.unit_id == "relay_nom_heldout")
        post_consolidation_latent_ticks = sum(e.ticks_used for e in latent_heldout)
        post_consolidation_failed_actuations = sum(e.failed_actuations for e in latent_heldout)

        return {
            "phase": "phase2_cold_boot_evaluation",
            "loaded_consolidated_rules": proto.loaded_consolidated_count,
            "epigenetic_generation": epigenetic_gen,
            "epigenetic_values": epigenetic_vals,
            "runtime_controls": runtime_ctrl,
            "task_a_retained": task_a_ep.goal_reached and task_a_ep.failed_actuations == 0,
            "all_heldout_goals_reached": all(e.goal_reached for e in episodes),
            "post_consolidation_latent_ticks": post_consolidation_latent_ticks,
            "post_consolidation_failed_actuations": post_consolidation_failed_actuations,
            "workspace_telemetry": ws_summary.to_dict(),
            "episodes": [asdict(e) for e in episodes],
            "final_rss_mb": round(read_process_rss_mb(), 3),
        }

    return asyncio.run(_run())


def run_stage1_subprocess_campaign(work_dir: Path, *, max_rss_mb: float = 250.0) -> dict[str, Any]:
    """Run sequential single-process cold-boot campaign across OS process boundaries.

    Strictly spawns **at most 1 child Python process at a time** (waiting for
    completion before starting the next) to respect the Stage-1 notebook RAM budget.
    """
    work_dir.mkdir(parents=True, exist_ok=True)
    db_main = work_dir / "stage1_consolidated.db"
    db_frozen = work_dir / "stage1_frozen_epigenome.db"
    for p in (db_main, db_frozen):
        if p.exists():
            p.unlink()

    def _invoke_cli(args: list[str]) -> dict[str, Any]:
        proc = subprocess.run(
            [sys.executable, "-m", "q_speace.bridge.latent_discovery", *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        out: dict[str, Any] = json.loads(proc.stdout)
        return out

    # 1. Process 1: Discovery & consolidation into SQLite -> process terminates!
    p1_main = _invoke_cli(
        ["--mode", "phase1", "--db-path", str(db_main), "--max-rss-mb", str(max_rss_mb)]
    )
    # 2. Process 2: Cold-boot fresh Python interpreter loading SQLite on unseen variants!
    p2_cold_boot = _invoke_cli(
        ["--mode", "phase2", "--db-path", str(db_main), "--max-rss-mb", str(max_rss_mb)]
    )
    # 3. Ablation A: Amnesic cold-boot (no SQLite DB) on identical unseen variants
    p2_amnesic = _invoke_cli(["--mode", "phase2-amnesic", "--max-rss-mb", str(max_rss_mb)])
    # 4. Ablation B: Frozen-epigenome cold-boot (Phase 1 runs with freeze_epigenome=True)
    _invoke_cli(
        [
            "--mode",
            "phase1",
            "--db-path",
            str(db_frozen),
            "--freeze-epigenome",
            "--max-rss-mb",
            str(max_rss_mb),
        ]
    )
    p2_frozen = _invoke_cli(
        ["--mode", "phase2", "--db-path", str(db_frozen), "--max-rss-mb", str(max_rss_mb)]
    )
    # 5. Ablation C: Shuffled-probe negative control (verifies causal probe reliance)
    p1_shuffled = run_phase1_discovery_process(
        work_dir / "stage1_shuffled.db", shuffle_probes=True, max_rss_mb=max_rss_mb
    )

    pre_ticks = int(p1_main["pre_consolidation_latent_ticks"])
    post_ticks = int(p2_cold_boot["post_consolidation_latent_ticks"])
    tick_reduction_ratio = round(1.0 - (post_ticks / max(pre_ticks, 1)), 4)

    ws_p1 = p1_main["workspace_telemetry"]
    ws_p2 = p2_cold_boot["workspace_telemetry"]
    peak_rss_all = max(
        float(ws_p1["peak_rss_mb"]),
        float(ws_p2["peak_rss_mb"]),
        float(p2_amnesic["workspace_telemetry"]["peak_rss_mb"]),
        float(p2_frozen["workspace_telemetry"]["peak_rss_mb"]),
        read_process_rss_mb(),
    )

    gates = {
        "gate1_workspace_criticality_and_nontrivial": bool(
            ws_p1["within_critical_band"] and ws_p1["non_trivial_dynamics"]
        ),
        "gate2_two_undeclared_latents_discovered": bool(
            p1_main["consolidated_rules_saved"] >= 2
            and p1_shuffled["consolidated_rules_saved"] == 0
        ),
        "gate3_cold_boot_tick_reduction_and_zero_failures": bool(
            p2_cold_boot["all_heldout_goals_reached"]
            and p2_cold_boot["task_a_retained"]
            and p2_cold_boot["post_consolidation_failed_actuations"] == 0
            and tick_reduction_ratio >= 0.35
            and post_ticks < int(p2_amnesic["post_consolidation_latent_ticks"])
            and post_ticks < int(p2_frozen["post_consolidation_latent_ticks"])
        ),
        "gate4_rss_under_250mb": bool(peak_rss_all < max_rss_mb),
    }

    return {
        "spec": "T261_T262_STAGE1_PROTOTYPE",
        "cpu_only": True,
        "mcp_actuation_permitted": False,
        "max_concurrent_processes": 1,
        "max_rss_budget_mb": max_rss_mb,
        "peak_rss_across_processes_mb": round(peak_rss_all, 3),
        "ticks_pre_consolidation": pre_ticks,
        "ticks_post_cold_boot": post_ticks,
        "tick_reduction_ratio": tick_reduction_ratio,
        "amnesic_cold_boot_ticks": int(p2_amnesic["post_consolidation_latent_ticks"]),
        "amnesic_failed_actuations": int(p2_amnesic["post_consolidation_failed_actuations"]),
        "frozen_epigenome_cold_boot_ticks": int(p2_frozen["post_consolidation_latent_ticks"]),
        "frozen_epigenome_failed_actuations": int(
            p2_frozen["post_consolidation_failed_actuations"]
        ),
        "shuffled_probe_consolidated_rules": int(p1_shuffled["consolidated_rules_saved"]),
        "phase1_summary": {
            "consolidated_rules_saved": p1_main["consolidated_rules_saved"],
            "discovered_rules": p1_main["discovered_rules"],
            "workspace_telemetry": ws_p1,
        },
        "phase2_cold_boot_summary": p2_cold_boot,
        "gates": gates,
        "all_gates_passed": all(gates.values()),
    }


def _cli_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stage-1 T261-T262 subprocess runner")
    parser.add_argument(
        "--mode",
        choices=("phase1", "phase2", "phase2-amnesic"),
        required=True,
    )
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument("--freeze-epigenome", action="store_true")
    parser.add_argument("--max-rss-mb", type=float, default=250.0)
    ns = parser.parse_args(argv)

    if ns.mode == "phase1":
        if ns.db_path is None:
            raise ValueError("--db-path is required for --mode phase1")
        res = run_phase1_discovery_process(
            ns.db_path,
            freeze_epigenome=ns.freeze_epigenome,
            max_rss_mb=ns.max_rss_mb,
        )
    elif ns.mode == "phase2":
        if ns.db_path is None:
            raise ValueError("--db-path is required for --mode phase2")
        res = run_phase2_cold_boot_process(
            ns.db_path, allow_consolidated_load=True, max_rss_mb=ns.max_rss_mb
        )
    else:
        res = run_phase2_cold_boot_process(
            None, allow_consolidated_load=False, max_rss_mb=ns.max_rss_mb
        )

    sys.stdout.write(json.dumps(res, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
