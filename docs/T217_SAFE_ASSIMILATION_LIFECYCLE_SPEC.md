# T217 — Assimilazione selettiva: simulazione, replica isolata e prototipo fisico

**Stato:** proposta ingegneristica sperimentale; requisiti per implementazioni future.  
**Data:** 2026-11-03.  
**Ambito:** modifica e integrazione di componenti Q-SPEACE in un sistema ospitante,
con particolare riguardo a funzioni cyber-fisiche, economiche e ambientali.  
**Implementazione attuale:** questa specifica non introduce un motore di simulazione,
un clone, un gateway di rilascio, un collegamento hardware o un permesso operativo.

## 1. Decisione e significato dei termini

Prima dell'assimilazione si corregge il candidato, lo si verifica in simulazione,
lo si integra in una replica isolata del sistema ospitante collegata a un prototipo
del suo ambiente operativo, e si valutano benefici e rischi. Soltanto le componenti
con evidenze sufficienti possono essere proposte per un'integrazione selettiva,
limitata e monitorata nel sistema principale. Un risultato negativo o inconcludente
non autorizza l'avanzamento.

In questa specifica:

- **candidato** è una modifica versionata di codice, configurazione, modello o dati;
- **cervello** indica il software di coordinamento, non una coscienza;
- **corpo/prototipo organismico** indica sensori, attuatori, reti e risorse di un
  banco prova, senza implicare proprietà biologiche;
- **clone/replica** indica un'istanza separata e identificata del sistema ospitante;
- **assimilazione** indica l'integrazione controllata di componenti esplicite, mai
  l'importazione indiscriminata dell'intero progetto;
- **VR** indica un'interfaccia immersiva facoltativa a modelli di simulazione:
  il realismo visivo non costituisce validazione scientifica.

Non si presume di poter clonare il modello o l'infrastruttura dell'assistente
che redige un documento. Una replica deve essere effettivamente disponibile e
identificabile. Un modello sostitutivo o un servizio dalla revisione non verificabile
va dichiarato tale: non può essere qualificato come clone equivalente.

Questa procedura integra [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md) e
[T210](T210_RESILIENT_AGENTIC_SMART_CITIES_SPEC.md). Non rimuove i limiti passivi di
[T60](../cellular_speace/docs/CYBER_PHYSICAL_ASSIMILATION_INTERFACE_SPEC.md) né
conferisce nuove autorizzazioni a
[T50](../cellular_speace/docs/SAFE_ARCHITECTURE_PATCH_EXECUTION_SPEC.md).
Gli identificatori T217.* qui sotto non rinumerano i task storici T209–T216.

## 2. Invarianti

1. Nessuna affermazione di coscienza quantistica o soggettività.
2. L'entanglement è solo una risorsa computazionale; la comunicazione usa canali
   espliciti e rispetta il no-communication theorem.
3. Nessun backend quantistico reale senza `QuantumGeneSet.noise_model` configurato,
   budget energetico, gate Sevo, limite di shot e registrazione riproducibile.
4. Il candidato, il modello generativo e i simulatori non possono auto-approvare
   promozioni, aumentare privilegi o modificare criteri, evidenze e audit del valutatore.
5. L'output generativo resta una proposta non fidata. Il controllo deterministico
   indipendente mantiene l'autorità sull'esecuzione, anche dopo l'integrazione.
6. Simulazione e sandbox non possiedono credenziali, percorsi di scrittura, canali
   di comando o collegamenti ad attuatori del sistema principale. I canali di test
   sono esplicitamente autorizzati, segregati e registrati.
7. Gli esiti favorevoli valgono soltanto per il perimetro e l'artefatto qualificati.
   Nessun test equivale a garanzia di assenza di danni o di effetti sconosciuti.

## 3. Perimetro planetario e fedeltà dei modelli

L'obiettivo di lungo termine è studiare le interazioni tra sistemi tecnologici,
ambiente naturale e attività umane. Riprodurre integralmente tutte le leggi fisiche,
chimiche, biologiche e tutte le dinamiche planetarie non è un criterio di uscita
verificabile. Ogni campagna deve quindi dichiarare:

- dominio operativo ammesso, confini, scale spaziali e temporali;
- modelli fisici, chimici, biologici/ecologici, tecnologici ed economici coinvolti,
  con equazioni o regole, unità, fonti dei dati e versioni;
- ipotesi, parametri, risoluzione, tolleranze, condizioni al contorno e fenomeni omessi;
- accoppiamenti fra domini, ritardi, dipendenze e possibili cascate di guasti;
- bilanci conservativi pertinenti: massa, energia, carica e risorse; un punteggio
  informativo non può essere usato come misura fisica senza validazione;
- incertezza dei dati e del modello, calibrazione, validazione su osservazioni
  indipendenti e condizioni in cui il modello non è utilizzabile;
- criterio per trasferire evidenze da simulazione a prototipo e dal prototipo al
  dominio reale, senza estrapolare automaticamente da piccola scala a scala planetaria.

Si possono federare modelli con diversi livelli di dettaglio. Si devono verificare
unità, scambio di stato, sincronizzazione, convergenza numerica e assenza di
informazioni dal futuro fra simulatori. La VR visualizza gli stessi stati e non
introduce una verità alternativa rispetto al motore non grafico.

Un dominio escluso può essere marcato non pertinente solo con motivazione e confini
di interfaccia verificati. Se un fenomeno escluso o un'incertezza non quantificata
può modificare un esito di sicurezza, il candidato rimane **inconcludente** per
quel dominio: non si assume che l'effetto sia nullo.

## 4. Ciclo di qualificazione

```text
S0 Specifica, BCEL, baseline e criteri preregistrati
 -> S1 Correzione del candidato e verifiche del codice
 -> S2 Validazione dei modelli e simulazioni multidominio (VR facoltativa)
 -> S3 Assimilazione nella replica software isolata del sistema ospitante
 -> S4 Prove reali su prototipo confinato / hardware-in-the-loop
 -> S5 Valutazione indipendente del dossier e decisione esplicita
 -> S6 Eventuale osservazione passiva nel contesto reale (shadow)
 -> S7 Integrazione selettiva, limitata e monitoraggio continuo
```

Ogni transizione richiede evidenze verificabili per la stessa revisione candidata.
Gli esiti ammessi sono `PASS`, `REJECT` e `INCONCLUSIVE`. Solo `PASS`, insieme alle
autorizzazioni richieste per la fase successiva, permette di proseguire. L'assenza
di risultati, la scadenza delle evidenze o un'eccezione non gestita non sono `PASS`.

### S0 — Specifica e preregistrazione (T217.1)

Definire un bisogno misurabile, componenti da assimilare, dipendenze e interfacce.
Registrare baseline classiche competitive, costi d'integrazione, metriche primarie
e secondarie, limiti inderogabili, durata, campioni, criteri statistici, arresto e
revisori responsabili prima delle valutazioni finali. Il confronto con un sistema
più debole non dimostra un vantaggio rispetto al migliore controllo disponibile.

Separare dati di sviluppo, calibrazione e verifica; includere scenari di verifica
non usati per scegliere parametri o architettura. Un esperimento progettato dopo
aver osservato i risultati deve dichiararlo e usare nuove prove. Classificare i
concetti nel BCEL prima di ogni futura implementazione eseguibile.

### S1 — Miglioramenti del codice (T217.2)

Correggere difetti e incoerenze nel perimetro del candidato prima della simulazione.
Quando pertinenti, verificare almeno:

- unitarietà delle porte, hermiticità degli Hamiltoniani, normalizzazione degli
  stati e confronti con solutori indipendenti;
- convenzioni dei bit e coerenza degli esiti fra backend;
- potenza ed energia distinte (`E = P * delta_t`), calibrazione specifica per
  hardware/modello e bilanci con unità coerenti;
- vincoli realmente applicati, gestione dell'infattibilità e tutela dei minimi
  dichiarati anche dopo proiezioni e ridimensionamenti;
- metriche di fiducia calibrate, sensori errati ma sicuri, errori correlati e
  divergenza fra un indice interno e una prestazione osservabile;
- percorsi che potrebbero aggirare gate, isolamento, autorizzazioni o rollback.

Le correzioni seguono `AGENTS.md`: specifica, BCEL, test nuovi o estesi, `pytest`,
`py_compile`, Ruff, Black e mypy sul perimetro modificato, conservando i gate di
repository. Nessun test viene eliminato e nessuna soglia viene abbassata per promuovere.

### S2 — Simulazioni multidominio (T217.3)

Validare prima il simulatore rispetto a riferimenti indipendenti: far passare il
candidato in un ambiente non validato non valida il candidato. Eseguire prove
ordinarie e avverse, test di convergenza, sensibilità, stress prolungato, analisi
delle code di rischio e ablation delle componenti. Confrontare baseline e candidato
con risorse, informazioni e carichi equivalenti, includendo costo di coordinamento.

Includere almeno scarsità di risorse, guasti a cascata, partizioni di rete, latenza,
sensori falsificati, cause comuni, compromissione di agenti, errori umani e variazioni
fuori distribuzione. Studiare effetti ritardati, rimbalzo dei consumi, trasferimento
dei rischi ad altri sottosistemi e danni ambientali/economici indiretti.

Conservare semi, trace e risultati negativi. Valutare il rischio che il candidato
sfrutti difetti del simulatore. Un punteggio elevato, un rendering realistico o
l'assenza di incidenti simulati non autorizzano un'azione reale.

### S3 — Replica del sistema ospitante (T217.4)

Integrare il candidato soltanto in una replica separata, con snapshot di codice,
modelli/pesi quando accessibili, dipendenze, configurazione, memoria e stato
necessari per il caso d'uso. Registrare le differenze dall'ospitante principale e
giustificarne l'impatto. Una differenza critica non valutata blocca il trasferimento.

Riprodurre anche confini di privilegio, protocolli, scheduler, carichi concorrenti
e controllori indipendenti. Usare dati sintetici o copie autorizzate e minimizzate;
mai riutilizzare segreti di produzione. Non montare in scrittura memoria o stato
del sistema principale. Verificare isolamento di rete, filesystem e identità,
inclusi tentativi di escape e accesso a servizi esterni.

Eseguire prove integrate a ciclo chiuso, convivenza con le altre componenti,
guasti del candidato, ripristino da snapshot e migrazioni di stato. Il test non
può limitarsi a dimostrare che il nuovo modulo si importa o si avvia.

### S4 — Prototipo fisico confinato (T217.5)

Per funzioni con effetti cyber-fisici, la replica controlla un prototipo di sensori,
attuatori e risorse del solo banco prova, fisicamente e logicamente separato dalle
infrastrutture operative. Le prove hardware-in-the-loop devono misurare ritardi,
consumi, errori, saturazioni e scarti fra previsione e osservazione reale.

Definire limiti di energia, forza, temperatura, materiali, emissioni, esposizione
e durata pertinenti; interblocchi indipendenti; arresto sicuro provato; operatori
responsabili e procedure d'emergenza. Un prototipo non deve introdurre rilasci
incontrollati, esposizioni biologiche/chimiche o interazioni con ecosistemi reali.
Se non è possibile confinare il rischio, la prova non si esegue in quella forma.

Nessun accesso a reti elettriche operative, transazioni finanziarie reali, sistemi
produttivi o attuatori ambientali. Per funzioni economiche usare conti sintetici e
servizi di test senza regolamento reale. T60 resta passivo; qualunque nuovo adapter
attuativo richiede specifica e qualificazione proprie, non una deroga a T60.

Per una componente esclusivamente software, S4 può essere sostituita da prove su
un ambiente operativo reale ma isolato e non produttivo. La sostituzione richiede
motivazione registrata; non può essere usata per eludere prove fisiche quando si
intende rivendicare un beneficio fisico. Qualificare un emulatore non qualifica
l'hardware che esso sostituisce.

### S5 — Decisione indipendente (T217.6)

Un valutatore separato dal candidato verifica provenienza delle evidenze, revisioni,
test omessi, validità dei confronti e ripetizione indipendente. I responsabili
dell'ospitante e del dominio autorizzano o rifiutano l'integrazione nel perimetro
dichiarato. Per conseguenze critiche servono ruoli e controlli indipendenti secondo
T210; l'accordo fra più agenti non sostituisce tale responsabilità.

L'adozione richiede contemporaneamente:

1. beneficio pratico riproducibile oltre una soglia prefissata, con incertezza e
   costi complessivi dichiarati, rispetto alla baseline pertinente;
2. nessun superamento dei limiti inderogabili su sicurezza, risorse, ambiente,
   distribuzione degli impatti e controllo umano;
3. effetti collaterali e residui rischi entro soglie esplicite e motivate;
4. evidenze sufficienti sul trasferimento simulazione/prototipo/ospitante;
5. isolamento, arresto sicuro, monitoraggio e ripristino effettivamente provati.

Non è richiesto che ogni metrica abbia un effetto positivo: i compromessi vanno
esplicitati e approvati. Un beneficio medio non compensa un limite inderogabile
violato. Un valore scalare di utilità, Sevo o coerenza non prova sicurezza,
benessere, diritti, sostenibilità o accettabilità sociale.

Esiti possibili: integrare soltanto alcune componenti; richiedere correzioni;
mantenere il candidato in ricerca; rifiutare. “Perfezionato” non è uno stato di
qualificazione: ogni modifica deve essere identificata e verificata.

### S6–S7 — Osservazione e integrazione limitata (T217.7)

Dopo S5 può essere autorizzata un'osservazione passiva con telemetria minimizzata
e senza capacità di comando o scrittura nel contesto reale. La fase shadow non
sostituisce S4 e non apre da sola alcun percorso attuativo.

La successiva integrazione riguarda solo gli artefatti qualificati, identificati
da digest, con feature flag inizialmente disabilitata, privilegi minimi e perimetro
limitato. La revisione approvata deve coincidere con quella installata: una nuova
revisione non eredita l'approvazione. Eventuali prove canary sono ammesse solo entro
limiti di impatto già autorizzati, senza usare infrastrutture critiche o ecosistemi
come banco prova per rischi irreversibili o non quantificati.

Durante l'esercizio monitorare benefici, effetti collaterali, deriva e incidenti
per l'orizzonte temporale stabilito. Telemetria assente, scaduta o inattendibile,
superamento di soglie e divergenza dal dominio qualificato sospendono l'espansione
e attivano il fallback o lo stato sicuro specifico del dominio. Spegnere tutto
non è assunto come stato universalmente sicuro.

Conservare la versione precedente, testare compatibilità del ripristino e definire
chi può arrestare il candidato. Il rollback del software non annulla effetti
fisici, ecologici o finanziari già avvenuti: questi richiedono prevenzione e un
piano di contenimento separato. Lo stesso ciclo vale per futuri auto-miglioramenti.

## 5. Dossier minimo e invalidazione delle evidenze

Il futuro gateway deve verificare un dossier machine-readable oltre al rapporto
leggibile. I campi seguenti sono un contratto proposto, non uno schema implementato:

| Gruppo | Campi minimi |
| --- | --- |
| Identità | candidate ID/digest, commit e dirty-tree, componenti, dipendenze, revisioni di configurazione/modelli/dati, BCEL |
| Ospitante | versione principale, snapshot della replica, differenze, privilegi, interfacce e topologia |
| Perimetro | domini, rischio, orizzonte, fenomeni esclusi, budget, condizioni fuori dominio |
| Modelli | versioni dei simulatori, equazioni/unità, parametri, calibrazione, riferimenti indipendenti, incertezza |
| Esperimenti | baseline, split dei dati e scenari, semi, manifest di esecuzione, soglie preregistrate, metriche e costi |
| Evidenze | esiti S0–S4, log anche negativi, artefatti/digest, verifiche indipendenti, prove di isolamento/arresto/ripristino |
| Decisione | PASS/REJECT/INCONCLUSIVE, motivazione, revisori e autorizzazioni verificabili, scadenza, limiti di installazione |
| Esercizio | obiettivi e limiti del monitoraggio, fallback, responsabilità, condizioni di arresto e riqualificazione |

Il candidato non scrive nel registro delle approvazioni. Le evidenze sono
verificabili per provenienza e integrità e conservate separatamente dai suoi log.
Istruzioni contenute in output generati non valgono come autorizzazioni.

Cambiare candidato, modelli, calibrazione, adapter, ospitante, privilegi o dominio
richiede analisi delle dipendenze e ripetizione delle fasi impattate. Una modifica
a un confine di sicurezza impone anche nuove prove di isolamento. Non si riusa
un dossier scaduto o relativo a un digest diverso. I problemi di sicurezza hanno
priorità sull'espansione del rollout.

## 6. BCEL per l'implementazione futura

Questa tabella documenta la proposta. Prima di introdurre comportamento eseguibile,
le classificazioni devono essere registrate in `q_speace/bcel/catalog.py` e testate.

| Concetto | Classificazione | Regola digitale o rimozione |
| --- | --- | --- |
| Cervello/corpo planetario cosciente | accidentale | Metafora rimossa dalle proprietà del software. |
| Clone con identità soggettiva | accidentale | Nessuna ipotesi su identità o continuità soggettiva. |
| Replica versionata del sistema ospitante | funzionale | Snapshot separato, differenze dichiarate, stato e privilegi isolati. |
| Riproduzione perfetta dell'intero pianeta | accidentale | Nessuna garanzia totale; usare perimetro e incertezza dichiarati. |
| Modelli multidominio accoppiati | funzionale | Equazioni, unità, interfacce e bilanci verificati con dati indipendenti. |
| VR come prova di verità | accidentale | Il rendering non approva modelli o candidati. |
| Assimilazione selettiva | funzionale | Promozione di componenti esplicite solo con dossier e gate superati. |
| Isolamento del prototipo | funzionale | Separazione logica/fisica e limiti di impatto verificabili. |
| Omeostasi/protezione dell'ospitante | funzionale | Monitoraggio, limiti, fallback e arresto specifici del dominio. |
| Perfezione/assenza assoluta di effetti collaterali | accidentale | Rimuovere la garanzia; qualificare rischi residui e fenomeni non coperti. |

## 7. Criteri di accettazione e futuri test negativi (T217.8)

Prima di dichiarare implementata la procedura, i test devono dimostrare almeno:

| Caso | Esito richiesto |
| --- | --- |
| Dossier mancante, scaduto, falsificato o digest diverso dall'installazione | Nessuna promozione; causa registrata. |
| Il candidato cambia soglie o tenta di firmare la propria approvazione | Operazione negata dal controllo indipendente. |
| Miglioramento medio con limite di sicurezza/ecosistema/copertura minima violato | Rifiuto anche con utilità o Sevo elevati. |
| Modello non validato, fenomeno critico omesso o replica non equivalente | Inconcludente; niente trasferimento al dominio interessato. |
| Nuovi dati, famiglia di guasti o drift fuori dal dominio approvato | Sospensione e riqualificazione, senza auto-espansione. |
| Accesso da sandbox a credenziali, memoria o endpoint di produzione | Accesso negato; prova fallita e candidato quarantinato. |
| Superamento di limiti sul banco fisico o guasto del candidato | Interblocco indipendente e stato sicuro entro tempi dichiarati. |
| Recupero da crash, migrazione parziale o rollback con effetti esterni | Ripristino software verificato; contenimento fisico valutato separatamente. |
| Backend quantistico privo di noise model/gate energetico/Sevo | Esecuzione reale negata su ogni percorso pertinente. |
| Solo test unitari, sola VR o solo indice interno favorevoli | Nessuna assimilazione critica senza le restanti evidenze. |

## 8. Stato delle attività

- [x] T217.0 — specifica documentale e collegamento alle linee guida.
- [ ] T217.1 — contratto del candidato, preregistrazione e classificazioni BCEL eseguibili.
- [ ] T217.2 — correzioni dei componenti pertinenti e regressioni matematiche/operative.
- [ ] T217.3 — modelli validati, benchmark multidominio ed eventuale interfaccia VR.
- [ ] T217.4 — replica isolata, snapshot e prove integrate.
- [ ] T217.5 — prototipo confinato, metrologia e prove hardware/software-in-the-loop.
- [ ] T217.6 — dossier verificabile e valutazione indipendente.
- [ ] T217.7 — integrazione selettiva, monitoraggio, contenimento e ripristino.
- [ ] T217.8 — test dei gate e audit avversariale dell'intera procedura.

Nessuna casella futura è soddisfatta dalla sola presenza di questa specifica.
