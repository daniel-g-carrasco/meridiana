# Studio 17: l'interfaccia, i bozzetti

23/10/2026. Daniel ha usato la versione con la fase 2 e ha chiesto un'interfaccia più chiara e più bella: le parti distinte (R18, R30), gli strumenti al posto giusto (R19), pulsanti e campi che si vedono (R22), grafici vivi (R23), aiuti accanto alle cose (R24), un pannello Verifiche che si capisce (R13), Meridio animato e la sua chat (R15). Questo studio dà per ogni tema almeno tre direzioni disegnate sul layout vero della finestra, con i pro, i contro, la fatica, i voti e una raccomandazione; dove la scelta dipende da un fatto c'è una prova in Qt. Le scelte sono di Daniel, guardando i bozzetti; i compiti per le sessioni cloud sono in bozza in `docs/compiti/17*.md` (sezione «Il piano»).

**Legenda**
- [V] letto nel codice di Meridiana, nella documentazione ufficiale del programma citato (con l'URL e la data in fondo) o verificato con una prova in `17-prove/`;
- [V, prova] provato in questa sessione, offscreen, su Linux; i risultati sono accanto agli script;
- [I] dedotto;
- [D] decisione proposta, da confermare.
- Voti da 1 a 5: efficacia (5 = risolve bene), rischio (5 = poco rischio), costo (5 = poca fatica). La fatica è in giorni di lavoro di una sessione, test compresi.

**Come è stato fatto.** Per ogni tema: le parole di Daniel; che cosa fa oggi Meridiana, letto nel codice (`ui/theme.py`, `ui/window.py`, `ui/properties.py`, `ui/charts.py`, `ui/energy_pages.py`, `ui/checks_page.py`, `ui/assistant.py`, `assistant.py`, `theme_colors.py`); come lo fanno GNOME con libadwaita, VS Code, Blender, Revit, DIALux evo, Fusion, Onshape, SketchUp, Windows 11 con Fluent 2 e WinUI, macOS, KDE, JetBrains, PVsyst, Aurora, OpenSolar, Solibri, Navisworks, Office e Qt stessa, dalla documentazione pubblica; le direzioni disegnate; una prova dove serve; la raccomandazione e ciò che resta a Daniel. Le norme non sono citate a memoria: le frasi delle verifiche nei bozzetti citano le fonti con i nomi che il programma usa già (`checks.py`), senza articoli nuovi. Le pagine non lette sono dette tema per tema in fondo.

**I bozzetti.** Sono in `docs/studio/17-prove/`, pagine HTML senza librerie e senza rete: si aprono con un doppio clic e `index.html` le elenca. Ogni pagina ha in alto il passaggio chiaro/scuro (resta memorizzato) e lo zoom; i colori sono variabili CSS ricavate come fa `theme_colors.derive()` con il bronzo e i fondi Meridiana (calce e notte), cioè la direzione scelta nello studio 13, sezione 7, con i valori della sezione 12; il carattere è Titillium Web dai file del programma (`data/fonts/`). Il generatore è `genera.py` (con `parti.py` per le parti comuni e `pagine_defg.py`): `python docs/studio/17-prove/genera.py` riscrive le otto pagine. Le finestre disegnate sono quelle di Meridiana: menu, schede, barra degli strumenti, Progetto e Proprietà, pianta e 3D affiancate, Verifiche, barra di stato, con la barra della vista dentro le viste come deciso nei ritocchi della fase 2 (passo 2) e la barra degli strumenti con le sole icone (passo 3).

**Le prove in Qt.** Due script offscreen con le schermate (`QWidget.grab()`), i numeri nei file `-risultati.txt`:
- `controlli_prova.py`: la finestra di Meridiana costruita con Fusion e un foglio di stile per tre coppie di direzioni (C1 con A1, C2 con A3, C3 con A2), in chiaro e in scuro; i contrasti misurati con `theme_colors.contrast`; il costo del foglio di stile (polish) e del disegno;
- `grafici_prova.py`: il grafico orario di un anno (8.760 punti) e quello mensile con matplotlib, pyqtgraph, Qt Charts, Qt Graphs 2D e una vista web; il primo disegno, il ridisegno, il passaggio del mouse, lo zoom, la memoria.

**Librerie.** Nessuna è stata aggiunta al programma. pyqtgraph è stato provato in un ambiente a parte ed è proposto, non deciso.

## In breve

Le raccomandazioni, due righe per tema; il resto nelle sezioni.

| Tema | Raccomandazione | Fatica |
|---|---|---|
| A. Le parti | A1, tre livelli di superficie: i tre fondi del tema ci sono già (finestra, pannelli, vista) ma stanno a 1,05:1 e l'occhio non li separa; si allargano a 1,15:1 circa e si aggiungono la linea di 1 px tra le parti e i titoli dei pannelli in maiuscoletto attenuato. L'albero T2: sezioni con intestazioni e conteggi, 8 px d'aria, i segni delle verifiche leggibili. Tutto in `theme_colors.py` e nel foglio di stile, costo misurato 16-37 ms. | 2-3 giorni |
| B. Gli strumenti | B1, la barra sotto le schede e dentro la scheda Modello, con le sole icone e l'etichetta «Disegna»: nelle altre schede sparisce. La barra laterale a icone (B2) resta l'alternativa se la finestra è bassa. Le fasi numerate (B4) no: Meridiana non è un flusso a tappe. | 1-2 giorni |
| C. Pulsanti, campi, gruppi | C2 tonale alla GNOME per i pulsanti (velo del testo, un solo pulsante pieno d'accento per pagina) e per i gruppi (schede piene con il titolo), con una correzione che la prova impone: in scuro la scheda oggi ha lo stesso colore del pannello (1,00:1), e i campi tonali stanno a 1,1:1; quindi un velo più forte in scuro, un bordo di 1 px a 3:1 ai campi (WCAG 1.4.11) e la riga d'accento a fuoco. Risultati R2, schede piene con il numero chiave in evidenza, con il bordo leggero in scuro. | 3-4 giorni |
| D. Grafici | pyqtgraph (MIT, +14 MB, 1-4 ms al passaggio e allo zoom contro 170-190 ms del ridisegno di matplotlib e 9 ms con il blitting), con il tema applicato e la legenda che accende e spegne; matplotlib resta per le immagini della relazione PDF (`ui/report.py` già le disegna da sé). Niente vista web: 111-126 MiB di ruota e un processo del browser per un grafico. | 5-7 giorni in due passi |
| E. Aiuti | E1 più una parte di E2: il «?» accanto ai titoli dei gruppi e ai campi che lo meritano apre un riquadro di tre righe con la fonte e i collegamenti al manuale e a «Come è calcolato»; una frase sotto il campo solo dove il valore non si spiega da solo; Maiusc+F1 e il «?» della finestra per la via da tastiera. I testi in un modulo Python con `_()`, uno per sezione, scritti qui per Sottocampo, Producibilità, Bilancio e Verifiche. | 3-4 giorni |
| F. Verifiche | F1 per oggetto come vista predefinita, con il passaggio a per livello (F2) e per area (F3) in un menu; la frase breve con il dettaglio a richiesta (che cosa, perché, che cosa fare) in un campo nuovo di `checks.Item`; «Correggi» sulla riga, l'occhio che mostra l'oggetto nelle viste; i conteggi nel titolo del pannello e nella barra di stato. | 3-4 giorni |
| G. Meridio | G1 sopra la base G3: respiro lento (4 s), sguardo di un pixel, «pensa» con gli occhi in su e i tre puntini; la chat si apre dall'angolo del personaggio in 220 ms e si ridimensiona dall'angolo; le domande pronte come elenco con la freccia; con «meno movimento» resta G3. In Qt con una QPixmap in cache e un timer a 20 fotogrammi al secondo, misurato sotto 0,3 ms a fotogramma. | 3-5 giorni |

Le domande per Daniel sono in fondo a ogni tema e raccolte nella sezione «Il piano».

## 0. L'indice dei bozzetti

Tutti in `docs/studio/17-prove/`. Ogni direzione ha il suo numero: nelle risposte basta dire «A1» o «T2».

| Pagina | Direzioni | Che cosa si prova sulla pagina |
|---|---|---|
| `A-parti.html` | A0 oggi; A1 tre livelli di superficie; A2 un livello e intestazioni piene; A3 pannelli come schede. L'albero: T1 oggi; T2 sezioni con intestazioni; T3 sezioni come schede | Il passaggio chiaro/scuro: i livelli devono reggere in tutti e due |
| `B-strumenti.html` | B1 barra sotto le schede, legata a Modello; B2 barra laterale a icone; B3 barra dentro la vista; B4 fasi alla DIALux con i gruppi | Le icone sole con i nomi nei suggerimenti (passa sopra) |
| `C-controlli.html` | C1 Fusion ritoccato; C2 alla GNOME, tonale; C3 contorni forti. I risultati: R1 schede con bordo; R2 schede piene con il numero chiave; R3 righe con il numero d'accento | Passaggio e fuoco sui pulsanti e sui campi; chiaro e scuro |
| `D-grafici.html` | D1 matplotlib con gli eventi; D2 pyqtgraph; D3 vista web | Il mensile e l'orario di un anno sintetico: passaci sopra, trascina per lo zoom (D2, D3), clicca la legenda; il tempo di disegno è scritto sotto |
| `E-aiuti.html` | E1 il «?» accanto ai titoli e ai campi; E2 frasi sotto i campi e suggerimenti estesi; E3 un pannello d'aiuto che segue il fuoco. In fondo i testi d'esempio per quattro sezioni | Clicca il «?» (E1); i testi scritti per davvero |
| `F-verifiche.html` | F1 per oggetto; F2 per livello, in schede; F3 per area, in tabella | La prima voce aperta con il dettaglio, «Correggi» e l'occhio |
| `G-meridio.html` | G1 respiro e sguardo, apertura dall'angolo, puntini, domande come elenco; G2 raggi che girano, scivola dal basso, testo che scorre, pastiglie; G3 fermo, senza animazione, numerate | Clicca Meridio per aprire e chiudere, muovi il mouse (G1), trascina l'angolo della chat; con «meno movimento» del sistema tutto è fermo |

Le schermate delle prove in Qt stanno accanto: `controlli_prova_*.png` (sei finestre) e `grafici_prova_*.png` (cinque grafici).

## A. Distinguere le parti dell'interfaccia

### A.1 Cosa chiede Daniel

R18: «sarebbe da migliorare la distinzione tra le varie sezioni dell'interfaccia. Non c'è grande distinzione tra menu e sottomenu (strumenti, proprietà, barre laterali, verifiche)».

R30: l'albero a sinistra è «senza spaziatura tra le sezioni, il tutto poco chiaro»; il segno accanto a «Sito: …» è «piccolissimo e disegnato male», e al passaggio non succede nulla (il segno e il suggerimento sono già nei ritocchi, passo 10; qui la presentazione).

### A.2 Che cosa fa oggi Meridiana [V]

- `theme_colors.derive()` dà già **tre fondi**: finestra, pannelli, vista (chiaro #f2f1ed, #f8f7f4, #ffffff; scuro #14181e, #1a1f26, #101318), più `header` per i titoli dei dock, `line` e `line_soft`. Ma finestra e pannelli stanno a **1,05:1 in chiaro e 1,08:1 in scuro** [V, prova: `controlli_prova-risultati.txt`]: sotto 1,1:1 l'occhio non li separa su uno schermo normale, e la finestra sembra di un colore solo. È la causa di R18.
- `ui/theme.py`, `style_sheet()`: la barra degli strumenti senza bordo; la barra di stato con una riga sopra; il titolo dei dock con il fondo `header`, 4 px di padding e una riga `line_soft` sotto; il riquadro delle schede con una riga sopra; le schede con la riga d'accento di 2 px sotto quella attiva. Non c'è una regola per i separatori tra i dock e il centro (`QMainWindow::separator`), né per le intestazioni dentro i pannelli.
- `ui/window.py`: un `QMainWindow` con tre `QDockWidget` (Progetto a sinistra, Proprietà a destra, Verifiche in basso), il `QTabWidget` centrale con le quattro schede, la barra «Strumenti» con testo accanto all'icona (diventa a sole icone con i ritocchi, passo 3), la barra di stato con il suggerimento, l'indicatore di lavoro, la misura, le coordinate e il pulsante di Meridio.
- L'albero: un `QTreeWidget` senza intestazione; la radice «Sito: nome», poi tre righe di gruppo «Edifici (n)», «Sottocampi (n)», «Esclusioni (n)» con l'icona del sito, e sotto gli oggetti con l'icona del tipo e il nome; i segni delle verifiche nella seconda colonna, il segno «da correggere» come icona. Le righe di gruppo hanno la stessa altezza e lo stesso carattere delle altre: da qui il «senza spaziatura» di R30.

### A.3 Come fanno i programmi di riferimento [V]

| Programma | Livelli di superficie | Intestazioni e separatori |
|---|---|---|
| GNOME, libadwaita 1.10 | Quattro grigi in chiaro: sidebar #ebebed, sidebar secondaria #f3f3f5, finestra #fafafb, vista e header bar #ffffff; in scuro l'ordine si rovescia (vista #1d1d20 la più scura, finestra #222226, sidebar #2e2e32). Le «card» stanno sul fondo della finestra. | Le barre sono piatte («flat») e il contenuto che scorre sotto mostra un'ombra; gli stili «raised» danno fondo opaco e ombra o bordo; i separatori sono colori d'ombra («shade»), non cornici; i titoli con le classi `.title-1`…`.title-4` e `.heading`, il «caption-heading» per i piccoli |
| VS Code | Ogni parte ha il suo fondo: `editor.background`, `sideBar.background`, `activityBar.background`, `panel.background`, `editorGroupHeader.tabsBackground`, `titleBar.activeBackground` | Un colore di bordo per ogni confine (`sideBar.border`, `panel.border`, `activityBar.border`, `statusBar.border`); le intestazioni di sezione del pannello laterale hanno fondo, bordo e testo propri (`sideBarSectionHeader.*`); i bordi forti solo nei temi ad alto contrasto (`contrastBorder`) |
| Blender 5.2 | La finestra divisa in aree con gli angoli arrotondati e un bordo di larghezza regolabile («Border Width»); dentro ogni editor le regioni (header, toolbar, sidebar) con il loro fondo, anche sovrapposte alla vista («Region Overlap») | Ogni editor ha un header, una striscia con menu e strumenti, che si può nascondere o spostare in basso; i pannelli dentro la sidebar hanno il titolo sempre visibile con la freccia e la maniglia |
| Revit 2023 | Un fondo solo per l'applicazione; la ribbon, la barra delle opzioni, le palette Proprietà e Browser di progetto e l'area di disegno si distinguono per posizione e cornice | Le palette hanno il titolo nella barra del dock; la ribbon ha le schede e i pannelli con l'etichetta sotto |
| Windows 11, Fluent 2 | «Windows 11 uses a two-layer system»: la base (Mica) con menu, comandi e navigazione, e il livello del contenuto, intero o a schede («cards»); con Mica Alt un terzo livello per la barra dei comandi | Tratti di 1 px («strokes») al posto delle ombre per i livelli bassi: card elevazione 8, controllo 2, livello 1; le ombre solo per ciò che galleggia; «lighter neutrals» sulle superfici che contano |
| macOS | Il materiale della sidebar (traslucido) contro il fondo della finestra e del contenuto; l'inspector come colonna di coda | Divisori sottili di 1 pt; la barra degli strumenti senza sfondo, distinta dal contenuto con l'effetto di bordo allo scorrimento |
| KDE | Un fondo, le parti distinte dalla posizione: «Group related items together by reducing the spacing between them, and increasing the spacing between groups» | «Avoid unnecessary frames, spacing, and padding around content views»; le liste con le righe alternate |
| Qt 6.12 | Fusion disegna i dock, le barre e i pannelli con la stessa `QPalette.Window`; il foglio di stile ha i sottocontrolli giusti: `QDockWidget::title`, `QMainWindow::separator`, `QToolBar::separator`, `QSplitter::handle`, `QTabWidget::pane`, `QHeaderView::section`, `QTreeView::branch` | La documentazione avverte: i fogli di stile sono «a tool for prototyping and for small, local adjustments»; per un tema intero conviene `QProxyStyle` con i ruoli della palette; ogni `setStyleSheet` sull'applicazione ripassa tutti i widget |

Il modello che ricorre: **due livelli, a volte tre**, distinti da fondi vicini ma separabili, un tratto di 1 px tra le parti, le intestazioni come superficie a sé; le cornici e le ombre solo per ciò che galleggia.

### A.4 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| A0 | Oggi | Nulla da fare | È ciò che Daniel lamenta | 0 | 1 | 5 | 5 |
| A1 | **Tre livelli di superficie**: finestra (menu, schede, strumenti, stato) sul fondo più scuro, pannelli sul fondo medio, viste e campi sul fondo più chiaro; un filo di `line` tra le parti; titoli dei pannelli in maiuscoletto attenuato | È il modello di libadwaita, VS Code, Fluent; i tre fondi ci sono già nel tema; cambia solo `derive()` (le L dei fondi) e il foglio di stile; in scuro i tre fondi del tema sono già distinti (#14181e, #1a1f26, #101318) | In chiaro la finestra diventa un po' più grigia (L da 0,957 a circa 0,94); il contrasto del testo attenuato sulla finestra scende (oggi 5,1:1) e va rimisurato; i fondi «Dal colore» e «Grigi» seguono | 1-2 giorni | 5 | 4 | 4 |
| A2 | **Un livello e intestazioni piene**: un fondo solo, separatori di 1 px, una striscia appena più scura con il titolo per ogni pannello e per le Verifiche | Il modello di Revit e dell'header di Blender; meno «disegno»; le intestazioni fanno il lavoro e portano i conteggi | I pannelli restano del colore della finestra: il problema di R18 si attenua ma resta tra pannelli e viste; le intestazioni piene si sommano a quelle dei gruppi (C3) | 1 giorno | 3 | 5 | 5 |
| A3 | **Pannelli come schede**: pannelli e viste come schede arrotondate che galleggiano sulla finestra con 8 px di spazio e un'ombra leggera; i titoli dentro la scheda | Il «layering» di Fluent 2 e le card di libadwaita; il più bello da fermo | Costa spazio (8 px per lato, 16-24 px in larghezza); in Qt richiede un contenitore con margini per ogni dock e l'ombra con `QGraphicsDropShadowEffect` (lenta) o disegnata; i dock trascinati perdono la scheda; nella prova la scheda in chiaro sta a 1,07:1 dal pannello: senza bordo non si vede | 3-4 giorni | 4 | 2 | 2 |

L'albero (R30):

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| T1 | Oggi: righe uguali, i gruppi con l'icona del sito | | Le sezioni non si vedono; il segno piccolo | 0 | 1 | 5 | 5 |
| T2 | **Sezioni con intestazioni**: «EDIFICI · 2», «SOTTOCAMPI · 2», «ESCLUSIONI · 2» in maiuscoletto attenuato con il conteggio, 8 px d'aria sopra ognuna, la freccina per aprire e chiudere, i conteggi dei moduli attenuati accanto al nome, i segni delle verifiche come pillole leggibili (✘ 1, ⚠ 2) | È l'Explorer di VS Code e le sezioni di AdwSidebar; in Qt è un delegato o un `QTreeWidgetItem` con carattere, altezza e colore propri e `setFirstColumnSpanned`; lo spazio sopra viene da `sizeHint` della riga; i conteggi dei segni sono già calcolati da `_mark_tree()` | Le intestazioni non si selezionano: la selezione del «sito» resta sulla radice; da scrivere il delegato per le pillole | 1 giorno | 5 | 4 | 4 |
| T3 | **Sezioni come schede**: ogni sezione in una scheda sul fondo del pannello (boxed list) | Più chiara da lontano; coerente con C2 | Più alta: con molti oggetti si scorre prima; in `QTreeWidget` una scheda per sezione vuol dire disegnare il fondo nel delegato o un widget per sezione (si perde l'albero unico e il trascinamento) | 2-3 giorni | 3 | 3 | 2 |

### A.5 La prova in Qt [V, prova: `controlli_prova.py`]

La finestra di Meridiana (menu, barra, tre dock, albero, modulo delle Proprietà con due gruppi, le Verifiche, la barra di stato: 101-108 widget) costruita con Fusion e un foglio di stile per A1, A2 e A3, in chiaro e in scuro, schermate `controlli_prova_C1_A1_*.png`, `C3_A2_*.png`, `C2_A3_*.png`.

| Misura | Chiaro | Scuro |
|---|---|---|
| finestra contro pannello (A1, i fondi di oggi) | 1,05:1 | 1,08:1 |
| linea `line` sul pannello | 1,37:1 | 1,28:1 |
| scheda A3 (`card`) sul pannello | 1,07:1 | 1,00:1 |
| bordo leggero `line_soft` sul pannello | 1,17:1 | 1,09:1 |
| testo attenuato sul pannello | 5,14:1 | 4,84:1 |
| foglio di stile applicato (polish), 21-23 regole | 16-28 ms | 23-37 ms |
| disegno della finestra | 8-11 ms | 7-14 ms |

- I tre livelli di A1 si fanno con il foglio di stile e la palette: 21 regole, 16-37 ms una volta sola all'avvio, nessun costo al disegno. Il `QMainWindow::separator` e il `QDockWidget::title` prendono i colori del tema [V].
- In chiaro i fondi di oggi stanno a 1,05:1: A1 chiede di **allargare** la distanza tra finestra e pannelli a 1,12-1,18:1 (in OKLCH: finestra L 0,94, pannelli 0,975, vista 1,0) e di tenere `line` a 1,35:1 o più; in scuro i valori di oggi bastano [I, dalla prova].
- A3 in chiaro non regge senza bordo: la scheda sta a 1,07:1 dal pannello; in scuro `card` è uguale al pannello (1,00:1) perché `derive()` non alza la scheda sopra il pannello nel tema scuro, mentre libadwaita la schiarisce con un velo bianco all'8 %. Qualunque direzione con le schede (A3, C2, R1, R2, T3) ha bisogno di **un token `card` più chiaro del pannello in scuro** [V, prova].

### A.6 Raccomandazione

- **A1** [D]: tre livelli, con `derive()` che allarga i fondi in chiaro e il foglio di stile che aggiunge la riga tra le parti (`QMainWindow::separator`, `QDockWidget` con il bordo `line`), i titoli dei dock in maiuscoletto attenuato di 11 px con 6 px di padding, e la barra degli strumenti sul fondo della finestra. Il testo attenuato va rimisurato sui fondi nuovi e tenuto sopra 4,5:1 (oggi 5,1:1 e 4,8:1, studio 13).
- Le **intestazioni piene** di A2 per le Verifiche e per i gruppi delle Proprietà (vedi C) stanno bene anche dentro A1: titolo con il fondo `header` e i conteggi.
- **T2** per l'albero [D]: le tre sezioni come intestazioni con il conteggio, l'aria sopra, i segni come pillole. È lo stesso delegato che poi serve alle Verifiche (F).
- A3 resta la direzione «bella»: si può riprendere per le sole viste (pianta e 3D con gli angoli arrotondati di 4 px dentro il loro contenitore), senza le ombre.

**Domande per Daniel.** A1 o A2 (o A1 con le intestazioni piene)? Per l'albero T2 o T3? I titoli dei pannelli in maiuscoletto o nel carattere normale?

## B. Dove stanno gli strumenti

### B.1 Cosa chiede Daniel

R19, seconda parte: «mi chiedo se inoltre non debbano stare loro sotto il menù con scritto "modello, producibilità, consumi, ecc." essendo che loro sono controlli della modellazione». La prima parte (le sole icone, forse su un fianco) è nei ritocchi, passo 3.

### B.2 Che cosa fa oggi Meridiana [V]

- `ui/window.py`: una sola barra «Strumenti» aggiunta al `QMainWindow` con `addToolBar`, quindi **sopra** le schede del `QTabWidget` centrale; testo accanto all'icona, icone di 18 px. Contiene, con i separatori: gli strumenti di disegno (Seleziona, Edificio, Falda, Sottocampo, Esclusione, Misura), i comandi delle viste (Pianta, 3D, Affiancate, Inquadra, le aiutanti), e in coda l'etichetta «Variante» con il suo menu a tendina.
- La barra resta uguale in tutte le schede: `_tab_changed` cambia solo la scheda di Meridio. In Producibilità, Consumi ed Economia gli strumenti di disegno non servono a nulla ma stanno lì: è la sensazione «non appartengono» di R19.
- Già deciso (ritocchi, passo 2): i comandi delle viste vanno dentro le viste, in una barra piccola in basso (Pianta, 3D, Affiancate, Inquadra, F3, F8); passo 3: la barra mostra le sole icone, i nomi nei suggerimenti.

### B.3 Come fanno i programmi di riferimento [V]

| Programma | Dove stanno gli strumenti | Nota |
|---|---|---|
| Revit 2023 | La ribbon con le schede sotto la barra del titolo; le schede contestuali compaiono con lo strumento o la selezione e si chiudono all'uscita; sotto la ribbon la barra delle opzioni dello strumento corrente; in fondo a ogni vista la View Control Bar | Gli strumenti sono legati alla scheda, la vista ha la sua barra |
| Blender 5.2 | La Toolbar verticale a sinistra dell'editor (T), con i gruppi che si aprono tenendo premuto; allargandola si hanno due colonne, poi le icone con il testo; le impostazioni dello strumento in una striscia sotto l'header; le proprietà nella sidebar N a destra | Barra laterale a icone dentro l'area, non fuori |
| DIALux evo | «Evo understands a mode as the individual work steps within a workspace»; «You will find the modes above the CAD window»; «You will always find the tools on the left side of the screen»; le azioni a destra dello strumento, «Settings, names and values are below the tools» | Fasi sopra, strumenti a sinistra in colonna |
| Fusion | «The Toolbar is divided into tabs that organize the tools into logical groupings», con le schede contestuali e gli ambienti; la Navigation Bar con zoom, pan e orbita in fondo alla tela | Come Revit, con la barra di vista in basso |
| Onshape | La barra delle feature in alto; «Access the Feature shortcut toolbar with the S key while in the graphics area» | La barra rapida compare al cursore |
| SketchUp | Le barre si agganciano in alto o in basso; «Large Tool Set» solo a sinistra | La colonna di icone grandi a sinistra è la tradizione CAD |
| VS Code, JetBrains | L'activity bar e le barre delle tool window sul bordo esterno, a icone, che aprono i pannelli; spostabili in alto, in basso o nascoste | Icone per aprire pannelli, non strumenti di disegno |
| GNOME | I comandi nella header bar, pulsanti piatti raggruppati da spazi (`.spacer`); i pannelli di utilità a sinistra se agiscono sulla vista, a destra se le sono subordinati; F9 per mostrarli e nasconderli | «Header bar controls which affect the sidebar list should be placed above the list» |
| Windows 11, WinUI | La NavigationView a sinistra, compatta a sole icone sotto 1007 px; la barra dei comandi «near the top of the window makes them more noticeable and discoverable», icone 20 px con l'etichetta a destra | La barra in alto per la scopribilità |
| macOS | La barra degli strumenti nella cornice in alto, senza sfondo; «Make every toolbar item available as a command in the menu bar» | Ogni strumento anche nel menu: Meridiana lo fa già (`shortcuts.commands()`) |

Due famiglie: i CAD e i BIM mettono gli strumenti **sopra, legati alla scheda o alla fase** (Revit, Fusion, DIALux) o **in colonna a sinistra** (Blender, SketchUp, DIALux); gli editor di testo usano la colonna a icone per aprire pannelli, non per disegnare. Tutti tengono i comandi di vista dentro o sotto la vista.

### B.4 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| B1 | **Barra sotto le schede, legata a Modello**: la barra sta nella pagina Modello, sotto la riga delle schede, con l'etichetta «Disegna» davanti alle icone; nelle altre schede sparisce (Producibilità ha Calcola e PVGIS nella pagina) | È ciò che Daniel propone; il modello di Revit e Fusion; ogni scheda porta i suoi comandi; in Qt una `QToolBar` è un widget qualsiasi e sta in un layout; libera la riga in alto | La barra non si sgancia né si sposta più (è nel layout); «Variante» non è della scheda Modello e va altrove (l'angolo destro della riga delle schede, `QTabWidget.setCornerWidget`); la scheda Impianto dello studio 16 avrà la sua barra (stringhe) | 1-2 giorni | 5 | 4 | 4 |
| B2 | **Barra laterale a icone**: una colonna di 44 px sul fianco sinistro, prima del pannello Progetto, icone di 20 px, lo strumento attivo con la riga d'accento; una `QToolBar` verticale in `LeftToolBarArea` | La toolbar «T» di Blender e il Large Tool Set di SketchUp; libera una riga in alto, utile sui portatili (768 px); è l'altra idea di Daniel in R19 | Sulle altre schede la colonna resta (vuota o con altro); le icone sole in colonna si leggono meno delle stesse in riga con l'etichetta «Disegna»; in Qt l'area delle barre sta fuori dall'area dei dock, quindi la colonna è a sinistra di Progetto, lontana dalla pianta | 1 giorno | 4 | 4 | 5 |
| B3 | **Barra dentro la vista**: gli strumenti galleggiano in alto al centro della pianta, i comandi di vista restano in basso | Vicina a dove si lavora (Aurora, OpenSolar, le app di disegno); nel 3D non c'è, giusto perché lì non si disegna | Copre una striscia di pianta; con le viste affiancate la pianta è stretta; due barre galleggianti nella stessa vista (strumenti e vista) fanno confusione; in Qt è un widget figlio della vista con il suo foglio di stile | 1-2 giorni | 3 | 3 | 4 |
| B4 | **Fasi alla DIALux, con i gruppi**: schede numerate (1 Modello, 2 Impianto, 3 Producibilità, 4 Consumi, 5 Bilancio ed economia, 6 Relazione) e una barra alla ribbon con i gruppi etichettati (Disegna, Modifica, Sole, Sfondo) | Chiarissima per chi comincia; i gruppi spiegano le icone | 76 px di altezza, testo sotto le icone (che Daniel non vuole); Meridiana non è un flusso a tappe: si torna al modello dopo aver visto i consumi; sei schede con i numeri occupano la riga | 2-3 giorni | 3 | 3 | 3 |

### B.5 Che cosa cambia in Qt [I, dal codice]

- B1: la pagina Modello prende un `QVBoxLayout` con la `QToolBar` in cima e sotto lo `QSplitter` di oggi; le `QAction` restano le stesse (menu, scorciatoie, suggerimenti nella barra di stato); il `QToolBar` nel layout non ha la maniglia e non galleggia (`setMovable(False)`, `setFloatable(False)`); il foglio di stile le dà il fondo della finestra (A1) e una riga sotto. «Variante» va nell'angolo della riga delle schede. Una preferenza «Strumenti: in alto / a sinistra» cambia l'orientamento della stessa barra dentro la pagina (`QBoxLayout` orizzontale): così B2 resta un'opzione senza una seconda barra.
- B2: `addToolBar(Qt.LeftToolBarArea, tools)`, `ToolButtonIconOnly`, icone 20 px: mezza giornata; ma la colonna sta a sinistra del dock Progetto.
- B3: come la barra della vista dei ritocchi (passo 2), un secondo widget sovrapposto: va coordinato con quella.
- B4: le schede sono già un `QTabWidget`; i gruppi con l'etichetta sotto sono widget a mano nella barra: la parte costosa è il testo sotto le icone.

### B.6 Raccomandazione

- **B1** [D]: la barra degli strumenti sotto le schede, dentro la scheda Modello, a sole icone con l'etichetta «Disegna» davanti; «Variante» nell'angolo destro delle schede; la preferenza «a sinistra» che gira la stessa barra in colonna (B2) per chi lavora su un portatile.
- B3 no: una sola barra galleggiante per vista, quella dei comandi di vista già decisa.
- B4 no come struttura; sì all'idea dei **gruppi**: nella barra B1 i separatori dividono Disegna (Edificio, Falda, Sottocampo, Esclusione), Modifica (Seleziona, Sposta e Ruota dello studio 16, Misura) e Sole; l'etichetta «Disegna» basta, le altre stanno nei suggerimenti.

**Domande per Daniel.** B1 in alto o B2 a sinistra come predefinita? «Variante» nell'angolo delle schede o nella barra di stato? La scheda Impianto (studio 16) avrà la sua barra con gli strumenti delle stringhe: stessa posizione?

## C. Pulsanti, campi e gruppi

### C.1 Cosa chiede Daniel

R22: «il design di tasti e bottoni non è il massimo. Vorrei proposte per cambiarlo. Le caselle di input non si distinguono bene dallo sfondo (almeno in modalità scura) e sarebbe buono dare alle varie sottosezioni un contorno più evidente (mi riferisco tipo a "distanze e margini, ecc..."). Anche i contorni all'interno dei risultati di "consumi", "bilancio ed economia", "producibilità", non si leggono. In tutti i casi citati sopra, non è possibile usare un approccio alla gnome nel quale sottosezioni e tasti non solo hanno contorno ma riempimento come il contorno?».

### C.2 Che cosa fa oggi Meridiana [V]

- Lo stile è Fusion con la palette del tema (`ui/theme.py`, `qpalette()`) e il foglio di stile della sezione A.2, che non tocca pulsanti, campi e gruppi: i **pulsanti** sono quelli di Fusion (sfumatura dal colore `Button`, bordo dai ruoli `Mid` e `Dark`); i **campi** hanno il fondo `Base` (il colore della vista) e il bordo di Fusion; i **gruppi** sono `QGroupBox` con il titolo sulla riga della cornice: «Sottocampo», «Distanze e margini», «Lati», «Vigili del fuoco», «Connessione e obblighi», «Passo dal sole» (`ui/properties.py`).
- I **riquadri dei risultati** (`Tiles` in `ui/energy_pages.py`: Producibilità, Consumi, Bilancio) sono `QFrame` con `StyledPanel`, l'etichetta e il numero, senza regola nel foglio di stile: il contorno è quello che Fusion disegna con i ruoli `Mid` e `Dark` della palette, e sui fondi di oggi sta sotto 1,4:1.
- I contrasti di oggi [V, prova]: il campo (fondo vista) sul pannello sta a **1,07:1 in chiaro e 1,12:1 in scuro**, il suo bordo `line` a 1,37:1 e 1,28:1. Sono i numeri di «le caselle non si distinguono dallo sfondo»: sotto 1,2:1 il fondo non si vede, e un bordo a 1,3:1 si perde; la soglia di WCAG 1.4.11 per un bordo che identifica il controllo è 3:1.

### C.3 Come fanno i programmi di riferimento [V]

| Sistema | Pulsanti | Campi | Gruppi e schede |
|---|---|---|---|
| GNOME, libadwaita | Il pulsante normale è un velo del colore del testo al 10 % (`color-mix(in srgb, currentColor 10%, transparent)`), 15 % al passaggio, 30 % premuto, **senza bordo** (solo in alto contrasto); `.flat` nelle barre («looking like a label or an icon until hovered»); `.suggested-action` pieno d'accento, e «Each view should only ever include a single button using either the suggested or destructive styles»; `.pill` «when a text button is situated in open space»; raggio 9 px | Lo stesso velo al 10 % dei pulsanti, non il fondo della vista; a fuoco un anello d'accento di 2 px al 50 %; nelle finestre delle preferenze le righe «entry row» dentro le liste; «Right-justify the content of spin boxes» | `AdwPreferencesGroup`: titolo, descrizione, una «boxed list» con le righe; `.card` raggio 12 px e ombra appena percettibile (`0 0 0 1px rgb(0 0 6 / 3%), 0 1px 3px 1px rgb(0 0 6 / 7%)`); in scuro la card è un velo bianco all'8 % sopra la finestra |
| Material 3 | Cinque tipi: «elevated, filled, filled tonal, outlined, and text»; il tonale «lighter background color and darker label color», «middle ground between filled and outlined»; a contorno «medium-emphasis»; testo «lowest priority» | Pieni («more visual emphasis») o a contorno («reduced emphasis helps simplify the layout») | Card elevate, piene o a contorno: «the type you use depends on style alone» |
| Windows 11, WinUI | Primary pieno d'accento, Secondary con il velo, Outline, Subtle, Transparent; «Only use one primary button in a layout»; il velo è bianco al 70 % in chiaro e al 6 % in scuro, il tratto al 6-7 % | Fondo con lo stesso velo, **bordo inferiore più scuro** (`ControlStrongStroke`) e a fuoco 2 px d'accento in basso | `SettingsCard`: fondo della card e tratto di 1 px, 16 px di padding; «Card elevation 8 stroke 1» |
| macOS | «Keep the number of prominent buttons to one or two per view»; «Use style, not size»; i pulsanti con il bordo (`bordered`), il principale pieno (`borderedProminent`), i piatti nelle barre | Il campo con il bordo e il fondo chiaro; il suggerimento dentro | Il box ha il titolo sopra; «adding nested boxes to define subgroups can make your interface feel busy and constrained» |
| KDE | Pulsanti con il bordo (Breeze), «Avoid making buttons checkable» | Bordo | «Avoid unnecessary frames»; la Kirigami Card «a rectangle with a shadow»; i gruppi del FormLayout separati da spazio e titoli |
| NN/g | «Flat UI Elements Attract Less Attention and Cause Uncertainty» (2017): +22 % di tempo e +25 % di fissazioni sui controlli piatti; «Avoid ghost buttons»; «Make sure your buttons at least vaguely look like physical buttons» | | |
| WCAG 2.2, 1.4.11 | Un bordo o un fondo che serve a riconoscere il controllo sta a **3:1** dal colore accanto; «does not require that controls have a visual boundary»; l'esempio del campo con il bordo #767676; il fuoco a 3:1 (2.4.7, 2.4.11); AAA 2 px di perimetro (2.4.13) | | |
| Qt 6.12 | Nel foglio di stile «the background may not appear unless you set the border property» su `QPushButton`; il `QGroupBox::title` si sposta con `subcontrol-origin` e `subcontrol-position`; `flat` toglie i lati e il fondo | `QLineEdit`, `QSpinBox` con fondo, bordo e `:focus` | `QGroupBox` con bordo, raggio e titolo spostato; una scheda è un `QFrame` con `border` e `border-radius` |

Il filo comune: **un solo pulsante pieno per vista**, gli altri tonali o piatti; i campi distinti dal fondo o dal bordo, **mai da entrambi deboli**; i gruppi come superficie con titolo, non come cornice.

### C.4 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| C1 | **Fusion ritoccato**: pulsanti con fondo leggero e bordo del tema, campi con il fondo della vista e il bordo, gruppi con titolo e riga sotto | Il più vicino a oggi: solo il foglio di stile; i pulsanti «sembrano pulsanti» (NN/g) | In scuro il campo resta a 1,12:1 e il bordo a 1,28:1: il difetto di R22 non si risolve senza alzare il bordo; i gruppi senza riempimento | 1 giorno | 2 | 5 | 5 |
| C2 | **Alla GNOME, tonale**: pulsanti pieni senza bordo (velo del testo all'8-10 %), il principale pieno d'accento, campi dello stesso velo, gruppi come schede arrotondate con il fondo proprio e il titolo | È il «riempimento come il contorno» che chiede Daniel; una gerarchia chiara (pieno, tonale, piatto); i gruppi si vedono senza cornici | Nella prova il velo tonale sta a 1,13:1 in chiaro e 1,08:1 in scuro, e la scheda a 1,07:1 e 1,00:1: senza un bordo o un velo più forte, in scuro sparisce tutto; NN/g avverte sui controlli piatti; serve la regola «un solo pulsante pieno per pagina» | 2-3 giorni | 4 | 3 | 4 |
| C3 | **Contorni forti**: pulsanti a contorno di 1,5 px nel colore del testo secondario, campi con bordo di 1,5 px, gruppi con cornice e intestazione piena | Si legge sempre: il bordo `text2` sta a 7,95:1 e 8,51:1; WCAG soddisfatta con margine; l'intestazione piena del gruppo funziona in Qt (`::title` con `subcontrol-origin: margin`) | La più «disegnata»: i contorni si sommano a quelli dei pannelli e dei campi (il «busy» di Apple); i pulsanti a contorno sono i «ghost buttons» che NN/g sconsiglia | 1-2 giorni | 3 | 4 | 4 |

I riquadri dei risultati:

| | Che cosa | Pro | Contro | Eff. |
|---|---|---|---|---|
| R1 | **Schede con bordo**: ogni numero in una scheda con fondo e bordo leggero, l'unità piccola, la fonte, il collegamento a «Come è calcolato» | Legge bene in griglia; il bordo si vede anche in scuro se è `line` (1,28:1) o più | Sei cornici su una pagina | 4 |
| R2 | **Schede piene, il risultato chiave in evidenza**: schede piene senza bordo, la prima nel velo d'accento | Il numero che conta si trova a colpo d'occhio; coerente con C2 | In scuro la scheda piena sparisce senza il bordo (1,00:1 nella prova) | 4 (5 con il bordo in scuro) |
| R3 | **Righe con il numero d'accento**: niente riquadri, righe separate da una linea | La più leggera | Meno «contorno», che è ciò che Daniel lamenta; i numeri in colonna si confrontano, ma non si raggruppano | 2 |

### C.5 La prova in Qt [V, prova: `controlli_prova.py`, `controlli_prova-risultati.txt`]

Le tre direzioni costruite con Fusion e il foglio di stile, in chiaro e in scuro (`controlli_prova_C1_A1_*.png`, `C2_A3_*.png`, `C3_A2_*.png`):

| Misura | Chiaro | Scuro | Serve |
|---|---|---|---|
| C1: campo (fondo vista) sul pannello | 1,07:1 | 1,12:1 | 3:1 se il fondo è l'unico segno |
| C1: bordo `line` sul pannello | 1,37:1 | 1,28:1 | 3:1 |
| C2: velo tonale sul pannello | 1,13:1 | 1,08:1 | 3:1 |
| C2: scheda `card` sul pannello | 1,07:1 | 1,00:1 | visibile (libadwaita aggiunge un'ombra) |
| C3: bordo `text2` sul pannello | 7,95:1 | 8,51:1 | 3:1 |
| testo attenuato sul pannello (un bordo in `muted` avrebbe lo stesso contrasto) | 5,14:1 | 4,84:1 | 3:1 |
| testo sul pulsante d'accento | 6,70:1 | 13,18:1 | 4,5:1 |
| foglio di stile (21-23 regole) | 16-28 ms | 23-37 ms | una volta |

- Tutto si fa con Fusion più il foglio di stile: il «?» accanto al titolo, la frase sotto il campo, i gruppi come schede, il titolo pieno. Nessuna regola ha richiesto un `QProxyStyle`. Il costo è il polish all'avvio (16-37 ms) e nulla al disegno (7-14 ms la finestra intera).
- Il tema scuro di oggi non ha un colore per le schede: `card` è il pannello. Per C2, R1, R2, A3 e T3 serve un **token nuovo** in `derive()`: in scuro `card` più chiaro del pannello di un velo bianco al 6-8 % (libadwaita 8 %, WinUI 5 %), in chiaro il bianco della vista con un bordo `line`.
- Un bordo nel colore `muted` sta a 5,1:1 e 4,8:1: basta e avanza per WCAG, ma è un bordo scuro su ogni campo; un grigio a 3,0-3,5:1 (L 0,58 in chiaro, 0,50 in scuro) è il minimo che si legge e resta discreto [I].

### C.6 Raccomandazione

**C2 con i bordi dove servono** [D], cioè il riempimento che chiede Daniel più ciò che la prova e la norma impongono:
- **pulsanti**: tonali, velo del testo all'8 % (12 % al passaggio, 20 % premuti), senza bordo, raggio 4 px (studio 13); **un solo pulsante pieno d'accento per pagina** (Posa i moduli nel Modello, Calcola in Producibilità, Scarica da PVGIS no); piatti nelle barre; quello distruttivo (Svuota) tonale con il testo nel colore degli errori; a fuoco l'anello d'accento di 2 px (2.4.7);
- **campi**: lo stesso velo (in scuro un velo nero al 22 %, come nel bozzetto) **più un bordo di 1 px a 3:1 o più** in tutti e due i temi, e a fuoco il bordo d'accento di 2 px (il modello WinUI: fondo tonale e tratto forte); i numeri allineati a destra; il campo disabilitato senza bordo (esente da 1.4.11);
- **gruppi**: schede con il fondo `card` (nuovo in scuro), bordo di 1 px `line`, raggio 8 px, il titolo nel carattere dei titoli dei pannelli (A1) con 8 px sopra; niente cornici dentro le schede (Apple: «nested boxes»);
- **risultati**: R2, schede piene con il numero chiave nel velo d'accento, con il bordo `line` in scuro; l'unità piccola, la fonte e «come è calcolato» come oggi in «Come è calcolato»;
- tutto nel foglio di stile e nella palette; se le regole superano la cinquantina, un `QProxyStyle` per i pulsanti e i campi (la via che la documentazione Qt indica per un tema intero).

C3 resta la scelta se Daniel preferisce i contorni ai riempimenti: regge WCAG da sola, ma è la più pesante da guardare.

**Domande per Daniel.** C2 (tonale con i bordi dei campi) o C3 (contorni)? Un solo pulsante pieno per pagina: quali (Posa i moduli, Calcola)? I risultati R1 o R2? I campi con il bordo intero o solo in basso (WinUI)?

## D. Grafici interattivi

### D.1 Cosa chiede Daniel

R23: «i grafici non sono dinamici, non visualizzano nulla al passaggio del mouse, non è possibile controllarli. Negli sketch negli artefatti era possibile far più cose e il tutto era più carino. come mai qua non è così?».

### D.2 Perché, e che cosa fa oggi Meridiana [V]

- La risposta alla domanda: la tela degli artefatti era **HTML e SVG in un browser**, dove ogni barra è un elemento con i suoi eventi e lo stile, e il disegno costa poco. In Meridiana un grafico è **un'immagine** che matplotlib disegna con Agg dentro un widget (`ui/charts.py`, `Canvas(FigureCanvasQTAgg)`): gli eventi del mouse ci sono (`mpl_connect`), ma ogni risposta che cambia il disegno vuole un ridisegno intero, e il ridisegno di un anno di valori orari costa 150-190 ms [V, prova]. La grafica è quella «da stampa» di matplotlib, con il tema di Meridiana applicato ai colori (`set_theme`).
- Oggi `Chart` offre quattro disegni (barre anche impilate, variazioni in percentuale, mappa di calore, linee) e un messaggio; il pulsante «Tabella» mostra gli stessi numeri in una `QTableWidget`; al passaggio del mouse `_moved` cerca l'elemento sotto il puntatore e mostra il valore nel suggerimento del widget; niente zoom, niente scelta delle serie dalla legenda. `Canvas` rimanda il ridisegno finché la dimensione non si ferma (150 ms), perché un ridisegno con il layout vincolato costava 95-300 ms a passo durante il trascinamento di uno splitter.
- I grafici sono sedici in `ui/energy_pages.py` (Producibilità 3, Consumi 4, Bilancio ed economia 9) più quelli del confronto delle varianti.
- La **relazione PDF** non usa questi widget: `ui/report.py` disegna le sue figure da sé con `FigureCanvasAgg` a 200 dpi in PNG (mensile, catena delle perdite, flusso di cassa). Cambiare la libreria della finestra non tocca la relazione.

### D.3 Le strade e le fonti [V]

| Strada | Licenza | Che cosa dà | Note dalla documentazione |
|---|---|---|---|
| matplotlib 3.11 con gli eventi | basata sulla PSF | `motion_notify_event`, `pick_event` sulla legenda, il widget `Cursor` con `useblit=True`; il blitting «can be used to (drastically) improve performance of interactive figures»; `NavigationToolbar2QT` per zoom e pan; mplcursors (zlib) per le annotazioni al passaggio | «Not all backends support blitting» (QtAgg sì); le regole `path.simplify` e lo stile `fast` per le linee lunghe |
| pyqtgraph 0.14.0 (16/11/2025) | MIT | «fast, interactive graphics»; «not nearly as complete/mature as matplotlib, but runs much faster»; mirino con `sigMouseMoved` e `InfiniteLine`; `ViewBox` con pan e zoom a rettangolo; `clipToView` e `autoDownsample`; legenda; esportazione SVG «preferred method for generating publication graphics» | Python 3.12+, Qt 6.8+, PySide6; «antialias False at the cost of reduced performance» è il predefinito; lo sfondo predefinito è nero, da impostare; «Printer... poorly supported» |
| Qt Graphs 2D (6.12) | GPL-3 o commerciale (Meridiana è GPL-3) | «Graphs 2D support only Qt Quick applications»: QML in un `QQuickWidget`; il segnale `hover(seriesName, position, value)`; zoom e pan dalla 6.9; il backend Canvas Painter dalla 6.12 | Nella guida di migrazione mancavano titoli e legende (6.8); ogni `QQuickWidget` è «at least one additional render pass»; senza GPU non disegna (come la vista 3D) |
| Qt Charts | nel pacchetto | `QChartView`, `hovered` per punto e per barra, zoom a rettangolo | «The Qt Charts module has been deprecated since Qt 6.10»; «We strongly advise against using it in new code» |
| Vista web (QtWebEngine) con una libreria JavaScript | LGPL-3 più Chromium; uPlot MIT (50 KB), Chart.js MIT, ECharts Apache-2, Plotly MIT (4,8 MB) | HTML e SVG come nella tela | La ruota `PySide6-WebEngine` 6.12 pesa 111 MiB su Linux e 126 su Windows; «Page rendering and JavaScript execution are separated from the GUI process»; il ponte `QWebChannel` è «asynchronous»; `printToPdf` asincrono; non si compila con MinGW |

### D.4 La prova [V, prova: `grafici_prova.py`, `grafici_prova-risultati.txt`]

Un anno di valori orari (8.760 punti) e il mensile, finestra di 600 × 300 px, offscreen, Python 3.13, PySide6 6.12. Due corse (la seconda tra parentesi dove diversa).

| Strada | Primo disegno | Ridisegno | Passaggio del mouse | Zoom | Memoria | PDF |
|---|---|---|---|---|---|---|
| matplotlib QtAgg | 243 (317) ms | 153 (180) ms | 179 ms con il ridisegno, **7,3 (9,0) ms con il blitting**; mensile 105 ms | con la barra di navigazione, un ridisegno | +51 MB | 710 (823) ms, 38 KB vettoriale |
| pyqtgraph 0.14 | 32 (38) ms senza antialiasing, 24 (31) con | 1-2 ms | mirino **3 (2) ms** e 4 (3) con antialiasing | 9 ms | +13 (14) MB | SVG dall'esportatore o `QPdfWriter`; la relazione resta a matplotlib |
| Qt Charts | 37 (58) ms | 6 ms | segnale per punto (non misurabile senza mouse) | 14 ms | +5 (4) MB | `render` su `QPdfWriter` |
| Qt Graphs 2D | 173 (245) ms di caricamento del QML | non disegna offscreen | segnale | | +29 (31) MB | `grabToImage`, raster |
| Vista web | 115 (535) ms la pagina; la prima corsa fredda del browser 9,3 s | | | | +68 (65) MB nel processo principale, più il processo del browser | `printToPdf` asincrono |

Le schermate: `grafici_prova_matplotlib.png`, `_pyqtgraph.png` (con il mirino e la lettura), `_qtcharts.png`, `_web.png`; quella di Qt Graphs è vuota (nessuna GPU offscreen).

- Con matplotlib il valore al passaggio si fa in 7-9 ms **solo con il blitting** (lo sfondo tenuto, solo l'annotazione ridisegnata); zoom e scelta delle serie restano un ridisegno di 150-190 ms sull'orario, 105 sul mensile: si sente, non blocca.
- pyqtgraph sta sotto i 10 ms in tutto: è l'unica strada con il mouse «vivo» su 8.760 punti senza trucchi, e costa 14 MB.
- Qt Graphs chiede la GPU come la vista 3D e un `QQuickWidget` per grafico (sedici): troppo per quello che dà oggi.
- La vista web riproduce la tela, ma al prezzo di 111-126 MiB di installazione, un processo in più e un ponte asincrono per ogni numero: sproporzionato per sedici grafici di una pagina.

### D.5 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| D1 | **matplotlib con gli eventi**: il valore al passaggio con un'annotazione e il blitting, la barra evidenziata, lo zoom con la barra di matplotlib o la rotella, il clic sulla legenda | Nessuna dipendenza; stessa grafica della relazione; `Chart` resta; 7-9 ms al passaggio | Zoom e serie a 105-190 ms; la barra di navigazione di matplotlib ha il suo aspetto (icone sue) e si deve ridisegnare con il tema; il blitting è fragile al ridimensionamento (lo sfondo va rifatto) | 2-3 giorni | 3 | 4 | 4 |
| D2 | **pyqtgraph**: mirino con la lettura dei valori, zoom con il trascinamento e la rotella, serie accese e spente dalla legenda, il tema applicato | 1-4 ms in tutto; widget Qt nativo (si stilizza con la palette e il foglio di stile); 8.760 punti senza fatica; `clipToView` per le serie lunghe | Una dipendenza nuova (da proporre); le quattro funzioni di `Chart` da riscrivere (barre impilate, mappa di calore, variazioni); la legenda e i titoli meno curati di matplotlib; lo stile è pensato per il nero: i colori del tema vanno impostati uno a uno | 5-7 giorni | 5 | 4 | 3 |
| D3 | **Vista web** con una libreria JavaScript | La resa della tela; i tooltip con tutte le serie, la panoramica con il pennello | 111-126 MiB; un processo del browser; il ponte asincrono; un secondo modo di disegnare per il PDF; sedici viste web in una pagina | 8-10 giorni | 4 | 2 | 1 |
| D4 | Qt Graphs 2D in `QQuickWidget` | Nel pacchetto; stessa catena della vista 3D | GPU necessaria; un `QQuickWidget` per grafico; legende e titoli ancora indietro; solo raster per il PDF | 6-8 giorni | 2 | 2 | 2 |

### D.6 Il prototipo

- In `D-grafici.html`, D2 è il prototipo della strada raccomandata: il mensile con le barre evidenziate e il valore, l'orario con il mirino, la lettura in alto, lo zoom trascinando e la legenda che accende e spegne; il tempo di disegno dell'SVG è scritto sotto ogni grafico.
- In Qt, `grafici_prova_pyqtgraph.png` è il mirino di pyqtgraph sull'anno sintetico, con la lettura «ore: kW» accanto al puntatore, misurato a 2-4 ms.

### D.7 Raccomandazione

- **D2, pyqtgraph** [D], in due passi: (1) `Chart` riscritto sopra `PlotWidget` con le stesse quattro funzioni (barre, variazioni, mappa di calore, linee), il messaggio, «Tabella», il tema (fondo, assi, griglia, colori delle serie da `theme_colors`, carattere Titillium Web), le serie lunghe con `clipToView`; (2) il mirino con la lettura dei valori, lo zoom con la rotella e il trascinamento, «Inquadra» con il doppio clic, la legenda che accende e spegne le serie, l'esportazione in SVG e PNG dal menu contestuale. La relazione PDF non cambia (`ui/report.py`).
- La dipendenza è una decisione di Daniel: pyqtgraph è MIT, puro Python, vuole solo numpy, che c'è già; PySide6 6.12 è tra le versioni dichiarate.
- Se Daniel non vuole la dipendenza, **D1** dà il valore al passaggio in 7-9 ms con il blitting e la scelta delle serie dalla legenda in 2-3 giorni; lo zoom resta lento sull'orario.

**Domande per Daniel.** pyqtgraph come dipendenza nuova? Quali interazioni contano di più: il valore al passaggio, lo zoom (solo sugli orari?), la scelta delle serie? «Tabella» resta?

## E. Aiuti accanto alle cose

### E.1 Cosa chiede Daniel

R24: «non ci sono helper di fianco ai risultati o nelle varie sezioni che li spiegano, che spiegano come utilizzare i comandi, cosa vogliano dire determinate cose».

### E.2 Che cosa fa oggi Meridiana [V]

- La **barra di stato** spiega lo strumento attivo («Sottocampo: disegna l'area dove possono andare i moduli», `self.tips` in `ui/window.py`): c'è, e resta.
- **41 suggerimenti** (`setToolTip`) nella finestra: alcuni con la sostanza («The distributor decides; CEI 0-16 Tab. 4 indicates low voltage up to 100 kW…», il parapetto che fa ombra), molti che ripetono il testo del menu a tendina; un solo `setStatusTip`. Nessun `QWhatsThis` (Maiusc+F1), nessun «?», nessun collegamento al manuale (`QDesktopServices.openUrl` non è usato nella finestra).
- **«Come è calcolato»** (`ui/pedigree.py`, `PedigreeView`): in ogni pagina dell'energia la scheda con i record del calcolo, le formule e le fonti; è l'aiuto più ricco del programma, ma sta in un'altra scheda rispetto al numero che spiega.
- **Meridio** risponde alle domande sul progetto; le domande pronte dipendono dalla scheda (`assistant.questions(tab)`).
- I testi d'aiuto che esistono stanno sparsi nel codice come stringhe `_()`: nessun posto unico, nessun controllo che ogni campo ne abbia uno.

### E.3 Come fanno i programmi di riferimento [V]

| Fonte | Che cosa dice |
|---|---|
| NN/g, Tooltip Guidelines (2019) | «Users shouldn't need to find a tooltip in order to complete their task»; i requisiti dei campi non vanno nei tooltip; «Tooltips are best when they provide additional explanation for a form field unfamiliar to some users»; l'icona «?» o «i» solo per i riquadri a clic |
| Microsoft, Win32 UX (2025) | Tooltip in 0,5 s, via dopo 5 s, «five words or less»; infotip «25 words or less»; «If it is essential, put it directly in the UI»; «Help is a last resort»; da evitare «'Learn more' links, generic Help buttons, and context-sensitive Help buttons on the title bar»; i collegamenti all'aiuto come domande («How do I…») |
| WinUI (2025-2026) | Tooltip: «if the information is available elsewhere in the same experience, you do not need a tooltip»; TeachingTip: «users, on average, only read 3-5 words»; InfoBar: icone e colore mai soli |
| GNOME HIG | «Don't rely on tooltips to communicate essential information»; se un controllo del contenitore ha il tooltip, tutti devono averlo; F1 aiuto, Ctrl+? scorciatoie; le righe delle liste con il sottotitolo (`AdwActionRow`); i banner per gli avvisi di contesto |
| Apple HIG, Offering help | «60 to 75 characters» per i tooltip; «avoid repeating a control's name»; il pulsante d'aiuto «circular, consistently sized buttons that contain a question mark», «no more than one help button per window», nell'angolo in basso |
| JetBrains | «Always use the help tooltip with the question mark icon», 250 px, 10 righe, 500 ms; l'inline help «no more than five lines», «70 characters» per riga, nelle finestre delle impostazioni «not constrained by space and not frequently used»; «Do not explain each option» |
| Blender 5.2 | Il tooltip con descrizione, scorciatoia, valore e, a scelta, il comando Python; F1 apre il manuale online sulla voce; «holding Alt then hovering» per vederlo subito |
| VS Code | Ogni impostazione ha `description` o `markdownDescription` sotto il campo; i walkthrough per cominciare |
| PVsyst, Revit, AutoCAD, DIALux evo | PVsyst: «press F1» apre l'aiuto sulla sezione, «small question mark buttons»; Revit: il tooltip esteso dopo un altro attimo («If you leave the cursor over the ribbon tool for another moment, additional information displays»), F1 contestuale, livelli Minimal/Normal/High; AutoCAD: tooltip estesi e «rollover»; DIALux evo: il menu «[?]» |
| KDE, Qt | «What's This? (Shift+F1)»; `QWhatsThis` «typically longer and more detailed than tooltips», il «?» nei dialoghi; `QWidget.toolTipDuration`, `whatsThis`, `statusTip`; dal 6.12 `QStyleHints::toolTipWakeUpDelay` |

Il filo comune: **l'essenziale nell'interfaccia** (etichetta, unità, frase sotto il campo), **il perché a richiesta** (il «?», Maiusc+F1), **il resto nel manuale** con un collegamento preciso, mai un «Aiuto» generico.

### E.4 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| E1 | **Il «?» accanto ai titoli e ai campi**: un pulsante piatto di 16 px accanto a ogni titolo di gruppo e ai campi che lo meritano; un clic apre un riquadro di tre righe con la fonte e i collegamenti al manuale e a «Come è calcolato» | La convenzione di macOS, JetBrains e dei dialoghi GTK; non ingombra; lo stesso riquadro serve ai risultati (un «?» accanto al numero); in Qt un `QToolButton` e un `QFrame` figlio della finestra (il popover della prova C2) | Un clic in più; il «?» va dosato (uno per gruppo, non per ogni campo); un «?» accanto a tutto diventa rumore | 2 giorni più i testi | 5 | 4 | 4 |
| E2 | **Frasi sotto i campi e suggerimenti estesi**: una frase attenuata sotto i campi che non si spiegano da soli; il suggerimento esteso (titolo, due righe, scorciatoia) dopo un attimo di sosta | Sempre visibile, non si cerca (NN/g); VS Code e GNOME lo fanno; il suggerimento esteso usa `QToolTip` con HTML, già in Qt | Allunga le Proprietà (ogni frase è una riga); va dosata; il tooltip resta un tooltip (sparisce, non si copia) | 1-2 giorni più i testi | 4 | 4 | 4 |
| E3 | **Un pannello d'aiuto che segue il fuoco**: un riquadro in fondo alle Proprietà (o un pannello Ctrl+?) che spiega il campo che ha il fuoco o il risultato sotto il mouse, con i collegamenti | Il «Dynamic Help» di Visual Studio e il pannello info di Blender; sempre lì, mai sopra; una cosa sola da imparare | Costa 70-90 px di altezza sempre; chi non lo guarda non lo vede; il fuoco salta con la tastiera; un pannello in più da chiudere | 2-3 giorni più i testi | 3 | 3 | 3 |

### E.5 Il contenuto: chi lo scrive, dove sta, come resta aggiornato [I]

- **Dove**: un modulo del nucleo, `src/meridiana/help.py`, con un dizionario `TEXTS` per identificatore («subfield.row_gap», «production.specific_yield», «checks.fail») e per ognuno: la frase breve (al massimo 75 caratteri, Apple), il testo (al massimo cinque righe di 70 caratteri, JetBrains), la fonte con lo stesso nome usato dalle verifiche (`checks.py`, `rules.py`), l'àncora nel manuale, il tipo di record di «Come è calcolato». Le stringhe passano da `_()`: l'inglese nel codice, l'italiano in `po/it.po`, come tutto il resto.
- **Chi**: le sessioni scrivono le bozze dai calcoli e dalle regole; Daniel rivede la sostanza tecnica e le fonti, come per le verifiche. Le norme non si citano a memoria: dove serve l'articolo, il testo lo lascia a lui.
- **Come resta aggiornato**: un test che ogni «?» e ogni frase sotto un campo abbia il suo testo in `help.py`, che nessun testo superi le lunghezze, che ogni fonte citata esista in `rules.py`; il testo sta accanto al campo che spiega (l'identificatore è quello del campo in `properties.py`), così una modifica al campo trova il suo testo.
- **I collegamenti**: «Manuale ›» apre `docs/manuale/…#àncora` con `QDesktopServices.openUrl` (locale o in rete); «Come è calcolato ›» porta alla scheda e scorre al record; «Chiedi a Meridio ›» apre la chat con la domanda pronta.

### E.6 Esempi scritti [I, in `E-aiuti.html`]

Proprietà del sottocampo:
- **Montaggio**: come i moduli stanno sulla superficie: complanari alla falda, su file inclinate (ancorate o zavorrate), est-ovest, a terra, in pensilina. Decide pendenza e passo.
- **Moduli per tavola, di traverso**: quanti moduli uno sopra l'altro in una tavola: 2 è la «2V» dei montaggi a terra.
- **Tra le file**: sulle falde è un valore; a terra lo dà il sole: nessuna ombra tra le file nel giorno di progetto, tra le ore della finestra.
- **Fuori dalle ombre**: toglie i moduli che gli ostacoli ombreggiano nel giorno di progetto. Dice quanti moduli costa.

Producibilità:
- **Resa specifica**: i kWh prodotti in un anno per ogni kWp installato. In Italia tra 1.000 e 1.500: sotto, cerca le ombre e l'orientamento.
- **Performance ratio**: quanto dell'energia che arriva sui moduli diventa energia al contatore. Tra 0,75 e 0,85 è normale.
- **Perdite**: ogni voce è un passo della catena, dal sole al contatore: ombre, temperatura, sporco, cavi, inverter. «Come è calcolato» mostra la formula e la fonte di ogni numero.
- **PVGIS**: l'anno tipo e l'orizzonte del sito, dal servizio europeo. Scaricati una volta, poi in cache.

Bilancio ed economia:
- **Autoconsumo**: la parte della produzione usata sul posto, ora per ora. Il resto va in rete.
- **Autosufficienza**: la parte dei consumi coperta dall'impianto. Con l'accumulo sale.
- **VAN**: il valore attuale netto a 20 anni: quanto rende l'impianto oltre il costo, scontato al tasso scelto. Positivo conviene.
- **Prezzi**: valori indicativi finché non scrivi quelli della bolletta e del preventivo; la relazione lo dice.

Verifiche:
- **Da correggere**: qualcosa che la norma o la posa non ammette: il progetto non va consegnato così. «Correggi» fa la cosa proposta, annullabile.
- **Da controllare**: una perdita o un rischio, non un divieto: decidi tu.
- **Da sapere**: un fatto che la relazione citerà: una soglia superata, un valore predefinito ancora in uso.
- **Fonte**: la norma con l'articolo e la pagina, o il modello di calcolo. Un clic la apre in «Come è calcolato».

I numeri degli esempi (1.000-1.500 kWh/kWp, 0,75-0,85) sono ordini di grandezza da confermare con Daniel, non valori di norma.

### E.7 Raccomandazione

- **E1 più la parte buona di E2** [D]: il «?» accanto ai titoli dei gruppi delle Proprietà, ai riquadri dei risultati e ai titoli dei grafici, che apre il riquadro con il testo, la fonte e i tre collegamenti; la frase sotto il campo **solo** dove il valore non si spiega da solo (Tra le file, Fuori dalle ombre, il giorno di progetto, Prezzi); i suggerimenti estesi (titolo, frase, scorciatoia) sugli strumenti della barra, che già hanno le sole icone; **Maiusc+F1** e il «?» della finestra per la via da tastiera, con gli stessi testi (`setWhatsThis`).
- La barra di stato resta per lo strumento; «Come è calcolato» resta la spiegazione lunga, raggiunta dal riquadro.
- E3 no come pannello fisso; sì come **modo** del riquadro: chi vuole può agganciarlo («Tieni aperto») in fondo alle Proprietà.

**Domande per Daniel.** Il «?» per gruppo o anche per campo? Le frasi sotto i campi: quali campi? Il manuale: in `docs/manuale/` nel repository (aperto dal programma come file) o in rete?

## F. Il pannello Verifiche

### F.1 Cosa chiede Daniel

R13: «è di sicuro da migliorarne il modo in cui vengono esposti tutti gli elementi perché siano più comprensibili». I pulsanti «Mostra ciò che…» che non funzionano bene sono nei ritocchi, passo 9.

### F.2 Che cosa fa oggi Meridiana [V]

- `checks.Item`: livello (`fail`, `warn`, `info`, `ok`), area, frase, fonte, bersaglio (`target`: sottocampo, edificio, scheda, sito), correzione (`fix`) con la sua etichetta (`fix_label`). Gli elementi sono ordinati per livello (`checks.py`), i conteggi per livello esistono (`counts`), e `about(items, kind, oid)` dà quelli che riguardano un oggetto.
- `ui/checks_page.py`: un `QTreeWidget` a tre colonne (segno, Che cosa, Fonte) con un nodo per **area** (Posa, Ombre, Stringhe, Connessione, Economia…) e sotto le righe; il segno nel carattere dei simboli e nel colore del livello; quattro pulsanti con i soli segni per filtrare i livelli (il suggerimento dice «Mostra ciò che è da correggere»); sotto, «Correggi» con l'etichetta della correzione e «Copia le note per la relazione»; il doppio clic porta all'oggetto; la selezione nelle viste mette in grassetto le righe sull'oggetto e scorre alla prima (`show_related`, il «Show Related Warnings» di Revit); il titolo del dock porta i conteggi.
- Quello che manca per capire: la frase è una sola riga con l'etichetta della correzione in coda tra parentesi quadre; non c'è il perché né il «che cosa fare» se non si corregge; l'area è un nome tecnico; non si vede a colpo d'occhio quali oggetti hanno problemi; i filtri sono quattro segni senza il numero.

### F.3 Come fanno i programmi di riferimento [V]

| Programma | Raggruppamento | Frase e dettaglio | Azioni e legame con le viste |
|---|---|---|---|
| VS Code, pannello Problemi | Per file (albero) o tabella («View as Table»); filtri per tipo, per file attivo, con esclusioni; i conteggi nella barra di stato | Una riga per problema con il codice e la fonte; Alt+F8 passa al successivo | Il clic porta alla riga; la lampadina offre le correzioni («Quick Fix») |
| JetBrains, Problems | Per file; gli errori dell'ispezione corrente | | «Fix» dalla riga |
| Revit, Review Warnings | Un albero per avviso con gli elementi; «Expand» mostra la struttura; «Show» evidenzia gli elementi; «Delete Checked» | «You can ignore warnings that require no action» («warning messages do not prohibit the current action») | «Show Related Warnings» dall'elemento selezionato; «the element highlights in all open views» |
| PVsyst | Semafori per sezione: «a red button means parameters to be defined, or not acceptable», «An orange button means acceptable, but not ideal»; «The Simulation will be enabled only when no button is red» | | Il pulsante rosso è nella sezione da sistemare |
| Aurora, OpenSolar | Il «Validation Report» avverte il progettista; i moduli «flash red» quando finiscono dentro una fascia di rispetto | | L'avviso è dove si disegna |
| Solibri | Per severità: «critical, moderate, or low»; accettare o rifiutare ogni risultato («the icon of the severity turns grey») | | |
| Navisworks, Clash Detective | Stati (New, Active, Reviewed, Approved, Resolved), gruppi, «Auto-Load viewpoint» | | La vista salta al punto |
| Office, Accessibility Checker | «Warnings, Errors, and Tips» con i conteggi | «see why and how to fix an issue»; «Recommended Actions» | L'azione proposta accanto |
| NN/g, Microsoft, JetBrains, KDE | | NN/g: «Display the error message close to the error's source», «never use exclusively color», «offer some potential remedies»; Microsoft: «problem, cause, and solution», «a single, complete sentence», «Avoid the word 'please'»; JetBrains: «Incorrect», non «Illegal»; KDE: «All error messages must be actionable», «Fix it» | |

Il filo comune: **per oggetto o per gravità, con i conteggi**; la frase breve con **il perché e la soluzione** a portata; l'azione («Fix») sulla riga; il clic che porta all'oggetto e l'oggetto che porta alle sue verifiche.

### F.4 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| F1 | **Per oggetto**: un nodo per oggetto (Copertura Sud, Sito, Copertura Nord) con l'icona del tipo e i conteggi («1 ✘ · 2 ⚠ · 1 ✔»); sotto le voci con la freccia che apre il dettaglio (che cosa, perché, che cosa fare); a destra la fonte, «Correggi» solo dove c'è, l'occhio che mostra l'oggetto nelle viste | Risponde a «che cosa c'è che non va in questa falda»; il modello del pannello Problemi di VS Code (per file) e di Revit; `target` e `about()` ci sono già; sta bene con l'albero del progetto (T2: gli stessi segni) | Le voci del sito (connessione, prezzi) stanno in un nodo «Sito» un po' lontano dal resto; per la relazione l'ordine per area era più comodo | 2-3 giorni | 5 | 4 | 4 |
| F2 | **Per livello, in schede**: prima «Da correggere», poi «Da controllare», «Da sapere», «Superate» (chiusa), ogni livello una scheda con il titolo in maiuscoletto; la frase porta l'oggetto davanti | Chiaro per chi deve consegnare: si parte dall'alto; il «Review Warnings» di Revit e l'Accessibility Checker; l'ordine per livello è già quello di `checks.py` | L'oggetto si ripete in ogni frase; i filtri per livello diventano doppi (schede chiuse o filtri); con molte «superate» la scheda in fondo è lunga | 2 giorni | 4 | 4 | 4 |
| F3 | **Per area, in tabella**: colonne segno, che cosa, dove, fonte, azione; le aree come righe di intestazione; ordinabile per colonna | L'ordine di oggi, ma leggibile; la «View as Table» di VS Code; adatta alla relazione e a «Copia le note» | Densa; il dettaglio a richiesta ci sta male in una tabella; le aree restano nomi tecnici | 1-2 giorni | 3 | 5 | 4 |

### F.5 Che cosa cambia nel codice [I]

- `checks.Item` prende un campo **`detail`** (il perché e che cosa fare, due o tre frasi) e, dove serve, i moduli coinvolti; lo scrivono le verifiche che già sanno il perché (`checks.py`, `energy/stringing.py`).
- Le tre viste sono tre modi di riempire lo stesso `QTreeWidget`: per oggetto (`target`), per livello, per area; un menu «Per oggetto ⌄» nella testa del pannello; la scelta resta nelle impostazioni (`config.py`).
- La riga aperta mostra il dettaglio come riga figlia a tutta larghezza (`setFirstColumnSpanned`, testo a capo con un delegato), non in un tooltip (NN/g: il dettaglio essenziale non va nel tooltip).
- «Correggi» e l'occhio come pulsanti nella riga (`setItemWidget` nell'ultima colonna) solo dove c'è una correzione; il pulsante grande sotto può restare per la tastiera; «Copia le note» resta.
- I filtri per livello restano pulsanti, con il segno **e il numero** («✘ 1»); i conteggi anche nella barra di stato, come VS Code; i ritocchi (passo 9) sistemano il loro difetto prima.
- Il legame con le viste è già in due sensi (doppio clic e `show_related`): si aggiunge l'occhio sulla riga e, nella pianta, il segno sull'oggetto (il piccolo segno delle verifiche dei ritocchi, passo 10, vale anche in pianta).

### F.6 Raccomandazione

- **F1 per oggetto come vista predefinita** [D], con il passaggio a per livello (F2) e per area (F3) dal menu nella testa del pannello; il dettaglio a richiesta con la freccia; «Correggi» e l'occhio sulla riga; i conteggi nei filtri, nel titolo e nella barra di stato; le «superate» chiuse per impostazione.
- Le frasi secondo le regole raccolte: una frase, il problema prima della causa, il numero che conta («3 moduli nell'ombra del Camino 1 nel giorno di progetto»), la fonte con il nome di `rules.py`; il dettaglio dice il perché e che cosa fare, anche quando non c'è «Correggi».

**Domande per Daniel.** Per oggetto o per livello come predefinita? «Correggi» sulla riga o solo sotto? Le «superate» nascoste finché non si chiedono?

## G. Meridio e la sua chat

### G.1 Cosa chiede Daniel

R15: «sarà da migliorarne l'estetica, renderlo magari dinamico, e migliorare anche l'estetica della chat con qualche animazione in apertura / chiusura, mentre sta parlando l'assistenza, possibilità di ridimensionare la chat, vista delle risposte consigliate più chiara con elenco».

### G.2 Che cosa fa oggi Meridiana [V]

- `assistant.py`: Meridio è un SVG su una griglia di 24: i raggi nel colore del testo, il disco del sole nel colore dell'assistente (la tinta opposta all'accento, studio 13, sezione 12), il sorriso e gli occhi nell'inchiostro scuro «come un adesivo»; «pensa» alza gli occhi di 0,8 e mostra tre puntini in alto a destra. Le domande pronte dipendono dalla scheda (`questions(tab)`).
- `ui/assistant.py`: la pixmap del personaggio è in cache (`picture`, `lru_cache`, resa da `QSvgRenderer` una volta per colore e dimensione); `Face` disegna il cerchio e la pixmap; chiuso è un cerchio di 46 px, aperto un pannello di **320 × 400 px a dimensione fissa** (`OPEN_SIZE`, `setFixedSize`), sotto 260 px di altezza le domande pronte spariscono; la sola animazione è lo scivolamento della posizione (`QPropertyAnimation` su `pos`, 320 ms), saltata con «meno movimento» (letto da Windows in `ui/theme.py`); la conversazione in un `QTextBrowser`, le domande pronte come tre `QPushButton`; nessun respiro, nessuno sguardo, nessuna animazione di apertura oltre lo scivolamento, nessun indicatore mentre risponde oltre alla faccia che «pensa», nessuna maniglia per ridimensionare.

### G.3 Come fanno i programmi di riferimento [V]

| Fonte | Che cosa dice |
|---|---|
| Microsoft Agent, Agent States (1998-2018, ritirato ma è la guida più esplicita sui personaggi) | «Design animations for the Idling states to communicate the state of the character, but not to distract the user»; «glancing around or blinking are good animations to assign to the IdlingLevel1 state»; «Animations that include many or large movements are not well suited for idle animations because they draw the user's attention»; «Maintaining the illusion does not take much: sometimes just an animated blink, visible breath, or body shift»; «randomly choose one of your animations»; Think «looks up and holds hand on head» |
| Duolingo, Rive (2022-2025) | I personaggi hanno una macchina a stati con «idle behavior like head nods, blinking, and eyebrows moving»; Lily con «eight different head animations and eight body animations»; i runtime Rive sono MIT ma non c'è un widget Qt ufficiale |
| Material 3, Motion | Durate: short 50-200 ms, medium 250-400, long 450-600; «duration should increase as the area/traversal of an animation increases»; la curva «emphasized decelerate» (0,05, 0,7, 0,1, 1) per ciò che entra |
| Fluent 2, Windows | 250 ms normale, 167 veloce, 83 velocissima; entrata con la curva (0, 0, 0, 1), uscita (1, 0, 1, 1); l'uscita «ALWAYS combine with fade out»; «Bare Minimum Fade 83ms»; «Design for and include a "no motion" setting» |
| Apple HIG, Motion | «Add motion purposefully»; «Don't add motion for the sake of adding motion. Gratuitous or excessive animation can distract people and may make them feel disconnected or physically uncomfortable»; «Make motion optional»; con meno movimento «Replacing transitions in x-, y-, and z-axes with fades» |
| GNOME, GTK | `gtk-enable-animations` e la preferenza «reduced motion» dal portale (`org.freedesktop.portal.Settings`); nella discussione GTK (2025): «Disabling every animation is not an accessibility setting: animations convey meaning» |
| WCAG 2.2, 2.3.3 | Il movimento innescato dall'interazione si deve poter spegnere, salvo quello essenziale |
| NN/g (2014, 2020) | «Movement in a person's peripheral vision triggers a stimulus-driven shift in visual attention»; «Slower transitions are less likely to cause an attention shift»; «Animations that are repeatedly encountered are roadblocks to content»; il riscontro «within 0.1 seconds»; «Animation in UX must be unobtrusive, brief, and subtle» |
| Le chat (VS Code Copilot 2026, Bot Framework, Copilot Studio, Material) | «progress indicator visible until an agent response finishes», il pulsante Stop nel campo; le risposte pronte «shown to the user for a single turn», «disappear after the user makes a selection»; «up to 10 suggested prompts»; i «suggestion chips» per restringere l'intento |
| Qt 6.12 | `QSizeGrip` ridimensiona «any widget with the Qt::SubWindow flag set»; le animazioni «are controlled by a global timer»; `QVariantAnimation` 250 ms predefiniti; `QGraphicsEffect`: «disable certain effects on slow platforms»; `windowOpacity` «update and resize significantly slower»; `QPainter`: `drawPixmap()` «in combination with simple transformations and opacity» è la via veloce; `QSvgRenderer` anima gli SVG con `animationEnabled` (6.7); `QQuickWidget` «disables the threaded render loop»; Qt Lottie è QML e GPL |

Il filo comune: **poco e lento** quando è fermo (respiro, battito di ciglia, sguardo), **breve** quando cambia (200-250 ms in entrata, meno in uscita, con la dissolvenza), **spento** quando il sistema chiede meno movimento, con gli stati che restano leggibili senza il movimento.

### G.4 Le direzioni

| | Che cosa | Pro | Contro | Fatica | Eff. | Rischio | Costo |
|---|---|---|---|---|---|---|---|
| G1 | **Respiro e sguardo, apertura dall'angolo, puntini, domande come elenco**: il personaggio respira (scala 1 → 1,04 in 4 s), gli occhi seguono il mouse di mezzo punto, «pensa» alza gli occhi e mostra i puntini; la chat si apre dall'angolo del personaggio in 220 ms (scala e dissolvenza) e si chiude al contrario; mentre risponde tre puntini nel fumetto e la faccia che pensa; le domande pronte in un elenco con la freccia; l'angolo in basso a destra ridimensiona | Il «visible breath» e lo sguardo di Microsoft Agent: vivo senza muoversi; durate nelle fasce di Material e Fluent; in Qt tutto con pixmap in cache e `QPropertyAnimation`; misurato sotto 0,2 ms a fotogramma | Lo sguardo che segue il mouse va dosato (un pixel, con un ritardo): se insegue troppo distrae (NN/g); il respiro continuo è un'animazione «repeatedly encountered»: va tenuto lento e piccolo | 3-5 giorni | 5 | 4 | 3 |
| G2 | **I raggi girano, scivola dal basso, testo che scorre, pastiglie**: i raggi girano in un minuto e il disco pulsa; la chat scivola dal basso in 260 ms; la risposta arriva parola per parola con il cursore; le domande pronte come pastiglie | Il movimento è nel contorno, non nel viso; lo scorrere del testo è l'uso delle chat dei modelli | I raggi che girano sono un movimento continuo in periferia (NN/g); il testo parola per parola richiede lo streaming dal fornitore (studio 14) e nel `QTextBrowser` un aggiornamento per parola; le pastiglie con frasi lunghe vanno a capo e si leggono peggio dell'elenco | 3-4 giorni | 3 | 3 | 3 |
| G3 | **Fermo, cambia solo di stato, nessuna animazione, numerate**: il personaggio cambia espressione per stato, il puntino nel suo colore dice che ha un parere; la chat appare e sparisce; le domande numerate si scelgono con 1, 2, 3 | È ciò che resta con «meno movimento»: la base obbligata; i numeri danno la via da tastiera | Da solo è quello di oggi con le espressioni: non risponde a «renderlo dinamico» | 1-2 giorni | 2 | 5 | 5 |

### G.5 La prova in Qt [V, prova: `meridio_prova.py`, `meridio_prova-risultati.txt`]

Meridio di 46 px con la pixmap in cache di oggi, 60 fotogrammi per misura, chiaro e scuro, offscreen (`meridio_prova_*_chiuso.png`, `*_aperto.png`):

| Misura | Chiaro | Scuro |
|---|---|---|
| respiro: la pixmap disegnata scalata (1,00-1,04) | 0,13 ms/fotogramma | 0,12 |
| sguardo: nove pixmap pre-disegnate (occhi spostati di ±0,5), disegnate una volta in 1,6 ms | 0,03 ms/fotogramma | 0,03 |
| «pensa»: le due pixmap alternate | 0,03 ms/fotogramma | 0,03 |
| l'SVG reso di nuovo a ogni fotogramma (senza cache) | 0,18 ms/fotogramma | 0,19 |
| apertura della chat (320 × 400, geometria e opacità, 220 ms, OutCubic) | 227 ms, 12 fotogrammi, 1,5 ms di disegno a fotogramma con `QGraphicsOpacityEffect` | 225 ms, 12 fotogrammi, 1,4 ms |
| lo stesso disegno senza l'effetto di opacità | 1,1 ms | 1,0 |

- A 20 fotogrammi al secondo il respiro costa circa 2,5 ms di CPU al secondo sul thread della finestra: nulla, anche su un portatile. Lo sguardo e «pensa» costano meno del respiro perché non scalano.
- Anche senza cache l'SVG di Meridio si rende in 0,2 ms: la cache serve, ma non è ciò che decide.
- L'apertura con l'opacità raddoppia il costo del fotogramma (1,0 → 1,5 ms): resta trascurabile; offscreen i 12 fotogrammi sono quelli del timer delle animazioni di Qt (circa 60 al secondo nella finestra vera, da vedere sul PC).
- Il ridimensionamento non ha bisogno di prova: `QSizeGrip` in un angolo e `setMinimumSize`/`setMaximumSize` al posto di `setFixedSize`.

### G.6 Raccomandazione

**G1 sopra la base G3** [D]:
- **il personaggio**: il respiro a 20 fotogrammi al secondo (scala 1 → 1,04 in 4 s, curva seno) con la pixmap in cache; lo sguardo con nove pixmap (±0,5 unità), che segue il mouse della finestra con 100 ms di ritardo e torna al centro dopo 2 s fermo; il battito di ciglia ogni 4-8 s a caso (Microsoft Agent: «randomly choose»); «pensa» (occhi in su e puntini) mentre Meridio lavora; tutto fermo quando la finestra non è attiva o Meridio è coperto;
- **la chat**: si apre dall'angolo del personaggio in 220 ms (geometria e opacità, curva in uscita morbida) e si chiude in 160 ms con la dissolvenza (Fluent: l'uscita sempre con il fade); si ridimensiona dall'angolo in basso a destra con `QSizeGrip`, da 280 × 240 fino all'area della finestra, e la misura resta in `config.py`; mentre risponde, tre puntini nel fumetto e la faccia che pensa, con «Ferma» nel campo;
- **le domande pronte** come elenco con la freccia e il testo intero, che spariscono per il turno dopo la scelta e tornano al turno dopo; i numeri 1, 2, 3 come scorciatoie (G3);
- **meno movimento**: letto da Windows (già) e dal portale su Linux (`org.freedesktop.portal.Settings`, `reduced-motion`); con la preferenza attiva nessuna animazione, solo i cambi di stato (G3); una preferenza di Meridiana «Meridio animato» per spegnerlo anche senza il sistema.
- G2 no ai raggi che girano e alle pastiglie; sì al testo che scorre quando il fornitore darà lo streaming (studio 14), come opzione.

**Domande per Daniel.** G1 o G2? Il battito di ciglia sì o no? Lo sguardo che segue il mouse o solo verso la selezione? Le domande pronte come elenco (G1) o numerate (G3)?

## Il piano

### Le domande a cui solo Daniel può rispondere

Raccolte dai temi; ognuna cambia il compito corrispondente.

**Risposte di Daniel del 23/10/2026:** A3 («mi piacciono molto») e l'albero T2; B4 («bella la suddivisione in fasi»); tema C: pulsanti e campi di inserimento C2, gruppi C3, risultati R2 senza bordi (precisato nella terza risposta); D2 («forse»: dal browser D2 e D3 sembravano uguali, la differenza sta nel programma); E3 («forse»); F2; le animazioni di G2 con le domande numerate di G3, più tre richieste su Meridio (faccia troppo scura in chiaro, mai coperto dalla chat, la chat come fumetto: R33 nel registro). L'ordine della domanda 8 non è stato contestato. I compiti vengono dopo la revisione completa (R32). Seconda risposta dello stesso giorno: B4 tiene il testo sotto le icone con l'opzione per toglierlo; E3 confermato nella forma del riquadro in fondo alle Proprietà; G2 con i raggi lenti, il battito di ciglia, piccoli movimenti e smorfie casuali; Meridio anche in versione pixelata (R34). I valori stanno in testa a ogni bozza `17a`-`17f`.

1. **A**: A1 (tre livelli) o A2 (un livello con le intestazioni piene), o A1 con le intestazioni piene? L'albero T2 o T3? I titoli dei pannelli in maiuscoletto o nel carattere normale?
2. **B**: la barra B1 sotto le schede o B2 a sinistra come predefinita? «Variante» nell'angolo delle schede o nella barra di stato? La scheda Impianto (studio 16) con la sua barra nella stessa posizione?
3. **C**: C2 tonale con i bordi dei campi, o C3 a contorni? Un solo pulsante pieno per pagina: quali? I risultati R1 (con bordo) o R2 (pieni con il numero chiave)? Il bordo dei campi intero o solo in basso?
4. **D**: pyqtgraph come dipendenza nuova (MIT)? Quali interazioni contano di più (valore al passaggio, zoom, scelta delle serie)? «Tabella» resta?
5. **E**: il «?» per gruppo o anche per campo? Le frasi sotto i campi: quali campi? Il manuale nel repository (`docs/manuale/`) o in rete?
6. **F**: per oggetto o per livello come vista predefinita? «Correggi» sulla riga o solo sotto? Le «superate» nascoste finché non si chiedono?
7. **G**: G1 o G2? Il battito di ciglia? Lo sguardo che segue il mouse o solo la selezione? Le domande pronte come elenco o numerate?
8. **Ordine e insieme**: A e C cambiano lo stesso foglio di stile e `derive()`: vanno insieme in un compito solo (17a) prima degli altri, perché B, E, F e G disegnano sopra quelle superfici. D è indipendente. Va bene così?

### Le bozze dei compiti

In `docs/compiti/`, una per tema, scritte sulla raccomandazione; i valori decisi da Daniel vanno in testa a ognuna prima di darle a una sessione.

| Compito | Tema | Fatica | Dipende da |
|---|---|---|---|
| `17a-superfici-controlli.md` | A e C: i tre livelli, le intestazioni, i gruppi, i pulsanti, i campi, i risultati, il token `card` in scuro, l'albero T2 | 5-7 giorni in due passi | i ritocchi della fase 2 (passo 3 e 10) |
| `17b-strumenti.md` | B: la barra sotto le schede nella scheda Modello, «Variante» nell'angolo, la preferenza «a sinistra» | 1-2 giorni | 17a (il fondo della barra) |
| `17c-grafici.md` | D: `Chart` su pyqtgraph in due passi | 5-7 giorni | la decisione sulla dipendenza |
| `17d-aiuti.md` | E: `help.py`, il «?», le frasi sotto i campi, Maiusc+F1, i testi delle quattro sezioni | 3-4 giorni | 17a (il popover e lo stile) |
| `17e-verifiche.md` | F: le tre viste, il dettaglio, «Correggi» e l'occhio sulla riga, i conteggi | 3-4 giorni | i ritocchi (passo 9), 17a (il delegato dell'albero) |
| `17f-meridio.md` | G: il personaggio animato, l'apertura, il ridimensionamento, le domande come elenco, meno movimento | 3-5 giorni | nessuno |

Ordine proposto: 17a, poi 17b e 17f (brevi, indipendenti), 17e, 17d, 17c per ultimo se la dipendenza è accettata.

### Che cosa resta da vedere sul PC di Daniel

- Le sei schermate di `controlli_prova` e le tre direzioni di A e C **nella finestra vera**, su Windows e su Linux: i contrasti sono misurati, l'impressione no; il tema scuro sull'OLED del portatile.
- I grafici di Qt Graphs e la vista 3D non si disegnano offscreen: se Daniel vuole vedere D4, va provato sul PC con la GPU; pyqtgraph va provato con il tema e con le serie vere (il mensile impilato, la mappa di calore).
- Meridio animato: i numeri dicono che costa nulla; se il respiro distrae si vede solo guardandolo per un'ora di lavoro.
- Il ridimensionamento della chat con `QSizeGrip` su Windows (le finestre senza cornice hanno le loro maniglie).

## Fonti

Tutte lette il 23/10/2026; la data tra parentesi è quella della pagina quando c'è.

**Tema A e B**
- A1 libadwaita, CSS variables (1.10.0): https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/css-variables.html ; style classes (1.11.alpha): https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html ; AdwToolbarView https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ToolbarView.html e ToolbarStyle https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/enum.ToolbarStyle.html ; AdwNavigationSplitView https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.NavigationSplitView.html ; AdwOverlaySplitView https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.OverlaySplitView.html ; adaptive layouts https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/adaptive-layouts.html ; AdwSidebar (1.9) https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.Sidebar.html ; AdwHeaderBar https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.HeaderBar.html ; boxed lists https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/boxed-lists.html
- A2 GNOME HIG: utility panes https://developer.gnome.org/hig/patterns/containers/utility-panes.html ; sidebars https://developer.gnome.org/hig/patterns/nav/sidebars.html ; header bars https://developer.gnome.org/hig/patterns/containers/header-bars.html ; boxed lists https://developer.gnome.org/hig/patterns/containers/boxed-lists.html ; UI styling https://developer.gnome.org/hig/guidelines/ui-styling.html
- A3 VS Code: theme color https://code.visualstudio.com/api/references/theme-color ; custom layout (21/10/2026) https://code.visualstudio.com/docs/configure/custom-layout ; user interface (21/10/2026) https://code.visualstudio.com/docs/getstarted/userinterface
- A4 Blender 5.2: introduction https://docs.blender.org/manual/en/latest/interface/window_system/introduction.html ; areas https://docs.blender.org/manual/en/latest/interface/window_system/areas.html ; regions https://docs.blender.org/manual/en/latest/interface/window_system/regions.html ; tool system (23/10/2026) https://docs.blender.org/manual/en/latest/interface/tool_system.html ; tabs and panels https://docs.blender.org/manual/en/latest/interface/window_system/tabs_panels.html ; preferences interface https://docs.blender.org/manual/en/latest/editors/preferences/interface.html ; themes https://docs.blender.org/manual/en/latest/editors/preferences/themes.html ; outliner https://docs.blender.org/manual/en/latest/editors/outliner/editing.html
- A5 Revit 2023: parts of the user interface https://help.autodesk.com/cloudhelp/2023/ENU/Revit-GetStarted/files/GUID-7793667D-5657-4382-9BEC-F7CB6AC8F53E.htm ; view control bar GUID-42872B9F-A4DE-472A-A88C-77879ACEC93E ; options bar GUID-28BDE98C-E8A9-4C74-8ABC-9DABD13163D9 ; properties palette GUID-A764EA7A-FE26-469B-857C-F3A70812FC34 ; project browser GUID-C8D3E5A6-02A5-43A9-AFFC-D49DD27398B1 ; ribbon GUID-1CA04013-04CE-4F55-9B0C-68FD7E7FF80B ; status bar GUID-23CCC541-4E99-4BCF-B1BA-3271F66477D0 (stessa base dell'URL)
- A6 DIALux: explanation of terms (27/04/2022) https://dialux4.support-en.dial.de/support/solutions/articles/9000115056-explanation-of-terms-legend ; working method of evo (27/04/2022) https://dialux4.support-en.dial.de/support/solutions/articles/9000114906 ; evo KB https://evo.support-en.dial.de/ ; light (12/04/2021) .../9000115305-light ; calculation objects (26/05/2021) .../9000115440 ; documentation (16/03/2017) .../9000116123 ; menu bar (16/04/2021) .../9000115108-menu-bar ; display options (27/05/2021) .../9000115112 ; user views (26/05/2021) .../9000115077 ; start screen (24/03/2022) .../9000115103 ; what's new in evo 11 https://www.dialux.com/en-GB/dialux/whats-new-in-dialux-evo-11
- A7 Fusion https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-THE-FUSION-INTERFACE.htm ; Onshape (15/10/2026) https://cad.onshape.com/help/Content/featuretools.htm ; SketchUp (21/10/2026) https://help.sketchup.com/en/sketchup/toolbars
- A8 Windows: layering (19/02/2026) https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/layering ; Mica (22/07/2026) https://learn.microsoft.com/en-us/windows/apps/design/style/mica ; materials (16/09/2024) https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/materials ; color (13/10/2026) https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/color ; NavigationView (02/10/2026) https://learn.microsoft.com/en-us/windows/apps/design/controls/navigationview ; command bar (13/10/2026) https://learn.microsoft.com/en-us/windows/apps/design/controls/command-bar ; TabView (21/07/2026) https://learn.microsoft.com/en-us/windows/apps/design/controls/tab-view ; Fluent 2 elevation https://fluent2.microsoft.design/elevation , color https://fluent2.microsoft.design/color , material https://fluent2.microsoft.design/material
- A9 Apple HIG (dagli endpoint JSON delle pagine): sidebars (08/06/2026) https://developer.apple.com/design/human-interface-guidelines/sidebars ; toolbars https://developer.apple.com/design/human-interface-guidelines/toolbars ; split views https://developer.apple.com/design/human-interface-guidelines/split-views ; materials https://developer.apple.com/design/human-interface-guidelines/materials ; SwiftUI inspector https://developer.apple.com/documentation/swiftui/view/inspector(ispresented:content:) ; WWDC23 10161 https://developer.apple.com/videos/play/wwdc2023/10161/ ; NSVisualEffectView.Material https://developer.apple.com/documentation/appkit/nsvisualeffectview/material
- A10 KDE HIG: layout and navigation https://develop.kde.org/hig/layout_and_nav/ ; displaying content https://develop.kde.org/hig/displaying_content/ ; Kirigami card https://develop.kde.org/docs/getting-started/kirigami/components-card/ ; pages https://develop.kde.org/docs/getting-started/kirigami/introduction-pages/
- A11 Qt 6.12: style sheets reference https://doc.qt.io/qt-6/stylesheet-reference.html ; examples https://doc.qt.io/qt-6/stylesheet-examples.html ; style sheets https://doc.qt.io/qt-6/stylesheet.html ; styling approaches https://doc.qt.io/qt-6/qtwidgets-styling-approaches.html ; QDockWidget https://doc.qt.io/qt-6/qdockwidget.html ; QMainWindow https://doc.qt.io/qt-6/qmainwindow.html ; QWidget https://doc.qt.io/qt-6/qwidget.html ; QStyle https://doc.qt.io/qt-6/qstyle.html ; QStyleFactory https://doc.qt.io/qt-6/qstylefactory.html ; Fusion https://doc.qt.io/qt-6/qtquickcontrols-fusion.html
- A12 JetBrains: tool window (17/11/2025) https://plugins.jetbrains.com/docs/intellij/tool-window.html ; toolbar (10/03/2025) https://plugins.jetbrains.com/docs/intellij/toolbar.html ; tabs (09/11/2025) https://plugins.jetbrains.com/docs/intellij/tabs.html ; icons (21/10/2024) https://plugins.jetbrains.com/docs/intellij/icons-style.html ; tool windows (17/08/2026) https://www.jetbrains.com/help/idea/tool-windows.html
- Non letti per A e B: libadwaita named-colors (404, sostituita da css-variables); fluent2 layering (404); le pagine HTML di Apple (JavaScript, letti gli endpoint JSON; nessuna pagina HIG «Inspectors»); SketchUp customizing-your-workspace (404); Onshape feature-toolbar (redirect); Qt gallery-fusion (404); JetBrains tree e list-and-tree-controls (404); DIALux evo non ha un articolo sul layout complessivo (preso dalla KB di DIALux 4); le altezze delle righe degli alberi non sono dichiarate in nessuna fonte ufficiale.

**Tema C**
- C1 GNOME HIG buttons https://developer.gnome.org/hig/patterns/controls/buttons.html ; text fields https://developer.gnome.org/hig/patterns/controls/text-fields.html ; spin buttons https://developer.gnome.org/hig/patterns/controls/spin-buttons.html ; libadwaita style classes (vedi A1); AdwPreferencesGroup https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.PreferencesGroup.html ; Adwaita `_buttons.scss`, `_colors.scss`, `_common.scss`, `_misc.scss`, `_entries.scss` da https://gitlab.gnome.org/GNOME/libadwaita/-/raw/main/src/stylesheet/widgets/ e `.../stylesheet/`
- C2 Material 3 (repository ufficiali): button https://raw.githubusercontent.com/material-components/material-web/main/docs/components/button.md ; CommonButton, TextField, Card in https://github.com/material-components/material-components-android/tree/master/docs/components
- C3 Windows: buttons (13/10/2026) https://learn.microsoft.com/en-us/windows/apps/design/controls/buttons ; Fluent 2 button usage https://fluent2.microsoft.design/components/web/react/core/button/usage ; modern button (16/04/2026) https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/controls/modern-controls/modern-control-button ; theme resources https://github.com/microsoft/microsoft-ui-xaml/blob/main/controls/dev/CommonStyles/Common_themeresources_any.xaml ; expander (26/02/2025) https://learn.microsoft.com/en-us/windows/apps/design/controls/expander ; SettingsCard (07/11/2024) https://learn.microsoft.com/en-us/dotnet/communitytoolkit/windows/settingscontrols/settingscard
- C4 Apple HIG: buttons https://developer.apple.com/design/human-interface-guidelines/buttons ; text fields https://developer.apple.com/design/human-interface-guidelines/text-fields ; boxes https://developer.apple.com/design/human-interface-guidelines/boxes ; disclosure controls https://developer.apple.com/design/human-interface-guidelines/disclosure-controls ; PrimitiveButtonStyle https://developer.apple.com/documentation/swiftui/primitivebuttonstyle
- C5 KDE HIG getting input https://develop.kde.org/hig/getting_input/ ; Kirigami FormLayout https://develop.kde.org/docs/getting-started/kirigami/components-formlayouts/
- C6 WCAG 2.2: 1.4.11 (06/09/2026) https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html ; 1.4.3 https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html ; 2.4.7 https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html ; 2.4.11 (15/06/2026) https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html ; 2.4.13 https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
- C7 Qt: QGroupBox https://doc.qt.io/qt-6/qgroupbox.html ; QPalette https://doc.qt.io/qt-6/qpalette.html ; style sheets (vedi A11)
- C8 NN/g: Flat UI elements (Moran, 03/09/2017) https://www.nngroup.com/articles/flat-ui-less-attention-cause-uncertainty/ ; flat-design best practices (12/03/2017) https://www.nngroup.com/articles/flat-design-best-practices/ ; long-term exposure (08/11/2015) https://www.nngroup.com/articles/flat-design-long-exposure/ ; button states (Gordon, 25/04/2025) https://www.nngroup.com/articles/button-states-communicate-interaction/
- Non letti per C: m3.material.io (JavaScript), fluent2 windows button (404), phabricator D12961 (500), qfusionstyle (404).

**Tema D**
- D1 matplotlib 3.11: license https://matplotlib.org/stable/project/license.html ; event handling https://matplotlib.org/stable/users/explain/figure/event_handling.html ; legend picking https://matplotlib.org/stable/gallery/event_handling/legend_picking.html ; Cursor https://matplotlib.org/stable/gallery/widgets/cursor.html ; blitting https://matplotlib.org/stable/users/explain/animations/blitting.html ; performance https://matplotlib.org/stable/users/explain/artists/performance.html ; Qt backend https://matplotlib.org/stable/api/backend_qt_api.html ; embedding in Qt https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_qt_sgskip.html ; backend_pdf https://matplotlib.org/stable/api/backend_pdf_api.html ; mplcursors 0.7.1 (18/03/2026) https://github.com/anntzer/mplcursors
- D2 pyqtgraph 0.14.0 (16/11/2025) https://github.com/pyqtgraph/pyqtgraph ; introduction https://pyqtgraph.readthedocs.io/en/latest/getting_started/introduction.html ; mouse interaction https://pyqtgraph.readthedocs.io/en/latest/user_guide/mouse_interaction.html ; PlotDataItem https://pyqtgraph.readthedocs.io/en/latest/api_reference/graphicsItems/plotdataitem.html ; config options https://pyqtgraph.readthedocs.io/en/latest/api_reference/config_options.html ; exporting https://pyqtgraph.readthedocs.io/en/latest/user_guide/exporting.html
- D3 Qt Graphs https://doc.qt.io/qt-6/qtgraphs-index.html ; Qt Charts https://doc.qt.io/qt-6/qtcharts-index.html ; QChartView https://doc.qt.io/qt-6/qchartview-qtcharts.html ; QXYSeries https://doc.qt.io/qt-6/qxyseries-qtcharts.html ; what's new 6.8 https://doc.qt.io/qt-6/whatsnew68.html e 6.12 https://doc.qt.io/qt-6/whatsnew612.html ; QuickWidgetGraphs example https://doc.qt.io/qt-6/qtgraphs-2d-quickwidgetgraphs-example.html ; migration https://doc.qt.io/qt-6/qtgraphs-migration-guide-2d.html ; QAbstractSeries https://doc.qt.io/qt-6/qabstractseries.html ; GraphsView https://doc.qt.io/qt-6/qml-qtgraphs-graphsview.html ; GraphsTheme https://doc.qt.io/qt-6/qml-qtgraphs-graphstheme.html
- D4 Qt WebEngine: overview https://doc.qt.io/qt-6.9/qtwebengine-overview.html ; licensing https://doc-snapshots.qt.io/qtwebengine/qtwebengine-licensing.html ; QWebChannel https://doc.qt.io/qt-6/qtwebchannel-javascript.html ; PySide6-WebEngine 6.12.0 su PyPI (JSON) https://pypi.org/pypi/PySide6-WebEngine/json ; Plotly.js https://github.com/plotly/plotly.js ; uPlot https://github.com/leeoniya/uPlot ; ECharts canvas vs SVG https://echarts.apache.org/handbook/en/best-practices/canvas-vs-svg/ ; QML Canvas https://doc.qt.io/qt-6/qml-qtquick-canvas.html ; Shape https://doc.qt.io/qt-6/qml-qtquick-shapes-shape.html ; QPdfWriter https://doc.qt.io/qt-6/qpdfwriter.html
- Non letti per D: pypi HTML, qtforpython QtCharts (404), observablehq (429), echarts api (JavaScript).

**Tema E**
- E1 NN/g: tooltip guidelines (Kendrick, 27/01/2019) https://www.nngroup.com/articles/tooltip-guidelines/ ; help and documentation (13/12/2020) https://www.nngroup.com/articles/help-and-documentation/ ; onboarding tutorials (12/02/2023) https://www.nngroup.com/articles/onboarding-tutorials/ ; instructional overlays (16/02/2014) https://www.nngroup.com/articles/mobile-instructional-overlay/
- E2 Microsoft: tooltips and infotips (11/03/2025) https://learn.microsoft.com/en-us/windows/win32/uxguide/ctrl-tooltips-and-infotips ; help (24/07/2025) https://learn.microsoft.com/en-us/windows/win32/uxguide/winenv-help ; WinUI tooltips (25/06/2026) https://learn.microsoft.com/en-us/windows/apps/design/controls/tooltips ; teaching tip (26/02/2025) https://learn.microsoft.com/en-us/windows/apps/design/controls/dialogs-and-flyouts/teaching-tip ; InfoBar https://learn.microsoft.com/en-us/windows/apps/design/controls/infobar
- E3 GNOME HIG tooltips https://developer.gnome.org/hig/patterns/feedback/tooltips.html ; banners https://developer.gnome.org/hig/patterns/feedback/banners.html ; keyboard https://developer.gnome.org/hig/reference/keyboard.html ; GtkApplication https://docs.gtk.org/gtk4/class.Application.html ; AdwActionRow https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ActionRow.html
- E4 Apple HIG offering help https://developer.apple.com/design/human-interface-guidelines/offering-help ; buttons (vedi C4); the menu bar https://developer.apple.com/design/human-interface-guidelines/the-menu-bar
- E5 Blender help system https://docs.blender.org/manual/en/latest/getting_started/help.html ; preferences interface (vedi A4)
- E6 JetBrains context help https://plugins.jetbrains.com/docs/intellij/context-help.html ; tooltip https://plugins.jetbrains.com/docs/intellij/tooltip.html ; inline help text https://plugins.jetbrains.com/docs/intellij/inline-help-text.html
- E7 VS Code contribution points https://code.visualstudio.com/api/references/contribution-points ; settings https://code.visualstudio.com/docs/configure/settings ; walkthroughs https://code.visualstudio.com/api/ux-guidelines/walkthroughs
- E8 PVsyst help https://www.pvsyst.com/help/ ; tips for beginners https://www.pvsyst.com/help/getting-started/tips-for-beginners.html ; Revit 2024 tooltips https://help.autodesk.com/cloudhelp/2024/ENU/Revit-GetStarted/files/GUID-0EA7DC65-4E4C-4321-9F38-A8E4C0AFFA23.htm ; AutoCAD 2019 extended tooltips https://help.autodesk.com/cloudhelp/2019/ENU/AutoCAD-LT/files/GUID-0DBFCEE4-2C57-4711-849D-9BE271495CA1.htm ; DIALux evo menu bar (vedi A6)
- E9 KDE fundamentals https://docs.kde.org/stable_kf6/en/khelpcenter/fundamentals/menus.html ; KDE HIG status changes https://develop.kde.org/hig/status_changes/ ; QWhatsThis https://doc.qt.io/qt-6/qwhatsthis.html ; QToolTip https://doc.qt.io/qt-6/qtooltip.html ; QStyleHints https://doc.qt.io/qt-6/qstylehints.html ; Qt Help https://doc.qt.io/qt-6/qthelp-framework.html
- Non letti per E: i centri di assistenza su Zendesk (403), projectmallard (503).

**Tema F**
- F1 VS Code editing evolved https://code.visualstudio.com/docs/editing/editingevolved ; release notes 1.41 https://code.visualstudio.com/updates/v1_41 , 1.23 https://code.visualstudio.com/updates/v1_23 , 1.68 https://code.visualstudio.com/updates/v1_68 ; JetBrains problems tool window (17/08/2026) https://www.jetbrains.com/help/idea/problems-tool-window.html
- F2 Revit: messages you can ignore (2020) https://help.autodesk.com/cloudhelp/2020/ENU/Revit-Troubleshooting/files/GUID-63125823-1B92-4DAF-9AC4-71B7D638FD10.htm ; review warnings (2020) GUID-F0945713 ; gathering warnings (2022) GUID-C3ACD5C4 ; delete checked (2014) GUID-4CB045A4 ; warnings for selected elements (2014) GUID-42294460 (stessa base dell'URL, anno nel percorso)
- F3 PVsyst tutorial https://www.pvsyst.com/help/project-design/grid-connected-system-definition/project-design-tutorial.html ; Aurora blog (10/2021) https://aurorasolar.com/blog/top-10-things-you-didnt-know-aurora-can-do-10-code-and-setback-requirements/ ; OpenSolar 2.31.0 https://www.opensolar.com/product-updates/release-2-31-0/
- F4 Solibri severity https://www.solibri.com/learn/understanding-the-severity-levels-of-checking-results ; Navisworks Clash Detective 2022 https://help.autodesk.com/cloudhelp/2022/ENU/Navisworks/files/GUID-FCC9E5E1-2717-48D2-8DBE-2055CF2DC61E.htm ; Office accessibility checker https://support.microsoft.com/en-us/office/improve-accessibility-with-the-accessibility-checker-a16f6de0-2f39-4a2b-8bd8-5ad801426c7f e rules https://support.microsoft.com/en-us/office/rules-for-the-accessibility-checker-651e08f2-0fc3-4e10-aaca-74b4a67101c1
- F5 NN/g error-message guidelines (14/05/2023) https://www.nngroup.com/articles/error-message-guidelines/ ; JetBrains validation errors https://plugins.jetbrains.com/docs/intellij/validation-errors.html ; Microsoft error messages (24/07/2025) https://learn.microsoft.com/en-us/windows/win32/uxguide/mess-error
- Non letti per F: help.solibri.com (403), Revit 2024 About Warnings (403), HelioScope e Aurora help (403, solo le anteprime).

**Tema G**
- G1 Microsoft Agent states (31/05/2018, ritirato) https://learn.microsoft.com/en-us/windows/win32/lwef/agent-states ; Genie animations https://learn.microsoft.com/en-us/windows/win32/lwef/microsoft-agent-animations-for-genie-character
- G2 Duolingo (10/11/2022) https://blog.duolingo.com/world-character-visemes/ ; Rive su Lily (20/03/2025) https://rive.app/blog/duolingo-s-ai-powered-video-call-brings-lily-to-life ; Rive state machine https://rive.app/docs/editor/state-machine/state-machine ; runtimes https://rive.app/docs/runtimes/getting-started ; rive-cpp https://github.com/rive-app/rive-cpp
- G3 Material 3 motion https://github.com/material-components/material-components-android/blob/master/docs/theming/Motion.md ; Fluent timing (18/09/2024) https://learn.microsoft.com/en-us/windows/apps/design/motion/timing-and-easing ; Windows motion (24/07/2024) https://learn.microsoft.com/en-us/windows/apps/design/signature-experiences/motion ; Fluent 2 motion https://fluent2.microsoft.design/motion ; Apple HIG motion https://developer.apple.com/design/human-interface-guidelines/motion e accessibility https://developer.apple.com/design/human-interface-guidelines/accessibility
- G4 GNOME, GTK: AdwTimedAnimation https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.TimedAnimation.html ; gtk-enable-animations https://docs.gtk.org/gtk4/property.Settings.gtk-enable-animations.html ; GTK MR 9077 (27/10/2025) https://gitlab.gnome.org/GNOME/gtk/-/merge_requests/9077 ; gnome-control-center MR 3253 (06/11/2025) https://gitlab.gnome.org/GNOME/gnome-control-center/-/merge_requests/3253 ; portale Settings https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Settings.html ; WCAG 2.3.3 https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html
- G5 NN/g: animation for attention and comprehension (Harley, 21/09/2014) https://www.nngroup.com/articles/animation-usability/ ; the role of animation and motion in UX (Laubheimer, 12/01/2020) https://www.nngroup.com/articles/animation-purpose-ux/
- G6 le chat: GitHub Copilot https://docs.github.com/en/copilot/how-tos/copilot-on-github/chat-with-copilot/chat-in-github ; VS Code Copilot chat (21/10/2026) https://code.visualstudio.com/docs/copilot/chat/copilot-chat ; Material chips https://github.com/material-components/material-components-android/blob/master/docs/components/Chip.md ; Bot Framework suggested actions (09/10/2024) https://learn.microsoft.com/en-us/azure/bot-service/bot-builder-howto-add-suggested-actions ; Copilot Studio starter prompts (01/09/2026) https://learn.microsoft.com/en-us/microsoft-copilot-studio/configure-starter-prompts
- G7 Qt: QSizeGrip https://doc.qt.io/qt-6/qsizegrip.html ; QRubberBand https://doc.qt.io/qt-6/qrubberband.html ; animation framework https://doc.qt.io/qt-6/animation-overview.html ; QPropertyAnimation https://doc.qt.io/qt-6/qpropertyanimation.html ; QVariantAnimation https://doc.qt.io/qt-6/qvariantanimation.html ; QEasingCurve https://doc.qt.io/qt-6/qeasingcurve.html ; QGraphicsEffect https://doc.qt.io/qt-6/qgraphicseffect.html ; QWidget windowOpacity https://doc.qt.io/qt-6/qwidget.html#windowOpacity-prop ; QPainter https://doc.qt.io/qt-6/qpainter.html ; QSvgRenderer https://doc.qt.io/qt-6/qsvgrenderer.html ; QQuickWidget https://doc.qt.io/qt-6/qquickwidget.html ; Animator https://doc.qt.io/qt-6/qml-qtquick-animator.html ; Qt Lottie https://doc.qt.io/qt-6/qtlottieanimation-index.html ; VectorImage https://doc.qt.io/qt-6/qml-qtquick-vectorimage-vectorimage.html
- Non letti per G: m3.material.io (JavaScript), help.openai.com (403), Dehn e van Mulken 2000 (403), le pagine HTML di GitLab (usata l'API).
