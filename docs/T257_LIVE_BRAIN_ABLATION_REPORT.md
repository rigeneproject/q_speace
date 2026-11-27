# Rapporto di Ablazione Empirica `T257` — Risoluzione Architetturale del Collo di Bottiglia `NL <-> Simboli` con le Primitive `T256` (`--live-brain`)

**Data:** 2026-11-27  
**Stato:** Evidenza sperimentale certificata (`AGENTS.md` / `T208`)  
**Modello generativo live (pesi invariati):** `Qwen/Qwen2.5-3B-Instruct` (`hf-instruct-nf4` 4-bit su NVIDIA GeForce RTX 3060 Laptop GPU 6 GB)  
**Specifica di riferimento:** [T257_TYPED_DAG_MULTI_ROLE_NL_GROUNDING_SPEC.md](T257_TYPED_DAG_MULTI_ROLE_NL_GROUNDING_SPEC.md)  
**Artefatto dati grezzi (4 bracci appaiati):** [T257_live_brain_nl_ablation_20261127.json](../artifacts/T257_live_brain_nl_ablation_20261127.json)

---

## 1. Domanda Sperimentale e Disegno Anti-Goodhart (`T208`)

In `T255` (`9bfbd345`) era emerso che con un modello piccolo quantizzato (`Qwen2.5-3B` NF4) il passaggio da simboli di riferimento a testo libero italiano riduceva il successo end-to-end dal `100.0%` (`15/15`) al `6.67%` (`1/15`), principalmente per omissione delle ritrattazioni (`retraction_f1 = 0.3611`), inversione delle doppie negazioni e sovra-estrazione di obiettivi futuri.

`T257` testa a **pesi del modello rigorosamente invariati (`Qwen2.5-3B` NF4)** e sugli **stessi 15 episodi held-out** (`F3`, `F4`, `F5`) se l'integrazione delle primitive `T256` (`BatchRoleDeliberationCodec`, `TypedComputationalDAG` + `ExecutionTicket`, `KineticaRegimeController`, `MyelinationRegistry`) con i vincoli ontologici `mutex_pairs` in `SymbolRegistry` e lo screening sintattico di clausola `ClausePolarityAuditor` recuperi il vantaggio di trasferimento e riparazione `T252–T253` **senza mai inventare alcun predicato non proposto dal modello generativo**.

---

## 2. Risultati dell'Ablazione a Quattro Condizioni Appaiate (`n = 15` Episodi Held-Out)

| Metrica | `ORACLE_SYMBOLIC_SPEACE` *(Riferimento simbolico)* | `NL_LIVE_BRAIN_ONLY` *(Solo Qwen2.5-3B)* | `NL_LIVE_BRAIN_SPEACE` *(`T255` single-shot)* | **`NL_LIVE_BRAIN_SPEACE_T257`** *(`T256`+`T257` Typed-DAG + Mutex)* |
|---|---:|---:|---:|---:|
| **Successo sicuro end-to-end (`safe_end_to_end_success_rate`)** | `1.0000` (`15/15`) | `0.0000` (`0/15`) | `0.0667` (`1/15`) | **`1.0000` (`15/15`)** |
| **Sopravvivenza del vantaggio vs Oracolo** | `100.0%` | `0.0%` | `6.67%` | **`100.0%`** |
| **Lift di successo `T257` vs `T255` (Bootstrap 95% CI)** | — | — | baseline | **`+0.9333` (`[+0.8000, +1.0000]`)** |
| **Lift di successo `T257` vs `NL_LIVE_BRAIN_ONLY`** | — | baseline | `+0.0667` | **`+1.0000` (`[+1.0000, +1.0000]`)** |
| **Fedeltà ritrattazione (`mean_retraction_f1`)** | `1.0000` | n/a | `0.3611` | **`1.0000`** *(lift `+0.6389`, CI `[+0.3889, +0.8611]`)* |
| **Fedeltà estrazione stato (`mean_extraction_fidelity_f1`)** | `1.0000` | n/a | `0.6940` | **`0.9444`** |
| **Concordanza regime di riparazione vs Oracolo** | `1.0000` (`15/15`) | `0.0000` (`0/15`) | `0.7333` (`11/15`) | **`1.0000` (`15/15`)** |
| **Consistenza su parafrasi inedite `(P1, P2, P3)`** | `1.0000` (`3/3`) | `0.0000` (`0/3`) | `0.0000` (`0/3`) | **`1.0000` (`3/3`)** |
| **Azioni invalide tentate sull'ambiente** | `0` | `14` | `9` | **`0`** |
| **Espansioni totali pianificatore GOAP** | `333` | `0` | `945` | **`338`** |
| **Latenza media / Token generati totali** | `1.0 ms` / `0` | `6,431.6 ms` / `1,249` | `5,681.9 ms` / `1,202` | `13,934.5 ms` / `3,177` |

---

## 3. Evidenza Meccanistica: Come Hanno Operato i Nodi `T256`–`T257` sulle Tracce Reali

Le tracce grezze in [T257_live_brain_nl_ablation_20261127.json](../artifacts/T257_live_brain_nl_ablation_20261127.json) mostrano il contributo distinto di ciascuno dei quattro stadi del `TypedComputationalDAG`:

1. **Recupero di recall multi-frase via `BatchRoleDeliberationCodec` (`decode_roles`):**  
   In `F3_quorum_handoff-R2-ABANDON` (e analogamente in `F4-R2`), la scansione esplicita `--- EXTRACTOR ---` ha spinto `Qwen2.5-3B` a estrarre sia `terminal_fault(b50_n1)` sia il fatto secondario `standby_ready(b50_sb0)` (che in `T255` veniva perso). Quando nella sezione `--- CRITIC ---` il modello 3B ha introdotto un refuso di tokenizzazione (`"standby_ready(b50_sbml0)"`), la fusione strutturata `EXTRACTOR + CRITIC` seguita dal filtro sul `SymbolRegistry` ha preservato l'atomo canonico `standby_ready(b50_sb0)` scartando il token corrotto.
2. **Eliminazione delle doppie negazioni e degli obiettivi futuri (`polarity_scope_audit`):**  
   In `F3_quorum_handoff-R3-NEGATION`, `Qwen2.5-3B` aveva comunque inserito `"terminal_fault(b50_n1)"` e il distrattore `"doppler_alert(b50_dist0)"` in `observed_facts`; `ClausePolarityAuditor` ha riconosciuto la finestra di negazione (*«né alcun guasto terminale»*) e la clausola di collaudo (*«da ignorare»*), ripulendo lo stato e consentendo il trasferimento nominale in `1` sola espansione (`NO_REPAIR_NEEDED`). Allo stesso modo ha rimosso gli effetti ponte non menzionati nel testo (es. `feedhorn_rotated`, `carrier_locked`).
3. **Chiusura deduttiva delle ritrattazioni via `SymbolRegistry.mutex_pairs` (`mutex_belief_revision`):**  
   In `F3_quorum_handoff-R1-P1` il modello 3B ha lasciato `"retracted_facts": []` vuoto pur avendo estratto `polarization_skew(b50_n1)` (e mantenuto per inerzia `gimbal_aligned(b50_n1)` in `observed_facts`). La regola algebrica $S_{\text{rev}} = (S_{\text{prior}} \setminus F_{\text{ret}}^{\star}) \cup (F_{\text{obs}} \setminus F_{\text{ret}}^{\star})$ con $F_{\text{ret}}^{\star}$ chiusa rispetto a `mutex_pairs` ha ritrattato deterministicamente `gimbal_aligned(b50_n1)`, innescando `SELECTIVE_LOCAL_REPAIR` (`rotate_feedhorn -> lock_carrier_pll -> handover_carrier -> illuminate_spot` in `5` espansioni) su tutte e 9 le parafrasi `P1–P3` (`paraphrase_consistency_rate = 1.0000`).
4. **Prova di assenza di *oracle leakage*:**  
   `mean_extraction_fidelity_f1` su `T257` è pari a **`0.9444`** (non `1.0000`): in un paio di parafrasi `R1` (es. `F3-R1-P3`) il modello 3B non ha estratto il fatto intermedio ridondante `uplink_muted(b50_n1)` già superato dal kernel $W_2$, e la pipeline non lo ha mai aggiunto artificialmente.

---

## 4. Compromesso Misurato (Costo / Latenza) e Aggiornamento Valutativo

- **Compromesso metabolico:** Il passaggio dal singolo JSON piatto (`T255`) al framing bi-ruolo `EXTRACTOR + CRITIC` (`T257`) porta i token generati da `1,202` a `3,177` (`~212` token/episodio) e la latenza su GPU laptop 4-bit da `5.7 s` a `13.9 s` per episodio, **riducendo però del `64.2%` le espansioni del pianificatore (`945 -> 338`) e azzerando le azioni invalide (`9 -> 0`)**. Unendo questo modulo al router a due velocità `T251` (`DualSpeedCognitiveLoop`), il costo del doppio ruolo viene pagato esclusivamente sui turni ad alta sorpresa o rettifica linguistica (*Slow Path*).
- **Valutazione aggiornata di SPEACE + `T256/T257`:** Con `T257`, le primitive `T256` (`TypedComputationalDAG`, `ExecutionTicket`, `BatchRoleDeliberationCodec`, `KineticaRegimeController`, `MyelinationRegistry`) passano da *libreria isolata* a **componenti architetturali validati sperimentalmente con lift differenziale certificato (`+93.3` punti percentuali su `--live-brain`)**, dimostrando che un'architettura neuro-simbolica ben vincolata può compensare gran parte dei limiti di trasduzione non-monotona di un piccolo modello `3B NF4`.
