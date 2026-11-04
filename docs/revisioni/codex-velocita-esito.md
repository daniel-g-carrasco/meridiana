# R372: indagine sui rallentamenti di Meridiana, 04/11/2026

Stato: indagine conclusa, misure e contenuti verificati. Commit impedito dai permessi del sandbox.

[V] Costi dimostrati: disegno dei grafici durante il trascinamento, disegno della pianta, disposizione ripetuta
dei controlli nel titolo delle Verifiche, lettura delle Impostazioni e catture della transizione di File.
Il confronto padre-figlio identifica un aggravio nel commit `96dc22f`.

[V] I costi di primo uso di Produzione e Consumi sono misurati; i precisi picchi di 280 e 479 ms del file
del 03/11 non hanno un'attribuzione certa. Le condizioni originali non registravano se le pagine fossero pronte
e se l'anno fosse ancora in calcolo. Il calcolo concorrente causa un ulteriore peggioramento riprodotto qui.

Le prove sono 105 processi riusciti, organizzati in 35 serie da tre. Il programma resta invariato.
Il commit richiesto e' impedito dai permessi del sandbox sui metadati Git, come documentato in fondo.

## Perimetro e metodo

Cartella: `C:\Users\Grasso\dev\meridiana-wt-r10-velocita`. I percorsi relativi del rapporto partono da qui.

[V] Il codice del programma resta invariato. Le esclusioni A/B sono applicate soltanto in memoria dal processo
di prova, con `docs/prestazioni/2026-11-04/probe.py`. Non sono correzioni da integrare.

[V] Base del lavoro: `b59f832`, ramo `r10-velocita`. Python 3.12.6, PySide6 6.12.0, Windows 26100,
piattaforma Qt `windows`, Dell a rapporto 2. Finestra 1600 x 960 pixel logici. I dati grezzi stanno in
`docs/prestazioni/2026-11-04/`. `environment.json` conserva le versioni delle dipendenze.

[V] Ogni serie utilizzata per le conclusioni comprende tre processi distinti, eseguiti in sequenza.
I prospetti riportano mediana e intervallo minimo-massimo; lo scarto e' massimo meno minimo.
`summary.json` conserva anche i tre valori di ogni metrica e lo scarto numerico.
I profili hanno una strumentazione aggiuntiva: campionamento del solo filo principale, cronometri di funzioni
e tempi degli eventi Qt attraverso `QApplication.notify`. I loro tempi sono inclusivi e non vanno sommati
fra chiamanti e chiamati, ne' scambiati per i tempi delle prove senza strumentazione.
Gli intervalli sono gli estremi osservati su tre prove, non intervalli di confidenza statistica.

[V] `action_ms` misura l'azione, compresi i cicli degli eventi fra i passi del trascinamento.
Un trascinamento contiene quaranta pause richieste di 16 ms. `blocked_ms` somma soltanto gli intervalli
del battito maggiori di 30 ms: non e' tempo CPU e la differenza fra due somme non e' un guadagno equivalente.
L'attraversamento della soglia puo' far cambiare molto questa somma anche quando la durata cambia poco.

[V] I primi tentativi senza cataloghi compilati usavano il testo inglese. Sono conservati come esplorativi,
esclusi dalle mediane. Le serie `it-screen-*` seguono la compilazione dei cataloghi italiani.
Anche la prima prova fuori dall'area visibile resta esplorativa. Le conclusioni sui trascinamenti
usano le serie ripetute visibili sul Dell.

## Confronto storico: condizioni da conservare

[V] I due file indicati nell'incarico contengono una sola misura ciascuno:
`2026-10-25/base-schermo-correzioni-4.json` e `2026-11-03/tutto-schermo-6042b8a.json`.
Non documentano da soli una regressione causata dal codice. Il carico concorrente e i driver non sono
controllati qui; WMI e l'identificativo del processore sono inaccessibili nel sandbox.
I JSON storici non conservano l'hash del progetto: non si puo' verificare che il campione attuale
sia identico a quello di allora. La copia compatibile permette il confronto odierno fra versioni.

[V] Il progetto di prova attuale e' in formato 16; `92c760e` legge fino al 13.
Per il confronto sulla stessa geometria e' stata preparata una copia nel formato del vecchio lettore:
quattro edifici, due sottocampi, 778 moduli sia sulla revisione vecchia sia sulla nuova.
Le tre chiavi non conosciute sono `network`, `network_consent` e `variants[0].design.energy.inverter_maker`.
La copia R02 viene riaperta dal vecchio lettore senza avvisi. Originale e copia hanno hash registrati in
`sample-conversion_R02.json`. La copia serve soltanto alle prove e resta in `build/speed/`.

[V] Due preparazioni sono state scartate: la prima lasciava la chiave `inverter_maker` nel dizionario
dell'energia e faceva apparire un avviso modale; la R01 perdeva i sottocampi perche' il vecchio lettore consuma
il dizionario passato. La R02 usa una copia profonda e verifica due sottocampi dopo la riapertura.
Le prove interrotte non entrano nei confronti.

[V] Il campo `opened.year_ms` di `tools/fluidity.py` attende `session.good_results()`, cioe' i layout riusciti,
non il risultato della produzione. Non e' utilizzabile come misura del completamento dell'anno energetico.
Le prove con dati energetici aggiunti attendono esplicitamente un risultato `sim` valido prima dei gesti.

## Esiti dei sei gesti

### Riferimento con anno energetico e grafici effettivi

[V] Serie `it-screen-weather-all-1/2/3.json`: stesso progetto, meteo registrato di Rho, anno calcolato
interamente in ciascuno dei tre processi prima dei gesti, pagine gia' costruite. Il risultato energetico
resta presente durante tutta la sequenza; dopo il primo ingresso sono visibili un grafico in Produzione,
uno in Consumi e due in Economia. Mediana [minimo; massimo], ms:

| Gesto | Azione | Blocco peggiore | Somma dei blocchi |
|---|---|---|---|
| Impianto, primo ingresso | 90,9 [88,2; 138,3] | 94,5 [91,9; 140,5] | 145,9 [144,1; 210,8] |
| Produzione, primo ingresso | 35,1 [35,0; 35,7] | 65,7 [63,0; 75,6] | 105,0 [102,3; 113,4] |
| Consumi, primo ingresso | 17,1 [16,7; 17,7] | 49,5 [49,1; 51,6] | 49,5 [49,1; 87,0] |
| File, prima chiusura | 81,8 [78,6; 81,9] | 157,9 [156,9; 164,5] | 228,2 [226,3; 245,2] |
| Bordo destro, trascinato in Modellazione | 1862,9 [1790,6; 1918,6] | 50,2 [44,2; 51,7] | 1593,6 [1555,6; 1662,8] |
| Finestra ridimensionata, sequenza base | 810,1 [795,5; 831,9] | 53,1 [53,1; 62,0] | 631,5 [612,2; 643,3] |

[V] Tornando in Consumi nella parte `charts` della stessa sequenza completa, il trascinamento destro costa
2786,8 [2778,2; 2811,3] ms, con 1841,9 [1755,0; 1843,0] ms di somma dei blocchi.
Il costo del bordo con grafici popolati e' quindi riprodotto; il primo ingresso da 479 ms del 03/11,
invece, resta distinto da questi ingressi con le pagine gia' preparate.

### Riferimento attuale, tre sequenze complete sul Dell

[V] Serie `it-screen-current-all-1/2/3.json`, progetto originale in formato 16, cataloghi italiani.
In questa configurazione il sandbox rifiuta i socket con `WinError 10013`: PVGIS 5.3 e 6 non restituiscono
il meteo e non vengono creati grafici effettivi. Questa tabella descrive tale stato, non un anno energetico
calcolato con successo. La presenza delle pagine e la presenza dei grafici sono due cose diverse.
Ogni cella e' mediana [minimo; massimo], in ms. La prima chiusura di File e il primo ingresso di ogni fase
sono tenuti distinti dalla visita successiva.

| Gesto | Azione | Blocco peggiore | Somma dei blocchi |
|---|---|---|---|
| Impianto, primo ingresso | 119,8 [118,4; 141,7] | 277,2 [274,4; 315,8] | 454,5 [451,8; 516,5] |
| Produzione, primo ingresso | 37,9 [36,6; 40,6] | 47,7 [46,1; 53,5] | 89,4 [86,8; 98,1] |
| Consumi, primo ingresso | 17,0 [14,7; 17,7] | 0,0 [0,0; 32,2] | 0,0 [0,0; 32,2] |
| File, prima chiusura | 92,6 [80,5; 121,3] | 183,5 [156,7; 216,6] | 265,6 [227,4; 321,6] |
| Bordo destro, trascinato in Modellazione | 2027,0 [1791,6; 2526,7] | 49,0 [46,3; 69,5] | 1750,1 [1585,4; 2217,0] |
| Finestra ridimensionata, sequenza base | 790,2 [763,9; 816,3] | 51,6 [51,2; 52,8] | 611,6 [602,7; 640,2] |

### Impianto: risposta del calcolo e aggiornamenti sincroni

[V] Nei tre profili `it-screen-events-all-*`, il primo ingresso comprende la risposta del calcolo energetico.
`_energy_done` occupa 224,62 [220,50; 232,71] ms sul filo principale. Al suo interno e' chiamato
`_start_plant(now=True)`: 154,34 [152,64; 163,59] ms, compresa la risposta dell'impianto.
Le Verifiche sono riempite due volte nel gesto: `_fill` totalizza 112,50 [107,31; 119,66] ms.
Il pannello dell'impianto viene aggiornato tre volte: `PlantInspector.show_plant` totalizza
43,69 [42,19; 45,55] ms. Questi numeri si sovrappongono e non si sommano.

[V] La chiamata `job.run()` avviene qui direttamente sul filo principale: il lavoro e' dichiarato come job,
ma il ramo `now=True` non lo consegna al pool. Il profilo distingue questa esecuzione dai job dei fili di lavoro.
La sola costruzione delle pagine dei risultati non spiega il blocco: all'inizio di queste prove le tre pagine
sono gia' costruite.

[I] Questo spiega una parte del ritardo di ingresso nella configurazione attuale. Non dimostra che tutto
il divario fra le due singole misure storiche provenga da una nuova modifica specifica.
Il ramo sincrono esiste gia' nel primo commit pubblico.

[V] La prova `async-plant-base`, tre passate, manda il solo job al pool anche nel caso `now=True`.
Il blocco peggiore scende a 193,9 [185,1; 206,1] ms, contro 277,2 [274,4; 315,8] ms del riferimento.
La somma dei blocchi resta 455,4 [435,1; 494,6] ms, contro 454,5 [451,8; 516,5] ms.
Si riduce il picco, senza risolvere la fluidita' complessiva. Restano da alleggerire gli aggiornamenti
del pannello e le due ricostruzioni delle Verifiche.

### Produzione e Consumi: distinguere pagine pronte e pagine ancora da costruire

[V] Il blocco storico di 479 ms di Consumi non e' stato riprodotto nelle tre sequenze complete con pagine
gia' preparate. Le ipotesi sull'origine di quel singolo valore restano non verificate.

[V] Disabilitando soltanto la costruzione durante il riposo (`--mode no-rest`), i tre profili mostrano
una costruzione al primo uso. `LazyPage.real` costa 109,10 [107,23; 109,13] ms in Produzione e
172,01 [165,19; 241,16] ms in Consumi. La sola creazione dei cinque oggetti `Chart` di Consumi costa
37,46 [37,16; 61,88] ms. Il resto include campi, stile, collegamenti e riproduzione dei dati differiti.
Sono tempi con strumentazione, non stime del guadagno di una correzione.

[V] Nelle prove con pagine pronte `LazyPage.real` non costruisce nulla al cambio di fase.
In Produzione restano aggiornamento dell'ispettore e impaginazione: `_show_inspector`
25,61 [23,52; 27,35] ms nel profilo; gli aggiornamenti Qt della finestra totalizzano
73,10 [66,84; 75,77] ms distribuiti su piu' eventi.

[I] Il primo uso sposta sul clic un costo reale. Il preparatore durante il riposo lo evita solo se ha avuto
tempo di terminare. Questa e' una causa dimostrata del caso ancora da costruire, non una spiegazione
verificata dei precisi 280 e 479 ms del file del 03/11.

[V] Con anno valido ma preparazione delle pagine disabilitata, tre prove senza profilo
(`weather-cold-base`) danno 149,9 [149,5; 152,3] ms di azione in Produzione e
222,6 [215,3; 230,9] ms in Consumi, contro 35,1 [35,0; 35,7] e 17,1 [16,7; 17,7] ms con pagine pronte.
Il costo aggiunto al clic e' quindi 114,8 e 205,5 ms nelle rispettive mediane.
Il blocco peggiore e' 152,7 [152,3; 153,6] ms in Produzione e 226,1 [219,1; 235,2] ms in Consumi.
Neppure questa condizione riproduce da sola il preciso blocco di 479 ms del riferimento storico.

[V] I tre profili della stessa condizione (`weather-cold-profile-base`) localizzano la costruzione in
`LazyPage.real`: 122,00 [120,74; 129,29] ms in Produzione e 220,56 [217,30; 236,50] ms in Consumi.
In Consumi i cinque `Chart.__init__` occupano 37,81 [37,23; 37,84] ms inclusi nel totale.
Il primo uso paga quindi soprattutto costruzione, stile e riproduzione dei dati differiti, oltre al
primo disegno che segue nel ciclo degli eventi. I profili di queste condizioni restano separati
da quelli senza meteo e dalle prove senza strumentazione.

### File: lettura anticipata delle Impostazioni, immagini della transizione e attribuzione del battito

[V] I tre profili registrano due letture complete delle Impostazioni tra i gesti, per un totale
di 392,68 [382,10; 429,33] ms. Non si deve attribuire questo totale alla sola chiusura di File:
`_read_settings_ahead` parte dopo l'apertura, durante la pausa dello strumento.

[V] Escludendo questa sola lettura (`no-settings`, tre prove), la prima chiusura passa da
92,6 [80,5; 121,3] a 31,6 [31,2; 31,8] ms di azione; la somma dei blocchi passa da
265,6 [227,4; 321,6] a 107,3 [104,5; 108,9] ms. La lettura crea pagine e lavoro differito
che pesano anche sulla successiva cattura e impaginazione.

[V] La transizione di chiusura esegue due `motion.picture`: 98,53 [96,43; 100,32] ms complessivi
nei tre profili. La cattura e' un `grab` della finestra nel rettangolo di File, a rapporto 2.
La chiamata diretta `motion.leave` occupa 90,85 [88,20; 91,86] ms; il secondo `grab` avviene dopo,
nel ciclo degli eventi. Ancora: sono tempi inclusivi, non contributi da sommare.

[V] Il battito del benchmark non viene azzerato prima di ciascun gesto. Se la lettura delle Impostazioni
finisce la pausa dopo l'ultimo battito elaborato, una parte del suo ritardo entra nel primo intervallo della
chiusura successiva. L'A/B `reset-heartbeat` conserva l'azione ma riparte con il battito all'inizio del gesto:
la chiusura costa 82,1 [80,2; 84,9] ms di azione e 155,3 [151,8; 163,3] ms di somma dei blocchi.
Non e' un'accelerazione del programma: cambia l'attribuzione del tempo fra due gesti.

[V] Senza caricamento anticipato, i tre profili misurano le due immagini in 44,47 [44,02; 45,44] ms,
contro 98,53 [96,43; 100,32] ms con le pagine delle Impostazioni create. Il costo indiretto sulla cattura
e sulla disposizione e' quindi riprodotto, oltre alla lettura durante la pausa.

[V] La prova `instant-file-close-base` elimina soltanto `motion.leave`, conservando l'apertura animata e
il caricamento anticipato. La prima chiusura costa 20,7 [20,6; 26,6] ms di azione, con 147,9 [131,0; 152,1] ms
di somma dei blocchi. Il risparmio mediano sull'azione e' 71,9 ms. Non si somma al risparmio di `no-settings`:
le due esclusioni toccano in parte lo stesso lavoro.

[V] L'A/B senza tutte le animazioni impedisce anche `_entered` e quindi il caricamento anticipato delle
Impostazioni. Non e' un esperimento che isola la sola animazione; per questo si usa il confronto precedente.

### Bordo destro e ridimensionamento: disegno e impaginazione durante ogni passo

[V] Tre sequenze senza 3D mantengono il problema: trascinamento destro della sequenza base
1962,0 [1854,1; 2013,1] ms, contro 2027,0 [1791,6; 2526,7] ms con 3D.
Gli intervalli si sovrappongono. Il risultato non sostiene che il 3D sia la causa dominante attuale.
Il sostituto senza 3D genera un avviso di attesa del primo fotogramma all'avvio: per questo confronto si usano
soltanto i gesti successivi, a finestra assestata.

[V] Nei tre profili del bordo destro ci sono migliaia di richieste a `CardTitle.sizeHint` in quaranta passi.
Gli eventi `UpdateRequest` della finestra comprendono il lavoro nativo di Qt e la presentazione a Windows.
I campioni Python non distinguono internamente tutti i costi C++ o del driver.

[V] Le tre serie `edges` sul progetto originale isolano il contributo dei componenti. Si riporta la durata
dell'azione, mediana [minimo; massimo] in ms; i blocchi e tutte le altre metriche sono in `summary.json`.

| Esclusione nel processo di prova | Bordo destro, Modellazione | Bordo destro, Consumi | Ridimensionamento in Consumi |
|---|---|---|---|
| Nessuna, `current-edges` | 1987,7 [1985,0; 2026,9] | 1605,7 [1593,7; 1695,0] | 716,3 [698,9; 742,7] |
| Controlli nel titolo, `no-tools-edges` | 1836,7 [1834,5; 1837,8] | 1468,6 [1415,9; 1620,8] | 646,5 [645,5; 660,6] |
| Disegno della pianta, `no-plan-paint-edges` | 1543,8 [1539,1; 1558,7] | 1622,7 [1617,4; 1996,5] | 712,5 [705,4; 724,9] |
| Disegno delle righe di Verifiche, `no-checks-paint-edges` | 1842,4 [1824,9; 1957,0] | 1480,5 [1468,5; 1516,3] | 692,8 [664,6; 728,2] |
| Disegno della scheda Proprieta'/Dati, `no-right-paint-edges` | 1890,9 [1853,9; 2229,6] | 1498,1 [1497,4; 1503,1] | 675,6 [649,7; 676,2] |

[V] Togliere il disegno della pianta risparmia 443,9 ms nella mediana del trascinamento in Modellazione.
In Consumi, dove la pianta e' nascosta, non risulta un guadagno. Le righe delle Verifiche contribuiscono
per circa 125-145 ms alla mediana del gesto nelle due fasi. Questi risparmi non si sommano fra loro:
le esclusioni cambiano il lavoro di ridisegno e la sua distribuzione nel ciclo degli eventi.
`no-right-paint` agisce sulla scheda Proprieta'/Dati, `docks[1]`; la scheda Verifiche resta disegnata.

[V] I controlli del titolo pesano anche quando il loro disegno non domina: eliminandoli la mediana
scende di 151,0 ms in Modellazione e di 137,1 ms in Consumi. Il loro calcolo della disposizione viene
richiesto ripetutamente da `sizeHint`, `minimumSizeHint`, `place`, `top_pad`, `row_height` e `body_height`.

[I] Il rimedio da provare e' conservare la disposizione gia' calcolata e ricalcolarla quando cambiano
larghezza, testi, visibilita', font o scala; per il disegno della pianta, un'immagine durante il trascinamento
con un ridisegno completo alla fine. Le esclusioni mostrano un costo eliminabile, non misurano ancora
una correzione che conservi tutti i comportamenti.

[V] Il ridimensionamento combina gli stessi componenti con gli eventi di nuova geometria.
Nei tre profili della sequenza base `_arrange` viene eseguito una volta, con costo inferiore a pochi ms:
non spiega le centinaia di ms del gesto. Rimane un costo del percorso nativo di aggiornamento e presentazione
che questi campioni Python non scompongono completamente. La causa interna del residuo non e' stata trovata.

### Grafici: confronto con dati, senza confonderli con le pagine vuote

[V] Tre prove `weather-edges` e tre `weather-chartless-edges`, tutte con lo stesso anno e nuovi widget,
mantengono dati, scena grafica e ridimensionamento; nella seconda serie viene escluso `Plot.paintEvent`.
Durata dell'azione, mediana [minimo; massimo], ms:

| Caso | Bordo destro, Modellazione | Bordo destro, Consumi | Ridimensionamento in Consumi |
|---|---|---|---|
| Disegno completo | 2061,4 [2019,7; 2082,7] | 2738,7 [2466,1; 2742,3] | 867,6 [849,7; 873,2] |
| Disegno dei grafici escluso | 2024,2 [1996,3; 2028,7] | 1681,4 [1678,5; 1685,2] | 758,2 [742,1; 767,7] |

[V] Il risparmio mediano e' 1057,3 ms sul trascinamento in Consumi e 109,4 ms sul ridimensionamento.
Nel trascinamento gli intervalli osservati non si sovrappongono. In Modellazione, dove i grafici sono
nascosti, non emerge un effetto confrontabile: gli intervalli si sovrappongono.
Nel ridimensionamento la somma dei blocchi resta quasi uguale, pur con un'azione piu' breve:
e' un altro motivo per conservare entrambe le metriche.

[I] Il disegno ripetuto del grafico durante ogni cambiamento di larghezza e' una causa dominante del costo
del bordo in Consumi. E' una causa dimostrata del ritardo attuale, non un nuovo commit colpevole gia' isolato:
il README delle prestazioni registrava la difficolta' dei bordi con grafici anche il 25/10.
La correzione da provare e' una rappresentazione ferma durante il trascinamento e il ridisegno completo
quando la larghezza si assesta, come gia' avviene per il 3D. Il guadagno della correzione resta da misurare:
qui e' misurata l'esclusione del disegno.

[V] Escludendo soltanto il disegno della scheda Dati, con i grafici ancora attivi
(`weather-no-right-paint-edges`, tre prove), il bordo di Consumi costa 2445,5 [2115,3; 2487,3] ms.
Il risparmio mediano e' 293,2 ms rispetto ai 2738,7 ms del controllo; gli intervalli si sovrappongono
parzialmente. Il costo non appartiene quindi tutto alla scheda Dati, ne' tutto al grafico.

### Calcolo concorrente: il filo di lavoro non rende automaticamente libera la finestra

[V] `weather-starting-all` segue il flusso originale dello strumento, con cache meteo disponibile ma senza
attendere esplicitamente l'anno. Tre processi nuovi, senza profilatore, danno queste durate dell'azione:

| Gesto | Calcolo non atteso, mediana [minimo; massimo], ms |
|---|---|
| Impianto, primo ingresso | 173,6 [168,9; 174,3] |
| Produzione, primo ingresso | 86,8 [73,5; 97,9] |
| Consumi, primo ingresso | 88,6 [82,5; 93,9] |
| File, prima chiusura | 496,0 [483,7; 657,6] |
| Bordo destro, Modellazione | 13392,3 [13322,7; 13803,9] |
| Finestra ridimensionata, sequenza base | 1365,0 [1351,5; 1376,7] |

[V] Questa condizione peggiora anche gesti che senza calcolo concorrente erano rapidi, con pagine gia'
costruite e senza grafici popolati. I valori non vanno mescolati con quelli ad anno terminato.
Il benchmark originale non attende questo termine: e' una variabile sostanziale del confronto.

[V] Nei tre profili mirati con calcolo concorrente e costruzione al primo uso
(`weather-starting-cold-profile-base`), `LazyPage.real` di Consumi occupa
486,16 [481,28; 521,10] ms, contro 220,56 [217,30; 236,50] ms con anno gia' disponibile.
I costruttori e le richieste di dimensione risultano amplificati. In ciascun processo si osservano
23 chiamate a `_energy_step`, per un totale di 4,50 [3,77; 4,82] ms: il costo diretto degli aggiornamenti
di avanzamento non spiega le lunghe fermate.

[I] Rimane una contesa di esecuzione fra nucleo e interfaccia, compatibile con CPU/GIL e con i numerosi
passaggi fra Qt e Python. Non e' stata isolata la quota CPU rispetto alla quota GIL. Il profilatore aggiunge
esso stesso passaggi Python per gli eventi Qt: i tempi dei profili concorrenti servono a localizzare il lavoro,
non a quantificare il guadagno di una correzione.

[I] La combinazione di primo uso e calcolo concorrente puo' produrre costi della stessa grandezza dei picchi
storici. Non dimostra che fosse la condizione del 03/11: per i precisi 280 e 479 ms la causa originale resta
non accertata. Per questo non propongo una correzione basata soltanto su quella singola misura.

## Quali commit hanno aggiunto costi

[V] `92c760e` non e' antenato di `HEAD`: appartiene alla storia precedente alla pubblicazione.
La ricerca usa quindi il primo commit pubblico, un campione intermedio e il confronto diretto padre-figlio,
con il benchmark corrente e la medesima copia R02 del progetto. Non e' una bisezione Git conclusa su tutti
i sei gesti.

| Revisione, tre prove `edges` | Bordo destro, Modellazione | Bordo destro, Consumi | Ridimensionamento in Consumi |
|---|---|---|---|
| `92c760e`, riferimento precedente alla pubblicazione | 1603,8 [1591,0; 1654,8] | 1868,7 [1811,3; 2006,7] | 860,7 [845,4; 882,4] |
| `3b1d8c8`, primo commit pubblico del 25/10 | 1501,1 [1425,0; 1756,0] | 1961,5 [1948,8; 2303,1] | 794,3 [786,3; 844,5] |
| `9dce421`, campione del 30/10 | 1660,7 [1621,6; 1689,1] | 1295,2 [1285,7; 1329,6] | 643,3 [615,9; 691,9] |
| `fa847b0`, padre di `96dc22f` | 1736,3 [1716,3; 1757,2] | 1329,3 [1310,5; 1364,6] | 616,5 [597,6; 618,6] |
| `96dc22f`, controlli nel titolo delle Verifiche, 03/11 | 1955,5 [1938,0; 1984,7] | 1560,3 [1551,2; 1575,9] | 712,7 [701,8; 720,1] |
| `b59f832`, attuale | 1991,6 [1944,7; 2087,4] | 1614,8 [1563,9; 1904,0] | 698,7 [695,0; 708,6] |

Le celle sono durate dell'azione, mediana [minimo; massimo], in ms.

[V] Il confronto con il padre diretto attribuisce a `96dc22f` un aggravio di 219,2 ms in Modellazione,
231,0 ms in Consumi e 96,2 ms nel ridimensionamento in Consumi. Gli intervalli osservati non si sovrappongono.
Questo identifica un contributo preciso alla regressione, non l'origine di ogni costo della finestra.

[V] La storia del codice individua inoltre:

- `6c4bc5d`, 02/11: introduce `LazyPage` e il costo di costruzione al primo uso.
- `cf04cb2`, 02/11: introduce la preparazione durante il riposo, che rende essenziale registrare se la pagina e' gia' pronta.
- `371572f`, 30/10: introduce `_read_settings_ahead`.
- `7828955`, 30/10: introduce `motion.leave`, con le immagini per la chiusura di File.

[I] Questi ultimi sono i commit che introducono i percorsi misurati dalle esclusioni A/B attuali.
Non sono stati misurati tutti contro il rispettivo padre: non si assegna loro il preciso divario delle
singole misure storiche. Per il restante costo della pianta e per la presentazione nativa non e' stato
isolato un primo commit responsabile.

[V] Anche il commit esatto `6042b8a` e' rimisurato tre volte, nello stato senza meteo del sandbox:
Produzione 40,7 [35,8; 46,2] ms di azione, Consumi 15,5 [15,0; 17,4] ms e prima chiusura di File
80,3 [78,0; 82,1] ms. La diversa condizione rispetto al file storico conta anche eseguendo lo stesso commit;
non si attribuisce il divario delle due date alle sole modifiche successive.

## Proposte, priorita' e rischio

L'ordine segue il guadagno osservato nelle esclusioni e il rischio dell'intervento. Nessuna modifica
al programma e' applicata. I risparmi di esclusioni che si sovrappongono non vanno sommati.

| Priorita' | Intervento da provare | Evidenza del guadagno o costo evitabile | Rischio |
|---|---|---|---|
| 1 | Tenere un'immagine del grafico mentre cambia larghezza, ridisegnarlo quando si assesta | Disegno escluso: 1057,3 ms in meno sul bordo di Consumi, 109,4 ms sul ridimensionamento. La soluzione completa non e' misurata | Medio: immagine coerente con il rapporto dei pixel, fine del gesto, nuovi dati arrivati durante il trascinamento |
| 2 | Tenere un'immagine della pianta durante il trascinamento del bordo | Disegno escluso: 443,9 ms in meno in Modellazione. La soluzione completa non e' misurata | Medio: trasformazione della vista, sovrapposizioni e ripresa dell'interazione dopo il gesto |
| 3 | Calcolare una sola volta la disposizione dei controlli del titolo per la stessa geometria e riusarla fra le richieste di dimensione | Controlli esclusi: 151,0 ms in meno in Modellazione e 137,1 ms in Consumi. Il confronto padre-figlio dimostra l'aggravio di `96dc22f` | Basso-medio: invalidazione su testo, visibilita', font e scala; preservare tutte le righe quando la scheda e' stretta |
| 4 | Conservare le Impostazioni gia' lette e invalidarle solo quando cambia cio' che mostrano; costruire e aggiornare per sezione | Lettura anticipata esclusa: prima chiusura da 92,6 a 31,6 ms. Due letture complete fra i gesti: circa 393 ms complessivi nei profili | Medio: evitare valori vecchi al cambio di progetto o configurazione |
| 5 | Rendere leggero il primo schermo delle pagine, distribuire la preparazione in passi brevi sul ciclo Qt | Pagina gia' pronta: evita 114,8 ms in Produzione e 205,5 ms in Consumi nelle mediane con anno valido | Medio: la costruzione dei widget resta sul filo Qt; i segnali e i dati differiti devono vedere una pagina coerente |
| 6 | Riempire le Verifiche una volta sola per lo stato finale e aggiornare soltanto le parti dell'ispettore cambiate | Due `_fill` nel primo Impianto costano circa 112,5 ms nel profilo. Il risparmio di una sola ricostruzione e' dedotto, non misurato con una correzione | Basso-medio: non perdere il risultato piu' recente dei job |
| 7 | Mandare il ricalcolo dell'impianto al pool anche nel ramo `now=True`, insieme al punto precedente | Provato da solo: picco da 277,2 a 193,9 ms, somma dei blocchi sostanzialmente invariata | Basso-medio: controllare i chiamanti che prima ricevevano il risultato subito; insufficiente da solo per la fluidita' |

[I] Il caso di calcolo concorrente richiede inoltre una prova del nucleo in un processo separato, o un profilo
mirato che permetta di ridurre la contesa e i passaggi Qt/Python. Il potenziale e' alto, ma non e' misurata
una correzione: serializzazione, trasferimento dei risultati e cancellazione sono rischi maggiori rispetto
agli interventi locali della tabella. La prova va fatta prima di scegliere quella modifica architetturale.

[V] Per File e' misurata anche una scelta piu' diretta: chiusura senza transizione, 20,7 ms contro 92,6 ms
di azione, guadagno mediano 71,9 ms. E' una scelta visiva di Daniel. Per mantenere la transizione si puo'
valutare il riuso delle immagini quando sono ancora valide; il relativo guadagno non e' stato misurato.

[I] Come primo lotto raccomando i punti 3 e 4: costo circoscritto, collegamento diretto con modifiche
identificate, verifica semplice contro queste serie. I punti 1 e 2 hanno il potenziale maggiore e richiedono
la prova della soluzione completa a schermo. Il solo spostamento di un job in background non basta.

## Comandi, controlli e limiti

### Ambiente e riproduzione

Comandi PowerShell eseguiti nella radice del worktree:

```powershell
$python = 'C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONPATH = 'tests;src'
$env:PATH = 'C:\Users\Grasso\dev\meridiana\.venv\Lib\site-packages\PySide6;' + $env:PATH
& $python tools/compile_po.py --python
& $python docs/prestazioni/2026-11-04/prepare_sample.py
& $python docs/prestazioni/2026-11-04/batch.py docs/prestazioni/2026-11-04/batch-initial.json
& $python docs/prestazioni/2026-11-04/batch.py docs/prestazioni/2026-11-04/batch-ab.json
& $python docs/prestazioni/2026-11-04/batch.py docs/prestazioni/2026-11-04/batch-data-history.json
& $python docs/prestazioni/2026-11-04/batch.py docs/prestazioni/2026-11-04/batch-final.json
& $python docs/prestazioni/2026-11-04/batch.py docs/prestazioni/2026-11-04/batch-concurrent.json
& $python docs/prestazioni/2026-11-04/summarise.py
& $python docs/prestazioni/2026-11-04/profile_summary.py
& $python docs/prestazioni/2026-11-04/profile_summary.py it-screen-no-rest-base
& $python docs/prestazioni/2026-11-04/profile_summary.py it-screen-no-settings-profile-base
```

Le specifiche `batch-initial`, `batch-ab`, `batch-data-history`, `batch-final` e `batch-concurrent`
elencano nomi, argomenti ed esclusioni di ogni serie.
`batch.py` esegue tre processi per serie, uno alla volta. I comandi non sovrascrivono una misura gia' presente;
la ripresa conserva i risultati completati. I log dei tentativi interrotti sono separati da quelli dei nuovi tentativi.
Per una nuova passata singola usare un nome di uscita nuovo, ad esempio:

```powershell
& $python docs/prestazioni/2026-11-04/probe.py --on-screen --sequence edges --out build/speed/nuova-passata.json
```

La preparazione iniziale degli archivi e' stata fatta con `git archive` e `tarfile`, contro gli oggetti Git locali.
`prepare_archives.py` ripete la preparazione senza modificare i metadati Git e controlla i sorgenti estratti.
L'oggetto `92c760e`, esterno alla storia pubblica, deve essere disponibile nel clone locale.

### Dati meteorologici delle prove aggiuntive

[V] `prepare_weather.py`, richiamato dal terzo batch, usa esclusivamente le risposte gia' registrate in
`tests/calcoli/riferimenti/`, per le stesse coordinate del progetto di Rho. Le chiamate HTTP sono sostituite
nel solo preparatore dalle risposte registrate; durante le misure il programma legge la cache temporanea.
Non sono stati richiesti dati a un servizio a pagamento.

[V] La prima preparazione, conservata in `weather-cache.json`, falliva la validazione dei dati incorporati:
`meteo.usable` non riconosce l'etichetta `PVGIS-SARAH3`. Il programma tentava quindi un nuovo download,
rifiutato dal sandbox, e la prova veniva interrotta per mancanza di un risultato `sim` valido.
La R01 della cache normalizza soltanto quell'etichetta a `SARAH-3`. Gli hash delle colonne orarie prima
e dopo sono identici in `weather-cache_R01.json`: nessun valore meteorologico e' modificato.
E' una preparazione diagnostica della cache, non una correzione del lettore del programma.

Le modalita' con dati verificano un risultato `sim` prima dei gesti e registrano il numero di grafici realmente
creati e visibili. La preparazione dell'anno e' separata dai tempi dei gesti. Nelle successive esclusioni del
disegno lo stesso risultato del nucleo puo' essere riusato, soltanto con la medesima chiave degli input:
finestra, pagine e grafici sono sempre nuovi. Il JSON dichiara se la preparazione ha usato questa cache.

### Verifiche della consegna

[V] `verify_artifacts.py`: 35 serie, 105 risultati presenti, tre ripetizioni per serie, stessa sequenza
in ciascuna, JSON coerenti, progetto originale e copia R02 con hash invariati, nessuna differenza nei sorgenti
di `src`, `tests`, `tools` e `po`. Le due tabelle di riferimento del rapporto e i principali guadagni sono
confrontati automaticamente con i dati grezzi. Il manifesto con gli hash di ogni risultato e' `verification.json`.

[V] `prepare_archives.py`: sei snapshot controllati contro i blob Git, normalizzando solo CRLF in LF.
`archives.json` conserva hash originali, hash dei blob e hash normalizzati. Non ci sono altre differenze
nei file controllati: `window.py`, `model.py`, `cards.py` di ogni snapshot.

[V] Lint completo `python -m ruff check --select F,E9,B .`: passato.
`python -W default -m unittest nucleo.test_release`: 6 test passati, con `QT_QPA_PLATFORM=offscreen`.
All'uscita compare un `ResourceWarning` della cartella temporanea ripulita implicitamente dal test.
`git diff --check`: passato. Non e' stata rilanciata tutta la suite del programma, che non e' modificato.

Comandi dei controlli:

```powershell
& $python docs/prestazioni/2026-11-04/prepare_archives.py
& $python docs/prestazioni/2026-11-04/verify_artifacts.py
& $python -m ruff check --select F,E9,B .
$env:QT_QPA_PLATFORM = 'offscreen'
& $python -W default -m unittest nucleo.test_release
git diff --check
```

[V] L'intervento non modifica gli altri rami, i checkout di avvio, i dati reali di Meridiana o gli archivi tecnici.
Le copie di lavoro e il risultato energetico temporaneo restano in `build/speed/`, escluso da Git.
Il file di incarico preesistente non e' modificato.

Nota di memoria proposta, `meridiana-prestazioni`: prima di confrontare i tempi registrare hash del progetto,
stato di costruzione delle pagine, anno disponibile o in corso e grafici effettivamente presenti.
`opened.year_ms` attende i layout, non l'anno: usarlo come completamento energetico porta a confrontare
condizioni diverse. La memoria in `C:\Users\Grasso\.claude` non e' stata modificata.

### Permessi Git

[V] Il sandbox ha rifiutato la creazione di un worktree temporaneo:

```text
git worktree add --detach .speed-worktrees/base-92c760e 92c760e
fatal: could not create directory of 'C:/Users/Grasso/dev/meridiana/.git/worktrees/base-92c760e': Permission denied
```

[V] Le revisioni vengono quindi estratte con `git archive` in sottocartelle di `build/speed/`, senza
cambiare altri rami. Il benchmark corrente e' eseguito contro i loro sorgenti; il campo `commit` del JSON
viene impostato alla revisione estratta, non al repository esterno che contiene la cartella.

[V] Anche lo staging e' impedito: la cartella dei metadati del worktree e' fuori dall'unica radice scrivibile.

```text
git add -- docs/prestazioni/2026-11-04/probe.py docs/prestazioni/2026-11-04/batch.py docs/prestazioni/2026-11-04/prepare_sample.py docs/prestazioni/2026-11-04/batch-initial.json
fatal: Unable to create 'C:/Users/Grasso/dev/meridiana/.git/worktrees/meridiana-wt-r10-velocita/index.lock': Permission denied
```

Il commit richiesto non e' registrato: non e' possibile creare l'indice del worktree con questi permessi.
Il ramo resta `r10-velocita`. Non sono stati fatti push, tag o release.
Anche il tentativo finale, con staging esplicito di rapporto, dati e tre documenti aggiornati, riceve lo stesso
rifiuto. Comando ed esito sono conservati in `git-stage-attempt.json`.

## Verifica di Claude, 04/11/2026

Rimisurato con lo stesso `probe.py`. I valori di questo rapporto tornano nello stato veloce: bordo destro in Modellazione 2006-2282 ms contro 2061,
in Consumi 2216-2745 contro 2739, finestra in Consumi 883-1037 contro 868. Il rapporto non vede però lo stato lento, in cui gli stessi gesti
impiegano circa il doppio: le passate successive alla prima, a poca distanza. Vedi `docs/prestazioni/README.md`.

Delle proposte sono state provate la 2 e la 3, con guadagno misurato, e sono nel programma. La 1, fatta come immagine ferma del grafico, non ha dato
guadagno misurabile e non è stata tenuta. Le altre restano da fare. I dati grezzi delle 105 prove sono nel ramo locale `r10-velocita-dati`, non pubblicato.
