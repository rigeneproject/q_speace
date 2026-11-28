# Frozen modules (T266-03)

**Rule.** Until the T267 external experiment is reported, the modules below receive bug fixes
and security fixes only. No new feature, no new spec, no new MCP tool. They stay in place:
the remote MCP service and the CLI import several of them, so they are not moved yet.

| Module | What it is (engineering name) | In the measured decision loop? | Status |
|---|---|---|---|
| `q_speace/quantum/` | numpy state-vector simulator, optional backend adapters | no | frozen |
| `q_speace/radio/` | simulated RF modulation / compliance emulator | no | frozen |
| `q_speace/economy/` | allocation and accounting primitives, stdio MCP server | no (served by MCP) | frozen |
| `q_speace/ptaa/` | governance demonstrator | no | frozen |
| `q_speace/singularity/` (IoNT, federation, compliance, phase evaluator) | simulated node federation, advisory evaluators | no (served by MCP) | frozen |
| `q_speace/seed/` | constitution, kill switch, change pipeline | kill switch and genome hash only | frozen except those two |
| `q_speace/fractal_qca*.py`, `schumann.py`, `earth_feed.py`, `systemic_resonance.py` | cellular-automaton and signal experiments | no | frozen |
| `q_speace/orchestrator.py` | cost/energy gate loop; its spike activity is seeded noise | no | frozen |
| `cellular_speace/` | separate code base (≈2,900 files) | only the 80-unit circuit via `neural_agent.py`, not required (T250) | frozen |

## Active core (candidates for the `brain` kernel, to be confirmed by T267)

| Module | Engineering name |
|---|---|
| `q_speace/bridge/grounding.py`, `typed_nl_pipeline.py`, `dual_speed.py` | closed-world symbol validation, belief revision, two-tier routing |
| `q_speace/routing.py`, `q_speace/aacm/typed_dag.py` | planner, typed plan graph |
| `q_speace/self_improvement_cortex/` (`epigenetics.py`, `macro_skills.py`, `skill_library.py`) | evidence counters with consolidation, reusable plan fragments |
| `q_speace/spiking_brain/memory.py` | SQLite episodic store |
| `q_speace/bridge/latent_discovery.py`, `stage1_workspace.py`, `stage2_cortex.py` | hypothesis induction from failures (sandbox prototypes) |
| `q_speace/spiking/` | integer quantisation, activity statistics (telemetry until an ablation shows an effect) |
| `q_speace/vertical_slice/`, `q_speace/experiments/` | evaluation harnesses |

## Glossary: bio-inspired term → engineering name

| Term in code/docs | What it does |
|---|---|
| epigenome / epigenetic consolidation | promotion/suppression counters with a threshold for persistence |
| myelination | registry that up-weights frequently successful routes |
| astrocyte syncytium | mass-conserving budget redistribution between nodes |
| criticality / branching ratio | closed-loop regulation of a quantisation threshold from activity counts |
| spikes | integer quantisation of an activity vector |
| global workspace / ignition | priority arbitration among proposals |
| genome / constitution | immutable configuration with a hash check |
| cortex, brain, organism | interface labels; no claim of awareness (AGENTS.md §2) |
