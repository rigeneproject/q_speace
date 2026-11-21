"""BCEL catalog — quantum equivalences (task T15).

Implements the Biological-Cybernetic Equivalence gate for Q-SPEACE:
each biological/quantum concept is classified as *accidental* (limit of
carbon chemistry, removed in silicon) or *functional* (emergent
stabilizer, kept as a mathematical rule). Mirrors cellular speace's
``speace_core/bcel/`` catalogue.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BCELEquivalence:
    concept: str
    classification: str  # "accidental" | "functional"
    digital_rule: str


_QUANTUM_EQUIVALENCES: list[BCELEquivalence] = [
    BCELEquivalence(
        "Remote MCP bounded advisory service (T225)",
        "functional",
        "Keep as classical authenticated message passing, per-principal admission, "
        "isolated sessions, and bounded numeric work. No actuation, self-minting "
        "budget, consciousness, or quantum communication. Bridge activation "
        "requires the configured independent attestation verifier.",
    ),
    BCELEquivalence(
        "Client homeostatic scheduling experiment (T224)",
        "functional",
        "Keep as explicit feedback from prior error/ambiguity counters to "
        "bounded sleep, independent pre-action reservations, and local DAT "
        "receipts. Tokens/DAT and cost operations are synthetic benchmark "
        "units, not cognition, measured physical energy, or economic authority. "
        "Compare false stops and completions against an ungated baseline.",
    ),
    BCELEquivalence(
        "MCP homeostatic primitive adapter (T223)",
        "functional",
        "Keep as classical JSON-RPC transport for clock proxies, estimated costs "
        "and read-only equivalence queries. DAT is process-local simulated "
        "accounting; scheduling, hard external budgets, and independent release "
        "approval remain client responsibilities. No consciousness, quantum "
        "communication, physical energy guarantee, or actuation is implied.",
    ),
    BCELEquivalence(
        "Entanglement (cell/planet communication)",
        "accidental",
        "Replaced by explicit message-passing; entanglement is a computational "
        "binding resource only (no-communication theorem).",
    ),
    BCELEquivalence(
        "Superposition (parallel hypotheses)",
        "functional",
        "Keep: represent multiple candidate states as amplitude weights; "
        "measurement = decision/collapse.",
    ),
    BCELEquivalence(
        "Biological fractal shape",
        "accidental",
        "Removed: 2D/3D fractal morphology is carbon-specific.",
    ),
    BCELEquivalence(
        "Fractal scaling rule (w_ij ~ d^-1.8)",
        "functional",
        "Keep as a recursive, scale-free weight update law in FractalQCA.",
    ),
    BCELEquivalence(
        "Cosmic Virus perturbation",
        "functional",
        "Keep as stochastic-resonance optimizer (CV dynamics).",
    ),
    BCELEquivalence(
        "ILF coherence / entropic gravity",
        "functional",
        "Keep as coherence_phi metric and adaptive clock r(t)=10/sqrt(S_info).",
    ),
    BCELEquivalence(
        "Radio wavefront as biological tissue",
        "accidental",
        "Replaced by wavefront_modulator: EM field is an engineered information "
        "carrier, not a living tissue.",
    ),
    BCELEquivalence(
        "Metasurface as artificial skin",
        "functional",
        "Keep as programmable beamforming / interference-pattern controller "
        "(MetasurfaceController).",
    ),
    BCELEquivalence(
        "SDR as artificial cochlea / vocal cords",
        "functional",
        "Keep as software-defined transceiver (SDRFrontend) — the functional "
        "equivalent of sense/transmit in the EM domain.",
    ),
    BCELEquivalence(
        "Cognitive radio as neural adaptation",
        "functional",
        "Keep as SpectrumSensor + adaptive frequency hopping based on "
        "environment MAP — a mathematical optimisation, not cognition.",
    ),
    BCELEquivalence(
        "Regulatory compliance as immune system",
        "functional",
        "Keep as ComplianceFilter / RadioEmulator — a hard gate that rejects "
        "non-compliant transmissions before they reach the antenna.",
    ),
    BCELEquivalence(
        "Biological confidence / introspection",
        "accidental",
        "Removed: no subjective uncertainty or consciousness claim is made.",
    ),
    BCELEquivalence(
        "Calibrated predictive confidence",
        "functional",
        "Keep as Brier-score and expected-calibration-error evaluation against "
        "labelled outcomes; it is a measurable forecast, not metacognition.",
    ),
    BCELEquivalence(
        "Conversation as cognitive agency",
        "accidental",
        "Removed: generated text is untrusted; only Sevo/coherence-gated "
        "belief updates may influence the organism.",
    ),
    BCELEquivalence(
        "Sacred or natural hexagon geometry",
        "accidental",
        "Removed: no physical, social, or computational property follows from "
        "a sacred-geometry analogy.",
    ),
    BCELEquivalence(
        "Six-node redundant cluster",
        "functional",
        "Keep as a fixed-cardinality, classical redundancy window with six "
        "unique node identifiers; it has no biological interpretation.",
    ),
    BCELEquivalence(
        "Systemic resonance",
        "functional",
        "Keep as a deterministic pairwise-affinity score penalized by entropy; "
        "it is an observability metric, not a conscious state.",
    ),
    BCELEquivalence(
        "Homeostasis",
        "functional",
        "Keep as thresholded feedback over measurable load, entropy, and "
        "tension; it never authorizes physical action.",
    ),
    BCELEquivalence(
        "Organism, soul, or consciousness in Paradigm 6.0",
        "accidental",
        "Removed: these are documentation metaphors and must not be represented "
        "as properties of software, models, or networks.",
    ),
    # --- T202: pseudo-spiking layer (BICLab/SpikingBrain-7B,
    #     arXiv:2509.05276, dynamic_spikes, SpikePlasticity, correlation)
    BCELEquivalence(
        "Spike firing (biological action potential)",
        "accidental",
        "Removed; only the integer-quantization rule "
        "vth = mean(|x|)/k survives as the dynamic_spikes() primitive. "
        "No claim of true neuromorphic firing on silicon.",
    ),
    BCELEquivalence(
        "Spike-timing correlation → entanglement fidelity",
        "functional",
        "Keep as classical software-binding metric: Pearson correlation of "
        "spike trains (rows = neurons) feeds the EntanglementRegistry as a "
        "fidelity-proxy. This is NOT a quantum-state fidelity measurement: "
        "the registry stores a label and a scalar, never fabricates an "
        "entangled state. The no-communication theorem is preserved by "
        "construction (no physical channel is implied by the binding).",
    ),
    BCELEquivalence(
        "Event-driven neural energy",
        "functional",
        "Keep as E = E_base + N_spike · W_PER_SPIKE in the cost model; "
        "sparse activity lowers the cognitive cost passed to the Sevo gate.",
    ),
    BCELEquivalence(
        "Frequency-based plasticity (STDP-like)",
        "functional",
        "Keep as exponential-moving-average decay rule "
        "ema_i = decay·ema_i + (1-decay)·rate_i, coefficients normalized "
        "to [0, 1]. No online backpropagation, no spike-timing-dependent "
        "weight update.",
    ),
    BCELEquivalence(
        "ILF-modulated spiking threshold",
        "functional",
        "Keep as vth = mean(|x|) / (k · (1 + β·coherence_phi)); the ILF "
        "field attenuates the dynamic-spike threshold as a metacognitive "
        "modulator, not a biological mechanism.",
    ),
    # --- T205: SpikingBrain satellite — language-model binding layer
    BCELEquivalence(
        "MoBA top-k sparse softmax attention",
        "functional",
        "Keep as the top-k softmax routing pattern over chunks "
        "(moba_chunk_size, moba_topk). The biological metaphor of "
        "selective attention is kept as a mathematical sparsity rule, not "
        "as a mechanism of cortical attention.",
    ),
    BCELEquivalence(
        "GLA / linear attention recurrence",
        "functional",
        "Keep as the gated-linear-attention recurrence (gla / gdn with "
        "SSE sparse state expansion). The RNN-like memory is a "
        "mathematical primitive for long-context efficiency, not a "
        "biologically grounded working-memory model.",
    ),
    BCELEquivalence(
        "DSSA dual-path activation coding (SpB2.0)",
        "functional",
        "Keep as the FP8/int8 dual-path computation pattern: high "
        "confidence responses may use the FP8 path, low confidence may "
        "fall back to the INT8-spike path. This is a computational "
        "metacognition signal, not a biological one. Note: the actual "
        "checkpoint is not publicly available as of August 2026; the "
        "StubSpikingBrainV2 backend only mimics the flatter belief "
        "distribution and faster plasticity decay, it does not run the "
        "real dual-path kernel.",
    ),
    BCELEquivalence(
        "Brain area as cognitive subdivision",
        "functional",
        "Keep the SpikingBrainCortex as one cognitive area (think / "
        "reason / verbalize / metacognize), with the ILF + Sevo + cost "
        "gate as the thalamic-style mediator. The biological metaphor of "
        "cortical specialization is preserved as a software binding "
        "topology; no claim of neurological correspondence is made.",
    ),
    BCELEquivalence(
        "SpikingBrain-7B / SpB2.0 model identity",
        "accidental",
        "Removed: the model identity (BICLab/SpikingBrain-7B base, "
        "SpB2.0-5B base/instruct/think, etc.) is a software artefact of "
        "the HuggingFace/ModelScope ecosystem. SPEACE uses the "
        "mathematical primitives (dynamic_spikes, MoBA, GLA, DSSA) and "
        "does not depend on running the original model. On the RTX 3060 "
        "Laptop 6 GB the original 7B cannot run with usable quality; "
        "Qwen2.5-3B-Instruct (NF4) is the operative backend, sharing "
        "only the HTTP /think contract.",
    ),
    # ----- q_speace_economy primitives (T6.*) -----
    BCELEquivalence(
        "J_c 5-tuple (T6.5 cognitive measurement)",
        "accidental",
        "Removed: the 'joule-consciousness 5-tuple' analogy is biological "
        "metaphor over a structured measurement tuple. The math "
        "(J, delta_S, delta_I_c, R_b, delta_C) survives as 5 "
        "independently measurable physical quantities; the "
        "'metabolic intentionality' framing does not.",
    ),
    BCELEquivalence(
        "Coherence gain in N-agent simulation (T6.7)",
        "functional",
        "Keep: 'coherence gain' is the measured increase in the agent's "
        "CME minimum axis or VTEC objective under the SPEACE policy, "
        "compared to a scalar-monetary baseline. It is a metric, not a "
        "conscious-state assertion.",
    ),
    BCELEquivalence(
        "DAT bound destination (T6.11 routing key)",
        "functional",
        "Keep: the DAT 'bound_to' field is a routing key that scopes "
        "where a token may be spent (e.g. 'positive-exergy-processes'). "
        "It is a routing rule, not an identity claim or a value system.",
    ),
    # --- T-SPB-3-B: declarative event router ---
    BCELEquivalence(
        "Cognitive area dispatch (language/quantum/spiking/native)",
        "functional",
        "Keep as the EventRouter in q_speace.routing: a pure, declarative "
        "first-match dispatcher that routes text_input → SpikingBrainCortex "
        "(language area), quantum_state/spike_train → native primitives, "
        "everything else → native orchestrator tick. The LLM is consulted "
        "only for events with non-empty text, not for every stimulus — "
        "this preserves the BCEL rule that 'generated text is untrusted; "
        "only Sevo/coherence-gated belief updates may influence the "
        "organism'.",
    ),
    BCELEquivalence(
        "Proof of Coherence admission (T6.22)",
        "functional",
        "Keep: admission control is a mechanical inequality on a 12-dim "
        "CME vector plus a cardinality check on the reference set. It "
        "is not a self-certification of identity, nor a moral judgement.",
    ),
    # ----- Bridge-v0 (T218) -----
    BCELEquivalence(
        "Bridge update state machine (T218)",
        "functional",
        "Keep as a deterministic finite automaton over signed records "
        "(journal, idempotency, fencing, two-phase coupled commit). "
        "'Fencing' is a monotonic epoch counter, not a biological "
        "immune metaphor.",
    ),
    BCELEquivalence(
        "Admissible-set screening as homeostasis (T218)",
        "accidental",
        "Removed: the projection onto P ∩ B_Delta(p^k) is convex "
        "geometry, not homeostasis. The homeostatic framing is dropped; "
        "the set-intersection projection and the deterministic "
        "lexicographic tie-break survive as mathematical rules.",
    ),
    BCELEquivalence(
        "Independent validation as conscience (T218)",
        "accidental",
        "Removed: HMAC attestations plus a bounded evaluation budget "
        "are cryptographic and resource rules. 'Independent "
        "validation' is an architectural separation of trust domains, "
        "not a moral or cognitive faculty.",
    ),
    BCELEquivalence(
        "Reachable-tube safety as proprioception (T218)",
        "accidental",
        "Removed: interval propagation over the observation-delay tube "
        "is a conservative numerical over-approximation; the UNKNOWN "
        "verdict is a first-class outcome. No bodily metaphor is "
        "load-bearing.",
    ),
    BCELEquivalence(
        "Recoverability guards as healing (T218)",
        "accidental",
        "Removed: software restore / controller transition / plant "
        "recovery are three declared operating procedures with "
        "hysteresis and integrator-reset guards. Not wound healing.",
    ),
    BCELEquivalence(
        "Reporting score as ethical judgement (T218)",
        "accidental",
        "Removed: U = Σαb − Σβh is a linear form with frozen, published "
        "coefficients — a reporting index with monotonicity at fixed "
        "coordinates and no multiplicative cancellation. It measures "
        "nothing ethical and settles no trade-off.",
    ),
    BCELEquivalence(
        "Causal certificate as wealth oracle (T218)",
        "accidental",
        "Removed: the lower bound V^ - e_total certifies a declared "
        "in-horizon target under a decomposed error budget; effects "
        "beyond the horizon are reported unresolved. It is not a "
        "currency, a wealth measure or a legitimacy proof.",
    ),
    # --- T222: NCM coarse-to-fine codec (Phase 0, codec only) ---
    BCELEquivalence(
        "Coarse-to-fine generation as cognition (T222)",
        "accidental",
        "Removed: coarse-to-fine is an ordering of granularity, not a "
        "mental process. No claim of concept formation, understanding, "
        "or general intelligence follows from level-wise reconstruction.",
    ),
    BCELEquivalence(
        "Multiscale residual quantization (T222)",
        "functional",
        "Keep as the digital rule x_k = x_{k-1} - decode(encode(x_{k-1})) "
        "with one codebook per level; it is a deterministic compression "
        "hierarchy, not a semantic model.",
    ),
    BCELEquivalence(
        "Learned discrete concept code (T222)",
        "functional",
        "Keep, with limits: a code is a learned discrete index that may "
        "preserve global structure. It is not an idea, a human concept, "
        "or evidence of comprehension.",
    ),
    BCELEquivalence(
        "Parallel level prediction as thought (T222)",
        "accidental",
        "Removed from Phase 0 and not claimed: the NCM generator, parallel "
        "code prediction, and NFE comparisons are future work, not an "
        "implemented cognitive faculty.",
    ),
]


class BCELCatalog:
    """Queryable catalog of quantum BCEL equivalences."""

    def __init__(self) -> None:
        self._entries: dict[str, BCELEquivalence] = {e.concept: e for e in _QUANTUM_EQUIVALENCES}

    def all(self) -> list[BCELEquivalence]:
        return list(self._entries.values())

    def get(self, concept: str) -> BCELEquivalence:
        if concept not in self._entries:
            raise KeyError(concept)
        return self._entries[concept]

    def is_functional(self, concept: str) -> bool:
        return self.get(concept).classification == "functional"

