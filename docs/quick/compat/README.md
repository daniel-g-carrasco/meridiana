# Usare le prove di compatibilità nei rami Quick

Questa cartella collega i requisiti di Daniel, il programma Widgets e le prove
del nuovo frontend. Il registro è un elenco di lavoro: una riga censita, un
comando del nucleo riusato o una foto acquisita non dimostrano da soli la parità.

La matrice fotografica è ancora in corso. Per gli esiti aggiornati leggere
`docs/quick/stato/r12-compat.md` e il rapporto `docs/quick/compat-esito.md`, quando
presente. La presenza di un `manifest.json.gz` certifica soltanto il caso che
elenca, non tutti i temi, le scale, le misure o gli stati richiesti.

## Preparare l'ambiente

Eseguire dalla radice del proprio worktree, dopo aver letto
`docs/quick/CONTESTO.md`. Esempio per il ramo compat su Windows:

```powershell
Set-Location C:\Users\Grasso\dev\meridiana-wt-r12-compat
$quickPython = 'C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'tests;src;.'
```

Negli altri rami cambiare soltanto il worktree. La `.venv` condivisa è in sola
lettura. I dati delle prove vanno in `build/` del proprio ramo, con impostazioni
e cache isolate. Non usare i profili reali di Meridiana e non salvare sopra il
progetto Rho di Daniel o sopra le fixture congelate.

## Quale file aggiornare

| File | Contenuto e uso |
|---|---|
| `parita.json` | Elementi Widgets, sorgenti, fasi, stato Quick, prove e differenze decise |
| `richieste.csv` | Tutte le righe di `docs/richieste.md`, destinazione, applicabilità e piano Quick |
| `prove.csv` | Metodi di `tests/widget` e `tests/finestra`, comportamento, assert e sostituzione Quick prevista |
| `scenarios.json` | Percorsi differenziali dichiarati, con comandi, argomenti e osservazioni |
| `differenze.json` | Eccezioni geometriche precise e motivate, usate dal comparatore |
| `riferimento/<run>/<caso>/` | Metadati Widgets compressi e manifest delle acquisizioni |
| `prove-native.md` | Contratto dei fotogrammi, delle finestre inattese e del conteggio delle chiamate Python |
| `tools/quick_rif_evidence.py` | Esecuzione isolata dei metodi scelti e produzione dei rapporti `cases` richiesti dal registro |

I riferimenti nei JSON e CSV sono relativi alla radice del repository. Gli ID
sono le chiavi di collegamento: per esempio `command:save`,
`phase_command:plant/modules/fill` e il nome completo di un metodo di prova.

[V] L'inventario iniziale comprende 752 elementi, 400 righe di richieste e
1.196 metodi Widgets. Le 400 righe hanno 398 numeri distinti: R30 e R31 compaiono
due volte nella fonte. `row_id`, per esempio `R30/1` e `R30/2`, conserva le
occorrenze e i loro diversi stati storici. Non rinumerarle e non inventare R399
o R400 per raggiungere il totale.

[V] `explicit_source_references` e `explicit_source_controls` riportano dove
compare il numero R nei sorgenti. Un riferimento esplicito non significa che il
test copra integralmente quella richiesta. [I] Le destinazioni e i piani di
portabilità sono proposte: 184 destinazioni iniziali sono state riviste leggendo
richieste e seguiti, le altre derivano dalle parole del testo. Ogni riga dichiara
la base della mappatura. La portabilità dei 1.196 metodi resta da verificare.

`behavior`, `module_contract` e `assertions` conservano il contratto originale
dei test, anche in inglese. `quick_replacement` indica il test che lo sostituirà;
`quick_test` svolge lo stesso ruolo nel registro delle richieste. Questi campi
non attribuiscono automaticamente copertura.

## Controllare e rigenerare i registri

```powershell
& $quickPython tools/quick_rif_registry.py --check
& $quickPython -m unittest quick.parity.test_registry
```

Il controllo non apre finestre. Confronta l'inventario con i sorgenti attuali,
le righe delle richieste e i metodi Widgets; verifica anche comandi e scorciatoie
nei manifest disponibili. Segnala elementi nuovi o scomparsi, sorgenti cambiate,
prove mancanti e percentuali non aggiornate. Codice di uscita diverso da zero:
leggere gli errori prima di modificare il registro.

Dopo una variazione intenzionale dei sorgenti o degli stati:

```powershell
& $quickPython tools/quick_rif_registry.py --refresh
git diff -- docs/quick/compat/parita.json docs/quick/compat/richieste.csv docs/quick/compat/prove.csv
& $quickPython tools/quick_rif_registry.py --check
```

`--refresh` aggiorna i campi derivati e il riepilogo; conserva gli stati e le
prove. Un elemento scomparso resta nel registro e continua a generare un errore:
la rigenerazione non lo elimina silenziosamente. `--create` serve solo per la
prima creazione e rifiuta un `parita.json` già esistente.

Attenzione alle modifiche editoriali: le destinazioni delle richieste con
`mapping_basis` che inizia con `[I]` sono rigenerate. Per conservare una revisione
manuale, usare una dicitura esplicita come `Revisione manuale: [I] destinazione
confrontata con R... e ...`, citando ciò che è stato letto. Non trasformare
un'inferenza in `[V]` per conservarla. Nei CSV vengono conservati gli stati,
i collegamenti ai test e `parity_ids`; i campi estratti dai sorgenti non si
correggono direttamente nel CSV.

## Stati e prove richieste

| Stato | Significato |
|---|---|
| `da fare` | Contratto censito, senza parità Quick dimostrata |
| `in corso` | Implementazione o verifica avviata, con lacune ancora aperte |
| `fatto` | Prova comportamentale eseguita con successo e confronto visivo rivisto |
| `differenza voluta` | Scelta esplicita documentata; non equivale a implementazione verificata |

La percentuale di ciascuna fase è il numero di elementi `fatto` con prove valide
diviso il totale degli elementi assegnati a quella fase. Gli elementi comuni
compaiono in più fasi: i totali non vanno sommati. Le differenze volute restano
separate e non aumentano il numeratore. I sei scostamenti iniziali riguardano
Plex, grey, indigo e l'accento permanente di Posa/Calcola, decisi in R390, R391 e
R396. Non dimostrano che tutti questi cambiamenti siano già realizzati.

Per una differenza voluta compilare `reason` e `decision`, con riferimento
leggibile, per esempio `docs/quick/CONTESTO.md#R396`. Il controllo verifica che
file e marcatore esistano; resta responsabilità del revisore verificare che la
decisione autorizzi proprio quello scostamento.

Per `fatto`, la lista `evidence` della voce di parità deve contenere almeno:

- Una prova `kind: "test"`: `path` del file Python, `symbol` nel formato
  `Classe.test_metodo`, `sha256` del file e `run` del rapporto di esecuzione.
  Il metodo deve esistere e contenere assert. Le prove del registro stesso
  non valgono come prove della UI.
- Una prova `kind: "visual"`: `path` dell'immagine, `sha256`, `reviewed_by`
  compilato dopo l'ispezione e `comparison` del confronto conservato.

Il rapporto indicato in `run` deve contenere una lista `cases`. La voce del
metodo deve riportare gli stessi `path`, `symbol` e `sha256`,
`result: "passed"` e `parity_ids` contenente l'ID della funzione dimostrata.
Tutti i percorsi devono essere file presenti nel repository o nel suo `build/`.
Conservare il log che giustifica l'esito; un hash lega la prova ai sorgenti,
non verifica da solo la correttezza semantica del test.

Il comando di controllo legge questi rapporti: non esegue i test. Per produrli
usare `tools/quick_rif_evidence.py`, descritto sotto. Il runner generale stampa
gli esiti ma non esporta il formato `cases`; anche i rapporti differenziali con
chiave `results` hanno un formato distinto. Un rapporto descrittivo o un
segnaposto non basta.

Nei CSV, `fatto` richiede `parity_ids`, con ID separati da `;`, che puntino a
voci `fatto` e provate in `parita.json`. Non riciclare il medesimo test per una
richiesta più ampia senza aggiungere gli assert e i gesti mancanti.

### Produrre il rapporto da un'esecuzione reale

Preparare un JSON che associa ciascun metodo completo agli ID che i suoi
assert verificano. Esempio di struttura, con nomi di test da sostituire con
quelli effettivamente implementati nel ramo:

```json
{
  "quick.pianta.test_gestures.PlanGestures.test_move_and_undo": [
    "command:tool_move",
    "phase_command:model/edit/tool_move"
  ]
}
```

Il metodo deve essere definito direttamente nella classe indicata. Gli ID
devono già esistere in `parita.json`; il runner rifiuta mappature vuote, ID
ignoti e chiavi JSON duplicate. Il collegamento semantico resta da verificare:
associare l'ID di un comando a un test estraneo non ne dimostra la parità.

Dopo aver salvato la mappa, per esempio in `build/compat-tests.json`:

```powershell
& $quickPython tools/quick_rif_evidence.py --mapping build/compat-tests.json --output build/quick-parity/gesti-R01.json --timeout 300
```

Scegliere prima l'ambiente offscreen o nativo adatto alla prova. Ogni metodo
parte in un interprete separato e conserva la normale gestione unittest delle
fixture di modulo e classe, comprese le pulizie. Il timeout comprende anche
l'avvio e la chiusura del processo; non è una misura di fluidità della UI.

Il runner scrive il JSON `cases` e il log completo accanto, in questo esempio
`build/quick-parity/gesti-R01.json.log`. Entrambi i nomi devono essere nuovi.
Conserva percorso del sorgente, simbolo, hash SHA-256, PID, ID di parità
ed esito effettivo. Per un errore durante l'import
potrebbero non essere disponibili simbolo e hash: quella prova non è passata.

`passed` deriva soltanto da `unittest.addSuccess`, con una sola prova eseguita
e uscita regolare del processo. Fallimenti, eccezioni, sottoprove fallite,
`skipped`, `expected_failure`, `unexpected_success`, timeout e crash restano
distinti e non valgono come successo. Un errore nella pulizia della classe
invalida anche un metodo che aveva già passato gli assert. Se il sorgente
cambia durante la prova, l'esito è `source_changed`.

Il codice di uscita è 0 solo se tutti i metodi risultano `passed`, 1 quando
almeno uno non è passato; gli errori di invocazione sono segnalati separatamente.
Il runner non promuove voci del registro e non produce la revisione visiva.
Dopo aver letto il log e guardato il confronto, collegare il rapporto in `run`
e l'immagine in `evidence`, poi eseguire il controllo dei registri.

## Collegare i comandi del proprio ramo

L'API è in `tests/quick/parity/differential.py`:

```python
from quick.parity.differential import Adapter, run_scenario

quick = Adapter("Quick", commands=actual_handlers,
                observe=read_actual_frontend_state, settle=wait_for_jobs)
result = run_scenario(scenario, widgets_adapter, quick)
```

`commands` associa i nomi dello scenario ai veri gestori del frontend;
`observe()` restituisce le osservazioni richieste; `settle()` aspetta i lavori
asincroni. I nomi degli scenari, come `building`, `calculate` e `save`, non
coincidono necessariamente con gli ID di `shortcuts.py`: il collegamento va
dichiarato nel test.

Partire da `COMMAND_SCENARIOS` e dalla descrizione in `scenarios.json`, mantenendo
coerenti le due rappresentazioni. Aggiungere i numeri R pertinenti e le prove
del nuovo ramo. Preparare due copie indipendenti della medesima fixture.
`connected_fixture()` offre un caso con moduli collegati, consumi e accumulo;
`quick.sample.recorded_weather` prepara i dati meteo registrati, senza rete.

`run_scenario` controlla prima la presenza di tutti i comandi, poi esegue entrambi
i lati e confronta ogni passo. `missing`, `different` ed `error` sono parità
incompleta. Non aggiungere all'adattatore una modifica diretta del modello per
simulare un comando Quick assente. Usare `write_evidence(path, results)` con un
nome nuovo per conservare esiti e differenze; i file esistenti vengono rifiutati.

`canonical_project` conserva il payload del progetto tranne il timestamp
`modified`; `compare` controlla campi mancanti, ordine delle liste e numeri con
tolleranze esplicite. Un confronto positivo dei comandi non dimostra che il
pulsante, la scorciatoia o il gesto li raggiungano: aggiungere eventi Qt reali
al `QQuickWindow`, controllando stato e pixel.

## Provare lettura e salvataggio dei formati

`tests/quick/parity/formats.py` espone `frozen_cases`, `QuickFiles`, `roundtrip`
e `current_config_roundtrip`. Le fixture in `tests/formati/file/` restano
immutate, comprese quelle corrotte o di versioni future.

`QuickFiles.open(path)` segue il caricamento iniziale attuale e crea una vera
finestra Quick. Per provare il salvataggio, passare a
`QuickFiles(cache, save_command=...)` un gestore con firma `(host, path)` che
chiami il comando reale del frontend. Non passare `Project.save` come sostituto.

`roundtrip(source, destination, quick, widgets_open=...)` apre in Quick, salva
in un percorso nuovo e riapre in Widgets. `widgets_open(path)` deve restituire
il progetto letto dalla vera `MainWindow`. La mancanza di Save o dell'adattatore
di riapertura produce `missing`; non è un ciclo di compatibilità riuscito.

Nel prototipo attuale Save e i comandi delle impostazioni Quick sono assenti.
`current_config_roundtrip` prova soltanto il contratto condiviso del file di
configurazione corrente. Lavora su copie e non dimostra la UI Impostazioni,
né richiede di retrocedere artificiosamente lo schema alle vecchie versioni.

## Riferimenti, confronti e finestre native

```powershell
& $quickPython tools/quick_rif.py --list
& $quickPython tools/quick_rif.py --fixture empty --theme light --scale 1 --size 1600x960 --states phase-model --run mio-ramo-r01
```

Il secondo comando è un'acquisizione diagnostica di un solo stato. Usare un
nome nuovo per ogni tentativo. `--matrix` richiede l'intera matrice prevista:
vuoto e Rho, due temi, scale 1 e 2, misure 1366×900, 1600×960 e 1920×1080.
`--resume` salta solo i casi completi verificati; non sovrascrive quelli parziali.
`--populated` aggiunge consumi, investimento e accumulo alla fixture Rho e va
trattato come caso supplementare, distinto dal progetto originale.

Le immagini sono in `build/riferimento/<run>/<caso>/`, i JSON e i manifest in
`docs/quick/compat/riferimento/<run>/<caso>/`. `--offscreen` è diagnostico e non
costituisce un riferimento GPU nativo. Prima di una cattura nativa togliere
`QT_QPA_PLATFORM=offscreen` dall'ambiente.

Il ramo Quick deve assegnare `objectName` univoci agli elementi da confrontare.
`geometry.capture_quick(window, scenario=..., meta=...)` cattura il loro albero
visivo. Una mappa JSON esplicita associa gli ID Widgets agli ID QML, eventualmente
con una corrispondenza dei ruoli colore. Gli elementi fuori dalla mappa non
sono coperti. Per struttura e limiti leggere `prove-native.md`.

`tools/quick_rif_compare.py` richiede `--widgets-json`, `--quick-json`,
`--widgets-image`, `--quick-image`, `--mapping` e `--output`. Le immagini devono
avere uguale dimensione fisica e DPR. Il risultato è un nuovo HTML autonomo con
le immagini e la differenza RGB; codice di uscita 1 se restano differenze
geometriche non approvate. La tolleranza massima è 1 px logico per rettangoli
e margini; testo, font e colori sono confrontati esattamente.

Le deroghe di `differenze.json` richiedono scenario, due ID, campo, valori prima
e dopo, richiesta e motivo. Non ammettono wildcard. Sono distinte dallo stato
`differenza voluta` nel registro: decidere il nuovo font non autorizza una
deroga indiscriminata su tutti gli elementi o su qualunque carattere.

Per i fotogrammi e le chiamate Python usare `FrameRecorder`, `PythonCalls` e
`native_app()` di `realwindow.py`, come descritto in `prove-native.md`.
Le prove native vanno in un processo dedicato:

```powershell
$env:QT_QPA_PLATFORM = $null
$env:MERIDIANA_QUICK_NATIVE = '1'
& $quickPython -m unittest quick.parity.test_realwindow
$env:MERIDIANA_QUICK_NATIVE = $null
```

Su Windows il percorso nativo usa Direct3D 11. Il readback dei fotogrammi rallenta
il rendering: non dimostra il limite di 30 ms né la fluidità effettiva a monitor.
Le prove che iniettano una finestra inattesa verificano il banco di prova; R392
si chiude solo verificando il vero ingresso nella pagina File Quick.

## Verifica prima di consegnare

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
& $quickPython tools/quick_rif_tests.py
& $quickPython -m unittest discover -s tests/formati -t tests
& $quickPython -m ruff check --select F,E9,B .
& $quickPython tools/quick_rif_registry.py --check
```

Il runner scopre anche i sottogruppi Quick dei rami uniti, ognuno in un processo
separato. Un sottogruppo con test deve contenere `__init__.py`. Le prove native
saltate offscreen restano da eseguire separatamente. Le differenze note marcate
`expectedFailure` restano aperte: il successo complessivo della suite non le
trasforma in funzioni compatibili.

Consegnare insieme codice, test, legami alle richieste, esiti effettivi e
confronti guardati. Nel proprio stato indicare quali combinazioni sono state
provate, quali capacità sono assenti e quali differenze attendono una decisione.
