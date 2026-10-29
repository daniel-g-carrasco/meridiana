# Note della producibilità nelle Verifiche: 29 ottobre 2026

Il test isolato `finestra.test_checks_views.ChecksOnTheViews.test_the_window_gives_the_panel_the_defaults_and_the_names` falliva: la nuova spiegazione sui moduli scollegati aveva 112 caratteri ed era usata interamente come titolo, oltre il limite di 90. La nota italiana è ancora più lunga.

`checks.py` ora assegna alle note lunghe della simulazione e del calcolo un titolo breve e conserva la nota integrale nel dettaglio. La nota sui moduli scollegati ha un titolo specifico; le altre hanno «Producibilità: note di calcolo». Livello, destinazione e spiegazione correttiva già presente restano gli stessi. Le note brevi conservano il proprio titolo. Il limite resta 90 e non cambiano geometria dell'interfaccia o regole del calcolo.

La nuova regressione verifica entrambe le sorgenti delle note, la conservazione integrale della spiegazione e del rimedio al clipping, il livello e il collegamento alla pagina Producibilità, il limite dei titoli e la conservazione delle note brevi.

Durante la prova è emerso che cinque test precedenti di `nucleo.test_checks.Gather` erano annidati accidentalmente dentro `_counts_cleared()`, dopo il suo `return`, e quindi mai scoperti. Spostati fuori classe i tre helper che interrompevano la classe, i cinque test sono tornati eseguibili. La loro fixture dell'inverter è stata aggiornata da `p_ac_kw=50` al contratto attuale `pac_total=50000`, senza cambiare le asserzioni.

Prove offscreen eseguite:

- Prima della correzione: test della finestra fallito sul titolo lungo; nuova regressione fallita perché le note mancavano dal dettaglio.
- Dopo la correzione: nuova regressione e test della finestra, 2 prove superate in 6,147 s.
- Dopo il ripristino dell'indentazione e della fixture: intero modulo mirato `nucleo.test_checks`, 30 prove superate in 0,613 s (24 già scoperte, 5 recuperate, 1 nuova).
- Ruff sui due file Python e `git diff --check`: superati.

Non è stata ripetuta la suite completa né eseguita alcuna installazione. Il pacchetto R12 precede questa correzione: occorre il successivo congelamento R13 per la verifica finale del binario.

Le due nuove stringhe richiedono la traduzione nel catalogo centrale, gestito dall'integratore: `Unconnected modules produce no energy` → `I moduli scollegati non producono energia`; `Production: calculation notes` → `Producibilità: note di calcolo`.

[V] L'integratore ha aggiunto le traduzioni prima del freeze R13; compilazione del catalogo e `msgfmt --check` superati.
