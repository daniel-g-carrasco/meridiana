# 2. Impianto

L'Impianto è la fase degli inverter e delle stringhe: ciò che collega i moduli posati alla rete.

- **Gli inverter** si scelgono dal catalogo (Calcolo > Aggiungi un inverter dal catalogo…) o li dimensiona Meridiana al rapporto CC/CA scritto nella pagina della Producibilità (Calcolo > Dimensiona l'inverter da solo). Un inverter dimensionato da solo è detto nelle Verifiche, da sapere.
- **Le stringhe** sono verificate con la CEI 64-8/7:2024 (verifiche delle stringhe in `checks.py`, calcolo in `energy/stringing.py`): la tensione a vuoto massima della stringa alla cella più fredda contro la tensione massima dell'inverter e dei moduli; la tensione di massima potenza alle temperature estreme contro la finestra MPPT; la corrente di cortocircuito massima, con il margine della norma, contro quella che l'ingresso sopporta; la protezione di ogni stringa quando sullo stesso ingresso ce ne sono tre o più. Ogni verifica che non passa dice perché e che cosa fare.
- **La temperatura più bassa del sito** (-10 °C per impostazione nella pagina della Producibilità) decide la tensione più alta: va presa dai dati climatici del luogo.

## Il pannello di destra

Tutto l'impianto si gestisce dal pannello di destra della fase; sopra la pianta non c'è niente.

- **Inverter**: l'elenco (quanti di ciascuno, dal catalogo o dai file .OND di PVsyst, con la ✕ per toglierne uno), «Aggiungi un inverter dal catalogo…», «Dimensiona l'inverter da solo», il rapporto CC/CA; per un inverter SolarEdge gli ottimizzatori.
- **Stringhe**: per ogni inverter e ingresso le sue stringhe, ognuna con il suo colore sulla pianta, i moduli e lo stato (segno e parola); un ingresso senza stringhe lo dice. Una riga scelta sceglie la stringa sulla pianta e la inquadra; **Canc** la elimina; il **doppio clic** la ridisegna; il tasto destro apre il suo menu (inverti il verso, ridisegna, sposta su un altro ingresso, elimina). Il **+** a destra di un ingresso disegna una stringa nuova su quell'ingresso. Sotto l'elenco: «Proponi le stringhe», «Completa le stringhe», «Elimina tutte le stringhe».
- **Proposta e verifiche**: la strategia e i moduli in serie che userà la prossima proposta (non cambiano le stringhe di adesso), la temperatura minima del sito e le condizioni delle verifiche.
- **Stringa scelta**: le verifiche della stringa scelta, con le fonti delle temperature.
- **Sottocampo selezionato**: l'inverter e l'ingresso dove la proposta manda le stringhe di quel sottocampo.

## Le stringhe sono tue

Meridiana non fa e non rifà mai le stringhe da sola: aggiungere o togliere un inverter, cambiare un modulo, posare di nuovo un sottocampo non crea e non sposta nessuna stringa (una stringa resta sul suo inverter anche quando l'elenco cambia la numerazione). I moduli che non sono in una stringa restano **fuori stringa**, con il bordo rosso sulla pianta, e le Verifiche lo dicono; la loro correzione è «Completa le stringhe». Attenzione: un modulo fuori stringa nell'impianto vero non produce, mentre la producibilità lo conta come se fosse collegato.

- **Proponi le stringhe** (barra o pannello, con il menu delle strategie di PVsyst: avanti e indietro lungo le file, una fila per stringa, a U su due file, una fila per MPPT): Meridiana mette in stringhe tutti i moduli posati, una volta sola, al posto delle stringhe che ci sono. Se ci sono già stringhe chiede prima. Un passo di annulla.
- **Completa le stringhe**: Meridiana propone stringhe solo per i moduli fuori stringa, prima sugli ingressi senza stringhe, poi su quelli che ne prendono altre lunghe come le tue; le tue restano come sono. Un passo di annulla.
- **Elimina tutte le stringhe**: dopo una domanda, tutti i moduli tornano fuori stringa. Un passo di annulla.
- I progetti salvati prima del formato 14, che avevano le stringhe proposte in automatico, all'apertura le tengono uguali: diventano tue senza domande e senza segnare il progetto come modificato.

## Disegnare una stringa a mano

1. Premi il **+** dell'ingresso che vuoi nell'elenco di destra, oppure «Disegna» nella barra (l'ingresso della stringa scelta, o il primo libero).
2. Clicca i moduli nell'ordine della stringa, oppure trascina sopra di essi: un modulo si prende quando il puntatore passa il suo centro. Sui moduli compare il numero d'ordine; la striscia in alto dice quanti moduli hai e quanti ne vuole l'ingresso («ne mancano 2 (da 7 a 25)»).
3. **Backspace** toglie l'ultimo modulo; **Invio** o un **doppio clic** chiude la stringa (un solo passo di annulla); **Esc** la annulla senza cambiare nulla.
4. Un modulo che è già in un'altra stringa viene rifiutato e la barra dice in quale; con **Maiusc** premuto il clic lo sposta nella stringa che stai disegnando (dopo, la barra dice da quale stringa è stato preso).

Il tasto destro mentre disegni apre «Chiudi la stringa», «Togli l'ultimo modulo», «Annulla la stringa»; su un modulo di una stringa apre «Salta questo modulo», «La stringa comincia qui», «finisce qui», inverti, ridisegna, sposta, elimina; su un modulo fuori stringa, «Nuova stringa da questo modulo».

## Sulla pianta

Ogni stringa ha la sua tinta (due stringhe vicine, anche nella fila accanto, non hanno mai la stessa; eliminarne una non ridipinge le altre), il nome inverter.ingresso.stringa sopra il primo modulo con il semaforo del suo stato (✔ corretta, ⚠ da verificare, ✘ fuori finestra o senza ingresso) e i suoi moduli pieni del suo colore. La linea passa dal centro di un modulo al successivo quando sono vicini; quando la stringa **salta** dei moduli la linea gira intorno ai moduli saltati lungo i loro bordi, **tratteggiata**, e i moduli saltati restano senza colore: un salto si vede sempre, mentre disegni e dopo. La stringa scelta è più larga, contornata e numerata. Da lontano i nomi che si sovrapporrebbero si nascondono (resta il colore; il nome è nel suggerimento). La [Producibilità](3-producibilita.md) riassume l'impianto e calcola l'anno su tutti gli inverter insieme.
