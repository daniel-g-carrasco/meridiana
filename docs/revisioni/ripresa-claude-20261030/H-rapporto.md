# R07, ripresa H: istanza unica, recupero, chiamanti di open_path, guida del modello, voce (Opus H, 30/10/2026)

Cartella `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, ramo `integra-kimi-9-10`, nessun commit. Nessuna rete, nessuna
chiamata a fornitori, nessuna finestra sullo schermo (tutto offscreen). Legenda: **[V]** verificato (con la prova
indicata), **[D]** dedotto, **[NV]** non verificato.

## 1. Che cosa ho rivisto

- `src/meridiana/app.py` (tutto), `src/meridiana/recovery.py` (tutto), `src/meridiana/session.py` (`autosave`,
  `drop_autosave`, sola lettura), `src/meridiana/ui/window.py` (solo `offer_recovery`, `open_path`, `_open`,
  `_keep_or_discard`; la funzione della marca del dimensionamento non l'ho aperta).
- Quotario: `src/quotario/single_instance.py`, `app.py` (`instance_channel`, `main`), `ui/window.py`
  (`open_handed_over`), `tests/test_single_instance.py`; guida `qt-app-template/docs/dal-template-gtk.md`, sezione 4
  (sola lettura).
- `src/meridiana/ui/assistant_chat.py` (`__init__`, `refresh`, `apply_preferences`, `ask`, `_consented`, `_done`,
  `_failed`, `_surveyed`, `show_setup`, `_setup_done`, `_opened`, `WindowHost.open_project`),
  `src/meridiana/assistant/setup.py`, `src/meridiana/ui/assistant_setup.py`, `src/meridiana/ui/file_page.py`
  (`_open_recent`, `close_page`), `src/meridiana/assistant/speech.py` (`worker_python`), `src/meridiana/ui/voice.py`
  (`Kokoro`, `Voice._kokoro_*`, sola lettura), `ui/preferences.py` (`_show_key`, `_set_key`, `_forget_key`, sola
  lettura), `ui/assistant.py` (`add_card`, `_fit_cards`, filtro Resize, sola lettura).
- Prove: `tests/finestra/test_assistant_window.py` (la prova del dock), `tests/finestra/test_assistant_chat.py`,
  `tests/formati/test_recovery.py`, `tests/nucleo/test_startup_r07.py`, `tests/nucleo/test_assistant_setup_r07.py`,
  `tests/_setup.py`, `tests/_fakes.py`.

## 2. Difetti trovati e corretti

### H1. Il secondo avvio proponeva, e con «No» cancellava, la copia automatica della finestra ancora aperta (alto) [V]
Caso di D: Meridiana aperta con modifiche non salvate, doppio clic su un progetto; il secondo processo diceva
«Meridiana stopped without saving ...», falso, e con «No» cancellava la copia della prima.
- Correzione (`recovery.py`): ogni avvio vero prende un **blocco per processo** (`recovery.claim`, chiamato da
  `app.main`): un file `state/recovery/owners/<pid>-<8 hex>.lock` tenuto aperto con il blocco del sistema
  (`msvcrt.locking` su Windows, `fcntl.flock` su Linux). Ogni copia scritta registra `"owner"`. `pending()` salta le
  copie il cui proprietario tiene ancora il blocco; un blocco lasciato da un arresto è libero (il sistema lo rilascia
  con il processo) e viene tolto. Nel dubbio (file di blocco che non si apre) la copia conta come in uso: mai
  proposta né cancellata a indovinare. Le copie senza proprietario (scritte prima, o dalle finestre delle prove che non
  fanno `claim`) e quelle del processo stesso restano proposte come prima. Il nome del proprietario letto dal file è
  controllato con una regex (`[0-9]+-[0-9a-f]{8}`): mai un percorso. All'avvio `claim` toglie anche i blocchi liberi
  lasciati da arresti senza copie. Uscita normale: `recovery.release` dopo `app.exec()`.
- Corsa su Linux gestita: se un altro avvio toglie il file appena creato prima del blocco, `claim` se ne accorge
  (`os.path.samestat`) e riprova.
- Prove (processi veri):
  - `formati.test_recovery.Instances.test_the_copy_of_a_meridiana_still_running_is_not_offered_to_another`
  - `...test_the_copy_of_a_meridiana_that_crashed_is_offered_and_its_lock_cleared` (processo ucciso)
  - `...test_a_new_start_clears_the_locks_of_crashed_starts_and_keeps_the_live_ones`
  - `...test_this_process_own_copies_and_the_older_ones_are_offered`
  - `...test_an_owner_name_that_is_not_a_lock_of_ours_is_never_a_path`
  - `finestra.test_second_start.SecondStart.test_the_copy_of_the_window_still_open_is_not_offered_and_survives_a_no`
    (finestra vera + processo proprietario): **rossa** con la regola vecchia (`recovery._running` forzato a «nessuno
    vivo»: compare la domanda «Recover the changes» e la risposta predefinita la cancellerebbe), verde dopo.
- Due trappole di Windows trovate scrivendo le prove: il `python.exe` del venv è un lanciatore (il pid di `Popen` non è
  quello dell'interprete: il processo proprietario stampa il suo segno); Windows rilascia i blocchi di un processo
  ucciso un istante dopo (documentato per `LockFileEx`): la prova aspetta il rilascio, il programma resta dal lato
  sicuro (copia non proposta finché il blocco c'è).

### H2. Con «Sì» il recupero ignorava il progetto aperto per nome (medio) [V]
`prepare_workspace` proponeva la copia più recente di qualunque progetto; con «Sì» il file chiesto non si apriva e
nessuno lo diceva.
- Correzione: `app.prepare_workspace` chiama `win.offer_recovery(explicit)`; con un progetto chiesto per nome si
  propone **solo la sua copia** (`recovery.pending(state, progetto)`); le copie di altri progetti non vengono toccate
  e restano per un avvio senza progetto (nessuna perdita). Senza progetto: come prima.
- Prova: `finestra.test_second_start.SecondStart.test_a_project_asked_for_by_name_is_opened_and_another_projects_copy_waits`
  (rossa prima: `offer_recovery` senza argomento e copia altrui proposta; verde dopo). Scelta mia, da confermare a
  Daniel: in alternativa si poteva proporre la copia altrui e poi aprire comunque il file chiesto (ma una finestra ha
  un solo progetto).

### H3. Istanza unica (alto: è la radice di H1) [V]
Nuovo `src/meridiana/single_instance.py`, copia del modulo di Quotario con i nomi di Meridiana (QLocalServer: named
pipe su Windows, socket in `XDG_RUNTIME_DIR` o `$XDG_RUNTIME_DIR/app/$FLATPAK_ID` su Linux; nome con app id e hash
dell'utente; messaggio JSON di una riga con percorsi assoluti e token di attivazione Wayland;
`AllowSetForegroundWindow(ASFW_ANY)` prima di consegnare).
- `app.instance_channel()`: come Quotario. `MERIDIANA_INSTANCE` nomina un altro canale o «off»; con
  `MERIDIANA_SCREENSHOT` (prove, CI, foto) **nessun canale**, salvo uno dato: le prove e le foto non consegnano mai
  file alla finestra di Daniel.
- `app.main`: dopo il log, se un Meridiana risponde gli consegna il progetto (percorso reso assoluto) ed esce con 0.
  Altrimenti ascolta **prima** di costruire la finestra; ciò che arriva intanto (anche durante la domanda di recupero)
  viene tenuto e consegnato appena la finestra è mostrata; se è arrivato un progetto, la visita guidata non parte.
  `--kokoro-worker`, `--self-test`, `--version`, `--help` non passano dal canale.
- `window.open_handed_over(files, token)` (nuova, solo apertura consegnata): finestra davanti (anche se ridotta a
  icona), poi «Salvare le modifiche?» come File > Apri, poi `open_path`, e chiude la pagina File se era aperta. Lo
  stesso progetto già aperto viene solo portato davanti, non riletto. Se è aperto un dialogo modale il progetto
  aspetta (riprova ogni 500 ms). Un file illeggibile è detto da `open_path`.
- Prove (`tests/finestra/test_second_start.py`):
  - `Channel.*` (nome con utente, socket Linux saltato su Windows, messaggi e scarti, regola delle foto);
  - `TwoProcesses.*` (ricevitore e mittente in due processi; nessuno in ascolto: risposta subito);
  - `TwoStarts.test_a_second_start_with_a_project_gives_it_to_the_first_window`: **due avvii veri di Meridiana**
    offscreen con cartelle XDG temporanee e un canale proprio; il secondo esce con 0, il primo apre il progetto
    (`last_project` nel suo config) ed esce lasciando libero il blocco del recupero. **Rossa** con il secondo avvio
    senza istanza unica (`MERIDIANA_INSTANCE=off`, cioè il comportamento di prima: seconda finestra, timeout),
    verde dopo;
  - `SecondStart.test_a_project_handed_over_comes_into_the_open_window_after_its_changes_are_asked_about`.

### H4. `assistant_chat.open_project` diceva «aperto» quando la riapertura dello stesso file falliva (medio) [V]
Testo esatto del rapporto D, sezione 4.1: ora `return self.win.open_path(Path(path))`.
Prova: `finestra.test_second_start.SecondStart.test_an_opening_that_fails_is_said_by_meridio_and_brings_file_open_back`
(rossa prima: `True is not false`).

### H5. Un recente sparito lasciava un progetto vuoto senza File > Apri (medio) [V]
Testo esatto del rapporto D, sezione 4.2: `if not self.host.open_path(Path(path)): self.host.open_file_page("open")`.
Prova: la stessa di H4, seconda parte (rossa con il vecchio `_open_recent` rimesso con `mock`: la pagina non torna).

### H6. La guida «Give Meridio a model» compariva anche con un modello utilizzabile (medio) [V]
Due casi:
- dopo una ricerca locale vuota (`_surveyed`) la guida compariva **sempre**, anche con un fornitore cloud configurato
  che risponde (a un clic nel menu del chip);
- all'apertura del fumetto (`_opened`) contava solo il nome del modello locale nelle impostazioni: un server locale che
  risponde con il modello che serve (`""`, llama-server) riceveva la guida a ogni apertura.
- Correzione: `Chat.model_ready()` = modello locale nominato, oppure server locale che ha già risposto in questa
  sessione (`local_answered`, azzerato quando il locale fallisce o cambia destinazione), oppure un fornitore cloud
  configurato. `_opened` mostra la guida solo senza nessuno di questi; `_surveyed` solo senza cloud configurato (la
  nota «I have not found a local model yet...» resta).
- Prove: `finestra.test_assistant_chat.Cloud.test_with_a_cloud_model_configured_the_guide_does_not_come_when_the_local_one_fails`
  (rossa con il vecchio `_surveyed`, verde dopo) e
  `finestra.test_assistant_chat.Chat.test_a_local_model_that_answered_needs_no_guide_at_the_next_opening` (rossa
  prima, verde dopo).

### H7. Keyring letto a ogni aggiornamento della chat (medio su Linux con portachiavi bloccato) [V]
`refresh()` (a ogni cambio del progetto) e `_opened` chiamavano `setup.available(cfg, keys.get)`: almeno una lettura
del keyring ogni volta (Anthropic ha sempre il modello di ripiego).
- Correzione: `setup.Ready` ricorda **solo se** una chiave c'è (mai la chiave), una lettura per fornitore;
  invalidazione con `setup.keys_changed()` (chiamata da `AssistantSetup.save_cloud` dopo `keys.put`), con
  `Chat.apply_preferences` (le Impostazioni possono aver salvato o tolto una chiave: `_set_key`/`_forget_key`
  emettono `liveChanged` che arriva lì), con `_setup_done`, e quando si cambia `chat.keys` (proprietà: le prove
  mettono il loro finto). Quando `ask` legge davvero la chiave per spedire, il ricordo si allinea (`_cloud_key`).
- Prova: `finestra.test_assistant_chat.Chat.test_the_keyring_is_read_once_per_provider_until_a_key_may_have_changed`
  (rossa prima: 5 aggiornamenti = 10 letture; verde dopo: 2, poi 2 dopo `keys_changed`, 2 dopo `apply_preferences`).

### H8. `~/fvtest/kokoro-venv` nel codice (basso) [V]
Tolto da `speech.worker_python`. Restano gli ambienti accanto al modello (`venv`, `.venv` nella cartella del modello
e in quella sopra, `~/.local/opt/kokoro`); il pacchetto Windows (frozen) usa sempre il proprio eseguibile
(`--kokoro-worker`), il Flatpak il proprio runtime: invariati.
- Prova: `nucleo.test_assistant_setup_r07.Setup.test_kokoro_never_looks_in_a_test_folder_of_one_pc` (rossa prima: il
  Python di `fvtest` scelto; verde dopo; controlla anche frozen e l'ambiente accanto al modello).
- [D] Sul portatile di Daniel, se il modello Kokoro non sta dentro o accanto a `~/fvtest/kokoro-venv`, la voce
  naturale cadrà sulla voce di sistema finché in Impostazioni > Assistente non si indica
  `~/fvtest/kokoro-venv/bin/python` come Python. Da dire a Daniel.

## 3. Difetti sospetti non confermati, e una prova che resta rossa

- **`finestra.test_assistant_window ... test_ctrl_l_..._dock_has_its_own_button` resta rossa (`356 not less than 260`)
  [V].** La premessa del compito («compare anche quando un fornitore cloud configurato risponde») non vale in quella
  prova: lì nessun modello è utilizzabile (server locale finto `offline`, ricerca vuota `nothing_local`, nessun cloud,
  modello locale `""`). La guida c'è quindi a buon diritto anche con la regola nuova (H6), e `_fit_cards`
  (`ui/assistant.py`) fissa l'altezza minima del contenitore delle schede alla loro altezza intera: il dock basso non
  può scendere sotto. Verifica: la stessa prova con la guida tolta nel punto in cui la prova toglie la scheda della
  ricerca (riga 177) passa **intera** (script `dock_with_card_dropped.py` nello scratchpad). Non l'ho allentata. Due
  strade, da decidere (vedi sezione 4): (a) in `ui/assistant.py` le schede cedono in un pannello basso (area che
  scorre), come i suggerimenti: vale per ogni scheda, anche consenso e lista dei modelli locali, che oggi bloccano il
  dock alto; (b) nella prova, togliere anche la guida alla riga 177, perché la prova è nata prima della guida R07.
  Consiglio (a).
- **`widget.test_attachments_catalog.Documents.test_docked_suggestions_do_not_lock_panel_above_compact_threshold`
  rossa (`340 not less than 260`)** [V]: stessa causa della prova del dock (la guida, legittima perché nessun modello
  risponde, blocca l'altezza minima del pannello agganciato). Con la guida mai mostrata passa; con la regola vecchia
  della guida è rossa uguale: non dipende da H6/H7 (script `diag_attach.py` nello scratchpad). Stessa decisione del
  punto 4.4.
- **`widget.test_attachments_catalog.Documents.test_switch_from_document_cloud_to_local_then_cloud_drops_local_history`
  in errore (`KeyError: 'local'`)** [V]: la prova chiama `chat._start(..., cloud)` con `assistant_provider = "local"`;
  `_start` calcola `self.cloud_profile()` e `setup.profile(cfg, "local")` cerca `CLOUD["local"]`. Non dipende dalle
  mie modifiche (stesso errore con la cache del keyring e la regola nuova tolte, `diag_attach.py`). Nell'uso normale
  `_start` riceve un fornitore cloud solo se è scelto il cloud [D], quindi «solo prove»; non corretto perché la
  semantica della prova (un turno cloud avviato a mano mentre è scelto il locale) è di chi l'ha scritta: da
  decidere se correggere la prova (impostare `assistant_provider = "claude"` prima di `_start`) o `_start`.
- **Le prove della finestra leggono il keyring vero del PC** [V lettura del codice]: `_setup.window` lascia
  `chat.keys = keys` (portachiavi reale); `refresh()` all'avvio chiede la chiave `anthropic` al Credential Locker di
  Daniel. Le regole dicono «non leggere chiavi»: va messo un finto in `_setup.window` (sezione 4).
- **Due finestre sullo stesso progetto** [D]: con l'istanza unica non capita più nell'uso normale, ma se il canale non
  funziona (o con `MERIDIANA_INSTANCE=off`) `session.drop_autosave` (salvataggio o chiusura) cancella lo slot del
  percorso, anche se è la copia dell'altra istanza. Lo slot è per progetto, non per processo. Fuori dai miei file
  (`session.py`); non corretto.
- **Guida già mostrata e cloud configurato poi dalle Impostazioni** [D]: la scheda già aperta resta finché non si
  sceglie «Not now». Scelta di presentazione; non cambiata.
- **Wayland**: il token di attivazione è passato come in Quotario [NV: nessun desktop Wayland qui].

## 4. Modifiche richieste a file non miei (testo esatto)

1. **`src/meridiana/ui/voice.py`, `Kokoro._err`** (circa riga 136): la riga `ready` che arriva insieme al timeout di 60 s
   fa emettere sia `ready` sia `failed`; `Voice._kokoro_ready` manda le frasi in coda a Kokoro, che subito dopo viene
   chiuso: frasi perse. Sostituire
   ```python
               if line.strip() == "ready":
                   self.load_timeout.stop()
   ```
   con
   ```python
               if line.strip() == "ready":
                   if self.stopping:           # the load timeout came first: its failure stands, the sentences wait for
                       continue                # the voice that takes Kokoro's place (Voice._kokoro_failed)
                   self.load_timeout.stop()
   ```
   Prova eseguita (non è un mio file, quindi solo nello scratchpad):
   `C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\kokoro_race.py`:
   con l'`_err` attuale la frase va al Kokoro che muore e la voce di sistema non la dice mai (rossa); con la
   correzione la dice la voce di sistema (verde). Prova da portare in `tests/widget/test_voice.py` (stessa sequenza:
   `Voice("en", engine="mock")`, `Kokoro` con un processo finto che risponde `ready`, `load_timeout.timeout.emit()`,
   poi `_err()`). Nota: in italiano il motore `mock` non ha voce e scarta la coda (rifiuto legittimo), per questo `en`.
2. **`src/meridiana/ui/preferences.py`**, `_set_key` dopo `keys.put(provider, key)` e `_forget_key` dopo
   `keys.forget(self._key_provider())`: aggiungere `setup.keys_changed()` (in `_forget_key` importare `setup`). Non
   indispensabile (oggi l'invalidazione arriva da `apply_preferences` via `liveChanged`), ma rende il ricordo giusto
   anche per la pagina Impostazioni stessa (`_show_key` chiama `setup.available(self.setup_cfg)` senza cache: lì
   nessun problema).
3. **`tests/_setup.py`, `window()`** dopo `win.assistant_chat.survey = nothing_local`: nessuna lettura del keyring vero
   nelle prove, per esempio
   `win.assistant_chat.keys = SimpleNamespace(get=lambda provider: "")` (con `from types import SimpleNamespace`).
   Attenzione: le prove `Cloud` di `test_assistant_chat.py` usano `MemoryKeyring` tramite `keyring.set_keyring` e
   `keys.put`: lì `chat.keys` deve restare il modulo `keys` (rimetterlo nel loro `setUp`:
   `self.chat.keys = keys` con `from meridiana.assistant import keys`). Non verificato sull'intera suite.
4. **Prova del dock** (sezione 3): strada (a) in `ui/assistant.py` (`_fit_cards`/contenitore `cards` in un'area che
   scorre quando il pannello è basso), oppure strada (b) in `tests/finestra/test_assistant_window.py` riga 177, dopo
   `win.assistant_chat._drop_survey()`: `win.assistant_chat._dismiss_setup()`. Decisione di Claude/Daniel.
5. **Template Qt** (`qt-app-template`): l'istanza unica ora c'è in due programmi (Quotario e Meridiana, stesso modulo);
   la guida `docs/dal-template-gtk.md`, sezione 4, dice ancora «da scrivere». Il blocco del recupero per processo
   (`recovery.claim`) è nuovo e va portato insieme a `recovery.py` dove il modello lo copia.
6. `docs/richieste.md` e `CHANGELOG.md`: righe da aggiungere da Claude (istanza unica, recupero per istanza).

## 5. msgid nuovi e traduzioni

Nessun msgid nuovo o cambiato. Le stringhe nuove sono solo nel log o nelle eccezioni (inglese, come le altre del log).

## 6. Prove eseguite

Ambiente: Git Bash, `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH="tests;src"`, PySide6 nel PATH, Python
`C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.
- `python -m unittest formati.test_recovery nucleo.test_session` -> 29 OK; `formati.test_recovery` da solo 3 volte di
  fila -> OK, OK, OK.
- `python -m unittest finestra.test_second_start` -> 11 OK (circa 30 s, compresi i due avvii veri).
- Prove rosse prima (script nello scratchpad, `mock` sul vecchio comportamento): `red_recovery.py` (FAIL atteso),
  `test_second_start_old.py` con `MERIDIANA_INSTANCE=off` (TimeoutExpired atteso), `red_recent.py` (FAIL atteso),
  `red_surveyed.py` (FAIL atteso), `kokoro_race.py` (rossa/verde).
- `python -m unittest nucleo.test_assistant_setup_r07 widget.test_voice` -> 20 OK.
- `python -m unittest finestra.test_assistant_chat finestra.test_assistant_window finestra.test_meridio_privacy
  finestra.test_archive_roundtrip_races widget.test_attachments_catalog widget.test_assistant_setup_r07
  nucleo.test_assistant_setup_r07 nucleo.test_startup_r07 widget.test_preferences` -> 74 prove, 2 rosse e 1 in errore,
  tutte descritte in 3 (prova del dock, prova del dock in `test_attachments_catalog`, `KeyError: 'local'`); le nuove
  prove di H tutte verdi. Le tre nuove prove della chat da sole: verdi.
- `python -m unittest formati.test_project_archive finestra.test_save_status` -> 19 OK.
- `python -m unittest finestra.test_window nucleo.test_startup_r07 finestra.test_second_start formati.test_recovery
  nucleo.test_session finestra.test_self_test` -> 73 prove, 1 rossa, 1 saltata. La rossa:
  `finestra.test_window.Stringing.test_nothing_comes_by_itself_and_a_string_is_drawn_numbered_taken_back_closed_and_given_up`
  (`'Plant > Strings: all 4 strings cleared' not found in 'PVGIS is off in Settings > Privacy: ...'`), rossa anche da
  sola due volte. [D] non dipende da H: riguarda stringatura e messaggio PVGIS nella barra di stato, nessuno dei due
  toccato da me; un altro agente sta cambiando `window.py`. Non verificato con le mie modifiche tolte.
- `python -m ruff check --select F,E9,B` sui file toccati -> «All checks passed!»; nessun U+2014.

## 7. Limiti e cose non verificate

- Solo Windows offscreen. Linux (`fcntl.flock`, socket in `XDG_RUNTIME_DIR`, Flatpak) [NV]: il codice segue Quotario,
  già provato là; la prova dei socket Linux si salta su Windows.
- Pacchetto Windows (PyInstaller) e installer non provati: QtNetwork è già nel pacchetto (lo usano le mappe).
- Finestra davanti su Windows reale (`AllowSetForegroundWindow`) e Wayland [NV]: offscreen non lo mostra.
- Nessuna suite completa (compito del root).
