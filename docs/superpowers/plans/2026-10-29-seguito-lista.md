# Meridiana: seguito completo della lista

Specifica: richieste R198-R234 in `docs/richieste.md`, proposta HTML approvata e messaggio di Daniel
«procedi con i punti rimasti nella lista, senza perdere quelli aggiunti dopo». Base: af17add.
Architettura invariata: Python/PySide6, core senza Qt, modifiche progetto tramite session.edit.
Le scelte visive gia approvate si attuano senza riaprire una richiesta di consenso.

## Stato iniziale verificato

- R198-R202, R204, R206-R208, R212, R218 e R224 implementati nel lotto 246ec58.
- R209: popup ridimensionati, verifica nativa degli angoli ancora distinta da offscreen.
- R213: EXE/ZIP Windows e Flatpak Linux verificati in R03; installazione e GPU native ancora da provare.
- R211 regola permanente: verifiche mirate durante sviluppo, generale per lotto; non allentare soglie.
- R214 regola permanente: ogni componente condiviso va nel template, con prove e manifest aggiornati.
- Non sono completati dalla sola consegna precedente i punti elencati sotto.

## Esecuzione e responsabilita

- [x] R203/R221, root: `ui/assistant.py`, superficie conversazione distinta, messaggi riconoscibili per ruolo,
  nomi espliciti, streaming e selezione/scorrimento conservati. Foto nei due temi e prova contenuto reale.
- [x] R205/R210, root: `ui/file_page.py`, `ui/preferences.py`, navigazione File distinta dalle impostazioni;
  salva/revisioni riuniti, sezioni di impostazioni dedicate, larghezze leggibili, tutti i comandi raggiungibili.
  Verificare accesso diretto Meridio e tastiera, salvataggio immediato/annulla/ripristino invariati.
- [x] R219, root: nuova icona Allinea a un lato, leggibile a 16/20 px, confronto fotografico.
- [x] R220, root: ricerca fonti primarie su tipografia/documentazione tecnica, gerarchia comune per testo,
  formule e tabelle; profili relazione per destinazione/dettaglio, header/footer/pagine; render PDF prima/dopo.
- [x] R222/R232-R234, Sol shared_ux: rientro invariabile Verifiche, hover calendario, tooltip stabile con palette
  autonoma e comparsa semplice. Test del sintomo e foto; riporto nel template.
- [x] R223, Sol shared_ux: confrontare animazione File Meridiana/template/Quotario e allineare il componente
  generico alla variante preferita; preservare modifiche utente preesistenti nei repository.
- [x] R215/R216, Astra format_packages_design: audit e correzioni dimensionamento/stringatura globale,
  orientamenti/inclinazioni compatibili anche fuori dalla modalita est-ovest, ingressi fisici e MPPT distinti.
- [x] R225-R229, Astra format_packages_design: audit ombre/bypass/stringhe/ottimizzatori singoli e doppi,
  SolarEdge e limiti degli ingressi con fonti locali prima del web; regressioni numeriche per ogni bug provato.
  Distinguere geometria, modello elettrico implementato e approssimazioni, senza dichiarazioni normative implicite.
- [x] R216/R217, root dopo audit: strumenti di posa est-ovest e pensiline, anche parcheggi; geometria separata
  da connessioni, undo e serializzazione provati; evitare cambi schema concorrenti senza accordo.
- [x] R230/R231, Sol inverter_focus: export IFC con identita stabili/dati e import geometrie complesse;
  superfici ausiliarie utilizzabili per posa e riposizionabili. Fixture reali di tessellazione/posizionamento/unita;
  distinguere proprieta IFC dai parametri nativi dell'applicazione destinataria.
- [x] Root: traduzioni, integrazione, revisione finale indipendente, aggiornamento Windows e template,
  aggiornare pacchetti solo dopo un lotto coerente e verificato.

## Confini e verifiche

Sol shared_ux possiede popups/day_picker/checks_page e relativi file template. Root possiede File/Preferences,
Meridio, relazioni e modello di posa. Astra possiede energy e checks.py. Sol inverter_focus possiede ifc_import/export.
Ogni modifica a model.py o schema catalogo va coordinata prima. Solo root aggiorna PO, registro richieste e manifest.
La tabella principale conserva tutti gli ID; i rapporti per sottosistema riportano prove, decisioni e limiti.
Nessun dato reale modificato dalle prove. Prove native separate e dichiarate. Nessun tag o release pubblica implicita.

## Registro di avanzamento

- Avvio: cartella di lavoro e cartelle Windows allineate ad af17add, nessuna modifica tracked preesistente
  in Meridiana. Template conserva le modifiche utente segnalate nel lotto precedente.

- Seguito: implementazione e revisioni completate nei perimetri del lotto; R215/R225-R229 restano parziali, con residui espliciti nel registro e nell'audit. I segni sopra indicano esecuzione del lotto, non validazione di ogni caso tecnico.
- Template pubblicato 3da1098; prove estese e mirate nel rapporto integrazione-seguito-20261029.md. Pacchetti da snapshot Windows R10/Linux R05 in preparazione, dopo correzione della posa obsoleta.
