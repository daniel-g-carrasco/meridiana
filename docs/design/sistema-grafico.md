# Sistema grafico

Le regole visive di Meridiana in un posto solo, scritte perché valgano anche per altri programmi (Daniel, 24/10/2026:
«dai massima priorità all'armonizzazione estetica e di stile, facendo un ottimo lavoro. L'obiettivo è avere un
template facilmente riutilizzabile per altri programmi»).

- I numeri stanno in `src/meridiana/gui/style/design.py`: scale chiuse, nessun valore scritto a mano nei componenti.
- I colori stanno nei gettoni del tema (`src/meridiana/app/interface/theme_colors.py`), ricavati da un accento e da una scelta di
  fondi.
- La galleria `python -m meridiana.gui.gallery [--theme light|dark] [--shot file.png]` mostra tutto su una pagina:
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
| XXS | 2 | fra pulsanti di una barra, la pista intorno ai segmenti |
| XS | 4 | dentro un controllo, sopra e sotto il testo |
| S | 6 | dentro una scheda, intorno al contenuto (`Layout.PAD`) |
| M | 8 | fra due schede (`Layout.GAP`), testo di un controllo dal bordo (`Line.TEXT_INSET`), fra le righe di un modulo |
| L | 12 | dai lati della finestra (`Layout.EDGE`), titolo di una scheda dal bordo, dentro un riquadro |
| XL | 16 | fra due gruppi di una pagina, dentro un riquadro della pagina File |
| XXL | 24 | intorno a una pagina |
| XXXL | 32 | margini delle pagine grandi |

### Raggi (`Radius`), per profondità

| Raggio | Cosa |
|---|---|
| 8 (`CARD`) | scheda, riquadro, pagina, finestrella (menu, elenco a tendina, aiuto a comparsa) |
| 6 (`VIEW`) | vista (pianta, 3D) dentro la sua scheda, a 6 px dal bordo (R77) |
| 6 (`CONTROL`) | pulsante, campo, elenco, gruppo, tabella, pulsante strumento, barra della vista, etichette sopra la pianta |
| 4 (`INNER`) | quello che sta dentro un controllo o una riga: voce di menu, selezione dentro una scheda, pulsantino su una riga, misure accanto al cursore (i suggerimenti dal 14/11/2026 hanno il raggio dei menu, `CARD`, R615) |
| 2 (`MARK`) | campioni di colore, tacche delle legende |

### Testo: il catalogo degli stili (`Text`)

### Testo: il catalogo degli stili (`Text`)

Carattere Inter, il testo a 13 px (Daniel, 25/10/2026: 14 px con R95, scelto sul confronto fatto sulla finestra vera al
200 %, cinque caratteri e tre motori di Windows; poi «diminuisci di 1px la dimensione del font. Da 14 a 13», R123).
Titillium Web, usato fino ad allora, a 13 px si leggeva piccolo e sottile: i suoi file restano in
`data/fonts/titillium-web` per un ritorno.

La dimensione del testo si sceglie in File > Impostazioni > Aspetto (R133, Daniel 26/10/2026: «farei 12, 13 e 14 come piccolo,
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
| `control` | 13 | normale | `text` | linguette (fasi, grafici e schede accorpate), segmenti delle piste (varianti, viste e filtri delle Verifiche), pulsanti strumento con la parola accanto, stati delle consegne |
| `secondary` | 12 | normale | `text2` | note sotto i campi, barra di stato, parole sotto gli strumenti, etichetta e dettaglio dei riquadri, titoli degli assi, tasti della pagina File, scala e fonte sulla pianta |
| `caption` | 11 | normale | `muted` | tacche dei grafici, formati dei riquadri File, costo della conversazione |
| `group` | 10 | normale | `muted` | in maiuscolo con spaziatura del 4 %: i nomi dei gruppi della barra della fase, 4 px sotto i comandi (R159: «più leggeri, piccoli, e distanziati») |
| `label` | 11 | semigrassetto | `muted` | in maiuscolo con spaziatura del 4 %: intestazioni delle sezioni (albero, Verifiche, pagina File), numeri nei dischi delle fasi e nei segni, facce del cubo, «N» della pianta, «Domande pronte» di Meridio |

Perché queste differenze:
- **13 il testo e i comandi**: linguette, segmenti e pulsanti hanno la grandezza del testo (le linguette a 15
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
  segni); restano fuori solo i disegni (pianta e 3D); i segni di stato sono i simboli (§4), mai caratteri.


### Misure (`Size`, `Icon`, `Line`)

- **Controlli**: alti 28 px (`Size.CONTROL`) tutti, pulsanti e campi (numeri, elenchi, date compresi), testo a 8 px
  dal bordo, bordo compreso. Prima i pulsanti erano 25, i campi 27, i numeri e le date 30.
- **Segmenti**: alti 24 px (`Size.CHIP`) su una pista di 28 (2 px intorno, `ui/segments.py`); anche gli stati delle consegne sono alti 24. Nessuna forma ha gli estremi tondi (R322, R328, Daniel 02/11/2026: «tutti i tasti devono essere portati su questo stile di rettangolo con angoli arrotondati, anziché su quello di rettangoli con due cerchi alle estremità»).
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
| `CHIP` | 24 | 6 | `control` | un pulsantino con la parola: i passi del tour. Le scelte fra viste non sono pulsanti: sono segmenti su una pista (`ui/segments.py`) |
| `SMALL` piccolo | 20 | 4 | `control` | croce delle schede, puntina e «Sgancia» dell'aiuto, «Correggi» sulle righe delle Verifiche |
| `HELP` «?» | 16 | 8 | `label` | il «?» di un gruppo o di un riquadro |
| `NAV` voce | 34 | 6 | `body` | le voci della pagina File |

Quick (R671, 16/11/2026): un comando compatto a sola icona usa `Controls/Button.qml`, `flat: true`,
`compact: true`, senza un fondo locale: quadrato `Theme.size.CHIP` (24), raggio `Theme.radius.CONTROL`,
icona nel colore del testo, stessi veli al passaggio, premuto e acceso e stesso anello del fuoco.
L'occhio delle Verifiche segue questa regola; il margine destro è `Theme.space.M`.
Il titolo della verifica resta `body` anche quando è correlata, aperta o evidenziata; la selezione colora il fondo
stesso della riga (`select_bg`), senza un rettangolo rientrato che lasci scoperti i bordi.

#### I pulsanti della barra della fase (`Bar`, R333)

Daniel, 03/11/2026: «armonizzare le dimensioni dei tasti, renderli più congruenti tra loro». Tre modi della barra (quale, lo
decide `arrangement.py`, R334), in ciascuno una sola altezza e una sola icona per tutti i pulsanti di tutte le fasi:

| Modo | Pulsante alto | Icona | Largo | Barra | Titolini |
|---|---|---|---|---|---|
| `UNDER` parola sotto | icona, riga della parola, 10 (50 a testo medio) | 24 | a passi di 16, minimo 48 | 69 | sì |
| `BESIDE` parola accanto | 28 | 16 | a passi di 8 | 31 | no |
| `ICONS` sola icona | 28 | 22 | sempre 32 | 47 | sì |

- **La regola delle larghezze**: la più piccola larghezza del passo che tiene la parola più `Bar.PAD`. Non una larghezza per
  parola: in italiano quattro larghezze sotto l'icona (48, 64, 80, più 96 e 112 per le parole lunghe), le stesse nella stessa
  posizione del gruppo. Il passo è più fine con la parola accanto, dove la parola è solo una parte del pulsante.
- **Il pulsante diviso** è il pulsante semplice più la striscia: la parte comando è il pulsante semplice
  (`PhaseToolButton`) e segue la regola sulla **parola più lunga fra quelle che possono andare sulla faccia**: la sua e
  quelle dei modi del suo menu (la barra non si muove quando la faccia cambia); i comandi una tantum («Togli tutte le
  misure») e le voci di un pulsante fisso stanno nel menu e non allargano il pulsante (R614, 14/11/2026: «Misura» era largo
  il doppio di «Squadra»). La striscia è `Bar.STRIP`, 14, alta tutto il pulsante, in tutti i modi.
- **Il contenuto sta in mezzo** (R614), sotto e accanto all'icona: l'aria che lascia il passo è uguale prima della parola
  e dopo, fino al bordo o alla striscia.
- Fra due pulsanti di un gruppo `Bar.GAP` (2). Fra due gruppi un filo alto quanto i pulsanti, con `Bar.GROUP_AIR` (8) per parte.
- Il pulsante primario della fase (Posa, Calcola): velo `field` e parola `strong`, nessun accento; spento senza velo.

**Il pulsante diviso** (`ui/phasebar.ToolMenuButton`, studio 26, G2): comando e striscia con il chevron, ciascuno col suo stato
(passaggio, premuto, spento). Quick (R644, variante 2 scelta da Daniel il 16/11/2026, «ci sta la 2»): un fondo solo, `Controls/SplitGround.qml`, per `SplitButton` e `PhaseSplitButton`; acceso, tutto il pulsante è acceso con gli angoli tondi solo all'esterno, in due toni senza filo: la metà del comando in `press`, quella della striscia un gradino meno (`hover`), e il cambio di tono a tutta altezza fa da divisore; il puntatore sul comando gli aggiunge lo strato `hover`, sulla striscia la porta sopra il comando (`hover` + `press`), il menu aperto ancora di più (`press` due volte), così le due metà non hanno mai lo stesso tono; spento, sotto il puntatore tutto il pulsante in `hover` e la metà sotto il puntatore col suo strato. Con il comando spento la striscia resta viva. La striscia e il
tasto destro aprono il menu con nomi e tasti.
Quick (R674, 16/11/2026): anche mappa di fondo e irraggiamento nella barra della pianta usano `SplitButton`,
con `compact: true`: altezza `ControlMetrics.viewButton` (27), metà comando della stessa larghezza e striscia
`ControlMetrics.viewArrow` (16). Fondo, raggi, freccia e stati restano quelli comuni, senza copie locali.
`commandOpensMenu` conserva il gesto della mappa di fondo; per l'irraggiamento il comando accende o spegne e
la freccia apre il pannello. `Button.menuAnchor` aggancia il menu o pannello all'intero pulsante, anche quando
lo apre la striscia. Il `ViewButton` 3D resta semplice: la variante con freccia, mai usata, è eliminata.
Cosa va sulla faccia:
1. un **modo di disegno** quando si accende, dal menu, con il suo tasto o da altrove, perché un modo acceso si deve vedere; un
   comando una tantum no;
2. i **distruttivi** mai (`Tool.fixed`): quello acceso si vede sulla striscia premuta; «Cancella tutte» (`Tool.danger`) sta in
   fondo, separata, in rosso;
3. **mai da sola**: una voce che si spegne si spegne sulla faccia;
4. un tasto cambia la faccia solo se il comando è un modo (segue dalla 1);
5. la parola cambia con l'icona, nello stesso posto e alla stessa larghezza, con una dissolvenza di `Motion.FAST` (subito con
   «meno movimento»);
6. la faccia dura la sessione: all'avvio torna la voce di base;
7. il suggerimento dice il comando di ora, il tasto e quanti altri ci sono.

Il pulsante «File» è disegnato come le fasi accanto: senza fondo a riposo, lo strato dell'hover sotto il
puntatore, quello del premuto finché la sua pagina è aperta (R158, R160).

### Sotto il puntatore e premuto

Daniel, 25/10/2026 (R160): «L'hover è ancora troppo incongruente ... Deve avere certi roundings, dimensioni e
caratteristiche di delta colore». Una regola sola, in tutti e due i temi:

- **colore**: il colore di riposo del controllo con sopra il colore del testo all'**8 %** sotto il puntatore e al
  **16 %** premuto o acceso (`theme_colors.HOVER`, `PRESS`; gettoni `hover` e `press`). Dove il controllo non ha
  un fondo suo (strumenti, segmenti, voci di menu, righe, fasi, «File») lo strato si usa trasparente; dove ce l'ha
  (pulsanti sul velo `field`, pulsanti dei riquadri sul `panel`) lo si calcola sopra
  (`theme_colors.state`). Nel tema scuro lo strato schiarisce, nel chiaro scurisce: non più il nero sul velo scuro;
- **forma**: quella del controllo, mai un'altra: 28 px e raggio 6 per pulsanti, strumenti, «File» e fasi; 24 px a
  4 per segmenti e linguette dei grafici; la voce di un menu col raggio 4; la riga di un elenco tutta la sua
  forma (la scheda di una verifica, la pillola di 4 px delle sezioni);
- **testo**: non cambia peso; i nomi spenti (fasi, linguette, segmenti) passano al colore del testo.

### Movimento (`Motion`)

**110 ms** (`FAST`), **130 ms** (`QUICK`), **180 ms** (`NORMAL`) e **240 ms** (`SLOW`), con curva in uscita
(OutCubic). Con «meno movimento», chiesto dal sistema o dalle preferenze, sono zero. `QUICK` è la chiusura del
fumetto di Meridio (Daniel, 25/10/2026: «130 ms»). Meridio scivola al posto nuovo col passo suo, 320 ms, col fumetto
aperto che scivola con lui (R155: a 130 ms era «troppo rapido, meglio com'era prima»); cambiando fase resta dov'è e
si sposta solo quanto basta per non stare sulla barra del sole. Le sue parole compaiono come se le dicesse (R156):
almeno 60 caratteri al secondo, quello che resta da dire detto entro 3 secondi dall'ultimo pezzo arrivato. La camera della
vista 3D va da una vista all'altra in `SLOW`.

Cambio di fase in Qt Quick (R640, 16/11/2026):

- Il velo unico resta per File e Impostazioni. Tra le fasi cambiano soltanto i contenuti, con
  `Controls/PhaseFade.qml`: `OpacityAnimator`, durata `Theme.motion.FAST` e curva del tema.
- `Workbench.leavingPhase` conserva la fase uscente per `FAST`, ritirata da una `PauseAnimation`.
  I contenuti uscenti restano disegnati ma perdono subito l'accesso: suggerimenti, menu e pannelli si chiudono
  con la regola comune degli elementi fuori portata. Un cambio rapido conserva soltanto l'ultima coppia.
- I corpi dell'ispettore, le pagine centrali, il banner dell'anno e i gruppi della barra riusano lo stesso
  componente. I fondi e i bordi delle schede non sfumano. Progetto entra ed esce da solo; durante l'uscita
  gli spazi delle altre schede sono congelati, poi il tavolo recupera lo spazio libero.
- Pianta, 3D e albero condivisi tra Modellazione e Impianto conservano gli oggetti e l'opacità, senza
  richiedere aggiornamenti della scena o dell'albero. Le viste sotto le pagine restano allocate e disabilitate.
- Con movimento ridotto il cambio è netto; attivarlo durante una dissolvenza la conclude subito.
  Nessun Timer aggiunto al cambio di fase, nessuna scrittura Python per fotogramma.

Restano valide le regole di R83: animare zone piccole, evitare gli effetti d'opacità dei vecchi Widgets su
zone grandi e preparare il necessario al primo uso mentre la finestra è ferma. Il vecchio velo del cambio
pagina non descrive più le transizioni tra fasi di Qt Quick.

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
| `select_bg`, `select_fg` | selezione in un elenco (anche la verifica aperta dal suo segno nelle Verifiche, R663 del 16/11/2026: prima un filo di 1 px della scala delle evidenziature, R617, che dal vivo non diceva «scelta»; Esc e un clic in un punto vuoto la tolgono, Tab e le frecce la spostano): un grigio che pende verso la tinta dell'accento (lo strumento acceso ha `press`, R158; il segmento scelto è rialzato in `panel` col filo) |
| `danger`, stati `good`/`warning`/`critical` | errori e semaforo: sempre con un segno o una parola, mai solo col colore |

Regole:

- **L'accento con misura** (R104, Daniel 25/10/2026: «lo vorrei un po' meno presente in tutto Meridiana il colore
  di accento»). Resta dove dice «questa è la cosa in mano»: il disco del numero della fase in mano, l'anello del
  fuoco (2 px), la selezione e il sottocampo sulla pianta e il modulo scelto in 3D (i disegni). Dal 25/10/2026
  (R158: «i pulsanti già evidenziati con il colore di accento non devono esistere, né negli strumenti né altrove
  ... sono brutti») nessun pulsante ne è pieno: né il `primary`, né lo strumento primario della barra, né «File»
  con la sua pagina aperta. Tolto, neutro, anche da: selezione (`select_bg`, ora con croma 0,018 al massimo: era la tinta pallida
  dell'accento), strumenti accesi, linguette e segmenti scelti, voce scelta della pagina File, riquadro chiave dei
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
| Contorno d'aggancio | Quick: `Controls/DropOutline.qml` (`M.DropOutline`); Widgets: nessuno | dove cadrà una cosa portata, detto subito (R504, studio 36, proposta 1, come VS Code e AutoCAD): linea d'accento di 2 px (`Line.FOCUS`), velo `accent_soft`, raggio delle schede, niente ombra e niente dentro; compare e sparisce in `FAST` (110 ms), scivola in `FAST` fra due posti mentre si vede, ricompare fermo al suo posto (`show` salta prima di mostrarsi). Il segnaposto tratteggiato della Workbench (`dropZone`) è dello stesso accento e nasce da questo contorno |
| Pagina della fase | foglio di stile (`#phase-pages`) | come una scheda |
| Pulsante | foglio di stile, `Button.PUSH` | velo `field`, raggio 6, 28 px, stile `strong`; nessuno pieno di accento (R158); `destructive` col testo rosso; sotto il puntatore lo strato `hover` sopra il velo (R160) |
| Pulsante strumento | `ui/phasebar.py`, foglio di stile, `Button.TOOL` | trasparente, raggio 6; `hover` sotto il puntatore, acceso e premuto in `press` (R158, R160) |
| Finestra di dialogo | Quick: `Controls/Dialog.qml` (`M.Dialog`), per le finestre di File `Dialogs/DialogWindow.qml`; velo `Controls/ModalVeil.qml`; misure in `ControlMetrics` (`dialogPad`, `dialogGap`, `dialogEdge`, `dialogWidth`) | **una sola finestra** per tutto il programma (R586, Daniel 11/11/2026: «devono essere centralizzate»). Chi la usa dice solo cosa vorrebbe: `implicitWidth` (una di `dialogWidth`, o la sua misura con nome in `dialogSize`) e, se serve, `implicitHeight` (altrimenti quella del contenuto, `fitHeight`); un contenuto che scorre da sé e riempie lo spazio (catalogo, elenco, pagina in `ScrollPage`) lo dice con `bodyScrolls: false` e riceve l'altezza esatta, senza un secondo scorrimento; il contenuto si dichiara dentro (un elemento, che prende la larghezza della finestra). Nessuna finestra imposta `width`, `height`, `x`, `y`, `anchors` o `contentItem` (prova `quick.shell.test_dialoghi_r586.Sources`). La finestra non è mai più grande dello spazio lasciato dalla finestra principale a `dialogEdge` dai lati; se il contenuto è più alto **scorre nel corpo** con la barra nel margine destro e le dissolvenze delle pagine (`EdgeFades`), mentre titolo e pulsanti restano fermi; il campo col fuoco da tastiera resta in vista. Si apre al centro del genitore (la finestra principale, o una vista: `parent`; un posto suo con `homeX`/`homeY`, la stringatura accanto al pannello), **si sposta trascinando il titolo**, non esce da `dialogEdge` e alla riapertura torna al suo posto. Il velo è `ModalVeil` (anche per un `M.Popup` modale): mentre c'è, il tema vela anche la **barra del titolo** dove la colora il programma (`backend/window_frame.py`: Windows 11 con DWM, Wayland con la decorazione di Qt); Windows 10 e le barre del sistema (X11, decorazioni del compositore) restano come sono. I `FileDialog` sono la finestra del sistema e restano fuori |
| Pista di segmenti | `ui/segments.py`: `Segments` (pulsanti), `on_bar` (una `QTabBar`: grafici, schede accorpate) | ogni scelta fra viste (R322, B1): pista `field` di 28 px e raggio 6, segmenti di 24 e raggio 4, testo `control` (tagliato coi puntini se manca lo spazio, il suggerimento lo dice intero); la scelta è un rettangolo in `panel` col filo `line` che **scorre** al segmento nuovo come la linguetta delle fasi (`OutCubic`, `Motion.FAST`, dopo il lavoro del cambio, subito con «riduci animazioni»); frecce sinistra e destra; con la tastiera sopra il filo è d'accento. Non esclusiva (`exclusive=False`: conteggi e filtri delle Verifiche, più d'uno acceso insieme): ogni acceso ha il suo rettangolo, che compare e scompare in dissolvenza |
| Campo (testo, numero, elenco, data) | foglio di stile, `ui/style.pad_fields` | velo `field` senza bordo; bordo `field_line` al passaggio, 2 px di accento col fuoco; frecce piccole e spente; numeri allineati a sinistra ; Quick (R582): `Controls/TextField.qml`, `NumberField.qml`, `ComboBox.qml`, `OverlayField.qml`, una regola in `ControlMetrics`: la riga di testo sta con maiuscole e cifre sul mezzo del campo (`textBaseline`: linea di base a (altezza + altezza delle maiuscole) / 2, su un pixel intero dello schermo), il suggerimento del campo vuoto e l'unità del numero sulla stessa linea di base del testo; il testo parte a `fieldInset` (M + 2) dal bordo sinistro in tutti. Nessuna pagina sposta il testo di un campo per conto suo |
| Frecce: due segni, due significati | Quick: `Controls/Arrow.qml` (`M.Arrow`), `Controls/Chevron.qml` (`M.Chevron`), `Controls/Steppers.qml`; misure in `ControlMetrics` (`arrowDepth`, `chevronBox`, `pixelSnap`) | scelta di Daniel dell'11/11/2026 (R592). **Freccia piena** dove si sceglie un valore: casella a scelta, pulsante con menu (anche la striscia di `SplitButton` e dei pulsanti della fase), sottomenu, passi di un numero (`Steppers`, in `NumberField` e nei numeri delle Proprietà), ordine di una colonna. Righe di pixel interi disegnate dal fornitore (`control:arrow-*`), 7 × 4 a 100 % in un riquadro 8 × 4, chiesta alla misura mostrata e posata su un pixel intero dello schermo: niente pixel a metà a 100, 125, 150, 175 e 200 %. **Freccia aperta** dove si apre o si chiude una sezione: gruppi, sezioni, albero Progetto, albero comune, Verifiche, catalogo, Meridio. È il disegno dell'albero Progetto (`control:chevron-down`, tratto 1,5 sul riquadro di 20), sempre a quella misura anche in un posto più piccolo, girata a destra quando è chiusa. Tutte e due grigie: `muted`, più scure sotto il puntatore o col fuoco (`text2` la piena, `text` l'aperta), il colore del testo spento da disattivate. Nessuna pagina disegna una freccia sua (`quick.controlli.test_frecce_r592`); restano a parte le frecce del calendario del sole (comandi «mese prima/dopo») e quelle del cubo 3D (orientamento) |
| Gruppo | `ui/style.py` (`Group`) | cornice `line`, raggio 6, intestazione piena in `line_soft` per tutta la larghezza, «?» sulla riga del titolo; **richiudibile** (R287, riga sotto) |
| Gruppo dentro un gruppo | `ui/style.py` (`Group.nested`) | a qualunque profondità, anche attraverso una pagina o un'area a scorrimento, non è una scheda (R343, Daniel 03/11/2026: «non mi piacciono le schede dentro le schede»): niente cornice né fascia piena, titolo `strong` su una linea `line` di 1 px per tutta la larghezza, il contenuto sul testo del padre senza margini propri (solo 6 px d'aria sotto la linea). Il chevron resta se è richiudibile, senza fondo: sotto il puntatore si scurisce lui. Regola unica: nessuno la chiede, il gruppo vede dove sta; rimesso fuori torna scheda con i suoi margini. Un titolo non ripete quello del padre: dentro la sezione Inverter gli inverter stanno senza gruppo, il «?» sull'intestazione della sezione |
| Stile dentro un gruppo | `ui/style.py` (`MeridianaStyle`), `ui/scrollbars.py` | lo stile di `Group` è quello dell'applicazione (`ScrollStyle`) con in più i gruppi: col foglio di stile globale Qt passa lo stile di un widget ai figli, e con Fusion puro le aree dentro un gruppo avevano le barre con le frecce (R339) |
| Sezione alta quanto il contenuto | `ui/style.py` (`FitArea`), `ui/plant_page.py` (`PlantSide`) | un'area a scorrimento in una colonna: alta quanto la sua pagina, scorre solo se non ci sta, mai più stretta della pagina; ciò che avanza resta sotto, fuori da ogni cornice (R337). La sezione che si chiude e quella che si apre hanno tempo e curva uguali: un solo movimento, fino all'altezza vera, senza ritorni (R338) |
| Comando lungo in un pannello stretto | `ui/style.py` (`wrap_button`) | le parole vanno su più righe invece di allargare il pannello; il minimo è la parola più lunga (R341) |
| Gruppo richiudibile | `ui/style.py` (`Group`, `_Fold`) | ogni gruppo si chiude e si riapre con un clic sulla sua intestazione (R287, Daniel 30/10/2026: «tutte le sottosezioni nella barra di destra devono poter essere collassate ... con un'animazione armonizzata»). Il segno è un chevron di 10 px nel colore `muted`, col tratto delle icone (1,7 px), prima del titolo: punta in basso aperto, a destra chiuso, e ruota con il movimento; il «?» resta al suo posto a destra. Sotto il puntatore l'intestazione prende lo strato `hover` (8 % del testo su `line_soft`) e il puntatore a mano. Il corpo (i campi, nel layout che il chiamante dà al gruppo come sempre: il gruppo lo sposta in un widget suo) si apre e si chiude in altezza in `Motion.NORMAL` (180 ms, OutCubic): mentre si muove il suo layout è fermo, così i campi vengono tagliati dal bordo del corpo e non schiacciati; aprendosi il corpo è prima disposto alla sua altezza intera e poi scoperto da zero. Chiuso, il gruppo è alto quanto l'intestazione più la linea della cornice: niente buchi, e Tab non entra nei campi nascosti (il corpo è nascosto). Con «meno movimento» si apre e si chiude subito. Lo stato è ricordato per tipo di gruppo (il suo id d'aiuto, altrimenti il titolo) per la sessione: la stessa pagina rifatta, o lo stesso gruppo di un altro oggetto, torna com'era stata lasciata. Un gruppo che non deve chiudersi si chiede con `collapsible=False`. I gruppi delle finestre di dialogo seguono la stessa regola |
| Tabella degli ingressi | `ui/plant_page.py` (`InputsTable`) | nel gruppo Stringhe, un ingresso (MPPT) per riga (R286): stringhe su quante ne prende, moduli in serie, Voc alla temperatura minima su quella massima, Umpp alla cella più calda e più fredda (la finestra MPPT nel suggerimento), Isc su quella dell'ingresso, lo stato come segno (parola e motivi nel suggerimento). Trattamento condiviso delle tabelle (`shared_tables.install`, compatta, senza velature), alta quanto le righe, nessuna barra sua; in un pannello stretto spariscono per prime Isc, poi Umpp, poi Voc, mai oltre il bordo del gruppo. La «stringa scelta» è in tre blocchi con titoli `label` (Identità e percorso, Elettrico, Verifiche), M (8) fra i blocchi e XS (4) fra titolo e testo, una grandezza per riga, le condizioni in `secondary` in fondo |
| Riquadro di un risultato | `ui/energy_pages.Tile`, `Tiles` | velo `field` senza bordo, raggio 8; etichetta `secondary`, cifra `display`, unità `description` sulla stessa linea di base della cifra, dettaglio `secondary`; il riquadro chiave è il primo, senza tinta (R104). Una griglia sola per Producibilità, Consumi, Bilancio ed economia (R309, R310): colonne uguali, tutti alti quanto il più esigente a quella larghezza, almeno due righe di dettaglio; etichetta e dettaglio vanno a capo, la cifra resta sulla sua riga; nessun suggerimento che ripeta l'etichetta |
| Striscia | foglio di stile (`#strip`) | come un riquadro, su una riga |
| Scheda dei grafici e sue sottoschede | `ui/energy_pages.chart_card`, `tab_stack` | una regola per tutte le sottoschede (R284, R285, Daniel 30/10/2026): i segmenti stanno al centro della loro fascia, con M (8) d'aria sopra e sotto (XS della scheda + XS della barra sopra; XS della barra + XS fra barra e filo sotto), la fascia alta 40; sotto il filo il contenuto di ogni sottoscheda, un grafico solo o una pila, parte a M (8), senza margini propri ai lati (li dà la scheda, 8) e in basso (8 della scheda); in una pila i grafici distano L (12), come le parti dei risultati. Prima: 10 sopra e 4 sotto i segmenti; «Bilancio», «Dimensioni» e «Accumulo» coi margini di Qt (11) intorno ai grafici, gli altri a 0 dal filo |
| Riga delle basi del calcolo | `ui/energy_pages.Page.show_basis` | la prima riga dei risultati, prima dei riquadri, in Producibilità, Consumi e Bilancio ed economia (R246, R292): inverter, moduli e batterie davvero nel calcolo, su una riga, a capo solo se la scheda è stretta, il dettaglio nel suggerimento |
| Pillola di stato | foglio di stile (`#state-*`) | 24 px, estremi tondi |
| Conteggio di un livello | `ui/checks_page.CountChip`, `CountRow`, `ui/status_pill.py` (`paint_pill`) | pillola a sé, non su una pista (R335, P3, Daniel 03/11/2026): 24 px, raggio 6, fondo e linea nel tono del livello mescolato al colore della finestra (10 % e 28 %, al buio 17 % e 38 %), segno 12 px col suo colore (`symbols.paint`, l'unico disegno dei segni) a sinistra, numero `label` nel colore del testo a destra; filtro acceso: fondo 19 % (al buio 26 %) e linea 65 %; sotto il puntatore a metà strada; lo zero sbiadito per intero (55 %), al suo posto; focus da tastiera: anello `accent` di 2 px. Le pillole distano S (6). Non si usa nelle righe dell'albero (R328: senza contenitore) |
| Varianti | `ui/variant_bar.py` | la pista di segmenti (R73, R322); «+» e «…» sulla stessa pista; tasto destro per il resto |
| Elenco a sezioni | `ui/sections.py`, `ui/marks.py` | intestazioni maiuscole 11 px con il conteggio, non selezionabili; a destra il segno e il numero, senza contenitore (R328) |
| Testata delle Verifiche | `ui/checks_page.ChecksPage.tools`, `ui/title_tools.py`, `ui/cards.CardTitle.set_tools` | la sola riga di testata (R345, Daniel 03/11/2026): titolo, pista delle viste, conteggi, a destra «Questa fase» e «Questo oggetto», «Copia le note per la relazione» come solo simbolo (20 px, `title-tool`, nome e suggerimento) e la X; strette, le parti vanno a capo ciascuna intera su righe sotto (mai tagliate né sovrapposte), una più larga di una riga si riduce al minimo (le parole delle piste con i puntini); la riga di sintesi sotto la testata c'è solo quando ha qualcosa da dire |
| Schede delle Verifiche | `ui/checks_page.ChecksTree` | le voci di una sezione in una scheda, niente selezione; sotto il puntatore la voce intera col suo dettaglio prende lo strato `hover` (R153, R160); il segno tiene il suo colore anche sulla riga scelta |
| Vista | `ui/cards.round_corners` | a 6 px dal bordo della sua scheda, quattro angoli a raggio 6 disegnati (non a maschera), 6 px fra due viste |
| Barra della vista | `ui/viewbar.py` | soli simboli, nome e tasto nel suggerimento; raggio 6, pulsanti raggio 4; quando la barra larga mostra le parole, «Allinea a un lato» resta un'eccezione a sola icona (R183); «Nord in alto» non ha pulsante, restano N, il segno del nord (R643) e menu del clic destro |
| Segno del nord (pianta, 3D, relazione) | disegno: `app/interface/north_sign.py` (letto dalla finestra con `Theme.signs.north` e dalla relazione in `report/figures.py`); finestra: `Controls/NorthSign.qml`, in pianta `Plan/Compass.qml`, in 3D `View3D/Viewport.qml` | R643 (Daniel 15/11/2026, proposta A dei bozzetti `meridiana-prove/r35-bussola`: «ago a due colori»), al posto del disco con la N e la freccina e dello stile B del 24/10/2026. Un ago a rombo in un riquadro di 100 unità: metà nord piena, metà sud tenue. **Sopra una vista**: disco di `ControlMetrics.northSign` (40 px) nel vetro `overlay.glass`, metà nord in `overlay.ink`, metà sud nello stesso inchiostro al 42 % (`north_sign.SOFT`); la N non c'è, la metà piena è il nord. Nord in alto: niente scritte. Vista ruotata: i gradi («37°», stile `label`, cifre di uguale larghezza) in una pillola di `northPill` (18 px) dello stesso vetro, raggio `CONTROL`, `Space.XS` sotto il disco, mai sulla mappa nuda; puntatore a mano e strato `overlay.hover` sul vetro; clic: nord in alto. Suggerimento con i gradi e l'ottante. In pianta in alto a destra a `Space.M` dai bordi, come prima; in 3D lo stesso segno piatto sullo schermo, sotto il cubo (`Space.S`), girato dove cade il nord della scena (`CubeMath.screenNorth`), clic: la camera guarda verso nord con la stessa altezza. **Sulla carta**: 12 mm (`PAPER_MM`), nero della relazione (`INK`), metà sud bianca col suo contorno di 0,3 mm (regge la fotocopia), «N» 2,8 mm semigrassetto sopra la punta, dritta; in alto a destra della pianta, nord in alto come la pianta stampata |
| Scala, fonte sulla pianta | `Plan/ScaleBar.qml`, `Plan/MapNotice.qml` | scala a linea con la lunghezza a destra, ciascuna in un riquadro di vetro (`overlay.glass`) che la avvolge con lo stesso margine; raggio 6; mai uno sopra l'altro |
| Riga delle fasi | `ui/phasebar.py` | linguette `control` (13 px), la fase in mano `strong`, con il disco del numero in `label`; sotto il puntatore un fondo `hover` di 28 px e raggio 6 come «File» (R160); la linguetta scelta e la scheda della barra sono una forma sola, unite da due angoli inversi del raggio delle schede (R84, come le linguette di GNOME); al cambio di fase la linguetta scorre fino alla nuova in 240 ms |
| Pulsante «File» e pagina File | `ui/phasebar.py`, `ui/file_page.py` | a sinistra delle fasi e disegnato come loro: senza fondo, `hover` sotto il puntatore, `press` con la pagina aperta (R158, R160); la pagina è una scheda con l'elenco dei posti a sinistra (`body`) e riquadri a destra (`title` e `description`) ; Quick (R578): ogni pagina di File e delle Impostazioni, comprese quelle che verranno, è larga al massimo `Layout.PAGE_WIDTH` (760, `Theme.layout.PAGE_WIDTH`) dopo il suo margine (`Layout.PAGE`): un solo valore in `File/FilePage.qml` (`right.pageWidth`) e in `File/FileSection.qml`, le colonne dei riquadri contate su quella larghezza; prova `quick.pagine.test_larghezza_r578` su ogni voce dell'elenco |
| Barra dei menu | `ui/menubar.py` | nascosta: Alt la aggiunge al suo posto sopra la riga delle fasi e il resto della finestra scende per farle posto, e risale quando va via (R164, `motion.push`, 180 ms; la barra di stato resta ferma); Vista > Barra dei menu la tiene sempre |
| Pulsanti delle schede | `ui/panel_buttons.py` | nella barra di stato, un'icona per scheda: piena se si vede, spenta se chiusa o coperta |
| Aiuto | `ui/help_box.py` | scheda sotto Proprietà; il testo occupa lo spazio che c'è; un «?» o F1 lo blocca sull'argomento (puntina accanto al titolo), «Sgancia» lo mette in una finestrella sua (R44, R68) |
| Elenco a righe | `ui/rows.RowList` | al posto di una tabella da leggere: nome a sinistra in semigrassetto, cosa è a destra in `text2`, una linea leggera fra due righe; alto quanto le righe, scorre con la scheda |
| Griglia di campi | `ui/rows.FieldGrid` | al posto di una tabella da scrivere (le bollette): i campi numerici normali in righe e colonne, i nomi a sinistra e in alto, il totale di ogni colonna; Tab da uno all'altro |
| Meridio | `ui/assistant.py` | il fumetto scivola di 10 px dalla sua parte e si accende; nome `title` sul lato opposto alla maniglia, conversazione `body`, «Domande pronte» `label`; opzioni come pulsanti del programma con hover, solo fra un turno e l'altro (R197) |
| Sezione con spunta | `ui/style.py` (`SectionGate`) | campi accesi solo nello stato previsto della spunta, attenuati altrimenti e con il suggerimento che spiega perché; valori conservati (R194) |
| Stato dei salvataggi | `ui/save_status.py` | piccolo arco durante la scrittura, poi «Salvato alle HH:MM» o «Salvato in automatico alle HH:MM» nella barra di stato; errori invariati (R195) |
| Barra di scorrimento | `ui/scrollbars.py` (`ScrollStyle`) | un cursore di 6 px, raggio 3, `line` a riposo, `muted` sotto il puntatore, `text2` premuto; nessuna guida, nessuna freccia; niente se non c'è da scorrere |

### I simboli (`ui/symbols.py`, R138, R330)

Un solo disegno per «confermato, errore, avviso, informazione, blocco»: nessun carattere di un font (✔ ⚠ ✘ ℹ e simili
non si usano più, una prova li cerca nei sorgenti), nessuna icona Lucide con quei significati. **Piatti** (R330, Daniel
02/11/2026: «come simboli usiamo quelli piatti»): un fondo di una tinta sola (il disco, il triangolo, l'anello del
divieto) e il segno **bianco opaco** sopra. Le geometrie stanno in `symbol_shapes.py`, senza Qt (16 unità, tratti di
1,7): le leggono la finestra (`ui/symbols.py`, con il disegnatore SVG di Qt) e la relazione (`report_typst/`, che le
passa a Typst nei dati e le disegna come immagini vettoriali).

| Simbolo | Significato | Tinta | Dove |
|---|---|---|---|
| `check` | confermato, superato | `good` | Verifiche «Superate», stringa corretta, tasto «Tieni» |
| `cross` | chiudi, no | `critical` | pulsanti «No», «Chiudi» delle finestre |
| `forbidden` | operazione non permessa | `critical` | nessun uso oggi; riservato ai comandi non ammessi |
| `stop` | blocco (le verifiche da correggere) | `critical` | livello «fail», stringa fuori finestra |
| `info` | dettaglio (le verifiche da sapere, le note) | `info` | livello «info», note |
| `warning` | possibile problema (da controllare) | `warning` | livello «warn», stringa da verificare |
| `error` | il programma ha incontrato un errore | `critical` | finestre di errore |
| `trash` | butta via | `critical` | «Scarta» di una finestra |
| `back` | torna indietro, niente è cambiato | `neutral` | «Annulla» di una finestra, ritorno alla proposta degli ottimizzatori |

**Regole d'uso**

- **Il triangolo è largo quanto il disco** (R330: «in larghezza sia uguale al diametro del cerchio»): 15 unità di
  larghezza, appena sopra e sotto il disco, perché a pari altezza il triangolo sembrava piccolo accanto ai cerchi. Lo
  vincola `test_the_warning_is_as_wide_as_the_disc`.
- **Il segno è dipinto, non ritagliato.** I piatti del 25/10/2026 furono rifiutati perché il segno era un buco nel
  fondo e lasciava vedere quello che c'era sotto (l'ortofoto, la pianta, la scheda): su un fondo qualunque il segno
  cambiava colore. Qui il fondo è pieno e il segno è un secondo tracciato bianco, opaco: lo stesso segno su ogni fondo.
  Per questo il divieto è un anello e la sua sbarra della stessa tinta, fusi senza giunta.
- **Una tinta per significato** (`theme_colors.STATUS` e `WARNING_INK`); sul fondo scuro il blu e il grigio si
  schiariscono (`TONES_DARK`), perché quelli scuri sparirebbero. Il colore non è l'unico indizio: ogni livello ha una
  forma sua (WCAG 1.4.1).
- **Testi e `alt` non cambiano**: il simbolo sta accanto al testo, che continua a dire la stessa cosa; i nomi dei
  livelli sono nei suggerimenti.
- **Si disegna solo qui.** Pianta, 3D, albero, conteggi, schede delle stringhe, dialoghi (`scrollbars.py` mette i
  simboli al posto delle icone standard di Qt) e relazione passano per le stesse forme; cambiare l'aspetto dei simboli
  è cambiare `symbol_shapes.py` e `symbols.py` e basta.
- **Mai la sfumatura**, mai un alone (R138).

**Le forme**

| Forma | Cosa dà | Quando |
|---|---|---|
| `symbols.icon(name)` | una `QIcon` (motore di icone) disegnata alla grandezza e alla densità chieste, chiara o scura secondo il fondo | pulsanti, voci d'albero, `setIcon` |
| `symbols.paint(painter, rect, name, dark=None, off=False)` | il disegno unico: pianta, 3D, conteggi, schede; `off`: grigio, per un livello vuoto | tutto ciò che dipinge da sé |
| `symbols.sign(name, rect)` | il solo segno come `QPainterPath`, per un fondo già nel colore del livello | caselle di spunta (`checkboxes.py`) |
| `symbols.html(name, size=14)` | un `<img>` per il testo ricco (PNG a 1, 2 e 3 volte nella cartella temporanea: Qt sceglie da solo); il carattere solo se la cartella non si può scrivere | etichette, note, righe delle schede |
| `symbol_shapes.report_marks()` | l'SVG di ogni livello con il segnaposto del colore, per Typst | solo la relazione (`template.typ`, `mark`) |

Nella relazione il colore del livello è quello della tavolozza della carta (`colours.ok/warn/fail/info` in
`template.typ`), non quello della finestra: cambia la tinta, non la forma.

**Eccezioni giustificate**: i caratteri nel solo `html()` quando la cartella temporanea non si scrive (ultima
risorsa); `⟳` (da ricalcolare) nelle note delle schede della posa, per cui non c'è un simbolo; `⋯`, `∥ ⊥ ⇧` delle guide
non sono segni di stato. La prova `tests/nucleo/test_symbols_sources.py` tiene l'elenco (`ALLOWED`).

## 5. I comportamenti

- **Fine morbida** (`ui/fades.py`): quando un elenco o una pagina continua oltre la scheda, l'ultimo pezzo sfuma nel
  colore della scheda invece di tagliarsi. La sfumatura è alta 12 px (al massimo un quinto dell'area), piena solo sul
  filo esterno e subito molto più leggera, dentro la linea e gli angoli tondi della scheda. Così la prima voce resta
  leggibile anche nel pannello Inverter scorso a metà (R192), senza riaprire il bordo ai contenuti. Compare solo dal
  lato dove c'è altro e non c'è quando il contenuto è fermo in cima. Daniel,
  24/10/2026: «carina la semplice sfumatura… mantienila come stile». Vale per ogni area che scorre dentro una scheda.
  Nelle pagine e nei pannelli ciò che scorre si ferma 8 px prima delle linee in alto e in basso della scheda
  (`fades.attach(area, air=True)`, `fades.AIR`), e la sfumatura sta sul bordo del contenuto: R177, Daniel
  26/10/2026, «i contenuti ... arrivano fino al limite della scheda sfondandolo» (all'85 % sul bordo, e senza
  aria, quello che c'era sotto arrivava fino alla linea). Gli elenchi no: il loro margine in alto è quello
  dell'intestazione.
  Quick (R590, Daniel 11/11/2026: «nel primo step di scrolling rimane proprio un taglio netto sulla scritta»): un
  solo componente, `Controls/EdgeFades.qml`, messo da `M.ScrollPage` e da ogni `M.ScrollBar` verticale (anche
  l'albero Progetto e le Verifiche, che avevano `Properties/ScrollEdges`, tolto). La sfumatura entra alta quanto il
  contenuto già passato oltre il bordo (fino alla sua altezza piena), piena sul bordo dal primo pixel: prima entrava
  intera ma trasparente in proporzione, e la riga tagliata restava nuda finché la lista non si era mossa di 24 px. In
  `M.ScrollPage` l'aria sta dentro ciò che scorre (`airInside`, ora per tutte le pagine): il contenuto sfuma fino al
  bordo del contenitore, senza la striscia vuota di 6 px dove spariva prima del bordo. La corsia della barra resta
  fuori dalla sfumatura.
  **La regola di oggi (R624, Daniel 15/11/2026: «la sfumatura deve essere una trasparenza gradiente del contenuto»,
  «mantenerla ben centralizzata»)**: la sfumatura è il contenuto che diventa trasparente verso il bordo, e sotto si
  vede quello che c'è (il pannello, la scheda, il fondo della relazione). Non è più una fascia di un colore dipinta
  sopra: quella funzionava solo se il contenuto stava su quel colore, e sulle righe delle Verifiche (colore scheda
  sopra il pannello) e sul foglio bianco della relazione nel tema scuro diventava un taglio netto o una fascia scura.
  - Un solo componente: `Controls/EdgeFades.qml`, uno strato (`layer`) dell'area che scorre con lo shader
    `Controls/edgefade.frag` (curva smoothstep: nessun gomito, quindi nessuna riga visibile dove la sfumatura comincia
    o finisce). Lunghezza nel tema: `Size.FADE` (16 px, al massimo un quinto dell'area), uguale per elenchi, tabelle,
    pagine, dialoghi e relazione. Il 15/11/2026 provata a 32 px (circa una riga): Daniel, dal programma vero,
    preferisce 16 (R633).
  - Nei pannelli di destra la cornice delle sottoschede di primo livello non sfuma (R633, «scheda sempre intera»): la
    disegnano le testate tenute (`Controls/HeldHeads.qml`) sopra ciò che scorre, dalla testata (al suo posto o
    tenuta) fino al fondo vero della sezione o, se la sezione prosegue oltre la parte visibile, fino al bordo visibile
    (sopra le testate tenute in fondo, o l'aria della pagina), dove si chiude con il suo lato inferiore arrotondato.
    Sfuma solo ciò che sta dentro.
  - Lo mettono solo i componenti di scorrimento comuni (`M.ScrollPage`, `M.List`, `M.Tree`, `M.Table`, `M.Dialog`,
    ogni `M.ScrollBar` verticale); parametri: l'area (`flickable`) e, se la barra sta dentro l'area, la sua corsia
    (`barRoom`); nella pagina di un pannello, le testate tenute ai bordi (`held`, R633): sotto di loro il contenuto
    non si vede e la sfumatura parte dal loro bordo, non da quello dell'area. Nessuna pagina fa una sfumatura da sé: gradienti, maschere, shader di dissolvenza fuori dal
    componente fanno fallire `tests/quick/sistema/test_sfumature_r624.py` (eccezioni scritte lì, col perché).
  - Compare solo dal lato dove c'è altro contenuto, alta quanto il contenuto già passato oltre il bordo (R590), e lo
    strato è acceso solo allora (una superficie grande quanto l'area: circa 5 MB a scala 2 per un pannello 1000×300).
  - Il renderer software di Qt (fuori schermo, le prove) non disegna shader: lì lo strato resta spento e il contenuto
    è intero, senza sfumatura. Come appare si prova su Direct3D 11 con una finestra mai mostrata
    (`tests/quick/controlli/test_dissolvenza_r624.py`, misura in `tests/quick/aiuti/dissolvenza.py`).
  - A scala frazionaria (2,5) l'area che sta su mezzo pixel si sposta di un pixel quando lo strato si accende: niente
    sfocatura, il testo resta nitido.
- **Finestrelle** (`ui/popups.py`): suggerimenti, menu, elenchi a tendina e aiuto a comparsa entrano sfumando in
  110 ms; gli effetti di Qt, che a 200 % scattano, sono spenti. Su Windows 11 il sistema li arrotonda e disegna la
  loro ombra e il bordo nel colore `line`; altrove il foglio di stile disegna lo stesso bordo e, per i suggerimenti,
  gli stessi angoli di 4 px su una finestrella trasparente intorno.
- **Suggerimenti** (R162, Daniel 25/10/2026: «una larghezza massima in cui il testo va in colonna ... una bella
  formattazione ai contenuti come fanno programmi tipo VS Code»): «Nome (tasto)» sulla prima riga e la spiegazione
  sotto diventano il nome (semigrassetto se segue una spiegazione), il tasto attenuato accanto, la spiegazione in
  un inchiostro più tenue 4 px sotto; a capo a 340 px; 6 px sopra e sotto e 8 ai lati (una riga: 28 px, come un
  controllo). Vale per ogni suggerimento, da dovunque venga, perché si formatta l'etichetta di Qt quando compare.
  Colori (R615, Daniel 14/11/2026: «per i tooltip starei con il 92 %, ma invertirei i colori: tooltip chiaro con
  tema chiaro e viceversa. Armonizziamo i loro colori di sfondo»): non più invertiti. Il fondo è quello dei menu e
  delle finestrelle (`card`) all'opacità `TIP_ALPHA` = 92 % (il token `tooltip_bg`, in `theme_colors`), con il filo
  `line` e il raggio `CARD` dei menu; il nome nel `text` del tema, spiegazione e tasto lo stesso `text` verso `card` (`TIP_SOFT` 0,22 e `TIP_KEY`
  0,32: anche il tasto a 4,5:1 o più dal fondo, qualunque cosa ci sia sotto).
- **Pagina File** (R157, riveduta con R178): entra in 180 ms con una dissolvenza e uno scorrimento di 16 px dal
  lato del menu (`ui/motion.enter`, `Entrance`). Il velo opaco tiene la fotografia di prima e dipinge quella della
  pagina: niente `QGraphicsOpacityEffect`, maschere o ridisposizioni ai fotogrammi. Con «meno movimento» la pagina è
  subito presente; si chiude subito. Le alternative fotografate sono il foglio che si scopre da sinistra e la sola
  dissolvenza, alla stessa durata.
- **Cambio di fase** (`ui/phasebar.Phases._changed`, come la barra multifunzione di Office): la pagina e gli
  strumenti della barra cambiano subito; scorre soltanto la linguetta scelta, fino alla nuova fase (110 ms, R97), con la stessa curva del rettangolo delle piste. Gli
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
  etichette lunghe vanno a capo e la loro altezza minima segue testo, larghezza e carattere, così la riga cresce
  con loro anche dopo un cambio di impostazioni (`grow_label`, anche per le righe create dopo, R193), una pila di
  pagine prende la misura della pagina mostrata, il campo passa sotto la
  sua etichetta quando non ci sta accanto, il titolo lungo di un gruppo si accorcia con «...» invece di allargarlo
  (25/10/2026: «Energia acquistata (tutti i costi variabili, imposte comprese)» spingeva i campi del Bilancio oltre la
  scheda), due pulsanti che non ci stanno affiancati vanno uno sotto l'altro. Prima i contenuti uscivano dalla
  colonna Dati (24/10/2026).
- **Trascinamento delle schede** (Quick: `Shell/Workbench.qml`, `DockPanel.qml`; R312, R504, R689, studio 36): la scheda portata conserva la misura iniziale, senza ingrandimento. Contorno immediato e segnaposto dopo DWELL promettono lo stesso posto finale esatto, con fondo neutro `hover` e bordo `card_line`; uno solo è mostrato alla volta. Le altre schede fanno spazio con CAREFUL ed EASE. Contenuti e viste restano alla misura naturale, tagliati dal contenitore che si muove; si impaginano all'inizio o alla fine, mai a ogni fotogramma. Le zone restano ferme durante il gesto: bande XXXL ai bordi e isteresi M anche alle diagonali. Le linguette si propongono solo con Alt. Le regole complete sono sotto, in «Spostamento delle schede».
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

### Spostamento delle schede (R689, seguito del 16/11/2026)

Un contenuto non si stira mai, né in larghezza né in altezza. Vale per la scheda portata,
per il rilascio, per le schede vicine e per le viste. Il contenitore (fondo, bordo, angoli)
cambia misura con CAREFUL ed EASE del tema. Il contenuto resta a scala 1 ed è tagliato
con `clip`; quando la destinazione è nota, viene impaginato una volta alla misura finale.

`Card.faceItem` separa testata e corpo dal fondo. `DockPanel` prepara questa superficie
alla misura di `placed`, senza seguire le dimensioni intermedie del fondo animato.
La fotografia del trasporto cattura soltanto quella superficie e conserva le dimensioni
naturali, tagliata dal fantasma. Nessuna scala di sollevamento. Anche lasciata flottante,
la scheda conserva la misura di partenza. `DockView` tiene il buffer alla misura naturale
per tutto il gesto e il rilascio: il suo contenitore lo ritaglia. All'arrivo il contenuto
vivo prende la misura vera; un eventuale raccordo usa soltanto la dissolvenza del tema.

Contorno e segnaposto usano la disposizione finale di `slot` e `sliceRect`: stessi margini,
GAP e angoli CARD del risultato. Il calcolo comprende lo spazio liberato all'origine e,
con Alt, il gruppo di linguette, anche se la scheda bersaglio era affiancata.
La loro geometria è ferma: animano le schede attorno. Non si mostrano due destinazioni
contemporaneamente. Il fondo è `Theme.colors.hover`, il bordo `Theme.colors.card_line`,
con spessore HAIR. Nessun colore d'accento nell'anteprima.

Al rilascio vince la destinazione della promessa mostrata: non si ricalcola un bersaglio
dalle coordinate dell'evento di rilascio. La fotografia raggiunge il posto dall'ultima
posizione portata in un movimento solo; la scheda viva appare all'arrivo.
Le aree d'aggancio restano quelle congelate all'inizio del gesto. L'isteresi M tiene
la proposta anche vicino ai confini diagonali: lo spazio per restare è più largo di
quello per entrare. L'anteprima si toglie quando il puntatore esce davvero dalla zona.

Con movimento ridotto durate nulle, compresa l'attesa DWELL, e nessuna animazione
geometrica. Le regole e le durate sono comuni a tutte le schede.

### Menu del testo (R683, 16/11/2026)

`TextActions` contiene stato, abilitazioni e azioni; `TextMenu` usa il Menu R662,
senza uno stile parallelo. `TextKeys` instrada i tasti degli editor. Il servizio GUI
`textEditing`, registrato da `install_controls`, fornisce traduzioni, tasti standard,
appunti/MIME, testo leggibile da QTextDocument e incolla numerico. Nessun Qt entra in app/core.

TextField, TextArea, NumberField, GrowingField e OverlayField ereditano lo stesso
comportamento. Destro, Menu e Maiusc+F10 aprono il popup differito; pressione lunga
usa gli eventi e la soglia di piattaforma. Il menu prende fuoco per la navigazione
Qt e conserva la selezione. Il segnale nativo `editingFinished` può arrivare al
passaggio al popup: i consumatori di TextField devono usare `commitRequested`,
che differisce la conferma fino all'uscita reale. OverlayField differisce allo stesso
modo `focusLost`. Identità/epoch, visibilità e disponibilità proteggono il bersaglio.

Una sola guardia GUI di ShortcutOverride impedisce che Undo, Redo, Taglia, Copia,
Incolla, Seleziona tutto e Canc raggiungano il progetto mentre si modifica testo,
anche in un campo vuoto o readOnly. Le operazioni restano in TextActions; non si
installano scorciatoie globali per campo. La cattura tasti delle Impostazioni
disabilita esplicitamente il router. Password non esporta testo.

`ReadableText` è TextArea bare readOnly, selezionabile anche da tastiera;
`CopyLabel` serve per valori compatti o troncati e copia il valore completo.
Pulsanti, assi, bussola e placeholder restano etichette. I tooltip transitori
restano transitori: il controllo di origine espone Copia descrizione quando serve.
Al momento dell'apertura si fissano selezione, intero, sorgente Markdown e
descrizione: lo streaming non cambia ciò che il comando copierà.

D1 B: un'unica politica numerica indica unità, tipo quantity facoltativo, limiti,
precisione e locale. Incolla e Ctrl+V validano il risultato completo, anche al
cursore o su selezione parziale; rifiutano ambiguità, unità incompatibili,
multilinea e valori fuori limite. Le conversioni e le espressioni quantity restano
nei campi che le supportavano. Una sostituzione QInputMethodEvent mantiene un
solo undo locale e non riscrive gli appunti.

Le copie semantiche usano TextActions anche nei menu esistenti: riga Verifiche con
fonte senza duplicati, nome oggetto, riepiloghi, cella con unità, righe TSV da modello
in ordine visibile, punto attivo del grafico, formula dalla sorgente TeX. La tabella
ha un solo menu condiviso, senza crearne uno completo per cella. D2 B offre Markdown
solo sui messaggi con sorgente formattata; D3 A rinvia il nuovo invito a Meridio.

La relazione usa QPdfDocument.getAllText su QThreadPool; solo il filo GUI può
scrivere gli appunti, verificando token e generazione. Leggi testo pagina apre
ReadableText senza copiare. Cache e risultati tardivi rispettano la generazione;
pagina senza testo non inventa un risultato. Nessun OCR o nuovo motore PDF.

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
| Quick: `Controls/DropOutline.qml` | il contorno d'aggancio del §4 e del §5 (da portare nel modello `qt-app-template`, pacchetto `qtkit`, con la riga della tabella del §4; la Workbench che lo usa resta di Meridiana) | `Theme` (`colors.accent`, `accent_soft`, `line.FOCUS`, `radius.CARD`, `motion.FAST`) |
| Quick: `Controls/OverlayField.qml` | il campo scritto sopra una vista, uno per tutte (R534): la lunghezza del lato in pianta (`Plan/SideEditor.qml`) e la quota dei vertici nella vista 3D. Fondo e testo delle pillole della pianta (`label_bg` opaco, `label_fg`), contorno della selezione (`sel`) largo `line.FOCUS`, raggio `radius.PLAN_LABEL`, testo `type.SMALL` a cifre di uguale larghezza, `space.XXS` sopra e sotto, `space.S` ai lati; davanti il numero in un disco (il lato) o una parola che dice cos'è («Quota da terra»), dopo l'unità; largo quanto ciò che contiene. Invio conferma, Esc annulla. Nella vista 3D resta accanto al vertice da cui si è aperto (13 px a destra e sotto, o in uno degli altri tre angoli se lì copre il manipolatore o un altro vertice scelto), lo segue in orbita, spostamento e zoom nello stesso fotogramma e si ferma al bordo quando il vertice esce. Da portare nel modello `qt-app-template` (`qtkit`) | `Theme` (`type.SMALL`, `space`, `radius.PLAN_LABEL`, `line.FOCUS`); i colori li passa la vista (`planColors`, `overlayColors`) |
| Quick: `Controls/PointerSign.qml` | il segno accanto al puntatore di un tasto che cambia il clic (R535): il + e il − della selezione in pianta (Ctrl aggiunge o toglie, Maiusc toglie), l'icona del comando su un lato (Allinea, R497), il Ctrl sui vertici della vista 3D (− sopra un vertice già scelto). Quadrato di 18 px, raggio 3, fondo `halo`, 14 px a destra e 16 sotto il puntatore, segno in grassetto 16 px azzurro (aggiunge) o rosso critico (`sweep_remove`, toglie). Da portare nel modello `qt-app-template` (`qtkit`) | `Theme` (`fontFamily`), `Icon` |
| `ui/menubar.py`, `ui/panel_buttons.py`, `ui/segments.py`, `ui/variant_bar.py` | barra dei menu ad Alt, pulsanti delle schede, pista di segmenti, varianti | `design`, `icons`, `motion` |
| `ui/day_picker.py` | il calendario dei campi data: un fondo solo, giorno scelto neutro, oggi in un anello | `design`, `icons` |
| `ui/icons.py` | icone Lucide (ISC) e proprie, nel colore del tema | `paths` |
| `ui/sections.py`, `ui/marks.py` | elenchi a sezioni con i segni | `design`, `symbols` |
| `symbol_shapes.py`, `ui/symbols.py` | i dieci simboli piatti (§4): le forme senza Qt, poi icona, disegno, segno e testo ricco | `theme_colors` (le forme); Qt Svg (il disegno) |
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
di scorrimento, il calendario, i campi data e il cursore, la pista delle schede accorpate e la minore presenza
dell'accento; la provenienza commit per commit è nel suo `docs/da-dove-viene.md`.

## 8. La carta: la relazione e i documenti stampati

La relazione (`ui/report.py`, `ui/report_chapters.py`, foglio in `ui/document_style.py` con `paper=True`, colori in
`ui/report_style.py`) non segue il tema della finestra: è carta bianca, inchiostro `INK`, secondario `MUTED`, filetti
`RULE`, fondo delle intestazioni `HEAD`, in chiaro e in scuro. Regole (R291, Daniel 30/10/2026: «la relazione è
brutta, va rivista da un punto di vista estetico e di esposizione dei contenuti»):

- **Quattro gradini di titolo, tutti semigrassetto**: h1 23 pt (solo il titolo del progetto), h2 16 pt (i capitoli,
  numerati, ognuno su una pagina nuova nel modello Completo), h3 12 pt (le sezioni), h4 10,5 pt (le voci); testo
  10,5 pt, didascalie e note 8,5 pt in `MUTED`. Lo spazio sopra un titolo cala con il livello (24, 18, 14 px). Un
  testo preso da un altro modulo (i record di «Come è calcolato») entra con i titoli **abbassati di un livello**.
- **Tabelle**: un punto meno del testo (9,5 pt), celle 4×6 px, intestazione su `HEAD` ripetuta a ogni pagina, un
  filetto `RULE` sotto ogni riga; **i numeri a destra e nudi, l'unità nell'intestazione** («Azimut, °», «PR, %»,
  «Valore attuale netto, €»); la riga del totale o del progetto evidenziata (`tr.result`); una riga di gruppo
  (`td.group`) al posto di una colonna che ripete lo stesso nome; larghezze date alle colonne delle tabelle larghe,
  così le parole dell'intestazione non si spezzano; mai una tabella più larga della pagina.
- **Fatti** (`facts`): etichetta in `MUTED` al 34 %, valore in inchiostro normale; semigrassetto solo per i numeri
  di testa della Sintesi.
- **Figure** (`figure`): centrate, larghe 620 px (16 cm), con la didascalia numerata subito sotto («Figura n. ...»),
  a interlinea 100 % perché il 125 % dei paragrafi lasciava una fascia bianca sotto l'immagine; la pianta alta
  quanto chiede il suo disegno; la legenda dei grafici sopra il grafico, mai sulle barre.
- **Niente due volte**: la pianta sta nella Sintesi e non torna in Coperture e posa; le verifiche delle stringhe
  una volta per ogni tipo di stringa, con gli ingressi su cui vale; le verifiche del capitolo per ambito.
- **Copertina**: nel Completo dipinta a sé (`_paint_cover`); nel Sintetico un blocco chiuso da un filetto `<hr>`
  prima del primo capitolo. Intestazione e piè di pagina a 7,5 pt in `MUTED` dalla seconda pagina.

## 9. Linee, pillole e contatori delle viste (R685, R692, 16/11/2026)

La variante D usa un tratto sottile e un alone sempre presente, leggero e uniforme. Queste regole sostituiscono
gli spessori e gli aloni precedenti del disegno, delle misure e delle selezioni. Il cubo e la barra della vista
3D restano comandi di navigazione, con le proprie regole.

I valori delle annotazioni stanno in `app/interface/view_colours.py.Annotation`, esposti da
`gui/style/design.py.Annotation` e da `Theme.annotation`. I colori vengono dal tema e dai ruoli del disegno.

| Elemento | Regola predefinita, in pixel logici |
|---|---|
| Linea | 1,5; alone nero con opacità 0,14, largo 2 in più del tratto; uguale in chiaro e scuro |
| Tratteggio | 6 pieni, 4 vuoti, anche con zoom e rotazione; estremi piatti per conservare il vuoto |
| Punto geometrico | 4,5; la zona che prende il clic conserva la sua misura separata |
| Testo delle pillole | 11, peso normale 400; le preferenze del testo continuano ad applicarsi |
| Direzione del testo | Lungo il lato o il segmento, angolo normalizzato in [-90°, 90°) |
| Contatore | Disco alto 16 con una cifra; con più cifre cresce in larghezza mantenendo le estremità tonde |

`Controls/ViewPath.qml` definisce lo stile delle ShapePath; `ViewStroke.qml` lo usa per i tratti singoli e
`ViewPoint.qml` per i punti. `ViewMarks.js` contiene le forme degli agganci. `ViewMask.qml` applica lo stesso
spessore e alone alla maschera di appartenenza della selezione. Le viste con molti elementi raggruppano i
percorsi, mantenendo lo stile comune. I passaggi di solo riempimento hanno inchiostro trasparente: non aggiungono
un secondo alone. Il vecchio alone nei dati della selezione è stato tolto.

`LengthPill.qml` è la pillola comune di lati, stringhe, misure e totali; `SpanLabel.qml` ne conserva l'interfaccia
per le misure. `CountBadge.qml` disegna i contatori, usato anche da Pill e CheckMark. Lati e stringhe misurano
le collisioni sul rettangolo ruotato; le misure tengono conto anche delle pillole dei lati.

[V] Software e Direct3D richiedono un adattamento diverso del tratto cosmetico e delle distanze del tratteggio;
lo fa ViewPath. Le prove dei pixel verificano entrambe le scale 1 e 2,5 sui due renderer. Nella finestra completa
Direct3D il renderer a curve perdeva alcuni poligoni della pianta, pur risultando pronto. I poligoni usano quindi
GeometryRenderer dentro una sola superficie della vista con quattro campioni MSAA, dal tema; in software si
disegna direttamente. I percorsi sullo schermo mantengono CurveRenderer. [I] Il costo della superficie su GPU e
la fluidità con progetti grandi vanno controllati sullo schermo vero.

Nel 3D `ViewRibbon.qml` fornisce il tratto e l'alone comuni a selezione, stringhe, ottimizzatori e passaggio del
mouse. La sezione dei nastri e la prospettiva conservano i limiti del motore descritti nello studio 52.
Le misure proiettate riusano MeasureLayer. Per R692 il lavoro `annotation_visibility` interseca i segmenti con
le ombre geometriche dei triangoli reali della scena: edifici, moduli e facce IFC trasformate. Conserva gli
intervalli visibili, senza sostituire le facce con le loro scatole. Il calcolo usa il processo dei lavori,
con geometria riusata e cancellazione; le risposte di una camera precedente vengono scartate.

La pillola di un tratto completamente coperto si nasconde; quella di un tratto coperto in parte usa la porzione
visibile più lunga, quando vi entra, senza spostarsi oltre i suoi estremi. Anche punti, riferimenti, guide e
tratto al puntatore rispettano i solidi. Durante un nuovo calcolo non si mostra la visibilità della camera
precedente. Le guardie sulle sorgenti e le prove dei pixel sono elencate in `docs/revisioni/linee-d-verifiche.json`.
