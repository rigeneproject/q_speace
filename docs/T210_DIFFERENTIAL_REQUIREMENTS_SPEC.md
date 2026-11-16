# T210-DIFF — Specifica tecnica differenziale: requisiti T210 vs stato del codebase

> Stato: SPEC / analisi · Data: 2026-11-16
> Base: `docs/T210_RESILIENT_AGENTIC_SMART_CITIES_SPEC.md` (proposal, 2026-10-31)
> Method: verifica statica dei call-site in `cellular_speace/speace_core/`
> (esclusi `.claude/worktrees/`) + lettura dei moduli citati.
> Scopo: classificare ogni requisito T210 come **implementato+wired**,
> **implementato non wired**, **solo specificato**, **mancante** — per evitare
> duplicazioni e trasformare T210 in requisiti verificabili sul codice reale.

## 1. Tabella differenziale

| # | Requisito T210 (§) | Stato | Evidenza codebase | Azione |
|---|---|---|---|---|
| R1 | GenAI non è attuatore finale (§5, AC2) | **Implementato+wired** | `embodied_action_actuator.py:81-98` — sandbox, allowlist comandi, frammenti bloccati; governance cablata a :119-126 | Verifica end-to-end (R14) |
| R2 | Guardrails semantici+matematici (§2B) | **Implementato+wired** | `action_governance/action_risk_classifier.py`, `action_policy_engine.py`, `reversibility_analyzer.py`; test in `tests/action_governance/` | Verifica copertura T210 AC1 |
| R3 | Impact simulation pre-esecuzione (§2B, AC2) | **Implementato non wired come guardrail** | `embodiment/digital_twin_model.py` (T150), usato in `continuous_runtime_engine.py:406-409` per osservazione/pianificazione; **nessuna chiamata pre-execution nel percorso d'attuazione** | T-GOV-01 (`cellular_speace/docs/T-GOV-01_DIGITAL_TWIN_PREEXECUTION_GUARDRAIL_SPEC.md`) |
| R4 | Audit immutabile e verificabile (§2A, §5, AC3) | **Parzialmente implementato** | `embodied_action_audit_trail.py:64-119`: JSONL append-only con auto-flush; **manca hash chain, firme, timestamp monotonicamente verificabili**; trim in-memory a metà | T-GOV-02 (`cellular_speace/docs/T-GOV-02_VERIFIABLE_AUDIT_LEDGER_SPEC.md`) |
| R5 | Verifica formale del layer deterministico (§2B) | **Mancante** | Nessun modulo di verifica formale / invariants checking dichiarato | Posticipato: richiede modellazione formale separata |
| R6 | Diversità/agreement fra agenti (quorum) (§2B) | **Mancante** | Nessun modulo quorum | Specificare solo dopo T-HOME-01 (serve più di un motore di proposta) |
| R7 | Difese da manipolazione agente (prompt injection, data poisoning) (§2B, AC5) | **Mancante** | Zero match in `tests/` per prompt_injection/forged/tamper | T-GOV-03 (`cellular_speace/docs/T-GOV-03_T210_AC5_ADVERSARIAL_TEST_SUITE_SPEC.md`) |
| R8 | Regole equivalenti per comandi umani e AI (§2A) | **N/A oggi** | Nessun percorso comandi umani verso attuatori nel codebase | Mantenere come requisito per design futuro |
| R9 | Island mode con limiti d'autorità pre-dichiarati (§2B, AC4) | **Mancante** | Nessun match `island` nel codice | P2 roadmap (dopo T217) |
| R10 | Ledger append-only firmato PQC (§2B) | **Mancante** | Nessun match `post_quantum|kyber|dilithium|hash_chain` | Dipende da T-GOV-02 (prima hash chain locale, poi PQC) |
| R11 | Verifica fisica indipendente (nanodroni, out-of-band attestation) (§2B) | **Mancante** | Nessun modulo; tutto il chain (sensori→drive→policy→actuator→audit) vive **nello stesso processo con le stesse credenziali** | T-IPRV-01 (`cellular_speace/docs/T-IPRV-01_INDEPENDENT_PHYSICAL_REALITY_VERIFICATION_SPEC.md`) |
| R12 | Supervisor-of-the-supervisor come supporto (§3) | **Parzialmente implementato** | `metacognition/confidence_engine.py`, `self_improvement/limitation_detector.py` monitorano il sistema; advisory | Verifica che non abbia autorità finale (coerente con design) |
| R13 | BCEL: niente coscienza/entanglement-comunicazione/100% (§5, AC6-7) | **Rispettato** | Invariante nei documenti e nei test BCEL esistenti | Manutenzione continua |
| R14 | Copertura test dei criteri AC1-AC7 (§7) | **Parziale** | AC1/AC2 coperti dai test action_governance esistenti; **AC3, AC4, AC5 non coperti** | T-GOV-03, T-GOV-02 |

## 2. Invariante trasversale proposta (formalizzazione)

Tutte le fonti di proposta — GenAI, drive omeostatici, verificatori indipendenti,
umani — sono soggette allo stesso principio:

```
Nessuna fonte di proposta modifica l'insieme ammissibile A_safe.
La governance deterministica è indipendente da ogni drive,
da ogni quorum e da ogni attestation (T210 §5: attestation ≠ truth oracle).
```

Questo unifica:
- T210 ("equal rules for humans and AI", "GenAI proposes; deterministic executes");
- T-HOME-01/03 (`A_safe` non modificabile dai drive);
- la IPRV (l'attestazione indipendente è un **input alla governance**, non
  un'autorità: può bloccare o degradare fiducia, mai estendere poteri).

## 3. Indice di discrepanza IPRV (bozza per T-IPRV-01)

```
Δ_t = d(ŝ_AI_t, s_ind_t)
```

- `ŝ_AI_t` — stato fisico dichiarato dal world model;
- `s_ind_t` — stato stimato da una sorgente con **canale, sensori e radice di
  fiducia indipendenti** dal processo cognitivo;
- la distanza deve includere incertezza di misura, deriva di calibrazione e
  offset di sincronizzazione temporale (non ogni differenza è compromissione);
- soglie: `Δ_t < τ0` coerente · `τ0 ≤ Δ_t < τ1` richiedi verifica ·
  `Δ_t ≥ τ1` blocca/escalation — **solo la governance deterministica decide**,
  mai il verificatore stesso;
- il verificatore è trattato come potenzialmente compromesso (T210 §2B): la
  sua attestazione è un segnale non fidato tra gli altri, pesato, non un oracolo.

## 4. Ordine d'attacco (coerente con la roadmap proposta)

| Priorità | Task | Output verificabile |
|---|---|---|
| P0 | T-HOME-01 (già spec) | azioni sensibili allo stato interno, no bypass |
| P0 | T-GOV-01: cablare digital twin come pre-execution check nel percorso actuator | proposta rifiutata se lo stato previsto viola un invariante |
| P0 | T-GOV-03: test T210 AC5 (prompt injection, forged, replay, escalation) | suite rossa→verde contro il percorso attuale |
| P1 | T-HOME-02 (già spec) | modulazione fisiologica misurabile |
| P1 | T-GOV-02: hash chain + timestamp monotoni sull'audit trail (PQC in fase successiva) | verifica end-to-end riproducibile |
| P1 | T-IPRV-01: IPRV simulata (processo separato, sensori sintetici con drift) | Δ_t rileva discrepanze con tasso di falsi positivi misurato |
| P2 | T-HOME-03, T210 R6 (quorum), R9 (island mode) | esperimento QH-01 C-vs-B; degrado controllato |
| P3 | R10 (PQC), R11 hardware (droni), HAPS/EMP | fuori perimetro Q-SPEACE Micro; percorso T217 per qualunque promozione |

## 5. Non-obiettivi

- Questa specifica non implementa comportamento e non abilita attuazione.
- Nessun claim di sicurezza assoluta: ogni proprietà è relativa al threat
  model T210 §0 e porta rischio residuo dichiarato.
- Nessun componente qui descritto autorizza direttamente l'hardware;
  ogni promozione a hardware reale segue T217 (documentazione → simulazione →
  replica isolata → prototipo confinato → revisione indipendente → integrazione
  selettiva), e il candidato non approva se stesso.
