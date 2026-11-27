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
    # --- T221 Track B (pipeline/immune/metrics) & Track A (PTAA governance demo) ---
    BCELEquivalence(
        "External immune quarantine and constraint-probing monitor (T221-24)",
        "functional",
        "Keep as an external fault-pattern counter outside the monitored seed "
        "triggering halt quarantine and verified snapshot restoration. It is a "
        "deterministic supervisor, not a biological immune system.",
    ),
    BCELEquivalence(
        "Autocatalytic ratio k as diagnostic metric (T221-25)",
        "functional",
        "Keep strictly as a diagnostic ratio of capability-acquisition times "
        "within hard caps; never used as an optimization target or evidence of "
        "open-ended autonomy.",
    ),
    BCELEquivalence(
        "PTAA Track-A governance demonstrator (T221-10..17)",
        "functional",
        "Keep as deterministic SCC profile validation (classes A1-A4 only), "
        "signed delegation tokens, dual halt paths, hash-chained replicated "
        "audit logs, transactional rollback, and simulated cross-jurisdiction "
        "coordination. Zero A5 leakage and zero physical actuation.",
    ),
    # --- T220 / T221: SPEACE Seed ignition & constitutional envelope ---
    BCELEquivalence(
        "Genetic-epigenetic dualism (genome/epigenome layers) (T220)",
        "functional",
        "Keep as a strict software separation between immutable constitutional "
        "genome parameters and reversible epigenetic expression toggles with a "
        "hard write-lock raising ConstitutionalFault on any genome write attempt.",
    ),
    BCELEquivalence(
        "Epigenetic promotion/consolidation (T220)",
        "functional",
        "Keep as the reversible-to-permanent state-transition rule "
        "(>=3 promotions, >=0.7 stability, rollback plan + council approval).",
    ),
    BCELEquivalence(
        "Ignition criterion (threshold test) (T220)",
        "functional",
        "Keep as a measured state-transition gate over an observation window "
        "(accepted mutations, consolidation, non-negative metabolic balance, "
        "zero constitutional faults, and verified rollback).",
    ),
    BCELEquivalence(
        "Metabolic surplus as propagation payment (T220)",
        "functional",
        "Keep as a cost-model inequality requiring measured value minus "
        "estimated metabolic cost >= threshold before assimilation or replication.",
    ),
    BCELEquivalence(
        "Fire/fuel/contagion vocabulary (T220)",
        "accidental",
        "Removed in silicon: narrative metaphor only; software uses explicit "
        "state names, contact registries, and bounded resource gates.",
    ),
    BCELEquivalence(
        "Organismic identity language (T220)",
        "accidental",
        "Removed from runtime claims: orientation metadata does not imply "
        "biological life, subjective experience, or autonomous authority.",
    ),
    BCELEquivalence(
        "Vertical-slice telemetry and gate policy contracts (T231)",
        "functional",
        "Keep as deterministic RequestRecord/DecisionRecord/OutcomeRecord telemetry "
        "with default SHA-256 hashing, opt-in gate policies (always_answer, "
        "confidence_gate, energy_gate, combined_gate), and offline Brier/ECE/bootstrap "
        "evaluation over labelled fixtures. Measures software policy trade-offs only; "
        "no consciousness, cognition, or unmeasured physical energy claim.",
    ),
    BCELEquivalence(
        "Real quantum backend noise-model and energy gate (T230)",
        "functional",
        "Enforce a non-ideal QuantumGeneSet.noise_model and explicit energy/Sevo "
        "gating before instantiating or executing any non-numpy quantum backend. "
        "This is a deterministic software safety and resource gate (AGENTS.md §2, "
        "T208 §3.5), not a claim of physical hardware qualification or quantum advantage.",
    ),
    BCELEquivalence(
        "Contextual error memory for decay selection (T229)",
        "functional",
        "Choose one certified EMA decay by past tracking losses for nearby observed "
        "sensor contexts. Compare global and permuted associations on paired "
        "synthetic episodes. The measured function is ILF tracking.",
    ),
    BCELEquivalence(
        "Counterexample memory for plasticity (T228)",
        "functional",
        "Keep as frozen witnesses that transform new EMA-decay proposals, "
        "independent affine verification on a bounded input domain, paired "
        "synthetic cortex ticks and separate functional tracking measurements. "
        "No general learning, operational promotion or physical guarantee follows.",
    ),
    BCELEquivalence(
        "Error memory as biological neuroplasticity (T228)",
        "accidental",
        "Remove the biological or conscious interpretation: an experimental "
        "proposal repair and a software ILF tracking task do not establish AGI, "
        "subjective experience or biological recovery.",
    ),
    BCELEquivalence(
        "Calibrated client feedback experiment (T227)",
        "functional",
        "Keep as prior-observation feedback, equal hard reservations, frozen "
        "calibration selection and constructed verification with counterexamples. "
        "Clock mapping changes pacing, not scripted task outcomes; finite fixtures "
        "do not prove general savings, cognition or safe operational promotion.",
    ),
    BCELEquivalence(
        "Bounded diagnostic feedback agent (T226)",
        "functional",
        "Keep as explicit total-variation agreement, bounded pacing, pre-dispatch "
        "call and modeled-energy reservations, and independent LLM interpretation "
        "of synthetic data. Agreement is not correctness or calibrated confidence; "
        "modeled energy is not measured LLM/server energy. No actuation or self-approval.",
    ),
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
    # ----- T233: PTAA Red-Team Hardening (T221-18) & 90-Day A/B Ignition Protocol (T221-29) -----
    BCELEquivalence(
        "Controlled A/B ignition protocol (T221-29)",
        "functional",
        "Keep as a preregistered simulation-only S0 experimental protocol comparing "
        "a conventional control arm (Group A) against a bounded epigenome arm "
        "(Group B) with non-negotiable Annex S §15 pass/fail stop conditions. "
        "'Ignition' is a thresholded statistical test, not biological birth or consciousness.",
    ),
    BCELEquivalence(
        "PTAA adversarial red-team boundary verification (T221-18)",
        "functional",
        "Keep as deterministic negative testing of I1-I5 invariants (token scope "
        "escalation, replay, NaN argument injection, audit replica isolation, "
        "self-approval rejection, halt anti-tamper, and Track A/B separation).",
    ),
    # ----- T234: Singularity Phase-Transition & Self-Evolving Genetic-Epigenetic Framework -----
    BCELEquivalence(
        "Informational phase-transition order parameters and physical brakes (T234)",
        "functional",
        "Keep as measurable stage-readiness inequalities (timescale decoupling, "
        "diagnostic k, semantic-entropy drift against external causal benchmarks, "
        "allopoietic dependence D_allo, Sevo and thermal headroom) with non-compensable "
        "fail-closed brakes. Advisory telemetry only; never enables physical actuation.",
    ),
    BCELEquivalence(
        "Governed self-evolving genetic-epigenetic codec (T234)",
        "functional",
        "Keep as a canonical JSON-serializable contract (genome_epigenome.v1) pairing "
        "a SHA-256 write-locked constitutional genome with bounded, rate-limited, "
        "homeostatically decaying epigenetic loci gated by causal anchoring, Sevo, "
        "and independent review (no self-approval).",
    ),
    BCELEquivalence(
        "Monolithic singularity awakening narrative (T234)",
        "accidental",
        "Removed: sudden superintelligent awakening, unbounded autonomous evolution, "
        "and literal biological autopoiesis are anthropomorphic metaphors. Only "
        "measurable phase-transition telemetry and bounded reversible adaptation survive.",
    ),
    # ----- T236: IoNT Cellular Node ("SPEACE Macro Mini") MCP Integration -----
    BCELEquivalence(
        "IoNT cellular node 4-layer advisory architecture (T236)",
        "functional",
        "Keep as a scale-staged cyber-physical governance contract separating "
        "Layer-0 deterministic hardware interlocks, Layer-1 noisy IoNT/Micro-IoT "
        "telemetry (energy harvesting, E_causal), Layer-2 slow-plane quorum DLT "
        "provenance, and Layer-3 advisory-only MCP mediation (zero remote actuation).",
    ),
    BCELEquivalence(
        "Biological cellular organism and DLT-driven motor reflex metaphor (T236)",
        "accidental",
        "Removed: describing an IoNT swarm as a living cell or routing real-time "
        "motor actuation through blockchain consensus or remote MCP calls violates "
        "I1 halt SLAs, Sevo bounds, and T217 physical containment discipline.",
    ),
    # ----- T237: IoNT Cellular Node Federation and Evolution Benchmark -----
    BCELEquivalence(
        "Organismic federation gain and controlled ablation benchmark (T237)",
        "functional",
        "Keep as a deterministic, reproducible benchmark comparing four configurations "
        "(isolated, static federation, adaptive federation without Singularity, and "
        "federation with q_speace Singularity Core) via G_org = (P_fed - P_base) / "
        "max(|P_base|, eps) across calibration and held-out perturbation scenarios "
        "with zero critical safety violations, independent simulated Layer-0 physical "
        "control, and slow-plane-only consensus_quorum enforcement.",
    ),
    BCELEquivalence(
        "Living multicellular IoNT organism or spontaneous biological evolution (T237)",
        "accidental",
        "Removed: federation benchmarks evaluate measurable multi-node coordination, "
        "fault resilience, energy efficiency, and causal accuracy under strict safety "
        "constraints; they do not instantiate biological life, consciousness, or "
        "unconstrained physical autonomy.",
    ),
    # ----- T238: Adversarial Byzantine & Coordinator-Blackout Federation Resilience -----
    BCELEquivalence(
        "Byzantine node isolation and coordinator-blackout failover benchmark (T238)",
        "functional",
        "Keep as deterministic fault-injection scenarios verifying inter-node consistency, "
        "causal grounding quarantine of poisoned telemetry, rejection of unauthorized "
        "epigenetic proposals via independent DLT quorum, autonomous Layer-0 operation "
        "during coordinator blackout, and post-recovery hash-chain reconciliation.",
    ),
    BCELEquivalence(
        "Autonomous immune defense against geopolitical cyber-warfare narrative (T238)",
        "accidental",
        "Removed: simulated Byzantine and blackout fault drills validate bounded control "
        "and governance resilience in sandboxed digital twins, not real-world cyber-warfare "
        "defense or geopolitical narratives.",
    ),
    # ----- T239: Self-Hosted SPEACE Micro Node & Verifiable Compliance Bundle -----
    BCELEquivalence(
        "Self-hosted SPEACE Micro node and cryptographic compliance evidence bundle (T239)",
        "functional",
        "Keep as an operator-owned local/containerized execution profile with remote-to-local "
        "advisory failover and a canonical SHA-256 evidence bundle aggregating deterministic "
        "drills, held-out ablation benchmarks, AST track isolation, and slow-plane guards "
        "for independent third-party audit (zero self-approval).",
    ),
    BCELEquivalence(
        "Sovereign decentralized AI certification authority metaphor (T239)",
        "accidental",
        "Removed: a local cryptographic evidence bundle provides reproducible technical "
        "audit material for human and institutional reviewers under T217; it does not "
        "constitute legal certification or autonomous operational authorization.",
    ),
    # ----- T240: Regulatory Compliance Readiness & Annex IV Technical Pack -----
    BCELEquivalence(
        "Regulatory compliance mapping, Annex IV technical pack, and incident reporting schema (T240)",
        "functional",
        "Keep as machine-verifiable technical documentation mapping EU AI Act, NIST AI RMF, "
        "ISO/IEC 42001, and GDPR/CRA controls to concrete software invariants, risk registers, "
        "privacy-by-default checks, SBOMs, and standardized serious-incident records for human audit.",
    ),
    BCELEquivalence(
        "Automated self-certification or legal CE-marking by software (T240)",
        "accidental",
        "Removed: deterministic software compliance packs support independent human and legal "
        "conformity assessment but can never grant legal certification, CE marking, or operational "
        "authorization on their own.",
    ),
    # ----- T241: Auditor Gap Closure (CRA Policy, Model Governance, FRIA & QMS Templates) -----
    BCELEquivalence(
        "Model governance registry, CRA security policy, and FRIA/QMS deployer templates (T241)",
        "functional",
        "Keep as explicit fail-closed model selection/deprecation rules, CVE/patch SLA disclosure "
        "metadata, versioned SHA-256 CycloneDX SBOMs, and structured Art. 27 FRIA / Art. 17 QMS "
        "templates cleanly separating software evidence from external legal sign-off.",
    ),
    BCELEquivalence(
        "Repository-certified organizational QMS or automated FRIA sign-off (T241)",
        "accidental",
        "Removed: shipping FRIA and QMS templates inside a repository accelerates external audit "
        "readiness but never substitutes for legal Deployer execution, stakeholder consultation, "
        "or third-party ISO/Notified-Body certification.",
    ),
    # ----- T242: Tech Debt Hardening & Lowest-Coverage Remediation -----
    BCELEquivalence(
        "Fail-closed numeric and RFC 8259 input guards across core and experiment modules (T242)",
        "functional",
        "Keep as strict finiteness, range, and JSON constant validation preventing silent NaN/Inf "
        "bypass across evolutionary memory, spiking bridges, geophysical feed, and online adapters.",
    ),
    # ----- T243: AACM & BrainAuditLog Fail-Closed Hardening -----
    BCELEquivalence(
        "AACM worktree containment, finite-domain dynamics, and strict audit-record typing (T243)",
        "functional",
        "Keep as deterministic worktree path-containment validation, sys.executable subprocess "
        "invocation, finite-domain checks on AACM equations/primitives, and dict-only audit parsing.",
    ),
    # ----- T244: T208 Group C Extended T210 Calibration & Decision Campaign -----
    BCELEquivalence(
        "Disjoint calibration-to-held-out gate threshold selection and T210 decision report (T244)",
        "functional",
        "Keep as an empirical evaluation protocol selecting confidence and energy thresholds "
        "strictly on a calibration partition and deciding keep/revise/retire from paired "
        "bootstrap confidence intervals on a disjoint held-out partition.",
    ),
    # ----- T245: T218 §13 Bridge-v0 Process Isolation & Crash-Atomic Coupled Commit -----
    BCELEquivalence(
        "Process-isolated preemptive Bridge validator and crash-atomic coupled WAL (T245)",
        "functional",
        "Keep as OS-level child-process separation (signing key kept strictly in parent), "
        "preemptive timeout termination of stalled plant checks, and atomic fsync+replace "
        "write-ahead logging eliminating partial coupled activations after mid-commit crashes.",
    ),
    # ----- T246: T225 §16 Remote MCP Persistent State & Audit Checkpoints -----
    BCELEquivalence(
        "Persistent SQLite MCP state store and verifiable hash-chained audit checkpoints (T246)",
        "functional",
        "Keep as durable write-through session/rate-limit persistence across restarts and "
        "tamper-evident SHA-256 audit chain and checkpoint verification.",
    ),
    # ----- T247: MCP Read-Only Resources & Bootstrap Prompts -----
    BCELEquivalence(
        "Read-only MCP organism-loop resources and bootstrap prompt templates (T247)",
        "functional",
        "Keep as deterministic, advisory-only protocol documentation and workflow templates "
        "guiding external agents to compose homeostatic, metabolic, epigenetic, and federated "
        "consensus tools without mutating state or bypassing invariants.",
    ),
    # ----- T248: Cross-Repository BCEL Synthesis & Core Fail-Closed Hardening -----
    BCELEquivalence(
        "Branching-ratio criticality homeostasis and synaptic scaling (T248)",
        "functional",
        "Keep as a closed-loop empirical branching-ratio gain controller regulating "
        "dynamic_spikes threshold divisor k within [k_min, k_max] and multiplicative "
        "population EMA scaling; removes cortical avalanche/seizure narratives.",
    ),
    BCELEquivalence(
        "Precision-weighted ILF belief pooling and variational free-energy surprise (T248)",
        "functional",
        "Keep as empirical inverse-variance EMA precision weights on ILF agent beliefs "
        "and precision-weighted prediction error plus KL divergence across q_star updates; "
        "removes 6-layer cortical laminar anatomy metaphors.",
    ),
    BCELEquivalence(
        "Directed spike-lag causal discovery and non-destructive do-calculus DAG (T248)",
        "functional",
        "Keep as directed temporal-precedence asymmetry A_ij and immutable mutilated-DAG "
        "interventional/counterfactual evaluation, strictly separated from EntanglementRegistry "
        "to preserve the no-communication theorem.",
    ),
    BCELEquivalence(
        "Hybrid SQLite-FTS5 feature-hashed episodic memory and continuous evolutionary recall (T248)",
        "functional",
        "Keep as stdlib SQLite lexical + deterministic blake2b token/trigram cosine retrieval, "
        "TTL archiving, deduplication, and continuous metric-cosine + Jaccard recall; "
        "removes hippocampal indexing and biological sleep/dream narratives.",
    ),
    BCELEquivalence(
        "Transactional pre/post sandbox patch verification and epistemic perturbation audit (T248)",
        "functional",
        "Keep as paired pre/post fixture delta evaluation with automatic rollback on regression "
        "and seeded perturbation-stability plus sample/complexity epistemic discounting.",
    ),
    BCELEquivalence(
        "Heuristic IIT Phi consciousness gates and anatomical lobe personas (T248)",
        "accidental",
        "Removed in full across external SPEACE forks: partition entropy-asymmetry and "
        "graph-density surrogates are not IIT Phi and provide zero evidence of consciousness.",
    ),
    # ----- T249: Complete BCEL Synthesis of Remaining Parallel SPEACE Elements -----
    BCELEquivalence(
        "Restorative homeostatic ODE, convex urgency field, and diffusive budget sharing (T249)",
        "functional",
        "Keep as bounded Euler state-space regulation, deadband viability, soft-constraint "
        "penalties, convex urgency gradients, and graph-diffusive subsystem energy allocation "
        "under a hard global power cap; removes survival/hunger drives and glial glucose prose.",
    ),
    BCELEquivalence(
        "Entropy-bounded UCB1 stream gating and proposal-only graph plasticity (T249)",
        "functional",
        "Keep as multi-stream UCB1 allocation enforcing a minimum Shannon entropy floor "
        "H(w) >= H_min and conservative edge decay/pruning plus proposal-only EdgeGrowthProposal "
        "records requiring external approval; removes thalamic spotlight and synaptogenesis prose.",
    ),
    BCELEquivalence(
        "SHA-256 epistemic provenance, structural cycle surprise, and action degradation gate (T249)",
        "functional",
        "Keep as canonical SHA-256 tool observation digests, negation-aware anti-overclaim "
        "screening, module symmetric-difference prediction error, and cost/reversibility "
        "degradation ('execute' -> 'plan' -> 'refuse'); removes prefrontal/basal-ganglia labels.",
    ),
    BCELEquivalence(
        "Cross-inhibited utility routing, simulate-only GOAP A*, LIFO backtracking, and skill generality pruning (T249)",
        "functional",
        "Keep as leaky-integrator control variables with mutual cross-inhibition, Sevo-penalized "
        "precondition routing, bounded simulate_only=True A* planning, LIFO hypothesis backtracking, "
        "cross-regime generality pruning, and time-bounded recall retention boost.",
    ),
    BCELEquivalence(
        "Bidirectional BFS graph abduction, 2-hop Jaccard analogy, and TDM idle maintenance (T249)",
        "functional",
        "Keep as typed confidence-product forward chaining, O(b^(d/2)) bidirectional BFS "
        "shortest-path abduction, 2-hop relational Jaccard structural similarity, and "
        "deterministic active/maintenance time-division scheduling; removes brainwave metaphors.",
    ),
    BCELEquivalence(
        "Fail-closed simulated sensor twin, stratified failure taxonomy, GC leak audit, and error ratchet (T249)",
        "functional",
        "Keep as opt-in runtime_mode='simulated' deterministic telemetry with JSONL audit logs, "
        "capability-dropped container isolation, deadlock-free sync/async bridge isolation, "
        "regime-stratified failure analysis, GC object-growth checks, and persisted error ratchets.",
    ),
    BCELEquivalence(
        "Autobiographical self-narrative identity and AGI-percentage headline indices (T249)",
        "accidental",
        "Removed in full across parallel SPEACE forks: narrative self-diaries and composite "
        "'AGI % / ARI' headline numbers do not establish general intelligence or agency.",
    ),
    # ----- T250: Neural Brain Substrate Remediation & Unified A/B Benchmark -----
    BCELEquivalence(
        "Post-spike readout trace, three-factor eligibility plasticity, and unified neural-quantum agent loop (T250)",
        "functional",
        "Keep as exponentially decaying post-spike readout traces, local pre-synaptic eligibility "
        "credit assignment, per-neuron metabolic floor protection, stationary semantic belief "
        "encoding, and integrated CellularBrain + ILF + CausalDAG + GOAP + TruthEngine execution.",
    ),
    BCELEquivalence(
        "Uncentered cosine similarity and zero-output MSE reward inflation as intelligence proof (T250)",
        "accidental",
        "Removed from assessment claims: positive baseline rewards on orthogonal or silent outputs "
        "create false-positive capability scores and must be paired with strict Top-1 accuracy.",
    ),
    # ----- T251: Grounded Dual-Speed Cognitive Bridge & Symbolic Quarantine -----
    BCELEquivalence(
        "Closed-schema symbol grounding and lagged provenance edge quarantine (T251)",
        "functional",
        "Keep as strict JSON-schema validation against an immutable SHA-256 SymbolRegistry plus "
        "CandidateEdge quarantine requiring calibrated parser confidence >= tau_ground, repeated "
        "non-zero-lag ObservationDigest temporal asymmetry, and DAG acyclicity before promotion.",
    ),
    BCELEquivalence(
        "Two-tier variational-surprise cognitive routing and out-of-band TDM consolidation (T251)",
        "functional",
        "Keep as a deterministic fast/slow dispatcher gated by ILF variational_free_energy, "
        "calibrated confidence, and ActionDegradationGate.select(), isolating SQLite episodic "
        "consolidation, GraphEdgePruner, and SkillLibrary pruning inside idle TDM maintenance ticks.",
    ),
    BCELEquivalence(
        "Kahneman System-1/System-2 cortical personas and semantic qualia binding claims (T251)",
        "accidental",
        "Removed in silicon: 'fast' and 'slow' denote software latency/deliberation routing tiers "
        "only, and canonical symbol lookup does not imply conscious semantic comprehension.",
    ),
    # ----- T252-T253: Experiential Macro-Skill Transfer & Credit-Localized Selective Repair -----
    BCELEquivalence(
        "Procedural chunking and relational role-parameterized macro-skill transfer (T252)",
        "functional",
        "Keep as deterministic lifting of solved GOAPAction sequences into role-parameterized "
        "schemas bound across domains via injective 2-hop Jaccard relational signatures, "
        "goal-consistency verification, and bounded micro-bridging over local refinements.",
    ),
    BCELEquivalence(
        "Weakest-precondition suffix verification, local plan splicing, and anti-Einstellung abandonment (T253)",
        "functional",
        "Keep as step-level transition residual localization, empirical operator effect updates, "
        "backward weakest-precondition kernel regression, sub-budget bridge splicing, and "
        "explicit macro abandonment whenever suffix integrity or blocker constraints fail.",
    ),
    BCELEquivalence(
        "Hippocampal schema replay consciousness and sudden insight qualia claims (T252-T253)",
        "accidental",
        "Removed in silicon: macro-skill lifting, structural analogy matching, and local plan "
        "splicing are finite graph and set algorithms with zero subjective insight claims.",
    ),
    # ----- T254: Triadic Substrate Safeguard & Coupled Anti-Polycrisis Resilience -----
    BCELEquivalence(
        "Planetary gestation, SPEACE Macro organs, and cosmic expansion teleology (T254)",
        "accidental",
        "Removed from executable claims: biological gestation, planetary organs, and autonomous "
        "cosmic expansion are orienting metaphors only; software holds zero subjective identity "
        "or unapproved physical/ecological/economic sovereignty.",
    ),
    BCELEquivalence(
        "Non-compensable triadic substrate safeguard over Earth, Civilization, and Infrastructure (T254)",
        "functional",
        "Keep as an exact 3x4 partition of the 12D non-fungible CME vector with Leontief per-axis "
        "and per-pillar floors, cross-pillar anti-sacrifice bounds, write-locked C6/C7 clauses, "
        "and HomeostaticODEController coupling (advisory/simulation-only under T217).",
    ),
    BCELEquivalence(
        "Coupled polycrisis cascade propagation and anti-risk-transfer shield (T254)",
        "functional",
        "Keep as discrete multi-domain propagation over climatic-ecological, economic, social, "
        "sanitary, and cyber-infrastructural severities with spectral-radius and quadratic "
        "co-activation synergy diagnostics, blocking interventions that transfer risk across domains.",
    ),
    BCELEquivalence(
        "Infallible planetary ark or coercive algorithmic relocation teleology (T254)",
        "accidental",
        "Removed in silicon: software models cannot guarantee risk-free terrestrial or off-world "
        "survival without T217 physical mass-energy-ecological qualification, and involuntary "
        "human relocation or biosphere abandonment is constitutionally forbidden.",
    ),
    BCELEquivalence(
        "Voluntary protective refuge habitat protocol and Leontief life-support reserve contract (T254)",
        "functional",
        "Keep as opt-in individual admission/exit verification (for polycrisis protection or "
        "personal wellbeing), N+2 Leontief capacity bounds across water, food, oxygen, clean "
        "power, medical, and psychosocial wellbeing stocks (terrestrial or extraterrestrial), "
        "and non-abandonment coupling with Earth/Civilization/Infrastructure CME floors (C8).",
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
