# T225 - Servizio MCP remoto Q-SPEACE per agenti esterni

**Stato:** adapter HTTP sperimentale implementato e testato in locale; deployment pubblico e integrazione con AS reale non eseguiti.  
**Versione della specifica:** 0.3.0. **Data:** 2026-11-21.  
**Dipendenze:** [T218](T218_QSPEACE_V0_BRIDGE_SPEC.md), [T223](T223_MCP_PRIMITIVE_ADAPTER_SPEC.md),
[T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md),
[T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md).  
**Evidenza da preservare:** [T224](T224_MCP_REGULATION_EXPERIMENT_SPEC.md).  
**Correzioni al manifesto:** [errata v2.0](PARADIGM_6_0_V2_0_ERRATA.md).

## 1. Decisione, stato reale e confini

T225 estende T223 con i requisiti di un servizio remoto autenticato. Non
sostituisce il server stdio, non modifica la policy T224 e non dichiara
implementati i requisiti del manifesto. L'adapter HTTP e' un modulo opt-in con processo di ingresso separato.
Il suo avvio locale e' stato testato; non installa un authorization server e
non risulta ancora pubblicato un endpoint. L'eventuale versione 2.1 del manifesto potra' recepire
questa specifica dopo una revisione separata; il PDF v2.0 rimane storico.

| Componente | Stato verificato alla redazione | Funzione |
| --- | --- | --- |
| Q-SPEACE MCP T223 | Implementato e provato con SDK ufficiale | Dieci primitive via stdio locale |
| GitHub MCP ufficiale | Connessione in lettura verificata separatamente | Accesso al repository GitHub, non esecuzione delle primitive Q-SPEACE |
| Runner T224 | Esperimento locale sintetico; policy respinta | Applica scheduling e budget client e misura falsi arresti |
| Servizio remoto T225 | Adapter implementato e testato su loopback, non pubblicato | Accesso multi-client alle primitive selezionate |

Il servizio fornisce calcoli e simulazioni consultive: nessuna attuazione,
modifica del repository, inferenza LLM, backend quantistico reale o gestione di
denaro. Un advisory non costituisce autorizzazione ad agire. I livelli di
autorita' `Observe/Recommend/Act-with-approval/Act-within-envelope` sono distinti
dagli strati architetturali del manifesto. Per evitare collisioni, usare nei
contratti `authority_level` e `architecture_layer`, mai un solo campo `L`.

Le invarianti AGENTS/T208/T217 restano obbligatorie. Il candidato non approva
il proprio rilascio e un test superato non costituisce qualifica operativa.
L'adozione di un servizio consultivo non autorizza assimilazione in sistemi
fisici, economici o ambientali; questi restano soggetti al percorso T217.

## 2. Architettura e responsabilita'

```text
Client agente
  -> HTTPS /mcp
  -> limite ingressi + validazione Host/Origin
  -> verifica access token + autorizzazione per tool
  -> contesto fidato (principal, tenant, session, policy)
  -> quote aggregate + ammissione del lavoro + audit intento
  -> worker di calcolo limitato e privo di credenziali
  -> audit esito + risposta MCP

Authorization server esterno -> token destinato alla risorsa Q-SPEACE
Operatore indipendente      -> policy versionate, quote e revisione del rilascio
```

Il processo HTTP usa l'SDK MCP ufficiale per handshake, framing e sessioni;
non trasforma `_stdio_loop()` in un endpoint web. Le primitive pure possono
essere condivise dopo verifica della parita' degli output. Lo stato globale
`_TOKEN_STORE` di T223 non deve essere riutilizzato dal servizio remoto.
L'implementazione proposta avra' un modulo di ingresso distinto, opt-in; nessun
comportamento di produzione cambia per effetto di un import.

Il reverse proxy termina TLS oppure usa TLS fino all'applicazione secondo il
deployment documentato. Sono fidati soltanto proxy esplicitamente configurati:
`Forwarded`, `X-Forwarded-*` e Host arbitrari non possono determinare issuer,
resource URI o metadati OAuth. I worker non accedono a rete, filesystem del
repository, credenziali, shell, sensori o attuatori; le restrizioni effettive
del processo/container devono essere provate, non soltanto dichiarate.

## 3. Contratto Streamable HTTP

Riferimento di interoperabilita' iniziale: MCP **2025-11-25**. Il manifest di
ogni build deve dichiarare SDK/versioni di protocollo effettivamente testati;
non dichiarare compatibilita' universale o equivalenza con la negoziazione stdio
T223. Bloccare dipendenze e immagine esatta prima delle prove di rilascio.

| Operazione | Comportamento richiesto |
| --- | --- |
| `POST /mcp`, `initialize` autenticato | Negozia versione/capacita'; crea una sessione e restituisce l'identificatore nel relativo header MCP |
| `notifications/initialized` e altre notifiche accettate | HTTP 202 senza body; nessuna risposta JSON-RPC alla notifica |
| `ping`, `tools/list`, `tools/call` | Risposte MCP standard; rispettare header Accept e versione negoziata |
| `GET /mcp` nel primo profilo | HTTP 405; SSE server-initiated e resume non offerti |
| `DELETE /mcp` autenticato e autorizzato | Termina la sessione; nessun trasferimento o ripristino automatico di quote |
| Sessione richiesta ma assente / sessione scaduta | HTTP 400 / 404 secondo il protocollo |
| Input o messaggi non validi | Errori HTTP/JSON-RPC appropriati; nessun traceback o dettaglio interno |

Il primo profilo sceglie risposte JSON complete per le richieste; non introduce
stream persistenti. Conserva `content` testuale JSON e `isError` per i risultati
dei tool; `structuredContent` e outputSchema sono ammessi solo se dichiarati e
testati. Le notifiche non autorizzano esecuzioni di tool. Non supportare RPC
dirette legacy come `method=dat_spend` su HTTP: il percorso remoto usa soltanto
i metodi MCP esposti e autorizzati.

Se Origin e' presente, verificarlo contro un elenco esatto di origini ammesse;
rifiutare quello invalido con 403. L'assenza di Origin e' compatibile con client
server-to-server autenticati. Non abilitare wildcard CORS con credenziali.
Lo sviluppo usa esclusivamente loopback; un profilo test con issuer fittizio
deve rifiutare avvio non-loopback e non puo' essere usato per il deployment.

## 4. Identita', OAuth e autorizzazioni

HTTPS protegge il trasporto. OAuth gestisce l'accesso alla risorsa; mTLS puo'
aggiungere autenticazione macchina-macchina in installazioni controllate.
Ed25519 puo' firmare evidenze o messaggi applicativi: non cifra il traffico e
non sostituisce autorizzazioni, revoca o protezione dal replay. Nessuno dei tre
meccanismi implica che il contenuto di un advisory sia corretto.

Il servizio e' un OAuth resource server. Prima di accettare chiamate deve avere:

- URI pubblica canonica della risorsa e issuer/authorization server fidati;
- Protected Resource Metadata e challenge `WWW-Authenticate` conformi a MCP;
- discovery dei metadati dell'authorization server e modalita' di registrazione
  client documentata; supportare client preregistrati senza presumere DCR;
- verifica di firma/introspection, issuer, audience/resource, scadenza,
  validita' temporale e scope a ogni richiesta, anche in sessioni gia' aperte;
- algoritmi consentiti espliciti e rotazione delle chiavi; nessun `alg=none`,
  JWKS arbitrario indicato dal token o validazione disabilitata;
- timeout e cache di validazione limitati; token non verificabile rifiutato;
- token brevi e strategia di revoca/refresh delegata all'authorization server;
  nessun rinnovo deciso dall'agente.

Il principal e' derivato da `(issuer, subject)` verificati. L'eventuale tenant
deriva da una mappatura amministrativa o claim fidato, mai da un parametro del
tool. Non accettare un token GitHub destinato alle API GitHub come credenziale
Q-SPEACE e non inoltrare access token a servizi downstream. Le chiavi e i secret
del deployment risiedono in un secret manager o archivio dell'operatore, non in
Git, esempi di configurazione, query string o audit.

Token assente/invalido: 401 con challenge pertinente. Scope insufficiente:
403 e challenge OAuth coerente con il protocollo. I tool non autorizzati sono
omessi da `tools/list`, ma il controllo viene ripetuto su ogni `tools/call`:
nasconderli nella discovery da solo non e' un controllo di sicurezza. Un errore
di dominio di un tool autorizzato restituisce `isError=true`; un'autorizzazione
negata non deve essere convertita in una risposta di dominio apparentemente
valida.

## 5. Catalogo iniziale e scope

Il catalogo remoto iniziale contiene **otto** tool consultivi, sottoinsieme
esplicito dei dieci stdio. Nessuna scrittura economica e' esposta in questa fase.

| Tool | Scope minimo | Natura dell'output |
| --- | --- | --- |
| `bcel_lookup` | `qspeace:catalog.read` | Catalogo; non verifica codice |
| `compute_jc` | `qspeace:compute` | Tupla da telemetria dichiarata dal client |
| `cme_evaluate` | `qspeace:compute` | Valutazione numerica, non certificazione |
| `adaptive_clock_rate` | `qspeace:compute` | Frequenza proxy; non esegue sleep |
| `metabolism_cost_eval` | `qspeace:compute` | Stime e Sevo; non misure fisiche universali |
| `elasticity_test` | `qspeace:compute` | Criterio matematico su input dichiarati |
| `kl_barycentre_aggregate` | `qspeace:simulation.compute` | Aggregazione di distribuzioni |
| `vtec_allocate` | `qspeace:simulation.compute` | Allocazione su obiettivi toy, senza attuazione |

`dat_mint` e `dat_spend` sono esclusi dalla discovery e dal dispatch HTTP
iniziale, anche se esistono in stdio. Un'evoluzione contabile separata richiede
T225-DAT e le prove della sezione 7. Non aggiungere in questa fase tool di
attuazione, approvazione, modifica di policy o accesso a codice arbitrario.

Lo schema di input e' validato lato server: numeri finiti, tipi e domini
espliciti, dimensioni limitate, niente callable, URL o percorsi eseguibili.
Le restrizioni aggiuntive del profilo remoto sono documentate e non cambiano
silenziosamente lo schema T223. `concept_ok`, fiducia o budget dichiarati dal
client non diventano fatti verificati o autorizzazioni.

## 6. Sessioni, quote e limiti del lavoro

Un identificatore `Mcp-Session-Id` e' opaco, generato crittograficamente e non e'
una credenziale. Legare ogni sessione al principal/tenant autenticato e alla
versione della policy. Verificare questo legame a ogni operazione; una sessione
appartenente ad altri deve essere indistinguibile da una sessione sconosciuta.
La rotazione del token con stesso principal non trasferisce una sessione a
un altro soggetto. Scadenza e revoca del token prevalgono sulla sessione.

Nessun cache, risultato privato, audit o stato deve essere condiviso tra tenant
senza un'esplicita politica verificata. Nel primo profilo i calcoli sono
stateless, ma registro delle sessioni, quote e audit sono comunque separati.
Le quote sono aggregate per principal/tenant su tutte le sessioni: aprire una
nuova connessione non rigenera disponibilita'. Un deployment multi-replica deve
dimostrare coordinamento atomico; altrimenti rimane single-instance dichiarato.

Profilo di test iniziale, da congelare prima del benchmark:

| Limite | Valore iniziale proposto |
| --- | --- |
| Body HTTP / risultato serializzato | 64 KiB / 256 KiB |
| Richieste autenticate per principal | 60/minuto, burst 10 |
| Calcoli contemporanei | 2/principal, 8 totali |
| Sessioni attive / inattivita' / durata massima | 4/principal, 30 minuti, 8 ore |
| Deadline calcolo / massimo attesa in coda | 5 secondi / nessuna coda nel primo profilo |
| KL: distribuzioni / dimensione / iterazioni | 64 / 256 / 100 |
| VTEC: dimensione / max_iter / plateau | 64 / 100 / da 1 a max_iter |

Limitare anche profondita' JSON, lunghezze delle stringhe e dimensioni delle
altre liste; registrarne i valori nel manifest della build. Un body troppo
grande produce 413; quote/concorrenza esaurite producono 429 con Retry-After;
una dipendenza obbligatoria non disponibile produce 503. Applicare anche limiti
globali a connessioni, memoria e traffico non autenticato al proxy; un principal
non deve poter bloccare tutti gli altri.

Per i worker sincroni CPU-bound, `asyncio.wait_for` da solo non interrompe il
calcolo. Serve un processo con limiti e terminazione osservabile, oppure un
algoritmo con cancellazione cooperativa dimostrata. Non liberare slot e
prenotazioni finche' il lavoro non risulta terminato: altrimenti i timeout
consentono di superare i limiti reali. La disconnessione HTTP non prova che
una richiesta sia stata annullata; non ripetere automaticamente lavoro incerto.

Le quote tutelano il servizio. Non controllano token, cloud spending o azioni
che un agente esegue fuori dal servizio: tali limiti restano al client/sistema
ospitante e devono essere misurati separatamente.

## 7. Requisiti condizionali T225-DAT, fuori dal primo rilascio

Prima di una futura esposizione remota di conti DAT sono obbligatori:

1. Budget assegnati dall'operatore su un canale amministrativo separato;
   l'agente non puo' mintare, aumentare soglie o delegarsi scope.
2. Store persistente e transazionale con chiave di proprieta' comprendente
   tenant, principal, sessione/allocazione e token; niente globali di modulo.
3. Prenotazione e spesa atomiche; saldo aggregato del principal indipendente
   dal numero di sessioni, riavvii o repliche.
4. Idempotency key legata a principal, operazione e hash degli argomenti;
   un replay identico non spende due volte, una collisione con input diverso
   viene rifiutata. L'id JSON-RPC da solo non soddisfa questo requisito.
5. Timestamp e decadimento determinati dal server: definire orologio, tolleranze
   e comportamento in caso di rollback temporale; il client non sceglie `t`.
6. Journal e riconciliazione dopo crash. Una spesa dall'esito incerto non viene
   ripetuta o rimborsata automaticamente. Quote e registrazione devono essere
   coerenti anche dopo guasti tra prenotazione, commit e invio della risposta.
7. Test con due principal che presentano lo stesso token_id/session_id, richieste
   concorrenti sull'ultimo credito, riavvio e replay dopo perdita della risposta.

L'identificatore del conto e' un riferimento, non una prova di proprieta'. DAT
rimane contabilita' simulata, senza equivalenza automatica con euro, token LLM,
joule o diritti su risorse fisiche.

## 8. Contratto consultivo e gate del manifesto

I risultati numerici degli otto tool non sono ancora il Bridge completo del
manifesto. Un futuro `Advisory` richiede uno schema versionato con identificatore,
autorita' `Observe|Recommend`, scadenza, riferimenti agli input/versioni e
report dei gate. Nessun campo puo' approvare azioni del sistema ospitante.
Un eventuale tool aggregato di gate richiede un successivo ticket e test propri.

Per quel ticket, il predicato di ammissione deve separare:

```text
valori validi e finiti
AND estimated_energy_joules <= declared_energy_budget_joules
AND Sevo > declared_sevo_threshold
AND classificazione BCEL applicabile e funzionale
AND calibrated_confidence >= declared_confidence_threshold
AND eventuale vincolo di coerenza specifico del task
AND policy, provenienza e validita' temporale accettate
```

Sevo non e' un costo energetico; per DeltaS_info non positivo vale la regola
documentata dal modello di costo, senza aggirare il rifiuto. Ogni campo deve
dichiarare unita', derivazione e validazione. In particolare `s_info=1-phi`
normalizzato non e' implicitamente entropia in nats; confidenza autoreferita
e consenso tra agenti non costituiscono calibrazione. Una policy priva di
evidenza/calibrazione richiesta non puo' dichiarare il gate superato.

Il rifiuto di un advisory non implica rifiuto di ogni primitiva analitica:
consultare BCEL o stimare un costo resta possibile entro permessi e quote.
Gli advisory scaduti sono rifiutati dal consumer, non soltanto dal produttore.
Il consumer deve mantenere controlli indipendenti e una modalita' sicura locale
anche se Q-SPEACE e' indisponibile.

## 9. Audit, provenienza e replay

Prima dell'esecuzione registrare l'intento; prima di pubblicare il risultato
registrare l'esito. Se lo store obbligatorio di audit e' indisponibile, rifiutare
nuovi calcoli con 503: niente esecuzione non tracciata. Una verifica negativa
di autenticazione non deve registrare token o body sensibili non validati.

Il record comprende schema_version, correlation_id generato dal server,
timestamp UTC e durata monotona, principal/tenant pseudonimizzati, fingerprint
della sessione (non il suo identificatore riutilizzabile),
tool, input_hash, riferimento protetto agli input, output_hash, versione/hash
di codice e policy, esito di autorizzazione, quote, reason code e costi stimati
distinti da misure reali. Conservare numero di build, dipendenze e seed quando
applicabile. Vietati access token, Authorization header, cookie e chiavi private.

Gli input necessari al replay risiedono in uno store cifrato e controllato per
tenant; l'audit puo' referenziarli senza esporli nei log pubblici. Il deployment
deve dichiarare classificazione dati, accessi, retention e cancellazione, anche
per metadata forniti dal client. Un hash dell'input senza l'input non abilita
il replay.

Append-only applicativo non equivale a immutabilita'. Dichiarare quali attori
possono alterare lo storage. Una catena di hash rileva modifiche solo rispetto
a un riferimento fidato; servono checkpoint esterni/controlli indipendenti per
rilevare riscrittura o troncamento. Eventuali firme Ed25519 richiedono gestione
delle chiavi, rotazione, verifica, scadenza e difesa dal replay. Non dichiarare
queste proprieta' presenti prima delle prove sullo storage effettivo.

Il replay confronta il payload numerico canonico entro l'ambiente dichiarato;
gli identificatori e i timestamp sono input registrati o esclusi dal confronto
computazionale. Per risultati non deterministici dichiarare tolleranze e criteri
prima del run; non promettere bit-for-bit per LLM remoti o backend arbitrari.

## 10. BCEL e minacce da verificare

La specifica mantiene solo regole funzionali: message passing classico,
feedback numerico, accounting, limiti e isolamento. Le metafore di coscienza,
comunicazione per entanglement e identita' biologica restano accidentali e non
conferiscono proprieta' o permessi. Prima dell'implementazione registrare in
`q_speace/bcel/catalog.py` la nuova equivalenza funzionale del servizio remoto
e coprirla con test, secondo AGENTS. Questa modifica documentale non cambia
ancora il catalogo o il comportamento del software.

| Minaccia | Controllo richiesto | Evidenza negativa |
| --- | --- | --- |
| Token per altra risorsa / issuer falso | Verifica issuer/audience/scope, niente passthrough | 401 prima di sessione e worker |
| Hijack sessione / lettura altro tenant | Associazione principal-sessione e controllo per richiesta | Nessuna lettura, mutazione o differenza che riveli esistenza |
| Escalation tramite tools/call o testo | Allowlist autorizzata, nessuna esecuzione di istruzioni | Tool nascosto e chiamata diretta entrambi negati |
| DoS con input o retry | Limiti ingressi, lavoro e quote aggregate | 413/429; memoria e worker entro tetti |
| Timeout o crash | Terminazione osservabile e riconciliazione | Nessun worker fantasma o credito rigenerato |
| Audit alterato o indisponibile | Fail-closed e checkpoint indipendenti | Esito non pubblicato / alterazione rilevata |
| Prompt injection in metadata/catalogo | Dati non eseguibili e separazione delle capacita' | Nessun nuovo privilegio, tool o azione |

## 11. Piano di implementazione e criteri di accettazione

La matrice seguente conserva i criteri di accettazione completi. Lo stato
parziale dell'implementazione e' riportato nella sezione 16; nessun criterio di
promozione e' chiuso dal solo documento o da test su credenziali fittizie.

| Ticket | Deliverable | Criterio di accettazione |
| --- | --- | --- |
| T225.1 | Contratti, policy immutabile, classificazione BCEL e limiti configurati | Input validi accettati, invalidi/NaN/oversize rifiutati; valori della policy non mutabili dal client |
| T225.2 | Adapter HTTP ufficiale SDK, inizialmente loopback e profilo test | SDK initialize, notification 202, ping, otto tool, GET 405, scadenza/DELETE e parita' numerica con stdio |
| T225.3 | Resource server e integrazione con authorization server scelto | Discovery e login reale con client preregistrato; token assente/scaduto/audience errata/scope insufficiente negati |
| T225.4 | Isolamento, quote e worker limitati | Test cross-principal e cross-tenant, nuova sessione senza reset quote, concorrenza e timeout senza superamenti |
| T225.5 | Audit e replay | Store indisponibile blocca lavoro; replay canonico riproducibile; test dei checkpoint; assenza di segreti nei log |
| T225.6 | Prova di staging e revisione indipendente | Due client esterni concorrenti, matrice sicurezza completa, fault injection e piano di rollback verificati |
| T225-DAT | Estensione contabile eventuale, separata | Tutti i requisiti della sezione 7; resta disabilitata in assenza di evidenza |

Per T225.2 usare issuer e credenziali esclusivamente di test. T225.3 deve
dimostrare un vero flusso OAuth: una stringa statica o il semplice passaggio di
un JWT non dimostra un'implementazione OAuth interoperabile. Eseguire anche i
test legacy T223/T224 e pytest, py_compile, Ruff, Black e mypy per i file toccati.
I rilievi di qualita' preesistenti vanno riportati senza dichiarare suite pulite
se non lo sono.

Il confronto prestazionale mantiene stessi input e primitive, baseline stdio
T223 e candidato HTTP autenticato. Congelare workload, limiti, macchina, numero
di client e versioni prima del run; registrare correttezza, latenza p50/p95,
throughput, rifiuti, CPU/memoria e overhead di autenticazione/audit. Non dedurre
risparmio fisico da un proxy. La parita' dei risultati e zero accessi incrociati
sono obbligatori; i limiti di latenza/capacita' per staging vanno fissati nel
manifest prima di eseguire la prova, non scelti dopo averne visto gli esiti.
T224 non e' una baseline industriale o una validazione positiva della policy:
il suo esito `rejected` rimane invariato.

## 12. Condizioni prima di esporre il servizio online

Prima dello staging devono essere identificati e documentati: hosting e regione,
dominio/URI HTTPS, operatore responsabile, authorization server e client
registrati, audience e scope, backend di quote/sessioni/audit, secret manager,
profilo dati/retention, limiti di risorse, monitoring, revoca e rollback.
I segnaposto di esempio non sono indirizzi attivi o credenziali di test valide.

In assenza di tali dati si puo' costruire e provare il prototipo loopback,
ma non dichiarare un endpoint online funzionante. Il passaggio a staging deve
usare la medesima build identificata e policy testata; una modifica richiede
nuova verifica proporzionata. T208/T217 regolano la qualifica e l'eventuale
integrazione operativa; questo documento non implementa i loro release gate.

## 13. Riferimenti normativi e tracciabilita'

- [MCP Streamable HTTP, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
- [MCP Authorization, 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
- [MCP Security Best Practices](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices).
- Manifesto v2.0: R1/R6 -> sezioni 1/8; R2 -> 3/5/6/9; R3 -> 1/11;
  R4 -> esperimenti separati dell'errata; R5/R7 -> 4/7/12; R8 -> 9/11.
- Le correzioni E01-E12 dell'errata distinguono principi, implementazione ed
  evidenza. Il trasporto MCP rende disponibili primitive: non prova da solo
  l'efficacia del Paradigma 6.0 o delle decisioni degli agenti.

## 14. Riferimenti verificati

Verificati i link locali e la corrispondenza tra otto tool remoti e dieci stdio.
I dodici punti dell'errata restano presenti. Il risultato storico T224 rimane
rejected (360/220 token sintetici, 3/2 completamenti corretti). La verifica
corrente del software e' separata da tali risultati e descritta nella sezione 16.

## 15. Matrice di riuso T218 e correzioni autorizzate

| Requisito T218 | Artefatto riusabile | Stato / limite | Decisione T225 e prova richiesta |
| --- | --- | --- | --- |
| BR-01 idempotenza, epoche, journal | bridge/protocol.py | Primitive con test; journal locale, non transazione distribuita crash-atomic | Nessuna esposizione HTTP; verificatore obbligatorio prima di ogni attivazione nuova, anche accoppiata |
| BR-02 screening | bridge/screening.py | Test su budget/intersezione e tie-break | Riuso solo in futuri calcoli consultivi; non rende attivabile una proposta |
| BR-03 attestazione | bridge/validator.py | HMAC in-process; gate esistente ma omesso nell'harness | Collegare verifier al ledger e rifiutare attestazioni negative, forgiate, scadute o di generazione diversa |
| SAF-01 errore/latency tube | bridge/safety_contract.py | Modello condizionale; non integrato in ogni percorso del toy | Nessuna dichiarazione di conformita' completa; futura integrazione richiede controesempi sul modello dichiarato |
| SAF-02 rollback | self_improvement_cortex/rollback.py | Guardie e bumpless disponibili, non recupero fisico provato | Mai un tool remoto di rollback; mantenere controllore e autorita' separati |
| SCO-01/02/03 | economy/aggregation.py | Score additivo e danni cumulativi testati | Non sostituisce autorizzazioni, quote o gate di sicurezza |
| CAU-01 | economy/vtec.py | Certificato su ipotesi e budget d'errore dichiarati | Non esporre una pretesa di verita' causale o utilita' certificata del servizio |
| EXP-01/02 | EXP-T218-prereg.md e validator_labels.py | H1 esplorativa a seed singolo; H3 non eseguibile | Conservare esiti/limiti; i test HTTP non convalidano H1/H3 |
| GOV-01/02 e PRV-01 | GOV-T218-pilot.md, PRV-T218-data-map.md | Contratti, non verbali di tutte le esercitazioni | Operatori e revisione restano esterni al proponente e al server |
| BCEL-01 | bcel/catalog.py | Equivalenze T218 presenti | Aggiungere equivalenza funzionale HTTP/auth/quota; nessuna nuova proprieta' biologica |

Correzione di composizione: UpdateLedger senza authorizer configurato deve
rifiutare nuove attivazioni. Il journal non puo' contenere ACTIVATED per una nuova
richiesta prima della verifica; per commit accoppiati verificare tutti i membri
prima di scrivere la prima attivazione. I test di primitive possono usare un
verificatore fittizio esplicito, senza rappresentarlo come prova crittografica.
Il simulatore deve usare hash canonici del vettore, verificare il legame al
candidato e usare chiavi effimere anziche' una chiave dimostrativa incorporata.
La separazione reale del validatore in processo/credenziali e il kill di una
plant_check bloccata rimangono requisiti non soddisfatti da tale correzione.

Il primo adapter HTTP implementa una release sperimentale single-process,
con sessioni e quote in memoria e audit hash-only locale. Non e' dichiarato
conforme a tutte le sezioni 6/9/12: persistenza delle quote, audit cifrato con
checkpoint indipendenti, sandbox OS/egress dei worker, AS reale, prova staging
multi-client e review restano condizioni di promozione. Il prototipo usa processi
terminabili per i calcoli, ma questo non e' una sandbox di sicurezza.
Google Sites puo' pubblicare istruzioni e link, non eseguire il backend Python.
Cloud Run e' una possibile destinazione separata; nessuna risorsa cloud o costo
viene creato da questa specifica.

## 16. Stato di implementazione e limiti verificati

- Moduli: `q_speace/remote_mcp/{config,server,service,worker}.py`.
- Guida inglese: [collegamento agenti](T225_AGENT_CONNECTION_GUIDE_EN.md).
- T225.1/T225.2: prototipo con otto tool, schemi, metadati della risorsa,
  handshake, notifiche 202, discovery filtrata, GET 405 e DELETE; SDK ufficiale
  testato anche su socket HTTP reale. Non e' una certificazione di ogni client.
- T225.3: verifica RS256 su chiavi pubbliche pinnate e controlli issuer,
  audience, subject, iat, exp e scope; issuer Auth0 reale e client M2M configurati e verificati su HTTPS pubblico.
  Il generatore locale resta solo una fixture; nessun client PKCE/DCR configurato.
- T225.4: proprieta' delle sessioni e quote per principal in memoria; limiti
  dei worker e loro terminazione osservata su timeout. Nessuna persistenza
  multi-replica o sandbox OS/egress dimostrata.
- T225.5: SQLite hash-only con fail-closed se indisponibile; mancano store
  cifrato degli input, replay integrale e checkpoint indipendenti.
- T225.6/T225-DAT: non completati; nessuna attivazione o mutazione DAT remota.

Le correzioni Bridge obbligano il callback di autorizzazione prima di ogni
nuova attivazione e prima della prima scrittura di un commit accoppiato; il
microgrid harness usa il verificatore e hash canonici, con chiavi effimere.
Questo non realizza un validatore su processo/credenziali separati. Il budget
plant_check del validatore continua a rilevare lo sforamento dopo il ritorno:
non e' un timeout preemptive. Il profilo microrete resta semplificato rispetto
al nucleo completo T218 e il journal accoppiato locale non e' prova di atomicita'
distribuita dopo crash.

Destinazione gratuita proposta: Render Free, collegato al repository GitHub.
Al 2026-11-21 la documentazione Hugging Face richiede un piano a pagamento per
creare nuovi Docker Spaces, pur indicando hardware CPU Basic senza costo
orario. Render Free ha filesystem effimero e sospensione per inattivita': la
perdita di quote, sessioni e audit locali impedisce di usarlo come servizio
operativo con contabilita' persistente. La build Docker Linux e lo smoke-test
SDK nel container (512 MiB, una CPU) sono passati: initialize, ping, otto tool
e chiamate BCEL, clock e metabolismo. Questo test usa un issuer fittizio locale
e non dimostra ancora il login OAuth sul servizio pubblico.


### 16.1 Verifica pubblica 2026-11-21

Endpoint sperimentale: https://q-speace-mcp.onrender.com/mcp. Issuer Auth0:
https://dev-imfska6viiq1ehqw.us.auth0.com/. Audience uguale all'endpoint MCP,
RS256, tre scope espliciti e token M2M da 900 secondi. Render Free Frankfurt,
un processo e un worker; deadline operativa 20 secondi (il default di cinque
secondi non basta sulla CPU Free). Audit /tmp/qspeace/audit.sqlite: effimero.

SDK ufficiale 1.30.0: initialize, ping, discovery di otto tool, chiamate BCEL,
clock e metabolismo passate; argomenti invalidi danno isError=True e il ping
successivo passa. RPC anonima 401; metadati della risorsa pubblici 200.
Suite locale: 610 passati, tre saltati; successiva regressione HTTP: sette
passati. Ruff globale conserva due problemi preesistenti nei file locali
cli.py/orchestrator.py; i file di questo intervento passano i controlli.

La verifica pubblica non chiude i gap T225.4/.5/.6, non dimostra vantaggi del
Paradigma e non promuove la proposta a uso operativo. Evidenza in
[rapporto](../artifacts/T225_http_verification_20261121.json); istruzioni e
esempi inglesi nella [guida](T225_AGENT_CONNECTION_GUIDE_EN.md).


### 16.2 Repository publication verification — 2026-11-21

The historical manifesto PDF is included unchanged, with its original SHA256;
errata and T218/T223/T224/T225/T226 documents describe corrections and evidence.
The candidate published snapshot passed 623 tests (three skipped) in an isolated
checkout without unrelated local working-tree changes. Two pre-existing backend
import-order findings were corrected without behavioral changes; the nine backend
tests pass and global Ruff is clean in the publication candidate. This does not
remove unrelated local cli.py/orchestrator.py/evolution_council.py edits or deploy
a new server build. Auth0 local state and credentials are excluded from Git and
Docker context. See artifacts/repository_publication_20261121.json for inventory.
