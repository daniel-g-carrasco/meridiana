# Servizi, cataloghi e Meridio: R235-R240

> Esecuzione: subagent-driven-development per i lotti indipendenti, integrazione nella sessione principale.

**Obiettivo:** attuare le richieste successive alla consegna R05 senza perdere nessun punto.
**Architettura:** estendere i servizi puri esistenti e collegarli a controller Qt; lavori lenti fuori dal thread grafico.
**Tecnologie:** Python, PySide6, cataloghi JSON, pypdf e aggiornamenti firmati già disponibili.
**Specifica:** docs/richieste.md R235-R240 e istruzione di Daniel «Procedi con i prossimi punti».
**Base:** bf0767b. Worktree esistente integra-kimi-9-10, separato dalla cartella di avvio.

## Scelte applicative

Aggiornamenti: riusare firma e downloader esistenti, stato persistente visibile all’avvio, automatismo facoltativo;
Windows installato e Flatpak seguono i rispettivi canali, sorgenti/portable mostrano il percorso appropriato.
Mai chiudere un progetto sporco automaticamente. Nessuna pubblicazione di una release implicita.
Allegati: lettura limitata PDF/testo in un job, anteprima e rimozione, invio soltanto con messaggio dell’utente;
documenti come dati, mai istruzioni. Catalogo personale locale con scheda modificabile e validata, fonte conservata.
Accumulo: configurazione in Impianto, analisi dei risultati nelle pagine di bilancio; AC/DC espliciti,
compatibilità attestata per modello e limiti. Audit sistematico distinguendo fonte, incoerenza e dato sconosciuto.
Segnalazioni: bozza dalla GUI o Meridio, anteprima del testo e diagnostica scelta, invio deliberato dal browser;
nessun dato di progetto o conversazione allegato implicitamente, nessuna segnalazione inviata durante i test.
Visita: primo avvio con invito saltabile, percorso richiamabile da Aiuto e chat; prossima/precedente/chiudi,
navigazione e spotlight sui veri elementi, nessuna modifica al progetto.

## Vincoli globali

- Codice/commenti inglesi, testo UI con gettext, documenti italiani, niente U+2014.
- Il progetto cambia solo tramite session.edit; nessun dato di targa inventato.
- Nessun accesso a chiavi private, nessuna chiamata cloud a pagamento nei test.
- Archivi tecnici locali prima delle fonti primarie online. Provenienza per le affermazioni tecniche.
- Test mirati durante i lotti; suite completa una volta prima dell’integrazione. Foto UI reali o offscreen dichiarate.
- Conservare file/log precedenti e modifiche preesistenti dei template; portare componenti condivisi nel Qt.
- Config migrazione unica 21 -> 22, coordinata; progetto schema solo se cambia struttura incompatibile.

## Lotti e responsabilità

- [x] A R235: updates.py, ui/update_dialog.py, ui/preferences.py area Privacy; controller aggiornamenti separato.
  Prove: opt-in, stato all’avvio, firma rifiutata, download/errore/cancel, progetto sporco, piattaforme e nessun riavvio forzato.
  L’integratore collega window.py/config.py. Confronto app-template e modulo riusabile Qt.
- [x] B R236: assistant/attachments.py, catalog/personal.py, ui/catalog_dialog.py e editor,
  ui/assistant.py/ui/assistant_chat.py/provider/conversation soltanto per gli allegati.
  Contratto: allegati estratti con nome/tipo/testo/fonte; scheda personale confermata, mai applicazione automatica.
  Prove: PDF/testo, limiti, file illeggibile, rimozione, privacy cloud, record incompleto e persistenza/selezione.
- [ ] C R237-R238: energy/storage.py o nuovi moduli dedicati, catalog/audit.py, ui/storage_page.py,
  catalog/data solo con fonte. Non modificare catalog/__init__.py o catalog_dialog.py senza coordinamento con B.
  Contratto: controller installabile su MainWindow, bilancio AC/DC e compatibilità con risultati espliciti.
  Prove: AC indipendente, DC compatibile/incompatibile/sconosciuto, limiti e stato cancellato/undo; audit tutto catalogo.
- [x] D R239-R240 integratore: feedback.py, ui/feedback.py, tour.py, ui/tour.py; integrazione centrale
  window.py/config.py, assistant/tools.py (nuove azioni), navigation_targets e scorciatoie.
  Prove: privacy bozza, nessun invio automatico, richiamo chat, invito una volta/salta/riprendi, navigazione senza edit.
- [ ] E revisione indipendente dei diff A-D; traduzioni, controlli finali, port template, integrazione Windows,
  pacchetti nuovi e consegna Linux verificata dopo congelamento (autorizzazione permanente di Daniel).

## Rischi da verificare

1. Risultato di un allegato arrivato dopo rimozione/cambio progetto: scartarlo.
2. Aggiornamento scaricato che tenta di chiudere dati non salvati: nessuna perdita.
3. Batteria dello stesso marchio ma modello non attestato: compatibilità sconosciuta, non positiva.
4. Testo di documento ostile o dati estratti ambigui: non diventa comando o dato verificato.
5. Tour in finestra stretta/pannello chiuso: navigare al vero elemento visibile o spiegare la destinazione.

## Registro esecuzione

Ricognizione: aggiornamenti firmati Windows, ricerca catalogo e spotlight esistono. Nessun catalogo personale
nella API corrente; nessuna visita guidata completa o flusso allegati nella chat. Nessun dato utente modificato.


Lotti A, B e D implementati e revisionati. R237 implementata; per R238 chiuso l’audit strutturale completo,
ma resta aperta la verifica puntuale generale sulle schede originali. Non viene dichiarata completata.
La suite finale ha trovato e corretto due difetti di integrazione (tool non esposti e campi accumulo non tipizzati)
e una regressione dimensionale della chat con allegati. Le aspettative di fasi e configurazione sono aggiornate.
Nuovo freeze di consegna: build/source-manifest-20261029-R17.json, 353 file.
