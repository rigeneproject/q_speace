# T210 — Resilient Agentic AI for Smart Cities: Hybrid Control, Post-Quantum Security, and Protection Against Human Error

**Author:** Roberto De Biase (CIO, Rigene Project)  
**Status:** proposal — documentation only, no executable path  
**Date:** 2026-10-31  
**Scope:** reference architecture, threat model, maturity-classified claims, and open
verification items for deploying agentic generative AI in critical infrastructure.  
**Non-goal:** assert quantum consciousness, grant entanglement any communication role,
or authorize direct GenAI actuation of physical systems.

---

## Technical Abstract

This abstract examines the current limits and possible architectures for deploying
agentic Generative AI in the control of critical infrastructure. The central thesis is
that, as far as publicly documented, no GenAI agent currently exercises direct,
autonomous, and structural control over critical physical systems. Integration should
rely on a hybrid, localized, and resilient architecture:

```
GenAI Agent -> Cloud -> Deterministic Software
```

where the deterministic layer holds final execution authority. No single actor, human or
artificial, should be able to produce a critical action alone. Security derives from the
independence and diversity of controls, not from the presumed reliability of any
component. Human error and risky human behavior are treated as a structural threat on a
par with technical failure and cyberattack. Content is classified by maturity:

- consolidated facts;
- established practices;
- architectural proposals to be validated;
- speculative hypotheses (with plausibility rating);
- claims to be verified.

## 0. Threat Model (Summary)

| Actor | Capability | Objective |
| --- | --- | --- |
| External cyber attacker | Network intrusion, supply-chain compromise, jamming/spoofing | Disruption, extortion, sabotage |
| State-level adversary | Advanced persistent threats, physical attack, possible EMP | Large-scale infrastructure denial |
| Malicious or coerced insider | Legitimate credentials and procedural knowledge | Sabotage, data theft |
| Well-meaning operator | Fatigue, overload, over-trust in AI | Unintentional error |
| Manipulated AI agent | Prompt injection or poisoned input data | Induced harmful proposals |
| Natural/technical events | Solar storms, earthquakes, component failure | Unplanned outage |

Any claim of security in this document is relative to this model. Absolute claims
("inviolable", "immune", "100%") are not made.

## 1. Consolidated Facts

- Generative models are probabilistic and do not guarantee identical outputs for
  identical inputs; critical physical control requires deterministic, verified,
  extensively tested software.
- In advanced deployments, agentic AI operates mainly as predictive and decision-support
  technology, with human approval for structural actions.
- IT and OT are separated: SCADA/PLC systems are often isolated from the Internet and from
  large AI models for cybersecurity reasons.
- The current role of GenAI in physical infrastructure is mainly predictive maintenance
  and software-based logistics optimization.
- Critical systems are designed against declared integrity levels (e.g., SIL under
  IEC 61508) with stated failure rates; "100% fault tolerance" does not exist.
- Human error remains a major cause of incidents in complex systems, even with advanced
  automation.
- Human-in-the-loop supervision is insufficient by itself: overload, poor training, or
  automation bias turn approval into a false safeguard.
- Safety requires defense in depth: technical, procedural, organizational, and physical
  measures.
- Critical systems should make correct actions easy and dangerous actions difficult or
  impossible.
- Fiber-optic links are immune to electromagnetic induction, but transceivers, drivers,
  and processors at their endpoints remain electronic and vulnerable.

## 2A. Established Practices

- Separation of duties and multi-person authorization (two-person rule; four/six-eyes for
  the highest criticality), with independent authentication and channels.
- Least privilege and just-in-time access, scoped by role, duration, and perimeter.
- Logical and physical interlocks: deterministic software rejects commands violating
  safety constraints even if formally authorized.
- Equal rules for humans and AI: human commands pass through the same guardrails and
  impact checks as AI proposals; no privileged bypass channel.
- Time-locks for irreversible actions, with cancellation window.
- Safe defaults and fail-safe / fail-operational design, chosen per infrastructure type.
- Non-electronic physical fail-safes: spring-loaded valves, mechanical interlocks, safety
  relays that reach a safe state with all electronics off.
- Kill switches and controlled break-glass procedures with strong trace and mandatory
  post-hoc review.
- Rate limiting and command quarantine for anomalous sequences.
- Immutable, separated audit log and replay: who did what, when, on which AI
  recommendation, with which outcome.
- Error-resistant human-machine interface: hierarchical alerts, no single-click destructive
  actions, contextual confirmations, dynamic checklists, displayed simulated impact rather
  than a bare yes/no.
- Fatigue and cognitive-load management: shifts, breaks, limits on simultaneous
  supervision, reduction of non-actionable alarms.
- Training, certification, skills redundancy: drills, tabletop exercises, red teaming,
  chaos engineering, including scenarios where the AI is wrong and the human must notice.
- Just culture and non-punitive reporting.
- Insider threat program: proportionate monitoring, role rotation, rapid revocation.
- Change management and configuration control for software, sensors, rules, and models.
- Total and diversified communication redundancy (private fiber, dedicated cellular, LEO
  satellite) and island mode with controlled degradation.

## 2B. Architectural Proposals to Be Validated

- Hybrid `GenAI -> Cloud -> deterministic software`, with GenAI as analysis and proposal
  layer only.
- Dual-layer guardrails: semantic and mathematical checks plus pre-execution impact
  simulation (digital twin or simplified physical model) of every critical command.
- Formal verification of the deterministic layer: proving that defined unsafe states are
  unreachable, beyond testing.
- Agent diversity: multiple independent models/vendors that must agree on critical
  proposals, to avoid correlated errors.
- Defense against agent manipulation: input sanitization, separation between data and
  instructions, and anomaly detection on agent proposals (prompt injection and data
  poisoning).
- Hierarchical/federated architecture: central GenAI for coordination; local Edge GenAIs
  with proposal authority and autonomous management within predefined limits. Execution
  authority remains with the deterministic layer.
- Post-quantum cryptography on conventional infrastructure, as a pragmatic alternative to
  hardware QKD.
- Signed, append-only ledgers (hash chain with PQC signatures, trusted timestamping) as
  baseline; DAG-based ledgers evaluated against this baseline for the actual command-audit
  use case.
- Behavioral anomaly detection on operators (schedules, sequences, privileges), with human
  escalation and no automatic punitive action.
- Island mode with explicit decision limits: predefined safety protocols, no expansion of
  authority during isolation.
- Nanodrone swarms for visual/thermal inspection and temporary sensor replacement,
  together with their own security case (spoofing, hijacking, jamming, authentication of
  swarm nodes).
- Stratospheric HAPS as communication relays and coordination nodes.
- EMP hardening by protection zones: shielding with controlled apertures, port-level
  transient suppression, wide-bandgap semiconductors as a contributing factor, optical
  links with hardened endpoints, shielded bunkers with cold backups reactivated by
  mechanical or human procedure.

## 3. Speculative Hypotheses

| Hypothesis | Plausibility |
| --- | --- |
| AI as "supervisor of the supervisor", detecting human errors and procedural deviations in real time, as support and never final judge | High |
| Verifiable, non-repudiable ledgers for every command and every human waiver, strengthening accountability | High |
| Edge AIs in island mode applying predefined safety protocols with explicit decision limits | Medium-high |
| Nanodrone swarms self-organizing into temporary aerial mesh networks | Medium-low (demonstrated at small scale; resilience and cost unproven) |
| Qualified resistance to a defined class of EMP threats through integrated hardening | Medium (achievable for defined classes, not as generic immunity) |
| HAPS as emergency compute nodes hosting reduced model copies | Low (limited by payload, power, cooling; current HAPS are largely demonstrators) |
| Risk reduction of the full chain through PQC plus append-only ledgers | Medium (reduces specific risks; does not make the system inviolable) |

## 4. Claims to Be Verified

- Absence, in every city worldwide, of direct and structural GenAI control over critical
  infrastructure (to be restated as "per public documentation" or verified with sources).
- Latency of DAG ledgers in the specific context of infrastructure commands.
- Technical and economic sustainability of HAPS with months-long endurance and high
  bandwidth.
- Effectiveness of nanodrone swarms in autonomy, bandwidth, physical resilience, cost, and
  security.
- Actual EMP resistance of the proposed solutions and their qualification in extreme
  scenarios.
- Definition of the safety case and target integrity levels (SIL) for each criticality
  tier.
- End-to-end security of `GenAI -> Cloud -> deterministic software`: key management,
  supply chain, endpoint attacks.
- Effectiveness of defenses against prompt injection and manipulation of the agent through
  input data.
- Balance between Edge AI autonomy and human supervision in critical situations; residual
  autonomy in island mode.
- Extent to which automation bias reduces human-in-the-loop effectiveness under pressure.
- Dual-authorization protocols compatible with real-time latency requirements.
- Behavioral detection without excessive false positives or violations of privacy and
  labor regulations.
- Regulatory compliance and legal accountability for automated decisions in critical
  infrastructure.
- Joint certification and audit of human and software protocols within an integrated
  safety case.

## 5. BCEL Classification

Required by `AGENTS.md` before any of this becomes executable code. This document does
not implement behavior; the table fixes which concepts may later become mathematical
rules and which must be dropped in silicon.

| Concept | Classification | Digital rule (if functional) |
| --- | --- | --- |
| GenAI as final actuator | accidental | Forbidden. GenAI proposes; the deterministic layer executes. |
| Deterministic execution layer | functional | Pure, total function over validated command + safety constraints; rejects unsafe states. |
| Probabilistic model output | functional | Treated only as an untrusted proposal with an explicit confidence channel. |
| Multi-agent agreement | functional | Threshold quorum over independent proposals before escalation. |
| Impact simulation / digital twin | functional | Pre-execution check of the resulting state against declared invariants. |
| Append-only audit ledger | functional | Hash-chained records with PQC signatures and monotonic timestamps. |
| Island mode | functional | Bounded autonomy with fixed, pre-declared decision limits; no authority expansion. |
| "Supervisor of the supervisor" | functional (support only) | Anomaly score over operator and AI actions; advisory, never final judge. |
| Human error as threat class | functional | Same guardrails and rate limits applied to human-originated commands. |
| Quantum consciousness / organism metaphor | accidental | No representation or inference of subjective states. |
| Entanglement as signaling channel | accidental | Forbidden. Entanglement is a computational resource only (no-communication theorem). |
| "Inviolable" / "immune" / "100%" security | accidental | Removed. Claims are relative to the threat model and carry residual risk. |
| EMP / HAPS / nanodrone specifics | accidental (for Q-SPEACE core) | Out of scope until separately specified and gated by the safety case. |

## 6. Relation to Q-SPEACE Invariants

- No claim of quantum consciousness: this spec assigns GenAI no subjective or final
  authority.
- Entanglement only as computational resource: PQC is proposed on conventional
  infrastructure; no entanglement-based communication.
- Every feature needs tests and passes the BCEL filter: nothing here is implemented; future
  implementation requires tests first.
- No real quantum backend without `QuantumGeneSet.noise_model` and an energy/Sevo gate:
  unaffected, since no quantum backend is proposed here.

## 7. Acceptance Criteria for Future Implementation

1. A deterministic guardrail module rejects every command that violates a declared safety
   invariant, regardless of whether the command originated from a human or an AI.
2. No code path lets a GenAI proposal reach an actuator without passing the deterministic
   guardrail and the impact simulation.
3. Audit records are append-only and verifiable end to end.
4. Island-mode autonomy cannot exceed its pre-declared decision limits.
5. Tests cover prompt injection, forged commands, replay, and authority escalation.
6. No test or document asserts absolute security, immunity, or quantum consciousness.
