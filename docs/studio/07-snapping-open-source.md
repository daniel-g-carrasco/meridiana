# Snapping e aiuti al disegno nei programmi open source: cosa può prendere Meridiana

Ricerca del 21/10/2026 per Meridiana (Python/PySide6, GPL-3.0-or-later), editor 2D che traccia contorni di edifici, falde e aree moduli sopra ortofoto.

Legenda:
- **[V]** verificato leggendo il sorgente o il manuale ufficiale, al commit indicato (link fisso con righe).
- **[I]** dedotto da me: interpretazione, proposta, oppure fonte non ufficiale.

Metodo: ho scaricato solo i singoli file (raw GitHub/GitLab), senza clonare i repository. Ho controllato che i file letti coincidano con i commit citati sotto.

---

## 0. In breve

1. Sì, i problemi di Meridiana sono già stati risolti bene altrove. I riferimenti più utili sono due.
   - **QGIS**, pannello "Advanced Digitizing": blocchi duri e morbidi, angoli comuni, parallelo e perpendicolare, campi numerici vicino al cursore, input tollerante con la virgola decimale.
   - **iD e JOSM** (editor OpenStreetMap): squadratura "Q" di un edificio tracciato su foto aerea, angoli rispetto a un lato di riferimento, edifici rettangolari in 2 o 3 clic.
2. La squadratura di iD è sotto licenza **ISC**: si può portare in Python dentro Meridiana, conservando la nota di copyright e di permesso. Ho scritto e provato una bozza (sezione 5.5).
3. Il cuore dello snapper di **LibreCAD** è **GPL-2.0-only**: non si può copiare in un programma GPL-3.0. Si possono solo imitare i comportamenti descritti nella documentazione.
4. QGIS, JOSM (core), FreeCAD, QCAD, Inkscape, Blender e SolveSpace hanno licenze compatibili con GPL-3.0-or-later. Conviene comunque **reimplementare i comportamenti** e non tradurre il codice, che è legato ai loro framework.
5. Da adottare per primi: squadratura Q con anteprima; input "lunghezza;angolo" con Tab tra i campi; blocchi duri (Shift, X, Y, valori digitati) distinti dai blocchi morbidi (angoli comuni, allineamenti); Tab per ciclare i candidati; isteresi; rettangolo da 3 clic.

---

## 1. Commit letti

| Progetto | Repository | Commit | Data |
|---|---|---|---|
| FreeCAD | https://github.com/FreeCAD/FreeCAD | d3f4da791daa | 21/10/2026 |
| FreeCAD wiki (copia in git) | https://github.com/FreeCAD/FreeCAD-documentation | 0499378a238c | 15/01/2025 |
| QGIS | https://github.com/qgis/QGIS | 28c25b31bec8 | 21/10/2026 |
| QGIS manuale | https://github.com/qgis/QGIS-Documentation | 0eb963b4ebc1 | 19/10/2026 |
| iD | https://github.com/openstreetmap/iD | 1f6118db61b8 | 21/10/2026 |
| JOSM core (mirror ufficiale) | https://github.com/JOSM/josm | 103fd7edce20 | 21/10/2026 |
| JOSM plugin | https://github.com/JOSM/josm-plugins | ef94f6899694 | 13/10/2026 |
| LibreCAD | https://github.com/LibreCAD/LibreCAD | d06eba4d4b36 | 21/10/2026 |
| QCAD CE | https://github.com/qcad/qcad | f0b35cb4ff79 | 20/10/2026 |
| Inkscape | https://gitlab.com/inkscape/inkscape | e3270ca91ce4 | 21/10/2026 |
| Blender (mirror GitHub) | https://github.com/blender/blender | 0506bcdae0db | 21/10/2026 |
| SolveSpace | https://github.com/solvespace/solvespace | 30e1c3ac0beb | 21/10/2026 |
| Potlatch 2 | https://github.com/systemed/potlatch2 | 14f6fd88ee6b | 31/12/2020 |

---

## 2. FreeCAD, Draft workbench (Python)

### 2.1 File
- `src/Mod/Draft/draftguitools/gui_snapper.py`: classe `Snapper`, tutta la logica di snap. [V] [gui_snapper.py](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py)
- `src/Mod/Draft/draftguitools/gui_trackers.py`: i "tracker", cioè la grafica temporanea (marcatore, linee guida, raggio, quote). [V] [gui_trackers.py](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_trackers.py#L63-L139)
- `src/Mod/Draft/DraftGui.py`: pannello dei comandi, campi X/Y/Z/Lunghezza/Angolo, tasti dentro il comando, blocchi dei campi. [V] [DraftGui.py](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1514-L1622)
- `src/Mod/Draft/draftguitools/gui_tool_utils.py`: `get_point()`, legge i modificatori e chiama lo snapper. [V] [gui_tool_utils.py L275-330](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_tool_utils.py#L275-L330)
- `src/Mod/Draft/draftutils/params.py` e `Resources/ui/preferences-*.ui`: valori di default. [V] [params.py L526-538](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftutils/params.py#L526-L538)
- `src/Mod/Draft/draftguitools/gui_snaps.py`: i comandi della barra degli snap. [V] [gui_snaps.py](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snaps.py)

### 2.2 Tipi di snap
Lock (interruttore generale), Near, Extension, Parallel, Grid, Endpoint, Midpoint, Perpendicular, Angle, Center, Ortho, Intersection, Special, Dimensions, WorkingPlane. [V] [gui_snapper.py L137-156](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L137-L156)

"Ortho" significa linee polari dal punto precedente a multipli di 45° (lista `polarAngles = [90, 45]`). [V] [L127](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L127), [L720-752](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L720-L752)

### 2.3 Ordine di valutazione (funzione `snap()`)
1. Calcola il raggio: `snapRange` pixel convertiti in unità del modello vicino al cursore. Default 8 px. [V] [L286-290](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L286-L290), [L1167-1172](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1167-L1172), [params.py L538](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftutils/params.py#L538)
2. Prima le direzioni: polare, poi "hold points", poi estensioni e parallele. Queste spostano il punto di lavoro e preparano una linea guida (`eline`). [V] [L316-321](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L316-L321), [L575-687](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L575-L687)
3. Poi l'oggetto sotto il cursore: per quell'oggetto genera **tutti** i candidati attivi (near, estremi, punto medio, perpendicolare, intersezioni, intersezione con la linea guida, centro e angoli degli archi). [V] [L389-470](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L389-L470)
4. **Scelta del vincitore**: vince il candidato più vicino al punto del cursore. Nessuna priorità fissa tra i tipi. Eccezione: "Near" perde se un altro candidato sta entro `snapRange` pixel sullo schermo. [V] [L487-517](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L487-L517). Regola introdotta il 11/03/2025. [V] [commit 849cf3fa](https://github.com/FreeCAD/FreeCAD/commit/849cf3fa756558945b4827885a0d0309824d3677)
   - Nota: la copia del wiki dice ancora che Near "ha la precedenza su molti altri snap". È anteriore a quel commit. [V] [Draft_Snap.md](https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Draft_Snap.md)
5. Se non c'è nessun oggetto: intersezione delle ultime due estensioni, altrimenti griglia. [V] [L339-346](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L339-L346)
6. Alla fine applica il vincolo (Shift) e i campi bloccati del pannello. [V] [L347-348](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L347-L348), [L1272-1290](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1272-L1290)

Altri dettagli utili:
- Ricorda gli ultimi 8 oggetti toccati, per estensioni, parallele e intersezioni "virtuali". [V] [L472-482](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L472-L482). È l'equivalente dei lati "acquisiti" di Meridiana. [I]
- **Hold point** (tasto Q): fissa un punto di riferimento. Poi aggancia gli assi orizzontale e verticale che passano per i punti fissati, le loro intersezioni e il punto medio tra due punti fissati. [V] [L920-969](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L920-L969), [L1785-1792](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1785-L1792)
- **Snap cycling** (tasto accento grave, `` ` ``): passa all'oggetto successivo sotto il cursore, quando gli oggetti si sovrappongono. [V] [DraftGui.py L72-84](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L72-L84), [L361-363](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L361-L363)

### 2.4 Modificatori, vincolo, assi
- Default: "Always snap" acceso; modificatore snap Ctrl (conta solo se "Always snap" è spento); vincolo Shift; modificatore Alt. [V] [preferences-draftsnap.ui L383-491](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/Resources/ui/preferences-draftsnap.ui#L383-L491), [gui_snapper.py L292-294](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L292-L294), [gui_tool_utils.py L52-64](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_tool_utils.py#L52-L64)
- **Shift tenuto**: il punto viene proiettato sull'asse del piano di lavoro più vicino alla direzione del movimento. L'asse scelto (`affinity`) resta fisso finché Shift resta premuto: non salta da X a Y. [V] [L1350-1430](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1350-L1430). È già una forma di isteresi. [I]
- **X, Y, Z**: forzano l'asse. Lo stesso tasto toglie il vincolo, un altro tasto lo cambia. [V] [DraftGui.py L1547-1558](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1547-L1558), [Draft_Constrain.md](https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Draft_Constrain.md)
- Raggio di snap: P lo aumenta e M lo riduce di 1 px, al volo, e mostra il cerchio del raggio. [V] [preferences-draftinterface.ui L557-586](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/Resources/ui/preferences-draftinterface.ui#L557-L586), [DraftGui.py L1939-1943](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1939-L1943)

### 2.5 Input numerico, relativo e globale
- Campi X, Y, Z, Lunghezza, Angolo. Invio nella Lunghezza porta il cursore nel campo Angolo. [V] [DraftGui.py L1428-1434](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1428-L1434)
- Se il primo carattere digitato è una lettera, vale come comando: R relativo, G globale, X/Y/Z assi, Q hold point, S snap on/off, ecc. [V] [DraftGui.py L1514-1622](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1514-L1622), [preferences-draftinterface.ui](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/Resources/ui/preferences-draftinterface.ui#L45-L702)
- Nel codice attuale L **blocca o sblocca l'angolo corrente**: poi si digita solo la lunghezza. È il flusso "blocco la direzione, scrivo la misura" che serve a Meridiana. La copia del wiki descrive ancora il vecchio L (passa tra X e Lunghezza). [V] [DraftGui.py L1542-1546](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1542-L1546), [L1945-1951](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1945-L1951), [Draft_Line.md](https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Draft_Line.md)
- Relativo: coordinate rispetto all'ultimo punto. Globale: sistema globale invece del piano di lavoro. [V] [gui_snapper.py L1511-1522](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1511-L1522), [Draft_Line.md](https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Draft_Line.md)
- **Campi bloccati**: un valore bloccato in X, Y, Lunghezza o Angolo sostituisce la componente del punto agganciato. [V] [DraftGui.py L422-457](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L422-L457)
- **Mouse delay**: dopo aver digitato un numero, per 1 secondo il mouse non cambia i valori. Evita di perdere il numero per un movimento involontario. [V] [preferences-draft.ui L267-279](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/Resources/ui/preferences-draft.ui#L267-L279), [DraftGui.py L1636-1653](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1636-L1653)

### 2.6 Tracker
Ogni tracker è un nodo Coin3D con un interruttore (`SoSwitch`) acceso o spento; può stare "sopra" la scena. Tipi: marcatore dello snap, linea tratteggiata (estensioni, vincolo), cerchio del raggio, quote temporanee, griglia. [V] [gui_trackers.py L63-139](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_trackers.py#L63-L139), [L1626-1665](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_trackers.py#L1626-L1665). In Meridiana l'equivalente sono oggetti di overlay del QGraphicsScene. [I]

### 2.7 Licenza
- Intestazione dei file: `SPDX-License-Identifier: LGPL-2.1-or-later` (il testo sotto dice "version 2 ... or any later"). [V] [gui_snapper.py L1-10](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1-L10)
- La LGPL 2.1, sezione 3, permette di passare il codice sotto GPL versione 2 o successiva. Quindi è utilizzabile in GPL-3.0-or-later, con le note di copyright. [V] [LICENSE L211-217](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/LICENSE#L211-L217)

---

## 3. QGIS

### 3.1 File
- `src/core/qgscadutils.cpp` e `.h`: funzione pura `QgsCadUtils::alignMapPoint()`. Riceve punto, vincoli e snap; restituisce il punto finale e i blocchi morbidi attivi. È il pezzo più vicino allo snapper di Meridiana. [V] [qgscadutils.cpp L44-499](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L44-L499)
- `src/gui/qgsadvanceddigitizingdockwidget.cpp` e `.h`: pannello, tasti, blocchi, guide di costruzione. [V] [dock .cpp](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp), [dock .h](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.h)
- `src/gui/qgsadvanceddigitizingfloater.cpp`: i campi che seguono il cursore ("floater"). [V] [floater](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingfloater.cpp)
- `src/core/qgssnappingutils.cpp`: snap agli oggetti e classifica dei candidati. [V] [qgssnappingutils.cpp](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgssnappingutils.cpp#L178-L224)
- `src/core/qgstracer.cpp`: tracing. [V] [qgstracer.cpp](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgstracer.cpp#L187-L235)

### 3.2 Snap agli oggetti e priorità
- Tolleranza di default: 12 pixel. [V] [qgis.cpp L73-75](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgis.cpp#L73-L75)
- Ordine fisso per tipo, poi distanza: estremo di linea, poi vertice o intersezione, poi punto medio, poi centroide, poi lato, poi area. Un vertice vince anche se un lato è più vicino. [V] [qgssnappingutils.cpp L178-224](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgssnappingutils.cpp#L178-L224)
- Le intersezioni tra lati vicini al cursore si calcolano unendo i lati trovati e prendendo i nuovi nodi; valgono come vertici. [V] [L110-176](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgssnappingutils.cpp#L110-L176)
- La priorità di Meridiana (vertice, medio, primo punto, poi intersezioni, poi direzioni, poi lato) è dello stesso tipo di questa di QGIS. [I] [qgssnappingutils.cpp L188-194](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgssnappingutils.cpp#L188-L194)

### 3.3 Vincoli: ordine in `alignMapPoint()`
1. Snap agli oggetti (e alle guide di costruzione visibili). [V] [L54-68](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L54-L68)
2. X bloccato: imposta X; se il cursore è su un lato, calcola Y sul lato. Se X non è bloccato, blocco morbido sull'X di un vertice "acquisito" entro 15 px. Lo stesso per Y. [V] [L86-170](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L86-L170)
3. Angoli comuni (blocco morbido): scatta se l'angolo è entro 10° **e** il cursore è entro 15 px dalla retta. Può essere relativo all'ultimo lato. [V] [L30-33](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L30-L33), [L172-206](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L172-L206)
4. Angolo (duro o morbido): proietta il punto sulla retta. Con X o Y bloccati calcola l'intersezione. Se il cursore è su un lato, "magnetizza" il punto all'intersezione tra retta e lato. [V] [L208-308](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L208-L308). È lo stesso caso "guida per lato" di Meridiana. [I]
5. Estensione di un lato (morbido, 15 px) a partire dall'ultimo vertice acquisito. [V] [L310-413](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L310-L413)
6. Distanza bloccata: cerchio attorno al punto precedente, intersecato con X, Y, estensione o lato. Se i vincoli sono incompatibili il risultato è marcato non valido e compare un avviso. [V] [L415-486](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L415-L486), [dock L1575-1582](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1575-L1582)

### 3.4 Blocchi duri e morbidi
- Tre stati per ogni vincolo: nessuno, morbido, duro. L'angolo comune imposta un blocco morbido col suo valore; il blocco duro lo mette l'utente. [V] [dock L1489-1504](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1489-L1504)
- Dopo ogni clic i blocchi si liberano, salvo quelli in "blocco continuo". [V] [dock L963-1010](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L963-L1010), [L1786-1787](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1786-L1787), [manuale L2188-2197](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2188-L2197)
- Parallelo e perpendicolare (tasto P): il primo P attiva perpendicolare, il secondo parallelo, il terzo spegne. Passando sopra un lato si vede l'anteprima (blocco morbido). Cliccando sul lato l'angolo diventa duro e quel clic **non** aggiunge un vertice. [V] [dock L2181-2206](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L2181-L2206), [L1723-1835](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1723-L1835)
- "X/Y Point" e "Line Extension": passando sopra un vertice lo si acquisisce (fino a 3, coda FIFO); ripassandoci dopo essere usciti lo si toglie. [V] [dock L1412-1443](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1412-L1443), [manuale L1982-1992](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L1982-L1992)
- Angoli comuni disponibili: 0 (spento), 0,1, 0,5, 1, 5, 10, 15, 18, 22,5, 30, 45, 90 gradi. N e Shift+N scorrono la lista. [V] [dock L172](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L172), [L2207-2227](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L2207-L2227)
- Menu "Snapping priority": priorità agli oggetti oppure agli angoli comuni. Il default dà priorità agli angoli. [V] [dock L55](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L55), [L178-196](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L178-L196)

### 3.5 Tasti

| Tasto | Da solo | Ctrl o Alt + tasto | Shift + tasto |
|---|---|---|---|
| D | campo distanza | blocca distanza | |
| A | campo angolo | blocca angolo | angolo relativo all'ultimo lato sì/no |
| X | campo X | blocca X | X relativa all'ultimo vertice sì/no |
| Y | campo Y | blocca Y | Y relativa sì/no |
| Z, M | campo Z, M | blocca (Z solo con Alt) | relativo sì/no |
| C | modo costruzione sì/no | | |
| P | perpendicolare, parallelo, spento | | |
| N | angolo comune successivo | | angolo precedente |
| Esc | libera i blocchi | | |
| Backspace, Canc | toglie l'ultimo punto | | |

Fonti: [V] [manuale L2063-2087](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2063-L2087), [dock L1837-1866](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1837-L1866), [L1964-2234](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1964-L2234).

Trucco Qt utile anche per PySide6: Ctrl+D e Ctrl+A vanno in conflitto con scorciatoie globali. QGIS intercetta l'evento `ShortcutOverride` oltre a `KeyPress`. [V] [dock L1942-1962](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1942-L1962)

### 3.6 Altri aiuti
- **Floater**: campi vicino al cursore con distanza, angolo, XY, azimut, angolo comune, area e perimetro. Ctrl o Alt + tasto blocca il valore e lo mette in modifica; Invio conferma. [V] [manuale L2009-2036](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2009-L2036), [L2165-2169](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2165-L2169)
- **Lettura dei numeri tollerante**: prova il numero, poi un'espressione; se fallisce toglie il separatore delle migliaia o sostituisce la virgola decimale col punto. [V] [dock L1083-1138](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1083-L1138)
- **Modo costruzione** (C): i clic non aggiungono vertici, servono come riferimenti per distanze e angoli; le guide si possono registrare, mostrare e agganciare. [V] [manuale L2199-2267](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2199-L2267)
- **Tracing** (T): segue in automatico i lati esistenti tra due clic; cammino minimo (Dijkstra) sul grafo dei lati agganciabili; può avere un offset. [V] [manuale L320-385](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L320-L385), [qgstracer.cpp L187-235](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgstracer.cpp#L187-L235)
- **Rettangolo da 3 punti**, due modi. "Distanza": il terzo punto dà la larghezza come distanza dal secondo. "Proiettato": la larghezza è la distanza del terzo punto dalla retta del primo lato. Il lato della costruzione dipende da dove sta il terzo punto. [V] [manuale L1894-1902](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L1894-L1902), [qgsquadrilateral.cpp L38-100](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/geometry/qgsquadrilateral.cpp#L38-L100)
- **Orthogonalize**: `QgsGeometry::orthogonalize(tolerance=1e-8, maxIterations=1000, angleThreshold=15)`. Il codice dice "adapted from original code in potlatch/id osm editor". [V] [qgsgeometry.h L1463-1470](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/geometry/qgsgeometry.h#L1463-L1470), [qgsinternalgeometryengine.cpp L435-667](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/geometry/qgsinternalgeometryengine.cpp#L435-L667)

### 3.7 Licenza
Intestazioni "GNU GPL version 2 ... or (at your option) any later version", cioè GPL-2.0-or-later (nessuna riga SPDX in questi file). [V] [qgscadutils.cpp L8-15](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L8-L15), [dock L8-14](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L8-L14). Il file del rettangolo da 3 punti è "version 3 or later". [V] [qgsmaptoolshaperectangle3points.cpp L9-14](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/app/maptools/qgsmaptoolshaperectangle3points.cpp#L9-L14). Compatibili con GPL-3.0-or-later. [I]

---

## 4. JOSM (Java)

### 4.1 Squadratura `OrthogonalizeAction` (tasto Q)
File: `src/org/openstreetmap/josm/actions/OrthogonalizeAction.java`. [V] [GitHub](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java), [Trac](https://josm.openstreetmap.de/browser/josm/trunk/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java)

Algoritmo deterministico, non iterativo: [V] [L312-475](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L312-L475)
1. Dà a ogni lato una direzione tra 4 (destra, su, sinistra, giù), confrontando ogni lato col precedente. [V] [L503-525](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L503-L525), [L641-662](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L641-L662)
2. Calcola l'orientamento medio: somma vettoriale dei lati orizzontali più i verticali ruotati di 90°.
3. Ruota tutto attorno al baricentro dei nodi, così i lati sono quasi nord-sud o est-ovest.
4. Per ogni catena di lati orizzontali collegati, mette a tutti i nodi la Y media. Lo stesso per i verticali con la X.
5. Ruota indietro.

Opzioni: [V] [L51-55](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L51-L55), [L195-234](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L195-L234)
- con 2 nodi selezionati in più, la direzione è fissata da quei due nodi, che non si muovono;
- con 1 nodo selezionato si sposta solo quel nodo;
- più vie con nodi in comune si squadrano insieme;
- Shift+Q annulla la squadratura per i nodi selezionati.
- Tolleranza 45°: "Current policy is to except just everything". [V] [L72-79](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L72-L79)

Pregio per Meridiana: angoli esattamente retti in un passo e la possibilità di tenere fisso un lato scelto (per esempio la gronda tracciata sull'ortofoto). Limite: forza **tutti** gli angoli a 90° o 180°, quindi rovina gli smussi a 45°. [I] [L389-456](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L389-L456)

### 4.2 Aggancio angolare durante il disegno (`DrawAction`, `DrawSnapHelper`)
- Nel modo disegno, premere di nuovo A attiva o spegne l'aggancio angolare. **Tenere premuto** A fissa l'angolo corrente; al rilascio torna libero. [V] [DrawAction.java L88-90](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawAction.java#L88-L90), [L357-376](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawAction.java#L357-L376), [DrawSnapHelper.java L514-572](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawSnapHelper.java#L514-L572)
- Angoli rispetto al **lato base**: 0, 30, 45, 60, 90, 120, 135, 150, 180; tolleranza 5°. [V] [DrawSnapHelper.java L241-242](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawSnapHelper.java#L241-L242), [L340-372](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawSnapHelper.java#L340-L372), [DrawAction.java L99-100](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawAction.java#L99-L100)
- Il lato base è il lato precedente, oppure un lato scelto passandoci sopra con Ctrl o con clic destro. Aggancia anche a 90° rispetto ai nodi della via in disegno, a qualsiasi distanza. [V] [DrawAction.java L803-815](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawAction.java#L803-L815), [L425-440](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawAction.java#L425-L440), [Help/Action/Draw/AngleSnap](https://josm.openstreetmap.de/wiki/Help/Action/Draw/AngleSnap)
- Ctrl toglie l'aggancio alle vie esistenti; Shift toglie il collegamento automatico; Alt inizia una via nuova. [V] [Help/Action/Draw](https://josm.openstreetmap.de/wiki/Help/Action/Draw)

### 4.3 Plugin buildings_tools
File in `buildings_tools/src/org/openstreetmap/josm/plugins/buildings_tools/`: `DrawBuildingAction.java`, `Building.java`, `AngleSnap.java`, `ToolSettings.java`, `BuildingSizeDialog.java`, `AddressDialog.java`, `MergeAddrPointsAction.java`, `BuildingCircleAction.java`, `BuildingRectangleAction.java`. [V] [cartella](https://github.com/JOSM/josm-plugins/tree/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/src/org/openstreetmap/josm/plugins/buildings_tools)
- Tasto B; stati: nessuno, disegno, larghezza, angolo fisso. [V] [DrawBuildingAction.java L61-89](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/src/org/openstreetmap/josm/plugins/buildings_tools/DrawBuildingAction.java#L61-L89)
- Rettangolo: si traccia un lato, poi si clicca sul lato opposto. Da 1 a 3 clic. Larghezza fissa opzionale (negativa = dall'altra parte), passo di lunghezza, indirizzo con numero civico che avanza di 2, selezione automatica del nuovo edificio, modo "edifici grandi" con Shift, modo a 2 clic (diagonale) quando la via selezionata è già squadrata. [V] [wiki BuildingsTools](https://wiki.openstreetmap.org/wiki/JOSM/Plugins/BuildingsTools)
- `AngleSnap`: raccoglie le direzioni dei lati della via selezionata, ridotte modulo 90°. Con 2 nodi aggiunge anche la direzione + 45°. Aggancia la direzione del cursore se è entro 22,5° (π/8). [V] [AngleSnap.java L29-133](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/src/org/openstreetmap/josm/plugins/buildings_tools/AngleSnap.java#L29-L133)

### 4.4 Licenze
- JOSM core: "GNU General Public License v2 or later". I file dicono solo "License: GPL. For details, see LICENSE file". [V] [LICENSE L1-13](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/LICENSE#L1-L13), [OrthogonalizeAction.java L1](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L1). Compatibile con GPL-3.0-or-later. [I]
- Il LICENSE di JOSM avvisa che i plugin possono avere licenze diverse. [V] [LICENSE L19-20](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/LICENSE#L19-L20)
- buildings_tools: intestazione "License: GPL" e file LICENSE col testo GPL v2, senza la frase "or later". [V] [LICENSE](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/LICENSE), [AngleSnap.java L1](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/src/org/openstreetmap/josm/plugins/buildings_tools/AngleSnap.java#L1). La GPL v2 (sezione 9) dice che se il programma non indica la versione si può scegliere qualsiasi versione. [V] [LICENSE L237-248](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/LICENSE#L237-L248). Ma il testo allegato è v2: la situazione è ambigua. Meglio non copiare e reimplementare. [I]

---

## 5. iD (JavaScript/TypeScript)

### 5.1 File
- `modules/actions/orthogonalize.ts` (prima `.js`, migrato a TypeScript a luglio 2026). [V] [orthogonalize.ts](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts), [storia del file](https://github.com/openstreetmap/iD/commits/develop/modules/actions/orthogonalize.ts)
- `modules/geo/ortho.ts`: punteggio e test "si può squadrare?". [V] [ortho.ts](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/geo/ortho.ts)
- `modules/operations/orthogonalize.js`: l'operazione dell'interfaccia (tasto, anteprima, messaggi). [V] [operations/orthogonalize.js](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/operations/orthogonalize.js)
- `modules/actions/circularize.ts`: "rendi circolare". [V] [circularize.ts](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/circularize.ts)
- Tasti: Q = Square, O = Circularize. [V] [data/core.yaml L111-147](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/data/core.yaml#L111-L147)

### 5.2 Algoritmo di squadratura
Parametri: soglia 13° ("gradi entro l'angolo retto o piatto da correggere"), epsilon 1e-4, massimo 1000 iterazioni. Le soglie si confrontano come coseni: `lower = cos(90° - 13°)`, `upper = cos(13°)`. [V] [L15-21](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L15-L21)

Per ogni vertice si calcola `d` = prodotto scalare dei versori verso il vertice precedente e il successivo (cioè il coseno dell'angolo interno).

1. **Semplificazione**: i vertici con `|d| > upper` (angolo entro 13° da 180°, quasi allineati) escono dalla forma da squadrare. [V] [L79-98](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L79-L98)
2. **Quali angoli si correggono**: solo quelli con `|d| < lower`, cioè entro 13° da 90°. Gli altri angoli (per esempio 45° o 135°) restano dove sono. [V] [L170-197](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L170-L197)
3. **Spostamento** di ogni vertice, calcolato per tutti e poi applicato insieme: lungo la bisettrice `normalize(p + q)`, di `0,1 · d · 2 · min(|p|, |q|)`. Se l'angolo è acuto il vertice va verso la corda e l'angolo si apre; se è ottuso va in fuori e l'angolo si chiude. Gli estremi di una linea aperta e i nodi ripetuti non si muovono. [V] [L104-110](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L104-L110), [L170-197](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L170-L197)
4. **Punteggio**: somma su ogni vertice di `2 · min(|d - 1|, |d|, |d + 1|)`, contando solo i vertici vicini a 90° o a 180°. Si tiene la forma col punteggio migliore; ci si ferma sotto epsilon. [V] [ortho.ts L8-42](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/geo/ortho.ts#L8-L42), [orthogonalize.ts L104-119](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L104-L119)
5. **Vertici tolti al punto 1**: se non hanno significato (nessun tag, una sola via) vengono **cancellati**; altrimenti vengono proiettati sul lato più vicino della forma squadrata. [V] [L134-157](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L134-L157)
6. **Caso a 3 nodi** (triangolo o singolo angolo): si muove solo il vertice centrale. Si può squadrare **un solo angolo** selezionando quel vertice. [V] [L44-76](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L44-L76), [operations L34-46](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/operations/orthogonalize.js#L34-L46)
7. **Quando è disabilitata**: "not_squarish" se nessun angolo è vicino a 90° o 180°; "square_enough" se è già squadrata entro epsilon. [V] [orthogonalize.ts L221-248](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L221-L248), [ortho.ts L72-93](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/geo/ortho.ts#L72-L93), [core.yaml L160-165](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/data/core.yaml#L160-L165)
8. **Interfaccia**: anteprima della forma squadrata ("auxiliary geometry") e animazione con un parametro t da 0 a 1. [V] [operations L120-136](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/operations/orthogonalize.js#L120-L136), [orthogonalize.ts L24-26](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L24-L26), [L251](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L251)

iD lavora in coordinate proiettate sullo schermo ([V] [L56-60](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L56-L60)). Meridiana può lavorare direttamente in metri sul piano locale: le soglie sono adimensionali e lo spostamento è proporzionale ai lati, quindi non cambia nulla. [I] [L182-193](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L182-L193)

### 5.3 Origine e parentela
- L'idea (punteggio `2·min(|d-1|,|d|,|d+1|)`, passo 0,1 lungo la bisettrice, 1000 passi) viene da Potlatch 2, `Quadrilateralise.as`, licenza WTFPL. [V] [Quadrilateralise.as L1-110](https://github.com/systemed/potlatch2/blob/14f6fd88ee6b444adea5e0d0ddfcb2e3be52c262/net/systemeD/potlatch2/tools/Quadrilateralise.as#L1-L110), [LICENCE.txt](https://github.com/systemed/potlatch2/blob/14f6fd88ee6b444adea5e0d0ddfcb2e3be52c262/LICENCE.txt)
- QGIS ne ha una versione C++ (GPL-2.0-or-later), soglia 15°, senza semplificazione e con il "trucco" per i lati quasi allineati. [V] [qgsinternalgeometryengine.cpp L435-603](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/geometry/qgsinternalgeometryengine.cpp#L435-L603)

### 5.4 Rendi circolare (O)
Baricentro e raggio mediano; i nodi "chiave" (condivisi o con tag) vengono proiettati sul cerchio, gli altri distribuiti a passo costante; si aggiungono nodi per avere lati di circa 4 m, tra 12 e 32 vertici. [V] [circularize.ts L20-140](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/circularize.ts#L20-L140), [L205-222](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/circularize.ts#L205-L222). Utile per ostacoli tondi (canne fumarie, serbatoi). [I]

### 5.5 Licenza e porting
- iD è sotto **ISC**: uso, copia e modifica permessi, "provided that the above copyright notice and this permission notice appear in all copies". [V] [LICENSE.md](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/LICENSE.md)
- La ISC è compatibile con la GPL (elenco FSF). [I] (pagina FSF non raggiungibile oggi, errore 429): https://www.gnu.org/licenses/license-list.html#ISC
- **Il porting è possibile.** Obblighi: tenere "Copyright (c) iD Contributors" e il testo del permesso ISC nel file portato e nelle note di terze parti. [V] [LICENSE.md](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/LICENSE.md)

Bozza Python che ho scritto seguendo il codice di iD e provato su due contorni. Sotto c'è la versione compatta (anche questa eseguita); il file completo con la ricomposizione e la prova è C:\Users\utente\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\tests\squadra_sketch.py. Risultati della prova:
- rettangolo 12 x 8 m storto (angoli 86,3 / 180 / 94,0 / 85,1 / 94,6) → 90,0 / 180 / 90,0 / 90,0 / 90,0;
- pianta a L con smusso (131,4° e 132,1°) → angoli retti a 90,0 e smussi rimasti a circa 131,7°.

```python
# SPDX-License-Identifier: GPL-3.0-or-later AND ISC
# Derivato da iD: modules/actions/orthogonalize.ts e modules/geo/ortho.ts
# Copyright (c) iD Contributors. ISC License (testo completo in LICENSES/ISC.txt).
# Modificato per Meridiana il <data>: Python, coordinate in metri, vertici allineati
# proiettati invece che cancellati.
import math

def _norm(v):
    l = math.hypot(v[0], v[1])
    return (v[0] / l, v[1] / l) if l > 0 else (0.0, 0.0)

def _ndot(a, b, o):
    p = _norm((a[0] - o[0], a[1] - o[1])); q = _norm((b[0] - o[0], b[1] - o[1]))
    return p[0] * q[0] + p[1] * q[1]

def squadra(punti, chiuso=True, soglia_gradi=13.0, eps=1e-4, max_iter=1000):
    lower = math.cos(math.radians(90 - soglia_gradi))
    upper = math.cos(math.radians(soglia_gradi))
    n = len(punti)
    semplice, dritti = [], []
    for i, p in enumerate(punti):                      # 1. semplificazione
        d = abs(_ndot(punti[i - 1], punti[(i + 1) % n], p)) if (chiuso or 0 < i < n - 1) else 0.0
        (dritti if d > upper else semplice).append(i)
    pts = [list(punti[i]) for i in semplice]; m = len(pts)

    def moto(i):                                       # 2-3. spostamento
        if not chiuso and i in (0, m - 1):
            return (0.0, 0.0)
        a, o, b = pts[i - 1], pts[i], pts[(i + 1) % m]
        p = (a[0] - o[0], a[1] - o[1]); q = (b[0] - o[0], b[1] - o[1])
        scala = 2 * min(math.hypot(*p), math.hypot(*q))
        p, q = _norm(p), _norm(q); d = p[0] * q[0] + p[1] * q[1]
        if abs(d) < lower:
            v = _norm((p[0] + q[0], p[1] + q[1])); k = 0.1 * d * scala
            return (v[0] * k, v[1] * k)
        return (0.0, 0.0)

    def punteggio():                                   # 4. punteggio
        s = 0.0
        for i in (range(m) if chiuso else range(1, m - 1)):
            d = _ndot(pts[i - 1], pts[(i + 1) % m], pts[i]); a = abs(d)
            if a < eps: d = 0.0
            elif not (a < lower or a > upper): continue
            s += 2 * min(abs(d - 1), abs(d), abs(d + 1))
        return s

    migliore, best = [p[:] for p in pts], math.inf
    for _ in range(max_iter):
        mov = [moto(i) for i in range(m)]
        for i, (dx, dy) in enumerate(mov):
            pts[i][0] += dx; pts[i][1] += dy
        s = punteggio()
        if s < best: best, migliore = s, [p[:] for p in pts]
        if best < eps: break
    # 5. ricomporre: vertici semplificati da 'migliore', vertici 'dritti' proiettati sul lato più vicino
    return semplice, dritti, migliore, best
```

---

## 6. LibreCAD (C++)

### 6.1 File e comportamento
- `librecad/src/lib/actions/rs_snapper.cpp` e `.h` (non più in `lib/engine`). [V] [rs_snapper.cpp](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.cpp)
- Modi di snap: libero, griglia, estremi, punti medi, distanza dagli estremi, centri, intersezioni, su entità, angolo. Restrizioni: nessuna, orizzontale, verticale, ortogonale. [V] [rs_snapper.h L58-95](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.h#L58-L95)
- Scelta: calcola tutti i modi attivi e vince il più vicino (nessuna priorità per tipo). Se il migliore è più lontano del raggio di snap e "libero" è attivo, resta il punto libero. Poi applica la restrizione rispetto allo "zero relativo". [V] [rs_snapper.cpp L701-790](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.cpp#L701-L790)
- Raggio di cattura delle entità 32 px. [V] [rs_snapper.h L248](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.h#L248)
- Aggancio angolare (di solito tenendo Shift), a passi configurabili (1, 3, 5, 10, 15, 18, 22,5, 30, 45, 90 gradi; default 10°), assoluto o relativo; "soft snap" con sensibilità 3°, spento di default. [V] [rs_snapper.cpp L343-393](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.cpp#L343-L393), [L1485-1557](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.cpp#L1485-L1557), [changelog L1164-1178](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/ChangeLogs/Conditional_search_Properties_Visual_Snap_Relative_Assistant/README.md#L1164-L1178)

### 6.2 Novità 2026 molto vicine a Meridiana
- **Visual Snap**: punti guida con raggi orizzontali, verticali, a passi d'angolo e cerchi di distanza. Un punto si aggiunge con **Tab** oppure fermando il cursore sopra per un tempo (opzione: con Ctrl). Ctrl + sosta lo toglie; Shift+Esc toglie l'ultimo; Esc azzera. [V] [changelog L630-780](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/ChangeLogs/Conditional_search_Properties_Visual_Snap_Relative_Assistant/README.md#L630-L780). È l'equivalente dei lati e punti "acquisiti" di Meridiana. [I]
- **Relative Point Input Assistant**: riquadro vicino al cursore per distanza, angolo, offset X e Y; Tab e Shift+Tab tra i campi; D, A, X, S attivano i campi; T relativo/assoluto; Invio conferma; Esc annulla. [V] [changelog L1190-1290](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/ChangeLogs/Conditional_search_Properties_Visual_Snap_Relative_Assistant/README.md#L1190-L1290)

### 6.3 Licenza
- "LibreCAD ... under the terms of the GNU General Public License version 2 (GPLv2)"; "released as a whole under the GPLv2". Deriva da QCAD 2.0.5 GPLv2. [V] [LICENSE L1-30](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/LICENSE#L1-L30), [L82](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/LICENSE#L82)
- `rs_snapper.cpp`: "GNU General Public License version 2", senza "or later" = **GPL-2.0-only**. [V] [rs_snapper.cpp L8-12](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/rs_snapper.cpp#L8-L12)
- I file nuovi del Visual Snap dicono "version 2 ... or any later version". [V] [lc_visual_snap_manager.cpp L5-11](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/librecad/src/lib/actions/visual_snap/lc_visual_snap_manager.cpp#L5-L11). Però si appoggiano a `rs_snapper` (GPL-2.0-only) e il progetto nel complesso è GPLv2: non li copierei. [I]
- La GPL v2 permette le versioni successive solo se il programma lo dice ("any later version"). [V] [testo GPL v2, sezione 9](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/LICENSE#L237-L248). Quindi codice GPL-2.0-only non entra in un programma GPL-3.0. [I] (FAQ FSF, non raggiungibile oggi): https://www.gnu.org/licenses/gpl-faq.html#AllCompatibility

---

## 7. QCAD Community Edition (C++ e script ECMAScript)

- Classi in `src/snap/` (RSnapAuto, RSnapEnd, RSnapMiddle, RSnapIntersection, RSnapPerpendicular, RSnapTangential, RSnapGrid, RSnapOnEntity, RSnapReference, RSnapFree...) e restrizioni RRestrictOrthogonal, RRestrictHorizontal, RRestrictVertical, RRestrictAngleLength, RRestrictOff. Base in `src/core/RSnap.h`, `RSnapRestriction.h`. Comandi in `scripts/Snap/`. [V] [src/snap](https://github.com/qcad/qcad/tree/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap), [scripts/Snap](https://github.com/qcad/qcad/tree/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/scripts/Snap)
- **Snap automatico con priorità fissa**: intersezione, estremi, punti medi, centri, perpendicolare, tangente, punti di riferimento, griglia, su entità, libero. Il primo tipo che trova un punto entro il raggio vince. [V] [RSnapAuto.cpp L52-270](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap/RSnapAuto.cpp#L52-L270)
- Se il mouse si è già mosso durante il calcolo, salta gli snap costosi e ripiega su griglia o libero. [V] [RSnapAuto.cpp L105-125](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap/RSnapAuto.cpp#L105-L125)
- Raggio di default 10 px (moltiplicato per la densità dello schermo). [V] [RSettings.cpp L1620-1628](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/core/RSettings.cpp#L1620-L1628)
- **Restrizione angolo/lunghezza**: angolo a passi (ripetuti) da un angolo base e lunghezza a passi (ripetuti) da una lunghezza base. [V] [RRestrictAngleLength.cpp L22-71](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap/RRestrictAngleLength.cpp#L22-L71). Il passo di lunghezza è utile per file di moduli. [I]
- Tasti a due lettere: E,O ortogonale; E,L angolo/lunghezza; S,A snap automatico; R,L blocca lo zero relativo. [V] [RestrictOrthogonalInit.js L5](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/scripts/Snap/RestrictOrthogonal/RestrictOrthogonalInit.js#L5), [RestrictAngleLengthInit.js L5](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/scripts/Snap/RestrictAngleLength/RestrictAngleLengthInit.js#L5), [SnapAutoInit.js L5](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/scripts/Snap/SnapAuto/SnapAutoInit.js#L5), [LockRelativeZeroInit.js L5](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/scripts/Snap/LockRelativeZero/LockRelativeZeroInit.js#L5)
- **Licenza**: file "either version 3 of the License, or (at your option) any later version" = **GPL-3.0-or-later**, con un'eccezione opzionale per il linking. [V] [RSnapAuto.cpp L1-17](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap/RSnapAuto.cpp#L1-L17), [LICENSE.txt](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/LICENSE.txt), [gpl-3.0-exceptions.txt](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/gpl-3.0-exceptions.txt). Compatibile con Meridiana. [I]

---

## 8. Inkscape (C++)

### 8.1 File
`src/snap.cpp`, `src/snap.h` (SnapManager), `src/snapped-point.cpp` (confronto tra candidati), `src/snapper.h`, `src/object-snapper.cpp`, `src/line-snapper.cpp` (griglie e guide), `src/alignment-snapper.cpp`, `src/snap-preferences.cpp`, `src/ui/tools/tool-base.cpp` (ritardo dello snap). [V] [snapped-point.cpp](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/snapped-point.cpp), [snap.cpp](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/snap.cpp)

### 8.2 Scelta del candidato (`isOtherSnapBetter`)
[V] [snapped-point.cpp L344-432](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/snapped-point.cpp#L344-432)
- un punto agganciato batte uno non agganciato;
- tra più nodi sorgente pesa distanza dal puntatore e distanza di snap (peso 0,5); "solo il nodo più vicino al puntatore" porta il peso a 1;
- la semplice proiezione su una linea di vincolo ha priorità minima;
- vince il più vicino, ma un punto "completamente vincolato" (nodo, intersezione) batte uno "parzialmente vincolato" (un punto su una linea) anche se più lontano;
- a parità di posizione, un nodo batte un'intersezione.

### 8.3 Tolleranze e stabilità
- Tolleranze di default in pixel dello schermo (divise per lo zoom): oggetti 20, guide 20, griglia 10, allineamento 5, distribuzione 5. [V] [sp-namedview.cpp L296-310](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/object/sp-namedview.cpp#L296-310), [snap.cpp L762-767](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/snap.cpp#L762-767). Nota: le guide di allineamento hanno una tolleranza più piccola degli oggetti. [I]
- **Snap ritardato**: finché il mouse va veloce (oltre 0,02 px/ms) lo snap è sospeso; si aggancia quando rallenta o dopo un ritardo configurabile. [V] [tool-base.cpp L1561-1637](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/ui/tools/tool-base.cpp#L1561-1637), [inkscape-preferences.cpp L2774-2778](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/ui/dialog/inkscape-preferences.cpp#L2774-2778)
- Indicatore dello snap con persistenza configurabile; "Always snap to grids/guides". [V] [inkscape-preferences.cpp L2744-2797](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/ui/dialog/inkscape-preferences.cpp#L2744-2797)
- Aggancio angolare a passi di π/n; la preferenza di default è 12 passi per 180° (15°). [V] [snap.cpp L402-437](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/snap.cpp#L402-437), [inkscape-preferences.cpp L2824-2829](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/ui/dialog/inkscape-preferences.cpp#L2824-2829)

### 8.4 Allineamento e distribuzione (dalla 1.2)
Guide temporanee orizzontali e verticali quando un oggetto è allineato a punti di altri oggetti; distribuzione a passo uguale; il tasto % attiva o spegne lo snap; modo "Simple" e "Advanced"; impostazioni globali e non più nel documento. Lavoro GSoC di Parth Pant. [V] [Release notes 1.2](https://wiki.inkscape.org/wiki/Release_notes/1.2), [alignment-snapper.cpp L1-10](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/alignment-snapper.cpp#L1-10)

### 8.5 Licenza
`SPDX-License-Identifier: GPL-2.0-or-later` in tutti i file letti. Il COPYING ricorda la catena "LGPL-2.1-or-later -> GPL-2.0-or-later -> GPL-3.0-or-later" e che i binari sono GPL-3.0-or-later. [V] [COPYING L4-31](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/COPYING#L4-31), [snapped-point.cpp L1](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/snapped-point.cpp#L1)

---

## 9. Blender (C++)

- File: `source/blender/editors/transform/transform_snap.cc`, `transform_snap_object.cc`, `transform_snap_object_mesh.cc`, `transform_snap.hh`. [V] [transform_snap.cc](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap.cc)
- **Snap Target**: Increment, Grid, Origin, Vertex, Edge, Face, Volume, Edge Center, Edge Perpendicular, Face Center; per elementi singoli Face Project e Face Nearest. Più modi insieme con Shift+clic. [V] [manuale Snapping](https://docs.blender.org/manual/en/latest/editors/3dview/controls/snapping.html), [sorgente del manuale](https://projects.blender.org/blender/blender-manual/src/branch/main/manual/editors/3dview/controls/snapping.rst)
- **Snap Base**: Closest (il punto della selezione più vicino al bersaglio), Center (punto pivot), Median (media), Active (elemento attivo). [V] [manuale Snapping](https://docs.blender.org/manual/en/latest/editors/3dview/controls/snapping.html)
- **Ctrl** tenuto inverte lo snap durante la trasformazione; Shift dà il passo fine (precisione); B ridefinisce il punto base; A marca più bersagli e la selezione va alla loro media. [V] [modal map](https://docs.blender.org/manual/en/latest/modeling/transform/modal_map.html), [transform_snap.cc L118-148](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap.cc#L118-L148)
- **Assi**: X, Y, Z vincolano; Shift+asse vincola al piano; premere di nuovo lo stesso tasto cambia orientamento (locale o globale); la terza volta toglie il vincolo. [V] [modal map](https://docs.blender.org/manual/en/latest/modeling/transform/modal_map.html)
- **Incremental snapping**: passi della griglia a partire dalla posizione iniziale; "Absolute Increment Snap" usa invece la griglia assoluta. [V] [manuale Snapping](https://docs.blender.org/manual/en/latest/editors/3dview/controls/snapping.html)
- Soglia di snap 30 px. [V] [transform_snap.hh L11](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap.hh#L11)
- **Zone sul lato**: quando il cursore è su un lato, conta anche la posizione lungo il lato. Con lato, estremo e medio attivi: tra il 40% e il 60% della lunghezza si propone il punto medio, fuori da questa fascia l'estremo più vicino. Il candidato vale solo se sta anche entro la soglia in pixel; altrimenti resta il punto sul lato. Con solo lato ed estremo le fasce sono a un terzo e due terzi. [V] [transform_snap_object.cc L225-300](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap_object.cc#L225-L300). Evita lo sfarfallio tra estremo e punto medio sui lati corti. [I]
- La griglia ignora la distanza massima, "per evitare salti indesiderati". [V] [transform_snap_object.cc L1036-1044](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap_object.cc#L1036-L1044)
- **Licenza**: `SPDX-License-Identifier: GPL-2.0-or-later`. [V] [transform_snap.cc L1-2](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap.cc#L1-L2)

---

## 10. SolveSpace (breve)

- Risolutore di vincoli geometrici: equazioni simboliche, linearizzazione, metodo di Newton modificato (Eigen SparseQR). [V] [system.cpp L1-12](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/src/system.cpp#L1-L12)
- Vincoli automatici: una linea quasi orizzontale o verticale (rapporto 0,02, circa 1,1°) riceve il vincolo H o V al clic; il rettangolo nasce con i vincoli H e V. [V] [graphicswin.cpp L1455-1479](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/src/graphicswin.cpp#L1455-L1479), [mouse.cpp L1037](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/src/mouse.cpp#L1037), [L1271-1275](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/src/mouse.cpp#L1271-L1275)
- Licenza: "GPL v3 or later". [V] [README L354-356](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/README.md#L354-L356)
- Esiste il pacchetto Python `python-solvespace` 3.0.8, GPLv3+. [V] [PyPI](https://pypi.org/project/python-solvespace/). Il pacchetto `slvs` 3.3 dichiara "MIT" nei classificatori, che non torna con la licenza di SolveSpace: da chiarire prima di usarlo. [V] [PyPI slvs](https://pypi.org/project/slvs/), interpretazione [I]
- Per Meridiana serve più avanti, se si vogliono vincoli che restano (lati paralleli che restano paralleli quando si sposta un vertice). Per lo snapping non serve. [I] [system.cpp](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/src/system.cpp#L1-L12)

---

## 11. Confronto rapido

| Programma | Come sceglie il candidato | Tolleranza default | Input numerico | Licenza | Copiabile in GPL-3.0+ |
|---|---|---|---|---|---|
| FreeCAD Draft | il più vicino; Near perde se altro entro raggio | 8 px | campi X/Y/Z, L/A, R/G | LGPL-2.1-or-later | sì, con note [I] |
| QGIS | per tipo, poi distanza; vincoli morbidi 15 px e 10° | 12 px | d/a/x/y, floater, virgola tollerata | GPL-2.0-or-later | sì, con note [I] |
| JOSM core | angoli rispetto al lato base, 5° | n.d. | n.d. | GPL-2.0-or-later | sì, con note [I] |
| buildings_tools | direzioni modulo 90°, 22,5° | n.d. | dialogo misure | "GPL" testo v2 | dubbio: reimplementare [I] |
| iD | squadratura iterativa 13° | n.d. | n.d. | ISC | sì, con nota ISC [I] |
| LibreCAD | il più vicino | 32 px cattura | assistente relativo, Tab | GPL-2.0-only | **no** [I] |
| QCAD CE | priorità fissa per tipo | 10 px | n.d. | GPL-3.0-or-later | sì, con note [I] |
| Inkscape | vincolato pieno prima, poi distanza | 20 px oggetti, 5 px allineamento | n.d. | GPL-2.0-or-later | sì, con note [I] |
| Blender | per elemento, zone sul lato | 30 px | n.d. | GPL-2.0-or-later | sì, con note [I] |
| SolveSpace | vincoli risolti | n.d. | n.d. | GPL-3.0-or-later | sì [I] |

Fonti delle righe: sezioni 2-10, dove ogni dato ha il suo link. "n.d." = non letto o non verificato in questa ricerca.

---

## 12. Raccomandazioni per Meridiana

Dalla descrizione ricevuta, lo snapper attuale di Meridiana copre già vertici, punti medi, primo punto, intersezioni guida per guida e guida per lato, estensioni, perpendicolari, parallele, lati acquisiti, polare a 15°, punto più vicino sul lato, tolleranza in pixel, Ctrl per il disegno libero, lunghezza digitata con Invio, etichetta vicino al cursore. Le proposte sotto aggiungono ciò che manca. Tutte sono [I] (mie proposte), con il riferimento al programma che le fa già.

### 12.1 Priorità alta

**A. Squadratura "Q" (porting dell'algoritmo di iD).**
- Porta `orthogonalize.ts` e `ortho.ts` in un modulo Python (`geometria/squadra.py`), con la bozza della sezione 5.5 come base.
- Default 13° come iD ([L15-21](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L15-L21)); impostabile tra 5° e 20° (QGIS usa 15°: [qgsgeometry.h L1470](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/geometry/qgsgeometry.h#L1470)).
- Lavorare in metri sul piano locale.
- Vertici quasi allineati: **proiettarli** sul lato, non cancellarli (iD li cancella: [L134-157](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L134-L157)). Cancellazione solo su richiesta.
- Q con un contorno selezionato: anteprima tratteggiata mentre Q è premuto, applicazione al rilascio, un solo passo di annulla (iD ha anteprima e transizione: [operations L120-136](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/operations/orthogonalize.js#L120-L136)).
- Q con un vertice selezionato: squadra solo quell'angolo (iD lo fa: [operations L34-46](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/operations/orthogonalize.js#L34-L46)).
- Messaggi in barra di stato: "non abbastanza squadrato" e "già squadrato" (gli stati di iD: [L221-248](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/orthogonalize.ts#L221-L248)).
- Variante Shift+Q "tieni fisso questo lato": il lato sotto il cursore (o il più lungo) dà la direzione e non si muove; algoritmo deterministico tipo JOSM (sezione 4.1, [L312-475](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/OrthogonalizeAction.java#L312-L475)). JOSM è GPL-2.0-or-later: si può portare con le note, oppure riscrivere dai 5 passi descritti.

**B. Input numerico "lunghezza;angolo".**
- Formato `5,20;90` oppure `5.20;90`: separatore `;` perché la virgola è il decimale italiano. SketchUp fa lo stesso: dove la virgola è decimale il separatore è il punto e virgola. [I] (forum, non documentazione ufficiale) https://forums.sketchup.com/t/typing-measurements/39987
- Leggere sia la virgola sia il punto come decimale, come fa QGIS ([dock L1083-1138](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1083-L1138)). Eventualmente piccole espressioni (`3,5+0,2`) con un parser sicuro, mai `eval`.
- La prima cifra digitata apre la casella vicino al cursore (come ora). Tab passa da lunghezza ad angolo, Shift+Tab torna indietro (LibreCAD: [changelog L1250-1262](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/ChangeLogs/Conditional_search_Properties_Visual_Snap_Relative_Assistant/README.md#L1250-L1262)); Invio conferma (FreeCAD passa al campo successivo con Invio: [DraftGui.py L1428-1434](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1428-L1434)); Esc annulla.
- Angolo: di default la **svolta** rispetto al lato precedente (come JOSM, [DrawSnapHelper.java L340-372](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawSnapHelper.java#L340-L372), e la modalità relativa di QGIS); un tasto (Shift+A, come QGIS: [manuale L2063-2087](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2063-L2087)) passa all'azimut assoluto. L'etichetta mostra quale dei due è attivo.
- Al primo tasto digitato la direzione si congela: il mouse non la cambia più finché si conferma o si annulla (come il "Mouse delay" di FreeCAD, [DraftGui.py L1636-1653](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L1636-L1653), ma senza tempo fisso).
- Un valore digitato diventa un **blocco duro**: lunghezza sola = cerchio attorno all'ultimo punto, e il cursore sceglie la direzione; lunghezza e angolo = punto fisso (QGIS, sezione 3.3, [qgscadutils.cpp L415-486](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L415-L486)).

**C. Blocchi duri e morbidi, come QGIS.**
- Morbidi: angoli polari, allineamenti a vertici acquisiti, estensioni, parallele e perpendicolari automatiche. Scattano solo entro la tolleranza e si disegnano tratteggiati ([qgscadutils.cpp L86-206](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L86-L206)).
- Duri: Shift tenuto, X, Y, P, valori digitati. Restano finché si clicca; poi si liberano, salvo un "blocco continuo" (QGIS: [dock L963-1010](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L963-L1010)).
- Con un blocco duro attivo, continuare a cercare l'intersezione con il lato sotto il cursore (QGIS "magnetizza" retta per lato: [qgscadutils.cpp L283-307](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/qgscadutils.cpp#L283-L307)).
- Vincoli incompatibili: punto non valido e avviso, invece di un punto sbagliato (QGIS: [dock L1575-1582](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1575-L1582)).

**D. Shift = blocca la direzione corrente.**
- Tenendo Shift si congela la direzione attiva in quel momento (polare, parallela, perpendicolare, estensione, oppure quella libera del mouse). Al rilascio torna tutto normale. JOSM fa lo stesso tenendo premuto A ([DrawAction.java L357-376](https://github.com/JOSM/josm/blob/103fd7edce2002679c41bc39e09f85c54c16a5b9/src/org/openstreetmap/josm/actions/mapmode/DrawAction.java#L357-L376)); FreeCAD con Shift sceglie un asse e lo tiene finché Shift è premuto ([gui_snapper.py L1350-1430](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1350-L1430)).
- Attenzione: con Shift premuto le cifre della tastiera italiana diventano simboli (Shift+1 dà "!"). Quindi servono anche le altre due strade: la direzione si congela al primo tasto numerico (punto B) e un tasto a levetta, come L di FreeCAD, che blocca o sblocca la direzione senza tenerlo premuto. [I] [layout KBDIT](https://kbdlayout.info/kbdit)

**E. Tab per ciclare i candidati.**
- Se ci sono più candidati entro la tolleranza (per esempio vertice, intersezione, punto medio vicini), Tab passa al successivo e Shift+Tab al precedente. L'indice si azzera quando il cursore si sposta oltre qualche pixel.
- FreeCAD fa una cosa simile col tasto accento grave, `` ` `` ([DraftGui.py L72-84](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/DraftGui.py#L72-L84)), ma sulla tastiera italiana l'accento grave non ha un tasto. [V] [layout KBDIT](https://kbdlayout.info/kbdit). Quindi Tab è la scelta giusta per Meridiana. [I]
- Tab ha due ruoli senza conflitto: con la casella numerica aperta cambia campo; senza casella cicla i candidati.

**F. Isteresi contro lo sfarfallio.** Nessuno dei programmi letti ha una vera isteresi spaziale; ci sono soluzioni vicine:
- FreeCAD tiene l'asse scelto finché Shift è premuto (sezione 2.4, [L1350-1430](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L1350-L1430));
- Inkscape sospende lo snap mentre il mouse va veloce (sezione 8.3, [tool-base.cpp L1561-1637](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/src/ui/tools/tool-base.cpp#L1561-1637));
- QCAD salta gli snap costosi se il mouse si è già mosso (sezione 7, [RSnapAuto.cpp L105-125](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap/RSnapAuto.cpp#L105-L125));
- Blender divide il lato in zone per estremo e medio, e non limita la distanza della griglia per evitare salti (sezione 9, [transform_snap_object.cc L225-300](https://github.com/blender/blender/blob/0506bcdae0db9f6f8a8132242bb3fcad84a92194/source/blender/editors/transform/transform_snap_object.cc#L225-L300)).

Proposta per Meridiana:
- il candidato attuale resta finché il cursore sta entro 1,5 volte la tolleranza;
- lo sostituisce solo un candidato di priorità più alta entro la tolleranza normale, oppure uno della stessa priorità più vicino di almeno 3 px;
- per le direzioni (polare, parallela, perpendicolare): si entra a 1 volta la tolleranza e si esce a 1,5 volte;
- facoltativo, come Inkscape: se il mouse va molto veloce, calcolare solo vertici e lati e rimandare il resto.

### 12.2 Priorità media

**G. Rettangolo da 3 clic** (tasto da decidere, per esempio R).
- Clic 1 e 2: primo lato, con tutti gli snap e la lunghezza digitabile.
- Terzo punto: larghezza come distanza dalla retta del primo lato (modo "proiettato" di QGIS); il lato dipende da dove sta il cursore (QGIS: [manuale L1894-1902](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L1894-L1902), [qgsquadrilateral.cpp L38-100](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/core/geometry/qgsquadrilateral.cpp#L38-L100)); larghezza digitabile.
- Variante a 2 clic sulla diagonale quando l'orientamento è già noto: lato di una falda o di un edificio selezionato (modo a 2 clic di buildings_tools: [wiki](https://wiki.openstreetmap.org/wiki/JOSM/Plugins/BuildingsTools)).
- Orientamento agganciato alle direzioni degli edifici vicini, modulo 90° (AngleSnap di buildings_tools, [L29-133](https://github.com/JOSM/josm-plugins/blob/ef94f68996940ed2e9e800984069fac32b723549/buildings_tools/src/org/openstreetmap/josm/plugins/buildings_tools/AngleSnap.java#L29-L133); finestra più stretta di 22,5°, per esempio 5°).

**H. Tasti X e Y.** X blocca sull'asse est-ovest, Y su nord-sud; premere di nuovo toglie il blocco (FreeCAD: [Draft_Constrain.md](https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Draft_Constrain.md)). Con un "lato di riferimento" scelto (clic destro sopra un lato, come JOSM: [AngleSnap help](https://josm.openstreetmap.de/wiki/Help/Action/Draw/AngleSnap); JOSM accetta anche Ctrl, che però in Meridiana è già il disegno libero) X e Y diventano "lungo il lato" e "perpendicolare al lato". Utile sulle falde.

**I. Passo polare variabile.** N e Shift+N cambiano il passo: 5°, 15°, 30°, 45°, 90° (QGIS: [dock L172](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L172), [L2207-2227](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L2207-L2227)). Il passo attivo compare nell'etichetta.

**J. Punto di riferimento temporaneo** (FreeCAD "hold point", che lì usa Q: [L920-969](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/src/Mod/Draft/draftguitools/gui_snapper.py#L920-L969)). In Meridiana Q va alla squadratura, quindi un altro tasto, per esempio H. Il punto dà assi X e Y e il punto medio tra due punti fissati (FreeCAD); oppure si fissa fermando il cursore su un vertice per un attimo (LibreCAD Visual Snap: [changelog L739-745](https://github.com/LibreCAD/LibreCAD/blob/d06eba4d4b361c8ae4a0c1e2c1ee2e8db3415622/ChangeLogs/Conditional_search_Properties_Visual_Snap_Relative_Assistant/README.md#L739-L745)).

### 12.3 Priorità bassa
- **Tracing** (QGIS T: [manuale L320-385](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L320-L385)): per una falda che condivide lati col contorno dell'edificio, percorrere il contorno tra due vertici cliccati scegliendo il verso più corto. Con pochi poligoni basta camminare sull'anello, senza grafo e Dijkstra.
- **Modo costruzione** (QGIS C: [manuale L2199-2267](https://github.com/qgis/QGIS-Documentation/blob/0eb963b4ebc19ad043401aca4e05c920e0156d7c/docs/user_manual/working_with_vector/editing_geometry_attributes.rst#L2199-L2267)): clic che creano solo riferimenti, per esempio per misurare distanze da un camino.
- **Passo di lunghezza** (QCAD: [RRestrictAngleLength.cpp L22-71](https://github.com/qcad/qcad/blob/f0b35cb4ff79613693bdc0c0bcbf723f445f71ac/src/snap/RRestrictAngleLength.cpp#L22-L71); buildings_tools): lunghezze a multipli di un passo, per esempio il passo dei moduli.
- **Rendi circolare** (iD O: [circularize.ts](https://github.com/openstreetmap/iD/blob/1f6118db61b86dd3a77bc8b39bd370842777cc3e/modules/actions/circularize.ts#L20-L140)) per ostacoli tondi.
- **Vincoli persistenti** (SolveSpace: [graphicswin.cpp L1455-1479](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/src/graphicswin.cpp#L1455-L1479)) solo se in futuro servono forme parametriche.

### 12.4 Mappa dei tasti proposta

| Tasto | Azione | Ispirazione |
|---|---|---|
| Ctrl tenuto | disegno libero (già presente) | Blender (inverte lo snap), JOSM |
| Shift tenuto | blocca la direzione corrente | JOSM (A tenuto), FreeCAD |
| L | blocca o sblocca la direzione a levetta | FreeCAD (L) |
| Tab / Shift+Tab | candidato successivo e precedente; tra i campi se la casella è aperta | FreeCAD (accento grave), LibreCAD |
| cifre | apre la casella lunghezza;angolo | Meridiana, FreeCAD |
| Shift+A | angolo relativo o assoluto | QGIS |
| X, Y | blocco sugli assi o sul lato di riferimento | FreeCAD, QGIS |
| P | perpendicolare, parallelo, spento (clic sul lato di riferimento) | QGIS |
| N, Shift+N | passo polare | QGIS |
| Q | squadra il contorno o l'angolo selezionato | iD, JOSM |
| Shift+Q | squadra tenendo fisso il lato scelto | JOSM (direzione fissata) |
| H | punto di riferimento temporaneo | FreeCAD (Q) |
| Esc | annulla la casella o libera i blocchi | QGIS |
| Backspace | toglie l'ultimo vertice | QGIS |

Fonti della colonna "Ispirazione": sezioni 2-10, dove ogni comportamento ha il suo link.

Attenzione in PySide6: se Ctrl+lettera o lettere singole sono anche scorciatoie di QAction, intercettare `QEvent.ShortcutOverride` nel widget della vista, come QGIS (sezione 3.5, [dock L1942-1962](https://github.com/qgis/QGIS/blob/28c25b31bec860fc24d6f88a65b36d26a5de3339/src/gui/qgsadvanceddigitizingdockwidget.cpp#L1942-L1962)). [I]

### 12.5 Codice: portare o riscrivere

| Fonte | Licenza | Decisione |
|---|---|---|
| iD orthogonalize | ISC | **portare** l'algoritmo; nota ISC nel file e in LICENSES/ISC.txt |
| Potlatch 2 Quadrilateralise | WTFPL | non serve: la versione iD è migliore |
| JOSM OrthogonalizeAction | GPL-2.0-or-later | portare o riscrivere la variante "lato fisso"; tenere il copyright JOSM |
| QGIS qgscadutils, orthogonalize | GPL-2.0-or-later | riscrivere dal comportamento; se si traduce un pezzo, tenere il copyright (2017 Martin Dobias) |
| FreeCAD gui_snapper.py | LGPL-2.1-or-later | riscrivere le idee (Near, hold point, mouse delay); codice legato a Coin3D e OCC |
| QCAD RSnapAuto | GPL-3.0-or-later | riscrivere: la logica è un elenco di priorità |
| Inkscape snapped-point | GPL-2.0-or-later | riscrivere le regole della sezione 8.2 se servono |
| Blender transform_snap | GPL-2.0-or-later | riscrivere le zone sul lato se servono |
| buildings_tools | "GPL", testo v2, versione non dichiarata | solo riscrivere |
| LibreCAD rs_snapper | GPL-2.0-only | **non copiare**; solo idee dalla documentazione |

Regole pratiche per il codice portato: [I], salvo dove indicato.
1. In testa al file: riga SPDX (per iD `GPL-3.0-or-later AND ISC`), copyright originale, link al file e al commit di origine.
2. Una nota di modifica con la data: la GPL v3 lo chiede ("prominent notices stating that you modified it, and giving a relevant date"). [V] [GPL v3 sezione 5a](https://github.com/solvespace/solvespace/blob/30e1c3ac0beb77fe3e098315b1bb662840ddc99a/COPYING.txt#L213-L222)
3. Testi completi delle licenze in una cartella `LICENSES/` e un file di note per le terze parti.
4. Codice da progetti GPL-2.0-or-later o LGPL-2.1-or-later: si distribuisce sotto GPL-3.0-or-later e si tengono intatti i loro avvisi. [V] per la LGPL [LICENSE FreeCAD L211-217](https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/LICENSE#L211-L217) e [catena Inkscape](https://gitlab.com/inkscape/inkscape/-/blob/e3270ca91ce4b7d3bad1c7560fb8a7e7063b42a0/COPYING#L27-L31); [I] per il resto.

---

## 13. Cosa non ho potuto verificare
- Il wiki di FreeCAD (wiki.freecad.org) blocca i lettori automatici. Ho letto la copia in git, ferma al 15/01/2025 e in un punto superata dal codice (regola di Near).
- Le pagine FSF su compatibilità (gnu.org) rispondevano "429 Too Many Requests". Le conclusioni sulla compatibilità sono quindi [I], appoggiate ai testi delle licenze che ho letto.
- Il limite di ricerche web della sessione si è esaurito. Non ho controllato la guida ufficiale di SketchUp (per il `;` ho solo il forum).
- Il manuale di Blender l'ho letto dal sorgente su projects.blender.org (ramo main, 21/10/2026); il server poi ha bloccato i download e il sorgente C++ l'ho confrontato col mirror GitHub.
- La bozza di squadratura è provata solo su due contorni di esempio. Prima di usarla servono test su contorni reali, anche concavi e con buchi.
