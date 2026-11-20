# T222 - Task registry: NCM codec, Fase 0

**Status:** registro di lavoro sperimentale. Companion di
`T222_NCM_CODEC_SPEC.md` e `T222_PREREG.json`.
**Data:** 2026-11-20.
**Ambito approvato:** sola Fase 0 (codec + calibrazione). Le Fasi 1-2 restano
future work non approvato.

Legenda: **DONE** = implementato e verificato; **PENDING** = autorizzato ma non
avviato; **BLOCKED** = dipende da un task non concluso; **NOT APPROVED** =
fuori dal perimetro approvato.

## Fase 0 - implementazione e calibrazione

| ID | Task | Dipende | Deliverable | Stato |
|---|---|---|---|---|
| T222-00 | Specifica Fase 0 e non-obiettivi | - | `T222_NCM_CODEC_SPEC.md` | DONE |
| T222-01 | Preregistrazione con sezioni separate | T222-00 | `T222_PREREG.json` (bozza) | DONE |
| T222-02 | Protocollo di blocco canonico (`lock_sha256`) | T222-01 | sez. 6.3 + `prereg_lock.py` | DONE |
| T222-03 | Codec residuo multiscala numpy | T222-00, T222-02 | `ncm_codec.py` | DONE |
| T222-04 | Harness di sola calibrazione (no held-out) | T222-03 | `ncm_calibration.py` | DONE |
| T222-05 | BCEL gate T222 | T222-00 | voci in `bcel/catalog.py` | DONE |
| T222-06 | Test codec, calibrazione, locking | T222-02, T222-03, T222-04 | 27 test dedicati | DONE |
| T222-07 | Completare e bloccare `pre_calibration` | T222-01, T222-02 | `pre_calibration` con `locked: true` e hash | PENDING |
| T222-08 | Run ufficiale di calibrazione | T222-07 | report `calibration_only` | BLOCKED |
| T222-09 | Derivare le soglie e bloccare `pre_evaluation` | T222-08 | soglie + protocollo + hash | BLOCKED |
| T222-10 | Run di valutazione su held-out | T222-09 | report di valutazione | BLOCKED |
| T222-11 | Decisione DoD Fase 0 | T222-10 | esito esplicito, positivo o negativo | BLOCKED |

## Future work - non approvato

| ID | Task | Stato |
|---|---|---|
| T222-F1 | Generatore gerarchico, predizione parallela, confronto NFE/latenza/energia | NOT APPROVED |
| T222-F2 | Integrazione AACM e uso di `coherence_phi` come stop | NOT APPROVED |

## Regole di avanzamento

1. T222-07 richiede una decisione umana sui parametri; nessun valore viene
   scelto automaticamente dal codice.
2. T222-08 usa solo train+calibration e **non** soddisfa il DoD.
3. T222-09 non può essere eseguito prima di T222-08 e non può usare l'held-out.
4. T222-10 è l'unico task che può aprire lo split held-out, dopo il lock di
   `pre_evaluation`.
5. Un risultato negativo o inconcludente in T222-11 chiude la Fase 0; non
   autorizza automaticamente le Fasi 1-2.
6. `noise_model` resta un campo di configurazione: nessun task T222 dichiara
   attivo un gate esecutivo su backend reale.

## Verifica corrente

```bash
python -m pytest tests/test_ncm_codec.py tests/test_ncm_calibration.py tests/test_prereg_lock.py -q --no-cov
python -m ruff check q_speace/spiking q_speace/bcel/catalog.py
python -m mypy q_speace/spiking/ncm_codec.py q_speace/spiking/ncm_calibration.py q_speace/spiking/prereg_lock.py
```

Stato 2026-11-20: 27 test T222 passati; suite completa 552 passed, 3 skipped;
`mypy` pulito sui tre moduli; nessun run ufficiale di calibrazione eseguito.
