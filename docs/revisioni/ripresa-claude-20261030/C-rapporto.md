# C: revisione indipendente del lotto C (R248, R249, R252, R253, R254, R257)

Opus C, 30/10/2026. Albero `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, nessun commit. Legenda: [V] verificato
(con la prova indicata), [D] dedotto, [N] non verificato.

## 1. Che cosa ho rivisto

- `src/meridiana/ui/dock_motion.py`: tutto (466 righe): `LayoutPreview`, `apply_target`, `Reflow`, `reflow`,
  `target_at`, `DockDrag`.
- `src/meridiana/ui/motion.py` (`git diff 23bd7a9`): `Entrance`, `enter`, `leave`, `Collapse`, `collapse`,
  `TreeMotion`, `SectionVeil`, `animate_tree`, registro `_RESPONSIVE`.
- `src/meridiana/ui/scrollbars.py` (`outer_inset`, `polish`, groove/slider/hit rect, style hint durata),
  `src/meridiana/ui/fades.py` (`attach`, registro), `src/meridiana/ui/file_page.py` (crossfade sezioni, entrata e
  uscita, tour), `src/meridiana/ui/cards.py` (`DockDrag`, `close_animated`), `src/meridiana/ui/panel_buttons.py`,
  `src/meridiana/ui/checks_page.py` (`animate_tree` per i gruppi), `src/meridiana/ui/theme.py` (la sola modifica,
  `row-pills`, è del lotto E, non di C).
- Prove `tests/widget/test_shared_motion.py`, `tests/finestra/test_design_system.py` (parti cambiate da C).

## 2. Difetti trovati e corretti

### 2.1 Due veli visibili riaprendo File durante l'uscita (punto 2; stesso difetto del modello Qt)
- [V] Riproduzione: `open_file_page("open")`, di nuovo `open_file_page("open")` (la comando alterna: chiude),
  `open_file_page("export")` → due `Entrance` visibili. `motion.leave` non era tracciata da `FilePage`, `open_page`
  non fermava nessun velo, e `enter`/`leave` non sostituivano il velo ancora sopra la stessa area.
- [V] Secondo difetto collegato: un velo fermato dall'esterno (o finito con «meno movimento» acceso e subito spento)
  non impediva alla sua `play` rimandata (`after_work`) di rimostrarlo: prova
  `test_less_motion_switched_on_and_off_before_the_exit_plays_leaves_no_veil` rossa prima della correzione.
- Correzione, allineata al modello Qt (Fable T, `T-rapporto.md` §4): `Entrance.cancel()`; `Entrance.play` e la
  `play` interna di `leave` escono se `done`; `FilePage.exit` tiene il velo d'uscita, `_left`, `_stop_entrance`
  (annulla entrata e uscita) chiamato in testa a `open_page` e a `close_page`; `self.exit = motion.leave(...)` con
  `finished -> _left`. In più (non ancora nel modello): `motion._replace(area)`, chiamato da `enter` e `leave`, che
  annulla qualunque `Entrance` ancora sopra la stessa area, per i chiamanti che non tengono il velo; `leave` toglie
  anche i `Veil` di crossfade rimasti dentro la pagina (altrimenti ricomparivano alla riapertura).
- Prove: `widget.test_shared_motion.SharedMotion.test_entering_again_while_leaving_keeps_one_veil`,
  `...test_a_cancelled_veil_never_plays_nor_shows_again` (gemella di quella del modello),
  `...test_less_motion_switched_on_and_off_before_the_exit_plays_leaves_no_veil`,
  `finestra.test_design_system.InTheWindow.test_file_opened_again_during_its_exit_shows_one_veil` (riapertura
  durante l'uscita e chiusura durante l'entrata). Rosse prima, verdi dopo.

### 2.2 Le sfumature automatiche sovrascrivevano la scelta esplicita e facevano scorrere l'Aiuto (R249)
- [V] `ScrollStyle.polish` chiama `fades.attach(area, air=True)` su ogni `QScrollArea`: aggiunge margini AIR
  (6+6 px) al viewport e, per la modifica di C (`edge.page = air ...`), ribalta la variante a ogni nuovo polish.
  La scheda Aiuto (`help_box._FitScroll`, alta quanto il testo) chiede sfumature semplici (`window.py` riga ~1230)
  ma riceveva comunque i margini: nella finestra vera margini 6/6 con `page False` (stato incoerente); a parità di
  testo di due righe la barra va a `maximum` 6-8 px invece di 0 (misura con e senza attach automatico).
- Correzione in `fades.attach(..., auto=False)`: con `auto=True` (solo il polish) non tocca un'area già sfumata, da
  chi la chiama o da un polish precedente; una chiamata esplicita senza `air` restituisce i margini che il polish
  aveva messo (`Fades.auto_margins`), qualunque sia l'ordine. `scrollbars.py` passa `auto=True`.
- Prove: `SharedMotion.test_automatic_fades_leave_an_explicit_variant_alone_in_either_order`,
  `InTheWindow.test_the_help_card_keeps_the_plain_fades_it_asked_for` (anche: Proprietà conserva AIR).

### 2.3 Il velo del collasso tagliava la pagina File (R253)
- [V] Con File aperta i pulsanti dei pannelli restano nella barra di stato. Un clic creava il `Reflow` sopra la
  pagina File, che si vedeva spezzata nei ritagli delle schede fino a fine movimento. Foto prima della correzione:
  `build/claude-r07/C-file-tagliato-dal-reflow-prima.png`.
- Correzione: `dock_motion._covered(window)`: se un fratello sopra le schede copre almeno metà dell'arena (File, la
  sua entrata) il cambio avviene subito, senza layer. Un overlay piccolo (Meridio) non conta.
- Prove: `DockMotion.test_a_page_over_the_cards_takes_the_change_at_once`,
  `InTheWindow.test_a_panel_toggled_under_file_changes_without_cutting_the_page` (rosse con `_covered` disattivato,
  verdi con la correzione).

### 2.4 Pannello flottante dipinto nel velo del collasso (R253)
- [V] `Reflow.__init__` includeva i dock flottanti (geometria in coordinate di schermo): una copia fantasma del
  pannello flottante compariva dentro la finestra e si «chiudeva» verso un bordo.
- Correzione: `_docked()` esclude flottanti e nascosti in `Reflow.__init__`, in `reflow.settle` e nell'annullo.
- Prova: `DockMotion.test_a_floating_panel_is_not_painted_into_the_reflow`.

### 2.5 Trascinamento non annullato se la finestra si nasconde o cambia DPR (punto 1)
- [V] Nascondendo la finestra a metà trascinamento Qt toglie la cattura del mouse ma `DockDrag` restava attivo, con
  il layer opaco tenuto aperto: alla nuova apparizione la finestra restava coperta da fotografie ferme.
- Correzione: il filtro dell'applicazione annulla su `WindowDeactivate`, `Hide`, `DevicePixelRatioChange` della
  finestra (`_CANCEL`).
- Prova: `DockMotion.test_hiding_the_window_or_changing_its_pixel_ratio_cancels_a_drag` (il cambio DPR è un evento
  sintetico: offscreen non cambia schermo [N] sul vero cambio di monitor).

### 2.6 Un `reflow` durante il trascinamento cancellava il layer sotto `DockDrag` (punto 1)
- [V] Un pannello alternato da tastiera mentre si trascina riusava il layer del trascinamento e lo chiudeva:
  `DockDrag.layer` restava su un oggetto cancellato; con «meno movimento» il layer veniva cancellato subito.
- Correzione: `Reflow.drag`; `reflow()` annulla prima il trascinamento in corso, in ogni ramo.
- Prova: `DockMotion.test_a_panel_toggled_during_a_drag_cancels_the_preview_first`.

### 2.7 Esc durante il trascinamento preso prima da una scorciatoia della finestra (punto 1)
- [V] Con un'azione Esc sulla finestra (le scorciatoie di Meridiana sono riassegnabili; di serie non ce n'è una su
  Esc) la scorciatoia scattava e il trascinamento restava aperto. Correzione: durante il trascinamento
  `ShortcutOverride` di Esc accettato.
- Prova: `DockMotion.test_escape_cancels_a_drag_before_a_window_shortcut_takes_it` (fuori dal trascinamento la
  scorciatoia funziona ancora).

### 2.8 Rilascio con `QPoint(0, 0)`
- [D] `... and self.origin` è falso per `QPoint(0, 0)` in PySide6 (verificato: `bool(QPoint(0,0)) is False`), quindi
  un clic all'origine dello schermo non chiudeva lo stato. Ora `is not None`. Nessuna prova dedicata.

## 3. Punti obbligati: esito

1. `dock_motion`: [V] nessun `restoreState` sul layout vero (solo sulla finestra di misura); `window.saveState()`
   è letto una volta per finestra di misura (sola lettura; le prove confrontano i byte prima/dopo). [V] Nessun
   `processEvents` nel risolutore (`_settle_layout` usa solo `activate`). [V] Risorse: la finestra di misura va
   con `deleteLater` a ogni cambio di bersaglio e alla fine; filtro dell'applicazione tolto in `finish`; `Reflow`
   cancellato a fine movimento; registro debole. Esc annulla e ripristina [V]. Chiusura/DPR: vedi 2.5.
2. Veli: vedi 2.1. `Collapse` ripetuto e invertito: rivisto, nessun difetto trovato [V con le prove di C]; vincoli
   ripristinati, nessun widget lasciato nascosto.
3. «Meno movimento» a metà: `Veil`, `Entrance`, `Collapse`, `TreeMotion`, `Reflow` sono nel registro e terminano
   subito [V prove di C]; la ricomparsa dopo spegni/riaccendi era il difetto 2.1 [V].
4. R248: misura nella finestra vera (capannone, 1400x900, scala 1), distanza fra thumb e linea della scheda: 9 px per
   tutte le aree che scorrono in Consumi, Impianto, Modello, Economia (pagine centrali, Dati/Proprietà, Aiuto,
   Verifiche) [V]; un valore 1 in Economia era un errore della mia scansione (ritaglio: ~8 px). Gutter riservato:
   `test_a_scroll_bar_that_comes_or_goes_moves_nothing` verde (la larghezza del viewport non cambia). R249: vedi 2.2.
5. Hover Verifiche a 2,5: [V] limite di QTest/offscreen. Con un semplice `QWidget` con mouse tracking (nessun codice
   di Meridiana, `build/claude-r07/C-qtest-mousemove-scala.py`): a scala 1 ogni `QTest.mouseMove` arriva; a scala 2
   e 2,5 alcuni movimenti non arrivano affatto e gli altri arrivano spostati di 1 px. Nel test delle Verifiche a 2,5
   il `mouseMoveEvent` del viewport non viene mai chiamato. Prova non allentata.

## 4. Difetti sospetti non confermati / osservazioni

- [D] Durante il collasso e per tutto il trascinamento il layer opaco copre anche Meridio flottante; la sua copia
  dentro la fotografia della scheda centrale si muove con la scheda. Cosmetico, non corretto.
- [D] `outer_inset` dà PAD a ogni `QScrollArea` fuori da un CardDock, anche dove la barra non è al bordo della scheda
  (colonna di navigazione di File, larghezza fissa `NAV_WIDTH + 8`: pulsanti 6 px più stretti; finestre di dialogo).
  Coerente con la convenzione, non cambiato.
- [D] Il polish automatico dà AIR anche all'anteprima del rapporto (`report_page.Preview`) e alle sezioni File;
  voluto da C per R249, non verificato a occhio da me.
- [N] Costo di `LayoutPreview.solve` (ricostruisce la finestra di misura a ogni cambio di bersaglio) non misurato.
- [D] `Reflow` resta alla geometria dell'arena di quando nasce: un ridimensionamento della finestra nei 110 ms del
  movimento non lo segue. `SectionVeil` resta fermo se si scorre durante i 110 ms.
- [D] `Collapse` ricorda i limiti d'altezza del chiamante: se il chiamante li cambia mentre la sezione è chiusa,
  all'apertura tornano quelli vecchi.

## 5. Modifiche richieste a file non miei

- Nessuna a `window.py` o `po/it.po`.
- Modello Qt (`qt-app-template`, al coordinatore): già con `cancel`/`exit`/`_stop_entrance` (T). Da riportare da
  Meridiana: `motion._replace` e la pulizia dei `Veil` in `leave`; `fades.attach(auto=...)` e `auto=True` in
  `scrollbars.ScrollStyle.polish`; in `dock_motion`: `_docked`, `_covered`, `Reflow.drag`, `_CANCEL`,
  `ShortcutOverride` di Esc, `origin is not None`; le prove corrispondenti di `test_shared_motion.py`.

## 6. msgid nuovi

Nessuno.

## 7. Prove eseguite

Ambiente delle regole, `python -m unittest` dalla cartella.
- Nuove prove prima della correzione: 9 rosse (più 2 rosse con `_covered` disattivato via monkeypatch).
- Dopo: `widget.test_shared_motion widget.test_fades widget.test_panel_edges widget.test_checks_page
  widget.test_help_box widget.test_assistant_widget widget.test_table_ux widget.test_template_controls
  finestra.test_design_system finestra.test_file_organization finestra.test_help_box finestra.test_checks_views
  finestra.test_new_project`: 134 OK (prima del porting di T). Nella prima esecuzione un fallimento in
  `test_assistant_widget` (angoli di Meridio): `assistant.py` era modificato da un altro agente durante l'esecuzione;
  da solo e il modulo intero ripetuto: verdi.
- Dopo il porting di T: `widget.test_shared_motion widget.test_fades widget.test_panel_edges
  widget.test_template_controls finestra.test_design_system finestra.test_file_organization finestra.test_new_project
  finestra.test_support_flow finestra.test_assistant_window nucleo.test_startup_r07 widget.test_navigation_targets`:
  78 prove, 77 OK, 1 rossa: `finestra.test_assistant_window.InTheWindow.test_ctrl_l_the_size_of_the_bubble_and_the_dock_are_kept_and_the_dock_has_its_own_button`
  (`356 not less than 260`, altezza del pannello di Meridio dopo `resizeDocks`). [V] Non dipende dalle mie
  modifiche: fallisce identica anche caricando le versioni di C prima della revisione di `motion.py`, `fades.py`,
  `scrollbars.py`, `file_page.py` (ricostruite da `23bd7a9` + `build/handoff-claude-20261030-R01/meridiana-tracked-final.patch`
  in una copia nello scratchpad) e con `fades.attach` riportato al comportamento di C. `assistant.py` è stato
  modificato da un altro agente alle 12:30 mentre lavoravo: da guardare con chi tiene Meridio/D.
- `QT_SCALE_FACTOR=2.5`: `widget.test_shared_motion widget.test_panel_edges widget.test_fades`: 24 OK.
- Ruff `--select F,E9,B` sui file toccati: verde. Nessun trattino lungo aggiunto.

## 8. Limiti

- Solo offscreen; nessuna prova su schermo fisico, cambio vero di monitor o Wayland.
- Il modello Qt non è stato toccato da me.
