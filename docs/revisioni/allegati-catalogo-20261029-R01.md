# R236: allegati e catalogo personale

29/10/2026. Lotto B del piano `2026-10-29-servizi-cataloghi-meridio.md`.

## Risultato

- [V] Meridio accetta PDF e testo UTF-8 (`.txt`, `.md`, `.csv`) dal pulsante e tramite trascinamento sul campo, sulla conversazione o sul pannello. Lettura locale in `QRunnable`, anteprima del testo e rimozione.
- [V] Limiti: quattro file o job contemporanei, 10 MiB per file, 40 pagine PDF, 60.000 caratteri per documento e per somma dei documenti del messaggio. PDF cifrati, file danneggiati, testo non UTF-8 e documenti senza testo sono rifiutati con motivo visibile. Nessun OCR implicito.
- [V] Aggiungere un documento non invia nulla. L'invio avviene con il messaggio successivo. Il payload contiene nome, tipo, fonte e testo, senza percorso locale. Il testo non viene salvato nel catalogo o nel progetto.
- [V] Ogni nuovo messaggio con allegati destinato al cloud richiede una conferma specifica, anche se esiste il consenso generale. Riservatezza ricontrollata all'avvio della chiamata, anche dopo una precedente conferma.
- [V] Documenti serializzati come dati non attendibili, con vincolo anche nel prompt di sistema. I tool rimangono disabilitati per l'intera conversazione che contiene documenti; una chiamata tool restituita comunque dal provider viene chiusa senza esecuzione. L'interfaccia spiega come riattivare gli strumenti tramite Nuova conversazione.
- [V] Una risposta JSON con `catalog_kind` e `record` crea una scheda di proposta. Il pulsante Rivedi apre l'editor; non importa e non cambia automaticamente il progetto. Lo strumento `propose_catalog_record`, integrato dalla sessione principale, usa lo stesso contratto tramite `WindowHost.prepare_catalog_record`.
- [V] Inserimento manuale senza AI, revisione di una scheda selezionata, campi essenziali con unità e ulteriori campi JSON. Valori mancanti restano sconosciuti: il salvataggio richiede i dati essenziali dichiarati, produttore, modello e fonte.
- [V] Catalogo personale in `Paths.data/catalog/personal.json`, scrittura atomica. Un modello personale già esistente viene rifiutato: una revisione richiede un nome distinto e conserva il precedente. I cataloghi distribuiti restano separati e i dati selezionati continuano a essere copiati nel progetto.
- [V] Filtro origine Personale, ricerca attraverso l'API catalogo, confronto di due-quattro righe con campi e dati sconosciuti espliciti. I campi AC/DC del lotto C vengono conservati e mostrati.
- [V] `audit_record` impedisce la conferma di una scheda incoerente, compreso il caso CEC `Imp > Isc`, sia con OK sia con doppio clic. Nessun valore del catalogo è stato corretto senza fonte.

## Prove

Ambiente Windows, Python della venv `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`, Qt offscreen. Nessuna chiamata cloud reale, nessuna chiave usata, nessuna API a pagamento.

- [V] 104 test superati: `widget.test_attachments_catalog`, `nucleo.test_attachments_personal`, `widget.test_catalog_dialog`, `widget.test_assistant_widget`, `nucleo.test_catalog`.
- [V] 22 test superati: `finestra.test_assistant_chat`, con directory PySide6 nel PATH e `QML2_IMPORT_PATH` esplicito.
- [V] 15 test nuovi verificano PDF con testo e senza testo, PDF errato, UTF-8 invalido, limiti, payload privo di percorso locale, rimozione, risposta di job rimossa/cambiata, consenso cloud specifico, riservatezza dopo consenso, blocco tool ostili, editor e persistenza, tipi/range dei rating opzionali, impedimento della scelta incoerente.
- [V] Il test del blocco `Imp > Isc` è stato eseguito prima della modifica e ha riprodotto la conferma erronea, poi è passato con la correzione.
- [V] Ruff F/E9/B pulito sui file del lotto e sui nuovi test.
- [V] Screenshot offscreen aperti e controllati: editor normale, editor stretto, allegato Meridio e confronto catalogo. I controlli e i pulsanti sono leggibili e raggiungibili. Immagini nella cartella omonima del rapporto; lingua inglese in questa verifica, prima dell'integrazione delle traduzioni.

Il primo tentativo dei test finestra ha prodotto 22 errori di setup: `qtquick3dhelpersplugin.dll` non trovata. Il medesimo gruppo, senza modifiche al runtime e con PATH/QML2_IMPORT_PATH corretti, ha poi superato tutti i 22 test. Il problema non è stato mascherato nei test.

## Contratti per l'integrazione

- `CatalogEditor(kind, record=None, parent=None)`: `record()` valida; `accept()` salva il prodotto personale; `saved` contiene il risultato.
- `review_record(kind, record=None, parent=None) -> dict | None`: editor modale deliberato dal progettista.
- `Chat.prepare_catalog_record(kind, record) -> bool`: crea una proposta da rivedere. Non apre da sola l'editor e non scrive dati.
- `WindowHost.prepare_catalog_record`: delega alla callback installata da Chat.
- Concordati e aggiunti i ponti della sessione principale: `local_assistant_command -> win._assistant_command`, `prepare_bug_report -> win._report_bug`, `start_guided_tour -> win._start_tour`.

## Limiti e verifiche residue

- [V] Rimozione e cambio conversazione/progetto ignorano il risultato tardivo. Non interrompono forzatamente il parser PDF già in esecuzione: il job termina senza ripristinare la scheda rimossa.
- [V] Un PDF scansionato richiede OCR esterno prima di essere allegato.
- [V] I campi tecnici ulteriori rimangono modificabili come JSON; i dati essenziali hanno campi dedicati.
- [I] La qualità della proposta dipende dal modello e dalla chiarezza della scheda: non è stata misurata con un servizio reale. La revisione umana e la validazione restano obbligatorie.
- Traduzioni e suite completa sono responsabilità dell'integratore, una sola volta per il lotto complessivo. Nessun commit o rilascio eseguito dal lotto B.

## Correzioni dopo review indipendente R236

[V] Quattro regressioni eseguite prima delle correzioni hanno riprodotto tre failure di consenso/provenienza e due errori di validazione, uno per ciascuna scheda strutturata. Dopo le correzioni, 19 test dedicati allegati/catalogo personale e 89 test mirati complessivi (`widget.test_attachments_catalog`, `nucleo.test_attachments_personal`, `widget.test_catalog_dialog`, `nucleo.test_catalog`) superati. Ruff sui quattro file aggiornati superato.

- [V] Ogni seguito cloud che reinvia una conversazione contenente documenti richiede una nuova conferma, anche senza allegati nuovi. La card dichiara esplicitamente il reinvio del testo precedente. Passando da cloud a locale e poi di nuovo a cloud, la conversazione locale viene eliminata secondo la barriera privacy già esistente, insieme allo stato di presenza dei documenti. La regressione usa la selezione del provider reale e controlla che nessun documento rimanga nel nuovo payload cloud.
- [V] Le copie personali di SUN2000-20K-MB0 e LUNA2000-7-S1 accettano array di correnti per MPPT, tabelle di corrente per numero di stringhe, dimensioni e intervalli di tensione per fase. Foglie numeriche finite e positive, selettori numerici e intervalli ordinati vengono validati senza appiattire la struttura originale. Tabelle/range malformati restano rifiutati.
- [V] Gli ancoraggi `field_sources` conservano fonte, pagina e revisione originarie. Il flag `verified` viene sempre rimosso da una scheda personale, anche se proveniva dal catalogo curato o da una dichiarazione del modello; lo stato dell'ancoraggio diventa `unverified_personal`. Un rating modificato non eredita la verifica del precedente e l'audit non lo promuove a `verified_field`. La scheda originale non viene mutata.

## Pannello Meridio compatto, correzione R02

[V] La suite finestra ha rilevato la regressione `test_ctrl_l_the_size_of_the_bubble_and_the_dock_are_kept_and_the_dock_has_its_own_button`: altezza minima 289 px, superiore alla soglia 260 px che nasconde i suggerimenti. La nuova riga Allegati impediva al dock di attraversare tale soglia. Riprodotto il medesimo errore nel test isolato; la sola rimozione runtime della riga riduceva l'altezza a 255 px e nascondeva i suggerimenti, isolando la causa senza modifiche permanenti.

[V] `SuggestionsBox` conserva la dimensione desiderata naturale ma permette altezza minima zero quando agganciata. Il layout può ridurre il dock e attivare la modalità compatta, mantenendo campo messaggio, conversazione e comando Allegati. La dimensione naturale e i suggerimenti tornano quando il pannello cresce; il fumetto flottante conserva il proprio minimo.

[V] Nuova regressione widget fallita prima della correzione (minimo 339 px nella configurazione del widget), poi superata. Il test finestra originario e i gruppi widget assistente/allegati hanno superato 31 prove; Ruff mirato superato. Foto offscreen `dock-compatto-offscreen-R02.png` controllata: suggerimenti nascosti a 172 px, campo e comando allegati visibili. Nessun cambiamento di soglia o indebolimento del test esistente.
