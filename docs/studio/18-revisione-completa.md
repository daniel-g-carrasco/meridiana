# Studio 18: la revisione completa di Meridiana

Revisione del 23/10/2026, chiesta da Daniel («una revisione completa del programma da tutti i punti di vista e anche una riscrittura totale o quasi se necessaria e un rifacimento della UX», registro R32) e fatta sul PC di Daniel, sul ramo `revisione-completa`, con un agente per tema e i controlli a campione del revisore principale. Il compito è `docs/compiti/18-revisione-completa.md`; i rapporti per tema, con gli script e i risultati, stanno in `docs/studio/18-prove/`; il progetto dell'interfaccia in `docs/design/interfaccia.md`.

**Legenda.** [V] verificato (come è detto nel rapporto del tema), [I] dedotto, [D] deciso da Daniel.

## 0. In breve: il verdetto

**Tenere il nucleo e migliorare per passi. Non riscrivere.**

- Meridiana ha 20.190 righe di Python in 83 file (15.643 di codice) e 637 test [V, G e D]. Il nucleo senza Qt (geometria, sole, posa, energia, verifiche, regole, cataloghi, file) è scritto come si deve e **fa i conti giusti**: il motore energetico coincide con pvlib passo per passo a 0,0000 [V, B]; a Rho, a parità di perdite e con i coefficienti recenti, sta a -0,02 % da PVGIS [V, B]; su otto casi PVsyst pubblici con lo stesso meteo sta entro ±1,5 % sull'energia DC e ±2 % sull'energia in rete [V, B3]; ombre esatte sui nodi della griglia, economia e fasce ARERA uguali al calcolo a mano [V, B]; 92 citazioni normative su 101 confermate parola per parola sull'archivio [V, B6].
- Il verdetto per modulo è **tieni per il 76 % delle righe, rifai per passi il 24 %, sostituisci 0** [V, A §8]: da rifare, sopra la stessa base e con i test verdi, `ui/window.py` (2.474 righe con 700 righe di dominio), la scena di `ui/plan.py`, `model.py` (riferimenti per indice, nessuna validazione), `layout.py`, `roofs.py`, `energy/system.py`.
- I difetti che pesano davvero non sono di linguaggio né di struttura generale: (1) ogni modifica riposa tutti i sottocampi e ricalcola l'anno, perché la chiave della posa serializza anche i nomi (rinominare un edificio sul progetto grande costa 328 ms sul filo della finestra più una posa e un calcolo dell'anno) [V, A]; (2) il file di progetto non è validato e l'apertura intercetta solo due tipi di errore: 8 file malformati su 20 fanno saltare lo slot senza messaggio [V, G]; (3) nessun `excepthook` e nessun log su file: gli errori non previsti sono invisibili [V, G]; (4) errori di rete, salvataggio e impostazioni che non arrivano all'utente [V, G]; (5) alcune note normative da correggere prima di finire in una relazione, in particolare N02/N03 sul DM 37/08, che guardano la potenza del FV invece della potenza impegnata dell'utenza e della superficie [V, B6, confermato dal revisore sull'art. 5 c. 2].
- **Prestazioni: non si compila nulla** (R31). Il ciclo caldo `dispatch` passa da 0,54 s a 0,07 s con un cambio di algoritmo in numpy (7,7 volte); numba e Rust darebbero 58 volte sullo stesso pezzo, cioè 61 ms in più su un calcolo di 1,2 s, a un costo di distribuzione alto (147 MB per numba; toolchain e CI per piattaforma per Rust) [V, C]. I colli veri (tabella d'ombra, `evaluate`, il filo della finestra) sono questioni di algoritmo e di dove gira il codice.
- **L'interfaccia si rifà sopra la struttura di oggi**, secondo il progetto scritto (`docs/design/interfaccia.md`): sei fasi come luoghi sempre apribili, pannelli come schede, barra della fase con i gruppi, Verifiche per livello, Meridio con il fumetto. Delle decisioni prese negli studi 12-17 tredici si contraddicono fra loro o con le prove; per ognuna c'è una via proposta.
- **Nessun pacchetto si costruisce oggi**: le ricette Windows e Flatpak sono ancora quelle dell'app GTK da cui Meridiana è nata, l'aggiornatore esiste ma nessuno lo chiama, e il CI ha consumato 973 minuti in tre giorni [V, H].

Perché non riscrivere: il valore di Meridiana sta nei calcoli e nelle regole, che sono giusti e provati; i difetti gravi sono concentrati in sei file e si curano uno alla volta con i 637 test come rete; una riscrittura di getto ripeterebbe il rischio da cui questi difetti vengono (codice scritto in due giorni senza un progetto dell'interfaccia) e butterebbe via le trappole già risolte (font, tema, scala dello schermo, thread di Qt). Il costo stimato delle correzioni di fondo (sezione 4) è di tre o quattro settimane di sessioni; quello di una riscrittura sarebbe di mesi, con gli stessi numeri da validare di nuovo.

## 1. Metodo

- Nove temi (A architettura, B calcoli in tre parti, C prestazioni, D test, E progetto dell'interfaccia, F lato professionale e mappe, G qualità e sicurezza, H pacchetti), ciascuno affidato a un agente con un mandato scritto: leggere tutto il codice del tema, non campionarlo; misurare con comandi ripetibili; marcare ogni affermazione [V] o [I]; non toccare il programma; scrivere il rapporto in `docs/studio/18-prove/`.
- Il revisore principale ha verificato a campione le affermazioni che decidono il verdetto, leggendo il codice e l'archivio delle norme: la chiave della posa (`model.py:361-369`), `edit()` senza ripristino (`window.py:1177-1185`), `open_path` (`window.py:2340`), il bug di `preferences.py:93`, `tileFailed` mai collegato, l'assenza di `excepthook`, il modello a un diodo adattato al solo punto STC (`components.py:176-201`), `pvtechchoice=crystSi` (`pvgis.py:31-33`), l'art. 5 c. 2 del DM 37/08 nell'archivio, le ricette GTK in `build-aux/`. Tutte confermate.
- Le misure sono state fatte offscreen (Python 3.12.6, PySide6 6.12.0, i7-12700H, 20 core) mentre altri agenti leggevano: ogni tempo è la mediana di almeno cinque ripetizioni; le misure sullo schermo vero del 22-23/10 (`C:\Users\utente\dev\meridiana-prove`) sono citate dove servono.
- Le norme sono state lette nell'archivio di Daniel (`l'archivio locale delle norme`, edizioni CEI 0-21 e 0-16 2026-07, CEI 64-8 2024, DCPREV 14030/2025, DM 37/08 integrato con il DM 130/25, D.Lgs. 199/2021 vigente, ARERA) con `cerca_norme.py`; i confronti esterni con pvlib 0.16.1, l'API PVGIS 5.3 e i rapporti PVsyst pubblici già raccolti nello studio 11.

## 2. I temi

### 2.A Architettura e modello dei dati (`18-prove/A-architettura.md`)

**Che cosa è stato guardato.** Tutti gli 83 file, il grafo delle importazioni dall'AST (210 archi, 0 cicli), il flusso dei dati, l'annulla, il formato del file, il modello geometrico contro lo studio 16; prove offscreen su progetti generati fino a 2.280 moduli.

**Numeri chiave [V].** Qt fuori da `ui/` solo in `app.py` dentro `main`; `window.py` 2.474 righe di cui circa 700 di dominio in 26 funzioni (`EnergyJob._compute` è l'intera catena energetica); una rinomina sul progetto da 20 edifici e 40 sottocampi: 328 ms sul filo della finestra, 40 sottocampi riposati, un calcolo dell'anno (5 su 5); `_show_tree` 160 ms per 31.793 chiamate a `MarkDelegate.sizeHint`; annulla 840 ms; istantanee economiche (0,1-2 ms, 12-213 kB) ma pila senza limite.

**Difetti principali.** La propagazione delle modifiche (`layout_key` serializza tutto, `_layout_done` riavvia sempre l'energia); nessun aggiornamento incrementale delle viste; `edit()` senza ripristino; file senza validazione; `config._typed` non controlla i float (`veil` testo fa cadere la finestra all'avvio); riferimenti fragili (`SubField.pitch` per indice, `removed` con chiavi di posizione che si spostano di 0,83 m cambiando il passo); falde sul rettangolo minimo (120 m² fuori da una L); il modello importa la simulazione.

**Verdetto.** Tieni 76 %; rifai per passi `model.py`, `roofs.py`, `layout.py`, `energy/system.py`, `window.py`, la scena di `plan.py`; sostituisci 0. L'architettura obiettivo (A §9): livelli `ui` / `session` (senza Qt: progetto, risultati, energia, selezione, annulla, chiavi per oggetto, eventi per argomento, lavori come funzioni) / `core` / `io` / `services`; migrazione «strangler» in sette passi con i test verdi, i primi quattro prima dei compiti 16a-g.

### 2.B Correttezza dei calcoli (`18-prove/B-calcoli.md`, `B-pvsyst.md`, `B-norme-citazioni.md`)

**Contro pvlib [V].** Stesso anno sintetico dei test, 188 LONGi 495 a 15° sud, 2 Huawei 50 kW: scarto 0,0000 su POA, IAM, temperatura della cella, potenza a 25 °C, DC, AC; contro `ModelChain` +1,21 % AC spiegati (IAM sul diffuso con Marion, come PVsyst; gamma del modello a un diodo contro quello di scheda).

**Contro PVGIS 5.3 [V].** Rho, 74,1 kWp: Meridiana 104.775 kWh (1.414 kWh/kWp, PR 85,8 %); PVGIS con le perdite predefinite del 14 % 94.483; a parità di perdite (8,0 %) e con i coefficienti `crystSi` del 2011 +3,66 %; con `crystSi2025` -0,02 %. L'orizzonte è irrilevante a Rho; lo spettro (+1,06 % in PVGIS) manca in Meridiana; il confronto mensile non è significativo (anno tipo contro media di 19 anni, mesi fino a +22 % di GHI).

**Contro PVsyst [V, B3].** Otto casi pubblici ricostruiti con l'API del nucleo: con lo stesso meteo orario e lo stesso modulo, GlobInc e GlobEff entro 0,2 %, EArrMPP entro ±1,5 %, E_Grid entro ±2 %, PR entro +1,8/-0,6 punti; geometria delle file (ombra, cielo nascosto, albedo) entro 0,1 punti. Scarti sistematici con la causa provata: bilancio termico con l'efficienza STC (+0,16/+0,57 punti), cavi DC scalati con P invece che con I² (+0,2/+0,25 punti), parametri del modulo CEC/De Soto invece del `.PAN` (±1 punto), effetto elettrico delle file sempre acceso (-1,49 % dove PVsyst lineare dà 0). Il meteo pesa più del modello: PVGIS 5.3 contro Meteonorm da +8 a +30 % di GHI fuori dall'Italia.

**Ombre, economia, fasce [V].** Geometria esatta sui nodi della griglia 5° x 4°; fra i nodi fino a 0,10 di frazione oraria, +1,2 % della perdita annua del muro; effetto elettrico uguale a Martinez-Moreno e a pvlib alla quinta cifra. `dispatch`, `balance`, VAN, TIR, tempi di ritorno, LCOE, bolletta: uguali al calcolo a mano a 1e-6; `band_of` contro ARERA 181/06: 0 ore diverse su 35.064 (2024-2027), Pasqua e ora legale comprese.

**Norme [V, B6].** 101 citazioni: 92 confermate con articolo e pagina, 7 imprecise (riferimenti, nessuna soglia sbagliata), 7 non verificabili (documenti assenti). Da correggere prima della relazione: N02/N03 (DM 37/08 art. 5 c. 2: potenza impegnata dell'utenza e superficie, non potenza del FV), N22 (Allegato Bbis della CEI 0-21, non Nbis), N15 (figure e alternative del 4.2 della DCPREV), N23/N27 (D.Lgs. 190/2024 Allegato A Sez. I; DM MASE 223/2026 al posto di TNE), N05 (FAQ CEI 2017 non in archivio), N04 (Allegato D e Gbis), `model.py:8` (CEI 82-25/1 3.2.3.2), N08, N13. Mancano le regole su potenza reattiva e cosφ (CEI 0-21 8.4.4.2), SLI e PIR (Allegato L), squilibrio tra fasi (8.3.1), cabina DSO oltre 100 kW in BT (7.4.10), cavi, SPD e RCD della sezione 712, collocazione degli inverter e compartimentazioni della DCPREV, BESS (circolare DCPREV 21021/2024 da scaricare).

**Difetti principali.** Il modello a un diodo adattato al solo punto STC (`components.py:176-201`): la resa a bassa irradianza è un artefatto (+0,9/+1,2 % sull'anno, dove PVsyst dà -0,5/-1,5 %); il secondo parere PVGIS con `pvtechchoice=crystSi` e la base di anni diversa (`pvgis.py:31-33`, `window.py:226-236`); `cells_in_series` fidato dal record CEC (`components.py:70-71`: il Jinko 540 diventa lineare); inverter per tutto l'impianto senza taglio per ingresso MPPT (`simulate.py:357-358`); parametri `.PAN` non letti (`panond.py:82-133`).

**Verdetto.** `simulate`, `nearshade`, `economics`, `bands`, `consumption`, `stringing`: tieni. Da relazione oggi: irradiazione sul piano e orizzonte, riflessione, temperatura, catena delle perdite, inverter (curva media, da dire), energia annua, resa, PR, bilancio orario, batteria, economia e fasce, con la fonte meteo scritta e le perdite dichiarate, per impianti fissi monofacciali a stringa con DC/AC vicino a 1 in BT (±2 % oltre al meteo). Non senza avvertenza: il passo «livello di irradianza», l'effetto elettrico delle ombre, l'autoconsumo su profili sintetici, il confronto mensile con PVGIS. Mancano bifacciale, spettro, degrado e P50/P90, neve, sporcamento mensile, trasformatore e ausiliari, cavi con lunghezze, inseguitori, meteo diverso da PVGIS.

### 2.C Prestazioni (`18-prove/C-prestazioni.md`)

**Bilancio proposto e stato di oggi [V, offscreen].** Avvio 1,52 s (obiettivo 1 s: pandas 0,41 s e matplotlib 0,35 s all'import); gesti 10-38 ms su 188 moduli e 53-114 ms su 4.682 (obiettivo 100 ms: `_show_3d` rifà `module_table` a ogni clic, `_layout_done` blocca 126-164 ms); calcolo 1,2-1,4 s a caldo e 2,1-2,5 s a freddo per 188 moduli (obiettivo 1 s), 4,6-5,2 s a freddo per 4.964 e 11,3 s per 20.493 (obiettivo 10 s); posa 0,34-0,76 s per 5.000 e 0,8-0,9 s per 20.493 (rispettato); apertura 0,5-0,6 s per 5.000 e 2,05 s per 20.000 (rispettato).

**R31, `dispatch` in cinque modi [V].** Riferimento 3,3 ms a chiamata, 538 ms per 156; stato a vettore per tutte le batterie e gli anni 70 ms (7,7 volte, zero dipendenze); numpy a prefisso 0,87 ms (2,6-3 volte); numba 0,055 ms (58 volte) ma 147 MB di pacchetti, 0,45 s di import, 142-499 ms di prima chiamata per processo; Rust: crate scritto, compilazione fermata al linker (gcc assente nella WSL), guadagno atteso pari a numba [I]. Tutte le varianti uguali al riferimento (`allclose` a 1e-9).

**Scalabilità [V].** Posa lineare (40-80 µs per modulo); tabella d'ombra 1,14 s per 188 moduli, 4,2 s per 5.000, 9,6-10,3 s per 20.000: cresce con piani x celle; memoria 12,7 kB per modulo (248 MB a 20.000); pianta sempre 15 elementi grafici, passaggio del mouse 1-5 ms.

**Verdetto.** Non si compila nulla e non si riscrive nessun modulo per le prestazioni: tre algoritmi da cambiare (`dispatch` a vettore con riuso dell'anno 1, una sola `simulate`, ombra per cella vettoriale) e quattro cicli da vettorializzare (`evaluate`, `module_table`, posa, `module_shapes`), import pigri: calcolo a caldo da 1,2-1,4 s a 0,4-0,6 s [I], avvio verso 0,6-0,7 s [I]. Compilare `dispatch` con numba o Rust è da non fare.

### 2.D I test (`18-prove/D-test.md`)

**Numeri [V].** 54 file, 8.541 righe, 637 test, 0 errori, 3 saltati; 149,9 s offscreen (368-389 s sullo schermo vero); 148 test costruiscono 157 `MainWindow` e costano 118 s; copertura 88,1 % (tracer C) e 89,2 % (`sysmon`, che vede i thread di Qt); nucleo alto (simulate 99 %, model 97,5 %, layout 97 %, nearshade 95 %).

**Buchi veri.** Le migrazioni del file provate mutando il JSON di oggi, nessun file d'esempio per versione; nessun test vede una risposta vera di PVGIS 5.3; il disegno fino al progetto (`_drawn`) senza test; la relazione provata senza inverter né regole; i rami d'errore su disco senza test; `test_release.py` con un `glob` non ricorsivo (un trattino lungo in `docs/studio/06` sfugge); valori normativi senza fonte nei test.

**Verdetto.** Il metodo (628 nomi su 637 sono frasi) si tiene. La suite si riorganizza in nucleo, calcoli con le fonti, formati con un file per versione, widget, finestra (50-55 test invece di 148), esterni a richiesta; obiettivi: nucleo e calcoli sotto 20 s, tutto sotto 2 minuti offscreen e 4 minuti sul secondo schermo. Dieci aggiunte subito (D §7.3).

### 2.E Il progetto dell'interfaccia (`docs/design/interfaccia.md`)

Il documento raccoglie le decisioni degli studi 12-17 e del registro in un disegno solo: chi la usa e che cosa deve uscire per ciascun destinatario; il percorso dal sito alla relazione nelle sei fasi di B4, come luoghi sempre apribili e non tappe; per ogni fase oggetti, azioni e tasti, pannelli, verifiche, uscite; la struttura della finestra (A3, T2, B4 con il testo e l'opzione, C2/C3/R2, D2, E3, F2, Meridio G2 con le domande numerate e il fumetto); **tredici contraddizioni** fra decisioni e studi con la via proposta per ognuna; le tre scelte aperte con una proposta (manuale nel repository letto dentro il programma; interazioni dei grafici in ordine: valore al passaggio, legenda, zoom sugli orari, esportazione; barra della fase a 68 px con il testo e 44 senza, sole icone sotto 900 px di altezza); la fase 6 «Relazione» come nuova; che cosa si tiene e che cosa si rifà, con l'ordine e il verdetto per ciascun compito 16a-g, 17a-f e 14; gli elaborati che mancano per una relazione da consegnare.

**Verdetto.** L'interfaccia si rifà sopra la base di oggi (`QMainWindow` con i pannelli, il `QTabWidget` che diventa la riga delle fasi, le barre nelle viste, il tema, le verifiche, l'annulla, i lavori in thread). Compiti da cambiare prima di lanciarli: 17b da riscrivere (è scritto su B1), 17d e 17e (scritti sulla raccomandazione invece che sulla scelta E3/F2), 17f (fumetto, raggi lenti, smorfie, pixel), 17a (regole di profondità), 16c e 16d (strumento Fila, inverter nell'ispettore); confermati 16a, 16b, 16e, 16f, 16g, 17c, 14.

### 2.F Il lato professionale e le mappe (`18-prove/F-professionale-mappe.md`)

Rapporto in forma ridotta (il primo agente si è fermato per il limite della sessione; il secondo ha letto i GetCapabilities veri dei servizi e le pagine delle licenze).

**Le mappe (R36) [V].** Il **WMS del Catasto dell'Agenzia delle Entrate** (`wms.cartografia.agenziaentrate.gov.it/inspire/wms/ows01.php`, WMS 1.3.0, livelli `fabbricati` e `CP.CadastralParcel`, CC BY 4.0, nessuna chiave, uso commerciale ammesso, Italia senza Trento e Bolzano) è la sorgente da aggiungere per prima, come sovrapposizione: non accetta EPSG:3857 né 4326 (solo 25832, 3044, 4258), quindi Meridiana deve riproiettare. Le ortofoto PCN/MASE 2012 non hanno vincoli dichiarati (50 cm) ma il servizio risponde solo in `http`. Le ortofoto regionali recenti (Lombardia 2018-2019 in WMTS, Piemonte AGEA 2018, Veneto 2018, 2021 e AGEA 2024) funzionano, ma la licenza d'uso non è dichiarata: da trattare come «solo visualizzazione e cache» finché le Regioni non rispondono. OSM vieta il prelievo anticipato e l'uso offline; Esri lega le immagini al suo software; Google Map Tiles vieta cache e archiviazione; Azure ammette al massimo sei mesi di cache; MapTiler e Mapbox non verificati: nessun servizio commerciale va predefinito. Le sagome degli edifici (Microsoft, CDLA Permissive 2.0; Overture, ODbL; OSM) sono salvabili con attribuzione; IGN, PNOA (CC BY 4.0) e swisstopo pure. Google Solar API: 10 USD per 1.000 chiamate (10.000 gratuite al mese), termini diversi nello SEE dall'08/07/2025, copertura italiana da verificare. Proposta: sorgenti configurabili con attribuzione obbligatoria e chiave nel portachiavi di sistema, mai nel file di progetto; tre livelli di conservazione (nel progetto, cache con scadenza, nulla).

**I programmi [V, prezzi letti il 23/10].** PVsyst CHF 700 l'anno; PV*SOL premium 845 EUR l'anno; Blumatica Impianti Fotovoltaici 250 EUR (2024, solo Windows); Sunny Design gratuito; HelioScope e Aurora 99-259 USD al mese; Solarius PV senza prezzo pubblico. Solarius e Blumatica fanno l'unifilare automatico, l'import DXF/DWG e IFC e le CER.

**Che cosa manca a Meridiana**, in ordine di valore (F §3): inverter e stringatura (16d), unifilare in DXF/DWG, cavi e protezioni, allegati per il distributore, pratica GSE, relazione consegnabile con il DM 37/08, import DXF/DWG e IFC, catasto e sagome, export DXF/IFC, accumulo dimensionato, l'elaborato di prevenzione incendi (dove Meridiana può battere gli altri), formati PVsyst, computo metrico, inseguitori e bifacciale, import meteo.

### 2.G Qualità del codice, sicurezza, licenze (`18-prove/G-qualita-sicurezza.md`)

**Numeri [V].** 1.228 funzioni, 27 oltre 60 righe, 11 oltre 100 (`simulate` 253, `_actions` 212, `MainWindow.__init__` 199, `build_html` 177, `layout.compute` 172, `evaluate` 161); 3 classi oltre 500 righe (`MainWindow` 2.074, `PlanView` 1.134, `Properties` 592); 100 `except`, nessuno nudo, 3 `except Exception` ai confini dei thread e loggati; 1.685 chiamate gettext tutte nel catalogo; 113 di 445 funzioni pubbliche del nucleo senza qualche annotazione. Stima: 71,5 % da tenere, 9,9 % da pulire, 18,6 % da rifare.

**Difetti principali.** La lettura del progetto senza validazione (8 file malformati su 20 fanno saltare lo slot, 3 lasciano la finestra a metà, `NaN` accettato); nessun `excepthook` e nessun log su file; riservatezza non detta (EXIF nelle immagini importate, progetto intero nelle copie di ripristino, indirizzo a Nominatim senza timeout, coordinate a PVGIS, riquadro ai server delle mappe con il PCN in HTTP) senza una riga nelle preferenze; errori mai mostrati (`tileFailed` scollegato, autosave e impostazioni solo su stderr); `preferences.py:93` riassegna `page` (le Preferenze si aprono sempre su Aspetto); testi non traducibili e italiano fisso nel nucleo; residui del template (metainfo, `.desktop`, icona e manifest descrivono il contatore di cartelle); `updates.py` e `minisign.py` completi ma non chiamati.

**Licenze [V].** Tutte compatibili con GPL-3.0-or-later (PySide6 LGPL-3, Qt Quick 3D GPL-3 quindi il binario è GPL-3, pvlib/shapely/numpy/scipy/pandas BSD, matplotlib PSF, requests Apache-2, Titillium OFL, Lucide ISC, CEC/SAM BSD-3). Mancano `requests` e `pandas` in `requirements.txt`, un file delle attribuzioni, `pyproject.toml`; `PySide6_WebEngine` nel venv è inutile.

**Verdetto.** Nucleo da tenere; finestra da rifare a pezzi (energia nel nucleo, `MainWindow` e `PlanView` divise per responsabilità). Prima di tutto, un giorno: validazione di `from_json` con messaggio e sostituzione del progetto a lettura finita; `excepthook` con log su file; `tileFailed`, autosave e impostazioni collegati alla barra di stato; poi la pagina delle preferenze sulla riservatezza e l'EXIF tolto.

### 2.H Pacchetti, rilascio, CI, documentazione (`18-prove/H-pacchetti.md`)

**Stato [V].** La spec di PyInstaller cerca MSYS2, gdbus e l'hook di gi; il manifest Flatpak monta il runtime GNOME senza PySide6, senza rete e con la home in sola lettura; desktop, metainfo, sito, CHANGELOG parlano di «una cartella contata». Il manifest Windows `dpiAware=true` bloccherebbe il per-monitor V2 di Qt (finestra sfocata sul secondo schermo). Flathub ha `org.kde.Platform` 6.10 e 6.11 (non 6.12) e `io.qt.PySide.BaseApp//6.11` con PySide 6.11.2: il pin `PySide6==6.12.0` va provato su 6.11.2 o si porta il wheel. L'aggiornatore (`updates.py`, `minisign.py`, 415 righe) è completo e testato ma nessuno lo chiama. Il CI: 127 esecuzioni in tre giorni, 973 minuti (Windows 5,1 min per job senza cache, WebEngine da 132 MB scaricato ogni volta), fermo dal 23/10 per la fatturazione.

**Verdetto.** Le ricette si sostituiscono con quelle di PySide6, pezzo per pezzo, tenendo ciò che è indipendente da GTK (Inno Setup, procedura di rilascio, firma, aggiornatore). Ordine: CI leggero (`H-ci-proposta.yml`: Linux offscreen a ogni push con cache, Windows solo su tag o a mano, circa 530 minuti al mese contro oltre 2.000), Windows (spec, manifest, icone con Pillow, `requirements.txt` con i tre wheel), aggiornatore in Qt e job di release con minisign, Flatpak (prova di 6.11.2 sul portatile), identità e documenti, manuale (dopo il progetto dell'interfaccia). 9-12 giorni.

## 3. Il verdetto complessivo

**Tenere e migliorare per passi.** Le prove dicono che la parte difficile di un programma di progettazione fotovoltaica, cioè i numeri, è giusta e documentata con la sua fonte; la parte che non regge è il modo in cui la finestra tiene insieme le cose, e si cura con una sessione senza Qt e con aggiornamenti per argomento (A §9), senza toccare i calcoli. I sei file da rifare per passi sono il 24 % delle righe; ogni passo lascia i test verdi e un programma che funziona.

**Che cosa non si fa.** Nessuna riscrittura di getto; nessun cambio di linguaggio (R31: Python con numpy scritto nel modo giusto dà il 90 % del guadagno di un linguaggio compilato sul pezzo misurato, senza costi di distribuzione); nessuna libreria nuova per le prestazioni; nessuna sostituzione di modulo con una libreria esterna (le decisioni prese escludono CGAL e una libreria minisign con ragione).

**L'architettura obiettivo** (A §9, riassunta): `ui` (Qt, solo cablaggio e viste), `session` (senza Qt: progetto, risultati, energia, selezione, annulla con ripristino, chiavi per oggetto, eventi per argomento, lavori come funzioni pure), `core` (modello tipizzato e validato, geometria, energia con la pipeline estratta, verifiche, regole), `io` (file con fixture per versione, impostazioni, scritture atomiche), `services` (meteo, PVGIS, tasselli, geocoding senza Qt). Regole: `core` non importa `session` né `ui`; `session` non importa Qt; `energy` non legge il `Project`; una vista si aggiorna per argomento, mai «tutto».

**Le tre cose da fare subito** (sezione 4, compito 18a), perché toccano i dati e la fiducia: la validazione del file di progetto con un messaggio, il gestore globale degli errori con il log, le note normative corrette.

## 4. Il piano

I compiti sono in `docs/compiti/` con il prefisso `18`; i compiti 16a-g, 17a-f e 14 restano, con le modifiche segnate in testa dalla revisione (`docs/design/interfaccia.md` §6.4). Fatica in giorni di sessione; le dipendenze dicono che cosa deve venire prima.

| Ordine | Compito | Che cosa | Fatica | Dipende da |
|---|---|---|---|---|
| 1 | `18a-fondamenta.md` | Validazione del file e dell'apertura; `excepthook` con log su file; errori di rete, autosave e impostazioni alla barra di stato; bug delle Preferenze; EXIF tolto e pagina della riservatezza; correzioni delle citazioni normative (B6 §4.1 e N02/N03); secondo parere PVGIS con `crystSi2025` e la base di anni detta; `requirements.txt`; `test_release` ricorsivo; residui del template | 3 | nessuno |
| 1 | `18f-pacchetti.md`, passo 1 | Il CI leggero al posto di `test.yml` | 0,5 | nessuno |
| 2 | `18b-sessione.md` | A §9.3, passi 1-4: pipeline energetica nel nucleo; `session.py` con l'annulla che ripristina; chiavi per oggetto ed eventi per argomento (accettazione: rinomina sotto 100 ms, nessuna posa, nessun anno); modello tipizzato e validato con un file d'esempio per versione | 7 | 18a |
| 2 | `18c-prestazioni.md` | C §7: `dispatch` a vettore con riuso dell'anno 1; una sola `simulate`; `evaluate` per array; ombra per cella vettoriale; `module_table` e posa in numpy; import pigri; tessere fuori dal filo principale | 4 | i passi sul nucleo subito; quelli sulla finestra dopo 18b |
| 2 | `18d-calcoli.md` | B §6 e B3 §8: modello del modulo (parametri `.PAN` via `calcparams_pvsyst`, `cells_in_series` robusto, bassa irradianza); efficienza al punto di lavoro nel bilancio termico; cavi in I²; interruttore lineare/elettrico con frazione; inverter per ingresso MPPT dalla stringatura (con 16d); LID coerente; i limiti dichiarati nella relazione; poi altre fonti meteo (`.MET`, CSV, 5.2/5.3) | 5 | nessuno per i primi passi; 16d per l'inverter per ingresso |
| 3 | `17a` (modificato), `17b` (riscritto: fasi e barra della fase, `phases.py`) | Le superfici e i controlli; le sei fasi con la fase 6 come guscio | 7-9 | 18b |
| 4 | `16d`, poi `16a`, `16b`, `16c` (sulla sessione) | Impianto e stringhe; tetti; sposta e ruota; posa manuale | come scritto | 17b, 18b |
| 5 | `17e`, `17d`, `17f` (modificati), in parallelo | Verifiche per livello; aiuto E3; Meridio con il fumetto | come scritto | 17a |
| 6 | `18e-test.md` | D §7: la suite riorganizzata (nucleo, calcoli con le fonti, formati, widget, finestra ridotta, esterni), le dieci aggiunte | 3, a tappe | 18b per la finestra ridotta |
| 7 | `17c`, `16e`, `16f`, `16g` | Grafici; filtri; attese; perno | come scritto | 17a |
| 8 | `18f-pacchetti.md`, passi 2-6 | Windows, aggiornatore, Flatpak, identità e documenti, manuale | 9-12 | 17a-b per il manuale |
| 9 | Fase Relazione piena (`design` §7) e `14-assistente-prototipo.md` | Gli elaborati; Meridio che risponde | da scrivere; come scritto | 16d, 17b |

Le sorgenti delle mappe (R36) entrano in un compito proprio quando il rapporto F è completo: sorgenti WMS/WMTS/XYZ configurabili con alcune predefinite, licenze lette sulle fonti.

## 5. Le domande a cui solo Daniel può rispondere

1. **La sessione prima dei tetti** (A §10): il piano mette `18b` prima di 16a-g, così tetti, sposta e file nascono sul modello nuovo. L'alternativa è fare 16a-g subito sulla finestra di oggi e migrare dopo, con il doppio lavoro. Va bene l'ordine proposto?
2. **I risultati salvati nel file di progetto** con la loro chiave (A §9.2, come fa PVsyst): alla riapertura si mostra e non si ricalcola; il file cresce. Sì o no?
3. **La riservatezza**: una pagina delle preferenze che dice quali servizi ricevono che cosa (Nominatim, PVGIS, mappe) e permette di spegnerli; alla prima apertura chiedere il consenso o solo informare?
4. **Altre fonti meteo** (B3 §8): leggere `.MET` e CSV di PVsyst e Meteonorm, scegliere PVGIS 5.2/5.3, è il primo passo per riprodurre un rapporto PVsyst italiano. Quanto conta rispetto al resto?
5. **Il CI**: adottare subito il flusso leggero (Linux a ogni push, Windows solo su tag o a mano) riaccende il CI con pochi minuti al mese. Sì?
6. **La FAQ CEI del 07/06/2017** citata in N05 non è in archivio: toglierla dal codice e appoggiare la regola a CEI 0-21 8.4.1 e Bbis.1, oppure la cerchi tu?
7. **Il manuale nel repository**, letto dentro il programma (design §5.1): va bene?
8. **pyqtgraph** come libreria nuova per i grafici (17c): il «forse» va chiuso prima di lanciare 17c.
9. **La barra della vista**: in alto a sinistra sotto la barra della fase (come deciso) o in basso a sinistra come Revit (design C6)? Si decide su una schermata di confronto, da fare nel 17a.
10. **Il segreto minisign nel repository** per il job di release (H): quando vorrai le release firmate.

## 6. Da provare sul PC di Daniel

- La prova della rinomina e dell'annulla sui progetti di Rho (188 e 4.682 moduli) sullo schermo vero (`18-prove/A-architettura-prove.py`), dopo 18b: rinomina sotto 100 ms.
- Che cosa vede l'utente quando uno slot solleva un'eccezione nella build senza console; PCN giù; «Trova il sito» senza rete; l'EXIF riletto da un `.meridiana` (G §11).
- La trasposizione a due falde del caso LaFact (-3 punti, B3 §6.11), con PVsyst sul PC.
- La suite con PySide6 6.11.2 e il build Flatpak sul portatile (H); il build Windows con la spec nuova sui due schermi (DPI 2,5).
- La misura Rust di `dispatch` (serve `gcc` nella WSL: comandi in C §8), solo per completezza: il verdetto non cambia.
- Un'ora di lavoro con Meridio animato; le schermate di 17a con i tre livelli di contorno (design C2); la barra della vista nelle due posizioni (C6).

## 7. Fonti e file

- Rapporti: `docs/studio/18-prove/A-architettura.md`, `B-calcoli.md`, `B-pvsyst.md`, `B-norme-citazioni.md`, `C-prestazioni.md`, `D-test.md`, `G-qualita-sicurezza.md`, `H-pacchetti.md`, `F-professionale-mappe.md`; `docs/design/interfaccia.md`.
- Script e risultati: `A-architettura-grafo.py`, `A-architettura-prove.py`, `confronto_pvlib.py`, `confronto_pvgis.py`, `ombre_caso_analitico.py`, `economia_a_mano.py`, `confronto_pvsyst.py`, `confronto_pvsyst_ipotesi.py`, `dispatch_varianti.py` con `dispatch_rs/`, `scalabilita.py`, `energia_tempo.py`, `avvio.py`, `profilo_energia.py`, `G-misure.py`, `G-prova-file-progetto.py`, `H-ci-minuti.py`, `H-ci-proposta.yml`, `D-coverage.txt`, `D-coverage-sysmon.txt`, ciascuno con il suo `-risultati.txt`.
- Esterni: pvlib 0.16.1; API PVGIS 5.3 (23/10/2026); i rapporti PVsyst pubblici dello studio 11; l'archivio delle norme di Daniel (edizioni in B6 §0); le misure del 22-23/10 in `C:\Users\utente\dev\meridiana-prove`.
