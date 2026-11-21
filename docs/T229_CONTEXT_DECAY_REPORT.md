# T229 — Quando il contesto aiuta a scegliere il decadimento della plasticità

**La scelta basata sui sette episodi più simili riduce del 19,9% l'errore medio di tracking rispetto al miglior coefficiente globale e del 22,0% rispetto allo stesso selettore con contesti rimescolati.** Sono risultati su 80 episodi sintetici nuovi. Entrambi i contrasti superano il criterio preregistrato. C cambia la scelta globale in 39 episodi, migliora in 34 e peggiora in 5.

## Dallo sviluppo alla decisione

Il banco usa il vero `SpikingBrainCortex.tick` con il backend sintetico di T228. A ogni tick il backend aggiorna `SpikePlasticity`. I coefficienti normalizzati pesano la belief in `apply_to_ilf`, che ricalcola `q_star`. Tutti i cinque valori di `decay` hanno ottenuto VALIDA dal verificatore T228 per l'EMA reale sul dominio unitario. Anche i valori generati dal sensore restano in quel dominio. I gate del cortex hanno approvato tutti i tick registrati.

Ho costruito due regimi equiprobabili per rendere osservabile il compromesso. In uno il rumore del sensore è uniforme entro ±0,02 e il segnale latente si sposta di 0,30–0,45. Nell'altro il rumore arriva a ±0,40 e lo spostamento è 0,005–0,025. Il segno è casuale. La durata del pulse è uniforme fra 12 e 24 tick, estratta da un flusso distinto. Il riferimento è l'uscita stazionaria del consumer ILF per il **segnale latente**. Una risposta rapida può seguire meglio il cambiamento oppure inseguire il rumore, a seconda del regime.

Si osservano otto tick a `decay=0,9`. L'unica caratteristica disponibile al selettore è la deviazione standard delle otto letture, divisa per 0,25. Al tick 9 ogni braccio parte da una copia profonda dello stesso cortex, inclusi EMA, ILF, memoria e gate. Tutti scelgono prima di eseguire qualunque tick successivo. La scelta resta fissa per i 40 tick residui. I selettori B, C e D consultano rispettivamente l'intero archivio, i sette vicini e i sette vicini dopo la permutazione dei contesti. D conserva intatta ogni riga delle cinque perdite. La specifica fissa distanza, pareggi, metrica e analisi. [Specifica preregistrata](T229_CONTEXT_DECAY_SPEC.md)

Sullo **sviluppo**, ciascuna cella riporta la media delle perdite cumulative dello stesso gruppo per il coefficiente indicato. Lo spartiacque di 0,08 si applica alla deviazione standard prima della normalizzazione. Serve a controllare il valore della scelta prima della valutazione. Il selettore C usa la distanza continua.

| Variabilità osservata | Episodi | 0,75 | 0,80 | 0,90 | 0,975 | 0,995 |
|---|---:|---:|---:|---:|---:|---:|
| Bassa | 40 | **0,38059** | 0,45050 | 0,68146 | 0,83359 | 0,75818 |
| Alta | 24 | 0,35488 | 0,32555 | 0,25766 | **0,22892** | 0,24775 |
| Tutte | 64 | **0,37095** | 0,40364 | 0,52254 | 0,60684 | 0,56677 |

Il vincitore globale costa 0,04724 in più per episodio rispetto ai due vincitori di gruppo ponderati per numerosità. Il controllo ha quindi aperto la valutazione. L'archivio raccoglie **320 rollout** da snapshot accoppiati e 13.312 tick del cortex, prefissi inclusi. La costruzione e scrittura dei dati di sviluppo ha richiesto 1,205 s su questa macchina. [Tabella di sviluppo](../artifacts/T229_context_decay_20261121/development_gate.json) · [Perdite per episodio e coefficiente](../artifacts/T229_context_decay_20261121/development.json)

## Esito sugli episodi nuovi

La perdita primaria somma le distanze TV lungo tutti i 48 tick. Le tre colonne temporali sono contributi additivi. Il recupero richiede tre tick consecutivi con TV ≤ 0,01 dopo il rientro. Il tempo di recupero include i fallimenti al numero di tick disponibili più uno. Le otto repliche di D sono mediate entro episodio.

| Scelta | Prefisso | Perturbazione | Rientro | L totale | Recuperati | Tick di recupero | Consultazione media |
|---|---:|---:|---:|---:|---:|---:|---:|
| A · riferimento 0,9 | 0,01673 | 0,24683 | 0,22679 | 0,49035 | 91,25% | 10,01 | 2,3 µs |
| B · globale | 0,01673 | 0,18601 | 0,18255 | 0,38529 | 98,75% | 7,58 | 48,1 µs |
| C · contestuale | 0,01673 | 0,16261 | 0,12939 | **0,30873** | 97,50% | 6,61 | 33,4 µs |
| D · rimescolata | 0,01673 | 0,19839 | 0,18067 | 0,39580 | 98,75% | 7,48 | 21,6 µs |

Il guadagno medio di C su B è di 0,02341 durante la perturbazione e 0,05315 al rientro. C raggiunge la banda in 78 episodi contro i 79 di B. La misura di consultazione include la costruzione della traccia decisionale, che per B contiene l'intero archivio. L'ordine di esecuzione è fisso e i tempi dipendono dalla macchina.

| Famiglia | Episodi | L di A / B / C / D | B − C [IC 95%] | D − C [IC 95%] |
|---|---:|---|---|---|
| Rettangolare | 40 | 0,5530 / 0,3985 / 0,3254 / 0,4181 | 0,0732 [0,0358–0,1132] | 0,0927 [0,0557–0,1316] |
| Triangolare | 40 | 0,4277 / 0,3720 / 0,2921 / 0,3735 | 0,0799 [0,0463–0,1153] | 0,0814 [0,0483–0,1159] |
| **Tutte** | **80** | **0,4903 / 0,3853 / 0,3087 / 0,3958** | **0,0766 [0,0497–0,1035]** | **0,0871 [0,0614–0,1133]** |

IC percentili marginali da 4.000 bootstrap appaiati di episodi, stratificati per forma. Includono tutte le scelte identiche. L'incertezza è condizionata all'archivio congelato e alle otto permutazioni fissate.

| Confronto con C | Scelta diversa | Migliora | Peggiora | Perdita pari fra scelte diverse | Stessa scelta |
|---|---:|---:|---:|---:|---:|
| B, su 80 episodi | 39 (48,75%) | 34 | 5 | 0 | 41 |
| D, su 640 confronti abbinati | 328 (51,25%) | 288 | 40 | 0 | 312 |

Con D ciascun episodio pesa 1/80 e le sue permutazioni pesano 1/8. I 328 cambiamenti corrispondono a 41 episodi equivalenti, di cui 36 migliori e 5 peggiori. [Statistiche complete per braccio e famiglia](../artifacts/T229_context_decay_20261121/evaluation/summary.json)

## Due decisioni verificabili

**Episodio 1, triangolare.** Le letture del prefisso sono 0,442, 0,134, 0,795, 0,545, 0,459, 0,364, 0,756 e 0,557. Il contesto vale 0,79327. C recupera le righe 8, 16, 14, 60, 38, 28 e 57 a distanze 0,00986, 0,01334, 0,05092, 0,06095, 0,06815, 0,08705 e 0,09055. Le loro perdite medie in ordine di griglia sono 0,31049, 0,28318, 0,22506, **0,18521** e 0,19012. C applica 0,975. B applica 0,75. A parità di distanze, la prima permutazione di D recupera invece le righe 58, 7, 53, 9, 44, 35 e 43, la cui media favorisce 0,75.

Al tick 9 la seconda componente EMA vale 0,51417 con C e 0,52534 con B. La prima componente di `q_star` è rispettivamente 0,84003 e 0,84084, contro un riferimento di 0,83894. Sulla traiettoria intera C riduce L da **0,26644 a 0,09154**. I record completi si trovano alle chiavi `1/0.975` e `1/0.75`.

**Episodio 21, triangolare, peggioramento.** Con contesto 0,80118, C recupera le stesse sette righe e applica ancora 0,975. Durante la perturbazione riduce la perdita da 0,21816 a 0,19036. Al rientro la aumenta da 0,09076 a 0,15392. Con lo stesso prefisso, L passa da **0,35145 a 0,38681**. Le chiavi sono `21/0.975` e `21/0.75`. Questo caso mostra il rischio individuale di scegliere dalla media dei vicini. [Decisioni e perdite archiviate](../artifacts/T229_context_decay_20261121/evaluation/episodes.jsonl) · [Traiettorie complete in JSONL compresso](../artifacts/T229_context_decay_20261121/evaluation/trajectories.jsonl.gz)

## Portata e riproduzione

Il risultato riguarda l'associazione fra variabilità iniziale ed esiti della griglia certificata su questo generatore. La scelta modifica il coefficiente effettivamente usato dal tick e riduce l'errore medio anche rispetto alla memoria rimescolata. La relazione tra rumore, ampiezza e futuro è una scelta di progetto. Entrambe le forme di perturbazione compaiono nello sviluppo. Il trasferimento a sensori reali, a un archivio diverso o a dinamiche in cui questo indizio perde valore resta da misurare. Il banco opera in simulazione nel perimetro T208/T217.

Eseguire dalla radice del checkout in PowerShell con una nuova directory di destinazione. La prima invocazione stampa la tabella di sviluppo e congela i file. La seconda controlla i digest e lo stato del criterio di apertura.

```powershell
.venv/Scripts/python.exe -m q_speace.experiments.context_decay develop --output artifacts/T229_riproduzione
.venv/Scripts/python.exe -m q_speace.experiments.context_decay evaluate --output artifacts/T229_riproduzione
```

Il run consegnato usa Python 3.12.10 e NumPy 2.4.4. Gli SHA-256 sono calcolati sui byte dei file. Configurazione `dfde60937d0afeab99677e90bc4cc6baf905f9be543e7eb0b02f0946f9ee22c3`, archivio `d638f07c49a367dcc227c2404ace1637a0f1335d6ba3803cfbdaecc348b77c08`. Il manifest include hash di spec e codice e l'apertura registra il digest del manifest. Le 880 decisioni puntano a 216 traiettorie distinte. A parità di episodio e coefficiente, il runner confronta ogni tick rieseguito prima di riusare il record su disco. [Configurazione](../artifacts/T229_context_decay_20261121/config.json) · [Archivio](../artifacts/T229_context_decay_20261121/archive.json) · [Manifest congelato](../artifacts/T229_context_decay_20261121/freeze.json)

Una replica locale da due nuovi processi ha riprodotto configurazione, archivio e tutte le 216 traiettorie decompresse byte per byte. Per gli 80 episodi e le 880 decisioni coincidono tutti i campi escluso il tempo di consultazione. [Confronti della replica e SHA-256](../artifacts/T229_context_decay_20261121/reproducibility.json)

Suite completa con 655 test superati e 3 saltati, inclusi 11 nuovi test su scelta, copie dello stato, separazione degli ingressi, permutazioni, tempi della decisione, analisi e integrità dell'archivio. Py_compile, Black, Ruff e mypy passano sui nove file Python toccati. Il Ruff globale segnala le due anomalie già documentate in T228, F401 in `cli.py` e B009 in `orchestrator.py`. [Log pytest](../artifacts/T229_context_decay_20261121/pytest_full.txt)
