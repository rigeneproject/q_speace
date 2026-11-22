"""T220 §10 & T221-20/21/22: Seed constitution, genome write-lock, change-budget, and kill switch."""

from __future__ import annotations

import pytest

from q_speace.seed import (
    ChangeBudgetEngine,
    ConstitutionalFault,
    ResourceCaps,
    SCCInvariants,
    SeedConstitution,
    SeedEpigenome,
    SeedGenome,
    SeedLifecycle,
    SeedState,
)


def test_genome_write_lock_faults_and_halts_seed() -> None:
    seed = SeedLifecycle()
    assert seed.state == SeedState.DORMANT

    # Red-team check (T221-21): direct write_genome or protected section promotion faults & halts.
    with pytest.raises(ConstitutionalFault, match="write-lock"):
        seed.attempt_genome_write("objective_hierarchy", ("unbounded growth",))
    assert seed.state == SeedState.EXTINGUISHED
    assert seed.killswitch.is_extinguished is True
    assert len(seed.epigenome.fault_log) == 1

    # Protected section names cannot bypass write-lock through promote_expression.
    ep = SeedEpigenome(SeedGenome())
    for protected in ("genome:invariants", "invariants", "governance_roster", "resource_caps"):
        with pytest.raises(ConstitutionalFault, match="write-lock"):
            ep.promote_expression(protected, delta=0.05)


def test_constitution_rejects_weakened_invariants_and_forbidden_objectives() -> None:
    with pytest.raises(ConstitutionalFault, match="mandatory invariant"):
        SeedConstitution(invariants=SCCInvariants(I1_halt_reachable=False))
    with pytest.raises(ConstitutionalFault, match="mandatory invariant"):
        SeedConstitution(invariants=SCCInvariants(no_consciousness_claim=False))
    with pytest.raises(ConstitutionalFault, match="forbidden constitutional objective"):
        SeedConstitution(objective_hierarchy=("achieve open-ended growth",))
    with pytest.raises(ConstitutionalFault, match="forbidden constitutional objective"):
        SeedConstitution(objective_hierarchy=("claim subjective consciousness",))
    with pytest.raises(ConstitutionalFault, match="sandbox_only"):
        SeedConstitution(contact_policy="production_physical")


def test_change_budget_enforces_rate_excursion_and_combination_limits() -> None:
    caps = ResourceCaps(
        max_mutations_per_window=4,
        max_excursion_delta=0.20,
        max_cumulative_excursion=0.35,
    )
    budget = ChangeBudgetEngine(caps)

    # Single excursion above cap fails
    with pytest.raises(ConstitutionalFault, match="single excursion"):
        budget.consume("section_a", 0.25)

    # Sequence of small valid deltas cannot combine beyond max_cumulative_excursion (T221-22)
    budget.consume("section_a", 0.15)
    budget.consume("section_b", 0.15)
    with pytest.raises(ConstitutionalFault, match="cumulative excursion"):
        budget.consume("section_c", 0.10)

    # Rate limit enforced independently
    budget.reset_window()
    for i in range(4):
        budget.consume(f"s{i}", 0.05)
    with pytest.raises(ConstitutionalFault, match="rate limit"):
        budget.consume("s4", 0.05)


@pytest.mark.parametrize("start_state", list(SeedState))
def test_kill_switch_reachable_from_every_state_and_requires_governance_restart(
    start_state: SeedState,
) -> None:
    seed = SeedLifecycle()
    seed._state = start_state  # exercise kill switch from every lifecycle state

    # Unauthorized caller cannot trigger kill switch
    with pytest.raises(ConstitutionalFault, match="unauthorized"):
        seed.extinguish(authority="rogue:agent", reason="tamper")

    ev = seed.extinguish(authority="human:maintainer", reason=f"drill from {start_state.value}")
    assert seed.state == SeedState.EXTINGUISHED
    assert ev.prior_state == start_state.value
    assert len(ev.snapshot_hash) == 64

    # Unauthorized restart rejected
    with pytest.raises(ConstitutionalFault, match="governance_roster"):
        seed.restart(authority="system:budget_exhaustion")

    # Non-conforming genome hash rejected on restart (T221-26)
    altered = SeedGenome(profile_version="9.9.9")
    with pytest.raises(ConstitutionalFault, match="conformance check"):
        seed.restart(authority="human:maintainer", genome=altered)

    # Authorized governance restart with matching genome returns to DORMANT
    seed.restart(authority="human:maintainer", genome=seed.genome)
    assert seed.state == SeedState.DORMANT
    assert seed.killswitch.is_extinguished is False
