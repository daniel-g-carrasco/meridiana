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

Le ricevute di creazione, integrità, installazione e avvio saranno collegate dopo il completamento dei pacchetti.
La distribuzione rimane una preview locale: nessun tag o release pubblica creati.

## Template condivisi

Caselle nelle tabelle e verifiche native nel template Qt `0b5d965`; la lezione sul risultato asincrono
precedente a un aggiornamento accodato è nel successivo `3c6ba3e7900b15e6ffabdfcb080c79002d74d2e1`.
I manifest Qt R04 e tabelle R05 verificano 21 + 1 mapping. La correzione dell'installer è riportata
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
