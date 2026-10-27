# Incarico 21 per Kimi: la pianta e le stringhe disegnate (R183, R184, R185, R186), 27/10/2026

Usa la skill meridiana: regole, divieti, prove automatiche, prova vera nella sessione nascosta, foto da guardare,
«armonizziamo». Leggi parola per parola le righe R183-R186 di docs/richieste.md: sono le parole di Daniel, con le
sue schermate descritte. Daniel lavora su Windows, con un portatile Dell e lo schermo a 200 %.

## Dove lavori
Nella cartella ~/dev/meridiana-kimi, sul ramo kimi-incarico-21 preso da origin/lavoro (il lanciatore lo crea).
Gli incarichi 22, 23 e 24 partiranno dal tuo ramo: lascialo pulito e verde.

## Punti
1. **R185, i numeri dei moduli.** Con la pianta ruotata (R146, R174) i numeri d'ordine delle stringhe disegnate a mano
   finiscono in fila lontano dai moduli, alcuni sovrapposti. Trova perché (probabilmente la posizione delle etichette
   calcolata senza la rotazione della vista) e correggi in modo che ogni numero stia sul suo modulo a ogni rotazione,
   zoom e spostamento. Prima una prova rossa: pianta ruotata di 30° e di 115°, ogni numero entro pochi pixel dal centro
   del suo modulo. Foto nella sessione nascosta, ruotata e no.
2. **R186, un pallino per ogni modulo stringato.** Sulla linea della stringa, al centro di ogni modulo che ne fa parte,
   un pallino nel colore della stringa, di misura costante sullo schermo, coerente con le pillole delle etichette
   (marks.py) e con i colori in chiaro e in scuro. Con molti moduli e da lontano non deve diventare una poltiglia:
   decidi tu una soglia di zoom sotto cui i pallini spariscono e scrivila nell'esito.
3. **R184, i salti fra i moduli.** Oggi la linea va a zig-zag fra due file, con tratti obliqui sopra i moduli e anse
   che escono dalla fila (le corsie di R134). Studia come la disegnano i programmi del mestiere (PVsyst, i configuratori
   dei costruttori di inverter, i programmi di progettazione FV) e come lo leggerebbe un installatore: la linea passa per
   i centri dei moduli nell'ordine della stringa; un salto (due moduli consecutivi non vicini) deve leggersi come salto
   senza confondersi con i moduli che scavalca; nessuna ansa fuori dalla fila; due salti che si sovrappongono restano
   distinguibili. Prepara due o tre modi, fotografali nella sessione nascosta sul progetto di prova con una stringa
   che fa avanti e indietro fra due file come quella di Daniel (a tre zoom, ruotata e no, chiaro e scuro), scegli quello
   che raccomandi, realizzalo e lascia gli altri descritti con le foto nell'esito, così Daniel può sceglierne un altro.
4. **R183, i pulsanti per ruotare.** Nella barra della pianta «Allinea a un lato» diventa un pulsante a sola icona,
   con il suggerimento che dice nome e tasto (A), come gli altri pulsanti a sola icona della barra (R165): disegna il
   simbolo nello stile dei simboli del programma. «Nord in alto» esce dalla barra, perché lo fa già il clic sulla bussola;
   restano il tasto N e la voce del menu del clic destro. Aggiorna le prove (test_viewbar) e il sistema grafico.
5. **Chiusura.** Righe R183-R186 del registro («fatto sul ramo kimi-incarico-21»), CHANGELOG, po/it.po, l'esito in
   docs/revisioni/kimi-incarico-21-esito.md (che cosa, come provato, le foto, i moduli condivisi cambiati), tutti i
   gruppi di prove, ruff, msgfmt, nessun processo acceso.
