# R215: assegnazione globale di inverter, stringhe e ottimizzatori

Seguito del 29/10/2026, revisione R02. [V] indica una verifica eseguita; [I] descrive una scelta o il suo perimetro.
Il riferimento iniziale e `docs/revisioni/ombre-stringatura-audit-20261029.md`.

## Piano eseguito

1. [V] Riprodotti i casi in cui la scelta di una sola lunghezza o l'occupazione anticipata di un ingresso lasciava
   moduli collegabili fuori. Aggiunti test prima del codice, con confronto a enumerazioni indipendenti.
2. [V] Costruita ricerca deterministica con vincoli elettrici locali e comuni, famiglie optimizer, budget e
   cancellazione. Conservato il contratto dei comandi e aggiunti risultati diagnostici per i worker UI.
3. [V] Integrati gruppi fisici degli ottimizzatori e correnti condizionate forniti dall'altro ambito. Verificate le
   modifiche manuali, la persistenza, la prestazione e le correzioni emerse dalla review.

## Ricerca e criterio

[V] `sizing.choose` mantiene l'ordine approvato: meno inverter, poi meno modelli inverter, poi rapporto DC/AC piu vicino
a quello richiesto. La distanza del terzo criterio e ora calcolata sul rapporto effettivo: 100/110 e piu vicino a 1
di 100/90, anche se le potenze AC differiscono entrambe di 10. Fonte catalogo e nome ordinano i pareggi. Il criterio
non usa costi, tariffe, energia annuale o NPV.

[V] Una proposta completa gia ottenuta dal posizionatore precedente viene conservata soltanto se tutti i controlli
la verificano. Negli altri casi il motore esplora assegnazioni alternative. Questo percorso rapido conserva le
distribuzioni bilanciate gia valide; non viene usato per concludere che una soluzione non esiste.

[V] La ricerca aggrega moduli elettricamente omogenei: identita e dati del modulo, inclinazione, azimut e destinazione.
Moduli orizzontali non vengono separati per azimut. La precisione angolare resta quella del layout, 0,1 gradi;
non introduce una nuova tolleranza normativa. Sullo stesso MPPT ordinario rimangono uguali tipo, orientamento e
lunghezza delle stringhe. Tracker distinti possono usare lunghezze diverse.

[V] Ogni ramo sceglie ingresso, lunghezza e numero di stringhe, rispettando finestra di tensione, corrente MPPT,
numero di ingressi fisici disponibile, limiti per connettore e corrente comune dell'inverter. Le correnti condizionate
sono verificate sul numero finale di stringhe: un limite dichiarato soltanto per due stringhe non viene riutilizzato
come limite per una. Una lista parziale di dati non replica il suo ultimo valore sui tracker successivi. L'assenza
di una corrente necessaria genera un avviso e impedisce una proposta dichiarata interamente verificata.

[V] Un limite aggregato di capacita per firma e un limite sul numero di tracker necessari eliminano rami impossibili
prima dell'esplorazione dettagliata. La memoria dei fallimenti usa conteggi e stati elettrici, evitando permutazioni
equivalenti di pannelli dello stesso gruppo. Una soluzione terminale attraversa gli stessi controlli usati per le
stringhe del progettista.

[V] Le strategie restano vincoli di instradamento: serpentina puo unire sottocampi con stessa firma e destinazioni
compatibili. La ricerca enumera anche quanti moduli prelevare da pool con destinazioni sovrapposte, senza indebolire
le preferenze esplicite; tre moduli automatici e tre destinati a 1.1 possono formare una stringa da sei su 1.1.
Le strategie per fila conservano i confini della fila; una fila per MPPT occupa un solo ingresso; la U costruisce
tratti simmetrici su coppie di file, con i tratti residui separati. Le scelte manuali mantenute da Completa restano
all'inizio della proposta e conservano i propri moduli.

## Ottimizzatori e gruppi fisici

[V] Per hardware implicito la ricerca considera i modelli optimizer SolarEdge per i quali il catalogo fornisce regole
compatibili, anche con famiglie inverter differenti. Puo scegliere hardware diverso per unita distinte mantenendo
l'ordine e il numero delle unita. La proposta restituisce le voci inverter/optimizer da salvare insieme alle stringhe.
Un optimizer scelto esplicitamente nella proposta o nelle stringhe mantenute resta vincolo del completamento.

[V] Anche il numero effettivo di ottimizzatori e le occupazioni singole/doppie entrano nella ricerca. Le occupazioni
proposte rimangono omogenee per tipo e geometria; i controlli seguono i gruppi effettivi, senza presumere sempre
`ceil(moduli/2)`. Per esempio 28 moduli su 28 gruppi singoli sono verificati come 28 ottimizzatori.

[V] `String.optimizer_group_sizes` viene letto e riscritto nei run. Il modello di progetto e passato al formato 20
nel lavoro coordinato dell'agente principale; questo ambito usa quel campo senza modificare `model.py/settings.py`.
`materialize_optimizer_groups(runs, plant)` rende esplicito il vecchio raggruppamento prima di una modifica UI.
Rimozione e taglio riducono soltanto i gruppi interessati; inversione inverte anche i gruppi; aggiungere un modulo
crea un nuovo gruppo singolo. Ridisegnare una stringa conserva i gruppi trattenuti e rifiuta un ordine che separa
i moduli di uno stesso ottimizzatore. Una partizione incompatibile viene segnalata come verifica fallita.

## Interfacce, budget e prova di completezza

- [V] `stringing.SearchBudget(limit=100000, cancelled=callback)` limita una proposta per stati visitati e controlla
  il callback durante la ricerca. La profondita e limitata prima del limite ricorsivo Python. Entrambi i limiti
  producono `search_complete=False`; non sono una dimostrazione di impossibilita elettrica.
- [V] `plant.proposal(..., search=budget)` restituisce `Plant` con `left`, `notes`, `search_complete`, `search_reason`
  e `search_nodes`. `plant.propose` conserva l'interfaccia storica che restituisce i run.
- [V] `Plant.entries=None` significa conservare l'hardware; una lista ne richiede esplicitamente la sostituzione.
  Questa distinzione e stata corretta dopo la review, con regressione su una proposta ordinaria reale.
- [V] Il dimensionamento usa un budget unico di 200.000 stati e al massimo 2.048 combinazioni inverter, comprendendo
  generazione e ordinamento delle categorie. Non salta una categoria ancora irrisolta per accettarne una successiva.
  Se un assegnamento o la ricerca delle famiglie supera il budget, `Result.ok=False` e `search_complete=False`.
  La cancellazione non applica una scelta parziale.
- [V] Una risposta negativa con ricerca completa riguarda l'intero spazio descritto dai dati forniti e dalla strategia
  selezionata. Una proposta parziale puo restare disponibile per mostrare i moduli fuori, ma non certifica una scelta
  di dimensionamento. I chiamanti UI asincroni e i controlli di adozione sono nell'ambito dell'agente principale.

[V] `plant.build(..., p_dc_by_inverter={numero: serie_oraria})` permette ai controlli di sovraccarico di usare la
produzione reale di ogni inverter. Quando questa mappa e presente, non viene ricostruita una quota dall'aggregato.
Il vecchio argomento aggregato rimane per compatibilita con i chiamanti precedenti; la nuova pipeline passa la mappa.

## Verifiche

[V] Ultimo giro: **126 test passati in 8,892 s** con Python
`C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe`, gruppi:

```text
calcoli.test_global_stringing
calcoli.test_optimizer_partitions
calcoli.test_sizing
calcoli.test_stringing
calcoli.test_optimizers
```

Ruff passa sui tre sorgenti posseduti e sui nuovi test. `git diff --check` non segnala errori.
La review ha riprodotto prima della correzione il crash con `imax_by_strings=[None, {"1": 10}]` sia nella capacita
sia nella cache dei controlli; la regressione ora passa.
La self-review ha poi riprodotto e corretto la falsa impossibilita dei pool con target compatibili diversi.
Verificati target automatico con MPPT imposto, inverter/MPPT espliciti, destinazione non disponibile e completamento
con stringa manuale preesistente: nessuna connessione mantenuta viene riscritta, nessun target non disponibile viene
spostato silenziosamente.

| Caso | Esito verificato |
| --- | --- |
| 19 moduli, due ingressi da massimo 10 | Tutti collegati con stringhe da 10 e 9 |
| Modulo flessibile e modulo con corrente maggiore, ingresso forte unico | Il secondo conserva l'ingresso necessario |
| Due piccoli sottocampi omogenei da 3 | Una stringa valida da 6 |
| Tre moduli auto e tre omogenei con target 1.1 | Stringa valida da 6 su 1.1; verificato anche Completa con altro MPPT occupato |
| Due orientamenti e corrente comune che ammette una sola stringa per unita | Due inverter, stringhe redistribuite |
| Un solo limite di corrente dichiarato per due stringhe | Configurazione finale corretta, nessuna potatura errata a una stringa |
| Sei moduli SolarEdge, primo suggerimento con minimo maggiore | Ricercata famiglia compatibile e hardware salvabile |
| Oracoli esaustivi indipendenti | Conteggi possibili identici su due tracker e su tre tracker/due orientamenti |
| U con 22 moduli su due file | Stringhe simmetriche complete con lunghezze diverse per tracker |
| Gruppi singoli/doppi e modifiche manuali | Conteggi reali, appartenenze conservate e partizioni invalide segnalate |

Misure sintetiche sul PC di verifica, librerie gia caricate:

| Caso | Stati | Tempo |
| --- | ---: | ---: |
| 1.901 moduli, 96 inverter con due ingressi da una stringa | 826, tutti collegati | 0,255519 s |
| Stessi moduli, 95 inverter, capacita totale 1.900 | 2, insufficienza dimostrata | 0,036452 s |
| Cancellazione durante il primo caso | 20, ricerca incompleta | 0,038879 s |

Log delle misure:
`C:\Users\Grasso\dev\meridiana-integra-kimi-9-10\build\global-sizing-20261029-R02\measurements-final-R02.json`.
Questi tempi descrivono le fixture e il PC usati; il budget e per stati, non una garanzia universale di durata.

[V] Review in sola lettura dell'altro ambito: `calcoli.test_electrical_iv` e `calcoli.test_electrical_network`,
16 test passati in 1,463 s. Non modificati i suoi sorgenti. L'allocazione annuale della corrente comune fra tracker
rimane proporzionale e dichiarata: e distinta dall'assegnazione globale verificata qui. Anche le ipotesi su geometria
delle celle, sovrapposizione delle ombre e bypass rimangono esplicite nel rapporto del modello elettrico.

[I] La prova di completezza riguarda catalogo, dati e strategie supportati. Non include costi, lunghezze reali dei
cavi, limiti non documentati, firmware proprietari o sistemi optimizer privi di regole nel catalogo. Non introduce
nuove soglie CEI/UNI: usa le verifiche e le fonti gia registrate nell'audit e nei dati elettrici coordinati.
Nessuna suite generale, build, installazione, modifica al registro richieste o commit in questo ambito.
