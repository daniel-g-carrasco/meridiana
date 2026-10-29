# Modello elettrico orario: revisione R02 del 29 ottobre 2026

## Esito e ambito

Il percorso ordinario `pipeline.compute` usa ora le curve I/V dei moduli effettivamente connessi, le sottostringhe con bypass, la ricomposizione serie/parallelo, i limiti orari disponibili degli ottimizzatori e la conversione AC distinta per inverter. I moduli scollegati, con riferimento a inverter inesistente o ingresso inesistente restano a produzione zero. La risoluzione dei riferimenti duplicati resta in `plant.build` ed è coperta da regressione.

Il vecchio percorso `simulate(..., strings=...)` / `with_strings` resta disponibile per i confronti storici del motore. La pipeline di progetto richiama `with_network` e non somma Martinez al nuovo risultato elettrico. Nessuna modifica al formato del progetto in questo ambito: si leggono i gruppi espliciti di ottimizzatori introdotti dal lotto coordinato.

## Implementazione effettiva

- `energy/nearshade.py`: intersezione dell'unione delle ombre con ogni cella di una griglia geometrica inferita dalle dimensioni e dal numero di celle. Le celle sono raggruppate per irradiamento in 17 livelli; non si usa soltanto l'area media della sottostringa. Sono mantenuti blocchi bypass e rami half-cell. La tabella solare resta a passi di 5°/4°, con interpolazione bilineare. I pesi delle coorti sono memorizzati a 16 bit; la cache geometrica ha un budget di 128 MiB.
- `energy/electrical.py`: parametri a diodo singolo del modulo scalati per le sezioni serie/parallelo. Le coorti di celle di una sezione sono in serie; i rami half-cell sono in parallelo; la sezione ha un bypass con caduta assunta di 0,5 V. Curve a 129 campioni, interpolazione lineare e ricerca del massimo di ciascun segmento, compresi picchi locali e confini della finestra di funzionamento. La corrente è comune lungo tutta la stringa: non esiste una propagazione del danno solo ai pannelli successivi.
- `energy/electrical_network.py`: le stringhe di un MPPT sono alla stessa tensione. Si applicano finestra MPPT, massimo DC assoluto disponibile, corrente condizionata dal numero di stringhe e limite del connettore. Il limite di corrente totale dell'inverter produce, quando necessario, una riduzione proporzionale delle potenze dei tracker, esplicitamente segnalata: non è un algoritmo ottimale di redistribuzione.
- Ottimizzatori: `module_groups` conserva i gruppi manuali, anche 2+1+2. Si rispettano topologia di ingresso serie/parallelo, finestra di tensione e corrente di ciascun ingresso documentate. All'uscita tutti gli ottimizzatori della stringa hanno una corrente comune; la somma delle tensioni disponibili deve raggiungere la tensione fissa inverter, rispettando `v_out_max`, `i_out_max` e la potenza continua della stringa. La potenza nominale STC ammessa dei moduli non viene trasformata in un taglio istantaneo inventato.
- `simulate.py`: qualità, LID e mismatch residuo si applicano una volta. La rete sostituisce lo stadio elettrico; i suoi limiti sono separati dalla perdita DC ohmica, poi ogni inverter ha efficienza PVWatts, clipping e perdita AC propri. Il registro nominale/25 °C/temperatura è coerente con l'irradiamento medio dei soli moduli connessi; i parametri del diodo variano con la temperatura, senza applicare anche una seconda correzione di potenza gamma.
- `pipeline.py`: passa l'anno DC distinto per inverter a `plant.build`, senza ridistribuire la somma sulla potenza nominale. L'API pubblica `Simulation.inverters` contiene `number`, `name`, `p_ac_kw`, `dc_kwh`, `clipping_kwh`, `ac_kwh`, `p_dc`, `p_ac`; la somma delle serie orarie coincide con l'impianto. I moduli non assegnati restano nella geometria e nei costi, non nella produzione.

## Prove numeriche e regressioni

Le prove sono sintetiche e riproducibili, non misure sperimentali né una certificazione del modello.

| Prova | Esito verificato |
|---|---|
| Modulo uniforme, 200/600/1.000 W/m² e 5/25/60 °C | confronto con `pvlib.max_power_point`, tolleranza 0,3% |
| Un blocco a 100 W/m², due a 1.000 W/m², 25 °C | riferimento indipendente `pvlib.v_from_i` su 10.001 correnti: 293,4623 W; modello: 293,4059 W, scarto −0,0192% |
| Stessa area schermata, una cella concentrata contro ombra distribuita | 293,4059 W contro 440,6359 W: il modello non perde la localizzazione |
| Rami half-cell e bypass | riduzione coerente con il ramo illuminato; invarianza rispetto all'ordine dei moduli in serie |
| Stringhe in parallelo | il massimo a tensione comune è inferiore alla somma dei massimi indipendenti nel caso disuniforme |
| Discretizzazione I/V | 129 contro 513 campioni: scarto entro 2,5% nei tre casi con più picchi testati |
| Ottimizzatori | limiti su ogni ingresso parallelo; tensione insufficiente con unità al buio; corrente di uscita; gruppi manuali diversi cambiano il bilancio di tensione; limite mancante dichiarato |
| Dati incompleti | ottimizzatore non identificato: zero con avviso; massimo MPPT assente: massimo DC disponibile e avviso di finestra non verificata |
| Inverter | due unità attive da 5/20 kW, DC 10/1 kW: il secondo non assorbe il clipping del primo |
| Connessioni | tutti scollegati a zero anche nei mesi/economia; duplicati non raddoppiati; inverter inutilizzato non assorbe clipping; stringa eccessivamente lunga perde energia fuori finestra |
| Bilancio | somme DC/AC per inverter uguali al totale; limitazione di corrente totale separata dalle perdite di cablaggio |
| Interruzione | callback osservata prima di ogni blocco di 48 ore illuminate |

Convergenza delle coorti per tre distribuzioni sintetiche di ombra su 20 celle per sezione (diffusa 100 W/m², diretta 900 W/m²):

| Livelli | Ombra concentrata mista, W | Ombra uniforme 21%, W | Una cella completamente in ombra, W |
|---:|---:|---:|---:|
| 5 | 76,7626 | 354,4969 | 52,9819 |
| 9 | 114,5972 | 357,0132 | 52,9819 |
| 17 | 142,1774 | 360,6067 | 52,9819 |
| 65 | 142,5099 | 365,4856 | 52,9819 |

Il caso concentrato esclude 5 e 9 livelli come default. I 17 livelli differiscono da 65 dello 0,23% / 1,33% / 0% nei casi sopra; il test ammette il 3%. Questa è una verifica su casi scelti, non un limite d'errore garantito per ogni geometria.

Esecuzioni: gruppo mirato di 51 prove (`test_electrical_iv`, `test_electrical_network`, `test_nearshade`, `test_connected_production`, `test_pipeline`, `test_optimizers.ThePipeline`) passato in 43,72 s. Dopo gli ultimi fast path e controlli sui dati mancanti, 19 prove I/V/rete passate in 1,48 s; Ruff sui file interessati passato. La suite generale è gestita dal coordinatore e non viene dichiarata superata da questo rapporto.

## Prestazioni e campione annuale

Probe riproducibile `build/probe_electrical_r02.py`, Python 3.12 dell'ambiente di Meridiana, Windows di Daniel, dati meteo sintetici offline, anno completo di 8.760 ore e due inverter da 12/40 kW. Le misure sono di processo, con altri controlli di integrazione in corso; non costituiscono un benchmark hardware isolato.

- Senza ostacoli, mantenendo file inclinate a 15° e ombra reciproca: 128 moduli, 8 stringhe, **6,72 s**, picco working set **211,91 MiB**, produzione 79.299,17 kWh.
- Con camino: 126 moduli, 8 stringhe. Prima versione completa 166,67 s; dopo raggruppamento delle sole coorti presenti e lettura diretta della tabella, 125,60 s; ultima versione con fast path uniforme **116,15 s**, picco **259,45 MiB**, produzione **75.769,51 kWh**. Differenza energetica rispetto alla prima versione: +0,0201%, dovuta al ricampionamento delle curve equivalenti. Il primo inverter produce 36.009,82 kWh AC con 7.313,66 kWh di clipping; il secondo produce 39.759,68 kWh AC senza clipping. Il totale DC è 86.214,08 kWh; le somme orarie per inverter sono verificate contro il totale.
- Curve temporanee limitate a blocchi di 48 ore illuminate; interpolazione compilata NumPy, riuso delle curve identiche e riduzione esatta delle sezioni illuminate uniformemente. La cancellazione è controllata tra i blocchi; la preparazione geometrica conserva i propri tempi precedenti.

Il progetto `.mer`, i risultati JSON e il risultato Python del probe sono in `build/electrical-r02` e `build/electrical-r02-clear`, per verificare anche tabella, CSV e PDF senza rete. Il campione con ostacolo è un caso di collaudo, non un impianto reale misurato.

## Limiti ancora aperti, da non presentare come chiusi

1. Diagrammi celle/bypass reali non presenti per tutti i moduli. La griglia geometrica e la topologia sono inferite; se il numero di celle non è utilizzabile, l'ombra torna alla media del blocco e un avviso segnala la possibile sovrastima delle ombre localizzate. Parametri diodo non validi: curva a tre punti di targa, con avviso e senza risoluzione del mismatch cellulare.
2. Valanga inversa, hotspot, correnti inverse di circolazione fra stringhe, variazione della temperatura fra singole celle, guasti, dinamica MPPT, isteresi di avvio e mappe OND di rendimento non sono simulati. Il bypass ha caduta costante assunta; il firmware di ottimizzatore/inverter resta sconosciuto.
3. Ombre di file e ostacoli: sovrapposizione statistica delle coorti perché il precedente modello di fila infinita non fornisce un poligono congiunto. La griglia solare e le coorti sono approssimazioni numeriche, non geometria continua esatta.
4. Paralleli esterni: se le stringhe superano i connettori e manca una mappa, sono applicati i limiti aggregati disponibili con avviso, ma non è verificata la corrente realmente condivisa da ciascun connettore. Nessuna connessione fisica viene inventata. I controlli di Isc/Voc di progetto restano distinti dalla curva di produzione.
5. Dati orari di ottimizzatore mancanti sono elencati. Rendimento costante; nessuna ricostruzione non documentata di dispositivi diversi da quelli supportati. La ripartizione delle perdite fra sottocampi è proporzionale alla potenza indipendente dei moduli; è una convenzione contabile, mentre il totale proviene dalla rete elettrica.
6. Il selettore della frazione elettrica attenua il contrasto di irradiamento verso la media del campo prima di ricombinare le curve; non è una percentuale lineare dell'energia perduta. Questo comportamento è dichiarato nelle note quando il valore non è 100%.
7. Il caso annuale con ostacoli rimane costoso. Il budget cache non limita la memoria di una singola scena geometrica in costruzione, e il benchmark non copre migliaia di moduli o molti ostacoli: non si dichiara la scalabilità di tali casi verificata.

R225–R228: gli aspetti implementabili con i dati attuali sono ora nel percorso effettivo e testati; restano parziali rispetto a una simulazione dettagliata certificata del componente reale, per i limiti sopra. Nessuna modifica a normative o soglie di verifica elettrica è introdotta dal modello I/V.

## Fonti e loro portata

Prima sono stati consultati `docs/studio/06-pvsyst-aurora-pvlib.md`, `10-pvsyst-formati-file.md`, `18-prove/ombre_caso_analitico.py`, l'audit R01 `ombre-stringatura-audit-20261029.md` e le schede SolarEdge locali in `C:\Users\Grasso\Elettrico\reference\catalogs\SolarEdge` già identificate dal lotto catalogo (DS-000091-IT, DS-000105-IT, note multiple modules e single string). I limiti numerici del costruttore provengono dal catalogo verificato dal lotto coordinato; non vengono ricavati da ricordi di normativa.

Fonti primarie online: [pvlib, esempio di ombra parziale del modulo](https://pvlib-python.readthedocs.io/en/stable/gallery/shading/plot_partial_module_shading_simple.html) per la dipendenza dalla distribuzione sulle celle e dalla topologia; [pvlib, tensione dalla corrente](https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.v_from_i.html) per il confronto numerico indipendente; [PVsyst, effetto dei bypass e dei paralleli](https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-layout/effect-of-the-by-pass-diodes.html) per il vincolo della tensione comune delle stringhe parallele. Queste fonti motivano le equazioni e le assunzioni; non validano automaticamente questa implementazione.
