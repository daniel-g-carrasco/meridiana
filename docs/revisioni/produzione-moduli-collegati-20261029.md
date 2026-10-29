# Produzione dei soli moduli collegati (R224)

29 ottobre 2026. Requisito di Daniel: un pannello non collegato deve contribuire zero alla producibilità dell'impianto.

## Difetto riprodotto

La pipeline calcolava l'energia su tutti i moduli posati; le stringhe intervenivano sulle verifiche e sulle perdite elettriche di ombreggiamento, senza escludere i moduli scollegati. La frase dell'assistente descriveva quindi un difetto reale, verificato nel codice e con un anno sintetico.

Fixture riproducibile: `tests/calcoli/test_connected_production.py`, capannone di Rho, 128 moduli, inverter esplicito da 20 kW, meteo sintetico, senza ombre vicine né orizzonte. Prima della correzione, zero stringhe o riferimenti a inverter/MPPT inesistenti davano 63.667,844404 kWh/anno. Con 8 moduli collegati, il DC era 16 volte quello della simulazione degli 8 moduli.

Dopo la correzione:

| Moduli collegati su 128 posati | Energia annua AC |
| --- | ---: |
| 0 | 0 kWh |
| 8 | 5.039,013504 kWh |
| 128 | 63.667,844404 kWh |

Sono dati della fixture sintetica, non una ricalcolazione del progetto mostrato nello screenshot.

## Correzione

- `src/meridiana/energy/pipeline.py`: considera produttivi solo i moduli presenti in una stringa su un ingresso esistente di un inverter esplicitamente scelto. L'inverter dimensionato come segnaposto non costituisce un collegamento. La geometria posata resta disponibile. Gli inverter completamente inutilizzati non aggiungono capacità AC al calcolo produttivo.
- `src/meridiana/energy/simulate.py`: `ArraySpec.connected` distingue geometria e moduli produttivi; il filtro interviene prima delle perdite DC e del clipping AC. Le ombre degli ostacoli sono valutate sul sottoinsieme produttivo, le file fisiche restano quelle posate. Ottimizzatori, limite di potenza delle stringhe e perdite dei cavi usano la potenza collegata. Il record di calcolo esplicita il numero di moduli produttivi.
- `src/meridiana/energy/plant.py`: le verifiche di sovraccarico ricevono il profilo DC effettivo; il nuovo argomento facoltativo `p_dc_connected=True` ripartisce tale profilo sulla potenza collegata. I vecchi chiamanti mantengono il comportamento precedente.
- `src/meridiana/energy/economics.py`: la produzione nulla non provoca divisioni per zero nel LCOE; il valore resta infinito, come assenza di energia sulla quale ripartire il costo.
- `src/meridiana/ui/selftest.py`: l'impianto dimostrativo del collaudo pacchetti ora contiene inverter e stringhe esplicitamente salvate. Nessuna attribuzione automatica è stata introdotta nei progetti dell'utente.

La potenza `sim.p_stc_kw` e `arrays.modules` continuano a descrivere il posato, anche ai fini dei costi. `arrays.connected_modules` e `arrays.connected_p_stc_kw` descrivono la quota produttiva. DC, AC, energia oraria e mensile, flussi economici e confronto PVGIS usano i soli moduli collegati. Senza moduli collegati PVGIS vale zero e non viene interrogato. La rimozione di una stringa rende obsoleto il risultato precedente tramite la chiave di cache energetica già esistente.

## Verifiche eseguite

- Otto regressioni nuove: nessun collegamento, inverter/MPPT inesistenti, collegamento parziale confrontato ora per ora con simulazione indipendente, duplicati, inverter segnaposto, invalidazione della cache dopo rimozione stringa, impianto interamente collegato invariato, inverter inutilizzato e clipping, ottimizzatori con collegamento parziale e nullo. Alcune condizioni sono sottocasi dello stesso test.
- Lotto mirato: **108 test passati in 38,183 s**, comprendente connessioni, pipeline, energia, ottimizzatori, economia, portabilità e `finestra.test_self_test.Run`. Quest'ultimo esegue il collaudo completo isolato dell'app da sorgente, inclusi energia e relazione PDF.
- Intero gruppo `calcoli`: **201 test eseguiti in 30,856 s**, 200 passati e un solo fallimento su un'asserzione testuale rimasta alla vecchia frase dei controlli. Dopo l'aggiornamento di quell'asserzione, la classe `OnlyWhenAsked` è stata rieseguita: **5/5 passati in 1,063 s**. Il gruppo completo non è stato ripetuto per questa sola modifica testuale.
- Ruff su tutti i sorgenti e test coinvolti: **passato**.
- Fixture storiche di pipeline, energia e portabilità aggiornate per dichiarare le connessioni quando richiedono produzione positiva.

## Limiti dichiarati

La conversione AC rimane il modello aggregato esistente tra gli inverter attivi; non è stata introdotta una simulazione oraria separata per ogni inverter o MPPT. Le verifiche di tensione/corrente restano verifiche: il motore non simula ogni protezione o arresto dell'inverter. Un collegamento a un ingresso esistente viene contato anche quando una verifica elettrica segnala un problema; quel problema resta visibile nei controlli.

Quando il campo è parzialmente collegato, il primo passaggio stima le temperature dell'anno e il secondo calcola la quota produttiva. Il campo interamente collegato riutilizza il primo passaggio. Una misurazione singola della fixture ha dato 0,493 s con zero collegati, 0,372 s con 8 e 0,298 s con 128; non è un benchmark né una garanzia per scene grandi. Nessuna ottimizzazione asincrona aggiunta.

Il valore nello screenshot dell'utente non è stato ricalcolato su quel progetto. Il collaudo dei pacchetti ricostruiti è separato dal collaudo da sorgente riportato qui.
