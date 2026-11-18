# Meridiana: convenzioni e buone pratiche per la revisione UX

Ricerca del 22/10/2026 per la revisione UX di Meridiana (Qt 6.12 / PySide6, Windows e Linux con Niri). Accompagna `12-revisione-ux-prestazioni.md`: lì ci sono le misure e il piano, qui le convenzioni, le fonti e le raccomandazioni. È stata fatta senza toccare il codice e senza aprire finestre.

**Legenda**
- [V] letto sulla fonte; tra «» il testo originale.
- [V-loc] letto nell'archivio locale di Daniel.
- [S] visto solo in un estratto di ricerca o su una fonte secondaria: non pienamente verificato.
- [D] deduzione mia, oppure ricordo non verificato.

**Metodo**
- Fonti ufficiali dove esistono: help Autodesk, SketchUp, Blender, FreeCAD, QGIS, DIALux, Aurora, HelioScope, PVsyst, OpenSolar, PVcase, Microsoft, GNOME, Apple, Qt, W3C, NN/g. Pagine lette il 21-22/10/2026.
- PVsyst cercato prima in locale, come da regola: `l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\pvsyst-tutorial-v8-1-grid-connected-en.pdf` (v8.1) e `l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\pvsyst-tutorial-v8-grid-connected-en.pdf` (v8.0), con le pagine indicate. Per le convenzioni d'interfaccia l'archivio locale non ha materiale.
- Gli help center Zendesk (Aurora, HelioScope, OpenSolar, PVcase) rispondono 403 ai lettori automatici: letti con User-Agent da browser o con l'API pubblica degli articoli. La wiki di FreeCAD ha una protezione anti-bot: usata la copia ufficiale su GitHub. bugreports.qt.io ora reindirizza a qt-project.atlassian.net.
- Nessun login, paywall o CAPTCHA. Il budget di ricerche web si è esaurito a fine lavoro: le voci rimaste aperte sono nel capitolo 6.

**Indice**
1. Scorciatoie e comandi (con la mappa proposta per Meridiana)
2. Navigazione 2D e 3D
3. Criticità nelle viste
4. Pannelli e moduli delle proprietà
5. Reattività
6. Cosa resta da verificare

---

## 1. Scorciatoie e comandi

### 1.1 AutoCAD (help 2026-2027, PDF ufficiale 2024)

**Ctrl e palette** [V]

| Tasto | Comando | Nota |
|---|---|---|
| Ctrl+1 | «Toggles Properties palette» | uguale in Revit |
| Ctrl+0 | «Toggles Clean Screen» | |
| Ctrl+2 / Ctrl+3 / Ctrl+9 | DesignCenter / «Toggles the Tool Palettes window» / «Toggles the Command Line window» | Ctrl+4, 6, 7, 8 altri gestori; Ctrl+5 libero |
| Ctrl+Maiusc+H | nasconde e rimostra tutte le palette | |
| Ctrl+Maiusc+P | «Toggles the Quick Properties interface» | contro la palette di VS Code |
| Ctrl+B | «Toggles Snap» | contro Ctrl+B di VS Code |
| Ctrl+F / G / L / U | osnap / griglia / «Toggles Ortho mode» / polare | doppioni dei tasti F |
| Ctrl+J o Ctrl+M | «Repeats last command» | contro Ctrl+J di VS Code |
| Ctrl+K | inserisce un collegamento ipertestuale | |
| Ctrl+[ o Ctrl+\ | «Cancels current command» | come Esc |
| Ctrl+Tab, Ctrl+PagSu/PagGiù | disegni aperti, schede dei layout | |
| Ctrl+I | «Toggles the Coordinates display» | in Meridiana Ctrl+I è l'import PVsyst |

**Tasti funzione** (AutoCAD 2026) [V]

| F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | F9 | F10 | F11 | F12 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| guida | cronologia comandi | osnap | osnap 3D | isopiano | UCS dinamico | griglia | orto | snap griglia | polare | puntamento osnap | input dinamico |

- «F8 and F10 are mutually exclusive» [V].
- F12: «Displays distances and angles near the cursor and accepts input as you use Tab between fields» [V]. Tenendo premuto F12 durante un comando l'input dinamico si spegne per il momento [V].

**Alias e comandi da tastiera** [V, PDF 2024; il file acad.pgp predefinito non è stato letto]
- Z ZOOM con le opzioni All, Extents («maximum extents of all objects»), Previous («You can restore up to 10 previous views»), Window, Object, tempo reale. «Z Invio E Invio» = zoom estensione è la prassi [D].
- P PAN; E ERASE; L LINE; M MOVE; CO COPY; RO ROTATE; MI MIRROR; O OFFSET; DI DIST; MEA MEASUREGEOM; LA LAYER; PR PROPERTIES; RE REGEN; TR TRIM; EX EXTEND; REC RECTANG; PL PLINE; ORBIT 3DORBIT; CUBE NAVVCUBE.

**Comportamenti** [V]
- Invio e Spazio: «press Enter or the spacebar to start the command»; «You can also repeat the previous command by pressing Enter or the spacebar.»
- Esc: «you can always escape by pressing the ESC key». Il nome del comando si completa da solo; AutoCorrect impara i refusi.
- Tasto destro configurabile (menu o Invio). Con «Time-Sensitive Right-Click»: «A quick click is the same as pressing Enter. A longer click displays a shortcut menu.»
- Selezione: «Drag from left to right to select all objects that are entirely enclosed»; «Drag from right to left to select all objects that are crossed»; Maiusc+clic toglie, Esc svuota.
- Input dinamico: «a command interface near the cursor in the drawing area»; Freccia giù apre le opzioni, Tab passa tra i campi.
- Mouse: rotella = zoom; doppio clic sulla rotella = zoom estensione; rotella premuta = pan (MBUTTONPAN=1); dalla 2026 «You can enter 3D orbit mode temporarily by pressing SHIFT and the mouse wheel»; durante l'orbita «A small dark sphere displays temporarily, representing the target point».
- Personalizzazione: alias nel file .pgp («<Alias>,*<Full command name>», si ricarica con REINIT); scorciatoie nel file CUIx.

### 1.2 Revit (PDF ufficiale delle scorciatoie © 2024, help 2026)

| Sequenza | Comando | Stato |
|---|---|---|
| VV o VG | Visibility/Graphics | [V] |
| ZA | «ZOOM ALL TO FIT» | [V] |
| ZE, ZF o ZX | «ZOOM TO FIT» | [V] |
| ZR o ZZ | «ZOOM IN REGION» | [V] |
| ZO o ZV | «ZOOM OUT(2X)» | [V] |
| ZP o ZC | «PREVIOUS PAN/ZOOM» | [V] |
| ZS | «ZOOM SHEET SIZE» | voce presente, codice non estratto: [D] |
| HH / HI / HC / IC / HR | nascondi elemento / isola elemento / nascondi categoria / isola categoria / «RESET TEMPORARY HIDE/ISOLATE» | [V] |
| TL | «THIN LINES» | [V] |
| WT / WC | affianca / sovrapponi le finestre | [V] |
| PP, Ctrl+1 o VP | «PROPERTIES; TOGGLE PROPERTIES PALETTE» | [V], lo stesso Ctrl+1 di AutoCAD |
| KS | dialogo delle scorciatoie | [V] |
| RC | «REPEAT LAST COMMAND» | [V] |
| MV, CO o CC, RO, MM, AL, DI | sposta, copia, ruota, specchia, allinea, quota | [V] |
| SD / WF / HL | ombreggiata con spigoli / fil di ferro / linee nascoste | [V] |
| SN | «SNAPS OFF» | [V] |

- Funzionamento [V]: «In Revit all keyboard shortcuts are made up of at least two keys pressed in sequence.» «When you press the final key in the shortcut, Revit executes the tool.» Niente Invio, nessun timer documentato. Massimo 5 tasti. Se più strumenti hanno la stessa sequenza si sceglie dalla barra di stato. Le scorciatoie compaiono nei tooltip.
- Mouse [V]: «Press the middle mouse button to pan the view.» «The position of the mouse pointer establishes the center of the zoom.» «In a 3D view, press Shift and use the middle button to orbit the model.» Il centro dell'orbita è il centro del modello, ma «If you select an object and then orbit the view, the selected object is used as the center of rotation.» Ctrl+Tab passa tra le viste aperte.
- View Control Bar sotto la vista [V]: scala, livello di dettaglio, stile, Sun Path sì/no, ombre sì/no, ritaglio, nascondi/isola temporaneo.

### 1.3 SketchUp (help aggiornato a ottobre 2026)

| Tasto | Strumento [V] |
|---|---|
| Spazio / Maiusc+Spazio | Select / Lasso Select |
| O | Orbit |
| H | Pan |
| Z | Zoom |
| Maiusc+Z | Zoom Extents |
| L R C A | Line, Rectangle, Circle, Arc |
| P M Q S F | Push/Pull, Move, Rotate, Scale, Offset |
| T E B | Tape Measure, Eraser, Paint Bucket |
| Maiusc+S | Search (ricerca dei comandi) |

- Mouse [V]: orbita = «click and hold the scroll wheel»; pan = rotella premuta più tasto sinistro, oppure Maiusc durante l'orbita; «When you zoom by scrolling, SketchUp uses your cursor as the zoom's center point»; doppio clic con l'orbita centra il modello.
- Personalizzazione [V]: Preferenze > Scorciatoie, con ricerca. «Numbers are reserved for some very specific commands or for adjusting measurements.» «You can't use shortcuts reserved by your operating system.»
- Zoom finestra: nessuna scorciatoia predefinita nelle pagine lette; Ctrl+Maiusc+W non verificato [D].

### 1.4 Blender (manuale 5.2 LTS)

Tn = tasto del tastierino numerico.

| Tasto | Azione [V] |
|---|---|
| Tn7 / Tn1 / Tn3 | vista dall'alto / frontale / destra |
| Ctrl+Tn7 / 1 / 3 | dal basso / posteriore / sinistra |
| Tn5 | prospettiva o ortogonale |
| Tn0 | camera attiva |
| Tn2 / 4 / 6 / 8, Tn9 | orbita a passi; lato opposto |
| Tn. (punto) | Frame Selected |
| Home | Frame All |
| Maiusc+B | Zoom Region |
| ` (accento grave) | menu a torta delle viste |
| N / T | barra laterale destra / barra strumenti |
| F3 | «Menu Search» (la palette dei comandi) |
| F1 / F2 / F9 | aiuto contestuale / rinomina / Adjust Last Operation; «F5 - F8 Reserved for user actions» |
| Ctrl+Spazio | «Toggle Maximize Area» |
| Ctrl+Alt+Spazio | Focus Mode (nasconde barre e pannelli) |
| centrale / Maiusc+centrale / rotella | orbita / pan / zoom |

- Gizmo di navigazione in alto a destra: un clic su un asse allinea la vista, un secondo clic passa al lato opposto [V].
- Portatili [V]: «Emulate Numpad: If you have a keyboard without a Numpad (e.g. on a laptop), you can tell Blender to treat the standard number keys as Numpad keys»; «Emulate 3 Button Mouse» usa Alt+sinistro.
- Preferenze di navigazione [V]: Orbit Around Selection, Auto Depth, Zoom to Mouse Position, Smooth View in millisecondi.
- Sopra un campo: «Ctrl - Wheel: Change the value in incremental steps»; la rotella da sola non cambia il valore [V].
- Keymap «Industry Compatible» [V]: F1-F4 viste fronte/lato/alto/camera, F = Frame Selected, A = Frame All, Tab = ricerca, Alt+tasti del mouse = navigazione.

### 1.5 FreeCAD (1.0, copia ufficiale della wiki e sorgente)

| Tasto | Comando [V] |
|---|---|
| 0 | isometrica |
| 1 / 2 / 3 | fronte / alto / destra |
| 4 / 5 / 6 | retro / basso / sinistra |
| V poi F | adatta tutto |
| V poi S | adatta alla selezione |
| V poi O / V poi P | ortogonale / prospettica |
| Maiusc+frecce sinistra/destra | rotazione di 90° |

- Stili di navigazione selezionabili [V]: Blender, CAD (predefinito: rotella zoom, centrale pan, centrale+sinistro rotazione), Gesture, Maya-Gesture, OpenCascade, OpenInventor, OpenSCAD, Revit (Maiusc+centrale rotazione), TinkerCAD, Touchpad.
- Navigation Cube in alto a destra, «26 faces», frecce, mini-cubo con menu [V].

### 1.6 QGIS (documentazione 3.44)

| Tasto | Comando [V] |
|---|---|
| Ctrl+Maiusc+F | Zoom Full |
| Ctrl+J | Zoom To Selection (contro Ctrl+J di VS Code) |
| Ctrl+B / Ctrl+Maiusc+B | nuovo segnalibro spaziale / elenco |
| F5 / F11 | aggiorna / schermo intero |
| Ctrl+Tab | «Toggle Panel Visibility» |
| Ctrl+Maiusc+Tab | «Toggle Map Only» |
| Ctrl+K | Locator, la palette |
| Ctrl+8 | pannello Overview |

- Mouse [V]: rotella zoom (Ctrl+rotella più fine), rotella premuta pan, Spazio+mouse pan, frecce pan; i tasti Indietro e Avanti del mouse scorrono la cronologia degli zoom.
- Pannelli [V]: Vista > Pannelli e Vista > Barre degli strumenti; «If you have accidentally hidden a toolbar, you can get it back using View > Toolbars».
- Locator [V]: prefissi per filtrare; la ricerca gira in thread separati, «This ensures that the UI is always responsive».
- Scorciatoie [V]: Impostazioni > Scorciatoie da tastiera, con ricerca, ripristino del predefinito, esportazione in XML o PDF.

### 1.7 Programmi fotovoltaici e illuminotecnici

**DIALux evo** (PDF ufficiale delle scorciatoie, evo 11.1 Patch 1, 05/2023) [V]

| Tasto | Comando |
|---|---|
| F1 / Ctrl+F1 | aiuto / «Display the overview of the keyboard shortcuts» |
| F2 | rinomina nell'albero; nella vista CAD mostra/nasconde il sistema di coordinate |
| F3-F9 | filtri della vista (linee ausiliarie, piani, fil di ferro, risultati, disegni, curve, falsi colori) |
| F11 / F12 | schermo intero / ripete l'ultima azione |
| Ctrl++ / Ctrl+- / Ctrl+* | zoom / zoom / «Position the camera so that the entire content of the CAD window will fit» |
| Ctrl+1...0 / Alt+1...0 | salva / richiama 10 posizioni della camera |
| Ctrl+Tn5 / Ctrl+Tn0 | pianta / 3D |
| Ctrl+Tn8 / 2 / 4 / 6 | viste 2D da davanti, dietro, sinistra, destra |
| Maiusc+Alt+lettera | apre strumenti e pannelli |
| Tab | manipolatore o campo numerico successivo |
| Ctrl+Maiusc+Spazio / Q | avvia / interrompe il calcolo |

- Senza rotella: «P + left mouse button = shift; Z + left mouse button = zoom» e WASD [V].
- Nord [V]: «Draw north arrow» sulla pianta oppure angolo in gradi; da evo 8 «The north orientation is displayed in 3D and 2D with a small preview at the bottom right».

**Aurora Solar** («Keyboard Shortcuts (System Design)», 15/04/2026) [V]

| Tasto | Comando |
|---|---|
| Maiusc+1 / Maiusc+2 | «Focus on all» / «Focus on selection» |
| centrale, o Spazio + sinistro | pan |
| destro trascinato in orizzontale / verticale | rotazione / inclinazione 3D |
| R, Q, W, E, T, L, G, M, P, V, B, C, H, A | strumenti a lettera singola (SmartRoof, ostruzioni, albero, LIDAR, mappa, moduli, strutture, inverter, quadri, stringhe, mostra/nascondi, Auto-Designer) |
| Ctrl tenuto | «Hold the Ctrl key to override mouse snapping» |
| Esc / Canc | esce dalla modalità / elimina |

- Nessun tasto per l'elenco delle scorciatoie trovato nell'help [D].

**HelioScope** («Keyboard Shortcuts», 21/07/2026) [V]
- Maiusc tenuto mentre si disegna: linee perpendicolari e snap; «vertex snapping takes precedence over angle snapping».
- Maiusc+trascina = orbita 3D; Maiusc+Spazio mostra/nasconde i moduli; Ctrl+C/V/R/Z/Y; Canc o Backspace; A/E keepout; S selezione multipla; frecce su/giù nei campi numerici cambiano il valore.

**PVsyst 8.1, editor 3D delle ombre vicine** [V-loc, tutorial v8.1 pp. 88-91; stessi tasti in v8.0 pp. 63-68; help online]

| Tasto | Comando |
|---|---|
| F2 / F3 / F4 / F5 | prospettiva di base / dall'alto / frontale / laterale |
| F6 | «Aligns the view to the current sun position» (vista dal sole) |
| F7 / F8 | zoom avanti / indietro |
| Ctrl+F | «Zooms to see all selected objects» |
| centrale / Maiusc+centrale | ruota attorno al target / pan |
| Ctrl+L | lazo e anche «Measure a Distance» (stesso tasto, due comandi) |
| Ctrl+Alt+R | ruota tutta la scena (su tastiera italiana Windows Ctrl+Alt = AltGr [D]) |
| Ctrl+G | elenco degli oggetti, selezione sincronizzata con la scena |

- Proiezione ortogonale predefinita, «recommended when constructing the scene»; «Enable camera animation: Animates the transition when switching views» [V-loc p. 89-90].

**OpenSolar e PVcase** [V]
- OpenSolar 3D: «Rotate: right-click + drag. Move / pan: left-click + drag. Zoom: scroll wheel»; nessun elenco di scorciatoie trovato.
- PVcase Ground Mount gira dentro AutoCAD e ne usa le convenzioni: alias, F3, F8, F12 («If you can't just type the commands in the model space... press F12»).
- Easy Solar: non cercato.

### 1.8 IDE: pannelli e palette

**VS Code** (documentazione al 21/10/2026) [V]

| Tasto (Windows e Linux) | Comando |
|---|---|
| Ctrl+B | barra laterale primaria («Toggle Sidebar Visibility») |
| Ctrl+Alt+B | barra laterale secondaria |
| Ctrl+J | pannello in basso |
| Ctrl+Maiusc+P o F1 | «Show All Commands» |
| Ctrl+P | apertura rapida |
| Ctrl+K Ctrl+S | editor delle scorciatoie |
| Ctrl+, | impostazioni |
| Ctrl+Maiusc+M | «Show Problems» |
| F8 / Maiusc+F8 | «Go to Next / Previous Error or Warning» (in tutti i file) |
| Ctrl+. | Quick Fix |
| Ctrl+K Z | modalità zen |
| Ctrl+= / Ctrl+- | zoom dell'interfaccia |

- La palette insegna i tasti: «You can see the default keyboard shortcut alongside the command in the Command Palette» [V].
- Pannelli: «View: Reset View Locations», Customize Layout > Restore Defaults [V].
- Tastiere non statunitensi [V]: le scorciatoie sono mostrate nel layout corrente; «VS Code does not contain default keybindings that are of the form Ctrl+Alt+[Key] on Windows, since these might produce vital characters» (AltGr). Tastiera italiana: Ctrl+/ «which on my Keyboard layout (Italy IT) is Ctrl+Shift+7» non funziona (issue #297698, 02/2026, Linux). Su Linux Ctrl+Maiusc+U è catturato dal metodo di input (issue #119691).

**JetBrains IntelliJ/PyCharm 2026.2** [V]
- Alt+1...Alt+0 finestre degli strumenti (Alt+1 Project, Alt+6 Problems); Ctrl+Maiusc+F12 nasconde/ripristina tutte; Maiusc+Esc nasconde l'attiva.
- Maiusc+F12 ripristina il layout predefinito; Window > Layouts per salvarne altri.
- Maiusc Maiusc = Search Everywhere; Ctrl+Maiusc+A = Find Action; Ctrl+Alt+S = impostazioni.
- F2 / Maiusc+F2 = errore successivo/precedente. **Ctrl+B = Go To Declaration**, quindi Ctrl+B «barra laterale» è solo di VS Code.
- «If your keyboard does not have an English layout, IntelliJ IDEA may not detect all the shortcuts correctly.» Su Linux segnala i conflitti con il sistema (Ctrl+Alt+L blocca lo schermo, Ctrl+Alt+T terminale, Alt+F7 e Alt+F8 spostano e ridimensionano la finestra).

### 1.9 Conflitti

**Windows 11** [V, pagina «Keyboard shortcuts in Windows»]
- Riservati al sistema: Win da solo e Win+quasi tutto; Alt+Tab; Alt+F4; Alt+Spazio (menu della finestra); Ctrl+Esc; Ctrl+Maiusc+Esc; Ctrl+Alt+Canc; Stamp.
- Cambio di lingua e layout: Win+Spazio; Ctrl+Maiusc «When multiple keyboard layouts are available, switch the keyboard layout»; Alt+Maiusc (solo da una risposta Microsoft Q&A).
- Convenzioni per le app: F1 guida; F2 rinomina; F5 aggiorna; F6 ciclo degli elementi della finestra; F10 barra dei menu; Maiusc+F10 menu contestuale; Alt+Invio proprietà; F11 schermo intero.
- In Esplora file: Ctrl+cifra «Move to that tab number»; **Ctrl+Maiusc+cifra «Change the view style»** (precedente utile per le modalità di vista).
- Regole di progettazione (Win32 UX guide, scritta per Windows 7 e mai ritirata) [V]:
  - «Don't use Ctrl+Alt combinations, because Windows interprets this combination in some language versions as an AltGR key, which generates alphanumeric characters.»
  - «Don't use the Windows logo modifier key for program shortcut keys.» «Don't use shortcut keys used by Windows.»
  - «Don't use Alt+alphanumeric key combinations for shortcut keys» (conflitto con i tasti di accesso dei menu).
  - «Don't use the following characters for shortcut keys: @ $ {} [] \ ~ | ^ ' < >.»
  - Liberi per i comandi frequenti: «Ctrl+G, J, K, L M, Q, R, or T; Ctrl+any number; F7, F8, F9, or F12; Shift+F2, F3, F4, F5, F7, F8, F9, F11, or F12; Alt+any function key except F4».
  - Liberi per i comandi rari: «Ctrl+any function key except F4 and F6; Ctrl+Shift+any letter or number».
  - Documentare ogni scorciatoia in menu, tooltip e una pagina unica; se sono tante, «provide the ability to customize».
- WinUI «Keyboard accelerators» [V]: «Single key (A, Delete, F2, Spacebar, Esc...) accelerators... are supported»; Ctrl+0 «Zoom to default view»; F6 e Maiusc+F6 riquadro successivo e precedente.

**GNOME** [V]
- HIG, scorciatoie standard: F1 guida; **F9 «Toggles utility pane visibility»**; F10 menu principale; **Ctrl+? «Opens the keyboard shortcuts dialog»**; Ctrl+, preferenze; Maiusc+Ctrl+P anteprima di stampa; Alt+Invio proprietà; Ctrl+0 dimensione normale.
- HIG, riservati: Alt+Tab, Alt+F4, Alt+F5, Alt+F6, Alt+F7, Alt+F8, Ctrl+Alt+Tab, Alt+Spazio, Ctrl+Alt+Canc. Regole: «Try to use Ctrl in combination with a letter»; «Do not use Alt for shortcut keys»; «GNOME reserves the use of the Super key».
- Schemi predefiniti: Ctrl+Alt+frecce cambiano area di lavoro; Alt+F2 esegui; Alt+F10 massimizza; Super+qualsiasi; Super+Spazio sorgente di input; su Wayland Ctrl+Alt+F1...F12 cambiano sessione.
- GTK: GtkApplication imposta Ctrl+? per la finestra delle scorciatoie (GtkShortcutsWindow deprecata dalla 4.18, sostituita da AdwShortcutsDialog). IBus: Ctrl+Maiusc+U inserimento Unicode; emoji ora su Super+. e Super+;.

**Niri** (default-config.kdl, ramo main, commit 5fe8877 del 11/10/2026; il repository YaLTeR/niri ora reindirizza a niri-wm/niri) [V]
- «"Mod" is a special modifier equal to Super when running on a TTY, and to Alt when running as a winit window.» Sul portatile di Daniel Niri gira su TTY, quindi Mod = Super.
- Tutti i legami predefiniti usano Mod, tranne: Stamp, Ctrl+Stamp, Alt+Stamp (schermate); Ctrl+Alt+Canc (uscita); i tasti XF86 (volume, luminosità, touchpad); Alt+F4 (solo nel ramo main). Nel codice sono fissi Ctrl+Alt+F1...F12 (cambio VT): «Hardcoded binds must never be inhibited».
- Mod+Maiusc+/ mostra l'elenco dei tasti («usually the same as Mod-?»); Mod+Esc attiva/disattiva l'inibizione delle scorciatoie.
- Un tasto legato al compositor non arriva all'applicazione.

**Tastiera italiana** [V, layout Microsoft «Italiano» e xkb «it»]

| Carattere | Come si scrive | Conseguenza per le scorciatoie |
|---|---|---|
| @ # | AltGr+ò, AltGr+à | da evitare |
| [ ] | AltGr+è, AltGr++ | da evitare (QTBUG-51848 aperto: Ctrl+[ ] non funzionano dove servono con AltGr) |
| { } | AltGr+Maiusc+è, AltGr+Maiusc++ | da evitare |
| / | Maiusc+7 | Ctrl+/ = Ctrl+Maiusc+7 |
| ? | Maiusc+' (tasto a destra dello 0) | ? e Ctrl+? raggiungibili |
| \ | tasto a sinistra dell'1 | da evitare (regola Microsoft) |
| ` ~ | assenti su Windows (AltGr+' e AltGr+ì su Linux) | il menu a torta di Blender non si raggiunge |
| € | AltGr+E | su Windows Ctrl+Alt+E scrive € |

- «This layout treats right Alt key as Control+Alt» (kbdlayout.info). Qt: «Key_AltGr: On Windows, when the KeyDown event for this key is sent, the Ctrl+Alt modifiers are also set». Su Linux AltGr è un modificatore distinto.
- Bug Qt aperti [V]: QTBUG-73247 (Windows: le scorciatoie dell'app rubano i caratteri scritti con AltGr), QTBUG-69317 (AltGr letto come Alt, si attivano i tasti di accesso dei menu), QTBUG-101152 (Ctrl++ non funziona su tastiera tedesca in Windows).

**Come Qt confronta i tasti** [V doc e sorgente; comportamento reale D]
- QKeySequence, «Keyboard Layout Issues»: una sequenza può «map to a different key, map to no keys at all, or require an additional modifier»; ammessi fino a 4 tasti in sequenza («Ctrl+X, Ctrl+C»).
- Nel sorgente (qwindowskeymapper.cpp, qxkbcommon.cpp) Qt prova il tasto base con tutti i modificatori e poi le varianti in cui Maiusc è «consumato» dal carattere. Sulla tastiera italiana quindi dovrebbero scattare «?», «Ctrl+?», «Ctrl+/» e «Ctrl+Maiusc+cifra»; **non scattano «Maiusc+?» né «Ctrl+Maiusc+/»** (servirebbe Maiusc due volte) [D da provare].
- Fuoco in un campo di testo [V sorgente]: QLineEdit e gli spinbox accettano ShortcutOverride per i caratteri stampabili, Canc, Backspace, Inizio, Fine e frecce, quindi le lettere singole non scattano mentre si scrive. QTreeView e le combo non modificabili no: con il fuoco nell'albero Progetto la lettera fa scattare lo strumento (si perde la ricerca per iniziale) [D].
- Contesti di QShortcut [V]: WidgetShortcut, WidgetWithChildrenShortcut, WindowShortcut (predefinito), ApplicationShortcut.

**Tasti funzione dei portatili** [V]
- Framework Laptop 13 AMD (firmware EC): senza Fn lock la riga funzione invia i tasti multimediali; Fn+F1...F12 dà i veri tasti F; **Fn+Esc** commuta il blocco, che resta memorizzato. Mappa senza Fn: F1 muto, F2-F3 volume, F4-F6 brani, F7-F8 luminosità, **F9 = Super+P**, F10 modalità aereo, **F11 = Stamp** (su Niri apre lo strumento di screenshot), F12 tasto Framework. Inizio/Fine = Fn+←/→, PagSu/PagGiù = Fn+↑/↓. Niente tastierino numerico.
- Lenovo ThinkPad: Fn+Esc commuta, con la spia spenta F1-F12 fanno le funzioni speciali. HP e Dell non verificati.
- JetBrains: le scorciatoie «cannot begin with the Fn key as it is reserved for hardware functions» [V].

**Wayland e accessibilità** [V]
- Protocollo keyboard-shortcuts-inhibit: il compositor «is under no obligation to disable all»; Niri, Mutter e KWin lo supportano; Qt non lo usa (QTBUG-116492 aperto).
- WCAG 2.2 SC 2.1.4 (livello A): una scorciatoia fatta di soli caratteri deve offrire almeno uno fra «Turn off», «Remap», «Active only on focus». EN 301 549 V3.2.1, 11.2.1.4.1, la applica al software non web.

### 1.10 Verifica dei tasti candidati

La colonna «Framework» indica cosa fa il tasto senza Fn lock (stato iniziale).

| Tasto | Windows 11 | GNOME | Niri (TTY) | Tastiera IT | Framework | Giudizio |
|---|---|---|---|---|---|---|
| Ctrl+B | grassetto nei testi | grassetto | libero | ok | ok | sicuro |
| Ctrl+1...9 | scheda N in Esplora e dialoghi; «Ctrl+any number» consigliato | libero | libero | ok | ok | sicuri |
| Ctrl+0 | zoom predefinito | dimensione normale | libero | ok | ok | sicuro, significato diverso da AutoCAD |
| Ctrl+J, Ctrl+K | liberi (consigliati) | liberi | liberi | ok | ok | sicuri |
| Ctrl+Maiusc+P | libero | anteprima di stampa | libero | ok | ok | conflitto lieve |
| Ctrl+P | stampa | stampa | libero | ok | ok | non per la palette |
| Ctrl+Maiusc+cifra | stile di vista in Esplora | libero | libero | Maiusc+cifra = simbolo, Qt usa il tasto base [D] | ok | da provare |
| F1 | guida | guida | libero | ok | muto | standard, non unico accesso |
| ? / Ctrl+? | liberi | Ctrl+? = scorciatoie | liberi | Maiusc+' / Ctrl+Maiusc+' | ok | ok in Qt [D] |
| Maiusc+? / Ctrl+Maiusc+/ | - | - | - | irraggiungibili | - | evitare |
| Ctrl+/ | libero | libero | libero | Ctrl+Maiusc+7, ok in Qt [D], rotto in VS Code | ok | accettabile, non preferito |
| F2 | rinomina | rinomina [D] | libero | ok | volume - | per Rinomina |
| F3 / F8 / F12 | trova successivo / consigliato / consigliato | Alt+F8 riservato | liberi | ok | volume +, luminosità, tasto Framework | ok con Fn |
| F4 | apre l'elenco della combo; Alt+F4 chiude | Alt+F4 riservato | Alt+F4 (main) | ok | brano precedente | evitare per comandi frequenti |
| F6 | riquadro successivo | Alt+F6 riservato | libero | ok | brano successivo | per il ciclo dei pannelli |
| F9 | consigliato | pannello laterale | libero | ok | Super+P | non usare |
| F10 | barra dei menu | menu | libero | ok | aereo | lasciare al sistema |
| F11 | schermo intero | Qt su GNOME usa Ctrl+F11 | libero | ok | Stamp, screenshot di Niri | solo come alias |
| Ctrl+Tab, Ctrl+PagSu/PagGiù | schede | Ctrl+Tab esce dai campi | liberi | ok | PagSu = Fn+↑ | schede centrali |
| Alt+lettera, Alt+cifra | tasti di accesso | vietato | Mod se Niri annidato | ok | ok | evitare |
| Ctrl+Alt+lettera | AltGr (Ctrl+Alt+E = €) | riservati vari | Ctrl+Alt+Canc, F1...F12 | AltGr | ok | evitare |
| Ctrl+Spazio | IME cinese se installato | vecchio elenco IBus | libero | ok | ok | evitare |
| Ctrl+Maiusc+U, Alt+Maiusc | - / cambio lingua | IBus Unicode | - | ok | ok | evitare |
| Ctrl+. | libero | emoji solo nei campi GTK | libero | ok | ok | sicuro in Qt [D] |
| Super/Win+qualsiasi | sistema | sistema | Mod di Niri | - | - | mai |

### 1.11 Cosa conviene a Meridiana

**Principi** [D, appoggiati alle fonti sopra]
1. **Una famiglia per categoria, dichiarata.** Pannelli, palette e verifiche dagli IDE (VS Code, che Daniel usa e cita); ausili al disegno, mouse e alias dal mondo Autodesk (AutoCAD e Revit, la sua memoria muscolare); strumenti a lettera singola come Aurora, HelioScope e SketchUp. Così i conflitti fra programmi si risolvono con una regola, non caso per caso.
2. **Mai un comando solo su un tasto F.** Sul Framework i tasti F sono multimediali senza Fn lock e F11 apre lo screenshot di Niri. Ogni comando sta in un menu, nella palette e, se frequente, su Ctrl+lettera o Ctrl+cifra. Gli ausili al disegno hanno anche un pulsante nella barra di stato, come in AutoCAD.
3. **Tasti vietati:** Win/Super; Alt+lettera e Alt+cifra; qualsiasi Ctrl+Alt; i caratteri scritti con AltGr ([ ] { } @ # ~ `) e \; Maiusc+?; Ctrl+Maiusc+/; Ctrl+Spazio; Ctrl+Maiusc+U; Alt+Maiusc.
4. **Lettere singole** attive in tutta la finestra tranne mentre si scrive in un campo (Qt lo fa già), **rimappabili** con un editor (WCAG 2.1.4). **Cifre** riservate alle lunghezze digitate, come in SketchUp.
5. **Scorciatoie visibili** in menu, tooltip e palette (Revit, VS Code), e un editor con ricerca, ripristino e esportazione (QGIS, SketchUp).
6. **In Qt** tutte le scorciatoie sono QAction della QMainWindow (non Shortcut QML: QTBUG-147913), con QKeySequence.StandardKey dove esiste (Annulla, Ripeti, Salva, Zoom).

**Mappa proposta**

| Gruppo | Tasto | Comando | Precedente | Note |
|---|---|---|---|---|
| Pannelli | Ctrl+B | pannello Progetto sì/no | VS Code [V] | AutoCAD Ctrl+B = snap (ha anche F9); JetBrains = dichiarazione |
| Pannelli | Ctrl+1 | pannello Proprietà sì/no | AutoCAD, Revit [V] | come chiede Daniel |
| Pannelli | Ctrl+J | pannello in basso (Verifiche) sì/no | VS Code [V] | AutoCAD Ctrl+J = ripeti (resta Invio) |
| Pannelli | Ctrl+Maiusc+M | apre Verifiche e ci mette il fuoco | VS Code «Show Problems» [V] | |
| Pannelli | Ctrl+0 | schermo pulito | AutoCAD [V] | Windows e GNOME: Ctrl+0 = zoom normale; Meridiana non ha uno «zoom 100%» |
| Pannelli | F6 / Maiusc+F6 | fuoco al riquadro successivo / precedente | Windows, WinUI [V] | alias, non unico accesso |
| Pannelli | (menu) | Vista > Pannelli > Ripristina disposizione | JetBrains Maiusc+F12, Visual Studio [V] | |
| Schede | Ctrl+Tab / Ctrl+Maiusc+Tab | scheda centrale successiva / precedente | Windows, QTabWidget, Revit [V] | |
| Schede | Ctrl+PagGiù / Ctrl+PagSu | idem | AutoCAD (layout) [V] | sul Framework: Ctrl+Fn+frecce |
| Viste | Ctrl+Maiusc+2 | solo pianta; di nuovo: affiancate | Esplora file Ctrl+Maiusc+cifra [V]; 2 = 2D [D] | sostituisce F2 |
| Viste | Ctrl+Maiusc+3 | solo 3D; di nuovo: affiancate | come sopra; Blender Ctrl+Spazio [V] | sostituisce F3 e F4 |
| Palette | Ctrl+Maiusc+P | palette: comandi, oggetti, impostazioni, alias AutoCAD («ZE», «ZW», «ZP») | VS Code [V]; QGIS Ctrl+K [V]; Blender F3 [V] | AutoCAD = proprietà rapide; GNOME = anteprima di stampa |
| Aiuto | Ctrl+? (Ctrl+Maiusc+' sulla tastiera IT) | elenco delle scorciatoie, con ricerca | GNOME/GTK [V] | da provare in Qt su Windows e Niri |
| Aiuto | ? (fuoco nella vista) | idem | app web [D] | lettera singola |
| Aiuto | F1 | guida | Windows, GNOME, Qt [V] | |
| Aiuto | Ctrl+, | preferenze | GNOME, VS Code [V] | |
| Strumenti | V B P S X D W | Seleziona, Edificio, Falda, Sottocampo, Esclusione, Misura, Stringhe | Aurora, HelioScope, SketchUp [V] | Misura su D dal 24/10/2026 (nota su M) |
| Strumenti | M | Sposta; dentro Sposta R ruota, C copia, Tab passa dalla distanza alla direzione | AutoCAD, SketchUp [V] | compito 16b; fuori da Sposta R resta il rettangolo |
| Strumenti | R, Q | rettangolo, squadra (durante il disegno) | SketchUp R [V] | invariati |
| Strumenti | Esc | esce dallo strumento o annulla il comando, torna a Seleziona | AutoCAD, Aurora [V] | in un campo ripristina il valore |
| Strumenti | Invio | conferma; a vuoto ripete l'ultimo strumento | AutoCAD [V] | |
| Strumenti | Canc | elimina | Windows [V] | |
| Strumenti | Ctrl tenuto / Maiusc tenuto | sospende l'aggancio / vincolo orto temporaneo | Aurora / HelioScope [V] | in Sposta Ctrl tenuto al clic fa una copia (SketchUp; Daniel, 23/10/2026) e gli agganci si spengono con F3 |
| Disegno | F3 | aggancio sì/no | AutoCAD, PVcase [V] | anche pulsante in barra di stato |
| Disegno | F8 | orto o squadra sì/no | AutoCAD, PVcase [V] | vedi decisione 1 |
| Disegno | F12 | lunghezze digitate vicino al cursore sì/no | AutoCAD [V] | |
| Disegno | F7 | griglia sì/no (se arriva) | AutoCAD [V] | |
| Modifica | F2 | rinomina | Windows, Qt [V] | libera F2 dalle viste |
| Modifica | F5 | ricalcola subito | Windows, Qt Refresh [V] | |
| Navigazione | rotella | zoom sul cursore | tutti [V] | invariato |
| Navigazione | centrale, Spazio tenuto | pan | AutoCAD, Revit, Aurora, QGIS [V] | invariato |
| Navigazione | Maiusc+centrale | orbita 3D | AutoCAD 2026, Revit [V] | oggi orbita col sinistro |
| Navigazione | destro trascinato | orbita (clic destro fermo = menu) | Onshape, Aurora, OpenSolar [V] | utile sul touchpad |
| Navigazione | doppio clic centrale | zoom estensione | AutoCAD [V] | |
| Navigazione | F | inquadra la selezione (tutto se vuota) | Blender IC, Qt Design Studio [V] | esiste già |
| Navigazione | Maiusc+Z | zoom estensione | SketchUp [V] | Z è libera |
| Navigazione | Z | zoom finestra (rettangolo) | SketchUp Z, AutoCAD Z W, Revit ZR [V] | nuova lettera |
| Navigazione | Inizio | vista Home (3D), estensione (pianta) | ViewCube, Blender [V] | Framework: Fn+← |
| Navigazione | Indietro / Avanti del mouse | vista precedente / successiva | QGIS [V]; AutoCAD ZOOM P [V] | anche «ZP» nella palette |
| Navigazione | N | nord in alto (pianta) / camera verso nord (3D) | ArcGIS N, MapLibre [V] | nuova lettera |
| Navigazione | frecce (3D) / Maiusc+frecce | orbita di 15° / di 90° (da S a E a N a O) | Onshape, FreeCAD [V] | in pianta le frecce fanno pan (QGIS, FreeCAD [V]); con Sposta attivo spostano la selezione di 10 cm, 1 m con Maiusc, 1 cm con Ctrl (PVsyst, compito 16b) |
| Navigazione | Tn7, Tn1, Tn3, Ctrl+Tn1, Ctrl+Tn3, Tn5, Tn0 | alto, da sud, da est, da nord, da ovest, prospettiva/parallela, vista dal sole | Blender [V], DIALux [V], PVsyst F6 [V-loc] | solo con tastierino; mentre si digita una lunghezza le cifre vanno al campo |
| Verifiche | Ctrl+Maiusc+M poi ↑/↓ | scorre i problemi, le viste seguono | VS Code, Solibri [V] | |
| Verifiche | Ctrl+. | «Correggi» sul problema o oggetto selezionato | VS Code Quick Fix [V] | |
| File | Ctrl+N/O/S, Ctrl+Maiusc+S, Ctrl+Z, Ctrl+Y e Ctrl+Maiusc+Z, Ctrl+X/C/V, Ctrl+A, Ctrl+F, Ctrl++ e Ctrl+- | standard | Qt StandardKey [V] | Ctrl+F cerca nel pannello attivo |
| File | Ctrl+I, Ctrl+E, Ctrl+Maiusc+N, Ctrl+Maiusc+C | import PVsyst, PDF, nuova variante, confronta varianti | esistenti | nessun conflitto di sistema |

Nota su M [D]: in AutoCAD e SketchUp M è «Sposta». Se Meridiana avrà uno strumento Sposta, conviene dargli M e spostare Misura su D (DI di AutoCAD) o T (metro di SketchUp). Deciso da Daniel il 23/10/2026 (studio 16, B.8): M Sposta, D Misura; fatto nel compito 16b, con le impostazioni alla versione 14 che portano su D chi aveva Misura su M.

**Decisioni per Daniel** (con la mia raccomandazione)
1. **F8: orto (AutoCAD) o problema successivo (VS Code)?** Raccomando l'orto. I tasti F restano una famiglia sola (ausili al disegno, come in AutoCAD e PVcase), e l'errore costa meno: premere F8 per abitudine VS Code accende l'orto (innocuo, visibile nella barra di stato); premerlo per abitudine AutoCAD a metà disegno farebbe saltare la vista su un problema. I problemi si scorrono con Ctrl+Maiusc+M e le frecce (Solibri: «move through the list of results using the arrow keys»). Chi preferisce F8 lo rimappa.
2. **Palette: Ctrl+Maiusc+P o Ctrl+K?** Raccomando Ctrl+Maiusc+P: è il tasto della palette più noto (VS Code) e lascia Ctrl+K libero per eventuali sequenze («Ctrl+K Ctrl+S»). Ctrl+K resta la seconda scelta (QGIS, e Windows lo dà libero).
3. **Modalità di vista: dove spostarle da F2/F3/F4?** Raccomando Ctrl+Maiusc+2 e Ctrl+Maiusc+3 come interruttori (solo 2D o solo 3D, di nuovo affiancate), più i tre pulsanti a scelta esclusiva nella barra. Alternative:
   - Ctrl+2/3/4: due tasti soli, ma AutoCAD e QGIS usano Ctrl+cifra per i pannelli e Ctrl+1 qui è già un pannello.
   - Tenere F2/F3/F4: c'è il precedente PVsyst (F2-F6 viste) e forse Archicad (F2 pianta, F3 3D: ricordo, non verificato [D]), ma vanno contro F2 rinomina, F3 osnap di AutoCAD e i tasti multimediali del portatile.
4. **Lettere singole: in tutta la finestra o solo con il fuoco nella vista?** Raccomando in tutta la finestra (QAction con WindowShortcut: Qt le blocca già nei campi di testo) più l'editor per rimapparle, che soddisfa WCAG 2.1.4. L'alternativa WidgetWithChildrenShortcut sulle viste è più rigorosa, ma dopo un clic sull'albero la lettera non funziona finché non si clicca nella vista.
5. **Sequenze alla Revit (ZE, ZA, ZP senza Invio)?** Sconsigliate. Con le lettere singole già usate funzionerebbero in Qt (Z farebbe da prefisso), ma un utente AutoCAD scrive «Z Invio E Invio»: l'Invio interromperebbe la sequenza e ripeterebbe l'ultimo strumento. Meglio gli alias nella palette.

**Da provare sul posto** (tastiera italiana, Windows e Niri): Ctrl+?, ?, Ctrl+Maiusc+2/3, Ctrl++ (QTBUG-101152), e che AltGr+è/AltGr++ nei campi non facciano scattare nulla (QTBUG-73247). Nell'elenco delle scorciatoie conviene scrivere che sul Framework i tasti F richiedono Fn o Fn+Esc.

### Fonti della sezione 1
- AutoCAD: https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-Customization/files/GUID-B6A9C126-230D-47F5-8973-464BC80E3736.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-ACAA0279-047D-458E-889F-60BBFDD40489.htm ; https://damassets.autodesk.net/content/dam/autodesk/www/shortcuts/autocad/autocad-shortcut-guide-en.pdf ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-OnBoarding/files/ACD_FOUNDATIONS_MAIN4.html ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-243E4DD0-8947-4905-AFE2-BE9B903A8C3F.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-3EBD4C17-F0A5-49FA-B131-4AABE2E727DB.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-7C6AE349-DDF0-40DF-9D1E-FA9702BE88BB.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-85CE824C-0AF4-4890-8487-ADBC92BF08F1.htm ; https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-B1CDEE41-F8BF-48A4-A895-273DBB295378.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Customization/files/GUID-D4CACED6-DFBA-43C3-BC42-8D980AB3AE75.htm ; https://help.autodesk.com/cloudhelp/2027/ENU/AutoCAD-LT/files/GUID-66E7DB72-B2A7-4166-9970-9E19CC06F739.htm
- Revit: https://damassets.autodesk.net/content/dam/autodesk/www/pdfs/revit-keyboard-shortcuts.pdf ; https://help.autodesk.com/cloudhelp/2026/ENU/Revit-HaveYouTried/files/GUID-D216F1C0-6346-445B-9FA6-74E5FD43D9A4.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Customize/files/GUID-DB5FC939-C9E4-418E-A9A5-44D5C05857B4.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/Revit-DocumentPresent/files/GUID-A3F4A7B5-225F-46D2-99D3-4C9771282DCA.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/Revit-GetStarted/files/GUID-42872B9F-A4DE-472A-A88C-77879ACEC93E.htm
- SketchUp: https://help.sketchup.com/en/default-keyboard-shortcuts ; https://help.sketchup.com/en/sketchup/viewing-model ; https://help.sketchup.com/en/creating-and-editing-shortcuts
- Blender: https://docs.blender.org/manual/en/latest/editors/3dview/navigate/viewpoint.html ; https://docs.blender.org/manual/en/latest/editors/3dview/navigate/navigation.html ; https://docs.blender.org/manual/en/latest/editors/3dview/navigate/introduction.html ; https://docs.blender.org/manual/en/latest/interface/keymap/blender_default.html ; https://docs.blender.org/manual/en/latest/interface/keymap/industry_compatible.html ; https://docs.blender.org/manual/en/latest/editors/preferences/input.html ; https://docs.blender.org/manual/en/latest/editors/preferences/navigation.html ; https://docs.blender.org/manual/en/latest/interface/window_system/areas.html
- FreeCAD: https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Mouse_navigation.md ; https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Navigation_Cube.md ; https://github.com/FreeCAD/FreeCAD/blob/main/src/Gui/CommandView.cpp
- QGIS: https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_gui.html ; https://docs.qgis.org/latest/en/docs/user_manual/map_views/map_view.html ; https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_configuration.html
- DIALux: https://www.dialux.com/fileadmin/user_upload/03_DIALux/DIALux_Shortcuts.pdf ; https://www.dialux.com/en-GB/dialux/version-history ; https://evo.support-en.dial.de/support/solutions/articles/9000121044-daylight ; https://www.dialux.com/en-GB/dialux/whats-new-in-dialux-evo-8
- Aurora: https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design
- HelioScope: https://help-center.helioscope.com/hc/en-us/articles/4419983762067-Keyboard-Shortcuts
- PVsyst: tutorial locali citati sopra; https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/global-scene-building-tools.html
- OpenSolar: https://support.opensolar.com/hc/en-us/articles/17311904509711-3D-Design-in-Proposal-Sharing-an-Interactive-3D-Proposal-with-Your-Customer ; PVcase: https://help.pvcase.com/hc/articles/35594698774547
- VS Code: https://code.visualstudio.com/docs/reference/default-keybindings ; https://code.visualstudio.com/docs/getstarted/tips-and-tricks ; https://code.visualstudio.com/docs/configure/custom-layout ; https://code.visualstudio.com/docs/configure/keybindings ; https://github.com/microsoft/vscode/wiki/Keybinding-Issues ; https://github.com/microsoft/vscode/issues/297698 ; https://github.com/microsoft/vscode/issues/119691
- JetBrains: https://www.jetbrains.com/help/idea/tool-windows.html ; https://www.jetbrains.com/help/idea/tool-window-layouts.html ; https://www.jetbrains.com/help/idea/mastering-keyboard-shortcuts.html ; https://www.jetbrains.com/help/idea/configuring-keyboard-and-mouse-shortcuts.html
- Windows: https://support.microsoft.com/en-us/windows/keyboard-shortcuts-in-windows-dcc61a57-8ff0-cffe-9796-cb9706c75eec ; https://learn.microsoft.com/en-us/windows/win32/uxguide/inter-keyboard ; https://learn.microsoft.com/en-us/windows/apps/design/input/keyboard-accelerators
- GNOME: https://developer.gnome.org/hig/reference/keyboard.html ; https://developer.gnome.org/hig/guidelines/keyboard.html ; https://github.com/GNOME/gsettings-desktop-schemas/blob/master/schemas/org.gnome.desktop.wm.keybindings.gschema.xml.in ; https://github.com/GNOME/mutter/tree/main/data ; https://github.com/GNOME/gnome-shell/blob/main/data/org.gnome.shell.gschema.xml.in ; https://help.gnome.org/users/gnome-help/stable/shell-keyboard-shortcuts.html.en ; https://docs.gtk.org/gtk4/class.Application.html ; https://github.com/ibus/ibus/blob/main/data/dconf/org.freedesktop.ibus.gschema.xml
- Niri: https://github.com/niri-wm/niri/blob/main/resources/default-config.kdl ; https://github.com/niri-wm/niri/blob/main/docs/wiki/Configuration:-Key-Bindings.md ; https://github.com/niri-wm/niri/blob/main/src/input/mod.rs
- Tastiera italiana: https://kbdlayout.info/kbdit ; https://learn.microsoft.com/globalization/keyboards/kbdit ; https://sources.debian.org/src/xkeyboard-config/2.48-1/symbols/it/
- Qt: https://doc.qt.io/qt-6/qkeysequence.html ; https://doc.qt.io/qt-6/qt.html#Key-enum ; https://doc.qt.io/qt-6/qt.html#ShortcutContext-enum ; https://doc.qt.io/qt-6/qevent.html ; https://doc.qt.io/qt-6/qguiapplication.html ; https://github.com/qt/qtbase/blob/dev/src/plugins/platforms/windows/qwindowskeymapper.cpp ; https://github.com/qt/qtbase/blob/dev/src/gui/platform/unix/qxkbcommon.cpp ; bug su https://qt-project.atlassian.net/browse/ : QTBUG-51848, QTBUG-73247, QTBUG-69317, QTBUG-101152, QTBUG-112736, QTBUG-116492, QTBUG-147913
- Portatili: https://github.com/FrameworkComputer/EmbeddedController/blob/fwk-lotus-azalea-19573/zephyr/program/framework/azalea/src/keyboard_customization.c ; https://community.frame.work/t/swap-function-multimedia-keys-by-default/12856 ; https://download.lenovo.com/pccbbs/pubs/t14s_gen1_x13_gen1/html_en/en/Use_the_keyboard_shortcuts_(topic)_T0000737959.html
- Wayland e accessibilità: https://wayland.app/protocols/keyboard-shortcuts-inhibit-unstable-v1 ; https://www.w3.org/WAI/WCAG22/Understanding/character-key-shortcuts.html ; https://www.etsi.org/deliver/etsi_en/301500_301599/301549/03.02.01_60/en_301549v030201p.pdf
- Solibri (frecce nell'elenco): https://help.solibri.com/hc/en-us/articles/1500004886382-Viewing-Checking-Results

---

## 2. Navigazione 2D e 3D

### 2.1 Nord, freccia del nord, azimut

| Dove | Cosa fa | Stato |
|---|---|---|
| Cartografia (Ordnance Survey) | «users will generally assume that the top of a map is north unless told otherwise»; la freccia «should ideally be small, simple and subtle» e «should not visually dominate the map»; distingue nord vero, magnetico e di griglia | [V] |
| QGIS 3.44 | freccia del nord predefinita in basso a sinistra, con «Automatic» che calcola il nord vero dal sistema di riferimento e somma la rotazione della mappa; barra di scala in alto a sinistra, «Automatically snap to round number on resize» | [V doc e sorgente] |
| Revit | «All models have 2 north orientations: Project North and True North». Il Project North è «typically based on the predominant axis of the building geometry»; il True North serve «for solar studies and rendering»; ogni pianta sceglie l'orientamento | [V] |
| AutoCAD | bussola sotto il ViewCube (NORTHDIRECTION); angoli predefiniti 0 = Est, antiorario | [V] |
| DIALux evo | «Draw north arrow» in pianta o angolo in gradi; dalla evo 8 anteprima del nord in basso a destra in 2D e 3D | [V] |
| PVsyst 8 | scena 3D: «X-direction is west, Y-direction is south, and Z points upward»; nel Module layout «A compass (top right of the drawing) indicates the orientation» | [V-loc: tutorial v8.0 p. 74; v8.1 pp. 97 e 116] |
| Mappe web | MapLibre/Mapbox: la bussola ruota con la mappa, tooltip «Drag to rotate map, click to reset north»; ArcGIS Scene Viewer: tasto N «Set the scene to north orientation», P vista perpendicolare; Google Maps: la bussola compare solo a mappa ruotata [S] | [V] |
| Disegno architettonico | nessuna norma trovata sulla posizione; prassi: una freccia per vista, nord vero sulle planimetrie per i permessi | [S] |

**Convenzioni dell'azimut**

| Fonte | 0° | Verso positivo | Stato |
|---|---|---|---|
| pvlib (motore di Meridiana) | Nord | Est, orario: N 0, E 90, S 180, O 270 | [V] |
| PVsyst 8 (emisfero nord) | Sud | Ovest: S 0, O +90, E −90 | [V-loc: v8.0 p. 74, v8.1 pp. 18 e 97; help online «positively towards the WEST»] |
| PVGIS 5.3 | Sud | «-90° is East, 0° is South and 90° is West» | [V] |
| Andrew Marsh 3D Sun-Path | Nord | «clockwise direction from due North» | [V] |
| AutoCAD | Est | antiorario | [V] |

[D] Nord di griglia e nord vero: in UTM la convergenza vale circa Δλ·sin φ, cioè circa 0,1° a Milano, −0,9° a Torino, 2,0° a Lecce. Se Meridiana usa coordinate proiettate (ortofoto, DSM), gli azimut vanno riferiti al nord vero, come fa la funzione «Automatic» di QGIS.

### 2.2 ViewCube, gizmo e cubo di navigazione

- **AutoCAD** [V]: 26 parti (6 facce, 12 spigoli, 8 vertici), frecce di rotazione di 90°, contorno continuo se la vista è una predefinita. Impostazioni: posizione, dimensione, opacità a riposo, «Snap to Closest View», «Zoom to Extents After View Change», «Use View Transitions When Switching Views», «Keep Scene Upright», «Show Compass Below the ViewCube». Menu (help AutoCAD per Mac) [S]: Home, Parallela, Prospettiva, «Set Current View as Home».
- **Revit** [V]: cubo trasparente a riposo, opaco al passaggio del mouse; la bussola sotto il cubo indica «the direction in which North is defined for the model»; un clic su una lettera cardinale ruota il modello, trascinare l'anello lo ruota attorno al pivot.
- **Blender** [V]: gizmo in alto a destra, assi X rosso, Y verde, Z blu; clic su un asse = vista allineata, secondo clic = lato opposto; pulsanti zoom, pan, camera, proiezione.
- **FreeCAD 1.x** [V]: cubo di 26 facce in alto a destra, frecce, vista opposta, mini-cubo con menu (ortogonale, prospettica, isometrica, adatta tutto, adatta selezione), opacità a riposo.
- **Onshape** [V]: frecce del cubo di 15° (Maiusc 90°, Ctrl 5°); da tastiera frecce 15°, Maiusc+frecce 90°, Ctrl+frecce 5°.
- **Qt Design Studio 4.8** [V]: «world axis helper» cliccabile, un secondo clic sullo stesso asse inverte la vista; nel sorgente (OriginGizmo.qml) è un elemento 2D Qt Quick, non una seconda View3D. Licenza GPL o commerciale: si prende l'idea, non il codice [D].

### 2.3 Barra di scala e minimappa

- QGIS [V]: barra di scala con stile, colori, unità del progetto, «snap to round number», posizione e margine; pannello Overview (Ctrl+8) con un rettangolo rosso trascinabile che rappresenta l'area visibile.
- Google Maps [S]: scala in basso a destra, un clic cambia l'unità.
- Minimappa: nessuna linea guida autorevole trovata. [D] Su una pianta di uno o pochi edifici non serve (bastano «adatta» e la cronologia delle viste); serve su impianti a terra grandi con molti sottocampi.

### 2.4 Zoom e pivot dell'orbita

| Programma | Estensione / selezione / finestra / precedente | Stato |
|---|---|---|
| AutoCAD | ZOOM All, Extents, Window, Object, Previous (fino a 10); doppio clic rotella = estensione | [V] |
| Revit | ZF/ZE, ZR/ZZ, ZP/ZC, ZA | [V] |
| SketchUp | Maiusc+Z estensione; Zoom Window; Fotocamera > Precedente; rotella sul cursore, strumento Zoom dal centro | [V] |
| Blender | Home, Tn. (selezione), Maiusc+B (regione) | [V] |
| FreeCAD | V,F; V,S; Ctrl++/Ctrl+-, PagSu/PagGiù | [V] |
| PVsyst 8.1 | F7/F8, rettangolo, Ctrl+F sugli oggetti selezionati, «Back to Default View» | [V-loc pp. 88-89] |
| Aurora | Maiusc+1 tutto, Maiusc+2 selezione | [V] |
| DIALux evo | Ctrl+* tutto, Ctrl++ e Ctrl+- | [V] |

**Pivot dell'orbita**
- AutoCAD [V]: sfera scura sul punto bersaglio; se si selezionano oggetti prima del comando, l'orbita si limita a quelli.
- Revit [V]: «The center of rotation is the center of all model geometry», oppure l'oggetto selezionato.
- Blender [V]: Alt+clic centrale fissa il punto; preferenze «Orbit Around Selection» (scomoda «for larger objects such as a terrain mesh»), «Auto Depth» («Use the depth under the mouse»), «Zoom to Mouse Position».
- FreeCAD [V]: Rotation mode Window center / Drag at cursor / Object center; «Rotation center indicator» dalla 1.0.
- Onshape [S, moderatore del forum]: raggio dal cursore; se colpisce una faccia quel punto è il pivot, altrimenti il centro dello schermo.
- PVsyst [V-loc]: «Click and drag to rotate around the current target».
- SketchUp [V]: per l'help ruota attorno al centro dell'area di disegno; per i forum il punto di partenza del trascinamento conta [S].

### 2.5 Viste standard e transizioni animate

- Viste standard [V]: Blender tastierino (7 alto, 1 fronte, 3 destra, Ctrl per gli opposti, 5 prospettiva); FreeCAD 0-6; DIALux Ctrl+tastierino; PVsyst F2-F6 con «Sun View»; Revit crea quattro prospetti «north, south, east, and west»; SketchUp menu Fotocamera.
- Transizioni [V]:
  - Blender Smooth View: «Time (in milliseconds) the animation takes when changing views ... Reduce to zero to remove the animation» (0-1000 ms; 200 ms predefiniti solo da fonte secondaria [S]).
  - AutoCAD «Use View Transitions When Switching Views»; FreeCAD anima le rotazioni non fatte col mouse; PVsyst «Enable camera animation ... may slightly reduce performance».
  - NN/g (Laubheimer 2020): «most animations should be in the range of 100-500 ms»; 200-300 ms per cambi sostanziali; «At 500ms, animations start to feel like a real drag»; ease-out; più frequente = più breve.
  - Material 3: short 50-200 ms, medium 250-400 ms, long 450-600 ms.
- Movimento ridotto [V]: WCAG 2.2 SC 2.3.3 (AAA); su Linux il portale espone `org.freedesktop.appearance` `reduced-motion`; su Windows SPI_GETCLIENTAREAANIMATION [S]; in Qt nessuna API trovata [S].

### 2.6 Mouse e touchpad

| Programma | Orbita | Pan | Zoom |
|---|---|---|---|
| AutoCAD | Maiusc+centrale [V] | centrale [V] | rotella [V] |
| Revit | Maiusc+centrale [V] | centrale [V] | rotella sul puntatore [V] |
| SketchUp | centrale [V] | centrale+sinistro, Maiusc in orbita [V] | rotella sul cursore [V] |
| Blender | centrale [V] | Maiusc+centrale [V] | rotella, Ctrl+centrale [V] |
| FreeCAD (CAD) | centrale+sinistro o +destro [V] | centrale [V] | rotella [V] |
| Fusion | Maiusc+centrale [S] | centrale [S] | rotella [S] |
| Onshape | destro [V] | Ctrl+destro o centrale [V] | rotella [V] |
| SolidWorks | centrale [S] | Ctrl+centrale [S] | rotella [S] |
| Aurora | destro orizzontale; destro verticale = inclinazione [V] | centrale, Spazio+sinistro [V] | - |
| HelioScope | Maiusc+trascina [V] | - | - |
| PVsyst 8.1 | centrale [V-loc] | Maiusc+centrale [V-loc] | F7/F8 [V-loc] |
| OpenSolar | destro [V] | sinistro [V] | rotella [V] |
| Qt OrbitCameraController | sinistro [V] | Ctrl+trascina [V] | rotella o pizzico [V] |

**Gesti del touchpad**
- Riservati al sistema [V]: Windows 11 tre e quattro dita; GNOME tre dita; Niri tre dita (aree di lavoro e scorrimento), quattro dita (panoramica), e Mod+tasti del mouse.
- Programmi [V]: Blender due dita = orbita, Maiusc+due dita = pan, Ctrl+due dita = zoom; FreeCAD stile Touchpad: Maiusc = pan, Alt = rotazione, Ctrl+Maiusc = zoom; Onshape su Windows: rotazione col tasto destro del touchpad, zoom col pizzico. Figma: pizzico e Ctrl+rotella = zoom [S].
- Cosa arriva a Qt (doc 6.12) [V]:
  - QWheelEvent: `pixelDelta` affidabile «such as macOS», «On X11 ... unreliable»; le fasi ScrollBegin/ScrollEnd «currently supported only on macOS»; `device()->type()` può valere Touchpad.
  - QNativeGestureEvent: zoom e rotazione a due dita su macOS e Wayland; Windows non citato.
  - Windows: il pizzico deve «simulate the vertical mouse wheel with the Ctrl key held down» (linee guida Microsoft per i touchpad), quindi arriva come Ctrl+rotella.
  - Qt Quick WheelHandler: di default solo `PointerDevice.Mouse`; «a conventional mouse with a wheel does not provide a scroll phase».

### 2.7 Percorso solare sovrapposto alla vista

- **Revit Sun Path** [V]: arco del giorno, analemma, area del sole nell'anno, bussola a terra («segmented circle placed on the ground plane»; «The ground compass indicates True North»); «Drag the sun along the daily path to change the time, or drag the daily path itself to change the date»; visibilità vista per vista. Dimensione e passi dell'animazione solo da fonte secondaria [S].
- **Ladybug LB SunPath** [V]: 3D o 2D (ortografica o stereografica), input `north`, `center_pt`, `scale`; punti del sole colorati con dati orari; uscita «compass» con «circles, lines and text objects that mark the cardinal directions».
- **Andrew Marsh 3D Sun-Path** [V]: data, ora, animazione di ora e data, interruttori per posizione del sole, angoli, ombre, linee giornaliere e annuali, diagrammi 2D.
- **PVsyst 8.1** [V-loc]: animazione delle ombre «By default ... December 21», icona che «locks the view to the sun's position», cursore delle ore, video (p. 99); F6 vista dal sole; diagramma di iso-ombreggiamento con le curve sovrapposte ai percorsi del sole (p. 67).
- **SketchUp** [V]: pannello Ombre con data e ora, «Use Sun for Shading»; nessun percorso solare nativo.
- **DIALux evo** [V]: data, ora e cielo nella scena di luce.
- **Solargraf** (03/2026) [V]: «Visualize sun path» con giorno e ora; il play «moves one hour per second».
- **OpenSolar** [V]: griglia 12 mesi × 24 ore; «When you click a specific hour ... that moment is ray-traced and visualized on the design canvas».
- Aurora e HelioScope: non verificato (HelioScope proietta l'ombra dei keepout per il 21/12 ore 10-14 [V, parte 3]).

### 2.8 Orientamento nella vista 3D: modelli trovati

- Anello della bussola sotto il ViewCube, con lettere cliccabili (AutoCAD, Revit) [V].
- Bussola a terra intorno al modello (Revit Sun Path, Ladybug) [V].
- Assi colorati X rosso, Y verde, Z blu (Blender, Qt AxisHelper, Qt Design Studio) [V].
- Bussola che ruota con la vista e torna al nord con un clic, più un tasto N (MapLibre, ArcGIS) [V].
- [D] Le ombre del sole all'ora corrente aiutano, ma senza etichette N/E/S/O non bastano.

### 2.9 Come farlo in Qt

- **QtQuick3D.Helpers** (6.12) [V]: 29 tipi, tra cui AxisHelper, InfiniteGrid, OrbitCameraController, WasdController, LookAtNode, ExtrudedTextGeometry; **nessun ViewCube né gizmo di navigazione**.
- **OrbitCameraController** [V]: ruota attorno al nodo `origin`, pan con Ctrl, zoom verso l'origine. Per il pivot sotto il cursore serve un controller proprio [D].
- **View3D** [V]: `pick`, `pickAll`, `rayPick`, `pickSubset` (6.8), `closestPointPick` e `pickInRect` (6.11, utile per la selezione a rettangolo), `mapFrom3DScene`/`mapTo3DScene`; `renderMode` Offscreen predefinito (il solo che «guarantees full graphics fidelity»). Esempio ufficiale «Qt Quick 3D - Picking».
- [D] Pivot sotto il cursore: alla pressione `pick(x, y)`; se colpisce si usa `scenePosition`, altrimenti l'intersezione con il piano del terreno, altrimenti il centro della selezione o del modello (il metodo di Onshape).
- [D] Etichette N/E/S/O: punti su un anello a terra, proiettati con `mapFrom3DScene` e disegnati come testo Qt Quick sopra la vista.
- [D] ViewCube: piccola View3D con la sua scena e una camera che copia la rotazione di quella principale, oppure gizmo 2D come OriginGizmo.
- **Pianta QGraphicsView** [V]: `drawForeground` lavora «in scene coordinates»; `AnchorUnderMouse` per lo zoom sul cursore; `RubberBandDrag` per lo zoom a finestra. Nel sorgente, con aggiornamento diverso da FullViewportUpdate e viewport non OpenGL, lo scorrimento sposta i pixel già disegnati (`viewport()->scroll`). [D] Una freccia del nord o una barra di scala fisse disegnate in drawForeground lascerebbero strisciate durante il pan: meglio un QWidget figlio del viewport, trasparente ai clic.

### 2.10 Cosa conviene a Meridiana

1. **Pianta** [D]
   - Freccia del nord piccola in **alto a destra**, lo stesso angolo del ViewCube in 3D, così l'orientamento si cerca sempre nello stesso posto (PVsyst la mette in alto a destra, DIALux in basso a destra, QGIS in basso a sinistra: non c'è uno standard). Ruota se la pianta è ruotata; un clic o N riporta il nord in alto. Tooltip con la convenzione dell'azimut.
   - Barra di scala in basso a sinistra con valori tondi 1-2-5 in metri; coordinate del cursore nella barra di stato; righelli facoltativi con `setViewportMargins`.
   - Nord di progetto facoltativo: ruotare la pianta lungo l'asse dell'edificio (Revit), con la freccia che continua a indicare il nord vero e l'angolo. I calcoli restano sempre sul nord vero.
   - Niente minimappa per i tetti; da valutare per gli impianti a terra grandi.
2. **3D**
   - ViewCube in alto a destra con facce **Alto, N, E, S, O** (al posto di fronte e retro: per il fotovoltaico «vista da sud» è il prospetto utile), spigoli e vertici cliccabili, anello della bussola, Home, menu (prospettiva/parallela, «Imposta la vista corrente come Home», adatta), semitrasparente a riposo.
   - Bussola a terra con N/E/S/O attorno al modello (Revit, Ladybug).
   - Pivot sotto il cursore con indicatore visibile durante l'orbita (AutoCAD, FreeCAD 1.0); con una selezione, pivot sulla selezione (Revit). Zoom verso il cursore anche in 3D.
   - Transizioni di 250-300 ms con ease-out, disattivabili, a zero se il sistema chiede movimento ridotto.
3. **Mouse e touchpad**
   - Profilo predefinito AutoCAD/Revit: centrale = pan, Maiusc+centrale = orbita, rotella = zoom sul cursore, doppio clic centrale = estensione, sinistro = selezione anche in 3D. Destro trascinato = orbita, destro fermo = menu contestuale (Onshape, Aurora, OpenSolar), utile sul portatile.
   - Profili alternativi in Preferenze (SketchUp, Blender), come gli stili di FreeCAD.
   - Touchpad: pizzico = zoom (Wayland: QNativeGestureEvent; Windows: Ctrl+rotella); due dita = pan quando Qt riconosce il touchpad [D da provare su Niri e Windows], con un'opzione in Preferenze. Mai gesti a tre o quattro dita.
4. **Sole**
   - Percorso solare alla Revit: arco del giorno, sole trascinabile sull'arco, arco trascinabile per cambiare data, bussola a terra con il nord vero; analemma facoltativo.
   - «Vista dal sole» (F6 di PVsyst) nel ViewCube e nella palette; data predefinita dell'animazione 21/12 (PVsyst) e finestra 10-14 per le verifiche d'ombra (HelioScope); riproduzione a un'ora al secondo (Solargraf).
   - Dal grafico alla vista: un clic su un'ora in Produzione mostra le ombre di quel momento nel 3D (OpenSolar).
5. **Azimut**: scrivere sempre la convenzione accanto al valore. A Daniel conviene vedere quella di PVsyst e PVGIS (0° = Sud, Ovest positivo); internamente si resta su pvlib (0° = Nord, orario).

### Fonti della sezione 2
- Nord e azimut: https://docs.os.uk/more-than-maps/geographic-data-visualisation/guide-to-cartography/north-arrows ; https://docs.qgis.org/latest/en/docs/user_manual/map_views/map_view.html ; https://github.com/qgis/QGIS/blob/master/src/app/decorations/qgsdecorationnortharrow.cpp ; https://help.autodesk.com/cloudhelp/2023/ENU/Revit-Model/files/GUID-ED5BC6E5-0B9D-477C-8F08-692A44E28646.htm ; https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-Core/files/GUID-78043EE2-114B-4F08-BFD7-7E5E429708A9.htm ; https://help.autodesk.com/cloudhelp/2021/ENU/AutoCAD-LT/files/GUID-2682959E-E66E-4381-A223-D2204AA2267A.htm ; https://help.sketchup.com/en/sketchup/casting-real-world-shadows ; https://evo.support-en.dial.de/support/solutions/articles/9000121044-daylight ; https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/global-referential-orientations.html ; https://pvlib-python.readthedocs.io/en/stable/user_guide/extras/nomenclature.html ; https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/getting-started-pvgis/pvgis-user-manual_en ; https://github.com/maplibre/maplibre-gl-js/blob/main/src/ui/control/navigation_control.ts ; https://docs.mapbox.com/mapbox-gl-js/api/markers/#navigationcontrol ; https://doc.arcgis.com/en/arcgis-online/get-started/navigate-scene.htm
- ViewCube e gizmo: https://help.autodesk.com/cloudhelp/2020/ENG/AutoCAD-Core/files/GUID-A90F5F1C-B338-4BDE-9D05-F26BFFE3B3A5.htm ; https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-787A15B5-773E-4385-A765-7889D1C64475.htm ; https://docs.blender.org/manual/en/latest/editors/3dview/navigate/introduction.html ; https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/Navigation_Cube.md ; https://cad.onshape.com/help/Content/View/view_navigation_and_the_view_cube.htm ; https://doc.qt.io/qtdesignstudio/studio-3d-editor.html ; https://github.com/qt-creator/qt-creator/blob/master/src/tools/qmlpuppet/mockfiles/qt6/OriginGizmo.qml
- Scala, zoom, pivot: https://docs.qgis.org/latest/en/docs/user_manual/introduction/general_tools.html ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-66E7DB72-B2A7-4166-9970-9E19CC06F739.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-85CE824C-0AF4-4890-8487-ADBC92BF08F1.htm ; https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-A3F4A7B5-225F-46D2-99D3-4C9771282DCA.htm ; https://help.sketchup.com/en/sketchup/viewing-model ; https://docs.blender.org/manual/en/latest/editors/3dview/navigate/navigation.html ; https://docs.blender.org/manual/en/latest/editors/preferences/navigation.html ; https://forum.onshape.com/discussion/14760/right-drag-center-of-rotation-suddenly-changed ; https://help.solidworks.com/2021/English/SolidWorks/sldworks/r_Middle_Mouse_Button.htm
- Viste e transizioni: https://docs.blender.org/manual/en/latest/editors/3dview/navigate/viewpoint.html ; https://docs.blender.org/manual/en/latest/editors/preferences/input.html ; https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-819DC7D0-FDAC-420E-ABDD-2E944211F331.htm ; https://www.nngroup.com/articles/animation-duration/ ; https://github.com/material-components/material-components-android/blob/master/lib/java/com/google/android/material/motion/res/values/tokens.xml ; https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html ; https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Settings.html
- Mouse e touchpad: https://support.microsoft.com/en-us/windows/touchpad-gestures-for-windows-a9d28305-4818-a5df-4e2b-e5590f850741 ; https://help.gnome.org/users/gnome-help/stable/touchscreen-gestures.html.en ; https://github.com/YaLTeR/niri/blob/main/docs/wiki/Gestures.md ; https://docs.blender.org/manual/en/latest/getting_started/configuration/hardware.html ; https://help.figma.com/hc/en-us/articles/1500004414582 ; https://doc.qt.io/qt-6/qwheelevent.html ; https://doc.qt.io/qt-6/qnativegestureevent.html ; https://learn.microsoft.com/en-us/windows/win32/wintouch/windows-touch-gestures-overview ; https://learn.microsoft.com/en-us/previous-versions/windows/hardware/design/dn613883(v=vs.85) ; https://doc.qt.io/qt-6/qml-qtquick-wheelhandler.html ; https://help-center.helioscope.com/hc/en-us/articles/4419983762067-Keyboard-Shortcuts
- Sole: https://help.autodesk.com/cloudhelp/2020/ENU/Revit-Analyze/files/GUID-CA024825-3211-4354-AC06-D81751AADA1A.htm ; https://github.com/ladybug-tools/ladybug-primer/blob/master/text/components/SunPath.md ; https://andrewmarsh.com/apps/staging/sunpath3d.html ; https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/view-tools/shadows-drawing.html ; https://www.solargraf.com/help-center/article/sun-path-animation-in-solargraf ; https://support.opensolar.com/hc/en-us/articles/4406938900505-How-to-Interpret-3D-Shading-Analysis
- Qt: https://doc.qt.io/qt-6/qtquick3d-helpers-qmlmodule.html ; https://doc.qt.io/qt-6/qml-qtquick3d-helpers-orbitcameracontroller.html ; https://doc.qt.io/qt-6/qml-qtquick3d-view3d.html ; https://doc.qt.io/qt-6/qtquick3d-picking-example.html ; https://doc.qt.io/qt-6/qgraphicsview.html ; https://github.com/qt/qtbase/blob/dev/src/widgets/graphicsview/qgraphicsview.cpp
- Locale: l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\pvsyst-tutorial-v8-1-grid-connected-en.pdf (pp. 18, 67, 88-90, 97, 99, 116, 118)

---

## 3. Criticità nelle viste

### 3.1 Programmi fotovoltaici

| Programma | Cosa mostra e come | Stato |
|---|---|---|
| Aurora, sovrapposizioni | controllo continuo mentre si posano i moduli: «Panels are yellow when overlapping setbacks»; «Panels are red when overlapping other panels or obstructions»; non blocca («you will still be able to finish your design and simulate»); si spegne da View settings | [V, 04/2026] |
| Aurora, percorsi antincendio | i moduli sopra un percorso «will turn yellow»; setback gialli, percorsi viola | [V] |
| Aurora, stringhe | mentre si trascina: «Red means the string length is too short or too long ... Green means the string length is valid» | [V, 09/2026] |
| Aurora, validazione | «Any errors will be presented within a new 'Instant Plan Set' side panel within Design Mode, allowing you to review and adjust in-context» | [V] |
| Aurora, irraggiamento | mappa attivata con il tasto i; al passaggio del mouse kWh, solar access, TOF e TSRF; «Yellow corresponds to higher solar potential while red corresponds to lower» | [V, 10/2026] |
| Aurora, simulazione | gli avvisi non bloccano (es. ore con tensione di stringa fuori finestra); gli errori impediscono il calcolo | [V] |
| HelioScope | moduli non in stringa «highlighted in orange and will not have the green string wire shown»; ombra per modulo «red representing greater shading and blue indicating less shading»; cursore di soglia che toglie i moduli più ombreggiati; calcolo rapido su «every hour of the 15th day of each month»; lunghezza di stringa fuori range = avviso, non blocco | [V] |
| OpenSolar | «If an issue is detected, the blue info icon turns red. Hover over it to view the specific warning»; avvisi DC/AC sotto 75%, sopra 133% e 150%; il progettista «can override warnings»; heatmap «yellow-to-red»; 6 punti per modulo: rosso ombra diretta, arancio stringa penalizzata, verde pieno sole | [V, 08/2026] |
| PVcase | perdita annua per modulo «as a percentage value, as a color gradient, or both»; filtro min/max e «Delete modules in this range»; «Roof health check»: «how many need your attention. You can click on Highlight» | [V, 2026] |
| PVsyst | «Messages in black are additional information», «Warnings in orange indicate design imperfections, but the system is still acceptable», «Errors in red mean serious mistakes, which will prevent the execution of the simulation» (v7, p. 13); soglie modificabili (v8.1, p. 11) | [V-loc] |
| PVsyst, Module layout | pannello blu che «continuously provides information about the status ... and the actions to be performed»; stringhe con «a different color depending on its number (colors 1 to 10)»; moduli non assegnati bianchi; selezione rossa (pp. 108-127) | [V-loc] |
| PVsyst, scena | tracker di riferimento verde, vicini che lo ombreggiano arancioni «in both the window and the scene»; elenco oggetti Ctrl+G: «Selecting an object in the list also highlights it in the shading scene» (pp. 78-79) | [V-loc] |
| DIALux evo | falsi colori: 27 colori in 3 fasce; «Right-click on the colour scale to set the value and assign a new colour, e.g. to clearly highlight limit values» | [V] |

### 3.2 CAD, BIM e verifica dei modelli

- **Revit** (help 2027) [V]: l'avviso compare in basso a destra e gli elementi coinvolti «are highlighted in a user-definable color»; «warning messages do not prohibit the current action»; gli errori possono richiedere di annullare l'ultima azione. Review Warnings (Gestisci > Interroga) con albero, «Show» che sceglie una vista adatta (vista propria, pianta, prospetto, tavola, 3D) e «Delete Checked»; dall'oggetto, «Show Related Warnings». Nessun interruttore nativo per vedere gli avvisi nella vista: l'idea «Reveal Warnings Tool» (2019, «similar to Show Worksets, with color-coding based on warning severity») è ferma a 27 voti.
- **Navisworks Clash Detective** [V]: «Highlight all clashes» con colori per stato; «Dim Other» o «Hide Other»; «Transparent Dimming»; «Auto Reveal»; «Animate Transitions» fra un conflitto e l'altro; stati New, Active, Reviewed, Approved, Resolved.
- **Solibri** [V]: gravità critica, moderata, bassa con icone che salgono sulla categoria («At least one issue in the category is 'Critical'»); problemi accettabili o rifiutabili; «You can move through the list of results using the arrow keys and zoom in on the components by pressing Z».
- **Fusion** [V]: «a yellow warning or red error highlights the feature in the Timeline»; schizzo completamente vincolato nero con lucchetto.
- **Onshape** [V]: testo arancione nella lista delle feature, filtri «:errors» e «:warnings», triangolo giallo per selezioni mancanti, campo non valido «outlined in red»; schizzi blu (non definito), nero (definito), rosso (sovravincolato), con Previous/Next nel Profile inspector; mappe di analisi con Viridis.
- **SolidWorks 2024** [V]: blu sotto definito, nero definito, giallo conflitti, rosso sovradefinito.

### 3.3 IDE e GIS

- **VS Code** [V]: la barra di stato mostra «a summary of all errors and warnings counts», un clic apre Problemi; problemi «rendered inline with the text and in the overview ruler»; F8/Maiusc+F8 su tutti i file, Alt+F8 nel file con un riquadro in linea e le Code Actions; decorazioni con il numero di errori nell'Explorer (1.20); filtro di testo (1.23) e per tipo «errors, warnings, and information» (1.41).
- **JetBrains 2026.2** [V]: widget in alto a destra che «displays the number of problems of each severity detected in the current file»; strisce nella barra di scorrimento; F2/Maiusc+F2 in ordine «errors > warnings > weak warnings»; pannello Problems con filtri e raggruppamento per gravità.
- **QGIS Topology Checker** [V]: tabella degli errori, «Show errors on the canvas», «Clicking a row in the table will zoom the map canvas to the concerned feature», filtro per regola.

### 3.4 Buone pratiche trasversali

| Regola | Testo | Stato |
|---|---|---|
| Non solo il colore | WCAG 2.2 SC 1.4.1 (A): «Color is not used as the only visual means of conveying information» | [V] |
| Contrasto | SC 1.4.11 (AA): almeno 3:1 per le «Parts of graphics required to understand the content» | [V] |
| Messaggi d'errore | NN/g 2023: «Display the error message close to the error's source»; «Use noticeable, redundant, and accessible indicators»; «Offer constructive advice» | [V] |
| Indicatori | NN/g 2024: «in close proximity to that element», condizionali e passivi | [V] |
| Errore o avviso | Microsoft: «if an issue blocks the user from proceeding, it is presented as an error; if the user can proceed, it's a warning»; «Warnings are not 'softened' errors»; «in-place errors always need error icons» | [V] |
| Non esagerare | Microsoft: un avviso deve indicare un rischio, servire subito, essere raro; «Display only one warning message per condition» | [V] |
| Contenuto | Microsoft: problema, causa, soluzione; «It's usually better to prevent an error than to report one» | [V] |
| Banner persistente | WinUI InfoBar: livelli Error, Warning, Success, Informational; «Icons and color should not be the only UI components signifying meaning» | [V] |
| Mappe di colore | matplotlib: mappe percettivamente uniformi; in jet la luminosità «vary widely»; evitare rosso e verde insieme; cividis dà una «nearly-identical visual-data interpretation» a chi non distingue rosso e verde (PLOS ONE 2018); ColorBrewer filtra «colorblind safe» | [V] |

Osservazione [D]: Aurora e OpenSolar usano scale dal giallo al rosso, HelioScope dal rosso al blu, e nessuna loro guida parla di daltonismo.

### 3.5 Cosa conviene a Meridiana

1. **Tre livelli**, come PVsyst e Windows: Errore (il risultato non vale o il calcolo non parte), Avviso (si procede), Informazione. Ogni livello ha icona e forma proprie oltre al colore (WCAG 1.4.1); soglie modificabili nelle impostazioni (PVsyst).
2. **Criticità dentro le viste**, controllate dal vivo e senza bloccare (Aurora), con un interruttore Vista > Mostra criticità:
   - moduli gialli in una fascia di rispetto e rossi se sovrapposti (Aurora), con tratteggio o icona oltre al colore [D];
   - distanza violata disegnata come quota rossa con il valore misurato e il minimo richiesto [D];
   - badge con l'icona della gravità sul baricentro dell'oggetto, con il numero se i problemi sono più d'uno, uguale in pianta e in 3D [D].
3. **Stringhe**: colori numerati per stringa (PVsyst, 10 colori); moduli non assegnati evidenziati (HelioScope); durante il cablaggio verde o rosso per la lunghezza valida (Aurora), con un'icona per i daltonici [D].
4. **Verifiche legate alla vista in due direzioni**: le Verifiche diventano anche un pannello in basso (Ctrl+J) visibile nella scheda Modello. La selezione nell'elenco evidenzia l'oggetto in pianta e in 3D, con «attenua il resto» e transizione animata (PVsyst, QGIS, Revit, Navisworks); dall'oggetto si arriva ai suoi avvisi (Revit «Show Related Warnings»). Filtri per gravità e per regola (VS Code, Onshape).
5. **Conteggi**: errori e avvisi nella barra di stato, cliccabili (VS Code); badge sugli elementi dell'albero Progetto, propagati al genitore (VS Code, Solibri).
6. **Navigazione**: Ctrl+Maiusc+M porta il fuoco sull'elenco, le frecce scorrono e le viste seguono (Solibri); Ctrl+. applica «Correggi» (VS Code). F8 solo se Daniel lo vuole (vedi 1.11).
7. **Mappe per modulo**: valore al passaggio del mouse (Aurora), gradiente, legenda con soglie modificabili e «seleziona sotto soglia» (PVcase, HelioScope, DIALux). Mappa viridis o cividis invece del giallo-rosso, salvo i colori di stato.
8. **Risultati obsoleti**: un banner fisso «Risultati da aggiornare» (InfoBar, Excel), non un avviso che appare e scompare.
9. **Testi**: problema, causa, soluzione; un messaggio per condizione; pochi avvisi, altrimenti si smette di leggerli (Microsoft).

### Fonti della sezione 3
- Aurora: https://help.aurorasolar.com/hc/en-us/articles/11977025528595-Panel-Overlap-Validation ; https://help.aurorasolar.com/hc/en-us/articles/13351033549715 ; https://help.aurorasolar.com/hc/en-us/articles/13139582090131-Stringing-and-Connecting ; https://help.aurorasolar.com/hc/en-us/articles/44272536242067-Obstructions ; https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine ; https://help.aurorasolar.com/hc/en-us/articles/33543611295379-Instant-Plan-Sets ; https://help.aurorasolar.com/hc/en-us/articles/21137017211411-How-to-leverage-an-irradiance-map ; https://help.aurorasolar.com/hc/en-us/articles/15453305274643-Assessing-Shading-Threats-in-Sales-Mode
- HelioScope: https://help-center.helioscope.com/hc/en-us/articles/8536897333395 ; https://help-center.helioscope.com/hc/en-us/articles/7835499970707-Optimize-shaded-modules ; https://help-center.helioscope.com/hc/en-us/articles/7900012596755-Keepout-from-shade ; https://help-center.helioscope.com/hc/en-us/articles/8198878093971-Shade-Reports ; https://help-center.helioscope.com/hc/en-us/articles/8198326521491-Stringing-in-HelioScope
- OpenSolar: https://support.opensolar.com/hc/en-us/articles/12382487281935-Inverter-sizing-and-stringing-recommendations ; https://support.opensolar.com/hc/en-us/articles/5548229048079-Heatmaps-on-OpenSolar ; https://support.opensolar.com/hc/en-us/articles/4406938900505-How-to-Interpret-3D-Shading-Analysis
- PVcase: https://help.pvcase.com/hc/en-us/articles/35594124325907-Shading-analysis ; https://help.pvcase.com/hc/en-us/articles/43635017183507-Release-notes-1-53 ; https://help.pvcase.com/hc/en-us/articles/44029863872019-Release-notes-1-54 ; https://help.pvcase.com/hc/en-us/articles/35594628496019-Shading-objects-Shading-analysis
- PVsyst locale: l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\pvsyst-tutorial-v7-grid-connected-1-en.pdf (pp. 10, 13) ; l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\pvsyst-tutorial-v8-1-grid-connected-en.pdf (pp. 11, 67, 78-85, 108-129)
- DIALux: https://evo.support-en.dial.de/support/solutions/articles/9000115683-false-colours
- Revit: https://help.autodesk.com/cloudhelp/2027/ENU/Revit-Troubleshooting/files/GUID-63125823-1B92-4DAF-9AC4-71B7D638FD10.htm ; https://help.autodesk.com/cloudhelp/2027/ENU/Revit-Troubleshooting/files/GUID-E946814B-D6BD-4296-864C-A7FD25BCD82E.htm ; https://help.autodesk.com/cloudhelp/2027/ENU/Revit-Troubleshooting/files/GUID-F0945713-4389-4F8E-B5DB-DCE03A8C1ADF.htm ; https://help.autodesk.com/cloudhelp/2027/ENU/Revit-Troubleshooting/files/GUID-42294460-2388-44D4-B68E-74943FC5179B.htm ; https://help.autodesk.com/cloudhelp/2027/ENU/Revit-Troubleshooting/files/GUID-04576598-F22B-41C6-98CC-A91AF5FE538B.htm ; https://forums.autodesk.com/t5/revit-ideas/reveal-warnings-tool/idi-p/8993348
- Navisworks, Solibri: https://help.autodesk.com/cloudhelp/2022/ENU/Navisworks/files/GUID-FCC9E5E1-2717-48D2-8DBE-2055CF2DC61E.htm ; https://help.solibri.com/hc/en-us/articles/1500004886382-Viewing-Checking-Results
- Fusion, Onshape, SolidWorks: https://help.autodesk.com/cloudhelp/ENU/Fusion-Model/files/SLD-COMPUTE-ALL.htm ; https://help.autodesk.com/cloudhelp/ENU/Fusion-Sketch/files/SKT-FULLY-DEFINE-CONSTRAIN-SKETCH.htm ; https://cad.onshape.com/help/Content/Home/error_indicators.htm ; https://cad.onshape.com/help/Content/feature_list.htm ; https://cad.onshape.com/help/Content/Home/colors.htm ; https://help.solidworks.com/2024/English/SolidWorks/sldworks/c_Sketch_Geometry_Status.htm
- IDE e GIS: https://code.visualstudio.com/docs/editing/editingevolved ; https://code.visualstudio.com/docs/reference/default-keybindings ; https://github.com/microsoft/vscode-docs/blob/main/release-notes/v1_20.md ; https://github.com/microsoft/vscode-docs/blob/main/release-notes/v1_41.md ; https://www.jetbrains.com/help/idea/file-and-project-wide-analysis.html ; https://www.jetbrains.com/help/idea/problems-tool-window.html ; https://docs.qgis.org/latest/en/docs/user_manual/plugins/core_plugins/plugins_topology_checker.html ; https://docs.qgis.org/latest/en/docs/user_manual/plugins/core_plugins/plugins_geometry_checker.html
- Buone pratiche: https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html ; https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html ; https://www.nngroup.com/articles/error-message-guidelines/ ; https://www.nngroup.com/articles/indicators-validations-notifications/ ; https://www.nngroup.com/articles/ten-usability-heuristics/ ; https://learn.microsoft.com/en-us/windows/win32/uxguide/vis-std-icons ; https://learn.microsoft.com/en-us/windows/win32/uxguide/mess-warn ; https://learn.microsoft.com/en-us/windows/win32/uxguide/mess-error ; https://learn.microsoft.com/en-us/windows/apps/design/controls/infobar ; https://matplotlib.org/stable/users/explain/colors/colormaps.html ; https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0199239 ; https://colorbrewer2.org/

---

## 4. Pannelli e moduli delle proprietà

### 4.1 Riaprire i pannelli chiusi e salvare i layout

| Dove | Cosa fa | Stato |
|---|---|---|
| Qt QDockWidget | `toggleViewAction()`: «Returns a checkable action that can be added to menus and toolbars so that the user can show or close this dock widget»; il testo è il titolo del pannello | [V] |
| Qt QMainWindow | `createPopupMenu()` è il menu del clic destro (oggi l'unico modo di riaprire i pannelli in Meridiana); `saveState`/`restoreState` con numero di versione: se non coincide lo stato resta com'è; serve un `objectName` unico per pannello e barra | [V] |
| Qt su Wayland | «Qt will ignore calls to set the top-level position»: un pannello flottante ritrova la dimensione, non la posizione | [V] |
| Niri | dalla 25.01 le finestre con un genitore (dialoghi) nascono flottanti; un QDockWidget staccato probabilmente si comporta così, da provare | [V] / [D] |
| Visual Studio | Window > Save / Apply / Manage Window Layout (Ctrl+Alt+1...0, massimo 10); Reset Window Layout; nel 2008-2010 layout separati per progettazione e debug, con lamentele per le finestre che si spostano da sole | [V] |
| JetBrains | View > Tool Windows; Maiusc+F12 ripristina il layout Default, che non si modifica; Window > Layouts per salvarne altri | [V] |
| VS Code | View > Appearance; «View: Reset View Locations»; Customize Layout > Restore Defaults | [V] |
| AutoCAD | «Press Ctrl+1 to easily show or hide the Properties palette»; Ctrl+0 schermo pulito; Workspace che «store the current state of the AutoCAD UI» | [V] |
| Revit | View > Windows > User Interface con le caselle Properties e Project Browser; la palette resta dov'era tra una sessione e l'altra | [V] |
| Blender | workspace come «predefined window layouts... geared towards a specific task», salvati nel file | [V] |
| QGIS | Vista > Pannelli e Barre degli strumenti; Ctrl+Tab nasconde i pannelli; Ctrl+Maiusc+Tab lascia solo la mappa | [V] |
| Qt Advanced Docking System | LGPL 2.1, layout con nome e auto-hide, pacchetto PySide6-QtAds; Wayland nativo dalla 5.0 | [V] |

Linee guida sui menu [V]:
- Apple: nel menu Vista «Show/Hide Sidebar», con il testo che riflette lo stato; «Avoid hiding the sidebar by default to ensure that it remains discoverable»; nei menu si scrive «Show Inspector», senza «panel».
- Microsoft: il menu Vista standard contiene barre degli strumenti, barra di stato, zoom, schermo intero (F11), aggiorna (F5); «Don't change menu item names dynamically... use bullets and checkmarks». Quindi Windows vuole la spunta, Apple il testo Mostra/Nascondi: la QAction spuntabile di Qt segue già Windows e GNOME.
- GNOME: «Side Pane | F9 | Toggles utility pane visibility»; «if the pane affects the main view, place it on the left... subordinate... on the right».

### 4.2 Pannelli che cambiano con la scheda o con la selezione

- Microsoft (finestre delle proprietà) [V]: l'ispettore mostra «Properties for the current selection» con «immediate commit... no need for OK, Cancel, and Apply». Le schede che non c'entrano e che l'utente non si aspetta si tolgono («remove the tab»); quelle che si aspetta si mostrano con i controlli disattivati e il motivo («Include text explaining why»).
- Apple [V]: «An inspector displays the details of the currently selected item, automatically updating its contents».
- Office [V]: schede contestuali nascoste che compaiono con la selezione (es. la tabella) e schede «modal» per le modalità (anteprima di stampa).
- Blender [V]: workspace per attività e «Visible Tabs» nell'editor Properties.
- NN/g [V]: l'errore di modalità nasce «when the user is not aware of the currently active mode» (2019); «Follow platform and industry conventions» e tenere gli elementi sempre nello stesso posto (2021); «Initially, show users only a few of the most important options» (2006).

Nascondere albero e proprietà nelle schede dei risultati? [D sulle fonti sopra]
- A favore: più spazio ai grafici; è la regola Microsoft del «togli ciò che non si applica»; ha precedenti nei layout per modalità di Visual Studio e nei workspace di Blender.
- Contro: le finestre che si spostano da sole disorientano (lamentele su Visual Studio); Apple chiede di non nascondere la barra laterale; nelle schede Bilancio e Verifiche l'albero serve per filtrare per sottocampo o variante e per arrivare all'oggetto.

### 4.3 Sezioni comprimibili, ricerca, selezione multipla

- NN/g «Accordions on Desktop» (2023) [V]: più sezioni aperte insieme, icona freccia o più, titolo e icona cliccabili, Espandi tutto e Comprimi tutto. Non parla di ricordare lo stato; Microsoft chiede di ricordare per utente la scheda aperta per ultima [V], che vale per analogia.
- Blender [V]: clic sul titolo apre o chiude, Ctrl+clic apre solo quello, trascinare sui titoli ne apre o chiude molti; ricerca Ctrl+F: «Matching properties remain visible; others are grayed out... highlights the first match and switches to the relevant tab».
- Unreal 5.8 [V]: casella «Search Details» e segno sui valori diversi dal predefinito. VS Code [V]: filtro @modified, barra colorata sulle voci cambiate, «Reset Setting».

| Selezione multipla | Come si mostra | Stato |
|---|---|---|
| AutoCAD | solo le proprietà comuni, «\*VARIES\* is shown» dove differiscono; filtro per tipo con il numero di oggetti | [V] |
| Revit | filtro con categoria e numero di elementi; proprietà d'istanza comuni; «<varies>» solo da fonte secondaria | [V] / [S] |
| Unity | «For property values that are different... the Inspector displays a dash (-)» | [V] |
| Microsoft | «Display the common properties... Where the property values differ... use a mixed state» | [V] |
| Qt | QCheckBox a tre stati; `QAbstractSpinBox.specialValueText` per mostrare un testo come «*varia*» | [V] |

### 4.4 Modifica dal vivo o conferma con Invio

- Microsoft [V]: gli ispettori applicano subito; WinUI NumberBox: ValueChanged dopo Invio, clic sulle frecce o perdita del fuoco; con AcceptsExpression calcola espressioni come «1+2^2».
- GNOME (wiki, bozza 2024) [V]: applicare subito quando si può; con un pulsante se serve «more than about one second»; nei campi di testo niente validazione né applicazione finché il fuoco non passa altrove.
- Apple [V]: validare «when people switch to another field».
- Revit [V]: conferma con «Move the cursor off the palette», «Press Enter», «Click Apply»; «Press Esc twice» annulla.
- Visual Studio (rinomina sul posto) [V]: Invio conferma, Esc annulla, clic fuori conferma.
- Qt [V]: `keyboardTracking` acceso di base (scrivendo 600 emette 6, 60, 600), spento emette solo con Invio, uscita o frecce; `editingFinished` all'uscita e con Invio; `correctionMode` torna all'ultimo valore valido; in QLineEdit Esc non fa nulla di suo; nelle viste a elementi (Qt 6.10+) Esc chiude l'editor «without committing»; i cursori emettono durante il trascinamento con `tracking` acceso e hanno `sliderReleased`.

### 4.5 Rotella sopra campi e combo in un'area che scorre

**Qt Widgets oggi** [V sorgente e bug]
- QAbstractSpinBox: politica `Qt::WheelFocus`; `wheelEvent` cambia sempre il valore e accetta l'evento senza guardare il fuoco; Ctrl moltiplica il passo per 10.
- QComboBox: `WheelFocus`; la rotella cambia voce ed emette anche `activated`, se lo stile lo consente: `SH_ComboBox_AllowWheelScrolling` è «on by default in all styles except the Mac style».
- QAbstractSlider: non guarda il fuoco.
- QApplication: l'evento va al widget sotto il puntatore e, **prima** di consegnarlo, Qt dà il fuoco ai widget con WheelFocus; risale ai genitori solo se nessuno lo accetta.
- Segnalazioni: QTBUG-19730 (2011, combo senza fuoco) chiusa il 16/10/2026 come fuori ambito senza correzione; QTBUG-12309 (spinbox); QTBUG-96235 (con StrongFocus il testo resta selezionato).
- Qt Quick Controls: `wheelEnabled` «The default value is false»: nella libreria più recente Qt ha scelto che i controlli non reagiscano alla rotella.

| Sistema | Comportamento | Stato |
|---|---|---|
| GTK 3 | spin button e combo cambiano valore con la rotella | [V sorgente] |
| GTK 4 | spin button come GTK 3; GtkScale cambia sempre; GtkDropDown (la nuova combo) ignora la rotella | [V sorgente] |
| Win32 | la rotella va alla finestra con il fuoco e risale; una combo chiusa passa alla voce successiva; in Windows 10/11 «Scroll inactive windows when I hover over them» | [V] |
| Guida Windows 7 | chiedeva il contrario: agire sul controllo sotto il puntatore «without clicking or having input focus», pensato per i controlli che scorrono | [V] |
| WinUI NumberBox | la rotella cambia il valore «when the NumberBox is in focus» | [V] |
| macOS | le combo native ignorano la rotella; WebKit: il cambio con la rotella «doesn't match any of Apple's platform behaviors» | [V] |
| Firefox | dalla **130** (e ESR 128.2) la rotella non cambia più i campi number e range: «users seem to be surprised» | [V] |
| Chrome, Edge, Safari | cambio solo con fuoco, puntatore sopra e un ascoltatore wheel; WebKit l'ha tolto il 23/01/2025 | [V] |
| GOV.UK (2020) | «Users can accidentally increase or decrease the number using the scroll wheel» | [V] |

**Ricetta Qt** [V logica dal sorgente; comportamento in PySide6 D]
1. Su spinbox, combo e cursori dentro aree che scorrono: `setFocusPolicy(Qt.StrongFocus)`, altrimenti la rotella dà il fuoco prima di arrivare e `hasFocus()` risulta già vero.
2. In `wheelEvent`: se `not self.hasFocus()`, `event.ignore()` e uscire (l'area scorre); altrimenti `super().wheelEvent(event)`. In alternativa un filtro d'applicazione che chiama `event.ignore()` e restituisce `True`. Un filtro che restituisce solo `True` blocca anche lo scorrimento dell'area.
3. Per il testo che resta selezionato (QTBUG-96235) provare `SH_SpinBox_SelectOnStep` [D].

### 4.6 Annulla e ripeti

- Qt [V]: QUndoStack unisce comandi consecutivi con `id()` e `mergeWith()`; `beginMacro()`/`endMacro()` fanno un passo solo di più comandi; `setClean()`/`cleanIndex()`/`cleanChanged` per il «modificato»; `undoLimit` «default value is 0... no limit»; QUndoView mostra la cronologia; Redo = Ctrl+Y e Ctrl+Maiusc+Z su Windows, Ctrl+Maiusc+Z su GNOME.
- Apple [V]: dire cosa si annulla («Undo Typing»); «Show the results of an undo or redo»; «Avoid placing unnecessary limits»; valutare di raggruppare i piccoli ritocchi successivi alla stessa proprietà.
- GNOME e Microsoft [V]: «undo is typically a better option than a confirmation dialog»; conferme solo per azioni gravi o non annullabili, altrimenti «Provide undo».
- AutoCAD UNDO [V]: Auto (una macro = un passo), Control > Combine (zoom e pan consecutivi = un passo), BEgin/End, Mark/Back: in AutoCAD zoom e pan rientrano nell'annulla.
- Blender [V]: Undo History, Adjust Last Operation (F9), limite dei passi; nel sorgente la selezione è annullabile, la rotazione e lo zoom della vista no.
- Revit: «Previous Pan/Zoom» separato dall'annulla [S].

### 4.7 Cosa conviene a Meridiana

1. **Menu Vista > Pannelli** con le `toggleViewAction`: Progetto (Ctrl+B), Proprietà (Ctrl+1), Verifiche (Ctrl+J), Cronologia (QUndoView); poi Schermo pulito (Ctrl+0) e «Ripristina disposizione predefinita». Al primo avvio si salva lo stato di fabbrica per il ripristino; `saveState` con versione da aumentare quando cambiano i pannelli; `objectName` unici.
2. **Su Niri** si ripristinano solo le dimensioni; provare un pannello staccato e, se si comporta male, disattivare `DockWidgetFloatable` su Wayland [D].
3. **Una sola disposizione dei pannelli, ispettore contestuale** [D]: nelle schede dei risultati il pannello Proprietà mostra le impostazioni del risultato (periodo, variante, unità, filtri) oppure si disattiva con il motivo; l'albero resta per filtrare per sottocampo e variante. Niente pannelli che spariscono da soli; se Daniel vuole più spazio, Ctrl+0 o Ctrl+B/Ctrl+1 bastano.
4. **Proprietà**: sezioni comprimibili, più aperte insieme, stato ricordato per tipo di oggetto, Espandi/Comprimi tutto; campo di ricerca in cima (Ctrl+F) che lascia visibili le corrispondenze e attenua le altre (Blender); segno sui valori diversi dal predefinito con «Ripristina» (Unreal, VS Code).
5. **Selezione multipla**: proprietà comuni, «*varia*» dove i valori differiscono, filtro per tipo con il numero di oggetti (AutoCAD, Revit), caselle a tre stati.
6. **Conferma** con Invio o uscita dal campo; Esc ripristina il valore; `keyboardTracking` spento; `editingFinished` come unico segnale di commit; anteprima dal vivo solo per cursori e trascinamenti. Ogni conferma è un comando QUndoStack. Facoltativo: espressioni nei campi numerici («12,5*3»), come NumberBox [D].
7. **Rotella**: ricetta StrongFocus + `ignore()` su tutti i campi numerici, combo e cursori dentro aree che scorrono; con il fuoco, Ctrl+rotella per passi grandi. È la scelta di Firefox 130, WebKit, WinUI e Qt Quick Controls.
8. **Annulla** [D sulle fonti sopra]: un'intenzione = un passo; trascinamenti con anteprima e un solo comando al rilascio; modifiche multiple e riempimento delle falde in una macro; viste fuori dall'annulla, con «Vista precedente» (tasti del mouse, «ZP» nella palette); selezione non annullata, ma l'oggetto ripristinato viene selezionato e mostrato (Apple); voci di menu parlanti («Annulla Sposta falda»); nessun limite (QUndoStack 0); `cleanIndex` per l'asterisco nel titolo.

### Fonti della sezione 4
- Qt: https://doc.qt.io/qt-6/qdockwidget.html ; https://doc.qt.io/qt-6/qmainwindow.html ; https://doc.qt.io/qt-6/qwidget.html ; https://doc.qt.io/qt-6/application-windows.html ; https://doc.qt.io/qt-6/qabstractspinbox.html ; https://doc.qt.io/qt-6/qlineedit.html ; https://doc.qt.io/qt-6/qabstractitemdelegate.html ; https://doc.qt.io/qt-6/qabstractslider.html ; https://doc.qt.io/qt-6/qcheckbox.html ; https://doc.qt.io/qt-6/qml-qtquick-controls-control.html ; https://doc.qt.io/qt-6/qundostack.html ; https://doc.qt.io/qt-6/qundocommand.html ; https://doc.qt.io/qt-6/qundoview.html ; https://bugreports.qt.io/browse/QTBUG-19730 ; https://bugreports.qt.io/browse/QTBUG-12309 ; https://bugreports.qt.io/browse/QTBUG-96235 ; https://bugreports.qt.io/browse/QTBUG-10708 ; https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System
- Niri: https://github.com/YaLTeR/niri/wiki/Floating-Windows
- IDE, CAD, altri: https://learn.microsoft.com/visualstudio/ide/customizing-window-layouts-in-visual-studio ; https://learn.microsoft.com/en-us/archive/blogs/zainnab/window-layouts-the-four-modes ; https://www.jetbrains.com/help/idea/tool-windows.html ; https://www.jetbrains.com/help/idea/tool-window-layouts.html ; https://code.visualstudio.com/docs/configure/custom-layout ; https://code.visualstudio.com/docs/getstarted/userinterface ; https://code.visualstudio.com/docs/configure/settings ; https://help.autodesk.com/cloudhelp/2022/ENU/AutoCAD-DidYouKnow/files/GUID-94C065AB-FF9E-4752-B778-23D2FBB87E18.htm ; https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DidYouKnow/files/GUID-48F7D8A3-DD65-4940-918B-8D26FBBE5D67.htm ; https://help.autodesk.com/cloudhelp/2024/ENU/AutoCAD-DidYouKnow/files/GUID-1D87D5C3-21BC-499E-A560-79592348D47E.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/Revit-GetStarted/files/GUID-C8D3E5A6-02A5-43A9-AFFC-D49DD27398B1.htm ; https://help.autodesk.com/cloudhelp/2023/ENU/Revit-GetStarted/files/GUID-A764EA7A-FE26-469B-857C-F3A70812FC34.htm ; https://help.autodesk.com/cloudhelp/2024/ENU/Revit-GetStarted/files/GUID-20EFAA24-2439-4ECA-97CD-4F32916F4CBE.htm ; https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-LT/files/GUID-2729A466-B199-4840-B92B-4D8A38A8ADB8.htm ; https://docs.blender.org/manual/en/latest/interface/window_system/workspaces.html ; https://docs.blender.org/manual/en/latest/editors/properties_editor.html ; https://docs.blender.org/manual/en/latest/interface/window_system/tabs_panels.html ; https://docs.blender.org/manual/en/latest/interface/undo_redo.html ; https://dev.epicgames.com/documentation/en-us/unreal-engine/level-editor-details-panel-in-unreal-engine ; https://docs.unity3d.com/2023.2/Documentation/Manual/UsingTheInspector.html ; https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_gui.html ; https://forums.autodesk.com/t5/revit-ideas/make-view-rewind-tool-discoverable/idi-p/7530658
- Linee guida: https://developer.apple.com/design/human-interface-guidelines/the-menu-bar ; https://developer.apple.com/design/human-interface-guidelines/sidebars ; https://developer.apple.com/design/human-interface-guidelines/panels ; https://developer.apple.com/design/human-interface-guidelines/text-fields ; https://developer.apple.com/design/human-interface-guidelines/undo-and-redo ; https://learn.microsoft.com/windows/win32/uxguide/cmd-menus ; https://learn.microsoft.com/windows/win32/uxguide/cmd-toolbars ; https://learn.microsoft.com/windows/win32/uxguide/win-property-win ; https://learn.microsoft.com/windows/win32/uxguide/mess-confirm ; https://learn.microsoft.com/windows/win32/uxguide/inter-mouse ; https://learn.microsoft.com/office/dev/add-ins/design/contextual-tabs ; https://learn.microsoft.com/windows/win32/windowsribbon/windowsribbon-controls-tab ; https://learn.microsoft.com/windows/apps/develop/ui/controls/number-box ; https://learn.microsoft.com/visualstudio/extensibility/ux-guidelines/composite-patterns-for-visual-studio ; https://developer.gnome.org/hig/reference/keyboard.html ; https://developer.gnome.org/hig/patterns/containers/utility-panes.html ; https://developer.gnome.org/hig/patterns/feedback/dialogs.html ; https://developer.gnome.org/hig/patterns/feedback/toasts.html ; https://wiki.gnome.org/Design/HIG/UtilityWindows ; https://www.nngroup.com/articles/modes/ ; https://www.nngroup.com/articles/consistency-and-standards/ ; https://www.nngroup.com/articles/progressive-disclosure/ ; https://www.nngroup.com/articles/accordions-on-desktop/
- Rotella fuori da Qt: https://gitlab.gnome.org/GNOME/gtk/-/blob/main/gtk/gtkspinbutton.c ; https://gitlab.gnome.org/GNOME/gtk/-/blob/main/gtk/gtkrange.c ; https://gitlab.gnome.org/GNOME/gtk/-/blob/main/gtk/gtkdropdown.c ; https://discourse.gnome.org/t/how-to-prevent-scrolling-to-change-the-value-on-spinbutton/14542 ; https://learn.microsoft.com/windows/win32/inputdev/about-mouse-input ; https://learn.microsoft.com/windows/win32/inputdev/wm-mousewheel ; https://learn.microsoft.com/windows/win32/w8cookbook/mousewheel-input-for-windows-8-1 ; https://bugs.webkit.org/show_bug.cgi?id=244240 ; https://bugzilla.mozilla.org/show_bug.cgi?id=1741469 ; https://bugzilla.mozilla.org/show_bug.cgi?id=1922948 ; https://github.com/whatwg/html/issues/10911 ; https://technology.blog.gov.uk/2020/02/24/why-the-gov-uk-design-system-team-changed-the-input-type-for-numbers/ ; https://falkus.co/2023/01/number-input-hassle

---

## 5. Reattività

### 5.1 Soglie e indicatori di avanzamento

| Fonte | Regola | Stato |
|---|---|---|
| Nielsen, «Response Times: The 3 Important Limits» (1993, rivisto 2014) | 0,1 s «about the limit for having the user feel that the system is reacting instantaneously»; 1 s «the limit for the user's flow of thought to stay uninterrupted»; 10 s «the limit for keeping the user's attention focused on the dialogue»; «percent-done progress indicators should be used for operations taking more than about 10 seconds» | [V] |
| NN/g, «Progress Indicators Make a Slow System Less Insufferable» (2014) | «Use a progress indicator for any action that takes longer than about 1.0 second»; animazione ciclica «for actions that take between 2-10 seconds»; percentuale oltre 10 s; sotto 1 s l'animazione distrae | [V] |
| Microsoft, «Progress Bars» (guida Windows 7) | operazioni di 2 s o più sono lunghe; fino a circa 5 s basta un indicatore di attività; «start with a busy pointer and convert to a progress bar after five seconds»; Annulla o Interrompi se dura più di qualche secondo; avanzamento non modale nella barra di stato; «Don't steal input focus» | [V] |
| Microsoft, «Mouse and Pointers» | cursore occupato «when users have to wait more than one second»; cursore «working in background» se il programma resta reattivo | [V] |
| Microsoft, «Keep the UI thread responsive» | «Write event handlers to return quickly... schedule it on a background thread and return» | [V] |
| Windows | un'app risulta «not responding» se non legge i messaggi per «5 seconds» | [V] |
| GNOME HIG, Spinners e Progress bars | indicare l'avanzamento «whenever an operation takes more than around three seconds»; barra per i compiti oltre circa 30 s; barre in linea, non finestre; «consider adding pause and/or cancel buttons» | [V] |
| GNOME mutter | `check-alive-timeout` 5000 ms | [V] |
| Apple HIG | «When possible, use a determinate progress indicator»; «Keep progress indicators moving»; «let people halt processing»; «Show something as soon as possible»; «Let people do other things... while they wait» | [V] |
| Excel (Microsoft Learn) | sotto 0,1 s il calcolo automatico va bene anche mentre si digita; tra 1 e 10 s gli utenti passano al calcolo manuale | [V] |
| Qt QProgressDialog | `minimumDuration` 4000 ms: il dialogo non compare se il compito finisce prima | [V] |

Sintesi [D]: entro 0,1 s nessun indicatore (navigazione, selezione, trascinamento); da 1 a 10 s un indicatore leggero e non modale, mostrato dopo un breve ritardo; oltre 10 s percentuale, stima del tempo e Annulla.

### 5.2 Calcolo in background, annullamento, debounce, risultati progressivi

- GNOME HIG 1.0 (2002) [V]: «Save time by displaying approximate results while calculating finished results»; «Discard unnecessary operations»; «show partial results as they become available».
- Excel [V]: «Stale value formatting» barra i valori non ricalcolati; la barra di stato mostra «Calculate»; con `xlAnyKey` «Pressing any key interrupts recalculation».
- HelioScope [V]: calcolo rapido delle ombre su 12 giorni prima del rapporto annuale (esempio di risultato approssimato prima di quello completo).
- MDN [V]: il debounce serve a «consolidate many noisy invocations into one single invocation».

| Strumento Qt/Python | Fatti | Stato |
|---|---|---|
| Thread della GUI | i widget «can only be used from the main thread» | [V] |
| QThread + worker | modello documentato; `requestInterruption()` è «advisory»; `terminate()` «dangerous and its use is discouraged» | [V] |
| QThreadPool | in PySide6 6.12 `start()` accetta anche un callable Python | [V] |
| QtConcurrent in PySide6 | solo QFutureVoid, QFutureQString e i watcher; manca `run()` (PYSIDE-1896, aperto dal 2022) | [V] |
| QTimer per il debounce | `start()`: «If the timer is already running, it will be stopped and restarted»; esiste il colpo singolo | [V] |
| GIL | «only one thread can execute Python code at once»; NumPy: «Many NumPy operations release the GIL» | [V] |
| ProcessPoolExecutor | «side-step the Global Interpreter Lock», solo oggetti serializzabili; `cancel()` non ferma un calcolo partito; dal 3.14 `terminate_workers()` | [V] |
| multiprocessing | spawn predefinito su Windows; nei programmi impacchettati serve `freeze_support()` | [V] |

### 5.3 QGraphicsView per la pianta (doc Qt 6.12)

| Impostazione | Testo Qt e uso | Stato |
|---|---|---|
| FullViewportUpdate | ridisegna tutto; conviene quando cercare cosa ridisegnare costa più che disegnare; preferita con QOpenGLWidget | [V] |
| MinimalViewportUpdate (predefinita) | regione minima; con molti piccoli cambiamenti può costare di più | [V] |
| SmartViewportUpdate | «attempt to find an optimal update mode by analyzing the areas that require a redraw» | [V] |
| BoundingRectViewportUpdate / NoViewportUpdate | rettangolo che contiene i cambiamenti / aggiornamento gestito da fuori | [V] |
| CacheBackground | pixmap del viewport, «invalidated every time the view is transformed»; nello scorrimento solo in parte; `resetCachedContent()` dopo un cambio | [V] |
| DeviceCoordinateCache | «for items that can move, but are not rotated, scaled or sheared»; «In some cases the cache can also slow down rendering» | [V] |
| DontSavePainterState, DontAdjustForAntialiasing | meno lavoro per oggetto; il secondo può lasciare «painting traces» | [V] |
| BspTreeIndex / NoIndex | BSP «best for static scenes»; NoIndex con molti oggetti in movimento | [V] |
| minimumRenderSize | non disegna gli oggetti più piccoli della soglia, che restano selezionabili | [V] |
| levelOfDetailFromTransform | 1 senza zoom, 0,5 a 1:2, 2 a 2:1 | [V] |
| Esempio «40000 Chips» | antialiasing spento, DontSavePainterState, SmartViewportUpdate; in `paint()` soglie di dettaglio da 0,125 a 2, sotto 0,125 un solo `fillRect` | [V] |
| Viewport OpenGL | `setViewport(new QOpenGLWidget)`; un QOpenGLWidget «turns on OpenGL-based compositing for the entire window»; ANGLE tolto in Qt 6 | [V] |

[D] Su Windows Qt Quick usa Direct3D 11 e «One top-level window can only use one single graphics API» (doc QQuickWidget): un QOpenGLWidget e un QQuickWidget nella stessa finestra entrano in conflitto, salvo forzare OpenGL ovunque.

### 5.4 QQuickWidget o QQuickView con createWindowContainer

| Aspetto | QQuickWidget | QQuickView + createWindowContainer |
|---|---|---|
| Resa | passaggio in più su una texture; «Using QQuickWidget disables the threaded render loop on all platforms» (niente Animator né animazioni legate al vsync) [V] | finestra nativa, render loop a thread possibile [V] |
| Widget sopra la vista | funzionano [V] | la vista resta sopra i widget come «an opaque box»; QTBUG-145021 (Won't Do): un popup finisce dietro la vista [V] |
| Fuoco | QTBUG-144102 (aperto): su Wayland Tab non entra nel QML, con entrambe le soluzioni [V] | «whether QWindow::requestActivate() actually gives the window focus, is platform dependent»; KDE KTouch ha tolto il contenitore perché «breaks Wayland text input» [V] |
| Scorciatoie | widget normale: le QAction della QMainWindow seguono le regole dei widget [D]; uno `Shortcut` QML dentro non scatta (QTBUG-147913) [V] | il controllo del contesto risale dalla QWindow alla finestra dei widget, quindi le QAction dovrebbero scattare [V codice] |
| Wayland | nessuna sottosuperficie [D dalla doc] | sottosuperficie; QTBUG-137940 (aperto, 6.9-6.10): blocco su mutter, wlroots e weston se copre tutta la finestra; Niri non provato [V] / [D] |
| HiDPI | QTBUG-147329 corretto in 6.12 Beta2; QTBUG-144938 (aperto): area di HoverHandler errata dopo un cambio di schermo con scala diversa [V] | QTBUG-143266 solo macOS [V] |
| Posizione di Qt | «QQuickWidget is an alternative to using QQuickView and QWidget::createWindowContainer(). The restrictions on stacking order do not apply... the above mentioned advantages come at the expense of performance» [V] | doc QOpenGLWidget: «strongly recommended to limit the usage of this approach to cases where there is no other choice» [V] |

Altre note [V]: View3D disegna per default fuori schermo, l'unica modalità con piena fedeltà; `renderStats` dà fps e tempi di resa, utili per misurare; QTBUG-138669 (memoria che cresce a ogni ridimensionamento) corretto nel ramo 6.12 il 21/09/2026, da verificare se già in 6.12.0. [D] Con QQuickWidget e View3D Offscreen i passaggi fuori schermo sono due; senza render loop a thread, ogni calcolo Python nel thread GUI ferma anche il 3D e l'animazione del sole.

### 5.5 Grafici interattivi in PySide6

| | matplotlib 3.11 | Qt Charts (6.12) | Qt Graphs 2D (6.12) | pyqtgraph 0.14 |
|---|---|---|---|---|
| Stato | maturo | «deprecated since Qt 6.10. For new projects, use the Qt Graphs module» [V] | 2D dalla 6.7 in anteprima, «fully supported» dalla 6.8 [V] | sviluppo attivo; la CI usa già PySide6 6.12 [V] |
| Resa | Agg raster; veloce solo con il blitting, che «drastically improve performance» [V] | Graphics View; `useOpenGL` molto più veloce ma perde etichette e stili [V] | Qt Quick Shapes su GPU [V] | «not nearly as complete/mature as matplotlib, but runs much faster» [V] |
| Interattività | zoom e pan con NavigationToolbar2QT [V]; mirino e tooltip da programmare [D] | di base [D] | dalla 6.10 più assi e hover sulle serie [V] | «interactive scaling and panning» [V] |
| Esportazione | PNG, PDF, SVG vettoriali [V] | PDF con QPdfWriter [D] | solo immagine [D] | PNG, SVG, CSV; stampa «not well supported» [V] |
| Uso dai widget | FigureCanvas [V] | QChartView [V] | solo QML, serve un QQuickWidget [V] / [D] | PlotWidget [D] |
| Mancanze in 6.8 | - | modulo deprecato | secondo la guida di migrazione: niente candlestick, box plot, «Titles and legends», asse logaritmico, polare [V] | meno tipi, aspetto meno curato [D] |
| Licenza | licenza di matplotlib, permissiva [D] | «Commercial or GPLv3» [V] | «Commercial or GPLv3» [V] | MIT [V] |

Nota [V]: su PyPI PySide6-Addons 6.12 dichiara «LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only», mentre la documentazione Qt indica GPLv3 per Charts, Graphs e Canvas Painter: da chiarire prima di distribuire.
[D] Gli 8760 punti orari sono pochi per tutte e quattro; le differenze stanno nella fluidità di zoom, pan e mirino (pyqtgraph la migliore) e nella qualità di stampa (matplotlib la migliore). Nessuna misura fatta: non era permesso installare pacchetti.

### 5.6 Cosa conviene a Meridiana

1. **Budget di tempo** [V Nielsen, D sul valore]: navigazione, selezione, trascinamento e digitazione entro 0,1 s; nessun lavoro occupa il thread GUI per più di 50-100 ms. Windows e mutter dicono «non risponde» a 5 s, ma l'utente se ne accorge molto prima.
2. **Ricalcolo automatico senza blocchi** [D sulle fonti]:
   - ogni modifica confermata riavvia un QTimer a colpo singolo di 200-300 ms (da tarare);
   - allo scadere parte il calcolo con un numero di generazione; i risultati di generazioni vecchie si scartano;
   - i risultati vecchi restano visibili ma marcati «da aggiornare» (grigi o con un banner, come Excel e InfoBar);
   - avanzamento non modale nella barra di stato con Annulla; spinner dopo circa 1 s; percentuale e stima oltre circa 10 s; niente dialoghi modali.
3. **Prima un'anteprima, poi il dettaglio**: giorni tipo o passo ridotto, poi le 8760 ore (GNOME HIG 1.0, HelioScope).
4. **Thread o processi**: numpy e pvlib in QThreadPool (NumPy rilascia il GIL); cicli in Python puro (ombre per modulo e per ora) in ProcessPoolExecutor con spawn e `freeze_support()` se si impacchetta; annullamento cooperativo con un flag controllato a blocchi.
5. **Pianta**: BspTreeIndex, livelli di dettaglio come «40000 Chips» (a zoom basso un rettangolo per fila), `minimumRenderSize`, antialiasing solo dove serve, cache solo dopo una misura; nord, scala e righelli come widget sovrapposti; niente QOpenGLWidget nella stessa finestra di un QQuickWidget in Direct3D.
6. **3D**: restare su QQuickWidget (sovrapposizioni, niente sottosuperfici Wayland, QAction che funzionano), misurare con `renderStats`; passare al contenitore solo se le misure lo chiedono, sapendo dei bug Wayland. ViewCube e bussola dentro il QML.
7. **Grafici**: pyqtgraph per le schede interattive, matplotlib per il PDF; non Qt Charts (deprecato); Qt Graphs più avanti (solo QML, GPLv3, funzioni mancanti).

### Fonti della sezione 5
- Soglie e indicatori: https://www.nngroup.com/articles/response-times-3-important-limits/ ; https://www.nngroup.com/articles/progress-indicators/ ; https://learn.microsoft.com/en-us/windows/win32/uxguide/progress-bars ; https://learn.microsoft.com/windows/win32/uxguide/inter-mouse ; https://learn.microsoft.com/windows/apps/develop/performance/keep-ui-thread-responsive ; https://learn.microsoft.com/windows/apps/develop/ui/controls/progress-controls ; https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-ishungappwindow ; https://developer.gnome.org/hig/patterns/feedback/spinners.html ; https://developer.gnome.org/hig/patterns/feedback/progress-bars.html ; https://github.com/GNOME/mutter/blob/main/data/org.gnome.mutter.gschema.xml.in ; https://developer.apple.com/design/human-interface-guidelines/progress-indicators ; https://developer.apple.com/design/human-interface-guidelines/loading ; https://doc.qt.io/qt-6/qprogressdialog.html
- Background e risultati obsoleti: https://www.en.pms.ifi.lmu.de/publications/diplomarbeiten/Sacha.Berger/literatur/misc/hig-1.0.pdf ; https://learn.microsoft.com/office/vba/excel/concepts/excel-performance/excel-improving-calculation-performance ; https://support.microsoft.com/en-us/office/stale-value-formatting-4b5c63c3-5dc7-4e9b-8e24-88bed1987dbd ; https://learn.microsoft.com/office/vba/api/excel.xlcalculationinterruptkey ; https://developer.mozilla.org/en-US/docs/Glossary/Debounce ; https://doc.qt.io/qt-6/threads-technologies.html ; https://doc.qt.io/qt-6/threads-qobject.html ; https://doc.qt.io/qt-6/qthread.html ; https://doc.qt.io/qt-6/qtimer.html ; https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThreadPool.html ; https://doc.qt.io/qtforpython-6/PySide6/QtConcurrent/QtConcurrent.html ; https://qt-project.atlassian.net/browse/PYSIDE-1896 ; https://docs.python.org/3/library/threading.html ; https://docs.python.org/3/library/concurrent.futures.html ; https://docs.python.org/3/library/multiprocessing.html ; https://numpy.org/doc/stable/reference/thread_safety.html ; https://help-center.helioscope.com/hc/en-us/articles/7835499970707-Optimize-shaded-modules
- QGraphicsView: https://doc.qt.io/qt-6/qgraphicsview.html ; https://doc.qt.io/qt-6/qgraphicsitem.html ; https://doc.qt.io/qt-6/qgraphicsscene.html ; https://doc.qt.io/qt-6/qstyleoptiongraphicsitem.html ; https://doc.qt.io/qt-6/graphicsview.html ; https://doc.qt.io/qt-6/qtwidgets-graphicsview-chip-example.html ; https://doc.qt.io/qt-6/qabstractscrollarea.html ; https://doc.qt.io/qt-6/qopenglwidget.html ; https://doc.qt.io/qt-6/opengl-changes-qt6.html
- QQuickWidget e contenitore: https://doc.qt.io/qt-6/qquickwidget.html ; https://doc.qt.io/qt-6/qwidget.html#createWindowContainer ; https://doc.qt.io/qt-6/qtquick3d-requirements.html ; https://doc.qt.io/qt-6/qml-qtquick3d-view3d.html ; https://code.qt.io/cgit/qt/qtbase.git/tree/src/widgets/kernel/qshortcut_widgets.cpp?h=6.10 ; https://invent.kde.org/education/ktouch/-/merge_requests/29 ; bug su https://qt-project.atlassian.net/browse/ : QTBUG-31774, QTBUG-117733, QTBUG-137940, QTBUG-138669, QTBUG-143266, QTBUG-144102, QTBUG-144938, QTBUG-145021, QTBUG-147329, QTBUG-147913
- Grafici: https://doc.qt.io/qt-6/qtcharts-index.html ; https://doc.qt.io/qt-6/qabstractseries-qtcharts.html ; https://doc.qt.io/qt-6/qtgraphs-index.html ; https://doc.qt.io/qt-6/qtgraphs-overview-2d.html ; https://doc.qt.io/qt-6/qtgraphs-migration-guide-2d.html ; https://doc.qt.io/qt-6/qtgraphswidgets-module.html ; https://www.qt.io/blog/qtgraphs-new-features-in-6.10 ; https://matplotlib.org/stable/users/explain/animations/blitting.html ; https://matplotlib.org/stable/users/explain/artists/performance.html ; https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html ; https://pyqtgraph.readthedocs.io/en/latest/getting_started/introduction.html ; https://pyqtgraph.readthedocs.io/en/latest/user_guide/exporting.html ; https://github.com/pyqtgraph/pyqtgraph ; https://github.com/pyqtgraph/pyqtgraph/issues/3653 ; https://pypi.org/project/PySide6-Addons/

---

## 6. Cosa resta da verificare

**Da provare sul posto** (Qt 6.12, tastiera italiana, Windows e Niri)
- Che Ctrl+?, ?, Ctrl+Maiusc+2/3 e Ctrl++ scattino davvero (la lettura del sorgente Qt dice sì per i primi tre).
- Che AltGr+è e AltGr++ scritti in un campo non facciano scattare scorciatoie né tasti di accesso (QTBUG-73247, QTBUG-69317).
- Se QtWayland su Niri segnala il touchpad (`device().type()`) e le fasi di scorrimento, e come arriva il pizzico.
- Un pannello staccato su Niri; le scorciatoie e il fuoco con il 3D in QQuickWidget; QTBUG-137940 su Niri se si passa al contenitore.
- Le prestazioni reali dei grafici con 8760 punti e della pianta con molti moduli.

**Non trovato o non leggibile**
- Archicad F2 pianta / F3 3D: ricordo non verificato (budget di ricerca esaurito).
- SketchUp: scorciatoia dello zoom finestra. Revit: il codice ZS dal PDF.
- Aurora: articolo «3D System Design» (404, archivio non disponibile), indicatore del nord, tasto per l'elenco delle scorciatoie, colori per stringa e conteggi degli avvisi.
- HelioScope e OpenSolar: indicatore del nord; testo e posizione degli avvisi di HelioScope.
- DIALux evo: navigazione col mouse e scorciatoie delle versioni 12 e 13.
- PVsyst: rotella e bussola nella scena 3D.
- Fusion: pagine di supporto (403). Easy Solar: non cercato.
- Valori predefiniti di Blender (Smooth View 200 ms, Orbit Around Selection, Auto Depth).
- HP e Dell (tasti funzione), pagine ufficiali non raggiungibili.
- Se la correzione di QTBUG-138669 è già in 6.12.0.
