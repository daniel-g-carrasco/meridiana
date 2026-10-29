# Ombre, stringatura e dimensionamento: audit del 29 ottobre 2026

Ambito R215 e R225-R229, sul seguito di `af17add`. Il modello geometrico est-ovest R216 e le pensiline R217 sono lavorazioni separate. Questo rapporto distingue correzioni dimostrate, verifiche numeriche e limiti ancora aperti; non certifica il progetto né una simulazione elettrica dettagliata.

## Correzioni implementate

| Caso riproducibile | Prima | Ora e prova |
|---|---|---|
| Completamento intorno a stringhe già disegnate | Conservava la lunghezza, perdeva modello e orientamento del gruppo esistente | Lo stesso MPPT si completa solo con la stessa firma modulo, inclinazione, azimut e lunghezza; `CompletingCompatibility` |
| Due falde SolarEdge da 6 moduli, orientamenti diversi | Il propositore le univa per raggiungere il minimo | Restano 12 moduli da collegare; due gruppi omogenei da 6 possono invece formare una stringa valida da 12 |
| Stringa manuale SolarEdge su più orientamenti | Nessun avviso specifico | Avviso globale consultabile; coppia dello stesso ottimizzatore con orientamenti/tipi diversi fallisce. Ottimizzatori distinti nella stessa stringa possono avere orientamenti diversi secondo il costruttore |
| Modulo fuori limite dopo il primo tipo di una stringa ottimizzata | Veniva controllato soltanto il primo tipo | Ogni tipo e numerosità effettiva dell'ottimizzatore viene controllato; il secondo tipo da 25 A Isc fallisce |
| Inverter SolarEdge diversi nella stessa proposta | Regole del primo modello applicate anche alla destinazione successiva | Destinazioni con architettura/regole diverse non condividono quella proposta; non vengono create stringhe da 10 ottimizzatori dove ne servono almeno 14 |
| Due moduli da 60 V Voc su P800p, Tmin -10 °C, coefficiente -0,25%/°C | Somma serie 130,5 V contro limite 83 V | Due ingressi paralleli dedicati: 65,25 V per ingresso, 6,5 A per ingresso contro 7 A, 720 W complessivi contro 800 W |
| Corrente totale inverter e limiti MPPT | Il totale poteva essere replicato su ogni MPPT; OND lo divideva in parti uguali | Il totale resta comune; nessuna ripartizione ricavata. OND reale Chint: 360 A totali, 12 MPPT, 36 ingressi fisici, limite per MPPT non disponibile |
| Dimensionamento con due stringhe da 13,4 A, limiti MPPT 20 A e totale 25 A | Dichiarava valida la combinazione | Rifiuta 26,8 A complessivi; i dati per MPPT mancanti generano avvisi e impediscono un dimensionamento dichiarato verificato |
| Connettori fisici | `strings_per_mppt` del catalogo ignorato; `NbInputs` OND usato come MPPT | Proposta limitata ai connettori dichiarati, avviso manuale quando occorre un parallelo esterno; `NbInputs` non sostituisce `NbMPPT` |
| Numero di inverter imposto dalla topologia | Ricerca troncata dal rapporto di potenza, anche quando servivano altri MPPT/connettori | Due gruppi da 20 moduli con orientamenti diversi trovano 2 inverter mono-MPPT; 96 moduli con un solo connettore per inverter trovano 4 inverter e 4 stringhe da 24 |
| Stringa manuale con moduli diversi | Potenza calcolata dal primo modulo | Somma reale: caso 8.400 W prima riportato come 7.200 W; avviso sul mix di tipi |

File modificati: `energy/plant.py`, `energy/stringing.py`, `energy/components.py`, `energy/optimizers.py`, `energy/sizing.py`, `catalog/panond.py`. I nuovi avvisi passano da `checks.plant_items()` senza cambiare `checks.py`. In `ui/pedigree.py` è modificata soltanto `limits()`: le limitazioni sono leggibili in «Come è calcolato» e nella relazione.

La firma geometrica usa la precisione di layout di 0,1°, normalizza l'azimut circolare e ignora l'azimut dei moduli orizzontali. È una regola del programma, non una tolleranza normativa. L'abbinamento dei due moduli di un ottimizzatore segue ancora l'ordine della stringa salvata.

## Ombre: cosa calcola il motore

`nearshade.py` proietta e unisce le ombre geometriche, conserva frazioni di area e blocchi interessati per modulo e interpola su griglia solare di 5° in azimut e 4° in elevazione. La disposizione dei blocchi deriva dal file modulo quando presente, altrimenti da ipotesi sul numero di diodi e celle. Le ombre tra file hanno un modello dedicato, con ipotesi di file e stringhe omogenee.

L'effetto elettrico usa la stima Martinez-Moreno. Un'ombra modifica la corrente comune della serie e il comportamento dei bypass: non spegne una sequenza di pannelli «a valle». Il motore non risolve le curve I/V di celle, diodi, stringhe parallele e MPPT. L'interpolazione dei blocchi toccati e l'approssimazione delle file non equivalgono a quel calcolo. La fonte primaria PVsyst distingue esplicitamente il calcolo dettagliato delle [curve I/V di modulo e stringa](https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-layout/index.html).

Prova quantitativa aggiunta: 10 moduli, 1/6 di un modulo ombreggiato, 3 blocchi interessati su 30, radiazione diretta 800 W/m² su globale 1.000 W/m². La perdita totale è 8,946236559% e coincide a 12 decimali con `pvlib.shading.direct_martinez`; invertire l'ordine della stringa non cambia il risultato. A parità di area, un solo blocco interessato riduce a un terzo la componente elettrica aggiuntiva. Fonte: [pvlib, direct_martinez, equazioni 6 e 8 del lavoro Martinez-Moreno, Muñoz e Lorenzo 2010](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.shading.direct_martinez.html). È un confronto tra implementazioni in un caso controllato, non una validazione annuale su misure né una prova di limite superiore universale.

Per gli ottimizzatori il motore considera la minore aggregazione delle perdite da ombra, l'efficienza fissa di conversione e i limiti continui della stringa. Non simula ora per ora clipping della corrente d'ingresso, tensioni d'uscita dei singoli ottimizzatori o numero minimo illuminato. Non rappresenta gli altri sistemi Huawei/Tigo/Sungrow né le varianti con cavi di derivazione opzionali sui modelli normalmente in serie. I doppi ingressi dedicati P485/P800p/P860/P960 sono riconosciuti; il caso numerico coperto qui è P800p. Non si dichiara verificata ogni combinazione commerciale.

## Fonti consultate e loro portata

La ricerca è partita da `docs/studio/06-pvsyst-aurora-pvlib.md`, `docs/studio/10-pvsyst-formati-file.md`, `docs/compiti/22-ottimizzatori.md`, `C:\Users\Grasso\Elettrico\output\programma-fv` e dall'archivio `C:\Users\Grasso\Elettrico\reference\catalogs\SolarEdge`. Le ricerche precedenti sono contesto; le regole applicate sono confrontate con le fonti primarie seguenti.

- `C:\Users\Grasso\Elettrico\reference\standards\cei\CEI 64-8_7 - 9 ed. - 2024-07.pdf`: letti integralmente art. 712.431.101-102, p. 95, 712.433.101-102, p. 97, Allegato B.1-B.2, p. 109. Le formule esistenti KU/KI e delle protezioni corrispondono ai passaggi consultati; nessuna soglia normativa nuova introdotta. La nota sull'assenza di correnti inverse tra MPPT impone una condizione del costruttore che il modello non descrive: le verifiche di parallelo per MPPT non costituiscono verifica completa dell'isolamento tra ingressi o dei cavi reali.
- SolarEdge, `optimizers\SolarEdge - Ottimizzatore S1000-S1200 commerciale - DS-000105-IT - 2025-12-01 IT.pdf`, p. 3, e `optimizers\SolarEdge - Power Optimizer P800p-P850-P950-P1100 - DS-000012-ENG - 2022-12-29 EN.pdf`, p. 3: tabelle di stringa e topologia del doppio ingresso P800p, con corrente limite per ingresso.
- SolarEdge, `application-notes\SolarEdge - Application note power optimizer compatibility with PV modules - v1.0 - 2025-01 EN.pdf`, pp. 1-3: compatibilità elettrica ingresso; `application-notes\SolarEdge - Application note single string design EU and RoW - v1.1 - 2026-08 EN.pdf`, p. 3 del PDF: criticità di rendimento per singola stringa su più falde. Non è un divieto generale di mescolare falde su ottimizzatori distinti.
- [SolarEdge, Connecting Power Optimizers to Multiple PV Modules, v1.7 novembre 2025](https://knowledge-center.solaredge.com/sites/kc/files/application-note-connecting-solaredge-power-optimizers-to-multiple-pv-modules.pdf), pp. 1-2 e 5: stesso tipo/orientamento/inclinazione sul medesimo ottimizzatore; differenze ammesse su ottimizzatori distinti; distinguere serie, doppio ingresso parallelo e derivazioni opzionali. Consultato online dopo la ricerca locale. Tentativi di archiviarlo con urllib/requests e User-Agent browser sui domini ufficiali respinti con HTTP 403: non risulta scaricato da questa attività.
- [Huawei SUN2000-12/15/17/20/25K-MB0, 01-202504](https://solar.huawei.com/admin/asset/v1/pro/view/c3ba89c365cb42ce92d9ba3c366253f1.pdf), p. 2: 2 MPPT, 4 ingressi, corrente 30 A con due stringhe e 20 A con una. Archiviato nuovo PDF in `C:\Users\Grasso\Elettrico\reference\catalogs\Huawei\inverters\Huawei - SUN2000-12-25K-MB0 - 01-202504 EN.pdf`. Il catalogo ha già `[2, 2]` connettori e `[30, 30]` A, ma la condizione 20/30 A è solo nelle note: non è ancora un limite strutturato. Il valore 40 A Isc del prospetto richiede conferma esplicita della portata prima di nuovi automatismi.

## Dati esposti e schema ancora necessario

API aggiunte a `InverterSpec`, senza cambiare il formato di progetto:

- `imax_total: float | None`, da `dc_current_max_a`, limite comune dell'inverter;
- `inputs_per_mppt: list | None`, da `strings_per_mppt`, coppie fisiche per tracker;
- `imax_per_mppt` e `iscmax_per_mppt` rimangono indipendenti; il totale può fungere da limite individuale soltanto quando è dichiarato un solo MPPT;
- OND conserva `dc_input_pairs` come conteggio fisico totale, senza dedurne una mappa. Se manca `NbMPPT`, resta mancante.

Per chiudere la mappa fisica serve un catalogo esplicito, proposto e non ancora implementato:

```text
trackers: [{id, voltage_min_v, voltage_max_v, operating_current_max_a,
            short_circuit_current_max_a,
            connection_modes: [{active_strings, operating_current_max_a}]}]
connectors: [{id, tracker_id, operating_current_max_a, short_circuit_current_max_a}]
shared_limits: [{members, kind, limit, source}]
reverse_current_isolation: {between_trackers, source}
```

Ogni limite deve avere fonte e unità; assenza significa dato mancante, non valore inventato. L'adattatore dei cataloghi attuali può ricostruire il numero di connettori per tracker, ma non le etichette reali del costruttore o limiti condizionati. Occorrono aggiornamenti a catalogo/importatori, `components`, verifiche/propositore, informazioni UI e test quantitativi. Per salvare quale connettore fisico è usato e le coppie esplicite di ottimizzatori occorre inoltre estendere il modello progetto con il suo proprietario; non è stato modificato `model.py` in questo ambito.

## Limiti aperti del dimensionamento

Il dimensionamento cerca prima meno inverter, poi meno modelli e infine il rapporto DC/AC più vicino: non ottimizza energia, costo o NPV. Il vecchio massimo derivato dalla potenza è rimosso. Per inverter ordinari il minimo esplorato considera sia il numero di firme modulo/orientamento per tracker, sia una capacità ottimistica per inverter calcolata da serie ammissibili e correnti/connettori. Il massimo deriva dal numero di moduli diviso la minima lunghezza ammissibile di stringa: ogni inverter attivo richiede almeno una stringa. Per architetture a tensione fissa si mantiene il massimo conservativo di un inverter per modulo.

Il budget è di 2.048 combinazioni per l'intera chiamata, non per numero di inverter. Una categoria viene ordinata interamente prima di valutarla; se non entra nel budget, il risultato è esplicitamente «ricerca incompleta». Non si restituisce come migliore una porzione arbitraria della categoria. `Result.search_complete` è falso per budget o cancellazione; `choose(..., cancelled=callable)` verifica la cancellazione tra categorie e combinazioni. Il chiamante UI usa ora `ui/sizing_job.py`: la ricerca lavora fuori dal thread grafico su una copia del progetto, con avanzamento indeterminato e comando Annulla. Il callback verifica il flag di interruzione; la consegna UI controlla l'identità del job e lo stato del progetto prima di applicare una proposta.

Il propositore resta euristico e non dimostra l'inesistenza di una soluzione quando lascia moduli fuori: la risposta negativa ora lo dice. In particolare il controllo rifiuta una disposizione che eccede il totale comune, ma il posizionatore non redistribuisce globalmente le stringhe per correggere quel totale; il caso 26,8 A contro 25 A è correttamente rifiutato, non risolto automaticamente. La proposta ottimizzata non effettua una ricerca globale tra famiglie SolarEdge eterogenee. Questi limiti richiedono un algoritmo di assegnazione ulteriore, non ripartizioni dei dati mancanti.

Il calcolo AC annuale aggrega gli inverter collegati e la loro potenza nominale: non calcola separatamente curve, clipping e accensione per ciascun inverter/MPPT. La stringatura corretta migliora le verifiche e la stima delle ombre, ma non rimuove questo limite di produzione.

## Validazione eseguita

174 test mirati finali passati in 10,600 s: `calcoli.test_stringing`, `test_optimizers`, `test_nearshade`, `test_connected_production`, `test_pipeline`, `test_sizing`; `nucleo.test_checks`, `test_pvsyst`, `test_panond`. I 13 test di dimensionamento includono orientamenti, connettori, limite comune, budget e cancellazione. Ruff passa sui file modificati dell'ambito e sui test; `git diff --check` non riporta errori. Le regressioni OND, limite comune e numero di inverter sono state eseguite prima delle correzioni e fallivano come previsto. Nessuna suite generale, pacchetto, commit o validazione su misure di campo in questo intervento.

### Correzione successiva di integrazione: primo import concorrente

La suite finestra ha evidenziato un ciclo di import tra il thread meteo (`pvlib.iotools`) e il dimensionamento (`pvlib.pvsystem`): entrambi fallivano cercando `singlediode` nel modulo ancora parzialmente inizializzato. Il nuovo `calcoli.test_lazy_pvlib` riproduce il problema in un subprocess pulito, sincronizzando i loader dei due thread e senza rete; falliva prima della correzione con lo stesso errore del log.

`energy/dependencies.py` fornisce ora `load_pvlib()`, che completa l'import del pacchetto radice sotto un lock prima dell'accesso ai sottopacchetti. I punti di uso in `components`, `stringing`, `meteo` e `simulate` rimangono differiti; nessuna libreria pesante viene caricata dall'import della finestra. Passano 25 prove race/meteo/dimensionamento in 3,157 s e 10 prove startup/race/pipeline in 4,503 s, con Ruff e controllo diff regolari. Il confine di gestione errori dei job Qt è una correzione separata del proprietario UI.
