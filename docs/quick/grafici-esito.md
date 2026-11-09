# Grafici e risultati in Qt Quick: esito

04/11/2026, ramo `r12-grafici`. Tema e controlli uniti da `r12-sistema`, commit
`82051f4`. Censimento iniziale: [stato/grafici.md](stato/grafici.md).

## Consegnato

[V] Portate tutte le forme censite di `ui/charts.py` e `charts_pg.py`: barre
singole/affiancate/impilate, perdite divergenti, mappe giorno tipo e annuali,
linee settimanali e orarie, cassa, confronti di dimensionamento e flussi economici.
`pyqtgraph` e Qt Widgets non sono importati dai nuovi moduli di produzione.
Il nucleo e `src/meridiana/ui/` non sono modificati.

[V] Quattro contenuti centrali: Produzione, Consumi, Economia e Accumulo. Tessere
con massimo cinque colonne e altezze uniformi, schede, testi, fonti, limiti del
modello, formule e «Come è calcolato». Accumulo oggi non ha un proprio grafico:
il riepilogo e la compatibilità sono in quella pagina, i risultati in Economia,
come nei Widgets. `ResultProperties.qml` mantiene separato l'innesto degli editor.

[V] Gesti: lettura sotto il puntatore, legenda con serie attivabili, rotella di
zoom solo sulle linee lunghe, propagazione della rotella negli altri grafici,
banda sinistra, panoramica centrale, doppio clic per inquadrare, menu contestuale.
SVG e PNG usano colori chiari, font scelto, intervallo visibile e serie nascoste.
La scala delle mappe usa i medesimi tredici colori del raster e dell'export.

[V] R394 A + 2: `Controls.Table` condivisa per le tabelle ordinarie. Le matrici
annuali usano `VirtualResultTable`, che virtualizza anche le colonne: 366 celle
per riga non vengono create tutte. Intestazioni/unità e totale restano fermi;
barre sottili sovrapposte. Senza dati si mostra il messaggio con il comando.
È presente il ripiego provvisorio per checkout del sistema privi della Table.

## Scelta del disegno, con le misure

[V] Scelti rettangoli e percorsi conservati sul scene graph di Qt Quick Shapes,
con una texture per la matrice. Le coordinate normalizzate si preparano una volta.
Il ridimensionamento cambia trasformazioni e assi; non ricostruisce i percorsi
e non richiama la preparazione Python. Lo zoom ritaglia in QML i soli segmenti
visibili, mantenendo quelli che attraversano il bordo e le interruzioni dei dati.
Questo evita l'allargamento dello stroke dovuto alla trasformazione anisotropa.

[V] Qt Graphs provato con `LineSeries` da 8.760 punti e `ScatterSeries` con delegate
di cella per la mappa. Termina con `Windows fatal exception: access violation`
in `QQmlApplicationEngine.loadData`, prima di popolare le serie. Lo stesso
sintomo è stato riprodotto anche con GraphsView vuoto. I due log finali sono in
[misure/grafici](misure/grafici/). **Non è disponibile un confronto numerico
valido delle prestazioni di Qt Graphs su questa installazione.** La scelta è
motivata dalla soluzione funzionante misurata e dal blocco riprodotto dell'altra,
non da un presunto vantaggio percentuale.

[V] Misura finale del componente `Chart.qml` completo: Windows, Direct3D 11,
scala 1, ciclo basic, 8.760 campioni, tre processi nuovi per forma, 40 resize reali
in ogni processo. Sei JSON `final-production-*.json` conservano ogni campione.

| Forma | Preparazione Python iniziale | Mediane sync/disegno nei 3 processi | Massimo sync/disegno | Preparazioni durante 40 resize |
|---|---:|---:|---:|---:|
| Linea 8.760 ore | 7,72–10,38 ms | 0,624 / 0,673 / 0,758 ms | 3,010 ms | 0 |
| Mappa 365×24 | 3,95–7,73 ms | 0,290 / 0,297 / 0,299 ms | 2,486 ms | 0 |

[V] Una preparazione iniziale e 40 frame di resize per processo; zero warning QML.
Le immagini finali delle due forme sono state aperte: la serie e la mappa ci sono,
quindi il costo basso non deriva da un disegno scomparso. Il benchmark distingue
`beforeSynchronizing → afterRendering` da `widthChanged → frameSwapped`.

[V] La seconda misura comprende la presentazione sul desktop separato e arriva
a 1.027,5 ms; mediana anche circa 1.002 ms. **Non si dichiara per questo una
fluidità misurata sul monitor di Daniel.** Serve la verifica della presentazione
nella shell unita. Il caricamento QML a freddo del processo, con cache disattivata,
è 1,30–1,65 s e il primo frame 1,46–1,81 s: non è sotto un fotogramma.
Il costo della geometria Python e il costo continuo del resize sono separati.

[V] Riferimento letto: `docs/revisioni/codex-velocita-esito.md`, Consumi Widgets
2.786 ms per 40 passi. Non si calcola un fattore di accelerazione fra quel
percorso di pagina intera e questo benchmark di un solo grafico.

Documentazione tecnica usata: [Qt Shape](https://doc.qt.io/qt-6/qml-qtquick-shapes-shape.html)
per geometria conservata e preprocessing asincrono,
[ShapePath](https://doc.qt.io/qt-6/qml-qtquick-shapes-shapepath.html) per lo stroke,
[GraphsView](https://doc.qt.io/qt-6.12/qml-qtgraphs-graphsview.html) per il confronto.

## Dati e compatibilità

[V] `charts_data.py` espone dati grezzi, serie, categorie, unità, fonti, tabelle,
tessere e pedigree. Usa le stesse funzioni del nucleo delle pagine Widgets.
Il differenziale usa il vero parser e il meteo registrato
`tests/calcoli/riferimenti/pvgis53-tmy-rho.json.gz`, PVcalc registrato, un anno
di 8.760 ore, consumo ufficio da 16.000 kWh, valutazione economica e confronti
FV/accumulo del nucleo. Nessuna rete reale.

[V] Verificati tutti i valori e l'ordine delle serie/tabelle, tessere, record,
formule e fonti, con e senza PVGIS/batteria, zero produzione/consumo, dati
mancanti ed errori. NaN/inf diventano null, mai zero. Un addendo mancante rende
indisponibile il solo totale relativo. Totali aggiunti soltanto alle quantità
additive; nessuna somma di percentuali, curve cumulative o medie orarie.

[V] `charts_controller.py` collega la sessione: conversione dei risultati in
worker, pubblicazione atomica delle pagine, scarto delle risposte obsolete,
aggiornamenti per topic, mantenimento delle pagine leggibili durante il lavoro.
I getter e i gesti non avviano calcoli. I wrapper QML sono già caricabili tramite
URL; API e collegamento nella [nota d'integrazione](grafici-integrazione.md).

## Primo uso e transizioni

[V] Pagine e grafici si costruiscono al primo ingresso nel viewport e si
conservano. La scheda precedente rimane fino alla disponibilità della nuova
geometria; poi avviene la dissolvenza. Formule fuori vista non vengono richieste.
La richiesta formula è asincrona, con cache e invalidazione di tema/font/scala.
I font sono registrati una volta, senza duplicarli a ogni formula.

[V] Prove di cambio scheda e Grafico/Tabella con prima visita e ritorno, movimento
normale e ridotto, controllando i pixel del contenuto. Nessun campione vuoto.
Sono catture campionate durante le transizioni: non una registrazione di ogni
frame presentato dal monitor fisico.

## Foto e differenze dichiarate

[V] [120 coppie Widgets/Quick](confronto/grafici/README.md), dieci soggetti,
chiaro/scuro, scala 1/2, 1366×900, 1600×960 e 1920×1080. Tutti i 24 contatti
aperti; quattro coppie controllate anche ingrandite. Manifest e originali in
`build/quick-foto/grafici`. Dimensioni fisiche verificate, non dedotte dal nome.

[V] Altre 36 foto delle pagine in italiano in `build/quick-foto/grafici-pagine/R03`,
più le 12 tabelle definitive in `build/quick-foto/grafici-tabelle/R01`, tutte
ispezionate. Fotografie di fonti, formule, finestra stretta e testo grande nei
medesimi archivi. I primi scatti a scala 2 limitati da Windows e le pagine in
inglese sono evidenze intermedie; non sono usati come matrice finale.

Differenze volute: legenda sopra il disegno, unità orizzontale, graduazioni
comuni e margine sinistro misurato dal testo. Non si dichiara parità dell'intera
immagine entro 1 px. Low residui: rampe delle linee leggermente più scalettate a
scala 1; raggruppamento delle quattro cifre Qt diverso dal formatter Widgets
in alcune celle. I dati grezzi sono identici.

## Verifica e consegna

[V] Revisione indipendente di adattatore, renderer, immagini e controller.
Corretti i rilievi medium sulla lettura obsoleta, scala cromatica, export zoom
ed errore delle Verifiche durante un anno valido; corretto il low sui font.

Comandi riproducibili, con il Python del progetto e `PYTHONPATH=tests;src`:

```text
python -m unittest discover -s tests/quick/grafici -t tests
python -W default -m unittest discover -s tests/formati -t tests
python -m ruff check --select F,E9,B .
python -m quick.grafici.benchmark production line --output build/quick-bench/line.json
python -m quick.grafici.benchmark production map --output build/quick-bench/map.json
python -m quick.grafici.photographs --theme light --size 1366x900
```

Per le finestre native: `QT_QPA_PLATFORM=windows`, `QSG_RHI_BACKEND=d3d11`,
`QSG_RENDER_LOOP=basic`; `QT_SCALE_FACTOR=1` oppure `2`. I test usano eventi Qt
sulle proprie finestre, mai mouse e tastiera fisici di Daniel.

[V] Formati: 96 test verdi, 39,108 s. La suite Widgets completa non è stata
rieseguita: UI e nucleo non modificati, secondo il perimetro del CONTESTO.
Riepilogo finale del lotto Quick e lint aggiunto dopo l'ultima esecuzione sotto.

La shell è proprietà di `r12-sistema`: i contenitori centrali delle quattro pagine
vanno collegati nell'unione tramite gli URL e `install_results`. Nessuna modifica
ad app/Shell da questo ramo. Restano esterni anche gli editor destri del ramo
Proprietà e la misura della presentazione sul monitor fisico.

Git: merge riusciti, staging/commit negati dal filesystem su config/index.lock
esterni alla radice scrivibile. File lasciati nel worktree, nessun push/tag e
nessun aggiramento. Il commit e l'integrazione spettano alla sessione che ha
accesso alla directory Git condivisa.
