# Incarico 22 per Kimi: il dimensionamento degli inverter e gli ingressi delle stringhe (R187, R188), 27/10/2026

Usa la skill meridiana. Leggi parola per parola le righe R187 e R188 di docs/richieste.md, e quelle che le precedono
sullo stesso tema (R114-R119, R141, R142, R134). Questa è ingegneria: Daniel è un progettista elettrico e i numeri
devono essere giusti, con la formula e la fonte di ogni verifica.

## Dove lavori
Nella cartella ~/dev/meridiana-kimi, sul ramo kimi-incarico-22 preso da kimi-incarico-21 (il lanciatore lo crea).

## Punti
1. **Gli errori del dimensionamento automatico.** Riproducili: progetti di prova (tests/_fixtures.py) e casi costruiti
   (un sottocampo, più sottocampi con orientamenti diversi, moduli grandi e piccoli, marche diverse del catalogo).
   Per ognuno: che cosa fa oggi, che errore dà, perché. Correggi con una prova rossa per errore.
2. **R187, inverter di potenze diverse e tutti i moduli in stringa.** Il dimensionamento automatico, scelta la marca,
   deve poter combinare modelli di potenze diverse della stessa marca, così che: il rapporto DC/AC chiesto sia
   rispettato al meglio; la stringatura proposta subito dopo metta in stringa tutti i moduli; ogni ingresso stia nei
   suoi limiti (tensione massima in ingresso a temperatura minima, finestra MPPT a temperature massima e minima,
   corrente massima dell'ingresso, numero di stringhe per ingresso). Se un numero di moduli non si può stringare tutto
   (per esempio un sottocampo con un numero primo di moduli fuori dalle lunghezze ammesse), il programma lo dice con il
   perché e propone la correzione più piccola (togliere o aggiungere N moduli, cambiare ingresso), invece di lasciarli
   fuori in silenzio. Il criterio di scelta fra combinazioni (meno inverter, poi meno modelli diversi, poi rapporto più
   vicino) scrivilo nel codice e nell'esito.
3. **R188, gli ingressi nel pannello a destra.** Per ogni inverter, da subito, tutti gli ingressi MPPT del modello,
   ognuno con: i moduli in serie minimi e massimi ammessi con il modulo e le temperature del sito, le stringhe in
   parallelo massime (dalla corrente dell'ingresso e dalla corrente del modulo), la potenza, lo stato (vuoto, in regola,
   fuori limite, con il simbolo e il perché). Da lì si attiva un ingresso per costruirne le stringhe (a mano o proposte).
   **Stringhe in parallelo**: più stringhe uguali sullo stesso ingresso, con le verifiche di corrente e di uniformità
   (stessa lunghezza, stesso orientamento, o il perché se no). Se il formato del progetto deve cambiare, nuovo formato
   con la sua migrazione, il file campione congelato e la riga in BROUGHT (vedi i formati 13 e 14).
4. **I calcoli giusti.** Ogni verifica ha la sua formula scritta (tensione a vuoto alla temperatura minima con il
   coefficiente del modulo, tensione MPP alla temperatura massima e minima di cella, corrente di corto circuito per
   ingresso, potenza) e i dati da cui parte (scheda del modulo e dell'inverter nel catalogo, temperature del sito). Dove
   citi una norma (IEC 62548, CEI 64-8 sezione 712, guida CEI 82-25) scrivi «[da verificare da Claude]» accanto
   all'articolo: Claude li controlla sulle norme vere. Prove con numeri calcolati a mano nell'esito per almeno tre casi.
5. **Chiusura.** Registro (R187, R188), CHANGELOG, po/it.po, esito in docs/revisioni/kimi-incarico-22-esito.md con le
   foto del pannello degli ingressi (chiaro e scuro, testo Medio e Grande) prese nella sessione nascosta, tutti i gruppi
   di prove, ruff, msgfmt.
