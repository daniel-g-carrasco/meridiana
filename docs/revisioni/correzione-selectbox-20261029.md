# Selectbox: ultima opzione coperta, 29 ottobre 2026

Richiesta di Daniel: eliminare la fascia di scorrimento che copre l'ultima opzione anche in elenchi di quattro voci. Difetto osservato in Quotario e Meridiana.

## Causa riprodotta

[V] Windows, Python 3.12 e Qt 6.12.0, piattaforma `offscreen`. Il popup viene costruito prima che la combobox riceva il focus. Qt memorizza due spaziatori da 3 px; con il focus il foglio di stile riduce il padding a 2 px, compensando il bordo più spesso del controllo. `showPopup()` misura quindi con 2 + 2 px, mentre gli spaziatori occupano ancora 3 + 3 px.

Quattro righe da 24 px richiedono una viewport da 96 px. I 2 px mancanti provocano l'apparizione dello scroller inferiore da 10 px: la viewport scende a 84 px e taglia l'ultima voce. La riproduzione mostra lo stesso sintomo della schermata di Daniel. Togliendo il focus il difetto scompare.

Il percorso è verificabile nel [sorgente Qt 6.12.0 di QComboBox](https://github.com/qt/qtbase/blob/v6.12.0/src/widgets/widgets/qcombobox.cpp), funzioni `updateTopBottomMargin()` e `showPopup()`.

## Correzione

`src/meridiana/ui/popups.py`: al focus della combobox, il contenitore ancora nascosto riceve un evento `StyleChange`. Qt aggiorna le proprie metriche prima di misurare e posizionare il popup. Non si impongono altezze, non si nascondono gli scroller e non si cambiano i colori o le dimensioni dei controlli.

Lo stesso handler è stato applicato a Quotario, al template Qt e ai checkout `meridiana` e `meridiana-lavoro`. I moduli preesistenti sono conservati: il porting riguarda soltanto l'import di `QComboBox`, la registrazione di `FocusIn` e il relativo handler.

## Verifiche

[V] Prima della correzione tre dei cinque nuovi test fallivano, riproducendo la viewport insufficiente e l'ultima voce non cliccabile. Dopo la correzione:

- cinque test di `tests/widget/test_combo_popups.py` superati in entrambi i checkout: quattro opzioni interamente visibili, clic sull'ultima riga, riapertura con ultima voce selezionata, cambio tema, posizione vicino al bordo inferiore dello schermo;
- cento opzioni continuano a scorrere, con popup limitato all'altezza disponibile; Fine e Invio raggiungono e selezionano l'ultima;
- due test esistenti di `tests/widget/test_tooltips.py` superati in entrambi i checkout;
- lint `ruff check --select F,E9,B` dei due file di codice e prove superato;
- Quotario e template: stessi cinque test superati; Quotario verificato anche al 125% e 200%, oltre alla combobox reale della finestra principale.

Per `meridiana-lavoro`, privo di `.venv` locale, è stato usato l'interprete di `meridiana/.venv` con cartella di lavoro e sorgenti del checkout `meridiana-lavoro`.

Tutte le prove sono offscreen. [V] Anche su Linux/WSL sono passate le sette prove popup/tooltip, in 2,969 s.
La suite completa Windows ha raccolto 1.593 prove, ma si è interrotta con un access violation durante
finestra.test_phase_bar.ReportAndPlant.test_the_report_phase_shows_its_pages_and_its_choices_are_edits_undone_with_ctrl_z.
Il log contiene anche un errore del renderer Qt Quick senza RHI e un errore di accesso alla cache temporanea:
non sono stati diagnosticati come conseguenze della correzione dei popup. Non si dichiara verde la suite completa.
Log locale ignorato da Git: build/ux-combo-diagnostic-20261029.log.
Nessuna verifica sullo schermo reale, nessun commit o push eseguito.
