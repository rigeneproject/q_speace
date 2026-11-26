# T252–T253 — Experiential Macro-Skill Transfer & Credit-Localized Selective Repair

**Status:** agentic (production)  
**Date:** 2026-11-26  
**Preregistration manifest:** [T252_T253_PREREG.json](T252_T253_PREREG.json) (locked via `q_speace/spiking/prereg_lock.py`)  
**Depends on:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T222](T222_NCM_CODEC_SPEC.md), [T248](T248_CROSS_REPO_SYNTHESIS_AND_CORE_HARDENING_SPEC.md), [T249](T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md), [T251](T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md)  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib only)  
**HTTP MCP surface impact:** Zero new MCP tools (preserves the 12-tool `T225`/`T247` surface)

---

## 1. Scientific Questions & Experimental Controls

`T251` demonstrated adaptive metacognitive effort allocation over developer-supplied symbols and operators (`proto-AGI` architectural scaffold). `T252` and `T253` test whether SPEACE exhibits **functional experiential generality** across unseen problem families via two distinct, falsifiable questions:

1. **Question Q1 (`T252` — Axis 3: Continual Memory & Analogical Skill Transfer):**  
   *Does procedural experience acquired autonomously in Environment A accelerate problem-solving in a non-isomorphic Environment B containing renamed symbols, structural distractors, and local precondition refinements?*  
   - **Primary Ablation (`SPEACE_EXPERIENTIAL` vs `SPEACE_AMNESIC`):** Both agents receive identical operators, observations, safety gates, and $A^*$ expansion budgets, and **both are permitted to learn during B**. The sole difference is whether `SkillLibrary` retains the role-parameterized macro-skills consolidated during A's `TDMMaintenanceScheduler` idle cycle.
2. **Question Q2 (`T253` — Axis 4: Credit-Localized Selective Repair vs Global Replan & Anti-Einstellung):**  
   *When an underlying transition rule in B mutates mid-episode without external notification, can SPEACE diagnose which step failed, preserve the still-valid prefix/suffix, synthesize a bounded local bridge, and — critically — recognize when the suffix itself is invalidated and must be abandoned?*  
   - **Primary Fork Control (`SPEACE_SELECTIVE_REPAIR` vs `SPEACE_GLOBAL_REPLAN`):** Cloned from the **exact same state and memory checkpoint immediately prior to the rule shift**. Neither clone receives the identity of the mutated rule. `SELECTIVE_REPAIR` applies weakest-precondition suffix verification and bounded local splicing; `GLOBAL_REPLAN` discards the broken macro-skill and replans globally from $S_k^{\mathrm{obs}} \to G$.
   - **Negative-Control Episodes (Suffix-Invalidating Shifts / Anti-Einstellung Gate):** Episodes where the rule change invalidates the goal-producing effect of the suffix or injects a persistent blocker fluent. Stubbornly forcing the old suffix wastes expansions or fails; the sound decision is `ABANDON_MACRO_AND_REPLAN`.

---

## 2. Mathematical Formalization

### 2.1 Role-Parameterized Macro-Skills (`T252` — Phase 1 & Phase 2)

Given a ground plan $\pi = [a_1, \dots, a_m]$ over relational fluents $r(o_1, \dots, o_d)$ that solved goal $G_A$ from $S_{0,A}$:
1. **Relational Role Lifting:** Concrete constants $\{o_1, \dots, o_p\}$ appearing in $\pi$ are lifted in canonical appearance order to role variables $\{?r_0, \dots, ?r_{p-1}\}$, producing `ParameterizedStep` templates $(\text{op}_i, \vec{\rho}_i, \mathrm{pre}_i(\vec{\rho}), \mathrm{add}_i(\vec{\rho}), \mathrm{del}_i(\vec{\rho}))$.
2. **2-Hop Relational Role Signatures:** Each role $?r_u$ records its source 2-hop neighborhood signature $\Sigma_A(?r_u)$ extracted via `SymbolicGraphReasoner` (`q_speace/spiking/reasoning.py`).
3. **Analogical Role Mapping in Environment B (`AnalogicalRoleMapper`):**  
   For candidate target entities $v \in V_B$ (which include **distractor objects** sharing partial 1-hop relations but disconnected from the goal chain), candidate bindings $\phi: \{?r_u\} \to V_B$ are ranked by mean 2-hop Jaccard similarity:
   $$J(\phi) = \frac{1}{p}\sum_{u=0}^{p-1} \frac{|\Sigma_A(?r_u) \cap \Sigma_B(\phi(?r_u))|}{|\Sigma_A(?r_u) \cup \Sigma_B(\phi(?r_u))|}$$
   subject to injectivity ($\phi(?r_u) \ne \phi(?r_w)$ for $u \ne w$) and goal-fluent grounding consistency ($G_B \subseteq \mathrm{add}(\phi(M)) \cup S_{0,B}$). Every selection emits an auditable `AnalogyAuditTrace`.
4. **Non-Isomorphic Precondition Micro-Bridging:**  
   When B introduces a local structural refinement (e.g., an extra safety-interlock or staging step required before $\phi(a_i)$), unsatisfied step preconditions $\mathrm{pre}(\phi(a_i)) \setminus S_{i-1}$ invoke a micro-bridge search capped at $B_{\mathrm{micro}} \ll B_{\mathrm{global}}$ expansions rather than full horizon search.

### 2.2 Transition Residual Diagnosis & Suffix Admissibility (`T253` — Phase 3)

During step-by-step execution of an instantiated macro-skill $M_\phi = [a_1, \dots, a_m]$:
1. **Surprise Detection & Step Localization:**  
   After executing $a_k$ from state $S_{k-1}$, compare predicted state $\hat{S}_k = (S_{k-1} \setminus \mathrm{del}_k) \cup \mathrm{add}_k$ against observed state $S_k^{\mathrm{obs}}$:
   $$\Delta^-_k = \hat{S}_k \setminus S_k^{\mathrm{obs}} \quad (\text{missing expected effects}), \qquad \Delta^+_k = S_k^{\mathrm{obs}} \setminus \hat{S}_k \quad (\text{unexpected side effects}).$$
   Non-empty $(\Delta^-_k \cup \Delta^+_k)$ injects prediction error into `InformationalLogicalField.observe_prediction_error()`, spiking `variational_free_energy() > tau_surprise`, and updates `EmpiricalOperatorModel` for $a_k$:
   $$\mathrm{add}_k^{\mathrm{emp}} \leftarrow (S_k^{\mathrm{obs}} \setminus S_{k-1}), \qquad \mathrm{del}_k^{\mathrm{emp}} \leftarrow (S_{k-1} \setminus S_k^{\mathrm{obs}}).$$
2. **Weakest-Precondition Regressed Kernel ($W_k$):**  
   For remaining suffix $M_{k+1..m}$ and goal $G$, regress backward from $W_m = G$:
   $$W_{j-1} = (W_j \setminus \mathrm{add}_j^{\mathrm{emp}}) \cup \mathrm{pre}_j^{\mathrm{emp}}, \qquad \text{requiring } W_j \cap \mathrm{del}_j^{\mathrm{emp}} = \emptyset \quad \forall j \in \{m, \dots, k+1\}.$$
3. **Three-Part Suffix Admissibility & Anti-Einstellung Rule:**  
   Retaining suffix $M_{k+1..m}$ (`SELECTIVE_LOCAL_REPAIR`) is permitted **if and only if**:
   - **(C1) Suffix Operator & Kernel Integrity:** $k < m$, regression $W_k$ is well-defined ($W_j \cap \mathrm{del}_j^{\mathrm{emp}} = \emptyset$), and forward simulation of $M_{k+1..m}$ from $W_k$ under `EmpiricalOperatorModel` satisfies $G$.
   - **(C2) Unclobbered Goal & Blocker Clearance:** No unexpected side-effect fluent $b \in \Delta^+_k$ is a terminal unremovable blocker or goal-negation fluent uncleaned by available operators.
   - **(C3) Sub-Budget Local Bridge Existence:** `GOAPPlanner.plan_with_stats(S_k^obs, W_k, max_expansions=B_local)` finds a valid bridge $\pi_{\mathrm{bridge}}$ within $B_{\mathrm{local}} = \max(4, \lfloor \alpha_{\mathrm{local}} \cdot B_{\mathrm{global}} \rfloor)$ ($\alpha_{\mathrm{local}} \in (0, 0.40]$).

   If **(C1)**, **(C2)**, or **(C3)** fails, the engine immediately emits `RepairDecision = "ABANDON_MACRO_AND_REPLAN"` with an explicit diagnostic code (`"terminal_or_suffix_invalidated"`, `"unrecoverable_blocker_fluent"`, or `"local_bridge_exceeded_budget"`), marks the skill regime-restricted via `ReconsolidationWindow`, and executes global replanning from $S_k^{\mathrm{obs}} \to G$.  
   When **(C1)–(C3)** succeed, the spliced macro-skill $[a_1, \dots, a_{k-1}, *\pi_{\mathrm{bridge}}, a_{k+1}, \dots, a_m]$ is lifted and reconsolidated in `SkillLibrary` for zero-search reuse on subsequent unseen variants (`Phase 3b`).

---

## 3. BCEL Classification Matrix (`q_speace/bcel/catalog.py`)

| Bio / Cognitive Concept | BCEL Class | Digital Rule in `q_speace` |
|---|---|---|
| Procedural chunking & relational schema transfer (`T252`) | `functional` | Lift solved `GOAPAction` traces during idle `TDMMaintenanceScheduler` ticks into role-parameterized `RoleParameterizedMacroSkill` schemas bound across domains via injective 2-hop Jaccard relational signatures and goal-consistency checks. |
| Reconsolidation splicing, weakest-precondition repair & anti-Einstellung abandonment (`T253`) | `functional` | Localize transition residuals $(\Delta^-_k, \Delta^+_k)$, update empirical operator effects, regress weakest preconditions $W_k$, splice a bounded bridge $\pi_{\mathrm{bridge}}$ when $W_k$ is reachable within $\lfloor \alpha B_{\mathrm{global}} \rfloor$, and deterministically abandon invalid suffixes. |
| Hippocampal replay consciousness & sudden "aha / insight" qualia (`T252–T253`) | `accidental` | Removed in silicon: macro-skill extraction, analogy matching, and local plan splicing are finite graph/set algorithms with zero subjective insight or biological memory claims. |

---

## 4. Preregistered Problem Families & Disjoint Split (`T252_T253_PREREG.json`)

Locked via `q_speace/spiking/prereg_lock.py` prior to evaluation:
- **Calibration Families (`n = 2` families, used exclusively to calibrate $\alpha_{\mathrm{local}}$ and $\tau_{\mathrm{analogy}}$):**
  - `F1_thermal_lock`: Microgrid valve/pump thermal recovery $\to$ Battery bay Busbar/chiller with distractor auxiliary fans and safety-pin micro-refinement.
  - `F2_staging_pipeline`: Data ingestion staging $\to$ Artifact signing pipeline with distractor cache nodes and checksum-gate micro-refinement.
- **Held-Out Families (`n = 3` unseen families, disjoint domain topologies & predicates):**
  - `F3_quorum_handoff`: Consensus shard drain/handoff $\to$ Satellite transponder beam handoff (with 3 distractor transponders + beacon-sync refinement; Phase 3 mid-step link-key mutation + suffix-invalidating receiver-offline control).
  - `F4_cryo_purification`: Cryogenic helium purge/chill $\to$ Cleanroom lithography chamber purge (with 3 distractor manifolds + purge-vent refinement; Phase 3 mid-step filter-clogged mutation + suffix-invalidating chamber-breach control).
  - `F5_containment_airlock`: Bio-sandbox equalization/seal $\to$ Autonomous ROV pressure-lock transfer (with 3 distractor hatches + seal-verify refinement; Phase 3 mid-step valve-stick mutation + suffix-invalidating hull-lockout control).

---

## 5. Acceptance Gates & Full 5-Axis Activation (`qspace eval agi-profile`)

1. **Phase 1 (Acquisition & Re-binding in A):** `100%` goal completion on novel object bindings in A with `0` planner expansions on re-execution.
2. **Phase 2 (`SPEACE_EXPERIENTIAL` vs `SPEACE_AMNESIC` in Held-Out B):** $\ge 50\%$ reduction in cumulative $A^*$ planner expansions across held-out families (`paired_bootstrap_ci` 95% lower bound $> 0$), `100%` distractor rejection in `AnalogyAuditTrace`, and non-inferior (`100%`) task success.
3. **Phase 3a (`SPEACE_SELECTIVE_REPAIR` vs `SPEACE_GLOBAL_REPLAN` on Repairable Shifts):** $\ge 40\%$ reduction in post-shift recovery expansions (`paired_bootstrap_ci` 95% lower bound $> 0$), `100%` recovery success, and $\ge 80\%$ expansion reduction on a **subsequent unseen variant (`Phase 3b`)** using the reconsolidated macro-skill.
4. **Phase 3c (Anti-Einstellung Suffix-Invalidated Controls):** `100%` accurate `ABANDON_MACRO_AND_REPLAN` classification and `100%` recovery via global replanning (vs `0%` success for a `STUBBORN_REUSE_CONTROL` diagnostic baseline).
5. **5/5 Radar Activation (`agi_profile.v1` / `qspace eval agi-profile`):** Populates Axis 3 (`3_continual_memory_and_skill_transfer`) and Axis 4 (`4_ood_abstraction_and_adaptation`) with empirical held-out scores and bootstrap 95% CIs alongside Axes 1, 2, and 5 (`overall_verdict = "PASS_ALL_5_AXES"` when all hard gates and phases pass).

---

## 6. Empirical Held-Out Results (`F3`–`F5`, `seed=2026`)

Reproducible via `qspace eval t252-benchmark --seed 2026` and `qspace eval agi-profile --seed 2026`:

| Experimental Phase & Metric (`3` Unseen Held-Out Families, `12` Paired Trajectories) | Control / Ablation Arm | SPEACE Target Arm | Reduction / Verdict |
|---|---:|---:|---:|
| **Phase 1 — Re-binding on Novel Objects in A** | — | `100.0%` (`0` $A^*$ expansions) | `PASS` |
| **Phase 2 — Transfer to Non-Isomorphic B (`EXPERIENTIAL` vs `AMNESIC`)** | `1,152` expansions (`100%` succ) | **`12` expansions** (`100%` succ, `100%` distractor rej) | **`-98.96%` expansions** (`Δ = +0.8120`) |
| **Phase 3a — Forked Pre-Shift Mid-Step Repair (`SELECTIVE` vs `GLOBAL_REPLAN`)** | `492` expansions (`100%` succ) | **`60` expansions** (`100%` succ) | **`-87.80%` expansions** |
| **Phase 3b — Subsequent Unseen Variant with Spliced Skill** | `492` expansions | **`0` expansions** (`100%` succ) | **`-100.0%` expansions** |
| **Phase 3c — Anti-Einstellung Suffix-Invalidated Negative Controls** | `0.0%` (`STUBBORN_REUSE`) | **`100.0%` abandon + `100.0%` standby recovery** | **`PASS` (`Δ_Axis4 = +0.7133`)** |

