# Catalogo Quick: esito del 04/11/2026

## Consegnato

- [V] Backend `QObject`, modello `QAbstractListModel` e pagina QML autonoma.
  Cinque categorie: moduli, inverter, microinverter, ottimizzatori e accumuli.
- [V] Lettura, preparazione dello schema, ricerca e ordinamento fuori dal filo
  della finestra. Ricerca ritardata di 160 ms; risultati superati scartati.
- [V] Ricerca con tutte le parole, origine, marca intera, potenza minima/massima.
  Per i moduli: famiglia, bifaccialità, rendimento minimo, lunghezza massima.
  Filtri ricordati per categoria durante il processo. Azzeramento esplicito.
- [V] Marche ricercabili in elenco virtualizzato. Selezione semplice, Ctrl e
  intervallo con Shift; confronto automatico dei primi quattro prodotti scelti.
- [V] Ordinamento numerico e per famiglia dal titolo delle colonne. La scelta
  segue il record. Ogni record incoerente è rifiutato da `audit_record`, come
  `CatalogDialog.accept` dei Widgets (R238).
- [V] Nessun limite a 400/500 righe (R25): prova con 17.000 record; fotografie
  con tutti i 21.713 moduli distribuiti. Solo le righe visibili hanno delegate.
- [V] Editor: campi obbligatori, tutti i campi presenti nello schema della categoria,
  valori complessi in JSON, aggiunta di campi arbitrari in JSON. I valori ignoti
  restano ignoti. Numeri italiani senza perdita della precisione originaria.
- [V] Validazione e salvataggio tramite `catalog.personal`. Le verifiche ereditate
  vengono invalidate. Duplicati rifiutati, campi e fonti aggiuntive conservati.
- [V] Destinazione assoluta esplicita, file JSON nella radice consentita risolta
  anche attraverso collegamenti. Predefinito: `cwd/build/catalog`. Il salvataggio
  parte disabilitato nei fatti finché manca una destinazione valida; l'errore resta
  nella scheda. File JSON preesistenti estranei ai cataloghi personali rifiutati.
- [V] Nessuna scrittura al profilo utente, ai cataloghi distribuiti o al progetto.
  Il nucleo e `src/meridiana/ui/` non sono stati modificati.
- [V] Link delle fonti apribili: HTTP(S) o PDF. Gli altri schemi sono rifiutati.
  PAN/OND delegati al chiamante con segnale, dalla pagina Catalogo (R315).

## Contratto per il chiamante

```python
from meridiana.quick.backend.catalog import create_page, PAGE_URL

backend = create_page(engine, session=None)
# Il chiamante carica PAGE_URL o istanzia Meridiana.Catalog.CatalogPage.
backend.chosen.connect(on_product)  # (kind: str, record: dict), copia indipendente
backend.importRequested.connect(on_import)  # kind: modules oppure inverters
```

`create_page` installa i controlli e il contesto `catalogBackend`; conserva il
backend sul motore. Il segnale `chosen` non cambia il progetto. L'inserimento nel
progetto compete al chiamante, attraverso `session.edit()`.

La pagina espone `property var backend`, sostituibile nell'istanza QML. Il backend
è anche costruibile direttamente con `CatalogBackend(session, parent,
safe_root=cartella, records=dizionario_opzionale)`. `records` serve alle prove e
agli usi con un catalogo esplicito; senza, legge il catalogo del nucleo in worker.

API principale: `setKind`, `setFilter`, `clearFilters`, `sortBy`, `select`,
`selectRange`, `choose`, `beginEdit`, `setEditorField`, `setEditorExtra`,
`setDestination`, `saveEditor`, `cancelEdit`, `openSource`, `requestImport`.
Proprietà: `model`, `kind`, `filters`, `brands`, `columns`, `details`,
`selectedRecord`, `selectedIds`, `selectedCount`, `selectedNames`, `busy`, `error`,
`editing`, `editorFields`, `editorExtra`, `destination`, `destinationFolder`.

## Prove

- [V] 18 prove specifiche verdi con piattaforma `offscreen`.
- [V] Le stesse 18 prove verdi su Windows nativo, Direct3D 11, scala 1.
- [V] Prova QML con eventi reali e pixel verdi anche su Windows nativo a scala 2.
- [V] Confronto dei gestori reali Widgets/Quick: tastiera nella ricerca, filtri,
  elenco risultante identico, record scelto identico, record revisionato e salvato
  identico a quello prodotto da `CatalogEditor.record()`.
- [V] Percorso QML: ricerca da tastiera, click di riga, Ctrl, End fino all'ultima
  riga, colore selezionato diverso nei pixel, delegate limitati, apertura editor,
  modifica del modello da tastiera, click Salva, rilettura del JSON prodotto.
- [V] Tema vivo: cambio chiaro/scuro, Plex/Inter e testo grande senza warning.
- [V] Sicurezza del file: destinazione mancante, fuori radice o di un catalogo
  distribuito, duplicato, JSON estraneo, JSON tecnico non oggetto, NaN, incoerenza
  Voc/Vmp e rating facoltativo prima ignoto. Nessuna modifica sui casi rifiutati.
- [V] Tutte le cinque categorie salvate in una destinazione temporanea; fonti per
  campo conservate e stato di verifica invalidato.
- [V] Lint `F,E9,B` sui file propri: verde. Nessun trattino lungo nei file propri.

Comando principale, con `PYTHONUTF8=1` e `PYTHONPATH=tests;src`:

```powershell
& C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe -m unittest discover -s tests/quick/impianto -p test_catalog*.py
```

## Fotografie e differenze volute

Cartella:
`C:\Users\Grasso\dev\meridiana-wt-r12-impianto\build\quick-foto\impianto`.

- [V] `catalog-{light,dark}-{1,2}-{1366x900,1600x960,1920x1080}.png`:
  dodici catture native, guardate singolarmente. Le dimensioni logiche sono
  realmente quelle richieste. A scala 2, il file maggiore è 3840 × 2160 pixel.
- [V] Quattro fotografie dell'editor: chiaro/scuro, scale 1/2, guardate.
- [V] Dodici fotografie Widgets corrispondenti, stessa collezione e selezione.
  Guardati i due riferimenti 1366 × 900, chiaro e scuro, per il confronto visivo.
- [V] `catalog-evidence-1.json` e `catalog-evidence-2.json`: piattaforma `windows`,
  `GraphicsApi.Direct3D11`, geometrie richieste/ottenute, DPR, numero record e
  nessun warning. La cattura impone `setMinimumSize`, come la galleria comune:
  senza, Windows riduceva la finestra alla superficie disponibile a scala 2.

La pagina Quick è una pagina, il riferimento Widgets un dialogo. Sono differenze
volute dalla migrazione: titolo e categoria visibili, comandi in alto e nella
scheda; confronto automatico alla selezione multipla; scheda verticale completa;
editor con campi propri invece del solo JSON facoltativo. R394: nessun angolo,
nessun numero di riga, intestazioni fino al bordo, unità sotto il titolo, sole
linee orizzontali, barra sovrapposta, conteggio fermo. R395: font e colori dal tema
comune, inclusi i menu e le barre di scorrimento comuni appena disponibili.

## Limiti dichiarati

- Il launcher e i collegamenti di `chosen`/`importRequested` alle altre fasi sono
  fuori dai file assegnati. Il loro completamento è del coordinatore.
- La scelta automatica delle marche preferite, con marche senza dati attenuate,
  appartiene a Impianto. Il filtro marca del catalogo conserva il comportamento
  del `CatalogDialog`, senza preferite.
- Le nuove stringhe hanno un fallback italiano confinato a `catalog_i18n.py`.
  Il catalogo gettext comune ha precedenza; migrazione dei msgid nuovi nel PO
  comune da coordinare. Contenuti originali delle schede e chiavi JSON restano
  quelli della fonte.
- Non sono dichiarati confronto geometrico Widgets entro 1 px, misure di frame
  time sul monitor reale o registrazioni fotogramma per fotogramma delle
  transizioni. La lista scorre in QML; Python fornisce soltanto i dati delle nuove
  righe che diventano visibili, senza gestore Python del movimento del puntatore.
- Suite generale e gruppo `formati` affidati al coordinatore per eseguirli una
  volta sull'intero lotto. Qui è stato verificato il catalogo, inclusa la parità
  con i gestori Widgets, senza modificare il programma Widgets.
