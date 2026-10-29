# Tabelle condivise: allineamento del 29/10/2026
Daniel ha approvato le proposte grafiche emerse in Quotario e il loro trasferimento nel template Qt, ricordando che Meridiana usa lo stesso stile.

## Modifica selettiva
- Nuovo src/meridiana/ui/shared_tables.py dal modulo src/qtkit/tables.py del template, commit 9acb7a857adecdbe57874282c48e84e21ee463c7.
- L'import di theme_colors è adattato al pacchetto superiore; il resto del modulo coincide con l'origine.
- Due righe in MainWindow.__init__ installano il trattamento sulle tabelle già costruite.
- project-tree, checks-tree, viste a una colonna e viste con testata nascosta sono escluse. I delegate specializzati restano.
- I dialoghi costruiti dopo la finestra principale richiedono ancora un'applicazione esplicita.
- I manifest template-sync-qt-tables.json e la revisione _R01 registrano trasformazione, hash e origine. Nessun aggiornamento cieco all'avvio.

## Verifiche
[V] Due test widget dedicati superati in entrambe le copie Windows; verificano esclusioni, idempotenza, delegate, cifre tabulari e cambio chiaro/scuro. Ruff pulito su entrambe le copie.
La suite generale Windows della copia principale ha superato 1.588 test (8 saltati) in 963,45 s; il rapporto di sviluppo 4 è in Quotario. Le due copie partivano da 3c6bf8d e hanno la medesima modifica selettiva.
Il modulo canonico ha dieci test dedicati superati anche su Linux/WSL. La suite completa di Meridiana su Linux non è stata eseguita in questa sessione.

Nessuna finestra sullo schermo di Daniel, nessun progetto utente aperto o modificato, nessun push e nessun rilascio.
