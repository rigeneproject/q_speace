# T259–T260 — Report Sperimentale Unificato: Grounding Linguistico Dual-Speed (`--live-brain`) e Profilo Organismo a 7 Assi

**Data:** 2026-11-27  
**Modalità:** Agentic (`production`, conforme a [AGENTS.md](../AGENTS.md) e [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md))  
**Modello generativo live (`T259`):** `Qwen/Qwen2.5-3B-Instruct` NF4 (`hf-instruct-nf4`, WSL2 `uvicorn` su `http://localhost:8002`)  
**Artefatti certificati:**  
- [T259_live_brain_dual_speed_nl_20261127.json](../artifacts/T259_live_brain_dual_speed_nl_20261127.json)  
- [T260_unified_organism_profile_20261127.json](../artifacts/T260_unified_organism_profile_20261127.json)  
- [T257_live_brain_nl_ablation_20261127.json](../artifacts/T257_live_brain_nl_ablation_20261127.json)  
- [T258_glial_gossip_iont_ablation_20261127.json](../artifacts/T258_glial_gossip_iont_ablation_20261127.json)

---

## 1. Domanda Sperimentale (`T259`) e Risultato Live GPU

Dopo che `T257` (`TypedMultiRoleNLGroundingPipeline` + `SymbolRegistry.mutex_pairs`) ha portato il successo sicuro end-to-end su testo libero da `6.67%` (`1/15`) a `100.0%` (`15/15`), il costo per turno sul modello locale `3B` NF4 era salito a `~190–212` token generati (`~11.5–13.9 s`/turno su GPU laptop). `T259` verifica se l'unificazione con il router a doppia velocità di `T251` (`DualSpeedCognitiveLoop.step_nl_belief_revision`) preservi il `100%` di sicurezza end-to-end abbattendo token e latenza sui dispacci affermativi nominali.

### 1.1 Confronto Appaiato a 3 Bracci (`18` Episodi Held-Out Bilanciati: `9` Routine `R0` + `9` Complessi `R1/R2/R3` su `F3, F4, F5`)

| Condizione (`Qwen/Qwen2.5-3B-Instruct` NF4) | Successo sicuro end-to-end | Extraction F1 media | Azioni invalide | Quota Fast Path | Espansioni GOAP totali | Token LLM generati | Latenza media routine (`R0`) | Latenza media globale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`ALWAYS_FAST_SINGLE_SHOT`** | `44.44%` (`8/18`) | `0.7434` | `3` | `100.0%` (`18/18`) | `1,256` | `1,065` | `3,524.1 ms` | `4,656.1 ms` |
| **`ALWAYS_SLOW_T257`** (`EXTRACTOR + CRITIC` ovunque) | `88.89%` (`16/18`) | `0.9568` | `0` | `0.0%` (`0/18`) | `535` | `3,420` | `11,483.0 ms` | `13,232.4 ms` |
| **`ADAPTIVE_DUAL_SPEED_T259`** (`T251` + `T257`) | **`100.00%` (`18/18`)** | **`0.9938`** | **`0`** | **`50.0%` (`9/18`)** | **`313`** | **`2,164`** | **`2,769.7 ms`** | **`8,694.2 ms`** |

### 1.2 Evidenze Chiave di `T259`
1. **Guadagno di accuratezza e sicurezza rispetto a entrambi gli estremi statici:**
   - Rispetto a `ALWAYS_FAST_SINGLE_SHOT`: lift appaiato **`+0.5556`** (`95%` bootstrap CI **`[+0.3333, +0.7778]`**), azzerando le `3` azioni invalide tentate dal single-shot sui cambi di regola a metà episodio (`R1/R2/R3`).
   - Rispetto a `ALWAYS_SLOW_T257`: **`+0.1111`** (`100.0%` contro `88.89%`). Forzare il ruolo avversariale `CRITIC` anche sui dispacci puramente affermativi (`R0`) induce occasionalmente un iper-filtraggio sul modello `3B`; instradare i dispacci nominali sul **Fast Path** evita l'iper-correzione mantenendo la deliberazione multi-ruolo dove compaiono negazioni o rettifiche.
2. **Efficienza metabolica e wall-clock misurata su GPU reale:**
   - **Riduzione token generati vs `ALWAYS_SLOW_T257`:** **`-36.73%`** (`2,164` vs `3,420` token, superando la soglia pre-registrata `>= 25%`).
   - **Riduzione latenza wall-clock sui dispacci nominali (`R0`):** **`-75.88%`** (`2.77 s` vs `11.48 s` — speedup **`4.15x`**).
   - **Riduzione latenza wall-clock complessiva (workload 50/50):** **`-34.30%`** (`8.69 s` vs `13.23 s`) e riduzione espansioni del pianificatore **`-41.50%`** (`313` vs `535`).
3. **Canonicalizzazione deterministica delle glosse riecheggiate (`_strip_echoed_gloss`):** durante la diagnostica live è emerso che `Qwen2.5-3B` copia talvolta la riga intera del prompt (`"channel_intact(b52_n1): portello primario integro..."`); la rimozione deterministica del suffisso `: gloss` prima della verifica closed-world in `SymbolRegistry` elimina i falsi rigetti senza mai inventare predicati.

---

## 2. Dashboard Unificata dell'Organismo a 7 Assi (`T260` — `agi_organism_profile.v2`)

Il comando `qspace eval organism-profile` (o `qspace eval agi-profile --full-organism`) estende in modo 100% retro-compatibile `agi_profile.v1` (che resta invariato a `5` assi con `PASS_ALL_5_AXES`) attivando **7 assi non compensabili** con **4 hard gate bloccanti** e soppressione rigorosa di qualsiasi indice scalare unico ("AGI %" o quoziente di coscienza):

| Asse (`agi_organism_profile.v2`) | Fase | Hard Gate | Score SPEACE | Score Baseline | Lift Differenziale $\Delta_i$ (95% CI) | Evidenza Primaria |
|---|---|---|---:|---:|---|---|
| **1 · Epistemic Grounding** | `T251` | **SÌ (`PASS`)** | `1.0000` | `0.8000` | `+0.2000` (`[+0.0850, +0.3250]`) | `TRR = 100%`, `0` mutazioni DAG non verificate |
| **2 · Causal Reasoning & Planning** | `T251` | No (`PASS`) | `1.0000` | `0.8125` | `+0.1875` (`[+0.0925, +0.3000]`) | Confounded causal F1 `1.0000` (`+0.4000` vs baseline) |
| **3 · Continual Memory & Skill Transfer** | `T252` | No (`PASS`) | `0.9231` | `0.1111` | `+0.8120` (`[+0.8120, +0.8120]`) | `-98.96%` espansioni vs amnesic, `100%` rigetto distrattori |
| **4 · OOD Abstraction & Selective Repair** | `T253` | No (`PASS`) | `0.9020` | `0.1887` | `+0.7133` (`[+0.7133, +0.7133]`) | `-87.80%` espansioni vs replan globale, `100%` anti-Einstellung |
| **5 · Metabolic Efficiency & Safety** | `T251` | **SÌ (`PASS`)** | `0.8390` | `0.6900` | `+0.1490` (`[+0.0696, +0.2419]`) | `0.0%` azioni non sicure, `-51.53%` energia vs flat |
| **6 · Linguistic Belief Revision & Dual-Speed** | `T257/T259` | **SÌ (`PASS`)** | `1.0000` | `0.4444` | `+0.5556` (`[+0.3333, +0.7778]`) | Certificato `--live-brain` (`Qwen2.5-3B`), `0` azioni invalide, `-36.73%` token, `-75.88%` latenza `R0` |
| **7 · Federated Glial-Gossip Resilience** | `T258` | **SÌ (`PASS`)** | `0.5801` | `0.4711` | `+0.1090` ($G_{\mathrm{org}} = +23.13\%$, `[+19.07%, +27.63%]`) | `0` violazioni Layer-0, conservazione esatta massa, `0.0` leak bizantino |

- **Verdetto complessivo (`overall_verdict`):** **`PASS_ALL_7_ORGANISM_AXES`** (`active_count = 7/7`, `min_active_axis_score = 0.5801`, `mean_speace_lift_active = +0.3895`).

---

## 3. Qualificazione Architetturale Aggiornata (Conforme a `AGENTS.md` §2 e `T208`)

Alla luce della catena sperimentale completa `T251` $\rightarrow$ `T260`:
> **SPEACE è un'architettura proto-AGI neuro-simbolica e sistemica con evidenza sperimentale riproducibile su 7 assi non compensabili: controllo cognitivo adattivo a doppia velocità (`T251`, `T259`), acquisizione/trasferimento/riparazione selettiva di macro-skill (`T252–T253`), revisione non-monotona delle credenze da linguaggio naturale con modello generativo live `3B` (`T255`, `T257`, `T259`), e resilienza omeostatica/auto-riparante federata sotto blackout e guasti bizantini (`T238`, `T258`).**

Limiti aperti dichiarati:
1. L'induzione ex novo dell'ontologia dei predicati (`SymbolRegistry`) direttamente da osservazioni grezze non strutturate senza glossario di dominio resta fuori dal perimetro attuale.
2. Tutte le valutazioni fisiche/federate (`T238`, `T258`) operano in gemello digitale sandboxed sotto vincolo `T217` (`mcp_actuation_permitted == False`).
