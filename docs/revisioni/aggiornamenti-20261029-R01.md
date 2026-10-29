# Aggiornamenti R235: revisione R01, 29/10/2026

[V] Aggiunto `ui/update_controller.py`: separa controllo, notifica persistente e politica automatica dalla finestra.
La preferenza `auto_install_updates` parte spenta. Con controllo abilitato, Windows installato e installer firmato
idoneo, apre un dialogo non modale e avvia il download. Prima del download e prima di Setup verifica che il progetto
sia pulito. Un progetto modificato resta aperto; l'utente salva e riprova. Nessuna chiamata a quit o riavvio forzato.
Il dialogo conserva il percorso verificato per riprovare dopo il salvataggio senza riscaricare.

[V] `pending_update` conserva soltanto versione e URL. All'avvio si riannuncia la versione più recente con messaggio
senza scadenza. Non si persiste un installer o una fiducia nella sua firma: ogni installazione usa il downloader
esistente, SHA-256, minisign, nome versione e handle Windows contro la sostituzione. Le firme non sono state cambiate.

[V] Distribuzione: il canale Flatpak è rilevato da FLATPAK_ID o /.flatpak-info. Il controllo manuale indica il centro
software e non interroga GitHub. La notifica GitHub precedentemente salvata non viene mostrata come aggiornamento
Flatpak. Portable e sorgenti mantengono apertura della pagina release; automatismo disabilitato in Preferenze.
Non si confronta la versione GitHub con il commit o la versione installata dal remote Flatpak.

## Confronto template

[V] Letti `app-template/template/src/sample_app/update_dialog.py`, `updates.py`, documenti filosofia e guida Qt
`qt-app-template/docs/dal-template-gtk.md`, sezione 8. Il GTK offre dialogo, download e avvio in thread, senza politica
persistente o protezione del progetto specifica dell'applicazione. Meridiana possedeva già il port Qt di questi
componenti e la verifica firma. Si mantiene il codice di firma esistente e si aggiunge il controller separato.
Il controller è il riferimento da adattare nel modello Qt: dipende da cfg, pool, notifica, controllo progetto e
persistenza forniti dalla finestra. Port nel modello coordinato dall'integratore per preservare modifiche utente.

## Verifiche

[V] Python `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`, Qt offscreen:
- `tests/nucleo/test_updates.py`: 13 prove superate, incluse firma, digest, dimensioni e annullamento.
- `tests/widget/test_update_dialog.py`: 6 prove superate, incluso riutilizzo del download dopo salvataggio.
- `tests/widget/test_update_policy.py`: 6 prove superate: persistenza, opt-in, progetto sporco prima e dopo download,
  Flatpak senza rete e rimozione notifica quando la versione è corrente.
- Ruff sui sei file cambiati: nessun rilievo.

[V] Foto offscreen `foto/aggiornamenti-20261029-dialog-R02.png` e `foto/aggiornamenti-20261029-privacy-R02.png`
ispezionate: testi leggibili, comando portable e opzione automatica disabilitata da sorgenti.
La foto R01 senza tema mostrava font incompleto e resta conservata; la prova valida usa `meridiana_look()`.

## Integrazione e limiti

Config: `auto_install_updates: bool = False`; `pending_update: dict = field(default_factory=dict)`.
Migrazione unica 21 -> 22 gestita dall'integratore. Collegare Privacy alla prima proprietà.
Creare `self.update_controller = UpdateController(self)` dopo `self.update_job = None`.
Delegare `_daily_update_check`, `check_updates`, `_update_answer` rispettivamente a `daily`, `check`, `answer`.
Al primo show chiamare `startup`, mantenendo il timer giornaliero Windows già esistente.

[V] Nessuna rete, chiave privata, installer reale, modifica dati utente o riavvio nei test. Restano all'integrazione
traduzioni e prova della finestra completa. L'effettiva sostituzione del pacchetto Windows e l'aggiornamento dal remote
Flatpak richiedono la prova nei rispettivi ambienti di distribuzione; non sono stati simulati come esito reale.

## Port nel modello Qt

[V] Aggiunti al modello Qt, senza toccare i tre file utente già modificati: `src/qtkit/update_policy.py`,
`tests/test_update_policy.py`, `docs/aggiornamenti-policy-R01.md`; raccordo in `docs/da-dove-viene.md`.
Il modulo è puro: confronto notifica persistente e consenso/canale/firma/progetto pulito, senza dipendenze
Meridiana o esecuzione di installer. Quattro prove mirate superate e Ruff mirato superato.
La funzione di decisione è anche disponibile in `meridiana.updates.automatic_install_allowed`.

[V] Il controllo manuale riporta in primo piano il download automatico già aperto, evitando un secondo dialogo
e una seconda installazione concorrente. La revoca del consenso durante il download blocca Setup.

[V] Modello Qt: suite completa 155 prove superate in 148,705 s e Ruff completo superato. Port committato e inviato
sul repository privato Qt con SHA `d3769a6`. I file utente `CLAUDE.md`, `README.md` e `docs/dal-template-gtk.md`
sono rimasti fuori dal commit. Nessuna modifica grafica al modello: fotografie galleria non rigenerate.

## Correzioni dopo revisione integratore

[V] Label automatismo ridotta a `Install signed updates automatically`; vincolo progetto salvato in nota separata
con wordWrap. Le quattro vecchie label dei servizi ampliavano già la pagina: titoli brevi e spiegazioni integrali
in etichette wordWrap eliminano anche quel vincolo. Foto offscreen a 360 e 600 pixel logici R04 ispezionate:
nessun testo tagliato, scrollbar orizzontale con massimo 0, contenuto utile rispettivamente 350 e 590 pixel.
Le R03 hanno sfondo trasparente; R04 compone lo scatto sul colore Window della palette per l'ispezione.

[V] Prova aggiuntiva: consenso revocato, retry rifiutato, consenso ripristinato e retry manuale consentito sullo
stesso download verificato, senza nuovo download. La guardia del controller torna positiva dopo il ripristino.
Nessun latch permanente. Test dialogo: 7 prove superate. Il modello Qt non è stato modificato per queste label.
[V] Dopo le correzioni: 7 prove policy, 7 prove dialogo e Ruff mirato superati. Le 13 prove core restano invariate.

## Correzione avvio Setup idempotente dopo revisione indipendente

[V] `UpdateDialog.start_requested` impedisce un secondo avvio dello stesso installer anche se arrivano un doppio
click, un callback duplicato o un richiamo rientrante. L'azione viene disabilitata prima del retry del download già
verificato e prima della chiamata a Setup. Un errore OSError nell'avvio rimuove il blocco e consente di riprovare.

[V] Nove test dialogo superati in 0,838 s e Ruff mirato superato. Le due nuove prove invocano soltanto callback in
memoria con un percorso segnaposto inerte: nessun eseguibile viene aperto, scaricato o avviato. Coprono revoca della
guardia seguita da retry, doppio click, callback duplicato/rientrante e ripresa dopo errore di avvio.
