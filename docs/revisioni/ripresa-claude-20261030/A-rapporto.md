# R07, lotto A: revisione indipendente (Opus A, 30/10/2026)

Ambito: R259/R260 (fornitori cloud di Meridio, configurazione, chiavi nel keyring, consenso per destinatario,
guida locale/cloud, voce Kokoro). Base `23bd7a9`, lavoro R07 non committato. Nessun commit, nessuna chiamata a
fornitori reali (solo FakeAnthropic/FakeServer e keyring in memoria), nessuna rete, nessuna chiave letta.

Legenda: **[V]** verificato (con la prova indicata), **[D]** dedotto dalla lettura, **[NV]** non verificato.

## 1. Che cosa ho rivisto

- `src/meridiana/assistant/setup.py` (nuovo, intero), `src/meridiana/ui/assistant_setup.py` (nuovo, intero).
- `git diff 23bd7a9` di: `ui/assistant_chat.py` (menu, choose, apply_preferences, ask/consenso/_start, _progress,
  stop, show_setup, _opened, WindowHost.navigation_settings), `ui/preferences.py` (MeridioPage, Preferences
  SECTIONS/_edited/undo, collegamenti), `config.py` (v22 -> v23 e validazione `_typed`), `assistant/providers.py`
  (OpenAICompatible, Ollama, Anthropic), `assistant/local.py` (`suggested`), `ui/assistant_local.py` (domanda RAM,
  scheda licenza), `assistant/speech.py` (`model_dirs`, `worker_python`), `ui/voice.py` (Kokoro: timeout di carico,
  `--kokoro-worker`), `assistant/persona.py`, `assistant/tools.py` (`read_navigation`),
  `assistant/navigation_help.py`. `kokoro_worker.py` non è cambiato rispetto a 23bd7a9.
- Lette per contesto (non mie): `assistant/privacy.py`, `assistant/keys.py`, `assistant/costs.py`,
  `ui/assistant.py` (stop/answer/finish), `ui/file_page.py` (ripopolamento Impostazioni), `ui/window.py`
  (`_apply_preferences`).
- Test: `tests/formati/test_config.py`, `tests/formati/test_formats.py`, fixture `config-v22/23.json`,
  `tests/finestra/test_assistant_chat.py`, `tests/nucleo/test_assistant_setup_r07.py`,
  `tests/widget/test_assistant_setup_r07.py`, `tests/nucleo/test_assistant_local.py`, `tests/_fakes.py`.

## 2. Difetti trovati e corretti

### A1. Impostazioni perse al riavvio dopo aver configurato un fornitore cloud (grave) [V]
`config._typed` controllava ogni campo `dict` come «tabella di tasti» (`nome -> [testo]`).
`assistant_cloud_profiles` (`provider -> {model, endpoint}`) non lo è: `Config.from_json` alzava `ValueError`,
`load()` trattava il file come danneggiato, lo metteva da parte e provava il `.bak`; dal secondo salvataggio anche il
`.bak` contiene i profili, quindi **ripartenza con le impostazioni predefinite** (tutte, non solo Meridio).
Stesso difetto, preesistente da R06, per `pending_update` (`{"version", "url"}`, scritto da
`updates.remember_release`): un aggiornamento segnalato e non installato faceva perdere le impostazioni al riavvio.
La fixture `config-v23.json` aveva `assistant_cloud_profiles: {}` (il valore predefinito, contro la regola delle
fixture «una scelta del progettista in ogni chiave»), per questo le prove non lo vedevano.
- Riproduzione: `Config(assistant_cloud_profiles={...})` -> `from_json(to_json())` -> `ValueError ... is not a table of
  keys`; idem `pending_update={"version": "1.2.0", "url": ...}`.
- Correzione (`config.py`): `_TEXT_TABLES = {"pending_update"}` (valori testo) e
  `_RECORD_TABLES = {"assistant_cloud_profiles"}` (valori `dict` di testo); gli altri campi `dict` restano tabelle di
  tasti. Un file con profili di forma sbagliata resta «danneggiato» (recupero dal `.bak`).
- Prova: `formati.test_config.ConfigTest.test_cloud_profiles_and_a_pending_update_survive_a_save_and_the_next_start`
  (rossa prima, verde dopo). Fixture `tests/formati/file/config-v23.json` (file nuovo, non ancora in Git) ora con
  due profili (`anthropic` Sonnet, `mistral`) e un `pending_update` non vuoto; verificato a parte che la vecchia
  `_typed` la dichiara danneggiata (`test_formats` l'avrebbe colta). Fixture v22 intatta. Ho anche convertito la
  fixture v23 da CRLF a LF come le precedenti.

### A2. Il modello scelto dal menu dopo la configurazione Anthropic veniva ignorato (difetto candidato) [V]
Il menu del chip scriveva solo `assistant_cloud_model`; `setup.profile()` dà precedenza a
`assistant_cloud_profiles['anthropic']['model']`, scritto dalla guida. Risultato: si sceglie Sonnet, si usa Haiku.
**Fonte di verità unica decisa: il profilo** (`assistant_cloud_profiles[provider]['model']`) per tutti i sette
fornitori. `assistant_cloud_model` resta solo come lettura di ripiego per un profilo Anthropic senza modello
(impostazioni scritte prima del formato 23) ed è riscritto come specchio dallo stesso punto, così i due valori nel
file non divergono.
- Correzione: nuova `setup.remember(cfg, provider, model, endpoint="")`, unico punto di scrittura (copia nuova della
  tabella, nessuna condivisione con la copia delle Impostazioni); usata da `AssistantSetup.save_cloud` e da
  `Chat.choose` (che ora salva anche il nome canonico `anthropic` invece dell'alias `claude`).
- Secondo difetto trovato con la stessa prova: nel gruppo esclusivo del menu la riga «Claude / Anthropic» veniva
  marcata dopo il modello e gli toglieva la spunta. Ora, se il modello Anthropic è uno dei due del menu, è marcato il
  modello e non la riga del fornitore.
- Prove: `finestra.test_assistant_chat.Cloud.test_a_model_chosen_in_the_menu_after_the_setup_is_the_one_used`
  (rossa prima: `'claude-haiku-5-5' != 'claude-sonnet-5-5'`, poi rossa sulla spunta, ora verde) e
  `nucleo.test_assistant_setup_r07.Setup.test_one_place_writes_the_cloud_model`.

### A3. Regressione: Claude Haiku/Sonnet persi i parametri del compito 14 [V]
La factory generica `setup.make` creava Anthropic con `effort=""` e senza fallback: Haiku 5.5 perdeva `effort: low`
(più lento e costoso), Sonnet 5.5 perdeva `effort: medium` e il fallback sui rifiuti (scelte in `_cloud` a 23bd7a9).
- Correzione: i due modelli del menu tengono i parametri di prima (Haiku `low`; Sonnet `medium`, fallback beta solo
  all'indirizzo Anthropic ufficiale, non promesso da un proxy); un modello scritto a mano riceve i default dell'API
  come voleva A.
- Prova: `nucleo.test_assistant_setup_r07.Setup.test_the_two_claude_models_of_the_menu_keep_their_effort_and_a_typed_model_gets_the_defaults`
  (rossa prima, verde dopo).

### A4. Cambio di destinazione durante una risposta: faccia «pensierosa» per sempre; cambio della voce interrompeva [V]
R07 aveva aggiunto `self.stop()` in `choose`, `apply_preferences`, `_setup_done` (giusto per il consenso: la carta in
attesa viene tolta). Ma `Chat.stop()` non riporta il personaggio a riposo: la risposta tardiva è scartata
(generazione), il pulsante Stop resta visibile e lo stato resta THINKING senza nulla in arrivo. Inoltre
`apply_preferences` è chiamata a ogni ritocco della pagina Assistente: **cambiare la voce (o l'animazione)
interrompeva la risposta in corso**.
- Correzione (`assistant_chat.py`): `_interrupt()` = `stop()` + nota «Stopped.» (msgid esistente) se c'era un turno,
  che riporta a IDLE come il pulsante Stop. `apply_preferences` interrompe solo se cambia la destinazione (fornitore
  canonico, server/modello locale, profili cloud, modello cloud) o se si ritira il consenso; `choose` solo se cambia
  fornitore o modello; `_setup_done` sempre.
- Prova: `finestra.test_assistant_chat.Chat.test_another_destination_while_he_answers_stops_the_turn_and_a_voice_change_does_not`
  (rossa prima sul primo punto; con il vecchio `stop()` da solo rossa su `thinking != idle`; verde dopo; la risposta
  tardiva del vecchio server non compare).

### A5. Limite d'attesa che taglia i modelli che ragionano mentre stanno lavorando [V]
`_progress` annullava se mancava il primo testo visibile entro 60 s (cloud) / 240 s (locale) dalla richiesta. I
modelli con ragionamento in streaming (DeepSeek reasoner, Qwen/Kimi con thinking: `reasoning_content`) o con lunghe
chiamate di strumenti mandano dati senza testo visibile: venivano annullati mentre il server lavorava (e la richiesta
cloud resta fatturata). Il trasporto, invece, ha già un timeout di inattività.
- Correzione: `Provider.active` (ora monotona dell'ultimo evento ricevuto, scritta dal lettore in
  `OpenAICompatible._read`, `Ollama._read_lines`, `Anthropic.stream`); `_progress` annulla dopo `limit` secondi di
  **silenzio** (`now - max(request_started, provider.active)`). Un server muto viene ancora annullato.
- Prova: `finestra.test_assistant_chat.Chat.test_a_model_that_reasons_before_its_first_word_is_not_cut_while_it_sends`
  (con il limite simulato a 2 s: 3,5 s di ragionamento poi la risposta; secondo caso server muto -> annullato
  dalla finestra). Rossa con il comportamento vecchio (script `old_progress.py` nello scratchpad). Una prima versione
  della prova cadeva a caso nel secondo caso: con lo stesso limite il timeout di lettura di `requests` e quello della
  finestra scattano insieme e a volte vince il trasporto («The local model does not answer…»). Corretta la prova (il
  trasporto della prova aspetta 10 s), non il codice: ora verde 3 volte su 3 da sola e nel giro completo.

### A6. Modello locale da 24 GB proposto a un PC con poca RAM dichiarata [V]
`local.suggested` trattava `budget_gb == 0` come «memoria ignota» e proponeva il primo (qwen3.6 35B, ~24 GB). Con
la nuova domanda R07 «quanta RAM ha il PC?», chi risponde 2, 4 o 6 GB ha budget 0 e riceveva il modello più grande.
- Correzione: il caso ignoto è già gestito in testa (RAM e VRAM 0 -> il più piccolo); nel ciclo conta solo
  `need_gb <= budget_gb`, altrimenti il più piccolo.
- Prova: `nucleo.test_assistant_local.Choice.test_on_a_pc_without_models_the_model_to_download_is_the_best_that_fits`
  (sottocasi 2/4/6 GB, rossi prima, verdi dopo; i casi 8/16/32 GB e DANIEL invariati).

### A7. La guida si riapriva a ogni apertura del fumetto dopo «Not now» [V]
`_opened` mostra la guida se `assistant_local_model == ""` e nessun cloud è configurato. Ma `""` è una scelta valida
(«quello che il server serve», llama-server): per questi utenti la carta tornava a ogni apertura, anche dopo «Not
now». Correzione: `setup_declined` per la sessione dopo «Not now»; dal menu «Set up a model…» e dopo un errore del
modello locale la guida si apre comunque.
- Prova: `finestra.test_assistant_chat.Chat.test_the_guide_set_aside_with_not_now_does_not_come_back_at_every_opening`.

### Verifiche senza difetto (prove nuove che passano già)
- Consenso per destinatario e cronologia [V]: `Cloud.test_a_new_api_address_asks_again_and_starts_a_fresh_conversation`:
  consenso dato ad `anthropic`; stesso fornitore a `https://proxy.example.org/anthropic` -> nuova carta di consenso
  con l'indirizzo; dopo «Allow» la richiesta al nuovo indirizzo non contiene la domanda precedente; consenso
  registrato come `anthropic:https://proxy.example.org/anthropic`.
- Impostazioni su copia temporanea [V]: `Cloud.test_the_settings_guide_works_on_a_copy_and_a_voice_change_keeps_the_provider`
  (finestra vera): guida compilata con OpenAI + chiave e lasciata con «Not now» -> nessuna chiave nel keyring,
  configurazione invariata, campo password vuoto; poi cambio di voce applicato subito e fornitore `mistral`, profilo
  e consensi invariati.

## 3. Difetti sospetti non confermati / osservazioni

- **Copia delle Impostazioni non riallineata** [D]: `MeridioPage.setup_cfg` è una copia fatta all'apertura della
  pagina (ripopolata a ogni ingresso in File > Impostazioni). Se, con le Impostazioni aperte, il fornitore o il
  modello cambiano dal chip della chat (possibile solo con Meridio agganciato e visibile accanto al File: non
  verificato che lo sia), il ritocco successivo della pagina (per es. la voce) riapplica destinazione e profili
  vecchi. Stesso comportamento dei radio button prima di R07. Non corretto: proposta, `choice()` restituisca
  `assistant_provider`/`assistant_cloud_profiles`/`assistant_cloud_model` solo se cambiati nella pagina.
- **Keyring e Annulla delle Impostazioni** [D]: «Undo the last change» ripristina la configurazione ma non il
  keyring; una chiave salvata dalla guida resta (orfana se il profilo viene annullato). Coerente con il vecchio
  «Set key», ma da dire.
- **Keyring letto a ogni `refresh()`** [D]: `setup.available()` legge il keyring per ogni fornitore con un modello;
  Anthropic ha sempre il modello di ripiego (`claude-haiku-5-5`), quindi c'è almeno una lettura a ogni refresh, anche
  all'avvio. Su Linux con portachiavi bloccato potrebbe comparire la richiesta di sblocco all'avvio, prima di R07 no.
  [NV] su fw13.
- **Percorso personale nel codice** [D]: `speech.worker_python` cerca anche `~/fvtest/kokoro-venv`, la cartella di
  prova di Daniel sul portatile. Innocuo ma non da prodotto (vale per tutta Italia): proposta di toglierlo.
- **Kokoro: "ready" dopo il timeout** [D]: se la riga `ready` arriva nello stesso giro in cui scatta il timeout di 60 s,
  `ready` e `failed` vengono emessi entrambi; le frasi in coda passano a Kokoro che viene subito chiuso e vanno perse.
  Finestra di pochi millisecondi; non corretto.
- **Testo «within {seconds} seconds»** [D]: con A5 il limite è di silenzio; la frase resta corretta nei casi reali
  (60/240 s), non cambiata per non toccare il catalogo.
- Strumenti del modello [V lettura]: `read_navigation` è di sola lettura; con documenti allegati gli strumenti non
  sono passati (`specs=[]`); le azioni sul progetto restano proposte con clic. Nessun segreto nei profili:
  `validate_endpoint` rifiuta credenziali, query e frammento nell'indirizzo; `repr` di OpenAICompatible/Anthropic
  senza chiave; gli errori mostrati non includono intestazioni.

## 4. Modifiche richieste a file non miei
Nessuna obbligatoria. Da valutare dal root:
- `src/meridiana/updates.py`/consegna: A1 corregge anche la perdita delle impostazioni con `pending_update` non
  vuoto, difetto presente nei pacchetti R06 già installati (Windows). Da citare nelle note di consegna.

## 5. msgid nuovi o cambiati
Nessuno. Ho riusato «Stopped.» (esistente). Nessuna stringa d'interfaccia nuova nelle correzioni.

## 6. Prove eseguite
Ambiente: Git Bash, `PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH="tests;src"`, PySide6 nel PATH, Python
`C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`.
- Base prima delle modifiche: `nucleo.test_assistant_setup_r07 widget.test_assistant_setup_r07
  finestra.test_assistant_chat widget.test_voice formati.test_config formati.test_formats` -> 76 OK.
- Dopo: `nucleo.test_assistant_{answers,local,navigation,persona,setup_r07,suggestions}
  widget.test_assistant_{card,local,presentation,setup_r07,widget} widget.test_voice widget.test_preferences
  formati.test_config formati.test_formats` -> **185 OK**.
- `finestra.test_assistant_chat finestra.test_meridio_privacy finestra.test_archive_roundtrip_races` -> **34 OK** (234 s, dopo la correzione della prova A5).
- `python -m ruff check --select F,E9,B` sui file toccati -> «All checks passed!». Nessun U+2014 nei file toccati.

## 7. Limiti e cose non verificate
- Nessuna chiamata reale ai sette fornitori: protocolli, crediti, regioni e nomi di modello non verificati (come A).
- A5 provato con il server finto a limite ridotto; il comportamento dei veri modelli che ragionano è dedotto dalla
  forma dello stream (`reasoning_content`). Nota [D]: in locale (240 s) e nel cloud (60 s) il limite della finestra
  coincide con il timeout di lettura del trasporto, quindi di solito è il trasporto a chiudere per primo e la
  finestra fa da rete di sicurezza; prima di A5 era invece la finestra a chiudere per prima, anche a dati in arrivo.
- `requests.iter_lines()` raggruppa i pezzi fino a 512 byte quando il server non usa chunked transfer (il server
  finto): per questo la prova usa un limite di 2 s e non 1 s.
- Pacchetti (Flatpak/Windows), worker Kokoro congelato e portachiavi Linux non provati in questa revisione.
- Non eseguita la suite completa (compito del root).
