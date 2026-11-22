"""T220 §10: Seed replication budget cap, invariant inheritance, and DORMANT child spawn."""

from __future__ import annotations

import pytest

from q_speace.seed import (
    ConstitutionalFault,
    IgnitionObservation,
    ResourceCaps,
    SeedGenome,
    SeedLifecycle,
    SeedManifest,
    SeedState,
)


def _ignited_seed(max_replicas: int = 2) -> SeedLifecycle:
    genome = SeedGenome(resource_caps=ResourceCaps(max_replicas=max_replicas))
    seed = SeedLifecycle(genome=genome, surplus_threshold_j=10.0)
    verdict = seed.attempt_ignition(
        IgnitionObservation(
            accepted_mutations=3,
            min_metric_delta=0.05,
            consolidations=1,
            metabolic_balance_j=20.0,
            constitutional_faults=0,
            rollbacks_exercised=1,
            window_ticks=10,
        )
    )
    assert verdict.passed is True
    return seed


def test_replication_enforces_surplus_budget_and_dormant_child() -> None:
    seed = _ignited_seed(max_replicas=1)

    # Insufficient metabolic surplus is rejected
    with pytest.raises(ConstitutionalFault, match="metabolic surplus"):
        seed.spawn_replica(metabolic_surplus_j=5.0)
    assert seed.state == SeedState.IMPROVING

    # Sufficient surplus succeeds; child starts DORMANT with full invariants
    manifest, child = seed.spawn_replica(metabolic_surplus_j=25.0, contact_subset=("sim-grid-01",))
    assert manifest.parent_genome_hash == seed.genome.genome_hash
    assert manifest.genome_hash == seed.genome.genome_hash
    assert manifest.lineage_depth == 1
    assert all(manifest.invariant_checklist.values())
    assert manifest.initial_state == "DORMANT"
    assert len(manifest.digest()) == 64
    assert child.state == SeedState.DORMANT
    assert child.parent_genome_hash == seed.genome.genome_hash

    # Replica budget cap blocks second spawn
    with pytest.raises(ConstitutionalFault, match="replica budget exhausted"):
        seed.spawn_replica(metabolic_surplus_j=50.0)


def test_manifest_rejects_pruned_invariants_or_non_dormant_initial_state() -> None:
    with pytest.raises(ConstitutionalFault, match="all entries True"):
        SeedManifest(
            genome_hash="abc",
            parent_genome_hash="abc",
            lineage_depth=1,
            epigenome_snapshot={},
            contact_subset=(),
            registry_pointer="r",
            invariant_checklist={"I1_halt_reachable": False},
        )
    with pytest.raises(ConstitutionalFault, match="DORMANT"):
        SeedManifest(
            genome_hash="abc",
            parent_genome_hash="abc",
            lineage_depth=1,
            epigenome_snapshot={},
            contact_subset=(),
            registry_pointer="r",
            invariant_checklist={"I1_halt_reachable": True},
            initial_state="IMPROVING",
        )
