# T228 — Risultati della memoria degli errori nella plasticità

Esperimento software, 21 novembre 2026. **La memoria migliora la prima selezione
delle candidate, ma non migliora il recupero funzionale in questo banco.**
Nessuna promozione operativa. Non è una dimostrazione di AGI o di neuroplasticità
biologica. Specifica preregistrata: `T228_ERROR_MEMORY_PLASTICITY_SPEC.md`.

## Implementazione effettivamente usata

Commit iniziale `055717742f7d49f49862a8e104dda08d2e04384c`, working tree già
modificato. Stato iniziale, hash e patch preesistente sono conservati in
`artifacts/T228_error_memory_20261121/`. T227 è preservato; il catalogo condiviso
riceve solo due voci aggiuntive T228. Nessun commit creato e nessun dato riservato
di altri esperimenti consumato. Letti integralmente documento di richiesta,
AGENTS applicabili, T208 e T217.

“SPEACE Micro” è il layer `q_speace`, come indicato in PARADIGMA_6_0_SPEC.
Il percorso scelto è `SpikingBrainCortex.tick → think → SyntheticBackend.think →
SpikePlasticity.update → coefficients → apply_to_ilf → compute_q_star`.
I file runtime originali sono `spiking/plasticity.py`, `spiking_brain/cortex.py`
e `edd_cvt/ilf.py`. Restano invariati. Il QuantumOrchestrator non contiene questo
aggiornamento di plasticità: non si è attribuito ad esso il risultato.

Il backend sperimentale fornisce attività sintetica a due unità e una belief
costante [0.9,0.1]; chiama la vera EMA e il vero tick del cortex, inclusi i gate
di confidenza, coerenza e Sevo. Il budget energetico fisico non è misurato;
nessun dispositivo o backend quantistico viene invocato. Non è il modello HTTP,
né un esperimento di comprensione linguistica. Gli spike ordinari dello stub
possono superare 1: la certificazione del banco non si estende ad essi.

Unico coefficiente proposto: `decay`, float64, ritenzione EMA adimensionale per
tick; default 0.9, intervallo (0,1) imposto dal costruttore. Il tick aggiorna
lo stato persistente `x' = decay*x + (1-decay)*abs(input)`. Il vettore risultante,
normalizzato per il massimo, modifica il peso dell'agente nel campo ILF e quindi
q_star. La soglia dinamica degli spike non è un parametro adattato in questo
percorso; non è stata inventata una regola di soglia al suo posto.

Il propositore è un algoritmo sperimentale, non una capacità già presente del
kernel: il council propone strategie generiche, non mutazioni di decay. Anche
l'archivio dei testimoni è nuovo e separato da WorkingMemory e EvolutionaryMemory.
L'applicatore usa la prima candidata verificata oppure la regola iniziale se
esaurisce il budget. La memoria non approva candidate.

## Proprietà verificata e copertura

Dominio continuo esplicito: ciascuna componente di stato x e di ingresso r è
in [0,1], due unità, un aggiornamento per tick. La proprietà reale richiede
`0 <= x' <= 1` e `abs(x'-x) <= 1/4`. Il limite 1/4 è introdotto dal banco e fissato
prima della valutazione; non è un limite biologico o di sicurezza operativa.
La normalizzazione dei coefficienti avviene dopo l'EMA, quindi non rende vera
questa proprietà. Per esempio decay=0.5, x=0, r=1 produce 0.5 e viola il limite.

Il verificatore in un modulo separato usa Fraction con il valore esatto del float
decay. Per un aggiornamento affine basta controllare i quattro vertici del
quadrato: minimo, massimo e massimo della variazione assoluta sono raggiunti
ai vertici. La prova copre tutti i punti reali del dominio, componente per
componente; non è un campionamento. VALIDA indica questo certificato, INVALIDA
include un vertice testimone, INDETERMINATA copre valori non finiti o non
applicabili al costruttore. Non è un verificatore ostile isolato a livello OS.

Il runtime NumPy float64 non è stato formalmente verificato: si conserva
esplicitamente il divario fra modello reale e arrotondamenti. Tutti gli otto
controesempi di esperienza e quelli respinti in valutazione sono rieseguiti nel
vero `SpikePlasticity.update`; nessuna divergenza osservata, gap massimo zero
nei testimoni di esperienza. I controlli includono decay=0.875 valido, 0.5
invalido, 0.75 valido e i due float immediatamente adiacenti (inferiore invalido,
superiore valido). Non si rivendica validità universale del programma floating
point né di ingressi oltre il dominio.

## Confronto fissato e costi

Esperienza: otto errori con seed 22801, replay e correzioni nuovamente verificate;
rollout delle correzioni su step estremi. Il contenuto è congelato prima della
valutazione. Recupero deterministico del primo testimone: dimezza il guadagno
`1-decay` finché quel testimone non viola più il limite. Non confronta solo
l'identità di una candidata già rifiutata.

A e B condividono propositore, feedback corrente, snapshot EMA [1,1], istanze
nuove del cortex, massimo due proposte grezze e prima valida applicata. A perde
l'accesso agli errori pregressi; B può correggere la proposta usando l'archivio
congelato. A può applicare la stessa correzione dopo il primo verdetto corrente.
Ogni trasformazione di una grezza è registrata; non ci sono scarti invisibili.
Nessun episodio aggiorna la memoria per il successivo. I seed di proposta e
perturbazione sono separati e accoppiati fra condizioni.

Valutazione: 24 coppie indipendenti per step con ampiezze nuove e 24 per pulse,
famiglia completamente esclusa dall'esperienza. Pulse ritorna a [1,1] al tick 12.
Orizzonte 32 tick. Metrica funzionale: distanza TV di q_star dal riferimento
stazionario corrente, ottenuto dal vero consumer ILF. Recupero: TV <=0.01 per
tre tick consecutivi dopo l'ultima transizione. Riportiamo il tick di conferma;
i mancati recuperi ricevono l'orizzonte residuo+1 (33 step, 21 pulse), senza
escluderli dalla media. Banda e orizzonte sono scelte preregistrate del banco.

Hash della configurazione, scritto prima della valutazione:
`52c899144d0905a4be414898da35d62f8a2ad84da3ccd273bb374eccd04df68b`.
Hash memoria:
`ae269a40c418a32551c32703104ba09d331966796ba55e2b36370ed371c29c3c`.
Il manifest conserva anche hash del codice e versioni Python/NumPy/Pydantic.

## Risultati grezzi aggregati

| Metrica | A senza memoria | B con memoria | B − A | Coppie |
|---|---:|---:|---:|---:|
| Prima candidata valida, tutte | 15/48 (31.25%) | 48/48 (100%) | +68.75 punti % | 48 |
| Proposte grezze medie fino alla prima valida | 1.6875 | 1 | −0.6875 | 48 |
| Chiamate al verificatore medie | 1.6875 | 1 | −0.6875 | 48 |
| Budget esauriti | 0/48 | 0/48 | 0 | 48 |
| Recupero funzionale | 40/48 (83.33%) | 40/48 (83.33%) | 0 | 48 |
| Tick di conferma, con censura dichiarata | 18.75 | 18.75 | 0 | 48 |
| TV finale media | 0.00677977 | 0.00677977 | 0 | 48 |
| Ricerca media, run 01 | 99.57 µs | 60.80 µs | −38.77 µs | 48 |
| Rollout medio, run 01 | 4.547 ms | 4.890 ms | +0.343 ms | 48 |

| Famiglia | Prima valida A/B | Recuperati A/B | Tick censurati A/B | Coppie |
|---|---|---|---|---:|
| Step nuovo | 6/24 / 24/24 | 21/24 / 21/24 | 21.5417 / 21.5417 | 24 |
| Pulse held-out | 9/24 / 24/24 | 19/24 / 19/24 | 15.9583 / 15.9583 | 24 |
| Candidate mai viste in esperienza | 15/48 / 48/48 | 40/48 / 40/48 | 18.75 / 18.75 | 48 |

Sono nuove tutte le grezze e le inviate, anche rispetto alle correzioni archiviate:
nessun effetto di eliminazione di duplicati. Ogni prima inviata richiede una
grezza; A ne richiede una seconda in 33 episodi. La validità del secondo tentativo
porta A alla stessa decay scelta da B: le traiettorie funzionali A/B risultano
identiche in ogni coppia. Nessun peggioramento di recupero, ma B ha rollout medio
più lento nel run 01: questi tempi piccoli sono rumorosi e non provano un vantaggio
di prestazioni hardware. Il costo offline dell'esperienza (16 verifiche, 8 replay,
8 rollout da 32 tick, serializzazione) non è incluso nei tempi di ricerca della
tabella: non si rivendica un risparmio totale ammortizzato.

Controlli: default decay=0.9 recupera 24/24 step (30.9167 tick) e 0/24 pulse;
quasi congelata `nextafter(1,0)` recupera 0/24 step e 24/24 pulse (3 tick).
Quest'ultimo risultato è un limite del compito: una regola che ignora il pulse
è già vicina al riferimento quando l'ingresso torna allo stato iniziale.
Pertanto “recupero dopo l'ultima transizione” non misura la capacità di rispondere
utilmente durante tutte le transizioni. Non viene usato per sostenere superiorità
generale della regola congelata o dei candidati.

## Traccia leggibile di riuso

`experience-0`: decay=0.3848763803960955, stato=0, ingresso=1. Il verificatore
prevede 0.6151236196039045; il runtime osserva lo stesso valore, superiore a 1/4.
La correzione 0.8462190950990238 viene memorizzata solo dopo VALIDA.

Nell'episodio nuovo `step-2`, B propone grezza 0.7092815592592614, recupera quel
testimone e invia 0.8546407796296307: VALIDA, senza aver già visto la candidata.
Con ingresso [1,0.03935331954197164], il primo vero tick cambia EMA da [1,1] a
[1,0.8603611474772377]; il gate approva e q_star diventa
[0.8853212282272053,0.11467877177279469]. TV iniziale 0.12730276227237916,
recupero confermato a 22 tick, TV finale 0.0015271716038098432.
A rifiuta la prima grezza, poi usa il feedback corrente e arriva alla stessa
decay e alla stessa traiettoria. Il riuso è efficace per la selezione anticipata,
non produce in questa coppia un recupero migliore.

## Riproduzione e verifiche

Dalla radice del checkout, PowerShell, scegliendo una directory inesistente:

```powershell
.venv/Scripts/python.exe -m q_speace.experiments.error_memory --output artifacts/T228_reproduction
.venv/Scripts/python.exe -m pytest tests/test_t228_error_memory.py
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m py_compile q_speace/experiments/error_memory.py q_speace/experiments/error_memory_verifier.py tests/test_t228_error_memory.py q_speace/bcel/catalog.py
.venv/Scripts/python.exe -m ruff check q_speace/experiments/error_memory.py q_speace/experiments/error_memory_verifier.py tests/test_t228_error_memory.py q_speace/bcel/catalog.py
.venv/Scripts/python.exe -m black --check q_speace/experiments/error_memory.py q_speace/experiments/error_memory_verifier.py tests/test_t228_error_memory.py q_speace/bcel/catalog.py
.venv/Scripts/python.exe -m mypy q_speace/experiments/error_memory.py q_speace/experiments/error_memory_verifier.py tests/test_t228_error_memory.py q_speace/bcel/catalog.py
```

Run 01 e run 02 consegnati in `artifacts/T228_error_memory_20261121/`:
config, preregistration, frozen_memory, verification_checks, experience_rollouts,
episodes.jsonl (proposte e tutti i tick), summary e completion. I 192 record per
run includono 96 episodi A/B e 96 controlli. Seconda esecuzione: tutti i campi
non temporali identici; hash config e memoria identici. È una replica nello
stesso ambiente da parte dello stesso agente, non una riproduzione indipendente.

### Pytest

11 test T228 passano; suite intera: **644 passed, 3 skipped**, coverage 83.05%,
soglia 20% conservata. Log `pytest_full.txt`. Test negativi includono fuori
dominio, limite numerico, budget zero/fallback, memoria congelata, pairing,
replay e rifiuto di sovrascrivere output.

### Compilazione, Black e mypy

py_compile e Black --check passano sui quattro file toccati; mypy passa sugli
stessi file anche senza `--follow-imports=silent` (log consegnato).

### Ruff

Perimetro toccato pulito. `ruff check q_speace` segnala due errori preesistenti:
F401 in cli.py:26 e B009 in orchestrator.py:215. Gli hash iniziali confermano che
entrambi i file, insieme a evolution_council.py, sono rimasti invariati; non si
è corretto il lavoro T227 per far passare il gate globale. Nessun gate abbassato.

## Verifica delle affermazioni Riemann / Lean

Fonti primarie consultate il 21 novembre 2026, senza rieseguire gli artefatti Lean:

- [Nota di Alpöge](https://alpo.ge/remark.pdf): attribuisce la prova proposta al
  lavoro con Claude e collega l'archivio Lean. Conferma l'annuncio, non permette
  di misurare indipendentemente il contributo creativo del modello.
- [Registro MIT di Andrew Sutherland](https://math.mit.edu/~drew/grh/), aggiornato
  alle 12:55 UTC, cioè 13:55 italiane: riporta compilazione di 175187 moduli,
  accettazione nanoda/con-leche, controllo delle cinque enunciazioni contro
  Mathlib e assiomi standard. Alcuni controlli completi risultano ancora in corso.
  Il registro delimita la portata formale e le dipendenze fidate; non è una
  nostra verifica locale della dimostrazione.
- [Clay](https://www.claymath.org/millennium/riemann-hypothesis/): la pagina mostra
  ancora “Unsolved”. Non si equipara un annuncio a riconoscimento definitivo.
- [Articolo originale AlphaProof](https://www.nature.com/articles/s41586-025-09833-y):
  descrive apprendimento per rinforzo in ambiente Lean. È un precedente di metodo,
  non evidenza della capacità del banco SPEACE.

L'esperimento non assume vera RH e non ne usa alcuna conseguenza matematica.

## Risposte alle cinque domande

1. Verificata la variazione limitata della EMA nel modello affine reale sul
   dominio unitario continuo; replay nel vero update e integrazione nel tick.
   Restano esclusi prova universale float64, backend reali e ingressi illimitati.
2. Sì, nel propositore costruito, su 48 coppie con candidate nuove e budget uguale,
   migliora la prima selezione e diminuiscono chiamate/proposte. Il testimone è
   particolarmente informativo per questa famiglia affine: non è apprendimento
   autonomo di strategie generali.
3. Il vantaggio di selezione compare anche sui pulse held-out. La distribuzione
   delle proposte resta la stessa e il vincolo è indipendente dalla perturbazione:
   questo trasferimento è limitato e non prova adattamento a nuove leggi dinamiche.
4. No: recuperi, tick e traiettorie A/B sono identici. A dispone di feedback
   sufficiente per ottenere la stessa soluzione entro il budget.
5. Restano incerti generalizzazione, valore della memoria su domini più complessi,
   robustezza floating point universale e costi totali ammortizzati. Il compito
   sintetico e la metrica pulse hanno limiti espliciti; nessuna conclusione su
   apprendimento linguistico, energia fisica o neuroplasticità generale è sostenuta.
