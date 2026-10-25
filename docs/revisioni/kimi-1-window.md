# Revisione Kimi 1: spezzare `ui/window.py`

Data: 25/10/2026. Ramo: `kimi-revisione`.

## Scopo e metodo

Ho letto per intero `src/meridiana/ui/window.py`, `session.py`, `jobs.py`, i punti di ingresso di `app.py` e
`selftest.py`, gli adattatori di `assistant_chat.py`, `file_page.py`, `plant_page.py`, `variants.py` e le prove di
`tests/finestra/test_window.py` e `tests/_setup.py`. Ho cercato tutti gli import di `ui.window` e gli accessi a
`win` nelle prove.

[V] Un'analisi AST del sorgente, senza eseguire la finestra, dà questi numeri:

- `window.py`: 4.652 righe;
- `MainWindow`: 4.435 righe, dalla riga 218 alla 4.652, con 274 metodi;
- `MainWindow.__init__`: 355 righe; `_actions`: 331; `_build_phases`: 39;
- nelle prove: 1.646 accessi ad attributi di `win` o `self.win`, su 182 nomi distinti;
- 276 accessi a 69 nomi privati distinti; `_select` ne ha 60, `_edited` 35, `_compute_energy` 11;
- due patch sostituiscono `meridiana.ui.window.CatalogDialog`; altre prove patchano metodi privati della classe.

[I] Le dimensioni dei passi proposti sotto sono stime delle righe spostate, non preventivi di durata. Servono a
tenere ogni revisione piccola e leggibile, non a fissare un obiettivo numerico arbitrario.

Questo rapporto non propone cambiamenti a calcoli, regole, soglie, testi visibili o comportamento del programma.

## Osservazioni, dalla più grave

### 1. `MainWindow` concentra responsabilità indipendenti e rende ogni modifica trasversale

- **File e righe**: `src/meridiana/ui/window.py:218-4652`; costruzione a `:231-585`; azioni a `:689-1019`;
  sessione a `:1880-1929`; relazione a `:1277-1367` e `:3338-3437`; impianto e stringhe a `:3439-4050`;
  importazioni a `:4075-4302`; file e recupero a `:4306-4489`.
- **Che cosa succede**: la stessa classe possiede widget, comandi, lavori Qt, anteprime, importazioni, esportazioni,
  adattatori fra gesti e `ProjectSession`, aggiornamenti delle viste e stato temporaneo delle stringhe. Per esempio,
  una modifica alla chiusura di una stringa tocca `_draft_finished` (`:3906-3945`), ma quel metodo dipende da
  `_runs`, `_strings_put`, `_show_chosen`, `_delete_string`, `_choose_string`, dallo stato della pianta e dalla
  generazione dell'impianto. Il revisore deve ricostruire una parte grande della finestra per valutare un gesto
  circoscritto.
- **Scenario concreto**: mentre si corregge la conferma di una stringa con Invio, un cambiamento apparentemente
  locale può alterare la stringa scelta, i conteggi delle verifiche, l'annulla e il disegno della pianta. Non c'è
  un confine di modulo che dica quale di questi effetti appartiene alla stringatura e quale alla finestra.
- **Gravità**: alta. Non è un difetto funzionale dimostrato, ma moltiplica il rischio di regressioni e il costo
  delle revisioni.
- **Prova**: [V] conteggio AST e lettura delle dipendenze dei metodi. [V] `test_window.py:1512-1771` attraversa
  tutti questi effetti nello stesso viaggio di stringatura.
- **Correzione proposta**: estrarre per responsabilità, con classi piccole e dipendenze esplicite, nel piano sotto.
  Mantenere `MainWindow` come guscio Qt e facciata di compatibilità durante tutta la migrazione. Non riscrivere e
  non introdurre un altro oggetto onnicomprensivo chiamato `AppContext`.
- **Rischio della correzione**: medio. Spostare insieme troppe responsabilità renderebbe il diff illeggibile;
  lasciare per sempre tutti gli inoltri conserverebbe accoppiamento. Per questo ogni componente va introdotto solo,
  con una facciata temporanea e una revisione finale dei contratti pubblici.

### 2. L'ordine di costruzione e alcune chiamate sincrone sono un contratto nascosto

- **File e righe**: `src/meridiana/ui/window.py:231-585`, in particolare `_actions()` a `:520`,
  `_build_phases()` a `:541`, `_theme_changed()` a `:550`, `_restore_window()` a `:571`, `_show_all()` a `:577`
  e `Chat(...)` a `:580`; `_plant_soon()` e `_start_plant()` a `:3489-3508`; `_plant_done()` a `:3514-3535`.
- **Che cosa succede**: la costruzione non è soltanto una lista di widget. `_actions` presuppone fasi, pannelli e
  viste già presenti; `_build_phases` aggiunge impianto e relazione; `_theme_changed` li raggiunge tutti;
  `_show_all` può avviare l'impianto. Se pvlib è già caricato, `_plant_soon` chiama `_start_plant(now=True)`, che
  esegue `job.run()` sul filo della finestra. Il segnale arriva quindi sincrono a `_plant_done`, che aggiorna
  pianta, ispettore, comandi e verifiche prima che `_show_all` sia terminato.
- **Scenario concreto**: all'apertura di un progetto, con pvlib già importato da un calcolo precedente, spostare la
  costruzione di `checks_page` o `plant_page` più in basso farebbe arrivare `_plant_done` quando quegli attributi
  non esistono ancora. Il risultato atteso sarebbe un `AttributeError` o una vista inizializzata due volte.
- **Gravità**: alta durante il refactor, perché un diff che sembra solo spostare codice può impedire l'avvio.
- **Prova**: [V] catena di chiamate letta nel sorgente. [I] l'`AttributeError` è la conseguenza dedotta di uno
  specifico riordino, non un guasto osservato nel programma attuale.
- **Correzione proposta**: conservare invariata la sequenza di `__init__` in ogni passo. Documentare nel costruttore
  i quattro traguardi: viste e pagine base, azioni, fasi complete, ripristino e primo aggiornamento. I nuovi
  componenti vanno creati nello stesso punto in cui oggi vengono chiamati i metodi estratti. I segnali devono
  mantenere gli stessi ricevitori e lo stesso carattere sincrono o accodato.
- **Rischio della correzione**: alto se si estrae `__init__` in blocco; basso se si estraggono prima foglie e
  controller e si lascia il guscio per ultimo. Non consiglio un metodo `_build_everything()` ulteriore.

### 3. Le prove e gli altri moduli usano la finestra come API, compresi i nomi privati

- **File e righe**: `tests/_setup.py:250-307`; `tests/finestra/test_window.py:1424-1425`, `:1943-1953`,
  `:2007-2008`; `src/meridiana/ui/assistant_chat.py:105-173`; `src/meridiana/ui/file_page.py:209-218` e
  `:356-386`; `src/meridiana/app.py:81-89`; `src/meridiana/ui/selftest.py:231-295`.
- **Che cosa succede**: le prove leggono e scrivono 182 attributi della finestra e chiamano 69 nomi privati.
  `WindowHost` chiama `_rules_facts`, `_navigate`, `_fix` e `_preferences`. Le patch sostituiscono simboli nel
  modulo `ui.window`, non nel componente che verrà estratto.
- **Scenario concreto**: spostare `_edited` in `ModelEditingController` ed eliminare subito `win._edited` rompe 35
  accessi nelle prove prima ancora di verificare il comportamento. Spostare l'import di `CatalogDialog` senza un
  re-export fa fallire le patch di `test_window.py`, anche se il catalogo funziona ancora.
- **Gravità**: alta per la fattibilità del piano. Un refactor presentato come “senza cambiamenti” diventerebbe una
  riscrittura simultanea di codice e prove, molto più difficile da validare.
- **Prova**: [V] scansione AST di tutti i file `tests/**/*.py`; [V] ricerca degli import e delle patch. I conteggi
  sono quelli della sezione «Scopo e metodo».
- **Correzione proposta**: durante la migrazione lasciare su `MainWindow` metodi e proprietà che inoltrano ai nuovi
  componenti, con stesso nome e firma. Conservare i re-export richiesti dalle patch. Non riscrivere in massa le
  prove nello stesso commit dello spostamento. Dopo, e solo come lavoro separato, portare le prove verso gesti e
  contratti pubblici invece che verso un altro interno.
- **Rischio della correzione**: basso per il comportamento, medio per il debito temporaneo. Serve un inventario
  degli inoltri e una decisione esplicita di Daniel prima di eliminarli.

### 4. `_session_changed` e `_show_all` hanno sequenze diverse che non vanno fuse

- **File e righe**: `src/meridiana/ui/window.py:1880-1929` e `:2561-2581`; propagazione in
  `src/meridiana/session.py:244-250`, `:262-278`, `:319-329` e `:350-356`.
- **Che cosa succede**: `_session_changed` aggiorna soltanto le viste interessate dai topic. `_show_all`, usato
  all'apertura, alla creazione, al recupero e dopo alcune importazioni, prepara invece tutta la finestra in un
  ordine esplicito. Il ritorno di una posa chiama `session.layout_done`, che emette nuovi topic mentre
  `_layout_done` è ancora in esecuzione; poi `_layout_done` decide se avviare l'anno.
- **Scenario concreto**: aprire un file non è equivalente a cambiare il nome di un edificio. Un'unica funzione
  `refresh_everything()` usata per entrambi riporterebbe ricalcoli e ridisegni dove i topic li avevano eliminati.
  Al contrario, distribuire `_show_all` fra componenti senza conservare l'ordine può mostrare l'ispettore prima
  dell'impianto o lasciare la pianta non inquadrata.
- **Gravità**: media. Il pericolo è una regressione di comportamento e fluidità durante una semplificazione
  apparentemente innocua.
- **Prova**: [V] confronto dei due metodi e di `ProjectSession.changed`; [V] le prove di selettività sono in
  `tests/finestra/test_speed.py` e i viaggi di apertura in `test_window.py`.
- **Correzione proposta**: tenere inizialmente `_session_changed` come smistatore sottile nel guscio. Esso chiamerà
  i metodi pubblici dei controller, senza cambiare condizioni né ordine. Mantenere `_show_all` come sequenza distinta
  finché tutti i componenti non sono stabili; solo alla fine valutare un `SessionPresenter` per topic, con le stesse
  prove di selettività. Non introdurre un nuovo bus di eventi globale.
- **Rischio della correzione**: medio, soprattutto per rientranza e lavori ripetuti. Ogni passo va verificato anche
  su rinomina, modifica geometrica, ritorno della posa, ritorno dell'anno e cambio di variante.

### 5. Alcuni confini fra componenti usano membri privati delle viste

- **File e righe**: `src/meridiana/ui/window.py:2163`, `:2734`, `:3149` e `:3162` chiamano `PlanView._pick`;
  `:3157` legge `View3D.backend._press`; `src/meridiana/ui/assistant_chat.py:147-173` chiama metodi privati della
  finestra.
- **Che cosa succede**: la selezione dal 3D, il menu contestuale e Meridio non dipendono da contratti pubblici
  stabili, ma da dettagli interni di pianta, backend e finestra.
- **Scenario concreto**: se il nuovo presentatore 3D cambia il modo in cui conserva il risultato del pick, il menu
  contestuale può aprirsi sull'oggetto sbagliato o su nessun oggetto. Se una correzione sposta `_navigate`, gli
  strumenti di Meridio smettono di portare l'utente alla fase richiesta.
- **Gravità**: media. Non richiede una riscrittura delle viste, ma va chiuso prima di usarle come dipendenze dei
  nuovi controller.
- **Prova**: [V] ricerca dei simboli e lettura dei chiamanti. Non ho modificato né eseguito questi percorsi per il
  presente rapporto.
- **Correzione proposta**: aggiungere piccoli metodi pubblici che delegano il comportamento attuale, per esempio
  `PlanView.pick_at(scene_point)` e un accessor per il pick premuto del backend. Far usare quelli alla finestra,
  lasciando i vecchi membri per compatibilità. In un passo successivo, cambiare solo l'interno di `WindowHost`:
  stessa interfaccia verso `assistant/tools.py`, ma chiamate pubbliche verso i controller.
- **Rischio della correzione**: basso se gli adattatori sono puri inoltri e hanno prove su coordinate, modulo e
  oggetto selezionato. Non cambiare algoritmi di pick in questo lavoro.

## Parti da estrarre e loro interfacce

Le interfacce sotto sono volutamente piccole. «Host» non deve diventare un dizionario universale: i costruttori
ricevono gli oggetti che usano e poche callback nominate. I widget restano creati e posseduti sul filo principale;
i lavori ricevono copie e restituiscono dati, non widget.

| Componente proposto | Che cosa contiene | Confine pubblico |
|---|---|---|
| `ui/workers.py` | `LayoutJob`, `EnergyJob`, `PlantJob`, `ExportIfcJob`, segnali e `_pvlib_loaded` | Stessi costruttori e segnali; nessun import di `MainWindow` |
| `ui/actions.py` | Costruzione di azioni, menu, gruppi, scorciatoie e descrizioni; assemblaggio delle barre in un passo distinto | `build_actions(host)` e `build_phase_bars(host)`, con risultati espliciti; `QAction` ancora figlie della finestra |
| `ui/project_files.py` | Nuovo, apri, salva, revisioni, recupero, configurazione e stato della finestra solo dove non è override Qt | Metodi `new/open_path/save/save_as/offer_recovery`; callback `keep_or_discard`, `refresh`, `select`, `tell` |
| `ui/scene_presenter.py` | Preparazione mesh e tabelle 3D, indice dei moduli, selezione e contorni, inquadramento 2D/3D | `refresh()`, `refresh_outline()`, `fit()`, `frame()`, `module_at()`; dati in ingresso da sessione, nessun calcolo energetico |
| `ui/model_editing.py` | Disegno e modifica degli oggetti, proprietà, sposta/ruota, eliminazione, menu degli oggetti | Metodi per gesti già esistenti; `session.edit()` unico canale; callback `select`, `tell`, `show_phase` |
| `ui/manual_layout.py` | File e moduli manuali, anteprime, cache della fila, cambio modulo | `row_preview`, `row_info`, comandi delle righe; algoritmi ancora in `manual.py` |
| `ui/energy_controller.py` | Timer e lavoro dell'anno, cancellazione, arrivo dei risultati, aggiornamento delle tre pagine | `compute(fetch)`, `cancel()`, `pending()`, `show_forms()`; generazioni ancora in `ProjectSession` |
| `ui/checks_controller.py` | Raccolta già offerta da `checks.py`, segni, navigazione, anteprima delle correzioni | `refresh()`, `show_marks()`, `fix(item)`, `answer(keep)`; nessuna soglia o regola spostata |
| `ui/plant_controller.py` | Lavoro dell'impianto, stato live, inverter e ottimizzatori, condizioni dell'ultimo anno | `refresh_soon()`, `pending()`, `state`, comandi inverter; esiti verso stringhe e verifiche in ordine attuale |
| `ui/stringing_controller.py` | Bozza, scelta, menu e modifiche delle stringhe | Metodi per gesti della pianta e dell'elenco; stato `chosen_string` e `draft_target`; modifiche solo con `session.edit` |
| `ui/report_controller.py` | Dati, profili, anteprima incrementale, PDF, CSV e stato degli elaborati | `refresh()`, `preview()`, `export_pdf()`, `export_csv()`, `cancel()`; generatori sempre sul filo principale |
| `ui/transfer_controller.py` | PVsyst, IFC, curve; processi e lavori di importazione/esportazione | Metodi già esposti dai comandi; `IfcReading` e `QProcess` solo sul filo principale |

### Componenti che non estrarrei

- **Assistente**: `ui/assistant.py`, `ui/assistant_chat.py`, `ui/voice.py` sono già componenti. Le poche funzioni
  `_assistant_*` di `window.py` sono il suo adattatore alla disposizione della finestra. Un ulteriore
  `AssistantManager` aggiungerebbe solo un livello. Va invece ristretto `WindowHost`, come detto nell'osservazione 5.
- **Pianta e vista 3D come widget**: `PlanView` e `View3D` restano dove sono. Si estrae soltanto la preparazione e
  il coordinamento dei loro dati. Il prestito della pianta fra Modello e Impianto (`_lend_plan` e `_return_plan`,
  `window.py:2871-2900`) resta nel guscio per l'ordine fra genitori Qt, splitter e visibilità.
- **Tema, pannelli e disposizione adattiva**: restano nel guscio insieme a `showEvent`, `resizeEvent`, `closeEvent`,
  `childEvent`, `eventFilter` e `menuBar`, che sono override di `QMainWindow`.
- **Stato del progetto**: resta in `ProjectSession`. Le proprietà `project`, `results`, `energy`, `selection` e le
  altre di `window.py:218-229` restano disponibili durante tutto il piano. Non si sposta `session.edit` dentro Qt.

## Ordine dei passi

Ogni riga è un commit separato, solo dopo approvazione di Daniel. Prima del passo 1 occorre una base verde: su
Linux i due fallimenti già segnalati nel gruppo `finestra` vanno riprodotti e risolti con le correzioni approvate
del rapporto 5. Finché la base è rossa, si possono confrontare i risultati con la base ma non dichiarare onestamente
«suite intera verde».

| Passo | Contenuto e dimensione stimata [I] | Prove mirate, oltre alla suite completa |
|---|---|---|
| 0 | Base e contratti: inventario dei nomi inoltrati; nessuna riga di produzione spostata. Confermare import pigro e i due fallimenti noti | `StartUp.test_the_window_imports_without_pandas_matplotlib_and_pvlib`; tutti i gruppi uno per processo |
| 1 | `workers.py`: spostamento meccanico dei quattro job e dei segnali, circa 210 righe; re-export in `window.py` | Ritorno di posa, energia, impianto, IFC; chiusura durante lavori |
| 2 | Piccoli contratti pubblici di pick per pianta e backend, circa 40-80 righe più prove | Selezione 2D/3D e menu contestuali; nessuna variazione delle coordinate |
| 3 | `actions.py`: prima `_actions`, circa 330 righe, poi `_build_phases` in un commit distinto, circa 40 | Ogni comando, tasto e menu; `test_phase_bar`, `test_panels`; patch di `CatalogDialog` invariate |
| 4 | `project_files.py`: file, salvataggi e recupero, circa 250-300 righe con inoltri | Apertura danneggiata, salvataggio, disco che rifiuta, recupero, chiusura che chiede il salvataggio |
| 5 | `scene_presenter.py`: circa 180-230 righe | `test_selection_3d`, navigazione, attese; identità di `module_index` e tabelle conservate |
| 6 | `model_editing.py`: circa 350-450 righe | Viaggi di disegno, modifica, sposta/ruota, annulla, proprietà |
| 7 | `manual_layout.py`: circa 350-400 righe | Tutti i viaggi `RowsByHand`; anteprima e cambio modulo |
| 8 | `energy_controller.py`: circa 170-220 righe | Calcolo, cancellazione PVGIS, generazione vecchia, valori stantii, pagine nascoste |
| 9 | `checks_controller.py`: circa 250-320 righe | Segni, filtri, navigazione, anteprima «Tieni/Annulla», Meridio |
| 10 | `plant_controller.py`: circa 180-220 righe | Impianto, inverter, ottimizzatori, ritorno sincrono e asincrono |
| 11 | `stringing_controller.py`: circa 400-470 righe | Tutti i viaggi `Stringing`, bozza durante annulla/cambio variante, menu |
| 12 | `report_controller.py`: circa 230-280 righe | Anteprima, annulla, allegati, CSV, stato elaborati; nessun import pesante anticipato |
| 13 | `transfer_controller.py`: circa 280-330 righe | PVsyst, IFC e curve; annulla lettura/esportazione; processo che termina dopo la finestra |
| 14 | Rientro finale: `_session_changed` solo come dispatcher, `WindowHost` su metodi pubblici, import inutili tolti | `test_speed`, `test_assistant_chat`, avvio, tutti i viaggi |
| 15 | Revisione degli inoltri: nessuna eliminazione automatica; elenco dei contratti da mantenere e proposta separata per le prove | Suite completa e rapporto a Daniel prima di qualunque rimozione |

[I] Alla fine `MainWindow` dovrebbe contenere soprattutto costruzione, proprietà Qt, facciata e smistamento. Non
fisserei un numero di righe come criterio di accettazione: il criterio è che una modifica di stringhe, relazione o
file non richieda più di aprire il guscio.

## Regole per mantenere ogni passo verde

1. **Prima spostare, poi semplificare.** Il primo commit di un componente riproduce condizioni e ordine attuali.
   Dedupliche, nuovi nomi pubblici e miglioramenti delle prestazioni sono commit successivi e richiedono anch'essi
   approvazione.
2. **Prove invariate durante lo spostamento.** Gli inoltri mantengono `win.*` e i re-export. Le nuove prove coprono
   soltanto il contratto pubblico aggiunto o un confine prima non osservabile. Non si cambia un'asserzione per
   adattarla al refactor.
3. **Import pigri.** `report`, grafici, pandas, matplotlib e pvlib non devono comparire fra gli import iniziali dei
   nuovi moduli se oggi sono caricati tardi. La prova del processo nuovo deve continuare a stampare `[]`.
4. **Stessa affinità Qt.** Timer e `QObject` dei controller hanno la finestra come genitore. I `QRunnable` non
   leggono né scrivono widget, sessione o viste; lavorano su snapshot e risultati come oggi.
5. **Stessi segnali.** Firme e ricevitori restano invariati. Le lambda che oggi dipendono dalla finestra non vanno
   trasferite senza un contesto Qt. Il caso sincrono di `PlantJob.run()` va provato esplicitamente.
6. **Stessa chiusura.** Ogni componente che possiede generatori, processi, timer o lavori deve essere raggiunto da
   `closeEvent` nello stesso ordine di oggi. Le questioni di durata specifiche sono nel rapporto 2.
7. **Verifica completa a ogni commit:** `python -m ruff check src tests tools`, poi i gruppi `nucleo`, `calcoli`,
   `formati`, `esterni`, `widget`, `finestra`, ciascuno in un processo e con `QT_QPA_PLATFORM=offscreen`. Il gruppo
   `esterni` va incluso secondo le sue condizioni di salto, senza attivare misure o risorse esterne non richieste.
8. **Nessuna misura di fluidità offscreen.** I passi 3, 5, 8, 9 e 14 possono cambiare import, numero di chiamate e
   ordine dei ridisegni. Dopo quei passi Claude deve ripetere `tools/fluidity.py` sullo schermo vero. Offscreen la
   vista 3D non viene disegnata: le prove possono verificare dati e segnali, non resa o fluidità del 3D.

## Raccomandazione

Consiglio di approvare il piano per passi 1-14, non una riscrittura unica. I primi tre passi sono i più sicuri e
preparano il resto. I passi 8-11, energia, verifiche, impianto e stringhe, sono quelli che richiedono maggiore
attenzione alla rientranza e ai segnali. La facciata `MainWindow` non è un fallimento del piano: è ciò che permette
di dimostrare, a ogni commit, che il comportamento non è cambiato.

Nessun file di codice è stato modificato per questo rapporto.
