# Revisione indipendente del lotto B (R242, R261, R263), Opus B, 30/10/2026

Base: `23bd7a9`, tranche R07 non committata sul disco. Nessun commit, nessuna operazione git di scrittura.
Legenda: [V] verificato (con la prova indicata), [I] dedotto, [NV] non verificato.

## 1. Che cosa ho rivisto

- `src/meridiana/navigation.py` righe 309-332 (`wheel_action`), diff completo rispetto a `23bd7a9`.
- `src/meridiana/ui/plan.py`: `wheelEvent` (1916-1928), `zoom_at` (1982-1995), `event` con i gesti nativi
  (2310-2333), Spazio: `keyPressEvent`, `_release_space`, `keyReleaseEvent`, `focusOutEvent`, `mouseMoveEvent`
  (2215-2225, 2340-2455).
- `src/meridiana/ui/view3d.py`: `Backend.wheel`, `touch_pan`, `end_touch_pan`, `touch_zoom`, `touch_orbit`,
  `_do`, `go`, `set_space`, `press/move/release`; `View3D.event`, `wheelEvent`, tasti di Spazio; `GizmoField`.
- `src/meridiana/camera.py` (solo lettura, per `ray`, `project`, `pan`, `zoom`, `zoom_point`).
- `src/meridiana/ui/day_picker.py` (diff completo), `src/meridiana/ui/plan_overlays.py` (`NorthArrow`),
  `src/meridiana/ui/input_log.py` (invariato rispetto alla base), `docs/registro-input.md`.
- Test di B: `tests/nucleo/test_touchpad_scroll.py`, `tests/widget/test_touchpad_geometry.py`,
  `tests/widget/test_calendar_geometry.py`, le tre attese cambiate in `tests/widget/test_plan.py`.
- Rapporto e brief del lotto (`build/overnight-r07/b-brief.md`, `b-report.md`), passaggio di Codex, esito
  dell'incarico Kimi 23 (R189, R190).

Giudizio generale: le correzioni di B sono sensate e ben provate (pick del fotogramma precedente ricostruito sul
raggio attuale, piano del pan conservato nel gesto, posizione QPointF nella pianta, calendario). Ho trovato tre
difetti, uno dei quali era già presente prima di B ma che B ha raddoppiato.

## 2. Difetti trovati e corretti

### D1. Scorrimento Wayland lento: salti di 4-12 px quando i pixel arrotondano a zero (medio)

- **Descrizione.** In uno scorrimento con fasi, `wheel_action` usava `angleDelta` quando `pixelDelta` era
  (0, 0). Il client Wayland di Qt arrotonda ogni `pixelDelta` e riporta il resto all'evento dopo, mentre
  `angleDelta` è 12 volte il movimento non arrotondato. [I: dal sorgente di Qt Wayland, `FrameData::angleDelta`
  restituisce `delta * -12` e `pixelDeltaAndError` arrotonda con l'errore accumulato. Il sorgente non è
  disponibile qui, quindi il dato è dedotto, non letto.] Con un movimento lento (0,3 px per evento) molti
  aggiornamenti hanno pixel (0, 0) e angolo (0, -4): la vista saltava di 4 px invece di 0. Prima di B il salto
  era di 2 px (mezzo angolo); B lo ha raddoppiato portando il ripiego a 1 px per unità. Può spiegare una parte
  dei «saltelli» di R189 su Linux.
- **Riproduzione [V].** Sequenza di sette eventi da 0,3 px con l'arrotondamento di Qt: spostamento totale
  -22 px invece di -2 (`AssertionError: -22.0 != -2`, prima della correzione).
- **Correzione.** `navigation.py`: in uno scorrimento con fasi si usano sempre i pixel, anche se sono zero;
  il ripiego sull'angolo resta solo per gli eventi senza fase (Windows, X11 libinput).
  `dx, dy = pixel if phased or pixel != (0.0, 0.0) else angle`, docstring aggiornata.
- **Prove.** `nucleo.test_touchpad_scroll.TouchpadScroll.test_a_phased_scroll_moves_by_its_pixels_even_when_they_round_to_zero`
  (fallita prima, passa dopo), `test_unphased_angle_only_touchpad_events_still_use_the_angle` (tutela del
  ripiego per X11).

### D2. 3D: cambio di vista durante uno scorrimento senza fasi, profondità vecchia (basso)

- **Descrizione.** `touch_pan` conserva la profondità del primo evento fino a 180 ms di pausa. Se nel frattempo
  si sceglie una vista (cubo, tasti, Home, `frame`), la profondità resta quella della camera precedente e il
  pan non segue più le dita: velocità sbagliata fino alla pausa.
- **Riproduzione [V].** Pan di 20 px subito dopo un cambio di vista di 180°: il punto si sposta di 16,17 px
  invece di 20.
- **Correzione.** `view3d.py`, `Backend.go`: chiama `self.end_touch_pan()` (tutti i cambi di camera passano
  da `go`).
- **Prova.** `widget.test_touchpad_geometry.TouchpadGeometry.test_a_view_change_inside_an_unphased_scroll_takes_a_new_pan_depth`.

### D3. 3D: Spazio da solo usa il punto di una rotella o di un clic precedente (medio; R190)

- **Descrizione.** Con Spazio senza pulsanti non c'è un pick: l'inizio del pan in `_do` prende `self._press[0]`,
  che contiene ancora il punto dell'ultima rotella (o dell'ultimo clic), in un altro punto dello schermo. Il pan
  seguiva quella profondità invece del cursore. Il difetto c'era già prima di B (stato residuo fra due gesti).
- **Riproduzione [V].** Rotella in (50, 50) sul terreno lontano, poi Spazio e mouse da (600, 450) a (640, 450):
  il punto sotto il cursore finisce a 780,5 px invece di 640 (3,5 volte troppo veloce).
- **Correzione.** `view3d.py`, `Backend.set_space`: alla pressione di Spazio, se nessun pulsante è premuto,
  `self._press = None`; il pan usa così il terreno (o il piano del target) sotto il cursore, come il
  trascinamento senza pick. Spazio + clic sinistro non cambia: la pressione rinnova il pick.
- **Prova.** `widget.test_view3d_navigation.Navigation.test_space_pan_does_not_take_the_depth_of_an_earlier_wheel_or_click`.

Prova aggiuntiva di copertura (passava già prima, nessun difetto):
`widget.test_touchpad_geometry.TouchpadGeometry.test_wheel_without_a_pick_or_with_a_stale_pick_behind_the_camera_keeps_the_cursor_anchor`
(cielo senza pick e pick vecchio dietro la camera: il punto sotto il cursore resta fermo, entro 1e-6 px).

## 3. Difetti sospetti non confermati

1. **Windows, due dita in verticale = zoom, non pan [I, importante per R189/R242].** In `qwindows.dll` di
   PySide6 6.12.0 c'è un solo `QWindowSystemInterface::handleWheelEvent` importato, quello **senza
   QPointingDevice**, e nessuna stringa di DirectManipulation o di touchpad (verificato estraendo le stringhe
   della DLL). Ne deduco che su Windows un touchpad di precisione arriva come `WM_MOUSEWHEEL` con dispositivo
   «mouse primario», `angleDelta` su un solo asse, senza fase e probabilmente `MouseEventNotSynthesized`: il
   verticale sarebbe classificato come rotella del mouse (zoom), l'orizzontale come pan. In questo caso
   `touchpad=True` non scatta mai su Windows, e le prove «Windows» del lotto 23 e di B (sorgente
   `SynthesizedBySystem`, angolo su due assi nello stesso evento) descrivono eventi che Windows forse non
   produce. È in contrasto con R242 («verticali troppo lenti»), che fa pensare a un verticale già in pan: per
   questo resta un sospetto. **Serve il registro reale** (`docs/registro-input.md`, `MERIDIANA_INPUT_LOG`) sul
   portatile Dell, con due dita verticali, orizzontali, pizzico e una rotella vera. Non ho cambiato il
   classificatore: distinguere un touchpad da una rotella ad alta risoluzione senza dispositivo e senza fasi
   richiede un'euristica (multipli di 120, frequenza) e la scelta è di Daniel.
2. **Ctrl + due dita su Wayland troppo veloce [I].** Con Ctrl i passi sono `angle / 120`; su Wayland l'angolo è
   12 volte i pixel, quindi un passo ogni 10 px di dita (con `pixel / 60` sarebbe ogni 60 px). Il pizzico vero
   su Wayland arriva come `NativeGesture` e non passa di qui; riguarda solo chi tiene Ctrl. Non cambiato.
3. **X11 con libinput [I].** Senza pixel, `angleDelta` vale circa 8 volte il movimento (incremento 15 del
   driver): pan 8 volte più veloce delle dita. Daniel usa Wayland (Niri): non cambiato, solo segnalato.
4. **Pianta, Spazio con ripetizione automatica [V, innocuo].** Le pressioni ripetute di Spazio non vengono
   accettate dalla pianta e risalgono ai genitori (la 3D invece le consuma). Nessun genitore oggi usa Spazio
   (cercato in `src`), quindi nessun effetto. Spazio + movimento e ripetizione Windows (solo pressioni ripetute)
   e X11 (rilasci finti) sono coperti dai test esistenti di pianta e 3D, verdi.
5. **Bussola R261 [V, nessun difetto].** Con `LETTER = 18,5` la N, misurata sulle metriche del carattere
   LABEL, sta a 2,0 px dal bordo del disco e 2,0 px dalla punta (testo medio), 2,5/2,5 (piccolo), 1,5/1,5
   (grande). Sul disegno reale alle scale 1; 1,5; 2; 2,5 la N occupa le righe 4-12,4 px e la punta inizia a
   17,6 px: separata. Margini simmetrici ma stretti col testo grande.

## 4. Modifiche richieste a file non miei

- **Template Qt, `C:\Users\Grasso\dev\qt-app-template\src\qtkit\gestures.py`** (righe 16-22): stesso difetto D1.
  Sostituire il blocco
  ```python
          if pixel != (0.0, 0.0):
              dx, dy = pixel
          elif angle != (0.0, 0.0):
              dx, dy = angle
          else:
              dx, dy = pixel
  ```
  con
  ```python
          dx, dy = pixel if phased or pixel != (0.0, 0.0) else angle
  ```
  e aggiungere alla docstring le due righe nuove di `navigation.wheel_action`; portare nel test del template le
  due prove nuove di `tests/nucleo/test_touchpad_scroll.py`.
- Nessuna modifica a `window.py` o `po/it.po`.

## 5. msgid nuovi o cambiati

Nessuno.

## 6. Prove eseguite

Ambiente come da regole (Python della venv di `meridiana`, offscreen, `PYTHONPATH=tests;src`).

- Prima delle modifiche, scale 1; 1,5; 2; 2,5 (`QT_SCALE_FACTOR`): `nucleo.test_touchpad_scroll
  nucleo.test_navigation widget.test_touchpad_geometry widget.test_calendar_geometry widget.test_calendar_hover
  widget.test_compass_layout widget.test_view3d_navigation widget.test_plan widget.test_sunbar
  widget.test_quick_image widget.test_input_log`: 137 test, OK a ogni scala.
- Prove nuove prima delle correzioni: 3 fallite (D1, D2, D3) come atteso.
- Dopo le correzioni, scale 1; 1,5; 2; 2,5: gli stessi moduli più `nucleo.test_navigation_help` e
  `widget.test_navigation_targets`: **150 test, OK a ogni scala**.
- `finestra.test_views_navigation`: 2 test, OK.
- `python -m ruff check --select F,E9,B` sui sorgenti e test toccati: `All checks passed!`.
- `git diff --check` sui file toccati: pulito. Nessun U+2014 nei file toccati.
- Sonde di misura (fuori dalla suite) nella cartella temporanea della sessione: classificatore, cambio di
  vista, Spazio dopo la rotella, metriche e pixel della N, spazio del campo angolo del gizmo.

File cambiati da me:
- `src/meridiana/navigation.py` (`wheel_action`, D1)
- `src/meridiana/ui/view3d.py` (`Backend.go` D2, `Backend.set_space` D3)
- `tests/nucleo/test_touchpad_scroll.py` (+2 test)
- `tests/widget/test_touchpad_geometry.py` (+2 test)
- `tests/widget/test_view3d_navigation.py` (+1 test)

## 7. Limiti e cose non verificate

- **Test fisico Linux non possibile ora**: il portatile (`fw13` / `lucciola.local`) non è raggiungibile. Le
  sequenze Wayland sono costruite con le classi Qt e con il comportamento di Qt Wayland dedotto [I]; vanno
  ripetute sul touchpad vero, idealmente con `MERIDIANA_INPUT_LOG` attivo.
- **Windows**: nessun touchpad fisico qui (PC fisso) e nessun registro reale di Daniel trovato (cercati file
  `.jsonl` nelle cartelle utente e temporanee). Vedi sospetto 3.1: è il punto più importante da chiudere.
- Nessuna finestra sullo schermo di Daniel: tutte le prove offscreen; la scala 2,5 è simulata con
  `QT_SCALE_FACTOR`, non con lo schermo reale (B l'aveva provata sul vero 250%).
- **Ambiguità R263 «angolo/anno», non chiusa.** Il calendario non ha un campo angolo: B ha corretto il campo
  **anno** (spin box tagliata nella barra), verificato dai test a 4 scale. Candidati per «casella dell'angolo»,
  da far scegliere a Daniel:
  1. il campo anno del calendario (corretto da B; ipotesi più probabile: refuso «anno» → «angolo»);
  2. il campo gradi del gizmo Sposta in 3D (`GizmoField`, larghezza fissa 64 px): misurato, area del testo
     48 px, «-359,9» richiede 42 px, quindi ci sta (a scala 1 e 2,5); i campi E/N con «-1234,56» (55 px) non
     ci stanno interi e scorrono;
  3. la barra del sole: altezza e azimut sono etichette, non campi (già detto da B).
  Nessuna correzione fatta su 2 e 3 finché Daniel non indica il controllo.
- Calendario: non ho ripetuto le foto reali di B; ho verificato solo i test geometrici e di alfa a quattro scale.
