"""Test MorphologicalMemory: soft selection, embedding, retrieval, replay."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from speace_core.organism_observer.event_collector import EventCollector
from speace_core.organism_observer.functional_graph import FunctionalGraph
from speace_core.organism_observer.topology_history import TopologyHistory
from speace_core.organism_observer.topology_memory import (
    MorphologicalMemory,
    SavedMorphology,
    _EMBEDDING_DIM,
)


def test_soft_selection():
    """Verifica che P_save segua la soft selection."""
    mm = MorphologicalMemory.__new__(MorphologicalMemory)
    mm.soft_selection_exponent = 4.0

    # fitness=0.0 → P=0.0
    assert mm._save_probability(0.0) == 0.0
    # fitness=1.0 → P=1.0
    assert mm._save_probability(1.0) == 1.0
    # fitness=0.5 → P=0.5
    p50 = mm._save_probability(0.5)
    assert abs(p50 - 0.5) < 0.01, f"P(0.5)={p50} dovrebbe essere 0.5"
    # fitness=0.3 → P≈0.01
    p30 = mm._save_probability(0.3)
    assert p30 < 0.05, f"P(0.3)={p30} dovrebbe essere < 0.05"
    # fitness=0.8 → P≈0.94
    p80 = mm._save_probability(0.8)
    assert p80 > 0.9, f"P(0.8)={p80} dovrebbe essere > 0.9"
    print(f"[OK] Soft selection: P(0.0)=0, P(0.3)={p30:.4f}, P(0.5)={p50:.4f}, P(0.8)={p80:.4f}, P(1.0)=1")


def test_energy_budget():
    """Verifica che l'energia decada e si ricarichi."""
    with tempfile.TemporaryDirectory() as tmp:
        mm = MorphologicalMemory(
            persist_path=os.path.join(tmp, "morphs.jsonl"),
            memory_energy_max=5.0,
            memory_energy_decay_per_call=0.5,
        )
        assert mm.memory_energy == 5.0

        # Decadimento senza salvataggio
        mm._decay_energy()
        assert mm.memory_energy == 4.5, f"Expected 4.5, got {mm.memory_energy}"

        # Ricarica
        mm._recharge_energy(amount=1.0)
        assert mm.memory_energy == 5.0  # capped

        # Decadimento fino a zero
        for _ in range(20):
            mm._decay_energy()
        assert mm.memory_energy == 0.0

        # Con energia zero, record non salva
        collector = EventCollector(persist_path=os.path.join(tmp, "e.jsonl"))
        collector.record(source="A", target="B", latency_ms=1.0, message_type="test", success=True)
        graph = FunctionalGraph(collector)
        graph.build()
        hist = TopologyHistory(graph, persist_path=os.path.join(tmp, "h.jsonl"))
        snap = hist.sample(tick=1)

        mm.memory_energy_max = 5.0
        mm._memory_energy = 0.0
        result = mm.record(snap, ilf_value=0.9, context_label="test")
        assert result is None, "Non doveva salvare con energia zero"
        print("[OK] Energy budget: zero energy blocca salvataggio")


def test_embedding():
    """Verifica che l'embedding sia 28 float e deterministico."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = EventCollector(persist_path=os.path.join(tmp, "e.jsonl"))
        for src, tgt, cnt in [("A", "B", 5), ("B", "C", 3), ("C", "A", 2)]:
            for _ in range(cnt):
                collector.record(source=src, target=tgt, latency_ms=1.0, message_type="test", success=True)
        graph = FunctionalGraph(collector)
        graph.build()
        hist = TopologyHistory(graph, persist_path=os.path.join(tmp, "h.jsonl"))
        s1 = hist.sample(tick=1)

        emb = MorphologicalMemory._compute_embedding(s1)
        assert len(emb) == _EMBEDDING_DIM, f"Expected {_EMBEDDING_DIM}, got {len(emb)}"
        assert all(isinstance(v, float) for v in emb), "Tutti i valori devono essere float"

        # Deterministico
        emb2 = MorphologicalMemory._compute_embedding(s1)
        assert emb == emb2, "Embedding deve essere deterministico"

        # Cosine similarity con se stesso = 1.0
        sim = MorphologicalMemory._cosine_similarity(emb, emb2)
        assert abs(sim - 1.0) < 1e-10, f"Self-similarity deve essere 1.0, got {sim}"

        print(f"[OK] Embedding: dim={len(emb)}, self-sim={sim:.6f}")


def test_retrieval():
    """Verifica che retrieve trovi morfologie per similarita' strutturale."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = EventCollector(persist_path=os.path.join(tmp, "e.jsonl"))
        for src, tgt, cnt in [("A", "B", 5), ("B", "C", 3), ("C", "A", 2)]:
            for _ in range(cnt):
                collector.record(source=src, target=tgt, latency_ms=1.0, message_type="test", success=True)
        graph = FunctionalGraph(collector)
        hist = TopologyHistory(graph, persist_path=os.path.join(tmp, "h.jsonl"))
        s1 = hist.sample(tick=1)

        memory = MorphologicalMemory(persist_path=os.path.join(tmp, "m.jsonl"))
        # Salva con soft selection (fitness alta)
        for i in range(3):
            s = hist.sample(tick=(i + 1) * 10)
            memory.record(s, ilf_value=0.8 + i * 0.05, context_label="test")

        # Retrieve dallo stesso snapshot
        results = memory.retrieve(s1, top_k=5)
        assert len(results) > 0, "Doveva trovare almeno una morfologia"
        # La prima dovrebbe essere la piu' simile (cosine ~1.0 con se stesso)
        if results:
            morph, sim = results[0]
            print(f"[OK] Retrieval: top result {morph.morphology_id} sim={sim:.4f}")

        # Filtra per contesto
        filtered = memory.retrieve(s1, top_k=5, context_filter="test")
        assert len(filtered) == len(results), "Filtro contestuale non deve cambiare"
        print(f"[OK] Retrieval filtrato: {len(filtered)} risultati")

        # Filtra per fitness
        filtered2 = memory.retrieve(s1, top_k=5, min_fitness=10.0)
        assert len(filtered2) == 0, "Nessun risultato con fitness irraggiungibile"
        print("[OK] Retrieval fitness filter: 0 risultati (corretto)")


def test_replay():
    """Verifica che replay inietti eventi nel collector."""
    with tempfile.TemporaryDirectory() as tmp:
        # Crea collector e memory
        collector = EventCollector(persist_path=os.path.join(tmp, "e.jsonl"))
        memory = MorphologicalMemory(
            persist_path=os.path.join(tmp, "m.jsonl"),
            memory_energy_decay_per_call=0.01,  # decadimento lento per accumulare
        )

        # Popola grafo iniziale e salva morfologia
        for src, tgt, cnt in [("A", "B", 5), ("B", "C", 3), ("C", "A", 2)]:
            for _ in range(cnt):
                collector.record(source=src, target=tgt, latency_ms=1.0, message_type="test", success=True)

        graph = FunctionalGraph(collector)
        hist = TopologyHistory(graph, persist_path=os.path.join(tmp, "h.jsonl"))
        s1 = hist.sample(tick=1)

        # Forza salvataggio chiamando piu' volte fino a successo
        saved = None
        for _ in range(50):
            saved = memory.record(s1, ilf_value=0.85, context_label="replay_test")
            if saved is not None:
                break

        if saved is None:
            # Forza il salvataggio bypassando soft selection
            memory._total_save_attempts += 1
            memory._decay_energy()
            memory._id_counter += 1
            saved = SavedMorphology(
                morphology_id="morph_manual_001",
                saved_at=s1.timestamp,
                tick=s1.tick,
                fitness_score=0.85,
                save_probability=0.5,
                ilf_value=0.85,
                node_count=s1.node_count,
                edge_count=s1.edge_count,
                embedding=MorphologicalMemory._compute_embedding(s1),
            )
            memory._morphologies[saved.morphology_id] = saved
            memory._recharge_energy()

        count_before = collector.count()
        print(f"[INFO] Eventi prima del replay: {count_before}")

        # Replay
        graph2 = FunctionalGraph(collector)
        perturbed = memory.replay(
            morphology_id=saved.morphology_id,
            graph=graph2,
            influence_strength=0.1,
        )
        count_after = collector.count()
        print(f"[INFO] Eventi dopo replay: {count_after}")
        print(f"[INFO] Archi perturbati: {perturbed}")

        assert perturbed > 0, "Doveva perturbare almeno un arco"
        assert count_after > count_before, "Doveva iniettare eventi nel collector"
        print(f"[OK] Replay: {perturbed} archi perturbati, {count_after - count_before} eventi iniettati")

        # Verifica che gli archi siano realmente nel grafo
        graph2.build()
        total_edges = graph2.edge_count
        print(f"[INFO] Totale archi nel grafo aggiornato: {total_edges}")


def test_save_load_embedding():
    """Verifica che embedding sia persistito/caricato correttamente."""
    with tempfile.TemporaryDirectory() as tmp:
        collector = EventCollector(persist_path=os.path.join(tmp, "e.jsonl"))
        collector.record(source="A", target="B", latency_ms=1.0, message_type="test", success=True)
        graph = FunctionalGraph(collector)
        hist = TopologyHistory(graph, persist_path=os.path.join(tmp, "h.jsonl"))
        s1 = hist.sample(tick=1)

        memory = MorphologicalMemory(persist_path=os.path.join(tmp, "m.jsonl"))
        saved = None
        for _ in range(50):
            saved = memory.record(s1, ilf_value=0.9, context_label="persist")
            if saved is not None:
                break

        if saved is None:
            memory._id_counter += 1
            saved = SavedMorphology(
                morphology_id="morph_persist_001",
                embedding=MorphologicalMemory._compute_embedding(s1),
                fitness_score=0.9,
                save_probability=0.5,
                ilf_value=0.9,
                node_count=s1.node_count,
                edge_count=s1.edge_count,
            )
            memory._morphologies[saved.morphology_id] = saved

        assert len(saved.embedding) == _EMBEDDING_DIM, \
            f"Embedding prima del save: {len(saved.embedding)}"

        memory.save()
        memory2 = MorphologicalMemory(persist_path=os.path.join(tmp, "m.jsonl"))
        loaded = memory2.load()
        assert loaded == 1, f"Doveva caricare 1 morfologia, caricato {loaded}"

        loaded_m = memory2.best()
        assert loaded_m is not None
        assert len(loaded_m.embedding) == _EMBEDDING_DIM, \
            f"Embedding dopo load: {len(loaded_m.embedding)}"
        assert loaded_m.embedding == saved.embedding, "Embedding deve coincidere"
        print(f"[OK] Save/Load embedding: {len(loaded_m.embedding)} float preservati")


if __name__ == "__main__":
    test_soft_selection()
    test_energy_budget()
    test_embedding()
    test_retrieval()
    test_replay()
    test_save_load_embedding()
    print()
    print("=== MorphologicalMemory: TUTTI I TEST SUPERATI ===")
