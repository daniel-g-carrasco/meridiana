# Revisione Kimi 3: armonia oltre testi e pulsanti

Data: 25/10/2026. Ramo: `kimi-revisione`.

## Metodo e confini

Ho letto `ui/design.py`, `theme_colors.py`, `docs/design/sistema-grafico.md` e i componenti UI che contengono colori,
misure, raggi o durate letterali. Una scansione AST ha cercato chiamate Qt di impaginazione, dimensioni, raggi e
timer; una ricerca testuale ha raccolto colori esadecimali, `QColor` e fogli di stile locali. Ho confrontato i
fallback con `theme_colors.derive(DEFAULT_SEED, False/True)`.

Non conto come difetti:

- zeri, la linea da 1 px (`Line.HAIR`), valori già presi da `Space`, `Radius`, `Size`, `Icon`, `Button`, `Motion`;
- misure calcolate da font, contenuto, densità o geometria della scena, numeri di colonne, unità e soglie tecniche;
- i colori propri di pianta e 3D in `view_colours.py`, esplicitamente fuori dal compito;
- palette dei grafici come dati (`SERIES`, `SEQUENTIAL`), già validate e non equivalenti al colore dell'interfaccia;
- costanti temporanee di rete, budget IFC, salvataggio e self-test, che non sono scelte di armonia;
- tempi del thread audio e delle richieste di rete. Per le durate considero animazioni, debounce, attese e aggiornamenti
  visibili dell'interfaccia.

Non ho misurato aspetto o fluidità sullo schermo. Le sostituzioni che cambiano anche di 1 px o pochi millisecondi la
resa sono proposte da confermare con la galleria e con le misure di Claude, non da applicare automaticamente.

## Osservazioni, dalla più grave

### 1. Le Verifiche ricavano ruoli colore nel widget invece che nel tema

- **File e righe**: `src/meridiana/ui/checks_page.py:28-39`, `:117-140`, `:300-335`, `:524-538`;
  `src/meridiana/ui/marks.py:17-52`, `:164-174`.
- **Che cosa succede**: `ChecksPage.set_colours` calcola da sé il fondo delle schede in scuro e l'alfa del passaggio.
  `ChecksTree` e `CountChip` hanno anche fallback diversi dai token. I segni introducono un colore «info» e vari
  colori d'inchiostro che non esistono nel catalogo. In scuro il fondo calcolato è necessario perché `card` coincide
  con `panel`, ma la formula è fuori dal sistema che dovrebbe verificarne i contrasti.
- **Scenario concreto**: si sceglie un accento o un fondo personalizzato. La maggior parte della finestra cambia
  secondo le regole di `theme_colors.derive`; le sottoschede delle Verifiche applicano invece una velatura fissa del
  4,5 % e un passaggio con alfa 18. I controlli di contrasto del tema non validano quella coppia di colori.
- **Gravità**: media. Può produrre incoerenza o contrasto insufficiente proprio nei pannelli densi di informazioni.
- **Prova**: [V] lettura delle formule e dei token derivati. [V] i fallback `select = #f5e3c8` e `focus = #b3541e`
  non coincidono con il bronzo derivato `select_bg = #ebe1d6` e `accent = #805210`; `CountChip.muted = #8a857c`
  non coincide con `muted = #6f685d`.
- **Correzione proposta**: spostare i ruoli in `theme_colors.derive` e nelle sue verifiche, senza cambiare i valori
  in questa fase:

  | Valore attuale | Destinazione proposta |
  |---|---|
  | `COLOURS` fail/warn/ok, `checks_page.py:31` | `theme_colors.STATUS["critical"/"warning"/"good"]`, già esistenti |
  | fondo scuro `mix(panel, white, 0.045)`, `:533` | nuovo token `checks_card`, con `CHECK_CARD_VEIL = 0.045`; non riusare `CARD_VEIL`, che ha un altro scopo |
  | alfa 18 del passaggio, `:534-537` | nuovo token `checks_hover`, oggi `text` con alfa 18 (`12` esadecimale) |
  | fallback `card/line/sink/select/focus`, `:134-135` | token `card`, `line`, `field`, `select_bg`, `accent` dal tema predefinito |
  | inchiostri `CountChip`, `:314` | token `text`, `muted`, `select_fg` |
  | `marks.FILL["info"] = #2e4a6b`, `marks.py:17` | nuovo `STATUS["info"]`, mantenendo il valore |
  | `marks.INK`, `:19` | nuova mappa `STATUS_FG`: bianco per fail/info/ok, testo scuro per warn |
  | bordi `#1e1c19` e `#6b4a00`, `:29` | nuova mappa `STATUS_EDGE`, perché `#6b4a00` non è `WARNING_INK` |
  | badge `#1e1c19` e `#ffffff`, `:48-52` | nuovi ruoli `badge_bg` e `badge_fg`, non il colore del testo generico |
  | `pill_colours`, `:164-174` | ruoli `warning`/`WARNING_INK` già esistenti; nuovi `info_fg` chiaro/scuro per il caso info |

- **Rischio della correzione**: medio. I token nuovi devono conservare gli stessi colori iniziali e superare i test
  di contrasto nelle due tonalità. Cambiare `#6b4a00` in `WARNING_INK` sarebbe una scelta estetica diversa, non una
  semplice centralizzazione.

### 2. Il bordo d'errore e le distanze delle pagine energetiche non seguono il sistema

- **File e righe**: `src/meridiana/ui/energy_pages.py:58-60`, `:72-100`, `:114-147`, `:176-183`,
  `:195-228`, `:280-286`, `:452-462`, `:692-698`; analoghi minimi dei grafici in `ui/charts.py:191-197` e
  `ui/charts_pg.py:212-216`.
- **Che cosa succede**: il campo `per_mppt` riceve un rosso letterale invece del token `danger`, che il tema adatta
  al fondo. Le stesse pagine contengono margini da 10 e 14 px e spaziature da 10 px, fuori dalla scala chiusa.
  Il minimo dei grafici, 160 px, è ripetuto in tre punti.
- **Scenario concreto**: inserendo una lettera in `per_mppt`, il bordo è `#d03b3b` in entrambi i temi. Nel tema
  chiaro predefinito il token corretto sarebbe `danger = #c53032`; in scuro `#ff716a`. Inoltre, cambiando i margini
  del modello grafico, i riquadri dei risultati non possono seguirlo perché 10 e 14 non hanno un nome nel catalogo.
- **Gravità**: media. Il colore d'errore può avere contrasto non controllato; le misure incoerenti sono visibili
  nelle pagine più usate dopo il Modello.
- **Prova**: [V] valori letti e confronto con i token derivati. [V] la scala ammette 2, 4, 6, 8, 12, 16, 24, 32,
  quindi 10 e 14 sono fuori.
- **Correzione proposta**:

  | Valore attuale | Costante esistente o proposta |
  |---|---|
  | bordo `#d03b3b`, `:461` | token `danger`, passato alle pagine con un piccolo `set_colours(tokens)` |
  | etichetta minima 24, `:60` | `Space.XXL` |
  | riquadro 12, 8, 12, 8 e spazi 2, 4, `:91-95` | `Space.L, Space.M, Space.L, Space.M`; `Space.XXS`, `Space.XS` |
  | `Tiles.TILE = 165`, `:117` | nuovo `Size.RESULT_TILE = 165` |
  | griglia 8, `:123` | `Space.M` |
  | minimo 120, `:128` | nuovo `Size.RESULT_MIN = 120` |
  | minimo 130, `:146` | `Size.RESULT_MIN + Size.SCROLLBAR`, cioè 130, senza nuovo numero |
  | area 280 x 160, `:181-182` | nuovi `Size.PANEL_MIN_WIDTH = 280` e `Size.CHART_MIN_HEIGHT = 160` |
  | carta grafico 8, 6, 8, 8, `:201` | `Space.M, Space.S, Space.M, Space.M` |
  | modulo 12, 2, 12, 10, `:217` | `Space.L, Space.XXS, Space.L`; l'ultimo 10 va portato a `Space.M = 8` o `Space.L = 12` dopo schermata |
  | risultati 16, 14, 16, 14 e spazio 10, `:220-221` | `Space.XL`; il 14 va a `Space.L = 12` o `Space.XL = 16`, lo spazio 10 a `Space.M` o `Space.L` dopo schermata |
  | pagina minima 320, `:228` | nuovo `Size.PAGE_MIN_WIDTH = 320` |
  | meteo 12, 6, 8, 6 e spazi 4, 12, `:283-286` | `Space.L, Space.S, Space.M, Space.S`; `Space.XS`, `Space.L` |
  | extra 48 del campo automatico, `:697` | `2 * Space.XXL`, già 48 |
  | minimi 160 dei grafici | stesso `Size.CHART_MIN_HEIGHT = 160` condiviso |
  | `charts_pg.TOP = 22` | `Size.COMPACT = 22`; margini 4 con `Space.XS`; il 10 di `:216` va a `Space.M` o `Space.L` |
  | legenda 12 e raggio 2, `charts_pg.py:159` | `Space.L` e `Radius.MARK` |

- **Rischio della correzione**: medio per il passaggio dei token alle pagine e per i cambi di 10 e 14 px; basso per
  le sostituzioni dirette. Le schermate di ogni fase nei due temi devono precedere la scelta fra 8/12 e 12/16.

### 3. Il catalogo del movimento non copre le durate effettivamente usate

- **File e righe**: `src/meridiana/ui/assistant.py:44-54`, `:167`, `:790-855`;
  `src/meridiana/ui/waiting.py:23-26`; `src/meridiana/ui/quick_image.py:22`, `:82-91`;
  `src/meridiana/ui/checks_page.py:136-141`; `src/meridiana/ui/report_page.py:113-116`;
  `src/meridiana/ui/appearance.py:19`, `:137-138`; `src/meridiana/ui/window.py:441-444`, `:4569`;
  `src/meridiana/ui/charts.py:121-133`; `src/meridiana/ui/sunbar.py:105-107`;
  `src/meridiana/ui/view3d.py:50-51`, `:174`; `src/meridiana/camera.py:18`; `src/meridiana/ui/plan.py:45`.
- **Che cosa succede**: il catalogo dichiara 110, 180 e 240 ms, ma Meridio scivola in 320 ms e il suo fumetto si
  chiude in 130 ms. La camera usa 250 ms. Altre attese dello stesso tipo sono duplicate con valori diversi o ripetute
  in moduli separati. Non sono necessariamente valori sbagliati: sono scelte non registrate nel catalogo.
- **Scenario concreto**: una revisione vuole rendere tutto il movimento più rapido. Cambiare `Motion.SLOW` modifica
  la linguetta delle fasi, ma non Meridio né la camera; cambiare il debounce di `QuickImage` non modifica quello
  delle Verifiche pur avendo lo stesso scopo e lo stesso valore.
- **Gravità**: media. La promessa «tre durate» non corrisponde al comportamento reale e rende le revisioni
  incoerenti.
- **Prova**: [V] ricerca delle costanti e dei timer. [V] `OPEN_MS` usa già `Motion.NORMAL`; `CLOSE_MS` è
  `Motion.FAST + 20`, quindi 130 ms. [V] le prove dei widget leggono `OPEN_MS` e `CLOSE_MS`, non i valori di
  `Motion` (`tests/widget/test_assistant_widget.py:157-167`).
- **Correzione proposta**: mantenere `Motion` per le animazioni e aggiungere `Timing` per debounce, frame e attese.
  I nomi nuovi conservano i valori attuali; unificazioni con `Motion.SLOW` o `FAST` solo dopo prova visiva.

  | Durata attuale | Destinazione proposta |
  |---|---|
  | Meridio 320 ms | nuovo `Motion.CHARACTER = 320`; usare `SLOW = 240` solo con nuova approvazione estetica |
  | chiusura fumetto 130 ms | nuovo `Motion.BUBBLE_CLOSE = 130` |
  | camera 250 ms | nuovo `Motion.CAMERA = 250`; `view3d` lo usa al posto di `camera.ANIMATION_MS`, senza import UI nel nucleo |
  | giro arco 1200 ms | nuovo `Motion.SPINNER_PERIOD = 1200` |
  | frame Meridio e risposta, 50 ms | nuovo `Timing.ASSISTANT_FRAME = 50`, condiviso |
  | tre puntini, 300 ms | nuovo `Timing.DOTS = 300` |
  | turno finto del widget solo, 600 ms | nuovo `Timing.EMPTY_TURN = 600` |
  | attesa prima dell'arco, 300 ms | nuovo `Timing.WAIT_THRESHOLD = 300` |
  | frame dell'arco, 16 ms | nuovo `Timing.FRAME = 16` |
  | limite scheletro, 3000 ms | nuovo `Timing.SKELETON_LIMIT = 3000` |
  | riposo 3D e Verifiche, 90 ms | nuovo `Timing.RESIZE_SETTLE = 90`, condiviso |
  | ridimensionamento anteprima, 80 ms | nuovo `Timing.PREVIEW_RESIZE = 80`; unificare a 90 solo dopo misura |
  | preferenze aspetto, 250 ms | nuovo `Timing.PREFERENCE_SETTLE = 250` |
  | anteprima relazione, 700 ms | nuovo `Timing.REPORT_PREVIEW = 700` |
  | attesa backend grafici, 30 ms | nuovo `Timing.CHARTS_PRELOAD = 30` |
  | avanzamento giorno, 80 ms | nuovo `Timing.SUN_FRAME = 80` |
  | polling tasto perno, 100 ms | nuovo `Timing.KEY_POLL = 100` |
  | perno dopo ricentra, 1000 ms | nuovo `Timing.PIVOT_HOLD = 1000` |
  | attesa tasto sinistro, 150 ms | nuovo `Timing.BUTTON_WAIT = 150` |
  | riscaldamento iniziale, 1500 ms | nuovo `Timing.WARM_UP = 1500` |

- **Rischio della correzione**: basso se si spostano soltanto i valori; medio se si unificano durate diverse.
  Ogni cambio effettivo va misurato sullo schermo: offscreen non dimostra fluidità né naturalezza del movimento.

### 4. Misure e raggi hanno eccezioni locali non registrate

- **File e righe**: soprattutto `ui/checks_page.py:35-39`, `:67-78`, `:117-118`, `:169`, `:286`,
  `:626-627`; `ui/phasebar.py:37-45`, `:195-199`, `:221-229`, `:254`, `:289-290`, `:332`;
  `ui/assistant.py:44-54`, `:166-167`, `:196-209`, `:236-264`, `:305`, `:400-401`;
  `ui/help_box.py:31`, `:336-337`, `:660`, `:683-693`, `:786`, `:803-805`;
  `ui/plant_page.py:50-71`, `:140-145`, `:171`, `:208-220`, `:440-446`, `:549-556`, `:729-730`;
  `ui/window.py:259`, `:415-421`, `:565-569`, `:700`, `:992`;
  `ui/viewbar.py:32-44`, `:52-57`, `:87`, `:112-115`; `ui/sunbar.py:58-83`;
  `ui/file_page.py:25`, `:88`; `ui/report_page.py:26`, `:136-147`;
  `ui/plan_overlays.py:56-95`; `ui/viewcube.py:19-21`; `ui/view3d.py:720-727`;
  `ui/properties.py:234`, `ui/template_dialog.py:22`, `ui/ifc_import.py:207`;
  `ui/appearance.py:36-59`; `ui/waiting.py:218-224`.
- **Che cosa succede**: molti valori hanno già un equivalente esatto e vanno soltanto sostituiti. Altri sono
  fuori scala o compensi locali. Alcuni sono dimensioni di componente legittime, ma non hanno un nome condiviso:
  cambiare il modello non li raggiunge.
- **Scenario concreto**: il raggio della scheda è 8, quello del fumetto 10; una pillola usa raggio 3 pur avendo
  `Radius.MARK = 2` e `Radius.INNER = 4`. La barra delle fasi combina 10, 6 e 5 px tramite sottrazioni locali,
  quindi la scala scritta nel documento non descrive il risultato.
- **Gravità**: bassa per i valori che hanno un equivalente diretto; media per le eccezioni che richiedono una
  scelta estetica.
- **Prova**: [V] scansione AST e lettura dei componenti. Non affermo che ogni eccezione sia brutta: affermo che non
  è registrata nel sistema.
- **Correzione proposta**: prima le sostituzioni esatte, poi le eccezioni. La tabella assegna ogni gruppo di valori.

  **Sostituzioni già possibili**

  | Valore e luogo | Costante esistente |
  |---|---|
  | margini stato 8, 2, 8, 2; etichette 6, `window.py:415-421` | `Space.M, Space.XXS`; `Space.S` |
  | maniglia 6, `window.py:259`; icona 22, `:700`; fondo 2, `:992` | `Space.S`; `Icon.BAR`; `Space.XXS` |
  | Verifiche: `PAD = 6`, `SECTION_AIR = 16`, `CARD_INSET = 8`, `CARD_RADIUS = 6` | `Space.S`, `Space.XL`, `Space.M`, `Radius.CONTROL` |
  | Verifiche: riga 34 | `Size.NAV` se si accetta il significato comune «riga di elenco»; altrimenti nuovo `Size.ROW = 34` |
  | Verifiche: coordinate 4, 2, 8, 4 della pillola | `Space.XS`, `Space.XXS`, `Space.M`, `Space.XS` |
  | Verifiche: indentazione 16, spazio bottoni 2 | `Space.XL`, `Space.XXS` |
  | fasi: icone 24 e 22; margini 4; spazi 2; +4 e +6 dei bottoni | `Icon.TILE`, `Icon.BAR`; `Space.XS`; `Space.XXS`; `Space.XS`, `Space.S` |
  | fasi: linee da 1; margine verticale 1; `inside + 3` | `Line.HAIR`; `Space.XXS + Line.HAIR` per il 3 |
  | Meridio: margini domande 4, 2; spazio 6; numero 12 | `Space.XS`, `Space.XXS`; `Space.S`; `Space.L` |
  | Meridio: bordi da 1; conversazione minima 24 | `Line.HAIR`; `Size.CHIP` |
  | `help_box.BUTTON = 16` | `Button.HELP[0]`, già definito e non usato lì |
  | aiuto: margini 2, 4, 2, 2; spazi 2; manuale 8 | `Space.XXS`, `Space.XS`, `Space.XXS`, `Space.XXS`; `Space.XXS`; `Space.M` |
  | impianto: spazi 8, 4, 2; griglia 8 | `Space.M`, `Space.XS`, `Space.XXS`; `Space.M` |
  | barra vista: margini 2; icone 16; separatore 1 x 16 | `Space.XXS`; `Icon.CONTROL`; `Line.HAIR` e `Space.XL` |
  | barra sole: margini 8 e spazio 8; testo +4 | `Space.M`; `Space.XS` |
  | anteprima relazione: margine laterale 16 e bordo +2 | `Space.XL`; `2 * Line.HAIR` |
  | aspetto: cerchio 28; elenco 76 | `Size.CONTROL`; `2 * Size.NAV + Space.M` |
  | `charts_pg.py:183`, margine 4 | `Space.XS` |
  | `panels`, `popups`, `fades`, `cards`: fallback già uguali ai token | helper `default_tokens()` esistente in `cards.py:178-179`, senza nuovi valori |

  **Valori che richiedono un token nuovo o una scelta sul valore**

  | Valore attuale | Destinazione proposta |
  |---|---|
  | Verifiche: fondo dettaglio 10 | `Space.M = 8` o `Space.L = 12` dopo schermata |
  | Verifiche: margine azioni `CARD_INSET + 6 = 14` | nuovo `Layout.CHECK_ACTIONS_RIGHT = 14` per conservare; altrimenti `Space.XL = 16` |
  | Verifiche: scostamento testo 5 | `Space.XS + Line.HAIR`, già 5 |
  | Verifiche: larghezza minima dettaglio 80 | nuovo `Size.DETAIL_MIN = 80` |
  | Verifiche: quota fonte 0,28 | nuovo `Layout.SOURCE_SHARE = 0.28`, non è una misura in px |
  | fasi: barre 68 e 44 | nuovi `Size.PHASE_BAR_TEXT = 68`, `Size.PHASE_BAR_ICONS = 44` |
  | fasi: disco 20 | nuovo `Size.BADGE = 20` |
  | fasi: `TAB_PAD` 10 e 16; `CARD_PAD` 10, 6, 10, 5 | 16 è `Space.XL`; 10 e 5 richiedono `Layout.PHASE_TAB_LEFT` e `Layout.PHASE_CARD_PAD` se restano, oppure normalizzazione dopo schermata |
  | fasi: icona File 15 | nuovo `Icon.FILE = 15`, oppure `Icon.CONTROL` dopo prova |
  | Meridio: raggio 10 e scivolata 10 | `Radius.CARD = 8` e `Space.M = 8` dopo prova; altrimenti nuovi `Radius.BUBBLE = 10`, `Layout.BUBBLE_SLIDE = 10` |
  | Meridio: punti 14, maniglia 14 | nuovi `Size.DOTS = 14`, `Size.GRIP = 14` |
  | Meridio: margini interni 10, 8 | `Space.L = 12` o `Space.M = 8` dopo schermata |
  | Meridio: soglie 220 e 260 | nuovi `Layout.BUBBLE_OPEN_MIN = 220`, `Layout.QUESTIONS_MIN = 260` |
  | aiuto: margini 12, 10 e 10, 8 | il 10 va a `Space.M` o `Space.L` dopo schermata |
  | aiuto: popup 280, capitoli 220, dialogo 320 x 220, manuale 940 x 680 | nuovi `Size.HELP_POPUP = 280`, `Size.MANUAL_NAV = 220`, `Size.HELP_DIALOG = (320, 220)`, `Size.MANUAL_WINDOW = (940, 680)` |
  | aiuto: soglia pannello 480 | nuovo `Layout.HELP_LOWEST = 480` |
  | impianto: campione 10 e raggi 3 | nuovo `Size.LEGEND_SWATCH = 10` per conservare; raggio a `Radius.MARK = 2` o `Radius.INNER = 4` dopo prova |
  | impianto: `sizeHint` 240 x 320 e minimo 180 x 120; elenco 200 | nuovi `Size.PLANT_HINT = (240, 320)`, `Size.PLANT_MIN = (180, 120)`, `Size.STRING_LIST = 200` |
  | barra sole: cursore minimo 80 | nuovo `Size.SUN_SLIDER_MIN = 80` |
  | barra sole: margine verticale 3 | `Space.XS = 4` o `Space.XXS = 2` dopo schermata |
  | barra vista: margine separatore 3 | `Space.XS = 4` o `Space.XXS = 2`; padding `Space.XL + 2 = 18` già esprimibile senza nuovo token |
  | barra attesa: larghezza 120 | nuovo `Size.PROGRESS = 120` |
  | nord 30 x 50; scala massima 120 | nuovi `Size.NORTH = (30, 50)`, `Size.SCALE_BAR_MAX = 120` |
  | cubo 150, cubo disegnato 64, anello 50 | nuovi `Size.VIEWCUBE = 150`, `Size.VIEWCUBE_BODY = 64`, `Size.VIEWCUBE_RING = 50` |
  | campo gizmo 64 | nuovo `Size.GIZMO_FIELD = 64` |
  | pagina File 250 e testo 760 | nuovi `Size.FILE_NAV = 250`, `Size.FILE_LEAD = 760` |
  | anteprima relazione massima 820 | nuovo `Size.REPORT_PREVIEW_MAX = 820` |
  | Proprietà 260; dialogo modello 220 x 160; anteprima IFC 320 x 220 | nuovi `Size.PROPERTIES_MIN = 260`, `Size.TEMPLATE_DIALOG = (220, 160)`, `Size.IFC_PREVIEW = (320, 220)` |
  | finestra stretta 1000; finestra bassa 900 | nuovi `Layout.NARROW = 1000`, `Layout.LOW_WINDOW = 900` |

  Le larghezze minime calcolate dal contenuto non vanno congelate in token: per esempio i campi data, le etichette
  del sole e le colonne delle fonti dipendono dai testi e dal font.

- **Rischio della correzione**: basso per le sostituzioni esatte, medio per i nuovi token, alto se si normalizzano
  tutti i valori senza guardare le schermate. Non creare un generico `Size.MEDIUM`: nasconderebbe il significato.

### 5. I fallback colore divergono dai token anche quando non c'è un difetto visibile oggi

- **File e righe**: `src/meridiana/ui/file_page.py:126`; `src/meridiana/ui/assistant.py:345-346`;
  `src/meridiana/ui/viewcube.py:39-40`; `src/meridiana/ui/panel_buttons.py:25`;
  `src/meridiana/ui/sections.py:21`; `src/meridiana/ui/waiting.py:290`, `:311`;
  `src/meridiana/ui/appearance.py:36`, `:42`; `src/meridiana/ui/plant_page.py:169-170`, `:334`;
  `src/meridiana/ui/cards.py:193-194`, `:219`; `src/meridiana/ui/popups.py:25`;
  `src/meridiana/ui/fades.py:20`; `src/meridiana/ui/cards.py:100`.
- **Che cosa succede**: molti componenti ricevono `set_colours` prima di essere mostrati, quindi il fallback non è
  necessariamente visibile. Ma alcuni fallback non corrispondono nemmeno al tema predefinito: un uso autonomo del
  widget o un cambio nell'ordine di costruzione mostrerebbe un altro aspetto.
- **Scenario concreto**: `FilePage` usa `#efede8` come finestra, mentre il token è `#f2f1ed`; le sezioni usano
  `#5f5a52` invece di `text2 = #514c44`; Meridio usa `line = #d8d3c9` invece di `#d9d5cc`.
- **Gravità**: bassa. È soprattutto un rischio di regressione e un costo di manutenzione, non un difetto visibile
  dimostrato nella finestra attuale.
- **Prova**: [V] confronto numerico con i token derivati; [V] `MainWindow._theme_changed` aggiorna questi componenti
  (`window.py:1070-1118`). Non ho classificato i fallback come errori visibili certi.
- **Correzione proposta**: usare un unico helper per i token predefiniti, come `cards.default_tokens()`, e queste
  corrispondenze, senza creare colori nuovi:

  | Fallback | Token o costante esistente |
  |---|---|
  | `FilePage`: window, panel, line | `window`, `panel`, `card_line` |
  | Meridio: text, assistant, panel, line, muted | `text`, `assistant`, `panel`, `line`, `muted` |
  | cubo: face, edge, line, text, hot, hot_ink, ring | `panel`, `line_soft`, `muted`, `text`, `select_bg`, `text`, `muted` |
  | pulsanti pannelli: on, off | `text2`, `muted` |
  | titoli sezioni | `text2` |
  | scheletro 3D: ink | `muted`; cielo e suolo restano in `view_colours` |
  | anteprima Aspetto: character | `assistant`, oggi già `#334f6d`; contorno `#24211d` può usare `assistant.INK`, già esistente |
  | impianto: text, muted, stati | `text`, `muted`, `theme_colors.STATUS`; non i colori delle serie dei grafici |
  | `CardTitle`, `CloseButton`, `popups`, `fades`, angoli viste | token `text`, `header`, `muted`, `line`, `panel`; nessuna nuova costante |

- **Rischio della correzione**: basso, ma va mantenuta l'inizializzazione prima dei widget e vanno provati i
  componenti anche da soli. Un helper che importa moduli pesanti sarebbe controproducente.

### 6. La carta ha una seconda palette separata, ma dispersa fra due moduli

- **File e righe**: `src/meridiana/ui/report.py:39-64`; `src/meridiana/ui/report_chapters.py:26-35`.
- **Che cosa succede**: PDF e anteprima usano colori per la carta che non devono diventare automaticamente quelli
  della finestra. Però `MUTED`, `RULE`, `HEAD`, `MARK_COLOURS`, `PLAN` e `STRING_HUES` sono costanti locali separate
  dallo stile della finestra e in parte diverse dai colori dei grafici su schermo.
- **Scenario concreto**: si rivede il grigio secondario della relazione. Bisogna sapere che `MUTED` è in
  `report_chapters`, mentre `RULE` e `HEAD` sono in `report`: il sistema grafico non lo dichiara.
- **Gravità**: bassa. Non propongo di applicare i token della finestra alla carta, ma di rendere esplicita la palette
  indipendente.
- **Prova**: [V] lettura dei due moduli e di `report_chapters`, che importa invece `CHROME` dai grafici.
- **Correzione proposta**: un `ui/report_style.py` con `PAPER`, `PAPER_STATUS`, `PAPER_PLAN` e `PAPER_STRING_HUES`,
  mantenendo i valori attuali. `INK` può restare `CHROME["light"]["ink"]`; `MUTED = #6b675f`, `RULE = #d9d4ca`,
  `HEAD = #f1eee8`, i quattro `MARK_COLOURS`, i sette `PLAN` e i dieci `STRING_HUES` restano valori della carta.
  `QColor("white")` nelle immagini PDF resta il bianco della pagina, non un token UI.
- **Rischio della correzione**: basso se è solo spostamento. Il rischio da evitare è applicare il tema scuro alla
  relazione stampata o alla sua anteprima.

## Piano consigliato

1. **Senza cambiare un pixel**: sostituire `theme_colors.STATUS` dove esiste, `Button.HELP`, `Space`, `Radius`,
   `Icon` e `Size` già equivalenti; introdurre i nomi `Timing` conservando ogni durata; usare i token predefiniti per
   i fallback.
2. **Ruoli nuovi con test**: `danger` nelle pagine, `checks_card`, `checks_hover`, `STATUS.info` e gli inchiostri dei
   segni. Estendere le prove di contrasto e il test statico del sistema ai componenti, non soltanto al foglio.
3. **Misure componenti**: aggiungere soltanto i token semantici elencati, conservando i valori attuali. Raggruppare
   i minimi condivisi, soprattutto `CHART_MIN_HEIGHT`.
4. **Scelte estetiche vere**: 10 e 14 px, raggio 10, raggi 3, chiusura a 130 ms, scivolata a 320 ms. Preparare la
   galleria prima/dopo in chiaro e scuro e far decidere a Daniel valore per valore. Non approvare una normalizzazione
   indistinta.
5. **Verifica**: `tests/finestra/test_design_system.py`, tutti i gruppi, `ruff`; schermate della galleria e delle
   fasi nei due temi. Claude misura `tools/fluidity.py` quando cambiano durate o debounce. La resa 3D non è valutata
   offscreen.

Una prova utile da aggiungere solo dopo approvazione è un inventario statico che fallisca su nuovi valori letterali
fuori dal catalogo, con una piccola lista di eccezioni geometriche e di dominio. Deve leggere le chiamate Qt e non
bandire numeri indiscriminatamente, altrimenti produrrebbe falsi positivi su font, coordinate e dati.

Nessun file di codice è stato modificato per questo rapporto.
