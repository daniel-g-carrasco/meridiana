# Formato .mer e pacchetti distribuibili

29 ottobre 2026. Disegno e implementazione del codec nel checkout `C:\Users\Grasso\dev\meridiana-integra-kimi-9-10`, base `209bd9a`, con modifiche di altre sessioni in corso. I percorsi relativi sotto sono riferiti a questa radice.

**Decisione di Daniel:** «non mi interessa aprire i vecchi .meridiana non è stato ancora utilizzato a livello produttivo, ricordatelo. Direi che ci sta il nuovo .mer pensatelo bene». ZIP approvato; nessun requisito di retrocompatibilità o procedura di conversione. I file esistenti non vengono modificati. La lettura JSON rimasta nel codice serve alle fixture storiche e non costituisce una promessa di compatibilità del prodotto.

[V] indica lettura del codice o comando eseguito in questa ricognizione; [P] indica una proposta. Questa ricognizione precede la costruzione dei pacchetti del lotto principale; non verifica installazione o pubblicazione e non consulta segreti. Le prove del 25 ottobre citate dal compito 18f sono documentazione storica, non verifiche della build attuale.

## 1. Stato verificato prima dell'implementazione

- [V] `src/meridiana/model.py`: formato logico 18, JSON testuale, migrazioni 1-18 e rifiuto delle versioni future. Il progetto contiene moduli, inverter, varianti, sito, clima, riservatezza e identificativi `job_id`/`series_id`.
- [V] `src/meridiana/portability.py`: allegati e logo incorporati in base64, profilo della relazione e meteo copiati nel progetto; limite di 64 MiB per singola risorsa decodificata. Il controllo avviene dopo la lettura/decodifica. Non risulta un limite complessivo del contenitore. Un allegato non leggibile può restare un riferimento esterno: il salvataggio non garantisce oggi che ogni risorsa sia incorporata.
- [V] `src/meridiana/underlay.py`: immagini di sfondo già incorporate in base64. `model.py` limita separatamente il testo dell'immagine a 64 MiB. I due limiti hanno quindi unità effettive diverse.
- [V] `src/meridiana/atomic.py`: temporaneo nella stessa cartella, flush/fsync, copia del precedente in `.bak`, sostituzione del file. La copia `.bak` viene scritta direttamente; il fallback copre errori di lettura/parsing JSON, non la successiva validazione semantica del progetto.
- [V] `src/meridiana/recovery.py`: autosalvataggi JSON nella cartella dello stato, recupero offerto senza sostituire automaticamente l'originale, revisioni `_Rnn` con nome libero.
- [V] `src/meridiana/registry.py`: SQLite locale versione 3, separato dal progetto. Non deve diventare un requisito per aprire il documento su un altro PC.
- [V] `src/meridiana/project_index.py`: cerca solo `.meridiana`, legge JSON direttamente. `ui/window.py`, `ui/file_page.py`, MIME Linux e Inno Setup contengono la vecchia estensione. Cambiare soltanto il filtro Salva non basta.

## 2. Tre alternative

Voti progettuali, non risultati di benchmark.

| Soluzione | Vantaggi | Costi e limiti | Voto per Meridiana |
|---|---|---|---|
| JSON esistente con estensione `.mer` | Passaggio rapido; mantiene lettura manuale e migrazioni | Base64 e copie in memoria; nessuna separazione degli allegati; rimangono da correggere limiti e atomicità | 7/10 |
| ZIP con JSON e risorse binarie | Un solo file; contenuto ispezionabile; allegati deduplicati; indice leggibile senza decodificare tutte le immagini | Nuovo lettore, limiti contro archivi ostili, salvataggio completo del contenitore | **9/10, consigliato** |
| SQLite per ogni progetto | Transazioni e accesso parziale | Nuovo schema e migrazioni; copie con WAL da gestire; meno leggibile a mano; confusione con il registro locale | 5/10 |

[V] Adottato ZIP dopo la decisione di Daniel. La libreria standard Python supporta ZIP e DEFLATE, evitando dipendenze nuove. Non si usano compressioni recenti: il programma usa anche Python 3.12. [Documentazione Python](https://docs.python.org/3/library/zipfile.html).

## 3. Contratto .mer implementato

```text
progetto.mer
  mimetype                 application/x-meridiana-project+zip
  manifest.json            formato contenitore, versioni, elenco e digest
  project.json             dati logici e riferimenti alle risorse
  assets/<sha256>           immagini, allegati PDF, logo, eventuali altri binari
```

[V] `mimetype` è la prima voce scritta, non compressa. `manifest.json` dichiara `format: meridiana-project-archive`, `container_version: 1`, `project_version: 18`, SHA-256 e dimensioni effettive di progetto e risorse. Il campo `producer` riporta soltanto nome e versione di Meridiana ed è facoltativo per il lettore; non è un criterio per accettare il documento. Questi hash verificano integrità, non autenticità o riservatezza. Il manifesto non duplica nomi, indirizzi o dati clienti.

[V] `project.json` conserva struttura, unità e identità attuali. Solo `underlays[].image`, `report.attachments[].data` e `resources.report_profile.logo_data` diventano riferimenti `{"$asset":"<sha256>"}`. Nome e ruolo restano nei campi già esistenti; non si aggiungono metadati duplicati. Il lettore ricostruisce gli stessi campi base64 prima di chiamare `Project.from_json`. La versione logica resta **18**: `to_json`, `from_json` e undo mantengono lo stesso contratto, mentre il nuovo adattatore ha versione contenitore 1. Non occorre una migrazione logica 18-19 per cambiare soltanto il trasporto dei byte.

[V] Dati climatici usati, componenti selezionati, immagini e allegati leggibili seguono il meccanismo di incorporamento esistente. Registro clienti completo, API key, cronologia assistente, cache mappe e modelli vocali restano esterni. Un progetto riservato mantiene il proprio campo `reserved`: ZIP non è cifratura. [Limite] Un allegato originale mancante e mai incorporato rimane un riferimento esterno, segnalato all'apertura con cache dalla logica esistente; non è stata aggiunta una nuova conferma nel dialogo Salva. Non dichiarare autonomo quel documento.

[P] I dati della commessa nel file restano limitati al necessario; `job_id` e `series_id` sopravvivono a conversione e revisione. Aprire un documento non importa automaticamente clienti e commesse nel registro della macchina ricevente.

### Integrazione e versioni

[V] `project_archive.read_document` è il lettore comune di modello e indice. Un file `.mer` deve essere un ZIP valido; non si deduce la validità dalla sola estensione. Il salvataggio richiesto con `.mer` scrive il nuovo contenitore; un percorso esplicitamente `.meridiana` mantiene JSON per i test esistenti. Nuovo suffisso, filtri, testi, MIME e associazioni sono integrati dal lotto dell'interfaccia/pacchetti. Nessuna UX di conversione, esportazione retrocompatibile o promessa di apertura con vecchie versioni è richiesta.

### Scrittura, recupero e limiti

[V] Il salvataggio prepara una copia del progetto, incorpora risorse e pubblica i campi modificati in memoria solo dopo la riuscita. [Limite] API sincrona conservata: non è stato introdotto un sistema di job o salvataggi concorrenti. Il costo reale misurato è nella sezione 5.

[V] Temporaneo univoco nella cartella destinazione, chiusura ZIP, flush/fsync; `.bak` anch'essa preparata con temporaneo e sostituzione prima di sostituire il progetto. Prima di aggiornare `.bak` si valida il documento precedente, inclusi hash e modello: un originale corrotto non prende il posto del backup valido. `Project.load` prova il backup anche per danni alle risorse o al modello; una versione futura alza `FutureVersionError` e non ripiega su una copia vecchia. [Limite] Non sono stati simulati guasti di rete o perdita di alimentazione; non si esegue fsync della directory POSIX.

[V] Recovery conserva l'API e il formato JSON della cartella dello stato, incorporando anche allegati leggibili aggiunti dopo l'ultimo salvataggio. Il profilo della relazione già incorporato sopravvive al salvataggio senza profilo esplicito. [Limiti] Nessun journal incrementale, lock o rilevamento di modifiche da un altro processo; una risorsa già mancante non può essere ricostruita. Le nuove scelte di profilo passate solo dalla finestra richiedono il normale salvataggio per entrare nel progetto.

[V] Limiti: 64 MiB per blob, 32 MiB per `project.json`, 2 MiB per manifesto, 512 MiB totali decompressi e per file compresso, 10.000 voci, profondità JSON 64. Anche il numero di voci e la dimensione della directory ZIP sono controllati prima di allocarla; ZIP64 e archivi multipart non ammessi. Conteggio byte durante decompressione; controlli su nomi, duplicati ZIP/JSON, symlink, cifratura, hash, risorse mancanti e non referenziate. Soltanto STORE e DEFLATE ammessi, nessun `extractall`. Il limite preesistente del modello di 64 MiB di testo base64 per uno sfondo resta più restrittivo del limite binario. La memoria di picco non è stata misurata alla soglia massima: non promettere la stessa reattività dei piccoli progetti.

[V] L'indice usa `include_assets=False`: valida manifesto, dimensioni, riferimenti e hash di `project.json`, senza decomprimere le risorse. È quindi un indice preliminare; un blob alterato può comparire finché l'apertura completa lo verifica. Il campo di riservatezza viene dal JSON verificato e i filtri esistenti continuano ad applicarsi. Il fingerprint dell'indice legge comunque tutto il file per SHA-256.

## 4. Pacchetti: stato e lacune

| Destinazione | Verificato nel checkout | Lavoro necessario |
|---|---|---|
| Windows x64 Setup `.exe` | Spec PyInstaller e script Inno in `build-aux/windows`; job in `.github/workflows/test.yml` con installazione e aggiornamento sul runner | Ricostruire lo SHA finale, verificare dipendenze nuove, associazione .mer, installazione/disinstallazione e progetto con allegati |
| Windows x64 ZIP | Job di archivio della cartella PyInstaller già presente | Prova su macchina senza Python; dichiarare che è «senza installazione». `paths.py` usa comunque AppData: non è un profilo interamente portatile su USB |
| Linux x86_64 `.flatpak` | Manifest KDE/BaseApp 6.11 presente; una vecchia build è documentata in 18f | Allineare dipendenze, ricostruire, provare sandbox e GPU, esportare bundle |
| Linux repository + `.flatpakref` | Ricette precedenti GTK in `build-aux/ci-gtk-da-adattare`, nessun job Flatpak attivo in `.github/workflows` | Portare workflow KDE, firma del repository e pubblicazione; attività distinta dalla build locale |

[V] `requirements.txt` include `pypdf` e `ifcopenshell`; la lista e il modulo generato Flatpak non li nominano. È una divergenza verificata delle ricette; non è stata eseguita una nuova prova per stabilire eventuali dipendenze già fornite dal runtime. IFC richiede inoltre prova esplicita nel bundle Windows: la spec non nomina un hook dedicato, il che da solo non prova un difetto.

[V] Windows locale: Python in `C:\Python312\python.exe`; PyInstaller non presente in questo interprete. ISCC non trovato nel PATH né nei due percorsi standard Inno Setup 6. Nessun `.venv-build` o `dist\Meridiana\Meridiana.exe` nel checkout esaminato. Non significa che non esistano installazioni in altre cartelle.

[V] WSL `openSUSE-Tumbleweed`: `flatpak` 1.18.4 e `flatpak-builder` disponibili, KDE Platform/SDK 6.11 e PySide BaseApp 6.11 installati per utente. `~/meridiana-pacchetti` esiste e pesa 2,3 GB. Non riutilizzare quei sorgenti come se fossero lo SHA finale.

[V] `ssh -o BatchMode=yes -o ConnectTimeout=5 fw13` raggiunge il portatile, architettura x86_64; `flatpak` presente, `flatpak-builder` non trovato nel PATH con il controllo eseguito. Nessuna finestra o installazione avviata.

[P] Obiettivo iniziale: Setup Windows, ZIP Windows e bundle Flatpak, con digest e rapporto di verifica sul medesimo commit. Il bundle Flatpak non include le dipendenze del runtime; per aggiornamenti regolari il repository è preferibile. [Documentazione Flatpak](https://docs.flatpak.org/en/latest/single-file-bundles.html).

[P] MSI serve se un cliente richiede distribuzione aziendale: nuova ricetta e prove di upgrade. MSIX serve per un canale che ne sfrutti identità/Store/gestione, con verifica di percorsi, firma e aggiornamenti; Microsoft richiede la firma del pacchetto. [Documentazione MSIX](https://learn.microsoft.com/en-us/windows/msix/overview). AppImage aggiunge un percorso Linux senza Flatpak con altre prove di compatibilità; deb/rpm richiedono scegliere distribuzioni e versioni supportate. Non sono prerequisiti per distribuire Meridiana. Valutazione di priorità: Setup/ZIP/Flatpak 9/10, AppImage 6/10, MSI/MSIX/deb/rpm 4/10 finché manca una richiesta concreta. Nessuna build ARM è verificata.

La firma minisign dell'aggiornatore è già prevista nel CI. Non equivale a una firma Authenticode riconosciuta da Windows. Disponibilità dei segreti e certificati non verificata e nessuna chiave consultata.

## 5. Prove e lavoro rimanente

[V] 88 test mirati passati: `formati.test_formats`, `test_project_files`, `test_project_archive`, `test_portability`, `test_recovery`, `nucleo.test_session`, `test_project_index`. Interprete `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`, Qt offscreen. Ruff sui file modificati passa. I nuovi casi verificano ZIP e deduplicazione, errori di sostituzione/backup, hash alterati, versioni future, percorsi ostili/duplicati, limiti prima dell'allocazione della directory, conservazione del profilo, indice senza decompressione e allegati nel recovery. Non è la suite completa o una verifica di installazione.

[V] Misura singola su Windows, byte casuali non comprimibili, cartella temporanea, stesso interprete; millisecondi, non un benchmark statistico:

| Allegato | Primo salvataggio | Apertura | Metadati | Risalvataggio con backup | Recovery |
|---|---:|---:|---:|---:|---:|
| 1 MiB | 67 | 34 | 1 | 64 | 12 |
| 8 MiB | 317 | 101 | 1 | 483 | 56 |

Rimane da integrare e verificare la UI `.mer` e i pacchetti nel lotto principale. Un salvataggio vicino a mezzo secondo con soli 8 MiB può già essere percepibile: il passaggio a un job in background è un miglioramento distinto, non dichiarato completato. Prove su Linux, GPU, share e file vicini ai limiti non eseguite da questo lotto.

Seguono allineamento delle dipendenze Flatpak/Windows, smoke test del bundle, build sullo stesso commit, prova di installazione/aggiornamento/disinstallazione, firma e canale di distribuzione. Decisioni rimaste a Daniel: eventuale profilo interamente su USB, canali aggiuntivi richiesti dai destinatari, quando pubblicare una release. La scelta ZIP è chiusa e non va riproposta.
