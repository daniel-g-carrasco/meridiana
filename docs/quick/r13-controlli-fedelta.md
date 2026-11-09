# r13-controlli: confronto di fedeltà

05/11/2026. Ramo `r13-controlli`. Rapporto della passata sui controlli comuni.

## Ambito e riferimento

[V] Il riferimento è il codice Widgets di produzione: `theme.py`, `style.py`,
`segments.py`, `scrollbars.py`, `checkboxes.py`, `status_pill.py`, `title_tools.py`,
`popups.py`, `sections.py`, `rows.py`, `cards.py`, `phasebar.py`, `icons.py` e `fades.py`.
Letti PASSATA-FEDELTA, CONTESTO, da-sistemare e controlli-api; viste le cinque
schermate di Daniel, comprese quelle sui rounding e sulle sottoschede delle Verifiche. Nessun file Widgets modificato.

Il confronto riproducibile è [controlli/index.html](confronto/controlli/index.html).
Ogni coppia mostra a sinistra un QWidget vero, a destra il controllo Quick,
con la stessa misura logica. Le immagini sono esposte al 200 %, anche quando
acquisite a DPR 2. Non sono ricostruzioni del riferimento in QML.

## Correzioni

| Famiglia | Risultato e riferimento |
|---|---|
| Pulsanti normali e comandi | Padding, altezza, sfondo neutro, testo e icona disattivati; un QPushButton selezionato non diventa uno strumento premuto. Il bordo di focus resta sopra lo strato hover, R161. |
| Strumenti e pulsante diviso | Modi icona/testo, Plex Condensed, misure della barra; R364: hover comune, parte indicata più marcata, nessuna linea centrale, giunzione quadrata. Il menu resta accessibile se il comando principale è disattivato; anche col tasto destro. |
| Campo testo e numero | Bordo assente a riposo, hover sottile, focus di 2 px, selezione coi colori condivisi. Tab seleziona; il clic prende il focus. Uscendo da un campo stretto torna visibile l'inizio. Unità vicina al valore, frecce SVG originali; incremento del numero appena digitato, limiti e ripetizione. Ruota solo col focus. |
| Tendina | Campo e freccia del QSS, voci coi colori della selezione e le misure del popup Fusion; abilitazione propagata all'elenco. Tastiera ed Esc provati. |
| Casella | Quadrato di 16 px dentro l'allocazione di 22, segno originale, stato parziale, selezione neutra, focus e disabilitazione. |
| Segmenti e linguette | Pista e selezione condivise; spostamento di 110 ms OutCubic; linguette di 32 px, distinta l'altezza 36 delle fasi. Nessuno strato hover aggiunto sopra la voce già scelta. |
| Pillole e conteggi | Badge negli stati Widgets; nuovo CountPill con geometria P3, simboli colorati, zero attenuato e spazio riservato per due cifre. |
| Scheda e sezione | Scheda panel con bordo card_line e raggio 8, titolo e croce alle posizioni Widgets, margine interno 6. Sezione con fascia, freccia, animazione di apertura e «?» separato; titolo ancora leggibile da disattivato. |
| Scorrimento e divisore | Barra di 10 px, tratto di 6, estremi di 8, minimo 28; colori di riposo/hover/pressione. Divisore trasparente di 8 px con cursore di ridimensionamento. |
| Sfumature | EdgeFades comune riprende STOPS/PAGE_STOPS, geometria e ritagli di ui/fades.py. Varianti lista, pagina e tabella; attive solo dove resta contenuto, senza intercettare i gesti. Integrate in List, Tree e Table. |
| Lista e albero | Altezze native, rientro 20, freccia piena, stanza di 10 px per lo scorrimento secondo R100. Nessuna cornice di focus né hover di riga aggiunti rispetto al QSS. Nell'albero Sinistra torna al padre, Destra al figlio; Home/End e doppio clic restano disponibili. |
| Tabella | R394 prevale sulla vecchia griglia: fascia estesa, unità sotto il titolo, soli separatori orizzontali, numeri a destra, totale fermo, barra sovrapposta. Peso 500 delle intestazioni preso dal bozzetto A + 2 approvato. Vuoto con comando. |
| Menu e sottomenu | Raggio, ombra, freccia piena, separatori, colonne condizionali per icone/spunte e scorciatoie a destra. Frecce saltano i separatori; apertura a puntatore ed Esc provati. |
| Tooltip | R367/R379: stesso HTML e misura QTextDocument, massimo 340 px, posizione del puntatore congelata, inversione vicino al fondo, sola opacità 90/60 ms, passaggio immediato al successivo. |
| Dialogo | Sfondo finestra, pulsanti nell'ordine Windows, Esc annulla e Invio conferma. Il focus già nel contenuto è conservato; `acceptOnReturn=false` lascia Invio a un editor multilinea. |
| Vuoto e avanzamento | Tipografia e toni Widgets. ProgressBar usa le due superfici statiche Fusion, scalate per DPR; l'animazione resta in Quick. |
| Cursore | Nuovo Slider comune: pista line/muted, maniglia 16, hover sulla maniglia, tastiera, trascinamento, passo pagina sulla pista con arresto al puntatore durante la pressione prolungata, Home/End e ruota col focus. |
| Icone | Stessi SVG di produzione, rasterizzati alla dimensione fisica; segni e croce riusano geometria e spessore dei pittori Widgets. Colore disattivato dalla palette comune. |

L'API precedente resta disponibile. Le aggiunte facoltative sono documentate in
[controlli-api.md](controlli-api.md). Nessuna nuova dipendenza installata.

## Prove e fotografie

[V] 48 prove mirate verdi: 27 nuove regressioni e 21 prove preesistenti dei controlli.
Ripetute a DPR 1 e 2: `tests-final-r06.log` e `scala2-final-r06.log`.
[V] 46 prove di sistema verdi. [V] 96 prove dei formati verdi.
I log sono in `build/quick-foto/r13-controlli/`; contengono anche i ResourceWarning
di pulizia dei temporanei già presenti nella suite, che non sono errori di QML.

[V] Le regressioni usano QTest/sendEvent, pixel del QQuickWindow e stato dei controlli.
Comprendono bordi nei due temi, rotella senza focus, numero appena digitato, menu
con separatore, sottomenu al puntatore, tooltip vicino al bordo e immobile dopo
l'apertura, clic destro sul pulsante diviso, navigazione nell'albero, campo stretto
e Invio nel dialogo. Il contatore dei provider Python resta a zero durante i
fotogrammi dei segmenti, delle sfumature durante lo scorrimento e dell'avanzamento
indeterminato. Una regressione confronta tutte le righe fisiche del tratto Fusion
dell'avanzamento, anche a DPR 2. Nessun fotogramma vuoto
o finestra di primo livello aggiuntiva nella prova.

[V] Matrice: 35 casi, 760 coppie e 1.520 immagini, chiaro/scuro, DPR 1/2, stati
applicabili e testo grande. Ritagli rivisti al 200 % in 96 tavole. Verifica automatica
di completezza, dimensioni e Direct3D 11 con `verify_evidence.py`. Le 48 coppie
delle sfumature hanno scarto massimo RGB di 1 su 255, controllato su ogni pixel.
I casi `field-narrow` e `combo-narrow` aggiungono la larghezza 85 px. Gli stati
non posseduti da un controllo sono esclusi: premere un tooltip, per esempio,
lo distrugge nei Widgets. Manifest JSON e `verifica.json` indicano ogni coppia.
Galleria completa: 48 schermate in `build/quick-foto/r13-controlli/gallery`,
1366×900, 1600×960 e 1920×1080. Windows, Direct3D 11, nessun offscreen.

[V] Percorso integrato `tests/quick/percorsi/controlli.json`: progetto di Rho,
12 passi su entrambi i programmi, hover, strumento, Esc, Impianto, Modellazione,
File, ritorno e tre misure. Ripetuto nei due temi e alle due scale; immagini e
stati in `build/quick-foto/r13-controlli/pilot-{light,dark}-s{1,2}`.
Due ripetizioni intermedie sono in `pilot-final-light-s1` e `pilot-final-r02-light-s1`.
La revisione visiva ha rilevato nel passo 08 di queste sei serie la vecchia immagine
di File ancora in uscita nei Widgets: i JSON concordano, la foto non è confrontabile.
Escluso quel passo dalle prove visive, conservando le immagini originali.
[V] Ripetuto il percorso nei quattro `pilot-settled-{light,dark}-s{1,2}`, attendendo
la fine effettiva del velo di entrata/uscita di File; riviste tutte le 48 nuove coppie.
L'adattamento è solo nella copia dello strumento di cattura in build, descritto e
identificato con hash nel JSON integration. Nessuna animazione di produzione cambiata.
L'ultimo ritocco alla tendina stretta (testo troncato senza puntini) è successivo a
questi percorsi ed è verificato nella matrice isolata e nelle 48 prove ripetute.

L'integrazione usa una copia di `r13-shell` archiviata in build, con sovrapposti
solo Controls, Theme e i due provider di questo ramo. Il SHA e, nell'ultima
ripetizione, gli hash dei file sono nei JSON `integration*`. Non è un merge.
La copia di prova non modifica né l'altro ramo né il progetto originale di Rho.
Il solo campo `modified` del progetto è escluso dal confronto, come nella suite
parity: il riferimento Widgets salva la propria copia temporanea all'apertura.

## Differenze dichiarate e limiti

- [V] R379 rimuove la salita ancora presente nel vecchio tooltip. R394 cambia
  intenzionalmente la vecchia griglia. Sono decisioni di Daniel già approvate.
- [V] Menu e dialoghi restano Popup.Item nella finestra Quick, come da API.
  Il dialogo ha il titolo interno; nel QDialog il titolo è nella cornice di
  Windows, esclusa da QWidget.grab. Non sono fotografie indistinguibili del
  dialogo intero. Nessuna finestra secondaria viene creata per simulare il titolo.
- [V] QWidget.grab dei popup non include il bordo, il rounding e l'ombra DWM.
  Quick li disegna dentro la propria finestra: il contorno esterno dei ritagli
  non certifica l'equivalenza della composizione del desktop.
- [V] A 200 % restano differenze di antialiasing e di allineamento fra QPainter
  e il grafo di scena, in particolare sugli angoli e su alcune basi del testo.
  Il terminale del riempimento Fusion dell'avanzamento può differire di un pixel.
- [V] Il test preesistente `quick.grafici.test_tables` chiede intestazioni con
  peso almeno 600. La base aveva 400; il bozzetto approvato prescrive 500.
  Il test resta rosso e non è stato indebolito nel ramo dei grafici.
- [V] La suite parity ha eseguito 70 prove: un fallimento nel registro CSV
  (`test_all_requests_and_test_methods_have_exact_inventory_rows`), sette saltate
  e due fallimenti attesi. Il log, precedente all'ultimo aggiornamento di richieste.md, contiene
  132 voci del registro da aggiornare;
  la prima è R388/1. Non è una suite tutta verde e non è stata indebolita.
- [V] Nei campi larghi 85 px Quick mostra l'inizio alla perdita del focus.
  Durante la sola pressione nel campo può restare il cursore in fondo fino al
  rilascio: questo dettaglio transitorio non è dichiarato identico. La tendina
  stretta ora tronca senza puntini, come il riferimento Widgets.
- [V] Il lint globale segnala 7 errori preesistenti in grafici, impianto e pagine.
  Il lint dell'area controlli è verde. I file degli altri rami restano intatti.
- [V] EdgeFades è pronto per le pagine degli altri rami: l'aggancio ai loro
  Flickable e il ridisegno delle righe specializzate di Verifiche restano a quei
  moduli. Le immagini delle sfumature isolate non certificano quei contenitori.
- [V] Le foto integrate mostrano ancora differenze di pianta, terreno 3D,
  disposizione delle schede, File e Verifiche. Non sono corrette in questo ramo.
- [I] Puntatore fisico, presentazione al monitor e fluidità sul Dell al 200 %
  restano da giudicare a schermo reale: il desktop separato non li misura.

Il rapporto non dichiara identità assoluta di ogni pixel né parità completa
dell'applicazione. I residui sopra sono visibili e separati dai controlli corretti.

## Salvataggio Git e riproduzione

[V] Disponibili i commit `0e2329f` e `5a3af9e`. I successivi `git add` sono
rifiutati: impossibile creare `index.lock` nel gitdir esterno al worktree.
Il tentativo di `git commit` richiesto alla ripresa non ha quindi prodotto un
commit. Anche il merge è rifiutato su `ORIG_HEAD.lock`. Nessun vincolo aggirato.
Le modifiche successive e le immagini restano nel worktree, pronte da aggiungere.
Ultimo tentativo del 05/11, dopo le verifiche: entrambi i comandi separati
`git add` e `git commit` escono con codice 1 e permesso negato su `index.lock`.

Comandi, con `PYTHONPATH=tests;src` e il Python della venv di Meridiana:

```text
python -m unittest quick.controlli.test_fidelity quick.sistema.test_controls
python -m quick.controlli.capture_pairs --matrix
python -m quick.controlli.capture_pairs --matrix --large --states normal
python -m quick.controlli.contact_sheets
python -m quick.controlli.verify_evidence
python -m quick.controlli.integrated_capture
```

Le superfici dei controlli, i token, le icone, le prove e la galleria sono
riusabili nel modello Quick previsto da R397; non è stato modificato il template.
