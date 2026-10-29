# Completamento elettrico e consegna R05

La consegna R05 completa questa tranche di R198-R234 e comprende l'installazione Linux richiesta in R241.
Le nuove funzioni R235-R240 rimangono registrate in coda: aggiornamenti, allegati e cataloghi personali,
accumulo, audit dei dati, segnalazioni e visita guidata. Non sono presentate come già implementate.

## Modifiche applicative

- Curve I/V dei moduli collegati, coorti di celle, bypass, stringhe e MPPT; conversione e clipping per inverter.
  Moduli scollegati a zero, mantenendo distinto il dato nominale dell'hardware. Risultati nel CSV e nella relazione.
- Ricerca globale vincolata di inverter/stringhe/ottimizzatori, budget e cancellazione espliciti. I comandi di
  stringatura lavorano fuori dal thread grafico; le proposte di dimensionamento devono collegare tutti i moduli.
  Proponi e Completa possono applicare una parte verificata, segnalando quanti moduli rimangono scollegati.
  Stringhe non verificate e superamento della corrente comune non vengono applicati automaticamente.
- Gruppi fisici di uno/due moduli per ottimizzatore, modificabili e persistenti nello schema logico 20 del `.mer`.
  Correnti per MPPT, per connettore e comuni distinte, compresi i limiti condizionati documentati del Huawei MB0.
- Correzioni emerse in revisione: conservazione dell'hardware quando la proposta cambia solo le stringhe,
  tabelle opzionali incomplete, intestazioni CSV con separatori o ritorni a capo, titoli brevi nelle Verifiche.
- Risultato asincrono vecchio scartato anche quando il nuovo aggiornamento è già accodato ma non ancora partito.
  Riprodotto il caso concreto: un risultato senza layout stava cancellando la proposta mentre il layout era pronto.

Il criterio del dimensionamento preferisce meno inverter, meno modelli e rapporto DC/AC più vicino. Non è
un'ottimizzazione globale economica o dell'energia annuale. Le ipotesi fisiche restano visibili nel programma.

## Verifiche

Suite completa eseguita per gruppi, poi ripetizioni mirate sui difetti e sui test aggiornati:

| Gruppo | Esecuzione iniziale | Seguito |
|---|---|---|
| Nucleo | 888 test, superata, 1 saltato | modulo Verifiche: 30 superati, inclusi 5 test recuperati e 1 nuovo |
| Formati | 87 test, superata | schema 20 e gruppi fisici inclusi |
| Componenti grafici | 457 test, superata, 1 saltato | foto dei gruppi nei due temi e PDF reale ispezionati |
| Calcoli | 269 test, un difetto nel metadato della potenza nominale | corretta la causa: 272 test superati |
| Finestra | 178 test, 9 fallimenti | tutti i 9 percorsi superati nelle ripetizioni mirate; prestazione del tema variabile sotto carico |

Ripetizioni mirate: 6 regressioni asincrone e 2 percorsi Stringing superati (41,509 s), 3 EnergyPages,
1 PlantPhase (19,561 s), percorso Optimizers, glifi e titoli delle Verifiche superati.

La prova del cambio tema ha misurato 1,146 s contro la soglia di 1 s: problema prestazionale già presente
nel lotto precedente, non nascosto cambiando la soglia. La ripetizione isolata finale, dopo le build,
passa con la stessa soglia (1 test, 16,345 s complessivi; log `build/completion-final-theme-isolated-R02.log`).
Resta un segnale di variabilità sotto carico, non una correzione prestazionale dichiarata. Le altre prove hanno distinto regressioni reali
da fixture senza collegamenti o con potenza incompatibile: le asserzioni elettriche non sono state indebolite.
Il test positivo SolarEdge ora usa un campo compatibile con il limite DC del modello e controlla che la scelta
degli ottimizzatori sia salvata e ripristinata da Annulla.

Ruff sui sorgenti, test e strumenti: superato. Traduzioni nuove tutte presenti; compilazione e `msgfmt --check`
superati. Il modello numerico è confrontato con pvlib e con casi analitici, non con una campagna di misure reali.
Campione annuale senza ostacoli: 6,72 s; con camino: 116,15 s. La cancellazione viene controllata fra blocchi
di 48 ore illuminate. Non si dichiara verificata la scalabilità a migliaia di moduli con molti ostacoli.

## Congelamento e pacchetti

Freeze tecnico Windows R14, 340 file applicativi/risorse: manifest
`build/source-manifest-20261029-R14.json`, SHA256
`a3c59ea8c62c716aa485dfdbe0c6129a8d45a7f028d08c6aec4811153c18e795`.
La corrispondente copia Linux è `source-r08`; i due script desktop sono normalizzati a LF soltanto nella copia.
I cataloghi gettext possono avere byte diversi tra compilatori: le voci tradotte sono confrontate semanticamente.
R11-R13 e gli snapshot Linux precedenti sono intermedi di verifica, non i pacchetti della consegna.

Commit applicativo `10da2fc`, integrato con fast-forward nelle cartelle `meridiana` e `meridiana-lavoro`.
Catalogo italiano ricompilato nella cartella di avvio; 339 file runtime/risorse confrontati senza differenze
normalizzando i fine riga. L'icona ICO generata esclusa dal confronto appartiene solo alla preparazione dei pacchetti.

Pacchetti in `dist/packages-20261029-R05`, con `package-receipt-R05.json` e `SHA256SUMS.txt`:

| Artefatto | Byte | SHA256 |
|---|---:|---|
| Setup Windows | 155243287 | `9dfcd52512c90d7a343a54708e2d961ba80b4dd6a5ee990bcf807c1cd1b87eac` |
| ZIP Windows | 218420119 | `adb123f6168412af00537ac0104d9c46cfc787af0ce671b81c7e9bad25c83b60` |
| Flatpak Linux | 185441592 | `5b2377305aaf1352653a6f29f53b48ce3f8dfc644438fdd26e9eb1b2f53cffab` |

Setup installato, avviato e disinstallato in una cartella nuova: tutti i codici 0; Direct3D11 e primo frame
superati. Focus invariato, registro/associazioni/collegamenti ripristinati, dati conservati. Rapporto
`verifica-desktop-pacchetti-20261029-R05.md`. ZIP controllato con `7z t`; Flatpak verificato con import/fsck,
6 probe e self-test offscreen. Ricevute complete conservate accanto agli artefatti.
La distribuzione rimane una preview locale: nessun tag o release pubblica creati.

## Installazione sul laptop Linux

R05 installato via SSH su `fw13` (`lucciola`), a livello utente. SHA256 del file trasferito identico alla
ricevuta; commit installato `ccd091d302a7c2c60d8adf5d7647e4c1f37077536467b0a849d1c4eee46dadb4`,
runtime KDE 6.11 già disponibile. La voce applicazioni e l'associazione MIME sono esportate da Flatpak.

Il self-test Wayland standard passa cataloghi, calcolo, IFC e PDF, ma fallisce il primo frame: Niri assegna
921 pixel logici, sotto la soglia responsive di 1000; la finestra mostra la pianta e nasconde il 3D
(larghezza zero). La diagnosi registra che il renderer salta correttamente la vista non esposta.
Una sonda sul medesimo Flatpak attiva la modalità 3D tramite il metodo esistente: primo rendering
158,8 ms, immagine non vuota, self-test zero errori in 9,18 s; ruotando di 30 gradi l'immagine cambia.
Nessun driver, monitor o preferenza utente modificato. Il limite del self-test standard rimane documentato;
non viene presentato come un self-test standard completamente verde. Rapporto
`installazione-laptop-20261029-R05.md`, ricevute in `build/laptop-install-20261029-R05`.

Avvio dal menu applicazioni: Meridiana; oppure `flatpak run io.github.daniel_g_carrasco.meridiana`.

## Template condivisi

Caselle nelle tabelle e verifiche native nel template Qt `0b5d965`; la lezione sul risultato asincrono
precedente a un aggiornamento accodato è nel successivo `3c6ba3e7900b15e6ffabdfcb080c79002d74d2e1`.
La precondizione di visibilità nelle prove grafiche responsive è documentata nel successivo
`9a42824545ed4c80c7be8d8f0931831cb80e79bd`. I manifest Qt R04 e tabelle R05 verificano 21 + 1 mapping
contro quest’ultimo commit. La correzione dell'installer è riportata
anche nel template GTK `8a3691f29561826cb2dfbbab50032b02075792a7`. I commit sono pubblicati nei soli
repository privati dei template; le modifiche preesistenti di Daniel sono state conservate.

## Riferimenti di dettaglio

- `modello-elettrico-20261029-R02.md`: equazioni, fonti, convergenza, misure e limiti.
- `dimensionamento-globale-20261029-R02.md`: spazio di ricerca, prove indipendenti e limiti del criterio.
- `dati-elettrici-20261029-R02.md`: fonti del catalogo, gruppi, formato e comandi.
- `revisione-completamento-20261029-R02.md` e `verifiche-titoli-note-20261029-R01.md`: difetti riprodotti e correzioni.
- `verifica-desktop-pacchetti-20261029-R02.md`: popup Windows nativi, GPU, installazioni isolate e template.
- `foto/completamento-20261029/relazione-R02/ombra-due-inverter.pdf`: relazione del caso sintetico con camino,
  con produzione e clipping distinti per inverter; pagina 4 renderizzata e ispezionata.
