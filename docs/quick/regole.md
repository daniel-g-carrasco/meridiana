# Le regole della casa della Quick

Le undici regole di `docs/revisioni/piano-riordino-r21.md` (sezione 5), ciascuna con la guardia che la tiene e il
componente da usare. I componenti sono quelli di `src/meridiana/quick/qml/Meridiana/Controls/qmldir` oggi
(07/11/2026, punta di `r20-unita`); dove la regola chiede un componente che ancora non c'è, è scritto quale fetta lo fa.

**La guardia principale** è `tests/quick/sistema/test_riordino.py`: legge `tools/censimento_riordino.py` e confronta ogni
conteggio con un tetto scritto nella prova, «mai più di oggi». Una riga nuova fuori regola fa rosso con file, riga e
componente da usare; un tetto lasciato più alto del censimento fa rosso anche lui (la fetta lo abbassa, in due righe:
il numero in `CEILINGS` e `--aggiorna` per la base delle righe note). `python tests/quick/sistema/test_riordino.py` stampa
la tabella; `--righe <guardia>` tutte le righe di una guardia.

| # | Regola | Guardia (tetto al 07/11) | Da usare |
|---|---|---|---|
| 1 | Fuori da `Controls/` nessun controllo di `QtQuick.Controls` | `controlli_grezzi` 96, 48 dopo F2 (r22-f2: popup, menu, tendine, campi a zero), 18 dopo F1 (r23-f1: le pagine che scorrono sono `M.ScrollPage`; restano 9 righe del prototipo legacy e lo `SplitView` del Workbench per F5, e 8 aree lasciate con il perché, elencate in `docs/quick/stato/r23-f1.md`) | `M.ScrollPage`, `M.List`, `M.ComboBox` (l'unica tendina: `model` di Qt oppure `options`/`value`/`chosen`, con `searchable`), `M.Popup` (il pannello che si apre attaccato al suo pulsante o campo: sotto, sopra, o `centered` modale), `M.Menu`, `M.MenuItem`, `M.ToolTip`, `M.Dialog`, `M.Button`, `M.ToolButton`, `M.CheckBox`, `M.RadioButton`, `M.Slider`, `M.NumberField`, `M.TextField`, `M.TextArea` (`bare` per un testo letto in pagina; in un `M.ScrollPage` con `follow` quando deve scorrere), `M.Tabs`, `M.Card`, `M.Section`, `M.Label`, `M.ProgressBar`, `M.SplitHandle`; la prova dice quale per ogni riga |
| 2 | Ogni area che scorre ha `M.ScrollBar` (corsia, velature, rimbalzo) | `barre_qt` 9, 2 dopo F1 (le due del prototipo legacy di `quick/Main.qml`, le toglie F5) | `M.ScrollPage` per una pagina (`leftMargin`, `air`, `airInside`, `spacing` al posto dei margini scritti nella `Flickable`; `groundAbove` quando sta su un fondo che non è il pannello: finestra, scheda, riquadro); `M.List` per una lista di testi; **una `ListView` con un delegato suo** (risultati, catalogo, verifiche, albero, impianto) **resta `ListView` con `M.ScrollBar` attaccata** e le righe che finiscono a `room` (R520): `M.List` non prende un `delegate` proprio, perché diventerebbe una seconda `ListView` con un nome diverso. La guardia `controlli_grezzi` non conta le `ListView` con `M.ScrollBar` né quelle con `interactive: false` (intestazione e totali mossi da un'altra vista); `M.EdgeFades` per le velature da sole |
| 3 | Ogni misura, spazio, raggio, colore, curva e durata viene da `Theme` o `ControlMetrics`; un valore nuovo nasce lì con il suo perché | `misure_a_numero` 72, `colori_esadecimali` 49, `colori_in_controls` 6, `easing_a_mano` 44, `durate_a_mano` 5; zero a fine F3 (colori) e F4 (misure, movimento) | `Theme.space`, `Theme.size`, `Theme.radius`, `Theme.line`, `Theme.type`, `Theme.colors` (`Theme.status`, `Theme.options`), `Theme.motion`, `Theme.icon`; `ControlMetrics` per le misure dei controlli |
| 4 | Ogni simbolo è un `M.Icon`; il punto elenco e il trattino dei valori mancanti sono testo | `unicode_come_simbolo` 0 (F3) e `test_simboli.py` (`KNOWN` vuoto; `test_one_help_mark`: un solo «?» d'aiuto) | `M.Icon` con il nome del provider (`quick/backend/controls.py`); `M.HelpMark`, `M.PointerSign`, `M.CheckMark` (interno) per i segni già disegnati. **Il «?» d'aiuto è uno solo, `M.HelpMark`**: l'icona tonda `circle-question-mark` a 12 px in un pulsante piatto di 20, con l'hover dei pulsanti piatti, nella testata di schede e sezioni e nelle tessere; nessun altro pulsante con «?» né altra `circle-question-mark` (i comandi «Aiuto» della barra di stato e della pagina File sono comandi, non segni) |
| 5 | Ogni finestra è un `M.Dialog`: una barra di pulsanti, un solo fondo | i `Popup` grezzi contano nella regola 1; `test_popup_frames.py` legge i menu fotogramma per fotogramma (R476, R480, R491); le finestre in `docs/quick/stato/r20-finestre.md` | `M.Dialog`; `M.Menu` per ciò che si apre da un pulsante |
| 6 | Una sola voce di menu, una sola tendina, una sola sezione, una sola tabella, una sola pillola: il nome del componente è l'unico posto dove quella cosa si disegna | nessuna guardia a conteggio: l'elenco qui sotto è il metro; i doppioni noti sono i file di F2 e F5 (`ResultChoice`, `PropertyChoice`, `Selector`, `UnderlayMenu`, `CollapsibleSection`, `ViewPill`; le tabelle a mano `PlantTable`, `VirtualResultTable`, `CommonResultTable` e il delegato del confronto sono su `M.Table` da r23-tabelle, resta la tabella del catalogo, con il perché in `docs/quick/stato/r23-tabelle.md`) | voce `M.MenuItem` (`M.MenuSeparator`), tendina `M.ComboBox`, sezione `M.Section` (`M.SectionBand`), tabella `M.Table`, pillola `M.CountPill` e `M.Badge` (F5 le porta a una famiglia sola), scheda `M.Card`, linguette `M.Tabs`, segmenti `M.Segments`, albero `M.Tree`, righe a chiave `M.KeyedRows`, gruppo `M.InfoGroup`, vuoto `M.EmptyState`, pulsante doppio `M.SplitButton`, campo sovrapposto `M.OverlayField`, contorno di rilascio `M.DropOutline` |
| 7 | Il Python non cerca oggetti QML per nome e non scrive le loro proprietà: espone proprietà e segnali, il QML li lega | `findChild_nel_backend` 40, `setProperty_nel_backend` 55; zero a fine F6 (c) | `Property` e `Signal` sull'oggetto di backend, `parts.py` lo monta, il QML fa binding |
| 8 | Un modulo di backend sotto le 800 righe | `moduli_backend_oltre_800` 8 (`plan`, `assistant_chat`, `dialogs`, `plan_edit`, `catalog`, `scene`, `plant`, `shell_compute`); zero a fine F6 (d) | un modulo per argomento |
| 9 | Un catalogo solo, UTF-8 valido, nessuna chiave doppia, nessuna voce senza riferimento | `po_codifica_rotta` 0, `po_chiavi_doppie` 0; `tools/compile_po.py --check` (F7 lo estende alle voci senza riferimento e lo mette in CI) | `backend.tr(...)` dal QML, `_()` nel Python; `msgctxt "plan"` quando F7 unisce `quick-plan` |
| 10 | Nelle prove nessuna attesa a tempo fisso senza un perché, ogni cartella con `__init__.py`, ogni modulo sulla base comune | `prove_senza_init` 0, `attese_qWait` 340, `attese_time_sleep` 56 (F8 li abbassa con `qWaitFor` e la base `QuickCase`) | `qWaitFor(condizione)`; `tests/_setup.py` (`keep_global_state`, `end_qt`) |
| 11 | Ogni componente nuovo di `Controls/` arriva nel modello `qt-app-template` con il suo commit di provenienza entro la revisione successiva | nessuna guardia automatica: elenco in `docs/da-dove-viene.md` del modello, da controllare a ogni «porto nel modello» | il componente così com'è in `Controls/`, con il commit nel registro |

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
`quick/backend/plan_edit.py` (`click`, `select_area`), `Plan/SelectionOverlay.qml` (il segno),
`View3D/Viewport.qml` e `backend/scene.py` (`beginVertex`, `selectVertices`); prove `quick/pianta/test_edit.py`
(`test_the_rule_of_the_selection_r529`) e `quick/percorsi/test_native_clic.py` (mouse e tastiera veri).

## Come si legge un rosso

```
Regola 3, misure, spazi e raggi scritti a numero: 73 oggi, tetto 72 (1 di troppo).
  Da usare: Theme.space / Theme.size / Theme.radius / ControlMetrics; un valore nuovo nasce lì con il suo perché.
  Righe nuove (non in riordino_base.json):
    src/meridiana/quick/qml/Meridiana/Shell/ProvaRossa.qml:5  spacing 8 -> Theme.space
  Per file: ProjectTreePage.qml 8, SiteMap.qml 6, ...
```

La riga nuova è la prima cosa che si legge: file, riga, cosa c'è e cosa usare. Se la base è vecchia (nessuna riga
nuova ma il conteggio è salito), `--aggiorna` la rifà e il rosso si rilegge.

## Come una fetta abbassa il suo tetto

1. Finito il lavoro, `python tests/quick/sistema/test_riordino.py`: le guardie scese dicono «abbassa il tetto a N».
2. Scrivere N in `CEILINGS` (un tetto scende soltanto; nel commento accanto c'è la fetta che lo porta a zero).
3. `python tests/quick/sistema/test_riordino.py --aggiorna` rifà `riordino_base.json`.
4. Nello stato della fetta (`docs/quick/stato/r21-<fetta>.md`) i numeri prima e dopo.
