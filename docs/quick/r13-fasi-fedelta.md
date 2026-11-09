# r13-fasi: Impianto e risultati, esito della passata

05/11/2026. [V] Parti installate nella finestra vera mediante `plant_part.py` e `charts_part.py`.
Tutti i controller condividono la `ProjectSession` della finestra. Nucleo e Widgets non modificati.
La fedeltà non è dichiarata indistinguibile: differenze e limiti sono elencati sotto.

## Cosa è stato portato

| Riferimento Widgets | Parte Quick | Riscontro |
|---|---|---|
| `ui/plant_page.py` | `PlantSide`, `PlantInverters`, `PlantInputCards`, `PlantDiagram`, `PlantTable`, controller Plant | Schede inverter, ingressi, stringhe, verifiche elettriche, selezione e modifica nella sessione |
| `ui/energy_pages.py` | `ResultsPage`, tre pagine e tre inspector, `charts_controller`, `charts_editor`, `charts_schema` | Tessere, tutte le schede, editor e basi dell'anno calcolato |
| `ui/storage_page.py` | `PlantStorage`, `Charts/StoragePage` | Catalogo, unità, configurazione, confronto delle taglie e risultato dell'accumulo |
| `ui/charts.py`, `ui/charts_pg.py` | `Chart`, `ChartGuide`, tabelle e backend Charts | Barre, impilate, perdite, linee, mappa oraria, flussi, tabelle e interazioni |
| `ui/catalog_dialog.py`, `brand_picker.py` | Catalog e PlantChoice, controller Catalog | Ricerca, filtri, ordinamento, selezione multipla, dettagli, preferiti, record personali |
| `ui/optimizer_groups.py` | `PlantOptimizerGroups`, controller Plant | Associazione dei gruppi ai moduli, modifica e annullamento |

[V] Barra Impianto: Catalogo, Scegli in automatico, Configura, Automatico, Disegna, Elimina stringa.
I dialoghi riaprono correttamente dopo Annulla; Esc termina il disegno e torna a Seleziona.
Rinomina inverter da F2, doppio clic e menu, ordine con Alt+freccia e trascinamento del disco.
Le tre righe elettriche, Uoc, Umpp e corrente sono confrontate con i Widgets usando gli stessi dati.
Importazione PVsyst con anteprima; elaborazione e lettura CSV in worker con controllo della generazione.

[V] Gli editor destri comprendono perdite e parametri termici/elettrici, sorgente e profilo consumi,
POD, fasce, mesi, bollette e CSV, costi, prezzi, finanziamento, CER e accumulo.
Ogni modifica passa per `session.edit()`, con undo; i draft non sopravvivono al cambio progetto.
Gli inspector invisibili mantengono dati e dimensioni senza ricalcolare il layout a ogni bordo.

[V] Produzione: Mesi, Perdite, Giorno tipo, Come è calcolato.
Consumi: Mesi, Giorno tipo, Anno, Settimana, Durata, Come è calcolato.
Economia: Bilancio, Anno, Bolletta, Flusso di cassa, Anno per anno, Taglia, Accumulo, Come è calcolato.
Formule e simboli hanno le dimensioni del riferimento; le quantità conservano le quattro colonne
simbolo, grandezza, valore/unità, fonte. Rendering delle formule asincrono e solo nella zona visibile.

[V] Grafici: colori delle serie dal riferimento, griglia, assi, legenda selezionabile,
lettura sotto il puntatore, cursore e punti, zoom a rotella e a rettangolo, ripristino con doppio clic,
menu del tasto destro ed esportazione SVG/PNG dell'intervallo e delle serie visibili.
I percorsi sono preparati una volta; il ridimensionamento usa trasformazioni QML senza ripreparare i dati in Python.
A scala 2 una prova ha riprodotto lo spessore errato di quattro pixel; ora il tratto è di due pixel fisici come nei Widgets.
Perdite mantiene almeno una riga leggibile per voce, anche con 24 voci in una pagina bassa.

[V] R394: intestazioni con unità, righe orizzontali leggere, totale fermo, barra senza spazio riservato,
vuoto con azione utile. Le stringhe hanno larghezza minima e scorrimento orizzontale: i valori numerici non vengono troncati.
R396: Calcola e Posa neutrali; puntino collegato rispettivamente a `energy_outdated` e agli effettivi layout obsoleti.
Prove su modifica e undo distinguono il risultato aggiornato da quello da ricalcolare.

## Anno reale nella finestra unita

[V] `live_year.py` apre una copia del progetto Rho, inserisce il meteo registrato nella cache temporanea,
preme F5 con un evento Qt e aspetta il worker reale. Nessun risultato energetico viene inserito dalla prova.
Esito: 8.760 ore, **425.566,385 kWh**, 358,56 kWp, 702 moduli collegati su 778, sette inverter, nessuna batteria.
Tutte e tre le pagine ricevono l'anno. Worker 163,49 s, trasferimento alla scena 11,63 ms, percorso totale 170,89 s.
Nessun avviso QML; contenuto del file originale invariato prima/dopo.
Il secondo parere PVGIS non è richiesto alla rete: la tessera lo dichiara indisponibile.
I valori e le foto sono in `confronto/r13-fasi/calcolo-f5.json` e nella sezione Calcolo da F5 della galleria.

## Fluidità: migliorata, requisito rigoroso ancora aperto

[V] Misura nativa nella finestra unita, render loop threaded, anno Rho caricato, grafico Consumi visibile.
Due trascinamenti da 120 passi per bordo, timer a 2 ms; nessun altro mio test durante la misura.
Lo strumento controlla anche il movimento effettivo del bordo e la variazione della larghezza del grafico.

| Finestra | Bordo destro, massimo | Bordo inferiore, massimo |
|---|---:|---:|
| 1600×960 | 26,10 ms | 11,03 ms |
| 1366×900 | 22,99 ms | 16,75 ms |
| 1920×1080 | 27,99 ms | 8,70 ms |

[V] Questo giro (`confronto/r13-fasi/resize-final-r03.json`) non ha intervalli oltre 30 ms.
La ripetizione automatica ha però registrato **30,64 ms** a 1600, un intervallo su 852 campioni;
gli altri cinque casi sono rimasti sotto 30 ms. Il giro precedente aveva anche una pausa di 130,30 ms
a 1366 (`resize-final-r02.json`). Non considero quindi garantito il limite richiesto.
`test_resize_budget` conserva soglia e `expectedFailure`, esteso a tutte e sei le combinazioni;
si attiva impostando `MERIDIANA_RHO_YEAR` alla fixture locale e va eseguito da solo.

[V] Prima dell'ultima unione erano comuni pause fra 40 e 70 ms. Eliminata la misura degli editor invisibili
mediante l'adattatore della parte Charts. Restano misure Python delle fonti del pannello Checks condiviso.
[I] L'ultima unione di più parti ha ridotto il costo, ma non è stata isolata la causa del miglioramento
né quella di ogni pausa residua. La misura del timer non è una misura della presentazione al monitor.

## Confronti conservati

[V] Galleria: `docs/quick/confronto/r13-fasi/index.html`, immagini WebP senza perdita.
124 coppie della matrice: 31 passi, chiaro/scuro, scala 1/2, misure 1366×900, 1600×960 e 1920×1080.
Venti coppie dei dieci tipi di grafico e ritagli al 200%; tre coppie aggiornate delle formule;
percorso dei comandi nella finestra unita e tre foto dopo il calcolo da F5.
I manifest conservano fase, dimensioni, scala, API grafica e cartelle sorgenti.
Acquisizioni Windows con Direct3D 11 sul desktop separato, senza comandare mouse o tastiera di Daniel.

[V] Guardati i fogli di confronto di tutta la matrice, le pagine delle formule, i gesti Impianto,
i grafici isolati e i ritagli di linee e marcatori. Le immagini documentano anche difetti corretti dopo:
la matrice precede le ultime correzioni di formule, altezza minima e tabella stringhe.
Le sezioni aggiornate sono indicate nella galleria. Non presento immagini storiche come prova dell'ultimo commit.

## Differenze e verifiche ancora necessarie

- [V] La geometria complessiva della finestra, alcuni margini delle tessere e l'area utile dei grafici
  differiscono dalle foto Widgets. Nei grafici scuri isolati resta una differenza del fondo dell'intestazione.
  I ritagli mostrano piccoli scarti di posizione di tacche e punti. Non è fedeltà completa al pixel.
- [V] Il riepilogo/meteo nella coda della barra dei risultati Widgets non ha un posto nel contratto attuale
  delle parti della shell. Il dato dell'impianto calcolato è presente nella pagina, non in quella coda.
- [V] Catalogo: il confronto dei selezionati è mostrato direttamente nei dettagli, invece di richiedere
  il pulsante Confronta dei Widgets. Stringhe: aggiunta vista Tabella con scorrimento orizzontale.
  Grafici: aggiunto spostamento con tasto centrale. Sono semplificazioni/aggiunte esplicite, non copie identiche.
- [V] SVG/PNG conservano dati, intervallo e serie; non è verificata l'identità di ogni tacca esportata
  con quella visualizzata da pyqtgraph. La posizione di ogni tooltip e tutti gli stati hover/menu
  non sono coperti da una matrice fotografica esaustiva.
- [V] Rho non contiene batterie: accumulo con batteria coperto dalle fixture e dalle prove dedicate,
  non da un secondo anno reale di Rho con accumulo. Nessuna modifica inventata al progetto originale.
- [V] Il desktop separato non misura la presentazione al monitor né il puntatore reale.
  La prova a schermo di Daniel resta separata. Nessun push, tag o rilascio eseguito.

## Prove automatiche e revisione

[V] Ultima unione della shell `631ef80b`, merge locale `ddd314f6`.
Sul contenuto finale delle parti, con piattaforma Windows e stile Basic:

| Gruppo | Esito |
|---|---|
| `quick.impianto` | 44 passate, 139,2 s, compreso il percorso con catalogo, undo, dialoghi, viste e trascinamento della tabella |
| `quick.grafici` | 69 eseguite: 68 passate, una saltata perché richiede Rho e macchina libera, 35,7 s |
| `quick.sistema` | 46 passate, 32,6 s |
| `formati` | 96 passate, 20,8 s |
| Spessore grafici a scala 2 | Sette prove passate dopo aver riprodotto il tratto errato di quattro pixel |
| Calcolo reale F5 | Passato, anno completo nelle tre pagine, originale invariato |
| Prestazioni, esecuzione separata | Un giro completo sotto 30 ms; ripetizione fallita a 30,64 ms, soglia mantenuta |
| Ruff F,E9,B su tutto il repository | Verde dopo l'ultima unione |
| `git diff --check` e riferimenti galleria | Verificati, nessun errore |

[V] La suite ha trovato anche un caricamento anticipato dei grafici fuori schermo: la posizione ometteva
l'altezza delle tessere sovrastanti. Riproduzione rossa a 350 px, correzione della posizione completa,
prove verdi sia con il secondo grafico fuori schermo sia con entrambi visibili in una pagina alta.
Matplotlib stampa avvisi sulla mappatura Unicode delle parentesi grandi; le foto mostrano le formule disegnate.
La revisione è svolta direttamente, senza altri agenti come prescritto dall'incarico.
I gruppi Widgets `widget` e `finestra` non sono stati rieseguiti: il loro codice non è stato modificato.

## Riproduzione

Usare Python della `.venv` di Meridiana, `PYTHONUTF8=1`, `PYTHONPATH=tests;src`,
`QT_QUICK_CONTROLS_STYLE=Basic`, piattaforma Windows senza `QT_QPA_PLATFORM=offscreen`.
Per i ritagli a scala 2 impostare `QT_SCALE_FACTOR=2`.

```text
python -m unittest discover -s tests/quick/impianto -t tests
python -m unittest discover -s tests/quick/grafici -t tests
python -m unittest discover -s tests/quick/sistema -t tests
python -m quick.grafici.live_year <progetto-Rho> <nuova-cartella>
python -m quick.grafici.resize_consumption <rho-year-it-r01.pickle> <nuovo.json>
python -m quick.grafici.review_gallery docs/quick/confronto/r13-fasi --update
```

La fixture locale è prodotta da `quick.grafici.calculated_rho`; i pickle sono solo risultati locali fidati.
Log, cronologia delle diagnosi e richieste alle altre parti: `docs/quick/stato/r13-fasi.md`.
