# Paradigma 6.0 v2.0 - Errata tecnica e allineamento al repository

**Stato:** revisione tecnica documentale; correzioni proposte per la successiva
edizione del manifesto. Nessuna implementazione o qualifica operativa implicita.  
**Data:** 2026-11-21. **Versione errata:** 0.1.0.  
**Documento esaminato:** [Manifesto v2.0 Technical Edition](Paradigm_6.0_Manifesto_v2.0_Technical_Edition.pdf), 16 pagine.  
**Commit di riferimento:** `ecd81531d7c31fc9fdaa85fa2d00e8cc381e2552`;
checkout locale con modifiche e materiali T224 non ancora tutti pubblicati.
SHA256 del PDF esaminato: `f585253fe4e81e01a383d3ed0b57a3595708b5ad69dc2fff497aad8254a31149`.
La presenza sul filesystem non dimostra disponibilita' sul medesimo commit online.

Questo documento accompagna il PDF storico e non lo sovrascrive. La
[specifica T225](T225_REMOTE_MCP_SERVICE_SPEC.md) rende operativi i requisiti
del futuro servizio MCP remoto; [T223](T223_MCP_PRIMITIVE_ADAPTER_SPEC.md)
rimane il contratto dell'adapter locale. Le correzioni sotto sono puntuali e
non autorizzano la sostituzione di componenti o l'attuazione.

## E01 - Titolo, non-claim e natura della revisione

**Riferimenti:** copertina, Parte I, Art. I e sezione J.

Il titolo "Sentient Technium" suggerisce una proprieta' che il corpo del testo
esclude. Per l'edizione tecnica adottare un titolo coerente, per esempio
"Reference Architecture for Auditable Agent Coordination". Organismo,
risonanza e metabolismo restano metafore soggette al filtro BCEL.

La Parte I documenta una revisione critica strutturata degli autori, non una
validazione indipendente provata dal documento. Per usare la qualifica di
peer review indipendente servono revisori, procedura ed evidenze identificabili.

## E02 - Sevo, energia e verso del gate

**Riferimento:** E.5, pagina 13; Art. VI. **Priorita': alta.**

Sostituire l'equivalenza "sevo_max = energy budget". Nel
[modello attuale](../q_speace/metabolism/cognitive_cost_model.py), Sevo e'
`DeltaU / DeltaS_info` e `passes_sevo` usa una soglia minima stretta `>`.
I limiti energetici riguardano separatamente watt o joule:

```text
energy_ok = estimated_energy_joules <= energy_budget_joules
sevo_ok   = Sevo > sevo_threshold
```

Specificare unita' dell'utilita', segno/significato di DeltaS_info, trattamento
di zero/valori negativi e dominio della calibrazione del costo. Una stima in
joule non e' una misura fisica verificata per ogni modello/hardware.
Non convertire DAT o token LLM in joule senza un modello indipendentemente
validato. Il valore 1.5 del codice non e' una costante fisica universale.

## E03 - Validazione fail-closed negli sketch

**Riferimenti:** E.1-E.5 e R2. **Priorita': alta.**

Il gate E.5 non controlla valori finiti: ad esempio `confidence=NaN` puo'
superarlo con gli altri parametri validi. Prima dei confronti validare tipi,
finitudine, domini, soglie ordinate e provenienza richiesta; input non valido
significa rifiuto, non un default favorevole. Validare anche array vuoti,
dimensioni, corrispondenza pesi/distribuzioni e somme normalizzabili.

Questo rilievo riguarda lo sketch del PDF; non dimostra un'identica vulnerabilita'
del server T223, che usa anche modelli di validazione degli input. Gli sketch
non vanno copiati in produzione senza test di controesempio e fuzzing.

## E04 - Unita', consenso, coerenza e confidenza

**Riferimenti:** Art. II, B, E.3 e glossario.

Distinguere `entropy_nats` da `normalized_s_info`: il campo `s_info` in
[ILF](../q_speace/edd_cvt/ilf.py) e' `1-coherence_phi`, una quantita' normalizzata.
Documentare distribuzione di riferimento, numero di stati, base del logaritmo,
finestra temporale e trasformazioni. La variabilita' deve indicare di quale
segnale e con quali unita' viene calcolata.

Consenso tra agenti e bassa entropia non provano correttezza. Il pooling deve
considerare fonti/modelli correlati: copie della stessa evidenza non diventano
conferme indipendenti. Una confidenza calibrata richiede outcome etichettati,
valutazione fuori campione e identificatore del protocollo di calibrazione;
un numero dichiarato dal modello o dal client non e' sufficiente.

## E05 - Metastabilita' e obiettivo del controllo

**Riferimenti:** Art. III, E.2, G.4.

La deviazione standard di R puo' essere un descrittore, ma massimizzarla da sola
premia anche oscillazioni inutili o rumore. Una sequenza costante R=0.5 ha
std=0; alternare 0.3 e 0.7 produce std=0.2 pur restando nella banda proposta.
Questo non prova un miglioramento del task o della resilienza.

Sostituire l'obiettivo incondizionato di massimizzazione con ipotesi di dominio,
bande e tempi caratteristici preregistrati, vincoli sulle oscillazioni e metriche
di prestazione/recupero. La fase di un segnale deve essere stimabile e definita:
non ogni log di agente possiede una fase periodica significativa. Il modulo
[systemic_resonance](../q_speace/systemic_resonance.py) gia' presente usa
affinita' pairwise penalizzata dall'entropia e non e' l'implementazione Kuramoto
proposta nel PDF.

## E06 - Topologie, H3 e comparatori

**Riferimenti:** M3, Art. III, R4, E.4, G.3.

Conservare la distinzione tra honeycomb di grado 3 e adiacenza di celle
esagonali. Correggere l'asserzione universale di grado 6 per H3: la griglia
sferica contiene dodici pentagoni a ogni risoluzione, come documentato da
[H3](https://h3geo.org/docs/core-library/overview/).

Uguale numero di nodi/capacita' non garantisce uguale costo di collegamento o
ridondanza. Dichiarare budget di archi, pesi, vincoli geografici, capacita' e
modello di guasto. La superiorita' simultanea su giant component, TTR e lambda2
e' un'ipotesi da testare, non una conseguenza della forma esagonale. Pubblicare
trade-off, risultati nulli e condizioni in cui altri grafi risultano migliori.

## E07 - Mappa del repository e collisione del nome Bridge

**Riferimenti:** C, D, E e WP1/WP2/WP6.

| Voce | Correzione verificabile |
| --- | --- |
| `q_speace/bridge/` | Esiste il Bridge transazionale T218; non e' il Bridge telemetria/advisory proposto. Evitare due implementazioni omonime senza mapping esplicito. |
| `systemic_resonance.py` | Il modulo esiste gia' nel pacchetto; non descriverlo soltanto come file root da spostare. Il modello numerico e' distinto da Kuramoto. |
| Qiskit | Esiste un [adapter Qiskit/Aer](../q_speace/quantum/backends/qiskit_backend.py); la sua presenza non dimostra esecuzione hardware qualificata o vantaggio quantistico. |
| Python | Il [pyproject](../pyproject.toml) richiede Python >=3.12, non >=3.10. |
| MCP | [T223](T223_MCP_PRIMITIVE_ADAPTER_SPEC.md) espone dieci primitive stdio; [T225](T225_REMOTE_MCP_SERVICE_SPEC.md) propone l'estensione remota. |
| Economia e altri moduli | `economy/`, `aacm/`, `radio/`, `spiking/` e `self_improvement_cortex/` esistono; descrivere stato e prove per componente, senza dedurne maturita' operativa comune. |

Ogni nuova tabella di stato deve indicare commit, dirty status, file, test ed
eventuale manifest sperimentale. Per una release usare un commit/build pulito
e identificabile. Non pianificare come nuovo cio' che e' gia' implementato e non
equiparare "implementato", "misurato", "validato" e "proposto".

## E08 - Due assi distinti: autorita' e strato architetturale

**Riferimenti:** Art. V e figura 1, pagina 10.

L0-L3 dell'Art. V indica autorita'; L0-L4 della figura indica strati. Rinominare
gli enum di autorita' con parole e mantenere un campo separato per lo strato.
Essere nello strato L2 non concede autorita' di azione con approvazione.

Un flag read-only o un nome di tool non implementa da solo R1. Servono controlli
di capacita' del consumer e restrizioni sul percorso effettivo di esecuzione.
L'analisi statica del call graph e' utile ma non copre da sola plugin, callback,
integrazioni dinamiche o consumatori che eseguono ciecamente un payload testuale.

## E09 - MCP come binding, autenticazione e stato

**Riferimenti:** Art. II, B e H.

Aggiungere MCP come binding per chiamate agentiche alle primitive. Non
sostituire automaticamente con MCP il trasporto di telemetria industriale o i
loop di controllo real-time. GitHub MCP legge il repository; Q-SPEACE MCP
esegue primitive. Un agente deve conoscere quale servizio sta usando e con
quali permessi. Leggere piu' codice riduce il rischio di errori, non li elimina.

Per uso remoto adottare il contratto [T225](T225_REMOTE_MCP_SERVICE_SPEC.md):
Streamable HTTP su HTTPS, OAuth come autorizzazione alla risorsa e isolamento
principal/tenant/sessione. mTLS e firme Ed25519 hanno ruoli aggiuntivi distinti;
non sono sostituti intercambiabili di OAuth o TLS. La sessione non e' una
credenziale. Rate limit, limiti del lavoro, provenienza e protezione dal replay
richiedono implementazione e prove specifiche.

## E10 - Economia separata e budget non autoassegnabili

**Riferimenti:** Art. IV e T223/T224.

La scelta di tenere fuori dal manifesto di riferimento i meccanismi monetari
e' compatibile con un work package sperimentale separato. Dichiarare in modo
esplicito tale separazione per DAT/VTEC invece di ignorarne l'esistenza.

I DAT di T223 sono stato process-local e il chiamante puo' mintarli: non sono un
limite di spesa affidabile per un agente non vincolato. T225 iniziale esclude
`dat_mint`/`dat_spend`; una futura estensione richiede quote assegnate da un
operatore indipendente, proprieta' verificata e transazioni idempotenti.

## E11 - Audit, replay e affermazioni di sicurezza

**Riferimenti:** R2, R8, B, G.5/G.6 e H.

Un file JSONL append-only non e' automaticamente immutabile. Definire attori,
storage, checkpoint indipendenti, gestione chiavi, retention e verifiche.
Una firma autentica il mittente e l'integrita' del messaggio, non la verita'
della telemetria. L'override deve essere autenticato e autorizzato; "sempre
onorato" non significa accettare un override da chiunque.

Separare replay del payload numerico da timestamp, expiry e identificatori.
Registrare input, clock di valutazione, dipendenze e policy; dichiarare il
perimetro in cui l'identicita' bit-for-bit e' ottenibile. Per componenti non
deterministiche usare criteri e tolleranze preregistrati. Un elenco di standard
non costituisce certificazione o valutazione di conformita'.

## E12 - Evidenza sperimentale e sequenza di sviluppo

**Riferimenti:** G, WP1-WP9, T208 e T224.

[T224](T224_MCP_REGULATION_EXPERIMENT_SPEC.md) dimostra una connessione reale
tra client e primitive, ma usa un benchmark deterministico sintetico. Nel run
di riferimento i token sintetici passano da 360 a 220 mentre i completamenti
corretti scendono da 3/4 a 2/4: la policy e' `rejected`. Questo risultato non va
riscritto come validazione positiva del Paradigma 6.0, ne' generalizzato a LLM,
risparmio energetico fisico o workload industriali.

Conservare quel risultato e definire un nuovo esperimento distinto, con policy
e criteri congelati prima del run e dati nuovi per una validazione successiva.
Priorita': correzioni del contratto, prototipo limitato, prove negative e
revisione indipendente; gli adapter dei diversi domini restano work package
separati. T217 continua a richiedere qualifica prima dell'integrazione operativa.

## Tracciabilita' editoriale e prossimo passo

T225 recepisce E02-E04 nei confini dei futuri gate, E08-E10 nei contratti di
accesso e stato, E11 in audit/replay ed E12 nella sequenza di verifica. E05-E06
restano ipotesi di ricerca da specificare e testare nei rispettivi ticket:
il servizio remoto non introduce implicitamente Kuramoto, H3 o una nuova
policy di controllo.

La successiva revisione del PDF deve integrare E01-E12, aggiornare i riferimenti
di commit e rendere visibili i risultati nulli/negativi. Questa errata non
rigenera il PDF e non cambia codice, dipendenze, endpoint o permessi.

