# T-GOV-01 — Digital twin come pre-execution guardrail

> Stato: SPEC / non implementato · Priorità: P0 · Modalità: agentic
> Origine: `docs/T210_DIFFERENTIAL_REQUIREMENTS_SPEC.md` R3; T210 §2B/§7 AC2
> Base esistente: `embodiment/digital_twin_model.py` (T150)

## 1. Motivazione

`DigitalTwinModel` esiste ed è usato in `continuous_runtime_engine.py:406-409`
come strumento di osservazione/pianificazione, ma **non come verifica
pre-esecuzione** nel percorso d'attuazione. T210 richiede che ogni comando
critico passi da una simulazione d'impatto prima dell'esecuzione:
"Pre-execution check of the resulting state against declared invariants"
(BCEL §5, functional).

## 2. Obiettivo

Inserire un check digitale del twin tra la proposta e la proposta-approvata nel
percorso `EmbodiedActionActuator.propose_action`, senza modificare la
governance deterministica né i suoi motori.

```
proposta → risk classifier → policy engine → [NOVO] impact check sul twin
        → approvazione / veto → sandbox esecuzione → audit
```

## 3. Design

- Il twin predice lo stato risultante previsto dell'azione (estendendo
  `predict`/trace già presenti, `digital_twin_model.py:108`).
- Un set di invarianti dichiarate (stesso sorgente di verità della policy
  engine, non duplicato) è valutato sullo stato previsto.
- Esito: `pass` / `reject(reason=invariant_id)` / `unverifiable(model_gap)`.
  `unverifiable` non approva di default: follow configurabile (rifiuto
  conservativo o escalation umana).
- Il check è registrato nell'audit con l'invariante valutata e lo stato
  previsto (tracciabilità della decisione).
- Costo computazionale: budget di latenza per proposta; se il twin non è
  disponibile il check degrada a rifiuto conservativo, mai a bypass.

## 4. Invarianti

- Il twin non estende mai l'insieme ammissibile `A_safe`: può solo confermare
  o rifiutare (coerente con l'invariante trasversale T210-DIFF §2).
- Nessun nuovo percorso d'attuazione; la governance resta l'ultima parola.

## 5. Criteri di accettazione

1. Una proposta che viola un invariante dichiarato è rifiutata dal check con
   motivo tracciato, a parità di policy engine (test deterministico).
2. Una proposta coerente con gli invarianti passa con esito `pass` registrato.
3. Twin assente/guasto → rifiuto conservativo + nota in audit, nessun bypass.
4. La latenza aggiunta per proposta è misurata e soggetta a budget
   configurato; superamento del budget → comportamento di degrado testato.
5. `pytest` sui percorsi toccati; nessuna regressione sui test
   `tests/action_governance/` esistenti.

## 6. Task checklist

- [ ] T-GOV-01.1 — spec review
- [ ] T-GOV-01.2 — estensione twin: predizione post-azione per i proposal
      kinds di `EmbodiedActionActuator`
- [ ] T-GOV-01.3 — valutatore invarianti condiviso con policy engine
- [ ] T-GOV-01.4 — integrazione nel percorso `propose_action` + audit record
- [ ] T-GOV-01.5 — test + budget latenza + degrado conservativo
