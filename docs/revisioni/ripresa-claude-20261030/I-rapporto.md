# Rapporto I: modifiche chieste da E, F, H applicate e verificate (Opus I, 30/10/2026)

Cartella `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, ramo `integra-kimi-9-10`, nessun commit, nessun file di
altri agenti toccato. Legenda: **[V]** verificato (con la prova indicata), **[D]** dedotto, **[NV]** non verificato.
Script di prova fuori dal repo:
`C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\opusI\`.

## 1. Che cosa ho rivisto e toccato

- `src/meridiana/ui/window.py`: `EnergySignals.step`, `EnergyJob` (`_progress`, docstring), costante nuova
  `PVGIS_STEPS`, `_session_changed` (ramo «file»), `_switch_variant`, `_compute_energy`, `_computing` (docstring),
  `_energy_step`, `_abandon_year` (nuova), `_cancel_pvgis`, `_sizing_done`, `_string_proposal_done`, `_strings_clear`.
  `_size_inverters` (rifatta da Fable M per R268) **non toccata**.
- `src/meridiana/ui/assistant.py`: classe nuova `CardsArea`, costante `DOCKED_CARDS_MIN`, contenitore delle schede,
  `_fit_cards`, `add_card`, `remove_card`, `set_docked`.
- `src/meridiana/ui/voice.py`: `Kokoro._err`.
- `src/meridiana/ui/preferences.py`: `MeridioPage._set_key`, `_forget_key`.
- Prove: `tests/finestra/test_waits.py` (helper `watch` spostato nella classe base, classe nuova `Years`),
  `tests/finestra/test_sizing_async.py` (classe nuova `WhatTheChoiceSays`), `tests/finestra/test_assistant_window.py`
  (asserzioni nuove sul dock basso), `tests/finestra/test_meridio_projects.py` (misura a fumetto aperto),
  `tests/widget/test_attachments_catalog.py` (KeyError), `tests/widget/test_voice.py` (prova nuova),
  `tests/widget/test_preferences.py` (prova nuova).
- `tests/_setup.py`: **non toccato** (vedi 2.9).

## 2. Difetti trovati, riproduzione, correzione, prova

### 2.1 Anni della produzione accumulati nel pool (E punto 1, R266, alto) [V]
- Prima: `_compute_energy` creava un nuovo `EnergyJob` senza fermare il precedente; il vecchio arrivava in fondo e
  consegnava il suo anno (scartato per generazione) dopo aver occupato un thread e il GIL.
- Correzione: `self.energy_job.interrupt()` prima del nuovo job.
- Prova: `finestra.test_waits.Years.test_a_year_asked_again_stops_the_one_before_which_tells_nothing` (rete finta da
  40 blocchi: due avvii ravvicinati; il primo si ferma al blocco successivo con `Interrupted`, non consegna nulla, il
  secondo arriva in fondo). **Rossa col comportamento di prima** (script `red_two_starts.py`, che rimette il vecchio
  `_compute_energy`: `AssertionError: Lists differ: [2] != []`, il primo job consegna l'anno), verde dopo.

### 2.2 L'anno del progetto vecchio consegnato al progetto appena aperto (trovato rivedendo, medio) [V]
- `session.take` (apri, nuovo, recupero, import) svuota l'anno ma non cambia la generazione: un job ancora in corso
  consegnava l'anno del progetto **precedente** al nuovo (mostrato grigio, e con `_energy_done` che può fare
  `meteo.capture` e un passo «Scarica il meteo» nell'annulla del nuovo progetto). Stesso caso col cambio di variante.
- Riproduzione: `finestra.test_waits.Years.test_another_project_opened_while_a_year_is_computed_never_gets_that_year`
  **rossa prima** (`win.energy` con le note dell'anno vecchio, nessun anno chiesto per il nuovo), verde dopo.
- Correzione: `_abandon_year()` (interrompe il job, fa passare la generazione, toglie le attese), chiamata dal ramo
  «file» di `_session_changed`, da `_switch_variant` e da `_cancel_pvgis`. Il cambio di variante è corretto allo stesso
  modo ma **senza prova propria** [D].

### 2.3 Barra della produzione che avanza nel passo della rete, etichetta, Cancel senza rete (E punti 2-4) [V]
- `EnergySignals.step = Signal(int, float, int, str)`; `_energy_step` riceve `done` float, `n=int(done)+1`.
- Etichetta: «Production: {what} ({n} of {total})»; **«PVGIS: ...» resta solo sui passi che possono chiedere PVGIS**
  (0 l'anno tipo, 1 l'orizzonte, 3 la stima PVGIS, costante `PVGIS_STEPS`) e solo se il job può usare la rete. Scelta
  mia rispetto alla «proposta minima» di E (tutto «Production:»): con la rete attiva l'utente vede ancora quando parla
  davvero PVGIS, che era l'intento di E. Per questo `tests/finestra/test_waits.py` riga 218
  (`"PVGIS: the horizon (2 of 3)"`, rete attiva, passo 1) **resta vera e non l'ho cambiata**.
- Cancel anche senza rete: al primo passo del job, se la barra non è già in corso, le parole («Production:
  Computing…») lasciano il posto alla barra con Cancel (stessa soglia di 300 ms).
- `_cancel_pvgis` dice «Production stopped: the values are those of the last computation.».
- Prova: `finestra.test_waits.Years.test_a_year_without_the_network_has_its_bar_and_cancel` (la barra compare senza
  rete, sempre «Production: the electrical network (3 of 4)», valori crescenti dentro il passo, Cancel la toglie, il job
  si ferma, nessun anno). **Rossa** con il vecchio `_energy_step` rimesso con una patch (`red_old_window.py`: la barra
  non compare, `False is not true : []`), verde dopo.
- Le prove esistenti `Bars.test_pvgis_moves_the_bar...` e `Arcs.test_the_arcs...` (parole «Production» prima del
  primo passo) restano verdi.

### 2.4 «PVGIS is off...» copriva il messaggio appena dato (diagnosi della prova rossa di H `Stringing`, medio) [V]
- Sintomo di H: `'Plant > Strings: all 4 strings cleared' not found in 'PVGIS is off in Settings > Privacy: ...'`.
- Causa: dopo ogni modifica l'anno ricalcolato da sé (`energy_timer`, 500 ms) passa da `_compute_energy`; senza meteo
  in cache e con PVGIS spento chiama `self.tell(refused)` e **sostituisce il messaggio della modifica** (barra di stato).
  La prova cade quando l'attesa del piano supera 500 ms (carico). Non è una prova vecchia: è un difetto dell'uso vero
  (ogni modifica cancellava dopo mezzo secondo il messaggio di R244).
- Riproduzione: `slow_plant.py` (rallenta `plant_model.build` di 0,9 s): **rossa** con lo stesso messaggio, alla riga
  1722 (`'Plant > Strings:' not found in 'PVGIS is off in Settings > Privacy: ...'`); da sola senza carico la prova
  passava. Verde dopo la correzione con lo stesso rallentamento.
- Correzione: chiesto dal progettista (`fetch=True`) il rifiuto si dice sempre; un anno ricalcolato da sé lo dice solo
  se la barra di stato è libera.
- Prova: `finestra.test_waits.Years.test_pvgis_refused_is_said_when_asked_never_over_what_a_change_said`.

### 2.5 `ngettext` in `_strings_clear` (E punto 5, basso) [V lint]
Singolare «the string was cleared; its modules stay laid». Nessuna prova nuova (la prova `Stringing` usa 4 stringhe).

### 2.6 Dimensionamento: note, motivo su più righe, stringhe con condizione (F punto 7) [V]
- `_sizing_done`: con una scelta riuscita aggiunge «Note: {notes}» (`result.notes`: condizione S1400, combinazioni non
  decise), messaggio per 30 s. Con un fallimento la barra di stato mostra la prima riga e, se il motivo ha altre righe,
  `QMessageBox.information(self, "Size the inverter by itself", result.reason)`.
- `_string_proposal_done`: `failed` usa `plant_model.acceptable(s)` (testo di F); in più, se le stringhe applicate hanno
  condizioni (`plant_model.conditions_of`), il messaggio le dice con «Note: ...» (aggiunta mia: senza, l'utente non
  sapeva perché la proposta era gialla).
- Prove: `finestra.test_sizing_async.WhatTheChoiceSays.test_a_choice_made_says_its_notes`,
  `test_a_choice_impossible_says_its_first_line_and_shows_the_whole_reason`,
  `test_strings_whose_only_warning_is_a_condition_are_proposed_and_the_condition_said` (una stringa con solo
  `opt_fuses` è applicata e la condizione detta; con anche una perdita, rifiutata). **Tutte e tre rosse** con il
  comportamento di prima rimesso con una patch (`red_old_window.py`: note mai dette; il motivo intero nella barra di
  stato; `acceptable` = solo `state == "ok"`), verdi dopo.

### 2.7 Schede del fumetto agganciato che bloccavano l'altezza del pannello (H 4.4, strada a) [V]
- Le schede sono ora in `CardsArea` (`QScrollArea`): **a fumetto** nessuna barra e altezza intera (il fumetto le mostra
  come prima: misurato, schede larghe 286 px come il pannello e alte quanto il loro testo a quella larghezza);
  **agganciato** l'area scende fino a `DOCKED_CARDS_MIN` (56 px) e scorre. L'altezza si ricalcola al cambio di
  larghezza e a ogni `LayoutRequest` delle schede (una scheda arriva, va o cambia testo).
- Due trappole trovate e gestite: lo stile dell'applicazione (`ScrollStyle.polish`) mette a ogni `QScrollArea` la barra
  sempre presente e l'aria sopra/sotto (`fades.attach(..., auto=True)`): `CardsArea.event(Polish)` la riporta a «nessun
  margine» (`fades.attach(self)`) e alla politica giusta (`follow_dock`); con la politica «as needed» la barra restava
  attaccata (contenuto misurato alla larghezza con la barra), per questo a fumetto è «always off».
- Prove: `finestra.test_assistant_window ... test_ctrl_l_the_size_of_the_bubble_and_the_dock_are_kept_and_the_dock_has_its_own_button`
  (era rossa `356 not less than 260`; ora verde, con asserzioni nuove: nel dock basso la scheda c'è, l'area è più bassa
  delle schede, scorre, il campo resta sotto) e `widget.test_attachments_catalog ... test_docked_suggestions_do_not_lock_panel_above_compact_threshold`
  (era rossa `340 not less than 260`), entrambe **senza soglie allentate**.
- `finestra.test_meridio_projects ... test_the_card_shows_path_and_revision_and_discard_allows_opening` misurava la
  scheda a fumetto **chiuso** (geometria mai disposta: 640 x 480 di default dentro un'area nascosta). Ora apre il
  fumetto e verifica di più: scheda non schiacciata (altezza >= `minimumSizeHint`), niente da scorrere, area e
  contenitore alti almeno quanto la scheda.

### 2.8 Kokoro: «ready» letto dopo il timeout di 60 s (H 4.1) [V]
- Correzione di H applicata in `Kokoro._err` (`if self.stopping: continue`).
- Prova: `widget.test_voice.NaturalVoice.test_a_ready_read_after_the_load_timeout_leaves_the_sentences_to_the_voice_in_its_place`
  (la sequenza di `kokoro_race.py`): **rossa prima** (al Kokoro che si chiude erano scritti la frase e `{"drop": true}`),
  verde dopo (nulla al worker, la frase alla voce di sistema).

### 2.9 Chiavi: Impostazioni e keyring delle prove (H 4.2 e 4.3)
- `_set_key` e `_forget_key` chiamano `setup.keys_changed()` dopo aver salvato o tolto la chiave. Prova:
  `widget.test_preferences.PreferencesAlone.test_a_key_stored_or_removed_here_is_read_again_by_whoever_remembered_it`
  (**rossa prima**: `1 != 2`, verde dopo).
- Keyring finto in `_setup.window`: **non serve, e non l'ho aggiunto** [V]. `tests/_setup.py` riga 28 imposta già
  `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring` per tutte le prove; verificato con `which_keyring.py`: le
  letture della chat in una finestra di prova passano dal backend `keyring.backends.null` (tre letture, tutte lì). La
  premessa di H («le prove leggono il keyring vero del PC») è falsa; resta vero che le letture avvengono (sul backend
  nullo), innocue.

### 2.10 `widget.test_attachments_catalog ... KeyError: 'local'` (prova da diagnosticare) [V]
- Causa: la prova chiama `chat._start(..., cloud)` con la destinazione scelta «local» (default della configurazione).
  Da R07 `_start` legge l'endpoint del fornitore scelto (`cloud_profile()`, per azzerare la conversazione quando cambia
  destinazione) e `CLOUD["local"]` non esiste. Nell'uso vero `_start` riceve un fornitore cloud solo dopo
  `wants_cloud()` (`ask`, `_consented`) [V lettura del codice]: è la prova a essere vecchia rispetto al cambio di A.
- Correzione della prova: `self.cfg.assistant_provider = 'claude'` prima del turno cloud. Controlla ancora ciò per cui
  è nata (dopo un turno locale, la nuova domanda cloud non porta la cronologia locale né i documenti).

## 3. Difetti sospetti non confermati

- `waiting.Progress` (file non mio) ha ancora la docstring «only for PVGIS and the PDF report»: ora vale anche per ogni
  anno della produzione. Da aggiornare chi ha `ui/waiting.py`.
- Con la barra anche senza rete, per i calcoli brevi (sotto 300 ms) non compare nulla, come prima; per quelli tra la
  soglia e il primo passo si vedono le parole, poi la barra [D].
- `_abandon_year` sul cambio di variante: corretto ma senza prova propria [D].
- `_string_proposal_done` con «Complete the strings»: se le stringhe disegnate a mano hanno avvertenze (non condizioni),
  il completamento resta rifiutato come prima: comportamento non cambiato, non indagato.

## 4. Modifiche richieste a file non miei

- `po/it.po` (vedi 5): msgid nuovi, il plurale nuovo di «all {n} strings cleared» (la voce esistente diventa
  `msgid`/`msgid_plural`), e «PVGIS stopped: the values are those of the last computation.» ora non più usato.
- `src/meridiana/ui/waiting.py`, docstring di `Progress`: «For the long works that know how far they are (PVGIS, the
  PDF report and every year of the production since R266; study 16, F4) ...».

## 5. msgid nuovi o cambiati e traduzioni proposte

| msgid | traduzione proposta |
|---|---|
| `Production: {what} ({n} of {total})` | `Produzione: {what} ({n} di {total})` |
| `Production stopped: the values are those of the last computation.` | `Calcolo della produzione fermato: i valori sono quelli dell'ultimo calcolo.` |
| `Note: {notes}` | `Nota: {notes}` |
| ngettext singolare `Plant > Strings: the string was cleared; its modules stay laid. Use Draw or Propose to start again. Undo restores the previous wiring.` | `Impianto > Stringhe: eliminata la stringa; i suoi moduli restano posati. Usa Disegna o Proponi per ricominciare. Annulla ripristina i collegamenti precedenti.` |
| plurale (msgid esistente) `Plant > Strings: all {n} strings cleared; ...` | invariata: `Impianto > Stringhe: eliminate tutte le {n} stringhe; i moduli restano posati. Usa Disegna o Proponi per ricominciare. Annulla ripristina i collegamenti precedenti.` |

Riusati senza cambi: `PVGIS: {what} ({n} of {total})`, `Size the inverter by itself`. Non più usato:
`PVGIS stopped: the values are those of the last computation.`.

## 6. Prove eseguite

Ambiente delle regole (Git Bash, offscreen, `PYTHONPATH="tests;src"`, PySide6 nel PATH, Python del venv di
`C:\Users\Grasso\dev\meridiana`).

- Widget: `python -m unittest widget.test_assistant_widget widget.test_assistant_presentation widget.test_assistant_local widget.test_assistant_setup_r07 widget.test_attachments_catalog widget.test_voice widget.test_preferences widget.test_string_list widget.test_navigation_targets widget.test_theme` -> 98 OK.
- Finestra (dimensionamento, stringhe, energia, Meridio, voce, attese): `python -m unittest finestra.test_assistant_chat finestra.test_assistant_window finestra.test_meridio_projects finestra.test_meridio_privacy finestra.test_meridio_tasks finestra.test_archive_roundtrip_races finestra.test_help_box finestra.test_support_flow finestra.test_waits finestra.test_sizing_async finestra.test_string_proposal_async finestra.test_climate_auto finestra.test_project_privacy finestra.test_phase_bar finestra.test_checks_views finestra.test_speed finestra.test_window` -> 126 prove in 548 s, **1 errore e 1 fallimento**:
  - `finestra.test_string_proposal_async ... test_valid_partial_wiring_is_applied_and_unconnected_modules_are_reported`: `TypeError` mio (la prova usa `tell=list.append`, io passavo la durata anche senza condizioni). Corretto: la durata si passa solo con una condizione. Rieseguito: verde.
  - `finestra.test_assistant_chat.Cloud.test_a_new_api_address_asks_again_and_starts_a_fresh_conversation` (`self.idle()` entro 10 s): da sola **3 volte su 3 verde**, e verde nel modulo intero; caduta di tempo sotto carico (altri agenti al lavoro), non un difetto [V ripetizione, D causa].
- Dopo le correzioni: `python -m unittest finestra.test_string_proposal_async finestra.test_sizing_async finestra.test_assistant_chat` -> 43 OK; `finestra.test_waits` -> 10 OK; `finestra.test_assistant_window widget.test_attachments_catalog finestra.test_meridio_projects` -> verdi.
- `slow_plant.py` (Stringing con il piano rallentato di 0,9 s): verde dopo, rossa prima.

- `python -m ruff check --select F,E9,B` sui file toccati: «All checks passed!»; nessun U+2014.
- Rosse prima / verdi dopo: `red_two_starts.py` (2.1), `red_old_window.py` (2.3, 2.6: 4 prove, tutte rosse), prova del cambio di progetto (2.2, eseguita sul codice prima
  della correzione), `slow_plant.py` (2.4), prova Kokoro (2.8), prova delle chiavi (2.9), prove del dock (2.7).

## 7. Limiti e cose non verificate

- Solo Windows offscreen. Nessuna foto del fumetto e del dock: l'aspetto delle schede in un dock basso che scorre (barra
  di 10 px, sfumature in alto e in basso di `fades`) va guardato sullo schermo [NV].
- Il «rosso prima» di 2.1, 2.3 e 2.6 è provato rimettendo la logica vecchia con patch (non con il file vecchio intero).
- Suite intera non eseguita (compito del consolidamento).
