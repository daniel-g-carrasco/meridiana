# Esito incarico 23: touchpad, Spazio e mappa da lontano, 28/10/2026

## Punto 1: il registro degli eventi

- [V] `MERIDIANA_INPUT_LOG=<file>` attiva `ui/input_log.py`. Scrive una riga JSON per ogni rotella, gesto, tasto e
  mouse ricevuto dalla pianta e dalla 3D. I campi comprendono tipo, ora UTC, `angleDelta`, `pixelDelta`, fase,
  modificatori, sorgente, dispositivo, posizione locale e globale. Per i tasti registra anche testo, conteggio e
  ripetizione automatica; per i gesti, tipo e valore; per il mouse, pulsante e pulsanti premuti.
- [V] Il filtro osserva sia il viewport della pianta sia la vista che riceve la tastiera, e la `View3D`. Non cambia
  l'accettazione degli eventi. Senza la variabile non crea file né filtri.
- [V] La guida per Daniel è in [docs/registro-input.md](../registro-input.md): chiusura del programma, avvio da
  PowerShell, gesti da ripetere, percorso `%TEMP%\meridiana-input.jsonl`, invio del file e rimozione della variabile.
- [V] Le prove `tests/widget/test_input_log.py` controllano i campi grezzi e i destinatari reali degli eventi in
  entrambe le viste.

## Punto 2: R189, touchpad e pizzico

**Causa riprodotta.** Su Windows gli eventi del touchpad di precisione hanno `angleDelta` e spesso nessuna fase. La
pianta usava solo la componente verticale come zoom: un evento `(120, 60)` cambiava la scala invece di spostare la
vista. La 3D inoltrava lo stesso evento alla scena come rotella. Inoltre Maiusc+due dita e il gesto nativo ruotavano.
[V: riproduzione prima della correzione e nuove prove Qt]

`navigation.wheel_action` classifica ora gli eventi una sola volta per pianta e 3D:

- scorrimento con fasi e `pixelDelta` su Wayland, oppure `angleDelta` sintetizzato dal sistema su Windows: pan;
- `angleDelta.x` non nullo: pan, quindi anche lo scorrimento orizzontale non diventa zoom;
- Ctrl: pizzico, con passi da `angleDelta.y / 120` o `pixelDelta.y / 60`;
- rotella verticale di un dispositivo reale senza fase: zoom del mouse, come prima.

Gli `angleDelta` di scorrimento valgono mezzo pixel per unità, senza accumuli o cambi di asse. Il pizzico nativo e
quello Ctrl+rotella conservano il punto di scena sotto il cursore. I gesti nativi di rotazione vengono accettati e
ignorati. Maiusc+due dita non orbita più. La rotazione della pianta resta nei comandi di R174 e R183.

### Sequenze Windows simulate

1. `angleDelta=(120, 60)`, `pixelDelta=(0, 0)`, `NoScrollPhase`, `MouseEventSynthesizedBySystem`: pan di 60 x 30
   pixel, scala invariata.
2. `angleDelta=(0, 60)`, stessa sorgente: pan verticale, senza zoom.
3. Ctrl con `angleDelta=(0, 60)` a `(300, 250)`: mezzo passo di zoom, punto sotto il cursore stabile.
4. `ZoomNativeGesture=0,25` a `(300, 250)`: ingrandimento di 1,25, punto stabile.
5. `RotateNativeGesture` di 17° nella pianta e 12° nella 3D, e Maiusc+scorrimento: nessuna rotazione.
6. Rotella fisica con `MouseEventNotSynthesized`, `angleDelta=(0, 120)`: zoom come prima.

### Sequenze Wayland simulate

1. `ScrollBegin` con `pixelDelta=(4, -3)`, `ScrollUpdate` con `(6, -2)`, `ScrollEnd` con `(0, 0)`: pan complessivo
   di 10 x -5 pixel, scala invariata.
2. `ScrollUpdate` con `pixelDelta=(0, 30)` e Ctrl: mezzo passo di zoom attorno al cursore.
3. Pizzico nativo sulla 3D: il punto scelto resta alle stesse coordinate proiettate entro 10⁻⁶ pixel.

Le prove sono in `tests/widget/test_plan.py`, `test_plan_aids.py` e `test_view3d_navigation.py`. Erano rosse prima
della correzione e sono verdi dopo. La vecchia prova che imponeva la rotazione nativa ora verifica il comando
`rotate_view`, conservando i controlli su coordinate e bussola.

## Punto 3: R190, Spazio con il movimento

**Causa riprodotta.** Spazio mostrava la mano ma armava soltanto Spazio+tasto sinistro. Senza quel pulsante il
centro della pianta e il target della 3D restavano identici. I rilasci finti della ripetizione automatica erano già
ignorati correttamente. [V: riproduzione con `QKeyEvent` e `QMouseEvent` prima della correzione]

- La macchina di stati condivisa riconosce Spazio anche senza pulsanti. Il mouse sposta la vista, il trascinamento
  col sinistro continua a funzionare e Maiusc+sinistro orbita ancora nella 3D.
- La pianta conserva l'ultima posizione del puntatore. Il rilascio vero chiude il pan e ripristina il cursore dello
  strumento precedente. Anche la perdita di fuoco chiude il gesto.
- La 3D chiude subito l'azione di pan al rilascio, senza aspettare un altro movimento del mouse.
- `isAutoRepeat()` protegge sia le pressioni sia i rilasci finti di Windows.

Sequenza provata in entrambe le viste: movimento iniziale a `(300, 250)`, pressione di Spazio, movimento a
`(360, 280)`, pressione e rilascio automatici, altro movimento a `(370, 290)`, rilascio vero, movimento a
`(380, 300)`. La vista si sposta solo nei primi due intervalli. Non viene disegnato né selezionato nulla. La stessa
sequenza è verificata nella macchina di stati per tutti i 14 stili.

## Punto 4: R191, Equal Earth

La scelta di Daniel era presente nel registro: il punto è stato realizzato, non saltato.

- `worldmap.equal_earth` implementa la formula di Šavrič, Patterson e Jenny, con raggio 6.371.007,2 m, meridiano
  centrale alla longitudine del sito e falsa nord alla sua latitudine. Il sito resta `(0, 0)`.
- Oltre 2.000 m/pixel il layer Natural Earth passa dal piano tangente a Equal Earth. Sotto 1.500 m/pixel torna alla
  pianta. L'isteresi evita cambi continui vicino alla soglia. La ricostruzione è sincrona, senza fotogrammi vuoti.
- Tutti i 177 stati del dato offline possono essere disegnati, senza il vecchio limite di 80°. Le geometrie che
  attraversano l'antimeridiano vengono spezzate invece di formare bande attraverso il mondo.
- Lontano le tessere sono nascoste e non richieste, il velo fotografico è spento e l'attribuzione è Natural Earth.
  Il punto del progetto resta visibile. La scala grafica è nascosta perché non è uniforme su tutto il planisfero.
- Il massimo zoom-out dipende dalla viewport: almeno 50.000 m/pixel e, se serve, di più per contenere il mondo
  intero anche in una vista stretta. Riavvicinandosi si torna allo stesso tetto.
- La formula è verificata sul campione ufficiale PROJ `(122°, 47°) -> (1,55; 0,89)` a raggio unitario, sul rapporto
  pubblicato 2,05458213:1, su simmetria, bordi ±180° e centro del sito. [V: `tests/nucleo/test_worldmap.py`]

Le prime fotografie hanno mostrato nomi sovrapposti. La collisione usava coordinate di scena per etichette che
ignorano lo zoom. Ora ancore e rettangoli sono calcolati nella viewport e i nomi sono centrati sull'ancora. Una prova
automatica impedisce le intersezioni; le fotografie finali confermano la leggibilità.

## Prova reale e fotografie

[V] Due giri nella sessione Wayland nascosta, avviati solo con `tools/real_session.sh` e runtime privato, hanno
aperto `capannone()` nella `MainWindow`. Sono passati gli eventi Windows di touchpad, Spazio con ripetizione
automatica su pianta e 3D, il passaggio a Equal Earth e il ritorno al tetto. Il secondo giro è avvenuto dopo la
correzione delle etichette.

Le foto sono state aperte e controllate: finestre complete, 3D non vuota, temi corretti, mondo intero e nomi senza
sovrapposizioni:

- [input in chiaro](foto/kimi23-input-chiaro.png)
- [input in scuro](foto/kimi23-input-scuro.png)
- [Equal Earth in chiaro](foto/kimi23-mondo-chiaro.png)
- [Equal Earth in scuro](foto/kimi23-mondo-scuro.png)

Alla fine `findmnt /run/user/1000/doc` mostra ancora il portale montato. Non restano processi del programma o della
sessione nascosta. Gli avvisi DBus e AT-SPI della sessione privata non hanno impedito il giro.

## Da provare sul Dell di Daniel

1. Con la guida del registro, ripetere i gesti sul touchpad di precisione Windows e mandare il JSON Lines.
2. Verificare che lo scorrimento segua le dita nei due assi, che il pizzico resti sotto il cursore e che Spazio
   muova senza richiedere il tasto sinistro.
3. Controllare il passaggio tetto-regione-Europa-mondo e ritorno a schermo 200 %, con la leggibilità dei nomi.

Il Dell Windows non è stato simulato come sistema operativo: qui gli eventi Windows sono costruiti con le stesse classi
Qt e le sequenze documentate, mentre il giro grafico reale è stato fatto su Wayland.

## Verifiche finali

- [V] `nucleo`: 808 prove, 4 saltate, OK.
- [V] `calcoli`: 193 prove, OK.
- [V] `formati`: 60 prove, OK.
- [V] `esterni`: 6 prove saltate perché mancano i dati esterni facoltativi, OK.
- [V] `widget`: 335 prove, 1 saltata, OK.
- [V] `finestra`: 134 prove, OK.
- [V] Totale: 1.536 prove, 11 saltate, nessun fallimento.
- [V] `ruff check src tests tools`, `git diff --check` e i 6 test di rilascio: OK.
- [V] `tools/compile_po.py` e `msgfmt --check po/it.po`: OK. Nessuna voce fuzzy; nessuna nuova stringa da tradurre.
- [V] Interprete `~/fvtest/venv314/bin/python` con `meridiana` caricato da `src` di questo checkout.
