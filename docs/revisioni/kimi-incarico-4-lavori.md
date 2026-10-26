# Incarico 4: lavori svolti

Data: 26/10/2026. Ramo `kimi-incarico-4`, da `origin/lavoro`. Interprete e dipendenze: `~/fvtest/venv314`, con
`PYTHONPATH=src` verificato su `meridiana.__file__`.

## Punto 1, R142

Commit: `756ae8d`, «Show the live target and state while drawing a string (R142)».

### Che cosa è cambiato

- Sulla pianta, una `ChipItem` con `swatch=True` segue l'ultimo modulo scelto. Prima del primo modulo segue il
  puntatore. Resta dentro la vista e mostra inverter, marca, modello, ingresso, numero di moduli, intervallo ammesso,
  stato e tasti per chiudere, tornare indietro e annullare.
- Lo stato usa gli stessi simboli disegnati delle etichette delle stringhe: moduli mancanti o in eccesso, conteggio
  giusto. Per SolarEdge mostra conteggio e intervallo senza giudizio.
- La stringa in disegno conserva il colore che avrà una volta chiusa. Il movimento del mouse aggiorna solo la linea
  provvisoria e la posizione della pillola, non la scena intera.
- Nell'elenco di destra l'ingresso interessato è evidenziato. L'evidenziazione e la pillola spariscono con Invio,
  doppio clic, Esc o uscita dalla stringatura. La striscia della pagina mostra lo stesso inverter e lo stesso ingresso.
- La patch non salvata dell'incarico 3 è stata ripresa solo per l'identificazione dell'inverter nella striscia. Il resto
  è stato rifatto per avere testo completo, stato, pillola, evidenziazione e prove richieste.

### Prove

- [V] Prima: le nuove prove erano rosse perché mancavano `ACTIVE_ROLE`, `draft_chip` e l'evidenziazione. Dopo: testo e
  simbolo verificati con 0, 1, minimo e massimo+1 moduli; intervallo sempre presente; pillola ancorata all'ultimo
  modulo e contenuta nella vista; ottimizzatori senza giudizio; ingresso evidenziato e poi ripulito con Invio ed Esc;
  nessun dialogo. Una spia verifica zero chiamate a `_draw_wiring` e `_draw_draft` durante il movimento del mouse.
- [V] Gruppo `widget`: 308 prove, 1 saltata. Viaggio `Stringing` e caso `Optimizers` verdi.
- [V] `ruff check src tests tools`, `compile_po.py` e `msgfmt --check` puliti. Nessuna voce fuzzy.

### Fotografie

- `docs/revisioni/foto/kimi4-r142-prima.png`
- `docs/revisioni/foto/kimi4-r142-dopo.png`

Progetto `_fixtures.capannone`, offscreen, 1400 x 960. Le foto sono generate da
`tools/kimi4_photos.py r142` e sono state guardate.

### Da provare sullo schermo

Disegnare una stringa su due inverter e ingressi diversi; leggere la pillola a scala 1 e 2, in chiaro e scuro; arrivare
al minimo e superare il massimo; chiudere con Invio e doppio clic, annullare con Esc; ripetere con SolarEdge. Resta da
giudicare il reale gesto del mouse, che qui è inviato da Qt in offscreen.

### Non fatto

Nessuna modifica a regole elettriche, proposta automatica, posa o formato del progetto. Nessuna prova sullo schermo
reale, per non aprire la finestra sul computer di Daniel.

## Punto 2, R134

Commit: questo commit, «Separate overlapping string jumps into screen lanes (R134)».

### Scelta e che cosa è cambiato

- `string_paths.Router.legs_together` calcola insieme i percorsi, senza Qt. I salti che condividono vertici o tratti
  ricevono corsie con distanza derivata da 6 pixel logici sullo schermo, quindi coerente a ogni ingrandimento.
- La corsia sposta solo i punti intermedi e sceglie attorno a ogni vertice la direzione libera più vicina al lato
  assegnato. Se il semplice spostamento attraversa un modulo o un altro salto, A* prova vertici diversi trattando i
  salti già assegnati come barriere. Ogni percorso accettato è validato contro i moduli veri, non solo quelli ristretti.
- Una stringa sola e le stringhe che non si incontrano conservano esattamente i percorsi precedenti. Tutti i salti di
  una stringa usano la stessa corsia.
- Sulle file completamente attaccate può non esistere spazio geometrico libero. In quel caso il percorso resta fuori
  dai moduli e la pianta usa un passo del tratteggio diverso per ogni corsia, invece di fingere una separazione che
  entrerebbe nei moduli.
- `plan.py` passa alle linee i percorsi e le corsie calcolati dal nucleo. Colori e riempimenti restano quelli di R117.

### Prove

- [V] Prima: tre stringhe disgiunte attorno allo stesso modulo avevano distanza zero. Le tre prove finali, rieseguite
  senza `legs_together`, hanno prodotto 5 errori su 3 test e sottocasi.
- [V] Dopo: `nucleo/test_string_paths.py`, 11 prove verdi. Tre stringhe non hanno vertici né tratti in comune; distanza
  minima almeno 3 px alle scale 10 e 25; nessun salto entra in un modulo; estremi invariati; file attaccate senza
  ingresso nei moduli e con tre corsie di tratteggio; una stringa e stringhe separate invariate; 8.000 moduli con
  percorso identico e sotto la soglia di 3 secondi.
- [V] Viaggi `Stringing` e `Optimizers` verdi. Fotografia completa in circa 5 secondi inclusi avvio e progetto, dopo
  avere scartato punti extra di A* che portavano lo stesso giro a circa 20 secondi.

### Fotografie

- `docs/revisioni/foto/kimi4-r134-prima.png`
- `docs/revisioni/foto/kimi4-r134-dopo.png`

Il triangolo è ricostruito sul capannone con tre stringhe disgiunte attorno allo stesso modulo centrale. Comando:
`tools/kimi4_photos.py r134`. Entrambe le immagini sono state guardate.

### Da provare sullo schermo

Rifare il triangolo con tre stringhe, cambiare ingrandimento due o più volte, selezionare le stringhe e verificare che
il modulo saltato resti leggibile. Ripetere su file distanziate e attaccate, in chiaro e scuro, valutando la distinzione
dei tratteggi sullo schermo reale.

### Non fatto

Nessuna modifica a regole elettriche o al formato. Il ripiego storico dei salti oltre 120 moduli resta invariato. Dove
non c'è spazio fra moduli non è stata forzata una distanza geometrica impossibile: vale il tratteggio distinto. Nessuna
fotografia sullo schermo reale.

## Verifica finale

- [V] Suite completa, un processo per gruppo: nucleo 790, calcoli 175, formati 59, esterni 6 con 6 saltati, widget 308
  con 1 saltato, finestra 129. Totale: 1.467 prove, 5 saltate, nessun fallimento.
- [V] `python -m ruff check src tests tools`: tutti i controlli superati.
- [V] `tools/compile_po.py` e `msgfmt --check po/it.po`: puliti; nessuna voce fuzzy.
- [V] `git diff --check`: pulito. Nessun push, merge, rebase o modifica ad altri rami.
