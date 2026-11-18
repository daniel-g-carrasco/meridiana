# 4. Consumi

I consumi decidono quanta produzione si usa sul posto. Il bilancio li incontra ora per ora con la produzione: per questo serve la loro forma, non solo il totale.

## Da dove vengono

Nella pagina dei Consumi si sceglie la base: un totale annuo, le tre fasce F1, F2, F3, le bollette mese per mese, una curva misurata (CSV a 15 minuti o oraria, Calcolo > Importa una curva di carico…) o un profilo tipo. Senza dati Meridiana stima i consumi dal progetto e lo dice nelle Verifiche, da sapere: il bilancio che ne esce è indicativo.

## I risultati

### Consumo all'anno

I consumi di un anno, da ciò che hai inserito. Gli altri riquadri ne descrivono la forma.

### Le fasce

Le fasce orarie dell'energia elettrica (`energy/bands.py`):

- F1: dal lunedì al venerdì, dalle 8 alle 19;
- F2: dal lunedì al venerdì dalle 7 alle 8 e dalle 19 alle 23; il sabato dalle 7 alle 23;
- F3: le notti, le domeniche e i festivi; le ore del sabato fuori da F2.

Un sito che usa la sua energia in F1 si sovrappone meglio alla produzione del giorno; i prezzi per fascia sono nella pagina del [Bilancio](5-bilancio.md#prezzi).

### La forma dei consumi

Le cifre che un'analisi energetica guarda per prime (`energy/consumption.py`, `figures`):

- l'ora più alta dell'anno;
- il carico di base: la potenza sotto cui il consumo non scende quasi mai, presa come il 5° percentile delle ore (il consumo le sta sopra nel 95 % delle ore);
- il fattore di carico: il consumo medio diviso per l'ora più alta;
- la quota dei consumi tra le 8 e le 18, quando un impianto produce di più;
- la quota nei fine settimana e nei festivi.

Un sito attivo di giorno usa più produzione; uno che consuma di notte o nei fine settimana ne manda di più in rete, e lì l'accumulo può servire.
