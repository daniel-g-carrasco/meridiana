# G. Qualità del codice, sicurezza e licenze

Tema G della revisione completa (studio 18, `docs/compiti/18-revisione-completa.md`). Rapporto del 23/10/2026 sul ramo
`revisione-completa`, stato del codice all'ultimo commit (`ee9b846`). Ogni affermazione è marcata [V] (verificata, con
come) o [I] (dedotta). Le righe citate sono quelle dei file di questo commit.

File di questo tema in `docs/studio/18-prove/`:
- `G-misure.txt`: i numeri grezzi (righe, funzioni lunghe, ogni `except`, import, duplicazioni, testi, type hints);
- `G-misure.py`: lo script che li produce (solo libreria standard, lettura AST, non tocca il programma);
- `G-prova-file-progetto.py` e `G-prova-file-progetto-risultati.txt`: venti file di progetto malformati dati a
  `model.Project.load` e alla finestra vera (offscreen, senza rete).

## 0. In breve

Verdetto: **il nucleo si tiene** (geometria, sole, posa, energia, catalogo, PVsyst: codice pulito, con le fonti scritte
accanto, 0 cicli di import, Qt mai importato fuori da `ui/` salvo `app.py`); **la finestra si rifà a pezzi**
(`ui/window.py` 2.474 righe con una classe di 2.074, `ui/plan.py` con una classe di 1.134, il lavoro energetico
orchestrato dentro la finestra); **la lettura del file di progetto si rifà** (nessuna validazione: 8 file malformati
su 20 fanno saltare la finestra senza un messaggio). Delle 20.190 righe stimo 14.442 da tenere com'è (71,5 %),
1.996 da pulire (9,9 %), 3.752 da rifare (18,6 %): sezione 8.

I punti più gravi:
1. `model.Project.from_json` non valida nulla: versione come testo, versione 0, un edificio scritto male, una
   variante non dizionario, un `sun_window` sbagliato, coordinate assurde escono come `TypeError`, `KeyError`,
   `AttributeError`, `OverflowError`, che `MainWindow.open_path` (`ui/window.py:2340`) non cattura; in 3 casi su 8
   l'eccezione arriva dopo che il progetto è già stato sostituito nella finestra (`ui/window.py:2344`) [V, sezione 6.1].
2. Nessun gestore globale delle eccezioni (`app.py`): PySide6 stampa il traceback su stderr e va avanti; l'utente non
   vede nulla, e nella build Windows senza console non lo vede nessuno [V, sezione 3.3].
3. Riservatezza: un'immagine importata è incollata nel progetto «com'è», metadati EXIF compresi
   (`ui/underlays.py:79-80`); progetto e immagini finiscono anche nelle copie di ripristino sotto
   `%LOCALAPPDATA%\Meridiana\state\recovery`; indirizzi e coordinate del sito vanno a Nominatim e a PVGIS senza che
   la finestra lo dica [V, sezione 6].
4. Errori che non arrivano all'utente: i tasselli che non arrivano (`tileFailed` non è collegato a nulla,
   `ui/tileloader.py:28`, `ui/plan.py:168`), il salvataggio automatico, delle impostazioni e dello stato della
   finestra che falliscono (`log.complain`, cioè stderr), tre `log.complain` sui dati energetici [V, sezione 3].
5. `ui/preferences.py:93` riassegna il parametro `page`: `Preferences(..., page="navigation")` apre sempre su
   Aspetto [V, provato offscreen].
6. Testi: le due note della posa (`layout.py:44-45`, `layout.py:250`) passano per `_(note)` con un argomento non
   letterale (`checks.py:129`, `ui/properties.py:697`): non stanno nel catalogo e restano in inglese; italiano fisso
   nel nucleo («Nuovo progetto», «Generico», «piano», «falda», «Hay e Davies»); formule con pedici italiani e
   etichette inglesi [V, sezione 4].
7. Codice morto o del template: `updates.py` e `minisign.py` (415 righe) non sono chiamati da nessuno;
   `config.check_updates` non è letto; metainfo, `.desktop`, l'icona e il manifest Flatpak descrivono ancora il
   contatore di cartelle del template [V, sezione 9].
8. Funzioni e classi troppo lunghe: 27 funzioni oltre 60 righe (3.066 righe), 11 oltre 100 (`simulate` 253,
   `_actions` 212, `MainWindow.__init__` 199, `build_html` 177, `layout.compute` 172, `evaluate` 161) [V].

## 1. Metodo

- Letti per intero tutti gli 83 file `.py` di `src/meridiana` (20.190 righe, `wc -l`) e `ui/qml/Scene.qml` [V].
  Il compito parla di 78 file e 18.800 righe: i numeri di oggi sono 83 e 20.190 (`G-misure.txt`, sezione 1).
- Misure con `G-misure.py` (AST e `tokenize`): righe per file (codice, docstring, commenti, vuote), lunghezza di
  funzioni e classi, ogni `except` con la sua classificazione, `print` e `log.complain`, grafo degli import (a
  livello di modulo e dentro le funzioni) con la ricerca dei cicli, finestre di righe uguali (anche a meno di nomi e
  numeri), stringhe passate ai widget senza `_()`, confronto di ogni `_()`/`ngettext`/`pgettext` con `po/it.po`,
  type hints delle funzioni pubbliche del nucleo. Macchina: PC di Daniel, Python 3.12.6, PySide6 6.12.0,
  `QT_QPA_PLATFORM=offscreen` per le prove con Qt.
- Prove sul file di progetto con `G-prova-file-progetto.py`: 20 file costruiti ad arte, prima a
  `model.Project.load`, poi alla finestra vera (`MainWindow`, sfondo «none», `TileLoader._pump` disattivato e
  finestre di dialogo registrate invece che mostrate): esito, dove salta, memoria, tempo.
- Licenze: metadati dei pacchetti installati nel venv (`importlib.metadata`), i file di licenza in `data/` e in
  `src/meridiana/catalog/data/`, le intestazioni dei sorgenti.
- Non fatto: nessuna chiamata di rete (vietata), nessun PDF malevolo (non ho un corpus; sezione 6.4 ragiona sul
  codice), la suite dei test non è stata lanciata (tema D), ruff non è stato lanciato.

## 2. Misure

### 2.1 Righe

| | file | righe | codice | docstring | commenti | vuote |
|---|---|---|---|---|---|---|
| nucleo (fuori da `ui/`) | 53 | 10.322 | 7.503 | | | |
| `ui/` | 30 | 9.868 | 8.140 | | | |
| totale | 83 | 20.190 | 15.643 | 1.614 | 319 | 2.614 |

[V] `G-misure.txt`, sezione 1. I dieci file più grandi: `ui/window.py` 2.474, `ui/plan.py` 1.229,
`ui/energy_pages.py` 836, `ui/properties.py` 763, `energy/simulate.py` 633, `ui/view3d.py` 494, `model.py` 466,
`rules.py` 443, `energy/consumption.py` 430, `energy/nearshade.py` 418. I docstring sono l'8 % del totale: ogni
modulo ne ha uno che dice cosa fa e perché, spesso con la data della prova; è una qualità rara e va tenuta.

### 2.2 Funzioni e classi lunghe

1.228 funzioni e metodi; 1.067 entro 20 righe, 104 fra 21 e 40, 30 fra 41 e 60, 16 fra 61 e 100, 11 oltre 100
[V]. Le 27 oltre 60 righe sono 3.066 righe (15 % del codice). Le più lunghe:

| righe | dove | nome |
|---|---|---|
| 253 | `energy/simulate.py:168` | `simulate` |
| 212 | `ui/window.py:604` | `MainWindow._actions` |
| 199 | `ui/window.py:402` | `MainWindow.__init__` |
| 177 | `ui/report.py:59` | `build_html` |
| 172 | `layout.py:193` | `compute` |
| 161 | `energy/economics.py:200` | `evaluate` |
| 124 | `ui/properties.py:575` | `Properties._build_subfield` |
| 122 | `pvsyst/mapping.py:168` | `design_of` |
| 121 | `ui/energy_pages.py:621` e `:155` | `EconomicsPage.__init__`, `EnergyPage.__init__` |
| 102 | `energy/stringing.py:115` | `plan` |
| 99 | `ui/energy_pages.py:397`, `pvsyst/pvobject.py:103`, `checks.py:111` | `ConsumptionPage.__init__`, `parse`, `gather` |
| 97 | `ui/window.py:154` | `EnergyJob._compute` |

L'elenco intero è in `G-misure.txt`, sezione 2. Classi: 143, tre oltre 500 righe: `MainWindow` 2.074
(`ui/window.py:401`), `PlanView` 1.134 (`ui/plan.py:96`), `Properties` 592 (`ui/properties.py:172`) [V].

Giudizio: nel nucleo le funzioni lunghe sono catene di calcolo lineari con un passo per blocco (`simulate`,
`evaluate`, `compute`): leggibili, ma non si possono provare a pezzi né riusare un passo da solo (il tema B lo paga:
per confrontare un passo con pvlib bisogna rifare tutta la catena). Nella finestra sono costruttori di widget e
menu: lunghe ma piatte.

### 2.3 Duplicazioni

Lo script trova poco di identico (un blocco di 9 righe) e una dozzina di blocchi della stessa forma [V,
`G-misure.txt` sezione 5]: il codice non è stato copiato e incollato. Le duplicazioni che contano le ho trovate
leggendo, e sono di idea, non di testo:

| cosa | dove | righe |
|---|---|---|
| la lettura della cella della tabella d'ombra, due volte uguale | `energy/nearshade.py:313-326` (`at`) e `:331-342` (`_corners`) | 9 identiche [V] |
| campi e inverter ricomputati da `results` tre volte nello stesso modo, con lo stesso `try` | `ui/window.py:1770-1775`, `:1835-1841`, `:2036-2042` | 6 x 3 [V] |
| le tabelle dei segni delle verifiche (✘ ⚠ ℹ ✔) | `ui/checks_page.py:20`, `ui/report.py:124` e `:199`, `ui/energy_pages.py:345`, `ui/marks.py:20` | 5 copie [V] |
| i colori dei livelli | `ui/checks_page.py:23` ripete `theme_colors.STATUS` (`theme_colors.py:24`) | [V] |
| i nomi dei mesi | `ui/report.py:50-52` e `ui/energy_pages.py:26-28`; più `MONTHS` italiano mai usato (`ui/energy_pages.py:23`) | [V] |
| la matrice ora per mese della mappa di calore | `ui/energy_pages.py:384-388` e `:600-604` | [V] |
| «campo + bottone in un QWidget con QHBoxLayout» | 9 volte fra `ui/properties.py` e `ui/energy_pages.py` (per esempio `:199-207` e `:669-677`) | [V] |
| le descrizioni dei montaggi | `layout.MOUNTINGS` (`layout.py:32-40`, mai letto) e `mounting_names` (`ui/properties.py:21-30`) | [V] |
| i nomi delle sorgenti delle mappe | `tiles.SOURCES[...].name` (`tiles.py:51-61`) e il dizionario `names` di `ui/window.py:740` | [V] |
| i nomi dei modelli di trasposizione | `ui/energy_pages.py:234` («Hay e Davies») e `energy/simulate.py:429` («Hay and Davies 1980») | [V] |
| `_(note)` su note non letterali | `checks.py:129` e `ui/properties.py:697` | [V] |

### 2.4 Import

210 archi a livello di modulo fra i moduli di `meridiana`, **0 cicli** [V, Tarjan sul grafo]. Qt è importato fuori
da `ui/` solo in `app.py:29-32` (giusto: è l'avvio) [V]. Nessun arco nucleo -> `ui` [V]. 62 import dentro
funzioni; nessuno serve a evitare un ciclo (portati in testa non ne chiuderebbero uno) [V]: sono per l'avvio
rapido (`app.py`, i dialoghi di `ui/window.py`) o per comodità (`viewaids.py:150`, `model.py:388`,
`energy/nearshade.py:66,99,111`, `energy/stringing.py:268`, `navigation.py:82-121`, `theme_colors.py:371`). Fragili
in un altro senso: `ui/window.py` dipende da 45 moduli interni (tutto il nucleo e tutta la `ui`), `ui/plan.py` da
12 [V]: la finestra è il punto in cui ogni cosa si tocca.

Un dettaglio: `model.py:388` importa `energy.system` dentro `shadow_exclusions`, e `energy/system.py` importa
`energy/simulate.py` che importa pvlib e pandas: la prima posa «fuori dalle ombre» paga l'import di pvlib (circa
un secondo, [I]) dentro il thread di posa.

## 3. Gestione degli errori

### 3.1 Il quadro

100 `except` in tutto (`G-misure.txt`, sezione 3) [V]. Nessun `except:` nudo; 3 `except Exception` tutti ai
confini dei thread (`ui/window.py:121`, `:149`, `ui/variants.py:48`), ognuno con `log.complain` e il risultato
riportato alla finestra (il layout fallito va fra i risultati, l'energia in `error_sim`, la variante nella cella);
2 `except BaseException` che puliscono e rilanciano (`atomic.py:30`, `config.py:256`) [V]. La regola di
`CLAUDE.md` («mai except Exception: pass») è rispettata alla lettera.

### 3.2 Quelli che tacciono

L'euristica dello script ne marca 44 «senza messaggio, log o raise»; letti uno per uno, la maggior parte sono
legittimi (un `return None` dopo un parse fallito, un `continue` su una codifica tentata). Quelli che nascondono
davvero qualcosa:

| dove | cattura | che cosa succede | gravità |
|---|---|---|---|
| `config.py:202` (`_set_aside`) | `OSError` | il file danneggiato non viene spostato, ma `Notice("recovered", aside)` ne cita il nome come se lo fosse (`config.py:226`) | bassa [V] |
| `config.py:236` (`load`) | `OSError` | il salvataggio delle impostazioni recuperate fallisce in silenzio | bassa [V] |
| `config.py:274` (`_keep_previous`) | `OSError` | il backup non fatto non è detto (il commento lo ammette) | bassa [V] |
| `recovery.py:51-52` (`pending`) | 5 tipi | una copia di ripristino illeggibile viene rinominata `.unreadable` senza dirlo: l'utente non saprà mai di aver perso un recupero | media [V] |
| `energy/meteo.py:135`, `:201`, `energy/pvgis.py:39` | cache illeggibile | si riscarica: va bene, ma il file rotto viene sovrascritto senza una riga di log | bassa [V] |
| `ui/energy_pages.py:330` (`_layout_changed`) | `ValueError` | «2;a» nelle stringhe per ingresso diventa «nessuna stringa» senza dirlo | media [V] |
| `ui/energy_pages.py:530` (`_bills`) | `ValueError` | una cella delle bollette non numerica diventa 0,0 in silenzio | media [V] |
| `ui/plan.py:577` (`_apply_typed`) | `ValueError` | una lunghezza digitata male viene scartata senza dirlo (il cursore la mostrava) | bassa [V] |
| `updates.py:112`, `:278`; `ui/theme.py:185`; `ui/qt_translations.py:24`; `ui/tileloader.py:51` | vari | ripieghi ragionevoli | nessuna [V] |

### 3.3 Errori che non arrivano all'utente

- **Eccezioni non previste negli slot.** Non c'è `sys.excepthook` né un gestore in `app.py` [V, grep]. PySide6
  stampa il traceback su stderr e continua [V, provato offscreen con un `QTimer.singleShot` che solleva]. Per
  l'utente il comando non fa niente. Nella build Windows (PyInstaller senza console, [I] dalla ricetta GTK di
  `build-aux/windows`) stderr non esiste: il messaggio è perso del tutto. Casi concreti verificati in sezione 6.1:
  otto file di progetto malformati, tre dei quali lasciano la finestra a metà (progetto sostituito, viste no).
- **I tasselli delle mappe.** `TileLoader.tileFailed` è emesso (`ui/tileloader.py:101`) ma nessuno lo collega
  (`ui/plan.py:167-168` collega solo `tileReady`) e `failures` non è letto da nessuno [V, grep]: con il PCN giù,
  o senza rete, la pianta resta senza foto e senza una parola.
- **Rete.** `SiteDialog._search` (`ui/window.py:352-363`) non imposta un timeout e `QNetworkRequest` ne ha 0 per
  default [V, letto da PySide6]: senza rete la finestra resta su «Searching…» finché il sistema non taglia la
  connessione. PVGIS invece ha i suoi timeout (60 s e 30 s) e l'errore arriva come `error_sim` [V].
- **File.** Il salvataggio automatico che fallisce (`ui/window.py:2243`), le impostazioni (`:2381`) e lo stato della
  finestra (`:2464`) vanno solo a `log.complain`: l'utente crede che il ripristino lo protegga e che le preferenze
  siano salvate [V]. Il salvataggio esplicito (`:2294`, `:2359`) e l'esportazione (`:2067`) invece avvisano [V].
- **Calcolo.** `_show_energy_forms`, `_show_checks`, `_rules_facts` (`ui/window.py:1773`, `:1839`, `:2040`) loggano
  e proseguono con liste vuote: la pagina Produzione mostra zero campi senza spiegare perché [V]. Il thread
  dell'energia riporta l'errore come `f"{type(error).__name__}: {error}"` (`ui/window.py:151`): un
  «KeyError: 'length'» grezzo nelle tessere (misurato con il caso `module_without_size`, sezione 6.1) [V].
- **Immagini.** Un'immagine del progetto che Qt non decodifica (troppo grande, o non un'immagine) dà una
  `QPixmap` nulla che si disegna come niente (`ui/underlays.py:87-96`): nessun messaggio [V, provato].

### 3.4 `print` e log

`log.py` ha una sola funzione, `complain`, che scrive su stderr (`log.py:16-18`); nessun modulo usa `logging`;
`print` compare solo in `__main__.py:24,28` (versione e uso) [V]. Non esiste un file di log: il docstring di
`log.py` lo dichiara. Per un programma da scrivania che gira senza console è una mancanza: i 18 `log.complain`
(sezione 3b di `G-misure.txt`) non lasciano traccia. Rifare `log.py` con `logging` su un file in `paths.state`
(rotazione, una riga per evento) è un lavoro da mezza giornata e dà a Daniel qualcosa da leggere quando «non è
successo niente».

## 4. Testi

- **Catalogo.** 1.685 chiamate `_()`/`ngettext`/`pgettext` nei sorgenti, 1.491 voci in `po/it.po`: **tutte le
  stringhe letterali sono nel catalogo** [V, confronto automatico]. L'intestazione del `.po` porta la data del
  22/10 ma il contenuto è aggiornato al 23/10 [V].
- **Due note mai tradotte.** `checks.py:129` e `ui/properties.py:697` chiamano `_(note)` su una variabile:
  `xgettext` non le estrae, e le due note di `layout.py:44-45` (`BALLAST_WARNING`) e `layout.py:250` («no room left
  inside the margins») non sono nel catalogo (`grep` su `po/it.po`: 0 risultati) [V]: nelle Verifiche e nelle
  Proprietà compaiono in inglese.
- **Italiano fisso nel nucleo**, mostrato anche nella finestra inglese: `model.py:185` «Nuovo progetto» (titolo e
  albero), `:435` «Progetto», `:166-168` «Generico» (nel menu dei moduli); `roofs.py:75,84,123,145` «piano» e
  «falda» (il campo `Pitch.name`, che nessuno legge [V, grep]); `sun.py:123` «ora solare» (`describe()`, mai
  chiamato [V]); `ui/energy_pages.py:23` `MONTHS` italiano mai usato; `:234` «Hay e Davies» [V].
- **Inglese fisso nel nucleo** che arriva a schermo: `tiles.py:51-61`, nomi e attribuzioni delle sorgenti (la
  barra di attribuzione dice «Ortofoto 2012: Geoportale Nazionale (MASE)», il tooltip del menu «WMS without
  access constraints or fees»: due lingue nello stesso punto) [V]; i messaggi delle eccezioni del nucleo elencati
  in `G-misure.txt` 6c (33 `raise` con testo inglese): quelli di `model.py:426,429`, `pvsyst/*`, `energy/meteo.py`
  arrivano all'utente attraverso `QMessageBox` e `error_sim` [V].
- **Formule in due lingue.** Pedici italiani e etichette inglesi nello stesso passo del «Come si calcola»:
  `energy/simulate.py:431` `G_{d,cielo}`, `:442-443` `h_{oriz}`, `f_{cielo}`, `:567` `A_{ombra}/A_{moduli}`;
  `energy/economics.py:210` `E_{auto}, E_{imm}, E_{rete}`, `:234` `E_{tagliata}`, `:311` `\Delta_{zona}`, `:323`
  `VAN`, `:334` `TIR` accanto a «Net present value» e «Internal rate of return» [V]. Vanno in una lingua sola, o
  i simboli vanno nel catalogo (come le etichette).
- **Formati di numeri e unità.** `i18n.number()` è usato quasi ovunque [V]; eccezioni: le f-string con `:.0f`,
  `:.1f`, `:g` in `energy/stringing.py:148-203` e `catalog/panond.py:114-167` scrivono il punto decimale anche in
  italiano («412.5 V» accanto a «15,0 °C» nel pannello delle stringhe) [V]; «m²» contro «m2» (`layout.py:205`);
  «kWp» e «kW» per la stessa grandezza (`ui/properties.py:719` «Po,cc {kw} kW» con il valore in kWp) [V];
  «Po,cc» è un simbolo italiano in un testo inglese [V].

## 5. Tipi e nomi

- **Type hints.** 445 funzioni pubbliche nel nucleo, 113 senza qualche annotazione (25 %) [V, elenco in
  `G-misure.txt` 7]: soprattutto `camera.py` (vettori numpy), `mesh.py`, `energy/nearshade.py` e tutte le funzioni
  che prendono `project` senza tipo (`checks.py:111`, `rules.py:88`, `energy/system.py:21-94`, `viewaids.py:46-144`).
  Più grave dei tipi mancanti: i contenitori senza forma. `SubField.params: dict`, `Project.energy: dict`,
  `consumption: dict`, `economics: dict`, `rules: dict` (`model.py:151,194-199`) sono dizionari liberi letti con
  `.get` in dieci moduli diversi; `results: dict` della finestra tiene `layout.Result` o `Exception` nello stesso
  posto (`ui/window.py:120`, poi 23 `isinstance(v, Exception)` sparsi [V, grep]). Un tipo `Design`/`EnergySettings`
  con i campi scritti, e un risultato che sia o un `Result` o un errore, toglierebbero metà dei controlli.
- **Nomi.** Identificatori in inglese, coerenti; abbreviazioni molto usate: `it` 590 volte, `rec` 229, `oid` 207,
  `sf` 164, `cfg` 97, `pm` 44, `vid` 42, `sfid` 38, `hb` 24, `econ` 22 [V, grep]. `kind` è il nome di sei cose
  diverse («building»/«subfield»/«exclusion», il tipo di esclusione, il tipo di sorgente del pedigree, il tipo di
  nodo PVsyst, il tipo di grafico, la categoria del catalogo) [V]. Le stringhe «building», «subfield», «exclusion»
  sono letterali in più di cento punti: un `Enum` o costanti in `model.py` darebbero un errore al posto di un
  ramo silenzioso. In `camera.py`/`navigation.py` i nomi seguono FreeCAD (bene, lo dicono).
- **Costanti magiche senza fonte** (quelle con la fonte scritta accanto sono la regola, e va lodata:
  `checks.py:18-22`, `rules.py:22-24`, `layout.py:44-45`, `energy/simulate.py:42-46`):
  `energy/components.py:73-75` 0,71 V per cella (detto «tried on 21/10/2026», non una fonte);
  `energy/consumption.py:114-115` 20 kWp e 1.200 kWh/kWp («an Italian order of magnitude»);
  `energy/economics.py:55-78` i prezzi (0,25 €/kWh, 1.300 €/kWp, 650 €/kWh, 20 €/kWp, 12 anni, 4 %) sono
  «indicativi» e il pedigree lo dice, ma non da dove vengono; `energy/nearshade.py:32-34` la griglia 5° x 4°;
  `ui/view3d.py:205` 0,0006; `camera.py:19-23`; `tiles.py:73` 400 tasselli; `ui/window.py:269` -10 °C (detto nel
  pedigree); `ui/charts.py:56`, `ui/plan.py:35`, `ui/assistant.py:24-27` tempi e pixel (di interfaccia, va bene) [V].

## 6. Sicurezza e riservatezza

### 6.1 Il file di progetto

**Formato.** JSON scritto da `atomic.write_json` (`atomic.py:17-33`: file temporaneo, fsync, rinomina, `.bak`),
`format: "meridiana-project"`, `version: 6`, migrazioni 1 -> 6 come lambda (`model.py:33-35`), tutto il progetto
in un dizionario, le immagini di sfondo in base64 dentro `underlays[].image` (`underlay.py:27`). La lettura
(`model.py:423-457`): controllo del `format`, rifiuto di una versione più nuova, migrazioni, poi `_build(kls, raw)`
che prende `raw.items()` e passa al dataclass i campi noti (`model.py:178-180`). Nessun controllo di tipo, di
intervallo, di dimensione; `json.loads` accetta `NaN` e `Infinity` (`allow_nan`, [V] con `json.dumps`) e
`write_json` le scrive.

**Prove** (`G-prova-file-progetto-risultati.txt`, 20 casi; «SLOT» = l'eccezione esce da `open_path`, PySide6 la
stampa e la finestra non fa nulla):

| file | `Project.load` | la finestra (`open_path`) |
|---|---|---|
| non JSON | `JSONDecodeError` (è `ValueError`) | messaggio «could not be opened» [V] |
| `format` diverso | `ValueError` | messaggio [V] |
| `version: "6"` (testo) | `TypeError` (`model.py:428`) | SLOT, nessun messaggio [V] |
| `version: 0` | `KeyError` (`model.py:431`) | SLOT [V] |
| `version: 99` | `ValueError` | messaggio [V] |
| `buildings: ["x"]` | `AttributeError` (`model.py:180`) | SLOT [V] |
| edificio senza `id` | `TypeError` | SLOT [V] |
| `footprint: "abc"` | carica | SLOT in `_show_all` (`roofs.py:74`), **dopo** `self.project = project` (`ui/window.py:2344`): progetto sostituito, viste e albero non aggiornati [V] |
| `site.lat: NaN` | carica, `lat = nan` | nessun errore; la posa parte e lascia 224 moduli con un sole a NaN; con una sorgente di mappe, `tiles.zoom_for` solleva `ValueError` (`tiles.py:69`, provato a parte) nel timer dei tasselli a ogni spostamento [V] |
| `site.lat: 1e308` | carica | SLOT (`OverflowError`) in `_show_all`, dopo la sostituzione [V] |
| `height: 1e300` | carica | nessun errore nelle prove fatte (3D e posa non provati con quel valore) [V] |
| `sun_window: {"foo": 1}` | carica | SLOT (`KeyError: 'day'`) dopo la sostituzione [V] |
| chiavi sconosciute | carica | perse al salvataggio senza avviso (`'foo' kept on save: False`) [V]; il docstring di `model.py:11-12` lo dichiara solo per le versioni più nuove |
| modulo senza `length` | carica | la posa fallisce nel thread, la verifica dice «KeyError: 'length'» [V] |
| `variants: []` | carica (`or` sul default) | ok [V] |
| `variants: ["v1"]` | `AttributeError` (`model.py:452`) | SLOT [V] |
| `name: "..\\..\\evil"` | carica | il nome proposto per salvare diventa `C:\Users\...\..\..\evil.meridiana` (`ui/window.py:2367`, `:2058`): solo un default del dialogo, l'utente conferma [V] |
| immagine PNG 20000 x 20000 (1,2 MB su disco, 1,6 MB in base64) | carica in 10 ms | Qt la rifiuta (limite di allocazione 256 MB, `QImageReader.allocationLimit()` [V]): pixmap nulla, nulla disegnato, nessun messaggio; `snapshot()` dell'annulla 0,000 s [V] |
| immagine 6000 x 6000 | carica | decodificata (144 MB di pixmap), disegnata [V] |
| `image` che non è un'immagine | carica | pixmap nulla, nessun messaggio [V] |

Totale: 8 casi su 20 saltano fuori dall'`except (OSError, ValueError)` di `ui/window.py:2340`; 3 di questi dopo la
sostituzione del progetto. `offer_recovery` (`ui/window.py:2274`) cattura `ValueError, KeyError, TypeError` ma non
`AttributeError` né `OverflowError` [V]. Il modello non è un rischio di esecuzione (nessun `pickle`, `eval`,
`exec`, `yaml` [V, grep]); è un rischio di crash silenzioso e di finestra incoerente. Un «percorso dentro il
file» non viene mai aperto: `underlay.name` è solo l'etichetta del menu (`ui/window.py:1120`), `datasheet_url` nel
pedigree è testo, non un link (`ui/pedigree.py:66`); l'unico `setOpenExternalLinks(True)` che segue un URL dei
dati è quello del catalogo (`ui/catalog_dialog.py:194`), che viene dai file del catalogo, non dal progetto [V].
Nessun limite alla dimensione del file letto (`atomic.py:40` legge tutto in memoria) [V].

Che cosa serve (è il difetto 1): una validazione di `from_json` che dica «il file non è un progetto Meridiana:
<campo>, <motivo>» come un `ValueError`, per ogni campo (tipi, numeri finiti, intervalli, lunghezze degli anelli,
dimensione delle immagini), e una lettura che non tocchi `self.project` finché tutto non è pronto.

### 6.2 File di cache e stato

Dove (`paths.py:37-48`): su Windows `%APPDATA%\Meridiana\config.json` e `%LOCALAPPDATA%\Meridiana\{state,data,cache}`;
su Linux `~/.config`, `~/.local/state`, `~/.local/share`, `~/.cache` sotto `meridiana` [V].

| file | contenuto | note |
|---|---|---|
| `config/config.json` (+ `.bak`, `.broken-<data>`) | tema, colore, tasti, `last_folder` e `last_project` (percorsi assoluti), `check_updates` | nessun segreto [V]; `config.py:3` cita un «keyring (extras/secrets)» che non esiste nel codice [V, grep] |
| `state/window.json` | geometria, stato dei pannelli, splitter (base64), modalità vista, posizioni dell'assistente | [V, `ui/window.py:2456-2465`] |
| `state/recovery/<sha1(percorso)[:16]>.json` | **tutto il progetto** (immagini comprese) più il percorso assoluto del file, ogni 2 minuti se ci sono modifiche | [V, `recovery.py:21-34`, `ui/window.py:127,2238-2248`]; cancellato al salvataggio o alla chiusura senza salvare |
| `cache/tiles/<sorgente>/<z>/<x>/<y>.img` | i tasselli scaricati (30 giorni) | le coordinate del sito sono deducibili dai nomi [V, `ui/tileloader.py:41`] |
| `cache/pvgis/tmy_<lat>_<lon>.json`, `horizon_...`, `pvcalc_<parametri>.json` | risposte intere di PVGIS con latitudine e longitudine a 4-5 decimali nel nome | [V, `energy/meteo.py:95`, `energy/pvgis.py:34`] |
| accanto al progetto: `<nome>.meridiana.bak` | la versione precedente del progetto | [V, `atomic.py:27-28`] |
| `%TEMP%\meridiana-update-*` | installer scaricati (codice non attivo) | [V, `updates.py:213-222`] |

Nulla è cifrato, ed è normale per questi dati; ma le copie di ripristino e la cache restano sul PC anche dopo
che il progetto è stato spostato o cancellato, e la cartella `cache` conserva la storia dei siti studiati. Un
«Svuota cache» nelle preferenze e la cancellazione della copia di ripristino anche quando il file viene cancellato
sono due righe nel piano.

### 6.3 La rete

| servizio e URL | quando parte | timeout | che cosa manda | senza rete |
|---|---|---|---|---|
| PCN WMS `http://wms.pcn.minambiente.it/ogc?map=...&REQUEST=GetMap&BBOX=...` (`tiles.py:52-54`, **HTTP in chiaro**) | a ogni spostamento o zoom della pianta, 120 ms dopo (`ui/plan.py:171-172`), al più 6 richieste in volo, 2 ritentativi (1 s, 3 s) | 20 s per trasferimento (`ui/tileloader.py:74`) | il riquadro geografico inquadrato (quindi il sito del cliente, alla precisione del tassello) e `User-Agent: Meridiana/0.1.0 (+github)` | pianta senza foto, nessun avviso (`tileFailed` scollegato) [V] |
| OSM `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, OpenTopoMap `https://tile.opentopomap.org/...` (`tiles.py:55-61`) | come sopra | come sopra | come sopra | come sopra [V] |
| Nominatim `https://nominatim.openstreetmap.org/search?q=<testo>&format=jsonv2&limit=8&countrycodes=it` (`ui/window.py:352-362`) | al bottone «Search» di «Trova il sito», al più una al secondo | **nessuno** (default 0 [V]) | **l'indirizzo digitato** (un dato personale del cliente), lo User-Agent | «Searching…» senza fine finché il sistema non chiude [V] |
| PVGIS 5.3 `https://re.jrc.ec.europa.eu/api/v5_3/tmy` e `printhorizon` via pvlib (`energy/meteo.py:140,207`), `PVcalc` via `requests` (`energy/pvgis.py:46`) | solo a «Fetch»/«Compute» (`fetch=True`, `ui/window.py:455-456`), se la cache manca; `PVcalc` una volta per campo (`ui/window.py:230-234`) | 60 s (tmy, PVcalc), 30 s (orizzonte) | latitudine e longitudine a 5 decimali (circa 1 m), potenza, inclinazione, azimut, perdite; lo User-Agent è quello di pvlib/requests, non Meridiana | `MeteoError` -> «The weather could not be had: ...» in Produzione e nelle Verifiche [V] |
| PVGIS 6 `https://photovoltaic-geographic-information-system.ec.europa.eu/api/v6/meteorological/typical-meteorological-year`, `topography/elevation`, `topography/horizon-profile` (`energy/meteo.py:162-191,212-214`) | se PVGIS 5.3 fallisce | gli stessi | come sopra, con `User-Agent: Meridiana (PV design; ...)` | come sopra [V] |
| GitHub `https://api.github.com/repos/daniel-g-carrasco/meridiana/releases/latest` e i download (`updates.py:39-41`) | **mai**: nessun modulo chiama `updates` [V, grep]; `config.check_updates` non è letto da nessuno | 15 s, risposta al più 1 MB; 30 s per lettura in download | lo User-Agent | niente |
| `gdbus` (Linux, `ui/theme.py:153-158`) | all'avvio e a ogni cambio del tema del portale | processo locale, non rete | niente | niente |

Nessuna telemetria, nessuna chiave nel codice [V, grep `secret`, `key`]. `CODE_SIGNING.md` dice che «i file aperti
non lasciano mai il computer» e che l'unica eccezione è il controllo degli aggiornamenti: la seconda parte descrive
codice non attivo, la prima è vera per i file ma non per l'indirizzo e le coordinate del sito, che partono verso
tre servizi senza che la finestra lo dica. Per un progettista che lavora su siti di clienti è un punto da scrivere
nelle preferenze e nella documentazione: quali servizi, che cosa ricevono, come spegnerli (le mappe già si
spengono con «None»; PVGIS parte solo su richiesta; Nominatim solo su richiesta). Le chiavi future dello studio 14
(Claude con la chiave API di Daniel) non devono passare da `config.json`: oggi non c'è nessun portachiavi nel
codice, il docstring di `config.py` promette una cosa che non c'è.

Due dettagli tecnici: il PCN è l'unica sorgente in HTTP, e un'immagine ricevuta in chiaro viene decodificata da Qt
e messa in cache [V]; `energy/pvgis.py:46` non manda lo User-Agent di Meridiana, mentre `tileloader` e `meteo` sì [V].

### 6.4 Il modulo PDF di Qt e le immagini

- Importazione (`ui/underlays.py:61-84`): PNG e JPEG con `QImage.loadFromData` (tutti i plugin che il wheel di
  PySide6 porta, non solo i due), PDF con `QtPdf` (`QPdfDocument`, basato su PDFium, nessun sandbox) reso a 200 dpi
  (`PDF_DPI`, `:16`) e ridotto entro 4.096 px di lato (`underlay.MAX_SIDE`) [V].
- **Un PNG o JPEG entro 4.096 px è incollato nel progetto così com'è** (`ui/underlays.py:79-80`: `data = raw`):
  con i suoi metadati, cioè l'EXIF di una foto (posizione GPS, data, macchina) [V]. Il progetto va al cliente e al
  committente: i metadati vanno tolti ricodificando sempre, o detto.
- Alla lettura nessun limite: il limite di Qt (256 MB di pixel) ferma le immagini enormi ma in silenzio
  (sezione 6.1); un'immagine da 4.096 x 4.096 x 4 = 67 MB di pixmap per ogni immagine è il costo massimo normale
  [V dal limite]. Il base64 dell'immagine viaggia nelle istantanee dell'annulla a ogni modifica (`ui/window.py:1180-1185`),
  ma è un `deepcopy` di stringhe: 0,000 s misurati su 1,6 MB [V]; `_state_key` lo evita apposta (`:2221-2224`).
- Esportazione del rapporto (`ui/report.py:238-260`): `QTextDocument` -> `QPdfWriter`, solo contenuto generato da
  Meridiana con `html.escape` sui testi del progetto [V]: nessun rischio da dati esterni. Le formule sono PNG di
  matplotlib in cache LRU di 1.024 voci (`ui/pedigree.py:26`): qualche decina di MB al massimo [I].

### 6.5 Altro

Nessun `eval`, `exec`, `pickle`, `subprocess`, `os.system` [V, grep]; un solo `QProcess` (`gdbus`, Linux) [V].
I file PVsyst sono letti come testo con un parser proprio (`pvsyst/pvobject.py`), i `.PAN`/`.OND` riga per riga
(`catalog/panond.py`), i CSV con pandas (`energy/consumption.py:369-421`): nessuno esegue nulla [V]. Le finestre
`QTextBrowser` dei risultati non caricano risorse esterne [V, i soli `addResource` sono locali].

## 7. Licenze

Meridiana: `LICENSE` è il testo della GPL v3; `metainfo.xml` e `README.md` dicono GPL-3.0-or-later; non c'è
`pyproject.toml` (il campo di licenza vive solo nel metainfo e nel README) [V].

| componente | versione | licenza | come verificata | con GPL-3.0-or-later |
|---|---|---|---|---|
| PySide6, shiboken6, PySide6_Essentials, PySide6_Addons, PySide6_Pdf | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | metadati del wheel [V] | sì (LGPL-3) |
| Qt Quick 3D (dentro Addons) | 6.12 | GPL-3 o commerciale | `README.md` e docs Qt [I, non raggiungibili offline] | sì, ma il binario distribuito è GPL-3 di fatto |
| PySide6_WebEngine | 6.12.0.140 | LGPL-3/GPL | metadati [V] | installato nel venv ma **non usato** [V, grep]: non va nell'installer |
| pvlib | 0.16.1 | BSD-3-Clause | metadati [V] | sì |
| shapely | 2.2.0 | BSD-3-Clause | metadati [V] | sì |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | metadati [V] | sì |
| scipy | 1.18.1 | BSD | metadati [V] | sì |
| matplotlib | 3.11.2 | licenza matplotlib (stile PSF, BSD-compatibile) | metadati [V] | sì |
| pandas (transitiva, usata direttamente) | 3.0.6 | BSD-3 | metadati [V] | sì; **non in `requirements.txt`** [V] |
| requests (transitiva, usata direttamente in `meteo.py`, `pvgis.py`) | 2.34.2 | Apache-2.0 | metadati [V] | sì (Apache 2 -> GPL 3); **non in `requirements.txt`** [V] |
| h5py, contourpy, cycler, fonttools, kiwisolver, pillow, pyparsing, python-dateutil, pytz, tzdata, urllib3, idna, charset-normalizer, certifi | varie | BSD, MIT, MIT-CMU, Apache-2.0, MPL-2.0 (certifi) | metadati [V] | sì |
| pyinstaller | 6.22.3 | GPL-2+ con eccezione | metadati [V] | strumento di build, non distribuito |
| Titillium Web | | SIL OFL 1.1 | `data/fonts/titillium-web/OFL.txt` [V] | sì (il font resta OFL) |
| icone Lucide (18 SVG) | | ISC (alcune MIT, da Feather) | `data/icons/lucide/LICENSE` [V] | sì |
| liste CEC/SAM (moduli e inverter) | | BSD-3 (Alliance for Energy Innovation) | `src/meridiana/catalog/data/LICENSE-NREL-SAM.txt` [V] | sì; la nota va nella distribuzione (clausola 2) [I] |
| cataloghi «curated» (JSON) | | dati di schede tecniche con URL e data | letti [V] | dati di fatto, non opere |
| `squaring.py` (porting da iD) | | ISC, intestazione SPDX `GPL-3.0-or-later AND ISC` | `squaring.py:1-11` [V] | sì |
| icona dell'app (`data/icons/hicolor`) | | sconosciuta: il commento dice «a tile in the GNOME blue with a folder and a mark» | `...scalable/apps/...svg:3-5` [V] | è l'icona del template, non di Meridiana |
| ortofoto PCN | | WMS «senza vincoli di accesso né costi» secondo il commento | `tiles.py:4-6` [V], termini reali [I] | tasselli solo in cache, mai nel progetto |
| OSM, OpenTopoMap | | ODbL + policy dei tasselli; CC-BY-SA 3.0 | `tiles.py:7-11` [V], termini reali [I] | attribuzione a schermo [V, `ui/plan_overlays.py:106-126`]; mai nel progetto |

Conclusione: tutto è compatibile con la GPL-3; il programma distribuito è GPL-3 per via di Qt Quick 3D [I].
Mancano: un file delle attribuzioni (le BSD chiedono la nota nelle distribuzioni binarie; l'«About» di
`ui/window.py:2386-2390` ne cita quattro su venti), `requests` e `pandas` in `requirements.txt`, e il campo di
licenza in un `pyproject.toml` che non c'è. Il tema F (R36) deve leggere i termini reali di PCN, OSM e OpenTopoMap:
qui ho verificato solo che il codice dica di rispettarli (attribuzione, cache di 30 giorni, nessun download in massa:
400 tasselli al più per vista, `tiles.py:73`).

## 8. Stima per file

Criterio: «tenere» = righe che non cambierei; «pulire» = righe da ritoccare dentro la struttura di oggi (spezzare,
rinominare, tradurre, togliere il morto); «rifare» = righe da riscrivere o spostare (la struttura non regge).
Le righe sono quelle di `G-misure.txt`; la ripartizione dentro un file è una stima mia [I].

| file | righe | tenere | pulire | rifare | motivo |
|---|---|---|---|---|---|
| `__init__.py` | 24 | 0 | 24 | 0 | docstring del template («GTK», «every desktop app of mine») |
| `__main__.py` | 35 | 0 | 35 | 0 | «usage: [FOLDER...]» del template; `faulthandler` su un file aperto e mai chiuso |
| `app.py` | 73 | 0 | 73 | 0 | nessun `excepthook`; import doppio di QtCore (`:29,32`) |
| `log.py` | 18 | 0 | 0 | 18 | serve un log su file |
| `atomic.py` | 46 | 46 | 0 | 0 | |
| `paths.py` | 83 | 83 | 0 | 0 | |
| `i18n.py` | 100 | 100 | 0 | 0 | |
| `config.py` | 275 | 245 | 30 | 0 | `except` silenziosi (`:202,236,274`), docstring sul keyring inesistente |
| `recovery.py` | 66 | 60 | 6 | 0 | copie illeggibili rinominate in silenzio |
| `model.py` | 466 | 300 | 0 | 166 | `from_json`/`_build` senza validazione; migrazioni come lambda; varianti come dizionari con `pop` |
| `geo.py` | 160 | 160 | 0 | 0 | |
| `sun.py` | 160 | 155 | 5 | 0 | `describe()` italiano e mai usato |
| `roofs.py` | 151 | 140 | 11 | 0 | `Pitch.name` italiano mai letto; il 16a lo rifà comunque sul poligono |
| `layout.py` | 364 | 190 | 0 | 174 | `compute` 172 righe: frame di lavoro, righe, celle, tavoli, metà est-ovest, pile in una funzione sola; `MOUNTINGS` morto; note inglesi non traducibili |
| `sides.py`, `squaring.py`, `snapping.py`, `mesh.py`, `underlay.py` | 843 | 843 | 0 | 0 | puliti, provati, senza Qt |
| `tiles.py` | 92 | 80 | 12 | 0 | nomi e licenze non traducibili; HTTP |
| `camera.py`, `navigation.py`, `navicube.py` | 650 | 650 | 0 | 0 | |
| `viewaids.py` | 184 | 170 | 14 | 0 | import pigri, `kind` a stringhe |
| `view_colours.py` | 67 | 60 | 7 | 0 | `plan(imagery)` ignora l'argomento; `PAPER` in attesa |
| `theme_colors.py` | 377 | 377 | 0 | 0 | |
| `rules.py` | 443 | 443 | 0 | 0 | codice banale; i testi li verifica il tema B in locale |
| `checks.py` | 301 | 200 | 101 | 0 | `gather` 99 righe; `_(note)` non estraibile |
| `compare.py`, `quantity.py`, `shortcuts.py`, `assistant.py` | 612 | 612 | 0 | 0 | |
| `minisign.py`, `updates.py` | 415 | 415 | 0 | 0 | ben fatti e provati, ma non collegati (tema H) |
| `energy/__init__.py`, `bands.py`, `pedigree.py` | 142 | 142 | 0 | 0 | |
| `energy/pvgis.py` | 65 | 55 | 10 | 0 | senza User-Agent; nome della cache con tutti i parametri |
| `energy/system.py` | 104 | 90 | 14 | 0 | `arrays_of` ricalcola `layout_params()` due volte |
| `energy/meteo.py` | 231 | 210 | 21 | 0 | `except` silenziosi sulla cache; messaggi non tradotti |
| `energy/components.py` | 245 | 225 | 20 | 0 | `from_record` 30 righe di `rec.get` con due nomi per campo |
| `energy/stringing.py` | 302 | 200 | 102 | 0 | `plan` 102 righe; numeri con il punto |
| `energy/simulate.py` | 633 | 380 | 0 | 253 | `simulate` 253 righe: un passo per funzione, provabile da solo (serve al tema B) |
| `energy/nearshade.py` | 418 | 390 | 28 | 0 | `at`/`_corners` duplicati |
| `energy/economics.py` | 414 | 253 | 0 | 161 | `evaluate` 161 righe, con il ciclo di `dispatch` dentro il ciclo degli anni (R31) |
| `energy/consumption.py` | 430 | 377 | 53 | 0 | `read_curve` 53 righe |
| `catalog/__init__.py`, `catalog/panond.py` | 333 | 333 | 0 | 0 | |
| `pvsyst/__init__.py`, `records.py`, `pvobject.py`, `project.py` | 679 | 679 | 0 | 0 | parser tollerante, anomalie dette: bene |
| `pvsyst/mapping.py` | 321 | 199 | 122 | 0 | `design_of` 122 righe |
| `ui/__init__.py`, `qt_translations.py`, `wheel.py`, `quantity_field.py`, `viewbar.py`, `inspector.py`, `pvsyst_import.py`, `icons.py` | 478 | 478 | 0 | 0 | |
| `ui/underlays.py` | 104 | 90 | 14 | 0 | EXIF conservato; nessun avviso sull'immagine rifiutata |
| `ui/tileloader.py` | 114 | 100 | 14 | 0 | `tileFailed` e `failures` senza ascoltatori |
| `ui/pedigree.py`, `plan_overlays.py`, `variants.py`, `sunbar.py`, `appearance.py`, `shortcuts_dialog.py`, `marks.py` | 1.083 | 1.083 | 0 | 0 | |
| `ui/preferences.py` | 124 | 118 | 6 | 0 | il parametro `page` riassegnato |
| `ui/viewcube.py` | 226 | 160 | 66 | 0 | `paintEvent` 67 righe |
| `ui/report.py` | 260 | 0 | 83 | 177 | `build_html` 177 righe di HTML in f-string; il tema E chiede altro al rapporto |
| `ui/catalog_dialog.py` | 297 | 225 | 72 | 0 | `__init__` 72 righe |
| `ui/checks_page.py` | 305 | 232 | 73 | 0 | `__init__` 73 righe; segni e colori duplicati |
| `ui/theme.py`, `ui/charts.py`, `ui/view3d.py` | 1.188 | 1.188 | 0 | 0 | |
| `ui/assistant.py` | 387 | 306 | 81 | 0 | `__init__` 81 righe |
| `ui/properties.py` | 763 | 400 | 363 | 0 | tre costruttori di pagina da 60-124 righe con lo stesso schema |
| `ui/energy_pages.py` | 836 | 300 | 536 | 0 | tre `__init__` da 99-121 righe; `MONTHS` morto; «Hay e Davies»; mappe di calore duplicate |
| `ui/plan.py` | 1.229 | 500 | 0 | 729 | `PlanView` 1.134 righe: strumenti, scelta oggetti, tasselli, sovrapposizioni, disegno, navigazione in una classe |
| `ui/window.py` | 2.474 | 400 | 0 | 2.074 | `MainWindow` 2.074 righe; `EnergyJob._compute` è il calcolo dell'energia dentro la finestra; `SiteDialog` con la rete dentro la finestra |
| **totale** | **20.190** | **14.442 (71,5 %)** | **1.996 (9,9 %)** | **3.752 (18,6 %)** | |

Nucleo: 8.862 da tenere, 688 da pulire, 772 da rifare (su 10.322). `ui/`: 5.580 da tenere, 1.308 da pulire,
2.980 da rifare (su 9.868) [I].

## 9. Difetti in ordine di gravità

1. **Lettura del progetto senza validazione** (`model.py:178-180`, `:423-457`; `ui/window.py:2337-2352`,
   `:2274`): 8 file su 20 fanno saltare lo slot senza messaggio, 3 lasciano la finestra a metà; `NaN` accettato e
   riscritto; nessun limite di dimensione [V, sezione 6.1].
2. **Nessun gestore globale delle eccezioni e nessun log su file** (`app.py`; `log.py:16-18`): ogni errore non
   previsto negli slot è invisibile, e nella build Windows senza console è perso [V, sezione 3.3].
3. **Riservatezza non detta**: EXIF conservato nelle immagini del progetto (`ui/underlays.py:79-80`); progetto
   intero nelle copie di ripristino (`recovery.py:30-34`); indirizzo a Nominatim (`ui/window.py:352-362`),
   coordinate a PVGIS (`energy/meteo.py`, `energy/pvgis.py:31-46`) e riquadro inquadrato ai server delle mappe
   (`ui/tileloader.py:72-75`, PCN in HTTP) senza una riga nelle preferenze o nella documentazione;
   `CODE_SIGNING.md` descrive un aggiornatore che non è collegato [V, sezioni 6.2-6.3].
4. **Errori che non arrivano all'utente**: `tileFailed` scollegato (`ui/tileloader.py:28`, `ui/plan.py:168`);
   autosave, impostazioni e stato della finestra solo su stderr (`ui/window.py:2243,2381,2464`); i tre
   `log.complain` dei dati energetici (`:1773,1839,2040`); Nominatim senza timeout (`:359-362`); errori grezzi
   «KeyError: 'length'» nelle tessere (`:151`) [V, sezione 3.3].
5. **`ui/preferences.py:93`**: `page = QWidget()` copre il parametro `page` della riga 80; `show_page(page)` alla
   riga 118 riceve il widget e non cambia pagina [V, provato: `Preferences(page="navigation")` apre su Aspetto].
6. **Testi** (sezione 4): `_(note)` non estraibile (`checks.py:129`, `ui/properties.py:697`; `layout.py:44-45,250`);
   italiano fisso in `model.py:166-168,185,435`, `roofs.py:75-145`, `sun.py:123`, `ui/energy_pages.py:23,234`;
   nomi e licenze delle sorgenti in `tiles.py:51-61`; formule bilingui in `energy/simulate.py:431-567` e
   `energy/economics.py:210-334`; numeri con il punto in `energy/stringing.py:148-203` [V].
7. **Codice morto e residui del template** [V]: `updates.py` e `minisign.py` non chiamati; `config.py:87-88`
   `check_updates` e `last_update_check` mai letti; `layout.MOUNTINGS` (`layout.py:32-40`); `Pitch.name`;
   `sun.DesignWindow.describe`; `ui/energy_pages.py:23` `MONTHS`; `tileloader.failures`; `view_colours.plan`
   ignora l'argomento; `__init__.py:1-8`, `__main__.py:28`, `data/*.metainfo.xml` (descrizione e release del
   contatore di cartelle), `data/*.desktop` (`Categories=Utility;GTK;`, `Keywords=files;folder;count`), l'icona
   (`data/icons/hicolor/scalable/apps/*.svg:3-5`), `build-aux/flatpak/*.yaml` e `build-aux/windows/*` (GTK, tema
   H), `config.py:3` (keyring inesistente), `catalog/__init__.py:6-7` (percorso della nota NREL sbagliato).
8. **Funzioni e classi troppo lunghe** (sezione 2.2): 27 oltre 60 righe, 3 classi oltre 500; `simulate`,
   `evaluate` e `compute` vanno spezzate a passi per il tema B; `MainWindow` e `PlanView` vanno divise per
   responsabilità [V].
9. **Calcolo dentro la finestra**: `EnergyJob._compute` e `_strings` (`ui/window.py:134-283`) orchestrano
   meteo, posa, stringhe, PVGIS, consumo, economia, dimensionamento: 130 righe di logica di calcolo in `ui/`,
   riusate da `_variant_figures` (`:1242-1257`) e non provabili senza Qt; `SiteDialog` (`:297-398`) tiene la
   geocodifica nella finestra; `ui/window.py` importa 45 moduli [V, sezione 2.4].
10. **Duplicazioni** (sezione 2.3): il trio campi/inverter (`ui/window.py:1770-1775,1835-1841,2036-2042`),
    `nearshade.at`/`_corners`, i segni delle verifiche in cinque posti, i mesi in due, le mappe di calore in due,
    i montaggi in due [V].
11. **Silenzi sugli input dell'utente**: `ui/energy_pages.py:326-332` e `:520-533` scartano o azzerano senza
    dirlo; `recovery.py:51-52` [V, sezione 3.2].
12. **Tipi e contenitori senza forma** (sezione 5): 113 funzioni pubbliche del nucleo senza qualche annotazione;
    `params`, `energy`, `consumption`, `economics`, `rules` dizionari liberi; `results` con `Result` o `Exception`;
    `kind` a stringhe [V].
13. **Costanti senza fonte** (sezione 5): `energy/components.py:73-75`, `energy/consumption.py:114-115`,
    `energy/economics.py:55-78`, `energy/nearshade.py:32-34`, `ui/view3d.py:205` [V].
14. **Dipendenze e licenze** (sezione 7): `requests` e `pandas` fuori da `requirements.txt`; nessun file delle
    attribuzioni; «About» incompleto (`ui/window.py:2386-2390`); PySide6_WebEngine nel venv; nessun
    `pyproject.toml` [V].
15. **Dettagli di rete** (sezione 6.3): PCN in HTTP (`tiles.py:52`); `energy/pvgis.py:46` senza User-Agent;
    `PVcalc` una richiesta per campo (`ui/window.py:230-234`) [V].
16. **Immagine troppo grande o non immagine**: accettata, disegnata come niente, senza avviso
    (`ui/underlays.py:87-96`; nessun controllo in `model.py:450-451`) [V].

## 10. Verdetto e raccomandazione

**Nucleo: tieni.** Nove moduli su dieci sono scritti come si deve: un docstring che dice il perché e la fonte,
nessun Qt, nessun ciclo, test accanto. Da pulire la lettura del file (`model.py`, da rifare), le tre catene lunghe
(`simulate`, `evaluate`, `compute`, da spezzare a passi, e il tema B ne ha bisogno per confrontare un passo alla
volta), le due note non traducibili, l'italiano fisso. `updates.py` e `minisign.py` vanno collegati nel tema H, non
riscritti.

**Finestra: rifai a pezzi, non di getto.** `ui/window.py` è il punto dove tutto si tocca: 2.074 righe di classe,
il calcolo dell'energia dentro, 45 moduli importati. La strada che non butta via nulla: (1) `EnergyJob._compute` e
`_strings` diventano un modulo del nucleo (`energy/run.py` o simile) con i suoi test senza Qt; (2) `SiteDialog` e
la geocodifica in un modulo loro; (3) `MainWindow` divisa per responsabilità (file e ripristino; azioni e menu;
selezione e viste; energia e verifiche; varianti), ognuna una classe o un modulo di 200-400 righe che riceve la
finestra; (4) `PlanView` divisa in strumenti di disegno, scelta e selezione, tasselli, sovrapposizioni. Il progetto
dell'interfaccia del tema E decide l'ordine; il tema G dice solo che si può fare senza riscrivere il nucleo.

**Prima di tutto, tre cose piccole e urgenti** (un giorno in tutto): la validazione di `from_json` con un
messaggio in parole e la sostituzione del progetto solo a lettura finita; un `sys.excepthook` che scriva su un
log in `paths.state` e mostri «Meridiana ha incontrato un errore: <riga>, il dettaglio è in <file>»; il
collegamento di `tileFailed`, degli errori di autosave e delle impostazioni alla barra di stato. Poi la pagina
delle preferenze sulla riservatezza (quali servizi, che cosa ricevono, come spegnerli) e l'EXIF tolto dalle
immagini importate.

## 11. Che cosa non ho fatto e che cosa resta da provare sul PC

- Nessuna chiamata di rete: i timeout e i comportamenti senza rete sono letti dal codice e da `QNetworkRequest`,
  non misurati su un server che non risponde.
- Nessun PDF malevolo dato a `QtPdf`; nessuna prova di memoria su immagini fra 4.096 e 8.000 px di lato
  (il caso da 6.000 px si decodifica in 144 MB) [V].
- La suite dei test e `ruff` non sono stati lanciati (tema D): le misure qui sono statiche e sulle prove scritte
  apposta.
- Da provare sul PC con la finestra vera: che cosa vede l'utente quando uno slot solleva (su schermo, con la build
  PyInstaller senza console); il PCN giù con la pianta aperta; «Trova il sito» con la rete staccata (resta su
  «Searching…»?); l'EXIF di una foto importata, riletto dal file `.meridiana` con un visualizzatore di metadati.
