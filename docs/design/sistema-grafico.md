# Sistema grafico

Le regole visive di Meridiana in un posto solo, scritte perché valgano anche per altri programmi (Daniel, 24/10/2026:
«dai massima priorità all'armonizzazione estetica e di stile, facendo un ottimo lavoro. L'obiettivo è avere un
template facilmente riutilizzabile per altri programmi»).

- I numeri stanno in `src/meridiana/ui/design.py`: scale chiuse, nessun valore scritto a mano nei componenti.
- I colori stanno nei gettoni del tema (`src/meridiana/theme_colors.py`), ricavati da un accento e da una scelta di
  fondi.
- La galleria `python -m meridiana.ui.gallery [light|dark] [--shot file.png]` mostra tutto su una pagina:
  gettoni, scale e componenti. È il controllo dell'armonia, perché un valore fuori scala si vede lì per primo, ed è
  la vetrina del modello.

## 1. Il principio: schede su un tavolo

La finestra è un **tavolo** (il fondo `window`) su cui stanno **schede** (`panel`), ognuna con un bordo sottile e
nessuna ombra. È la scelta di Daniel fra due prove del 24/10/2026: «vai con niente ombre». Tre piani:

| Piano | Gettone | Cosa ci sta |
|---|---|---|
| Tavolo | `window` | la riga delle fasi, la barra di stato, gli spazi fra le schede |
| Scheda | `panel` | i pannelli (Progetto, Proprietà, Verifiche, Aiuto), la pagina della fase, la pagina File |
| Vista | `view`, `card` | gli elenchi delle finestre di dialogo, le tabelle, i riquadri bianchi |

Regole:

- **Distanze**: le schede stanno a 8 px una dall'altra e dalle barre (`Layout.GAP`), a 12 px dai lati della
  finestra (`Layout.EDGE`).
- **Titolo**: dentro la scheda, a 12 px dal bordo, nello stile `title` (14 px semigrassetto).
- **Niente schede dentro una scheda**: un raggruppamento dentro una scheda è un *gruppo* (§4), non un'altra scheda.
- **Un solo fondo**: il tavolo lo dipinge solo la finestra. Barra dei menu, barra di stato e riga delle fasi sono
  trasparenti. Un fondo dipinto sopra quello della finestra taglia di netto quello che c'è sotto: è il difetto di
  ombre e separatori del 24/10/2026.

## 2. Le scale

### Spaziature (`Space`)

**2, 4, 6, 8, 12, 16, 24, 32**, e niente in mezzo.

| Nome | px | Uso tipico |
|---|---|---|
| XXS | 2 | fra pulsanti di una barra, fra pillole |
| XS | 4 | dentro un controllo, sopra e sotto il testo |
| S | 6 | dentro una scheda, intorno al contenuto (`Layout.PAD`) |
| M | 8 | fra due schede (`Layout.GAP`), testo di un controllo dal bordo (`Line.TEXT_INSET`), fra le righe di un modulo |
| L | 12 | dai lati della finestra (`Layout.EDGE`), titolo di una scheda dal bordo, dentro un riquadro |
| XL | 16 | fra due gruppi di una pagina, dentro un riquadro della pagina File |
| XXL | 24 | intorno a una pagina, altezza della sfumatura di fine contenuto |
| XXXL | 32 | margini delle pagine grandi |

### Raggi (`Radius`), per profondità

| Raggio | Cosa |
|---|---|
| 8 (`CARD`) | scheda, riquadro, pagina, finestrella (menu, elenco a tendina, aiuto a comparsa) |
| 6 (`VIEW`) | vista (pianta, 3D) dentro la sua scheda, a 6 px dal bordo (R77) |
| 6 (`CONTROL`) | pulsante, campo, elenco, gruppo, tabella, pulsante strumento, barra della vista, etichette sopra la pianta |
| 4 (`INNER`) | quello che sta dentro un controllo o una riga: voce di menu, selezione dentro una scheda, pulsantino su una riga, misure accanto al cursore, suggerimenti (Windows li arrotonda a 4) |
| 2 (`MARK`) | campioni di colore, tacche delle legende |
| metà altezza | pillola: gettoni, conteggi, stati, varianti |

### Testo: il catalogo degli stili (`Text`)

### Testo: il catalogo degli stili (`Text`)

Carattere Inter, il testo a 13 px (Daniel, 25/10/2026: 14 px con R95, scelto sul confronto fatto sulla finestra vera al
200 %, cinque caratteri e tre motori di Windows; poi «diminuisci di 1px la dimensione del font. Da 14 a 13», R123).
Titillium Web, usato fino ad allora, a 13 px si leggeva piccolo e sottile: i suoi file restano in
`data/fonts/titillium-web` per un ritorno.

La dimensione del testo si sceglie in Preferenze > Aspetto (R133, Daniel 26/10/2026: «farei 12, 13 e 14 come piccolo,
medio e grande»): Piccolo, Medio (13 px, quella di queste tabelle) e Grande spostano tutta la scala di un pixel in giù o
in su (`design.set_text_size` all'avvio; con la finestra aperta `theme.change_text_size`, subito: ogni testo di un
pixel, una volta sola, anche quelli che la dimensione la prendono dal contenitore). Perché: su uno schermo al
100 % i 13 px del testo sono 13 pixel veri e il testo sembra stretto; al 200 % (il 4K di casa) sono 26 (R171, misurato
sulla finestra vera: stessa larghezza, al pixel, che in Chrome con gli stessi file).

Daniel, 25/10/2026 (R121): «Vedo ancora troppe differenze tra dimensioni testo, stili, colori nelle varie sezioni
(alcune differenze ci devono essere ma non devono essere troppe e devono avere un senso, e devono essere salvate come
stile, tipo i testi nelle linguette sono troppo grandi)». Ogni testo della finestra è uno di questi dieci stili, con
un nome, in `ui/design.py` (`Text`); niente altro. Sei grandezze (11, 12, 13, 14, 18, 22) e due pesi (normale 400,
semigrassetto 600): il grassetto (700) non c'è più, chi lo chiede ha il semigrassetto (`Type.BOLD`), e il «<b>» del
testo ricco diventa semigrassetto (`design.strong`, `design.semibold`, il foglio dei documenti).

| Stile | px | Peso | Colore | Dove |
|---|---|---|---|---|
| `display` | 22 | semigrassetto | `text` | cifra di un risultato, titolo di una pagina (File) e il primo titolo del manuale |
| `heading` | 18 | semigrassetto | `text` | titolo dentro una pagina o una finestra di dialogo (aggiornamento, secondo titolo del manuale) |
| `title` | 14 | semigrassetto | `text` | titolo di una scheda (Progetto, Proprietà, Aiuto, Verifiche), di Meridio, di un riquadro della pagina File, terzo titolo del manuale |
| `strong` | 13 | semigrassetto | `text` | titolo di un gruppo, nome in una riga, soggetto dell'aiuto, titoli dentro un pannello (risultati, consegne, relazione) e di un grafico, parola di un pulsante (anche «File»), nome della fase in mano, ciò che spicca dentro una frase |
| `body` | 13 | normale | `text` | il testo: campi, etichette, elenchi (albero del progetto, Verifiche, tabelle), menu, suggerimenti, aiuto, conversazione con Meridio, voci della pagina File |
| `description` | 13 | normale | `text2` | una frase che spiega sotto un titolo: guida della pagina File, testo dei riquadri File, unità accanto alla cifra |
| `control` | 13 | normale | `text` | linguette (fasi, grafici, schede accorpate, Preferenze), pillole delle varianti, gettoni e conteggi delle Verifiche, pulsanti strumento con la parola accanto, stati delle consegne |
| `secondary` | 12 | normale | `text2` | note sotto i campi, barra di stato, parole sotto gli strumenti, etichetta e dettaglio dei riquadri, titoli degli assi, tasti della pagina File, scala e fonte sulla pianta |
| `caption` | 11 | normale | `muted` | tacche dei grafici, formati dei riquadri File, costo della conversazione |
| `group` | 10 | normale | `muted` | in maiuscolo con spaziatura del 4 %: i nomi dei gruppi della barra della fase, 4 px sotto i comandi (R159: «più leggeri, piccoli, e distanziati») |
| `label` | 11 | semigrassetto | `muted` | in maiuscolo con spaziatura del 4 %: intestazioni delle sezioni (albero, Verifiche, pagina File), numeri nei dischi delle fasi e nei segni, facce del cubo, «N» della pianta, «Domande pronte» di Meridio |

Perché queste differenze:
- **13 il testo e i comandi**: linguette, pillole e pulsanti hanno la grandezza del testo (le linguette a 15
  sembravano troppo grandi); si distinguono per la forma, non per il carattere.
- **14 semigrassetto solo i titoli delle schede**, il primo livello; **13 semigrassetto** (`strong`) il secondo:
  gruppi, righe, titoli dentro un pannello, la parola dei pulsanti.
- **12 il secondario**: ciò che accompagna (note, stato, parole degli strumenti), mai una frase da leggere a lungo.
- **11 solo per le etichette**: le maiuscole a 11 si leggono come i 12 normali; le tacche dei grafici.
- **22 e 18** solo per le cifre dei risultati e i titoli di pagina.
- **I colori del testo sono tre** (`text`, `text2`, `muted`): ogni stile ha il suo, e lo mette il foglio di stile
  con la proprietà `tone` (`design.set_text`).

Le regole:
- **I caratteri li mette il codice**, mai il foglio di stile: `design.set_text(widget, Text.X)` (carattere e colore),
  `design.text_font(Text.X)` per chi disegna da sé. Il foglio non contiene né `font-size` né `font-weight` (lo
  controlla la prova `test_the_sheet_has_the_rules_of_the_surfaces_and_only_the_colours_of_the_tokens`), salvo una
  regola: la barra delle linguette di una `QTabWidget` (grafici, Preferenze) sotto un foglio di stile prende il
  carattere della sua `QTabWidget` qualunque cosa le si dia, a meno che glielo dia il foglio (Qt la tratta da «figlia
  naturale», come ogni widget che si chiama `qt_...`).
- **Le classi di Qt hanno il loro stile** (`theme.class_fonts`): i pulsanti `strong`, linguette e pulsanti strumento
  `control`, intestazioni delle tabelle e barra di stato `secondary`, elenchi, menu, suggerimenti e finestre di
  messaggio `body`. È anche la correzione del difetto per cui l'albero del progetto e le Verifiche sembravano più
  piccoli dell'aiuto: Qt, impostando lo stile, ridava a elenchi, menu, suggerimenti e barra di stato il carattere di
  Windows (Segoe UI 9 pt, 12 px), e lo rifà a ogni `setStyle` (anche il primo foglio di stile ne imposta uno).
- **Il testo ricco** (aiuto, Meridio, manuale): niente `font-size` scritti a mano; i titoli del manuale e delle note
  di versione presi dal catalogo (`help_box.dress`).
- **La prova** `test_every_text_of_the_window_is_a_style_of_the_catalogue` gira tutte le fasi e la pagina File e
  guarda ogni testo, anche quelli che la finestra disegna da sé (titoli delle schede, linguette delle fasi, sezioni,
  segni); restano fuori solo i disegni (pianta e 3D) e il carattere dei segni (✔ ⚠ ✘).


### Misure (`Size`, `Icon`, `Line`)

- **Controlli**: alti 28 px (`Size.CONTROL`) tutti, pulsanti e campi (numeri, elenchi, date compresi), testo a 8 px
  dal bordo, bordo compreso. Prima i pulsanti erano 25, i campi 27, i numeri e le date 30.
- **Pillole**: alte 24 px (`Size.CHIP`); gettoni, conteggi, stati, varianti e linguette.
- **Barre di scorrimento**: 10 px di posto, il cursore largo 6 (`Size.SCROLLBAR`, `Size.THUMB`).
- **Linguette e righe**: linguette delle fasi 36 px (`Size.TAB`); voci di un elenco di posti, come la pagina File,
  34 px (`Size.NAV`).
- **Icone**: 16 in un controllo, 18 in un elenco, 22 in una barra, 24 in un riquadro; tratto 1,7 px, come i bozzetti.
- **Linee**: 1 px per ogni profondità, 2 px per il fuoco con l'accento.

### I tasti (`Button`)

Daniel, 25/10/2026 (R121): «deve includere tutti i tasti». Sei tipi, ciascuno con un'altezza e un raggio:

| Tipo | Alto | Raggio | Testo | Dove |
|---|---|---|---|---|
| `PUSH` pulsante | 28 | 6 | `strong` | i comandi («Calcola», «Esporta…», «OK»); velo `field`; nessuno pieno di accento (R158), nemmeno il `primary`; `destructive` col testo rosso; spento senza velo |
| `TOOL` strumento | 28, o icona 24 e parola | 6 | `secondary` sotto l'icona, `control` accanto | barra della fase, barra della vista, barra del sole, pulsanti della barra di stato |
| `CHIP` pillola | 24 | 12 | `control` | gettoni e conteggi delle Verifiche, «Tabella» dei grafici, pillole delle varianti, linguette dei grafici, delle schede accorpate e delle Preferenze, stati delle consegne |
| `SMALL` piccolo | 20 | 4 | `control` | croce delle schede, puntina e «Sgancia» dell'aiuto, «Correggi» sulle righe delle Verifiche |
| `HELP` «?» | 16 | 8 | `label` | il «?» di un gruppo o di un riquadro |
| `NAV` voce | 34 | 6 | `body` | le voci della pagina File |

Il pulsante «File» è disegnato come le fasi accanto: senza fondo a riposo, lo strato dell'hover sotto il
puntatore, quello del premuto finché la sua pagina è aperta (R158, R160).

### Sotto il puntatore e premuto

Daniel, 25/10/2026 (R160): «L'hover è ancora troppo incongruente ... Deve avere certi roundings, dimensioni e
caratteristiche di delta colore». Una regola sola, in tutti e due i temi:

- **colore**: il colore di riposo del controllo con sopra il colore del testo all'**8 %** sotto il puntatore e al
  **16 %** premuto o acceso (`theme_colors.HOVER`, `PRESS`; gettoni `hover` e `press`). Dove il controllo non ha
  un fondo suo (strumenti, pillole, voci di menu, righe, fasi, «File») lo strato si usa trasparente; dove ce l'ha
  (pulsanti e linguette sul velo `field`, pulsanti dei riquadri sul `panel`) lo si calcola sopra
  (`theme_colors.state`). Nel tema scuro lo strato schiarisce, nel chiaro scurisce: non più il nero sul velo scuro;
- **forma**: quella del controllo, mai un'altra: 28 px e raggio 6 per pulsanti, strumenti, «File» e fasi; 24 px a
  pillola per pillole e linguette dei grafici; la voce di un menu col raggio 4; la riga di un elenco tutta la sua
  forma (la scheda di una verifica, la pillola di 4 px delle sezioni);
- **testo**: non cambia peso; i nomi spenti (fasi, linguette, pillole delle varianti) passano al colore del testo.

### Movimento (`Motion`)

**110 ms** (`FAST`), **130 ms** (`QUICK`), **180 ms** (`NORMAL`) e **240 ms** (`SLOW`), con curva in uscita
(OutCubic). Con «meno movimento», chiesto dal sistema o dalle preferenze, sono zero. `QUICK` è la chiusura del
fumetto di Meridio (Daniel, 25/10/2026: «130 ms»). Meridio scivola al posto nuovo col passo suo, 320 ms, col fumetto
aperto che scivola con lui (R155: a 130 ms era «troppo rapido, meglio com'era prima»); cambiando fase resta dov'è e
si sposta solo quanto basta per non stare sulla barra del sole. Le sue parole compaiono come se le dicesse (R156):
almeno 60 caratteri al secondo, quello che resta da dire detto entro 3 secondi dall'ultimo pezzo arrivato. La camera della
vista 3D va da una vista all'altra in `SLOW`.

Regole del movimento (R83, misurate il 24/10/2026):
- si muove solo una zona piccola: mai l'intera pagina (un fotogramma della pagina costava 23-45 ms, uno
  dell'intestazione e della barra 5-8 ms, sotto i 16 ms dei 60 fotogrammi al secondo);
- mai `QGraphicsOpacityEffect` su zone grandi: ridisegna tutto sotto di sé a ogni fotogramma; si dipingono due
  fotografie con l'opacità del pittore, sotto un velo opaco (`ui/motion.Veil`);
- il movimento parte dopo il lavoro che il cambio chiede alla finestra (il giro successivo del ciclo degli eventi),
  così mostra tutti i fotogrammi; durante quel lavoro il velo tiene ferma l'immagine di prima;
- quello che servirebbe al primo uso (la prima fotografia, la libreria dei grafici) si prepara a finestra ferma
  dopo l'avvio.

## 3. I colori

I gettoni vengono da `theme_colors.derive(accento, scuro, fondi)`; in chiaro e in scuro hanno gli stessi nomi.
I principali:

| Gettone | Ruolo |
|---|---|
| `window`, `panel`, `view`, `card`, `field` | tavolo, scheda, vista, bianco delle tabelle, velo tonale dei controlli |
| `line`, `line_soft`, `card_line` | linea piena (anche il bordo delle schede), linea leggera dentro le schede |
| `text`, `text2`, `muted` | testo, secondario, spento |
| `accent`, `accent_fg`, `accent_hover`, `accent_soft` | il colore scelto: la fase in mano e il fuoco, nessun pulsante pieno (R158) |
| `hover`, `press` | lo strato del testo all'8 % e al 16 %: sotto il puntatore, premuto o acceso (R160) |
| `select_bg`, `select_fg` | selezione in un elenco: un grigio che pende verso la tinta dell'accento (lo strumento acceso e la pillola scelta hanno `press`, R158) |
| `danger`, stati `good`/`warning`/`critical` | errori e semaforo: sempre con un segno o una parola, mai solo col colore |

Regole:

- **L'accento con misura** (R104, Daniel 25/10/2026: «lo vorrei un po' meno presente in tutto Meridiana il colore
  di accento»). Resta dove dice «questa è la cosa in mano»: il disco del numero della fase in mano, l'anello del
  fuoco (2 px), la selezione e il sottocampo sulla pianta e il modulo scelto in 3D (i disegni). Dal 25/10/2026
  (R158: «i pulsanti già evidenziati con il colore di accento non devono esistere, né negli strumenti né altrove
  ... sono brutti») nessun pulsante ne è pieno: né il `primary`, né lo strumento primario della barra, né «File»
  con la sua pagina aperta. Tolto, neutro, anche da: selezione (`select_bg`, ora con croma 0,018 al massimo: era la tinta pallida
  dell'accento), strumenti accesi, linguette e pillole scelte, voce scelta della pagina File, riquadro chiave dei
  risultati (era in `accent_soft`), «Correggi» sulle righe delle Verifiche (era pieno di accento), stato «da
  aggiornare» delle consegne (ora un contorno), passaggio sulla barra della vista e sul cubo, arco dell'attesa,
  collegamenti dell'aiuto (ora nel colore del testo, sottolineati). La prova
  `test_the_accent_of_the_sheet_only_for_what_is_in_hand_and_the_one_action` lo controlla regola per regola,
  `test_the_accent_shows_only_on_the_phase_in_hand_and_the_one_action` sulla finestra disegnata.
- **Solo gettoni**: nessun colore scritto a mano nel foglio di stile. Lo controlla la prova
  `test_the_sheet_has_the_rules_of_the_surfaces_and_only_the_colours_of_the_tokens`.
- **Scuro in scala di grigi**: grigi neutri e più contrastati (24/10/2026).
- **Pianta e 3D**: tengono i loro colori in entrambi i temi (`view_colours.py`, R16).
- **Grafici**: le serie hanno la loro tavolozza validata (D2); l'accento è dell'interfaccia, non dei dati.

## 4. I componenti

| Componente | Dove | Regola |
|---|---|---|
| Scheda di un pannello | `ui/cards.py` (`CardDock`) | fondo `panel`, linea `card_line`, raggio 8, titolo 14 semigrassetto, croce che chiude |
| Pagina della fase | foglio di stile (`#phase-pages`) | come una scheda |
| Pulsante | foglio di stile, `Button.PUSH` | velo `field`, raggio 6, 28 px, stile `strong`; nessuno pieno di accento (R158); `destructive` col testo rosso; sotto il puntatore lo strato `hover` sopra il velo (R160) |
| Pulsante strumento | `ui/phasebar.py`, foglio di stile, `Button.TOOL` | trasparente, raggio 6; `hover` sotto il puntatore, acceso e premuto in `press` (R158, R160) |
| Pillola e linguetta | foglio di stile, `Button.CHIP` | 24 px, estremi tondi, stile `control`; le linguette di ogni barra (grafici, schede accorpate, Preferenze) come le pillole delle schede accorpate: fondo `field`, quella scelta sul fondo della scheda col suo filo |
| Campo (testo, numero, elenco, data) | foglio di stile, `ui/style.pad_fields` | velo `field` senza bordo; bordo `field_line` al passaggio, 2 px di accento col fuoco; frecce piccole e spente; numeri allineati a sinistra |
| Gruppo | `ui/style.py` (`Group`) | cornice `line`, raggio 6, intestazione piena in `line_soft` per tutta la larghezza, «?» sulla riga del titolo |
| Riquadro di un risultato | `ui/energy_pages.Tile` | velo `field` senza bordo, raggio 8; etichetta `secondary`, cifra `display`, unità `description`, dettaglio `secondary`; il riquadro chiave è il primo, senza tinta (R104) |
| Striscia | foglio di stile (`#strip`) | come un riquadro, su una riga |
| Pillola di stato | foglio di stile (`#state-*`) | 24 px, estremi tondi |
| Gettone e conteggio | `ui/checks_page.py` | pillola con bordo, segno a sinistra |
| Selettore a segmenti | `ui/variant_bar.py` | pillole su una pista `field`, la scelta rialzata in `panel` con la linea; «+» per aggiungere; tasto destro per il resto |
| Elenco a sezioni | `ui/sections.py`, `ui/marks.py` | intestazioni maiuscole 11 px con il conteggio, non selezionabili; segni come pillole a destra |
| Schede delle Verifiche | `ui/checks_page.ChecksTree` | le voci di una sezione in una scheda, niente selezione; sotto il puntatore la voce intera col suo dettaglio prende lo strato `hover` (R153, R160); il segno tiene il suo colore anche sulla riga scelta |
| Vista | `ui/cards.round_corners` | a 6 px dal bordo della sua scheda, quattro angoli a raggio 6 disegnati (non a maschera), 6 px fra due viste |
| Barra della vista | `ui/viewbar.py` | soli simboli, nome e tasto nel suggerimento; raggio 6, pulsanti raggio 4 |
| Nord, scala, fonte sulla pianta | `ui/plan_overlays.py` | stile B scelto il 24/10/2026: freccia sottile sotto la N, scala a linea con la lunghezza a destra, ciascuno in un riquadro trasparente al 55 % che lo avvolge con lo stesso margine; raggio 6, testo 12; mai uno sopra l'altro |
| Riga delle fasi | `ui/phasebar.py` | linguette `control` (13 px), la fase in mano `strong`, con il disco del numero in `label`; sotto il puntatore un fondo `hover` di 28 px e raggio 6 come «File» (R160); la linguetta scelta e la scheda della barra sono una forma sola, unite da due angoli inversi del raggio delle schede (R84, come le linguette di GNOME); al cambio di fase la linguetta scorre fino alla nuova in 240 ms |
| Pulsante «File» e pagina File | `ui/phasebar.py`, `ui/file_page.py` | a sinistra delle fasi e disegnato come loro: senza fondo, `hover` sotto il puntatore, `press` con la pagina aperta (R158, R160); la pagina è una scheda con l'elenco dei posti a sinistra (`body`) e riquadri a destra (`title` e `description`) |
| Barra dei menu | `ui/menubar.py` | nascosta: Alt la aggiunge al suo posto sopra la riga delle fasi e il resto della finestra scende per farle posto, e risale quando va via (R164, `motion.push`, 180 ms; la barra di stato resta ferma); Vista > Barra dei menu la tiene sempre |
| Pulsanti delle schede | `ui/panel_buttons.py` | nella barra di stato, un'icona per scheda: piena se si vede, spenta se chiusa o coperta |
| Aiuto | `ui/help_box.py` | scheda sotto Proprietà; il testo occupa lo spazio che c'è; un «?» o F1 lo blocca sull'argomento (puntina accanto al titolo), «Sgancia» lo mette in una finestrella sua (R44, R68) |
| Elenco a righe | `ui/rows.RowList` | al posto di una tabella da leggere: nome a sinistra in semigrassetto, cosa è a destra in `text2`, una linea leggera fra due righe; alto quanto le righe, scorre con la scheda |
| Griglia di campi | `ui/rows.FieldGrid` | al posto di una tabella da scrivere (le bollette): i campi numerici normali in righe e colonne, i nomi a sinistra e in alto, il totale di ogni colonna; Tab da uno all'altro |
| Meridio | `ui/assistant.py` | il fumetto scivola di 10 px dalla sua parte e si accende; nome `title`, conversazione `body`, «Domande pronte» `label` |
| Barra di scorrimento | `ui/scrollbars.py` (`ScrollStyle`) | un cursore di 6 px, raggio 3, `line` a riposo, `muted` sotto il puntatore, `text2` premuto; nessuna guida, nessuna freccia; niente se non c'è da scorrere |

## 5. I comportamenti

- **Fine morbida** (`ui/fades.py`): quando un elenco o una pagina continua oltre la scheda, l'ultimo pezzo sfuma nel
  colore della scheda invece di tagliarsi. La sfumatura è alta 16 px (al massimo un quinto dell'area), piena sul
  bordo e subito più leggera, dentro la linea e gli angoli tondi della scheda (R161: a 24 px e piena era «troppo accentuata» su uno
  schermo piccolo e scuro, e passava sopra il bordo), e compare solo dal lato dove c'è altro. Daniel,
  24/10/2026: «carina la semplice sfumatura… mantienila come stile». Vale per ogni area che scorre dentro una scheda.
  Nelle pagine e nei pannelli ciò che scorre si ferma 8 px prima delle linee in alto e in basso della scheda
  (`fades.attach(area, air=True)`, `fades.AIR`), e la sfumatura sta sul bordo del contenuto: R177, Daniel
  26/10/2026, «i contenuti ... arrivano fino al limite della scheda sfondandolo» (all'85 % sul bordo, e senza
  aria, quello che c'era sotto arrivava fino alla linea). Gli elenchi no: il loro margine in alto è quello
  dell'intestazione.
- **Finestrelle** (`ui/popups.py`): suggerimenti, menu, elenchi a tendina e aiuto a comparsa entrano sfumando in
  110 ms; gli effetti di Qt, che a 200 % scattano, sono spenti. Su Windows 11 il sistema li arrotonda e disegna la
  loro ombra e il bordo nel colore `line`; altrove il foglio di stile disegna lo stesso bordo e, per i suggerimenti,
  gli stessi angoli di 4 px su una finestrella trasparente intorno.
- **Suggerimenti** (R162, Daniel 25/10/2026: «una larghezza massima in cui il testo va in colonna ... una bella
  formattazione ai contenuti come fanno programmi tipo VS Code»): «Nome (tasto)» sulla prima riga e la spiegazione
  sotto diventano il nome (semigrassetto se segue una spiegazione), il tasto attenuato accanto, la spiegazione in
  un inchiostro più tenue 4 px sotto; a capo a 340 px; 6 px sopra e sotto e 8 ai lati (una riga: 28 px, come un
  controllo). Vale per ogni suggerimento, da dovunque venga, perché si formatta l'etichetta di Qt quando compare.
- **Pagina File** (R157, riveduta con R178): entra in 180 ms con una dissolvenza e uno scorrimento di 16 px dal
  lato del menu (`ui/motion.enter`, `Entrance`). Il velo opaco tiene la fotografia di prima e dipinge quella della
  pagina: niente `QGraphicsOpacityEffect`, maschere o ridisposizioni ai fotogrammi. Con «meno movimento» la pagina è
  subito presente; si chiude subito. Le alternative fotografate sono il foglio che si scopre da sinistra e la sola
  dissolvenza, alla stessa durata.
- **Cambio di fase** (`ui/phasebar.Phases._changed`, come la barra multifunzione di Office): la pagina e gli
  strumenti della barra cambiano subito; scorre soltanto la linguetta scelta, fino alla nuova fase (110 ms, R97). Gli
  strumenti che entravano scorrendo sfarfallavano (Daniel, 24/10/2026): niente movimento dentro una barra piena di
  controlli.
- **Cambio di argomento** (`ui/motion.crossfade`): l'argomento delle Proprietà sfuma nel successivo in 180 ms; lo
  stesso argomento rifatto (un valore cambiato) non sfuma.
- **Righe espandibili** (le Verifiche): si aprono subito, senza l'animazione di Qt (lenta, e spostava l'elenco);
  la freccia apre e chiude soltanto, senza prendere la riga né muovere le viste; il dettaglio sta sul fondo della
  scheda, attenuato e un punto più piccolo, sotto il testo della riga, come le righe espandibili di libadwaita.
- **Separatori**: fra due schede nessun segno; il puntatore a doppia freccia dice dove si ridimensiona (Daniel,
  25/10/2026, R113: la linea tratteggiata del 24/10 tolta, «sono proprio brutte»).
- **Viste**: angoli disegnati nel colore della scheda; le etichette sopra la pianta stanno a 8 px dai bordi.
- **Moduli dentro la scheda** (`ui/style.pad_fields`): in una scheda che scorre nessun campo allarga la colonna
  oltre il bordo. Gli elenchi a tendina si accorciano (il testo intero nel suggerimento e nell'elenco aperto), le
  etichette lunghe vanno a capo, una pila di pagine prende la misura della pagina mostrata, il campo passa sotto la
  sua etichetta quando non ci sta accanto, il titolo lungo di un gruppo si accorcia con «...» invece di allargarlo
  (25/10/2026: «Energia acquistata (tutti i costi variabili, imposte comprese)» spingeva i campi del Bilancio oltre la
  scheda), due pulsanti che non ci stanno affiancati vanno uno sotto l'altro. Prima i contenuti uscivano dalla
  colonna Dati (24/10/2026).
- **Rotella**: cambia un numero o una scelta solo nel campo che ha la tastiera; altrimenti fa scorrere la scheda
  (`ui/wheel.py`).
- **Barre di scorrimento** (`ui/scrollbars.py`, R100; Daniel, 25/10/2026: «Le varie barre di scorrimento, quando
  compaiono, spostano tutti i contenuti in modo fastidioso. Forse deve occupare meno spazio e avere spazio già
  assegnato?»). Ogni elenco, modulo e testo da leggere tiene a destra il posto della barra (10 px) anche quando non
  scorre: la barra c'è sempre, disegnata vuota finché non serve; così quando compare, o quando un ridimensionamento
  la fa comparire, nulla si sposta. Il cursore è sottile (6 px) e senza guida. Non la tengono la pianta (si sposta
  col mouse), gli elenchi delle finestrelle (si misurano da sé) e i campi in cui si scrive.
  Provate e scartate il 25/10/2026 le barre «transitorie» di Qt, sopra il contenuto come in VS Code: il foglio di
  stile le spegne appena una sua regola tocca la barra; disegnate dallo stile, coprivano la fine delle righe (i segni
  dell'albero, «Correggi» delle Verifiche) e ne prendevano i clic; e gli alberi rifanno da sé i margini della loro
  vista, quindi non si poteva tenere loro un posto accanto.
  Il posto: la barra sta a 6 px dal bordo destro della sua scheda, in ogni scheda (nessun margine proprio a
  destra di ciò che scorre), e il cursore non va oltre 8 px dalle estremità (`scrollbars.END = Radius.CARD`),
  fuori dagli angoli tondi: R182, Daniel 26/10/2026, «mi piace di più la versione più attaccata al bordo destro
  della scheda ... anche se non deve sforare sopra e sotto».

## 6. Cosa non si fa

- Ombre sotto le schede (prova A del 24/10/2026, scartata).
- Tabelle vere dentro le schede (R79): rotella e frecce passano alla scheda ai bordi, i contenuti escono. Un elenco
  di cose si mostra come righe o riquadri; i valori da scrivere come campi di un modulo.
- Colori scritti a mano; misure fuori scala; testo sotto 10 px.
- Testo sopra un'immagine senza fondo; parole semitrasparenti (si leggono sfocate, come era il cubo della vista).
- Più di un pulsante pieno di accento per pagina.
- Effetti di Qt per menu e suggerimenti, e maschere per arrotondare (gradini).

## 7. Riusarlo in un altro programma

I moduli generici, che non sanno niente di fotovoltaico:

| Modulo | Cosa porta | Dipende da |
|---|---|---|
| `ui/design.py` | le scale, il catalogo dei testi (`Text`), i tipi di tasti (`Button`) | niente (Qt solo per `font`, `text_font`, `set_text`) |
| `theme_colors.py` | i gettoni da un accento, contrasti verificati | niente |
| `ui/theme.py` | tavolozza, foglio di stile, caratteri e loro stili per classe, accento del sistema | `paths` (i file dei caratteri), `i18n` |
| `ui/scrollbars.py` | lo stile dell'applicazione: Fusion con le barre di scorrimento sottili che tengono il loro posto | `design` |
| `ui/style.py` | gruppi, menu senza sottolineature, testo dei campi | `design` |
| `ui/cards.py` | schede dei pannelli, distanze, angoli delle viste | `design`, `theme_colors` |
| `ui/popups.py`, `ui/fades.py`, `ui/motion.py`, `ui/separators.py` | i comportamenti del §5 | `design` |
| `ui/menubar.py`, `ui/panel_buttons.py`, `ui/variant_bar.py` | barra dei menu ad Alt, pulsanti delle schede, selettore a segmenti | `design`, `icons` |
| `ui/day_picker.py` | il calendario dei campi data: un fondo solo, giorno scelto neutro, oggi in un anello | `design`, `icons` |
| `ui/icons.py` | icone Lucide (ISC) e proprie, nel colore del tema | `paths` |
| `ui/sections.py`, `ui/marks.py` | elenchi a sezioni con i segni | `design` |
| `ui/rows.py` | elenco a righe e griglia di campi al posto delle tabelle | `design` |
| `ui/phasebar.py`, `ui/file_page.py` | riga delle fasi con la barra; pagina File | il contenuto viene dal programma (`phases.py`, i comandi) |
| `ui/gallery.py` | la vetrina | tutti i precedenti |

Passi per un programma nuovo:

1. copiare i moduli della tabella, i caratteri (`data/fonts/inter`, OFL) e le icone (`data/icons`);
2. all'avvio creare `Theme(cfg)` prima della finestra: tavolozza, foglio di stile, caratteri, finestrelle e
   movimento;
3. fare della finestra un tavolo di `CardDock` con `keep_gaps`, le viste con `round_corners`, le aree che scorrono con
   `fades.attach`;
4. prendere ogni misura da `design.py` e ogni colore dai gettoni;
5. controllare con la galleria in chiaro e in scuro.

Il modello a sé esiste dal 24/10/2026: `%USERPROFILE%\dev\qt-app-template`, pacchetto `qtkit`, con la galleria e
una finestra d'esempio. Il 25/10/2026 (R122) vi sono stati portati il catalogo dei testi, i tipi di tasti, le barre
di scorrimento, il calendario, i campi data e il cursore, le pillole delle schede accorpate e la minore presenza
dell'accento; la provenienza commit per commit è nel suo `docs/da-dove-viene.md`.
