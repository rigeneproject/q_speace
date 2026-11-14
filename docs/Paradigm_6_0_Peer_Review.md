# Peer review multilivello di Paradigm 6.0

**Data:** 14 novembre 2026  
**Documento:** Paradigm_6_0_Revised.md, versione 1, 4.260 parole  
**Impronta SHA256:** `816b592cfd404d907e333a87f7495112868654681bbbb7528ef8754626c6ff04`  
**Esito editoriale proposto:** revisione maggiore

## Valutazione complessiva

La versione revisionata costituisce una base coerente per un programma di ricerca. Gli errori macroscopici della precedente formulazione sono stati corretti: contabilità fisica e informazione sono separate, il prodotto con segno che poteva occultare un danno è eliminato, la geometria della rete è qualificata e le garanzie sono presentate come condizionali. La coscienza non viene più assunta come proprietà acquisita.

Il documento non è ancora una specifica operativa riproducibile. Il problema dominante è la distanza tra requisiti ben formulati e una realizzazione concreta che ne definisca responsabilità, algoritmi, tempi, assunzioni e criteri di accettazione. L'assenza di risultati sperimentali è dichiarata: non è stata trattata come una contraddizione o come evidenza di fallimento.

La decisione consigliata è **revisione maggiore per un position paper o una proposta architetturale; integrazione sostanziale prima di presentarlo come specifica implementabile**. Non è pronto come articolo di risultati o base autonoma per un deployment. Nessuno dei cinque esami ha identificato una nuova contraddizione fatale; questo non equivale a una prova di correttezza o completezza.

## Metodo e limiti della revisione

Cinque agenti AI hanno ricevuto incarichi distinti e hanno letto il medesimo documento. Le prime relazioni sono state prodotte separatamente. Sono seguiti un controllo reciproco tra revisione matematica e revisione dei sistemi e un controllo metodologico dei rilievi sulla governance. Il coordinatore ha deduplicato i rilievi, verificato esempi algebrici e confrontato alcune fonti primarie.

Si tratta di una revisione multiagente assistita da IA, non di una peer review esterna organizzata da una rivista. Gli agenti condividono modello e contesto di base: separazione dei compiti e contraddittorio riducono alcuni errori, ma non costituiscono indipendenza statistica o diversità di competenze umane. Il coordinatore ha inoltre partecipato alla riscrittura: questo possibile bias va dichiarato.

Non sono stati eseguiti esperimenti sull'architettura SPEACE, penetration test, verifiche di codice o una ricerca sistematica di anteriorità. Le semplici verifiche numeriche dei controesempi non sono risultati sperimentali del progetto. Il manoscritto esaminato non è stato modificato da questa review.

## Livelli di esame

| Revisore | Ambito | Risultato principale |
|---|---|---|
| MAT | Matematica e fisica | Formalismo di base coerente; composizione degli errori e aggregazione da precisare |
| SYS | Controllo e sistemi distribuiti | Mancano contratti osservazione–attuazione, recupero e aggiornamento |
| GOV | Governance sicurezza e privacy | Le promesse normative richiedono procedure verificabili sotto conflitto |
| EXP | Metodo sperimentale e causalità | H1–H4 non costituiscono ancora un protocollo riproducibile |
| EDT | Posizionamento editoriale e contributo | Originalità da delimitare rispetto alla letteratura pertinente |

Le etichette dei rilievi nelle appendici restano quelle dei revisori. Per evitare ambiguità, MAT-M1 indica M1 dell'appendice matematica; EXP-M1 indica M1 dell'appendice metodologica. Le gravità finali sono quelle della sintesi seguente, che prevalgono sulle valutazioni individuali quando il contraddittorio le ha modificate.

## Revisioni maggiori prioritarie

### R1 Definire una realizzazione minima e il contributo originale

**Sezioni:** 1.3, 2, 10, 12. **Origine:** EXP-M1, EDT-E1/E2/E5.

Le funzioni assegnate a q_speace possono essere svolte anche da un supervisore adattivo convenzionale. Senza una configurazione congelata, un confronto può misurare tuning, maggiori risorse o diversa qualità del codice anziché il contributo rivendicato.

Richiesta: definire q_speace-v0 in un solo dominio, con stato, osservazioni, algoritmo, memoria, parametri modificabili, frequenze e regola di apprendimento. Distinguere nucleo obbligatorio ed estensioni opzionali. Confrontare esplicitamente Bridge, Simplex/runtime assurance e filtri di sicurezza predittivi [S1–S3]. Questi precedenti non dimostrano assenza di originalità: impongono di localizzarla.

**Chiusura:** matrice dei componenti identici e diversi rispetto alle baseline; una decisione completa dalla misura all'attuazione o al rigetto; formulazione di una differenza verificabile rispetto ai precedenti.

### R2 Precisare il contratto di sicurezza e l'indipendenza del validatore

**Sezioni:** 2.1–2.3, 3.3, 9. **Origine:** SYS-C1/C2/C4/C5, GOV-G2.

La sicurezza è formulata sullo stato fisico, ma il sistema decide da osservazioni incerte e ritardate. L'indipendenza del validatore è descritta funzionalmente, senza delimitare credenziali, dipendenze comuni e componente che impedisce l'attuazione non approvata. Ripristinare parametri precedenti non ripristina lo stato fisico.

Richiesta: per il dimostratore, definire errore osservativo, età dei dati, ritardi tollerati, confine di fiducia, gestione della mancata risposta e condizioni di transizione al fallback. La metodologia formale può essere scelta in funzione del dominio; non viene imposto un particolare algoritmo di controllo.

**Chiusura:** un'argomentazione verificabile che colleghi osservazione, validazione e attuazione sotto assunzioni esplicite; prove di dati obsoleti, rollback dopo accumulo fisico e tentativi di bypass entro il modello di minaccia. Le garanzie di sicurezza e quelle di servizio devono restare distinte quando le risorse non bastano.

### R3 Definire le proprietà del protocollo di aggiornamento

**Sezioni:** 2.2, 9. **Origine:** SYS-C3, GOV-G3.

Versioni e scadenze non definiscono da sole il comportamento durante duplicazioni, riordinamenti, crash e attivazioni parziali. Le modifiche accoppiate possono essere ammissibili separatamente e incompatibili insieme. Per esempio, due celle che consumano 0,4 ciascuna sotto un limite comune di 1 possono approvare separatamente incrementi di 0,15; l'attivazione simultanea porta il consumo a 1,1.

Richiesta: specificare validità delle versioni, applicazione idempotente, compatibilità delle attivazioni parziali, autorità di attuazione e recupero dopo crash. Un protocollo di riferimento deve soddisfare queste proprietà; non serve imporre consenso globale per ogni aggiornamento.

**Chiusura:** tracce riproducibili per riordino, duplicazione, partizione e riconnessione con esiti ammessi dichiarati. Distinguere membership, rilevazione di anomalia, attribuzione della colpa e quarantena.

### R4 Rendere il valore causale e il suo limite inferiore ben definiti

**Sezioni:** 6.1–6.3. **Origine:** MAT-M3, EXP-M4.

La formula del limite inferiore è plausibile, ma non basta senza definire il valore bersaglio, l'intervento, la policy successiva, l'orizzonte e il significato degli errori. Un errore limitato per ciascuna delle due traiettorie non equivale allo stesso limite sulla differenza: con errori opposti di modulo e, la differenza può sbagliare di 2e. Questo è un caso da prevenire, non un errore già dimostrato nel manoscritto.

Richiesta: distinguere errore del modello, troncamento spaziale, troncamento temporale ed eventuale errore statistico; evitare doppio conteggio. Precisare se il limite è deterministico o probabilistico. Un effetto negativo oltre H non deve scomparire dal giudizio per una scelta conveniente dell'orizzonte.

**Chiusura:** esempi con verità nota nel simulatore, effetti post-H, errori opposti e copertura del limite dichiarato. L'identificazione causale nel mondo reale va trattata separatamente: una simulazione con interventi definiti non richiede di dimostrare già l'identificazione da dati osservazionali reali.

### R5 Costruire l'aggregazione e rappresentare danni concentrati nel tempo

**Sezioni:** 5, 6, 10.1. **Origine:** MAT-M2/M6, GOV-G4.

La richiesta di invarianza alla suddivisione delle celle è appropriata, ma non segue dai soli pesi. Con due regioni di pari peso, valori 0 e 1 e normalizzazione b(x)=x², il punteggio separato è 0,5 mentre quello ottenuto normalizzando la media aggregata è 0,25. La realtà fisica è identica.

Richiesta: definire una misura additiva e una regola di aggregazione compatibile, oppure dichiarare la sensibilità alla risoluzione. Identificare anche gruppi interessati e finestre cumulative: un danno piccolo ma reiterato sullo stesso gruppo può restare invisibile nella media della cella.

**Chiusura:** test accorpamento/suddivisione con eterogeneità e normalizzazioni non lineari; confronto tra scenari con beneficio totale uguale ma diversa concentrazione e durata del danno. I danni non compensabili restano vincoli esterni, non penalità aggirabili con un beneficio maggiore.

### R6 Trasformare H1 H2 e H3 in un protocollo preregistrabile

**Sezioni:** 10.2–10.4. **Origine:** EXP-M1–M5.

Richiesta: scegliere endpoint primario, margine di interesse, criterio di sicurezza, baseline selezionata fuori dal test finale, budget di tuning e numero di repliche. L'unità statistica non può essere automaticamente il singolo tick o la singola cella: le dipendenze della rete vanno rispettate.

Il modello del decisore e il valutatore degli esiti devono essere distinti abbastanza da evitare una verifica circolare. Le proposte dannose e sicure di H2 richiedono un riferimento indipendente dal validatore valutato. Il sistema che rifiuta tutto deve fallire il criterio di utilità; quello che accetta tutto deve fallire il criterio di protezione.

**Chiusura:** protocollo completo per un dominio, repliche a livello di traiettoria, casi non determinabili, fallimenti e incertezza riportati; soglie dichiarate prima dei risultati. Nessuna numerosità universale è prescritta senza analisi di precisione o potenza.

### R7 Rendere eseguibili governance e criteri di conformità

**Sezioni:** 3, 9–11. **Origine:** GOV-G1/G3/G5/G6, EDT-E3.

Richiesta: definire un contratto minimo per il pilota con competenze, conflitti d'autorità, ricorsi, emergenze, scarsità, ammissione e quarantena. Collegare i requisiti a responsabili, artefatti ed evidenze. Separare conformità documentale, tecnica e valutazione delle prestazioni.

Per un pilota con dati umani, aggiungere inventario dei dati e flussi, accessi, retention, divulgazione per gli audit e cancellazione. Questi requisiti non impongono di raccogliere dati personali nei primi esperimenti: una simulazione sintetica è sufficiente per iniziare.

**Chiusura:** esercitazioni di conflitto e falsa accusa, mappa requisito–procedura–evidenza e regole provvisorie durante i ricorsi. La legittimità delle decisioni non può essere dimostrata da uno score positivo o da un test automatico.

## Correzioni locali

| ID | Sezione | Intervento richiesto |
|---|---|---|
| L1 | 2.2 | Esplicitare rigetto dopo proiezione se il budget è superato, oppure proiettare sull'intersezione dei vincoli; gestire insieme vuoto e non unicità |
| L2 | 4.2 | Fissare riferimento termodinamico comune nel pilota e dichiarare la soglia di potenza in watt |
| L3 | 7 | Enunciare nonnegatività dei pesi nel punto d'uso, processo congiunto dei rumori e trattamento delle fasi |
| L4 | 5.2 e registro | Chiamare la proprietà monotonicità a coordinate fissate e assenza di cancellazione moltiplicativa, non impossibilità di ogni compensazione |
| L5 | 10.4 H4 | Misurare l'effetto incrementale del componente contro un sostituto funzionante; non richiedere che il vantaggio persista dopo averne rimosso la causa |
| L6 | Corpo e appendici | Spostare parte delle confutazioni del vecchio testo nel registro, così che la nuova proposta sia leggibile autonomamente |

L1 è stato classificato diversamente dai due revisori tecnici. Il contraddittorio conclude **minor nel manoscritto attuale, da risolvere prima dell'implementazione**: proiezione e disuguaglianza possono essere interpretate come due condizioni di screening, non come un falso teorema. L5 è una modifica testuale locale con conseguenze importanti sull'attribuzione sperimentale.

## Decisioni del contraddittorio

1. Non contare i requisiti già riconosciuti come altrettante nuove confutazioni. Gran parte di R2 e R3 consiste nel concretizzare contratti rinviati dal testo.
2. Non imporre fattibilità indefinita di tutti i servizi sotto scarsità arbitraria. Se viene rivendicata invarianza robusta, vanno specificate le condizioni che la sostengono; altrimenti vanno dichiarati degrado e limiti.
3. Non dichiarare dimostrata la non-originalità. Le somiglianze con Simplex e safety filters richiedono un confronto e una differenza verificabile, non un verdetto assoluto.
4. Non scambiare monotonicità parziale per divieto di qualsiasi trade-off. Il nuovo score corregge un incentivo perverso specifico, non risolve universalmente Goodhart.
5. Distinguere simulazione sintetica, pilota e deployment: alcune richieste su privacy e procedure umane sono gate del pilota, non prerequisiti per ogni calcolo preliminare.

## Ordine di revisione consigliato

Prima definire un dominio e q_speace-v0, quindi scrivere il contratto Bridge e l'esempio completo. Successivamente precisare valutazione causale e aggregazione, congelare il protocollo sperimentale e aggiungere la matrice di conformità. Il confronto bibliografico deve accompagnare la definizione del contributo, non essere rimandato alla fine.

Un allegato operativo ben circoscritto è più utile di un'ulteriore espansione della visione planetaria. Il risultato del prossimo ciclo dovrebbe consentire a due gruppi di implementare lo stesso esperimento e interpretarne l'esito con la stessa regola.

## Fonti di confronto verificate dal coordinatore

S1. Phan, D. T. et al. *Neural Simplex Architecture*, NASA Formal Methods 2020, preprint https://arxiv.org/abs/1908.00528 . Precedente per controllore avanzato, controllo di riserva e miglioramento online.

S2. Wabersich, K. P. e Zeilinger, M. N. *A predictive safety filter for learning-based control of constrained nonlinear dynamical systems*, Automatica, 2021; preprint https://arxiv.org/abs/1812.05506 . Precedente per verifica di input proposti rispetto a stato, vincoli e incertezza.

S3. NASA, *A Formal Verification Framework for Runtime Assurance*, record https://ntrs.nasa.gov/citations/20230017350 . Il record indicizzato descrive una formalizzazione di Simplex; la pagina diretta non è stata recuperata dal coordinatore per timeout. Non viene presentata come lettura integrale.

I riferimenti ulteriori consultati dai revisori sono riportati nelle rispettive relazioni. Il confronto è mirato e non esaustivo.

## Relazioni individuali

Le appendici seguenti conservano integralmente le cinque relazioni di prima lettura. Dove una gravità o formulazione differisce dalla sintesi, fa fede l'aggiudicazione del coordinatore riportata sopra. Le relazioni sono valutazioni testuali, non risultati di attacchi o esperimenti eseguiti.


---

## Appendice A Matematica e fisica

# Esaminatore M — Matematica e fisica

Documento esaminato: Paradigm_6_0_Revised.md, versione 1, 14 novembre 2026; 415 righe. Esame del testo e verifica algebrica di controesempi. Nessuna simulazione dell'architettura, audit del codice o validazione sperimentale.

## Giudizio

**Revisione maggiore per qualificarlo come specifica operativa; impianto matematico complessivamente coerente come programma di ricerca.** Non rilevo la ripetizione degli errori macroscopici del testo originale: la somma tra joule e watt è rimossa, il prodotto con segno patologico è sostituito, la crescita del reticolo è corretta e l'invariante spettrale non è più presentato come autoimplementante. Le criticità principali residue sono obblighi di specificazione e composizione delle garanzie, non evidenza che l'architettura sia impossibile.

## Rilievi

### M1 — La proiezione non implementa anche il limite di aggiornamento

**Sezione 2.2; major per una specifica eseguibile; ambiguità operativa, non teorema falso esplicitamente enunciato.**

La formula definisce il candidato proiettandolo su P_i e affianca il vincolo di distanza da p_i^k. Il primo passaggio non garantisce il secondo. Per P=[0,10], p^k=0, proposta=10 e Delta=1, la proiezione restituisce 10, fuori dal budget. Il testo può essere interpretato come proiezione seguita da rigetto, ma non lo dice; non definisce inoltre esistenza, unicità o selezione della proiezione se P è non convesso.

**Correzione:** dichiarare esplicitamente se il candidato fuori budget viene rigettato oppure usare la proiezione su F_i^k = P_i ∩ {p: ||p−p_i^k||≤Delta_i}. Specificare norma, non-vuotezza, chiusura e, se si richiede unicità, convessità rispetto alla proiezione scelta; altrimenti una regola deterministica di selezione. Se cambia P_i, l'ultimo parametro approvato può non appartenere più a F_i^k: occorre un protocollo di migrazione o fallback.

**Chiusura verificabile:** casi di candidato fuori budget, insieme ammissibile vuoto e nuova policy incompatibile, tutti con esito prescritto. Il controesempio numerico è stato verificato.

### M2 — L'invarianza alla suddivisione delle celle non deriva dalla scelta dei soli pesi

**Sezioni 5.2, 6.1, 10.1; major; proprietà richiesta ma non costruita.**

Il testo richiede che rho_i impedisca guadagni artificiali suddividendo celle. Se i punteggi sono ottenuti normalizzando una media locale in modo non lineare, pesi additivi non bastano. Due porzioni di uguale peso con variabile fisica 0 e 1, e normalizzazione b(x)=x², danno punteggio fine 0.5·0²+0.5·1²=0.5; accorpate danno ((0+1)/2)²=0.25. La situazione fisica non cambia ma il punteggio sì. Un'analoga discrepanza si trasmette alla differenza controfattuale se varia con l'azione.

**Correzione:** definire una misura additiva mu su persone, aree o unità di servizio e densità di beneficio/danno su una granularità di riferimento. Porre rho_i U_i = integrale sulla cella di u(z) rispetto a mu, oppure prescrivere una regola di aggregazione equivalente. Se alcune variabili sono intrinsecamente non additive, dichiararne la sensibilità alla partizione invece di promettere invarianza universale. Richiedere rho_i≥0 e separare unità estensive da indicatori intensivi.

**Chiusura verificabile:** confronto accorpamento/suddivisione su stati eterogenei e normalizzazioni non lineari; uguaglianza entro tolleranza oppure errore di discretizzazione dichiarato. Il controesempio numerico è stato verificato.

### M3 — Il certificato di valore positivo richiede un dominio e una semantica dell'errore più precisi

**Sezioni 6.1–6.3; major; garanzia condizionale corretta in principio ma non ancora applicabile.**

V_hat−epsilon_model−epsilon_tail è un limite inferiore solo se gli epsilon limitano l'errore sulla stessa quantità incrementale, rispetto alla stessa policy, misura e finestra. Se ciascuna traiettoria ha errore massimo e, la differenza può avere errore 2e. Il testo non commette esplicitamente tale errore, ma non definisce quale quantità sia certificata. Il supporto temporale degli effetti oltre H rimane inoltre ambiguo: un'azione può avere valore positivo entro H e danno differito molto maggiore dopo H.

**Correzione:** definire un valore bersaglio V* e imporre, per esempio, |V_hat−V*_{Omega,H}|≤epsilon_model e V*−V*_{Omega,H}≥−epsilon_tail. Specificare se il tail copre spazio, tempo o entrambi, evitando duplicazioni. Se l'attesa è stimata via Monte Carlo, includere un termine statistico con livello di confidenza esplicito oppure dichiarare che il certificato non è computabile con i dati disponibili. Definire l'intervento a: durata, policy successiva e baseline; confrontare le stesse condizioni esogene non costituisce da solo identificazione causale da dati osservazionali.

**Chiusura verificabile:** esempio con esito vero noto nel simulatore, errori sulle due traiettorie di segno opposto, effetto post-H e verifica della copertura del limite dichiarato. La garanzia va riferita al simulatore/modello quando non si dispone di identificazione sul sistema reale.

### M4 — Contabilità dell'exergia e riferimenti tra celle da completare

**Sezione 4.2; minor nel programma di ricerca, bloccante per l'implementazione fisica.**

Il bilancio è dimensionalmente coerente. Tuttavia la confrontabilità dei flussi tra celle richiede un riferimento termodinamico comune o conversioni esplicite, con temperatura, pressione e composizione di riferimento pertinenti. La frase «declared reference environment» lascia aperta la possibilità di riferimenti locali incompatibili. Riferimenti variabili nel tempo richiedono inoltre attenzione ai termini aggiuntivi nel bilancio della grandezza definita rispetto a quel riferimento. Il simbolo X_min indica una soglia applicata a un flusso, mentre X_i è uno stock: la sua unità dovrebbe essere resa esplicita come watt.

**Correzione:** nel primo prototipo fissare un ambiente di riferimento comune e stazionario; definire unità e convenzioni dei flussi ai confini; rinominare la soglia P_X,min o dot X_min. Specificare per una singola tecnologia la potenza utile, gli ingressi e la contabilizzazione della variazione delle scorte.

**Chiusura verificabile:** sommando i bilanci delle celle, gli scambi interni si cancellano; rimangono variazione di stock, scambi esterni e distruzione. Nessuna pretesa di dedurre il valore sociale dal segno del flusso.

### M5 — Ipotesi dei diagnostici di fase non dichiarate nel punto d'uso

**Sezioni 7.1–7.2; minor; omissione di dominio.**

Gli intervalli C_i∈[0,1] e A_i∈[−1,1] richiedono w_ij≥0. La nonnegatività compare nella sezione spettrale 8.2 per il grafo non orientato, ma non è enunciata chiaramente per il modulo di fase, che può essere un oggetto distinto. Per pesi firmati la normalizzazione con la somma non conserva quei limiti. Se si vuole interpretare s_i/d_i come intensità in [0,1], servono anche w_ij≤1; altrimenti è semplicemente una media dei pesi. La dinamica stocastica dovrebbe precisare correlazione tra W_i, adattamento e regolarità dei pesi, e trattamento delle fasi modulo 2pi.

**Correzione:** dichiarare localmente pesi nonnegativi e, se desiderato, limitati; definire processo congiunto dei rumori e politica di aggiornamento dei pesi. Non è necessario imporre simmetria al modello di fase, ma le garanzie ricavate per Laplaciani simmetrici non vanno trasferite automaticamente.

**Chiusura verificabile:** test pesi nulli, molto piccoli e massimi, oltre ai casi già previsti. I diagnostici già presenti sono corretti sotto le ipotesi indicate.

### M6 — La monotonicità del punteggio è locale alle coordinate e alla versione della policy

**Sezione 5.2; minor, chiarimento necessario per evitare sovrainterpretazioni.**

La derivata parziale −beta_m è corretta. Non dimostra però che un'azione che aumenta un danno debba peggiorare il valore totale, perché può simultaneamente aumentare i benefici o ridurre altri danni. Il testo riconosce già questo limite nelle sezioni 5.1 e 6.3: non vi è contraddizione, ma la denominazione «noncancelling harms» nel registro può suggerire più di quanto sia provato. Inoltre normalizzazioni e policy variabili nel tempo devono essere condivise tra scenario con azione e baseline, altrimenti si misura anche un cambiamento di metro.

**Correzione:** descrivere la proprietà come «assenza di cancellazione moltiplicativa e monotonicità a coordinate fissate». Congelare la versione della funzione di valore nel confronto, o separare esplicitamente gli effetti dell'azione da quelli della revisione della policy. I danni non compensabili devono rimanere vincoli esterni, come già previsto.

**Chiusura verificabile:** distinguere test di monotonicità isolata, test di trade-off consentito e test di violazione inderogabile. Un aumento di danno compensabile può legittimamente accompagnarsi a un punteggio totale maggiore: non deve essere classificato come bug della nuova formula.

## Punti confermati

- La formula 1+3r(r+1) è corretta per palle del grafo dei centri esagonali; chiarire il duale a grado sei elimina l'ambiguità del reticolo originale.
- Il decadimento spettrale indicato è formulato con qualificazioni appropriate; non si promette una garanzia indipendente da N.
- La separazione tra entropia generata, stock di entropia, exergia e informazione è un miglioramento reale.
- Il confronto C_i/A_i risolve correttamente il problema della fase centrale. La distinzione tra rumore e libertà umana evita un'inferenza matematica ingiustificata.
- Il valore è presentato come stima con dipendenza dal modello, non come valuta oggettiva o teorema di ricchezza.

## Limiti e raccomandazione

Questo esame verifica coerenza formale e completezza delle condizioni, non originalità della ricerca né validità di un impianto fisico. Le fonti già riportate nel documento non bastano a costituire una rassegna di controllo robusto, causalità o termodinamica applicata. Non ho identificato una nuova contraddizione fatale che richieda abbandonare il progetto. Prima di chiamarlo specifica operativa, chiudere M1–M3 con un esempio end-to-end in un solo dominio e rendere esplicite le ipotesi M4–M6. Per un position paper, i medesimi punti possono essere presentati come obblighi della futura istanziazione, purché il titolo e il contributo siano calibrati di conseguenza.


---

## Appendice B Controllo e sistemi distribuiti

# Relazione del revisore su controllo software e sistemi distribuiti

Documento esaminato: Paradigm_6_0_Revised.md, versione corrente datata 14 novembre 2026. Revisione indipendente assistita da IA, basata sul testo; non audit del codice, certificazione o prova sperimentale.

## Giudizio

**Revisione maggiore per una specifica operativa; impianto utilizzabile come architettura di ricerca.** La separazione tra proposta adattiva, validazione ed esecuzione è coerente e il testo riconosce correttamente che determinismo, autenticazione, connettività e sicurezza fisica sono proprietà distinte. Le lacune sotto elencate non smentiscono esperimenti, perché il documento dichiara esplicitamente di non presentarne. Impediscono però a due implementatori indipendenti di costruire sistemi equivalenti o di riprodurre una garanzia.

Il contributo tecnico va posizionato rispetto alle architetture di runtime assurance e Simplex: non è sufficiente rivendicare originalità per la sola presenza di un supervisore adattivo e di un controllore fidato. Il framework NASA citato in fondo è un precedente pertinente, non una validazione di SPEACE.

## C1 Il contratto di sicurezza non include esplicitamente osservazione e latenza

**Gravità: major. Sezioni 1.3, 2.1 e 2.3. Tipo: specifica incompleta, non falso teorema.**

L'invarianza è formulata sullo stato fisico x, mentre il supervisore opera su stime, dati compressi e messaggi ritardati. Il testo non definisce l'insieme degli stati compatibili con una misura né come quell'insieme sia propagato fino all'istante effettivo di attuazione. Validare un comando rispetto allo stato stimato al tempo di campionamento non implica che sia sicuro quando viene applicato.

**Correzione richiesta:** definire modello di misura, errore ammesso, età massima del dato, tempo massimo di validazione e attuazione. Il validatore deve verificare il comando su un insieme raggiungibile che includa errore e ritardo, oppure usare un'altra garanzia esplicita e appropriata al dominio. Distinguere errore di stima limitato da perdita totale di osservabilità.

**Criterio di accettazione:** per un impianto minimo, mostrare che ogni stato compatibile con il contratto di osservazione resta nell'insieme sicuro durante il ritardo massimo e dopo l'azione approvata. Iniettare dati obsoleti e latenza superiore alla soglia, verificando il passaggio tempestivo alla modalità prevista.

## C2 Rollback dei parametri e recupero fisico sono operazioni diverse

**Gravità: major. Sezioni 2.2, 2.3 e articolo VI. Tipo: requisito operativo insufficiente.**

Una configurazione approvata in passato non è automaticamente applicabile allo stato attuale. Il cambiamento può aver modificato stock fisici, integratori del controllore, memoria dell'estimatore o configurazioni dei vicini. Ripristinare soltanto il vettore p non ripristina questi stati. Il testo avverte correttamente che il fallback va valutato, ma non specifica la condizione per rientrarvi.

**Correzione richiesta:** distinguere ripristino software, transizione del controllore e recupero dell'impianto. Definire regione di recuperabilità, trattamento dello stato interno del controllore e guardie di commutazione; includere isteresi o vincoli temporali quando necessari. La configurazione precedente va riesaminata rispetto allo stato corrente, salvo che un certificato già copra la transizione.

**Criterio di accettazione:** testare il rollback dopo accumulo fisico e integrale, non soltanto immediatamente dopo un aggiornamento. Esplicitare quali stati consentono il recupero e quali richiedono una diversa procedura. Nessun test deve chiamare «ripristino sicuro» il solo caricamento del vecchio file.

## C3 Il ciclo di vita degli aggiornamenti non è ancora un protocollo distribuito

**Gravità: major. Sezioni 2, 2.2 e 9. Tipo: specifica incompleta riconosciuta in parte dal testo.**

Versioning, expiry e coordinamento sono richiesti, ma non è definita la semantica di proposta, approvazione e attivazione. Un candidato può essere validato sulla versione k e arrivare dopo l'attivazione di k+1; messaggi duplicati o un riavvio possono applicarlo di nuovo. In una modifica a più celle, alcune possono effettuare l'attivazione mentre altre perdono il messaggio. Un timestamp da solo non stabilisce un ordinamento causale affidabile tra dispositivi.

**Correzione richiesta:** introdurre una macchina a stati con identificatore univoco, versione-base, hash dei parametri, epoca di policy, ambito, dipendenze, scadenza e attestazione di validazione. Definire l'applicazione idempotente, rifiuto delle versioni obsolete, persistenza dopo crash e fencing delle vecchie autorità. Per gli aggiornamenti accoppiati, scegliere un protocollo preciso oppure dimostrare la compatibilità delle attivazioni parziali; non è necessario imporre consenso globale a tutte le operazioni.

**Criterio di accettazione:** tracce riproducibili con duplicazione, riordinamento, partizione, crash tra approvazione e applicazione, e riconnessione. Ogni traccia deve preservare gli invarianti dichiarati oppure entrare in una modalità degradata specificata, senza doppia autorità di attuazione.

## C4 L'indipendenza del validatore è un requisito funzionale senza confine di fiducia

**Gravità: major. Sezioni 2, 3.3 e 9. Tipo: architettura di sicurezza da completare.**

Separare i dispositivi può ridurre alcuni guasti, ma non dimostra indipendenza se proposta e validazione condividono modello corrotto, alimentazione, credenziali, libreria vulnerabile o canale sensoriale. Il divieto di auto-riscrivere i permessi è corretto, ma manca l'identificazione del componente che effettivamente impedisce l'attuazione non autorizzata.

**Correzione richiesta:** definire la base fidata minima e il confine di attuazione: arbitro, permessi, aggiornamenti del validatore, dipendenze comuni e budget di risorse. Il proponente non deve poter saturare il validatore o aggirarlo attraverso un altro endpoint. Dichiarare quali guasti comuni restano fuori dal modello invece di suggerire indipendenza assoluta.

**Criterio di accettazione:** una matrice componente–privilegio–guasto e prove di bypass, esaurimento risorse, alterazione dei certificati, modello obsoleto e perdita di una dipendenza comune. La continuità di servizio dichiarata deve essere verificata anche quando il validatore non risponde.

## C5 L'ammissibilità deve essere ricorsivamente fattibile nel dominio scelto

**Gravità: major per la specifica operativa; requisito da istanziare per il programma di ricerca. Sezioni 2.3, 5.1 e 8.3.**

Il documento richiede correttamente invarianti e riconosce che l'insieme delle azioni può essere vuoto. Tuttavia, non descrive il legame tra insieme sicuro, scorte, service floor e capacità di mantenere una scelta ammissibile al passo successivo. Un'azione può rispettare i limiti immediati e consumare tutta la riserva necessaria al servizio successivo. L'escalation istituzionale non crea automaticamente risorse né può essere assunta istantanea.

**Correzione richiesta:** per il primo dominio, definire insieme robustamente controllato-invariante o condizione equivalente, riserve minime, orizzonte operativo e procedura per infeasibilità. Specificare la precedenza tra servizio nominale, servizio protetto e limiti fisici quando non sono simultaneamente realizzabili. Separare mantenimento della sicurezza da mantenimento di tutti gli obiettivi di servizio.

**Criterio di accettazione:** scenario con scarsità prolungata e domanda incompatibile; il sistema deve rilevare anticipatamente il deficit dove il modello lo permette e applicare la gerarchia dichiarata. La relazione di prova deve indicare quali garanzie cessano quando le ipotesi non valgono.

## C6 La proiezione non applica da sola il limite di aggiornamento

**Gravità: minor, correggibile localmente. Sezione 2.2. Tipo: ambiguità algoritmica.**

Il testo scrive p_cand = Pi_P(p_tilde) e, a fianco, impone ||p_cand-p_k|| ≤ Delta. La prima operazione non assicura la seconda. Per esempio, con P=[0,10], p_k=0, proposta 10 e Delta=1, la proiezione restituisce 10. Non è un errore se la disuguaglianza è intesa come test separato, ma il ramo di rifiuto non è scritto.

**Correzione richiesta:** indicare esplicitamente «proietta e poi rifiuta se il budget è superato», oppure proiettare sull'intersezione P ∩ B_Delta(p_k), definendo esistenza, eventuale non unicità e gestione dell'insieme vuoto. Nessuna di queste operazioni sostituisce il validatore fisico.

**Criterio di accettazione:** il caso numerico sopra deve produrre rifiuto o un candidato entro 1; il risultato e la ragione devono essere registrati.

## Punti già solidi da preservare

- Il testo evita l'equivalenza errata tra agente generativo e controllore deterministico.
- Il controllo locale non è subordinato a una risposta sincrona del supervisore.
- Compressione e sorpresa non diventano l'unico ingresso dei segnali critici.
- La revisione distingue connettività del grafo da capacità fisica e garanzie di servizio.
- Gli aggiornamenti accoppiati e la non sicurezza automatica del fallback sono già riconosciuti; i rilievi chiedono di trasformare questi avvertimenti in contratti eseguibili.
- Il confronto con baseline e la distinzione tra test finiti e garanzie sono appropriati.

## Riferimenti verificati e limiti

1. NASA, *A Verification Framework for Runtime Assurance of Autonomous UAS* (2024), https://ntrs.nasa.gov/citations/20240007986. Precedente primario per runtime assurance, commutazione e requisiti di campionamento; non prova di correttezza del Bridge proposto.
2. Leslie Lamport, *Time, Clocks, and the Ordering of Events in a Distributed System* (1978), https://lamport.org/pubs/time-clocks.pdf. Fondamento primario per distinguere ordinamento degli eventi e semplici timestamp.

Le osservazioni C1–C6 derivano dalla lettura delle sezioni indicate e da analisi di contratto, non da vulnerabilità osservate su un'implementazione. Non sono stati eseguiti test su un sistema SPEACE reale. Raccomandazione: aggiungere un allegato di riferimento per un singolo impianto e un protocollo Bridge minimo; solo dopo, valutare la generalizzazione a più domini.


---

## Appendice C Governance e sicurezza

# Relazione del revisore G

**Ambito:** governance, sicurezza avversariale, privacy, autonomia umana e distribuzione di benefici e danni.  
**Documento:** Paradigm_6_0_Revised.md, versione del 14 novembre 2026.  
**Metodo:** esame concettuale del testo completo e costruzione di scenari di fallimento; nessun test operativo, audit del codice o verifica di conformità giuridica. I rilievi riguardano la specifica proposta, non un sistema implementato.

## Giudizio

**Revisione maggiore per una specifica operativa; proposta di ricerca promettente e utilizzabile come agenda, ma incompleta.** Non emergono, nel mio ambito, motivi per respingere il principio del Bridge. La revisione distingue correttamente legittimità, misura e controllo. Tuttavia, alcune proprietà cruciali sono demandate a futuri accordi senza specificare il loro contratto minimo. Per un documento programmatico è una limitazione dichiarabile; per qualificare un prototipo come conforme è un ostacolo sostanziale.

Non giudico l'assenza di risultati sperimentali una contraddizione: il documento la dichiara. Il problema è che alcune prove necessarie per governance e sicurezza non sono ancora inserite nel programma sperimentale.

## Punti forti

- §§3.1–3.2 separano giustamente autonomia umana, restrizioni verificabili automaticamente e giudizio istituzionale.
- §§5–6 evitano che un indice annulli matematicamente un danno negativo e riconoscono che un totale positivo non basta a tutelare ciascun gruppo.
- §9 distingue autenticità del messaggio e verità fisica, incluso il limite delle misure colluse.
- §§2.3, 8.3 e 9 riconoscono che arresto o isolamento non equivalgono automaticamente a sicurezza e proteggono la continuità dei servizi.
- La carta normativa esclude l'indispensabilità e la resistenza alla supervisione legittima come obiettivi del sistema. Questa è una scelta progettuale importante e coerente con la verificabilità.

## Rilievi prioritari

### G1 — Le autorità e la risoluzione dei conflitti restano un requisito senza protocollo minimo

**Gravità:** maggiore, lacuna operativa. **Sezioni:** 3.2–3.3, 5.1, 8.3, 11 articoli III–V.

Il testo richiede di identificare proprietari, veto, appelli ed emergenze, ma non definisce come prevalgano decisioni incompatibili tra celle. La policentricità può significare autorità distribuita oppure una serie di veti inconciliabili. Riconoscere il problema non specifica il comportamento dell'architettura.

**Scenario:** durante una carenza, due comunità invocano quote protette incompatibili; un ente dispone una redistribuzione e un altro la vieta. Il sistema non dispone di una decisione ammissibile. Un'escalation senza termine può trasformarsi in sospensione indefinita del servizio o in una scelta discrezionale dell'operatore tecnico.

**Correzione:** introdurre un contratto di governance minimo per il pilota: ruoli e competenze, rappresentanza degli interessati anche esterni, categorie di decisioni non delegabili, priorità tra vincoli, autorità di risoluzione, tempi di risposta, regola provvisoria durante il ricorso, motivazione registrata e riesame. Non è necessario scegliere una costituzione planetaria, ma occorre un esempio eseguibile per un solo dominio.

**Criterio di accettazione:** esercitazione documentata di conflitto fra due celle e scarsità fisicamente inevitabile, con decisione entro un tempo dichiarato, traccia dell'autorità competente e trattamento esplicito degli utenti che rimangono sotto il livello di servizio ordinario.

### G2 — Indipendenza del validatore e controllo del ciclo di vita non sono sufficientemente definite

**Gravità:** maggiore, lacuna di assurance. **Sezioni:** 2, 2.2, 3.3, 9, 10.1.

La separazione del proponente dal validatore è positiva. La frase «may be separated across devices» non stabilisce però un confine di fiducia. Due processi o dispositivi amministrati dalla stessa credenziale compromessa possono essere modificati insieme. Il divieto per q_speace di riscrivere i propri permessi non copre la cattura dell'amministratore o della distribuzione software.

**Scenario:** una chiave di manutenzione autorizza sia l'aggiornamento del modello sia quello dei limiti del validatore. Un attacco a quella chiave fa approvare aggiornamenti nominalmente autorizzati ma dannosi; il test «q_speace cannot bypass validation» continua a passare perché il bypass avviene nel piano amministrativo.

**Correzione:** definire ruoli, credenziali e dipendenze del piano di controllo; accessi consentiti tra proponente, validatore e attuazione; procedura di revisione degli aggiornamenti; revoca e recupero delle chiavi; log verificabili fuori dal dominio compromesso. L'indipendenza richiesta va espressa rispetto a un modello di compromissione, non al numero di macchine.

**Criterio di accettazione:** prove con compromissione separata del proponente, di un account di manutenzione e di una fonte di aggiornamento; per ogni caso indicare le modifiche ancora possibili e dimostrare che non superino il confine dichiarato. Non pretendere immunità alla compromissione simultanea di tutte le autorità.

### G3 — Mancano decisioni di ammissione e isolamento verificabili sotto collusione

**Gravità:** maggiore per il prototipo distribuito. **Sezioni:** 8.3, 9, 10.1–10.2.

Il threat model elenca correttamente identità multiple, replay e collusione, ma resta un catalogo. Il testo chiede di specificare membership e fault tolerance senza scegliere un profilo minimo per il pilota. Non è ancora possibile verificare che un gruppo di vicini non possa fabbricare autorità, confermare dati falsi o espellere una cella scomoda.

**Scenario:** celle colluse denunciano una cella onesta come inaffidabile oppure confermano misure reciprocamente coerenti ma false. L'esclusione dei privilegi di controllo può avere effetti materiali anche quando il servizio minimo è formalmente preservato.

**Correzione:** istanziare il protocollo del pilota: ammissione e identità, numero o classe di guasti assunti, criteri e autorità di quarantena, scadenza e revoca della quarantena, canale di ricorso, trattamento di un'autorità compromessa. Distinguere la rilevazione dell'anomalia, l'attribuzione della responsabilità e l'azione di contenimento.

**Criterio di accettazione:** scenari di falsa accusa, replay, identità aggiunta abusivamente e collusione entro/fuori l'envelope dichiarato, con tassi di falso isolamento e tempi di ripristino riportati. L'esito «non rilevabile sotto queste assunzioni» è accettabile come limite esplicito, non come successo di rilevazione.

### G4 — Il reporting per cella non basta a controllare danni concentrati e cumulativi

**Gravità:** maggiore, incompletezza del modello distributivo. **Sezioni:** 5.2, 6.1–6.3, 8.3, 10.

Il testo riconosce le perdite locali e impone soglie esterne allo score, ma non definisce l'unità dei soggetti protetti né l'orizzonte cumulativo. Una cella può aggregare gruppi con bisogni diversi. Inoltre, una sequenza di azioni ammissibili isolate può gravare ripetutamente sugli stessi utenti senza violare una soglia istantanea.

**Scenario:** il controllore riduce ogni giorno, entro i limiti per singolo intervento, il servizio allo stesso quartiere per migliorare il bilancio complessivo. Il servizio medio della cella e il punteggio totale migliorano mentre un gruppo subisce un carico sproporzionato. È un esempio di lacuna, non la dimostrazione che lo score provochi necessariamente tale comportamento.

**Correzione:** dichiarare unità e gruppi di valutazione pertinenti, profili di bisogno, limiti di durata e accumulo, trattamento dei dati mancanti, revisione di pesi e normalizzazioni, e regole per lo stato di scarsità. Se il dato distributivo è indisponibile per ragioni di privacy, rappresentare l'incertezza anziché assumere equità.

**Criterio di accettazione:** due scenari con lo stesso beneficio aggregato ma diversa concentrazione e persistenza del danno devono risultare distinguibili nel report; una sequenza che supera il limite cumulativo dichiarato deve essere bloccata o escalata indipendentemente dal punteggio totale.

### G5 — La privacy necessita di una mappa dei flussi e di una regola per gli audit

**Gravità:** maggiore prima del pilota con dati umani; non blocca una simulazione sintetica. **Sezioni:** 2.1, 3.4, 9, 11 articolo II.

Minimizzazione, retention e accessi sono correttamente richiamati. Rimane una tensione concreta tra canali grezzi conservati, prove indipendenti e registri consultabili. La telemetria può rivelare abitudini anche senza un esplicito «agency score». Il documento non identifica quali dati lascino una cella né quali informazioni siano necessarie a ciascun revisore.

**Scenario:** serie temporali di consumo, unite a timestamp e log delle richieste, consentono a un vicino o a un auditor di inferire presenze e routine personali; l'aggregazione di un solo flusso non risolve la correlazione tra flussi.

**Correzione:** aggiungere inventario dei dati, diagramma dei flussi, scopi, destinatari, granularità, durata, regola di eliminazione e accessi d'emergenza. Separare evidenza tecnica per auditor autorizzati dal reporting pubblico. Se si usa differential privacy, dichiarare unità protetta, meccanismo, budget e composizione temporale, insieme al costo di utilità; non imporla indiscriminatamente ai segnali di controllo.

**Criterio di accettazione:** un test di ricostruzione o linkage sul dataset dimostrativo, più una verifica degli accessi e della cancellazione, con risultati e limiti espliciti. Nessun dato umano reale è necessario per i primi esperimenti.

### G6 — I gate sperimentali non verificano ancora le principali promesse normative

**Gravità:** maggiore per la tracciabilità, risolvibile editorialmente e progettualmente. **Sezioni:** 10.1–10.5 rispetto a 3 e 11.

Le ipotesi H1–H4 misurano soprattutto prestazioni, validazione e causalità. Non coprono direttamente ricorsi, poteri d'emergenza, conflitti tra autorità, discriminazione cumulativa o inferenze sui dati. Documentare responsabilità non equivale a dimostrare che una procedura funzioni.

**Correzione:** aggiungere una matrice requisito–minaccia–controllo–evidenza–responsabile. Per le promesse normative usare esercitazioni procedurali e verifiche di accesso, senza fingere che ogni diritto sia un test unitario. Rendere esplicito quali gate sono tecnici e quali richiedono decisione istituzionale motivata.

**Criterio di accettazione:** per ciascun impegno operativo della carta, indicare almeno una procedura, un responsabile e un'evidenza richiesta oppure dichiararlo fuori ambito del pilota. Nessun gate dovrebbe essere chiuso soltanto perché il punteggio di prestazione è positivo.

## Decisione e priorità

Per il prossimo ciclo suggerisco un unico caso d'uso sintetico, con un contratto di governance compilato e un profilo di minaccia realistico. G1–G3 sono necessari per dichiarare specificato il comportamento di un prototipo distribuito; G4–G6 collegano l'architettura alle promesse sociali e alle condizioni di un successivo pilota.

La proposta è coerente nel rifiutare l'equivalenza tra metrica, verità e legittimità. Deve ora rendere verificabile questa distinzione anche quando le autorità dissentono, le risorse non bastano o la fonte nominalmente fidata è compromessa. Non vi sono basi, nel documento esaminato, per affermare prontezza al deployment; esistono basi per un programma di ricerca locale ben delimitato.

## Limiti del riesame

Questa è una revisione assistita da un agente, non una peer review editoriale esterna né un parere legale. I rilievi sono deduzioni dai requisiti e dalle omissioni del testo: non sono risultati di attacchi realmente eseguiti. Non è stata esaminata l'originalità rispetto alla letteratura, affidata agli altri revisori.


---

## Appendice D Metodo sperimentale

# Revisore M — Metodo sperimentale e inferenza causale

Documento esaminato: `Paradigm_6_0_Revised.md`, versione corrente del 14 novembre 2026, 4.260 parole. Revisione indipendente di un agente AI, basata sulla lettura integrale. Nessun esperimento eseguito; nessuna verifica dell'implementazione implicita nel giudizio.

## Giudizio

**Revisione maggiore per una specifica sperimentale operativa; buona base per un programma di ricerca concettuale.** L'assenza di risultati è dichiarata correttamente e non è, da sola, un difetto per questo genere di documento. Il limite sostanziale è che H1–H4 sono ancora famiglie di ipotesi: mancano le scelte che permetterebbero a due gruppi indipendenti di eseguire lo stesso test e ottenere un verdetto confrontabile. Non rilevo in questo ambito una contraddizione che renda impossibile il progetto; rilevo sei lacune o ambiguità che impediscono di attribuire un eventuale vantaggio a q_speace con sufficiente precisione.

## Elementi metodologici validi

- Il testo distingue correttamente proposta, requisito, stima e risultato.
- Introduce confronti con controllo locale e supervisione adattiva convenzionale, budget confrontabili, ablation e preregistrazione.
- Separa l'ammissibilità dalla massimizzazione del punteggio e non presenta una simulazione senza violazioni come prova universale di sicurezza.
- Riconosce che il controfattuale dipende dal modello, che le esternalità possono essere nonlocali e che le azioni simultanee non possono essere attribuite come indipendenti.
- Limita correttamente la generalizzazione: un successo locale non dimostra un organismo planetario cosciente.

## Rilievi

### M1 — Il trattamento sperimentale q_speace non è ancora identificato

**Gravità:** maggiore. **Sezioni:** 1.3, 10.2–10.4.

q_speace è definito da funzioni che possono essere svolte anche dalla supervisione adattiva convenzionale scelta come baseline. Non sono fissati algoritmo, regola di apprendimento, memoria, parametri modificabili, periodicità di aggiornamento e stato iniziale. Un confronto tra due implementazioni arbitrarie può dunque misurare qualità di implementazione, tuning o informazione aggiuntiva anziché il contributo architetturale proposto.

**Correzione richiesta:** definire una realizzazione minima q_speace-v0 e un elenco di differenze rispetto a una baseline nominata. Separare l'effetto del Bridge, quello del predittore e quello dell'adattamento; usare lo stesso plant, lo stesso validatore e la stessa interfaccia di osservazione nel confronto principale. Dichiarare anche budget di tuning e dati di addestramento, oltre al costo di inferenza.

**Criterio di accettazione:** tabella dei componenti identici/diversi per ogni braccio, configurazioni congelate prima dei test e pacchetto eseguibile o pseudocodice sufficientemente completo da ricostruirle.

### M2 — H1 consente selezione favorevole degli esiti e non specifica il test di sicurezza

**Gravità:** maggiore. **Sezioni:** 10.2 e 10.4, H1.

La frase «recovery time or cumulative service shortfall» lascia aperta la scelta post hoc dell'esito favorevole. Anche «strongest matched baseline» deve essere selezionata su dati diversi dal test finale. La semplice permanenza sotto una tolleranza dichiarata non specifica se si confrontino probabilità di violazione, numero, durata o severità, né con quale incertezza. Un sistema può recuperare prima ma violare più spesso i vincoli durante il recupero.

**Correzione richiesta:** scegliere un endpoint primario oppure dichiarare esplicitamente una regola per endpoint multipli; fissare margine di miglioramento pratico, regola di selezione baseline, criterio di non inferiorità per sicurezza, intervalli e gestione dei fallimenti. Le violazioni rare richiedono una valutazione distinta dall'accuratezza media.

**Criterio di accettazione:** una regola di pass/fail decidibile prima di osservare i dati, che includa miglioramento primario e contemporaneo rispetto del criterio di sicurezza. Report separato di gravità, esposizione e casi non recuperati.

### M3 — L'unità statistica e il trattamento della dipendenza sono mancanti

**Gravità:** maggiore. **Sezioni:** 10.2–10.4.

Il testo richiede distribuzioni su seed e scenari, ma non definisce le repliche indipendenti. Le 19 o 37 celle interagiscono, e le misure successive della stessa traiettoria sono dipendenti: non possono essere trattate automaticamente come altrettanti campioni indipendenti. Un elevato numero di tick potrebbe produrre intervalli artificialmente stretti senza aumentare il numero di esperimenti indipendenti.

**Correzione richiesta:** usare la traiettoria completa della rete come unità sperimentale di base; distinguere repliche di scenario, casualità del plant e casualità dell'algoritmo. Accoppiare i bracci sugli stessi disturbi esogeni quando appropriato, separando i flussi casuali dipendenti dalla politica. Definire numerosità tramite potenza o precisione desiderata e procedura di stima che rispetti la struttura gerarchica.

**Criterio di accettazione:** piano statistico con unità, numero di repliche, metodo degli intervalli, dati mancanti/fallimenti, arresto e correzioni per confronti multipli; pubblicazione delle differenze per traiettoria, non soltanto delle medie di cella.

### M4 — La valutazione causale può diventare circolare

**Gravità:** maggiore. **Sezioni:** 6.1–6.3, 10.1, H3.

Il documento riconosce i limiti del modello ma non separa esplicitamente il modello usato dal decisore da quello che genera e valuta gli esiti sperimentali. Se lo stesso modello costruisce la stima di V e il simulatore con cui se ne giudica la bontà, un risultato positivo può riflettere coerenza interna più che capacità di rilevare esternalità non previste. In una rete con interferenza, il trattamento è inoltre una politica congiunta o una sequenza d'interventi, non necessariamente una singola azione isolata.

**Correzione richiesta:** definire l'estimando — intervento, baseline, orizzonte e popolazione/celle interessate — e distinguere modello del controllore, simulatore di riferimento ed eventuali dati osservati. Includere dinamiche e canali di esternalità nascosti al decisore, perturbazioni dei parametri e famiglie di modelli non impiegate nel tuning. Le stime controfattuali reali richiedono ipotesi d'identificazione dichiarate; l'abbinamento degli scenari in simulazione non le dimostra per il mondo reale.

**Criterio di accettazione:** H3 testata su casi con segno ed entità dell'esternalità noti al valutatore ma non forniti direttamente al decisore, con tassi di falsi positivi/negativi e casi «non determinabile». Giudizio separato di accuratezza sotto modello corretto e robustezza al modello errato.

### M5 — H2 richiede un riferimento indipendente per etichettare le proposte

**Gravità:** maggiore. **Sezioni:** 2.3, 10.1 e 10.4, H2.

H2 distingue proposte dannose e falsi rifiuti, ma non definisce come stabilirne le etichette. Usare il medesimo validatore come giudice della propria correttezza renderebbe il test tautologico. Anche un validatore che rifiuta tutto elimina gli aggiornamenti dannosi: la proposta di misurare falsi rifiuti è corretta, ma va resa operativa insieme al costo dei ritardi e degli errori accettati.

**Correzione richiesta:** costruire una suite etichettata indipendentemente, usando casi analiticamente risolvibili, esplorazione esaustiva su sistemi piccoli o un riferimento di simulazione distinto. Separare errori certi da casi indecidibili entro il budget. Specificare falsi accettati dannosi, falsi rifiuti, astensioni, latenza e utilità degli aggiornamenti consentiti.

**Criterio di accettazione:** il sistema «rifiuta tutto» fallisce il requisito di utilità; il sistema «accetta tutto» fallisce quello di protezione. Il validatore proposto deve soddisfare soglie preregistrate su entrambi, senza valutare le proprie etichette.

### M6 — H4 è ambigua sul significato di ablation

**Gravità:** minore nella formulazione, maggiore per l'attribuzione se non corretta. **Sezioni:** 10.3–10.4, H4.

«Any claimed advantage ... persists in component ablations» può significare che il vantaggio debba persistere persino quando si rimuove il componente cui lo si attribuisce. Ma in quel caso l'evidenza a favore del suo contributo sarebbe più debole, non più forte. Eliminare un modulo può inoltre rendere la baseline artificialmente non funzionante.

**Correzione richiesta:** sostituire H4 con: «L'aggiunta del componente C, rispetto alla sua sostituzione con un'alternativa specificata e funzionante, produce un effetto incrementale preregistrato sotto budget confrontabili; l'effetto è robusto alle ablation di componenti non essenziali e alle variazioni di scenario dichiarate». Se si ipotizzano interazioni, prevedere confronti fattoriali limitati e motivati.

**Criterio di accettazione:** contrasto definito per ogni componente rivendicato, sostituto convenzionale operativo, intervallo sull'effetto incrementale e resoconto degli effetti di interazione. Nessun obbligo che un vantaggio sopravviva alla rimozione della propria causa.

## Indicazione editoriale conclusiva

Non chiederei ora di dimostrare una superiorità planetaria, né penalizzerei il manoscritto per non avere risultati che dichiara assenti. Chiederei un **allegato sperimentale vincolante per un solo dominio**: plant, q_speace-v0, baseline, scenari, dataset/tuning/test, metriche, regole decisionali, unità sperimentale e configurazioni riproducibili. Con tale allegato il documento potrebbe diventare un protocollo di ricerca valutabile prima dell'esperimento. Nella forma corrente è una specifica di requisiti del programma, non ancora un protocollo eseguibile.

I rilievi derivano direttamente dalla struttura interna delle ipotesi e del disegno proposto. Non è stata svolta una revisione sistematica della letteratura statistica o dei benchmark esistenti.


---

## Appendice E Revisione editoriale

# Relazione E — Revisione editoriale e posizionamento scientifico

Documento esaminato: *Paradigm 6.0 — Cybernetic Architecture Mathematical Primitives and Operational Research Specification*, revisione 14 novembre 2026, circa 4.260 parole. Revisore: agente AI incaricato del livello editoriale, contributo e letteratura. La revisione riguarda il testo e un confronto bibliografico mirato; non è una certificazione, una revisione sistematica della letteratura o una valutazione di codice.

## Giudizio

**Revisione maggiore per una proposta architetturale o position paper; non ancora valutabile come articolo di risultati sperimentali.** Il documento esplicita correttamente che non presenta risultati e non va penalizzato per non essere ciò che dichiara di non essere. Tuttavia, anche una proposta di ricerca deve identificare con precisione il contributo rispetto a precedenti pertinenti, formulare un caso applicativo circoscritto e consentire di capire quali requisiti definiscano la conformità.

Il testo ha migliorato nettamente la disciplina delle affermazioni: separa aspirazioni, misure, scelte normative e garanzie condizionate. L'assenza di una pretesa dimostrazione della coscienza è appropriata. Le sezioni 5 e 6 delimitano bene ciò che una formula aggregata può e non può attestare. Il problema editoriale dominante non è più l'eccesso di assertività: è la difficoltà di identificare una proposta positiva sufficientemente specifica tra numerose correzioni, condizioni e opzioni.

## E1 — Contributo originale non ancora delimitato

**Gravità: major. Sezioni: abstract, 1.1–1.3, 2, 12, riferimenti.**

La conclusione identifica il Bridge come contributo centrale, ma la bibliografia non include i precedenti più vicini alla separazione fra componente adattiva, validazione e comportamento di riserva. Simplex era già motivato dagli aggiornamenti online sicuri di componenti industriali in presenza di errori nei moduli nuovi [E-R1]. Neural Simplex tratta controllori neurali, supervisione, fallback e miglioramento online [E-R2]. Questi precedenti non dimostrano che Paradigm 6.0 sia privo di originalità; rendono però necessario spiegare quale differenza concreta esso introduce.

**Correzione richiesta:** aggiungere una sezione di lavori correlati e una matrice di confronto: autorità esecutiva; filtro di azioni o di aggiornamenti dei parametri; garanzie; distribuzione e asincronia; trattamento delle esternalità; governance. Distinguere componenti adottate, estese e soltanto proposte. Una possibile originalità è l'integrazione di adattamento verificato, contabilizzazione delle esternalità e governance policentrica, ma resta da argomentare e verificare.

**Criterio di accettazione:** ogni contributo dichiarato deve avere un precedente pertinente, una differenza identificabile e una prova o esperimento capace di mettere alla prova quella differenza. Evitare sia la pretesa di inventare il controllo supervisore sia una dichiarazione affrettata di assenza di originalità.

## E2 — Manca un esempio completo che renda unitaria l'architettura

**Gravità: major. Sezioni: 1.2, 4–8, 10.2.**

Le sezioni sono individualmente comprensibili, ma restano generiche: non si vede ancora una misura attraversare il Bridge, produrre un parametro candidato, essere approvata o respinta e modificare un servizio. Le 19 o 37 celle specificano una geometria, non il problema scientifico. Senza una singola istanza, termini come servizio, danno, confine causale e parametro adattivo possono assumere significati diversi da una sezione all'altra.

**Correzione richiesta:** aggiungere un esempio end-to-end in un solo dominio, per esempio una rete simulata di serbatoi e pompe o una microrete energetica. Specificare sensori, stato, attuatori, parametro aggiornabile, tempi, limite fisico, beneficio, danno, caso di rifiuto e funzionamento degradato. Le scelte numeriche devono essere etichettate come configurazione proposta, non come dati sperimentali.

**Criterio di accettazione:** un lettore deve poter tracciare una singola decisione dall'osservazione all'esito e assegnare a ogni simbolo rilevante una grandezza concreta. Un esempio lavorato è sufficiente per il position paper; un articolo di risultati richiederebbe implementazione e misure.

## E3 — Il contratto di conformità non è ancora verificabile

**Gravità: major per una operational specification; moderata per un position paper. Sezioni: Status and scope, 2–3, 9–10.**

La dichiarazione iniziale assegna a “must” il significato di requisito per un prototipo conforme. Nel seguito, però, molti requisiti rinviano a decisioni future senza identificare un artefatto o un responsabile. “Preserve the information needed” e “specify membership, tolerated faults, timing assumptions” sono obblighi ragionevoli, ma non definiscono ancora quando una implementazione può dichiararsi conforme al documento.

**Correzione richiesta:** aggiungere una tabella con identificativo requisito, livello obbligatorio/opzionale, responsabile, artefatto richiesto, verifica e stato. Per esempio: BR-01 schema messaggi; BR-02 budget temporale; GOV-01 processo aggiornamento policy; EXP-01 protocollo preregistrato. Distinguere conformità documentale, conformità del prototipo e validazione prestazionale.

**Criterio di accettazione:** due revisori devono poter classificare gli stessi artefatti come soddisfatti, non soddisfatti o non applicabili senza dover inventare soglie. In alternativa, rinominare il lavoro come “architecture and research agenda” e rinviare esplicitamente la specifica normativa a un allegato futuro.

## E4 — La versione revisionata dipende troppo dalla confutazione della versione precedente

**Gravità: minor. Sezioni: 1.1, 3.1, 4.3, 5.2, 7.2, 8.1, Revision record.**

La discussione delle formule eliminate e delle equivalenze respinte è utile nel percorso di revisione, ma interrompe la definizione del sistema per un lettore nuovo. La presenza del registro revisioni permette già di conservare tale tracciabilità.

**Correzione richiesta:** mantenere nel corpo soltanto le distinzioni necessarie a comprendere la nuova architettura; spostare le confutazioni dettagliate del vecchio indice, di Landauer come valore semantico e della precedente formula di fase in un'appendice tecnica delle revisioni. Presentare prima il meccanismo positivo, poi i suoi limiti.

**Criterio di accettazione:** il corpo deve essere leggibile senza conoscere il precedente manoscritto, e ciascuna sezione deve chiarire prima quale oggetto viene definito e come viene utilizzato.

## E5 — Nucleo obbligatorio e moduli opzionali non sono separati abbastanza

**Gravità: minor, con effetti sul disegno degli esperimenti. Sezioni: 1.3, 4.1, 7, 8.1, 10.3–10.4.**

Spiking, quantum-inspired, Digital DNA, memoria, fasi e reticolo esagonale compaiono come opzioni o candidati. Non è però esplicitato quali siano necessari perché un prototipo sia qualificato come q_speace. Il rischio è che il nome cambi significato tra benchmark e ablation: un risultato negativo potrebbe essere attribuito a un'altra variante non testata.

**Correzione richiesta:** inserire una configurazione minima congelata e una lista di estensioni. Per ogni estensione, specificare il meccanismo ipotizzato, il costo e l'esperimento che ne giustificherebbe l'inclusione. “Quantum-inspired” deve indicare una rappresentazione o operazione concreta; non basta il nome.

**Criterio di accettazione:** H1 deve riferirsi a un'unica configurazione descritta; H4 deve elencare componenti realmente presenti in essa. I moduli non implementati rimangono nella roadmap.

## Valutazione per destinazione editoriale

| Destinazione | Valutazione |
|---|---|
| Documento di lavoro interno | Utile già ora per organizzare requisiti e discussioni |
| Position paper interdisciplinare | Candidato credibile dopo E1 ed E2 e chiarimento del tipo di contributo |
| Specifica implementabile | Richiede E2, E3, configurazione minima e dettagli tecnici aggiuntivi |
| Articolo sperimentale o di controllo formale | Non pronto: mancano implementazione, risultati o teoremi corrispondenti |

## Fonti primarie consultate

E-R1. Lui Sha, *A Software Architecture for Dependable and Evolvable Industrial Computing Systems*, CMU/SEI-95-TR-005, 1995. Pagina ufficiale e abstract: https://www.sei.cmu.edu/library/a-software-architecture-for-dependable-and-evolvable-industrial-computing-systems/ . Il confronto qui usa soltanto la finalità documentata di aggiornamento online affidabile; non attribuisce a Simplex tutte le proprietà del Bridge.

E-R2. Dung T. Phan et al., *Neural Simplex Architecture*, arXiv:1908.00528v2, 2020, NASA Formal Methods. https://arxiv.org/abs/1908.00528 . Il confronto qui usa architettura neurale, fallback e miglioramento online descritti dagli autori; non afferma equivalenza con la modulazione distribuita dei parametri.

Le fonti sono state consultate in modo mirato: non costituiscono una ricerca esaustiva di anteriorità. Non viene formulato un giudizio legale o brevettuale di novità.
