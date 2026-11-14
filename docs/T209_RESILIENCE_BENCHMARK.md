# T209 — Report benchmark di resilienza

## Metodo

Il benchmark usa sei nodi classici con fase allineata, entropia `0,05` e
tensione `0,10`. Non usa backend quantistici, rete, dispositivi o attuatori.

La prova applica un guasto controllato al nodo `n0` e confronta:

- **gruppo ridondante:** capacità residua = nodi disponibili / sei;
- **baseline a percorso singolo:** capacità = zero quando il solo percorso
  fallisce.

## Risultato

| Scenario | Capacità residua |
| --- | ---: |
| Sei nodi, nessun guasto | 1,00 |
| Gruppo ridondante, un guasto | 0,8333 (5/6) |
| Baseline a percorso singolo, un guasto | 0,00 |

Il risultato è coperto da `tests/test_systemic_resonance.py` e rappresenta
soltanto disponibilità di componenti: non è un indicatore di coscienza,
intenzionalità o autonomia.

## Decisione

**Adottare per simulazione e osservabilità.** Il motore può essere usato per
presentare metriche in dashboard o test di topologia. Non è autorizzato per
controllo di infrastrutture, azioni fisiche o selezione automatica di backend.

Il prossimo lavoro, se richiesto, è un adattatore di sola lettura verso dati
di simulazione con contratti d'ingresso e budget espliciti.
