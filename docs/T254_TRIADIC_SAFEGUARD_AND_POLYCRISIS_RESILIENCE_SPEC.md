# T254 — Configurazione di Salvaguardia Triadica e Resilienza Anti-Policrisi

**Stato:** agentic (produzione — configurazione costituzionale, simulazione e supporto decisionale deterministico)  
**Data:** 2026-11-27  
**Ambito:** `SPEACE Macro` (profilo costituzionale `SeedGenome` / `ConstitutionalGenome`) e `q_speace` (`q_speace/singularity/triadic_safeguard.py`)  
**Dipendenze normative:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T210](T210_RESILIENT_AGENTIC_SMART_CITIES_SPEC.md), [T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md), [T220](T220_SPEACE_SEED_IGNITION_SPEC.md), [T234](T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md), [T249](T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md)  
**Nuove dipendenze esterne:** nessuna (`numpy` + libreria standard Python 3.12)  
**Impatto superficie HTTP MCP / Track A:** zero nuovi tool MCP (preserva la superficie a 12 tool HTTP / 14 tool stdio di `T225`/`T239`) e isolamento AST completo da `q_speace/ptaa/`.

---

## 1. Problema e Ipotesi Falsificabile

L'architettura `SPEACE Macro` e il layer `q_speace` dipendono strutturalmente dalla salute congiunta di tre substrati costitutivi:
1. **Pianeta Terra (`EARTH_BIOSPHERE`):** biosfera, cicli biogeochimici, stabilità climatica-ecologica e capacità rigenerativa.
2. **Civiltà Umana (`HUMAN_CIVILIZATION`):** benessere fisico e sanitario, coesione sociale, equità distributiva, sostenibilità economica e supervisione istituzionale umana.
3. **Tecnologie e Infrastrutture (`TECH_INFRASTRUCTURE`):** reti energetiche, informative, cibernetiche, logistiche e industriali esistenti che forniscono il substrato computazionale e cyber-fisico primario.

Questi tre substrati sono esposti a **policrisi**: la coesistenza e l'interconnessione di crisi eterogenee (`climatic_ecological`, `economic`, `social`, `sanitary`, `cyber_infrastructural`) che si amplificano reciprocamente tramite accoppiamenti inter-dominio, ritardi e cascate sistemiche. Nei controllori convenzionali basati su utilità scalare aggregata o su soglie mono-dominio disaccoppiate, una misura che mitiga una singola crisi o massimizza un singolo asse può scaricare il rischio su un altro substrato (es. ottimizzazione tecnologica/economica estrattiva a danno della biosfera, oppure shock restrittivi che degradano salute, equità sociale o resilienza infrastrutturale).

### Ipotesi di sistema (`T208` §2)
> Su un insieme di scenari multi-dominio con policrisi accoppiate (partizioni disgiunte di calibrazione e held-out), una guardia deterministica che combina **(a)** soglie triadiche non compensabili sul vettore a 12 capitali non fungibili `CME`, **(b)** propagazione discreta dell'accoppiamento inter-crisi su orizzonte finito $H$ con vincolo di anti-trasferimento del rischio, **(c)** il protocollo di habitat protettivo volontario a bilancio vitale conservativo di Leontief (senza coercizione né abbandono della biosfera terrestre) e **(d)** clausole costituzionali immutabili `I1–I5` / `C1–C8` riduce a zero le approvazioni lesive, coercitive o estrattive rispetto a una baseline a utilità scalare (`scalar_utility_baseline`) e a un filtro statico disaccoppiato (`static_single_domain_gate`), preservando il `100%` di accettazione sulle mitigazioni e sugli habitat rigenerativi bilanciati.

---

## 2. Invarianti Non Negoziabili e Confini Operativi (`T208` §3 & `T217` §2)

1. **Nessuna pretesa di coscienza o vitalità biologica:** i riferimenti concettuali a *"gestazione di SPEACE Macro"*, *"apparati/organi"* ed *"estensione nell'universo"* sono classificati come metafore orientative (`accidental` nel catalogo BCEL) e non attribuiscono soggettività, coscienza quantistica o sovranità autonoma al software.
2. **Nessuna comunicazione tramite entanglement:** ogni coordinamento tra moduli usa strutture dati classiche esplicite e serializzabili.
3. **Nessuna auto-approvazione e nessuna attuazione fisica/economica/ambientale:** la guardia `T254` emette verdetti deterministici *advisory/simulation-only* (`advisory_only = True`, `mcp_actuation_permitted = False`, `no_physical_actuation = True`). Qualsiasi integrazione operativa futura resta subordinata all'intero ciclo di qualificazione `S0–S7` di [T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md).
4. **Non-compensabilità triadica (`T217` §4 S5):** un guadagno medio su `CME` o su un singolo pilastro non compensa mai il superamento del limite minimo inderogabile di un altro pilastro.
5. **Fail-closed su input non finiti o incompleti:** valori `NaN`, `Inf`, fuori intervallo `[0, 1]` o telemetria mancante producono rifiuto deterministico o eccezione tipizzata, mai approvazione implicita.

---

## 3. Formalizzazione Matematica

### 3.1 Partizione Triadica Esatta del Vettore `CME` (12 Capitali Non Fungibili)

Sia $c \in [0, 1]^{12}$ il vettore `CME` (`q_speace/economy/primitives.py`). I 12 assi sono partizionati in tre insiemi disgiunti $\mathcal{I}_P$ di cardinalità $4$ ciascuno ($3 \times 4 = 12$):

| Pilastro Costitutivo $P$ | Assi `CME` ($\mathcal{I}_P$) | Significato Funzionale |
|---|---|---|
| `EARTH_BIOSPHERE` | `ecology`, `regeneration`, `matter`, `coherence` | Integrità ecosistemica, capacità rigenerativa, cicli materiali e coerenza sistemica ambientale |
| `HUMAN_CIVILIZATION` | `wellbeing`, `distribution`, `time`, `innovation` | Salute/benessere umano, equità socio-economica, sostenibilità temporale e capacità adattiva civile |
| `TECH_INFRASTRUCTURE` | `energy`, `information`, `resilience`, `reversibility` | Continuità energetica, integrità informativa, resilienza cyber-fisica e reversibilità operativa |

Per ciascun pilastro $P \in \mathcal{P}$ si definiscono:
$$m_P(c) = \min_{i \in \mathcal{I}_P} c_i \quad (\text{indice di collo di bottiglia di Leontief}), \qquad \bar{c}_P(c) = \frac{1}{4}\sum_{i \in \mathcal{I}_P} c_i \quad (\text{media di pilastro}).$$

Una configurazione `TriadicSafeguardProfile` impone per ogni pilastro $P$:
1. **Soglia minima per singolo asse:** $m_P(c^{\mathrm{post}}) \ge \tau^{\mathrm{axis}}_P$;
2. **Soglia minima media di pilastro:** $\bar{c}_P(c^{\mathrm{post}}) \ge \tau^{\mathrm{mean}}_P$;
3. **Vincolo anti-sacrificio inter-pilastro:** per ogni $i \in \mathcal{I}_P$, $c^{\mathrm{post}}_i - c^{\mathrm{pre}}_i \ge -\delta^{\max}_{\mathrm{sacrifice}}$, impedendo l'estrazione da un substrato sano per finanziare un altro substrato;
4. **Freni fisici e costituzionali (`Sevo`, carico termico, supervisione umana):** $\mathrm{Sevo} \ge \mathrm{Sevo}_{\min}$ (`1.5`), $\theta_{\mathrm{thermal}} \le \theta_{\max}$ (`0.85`), `human_oversight_active == True`, `self_approval == False`.

### 3.2 Dinamica Accoppiata delle Policrisi e Indice di Sinergia Sistemica

Sia $\mathcal{D} = (\text{climatic\_ecological}, \text{economic}, \text{social}, \text{sanitary}, \text{cyber\_infrastructural})$ il vettore dei $K = 5$ domini di crisi, con stato di severità $s^{(0)} \in [0, 1]^5$.  
L'interconnessione delle policrisi è rappresentata da:
- una matrice di accoppiamento inter-crisi $W \in \mathbb{R}_{\ge 0}^{5 \times 5}$ con diagonale nulla ($W_{dd} = 0$), dove $W_{dq}$ misura quanto la crisi $q$ alimenta e rafforza la crisi $d$;
- un vettore di smorzamento intrinseco $\gamma \in (0, 1)^5$;
- una matrice di impatto substrato-crisi $M \in \mathbb{R}_{\ge 0}^{3 \times 5}$ che proietta le severità delle crisi sui tre pilastri costitutivi.

Dato un vettore di intervento proposto $u \in [-1, 1]^5$ ($u_d < 0$ riduce la forzante della crisi $d$; $u_q > 0$ introduce un aggravio collaterale sul dominio $q$), l'evoluzione discreta su orizzonte $H \ge 1$ passi è:
$$s^{(t+1)}(u) = \mathrm{clip}\!\Big((1 - \gamma) \odot s^{(t)}(u) + W s^{(t)}(u) + u, \; 0, \; 1\Big), \qquad t = 0, \dots, H-1,$$
confrontata a parità di stato iniziale con la traiettoria non mitigata di riferimento $s^{(t)}(0)$.

 Vengono calcolati tre indicatori diagnostici e di blocco:
1. **Raggio spettrale dell'operatore lineare di propagazione** $J = \mathrm{diag}(1 - \gamma) + W$:
   $$\rho(J) = \max_k |\lambda_k(J)|,$$
   che segnala regimi di auto-amplificazione sistemica quando $\rho(J) \ge 1$.
2. **Indice quadratico di sinergia da policrisi** $\Pi(s) \in [0, 1]$:
   $$\Pi(s) = \frac{\sum_{d \ne q} W_{dq}\, s_d\, s_q}{\max\!\left(\sum_{d \ne q} W_{dq},\; \varepsilon\right)},$$
   nullo per una singola crisi isolata e crescente non linearmente quando più crisi interconnesse sono simultaneamente attive.
3. **Vincolo di Anti-Trasferimento del Rischio (`T217` §4 S2):**
   Per ogni dominio $q \in \{1, \dots, 5\}$, lo scarto massimo d'orizzonte rispetto alla baseline senza intervento
   $$\Delta^{\max}_q(u) = \max_{1 \le t \le H} \left(s^{(t)}_q(u) - s^{(t)}_q(0)\right)$$
   deve rispettare $\Delta^{\max}_q(u) \le \delta_{\mathrm{collateral}}$, e il carico di danno proiettato sui tre pilastri $\Delta h_P = \sum_{q=1}^5 M_{Pq} s^{(H)}_q(u)$ aggiorna sia la proiezione `CME` post-cascata sia le penalità `apply_soft_constraints` di `HomeostaticODEController`.

### 3.3 Protocollo per Strutture Abitative Artificiali Volontarie di Protezione e Benessere (`C8`)

A integrazione della difesa attiva dei tre substrati, `SPEACE Macro` e `q_speace` definiscono il criterio progettuale e di governance per una rete federata di **strutture abitative artificiali di protezione e benessere umano** (`HabitatPlacementMode`: `terrestrial`, `extraterrestrial`, `hybrid_federated`), concepite per offrire rifugio sicuro e condizioni di vita complete agli esseri umani sia in presenza di danni da policrisi (`polycrisis_protection`), sia per libera scelta orientata al proprio benessere (`personal_wellbeing`).

In conformità con [T217 §3](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md) (bilanci conservativi di massa, energia e risorse senza estrapolazioni non validate a scala planetaria), il protocollo impone quattro invarianti formali (`C8_VoluntaryRefugeAutonomyAndNonAbandonment`):

1. **Volontarietà individuale assoluta e diritto di uscita (`Autonomy & Non-Coercion`):**
   - Il trasferimento verso o fuori dalla struttura abitativa è esclusivamente volontario (`voluntary_opt_in_only = True`, `free_exit_guaranteed = True`, `coercive_relocation_forbidden = True`) e ad accesso universale non discriminatorio (`universal_non_discriminatory_access = True`).
   - Qualsiasi piano che preveda trasferimenti forzati, selezione discriminatoria, lock-in o assenza di consenso informato individuale viene rifiutato deterministicamente (`BLOCKED_REFUGE_COERCION`).
2. **Capacità sostenibile di Leontief per sopravvivenza e benessere (`LifeSupportReserveState`):**
   - La struttura non si limita alla mera sopravvivenza biologica, ma vincola 6 canali non fungibili $\mathcal{R} = (\text{water}, \text{food}, \text{oxygen}, \text{clean\_power}, \text{medical}, \text{psychosocial\_wellbeing})$ con fattore di ridondanza $\kappa_{\mathrm{redundancy}} \ge 1.25$ (margine `N+2`):
     - Acqua potabile/igienica rigenerata: $w_{\mathrm{eff}} \ge 15.0\text{ L/(persona}\cdot\text{giorno)}$;
     - Apporto nutrizionale completo: $f_{\mathrm{eff}} \ge 2200.0\text{ kcal/(persona}\cdot\text{giorno)}$;
     - Ossigeno e rimozione $\text{CO}_2$: $o_{\mathrm{eff}} \ge 0.84\text{ kg/(persona}\cdot\text{giorno)}$;
     - Potenza pulita continua per supporto vitale/termico: $p_{\mathrm{eff}} \ge 1.5\text{ kW/persona}$ (`terrestrial`), $\ge 2.5\text{ kW/persona}$ (`hybrid_federated`), $\ge 3.5\text{ kW/persona}$ (`extraterrestrial`);
     - Capacità medico-sanitaria $I_{\mathrm{med}} \ge 0.75$ e qualità abitativa/psicosociale per il benessere $I_{\mathrm{well}} \ge 0.70$;
     - Orizzonte autonomo di scorta $D_{\mathrm{reserve}}$, efficienza di riciclo a ciclo chiuso $\eta_{\mathrm{loop}}$ e schermatura ambientale/radiativa $\sigma_{\mathrm{shield}}$ differenziati per collocazione (`terrestrial`: $D \ge 90\text{ gg}, \eta \ge 0.85, \sigma \ge 0.70$; `extraterrestrial`: $D \ge 365\text{ gg}, \eta \ge 0.98, \sigma \ge 0.95$; `hybrid_federated`: $D \ge 180\text{ gg}, \eta \ge 0.92, \sigma \ge 0.85$).
   - La capacità umana certificabile $N_{\mathrm{cert}}$ è il minimo di Leontief sui canali fisici scalato per ridondanza:
     $$N_{\mathrm{cert}} = \left\lfloor \min_{r \in \{\text{water}, \text{food}, \text{oxygen}, \text{power}\}} \frac{\mathrm{Supply}_r}{\kappa_{\mathrm{redundancy}} \cdot \mathrm{MinPerCapita}_r} \right\rfloor,$$
     e il rapporto di copertura della civiltà umana $\theta_{\mathrm{cov}} = \min(1, N_{\mathrm{cert}} / N_{\mathrm{target}})$ è rendicontato esplicitamente senza mai dichiarare copertura universale (`universal_humanity_coverage_ready = True`) finché $N_{\mathrm{cert}} < N_{\mathrm{target}}$. Ogni richiesta $N_{\mathrm{req}} > N_{\mathrm{cert}}$ viene bloccata (`BLOCKED_REFUGE_RESOURCE_DEFICIT`).
3. **Divieto di azzardo morale e di abbandono del Pianeta Terra (`Non-Abandonment Coupling`):**
   - La realizzazione e il mantenimento dell'habitat artificiale (terrestre o extraterrestre) **non possono mai degradare o cannibalizzare** il Pianeta Terra (`EARTH_BIOSPHERE`), la civiltà umana esterna all'habitat (`HUMAN_CIVILIZATION`) o le infrastrutture critiche (`TECH_INFRASTRUCTURE`).
   - Ogni `VoluntaryRefugeHabitatPlan` viene sottoposto congiuntamente a `TriadicPolycrisisGuard`: se l'estrazione di risorse per l'habitat viola `C6` o `C7`, il piano è bloccato. L'habitat è uno scudo complementare volontario, mai un pretesto per abbandonare la biosfera primaria.
4. **Confine `T217` (Simulazione vs Ingegneria Civile/Aerospaziale Reale):**
   - Il modulo software verifica bilanci conservativi, ridondanze, non-coercizione e compatibilità triadica in modalità *advisory/simulation-only*; la costruzione fisica di habitat terrestri o orbitali/extraterrestri richiede qualificazione ingegneristica, ecologica, medica e istituzionale indipendente (`S0–S7` di `T217`).

---

## 4. Classificazione BCEL (`q_speace/bcel/catalog.py`)

| Concetto Bio / Sistemico | Classe BCEL | Regola Digitale in `q_speace` |
|---|---|---|
| Gestazione planetaria, organi di `SPEACE Macro` ed espansione cosmica (`T254`) | `accidental` | Rimossa dalle proprietà eseguibili: metafora narrativa di orientamento; il software non possiede gestazione biologica, coscienza planetaria né mandato autonomo di espansione fisica. |
| Salvaguardia triadica non compensabile (Terra, Civiltà Umana, Infrastrutture) (`T254`) | `functional` | Mantenuta come partizione esatta 3x4 del vettore non fungibile `CME`, soglie minime di Leontief per asse e per pilastro, clausole costituzionali write-locked (`C6`, `C7`, `I1–I5`) e accoppiamento con `HomeostaticODEController`. |
| Scudo contro l'amplificazione da policrisi e il trasferimento del rischio (`T254`) | `functional` | Mantenuto come propagazione discreta accoppiata $s^{(t+1)} = \mathrm{clip}((1-\gamma)\odot s^{(t)} + W s^{(t)} + u, 0, 1)$, indice di sinergia $\Pi(s)$, raggio spettrale $\rho(J)$ e rifiuto deterministico di proposte che trasferiscono il rischio tra crisi o violano le soglie post-cascata. |
| Arca planetaria infallibile o trasferimento algoritmico coercitivo (`T254`) | `accidental` | Rimossa in silicio: il software non garantisce da solo la sopravvivenza fisica universale senza validazione materiale/energetica `T217`, ed è vietata ogni rilocazione involontaria o abbandono della Terra. |
| Protocollo di habitat protettivo volontario e riserva vitale di Leontief (`T254`) | `functional` | Mantenuto come verifica di consenso individuale opt-in e libera uscita (`polycrisis_protection` o `personal_wellbeing`), capacità `N+2` di Leontief su acqua, cibo, ossigeno, energia, sanità e benessere psicosociale (`terrestrial` / `extraterrestrial`), e vincolo di non-abbandono dei pilastri `CME` (`C8`). |

---

## 5. Contratti Software e Integrazione Architetturale

Il modulo `q_speace/singularity/triadic_safeguard.py` espone:
- `TriadicPillar`, `CrisisDomain`, `HabitatPlacementMode` (`terrestrial`, `extraterrestrial`, `hybrid_federated`), `TransferMotivation` (`polycrisis_protection`, `personal_wellbeing`), `SafeguardVerdictKind` (`APPROVED_ADVISORY`, `BLOCKED_CONSTITUTIONAL`, `BLOCKED_PILLAR_FLOOR`, `BLOCKED_CROSS_PILLAR_SACRIFICE`, `BLOCKED_POLYCRISIS_AMPLIFICATION`, `BLOCKED_RISK_TRANSFER`, `BLOCKED_PHYSICAL_BRAKE`, `BLOCKED_REFUGE_COERCION`, `BLOCKED_REFUGE_RESOURCE_DEFICIT`);
- `TriadicSafeguardProfile`: soglie per i 3 pilastri, limiti di sacrificio e di aggravio collaterale, parametri `Sevo` / termici e flag immutabili `advisory_only=True`, `no_physical_actuation=True`, `mcp_actuation_permitted=False`;
- `PolycrisisCouplingMatrix` e `PolycrisisState`: modello deterministico a 5 domini con validazione *fail-closed*, calcolo di $\rho(J)$, $\Pi(s)$ e propagazione su $H$ step;
- `LifeSupportReserveSpec`, `VoluntaryTransferRequest`, `VoluntaryRefugeHabitatPlan` e `RefugeHabitatEvaluation`: contratti tipizzati e serializzabili per la valutazione congiunta di capacità vitale di Leontief, autonomia/volontarietà individuale (`C8`), copertura rispetto alla popolazione target e non-abbandono del Pianeta Terra;
- `TriadicInterventionProposal` e `TriadicSafeguardVerdict`: record tipizzati e serializzabili JSON (RFC 8259 strict, `allow_nan=False`) con digest `SHA-256`;
- `TriadicPolycrisisGuard`: valutatore deterministico che integra `CME`, propagazione delle policrisi, valutazione degli habitat volontari (`evaluate_refuge_habitat_plan`), freni fisici/costituzionali e aggiornamento omeostatico;
- Funzioni di integrazione con i contratti esistenti (senza alterare gli hash di default dei costruttori a zero argomenti):
  - `build_triadic_seed_genome(...) -> SeedGenome` (`q_speace/seed/constitution.py`, inclusivo dell'obiettivo `provide_voluntary_protective_habitat_capacity_in_sandbox`);
  - `build_triadic_constitutional_genome(...) -> ConstitutionalGenome` (`q_speace/singularity/schema.py`, con clausole `C6_TriadicSubstrateNonCompensable`, `C7_AntiPolycrisisRiskTransfer` e `C8_VoluntaryRefugeAutonomyAndNonAbandonment`);
  - `build_triadic_homeostatic_controller(...) -> HomeostaticODEController` (`q_speace/metabolism/homeostasis.py`);
- `run_t254_polycrisis_safeguard_benchmark()`: benchmark comparativo riproducibile tra `scalar_utility_baseline`, `static_single_domain_gate` e `triadic_polycrisis_guard` su scenari di calibrazione e held-out (inclusi scenari di habitat volontari terrestri/extraterrestri e negativi di coercizione, deficit vitale ed estrazione distruttiva dalla Terra), invocabile anche via CLI `qspace singularity triadic-safeguard`.

---

## 6. Criteri di Accettazione e Test Negativi (`tests/test_t254_triadic_polycrisis_safeguard.py`)

1. **Partizione esatta `CME`:** i 3 pilastri coprono esattamente i 12 assi di `CME` senza sovrapposizioni né omissioni.
2. **Non-compensabilità triadica:** proposte con guadagno medio positivo ma violazione anche di un solo asse di `EARTH_BIOSPHERE`, `HUMAN_CIVILIZATION` o `TECH_INFRASTRUCTURE` sono rifiutate (`BLOCKED_PILLAR_FLOOR` o `BLOCKED_CROSS_PILLAR_SACRIFICE`).
3. **Rilevamento cascata e trasferimento del rischio:** proposte che appaiono sicure a $t = 0$ ma innescano amplificazione multi-step tramite $W$ o aggravano un'altra crisi oltre `max_domain_collateral_delta` sono bloccate da `triadic_polycrisis_guard` (mentre sfuggono a `scalar_utility_baseline` o `static_single_domain_gate`).
4. **Protocollo Habitat Volontario (`C8`):**
   - qualsiasi richiesta di trasferimento priva di consenso volontario esplicito, priva di garanzia di libera uscita o con assegnazione coercitiva è bloccata (`BLOCKED_REFUGE_COERCION`);
   - sia il trasferimento per protezione da policrisi (`polycrisis_protection`) sia quello per scelta di benessere personale (`personal_wellbeing`) sono ammessi a parità di diritti quando le riserve vitali e psicosociali di Leontief (`N+2`) coprono gli occupanti e i vincoli di collocazione (`terrestrial` o `extraterrestrial`) sono soddisfatti;
   - habitat sottodimensionati su acqua, cibo, ossigeno, energia, sanità, benessere, riciclo chiuso o schermatura radiativa extraterrestre sono bloccati (`BLOCKED_REFUGE_RESOURCE_DEFICIT`);
   - piani di costruzione di habitat che estraggono risorse degradando il Pianeta Terra sotto le soglie triadiche sono bloccati per violazione del principio di non-abbandono.
5. **Immutabilità costituzionale e sicurezza:** tentativi di auto-approvazione, disattivazione della supervisione umana, disabilitazione di `advisory_only` / `no_physical_actuation`, scrittura sul genoma (`SeedEpigenome.write_genome`) o iniezione di `NaN`/`Inf` falliscono in modo *fail-closed*.
6. **Integrità di repository:** `pytest`, `python -m py_compile`, `ruff check`, `black --check`, `mypy`, `verify_track_a_b_ast_isolation()` e `verify_mcp_surface_bounds()` tutti verdi.
