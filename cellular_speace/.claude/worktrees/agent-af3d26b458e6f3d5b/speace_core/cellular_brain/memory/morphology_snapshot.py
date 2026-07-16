from typing import Any, Dict

from pydantic import BaseModel, Field


class MorphologySnapshot(BaseModel):
    snapshot_id: str
    timestamp: float = 0.0
    tick: int = 0
    neuron_count: int = 0
    synapse_count: int = 0
    active_synapse_count: int = 0
    pruned_synapse_count: int = 0
    average_weight: float = 0.0
    average_trust: float = 0.0
    average_energy: float = 0.0
    coherence_phi: float = 0.0
    myelinated_pathways: int = 0
    # T12 — burst metadata
    execution_mode: str = "global_tick"
    burst_id: int = 0
    fired_neurons: int = 0
    propagated_synapses: int = 0
    fire_queue_size: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
