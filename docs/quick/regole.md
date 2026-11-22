# Le regole della casa della Quick

Le undici regole di `docs/revisioni/piano-riordino-r21.md` (sezione 5), ciascuna con la guardia che la tiene e il
componente da usare. I componenti sono quelli di `src/meridiana/gui/qml/Meridiana/Controls/qmldir` oggi
(07/11/2026, punta di `r20-unita`); dove la regola chiede un componente che ancora non c'è, è scritto quale fetta lo fa.

**La guardia principale** è `tests/quick/sistema/test_riordino.py`: legge `tools/censimento_riordino.py` e confronta ogni
conteggio con un tetto scritto nella prova, «mai più di oggi». Una riga nuova fuori regola fa rosso con file, riga e
componente da usare; un tetto lasciato più alto del censimento fa rosso anche lui (la fetta lo abbassa, in due righe:
il numero in `CEILINGS` e `--aggiorna` per la base delle righe note). `python tests/quick/sistema/test_riordino.py` stampa
la tabella; `--righe <guardia>` tutte le righe di una guardia.

| # | Regola | Guardia (tetto al 07/11) | Da usare |
|---|---|---|---|
| 1 | Fuori da `Controls/` nessun controllo di `QtQuick.Controls` | `controlli_grezzi` 96, 48 dopo F2 (r22-f2: popup, menu, tendine, campi a zero), 18 dopo F1 (r23-f1: le pagine che scorrono sono `M.ScrollPage`; restano 9 righe del prototipo legacy e lo `SplitView` del Workbench per F5, e 8 aree lasciate con il perché, elencate in `docs/quick/stato/r23-f1.md`) | `M.ScrollPage`, `M.List`, `M.ComboBox` (l'unica tendina: `model` di Qt oppure `options`/`value`/`chosen`, con `searchable`), `M.Popup` (il pannello che si apre attaccato al suo pulsante o campo: sotto, sopra, o `centered` modale), `M.Menu`, `M.MenuItem`, `M.ToolTip`, `M.Dialog`, `M.Button`, `M.ToolButton`, `M.CheckBox`, `M.RadioButton`, `M.Slider`, `M.NumberField`, `M.TextField`, `M.TextArea` (`bare` per un testo letto in pagina; in un `M.ScrollPage` con `follow` quando deve scorrere), `M.Tabs`, `M.Card`, `M.Section`, `M.Label`, `M.ProgressBar`, `M.SplitHandle`; la prova dice quale per ogni riga |
| 2 | Ogni area che scorre ha `M.ScrollBar` (corsia, velature, rimbalzo) | `barre_qt` 9, 2 dopo F1 (le due del prototipo legacy di `quick/Main.qml`, le toglie F5) | `M.ScrollPage` per una pagina (`leftMargin`, `air`, `airInside`, `spacing` al posto dei margini scritti nella `Flickable`); `M.List` per una lista di testi; **una `ListView` con un delegato suo** (risultati, catalogo, verifiche, albero, impianto) **resta `ListView` con `M.ScrollBar` attaccata** e le righe che finiscono a `room` (R520): `M.List` non prende un `delegate` proprio, perché diventerebbe una seconda `ListView` con un nome diverso. La guardia `controlli_grezzi` non conta le `ListView` con `M.ScrollBar` né quelle con `interactive: false` (intestazione e totali mossi da un'altra vista). **Le sfumature ai bordi (R624)** sono una sola, `M.EdgeFades`: il contenuto che diventa trasparente verso il bordo (strato con lo shader `edgefade.frag`, lunghezza `Theme.size.FADE`), messo solo dai componenti di scorrimento (`M.ScrollPage`, `M.List`, `M.Tree`, `M.Table`, `M.Dialog`, `M.ScrollBar`) con `flickable` e al più `barRoom` (e `held`, le testate tenute di `M.ScrollPage`, R633); nessuna sfumatura fatta a mano (gradiente, maschera, shader): guardia `tests/quick/sistema/test_sfumature_r624.py`, con le eccezioni e il perché; come appare, `tests/quick/controlli/test_dissolvenza_r624.py` su Direct3D 11 |
| 3 | Ogni misura, spazio, raggio, colore, curva e durata viene da `Theme` o `ControlMetrics`; un valore nuovo nasce lì con il suo perché | `misure_a_numero` 72, `colori_esadecimali` 49, `colori_in_controls` 6, `easing_a_mano` 44, `durate_a_mano` 5; zero a fine F3 (colori) e F4 (misure, movimento) | `Theme.space`, `Theme.size`, `Theme.radius`, `Theme.line`, `Theme.type`, `Theme.colors` (`Theme.status`, `Theme.options`), `Theme.motion`, `Theme.icon`; `ControlMetrics` per le misure dei controlli |
| 4 | Ogni simbolo è un `M.Icon`; il punto elenco e il trattino dei valori mancanti sono testo | `unicode_come_simbolo` 0 (F3) e `test_simboli.py` (`KNOWN` vuoto; `test_one_help_mark`: un solo «?» d'aiuto) | `M.Icon` con il nome del provider (`quick/backend/controls.py`); `M.HelpMark`, `M.PointerSign`, `M.CheckMark` (interno) per i segni già disegnati. **Il «?» d'aiuto è uno solo, `M.HelpMark`** (R596, 13/11/2026): disco pieno grigio di `Theme.icon.CONTROL` col «?» del carattere in una zona di 20, grigi `help_disc*` che si scuriscono al passaggio e premuto, anello del fuoco tondo come la scelta singola, filo sottile deciso dal fondo (`Theme.helpEdge`); apre la nuvoletta con l'unico ingresso `M.Help.show(chiave, segno)` (R597, `M.HelpBubble` sopra `M.Popup` con punta), nella testata di schede e sezioni e nelle tessere; nessun altro pulsante con «?» né altra `circle-question-mark` (i comandi «Aiuto» della barra di stato e della pagina File sono comandi, non segni) |
| 5 | Ogni finestra è un `M.Dialog`: una barra di pulsanti, un solo fondo | i `Popup` grezzi contano nella regola 1; `test_popup_frames.py` legge i menu fotogramma per fotogramma (R476, R480, R491); le finestre in `docs/quick/stato/r20-finestre.md` | `M.Dialog`; `M.Menu` per ciò che si apre da un pulsante |
| 6 | Una sola voce di menu, una sola tendina, una sola sezione, una sola tabella, una sola pillola: il nome del componente è l'unico posto dove quella cosa si disegna | nessuna guardia a conteggio: l'elenco qui sotto è il metro; i doppioni noti sono i file di F2 e F5 (`ResultChoice`, `PropertyChoice`, `Selector`, `UnderlayMenu`, `CollapsibleSection`, `ViewPill`; le tabelle a mano `PlantTable`, `VirtualResultTable`, `CommonResultTable` e il delegato del confronto sono su `M.Table` da r23-tabelle, resta la tabella del catalogo, con il perché in `docs/quick/stato/r23-tabelle.md`) | voce `M.MenuItem` (`M.MenuSeparator`), tendina `M.ComboBox`, sezione `M.Section` (`M.SectionBand`), tabella `M.Table`, pillola `M.CountPill` e `M.Badge` (F5 le porta a una famiglia sola), scheda `M.Card`, linguette `M.Tabs`, segmenti `M.Segments`, albero `M.Tree`, righe a chiave `M.KeyedRows`, gruppo `M.InfoGroup`, vuoto `M.EmptyState`, pulsante doppio `M.SplitButton`, campo sovrapposto `M.OverlayField`, contorno di rilascio `M.DropOutline` |
| 7 | Il Python non cerca oggetti QML per nome e non scrive le loro proprietà: espone proprietà e segnali, il QML li lega | `findChild_nel_backend` 40, `setProperty_nel_backend` 55; zero a fine F6 (c) | `Property` e `Signal` sull'oggetto di backend, `parts.py` lo monta, il QML fa binding |
| 8 | Un modulo di backend sotto le 800 righe | `moduli_backend_oltre_800` 8 (`plan`, `assistant_chat`, `dialogs`, `plan_edit`, `catalog`, `scene`, `plant`, `shell_compute`); zero a fine F6 (d) | un modulo per argomento |
| 9 | Un catalogo solo, UTF-8 valido, nessuna chiave doppia, nessuna voce senza riferimento | `po_codifica_rotta` 0, `po_chiavi_doppie` 0; `tools/compile_po.py --check` (F7 lo estende alle voci senza riferimento e lo mette in CI) | `backend.tr(...)` dal QML, `_()` nel Python; `msgctxt "plan"` quando F7 unisce `quick-plan` |
| 10 | Nelle prove nessuna attesa a tempo fisso (qWait, time.sleep) senza il suo perché sulla stessa riga, nella forma `# wait: <motivo>` (Daniel 21/11/2026: le altre si riscrivono con una condizione; la guardia conta solo quelle senza motivo), ogni cartella con `__init__.py`, ogni modulo sulla base comune | `prove_senza_init` 0, `attese_qWait` 340, `attese_time_sleep` 56 (F8 li abbassa con `qWaitFor` e la base `QuickCase`) | `qWaitFor(condizione)`; `tests/_setup.py` (`keep_global_state`, `end_qt`) |
| 11 | Ogni componente nuovo di `Controls/` arriva nel modello `qt-app-template` con il suo commit di provenienza entro la revisione successiva | nessuna guardia automatica: elenco in `docs/da-dove-viene.md` del modello, da controllare a ogni «porto nel modello» | il componente così com'è in `Controls/`, con il commit nel registro |

## Come si fa una finestra (R607, Daniel 14/11/2026)

Una finestra è un `M.Dialog` con dentro il solo contenuto: margini, testata, scorrimento e pulsanti sono suoi, e una
finestra nuova non scrive né misure né colori né pulsanti propri. Prova: `tests/quick/shell/test_finestre_r607.py`.

1. **Testata**: `title`; `subtitle` quando la finestra nomina una cosa sola (il file che legge), una riga, accorciata
   con i puntini; il testo intero, per un file il percorso, va in `subtitleTip` e compare nel suggerimento. Nomi brevi,
   mai percorsi (per i file `core/model/imported.file_stem`). La testata sposta la finestra; sopra di lei il puntatore
   è quello delle quattro frecce, come sui titoli dei pannelli.
2. **Corpo**: l'oggetto dichiarato dentro; scorre il corpo e solo lui (R601: nessuna barra dentro un'altra). Una pagina
   che scorre da sé dà `bodyScrolls: false`.
3. **Riga del lavoro**, quando la finestra mostra un lavoro: `M.WorkRow { row: work.slots.<posto> }` nel corpo, larga
   quanto il corpo. Sopra le parole: a sinistra titolo e fase (la fase prende il posto che resta, puntini e
   suggerimento), a destra in piccolo percentuale e «· tempo», larghi quanto il loro massimo; sotto il filo
   (`M.ProgressBar`: `ControlMetrics.progressThread` px, estremi tondi, traccia `line_soft`, fatto in `text2`, nessun
   accento; senza totale un pezzo di un quarto che scorre). Testi su una linea di base. Nella barra di stato la stessa
   riga in una linea (`inline: true`): titolo, fase in `ControlMetrics.workPhase`, filo che prende il resto, numeri,
   Annulla. Un avanzamento si disegna solo con questi due componenti.
4. **Un solo «Annulla»**: il lavoro di una finestra lo ferma l'«Annulla» della finestra (`rejectText`), che lo ferma e
   chiude; chi usa la finestra lega il rifiuto all'annullamento del lavoro. La riga del lavoro dentro una finestra non
   disegna il suo (lo legge da `stopsJobs` del corpo); fuori, nella barra di stato, lo tiene.
5. **Piede**: `acceptText`, `rejectText` a destra; le altre azioni in `actions`, a sinistra, sulla stessa riga. Nessuna
   fila di pulsanti nel corpo. Stessa altezza, stessa linea di base, l'ultimo al margine della finestra.
6. **Misure**: `ControlMetrics.dialogPad` sui quattro lati, `dialogGap` tra testata, corpo e piede, `dialogButtonGap`
   tra i pulsanti; la larghezza è `dialogWidth.normal` se la finestra non ne chiede un'altra in `dialogSize`.
7. **Si sposta e si ridimensiona** (R628, Daniel 15/11/2026): trascinata per la testata va ovunque sulla finestra del
   programma e può uscirne in parte, ma resta sempre `ControlMetrics.dialogHold` della testata dentro su ogni lato e la
   testata mai sopra il bordo alto; il programma rimpicciolito la riporta raggiungibile; si riapre al suo posto. Lati e
   angoli la ridimensionano (`dialogGrip` dentro la cornice, nel margine, senza segni: lo dice il puntatore), dal minimo
   (testata, piede, `dialogLeast.body` di corpo, la fila dei pulsanti) a tutta la finestra del programma; la grandezza
   scelta si ricorda per tipo (`sizeKey`, di solito l'`objectName`; le finestre di File per `kind`) in `M.DialogSizes`,
   salvata con la disposizione (`quick-shell.json`); il doppio clic su una maniglia torna a quella che chiede. Una
   finestra che non deve cambiare grandezza dà `resizable: false`. Prova: `tests/quick/shell/test_finestre_libere_r628.py`.
8. **Meridio sopra** (R628): le finestre stanno nello strato di Qt al gradino `Theme.stack.WINDOW`, Meridio sul suo palco
   (`assistantStage` del Workbench, `ASSISTANT`) sopra di loro, i menu e i suggerimenti (`POPUP`) sopra tutti. Con la
   tastiera nel fumetto di Meridio, Invio ed Esc sono suoi (`keyboardAway`): la finestra non preme il suo pulsante e
   non si chiude; chiuso il fumetto la tastiera torna alla finestra.

## Come si fa il corpo di un pannello (R631, Daniel 15/11/2026)

Il corpo di un pannello laterale fatto di sezioni (Proprietà, Impianto, i dati di Producibilità, Consumi e Bilancio,
Elaborati) è un `M.PanelPage` e solo lui: uno scorrimento per tutto il pannello, la barra a destra della scheda, fuori
dalle sezioni; le sezioni sono figlie della pagina (o di un modulo largo quanto lei) e non hanno margini propri.

1. **Margini** (R637, che sostituisce R633): ogni scheda agganciata (`Shell/DockPanel.qml`: i pannelli di destra,
   Progetto, Verifiche) tiene `ControlMetrics.cardMargin` (`Theme.space.L`, 12 px) tra il bordo e ciò che contiene sui
   quattro lati; in alto dalla riga del titolo (per le Verifiche, dalla riga dei loro strumenti). Lo dà il corpo della
   scheda (`Card.bodyMargin`); le pagine dentro non hanno margini propri (`M.PanelPage` senza margini né aria). La
   barra di scorrimento di ciò che riempie la scheda sta nel margine di destra (`M.ScrollBar.inMargin`), che la prende
   tutto (12 px): cursore di 4 centrato (4 e 4), 6 con il mouse sopra o trascinando (3 e 3), R655
   (`ControlMetrics.marginThumb`, `marginThumbHover`; uguali danno un cursore che non cambia). La rotella e il
   touchpad sopra una barra fanno scorrere la sua lista (R654). Fino a R637: pannelli 22 ai lati, 11 sotto il titolo,
   14 in fondo; Progetto 12 a sinistra; Verifiche 17 / 26 ai lati. `panelGap` tra due sezioni.
2. **Testate sempre in vista** (R633): mentre la pagina scorre, la testata di una sezione che uscirebbe in alto resta
   in cima, sotto quelle prima di lei; quelle delle sezioni sotto la pagina aspettano in fondo (`Controls/HeldHeads.qml`,
   messo da `M.ScrollPage` con `keepHeads`, cioè da `M.PanelPage`; le sezioni si annunciano da sole,
   `Section.headKeeper`). La testata tenuta è la testata della sezione disegnata una seconda volta
   (`Controls/SectionHead.qml`, la stessa al pixel); il contenuto passa sotto e si dissolve dal suo bordo
   (`EdgeFades.held`), mai sopra una testata al suo posto. La cornice della sezione non sfuma mai: la disegnano le
   testate tenute sopra ciò che scorre, dalla testata al fondo vero della sezione o al bordo visibile, dove si chiude
   arrotondata (la fascia della testata arrotonda il suo piede quando sotto non si vede più il corpo). In cima e in fondo al più un quarto della pagina ciascuno
   (`ControlMetrics.heldShare`): oltre, le testate più lontane escono spinte dalla nuova. Il clic su una testata tenuta
   apre o chiude la sua sezione come al suo posto e porta la testata al suo posto in cima (la sezione in vista);
   Tab raggiunge le testate vere, mai le copie. I gruppi dentro una sezione non sono tenuti.
3. **Niente scorrimento dentro una sezione** (R601): il contenuto di una sezione è alto quanto ciò che contiene; una
   tabella dentro una sezione prende `wholeHeight` (`M.Table`) e mostra tutte le righe.
4. **Gruppi dentro una sezione**: `M.Section` annidata (titolo sulla sua linea, `docs/design/sistema-grafico.md`,
   «Gruppo dentro un gruppo»), mai una scheda dentro una scheda.
5. **Eccezioni**: l'albero del Progetto (`M.Tree`) e le Verifiche (una `ListView` con `M.ScrollBar`) sono elenchi, non
   sezioni: lo scorrimento è il loro, uno solo.

Prove: `tests/quick/shell/test_pannelli_r631.py` (sul programma vero: margini uguali entro 1 px e un solo scorrimento
in ogni fase e in ogni sezione dell'Impianto; nei file: un corpo di pannello non si costruisce il telaio da sé);
`tests/quick/shell/test_testate_r633.py` (testate tenute in cima e in fondo, quota, clic, rotella, Tab; su Direct3D 11
la testata tenuta uguale al pixel e la dissolvenza dal suo bordo; sul programma vero la barra e le sezioni centrate).

## Le evidenziature (R617, Daniel 14/11/2026)

Un'evidenziatura dinamica (ciò che Meridio indica, una voce aperta da un'altra parte, il lato acceso di un disegno, la
selezione e ciò che sta sotto il puntatore in pianta) non scrive né colore, né spessore, né distacco, né durata: la scala
è `design.Highlight` (`Theme.highlight`), i colori sono quelli del tema e delle viste, con il loro significato.

1. **Intorno a un elemento dell'interfaccia**: `M.Highlight` (filo sottile nel grigio del fuoco, a `GAP` su tutti e
   quattro i lati, raggio = raggio dell'elemento + distacco, arriva più largo e si posa). Chi lo usa dà solo dove
   (`targetRect`, `radii`) e quando (`active`, `target`, `persistent`). Una riga senza spazio attorno (una fetta di
   scheda) lo prende `inside`, con il suo filo di bordo in `edgeLine`.
2. **Un lato acceso in pianta**: `M.LitSide` (`Theme.highlight.SIDE`, estremi tagliati sul lato), nel colore della
   selezione o del disegno; chi disegna con un pennello (l'anteprima delle finestre) prende `design.Highlight.SIDE`.
3. **In pianta, dal Python**: `plan.lit_pens` e i nomi di `design.Highlight`; nessun numero né colore a mano.
4. **L'anello del fuoco** resta di ogni controllo e solo da tastiera (`Theme.focusRing`), stesso grigio, `FOCUS`.

Prova: `tests/quick/sistema/test_evidenziature_r617.py` (i file del censimento, i due componenti, la centratura sui
pixel: i quattro distacchi entro 1 px, gli angoli concentrici, il lato centrato sulla sua linea).

## La regola della selezione (R529, Daniel 07/11/2026 sera)

Uguale in pianta e nel 3D, per moduli, edifici, oggetti e vertici; la dice la barra d'aiuto in basso e la dice il segno
accanto al puntatore (`M.PointerSign`):

| Gesto | Cosa fa | Segno |
|---|---|---|
| clic | sceglie solo quello: la selezione ricomincia (anche dopo una finestra); il secondo clic sullo stesso modulo dà la fila | nessuno |
| Maiusc+clic | aggiunge (se c'è già, resta) | «+» |
| Ctrl+clic | aggiunge o toglie: alterna | «+» su ciò che non c'è, «−» su ciò che c'è |
| finestra o lazo | la selezione ricomincia con ciò che prende | nessuno |
| Maiusc+finestra | aggiunge ciò che prende | «+» |
| Ctrl+finestra | toglie ciò che prende | «−» |

Eccezioni con un altro senso, dette nella barra: nell'albero del progetto Maiusc sceglie da qui a là, come in ogni
elenco; nella stringa a mano Maiusc+clic sposta un modulo da un'altra stringa; con Sposta e Ruota Ctrl copia; nel 3D
Maiusc con il trascinamento muove la vista, quindi la finestra sui vertici è semplice o con Ctrl. Codice:
`gui/backend/plan_edit.py` (`click`, `select_area`), `Plan/SelectionOverlay.qml` (il segno),
`View3D/Viewport.qml` e `backend/scene.py` (`beginVertex`, `selectVertices`); prove `quick/pianta/test_edit.py`
(`test_the_rule_of_the_selection_r529`) e `quick/percorsi/test_native_clic.py` (mouse e tastiera veri).

## Come si legge un rosso

```
Regola 3, misure, spazi e raggi scritti a numero: 73 oggi, tetto 72 (1 di troppo).
  Da usare: Theme.space / Theme.size / Theme.radius / ControlMetrics; un valore nuovo nasce lì con il suo perché.
  Righe nuove (non in riordino_base.json):
    src/meridiana/gui/qml/Meridiana/Shell/ProvaRossa.qml:5  spacing 8 -> Theme.space
  Per file: ProjectTreePage.qml 8, SiteMap.qml 6, ...
```

La riga nuova è la prima cosa che si legge: file, riga, cosa c'è e cosa usare. Se la base è vecchia (nessuna riga
nuova ma il conteggio è salito), `--aggiorna` la rifà e il rosso si rilegge.

## Come una fetta abbassa il suo tetto

1. Finito il lavoro, `python tests/quick/sistema/test_riordino.py`: le guardie scese dicono «abbassa il tetto a N».
2. Scrivere N in `CEILINGS` (un tetto scende soltanto; nel commento accanto c'è la fetta che lo porta a zero).
3. `python tests/quick/sistema/test_riordino.py --aggiorna` rifà `riordino_base.json`.
4. Nello stato della fetta (`docs/quick/stato/r21-<fetta>.md`) i numeri prima e dopo.
