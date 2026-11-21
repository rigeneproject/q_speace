# T229 — Scelta contestuale di un coefficiente certificato

Protocollo del 21 novembre 2026, scritto prima dello sviluppo e della valutazione.
HEAD iniziale 055717742f7d49f49862a8e104dda08d2e04384c. Il checkout contiene T227
e T228 in lavorazione. T229 compare libero nella ricerca su docs, q_speace e tests.
Si applicano AGENTS, T208 e T217. Banco software sintetico opt-in. Ripristino
chiudendo l'istanza locale. Nessun cambiamento dei parametri operativi.

## Compito e tempo della decisione

Usare il backend sintetico, SpikePlasticity e il cortex di T228 con i gate
standard. Due unità, belief (0.9,0.1), ingressi (1,s) limitati al dominio
certificato. Stato iniziale EMA (1,0.5). Il riferimento q_star è l'uscita ILF
stazionaria T228 per il segnale **latente** (1,u). Il rumore del sensore altera
s, mentre il bersaglio resta u. In 48 tick, i primi 8 sono osservazione comune
a d=0.9 con u=0.5. Subito prima del nono tick copiare con deepcopy l'intero
cortex vivo, inclusi backend/EMA, memoria, ILF, cost model, gate e storia.
Ogni decisore sceglie una volta. Unico ingresso contestuale, la deviazione
standard della seconda lettura nei primi otto tick (ddof=0, scala fissa 0.25).
Il selettore riceve solo questo valore. Durata, forma futura, regime, etichetta,
seed, stato latente e traiettorie sono riservati al generatore e al valutatore.

Generatore costruito per sondare un compromesso fra inerzia ed errore da rumore.
Due regimi equiprobabili: sensore preciso e ampia escursione latente, oppure
sensore rumoroso ed escursione piccola. Il regime comune a prefisso e seguito
rende la qualità del sensore un indizio statistico osservabile. Non è un dato
empirico su sensori reali. Famiglie rettangolare e triangolare con ritorno alla
baseline. Durata e segno casuali, durata indipendente dal prefisso. Semi
distinti per split e per episodio. Bilanciamento per forma, non per esito.

## Sviluppo, archivio e scelta

Griglia ordinata (0.75,0.8,0.9,0.975,0.995), interamente verificata con T228.
64 episodi sviluppo, 80 nuovi in valutazione, metà per famiglia. Su sviluppo
provare ogni d dallo stesso snapshot e conservare la riga intera di perdite.
Tabella per contesto osservabile (std grezza <=0.08 o >0.08), vincitore e costo
del coefficiente globale. Aprire la valutazione solo se entrambi i gruppi
esistono e i rispettivi minimi medi sono diversi, riportando il costo globale.
Se fallisce, riportare il controllo senza usare gli episodi nuovi.

A usa 0.9. B minimizza la perdita media di archivio. C usa la media dei 7 vicini
per distanza assoluta sul contesto normalizzato. Pareggi per indice di sviluppo
nei vicini, ordine di griglia nella scelta. D usa lo stesso codice di C con
8 permutazioni predeterminate dei soli vettori di contesto. Archivi ordinati
per ID stabile, righe di esiti fisse. Una sola decisione e rollout per braccio
o replica D. Registrare per ogni scelta contesto, riferimenti alle righe con
distanze e perdite, punteggi, coefficiente osservato dal kernel, ingressi e
traiettorie. Salvare hash di config, codice, spec, archivio e sviluppo prima
della valutazione. Nessuna scrittura di memoria durante la valutazione.

## Analisi fissata

Primario L = somma delle distanze TV tra q_star e riferimento latente nei 48
tick. Prefisso, perturbazione e rientro sono additivi. Contrasti principali
B−C e D−C per tutte le coppie incluse parità, con D mediata prima per episodio.
IC percentile 95% su 4000 bootstrap di episodi, stratificato per forma nel
totale. Risultati anche per famiglia. Per sostenere il beneficio sul banco si
richiedono entrambi i limiti inferiori positivi (IC marginali). Confrontare
scelte diverse, migliori, peggiori, uguali contro B e contro ogni replica D
con pesi uguali entro episodio. Mostrare casi di peggioramento se presenti.
Recupero secondario entro banda TV 0.01 per 3 tick consecutivi dal rientro,
tempo censurato a orizzonte residuo+1. Misurare costo di consultazione e di
costruzione archivio separatamente. Replica locale deterministica, tempi esclusi.
Config con semi e parametri numerici persistita prima della valutazione.

## BCEL, consegna e limiti

Memoria funzionale = tabella di esiti empirici con scelta deterministica.
La metafora biologica è accidentale, già classificata in T228. Aggiungere voce
T229 e test. Verificare clone, isolamento informativo, permutazioni, fasi,
contrasti e applicazione reale. Consegna di codice, manifest, dati, relazione e
comando. Nessun uso di backend quantistici o attuatori.
