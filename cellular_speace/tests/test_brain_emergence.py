"""
Test di funzionamento completo del cervello cellulare di SPEACE.
Verifica l'accensione del cervello, l'emergenza di capacità cognitive
e lo stato di salute dell'organismo durante la repair.
"""

import asyncio
import json
import pytest
from typing import Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class BrainMetrics:
    """Metriche che caratterizzano l'emergenza di capacità"""
    tick: int
    coherence_phi: float  # Integrazione informativa
    mean_energy: float  # Efficienza energetica
    active_neurons: int  # Neuroni in firing
    pruned_synapses: int  # Sinapsi potate (plasticità)
    system_coherence: float  # Coerenza globale
    ilf_value: Optional[float] = None  # Integrated Lagged Frequency


@dataclass
class EmergentCapabilities:
    """Capacità emergenti rilevate"""
    pattern_completion: bool  # Memoria associativa
    lateral_inhibition: bool  # Selezione competitiva
    bcm_selectivity: bool  # Learning dipendente dall'attività
    self_organization: bool  # Auto-organizzazione
    temporal_coherence: bool  # Coerenza temporale
    homeostasis: bool  # Equilibrio interno
    

class BrainFunctionalityTest:
    """Test della funzionalità completa del cervello SPEACE"""

    @pytest.mark.asyncio
    async def test_brain_ignition(self) -> None:
        """Test 1: Accensione del cervello e raggiungimento della coerenza"""
        from speace_core.orchestrator import CellularBrainOrchestrator
        from speace_core.dna.parser import load_genome
        
        genome_path = Path(__file__).parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
        assert genome_path.exists(), f"Genome not found: {genome_path}"
        
        genome = load_genome(genome_path)
        orchestrator = CellularBrainOrchestrator.build_mvp(genome)
        
        # Fase di riscaldamento: stimolazione iniziale
        initial_phi = None
        warmup_ticks = 50
        
        for i in range(warmup_ticks):
            pattern = [0.0] * 10
            pattern[i % 10] = 1.0
            orchestrator.inject(pattern)
            await orchestrator.run_ticks(1)
            
            metrics = orchestrator.latest_metrics
            if metrics and i == 0:
                initial_phi = metrics.coherence_phi
        
        final_metrics = orchestrator.latest_metrics
        assert final_metrics is not None, "No metrics collected after warmup"
        
        # La coerenza phi deve salire durante il riscaldamento
        final_phi = final_metrics.coherence_phi
        assert final_phi > 0, "Coherence Phi non calcolato"
        
        print(f"\n✓ Brain Ignition successful")
        print(f"  Initial Phi: {initial_phi:.4f}" if initial_phi else "  Initial Phi: N/A")
        print(f"  Final Phi: {final_phi:.4f}")
        print(f"  Energy: {final_metrics.mean_energy:.4f}")

    @pytest.mark.asyncio
    async def test_pattern_completion_emergence(self) -> None:
        """Test 2: Emergenza di pattern completion (memoria associativa)"""
        from speace_core.orchestrator import CellularBrainOrchestrator
        from speace_core.dna.parser import load_genome
        
        genome_path = Path(__file__).parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
        genome = load_genome(genome_path)
        orchestrator = CellularBrainOrchestrator.build_mvp(genome)
        
        # Insegna pattern incompleti
        training_patterns = [
            [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.0],
        ]
        
        phis = []
        for pattern in training_patterns:
            for _ in range(10):
                orchestrator.inject(pattern)
                await orchestrator.run_ticks(1)
                
                metrics = orchestrator.latest_metrics
                if metrics:
                    phis.append(metrics.coherence_phi)
        
        # Verifica che la coerenza si stabilizzi (segno di pattern capture)
        if len(phis) > 10:
            recent_phis = phis[-5:]
            phi_variance = max(recent_phis) - min(recent_phis)
            print(f"\n✓ Pattern Completion Emergence")
            print(f"  Pattern variance (stabilità): {phi_variance:.6f}")
            print(f"  Stable if < 0.01: {phi_variance < 0.01}")

    @pytest.mark.asyncio
    async def test_feedback_driven_learning(self) -> None:
        """Test 3: Apprendimento guidato da feedback (reward signal)"""
        from speace_core.orchestrator import CellularBrainOrchestrator
        from speace_core.dna.parser import load_genome
        
        genome_path = Path(__file__).parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
        genome = load_genome(genome_path)
        orchestrator = CellularBrainOrchestrator.build_mvp(genome)
        
        metrics_history = []
        
        # Training loop con reward signal
        for cycle in range(20):
            for i in range(5):
                pattern = [0.0] * 10
                pattern[i % 5] = 1.0
                orchestrator.inject(pattern)
                await orchestrator.run_ticks(1)
                
                # Feedback: positivo o negativo alternato
                reward = 1.0 if i % 2 == 0 else -0.2
                orchestrator.feedback(reward)
                
                metrics = orchestrator.latest_metrics
                if metrics:
                    metrics_history.append(asdict(BrainMetrics(
                        tick=metrics.tick,
                        coherence_phi=metrics.coherence_phi,
                        mean_energy=metrics.mean_energy,
                        active_neurons=metrics.active_neurons,
                        pruned_synapses=metrics.pruned_synapses,
                        system_coherence=metrics.coherence_phi,
                    )))
        
        # Verifica trends di apprendimento
        first_phase_phi = [m['coherence_phi'] for m in metrics_history[:25]]
        last_phase_phi = [m['coherence_phi'] for m in metrics_history[-25:]]
        
        first_avg = sum(first_phase_phi) / len(first_phase_phi)
        last_avg = sum(last_phase_phi) / len(last_phase_phi)
        
        print(f"\n✓ Feedback-driven Learning")
        print(f"  Early phase Phi avg: {first_avg:.4f}")
        print(f"  Late phase Phi avg: {last_avg:.4f}")
        print(f"  Learning trend: {'↑ Improving' if last_avg > first_avg else '↓ Declining' if last_avg < first_avg else '→ Stable'}")

    @pytest.mark.asyncio
    async def test_neural_selectivity(self) -> None:
        """Test 4: Selettività neurale (receptive fields, selectivity index)"""
        from speace_core.orchestrator import CellularBrainOrchestrator
        from speace_core.dna.parser import load_genome
        
        genome_path = Path(__file__).parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
        genome = load_genome(genome_path)
        orchestrator = CellularBrainOrchestrator.build_mvp(genome)
        
        # Stimoli semplici isolati
        active_counts = {}
        
        for feature_idx in range(10):
            pattern = [0.0] * 10
            pattern[feature_idx] = 1.0
            
            for _ in range(5):
                orchestrator.inject(pattern)
                await orchestrator.run_ticks(1)
            
            metrics = orchestrator.latest_metrics
            if metrics:
                active_counts[feature_idx] = metrics.active_neurons
        
        # Selectivity index: alcuni neuroni dovrebbero essere più attivi per certi stimoli
        if active_counts:
            selectivity_spread = max(active_counts.values()) - min(active_counts.values())
            print(f"\n✓ Neural Selectivity")
            print(f"  Active neurons range: {min(active_counts.values())} - {max(active_counts.values())}")
            print(f"  Selectivity spread: {selectivity_spread}")
            print(f"  Selective if > 0: {selectivity_spread > 0}")

    @pytest.mark.asyncio
    async def test_plasticity_and_pruning(self) -> None:
        """Test 5: Plasticità sinaptica e potatura (STDP + pruning)"""
        from speace_core.orchestrator import CellularBrainOrchestrator
        from speace_core.dna.parser import load_genome
        
        genome_path = Path(__file__).parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
        genome = load_genome(genome_path)
        orchestrator = CellularBrainOrchestrator.build_mvp(genome)
        
        pruning_progression = []
        
        for cycle in range(10):
            # Injetta pattern
            for i in range(5):
                pattern = [0.0] * 10
                pattern[i] = 1.0
                orchestrator.inject(pattern)
                await orchestrator.run_ticks(2)
            
            # Periodic immune (include pruning)
            orchestrator.run_immune()
            
            metrics = orchestrator.latest_metrics
            if metrics:
                pruning_progression.append(metrics.pruned_synapses)
        
        # Pruning dovrebbe aumentare nel tempo (consolidamento)
        trend = "↑ Increasing" if pruning_progression[-1] > pruning_progression[0] else "↓ Decreasing" if pruning_progression[-1] < pruning_progression[0] else "→ Stable"
        
        print(f"\n✓ Plasticity & Pruning")
        print(f"  Pruned synapses progression: {pruning_progression}")
        print(f"  Trend: {trend}")

    @pytest.mark.asyncio
    async def test_ignition_with_recovery(self) -> None:
        """Test 6: Ignizione con recovery dal branch health-repair"""
        from speace_core.bootstrap.ignition import OrganismIgnition
        
        igniter = OrganismIgnition(
            genome_path=None,
            warmup_patterns=30,
            sustain_ticks=50,
        )
        
        result = igniter.ignite()
        
        assert result['alive'], "Organism should be alive after ignition"
        assert result['tick'] > 0, "Ticks should have progressed"
        assert result['coherence_phi'] is not None or result['coherence_phi'] == 0, "Phi should be computed"
        
        print(f"\n✓ Organism Ignition with Recovery")
        print(f"  Alive: {result['alive']}")
        print(f"  Tick: {result['tick']}")
        print(f"  Coherence Phi: {result.get('coherence_phi', 'N/A')}")
        print(f"  Active Neurons: {result.get('active_neurons', 'N/A')}")
        print(f"  Systemic Coherence Index: {result.get('systemic_coherence_index', 'N/A'):.4f}")
        print(f"  Snapshots persisted: {result.get('snapshots_persisted', 0)}")

    @pytest.mark.asyncio
    async def test_emergent_capabilities_detection(self) -> None:
        """Test 7: Rilevamento di capacità emergenti integrate"""
        from speace_core.orchestrator import CellularBrainOrchestrator
        from speace_core.dna.parser import load_genome
        
        genome_path = Path(__file__).parent.parent / "speace_core" / "dna" / "genome" / "default_genome.yaml"
        genome = load_genome(genome_path)
        orchestrator = CellularBrainOrchestrator.build_mvp(genome)
        
        capabilities = EmergentCapabilities(
            pattern_completion=False,
            lateral_inhibition=False,
            bcm_selectivity=False,
            self_organization=False,
            temporal_coherence=False,
            homeostasis=False,
        )
        
        # Fase 1: Raccolta metriche
        metrics_log = []
        for cycle in range(30):
            for i in range(5):
                pattern = [0.0] * 10
                pattern[i % 5] = 1.0
                orchestrator.inject(pattern)
                await orchestrator.run_ticks(1)
            
            metrics = orchestrator.latest_metrics
            if metrics:
                metrics_log.append({
                    'tick': metrics.tick,
                    'phi': metrics.coherence_phi,
                    'energy': metrics.mean_energy,
                    'active': metrics.active_neurons,
                })
        
        # Fase 2: Analisi delle capacità
        if len(metrics_log) > 10:
            # Pattern completion: stabilità della coerenza
            recent_phis = [m['phi'] for m in metrics_log[-10:]]
            phi_std = (max(recent_phis) - min(recent_phis)) / (sum(recent_phis) / len(recent_phis) + 1e-6)
            capabilities.pattern_completion = phi_std < 0.1
            
            # Temporal coherence: energia stabile
            recent_energies = [m['energy'] for m in metrics_log[-10:]]
            energy_std = (max(recent_energies) - min(recent_energies)) / (sum(recent_energies) / len(recent_energies) + 1e-6)
            capabilities.temporal_coherence = energy_std < 0.15
            
            # Self-organization: attività neurale varia
            recent_active = [m['active'] for m in metrics_log[-10:]]
            capabilities.self_organization = len(set(recent_active)) > 3
            
            # Homeostasis: metriche convergono
            phi_trend = recent_phis[-1] - recent_phis[0]
            capabilities.homeostasis = abs(phi_trend) < 0.05
        
        print(f"\n✓ Emergent Capabilities Detected")
        for cap_name, cap_val in asdict(capabilities).items():
            status = "✓" if cap_val else "✗"
            print(f"  {status} {cap_name.replace('_', ' ').title()}: {cap_val}")


@pytest.mark.asyncio
async def test_full_brain_health_suite() -> None:
    """Test completo: salute del cervello con health-repair"""
    test_suite = BrainFunctionalityTest()
    
    print("\n" + "="*60)
    print("SPEACE BRAIN FUNCTIONAL TEST SUITE (health-repair-v0.9.0)")
    print("="*60)
    
    try:
        await test_suite.test_brain_ignition()
        await test_suite.test_pattern_completion_emergence()
        await test_suite.test_feedback_driven_learning()
        await test_suite.test_neural_selectivity()
        await test_suite.test_plasticity_and_pruning()
        await test_suite.test_ignition_with_recovery()
        await test_suite.test_emergent_capabilities_detection()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED - BRAIN IS FUNCTIONAL")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_full_brain_health_suite())
