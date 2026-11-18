# Tema A: architettura e modello dei dati

Revisione completa di Meridiana (studio 18), tema A. Ramo `revisione-completa`, 23/10/2026. Lettura di tutto `src/meridiana` e prove offscreen sul PC di Daniel.

Legenda: **[V]** verificato, con il modo tra parentesi; **[I]** dedotto dalla lettura, non provato con un'esecuzione. Le righe sono quelle del ramo `revisione-completa` al 23/10/2026 (`file:riga`).

## 0. In breve

- Il confine nucleo/finestra regge: fuori da `ui/` solo `app.py:29-32` importa Qt, dentro la funzione `main`, e nessun modulo del nucleo importa `ui` tranne `app.py` [V grafo]. Niente cicli di importazione al livello del modulo [V grafo].
- Il difetto di architettura più grave non è dove sta il codice ma **come si propagano le modifiche**: ogni `edit()` fa un'istantanea intera, ridisegna tutto (pianta, albero, proprietà, pagine) e fa ripartire la posa di ogni sottocampo e il calcolo dell'anno intero, perché la chiave di posa serializza ogni edificio ed esclusione per intero (nome e categoria antincendio compresi) e il ritorno della posa fa sempre ripartire l'energia. Rinominare un edificio sul progetto generato da 20 edifici e 2.280 moduli: 328 ms nel thread della finestra, poi 40 sottocampi riposati e un calcolo dell'anno avviato; cinque rinomine, cinque calcoli dell'anno; una modifica dell'altezza arriva alla quiete dopo 1,25 s [V prova].
- `window.py` (2.474 righe) contiene circa 700 righe di regole di dominio e di orchestrazione in 26 funzioni (la catena energetica intera in `EnergyJob._compute`, le regole di creazione, la cancellazione a cascata, l'ospite di un contorno, la politica di recupero): non si prova senza Qt e non si riusa fuori dalla finestra [V elenco in 3.4].
- L'annulla a istantanee è semplice e corretto per i progetti di oggi (0,1-2 ms per istantanea, 12-213 kB per passo) [V prova]; il suo costo vero è il ridisegno totale che segue (9 ms sul progetto piccolo, 840 ms sul grande) [V prova]. Due limiti: una modifica che solleva un'eccezione lascia il progetto cambiato senza passo di annullamento [V prova]; la pila non ha limite [V grep].
- Il file `.meridiana` non ha validazione: un file danneggiato produce `KeyError`, `TypeError`, `AttributeError` che `open_path` non intercetta (prende solo `OSError` e `ValueError`) [V prova]; un valore del tipo sbagliato accettato (latitudine testo) esplode più tardi [V prova]. Le impostazioni controllano bool, int e str ma non i float: `veil` testo fa cadere la finestra all'avvio [V prova].
- Il modello geometrico (anelli assoluti, falde calcolate sul rettangolo minimo, moduli derivati con chiavi `riga:posto`, un solo inverter in un dizionario libero) non regge i temi A, B, C e D dello studio 16 senza cambiare `model.py`, `roofs.py`, `layout.py` e `energy/system.py`: i punti in 6.
- **Verdetto**: tenere il nucleo (geometria, sole, energia, verifiche, regole, servizi, aiuti alle viste: circa 76 % delle righe), rifare per passi `model.py`, `roofs.py`, `layout.py`, `energy/system.py`, `ui/window.py` e la gestione della scena in `ui/plan.py` (circa 4.800 righe, 24 %), non sostituire nulla con una libreria. Il come, un modulo alla volta con i test verdi, in 9.

## 1. Metodo

Che cosa ho letto, per intero:
- gli 83 file `.py` di `src/meridiana` (20.190 righe con `wc -l`, 17.576 non vuote, 17.252 di codice senza le righe di solo commento) [V `A-architettura-grafo.py`] e `ui/qml/Scene.qml` (186 righe); il compito dice «78 file, circa 18.800 righe»: i numeri qui sono quelli misurati sul ramo;
- `docs/progetto.md` (sezione 2), `docs/studio/16-modellazione.md` (temi A, B, C, D e il piano), `docs/compiti/16a-16g`, le righe R12, R31, R32, R35, R36 di `docs/richieste.md`, `tests/_setup.py`, l'inizio di `tests/test_window.py`, i test delle migrazioni in `tests/test_model.py` e `tests/test_config.py`.

Che cosa ho eseguito, con il Python del programma (3.12.6, PySide6 6.12.0, numpy 2.5.4, pandas 3.0.6, Windows 11, `QT_QPA_PLATFORM=offscreen`, senza rete):
- `A-architettura-grafo.py`: il grafo delle importazioni dall'AST di ogni file (importazioni in testa e dentro le funzioni, chi importa Qt, chi importa `ui`, i cicli); l'uscita è `A-architettura-grafo.txt`;
- `A-architettura-prove.py`: il costo delle istantanee, della chiave di stato e delle chiavi di posa su tre progetti generati (1 edificio; 20 edifici con 40 sottocampi e 60 esclusioni; lo stesso con un'immagine di 4 MB sotto il disegno); il comportamento di `from_json` e di `Config.from_json` con dati danneggiati; le chiavi `riga:posto` dei moduli tolti a mano; le falde di `roofs.py` su una L; poi, con una `MainWindow` offscreen come nei test, il costo di `edit()`, di ogni pezzo di `_show_all`, dell'annulla, e che cosa fa ripartire una rinomina; l'uscita è `A-architettura-risultati.txt` (mediane di 5 esecuzioni);
- `grep` per i conteggi (test, usi di `.pitches()`, `setUndoLimit`), uno script `ast` per gli intervalli di riga delle 149 funzioni di `window.py`.

Che cosa non ho fatto: la suite dei test (6,5 minuti su Windows, non richiesta dal tema); prove con la rete o con la GPU; nessuna modifica a `src/`.

## 2. La mappa dei moduli

Righe: totali (di codice). «Importa» sono i moduli del pacchetto importati in testa al file; tra parentesi quelli importati dentro una funzione. «Da» sono i moduli che lo importano. Tutto da `A-architettura-grafo.txt` [V].

### 2.1 Nucleo: il progetto, la geometria, la posa

| Modulo | Righe | Responsabilità | Importa | Da |
|---|---|---|---|---|
| `model.py` | 466 (378) | Il progetto: sito, edifici con il tetto, sottocampi, esclusioni, moduli, varianti, immagini; il file `.meridiana` con versione e migrazioni; la posa di un sottocampo (`fill`) e la sua chiave (`layout_key`); le ombre come esclusioni (`shadow_exclusions`). | atomic, layout, roofs, sun, underlay, `meridiana` (energy.nearshade, energy.system, i18n) | pvsyst.mapping, ui.properties, ui.window, viewaids |
| `geo.py` | 160 (124) | Riferimento locale ENU su WGS84, azimut CEI 82-25, Web Mercator per i tasselli, coordinate scritte. | nessuno | energy.nearshade, energy.stringing, layout, mesh, roofs, tiles, ui.plan, ui.window |
| `sun.py` | 160 (131) | Posizione del sole (NOAA/Meeus), finestra di progetto, passo delle file (CEI 82-25/3 6.2). | nessuno | layout, model, ui.sunbar |
| `roofs.py` | 151 (118) | Le falde: piano, una falda, due falde e padiglione sul rettangolo minimo, falda libera. | geo | model |
| `layout.py` | 364 (310) | La posa dei moduli in un'area: montaggi, file, tavole, passo, regole VVF, `PlacedModule` con chiave `riga:posto`. | geo, sun | model, ui.properties |
| `mesh.py` | 303 (247) | Triangoli di edifici e prismi, nastri dei contorni, tabella delle istanze dei moduli per Qt Quick 3D. | geo | energy.nearshade, ui.view3d, ui.window, viewaids |
| `sides.py` | 59 (47) | Lunghezze dei lati, lato più vicino, stiramento di un lato come nei CAD. | i18n | ui.plan, ui.properties, ui.window |
| `snapping.py` | 255 (201) | Gli agganci del disegno: oggetti, intersezioni, direzioni, polare, orto. | nessuno | ui.plan |
| `squaring.py` | 133 (104) | Squadratura dei contorni (port di iD, ISC). | nessuno | ui.window |
| `underlay.py` | 93 (72) | Le immagini sotto il disegno: dove vanno i pixel, scala a due punti, sposta, ruota. | nessuno | model, ui.underlays, ui.window |
| `quantity.py` | 212 (180) | Quantità scritte con unità e calcoli, parser proprio senza `eval`. | i18n | ui.quantity_field, ui.window |

### 2.2 Nucleo: l'energia

| Modulo | Righe | Responsabilità | Importa | Da |
|---|---|---|---|---|
| `energy/__init__.py` | 4 (4) | Docstring del pacchetto. | nessuno | nessuno |
| `energy/simulate.py` | 633 (560) | L'anno orario con la catena delle perdite (pvlib), il pedigree di ogni passo. | components, meteo, nearshade, pedigree, i18n | consumption, system, ui.energy_pages, ui.window |
| `energy/system.py` | 104 (89) | Dal progetto al modello: campi per orientamento (`arrays_of`), ostacoli (`obstacles_of`), inverter (`inverter_of`), perdite, perdita per PVGIS. | components, nearshade, simulate, i18n | model (lazy), ui.window |
| `energy/components.py` | 245 (217) | Modulo (De Soto adattato alla scheda) e inverter per il modello. | pedigree, i18n | simulate, stringing, system |
| `energy/nearshade.py` | 418 (360) | Ombre vicine: solidi convessi, tabella sulle posizioni del sole, effetto elettrico (Martinez-Moreno), cache globale di 16 scene. | (geo, mesh) | simulate, system, model |
| `energy/stringing.py` | 302 (263) | Stringhe: intervallo in serie, verifiche CEI 64-8/7, proposta, serpentina e assegnazione. | components, pedigree, i18n, (geo) | ui.window |
| `energy/meteo.py` | 231 (198) | Anno tipo e orizzonte da PVGIS 5.3 o 6, con cache su disco. | atomic, pedigree, i18n | pvgis, simulate, ui.window |
| `energy/pvgis.py` | 65 (56) | PVcalc come secondo parere, con cache. | atomic, meteo, pedigree, i18n | ui.window |
| `energy/consumption.py` | 430 (369) | Consumi: profili sintetici, calibrazione su bollette e fasce, curve misurate, ipotesi dal contesto. | bands, pedigree, simulate, i18n | checks (lazy), ui.energy_pages, ui.window |
| `energy/economics.py` | 414 (365) | Bilancio orario con accumulo e limite di immissione, VAN, TIR, LCOE, CER, dimensionamento. | bands, pedigree, i18n | checks (lazy), ui.energy_pages, ui.window |
| `energy/bands.py` | 56 (46) | Fasce ARERA F1-F3 con le festività. | nessuno | consumption, economics, ui.energy_pages (lazy) |
| `energy/pedigree.py` | 82 (62) | Sorgente, quantità, passo, registro: la provenienza dei numeri. | i18n | 7 moduli energy, ui.pedigree, ui.window |

### 2.3 Nucleo: verifiche, regole, confronto, catalogo, PVsyst

| Modulo | Righe | Responsabilità | Importa | Da |
|---|---|---|---|---|
| `checks.py` | 301 (255) | Le voci delle verifiche da posa, ombre, stringhe, connessione, regole, importazione; segni per le viste. | rules, i18n, (energy.consumption, energy.economics) | ui.checks_page, ui.report, ui.window |
| `rules.py` | 443 (398) | Le regole (CEI 0-21, 0-16, 64-8/7, DM 37/08, DCPREV, D.Lgs. 199/2021, Lombardia) come fatti, paragrafi e fonti. | i18n | checks, ui.properties, ui.report, ui.window |
| `compare.py` | 73 (58) | Le cifre di una variante e il confronto. | i18n | ui.inspector, ui.variants, ui.window |
| `catalog/__init__.py` | 161 (134) | Il catalogo (schede lette e lista CEC), ricerca, ordinamento, record per il progetto. | nessuno | pvsyst.mapping, ui.catalog_dialog, ui.window |
| `catalog/panond.py` | 172 (154) | Lettura dei file .PAN e .OND di PVsyst. | i18n | pvsyst.mapping (lazy), ui.window (lazy) |
| `pvsyst/__init__.py` | 7 (6) | Docstring. | nessuno | nessuno |
| `pvsyst/pvobject.py` | 237 (202) | Il lettore tollerante del formato testo di PVsyst. | nessuno | pvsyst.project, pvsyst.records, ui.window (lazy) |
| `pvsyst/records.py` | 66 (52) | I record orari compatti in base 62. | pvobject | pvsyst.project |
| `pvsyst/project.py` | 369 (320) | Il progetto e le varianti di PVsyst come dati. | pvobject, records | pvsyst.mapping, ui.window (lazy) |
| `pvsyst/mapping.py` | 321 (283) | Da un progetto PVsyst a un progetto Meridiana, con ciò che è approssimato o manca. | catalog, model, project, i18n, (catalog.panond) | ui.window (lazy) |

### 2.4 Nucleo: servizi e identità dell'app

| Modulo | Righe | Responsabilità | Importa | Da |
|---|---|---|---|---|
| `__init__.py` | 24 (19) | Versione, APP_ID, nomi. La docstring parla ancora di GTK (righe 1-9) [V lettura]. | nessuno | 11 moduli |
| `__main__.py` | 35 (26) | Riga di comando, `--version`, `--help`, avvio. | i18n, (app) | nessuno |
| `app.py` | 73 (52) | La `QApplication`, le impostazioni, la finestra, il progetto da aprire, lo screenshot per i test. Qt importato dentro `main` (29-32). | (config, i18n, paths, ui.qt_translations, ui.window) | __main__ |
| `atomic.py` | 46 (39) | JSON scritto intero o per niente, `.bak`, lettura dalla copia. | nessuno | energy.meteo, energy.pvgis, model, recovery, ui.window |
| `recovery.py` | 66 (51) | Copia di recupero per progetto, revisioni `_Rnn`. | atomic | ui.window |
| `config.py` | 275 (225) | Le impostazioni con versione 8, migrazioni, tipi dei campi, salvataggio atomico con copia. | `meridiana` | app, ui.preferences, ui.window |
| `paths.py` | 83 (65) | Cartelle XDG e Windows, file spediti con il programma. | `meridiana` | app, ui.icons, ui.theme, ui.window |
| `i18n.py` | 100 (76) | gettext, lingua, numeri scritti. | `meridiana` | 48 moduli |
| `log.py` | 18 (13) | `complain`: gli errori detti su stderr. | `meridiana` | 6 moduli ui |
| `tiles.py` | 92 (75) | Sorgenti di sfondo (PCN, OSM, OpenTopoMap), zoom, tasselli, quadrilateri sul piano. | geo | ui.plan, ui.tileloader, ui.window |
| `updates.py` | 279 (222) | Aggiornamenti dalle release GitHub, con SHA-256 e firma. Non importato da nessuno nel programma [V grafo]. | minisign, i18n | nessuno |
| `minisign.py` | 136 (105) | Ed25519 e minisign con la sola libreria standard. | nessuno | updates |
| `shortcuts.py` | 214 (173) | I comandi e i tasti, i tasti da evitare, i conflitti. | i18n | ui.shortcuts_dialog, ui.window |
| `assistant.py` | 113 (85) | Meridio: SVG, posti, domande pronte. | theme_colors, (i18n) | ui.assistant, ui.preferences, ui.window |

### 2.5 Nucleo: aiuti alle viste (senza Qt)

| Modulo | Righe | Responsabilità | Importa | Da |
|---|---|---|---|---|
| `navigation.py` | 271 (233) | Gli stili del mouse come tabelle e la macchina di stati. | (i18n) | ui.plan, ui.preferences, ui.view3d |
| `camera.py` | 250 (198) | La camera del 3D: orbita, pan, zoom, viste, proiezione, animazione. | nessuno | navicube, ui.view3d |
| `navicube.py` | 129 (101) | Il cubo di vista: 26 parti, viste, frecce. | camera, (i18n) | ui.viewcube |
| `viewaids.py` | 184 (158) | Barra di scala, cosa c'è sotto il cursore, misura, contorni per il 3D. | i18n, (mesh, model) | ui.plan, ui.plan_overlays, ui.window |
| `theme_colors.py` | 377 (299) | I colori del tema da un colore scelto, in OKLCH; la palette Qt come dizionario. | (i18n) | assistant, view_colours, 7 moduli ui |
| `view_colours.py` | 67 (46) | I colori propri di pianta e 3D. | theme_colors | ui.plan, ui.view3d, ui.window |

### 2.6 Finestra (`ui/`)

| Modulo | Righe | Responsabilità | Importa (dal pacchetto) | Da |
|---|---|---|---|---|
| `ui/__init__.py` | 13 (11) | `tell`: emettere da un thread anche se la finestra è sparita. | nessuno | ui.variants, ui.window |
| `ui/window.py` | 2.474 (2.217) | Tutto: la finestra, i lavori `LayoutJob` e `EnergyJob` con la catena energetica, l'annulla, lo stato (risultati, chiavi, energia, selezione), i menu, la selezione comune, i file, il recupero, l'importazione PVsyst, il dialogo del sito con Nominatim. Importa 45 moduli del pacchetto (58 con quelli pigri) [V grafo]. | 45 (+13 pigri) | app |
| `ui/plan.py` | 1.229 (1.088) | La pianta: scena ricostruita a ogni `show_project`, disegno con gli agganci, selezione, stringhe, tasselli, marks, immagini. | geo, i18n, navigation, sides, snapping, theme_colors, tiles, view_colours, viewaids, plan_overlays, theme, tileloader (+3) | ui.window |
| `ui/view3d.py` | 494 (407) | Qt Quick 3D in un `QQuickWidget`: una geometria per gli edifici, una tabella di istanze per i moduli, il backend della camera e dei pick. | camera, mesh, navigation, view_colours (+marks, viewcube) | ui.window |
| `ui/properties.py` | 763 (673) | Il pannello Proprietà: pagine per tipo, valori legati, aggiornati senza ricostruire. | i18n, layout, model, rules, sides, quantity_field, theme | ui.energy_pages, ui.plan, ui.window |
| `ui/energy_pages.py` | 836 (766) | Le tre pagine energetiche: moduli, grafici, pedigree. | energy.consumption, economics, simulate, i18n, charts, pedigree, properties, theme (+bands) | ui.window |
| `ui/checks_page.py` | 305 (271) | Il pannello Verifiche con filtri, sottoinsiemi, Correggi. | checks, i18n, marks, theme | ui.window |
| `ui/charts.py` | 384 (336) | Grafici matplotlib con tabella, ridisegno a misura ferma. | i18n | energy_pages, pedigree, report, window |
| `ui/pedigree.py` | 122 (104) | «Come è calcolato» in HTML con le formule disegnate. | energy.pedigree, i18n, charts, theme | energy_pages, report |
| `ui/report.py` | 260 (238) | La relazione PDF (QTextDocument + QPdfWriter). | i18n, `meridiana`, charts, pedigree, theme (+checks, rules) | ui.window (lazy) |
| `ui/inspector.py` | 73 (62) | Il pannello destro che segue la scheda: proprietà o cifre. | compare, i18n | ui.window |
| `ui/variants.py` | 141 (121) | Il confronto delle varianti in un thread (`CompareJob`). | compare, i18n, log, ui, theme | ui.window (lazy) |
| `ui/catalog_dialog.py` | 297 (260) | Il catalogo a modello/proxy. | catalog, i18n, theme | ui.window |
| `ui/theme.py` | 310 (245) | Fusion, palette, foglio di stile, font, accento del sistema. | i18n, log, paths, theme_colors | 12 moduli ui |
| `ui/appearance.py` | 174 (150) | Preferenze > Aspetto con anteprima. | i18n, theme_colors, theme | ui.preferences |
| `ui/preferences.py` | 124 (107) | Il dialogo delle preferenze. | assistant, config, i18n, navigation, appearance, shortcuts_dialog | ui.window (lazy) |
| `ui/shortcuts_dialog.py` | 174 (151) | L'editor dei tasti. | i18n, shortcuts, theme | preferences, window (lazy) |
| `ui/assistant.py` | 387 (338) | Meridio flottante o agganciato. | assistant, i18n, icons | ui.window |
| `ui/icons.py` | 79 (63) | Icone Lucide ricolorate. | log, paths | ui.assistant, ui.window |
| `ui/marks.py` | 184 (149) | I segni delle verifiche: pittore, icona, delegato, item di pianta, overlay 3D. | theme_colors, theme | checks_page, plan, view3d, window |
| `ui/viewcube.py` | 226 (191) | Il cubo di vista disegnato. | i18n, navicube, theme_colors | ui.view3d (lazy) |
| `ui/viewbar.py` | 70 (57) | La barra dei comandi dentro le viste. | theme_colors | ui.window |
| `ui/plan_overlays.py` | 139 (112) | Nord, barra di scala, attribuzione. | i18n, theme_colors, viewaids | ui.plan |
| `ui/sunbar.py` | 149 (127) | Giorno, ora e animazione del sole. | i18n, sun | ui.window |
| `ui/underlays.py` | 104 (85) | Lettura di PNG, JPEG, PDF; pixmap e trasformazione. | i18n, underlay | ui.plan (lazy), ui.window |
| `ui/tileloader.py` | 114 (99) | Rete dei tasselli con cache. | log, `meridiana`, tiles | ui.plan, ui.window (lazy) |
| `ui/quantity_field.py` | 61 (49) | Il campo con unità. | i18n, quantity | ui.properties |
| `ui/wheel.py` | 57 (47) | La rotella non cambia i campi senza fuoco. | nessuno | ui.window |
| `ui/pvsyst_import.py` | 78 (66) | I due dialoghi dell'importazione PVsyst. | i18n | ui.window (lazy) |
| `ui/qt_translations.py` | 47 (38) | `qtbase_<lingua>.qm`. | log | app (lazy) |

### 2.7 Che cosa dice il grafo

- **Qt fuori da `ui/`**: solo `app.py:29-32` (`QTimer`, `QApplication`, `QLocale`), dentro `main` [V grep `^\s*(from|import)\s+(PySide6|shiboken)` e grafo]. Il nucleo è davvero senza Qt: 53 moduli su 83 non lo toccano (i 29 di `ui/` con Qt più `app.py` sono gli altri 30).
- **Il nucleo che importa `ui`**: solo `app.py` (`ui.window`, `ui.qt_translations`) [V grafo]: giusto, è il punto d'ingresso.
- **Cicli**: nessuno tra le importazioni in testa [V grafo]. Due dipendenze a due vie sono nascoste nelle importazioni pigre: `model.py:388` importa `energy.nearshade` e `energy.system` per `shadow_exclusions`, mentre `energy/system.py:21-81` legge il `Project` (`obstacle_prisms`, `pitches`, `layout_params`): il modello dipende dal pacchetto della simulazione e viceversa [V grafo e lettura]. Con `shade_free` acceso, il thread della posa importa `simulate` e quindi pandas e pvlib [I: `energy/system.py:13` importa `simulate` in testa].
- **Il centro di gravità** è `ui/window.py`: 45 moduli importati in testa, 58 con i pigri; nessun altro modulo supera i 12 [V grafo]. Il nucleo non ha un oggetto che tenga insieme progetto, risultati ed energia: lo fa la finestra (sezione 3).
- `updates.py` (e con lui `minisign.py`, che solo `updates` importa) non è importato da nessun modulo della finestra: l'aggiornatore della finestra non c'è ancora [V grafo].
- `docs/progetto.md` sezione 2 non elenca 27 moduli su 83: nel nucleo `assistant`, `atomic`, `checks`, `compare`, `config`, `i18n`, `log`, `minisign`, `paths`, `recovery`, `rules`, `sides`, `updates`, i cinque di `pvsyst/`, `app`, `__main__`; nella finestra `assistant`, `checks_page`, `preferences`, `pvsyst_import`, `qt_translations`, `quantity_field`, `shortcuts_dialog`, `sunbar`, `variants`, `wheel` [V confronto della tabella con l'elenco dei file]. La sezione 3 dice «Manca ancora il salvataggio automatico» mentre `recovery.py` e `_autosave` (window.py:2238-2248, ogni 120 s) esistono e sono provati (`test_recovery.py`) [V].

## 3. Il flusso dei dati

### 3.1 Chi possiede la verità

- Il progetto (`model.Project`) è la verità del disegno e delle impostazioni: edifici, sottocampi, esclusioni, moduli scelti, `energy`, `consumption`, `economics`, `rules`, varianti, immagini [V `model.py:183-207`].
- I **risultati non sono nel modello**: `MainWindow.results` (id del sottocampo → `layout.Result` o `Exception`), `MainWindow.layout_keys`, `MainWindow.energy` (il dizionario che `EnergyJob` restituisce: `sim`, `load`, `econ`, `strings`, `wiring`, `pvgis`, `sizing`, `storage`, `shade_free_counts`, `context`, `notes`, `error_sim`), la selezione (`selection`, `selected_module`, `hovered_3d`), la tabella di picking del 3D (`module_index`) vivono nella finestra [V `window.py:405-412, 460-461`]. Ogni cosa che legge i risultati (verifiche, relazione, confronto, proprietà, misure) deve passare dalla finestra, e il confronto delle varianti deve istanziare `LayoutJob` ed `EnergyJob` per calcolare una variante fuori dallo schermo (`_variant_figures`, 1242-1257) [V].
- Le viste tengono copie: la pianta `drawn = (project, results)`, `rings`, `module_shapes` (254-336); il 3D la geometria caricata; Proprietà `shown` con l'oggetto e il risultato [V].

### 3.2 Come si propagano le modifiche

```
gesto (pianta, proprietà, menu, verifiche)
  -> MainWindow._edited / _drawn / _delete / _action / ...   (regole di dominio qui)
  -> edit(text, change, merge)                             window.py:1177
       before = snapshot(); change(project); after = snapshot()
       before != after  -> undo.push(Snapshot)
       _show_all()                                          window.py:1564
           plan.show_project(project, results di prima)     scena rifatta intera (plan.py:254)
           _show_variants, _show_tree, _show_properties, _show_measure, _title (dirty), _show_energy_forms
           relayout_timer 150 ms -> _start_layout            window.py:1578
  -> LayoutJob (thread, copia del progetto da JSON)         window.py:94
       per ogni sottocampo filled: chiave = layout_key; uguale alla precedente -> risultato tenuto; altrimenti fill()
  -> _layout_done (thread della finestra)                   window.py:1585
       results, layout_keys; plan.show_project; _show_tree; _show_properties; _show_measure; _show_3d;
       _show_energy_forms; energy_timer 500 ms se la scheda non è il Modello o se energy non è vuoto; _show_checks
  -> EnergyJob (thread, copia del progetto da JSON + results)  window.py:134
       _compute: meteo, arrays_of, consumi, simulate, stringhe, wiring, simulate di nuovo con le stringhe,
       conteggi fuori ombra, PVGIS, economia, dimensionamenti
  -> _energy_done                                           window.py:1812
       pagine, wiring sulla pianta, ispettore, _show_checks -> _show_marks (pianta, 3D, albero, barra di stato)
```

Letto nel codice [V]. Le prove dicono che cosa costa (sezione 4 e `A-architettura-risultati.txt`).

### 3.3 Coerenza tra pianta, 3D, Proprietà e Verifiche

- La pianta è ridisegnata subito a ogni `edit()` con i **risultati vecchi** (i moduli della posa precedente sopra il contorno nuovo), il 3D, le verifiche e i segni solo al ritorno della posa: `_show_all` non chiama `_show_3d` né `_show_checks` [V `window.py:1564-1576`; prova: dopo una modifica dell'altezza la pianta mostra 12 m subito, il 3D dopo `_layout_done`, 190 ms sul progetto piccolo e 1.246 ms sul grande].
- Le pagine dell'energia tengono i valori vecchi finché torna l'anno nuovo, senza segno (P7 dello studio 12, F1 dello studio 16) [V `_energy_done` è l'unico punto che le aggiorna]. L'annulla non azzera `self.energy`: dopo un Ctrl+Z l'ispettore dei risultati mostra le cifre di prima finché il ricalcolo non è finito [I da `restore`, 1172-1175].
- Le stringhe sulla pianta sono disegnate solo se i moduli su cui furono calcolate sono ancora tutti lì (`plan.py:362-364`): coerente, ma spariscono a ogni posa finché l'energia non torna (2-4 s sul progetto di Daniel, R31) [V lettura].
- Proprietà: aggiornate sul posto, ricostruite solo se cambia la forma (`properties.py:198-203, 566-567`): la parte meglio pensata del flusso [V].
- Il 3D sceglie «quello che la pianta sceglierebbe»: `_point_picked_3d` e `_hover_3d` chiamano `self.plan._pick` (1390, 1685) e `_view3d_menu` legge `self.view3d.backend._press` (1957): la selezione è una, ma passando da membri privati di un'altra vista [V].
- La chiave di posa non entra nel file: alla riapertura tutto è «da posare» e si ricalcola [V `layout_state`, 371-379].

### 3.4 La logica di dominio dentro `window.py`

Le funzioni che contengono regole, scelte di dominio o l'orchestrazione dei calcoli (intervalli dallo script `ast`) [V]:

| Funzione | Righe | Che cosa decide |
|---|---|---|
| `EnergyJob._compute` | 154-250 (97) | Tutta la catena: cache meteo, `arrays_of`, consumi dal contesto, orizzonte, inverter, `simulate`, stringhe, `assign`, seconda simulazione con le stringhe, conteggi fuori ombra, PVGIS per campo, degrado, economia, dimensionamenti, batteria. |
| `EnergyJob._strings` | 254-283 (30) | Tmin predefinita -10 °C, il modulo «più usato», i moduli divisi per il numero di inverter, proposta o piano. |
| `set_path` | 286-294 (9) | La scrittura per percorso nei dizionari `energy`, `consumption`, `economics`: un percorso sbagliato crea una chiave nuova in silenzio. |
| `SiteDialog._search`, `_found` | 336-385 (49) | Il geocoding con Nominatim (rete, limite di una richiesta al secondo, `countrycodes=it`). |
| `_square` | 964-988 (25) | Quale attributo squadrare per tipo di oggetto. |
| `_import_image` | 1040-1057 (18) | L'immagine larga 0,8 della vista, al centro. |
| `_fit` | 1147-1165 (19) | Il raggio dell'inquadratura 3D (`max(dx, dy) / 2 · 1,2 + 2`). |
| `_variant_figures` | 1242-1257 (16) | Come si calcola una variante fuori dalla finestra: istanziando i lavori. |
| `_host` | 1269-1278 (10) | A quale edificio e falda appartiene un contorno (punto rappresentativo, `buffer(1e-6)`). |
| `_drawn` | 1280-1329 (50) | I predefiniti di creazione: altezza 6 m, montaggio coplanare se la falda è inclinata altrimenti file inclinate, a terra senza edificio; esclusione «lucernario»; falda libera a 15°, che trasforma il tetto in «free». |
| `_centre_3d` | 1352-1363 (12) | Il centro di un oggetto per il perno (media dei vertici, quota dell'edificio). |
| `_delete` | 1421-1446 (26) | La cancellazione a cascata (sottocampi ed esclusioni dell'edificio), il modulo tolto in `removed`. |
| `_edited`, `_merge_key` | 1450-1481 (30) | Come un percorso di campo cambia l'oggetto (`params.azimuth` None toglie la chiave), quali modifiche si fondono nell'annulla. |
| `_action` | 1483-1499 (17) | «Posa» azzera `removed`. |
| `_vertex_moved` | 1535-1547 (13) | Un contorno che si incrocia o sparisce è rifiutato (`is_valid`, area 0,5). |
| `_find_site` | 1549-1560 (12) | Il sito si sposta solo prima di disegnare. |
| `_show_3d` | 1607-1661 (55) | Il montaggio della scena: colori per selezione, tabella dei moduli e `module_index`, sole. |
| `_show_energy_forms` | 1769-1782 (14) | Il contesto dei consumi legato alla produzione solo se la potenza coincide. |
| `_show_checks`, `_rules_facts` | 1834-1846, 2035-2043 (22) | Che cosa dare a `checks.gather` e a `rules.facts`. |
| `_choose_module`, `_import_pvsyst` | 2083-2128 (45) | Gli id dei moduli nel progetto (`cur:…`, `pan:nome`), l'inverter importato in `energy`. |
| `_import_pvsyst_project` | 2130-2187 (58) | L'orchestrazione dell'importazione. |
| `_import_curve` | 2189-2201 (13) | Una curva importata toglie le bollette mensili. |
| `_state_key` | 2217-2224 (8) | Che cosa conta come «modificato» (l'immagine per lunghezza ed estremi). |
| `_autosave`, `_drop_autosave`, `offer_recovery` | 2238-2285 (47) | La politica del recupero. |

Circa 700 righe su 2.474 (28 %) in 26 funzioni [V somma degli intervalli]. Il resto della finestra è davvero finestra (menu, dock, azioni, cablaggio dei segnali: `__init__` 199 righe e `_actions` 212 righe).

### 3.5 I thread

- `LayoutJob` ed `EnergyJob` lavorano su una copia del progetto ricostruita dal JSON (`window.py:1580, 1803`); i risultati tornano con una generazione e quelli vecchi sono scartati (1586, 1813); `tell` (ui/__init__.py:6-13) ignora la finestra già distrutta [V]. Il modello dei thread è sano.
- Il costo nascosto: `EnergyJob` riceve anche i `Result` delle pose (oggetti condivisi, letti soltanto) e `nearshade._CACHE` è un dizionario globale protetto da lock (nearshade.py:285-310) [V]: va bene finché c'è una finestra sola.
- `CompareJob` (ui/variants.py:38-52) esegue `LayoutJob.run()` ed `EnergyJob._compute()` nel suo thread, in serie [V]: la via per calcolare «fuori dalla finestra» esiste già, ma passa dalle classi della finestra.

## 4. L'annulla

### 4.1 Come funziona

`Snapshot(QUndoCommand)` tiene il progetto come JSON prima e dopo (`window.py:55-87`); `edit()` (1177-1185) prende `before = snapshot()`, applica `change(project)`, prende `after`, confronta i due dizionari e spinge il comando solo se differiscono; `redo` salta la prima volta; `undo` e `redo` chiamano `restore(data)` (1172-1175): `Project.from_json(deepcopy(data))`, `props.drop_typing()`, `_show_all()`. Le modifiche numeriche con la stessa chiave entro 2 s si fondono (`mergeWith`, 74-78); l'`id` del comando è `hash(merge) & 0x7FFFFFFF` (71-72). La chiave di stato `_state_key` (2217-2224) decide il «modificato» confrontando il JSON senza `modified` e con l'immagine ridotta a lunghezza ed estremi [V lettura].

### 4.2 Il costo, misurato

Progetti generati, mediane di 5 (`A-architettura-risultati.txt`) [V]:

| | 1 edificio, 1 sottocampo (JSON 2 kB) | 20 edifici, 40 sottocampi, 60 esclusioni (25 kB) | lo stesso con un'immagine di 4 MB (5,5 MB) |
|---|---|---|---|
| `snapshot()` (`edit` ne fa due) | 0,10 ms | 1,5 ms | 2,0 ms |
| `before != after` | 0,00 ms | 0,02 ms | 0,02 ms |
| `restore` (solo `from_json`) | 0,10 ms | 1,3 ms | 1,3 ms |
| `_state_key` (JSON intero, non ridotto) | 0,07 ms | 0,9 ms | 15 ms |
| memoria di un passo (prima + dopo) | 12 kB | 213 kB | 211 kB |
| `edit()` di un nome nella finestra | 6 ms | 328 ms | non misurato |
| `undo.undo()` nella finestra | 9 ms | 840 ms | non misurato |

L'immagine non pesa sull'annulla: le stringhe base64 sono immutabili e `deepcopy` le condivide (2,0 ms con 5,5 MB) [V]. Ciò che costa è il ridisegno totale (`_show_all` più la posa e i ridisegni di `_layout_done`), non l'istantanea: la stessa rinomina costa 6 ms su un edificio e 328 ms su venti, e l'annulla 840 ms [V].

### 4.3 I limiti

1. **Nessun ripristino se `change` solleva**: il progetto resta cambiato, senza passo di annullamento e senza ridisegno (`edit()`, 1181-1185, non ha `try`). Prova: una `change` che aggiunge un edificio e poi divide per zero lascia 21 edifici con la pila a 5 passi come prima e il progetto «modificato» [V prova]. Oggi le `change` sono quasi tutte innocue, ma `p.duplicate` (`ValueError`), `p.remove_variant`, `p.switch_variant` (`StopIteration`, `KeyError` su un file a mano) possono sollevare.
2. **I risultati non fanno parte dell'istantanea**: un annulla riporta il progetto ma lascia `results`, `layout_keys`, `energy` come sono; la coerenza torna solo con la posa (le chiavi cambiate) e con il ricalcolo dell'energia, che parte sempre (sezione 7, difetto 1) [V].
3. **Modifiche a vuoto ridisegnano tutto**: `edit()` chiama `_show_all()` anche quando `before == after` (1185) [V lettura].
4. La pila non ha limite (`setUndoLimit` mai chiamato) [V grep]: a 213 kB per passo servono 5.000 passi per 1 GB; non è un problema oggi, lo diventa con i moduli espliciti del tema C (4.682 moduli × 6 numeri per passo).
5. L'`id` del comando da un `hash` troncato a 31 bit: una collisione tra due chiavi diverse fonderebbe passi di oggetti diversi; improbabile, ma gratuito da evitare con una tabella chiave → id [I].
6. `Snapshot` tiene un riferimento alla finestra; `restore` rilancia `from_json` e quindi le migrazioni (a vuoto, perché il JSON è della versione corrente) [V lettura].
7. La selezione, la vista e la scheda non sono nell'istantanea: dopo l'annulla di «Disegna un edificio» la selezione punta a un id che non c'è e le Proprietà tornano al sito [I da `_show_properties`, 1753-1765].

Il disegno a istantanee va tenuto: è esatto, costa poco e copre ogni modifica senza scrivere un comando per ognuna. Quello che va cambiato è intorno: il ripristino in caso di errore, i risultati invalidati per chiave e non ricalcolati tutti, il ridisegno per argomento.

## 5. Il formato del file, le impostazioni, lo stato della finestra, le scritture atomiche

### 5.1 Il file `.meridiana`

- `FORMAT_VERSION = 6` (`model.py:27`), `MIGRATIONS` da 1 a 5 (33-35): 1→2, 2→3 e 4→5 sono identità (i campi nuovi hanno un predefinito nella dataclass), 3→4 aggiunge le varianti, 5→6 le immagini [V]. Le migrazioni provate nei test: dalla versione 1 e dalla 3 (`test_model.py:67, 127`) [V grep]; non c'è un file di prova per versione in `tests/fixtures` (solo `sun_reference.json`) [V ls].
- `to_json` è `asdict` più `format`, `version`, `app_version` (416-421); `app_version` non è mai letto [V grep]. `from_json` (423-457) filtra i campi sconosciuti (`_build`, 178-180) e ricostruisce le dataclass **senza controllare i tipi**: le prove danno [V]:
  - senza la chiave `version`: `KeyError: 0` (427: `data.get("version", 0)` poi `MIGRATIONS[0]` a 431);
  - un edificio senza `name` e `footprint`: `TypeError` dal costruttore;
  - `buildings` dizionario invece di lista: `AttributeError`;
  - un sottocampo con `ring` numero: accettato, poi `TypeError` nella posa; la latitudine testo: accettata, poi `ValueError` nel calcolo;
  - `open_path` (2337-2343) intercetta solo `OSError` e `ValueError`: `KeyError`, `TypeError`, `AttributeError` escono dallo slot, il progetto non si apre e nessun messaggio lo dice (PySide stampa il traceback su stderr) [V prova + I sul comportamento dello slot]. `offer_recovery` (2274) prende anche `KeyError` e `TypeError`, non `AttributeError` [V lettura].
- Le varianti: il disegno della variante in mano sta nei campi del `Project`, quelli delle altre in `variants[i]["design"]` come JSON annidato (262-290): due rappresentazioni dello stesso tipo di dato, e `switch_variant` fa `target.pop("design")`, `KeyError` se un file a mano ne è privo [V lettura]. `energy["thermal"]` è per id di sottocampo, e gli id (`s1`, `s2`) si ripetono tra varianti: coerente finché il disegno è per variante, da ricordare quando le stringhe (16d) citeranno i moduli per chiave.
- L'immagine sotto il disegno sta nel file in base64: un PNG di 4 MB fa un file di 5,5 MB con `indent=1`, più `.bak` e la copia di recupero (tre copie su disco) [V misura del JSON; I per le copie]. È una scelta dichiarata (R21: il file intero su un altro PC) e va bene; il limite di 4.096 px (`underlay.MAX_SIDE`) la tiene a bada.
- I dizionari liberi `energy`, `consumption`, `economics`, `rules`, `modules` sono scritti da `set_path` senza schema: `Losses.from_dict` e `Settings.from_dict` ignorano le chiavi sconosciute (`hasattr`), quindi un errore di percorso non si vede mai [V lettura `simulate.py:70-76`, `economics.py:82-91`].

### 5.2 Le impostazioni (`config.py`)

- `CONFIG_VERSION = 8`, sette migrazioni ognuna provata (`test_config.py:97-162`) [V]. Le migrazioni aggiungono un valore predefinito che `from_json` darebbe comunque: il numero di versione documenta la storia più che cambiare i dati [I].
- `_typed` (120-140) controlla bool, int, str e il dizionario dei tasti; **non i float**: `veil` «forty percent» è accettato [V prova], e `plan.set_veil` (window.py:579 → `plan.py:207`, `float(strength)`) solleva alla costruzione della finestra [I lettura; la prova lo mostra su `view_colours.veil`, che solleva `TypeError`]. Il file resta accettato perché `Damaged` scatta solo in `_read`; il programma cade all'avvio finché il file non è corretto a mano.
- `save` atomico con la copia come hard link o copia (242-275), `load` con le quattro situazioni e le `notices` [V lettura; `test_config.py:38-75`].

### 5.3 Lo stato della finestra e le scritture atomiche

- `window.json` (geometria, stato dei dock, split, vista, posti dell'assistente) scritto con `atomic.write_json(keep_backup=False)` e letto con tolleranza (`_restore_window`, 2436-2454) [V].
- `atomic.write_json` (17-33): file temporaneo nella stessa cartella, `fsync`, copia del precedente in `.bak` con `copy2`, `os.replace`; se la copia fallisce il salvataggio fallisce (giusto: mai senza copia). Manca l'`fsync` della cartella su POSIX (il rinomino può restare nel buffer) [I]. `read_json` (36-46) torna alla copia dicendolo [V `test_model.py:55-58`].
- Il recupero (`recovery.py`): uno slot per file (sha1 del percorso) e uno per «nuovo»; copia ogni 120 s se c'è qualcosa da salvare; tolta al salvataggio e alla chiusura; offerta all'avvio [V lettura]. Un'immagine di 4 MB fa 15 ms di JSON a ogni copia, nel thread della finestra [V misura di `json.dumps`]: sostenibile.

### 5.4 Che cosa manca

1. Una validazione del file che dica dove sta l'errore (`buildings[2].footprint: non è una lista di punti`) e sollevi `ValueError`, così che `open_path` la mostri; oggi la promessa della docstring di `model.py` («refused rather than half read») vale solo per la versione.
2. Un file di prova per ogni versione del formato in `tests/fixtures`, aperto e confrontato campo per campo (le migrazioni 5→6 e 4→5 non hanno test propri; 16a aggiungerà la 6→7 con un cambio di significato).
3. Il controllo dei float in `_typed`.
4. Uno schema per `energy`, `consumption`, `economics` (dataclass con `from_dict` che rifiuta le chiavi ignote, o almeno le dica).
5. I risultati nel file, come PVsyst: oggi aprire un progetto vuol dire riposare e ricalcolare tutto prima di vedere un numero (sezione 3.3).

## 6. Il modello geometrico di oggi contro lo studio 16

Oggi [V lettura]: `Building` ha un anello assoluto, un'altezza di gronda e un `Roof(type, eave_side, ridge_along, tilt, free_pitches)` dove `free_pitches` è una lista di dizionari grezzi senza id; le falde sono **calcolate a ogni chiamata** di `pitches()` (12 punti di chiamata in 5 moduli, nessuna cache) [V grep]; `SubField` ha un anello assoluto, l'id dell'edificio e l'**indice** della falda, l'id del modulo, `params` libero, `filled`, `removed`; `ExclusionItem` un anello assoluto, il tipo, la distanza, l'edificio, l'altezza; i moduli esistono solo in `layout.Result` con la chiave `riga:posto[:livello]`; il 3D è una geometria sola più una tabella di istanze.

| Studio 16 chiede | Il modello di oggi | Perché non regge |
|---|---|---|
| **A. Tetti a falde su piante qualsiasi** con colmo quotato e testate per lato | `roofs.gable` e `hip` costruiscono sul rettangolo minimo (`roofs.py:55-60, 109-146`); su una L di 240 m² le due falde coprono 360 m², 120 fuori dalla pianta, e nell'angolo interno il tetto sta a 8,9 m con la gronda a 6 m: nessun compluvio [V prova]. `Roof` non ha attributi per lato (16a vuole `edges` e `ridge_height`). | Il modello del tetto è «un tipo e due numeri», non «un lato e i suoi attributi». `SubField.pitch` è un indice in una lista la cui lunghezza cambia con il tipo (piano 1, due falde 2, padiglione 4, libere n): cambiando tipo l'indice punta a un'altra falda e `surface_of` ripiega su `pitches[0]` in silenzio (`model.py:318`) [V lettura]. Con lo scheletro le falde saranno una per lato di gronda: l'indice va sostituito da un riferimento stabile («lato n») e il rimappamento alla migrazione (previsto in 16a) è obbligato. |
| **B. Sposta e ruota** in pianta e nel 3D, con ciò che appartiene all'oggetto | Nessuna trasformazione di oggetti; `duplicate` sposta solo l'oggetto copiato, non i sottocampi e le esclusioni dell'edificio (`model.py:231-258`) [V]; l'appartenenza (`building`, `pitch`) è decisa una volta al disegno da `_host` (window.py:1269-1278) e mai ricontrollata. | Gli anelli sono assoluti e sconnessi: spostare un edificio è spostare tre liste e ricalcolare l'ospite di ciascuna. Serve il `move.py` di 16b, ma anche un posto dove vivano le relazioni (sottocampi di un edificio, esclusioni di un edificio) con un metodo solo. Nel 3D non ci sono nodi per oggetto: la scena è una mesh e una tabella (`view3d.py:414-425`); l'anteprima di un trascinamento richiede un nodo a parte, perché rifare la scena costa 40 ms a fotogramma su 2.280 moduli [V misura di `_show_3d`]. |
| **C. Posa manuale, file, esplosione** | I moduli sono derivati (`layout.compute`, 364 righe in una funzione di 170); l'unica correzione a mano è `removed` con chiavi `riga:posto`; cambiando il passo tra i moduli da 2 a 10 cm la chiave `0:7` passa a un modulo spostato di 0,83 m: il buco si sposta con la chiave [V prova]. Le stringhe (`stringing.serpentine`) e le ombre (`nearshade` per `pm.key`) leggono le stesse chiavi. | Non c'è un oggetto «fila» né un id stabile di modulo. 16c propone `Row` in `layout.py` e `SubField.rows`, `manual`: giusto, ma il generatore va spezzato (geometria delle file, riempimento, gruppi VVF come verifica) e le chiavi devono diventare id. Anche l'annulla a istantanee deve restare sostenibile con i moduli espliciti: 4.682 moduli × 6 numeri = circa 200 kB per istantanea, accettabile, ma le istantanee cominceranno a pesare quanto il progetto. |
| **D. Inverter multipli, MPPT, editor delle stringhe, modalità di stringatura (R12)** | Un solo record `energy["inverter"]` con `inverter_count`, `strings = {n_series, per_mppt}` (`system.inverter_of`, 84-91; `EnergyJob._strings`, 254-283); l'assegnazione (`assign`) è ricalcolata a ogni anno e mai salvata; le verifiche delle stringhe esistono solo dopo la simulazione, perché `t_cell_max` viene da lì [V]. | Non c'è un oggetto «impianto»: inverter, ingressi, stringhe. 16d lo mette in `energy["inverters"]` e `energy["strings"]["runs"]` dentro il dizionario libero: funziona, ma sarebbe il quarto dizionario senza schema. Meglio un `Plant` tipizzato nel modello, con le stringhe come liste di id di modulo (quindi dopo C) e le verifiche in diretta calcolate dal nucleo su condizioni di progetto (già previsto). |

In più, trasversale: i dizionari `params`, `energy`, `consumption`, `economics`, `rules`, `modules` non hanno tipi; `layout_params()` fa `setattr` di qualunque valore (`model.py:155-162`); l'id del modulo nel progetto è una stringa composta in tre modi diversi (`cur:…`, `pan:nome`, `generic-450`) decisa nella finestra (window.py:2087, 2120) e in `pvsyst/mapping.py:79, 86, 93` [V].

## 7. I difetti, in ordine di gravità

1. **Ogni modifica riposa tutto e ricalcola l'anno** (gravità alta: tempo e valori vecchi). `Project.layout_key` (`model.py:361-369`) serializza `asdict` di ogni edificio e ogni esclusione: il nome, la categoria antincendio, il parapetto, tutto; `_layout_done` (`window.py:1596-1597`) fa ripartire `energy_timer` ogni volta che `energy` non è vuoto. Caso: rinominare un edificio su 20 edifici e 40 sottocampi riposa 40 sottocampi e avvia un calcolo dell'anno; cinque rinomine, cinque calcoli [V prova]; sul progetto di Daniel ogni calcolo dura 3,55 s (R31). Un edificio rinominato cambia la chiave di un sottocampo su un altro edificio, e così la sua categoria antincendio [V prova].
2. **Nessun aggiornamento incrementale delle viste** (gravità alta). `_show_all` e `_layout_done` rifanno pianta (scena cancellata e ricreata, `plan.py:263-266`), albero, proprietà, pagine, 3D, verifiche a ogni modifica: 328 ms nel thread della finestra per una rinomina, 1,25 s fino alla quiete per un'altezza, sul progetto grande [V]. Dentro: `_show_tree` 160 ms (nel profilo, con il suo sovraccarico, 234 ms di cui 143 in `_mark_tree`: 31.793 chiamate a `MarkDelegate.sizeHint` per 124 righe, perché ogni `setData` fa rimisurare la colonna a `ResizeToContents`; e 85 ms di `layout_key`) [V profilo]; `_show_energy_forms` 148 ms e `_show_checks` 100 ms, nel profilo per l'80 % dentro `system.arrays_of` → `obstacles_of` → `project.obstacle_prisms()` rifatto per ognuno dei 40 sottocampi (2.400 `roof_z` con `Point` e `Polygon` di shapely) [V profilo]; `_rules_facts` (`window.py:2035-2043`) lo rifà ancora quando si copiano le note o si esporta la relazione [V lettura].
3. **`edit()` senza ripristino** (`window.py:1177-1185`): il progetto resta a metà senza passo di annullamento [V prova, sezione 4.3].
4. **File di progetto senza validazione** (`model.py:423-457`) e `open_path` che intercetta solo `OSError` e `ValueError` (`window.py:2340`): un file danneggiato produce eccezioni non dette [V prova, sezione 5.1].
5. **Le regole di dominio nella finestra** (sezione 3.4, circa 700 righe): la catena energetica (`EnergyJob._compute`) si prova solo passando dalla finestra o istanziando `EnergyJob` (come fa `_variant_figures`); i predefiniti di creazione, la cascata della cancellazione, l'ospite di un contorno non hanno un test del nucleo [V lettura; `test_window.py` li prova con una finestra vera, 59 test].
6. **Riferimenti fragili nel modello**: `SubField.pitch` indice (`model.py:149, 318`), `removed` con chiavi di posizione (`layout.py:123-125, 337-339`), `module_index` del 3D rifatto a ogni `_show_3d` (`window.py:1640, 1654`), `energy["thermal"]` per id di sottocampo [V lettura; prova per `removed`].
7. **`config._typed` non controlla i float** (`config.py:131`): `veil` testo fa cadere la finestra all'avvio (`window.py:579`) [V prova].
8. **Le falde sul rettangolo minimo** (`roofs.py:55-60`): 120 m² di tetto fuori da una L, nessun compluvio [V prova]; già deciso in 16a.
9. **Due rappresentazioni delle varianti** e `switch_variant` che fa `pop("design")` (`model.py:283-290`): `KeyError` su un file a mano senza `design` [I]; `_switch_variant` azzera `results` ed `energy` prima dell'`edit` (`window.py:1204-1205`), ma l'annulla dello scambio non li azzera [I].
10. **Il 3D e le verifiche in ritardo sulla pianta** (`_show_all`, 1564-1576, non chiama `_show_3d` né `_show_checks`): dopo una modifica d'altezza la pianta è nuova e il 3D vecchio per 150 ms più la posa [V prova].
11. **Accoppiamenti privati tra viste**: `self.plan._pick` usato per il 3D (`window.py:1390, 1685, 1962`), `self.view3d.backend._press` letto dalla finestra (1957) [V].
12. **Il modello importa la simulazione**: `model.py:388` → `energy.system`/`energy.nearshade`; con `shade_free` il thread della posa carica pandas e pvlib [V grafo; I sul caricamento].
13. **Documentazione fuori fase**: la docstring di `__init__.py` descrive un'app GTK; `progetto.md` sezione 2 manca di 27 moduli e la sezione 3 dice che il salvataggio automatico manca [V].
14. **Minori**: `set_path` crea chiavi ignote in silenzio (`window.py:286-294`); `app_version` scritto e mai letto; `Snapshot.id` da `hash` a 31 bit; nessun limite alla pila; `_import_image` e `_fit` con costanti di dominio nella finestra [V lettura].

## 8. Il verdetto per modulo

**Tieni** = resta com'è o con ritocchi; **rifai** = nuova struttura al suo posto, per passi, con i test portati; **sostituisci** = una libreria o un altro modulo al posto suo. Nessun modulo va sostituito: dove una libreria esiste (CGAL per lo scheletro, una libreria minisign) le decisioni prese la escludono con ragione.

| Modulo | Verdetto | Motivo e prova |
|---|---|---|
| `geo`, `sun`, `sides`, `snapping`, `squaring`, `underlay`, `quantity`, `shortcuts`, `navigation`, `camera`, `navicube`, `viewaids`, `theme_colors`, `view_colours`, `assistant`, `tiles` | tieni | Puri, piccoli, con test propri (da 4 a 23 ciascuno) [V conteggio]; `tiles` cresce con R36 (sorgenti configurabili) senza cambiare forma. |
| `model.py` | rifai (per passi, stessa API) | Riferimenti per indice e per chiave di posizione, dizionari senza schema, nessuna validazione, chiave di posa che serializza tutto, due rappresentazioni delle varianti, dipendenza dalla simulazione (difetti 1, 4, 6, 9, 12). Le prove di 5.1 e di `layout_key`. |
| `roofs.py` | rifai | Rettangolo minimo (prova della L); il compito 16a lo prevede con `skeleton.py`. |
| `layout.py` | rifai (il generatore in parti) | `compute` di 170 righe con geometria, riempimento, gruppi VVF e chiavi insieme; le chiavi `riga:posto` (prova dello spostamento di 0,83 m); 16c chiede le file come oggetti. I 20 test di oggi restano la rete di protezione. |
| `mesh.py` | tieni | Puro e provato (13 test); gli manca solo la geometria per nodo (gizmo, anteprima) da aggiungere. |
| `energy/simulate`, `components`, `nearshade`, `stringing`, `meteo`, `pvgis`, `consumption`, `economics`, `bands`, `pedigree` | tieni (per l'architettura; i numeri li giudica il tema B) | Senza Qt, con il pedigree, con test (da 3 a 23 ciascuno); la cache globale di `nearshade` va passata come oggetto quando ci sarà una sessione. |
| `energy/system.py` | rifai | È il punto dove il progetto diventa «impianto»: un solo inverter, `obstacles_of` rifatto per sottocampo (prova del profilo), nessun oggetto per inverter e ingressi (16d). |
| `checks.py`, `rules.py`, `compare.py` | tieni | Puri; prendono progetto, risultati ed energia come argomenti: pronti per una sessione. Il contenuto delle regole lo verifica il tema B in locale. |
| `catalog/`, `pvsyst/` | tieni | Letti e provati (9, 5, 13 test); 16e aggiunge campi al catalogo senza cambiarne la forma. |
| `atomic`, `recovery`, `config`, `paths`, `i18n`, `log`, `updates`, `minisign`, `app`, `__main__` | tieni | Piccoli e provati; `config._typed` da correggere per i float; `updates` entra in gioco con il tema H. |
| `ui/window.py` | rifai (spezzandolo) | 2.474 righe, 45 moduli importati, 700 righe di dominio, possiede la verità dei risultati, nessun aggiornamento per argomento (difetti 1, 2, 3, 5, 10, 11). |
| `ui/plan.py` | rifai la scena, tieni i gesti | `show_project` cancella e ricrea tutti gli item (20-42 ms sul progetto grande, a ogni modifica) [V]; il disegno con gli agganci, i pick, le quote, i marks sono buoni e provati (11 + 7 + 10 test). |
| `ui/view3d.py` | tieni | Il backend con la camera del nucleo e i bindings è la lezione pagata; mancano i nodi per oggetto (16b, 16g). |
| `ui/properties.py` | tieni | L'aggiornamento sul posto con i `_bind` è il modello da seguire per le altre viste. |
| `ui/energy_pages.py`, `charts.py`, `pedigree.py`, `report.py`, `inspector.py`, `variants.py`, `checks_page.py`, `catalog_dialog.py` | tieni (l'interfaccia la giudica il tema E) | Mostrano e raccolgono; `energy_pages.show_project` ricostruisce le righe termiche a ogni chiamata (`energy_pages.py:312-322`), da legare come le Proprietà. |
| `ui/theme`, `appearance`, `icons`, `marks`, `viewcube`, `viewbar`, `plan_overlays`, `sunbar`, `underlays`, `tileloader`, `wheel`, `quantity_field`, `shortcuts_dialog`, `preferences`, `pvsyst_import`, `qt_translations`, `assistant` | tieni | Moduli di una cosa sola, provati; `marks.MarkDelegate` con `ResizeToContents` è la causa dei 143 ms dell'albero (difetto 2), da correggere nella colonna, non nel modulo. |

In righe: da rifare `window.py` 2.474, `plan.py` 1.229 (metà), `model.py` 466, `layout.py` 364, `roofs.py` 151, `energy/system.py` 104: 4.788 righe, il 24 % di 20.190; da tenere il resto, 76 %; da sostituire 0 [V somma].

## 9. L'architettura obiettivo

### 9.1 I livelli e i confini

```
ui/                 finestra, viste, dialoghi: mostrano la sessione e riportano i gesti; Qt solo qui
  window.py (cablaggio, < 600 righe)  plan/  view3d/  properties  pages  checks_page  ...
session/            Qt-free: la verità viva del lavoro e la sua propagazione
  ProjectSession: project + results + energy + selection; edit(command) con l'annulla a istantanee;
                  chiavi per oggetto; invalidazione; eventi per argomento; i lavori come funzioni
  jobs.py: layout_of(project, known) e energy_of(project, results, cache, fetch) come funzioni pure;
           JobRunner: un protocollo; l'implementazione con QThreadPool sta in ui/
core/               il dominio, puro
  model (tipizzato, validato, con id stabili e relazioni), geometry (geo, roofs+skeleton, layout rows, mesh, sides,
  snapping, squaring, underlay), energy/ (pipeline.py in più), checks, rules, compare, quantity, sun
io/                 atomic, recovery, config, project file (schema + migrazioni con fixture per versione)
services/           meteo, pvgis, tiles, geocoding: interfacce senza Qt; la rete Qt (tileloader, Nominatim) in ui/
```

Regole: `core` non importa `session` né `ui`; `session` non importa Qt; `energy` non legge il `Project` (riceve un `PlantSpec` costruito dalla sessione: oggi `system.py` lo legge); una vista si aggiorna per argomento (`project:geometry`, `layout:<id>`, `energy`, `selection`, `checks`), mai «tutto».

### 9.2 Che cosa cambia nei dati

- `Building` con id, anello, `Roof(edges per lato, ridge_height, free_pitches con id)` e una cache delle falde invalidata dalla chiave di geometria.
- `SubField.pitch` → riferimento al lato di gronda; `rows` e `manual` (16c); `removed` → id di modulo.
- `Plant` tipizzato: inverter con ingressi, stringhe come liste di id di modulo, condizioni di progetto (16d); `EnergySettings`, `ConsumptionSettings`, `EconomicsSettings` dataclass con `from_dict` che dice le chiavi ignote.
- Chiavi per oggetto: `geometry_key(building)` (anello, altezza, tetto, parapetto), `layout_key(sf)` = campi del sottocampo + chiave di geometria dell'edificio ospite + esclusioni dell'ospite + sito + finestra + **le chiavi di geometria di tutti gli edifici solo se `shade_free`**; `energy_key` = chiavi di posa + `energy` + `consumption` + `economics`: così una rinomina non muove nulla e un'altezza riposa solo i sottocampi di quell'edificio.
- I risultati salvati nel file con la loro chiave (facoltativo, come PVsyst): alla riapertura si mostra e non si ricalcola.

### 9.3 La migrazione «strangler», un modulo alla volta, 637 test verdi

Ogni passo: il modulo nuovo accanto al vecchio; i chiamanti spostati uno alla volta; i test vecchi che passano come sono (le proprietà della finestra restano come alias finché un test le usa); il vecchio cancellato quando nessuno lo importa. Mai due implementazioni oltre un rilascio.

1. **`energy/pipeline.py`** (1 giorno): `EnergyJob._compute` e `_strings` spostati tali e quali in `compute(project, results, cache, fetch) -> EnergyResult` (dataclass al posto del dizionario `out`); `EnergyJob.run` lo chiama; `_variant_figures` e `CompareJob` lo chiamano senza istanziare i lavori; test del nucleo sull'anno sintetico di `tests/_energy.py`. Chiude il difetto 5 per la parte più pesante.
2. **`session.py`** (2 giorni): `ProjectSession` con `project`, `results`, `layout_keys`, `energy`, `generation`, `undo` (le istantanee di oggi, con `try/except` che ripristina `before`), `dirty`, `autosave`; `MainWindow` la crea e le delega; `edit()` della finestra diventa `self.session.edit(...)` più il ridisegno. I 59 test della finestra passano perché gli attributi sono proxy; nascono i test della sessione senza Qt (annulla, chiavi, ripristino in caso di errore).
3. **Chiavi per oggetto ed eventi per argomento** (2 giorni): `session.key_of(sf)` sulla sola geometria; `changed(topics)`; `_show_tree`, `_show_3d`, `_show_checks`, le pagine iscritte ai loro argomenti; `arrays_of` con gli ostacoli calcolati una volta per progetto; misura di accettazione: una rinomina sul progetto grande sotto 100 ms e nessuna posa, nessun calcolo dell'anno. Chiude i difetti 1 e 2.
4. **`model.py` tipizzato e validato** (2 giorni): `from_json` che valida e solleva `ValueError` con il percorso; `open_path` che lo mostra; `_typed` con i float; fixture per versione 1-6; `EnergySettings` e compagni; `app_version` letto o tolto.
5. **Geometria** (i compiti 16a, 16b, 16c, come già scritti, ma costruiti sulla sessione): `skeleton.py` e `Roof.edges`; `move.py` sulle relazioni della sessione; `Row` e id di modulo; `nearshade` e `stringing` per id.
6. **Le scene incrementali** (3 giorni): `plan.py` con un item per oggetto aggiornato sul posto (dizionario id → item) e la ricostruzione solo per l'oggetto toccato; `view3d` con un nodo per oggetto per selezione, anteprima e gizmo (16b, 16g); `MarkDelegate` senza `ResizeToContents` sulla colonna.
7. **`window.py` ridotto al cablaggio** (1 giorno alla fine): ciò che resta di dominio (`_drawn`, `_delete`, `_host`, `_find_site`, gli id dei moduli, la politica di recupero) va in `session` o in `core`; `SiteDialog` in `ui/site_dialog.py` con il geocoding in `services/`.

Ordine consigliato: 1, 2, 3, 4 prima dei compiti 16a-g (così i tetti, lo sposta e le file nascono sul modello nuovo e non sulla finestra); 5 e 6 insieme ai compiti; 7 alla fine. I compiti 16a-16g restano validi nel contenuto; cambiano la base (`session` invece di `MainWindow`) e le chiavi (id invece di indici).

## 10. Da provare sul PC di Daniel e domande

- La stessa prova (`A-architettura-prove.py`) sul progetto di Rho da 188 moduli e su quello da 4.682, con lo schermo vero: il costo di una rinomina e di un annulla con la GPU; attesi circa 3,5 s di calcolo in sottofondo per ogni rinomina (R31) finché il difetto 1 non è chiuso.
- Un file `.meridiana` scritto a mano con un campo del tipo sbagliato, aperto dal menu: che cosa vede Daniel (la finestra non apre nulla e non dice niente, se la lettura del traceback è giusta).

Domande a cui solo Daniel può rispondere:
1. I risultati (posa, anno, economia) vanno salvati nel file del progetto, come fa PVsyst, così che la relazione si apra senza ricalcolare? Costo: file più grandi (l'anno orario pesa circa 0,5 MB per variante), una chiave che dica se sono vecchi.
2. La sessione (passo 2) e le chiavi (passo 3) prima dei compiti 16a-g, oppure dopo: prima costa 5 giorni e rende i compiti più semplici; dopo, i compiti nascono sulla finestra e vanno spostati una seconda volta.
3. I dizionari liberi (`energy`, `consumption`, `economics`, `rules`) diventano dataclass tipizzate, con una migrazione del formato (7), o restano dizionari con uno schema di controllo?
