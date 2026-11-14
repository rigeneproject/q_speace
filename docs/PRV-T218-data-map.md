# PRV-T218 — Mappa dati e privacy del dataset dimostrativo (T218-T12, PRV-01)

**Stato:** nessun dato umano reale nel ciclo; dataset sintetico.
**Riferimenti:** `T218_QSPEACE_V0_BRIDGE_SPEC.md` §8.3; peer review G5.

## 1 Inventario dati

| Dato | Origine | Granularità | Retention | Accesso |
|---|---|---|---|---|
| Serie SoC/load/solar sintetiche | generatore seed 20261114 | 1 min, per cella | durata ciclo | team, auditori |
| Journal aggiornamenti | `UpdateLedger` | per proposta | permanente (registro) | auditori, policy owner |
| Etichette suite H2 | `validator_labels.py` | per caso | permanente | team |
| Metriche traiettoria | `TrajectoryMetrics` | per braccio | permanente | team, auditori |

## 2 Flussi verso l'esterno

- Nessun dato lascia il repository nel ciclo v0.
- Nel pilota (futuro): i canali grezzi NON lasciano la cella; solo aggregati dichiarati; gli auditori accedono via interfaccia separata con log degli accessi.

## 3 Test di ricostruzione/linkage

Richiesto prima del pilota con dati umani: tentativo di ricostruzione di routine da serie di consumo + log richieste sul dataset dimostrativo, con risultati e limiti espliciti (G5). Esito: documento di valutazione utilità/privacy.

## 4 Differential privacy

Applicabile solo con unità protetta, meccanismo, budget e composizione dichiarati; mai sui segnali di controllo (spec §3.4: non invalidare silenziosamente le stime di sicurezza).

## 5 Cancellazione e accessi d'emergenza

- Cancellazione: il journal degli aggiornamenti è registro di audit e non è cancellabile; i dati di telemetria sintetica sono eliminabili su richiesta del policy owner con nota nel registro.
- Accesso d'emergenza: solo lettura, doppia firma safety officer + auditore, tracciato nel journal.
