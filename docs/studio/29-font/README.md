# Studio 29: il carattere di Meridiana (Inter, i Nerd Fonts, i condensati, JetBrains Mono)

Agente FT, 03/11/2026, ramo `r10-font`. Daniel: «mi fai delle valutazioni di cambio font con tipo nerdfonts o altri font leggibili
magari con possibilità condensed per dove c'è poco posto? tipo quello che ho in Lucciola o simili?»; poi, via coordinatore:
JetBrains Mono come finalista, in due usi (tutta l'interfaccia; solo numeri e valori). Solo studio: **nessun codice del programma
è cambiato**. La decisione è di Daniel.

- `bozzetti.html`: le foto affiancate (barra, pannello Impianto stretto, finestre), il grafico delle larghezze, le prove sull'asse
  `wdth`. `foto/`: le foto (`<variante>-<1|2>x-<light|dark>-<bar|panel|window>.png`, il 2x ha il doppio dei pixel).
- `misure.json`, `prove/`: misure e script, ripetibili (`prove/` ha percorsi della cartella di lavoro dell'agente: vanno adattati).
  `genera.py` riscrive `bozzetti.html`.

Convenzione: **[V]** verificato (come), **[D]** dedotto, **[N]** non verificato.

## 0. In breve

1. **I Nerd Fonts non servono per l'interfaccia.** Sono font da terminale con migliaia di icone nella zona privata di Unicode; Meridiana
   ha già Lucide e simboli disegnati; ogni file pesa 2,5 MB contro 0,1-0,4 MB. Se servono le icone, esiste «Symbols Nerd Font» da sola,
   ma anche lì non servirebbe. Sezione 6.
2. **Il condensato vero in Qt c'è, ma con una regola.** `QFont.setVariableAxis("wdth", ...)` cambia davvero la forma delle lettere, su
   Windows e su Linux, con font a asse variabile (Open Sans, Noto Sans, Roboto, IBM Plex Sans, Archivo). Ma su Linux, se il peso è
   dato con `setWeight`, **l'asse `wdth` viene perso** (Open Sans, Noto Sans) o **il peso non viene applicato** (Roboto, Archivo): serve
   impostare `wght` e `wdth` entrambi come assi. I **file condensati statici** (IBM Plex Sans Condensed, Fira Sans Condensed, Barlow
   Semi Condensed) funzionano uguale su Windows e Linux, con i pesi. Sezione 4.
3. **Raccomandazione: tenere Inter come carattere del programma**, perché è già il candidato che conserva di più i tratti per cui a Daniel
   piace JetBrains Mono (altezza della x, forme aperte, cifre chiare), e **fare due aggiunte piccole**: (a) cifre tabellari
   (`tnum`) per numeri, tabelle e campi, a costo quasi zero; (b) un **condensato solo dove manca posto**: IBM Plex Sans Condensed
   (statico, OFL, 111 KB per peso), oppure Inter Tight se si vuole un guadagno più piccolo con lo stesso disegno. Cambiare tutto il
   programma in un altro font non dà abbastanza: nessun candidato è più stretto di Inter di più dell'8-9 % senza perdere leggibilità
   a 13 px, e i più larghi di x-height (Noto, Open Sans) costano righe più alte. Sezioni 8 e 9.
4. **JetBrains Mono per tutta l'interfaccia no** (+29 % di larghezza sui testi veri, il pannello Impianto non scende sotto 314 px contro
   298): **solo per numeri e valori sì**, è ottimo, con il costo di +17 % sui numeri e dei campi a combinazione (`QComboBox`) che
   troncano il testo. Non esiste una variante proporzionale o più stretta distribuibile («JetBrains Sans» non è pubblicato). Sezione 7.

## 1. Che cosa vede Daniel a Lucciola, e quale «font di sistema» ha in mente

- [V, `ssh fw13`, `gsettings`] Interfaccia GNOME: **Adwaita Sans 11**; testo a spaziatura fissa: **Adwaita Mono 11**. [V, `fc-list`]
  Installati: **JetBrains Mono** (RPM di sistema, `/usr/share/fonts/jetbrains-mono-fonts/`, file `.otf`), **DroidSansMono Nerd Font**
  (`~/.local/share/fonts/Droid Sans Mono for Powerline Nerd Font Complete.otf`), Adwaita Sans/Mono, Droid Sans. [V, `fc-match`] Il
  generico `sans-serif` si risolve in **Noto Sans**.
- [V] **Adwaita Sans è derivato da Inter**: il suo `LICENSE` (OFL 1.1) elenca come primo copyright «The Inter Project Authors», poi
  Jamie Gravendeel e Florian Müllner (GNOME); il file ha 859 KB, assi `opsz` e `wght` come Inter, e le misure sono quasi identiche
  (101 % di Inter sui testi veri; x-height 0,546 em, uguale). Il mio ricordo era giusto. **Adwaita Mono** porta il copyright di
  Belleve Invis, l'autore di Iosevka, quindi è un derivato di Iosevka [D dal copyright, non ho confrontato i disegni].
- **Quale font intende Daniel con «di sistema» non lo so** [N]. Le ipotesi: (a) l'interfaccia di Lucciola, cioè Adwaita Sans, che è
  Inter: allora ha già Inter anche in Meridiana; (b) il terminale o l'editor con **JetBrains Mono** o **DroidSansMono Nerd Font**;
  (c) su Windows, **Segoe UI**, il font del sistema che Meridiana sostituisce. Per questo JetBrains Mono è tra i finalisti.
- [D] Anche a parità di carattere, a Lucciola il testo sembra diverso perché Linux disegna con FreeType, senza hinting e con
  anti-aliasing a toni di grigio, mentre Windows usa DirectWrite con hinting e ClearType. R95 (25/10) aveva già escluso il motore di
  Windows come causa del difetto di allora (il difetto era Titillium Web). Se a Daniel il testo piace di più a Lucciola con Adwaita Sans,
  **è probabile che sia in parte la resa e non il carattere**: una prova semplice è la foto della stessa finestra sui due schermi.

## 2. Censimento: licenza, peso, fonte

Tutti scaricati il 03/11/2026 in `scratchpad\font\dl\<famiglia>\` (dati, nessuno script lì dentro), file non modificati. Il peso è quello
dei file che servirebbero (Regular e SemiBold dove sono statici; il file solo dove è variabile).

| Famiglia | Licenza | KB | Fonte | Forma |
|---|---|---|---|---|
| **Inter 4.1** (oggi) | OFL 1.1 | 1223 (3 statici) | rsms/inter v4.1; copia già in `data/fonts/inter` | statico 400/600/700 |
| Inter (variabile `opsz,wght`) | OFL 1.1 | 876 | google/fonts `ofl/inter` | variabile |
| Inter Tight | OFL 1.1 | 568 | google/fonts `ofl/intertight` | variabile `wght` |
| Adwaita Sans | OFL 1.1 | 859 | GNOME/adwaita-fonts `sans/` | variabile `opsz,wght` |
| Noto Sans | OFL 1.1 | 2001 | google/fonts `ofl/notosans` | variabile `wdth` 62,5-100, `wght` |
| Open Sans | OFL 1.1 | 520 | google/fonts `ofl/opensans` | variabile `wdth` 75-100, `wght` |
| Roboto | OFL 1.1 | 477 | google/fonts `ofl/roboto` | variabile `wdth`, `wght` |
| Roboto Condensed | OFL 1.1 | 363 | google/fonts `ofl/robotocondensed` | variabile `wght` (condensato fisso) |
| Roboto Flex | OFL 1.1 | 1745 | google/fonts `ofl/robotoflex` | variabile, 13 assi |
| IBM Plex Sans | OFL 1.1 (nome riservato «Plex») | 525 | google/fonts `ofl/ibmplexsans` | variabile `wdth` 85-100, `wght` |
| IBM Plex Sans Condensed | OFL 1.1 (nome riservato) | 218 (2 statici) | google/fonts `ofl/ibmplexsanscondensed` | statico |
| Source Sans 3 | OFL 1.1 (nome riservato «Source») | 631 | google/fonts `ofl/sourcesans3` | variabile `wght` |
| Fira Sans | OFL 1.1 | 924 (2 statici) | google/fonts `ofl/firasans` | statico |
| Fira Sans Condensed | OFL 1.1 | 926 (2 statici) | google/fonts `ofl/firasanscondensed` | statico |
| Barlow | OFL 1.1 | 208 (2 statici) | google/fonts `ofl/barlow` | statico |
| Barlow Semi Condensed | OFL 1.1 | 210 (2 statici) | google/fonts `ofl/barlowsemicondensed` | statico |
| Archivo | OFL 1.1 | 643 | google/fonts `ofl/archivo` | variabile `wdth` 62-125, `wght` |
| JetBrains Mono 2.304 | OFL 1.1 | 538 (2 statici) | JetBrains/JetBrainsMono v2.304 `fonts/ttf` | statico, a spaziatura fissa |
| JetBrainsMono Nerd Font (e «Propo») | OFL 1.1 (font) + licenze delle serie di icone | 2511 ciascuno | ryanoasis/nerd-fonts v3.5.1 | statico, a spaziatura fissa |
| Ubuntu Nerd Font Propo (Regular e Condensed) | **Ubuntu Font Licence 1.0**, non OFL | 2477 e 2471 | ryanoasis/nerd-fonts v3.5.1 | statico, proporzionale |
| Adwaita Mono | OFL 1.1 | 1386 | GNOME/adwaita-fonts `mono/` | statico, a spaziatura fissa |

[V] Le licenze sono quelle dei file `OFL.txt`/`LICENSE` scaricati accanto ai font (prima riga del copyright letta). OFL permette di
incorporare i font in un programma GPL e nei PDF della relazione (Typst), senza vendere il font da solo; i nomi riservati (Plex,
Source) impediscono solo di rinominare una versione modificata. [D] La Ubuntu Font Licence è libera ma è un'altra licenza: da leggere
prima di distribuirla, la eviterei senza una ragione. «Ubuntu Sans» come Nerd Font non è nel repository ma solo un `README`
(si scarica dalle release): non l'ho provato.

## 3. Misure con Qt

[V] `prove/measure.py`: `QFontMetricsF.horizontalAdvance` a 13 px, Windows 11, PySide6 6.12 (DirectWrite, hinting predefinito,
**che è quello che Meridiana ha a 100 % su Windows**: le larghezze sono intere per carattere, per questo ±2-3 punti sono rumore;
la colonna «nh» è senza hinting, cioè la larghezza di disegno che si ha a 200 % e su Linux). Testi: le fasi, i comandi delle barre,
le etichette («Rapporto DC/AC voluto», «Aggiungi un inverter dal catalogo…»), le voci delle Verifiche, i numeri («1,44», «5.489,56»),
e **3181 stringhe vere** di `po/it.po` (fino a 70 caratteri, segnaposto sostituiti). 100 % = Inter 4.1 statico (le fasi sono 402 px).
Il peso del file è in KB; «x/em» l'altezza della x (OS/2) e «riga» l'altezza di una riga di testo a 13 px.

| Carattere | fasi | barra | etichette | verifiche | numeri | **testi veri** | nh | x/em | riga | cifre | `tnum` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Inter 4.1** (oggi) | 100 | 100 | 100 | 100 | 100 | **100** | 100 | 0,546 | 16 | proporzionali | sì |
| Inter, spaziatura -0,2 px | 97 | 97 | 97 | 97 | 97 | 97 | 97 | 0,546 | 16 | prop. | sì |
| Inter, spaziatura -0,4 px | 94 | 94 | 94 | 94 | 94 | 94 | 94 | 0,546 | 16 | prop. | sì |
| Inter, cifre tabellari | 100 | 99 | 99 | 98 | 102 | 98 | 100 | 0,546 | 16 | **tabellari** | sì |
| Inter Tight | 93 | 93 | 92 | 91 | 89 | 91 | 90 | 0,546 | 16 | prop. | sì |
| Adwaita Sans | 102 | 101 | 101 | 102 | 100 | 101 | 100 | 0,546 | 16 | prop. | sì |
| Noto Sans (wdth 100) | 99 | 98 | 97 | 97 | 91 | 97 | 99 | 0,536 | **18** | tabellari | sì |
| Noto Sans wdth 87,5 | 93 | 92 | 91 | 91 | 89 | 91 | 90 | 0,536 | 18 | tab. | sì |
| Noto Sans wdth 75 | 89 | 87 | 86 | 85 | 79 | 86 | 82 | 0,536 | 18 | tab. | sì |
| Open Sans (wdth 100) | 98 | 97 | 96 | 95 | 91 | 95 | 99 | 0,535 | 18 | tab. | sì |
| Open Sans wdth 87,5 | 86 | 85 | 85 | 84 | 80 | 84 | 86 | 0,535 | 18 | tab. | sì |
| Open Sans wdth 75 | 74 | 72 | 73 | 71 | 76 | 71 | 73 | 0,535 | 18 | tab. | sì |
| Roboto (wdth 100) | 92 | 91 | 91 | 91 | 90 | 91 | 94 | 0,528 | 15 | tab. | sì |
| Roboto wdth 75 = Roboto Condensed | 84 | 83 | 82 | 82 | 79 | 82 | 84 | 0,528 | 15 | tab. | sì |
| Roboto Flex (wdth 100) | 98 | 95 | 95 | 95 | 93 | 95 | 94 | 0,514 | 15 | tab. | no |
| IBM Plex Sans | 96 | 95 | 94 | 94 | 102 | 94 | 95 | 0,516 | 17 | tab. | no |
| IBM Plex Sans wdth 85 | 92 | 91 | 89 | 90 | 89 | 90 | 90 | 0,516 | 17 | tab. | no |
| **IBM Plex Sans Condensed** | 87 | 85 | 86 | 85 | 89 | **86** | 86 | 0,516 | 17 | tab. | no |
| Source Sans 3 | 91 | 88 | 89 | 87 | 81 | 88 | 88 | 0,478 | 18 | tab. | no |
| Fira Sans | 100 | 98 | 97 | 96 | 87 | 96 | 96 | 0,527 | 15 | prop. | sì |
| **Fira Sans Condensed** | 86 | 86 | 86 | 85 | 80 | **85** | 86 | 0,526 | 15 | prop. | sì |
| Barlow | 92 | 93 | 91 | 92 | 87 | 91 | 90 | 0,506 | 16 | prop. | sì |
| Barlow Semi Condensed | 81 | 81 | 80 | 81 | 77 | 81 | 81 | 0,506 | 16 | prop. | sì |
| Archivo (wdth 100) | 98 | 97 | 96 | 95 | 96 | 96 | 93 | 0,526 | 14 | prop. | sì |
| Archivo wdth 87,5 | 90 | 89 | 87 | 86 | 84 | 86 | 83 | 0,526 | 14 | prop. | sì |
| Archivo wdth 75 | 80 | 78 | 78 | 77 | 77 | 77 | 74 | 0,526 | 14 | prop. | sì |
| Ubuntu Nerd Font Propo | 97 | 96 | 96 | 94 | 90 | 95 | 96 | 0,520 | 15 | tab. | sì |
| Ubuntu Nerd Font Propo Condensed | 80 | 79 | 79 | 78 | 77 | 78 | 78 | 0,520 | 15 | tab. | sì |
| **JetBrains Mono** (= tutti i Nerd Font JB, = Adwaita Mono) | 123 | 126 | 122 | 132 | 117 | **129** | 127 | 0,550 | 17 | tabellari | no |

Che cosa dicono:
- [V] **Inter non è un font largo**: Noto Sans (97 %), Open Sans (95 %), Fira Sans (96 %), IBM Plex Sans (94 %), Archivo (96 %) sono tutti
  quasi alla pari. Cambiare famiglia senza condensare non fa guadagnare posto. Per risparmiare davvero servono un condensato o
  una spaziatura ridotta.
- [V] **Altezza della riga** (a 13 px, dai metrici dei font): Noto Sans e Open Sans fanno 18 px contro 16 di Inter, +12 % in verticale su
  ogni riga di tabella, di lista e di campo; Fira, Roboto, Ubuntu 15; Archivo 14. [D] Un font con riga più bassa dà posto in verticale
  (le Verifiche sono basse su 1366 x 768), uno con riga più alta ne toglie.
- [V] **Cifre**: Inter ha cifre **proporzionali** per default (l'«1» è 0,62 dello «0») e la feature `tnum`; con `tnum` «1,111» e «0,000»
  hanno la stessa larghezza, provato su Windows (35 e 35 px) e su Linux (37,2 e 37,2 px), con Qt 6.12 (`QFont.setFeature(QFont.Tag("tnum"), 1)`).
  Costo: i numeri passano da 100 a 102 % di larghezza (a 13 px). Noto, Open Sans, Roboto, Plex, Source e JetBrains hanno già cifre tabellari.
- [V] **Copertura** (`QFontMetricsF.inFontUcs4` sui caratteri non ASCII di `po/it.po`, più °, ², ·, «», −, ≥, ∥, ⊥): tutti i candidati
  hanno à è ì ò ù é ° ² · « » − ≥ € × Ω γ → … **Nessun** candidato proporzionale ha ∥ ⊥ ⋯ ✕; Inter, che oggi non li ha, li fa già
  disegnare in un font a parte (`theme.mark`, `SYMBOL_FAMILY`): non cambia nulla cambiando font. **JetBrains Mono ha ∥ ⊥ ⋯** (mancano
  solo ✕ e pochi altri), quindi nei suoi usi sarebbe un vantaggio piccolo.
- [V] Il **peso**: il passaggio a un font statico condensato è leggero (Plex Condensed 109 KB per peso, Barlow 105); i variabili grandi
  (Noto 2,0 MB, Roboto Flex 1,7 MB) pesano nel pacchetto e nel Flatpak.

## 4. L'asse `wdth` in Qt (il condensato vero)

[V] `prove/axis2.py`, `axis3.py`, `axis4.py`, foto `foto/axis-win.png` e `foto/axis-linux.png`. PySide6 6.12.0 su Windows 11 (offscreen,
DirectWrite) e su Fedora (Lucciola, `~/fvtest/venv314`, offscreen, FreeType), con una cartella temporanea `~/tmp-font-claude` mia (cancellata
cartella temporanea mia da cancellare; non ho chiuso nulla né aperto finestre).

1. **`setVariableAxis(wdth, v)` funziona**, su entrambe le piattaforme: le lettere cambiano davvero forma (nelle foto sono condensate
   e non schiacciate), le larghezze coincidono con quelle calcolate con fontTools (Noto Sans, Inter Tight: scarto 0,4-0,6 px su 190-224 px).
   Open Sans a `wdth` 75 su Windows 199 px contro 255 (-22 %), su Linux 196 contro 263 (-25 %). Il valore è limitato al campo dell'asse
   (IBM Plex Sans non scende sotto 85: `wdth` 75 dà la larghezza di 85).
2. **`setStretch(75)` non è la stessa cosa**: per Open Sans e Roboto coincide con l'asse, per Noto Sans, IBM Plex Sans, Archivo (e per
   Roboto su Linux) **schiaccia sinteticamente** le lettere oltre l'asse (si vede nella foto: sottili, con i tratti verticali ridotti). Non usarlo.
3. **Il nome dello stile («Condensed Regular») non basta**: su Windows funziona (Roboto e Open Sans), su Linux no (larghezza uguale al normale).
4. **Combinazione con il peso, Linux** (Meridiana dà il peso con `QFont.setWeight` in `design.font()`): con `setWeight(DemiBold)` più l'asse
   `wdth`, **su Linux Open Sans e Noto Sans perdono il `wdth`** (270,9 px, cioè più larghi del normale) e **Roboto non applica il
   peso** (il semigrassetto ha la larghezza del Regular) e **Archivo** ha il Regular già disegnato in semigrassetto (il primo stile del file), quindi i due pesi coincidono; su Windows invece tutto funziona. **L'unica forma che funziona su entrambi è
   dare `wght` e `wdth` entrambi come assi**, lasciando il peso del `QFont` a Normal: `setVariableAxis(wght, 600)` e `setVariableAxis(wdth, 75)`.
   Provato per Open Sans, Noto, Roboto, Archivo (Linux 207,6 / 229,4 / 228,8 / 209,1 px). Un altro motivo per non usare Archivo senza l'asse `wght` esplicito (foto `axis-linux.png`: le righe Archivo sono in semigrassetto).
5. **Gli stili del foglio di stile**: [V, Windows e Linux] `QLabel{font-weight:600}` in un foglio di stile **annulla l'asse `wdth`** impostato
   sul widget su Linux (271 px, cioè di nuovo largo) e lo mantiene su Windows (209 px); `font-size:14px` e `color` lo mantengono; la copia del
   `QFont` e `app.setFont()` lo mantengono. In Meridiana ci sono 14 punti con `font-weight` nei fogli di stile.
6. **Font statici condensati** (Fira Sans Condensed, IBM Plex Sans Condensed, Barlow Semi Condensed): [V] stessa famiglia Qt per i due
   pesi, `setWeight(DemiBold)` sceglie il file SemiBold (esatto, `exactMatch()`), identico su Windows e Linux (Plex Condensed 232,7 e 240,4 px su Linux).
   **Per Meridiana è la strada sicura.** (Roboto Condensed è un file variabile `wght` ma il suo condensato è fisso: anche questo funziona.)

Quindi: un font variabile con asse `wdth` vale come «condensato» solo se il programma imposta gli assi esplicitamente (e non usa
`font-weight` nei fogli di stile per quei widget); i font statici condensati valgono sempre. [N] Non ho provato Qt Quick (le scene 3D e
le pagine QML) né l'asse con `QFontDatabase.addApplicationFont` da un file impacchettato PyInstaller/Flatpak (i file sono letti allo stesso modo di oggi).

## 5. Le foto

[V] `prove/photo.py` + `run_photo.sh`: la `MainWindow` vera (`tests/_setup.window`), progetto «Capannone», italiano, fase Impianto, 1500 x 960
logici (le barre mostrano le parole), sottocampo selezionato (il pannello Proprietà ha i campi), pannello tirato a 276 px, 100 % e 200 %
(`QT_SCALE_FACTOR=2`, schermo virtuale doppio), chiaro e scuro. Il carattere è sostituito **senza toccare il sorgente**: `theme.FONT_DIR` e
`FONT_FILES` puntati a una cartella dei candidati, `paths.shipped` sostituito per quella cartella; il condensato e JetBrains Mono per i
valori sono dati ai widget dopo la creazione. `bozzetti.html` le mostra affiancate. Aperte e guardate le barre (100 % chiaro, 200 % scuro),
i pannelli (100 % chiaro, 200 % chiaro e scuro) e due ingrandimenti a 200 %.

Cosa si vede:
- [V] **Barra Impianto** (fino alla freccia dopo «Elimina stringa», letto dalle foto a 100 %, ±3 px): Inter 950 px, Inter Tight 935,
  Plex Condensed 856, Fira Condensed 856, Noto Sans wdth 75 844, JetBrains Mono ovunque 1128 (+19 %, e la striscia di stato che sta a destra della barra sparisce). Inter con
  Plex Condensed nei bottoni è coerente: il condensato si legge come «lo stesso testo più stretto», non come un altro carattere, nei bottoni
  piccoli. Inter Tight guadagna poco (15 px) perché i bottoni hanno anche icone e margini.
- [V] **Pannello Impianto**: il contenuto fissa un minimo di larghezza che cambia con il carattere: Inter 298 px (chiesti 276), Inter Tight 289,
  Plex Sans 286, Fira Sans 286, Noto 293, **JetBrains Mono ovunque 314**. Con le etichette del pannello in condensato il testo è chiaro anche a 200 %,
  ma la colonna delle etichette tiene la stessa larghezza e «Moduli per tavola, in altezza» va a capo uguale: il guadagno viene solo se il layout
  è ripensato (l'etichetta occupa metà della riga).
- [V, **trappola di layout**] Con Fira Condensed e con Noto wdth 75 nelle etichette del pannello, il layout **passa da etichetta sopra il
  campo a etichetta accanto al campo** per «Montaggio», e il menu a tendina si tronca («File inclinate,»): le soglie di quei form sono misurate sul
  testo, quindi cambiare i metrici cambia le decisioni. Costo reale del passaggio, vedi sezione 10.
- [V] **JetBrains Mono per i valori** (campi, caselle numeriche, menu a tendina, tabelle e liste, etichette solo numeriche: 97-142 widget): i valori
  «15,0°», «0,0°», «9,50 m» si leggono molto bene e si allineano; **i menu a tendina troncano** («Generico 450 W» diventa «Generico 450»;
  «File inclinate, ancorate» resta); lo zero ha un segno interno e si distingue dalla «O» (utile). Il resto resta in Inter: l'effetto
  misto non stona nel pannello, perché etichetta e valore sono già due livelli diversi.
- [V] **JetBrains Mono ovunque**: la barra Impianto cresce da 950 a ~1128 px e perde la striscia di stato a destra, nel pannello il menu «Montaggio» si
  tronca («File inclina») e le etichette vanno a capo di più: è la prova che non va per tutto.
- [N] **La resa a schermo vero su Windows** (ClearType, hinting) non si vede offscreen: la foto offscreen usa il rasterizzatore di Qt, non lo
  schermo. R95 aveva già visto che l'effetto dei 13 px dipende dalla resa a schermo: per i finalisti **serve una foto su schermo vero** prima di decidere.

## 6. I Nerd Fonts: servono per l'interfaccia?

**No.** [V] Sono font normali (JetBrains Mono, Ubuntu, Droid Sans Mono, Hack…) ai quali un programma di «patching» aggiunge migliaia di
glifi nella zona privata di Unicode (Font Awesome, Material Design, Devicons, Powerline, Octicons, simboli di Pomicons, ecc.), pensati per
i terminali e le righe di stato (`nvim`, `starship`). Perché non servono a Meridiana:
- **Le icone ci sono già**: Lucide come SVG e simboli disegnati in `ui/marks.py` (R-simboli); i glifi di un font non seguono il colore dei temi
  né la resa a 200 % meglio di un SVG, e non sono cercabili nei temi. [D]
- **Sono pesanti**: [V] JetBrainsMono Nerd Font 2511 KB e Ubuntu Nerd Font Propo 2477 KB per **un** peso, contro 273 KB del JetBrains Mono originale e
  218 KB dei due pesi di Plex Condensed. Quattro file in più fanno 10 MB nel pacchetto Windows e nel Flatpak.
- **Licenze miste**: il font base è OFL (JetBrains) o UFL (Ubuntu); le serie di icone hanno licenze loro (MIT, Apache, CC BY…): da elencare nell'avviso
  di terze parti. [D]
- **Non sono più stretti né migliori come testo**: [V] «JetBrainsMono Nerd Font Propo» ha **la stessa larghezza di JetBrains Mono** (129 % di Inter
  sui testi veri): il «Propo» dei Nerd Fonts rende **proporzionali le icone**, non le lettere. L'unico Nerd Font con lettere proporzionali e un
  condensato è **Ubuntu Nerd Font Propo** (95 % e 78 %): è il carattere Ubuntu con le icone, non è migliore di Plex Condensed e ha la licenza UFL.
- Il nome di famiglia di Windows dei patchati è cambiato («JetBrainsMono NF»), il che sposta i rimandi e i test: nessun vantaggio.
- Se mai servisse una sola icona di un set Nerd, esiste **Symbols Nerd Font** da sola (2,5 MB); è un font da aggiungere come ripiego, non da scegliere.

La domanda «Nerd Font» di Daniel è di fatto «un font leggibile con aspetto da terminale»: la risposta è JetBrains Mono semplice, non patchato.

## 7. JetBrains Mono: perché piace, cosa lo ricorda, JetBrains Sans

**Perché piace** [D, non l'ho verificato con Daniel; è letto dalle misure]: JetBrains Mono è disegnato per leggere codice a corpi piccoli.
- **x-height alta**: [V] 550 su 1000 em (0,550), con maiuscole a 0,730: la x è il 75 % della maiuscola. Le minuscole sembrano grandi
  anche a 13 px, e non c'è bisogno di aumentare il corpo.
- **Forme aperte e regolari** (aperture di c, e, s, a ampie, terminazioni orizzontali), poche ambiguità: «1», «l», «I», «0», «O» si distinguono.
- **Cifre chiare e tabellari**: ogni cifra ha la stessa larghezza, lo zero con un segno interno (foto), «1» con la base: i numeri si leggono e si
  confrontano a colpo d'occhio.
- Spaziatura costante: le colonne di numeri stanno in fila.

**Quale candidato lo conserva di più**: [V] la misura più direttamente confrontabile è il rapporto x/maiuscola: **JetBrains 0,753, Inter 0,750**
(Adwaita Sans identico a Inter, 0,750), Noto 0,751, Open Sans 0,750, Fira 0,765, Roboto 0,744, IBM Plex 0,740, Source 0,724. E x/em: JetBrains 0,550,
**Inter 0,546**, Noto 0,536, Open Sans 0,535, Roboto 0,528, Fira 0,527, Archivo 0,526, Plex 0,516, Source 0,478. Quindi **Inter (e Adwaita Sans, che ne è
derivato) è il più vicino** per altezza della x e proporzioni. Inter ha anche le feature `zero` (zero con segno interno), `ss02` (lettere
disambiguate: «l», «I»), `tnum` (cifre tabellari): [V, elenco delle feature del file Inter-Regular.ttf] ci sono; [N] `zero` e `ss02` non li ho
provati in Qt, `tnum` sì. Dopo Inter, per l'aspetto da «font di strumento» propongo IBM Plex Sans (più «ingegneristico»; cifre tabellari; x più bassa)
e Fira Sans (della stessa famiglia concettuale di Fira Mono, con x alta ma riga più bassa).

**Variante proporzionale o più stretta dello stesso stile**:
- [V] JetBrains Mono ha solo pesi (Thin-ExtraBold), corsivi e la versione senza legature («NL»); **nessuna variante condensata**. La larghezza dei
  caratteri è fissa a 0,6 em; i «Nerd Font Propo» non cambiano le lettere.
- **JetBrains Sans** (il carattere proporzionale dell'interfaccia degli IDE JetBrains e di Writerside) **non è distribuibile**: [N, dalla ricerca
  web] in una risposta del personale JetBrains su YouTrack (WRS-2431, ~2024) risulta «non pubblicato come font open source», servito solo dai
  siti JetBrains per Writerside, con l'intenzione di pubblicarlo in futuro, senza data; la pagina di YouTrack non si è lasciata leggere
  direttamente (vuota), quindi la frase non è verificata sul sito e potrebbe essere cambiata. [V] Non esiste su GitHub nel repository ufficiale
  (`JetBrains/JetBrainsMono`, sorgenti e release: solo Mono). Si può quindi **dire «no» finché non lo pubblicano**.
- Parenti a spaziatura variabile con forme simili: Inter (già in uso, sopra), Fira Sans, IBM Plex Sans; un font quasi-proporzionale derivato dallo
  stesso schema è **Iosevka Aile/Etoile** (OFL) [N, non provato].

**I due usi provati** (foto, sezione 5):
1. **Tutta l'interfaccia in JetBrains Mono**: [V] +29 % sui testi veri, +26 % sulla barra, pannello minimo 314 px, barra Impianto da 950 a ~1128 px (senza la striscia di stato).
   Voto di risparmio di spazio 1/5. **No**.
2. **Solo numeri e valori in JetBrains Mono, resto in Inter**: [V] numeri +17 % di larghezza (ma tabellari), colonne allineate; **il costo è nei campi
   a combinazione e nei nomi lunghi** che si troncano; nelle tabelle di tavole e checks (cifre e valori in colonna) è un guadagno di leggibilità
   netto, nei campi di una riga è neutro. Se Daniel vuole l'aspetto JetBrains, **è l'uso giusto**, ma con due paletti: limitato a caselle numeriche,
   tabelle e liste di valori (non ai menu a tendina e ai campi di testo libero), e con Inter con `tnum` come ripiego se non convince.
   Alternativa a costo zero: Inter con `tnum` (+ `zero`), che ottiene metà del vantaggio (allineamento) senza una seconda famiglia né +17 % di larghezza.

## 8. Voti (1 = pessimo, 5 = ottimo)

«Leggibilità» a 13 px dal pannello e dalla barra a 100 % e 200 % (foto offscreen: [N] sulla resa a schermo); «risparmio» = larghezza sui testi
veri e, dove conta, altezza di riga; «condensato» = disponibilità di un condensato che in Qt funziona su Windows **e** Linux (sezione 4);
«cifre» = tabellari disponibili; «copertura» = caratteri usati; «peso e licenza» = KB per i file che servono e licenza; «Lucide» = armonia con le
icone a tratto sottile, arrotondate, di Meridiana [D, dal confronto a occhio delle foto].

| Candidato | Leggibilità | Risparmio | Condensato | Cifre | Copertura | Peso e licenza | Lucide | Giudizio |
|---|---|---|---|---|---|---|---|---|
| **Inter 4.1** (oggi) | 5 | 3 | 1 | 3 (4 con `tnum`) | 4 | 3 (1,2 MB), OFL | 5 | base da tenere |
| Inter + `tnum` | 5 | 3 | 1 | **5** | 4 | uguale | 5 | **sì, quasi gratis** |
| Inter Tight | 4 | 4 (-9 %) | 2 (stesso disegno, non condensato) | 3 (4 con `tnum`) | 4 | 4 (568 KB), OFL | 5 | sì, per i posti stretti con poca differenza |
| Adwaita Sans | 5 | 3 | 1 | 3 | 4 | 4 (859 KB), OFL | 5 | uguale a Inter: nessun motivo |
| Noto Sans | 4 | 3, riga +2 px (2) | 3 (asse, regola sez. 4) | 4 | 5 | **2 (2 MB)**, OFL | 3 | no |
| Open Sans | 4 | 3, riga +2 px (2) | 3 (asse; vero fino a 75) | 4 | 4 | 4 (520 KB), OFL | 3 | no |
| Roboto / Roboto Condensed | 4 | 4 (-9 %; condensato -18 %) | 4 (statico variabile `wght`; `wdth` con regola) | 4 | 4 | 4, OFL | 3 | 2º, ma su Linux il peso con `setWeight` non si applica |
| Roboto Flex | 3 | 4 | 3 | 4 | 4 | 2 (1,7 MB), OFL | 3 | no |
| **IBM Plex Sans** | 4 | 4 (-6 %), riga +1 px | **5 (Condensed statico, -14 %, 111 KB per peso)** | **5** | 4 | 5, OFL (nome riservato) | 3-4 | **sì, per il condensato** |
| Source Sans 3 | 3 (x 0,478: piccola a 13 px) | 4 (-12 %) | 1 | 4 | 4 | 4, OFL | 3 | no |
| Fira Sans / Condensed | 4 | 3 (-4 %), riga **-1 px** (4) | 5 (Condensed statico, -15 %) | 3 (tab. con `tnum`) | 4 | 3 (0,9 MB per i due), OFL | 3 | buona 2ª scelta per il condensato |
| Barlow / Semi Condensed | 3 (x 0,506, forme più «tecniche») | 4 (-9 %; semicond. -19 %) | 5 | 3 | 4 | 5 (105 KB), OFL | 2 | no (il disegno è troppo diverso da Inter) |
| Archivo | 4 | 3, riga **-2 px** (4) | 3 (asse, regola sez. 4; su Linux peso sbagliato) | 3 | 4 | 4, OFL | 3 | no |
| Ubuntu Nerd Font Propo (+ Condensed) | 4 | 4 | 4 (statico) | 4 | 4 | **1** (2,5 MB per peso), UFL | 3 | no |
| **JetBrains Mono ovunque** | 4 | **1** (+29 %) | 1 | 5 | **5** (ha ∥ ⊥ ⋯) | 5 (270 KB per peso), OFL | 3 | **no** |
| **Inter + JetBrains Mono per i valori** | 5 (valori: 5) | 2 (valori +17 %) | 1 | **5** | 5 | 4, OFL | 4 | **sì, se vuole l'aspetto** |
| Inter con spaziatura -0,2 / -0,4 px | 4 / 3 | 4 / 5 (-3 / -6 %) | 1 | 3 | 4 | uguale | 5 | -0,2 px possibile dove stretto, -0,4 no |
| Nerd Font (qualunque) per l'interfaccia | = al font base | = al base | = | = | = | **1** | = | **no** |

Note ai voti: per Inter con spaziatura ridotta [V] la riduzione vale 3 % a -0,2 px e 6 % a -0,4 px, uguale per tutti i testi (è additiva per carattere); a 13 px
**-0,4 px comincia a far toccare le lettere** (guardare «rn», «il», «ti» nella foto «inter-ls»); [D] la foto 200 % è più indulgente di Windows a 100 %.
Il passaggio da solo a `tnum` è, nel mio giudizio, il guadagno più alto per costo più basso.

## 9. Raccomandazione

La decisione è di Daniel. Io farei, in quest'ordine:

1. **Restare con Inter 4.1** come carattere del programma (R95/R123). Nessun altro candidato proporzionale è chiaramente più leggibile a 13 px
   né più stretto senza condensare, e Inter è il più vicino a ciò che di JetBrains Mono e di Lucciola piace (sez. 1 e 7).
2. **Cifre tabellari su tutti i numeri** (`QFont.setFeature(QFont.Tag("tnum"), 1)`, e se piace `zero`), in `design.font()` o nelle `Text` che mostrano
   valori (tabelle, caselle numeriche, Verifiche, risultati, grafici di testo): +2 % di larghezza sui numeri, colonne allineate. [V] funziona in Qt su Windows e Linux.
3. **Il condensato solo in questi posti**, con **IBM Plex Sans Condensed** (statico Regular e SemiBold, 218 KB, OFL; -14 % di larghezza, riga
   +1 px) o, se non piace un secondo carattere, **Inter Tight** (-9 %, stesso disegno):
   - i **bottoni con parole delle barre** (la barra Impianto passa da 950 a ~860 px: il modo «parole» regge a larghezze più basse, cioè più
     spesso senza ripiegare sulle icone) [V dalle foto];
   - le **linguette delle fasi** (la riga delle fasi chiede 788 px, studio 27) e i **titoli dei pannelli** a destra e a sinistra;
   - le **etichette dei form nel pannello Proprietà stretto** (≤ 300 px) e le **intestazioni di colonna** delle tabelle fitte (Verifiche, elenchi di stringhe);
   - **non** nel testo corrente, nei messaggi, nelle voci di menu, nei campi di testo, nella relazione né nel manuale.
4. **Se Daniel vuole l'aspetto di JetBrains Mono** (valori): JetBrains Mono (statico, 270 KB) solo per caselle numeriche, tabelle e liste di valori; mai per i
   campi a elenco e per i nomi.
5. **Non** adottare i Nerd Fonts, **né** tutto il programma in JetBrains Mono, **né** un font a asse `wdth` per tutto il programma, **né** la spaziatura -0,4 px.
   Aspettare «JetBrains Sans» se mai uscirà con licenza libera.
6. **Prima di decidere: una foto su schermo vero** (Windows 200 % e Linux) dei tre candidati (Inter con `tnum`, Inter + Plex Condensed, Inter + JetBrains Mono per
   i valori), cosa che l'offscreen non può dare.

## 10. Costo stimato e rischi

Costo (ore di lavoro, stima mia [D], da confermare con un piccolo prototipo):
- **Cifre tabellari**: 0,5-1 h per mettere `tnum` nella funzione `design.font()`/`text_font()` e in un test che controlla l'allineamento; 1 h per cercare i punti
  dove `QFont` viene creato fuori da `design` (grafici, delegati, `setStyleSheet`). Dove un font sia dato in un foglio di stile, la feature non c'è: da verificare.
- **Condensato statico (Plex Condensed)**: 218 KB di file in `data/fonts/ibm-plex-sans-condensed` con la sua `OFL.txt` e il README del tipo di quello di Inter,
  `FONT_FILES` e `FONT_WEIGHTS` in `ui/theme.py`, `load_fonts()` che carica anche questi (oggi carica solo la famiglia Inter e tiene la prima famiglia), una
  `Text` nuova nel catalogo `design.Text` (es. `Text.CONTROL_NARROW`, `BAR_NARROW`) con la famiglia condensata, e applicarla nei 4-5 punti (barre,
  linguette, titoli, etichette del pannello, intestazioni). Circa **4-6 h**; più **3-5 h** per i controlli di layout sotto.
- **Controlli di layout**: le soglie che dipendono dal testo (il modo parole/icone `_fit_bars`, `LOW_WINDOW`, la riga delle fasi 788 px, i form del pannello
  che passano da etichetta sopra a etichetta accanto) sono misurate sulla larghezza del testo: con un testo più stretto **cambiano**, a volte in meglio
  (più parole nella barra), a volte no (foto con Fira e Noto: il menu a tendina si tronca perché l'etichetta passa accanto). Servono: rivedere le soglie dello
  studio 27, e una prova di `sizeHint` a pannello stretto con il nuovo font; **tests/finestra/test_glyphs.py** (legge il file Inter), `tests/_setup.py`,
  **`tests/nucleo/test_report_typst.py`** (famiglie ammesse nel PDF: «Titillium Web» e «Inter»), il CI Windows (`.github/workflows/test.yml` riga 147, cerca
  `share\fonts\inter\Inter-Regular.ttf`), `build-aux/windows/meridiana.spec` e il Flatpak (copiano tutto `data/fonts`, già a posto).
- **Il modello Qt (`qt-app-template`)**: [N, solo letto l'elenco] `src/qtkit/theme.py`, `design.py`, `gallery.py`, `data/fonts/inter` (con i test `test_looks.py` e
  `test_style_sheet.py`) e `docs/sistema-grafico.md` parlano di Inter. Il coordinatore porta nel modello: la funzione del condensato (una `Text` stretta),
  `tnum` nelle `Text` numeriche, il caricamento di una seconda famiglia, e la regola dell'asse (sezione 4, punto 4).
- **Totale** per la raccomandazione (3 + eventuale 4): circa **10-14 h** con le prove.
- **Un font variabile con asse `wdth`** (alternativa che non consiglio): +2 h per scrivere gli assi in `design.font()` e +2-3 h per togliere i `font-weight` dai
  fogli di stile dei widget interessati (14 occorrenze di `font-weight` nei `.py`), più il rischio di vedere sparire il condensato su Linux dopo un
  aggiornamento di Qt.

Rischi:
- **Resa a schermo non vista** (ClearType, hinting a 13 px): un secondo carattere nei bottoni stretti può essere meno nitido di Inter; Plex Condensed a 13 px
  ha la x bassa (0,516). Da vedere sullo schermo.
- **Mescolare due famiglie**: nei bottoni stretti il condensato è un secondo carattere; nelle foto regge (Plex Condensed accanto a Inter), ma una barra con
  alcuni bottoni condensati e altri no può sembrare incoerente: applicarlo a tutta la barra o a niente.
- **Font variabile su Linux**: vedi sezione 4 (peso perso, `wdth` perso, Archivo a semigrassetto): per questo propongo file statici.
- **Il nome riservato di Plex** vieta di rinominare una versione modificata (non serve) e di distribuire un sottoinsieme rinominato: usare i file come sono.
- **La relazione (Typst)**: il PDF usa Inter e Titillium Web (`report_typst/engine.py`): se Inter resta, nulla; se si cambia carattere, anche i PDF e la prova del
  test vanno rifatti.
- **Metrics della riga**: Noto e Open Sans +2 px per riga: eventuali altezze fisse a 26-28 px per le righe delle liste non reggono; non li consiglio per questo.

## 11. Non fatto, limiti

- [N] Resa a schermo vero (Windows 100 % e 200 %, Linux). [N] Qt Quick e le viste 3D (non disegnano offscreen). [N] La relazione PDF con un altro carattere.
- [N] Non ho provato `zero` e `ss02` di Inter in Qt, né Iosevka Aile, né Ubuntu Sans Nerd.
- [V] Nessun file del programma toccato; i file scaricati sono in `scratchpad\font\dl\` (fuori dal repository) e non sono stati aggiunti a git.
  Su Lucciola ho usato una cartella mia `~/tmp-font-claude` (font di prova e script, nessuna finestra, nulla chiuso): **da cancellare**; l'ho lasciata perché è
  una cartella di prova, ma Daniel decide se tenerla.

## 12. Come rifare

```
# misure (dalla cartella dei prove; Windows, PySide6 6.12)
python measure.py misure.json ; python tabella.py misure.json
# foto: dalla radice del repository, ambiente dei test, con i font scaricati in scratchpad\font\dl
./run_photo.sh <variante> <1|2> <light|dark>
# bozzetti
python genera.py
```
