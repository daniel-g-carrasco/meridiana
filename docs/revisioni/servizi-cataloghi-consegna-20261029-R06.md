# Servizi e cataloghi: consegna R06

Specifica: R235-R240, piano `docs/superpowers/plans/2026-10-29-servizi-cataloghi-meridio.md`.
Base bf0767b. R241 della tranche precedente resta verificata; questa consegna conserva il pacchetto R05.

## Funzioni

Aggiornamenti firmati Windows opt-in, avviso conservato e verifica di progetto pulito anche dopo il download;
revoca del consenso e retry senza avviare due installatori. Flatpak segue il proprio canale di distribuzione:
non si confronta un bundle con la versione GitHub. Allegati PDF/testo estratti localmente, consenso cloud per
ogni invio anche della cronologia, strumenti disattivati durante l’analisi di documenti. Catalogo personale
con dati essenziali, fonte, confronto e blocco delle incoerenze; le schede proposte sono riviste prima di salvarle.

Accumulo in Impianto: AC/DC, compatibilità degli esatti modelli, limiti e quantità; la configurazione è
annullabile. Il bilancio resta equivalente AC: non è una simulazione del recupero di clipping tramite batteria DC.
Segnalazioni con anteprima e diagnostica scelta, invio deliberato nel browser. Tour con invito, navigazione reale,
sospensione/ripresa e richiamo dalla chat senza modello. Configurazione migrata da 21 a 22, progetto ancora 20.

## Revisione incrociata

Sono stati riprodotti e corretti: reinvio dei documenti storici senza nuovo consenso, array/tabelle MB0 e
LUNA rifiutati dall’editor, attestazioni di verifica ereditate dopo modifica personale, calcolo DC con limiti
mancanti, avvio duplicato dell’installer al retry, attributo `window` del tour che nascondeva il metodo Qt.
La diagnostica della segnalazione è stata collegata alla GUI con scelta esplicita e anteprima redatta.
Le riletture mirate dei revisori chiudono i difetti dei rispettivi ambiti. La suite integrata ha inoltre trovato
e corretto i tre tool non inclusi negli schemi inviati al modello, i campi accumulo mancanti nelle impostazioni
tipizzate e il minimo del dock di Meridio che impediva di nascondere i suggerimenti dopo l’aggiunta degli allegati.
Il test finestra originale e 30 prove widget passano dopo la correzione del dock, senza cambiare la soglia.

## Limiti dichiarati

- R238: audit strutturale di 24.262 record, non verifica di tutte le schede tecniche originali. 34 campi
  Huawei riverificati su fonti primarie; quattro moduli CEC incoerenti segnalati e bloccati nella selezione.
- Nessun OCR negli allegati, massimo 40 pagine/10 MB per file e 60.000 caratteri totali; nessuna prova con API
  a pagamento. L’efficacia di estrazione dei singoli modelli AI non è certificata.
- Campi personali avanzati in JSON; una scheda personale è dichiarata, non automaticamente verificata.
- DC: nessun recupero di clipping, nessuna simulazione dei controlli proprietari; dati indispensabili mancanti
  bloccano il calcolo anziché essere stimati.
- Aggiornamenti automatici applicativi per Windows installato; su Flatpak il canale è gestito dal sistema.
  Nessuna release pubblica o aggiornamento remoto è stato pubblicato implicitamente.

## Verifiche e consegna

Eseguiti i cinque gruppi della suite. Esiti conclusivi:

- Nucleo: 925 prove, una saltata, verde dopo i due difetti d’integrazione e l’aggiornamento delle fasi.
- Formati: 87 prove verdi, aspettative e fixture della configurazione 22 allineate.
- Calcoli: 272 prove verdi.
- Widget: 480 prove, una saltata, verdi; aggiunta successivamente una regressione sul dock e rieseguite
  30 prove widget insieme alla prova finestra originale, tutte verdi.
- Finestra: 183 prove nella suite completa. Tre esiti iniziali da risolvere: dock corretto e riverificato;
  aspettativa della toolbar aggiornata con Accumulo e intero percorso Impianto verde (15,913 s);
  soglia tema 1,044 s contro 1 s durante la suite. Lo stesso test sulla base bf0767b fallisce a 1,588 s;
  sul candidato, a compressione terminata, passa con soglia invariata e controlli immagini nei due temi.
  Nessuna soglia allentata e nessun test saltato per ottenere l’esito.
- Ruff completo, diff check e GNU msgfmt --check --check-format senza errori.

I log iniziali sono conservati. I soli gruppi inizialmente rossi e i percorsi interessati dalle correzioni sono
stati ripetuti; non è stata rilanciata l’intera suite dopo ogni ritocco. Il tempo del cambio tema resta sensibile
al carico: la prova finale positiva non è una garanzia inferiore a un secondo sotto qualunque carico.

Template Qt acd4ab3108d3c69850a7b87192885c1d69e0efc1: 23 mappature principali e una tabelle verificate.
Portati politica comune aggiornamenti e GuideCard riusabile; mantenute le modifiche preesistenti dell’utente.
Foto dei flussi in foto/servizi-meridio-20261029-R06: offscreen, chiaro e scuro, ispezionate visivamente.

Pacchetti R06 costruiti dallo stesso freeze R17 di 353 file, SHA-256 del manifest
c19960fa2b64464a0e9498eed9ff48ec0e420d58a9e4494641a7e7957f8c79a3.
Windows portabile e installato: autotest Direct3D11 senza errori, installazione/disinstallazione isolate
verificate. Flatpak: autotest e undici prove aggiuntive, dipendenze, sorgenti, traduzioni e reimportazione
OSTree verificati. Anteprime locali; nessuna pubblicazione o tag impliciti.

Rapporti: pacchetti-windows-20261029-R06.md, pacchetto-flatpak-20261029-R06.md,
aggiornamenti-20261029-R01.md, allegati-catalogo-20261029-R01.md,
accumulo-audit-20261029-R01.md, accumulo-audit-review-20261029-R02.md e accumulo-settings-20261029-R03.md.
La ricevuta di integrazione e installazione finale viene aggiunta dopo il commit applicativo.
