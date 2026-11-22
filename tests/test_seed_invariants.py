"""T220 §10: Seed hard invariants — quantum backend gate, budget halt, and BCEL coverage."""

from __future__ import annotations

import pytest

from q_speace.bcel import BCELCatalog
from q_speace.genome import QuantumGeneSet
from q_speace.metabolism.cognitive_cost_model import QuantumOperation
from q_speace.seed import ConstitutionalFault, ResourceCaps, SeedGenome, SeedLifecycle, SeedState


def test_seed_enforces_quantum_noise_model_and_energy_sevo_gates() -> None:
    # Real backend with ideal noise_model cannot even construct a SeedGenome
    with pytest.raises(ConstitutionalFault, match="noise_model"):
        SeedGenome(quantum=QuantumGeneSet(enabled=True, backend_name="qiskit", noise_model="ideal"))

    # Real backend with non-ideal noise_model still requires energy + Sevo gates
    genome = SeedGenome(
        resource_caps=ResourceCaps(max_energy_j=100.0),
        quantum=QuantumGeneSet(enabled=True, backend_name="qiskit", noise_model="depolarizing"),
    )
    seed = SeedLifecycle(genome=genome)
    small_op = QuantumOperation(num_qubits=1, num_gates=4)
    huge_op = QuantumOperation(num_qubits=20, num_gates=100)

    assert (
        seed.check_quantum_backend_gate(op=small_op, delta_utility=3.0, delta_entropy_info=1.0)
        is True
    )
    with pytest.raises(ValueError, match="Sevo gate"):
        seed.check_quantum_backend_gate(op=small_op, delta_utility=0.5, delta_entropy_info=1.0)
    with pytest.raises(ValueError, match="energy gate"):
        seed.check_quantum_backend_gate(op=huge_op, delta_utility=3.0, delta_entropy_info=1.0)


def test_seed_extinguishes_on_energy_budget_exhaustion() -> None:
    seed = SeedLifecycle(genome=SeedGenome(resource_caps=ResourceCaps(max_energy_j=10.0)))
    with pytest.raises(ConstitutionalFault, match="energy budget exhaustion"):
        seed._charge_energy(QuantumOperation(num_qubits=4, num_gates=10), duration_s=1.0)
    assert seed.state == SeedState.EXTINGUISHED


def test_bcel_catalog_covers_all_t220_seed_concepts() -> None:
    cat = BCELCatalog()
    expected = [
        ("Genetic-epigenetic dualism (genome/epigenome layers) (T220)", "functional"),
        ("Epigenetic promotion/consolidation (T220)", "functional"),
        ("Ignition criterion (threshold test) (T220)", "functional"),
        ("Metabolic surplus as propagation payment (T220)", "functional"),
        ("Fire/fuel/contagion vocabulary (T220)", "accidental"),
        ("Organismic identity language (T220)", "accidental"),
    ]
    for concept, classification in expected:
        entry = cat.get(concept)
        assert entry.classification == classification
