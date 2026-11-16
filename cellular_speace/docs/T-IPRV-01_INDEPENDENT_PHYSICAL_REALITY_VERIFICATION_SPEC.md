# T-IPRV-01 — Independent Physical Reality Verification (simulata)

> Stato: SPEC / non implementato · Priorità: P1 · Modalità: agentic (simulazione)
> Origine: `docs/T210_DIFFERENTIAL_REQUIREMENTS_SPEC.md` R11; T210 §2B, §7 AC7
> Principio: il sistema cognitivo non è l'unica fonte di verità sul proprio
> stato e sull'ambiente.

## 1. Motivazione

Oggi ogni elemento del chain — sensori (`CyberPhysicalSensorArray`), drive,
policy engine, actuator, audit — vive nello stesso processo Python con le
stesse credenziali. Un compromesso del processo compromette l'intera
catena di osservazione e controllo. T210 §2B propone verificatori fisici
indipendenti (nanodroni) come attestazione out-of-band dello stato reale,
con il swarm stesso trattato come potenzialmente compromesso e l'attestazione
che attesta lo stato fisico, **mai la verità semantica** di un'asserzione.

Questa spec generalizza il concetto senza dipendere dai nanodroni e la rende
eseguibile **prima** in simulazione, come previsto dal percorso T217.

## 2. Obiettivo

Un verificatore indipendente (processo separato) che stima lo stato dell'
ambiente e lo confronta con lo stato dichiarato dal world model di SPEACE,
producendo un indice di discrepanza consumato dalla governance deterministica.

## 3. Design

```
SPEACE (processo A)                    Verificatore (processo B)
world model → ŝ_AI_t                   sensori propri (simulati) → s_ind_t
        └──────────── canale controllato ────────────┘
                          ↓
        Governance deterministica: Δ_t = d(ŝ_AI_t, s_ind_t)
        Δ < τ0 → coerente · τ0 ≤ Δ < τ1 → richiedi verifica
        Δ ≥ τ1 → blocca/escalation
```

- **Indipendenza strutturale**: processo separato, sensori sintetici propri
  (con drift, rumore, calibrazione imperfetta), radice di fiducia separata,
  canale di comunicazione con firma e timestamp — non variabili condivise
  in-process.
- **Incertezza**: `d` pesa errore di misura, deriva di calibrazione e offset
  di sincronizzazione; non ogni differenza è compromissione.
- **Ruolo del verificatore**: la sua attestazione è **un input alla
  governance**, non un'autorità. Può bloccare o degradare fiducia; non può
  estendere poteri, approvare azioni, né modificare `A_safe`.
- Il verificatore conferma una temperatura o una posizione; **non dimostra**
  che una decisione sia corretta o sicura (no truth oracle — T210 BCEL:
  attestation ≠ semantic truth).

## 4. Simulazione (perimetro di questa spec)

- Ambiente sintetico con stato vero `s_true_t` noto solo al simulatore.
- Guasti iniettabili nel verificatore stesso (sensori off-line, spoofing
  simulato, delay) per misurare come la governance pesa una fonte anch'essa
  fallibile.
- Attacchi simulati al processo cognitivo (world model alterato) per misurare
  il tasso di rilevamento di Δ_t.

## 5. Criteri di accettazione

1. Processi separati effettivi (nessuna variabile condivisa): verificato dal
   test harness.
2. World model alterato → Δ_t supera τ1 con tasso di rilevamento misurato e
   preregistrato; false positive su drift naturale misurati e sotto la
   soglia dichiarata.
3. Guasto del verificatore → la governance non perde consistenza: l'attestazione
   assente degrada la fiducia, non la estende.
4. Nessun percorso dal verificatore agli attuatori.
5. Report con tasso di rilevamento, false positive e latenze.

## 6. Confine hardware

L'estensione a verificatori fisici reali (droni, sensori out-of-band) è fuori
dal perimetro di questa spec e segue T217 (documentazione → simulazione →
replica isolata → prototipo confinato → revisione indipendente). La maturità
di swarm di nanodroni (autonomia, larghezza di banda, resilienza, costo,
sicurezza) resta da verificare come indicato in T210 §4.

## 7. Task checklist

- [ ] T-IPRV-01.1 — spec review + preregistrazione soglie τ0/τ1 e tassi attesi
- [ ] T-IPRV-01.2 — ambiente sintetico con stato vero nascosto
- [ ] T-IPRV-01.3 — verificatore in processo separato + canale firmato
- [ ] T-IPRV-01.4 — governance consumer di Δ_t (blocca/richiede verifica)
- [ ] T-IPRV-01.5 — iniezione guasti (verificatore e world model)
- [ ] T-IPRV-01.6 — report tassi + revisione indipendente prima di ogni
      promozione oltre la simulazione
