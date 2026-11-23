# T236 — IoNT Cellular Node ("SPEACE Macro Mini") Integration into `q_speace/singularity/` & MCP

**Status:** agentic (production advisory contract, governance DLT ledger & sandboxed digital twin)  
**Date:** 2026-11-23  
**Dependencies:** `AGENTS.md`, `T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`,
`T225_REMOTE_MCP_SERVICE_SPEC.md`, `T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md`.  
**Non-goals:** No physical hardware actuation over MCP, no DLT consensus inside real-time motor
control loops, no claims of biological cellular life or TRL-9 general-purpose nanoscale robotics.

---

## 1. 4-Layer Architecture for External IoNT / Micro-IoT Cellular Nodes

Extends `q_speace/singularity/` so external cyber-physical cellular nodes ("SPEACE Macro Mini":
GenAI swarm + lightweight governance DLT + IoNT/Micro-IoT sensors and actuators) can connect to
`q_speace` via MCP under strict physical, thermodynamic, and T217 safety boundaries:

- **Layer 0 — Deterministic Hardware Safety Interlock (`< 5 ms`, no LLM/DLT/MCP)**:
  mandatory firmware/MCU e-stop (`I1`), thermal/power/force/geo-fence containment. Missing
  interlock when `actuator_count > 0` fails closed (`layer0_hardware_interlock_missing`).
- **Layer 1 — Scale-Staged IoNT / Micro-IoT Periphery (`10–200 ms`)**:
  explicit TRL staging (`SIMULATION_DIGITAL_TWIN` → `BENCHTOP_MICRO_IOT_MEMS` →
  `CONFINED_MICROFLUIDIC_LAB` → `NANOSCALE_IONT_RESEARCH`) with explicit energy harvesting,
  packet loss, and physical sensor reality-grounding error ($E_{\text{causal}} \le 0.03$).
- **Layer 2 — Edge GenAI Swarm + Lightweight Governance DLT (`0.5–10 s`, slow plane)**:
  `DLTSwarmLedger` records hash-chained provenance, quorum approvals (`proposer_id` excluded),
  `genome_sha256`, and monotonic epochs. Putting DLT inside the real-time motor loop is
  unconditionally prohibited (`dlt_in_realtime_motor_loop_prohibited`).
- **Layer 3 — Advisory `q_speace` MCP Bridge (`1–60 s`, `mcp_actuation_permitted=False`)**:
  new advisory MCP tool **`iont_node_assess`** (scope `qspeace:compute`) + manifest section
  `iont_cellular_nodes`, enabling connected nodes to audit Layer-0 interlock compliance,
  DLT separation, containment, conservative $D_{\text{allo}}$, and advisory epigenetic adjustments.

---

## 2. BCEL Classification

Registered in `q_speace/bcel/catalog.py`:
- **IoNT cellular node 4-layer advisory architecture (T236)** — `functional`
- **Biological cellular organism and DLT-driven motor reflex metaphor (T236)** — `accidental`
