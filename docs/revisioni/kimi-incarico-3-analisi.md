# Incarico 3: analisi prima delle correzioni

Data: 25/10/2026. Legenda: [V] verificato con una prova sul codice, [I] dedotto o da verificare sullo schermo.

## 1. R147: selezione di un modulo e della sua fila

### Il percorso prima della correzione

**Pianta.** `PlanView._pick` cerca nell'ordine esclusione, modulo, sottocampo, falda, edificio. Il modulo viene preso solo se il punto è dentro il quadrilatero. Non c'è tolleranza intorno al suo bordo. Il primo clic sinistro chiama `moduleClicked`: la sessione seleziona il sottocampo e ricorda il modulo. Un secondo clic su un modulo della stessa fila seleziona la fila. Un clic successivo torna al modulo. È il modello a due livelli deciso con R9 e il compito 16c.

Il doppio clic segue la sequenza di Qt `press`, `release`, `press`, `double click`, `release`. Sulla seconda pressione la pianta seleziona quindi la fila; poi `_module_double_clicked` sceglie la fila se contiene più moduli e ruota di 90° solo un modulo esploso. Non c'è quindi un conflitto da correggere fra doppio clic e rotazione. [V: `widget.test_plan.PlanNavigation.test_a_double_tap_selects_the_row_and_still_reports_the_double_click`, già verde prima della modifica; `finestra.test_window.RowsByHand` per la rotazione del modulo esploso]

**Vista 3D.** QML chiama `view.pick(x, y)` e il raggio restituisce il modulo o l'edificio sotto il puntatore. `Navigator` emette la selezione al rilascio se il movimento non ha superato la soglia del clic. La finestra selezionava però sempre il modulo: il secondo clic non prendeva la fila e l'anteprima non la mostrava. Il suolo rimanda al picking geometrico della pianta. [V: lettura di `Scene.qml`, `view3d.Backend._do`, `MainWindow._module_picked_3d`; nuova prova 3D rossa prima della modifica]

**Mouse e touchpad.** Tap-to-click e clic fisico arrivano a `PlanView` come `QMouseEvent` con tasto sinistro; anche il doppio tocco segue la sequenza del doppio clic. In AutoCAD il tasto sinistro può precedere la combinazione sinistro+destro: viene trattenuto per 150 ms. Un tap breve agisce al rilascio, una pressione lunga agisce allo scadere del timer. [V: `PlanView.mousePressEvent`, `_left_now`, `mouseReleaseEvent`; prove con `QMouseEvent`] La consegna effettiva di libinput su Wayland resta [I] fino alla prova sul portatile.

### Tolleranze prima, in pixel logici

| Gesto | Pianta | Vista 3D | A scala 2, pixel fisici |
|---|---:|---:|---:|
| Modulo sotto il puntatore | 0, solo dentro il poligono | raggio sul poligono, nessuna espansione | 0 |
| Movimento ancora considerato clic | 4 in somma sugli assi | 4 in somma sugli assi | 8 |
| Vertice o estremo della fila | 8 | 8 per il gizmo | 16 |
| Lato selezionato | 14 | non applicabile | 28 |
| Primo punto per chiudere un contorno | 10 | non applicabile | 20 |
| Attesa del clic sinistro prima di agire | 150 ms | non applicabile | invariata |

Le posizioni dei `QMouseEvent` e le misure di `QGraphicsView` sono in pixel logici. Il fattore di scala non dimezza queste tolleranze sullo schermo. [V: stesse prove eseguite con `QT_SCALE_FACTOR=2`]

### Perché il touchpad rende il difetto frequente

Un modulo lontano è un bersaglio di pochi pixel. Il dito produce piccoli spostamenti mentre preme o solleva, soprattutto con clic fisico. Il picking esatto trasforma quindi un tentativo sul bordo in una selezione del sottocampo. Il secondo gesto sembra non rispondere perché nel frattempo è cambiato il livello selezionato. Mancano inoltre un'uscita con Esc e una spiegazione del secondo clic. Nella 3D il secondo clic non aveva proprio lo stesso risultato della pianta. [V per i percorsi del codice e i casi riprodotti; [I] per la frequenza sul dispositivo reale]

### Modello attuato

Resta la decisione R9, senza introdurre un ritardo generale né un terzo clic con un altro significato:

1. il clic prende l'oggetto più piccolo sotto il puntatore;
2. in pianta un modulo può essere preso entro 6 px logici dal bordo, scegliendo il più vicino; a scala 2 sono 12 px fisici;
3. un secondo clic sulla stessa fila seleziona la fila, in pianta e nella 3D;
4. un clic su un modulo quando la fila è già selezionata torna al modulo;
5. Esc passa da fila o modulo al sottocampo, poi all'edificio e infine al sito;
6. il passaggio del puntatore e la barra di stato dicono quale livello verrà preso o è selezionato.

La stringatura conserva il suo picking esatto, perché durante un trascinamento una tolleranza potrebbe prendere un modulo vicino non voluto. Un'esclusione sotto il puntatore continua ad avere precedenza su un modulo vicino. Le coordinate e i dati del progetto non cambiano.

### Prove

Prima della correzione, con il progetto `_fixtures.capannone`:

- tocco a 3 px logici dal bordo: rosso, nessun modulo selezionato;
- due tocchi e Esc dalla fila: rosso, la selezione resta sulla fila;
- Esc dal modulo: rosso, il modulo resta selezionato;
- secondo clic e anteprima nella 3D: rosso, resta il modulo invece della fila;
- doppio tocco su una fila: verde già prima;
- a 7 px logici dal bordo non viene selezionato il modulo, per controllare anche il limite esterno.

Dopo: 6 prove di `widget.test_plan.PlanNavigation` verdi sia a scala 1 sia con `QT_SCALE_FACTOR=2`; 3 prove di `finestra.test_selection_3d` verdi. Il rendering 3D resta non valutabile offscreen: le prove controllano eventi, selezione e geometria, non i pixel della scena.

### Da provare sul portatile

Con il progetto di prova, non con quelli di Daniel:

1. avvicinarsi e allontanarsi dal bordo di un modulo e verificare il contorno di anteprima;
2. fare un tap e un clic fisico sullo stesso modulo, poi il secondo sulla stessa fila;
3. ripetere il doppio tocco su una fila e su un modulo esploso;
4. premere Esc da fila, modulo e sottocampo, in pianta e nella 3D;
5. ripetere a scala 2 controllando che il margine di 6 px logici sia comodo e non prenda il modulo vicino per errore.

### Nota sul controllo di base

La prima suite del nucleo ha eseguito 786 prove e si è fermata su `test_no_em_dash_anywhere_the_user_reads`: il commit di base conteneva un trattino lungo U+2014 nella docstring di `ui/symbols.py`, file non toccato da questo punto. È sostituito dal segno meno U+2212, senza cambiare i simboli disegnati. La prova è ripetuta prima del commit.

## 2. R141 e R144: «non risponde» su Linux

### Che cosa è verificato

**«Proponi» non calcola al primo tocco.** Il comando `strings_auto` ha un `QMenu` con quattro strategie. Il `QToolButton` della barra usa `InstantPopup`: un solo clic, e quindi un tap che Qt consegna come clic, apre il menu senza proporre alcuna stringa. La proposta parte solo scegliendo una strategia. Il menu appartiene alla `MainWindow`, quindi ha un genitore Qt; il genitore transitorio Wayland e la posizione sullo schermo non sono valutabili con la piattaforma offscreen. [V: `window.py:939-957`, `phasebar.py:153-167`, nuova prova `test_propose_is_a_menu_opened_by_one_click_and_sizing_says_what_it_did`]

**Il dimensionamento risponde a parole.** Con un inverter nel catalogo del progetto calcola quanti esemplari servono e scrive modello, quantità e rapporto DC/AC nella barra di stato. Senza inverter non ne sceglie uno dal catalogo: conserva il dimensionamento astratto e lo dice nella stessa barra. Il messaggio resta per sei secondi. [V: `window.py:3484-3503`, nuova prova citata]

**La Producibilità riparte dopo una modifica.** Una modifica geometrica segna l'anno come da aggiornare, mantiene leggibili i vecchi valori in grigio e, al ritorno della posa, avvia il timer di 500 ms. Al ritorno del calcolo i valori e il titolo della fase tornano puliti. [V: `StaleValues.test_the_values_are_greyed_while_the_project_has_changed_and_clean_with_the_new_year_or_an_undo`, già presente e rieseguita]

### Ipotesi ancora da distinguere sul portatile

1. **Dopo un tap su «Proponi» non è stata scelta una strategia.** Prova: compare il menu? Se sì, scegliere «avanti e indietro» e guardare la barra di stato. Questo spiega l'assenza di stringhe senza un guasto del calcolo. [I]
2. **Il menu si apre fuori schermo o senza genitore transitorio su Niri.** Prova: ripetere con la finestra non massimizzata e poi con Calcola > Proponi le stringhe. Se dal menu tradizionale funziona e dalla barra no, il difetto è del popup Wayland, non della stringatura. [I]
3. **L'esito del dimensionamento passa inosservato.** Prova: osservare la barra di stato subito dopo il comando e la riga degli inverter a destra. Il messaggio c'è, ma non dice quanto dura né apre un riepilogo. [V per il messaggio, I per la percezione]
4. **La Producibilità mostra un anno vecchio o nessun anno mentre posa e calcolo sono in corso.** Prova: attendere la fine delle indicazioni di calcolo e controllare il puntino «·» accanto a Producibilità. Se resta, premere F5. Se il progetto non ha moduli posati, il risultato vuoto è atteso. [I]
5. **Un progetto diverso dal progetto di prova produce un errore.** Prova: leggere il campo sotto il modulo e il registro; non attribuire a Wayland un errore dei dati. [I]

Nessuna correzione è fatta in questo punto: il comportamento del menu e dell'aggiornamento è confermato, il sintomo sullo schermo Wayland non è riprodotto. La scelta della marca e un esito più esplicito del dimensionamento sono il punto 7.

### Da provare sullo schermo

1. Un tap su «Proponi»: fotografare dove compare il menu e scegliere una strategia.
2. Ripetere dal menu Calcola e con la finestra ridotta.
3. Premere «Dimensiona l'inverter da solo»: controllare subito la barra di stato e il pannello di destra.
4. Cambiare l'altezza dell'edificio: il puntino su Producibilità deve comparire, i valori restare leggibili in grigio e aggiornarsi da soli.
