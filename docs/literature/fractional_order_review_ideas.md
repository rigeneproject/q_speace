# Fractional-order review — idee emerse, non implementate

**Status**: speculative notes (NOT a spec, NOT a plan, NOT validated)
**Source**: review sui "comportamenti di ordine frazionario" condivisa da Rajasekar, India
**Date**: 2026-08-22
**Author**: Q-SPEACE (curation note, no implementation implied)

> **Epistemic disclaimer (obbligatorio)**
>
> Questa nota elenca idee concettuali emerse da una review di letteratura.
> **Nessuna di queste idee è stata validata sperimentalmente su dati
> SPEACE**. Sono "background speculativo", non "modelli operativi". Non
> costituiscono triangolazione (vedi `memory/epistemic-honesty-papers.md`):
> sono punti di contatto *teorici* tra formalismi matematici noti
> (derivate frazionarie, kernel di Mittag-Leffler, voli di Lévy,
> meccanica quantistica frazionaria di Laskin) e primitive già presenti
> nel repo. Ogni punto che diventasse operativo richiederebbe (1)
> scoping dedicato, (2) benchmark sintetico riproducibile, (3) review
> PR con adversarial verify.

---

## 1. STDP a power-law → affinamento del NeuroplasticKernel

### Stato attuale (verificato in `docs/T202_SPIKING_SPEC.md` § 3)

La regola STDP-like implementata è **EMA decay esponenziale**:
```
w(Δt) ∝ exp(-λ·Δt) · rate
```
(vedi `q_speace/spiking/plasticity.py`, BCEL riga "Frequency-based
plasticity" = functional).

### Punto della review

La review (Sez. X) cita lavori su *"fractional order electrical
conductance"* delle membrane cellulari e su pattern geometrici scale-free
nelle reti neurali biologiche. Letteratura indipendente (non verificata
qui) riporta che tracce di eleggibilità sinaptica mostrano *power-law
forgetting* meglio descritto da derivate di ordine frazionario che da
decadimento esponenziale puro.

### Mappatura su SPEACE

Il kernel STDP attuale ha un singolo parametro λ. Una versione
frazionaria userebbe un **kernel di Mittag-Leffler**:
```
E_α(-λ·t^α) = Σ (-1)^k · (λ·t^α)^k / Γ(α·k + 1)
```
con α ∈ (0, 2] — per α = 1 si riduce all'esponenziale classico
(retrocompatibile).

### Cosa servirebbe per renderlo operativo (non in scope qui)

1. Verifica firma attuale di `NeuroplasticKernel` (esiste già un
   parametro di shape, o serve una nuova firma?).
2. Scelta parametrizzazione: serie ipergeometrica troncata vs Laplace
   pair tabulato vs approssimazione a somma di esponenziali (prism
   method).
3. Benchmark sintetico minimo: spike-pair protocol STDP con ISI
   variabile (10, 50, 100, 500 ms), esponenziale vs Mittag-Leffler,
   su dati generati, *prima* di toccare il sidecar.
4. Adversarial verify del benchmark: un reviewer che cerca di
   dimostrare che la differenza è indistinguibile dal rumore.

**Costo/beneficio attuale**: la differenza fenotipica tra esponenziale
e Mittag-Leffler emerge su finestre lunghe (>> 1/λ). Per i task
correnti di SPEACE (rate, sparsity, energy accounting) l'esponenziale
è probabilmente sufficiente. Il valore aggiunto emergerebbe solo
quando la plasticità dovrà mantenere memoria cross-session.

---

## 2. Damping non-esponenziale → eligibility trace a coda pesante

### Punto della review (Sez. III)

Sistemi con attrito a legge di potenza mostrano "fractional order
dampings" — l'energia non decade come `exp(-γt)` ma come
`t^(-α)`.

### Mappatura su SPEACE

Stesso principio del § 1 applicato all'eligibility trace. Se § 1 viene
implementato, questo cade gratis (sostituire il kernel di decadimento
in un punto solo). Se § 1 non viene implementato, l'eligibility trace
da sola non giustifica il cambio.

**Status**: subordinato a § 1.

---

## 3. Schrödinger frazionaria (Laskin) → ispirazione per Q* / ILF

### Punto della review (Sez. VIII)

L'equazione di Schrödinger frazionaria di Laskin sostituisce i path
integrali Gaussiani con **voli di Lévy**: il propagatore non è più
`exp(-|x|²/4Dt)` ma `exp(-|x|^α / Dt)` con α ∈ (0, 2]. Questo cambia
il tipo di "esplorazione dello spazio" fatto dal sistema.

### Mappatura concettuale (NON formale) su SPEACE

La cascata RG/Haken di Q-SPEACE propaga *segnature coarse-grained*
(φ, S, σ) tra livelli invece dello stato pieno. Questo è un'idea
*topologicamente* parente della scelta di Laskin (sostituire una
struttura "piena" con una struttura "a salti"), ma **non è la stessa
cosa**:

- Laskin cambia la *metrica* dello spazio (Lévy vs Gauss).
- RG cambia la *granularità* dell'informazione mantenendo la struttura
  locale.

Queste sono parenti per analogia, non identiche per costruzione.

### Cautela esplicita

Proporre Lévy come "modello operativo" per il calcolo del baricentro
Q* significherebbe ridefinire il dominio, non affinare un'euristica.
**Status**: ispirazione concettuale, non modello operativo. Non aprire
issue T-SPB su questa base senza scoping separato.

---

## 4. Scale-free nested-cascade → analogia con l'architettura Q-SPEACE

### Punto della review (Sez. VII e X)

Diffusione anomala e pattern frattali in strutture biologiche
multiscala (dai polmoni alle fibre muscolari ai neuroni).

### Mappatura su SPEACE

L'architettura nested-cascade di Q-SPEACE — dove solo l'informazione
coarse-grained attraversa i confini tra livelli — risuona con
l'osservazione biologica che strutture scale-free riducono il costo
metabolico del trasporto (West, Brown, Enquist 1997, "A General
Model for the Origin of Allometric Scaling Laws in Biology").

**Importante**: è un'**analogia strutturale**, non un'**equivalenza
formale**. La giustificazione della cascata in Q-SPEACE rimane la
schiavitù dei parametri d'ordine di Haken (slaving principle), non
l'ottimizzazione metabolica biologica.

**Status**: analogia documentale utile, non vincolante per il design.

---

## 5. Metamateriali / elettrodinamica frazionaria → radio layer

### Punto della review (Sez. V)

Propagazione in mezzi con memoria elettromagnetica descritta da
derivate frazionarie.

### Mappatura su SPEACE

Rilevante **solo se** in futuro il radio layer (Strato 2, SDR /
beamforming) dovrà modellare propagazione in mezzi dispersivi o con
memoria (es. terreno, ionosfera). Per ora il modello del radio layer
non include questa fenomenologia.

**Status**: riferimento di riserva, non urgente. Aggiungere in coda al
backlog radio layer se mai quel layer verrà esteso.

---

## 6. Physics of Toys — analogia pedagogica Slinky

### Punto del libro

Il capitolo sullo **Slinky che cade** illustra che la perturbazione
gravitazionale si propaga lungo la molla a velocità finita (≈ velocità
del suono nel mezzo), non istantaneamente.

### Mappatura su SPEACE

Concettualmente parente del principio Q-SPEACE per cui *solo le
segnature coarse-grained attraversano i livelli gerarchici*. Ma —
**cautela** — illustra in realtà un principio diverso:

- Slinky = propagazione a velocità finita (= causalità relativistica).
- Coarse-graining Q-SPEACE = perdita di informazione non essenziale
  (= schiavitù di Haken).

Sono parenti per *metafora* ("niente si propaga gratis"), non per
*meccanica*. Usare in una presentazione esterna solo se accompagnata
dalla formula: *"analogia, non modello — la vera motivazione del
coarse-graining in Q-SPEACE è la schiavitù dei parametri d'ordine di
Haken"*. Mai presentare Slinky + Lévy + Laskin come concatenazione
implicita: Slinky dice "propagazione finita", Laskin dice "salti
lunghi", sono **opposti** (un volo di Lévy può propagare
istantaneamente in senso statistico).

**Status**: immagine efficace per divulgazione, con caveat obbligatorio.

---

## 7. Riassunto operativo

| Punto | Promettente? | Cosa serve per renderlo operativo | Owner proposto |
|---|---|---|---|
| 1. STDP Mittag-Leffler | Sì, con scoping | Scoping 1 pagina + benchmark sintetico + PR | T-SPB (futuro) |
| 2. Eligibility trace a coda pesante | Subordinato a § 1 | Cade gratis con § 1 | — |
| 3. Laskin / Q* | No (oggi) | Ridefinizione di dominio, non affinamento | Nessuno per ora |
| 4. Scale-free cascade | No (analogia) | Già documentato, basta menzionare | AACM paper § background |
| 5. Metamateriali / radio | No (oggi) | Backlog radio layer | Nessuno per ora |
| 6. Slinky divulgazione | Sì, con caveat | Usare in presentazione solo con disclaimer | Outreach (futuro) |

---

## 8. Cosa NON è questa nota

- Non è una spec (mancano scelte implementative vincolanti).
- Non è un backlog (i punti 3 e 5 non hanno urgenza).
- Non è una triangolazione (manca validazione sperimentale su SPEACE).
- Non è un proof-of-concept (tutti i numeri sono concettuali).

Per diventare uno qualsiasi di questi servono: scoping dedicato,
benchmark riproducibile, PR con adversarial verify, e una decisione
esplicita sulla priorità rispetto al backlog T-SPB corrente.

---

## 9. Riferimenti interni (cross-link)

- `docs/T202_SPIKING_SPEC.md` § 3 — regola STDP attuale (EMA esponenziale)
- `q_speace/spiking/plasticity.py` — implementazione corrente
- `q_speace/orchestrator.py` — calcolo del baricentro Q*
- `docs/T-SPB-0A_PLAN.md`, `T-SPB-4` — roadmap cognitive interface
- `docs/q_speace_economy.md` — applicazioni in q_speace_economy
- `memory/rajasekar-bibliography-notes.md` — mappatura titoli Rajasekar
- `memory/epistemic-honesty-papers.md` — regola di onestà epistemica
- `memory/aacm-rule-10-triangulation.md` — Vincolo D e triangolazione

---

## 10. Analisi del feedback GPT (2026-08-22)

> **Provenance**: riflessione prodotta da un modello esterno (GPT) sul
> prompt che includeva la review Rajasekar e una sintesi delle § 1–6 di
> questa nota. Trattata come **input per ragionare**, non come fonte
> primaria. Nessuna sezione di questa nota cita contenuti del feedback
> come se fossero referenti indipendenti.

### 10.1 Cosa del feedback è matematicamente fondato

1. **La distinzione "memory as storage" vs "memory as dynamics"** è un
   framing reale, presente in letteratura (Fusi & Abbott 2007 su
   criticalità e illusione di memoria; Tiño & Scherr 2020 su chaos in
   reservoir computing). La review Rajasekar non la inventa; la mette
   in forma matematica. Va bene come *frame narrativo* per un paper.

2. **L'interpretazione α < 1 → decadimento, α > 1 → persistenza** è
   coerente con le proprietà note del kernel di Mittag-Leffler
   `E_α(-λ·t^α)`. Conferma quanto detto in § 1.

3. **L'idea di un kernel integrale `M(t) = ∫₀ᵗ K(t-τ;α) x(τ) dτ` al
   posto di working/STM/LTM stratificate** è un costrutto standard
   (operatori di Volterra, fading memory di Boyd-Chua, neural ODE con
   memoria). È *una* soluzione, non *la* soluzione al problema della
   stratificazione mnemonica.

### 10.2 Cosa del feedback è retorica overclaim o design prematuro

1. **"Memory as dynamics vs memory as storage" come dicotomia esclusiva**
   è una semplificazione narrativa. Biologicamente il sistema fa
   entrambe le cose su scale diverse (dynamics a breve, storage a
   lungo). Trattarle come alternative è forte, non accurato.

2. **I nomi "Fractional Memory Phenotype" e "Fractional Neuroplasticity
   Layer (FNL)"** sono labeling creativo. Senza (a) equazione operativa
   del layer, (b) protocollo sperimentale che distingua FNL da un
   EMA multi-scala parametrizzato, (c) definizione operativa di Θ, Kₜ,
   αₜ, sono etichette. Accettabili come brainstorm; non come design.

3. **α(t) dinamico guidato da `α(t) = G(E(t), C(t), R(t))`** è il
   punto più delicato. **Cautela matematica seria**: un operatore
   D^α(t) con α che varia nel tempo *perde* stazionarietà e la proprietà
   di memoria non locale che la fractional calculus dovrebbe fornire.
   Se α è a sua volta frutto di un'equazione con i suoi parametri, si
   è solo spostato il problema di un livello. La review Rajasekar non
   affronta α(t); non lo affronta nemmeno il feedback. **Non
   presentarlo come se fosse risolto**.

4. **"Il paper potrebbe offrirci non un'altra tecnica ma una
   formalizzazione del concetto di memoria storicamente attiva"** è
   retorica. La fractional calculus *è* una formalizzazione del
   concetto generale di memoria pesata, che esiste in molte forme
   (Volterra, fading memory, neural ODE). Non è *la* formalizzazione
   del problema specifico di SPEACE.

5. **"Passare dalla correzione dell'output alla trasformazione
   persistente del processo cognitivo"** è un *obiettivo* legittimo
   per Q-SPEACE, ma la fractional calculus da sola non lo realizza.
   Servirebbe una teoria di *come* α si aggiorna in funzione
   dell'esperienza, che è esattamente il punto che né la review né il
   feedback risolvono.

### 10.3 Cosa rimane in piedi dopo la verifica

Tenendo i piedi per terra:

- **§ 1 (STDP Mittag-Leffler)** rimane il punto operativo più
  promettente. Il feedback non aggiunge né toglie: serve benchmark
  sintetico esponenziale vs Mittag-Leffler su spike-pair STDP
  *prima* di parlare di FNL.
- **§ 6 (Slinky divulgazione)** rimane valido come analogia, *con il
  caveat* esplicito (non mescolabile con Lévy/Laskin).
- **§ 3, § 4, § 5 (Laskin, scale-free, metamateriali)** restano
  ispirazioni concettuali non operative — il feedback non le promuove.
- **FNL / Fractional Memory Phenotype** non diventano design: vanno
  riportati a livello di *brainstorm documentato* (questa sezione),
  con esplicito "richiede scoping matematico separato, non
  implementazione diretta".

### 10.4 Cosa NON è il feedback GPT

- Non è una fonte indipendente (è una rilettura della stessa review).
- Non è un proof-of-concept (nessun benchmark numerico).
- Non è una triangolazione (è lo stesso input, rielaborato).
- Non è una decisione di design (richiede validazione separata).

Per le regole di onestà epistemica vedi
`memory/epistemic-honesty-papers.md` e
`memory/aacm-rule-10-triangulation.md`.

---

## 11. Decisione finale: cosa rimane in piedi

Dopo la verifica del feedback esterno (§ 10), la situazione dei 6
punti della review + 1 punto Slinky + 1 punto FNL-feedback è la
seguente:

| Punto | Promettente? | Verdetto finale | Azione richiesta per diventare operativo |
|---|---|---|---|
| § 1 STDP Mittag-Leffler | Sì, con gating | Resta in piedi | Scoping 1 pagina + benchmark spike-pair sintetico + PR con adversarial verify |
| § 2 Eligibility trace a coda pesante | Subordinato | Cade gratis con § 1 | Nessuna azione separata |
| § 3 Laskin / Q* | No (oggi) | Resta fuori | Solo se mai Q* verrà riformulato; non oggi |
| § 4 Scale-free cascade | Solo analogia | Resta come background | Menzionare in AACM paper § background, non in design |
| § 5 Metamateriali / radio | No (oggi) | Resta riserva | Backlog radio layer; nessuna urgenza |
| § 6 Slinky divulgazione | Sì, con caveat | Resta valido | Usare in presentazione esterna con disclaimer obbligatorio |
| FNL / Fractional Memory Phenotype (feedback GPT) | No (design prematuro) | Resta brainstorm | Richiede scoping matematico separato; non implementazione diretta |

### 11.1 Cosa NON fare adesso

- Non aprire issue T-SPB per FNL.
- Non toccare `q_speace/spiking/plasticity.py` senza benchmark
  sintetico approvato.
- Non citare il feedback GPT in un paper come se fosse una fonte
  indipendente.
- Non presentare "memory as dynamics" come scoperta di SPEACE — è
  framing preesistente.

### 11.2 Cosa fare se l'obiettivo "trasformazione persistente" torna rilevante

Quando (e se) Q-SPEACE avrà bisogno di un meccanismo di
trasformazione persistente del processo cognitivo in seguito
all'esperienza, il percorso minimo onesto è:

1. Identificare la *specifica* proprietà che l'esponente α dovrebbe
   avere (decadimento monotono? coda pesante? finestra temporale
   fissa?).
2. Confrontare *almeno tre* formalismi candidati (esponenziale
   classico, kernel di Mittag-Leffler, neural ODE con memoria,
   reservoir con fading memory di Boyd-Chua).
3. Definire un protocollo sperimentale sintetico che distingua i
   candidati (es. spike-pair con ISI variabile + misura di
   discriminabilità statistica).
4. Solo dopo: scrivere uno spec, chiedere PR review con adversarial
   verify, e solo allora toccare il sidecar.

Questo percorso è indipendente dal fatto che la review Rajasekar o il
feedback GPT esistano: è la procedura standard di validazione
concettuale. La review può essere citata in quel momento come
*background*, non come *fonte del design*.

### 11.3 Stato del file

Questo file resta un **brainstorm documentato**, non una spec, non un
backlog operativo. Le § 1–6 mantengono il loro status originale; § 10
e § 11 sono il log della verifica del feedback ricevuto.

Per diventare uno qualsiasi di backlog operativo o spec, serve PR
separata con scoping dedicato.

