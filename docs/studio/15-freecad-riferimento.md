# FreeCAD come riferimento e come «programma gemello»

22/10/2026. Daniel ha chiesto: «stai verificando come fa FreeCAD per gestire tutto ciò? navigazione, modellazione, scorciatoie, ecc? forse è il riferimento più solido a cui buttare un occhio ed è pure open source, quindi gli si può "rubare" qualcosa e garantirne la compatibilità reciproca sarebbe bellissimo!». In più ha chiesto il mouse della vista 3D «come FreeCAD», e se FreeCAD lo fa come AutoCAD (sezione 2.1).

**Legenda**
- [V] letto nel codice o nella documentazione ufficiale, alla versione indicata;
- [V, prova] provato sul laptop Linux (Lucciola, Niri) con FreeCAD 1.1.4;
- [I] dedotto.

**Versioni lette** (codice su GitHub a commit fissi):
- stabile **1.1.4** = `4fd3bf3` (rilascio del 28/09/2026);
- **26.3 RC2** = `9fb16e7` (18/10/2026);
- **main** = `d3f4da7` (21/10/2026).

I prefissi completi dei link sono nelle fonti, in fondo.

**Cosa c'era già, e non è stato rifatto**
- 07-snapping-open-source.md: lo snapper di Draft letto nel codice (sezione 2).
- 05a-disegno-cad-dettaglio.md: i modificatori (Maiusc, Ctrl, Alt) e le tolleranze di FreeCAD accanto agli altri CAD.
- 12a-convenzioni-ux.md: scorciatoie di FreeCAD 1.x (1.5), cubo (2.2), pivot e stile CAD (2.4, 2.6).
- 01-confronto-approcci.md: «E3. FreeCAD 1.1» come base, scartata. La valutazione regge (sezione 4.3).

Questo studio aggiunge il codice di ogni stile di navigazione e del NaviCube, la parte «modellazione e interfaccia», il BIM con il sole, e soprattutto le **prove di compatibilità**: IFC nei due sensi, .FCStd, macro.

## In breve

1. **FreeCAD non fa come AutoCAD con lo stile predefinito** [V].
   - Lo stile predefinito è «CAD»: centrale = pan, centrale tenuto più sinistro (o destro) = orbita, rotella = zoom sul cursore.
   - Lo stile che coincide con AutoCAD è **«Revit»**: centrale = pan, Maiusc+centrale = orbita, rotella = zoom sul cursore.
   - Restano quattro differenze:
     - il doppio clic centrale non adatta la vista, ricentra sul punto cliccato;
     - il perno è al centro della finestra, se non si cambia la preferenza;
     - l'orbita è libera («Rounded Arcball») e non vincolata alla verticale;
     - la selezione aggiunge con Ctrl.
   - Tabella completa nella sezione 2.
2. **Da prendere da FreeCAD** (idee; il codice è C++ legato a Coin3D):
   - stili di navigazione scelti nelle Preferenze;
   - ricentrare con il clic centrale;
   - il cubo con le etichette delle facce modificabili;
   - campi con unità e aritmetica («2 m + 30 cm»);
   - testo di preselezione con le coordinate nella barra di stato;
   - misura rapida della selezione;
   - ricalcolo dei soli oggetti «toccati»;
   - editor delle scorciatoie che mostra i conflitti mentre si digita;
   - pannello attività con OK e Annulla legati a una transazione;
   - piano di lavoro sulla falda.
   Tabella nella sezione 6.
3. **La compatibilità da costruire per prima: esportare IFC4 da Meridiana** con ifcopenshell.
   - [V, prova] Il prototipo funziona già:
     - esporta 188 moduli `IfcSolarDevice` con un tipo condiviso e i Pset;
     - FreeCAD 1.1.4 lo apre con geometria, posizioni e proprietà corrette.
   - Fatica per portarlo nel programma: 3-4 giorni.
   - Poi la lettura degli IFC dell'architetto (5-8 giorni): il prototipo legge bene i file di Meridiana e di FreeCAD; su un file di terzi servono regole di tolleranza.
4. **Le prove** (sezione 8) hanno trovato cinque problemi di FreeCAD 1.1.4, utili da segnalare a monte:
   - l'apertura IFC (NativeIFC) non mostra latitudine e longitudine del sito;
   - il vecchio importatore, l'unico che legge il nord, non parte con l'ifcopenshell che FreeCAD stesso distribuisce;
   - l'esportazione tronca latitudine e longitudine al secondo intero: fino a circa 30 m di errore;
   - il diagramma solare non funziona nei pacchetti ufficiali (manca pysolar), e dal codice risulta specchiato est-ovest [I, non provato];
   - pareti esportate come «MOVABLE» e tetti a falde come «FLAT_ROOF».
5. **.FCStd**: [V, prova] si può scrivere senza FreeCAD; un file minimo con oggetti parametrici si apre e si ricalcola. Come formato di scambio però è sconsigliato: interno, cambia tra le versioni, e FreeCAD ha appena stretto i controlli di sicurezza su questi file.
6. **Macro per FreeCAD**: [V, prova] il codice di Meridiana gira dentro FreeCAD, perché l'AppImage ha numpy e shapely. Una macro di 150 righe costruisce il progetto con gli oggetti del BIM in 3 s, e FreeCAD lo riesporta in IFC. Un addon vero costa 3-5 giorni; non è la prima cosa da fare.

## 1. Versione, stato, licenza

| | 1.1.4 (stabile) | 26.3 RC2 | Fonte |
|---|---|---|---|
| Data | 28/09/2026, ultima della serie 1.1 | 18/10/2026; la stabile non è ancora uscita al 22/10/2026 | [V] F1, F2 |
| Numerazione | | per anni, tre rilasci l'anno (blog del 26/06/2026) | [V] F3 |
| Qt / PySide6 | AppImage: Qt 6.8.3, PySide6 6.8.3, Python 3.11.14 [V, prova]; Flatpak di Flathub: Qt 6.11 (runtime KDE 6.11), Python 3.13 | Qt 6.11, Python 3.13, OCCT 8.0 | [V] F4 |
| ifcopenshell incluso | 0.8.4 [V, prova] | 0.8.5 | [V] F4 |
| numpy / shapely nell'AppImage | 1.26.4 / 2.1.2 [V, prova] | | |
| Dimensione | AppImage 821 MB; Flatpak 414 MB da scaricare, 1,3 GB installato più il runtime KDE | | [V] |

**Licenza.**
- FreeCAD è **LGPL-2.1-or-later** [V]:
  - il file LICENSE ha il testo della LGPL 2.1;
  - i file hanno l'intestazione SPDX `LGPL-2.1-or-later`; i più vecchi dicono «version 2 ... or any later version»;
  - all'avvio FreeCAD stampa «licensed under the terms of LGPL2+ license» [V, prova].
- La LGPL 2.1, sezione 3, permette di passare alla GPL «version 2 or later», quindi **il codice si può riprendere in Meridiana (GPL-3.0-or-later) tenendo le note di copyright** [V F5; è una lettura della licenza, non un parere legale].
  - Anche il NaviCube, nato nel 2017 da Kustaa Nyholm, ha intestazione LGPL v2 o successive in 1.1.4 e `LGPL-2.1-or-later` in 26.3 [V N12].
- In pratica si prendono idee:
  - quasi tutto è C++ legato a Coin3D e OpenCascade;
  - fanno eccezione il Python di Draft e BIM, per esempio WorkingPlane.py e i calcoli del Sito.
- Dipendenze:
  - **ifcopenshell** è LGPL-3.0-or-later e si può usare come libreria [V];
  - pysolar è GPL-3.0-or-later [V];
  - **ladybug è AGPL-3.0**, da evitare [V B7].

## 2. Navigazione

### 2.1 La domanda di Daniel: il mouse «come FreeCAD», e FreeCAD fa come AutoCAD?

**Lo stile predefinito di FreeCAD 1.x è «CAD»** [V]. È il valore di ripiego del parametro `NavigationStyle` in 1.1.4 e in 26.3, nella pagina delle preferenze, nelle impostazioni della vista e nella pagina di primo avvio; nessun «preference pack» lo cambia [V N4]. La prova lo conferma: parametro e vista dicono `Gui::CADNavigationStyle` [V, prova].

Stile CAD, gesto per gesto [V N1, N13]:
- seleziona: sinistro; Ctrl+sinistro aggiunge;
- pan: centrale tenuto; in alternativa Ctrl+destro;
- orbita: centrale tenuto, poi sinistro (o destro) tenuto; in alternativa Maiusc+destro;
- zoom: rotella, verso il cursore; oppure, con il centrale tenuto, un clic breve del sinistro o del destro e poi muovere in su o in giù; oppure Ctrl+Maiusc+destro;
- clic centrale breve: ricentra la vista sul punto sotto il cursore, che diventa il nuovo centro di rotazione (`lookAtPoint`) [V N8];
- destro fermo: menu contestuale.

**Lo stile che coincide con AutoCAD è «Revit»** [V N2, N13]:
- seleziona: sinistro;
- pan: centrale, oppure sinistro+destro insieme;
- orbita: **Maiusc+centrale**, oppure centrale+destro;
- zoom: rotella, verso il cursore; Ctrl+centrale trascinando; Ctrl+Maiusc+destro;
- clic centrale breve: ricentra sul punto;
- destro: menu.

**Differenze rimaste tra AutoCAD e FreeCAD «Revit»**

| Gesto | AutoCAD (12a, 1.1 e 2.6) | FreeCAD, stile Revit | Uguale? |
|---|---|---|---|
| Pan | centrale | centrale (anche sinistro+destro) | sì |
| Orbita | Maiusc+centrale, orbita 3D: l'orbita vincolata, con la verticale che resta verticale [I sul vincolo] | Maiusc+centrale. Il tipo di orbita è una preferenza a parte: dalla 1.1 il predefinito è **Rounded Arcball**, libero; per l'orbita di AutoCAD serve **Turntable** [V N5] | il gesto sì, il movimento no se non si cambia la preferenza |
| Perno dell'orbita | il punto bersaglio, segnato da una piccola sfera scura (12a 2.4) | preferenza «Rotation mode», predefinita **Window center**, cioè il punto focale al centro della vista. Le alternative: «Drag at cursor» (punto del modello sotto il cursore) e «Object center» (centro dell'ingombro). Il clic centrale ricentra la vista e il perno su un punto. Un indicatore mostra il centro di rotazione, acceso di base [V N6] | no |
| Zoom con la rotella | verso il cursore | verso il cursore (`ZoomAtCursor`, vero di base), passo del 20% (`ZoomStep` 0,2) [V N7] | sì |
| Doppio clic centrale | zoom estensione | ogni clic breve ricentra sul punto, quindi il doppio clic ricentra due volte. «Adatta tutto» è la sequenza V, F o il menu del cubo [V N2, N10] | **no** |
| Destro | menu, oppure Invio (configurabile) | menu | quasi |
| Selezione | il clic aggiunge, Maiusc+clic toglie; riquadro da sinistra a destra = finestra, da destra a sinistra = intersezione | Ctrl+clic aggiunge. Il riquadro trascinato con finestra e intersezione arriva solo in **26.3** (commit 12a68e8c2c, PR #29547); in 1.1.4 serve Maiusc+B [V N14, N10] | no |
| In più in FreeCAD | | sinistro+destro = pan; centrale+destro = orbita; Ctrl+centrale = zoom trascinando | |

**In una riga.** «Come FreeCAD» e «come AutoCAD» sono due cose diverse con lo stile predefinito. Coincidono quasi con lo stile «Revit» di FreeCAD, impostando l'orbita «Turntable» e il perno «Drag at cursor», e aggiungendo il doppio clic centrale per l'estensione, che FreeCAD non ha.

Per Meridiana: gli stessi stili di FreeCAD tra cui scegliere, più uno «AutoCAD»; il predefinito lo decide Daniel (2.6). 12a proponeva AutoCAD/Revit.

### 2.2 Gli stili: un rigo per stile, una colonna per gesto

Codice 26.3 RC2, uguale in 1.1.4 dove non è detto altro [V N1, N2, N3]; descrizioni ufficiali della wiki, revisione del 06/02/2026 [V N13]. «Centrale» è la rotella premuta.

| Stile | Seleziona | Pan | Orbita | Zoom: rotella | Zoom: trascinando | Clic centrale breve | Menu e altro |
|---|---|---|---|---|---|---|---|
| **CAD** (predefinito) | sinistro | centrale; Ctrl+destro | centrale + sinistro o destro; Maiusc+destro | verso il cursore | centrale tenuto + clic breve sinistro o destro, poi su/giù; Ctrl+Maiusc+destro | ricentra sul punto | destro fermo = menu |
| **Revit** | sinistro | centrale; sinistro+destro | Maiusc+centrale; centrale+destro | verso il cursore | Ctrl+centrale; Ctrl+Maiusc+destro | ricentra | destro = menu |
| **Blender** | sinistro | Maiusc+centrale; sinistro+destro | centrale | verso il cursore | Ctrl+centrale; Ctrl+Maiusc+destro | ricentra | destro = menu |
| **SolidWorks** (dalla 1.1) | sinistro | Ctrl+centrale | centrale | verso il cursore | Maiusc+centrale | ricentra | destro = menu |
| **Siemens NX** (dalla 1.1) | sinistro | Maiusc+centrale; centrale+destro | centrale | verso il cursore | centrale+sinistro; centrale e poi Ctrl | ricentra | Ctrl+F adatta; Inizio isometrica; Fine trimetrica; F8 dall'alto |
| **OpenInventor** | Ctrl o Maiusc + sinistro | centrale; Ctrl+Maiusc+sinistro | sinistro trascinato (con «Enable spinning animations», spento di base, la vista continua a girare se si lascia in movimento) | verso il cursore | sinistro+centrale; Ctrl+centrale | ricentra; anche Maiusc+clic sinistro | destro = menu |
| **OpenCascade** | sinistro | centrale, anche con Ctrl | Ctrl+destro; centrale+destro | verso il cursore | Ctrl+sinistro | nulla | destro = menu |
| **OpenSCAD** | sinistro (clic) | destro trascinato | sinistro trascinato | verso il cursore | centrale; Maiusc+destro | nulla | destro fermo = menu |
| **TinkerCAD** | sinistro | centrale | destro trascinato | verso il cursore | no | nulla | destro fermo = menu |
| **Touchpad** | sinistro | Maiusc e muovere | Alt e muovere; Maiusc+sinistro | verso il cursore | Ctrl+Maiusc e muovere | nulla | pensato per il touchpad con i tasti |
| **Gesture** | tocco o sinistro | destro; due dita | sinistro trascinato (nelle modifiche Alt+sinistro); un dito | verso il cursore; pizzico; PagSu/PagGiù | no | ricentra; anche il tasto H | inclinazione: sinistro+destro di lato |
| **Maya-Gesture** | sinistro | Alt+centrale | Alt+sinistro | verso il cursore; pizzico | Alt+destro | ricentra; anche H | inclinazione: Alt+sinistro+destro |
| *Riferimento: AutoCAD* | sinistro | centrale | Maiusc+centrale | verso il cursore | no | no | doppio clic centrale = estensione |
| *Riferimento: Meridiana oggi* | sinistro (solo moduli in 3D) | Ctrl+trascina | sinistro | verso l'origine | no | no | (OrbitCameraController di Qt, 12a 2.9) |

**Comune a tutti gli stili** [V N13, N10]:
- Ctrl+clic per la selezione multipla;
- PagSu e PagGiù oppure Ctrl++ e Ctrl+- per lo zoom;
- le frecce spostano la vista;
- Maiusc+freccia sinistra e destra ruotano di 90 gradi;
- il destro senza trascinare apre il menu, anche dove il destro serve a navigare.

**Novità 26.3 rispetto a 1.1.4** [V N14]:
- selezione a riquadro trascinando nella vista;
- **«Touchpad scroll pans instead of zooming»**:
  - con un dispositivo «preciso» due dita fanno pan, Maiusc+due dita orbita, Ctrl+due dita zoom;
  - acceso di base solo su macOS;
  - in 1.1.4 la rotella fa sempre zoom (`processWheelEvent`);
- il cubo:
  - doppio clic su una faccia: orienta e centra;
  - trascinarlo fa orbitare;
  - pulsante Home animato;
- il sottomenu «Navigation styles» è sparito dal menu contestuale della vista: resta il pulsante nella barra di stato;
- blocchi d'orientamento e d'orbita a disposizione dei comandi, cioè API e non preferenze.

### 2.3 Tastiera e comandi di vista

[V N10, N11] (stesse scorciatoie in 1.1.4 e 26.3, salvo dove indicato):

| Tasto | Comando |
|---|---|
| 0 / 1 / 2 / 3 / 4 / 5 / 6 | isometrica / fronte / alto / destra / retro / basso / sinistra |
| V, F / V, S | adatta tutto / adatta alla selezione |
| V, O / V, P | ortogonale / prospettica |
| V, 1 ... V, 7 | stili di disegno (come è, punti, fil di ferro, linee nascoste, senza ombreggiatura, ombreggiato, linee piatte) |
| Inizio / Fine / Maiusc+Fine | vista Home / richiama / memorizza la vista di lavoro |
| Maiusc+← / Maiusc+→ | ruota di 90 gradi |
| Ctrl+B | zoom a riquadro |
| Maiusc+B / Maiusc+E | selezione a riquadro di oggetti / di elementi |
| S, B / S, F | selezione precedente / successiva |
| G, G (o pressione lunga di 1 s) | «Clarify selection»: elenco degli oggetti sotto il cursore |
| Spazio | mostra / nasconde la selezione |
| Esc | passa tra navigazione e modifica |
| V, T | trasparenza |
| A, C | assi |
| F11 / Alt+F11 | schermo intero della vista / della finestra |
| Ctrl+freccia | pannelli sovrapposti a sinistra, destra, sopra, sotto |
| Ctrl+Maiusc+P | **invia la selezione alla console Python** |
| F5 | ricalcola |
| Ctrl+0 (26.3) | pannelli in basso (report e console) |

### 2.4 Impostazioni della navigazione

Preferenze > Visualizzazione > Navigazione [V N4-N9].

| Impostazione | Valori | Predefinito |
|---|---|---|
| Stile | i 12 della tabella 2.2 | CAD |
| Tipo di orbita | Rounded Arcball, Trackball, Trackball classic, Free Turntable, Turntable | Rounded Arcball (dalla 1.1) |
| Rotation mode | Window center, Drag at cursor, Object center | Window center (incoerenza nel codice: la reimpostazione usa Drag at cursor) |
| Indicatore del centro di rotazione | sì/no, dimensione 5, colore | sì |
| Zoom at cursor / Invert zoom / passo | | sì / sì / 0,2 |
| Animazioni di navigazione | sì/no, durata 100-10000 ms | sì, **500 ms** |
| Animazioni di rotazione libera (spin) | | no |
| Cubo | angolo, scostamento, dimensione 132 px, smusso 0,12, opacità a riposo 50%, colori, carattere, assi accanto, «Rotate to nearest», passi per giro 8 (45 gradi) | in alto a destra |
| Etichette delle facce | testo libero per FRONT, TOP, RIGHT, REAR, BOTTOM, LEFT | in inglese, tradotte |
| Orientamento della camera dei documenti nuovi e della vista Home | Isometric, Dimetric, Trimetric, Top, Front, Left, Right, Rear, Bottom, Custom | Trimetric |
| Clarify selection con pressione lunga | sì/no, 0,3-3 s | sì, 1 s |
| Touchpad scroll pans (26.3) | sì/no | no (sì su macOS) |

[V, prova] Le animazioni di 500 ms sono abbastanza lunghe da far uscire un'immagine vuota se la si salva subito dopo un cambio di vista: nella macro di prova sono state spente. 12a (2.5) indica 200-300 ms per i cambi di vista: Meridiana deve stare più corta di FreeCAD.

### 2.5 Il NaviCube

[V N12]
- **Dove sta.** `src/Gui/NaviCube.cpp`, C++:
  - 1.1.4: 1.411 righe, disegno OpenGL proprio;
  - 26.3: 1.452 righe più il nodo Coin `SoNaviCube` (rifatto a marzo-giugno 2026).
- **Parti**:
  - 26 facce cliccabili: 6 principali, 12 spigoli, 8 vertici;
  - 4 frecce, che ruotano di 360/8 = 45 gradi;
  - 2 frecce curve, che ruotano attorno all'asse della vista;
  - un punto per la vista opposta;
  - il mini-cubo con il menu;
  - in 26.3 anche un pulsante Home.
- **Orientamenti.** Ogni faccia ha una rotazione fissa (`getFaceRotation`). Con «Rotate to nearest» la camera va all'orientamento più vicino tra 4 (facce e spigoli) o 6 (vertici), così il clic su una faccia non capovolge la vista.
- **Clic e trascinamento.**
  - Clic su una faccia: orienta, con animazione.
  - Doppio clic sulla stessa faccia: orienta e centra (26.3).
  - Trascinando il cubo:
    - 26.3: la vista orbita attorno alla sfera che contiene la scena;
    - con «Movable Navigation Cube» invece il cubo si sposta.
- **Menu** (personalizzabile da ogni workbench): ortogonale, prospettica, isometrica | adatta tutto, adatta selezione, allinea alla selezione | cubo spostabile.
- **Assi.** Dal codice [V N12] e dalla prova [V, prova, immagine `capannone_sud.png`]: «Front» guarda da −Y verso +Y, «Right» da +X, «Top» da +Z. Con l'asse Y verso il nord (Meridiana, e il BIM con declinazione zero):
  - FRONT è **la vista da sud**;
  - RIGHT da est;
  - REAR da nord;
  - LEFT da ovest.
  Le etichette sono testo libero: in FreeCAD si possono scrivere S, E, N, O al posto di FRONT, RIGHT, REAR, LEFT.

### 2.6 Cosa replicare in Meridiana

**A. Profili di navigazione**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A1. Un solo profilo (AutoCAD/Revit, 12a) | 3 | 5 | 5 | chi viene da FreeCAD, Blender o SolidWorks resta scontento |
| A2. I profili più usati: «AutoCAD/Revit», «FreeCAD (CAD)», «Blender», «SolidWorks», «SketchUp», «Touchpad» | 4 | 4 | 4 | copre quasi tutti, ma non è «gli stessi stili di FreeCAD» |
| A3. **Gli stessi stili di FreeCAD**, con i loro nomi, più «AutoCAD» (lo stile Revit con il doppio clic centrale = estensione) e «SketchUp». Ogni stile è una tabella di dati (gesto → azione) in un modulo senza Qt, con i suoi test; di Gesture e Maya-Gesture solo la parte del mouse | 5 | 4 | 3 | una sola macchina di stati per pianta e 3D: uno stile in più è una tabella e qualche test, non codice nuovo. FreeCAD scrive invece una classe C++ per stile, con molta logica copiata: da non imitare |
| A4. I 12 stili identici anche al tocco (tocco, tieni premuto, due dita) | 3 | 2 | 2 | i gesti touch di FreeCAD sono macchine di stati difficili, scritte per Windows e Qt 5; nessuno schermo touch tra i PC di Daniel |

**Raccomandazione: A3**, che è anche ciò che Daniel ha chiesto («come FreeCAD»).
- Lo stile «CAD» riproduce quello predefinito di FreeCAD; «AutoCAD» è lo stile Revit con il doppio clic centrale per l'estensione.
- In pianta valgono pan e zoom dello stile; i gesti d'orbita non fanno nulla.
- Il predefinito lo sceglie Daniel. La ricerca suggerisce «AutoCAD» (12a), perché Daniel lavora in AutoCAD; «CAD» se preferisce avere le mani di FreeCAD.
- Fatica: 3-4 giorni con i test, in fase 2 (A2 costerebbe 2-3 giorni).

**B. Dettagli da prendere** [I, salvo dove indicato]
- **Clic centrale breve = ricentra sul punto** (`lookAtPoint` di FreeCAD) [V N8]:
  - utile e gratuito;
  - non va in conflitto con il pan, perché scatta solo se il mouse non si è mosso;
  - in pianta: centra la vista sul punto.
- **Perno**:
  - predefinito «punto sotto il cursore», con ripiego sul piano del terreno (12a 2.9), cioè il «Drag at cursor» di FreeCAD;
  - in alternativa «centro della selezione» e «centro della finestra»;
  - con l'indicatore visibile durante l'orbita, come FreeCAD.
- **Orbita Turntable** predefinita (la verticale resta verticale), Arcball a scelta. L'arcball di FreeCAD è pensata per i pezzi meccanici: per un edificio fa perdere l'orizzonte.
- **Animazioni** di 250 ms, non i 500 di FreeCAD; spente se il sistema chiede meno movimento.
- **Touchpad** come 26.3: con un dispositivo preciso due dita = pan, Maiusc = orbita, Ctrl o pizzico = zoom. In più il profilo «Touchpad» con i tasti, per chi preferisce.
- **Cubo** con la struttura di FreeCAD:
  - 26 parti;
  - frecce di 45 gradi (12a: 15 e 90 con Maiusc; si può tenere 15 con Maiusc a 90, come Onshape);
  - rotazione attorno alla vista;
  - vista opposta, Home;
  - «ruota all'orientamento più vicino»;
  - doppio clic che centra; trascinamento che orbita;
  - menu con prospettiva/parallela, adatta, allinea alla selezione, e in più «vista dal sole» e «imposta come Home».
  - Facce Alto, N, E, S, O come in 12a.
  - Fatica M, fase 2 (già nel piano come T1).

## 3. Modellazione e interfaccia

Dalla ricerca nel codice 1.1.4, 26.3 e main [V A1-A11]. Per ogni voce la conclusione per Meridiana, con un voto da 1 a 5 di convenienza.

### 3.1 Pannello delle attività (Task panel)

- **Come funziona** [V A1]:
  - un `TaskDialog` ha OK e Annulla, più Applica e Aiuto se servono;
  - i pulsanti stanno **in alto** e centrati, per scelta del dialogo e non dell'utente;
  - la Design Guide del gruppo di design vuole «Ok e Cancel ... at the top of each panel».
- **Con un dialogo aperto**:
  - i comandi che modificano il documento si spengono; vista e selezione restano libere;
  - un dialogo alla volta in 1.1.4; uno per documento in 26.3.
- **Tasti.** Invio = pulsante predefinito, Esc = Annulla. Esc che chiude il pannello sorprende chi viene da altri CAD (la wiki lo dice): in 26.3 lo Sketcher usa Esc come OK.
- **Transazione.** La apre il comando o l'entrata in modifica, e dura quanto il pannello: OK conferma (un passo d'annullamento), Annulla la annulla tutta.
- **Per Meridiana.** Pannello attività per gli strumenti a più passi (posa su falda, edificio da tre punti, anteprima di «Correggi»):
  - OK e Annulla in alto, Invio = OK, Esc = Annulla;
  - nel disegno Esc toglie prima l'ultimo punto;
  - all'apertura un'istantanea «prima», OK = un solo passo d'annullamento col nome dello strumento, Annulla = ripristino.
  - Idea, M, **voto 4**.

### 3.2 Editor delle proprietà, quantità, espressioni

- **Editor delle proprietà** [V A2]:
  - schede Vista e Dati in basso;
  - gruppi;
  - menu contestuale con «Show Hidden», espandi e comprimi, aggiungi e rinomina proprietà, «Expression...»;
  - 26.3 aggiunge «Property Uses», cioè chi usa quella proprietà nelle espressioni;
  - ogni modifica in Dati è una transazione «Edit Oggetto.Proprietà» seguita da un ricalcolo.
- **Campi con unità** (`Gui::QuantitySpinBox`) [V A2]:
  - accettano «2 m + 30 cm», «150 cm», «0,8*3 m»;
  - ai pezzi senza unità aggiungono l'unità del campo;
  - punto e virgola valgono entrambi come separatore decimale.
  - **Difetto aperto**: con la virgola decimale «0.5» diventa 5, perché il campo toglie il separatore delle migliaia (issue #22558, aperta dal 18/07/2025).
  - Due grammatiche flex+bison:
    - quantità: numeri, unità, `+ - * / ^`, funzioni, fino a tre quantità accostate;
    - espressioni: riferimenti `Oggetto.Proprietà`, `<<Etichetta>>`, alias del foglio, funzioni, condizioni.
- **Sistemi di unità** [V A2]: Standard (mm), MKS, US, Imperial decimal, Building Euro (cm, m², m³), Building US, Metric small parts, Imperial civil, FEM, Meter decimal. Ognuno è una tabella di soglie: per esempio le lunghezze in mm sotto 10 m, poi in m.
- **Espressioni con «=»** [V A2]:
  - «=» apre un editor a comparsa con completamento e anteprima; l'icona f(x) segna il campo legato;
  - un controllo rifiuta i cicli;
  - è criticato perché interrompe il lavoro (issue #21031).
- **Per Meridiana**:
  - campi con unità e aritmetica, scritti in Python (un parser piccolo o `ast` con una tabella di unità), con punto e virgola decimali, senza mai togliere in silenzio un separatore: S, **voto 5** (si lega a I1-I4 di 12);
  - soglie per mostrare W, kW, MW e kWh, MWh: S, voto 4;
  - riferimenti con «=»: rimandare, voto 2;
  - «dove si usa questo valore» come Property Uses, cioè la genealogia letta al contrario: S-M, voto 3.

### 3.3 Preselezione e selezione

- **Colori** [V A3]:
  - 1.1.4: preselezione gialla #E1E114, selezione verde #1CAD1C (tema Classic); nei temi Light e Dark coppie diverse;
  - **26.3**: preselezione #0AC8FF e selezione #00ABFF in tutti i temi, «better visible in all themes and closer to each other» (PR #31050).
- **Cosa si evidenzia**: l'elemento sotto il cursore (faccia, spigolo, vertice) o l'oggetto.
- **Barra di stato**: «Preselected: Doc.Oggetto.Elemento (x, y, z)» con le unità del documento.
- **Std_ClarifySelection** (1.1): G, G oppure pressione lunga di 1 s; un menu raggruppato per tipo con gli oggetti sotto il cursore e l'anteprima al passaggio.
- **Per Meridiana**:
  - testo di preselezione nella barra di stato («Falda 2, Uffici (12,40; 7,85; z 6,20 m)»): S, **voto 5**;
  - preselezione e selezione in due tinte vicine, più un contorno per non affidarsi al solo colore: S, voto 4;
  - «chiarisci selezione» tra modulo, falda, edificio ed esclusione: `QGraphicsView.items(pos)` dà già l'elenco. S-M, **voto 4**.

### 3.4 Report view e console Python

- **Report** [V A4]: livelli Messaggio, Log, Avviso, Errore, con colori; orario per riga; «mostra il report su errore» spento di base.
- **Notifiche**: un contatore nella barra di stato e avvisi a comparsa di 5-20 s.
- **Console Python**:
  - completamento;
  - ogni comando dell'interfaccia vi compare come riga Python (preferenza accesa);
  - Ctrl+Maiusc+P manda la selezione alla console.
- **Per Meridiana**:
  - niente console: Meridiana non ha un'API di scripting;
  - un registro con livelli e il contatore delle notifiche c'è già nel piano (P7, C3), voto 3;
  - l'eco delle azioni come Python: voto 1.

### 3.5 Macro e annulla a transazioni

- **Macro** [V A5]: la registrazione scrive le righe Python dei comandi in un file .FCMacro; l'Addon Manager distribuisce macro e workbench.
- **Annulla a transazioni**:
  - si salvano solo le proprietà cambiate e gli oggetti creati o cancellati;
  - il pulsante Annulla ha un menu a discesa con i nomi dei passi;
  - limite di **20 passi** e nessun limite di memoria;
  - dopo un annullamento non si ricalcola, perché le forme sono nella transazione.
- **Confronto con Meridiana** (istantanee del progetto intero, esatte per costruzione):

| | FreeCAD | Meridiana |
|---|---|---|
| Cosa si salva | solo ciò che cambia | tutto il progetto, prima e dopo |
| Esattezza | solo se ogni modifica passa da una proprietà registrata | esatta per costruzione |
| Dopo un annullamento | nessun ricalcolo | ripartono posa ed energia |
| Limite | 20 passi | nessuno |

- **Per Meridiana**:
  - tenere le istantanee;
  - aggiungere:
    - il menu a discesa della cronologia: S, voto 4;
    - i risultati derivati in una cache per impronta degli input, così un annullamento non rifà posa ed energia: M, **voto 4**;
    - inizio, conferma e annullamento per i pannelli attività (3.1): S, voto 5.
  - Macro: voto 1.

### 3.6 Ricalcolo degli oggetti «toccati»

- **Come funziona** [V A6]:
  - cambiare una proprietà «tocca» l'oggetto;
  - `Document::recompute` ordina gli oggetti con un ordinamento topologico del grafo delle dipendenze e ricalcola solo chi deve, poi tocca chi dipende;
  - un oggetto in errore ferma ciò che sta a valle.
- **Nell'albero**: un segno blu «da ricalcolare» e uno rosso «errore» col testo nel suggerimento; F5 ricalcola.
- **26.3**: ricalcolo **asincrono** in un thread (PR #21292) e a **grana fine** sulle proprietà (PR #25603), sperimentali ma accesi di base.
- **Per Meridiana**: è la risposta strutturale a P5 di 12 («ogni modifica rifà tutto»).
  - Un grafo dei prodotti: falde → posa per sottocampo → ombre → stringhe → energia → verifiche, con `graphlib.TopologicalSorter` della libreria standard.
  - Ogni modifica sporca solo ciò che sta a valle.
  - Segni «da ricalcolare» ed «errore» su albero e viste.
  - M, **voto 5**, fase 2.

### 3.7 Piano di lavoro di Draft e BIM

- **Codice** [V A7]: `WorkingPlane.py`, Python, LGPL, circa 1.900 righe.
- **Funzioni**:
  - un piano per vista, modalità Auto, cronologia di 10 stati con Precedente e Successivo;
  - piano da faccia, da faccia e spigolo, da tre punti, dalla vista;
  - griglia legata al piano;
  - in 26.3 i valori digitati si bloccano col lucchetto.
- **Per Meridiana**: disegnare sulla falda inclinata, in fase 3.
  - Piano con u lungo la gronda e v lungo la massima pendenza.
  - Cursore proiettato sul piano (in 3D raggio-piano, in pianta verticale).
  - Lunghezze digitate in vera grandezza o in proiezione, dicendo quale.
  - La matematica è poca, si riscrive in numpy. M, **voto 4**.

### 3.8 Workbench, barre, ricerca dei comandi

- **Workbench** [V A8]:
  - si scelgono da una tendina o da schede (1.0); W, 1 ... W, 9;
  - barre e menu cambiano col workbench;
  - pannelli sovrapposti trasparenti (1.0, circa 6.400 righe di C++).
- **Ricerca dei comandi**: **non esiste** nel nucleo, né in 1.1.4 né in 26.3. È la richiesta d'interfaccia con più voti (issue #8290, dal 2023); la PR #25833 è in bozza.
- **Per Meridiana**:
  - le schede (Modello, Produzione, ...) sono già i «workbench»: una barra globale fissa e mai uno strumento doppio tra le schede;
  - la palette Ctrl+Maiusc+P di 12 è un punto in cui Meridiana può fare meglio di FreeCAD: S, **voto 5**;
  - i pannelli sovrapposti: voto 1.

### 3.9 Dialogo delle scorciatoie

- **Dove sta** [V A9]: Strumenti > Personalizza > Tastiera; in 26.3 passa nelle Preferenze.
- **Funzioni**:
  - ricerca con completamento;
  - colonne Comando, Scorciatoia, Predefinita;
  - **i conflitti compaiono mentre si digita**: dopo 200 ms un elenco di priorità dei comandi con la stessa scorciatoia (ShortcutManager);
  - ripristino;
  - esportazione come «preference pack».
- **Conflitti veri**: in 1.1 BIM Nudge usava Ctrl+frecce, già prese dai pannelli; in 26.3 è passato ad Alt+tasti.
- **Per Meridiana**: l'editor richiesto da WCAG 2.1.4 (N6 di 12).
  - Ricerca; conflitti mostrati subito, dicendo cosa smette di funzionare (meglio di FreeCAD, che li mette in un elenco di priorità).
  - Ripristino; esportazione in JSON delle sole differenze; interruttore per le lettere singole.
  - S-M, **voto 5**.

### 3.10 Critiche alla UX di FreeCAD, da non copiare

| Critica | Fonte | Stato |
|---|---|---|
| Nessuna ricerca dei comandi | issue #8290 (28/01/2023, 33 voti) | aperta |
| Strumenti doppi tra workbench (Part e PartDesign, BIM e Draft) | issue #16155, #24894; Design Guide: «Avoid providing multiple ways to achieve the same goal» | aperte |
| Errori incomprensibili («BRep_API: command not done») | issue #19255 | in parte migliorato nella 1.1 |
| La rotella cambia i valori nei campi | issue #17684 | aperta: lo stesso difetto di Meridiana (I2 di 12) |
| Lentezza con preselezione e navigazione su file grandi | issue #17185 | aperta |
| Editor delle espressioni modale | issue #21031 | 26.3 migliora |
| Virgola decimale che moltiplica per 10 | issue #22558 | aperta |
| Esc chiude il pannello attività | wiki Task panel | lo Sketcher in 26.3 cambia |
| Stile di navigazione predefinito diverso da quello di chi viene da altri CAD | 1.1 aggiunge SolidWorks e NX; il primo avvio chiede lo stile | |
| «Steep learning curve, inconsistent workflow, ugly, confusing UI» | Ondsel, B. Collette, 15/11/2023 | il gruppo di design esiste dalla fine del 2023 |
| Volume: 1.074 issue aperte con l'etichetta «Topic: User Interface» | GitHub, 22/10/2026 | |

Fonti: A10.

**Da non copiare**:
- strumenti doppi;
- messaggi senza un'azione suggerita;
- editor modali per cose quotidiane;
- comportamenti nascosti nelle preferenze;
- separatori decimali tolti in silenzio;
- un'evidenza al passaggio che ridisegna tutto.

**Migliorato da 1.0, 1.1 e 26.3** [V A10]:
- temi chiaro e scuro;
- preferenze con ricerca;
- misura unificata;
- suggerimenti dei tasti nella barra di stato;
- Clarify Selection;
- più documenti in modifica;
- ricalcolo a grana fine.

### 3.11 Altro da prendere

[V A11]
- **Misura rapida** (1.0): 100 ms dopo un cambio di selezione la barra di stato mostra area, lunghezza, distanza, angolo.
  - Per Meridiana: con falde o sottocampi selezionati, area, kWp, moduli, azimut e inclinazione.
  - S, **voto 5**.
- **Salva immagine** (Std_ViewScreenShot), con dimensione, proporzioni e sfondo: per le immagini della relazione. S, voto 4.
- **Nudge del BIM**: spostare la selezione con la tastiera, con il passo scelto nella barra di stato. Per spostare edifici ed esclusioni. S, voto 4.
- **Suggerimenti dei tasti** (1.1): le regole della Design Guide, «[tasto] azione», al massimo 6, prima i modificatori. Meridiana li ha già: adottare le regole. S, voto 4.
- **Doppio clic = pannello di modifica** (1.1, BIM): S, voto 4.
- **Allinea alla selezione**: in Meridiana diventa «vista perpendicolare alla falda». S, voto 4.

## 4. BIM e sole

### 4.1 L'oggetto Sito

Fonte: `src/Mod/BIM/ArchSite.py`, Python, LGPL [V B1].

- **Proprietà**:
  - Latitude, Longitude in gradi decimali; Elevation in mm;
  - **Declination**: l'angolo dal +Y del documento al nord vero, **positivo in senso antiorario**;
  - TimeZone in ore intere, senza ora legale;
  - EPWFile, che serve alla rosa dei venti;
  - indirizzo; terreno; sterri e riporti.
- **Vista**:
  - bussola: 4 frecce, il nord rosso, ruotabile;
  - diagramma solare: scala 20 m, posizione, colore;
  - orientamento «Project North» o «True North»;
  - posizione del sole (1.1): data, ora a mezz'ore;
  - etichette delle ore.
- **Diagramma solare.**
  - Codice di FreeCAD che chiede le posizioni del sole a **ladybug** (AGPL) o a **pysolar** (GPL).
  - [V B1, B4] Nessuna delle due è nei pacchetti ufficiali; il Flatpak di Flathub ha pysolar 0.13.
  - [V, prova] Nell'AppImage 1.1.4, accendendo diagramma e sole:
    - «The pysolar module was not found. Unable to generate solar diagrams»;
    - «Ladybug or Pysolar module not found. Cannot calculate sun position.»
- **Errore nella formula** [V codice, I effetto]:
  - il codice converte l'azimut con `az = 90 + azimut` (ArchSite.py righe 184 e 194, uguali in 1.1.4, 26.3 e main);
  - ladybug e pysolar misurano l'azimut dal nord in senso orario;
  - il sole del mattino finisce quindi su −X, cioè a ovest: il diagramma è **specchiato est-ovest**;
  - le etichette delle ore sono «aggiustate» con `h = 24 - h`, commento «not sure why this is needed now... But it is.»;
  - la formula giusta è `az = 90 - azimut`.
- **Posizione del sole** (1.1, PR #22516):
  - sfera gialla, arco del giorno in tre colori (prima delle 10, 10-14, dopo le 14), una linea «Sun Ray» per tracciare le ombre a mano;
  - **non proietta ombre**;
  - in 1.1.4 ignora la Declination; è corretto solo in 26.3 (issue #28471) [V B1].
- **Declination e IFC** [V B2]:
  - in esportazione TrueNorth = (−sin D, cos D);
  - è la stessa convenzione di `ifcopenshell.api.georeference.edit_true_north`;
  - [V, prova] con D = 20 gradi FreeCAD ha scritto (−0,342; 0,940).
- **Per Meridiana**:
  - prendere le idee del pannello del sole di 26.3: data, cursore a mezz'ore, arco colorato, raggio;
  - non il codice;
  - aggiungere un test contro pvlib per non ripetere l'errore est-ovest.
  - S, voto 3.

### 4.2 Ombre e sole negli strumenti per FreeCAD

[V B3]
- La vista 3D di FreeCAD **non ha ombre**, né in 1.1.4 né in 26.3.
- Ci sono solo:
  - immagini con ombre da Python (`OfflineRenderingUtils`);
  - il workbench Render (LGPL, «UNMAINTAINED»), con una luce SunSky che prende un vettore, senza luogo né ora.
- **Per Meridiana**: niente da prendere. Qt Quick 3D ha già le ombre del sole all'ora scelta.

### 4.3 Workbench per il fotovoltaico

[V B4]

| Progetto | Cosa fa | Licenza | Stato |
|---|---|---|---|
| **PVPlant** (JavierBrana) | impianti a terra: terreno da DEM, pendenze, telai e tracker, stringhe, quadri, cavi, scavi, strade, recinzioni, computi, DXF, export verso PVsyst | intestazioni LGPL v2 o successive, **nessun file LICENSE** | fermo dal 14/10/2023, PySide2, non nell'indice degli addon |
| **Solar** (Francisco-Rosa) | percorso del sole animato, analisi d'irraggiamento (ladybug-radiance più Radiance), ombre in bianco e nero, scrive latitudine, longitudine e Declination nel Sito | LGPL-2.1-or-later, ma dipende da ladybug (AGPL) e pysolar (GPL) | attivo: nato il 13/07/2025, ultimo commit 10/10/2026, nell'indice ufficiale |
| **FreePVC** (darkmatter11235) | «alternativa a PVCase» per impianti a terra, con server MCP e ombre con pvlib | MIT | nato il 14/02/2026, ultimo commit 28/07/2026, nessuna stella |

**Per Meridiana**:
- nessun codice da prendere: PVPlant andrebbe chiesto all'autore;
- la compatibilità utile è l'IFC con un Sito georiferito, che Solar e il BIM sanno leggere;
- collaborare: voto 2;
- essere compatibili via IFC: voto 4 (sezione 5).

## 5. Compatibilità reciproca

### 5.1 (a) Gesti: un profilo «FreeCAD» dentro Meridiana

- Il profilo è lo stile «CAD» di 2.6 (il mouse) più i tasti di vista di FreeCAD (2.3).
- Con i tasti di 12a ci sono conflitti, da risolvere solo dentro questo profilo, senza cambiare il predefinito:

| Tasto | FreeCAD | Meridiana (12a) | Conflitto | Proposta per il profilo «FreeCAD» |
|---|---|---|---|---|
| 0-6 | viste standard | le cifre sono delle lunghezze digitate | **sì** | attive solo con il fuoco nella vista 3D e nessuno strumento di disegno attivo; tastierino come in 12a |
| V, F / V, S / V, O / V, P | adatta tutto / selezione / ortogonale / prospettica | V = Seleziona (lettera singola) | **sì** | V diventa un prefisso; Seleziona con Esc; F resta «inquadra» |
| Spazio | mostra/nasconde | Spazio tenuto = pan | **sì** | tenere il pan di Meridiana |
| Esc | navigazione/modifica | esce dallo strumento | in parte | tenere quello di Meridiana |
| Ctrl+B | zoom a riquadro | pannello Progetto (VS Code) | **sì** | tenere Ctrl+B; zoom a riquadro = Z |
| Ctrl+Maiusc+P | invia alla console Python | palette dei comandi | sì, ma Meridiana non ha console | tenere la palette |
| frecce | pan | in 3D orbita di 15 gradi, in pianta pan | in parte | nel profilo le frecce fanno pan anche in 3D |
| Maiusc+← → | ruota di 90 gradi | Maiusc+frecce, 90 gradi | no | uguale |
| Inizio | vista Home | vista iniziale | no | uguale |
| Fine / Maiusc+Fine | richiama / memorizza la vista di lavoro | libero | no | aggiungere in tutti i profili |
| PagSu / PagGiù, Ctrl++ / Ctrl+- | zoom | Ctrl++ / Ctrl+- | no | aggiungere PagSu e PagGiù |
| Maiusc+B | selezione a riquadro | libero | no | aggiungere |
| G, G e pressione lunga | chiarisci selezione | libero | no | aggiungere in tutti i profili |
| F5 | ricalcola | ricalcola subito | no | uguale |
| Ctrl+0 (26.3) | pannelli in basso | schermo pulito | no, senso vicino | uguale |
| F11 | schermo intero | sul Framework è Stamp, che su Niri apre lo screenshot | rischio | solo menu (regola 2 di 12) |

- Fatica: con A3 il mouse dello stile «CAD» c'è già; restano i tasti di vista, quindi S.
- **Voto 4**: costa poco e dà a un utente FreeCAD le mani al posto giusto.

### 5.2 (b) IFC: la via principale

**Esportazione da Meridiana** [V, prova].
- **Script.** `meridiana_ifc.py` (470 righe):
  - carica un .meridiana con il codice di Meridiana;
  - fa la posa (`Project.fill`);
  - scrive un IFC4 con ifcopenshell 0.9.0.post1 (Python 3.15, sul laptop).
- **Contenuto del file**:
  - progetto in metri, gradi e watt;
  - contesto Model/Body con il TrueNorth;
  - IfcSite con RefLatitude e RefLongitude **con i milionesimi di secondo** e, a richiesta, una IfcMapConversion su UTM 32N (EPSG:32632) con la convergenza (0,0214 gradi a Rho);
  - un IfcBuilding con un piano per edificio;
  - pareti (il profilo del lato fino al tetto, estruso verso l'interno);
  - IfcRoof con un IfcSlab ROOF per falda;
  - parapetti IfcWall PARAPET, camino IfcChimney, impianto in copertura IfcBuildingElementProxy, albero IfcGeographicElement;
  - un IfcSolarDeviceType SOLARPANEL con la forma condivisa e **188 IfcSolarDevice** con IfcMappedItem;
  - i Pset:
    - Pset_ManufacturerTypeInformation e Pset_SolarDeviceTypeCommon;
    - `Meridiana_DatiModulo`: Pmax, Voc, Isc, Vmp, Imp, efficienza, dimensioni;
    - `Meridiana_Modulo`: sottocampo, fila, posto, inclinazione, azimut CEI, potenza;
    - `Meridiana_Falda`, `Meridiana_Ostacolo`;
  - un IfcGroup per sottocampo.
- **Esito**:
  - 351 kB, 1,3 s;
  - `ifcopenshell.validate`: nessun problema di schema (senza le regole EXPRESS);
  - una seconda versione ruotata di 30 gradi con il TrueNorth corrispondente, per provare il nord.

**FreeCAD 1.1.4 apre l'IFC di Meridiana** [V, prova; AppImage, console e interfaccia].

| Cosa | NativeIFC (File > Apri, il predefinito) | Importatore classico |
|---|---|---|
| Esito | 211 oggetti in 12 s; immagini in `risultati` | **non parte**: `AttributeError: 'Settings' object has no attribute 'USE_BREP_DATA'`. Usa ancora una costante di ifcopenshell 0.7 che la 0.8.4, inclusa nell'AppImage, non ha più (importIFC.py riga 242, uguale in 26.3) |
| Geometria | esatta: il modulo campione sta in (28655; 17784,55; 9868,45) mm, normale (0; −0,259; 0,966), volume 61.236.000 mm³ = 1,134 × 1,8 × 0,03 m | |
| Classi | IfcSolarDevice ×188 col loro PredefinedType; IfcWall ×12; IfcRoof ×2 con dentro le forme delle falde (gli IfcSlab non diventano oggetti a sé); camino, proxy, elemento geografico. Gli IfcGroup non vengono caricati | |
| Pset | con `show_psets`: inclinazione e azimut come **angoli in gradi** (il file usa i gradi), interi e testi giusti. La potenza (IfcPowerMeasure) diventa un testo «495.» | |
| Sito | RefElevation c'è, ma **RefLatitude e RefLongitude non compaiono** | sarebbe un Arch Site con Latitude, Longitude e Declination |
| Nord | **ignorato**: il file ruotato appare ruotato e nessuna proprietà dice dov'è il nord | il TrueNorth diventerebbe la Declination [V codice B2] |

Perché manca la latitudine [V codice]: in `ifc_tools.py` (1.1.4, righe 676-702, stesso ordine in 26.3) il ramo per le liste viene prima di quello pensato per RefLatitude e RefLongitude. Una lista di quattro interi entra lì e non crea nulla. Correzione di una riga: spostare il ramo.

**Il contrario: FreeCAD esporta, Meridiana legge** [V, prova].
- **In FreeCAD**, con l'API Python del BIM (`fc_crea_bim.py`): Sito con latitudine 45,5226, longitudine 9,03, quota 150 m, Declination 20 gradi; pareti, tetto a capanna di 30 gradi, un modulo come Equipment «Solar Device» SOLARPANEL; esportazione con exportIFC.
- **Il file** (5,7 kB, IFC4, metri e gradi):
  - RefLatitude (45, 31, 21) e RefLongitude (**9, 1, 47**): troncati al secondo intero;
    - 45,5226 vale 45 gradi 31 primi 21,36 secondi;
    - 9,03 vale 9 gradi 1 primo 48,0 secondi, ma in virgola mobile è 47,9999, e il troncamento fa 47;
    - errore di circa 11 m in latitudine e 22 m in longitudine; può arrivare a 31 m in latitudine;
  - RefElevation 150 m: giusta;
  - TrueNorth (−0,342; 0,940) = Declination 20 gradi in senso antiorario: giusto;
  - parete **IfcWall .MOVABLE.** e tetto a capanna **IfcRoof .FLAT_ROOF.**: è il primo valore dell'elenco, il predefinito degli oggetti Arch [V, prova; I sulla causa];
  - modulo IfcSolarDevice SOLARPANEL con IfcFacetedBrep.
- **In Meridiana**: `leggi_ifc.py` (ifcopenshell 0.9) legge il file, ruota tutto sul nord vero e ricava:
  - edificio ruotato di 20 gradi;
  - due falde di 30 gradi con azimut CEI −160 e +20;
  - il modulo a 30 gradi con azimut +20;
  - gronda 6,0 m.
  - Coerente col modello di partenza.

**Andata e ritorno di Meridiana** [V, prova]. `leggi_ifc.py` sui due file di Meridiana ritrova:
- i contorni esatti: 40 × 20 m e 20 × 8 m;
- le gronde: 9,5 e 13,0 m;
- le falde: piana e due di 25 gradi con azimut 0 e 180;
- 188 moduli a 15 gradi e azimut 0, con il primo centro uguale a quello di Meridiana;
- camino, impianto e albero.
La versione ruotata di 30 gradi dà **le stesse coordinate sul nord vero**.

**Un IFC di terzi** [V, prova]. Il campione «Building-Architecture.ifc» di buildingSMART, scritto da «IFC manager for sketchup», mostra cosa aspettarsi:
- millimetri;
- due IfcSite, con la copertura appesa al secondo e non all'edificio;
- falde IfcSlab senza PredefinedType, raccolte in un IfcRoof;
- nessuna RefLatitude;
- una IfcMapConversion con Scale 0,001 e asse X ruotato di 60 gradi, mentre il TrueNorth dice +Y.
Con due regole in più (falde = figlie di un IfcRoof; elementi senza edificio assegnati all'edificio che coprono) il lettore trova due falde di 45 gradi verso est e ovest.

**Regole che ne vengono per il lettore di Meridiana** [I]:
- il nord dal TrueNorth, ma se c'è una IfcMapConversion vale il suo asse X, più la convergenza della proiezione; se le due cose non tornano, chiedere;
- latitudine e longitudine di FreeCAD possono essere sbagliate di decine di metri: se c'è la mappa (IfcMapConversion o il punto scelto sull'ortofoto), vince la mappa;
- le falde si riconoscono dalla geometria (facce rivolte verso l'alto di IfcRoof, delle sue parti, di IfcSlab ROOF, di IfcCovering ROOFING), non dal PredefinedType;
- il contorno dell'edificio viene dalle pareti, non dalla copertura, che ha le sporgenze;
- tolleranza: elementi fuori dall'edificio, più siti, unità diverse;
- un'anteprima con conferma prima di creare gli edifici.

**Opzioni per l'esportazione**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| E1. ifcopenshell come dipendenza (LGPL-3.0-or-later) | 5 | 4 | 4 | il prototipo funziona; ruota da 43 MB su Windows e 55 MB su Linux, ma solo numpy, shapely e quattro librerie leggere come dipendenze; c'è per Python 3.10-3.15 su Windows, macOS e Linux [V] |
| E2. Scrittore IFC proprio (il formato STEP è testo) | 3 | 2 | 2 | nessuna dipendenza, ma tutta la correttezza è a carico nostro e per leggere servirebbe comunque ifcopenshell |
| E3. Solo .FCStd | 2 | 2 | 3 | vedi 5.3 |

**Raccomandazione: E1**, come dipendenza facoltativa caricata solo quando si esporta o si importa.

### 5.3 (c) Il formato .FCStd

- **Struttura** [V B5]:
  - uno ZIP con `Document.xml`, `GuiDocument.xml` e i file delle forme (BREP in testo di OpenCascade, oppure binari);
  - le mappe della nomenclatura topologica;
  - la miniatura.
- **Regole del formato**:
  - Document.xml ha `SchemaVersion="4"`;
  - per oggetto: tipo C++, proprietà con il loro tipo, Placement con quaternione e asse-angolo;
  - lo stato dei FeaturePython è JSON in base64;
  - i file laterali vanno nell'ordine in cui l'XML li cita, perché il lettore cerca solo in avanti.
- **Si può scrivere senza FreeCAD?** **Sì** [V, prova]:
  - `genera_fcstd_minimo.py` (scritto in questo studio) produce 1,7 kB con 15 oggetti: Part::Polygon, Part::Extrusion, Part::Box, un gruppo;
  - FreeCAD 1.1.4 lo apre, ricalcola tutto (edificio 20 × 10 × 6 m = 1.200 m³, falde, 8 moduli da 0,0904 m³), nessun errore, e lo risalva (16 kB).
- **Si può leggere?** Lo ZIP e l'XML sì; per le forme serve un lettore BREP. Su PyPI non c'è una libreria; cadmpeg (Rust, Apache-2.0) ha una specifica indipendente [V B5].
- **Contro**:
  - formato interno, senza specifica ufficiale;
  - la mappa topologica cambia (versione 4 → 5 nella 1.1);
  - dalla 1.1.2 i Proxy si caricano solo da moduli installati e i nomi dei file laterali sono controllati; la 1.1.4 corregge due ZipSlip;
  - con gli oggetti del BIM servirebbe che FreeCAD li ricostruisse.
- **Voto 2**: utile solo come uscita di comodo, per esempio «apri in FreeCAD» con oggetti Part. L'IFC fa meglio lo stesso lavoro. Fatica S.

### 5.4 (d) Una macro o un workbench per FreeCAD

**Prova** [V, prova]: `importa_meridiana.FCMacro`, 150 righe.
- **Dentro FreeCAD gira il codice di Meridiana**: model, roofs, layout, sun, geo, perché l'AppImage ha Python 3.11.14, numpy 1.26.4 e shapely 2.1.2.
- La macro carica il .meridiana, fa la posa e costruisce:
  - Arch Site con latitudine e longitudine;
  - due Building con il corpo (Structure) e le falde (Roof da solido);
  - ostacoli come Equipment con il loro IfcType;
  - **188 moduli** come Equipment «Solar Device» SOLARPANEL.
- **Esito**:
  - 404 oggetti in 3,2 s in console, 5,6 s nell'interfaccia; nessun errore;
  - FreeCAD li esporta in IFC (292 kB, 2,0 s);
  - `leggi_ifc.py` ritrova la stessa geometria (contorni, falde, 188 moduli a 15 gradi); latitudine e longitudine sono di nuovo troncate;
  - acceso il diagramma solare sul Sito: manca pysolar (4.1).

**API usate** [V B6]:
- `Arch.makeSite`, `makeBuilding`, `makeStructure`, `makeRoof` (con una base solida ne usa la forma), `makeEquipment` più `IfcType = "Solar Device"` e `PredefinedType = "SOLARPANEL"`;
- `Part` per contorni ed estrusioni;
- unità in mm.

**Un addon vero** [V B6, I sulla fatica]:
- **Struttura**:
  - `freecad/meridiana/init.py` e `init_gui.py`;
  - `package.xml` per l'Addon Manager, con licenza GPL-3.0-or-later ammessa;
  - `FreeCAD.addImportType("Meridiana (*.meridiana)", "importMeridiana")` con `open`, `insert` e `export`.
- **Due strade**:

| Strada | Fatica | Pro | Contro |
|---|---|---|---|
| D1. Oggetti del BIM, come la macro | 3-5 giorni per l'apertura; 5-8 con il ritorno verso Meridiana (sito, contorni, falde, ostacoli) | Arch Site vero (bussola, sole se c'è pysolar); oggetti modificabili | due ambienti Python (3.11 di FreeCAD, 3.12-3.15 di Meridiana); il codice di Meridiana va copiato dentro l'addon o installato; un oggetto Python per modulo pesa sui progetti grandi [I] |
| D2. L'addon chiama l'esportatore IFC di Meridiana e apre il file con NativeIFC | 1-2 giorni, dopo E1 | un solo formato da mantenere | il sito resta senza latitudine finché FreeCAD non corregge NativeIFC; niente sole del BIM |

**Raccomandazione**: dopo l'IFC, e solo se Daniel o un collega usano FreeCAD.
- Prima D2, quasi gratis.
- D1 se si vuole modificare in FreeCAD e tornare in Meridiana.
- **Voto 3.**

### 5.5 Quale compatibilità costruire, e in che ordine

1. **Esportazione IFC4 da Meridiana** (E1): 3-4 giorni.
   - Il modulo senza Qt, dal prototipo.
   - Test di andata e ritorno con il lettore e `ifcopenshell.validate`.
   - Voce «Esporta IFC4...» e opzioni: nord di progetto, IfcMapConversion su UTM o RDN2008.
   - Pset con nomi stabili e dipendenza nel pacchetto.
   - **Voto 5. Fase 3**, prima voce.
2. **Lettura di un IFC** per avere edifici e falde: 5-8 giorni, con l'anteprima e la conferma.
   - Rientra nell'«edificio da modello» che Meridiana non ha ancora.
   - Voto 4, fase 3.
3. **Tasti di vista di FreeCAD nello stile «CAD»** (5.1): S, dopo gli stili della fase 2. Voto 4.
4. **Segnalare i cinque problemi** trovati a FreeCAD, con i file di prova come allegato.
   - Le prime tre correzioni sono piccole: latitudine in NativeIFC, troncamento al secondo, costante di ifcopenshell 0.8.
   - Mezza giornata per scrivere le issue.
   - È la «collaborazione» più utile: rende FreeCAD un lettore affidabile dei file di Meridiana.
   - Voto 5. Decide Daniel se e quando.
5. **Addon per FreeCAD** (D2, poi D1): voto 3, più avanti.
6. **.FCStd**: no, voto 2.

## 6. Cosa «rubare»: tabella dei candidati

| Candidato | Codice o idea | Linguaggio | Licenza | Fatica | Voto | Fase |
|---|---|---|---|---|---|---|
| Stili di navigazione (tabelle, clic centrale che ricentra, perno, indicatore) | idea: le classi C++ hanno logica copiata, conviene una tabella dati | C++ | LGPL-2.1-or-later | M | 5 | 2 |
| NaviCube (26 parti, frecce, orientamento più vicino, doppio clic, trascinamento, menu, etichette libere) | idea; la matematica di `getNearestOrientation` (100 righe) si può tradurre | C++ | LGPL-2.1-or-later | M | 5 | 2 |
| Campo Quantity e parser delle unità | idea: grammatiche flex+bison legate a Base::Unit; in Python si riscrive in 200-300 righe | C++ | LGPL | S | 5 | 2 |
| Espressioni con «=» | idea, più avanti | C++ | LGPL | L | 2 | - |
| Pannello attività con transazione | idea | C++ | LGPL | M | 4 | 3 |
| Dialogo delle scorciatoie con conflitti in diretta | idea | C++ | LGPL | S-M | 5 | 2 |
| Preselezione nella barra di stato e misura rapida | idea | C++ | LGPL | S | 5 | 2 |
| Chiarisci selezione (G, G, pressione lunga) | idea | C++ | LGPL | S-M | 4 | 3 |
| Ricalcolo degli oggetti toccati (grafo, segni) | idea | C++ | LGPL | M | 5 | 2 |
| Piano di lavoro (WorkingPlane.py) | codice traducibile: Python | Python | LGPL-2.1-or-later | M | 4 | 3 |
| Diagramma solare del Sito | solo idea (dipende da pysolar o ladybug, ed è specchiato) | Python | LGPL | S | 2 | 3 |
| Pannello del sole di 26.3 (data, mezz'ore, arco in tre colori, raggio) | idea | Python | LGPL | S | 3 | 3 |
| Snapper di Draft | già in 07: idee | Python | LGPL | - | - | - |
| Esportatore IFC (exportIFC.py) | no: Meridiana scrive meglio con ifcopenshell.api (prova 5.2) | Python | LGPL | - | 1 | - |
| Nudge del BIM, salva immagine, suggerimenti dei tasti | idea | Python e C++ | LGPL | S | 4 | 3 |

## 7. Cosa entra nel piano di 12

**Fase 2** (chiarezza e navigazione), in aggiunta o a precisazione:
- **T1-T3 e i profili**:
  - modulo degli stili di navigazione (2.6, A3): gli stessi di FreeCAD come tabelle di dati, più «AutoCAD» e «SketchUp»; il predefinito lo decide Daniel;
  - clic centrale che ricentra; perno sotto il cursore con indicatore; orbita Turntable;
  - animazioni di 250 ms;
  - cubo con la struttura del NaviCube e facce N, E, S, O.
- **I1-I4**: campi con unità e aritmetica (3.2).
- **V3 e T4**: testo di preselezione con coordinate nella barra di stato; misura rapida della selezione (3.3, 3.11).
- **N6**: editor delle scorciatoie con conflitti in diretta (3.9).
- **P5**: grafo dei prodotti con ricalcolo a valle e segni «da ricalcolare» ed «errore» (3.6).

**Fase 3**:
- **Esportazione IFC4** (5.5, punto 1), poi **lettura IFC** (punto 2).
- Pannello attività con OK e Annulla legati all'istantanea (3.1).
- Piano di lavoro sulla falda (3.7).
- Chiarisci selezione (3.3).
- Pannello del sole come 26.3, con il test contro pvlib (4.1).
- I tasti di vista di FreeCAD nello stile «CAD» (5.1).
- Issue a FreeCAD (5.5, punto 4).

## 8. Le prove fatte

Tutte sul laptop Lucciola (Fedora 45, Niri, Wayland con Xwayland), FreeCAD 1.1.4 AppImage. Script in `C:\Users\utente\dev\meridiana-prove\freecad-2026-10-22`, risultati in `C:\Users\utente\dev\meridiana-prove\freecad-2026-10-22\risultati`.

| Prova | Script | Esito [V, prova] |
|---|---|---|
| Meridiana → IFC4 | `C:\Users\utente\dev\meridiana-prove\freecad-2026-10-22\meridiana_ifc.py` | `capannone.ifc` (nord su +Y) e `capannone_nord30.ifc` (progetto ruotato di 30 gradi); 188 moduli; validazione senza problemi |
| FreeCAD apre l'IFC (console) | `fc_leggi_ifc.py` con `fc_env.sh` | NativeIFC: geometria, posizioni e Pset giusti; latitudine e longitudine del sito assenti; nord ignorato. Importatore classico: si ferma su `USE_BREP_DATA` (`risultati\fc_leggi_ifc.json`) |
| FreeCAD apre l'IFC (interfaccia, immagini dalla finestra di FreeCAD) | `fc_screenshot.py` | `capannone_iso.png`, `capannone_alto.png`, `capannone_sud.png`, `capannone_finestra.png` e i quattro del file ruotato; stile di navigazione CAD; FRONT = vista da sud |
| FreeCAD BIM → IFC → ifcopenshell | `fc_crea_bim.py`, `leggi_ifc.py` | latitudine e longitudine troncate al secondo; TrueNorth giusto; MOVABLE e FLAT_ROOF; falde e modulo ritrovati (`risultati\leggi_ifc.json`) |
| Andata e ritorno di Meridiana, e un IFC di terzi | `leggi_ifc.py` | contorni, gronde, falde, moduli e ostacoli identici; stesse coordinate col nord ruotato; campione buildingSMART letto con due regole in più |
| .FCStd scritto a mano | `genera_fcstd_minimo.py`, `fc_apri_fcstd.py` | aperto, ricalcolato, valido, risalvato (`risultati\minimo_aperto.json`) |
| Macro che apre un .meridiana | `importa_meridiana.FCMacro`, `fc_macro_gui.py` | 404 oggetti in 3,2 s; IFC di FreeCAD da 292 kB riletto giusto; diagramma solare e sole: manca pysolar (`risultati\da_macro_gui.json`, `da_macro_iso.png`) |

Note sulle prove:
- **Configurazione isolata.** FreeCAD è stato lanciato con `FREECAD_USER_HOME` e `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` in `~/fvtest/freecad/home`: nella home di Daniel non è stato creato nulla di FreeCAD (controllato).
- **Xwayland e driver.** L'AppImage forza Xwayland (`QT_QPA_PLATFORM=xcb` nel suo AppRun) e la sua Mesa non carica il driver AMD del laptop («failed to load driver: radeonsi»): la vista 3D va, probabilmente con il disegno software [V log, I effetto]. Il Flatpak non è stato provato.
- **Immagini.** Nell'interfaccia le animazioni di vista (500 ms) vanno spente prima di salvare un'immagine, altrimenti esce vuota (successo alla prima prova).
- **Il lettore** (`leggi_ifc.py`) è un prototipo: tiene le facce rivolte verso l'alto e scarta le superfici piccole. Sui file di FreeCAD e di Meridiana basta; per i file di terzi servono altre regole (5.2).

## 9. Cosa è stato installato, e dove

Sul laptop:
- **FreeCAD 1.1.4 AppImage** ufficiale (821 MB, somma SHA-256 controllata):
  - in `~/fvtest/freecad`, con gli script in `prove`, i risultati in `out`, la configurazione isolata in `home`, il campione buildingSMART in `terzi`;
  - in tutto 789 MB.
  - Nessun Flatpak installato.
- **Venv con ifcopenshell 0.9.0.post1, shapely 2.2.0, numpy 2.5.4** (Python 3.15), 301 MB.
  - **Per un mio errore** è finito in `~/venv` invece che in `~/fvtest/freecad/venv`: un `cd` finito in un processo in background.
  - Contiene solo questi pacchetti, creati alle 15:59 del 22/10/2026.
  - Non ho potuto cancellarlo né spostarlo: il permesso è stato negato.
  - Si toglie con `rm -rf ~/venv`.
  - Controllato la sera del 22/10/2026, senza toccarlo: creato alle 15:59:50 con `python3 -m venv ~/venv`, nessun file più vecchio, nessun file di avvio della shell lo nomina. Toglierlo lo decide Daniel.
- Nessun processo di FreeCAD rimasto acceso; i punti di montaggio dell'AppImage sono stati smontati (controllato).

Su Windows: nulla installato, nessuna finestra aperta.

## 10. Limiti e cose aperte

- **Fonti non raggiunte.**
  - La wiki di FreeCAD è dietro Anubis, una prova di lavoro anti-bot che non è stata aggirata.
  - Sono state usate la copia ufficiale su GitHub (15/01/2025, vecchia) e gli snapshot della Wayback Machine. Per la pagina della navigazione lo snapshot del 06/02/2026: quelli successivi hanno archiviato la pagina anti-bot.
  - La Wayback ha poi bloccato le richieste ripetute.
  - Il forum non è stato letto: le critiche UX vengono da GitHub, dalla Design Guide, da Ondsel, da Libre Arts e dal blog ufficiale.
- **Non provato**:
  - 26.3 (le sue novità sono lette nel codice);
  - il Flatpak, con pysolar: diagramma e sole;
  - lo specchio est-ovest del diagramma solare, che resta [I];
  - l'importatore classico con ifcopenshell 0.7, che è l'unico che leggerebbe nord e latitudine.
- **Da verificare con un utente AutoCAD** (Daniel): se con lo stile «Revit», orbita Turntable e perno «Drag at cursor» FreeCAD si sente davvero come AutoCAD.

## Fonti

Consultate il 22/10/2026. Prefissi:
- **114** = https://github.com/FreeCAD/FreeCAD/blob/4fd3bf320d9566a27e60069fc8387448aaa3a094/
- **263** = https://github.com/FreeCAD/FreeCAD/blob/9fb16e7f981adb09f7d7f130ce085d68e9825358/
- **main** = https://github.com/FreeCAD/FreeCAD/blob/d3f4da791daa9e94f340b81770d13f090ec679c6/

**Generali**
- F1 https://github.com/FreeCAD/FreeCAD/releases/tag/1.1.4
- F2 https://github.com/FreeCAD/FreeCAD/releases/tag/26.3rc2
- F3 https://blog.freecad.org/2026/06/26/new-freecad-versioning-scheme-and-development-cycle/ ; https://blog.freecad.org/2026/10/18/freecad-26-3-release-candidate-2/
- F4 Pacchetti:
  - 114 package/rattler-build/recipe.yaml#L140-L185 e pixi.lock#L94;
  - 263 pixi.toml#L37-L61;
  - https://github.com/flathub/org.freecad.FreeCAD/blob/f043288fa86f6e780aaefdbc5a0aa6cdef5f3fb4/org.freecad.FreeCAD.yaml#L476-L504;
  - versioni dell'AppImage lette sul laptop [V, prova].
- F5 114 LICENSE#L211-L221

**Navigazione (N)**
- N1 263 src/Gui/Navigation/CADNavigationStyle.cpp#L45-L62 (descrizione), #L106-L230 (pulsanti), #L261-L325 (combinazioni); 114 stesso file #L45-L62, #L253-L320.
- N2 263 src/Gui/Navigation/RevitNavigationStyle.cpp#L47-L61, #L253-L300; 114 #L47-L61, #L245-L290.
- N3 263 src/Gui/Navigation/:
  - BlenderNavigationStyle.cpp#L45;
  - SolidWorksNavigationStyle.cpp#L45;
  - SiemensNXNavigationStyle.cpp#L40-L170 e #L419;
  - InventorNavigationStyle.cpp#L46;
  - OpenCascadeNavigationStyle.cpp#L45;
  - OpenSCADNavigationStyle.cpp#L45;
  - TinkerCADNavigationStyle.cpp#L45;
  - TouchpadNavigationStyle.cpp#L44;
  - GestureNavigationStyle.cpp#L951;
  - MayaGestureNavigationStyle.cpp#L95.
- N4 Stile predefinito:
  - 114 src/Gui/PreferencePages/DlgSettingsNavigation.cpp#L168;
  - 114 src/Gui/View3DSettings.cpp#L292;
  - 114 src/Mod/Start/Gui/GeneralSettingsWidget.cpp#L246;
  - 263 src/Gui/PreferencePages/DlgSettingsNavigation.cpp#L180-L181;
  - 263 src/Gui/View3DSettings.cpp#L284-L285.
- N5 Tipo di orbita: 114 DlgSettingsNavigation.cpp#L174; 114 View3DSettings.cpp#L300; 114 src/Gui/Navigation/NavigationStyle.h#L118-L125.
- N6 Perno:
  - 114 src/Gui/Navigation/NavigationStyle.cpp#L381;
  - 114 DlgSettingsNavigation.cpp#L178 e #L184;
  - 114 View3DSettings.cpp#L336;
  - 263 src/Gui/PreferencePages/DlgSettingsNavigation.ui#L521-L555;
  - 263 src/Gui/Navigation/NavigationStyle.cpp#L1556-L1630.
- N7 Zoom e rotella:
  - 263 src/Gui/Navigation/NavigationStyle.cpp#L485-L493 e #L2560-L2635;
  - 114 src/Gui/Navigation/NavigationStyle.cpp#L2029-L2037;
  - 263 DlgSettingsNavigation.ui#L737-L755.
- N8 Ricentrare: 263 src/Gui/Navigation/NavigationStyle.cpp#L582-L624; 263 CADNavigationStyle.cpp#L190-L200.
- N9 Animazioni: 114 src/Gui/View3DInventorViewer.cpp#L3929-L3933; 263 DlgSettingsNavigation.ui#L825-L851; 114 DlgSettingsNavigation.cpp#L187.
- N10 Scorciatoie di vista:
  - 114 src/Gui/CommandView.cpp#L141, #L193, #L1357, #L1415, #L1536, #L1606, #L1656, #L1686, #L2871, #L2905, #L4171, #L4235;
  - 263 src/Gui/CommandView.cpp#L3862.
- N11 114 src/Gui/CommandFeat.cpp#L200-L215 (Ctrl+Maiusc+P).
- N12 NaviCube:
  - 114 src/Gui/NaviCube.cpp#L1-L12 (licenza), #L84-L121 (parti), #L1374-L1400 (menu);
  - 263 src/Gui/NaviCube.cpp#L1-L4, #L538-L636 (rotazioni), #L959-L1055 (orientamento più vicino), #L1057-L1157 (clic, doppio clic, pulsanti), #L1180-L1260 (trascinamento), #L1415-L1452 (menu);
  - 263 src/Gui/View3DSettings.cpp#L561-L681 (opzioni);
  - commit https://github.com/FreeCAD/FreeCAD/commit/e2b233eab1 , /commit/3b9f450c4b , /commit/4afb67a509 , /commit/8d7fa63898 , /commit/d2aa4a5a85
- N13 Wiki «Mouse navigation», revisione oldid=1697080: http://web.archive.org/web/20260206203841/https://wiki.freecad.org/Mouse_navigation ; copia ufficiale (15/01/2025): https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Mouse_navigation.md
- N14 Novità 26.3, commit:
  - https://github.com/FreeCAD/FreeCAD/commit/12a68e8c2c (riquadro);
  - /commit/3282ccce13 (touchpad);
  - /commit/7b4770c3f2 (menu);
  - /commit/00b0c9b43d e /commit/d931edb3ef (orbita vincolata e blocco dell'orientamento);
  - 114 src/Gui/Navigation/NavigationStyle.cpp#L2090 (il sottomenu in 1.1.4).

**Modellazione e interfaccia (A)**. Tutte le righe sono nel rapporto di ricerca `C:\Users\utente\dev\meridiana-prove\freecad-2026-10-22\ricerca\rapporto-modellazione-interfaccia.md`; qui le principali:
- A1 Pannello attività:
  - 114 src/Gui/TaskView/TaskDialog.h#L58-L211;
  - 114 src/Gui/TaskView/TaskView.cpp#L397-L460 e #L609-L675;
  - 114 src/Gui/Control.cpp#L148-L263;
  - 114 src/Gui/Document.cpp#L680-L760;
  - 263 src/Gui/TaskView/TaskView.cpp#L353-L477;
  - Design Guide https://github.com/FreeCAD/DevelopersHandbook/blob/575217fca3d06bfc6157b9b14f41cde482774116/designguide/elements.md#L33-L46
- A2 Proprietà, quantità, espressioni:
  - 114 src/Gui/propertyeditor/PropertyEditor.cpp#L388-L473 e #L792-L1075;
  - 114 src/Gui/QuantitySpinBox.cpp#L88-L299;
  - 114 src/Gui/InputField.cpp#L205-L280;
  - 114 src/Base/Quantity.l#L43-L242 e Quantity.y#L33-L85;
  - 114 src/App/Expression.y#L64-L190;
  - 114 src/Gui/Dialogs/DlgExpressionInput.cpp#L76-L273;
  - 114 src/Base/UnitsSchemasData.h#L53-L642;
  - issue https://github.com/FreeCAD/FreeCAD/issues/22558 e /issues/21031
- A3 Selezione:
  - 114 src/Gui/PreferencePages/DlgSettingsSelection.ui#L24-L176;
  - 114 src/Gui/Selection/Selection.cpp#L970-L1012;
  - 114 src/Gui/CommandView.cpp#L4218-L4290;
  - 263 src/Gui/Selection/SelectionColors.h#L32-L63;
  - PR https://github.com/FreeCAD/FreeCAD/pull/31050 e /pull/22029
- A4 Report e console: 114 src/Gui/ReportView.cpp#L140-L263; 114 src/Gui/PreferencePages/DlgSettingsReportView.ui#L121-L517; 114 src/Gui/PreferencePages/DlgSettingsMacro.ui#L139-L201.
- A5 Macro e annulla:
  - 114 src/Gui/Command.cpp#L446-L789;
  - 114 src/Gui/Macro.cpp#L54-L336;
  - 114 src/App/Document.cpp#L157-L523;
  - 114 src/App/Transactions.cpp#L108-L269;
  - 114 src/Gui/Dialogs/DlgUndoRedo.cpp#L55-L79.
- A6 Ricalcolo:
  - 114 src/App/DocumentObject.cpp#L214-L325;
  - 114 src/App/Document.cpp#L2429-L2800;
  - 114 src/Gui/Tree.cpp#L1179-L1194;
  - 263 src/App/Application.cpp#L805-L864;
  - PR https://github.com/FreeCAD/FreeCAD/pull/21292 e /pull/25603
- A7 Piano di lavoro: 114 src/Mod/Draft/WorkingPlane.py#L61-L620 e #L1190-L1843; 263 src/Mod/Draft/WorkingPlane.py#L247-L320.
- A8 Workbench e barre: 114 src/Gui/WorkbenchSelector.cpp#L46-L130; 114 src/Gui/CommandCompleter.cpp#L94-L161; issue https://github.com/FreeCAD/FreeCAD/issues/8290 ; PR /pull/25833
- A9 Scorciatoie:
  - 114 src/Gui/Dialogs/DlgKeyboard.ui#L37-L304;
  - 114 src/Gui/Dialogs/DlgKeyboardImp.cpp#L145-L402;
  - 114 src/Gui/ShortcutManager.cpp#L188-L413;
  - 263 src/Mod/BIM/bimcommands/BimNudge.py#L125-L311.
- A10 Critiche:
  - issue https://github.com/FreeCAD/FreeCAD/issues/16155 , /issues/24894 , /issues/19255 , /issues/17684 , /issues/17185 ;
  - https://www.ondsel.com/blog/freecad-breaking-open-source-ux-curse/ (15/11/2023);
  - https://librearts.org/2024/11/freecad-1-0/ ;
  - https://blog.freecad.org/2026/03/25/freecad-version-1-1-released/ ;
  - note di rilascio: http://web.archive.org/web/20261005163231/https://wiki.freecad.org/Release_notes_1.1 e http://web.archive.org/web/20261020200101/https://wiki.freecad.org/Release_notes_26.3
- A11 114 src/Mod/Measure/Gui/QuickMeasure.cpp#L58-L338; 114 src/Mod/BIM/BimStatus.py#L45-L213; 114 src/Gui/InputHint.h

**BIM, IFC, FCStd (B)**
- B1 Sito:
  - 114 src/Mod/BIM/ArchSite.py#L109-L302 (diagramma), #L539-L776 (proprietà), #L1046-L1230 (vista), #L1806-L2078 (sole);
  - 263 src/Mod/BIM/ArchSite.py#L1028-L1323 e #L1656-L1660;
  - main src/Mod/BIM/ArchSite.py#L184-L210;
  - PR https://github.com/FreeCAD/FreeCAD/pull/22516 ; issue /issues/28471 , /issues/26194 , /issues/29834
- B2 Importazione ed esportazione IFC:
  - 114 src/Mod/BIM/importers/exportIFC.py#L426-L435 e #L2564-L2599;
  - 114 src/Mod/BIM/importers/importIFC.py#L239-L246 e #L993-L1024;
  - 114 src/Mod/BIM/importers/importIFCHelper.py#L55-L77;
  - 114 src/Mod/BIM/nativeifc/ifc_tools.py#L590-L705;
  - 114 src/Mod/BIM/nativeifc/ifc_import.py#L45-L185;
  - 114 src/Mod/BIM/nativeifc/ifc_psets.py#L92-L170;
  - 263 src/Mod/BIM/nativeifc/ifc_tools.py#L688-L714;
  - 114 src/Mod/BIM/Init.py#L27-L29;
  - issue https://github.com/FreeCAD/FreeCAD/issues/16064 (un caso simile con un'altra costante di ifcopenshell, chiuso nel 2024);
  - https://github.com/IfcOpenShell/IfcOpenShell/blob/158fe92644cfe2bc37be513d9838c95d9f2233cf/src/ifcopenshell-python/ifcopenshell/api/georeference/edit_true_north.py#L25-L72
- B3 Ombre: 114 src/Mod/BIM/OfflineRenderingUtils.py#L333-L406; https://github.com/FreeCAD/FreeCAD-render/blob/08be2fe94b8a998323c8a5443f7f0afd0d05bed5/Render/lights.py#L263-L330
- B4 Workbench FV:
  - https://github.com/JavierBrana/PVPlant/blob/7852ee562c92706e5e3e5d095cefccd5070b18d3/InitGui.py#L1-L107 ;
  - https://github.com/Francisco-Rosa/Solar/blob/44abb90ab6310813780f5cb040a8cadde5da941c/package.xml ;
  - https://github.com/darkmatter11235/freepv/tree/60825daa9dff68e0a565481c346fc613c067c46c ;
  - https://github.com/FreeCAD/Addons/blob/4845e9c7e6318d211edd749b86934036dd60d393/Data/Index.json ;
  - https://github.com/flathub/org.freecad.FreeCAD/blob/f043288fa86f6e780aaefdbc5a0aa6cdef5f3fb4/python3-modules.yaml#L196-L205
- B5 FCStd:
  - 114 src/App/Document.cpp#L1259-L1349;
  - 114 src/App/PropertyContainer.cpp#L310-L385;
  - 114 src/App/PropertyPythonObject.cpp#L88-L271;
  - 114 src/Base/Reader.cpp#L445-L495;
  - 114 src/Mod/Part/App/PropertyTopoShape.cpp#L364-L532;
  - avvisi di sicurezza https://github.com/FreeCAD/FreeCAD/security/advisories/GHSA-9624-pf2m-8cgg e GHSA-9vjf-h8f4-c229 ;
  - https://github.com/cadmpeg/cadmpeg/blob/98b58f439b2a60ad08c9495fec52347922d550e3/docs/formats/freecad_fcstd.md
- B6 API per un addon:
  - 114 src/Mod/BIM/Arch.py#L212, #L368-L404, #L1091-L1178, #L1247-L1284;
  - 114 src/Mod/BIM/ArchIFC.py#L254-L334;
  - 114 src/App/FreeCADInit.py#L291-L315;
  - 114 src/Gui/Application.cpp#L813-L870;
  - wiki (copia del 15/01/2025) https://github.com/FreeCAD/FreeCAD-documentation/blob/0499378a238ce4c77c643b9cc4a03d0947381e45/wiki/Workbench_creation.md
- B7 Licenze:
  - https://pypi.org/project/ifcopenshell/0.9.0.post1/ ;
  - https://github.com/pingswept/pysolar/blob/5ab944f5b3992306c2c90c18d28aff58d6ded9aa/COPYING ;
  - https://pypi.org/project/ladybug-core/0.44.62/

**Campione IFC di terzi**: https://github.com/buildingSMART/Sample-Test-Files/blob/main/IFC%204.0.2.1%20(IFC%204%20ADD2%20TC1)/Simple-Scene/Building-Architecture.ifc

**Meridiana** (solo lettura):
- `C:\Users\utente\dev\meridiana-lavoro\src\meridiana\model.py`
- `C:\Users\utente\dev\meridiana-lavoro\src\meridiana\geo.py`
- `C:\Users\utente\dev\meridiana-lavoro\src\meridiana\layout.py`
- `C:\Users\utente\dev\meridiana-lavoro\src\meridiana\mesh.py`
- studi 01, 05a, 07, 12, 12a in `C:\Users\utente\dev\meridiana-lavoro\docs\studio`
