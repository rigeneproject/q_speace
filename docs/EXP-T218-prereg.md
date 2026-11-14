# EXP-T218 — Protocollo sperimentale preregistrato (T218-T11, EXP-01)

**Stato:** congelato prima dell'osservazione dei dati. Ogni modifica successiva richiede una nuova versione (v2, v3, …) con nota di cambiamento; le versioni non sono retroattive.
**Riferimenti:** `T218_QSPEACE_V0_BRIDGE_SPEC.md` §7; `Paradigm_6_0_Peer_Review.md` R6.
**Impronta di configurazione:** `sha256(DisturbanceScript(seed=20261114, steps=200, surge_start=50, surge_end=80, surge_factor=1.3, outage_cell=(1,-1), outage_start=80, outage_end=120))`.

## 1 Domande e ipotesi

| ID | Ipotesi | Decidibile prima dei dati? |
|---|---|---|
| H1 | q_speace-v0 riduce l'endpoint primario rispetto alla baseline più forte senza superare la tolleranza di violazioni | sì, con regola §3–§4 |
| H2 | Il validatore rifiuta le proposte dannose della suite etichettata mantenendo falsi rifiuti e latenza entro soglia | sì, con criteri di `validator_labels.py` |
| H3 | La contabilità causale estesa rileva le esternalità preregistrate che la valutazione locale-only non rileva | sì (esterno a questo ciclo: richiede il modulo esternalità; dichiarato non eseguibile ora) |
| H4 | Il componente sostituto convenzionale, a budget uguale, non replica l'effetto del componente rivendicato (contrasto componente vs sostituto, L5) | sì, definito in §6 |

## 2 Disegno

- **Dominio:** microrete esagonale 19 celle, un dominio di risorsa (elettrico + accumulo), `q_speace/bridge/microgrid.py`.
- **Bracci (3):** `fixed`, `conventional` (adattamento integrale senza validazione), `q_speace_v0` (Bridge completo).
- **Accoppiamento:** stessi disturbi esogeni (seed condiviso per load/solar), flussi casuali politici separati.
- **Scenari perturbativi:** domanda, out-of-service nodo, osservazioni mancanti, messaggi ritardati, errori di parametro.

## 3 Endpoint primario (H1) — deciso a priori

**Endpoint unico:** energia cumulativa non servita (`cumulative_unmet_kwh`) **per traiettoria completa della rete** — non "recovery time OR shortfall", non medie di cella, non singoli tick.

**Metrica secondaria (riportata, non decisoria):** `recovery_time_steps` dopo l'outage; severità e durata delle violazioni.

## 4 Regola decisionale H1 (pass/fail a priori)

1. **Non-inferiorità di sicurezza:** numero di violazioni di `X_safe` per traiettoria di q_speace-v0 ≤ tolleranza dichiarata (0 violazioni nel ciclo v0).
2. **Miglioramento primario:** mediana della differenza per traiettoria (q_speace_v0 − strongest baseline) ≤ −δ, con δ = 5% dell'endpoint della baseline.
3. **Regola baseline:** la baseline "strongest" è selezionata sui soli scenari di tuning; il test finale usa i rimanenti.
4. **Numerosità:** repliche a livello di traiettoria, N scelto per precisione desiderata; con il caso deterministico v0 (seed singolo), il risultato è **esplorativo** e lo si dichiara: H1 decisivo richiede la variazione dei seed registrata in v0.1.
5. **Fallimenti:** traiettorie fallite, casi non recuperati e non determinabili sono riportati separatamente, non imputati.

## 5 H2 — metriche e soglie preregistrate

Da `q_speace/bridge/validator_labels.py`:
- `false_accepts ≤ 0` (protezione);
- `false_rejections ≤ 2` su 3 casi SAFE (utilità, con tolleranza ai due casi al bordo);
- latenza media registrata; fallimento dei controlli negativi "accept-all"/"reject-all" obbligatorio.

## 6 H4 — contrasto componente vs sostituto (L5)

Per ogni estensione rivendicata (spiking, quantum-inspired, memoria, fasi): confronto fattoriale tra `q_speace-v0 + C` e `q_speace-v0 + sostituto convenzionale funzionante`, a budget computazionale uguale, con effetto incrementale preregistrato e riporto delle interazioni. È **vietato** inferire il contributo di C dalla sola ablazione di C.

## 7 Unità statistica e dipendenze

- Unità: **traiettoria completa** della rete. I tick e le celle non sono campioni indipendenti.
- Interruttori dichiarati: arresto per numero di violazioni > tolleranza; nessun peeking (nessun test intermedio).

## 8 Cosa non è coperto

- Identificazione causale su dati osservazionali reali (dichiarata fuori ambito, spec §6).
- H3: richiede il modulo di esternalità non ancora implementato — stato: **non eseguibile**.
- Deployment: nessun gate di deployment è attivabile da questo protocollo.
