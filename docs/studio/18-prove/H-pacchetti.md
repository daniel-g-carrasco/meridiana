# Tema H della revisione completa: pacchetti, rilascio, CI e documentazione

Prova del 23/10/2026 per `docs/studio/18-revisione-completa.md`, sezione H. Il programma non è stato toccato: nessun build, nessuna installazione. Le misure stanno in `H-pacchetti-risultati.txt`, gli script in `H-ci-minuti.sh` e `H-ci-minuti.py`, il flusso CI proposto in `H-ci-proposta.yml`. Ogni affermazione è marcata [V] (verificata, e come) o [I] (dedotta, con la fonte). Le fonti web sono in fondo, con la data di lettura.

## 0. In breve

- **Le ricette di pacchetto sono ancora quelle dell'app campione GTK** [V, lettura]: la spec di PyInstaller cerca MSYS2, `gdbus.exe`, l'hook di `gi` e due moduli che non esistono; il manifest Flatpak monta il runtime GNOME 50 senza PySide6, numpy, scipy, pandas, matplotlib, shapely, pvlib e senza rete; gli script delle icone importano `gi`; il `.desktop`, il metainfo, il sito, il CHANGELOG 0.1.0 e due docstring parlano ancora di «una cartella contata». Nessuno dei due pacchetti si può costruire oggi.
- **Per PySide6 6.12 il lavoro è noto e misurato** [V misure, I esiti]: PyInstaller 6.22.3 ha gli hook per tutto (QtQuick3D, QML, traduzioni `qtbase_*.qm`, matplotlib, scipy, pandas, shapely, h5py); le due trappole sono il wheel `PySide6_WebEngine` che il meta-pacchetto installa (132 MB scaricati a ogni giro di CI, 194 MB di DLL che l'hook QML trascina nel bundle) e il manifest Windows con `dpiAware=true`, che blocca Qt sul DPI «di sistema» e sfoca la finestra sul secondo schermo di Daniel. Installer atteso 120-160 MB, 400-500 MB su disco [I].
- **Flatpak**: runtime KDE 6.11 con il BaseApp `io.qt.PySide.BaseApp//6.11` (PySide 6.11.2) e le dipendenze Python da wheel fissati con `flatpak-pip-generator`; non esiste ancora un runtime 6.12 su Flathub [V]. Il pin `PySide6==6.12.0` va provato su 6.11.2 (l'API di `getInstanceBuffer` è stata provata solo su 6.12.0) o si passa al wheel 6.12 dentro il Flatpak [I]. Permessi: rete (PVGIS, Nominatim, tasselli) e cartella home in scrittura (`.bak` e `_Rnn` accanto al progetto).
- **L'aggiornatore è codice morto** [V, grep]: `updates.py` e `minisign.py` sono pronti e testati, ma nessuno li chiama dalla finestra Qt; `check_updates` sta in `config.py` senza voce nelle Preferenze; `CODE_SIGNING.md` promette un controllo che non avviene. La firma minisign con la chiave comune delle altre app è già prevista (chiave pubblica in `updates.py:50`); manca il workflow che firma e il segreto nel repository.
- **Il CI** [V, gh]: 127 run in tre giorni, 973 minuti fatturati (337 Linux, 636 Windows), il job Windows a ogni push di ogni richiesta di unione e senza cache; dal 23/10 alle 12:14 GitHub rifiuta i job («recent account payments have failed or your spending limit needs to be increased»). Il flusso proposto (`H-ci-proposta.yml`) costa 3 minuti a push e 30-40 a tag.
- **Documentazione**: `progetto.md` e `funzionalita.md` sono buoni ma datati nell'intestazione e muti sul rilascio; il manuale non esiste: proposta in 8.5 (Markdown in `docs/manuale/`, spedito con il programma, aperto in un `QTextBrowser` con F1, tenuto allineato da test).
- **Fatica complessiva**: 9-12 giorni, in sei pezzi indipendenti (sezione 10).

## 1. Metodo

Letti per intero: `build-aux/` (spec, iss, manifest, main, manifest Flatpak, i tre workflow GTK parcheggiati), `.github/workflows/test.yml`, `tools/`, `requirements.txt`, `CHANGELOG.md`, `README.md`, `CODE_SIGNING.md`, `.gitignore`, `bin/meridiana`, `site/index.html`, `data/*.desktop`, `data/*.metainfo.xml`, `src/meridiana/{__init__,__main__,app,paths,i18n,config,updates,minisign,log,recovery,atomic}.py`, `src/meridiana/ui/{qt_translations,view3d}.py`, `src/meridiana/ui/qml/Scene.qml`, `tests/{_setup,test_updates,test_i18n,test_release,test_app}.py`, `docs/progetto.md`, `docs/funzionalita.md`, `docs/richieste.md`, la sezione E di `docs/studio/17-interfaccia.md` e `docs/compiti/17d-aiuti.md`; in sola lettura i documenti del template (`app-template/docs/03-windows.md`, `04-linux.md`, `05-ci-rilascio.md`, `08-trappole.md`) e la skill `nuova-app`.

Misurato sul PC di Daniel (Windows 11, venv `C:\Users\utente\dev\meridiana\.venv`, Python 3.12.6, PySide6 6.12.0, PyInstaller 6.22.3): le dimensioni di ogni pacchetto installato, del wheel Windows di PySide6 pezzo per pezzo (DLL, `.pyd`, plugin, QML, traduzioni, resources), e che cosa fanno gli hook di PyInstaller per PySide6 (letti in `site-packages/PyInstaller`, con file e riga). Con `gh` in sola lettura: tutti i run del CI con la durata di ogni job, i rami del BaseApp PySide su Flathub e il suo manifest, gli SHA delle azioni da ancorare; dal WSL del PC `flatpak remote-ls flathub` per i runtime KDE pubblicati. Sul web: le pagine di PyPI (dimensioni dei wheel), di GitHub (fatturazione, immagini dei runner), di Flathub e flatpak-builder-tools, di Qt e di Microsoft (DPI). Dove un esito dipende da un build che non ho eseguito, sta scritto [I].

## 2. Le ricette di oggi: che cosa è ancora dell'app GTK

### 2.1 Windows (`build-aux/windows/`)

| Dove | Che cosa c'è | Effetto con PySide6 |
|---|---|---|
| `meridiana.spec:2-5,11` | Commento MSYS2 UCRT64; `prefix = sys.prefix` come `C:/msys64/ucrt64` | Il build si fa dal venv di python.org: il prefisso non ha `bin/gdbus.exe` né `etc/ssl` (solo avvisi) [V lettura] |
| `meridiana.spec:21-27` | `gdbus.exe` nel bundle per l'istanza unica di GApplication | Non serve a Qt; l'istanza unica, se la si vuole, è un `QLocalServer` [I] |
| `meridiana.spec:29-36` | Il CA bundle di MSYS2 per `updates.ssl_context` | Con il Python di python.org `ssl.create_default_context()` legge lo store di Windows; `QtNetwork` usa Schannel (`plugins/tls/qschannelbackend.dll`); `requests` porta certifi [I] |
| `meridiana.spec:44` | `hiddenimports=['meridiana.win32', 'meridiana.wintoast', 'meridiana.minisign']` | `win32.py` e `wintoast.py` non esistono in `src/meridiana` (78 file elencati) [V]: PyInstaller avvisa «hidden import not found» e va avanti [I] |
| `meridiana.spec:45-46` | `hooksconfig` per `gi` (GTK 4, Adw) | Ignorato senza `gi`; con PySide6 serve semmai `hooksconfig={'matplotlib': {'backends': ['QtAgg', 'Agg']}}` (charts.py:21 usa `QtAgg`, report.py:31 `Agg`) [V codice, I opzione] |
| `meridiana.spec:13-19` | `datas`: `data/icons` e `data/fonts` in `share/`, `locale/` in `share/locale` | Giusto anche per Qt: `paths.shipped` cerca `_MEIPASS/share` (paths.py:64-65) e `i18n` cerca `_MEIPASS/share/locale` (i18n.py:21-22) [V] |
| `meridiana.spec:48-62` | `excludes=['tkinter']`, `console=False`, `COLLECT` in cartella | Da tenere; mancano le esclusioni e la potatura di Qt (sezione 3.2) |
| `meridiana.iss` | Inno Setup: per utente senza UAC, `CloseApplications`, `[InstallDelete]` di `_internal`, `AppUserModelID`, chiave di registro dei toast cancellata alla disinstallazione (:90-96) | Vale quasi tutto anche per Qt; la chiave dei toast è dell'app GTK; manca l'associazione del tipo `.meridiana` (`[Registry]`) [V lettura] |
| `meridiana.manifest:5-12,33` | `dpiAware=true` (consapevolezza «di sistema») con il commento su GTK che non scala a frazioni | **Qt 6 è «Per-Monitor DPI Aware V2» per impostazione** (doc.qt.io/highdpi) e lo imposta all'avvio; Windows rifiuta il cambio se il manifest ha già deciso: «ERROR_ACCESS_DENIED if the default API awareness mode for the process has already been set (via a previous API call or within the application manifest)» (learn.microsoft.com, `SetProcessDpiAwarenessContext`). Con questo manifest Windows ridimensiona lui la finestra sul monitor a scala diversa: sfocata sul secondo schermo di Daniel (rapporto 2,5, `CLAUDE.md`) [V fonti, I effetto fino alla prova] |
| `meridiana_main.py` | `from meridiana.__main__ import main` | Va bene com'è [V] |

### 2.2 Strumenti (`tools/`)

- `make_ico.py:14-17` e `make_icons.py:16-18` importano `gi` e `GdkPixbuf`: non ci sono nel venv Qt (pip list) [V]. Rifare con Pillow (già installato da matplotlib: `Image.save(..., sizes=[...])` scrive un `.ico` a più misure) o con `QSvgRenderer` + `QImage` [I].
- `compile_po.py:41` chiama solo `msgfmt`: il runner Windows di GitHub non ha gettext, e il job Windows di oggi non compila i cataloghi (`test.yml:49-50`); `test_i18n.py:18` salta senza `locale/it`. Serve un ripiego in Python (`polib`, già nello script cloud, o `Tools/i18n/msgfmt.py` di CPython), oppure i cataloghi compilati su Linux e passati come artifact (così fa `H-ci-proposta.yml`) [V lettura].
- `flatpak_repo_files.py:19` ha ancora la descrizione dell'app campione e `:74` punta a `README#flatpak`, un'ancora che nel README non c'è [V].
- `cloud-setup.sh:11` installa `polib`, che nessun file di `src`, `tests` e `tools` importa [V grep].

### 2.3 Flatpak (`build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml`)

- `:14-17` runtime `org.gnome.Platform//50`: non contiene Qt né PySide6; `:35-44` installa solo i sorgenti, i font, le icone e i cataloghi; non un modulo Python delle dipendenze. `/app/bin/meridiana --version` (`:55`) passa perché `__main__.py:23-25` risponde prima di importare Qt: il build riuscirebbe e l'app non partirebbe [V lettura].
- `:19-33` permessi: `--filesystem=home:ro` (motivato dal contare le cartelle) e `xdg-config/gtk-4.0:ro`; **manca `--share=network`**: PVGIS (`energy/meteo.py:32-33`), Nominatim (`ui/window.py:352`), i tasselli (`tiles.py:52-60`) e GitHub non raggiungibili. E con la home in sola lettura `atomic.write_json` non può scrivere il `.bak` accanto al progetto (`atomic.py:27-28`) né la revisione `_Rnn` (`recovery.py:56-66`) [V lettura].
- Gli script del CI in `build-aux/ci-gtk-da-adattare/` montano il container `flatpak-github-actions:gnome-50` (`build.yml:25`, `flatpak-repo.yml:40`) e, per Windows, MSYS2 con GTK 4 e libadwaita (`windows.yml:39-46,94-103`), con i controlli su `gi_typelibs`, `gdbus.exe`, `gtk4-update-icon-cache` (`:109-128`) [V].

### 2.4 Identità e testi dell'app campione

`data/io.github.daniel_g_carrasco.meridiana.desktop:9-11` (`Categories=Utility;GTK;`, `Keywords=files;folder;count;`); `data/...metainfo.xml:20-24` (descrizione «counts the files of a folder», anche in italiano), `:37-38` (i blu di GNOME), `:53-57` (release 0.1.0 «a folder counted»), nessuna `<screenshots>`; `site/index.html:6-7,51-52,69-71` (stessa app) e `:74` «MIT licence» contro la GPL; `CHANGELOG.md:91-96` (0.1.0 «a folder counted») e `:3-6` (la promessa degli aggiornamenti Flatpak dal repository proprio); `src/meridiana/__init__.py:1-9` (docstring GTK); `src/meridiana/__main__.py:28` («usage: {command} [FOLDER...]»); `updates.py:1-2` (su Linux «the Flatpak brings it, from GNOME Software») [V lettura]. `tests/test_release.py` controlla la coerenza di versione fra codice, CHANGELOG e metainfo, non i contenuti: per questo passano.

### 2.5 Dipendenze

- `requirements.txt:6` `PySide6==6.12.0` è il meta-pacchetto: su PyPI richiede `PySide6_Essentials`, `PySide6_Addons`, `PySide6_WebEngine==6.12.0.140` e `PySide6_Pdf==6.12.0.140` [V pip show e PyPI]. Meridiana importa QtCore, QtGui, QtWidgets, QtNetwork, QtSvg, QtQml, QtQuick3D, QtQuickWidgets, QtPdf e QtDBus (solo Linux) [V grep]; WebEngine mai. Il wheel WebEngine pesa 131,7 MB (Windows) e viene scaricato a ogni giro del CI; nel venv sono 194 MB di `Qt6WebEngineCore.dll` più 101 MB di resources [V].
- `requests` è importato direttamente (`meteo.py:137,155,204`, `pvgis.py:44`, `tests/test_meteo.py:14`) ma arriva solo come dipendenza di pvlib [V]. Va scritto.
- `h5py` è richiesto da pvlib e importato a livello di modulo (`pvlib/clearsky.py:12`, `pvlib/location.py:13`): entra nel bundle con le DLL HDF5 anche se Meridiana non lo usa [V].

## 3. Che cosa serve per PySide6 6.12 su Windows

### 3.1 Come lavora PyInstaller 6.22.3 con PySide6 (fatti letti nel codice degli hook)

- Il pacchetto congelato tiene Qt in `_MEIPASS/PySide6` su Windows (`PySide6/Qt` su Linux e macOS): `hooks/rthooks/pyi_rth_pyside6.py:26-31,48`; il run-time hook imposta `QT_PLUGIN_PATH` e `QML2_IMPORT_PATH` e registra un `qt.conf` incorporato con `Prefix = <_MEIPASS>/PySide6` (`fake-modules/_pyi_rth_utils/qt.py:82-85`): quindi `QLibraryInfo.path(TranslationsPath)` risponde `<_MEIPASS>/PySide6/translations` [V].
- **Le traduzioni**: la tabella dei moduli dichiara per QtCore `translations=["qt", "qtbase"]` (`utils/hooks/qt/_modules_info.py:175`) e l'hook raccoglie `qt_*.qm` e `qtbase_*.qm` di tutte le lingue in `<qt_rel_dir>/translations` (`utils/hooks/qt/__init__.py:461-478`): 99 file, 6,7 MB, con `qtbase_it.qm` (157 KB) [V]. Quindi la nota [I] del diario (`docs/progetto.md:167`) diventa [V] per la raccolta; `qt_translations.folders()` trova il catalogo dal primo elemento (QLibraryInfo). I due percorsi espliciti per il congelato in `ui/qt_translations.py:28` (`PySide6/Qt/translations`, `share/qt/translations`) sono quelli di Linux: innocui su Windows, da correggere in `PySide6/translations` per robustezza [V lettura, I esito a build fatto]. Si può potare tutto tranne `*_it.qm` e `*_en.qm` dopo l'analisi.
- **Il QML**: `hook-PySide6.QtQml.py` chiama `collect_qtqml_files` (`__init__.py:916-967`), che raccoglie **ogni** cartella con un `qmldir` nella directory `qml` del wheel (20,2 MB: QtQuick 10,4, QtQuick3D 2,5, ma anche Qt3D, QtCharts, QtGraphs, QtMultimedia, QtLocation, Qt5Compat, QtWebEngine); un plugin è scartato solo se una sua dipendenza Qt manca o si risolve fuori dalla cartella di Qt (`:550-575`). Le DLL di cui i plugin hanno bisogno seguono per analisi dei binari: con `PySide6_WebEngine` nel venv, `qml/QtWebEngine` passa e porta `Qt6WebEngineCore.dll` (194 MB) [V lettura, I misura finale]. Non esiste un'opzione di `hooksconfig` per escludere plugin, QML o traduzioni di Qt (pyinstaller.org/hooks-config, 23/10/2026) [V].
- **Qt Quick 3D**: `QtQuick3D` è in `_modules_info.py:324` senza plugin propri; `Scene.qml` importa `QtQuick`, `QtQuick3D`, `QtQuick3D.Helpers` e il modulo `Meridiana` registrato da Python (`view3d.py:28-33`, `QmlElement`), caricato da file (`:382`): il file `.qml` va nei `datas` del pacchetto (`src/meridiana/ui/qml/Scene.qml`, non raccolto da solo) [V lettura]. Le DLL necessarie, sommate dal wheel: 73,5 MB (Core, Gui, Widgets, Network, Qml, Quick, Quick3D e famiglia, ShaderTools, OpenGL, Pdf, Svg, PrintSupport, Controls2 e Dialogs2 che i plugin QML di `QtQuick` trascinano), più 23,2 MB di `.pyd`, più `opengl32sw.dll` 19,7 MB (raccolto da `collect_extra_binaries`, `:628-648`) [V].
- **Plugin**: per modulo (platforms 2,2 MB, imageformats 2,4, tls 0,6, iconengines, styles, generic, platforminputcontexts, networkinformation; qmltooling 1,3 è il debugger QML, da togliere) [V elenco].
- **matplotlib**: l'hook raccoglie `mpl-data` (10 MB) e i backend secondo `hooksconfig['matplotlib']['backends']` ('auto' per impostazione, cerca `matplotlib.use()`: `charts.py:21` dichiara `QtAgg`) [V]. **pvlib**: nessun hook; i suoi 29 MB di dati (`pvlib/data`: liste CEC e `.h5`) non vengono raccolti, e Meridiana non li usa (chiama solo `get_pvgis_tmy` e `get_pvgis_horizon`, `meteo.py:138,205`) [V]. **scipy, pandas, numpy, shapely, h5py**: hook presenti (PyInstaller e hooks-contrib) [V elenco].

### 3.2 La spec da scrivere (i pezzi)

1. `Analysis` con `pathex=[src]`, `datas`: `data/icons`, `data/fonts`, `locale/` (in `share/...`), `src/meridiana/ui/qml/Scene.qml` (in `meridiana/ui/qml`), i cataloghi `src/meridiana/catalog/data` (`catalog/__init__.py:22` li legge accanto al modulo; PyInstaller non prende i file non Python di un pacchetto senza `collect_data_files('meridiana')` o una voce in `datas`), e in futuro il manuale; `hiddenimports` nessuno (gli import sono espliciti); `excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick', 'PySide6.Qt3DCore', 'PySide6.QtCharts', 'PySide6.QtMultimedia', ...]`; `hooksconfig={'matplotlib': {'backends': ['QtAgg', 'Agg']}}`.
2. **Potatura** dopo l'analisi (`a.binaries`, `a.datas` filtrati per prefisso): `PySide6/qml/{QtWebEngine,Qt3D,QtCharts,QtGraphs,QtDataVisualization,QtMultimedia,QtLocation,QtPositioning,Qt5Compat,QtRemoteObjects,QtScxml,QtSensors,QtTest,QtTextToSpeech,QtWebChannel,QtWebSockets,QtWebView}`, le DLL `Qt63D*`, `Qt6Charts*`, `Qt6Graphs*`, `Qt6Multimedia*`, `Qt6Location*`, `Qt6Positioning*`, `Qt6WebEngine*`, `Qt6Designer*`, i plugin `qmltooling`, `sqldrivers`, `sceneparsers`, `renderers`, `assetimporters`, le traduzioni diverse da `*_it.qm` e `*_en.qm`. Più semplice e sicuro: **nel venv del build non installare `PySide6` ma `PySide6_Essentials`, `PySide6_Addons`, `PySide6_Pdf`** (il wheel WebEngine sparisce e il suo plugin QML viene scartato da solo perché le DLL mancano) [I dalla lettura di `:550-575`]. Lo fa `H-ci-proposta.yml` (`pip uninstall -y PySide6 PySide6_WebEngine`).
3. `EXE` con `console=False`, l'icona, un manifest nuovo: `<dpiAwareness>PerMonitorV2</dpiAwareness>` (o nessun elemento DPI, lasciando fare a Qt), `longPathAware` sì, i `supportedOS` e `requestedExecutionLevel asInvoker` come oggi. Da provare sul PC con i due monitor [I].
4. `COLLECT` in cartella (mai onefile: estrazione a ogni avvio e la vista 3D).
5. Controlli del bundle (nel CI, `H-ci-proposta.yml`): esistono `PySide6/translations/qtbase_it.qm`, `PySide6/qml/QtQuick3D/qmldir`, `PySide6/qml/QtQuick3D/Helpers/qmldir`, `PySide6/plugins/platforms/qwindows.dll`, `share/locale/it/LC_MESSAGES/meridiana.mo`, i font; non esistono `Qt6WebEngineCore.dll`, `qml/QtWebEngine`, `Qt63DRender.dll`.

### 3.3 Inno Setup

Resta quasi tutto (`PrivilegesRequired=lowest`, `CloseApplications`, `[InstallDelete]`, `[Run]` con `runasoriginaluser`). Da togliere la chiave dei toast (`:90-96`); da aggiungere `[Registry]` per `.meridiana` (ProgID, icona, `Open`) e `ChangesAssociations=yes`; `CheckForMutexes('')` (`:86`) non controlla nulla: o un mutex vero (`AppMutex` in `[Setup]` e `QLocalServer`/`QSharedMemory` nell'app), o solo `FindWindowByWindowName` [V lettura, I proposta].

### 3.4 La dimensione attesa [I, dai numeri misurati]

Su disco (cartella `dist/Meridiana`): Qt necessaria circa 150 MB (DLL 60-74, `.pyd` 23, `opengl32sw` 20, plugin 8, QML QtQuick e QtQuick3D 15, traduzioni 7 o 0,3 se potate); Python 3.12 e libreria 20; numpy 51; scipy 60-128 (gli hook prendono i sottopacchetti importati e le loro DLL; pvlib importa `optimize`, `special`, `interpolate`, `linalg`); pandas 60; matplotlib con Pillow e fontTools 64; shapely 6; h5py e HDF5 10; pvlib (solo codice) 2; requests e compagnia 3; Meridiana con i cataloghi 4; font e icone 0,5. **Totale 400-500 MB.** L'app GTK campione pesava 130-140 MB (`03-windows.md`): Meridiana è tre volte tanto, e il grosso è numerico (scipy, pandas, numpy), non Qt.

Installer Inno (LZMA2 solido) e zip portabile: i wheel compressi danno il riferimento (`H-pacchetti-risultati.txt`, 4): la parte usata di Essentials 50-55 MB, Quick3D da Addons 8, Pdf 3, shiboken 1,3, numpy 12,6, scipy 20-37, pandas 9,7, matplotlib e Pillow e fontTools 22, shapely 1,8, h5py 3,2, Python 11, Meridiana 3: **installer 120-160 MB**, zip 150-180 MB. Un download accettabile per un progettista, lontano dai 40-60 MB a cui le app del template abituano. Si scende solo rinunciando a pandas (pvlib lo richiede) o a scipy (serve a pvlib e al punto di massima potenza `chandrupatla`, `requirements.txt:4-5`): non ora.

### 3.5 Il build in locale e nel CI

Dal venv di python.org (3.12, come oggi), senza MSYS2: `python tools/compile_po.py` (su Windows serve il ripiego di 2.2 o i `.mo` già compilati), `python tools/make_ico.py` (riscritto), `pyinstaller --noconfirm build-aux/windows/meridiana.spec`, poi `ISCC.exe /DAppVersion=... build-aux\windows\meridiana.iss`. Sul runner `windows-2025` Inno Setup 6.7.1, Python 3.12.10 e 7zip 26.04 sono preinstallati (immagine 20261021.299.1) [V]: il download e il controllo SHA-256 di `windows.yml:149-160` non servono più (restano come ripiego nel file proposto).

## 4. Flatpak

### 4.1 Runtime e BaseApp (stato al 23/10/2026)

- Flathub pubblica `org.kde.Platform` e `org.kde.Sdk` nei rami `5.15-25.08`, `6.10`, `6.11` [V, `flatpak remote-ls flathub --runtime` dal WSL del PC]. Il ramo `qt6.12` del runtime KDE esiste su invent.kde.org (ultimo commit 06/10/2026) ma non è pubblicato [V, API GitLab].
- `io.qt.PySide.BaseApp` ha i rami `branch/6.7 ... branch/6.11`; nessun 6.12. Il 6.11 (ultimo commit 15/09/2026 «Update to 6.11.2») compila `pyside-setup v6.11.2` contro il Qt del runtime, parte da `io.qt.qtwebengine.BaseApp//6.11` e lascia uno script `/app/cleanup-BaseApp.sh` con `BASEAPP_REMOVE_WEBENGINE` e `BASEAPP_DISABLE_NUMPY` [V manifest letto via API]. Il 21/10/2026 il template ha provato questo BaseApp su niri: Quick 3D presente, GPU funzionante nella sandbox (`04-linux.md`, «Flatpak io.qt.PySide.BaseApp//6.11») [V doc].
- Il BaseApp installa anche `libLLVM.so.21`, `libclang-cpp.so.21`, `libclang.so.21` in `/app/lib` (servono a shiboken per generare, non all'app): lo script di pulizia non li toglie; l'app li toglie da sé in `cleanup` [V manifest, I dimensione: 100-150 MB].

**La scelta da fare**: `requirements.txt` fissa `PySide6==6.12.0` perché `QQuick3DInstancing.getInstanceBuffer` ha cambiato firma fra le versioni (`view3d.py:78-79`, provata solo su 6.12.0). Tre vie:
- (A) **BaseApp 6.11 (PySide 6.11.2) e il pin allargato a `>=6.11`** dopo aver fatto girare la suite su 6.11.2 (mezza giornata, sul laptop o in un venv a parte); se `getInstanceBuffer` differisce, un ramo per versione nel codice. È la via del template e di Flathub (un runtime, un Qt, un solo PySide) [I].
- (B) **Il wheel manylinux di PySide6 6.12.0 dentro il Flatpak** (Essentials 84,3 MB + Addons 59,2 + Pdf 2,8 + shiboken 0,3 compressi) su `org.kde.Platform//6.11` o sul Freedesktop 25.08: il wheel porta il suo Qt 6.12 intero, autosufficiente come su Windows; nessuna prova fatta nella sandbox (plugin `wayland`/`xcb` del wheel contro le librerie del runtime) [I]. Costo: 150 MB in più di download e due Qt.
- (C) **Aspettare il BaseApp 6.12** (il runtime 6.12 è in preparazione): nessuna data [I].

Raccomandazione: (A), con (B) come ripiego se la 6.11.2 non regge l'instancing.

### 4.2 Il manifest proposto (schema)

```yaml
app-id: io.github.daniel_g_carrasco.meridiana
runtime: org.kde.Platform
runtime-version: '6.11'
sdk: org.kde.Sdk
base: io.qt.PySide.BaseApp
base-version: '6.11'
command: meridiana
finish-args:
  - --share=ipc
  - --socket=wayland
  - --socket=fallback-x11
  - --device=dri                 # Qt Quick 3D sulla GPU
  - --share=network              # PVGIS, Nominatim, tasselli delle mappe, aggiornamenti
  - --filesystem=home            # il .bak e le revisioni _Rnn accanto al file di progetto (atomic.py, recovery.py)
cleanup-commands:
  - /app/cleanup-BaseApp.sh
  - rm -rf /app/lib/libLLVM* /app/lib/libclang*
build-options:
  env:
    BASEAPP_REMOVE_WEBENGINE: '1'
modules:
  - python3-requirements.json    # numpy, scipy, pandas, matplotlib, pillow, fonttools, contourpy, kiwisolver,
                                 # pvlib, h5py, shapely, requests, ...: wheel manylinux fissati da flatpak-pip-generator
  - name: meridiana              # come oggi: sorgenti in /app/share/meridiana, bin, cataloghi, desktop, metainfo, icone
```

`flatpak-pip-generator --runtime org.kde.Sdk//6.11 --requirements-file requirements.txt --prefer-wheels=numpy,scipy,pandas,matplotlib,pillow,fonttools,contourpy,kiwisolver,shapely,h5py` scrive il modulo con `url` e `sha256` per `x86_64` e `aarch64` e `pip install --no-index` (nessuna rete nel build: Flathub, requisiti) [V readme e docs]. `PySide6` va tolto dal file dato al generatore (lo porta il BaseApp). Il launcher `bin/meridiana` trova già `/app/share/meridiana` (`bin/meridiana:9`); `paths.shipped` cerca `/app/share/meridiana/<fonts|icons>` (`paths.py:66`); `compile_po.py --dest /app/share/locale` ha `msgfmt` nell'SDK [V].

Permessi, con la regola di Flathub «Static permissions must be kept to an absolute minimum» e «using the portal becomes mandatory instead of static permissions» dove un portale basta [V docs]: i file di progetto passano dai dialoghi (portale) e basterebbe questo per aprire e salvare un file; ma `.bak` e `_Rnn` sono file nuovi accanto a quello scelto, che il portale dei documenti non concede: da qui `--filesystem=home` (Spola) o `host` (p7m, `04-linux.md`) [V doc, I per Meridiana]. Via `xdg-config/gtk-4.0:ro` e `home:ro`. Il salvataggio automatico sta in `state` (`recovery.py:21-27`) e le cache in `cache` (`meteo.py:94-95`, `tileloader.py`): dentro `~/.var/app/<id>/`, nessun permesso [V]. `gdbus` per l'accento del portale (`ui/theme.py:157`) è nel runtime Freedesktop [I].

### 4.3 Dimensione attesa [I]

Installata: dipendenze Python 350 MB (numpy 51, scipy 128, pandas 60, matplotlib e Pillow e fontTools 64, pvlib 31 con i dati che il wheel porta, h5py 10, shapely 6), PySide6 dal BaseApp dopo la pulizia 60-100 MB (solo i binding, il Qt è del runtime), Meridiana 5: **400-450 MB** (più 100-150 se si lasciano LLVM e clang). Download dal repository ostree 130-180 MB; il runtime KDE 6.11 in più la prima volta (circa 1 GB), condiviso con le altre app Qt.

### 4.4 Repository proprio, bundle, metainfo

`flatpak-repo.yml` (repo ostree su `gh-pages` firmato GPG, `.flatpakref`) e `build.yml` (bundle firmato minisign allegato alla release) restano validi cambiando il container (`flatpak-github-actions:kde-6.11`) e il manifest [V lettura]; servono la chiave GPG dedicata (`FLATPAK_GPG_PRIVATE_KEY`, `FLATPAK_GPG_KEY_ID`) e Pages, che su un repository privato con il piano gratuito non si attiva (`04-linux.md`) [V doc]. Il metainfo va riscritto (descrizione, `<screenshots>` con immagini raggiungibili, `<releases>` vere, i colori Meridiana) e il `.desktop` (`Categories=Science;Engineering;Qt;`, `Keywords`, `MimeType=application/x-meridiana;` con il file `mime/packages` relativo).

## 5. L'aggiornatore e la firma

### 5.1 Che cosa fa `updates.py` (letto riga per riga)

- Chiede a `https://api.github.com/repos/daniel-g-carrasco/meridiana/releases/latest` con la libreria standard (`:40,118-120`), legge al massimo 1 MB (`:55,146-148`), confronta la versione (`:91-93`).
- Accetta solo l'installer chiamato `meridiana-setup-v<versione>-windows-x64.exe` della stessa release, scaricato da `github.com/.../releases/download/`, con lo SHA-256 che GitHub pubblica (`digest`) e il `.minisig` accanto (`:43,161-168`): un installer di un'altra versione, pur firmato, è rifiutato (`:13-17`, test `test_updates.py:69-74`).
- Scarica in una cartella temporanea propria, non più byte di quanti la release dichiara (`:241-250`), controlla dimensione e SHA-256 (`:258-259`), verifica la firma Ed25519 di minisign sul BLAKE2b-512 del file e il commento fidato, che deve nominare il file (`:261-267`, `minisign.py:112-136`), poi tiene aperto l'installer senza condivisione di scrittura fino all'uscita (`hold`, `:183-202`) perché Setup lo rilegga intatto [V].
- Decide da sé di essere «l'app installata» solo se accanto all'exe c'è `unins000.exe` (`:97-100`); dai sorgenti e dallo zip apre la pagina della release [V].
- La chiave pubblica è quella condivisa dalle app di Daniel, id `CEFFF9269F08F845` (`:45-50`; `CODE_SIGNING.md:14-16`); la metà segreta sta in `C:\Users\utente\.config\minisign-app-releases` (non letta, citata dal template `05-ci-rilascio.md`) [V].

### 5.2 Che cosa non fa

- **Nessuno lo chiama**: `grep -rn "updates\|minisign" src/meridiana` fuori dai due moduli trova solo `config.py:87-88` (`check_updates`, `last_update_check`), che nessun altro file legge; `ui/preferences.py` non ha la casella; il menu Aiuto ha solo Scorciatoie e Informazioni (`ui/window.py:810-813`) [V]. La finestra di dialogo dell'app GTK (`update_dialog.py` del template) non è stata portata.
- `CODE_SIGNING.md:9-12` e `:36-42` descrivono un controllo giornaliero che non esiste [V].
- `tests/test_updates.py:143-150` controlla che il workflow Windows verifichi con la stessa chiave, ma salta perché `.github/workflows/windows.yml` non c'è: il legame chiave-CI oggi non è provato da nulla [V].
- Su Linux l'aggiornamento è del Flatpak (repository proprio, `flatpak-repo.yml`), parcheggiato [V].

### 5.3 Da fare

1. Portare in Qt il pezzo mancante: un `QRunnable` che 60 s dopo l'avvio, al massimo una volta al giorno e se `cfg.check_updates`, chiama `latest_release()`; una finestra con le note, «Scarica e installa» (progresso, annulla), «Più tardi», «Apri la pagina»; `Aiuto > Cerca aggiornamenti`; la casella in Preferenze; `clean_downloads()` all'avvio. Test offscreen con `MERIDIANA_DEV_RELEASE_API` (già previsto, `updates.py:139-143`). Un giorno.
2. Il workflow di release (in `H-ci-proposta.yml`, job `release`): firma installer e zip con `MINISIGN_SECRET_KEY`, verifica con la chiave pubblica scritta nel workflow, carica i `.minisig`; `gh secret set MINISIGN_SECRET_KEY` dalla chiave condivisa (sintassi in `02-guida.md` del template) dopo il sì di Daniel. `test_updates.KeyTest` va puntato al file nuovo (o il file si chiama `windows.yml`).
3. La rotazione della chiave non ha ancora un piano (lo dice il template): un'app che accetta due chiavi pubbliche per un periodo. Non urgente.
4. `CODE_SIGNING.md` e la privacy policy vanno riscritti sui fatti: il Flatpak non controlla; Windows controlla solo se abilitato; i dati del progetto non escono mai; PVGIS, Nominatim e i tasselli sì (coordinate del sito, indirizzo cercato): va detto lì e nel manuale.

### 5.4 Versione, CHANGELOG, metainfo

Oggi: `__version__ = "0.1.0"` (`__init__.py:13`), `CHANGELOG.md` con `[Unreleased]` di 45 righe e una voce 0.1.0 dell'app campione, metainfo con la stessa 0.1.0; `test_release.py:19-27` esige che la versione in testa a CHANGELOG e metainfo sia `__version__` [V]. Proposta: la prima release Qt è la **0.2.0**: la voce 0.1.0 resta con una riga che dica «lo scheletro del template, prima di Meridiana»; `[Unreleased]` diventa `[0.2.0] - data` (le parole dell'utente, come il template chiede), il metainfo riceve `<release version="0.2.0">` con un paragrafo; `tools/compile_po.py`, suite, lint, push, CI verde sullo SHA completo, tag `v0.2.0`, controllo dei file della release: la procedura di `05-ci-rilascio.md` vale tale e quale. Il controllo «tag = `__version__`» c'è già in `test.yml:35-41` e nel file proposto. Il `CHANGELOG.md:3-6` va corretto sul come arrivano gli aggiornamenti (Windows dall'app, Linux dal repository Flatpak quando ci sarà).

## 6. Il CI

### 6.1 Oggi [V, `gh`]

`test.yml`: `core-linux` (apt, venv, ruff, `compile_po`, suite offscreen, validatori, controllo del tag) e `core-windows` (pip, suite sul desktop del runner, senza cataloghi né lint), su ogni push a `main`, ogni `pull_request` e `workflow_call`.

| Giorno | Run | Linux (min eseguiti / fatturati) | Windows (min eseguiti / fatturati) |
|---|---|---|---|
| 21/10 | 31 | 59 / 73 | 105 / 123 |
| 22/10 | 45 | 128 / 148 | 265 / 288 |
| 23/10 (fino alle 16) | 51, di cui 14 rifiutati | 98 / 116 | 207 / 225 |
| **Totale** | 127 | **285,6 / 337** (2,53 min per job) | **576,7 / 636** (5,10 min per job) |

GitHub arrotonda ogni job al minuto («GitHub rounds the minutes and partial minutes each job uses up to the nearest whole minute», docs.github.com, prezzi dei runner) [V]: un run medio costa 3 + 6 = 9 minuti fatturati; con il vecchio criterio «Windows conta doppio» sono 15, e i 973 minuti dei tre giorni diventano 1.609 dei 2.000 mensili del piano Free [V quota, I criterio: le pagine di GitHub lette il 23/10/2026, anche quella in giapponese, non riportano più i moltiplicatori 2x e 10x ma i prezzi, Linux 0,006 e Windows 0,010 USD al minuto, cioè Windows a 1,67 volte]. Al prezzo di oggi i tre giorni valgono 8,38 USD. Il blocco è arrivato il 23/10 alle 12:14 con l'annotazione «The job was not started because recent account payments have failed or your spending limit needs to be increased»: coerente con «If your account does not have a valid payment method on file, usage is blocked once you use up your quota» [V], contando che la stessa quota mensile dell'account l'hanno consumata anche i run privati di `app-template` e `app-template-test` del 21/10 (`04-linux.md`) [I].

Perché il job Windows dura 5 minuti: scarica a ogni giro i wheel senza cache (PySide6 intero, compreso WebEngine 132 MB) e fa girare le finestre vere; la suite su Windows dura 4-6 minuti anche sul PC (6,5 minuti il 23/10, `docs/progetto.md:141`) [V].

### 6.2 Il flusso proposto (`H-ci-proposta.yml`)

- **`linux`** a ogni push di qualsiasi ramo: `ubuntu-24.04` (non `ubuntu-latest`, che fra il 19/10 e il 19/11/2026 passa a Ubuntu 26.04, issue 14748 di runner-images [V]), `setup-python` 3.12 con `cache: pip` (la cache dei wheel scaricati, chiave sull'hash di `requirements.txt` [V README di setup-python]), ruff, cataloghi, suite offscreen, validatori, tag uguale a `__version__`; 2-3 minuti fatturati.
- **Niente `pull_request`**: il push del ramo fa lo stesso lavoro e GitHub mostra lo stato sul commit e nella richiesta di unione; oggi un ramo con richiesta aperta spende il doppio (push e pull_request, come il 22-23/10) [V elenco run].
- **`paths-ignore`** per `docs/**`, `**.md`, `site/**`: gli studi e i compiti (la maggior parte dei commit di questi giorni) non consumano nulla. I tag non sono filtrati dai percorsi.
- **`concurrency` con `cancel-in-progress`** sui rami: un push sopra un push cancella il run vecchio.
- **`windows`** solo sui tag `v*` e a mano (`workflow_dispatch` con la casella): `windows-2025`, suite sul desktop del runner, PyInstaller con il venv senza WebEngine, controlli del bundle, prova dell'exe con lo screenshot, zip, Inno Setup preinstallato, installazione silenziosa e aggiornamento sopra l'app in esecuzione; 12-20 minuti, fatturati a 0,010 USD.
- **`release`** sul tag: firma minisign e caricamento (il Flatpak resta in un workflow a parte sul tag).
- Stima mensile: 150 push × 3 minuti = 450, più 2 tag × 40 = 80: **circa 530 minuti al mese** contro i 2.000 e più del ritmo di oggi (127 run in tre giorni × 9-15). La suite completa su Windows prima delle release, non a ogni commit, come Daniel ha già deciso il 23/10 («affidiamoci al repository locale», `docs/richieste.md`).

Alternative: rendere pubblico il repository («GitHub Actions usage is free for ... public repositories», docs.github.com [V]; è una domanda aperta di `docs/progetto.md:114`); un runner self-hosted sul laptop Linux (gratuito, ma deve essere acceso); tenere il CI spento e fare suite e lint sul PC prima di ogni unione (lo stato di oggi).

## 7. La documentazione

### 7.1 `README.md`

Aggiornato nelle funzioni; `:33` dice «Python 3.11 or newer» mentre `CLAUDE.md` e `docs/progetto.md` dicono 3.12+ [V]; manca una sezione per chi installa (installer Windows, zip, Flatpak, aggiornamenti, firma) con l'ancora `#flatpak` che `tools/flatpak_repo_files.py:74` promette; manca la riga sulle reti usate (PVGIS, OSM, PCN) e sulla licenza dei dati. Mezza giornata insieme al sito.

### 7.2 `docs/progetto.md`

Il diario (appendice A) è la parte migliore del repository. Difetti: `:3` «Stato al 22/10/2026 sera» con righe del 23/10; `:105` «Manca ancora il salvataggio automatico» mentre `funzionalita.md:58` lo dà fatto e `recovery.py` esiste [V]; la mappa dei moduli (sezione 2) non elenca `energy/nearshade.py`, `pvsyst/`, `checks.py`, `rules.py`, `compare.py`, `assistant.py`, `recovery.py`, `atomic.py`, `updates.py`, `minisign.py`, `ui/assistant.py`, `ui/checks_page.py`, `ui/variants.py`, `ui/sunbar.py`, `ui/shortcuts_dialog.py`, `ui/pvsyst_import.py` [V confronto con l'elenco dei 78 file]; **non c'è una sezione sul rilascio** (dove si costruiscono installer e Flatpak, con quale Python, le chiavi, la procedura, i file di una release, l'aggiornatore). Proposta: una sezione 4 «Rilascio e pacchetti» di una pagina, da questo rapporto, più la riga nel diario.

### 7.3 `docs/funzionalita.md`

`:3` «Stato al 22/10/2026 mattina» con voci del 23/10 [V]. Manca la sezione «Installazione e aggiornamenti» (installer, zip, Flatpak, aggiornatore, firma: tutte ○ oggi) e la voce «Manuale» (○). Un'ora.

### 7.4 `CHANGELOG.md`, metainfo, `CODE_SIGNING.md`

Visti in 2.4 e 5.4. Mezza giornata per i testi dell'identità (desktop, metainfo con screenshot, sito, `flatpak_repo_files.py`, docstring, `CODE_SIGNING.md`).

### 7.5 Il manuale utente (non esiste)

Lo studio 17 (E.7) lascia aperta la scelta «nel repository o in rete» e `17d-aiuti.md` presuppone `docs/manuale/` aperto come file con `QDesktopServices.openUrl`, che su Windows dipende dall'associazione dei `.md` (nota in fondo a 17d). Proposta che chiude la domanda:

- **Dove**: i sorgenti in `docs/manuale/`, Markdown in italiano (l'inglese dopo, nella stessa struttura `docs/manual/`), un file per capitolo, immagini PNG accanto. **Spedito con il programma**: PyInstaller lo mette in `share/manuale`, il Flatpak in `/app/share/meridiana/manuale`, `paths.shipped("manuale", "indice.md")` lo trova (una radice in più in `paths.py:63` per il checkout). Lo stesso Markdown si legge su GitHub e, quando il repository sarà pubblico, in rete: una fonte sola, nessun generatore.
- **Come si apre**: dentro il programma, non nel browser: un `QTextBrowser` in una finestra «Manuale» (o un pannello agganciabile) con Indietro, Avanti, l'indice e la ricerca. `QTextBrowser.setSource()` carica un `.md` con `QTextDocument::setMarkdown()` nel dialetto GitHub (tabelle, elenchi di caselle, collegamenti automatici), `backward()` e `forward()` e `searchPaths` per le immagini: nessuna dipendenza nuova (doc.qt.io, `QTextBrowser` e `QTextDocument::setMarkdown`) [V docs]. `F1` apre il capitolo della fase in uso (Modello, Impianto, Producibilità, Consumi, Bilancio, Relazione: B4 dello studio 17); `Aiuto > Manuale`; il collegamento «Manuale ›» del riquadro d'aiuto di 17d apre `capitolo.md#ancora`; `Maiusc+F1` sul campo fa lo stesso.
- **Struttura**: `00-primi-passi.md` (installare, il primo progetto in dieci passi), `01-modello.md`, `02-impianto.md`, `03-producibilita.md`, `04-consumi.md`, `05-bilancio-economia.md`, `06-relazione.md`, `07-comandi.md` (ogni comando con il tasto, **generato** da `shortcuts.py`), `08-norme-e-fonti.md` (ogni regola con la fonte, **generato** da `rules.py` e `checks.py`), `09-file-e-revisioni.md` (il `.meridiana`, `.bak`, `_Rnn`, il recupero, che cosa esce in rete), `10-installazione-e-aggiornamenti.md` (Windows, Flatpak, firma, verifica di un download), `11-domande.md`. Ogni numero del manuale dice da dove viene, come la relazione.
- **Come resta allineato al codice**: un test `tests/test_manuale.py` che (1) ogni ancora citata in `help.py` (17d) esiste nei capitoli, (2) ogni comando di `shortcuts.COMMANDS` compare in `07-comandi.md`, (3) ogni fonte di `rules.py` compare in `08-norme-e-fonti.md`, (4) i capitoli generati sono uguali a quelli che `tools/manuale.py` rigenera (il test fallisce se il codice cambia e il manuale no), (5) nessun trattino lungo (già `test_release.py`). Le schermate: `tools/manuale_schermate.py` apre il progetto d'esempio offscreen a misura fissa, nel tema chiaro, e le riscrive; si rilancia prima di ogni release (passo nella procedura). L'intestazione dell'indice porta la versione, controllata da `test_release.py`.
- **Fatica**: struttura, viewer Qt con F1 e i collegamenti, test: 2 giorni; i primi sei capitoli scritti: 2-3 giorni (i testi di E.6 dello studio 17 sono il seme); i due generati: mezza giornata.

## 8. Difetti in ordine di gravità

1. **Il Flatpak non si può costruire né avviare**: runtime GNOME senza Qt né dipendenze, nessuna rete, home in sola lettura. `build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml:14-17,19-33,35-44` [V lettura].
2. **La spec di Windows è dell'app GTK** e, lanciata com'è nel venv di oggi, darebbe un bundle con WebEngine (300 MB in più) e il manifest sbagliato: `build-aux/windows/meridiana.spec:11,21-36,44-46`; `meridiana.manifest:33` (`dpiAware=true` blocca il per-monitor V2 di Qt: «ERROR_ACCESS_DENIED if ... already been set ... within the application manifest», Microsoft) [V lettura e fonti, I esito del build].
3. **L'aggiornatore non è collegato**: `updates.py` senza chiamanti; `config.py:87-88` senza Preferenze; `CODE_SIGNING.md:9-12,36-42` promette ciò che non c'è; `tests/test_updates.py:143-150` inerte [V].
4. **`requirements.txt:6`** installa `PySide6_WebEngine` (132 MB a ogni `pip install`, rischio nel bundle) e non dichiara `requests` [V].
5. **`tools/make_ico.py:14` e `tools/make_icons.py:16`** importano `gi`: l'icona dell'exe e le PNG non si rigenerano nel venv Qt [V].
6. **`tools/compile_po.py:41`** senza ripiego a `msgfmt`: il job Windows e un pacchetto Windows costruito su Windows restano senza traduzioni [V].
7. **Testi dell'app campione** in `.desktop:9-11`, metainfo `:20-24,37-38,53-57`, `site/index.html:6-7,51-52,69-74`, `CHANGELOG.md:3-6,91-96`, `tools/flatpak_repo_files.py:19,74`, `__init__.py:1-9`, `__main__.py:28`, `updates.py:1-2` [V].
8. **Il CI consuma per niente**: Windows a ogni push di ogni richiesta (5 minuti, senza cache), doppio run push e pull_request, run anche per i commit di soli documenti, nessun `concurrency`; `test.yml:7-11,43-50` [V].
9. **Nessuna associazione del tipo di file** `.meridiana` (Inno `[Registry]`, `MimeType` nel `.desktop`) [V assenza].
10. **Documenti**: `docs/progetto.md:3,105` e mappa dei moduli incompleta; `docs/funzionalita.md:3`; `README.md:33` e l'ancora `#flatpak` mancante; nessuna sezione sul rilascio; nessun manuale [V].
11. **`ui/qt_translations.py:28`**: i percorsi del congelato sono quelli di Linux (innocuo su Windows grazie a `QLibraryInfo`) [V].
12. **`cloud-setup.sh:11`** installa `polib` inutilizzato [V].

## 9. Raccomandazione

Non c'è nulla da «rifare» nel senso dello studio: le ricette vanno **sostituite** con quelle di PySide6, pezzo per pezzo, tenendo quello che è indipendente da GTK (Inno Setup, la procedura di rilascio, la firma, `updates.py` e `minisign.py`, `flatpak-repo.yml`). L'ordine che conviene:

1. **Il CI leggero** (`H-ci-proposta.yml` al posto di `test.yml`, solo il job `linux` attivo finché la spec non esiste): mezza giornata; da fare subito, costa 3 minuti a push e riapre il CI anche con la quota di oggi.
2. **Windows**: spec, manifest, `make_ico.py` con Pillow, `requirements.txt` con i tre wheel e `requests`, `compile_po.py` con il ripiego; build sul PC e prova sui due monitor (DPI), poi il job `windows` del CI a mano: 1-2 giorni.
3. **L'aggiornatore in Qt** e il job `release` con il segreto minisign: 1 giorno.
4. **Flatpak**: la prova di PySide 6.11.2 sulla suite (mezza giornata, sul laptop), poi manifest con BaseApp 6.11 e `flatpak-pip-generator`, permessi, pulizia, build e prova su niri: 1-2 giorni; il repository ostree e il bundle quando il repository sarà pubblico.
5. **Identità e documenti**: desktop, metainfo con screenshot, sito, CHANGELOG 0.2.0, `CODE_SIGNING.md`, README, `progetto.md` sezione «Rilascio e pacchetti», `funzionalita.md`: 1 giorno.
6. **Il manuale**: viewer e test 2 giorni, capitoli 2-3 giorni; dopo il progetto dell'interfaccia (tema E), perché i capitoli seguono le fasi B4.

Totale 9-12 giorni; i pezzi 1, 2, 3 e 5 non dipendono dalla revisione dell'interfaccia e si possono fare prima.

## 10. Da provare sul PC di Daniel e che cosa non ho fatto

- Il build con la spec nuova e le dimensioni vere del bundle e dell'installer (qui stimate); la finestra sui due monitor con il manifest per-monitor V2; l'avvio dell'exe con la 3D (Direct3D 11) e le traduzioni Qt in italiano nel pacchetto.
- La suite con PySide6 6.11.2 (per il Flatpak) e il build Flatpak sul laptop con niri.
- Il segreto `MINISIGN_SECRET_KEY` nel repository e il primo tag: azioni verso l'esterno, dopo il sì di Daniel.
- Non ho letto le pagine di Qt for Python sui wheel (la pagina è renderizzata in JavaScript); le ho sostituite con `pip show` e i RECORD dei dist-info locali, che dicono la stessa cosa.
- L'endpoint `timing` di GitHub risponde «billable 0» per tutti i run: i minuti sono ricavati dalle durate dei job con l'arrotondamento documentato; il totale vero dell'account (che somma i repository privati) si legge solo in «Billing & plans».

## 11. Fonti (lette il 23/10/2026)

- PyInstaller 6.22.3 nel venv: `PyInstaller/hooks/hook-PySide6*.py`, `PyInstaller/hooks/rthooks/pyi_rth_pyside6.py`, `PyInstaller/fake-modules/_pyi_rth_utils/qt.py`, `PyInstaller/utils/hooks/qt/__init__.py`, `PyInstaller/utils/hooks/qt/_modules_info.py`; documentazione: https://pyinstaller.org/en/stable/hooks-config.html , https://pyinstaller.org/en/stable/usage.html
- PyPI (JSON): https://pypi.org/pypi/PySide6/6.12.0/json , .../PySide6-Essentials/6.12.0/json , .../PySide6-Addons/6.12.0/json , .../PySide6-Pdf/6.12.0.140/json , .../PySide6-WebEngine/6.12.0.140/json , .../shiboken6/6.12.0/json , .../numpy/2.5.4/json , .../scipy/1.18.1/json , .../pandas/3.0.6/json , .../matplotlib/3.11.2/json , .../pillow/13.0.0/json , .../pvlib/0.16.1/json , .../shapely/2.2.0/json , .../h5py/3.16.0/json
- GitHub: https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-actions , https://docs.github.com/en/billing/reference/actions-runner-pricing , https://docs.github.com/ja/billing/managing-billing-for-your-products/about-billing-for-github-actions ; https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md (immagine 20261021.299.1) ; https://github.com/actions/runner-images/issues/14748 ; https://github.com/actions/setup-python (README, «Caching packages dependencies») ; API `gh` per i run e i job di `daniel-g-carrasco/meridiana` e per i tag di `actions/*`
- Flathub e Flatpak: https://github.com/flathub/io.qt.PySide.BaseApp (rami e `branch/6.11`: manifest, `cleanup.sh`) ; https://github.com/flathub/com.riverbankcomputing.PyQt.BaseApp (rami) ; https://invent.kde.org/packaging/flatpak-kde-runtime (rami via API) ; https://docs.flathub.org/docs/for-app-authors/requirements ; https://docs.flatpak.org/en/latest/available-runtimes.html ; https://github.com/flatpak/flatpak-builder-tools/blob/master/pip/readme.md ; `flatpak remote-ls flathub --runtime` dal WSL del PC
- Qt e Microsoft: https://doc.qt.io/qt-6/highdpi.html ; https://doc.qt.io/qt-6/qtextbrowser.html ; https://doc.qt.io/qt-6/qtextdocument.html ; https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setprocessdpiawarenesscontext ; https://learn.microsoft.com/windows/win32/sbscs/application-manifests
- Template delle app di Daniel (sola lettura): `C:\Users\utente\dev\app-template\docs\03-windows.md`, `04-linux.md`, `05-ci-rilascio.md`, `08-trappole.md`; `C:\Users\utente\.claude\skills\nuova-app\SKILL.md`
