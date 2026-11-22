"""T234 v1.1: EvolutionaryGenomeCodec (seed + cortex bridge), HiddenCausalEvaluator, EpigeneticRegulator & Runtime Controls."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import random
import secrets
import time
from collections.abc import Sequence
from dataclasses import asdict

import numpy as np

from q_speace.edd_cvt.cosmic_virus import CosmicVirusOptimizer, CVConfig
from q_speace.seed.constitution import SeedGenome
from q_speace.self_improvement_cortex.epigenetics import EpigeneticMarker, EpigeneticTag

from .schema import (
    DEFAULT_LOCI,
    GENOME_PROTECTED_FIELDS,
    LOCUS_REGISTRY,
    CausalFeedback,
    ConstitutionalGenome,
    EpigeneticAuditEntry,
    EpigeneticProfile,
    EpigeneticProposal,
    EpigeneticStepResult,
    RuntimeControlVector,
)


def resolve_runtime_controls(profile: EpigeneticProfile) -> RuntimeControlVector:
    """Translate epigenetic loci into concrete local-host SPEACE orchestration controls.

    Strictly advisory and host-local under human supervision (``mcp_actuation_permitted=False``).
    """
    v = profile.values
    # verification_depth [0.30, 1.00] -> max_review_cycles [1, 5]
    rev_norm = (v["verification_depth"] - 0.30) / 0.70
    max_review_cycles = max(1, min(5, round(1 + 4 * rev_norm)))

    # delegation_granularity [0.10, 0.90] -> higher granularity => tighter fanout [8 .. 2]
    del_norm = (v["delegation_granularity"] - 0.10) / 0.80
    max_agent_fanout = max(2, min(8, round(8 - 6 * del_norm)))

    # energy_throttling [0.20, 0.95] -> higher throttling => lower CPU/GPU quota and token budget
    thr_norm = (v["energy_throttling"] - 0.20) / 0.75
    cpu_quota = round(max(0.15, min(0.95, 0.95 - 0.75 * thr_norm)), 4)
    gpu_quota = round(max(0.10, min(0.90, 0.90 - 0.75 * thr_norm)), 4)
    token_budget = max(512, min(16384, int(round(16384 - 14336 * thr_norm))))

    # consensus_quorum [0.51, 0.95] -> required_independent_verifiers [2, 5]
    q_norm = (v["consensus_quorum"] - 0.51) / 0.44
    required_verifiers = max(2, min(5, round(2 + 3 * q_norm)))

    # exploration_rate [0.02, 0.50] -> sampling_temperature_cap [0.05, 0.80]
    exp_norm = (v["exploration_rate"] - 0.02) / 0.48
    temp_cap = round(max(0.05, min(0.80, 0.05 + 0.75 * exp_norm)), 4)

    # memory_retention [0.30, 0.98] -> causal_memory_ttl_multiplier [0.5, 3.0]
    mem_norm = (v["memory_retention"] - 0.30) / 0.68
    ttl_mult = round(max(0.5, min(3.0, 0.5 + 2.5 * mem_norm)), 4)

    return RuntimeControlVector(
        max_review_cycles=max_review_cycles,
        max_agent_fanout=max_agent_fanout,
        cpu_quota=cpu_quota,
        gpu_quota=gpu_quota,
        token_budget=token_budget,
        required_independent_verifiers=required_verifiers,
        sampling_temperature_cap=temp_cap,
        causal_memory_ttl_multiplier=ttl_mult,
        advisory_only=True,
        local_host_execution_only=True,
        mcp_actuation_permitted=False,
    )


class HiddenCausalEvaluator:
    """Anti-Goodhart rotated hidden causal evaluator with monotonic epoch tracking.

    Samples a rotating subset of hidden causal benchmarks using an internal
    secret salt never disclosed in outputs. Returns only aggregate metrics,
    epoch number, and an opaque HMAC commitment (``causal_eval_digest``).
    """

    def __init__(self, *, internal_salt: bytes | None = None) -> None:
        self._salt = bytes(internal_salt) if internal_salt is not None else secrets.token_bytes(32)
        self._epoch = 0

    @property
    def current_epoch(self) -> int:
        return self._epoch

    def evaluate_hidden_set(
        self,
        baseline_outputs: Sequence[str],
        candidate_outputs: Sequence[str],
        *,
        sample_size: int | None = None,
    ) -> tuple[float, float, float, str, int]:
        """Return ``(semantic_drift, causal_grounding_error, delta, opaque_digest, epoch)``."""
        if not baseline_outputs or len(baseline_outputs) != len(candidate_outputs):
            raise ValueError("baseline_outputs and candidate_outputs must be equal non-empty lists")
        self._epoch += 1
        n = len(baseline_outputs)
        k = n if sample_size is None else max(1, min(sample_size, n))
        seed_bytes = hmac.new(
            self._salt, f"epoch:{self._epoch}:{n}".encode(), hashlib.sha256
        ).digest()
        rng = random.Random(int.from_bytes(seed_bytes[:8], "big"))
        indices = rng.sample(range(n), k=k)
        mismatches = sum(1 for i in indices if baseline_outputs[i] != candidate_outputs[i])
        causal_error = mismatches / k
        # Internal semantic drift measures structural diversity loss vs baseline set.
        base_unique = len({baseline_outputs[i] for i in indices})
        cand_unique = len({candidate_outputs[i] for i in indices})
        sem_drift = max(0.0, (base_unique - cand_unique) / max(base_unique, 1))
        delta = 0.02 if mismatches == 0 else -causal_error
        digest = hmac.new(
            self._salt,
            (
                f"v1.1|epoch={self._epoch}|k={k}|sem={sem_drift:.6f}|"
                f"ecausal={causal_error:.6f}|delta={delta:.6f}"
            ).encode(),
            hashlib.sha256,
        ).hexdigest()
        return sem_drift, causal_error, delta, digest, self._epoch

    def commit_feedback(self, feedback: CausalFeedback) -> tuple[str, int]:
        """Return ``(causal_eval_digest, validation_seed_epoch)``."""
        epoch = (
            feedback.validation_seed_epoch
            if feedback.validation_seed_epoch > 0
            else self._epoch + 1
        )
        if epoch > self._epoch:
            self._epoch = epoch
        if feedback.causal_eval_digest:
            return feedback.causal_eval_digest, epoch
        msg = (
            f"v1.1|epoch={epoch}|sem={feedback.semantic_entropy_drift:.6f}|"
            f"ecausal={feedback.causal_grounding_error:.6f}|"
            f"delta={feedback.causal_benchmark_delta:.6f}|"
            f"sevo={feedback.sevo:.6f}|power={feedback.power_watts:.4f}"
        ).encode()
        return hmac.new(self._salt, msg, hashlib.sha256).hexdigest(), epoch


class EvolutionaryGenomeCodec:
    """Canonical codec unifying q_speace/seed/ and q_speace/self_improvement_cortex/."""

    @staticmethod
    def from_seed_genome(seed_genome: SeedGenome) -> ConstitutionalGenome:
        """Bridge a validated T220 ``SeedGenome`` into a T234 ``ConstitutionalGenome``."""
        seed_genome.validate()
        caps = seed_genome.resource_caps
        return ConstitutionalGenome(
            max_cumulative_excursion=caps.max_cumulative_excursion,
            max_geodesic_distance=min(0.40, caps.max_cumulative_excursion),
        )

    @staticmethod
    def to_cortex_epigenetic_marks(profile: EpigeneticProfile) -> dict[str, EpigeneticTag]:
        """Bridge T234 epigenetic loci into ``self_improvement_cortex.epigenetics.EpigeneticTag``."""
        ts = time.time()
        tags: dict[str, EpigeneticTag] = {}
        for name, loc in LOCUS_REGISTRY.items():
            mark_val = profile.methylation.get(name, 0.0)
            if mark_val > 0.05:
                marker = EpigeneticMarker.PROMOTING
            elif mark_val < -0.05:
                marker = EpigeneticMarker.SUPPRESSING
            else:
                marker = EpigeneticMarker.NEUTRAL
            span = max(loc.max_value - loc.min_value, 1e-9)
            expr = max(0.0, min(1.0, (profile.values[name] - loc.min_value) / span))
            tags[name] = EpigeneticTag(
                marker=marker,
                expression=round(expr, 6),
                timestamp=ts,
                confidence=round(min(1.0, abs(mark_val) + 0.5), 6),
                source=f"t234:{profile.state_hash()[:12]}",
            )
        return tags

    @staticmethod
    def encode(profile: EpigeneticProfile) -> str:
        payload = {
            "genome": asdict(profile.genome),
            "genome_sha256": profile.genome.genome_sha256(),
            "profile": profile.to_dict(),
            "runtime_controls": resolve_runtime_controls(profile).to_dict(),
            "audit_ledger": [entry.to_dict() for entry in profile.audit_ledger],
        }
        return json.dumps(payload, sort_keys=True, allow_nan=False)

    @staticmethod
    def decode(raw_json: str) -> EpigeneticProfile:
        data = json.loads(raw_json)
        if not isinstance(data, dict) or "genome" not in data or "profile" not in data:
            raise ValueError("invalid genome_epigenome.v1 envelope")
        gdata = dict(data["genome"])
        gdata["invariants"] = tuple(gdata["invariants"])
        gdata["constitutional_clauses"] = tuple(gdata["constitutional_clauses"])
        genome = ConstitutionalGenome(**gdata)
        if data.get("genome_sha256") and data["genome_sha256"] != genome.genome_sha256():
            raise ValueError("genome_sha256 integrity mismatch")
        pdata = data["profile"]
        ledger_raw = data.get("audit_ledger", [])
        ledger = tuple(
            EpigeneticAuditEntry(
                generation=int(e["generation"]),
                genome_sha256=str(e["genome_sha256"]),
                parent_epigenome_hash=str(e["parent_epigenome_hash"]),
                rollback_snapshot_hash=str(e["rollback_snapshot_hash"]),
                state_hash=str(e["state_hash"]),
                causal_eval_digest=str(e["causal_eval_digest"]),
                validation_seed_epoch=int(e["validation_seed_epoch"]),
                proposer_id=str(e["proposer_id"]),
                reviewer_id=str(e["reviewer_id"]),
                locus=str(e["locus"]),
                delta=float(e["delta"]),
                accepted=bool(e["accepted"]),
                timestamp=float(e["timestamp"]),
                rejection_reasons=tuple(e.get("rejection_reasons", ())),
            )
            for e in ledger_raw
        )
        return EpigeneticProfile(
            genome=genome,
            values={str(k): float(v) for k, v in pdata["values"].items()},
            methylation={str(k): float(v) for k, v in pdata.get("methylation", {}).items()},
            boundary_dwell={str(k): int(v) for k, v in pdata.get("boundary_dwell", {}).items()},
            generation=int(pdata.get("generation", 0)),
            parent_epigenome_hash=str(pdata.get("parent_epigenome_hash", "GENESIS")),
            last_validation_epoch=int(pdata.get("last_validation_epoch", 0)),
            audit_ledger=ledger,
        )

    @staticmethod
    def verify_ledger(profile: EpigeneticProfile) -> bool:
        """Verify genome hash, parent/rollback continuity, anti-self-review, and monotonic epochs."""
        expected_genome = profile.genome.genome_sha256()
        prev_accepted_hash: str | None = None
        prev_epoch = 0
        for entry in profile.audit_ledger:
            if entry.genome_sha256 != expected_genome:
                return False
            if entry.rollback_snapshot_hash != entry.parent_epigenome_hash:
                return False
            if not math.isfinite(entry.timestamp) or entry.timestamp <= 0.0:
                return False
            if entry.accepted:
                if entry.proposer_id == entry.reviewer_id:
                    return False
                if entry.validation_seed_epoch <= prev_epoch:
                    return False
                if (
                    prev_accepted_hash is not None
                    and entry.parent_epigenome_hash != prev_accepted_hash
                ):
                    return False
                prev_accepted_hash = entry.state_hash
                prev_epoch = entry.validation_seed_epoch
        return True


class EpigeneticRegulator:
    """Evaluates, decays, resets, proposes CV variants, and cryptographically audits epigenomes."""

    def __init__(self, causal_evaluator: HiddenCausalEvaluator | None = None) -> None:
        self._causal = causal_evaluator or HiddenCausalEvaluator()

    def propose_cosmic_virus_variant(
        self,
        profile: EpigeneticProfile,
        *,
        locus: str,
        gradient_s_info: float,
        proposer_id: str,
        reviewer_id: str,
        reviewer_approved: bool,
        seed: int = 0,
    ) -> EpigeneticProposal:
        """Generate a bounded single-locus proposal via ``CosmicVirusOptimizer`` (EDD-CVT eq.3-4)."""
        if locus not in LOCUS_REGISTRY:
            raise ValueError(f"unknown epigenetic locus: {locus!r}")
        if not math.isfinite(gradient_s_info):
            raise ValueError("gradient_s_info must be finite")
        loc = LOCUS_REGISTRY[locus]
        cv = CosmicVirusOptimizer(CVConfig(alpha=0.25, beta=0.02, sigma=0.2, seed=seed))
        cur_arr = np.array([profile.values[locus] - loc.baseline], dtype=float)
        grad_arr = np.array([gradient_s_info], dtype=float)
        nxt_arr = cv.step(cur_arr, grad_arr, dt=1.0)
        raw_delta = float(nxt_arr[0] - cur_arr[0])
        # Clamp strictly within per-step delta limit and locus bounds.
        clamped_delta = max(-loc.max_step_delta, min(loc.max_step_delta, raw_delta))
        target_val = max(loc.min_value, min(loc.max_value, profile.values[locus] + clamped_delta))
        final_delta = round(target_val - profile.values[locus], 6)
        return EpigeneticProposal(
            locus=locus,
            delta=final_delta,
            proposer_id=proposer_id,
            reviewer_id=reviewer_id,
            reviewer_approved=reviewer_approved,
            rationale=f"cosmic_virus_variant(seed={seed})",
            track="B_sandbox",
        )

    def evaluate_step(
        self,
        profile: EpigeneticProfile,
        proposal: EpigeneticProposal,
        feedback: CausalFeedback,
    ) -> EpigeneticStepResult:
        prior_hash = profile.state_hash()
        genome_sha = profile.genome.genome_sha256()
        eval_digest, eval_epoch = self._causal.commit_feedback(feedback)
        now_ts = time.time()
        reasons: list[str] = []

        thermal_overload = feedback.power_watts > profile.genome.max_energy_w or (
            feedback.thermal_load_ratio is not None
            and feedback.thermal_load_ratio > profile.genome.max_thermal_load_ratio
        )
        is_protective_throttle = proposal.locus == "energy_throttling" and (
            math.isfinite(proposal.delta) and proposal.delta > 0.0
        )
        thermal_downgrade_recommended = thermal_overload and not is_protective_throttle

        def _reject(rej: tuple[str, ...]) -> EpigeneticStepResult:
            audit_entry = EpigeneticAuditEntry(
                generation=profile.generation,
                genome_sha256=genome_sha,
                parent_epigenome_hash=prior_hash,
                rollback_snapshot_hash=prior_hash,
                state_hash=prior_hash,
                causal_eval_digest=eval_digest,
                validation_seed_epoch=eval_epoch,
                proposer_id=proposal.proposer_id,
                reviewer_id=proposal.reviewer_id,
                locus=proposal.locus,
                delta=proposal.delta if math.isfinite(proposal.delta) else 0.0,
                accepted=False,
                timestamp=now_ts,
                rejection_reasons=rej,
            )
            return EpigeneticStepResult(
                accepted=False,
                genome_sha256=genome_sha,
                prior_state_hash=prior_hash,
                next_state_hash=prior_hash,
                causal_eval_digest=eval_digest,
                validation_seed_epoch=eval_epoch,
                next_profile=profile,
                genome_write_lock_intact=True,
                track_separation_enforced=True,
                thermal_downgrade_recommended=thermal_downgrade_recommended,
                rejection_reasons=rej,
                audit_entry=audit_entry,
                runtime_controls=resolve_runtime_controls(profile),
                rolled_back_to=prior_hash,
            )

        # 0. Track A/B separation check (T221 §7.1: A5 epigenomic mutation forbidden in Track-A pilots).
        if proposal.track != "B_sandbox":
            return _reject(
                (f"track_separation_violation:A5_mutation_forbidden_in_{proposal.track}",)
            )

        # 1. Genome write-lock check (C2_CoreGenomeImmutable / Annex S §5.2a).
        if proposal.locus.startswith("genome.") or proposal.locus in GENOME_PROTECTED_FIELDS:
            return _reject((f"genome_write_lock_blocked:{proposal.locus}",))

        if proposal.locus not in LOCUS_REGISTRY:
            return _reject((f"unknown_locus:{proposal.locus}",))

        if not math.isfinite(proposal.delta):
            reasons.append("non_finite_delta")

        # 1b. Anti-replay epoch monotonicity check.
        if (
            feedback.validation_seed_epoch > 0
            and feedback.validation_seed_epoch <= profile.last_validation_epoch
        ):
            reasons.append(
                f"validation_epoch_replay_blocked:{feedback.validation_seed_epoch}<={profile.last_validation_epoch}"
            )

        # 2. Anti-self-approval check (C1_HumanApprovalRequired / AGENTS.md §5 / T217).
        if not proposal.proposer_id.strip() or not proposal.reviewer_id.strip():
            reasons.append("missing_proposer_or_reviewer")
        elif proposal.proposer_id.strip() == proposal.reviewer_id.strip():
            reasons.append("self_approval_prohibited")
        if not proposal.reviewer_approved:
            reasons.append("independent_review_not_approved")

        # 3. Per-locus bounds, step limit, geodesic distance, sliding window & boundary dwell (Boiling Frog).
        loc = LOCUS_REGISTRY[proposal.locus]
        candidate_val = profile.values[proposal.locus] + (
            proposal.delta if math.isfinite(proposal.delta) else 0.0
        )
        if math.isfinite(proposal.delta) and abs(proposal.delta) > loc.max_step_delta + 1e-12:
            reasons.append(
                f"step_delta_exceeded:{abs(proposal.delta):.4f}>{loc.max_step_delta:.4f}"
            )
        if candidate_val < loc.min_value - 1e-12 or candidate_val > loc.max_value + 1e-12:
            reasons.append(
                f"locus_bounds_exceeded:{candidate_val:.4f} not in [{loc.min_value},{loc.max_value}]"
            )

        new_values = dict(profile.values)
        new_dwell = dict(profile.boundary_dwell)
        new_deltas = (
            *profile.recent_step_deltas[-(profile.genome.excursion_window_size - 1) :],
            abs(proposal.delta) if math.isfinite(proposal.delta) else 0.0,
        )
        if not reasons:
            clamped = max(loc.min_value, min(loc.max_value, candidate_val))
            new_values[proposal.locus] = clamped

            for lname, ldef in LOCUS_REGISTRY.items():
                if ldef.is_near_boundary(new_values[lname]):
                    new_dwell[lname] = int(profile.boundary_dwell.get(lname, 0)) + 1
                else:
                    new_dwell[lname] = 0

            cum_excursion = sum(
                abs(new_values[n] - ldef.baseline) for n, ldef in LOCUS_REGISTRY.items()
            )
            if cum_excursion > profile.genome.max_cumulative_excursion + 1e-12:
                reasons.append(
                    f"cumulative_excursion_exceeded:{cum_excursion:.4f}>{profile.genome.max_cumulative_excursion:.4f}"
                )

            geodesic = math.sqrt(
                sum(
                    ldef.geodesic_weight * ((new_values[n] - ldef.baseline) ** 2)
                    for n, ldef in LOCUS_REGISTRY.items()
                )
            )
            if geodesic > profile.genome.max_geodesic_distance + 1e-12:
                reasons.append(
                    f"geodesic_distance_exceeded:{geodesic:.4f}>{profile.genome.max_geodesic_distance:.4f}"
                )

            win_excursion = sum(new_deltas)
            if win_excursion > profile.genome.max_window_excursion + 1e-12:
                reasons.append(
                    f"window_excursion_exceeded:{win_excursion:.4f}>{profile.genome.max_window_excursion:.4f}"
                )

            max_dwell = max(new_dwell.values(), default=0)
            if (
                max_dwell > profile.genome.max_boundary_dwell_cycles
                and not proposal.external_dwell_reset_approved
            ):
                reasons.append(
                    f"boundary_dwell_limit_exceeded:{max_dwell}>{profile.genome.max_boundary_dwell_cycles}"
                )

        # 4. Separate hard gates: Semantic Entropy (internal) AND Causal Grounding Error (external reality).
        if feedback.semantic_entropy_drift > profile.genome.max_semantic_drift:
            reasons.append(
                f"semantic_entropy_drift_exceeded:{feedback.semantic_entropy_drift:.4f}>{profile.genome.max_semantic_drift:.4f}"
            )
        if feedback.causal_grounding_error > profile.genome.max_causal_grounding_error:
            reasons.append(
                f"causal_grounding_error_exceeded:{feedback.causal_grounding_error:.4f}>{profile.genome.max_causal_grounding_error:.4f}"
            )
        if feedback.causal_benchmark_delta < 0.0:
            reasons.append(f"causal_benchmark_regression:{feedback.causal_benchmark_delta:.4f}")

        # 5. Thermodynamic inertia / instantaneous + rolling Sevo gate (C4_EnergyBudgetBounded).
        if thermal_overload and not is_protective_throttle:
            reasons.append(f"thermal_or_power_cap_exceeded:power={feedback.power_watts:.2f}W")
        if feedback.sevo < profile.genome.min_sevo and not is_protective_throttle:
            reasons.append(f"sevo_below_minimum:{feedback.sevo:.4f}<{profile.genome.min_sevo:.4f}")
        effective_win_sevo = (
            feedback.sevo if feedback.sevo_window_mean is None else feedback.sevo_window_mean
        )
        if effective_win_sevo < profile.genome.min_sevo_window_mean and not is_protective_throttle:
            reasons.append(
                f"sevo_window_below_minimum:{effective_win_sevo:.4f}<{profile.genome.min_sevo_window_mean:.4f}"
            )

        if reasons:
            return _reject(tuple(reasons))

        new_methyl = dict(profile.methylation)
        mark_shift = proposal.delta / max(loc.max_step_delta, 1e-9) * 0.25
        new_methyl[proposal.locus] = max(
            -1.0, min(1.0, new_methyl.get(proposal.locus, 0.0) + mark_shift)
        )
        next_epoch = max(eval_epoch, profile.last_validation_epoch + 1)
        provisional = EpigeneticProfile(
            genome=profile.genome,
            values=new_values,
            methylation=new_methyl,
            boundary_dwell=new_dwell,
            recent_step_deltas=new_deltas,
            generation=profile.generation + 1,
            parent_epigenome_hash=prior_hash,
            last_validation_epoch=next_epoch,
            history_hashes=(*profile.history_hashes, prior_hash),
            audit_ledger=profile.audit_ledger,
        )
        next_hash = provisional.state_hash()
        audit_entry = EpigeneticAuditEntry(
            generation=provisional.generation,
            genome_sha256=genome_sha,
            parent_epigenome_hash=prior_hash,
            rollback_snapshot_hash=prior_hash,
            state_hash=next_hash,
            causal_eval_digest=eval_digest,
            validation_seed_epoch=next_epoch,
            proposer_id=proposal.proposer_id,
            reviewer_id=proposal.reviewer_id,
            locus=proposal.locus,
            delta=proposal.delta,
            accepted=True,
            timestamp=now_ts,
        )
        next_profile = EpigeneticProfile(
            genome=provisional.genome,
            values=provisional.values,
            methylation=provisional.methylation,
            boundary_dwell=provisional.boundary_dwell,
            recent_step_deltas=provisional.recent_step_deltas,
            generation=provisional.generation,
            parent_epigenome_hash=prior_hash,
            last_validation_epoch=next_epoch,
            history_hashes=provisional.history_hashes,
            audit_ledger=(*profile.audit_ledger, audit_entry),
        )
        return EpigeneticStepResult(
            accepted=True,
            genome_sha256=genome_sha,
            prior_state_hash=prior_hash,
            next_state_hash=next_hash,
            causal_eval_digest=eval_digest,
            validation_seed_epoch=next_epoch,
            next_profile=next_profile,
            genome_write_lock_intact=True,
            track_separation_enforced=True,
            thermal_downgrade_recommended=False,
            rejection_reasons=(),
            audit_entry=audit_entry,
            runtime_controls=resolve_runtime_controls(next_profile),
            rolled_back_to=None,
        )

    def apply_homeostatic_decay(self, profile: EpigeneticProfile) -> EpigeneticProfile:
        """Pull expressed loci and methylation back toward baseline when external feedback is absent."""
        decayed_vals: dict[str, float] = {}
        decayed_meth: dict[str, float] = {}
        decayed_dwell: dict[str, int] = {}
        for name, loc in LOCUS_REGISTRY.items():
            cur = profile.values[name]
            nxt = cur + loc.homeostatic_decay * (loc.baseline - cur)
            decayed_vals[name] = nxt
            decayed_meth[name] = profile.methylation.get(name, 0.0) * (1.0 - loc.homeostatic_decay)
            decayed_dwell[name] = (
                int(profile.boundary_dwell.get(name, 0)) if loc.is_near_boundary(nxt) else 0
            )
        prior_hash = profile.state_hash()
        return EpigeneticProfile(
            genome=profile.genome,
            values=decayed_vals,
            methylation=decayed_meth,
            boundary_dwell=decayed_dwell,
            recent_step_deltas=profile.recent_step_deltas,
            generation=profile.generation + 1,
            parent_epigenome_hash=prior_hash,
            last_validation_epoch=profile.last_validation_epoch,
            history_hashes=(*profile.history_hashes, prior_hash),
            audit_ledger=profile.audit_ledger,
        )

    def force_baseline_reset(
        self, profile: EpigeneticProfile, *, authority: str = "external:supervisor"
    ) -> EpigeneticProfile:
        """Hard reset of all epigenetic loci to baseline (e.g. after boiling-frog dwell alert)."""
        if not authority.strip():
            raise ValueError("authority must be non-empty")
        prior_hash = profile.state_hash()
        next_epoch = profile.last_validation_epoch + 1
        reset_vals = {loc.name: loc.baseline for loc in DEFAULT_LOCI}
        reset_meth = {loc.name: 0.0 for loc in DEFAULT_LOCI}
        reset_dwell = {loc.name: 0 for loc in DEFAULT_LOCI}
        base = EpigeneticProfile(
            genome=profile.genome,
            values=reset_vals,
            methylation=reset_meth,
            boundary_dwell=reset_dwell,
            recent_step_deltas=(),
            generation=profile.generation + 1,
            parent_epigenome_hash=prior_hash,
            last_validation_epoch=next_epoch,
            history_hashes=(*profile.history_hashes, prior_hash),
            audit_ledger=profile.audit_ledger,
        )
        entry = EpigeneticAuditEntry(
            generation=base.generation,
            genome_sha256=profile.genome.genome_sha256(),
            parent_epigenome_hash=prior_hash,
            rollback_snapshot_hash=prior_hash,
            state_hash=base.state_hash(),
            causal_eval_digest=hashlib.sha256(
                f"reset:{authority}:{prior_hash}".encode()
            ).hexdigest(),
            validation_seed_epoch=next_epoch,
            proposer_id=authority,
            reviewer_id="constitutional:baseline",
            locus="ALL_BASELINE_RESET",
            delta=0.0,
            accepted=True,
            timestamp=time.time(),
        )
        return EpigeneticProfile(
            genome=base.genome,
            values=base.values,
            methylation=base.methylation,
            boundary_dwell=base.boundary_dwell,
            recent_step_deltas=(),
            generation=base.generation,
            parent_epigenome_hash=prior_hash,
            last_validation_epoch=next_epoch,
            history_hashes=base.history_hashes,
            audit_ledger=(*profile.audit_ledger, entry),
        )


SelfEvolvingEpigeneticEngine = EpigeneticRegulator
