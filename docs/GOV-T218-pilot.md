# GOV-T218 — Contratto di governance del pilota (T218-T12, GOV-01)

**Stato:** contratto minimo compilato per il dominio microrete; nessuna legittimità politica è derivata da formule o punteggi (Art. V carta Revised).
**Riferimenti:** `T218_QSPEACE_V0_BRIDGE_SPEC.md` §8; peer review G1/G3/G6.

## 1 Ruoli e competenze

| Ruolo | Competenze | Non può |
|---|---|---|
| Policy owner | versiona `P_i`, soglie di servizio, pesi α/β | eseguire attivazioni degli aggiornamenti |
| Safety officer | doppia firma su aggiornamenti del validatore; dichiarazione dei modelli di guasto | modificare `P_i` da solo |
| Operatore di cella | gestione locale, richiesta fallback | auto-approvare proprie proposte fuori policy |
| Rappresentante interessati | ricorsi, veto su categoria "decisioni non delegabili" | modificare il validatore |
| Auditore esterno | accesso in lettura ai registri | esecuzione |

## 2 Categorie di decisioni non delegabili a formule

1. Pesi α/β e normalizzazioni del punteggio (`ScorePolicy`).
2. Soglie di servizio protetto e riserve minime.
3. Perdono/quarantena definitiva di una cella (oltre il tempo dichiarato).
4. Modifica di questo contratto.

## 3 Conflitti tra autorità (G1)

Precedenza dichiarata: **sicurezza fisica > servizio protetto > obiettivi economici**.
Con decisioni incompatibili tra celle (es. due quote protette durante carenza):
- autorità di risoluzione: policy owner, con decisione motivata entro **48 h**;
- regola provvisoria durante ricorso: ripartizione proporzionale dichiarata nel contratto di dominio (nessuna interruzione del servizio protetto);
- ricorso: entro 7 giorni, al collegio policy owner + rappresentante interessati + auditore.

## 4 Emergenze e scarsità (C5, G1)

- Potere d'emergenza: bounded scope, scadenza automatica ≤ 72 h, riesame obbligatorio.
- Infeasibilità (domanda > capacità): procedura dichiarata di ripartizione + escalation al policy owner; **mai** taglio silenzioso dei necessari a una popolazione per dato contestato (§9 Revised).

## 5 Ammissione e quarantena (G3)

- Membership: registro firmato dal policy owner; ammissione con doppia firma.
- Rilevazione anomalia ≠ attribuzione ≠ contenimento: ruoli e canali distinti.
- Quarantena: durata ≤ 24 h rinnovabile con decisione motivata; revoca documentata; canale di ricorso attivo durante la quarantena; il servizio protetto resta garantito via interfaccia sicura dove feasible.
- Falsa accusa: test di esercitazione obbligatorio (§7); tasso di falso isolamento riportato.

## 6 Esercitazioni obbligatorie prima del pilota

| Esercitazione | Esito richiesto |
|---|---|
| Conflitto due celle + carenza inevitabile | decisione motivata entro 48 h, traccia dell'autorità, gestione sotto-floor |
| Falsa accusa di una cella onesta | quarantena revocata entro il tempo dichiarato, tasso di falso isolamento registrato |
| Compromissione account di manutenzione | nessuna attuazione fuori `P_i`; modifiche residue enumerate (C4/G2) |

## 7 Matrice requisito → procedura → evidenza → responsabile

| Requisito | Procedura | Evidenza | Responsabile |
|---|---|---|---|
| GOV-01 contratto compilato | questo documento | hash nel repo | policy owner |
| G1 conflitto | esercitazione §6.1 | verbale + tempi | safety officer |
| G3 falsa accusa | esercitazione §6.2 | registro quarantene | operatore |
| G2 compromissione | esercitazione §6.3 | matrice privilegi-guasto | auditore |
| G6 no gate da punteggio | regola §8 | checklist gate | policy owner |

## 8 Nessun gate chiuso da un punteggio

Nessun gate (tecnico o istituzionale) è chiuso solo dal segno di `U` o da un test di prestazione positivo. I gate tecnici sono elencati nella matrice di conformità T218; i gate istituzionali richiedono decisione motivata registrata.

La mappa dati e privacy del dataset dimostrativo è nell'artefatto separato `PRV-T218-data-map.md` (PRV-01).
