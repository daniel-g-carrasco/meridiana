# r13-file: esito della passata di fedeltà

05/11/2026. Ramo `r13-file`. Widgets e nucleo di calcolo invariati.

[V] Ultimo commit: `73996f1a`. Le ultime correzioni delle coordinate, l'attesa Qt
dei test e questa consegna sono nel checkout. Il commit finale non è stato
possibile: `git add` non può creare `index.lock` nella cartella Git condivisa,
fuori dalla radice scrivibile del sandbox. Stato dettagliato in
[stato/r13-file.md](stato/r13-file.md). Nessun push.

## Esito

[V] File, le sette categorie delle Impostazioni, Anagrafica, Nuovo progetto,
Relazione e finestre sono agganciati al registro delle parti della finestra vera.
Condividono sessione, configurazione, annulla/ripristina, comandi e cartelle della
finestra. Non serve avviare la galleria isolata per usarli.

[V] Il confronto permanente è [confronto/r13-file/index.html](confronto/r13-file/index.html):
Widgets a sinistra, Quick a destra: 124 coppie originali e 172 coppie di ritagli al
200%, più due stati Quick dell'avanzamento. La matrice File definitiva è review-r8,
le finestre workflows-r9, gli importatori imports-r4, la relazione report-fixture-r5.
Il manifest riporta il percorso di ogni sorgente. Non è una dichiarazione di
indistinguibilità: le differenze residue sono elencate sotto.

[V] **Il blocco in `QTest.qWait` è un limite della prova integrata, non una
diagnosi di blocco del programma normale.** Riprodotto dopo `fded9913`: il primo
`qWait(100)` di `FilePartTest` non ritorna; traccia dopo 45 s in
`confronto/r13-file/verifiche/threaded-integrato.txt`. Sostituendo soltanto l'attesa
del test con `QEventLoop` e `QTimer`, la stessa finestra con render loop threaded
apre il dialogo, risponde a Esc e chiude: prova verde in 9,916 s. Nessuna modifica
al renderer, alla scena o al default dell'app. Il meccanismo interno del blocco
di qWait non è stato dimostrato. Il precedente callback Python di
`QQuickPaintedItem` è stato rimosso dalle anteprime proprie, verificate a thread.
La suite completa delle pagine passa poi con threaded: 81 test, 174,916 s,
compresa l'ultima correzione delle coordinate e del marker.

Le foto e la prima suite cumulativa usano **Direct3D 11 nativo, piattaforma windows,
render loop basic**, sul desktop separato autorizzato. La ricevuta riporta
separatamente le verifiche con threaded; nessuna foto basic viene presentata come
misura di fluidità del render a thread.

## Porting e gesti verificati

| Riferimento Widgets letto | Parti Quick | Copertura concreta |
|---|---|---|
| `file_page.py` | `files.py`, `files_part.py`, `File/` | Apri/recenti, salva, salva come, revisione, esporta, cataloghi, aiuto; protezione progetto modificato, errori, file atomici e `.bak` |
| `preferences.py`, `appearance.py` | `settings*.py`, `Settings/` | Aspetto, Navigazione, Tastiera, Assistente, Relazione, Mappe, Riservatezza; applicazione immediata, annulla ultima modifica, ripristino con conferma |
| `new_project.py`, `registry_page.py` | `dialogs.py`, `Dialogs/` | Coordinate e coppie incollate, anagrafica, sito riservato, validazione, creazione e annullamento |
| `report_page.py`, `report.py` | `report.py`, `Report/` | Modello, firma, committente, revisione, indirizzo, capitoli, allegati, registro CSV, anteprima, esportazione, annullamento |
| `template_dialog.py`, `canopy_dialog.py` | `dialogs_preview.py`, `Dialogs/` | Forme e misure, formule, anteprima con quote e lati evidenziati, rotazione, posa; stessa geometria dei Widgets |
| `shortcuts_dialog.py` | `dialogs.py`, `SettingsKeyboard.qml` | Ricerca, acquisizione tasto, conflitto e assegnazione esplicita, annulla, persistenza atomica |
| `site_dialog.py` | `dialogs.py`, `Dialogs/` | Ricerca e scelta, errori, permessi di rete e riservatezza, modifica annullabile, divieto di spostamento dopo il disegno |
| `ifc_import.py`, `pvsyst_import.py` | `dialogs_jobs.py`, `Dialogs/` | Lettura asincrona dei file reali delle prove, scelte, riepilogo, anteprima, importazione e annulla; sorgenti intatte |
| `update_dialog.py` | `dialogs_jobs.py`, `files_part.py`, `Dialogs/` | Stato, versione, note, avanzamento, annullamento, firma verificata prima dell'offerta di installazione, protezione modifiche |

[V] `files_part.py` registra i posti File, anteprima della Relazione, ispettore
Relazione e overlay delle finestre. I comandi Logo e Profilo aprono le impostazioni
effettive. Il catalogo in consultazione e gli importatori PAN/OND riusano il catalogo
esistente. La segnalazione prepara una bozza locale modificabile: allega soltanto
i dati diagnostici scelti, oscura i segreti e apre la pagina di invio soltanto su
comando. Nessuna segnalazione è stata inviata durante le prove.

[V] R378: cambio della sottosezione sul solo lato destro, opacità senza spostamento;
entrata da una fase conservata, movimento ridotto immediato. R392: File e dialoghi
interni alla stessa finestra, nessun nuovo primo livello nelle prove dedicate.
Le prove sono in `test_pages.py`, `test_fidelity.py` e `test_file_part.py`.

[V] Il copione `tests/quick/pagine/pilot_file.py`, con
`tests/quick/percorsi/file.json`, percorre 14 passi sui due programmi con eventi Qt
reali: passaggio del puntatore, File, Impostazioni e categorie, sezioni e ritorno.
La ricerca dei controlli è limitata alla pagina File per distinguere le voci omonime
delle fasi. Esc è verificato direttamente nella finestra Quick. Sul desktop
separato la scorciatoia Widgets della finestra inattiva non risponde al tasto
inviato al QWidget: il percorso comune usa il pulsante Torna al progetto.

## Correzioni nate dalle prove

- [V] Prima anteprima PDF: creata la cartella cache padre. Richiesta manuale:
  consumato il timer automatico pendente per evitare una seconda compilazione.
  Restano visibili le pagine precedenti fino alla consegna completa delle nuove.
- [V] Anteprime edificio e pensilina: stessa geometria, proiezione e quote dei
  Widgets, rasterizzate sul filo GUI e caricate da `Image`; niente Python nel
  callback del filo grafico. DPR fornito da QML, senza invalidare la finestra.
- [V] IFC: ripresi origine, nord, falde, coordinate, distanze, scelte complete e
  riepilogo separato tra preso, approssimato e lasciato fuori. Corretta la vista
  dall'alto che risultava specchiata rispetto ai Widgets.
- [V] Tema iniziale della parte allineato alla configurazione condivisa della
  finestra: Plex, indaco, grigio. Le scorciatoie passano al registro attivo.
- [V] Rimozione dell'ultimo profilo: valore interno vuoto valido, tendina con
  profilo effettivo o Nessuno, senza riferimento a un profilo cancellato.
- [V] Foto dei due PDF inizialmente diverse: il riferimento Widgets scaricava
  l'orizzonte prima di disattivare la rete. La configurazione ora lo impedisce
  prima della costruzione della finestra. La fixture calcolata mostra in entrambi
  57,60 kWp, 54.311 kWh e PR 54,1%. Non sono dati meteorologici reali del progetto.
- [V] Nuovo progetto: una sola coordinata rendeva valido il punto con l'altra a
  zero. Prova rossa prima della correzione, poi verde; servono entrambe. La coppia
  incollata in Latitudine passa dal campo QML vero e Nuovo azzera la mappa precedente.
- [V] Schede File: ripresi separatori, Esci in fondo, riempimenti e chip dei
  formati. Le descrizioni vuote non vengono tradotte: gettext restituiva l'intera
  intestazione del catalogo, riprodotta nelle foto e coperta dalla regressione.

## Prove conservate e riproduzione

Python: `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.
Ambiente: `PYTHONUTF8=1`, `PYTHONPATH=tests;src`, `MERIDIANA_QUICK_NATIVE=1`,
`QSG_RENDER_LOOP=basic`, senza `QT_QPA_PLATFORM=offscreen`.

| Controllo | Esito e ricevuta |
|---|---|
| Pagine, dopo il merge `fded9913` | [V] 81 test verdi, 162,802 s; `pagine-postmerge.log` |
| Pagine, consegna dopo `73996f1a` | [V] 81 test verdi, 130,019 s; `pagine-consegna.log` |
| Pagine definitive, rendering threaded | [V] 81 test verdi, 174,916 s; `pagine-threaded.log` |
| Relazione, regressione timer | [V] 11 test verdi, 47,615 s; `relazione-timer.log` |
| Sistema, integrazione `fded9913` | [V] 46 test verdi, 42,799 s; `sistema-finale.log` |
| Allineamenti Relazione/Impostazioni/finestre | [V] 24 test verdi, 93,821 s; `allineamenti.log` |
| File e coordinate Nuovo progetto | [V] 32 test verdi, 50,268 s; `file-nuovo.log` |
| Descrizioni vuote e campi QML | [V] 13 test verdi, 34,508 s; `cataloghi-coordinate.log` |
| Ultima correzione del punto sulla mappa | [V] 17 test verdi, 21,895 s; `coordinate-finali.log`; marker tolto e mappe online disattivate quando le coordinate diventano incomplete |
| Formati, Widgets invariati | [V] 96 test verdi, 26,160 s; `formati.log` |
| Lint completo dopo `fded9913` | [V] `ruff check --select F,E9,B .`, verde; `lint.log` |
| Anteprime isolate con threaded | [V] Due test verdi; `anteprime-threaded.log` |
| Finestra integrata con threaded e qWait | [V] Blocco del test riprodotto, interrotto; `threaded-integrato.txt` |
| Stessa prova con ciclo eventi Qt e threaded | [V] Verde, 9,916 s, senza modifiche applicative; `threaded-ciclo-eventi.log` |

Le ricevute sono nella sottocartella `confronto/r13-file/verifiche/`.
I gruppi mirati ripetono parte degli 81 test, non sono casi aggiuntivi al totale.
Nessuna soglia è stata allentata. Una precedente
prova temporale aveva misurato 141 ms contro 100 ms durante acquisizioni parallele;
la ripetizione della suite a carico ridotto è verde. Il precedente B905 della
pianta è risolto dal merge del ramo proprietario, senza modificarne il file qui.

Comandi riproducibili, dalla radice del checkout:

```text
python -m unittest discover -s tests/quick/pagine -t tests -v
python -m unittest discover -s tests/quick/sistema -t tests -v
python -m unittest discover -s tests/formati -t tests -v
python -m ruff check --select F,E9,B .
python tests/quick/pagine/build_gallery.py
```

Per ripetere la suite delle pagine con il rendering a thread, impostare
`QSG_RENDER_LOOP=threaded` ed eseguire lo stesso comando unittest.

Acquisizioni: `capture_fidelity.py` per la matrice, `capture_workflows.py` per
finestre e relazione, `capture_imports.py` per importazioni/aggiornamento. Tutti
accettano `--help`; `QT_SCALE_FACTOR=2` ripete la prova a DPR 2. La relazione
calcolata usa `--reference-fixture --compute --reports-only`, meteo sintetico e
rete disattivata. Il calcolo completo di Rho non ha consegnato un risultato entro
i 120 s del tentativo su entrambi i programmi: non è conteggiato tra le prove verdi.

## Differenze visive e semplificazioni

Ogni voce rimanda alla coppia prima/dopo nella galleria.

- **Finestre interne:** titolo e cornice fanno parte dell'overlay Quick. Nei
  Widgets il titolo appartiene alla finestra Windows e non compare nel `grab()`
  del dialogo. Dimensioni del contenuto e ordine delle azioni ripresi dai Widgets;
  resta diversa la cornice. Confronti `finestre-*` e `importazioni-*`.
- **PVsyst:** scelta del file, variante, lettura e riepilogo nella stessa finestra,
  anziché due dialoghi consecutivi. Funzioni conservate; differente disposizione
  del riepilogo. Confronti `importazioni-*-pvsyst*`.
- **Impostazioni estese:** Aspetto raccoglie le opzioni aggiuntive in una sezione
  apribile sotto Anteprima. Assistente espone configurazione locale, cloud e voce
  nella pagina; i Widgets hanno anche finestre Configura. Non sono rimossi campi.
  Confronti `*-preferences-appearance` e `*-preferences-assistant`.
- **Controlli comuni:** restano piccole differenze di resa di bordi, focus,
  caselle, righe della tabella Tastiera e misure del testo. La tabella Quick segue
  il sistema comune; non è dichiarata uguaglianza dei pixel. Confronti al 200%.
- **Nuovo progetto e Sito:** titolo, introduzione, ricerca, coordinate testuali,
  spiegazioni, dati facoltativi e comando in fondo alla colonna ripresi dai Widgets.
  Natural Earth usa gli stessi colori e nomi, ma la mappa Quick conserva Web Mercator;
  i Widgets usano il piano locale e Equal Earth alle scale maggiori. Scala, contorni,
  nomi visibili e comandi della mappa non sono indistinguibili. Le validazioni e la
  creazione sono provate; il servizio online è simulato. Confronti `*-new` e `*-site`.
- **Relazione:** stato accanto al titolo, pagine fino a 820 px più bordo, controllo
  capitoli e anteprima riallineati. Durante il lavoro Quick aggiunge una barra di
  avanzamento e Annulla. L'aiuto è nel fumetto, secondo R383, anziché nel dock
  Widgets. Cornice, scrollbar e rendering del PDF possono differire di pochi pixel.
- **Contorno della finestra:** le foto conservano anche differenze di fasi,
  Verifiche e posizione di Meridio, di competenza degli altri rami. Non vengono
  ritoccate per far sembrare le coppie più simili. Le sorgenti della matrice e dei
  dialoghi sono datate nel manifest e possono precedere l'ultimo merge della shell.

## Non verificato

Presentazione e fluidità sul monitor di Daniel, puntatore di sistema, tutte le
combinazioni di tooltip e stati dei controlli al 200%, ogni livello di testo grande
nelle quindici finestre, servizi esterni con credenziali, installazione effettiva
di aggiornamenti, download reali dei modelli o della voce. Nessun rilascio, push o
tag. I test `widget` e `finestra` completi non sono stati rilanciati: il codice
Widgets non è stato cambiato; sono stati eseguiti i confronti mirati e i formati.

## Riutilizzabile nel modello comune, R397

Registro della parte File, navigazione a due livelli, transizione del solo contenuto,
piede fisso con annulla/ripristina, moduli con campi a fuoco, overlay unico delle
finestre, anteprime raster preparate sul filo GUI e conservazione delle pagine
durante la generazione asincrona. Il trasferimento al template non è stato eseguito.
