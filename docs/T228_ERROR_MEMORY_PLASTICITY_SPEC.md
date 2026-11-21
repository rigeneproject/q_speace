# T228 — Memoria dei controesempi nella plasticità

Stato: esperimento software isolato, preregistrazione del 21 novembre 2026.
Non autorizza promozione, attuazione o backend quantistici reali (T208/T217).

## Ricognizione prima delle modifiche

Commit iniziale: `055717742f7d49f49862a8e104dda08d2e04384c`.
T228 non compare nei percorsi docs, q_speace e tests alla ricognizione.
Il manifest iniziale conserva status e hash dei file modificati preesistenti,
inclusi T227, che non vengono sovrascritti. Unica aggiunta condivisa: voci BCEL.
SPEACE Micro è il pacchetto q_speace secondo PARADIGMA_6_0_SPEC.
Il QuantumOrchestrator non aggiorna SpikePlasticity; il percorso scelto è
SpikingBrainCortex.tick -> think -> backend.think -> SpikePlasticity.update ->
coefficients -> apply_to_ilf -> InformationalLogicalField.compute_q_star.
StubSpikingBrain usa già questa EMA; i suoi ingressi hash non rappresentano
un compito funzionale controllato. Il banco introduce un backend sintetico che
riusa SpikePlasticity e il vero cortex.tick, con tutti i gate ordinari attivi.
Non sostituisce il tick con equazioni alternative. Non prova il comportamento
del modello HTTP o dell'intero QuantumOrchestrator.

Parametro unico: decay, float64 adimensionale, ritenzione per tick, default 0.9;
limiti (0,1) da SpikePlasticity.__init__. Lo stato EMA è persistente fra tick;
coefficients normalizza per massimo, senza clamp sull'aggiornamento EMA.
Il council esistente propone strategie generiche, non coefficienti decay;
non viene modificato. Propositore e archivio di controesempi sono sperimentali,
distinti da WorkingMemory (ThinkResult) e dalla memoria di esiti delle mutazioni.

## Proprietà e verificatore

Regola U_d(x,r)=d*x+(1-d)*abs(r), per ciascuna delle due unità.
D: stato EMA x in [0,1], ingresso r in [0,1], dimensione 2, un update per tick.
È un sottodominio esplicito: gli spike ordinari possono superare 1 e non sono
coperti. I: EMA in [0,1] e |U_d-x| <= 1/4 nel modello reale.
Il limite 1/4 è introdotto dal banco per evitare salti istantanei, non deriva
da una garanzia biologica o da requisiti operativi. V(d) richiede I su tutto D.
Verifica indipendente esatta con Fraction agli estremi del quadrato: affine,
massimi/minimi e massimo valore assoluto sono ai vertici. Nessun campionamento
spacciato per prova. d non finito/fuori modello -> INDETERMINATA; violazione ->
INVALIDA con vertice testimone; altrimenti VALIDA. d=0 o 1 non è applicabile
al costruttore e resta INDETERMINATA. Non è una prova Lean né del runtime intero.
Il certificato è sui reali con d uguale esattamente al float rappresentato;
runtime float64: replay confrontato con modello, tolleranza 8*eps. La garanzia
floating point non viene dichiarata formalmente dimostrata. Verificare 0.875,
0.5, 0.75 e i float adiacenti; replay di ogni controesempio.

## Protocollo fissato prima della valutazione

Snapshot EMA [1,1], ILF nuovo con smoothing di default del cortex, belief
costante [0.9,0.1], confidence=1, backend senza rete. Riferimento funzionale:
q_star stazionario ottenuto dal vero apply_to_ilf con coefficienti normalizzati
degli ingressi correnti. Metrica: distanza TV fra q_star effettivo e riferimento,
distinta da decay e dalla proprietà di variazione. È tracking software sintetico.
Famiglie esperienza: step verso [1,0] o [0,1]. Valutazione: step con ampiezze
nuove e famiglia held-out pulse che ritorna a [1,1] a tick 12, mai in esperienza.
24 seed indipendenti per famiglia, accoppiati A/B; flussi proposte e ingressi
separati. 32 tick, banda TV <=0.01 per 3 tick consecutivi; recupero misurato
dopo l'ultima transizione della perturbazione. Fallimenti censurati a orizzonte+1.
Queste soglie sono scelte ingegneristiche preregistrate, non tarate sulla valutazione.

Esperienza: 8 candidati decay <0.75 generati con seed dedicato. Memorizzare
vertice, risultato reale, replay e correzione verificata d'=1-(1-d)/2^k finché
il testimone non viola più I. La correzione apprende dal testimone, non legge
il limite ammissibile di decay dal verificatore. Recupero: primo testimone
conservato, stesso algoritmo per feedback corrente A e memoria B.
Memoria congelata serializzata e hash prima della valutazione, nessun flusso
di scrittura fra episodi. Ogni episodio riparte dallo stesso snapshot.
Budget massimo 2 proposte grezze; prima uniforme [0.25,0.99], seconda correzione
da feedback corrente se disponibile. B può correggere la prima usando memoria.
Ogni proposta grezza conta anche se trasformata; registrare grezza, inviata,
testimone recuperato, verdetto, chiamate, tempi ricerca e rollout separati.
Prima valida applicata, altrimenti decay default 0.9. Stesse politiche A/B.
Controlli aggiuntivi: default 0.9 e quasi congelata nextafter(1,0).

## Risultati e criteri

Salvare config+hash, memoria+hash e hash sorgenti prima di aprire valutazione;
risultati JSONL per proposta/episodio/tick, manifest e aggregati con A, B,
differenza accoppiata e n per tutte le metriche, famiglia e candidate nuove.
Validità prima inviata, grezze/chiamate/tempo prima valida, esaurimenti,
recupero, tempo censurato e TV finale. Nuova significa grezza/inviata non
identica alle candidate di esperienza; segnalare eventuale deduplicazione.
Documentare peggioramenti e traccia completa scoperta -> riuso -> funzione.
Nessuna soglia di effetto abilita promozione. Un beneficio di selezione non
equivale a recupero né a neuroplasticità generale; niente inferenza AGI.

## Consegna e controlli

Spec -> BCEL -> test -> implementazione -> pytest, py_compile, Ruff, Black,
mypy -> esecuzione -> relazione italiana. Nessuna dipendenza nuova. Modulo
opt-in eseguibile con python -m, output in directory nuova (rifiuto overwrite).
Rollback: non invocare il modulo; configurazioni ordinarie non cambiano.
