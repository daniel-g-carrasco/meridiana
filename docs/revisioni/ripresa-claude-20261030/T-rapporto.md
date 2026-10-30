# Rapporto T: le quattro prove rosse del modello Qt (qt-app-template), 30/10/2026

Agente «Fable T». Repository: `C:\Users\Grasso\dev\qt-app-template` (port R07 sul disco, non committato).
Niente git oltre la lettura; `CLAUDE.md`, `README.md` e `docs/dal-template-gtk.md` non toccati.
Legenda: [V] verificato (con quale prova o misura), [I] dedotto, [N] non verificato.

## 1. Che cosa ho rivisto

- `src/qtkit/fades.py` (tutto; diff da HEAD: `HEIGHT`, `STOPS`, `PAGE_STOPS`, `_LIVE.discard`, `edge.page`),
  confrontato con `src/meridiana/ui/fades.py` dell'albero di Meridiana: **identici byte a byte** (0 righe diverse).
- `src/qtkit/scrollbars.py` (tutto; diff da HEAD: `outer_inset`, `PM_ScrollBarExtent`, `_groove`/`_slider` con il
  widget, `polish` che aggancia le sfumature, `SH_Widget_Animation_Duration`); gemello di Meridiana: differiscono solo
  docstring e il nome dell'attributo `_qtkit_scroll_style`.
- `src/qtkit/status_pill.py` (tutto; diff da HEAD: `RIGHT` 8→10, `SYMBOL` 14→13); gemello: solo l'import.
- `src/qtkit/motion.py` righe 211-328 (`Entrance`, `enter`, `leave`) e `src/qtkit/file_page.py` righe 380-470
  (`show_section`, `open_page`, `_stop_entrance`, `close_page`); `src/qtkit/window.py` 231-250 (`open_file_page`).
- `src/qtkit/gestures.py` (tutto), su richiesta del coordinatore (revisione B di Meridiana).
- Le prove `tests/test_behaviours.py`, `test_file_entrance.py`, `test_status_pill.py`, `test_gestures_compass_r07.py`,
  `test_shared_motion_r07.py` (lettura) e le gemelle di Meridiana (`tests/finestra/test_design_system.py` 160-185 e
  495-556, `tests/widget/test_fades.py`, `tests/widget/test_status_pill.py`, `tests/nucleo/test_touchpad_scroll.py`).
- Le richieste di Meridiana R192, R248, R256 in `docs/richieste.md` e l'esito `docs/revisioni/kimi-incarico-24-esito.md`.

Riproduzione [V]: le quattro prove rosse rifatte in locale danno **gli stessi quattro numeri del log**
`build/overnight-r07/template-full-before-review.log`: `12 != 16`, `16 != 10`, `2 != 1`, `30.0 != 32`.

## 2. Esito prova per prova

### 2.1 `test_behaviours`: sfumatura 16 → 12 px. Prova vecchia; cambio voluto.

- [V] `fades.py` del modello è identico a quello di Meridiana; i 12 px (`HEIGHT = Space.L`) e la curva «piena solo sul
  filo esterno, poi 42 %, 10 %, trasparente» sono la scelta di Daniel in **R192** (27/10/2026, «Il modo in cui sfumano i
  contenuti nelle schede è peggiorato»; esito incarico 24: «scelta la via di mezzo, 12 px, piena solo sul filo e
  rapidamente trasparente»). Nelle pagine con l'aria resta la curva larga di R177 (`PAGE_STOPS`, 75 % a 2 px).
- [I] La nota del 29/10 nel modello («il modello conserva la sua fascia da 16 px; Meridiana mantiene la variante da
  12 px», `docs/da-dove-viene.md` riga 387 e `docs/revisioni/2026-10-29-correzioni-uso.md`) non cita una decisione di
  Daniel: è una scelta prudente di un agente, superata dal mandato «tutte le correzioni di stile le portiamo nel
  template» (R164) e dal port R07. Se Daniel voleva davvero due altezze diverse, va chiesto a lui: lo segnalo.
- Fatto: la prova attende 12 e controlla `HEIGHT`, `STOPS[0] = (0, 1)` e `STOPS[1][1] <= 0.5`, con il commento storico
  (24 → 16 → 12). `docs/sistema-grafico.md`: tabella delle spaziature (altezza della sfumatura a L 12, non più a XXL 24),
  §5 «Fine morbida» riscritto con R161/R177/R192 e le due curve, e l'aggancio automatico di `ScrollStyle.polish`.
- Fotografie prima/dopo [V], offscreen al 200 %, fase 1 della galleria, chiaro e scuro:
  `build\claude-r07\T-sfumature-before-light.png`, `-before-dark.png`, `-after-light.png`, `-after-dark.png`, ritagli
  affiancati in `T-sfumature-confronto.png` (le etichette del confronto non sono renderizzate: l'ordine è chiaro
  prima, chiaro dopo, scuro prima, scuro dopo). Il «prima» è la galleria con i valori di HEAD (16 px, curva larga)
  rimessi a mano prima di costruirla. Misura: prima e dopo differiscono **solo** nelle righe 1868-1897 dell'immagine
  (il fondo della scheda dell'elenco e della pagina: 32 px a 200 % prima, 24 dopo); nessun altro pixel cambia.

### 2.2 Barre di scorrimento: 10 → 16 px. Prova vecchia; il gutter e il cursore vanno distinti.

- [V] Il posto riservato (`PM_ScrollBarExtent`) è `Size.SCROLLBAR + outer_inset(widget)`: 16 px per una `QScrollArea`
  fuori da una `CardDock` (il `PAD` di 6 px che una scheda-dock dà da sé intorno al contenuto), 10 px dentro una
  `CardDock`. È **R248** (Daniel, 29/10/2026: la distanza fra barra e bordo destro della scheda differiva fra la scheda
  principale e il pannello accanto). La guida (`SC_ScrollBarGroove`) e il cursore restano nei primi 10 px; l'inset
  resta vuoto; il cursore (6 px) finisce a 8 px dal bordo della scheda in tutti e due i casi.
- Fatto, `test_a_scroll_bar_that_comes_or_goes_moves_nothing`: `outer_inset(bar) == PAD`, larghezza 16, guida a x 0
  larga 10, contenuto fermo (geometria del viewport **e** posizione del widget interno prima e dopo che la barra
  compare), e sull'immagine della barra piena: esattamente 6 colonne disegnate, da x 2 a x 7, niente oltre x 10.
  Nuova `test_in_a_card_dock_the_bar_keeps_only_its_gutter_and_the_thumb_is_as_far_from_the_edge`: pagina e
  pannello in una `QMainWindow`, inset 0 nel dock, larghezze 10 e 16, il rettangolo del cursore a `PAD` dal bordo della
  scheda in entrambi (stessa distanza), quindi l'inchiostro a 8 px.
- `docs/sistema-grafico.md`: §2 Misure, tabella dei componenti e §5 «Barre di scorrimento» dicono gutter e inset.

### 2.3 `test_file_entrance`: due veli. **Difetto vero** di ciclo di vita, corretto.

Diagnosi [V] con uno script che elenca i veli a ogni passo (`scratchpad\diag_veils.py`), prima della correzione:
1. apri → `slide` visibile (tracciato in `page.entrance`);
2. apri di nuovo (il comando della finestra chiude) → il `slide` fermato e nascosto ma **non segnato `done`**; il velo
   d'uscita `leave` creato da `motion.leave` **non tracciato da nessuno**;
3. riapri → `leave` ancora visibile + nuovo `slide` visibile: **due veli**; e la `play` rimandata del primo `slide`,
   quando scatta con la pagina di nuovo visibile, lo rianima nascosto (animazione per niente).
Il secondo difetto, più grave in potenza [V, prova `test_a_cancelled_veil_never_plays_nor_shows_again` contro la copia
pre-correzione]: fermare un velo dall'esterno (stop, hide, deleteLater) non bastava, perché la `play` del `leave`
rimandata da `after_work` fa `show()` e riparte: un velo «cancellato» poteva ricomparire.

Correzione (piccola, nello stile del file):
- `motion.py`: `Entrance.play` e la `play` di `leave` non fanno nulla se `done`; nuovo `Entrance.cancel()` (=
  `_finish`: stop, hide, `finished`, deleteLater) con la spiegazione; docstring di `leave` dice che il chiamante tiene
  il velo e lo annulla se l'area torna prima.
- `file_page.py`: `self.exit` (il velo d'uscita) accanto a `self.entrance`; `close_page` lo conserva e collega
  `finished` a `_left`; `_stop_entrance` annulla entrambi con `cancel()`.
Prove: `test_reopening_and_closing_during_the_entrance_do_not_leave_a_live_veil` resa precisa (chi è visibile a ogni
passo: solo il `leave` dopo la chiusura, solo il nuovo `slide` dopo la riapertura, `page.exit` None, il velo vecchio
`done`; dopo l'ultima chiusura il solo `leave`, poi niente), più la nuova `test_a_cancelled_veil_never_plays_nor_shows_again`.
[V] Tutte e due **falliscono contro la copia del codice pre-correzione** (ricostruita in
`scratchpad\oldsrc` con il suo `support.py`: «unexpectedly None» e «False is not true») e passano sul corretto.
Nota: l'ultima asserzione della prova vecchia («nessun velo visibile subito dopo `close_page` + un
`processEvents`») era incompatibile con l'uscita animata di R07 (110 ms): ora si attende la fine del `leave`. Non è un
allentamento: il controllo che non resti un velo vivo c'è ancora, e la riapertura durante l'uscita è coperta.
Gravità del difetto per l'utente: media (due immagini sovrapposte per un decimo di secondo riaprendo File subito dopo
averla chiusa; nessuna perdita). Lo stesso difetto è in Meridiana: §4.

### 2.4 `status_pill`: numero a width-8 → width-10. Prova vecchia; attesa aggiornata e centratura verificata.

- [V] `RIGHT = 10`, `SYMBOL = 13` sono **R256** (Daniel: «simboli solo leggermente più piccoli e un poco più di spazio
  a destra dei numeri»); la prova gemella di Meridiana attende già `width() - 10`.
- Fatto: attesa a 10 e casella del segno 13, con la citazione. Nuova
  `test_the_painted_pill_centres_its_ink_and_keeps_the_room_at_both_ends`: dipinge le 16 pillole (4 livelli × «0»,
  «1», «12», «999») a 24 px e misura i **pixel** d'inchiostro (più vicini all'inchiostro che al fondo): centro
  verticale del segno e del numero a metà altezza ± 1 px, centro del segno sul centro della casella (6 + 13/2) ± 1,
  segno non prima di 5 px, ultimo pixel del numero a 10 ± 1 px dall'estremo destro, almeno 3 px fra segno e numero.
  Mentre la scrivevo ho corretto un'ipotesi mia sbagliata: il «!» e la «i» sono stretti e centrati nella casella, non
  appoggiati a sinistra (la prima stesura chiedeva il bordo sinistro a 6 e cadeva su `warn`).
- Disegno guardato [V]: `build\claude-r07\T-pillole.png` (16 pillole × 4, chiaro e scuro, con guide magenta a 6 px, a
  10 px dal bordo destro e a metà altezza) e i ritagli `T-pillole-zoom-chiaro.png`, `T-pillole-zoom-scuro.png`: il
  numero finisce sulla guida di destra, l'inchiostro sta sulla mezzeria, lo zero è attenuato.
- `docs/sistema-grafico.md`: riga nuova «Conteggio di un segno» nella tabella dei componenti.

### 2.5 In più, dal coordinatore: `gestures.py`, scorrimento con fasi (revisione B di Meridiana)

- [V] Con `pixel == (0, 0)` e fasi attive il classificatore ripiegava su `angle`, che su Wayland vale circa 12 volte il
  movimento (il client Qt arrotonda i pixel e riporta il resto all'evento dopo): `('pan', 0, -4)` dove doveva essere
  `('pan', 0, 0)` (provato eseguendo la vecchia funzione). Portata la regola di `src/meridiana/navigation.py`:
  `dx, dy = pixel if phased or pixel != (0.0, 0.0) else angle`, con la frase di spiegazione nella docstring.
- Prova `test_a_phased_scroll_moves_by_its_pixels_even_when_they_round_to_zero` in `tests/test_gestures_compass_r07.py`
  (la stessa sequenza di Meridiana: sette passi da 0,3 px, totale −2, e il caso secco; più il caso senza fasi di X11
  che usa ancora l'angolo).

## 3. Difetti sospetti non confermati

- [N] `motion.leave` fotografa l'area (`picture(area)`) **prima** di `change()`: se un velo d'entrata è ancora sopra la
  pagina e non è stato annullato, la foto lo conterrebbe. Con `_stop_entrance` chiamata prima (come ora in
  `close_page`) non succede; un altro chiamante di `leave` dovrebbe fare lo stesso. Non visto in pratica.
- [N] `ScrollStyle.polish` aggancia `fades.attach(target, air=True)` a **ogni** `QScrollArea`, anche a quelle che non
  stanno in una scheda (dialoghi, liste di finestrelle che sono `QScrollArea`?): l'aria di 6 px sopra e sotto arriva
  dovunque. Nella galleria e nell'esempio non vedo effetti sgraditi; da tenere d'occhio nei programmi.
- [I] `outer_inset` riconosce la scheda-dock dalla presenza di `card_rect`: un programma che mette una `QScrollArea`
  in un contenitore proprio con il suo `PAD` avrà 6 px in più. È il contratto scelto in Meridiana; documentato.

## 4. Modifiche richieste a file non miei (Meridiana, sola lettura qui)

Lo stesso difetto 2.3 è in `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\src\meridiana\ui\file_page.py` e
`src\meridiana\ui\motion.py` (albero di lavoro R07). Testo esatto:

`src/meridiana/ui/motion.py`
- riga 234, `Entrance.play`: come prima riga del corpo aggiungere
  `        if self.done:                               # cancelled while the window settled: it never plays`
  `            return`
- prima di `def _finish` (riga 249) aggiungere
  `    def cancel(self) -> None:`
  `        """The veil dropped before or while it plays (the page opened again during its exit, closed during its`
  `        entrance): hidden at once, `finished` emitted, and its play left for after the window's work does nothing.`
  `        Stopping the animation and hiding it from outside was not enough: that play showed it again."""`
  `        self._finish()`
- riga 333, la `play()` interna di `leave`: come prima riga del corpo aggiungere
  `        if entrance.done:                           # cancelled: the area came back before its exit played`
  `            return`

`src/meridiana/ui/file_page.py`
- riga 184, dopo `self.entrance = None`: `        self.exit = None                            # the veil of the page leaving (motion.leave), until it has played`
- dopo `_entered` (righe 535-537) aggiungere `    def _left(self) -> None:` / `        self.exit = None`
- righe 549-553 di `close_page` (il blocco `if self.entrance is not None: ... self.entrance = None`) sostituire con
  `            for veil in (self.entrance, self.exit):` / `                if veil is not None:` /
  `                    veil.cancel()` / `            self.entrance = self.exit = None`
  e lo stesso blocco va messo in testa a `open_page` (riga 505), prima di `self.place()`: [V] in Meridiana
  `open_page` oggi non ferma nessun velo precedente (l'unico `animation.stop()` è in `close_page`, riga 550), quindi
  lì la riapertura durante l'uscita lascia il `leave` visibile sotto la nuova entrata esattamente come nel modello.
- riga 563: `            motion.leave(self, dismiss)` → `            self.exit = motion.leave(self, dismiss)` /
  `            if self.exit is not None:` / `                self.exit.finished.connect(self._left)`
Prova per Meridiana: la stessa `test_reopening_and_closing_during_the_entrance_do_not_leave_a_live_veil` adattata
(`tests/finestra/test_design_system.py`, dopo la prova della pagina File).

Fuori da questo compito ma visto: `src/meridiana/ui/window.py` non è coinvolto (la toggle è `open_file_page` →
`close_page`, come nel modello).

## 5. msgid nuovi e traduzioni

Nessuno: nessun testo d'interfaccia aggiunto o cambiato (solo codice, commenti e prove in inglese, documenti in
italiano). Nessun trattino lungo (controllato da `test_repository`).

## 6. Prove eseguite

Ambiente: `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`, `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen
PYTHONPATH="tests;src"`, `PATH` con `...\.venv\Lib\site-packages\PySide6` davanti, dalla cartella del modello.

- Riproduzione dei 4 rossi: `python -m unittest test_behaviours.Behaviours.test_a_list... test_behaviours.ScrollBars
  test_file_entrance test_status_pill` → 4 fallimenti con gli stessi numeri del log [V].
- `python -m unittest discover -s tests` dopo le correzioni: **174 prove, OK** in 205 s (rallentata dalle foto in
  parallelo), log `build\claude-r07\T-suite-template.log`; poi i moduli toccati dopo le correzioni di ruff
  (`test_behaviours test_file_entrance test_status_pill test_gestures_compass_r07 test_repository`): 26 prove OK;
  suite intera finale a fine lavoro, dopo tutte le modifiche: **175 prove, OK** in 232 s (il PC era carico di altri
  agenti; nessuna prova di tempo è caduta), log `build\claude-r07\T-suite-template-finale.log`.
- `python -m ruff check .` → «All checks passed!» (dopo aver tolto un import inutile e due chiusure su variabili di
  ciclo nelle mie prove).
- Contro la copia pre-correzione (`scratchpad\oldsrc` + `oldsrc-tests`): le due prove dell'entrata falliscono [V].
- Galleria, offscreen, `QT_SCALE_FACTOR=2 --size 1600x1000`: chiaro, scuro, `--file --alt`, `--phase 2` scuro,
  `--phase 3` chiaro, guardate: `build\claude-r07\T-galleria-*.png`. Niente di storto: pillole con lo spazio a destra,
  barre nel loro posto, pagina File e barra di Alt a posto, simboli e segni in fase 2. Le stesse cinque immagini
  **copiate su `docs\galleria-*.png`** (quelle del 26/10 erano prima delle sfumature, delle pillole e dell'inset: la
  regola di `CLAUDE.md` dice di rifarle quando l'aspetto cambia); se non si vogliono nel commit, `git checkout -- docs/*.png`.

## 7. Allineamento con Meridiana R07 (sola lettura)

`python tools\check_template_alignment.py --upstream C:\Users\Grasso\dev\qt-app-template --manifest
template-sync-qt_R05.json` (dalla cartella di Meridiana) → **«Changed since alignment»** per: `fades.py`,
`scrollbars.py`, `theme.py`, `file_page.py`, `status_pill.py`, `spotlight.py`, `day_picker.py`, `motion.py`,
`conversation_view.py` (da tutte e due le parti), `window.py` di Meridiana, e fra i file del consumatore `charts.py`,
`panel_buttons.py`, `checks_page.py`. Atteso: il manifest R05 fotografa acd4ab3 e un albero di Meridiana pre-R07; non
dichiara allineamento.

Confronto diretto dei gemelli (`diff --strip-trailing-cr`, righe diverse): identici `fades`, `spotlight`,
`conversation_view`, `document_style`, `document_layout`, `dock_motion`; solo import/docstring/nome attributo
`status_pill` (2), `day_picker` (2), `guide_card` (2), `help` (2), `panel_buttons` (2), `checkboxes` (3), `tables` (3),
`popups` (14), `scrollbars` (19); con le differenze documentate del modello neutro `cards` (26), `sections` (50),
`style` (90), `marks` (129), `phasebar` (186), `theme` (308), `file_page` (456). `motion.py`: 52 righe, di cui la
docstring e **la correzione 2.3 che Meridiana ancora non ha** (§4): finché non la riceve, i due non sono allineati
su `motion.py` e `file_page.py`. `compass.py` e `gestures.py` esistono solo nel modello (in Meridiana la bussola sta in
`plan_overlays.py` e il classificatore in `navigation.py`): `gestures.wheel_action` ora ha la stessa regola di
`navigation.wheel_action`.

Nota proposta per `docs/da-dove-viene.md` (NON applicata; va sotto l'elenco in testa, prima di «Modulo per modulo»):

> - **Allineamento con Meridiana R07 (albero di lavoro `integra-kimi-9-10` dopo 23bd7a9, 30/10/2026)**: cards,
>   panel_buttons, motion (`Entrance.finished`, `leave`, `Collapse`, `TreeMotion`/`SectionVeil`, `set_reduced` che
>   avvisa i controllori), scrollbars (R248: il posto della barra comprende il `PAD` fuori da una scheda-dock,
>   `outer_inset`; le sfumature agganciate da `polish`), fades (R192: 12 px, piena solo sul filo e subito trasparente;
>   supera la nota del 29/10 che teneva 16 px nel modello), day_picker, spotlight, conversation_view, status_pill
>   (R256: segno 13 px, 10 px a destra del numero), theme (righe a pillola), i18n, FilePage con cambio di sezione e
>   uscita animati; nuovi `compass.py` (sola bussola neutra), `gestures.py` (classificatore rotella/touchpad, con la
>   regola della revisione B: uno scorrimento con fasi si muove dei suoi pixel anche quando arrotondano a zero) e
>   `dock_motion.py`. Nati qui e da riportare in Meridiana (rapporto T): `Entrance.cancel`, la `play` che non scatta
>   su un velo annullato, `FilePage.exit` che tiene il velo d'uscita e lo annulla alla riapertura (due veli visibili
>   altrimenti). Non venuti: Meridio durante il tour (`guidedTourActive`), le sezioni della pagina File di Meridiana,
>   la pianta ruotabile. Il manifest del consumatore resta `template-sync-qt_R05.json` (acd4ab3): la revisione R06 va
>   scritta dopo il commit del modello e il port della correzione in Meridiana, con gli hash nuovi; fino ad allora
>   `check_template_alignment.py` segnala, com'è giusto, i nove moduli cambiati da tutte e due le parti.

## 9. Secondo incarico: le correzioni della revisione C portate nel modello (30/10/2026, pomeriggio)

Fonte: `build\claude-r07\C-rapporto.md` §5 e i diff `git diff 23bd7a9` di Meridiana (sola lettura) su `ui/motion.py`,
`ui/fades.py`, `ui/scrollbars.py`, `ui/dock_motion.py`, `ui/file_page.py`.

Che cosa è venuto, modulo per modulo [V, `diff --strip-trailing-cr` con i gemelli dopo il port]:
- `motion.py`: `_replace(area)` chiamata da `enter` e `leave` (annulla ogni `Entrance` ancora sopra la stessa area,
  per i chiamanti che non tengono il velo; in `leave` anche nel ramo «meno movimento»); `leave` toglie i `Veil` di
  crossfade rimasti dentro l'area (altrimenti rigiocavano alla riapertura). Gemello: identico salvo la docstring di
  modulo (la storica differenza «Meridiana's R75 ...») e una riga vuota finale.
- `fades.py`: `attach(..., auto=False)`, `Fades.auto_margins`; con `auto=True` (solo il polish) non tocca un'area già
  sfumata, in qualunque ordine; una chiamata esplicita senza `air` si riprende i margini dati dal polish; `edge.page`
  segue l'ultima chiamata esplicita. Gemello: **identico**.
- `scrollbars.py`: `polish` chiama `fades.attach(target, air=True, auto=True)`. Gemello: solo docstring e
  `_qtkit_scroll_style`.
- `dock_motion.py`: copiato tale e quale da Meridiana (gli import erano già gli stessi): `_docked` (flottanti e
  nascosti fuori da `Reflow.__init__`, `settle` e annullo), `_covered` (pagina che copre almeno metà dell'arena: cambio
  subito, nessun velo), `Reflow.drag` e `reflow()` che annulla prima il trascinamento in corso, `_CANCEL`
  (`WindowDeactivate`, `Hide`, `DevicePixelRatioChange`), `ShortcutOverride` di Esc accettato durante il
  trascinamento, `self.origin is not None`. Gemello: **identico**.
- `file_page.py`, un adattamento del modello e non di Meridiana: la `Section` chiamava `fades.attach(self)` (variante
  semplice) e con `auto` quella chiamata vince sul polish, così le sezioni della pagina File perdevano l'aria e la
  curva di pagina (foto: 391 righe diverse rispetto alla galleria di prima); Meridiana non ha quella chiamata e le sue
  sezioni prendono l'aria dal polish. Ora `fades.attach(self, air=True)`: la pagina File torna **identica pixel per
  pixel** alla foto fatta prima del port (`T2-galleria-file-chiaro.png` vs `T-galleria-file-chiaro.png`, 0 righe
  diverse); la galleria in chiaro idem (0 righe). Le cinque foto di `docs/` restano quindi valide.
- `tests/support.py`: `turn_events(app, ms)` come in `_setup.py` di Meridiana.

Prove portate in `tests/test_shared_motion_r07.py` (da `tests/widget/test_shared_motion.py` di Meridiana, con
`support` al posto di `_setup`, `_qtkit_scroll_style`, `qtkit`): `test_automatic_fades_leave_an_explicit_variant_alone_in_either_order`,
`_overlay`, `test_entering_again_while_leaving_keeps_one_veil`, `test_a_cancelled_veil_never_plays_nor_shows_again`
(gemella di quella di `test_file_entrance`, tenuta per l'identità dei file), `test_less_motion_switched_on_and_off_before_the_exit_plays_leaves_no_veil`,
`_start_drag`, `_no_live_layer`, `test_a_floating_panel_is_not_painted_into_the_reflow`,
`test_a_page_over_the_cards_takes_the_change_at_once`, `test_hiding_the_window_or_changing_its_pixel_ratio_cancels_a_drag`,
`test_a_panel_toggled_during_a_drag_cancels_the_preview_first`, `test_escape_cancels_a_drag_before_a_window_shortcut_takes_it`;
in più, mia, `test_leaving_drops_the_crossfade_veils_still_inside_the_area` (la pulizia dei `Veil` in `leave`, che C
descrive ma non prova da sola).

Controprove [V]:
- contro una copia del modello senza `_replace`, senza la pulizia dei `Veil` e con la vecchia `attach`
  (`scratchpad\oldsrc2`, ricostruita a rovescio dalle modifiche): `test_entering_again...`, `test_leaving_drops...`
  e `test_automatic_fades...` **falliscono** (3 su 3; la terza con margini `(6, 6) != (0, 0)`);
- con `_covered` disattivato (`dock_motion._covered = lambda w: False`, come ha fatto C): `test_a_page_over_the_cards...`
  **fallisce**. Per `_docked`, `_CANCEL`, `Reflow.drag`, `ShortcutOverride` e `origin is not None` non ho una versione
  precedente di `dock_motion.py` (non è tracciato in Meridiana e la copia del modello l'ho sovrascritta): le prove
  sono quelle che C ha visto rosse prima della sua correzione [D], qui solo verdi.
- Prove mirate dopo il port: `test_shared_motion_r07 test_file_entrance test_behaviours test_window
  test_file_navigation` 59 OK; dopo la `Section`: `test_file_entrance test_file_navigation test_window test_sections
  test_navigation_ux` 40 OK; `ruff check .` pulito. Suite intera: vedi sotto.

Documenti: `docs/sistema-grafico.md` §5 (il polish e `auto`, R249; `enter`/`leave` che sostituiscono il velo sopra la
stessa area) e una riga nuova nella tabella dei componenti per `dock_motion.py` (schede che si aprono, chiudono e
trascinano, con le regole di C). Nessun msgid nuovo. Nessun trattino lungo.

Per la nota di `da-dove-viene.md` (§7 sopra) si aggiunge: «`motion._replace` e la pulizia dei veli in `leave`,
`fades.attach(auto=...)`, `dock_motion` con `_docked`/`_covered`/`_CANCEL`/Esc, dalla revisione C di Meridiana del
30/10/2026; la `Section` di File chiede esplicitamente la variante di pagina».

Suite intera del modello dopo il port di C: **185 prove, OK** in 106 s (`python -m unittest discover -s tests`, log
`build\claude-r07\T-suite-template-finale-C.log`); `ruff check .` pulito; `test_repository` rilanciato dopo i
ritocchi ai documenti: OK. Stato del lavoro: `src/qtkit/{motion,fades,scrollbars,dock_motion,file_page}.py`,
`tests/{support,test_shared_motion_r07}.py`, `docs/sistema-grafico.md`; sempre niente git, `CLAUDE.md`, `README.md`
e `docs/dal-template-gtk.md` intatti.

## 10. Terzo incarico: lo spotlight della revisione D (30/10/2026, pomeriggio)

Fonte: `build\claude-r07\D-rapporto.md` §4 punto 4 e `git diff 23bd7a9 -- src/meridiana/ui/spotlight.py` (geometria
della guida intersecata con la finestra, anello costruito attorno a `target_rect` e non dal rettangolo della guida,
che spostava l'anello quando la guida era tagliata dal bordo: R265), più le due prove nuove di
`tests/widget/test_spotlight.py`.

- [V] `src/qtkit/spotlight.py` è già **identico** a `src/meridiana/ui/spotlight.py` con la correzione di D
  (`diff --strip-trailing-cr` vuoto; `target_rect` e `intersected` alle righe 57-65): la correzione era entrata nel
  modello con il port R07 di Codex, dopo il lavoro di D. Niente da cambiare nel codice.
- [V] `src/qtkit/conversation_view.py` è anch'esso identico al gemello: il cambio generico di D (colore del ruolo
  `assistant` nell'intestazione, 78 % di larghezza per i messaggi in uscita e 90 % per quelli in entrata) c'è già.
- Portate in `tests/test_spotlight.py` le due prove di Meridiana (`support` al posto di `_setup`, `qtkit`):
  `test_ring_and_pen_stay_inside_window_for_phase_tabs_at_top_edge` e
  `test_ring_hugs_the_target_at_all_four_window_edges` (R265: anello dentro la finestra a ogni istante e, sui lati
  lontani dal bordo, sempre attorno al bersaglio e mai attraverso, nei quattro angoli e al centro).
- Controprova [V]: contro una copia con lo `spotlight.py` pre-D (`scratchpad\oldsrc3`, ricostruito a rovescio dal
  diff) **tutte e due le prove falliscono**; sul codice attuale `test_spotlight`: 7 OK.
- Suite intera del modello: **187 prove, OK** in 99 s (`T-suite-template-finale-D.log`); `ruff check .` pulito.
  Nessun documento toccato (l'aspetto non cambia); nessun msgid; niente git.

## 11. Quarto incarico: il componente di R268 (`NamePicker`, `NameDialog`) nel modello (30/10/2026, pomeriggio)

Fonte: `build\claude-r07\M-rapporto.md` §8 (e §5 per le traduzioni), `src/meridiana/ui/brand_picker.py`,
`tests/widget/test_brand_picker.py` (sola lettura).

- `src/qtkit/name_picker.py`: copia di `brand_picker.py` con i soli import cambiati (`from . import theme_colors`,
  `from .i18n import _`) [V: `diff --strip-trailing-cr` dà solo quelle due righe] **più una correzione mia** (sotto).
  Dipendenze verificate nel modello: `theme_colors.HOVER`, `theme_colors.faded_text`, i gettoni `card`, `select_bg`,
  `text`.
- Traduzioni: il modello non ha un `.po`, ha il dizionario `i18n.ITALIAN` (la prova
  `test_repository` esige che ogni stringa in `_()` del pacchetto vi stia, e nessuna di più). Aggiunte le cinque di
  M §5: «Favourites» → «Preferiti», «All» → «Tutti», «Search…» → «Cerca…», «Add to favourites (Ctrl+D)» → «Aggiungi
  ai preferiti (Ctrl+D)», «Remove from favourites (Ctrl+D)» → «Togli dai preferiti (Ctrl+D)».
- `tests/test_name_picker.py`: i 13 casi di Meridiana con `support` (`app`, `theme`, `dispose`, e il nuovo
  `support.keyboard_or_skip`, portato da `_setup` con `wait_until` al posto di `QTest.qWaitFor`, che PySide6 non ha);
  le intestazioni e il suggerimento attesi in italiano («Preferiti», «Tutti», «Aggiungi ai preferiti (Ctrl+D)»)
  perché `support.theme` configura il modello con `i18n.italian`; la prova dei colori rimette il tema chiaro alla
  fine. Più una prova mia (sotto): 14 in tutto.
- Galleria, fase 2 «Componenti»: la voce «Scelta di un nome fra molti» (30 marche, due preferite, tre attenuate con il
  perché, «Huawei» in mano, segnaposto «Cerca una marca»), affiancata ai sette simboli con `side_by_side` perché in
  fondo alla pagina la foto la tagliava dopo quattro righe; `self.picker` sulla galleria. Foto nei due temi guardate
  (`T3-galleria-componenti-chiaro.png`, `-scuro.png`, ritagli `T3-picker-zoom-*.png`): campo, elenco di otto righe
  scorso sul nome in mano con la sua pillola e la stella, barra nel suo gutter; `docs\galleria-componenti-scuro.png`
  rifatta (le altre quattro foto non cambiano: la voce sta solo in fase 2).
- `docs/sistema-grafico.md`: riga «Scelta di un nome fra molti» nella tabella dei componenti (ricerca senza maiuscole
  e accenti, otto righe, preferiti con la stella e di chi sono, attenuati col perché, tasti, colori dalla tavolozza).

Difetto trovato e corretto [V], da riportare in Meridiana (`src/meridiana/ui/brand_picker.py`, `RowDelegate.paint`,
riga 91): aperto sul nome in mano lontano nell'elenco (la lista scorre fino a lui), la riga **in cima** alla vista
riceve `State_MouseOver` con il puntatore da tutt'altra parte, e si disegna con la pillola dell'hover e la stella a
contorno (nella galleria «Deye» sopra «Huawei»). Riprodotto con un `NamePicker` da solo offscreen: cursore a (10, 10),
viewport a (893, 743), `underMouse()` falso, nessun evento Hover/Enter arriva al viewport, eppure il delegato riceve
lo stato sulla prima riga visibile; succede solo se l'elenco è scorso (`scroll=364`), non a scorrimento zero; non
dipende da `WA_Hover` né dal mouse tracking. [I] È l'indice hover interno di `QAbstractItemView` rimesso dopo lo
scorrimento fatto dal codice; la causa esatta in Qt non l'ho isolata. Correzione, due righe nel delegato:
`view = option.widget` / `under = view is None or not hasattr(view, "viewport") or view.viewport().underMouse()` /
`hover = bool(option.state & QStyle.StateFlag.State_MouseOver) and under`, con il commento. Prova
`test_a_list_opened_on_a_name_far_down_shows_no_hover_pill_on_its_top_row`: **rossa** contro una copia con la riga
originale (`scratchpad\oldsrc4`), verde ora. Finché Meridiana non la riceve, `brand_picker.py` e `name_picker.py`
differiscono di queste righe oltre agli import. Gravità: bassa (estetica; sparisce al primo movimento del mouse).
[N] Sullo schermo vero non provato; con il puntatore davvero sopra la riga la pillola resta.

Prove: `test_name_picker` 14 OK; prima, con `test_repository test_looks test_window test_design`, 58 OK (dopo aver
tolto `QTest.qWaitFor`); suite intera **201 prove, OK** in 75 s (`T-suite-template-finale-M.log`); `ruff check .`
pulito. Niente git; `CLAUDE.md`, `README.md`, `docs/dal-template-gtk.md` intatti.

Per la nota di `da-dove-viene.md` (§7) si aggiunge: «`name_picker.py` da `ui/brand_picker.py` di Meridiana (R268,
Fable M, 30/10/2026): solo gli import cambiano, più la guardia dell'hover nata qui e da riportare; prove gemelle in
`tests/test_name_picker.py`; i cinque msgid in `i18n.ITALIAN`». Il manifest del consumatore avrà la voce
`ui/brand_picker.py` → `name_picker.py` nella revisione R06, con gli hash dopo il commit.

## 8. Limiti e cose non verificate

- [N] Niente sullo schermo vero: foto e prove solo offscreen (regola). L'uscita animata della pagina File e la
  riapertura durante l'uscita non le ho viste a occhio a 60 Hz; le prove misurano stati e veli, non la fluidità.
- [N] Non ho eseguito la suite di Meridiana né toccato i suoi file: la correzione 2.3 lì è solo testo proposto.
- [I] La scelta 12 px nel modello è dedotta da R192 + R164; se Daniel voleva tenere 16 nel modello (nota del 29/10) va
  rimesso `HEIGHT = Space.XL` con la prova e la regola, cosa di un minuto.
- Il manifest R06 e l'«Ultimo allineamento» di `da-dove-viene.md` non li ho scritti (il compito diceva di prepararli).
- File creati da me fuori dal repository: in `build\claude-r07\` i `T-*.png`, `T-suite-template*.log` e questo
  rapporto; nello scratchpad della sessione gli script `diag_veils.py`, `make_old.py`, `shoot_fades.py`,
  `crop_fades.py`, `draw_pills.py` e la copia `oldsrc`.
