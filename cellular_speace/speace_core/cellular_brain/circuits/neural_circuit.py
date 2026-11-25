import random
from typing import List

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from speace_core.cellular_brain.base.digital_signal import DigitalSignal
from speace_core.cellular_brain.cells.digital_astrocyte import DigitalAstrocyte
from speace_core.cellular_brain.cells.digital_microglia import DigitalMicroglia
from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_oligodendrocyte import DigitalOligodendrocyte
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.cellular_brain.dynamics.stdp_engine import STDPEngine
from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class NeuralCircuit(BaseModel):
    circuit_id: str
    input_neurons: List[DigitalNeuron] = []
    hidden_neurons: List[DigitalNeuron] = []
    output_neurons: List[DigitalNeuron] = []
    synapses: List[DigitalSynapse] = []
    astrocytes: List[DigitalAstrocyte] = []
    microglia: List[DigitalMicroglia] = []
    oligodendrocytes: List[DigitalOligodendrocyte] = []
    feedback_buffer: List[float] = []
    memory: MorphologicalMemory | None = None
    current_tick: int = 0
    stdp_enabled: bool = True
    stdp_engine: STDPEngine = Field(default_factory=STDPEngine)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _neuron_index: dict[str, DigitalNeuron] = PrivateAttr(default_factory=dict)
    _synapse_index: dict[tuple[str, str], DigitalSynapse] = PrivateAttr(default_factory=dict)
    _incoming_index: dict[str, list[DigitalSynapse]] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _sync_indexes(self):
        self._neuron_index.clear()
        for n in self.input_neurons + self.hidden_neurons + self.output_neurons:
            self._neuron_index[n.cell_id] = n
        self._synapse_index.clear()
        self._incoming_index.clear()
        for s in self.synapses:
            self._synapse_index[(s.source, s.target)] = s
            self._incoming_index.setdefault(s.target, []).append(s)
        return self

    def add_neuron(self, neuron: DigitalNeuron) -> None:
        self.hidden_neurons.append(neuron)
        self._neuron_index[neuron.cell_id] = neuron

    def remove_neuron(self, cell_id: str) -> None:
        neuron = self._neuron_index.pop(cell_id, None)
        if neuron is None:
            return
        if neuron in self.input_neurons:
            self.input_neurons.remove(neuron)
        elif neuron in self.hidden_neurons:
            self.hidden_neurons.remove(neuron)
        elif neuron in self.output_neurons:
            self.output_neurons.remove(neuron)

    def add_synapse(self, synapse: DigitalSynapse) -> None:
        self.synapses.append(synapse)
        self._synapse_index[(synapse.source, synapse.target)] = synapse
        self._incoming_index.setdefault(synapse.target, []).append(synapse)

    def remove_synapse(self, source: str, target: str) -> None:
        key = (source, target)
        synapse = self._synapse_index.pop(key, None)
        if synapse is not None:
            self.synapses.remove(synapse)
            incoming = self._incoming_index.get(target, [])
            if synapse in incoming:
                incoming.remove(synapse)

    def inject_input(self, pattern: List[float]) -> None:
        for neuron, strength in zip(self.input_neurons, pattern):
            neuron.activation += strength

    def reset_transient_state(self) -> None:
        """Clear transient per-trial activations and eligibility traces while preserving weights."""
        for n in self.input_neurons + self.hidden_neurons + self.output_neurons:
            n.activation = 0.0
            n.firing_trace = 0.0
            n.refractory_counter = 0
            n.snooze_counter = 0
        for syn in self.synapses:
            syn.pre_trace = 0.0
            syn.post_trace = 0.0
            syn.last_pre_spike_tick = None
            syn.last_post_spike_tick = None

    async def tick(self) -> List[DigitalSignal]:
        self.current_tick += 1
        all_neurons = self.input_neurons + self.hidden_neurons + self.output_neurons
        outbound: List[DigitalSignal] = []

        # Decay synaptic eligibility traces smoothly across ticks
        for syn in self.synapses:
            syn.pre_trace *= 0.70
            syn.post_trace *= 0.70
            if syn.pre_trace < 1e-4:
                syn.pre_trace = 0.0
            if syn.post_trace < 1e-4:
                syn.post_trace = 0.0

        # Astrocyte regulation
        for astro in self.astrocytes:
            astro.regulate(all_neurons)

        # Layer-ordered causal propagation: input -> hidden -> output
        for layer_idx, layer_neurons in enumerate(
            (self.input_neurons, self.hidden_neurons, self.output_neurons)
        ):
            layer_signals: List[DigitalSignal] = []
            for neuron in layer_neurons:
                pre_strength = neuron.activation
                will_fire = (
                    pre_strength >= neuron.threshold
                    and neuron.energy > 0.1
                    and neuron.snooze_counter == 0
                    and neuron.refractory_counter == 0
                )
                neuron_signals = await neuron.tick()
                if will_fire:
                    for syn in self._incoming_index.get(neuron.cell_id, []):
                        if syn.state != "pruned":
                            syn.last_post_spike_tick = self.current_tick
                            syn.post_trace = min(1.5, max(syn.post_trace, pre_strength))
                elif neuron.readout > 0.01:
                    for syn in self._incoming_index.get(neuron.cell_id, []):
                        if syn.state != "pruned":
                            syn.post_trace = max(syn.post_trace, neuron.readout)

                for sig in neuron_signals:
                    syn = self._find_synapse(sig.source, sig.target)
                    if syn and syn.state != "pruned":
                        syn.last_pre_spike_tick = self.current_tick
                        syn.pre_trace = min(1.5, max(syn.pre_trace, sig.strength))
                        transmitted = syn.transmit(sig)
                        outbound.append(transmitted)
                        layer_signals.append(transmitted)

            # Deliver signals immediately to downstream layers so causal feedforward paths
            # settle within the cognitive tick while recurrent/backward links take effect next tick.
            for sig in layer_signals:
                target = self._find_neuron(sig.target)
                if target is not None:
                    await target.receive(sig)
                    if layer_idx == 1 and target in self.output_neurons:
                        in_syn = self._find_synapse(sig.source, sig.target)
                        if in_syn is not None:
                            in_syn.post_trace = max(in_syn.post_trace, target.activation)

        return outbound

    def learn_supervised(self, target_vector: List[float], lr: float = 0.30) -> None:
        """Three-factor local error-modulated Hebbian/delta learning on active pre-synaptic traces."""
        readouts = self.readout_activations
        max_r = max(readouts) if readouts else 0.0
        denom = max(max_r, 0.35)
        norm_pred = [r / denom for r in readouts]

        for out_idx, out_neuron in enumerate(self.output_neurons):
            if out_idx >= len(target_vector):
                break
            tgt_val = float(target_vector[out_idx])
            pred_val = norm_pred[out_idx] if out_idx < len(norm_pred) else 0.0
            err = tgt_val - pred_val
            for syn in self._incoming_index.get(out_neuron.cell_id, []):
                if syn.state == "pruned" or syn.pre_trace <= 0.05:
                    continue
                delta = lr * err * min(1.0, syn.pre_trace)
                syn.weight = max(0.01, min(1.0, syn.weight + delta))
                if delta > 0:
                    syn.trust = max(0.1, min(1.0, syn.trust + 0.5 * delta))
                    syn.last_post_spike_tick = self.current_tick

        # Consume trial eligibility traces after supervised teacher credit assignment
        # so completed-trial stimuli do not bleed into subsequent independent trials.
        for syn in self.synapses:
            syn.pre_trace = 0.0
            syn.post_trace = 0.0

    def apply_feedback(self, score: float) -> None:
        event_type = (
            MorphologyEventType.SYNAPSE_REINFORCED
            if score > 0
            else MorphologyEventType.SYNAPSE_WEAKENED
        )
        has_traces = any(s.pre_trace > 0.01 for s in self.synapses if s.state != "pruned")
        for syn in self.synapses:
            if syn.state == "pruned":
                continue
            old_weight = syn.weight
            elig = (syn.pre_trace * max(syn.post_trace, 0.2)) if has_traces else 1.0
            if elig <= 1e-4:
                continue
            if score > 0:
                syn.reinforce(score * 0.15 * elig if has_traces else score * 0.02)
            else:
                syn.weaken(abs(score) * 0.15 * elig if has_traces else abs(score) * 0.02)
            if self.memory:
                self.memory.create_event(
                    event_type=event_type,
                    source_id=syn.source,
                    target_id=syn.target,
                    metadata={
                        "old_weight": old_weight,
                        "new_weight": syn.weight,
                        "feedback_score": score,
                    },
                )

        # STDP on recently active synapses, using feedback as neuromodulator (dopamine)
        if self.stdp_enabled and self.stdp_engine is not None:
            self.stdp_engine.apply_updates(self.synapses, dopamine=score, base_plasticity=1.0)
            for syn in self.synapses:
                syn.last_pre_spike_tick = None
                syn.last_post_spike_tick = None

        for neuron in self.hidden_neurons + self.output_neurons:
            neuron.adapt(score * 0.1 if has_traces else score)
        self.feedback_buffer.append(score)

    def run_immune(self) -> None:
        all_neurons = self.input_neurons + self.hidden_neurons + self.output_neurons
        for mg in self.microglia:
            pruned = mg.inspect(all_neurons, self.synapses)
            if self.memory:
                for syn_id in pruned:
                    self.memory.create_event(
                        event_type=MorphologyEventType.SYNAPSE_PRUNED,
                        metadata={"synapse_id": syn_id, "reason": "low_trust_low_usage"},
                    )

    def _find_synapse(self, source: str, target: str) -> DigitalSynapse | None:
        return self._synapse_index.get((source, target))

    def _find_neuron(self, cell_id: str) -> DigitalNeuron | None:
        return self._neuron_index.get(cell_id)

    @property
    def output_activations(self) -> List[float]:
        return [n.readout for n in self.output_neurons]

    @property
    def readout_activations(self) -> List[float]:
        return [n.readout for n in self.output_neurons]

    @property
    def all_neurons(self) -> List[DigitalNeuron]:
        return self.input_neurons + self.hidden_neurons + self.output_neurons
