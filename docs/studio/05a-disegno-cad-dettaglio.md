# UX del disegno di precisione: stato dell'arte e regole per Meridiana

Ricerca del 21/10/2026. [V] = letto in fonte ufficiale (help, documentazione o codice del produttore); [I] = fonte secondaria o mia deduzione. Codici delle fonti, con URL e data, in coda a ogni sezione.

## 1. AutoCAD 2026

| Variabile | Default | Note | Fonte |
|---|---|---|---|
| APERTURE | 10 | cattura snap, 1-50; DIP sui 4K (pixel = DIP·DPI/96), pixel a 96 DPI | [V] A1, A2 |
| PICKBOX | 3 | selezione, DIP | [V] A3 |
| AUTOSNAP | 63 | 1 marker, 2 tooltip, 4 magnete, 8 polare, 16 tracking, 32 tooltip | [V] A4 |
| AUTOSNAPSIZE | non trovata | la scheda Disegno non lega variabili alla dimensione del marker; ActiveX AutoSnapMarkerSize 1-20 px | [V] A2, A5 |
| OSMODE | 4133 | estremo, centro, intersezione, estensione | [V] A6 |
| OSNAPCOORD | 2 | coordinate digitate battono gli snap | [V] A7 |
| POLARANG / POLARADDANG | 90 / "" | incrementi 90, 45, 30, 22.5, 18, 15, 10, 5; fino a 10 angoli assoluti aggiuntivi | [V] A8 |
| POLARMODE | 0 | bit 1 relativo all'ultimo segmento, 2 tracking polare, 4 angoli aggiuntivi, 8 acquisizione con Shift | [V] A9 |
| TRACKPATH | 0 | guide a tutto schermo | [V] A10 |
| DYNMODE, DYNPROMPT, DYNPICOORDS, DYNPIFORMAT | 3, 1, 0, 0 | input dinamico attivo, relativo, polare | [V] A11 |

- Marker per tipo (schermata ufficiale): quadrato estremo, triangolo medio, cerchio centro, X intersezione, rombo quadrante, squadretta perpendicolare, clessidra vicino, «//» parallelo, puntini estensione [V] A12; magnete e tooltip; colore dalla finestra Colori, default non trovato [V] A2.
- Tab scorre i candidati; vince il più vicino al centro del cursore; Shift+tasto destro = menu snap per un punto; FROM = base + offset; «tt» = tracking temporaneo [V] A13, A14.
- Tracking: «pause over the point» per acquisire, nuova sosta per rilasciare, «+» sul punto, guide 0/90/180/270°; Shift evita l'acquisizione [V] A12, A14. Durata della sosta e numero massimo di punti: non trovati.
- Polare relativo all'UCS o all'ultimo segmento [V] A15; polare + Intersection dà l'incrocio guida/oggetto [V] A16; «<30» blocca l'angolo, ma coordinate e snap prevalgono, e l'orto è ignorato se si digita o si aggancia [V] A17.
- F3 snap, F8 orto, F10 polare (F8 e F10 si escludono), F11 tracking, F12 input dinamico «con Tab tra i campi» [V] A18; di default sono attivi snap, polare, tracking e input dinamico, l'orto è spento [V] A22. Override tenuti: Shift = orto invertito, Shift+A snap, Shift+D o Shift+L disattivano snap e tracking, Shift+Q tracking, Shift+X polare, Shift+E/M/C forza estremo/medio/centro [V] A19.
- Input dinamico: dal secondo punto polari relative senza «@»; «#» assolute, «@» relative se il formato è assoluto, «*» WCS; lunghezza, Tab, angolo, Invio; dopo Tab il campo ha un lucchetto e vincola il cursore; freccia su = valori recenti [V] A20. LINE: «Undo» toglie l'ultimo segmento [V] A21.

Fonti (AC = https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/, senza data, consultato 21/10/2026): A1 AC GUID-2AA8CF8E-267F-4BD6-80CD-0E7C48B8A9F1.htm; A2 AC GUID-33A0F8E8-9981-4111-AD73-128B20D7975C.htm; A3 AC GUID-363698CF-C3DC-4770-81EF-CB09D86B3D3A.htm; A4 AC GUID-BE7947EB-2A08-4406-A169-4C5E125B1F4D.htm; A5 https://help.autodesk.com/cloudhelp/2017/ENU/AutoCAD-ActiveX/files/GUID-13574F50-ED66-4842-9CF1-841D8ABA798E.htm; A6 AC GUID-DD9B3216-A533-4D47-95D8-7585F738FD75.htm; A7 AC GUID-94994960-5E62-4044-BEF7-9CF91667F641.htm; A8 AC GUID-0CF67F9E-F953-43D6-9227-0D56E0E693ED.htm e GUID-73162BAB-C98D-4159-A653-E4C7D4CB38C3.htm; A9 AC GUID-D91628CC-9975-4DBF-8D02-10B23A6F3ED5.htm; A10 AC GUID-6BF0703C-28B2-4591-8337-34B8C20443F2.htm; A11 AC GUID-1ED138FF-2679-45C4-9C2C-332A821C9D12.htm, GUID-FA6A4CC1-DF9D-452C-93EA-48FFD0E08E1C.htm, GUID-87D649DF-8474-4F55-806E-604906030B36.htm, GUID-03D36D36-D734-43C3-BA4D-EA68C573F73C.htm; A12 AC GUID-50383F73-4F23-4F70-B4FC-52D5748D80AF.htm; A13 AC GUID-8F5E5431-9EFB-414E-BC6D-2C65EFB2DAC3.htm, GUID-76B81C1A-373E-4BCD-975A-789FB36C89FE.htm, GUID-0EB8FEA1-4C14-40C6-8254-DB6693DB481C.htm; A14 AC GUID-665DC37F-8C3E-414A-9369-72A13C0BE07A.htm; A15 AC GUID-D7CBB7B0-9140-4C53-88EF-08EAA09FA9D7.htm; A16 AC GUID-7EC3C63D-EA4E-4E65-A676-C3A3627E3F19.htm; A17 AC GUID-92BDE481-49D0-4AED-A6C5-0B78051EAE99.htm, GUID-C3B5D7B3-8057-4D8B-A3A2-0F5F0778BF37.htm; A18 AC GUID-ACAA0279-047D-458E-889F-60BBFDD40489.htm; A19 https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-B4AC255C-DF3E-44BB-9235-6E91D53CBA90.htm; A20 AC GUID-3EBD4C17-F0A5-49FA-B131-4AABE2E727DB.htm, GUID-AE225073-2ECD-41CC-9B8A-61743E8CFBA9.htm, GUID-A265C30C-CFD8-405D-BEE2-257B379475E2.htm; A21 AC GUID-E8C1190C-A26C-484C-ADDD-DDF81666F69F.htm; A22 pulsanti di stato AC GUID-440F891E-E698-4A99-9DDF-AC4F9C20AD76.htm (orto), GUID-7422CD82-2079-4CDC-AE6F-854DF2D07188.htm (polare), GUID-0E9FA54A-5A75-49BD-88BC-600975585D99.htm (tracking), GUID-258AA5A6-39B2-4CFC-B4ED-C5F0DA3D2EE8.htm (snap), GUID-C5381B8D-FAE1-437D-BC08-6D279073A61C.htm (input dinamico).

## 2. SketchUp

- Inferenze di punto (icone dell'help): estremo punto verde, medio ciano, intersezione X rossa, su spigolo quadrato rosso, su faccia rombo blu, centro punto blu, con ScreenTip; magenta dentro gruppi e componenti [V] S1, S2. Lineari: assi rosso, verde, blu; From Point tratteggiato col colore dell'asse; parallelo e perpendicolare magenta; Extend Edge; Tangent at Vertex [V] S1.
- Risveglio: sostando su un punto, SketchUp dà priorità all'allineamento con quel punto [V] S1.
- Shift blocca la direzione attiva (anche Through Point); frecce → rosso, ← verde, ↑ blu, ↓ parallelo/perpendicolare; il blocco tiene la direzione mentre si punta geometria altrove [V] S1. Alt (Cmd su Mac) nel Line tool cicla: tutte le inferenze, nessuna lineare, solo parallelo/perpendicolare [V] S1.
- Measurements box: si digita e Invio, ripetibile finché non si inizia altro [V] S1; «non cliccare nel box» [I] S5. [x,y,z] assolute, <x,y,z> relative [V] S1. Rettangolo «8',20'», parziali «3',» o «,3'», negativi invertono [V] S3. Serie «3x» esterne, «3/» interne; suffissi mm, cm, m [V] S4. Con virgola decimale il separatore è «;» [I] S6.
- Perché è intuitivo [I]: niente modalità da impostare; inferenze sempre attive ma «svegliate» dall'utente; numeri digitati senza puntare un campo e correggibili dopo; colore = direzione; un tasto per bloccare. È l'idea di Bier e Stone (R2).

Fonti (SU = https://help.sketchup.com/en/): S1 SU sketchup/introducing-drawing-basics-and-concepts (agg. 29/09/2026); S2 SU sketchup/tips-and-tricks (29/09/2026); S3 SU sketchup/drawing-basic-shapes (29/09/2026); S4 SU using-measurements-box (29/09/2026); S5 https://forums.sketchup.com/t/how-to-enter-values-into-measurements-box/13620 (28/07/2015); S6 https://forums.sketchup.com/t/unable-to-enter-exact-dimensions-when-creating-a-rectangle-shape/73061 (27/07/2018).

## 3. Onshape e Fusion

| | Onshape | Fusion |
|---|---|---|
| Vincoli | coincidente, concentrico, parallelo, tangente, orizzontale, verticale, perpendicolare, uguale, punto medio, normale, pierce, simmetrico, fisso, curvatura [V] O1 | gli stessi senza normale e pierce, più collineare [V] F1 |
| Inferenza | H/V verso origine ed entità; medio, parallelo, coincidente si «svegliano» avvicinando il cursore [V] O2 | agganciando un punto si aggiungono i vincoli logici [V] F2 |
| Sopprimere | Shift trascinando [V] O2 | Ctrl (Cmd) tenuto [I] F3 |
| Colori | blu sotto-vincolato, nero vincolato, rosso sovra-vincolato [V] O1 | blu (centerline arancio) libero, nero vincolato [V] F4 |
| Quote | guidanti nere, guidate grigio chiaro; una quota che sovra-vincola diventa guidata da sola [V] O3 | guidate tra parentesi, automatiche se sovra-vincolerebbero; «Fusion does not allow over-constrained sketches» [V] F5 |
| Digitare | valore + Invio subito dopo la linea, diventa quota [V] O4 | lunghezza, Tab, angolo (Ellipse); clic sul primo punto chiude [V] F2, F6 |

Fonti (OS = https://cad.onshape.com/help/Content/, agg. 15/10/2026; FU = https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/files/, consultato 21/10/2026): O1 OS constraints.htm; O2 OS Sketch/automatic_inferencing.htm; O3 OS Sketch/dimension.htm; O4 OS Sketch/line.htm; F1 FU SKT-CONSTRAINTS.htm; F2 FU SKT-CREATE-LINES.htm; F3 https://hackaday.io/project/163649 (29/01/2019; il thread Autodesk risponde 403); F4 FU SKT-FULLY-DEFINE-CONSTRAIN-SKETCH.htm; F5 FU SKT-SKETCH-CREATE-DIMENSIONS.htm e https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/fusion_SketchDimension_isDriving.htm; F6 FU SKT-CREATE-ELLIPSE.htm.

## 4. Riferimenti Qt e open source

- QGIS Advanced Digitizing (Ctrl+4): campi d, a, x, y; lettera = imposta, Ctrl+ o Alt+lettera = blocca, Shift+lettera = relativo; C costruzione; P perpendicolare, PP parallelo; N cicla angoli comuni; blocco continuo; «floater» con distanza e angolo accanto al cursore; Backspace toglie l'ultimo vertice, tasto destro chiude [V] Q1. Tolleranza in pixel o unità mappa, «10 to 12 pixels ... depends on the DPI» [V] Q1; default nel codice 12 px, marker magenta, snapping spento nei progetti nuovi [V] Q2.
- FreeCAD Draft: snapRange 8 px convertiti in distanza 3D a ogni movimento; «Near» è passivo e perde contro ogni snap attivo entro snapRange; Shift vincola H/V, Ctrl = snap solo se «Always snap» è spento, Alt = copia; coordinate nel pannello (X, Y, Z oppure Lunghezza e Angolo, Invio dopo ciascuno); in comando X/Y/Z blocca, L passa da X a Lunghezza, Q «hold point», ` cicla sovrapposti, R relativo (default), / annulla l'ultimo punto; il Draft Tray regola piano di lavoro, stile, costruzione e layer [V] D1, D2.
- LibreCAD: snap griglia, estremi, su entità, centro, medio, distanza, intersezione; restrizioni H, V, ortogonale; «relative zero» bloccabile [V] L1.
- Altre tolleranze: Inkscape oggetti 20, guide 20, griglia 10, allineamento 5 px di schermo [V] K1; Illustrator in punti, default non trovato in fonte ufficiale [I] K2; Figma non trovato.

Fonti (consultate 21/10/2026): Q1 https://docs.qgis.org/latest/en/docs/user_manual/working_with_vector/editing_geometry_attributes.html (agg. 10/08/2026); Q2 https://github.com/qgis/QGIS/blob/master/src/core/qgis.cpp e src/core/settings/qgssettingsregistrycore.cpp; D1 https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Draft_Snap.md, Draft_Constrain.md, Draft_Line.md, Draft_Wire.md, Draft_Tray.md (copia ufficiale del wiki, che blocca i bot); D2 https://github.com/FreeCAD/FreeCAD/tree/main/src/Mod/Draft (draftutils/params.py, draftguitools/gui_snapper.py, Resources/ui/preferences-draftsnap.ui e preferences-draftinterface.ui); L1 https://docs.librecad.org/en/latest/ref/snaps.html; K1 https://gitlab.com/inkscape/inkscape/-/blob/master/src/object/sp-namedview.cpp e src/snap.cpp; K2 https://helpx.adobe.com/illustrator/desktop/measure-and-align/grids-and-guides/smart-guides-options.html (403, letta tramite motore di ricerca).

## 5. Letteratura

- Bier e Stone, «Snap-dragging», SIGGRAPH '86, pp. 233-240, doi:10.1145/15922.15912: cursore attratto («gravity») da punti, linee e cerchi di allineamento costruiti in automatico; il «caret» agganciato è distinto dal cursore; via di mezzo tra griglie e vincoli [V] R1, R2.
- Igarashi et al., «Interactive beautification», UIST '97, doi:10.1145/263407.263525; Baudisch et al., «Snap-and-go», CHI 2005, doi:10.1145/1054972.1055014 [V] R3.

Fonti: R1 https://doi.org/10.1145/15922.15912; R2 bozza del gennaio 1986 https://xeroxparcarchive.computerhistory.org/cyan/gargoyle/siggraph86/.Drag.tioga!1.txt; R3 https://doi.org/10.1145/263407.263525 e https://doi.org/10.1145/1054972.1055014 (metadati verificati su doi.org il 21/10/2026).

## 6. Modificatori presi dal sistema

| Ambiente | Intercettati di default | Fonte |
|---|---|---|
| Niri | Mod = Super su TTY, Alt se annidato (configurabile da 25.05); Mod+sinistro sposta, Mod+destro ridimensiona, Mod+centrale trascina la vista, Mod+rotella consumata da niri; senza Mod: Alt+F4, Ctrl+Print, Alt+Print, Ctrl+Alt+Canc | [V] N1 |
| KDE Plasma 6 | Meta+sinistro sposta, +centrale alza/abbassa, +destro ridimensiona | [V] K3 |
| GNOME | Super+sinistro sposta, +centrale ridimensiona, +destro menu; Super da solo = panoramica | [V] G1 |
| Windows 11 | Win e Win+...; Alt+Tab, Alt+F4, Alt+Esc, Alt+Spazio; Ctrl+Esc; Ctrl+Shift cambia layout; Shift 5 volte = Tasti permanenti | [V] W1, W2 |
| Qt | Alt da solo porta ai menu (hint di stile; attivo con lo stile Windows [I]) | [V] Q3 |

Fonti (consultate 21/10/2026): N1 https://github.com/YaLTeR/niri/blob/main/resources/default-config.kdl e docs/wiki (Configuration:-Key-Bindings.md, Gestures.md); K3 https://invent.kde.org/plasma/kwin/-/blob/master/src/kwin.kcfg; G1 https://gitlab.gnome.org/GNOME/gsettings-desktop-schemas (org.gnome.desktop.wm.preferences) e https://gitlab.gnome.org/GNOME/mutter/-/blob/main/data/org.gnome.mutter.gschema.xml.in; W1 https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-dcc61a57-8ff0-cffe-9796-cb9706c75eec; W2 https://learn.microsoft.com/windows/win32/winauto/built-in-accessibility-features; Q3 https://doc.qt.io/qt-6/qstyle.html.

## 7. Regole da adottare per Meridiana [I]

**Agganci e priorità**
- Punti: vertice, medio, intersezione (anche guida/guida e guida/spigolo, A16), centro o baricentro di falda, piede della perpendicolare, «su spigolo». Direzioni: assi locali, polare, parallelo/perpendicolare allo spigolo sorvolato, prolungamento, allineamento da punti acquisiti.
- Ordine: vertice e intersezione > medio, centro, perpendicolare > incrocio di guide > su spigolo > guida > griglia > libero. «Su spigolo» vince solo se nessun aggancio attivo è in tolleranza (D2); a parità il più vicino, Tab scorre (A13); isteresi 2-3 px contro lo sfarfallio.
- Guide solo da geometria «svegliata»: ultimo punto, punti acquisiti, spigolo sotto il cursore (S1, O2, R2). Acquisizione con sosta di circa 400 ms (valore mio) o col tasto Q (D1); «+» sul punto, nuova sosta per rilasciarlo (A12); al massimo 5-7 punti.
- Polare riferito agli assi dell'edificio o della falda (l'UCS di Meridiana), opzione «relativo all'ultimo segmento»; 90° più angoli aggiuntivi per l'azimut (A9).
- Gli agganci danno coordinate, non vincoli (modello AutoCAD); relazioni persistenti solo esplicite, e se sovra-vincolano diventano quote di riferimento (O3, F5).
- Vista 3D: stessi raggi in pixel sul punto proiettato e inferenza «su faccia» (SketchUp) per posare campi su falde e facciate.

**Tolleranze in pixel logici**
- Raggio in pixel di schermo convertito in metri a ogni movimento (metri = pixel / pixel per metro della vista). Qt lavora in pixel indipendenti dal dispositivo: 10 px diventano 15 px fisici al 150% [V] (https://doc.qt.io/qt-6/highdpi.html), come APERTURE in DIP (A2); per penna e touch serve un raggio maggiore.
- Punti 10 px (AutoCAD 10, QGIS 12, FreeCAD 8); guide e spigoli 6 px, così vincono i punti; selezione 3-5 px; tutto regolabile.
- Marker e testi a dimensione costante con ItemIgnoresTransformations e penne cosmetiche; candidati cercati nel rettangolo attorno al cursore con l'indice BSP [V] (https://doc.qt.io/qt-6/qgraphicsitem.html, https://doc.qt.io/qt-6/qpen.html, https://doc.qt.io/qt-6/qgraphicsscene.html).

**Feedback**
- Forma = tipo (A12), un colore forte con alone scuro (sull'ortofoto un colore pieno sparisce); guide tratteggiate a tutta vista, colorate per direzione: X rosso, Y verde, Z blu, parallelo/perpendicolare magenta (S1).
- Tooltip vicino al cursore con aggancio, distanza, angolo; punto agganciato disegnato sul marker, cursore di sistema fermo (R2); campi d e a accanto al cursore e ripetuti nella barra di stato.

**Digitazione**
- Nessun clic: cifra, segno, «@», «#», «<» aprono il campo (A20, S1, O4); Tab lunghezza → angolo con lucchetto sul campo scritto (A20, F6); Invio conferma; freccia su = valori recenti.
- Default relativo polare; «#x;y» assoluto, «@dx;dy» relativo, «d<a» polare; separatore «;» perché la virgola è decimale (S6); suffissi m, cm, mm.
- Valore + Invio subito dopo un clic ridimensiona l'ultimo segmento (S1); rettangoli «L;W» con parziali; serie «x5» e «/5» per file di moduli (S4). Le coordinate digitate battono gli agganci (A7).

**Blocchi e sospensione**
- Shift tenuto = «blocca ciò che vedi»: la guida attiva se c'è (SketchUp, FreeCAD), altrimenti l'orto locale; con l'orto acceso (F8) lo sospende, come AutoCAD (A19). Con un blocco attivo l'aggancio si proietta sulla linea bloccata (S1); senza blocco l'aggancio prevale (A17).
- Frecce in comando: → X, ← Y, ↓ parallelo/perpendicolare, ↑ Z nel 3D; la stessa freccia sblocca.
- Ctrl tenuto = niente agganci, guide né acquisizioni (scelta di Fusion e richiesta di Daniel). F3, F8, F10, F11, F12 come in AutoCAD, anche tenuti (A18, A19).

**Polilinea**
- Backspace o Ctrl+Z in comando = togli l'ultimo vertice (Q1, A21, D1); «C» o clic sul primo punto = chiudi (F2); Invio o tasto destro = termina (Q1); Shift+destro = menu agganci (A13); Esc a livelli: svuota il campo, annulla il segmento, esce.

## 8. Conflitti di convenzione e scelta

| Tasto | Negli altri programmi | Rischi di sistema | Meridiana |
|---|---|---|---|
| Shift | AutoCAD orto e niente acquisizione; SketchUp e FreeCAD bloccano; Onshape sopprime (al contrario) | Shift 5 volte = Tasti permanenti; Ctrl+Shift = layout (Windows) | blocco, solo tenuto, mai a tocchi |
| Ctrl | Fusion sopprime [I]; FreeCAD snap a richiesta; SketchUp copia; QGIS blocca | nessun WM lo usa col mouse | sospensione guide e agganci |
| Alt | SketchUp cicla le inferenze; QGIS alternativa a Ctrl; FreeCAD copia | Niri annidato: Alt+trascina sposta la finestra; Windows: menu, Alt+Tab | solo funzioni secondarie, mai col trascinamento |
| Super/Meta/Win | nessuno | Niri, KDE, GNOME: +mouse = finestre; Windows: Start | mai |
| Tab | AutoCAD cicla snap e campi; FreeCAD usa «`» | «`» manca sulla tastiera italiana [I] | campo vuoto: cicla; dopo un valore: campo successivo |

Motivazione [I]: per Daniel Shift vuol dire «vincola» (AutoCAD), e così in SketchUp e FreeCAD; solo Onshape lo usa al contrario. Ctrl non è preso da nessun gestore di finestre come modificatore del mouse, ha il precedente di Fusion ed è ciò che Daniel ha chiesto. Alt e Super sono contesi da Niri annidato, KDE, GNOME e Windows; per le combinazioni a rischio conviene offrire due tasti, come fa QGIS con Ctrl e Alt.

Note di metodo: l'help Autodesk è stato letto nelle pagine HTML statiche «cloudhelp» (la versione interattiva non si legge senza JavaScript); il wiki FreeCAD blocca i bot, quindi ho letto la copia ufficiale su GitHub e il codice; pagine Adobe e forum Autodesk rispondono 403. Nessun login, nessun modulo.
