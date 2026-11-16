# T-GOV-02 — Audit ledger verificabile (hash chain + timestamp monotoni)

> Stato: SPEC / non implementato · Priorità: P1 · Modalità: agentic
> Origine: `docs/T210_DIFFERENTIAL_REQUIREMENTS_SPEC.md` R4, R10; T210 §2A, §7 AC3
> Base esistente: `embodiment/embodied_action_audit_trail.py`

## 1. Motivazione

`EmbodiedActionAuditTrail` è append-only JSONL con auto-flush
(`embodied_action_audit_trail.py:64-119`), ma **non è verificabile**:
- nessun hash chain fra entry;
- nessuna firma;
- `wall_time` non monotonicamente vincolato né attestato;
- trim in-memory (metà storico) senza contropartita persistente del vincolo.

T210 AC3 richiede "Audit records are append-only and verifiable end to end".
La classificazione BCEL (§5): "Append-only audit ledger — hash-chained records
with PQC signatures and monotonic timestamps" (functional).

## 2. Obiettivo

Rendere il trail verificabile end-to-end senza cambiare il formato semantico
delle entry (retrocompatibilità con i lettori esistenti).

## 3. Design

Per ogni entry:
```
h_t = SHA256(h_{t-1} ‖ canonical(entry_t))
seq_t = seq_{t-1} + 1          (monotonic, persistito)
```
- `canonical(entry)`: serializzazione deterministica (chiavi ordinate, float
  in formato fisso) — stesso principio di hashing canonico già adottato in
  T218 Bridge-v0.
- Il chain head corrente è esposto per confronto esterno (checkpoint periodico
  su file separato, append-only).
- Verificatore `verify_chain(log)`: ricalcola e segnala la prima entry
  manomessa o fuori sequenza.
- Firma: fase 1 nessuna firma (integrità locale); fase 2 firma del chain head
  a checkpoint (chiave gestita fuori dal processo cognitivo — indipendenza,
  coerente con T210-DIFF R11). PQC (fase 3) solo dopo fissata l'interfaccia di
  firma, con algoritmo da selezionare in fase di implementazione.
- Il trim in-memory resta (è solo vista), la catena persistita non è mai
  troncata.

## 4. Invarianti

- L'audit non è modificabile dal percorso cognitivo: append-only sul disco,
  verifica esterna possibile senza credenziali del processo.
- Nessun claim di inviolabilità assoluta: l'integrità è relativa al threat
  model (un attaccante con write access al disco può rifare la catena; la
  firma a checkpoint con chiave esterna ne alza il costo).

## 5. Criteri di accettazione

1. `verify_chain` su un log legittimo ritorna valido; su una singola entry
   alterata (valore, cancellazione, riordino) individua esattamente la prima
   entry corrotta (test parametrico).
2. Le entry pre-esistenti senza hash restano leggibili; il chain inizia dal
   primo entry nuovo con `prev_hash = GENESIS` dichiarato nel log.
3. Riavvio del processo: il chain riprende da `h_{t-1}` persistito senza
   rotture (test di restart).
4. Format JSONL retrocompatibile: i campi nuovi sono additivi.
5. `pytest` con suite dedicata; nessuna regressione sul loop embodied.

## 6. Task checklist

- [ ] T-GOV-02.1 — spec review
- [ ] T-GOV-02.2 — hashing canonico + chain nel trail
- [ ] T-GOV-02.3 — verificatore indipendente + checkpoint head
- [ ] T-GOV-02.4 — test manomissione parametrica + restart
- [ ] T-GOV-02.5 — interfaccia firma per fase 2/3 (PQC in fase separata)
