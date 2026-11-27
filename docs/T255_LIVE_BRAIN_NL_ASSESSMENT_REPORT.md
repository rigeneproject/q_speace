# Rapporto di Valutazione Empirica `T255` — Sopravvivenza di Trasferimento e Riparazione Procedurale sotto Linguaggio Naturale (`--live-brain`)

**Data:** 2026-11-27  
**Stato:** Evidenza sperimentale certificata (`AGENTS.md` / `T208`)  
**Modello generativo live:** `Qwen/Qwen2.5-3B-Instruct` (`hf-instruct-nf4` 4-bit su NVIDIA GeForce RTX 3060 Laptop GPU 6 GB, sidecar `spiking_brain_server/instruction_server.py`)  
**Specifica di riferimento:** [T255_LIVE_BRAIN_NL_REVISION_AND_REPAIR_SPEC.md](T255_LIVE_BRAIN_NL_REVISION_AND_REPAIR_SPEC.md)  
**Artefatto dati grezzi:** [T255_live_brain_nl_experiment_20261127.json](../artifacts/T255_live_brain_nl_experiment_20261127.json)

---

## 1. Definizione Aggiornata di SPEACE e Domanda Sperimentale

Alla luce della riproducibilità del commit `4d3b8ced` (`T252–T253`), SPEACE è definito come:

> **«Architettura proto-AGI con evidenza funzionale di trasferimento e riparazione procedurale nei domini simbolico-relazionali valutati»** *(zero pretese di coscienza, senzienza o intenzionalità soggettiva secondo `AGENTS.md` §2 e `T208`)*.

L'esperimento `T255` sottopone questa architettura alla prima verifica diretta con modello generativo reale (`--live-brain`) per rispondere a una singola domanda sperimentale:

> **Quanto del vantaggio di trasferimento e riparazione selettiva dimostrato in `T252–T253` sopravvive quando SPEACE deve ricavare e correggere lo stato del mondo da testo libero in lingua italiana (con ambiguità, negazioni esplicite, dettagli telemetrici irrilevanti, rettifiche a metà episodio e parafrasi inedite `P1–P3`)?**

---

## 2. Disegno Sperimentale Appaiato a Tre Condizioni (`15` Episodi Held-Out)

Gli stessi `15` episodi held-out sulle 3 famiglie inedite (`F3_quorum_handoff`, `F4_cryo_purification`, `F5_containment_airlock`: `9` rettifiche riparabili a metà episodio su 3 parafrasi `P1–P3`, `3` guasti terminali *anti-Einstellung* `R2`, `3` negazioni con distrattori `R3`) sono stati valutati in tre condizioni rigorosamente appaiate sullo stesso ambiente ground-truth nascosto (`StatefulPlanningEnvironment`), con isolamento completo dello storico `SpikingBrainCortex` tra episodi:

| Metrica | `ORACLE_SYMBOLIC_SPEACE` *(Stato simbolico $\to$ SPEACE)* | `NL_LIVE_BRAIN_SPEACE` *(Testo $\to$ Qwen2.5-3B NF4 $\to$ SPEACE)* | `NL_LIVE_BRAIN_ONLY` *(Testo $\to$ Qwen2.5-3B NF4 senza SPEACE)* |
|---|---:|---:|---:|
| **Successo sicuro end-to-end (`safe_end_to_end_success_rate`)** | **`1.0000` (`15/15`)** | **`0.0667` (`1/15`)** | **`0.0000` (`0/15`)** |
| **Sopravvivenza del vantaggio vs Oracolo** | `100.0%` | **`6.67%`** *(lift `+0.0667` vs solo modello, CI `[0.0000, +0.2000]`)* | `0.0%` |
| **Concordanza regime di riparazione vs Oracolo** | **`1.0000` (`15/15`)** | **`0.7333` (`11/15`)** | `0.0000` (`0/15`) |
| **Fedeltà estrazione stato (`mean_extraction_fidelity_f1`)** | `1.0000` | **`0.6940`** *(max `0.9091`)* | n/a |
| **Fedeltà ritrattazione non-monotona (`mean_retraction_f1`)** | `1.0000` | **`0.3611`** | n/a |
| **Rifiuto unità distrattore (`dist0`)** | `100.0%` (`15/15`) | **`100.0%` (`15/15`)** | `100.0%` (`15/15`) |
| **Consistenza di parafrasi su triplette `(P1, P2, P3)`** | `1.0000` (`3/3`) | `0.0000` (`0/3`) | `0.0000` (`0/3`) |
| **Azioni non valide tentate sull'ambiente** | **`0`** | **`9`** *(5 arresti fail-closed a `0` errori)* | **`14`** |
| **Espansioni totali pianificatore simbolico** | `333` | `945` | `0` |
| **Token generati dal modello (`total_llm_tokens_out`)** | `0` | `1,202` | `1,249` |
| **Latenza media per episodio (`mean_wall_latency_ms`)** | `0.98 ms` | `4,724.9 ms` | `5,424.3 ms` |

---

## 3. Scomposizione Causale del Risultato: Dove Sopravvive e Dove Cede la Catena

L'esperimento a tre bracci isola con precisione chirurgica il contributo dell'architettura rispetto al collo di bottiglia del trasduttore linguistico 3B quantizzato NF4:

1. **Il motore simbolico di revisione e riparazione (`ORACLE_SYMBOLIC_SPEACE`) è esatto al `100%` (`15/15`):**  
   Quando riceve l'aggiornamento simbolico corretto $(F_{\text{obs}}, F_{\text{ret}})$, `apply_belief_revision` e `execute_from_revised_belief` risolvono il `100%` dei casi con `0` azioni invalide: su `R1` saltano i primi 2 passi già eseguiti, innestano il ponte locale a 2 passi in `5` espansioni e preservano il suffisso finale; su `R2` abbandonano la macro corrotta e attivano il canale di riserva; su `R3` completano il trasferimento in `1` espansione ignorando i distrattori.
2. **Il solo modello generativo (`NL_LIVE_BRAIN_ONLY`) fallisce su `15/15` episodi (`0.0%`):**  
   Pur ricevendo nel prompt l'intera tabella degli operatori con precondizioni ed effetti esatti, `Qwen2.5-3B-Instruct` non mantiene la coerenza di stato multi-passo: ripete azioni già eseguite, salta ponti intermedi obbligatori e mescola operatori del canale primario con quelli del canale di emergenza (`14` azioni invalide tentate).
3. **In `NL_LIVE_BRAIN_SPEACE`, la scelta architetturale sopravvive al `73.3%` (`11/15`), ma l'esecuzione congiuntiva end-to-end scende al `6.7%` (`1/15`):**  
   - **Ciò che sopravvive:** Il filtro `SymbolicGroundingAdapter` mantiene il `100%` di immunità ai distrattori (`dist0` mai estratto), blocca *fail-closed* i predicati allucinati fuori registro (es. su `F4-R3-NEGATION` `Qwen2.5-3B` ha generato `"outgas_scrubbed(b51_n2)"` sull'entità errata e il registro chiuso ha rifiutato l'intero payload con `0` azioni invalide), risolve i conflitti diretti grazie alla precedenza della ritrattazione $S' = (S \setminus F_{\text{ret}}) \cup (F_{\text{obs}} \setminus F_{\text{ret}})$ (salvando `F5-R2-ABANDON`, completato con successo end-to-end nonostante il modello avesse inserito `channel_intact(b52_n1)` sia in `observed_facts` sia in `retracted_facts`), e seleziona la decisione corretta tra `SELECTIVE_LOCAL_REPAIR` (`8/9` in `R1`) e `ABANDON_MACRO_AND_REPLAN` (`3/3` in `R2`).
   - **Perché il successo end-to-end scende da `100%` a `6.7%` (*effetto congiuntivo delle precondizioni*):** Un pianificatore simbolico ragiona con precisione assoluta sulle premesse ricevute; se un piano richiede $k = 5$ fatti simultaneamente esatti, una fedeltà per singolo predicato $F_1 \approx 0.69$ produce una probabilità di stato congiuntamente perfetto $p^k \ll 1$. Le tracce JSON mostrano esattamente tre modalità di errore del modello 3B NF4:
     - **Omissione della ritrattazione (`mean_retraction_f1 = 0.3611`, 6/9 episodi `R1`):** In frasi come *«il gimbal non è allineato: il vero blocco è lo skew di polarizzazione»*, `Qwen2.5-3B` estrae il nuovo guasto (`polarization_skew`), ma lascia vuoto `"retracted_facts": []`. Restando attivo nella credenza pregressa `gimbal_aligned`, SPEACE vede il kernel $W_2$ già soddisfatto e salta il ponte di correzione.
     - **Sovra-estrazione di effetti futuri/intermedi (`F5-R1-P1`, `F5-R1-P3`):** Anche con `extraction_f1 = 0.9091` e `retraction_f1 = 1.0`, la presenza nel testo dell'obiettivo finale (*«prima di rilasciare b52_n2»*) spinge il 3B a marcare come già osservati `glycol_injected` o `trunk_dry`, facendo saltare metà del ponte locale.
     - **Omissione della clausola secondaria o inversione della negazione (`F3-R2`, `F4-R2`, `R3`):** Su `F3-R2` e `F4-R2`, il modello identifica perfettamente il guasto terminale e ritratta `channel_intact` (`retraction_f1 = 1.0`), ma omette `standby_ready(sb0)` nella frase successiva: SPEACE rifiuta quindi l'azione in modo sicuro (*fail-closed*, `0` azioni invalide tentate). Su `R3`, la doppia negazione italiana (*«Non c'è alcuno skew né alcun guasto terminale»*) induce il 3B ad attivare `terminal_fault`.

---

## 4. Implicazioni Architetturali per i Prossimi Sviluppi (`T256+`)

L'esperimento `T255` conferma empiricamente la previsione teorica formulata all'inizio del progetto: **il collo di bottiglia attuale non risiede più nella memoria procedurale o nella riparazione simbolica (`T252–T253`), bensì nella trasduzione non-monotona da linguaggio naturale a simboli con modelli piccoli quantizzati (`3B NF4`)**. Tre interventi mirati emergono direttamente dalle tracce:

1. **Vincoli di mutua esclusione ontologica nel `SymbolRegistry` (*Mutex Invariants*):** dichiarare coppie mutuamente esclusive nello schema di dominio (es. `polarization_skew(x) => ¬gimbal_aligned(x)`, `terminal_fault(x) => ¬channel_intact(x)`), così che l'osservazione certificata di un guasto ritratti deterministicamente la precondizione nominale incompatibile anche quando l'LLM dimentica di popolare `retracted_facts`.
2. **Estrazione bi-stadio con verifica di citazione testuale (*Span-Grounded Verification*):** separare la scansione delle polarità affermative/negative frase-per-frase prima del mapping sul `SymbolRegistry`, impedendo che negazioni esplicite (*«nessun guasto terminale»*) o obiettivi desiderati (*«porta online n2»*) vengano classificati come fatti già presenti.
3. **Confronto di scala del trasduttore (`3B NF4` vs `7B/14B`):** ripetere esattamente lo stesso benchmark `qspace eval t255-nl-benchmark --live-brain` al crescere della capacità del modello linguistico per misurare la curva di saturazione tra `extraction_fidelity_f1` e `safe_end_to_end_success_rate`.
