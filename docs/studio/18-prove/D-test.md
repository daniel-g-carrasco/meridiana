# Tema D: i test di Meridiana (studio 18, revisione completa)

Prove del 23/10/2026 sul PC di Daniel (Windows 11 Pro 10.0.26100, Python 3.12.6, PySide6 6.12, coverage 7.17.0),
ramo `revisione-completa` al commit ee9b846. Tutti i test sono stati lanciati solo con `QT_QPA_PLATFORM=offscreen`,
mai sullo schermo. Ogni affermazione porta [V] (verificata, con come) o [I] (dedotta). Nulla del programma e dei test
è stato cambiato; i file di lavoro stanno nella scratchpad della sessione (cartella `D`), i risultati in questa
cartella (`D-coverage.txt`, `D-coverage-sysmon.txt`).

## 0. In breve

- La suite è sana: 637 test, 0 errori, 3 saltati per piattaforma, 150 s offscreen su questo PC [V: run dei tempi
  delle 15:56]. I 6,5 minuti citati nel compito sono quelli dei registri di Daniel con lo schermo vero (389 s per
  518 test alle 11:16, 368 s per 555 test alle 12:46) [V: `C:\Users\utente\dev\meridiana-prove\suite-dopo-correzioni.log`
  e `suite-correzioni.log`]; offscreen la stessa suite costa 2,5 volte meno [I: il confronto fra i registri e il
  run di oggi, macchina uguale].
- Il tempo sta quasi tutto nelle finestre: 157 `MainWindow` costruite da 148 test, 118 s su 150 [V: contatore nel
  runner dei tempi]. Il nucleo senza Qt costa 29 s, di cui 20,7 s sono i tre test sui file PVsyst di Daniel che
  girano solo sul suo PC: senza quelli, 8,6 s per 429 test [V].
- La copertura del nucleo è alta (`simulate.py` 99 %, `model.py` 97 %, `config.py` 91 %, `layout.py` 97 %,
  `nearshade.py` 95 %); i buchi veri sono la risposta vera di PVGIS 5.3 (i test la simulano solo come 403 e
  provano il PVGIS 6 di riserva), l'orizzonte da 5.3, la seconda opinione PVGIS, le migrazioni del file senza file
  d'esempio, il passaggio dal disegno sulla pianta al
  progetto (`MainWindow._drawn`), la pagina delle proprietà di un'esclusione, le sezioni stringhe, cablaggio e note
  normative della relazione [V: `D-coverage.txt`, righe scoperte lette nel sorgente].
- Il metodo dei nomi come frasi va tenuto: 628 nomi su 637 sono frasi di quattro parole o più [V: conteggio sui
  `def test_`]. I difetti sono di struttura, non di stile: una classe che fa girare otto test due volte, finestre
  lasciate vive, attese fisse, rami che saltano in silenzio quando la finestra non ha il focus, valori normativi
  senza fonte nei test dei calcoli.
- La proposta: cinque cartelle (nucleo, calcoli con riferimenti, formati con un file per versione, widget singoli,
  finestra ridotta ai gesti) più un gruppo opzionale per i file esterni; obiettivi nucleo + calcoli + formati sotto
  20 s, tutto sotto 2 minuti offscreen e sotto 4 minuti sul secondo schermo.

## 1. Metodo

- Letti per intero i 54 file `tests/test_*.py` (8.541 righe) più `tests/_setup.py` (70) e `tests/_energy.py` (41)
  [V: `wc -l`; il compito diceva 50 file e 7.500 righe, i numeri di oggi sono questi]. Un'analisi statica
  (`static_tests.py` nella scratchpad, con `ast`) ha contato per file i test, le classi, le costruzioni di
  `MainWindow`, le attese, i rami condizionati dal focus, i `grab()`, i percorsi del PC di Daniel.
- Copertura: `python -m pip install coverage` nel venv dell'app (unica installazione), poi dalla radice
  `QT_QPA_PLATFORM=offscreen python -m coverage run --source=src/meridiana -m unittest discover -s tests`
  (15:53-15:56, 167 s, 637 test OK) e `python -m coverage report -m > docs/studio/18-prove/D-coverage.txt` [V].
  Una seconda misura con `COVERAGE_CORE=sysmon` è spiegata al punto 3.1. Il file `.coverage` della radice è stato
  cancellato alla fine.
- Tempi: `tempi_test_d.py` nella scratchpad, adattamento in sola lettura di
  `C:\Users\utente\dev\meridiana-prove\tempi_test.py`: tempo di ogni test, esito, numero di `MainWindow` e di
  `QDialog` costruiti durante il test (wrapper sugli `__init__`), tempo di discovery; uscita in `tempi.json` e
  `tempi.txt`. Lanciato subito dopo la copertura (15:56-15:58); al via c'erano due altri processi Python sulla
  macchina [V: `run_d.log`, `tasklist`]: le sessioni degli altri temi della revisione hanno scritto in questa
  cartella fra le 15:59 e le 16:12 e facevano misure in parallelo, quindi i tempi assoluti di oggi possono
  essere gonfiati di un 10-20 % [I]; i rapporti fra i gruppi di test non cambiano.
  Poi tre run di confronto sull'ordine (`run_exp.sh`, 16:03-16:05): `test_window` intero, `test_window.Window`
  da sola, `test_theme` da solo (punto 4.4).
- Prima dei test ho provato `python tools/compile_po.py` come chiede `CLAUDE.md`: fallisce perché `msgfmt` non è
  nel PATH di questa shell [V: `compile_po.log`, `FileNotFoundError`]. Il catalogo `locale/it/LC_MESSAGES/meridiana.mo`
  è delle 12:40, `po/it.po` delle 15:04 [V: `ls -l`]: i test di `test_i18n.py` sono passati con il catalogo
  vecchio, e questo è di per sé una fragilità (punto 5.7).
- Il repository non è stato toccato: niente git, nessuna modifica a `src/`, `tests/`, `po/`, `data/`, `tools/`;
  i soli file nuovi sono in `docs/studio/18-prove/` [V].

## 2. I file dei test, uno per uno

Colonne: che cosa copre; numero di test; `MainWindow` costruite nel modulo durante il run; secondi offscreen del
modulo; fragilità (tempi, attese, schermo, scala dei pixel, rete, file di Daniel, stato globale); giudizio in una
riga. Le colonne Test, Finestre e Secondi sono [V] (`tempi.txt`); le fragilità sono [V] per lettura del file alla
riga indicata; il giudizio è [I].

| File | Copre | Test | Finestre | s | Fragilità | Giudizio |
|---|---|---|---|---|---|---|
| test_app.py | nucleo: `app.linux_theme` | 4 | 0 | 0,0 | mock di `sys.platform` | Buono, piccolo e netto. |
| test_assistant.py | nucleo (disco di Meridio, posti, domande) e finestra (`InTheWindow`) | 22 | 16 | 6,5 | animazione di 320 ms attesa viva (riga 178); ramo sul focus a riga 220; `unittest.main()` a riga 84 prima dell'ultima classe | Buono nel nucleo; la parte finestra ricostruisce 16 finestre per provare un widget che vive da solo. |
| test_background.py | finestra: menu dello sfondo, immagini sotto il disegno | 10 | 10 | 6,5 | `wait_until` sul layout; click in coordinate di scena con tolleranza 0,2 m (riga 141); salta se manca il modulo PDF di Qt (187); importa `sample`, `wait_until` da `test_window` | Buono; ogni test paga una finestra intera per provare `underlay` e un menu. |
| test_camera.py | nucleo: camera 3D | 18 | 0 | 0,0 | seme fisso (riga 27); verifica la costante `ANIMATION_MS == 250` (206) | Ottimo: geometria provata per invarianti. |
| test_catalog.py | nucleo: catalogo CEC e ordinamento | 9 | 0 | 0,2 | dipende dai dati in `data/` (Longi, Jinko, Trina devono esserci) | Buono. |
| test_catalog_dialog.py | widget: `CatalogDialog` | 6 | 0 (7 dialoghi) | 1,1 | asserzioni sul tempo di parete `FAST = 0,6 s` (righe 12, 38, 57) | Buono, ma fragile sotto carico o con coverage. |
| test_checks.py | nucleo: `checks` (connessione, raccolta, segni) | 15 | 0 | 0,0 | gli articoli CEI 0-21 sono stringhe nel test («8.3», «8.6.2», «8.2.2.4», «6.3»): da verificare in locale (tema B) | Ottimo. |
| test_checks_views.py | finestra: segni su pianta, 3D, albero; lista e filtri | 12 | 12 | 5,6 | `wait_until`; ruolo Qt scritto come 256 (righe 103, 139, 146, 187); importa da `test_window` | Buono; metà dei test riguarda `ChecksPage` da sola. |
| test_compare.py | nucleo: confronto varianti | 3 | 0 | 0,0 | nessuna | Buono. |
| test_config.py | nucleo: impostazioni e migrazioni 1-8 | 12 | 0 | 0,2 | nessuna | Ottimo: ogni versione ha il suo test, il file danneggiato pure. |
| test_consumption.py | nucleo: fasce ARERA, profili, curve misurate, CSV | 19 | 0 | 0,5 | nessuna | Ottimo; i default (3 kW, 2.700 kWh) non dicono da dove vengono (121). |
| test_economics.py | nucleo: TIP, bilancio, VAN, batteria, taglie | 14 | 0 | 1,9 | nessuna | Ottimo; 650 €/kWh (123, 157) e il DM 414/2023 senza articolo (21). |
| test_energy.py | nucleo: `simulate`, modulo, IAM, ombre tra file | 23 | 0 | 1,8 | anno sintetico calcolato all'import (riga 19); niente rete | Buono; soglie di plausibilità senza fonte (52-53, 87-88). |
| test_geo.py | nucleo: sistema locale, azimut, Mercatore | 13 | 0 | 0,0 | nessuna | Ottimo: i raggi WGS84 sono ricalcolati nel test. |
| test_glyphs.py | finestra e widget: i caratteri che Titillium Web disegna | 4 | 1 | 0,6 | font nel repository; `SYMBOL_FAMILY` patchata (98); importa da `test_window` | Buono: regressione mirata di Windows. |
| test_i18n.py | nucleo e Qt: lingua, plurali, numeri, parole di Qt | 10 | 0 | 0,0 | dipende da `locale/*.mo`, artefatto di build (18); modifica `os.environ` e lo stato globale di `i18n` e delle traduzioni di Qt (20-24, 84); un test solo Windows (65) | Buono, ma poggia su un file che il runner non produce. |
| test_layout.py | nucleo: posa, regole VVF, tavoli, est-ovest | 20 | 0 | 0,4 | nessuna | Ottimo; 1 m, 20 m, 2 m senza la guida VVF citata (88-104). |
| test_marks.py | widget: icone dei segni e delegato dell'albero | 2 | 0 | 0,0 | `grab()` con DPR e soglia di pixel (53-60); verifica `MARK_ROLE == UserRole + 1` (61) | Buono; fragile sullo schermo vero (già corretto il 23/10). |
| test_mesh.py | nucleo: triangoli, normali, bordi | 13 | 0 | 0,0 | nessuna | Ottimo. |
| test_meteo.py | nucleo: PVGIS 6 di riserva | 3 | 0 | 0,3 | rete simulata (44-51) | Buono, ma prova solo la via di riserva (punto 3.3). |
| test_minisign.py | nucleo: Ed25519, firme | 3 | 0 | 0,1 | vettori RFC 8032 citati | Ottimo. |
| test_model.py | nucleo: file, backup, varianti, fill, duplicati | 27 | 0 | 0,1 | nessuna | Buono; le migrazioni (1 e 3) sono provate mutando il JSON corrente, non con file d'esempio. |
| test_navicube.py | nucleo: cubo di navigazione | 9 | 0 | 0,0 | nessuna | Ottimo. |
| test_navigation.py | nucleo: stili e macchina a stati del mouse | 17 | 0 | 0,0 | nessuna; tabella 2.2 dello studio 15 citata | Ottimo. |
| test_nearshade.py | nucleo: ombre vicine, blocchi, elettrico | 12 | 0 | 0,6 | nessuna | Ottimo: casi analitici con la geometria a mano, Martinez-Moreno 2010 citato (101). |
| test_panels.py | finestra: barra, albero, menu contestuali, pannello destro | 9 | 9 | 6,3 | `wait_until`; ruolo 256 (115, 117); cambio tema (105-107); importa da `test_window` | Buono. |
| test_panond.py | nucleo: file PAN e OND | 5 | 0 | 0,0 | file reali di pvlib con licenza in cartella | Ottimo. |
| test_paths.py | nucleo: cartelle | 4 | 0 | 0,0 | uno solo Linux (saltato qui), uno solo Windows | Buono. |
| test_plan.py | widget: `PlanView` da sola, mouse e tastiera | 19 (11 distinti) | 0 | 0,1 | `QTest` a pixel con tolleranza 3 px (93); ramo su `isExposed()` (72); `Sides(Drawing)` fa girare otto test due volte (182) | Buono e veloce: il modello per i test della finestra. |
| test_plan_aids.py | finestra: freccia del nord, barra di scala, cursore, misura | 7 | 7 | 4,3 | `wait_until`; «10» al posto di `MARGIN` (72-73); asserzione oscura (79-80) | Buono. |
| test_pvsyst.py | nucleo: formato PVsyst, progetto, mappatura; `RealFiles` | 13 | 0 | 20,8 | `RealFiles` solo con `C:\Users\utente\dev\meridiana-prove\pvsyst-campioni` (riga 20), 20,7 s | Buono; i tre test sui file reali vanno in un gruppo a parte. |
| test_quantity.py | nucleo: quantità con unità, errori, niente `eval` | 13 | 0 | 0,0 | nessuna | Ottimo. |
| test_quantity_field.py | widget: campo quantità | 4 | 0 | 0,0 | `return` silenzioso senza focus (78-79); `wheel.guard` sull'app condivisa (20) | Buono. |
| test_recovery.py | nucleo: copie di recupero, revisioni | 3 | 0 | 0,1 | `time.sleep(0,05)` (22) | Buono. |
| test_release.py | repository: versione, metainfo, SVG, trattino lungo | 5 | 0 | 0,0 | `glob` non ricorsivo su `docs` (68-70) | Buono ma bucato: `docs/studio/06-pvsyst-aurora-pvlib.md` ha un trattino lungo che non vede [V: `grep`]. |
| test_roofs.py | nucleo: falde | 9 | 0 | 0,0 | nessuna | Ottimo. |
| test_rules.py | nucleo: note N01-N27, minimo rinnovabile, testo | 13 | 0 | 0,0 | nessuna | Buono; k 0,05, 0,025, 0,08, 0,06 e la soglia 100 kW senza la fonte nel test (50-52, 76-84). |
| test_shortcuts.py | nucleo: comandi e tasti | 11 | 0 | 0,0 | nessuna | Ottimo. |
| test_sides.py | nucleo: lati di un contorno | 5 | 0 | 0,0 | nessuna | Ottimo. |
| test_snapping.py | nucleo: agganci | 18 | 0 | 0,0 | nessuna | Ottimo. |
| test_squaring.py | nucleo: squadratura | 4 | 0 | 0,0 | nessuna | Buono. |
| test_stringing.py | nucleo: stringhe e CEI 64-8/7 | 14 | 0 | 0,1 | un test salta se il catalogo non ha i due prodotti (75) | Ottimo; esempio dell'allegato B citato (30). |
| test_sun.py | nucleo: posizione del sole, interasse | 11 | 0 | 0,0 | fixture con provenienza (pvlib SPA, 21/10/2026) | Ottimo. |
| test_theme.py | finestra: palette, Fusion, colori delle viste, anteprima | 10 | 9 | 10,6 | cambi di tema sull'app condivisa; attesa fissa di 0,4 s (139); un test solo Linux (157) | Buono ma il più caro per finestra (1,1 s mediano). |
| test_theme_colors.py | nucleo: colori dal seme | 23 | 0 | 1,4 | valori aurei da `colori.js` citati | Ottimo. |
| test_tiles.py | nucleo: tasselli | 6 | 0 | 0,0 | nessuna | Ottimo. |
| test_underlay.py | nucleo: immagini sotto il disegno, migrazione 5-6 | 13 | 0 | 0,0 | nessuna | Ottimo. |
| test_updates.py | nucleo: release, download, firme, blocco del file | 11 | 0 | 0,8 | un test saltato (workflow Windows assente, 145); uno solo Windows che esegue `whoami.exe` (156) | Ottimo. |
| test_view_colours.py | nucleo: colori delle viste | 8 | 0 | 0,0 | nessuna | Ottimo. |
| test_viewaids.py | nucleo: barra di scala, altezze, misure, contorni | 9 | 0 | 0,0 | nessuna | Ottimo. |
| test_viewbar.py | finestra: barre nelle viste | 8 | 8 | 4,9 | `wait_until`; `QTest.keyClick` F3 e F8 (92, 96); cambio tema (119) | Buono. |
| test_viewcube.py | finestra: cubo, selezione condivisa, F | 12 | 12 | 6,4 | `wait_until` su `fitted` (39); geometria a pixel (50-51) | Buono. |
| test_views_navigation.py | finestra: mouse in 3D e in pianta, preferenze | 11 | 11 | 5,9 | animazioni vere (250 ms) e attese fino a 2 s (110, 122); stato globale `SystemAccent.motion` (129-133) | Buono. |
| test_window.py | finestra: tutto; widget `Properties` | 59 | 62 | 61,7 | 17 `wait_until`; attese fisse (269, 583); sei rami sul focus; `EnergyPages` chiude senza `dispose` (842); `_setup`-like helper (`wait_until`, `sample`) importati da sei altri moduli | Il cuore della suite, da dividere: 41 % del tempo. |

Totale: 637 test (629 distinti), 157 `MainWindow`, 150 s [V].

## 3. Copertura

### 3.1 Numeri e un avvertimento sul metodo

- Tracer C (il default di coverage su Python 3.12): 88,1 % di 13.875 istruzioni, 1.645 scoperte
  [V: `D-coverage.txt`, totale].
- Il tracer C vede solo i thread che Python crea: `LayoutJob.run` (`src/meridiana/ui/window.py:105-124`) e
  `EnergyJob.run` (`window.py:143-250`) risultano scoperti pur essendo eseguiti da ogni test della finestra che
  aspetta un layout [V: le righe 106-124 e 144-250 sono nella colonna Missing mentre `test_window.Window.setUp`
  attende `self.win.results`]. Per questo ho ripetuto la misura con `COVERAGE_CORE=sysmon` (il core su
  `sys.monitoring`, che è dell'interprete e non del thread): 89,2 % di 13.875 istruzioni, 1.499 scoperte, 146 in
  meno; `window.py` dal 73,0 % al 78,9 % (415 scoperte invece di 530), `meteo.py` dall'83,3 % all'86,5 %,
  `pvgis.py` dal 38 % al 51 %, `system.py` dall'83 % all'89 %, `consumption.py` dal 93 % al 95 %, `stringing.py`
  dal 94,5 % al 96,7 %, `variants.py` dal 91 % al 95,5 %, il resto uguale; 637 test OK in 138 s (16:01-16:03)
  [V: `D-coverage-sysmon.txt`, `run_sysmon.log`]. Le righe citate sotto sono quelle del run con sysmon dove i due
  differiscono.
- Discovery della suite: 1,6 s prima del primo test (import di PySide6, pvlib, pandas, shapely) [V: `tempi.txt`].

### 3.2 I moduli meno coperti

| Modulo | Copertura C | Copertura sysmon | Che cosa manca |
|---|---|---|---|
| `__main__.py`, `app.py`, `ui/__init__.py` | 0 %, 29 %, 17 % | 0 %, 29 %, 50 % | l'avvio vero (tema, locale, recupero, schermata): nessun test lancia `main()` [V] |
| `ui/pvsyst_import.py` | 33 % | 33 % | i dialoghi di scelta e di riepilogo: i test iniettano `choose` e `confirm` come lambda (`test_window.py:168-169`) [V] |
| `ui/tileloader.py` | 34 % | 34 % | i tasselli dalla rete: i test usano `background="none"` [V] |
| `energy/pvgis.py` | 38 % | 51 % | la seconda opinione PVcalc: solo l'errore «non in cache» (41-42), mai una risposta letta (43-61) [V] |
| `ui/charts.py` | 66 % | 66 % | il throttling del resize (72-93), i grafici `changes`, `heatmap`, `line` (279-352), il testo sotto il puntatore (365-384) [V] |
| `ui/window.py` | 73 % | 79 % | vedi 3.3 [V] |
| `ui/theme.py` | 75 % | 75 % | il portale di Linux (124-187): saltato su Windows [V] |
| `ui/report.py` | 80 % | 80 % | PVGIS a confronto (86-100), tabella delle stringhe (121-132), cablaggio (136-141), verifiche e note normative (198-216) [V] |
| `ui/plan.py` | 82 % | 82 % | rotella e pan con eventi veri (631-667), tasti Spazio, Ctrl, Canc, cifre digitate (880-946), disegno delle guide e delle etichette (998-1147), tasselli (1156-1190) [V] |
| `energy/meteo.py` | 83 % | 87 % | vedi 3.3 [V] |
| `energy/system.py` | 83 % | 89 % | ostacoli sotto una falda (`obstacles_of`, 29-46) e il nome del lato (73) [V] |
| `ui/properties.py` | 88 % | 88 % | la pagina di un'esclusione (`show_exclusion`, 733-763) e il ritorno del focus (291-328) [V] |

### 3.3 Le righe importanti scoperte, per argomento

Calcoli [V: `D-coverage-sysmon.txt` e lettura delle righe]:
- `energy/simulate.py` 99,1 %: scoperte solo 138 (un orizzonte senza il punto a 90°) e 485-488 (una spiegazione di
  formula). I calcoli sono tutti eseguiti; se siano giusti lo dice il tema B, non la copertura.
- `energy/nearshade.py` 95 %: `under()` (78-87, l'ombra di una falda sul piano sotto) non ha test;
  `cached_shading` non svuota mai la cache (308).
- `energy/stringing.py` 96,7 %: `strings_allowed` senza il limite di corrente per MPPT (73), `vmp_at` (76-81), i
  messaggi sul fusibile e sull'intervallo (202, 214), i due `return None` di `suggest` (225, 240).
- `energy/consumption.py` 95 %: curva vuota o parziale (290, 302), i consumi dati mese per mese senza fasce
  (338-341: un ingresso dell'interfaccia senza test), CSV non UTF-8 (378-379), file senza date né valori (420).
- `energy/components.py` 93 %: il ripiego lineare quando il fit a cinque parametri fallisce (176-201) non è mai
  provato: un modulo con una scheda strana cadrebbe lì senza che un test lo sappia.
- `sun.py` 87 %: `sun_path` (150-160) e `noon_elevation` (146-147) senza test.
- `rules.py` 98 %: BIPV e pensiline nelle `facts` (118, 120), il testo «+10 %» per l'edificio pubblico (167).
- `checks.py` 97 %: le voci «ogni verifica delle stringhe passata» (181) e «moduli in nessuna stringa» (185).

Formato del file e migrazioni [V]:
- `model.py` 97,5 %: scoperte 453 (variante in mano assente nel file: si prende la prima) e 456 (il `design`
  della variante corrente nel JSON). `MIGRATIONS` 1-2, 2-3 e 4-5 sono identità (`model.py:33-35`) e non hanno un
  test proprio; 3-4 ha `test_model.py:125`, 5-6 ha `test_underlay.py:115`; la versione 1 è provata togliendo due
  chiavi al JSON di oggi (`test_model.py:65-74`). Nessun file `.meridiana` di una versione passata è nel
  repository: un cambiamento nel `to_json` di oggi cambierebbe anche «il file vecchio» dei test.
- `config.py` 91 %: le migrazioni 1-8 hanno tutte un test; scoperti i soli rami d'errore su disco
  (`_set_aside` 202, `load` 236, `save` 256-261, `_keep_previous` 272-275).

Salvataggio [V]:
- `atomic.py` 88 %: il ramo `except BaseException` che cancella il temporaneo (30-33) non è provato: è la promessa
  «scritto tutto o niente».
- `ui/window.py`: `_save_as` (2366-2386), `_new` (2318-2335), gli `except OSError` di apertura e salvataggio
  (2243, 2294, 2340, 2359, 2381, 2464), `closeEvent` con il rifiuto (2474), `offer_recovery` senza copia (2260),
  `_save_revision` senza percorso (2289): i dialoghi di file non sono mai attraversati; i test chiamano `_save()`
  con un percorso già noto.

Rete ed errori di rete [V: righe scoperte nel run con sysmon; le conseguenze sono [I]]:
- `energy/meteo.py`: `typical_year` è provata solo con `get_pvgis_tmy` che risponde 403 (`test_meteo.py:59-61`)
  e con il finto PVGIS 6: nessun test vede una risposta vera, o registrata, di PVGIS 5.3. Il controllo sulla forma
  della risposta (146-147) è quindi esercitato solo sul frame di PVGIS 6; l'orizzonte da 5.3 (`get_pvgis_horizon`,
  206-209 e 230) e la richiesta vera (`_get_json`, 154-159) non sono mai eseguiti; l'etichetta «PVGIS 5.3»
  (110-112) è coperta solo attraverso la cache che `_energy.write_cache` scrive con i metadati di 5.3. Se pvlib
  cambiasse i nomi delle colonne o il senso di `coerce_year`, la suite non se ne accorgerebbe. Gli errori della
  cache danneggiata (124-125, 135-136) e della risposta corta (147, 178) non hanno test.
- `energy/pvgis.py` (51 % con sysmon): la seconda opinione PVcalc è esercitata fino all'errore «non in cache» con
  `network=False` (41-42); la lettura di una risposta (43-61) mai. `ui/tileloader.py` (44-114) e `SiteDialog` in
  `ui/window.py` (297-398, la ricerca dell'indirizzo con `QNetworkAccessManager`) sono fuori dai test, giustamente,
  ma senza un doppio registrato che faccia da risposta.

Finestra [V]:
- `MainWindow._drawn` (`ui/window.py:1280-1329`): il passaggio dal contorno disegnato al progetto (edificio,
  sotto-campo con `coplanar` o `tilted_anchored`, esclusione) non ha test; `test_plan.py` si ferma al segnale
  `polygonDrawn`.
- `_show_properties` per un'esclusione (1763) e `Properties.show_exclusion` (733-763): selezionare un'esclusione
  nella finestra non è mai provato.
- `_rename_variant`, `_delete_variant`, `_variant_figures` (1218-1257), `_find_site` (1549-1560), la scelta di
  inverter, batteria e modulo dal catalogo nella finestra (2073-2094), `_import_pvsyst` con il dialogo (2096-2110),
  `_export_report` (2053-2071): comandi del menu senza test.

Dentro i lavori in thread, che solo sysmon vede [V: `D-coverage-sysmon.txt`, `window.py` e `variants.py`]:
- `LayoutJob.run`: un'eccezione di posa che non sia `ValueError` (119-123, `log.complain`) non è provata.
- `EnergyJob.run`: il meteo che manca o è danneggiato (147-151, 180-181), «posa prima i moduli» (183-184), le
  stringhe per campo quando ci sono ostacoli (204-206: l'effetto elettrico con il cablaggio su un progetto con
  ostacoli), la somma delle stime PVGIS (233-236), una stringatura data dal progettista invece di quella suggerita
  (276-282): tutti senza test. I test di `EnergyPages` percorrono una sola strada: cache presente, stringhe
  suggerite, nessun ostacolo.
- `CompareJob` (`ui/variants.py:48-50`): la variante che fallisce con un'eccezione non è provata.
- `_variant_figures` con il meteo che manca (1255-1256).

## 4. Tempi

### 4.1 Il totale e dove va

- Run dei tempi: 149,9 s per 637 test, più 1,6 s di discovery; 0 errori, 3 saltati [V: `tempi.txt`]. Con il
  tracer C di coverage: 167 s; con sysmon: 138 s [V: `coverage-run.log`, `coverage-sysmon-run.log`]. La macchina
  non era tutta mia (punto 1): il totale vero offscreen sta fra 135 e 150 s [I].
- Mediana 3 ms, media 235 ms: 118 test sopra 0,5 s valgono 127 s; 441 test sotto 50 ms valgono meno di 2 s
  [V: `analisi_tempi.py` su `tempi.json`].
- Per tipo: 148 test costruiscono almeno una `MainWindow` e costano 118,2 s (0,80 s in media); 8 test con un solo
  dialogo 1,1 s; 481 test senza finestra 30,5 s, di cui 20,7 s i tre `test_pvsyst.RealFiles` [V].
- Per modulo: i 16 moduli che hanno bisogno di Qt valgono 120,6 s per 205 test; i 38 senza Qt 29,2 s per 432 test,
  8,6 s senza `RealFiles` [V].
- Il costo fisso di una finestra: il test più rapido di ogni classe che costruisce una `MainWindow` in `setUp`
  sta fra 0,28 s (`test_assistant.InTheWindow`, senza progetto aperto) e 0,53 s (`test_panels`, `test_plan_aids`,
  `test_window.EnergyPages`, con `open_path` e attesa del layout) [V: minimo per classe in `analisi_tempi.py`].
  Su 157 finestre fa circa 70 s di sola scenografia [I: 157 per 0,45 s].
- Sullo schermo vero di Daniel i registri dicono 3-5 s per test di finestra (`test_views_navigation` 26-35 s per
  11 test, `test_assistant` 28-31 s per 22) contro 0,5 s qui: le stesse finestre costano 6-8 volte di più
  [V: i due registri; I: la causa è il rendering vero a DPR 2,5 e le animazioni].

### 4.2 I 20 test più lenti (offscreen) e perché

Tempi [V: `tempi.txt`]; il perché è [I] dalla lettura del test, salvo dove indicato.

| s | Test | Perché |
|---|---|---|
| 18,75 | test_pvsyst.RealFiles.test_every_variant_is_laid_with_pvsysts_modules | legge ogni PRJ dei campioni di Daniel e posa ogni variante (`p.fill` per ciascuna) |
| 6,48 | test_window.EnergyPages.test_variants_keep_their_own_design_and_are_compared | un calcolo energetico intero più il `CompareJob` su due varianti: tre simulazioni di 8.760 ore con taglie e batteria |
| 3,56 | EnergyPages.test_without_bills_the_consumption_follows_the_context | due calcoli interi (`compute()` due volte) |
| 3,47 | EnergyPages.test_the_report_is_a_pdf_with_its_calculations | un calcolo più il PDF: figure matplotlib e formule disegnate |
| 3,06 | EnergyPages.test_strings_are_suggested_and_checked_with_an_inverter_from_the_catalogue | due calcoli, più cablaggio e disegno delle stringhe |
| 2,93 | EnergyPages.test_an_edit_on_a_page_is_undoable_and_recomputed | due calcoli |
| 2,70 | EnergyPages.test_production_consumption_and_economics_from_the_cache | un calcolo e le quattro schede disegnate |
| 2,65 | EnergyPages.test_a_measured_curve_from_a_csv | un calcolo con 8.760 righe misurate rimappate |
| 2,65 | test_theme.ThemeOfTheWindow.test_the_plan_and_the_3d_view_keep_their_own_colours_in_both_themes | sei cambi di tema: ogni cambio ripulisce ogni widget della finestra |
| 2,25 | ThemeOfTheWindow.test_the_preview_changes_at_once_and_the_window_when_the_choice_settles | dialogo delle preferenze, attesa fino a 3 s del tema e attesa fissa di 0,4 s |
| 2,03 | EnergyPages.test_a_result_draws_only_what_is_on_screen | un calcolo e il cambio di scheda |
| 1,85 | test_pvsyst.RealFiles.test_every_text_file_reads_cleanly | legge tutti i file di testo dei campioni |
| 1,78 | EnergyPages.test_the_checks_gather_the_project_and_lead_to_the_place | un calcolo |
| 1,76 | EnergyPages.test_the_site_sets_the_rules_and_their_notes_are_copied | un calcolo |
| 1,39 | test_panels.Panels.test_the_icons_take_the_colour_of_the_theme | due cambi di tema e una scansione 48 x 48 di pixel in Python |
| 1,27 | test_viewbar.ViewBars.test_the_bars_take_the_colours_of_the_theme | due cambi di tema |
| 1,24 | test_window.Window.test_a_new_window_has_nothing_to_save | una seconda `MainWindow` oltre a quella di `setUp` |
| 1,22 | ThemeOfTheWindow.test_the_system_accent_is_used_when_chosen_and_bronze_without_one | due cambi di tema |
| 1,20 | ThemeOfTheWindow.test_a_change_of_theme_leaves_no_old_colour | due cambi di tema |
| 1,13 | test_theme_colors.RandomColours.test_500_colours_at_random_keep_the_contrasts_and_the_distances | 3.000 `derive()` in Python puro |

Il calcolo energetico di `EnergyPages` costa 1,3-2,5 s a chiamata [I: differenza fra i test con uno e con due
`compute()`]; è lo stesso costo misurato in locale per R31 (3,55 s su 188 moduli, 2,3 s nel ciclo `dispatch`),
che il tema C tratta. Dodici test lo rifanno da capo sullo stesso progetto: un risultato calcolato una volta per
classe basterebbe a nove di loro [I].

### 4.3 Quante finestre vere servono

- Oggi: 148 test con `MainWindow`, 157 finestre, in 11 moduli [V].
- Che cosa provano davvero attraverso la finestra, letto test per test [I]: il giro completo (apri, posa in thread,
  modifica, annulla, salva, riapri, recupero, revisione, pannelli stretti) in `test_window.Window`, circa 15 test;
  il calcolo energetico con le pagine e la relazione in `EnergyPages`, 6 test se il risultato è condiviso; il
  backend 3D legato al QML e il cubo (`test_views_navigation`, `test_viewcube`), circa 8; l'assistente agganciato
  e sganciato, 4; lo sfondo e le immagini, 4; il tema sull'app vera, 4; pannelli, barre, segni e aiuti, circa 10.
  In tutto 50-55 finestre.
- Le altre 95-100 provano logica che non ha bisogno della finestra: `context_actions`, `_select` e l'opacità,
  `_state_key`, i filtri e i conteggi di `ChecksPage`, i posti dell'assistente, la barra di scala, la misura
  rapida, i tooltip della barra. Sono test del widget singolo (come `test_plan.py` e `test_catalog_dialog.py`,
  0,05-0,15 s l'uno) o test del nucleo su un oggetto «documento» senza Qt (selezione, modifiche, impronte dello
  stato, azioni possibili), che il tema A propone di estrarre da `window.py` [I].
- Stima del guadagno: 100 finestre in meno fanno 45-50 s offscreen e 300-400 s sullo schermo vero [I: 0,45 s e
  3-4 s per finestra].

### 4.4 Esperimenti sull'ordine e sulle finestre lasciate vive

Tre run in più dopo la copertura con sysmon (16:03-16:05, `run_exp.sh`), con lo stesso runner dei tempi
[V: `exp_window_all`, `exp_window_class`, `exp_theme` nella scratchpad, `confronto_exp.py`]:
- `test_window` da solo: 59 test in 55,5 s contro 61,7 s nella suite intera. `test_window.Window` da sola (44
  test, nessuna finestra viva prima): 26,8 s; gli stessi 44 test dopo `EnergyPages` con le sue 13 finestre solo
  chiuse: 24,7 s; nella suite intera: 29,5 s. Offscreen, le finestre lasciate vive non costano nulla di
  misurabile: i test di `Window` non cambiano la palette, che è il caso in cui la docstring di `dispose` ha visto
  i minuti. Il difetto resta un rischio (timer e segnali di 13 finestre vive, l'autosalvataggio dopo 120 s) e un
  costo probabile sullo schermo vero [I], non un costo misurato qui.
- `test_theme` da solo: 8,9 s contro 10,6 s nella suite; test per test, nella suite i cambi di tema costano il
  20-40 % in più (2.650 ms contro 1.899 per i colori delle viste, 1.217 contro 855 per l'accento di sistema),
  salvo il primo test del run da solo, che paga i caricamenti iniziali (1.954 ms contro 1.200). Gli oggetti
  accumulati dai moduli precedenti (cataloghi, cache, widget in attesa di `deleteLater`) pesano su ogni
  ripulitura della palette [I].
- In tutto l'ordine pesa il 5-15 % offscreen: la suite è ragionevolmente indipendente dall'ordine, e nessun test
  è fallito in nessuno dei sei run di oggi [V].

## 5. Qualità

### 5.1 I nomi come frasi: da tenere

628 test su 637 hanno un nome di quattro parole o più che si legge come una frase; i nove corti sono
`test_quaternions`, `test_format_versions`, `test_easter`, `test_weekdays`, `test_pod`, `test_plurals`,
`test_nearest_folder`, `test_moved`, `test_newer` [V: conteggio sui `def test_`]. I docstring dei moduli dicono
che cosa il modulo promette e, dove serve, il perché (la data della richiesta di Daniel, lo studio): è il metodo
giusto per un programma che deve spiegare i suoi numeri, e la struttura proposta al punto 7 lo tiene.

### 5.2 Test che verificano dettagli di implementazione [V per lettura]

- `test_camera.py:206` `ANIMATION_MS == 250`; `test_marks.py:61` `MARK_ROLE == UserRole + 1`;
  `test_navigation.py:207` `DEFAULT_STYLE == "autocad"`: costanti ricopiate, non comportamento.
- `test_viewcube.py:50-51`: il cubo a «`width() - 7`» e «`y() == 6`», pixel della geometria interna.
- `test_assistant.py:24-42`: le coordinate SVG di Meridio cifra per cifra («10.2», «5.3», «1.3»). È lo studio 14
  che le fissa, quindi è accettabile come test di conformità, ma ogni ritocco del disegno rompe il test.
- `test_plan_aids.py:98, 125`: il `viewportUpdateMode` di `QGraphicsView`; `test_plan_aids.py:132`: il
  `cacheMode` degli item. Sono scelte di prestazione: meglio misurare le ridisegnature, come fa
  `test_plan.py:47-78`.
- `test_catalog_dialog.py:38, 57`: tempo di parete sotto 0,6 s. Sotto coverage è passato (0,13-0,15 s misurati nel
  commento), ma una macchina carica lo fa fallire senza che il programma sia cambiato.
- Ruoli Qt scritti come numeri: `data(1, 256)` in `test_checks_views.py:103, 139, 146, 187`, `data(0, 256)` in
  `test_panels.py:115, 117`, `data(1, 0x0100)` in `test_window.py:898`.

### 5.3 Duplicati [V per lettura]

- `tests/test_plan.py:182`: `class Sides(Drawing)` eredita gli otto test di `Drawing`, che unittest fa girare due
  volte (`test_plan.Sides.test_a_building_is_drawn_with_clicks_and_closed_with_enter` e gli altri sette compaiono
  in `tempi.json`): 637 test eseguiti, 629 distinti.
- Tre progetti d'esempio diversi con lo stesso nome `sample()`: `test_model.py:14`, `test_window.py:28`,
  `test_viewaids.py:11`; `wait_until` vive in `test_window.py:18` e sei moduli lo importano da lì
  (`test_background`, `test_checks_views`, `test_glyphs`, `test_panels`, `test_plan_aids`, `test_theme`,
  `test_viewbar`, `test_viewcube`, `test_views_navigation`): un test della finestra dipende dall'import di un altro
  modulo di test.
- `walk()` scritto due volte in `test_window.py:681-688` e `729-737`; `rows()` due volte in
  `test_checks_views.py:101-104` e `133-136`.
- Le migrazioni del progetto sono sparse: versione 1 in `test_model.py:65`, 2 in `test_rules.py:139-142`, 3 in
  `test_model.py:125`, 5 in `test_underlay.py:115`; la 4 non c'è.

### 5.4 Asserzioni deboli [V per lettura]

- Rami che tacciono quando la finestra non ha il focus: `test_assistant.py:220` (sceglie `close_panel()` al posto
  di Esc), `test_quantity_field.py:78-79` (`return` prima dell'asserzione sulla rotella), `test_window.py:273`
  (`return` prima del controllo del focus), `test_window.py:411` (`if gap.hasFocus()`), `test_window.py:774`,
  `test_plan.py:72` (`isExposed()`); tre `skipTest` espliciti a `test_window.py:319, 341, 384` sono la forma
  corretta, perché l'esito dice che il test non ha provato.
- `test_i18n.py:72`: `count(1200)` accettato in quattro forme.
- `test_plan_aids.py:79-80`: una stringa costruita per verificare che la lunghezza della barra cominci per 1, 2 o
  5; si legge solo a fatica.
- `assertTrue(found)` e simili senza messaggio: `test_catalog.py:20`, `test_glyphs.py:149`,
  `test_plan_aids.py:131`.
- Attese fisse al posto di una condizione: `test_window.py:269` e `583` (0,3 s), `test_theme.py:139` (0,4 s),
  `test_recovery.py:22` (`sleep` 0,05 s per far avanzare l'orologio di Windows).

### 5.5 Valori «magici» senza fonte nei test dei calcoli [V per lettura; la verifica dei valori è del tema B]

- `test_energy.py:52-53` (resa a bassa luce fra 0,92 e 1,02 e fra 0,88 e 1,02), `87-88` (PR fra 0,70 e 0,92,
  resa fra 900 e 2.000 kWh/kWp), `83` (Sud batte Nord di 1,3), `94` (orizzonte a 89°: meno di -40 %), `117-118`,
  `146-152`: soglie di plausibilità scelte a mano. `131-133` cita il rapporto PVsyst di Montescaglioso (4,4 % e
  76,9 %) senza l'indirizzo del rapporto; `187-188` cita il file ET-M772BH550GL.PAN (che è in `tests/data`).
- `test_economics.py:21-31`: la tariffa del DM MASE 414/2023 (80 + max(0, 180 - Pz), tetto 120, +10 al Nord, 60 e
  100 oltre 600 kW) senza articolo né allegato; `123` e `157`: 650 €/kWh di batteria; `56`: 25 anni; `85`: 20 anni
  di incentivo.
- `test_consumption.py:121`: 3 kW e 2.700 kWh per una casa; `128`: `YIELD_GUESS`; `131`: «CEI 0-21 Tab. 5» per
  i 150 kW in MT (citata nel commento, non nell'asserzione). Le fasce F1-F3 (`29-50`) sono giuste a memoria di chi
  scrive ma la delibera ARERA non è nominata.
- `test_rules.py:50-52`: 100 kW come confine BT/MT e 12.000 kW per l'AT; `76-78`: k = 0,05 e 0,025 e +10 % per
  l'edificio pubblico; `82-84`: 0,08 e 0,06 per la Lombardia dal 2027. Nessuna di queste righe nomina la norma o
  la legge; il commento a `36` cita «CEI 0-21:2026-07 3.61» ed è l'eccezione.
- `test_checks.py:17-33`: 4,6 kW e 6 kW per il monofase, 100 kW per la MT, gli articoli 8.3, 8.6.2, 8.2.2.4, 6.3
  come stringhe da ritrovare: giusto il modo, ma la pagina della norma non c'è.
- `test_layout.py:88-104`: 1 m dal bordo, gruppi di 20 m distanti 2 m: la guida VVF non è citata.
- `test_stringing.py:30-33`: l'esempio dell'allegato B della CEI 64-8/7 (KU 1,14, 43,7 V) è citato bene; `85`:
  «1,35 x 25» rimanda a 712.431.101 solo nel sorgente (`stringing.py:205`).
- Bene fatti: `test_nearshade.py` (geometria ricavata a mano nei commenti, Martinez-Moreno 2010 eq. 6 a `101`),
  `test_sun.py` (fixture con `source` e data), `test_geo.py` (raggi WGS84 ricalcolati), `test_minisign.py`
  (RFC 8032 7.1), `test_theme_colors.py` (valori da `colori.js`), `test_navigation.py` (tabella 2.2 dello
  studio 15), `test_panond.py` (file di pvlib con licenza).

### 5.6 Test saltati

- Sempre, su questo PC [V: `tempi.txt`]: `test_paths.PathsTest.test_the_home_folder_without_them` (cartelle di
  Linux), `test_theme.PortalAccent.test_the_portals_accent_is_read_without_waiting` (portale di Linux),
  `test_updates.KeyTest.test_the_ci_checks_its_signatures_with_the_key_the_app_trusts` (il workflow Windows non
  esiste ancora: `build-aux/ci-gtk-da-adattare`).
- A condizione [V per lettura]: `test_pvsyst.RealFiles` (3 test) gira solo se esiste
  `C:\Users\utente\dev\meridiana-prove\pvsyst-campioni` o `MERIDIANA_PVSYST_SAMPLES` (`test_pvsyst.py:20, 128`):
  nel CI non gira mai, sul PC di Daniel costa 20,7 s; `test_stringing.py:75` salta se il catalogo non ha
  SUN2000-10KTL-M1 e LR7-54HVH; `test_background.py:187` salta senza il modulo PDF di Qt; `test_i18n.py:18`
  salta l'intera `LanguageTest` senza il `.mo` compilato; `test_updates.py:155` e `test_paths.py:40` solo Windows.

### 5.7 Dipendenze dall'ordine e dallo stato globale [V per lettura, salvo dove indicato]

- Una sola `QApplication` per tutta la suite (`_setup.qt_or_skip`), e su di essa i test cambiano cose che restano:
  la palette e il foglio di stile (`_appearance` in `test_theme.py`, `test_panels.py:105`, `test_viewbar.py:119`,
  rimessi «light» a fine test ma non dopo un fallimento), le traduzioni di Qt (`test_i18n.py:84` rimette «en»),
  `SystemAccent.motion` (`test_views_navigation.py:129-133`, lasciato a «meno movimento»), il filtro
  `wheel.guard` (`test_quantity_field.py:20`), le variabili d'ambiente della lingua (`test_i18n.py:21-22`).
- `test_window.EnergyPages.setUp` chiude le finestre con `addCleanup(self.win.close)` (`test_window.py:842`)
  invece di `_setup.dispose`: la docstring di `dispose` (`_setup.py:60-63`) spiega che una finestra solo chiusa
  resta viva e viene ripulita a ogni cambio di palette, e che «sul runner Windows i test del tema sono passati da
  secondi a minuti». Tredici finestre con timer (`autosave_timer` 120 s, `energy_timer`, `relayout_timer`,
  `window.py:463-583`) restano vive per il resto del modulo. Le eccezioni «QSplitter already deleted» in
  `_first_layout` nei registri di Daniel delle 11:16 e 12:46 (sette per run) sono di questa natura [I: stesso
  sintomo, un timer che arriva a finestra distrutta]; offscreen oggi non è comparsa nessuna traccia [V: `grep
  Traceback` sui due log].
- `test_i18n.LanguageTest` cambia `i18n._translation` e lo rimette (`setUp`, riga 23-24); gli altri moduli leggono
  le stringhe inglesi grazie a `LANGUAGE=en` in `_setup.py:70`.
- `test_catalog_dialog` carica il catalogo in `setUpClass` perché la soglia di 0,6 s vale «alla seconda apertura»:
  il test della velocità dipende da una cache globale calda.
- `test_energy.py:19` calcola l'anno sintetico all'import del modulo: la discovery paga pvlib anche quando si
  lancia un altro file.

## 6. Difetti in ordine di gravità

1. `tests/test_model.py:65-74, 125-131`: le migrazioni del file `.meridiana` sono provate mutando il JSON di oggi;
   nessun file d'esempio per versione, la 4 non è provata. Sono i file di Daniel a rischio [V].
2. `tests/test_meteo.py:58-75` e `src/meridiana/energy/meteo.py:139-147, 206-209, 230`: nessun test vede una
   risposta di PVGIS 5.3 (solo il 403 e il finto PVGIS 6); l'orizzonte da 5.3 e la seconda opinione
   (`energy/pvgis.py:43-61`) non sono mai eseguiti [V].
3. `src/meridiana/ui/window.py:1280-1329` (`_drawn`): nessun test attraversa il disegno fino al progetto [V];
   `window.py:1763` e `ui/properties.py:733-763`: la pagina delle proprietà di un'esclusione non è mai mostrata da
   un test [V].
4. `tests/test_window.py:992-1003`: la relazione è provata senza inverter né regole: le sezioni stringhe,
   cablaggio e note normative di `ui/report.py:121-141, 198-216` non sono mai generate [V].
5. `src/meridiana/atomic.py:30-33`, `config.py:202, 236, 256-261, 272-275`, `window.py:2243-2386`: i rami
   d'errore della scrittura su disco non hanno test [V].
6. `tests/test_window.py:842`: le 13 finestre di `EnergyPages` sono chiuse e non eliminate; timer e segnali restano
   vivi per il resto del modulo (5.7). Offscreen non costa nulla di misurabile (4.4) [V]; il rischio è sullo
   schermo vero e in un ordine diverso dei test [I].
7. `tests/test_plan.py:182`: `Sides(Drawing)` fa girare otto test due volte [V].
8. `tests/test_pvsyst.py:20, 128-155`: percorso del PC di Daniel nel test; tre test che valgono 20,7 s non girano
   mai nel CI [V].
9. `tests/test_release.py:68-70`: `glob` non ricorsivo su `docs`: `docs/studio/06-pvsyst-aurora-pvlib.md`
   contiene un trattino lungo che il test non vede [V].
10. `tests/test_catalog_dialog.py:12, 38, 57`: asserzioni sul tempo di parete [V].
11. Rami che tacciono senza focus: `tests/test_assistant.py:220`, `test_quantity_field.py:78-79`,
    `test_window.py:273, 411, 774`, `test_plan.py:72` [V].
12. Attese fisse: `tests/test_window.py:269, 583`, `test_theme.py:139`, `test_recovery.py:22` [V].
13. Stato globale non rimesso a posto dopo un fallimento: palette e foglio di stile, traduzioni di Qt,
    `SystemAccent.motion` (5.7) [V].
14. `tests/test_i18n.py:18`: dipende da `locale/*.mo`, che oggi è più vecchio di `po/it.po` e che il runner non
    ricompila (`compile_po.py` vuole `msgfmt` nel PATH) [V].
15. Valori normativi senza fonte nei test (5.5): `test_rules.py:50-52, 76-84`, `test_economics.py:21-31, 123`,
    `test_layout.py:88-104`, `test_checks.py:17-33`, `test_consumption.py:121` [V].
16. Test su costanti e pixel (5.2): `test_camera.py:206`, `test_marks.py:61`, `test_viewcube.py:50-51`,
    `test_navigation.py:207`, `test_plan_aids.py:98, 125, 132` [V].
17. Helper condivisi in un modulo di test (`test_window.py:18, 28`) importati da altri nove moduli; tre `sample()`
    diversi; `walk()` e `rows()` doppi (5.3) [V].
18. `tests/test_assistant.py:84-85`: `unittest.main()` prima della classe `InTheWindow`, che lanciando il file
    da solo non gira [V].
19. `src/meridiana/energy/components.py:176-201`: il ripiego lineare del modello del modulo non ha test [V].
20. La misura di copertura con il tracer C non vede i thread di Qt (3.1): un CI che misurasse la copertura senza
    `COVERAGE_CORE=sysmon` darebbe `window.py` al 73 % per un difetto dello strumento [V].

## 7. La proposta

### 7.1 La struttura della suite dopo la revisione

```
tests/
  _setup.py          QApplication, dispose, wait_until, screen; reset dello stato globale a fine modulo
  _fixtures.py       i progetti d'esempio (uno per uso: capannone, casa a falde, con ostacoli), l'anno sintetico
  nucleo/            senza Qt: model, config, layout, roofs, geo, sun, snapping, sides, squaring, shortcuts,
                     navigation, navicube, camera, mesh, tiles, viewaids, view_colours, theme_colors, assistant,
                     quantity, recovery, minisign, updates, paths, i18n (senza Qt), catalog, panond, pvsyst,
                     compare, rules, checks
  calcoli/           energy: simulate, nearshade, stringing, economics, consumption, bands, meteo, components;
                     ogni valore atteso con la fonte accanto (norma, articolo e pagina; rapporto PVsyst con
                     indirizzo; pvlib ModelChain con versione); i file di riferimento in calcoli/riferimenti/
                     con un README che dice da dove vengono
  formati/           un file .meridiana per ogni versione 1-6 e un config.json per ogni versione 1-8, scritti
                     una volta e mai rigenerati; un test che apre ciascuno e confronta con il risultato atteso;
                     i file danneggiati, troncati, di una versione futura; le scritture atomiche con il
                     fallimento a metà
  widget/            offscreen, un widget alla volta, senza MainWindow: PlanView (già così), CatalogDialog (già
                     così), ChecksPage, Properties, Assistant, ViewBar, ViewCube, QuantityField, SunBar, i grafici
  finestra/          la MainWindow vera, 50-55 test: i gesti dal sito alla relazione, i thread, l'annulla, i
                     file, i pannelli, il tema sull'app, il 3D legato al QML
  esterni/           opzionali con una variabile d'ambiente: i campioni PVsyst di Daniel, PVGIS vero, i tasselli
```

- I test della finestra prendono la finestra da una fixture unica (`window(project, cfg)` in `_setup.py`) che
  fa `open_path`, aspetta il layout e garantisce `dispose`; `EnergyPages` calcola una volta per classe
  (`setUpClass`) e i test che modificano ricalcolano solo loro.
- La copertura si misura con `COVERAGE_CORE=sysmon` (già nel runner dei tempi, da mettere in `CLAUDE.md`), una
  volta a settimana o a richiesta, non a ogni push.
- Il CI lancia nucleo, calcoli, formati e widget su Linux e Windows a ogni pull request (meno di un minuto),
  finestra solo offscreen su Linux a ogni pull request e sul desktop del runner Windows prima di un rilascio;
  esterni mai nel CI.
- Lo stato globale: `_setup.py` registra a fine modulo (`addModuleCleanup`) il ripristino della palette, del
  foglio di stile, delle traduzioni di Qt, di `SystemAccent.motion` e dell'ambiente.

### 7.2 Obiettivi di tempo

| Gruppo | Oggi (offscreen, questo PC) | Obiettivo |
|---|---|---|
| nucleo + calcoli + formati | 29,2 s (8,6 s senza i campioni PVsyst) [V] | sotto 20 s, senza pvlib all'import dei moduli |
| widget | circa 2 s (`test_plan`, `test_catalog_dialog`, `test_marks`, `test_quantity_field`, `test_glyphs`) [V] | sotto 20 s con i widget tolti alla finestra |
| finestra | 118 s per 148 test [V] | sotto 60 s per 50-55 test; `EnergyPages` con un calcolo per classe |
| tutto, offscreen | 150 s + 1,6 s di discovery [V] | sotto 2 minuti; discovery sotto 1 s |
| tutto, sul secondo schermo di Daniel | 6-6,5 minuti per 518-555 test [V: registri] | sotto 4 minuti [I: 100 finestre in meno a 3-4 s l'una] |
| esterni | 20,7 s [V] | fuori dal totale, a richiesta |

### 7.3 Da aggiungere subito

1. `_setup.dispose` in `EnergyPages` e il calcolo condiviso per classe (difetto 6; mezz'ora).
2. I file d'esempio di ogni versione del progetto e delle impostazioni, con il test che li apre (difetto 1): i
   file vanno scritti oggi dal programma di oggi e poi congelati; per le versioni passate si ricostruiscono dai
   commenti di `model.py:28-32` e dai migratori di `config.py:34-69`.
3. Una risposta registrata di PVGIS 5.3 (il JSON vero di `get_pvgis_tmy` e di `get_pvgis_horizon`, salvati una
   volta con la rete e messi in `calcoli/riferimenti/`) e i loro errori: 403, risposta corta, colonne mancanti;
   lo stesso per PVcalc (difetto 2).
4. Un test che disegna un edificio, un sotto-campo e un'esclusione nella finestra e li trova nel progetto, con
   l'annulla (difetto 3); un test che seleziona un'esclusione e legge la sua pagina.
5. La relazione con inverter, stringhe, cablaggio e regole, e il controllo che le sezioni ci siano (difetto 4).
6. La scrittura atomica che fallisce a metà (`atomic.py:30-33`), la cartella in sola lettura, il `.bak` che non
   si può rinominare (difetto 5).
7. `rglob` in `test_release.py` e la correzione del trattino in `docs/studio/06` (difetto 9).
8. Le fonti accanto ai valori (difetto 15): basta un commento con norma, edizione, articolo e pagina, da riempire
   nella sessione locale con l'archivio (il tema B fa l'elenco).
9. Il ripiego lineare di `components.py` con un modulo dalla scheda incoerente (difetto 19).
10. `COVERAGE_CORE=sysmon` scritto in `CLAUDE.md` accanto al comando dei test (difetto 20).

### 7.4 Da togliere

- L'ereditarietà `Sides(Drawing)` (un mixin o una classe base senza test).
- Le asserzioni sul tempo di parete in `test_catalog_dialog.py`: al loro posto contare le righe lette dal modello
  (il proxy non deve toccare tutti i 16.959 record) e tenere il tempo in un test del gruppo esterni.
- I test sulle costanti (`ANIMATION_MS`, `MARK_ROLE`, `DEFAULT_STYLE`, i 6 e 7 pixel del cubo) e sulle modalità
  interne di `QGraphicsView`.
- I rami che tacciono senza focus: o `QTest.qWaitForWindowActive` e poi l'asserzione, o `skipTest` con il motivo.
- Le attese fisse: una condizione da aspettare, sempre.
- I percorsi del PC di Daniel nei test: solo la variabile d'ambiente, con il gruppo esterni.
- Le 95-100 finestre di troppo (4.3), una classe alla volta, man mano che il tema A sposta la logica fuori da
  `window.py`.

## 8. Fonti e file

- Comandi e registri: `run_d.log`, `coverage-run.log`, `tempi.txt`, `tempi.json`, `tempi-run.log`,
  `coverage.json`, `run_sysmon.log`, `coverage-sysmon.json`, gli script `tempi_test_d.py`, `static_tests.py`,
  `missing_lines.py`, `enclosing.py`, `analisi_tempi.py`, `run_d.sh`, `run_sysmon.sh`, `run_exp.sh` nella
  scratchpad della sessione, cartella `D`.
- Rapporti di copertura: `docs/studio/18-prove/D-coverage.txt` (tracer C) e `D-coverage-sysmon.txt` (sysmon).
- Registri di Daniel: `C:\Users\utente\dev\meridiana-prove\suite-dopo-correzioni.log` (11:16, 518 test,
  389,3 s), `suite-correzioni.log` (12:46, 555 test, 368,3 s), `fase2-suite-windows.log` (10:40, interrotto a
  1.177 s), `tempi_test.py`.
- Documenti del repository: `CLAUDE.md` (comandi dei test, lezione sui `grab()` a DPR 2,5),
  `docs/compiti/18-revisione-completa.md` (tema D), `tests/data/pvsyst/README.md`.
