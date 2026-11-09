# r13-vista3d: esito della passata di fedeltà

4 e 5 novembre 2026. Ramo `r13-vista3d`, Windows, Qt Quick 3D su Direct3D 11.

## Esito

[V] Portate nella vista Quick le barre, il sole, il cubo, i contorni e i gesti del riferimento Widgets. Corretti anche i difetti emersi nel percorso Rho: terreno a strisce, calendario che ignorava Esc, maniglie non raggiungibili con Vertici attivo, camera che seguiva la prima anteprima di spostamento, Meridio che rimaneva lontano dall'angolo dopo il ridimensionamento.

Non dichiaro identità di ogni pixel o il raggiungimento del limite di 30 ms. Le differenze residue e le misure sono sotto. Il terreno all'orizzonte è una differenza richiesta esplicitamente rispetto al rettangolo finito dei Widgets di questa base.

Confronto apribile sul PC:

```text
C:\Users\Grasso\dev\meridiana-wt-r13-vista3d\docs\quick\confronto\r13-vista3d\index.html
```

L'indice contiene foto intere, ritagli al 200 %, metadati della camera e sei stati della finestra Rho. Le prove e il copione restano nel repository. Nessuna modifica ai Widgets, ai modelli scelti o ai bozzetti di inserimento in attesa di Daniel.

## Cosa è stato portato

| Parte | Risultato e riscontro |
|---|---|
| Barra della vista | [V] Scheda in alto a sinistra, 101 × 33, margini 8; adatta/più/meno con pulsanti 31 × 27 e icone 16. Selettore delle viste presente qui solo in 3D sola. Strumenti collegati ai comandi della finestra, senza i blocchi provvisori. |
| Sole | [V] Riga sotto la scena alta 34, play/giorno/cursore/ora/altezza e azimut/sole. Giorno 86, play e sole 27, spazi 8. Passo dieci minuti, timer 80 ms, giorno di progetto e mezzogiorno solare. Altezza apparente, testo e comportamento confrontati direttamente con `ui/sunbar.py`. Il cambio sito reimposta il sole; una rinomina conserva data e ora scelte. |
| Calendario | [V] 302 × 224 normale, 316 × 224 con testo grande. Mese, anno e giorno funzionanti. Esc chiude il popup prima di cambiare strumento o selezione. Barra verificata anche a 400 px con testo grande: cursore almeno 80 e pulsante Sole visibile. |
| Terreno e luce | [V] Piano di 40 km centrato sul bersaglio della camera, stesso colore e materiale. Riceve le ombre, senza proiettarne una propria. Restano quattro luci, intensità, PCF8, due cascate e materiali del riferimento. Le strisce del terreno sono riprodotte e corrette, senza spegnere le ombre degli edifici. |
| Selezione e hover | [V] Contorni come geometria 3D con profondità: la parte dietro un muro non si vede più. Stessa geometria `mesh.ribbons`, colori per tipo, tratto 1,6 px e alone 2,5. Hover 1,3 px. Il materiale passa attraverso lo stesso tone mapping del riferimento. Il positivo della prova controlla che il contorno davanti resti visibile. |
| Cubo | [V] Stesse trasformazioni e facce, etichette maiuscole, misura 112 o 76 nella vista piccola, margine 6, frecce e menu. Cardinali disegnati prima delle facce, senza sovrapporre le lettere. Nessuna ombra aggiuntiva inventata. |
| Camera | [V] Inquadratura iniziale adattata alla misura della vista. F inquadra il contorno selezionato alla quota usata dai Widgets. Preferenze di navigazione, orbita e pivot collegate alle Impostazioni reali. La prima modifica di un oggetto conserva la camera: non reinquadra ogni anteprima. |
| Gesti e R365 | [V] Orbita, pan, zoom al cursore, touchpad e cubo restano in QML durante il movimento. Vertici, quote, distacco e spigoli aggiornati dal vivo; Sposta con Vertici attivo usa le maniglie prima della selezione a finestra. Commit e Undo restano nella sessione. |
| Menu e tasti | [V] Menu sul punto cliccato, rinomina, duplicazione, eliminazione, sottocampi, righe e layout. Riempi ripristina le esclusioni automatiche e conserva quelle manuali. Esc annulla prima l'anteprima, poi lascia lo strumento, poi risale nella selezione. Inquadra e zoom sincronizzati con la pianta; Agganci sincronizzato nei due sensi. |
| Meridio | [V] L'adattatore della scena indica al componente esistente il rettangolo della vista visibile. In basso a destra anche dopo resize; posizioni salvate dall'utente conservate. Nelle altre fasi torna al rettangolo centrale della shell. |

Fonti lette nel repository: `ui/view3d.py`, `ui/preview3d.py`, `ui/viewbar.py`, `ui/sunbar.py`, `ui/viewcube.py`, `ui/day_picker.py`, `ui/qml/Scene.qml`, gestori di `ui/window.py`, nucleo `camera`, `navigation`, `gizmo`, `mesh` e `viewaids`. Per il passaggio del colore nello shader è stata verificata la documentazione primaria [Qt CustomMaterial](https://doc.qt.io/qt-6/qml-qtquick3d-custommaterial.html).

[V] Il menu destro contiene solo le azioni oggetto dei Widgets: nove voci/separatori per l'edificio, due nel vuoto. Le voci aggiuntive del prototipo sono state tolte. Il riferimento Widgets non espone wireframe/xray o un interruttore delle ombre: la vista resta ombreggiata; quelle proprietà del renderer sono ancora usate dalle prove, senza aggiungere controlli alla barra di riferimento.

## Confronto visivo

[V] Cinque coppie native sulla stessa camera e sullo stesso capannone con moduli: chiaro/scuro, scale 1/2, vista 800 × 600; vista 400 × 600 con testo grande. Ogni coppia comprende normale, selezionata, maniglie e calendario. L'indice mostra al 200 % barra, cubo, sole, contorno, maniglie e calendario.

[V] Nel ritaglio tetto/pareti la differenza media per canale è fra 0,072 e 0,084 su 255; fra 0,27 e 0,36 % dei pixel supera otto livelli di differenza. È una misura locale, non un punteggio di equivalenza dell'intera finestra: esclude il terreno lontano e non misura l'usabilità. Dati in `confronto/r13-vista3d/metrics.json`.

[V] Percorso Rho di 21 passi con eventi Qt reali: apertura, 3D sola, hover e tooltip di Inquadra, selezione, menu destro, orbita, pan, menu del cubo, calendario ed Esc, F, più/meno, resize a 1366 × 900, Impianto e ritorno a Modellazione, resize a 1920 × 1080. La camera del confronto isolato è congelata; quella del percorso completo segue i gesti nelle rispettive finestre.

[V] Per le foto del percorso, l'animazione di Meridio è disabilitata in entrambi i programmi, come già nel pilot Widgets; altrimenti il fotogramma al resize può cogliere una posizione intermedia. La prova d'integrazione usa l'animazione attiva e attende l'arrivo nell'angolo, senza allargare la tolleranza. I log `scene-state` riportano posizione, rettangolo ospite e fase a ogni passo.

[V] Il pilot specifico corregge gli eventi di trascinamento: `MouseMove` ha `button=NoButton` e il pulsante tenuto in `buttons`. Il vecchio copione faceva orbitare i Widgets ma non Quick; la nuova prova nella finestra completa riproduce prima la rotazione immutata, poi verifica orbita e pan effettivi. Nei Widgets il calendario si apre premendo la freccia del campo data; i popup nativi sono acquisiti separatamente e composti, alle loro coordinate reali, nella foto della finestra, perché `QWidget.grab()` da solo non li include.

Differenze residue:

- [V] Orizzonte continuo richiesto: il vecchio terreno termina e lascia vedere il cielo anche dove la camera guarda sotto l'orizzonte. Quick mantiene il terreno in quella zona. Il cielo usa gli stessi colori e resta visibile quando entra nell'inquadratura.
- [V] Piccole differenze di antialiasing fra pittura raster e Quick e di distribuzione delle celle del calendario. Il controllo giorno Quick apre il calendario e consente le frecce su/giù; non riproduce l'editing a sezioni giorno/mese di `QDateEdit`.
- [V] Le altre parti della finestra Rho sono quelle dei rami integrati: il confronto completo mostra anche differenze nelle Verifiche e nelle proprietà. Non sono nascoste o attribuite al renderer 3D.
- Non sono stati osservati il puntatore fisico o i tempi di presentazione sul monitor di Daniel: finestre native sul desktop separato, eventi Qt e lettura dei frame. Non eseguiti controlli manuali su Linux o altri driver grafici.

## Modelli e fluidità

[V] Stesse 528 istanze: 200 auto, 200 persone e 128 moduli. Due geometrie condivise e due gruppi per i modelli, qualità originale, ombre attive. Nessun modello sostituito, nessuna riduzione di dettaglio. Nessuna chiamata Python durante l'orbita e nessun avviso QML nei rapporti.

| Misura finale | Scala 1 | Scala 2 |
|---|---:|---:|
| Pixel, finestra logica 1600 × 960 | 1600 × 960 | 3200 × 1920 |
| Frame misurati dopo riscaldamento | 245 | 241 |
| Mediana | 33,31 ms | 49,92 ms |
| Percentile 95 | 35,46 ms | 51,94 ms |
| Massimo | 51,36 ms | 67,65 ms |
| Frame oltre 30 ms | 234 | 241 |

[V] Il limite di 30 ms per ogni frame non passa. Le prime misure erano 31,0/33,4 ms di mediana; le ripetizioni finali sono nella tabella. La macchina era condivisa con altro lavoro: non attribuisco la variazione al singolo cambiamento del terreno. Non c'è una misura controllata sufficiente per dichiarare assenza di regressione rispetto ai Widgets. R389 resta aperta; la prova mantiene la soglia originale come fallimento atteso, senza presentarla come una prova di fluidità superata.

Rapporti completi, inclusi tutti i frame e il tempo di caricamento: `confronto/r13-vista3d/verifiche/timing-scale-1.json` e `timing-scale-2.json`.

## Verifiche riproducibili

Comandi eseguiti con Python della venv di Meridiana, `PYTHONPATH=tests;src`, cache QML e shader disabilitate per le prove native. Rapporti testuali in `confronto/r13-vista3d/verifiche/`.

| Verifica | Esito |
|---|---|
| Vista3d completa offscreen | [V] 102 eseguite, nessun fallimento, 18 saltate perché native o dipendenti dai rapporti di tempo. |
| Sistema Quick | [V] 46 passate. |
| Pixel e gesti D3D11 | [V] Le 15 prove della scena passano. Il log della sessione da 20 prove include anche il fallimento sull'attesa fissa dell'animazione di Meridio, poi corretto nel solo test. |
| Finestra completa D3D11, dopo la correzione dell'attesa | [V] Tutte le cinque prove passate; successivi controlli di resize/ritorno da Impianto e di orbita/pan con eventi reali passati. |
| Fedeltà dati e menu | [V] Sette prove passate, incluso ripristino delle esclusioni automatiche e Undo. |
| Formati | [V] 96 passate. |
| Compatibilità `parity` | [V] 70 eseguite: un fallimento, sette saltate e due fallimenti attesi. Fallisce l'inventario CSV condiviso: 132 segnalazioni di dati non aggiornati rispetto a richieste e prove correnti. Elenco completo in `parity-inventory.json`; nessuna soglia allentata e nessun CSV fuori ambito riscritto. |
| Prestazioni | [V] Integrità del carico e assenza di callback Python passate; limite di 30 ms fallito come atteso. |
| Lint e diff | [V] File propri e `git diff --check` passati. Lint globale: un B905 in `tests/quick/pianta/test_fidelity.py:30`, fuori ambito. |

```powershell
# Suite senza richiedere un dispositivo 3D.
$env:QT_QPA_PLATFORM='offscreen'
python -m unittest discover -s tests/quick/vista3d -t tests
python -m unittest discover -s tests/quick/sistema -t tests
python -m unittest discover -s tests/quick/parity -t tests

# Pixel e gesti reali D3D11.
$env:QT_QPA_PLATFORM='windows'
$env:MERIDIANA_QUICK_3D_NATIVE='1'
python -m unittest quick.vista3d.test_fidelity_native quick.vista3d.test_native quick.vista3d.test_integration

# Le due implementazioni, stessi 21 gesti.
python -m quick.vista3d.pilot_scene tests/quick/percorsi/vista3d.json --engine both --project docs/quick/compat/fixtures/rho.meridiana --out build/quick-foto/r13-vista3d/pilot-final-light-1

# Foto a camera congelata: eseguire widgets prima di quick, per ciascuna scala/tema.
python -m quick.vista3d.capture_fidelity --engine widgets --out build/quick-foto/r13-vista3d/detail-light-1
python -m quick.vista3d.capture_fidelity --engine quick --out build/quick-foto/r13-vista3d/detail-light-1
python -m quick.vista3d.compare_fidelity
```

[V] La prima suite integrata segnalava `flatMap` nel menu Oggetto 3D della shell; risolta dall'aggiornamento integrato con `a553bb3a`. Lo slider produceva anche avvisi propri di personalizzazione dello stile Windows: ora usa esplicitamente Basic. I log precedenti conservano queste evidenze.

[V] La prima esecuzione Widgets del copione produsse tutte le foto ma rimase nella pulizia finale. Il pilot condiviso aggiornato abbandona il calcolo automatico prima di pulire. Non è stata modificata la chiusura del programma Widgets.

[V] Una ripetizione Quick si è interrotta al passo Esc per `ChecksPage.qml:200: Cannot create delegate / Object or context destroyed during incubation`. La successiva esecuzione dei 21 passi è terminata senza avvisi. I due log sono conservati; il problema delle Verifiche è segnalato al relativo ramo nello stato, senza modificare i suoi file o filtrare gli avvisi del pilot.

Le modifiche proprie sono limitate a `scene*.py`, `qml/Meridiana/View3D`, prove vista3d, relativo copione e documenti di questa passata. Nessun push o rilascio.
