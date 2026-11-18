# Meridiana: studio estetico

Studio del 22/10/2026. **[V]** = verificato (letto nella fonte, misurato o provato sul programma vero). **[I]** = dedotto.

**Che cosa chiede Daniel.** Variazioni estetiche del programma, minimali come DIALux evo ma con un tocco di personalità; tema chiaro e scuro, dal sistema o scelto; qualche somiglianza con GNOME, con Niri e con il suo Lucciola; la prova che in Qt le personalizzazioni non diano problemi; un posto discreto per l'assistente, di cui il nome e il disegno restano da decidere.

**Artefatto.** https://claude.ai/artifact/HGTStmiCgyT1pTqC53jARn (privato finché Daniel non lo condivide). È una tela con undici tavole:
- **Panoramica**: le quattro direzioni con i colori, i font, le icone e la raccomandazione;
- **Confronto interattivo**: la finestra con il selettore della direzione;
- **Verifica in Qt**: le schermate vere del programma e le misure;
- otto finestre, Modello e Producibilità per ogni direzione.

Ogni finestra ha in alto a destra il tema Sistema, Chiaro o Scuro. Le schede Modello e Producibilità funzionano; i pannelli si chiudono e si riaprono; il pulsante Assistente è nella barra di stato. Nel bozzetto le scorciatoie (Ctrl+B, Ctrl+1) sono scritte, non attive.

## 1. In breve

- **Direzione raccomandata: Meridiana.** Calce e bronzo di giorno, notte e sole pallido di sera, Titillium Web, la disposizione di DIALux evo, raggi e spazi di libadwaita. In scuro sta accanto a Lucciola. Motivi al paragrafo 9.
- **In Qt si fa, con quattro condizioni [V]:**
  - Fusion anche su Windows. Lo stile windows11 con una palette propria rende illeggibili menu e caselle a discesa.
  - Due palette complete, non parziali.
  - Un solo foglio di stile, globale, messo prima della finestra. I fogli locali rompono il cambio di palette.
  - Un oggetto Tema che dà i colori anche alla pianta, al 3D e ai grafici.
- **Difetti di oggi, trovati con le prove [V]:**
  - su Niri la scelta «Chiaro» o «Scuro» delle impostazioni non fa nulla, perché `setColorScheme()` non agisce con il tema del portale;
  - se il sistema cambia tema a programma aperto, la palette di Qt non segue;
  - la selezione nella pianta (#ffb000) e il colore di avviso (#fab219) sono lo stesso giallo: distanza OKLab 0,9.
- **Palette dei grafici: resta com'è.** È validata per i daltonici e l'ho rivalidata sulle superfici di ogni direzione [V]. Stati e grafici hanno gli stessi colori in tutte le direzioni.

## 2. Da dove sono partito

**Il programma oggi [V]** (schermate della revisione UX e codice in `src/meridiana/ui`):
- su Windows lo stile windows11 in scuro: barra dei menu, barra strumenti solo testo, schede, pannelli Progetto e Proprietà;
- la pianta ha il fondo scuro fisso (`#2b2f33` in `plan.py`) in ogni tema. I colori sono scritti nel codice:
  - edifici `#f2efe6`;
  - sottocampo `#5ab0ff`;
  - esclusioni `#ff5a4f`;
  - moduli `rgba(25,45,90)`;
  - selezione e disegno `#ffb000`;
  - guide `#7fd4ff`;
- il 3D ha cielo `#cfe0ec` e suolo `#9fae93` fissi in `Scene.qml`, e i colori degli edifici in `mesh.py`;
- i grafici (`charts.py`) usano la palette validata in chiaro e in scuro e scelgono il modo dalla luminosità della palette;
- le verifiche (`checks_page.py`) usano i colori di stato della stessa palette;
- `app.py` imposta il tema del portale su Niri e chiama `styleHints().setColorScheme()` per «chiaro» e «scuro».

**Lucciola, il portatile [V]** (`/etc/os-release`, gsettings, `~/.config/niri`, `~/.config/noctalia`, `~/.config/gtk-4.0`, `/usr/share/lucciola`; solo lettura, nessuna schermata):
- **Sistema:** Lucciola 45 (variante «margine», base Fedora 45).
- **Impostazioni GNOME:**
  - `prefer-dark`;
  - accento `yellow`;
  - font `Adwaita Sans 11`, monospazio `Adwaita Mono 11`;
  - icone Adwaita;
  - `adw-gtk3-dark`.
- **Palette «Margine» di Noctalia** (`/usr/share/lucciola/noctalia/palettes/Margine.json`), solo scura:

  | Ruolo | Colore |
  |---|---|
  | primario | #e6d5bf (beige) |
  | secondario | #c2a180 (sabbia) |
  | terziario | #cba6f7 (lavanda) |
  | errore | #ff938c |
  | superficie | #121212 |
  | superficie variante | #1f1f1f |
  | testo | #ece6df |
  | testo attenuato | #b8b2ab |
  | contorno | #3a3a40 |
  | sotto il puntatore | #2e2e32 |

  La guida di Lucciola aggiunge `--raised #1a1a1a` e `--line #2a2a2e`.
- **Niri** (`/usr/share/lucciola/niri/config.kdl` e `~/.config/niri/lucciola-colors.kdl`):
  - gap 6;
  - anello di fuoco spento;
  - bordo di 3 px, `#e6d5bf` sulla finestra attiva e `#121212` sulle altre;
  - ombra (softness 24, spread 4, offset 0,4, `#1a1a1ab8`);
  - angoli delle finestre arrotondati di 15 px, «matching libadwaita's own window radius».
- **Barra di Noctalia** (`20-margine-style.toml`, `22-panels-and-dock.toml`):
  - in alto, alta 36 px, raggio 12;
  - contorno di 2 px nel colore primario;
  - JetBrains Mono peso 500, padding 16, spazio tra i widget 14.
- **Colori per Qt.** Le app Qt prendono i colori di Noctalia da `~/.config/kdeglobals`, attraverso il tema KDE. Meridiana usa invece il tema del portale, quindi su Lucciola non li vede [V configurazione; I effetto].

**Riferimenti esterni** (fonti al paragrafo 12):
- **DIALux evo 14** (aprile 2026) [V]:
  - le modalità sono schede in alto con icona colorata e testo: Project, Construction, Light, Calculation objects, Export, Documentation;
  - sopra la vista CAD c'è il percorso Site > Building > Storey > Room;
  - a sinistra una colonna di icone con il pannello dello strumento a sezioni;
  - a destra il «Results overview» con un semaforo sui valori obiettivo;
  - in basso la barra di stato con oggetti e notifiche;
  - la pianta 2D è bianca con i righelli.
  - **Correzione al brief:** l'interfaccia di DIALux non è chiara ma antracite (evo 13) o grigio medio (evo 14), e il colore di fondo non si cambia [V]. «Studio» ne prende la struttura, non il grigio scuro.
- **libadwaita 1.10 e GNOME HIG** [V]:
  - superfici: chiaro finestra `#fafafb`, vista `#ffffff`, barra `#ffffff`, barra laterale `#ebebed`; scuro `#222226`, `#1d1d20`, `#2e2e32`, `#2e2e32`;
  - accenti di sistema: blu `#3584e4` di base, giallo `#c88800`, ecc.;
  - raggi: 9 px i pulsanti, 12 le schede, 15 finestre e popover;
  - font Adwaita Sans e Adwaita Mono, SIL OFL 1.1, da GNOME 48;
  - cifre tabellari con la classe `numeric`;
  - barra in alto alta almeno 47 px;
  - pannelli di servizio a sinistra se agiscono sulla vista principale.
- **Niri v26.04, valori di base** [V]:
  - gap 16;
  - anello di fuoco di 4 px, `#7fc8ff` attivo e `#505050` inattivo;
  - bordo spento;
  - finestre non arrotondate; nel file di esempio c'è `geometry-corner-radius 12`.

## 3. Regole uguali in tutte le direzioni

1. **Stati: i colori della palette dei grafici, fissi.**

   | Stato | Colore |
   |---|---|
   | da correggere | #d03b3b |
   | da controllare | #fab219 |
   | grave | #ec835a |
   | superata | #0ca30c |
   | da sapere | colore del testo |

   - Ogni stato va sempre con icona e parola. In chiaro il giallo d'avviso ha contrasto 1,8:1 e l'icona da sola non basta: nei riquadri l'icona è un ocra più scuro (#b07a00) [V calcolo].
   - **Sulla pianta e nel 3D** le criticità diventano un segno sull'oggetto: triangolo e percentuale. Nella barra di stato c'è il contatore («2 da controllare», cliccabile), e la scheda Verifiche ha il numero.
2. **Grafici: `SERIES`, `SEQUENTIAL` e la coppia divergente non cambiano.**
   - Ho ripassato il validatore su ogni superficie, in chiaro su #ffffff e #fbfaf9, in scuro su #1d1f22, #1d1d20, #161616 e #101318 [V]. In scuro passa ogni controllo.
   - In chiaro acqua, giallo e magenta restano sotto 3:1, come già oggi. Li compensano le etichette e la tabella, che il programma ha.
   - Cambiano solo la superficie, la griglia, gli assi e il font, che vengono dalla direzione.
3. **Selezione diversa dall'avviso.**
   - Ogni direzione seleziona nel suo colore, con un alone a due toni: una linea scura larga sotto una chiara stretta in scuro, e il contrario in chiaro.
   - Sull'ortofoto il beige pallido di Lucciola da solo si perde sui tetti chiari [V schermata]. Con l'alone si legge su foto, moduli blu e fondo pieno [I].
   - L'accento di sistema non va mai usato per la selezione nella pianta: su Lucciola l'accento è giallo, e nel tema scuro di GNOME diventa `#ffc057`, a 4,3 dall'avviso [V calcolo].
4. **Icone: Lucide (ISC)**, griglia 24 e tratto arrotondato come i simbolici GNOME, oltre 1.600 icone, SVG semplici.
   - Il tratto cambia con la direzione: 1,5 / 2 / 1,75 / 1,5.
   - Tabler (MIT) è la riserva per i simboli tecnici; Phosphor (MIT) e Material Symbols (Apache 2.0) sono confrontati nella Panoramica.
   - Tutte e quattro le licenze sono compatibili con la GPL-3.0 [I].
5. **Barra strumenti con icona e testo**, scheda dei risultati senza i pannelli del modello, stato del calcolo nella barra di stato senza bloccare.
   - Freccia del nord e barra di scala in pianta; cubo di vista con N, E, S, O nel 3D.
   - Pannelli che si riaprono dalla barra e con Ctrl+B e Ctrl+1. È la direzione della revisione UX, già nei bozzetti.
6. **Assistente** (decisioni del 22/10/2026 sera, studio 14 sezione 7.3).
   - Un personaggio che fluttua sopra le viste: con un clic si apre la chat per chiedere un parere.
   - La chat resta la stessa in tutte le schede e si sposta dove non copre il lavoro.
   - Nella barra di stato c'è il personaggio piccolo con il nome, come l'icona di Copilot in VS Code.
   - Il colore è un ruolo a parte, non l'accento: lavanda in Lucciola; in Meridiana la tinta opposta al colore scelto (sezione 12), che con il bronzo è il blu ardesia.
   - Nome e disegno li sceglie Daniel: tre proposte sulla tela (Gnomone, Meridio, Lucciola).
7. **La pianta e il 3D hanno colori propri, uguali nei due temi** (Daniel, 23/10/2026: «per tema intendevo sull'interfaccia e al massimo in bottoni che ci sono in modellazione»; col tema il 3D «sembra sempre notte» e le linee arancioni non si vedono).
   - Il tema vale per finestre, pannelli, campi, pulsanti, barre e i pulsanti sopra le viste (cubo, assistente). Pianta e 3D prendono i colori da `view_colours.py`, quelli di prima della fase 2 (commit `9cc8314`): falde arancioni, cielo di giorno.
   - L'ortofoto è sempre velata di nero (40% predefinito, Vista › Sfondo › Scurisci lo sfondo) e i tratti sono chiari e saturi sopra un alone scuro: si leggono sui tetti chiari e su quelli scuri [V calcolo, `test_view_colours.py`]. Senza ortofoto il fondo è chiaro (#f3f1ec), con tratti scuri e alone chiaro.
   - La selezione è magenta (#ff38c8), lontana dal giallo degli avvisi, dal rosso degli errori e dal blu dei sottocampi; quello sotto il cursore è lo stesso magenta più chiaro. Nel 3D l'oggetto selezionato si tinge e ha il contorno marcato, come in FreeCAD (studio 15, 3.3).

## 4. Studio, alla DIALux evo

**Idea.** Grigi tecnici e molto spazio al disegno: le fasi in alto come schede con icona e testo, la pianta bianca, un blu preciso per selezione e fuoco.
- **Font:** IBM Plex Sans e IBM Plex Mono (OFL), 10 pt; le cifre sono già tabellari [V].
- **Raggi e spazi:** raggi 4 e 6 px; spazi 4, 8, 12.
- **Bordi:** pannelli separati da linee, non da spazi.

| Ruolo | Chiaro | Scuro |
|---|---|---|
| finestra / pannelli / vista | #ebedf0 / #f5f6f8 / #ffffff | #2b2d31 / #25272b / #1d1f22 |
| barra delle fasi | #dfe2e6 | #383b40 |
| linee / linee leggere | #cdd2d8 / #e3e6ea | #3d4046 / #32353a |
| testo / secondario / attenuato | #1b1e23 / #454b54 / #666c76 | #e8eaed / #b8bcc3 / #8e939b |
| accento / su accento | #1f6fd1 / #ffffff | #4c9bff / #0b1424 |
| selezione nelle liste | #d6e5f8 su #10233d | #24405f su #e8f1ff |
| pianta: fondo / edifici / moduli | #ffffff / #2c3138 / #1e3a66 | #1d1f22 / #c9cdd3 / #223c66 |
| pianta: selezione / alone / guide | #1f6fd1 / #ffffff / #c026d3 | #7ab8ff / #0b0c0e / #e879f9 |
| 3D: cielo / suolo / falde | #e8ecf0 su #f8f9fa / #d5d9d0 / #b0a89c | #34373c su #45494f / #3a3f3a / #8c847a |

- **Pro:** neutra, si legge bene, fa poca fatica su Windows.
- **Contro:** poca personalità; con l'antracite di DIALux in scuro non ha legami con Lucciola.

## 5. Adwaita, come un'app GNOME

**Idea.** Le superfici, i raggi e la tipografia di libadwaita.
- **Barra in alto alla GNOME:** schede al centro, pannelli, annulla e ripeti a sinistra, tema e menu principale a destra.
- **Accento:** quello del sistema; nel bozzetto il blu di base.
- **Font:** Adwaita Sans (OFL, derivata da Inter) e Adwaita Mono; cifre in colonna con `tnum`.
- **Raggi e spazi:** raggi 9, 12, 15; spazi 6, 12, 18, 24.

| Ruolo | Chiaro | Scuro |
|---|---|---|
| finestra / barra laterale / vista / barra | #fafafb / #ebebed / #ffffff / #ffffff | #222226 / #2e2e32 / #1d1d20 / #2e2e32 |
| linee | #dcdcdf | #434347 |
| testo / secondario / attenuato | #323236 / #5e5e64 / #67676c | #ffffff / #c0c0c4 / #9a9a9c |
| accento (fondo) / accento (linee e testo) | #3584e4 / #0461be | #3584e4 / #81d0ff |
| pianta: fondo / selezione / guide | #ffffff / #0461be / #9141ac | #1d1d20 / #81d0ff / #dc8add |
| 3D: cielo / suolo / falde | #cfe1f5 su #f1f6fb / #cdd8c6 / #b5835a | #2a3442 su #3b4656 / #2f352e / #986a44 |

- **Pro:** è il più vicino a GNOME e sta bene su Niri.
- **Contro:**
  - su Windows sembra un ospite;
  - la barra senza menu va rifatta in Qt: un pulsante con il menu e i comandi visibili;
  - Qt su Linux non legge l'accento del sistema [V], va chiesto al portale a mano;
  - l'accento giallo di Lucciola si confonderebbe con gli avvisi.

## 6. Lucciola, i toni del portatile

**Idea.** Il quasi nero di Noctalia e il beige del bordo di Niri.
- **Pannello attivo:** la pianta ha il bordo beige di 2 px, come la finestra a fuoco in Niri.
- **Barra strumenti:** una barra sospesa con raggio 12 e contorno beige, come quella di Noctalia; le etichette e la barra di stato in JetBrains Mono.
- **Spazi tra i pannelli:** 6 px, i gap di Lucciola.
- **Assistente:** in lavanda.
- **Cielo del 3D:** al crepuscolo, come lo sfondo di Lucciola.
- **Tema chiaro:** non esiste in Lucciola; l'ho derivato tenendo il beige come fondo della selezione.

| Ruolo | Chiaro (derivato) | Scuro |
|---|---|---|
| finestra / pannelli / vista / schede | #f4f3f1 / #fbfaf9 / #ffffff / #ffffff | #121212 / #1a1a1a / #161616 / #1f1f1f |
| linee | #dedad5 | #2a2a2e |
| testo / secondario / attenuato | #121212 / #4a4540 / #6e675f | #ece6df / #b8b2ab / #8c8579 |
| accento / su accento | #8a6a45 / #ffffff | #e6d5bf / #121212 |
| selezione nelle liste | #e6d5bf su #121212 | #e6d5bf su #121212 |
| assistente | #7c4dcc | #cba6f7 |
| pianta: fondo / moduli / bordo moduli | #fbfaf9 / #1c2a44 / #9fb2d4 | #161616 / #1c2a44 / #8fa9d6 |
| pianta: selezione / esclusioni / guide | #8a6a45 / #6e675f / #7c4dcc | #e6d5bf / #c2a180 / #cba6f7 |
| 3D: cielo / suolo / falde | #e9e6ef su #f7f3ee / #d9d6cc / #b57a5c | #17151c su #2f2733 / #1d211d / #a0705a |

- **Pro:** è la più vicina a ciò che Daniel ha scelto per sé; in scuro è bellissima.
- **Contro:**
  - è personale, e su Windows, per i colleghi, è un tema scuro e basta;
  - il chiaro è un'aggiunta, non nasce da Lucciola;
  - il beige da solo si perde sull'ortofoto [V].

## 7. Meridiana, l'accento caldo (raccomandata)

**Idea.** Le meridiane dipinte sui muri: la calce, il bronzo dello gnomone, la linea del mezzogiorno; di sera, la notte e un sole pallido.
- **Tocchi di personalità:**
  - un punto dell'accento davanti alla scheda attiva, il sole sulla linea;
  - «XII» accanto all'ora della barra del sole, la linea del mezzogiorno;
  - coppi in terracotta nel 3D;
  - cifre sempre in colonna.
- **Font:** Titillium Web (OFL), nata all'Accademia di Belle Arti di Urbino.
  - Ha le cifre tabellari di serie e lo zero senza barra [V].
  - Ho scartato Atkinson Hyperlegible: lo zero barrato non ha alternativa e in un programma elettrico si confonde con Ø [V].
- **Raggi e spazi:** raggi 4 e 8 px; spazi 4, 8, 16.

| Ruolo | Chiaro | Scuro |
|---|---|---|
| finestra / pannelli / vista | #f2f1ed / #f8f7f4 / #ffffff | #14181e / #1a1f26 / #101318 |
| linee / leggere | #d9d5cc / #e8e5de | #2b323c / #20262e |
| testo / secondario / attenuato | #1e1c19 / #514c44 / #6f685d | #ece8e1 / #c0b9ad / #918a7e |
| accento / su accento | #8b5a12 (bronzo) / #ffffff | #f2dca4 (sole pallido) / #14181e |
| selezione nelle liste | #f1e4cc su #1e1c19 | #3a3428 su #f6efe0 |
| assistente | #2e4a6b | #9ec1e8 |
| pianta: fondo / edifici / moduli | #fbfaf8 / #3a352d / #1f3352 | #101318 / #d8d2c6 / #1d3152 |
| pianta: selezione / alone / guide | #8b5a12 / #ffffff / #2e6fb0 | #f2dca4 / #0b0d10 / #8ab4f8 |
| 3D: cielo / suolo / pareti / falde | #dde7f0 su #f6f2ea / #d6d0bf / #f0ebe1 / #b5643f | #0f141c su #1f2a3a / #23272a / #d6d0c4 / #9a5a3e |

**Contrasti verificati [V]:**
- bronzo su bianco 5,9:1, testo bianco sul bronzo 5,9:1;
- sole pallido su #101318 13,8:1;
- testo attenuato 5,1:1 in chiaro e 4,8:1 in scuro.

**Distanza dal giallo d'avviso [V]:** il bronzo è a 30,8, il sole pallido a 12,7. Qui il segno d'avviso porta sempre il triangolo.

- **Pro:** ha un carattere suo senza essere rumorosa; italiana come chi la usa; in scuro è parente di Lucciola; funziona uguale su Windows e su Linux.
- **Contro:**
  - lo scuro è vicino a Lucciola;
  - Titillium Web non l'ho ancora provata a 100% su Windows [I];
  - il sole pallido in scuro sta a 12,7 dal giallo d'avviso: si regge sulla forma del segno.

## 8. Verifica in Qt

**Come.** Sul portatile (Lucciola, Niri, Wayland, PySide6 6.12) uno script fuori dal repository, in `~/fvtest/estetica`:
- apre la vera `MainWindow` del ramo di lavoro (`~/fvtest/meridiana-ux`) con `sample.meridiana`, in una cartella temporanea per le impostazioni;
- applica Fusion, la palette, il foglio di stile, i font dai file e le icone ricolorate;
- ricolora pianta, 3D e grafici sostituendo a runtime i nomi `QColor` di `plan.py` e le costanti di `mesh.py`, con una copia di `Scene.qml` dotata di cielo a gradiente e cubo di vista;
- salva le schermate con `win.grab()` per le quattro direzioni, in chiaro e in scuro.

Per il cambio di tema dal sistema ho usato un portale finto (`/usr/bin/python3` con Gio) su un bus D-Bus privato (`dbus-run-session`): le impostazioni di Daniel non sono state toccate. Su Windows c'è stato un solo giro con la finestra, 67 secondi sul secondo schermo, con windows11 e con Fusion. Prima c'erano stati solo brevi script senza finestre: le prove sulla palette fatte durante la ricerca e il disegno di controllo della geometria dei bozzetti.

| Prova | Esito | |
|---|---|---|
| Palette completa su Fusion | Ogni widget la segue, in chiaro e in scuro, su Linux e su Windows | [V] |
| Stile windows11 con palette propria | Con il sistema scuro e la palette chiara, il testo del menu e delle caselle a discesa resta bianco: illeggibile. Il pulsante attivo prende l'accento di Windows | [V] |
| `setColorScheme(Light/Dark)` con il tema del portale (Niri) | Nessun effetto, nessun segnale. La scelta del tema nelle impostazioni di oggi su Niri non funziona | [V] |
| `setColorScheme` su Windows | Funziona; `colorSchemeChanged` arriva quando la palette è ancora quella vecchia | [V] |
| Il sistema passa a chiaro con l'app aperta (portale finto) | `colorSchemeChanged(Light)` arriva, ma la palette di Qt resta scura (`#323232`). Con le nostre palette scelte su quel segnale cambia tutto, nei due versi | [V] |
| Accento del portale (giallo) | Ignorato: `QPalette.Accent` resta `#308cc6` | [V] |
| Cambio di tema con la sola palette | Da meno di 1 ms a 0,2 s con il ridisegno (portatile); da 0,3 a 25 ms su Windows | [V] |
| Foglio di stile globale rimesso al cambio di tema | Da 0,42 a 0,89 s (portatile), da 0,36 a 0,45 s (Windows), con circa 1.000 widget | [V] |
| Apertura della finestra con il foglio globale | 0,24-0,29 s contro 0,09-0,20 s (portatile); 0,55 s contro 0,09 s su Windows (una misura) | [V] |
| Fogli locali su barra strumenti, schede, barra di stato | 3-20 ms, ma dopo il cambio di palette la barra del sole (e in una prova anche il suggerimento della barra di stato) resta con il testo del tema di prima | [V] |
| Font dai file con `QFontDatabase.addApplicationFont` | IBM Plex, Adwaita, Atkinson e Titillium caricati in 0,2-14 ms, anche variabili; su Windows IBM Plex Sans compare anche con i nomi delle istanze: il nome va letto da `applicationFontFamilies()` | [V] |
| Cifre tabellari con `QFont.setFeature("tnum")` | Adwaita Sans: «1111» passa da 24,4 a 38,9 px, come «0000» | [V] |
| Icone SVG ricolorate | Un `QIconEngine` di circa 40 righe disegna l'SVG nel colore della palette al momento; le icone seguono il cambio di tema | [V] |
| Menu, caselle a discesa, suggerimenti su Wayland | Menu e caselle aperti da programma non compaiono («Failed to create grabbing popup... parent window has received input»): su Wayland serve un clic vero. I suggerimenti sì. Il menu disegnato segue la palette | [V] |
| Pannelli flottanti su Niri | I pannelli di Meridiana non sono flottanti (`DockWidgetFloatable` assente) e conviene che restino così: niri non ha `xdg-toplevel-drag` | [V codice, I effetto] |
| Vista 3D | Gradiente del cielo, materiali e cubo cambiano a caldo da Python. Un valore messo da Python su una proprietà legata nel QML torna indietro al primo aggiornamento (il suolo è tornato verde): il tema va dato al QML come proprietà a cui legarsi. I testi dentro il View3D non si trovano con `findChild` | [V] |
| Cubo di vista con N, E, S, O | Un secondo `View3D` in un angolo, con la camera legata a quella principale: circa 60 righe di QML, funziona | [V] |
| Grafici matplotlib | Superficie, griglia e font della direzione (registrato con `font_manager.addfont`) presi a ogni disegno | [V] |

**Che cosa ho messo sul portatile** (solo in `~/fvtest/estetica`, nessun pacchetto installato):
- gli script `tema.py`, `prova_estetica.py`, `prova_portale.py`, `mock_portal.py`, `prova_niri.py`, `run_laptop.sh`;
- la copia `scena_tema.qml` e `tokens.json`;
- 12 file di font: IBM Plex, Adwaita, Atkinson, Titillium Web, tutti OFL;
- 56 icone Lucide;
- la cartella `out/` con schermate e rapporti.

**Una nota sulle finestre di prova su Niri.** Le finestre nuove non prendono il fuoco. `set-window-width --id` non cambia la colonna, `toggle-window-floating --id` più un `resize` sì. In una prima versione avevo usato `maximize-column`, che agisce sulla finestra a fuoco. Dopo ho controllato: nessuna finestra era a fuoco e le colonne di Daniel risultano a mezza larghezza, tranne VS Code «dev» a tutta larghezza; se non l'aveva lasciata così, va rimessa com'era.

## 9. Raccomandazione

**Meridiana.** Rispetto a Studio ha personalità senza perdere la sobrietà; rispetto ad Adwaita funziona uguale su Windows; rispetto a Lucciola non è un tema personale ma l'identità del programma, e in scuro le assomiglia. Prende da DIALux evo la struttura, da libadwaita le metriche, da Lucciola il bordo del pannello attivo, se Daniel lo vuole.

**Come farla in Qt, a passi** (stima per chi conosce il codice):

1. **Modulo `ui/theme.py`** (0,5-1 giorno):
   - un oggetto Tema con i colori chiari e scuri di Meridiana (tabelle sopra), la palette completa (tutti i ruoli, gruppi Active, Inactive e Disabled, `Accent` compreso) e il foglio di stile globale;
   - i colori non sono più due tabelle fisse: il Tema li calcola dal colore scelto e dai fondi (sezione 12);
   - Fusion anche su Windows;
   - prove: ogni ruolo è impostato, i contrasti tengono.
2. **Chiaro e scuro** (0,5 giorno):
   - al posto di `apply_theme()` con `setColorScheme`, la scelta della palette;
   - «Sistema» segue `colorSchemeChanged`, anche dal portale su Niri; «Chiaro» e «Scuro» mettono la palette;
   - su Windows anche `setColorScheme`, per la barra del titolo.
3. **Font** (0,5 giorno):
   - Titillium Web in `data/fonts` con la licenza OFL, caricata all'avvio da file;
   - il nome letto da `applicationFontFamilies()`;
   - il font registrato anche in matplotlib;
   - incluso nell'installer e nel Flatpak.
4. **Icone** (0,5 giorno): una cartella con le Lucide usate e la licenza ISC, il motore di icone ricolorate, barra con icona e testo.
5. **Pianta** (1 giorno):
   - i colori di `plan.py` presi dal Tema;
   - selezione con alone a due toni, distinta dall'avviso;
   - segni delle criticità sugli oggetti;
   - freccia del nord e barra di scala;
   - fondo chiaro in tema chiaro quando non c'è l'ortofoto.
6. **3D** (1 giorno):
   - il `Backend` espone i colori del Tema (cielo, suolo, cubo) e `Scene.qml` vi si lega;
   - cielo a gradiente dietro un `View3D` trasparente;
   - i colori di `mesh.py` dal Tema;
   - cubo di vista.
7. **Grafici e verifiche** (0,5 giorno): `CHROME` dal Tema e nuovo disegno al cambio; colori di stato invariati.
8. **Foglio di stile** (0,5 giorno):
   - poche regole globali (schede, barra strumenti, titoli dei pannelli, barra di stato) con colori espliciti;
   - rimesso una volta al cambio di tema, sapendo che costa 0,4-0,9 s;
   - se pesa, il passo dopo è uno stile proxy su Fusion al posto del foglio.
9. **Prove** (0,5 giorno): schermate chiaro e scuro su Windows e su Linux, contrasti, e un test che non torni lo stile windows11.

In tutto circa 5-6 giorni. Le direzioni scartate restano possibili come temi alternativi solo a fine lavoro: il costo vero è il Tema, non i colori.

## 10. Rischi

- **Rinunciare a windows11.** Su Windows Meridiana non avrà più i controlli di Windows 11 [I]. Qt stessa indica Fusion per le palette proprie [V].
- **Foglio di stile.**
  - Costa all'apertura e a ogni cambio di tema [V].
  - Mischiato con `setPalette` su singoli widget dà colori vecchi [V].
  - Un font messo nel foglio vince su `setFont` e fa perdere `tnum` [I, dalla documentazione].
  - Regola: un foglio globale senza font, o nessun foglio.
- **Tema su Niri.** Qt non segue da solo il cambio di schema e non legge l'accento [V]: tocca a Meridiana.
- **Font.** I nomi delle famiglie cambiano tra Windows e Linux [V]. Titillium Web su Windows a 100% è da provare [I].
- **Ortofoto.** I colori pallidi spariscono sui tetti chiari [V]: serve l'alone a due toni.
- **3D.** Valori impostati da Python e binding QML si contendono le proprietà [V]: il tema va solo in binding.
- **Relazione PDF.** `report.py` scrive in colori fissi e deve restare chiara anche col tema scuro [I].
- **Prove automatiche su Wayland.** Menu e caselle non si aprono senza input [V]: i test che li aprono vanno fatti su X11, offscreen o Windows.

**Fuori tema ma utile alla revisione delle prestazioni [V].** Dopo `shiboken6.delete(win)` restano vivi 437 widget per ogni finestra aperta: qualcosa di grande non ha la finestra come genitore.

## 11. Che cosa resta da decidere a Daniel

**Deciso il 22/10/2026** (commento sulla tela): la direzione è **Meridiana**. L'assistente diventa una scheda flottante in basso a destra, sopra le viste, che si apre e si chiude dalla barra di stato. La tela è aggiornata alla versione 15.

**Deciso il 22/10/2026 sera** (messaggi di Daniel):
- i colori di Meridiana si cambiano con una scelta sola (sezione 12); il bronzo resta il colore di partenza;
- l'assistente è un personaggio che fluttua e si clicca per chiedere un parere, sul modello di VS Code; resta lo stesso tra le schede e si sposta da solo (studio 14, sezione 7.3).

La tela è alla versione 17.

Resta da decidere:
- **Direzione.** ~~Meridiana, o una delle altre tre.~~ Meridiana.
- **Lucciola.** Se portare il bordo del pannello attivo (2 px di accento) anche in Meridiana.
- **Disposizione.** Barra delle fasi alla DIALux (Studio) o schede sotto la barra strumenti (Meridiana).
- **Assistente.** ~~Nome, simbolo e colore.~~ Nome e disegno: tre proposte sulla tela. Il colore viene dal colore scelto.
- **Colori pronti.** Se vanno bene i dieci della sezione 12.1, o se ne servono altri.

## 12. Colore a scelta

Daniel, 22/10/2026 sera: «non sono sicuro sulle colorazioni di Meridiana, ma piuttosto le facciamo cambiabili, con possibilità di variarne il colore in modo semplice».

### 12.1 Come si sceglie

- Il pulsante «Colore» accanto a «Tema» nella barra dei menu; la stessa scelta in Preferenze › Aspetto.
- Dieci colori pronti: Sistema, Bronzo (quello di partenza), Cotto, Oliva, Bosco, Petrolio, Blu, Indaco, Prugna, Grafite.
- «Un altro colore»: il selettore dei colori.
- «Fondi»:
  - Meridiana: calce e notte, come nella sezione 7;
  - Dal colore: grigi appena tinti dal colore scelto;
  - Grigi: neutri.
- Un'anteprima con selezione, pulsante, avviso e personaggio, e due righe: il contrasto, e se Meridiana ha ritoccato il colore.
- È una preferenza di chi usa il programma, non del progetto: sta nelle impostazioni, non nel file `.meridiana`.

Sulla tela: il pulsante «Colore» nella finestra di Meridiana, e la tavola «Meridiana, colore a scelta e assistente» (Petrolio, fondi dal colore).

### 12.2 Che cosa si ricava dal colore scelto

Tutto in OKLCH, lo spazio colore in cui la luminosità L è quella che l'occhio percepisce. Si cambiano L e la saturazione C, e si tiene la tinta h.

| Ruolo | Chiaro | Scuro |
|---|---|---|
| accento | L al massimo 0,60 e C al massimo 0,17, poi più scuro finché il bianco sopra ha almeno 4,6:1 | L almeno 0,82 e C al massimo 0,11, poi più chiaro finché sul fondo della vista ha almeno 7:1 |
| testo sull'accento | bianco | il colore della finestra |
| selezione nelle liste | stessa tinta, L 0,925, C fino a 0,055 | stessa tinta, L 0,34, C fino a 0,05 |
| pianta: selezione e contorno dei sottocampi | l'accento | l'accento |
| 3D: modulo selezionato | stessa tinta, L 0,88, C fino a 0,09 | l'accento |
| assistente (ruolo a parte, regola 3.6) | la tinta opposta (h + 180°), L 0,42, C 0,06 | la tinta opposta, L 0,80, C 0,06 |
| fondi «Dal colore» e «Grigi» | finestra L 0,957, pannelli 0,978, linee 0,872, testo 0,235, attenuato 0,515; C fino a 0,016, zero per i grigi | finestra 0,205, pannelli 0,228, vista 0,178, linee 0,318, testo 0,94, attenuato 0,665 |
| stati, grafici, moduli, edifici, cielo | non cambiano | non cambiano |

Con il bronzo la tinta opposta torna il blu ardesia della sezione 7: #334f6d contro #2e4a6b in chiaro, #a1c1e4 contro #9ec1e8 in scuro.

Dal 23/10/2026 le righe «pianta» e «3D» della tabella non si usano più: pianta e 3D hanno colori propri, uguali nei due temi (regola 3.7). I gettoni restano nel calcolo di riferimento (`13-colori/`) per non staccare il Python dal riferimento.

### 12.3 Gli stati restano riconoscibili

- Un colore ricavato (accento, assistente, modulo selezionato) non può stare a meno di 0,15 in OKLab da un colore di stato: #fab219 avviso, #d03b3b errore, #0ca30c superata.
- Se ci sta, Meridiana lo sposta a piccoli passi finché non se ne stacca: più scuro in chiaro, più chiaro e meno saturo in scuro.
- L'anteprima lo dice: «Era vicino al rosso degli errori: Meridiana lo ha scurito un poco per tenerli distinti».
- Risolve anche C6 della revisione: il sole pallido di oggi, a 12,7 dal giallo d'avviso, diventa #f1dac1, a 15.

### 12.4 Prove [V calcolo]

Gli script sono in `C:\Users\utente\dev\meridiana-prove\colori-2026-10-22` e, perché li veda anche una sessione nel cloud, nel repository in `docs/studio/13-colori` (si lanciano con `node`):
- `colori.js` contiene lo stesso codice della tela;
- `tabella.js` produce la tabella qui sotto;
- `casuali.js` fa le prove a caso.

Colori pronti con i fondi Meridiana; il contrasto dell'accento scuro è sul fondo della vista #101318:

| Colore | Scelto | Accento chiaro (bianco sopra) | Accento scuro (sul fondo) | Assistente chiaro / scuro | Ritoccato |
|---|---|---|---|---|---|
| Sistema (Windows) | #0078d4 | #0075cf (4,7:1) | #97c9ff (10,7:1) | #624726 / #e2d5c7 | - |
| Sistema (Lucciola, giallo di GNOME) | #c88800 | #906102 (5,4:1) | #f3e2ca (14,7:1) | #374e6e / #a5c0e5 | chiaro, dall'errore; scuro, dall'avviso |
| Bronzo, di partenza | #8b5a12 | #805210 (6,7:1) | #f1dac1 (13,8:1) | #334f6d / #a1c1e4 | chiaro, dall'errore; scuro, dall'avviso |
| Cotto | #a4482b | #7e351e (8,7:1) | #f9d5ca (13,6:1) | #205563 / #92c8d8 | chiaro, dall'errore; scuro, dall'avviso |
| Oliva | #5f6b1f | #5f6b1f (5,8:1) | #dbe2c4 (13,9:1) | #51466a / #c2b6e0 | scuro, dall'avviso |
| Bosco | #2f6b4f | #2f6b4f (6,3:1) | #97d4b4 (11,0:1) | #634057 / #daafc9 | - |
| Petrolio | #1f6a7a | #1f6a7a (6,2:1) | #8ad1e3 (10,9:1) | #6a4136 / #e4cbc4 | - |
| Blu | #2a5ea8 | #2a5ea8 (6,4:1) | #9fc6ff (10,6:1) | #5f4925 / #e1d6c6 | - |
| Indaco | #5b4bb0 | #5b4bb0 (6,8:1) | #bfbbff (10,4:1) | #514f26 / #d9d9c7 | - |
| Prugna | #8a3a6e | #8a3a6e (7,2:1) | #f6a7d7 (10,1:1) | #2b5744 / #9bcab3 | - |
| Grafite | #4a4f57 | #4a4f57 (8,2:1) | #bfc4ce (10,6:1) | #5e4925 / #e0d6c6 | - |

**2.000 colori a caso**, con i tre fondi, in chiaro e in scuro: nessun controllo fallisce. I casi peggiori stanno sulle soglie scelte:
- testo sull'accento 4,6:1;
- testo attenuato sui pannelli 4,8:1;
- testo sulla selezione 9,4:1;
- distanza dagli stati 0,150.

### 12.5 Il colore del sistema

- **Windows** [V su questo PC, Qt 6.12]: Qt mette l'accento di Windows nella palette della piattaforma. `Highlight` vale #0078d4, `Accent` #4cc2ff (la variante chiara), il registro #0078d7. Meridiana lo legge prima di mettere la sua palette, e lo rilegge quando Windows lo cambia.
- **Linux** [V su Lucciola]: Qt non legge l'accento del portale (sezione 8), quindi Meridiana lo chiede da sé al portale, con QtDBus.
  - Legge la chiave `accent-color` di `org.freedesktop.appearance` e ascolta `SettingChanged`.
  - Su Lucciola il portale dà il giallo di GNOME, #c88800, con il sistema in scuro.
  - Diventa #906102 in chiaro e #f3e2ca in scuro, ritoccati dall'errore e dall'avviso.
- Senza un accento di sistema, per esempio su X11 senza portale, Meridiana usa il bronzo.

### 12.6 Nel codice

- `ui/theme.py` (passo 1 della sezione 9) calcola il Tema con la stessa funzione provata qui, tradotta in Python: una quarantina di righe, senza librerie nuove.
- Test: i contrasti e le distanze della 12.4, per ogni colore pronto e per 500 colori a caso, con i tre fondi e i due temi.
- Quando si cambia colore:
  - l'anteprima nel riquadro cambia subito;
  - la finestra intera si aggiorna al rilascio, o dopo 250 ms senza movimenti, perché rimettere il foglio di stile costa 0,4-0,9 s (sezione 8);
  - il 3D non cambia: ha i suoi colori (regola 3.7); il cubo di vista sì, perché è un pulsante sopra la vista.
- Il colore dell'assistente passa anche al disegno del personaggio (studio 14, sezione 8).

## 13. Fonti

Consultate il 22/10/2026.

**DIALux evo**
- https://www.dialux.com/en-GB/dialux/whats-new-in-dialux-evo-14
- https://www.dialux.com/en-GB/dialux/whats-new-in-dialux-evo-13
- https://www.dialux.com/en-GB/dialux/whats-new-in-dialux-evo-12
- https://www.dialux.com/en-GB/free-dialux-basic-course/how-does-the-dialux-evo-user-interface-work
- https://evo.support-en.dial.de/support/solutions/articles/9000115077-user-views
- https://evo.support-en.dial.de/support/solutions/articles/9000115624-results-overview
- https://evo.support-en.dial.de/support/solutions/articles/9000115112-display-options
- https://evo.support-en.dial.de/support/solutions/articles/9000066070-is-it-possible-to-configure-the-background-colour-
- https://evo.support-en.dial.de/support/solutions/articles/9000115683-false-colours

**GNOME e libadwaita**
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/css-variables.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/enum.AccentColor.html
- https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/style-classes.html
- https://developer.gnome.org/hig/guidelines/typography.html
- https://developer.gnome.org/hig/patterns/containers/header-bars.html
- https://developer.gnome.org/hig/patterns/containers/utility-panes.html
- https://release.gnome.org/47/ e https://release.gnome.org/48/
- https://github.com/GNOME/adwaita-fonts
- https://flatpak.github.io/xdg-desktop-portal/docs/doc-org.freedesktop.portal.Settings.html

**Niri**
- https://github.com/niri-wm/niri (README e `resources/default-config.kdl`)
- https://niri-wm.github.io/niri/Configuration%3A-Layout.html
- https://niri-wm.github.io/niri/Configuration%3A-Window-Rules.html

**Qt**
- https://doc.qt.io/qt-6/qtwidgets-styling-approaches.html
- https://doc.qt.io/qt-6/qstylehints.html#colorScheme-prop
- https://doc.qt.io/qt-6/qapplication.html#setPalette
- https://doc.qt.io/qt-6/qfont.html#setFeature
- https://doc.qt.io/qt-6/qml-qtquick3d-sceneenvironment.html
- https://www.qt.io/blog/dark-mode-on-windows-11-with-qt-6.5 («The Fusion style is our preferred style for Windows 11»)
- sorgenti Qt 6.12 su github.com/qt: `qwindows11style.cpp`, `qxdgdesktopportaltheme.cpp`, `qgenericunixtheme.cpp`, `qstylesheetstyle.cpp`

**Wayland**
- https://wayland.app/protocols/xdg-toplevel-drag-v1

**Colore** (sezione 12)
- OKLab e OKLCH: https://bottosson.github.io/posts/oklab/
- WCAG 2.2, contrasto del testo (1.4.3) e degli elementi grafici (1.4.11): https://www.w3.org/TR/WCAG22/
- Qt, ruoli della palette (`Accent`, `Highlight`): https://doc.qt.io/qt-6/qpalette.html#ColorRole-enum
- Portale, `org.freedesktop.appearance` e `accent-color`: la pagina dei Settings tra le fonti GNOME qui sopra

**Icone e font**
- Lucide (ISC): https://lucide.dev, pacchetto `lucide-static` 1.49.0
- Tabler (MIT): `@tabler/icons` 3.47.0
- Phosphor (MIT): `@phosphor-icons/core` 2.1.1
- Material Symbols (Apache 2.0): `@material-symbols/svg-400` 0.47.4
- Titillium Web, IBM Plex, Atkinson Hyperlegible: https://github.com/google/fonts (cartelle `ofl/...`, licenza OFL)

**Palette dei grafici.** Lo strumento di validazione della skill dataviz (`validate_palette.py`), con le superfici di ogni direzione.
