# T209 — Simulatore di resilienza esagonale

## Stato

In corso. Questa è una specifica di produzione: sostituisce i riferimenti
metaforici a coscienza, organismo o geometria sacra con regole verificabili.

## Obiettivo

Fornire una libreria classica e deterministica che valuti gruppi di sei nodi
in base a carico, entropia, tensione e fase. Il risultato è un indicatore di
salute per simulazioni e dashboard, non un comando operativo.

## BCEL

| Concetto | Classificazione | Regola digitale |
| --- | --- | --- |
| Geometria sacra / esagono naturale | accidentale | Non influenza il calcolo. |
| Gruppo di sei nodi ridondanti | funzionale | Finestra fissa di sei identificatori univoci. |
| Risonanza sistemica | funzionale | Media delle affinità a coppie, penalizzata dall'entropia. |
| Omeostasi | funzionale | Stato sano solo se tensione, entropia e risonanza rispettano soglie configurate. |
| Organismo, anima, coscienza | accidentale | Nessuna rappresentazione o inferenza di stati soggettivi. |

## Contratto API

- `NodeState` accetta valori finiti in `[0, 1]` per carico, entropia e
  tensione e una fase finita in radianti.
- `ResonanceEngine` trova esclusivamente cluster con sei nodi distinti.
- `SystemHealth` restituisce metriche e uno stato tra `empty`, `degraded`,
  `stable`; non effettua I/O, attuazione o comunicazione.
- I risultati sono ordinati deterministicamente per punteggio e identificatore.

## Criteri di accettazione

1. Meno di sei nodi restituisce zero cluster e stato `empty`.
2. Sei nodi allineati e a bassa entropia producono un cluster `stable`.
3. Entropia o tensione elevate degradano lo stato anche in presenza di sei nodi.
4. Input non finiti o fuori intervallo sono rifiutati.
5. La suite verifica assenza di azioni fisiche, backend quantistici e canali di
   comunicazione impliciti.

## Sequenza di task

- [x] T209.1 — specifica, BCEL e test di classificazione.
- [ ] T209.2 — motore deterministico e test unitari.
- [ ] T209.3 — simulazione di guasto e baseline.
- [ ] T209.4 — report di benchmark e decisione di adozione.

## Vincoli

Il task usa solo calcolo classico. Un'estensione quantistica richiederebbe un
`QuantumGeneSet.noise_model`, un gate energetico/Sevo e una specifica distinta.
