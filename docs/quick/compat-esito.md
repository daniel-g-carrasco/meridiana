# r12-compat: esito delle prove di compatibilità

04/11/2026. R389 e R392. Ramo `r12-compat`.

Il banco di compatibilità collega il programma Widgets reale, il prototipo
Quick e le richieste di Daniel. Non attribuisce al nuovo programma funzioni
che ancora mancano. Nessuna pagina Quick, nessun file di `src/meridiana/ui/`
e nessun algoritmo del nucleo sono stati modificati.

## Materiale consegnato

| Parte | Risultato |
|---|---|
| Riferimento Widgets | `tools/quick_rif.py`, fixture Rho congelata, JSON gzip canonici e PNG nativi |
| Confronto geometrico | `geometry.py`, mappa esplicita, massimo 1 px logico, font e colori esatti |
| Confronto fotografico | `tools/quick_rif_compare.py`, HTML autonomo con due foto e differenza RGB |
| Registro di parità | 752 elementi in `parita.json`, controllo contro sorgenti e QActions reali |
| Richieste | 400 righe in `richieste.csv`, senza perdere le occorrenze duplicate |
| Prove Widgets | 1.196 metodi in `prove.csv`, contratto, assert e portabilità proposta |
| Differenziale | 19 scenari, comandi reali e osservazioni dopo ogni passo |
| Formati | Tutte le 57 fixture classificate, caricamento nel vero QML e salvataggi mancanti espliciti |
| Finestre vere | Fotogrammi, geometria, regioni scomparse, popup inattesi e profiler Python |
| CI | Un processo per sottogruppo Quick, più prove Windows Direct3D 11 e artefatti |

La guida per gli altri rami è `docs/quick/compat/README.md`. Il contratto nativo
e le limitazioni delle catture sono in `docs/quick/compat/prove-native.md`.

## Riferimenti nativi

La matrice prevista comprende 24 combinazioni: vuoto e Rho, chiaro e scuro,
scala 1 e 2, misure logiche 1366×900, 1600×960 e 1920×1080. Ogni combinazione
ha 35 stati: sei fasi, selezione edificio, quattro stati Impianto, sette pagine
File, sette pagine Impostazioni, nove menu aperti e Meridio.

Le acquisizioni usano la vera `MainWindow`, piattaforma Windows e Direct3D 11,
sul desktop isolato. Non sono ricostruzioni della UI. Impostazioni, cache e
salvataggi sono propri del banco; rete e voce sono spente. L'animazione del
personaggio è ferma per rendere stabile il riferimento statico. I menu aperti
sono composti sopra la cattura del contenuto della finestra.

La fixture Rho conserva i byte del progetto autorizzato, con hash verificato:
quattro edifici, due sottocampi, 778 moduli posati, sette inverter e 57 stringhe.
Il calcolo usa anno tipico e orizzonte PVGIS 5.3 registrati, mantenendo ombre e
rete elettrica. [V] La diagnosi separata del calcolo originale ha prodotto
425.352,850629 kWh in 8.760 ore: circa 215 s, dei quali 194 nella rete elettrica.
Il limite iniziale di 240 s non bastava sotto carico; il banco attende fino a
1.200 s e riusa il risultato nelle sei combinazioni di tema e misura.

`popolati-v1` è distinto dall'originale: aggiunge 400.000 kWh/anno di consumi,
450.000 euro di investimento e accumulo da 200 kWh, 100 kW, rendimento 90%.
Le modifiche della fixture sono registrate nel manifest. Serve a mostrare
grafici Consumi, Economia e Accumulo pieni, anche se l'originale non contiene
consumi e investimento.

Al 200% alcune finestre eccedono il desktop disponibile. La misura è fissata
e verificata prima della cattura, senza ridimensionare le foto: l'immagine
contiene l'intera superficie renderizzata, anche fuori dal monitor virtuale.
Non è una misura della presentazione fisica sul monitor.

I JSON sono in `docs/quick/compat/riferimento/`; i PNG corrispondenti, con hash
nei JSON, sono in `build/riferimento/`. Le catture precedenti non vengono
sovrascritte. `--resume` controlla stati e hash prima di saltare un caso completo.

## Cosa il confronto ha trovato

[V] `docs/quick/confronto/prototipo-v2-model-empty.html` confronta fotografie
native a 1600×960, scala 1. Nei quattro elementi mappati ci sono 19 differenze
di geometria, margini, carattere o testo. Differiscono 1.377.362 pixel su
1.536.000. Il numero di pixel è descrittivo: non è una soglia di accettazione.
Il prototipo attuale non ripete ancora la struttura del Widgets.

La revisione ha trovato e corretto due difetti del banco: `QFont` poteva
restituire punti non risolti per un font specificato in pixel; snapshot
incompleti potevano confrontare due valori mancanti come uguali. Ora entrambi
i font usano `QFontInfo` e i dati malformati sono rifiutati. Le regressioni
includono NaN, infinito, font incompleti e rettangoli non validi. Il confronto
v1 resta come documento storico; per il risultato attuale usare v2.

[V] Le vere operazioni di rinomina, altezza, annulla e ripeti conservano il
progetto dopo ogni passo. Restano differenze nei testi di annulla e nel nome
del nuovo edificio, marcate `expectedFailure` e controllate anche da una prova
che ne accerta la causa precisa. Un errore casuale non soddisfa quella prova.

[V] Sulla fixture differenziale collegata, entrambi i veri worker calcolano
8.760 ore con produzione uguale ora per ora: 50.583,392864 kWh, accumulo da
20 kWh e risultati economici presenti. Il confronto completo resta diverso:
persistenza del meteo nel progetto, Verifiche e messaggi non coincidono.
Non basta l'uguaglianza dei kWh per dichiarare parità.

I percorsi per falda, sottocampo, posa, esclusione, fila, sposta, ruota,
varianti, stringhe automatiche e manuali, inverter, accumulo, consumi,
economia, relazione e salvataggio sono censiti. Un comando Quick assente
produce `missing` prima di iniziare lo scenario. Nessuna modifica diretta al
modello viene usata per fingere quel comando.

## Formati e dati

[V] 26 progetti congelati validi si aprono nella vera finestra Quick con
contenuto canonico invariato rispetto al caricamento condiviso. Tre progetti
malformati o futuri vengono rifiutati. Le 28 fixture di configurazione restano
esplicitamente mancanti nel frontend Quick. È provato separatamente il formato
corrente di `config.json`, versione 26, senza migrazioni di ritorno.

[V] Un archivio `.mer` con risorse e allegati conserva i dati in apertura.
Le fixture originali restano intatte. **Save Quick non esiste ancora**:
il ciclo Quick apre, salva, Widgets riapre è predisposto ma non può essere
certificato. Il risultato è `missing: Quick:save`, non un falso successo del
solo `Project.save`. Anche la UI delle impostazioni e i dati della relazione
Quick attendono i comandi reali degli altri rami.

## Registri e avanzamento

[V] Sono censiti 92 comandi, 92 scorciatoie associate, 53 comandi delle fasi,
108 gestori locali di tasti, 54 preferenze, 35 pagine, 96 sezioni, 124 voci di
menu, 19 dialoghi, 66 chiamate a dialoghi standard, sette scorciatoie locali e
sei fasi. Il controllo rileva elementi nuovi o scomparsi e rifiuta `fatto`
senza prova eseguita, hash e confronto visivo rivisto.

[V] Le 400 righe delle richieste contengono 398 numeri R distinti: R30 e R31
compaiono due volte. Le occorrenze sono conservate. Non sono inventate R399 o
R400. 184 destinazioni sono state rilette e affinate; le altre sono inferenze
esplicitamente dichiarate. Il censimento delle 1.196 prove conserva nome,
contratto e assert; la proposta di portabilità richiede ancora revisione
durante il trasferimento del relativo controllo.

Il registro parte da 746 elementi `da fare` e sei `differenza voluta`, secondo
R390, R391 e R396. **La parità certificata è 0% in ogni fase**: le verifiche
parziali del prototipo non bastano per promuovere funzioni complete con la
relativa prova visiva. Questo è l'avanzamento del nuovo frontend, non quello
del lavoro di costruzione del banco.

## Fotogrammi e gesti

[V] Le prove native verificano presenza dei contenuti GPU, stabilità delle
regioni, pan reale del prototipo senza chiamate Python durante il gesto e
passaggio Modellazione, Produzione, Modellazione. Prove di guasto introducono
fotogrammi vuoti, regioni scomparse, salti, finestre aggiuntive e chiamate Python.
Il filtro intercetta anche una finestra mostrata e nascosta fra due catture.

La lettura è richiesta da `frameSwapped`, ma `grabWindow()` sincronizza un
ulteriore rendering. Non è la copia esatta di ogni buffer presentato. Il
readback altera i tempi: non certifica i 30 ms né la fluidità sul monitor.
R392 resta aperta fino alla prova della vera pagina File Quick, oggi assente.

## Verifiche finali

Gli esiti conclusivi, il numero delle catture e il log della suite vengono
riportati qui dopo l'ultima esecuzione. I gruppi Widgets `widget` e `finestra`
non sono stati rilanciati: il loro codice non cambia e `CONTESTO.md` prescrive
in questo caso il gruppo `formati` e il lint. Nessun push, tag o rilascio.
