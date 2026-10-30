# D: revisione indipendente del lotto D (avvio, visita guidata, spotlight, fumetto)

Opus D, 30/10/2026. Cartella `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, ramo `integra-kimi-9-10`, nessun commit.

## 1. Che cosa ho rivisto

- `git diff 23bd7a9` di `src/meridiana/app.py` (prepare_workspace, main), `src/meridiana/tour.py` (passo 13, comando
  locale di navigazione), `src/meridiana/ui/tour.py` (tutta: TourDialog nel fumetto), `src/meridiana/ui/spotlight.py`
  (tutta), `src/meridiana/ui/conversation_view.py`, `src/meridiana/ui/assistant.py` (CornerGrip, Bubble,
  intestazione, chat_content, questions_content, `_fit_bubble_content`, `add_card`, filtro eventi del pannello).
- Per contesto (non modificati): `ui/window.py` (`open_file_page`, `_show_assistant`, `offer_recovery`, `open_path`,
  `_offer_tour`, `_start_tour`, `_support_closed`, `closeEvent`, `_preferences`), `ui/file_page.py` (`open_page`,
  `close_page`, `_open_recent`), `ui/assistant_chat.py` (`_opened`, `open_project`), `ui/guide_card.py`,
  `ui/motion.py` (`enter`), `recovery.py`, `assistant/__init__.py` (`bubble_place`), `__main__.py`.
- I test del lotto e `build/overnight-r07/d-verify.py` (rifatto girare su una copia, vedi 6).

## 2. Difetti trovati e corretti

Ogni difetto è stato riprodotto con una prova rossa prima della correzione.

**D1. Argomenti di Qt presi per un progetto da aprire** (`app.py`). `main` leggeva i file da `argv`. Prima il
controllo `target.exists()` copriva il problema. Con l'apertura esplicita di R07 quel controllo non c'è più, e
`meridiana -platform offscreen` (o `-style Fusion`) apriva «offscreen» come progetto: compariva una finestra di
avviso modale prima di `win.show()` e l'avvio si fermava.
- Riproduzione: `test_qt_options_on_the_command_line_are_not_a_project` (processo vero con
  `-m meridiana -platform offscreen`, cartelle XDG temporanee, `MERIDIANA_SCREENSHOT`). Prima: timeout di 90 s.
- Correzione: nuova `app.explicit_project(arguments)`. `main` la chiama con `app.arguments()`, da cui Qt ha già tolto
  le sue opzioni (verificato: `['meridiana','-platform','offscreen','-style','Fusion','C:/x y/progetto.mer']` diventa
  `['meridiana','C:/x y/progetto.mer']`). Su Windows `arguments()` è anche la forma Unicode della riga di comando.
- Docstring del modulo aggiornata: non apre più «the last one opened».
- Prove: `test_only_a_document_argument_is_an_explicit_project` e quella sopra, verdi.

**D2. Testo dei passi tagliato nel fumetto** (`ui/tour.py`). La descrizione aveva politica verticale `Maximum` e il
titolo `Fixed`: altezza bloccata alla sizeHint, calcolata per un'altra larghezza. Si perdeva l'ultima riga, per
esempio «each task.» al passo 2 e «Meridio.» al passo 12. Si vede nelle foto originali
`build/overnight-r07/d-tour-model.png` e `d-tour-settings.png`.
- Riproduzione: `test_every_step_of_the_tour_is_read_whole_in_the_bubble`. Prima: `48 not >= 64` sul passo «model».
- Correzione: tolte le due righe `setSizePolicy(... Fixed/Maximum)`. Resta altezza per larghezza, e lo stretch
  inserito da D prende lo spazio in più (le etichette non si allargano). Verificato nelle foto a 1, 2 e 2,5.

**D3. La visita accendeva Meridio nelle impostazioni** (`ui/tour.py`). `TourDialog.__init__` chiamava
`window._show_assistant(True)`, che scrive `cfg.assistant = True`, e `present()` salvava la configurazione a ogni
passo. Se Daniel aveva spento Meridio e chiudeva la finestra durante la visita, al riavvio Meridio era acceso.
`_finished` ripristinava solo a visita conclusa.
- Riproduzione: `test_a_tour_shows_meridio_without_turning_him_on_in_the_settings` (legge anche il file su disco).
- Correzione: `_show_meridio()` mostra Meridio e rimette subito `cfg.assistant` com'era. Usata nel costruttore e nel
  passo «assistant». A fine visita `_show_assistant(self.host.cfg.assistant)`, cioè l'impostazione attuale (Daniel
  può averla cambiata in Impostazioni durante la visita). Tolti gli attributi non più usati `assistant_was_enabled` e
  `assistant_was_docked`.

**D4. Agganciato a mano durante la visita: stato incoerente** (`ui/tour.py`).
- `_finished` rimetteva `set_docked(stato iniziale)`, mentre `cfg.assistant_docked` diceva il contrario.
- `present()` faceva `assistant.show()` anche da agganciato, e il personaggio fluttuante restava visibile accanto al
  pannello.
- In più, chiudendo da agganciato si faceva prima `set_docked(True)` (pannello mostrato) e poi `close_panel()`: il
  pannello compariva e spariva subito.
- Riproduzione: `test_an_interrupted_tour_gives_the_conversation_back_as_it_was`, ultima parte. Prima: `True is not
  false` su `assistant.isVisible()`.
- Correzione: `set_docked(self.host.cfg.assistant_docked)`. Il personaggio si mostra solo se non è agganciato.
  `close_panel()` viene prima di `set_docked`.

**D5. Fumetto che cresce verso la barra e salta alla prima ridimensionatura** (`ui/assistant.py`,
`_fit_bubble_content`). Il difetto c'era già alla base, ma rientra in R258 (quattro angoli). Con fumetto a
sinistra/destra, cresceva sempre verso l'alto fino a `top`, senza margine. Con Meridio in un angolo alto il fumetto
toccava la barra (y=0 invece di 12). Al rilascio della maniglia `place_bubble` lo riportava a y=12, così l'angolo
«fermo» si spostava di 12 px. Anche con coda in basso cresceva verso il personaggio.
- Riproduzione: `test_in_all_four_corners_the_grip_resizes_and_the_corner_by_him_stays_after_release`, con
  trascinamento e rilascio veri e Meridio in ciascun angolo. Prima: `(62, 12) != (62, 0)` in alto a sinistra.
  Rosso confermato rimettendo la funzione vecchia in memoria.
- Correzione: cresce lontano dal bordo allineato con lui (in giù se Meridio sta nella metà alta o la coda è in alto,
  altrimenti in su), entro `MARGIN`, senza mai spostare il bordo vicino a lui.

**D6. Dopo la visita intera, righe del fumetto sovrapposte** (`ui/assistant.py`). Il difetto si vede nelle foto della
mia verifica. Dopo i 13 passi e «Start», alla prima apertura di Meridio la scheda «Give Meridio a model» (A) arrivava
in un fumetto già adattato. Restava alto 400 px contro un minimo di 472. Scheda, «Suggestions», righe e «Attach PDF»
erano disegnati uno sopra l'altro (`D-conversation-x1.png` della prima corsa). Due cause:
- `add_card` non riadattava il fumetto;
- i suggerimenti ricomparsi dopo l'ingrandimento (filtro Resize del pannello) non lo riadattavano di nuovo.
- Riproduzione: `test_a_card_arriving_in_an_open_bubble_makes_room_instead_of_overlapping` (widget, prima `240 not >=
  387`) e `test_after_the_whole_tour_meridio_opens_without_overlapping_rows` (finestra). Lo script
  `build/claude-r07/D-foto/dbg_d.py all-start` mostrava `overlaps [('QWidget','SuggestionsBox'),
  ('SuggestionsBox','QPushButton')]` prima e `overlaps []` dopo.
- Correzione:
  - `add_card` avvia `questions_timer`, quindi `_fit_questions` e poi `_fit_bubble_content`;
  - il filtro Resize riavvia il timer quando i suggerimenti tornano visibili;
  - `needed` usa `max(sizeHint, minimumSizeHint)` del pannello.

**D7. Prova vecchia del tour rossa** (`tests/nucleo/test_support_tour.py`). Aspettava `version == 22`, ma dopo la
config 23 di A la migrazione arriva a 23. Ora confronta con `config.CONFIG_VERSION`: la prova controlla che tutte le
migrazioni girino. La verifica non è indebolita.

## 3. Sospetti non confermati o fuori dai miei file

- **Prova `test_ctrl_l_..._dock_has_its_own_button` rossa (`356 not less than 260`), segnalata dal coordinatore.**
  Non dipende dalle mie modifiche né, in modo determinante, dal lotto D. La causa è la scheda di configurazione del
  modello di A (`AssistantSetup`, minimo 159 px). `Chat._opened` la mostra perché nella prova
  `cfg.assistant_local_model` è vuoto e `setup.available()` è falso, anche se un fornitore finto sta rispondendo.
  - Prova: stesso test con `Chat.show_setup` reso nullo, OK; così com'è, FAIL.
  - Misura del pannello agganciato basso: testa 47 px + chat_content 285 px, di cui scheda 159.
  - Il titolo centrato di D (R258) alza la testa da circa 28 a 47 px, ma senza scheda il minimo resta sotto 260.
  - `_fit_bubble_content` (che ho toccato) esce subito quando è agganciato.
  - Da decidere ad A o a Claude: (a) mostrare la scheda solo se nessun fornitore è davvero attivo (la prova la vede
    mentre Meridio risponde); (b) in un pannello agganciato basso la scheda dovrebbe scorrere o ridursi, come già i
    suggerimenti, altrimenti il dock non si abbassa e schiaccia gli altri pannelli. Non l'ho corretto: tocca
    `assistant_chat.py` / `assistant_setup.py` ed è una scelta di presentazione.
- **Istanza unica**: non esiste. Nessun `QLocalServer`/`QLocalSocket`; il mutex Windows serve solo all'installatore.
  Un secondo avvio con un `.mer` apre una seconda finestra con quel progetto, il che è coerente con R251. Dal codice
  deduco un problema già presente alla base: `recovery.pending()` non distingue la copia automatica di un'istanza
  ancora aperta.
  - Doppio clic su un `.mer` mentre Meridiana è aperta con modifiche non salvate: la seconda istanza chiede
    «Meridiana stopped without saving ... Recover?», che è falso.
  - Con «No» cancella la copia della prima istanza (`c["file"].unlink`).
  - Con «Sì» ignora il file esplicito, senza dirlo.
  - Fuori dai miei file (`recovery.py`, `window.py`). Proposta: un `QLockFile` per istanza nella cartella state, e
    `pending()` che salta le copie di istanze vive. Non verificato con due processi veri.
- **Chiamanti di `open_path` (ora bool)**: `app.prepare_workspace` usa l'esito. `window._open` e `selftest` lo
  ignorano senza danno. Due casi da sistemare:
  - `assistant_chat.open_project` restituisce `self.win.path == target`. Se si riapre lo stesso file e l'apertura
    fallisce, risponde comunque «aperto».
  - `file_page._open_recent` chiude la pagina prima di aprire. Con un recente mancante all'avvio si resta su un
    progetto vuoto senza la pagina Apri.
- **Prova `test_a_model_that_reasons_before_its_first_word_is_not_cut_while_it_sends`** (`test_assistant_chat`, di A):
  rossa una volta nella corsa insieme ad altri moduli, verde da sola (limite di 2 s, carico in parallelo). Il file di
  prova era stato modificato alle 12:32 da un altro agente.
- **Meridio sopra la pagina File a fine visita**: la visita termina su Nuovo con il personaggio visibile sopra la
  pagina File. Di norma File lo nasconde. Il testo del passo 13 («I will stay here») fa pensare che sia voluto. Lo
  lascio a Daniel.
- **Larghezza minima del fumetto**: `minimumSizeHint` del pannello (314) supera `BUBBLE_MIN` (280). Un fumetto
  impostato a 280 (da configurazione) salta a 314 al primo trascinamento. Effetto piccolo, non corretto.
- **Visita interrotta chiudendo la finestra al primo avvio**: `tour_status` resta «active». Al riavvio si apre File >
  Apri (lista vuota) senza ripropostare la visita. È coerente con la regola «prima volta Nuovo», ma per chi non ha
  ancora nessun progetto si potrebbe preferire Nuovo. Scelta di Daniel.

## 4. Modifiche richieste a file non miei

1. `src/meridiana/ui/assistant_chat.py`, `open_project` (circa riga 164): sostituire
   `self.win.open_path(target)` + `return self.win.path == target` con `return self.win.open_path(target)`.
2. `src/meridiana/ui/file_page.py`, `_open_recent` (circa riga 501): dopo `self.close_page()` scrivere
   `if not self.host.open_path(Path(path)): self.host.open_file_page("open")`.
3. A/Claude: scheda di configurazione nel pannello agganciato basso e condizione di `show_setup` (vedi 3, primo
   punto). Poi rieseguire `tests.finestra.test_assistant_window`.
4. Template Qt: la correzione di `spotlight.py` di D (geometria intersecata con la finestra, anello attorno a
   `target_rect`) va riportata nel template. Ho aggiunto la prova `test_ring_hugs_the_target_at_all_four_window_edges`
   da portare insieme. Le mie correzioni ad `assistant.py` e `tour.py` riguardano solo Meridiana.

## 5. msgid nuovi o cambiati

Nessun msgid nuovo o cambiato da me. Ho controllato che quelli del lotto D siano in `po/it.po`: «Let us start
designing» → «Iniziamo a progettare», «Start» → «Inizia», i due testi «Now it is time to start designing...» e
«Meridio: guided tour».

## 6. Prove eseguite

Ambiente come da REGOLE-AGENTI (Git Bash, offscreen, PATH PySide6).

- `python -m unittest tests.nucleo.test_startup_r07 tests.nucleo.test_support_tour tests.nucleo.test_navigation_help
  tests.widget.test_spotlight tests.widget.test_assistant_widget tests.widget.test_assistant_presentation
  tests.finestra.test_support_flow tests.finestra.test_assistant_window tests.finestra.test_assistant_chat`
  → 88 prove, 2 rosse, entrambe descritte in 3 (`test_ctrl_l...` per la scheda di A, `test_a_model_that_reasons...`
  verde da sola). Log: `build/claude-r07/D-foto/D-test-R01.log`.
- `test_sixty_frames_cost_less_than_a_millisecond...` è caduta una volta sotto carico (1,28 ms). Da sola e nel modulo
  intero è verde (20/20). Soglia non toccata.
- Ruff `--select F,E9,B` su tutti i miei file e test: verde. Nessun U+2014.
- `build/overnight-r07/d-verify.py`: rifatto girare su una copia in `build/claude-r07/D-foto/` per non sovrascrivere
  le foto di D. L'ultima asserzione («AutoCAD» nel testo) fallisce perché il testo appare a macchina (motion non
  ridotto sull'assistente). È un limite dello script: il messaggio c'è in `assistant.messages`. Le foto mostravano i
  difetti D2 (testo tagliato).
- Nuovo `build/claude-r07/D-foto/D-verify-R01.py`, che guida la visita con i suoi pulsanti dall'invito a «Start» e
  controlla:
  - fumetto dentro la finestra a ogni passo e testo intero;
  - anello dello spotlight dentro la finestra;
  - stato finale: File > Nuovo, guard tolto, conversazione e cronologia di nuovo nel fumetto, aperto/chiuso come
    prima;
  - Meridio nei quattro angoli con la maniglia dentro il fumetto;
  - comando «Come mi muovo in 3D?».

  Eseguito a QT_SCALE_FACTOR 1, 2 e 2,5, prima e dopo D6: 252 controlli OK, 0 problemi
  (`D-verify-R01.log`, `D-verify-R02.log`).
- Foto controllate a occhio:
  - `D-tour-model-x2_5.png`: testo intero, anello sulla linguetta «Model» visibile anche in alto;
  - `D-tour-settings-x2.png`: «...by asking Meridio.» intero;
  - `D-tour-start-x1.png`: passo 13 con «Start»;
  - `D-tour-end-x1.png`: File > Nuovo, messaggio nella barra di stato, fumetto chiuso come prima;
  - `D-corner-left-top-x1.png`: maniglia in basso a destra, titolo centrato, ruoli «You» a destra e «Meridio» a
    sinistra distinti;
  - `D-conversation-x1.png` della prima corsa: le sovrapposizioni D6 (rigenerata dopo la correzione).

## 7. Limiti e cose non verificate

- Solo offscreen. Nessuna prova su finestra vera Windows o Linux, nessun trascinamento con puntatore fisico. La DPR è
  simulata con QT_SCALE_FACTOR.
- Temi chiaro/scuro: le foto sono nel tema predefinito, il tema scuro non è stato fotografato.
- `explicit_project` su Windows con l'eseguibile PyInstaller: dedotto dal codice di Qt (`arguments()` ricostruisce la
  riga di comando Unicode e conserva il filtro). Non provato sul pacchetto.
- Istanza unica e recupero con due processi: dedotto dalla lettura, non riprodotto.
- `navigation_help.py` (A) non rivisto a fondo: ho solo verificato che il comando offline risponda con il profilo
  reale («Your navigation profile: AutoCAD ...», tasto F letto dalle scorciatoie).
