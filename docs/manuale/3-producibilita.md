# 3. Producibilità

Meridiana calcola l'anno tipo ora per ora, dal sole sui moduli al contatore, con il meteo del sito. A sinistra ciò che decidi (meteo, campi, inverter, stringhe, perdite), a destra i risultati: i riquadri con le cifre, i grafici e «Come è calcolato». Calcola (F5) rifà il conto; il pannello di destra mostra le cifre della variante in mano.

## Collegamento dei moduli

I moduli posati ma fuori stringa non contribuiscono alla producibilita dell'impianto. Contano soltanto quelli
collegati mediante una stringa a un ingresso di un inverter presente. Senza collegamenti, l'energia calcolata
è zero. Collegare o scollegare moduli rende i risultati precedenti da ricalcolare: premi F5 dopo la modifica.
La potenza e il numero dei moduli posati rimangono informazioni geometriche del progetto; non sono una promessa
di produzione. La stima PVGIS di confronto segue i moduli collegati.

## Il meteo del sito

### PVGIS

PVGIS è il servizio del Centro comune di ricerca (JRC) della Commissione europea. Dà l'anno meteo tipo del sito (ora per ora: irraggiamento, temperatura, vento) e l'orizzonte lontano, con le montagne e le colline che nascondono il sole basso. Si scaricano una volta e restano nella cache: senza rete Meridiana calcola con ciò che ha già. Al salvataggio entrano anche nel file del progetto, che così si apre e si calcola su un altro PC senza scaricarli di nuovo. Se cambi il sito, il meteo del posto precedente non viene usato. La rete verso PVGIS si spegne in File > Impostazioni > Riservatezza.

Il riquadro «PVGIS, secondo parere» mostra la stima di PVGIS (servizio PVcalc) per lo stesso impianto: tecnologia crystSi2025, media degli anni 2005-2023 (banca dati SARAH3), come scrive il riquadro stesso. Non è lo stesso conto di Meridiana (un anno tipo contro una media di anni, perdite diverse): uno scarto di qualche punto percentuale è normale, uno grande va guardato.

## I risultati

### Energia all'anno

L'energia che l'impianto dà al contatore nell'anno tipo del sito, dopo tutta la catena delle perdite: ombre, riflessione, sporco, temperatura, cavi, inverter. È la cifra della relazione. «Come è calcolato» mostra ogni passo, dal sole al contatore, con la sua fonte.

### Producibilità specifica

L'energia di un anno divisa per la potenza dei moduli (kWh/kWp): confronta impianti di taglia diversa. In Italia sta spesso tra 1.000 e 1.500 kWh/kWp, da nord a sud (ordine di grandezza da confermare, non un valore di norma). Molto sotto, guarda le ombre, l'orientamento e l'inclinazione.

### Indice di prestazione

Il performance ratio (PR): l'energia al contatore divisa per quella che i moduli darebbero alla potenza nominale con l'irraggiamento sul loro piano. Misura le perdite, non il sole del sito. Tra 75 e 85 % è normale per un impianto con poche ombre (ordine di grandezza da confermare); più in basso, guarda le perdite.

### Potenza

La somma delle potenze di targa dei moduli in condizioni standard (STC), in kWp; sotto, la potenza CA degli inverter e il rapporto CC/CA. Per le regole di connessione la potenza nominale dell'impianto è la minore delle due (CEI 0-21:2026-07, 3.61, p. 16, citata in `rules.py`).

## Perdite

Ogni voce è un passo della catena dal sole al contatore. Il grafico «Dal sole al contatore: ogni passo» le mostra in ordine; «Come è calcolato» dà la formula e la fonte di ognuna. I predefiniti (`energy/simulate.py`, `Losses`) sono segnati come tali:

- modello di trasposizione Perez 1990; riflettanza del suolo (albedo) 0,20;
- ombre dell'orizzonte lontano e degli ostacoli della scena, accese;
- riflessione sul vetro, modello ASHRAE con b0 = 0,05;
- sporco 2 %; qualità dei moduli 0 %; mismatch 1 %;
- degradazione indotta dalla luce (LID) dalla scheda del modulo, altrimenti 1 %;
- cavi CC 1,5 % in STC; cavi CA 1 % alla potenza CA nominale; indisponibilità 0 %;
- temperatura delle celle con il modello termico di PVsyst; l'effetto elettrico delle ombre sulle stringhe applicato per intero.

Quello che il modello non calcola o stima soltanto (moduli bifacciali, correzione spettrale, neve, trasformatore MT, taglio per ingresso MPPT) è elencato in fondo a «Come è calcolato» e nella relazione.

## Come è calcolato

La scheda «Come è calcolato» di ogni pagina dei risultati mostra i passi del calcolo: la formula, la spiegazione, i valori entrati con la loro fonte (tua, predefinita, dato, norma, modello, calcolata), il risultato e il riferimento. Il collegamento «Come è calcolato ›» del riquadro d'aiuto apre la scheda al passo giusto.
