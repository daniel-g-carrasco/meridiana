# M, rapporto: R268, scelta della marca nel dimensionamento automatico (30/10/2026)

Richiesta (Daniel, R268): la lista delle marche nel dimensionamento automatico degli inverter «invade tutta
l'altezza dello schermo»; sostituirla con una ricerca compatta ad altezza limitata, preferiti persistenti e
selezionabili, preferiti dell'utente separati dal progetto, tutte le marche raggiungibili, componente generico da
portare nel modello Qt. Aggiunta del coordinatore (da F, punto 7): le marche senza alcun record dimensionabile
(«ABB», «SolarEdge Technologies Ltd»: lista CEC USA senza numero di MPPT) restano raggiungibili ma attenuate, con il
perché e la marca alternativa nel suggerimento, e non proposte per prime.

## 1. Che cosa ho rivisto e fatto

Letti: `REGOLE-AGENTI.md`, la riga R268 di `docs/richieste.md`, il paragrafo R268 del passaggio, `docs/design/
sistema-grafico.md` (tutto), `src/meridiana/config.py` (tutto, con il diff di Opus A su `_typed`), `ui/window.py`
`_size_inverters` (righe 3901-3960), `ui/catalog_dialog.py` (il campo di ricerca), `ui/sections.py` (pillola della
riga e colore attenuato), `ui/day_picker.py` (componente generico che legge la tavolozza), `ui/design.py`,
`ui/icons.py` (nessuna stella fra le icone Lucide incluse: la stella è disegnata), `theme_colors.palette`
(quali gettoni finiscono in quali ruoli della QPalette), `energy/sizing.py` di F (`missing_fields`, `alternatives`,
sola lettura), i tre test di finestra che mimano la scelta della marca, `tests/_setup.py`.

File miei:

| File | Cosa |
|---|---|
| `src/meridiana/ui/brand_picker.py` (nuovo, 450 righe) | `NamePicker` (campo di ricerca + elenco), `NameList`, `RowDelegate`, `NameDialog` con `NameDialog.ask(...)`; `fold()` per la ricerca senza maiuscole e accenti |
| `src/meridiana/config.py` | campo `inverter_brand_favourites: list` (vuoto), migrazione `_v23_to_v24`, `CONFIG_VERSION = 24`, controllo di tipo `_TEXT_LISTS` in `_typed` |
| `src/meridiana/ui/window.py` | solo `_size_inverters`: `QInputDialog.getItem` sostituito dal `NameDialog`; marche non dimensionabili calcolate con `sizing.missing_fields` e `sizing.alternatives` (F); preferiti salvati in `cfg` anche con Annulla |
| `tests/formati/file/config-v24.json` (nuovo, congelato) | il v23 con `"version": 24` e `"inverter_brand_favourites": ["Huawei", "SMA", "Fronius"]` |
| `tests/formati/test_formats.py` | riga `24: {"inverter_brand_favourites"}` in `BROUGHT`; prova nuova `test_the_starred_makers_survive_a_save_and_a_restart_and_anything_else_there_is_damage` |
| `tests/formati/test_config.py` | solo le due righe che fissavano la versione a 23 (ora 24) più l'asserzione del nuovo campo vuoto; file di Opus A, toccato perché «quelle dei formati» sono nel mio incarico e altrimenti restava rosso |
| `tests/widget/test_brand_picker.py` (nuovo, 13 prove) | ricerca, altezza, preferiti e stella, preselezione, tastiera, attenuati, colori nei due temi, `ask` |
| `build/claude-r07/M-picker-*.png` | foto offscreen (sotto) |

Nome del campo: `inverter_brand_favourites` (ortografia britannica come il resto del codice: `colour`, `catalogue`),
non `inverter_brand_favorites` dell'incarico.

### Il componente (`ui/brand_picker.py`)

- **Ricerca**: `QLineEdit` con pulsante di cancellazione, filtro a ogni carattere; `fold()` (NFKD senza segni
  diacritici + `casefold`): «HUTT», «hüt» trovano «Hüttinger», «ENERGIE» trova «Zeta Énergie».
- **Elenco**: `QListWidget` con delegato; altezza fissa = min(8, righe totali) righe da 28 px (`Size.CONTROL`),
  minimo 3, poi scorre; fissa, così un filtro che accorcia l'elenco non sposta OK/Annulla. Con le 165 marche degli
  inverter: 8 righe, 226 px (prima la tendina di `QInputDialog` andava a tutto schermo).
- **Preferiti** in cima sotto l'intestazione «Favourites» (stile `label`, maiuscole 11 px come le sezioni), poi
  «All manufacturers» (il chiamante passa il titolo; il generico dice «All»); stella a destra di ogni riga: piena sul
  preferito, contorno attenuato sulla riga in mano o sotto il puntatore; clic sulla stella aggiunge/toglie senza
  cambiare la riga scelta; `favouritesChanged` a ogni cambio; ordine dei preferiti = ordine in cui sono stati
  segnati. Un preferito che l'elenco non conosce resta nella lista ma non si mostra.
- **Attenuati** (`dimmed: {nome: perché}`): dopo gli altri dentro la sezione «All», inchiostro `faded_text`
  (lo stesso dei controlli spenti), suggerimento con il perché; un attenuato segnato preferito sale fra i preferiti.
  Nel catalogo di oggi sono 150 marche su 165 (solo 15 hanno record con potenza CA, numero MPPT e tensioni MPPT):
  le 15 dimensionabili vengono prima, poi le CEC.
- **Preselezione**: `current` confrontato con `fold` (il progetto può averla scritta in altro caso); conservata
  attraverso una ricerca che la mostra ancora; altrimenti la prima mostrata.
- **Tastiera**: nel campo Su/Giù/PagSu/PagGiù muovono la scelta saltando le intestazioni, Invio sceglie, Esc cancella
  prima la ricerca e poi chiude, Ctrl+F torna al campo, Ctrl+D segna/toglie il preferito in mano; nell'elenco
  Invio sceglie, Spazio segna, una lettera va nel campo di ricerca.
- **Stile**: colori solo dalla tavolozza (`Text`, `PlaceholderText` = `muted`, `Highlight` = `select_bg`, gruppo
  Disabled = `faded_text`), hover = testo all'8 % (`theme_colors.HOVER`, R160), pillola raggio 4 (`Radius.INNER`),
  testo `Text.BODY` e intestazioni `Text.LABEL` via `design.text_font`, misure da `design.py` (`Space`, `Line`,
  `Icon`); elenco e campo prendono bordo, fondo `card` e raggio 6 dal foglio di stile globale. Nessun numero a mano
  salvo `STAR_INNER = 0.42` (proporzione della stella) e i limiti di larghezza 240-420 px.
- `NameDialog.ask(parent, title, prompt, names, *, current, favourites, dimmed, placeholder, favourites_title,
  others_title) -> (nome, ok, preferiti_ora)`: i preferiti tornano anche con Annulla, perché sono dell'utente.

### La finestra (`_size_inverters`)

`records = list(catalog.load("inverters"))` una volta sola (prima era letto dopo la scelta); `sizable` = marche con
almeno un record senza `sizing.missing_fields`; per le altre il motivo «No model of {maker} in the catalogue has the
datasheet data the sizing needs.» + «Sizable instead: ...» di F (`sizing.alternatives(name, records)`: «FIMER: 4 models
with complete data, 10.0 to 100.0 kW (FIMER took over ABB's ...)»). Costo misurato: 0,02 s il catalogo, 0,22 s le
alternative per le 150 marche [V, script in locale]. Dopo `ask`: se i preferiti sono cambiati, `cfg` aggiornato e
`_save_config()`; poi `if not ok: return` come prima; `candidates` da `records`.

## 2. Difetti trovati (nel codice di partenza) e correzioni

1. **La lista a tutto schermo** (R268, medium): `QInputDialog.getItem` con 165 voci apre una tendina alta quanto lo
   schermo. Riproduzione: non riproducibile offscreen in prova (la tendina di Qt si misura sullo schermo); verificato
   invece che il nuovo elenco è alto 226 px con 165 marche e scorre fino all'ultima
   (`test_the_list_is_about_eight_rows_tall_and_scrolls_to_every_name`).
2. **Marche non dimensionabili proposte come le altre** (da F, medium): «ABB» era la prima voce della tendina e dava
   solo un errore dopo la ricerca. Ora attenuata, dopo le altre, con il perché e «FIMER» nel suggerimento
   (`test_the_attenuated_names_come_last_stay_reachable_and_say_why`; nel programma verificato con lo script delle
   foto: 150 attenuate, 9 con alternativa).
3. **Nessun difetto nuovo in `config._typed`**: una lista di testi passava senza controllo (le liste non erano
   tipizzate: `recent`, `report_profiles`, `map_sources` sono lette voce per voce da chi le usa). Per il campo nuovo ho
   aggiunto `_TEXT_LISTS`: una stringa, una lista con un numero o un dizionario sotto quella chiave sono «danno» e
   si recupera la copia precedente (prova con i tre casi). Salvataggio e riavvio con accenti: verificato
   (`["Huawei", "SMA", "Zeta Énergie"]` scritto in UTF-8 e riletto uguale).

## 3. Difetti sospetti non confermati

- `tests/formati/test_recovery.py::Instances::test_a_new_start_clears_the_locks_of_crashed_starts_and_keeps_the_live_ones`
  fallisce (3 != 2, e da solo con un errore): è una prova nuova di un altro agente (sottoprocessi veri con lock),
  non toccata da me e non legata al mio lavoro; da guardare da chi l'ha scritta (potrebbe soffrire del carico
  degli agenti in parallelo).
- Il delegato disegna i testi con `design.text_font(Text.BODY, option.font)`: se la dimensione del testo cambia a
  finestra aperta (`theme.change_text_size`) la finestrella, modale e breve, non è mai aperta in quel momento;
  non verificato il caso.
- Su Windows 11 con lo stile nativo del sistema le finestrelle hanno gli angoli arrotondati dal sistema (§5 delle
  regole): il `QDialog` non è una «finestrella» di quel tipo e non ho previsto nulla in più. Non verificato sullo
  schermo vero (regola: solo offscreen).

## 4. Modifiche richieste a file non miei (testo esatto)

I tre test di finestra mimano `QInputDialog.getItem`, che `_size_inverters` non chiama più: con il codice nuovo
**restano appesi** (la finestrella modale aspetta per sempre offscreen). Le patch sotto le ho provate su copie nel
mio scratchpad con lo stesso `_setup`: 6 prove, tutte verdi in 39 s [V].

`tests/finestra/test_sizing_async.py`:
- riga 38: `patch('meridiana.ui.window.QInputDialog.getItem', return_value=('Acme', True)):` →
  `patch('meridiana.ui.brand_picker.NameDialog.ask', return_value=('Acme', True, [])):`
- riga 74: `patch('meridiana.ui.window.QInputDialog.getItem', return_value=('', False)) as ask:` →
  `patch('meridiana.ui.brand_picker.NameDialog.ask', return_value=('', False, [])) as ask:`

`tests/finestra/test_phase_bar.py` (righe 134 e 147, uguali):
- `mock.patch.object(QInputDialog, "getItem", return_value=("Acme", True)):` →
  `mock.patch("meridiana.ui.brand_picker.NameDialog.ask", return_value=("Acme", True, [])):`
  (la riga `from PySide6.QtWidgets import QInputDialog` che precede può restare o andare via).

`tests/finestra/test_window.py`:
- righe 1560, 1571, 1606: `mock.patch.object(QInputDialog, "getItem", return_value=("Acme", True))` →
  `mock.patch("meridiana.ui.brand_picker.NameDialog.ask", return_value=("Acme", True, []))`
- riga 1587: `mock.patch.object(QInputDialog, "getItem", return_value=("Acme", False)) as cancelled:` →
  `mock.patch("meridiana.ui.brand_picker.NameDialog.ask", return_value=("Acme", False, [])) as cancelled:`
- riga 1590: `self.assertEqual(cancelled.call_args.args[4], 0)                 # the remembered brand is preselected` →
  `self.assertEqual(cancelled.call_args.kwargs["current"], "Acme")   # the remembered brand is preselected`

`po/it.po`: i msgid del §5. `docs/richieste.md`: R268 da aggiornare con l'esito. `docs/design/sistema-grafico.md`
§4: una riga «Scelta di un nome | `ui/brand_picker.py` | ricerca senza maiuscole e accenti, elenco di 8 righe,
preferiti in cima con la stella, attenuati in fondo col perché, tastiera completa» e §7 il modulo fra i generici
(dipende da `design`, `theme_colors`, `i18n`). Non ho toccato i documenti: non erano nell'incarico.

Da decidere (Daniel o coordinatore): se la finestrella debba anche unire «SolarEdge» e «SolarEdge Technologies Ltd»
in una voce (suggerimento di F): non fatto, il componente mostra i nomi come li dà il catalogo.

## 5. msgid nuovi e traduzioni proposte

`ui/brand_picker.py`:
- "Favourites" → «Preferiti»
- "All" (intestazione generica, il chiamante può sostituirla) → già in `it.po` come «Tutti» (voce del catalogo), va bene
- "Search…" → «Cerca…»
- "Add to favourites (Ctrl+D)" → «Aggiungi ai preferiti (Ctrl+D)»
- "Remove from favourites (Ctrl+D)" → «Togli dai preferiti (Ctrl+D)»

`ui/window.py` (`_size_inverters`):
- "Search a manufacturer" → «Cerca una marca» («Manufacturer:» è già «Marca:»)
- "All manufacturers" → «Tutte le marche»
- "No model of {maker} in the catalogue has the datasheet data the sizing needs." → «Nessun modello di {maker} nel
  catalogo ha i dati di scheda tecnica che servono al dimensionamento.»
- "Sizable instead: {brands}." → già di F (§8 del suo rapporto: «Si possono dimensionare invece: {brands}.»)

## 6. Prove eseguite

Ambiente: Git Bash, `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH="tests;src"`, PATH con PySide6 del venv,
Python `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.

- `python -m ruff check --select F,E9,B src/meridiana/ui/brand_picker.py src/meridiana/config.py
  src/meridiana/ui/window.py tests/widget/test_brand_picker.py tests/formati/test_formats.py
  tests/formati/test_config.py`: All checks passed.
- `python -m unittest tests.widget.test_brand_picker tests.formati.test_formats tests.formati.test_config`:
  49 prove, OK (2 s).
- `python -m unittest discover -s tests/formati -t tests`: 95 prove, 1 fallimento, `test_recovery.Instances` (non
  mio, §3); prima della correzione di `test_config` erano 2 (la versione fissata a 23).
- `python -m unittest tests.nucleo.test_release`: 6 OK (nessun trattino lungo, anche nei file nuovi).
- Copie patchate dei tre test di finestra (§4) nello scratchpad: `test_sizing_async_m` (3), `test_phase_bar_m`
  (2: `test_propose_is_a_menu...`, `test_sizing_without_modules...`), `test_window_m.PlantPhase.test_the_plant_phase_lends...`:
  6 OK in 39 s. Le prove originali NON le ho lanciate (si bloccherebbero).
- Foto offscreen (`dialog.grab()`, con le 165 marche vere, 150 attenuate, preferiti Huawei/SMA/Fronius, progetto
  «SMA»; e con 3 nomi e 1 preferito), guardate una per una:
  - `build/claude-r07/M-picker-chiaro-x1.png`, `M-picker-scuro-x1.png` (423 x 346 px);
  - `M-picker-chiaro-x2.png`, `M-picker-scuro-x2.png` (`QT_SCALE_FACTOR=2`, 846 x 692 px: anello del fuoco 2 px
    di accento, stella e testi nitidi, nessun gradino);
  - `M-picker-pochi-chiaro-x1.png`, `M-picker-pochi-scuro-x2.png` (3 nomi: elenco di 5 righe, 142 px);
  - `M-picker-ricerca-scuro-x1.png`, `M-picker-ricerca-chiaro-x2.png` (ricerca «sol»: 3 dimensionabili in cima,
    poi le CEC attenuate, nessuna intestazione perché i preferiti non corrispondono).
  Visto nelle foto: pillola della selezione `select_bg` con raggio 4, stella piena sui preferiti e contorno sulla
  riga in mano, intestazioni maiuscole attenuate, OK/Annulla con le icone di Fusion come gli altri dialoghi del
  programma (non è mio: lo stile dei `QDialogButtonBox` è quello di tutta Meridiana).

## 7. Limiti e cose non verificate

- Nessuna prova sullo schermo vero né a mano con la finestra intera: la finestrella è stata vista solo offscreen e
  da sola (non aperta dal comando «Dimensiona da solo» con un progetto vero: i test di finestra che lo fanno sono
  quelli del §4, verificati sulle copie).
- `po/it.po` non toccato: in italiano i testi nuovi escono in inglese finché Claude non aggiunge i msgid.
- Il suggerimento sulla stella e sugli attenuati è fatto nel mio `event()` con `QToolTip.showText`: ha la
  formattazione dei suggerimenti del programma (`popups.lay_out_tip` formatta l'etichetta quando compare), ma non
  l'ho fotografato.
- Non ho misurato i tempi di apertura con il catalogo vero dentro la finestra (solo nello script: 0,25 s in tutto
  per calcolare attenuati e alternative, prima di aprire).
- `tests/formati/test_recovery.py` rosso per una prova non mia (§3).

## 8. Proposta di port nel modello Qt (`C:\Users\Grasso\dev\qt-app-template`, non modificato)

1. Copiare `src/meridiana/ui/brand_picker.py` in `src/qtkit/name_picker.py` (nome generico: nulla dentro parla di
   inverter) cambiando solo gli import: `from .. import theme_colors` → `from . import theme_colors`;
   `from ..i18n import _` → `from .i18n import _`; `from . import design` e `from .design import ...` invariati.
   Nessun'altra dipendenza (niente `paths`, niente icone: la stella è disegnata).
2. Prove: `tests/widget/test_brand_picker.py` → `tests/test_name_picker.py` con `support` al posto di `_setup`
   (`qt_or_skip`, `meridiana_look` → l'equivalente del modello, `dispose`, `keyboard_or_skip`), gli stessi 13 casi;
   la prova dei colori usa i gettoni `card`, `select_bg`, `text` e `theme_colors.faded_text`, che il modello ha.
3. Galleria (`gallery.py`): una voce «Scelta di un nome» con 30 nomi, 2 preferiti, 3 attenuati, uno scelto: è il
   controllo dell'armonia in chiaro e scuro (le quattro foto di questo rapporto sono il riferimento).
4. Documenti del modello: una riga in `docs/da-dove-viene.md` (origine `ui/brand_picker.py`, R268, commit da
   registrare dopo l'integrazione) e il componente nella tabella dei componenti del `README`/`sistema-grafico`:
   «ricerca senza maiuscole e accenti; elenco di al massimo 8 righe; preferiti in cima con la stella; attenuati in
   fondo col perché; Su/Giù, Invio, Esc, Ctrl+F, Ctrl+D».
5. Le impostazioni: il modello non prescrive dove stiano i preferiti; il contratto è «il chiamante passa la lista e
   si tiene quella restituita da `ask`, anche con Annulla». In Meridiana sta in `config.inverter_brand_favourites`.
6. Manifest `template-sync-qt_Rnn.json`: una voce `ui/brand_picker.py` → `name_picker.py` con l'hash del file al
   commit, nella revisione successiva (non dichiarare allineamento prima del commit di Meridiana).
