import pytest

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.cellular_brain.memory.morphology_snapshot import MorphologySnapshot


@pytest.fixture
def memory(tmp_path):
    return MorphologicalMemory(storage_path=str(tmp_path / "morph"))


def test_create_event(memory):
    event = memory.create_event(
        MorphologyEventType.SYNAPSE_REINFORCED,
        source_id="a",
        target_id="b",
        metadata={"old_weight": 0.5, "new_weight": 0.6},
    )
    assert event.event_type == MorphologyEventType.SYNAPSE_REINFORCED
    assert event.source_id == "a"
    assert len(memory.events) == 1


def test_record_snapshot(memory):
    snap = MorphologySnapshot(snapshot_id="s1", tick=1, coherence_phi=0.8)
    memory.record_snapshot(snap)
    assert len(memory.snapshots) == 1
    assert memory.latest_phi() == 0.8


def test_phi_trend(memory):
    memory.record_snapshot(MorphologySnapshot(snapshot_id="s1", tick=1, coherence_phi=0.5))
    memory.record_snapshot(MorphologySnapshot(snapshot_id="s2", tick=2, coherence_phi=0.7))
    assert memory.phi_trend() == pytest.approx(0.2)


def test_count_events(memory):
    memory.create_event(MorphologyEventType.SYNAPSE_REINFORCED)
    memory.create_event(MorphologyEventType.SYNAPSE_REINFORCED)
    memory.create_event(MorphologyEventType.SYNAPSE_PRUNED)
    assert memory.count_events(MorphologyEventType.SYNAPSE_REINFORCED) == 2
    assert memory.count_events(MorphologyEventType.SYNAPSE_PRUNED) == 1


def test_save_and_load(memory):
    memory.create_event(MorphologyEventType.SYNAPSE_REINFORCED, source_id="a")
    memory.record_snapshot(MorphologySnapshot(snapshot_id="s1", tick=1, coherence_phi=0.6))
    memory.save()

    new_mem = MorphologicalMemory(storage_path=memory.storage_path)
    new_mem.load()
    assert len(new_mem.events) == 1
    assert new_mem.events[0].source_id == "a"
    assert len(new_mem.snapshots) == 1
    assert new_mem.latest_phi() == 0.6


def test_load_missing_files(memory):
    # should not raise
    memory.load()
    assert memory.events == []
    assert memory.snapshots == []
