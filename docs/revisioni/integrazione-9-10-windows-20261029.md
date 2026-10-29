# Integrazione degli incarichi 9 e 10 su Windows

29/10/2026. Base Windows `9c3317f`, ramo Kimi `1e39c69`. R150 e R151.

## Revisione e correzioni

- [V] Backup SQLite: Windows rifiutava fsync sul descrittore aperto in sola lettura. Il file temporaneo del backup viene aperto in lettura e scrittura; le prove del registro esercitano creazione, commit e backup.
- [V] Le due varianti del formato 17 sono leggibili. Il formato 18 conserva `climate`, risorse incorporate, commessa e serie. La prova dedicata carica entrambe le rappresentazioni, risalva e riapre senza perdere dati. Il campione Windows v17 resta invariato.
- [V] Scansioni dell'indice serializzate e richieste accorpate: una scansione vecchia non termina dopo quella nuova sovrascrivendone la riservatezza. Le risposte cloud consultano anche lo stato attuale della commessa.
- [V] Gli alias cloud sono ripristinati solo per eseguire gli strumenti locali. La cronologia diretta al modello conserva gli alias. Coperto anche il percorso sincrono della conversazione.
- [V] I singoli progetti collegati al registro sono indicizzati anche senza una cartella collegata. Nessuna scansione dei file vicini implicita.
- [V] L'export/import JSON include le attività con scadenza, completamento e riferimenti. Anteprima, validazione, transazione e unione per id; i vecchi JSON senza attività non cancellano quelle locali.
- [V] La scheda di apertura e quella delle attività nascondono i suggerimenti durante la conferma. Le normali proposte di modifica conservano i suggerimenti già previsti da R197.
- [V] Le traduzioni Windows esistenti sono conservate, aggiungendo le voci nuove di Kimi. Catalogo compilato con il compilatore del repository.

## Ambito delle verifiche

Prove con dati inventati, piattaforma Qt offscreen su Windows, nessuna chiamata vera ai modelli. Le fotografie Wayland di Kimi sono incluse nei suoi rapporti; la fotografia di apertura chiara è stata anche ispezionata durante questa revisione. Non sono stati usati registri o commesse reali per le prove.

Gli esiti finali e l'aggiornamento delle cartelle sono registrati dopo la suite.

## Esito Windows

[V] Ruff, catalogo e diff check superati. Nucleo 862 prove (1 saltata), calcoli 193, formati 70 e widget 360 (1 saltata) superati. Gruppo finestra: 162 prove eseguite in 1.432,826 s, due fallimenti e un errore iniziali.

[V] L'errore del test di salvataggio dipendeva dalla firma del suo osservatore, rimasta a un solo argomento; aggiornato per inoltrare cache e profilo, tutte e tre le prove del modulo passano. La prova delle stringhe confrontava lo stato salvato mentre R196 incorporava il clima: la differenza esatta era `climate`, non le stringhe. Ora il campione incorpora già il clima offline, e il percorso passa senza indebolire le asserzioni su undo, dirty o stringatura.

[V] Resta aperta la prova di tempo del cambio tema: 1,381 s contro il limite di 1 s nel giro completo. Ripetuta sulla versione precedente `9c3317f`, senza l'integrazione Kimi, fallisce anch'essa (1,166 s). Non è dichiarata verde e il limite non è stato allargato. Sarà rivalutata nel successivo allineamento grafico. Il test della relazione indicato nel precedente crash è passato in questa esecuzione; non è una prova che il vecchio crash sia risolto.

Le modifiche locali delle selectbox sono conservate separatamente nei due checkout. Copia preventiva in `C:\Users\Grasso\dev\meridiana-backup-integrazione-20261029-135939`.
