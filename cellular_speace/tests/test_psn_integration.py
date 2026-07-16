"""Quick integration test for the PSN Phase C implementation."""
import sys
sys.path.insert(0, ".")

from speace_core.cellular_brain.psn import (
    Physiome, PhysiologicalSignalBus, NeuralBus, EndocrineBus, DigitalMetabolism,
)

def main():
    # 1. Load Physiome from YAML
    physiome = Physiome("speace_core/dna/genome/physiology")
    physiome.load()
    violations = physiome.validate()
    if violations:
        print("VIOLATIONS:", violations)
        return False
    print("Physiome: valid")
    print(f"  Systems: {len(physiome.systems)}")
    print(f"  Organs: {len(physiome.organs)}")
    print(f"  Tissues: {len(physiome.tissues_by_id)}")
    print(f"  Cells: {len(physiome.cells)}")
    print(f"  Molecules: {len(physiome.molecules)}")
    print(f"  Constitutional signals: {len(physiome.constitutional_signals)}")
    print(f"  Epigenetic signals: {len(physiome.epigenetic_signals)}")
    print(f"  Receptors: {len(physiome.receptors)} tissues")
    print(f"  Policies: {len(physiome.policies)}")

    # 2. Create PSN from Physiome
    psn = PhysiologicalSignalBus(physiome)
    hp = psn.endocrine.snapshot()
    print(f"PSN: {len(hp)} hormone pools registered")
    print(f"PSN: {psn.metabolism.tissue_count} tissue budgets registered")

    # 3. Test basic operations
    psn.tick_begin(1)
    psn.publish_stream("stress", 0.7, source="hpa_axis")
    psn.publish_stream("energy", 0.4, source="metabolism")
    psn.publish_event("reward", 0.9, source="VTA", category="reward")
    psn.tick_end(1)

    snap = psn.snapshot(1)
    print(f"Streams: {snap.streams}")
    print(f"Neural synapses: {len(snap.neural_synapses)}")
    active = {k: round(v, 3) for k, v in snap.endocrine_pools.items() if v > 0.01}
    print(f"Endocrine pools: {active}")
    print(f"Global energy: {round(snap.global_energy, 3)}")
    print(f"Temperature: {round(snap.temperature, 3)}")

    # 4. Test second tick with decay
    psn.tick_begin(2)
    psn.tick_end(2)
    cortisol = round(psn.endocrine.read("cortisol") or 0, 3)
    print(f"Tick 2 cortisol: {cortisol}")
    energy = round(psn.read_stream("energy") or 0, 3)
    print(f"Tick 2 energy stream: {energy}")

    # 5. Test policy evaluation
    alloc = psn.evaluate_policy("energy_allocation", {"stress": 0.7, "fatigue": 0.3, "threat": 0.5})
    print(f"Policy allocation: {alloc}")

    # 6. Test snapshots
    print(f"Stream snapshot: {psn.stream_snapshot()}")

    print("All checks passed.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
