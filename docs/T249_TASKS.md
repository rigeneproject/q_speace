# T249 — Task Registry: Complete Parallel-Repository BCEL Synthesis

**Status:** production task registry (agentic mode).  
**Companion specification:** [T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md](T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md).  
**Execution discipline:** sequential gated execution (`T249-01` → `T249-08`); every task requires BCEL registration, strict `math.isfinite` fail-closed guards, deterministic tests, and zero new runtime dependencies.

| ID | Status | Source Repository(ies) | Target Module(s) in `q_speace` | Depends | Deliverable |
|---|---|---|---|---|---|
| `T249-01` | `DONE` | `speaceorganismocibernetico` (M5), `speace_ds` | `q_speace/metabolism/homeostasis.py`, `q_speace/orchestrator.py` | `T248` | `HomeostaticODEController` (restorative ODE + viability + soft constraints + convex urgency gradient) & `DiffusiveBudgetAllocator` |
| `T249-02` | `DONE` | `speaceorganismocibernetico` (M5) | `q_speace/aacm/plasticity.py` | `T249-01` | `EntropyBoundedUCB1Gating` (Shannon floor $H(\mathbf{w}) \ge H_{\min}$), `GraphEdgePruner`, & proposal-only `ProposalOnlyEdgeGrower` |
| `T249-03` | `DONE` | `GTP SPEACE` (`v3.20.15`) | `q_speace/spiking_brain/truth_engine.py`, `q_speace/spiking_brain/cortex.py` | `T249-02` | `TruthEngine` (SHA-256 `ObservationDigest` + negation-aware anti-overclaim guard), `StructuralPredictiveCoder`, & `ActionDegradationGate` |
| `T249-04` | `DONE` | `cellular_speace_ollama`, `speace_ds` | `q_speace/routing.py`, `q_speace/self_improvement_cortex/skill_library.py` | `T249-03` | `UtilityDriveSystem`, `CostAwareRouter`, `simulate_only` A* `GOAPPlanner`, LIFO `HypothesisStack`, `SkillLibrary`, & `ReconsolidationWindow` |
| `T249-05` | `DONE` | `speace_agi` | `q_speace/spiking/reasoning.py` | `T249-04` | `SymbolicGraphReasoner` (forward chaining, bidirectional BFS `abduce`, 2-hop Jaccard analogy) & `TDMMaintenanceScheduler` |
| `T249-06` | `DONE` | `cellular_speace_{docker,gpt,opus,big}` | `q_speace/bridge/simulated_sensor.py`, `deploy/sandbox/`, `q_speace/vertical_slice/diagnostics.py` | `T249-05` | `SimulatedSensorAdapter` + Stage-2.5 sandbox profile, `run_coro_isolated`, `StratifiedFailureAnalyzer`, `MemoryLeakAuditor`, & `DifferentialErrorRatchet` |
| `T249-07` | `DONE` | Cross-cutting | `q_speace/cli.py`, `tests/test_t249_complete_parallel_synthesis.py` | `T249-06` | Read-only CLI diagnostic commands (`qspace eval stratify`, `qspace quantum memory-audit`) + full unit/integration test suite |
| `T249-08` | `DONE` | `q_speace` canonical repo | `.github/workflows/ci.yml` gates + `origin/main` | `T249-07` | `pytest`, `ruff`, `black`, `mypy`, `py_compile`, CycloneDX SBOM verification, git commit & push to GitHub |
