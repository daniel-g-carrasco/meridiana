# Programma FV: confronto degli approcci

21/10/2026. Studio preliminare per il programma di progettazione fotovoltaica di Daniel: mappa, modello 3D di edifici e pannelli, ombre, producibilità, stringatura, verifiche normative, note ed elaborati. Requisiti di partenza: ottimo su **Linux** (Fedora Atomic, GNOME 50, Wayland, Flatpak) e su **Windows 11** (PC di lavoro), moderno, possibilmente in Python.

Legenda: **[V]** verificato, cioè provato su questo PC o letto in una fonte ufficiale il 21/10/2026; **[I]** dedotto o preso da una fonte secondaria. I voti della sezione 5 sono un giudizio costruito sui fatti delle sezioni 3 e 4.

Documenti collegati, nella stessa cartella `C:\Users\utente\Elettrico\output\programma-fv\`:
- `02-requisiti-normativi.md`: che cosa chiedono norme e leggi al programma;
- `03-architettura-e-prima-fase.md`: come costruirlo, qualunque interfaccia si scelga;
- `prove\`: gli script e gli screenshot delle prove della sezione 3.

## 1. In breve

- Il cuore del programma va scritto **in Python e senza interfaccia, in ogni caso**: modello, geometria, calcoli, regole normative e documenti. È il lavoro che vale di più ed è lo stesso con qualunque finestra. La scelta dell'interfaccia decide soprattutto come si fanno **mappa e 3D**.
- Le prove su questo PC (sezione 3):
  - **Qt 6** e le **tecnologie web** fanno girare la scena realistica (3.600 moduli, sole e ombre) a 60 fotogrammi al secondo, con la selezione del singolo modulo.
  - **GTK 4 su Windows** non supera 18-29 fotogrammi al secondo anche con una scena vuota: su Windows GTK compone la finestra con cairo, e ogni fotogramma 3D passa dalla CPU.
- Su una trentina di approcci considerati ne restano **quattro seri**:
  1. **Qt 6 (PySide6) con mappa e 3D dentro un motore web interno.** Qt WebEngine ospita OpenLayers e three.js; il risultato è un'app Python vera, con le librerie migliori per mappa e 3D e licenze libere. Provato a 60 fps, con selezione del modulo e mappa con poligono. Contro: due linguaggi (Python e JavaScript) e un pacchetto grande.
  2. **Qt 6 (PySide6) con Qt Quick 3D e Qt Location.** Tutto nativo Qt, provato a 60 fps. Qt Quick 3D è GPLv3: per un programma open source significa solo che il programma esce GPLv3 (sezione 8). Contro: Qt Location è ancora in anteprima e non legge i servizi WMS, come le ortofoto nazionali; serve il linguaggio QML.
  3. **Electron, o il browser, con Python accanto.** Stesse librerie del punto 1, con lo stesso Chromium su Linux e Windows. Contro: due processi, due catene di pacchetti, niente riuso del template.
  4. **GTK 4 + libadwaita, il template di casa.** È il migliore su GNOME e il più rapido da avviare. Contro: il 3D va scritto da zero sopra OpenGL ed è frenato proprio su Windows; la mappa va costruita (libshumate non è nel runtime GNOME).
- **Esclusi, per motivi verificati:**
  - le altre librerie Python (wxPython, Kivy, Dear PyGui, Flet, Toga): 3D assente o povero, Wayland debole;
  - i toolkit in altri linguaggi (Flutter, Avalonia, JavaFX, Compose, Slint, egui): 3D immaturo o assente, e si perde Python;
  - .NET MAUI: non gira su Linux;
  - Tauri 2 e pywebview su Linux: usano WebKitGTK, il cui WebGL è a rischio secondo la stessa documentazione di Tauri.
- **Interessanti, ma non come prodotto unico:**
  - Godot: 3D eccellente, ma niente Python;
  - plugin di Blender, QGIS o FreeCAD: interfacce non fatte per moduli, verifiche e relazioni, e si lavorerebbe dentro un altro programma.
- **Comprare:** i programmi da scrivania (Solarius PV, PVsyst, PV*SOL) girano solo su Windows; su Linux ci sono solo prodotti web a canone.
- **La mia classifica:** 1) Qt + WebEngine; 2) Qt Quick 3D, molto vicino; 3) Electron; 4) GTK. La decisione è di Daniel: la sezione 9 dice cosa proverei prima.
- **Vista satellitare** (sezione 7): dove manca il rilievo 3D degli edifici, si disegna l'edificio sulla foto aerea. Le fonti utilizzabili sono:
  - l'ortofoto nazionale PCN del 2012, senza chiave e senza condizioni [V];
  - Esri, recente, con un account gratuito per ogni utente;
  - qualunque servizio WMS o XYZ a cui l'utente abbia diritto.
  
  In Lombardia il DBGT dà già il 3D (impronte, altezze, falde) con licenza aperta.

## 2. Che cosa deve fare il programma

Sono i requisiti che decidono la tecnologia. Il dettaglio normativo è in `02-requisiti-normativi.md`.

| Requisito | Perché pesa sulla scelta |
|---|---|
| **Mappa:** trovare il sito; sfondo stradale e ortofoto con una licenza utilizzabile; impronte degli edifici (OSM, DBGT Lombardia); disegnare e misurare poligoni in metri | serve una libreria di mappe con WMS/WMTS/WFS, proiezioni e strumenti di disegno |
| **3D:** edifici a prisma, falde, migliaia di moduli, ostacoli, sole per data e ora con le ombre, selezione col mouse; poi modifiche dirette | serve un motore 3D con instancing, ombre e selezione |
| **Calcoli:** PVGIS; il metodo convenzionale per Legge 10, APE e obbligo FER; la posa con i vincoli VVF; stringatura; cavi; regole e note con le fonti | Python ha già tutto (numpy, shapely, pvlib, PySAM) e le regole della libreria R02 sono già in Python |
| **Documenti:** note per capitoli in italiano e inglese, relazione Word sul format dell'ufficio, Excel, DXF per i disegni, PDF | python-docx, openpyxl, ezdxf |
| **Piattaforme:** Windows 11 e Linux (GNOME, Wayland, Flatpak), entrambi "ottimi" | esclude o penalizza chi è debole su uno dei due |
| **Dati dell'utente:** progetti su disco e nelle cartelle di commessa, salvataggio atomico, revisioni `_Rnn`, mai sovrascrivere | serve l'accesso pieno ai file, facile da un'app nativa e macchinoso da un browser |
| **Manutenzione:** Daniel con Claude, con test automatici, CI e rilasci firmati | contano la quantità di codice e il numero di linguaggi |

## 3. Le prove fatte su questo PC

**Macchina:** Windows 11 Pro, Intel Iris Xe + NVIDIA RTX A2000, schermo a scala 200%.

**Scena di prova** (uguale per tutti dove indicato):
- un capannone di 160 × 100 m;
- 3.600 moduli da 1,13 × 2,28 m, inclinati di 10° in file ogni 3 m;
- un ostacolo sul tetto;
- il sole che si muove con le ombre e la telecamera che ruota;
- la selezione col mouse al centro dello schermo.

Script e screenshot sono in `C:\Users\utente\Elettrico\output\programma-fv\prove\`.

| Tecnologia | Come disegna su Windows | Risultato |
|---|---|---|
| GTK 4.24.1 (MSYS2), GtkGLArea | OpenGL 4.6 core su Iris Xe. Shader compilato e pixel riletti giusti, ma la finestra la compone cairo: i renderer `gl` e `vulkan` non partono ("OpenGL requires Direct Composition") | **18-29 fps con un solo triangolo** a finestra intera (2560 × 1522 pixel). Il limite è la copia GPU→CPU, non la scena [V] |
| Qt 6.12 (PySide6), Qt Quick 3D | Direct3D 11 | scena completa a **60 fps**, cioè la frequenza dello schermo; selezione del singolo modulo (n. 1877). Le ombre vanno regolate: strisce sul terreno (`prove\qt_3d.png`) [V] |
| Qt 6.12, Qt Location (plugin OSM con URL delle tile proprio) | Direct3D 11 | tile OSM a zoom 18 con un poligono sopra (`prove\qt_map.png`) [V] |
| Chrome, three.js r160 | ANGLE su Direct3D 11 | scena completa a **60 fps**, selezione (n. 1860), ombre pulite senza regolazioni (`prove\web_3d.png`) [V] |
| Qt 6.12 con Qt WebEngine: three.js e OpenLayers dentro la finestra PySide6 | ANGLE su Direct3D 11 | scena completa a **60 fps** con selezione (n. 1860). Mappa OpenLayers con tile OSM, poligono e area calcolata: 3.352 m² su 3.360 attesi (`prove\qtweb_map.png`) [V] |

Altri fatti verificati oggi:
- **PVGIS 5.3 non manda intestazioni CORS.** La documentazione lo dice: "access to PVGIS APIs via AJAX is not allowed". Da una pagina web non si può chiamare: serve un Python dietro. [V]
- **PVGIS accetta un orizzonte fornito da noi (`userhorizon`).** Con ostacoli a sud, 1 kWp a Rho (MI) passa da 1.356 a 1.053 kWh/anno. Fornisce anche l'anno tipo orario: 8.760 righe con temperatura, radiazione globale, diretta e diffusa, vento. [V]
  - Limite: secondo il metodo JRC l'orizzonte toglie la radiazione diretta ma non riduce il diffuso. [V]
- **PVGIS 6 beta** risponde con CORS aperto, ma è una beta con limiti stretti: 200 chiamate l'ora per client. [V]
- **Pacchetti MSYS2:**
  - disponibili, ma non installati: libshumate 1.7, numpy 2.5, scipy 1.18, pandas 3.0, shapely 2.2, pyproj 3.7, trimesh 4.6, PyOpenGL 3.1.10;
  - assenti: WebKitGTK, pywebview, pythonnet. [V]
- **Browser:** Edge non è installato su questo PC; il runtime WebView2 sì, versione 155. [V]
- **Overpass**, il servizio che restituisce gli edifici di OSM, era saturo in due tentativi: un programma vero deve ritentare e tenere una cache. [V]

## 4. Gli approcci, uno per uno

### A. App da scrivania in Python

**A1. GTK 4 + libadwaita (il template di casa).** Il 3D si fa con GtkGLArea e PyOpenGL, scritto da noi; la mappa con libshumate o con un widget nostro.
- Pro:
  - è tutto pronto: CI, installer firmato, Flatpak, aggiornamenti, 53 test, regole di casa;
  - un solo linguaggio;
  - è il migliore su GNOME;
  - la licenza può restare MIT.
- Contro:
  - su Windows, che è il PC di lavoro, la composizione cairo limita il 3D a 18-29 fps a finestra intera [V];
  - il 3D si scrive da zero (telecamera, selezione, ombre, etichette, maniglie): per GTK 4 in Python non esiste una libreria 3D [I];
  - libshumate non è nel runtime GNOME (49, 50, 51) e va compilato nel Flatpak, come fa GNOME Maps [V]; disegno, misure, WMS e proiezioni restano comunque da scrivere;
  - WebKitGTK esiste solo su Linux (è nel runtime GNOME 50, manca in MSYS2) [V]: su Windows niente librerie web dentro la finestra;
  - su Windows GTK scala solo a numeri interi (`docs\03-windows.md` del template): a 150% la finestra è leggermente sfocata.

**A2. Qt 6 (PySide6) + QML, con Qt Quick 3D e Qt Location.**
- Pro:
  - provato a 60 fps, con ombre e selezione del singolo modulo [V];
  - Direct3D 11 su Windows, OpenGL o Vulkan su Linux [V];
  - instancing, ombre a cascata dalla 6.8, selezione a riquadro dalla 6.11 [V];
  - buono su Wayland: decorazioni Adwaita predefinite su GNOME dalla 6.8, scala frazionaria dalla 6.5 [V];
  - Qt 6.12 è LTS per 5 anni [V];
  - PyInstaller ha gli hook per Quick 3D, Location e WebEngine [V].
- Contro:
  - Qt Quick 3D è GPLv3 o commerciale [V]: il programma deve uscire GPLv3. Per un programma open source non è un ostacolo (sezione 8);
  - Qt Location nella 6.12 è ancora "technology preview"; la mappa predefinita chiede una chiave e il satellite è spento, quindi serve un servizio di tile proprio [V];
  - Qt Location ha solo i plugin osm e itemsoverlay, cioè tile XYZ [V]. I servizi WMS, come le ortofoto nazionali PCN, vanno convertiti da un piccolo server locale o mostrati come immagine nella pianta [I];
  - oltre a Python si scrive QML, un linguaggio dichiarativo con espressioni JavaScript;
  - Flatpak da provare: la BaseApp di PySide arriva alla 6.11 e il suo README dice che Quick 3D è escluso, mentre il runtime KDE lo contiene [V].

**A3. Qt 6 (PySide6) Widgets + VTK (PyVista, pyvistaqt).**
- Pro:
  - tutto in Python;
  - VTK è un motore 3D scientifico maturo (BSD);
  - pyvistaqt 0.13 (09/2026) gira su Wayland nativo e compone sulla GPU [V];
  - la licenza dell'app resta libera.
- Contro:
  - le ombre di PyVista hanno "known issues" [V];
  - le wheel di VTK pesano 80-140 MB per ogni versione di Python [V];
  - la mappa resta da risolvere (Qt Location o un motore web);
  - VTK è fatto per la visualizzazione scientifica più che per un editor con maniglie [I].

**A4. Qt 6 (PySide6) + Qt WebEngine, con OpenLayers e three.js dentro la finestra.**
- Pro:
  - provato a 60 fps, con selezione, mappa, poligono e area [V];
  - le librerie migliori per le mappe (OpenLayers: WMS, WMTS, WFS, proiezioni, strumenti di disegno) e per il 3D (three.js: instancing, ombre, selezione, maniglie) [I sulle funzioni non provate];
  - Python e pagina stanno nello stesso processo (QWebChannel): niente server locale, nessuna porta aperta, nessun problema di CORS, perché le chiamate a PVGIS le fa Python;
  - OpenLayers legge direttamente WMS (le ortofoto PCN) e WFS (il DBGT lombardo) [I];
  - Qt è LGPL, three.js è MIT, OpenLayers è BSD: il programma può avere la licenza open source che si preferisce;
  - la BaseApp Flatpak di PySide include già WebEngine [V];
  - finestre, dialoghi, file, Word ed Excel restano Python nativo.
- Contro:
  - due linguaggi, con JavaScript confinato nelle due viste (mappa e 3D);
  - pacchetto grande: la wheel di WebEngine pesa 132 MB, circa 350 MB estratti [V];
  - WebEngine con la wheel separata va provato in PyInstaller [I];
  - gli aggiornamenti di sicurezza di Chromium arrivano con le versioni di Qt.

**A5. wxPython.** Scartato: wxWidgets 3.3 è dichiarato "API/ABI unstable", usa GTK 3 su Linux, non ha wheel Linux su PyPI e il 3D si fa solo con PyOpenGL da zero [V].

**A6. Kivy, Dear PyGui, Flet, Toga.** Scartati [V]:
- Kivy: fermo al 12/2024, con problemi su Wayland;
- Dear PyGui: in manutenzione, solo XWayland, 3D senza depth buffer;
- Flet 1.0: niente 3D e niente WebView sul desktop;
- Toga: la mappa ha solo segnaposti, niente 3D.

### B. Interfaccia web con un motore Python

**B1. Python in locale + pagina nel browser (OpenLayers e three.js).**
- Pro:
  - le stesse librerie di A4, già provate in Chrome [V];
  - Linux e Windows identici;
  - un giorno può diventare un servizio per l'ufficio (B6).
- Contro:
  - non è un'app: è una scheda del browser più un server da avviare e chiudere;
  - il server deve ascoltare solo su 127.0.0.1 con un gettone segreto, perché qualunque sito aperto nel browser potrebbe chiamarlo [I];
  - i file passano tutti dal server;
  - due linguaggi;
  - il template serve solo a metà.

**B2. Framework "tutto Python": NiceGUI, Panel, Reflex, Streamlit, Dash.**
- NiceGUI ha `ui.scene` (three.js con selezione) e `ui.leaflet` con il disegno di poligoni [V].
- Instancing e ombre non sono documentati [V]: per un editor 3D vero si finisce a scrivere JavaScript.
- Per default ascolta su tutte le interfacce (0.0.0.0) [V]: va forzato 127.0.0.1.
- Streamlit, Panel e Dash sono pensati per cruscotti, non per editor.

**B3. pywebview, cioè una finestra nativa con il motore web del sistema.**
- Su Windows serve pythonnet con .NET, e quindi un Python di python.org invece di quello di MSYS2 [V/I].
- Su Linux usa WebKitGTK 4.1 (GTK 3) [V], con gli stessi rischi WebGL di B5.

**B4. Electron + Python affiancato.**
- Pro:
  - Chromium è incluso, quindi il WebGL è identico su Linux e Windows;
  - Wayland nativo per default dalla versione 38 [V];
  - c'è una BaseApp Flatpak [V];
  - è maturo: VS Code è fatto così.
- Contro:
  - due processi, Electron e Python, che parlano via HTTP o standard input;
  - in più la toolchain Node/npm;
  - due pacchettizzazioni, electron-builder e PyInstaller [V];
  - 85-150 MB solo per Electron [I];
  - nessun riuso del template.

**B5. Tauri 2 + Python affiancato.** È leggero, ma:
- su Linux usa WebKitGTK 4.1, e la sua documentazione avverte che WebGL può passare "silently" a un percorso lento [V];
- Tauri 3, con Chromium, è ancora alpha [V];
- aggiunge un terzo linguaggio, Rust.

**B6. Servizio per l'ufficio** (un server su una macchina dell'ufficio, i colleghi dal browser).
- Pro: nessuna installazione, colleghi inclusi.
- Contro: servono un server, gli accessi, i backup, e i dati di commessa viaggiano in rete.
- Da considerare dopo, partendo da B1.

### C. Toolkit in altri linguaggi

Python verrebbe riscritto o affiancato. Lo stato di ciascuno [V]:

| Toolkit | Stato |
|---|---|
| Flutter 3.47 | su Linux usa GTK 3; Fedora non è tra le distribuzioni supportate; il 3D è in "early preview" |
| Avalonia 12 | Wayland solo sperimentale; il 3D va integrato a mano |
| .NET MAUI | niente Linux |
| JavaFX 27 | 3D senza ombre, gira in XWayland |
| Compose Multiplatform | niente 3D, gira in XWayland |
| Slint | 3D solo da Rust o C++ |
| egui | 3D via callback; mappe solo da librerie di terzi |

Qt in C++ è lo stesso Qt di A2-A4, ma senza Python.

In tutti i casi si perde Python, e con lui pvlib, PySAM e le regole della R02; il costo sale molto. Scartati.

### D. Motori di gioco

- **Godot 4.7.**
  - Pro: 3D completo, export per Linux e Windows (circa 93 MB), esistono app non di gioco come Pixelorama e Material Maker [V].
  - Contro: niente Python ufficiale (si usano GDScript o C#), mappe da scrivere, Wayland non predefinito [V]. I calcoli andrebbero in un Python affiancato.
- **Unity e Unreal:** esclusi per licenze e peso.

### E. Plugin di programmi esistenti

- **E1. Blender 5.2.**
  - Pro: 3D completo; l'estensione ufficiale Sun Position mette il sole per luogo, data e ora; BlenderGIS importa da OSM edifici con altezze e i DEM [V].
  - Contro:
    - un add-on deve essere GPL [V], il che per un programma open source va bene;
    - le basemap Google e Bing di BlenderGIS sono accessi non autorizzati [V sul codice, la valutazione è mia];
    - l'interfaccia di Blender non è fatta per moduli, verifiche e relazioni, e si lavorerebbe dentro Blender.
- **E2. QGIS 3.44 / 4.x.**
  - Pro: il migliore per mappe, WMS, WFS, proiezioni e DBGT Lombardia; ha una vista 3D con estrusioni e luci con ombre [V]; c'è UMEP/SEBE per l'irraggiamento sui tetti da DSM (GPL) [V].
  - Contro: la vista 3D non ha il sole per data e ora; non esiste un plugin PVGIS; i plugin devono essere GPL [V].
  - Ottimo come strumento d'appoggio per analizzare il sito, non come programma FV.
- **E3. FreeCAD 1.1.**
  - Pro: BIM con IFC nativo; dalla 1.1 il Site ha la posizione del sole [V].
  - Contro: nessun workbench per impianti FV attivo [V]:
    - PVPlant è fermo dal 2023;
    - "Solar" fa solo analisi solare e dipende da Ladybug, che è AGPL.
- **E4. SketchUp, Rhino/Grasshopper con Ladybug, Revit:** non girano su Linux [V].

### F. Comprare

| Prodotto | Piattaforma | Prezzo | Note |
|---|---|---|---|
| ACCA Solarius PV | solo Windows 64 bit [V] | non pubblicato; Power Pack 599 € [V] | UNI 10349, ENEA, PVGIS, 3D/BIM con IFC, cavi CEI-UNEL, unifilare, relazione, CER [V]. La UNI/TS 11300-4 non è citata |
| PVsyst 8 | solo Windows [V] | CHF 700/anno [V] | lo standard per la producibilità, con ombre vicine in 3D |
| PV*SOL premium 2026 | Windows [V] | 845 €/anno [V] | 3D e ombre, interfaccia in italiano |
| SMA Sunny Design | web [V] | gratis; PRO 600 €/anno [V] | |
| SolarEdge Designer | web | gratis | solo componenti SolarEdge [I] |
| Aurora, HelioScope | web | 135-259 $/mese per utente [V] | pensati per USA e Regno Unito |
| SAM (NLR, ex NREL) | Windows, macOS e **Linux** [V] | gratis | solo prestazioni; da Python con PySAM |

- Nessuno contiene le regole e le note della R02, i vincoli di posa della guida VVF 2025, il metodo dell'Allegato H lombardo né il format dell'ufficio.
- Su Linux funzionano solo i prodotti web.
- Anche se il programma si scrive, Solarius PV o PVsyst restano utili come **termine di confronto** per validarne i risultati.

### G. Strategie miste

- **G1. Un solo core Python, interfaccia intercambiabile.** Vale per tutti gli approcci A e B e protegge dalla scelta sbagliata dell'interfaccia.
- **G2. "Excel+".** Si tiene la R02 e si aggiungono script Python (PVGIS, Solar API, Allegato H). Costo minimo, ma niente mappa né 3D.
- **G3. A fasi.** Nella prima fase mappa, pianta 2D e un 3D di sola visione; il 3D modificabile viene dopo. Riduce il rischio con qualunque interfaccia, GTK compresa.

## 5. Tabella di confronto

Voti da 1 a 5, dove 5 è il migliore. È il mio giudizio sui fatti delle sezioni 3 e 4.

| Approccio | Linux | Windows | 3D | Mappa | Solo Python | Pacchetti e rilasci | Riuso di casa | Maturità |
|---|---|---|---|---|---|---|---|---|
| A1 GTK 4 | 5 | 3 | 2 | 3 | 5 | 5 | 5 | 4 |
| A2 Qt + Quick 3D | 4 | 5 | 5 | 3 | 3 | 4 | 3 | 4 |
| A3 Qt + VTK | 4 | 5 | 4 | 3 | 5 | 3 | 3 | 4 |
| A4 Qt + WebEngine | 4 | 5 | 5 | 5 | 3 | 3 | 3 | 4 |
| B1 Browser + Python | 5 | 5 | 5 | 5 | 3 | 3 | 2 | 4 |
| B2 NiceGUI | 5 | 5 | 3 | 4 | 4 | 4 | 2 | 3 |
| B4 Electron + Python | 5 | 5 | 5 | 5 | 2 | 2 | 1 | 5 |
| B5 Tauri + Python | 2 | 5 | 3 | 5 | 2 | 4 | 1 | 3 |
| C Altri linguaggi | 3 | 4 | 2 | 3 | 1 | 4 | 1 | 3 |
| D Godot | 4 | 5 | 5 | 2 | 2 | 4 | 1 | 3 |
| E1 Blender | 5 | 5 | 5 | 3 | 5 | 2 | 1 | 4 |
| E2 QGIS | 5 | 5 | 3 | 5 | 5 | 2 | 1 | 5 |
| F Comprare (desktop) | 1 | 5 | 4 | 3 | - | 5 | 1 | 5 |

Per un programma open source la licenza del codice non penalizza nessun approccio: decide solo quale licenza dare al programma (sezione 8).

Note sui voti:
- A2-A4 hanno 4 e non 5 su Linux perché su GNOME Qt non ha l'aspetto nativo e il Flatpak passa dal runtime KDE con la BaseApp di PySide.
  - Aggiornamento dopo le prove del 21/10 sera (`04-prove-brevi.md`): Daniel usa Niri, non GNOME, e lì Qt gira nativo Wayland.
  - Prototipo A4 a 60 fps, Quick 3D a 120 fps, anche dentro la Flatpak con la GPU.
  - Su Linux il voto di A2-A4 sale a 5.
- B1 ha 5 su Linux, ma è una scheda del browser, non un'app.

## 6. Motori di calcolo

Sono indipendenti dall'interfaccia.

| Motore | Licenza | Uso nel programma |
|---|---|---|
| PVGIS 5.3 (API del JRC) | uso libero, citando la fonte [V] | producibilità realistica, orizzonte, anno tipo. **Non** per Legge 10, APE e coperture dell'obbligo FER (vedi `02`) |
| Metodo convenzionale mensile: Allegato H lombardo; nel resto d'Italia UNI/TS 11300-4 con UNI 10349-1 | lo scriviamo noi seguendo il testo | numeri ufficiali per la relazione Legge 10, l'APE e le coperture dell'obbligo FER. I dati lombardi sono nel decreto regionale; le UNI sono a pagamento |
| pvlib 0.16 | BSD-3 [V] | posizione del sole, trasposizione, temperature, calcoli orari. Dipendenze pesanti (pandas, scipy, h5py); database CEC del 2019 [V] |
| PySAM 7.1 (NLR) | BSD-3 [V] | simulazione dettagliata: ombre per stringa, inverter, moduli CEC. Wheel per Windows e Linux [V] |
| Radiance 6.1 | tipo BSD [V] | ombre e irraggiamento con ray tracing, per i casi difficili |
| Ladybug Tools | **AGPL-3.0** [V] | da evitare, salvo che l'app sia AGPL |
| solarfactors (il fork mantenuto di pvfactors) | BSD-3 [V] | ombre reciproche tra le file, moduli bifacciali |
| shapely (GEOS) e numpy | BSD | geometria della posa: fasce, corridoi, esclusioni, superfici |
| Google Solar API | a pagamento, con 10.000 richieste gratis al mese [V] | falde degli edifici esistenti già pronte, con inclinazione e azimut. Qualità alta a Milano e nell'hinterland [V] |

## 7. Dati: mappe, immagini, edifici

| Fonte | Licenza e limiti | Uso |
|---|---|---|
| Tile OSM | attribuzione; User-Agent proprio; cache di almeno 7 giorni; niente scarico massivo né uso offline [V] | mappa per trovare il sito |
| Impronte degli edifici OSM (Overpass) | ODbL con attribuzione; circa 10.000 richieste al giorno; oggi era saturo [V] | edifici vicini come ostacoli; le altezze spesso mancano [I] |
| **DBGT Lombardia, tema Edificato** | **CC BY 4.0**, WFS e shapefile, con altezze e falde [V] | edifici e coperture in Lombardia. Le altre regioni hanno banche dati topografiche simili, con licenze e contenuti da verificare una per una [I]; dove mancano, si modella l'edificio sulla foto aerea |
| Ortofoto Esri World Imagery | account gratuito ArcGIS Location Platform: 2 milioni di tile al mese, uso commerciale ammesso, scritta "Powered by Esri" [V]. La chiave è personale: in un programma open source non si pubblica nel codice, ognuno inserisce la sua nelle preferenze [I] | sfondo aereo recente |
| Ortofoto nazionali PCN (WMS) | il servizio dichiara "nessun vincolo di accesso" e "nessuna condizione applicata"; citare la fonte; pixel di 50 cm; la più recente è del 2012 [V]. Si leggono falde, shed e lucernari (`prove\pcn_ortofoto_2012_rho.png`) | sfondo aereo senza chiave, ma datato: mancano gli edifici successivi al 2012 |
| Qualunque WMS o XYZ dell'utente | secondo i diritti dell'utente | per esempio un abbonamento aziendale o un'ortofoto comunale |
| Ortofoto Regione Lombardia 2021 e 2024 | copyright AGEA, licenza concessa alla sola Regione [V] | non usabili in un prodotto |
| Google: tile satellitari e 3D fotorealistico | non disponibili per i progetti fatturati in Europa dall'08/07/2025 (errore 403) [V] | esclusi |
| DXF e IFC del progetto | dati di commessa | edifici nuovi, che sulla mappa non esistono ancora |

## 8. Licenze, in parole semplici

Il programma sarà open source. Le licenze in gioco sono di due tipi, e l'open source ne risolve uno solo.

**1. Licenze del software, cioè le librerie che usiamo: con l'open source nessun ostacolo vero.** Alcune librerie sono "contagiose": se le usi, il programma intero deve uscire con la loro licenza o una compatibile.

| Componente | Che cosa comporta per il programma |
|---|---|
| GTK; Qt Widgets, Location, WebEngine (LGPL); three.js, OpenLayers, VTK, pvlib, PySAM, shapely (MIT o BSD) | qualunque licenza open source. Qt LGPL chiede di distribuire le sue librerie come file separati, sostituibili, con l'avviso di licenza [V]; PyInstaller in modalità cartella lo fa [I] |
| Qt Quick 3D (GPLv3) | il programma esce GPLv3 |
| Ladybug Tools, PyMuPDF (AGPL-3.0) | il programma esce AGPL-3.0, come Cartiglio |
| Plugin di Blender o QGIS | GPL |

In pratica:
- La GPLv3 vuol dire che chi modifica il programma e lo ridistribuisce deve pubblicare anche lui il sorgente.
- Usarlo, anche in ufficio e per lavoro, non comporta alcun obbligo.
- **Proposta: licenza GPLv3**, che accetta tutte le librerie trovate tranne le AGPL. Se mai servissero Ladybug o PyMuPDF, si passa ad AGPL.

**2. Licenze dei dati e dei servizi: qui l'open source non cambia nulla.** Non riguardano il nostro codice, ma l'uso di dati di altri:
- **Ortofoto della Regione Lombardia 2021 e 2024:** sono di AGEA, concesse alla Regione per i suoi fini [V]. Non possiamo offrirle nel programma.
- **Google:** non dà più le immagini satellitari né il 3D per questo uso in Europa [V].
- **Esri:** le immagini sono gratuite con un account, ma la chiave è personale. Non si può pubblicare nel codice: ogni utente inserisce la sua, gratuita, nelle preferenze [I].
- **OpenStreetMap:** libero, con l'attribuzione a video e le regole d'uso dei tile (niente scarico massivo) [V].
- **Norme UNI e CEI:**
  - le tabelle (per esempio i dati climatici della UNI 10349-1) e i testi delle norme sono protetti: nel repository pubblico non possono stare;
  - il programma può citarle e applicarne le formule, e chi ha la norma può caricare i dati in locale [I].
- **Leggi e atti pubblici:** sono liberi, perché la legge sul diritto d'autore non si applica ai testi degli atti ufficiali dello Stato e delle amministrazioni pubbliche (L. 633/1941, art. 5) [I: fonte secondaria, da ricontrollare su Normattiva]. Per questo i dati climatici dell'Allegato H lombardo possono stare nel programma.

## 9. Raccomandazione e prove prima di decidere

**Le prove brevi sono state fatte il 21/10/2026 sera**, su Windows e sul portatile Linux con Niri, anche in Flatpak. Risultati e proposta sono in `04-prove-brevi.md`: Qt + WebEngine (A4) le passa tutte.

**Classifica:** A4 Qt + WebEngine, poi A2 Qt Quick 3D (molto vicino), poi B4 Electron, poi A1 GTK.

**Perché A4 per primo:**
- è un'app da scrivania Python, come le altre di Daniel: file, dialoghi, Word, Excel e calcoli restano nativi;
- per mappa e 3D usa le librerie più forti che esistono, provate oggi a 60 fps sul PC di lavoro;
- legge direttamente le ortofoto WMS e il DBGT in WFS, e si può stendere l'ortofoto sotto il modello 3D [I];
- è ottimo su Linux e su Windows;
- il JavaScript è confinato in due viste.

A2 è l'alternativa tutta Qt: il 3D si scrive in QML invece che in JavaScript, il pacchetto è più piccolo, ma la mappa è meno capace.

**Se Daniel preferisce restare su GTK** è fattibile, con due condizioni:
- strategia G3: pianta 2D e 3D di sola visione, accettando 18-29 fps su Windows a finestra intera;
- un 3D scritto da noi, con un ripiego cairo se OpenGL manca.

Su Linux GTK resta il più bello.

**Prima di decidere proverei** (prove brevi, nello scratchpad):
1. **Flatpak:** la BaseApp di PySide 6.11 su Fedora Atomic. Avvio, WebEngine, per A2 anche `import PySide6.QtQuick3D`, Wayland, scala frazionaria, dimensione.
2. **PyInstaller su Windows** con PySide6 6.12 e WebEngine: dimensione dell'installer e tempo di avvio.
3. **Lo stesso prototipo sul portatile Linux:** fotogrammi al secondo e selezione.
4. **GTK su Linux:** verificare che GtkGLArea venga composta sulla GPU senza copia, se si vuole tenere aperta l'opzione GTK.
5. **Un'interazione vera:** disegnare una falda sulla mappa e vederla in 3D, con i moduli posati e i vincoli VVF (1 m dal bordo, gruppi di al massimo 20 m, corridoi di 2 m). In A4 e, per confronto, in A2.

Qualunque sia la scelta, il core Python è lo stesso e si può cominciare subito: `03-architettura-e-prima-fase.md`.

## 10. Fonti principali

Le fonti sono state lette il 21/10/2026; gli elenchi completi stanno nei resoconti delle ricerche.

**Qt**
- Licenza di Qt Quick 3D: doc.qt.io/qt-6/qtquick3d-index.html
- Obblighi LGPL: qt.io/licensing/open-source-lgpl-obligations
- Qt Location, plugin OSM: doc.qt.io/qt-6/location-plugin-osm.html; maps-redirect.qt.io/osm/5.8/street
- BaseApp Flatpak di PySide: github.com/flathub/io.qt.PySide.BaseApp
- Runtime KDE: invent.kde.org/packaging/flatpak-kde-runtime

**GTK**
- libshumate assente dal runtime GNOME: gitlab.gnome.org/GNOME/gnome-build-meta (rami gnome-49, 50, 51); GNOME Maps lo compila: github.com/flathub/org.gnome.Maps

**Web**
- Electron 38 su Wayland: electronjs.org/blog/electron-38-0
- WebGL di Tauri su Linux: v2.tauri.app/develop/debug/linux-graphics/
- NiceGUI: nicegui.io/documentation

**PVGIS**
- API: joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/api-non-interactive-service_en
- Metodi di calcolo (orizzonte e diffuso): .../pvgis-data-sources-calculation-methods_en
- PVGIS 6 beta: photovoltaic-geographic-information-system.ec.europa.eu/api/v6/openapi.json

**Dati**
- Tile OSM: operations.osmfoundation.org/policies/tiles/
- Esri: location.arcgis.com/help/licensing-and-attribution/
- Google, termini per lo Spazio economico europeo: developers.google.com/maps/comms/eea/map-tiles
- Copertura della Solar API: developers.google.com/maps/documentation/solar/coverage
- DBGT Lombardia: scheda RNDT r_lombar:3493af32

**Programmi**
- Solarius PV: acca.it/requisiti/solarius-pv
- PVsyst: pvsyst.com/en/shop/
- PV*SOL: valentin-software.com/en/products/pvsol-premium/
- SAM: sam.nlr.gov/download.html
- Blender, licenza degli add-on: blender.org/about/license/
- Plugin QGIS: plugins.qgis.org/docs/publish
