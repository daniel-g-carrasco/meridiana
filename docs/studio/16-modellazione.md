# Studio 16: modellazione

23/10/2026. Daniel ha provato il programma e ha chiesto sette cose: i tetti a falde sulle piante non rettangolari, lo sposta e ruota nel 3D come in DIALux evo, la posa dei moduli a mano con le file e l'esplosione, un editor delle stringhe e la scelta dell'inverter, filtri migliori nel catalogo dei moduli, i segnaposti mentre si aspetta, un mirino sul perno della vista 3D. Questo studio dà per ogni tema le alternative con le prove, i voti e una raccomandazione; le scelte sono sue, e i compiti per le sessioni cloud sono in bozza in `docs/compiti/` (sezione «Il piano»).

**Legenda**
- [V] letto nel codice di Meridiana, nella documentazione ufficiale del programma citato (con l'URL e la data in fondo) o verificato con una prova in `16-prove/`;
- [V, prova] provato in questa sessione, offscreen, su Linux; i risultati sono accanto agli script;
- [I] dedotto;
- [D] decisione proposta, da confermare.
- Voti da 1 a 5: efficacia (5 = risolve bene), rischio (5 = poco rischio), costo (5 = poca fatica). La fatica è in giorni di lavoro di una sessione, test compresi.

**Come è stato fatto.** Per ogni tema: le parole di Daniel; che cosa fa oggi Meridiana, letto nel codice (`roofs.py`, `model.py`, `layout.py`, `energy/stringing.py`, `catalog/`, `ui/`); come lo fanno DIALux evo, PVsyst, Aurora, OpenSolar, HelioScope, PV\*SOL, SketchUp con Skelion, Revit, AutoCAD, FreeCAD, Blender, Sunny Design, SolarEdge Designer, PVcase e Solarius, dalla loro documentazione pubblica; tutte le famiglie di soluzioni con pro, contro, rischi, fatica e voti; una prova dove la scelta dipende da un fatto; la raccomandazione e ciò che resta a Daniel. Le pagine dietro login o CAPTCHA non sono state aggirate: i centri di assistenza su Zendesk (Aurora, HelioScope, OpenSolar, PVcase) rifiutano le pagine HTML ma espongono gli stessi articoli dalla loro API pubblica (`/api/v2/help_center/.../articles/<id>.json`), con la data di aggiornamento; le pagine non lette sono dette tema per tema. **Le norme non sono citate a memoria**: la UNI 9460 non c'è nell'archivio, e per le pendenze si usano le schede pubbliche dei produttori.

**Librerie.** Nessuna è stata aggiunta al programma. Quelle provate (polyskel, bpypolyskel, CGAL, mathutils) stanno in un ambiente a parte e sono proposte, non decise: ogni libreria nuova è una decisione di Daniel.

## In breve

Le raccomandazioni, due righe per tema; il resto nelle sezioni.

| Tema | Raccomandazione | Fatica |
|---|---|---|
| A. Tetti a falde | Lo scheletro dritto scritto in casa, in Python esatto, verificato contro le 306 piante di riferimento calcolate con CGAL (`16-prove/scheletro-riferimento.json`); le testate come lati «senza falda» alla Revit; il colmo si quota e dà la pendenza; i modelli di edificio (L, T, U, trapezio) come aiuto al disegno. Formato file 6 con migrazione. | 6-9 giorni in due passi |
| B. Sposta e ruota | Strumenti Sposta (M) e Ruota con punto base e secondo punto, valore digitato e copia come AutoCAD, in pianta e nel 3D con lo stesso nucleo; nel 3D il gizmo a frecce e anelli di DIALux, disegnato in QML e scelto in Python sullo schermo; agganci della pianta riusati. | 7-10 giorni in due passi |
| C. Posa manuale | Tenere la posa automatica come generatore e aggiungere le correzioni per riga (file spostate, tolte, aggiunte) e per modulo, salvate come «correzioni» sul risultato; «esplodi» rende i moduli oggetti espliciti con la posa automatica spenta, mai distrutta in silenzio (l'avvertimento di PVsyst). | 8-12 giorni in tre passi |
| D. Inverter e stringhe | Una scheda «Impianto» tra Modello e Producibilità, con gli inverter (più di uno, con gli MPPT) e l'editor delle stringhe: automatico, poi clic e trascinamento sui moduli, colori per stringa e verifiche CEI 64-8/7 in diretta. Il gruppo «Inverter» resta anche in Producibilità come collegamento. | 8-10 giorni in due passi |
| E. Filtri del catalogo | Un campo «famiglia della cella» ricavato dal testo al caricamento (TOPCon, HJT, back contact, PERC, mono, poli, film sottile, non detto) e un campo «bifacciale», con i filtri a caselle sopra la tabella, il conteggio e l'ordinamento per colonna; la bifaccialità resta per scheda. | 2-3 giorni |
| F. Attese visibili | Tre indicatori leggeri già misurati sotto 1 ms: segno «da aggiornare» sui valori vecchi (come Excel e FreeCAD), scheletro grigio per la 3D e per le pagine alla prima apertura, arco nella zona che aspetta dopo 300 ms, barra di avanzamento solo per PVGIS e PDF, con Annulla. | 3-4 giorni |
| G. Perno della 3D | Mirino a tre anelli (la «palla con le cinture» di Autodesk) visibile durante l'orbita e, a scelta, al passaggio con Maiusc; un «fissa il perno qui» con il clic centrale; mai sempre visibile. | 1-2 giorni |

Le domande per Daniel sono in fondo a ogni tema e raccolte nella sezione «Il piano».

## A. Tetti a falde su piante qualsiasi

### A.1 Cosa chiede Daniel

«Quando l'edificio non ha una geometria rettangolare, e c'è un tetto a falde, il tutto si sballa completamente.»

«Sarebbe buona la possibilità di poter disegnare delle geometrie particolari di tetti a falda disegnandone il colmo e dandogli altezza (con default di inclinazione come quello che di solito si usa in costruzione). Oppure (o in aggiunta) mettere a disposizione dei template di edificio già realizzati, tipo edifici ad L, quadrati, con forma trapezoidale, ecc.»

### A.2 Che cosa fa oggi Meridiana [V]

- `roofs.py`: cinque tipi. Piano; a una falda, verso il lato di gronda scelto; a due falde e a padiglione, costruiti **sul rettangolo ruotato minimo** che contiene la pianta (`_rect`), con il colmo lungo il lato lungo o parallelo a un lato scelto (formato 5); falde libere, disegnate una per una con il loro lato di gronda e la pendenza (15° predefiniti in `window.py`).
- Una falda (`Pitch`) è un anello in pianta più un piano: pendenza, azimut CEI e quota in un punto. Tutto il resto legge solo questo: la posa (`SubField.pitch` è l'indice della falda), la pianta (contorni e freccia di pendenza), il 3D (`mesh.building_triangles`: i muri salgono fino al tetto lungo i lati), le ombre (`system.obstacles_of`: le falde degli altri edifici e, solo per i tetti «free», le altre falde dello stesso edificio), la relazione.
- **Su una L** [V, prova]: con due falde a 20° su una L di 20 × 18 m con braccio di 8 m, le due falde coprono il rettangolo 20 × 18 (360 m²) contro 240 m² di pianta: 120 m² di tetto fuori dalla pianta, nessuna compluvio, e nell'angolo interno il tetto sta a 8,91 m con la gronda a 6 m. Il padiglione fa lo stesso. Il programma avverte («a footprint that is not a rectangle is told», `test_roofs.py`), ma il risultato è quello che Daniel ha visto.
- Il tipo «free» funziona per qualsiasi pianta, ma tocca al progettista disegnare ogni falda, con colmi e compluvi a occhio.

### A.3 Come fanno i programmi di riferimento [V]

| Programma | Come definisce il tetto | Piante a L, T, U |
|---|---|---|
| Revit | «Roof by footprint»: un anello chiuso; per ogni linea «Defines Roof Slope» sì o no con la sua pendenza; «One sloped line forms a flat roof», «Two opposite sloped lines form a gable», «Three or four sloped lines form a hip roof». Frecce di pendenza per i casi speciali; tetto per estrusione da un profilo. L'algoritmo dei colmi non è documentato; i piani che salgono da ogni lato e si intersecano sono lo scheletro dritto [I]. | Sì, da sole: colmi, displuvi e compluvi derivati |
| Aurora SmartRoof | Si clicca sugli angoli, residenziale parte «Pitched», commerciale «Flat»; cinque tipi di spigolo (eave, hip, rake, ridge, valley); la pendenza per faccia in «Edge & Face properties»; «Edit roof mode» per spiombare una faccia, cambiare la quota della gronda, abbaini contati per numero di falde, «flat fold»; l'AI «infers the inner faces». | Sì, le facce interne sono dedotte |
| OpenSolar | Quick Roof: spilli sugli angoli, «Complete the roof shape to generate the structure», maniglie a freccia per quote e angoli, «Edit Slope Individually»; spigoli a colori (gronda verde, colmo giallo, compluvio e rake blu); i moduli si orientano da soli verso la gronda. | Sì |
| DIALux evo | Nove tipi (a farfalla, due falde, piano, mansarda olandese, mezzo padiglione, padiglione, mansarda, piramide, una falda); «The automatic placement function adjusts the roof to the floor contour»; si può anche disegnare ogni tipo a mano, «Any slopes are then calculated automatically». | Sì per i tipi; come adatti una L non è detto |
| PV\*SOL premium | Oggetti rettangolari estrusi dalla pianta, con la linea del colmo disegnata per il padiglione; per le piante qualsiasi una sola falda verso il lato scelto («the longest edge is preset»); per la L lo staff dice: «draw several polygons and extrude the buildings one after the other», «The polygons must be rectangular». | No: blocchi rettangolari accostati |
| PVsyst | Oggetti elementari «House + 2-sided roof», «2-sided roof+gables», «4-sided roof», quotati o trascinati nelle viste ortogonali; «More complex objects are obtained by assembling elementary objects». | No: si compone a mano |
| HelioScope | Solo piani: ogni «field segment» ha pendenza e azimut, con «Independent Tilt» e «Set to Top Edge / Bottom Edge» per l'azimut. | Non modella il tetto |
| FreeCAD BIM Roof | Da un filo chiuso, per ogni lato angolo, run, sporto, spessore; angolo 90° per la testata; «still in development, and might fail with very complex shapes»; nel sorgente «Arch Roof: Case not implemented». È un'estrusione per profili, non uno scheletro. | In parte |
| SketchUp, Skelion | Nessuno strumento tetto; Skelion posa i pannelli su una faccia esistente («Insert solar panels in any roof», anche curvi). | Non modella il tetto |
| AutoCAD Architecture | ROOFADD con Plate Height, Rise, Slope e sporto; l'AutoCAD puro non ha tetti. | Sì, nel toolset |

**Due famiglie** [I]: chi risolve la pianta (Revit, Aurora, OpenSolar, DIALux evo) prende il contorno più un attributo per lato e ricava colmi, displuvi e compluvi da solo; chi compone primitive (PVsyst, PV\*SOL, FreeCAD) chiede di spezzare la L in rettangoli. Il vocabolario per lato è lo stesso ovunque: gronda, colmo, displuvio, compluvio, testata (rake).

### A.4 Gli algoritmi e le librerie [V]

- **Lo scheletro dritto** (Aichholzer, Alberts, Aurenhammer e Gärtner, 1995) è la geometria di tutti i tetti a pendenza uguale: ogni lato avanza verso l'interno alla stessa velocità e le tracce dei vertici sono colmi, displuvi e compluvi. L'articolo del 1995 lo presenta proprio come «a systematic way to build a polygonal roof over a ground-level wall layout». Con un peso per lato (velocità diversa) si hanno pendenze diverse per falda; con peso infinito su un lato, quel lato non genera una falda: è la testata.
- **Felkel e Obdržálek (1998)** è l'algoritmo delle implementazioni in Python; è noto per sbagliare su alcune piante («shown to be incorrect for certain input polygons», README di polyskel).
- Implementazioni:

| Libreria | Licenza | Dove | Stato | Pesi | Fori |
|---|---|---|---|---|---|
| CGAL Straight_skeleton_2 | GPL-3+ (pacchetto GPL; doppia licenza con quella commerciale) | C++, apt `libcgal-dev` 5.6; Python solo via scikit-geometry (conda, ultimo commit 04/12/2023, non su PyPI) o `cgal` su PyPI (nessuna ruota per il nostro Python [V, prova]) | riferimento del settore; nella 6.x pesi ed estrusione del tetto (`extrude_skeleton`) | 6.x sì | sì |
| polyskel (Botffy) | LGPL-3 | GitHub, non su PyPI, ultimo commit 12/10/2020, dipende da euclid3 | «a bit crap» per sua stessa ammissione | no | sì |
| shapely-polyskel | LGPL-3 | PyPI 0.1.2 del 05/01/2025, Python ≥ 3.10 | stesso algoritmo, stesse riserve | no | sì |
| bpypolyskel (prochitecture) | GPL-3 | GitHub, ultimo commit 13/03/2026, dipende da mathutils | porting con riparazioni; «tested against all 320.000 hipped roofs in the OpenStreetMap database... 99.99%»; «does not provide a straight skeleton in a mathematical sense» | no | sì |
| ladybug-geometry-polyskel | AGPL-3 | PyPI | da evitare per la licenza | no | sì |
| shapely 2.2 / GEOS 3.14 | BSD | installato | nessuno scheletro né asse mediano nelle note di rilascio di GEOS 3.13, 3.14 e 3.15 | | |
| npm straight-skeleton 3.0 | MIT | JavaScript (CGAL in wasm) | non serve a Python | no | sì |

### A.5 La prova [V, prova]

`16-prove/scheletro.py`, con `scheletro_cgal.cpp` come riferimento esatto e `scheletro-risultati.txt`:
- sei piante (rettangolo, L, T, U, trapezio, rettangolo con un lato corto storto), padiglione e due falde con le testate;
- il padiglione: facce dallo scheletro con shapely (`polygonize`), una faccia per lato di gronda, copertura del 100 % della pianta, nodi equidistanti dai lati (è la condizione del tetto a pendenze uguali);
- le due falde: i lati di testata spinti lontano lungo le gronde vicine prima dello scheletro, facce ritagliate sulla pianta, faccia della testata scartata. È l'effetto del peso infinito, senza scheletro pesato. Funziona anche sulle testate storte (trapezio);
- 300 piante rettilinee a caso (rettangolo con una a tre rientranze o sporgenze), stesse tre verifiche, con tre implementazioni.

| Implementazione | Le 12 prove (6 piante × 2 tetti) | 300 piante a caso: esatte, approssimate (facce fuse, nodi entro 5 cm), sbagliate o fallite | Tempo per pianta |
|---|---|---|---|
| CGAL 5.6 | 12 su 12 | 300, 0, 0 | 30 ms (compreso avviare il processo) |
| polyskel | 12 su 12 | 196, 23, 81 | 8-11 ms |
| bpypolyskel | 12 su 12 | 44, 243, 13 | 2-7 ms |

- polyskel sbaglia già su un rettangolo con una sporgenza di 5 m (un nodo a 6,8 m dal posto giusto): non si può usare così com'è.
- bpypolyskel fonde apposta le facce piccole (è fatto per i tetti di OpenStreetMap visti da lontano): per un programma che posa moduli su piani, una faccia fusa è una falda sbagliata.
- CGAL è esatto su tutte, ma vuole un'estensione compilata (28 s di compilazione qui, GMP e MPFR, ruote da costruire per Windows e Linux, Flatpak e PyInstaller da adattare) e nessuna ruota Python pronta per il nostro Python.
- Le 306 piante con le facce esatte di CGAL sono salvate in `scheletro-riferimento.json` (242 KB): sono il banco di prova di qualsiasi implementazione futura, senza CGAL tra le dipendenze.
- `scheletro.png` mostra i dodici tetti.

### A.6 Le famiglie di soluzioni

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A1. **Scheletro dritto scritto in casa**: Python puro, aritmetica esatta (`fractions`) sui pochi vertici di una pianta (4-20), eventi di lato e di divisione, testate per estensione dei lati (provata); verificato contro il riferimento CGAL | 5 | 3 | 3 | 4-6 giorni. Il rischio è l'algoritmo (i casi degeneri: eventi simultanei, vertici allineati); le 306 piante di riferimento lo contengono. Niente dipendenze |
| A2. CGAL come estensione C++ | 5 | 3 | 2 | esatto e con i pesi, ma una dipendenza compilata in un programma Python: build su Windows, Flatpak, PyInstaller; 3-5 giorni di impianto e manutenzione per sempre |
| A3. polyskel o shapely-polyskel copiati e riparati | 3 | 2 | 3 | 81 piante su 300 sbagliate: ripararlo è riscriverlo; la LGPL va bene |
| A4. bpypolyskel copiato (GPL-3, compatibile) | 3 | 3 | 4 | funziona «per il 99,99 %» ma approssima; il codice dipende da mathutils (un pacchetto C) e dai suoi raggruppamenti di nodi; si potrebbe spegnere la fusione, con lo stesso lavoro di A1 |
| A5. Lato per lato come Revit: tipo di lato (gronda, testata) e pendenza propria | 5 | 3 | 3 | è A1 più i pesi; con pendenze uguali e testate si ha dalla A1 senza costo; le pendenze diverse per falda sono lo scheletro pesato (fase 2, 2-3 giorni in più) |
| A6. Colmo disegnato con la sua altezza | 4 | 3 | 4 | da solo definisce il tetto solo sui rettangoli (è quello che fa PV\*SOL); sulle altre piante serve comunque lo scheletro. Come **vincolo** sullo scheletro (si clicca il colmo calcolato, si scrive la sua quota, la pendenza viene da `slope_from_heights`) costa un giorno e dà a Daniel il gesto che ha chiesto |
| A7. Modelli di edificio (rettangolo, L, T, U, trapezio, cortile) con le quote | 3 | 5 | 4 | da soli non fanno il tetto: servono con A1. Come aiuto al disegno (pianta parametrica, poi lati modificabili con `sides.stretch`) 1-2 giorni. Il cortile è un foro: lo scheletro con i fori è un passo in più |
| A8. Composizione di blocchi rettangolari (PVsyst, PV\*SOL) | 2 | 4 | 4 | niente algoritmo nuovo, ma i tetti si attraversano senza compluvi: moduli e ombre sbagliati vicino agli incroci; è quello che Daniel ha già visto come «si sballa» |
| A9. Restare con le falde libere, migliorate (agganci ai colmi, pendenza dalla quota) | 2 | 5 | 4 | resta il ripiego per i tetti strani (mansarde, abbaini, quote di gronda diverse), non la via normale |

### A.7 Che cosa cambia nel programma [I]

- **`roofs.py`**: un nuovo modulo `skeleton.py` nel nucleo (lo scheletro, le facce, le testate); `gable` e `hip` lo usano per qualsiasi pianta; su un rettangolo il risultato coincide con quello di oggi (da provare nei test). Le falde escono una per lato di gronda, **nell'ordine dei lati**: l'indice della falda è stabile e leggibile («falda del lato 3»).
- **`model.py`**: formato 6. `Roof` prende `edges: list[str]` (per lato: «eave» o «gable»; più avanti «eave» con pendenza propria) e `ridge_height: float | None`. Migrazione 5 → 6: per i tetti a due falde di oggi, i due lati del rettangolo perpendicolari a `ridge_along` (o al lato lungo) diventano testate; per i padiglioni tutti «eave». Per le piante non rettangolari il tetto cambia davvero: il file va aperto con un avviso («il tetto di Edificio 2 ora segue la pianta: controlla le falde e i sottocampi») e i `SubField.pitch` vanno rimappati sulla falda che contiene il baricentro del sottocampo.
- **Posa**: niente da cambiare in `layout.py`; i sottocampi sulle falde cambiate si segnano «da posare di nuovo» con la chiave di posa (già fatto in fase 2).
- **Ombre**: `obstacles_of` oggi considera le altre falde dello stesso edificio solo per i tetti «free»; con lo scheletro le ombre tra falde dello stesso tetto (un braccio della L sull'altro) servono per tutti i tipi: due righe.
- **3D**: `mesh.building_triangles` già alza i muri fino al tetto lungo i lati; con le facce esatte i muri delle testate diventano i timpani da soli (la faccia della testata non c'è e il muro sale fino al colmo). I compluvi vengono dalle facce.
- **Pianta**: le falde si disegnano come oggi; una freccia di pendenza per faccia; il colmo evidenziato al passaggio per quotarlo (A6).
- **Proprietà**: il gruppo «Tetto» prende la lista dei lati con il tipo (gronda o testata) e il pulsante «Scegli sulla pianta» che c'è già per gronda e colmo; «Quota del colmo» accanto alla pendenza.
- **Modelli (A7)**: nel menu Disegna, «Edificio da modello…»: rettangolo, L, T, U, trapezio, cortile, con le quote in una finestra o, meglio, con i lati nel gruppo «Lati» che esiste già.

### A.8 La pendenza predefinita [V]

Nessun programma di riferimento documenta un valore numerico predefinito (Aurora dice solo «Pitched» per il residenziale). Dalle schede pubbliche dei produttori:
- tegola marsigliese Pica/Terreal: «pendenza minima > al 35 %» (19,3°); SanMarco Santenay «> al 35 % (fino al 19 % in situazione protetta)»; tegola portoghese «> al 30 %» (16,7°);
- coppo Wierer Coppo Titan «fino a 5,7° (10 %)» (portale infobuild, non la scheda);
- pannelli sandwich Isopan Isocop «minimum slope of 7 %» (4°), Isodomus a effetto coppo «11 %» (6,3°); al convegno ANIT 2023 Isopan: coperture piane 1-2 %, inclinate «solitamente > 7 %».
- Le guide tecniche (edilizia.com, 2026) citano la UNI 9460:2023 come norma di progetto senza riportarne i numeri: **l'archivio sul PC non ha la UNI 9460**, quindi i valori sopra vengono dalle schede e vanno detti come tali nel programma.
- **Aggiunto il 23/10/2026 dalla sessione locale [V]:** il *Manuale coperture in laterizio 2025* dell'ANDIL, curato dal coordinatore del gruppo UNI/CT 033/GL 15, che cita la UNI 9460:2023 (pagg. 4, 34 e 37). È archiviato in `reference\publications\andil` sul PC di Daniel. A pag. 7:
  - «per climi mediamente piovosi e con modeste precipitazioni nevose, si adottano comunemente pendenze intorno al 30-35%»;
  - pendenza minima 30%, marsigliesi 35%, sotto il 30% «sconsigliata», salvo diverse indicazioni dei produttori;
  - con molta neve si arriva al 150%.

  La proposta del 35% resta dentro questi valori, e la fonte da citare nel programma è il manuale ANDIL.

Proposta [D]: predefinito **35 % (19,3°)** per i tetti a falde, con la nota «pendenza minima delle tegole marsigliesi secondo le schede dei produttori; cambiarla se la copertura è in lamiera (7 %) o in coppi»; resta modificabile in gradi e in percento come oggi.

### A.9 Raccomandazione

**A1 con A5 (solo testate) e A6 come vincolo, poi A7**, in due compiti:
1. `skeleton.py` nel nucleo con i test sulle 306 piante di riferimento; `gable` e `hip` su qualsiasi pianta; formato 6 con la migrazione e l'avviso; lati «gronda o testata» nelle proprietà con la scelta sulla pianta; quota del colmo; ombre tra le falde dello stesso tetto; 4-6 giorni.
2. I modelli di edificio e il cortile (fori nello scheletro); le pendenze per lato (scheletro pesato) se Daniel le vuole; 2-3 giorni.

CGAL resta l'oracolo delle prove, non una dipendenza. Le falde libere restano per i tetti che lo scheletro non descrive.

**Da decidere a Daniel**
- La pendenza predefinita: 35 % (tegole) o un'altra, e se chiedere il tipo di copertura (tegole, coppi, lamiera) al posto di un numero.
- Se le pendenze diverse per falda (Revit) servono subito o dopo.
- Se un tetto a due falde su una L deve avere le testate sui due bracci (il predefinito proposto) o un colmo solo con un braccio a padiglione: con i lati «gronda o testata» si ottengono entrambi, serve solo il predefinito.

## B. Spostare e ruotare, nel 3D e in pianta

### B.1 Cosa chiede Daniel

«La vista 3d non permette di spostare oggetti. Sarebbe buono che fosse possibile farlo alla stregua di Dialux EVO: si mette a disposizione strumento sposta e ruota, e quando si sposta escono fuori i vettori x / y / z che a seconda di dove si preme permettono di spostare. Da ragionarsi modi per farlo in modo preciso con suggerimenti / snapping / step o dichiarare uno spostamento di un numero preciso come in CAD se si sta digitando. Se si preme sulla rotazione stessa cosa più o meno, compaiono le maniglie circolari.»

### B.2 Che cosa fa oggi Meridiana [V]

- **In pianta** non c'è uno strumento Sposta né Ruota. Si può: trascinare un vertice del contorno selezionato (`plan.py`, `dragging`, con gli agganci dello `Snapper` e Ctrl per il trascinamento libero); cambiare la lunghezza di un lato con il doppio clic o dal gruppo «Lati» (`sides.stretch`: ciò che sta oltre il lato si muove con lui); duplicare un oggetto con uno scarto fisso di 1 m est e 1 m sud (`Project.duplicate`). Nessun oggetto si sposta intero, nessuno ruota.
- **Nel 3D** il clic seleziona (il modulo per indice, il resto dal punto della pianta sotto il cursore, `_point_picked_3d`); il resto è navigazione (`navigation.py`, `camera.py`). La scena è una sola geometria per gli edifici e una tabella di istanze per i moduli: non ci sono «oggetti» da trascinare, ma il backend sa già che cosa è stato premuto (`_press`: punto colpito, nome, indice) e il centro della selezione (`_centre_3d`, usato come perno).
- **Annulla**: ogni modifica passa da `edit()` con un'istantanea; le modifiche numeriche ravvicinate si fondono in un passo (`Snapshot.mergeWith`, 2 s). Un trascinamento può fondere i suoi passi con la stessa chiave.
- **Che cosa dipende da una posizione**: i sottocampi e le esclusioni portano l'`id` dell'edificio e gli anelli in metri assoluti; spostare un edificio vuol dire spostare anche loro (oggi `duplicate` copia solo l'oggetto). L'orientamento delle file è in `params["azimuth"]` (None = automatico): ruotando un sottocampo con azimut esplicito va ruotato anche quello. Il lato di gronda e il lato del colmo sono indici dei lati: una rotazione non li tocca.

### B.3 Come fanno i programmi di riferimento [V]

| Programma | Sposta | Ruota | Precisione |
|---|---|---|---|
| DIALux evo | Manipolatore di traslazione (Ctrl+Maiusc+T), «Tab» attiva il manipolatore successivo e poi «Activate the next available edit field of the current manipulator»: il valore si scrive nel campo del manipolatore; «drag & drop, simply pull the object»; copia con Ctrl+C e «Insert a copied CAD object at the current mouse position Ctrl+M»; strumento «Copy and arrange» (lungo una linea, in cerchio, allinea) | Manipolatore di rotazione (Ctrl+Maiusc+R), stessi campi | Dal registro delle modifiche evo 5.2: «Colour code for movement and rotation with input fields». Le frecce x/y/z non sono descritte nella documentazione pubblica oltre la scheda dei tasti: il comportamento che Daniel descrive è quello del programma, non di un testo |
| AutoCAD | MOVE: punto base e secondo punto («a vector that indicates how far, and in what direction»), oppure spostamento scritto; con l'input dinamico «relative coordinates are the default» | ROTATE: punto base, angolo scritto o secondo punto, «Copy», «Reference» (da un angolo a uno assoluto) | Grip: «The default grip mode is STRETCH», Invio o Spazio ciclano Move, Rotate, Scale, Mirror; «The grip you select is the base point»; Ctrl cicla il menu del grip; snap polare «90, 60, 45, 30, 22.5, 18, 15, 10, and 5 degrees»; F8 orto o Maiusc tenuto; F12 input dinamico, Tab passa tra i campi |
| Revit | Move: «Constrain» (solo perpendicolare o collineare), «Disjoin», punto di partenza, poi clic o «type a value for the distance to move the element, and press Enter»; trascinamento diretto, Maiusc toglie il vincolo | Rotate: centro trascinabile, Spazio o «Place Center of Rotation», «The control snaps to points and lines of interest», Copy, angolo scritto | Le quote temporanee si scrivono e «The element moves to satisfy the new dimension requirement»; frecce della tastiera: «nudges the element a specific distance based on your current zoom factor» |
| SketchUp | Move (M): il valore si scrive nel Measurements box senza cliccarci, «hold down the Shift key when the move line turns the color of your desired axis», frecce per bloccare un asse (destra rossa, sinistra verde, su blu); Ctrl = copia, «7x» sette copie, «5/» quattro copie tra le due | Rotate (Q): il goniometro, «Click to set your angle's vertex», tacche ogni 15° («your cursor will snap to the tick marks»), precisione 0,1° | |
| FreeCAD | Draft Move: punto base, X/Y/Z scritti, Relative (R), Global (G), Copy (C), «Holding down Alt after picking the base point will also toggle copy mode»; Std TransformManip (1.0): «drag to translate the object along that axis», piani, sfere per ruotare, «Increments task panel», Cancel ripristina | Draft Rotate: centro, angolo base, rotazione; stesse opzioni | Snap di Draft (S) |
| Blender | G, poi X/Y/Z per vincolare (una pressione: orientamento corrente, due: globale, tre: libero), Maiusc+X piano; numeri scritti, Tab tra gli assi («G 1 and Tab 1 and Tab 1»); gizmo a frecce e quadratini | R, «R R» trackball; anelli del gizmo | Maiusc = un decimo, Ctrl = scatti («rotations of 5 degrees»), Maiusc+Ctrl = 0,1 e 1° |
| PVsyst 3D | «Move objects - Ctrl+B»: finestra di posizione più trascinamento lungo uno o due assi; frecce solo con modificatore: Ctrl 1 cm, Maiusc 10 cm, Ctrl+Maiusc 1 m | «Rotate objects - Ctrl+R», azimut nella finestra | Viste ortogonali consigliate |
| Aurora, HelioScope, OpenSolar, PV\*SOL | In pianta: trascinamento; Aurora «click and drag the arrows to the right» per ruotare, doppio clic = 90°, Ctrl toglie l'aggancio; HelioScope Ctrl+R o menu «Rotate»; OpenSolar l'azimut lo dà la fila trascinata; PV\*SOL posizione in metri dall'origine e orientamento 0-360° in campi | | Nessuno ha un gizmo 3D |
| Qt Design Studio (editor 3D di Qt) | Gizmo: «drag the component along the axis», «plane handle», «gray handle at the center»; W/E/R; Ctrl = snap, Maiusc = un decimo del passo | «drag the axis ring» | È codice GPL-3.0-only con eccezione Qt, in qt-creator (`MoveGizmo.qml`, `RotateGizmo.qml`, `mousearea3d.cpp`): leggibile per il metodo |

**La grammatica comune** [I]: punto base, poi secondo punto o valore scritto; Copia come interruttore dentro il comando; vincolo a un asse con un tasto tenuto o una lettera; scatti di angolo e passi di distanza con Ctrl o Maiusc; nel 3D frecce colorate (x rossa, y verde, z blu), anelli per ruotare, maniglie della stessa grandezza sullo schermo.

### B.4 La prova in Qt Quick 3D [V, prova]

`16-prove/gizmo.py` e `gizmo-risultati.txt`, nella configurazione di Meridiana (QQuickWidget, camera di `camera.py` legata in QML):
- la proiezione di QML (`mapFrom3DScene`) coincide con `camera.Camera.project` al pixel (scarto 0,000 px): il nucleo Python può ragionare sui pixel senza chiedere nulla a QML;
- le maniglie restano della stessa grandezza sullo schermo legando la scala del nodo alla distanza della camera (115 px a distanza 1 e a distanza 3, chiesti 120 meno lo scorcio), come già fa l'indicatore del perno in `Scene.qml` e come fa Qt Design Studio («measure up a distance on the view (100px)»);
- il trascinamento vincolato a un asse, dal pixel al punto dell'asse più vicino al raggio della camera (due rette sghembe): errore 6 × 10⁻⁶ m su spostamenti di 0,5, 2,5 e 3 m; la rotazione sull'anello, dal pixel al punto sul piano dell'anello: errore 10⁻⁴ gradi;
- la scelta della maniglia in Python sullo schermo (proiezione e distanza in pixel, come `plan._side_near`): x, y, z riconosciute a 6 px dalla freccia in 0,17 ms, niente in un angolo;
- **`View3D.pick` non si prova offscreen**: senza GPU Qt Quick 3D non disegna («The View3D item is not going to display anything») e il pick non vede nulla. Nel programma vero funziona (i moduli si selezionano così dal 21/10), ma il costo e l'affidabilità sulle maniglie sottili vanno visti sul PC. La scelta in Python non ha questo problema ed è testabile offscreen.

### B.5 Le famiglie di soluzioni

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| B1. **Comando Sposta/Ruota alla AutoCAD**, in pianta: punto base, secondo punto con gli agganci, oppure valore scritto (distanza; angolo; «@2;3» relativo), Copia con Ctrl tenuto, Invio ripete; stesso nucleo (`move.py`: trasla o ruota un oggetto e ciò che gli appartiene) | 5 | 5 | 4 | 2-3 giorni. Riusa `Snapper` (vertici, medi, perpendicolari, polare), le lunghezze digitate di `_apply_typed`, l'annulla a istantanee. Vale per edifici (con sottocampi ed esclusioni), sottocampi, esclusioni, falde libere |
| B2. **Gizmo nel 3D** alla DIALux: frecce x, y, z, quadratini dei piani, anelli; frecce scelte sullo schermo in Python; trascinamento vincolato con la matematica provata; valore scritto nel campo accanto (Tab tra i campi, come DIALux); stesso nucleo di B1 | 5 | 3 | 3 | 3-4 giorni. Disegno in QML (Model con `#Cylinder`, `#Cone`, un anello da un cilindro piatto o da una geometria propria); il rischio è la sensazione del trascinamento con il mouse vero, da provare sul PC |
| B3. Maniglie sugli spigoli (grip) alla AutoCAD, in pianta: un grip per vertice (già c'è), uno al centro per spostare, uno sul contorno per ruotare; Invio o Spazio cicla i modi | 4 | 4 | 4 | 1-2 giorni sopra B1; è la via più veloce con il mouse, senza menu |
| B4. Solo campi numerici nelle Proprietà (posizione del baricentro, rotazione), senza gesti | 2 | 5 | 5 | 0,5 giorni; utile comunque come «Posizione» nelle proprietà, ma non è quello che Daniel chiede |
| B5. `View3D.pick` sulle maniglie (modelli `pickable`) al posto della scelta sullo schermo | 4 | 3 | 4 | funziona solo con la GPU, non testabile in CI; il pick su un cilindro sottile è a tutta precisione (mesh statica), ma la tolleranza in pixel non si regola. Si può usare per il corpo dell'oggetto e tenere la scelta in Python per le maniglie |
| B6. Riusare i QML di Qt Design Studio (GPL-3.0-only con eccezione Qt) | 3 | 3 | 3 | compatibile con la GPL-3.0-or-later, ma legati a `MouseArea3D` (C++ del puppet) e ai suoi segnali: più da leggere che da copiare |
| B7. Trascinamento libero nel 3D sul piano del terreno o del tetto (senza frecce), con Maiusc per vincolare | 3 | 3 | 4 | semplice, ma è quello che DIALux evita: la profondità è ambigua in prospettiva. Può convivere con B2 come «maniglia centrale» |

### B.6 La precisione [I, dalle fonti di B.3]

- **Agganci**: in pianta gli stessi dello `Snapper` (vertice, medio, perpendicolare, parallelo, polare 15°), con il punto base che si aggancia e il secondo punto che si aggancia; nel 3D gli stessi punti proiettati (regola 11 dello studio 05a) più l'aggancio «sulla faccia».
- **Passi**: Ctrl tenuto durante il trascinamento = scatti di 10 cm e di 5° (Blender, PVsyst); Maiusc = passi fini (1 cm, 1°) come il «one tenth» di Qt Design Studio e Blender. Ctrl da solo nel disegno oggi sospende gli agganci: nello strumento Sposta il significato va scelto (vedi le domande).
- **Valori digitati**: una cifra apre il campo (come nel disegno), Tab passa da distanza ad angolo o da x a y a z, Invio applica; prefisso «@» non serve (relativo per impostazione predefinita, come l'input dinamico di AutoCAD); le coordinate assolute con «#» (AutoCAD) restano per chi le vuole.
- **Angoli a scatti**: 15° come SketchUp, 5° con Ctrl, 90° con Maiusc (stessa scelta delle frecce del cubo, studio 15).
- **Copia mentre si sposta**: Ctrl tenuto al rilascio (SketchUp, FreeCAD con Alt: Alt è vietato su Niri, studio 05a), oppure «C» durante il comando (FreeCAD); «3x» e «3/» per le serie (SketchUp), utili per le file di ostacoli.
- **Sposta con la tastiera**: frecce = 10 cm, Maiusc+frecce = 1 m, Ctrl+frecce = 1 cm (PVsyst), solo con lo strumento Sposta attivo (nel 3D le frecce oggi orbitano, in pianta fanno pan).

### B.7 Annulla, falde, ostacoli, sottocampi [I]

- Un trascinamento è un passo solo: l'istantanea si prende al rilascio; durante il gesto si muove un'anteprima (contorno in pianta, nodo nel 3D), non il progetto. I valori digitati nel campo si fondono con la chiave di `Snapshot` come oggi.
- Edificio: si spostano e ruotano con lui i sottocampi e le esclusioni che lo citano (`building == b.id`), le falde libere (anelli assoluti), il nord dell'azimut esplicito dei sottocampi; la chiave di posa cambia e i sottocampi si riposano da soli.
- Falde libere: si spostano solo dentro il loro edificio (altrimenti rifiuto con il motivo); le falde dello scheletro (tema A) non si spostano: seguono la pianta.
- Esclusioni: libere; se escono dall'edificio cambiano `building` (a terra o altro edificio, con `_host`).
- Sottocampi: si spostano solo sulla stessa falda o sul terreno; i moduli tolti a mano (`removed`, chiavi di riga e posto) restano validi solo se la posa è la stessa; con la posa a mano (tema C) i moduli espliciti si spostano con il sottocampo.
- Rotazione di un sottocampo: ruota l'anello attorno al baricentro e, se `azimuth` è esplicito, lo ruota dello stesso angolo; con «automatico» la posa si rifà.

### B.8 Raccomandazione

**B1 poi B2, con B3 come rifinitura**, in due compiti:
1. Il nucleo `move.py` (trasla, ruota, con ciò che appartiene all'oggetto, e i rifiuti motivati) e lo strumento in pianta: M = Sposta (Misura passa a D, come previsto in 12a), Ruota nello stesso strumento con «R» o dal grip; punto base e secondo punto con gli agganci, valori digitati, Ctrl = copia al rilascio, frecce con i passi; test del nucleo e della pianta offscreen. 3-4 giorni.
2. Il gizmo nel 3D: frecce, piani e anelli in QML, scelti in Python sullo schermo, trascinamento vincolato, campo numerico con Tab, stessi passi; la selezione del corpo con `View3D.pick` come oggi. 3-4 giorni, più la prova sul PC con il mouse vero.

**Da decidere a Daniel**
- Ctrl durante lo spostamento: copia (SketchUp) o scatti (Blender)? Proposta: Ctrl = copia al rilascio come SketchUp e AutoCAD (grip con Ctrl), gli scatti sempre attivi con l'aggancio (F3) e fini con Maiusc.
- Il tasto M a Sposta e Misura su D: come proposto in 12a.
- Se il gizmo deve comparire alla selezione (DIALux, Blender con il gizmo acceso) o solo con lo strumento attivo (Qt Design Studio con W). Proposta: solo con lo strumento, per non coprire i moduli piccoli.

## C. Posa manuale dei moduli, file ed esplosione

### C.1 Cosa chiede Daniel

«Il posizionamento dei pannelli fotovoltaici non è il massimo. Al momento si disegna l'area e poi l'app la popola in automatico. Non è possibile invece disegnare direttamente i pannelli con passo selezionato e tutto il resto?»

«Una volta disegnati i pannelli, avere la possibilità di selezionare e spostare le singole file, e di "esploderle" e poter selezionare e spostare i singoli pannelli.»

### C.2 Che cosa fa oggi Meridiana [V]

- Il sottocampo è un'area (`SubField.ring`) con i parametri di posa (`layout.Params`: montaggio, verticale o orizzontale, tavole, passo da sole, valore o GCR, margini, regole VVF, fuori dalle ombre). I moduli esistono solo nel risultato (`layout.compute` → `Result.modules`, una lista di `PlacedModule` con riga, posto, gruppo, angoli in pianta, centro, quota, inclinazione, azimut, livello) e si ricalcolano a ogni cambiamento della chiave di posa (`layout_key`).
- L'unica correzione a mano è **togliere un modulo**: Canc sul modulo selezionato aggiunge la sua chiave «riga:posto» a `SubField.removed`; la posa successiva lo salta. Le chiavi valgono finché la posa non cambia le righe (altro modulo, altro passo): allora le esclusioni a mano cadono su altri moduli o nel vuoto, senza avviso [I dal codice].
- Da questi moduli dipendono: le stringhe (`stringing.assign` percorre `Result.modules` a serpentina riga per riga), i gruppi e i corridoi dei Vigili del Fuoco (calcolati dentro `compute`, `groups` nel risultato), le ombre vicine e il loro effetto elettrico (`nearshade`, per stringa), il conteggio e la potenza nelle pagine dell'energia, il 3D (una tabella di istanze da `Result.modules`), la relazione, il confronto delle varianti (i sottocampi sono per variante).
- Non c'è una posa a mano: nessuna fila disegnata, nessun modulo spostato, nessuna matrice.

### C.3 Come fanno i programmi di riferimento [V]

| Programma | Area che si riempie da sola | File o matrici disegnate | Moduli uno per uno | Da automatico a manuale |
|---|---|---|---|---|
| Aurora | «Fill roof face»; «Solar Panels in Design Mode will snap in place based on default row and column spacing», Ctrl sospende; a terra: clic per l'inizio, «Move your cursor to the right until you have the desired number of columns then left-click again», poi le righe; «AutoDesigner» con «Max fit» | sì (a terra: colonne e righe; poi «rows, columns, and spacing» nella barra) | «Manually place»: «select the specific spot you want to place a single panel or click and drag your mouse to place multiple panels»; Canc; doppio clic ruota di 90°; selezione multipla «delete, duplicate, move, or rotate multiple objects at the same time»; in Sales Mode «Tap to turn a single module on or off» | i due metodi si alternano dal banner; «Users can easily switch between the two methods as needed» |
| OpenSolar | «Click and drag to draw panel arrays on the roof»; a terra la prima fila trascinata, poi «Fill Rectangle», Gap X/Y, «Offset Rows», «Modules Per Row» | sì: la fila è il gesto che dà anche l'azimut | il gruppo è l'unità: «Click on the panel group to access its settings»; una selezione di pannelli diventa «a new panel array... fully editable... repositioned» | «Ada Auto Design»: «can be modified like normal» |
| HelioScope | «The Field Segment will automatically fill up with modules»; Row/Module/Frame spacing; «Frames... up and wide»; allineamento «justified, centered, left, or right»; «Align Modules to Click» | no (ma «frames» come blocchi) | «Remove Module» con «Restore Modules» (una maschera, non una cancellazione); strumenti manuali solo con «Flush Mount Racking»: aggiungi fila («Click once to start... Drag the cursor to the end of the row»), singoli, sposta con Maiusc che aggancia alle file; «We recommend using Manual Module Controls for smaller, residential-size arrays» | «Placing a module over an automatically placed module will remove that module from the layout» |
| PV\*SOL premium | «Automatisch belegen»; formazione di moduli = «strenge Anordnung von Modulen innerhalb eines Rasters» | file di moduli trascinate una per una con il sistema di montaggio attivo (2, 5, 10, 20, 50 moduli o un numero scelto), «Rows of modules currently in an invalid area are shown in red» | Maiusc+clic riga, Alt+clic colonna; aree e aree vietate «per Drag&Drop verschoben» | «Module row arrays and module arrays can never be placed on the same active solar surface»; cambiando modulo di pari misura «Die Anordnung der Module... sowie die Verschaltung bleibt erhalten» |
| PVsyst | «Zone» con Pitch, Tables spacing, Align tables, «Fill zone» | «Slide row», «Add tables» a sinistra o a destra; tavole a mano | nel Module Layout «suppress some modules in the table (by right-clicking)»; sui piani poligonali «left-clicking adds a module and right-clicking removes one» | «Once tables are generated you can edit, delete, move or rotate them as you wish independently»; **«Warning : Any changes on rows will be lost if you generate the zone again»**; frecce con Ctrl 1 cm, Maiusc 10 cm, Ctrl+Maiusc 1 m |
| Sunny Design | «[Align PV modules]» con spaziature e corridoi ogni N file | no | «Click the required module and drag» sulla griglia, Ctrl libero, Ctrl+A; «snap-to-grid» (5.22); «When roof objects are moved, existing PV modules are automatically removed or added» (5.61) | lo stesso modello: griglia con moduli spostabili |
| SolarEdge Designer | «automatically fill the desired roof facet», «Toggle auto-fill», racking, row offset, orientazione, spaziature | | «module group»; il singolo con doppio clic (scheda dei tasti, solo dall'anteprima) | |
| PVcase Roof Mount (in AutoCAD) | PV area con frames, «Partial Frames», «Align rows», «Clear PV area», «Draw alignment line» | | frames spostati con Move di AutoCAD | i frames spostati «their color changes to red» e finiscono nel layer «PVcase Shadow Block» finché non si fa «Reassign frames» |
| Skelion (SketchUp) | pannelli inseriti su una faccia | | componenti di SketchUp: Move e Rotate nativi | |

**Quattro famiglie** [I]: (a) area che si riempie, con le rimozioni come maschera (HelioScope, Aurora Fill, SolarEdge, PVcase, Sunny Design); (b) file disegnate con il passo (PV\*SOL, PVsyst zone e sheds, OpenSolar a terra, Aurora a terra); (c) moduli oggetti uno per uno (Sunny Design, HelioScope manuale, Aurora manuale, Skelion); (d) ibridi: da automatico a modificabile (PVsyst tavole dopo il fill, OpenSolar nuovo gruppo da una selezione, PVcase frames rossi). **Nessuno ha un comando «esplodi»**: i più vicini sono le tavole indipendenti di PVsyst dopo il riempimento e il nuovo gruppo di OpenSolar. Tutti tengono un invariante: un tipo di modulo e un orientamento per superficie (Sunny Design, PV\*SOL), una pendenza e un azimut per gruppo (OpenSolar, HelioScope). Solo PVsyst avverte che rigenerare cancella le modifiche a mano.

### C.4 Il modello dei dati: le alternative

Oggi: **posa automatica con una maschera di rimozioni** (famiglia a). Le alternative:

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| C1. **Correzioni sulla posa automatica**: oltre a `removed`, per riga uno scarto (`shift[riga] = (du, dv)`), righe soppresse, righe aggiunte in coda; i moduli restano derivati | 3 | 4 | 4 | 2-3 giorni. Dà «sposta la fila» subito; ma le chiavi «riga:posto» restano fragili: ogni cambio di passo le sposta su altri moduli, come oggi con `removed`. Non dà il singolo modulo spostato |
| C2. **File come oggetti** (`SubField.rows`: origine, direzione, numero di moduli, passo tra moduli, livello delle tavole), generate dalla posa automatica e poi modificabili: spostare, accorciare, allungare, aggiungere, togliere; i moduli derivano dalle file in modo deterministico; `removed` resta per i singoli | 5 | 3 | 3 | 4-6 giorni. È la famiglia (b) di PV\*SOL, PVsyst e OpenSolar: la fila è l'unità che il progettista disegna e sposta. Le chiavi dei moduli diventano «fila:posto» con la fila identificata, non numerata: stabili |
| C3. **Moduli espliciti** (`SubField.modules`: lista di `PlacedModule` salvata nel file), la posa automatica solo come riempimento iniziale | 4 | 2 | 2 | 5-7 giorni. Il modello più libero (famiglia c) ma il più costoso: ogni spostamento, ogni cambio di modulo, ogni verifica va riscritta sui moduli; il file cresce (4.682 moduli × 6 numeri); si perde il passo dal sole e la pendenza coerente |
| C4. **Ibrido a tre livelli**: area → file (C2) → moduli; la posa automatica scrive le file; «esplodi» trasforma una fila (o tutte) in moduli singoli (file di un modulo), spostabili uno per uno; un interruttore `manual` spegne la rigenerazione e un «Riposa in automatico» la riaccende chiedendo conferma, con l'avvertimento di PVsyst | 5 | 3 | 3 | 6-8 giorni in tutto (C2 più 2 giorni). Dà a Daniel le tre cose chieste (file disegnate con il passo, file spostate, moduli esplosi e spostati) senza perdere l'automatismo e senza un secondo modello |
| C5. Solo «matrice» a mano (righe × colonne con passo) come oggetto nuovo accanto al sottocampo | 3 | 4 | 4 | 2-3 giorni; copre il «disegnare i pannelli con passo selezionato» ma non le file spostate singolarmente né i singoli; e sarebbe un terzo oggetto da stringare e verificare |

**Che cosa si perde e si guadagna** [I]:
- C1 tiene tutto l'automatismo (passo dal sole, VVF, ombre) ma le correzioni sono fragili e il singolo modulo non si sposta.
- C2 e C4 tengono il generatore come «proposta» e rendono le file oggetti veri: la stringatura a serpentina continua a leggere le file (`serpentine` raggruppa per `row`), i gruppi VVF si ricalcolano dalla geometria delle file, il 3D e la relazione non cambiano (leggono `Result.modules`). Si perde l'automatismo solo dove il progettista lo ha spento, e lo si dice.
- C3 è il più generale e il più costoso; si può arrivarci dopo C4 se servirà (per i moduli di forma diversa nello stesso sottocampo, oggi vietati).

### C.5 Che cosa cambia per stringhe, VVF, esclusioni, ombre, varianti, annulla [I]

- **Stringhe**: `assign` prende `(sottocampo, moduli posati)` e serpentina per riga: con le file oggetti la riga è la fila; i moduli esplosi hanno la loro fila di uno. Una fila spostata cambia le distanze ma non l'ordine; le stringhe del progettista (tema D) sono riferite alle chiavi stabili «fila:posto», quindi sopravvivono a uno spostamento e cadono solo se la fila sparisce (allora si dice quali moduli sono rimasti fuori, come oggi `wiring.left`).
- **Vigili del Fuoco**: oggi la posa automatica rispetta gruppi di 20 m e corridoi di 2 m costruendoli. Con le file a mano le regole diventano **verifiche**: gruppi ricavati dalle file (unione delle impronte, raggruppate a meno di 2 m), avviso «gruppo di 26 m» o «corridoio di 1,4 m» nella pagina Verifiche con il «Correggi» che riposa in automatico. È il modello di Aurora: «errori segnalati a colori senza bloccare» (studio 05).
- **Esclusioni e margini**: una fila trascinata su un lucernario o fuori dal margine si colora di rosso durante il gesto (PV\*SOL) e, se lasciata lì, produce una verifica «3 moduli sull'esclusione Lucernario 2»; non si vieta, perché il progettista può avere ragione (un'esclusione approssimata).
- **Ombre**: «fuori dalle ombre» resta un'opzione del generatore; con la posa a mano diventa anch'essa una verifica («5 moduli in ombra nel giorno di progetto»), con il conteggio che c'è già (`count_out_of_shadows`).
- **Varianti**: le file stanno nel sottocampo, che è per variante: nulla cambia. Il confronto delle varianti legge i risultati: nulla cambia.
- **Annulla**: un trascinamento di fila è un'istantanea al rilascio; «esplodi» e «riposa in automatico» sono passi con il loro nome.
- **File `.meridiana`**: `SubField.rows` (lista) e `manual: bool`; versione del formato +1 (insieme al tema A: una sola migrazione, 6 → 7 o direttamente 7); i file vecchi hanno `rows = []` e `manual = False`, cioè come oggi.
- **Finestra**: strumento «Fila» (disegna una fila: primo clic, direzione e lunghezza con gli agganci, il passo dal pannello; come la fila trascinata di OpenSolar), selezione della fila in pianta (clic sul modulo con Maiusc? meglio: un clic seleziona il modulo, un secondo clic sulla stessa fila la seleziona tutta, come i livelli di selezione di Draft e SketchUp), Sposta del tema B sulle file e sui moduli esplosi, menu contestuale con «Esplodi», «Riposa in automatico», «Togli la fila», «Aggiungi una fila in coda».

### C.6 Raccomandazione

**C4**, in tre compiti:
1. Le file come oggetti: `rows` nel modello, generate da `layout.compute` (che oggi ha già righe, posti, gruppi), chiavi stabili, `Result` ricostruito dalle file; nessun gesto nuovo; tutti i test di oggi devono dare gli stessi moduli (la prova è che i 23 progetti PVsyst importati posano ancora gli stessi moduli). 3 giorni.
2. I gesti sulle file: strumento Fila, sposta (con il tema B), accorcia, allunga, togli, aggiungi; le regole VVF e le ombre come verifiche; `manual` con l'avvertimento. 3-4 giorni.
3. Esplodi e i singoli moduli: fila di un modulo, sposta, ruota di 90° (doppio clic, come Aurora), Canc; stringhe e relazione sui moduli esplosi. 2 giorni.

**Da decidere a Daniel**
- Se la posa automatica deve restare il gesto principale (si disegna l'area e si chiede «Posa», poi si corregge) o se lo strumento Fila deve diventare il primo gesto: la raccomandazione è tenere l'automatico come prima proposta, perché il passo dal sole e le regole VVF sono il valore di Meridiana.
- Quando si cambia modulo, passo o inclinazione con le file a mano: rigenerare chiedendo (PVsyst) o adattare le file tenendo origine e numero di moduli (PV\*SOL quando le misure sono uguali)? Proposta: adattare quando il modulo ha le stesse misure entro 2 cm, chiedere altrimenti.
- Se i moduli esplosi possono uscire dal sottocampo o cambiare falda: proposta no, restano dentro il loro sottocampo (invariante di tutti i programmi letti).

## D. Inverter e stringhe

### D.1 Cosa chiede Daniel

«Non vedo un editor di stringatura e da nessuna parte la possibilità di scegliere inverter.»

### D.2 Che cosa fa oggi Meridiana [V]

- L'inverter si sceglie nella scheda **Producibilità**, gruppo «Inverter»: «Scegli dal catalogo…», «Dimensiona da solo» (rapporto DC/AC), «Quanti». Un solo modello per progetto (`energy["inverter"]`, `inverter_count`), nessuna assegnazione dei sottocampi agli inverter o agli MPPT: `_strings` in `EnergyJob` prende il modulo più usato e divide i moduli per il numero di inverter.
- Le stringhe stanno nello stesso posto, gruppo «Stringhe (CEI 64-8/7)»: temperatura minima, moduli in serie (0 = suggerite), «stringhe su ogni ingresso» scritte come «2;1». La proposta (`stringing.suggest`) e le verifiche (`stringing.plan`: Uoc max a Tmin, Isc max, finestra MPPT alla cella più calda e più fredda dell'anno tipo, protezioni di stringa oltre due in parallelo, SELV) escono dopo il calcolo dell'energia, perché la temperatura massima di cella viene dalla simulazione.
- Le stringhe si **disegnano in pianta** (`assign` a serpentina riga per riga, mai tra due sottocampi; nome inverter.ingresso.stringa; colore per ingresso; W le mostra e nasconde) e i moduli fuori stringa sono segnalati nelle Verifiche. Nessuna modifica a mano: né sui moduli né sull'ordine.
- Daniel non ha trovato né l'uno né l'altro: la progettazione elettrica non ha un posto suo, sta in fondo a una pagina di parametri della simulazione.

### D.3 Come fanno i programmi di riferimento [V]

| Programma | Dove sta l'elettrico | Più inverter e MPPT | Stringhe a mano | Verifiche in diretta |
|---|---|---|---|---|
| PVsyst | Finestra «System» della variante (sottocampi con modulo, inverter, «Show sizing»); poi «Shadings > Electrical shadings: Module Layout», schede Mechanical ed Electrical, «usually the last step» | Sub-array illimitati, «identical modules and inverters, same number of modules in series, same orientation» per ingresso; multi-MPPT come inverter intero o «independent MPPT inputs» («you enter the number of MPPTs rather than the number of inverters»); 10 stringhe su 3 MPPT = 3 + 3 + 4 | Nel Module Layout: a sinistra «a list of all inverter (or MPPT) inputs», si sceglie la stringa e si cliccano i moduli, «You can un-assign a module by right-clicking», trascinamento per scambiare; «Auto Attribution» con strategie (una fila per stringa, «U-connexion», «Left to right» o «Going back and forth», «Same row per MPPT»); «obviously cumbersome with a big system» | Grafico di dimensionamento; «Red warnings mean the simulation cannot run. Orange warnings are advisory. The System LED button shows the same color codes»; condizioni Vmpp a 60 °C sopra il minimo, Vmpp a 20 °C sotto il massimo MPPT, Voc a -10 °C sotto la massima assoluta e sotto la tensione di sistema del modulo (le prime due «fuzzy», le altre obbligatorie); sovraccarico 0,2-3 % arancione, oltre 3 % blocca |
| Aurora | Design Mode, menu «System» a sinistra: «Add Components» (inverter posato sulla scena), «String/Connect» (tasto C), «AutoStringer», «AutoDesigner» | Inverter posati uno per uno | «Left click and hold to drag the string across modules», «Release left click to complete the string», il nodo della stringa trascinato la allunga o accorcia; Auto-String su una selezione | «Red means the string length is too short or too long (outside the inverter's acceptable voltage input range)», «Green means the string length is valid»; «Validate design» elenca «Panels not strung to inverters» |
| HelioScope | Passi «3. Mechanical Layout» e «4. Electrical Design»; «Wiring Zone is where you define the electrical settings for one or more Field Segments» | Inverter dal menu, quantità automatica a DC/AC 1,25; combiner; cablaggio che segue gli inverter spostati | Nessuna: «set from temperature» (ASHRAE) o «set manually» la lunghezza delle stringhe, instradamento «Along Racking / Up and Down Racking»; i moduli che non fanno una stringa intera restano «unstrung» | Avviso di clipping fuori dalla finestra MPP |
| OpenSolar | «Project Zone > Design tab», schede Panel, Inverter, Battery…; «+ Inverter», «+ String» per MPPT | Più inverter; MPPT espliciti | Si sceglie la stringa e si trascina sui pannelli («dragging across panels to connect them»); «Auto String» | «Real-time compatibility feedback via color-coded icons and pop-ups», «A dedicated MPPT pop-up appears for each MPPT input» con «Voltage per string at temperature extremes», l'icona «turns red»; DC/AC 75 % / 133 % / 150 % |
| PV\*SOL premium | Pagina «Inverters» dopo «PV Modules» e «3D Design»: Configuration, Configuration check, Configuration limits, Polystring | «Per used MPP tracker: Specify number of strings and number of modules per string»; «Suggest configuration» e «Select configuration»; SolarEdge con le sue regole | Nel 3D: «Change module assignments», i moduli trascinati accanto alla loro stringa (dal forum della hotline); «Polystring» solo a mano | Vmpp min a 70 °C, max a 15 °C, Voc a -10 °C; «prohibited range» (blocca) e «blocking range» (perdite) |
| Sunny Design | Pagina «Configure PV system» (aree «Inverter design», «PV inverter») e «Visual roof planning» con la scheda «Electrical design» | Fino a 6 campi per sottoprogetto, inverter con «Inverter Filter», «Design suggestions», «Automatic design», «Manual design» | Clic sui moduli in ordine o trascinamento («connect when the pointer passes their middle»); mouseover sugli estremi per allungare; clic toglie o aggiunge; «Recalculating strings» per stringa, falda o tutte; nome «1A.1.3» (inverter 1, ingresso A, stringa 1, modulo 3) | Contorno rosso = modulo non collegato; linea rossa = stringa senza ingresso; superficie rossa = troppo corta o lunga; linea gialla = collegata; superficie verde = corretta e selezionata; «Colored» per stringa |
| SolarEdge Designer | «Easily create electrical designs for sites with multiple module groups», «auto-stringing to separate areas on a site and string specific module groups together» | Per gruppo di moduli | «s» avvia la stringa (scheda dei tasti, solo dall'anteprima) | |
| Solarius PV | «Configurazione guidata del generatore e del quadro» | Il configuratore propone «solo le composizioni del campo fotovoltaico (numero di stringhe per numero di moduli)» che passano le verifiche | No | «diagnostica operativa... alert» |

**Quattro famiglie** [I]: (a) solo automatico con parametri (HelioScope, Solarius); (b) automatico, poi clic o trascinamento sui moduli (PVsyst, Sunny Design, SolarEdge); (c) tutto in tabella (PV\*SOL, finestra System di PVsyst); (d) trascinamento sui moduli in pianta (Aurora, OpenSolar). Tutti: prima l'inverter, poi le stringhe; colori per stringa o per validità; verifiche come colore più finestra o grafico; «ricalcola» come via d'uscita dopo le modifiche a mano.

### D.4 Dove deve stare

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| D1. **Una scheda «Impianto»** tra Modello e Producibilità: a sinistra la pianta con le stringhe (la stessa `PlanView`, in modo stringhe), a destra gli inverter con i loro MPPT e l'elenco delle stringhe; le Verifiche in basso | 5 | 4 | 3 | è il passo «Electrical» di HelioScope, la pagina «Inverters» di PV\*SOL, «Configure PV system» di SMA: dove un progettista lo cerca. 2 giorni di scheda più l'editor |
| D2. Un gruppo «Elettrico» nelle Proprietà del sottocampo (inverter e ingresso del sottocampo) | 3 | 4 | 4 | utile in più, ma non è un editor: non si vede l'insieme |
| D3. Un pannello agganciabile «Stringhe» nella scheda Modello | 3 | 3 | 3 | la pianta della scheda Modello è già piena (disegno, falde, ostacoli); mescolare la posa con l'elettrico confonde |
| D4. Lasciare tutto in Producibilità ma in cima, con un titolo chiaro | 2 | 5 | 5 | non è stato trovato lì |

### D.5 Più inverter e i loro MPPT [I]

- Modello: `energy["inverters"]` = lista di `{record, count, name}`; ogni sottocampo cita l'inverter e l'ingresso (`sf.params["inverter"]`, `["mppt"]`) oppure «automatico»; l'inverter unico di oggi diventa il primo della lista (migrazione dei dati dell'energia, non del formato: `energy` è un dizionario di ciò che differisce dai predefiniti).
- `system.arrays_of` raggruppa già per modulo e orientamento (`ArraySpec`); i gruppi vanno distribuiti sugli ingressi con la regola di PVsyst (identici per ingresso, stringhe spalmate 3 + 3 + 4) e il «dimensiona da solo» prende tanti inverter quanti servono con il rapporto DC/AC.
- Le verifiche per ingresso ci sono già (`plan`: corrente di ingresso, cortocircuito, fusibili); mancano il rapporto DC/AC per inverter e il bilanciamento tra ingressi (avviso, come PVsyst).
- Il catalogo ha già `mppt_count`, `strings_per_mppt`, le correnti per ingresso (`inverters_curated.json`); la lista CEC no (solo curve).

### D.6 L'editor delle stringhe [I]

- **Automatico prima**: la proposta di oggi (`suggest` e `assign`), con le strategie di PVsyst come opzioni: una fila per stringa, «a U» su due file, «avanti e indietro»; e «una fila per MPPT».
- **Poi a mano, sui moduli in pianta**: si sceglie una stringa nell'elenco (o se ne crea una su un ingresso) e si cliccano i moduli in ordine (PVsyst, Sunny Design) o si trascina sopra (Aurora, OpenSolar: «connect when the pointer passes their middle»); clic destro toglie; trascinando l'estremo si allunga; un modulo preso da un'altra stringa le viene tolto, con l'avviso.
- **Colori**: uno per stringa dal tema (`theme_colors` ha già i colori degli stati e della selezione: servono 8-10 tinte distinte dal colore scelto, come i «colori dei componenti elettronici» di PVsyst), più il semaforo di Sunny Design: rosso se la stringa è fuori dalla finestra o senza ingresso, giallo se collegata ma da verificare, verde se corretta; i moduli fuori stringa con il contorno rosso.
- **Verifiche in diretta**: `stringing.plan` costa pochi millisecondi (quattro chiamate al modello a un diodo) e si può rifare a ogni clic; la temperatura massima di cella dalla simulazione, se c'è, altrimenti le condizioni di progetto (PVsyst 60/20/-10 °C, PV\*SOL 70/15/-10 °C: scelte di programma, non norma) con la fonte scritta nel pedigree; la CEI 64-8/7 resta citata solo con i riferimenti già in `stringing.py` (archivio sul PC).
- **Dove si salva**: `energy["strings"]` oggi è `{n_series, per_mppt}`; diventa l'elenco delle stringhe `{inverter, mppt, modules: [chiavi "sottocampo/fila:posto"]}` con `auto: true` finché non si tocca; le chiavi stabili del tema C servono anche qui.
- **Il tasto W** mostra e nasconde le stringhe in ogni scheda; nella scheda Impianto sono sempre visibili.

### D.7 Raccomandazione

**D1 con D5 e D6**, in due compiti:
1. La scheda Impianto e gli inverter: lista di inverter con MPPT, sottocampi assegnati agli ingressi o automatici, «dimensiona da solo» su più inverter, verifiche per inverter e ingresso; il gruppo «Inverter» in Producibilità diventa un rimando («Impianto: 2 × SUN2000-10KTL, cambia…»). 4-5 giorni.
2. L'editor delle stringhe: automatico con le strategie, a mano con clic e trascinamento, colori per stringa e semaforo, verifiche in diretta, relazione con l'elenco delle stringhe per inverter. 4-5 giorni.

**Da decidere a Daniel**
- Il nome della scheda: «Impianto», «Elettrico» o «Stringhe e inverter».
- Le condizioni di progetto per le verifiche in diretta prima della simulazione: PVsyst (60/20/-10 °C), PV\*SOL (70/15/-10 °C) o valori suoi.
- Se gli ottimizzatori e i microinverter (già nel catalogo) entrano nello stesso editor subito (Aurora: con i micro «modules do not need to be strung») o dopo.

**Aggiunto il 23/10/2026, idea di Daniel (R12 di `docs/richieste.md`):** «una modalità di stringatura dedicata che mostra opzioni inverter flottanti, in maniera chiara a seconda di stringhe supportate, se queste sono soddisfatte oppure no, se sono utilizzate e va bene, oppure no». Nell'editor delle stringhe:
- un pannello flottante per ogni inverter, sopra la pianta, con gli ingressi e gli MPPT;
- per ogni ingresso le stringhe che accetta, quelle collegate e il loro stato (verifica soddisfatta o no, ingresso usato o libero), con colore, icona e parola.
Il compito `16d-impianto-e-stringhe.md` lo prende nel secondo passo.

## E. Scelta dei moduli: i filtri del catalogo

### E.1 Cosa chiede Daniel

«La scelta dei pannelli non è molto semplice. Sarebbe buono avere dei filtri fatti meglio che almeno permettano di distinguere per monocristallino / policristallino, ecc, e tra mono e bifacciale (anche se so che al giorno d'oggi si commercializzano praticamente solo i bifacciali).»

### E.2 Che cosa fa oggi Meridiana [V]

- `catalog_dialog.py`: una casella di ricerca (ogni parola deve comparire in marca, modello o serie), l'origine (schede lette per Meridiana, lista CEC), un intervallo di potenza, la tabella (marca, modello, W, tecnologia, origine) limitata ai primi 400, la scheda completa a destra con l'indirizzo della scheda tecnica. Nessun ordinamento per colonna, nessun filtro su tecnologia, bifacciale, dimensioni, efficienza, marca, anno.
- `catalog.search` filtra in Python su tutti i record a ogni battuta (dopo 200 ms): con 16.959 record costa 2-3 ms senza classificazione [V, prova], va bene.

### E.3 Che cosa c'è davvero nei dati [V, prova: `16-prove/catalogo_filtri.py`]

| Campo | Schede lette (73) | Lista CEC (16.886) |
|---|---|---|
| marca, modello, potenza, Vmp, Imp, Voc, Isc, coefficienti | 73 | 16.886 |
| tecnologia | 73, scritta libera: «n-type TOPCon» 40, «n-type (architecture not stated)» 10, «HJT» 9, «back contact (ABC, HPBC 2.0, GPC, MWT…)» 13, una «n-type TOPCon (shingled…)» | 16.886, enumerata: Mono-c-Si 15.302 (più 9 «Mono-C-si»), Multi-c-Si 1.409, CdTe 126, Thin Film 27, CIGS 7, a-Si/nc 6 |
| bifacciale sì/no | 73 (47 sì) | 16.886 (3.732 sì) |
| bifaccialità (%) | 36 | 0 |
| celle | 67 | 16.886 (celle in serie) |
| dimensioni | 73 | 1.745 |
| efficienza | 73 dichiarata | 0 dichiarata, ricavabile da potenza e dimensioni per 1.745 |
| data | 73 (`retrieved`, ottobre 2026) | 0 nella copia in uso |
| tipo di cella (PERC, TOPCon, HJT, IBC) come campo | no (nel testo di «tecnologia» e nelle note) | no |

- La lista CEC nella forma in cui NREL la distribuisce con SAM (`CEC Modules.csv`, letto il 23/10/2026: 21.677 moduli, «Version 2026.7.3», «Date 6/23/2026» uguali per tutte le righe) ha le colonne `Technology` (famiglia del materiale), `Bifacial` (0/1), `Length`, `Width`, `BIPV`, i parametri a un diodo; **nessun tipo di cella, nessuna bifaccialità**. La copia nel programma è più vecchia (16.886 moduli).
- La lista della California Energy Commission (xlsx del 21/10/2026, 22.424 righe) ha in più `Family` («Monocrystalline» 18.259, «Polycrystalline» 3.823, «Thin Film» 328), `CEC Listing Date` e `Last Update`, la `Description` libera; **nessuna colonna «bifacial»**: la parola sta nel testo di 4.077 righe, «topcon» in 30, «hjt» in 69, «perc» in 128, «half-cut» in 10.259. Le dimensioni non sono più raccolte («No longer collected»). Aggiornata «three times a month».
- PVsyst: tecnologia enumerata nel .PAN (`Technol=mtSiMono`), «Bifacial» con il fattore di bifaccialità, «Obsolete devices are marked by the year of retrieval», opzione «presenting only the available devices», i preferiti «shown in green». PV\*SOL: tipi di cella «Si monocrystalline; Si polycrystalline; Si amorphous; … HIT; CIS; CdTe», fattore bifacciale «usually 70-80 %». Aurora: ricerca per nome, e «simulations currently do not model rear side power gain for bifacial modules». HelioScope: colonna «Module Type» con «Bifacial». OpenSolar: «Bifaciality» e «Transmission Factor» per modulo. ENF Solar (directory pubblica, 403 alla lettura): tag «Bifacial», «N-type», «HJT», «TOPCon», «PERC» per prodotto, «14 different search filters» dal comunicato del 2012.
- pvlib: `fit_cec_sam` vuole `celltype` in «monoSi, multiSi, polySi, cis, cigs, cdte, amorphous»; `infinite_sheds.get_irradiance` vuole `bifaciality` (predefinito 0,8). Quindi per il calcolo servono la famiglia del materiale e la bifaccialità; il tipo di cella (PERC, TOPCon, HJT) serve al progettista, non al modello.

**Conclusione** [I]: si può filtrare subito su famiglia del materiale, bifacciale sì/no, potenza, marca, origine; dimensioni ed efficienza su tutte le schede lette e su 1.745 della CEC; il tipo di cella (PERC, TOPCon, HJT, back contact) va **ricavato dal testo** e tenuto come «non detto» quando manca; la bifaccialità e la data per modello esistono solo nelle schede lette.

### E.4 La classificazione dal testo [V, prova]

Con sette espressioni regolari sui campi tecnologia, modello, serie e note (TOPCon; HJT, HIT, heterojunction; back contact, ABC, HPBC, IBC, BC; PERC; CdTe, CIGS, a-Si, thin film; multi, poly; mono):
- schede lette: TOPCon 48, back contact 13, HJT 9, non detto 3;
- CEC: monocristallino 15.310, policristallino 1.409, film sottile 166, HJT 1;
- **Correzione del 24/10/2026 [V]:** il conteggio delle schede lette (TOPCon 48, non detto 3) prendeva per TOPCon sette schede che scrivono «TOPCon is not printed» o «not stated», e i «mono» e «multi» nudi facevano silicio di «mono-facial» e «multilayer». Con le frasi negate escluse e le parole del silicio intere: TOPCon 41, contatti posteriori 13, HJT 9, non detto 10 (come in `docs/catalogo/moduli.md`); la CEC resta mono 15.310, poli 1.409, film sottile 166, HJT 1 sulla lista di allora.
- classificare tutto il catalogo una volta costa 111-132 ms (si fa al caricamento, in `catalog.load`, già in cache), poi il filtro costa 2,6 ms.
- Per le schede lette, la famiglia andrebbe scritta **come campo** nel JSON dalla prossima lettura delle schede (`cell_family`, `bifaciality_pct` c'è già), e la regola dal testo resta per la CEC.

### E.5 I filtri e la finestra

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| E1. **Filtri a faccette sopra la tabella**: famiglia della cella (combo: tutte, mono, poli, TOPCon, HJT, back contact, PERC, film sottile, non detto), bifacciale (tutti, sì, no), marca (combo con le marche dell'origine scelta), potenza da-a (c'è), efficienza minima, lunghezza massima, origine (c'è); il conteggio «n di N» (c'è); ordinamento per colonna; la ricerca viva | 5 | 5 | 4 | 1,5-2 giorni. GNOME HIG: «Search should be “live” wherever possible», combo solo con almeno tre voci; KDE: combo fino a 10 voci, oltre una lista; WinUI: «checkboxes, radio buttons, and sliders», la lista si aggiorna mentre si scrive |
| E2. Le stesse faccette come colonne di un `QSortFilterProxyModel` con `filterAcceptsRow` | 4 | 4 | 3 | più «Qt», ma il filtro in Python sulla lista costa 3 ms: il proxy non serve; `invalidateFilter` è deprecato dalla 6.13 |
| E3. Una barra laterale di faccette con i conteggi per valore (come i negozi online) | 4 | 4 | 3 | i conteggi per valore sono utili («TOPCon (48)»), costano un passaggio in più sui 17.000 record (3 ms): si può, in un secondo tempo |
| E4. Aggiornare la lista CEC dalla copia SAM (21.677 moduli, 2026.7.3) con `Length`/`Width` e `Bifacial`, e arricchirla con `Family`, `CEC Listing Date` e la `Description` della lista CEC (bifacciale e tipo di cella dal testo) | 4 | 4 | 4 | 1 giorno di strumento in `tools/`; la licenza BSD-3 di SAM è già nel programma; i dati CEC sono pubblici senza licenza dichiarata (da dire nella relazione come oggi) |
| E5. Una bifaccialità stimata per famiglia dove manca (PERC circa 0,70, TOPCon e HJT circa 0,80, dai valori di PV\*SOL «70-80 %» e dal predefinito 0,8 di pvlib) | 3 | 3 | 5 | mezza giornata; va marcata «stimata» nel pedigree e nella relazione, come ogni predefinito; Daniel decide se vuole numeri stimati nel catalogo |
| E6. Preferiti e «solo i disponibili» alla PVsyst | 3 | 5 | 4 | 1 giorno; i preferiti per marca sono quello che un progettista usa davvero; la disponibilità richiede la data per modello (solo schede lette) |

### E.6 Raccomandazione

**E1 con E4**, un compito di 2-3 giorni: il campo `cell_family` calcolato al caricamento (e scritto nelle schede lette), `bifacial` normalizzato, la finestra con le faccette, l'ordinamento per colonna, il conteggio, e lo strumento che rilegge la lista SAM con le dimensioni e il flag bifacciale. E5 ed E6 dopo, se Daniel li vuole.

**Da decidere a Daniel**
- Se i valori stimati di bifaccialità vanno nel catalogo (marcati) o se i moduli senza bifaccialità restano «mono» nel calcolo finché non la si scrive.
- Se «policristallino» merita un filtro proprio oggi (1.409 moduli CEC, 0 tra le schede lette) o basta la famiglia «mono/poli» dentro «tecnologia».
- Se aggiornare la lista CEC a ogni rilascio (uno strumento in `tools/`) o a mano.

## F. Attese visibili

### F.1 Cosa chiede Daniel

«Non è possibile mettere delle sorte di placeholder e caricamenti laddove sta renderizzando qualcosa?»

### F.2 Dove la finestra aspetta oggi [V]

Dalle misure dello studio 12 (Windows, progetto di prova con 188 moduli e grande con 4.682) e dall'appendice A del 23/10/2026:

| Attesa | Quanto | Che cosa si vede oggi |
|---|---|---|
| Avvio: costruzione della finestra | 0,7 s sul PC di Daniel (era 3,1) | nulla, poi la finestra |
| Prima accensione della vista 3D | circa 1 s (studio 12); 120 ms offscreen senza GPU [V, prova] | un riquadro vuoto |
| Posa dei moduli (thread) | 50-500 ms; «{n} moduli posati in {ms} ms» alla fine | il sottocampo «da posare di nuovo» con «…» nell'albero e la nota nelle proprietà (fase 2); nessun segno sulla pianta |
| Energia (thread) | 2,4-3,2 s sul progetto di prova dalla modifica alla fine; prima 6 s | «Producibilità: calcolo…» come testo permanente nella barra di stato (`busy`); i valori vecchi restano nelle pagine come se fossero nuovi (P7 dello studio 12, ancora aperto) |
| Ritorno del calcolo (thread della finestra) | 50-93 ms prova, 100-246 ms grande | nulla (sotto la soglia) |
| Sfondo della pianta (tessere) | 86 ms all'apertura dal disco (P8), poi la rete | celle vuote, poi le tessere |
| Catalogo | la prima `load` legge e decomprime 16.886 record | la finestra si apre quando è pronta |
| PVGIS | secondi, dipende dalla rete; con cache zero | «Scarico il meteo e calcolo…» nella barra di stato |
| Relazione PDF | 1-3 s [I] | il cursore, poi «Relazione scritta» |
| Prima apertura di Consumi e Bilancio | 80-180 ms | nulla |

### F.3 Che cosa dicono le linee guida e i programmi [V]

- **Soglie**: Nielsen 0,1 / 1 / 10 s (già nello studio 12a); NN/g: «Use a progress indicator for any action that takes longer than about 1.0 second», animazione ciclica «for actions that take between 2-10 seconds», percentuale oltre 10 s; Material 3: «Instant (under 200ms) No indicator; Short (200ms-5s) Loading indicator; Long (Over 5s) Progress indicator» (dall'anteprima, il sito non si legge senza JavaScript); GNOME: «Progress needs to be indicated whenever an operation takes more than around three seconds», «consider only showing the spinner after a period of time has elapsed», barra oltre 30 s; RAIL: 100 ms per la risposta, 1.000 ms oltre i quali «users lose focus»; `QProgressDialog` compare solo se la stima supera `minimumDuration` (4 s).
- **Scheletri**: NN/g (Tankala, 2023): «used to indicate progress only when the process that the system is performing is a full-page load», «with a wait time that's under 10 seconds», «If a page takes less than 1 second to load, skeleton screens or spinners aren't necessary»; Fluent 2: «A skeleton lets people know that a section of content is loading without blocking other parts of the page», per contenuti oltre un secondo, non per processi lunghi; Apple «Loading»: «Show something as soon as possible... placeholder text, graphics, or animations as content loads, replacing these elements as content becomes available», «Let people do other things in your app... while they wait»; Wroblewski (2013): «progress indicators by definition call attention to the fact that someone needs to wait».
- **Indicatori**: Apple: «All progress indicators are transient», «Keep progress indicators moving», «Don't switch from the circular style to the bar style», macOS «Prefer an activity indicator (spinner) to communicate the status of a background operation»; WinUI: la barra indeterminata «does not block user interaction», l'anello «blocks user interaction», e «do not put a progress indicator on each list item... use a ProgressBar and place it at the top of the collection»; JetBrains: barra nella barra di stato per i processi non bloccanti, tempo residuo arrotondato a 1, 2, 3, 5, 10, 15, 20, 30 s, «Cancel» se si può interrompere; VS Code: «progress is best kept within context», il poco importante «in the status bar».
- **Valori vecchi segnati**: Excel, «Stale value formatting»: «In Partial and Manual Calculation modes, Excel denotes a stale cell with a strikethrough»; FreeCAD: «White check mark on blue background: This indicates that the object has to be recomputed», F5 ricalcola, «Allow aborting recomputation... by pressing Esc»; QGIS: «a progress bar is displayed in the status bar», Esc ferma il disegno, la tela si disegna fuori schermo e si copia ogni 250 ms («Map update interval»); Blender: la barra di stato «Shows the progress of the currently running task... can be aborted by clicking the cancel button».
- **Programmi FV**: PVsyst «A progress bar will appear, indicating how much of the simulation is still to be performed» (tutorial v7); DIALux evo: «Start calculation Ctrl + Shift + Space», «Abort calculation Ctrl + Shift + Q», il pulsante diventa «Cancel calculation»; HelioScope: barra blu delle simulazioni in corso (solo dall'anteprima); Aurora: simulazione asincrona nell'API.
- **Accessibilità**: WCAG 2.2.2: un'animazione che dura più di 5 s accanto ad altro contenuto va potersi fermare; 2.3.3 chiede di poter spegnere il movimento (Meridiana legge già la preferenza di meno movimento).

### F.4 La prova [V, prova: `16-prove/attese.py`]

Offscreen, Linux:
- un arco che gira a 60 Hz sopra una pianta di 5.000 moduli: 63 fotogrammi al secondo, 0,12 ms l'uno (massimo 0,86); la pianta sotto ridisegna solo il rettangolo dell'arco, 0,09 ms a volta: **un indicatore sopra la pianta non costa nulla**;
- `QProgressBar` in modo «occupato» nella barra di stato: 60 ridisegni al secondo, 0,38 ms (massimo 4,8);
- un segnaposto a scheletro (tre gruppi di barre grigie) si costruisce e si mostra in 7 ms contro 6 ms della pagina vera con 18 campi: **lo scheletro non è più veloce della pagina**; ha senso solo dove la pagina vera deve aspettare un calcolo, non per nascondere la costruzione;
- la fotografia di una pagina (`QWidget.grab`, 360 × 682) costa 3 ms: si può mostrare l'immagine della pagina vecchia mentre si ricostruisce, al posto di uno scheletro;
- un `QQuickWidget` con una scena 3D: 19 ms di `setSource` e 120 ms al primo fotogramma offscreen (circa 1 s sul PC con la GPU, studio 12): 8-60 fotogrammi in cui un segnaposto si vedrebbe.

### F.5 Le famiglie di soluzioni

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| F1. **Valori vecchi segnati «da aggiornare»** nelle pagine dell'energia e nelle verifiche quando il progetto cambia dopo l'ultimo calcolo (grigio e barrato come Excel, un segno nel titolo della scheda come il check blu di FreeCAD), tolto al ritorno del risultato | 5 | 5 | 4 | 1 giorno; chiude P7 dello studio 12; costo zero (è una proprietà dei widget già aggiornati senza ricostruire) |
| F2. **Scheletro per la 3D** all'avvio (un riquadro con cielo, terreno e il contorno degli edifici dalla pianta, in `QPainter`, sopra il `QQuickWidget` finché non arriva il primo fotogramma) e per le pagine alla prima apertura (Consumi, Bilancio: la pagina si costruisce in un timer dopo lo scheletro) | 4 | 4 | 4 | 1 giorno; la 3D è l'unica attesa di circa 1 s senza nulla sullo schermo; per le pagine da 80-180 ms lo scheletro sparisce subito (sotto le soglie: si può evitare) |
| F3. **Arco nella zona che aspetta**, dopo 300 ms: in alto a destra della pianta durante la posa (sul sottocampo che si riposa), sulla pagina dell'energia durante il calcolo, nel catalogo durante la prima lettura; come l'arco provato, 0,1 ms a fotogramma; fermo se il sistema chiede meno movimento | 5 | 5 | 4 | 1 giorno; «within context» (VS Code), «In a corner» (JetBrains); sotto 300 ms nessun indicatore (Material 200 ms, RAIL 100 ms, Nielsen 1 s: 300 ms è il mezzo) |
| F4. **Barra di avanzamento nella barra di stato con Annulla** per PVGIS (scarico, passi noti) e per la relazione PDF (pagine); percentuale solo lì | 4 | 4 | 4 | 1 giorno; i lavori sono già in thread con la generazione: Annulla = scartare il risultato (il thread finisce da solo), come «cancel()» che non ferma un calcolo partito; `requestInterruption` per PVGIS tra una richiesta e l'altra |
| F5. Risultati parziali: la produzione mensile prima dell'economia, le ombre di 12 giorni prima dell'anno (HelioScope), la posa sottocampo per sottocampo appena pronta | 4 | 3 | 3 | 2 giorni; il calcolo dell'energia è già a passi (simulazione, consumi, bilancio, economia): basta emettere un segnale per passo e aggiornare la pagina a pezzi; la posa già riposa solo ciò che è cambiato |
| F6. Finestra modale di avanzamento (`QProgressDialog`) | 1 | 5 | 5 | contro tutte le linee guida lette per i lavori non bloccanti; solo per l'importazione di un progetto PVsyst, se mai |
| F7. Spinner animato (QMovie) o effetti di opacità (`QGraphicsOpacityEffect`) sulla pagina intera | 2 | 3 | 4 | la pagina opaca blocca la lettura dei valori vecchi, che è proprio ciò che si vuole tenere; Qt avverte di disattivare gli effetti sulle piattaforme lente |

### F.6 Raccomandazione

**F1, F3, F2 (solo la 3D) e F4**, in un compito di 3-4 giorni, in quest'ordine; F5 dopo, con la scheda Impianto (tema D), perché le stringhe in diretta ne hanno bisogno.
- Regole fisse [D]: niente sotto 300 ms; arco nella zona interessata da 300 ms a 10 s, con il testo nella barra di stato; barra con percentuale e Annulla solo per PVGIS e PDF; valori vecchi sempre visibili e segnati; nessuna finestra modale; tutto fermo con «meno movimento».
- Da vedere a occhio sul PC: lo scheletro della 3D sopra il `QQuickWidget` vero (sul PC il primo fotogramma arriva dalla GPU, e il segnaposto va tolto al segnale giusto: `sceneGraphInitialized` o il primo `afterRendering`).

**Da decidere a Daniel**
- La soglia (300 ms proposta) e se l'arco va anche sulla pianta durante la posa, dove oggi c'è solo «…» nell'albero.
- Se i valori «da aggiornare» vanno barrati (Excel) o solo grigi con il segno nel titolo della scheda.

## G. Il perno della vista 3D

### G.1 Cosa chiede Daniel

«In vista 3d ci si sposta con ctrl all'interno del disegno, quando non si preme la vista si ancora su un punto centrale, che ci sta, ma sarebbe buono vedere un mirino che permetta di capire a cosa è ancorata la vista.»

### G.2 Che cosa fa oggi Meridiana [V]

- Il perno dell'orbita è il punto del modello sotto il cursore al momento della pressione, altrimenti il terreno sotto il cursore, altrimenti il bersaglio della camera (`camera.pivot`, il «Drag at cursor» di FreeCAD); nelle preferenze si può scegliere «centro della selezione» o «centro della finestra» (`pivot_mode`).
- Durante l'orbita `Scene.qml` mostra una pallina scura sul perno (`backend.orbiting`, `pivotScale` la tiene a circa 10 px); appena si rilascia sparisce. Il clic centrale breve ricentra sul punto (`recentre`) e lo fa diventare il bersaglio.
- Il gesto che Daniel descrive («con ctrl») è lo stile di navigazione scelto nelle preferenze (studio 15: in «CAD» Ctrl+destro o centrale più sinistro; in «AutoCAD» Maiusc+centrale): fuori dal trascinamento la vista non è ancorata a nulla di visibile, e il bersaglio della camera (il punto dell'ultimo ricentra o dell'ultimo «adatta») non si vede mai.

### G.3 Come fanno i programmi [V]

| Programma | Quando si vede il perno | Com'è | Come si sceglie |
|---|---|---|---|
| FreeCAD 1.0+ | Solo durante il trascinamento («the rotation center of the view is shown when dragging», `showRotationCenter(true)` entrando in DRAGGING) | Sfera rossa semitrasparente (colore 0xFF0000B3), `SoShapeScale` quindi della stessa grandezza sullo schermo, sopra tutto (`SoAnnotation`), dimensione e colore nelle preferenze, disattivabile | «Rotation mode»: Window center, Drag at cursor (punto colpito, altrimenti il piano focale), Object center (centro della scatola della scena) |
| AutoCAD 3DORBIT | «A small dark sphere displays temporarily, representing the target point about which your view rotates» | Sfera scura | ORBITAUTOTARGET 0: dove si clicca, «will snap to the nearest feature on an object when your cursor hovers over the object»; 1: centro degli oggetti visibili |
| Revit | Con lo strumento Center delle SteeringWheels: «a sphere (pivot point) displays, along with the cursor» mentre si passa sul modello; con Maiusc+centrale nulla | Sfera (verde nelle SteeringWheels) | «The center of rotation is the center of all model geometry», o l'oggetto selezionato; Ctrl nell'Orbit sposta il perno |
| SketchUp | Mai | | «rotate around the center of the drawing area»; doppio clic centra |
| Blender | Mai durante l'orbita; il cursore 3D (mirino sempre visibile) è il perno delle trasformazioni, non dell'orbita | | «Orbit Around Selection», «Auto Depth», Alt+centrale fissa il «point of interest» |
| Rhino 8 | Solo a richiesta: il widget della camera (`Camera Show`) mostra il target in altre viste | | «RotateViewAroundObjectAtMouseCursor», «Zoom Target», «Auto adjust camera target after Pan and Zoom» |
| Fusion, Onshape, Unity, Unreal, Godot | Nessun segno documentato | | Fusion «Orbit around point» con Maiusc+clic+centrale; Unreal «Orbit camera around selection»; Godot scatti di 45° con Alt |
| DIALux evo | Niente di documentato sul centro di rotazione (solo WASD, Z e P per zoom e pan senza rotella) | | |
| Autodesk Research, «Safe 3D Navigation» (2008) | «The first, and perhaps most critical feedback, is to explicitly display the navigation pivot point in the scene» | «a visibly labeled green-ball in the scene with visual hints about its depth... wrapped in three orthogonal belt lines to make any rotation of the ball perceivable»; se il perno esce dallo schermo «the pivot point is centered in the canvas but keeping the same depth level» | «Click or drag on model to set pivot»; «When we introduced this feature, it had an immediate positive effect in all of our user tests» |

**In sintesi** [I]: nessun CAD mostra il perno sempre; FreeCAD e AutoCAD lo mostrano durante l'orbita; Revit e Autodesk Research lo mostrano **al passaggio con lo strumento che lo imposta**; tutti lo scelgono tra «sotto il cursore», «selezione» e «centro».

### G.4 Le famiglie di soluzioni

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| G1. **Mirino durante l'orbita, più chiaro**: al posto della pallina, la «palla con tre cinture» di Autodesk (tre anelli ortogonali, un punto al centro), della stessa grandezza sullo schermo, nel colore d'accento del tema con l'alone; già tutto in QML (`pivotScale`, `orbiting`) | 4 | 5 | 5 | 0,5 giorni; risponde a «capire a cosa è ancorata» mentre si gira |
| G2. **Mirino al passaggio con il tasto del gesto tenuto** (Maiusc nello stile AutoCAD, Ctrl in CAD): prima di premere il mouse, il mirino segue il punto sotto il cursore che diventerà il perno; si ferma sul perno appena si preme | 5 | 4 | 4 | 1 giorno; è il «Center tool» di Revit e la «green ball» di Autodesk; costa un `pick` per movimento del mouse solo con il tasto tenuto (il pick è già fatto a ogni pressione e rotella; sul PC è da misurare: 0,2-1 ms per fotogramma secondo lo studio 12) |
| G3. **Mirino sempre visibile sul bersaglio della camera** (il punto dell'ultimo ricentra, adatta o orbita) | 2 | 3 | 5 | 0,5 giorni; è quello che Daniel chiede alla lettera, ma nessun CAD lo fa: con il perno «sotto il cursore» il bersaglio non è il perno della prossima orbita, e il segno mentirebbe; sta tra i moduli e copre il disegno; Blender tiene sempre visibile solo il cursore 3D, che non è l'orbita |
| G4. **«Fissa il perno qui»**: il clic centrale breve (già «ricentra») lascia il mirino visibile per un secondo e lo fa diventare il perno finché non si clicca altrove; con `pivot_mode = "centre"` il mirino sta sul bersaglio sempre, perché lì è davvero il perno | 4 | 5 | 5 | 0,5 giorni; dà a chi vuole il perno fisso (Daniel: «si ancora su un punto centrale») il segno coerente, e il modo sotto il cursore resta senza segno fuori dall'orbita |
| G5. Il perno che resta sullo schermo: se esce dalla vista, torna al centro della vista alla stessa profondità (Autodesk) | 3 | 4 | 5 | 0,5 giorni; evita l'orbita che «sembra uno zoom» quando il perno è fuori |

### G.5 Raccomandazione

**G1 con G2 e G4**, un compito di 1-2 giorni: il mirino a tre anelli durante l'orbita; al passaggio con il tasto del gesto tenuto (G2), disattivabile nelle preferenze accanto a «perno»; il clic centrale che fissa il perno e lo mostra; con il perno «centro della finestra» il mirino sul bersaglio sempre (G4); G5 se costa poco. **Niente mirino sempre visibile** con il perno sotto il cursore, perché mentirebbe. Da provare sul PC: il costo del pick a ogni movimento con Maiusc tenuto e la leggibilità del mirino sull'ortofoto.

**Da decidere a Daniel**
- Se il mirino al passaggio deve apparire solo con il tasto del gesto tenuto (proposto) o sempre con il mouse fermo per 400 ms sul modello (come i punti «acquisiti» del disegno).
- Il predefinito del perno: «sotto il cursore» (oggi, FreeCAD, AutoCAD) o «centro della finestra» con il mirino fisso, che è il comportamento che ha descritto.

## Il piano

### L'ordine, per valore e fatica

| Ordine | Tema | Perché qui | Fatica | Dipende da |
|---|---|---|---|---|
| 1 | **D. Impianto e stringhe** | È ciò che Daniel non ha trovato: un progettista cerca l'elettrico prima di ogni altra cosa; chiude anche una riga «○» di `funzionalita.md` | 8-10 giorni | nulla (meglio dopo C per le chiavi stabili, ma non necessario) |
| 2 | **A. Tetti a falde** | È il difetto più visibile («si sballa completamente») e il più rischioso: l'algoritmo va fatto presto, con il riferimento già pronto | 6-9 giorni | nulla |
| 3 | **E. Filtri del catalogo** | Poca fatica, risultato immediato; i dati ci sono | 2-3 giorni | nulla |
| 4 | **F. Attese visibili** | Poca fatica; chiude P7 dello studio 12; serve anche a D (stringhe in diretta) | 3-4 giorni | nulla |
| 5 | **G. Perno della 3D** | Un giorno o due, tutto già in QML | 1-2 giorni | nulla |
| 6 | **B. Sposta e ruota** | Fatica media, gesto quotidiano; prepara C | 7-10 giorni | nulla |
| 7 | **C. Posa manuale** | La più lunga e la più delicata per il modello dei dati; richiede B per i gesti | 8-12 giorni | B |

In tutto 35-50 giorni di sessione. I temi E, F e G si possono dare a sessioni cloud in parallelo con D o A, perché toccano file diversi (`catalog_dialog.py`; `window.py` e le pagine dell'energia; `view3d.py` e `Scene.qml`). A e B toccano il formato e il modello: uno alla volta, e il formato sale una volta sola per ogni unione (6 per A, 7 per C).

### Le bozze dei compiti

In `docs/compiti/`, da lanciare dopo la decisione di Daniel, ognuna con i passi, i commit e i test:
- `16a-tetti-a-falde.md`
- `16b-sposta-e-ruota.md`
- `16c-posa-manuale.md`
- `16d-impianto-e-stringhe.md`
- `16e-filtri-catalogo.md`
- `16f-attese.md`
- `16g-perno-3d.md`

### Le domande a cui solo Daniel può rispondere

**Risposta di Daniel, 23/10/2026: «Tutti i punti proposti vanno bene!».** Valgono le proposte qui sotto; per la pendenza la fonte da citare è il manuale ANDIL 2025 (sezione A.8). I valori decisi sono scritti in testa a ogni compito `docs/compiti/16*.md`.

1. **A**: la pendenza predefinita (35 %, 19,3°, dalle schede delle tegole marsigliesi; oppure il tipo di copertura al posto di un numero); le pendenze per lato subito o dopo; le testate di una L sui due bracci come predefinito.
2. **B**: Ctrl durante lo spostamento = copia (proposto) o scatti; M a Sposta e Misura su D; il gizmo solo con lo strumento attivo (proposto) o a ogni selezione.
3. **C**: la posa automatica resta il primo gesto (proposto); al cambio di modulo con file a mano adattare se le misure coincidono entro 2 cm, altrimenti chiedere (proposto); i moduli esplosi restano nel loro sottocampo (proposto).
4. **D**: il nome della scheda («Impianto» proposto); le condizioni di progetto per le verifiche in diretta prima della simulazione (PVsyst 60/20/-10 °C proposte); ottimizzatori e microinverter subito o dopo.
5. **E**: bifaccialità stimata nel catalogo (marcata) o no; un filtro «policristallino» proprio; lo strumento per aggiornare la lista CEC.
6. **F**: la soglia (300 ms proposta); l'arco anche sulla pianta durante la posa; valori «da aggiornare» barrati o solo grigi.
7. **G**: mirino al passaggio con il tasto del gesto tenuto (proposto) o con il mouse fermo; il predefinito del perno.
8. **Librerie**: nessuna nuova è necessaria; CGAL resta fuori dal programma come oracolo delle prove. Se Daniel preferisse CGAL come dipendenza (A2), la strada è un'estensione C++ con le ruote per Windows e Linux: va deciso prima del compito A.

### Che cosa resta da controllare sul PC

- `View3D.pick` sulle maniglie sottili del gizmo (tema B) e il costo del pick a ogni movimento con il tasto tenuto (tema G): offscreen non c'è la GPU.
- Lo scheletro sopra la 3D vera (tema F): il segnale del primo fotogramma.
- I colori nuovi (frecce del gizmo, stringhe, mirino) sull'ortofoto e sui due temi.
- La UNI 9460, se Daniel la reperisce: confermare o cambiare la pendenza predefinita e la sua fonte.
## Fonti

Consultate il 23/10/2026, salvo dove indicato. Le pagine Zendesk (Aurora, HelioScope, OpenSolar, PVcase) sono state lette dall'API pubblica del centro di assistenza, con la data di aggiornamento dell'articolo.

**Tema A**
- A1 Revit 2025, Roof by footprint: https://help.autodesk.com/view/RVT/2025/ENU/?guid=GUID-4EE804D4-CF0B-46C9-AE61-339B78E4EA8D
- A2 Revit 2016, Defines Slope: https://help.autodesk.com/cloudhelp/2016/ENU/Revit-Model/files/GUID-9712A61C-D82C-4FD0-9355-7280394DCBC3.htm ; frecce di pendenza GUID-C1C203F9-DAF9-450B-BEB1-DE8CC40BA101 ; per estrusione (2020) GUID-E0DB4409-4E19-421F-ABCF-4DDA3A0F9953
- A3 Aurora, SmartRoof Best Practices (02/10/2026): https://help.aurorasolar.com/hc/en-us/articles/360034501014 ; Edit roof mode (17/09/2026): .../21295970356243 ; Draw Roof Face (15/04/2026): .../360015777974 ; Roof Edges API: https://docs.aurorasolar.com/changelog/roof-summary-api-roof-edges
- A4 OpenSolar, Different Edge Types (14/10/2026): https://support.opensolar.com/hc/en-us/articles/4406938905113 ; Manual mode, Quick Roof (01/10/2026): .../13251322728975 ; 2D (04/10/2026): .../13240973769231
- A5 HelioScope, Independent Tilt (10/07/2025): https://help-center.helioscope.com/hc/en-us/articles/30094645765011 ; Residential design (13/06/2026): .../4419969087379
- A6 PV*SOL, 3D design: https://help.valentin-software.com/pvsol/en/pages/3d-design/ ; forum ufficiale, tutorial dello staff: https://forum.valentin-software.com/topic/374-tutorial-pvsol-premium-map-import-and-extrusion-of-3d-objects-for-fast-pv-systems/ (23/02/2016), https://forum.valentin-software.com/topic/452-tutorial-pvsol-premium-%E2%80%93-the-new-3d-features-2017-pv-system-miami-usa/ (02/01/2017), topic 10507 (risposta della hotline sulla L)
- A7 PVsyst, oggetti elementari: https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/object-types/elementary-objects.html ; oggetti composti: .../building-or-composed-objects.html
- A8 DIALux evo, Actions in the roofs tool (26/04/2022): https://evo.support-en.dial.de/support/solutions/articles/9000123943-actions-in-the-roofs-tool
- A9 FreeCAD, Arch Roof (copia ufficiale della wiki): https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/Arch_Roof.md ; sorgente https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Mod/BIM/ArchRoof.py
- A10 Skelion: https://www.skelion.com/ , https://www.skelion.com/en/features.htm ; blog SketchUp: https://www.sketchup.com/blog/en-US/article/skelion-solar-energy-design-plugin-sketchup
- A11 AutoCAD Architecture 2024, ROOFADD: https://help.autodesk.com/cloudhelp/2024/CHT/AutoCAD-Architecture/files/GUID-F287FECD-E0E0-44A8-A921-6BC97DA599A3.htm
- A12 Aichholzer, Alberts, Aurenhammer, Gärtner, «A novel type of skeleton for polygons», JUCS 1(12), 1995, DOI 10.3217/jucs-001-12-0752: https://www.sthu.org/misc/SKRW14/papers/Aichholzer_1995_ANovelTypeOfSkeletonsForPolygons.pdf ; Felkel, Obdržálek, «Straight skeleton implementation», SCCG 1998: https://www.sthu.org/misc/SKRW14/papers/Felkel_1998_StraightSkeletonImplementation.pdf
- A13 CGAL Straight_skeleton_2: https://doc.cgal.org/latest/Straight_skeleton_2/index.html ; licenze dei pacchetti: https://doc.cgal.org/latest/Manual/packages.html , https://www.cgal.org/license.html
- A14 polyskel: https://github.com/Botffy/polyskel (LGPL-3, ultimo commit 12/10/2020); shapely-polyskel: https://github.com/vec2pt/shapely-polyskel (PyPI 0.1.2, 05/01/2025); bpypolyskel: https://github.com/prochitecture/bpypolyskel (GPL-3, ultimo commit 13/03/2026); scikit-geometry: https://scikit-geometry.github.io/scikit-geometry/skeleton.html ; Shapely 2.x note di rilascio: https://shapely.readthedocs.io/en/stable/release/2.x.html ; GEOS NEWS: https://github.com/libgeos/geos/blob/main/NEWS.md
- A15 Pendenze: Isopan Isocop https://mannigroup.b-cdn.net/2021/06/TDS_Isocop_EN.pdf ; Isodomus https://mannigroup.b-cdn.net/2021/04/TDS_Isodomus_EN-rev03.pdf ; ANIT, convegno Isopan 29/11/2023 https://www.anit.it/wp-content/uploads/2023/12/Convegno_ANIT_Isopan_29.11.23_1.pdf ; Pica tegola marsigliese https://pdf.archiexpo.com/pdf/pica/tegola-marsigliese/59835-410696.html e portoghese https://pdf.archiexpo.com/pdf/wienerberger/tegola-portoghese/59835-410665.html (solo dall'anteprima del motore di ricerca: il sito risponde 403); Wierer Coppo Titan su infobuild https://www.infobuild.it/?p=533396 (portale, non scheda); edilizia.com marsigliese (18/09/2026) https://www.edilizia.com/?p=98409 e portoghese (31/08/2026) https://www.edilizia.com/guide/tegole-portoghesi-misure-pendenza-listelli-posa/
- Non letti per il tema A: le pagine HTML dei centri Zendesk (403; usata l'API), wiki.freecad.org (protezione anti-bot; usata la copia su GitHub), archiexpo (403), la guida di Skelion (solo su Scribd), la data di CGAL 6.2.1.

**Tema B**
- B1 DIALux evo, scheda ufficiale dei tasti «Version 2 (DIALux evo 11.1 Patch 1)», 24/05/2023: https://www.dialux.com/fileadmin/user_upload/03_DIALux/DIALux_Shortcuts.pdf ; Knowledge Base: Furniture and Objects (10/02/2023) https://evo.support-en.dial.de/support/solutions/articles/9000123946-actions-in-furniture-and-objects-tool ; Copy and arrange (29/03/2023) .../9000123957-actions-in-the-copy-and-arrange-tool ; Keyboard shortcuts (15/02/2023) .../9000115111-keyboard-shortcuts ; manuale evo (PDF del 2016, copia su Voltimum) https://content.voltimum.com/es/31056/dialux_evo_manual.pdf
- B2 AutoCAD 2026: MOVE https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-47CE7325-84C0-4414-80A3-29DC98392709.htm ; ROTATE GUID-1C265537-FBAC-48D5-B448-B72E777071E5 ; grip «Just Grip It!» https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-DidYouKnow/files/GUID-BBEA1F71-EB16-4D49-80D9-970A6909F508.htm ; polar tracking GUID-7EC3C63D-EA4E-4E65-A676-C3A3627E3F19 ; dynamic input GUID-38EC86CF-D96A-455F-A5DE-2CDA23C28FC4 ; fondamenti https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-OnBoarding/files/ACD_FOUNDATIONS_MAIN6.html
- B3 Revit 2026: Move https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Model/files/GUID-399D3557-93A0-42B7-AF77-E28931823335.htm ; Rotate GUID-9C25D11A-C4D3-4B0A-9793-45E82464840A ; trascinamento GUID-4CB0246D-D7E9-4CEA-BF4C-159269220B53 ; frecce https://help.autodesk.com/cloudhelp/2026/ENU/Revit-Troubleshooting/files/GUID-064B3C67-29FA-49AA-8BB3-E118FB28C3E5.htm ; quote temporanee https://help.autodesk.com/cloudhelp/2026/ENU/Revit-DocumentPresent/files/GUID-575DC14F-5571-4BB5-ACF3-991A8F49758F.htm
- B4 SketchUp: Moving entities https://help.sketchup.com/en/sketchup/moving-entities-around ; basics https://help.sketchup.com/en/sketchup/introducing-drawing-basics-and-concepts ; copie https://help.sketchup.com/en/article/3000092 (letta dall'anteprima: la pagina reindirizza) e https://help.sketchup.com/en/using-measurements-box ; Rotate https://help.sketchup.com/en/sketchup/flipping-mirroring-rotating-and-arrays ; angoli https://help.sketchup.com/en/measuring-angles ; tasti https://help.sketchup.com/en/default-keyboard-shortcuts
- B5 FreeCAD (copia ufficiale della wiki su GitHub): Draft_Move.md, Draft_Rotate.md, Std_TransformManip.md, Release_notes_1.0.md, Placement.md in https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/
- B6 Blender 5.2: move https://docs.blender.org/manual/en/latest/scene_layout/object/editing/transform/move.html ; rotate .../rotate.html ; axis locking .../control/axis_locking.html ; numeric input .../control/numeric_input.html ; precision .../control/precision.html ; gizmo https://docs.blender.org/manual/en/latest/editors/3dview/display/gizmo.html ; keymap https://docs.blender.org/manual/en/latest/editors/preferences/keymap.html
- B7 PVsyst: object positioning https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/construction-tools/object-positioning.html ; global scene tools https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/global-scene-building-tools.html
- B8 Aurora, Keyboard Shortcuts (15/04/2026): https://help.aurorasolar.com/hc/en-us/articles/220132608 ; Obstructions (08/07/2026): .../44272536242067 ; HelioScope, Rotate (09/07/2025): https://help-center.helioscope.com/hc/en-us/articles/36079459077651 ; Keyboard Shortcuts (21/07/2026): .../4419983762067 ; OpenSolar, ground mount (02/10/2026): https://support.opensolar.com/hc/en-us/articles/12354292806159 ; PV*SOL 3D: http://3d-help.valentin-software.com/pvsol/en/html/en/3d/Das_untere_Berarbeitungsmen%C3%BC.htm e .../en/Eingabefeld.htm
- B9 Qt 6.12: View3D https://doc.qt.io/qt-6/qml-qtquick3d-view3d.html ; Model https://doc.qt.io/qt-6/qml-qtquick3d-model.html ; pickResult https://doc.qt.io/qt-6/qml-pickresult.html ; esempio di picking https://doc.qt.io/qt-6/qtquick3d-picking-example.html ; DragHandler https://doc.qt.io/qt-6/qml-qtquick-draghandler.html ; Helpers https://doc.qt.io/qt-6/qtquick3d-helpers-qmlmodule.html ; Qt Design Studio, editor 3D https://doc.qt.io/qtdesignstudio/studio-3d-editor.html ; sorgente dei gizmo di Qt Creator v10.0.2 https://code.qt.io/cgit/qt-creator/qt-creator.git/tree/src/tools/qml2puppet/mockfiles/qt6?h=v10.0.2 e https://code.qt.io/cgit/qt-creator/qt-creator.git/plain/src/tools/qml2puppet/qml2puppet/editor3d/mousearea3d.cpp?h=v10.0.2 (licenza «LicenseRef-Qt-Commercial OR GPL-3.0-only WITH Qt-GPL-exception-1.0»)
- B10 Conner, Snibbe, Herndon, Robbins, Zeleznik, van Dam, «Three-Dimensional Widgets», I3D 1992 (copia dell'autore): https://www.microsoft.com/en-us/research/wp-content/uploads/1992/01/workshop92-widgets.pdf
- Non letti per il tema B: Houde 1992 e gli altri articoli ACM (403), la scheda PDF dei tasti di Revit (403), i video ufficiali DIALux (senza trascrizione), wiki.freecad.org (anti-bot; usata la copia su GitHub).

**Tema C**
- C1 Aurora: Solar Panel Placement in Design Mode (02/09/2026) https://help.aurorasolar.com/hc/en-us/articles/19320214409747 ; Step-by-step guide (01/10/2026) .../21255453781139 ; Keyboard Shortcuts (15/04/2026) .../220132608 ; Design settings (17/06/2026) .../4406930393875 ; Multi-Object Selection (15/04/2026) .../24253418353555 ; Ground Mount (30/07/2026) .../225423788 ; Sales Mode (21/10/2026) .../14993382052371 ; Automatic Adders (13/10/2026) .../19843311586323
- C2 OpenSolar: design in 3D (02/10/2026) https://support.opensolar.com/hc/en-us/articles/13250869794319 ; 2D (04/10/2026) .../13240973769231 ; ground mount and fixed tilt (02/10/2026) .../12354292806159 ; commercial (09/10/2026) .../12354276533647 ; dual tilt (26/08/2026) .../12382458532751 ; optimizers (26/08/2026) .../13279781572623 ; Ada Auto Design (02/09/2026) .../13780099656719
- C3 HelioScope: Residential design (13/06/2026) https://help-center.helioscope.com/hc/en-us/articles/4419969087379 ; Mechanical Layout (23/08/2026) .../4419952640531 ; Field Segment Overview (29/05/2026) .../7835324941203 ; Frames (08/07/2025) .../7835959528339 ; Shift modules (08/07/2025) .../7835642525459 ; Delete individual modules (08/07/2025) .../7835883772563 ; Manually Moving Modules (10/09/2025) .../7835400821267 ; Keyboard Shortcuts (21/07/2026) .../4419983762067
- C4 PV*SOL: graphic coverage https://help.valentin-software.com/pvsol/en/pages/pv-modules/graphic-coverage/ ; 3D: https://3d-help.valentin-software.com/pvsol/de/html/de/Dachvisualisierung.htm , .../en/html/en/Belegungsfeld.htm , .../en/html/en/Modulbelegung.htm , .../de/html/de/3d/Glossar_PV.htm , .../en/html/en/3d/Modulreihen_anlegen.htm , .../en/html/en/3d/Drag_and_Drop.htm , .../en/html/en/3d/Mehrfachauswahl.htm , .../de/html/de/3d/Referenz-Module.htm , .../en/html/en/3d/Modulverschaltung_Seitenmenue.htm ; sistemi di montaggio https://help.valentin-software.com/pvsol/en/pages/3d-design/interface-to-mounting-system-software/
- C5 PVsyst: PV fields https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/object-types/pv-fields.html ; zones of tables .../construction-tools/zones-of-tables.html ; object positioning .../construction-tools/object-positioning.html ; object selection .../construction-tools/object-selection.html ; mechanical definition https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-layout/mechanical-definition.html
- C6 Sunny Design: https://manuals.sma.de/SDesign/en-US/14363985419.html , .../14363989771.html , .../14363987595.html ; note di rilascio https://www.sma.de/en/products/apps-software/sunny-design
- C7 SolarEdge Designer: https://marketing.solaredge.com/solaredge-designer-0 (08/2022), https://marketing.solaredge.com/solaredge-designer-0-8 (07/2021); la scheda dei tasti (knowledge-center) risponde 403: solo dall'anteprima
- C8 PVcase Roof Mount: Layout settings (23/07/2026) https://help.pvcase.com/hc/en-us/articles/43343107921555 ; Spacing .../43345035151635 ; Roof builder .../43257651953299 ; Right-click actions .../35594541435027 ; Common questions .../35602533673875
- C9 Skelion: https://www.skelion.com/en/features.htm , https://skelion.com/en/training.htm (video senza trascrizione)
- Non letti per il tema C: HTML Zendesk (403, usata l'API), SolarEdge PDF (403), manuale SMA PDF (binario), pagine v7 di PVsyst (solo JavaScript), guida di Skelion (Scribd).

**Tema D**
- D1 PVsyst: project design https://www.pvsyst.com/help/project-design/index.html ; System https://www.pvsyst.com/help/project-design/grid-connected-system-definition/index.html ; sub-arrays .../sub-arrays.html ; multi-MPPT .../multi-mppt-inverters/index.html ; voltage sizing .../array-voltage-sizing-according-to-inverter.html ; design temperatures .../design-temperatures.html ; inverter sizing .../inverter-array-sizing.html ; Module Layout https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-layout/index.html , .../electrical-definition.html , .../procedures-in-the-dialog.html ; v7 https://www.pvsyst.com/help-pvsyst7/modulelayout_electrical.htm e .../modulelayout_automatic.htm ; mismatch https://www.pvsyst.com/help/project-design/array-and-system-losses/array-mismatch-losses/index.html
- D2 Aurora: Stringing and Connecting (30/09/2026) https://help.aurorasolar.com/hc/en-us/articles/13139582090131 ; Step-by-step (01/10/2026) .../21255453781139 ; Multi-input MLPE (15/04/2026) .../8589759844627 ; Instant Plan Sets (27/01/2026) .../33543611295379 ; Inverter Efficiency Curves .../115001389928
- D3 HelioScope: Overview (15/08/2025) https://help-center.helioscope.com/hc/en-us/articles/4417518779667 ; Wiring Zones (09/07/2025) .../8198405358227 ; Electrical Design (21/10/2026) .../4419953067411 ; Stringing (09/07/2025) .../8198326521491 ; Unstrung modules .../8536897333395
- D4 OpenSolar: Stringing, Micro-Inverters and Power Optimizers (22/10/2026) https://support.opensolar.com/hc/en-us/articles/4406931180313 ; design in 3D (02/10/2026) .../13250869794319 ; Inverter sizing and stringing recommendations (26/08/2026) .../12382487281935
- D5 PV*SOL: Inverters, Configuration https://help.valentin-software.com/pvsol/en/pages/inverters/configuration/ ; Configuration check .../configuration-check/ ; Polystring .../polystring-connection/ ; Plans https://help.valentin-software.com/pvsol/en/pages/plans-and-parts-list/ ; FAQ https://help.valentin-software.com/pvsol/en/faq/
- D6 SolarEdge Designer: https://marketing.solaredge.com/solaredge-designer-0-20 (02/2022); le pagine del knowledge-center rispondono 403
- D7 Sunny Design: https://manuals.sma.de/SDesign/en-US/14568603275.html , .../14362187659.html , .../14448218507.html , .../14449198731.html , .../14449205259.html , .../14365264011.html , .../14317464203.html , .../14365261835.html , .../14518690699.html , .../14518697227.html , .../14518692875.html , .../14398229131.html , .../14518695051.html , .../14561189643.html
- D8 Solarius PV: https://www.acca.it/software-fotovoltaico ; scheda https://download.acca.it/Files/Scheda/Solarius-PV.pdf (06/07/2021)
- Non letti per il tema D: HTML Zendesk (403, usata l'API), solaredge.com e knowledge-center (403), la guida 3D di PV*SOL (404, in revisione), pagine dinamiche di acca.it.

**Tema E**
- E1 SAM, CEC Modules.csv (letto il 23/10/2026): https://raw.githubusercontent.com/NREL/SAM/develop/deploy/libraries/CEC%20Modules.csv ; pvlib retrieve_sam https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.retrieve_sam.html ; copia 2019 in pvlib https://raw.githubusercontent.com/pvlib/pvlib-python/main/pvlib/data/sam-library-cec-modules-2019-03-05.csv
- E2 CEC Solar Equipment Lists: https://solarequipment.energy.ca.gov/Home/PVModuleList (xlsx scaricato, dati al 21/10/2026); https://www.energy.ca.gov/programs-and-topics/programs/solar-equipment-lists
- E3 PVsyst: modules in the database https://www.pvsyst.com/help/component-database/photovoltaics-modules/modules-in-the-database/index.html ; basic data .../pv-modules-main-interface/pv-modules-basic-data/index.html ; main interface .../pv-modules-main-interface/index.html ; sizes and technology .../pv-modules-sizes-and-technology.html ; bifacial systems https://www.pvsyst.com/help/project-design/bifacial-systems/index.html ; favorites https://www.pvsyst.com/help/component-database/favorites.html ; .PAN di prova in pvlib https://raw.githubusercontent.com/pvlib/pvlib-python/main/tests/data/ET-M772BH550GL.PAN
- E4 PV*SOL: PV modules https://help.valentin-software.com/pvsol/en/databases/components/pv-modules/ ; bifacial modules https://help.valentin-software.com/pvsol/en/calculation/pv-modules/bifacial-modules/ ; Aurora, Bifacial modules https://help.aurorasolar.com/hc/en-us/articles/37506465565203 e database .../6964101736083 (solo dall'anteprima: 403); HelioScope .../41739863126163 (anteprima); OpenSolar .../12354293982351 (anteprima); ENF Solar https://www.enfsolar.com/pv/panel (403) e il comunicato https://www.pv-magazine.com/press-releases/enf-launches-advanced-global-solar-panel-directory_10009518/
- E5 pvlib: calcparams_cec https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_cec.html ; fit_cec_sam https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.ivtools.sdm.fit_cec_sam.html ; infinite_sheds https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.bifacial.infinite_sheds.get_irradiance.html
- E6 IEC 61215-1:2021 https://webstore.iec.ch/en/publication/61345 ; IEC 61853-1 https://webstore.iec.ch/en/publication/6035 (solo le pagine pubbliche del negozio)
- E7 Qt: QSortFilterProxyModel https://doc.qt.io/qt-6/qsortfilterproxymodel.html ; QCompleter https://doc.qt.io/qt-6/qcompleter.html ; GNOME HIG search https://developer.gnome.org/hig/patterns/nav/search.html e drop-downs https://developer.gnome.org/hig/patterns/controls/drop-downs.html ; KDE HIG https://develop.kde.org/hig/getting_input/ ; WinUI list filtering (15/07/2026) https://learn.microsoft.com/windows/apps/develop/ui/controls/listview-filtering
- E8 pv magazine, studio su 842 moduli bifacciali (24/07/2025): https://www.pv-magazine.com/2025/07/24/parameter-analysis-of-842-bifacial-solar-modules-from-236-manufacturers/ (l'articolo di RSER è a pagamento)
- Non letti per il tema E: enfsolar.com (403), HTML Zendesk (403), l'aiuto di SAM (rete), l'elenco delle tecnologie di PVsyst (non enumerato nelle pagine lette), il database di RSER (a pagamento).

**Tema F**
- F1 NN/g, Skeleton Screens 101 (Tankala, 04/06/2023, rivisto 02/09/2026): https://www.nngroup.com/articles/skeleton-screens/ ; Progress Indicators (Sherwin, 26/10/2014): https://www.nngroup.com/articles/progress-indicators/ ; Wroblewski, Avoid The Spinner (17/09/2013): https://www.lukew.com/ff/entry.asp?1797
- F2 Material 3, Progress indicators (letto dall'anteprima: la pagina è solo JavaScript): https://m3.material.io/components/progress-indicators/guidelines ; Apple HIG, Progress indicators (12/09/2023) https://developer.apple.com/design/human-interface-guidelines/progress-indicators e Loading (09/06/2025) https://developer.apple.com/design/human-interface-guidelines/loading ; WinUI, Guidelines for progress controls (08/07/2026) https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/progress-controls ; Fluent 2, Skeleton https://fluent2.microsoft.design/components/web/react/core/skeleton/usage ; KDE HIG https://develop.kde.org/hig/status_changes/ e Kirigami https://develop.kde.org/docs/getting-started/kirigami/components-progressbars/ ; GNOME HIG spinners https://developer.gnome.org/hig/patterns/feedback/spinners.html , progress bars https://developer.gnome.org/hig/patterns/feedback/progress-bars.html , placeholders https://developer.gnome.org/hig/patterns/feedback/placeholders.html
- F3 Qt 6.12: QProgressBar https://doc.qt.io/qt-6/qprogressbar.html ; QProgressDialog https://doc.qt.io/qt-6/qprogressdialog.html ; QMovie https://doc.qt.io/qt-6/qmovie.html ; QGraphicsOpacityEffect https://doc.qt.io/qt-6/qgraphicsopacityeffect.html ; QStackedLayout https://doc.qt.io/qt-6/qstackedlayout.html ; QQuickWidget https://doc.qt.io/qt-6/qquickwidget.html ; Loader https://doc.qt.io/qt-6/qml-qtquick-loader.html ; Component https://doc.qt.io/qt-6/qml-qtqml-component.html ; BusyIndicator https://doc.qt.io/qt-6/qml-qtquick-controls-busyindicator.html ; QWidget https://doc.qt.io/qt-6/qwidget.html ; QStatusBar https://doc.qt.io/qt-6/qstatusbar.html ; QTimer https://doc.qt.io/qt-6/qtimer.html ; QGraphicsView https://doc.qt.io/qt-6/qgraphicsview.html
- F4 Excel, Stale value formatting: https://support.microsoft.com/en-us/office/stale-value-formatting-4b5c63c3-5dc7-4e9b-8e24-88bed1987dbd ; VS Code API https://code.visualstudio.com/api/references/vscode-api e UX guidelines https://code.visualstudio.com/api/ux-guidelines/notifications ; JetBrains https://plugins.jetbrains.com/docs/intellij/progress-bar.html e https://plugins.jetbrains.com/docs/intellij/loader.html ; FreeCAD (copia della wiki) Std_Refresh.md, Tree_view.md, Preferences_Editor.md in https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/ ; AutoCAD REGEN 2026 https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-CC98095F-B4C4-4B25-9097-A7B6EF4260B2.htm ; Revit 2024 barra di stato https://help.autodesk.com/cloudhelp/2024/ENU/Revit-GetStarted/files/GUID-23CCC541-4E99-4BCF-B1BA-3271F66477D0.htm ; Blender status bar https://docs.blender.org/manual/en/latest/interface/window_system/status_bar.html ; QGIS GUI https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_gui.html , map view https://docs.qgis.org/latest/en/docs/user_manual/map_views/map_view.html , options https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_configuration.html
- F5 PVsyst simulation https://www.pvsyst.com/help/project-design/simulation/index.html e tutorial v7 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-7/pvsyst-tutorial-v7-standalone-en.pdf ; DIALux evo shortcuts PDF (vedi B1) e Start calculation (17/02/2023) https://evo.support-en.dial.de/support/solutions/articles/9000115434-start-calculation ; Aurora API https://docs.aurorasolar.com/reference/performance-simulation ; HelioScope Simulation and Report (anteprima) https://help-center.helioscope.com/hc/en-us/articles/4419967126931
- F6 RAIL (10/06/2020) https://web.dev/articles/rail ; WCAG 2.1 SC 2.3.3 https://www.w3.org/WAI/WCAG21/Understanding/animation-from-interactions.html e SC 2.2.2 https://www.w3.org/WAI/WCAG21/Understanding/pause-stop-hide.html ; soglia di Doherty solo da fonte secondaria https://lawsofux.com/doherty-threshold/
- Non letti per il tema F: uxdesign.cc (403), m3.material.io (JavaScript), la pagina Shimmer di Microsoft (404), wiki.freecad.org (anti-bot), HTML di HelioScope e Aurora (403), Doherty e Thadani 1982 (solo scansione).

**Tema G**
- G1 FreeCAD (copia della wiki su GitHub): Preferences_Editor.md e Release_notes_1.0.md in https://raw.githubusercontent.com/FreeCAD/FreeCAD-documentation/main/wiki/ ; sorgente https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Gui/View3DInventorViewer.cpp , https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Gui/Navigation/NavigationStyle.h , https://raw.githubusercontent.com/FreeCAD/FreeCAD/main/src/Gui/PreferencePages/DlgSettingsNavigation.ui (LGPL-2.1-or-later)
- G2 Revit: About Navigating Views (2023) https://help.autodesk.com/cloudhelp/2023/ENU/Revit-DocumentPresent/files/GUID-A3F4A7B5-225F-46D2-99D3-4C9771282DCA.htm ; Define the Center of the Model View (2023) GUID-FED6E969-4E3A-4540-B765-F7961C07AEBC ; Orbit Tool (2018) https://help.autodesk.com/cloudhelp/2018/ENU/Revit-DocumentPresent/files/GUID-3B52C5FC-D1C6-48E6-B847-6C1E566058C0.htm
- G3 AutoCAD: 3DORBIT (2026) https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-Core/files/GUID-85CE824C-0AF4-4890-8487-ADBC92BF08F1.htm ; ORBITAUTOTARGET (2015) https://help.autodesk.com/cloudhelp/2015/ENU/AutoCAD-Core/files/GUID-4E7E1156-CADF-410C-BDD0-C209FDD8953E.htm ; 3D Orbit shortcut menu (2023) GUID-3677ED1F-112A-45E5-A7BD-59EFDE849A34
- G4 SketchUp, Viewing a model: https://help.sketchup.com/en/sketchup/viewing-model
- G5 Blender 5.2: navigation preferences https://docs.blender.org/manual/en/latest/editors/preferences/navigation.html ; navigation https://docs.blender.org/manual/en/latest/editors/3dview/navigate/navigation.html ; 3D cursor https://docs.blender.org/manual/en/latest/editors/3dview/3d_cursor.html
- G6 DIALux evo KB: Keyboard shortcuts (15/02/2023) https://evo.support-en.dial.de/support/solutions/articles/9000115111-keyboard-shortcuts ; Views (26/05/2021) .../9000115077-user-views
- G7 Rhino 8: RotateView https://docs.mcneel.com/rhino/8/help/en-us/commands/rotateview.htm ; Options View https://docs.mcneel.com/rhino/8/help/en-us/options/view.htm ; Zoom https://docs.mcneel.com/rhino/8/help/en-us/commands/zoom.htm ; Camera https://docs.mcneel.com/rhino/8/help/en-us/commands/camera.htm
- G8 Fusion shortcuts https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-F0491540-0324-470A-B651-2238D0EFAC30 e navigation bar https://help.autodesk.com/cloudhelp/ENU/Fusion-GetStarted/files/GS-NAVIGATION-BAR.htm ; Onshape https://cad.onshape.com/help/Content/View/view_navigation_and_the_view_cube.htm ; Unity https://docs.unity3d.com/Manual/SceneViewNavigation.html ; Unreal https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/UnrealEd/ULevelEditorViewportSettings e https://dev.epicgames.com/documentation/en-us/unreal-engine/viewport-controls-in-unreal-engine ; Godot https://docs.godotengine.org/en/stable/classes/class_editorsettings.html
- G9 Fitzmaurice, Matejka, Mordatch, Khan, Kurtenbach, «Safe 3D Navigation», I3D 2008 (Autodesk Research): https://research.autodesk.com/app/uploads/2023/03/safe-3d-navigation.pdf_recHpo5niNlpDtQQu.pdf ; NN/g, Visibility of System Status (03/06/2018) https://www.nngroup.com/articles/visibility-system-status/
- Non letti per il tema G: wiki.freecad.org (anti-bot), la scheda PDF dei tasti DIALux (testo non estraibile in questa lettura), le pagine web di Fusion (404), Fusion «Set Orbit Center» (solo forum).
