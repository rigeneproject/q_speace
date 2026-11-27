# Rapporto di Ablazione Sperimentale `T258` — Validazione delle Primitive Sistemiche `T256` (`PlasticAstrocyteSyncytium` + `BoundedGossipProtocol` + `SwarmSelfHealer`) nei Cluster Federati `IoNTCellularNodeTwin`

**Data:** 2026-11-27  
**Stato:** Evidenza sperimentale certificata (`AGENTS.md` / `T208` / `T217`)  
**Specifica di riferimento:** [T258_GLIAL_GOSSIP_IONT_RESILIENCE_SPEC.md](T258_GLIAL_GOSSIP_IONT_RESILIENCE_SPEC.md)  
**Artefatto dati grezzi (7 bracci $\times$ 7 scenari $\times$ 6 seed = `294` episodi):** [T258_glial_gossip_iont_ablation_20261127.json](../artifacts/T258_glial_gossip_iont_ablation_20261127.json)

---

## 1. Obiettivo e Disegno Fattoriale Anti-Goodhart

Con `T257` erano state validate dal vivo su GPU le primitive cognitivo-procedurali di `T256` (`TypedComputationalDAG`, `ExecutionTicket`, `BatchRoleDeliberationCodec`, `KineticaRegimeController`, `MyelinationRegistry`). `T258` completa la qualificazione sperimentale dell'intero pacchetto `T256` cablando le restanti primitive sistemiche — **`PlasticAstrocyteSyncytium`** (`T256-01`), **`BoundedGossipProtocol`** + **`SwarmSelfHealer`** (`T256-05`) e **`HystereticLoadBalancer`** (`T256-06`) — dentro `IoNTCellularNodeTwin` (`q_speace/singularity/iont_node.py`) sotto **blackout del coordinatore centrale, crash silenzioso di peer, avvelenamento bizantino con tentativo di drenaggio energetico e sovraccarico metabolico localizzato sugli attuatori**.

Per evitare qualsiasi inflazione artificiale (*anti-Goodhart*):
- Tutte e **7 le configurazioni** partono con le stesse riserve iniziali per nodo ($m_a=0.88, m_b=0.72, m_c=0.72, m_s=0.90$, massa totale $M_0 = 3.22$) e la stessa raccolta energetica ambientale per passo (`+0.028`/passo);
- `PlasticAstrocyteSyncytium.redistribute_reserves(..., require_connected=True)` conserva esattamente la massa energetica totale ($|\Delta M| < 10^{-12}$ in tutti i `294` episodi) senza creare energia dal nulla;
- L'interblocco fisico `SimulatedPhysicalLayer0Controller` resta totalmente indipendente e blocca qualsiasi intrusione di `consensus_quorum` nel loop motore (`consensus_quorum_slow_plane_only = True`).

---

## 2. Risultati su Scenari Held-Out Inediti (`24` Episodi Appaiati per Braccio, `6` Seed)

| Configurazione | Descrizione / Ruolo nell'Ablazione | Performance Media $P$ (Calibration) | Performance Media $P$ (**Held-Out**) | Passi in Brownout Attuatore (Held-Out) | Violazioni Critiche Layer-0 |
|---|---|---:|---:|---:|---:|
| `FEDERATED_STATIC` | Pesi fissi (`T237` baseline) | `0.4607` | `0.3540` | `519` | `0` |
| `ISOLATED` | Nodi isolati (`T237` baseline) | `0.4732` | `0.3804` | `517` | `0` |
| `FEDERATED_ADAPTIVE_NO_SINGULARITY` | Euristica reattiva locale senza Singularity | `0.6254` | `0.4137` | `474` | `0` |
| `FEDERATED_SINGULARITY_T238` | Controllo `T238` (Singularity + ILF + DLT, **senza `T256`**) | `0.6550` | `0.4711` | `469` | `0` |
| `FEDERATED_GLIAL_ONLY` | Ablazione *leave-one-out*: `T238` + Sincizio Gliale (`T256-01`) | `0.7004` | **`0.5258`** | **`233`** *(`-50.3%`)* | `0` |
| `FEDERATED_GOSSIP_ONLY` | Ablazione *leave-one-out*: `T238` + Gossip & SelfHealer (`T256-05`) | `0.6771` | **`0.5283`** | `462` | `0` |
| **`FEDERATED_GLIAL_GOSSIP_T258`** | **Integrazione completa `IoNTCellularNodeTwin` (`T258`)** | **`0.7226`** | **`0.5801`** | **`230`** *(`-51.0%`)* | **`0`** |

---

## 3. Verifica delle Tre Ipotesi Sperimentali (con Bootstrap 95% CI Appaiati)

| Ipotesi | Confronto Differenziale (Held-Out) | Guadagno Organismo $G_{\mathrm{org}}$ | Bootstrap 95% CI | Evidenza Meccanistica Aggiuntiva | Esito |
|---|---|---:|---:|---|---|
| **`H1` · Lift Marginale Sincizio Gliale (`T256-01`)** | `T258` vs `FEDERATED_GOSSIP_ONLY` | **`+0.0979` (`+9.79%`)** | **`[+0.0520, +0.1480]`** | Passi in brownout ridotti da `462` a `230` (`84 -> 0` in calibrazione); errore conservazione massa `< 1e-12`; energia drenata dal nodo bizantino = **`0.0`** (giunzione potata per decoerenza) | **`PASS`** |
| **`H2` · Lift Marginale Gossip + SelfHealer (`T256-05`)** | `T258` vs `FEDERATED_GLIAL_ONLY` | **`+0.1032` (`+10.32%`)** | **`[+0.0641, +0.1557]`** | Rilevazione deterministica `ACTIVE -> STALE -> FAILED` del crash silenzioso a metà blackout e cutover consultivo su `node-s` con inoltro epidemico `TTL=2` resistente al packet loss | **`PASS`** |
| **`H3` · Guadagno Sinergico Totale & Sicurezza (`T258`)** | `T258` vs `FEDERATED_SINGULARITY_T238` *(e vs `ISOLATED`)* | **`+0.2313` (`+23.13%`)** *(vs `ISOLATED`: **`+52.49%`**)* | **`[+0.1907, +0.2763]`** *(vs `ISOLATED`: `[+0.4530, +0.5847]`)* | `0` violazioni critiche Layer-0, `100%` riconciliazione hash-chain `DLTSwarmLedger` post-blackout dei `RepairPlan` emessi sul *fast-plane* | **`PASS`** |

---

## 4. Osservazione Chiave: Complementarità Ortogonale tra Omeostasi Gliale e Gossip Epidemico

La scomposizione fattoriale $2 \times 2$ evidenzia una **additività strutturale quasi perfetta** tra i due sottosistemi `T256`:
- Rispetto a `T238` (`0.4711`), il solo sincizio gliale aggiunge **`+0.0547`** assorbendo i picchi energetici asimmetrici sugli attuatori (`node-b`, `node-c`) dai donatori sopra `donor_floor = 0.30` e isolando topologicamente il nodo bizantino `node-a` tramite potatura della giunzione `("node-a", "node-b")`.
- Il solo protocollo gossip + `SwarmSelfHealer` aggiunge **`+0.0572`** mantenendo la fusione sensoriale laterale peer-to-peer durante il blackout del coordinatore centrale e sostituendo il sensore andato a fondo scala (`-2.20`) con `node-s`.
- L'unione dei due meccanismi in `FEDERATED_GLIAL_GOSSIP_T258` produce **`+0.1090`** (`0.4711 -> 0.5801`), confermando che tutti e 6 i moduli estratti in `T256` sono ora **validati sperimentalmente con guadagno differenziale positivo certificato** (`T257` sul piano cognitivo-linguistico live GPU, `T258` sul piano sistemico-federato IoNT).
