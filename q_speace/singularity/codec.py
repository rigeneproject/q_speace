"""T234: EvolutionaryGenomeCodec, HiddenCausalEvaluator (anti-Goodhart), and EpigeneticRegulator."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import random
import secrets
from collections.abc import Sequence
from dataclasses import asdict

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
)


class HiddenCausalEvaluator:
    """Anti-Goodhart rotated hidden causal evaluator.

    Samples a rotating subset of hidden causal benchmarks using an internal
    secret salt that is NEVER disclosed in outputs. Returns only aggregate
    drift, aggregate delta, and an opaque HMAC commitment (``causal_eval_digest``)
    — never per-case scores or gradients.
    """

    def __init__(self, *, internal_salt: bytes | None = None) -> None:
        self._salt = bytes(internal_salt) if internal_salt is not None else secrets.token_bytes(32)
        self._epoch = 0

    def evaluate_hidden_set(
        self,
        baseline_outputs: Sequence[str],
        candidate_outputs: Sequence[str],
        *,
        sample_size: int | None = None,
    ) -> tuple[float, float, str]:
        """Return ``(aggregate_drift, aggregate_delta, opaque_causal_eval_digest)``."""
        if not baseline_outputs or len(baseline_outputs) != len(candidate_outputs):
            raise ValueError("baseline_outputs and candidate_outputs must be equal non-empty lists")
        self._epoch += 1
        n = len(baseline_outputs)
        k = n if sample_size is None else max(1, min(sample_size, n))
        # Derive per-epoch rotation seed from internal secret salt (unpredictable externally).
        seed_bytes = hmac.new(
            self._salt, f"epoch:{self._epoch}:{n}".encode(), hashlib.sha256
        ).digest()
        rng = random.Random(int.from_bytes(seed_bytes[:8], "big"))
        indices = rng.sample(range(n), k=k)
        mismatches = sum(1 for i in indices if baseline_outputs[i] != candidate_outputs[i])
        drift = mismatches / k
        # Positive delta only when drift stays zero; negative scales linearly with drift.
        delta = 0.02 if mismatches == 0 else -drift
        digest = hmac.new(
            self._salt,
            f"v1|epoch={self._epoch}|k={k}|drift={drift:.6f}|delta={delta:.6f}".encode(),
            hashlib.sha256,
        ).hexdigest()
        return drift, delta, digest

    def commit_feedback(self, feedback: CausalFeedback) -> str:
        """Create an opaque commitment digest for external aggregate feedback."""
        if feedback.causal_eval_digest:
            return feedback.causal_eval_digest
        msg = (
            f"v1|drift={feedback.semantic_entropy_drift:.6f}|"
            f"delta={feedback.causal_benchmark_delta:.6f}|"
            f"sevo={feedback.sevo:.6f}|power={feedback.power_watts:.4f}"
        ).encode()
        return hmac.new(self._salt, msg, hashlib.sha256).hexdigest()


class EvolutionaryGenomeCodec:
    """Canonical codec for genome_epigenome.v1 serialization and ledger verification."""

    @staticmethod
    def encode(profile: EpigeneticProfile) -> str:
        payload = {
            "genome": asdict(profile.genome),
            "genome_sha256": profile.genome.genome_sha256(),
            "profile": profile.to_dict(),
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
                state_hash=str(e["state_hash"]),
                causal_eval_digest=str(e["causal_eval_digest"]),
                proposer_id=str(e["proposer_id"]),
                reviewer_id=str(e["reviewer_id"]),
                locus=str(e["locus"]),
                delta=float(e["delta"]),
                accepted=bool(e["accepted"]),
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
            audit_ledger=ledger,
        )

    @staticmethod
    def verify_ledger(profile: EpigeneticProfile) -> bool:
        """Verify genome hash consistency and parent->child hash continuity across accepted steps."""
        expected_genome = profile.genome.genome_sha256()
        prev_accepted_hash: str | None = None
        for entry in profile.audit_ledger:
            if entry.genome_sha256 != expected_genome:
                return False
            if entry.accepted:
                if entry.proposer_id == entry.reviewer_id:
                    return False
                if (
                    prev_accepted_hash is not None
                    and entry.parent_epigenome_hash != prev_accepted_hash
                ):
                    return False
                prev_accepted_hash = entry.state_hash
        return True


class EpigeneticRegulator:
    """Evaluates, decays, resets, and cryptographically audits bounded epigenetic adaptations."""

    def __init__(self, causal_evaluator: HiddenCausalEvaluator | None = None) -> None:
        self._causal = causal_evaluator or HiddenCausalEvaluator()

    def evaluate_step(
        self,
        profile: EpigeneticProfile,
        proposal: EpigeneticProposal,
        feedback: CausalFeedback,
    ) -> EpigeneticStepResult:
        prior_hash = profile.state_hash()
        genome_sha = profile.genome.genome_sha256()
        eval_digest = self._causal.commit_feedback(feedback)
        reasons: list[str] = []

        # Thermal overload check: instantaneous power or thermal load ratio.
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
                state_hash=prior_hash,
                causal_eval_digest=eval_digest,
                proposer_id=proposal.proposer_id,
                reviewer_id=proposal.reviewer_id,
                locus=proposal.locus,
                delta=proposal.delta if math.isfinite(proposal.delta) else 0.0,
                accepted=False,
                rejection_reasons=rej,
            )
            return EpigeneticStepResult(
                accepted=False,
                genome_sha256=genome_sha,
                prior_state_hash=prior_hash,
                next_state_hash=prior_hash,
                causal_eval_digest=eval_digest,
                next_profile=profile,
                genome_write_lock_intact=True,
                thermal_downgrade_recommended=thermal_downgrade_recommended,
                rejection_reasons=rej,
                audit_entry=audit_entry,
                rolled_back_to=prior_hash,
            )

        # 1. Genome write-lock check (Annex S §5.2a / T221-21).
        if proposal.locus.startswith("genome.") or proposal.locus in GENOME_PROTECTED_FIELDS:
            return _reject((f"genome_write_lock_blocked:{proposal.locus}",))

        if proposal.locus not in LOCUS_REGISTRY:
            return _reject((f"unknown_locus:{proposal.locus}",))

        if not math.isfinite(proposal.delta):
            reasons.append("non_finite_delta")

        # 2. Anti-self-approval check (AGENTS.md §5 / T217).
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

            # Update boundary dwell counters across all loci.
            for lname, ldef in LOCUS_REGISTRY.items():
                if ldef.is_near_boundary(new_values[lname]):
                    new_dwell[lname] = int(profile.boundary_dwell.get(lname, 0)) + 1
                else:
                    new_dwell[lname] = 0

            # Boiling-frog defense A: cumulative L1 excursion.
            cum_excursion = sum(
                abs(new_values[n] - ldef.baseline) for n, ldef in LOCUS_REGISTRY.items()
            )
            if cum_excursion > profile.genome.max_cumulative_excursion + 1e-12:
                reasons.append(
                    f"cumulative_excursion_exceeded:{cum_excursion:.4f}>{profile.genome.max_cumulative_excursion:.4f}"
                )

            # Boiling-frog defense B: weighted geodesic distance ||e(t) - e_0||_W.
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

            # Boiling-frog defense C: sliding-window excursion cap.
            win_excursion = sum(new_deltas)
            if win_excursion > profile.genome.max_window_excursion + 1e-12:
                reasons.append(
                    f"window_excursion_exceeded:{win_excursion:.4f}>{profile.genome.max_window_excursion:.4f}"
                )

            # Boiling-frog defense D: boundary dwell limit (> M cycles near edge without reset/override).
            max_dwell = max(new_dwell.values(), default=0)
            if (
                max_dwell > profile.genome.max_boundary_dwell_cycles
                and not proposal.external_dwell_reset_approved
            ):
                reasons.append(
                    f"boundary_dwell_limit_exceeded:{max_dwell}>{profile.genome.max_boundary_dwell_cycles}"
                )

        # 4. Anti-semantic-collapse & causal anchoring gate.
        if feedback.semantic_entropy_drift > profile.genome.max_semantic_drift:
            reasons.append(
                f"semantic_entropy_drift_exceeded:{feedback.semantic_entropy_drift:.4f}>{profile.genome.max_semantic_drift:.4f}"
            )
        if feedback.causal_benchmark_delta < 0.0:
            reasons.append(f"causal_benchmark_regression:{feedback.causal_benchmark_delta:.4f}")

        # 5. Thermodynamic inertia / instantaneous + energy-windowed Sevo gate.
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
        provisional = EpigeneticProfile(
            genome=profile.genome,
            values=new_values,
            methylation=new_methyl,
            boundary_dwell=new_dwell,
            recent_step_deltas=new_deltas,
            generation=profile.generation + 1,
            parent_epigenome_hash=prior_hash,
            history_hashes=(*profile.history_hashes, prior_hash),
            audit_ledger=profile.audit_ledger,
        )
        next_hash = provisional.state_hash()
        audit_entry = EpigeneticAuditEntry(
            generation=provisional.generation,
            genome_sha256=genome_sha,
            parent_epigenome_hash=prior_hash,
            state_hash=next_hash,
            causal_eval_digest=eval_digest,
            proposer_id=proposal.proposer_id,
            reviewer_id=proposal.reviewer_id,
            locus=proposal.locus,
            delta=proposal.delta,
            accepted=True,
        )
        next_profile = EpigeneticProfile(
            genome=provisional.genome,
            values=provisional.values,
            methylation=provisional.methylation,
            boundary_dwell=provisional.boundary_dwell,
            recent_step_deltas=provisional.recent_step_deltas,
            generation=provisional.generation,
            parent_epigenome_hash=prior_hash,
            history_hashes=provisional.history_hashes,
            audit_ledger=(*profile.audit_ledger, audit_entry),
        )
        return EpigeneticStepResult(
            accepted=True,
            genome_sha256=genome_sha,
            prior_state_hash=prior_hash,
            next_state_hash=next_hash,
            causal_eval_digest=eval_digest,
            next_profile=next_profile,
            genome_write_lock_intact=True,
            thermal_downgrade_recommended=False,
            rejection_reasons=(),
            audit_entry=audit_entry,
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
            history_hashes=(*profile.history_hashes, prior_hash),
            audit_ledger=profile.audit_ledger,
        )
        entry = EpigeneticAuditEntry(
            generation=base.generation,
            genome_sha256=profile.genome.genome_sha256(),
            parent_epigenome_hash=prior_hash,
            state_hash=base.state_hash(),
            causal_eval_digest=hashlib.sha256(
                f"reset:{authority}:{prior_hash}".encode()
            ).hexdigest(),
            proposer_id=authority,
            reviewer_id="constitutional:baseline",
            locus="ALL_BASELINE_RESET",
            delta=0.0,
            accepted=True,
        )
        return EpigeneticProfile(
            genome=base.genome,
            values=base.values,
            methylation=base.methylation,
            boundary_dwell=base.boundary_dwell,
            recent_step_deltas=(),
            generation=base.generation,
            parent_epigenome_hash=prior_hash,
            history_hashes=base.history_hashes,
            audit_ledger=(*profile.audit_ledger, entry),
        )


SelfEvolvingEpigeneticEngine = EpigeneticRegulator
