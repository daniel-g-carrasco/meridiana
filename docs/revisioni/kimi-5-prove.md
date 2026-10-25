# Revisione Kimi 5: prove lente, fragili, doppioni e fallimenti Linux

Data: 25/10/2026. Ramo: `kimi-revisione`.

## Ambiente e risultato complessivo

Ho usato Python 3.14.9, PySide6 6.12, `QT_QPA_PLATFORM=offscreen`, `PYTHONPATH=src` della copia
`meridiana-kimi` e cartelle XDG temporanee. Ogni gruppo è stato eseguito in un processo separato. Un runner con
`TextTestResult` ha registrato il tempo di ogni test. Non ho aperto la finestra sullo schermo e non ho misurato
fluidità o aspetto.

`ruff check src tests tools`: **tutto verde**. Prima del gruppo `finestra` ho dovuto eseguire anche
`python tools/compile_po.py`, previsto dalle regole del progetto: senza il catalogo compilato, il self-test fallisce.

| Gruppo | Prove eseguite | Fallimenti | Saltate |
|---|---:|---:|---:|
| `nucleo` | 780 | 0 | 4 |
| `calcoli` | 174 | 0 | 0 |
| `formati` | 58 | 0 | 0 |
| `esterni` | 6 | 0 | 6 |
| `widget` | 276 | 3 | 0 |
| `finestra` | 118 | 3 | 0 |
| **Totale** | **1.412** | **6** | **10** |

Il totale è coerente con le 1.411 prove segnalate su Windows più la prova specifica del portale Linux
(`widget/test_system_accent.py`). I sei fallimenti sono stati rieseguiti e analizzati. Uno, il self-test, è passato
dopo la compilazione del catalogo. Gli altri cinque comprendono i due casi segnalati da Daniel, due prove voce con
la stessa dipendenza e il renderer 3D. La prova dell'accento è intermittente: è fallita nella corsa completa e poi
è passata isolata e nel modulo intero.

Offscreen la vista 3D ordinaria non viene disegnata. Per questo non deduco conclusioni sulla resa 3D reale dai test
della finestra. Il caso `report_3d`, che usa `QT_QUICK_BACKEND=rhi`, è trattato a parte: qui il renderer dichiara
un dispositivo ma non costruisce la pipeline, quindi non è una prova valida dei contenuti.

## I due fallimenti segnalati, causa e correzione

### 1. `test_ctrl_l_the_size_of_the_bubble`: una scheda nuova impedisce il pannello basso

- **File e righe**: `tests/finestra/test_assistant_window.py:165-177`; creazione della scheda in
  `src/meridiana/ui/assistant_chat.py:589-595`; contenuto del pannello in `src/meridiana/ui/assistant.py:462-490`;
  condizione di visibilità in `:883-885`.
- **Che cosa succede**: dopo la risposta, Meridio mostra la scheda «No local model on this PC». Essa aggiunge 87 px
  al contenuto. Prima di toglierla, `panel.minimumSizeHint()` è 296 x 305 e il dock chiede 350 px: la chiamata
  `resizeDocks(..., QUESTIONS_HEIGHT // 2)`, cioè 130, non può scendere sotto il minimo. Il test si attende invece
  meno di 260 px.
- **Scenario concreto**: la risposta locale senza modello crea la scheda. Poi Proprietà e Verifiche vengono
  riaperte e il dock viene ridotto. La condizione `event.size().height() >= 260` resta vera perché il pannello è 305,
  quindi le domande restano visibili.
- **Gravità**: media. Il test non raggiunge lo scenario che vuole verificare. Non è un difetto del meccanismo di
  nascondere le domande.
- **Prova**: [V] il test fallisce con `305 not less than 260`, anche isolato. [V] rimuovendo prima la scheda con
  `win.assistant_chat._drop_survey()`, il minimo scende a 212, il pannello effettivo è 212 e l'intero test passa.
- **Correzione proposta**: prima del ridimensionamento, eliminare la scheda del modello locale con
  `win.assistant_chat._drop_survey()`. È contenuto estraneo allo scopo del test, introdotto dopo la sua scrittura.
  Non cambiare `QUESTIONS_HEIGHT` e non allargare l'attesa a 305 per nascondere il problema.
- **Rischio della correzione**: basso. Si cambia soltanto il contesto del test, non il comportamento del programma.
  Se in futuro si vorrà un pannello che ammette anche schede lunghe, servirà invece una soluzione con scorrimento,
  da decidere come cambiamento di prodotto separato.

### 2. `test_the_accent...`: l'anello del focus è scambiato per accento fuori posto

- **File e righe**: `tests/finestra/test_design_system.py:328-358`; il bordo previsto per i campi attivi è in
  `src/meridiana/ui/theme.py:274-282`.
- **Che cosa succede**: il test permette l'accento sulle viste, sulla linguetta della fase e sui pulsanti primari o
  con focus, ma non sul campo attivo. Il tema disegna invece correttamente un bordo di 2 px con l'accento anche
  attorno a `QLineEdit`, spin box, combo e campi data.
- **Scenario concreto**: un `QuantityField` delle Proprietà ha il focus quando viene fatta la fotografia. I suoi
  pixel di bordo rientrano nella tolleranza del colore dell'accento, ma il rettangolo del campo non è fra quelli
  consentiti. Il test li chiama «stray».
- **Gravità**: media, perché il test può fallire a seconda di quale campo abbia il focus e quindi dell'ordine e dei
  tempi delle prove precedenti.
- **Prova**: [V] nella corsa completa il test fallisce; isolato e con tutto `test_design_system` passa. [V] forzando
  il focus su un campo, la versione attuale trova 62 punti fuori dai rettangoli consentiti. [V] aggiungendo soltanto
  il rettangolo del widget attivo, gli stessi punti diventano zero. Non ho cambiato il programma.
- **Correzione proposta**: aggiungere a `allowed` il rettangolo di `QApplication.focusWidget()` quando esiste ed è
  diverso da `win`, con lo stesso margine di 2 px usato per i pulsanti. Non consentire l'intera finestra e non
  togliere il bordo dal tema.
- **Rischio della correzione**: basso. Continua a rilevare accenti fuori posto, ma riconosce l'uso legittimo del
  focus previsto da R104.

## Altri fallimenti trovati nella stessa revisione

### 3. Due prove voce dipendono dal modello installato nella home reale

- **File e righe**: `tests/widget/test_voice.py:70-76` e `:101-125`;
  `tests/finestra/test_assistant_chat.py:415-422`; ricerca del modello in
  `src/meridiana/assistant/speech.py:50-69` e disponibilità in `src/meridiana/ui/voice.py:228-250`.
- **Che cosa succede**: `find_model` guarda anche `~/.local/opt/kokoro` e `~/.local/share/kokoro`, dove il modello è
  presente su questo portatile. `natural_model()` lo accetta e `sys.executable` fornisce un interprete, quindi il
  programma considera disponibile Kokoro anche quando `engines()` è simulato vuoto.
- **Scenario concreto**: `test_no_engine_at_all...` si attende `available() == False`, ma ottiene `True`.
  `test_the_frames...` si attende che una cartella vuota non contenga il modello, ma trova quello della home.
  `Spoken.test_without_an_engine...` si attende il pulsante spento e lo trova attivo.
- **Gravità**: media. Le attese dipendono dal PC, non dal comportamento richiesto dal test.
- **Prova**: [V] i tre test falliscono qui. [V] con una home temporanea e `natural_model = None`, tutti passano.
  Non è necessario leggere il contenuto del modello per dimostrare la dipendenza.
- **Correzione proposta**: isolare `Path.home()` su una cartella temporanea e, per i test «nessun motore», simulare
  anche `Voice.natural_model()` che restituisce `None`, non soltanto `voice.engines()`. Per `find_model`, la home
  temporanea basta e mantiene la prova dei percorsi configurati e della cartella dati.
- **Rischio della correzione**: basso. Non modifica la scoperta reale di Kokoro, solo i confini del test.

### 4. `report_3d`: RHI esiste, ma la pipeline grafica non funziona

- **File e righe**: `tests/widget/test_report_3d.py:54-82`; creazione e controllo del renderer in
  `src/meridiana/ui/report_3d.py:51-68` e `:125-151`; immagine letta in `:93-109`.
- **Che cosa succede**: `renderer()` trova un RHI e `available()` restituisce vero. La creazione della pipeline
  fallisce per mancanza di codice GLSL compatibile, e le immagini prodotte sono completamente bianche. Il test cerca
  il navy dei moduli e fallisce con 0 pixel.
- **Scenario concreto**: con `QT_QUICK_BACKEND=rhi` e `QT_QPA_PLATFORM=offscreen`, il processo stampa
  `Failed to build graphics pipeline state` più volte, ma esce con codice 0 e salva due PNG bianchi.
- **Gravità**: media. Il test non può valutare la scena. Inoltre `available()` non garantisce che il risultato sia
  disegnato, quindi una relazione potrebbe includere immagini vuote su un sistema con la stessa limitazione.
- **Prova**: [V] entrambe le immagini sono bianche, lette con il visualizzatore; [V] il log contiene l'errore di
  pipeline; [V] il test fallisce con `0 not greater than 1485.0` per `south_east`. Non ho tratto conclusioni sulla
  GPU reale.
- **Correzione proposta**: nel test, saltare con motivo esplicito quando il log contiene `Failed to build graphics
  pipeline state`, invece di valutare i pixel. Separatamente consiglio una guardia di prodotto: se l'immagine è
  intera bianca (i byte sono tutti `0xff`), `render` restituisce `{}` e la relazione lascia fuori le figure anziché
  pubblicare rettangoli vuoti. Un test di capacità dovrebbe verificare una scena minima nota prima di dichiarare il
  renderer disponibile.
- **Rischio della correzione**: basso per il salto esplicito, medio per la guardia di prodotto. Un controllo bianco
  non deve eliminare una scena legittimamente bianca: va fatto solo quando la scena contiene moduli ed edifici,
  come già garantito dall'ingresso di `render`.

### 5. Il self-test richiede la compilazione del catalogo prima della suite

- **File e righe**: `src/meridiana/ui/selftest.py:120-126`; `tests/finestra/test_self_test.py:43-61`;
  `tools/compile_po.py:151-162`.
- **Che cosa succede**: il controllo chiede che la traduzione italiana esista davvero. Il checkout non aveva ancora
  `locale/it/LC_MESSAGES/meridiana.mo`, quindi `translation_for("it").gettext("Preferences")` restituiva l'inglese.
- **Scenario concreto**: il self-test esegue tutti i controlli ma esce con `FAIL catalogue it`. Dopo
  `python tools/compile_po.py`, lo stesso test passa con `PASS all: 0 failed`.
- **Gravità**: bassa. È un prerequisito della suite, non un difetto dell'applicazione o del catalogo sorgente.
- **Prova**: [V] fallimento iniziale e successo dopo compilazione. [V] `po/it.po` passa anche `msgfmt --check`.
- **Correzione proposta**: mantenere `python tools/compile_po.py` prima della suite e nei compiti che preparano il
  clone. Non cambiare il self-test per accettare l'inglese.
- **Rischio della correzione**: nessuno, è il passaggio già documentato in `CLAUDE.md`.

## Le 20 prove più lente

[V] Misure da un'esecuzione completa di `finestra`, 234,589 s complessivi. Le prime 20 sommano 98,042 s, il 41,8 %
del gruppo. Sono tutte in `finestra`; la prima prova di `widget` è successiva nella classifica.

| Secondi | Prova |
|---:|---|
| 10,407 | `finestra.test_self_test.Run.test_the_self_test_passes_and_leaves_nothing_in_the_users_folders` |
| 8,550 | `finestra.test_theme.ThemeOfTheWindow.test_a_change_of_theme_leaves_no_old_colour_and_the_views_keep_their_own` |
| 8,338 | `finestra.test_phase_bar.ReportAndPlant.test_the_report_phase_shows_its_pages_and_its_choices_are_edits_undone_with_ctrl_z` |
| 7,345 | `finestra.test_waits.Bars.test_the_report_shows_its_bar_page_by_page_and_cancel_leaves_nothing` |
| 6,314 | `finestra.test_theme.ThemeOfTheWindow.test_the_preview_changes_at_once_and_the_window_when_the_choice_settles` |
| 5,582 | `finestra.test_window.EnergyPages.test_the_pages_draw_only_what_is_on_screen_the_year_the_consumption_the_economics_and_their_edits` |
| 4,994 | `finestra.test_speed.Speed.test_a_rename_moves_nothing_and_costs_little_and_a_height_lays_again_only_the_sub_fields_it_touches` |
| 4,544 | `finestra.test_theme.ThemeOfTheWindow.test_the_sheet_goes_on_the_whole_window_quickly_and_it_draws_in_both_themes_with_the_screenshots_kept` |
| 4,324 | `finestra.test_window.Stringing.test_another_string_refused_moved_drawn_again_the_list_and_an_older_proposal` |
| 4,230 | `finestra.test_waits.Bars.test_pvgis_moves_the_bar_step_by_step_and_cancel_half_way_leaves_the_project_as_it_was` |
| 3,746 | `finestra.test_window.EnergyPages.test_the_variants_compared_and_the_strings_proposed_with_an_inverter_from_the_catalogue` |
| 3,705 | `finestra.test_waits.Arcs.test_the_arcs_of_the_plan_and_of_the_pages_past_the_threshold_with_the_words_in_the_status_bar` |
| 3,569 | `finestra.test_window.EnergyPages.test_the_checks_gather_the_project_lead_to_the_place_apply_a_fix_and_carry_the_rules` |
| 3,359 | `finestra.test_window.Stringing.test_nothing_comes_by_itself_and_a_string_is_drawn_numbered_taken_back_closed_and_given_up` |
| 3,341 | `finestra.test_assistant_chat.Cloud.test_no_network_the_question_goes_to_the_local_model_and_it_is_said` |
| 3,334 | `finestra.test_window.PlantPhase.test_the_plant_phase_lends_the_plan_production_leads_to_it_and_its_inverters_and_inputs` |
| 3,170 | `finestra.test_waits.StaleValues.test_the_values_are_greyed_while_the_project_has_changed_and_clean_with_the_new_year_or_an_undo` |
| 3,084 | `finestra.test_surfaces.Cards.test_every_panel_is_a_card_eight_pixels_from_the_window_and_its_neighbours_with_the_views_rounded` |
| 3,063 | `finestra.test_panels.Panels.test_the_icons_the_tree_the_right_panel_and_the_quick_measure_follow_the_theme_the_selection_and_the_tab` |
| 3,043 | `finestra.test_window.Window.test_the_layout_follows_each_change_only_where_it_touches_and_a_failure_is_marked` |

**Valutazione**: il costo dominante non è una duplicazione gratuita. Ci sono integrazione completa, calcoli veri,
relazioni PDF, pose e impianti che cambiano. I viaggi condividono già una finestra, quindi non proporrei tagli.
Per ridurre il tempo senza perdere copertura:

1. tenere il self-test come prova d'integrazione distinta, senza ripeterlo in altri gruppi;
2. misurare quali `again()` riaprono lo stesso progetto senza essere necessari al reset e togliere soltanto quelli
   dimostrabilmente superflui, uno alla volta;
3. non ripetere anteprime o calcoli quando il progetto non cambia, riusando la finestra del viaggio dove il test non
   verifica proprio quel ricalcolo;
4. non spostare i test di comportamento in `esterni`: solo le asserzioni sui millisecondi appartengono lì.

**Rischio della correzione**: medio. Unire o velocizzare test senza distinguere il reset necessario lascerebbe
stato condiviso e nuove dipendenze d'ordine.

## Fragilità da tempi, ordine e piattaforma

### 6. Soglie di prestazione nella suite normale

- **File e righe**: `tests/widget/test_assistant_widget.py:265-280` (media sotto 1 ms a fotogramma);
  `tests/nucleo/test_catalog.py:147-166` (0,2 e 0,4 s); `tests/widget/test_charts.py:109-125` (50 ms a `grab`);
  `tests/finestra/test_theme.py:111-114` (1 s); `tests/widget/test_assistant_local.py:51-61` (0,3 s);
  `tests/nucleo/test_skeleton.py:128-137` (50 ms); `tests/nucleo/test_assistant_answers.py:128-147` (1 s per Stop);
  `tests/widget/test_ifc_import.py:51-56` (10 s per l'arresto); `tests/widget/test_report_3d.py:63-65` (50 ms
  cache e confronto fra tempi); `tests/finestra/test_speed.py:16`, `:69-74` (400 ms per modifica).
- **Che cosa succede**: queste prove misurano il wall clock e dipendono dal carico, dalla CPU, dal renderer e dalla
  prima importazione. La prova del tema ha impiegato 0,989 s su un limite di 1 s: un altro carico minimo può farla
  fallire senza regressione funzionale. La documentazione del progetto registra già fallimenti del catalogo e dei
  fotogrammi di Meridio su una macchina occupata.
- **Scenario concreto**: mentre altre suite lavorano, `grab()` o la classificazione supera la soglia anche se i
  pixel e i risultati sono corretti. `test_report_3d` confronta inoltre due macchine di rendering diverse, quindi la
  durata dipende dalla compilazione degli shader.
- **Gravità**: media. Falsi rossi intermittenti che rendono difficile capire se un commit sia responsabile.
- **Prova**: [V] lettura delle soglie e dei tempi attuali; [V] `docs/progetto.md:306-307` documenta fallimenti di
  soli tempi sotto carico in precedenti esecuzioni. Non ho introdotto carico artificiale per riprodurli di nuovo.
- **Correzione proposta**: lasciare nelle suite normali le asserzioni strutturali (celle create, dati restituiti,
  pixel, risultati) e spostare le soglie temporali in `esterni`, attivate con `MERIDIANA_ESTERNI=1` su macchina non
  occupata. Misurare mediana e varianza, non imporre un singolo valore assoluto per tutte le piattaforme. Per Stop e
  processi, usare condizioni e timeout come limiti di sicurezza, non come obiettivo di prestazione.
- **Rischio della correzione**: basso per i falsi rossi, medio per la perdita di visibilità su regressioni reali di
  prestazione. I valori vanno conservati nelle misure di `docs/prestazioni`, non semplicemente eliminati.

### 7. Dipendenze da piattaforma e ordine già presenti ma gestite

- **File e righe**: `tests/_setup.py:31-47`, `:110-127`, `:158-184`, `:237-247`;
  `tests/widget/test_system_accent.py:21-39`; `tests/widget/test_report_3d.py:54-65`;
  `tests/widget/test_qt_words.py:20-47`.
- **Che cosa succede**: alcune prove richiedono Linux, il portale, traduzioni Qt o una pipeline RHI, altre richiedono
  il focus che non tutti i desktop concedono. I salti previsti sono corretti e non vanno trasformati in fallimenti.
- **Scenario concreto**: senza motore testo-voce la prova si salta con motivo; senza display o attivazione si salta
  la tastiera; senza catalogo compilato, invece, il self-test fallisce perché il prerequisito è obbligatorio.
- **Gravità**: bassa. L'architettura dei salti è per lo più corretta; il rischio è considerare ogni salto un
  successo completo della piattaforma.
- **Prova**: [V] sei test saltati in `esterni`, quattro in `nucleo`; [V] `keyboard_or_skip` dichiara il motivo
  invece di passare in silenzio.
- **Correzione proposta**: riportare nel riepilogo del CI conteggio e motivo dei salti, soprattutto RHI, voce e
  tastiera. Non saltare il controllo del catalogo italiano: compilarlo come da regole.
- **Rischio della correzione**: basso. Si evita soltanto di scambiare copertura mancante per esito verde.

## Doppioni

- **File e righe**: tutti i `tests/**/test_*.py`; l'unico nome ripetuto è
  `calcoli/test_economics.py:218` e `calcoli/test_energy.py:435`, entrambi `test_every_formula_can_be_drawn`, ma su
  dati e responsabilità diverse.
- **Che cosa succede**: non emergono corpi di prova identici. Anche allentando il confronto non si trovano coppie
  con almeno 12 righe e somiglianza AST ≥ 0,84. I viaggi richiamano gli stessi helper, ma verificano passi diversi.
- **Scenario concreto**: il nome ripetuto per le formule non è un doppione: economia e bilancio energetico hanno
  fixture e asserzioni differenti.
- **Gravità**: bassa. Non c'è una rimozione da consigliare.
- **Prova**: [V] confronto AST dei corpi, senza docstring, e confronto testuale normalizzato. Non è una prova
  assoluta che non esistano somiglianze semantiche, ma non ci sono doppioni letterali o quasi letterali.
- **Correzione proposta**: nessuna. Non accorciare i viaggi per ridurre il conteggio, perché coprono stati diversi.
- **Rischio della correzione**: nessuno; la scorciatoia sarebbe perdere copertura senza beneficio.

## Ordine consigliato

1. Correggere le attese dei test: scheda locale prima del pannello basso, rettangolo del campo attivo nell'accento,
   home e Kokoro isolati, salto RHI esplicito quando manca la pipeline.
2. Mantenere la compilazione del catalogo come prerequisito e poi rieseguire tutti i gruppi per avere una base verde.
3. Spostare le soglie di millisecondi in `esterni` e conservare le misure sulle macchine adatte.
4. Solo dopo, valutare i tempi delle prove più lente senza eliminare test o creare nuove dipendenze.

Le correzioni dei punti 1-3 possono essere commit separati. Prima di ognuno: prova rossa riprodotta, prova verde
dopo, `ruff`, suite completa. La guardia contro immagini bianche di `report_3d`, se approvata, va invece scritta
come modifica di prodotto con una prova specifica e revisione di Claude.

Nessun file di codice o di prova è stato modificato per questo rapporto.
