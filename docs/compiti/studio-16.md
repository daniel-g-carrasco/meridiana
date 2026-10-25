# Compito per una sessione cloud: lo studio 16, modellazione

23/10/2026. Uno studio, non codice del programma: le alternative per ogni richiesta di Daniel qui sotto, con le prove dove decidono, i voti e una raccomandazione. Le scelte le fa Daniel; poi si scrivono i compiti per farle.

## Come lavorare

- Prima di tutto `git config user.name "Daniel Grasso"` e `git config user.email code@danielgrasso.com`; poi leggi `CLAUDE.md`, `docs/progetto.md` e gli studi che ogni tema indica.
- Ramo `studio-16` da `lavoro`; richiesta di unione **in bozza** verso `lavoro`, con i temi come caselle; ogni tema finito è un commit, spinto subito.
- Il risultato:
  - `docs/studio/16-modellazione.md`, in italiano, come gli altri studi: frasi brevi, elenchi, [V] per quello che hai verificato (dici come) e [I] per quello che deduci, le fonti con l'URL e la data in fondo;
  - le prove in `docs/studio/16-prove/`, piccole e lanciabili, mai in `src/`.
- **Il metodo, per ogni tema:**
  1. cosa chiede Daniel, con le sue parole;
  2. che cosa fa oggi Meridiana, letto nel codice;
  3. come lo fanno i programmi di riferimento, dalla loro documentazione ufficiale: DIALux evo, PVsyst, Aurora Solar, OpenSolar, HelioScope, PV*SOL, SketchUp con Skelion, Revit, AutoCAD, FreeCAD (`docs/studio/15-freecad-riferimento.md`), e altri se servono;
  4. **tutte** le famiglie di soluzioni, non solo la prima: pro e contro tecnici, rischi, fatica in giorni, voti da 1 a 5;
  5. una prova quando la scelta dipende da un fatto verificabile (un algoritmo, una libreria, una licenza, un costo in Qt);
  6. la raccomandazione, e quello che resta da decidere a Daniel.
- **Librerie:** solo con licenza compatibile con la GPL-3.0-or-later; ogni libreria nuova è una decisione di Daniel, quindi va proposta, non aggiunta.
- **Norme:** mai a memoria. L'archivio delle norme è sul PC di Daniel e la UNI 9460 (coperture discontinue) non c'è. Per le pendenze usa le schede tecniche pubbliche dei produttori, dicendolo.
- **Siti chiusi:** la documentazione dietro login, abbonamento o CAPTCHA non si aggira. Usa le pagine pubbliche, i video ufficiali con le loro trascrizioni, gli archivi web, e scrivi che cosa non sei riuscito a leggere.
- Se la conversazione viene riassunta, rileggi questo file e la richiesta di unione.
- **Alla fine**, un riassunto in italiano per Daniel:
  - per ogni tema, la raccomandazione in due righe;
  - le domande a cui solo lui può rispondere.

## I temi

### A. Tetti a falde su piante qualsiasi
Daniel:
- «quando l'edificio non ha una geometria rettangolare, e c'è un tetto a falde, il tutto si sballa completamente»;
- «sarebbe buona la possibilità di poter disegnare delle geometrie particolari di tetti a falda disegnandone il colmo e dandogli altezza (con default di inclinazione come quello che di solito si usa in costruzione). Oppure (o in aggiunta) mettere a disposizione dei template di edificio già realizzati, tipo edifici ad L, quadrati, con forma trapezoidale, ecc».

Oggi `roofs.py` costruisce i tetti a due falde e a padiglione sul rettangolo minimo che contiene la pianta: su una L il tetto non segue la forma.

Da studiare:
- lo scheletro dritto (straight skeleton) per i padiglioni su poligoni qualsiasi, e le due falde con le testate; gli algoritmi, le implementazioni in Python e le loro licenze; una prova su L, T, U, trapezio e pianta con un lato corto storto;
- la falda definita lato per lato, come in Revit e in SketchUp;
- il colmo disegnato con la sua altezza, e una pendenza predefinita giustificata dalle schede dei produttori;
- i modelli di edificio parametrici (rettangolo, L, T, U, trapezio, cortile) con le loro quote;
- che cosa cambia per le falde, la posa, le ombre, il 3D e il file `.meridiana` (versione e migrazione).

### B. Spostare e ruotare, nel 3D e in pianta
Daniel: «la vista 3d non permette di spostare oggetti. Sarebbe buono che fosse possibile farlo alla stregua di Dialux EVO: si mette a disposizione strumento sposta e ruota, e quando si sposta escono fuori i vettori x / y / z che a seconda di dove si preme permettono di spostare. Da ragionarsi modi per farlo in modo preciso con suggerimenti / snapping / step o dichiarare uno spostamento di un numero preciso come in CAD se si sta digitando. Se si preme sulla rotazione stessa cosa più o meno, compaiono le maniglie circolari».

Da studiare:
- le maniglie di DIALux evo, e le famiglie analoghe: gizmo a frecce e anelli, punto base con il secondo punto come in AutoCAD, input dinamico digitato, maniglie sugli spigoli;
- la precisione: agganci, passi, valori digitati, angoli a scatti, copia mentre si sposta;
- come farlo in Qt Quick 3D (picking, trascinamento vincolato a un asse, maniglie della stessa grandezza sullo schermo) e in pianta (`ui/plan.py`, `snapping.py`, `sides.py`);
- l'annullamento, e la stessa cosa sulle falde, sugli ostacoli e sui sottocampi.

### C. Posa manuale dei moduli, file ed esplosione
Daniel:
- «il posizionamento dei pannelli fotovoltaici non è il massimo. Al momento si disegna l'area e poi l'app la popola in automatico. Non è possibile invece disegnare direttamente i pannelli con passo selezionato e tutto il resto?»;
- «una volta disegnati i pannelli, avere la possibilità di selezionare e spostare le singole file, e di "esploderle" e poter selezionare e spostare i singoli pannelli».

Da studiare:
- come lo fanno Aurora, OpenSolar, HelioScope, PV*SOL, PVsyst e Skelion: righe disegnate, matrici, posa a mano, conversione da automatico a manuale;
- il modello dei dati (`model.py`, `layout.py`): posa automatica con correzioni, oppure moduli espliciti, e che cosa si perde e si guadagna in ognuno;
- l'effetto su stringhe, verifiche dei Vigili del Fuoco, esclusioni, ombre, varianti e annullamento.

### D. Inverter e stringhe
Daniel: «Non vedo un editor di stringatura e da nessuna parte la possibilità di scegliere inverter».

Oggi:
- l'inverter si sceglie nella pagina Producibilità, nel gruppo «Inverter» (catalogo, dimensionamento automatico, numero, rapporto DC/AC), dove Daniel non l'ha trovato;
- le stringhe sono proposte da sole (`energy/stringing.py`: `suggest`, `assign` a serpentina) e disegnate in pianta, senza modifica a mano.

Da studiare:
- dove deve stare la progettazione elettrica perché la si trovi: una scheda «Impianto», un gruppo delle Proprietà del sottocampo, un pannello;
- più inverter e i loro MPPT;
- un editor delle stringhe come in PVsyst, Aurora e HelioScope: automatico, poi a mano con clic o trascinamento sui moduli, colori per stringa, verifiche CEI 64-8/7 in diretta (`rules.py`, `checks.py`).

### E. Scelta dei moduli: i filtri del catalogo
Daniel: «La scelta dei pannelli non è molto semplice. Sarebbe buono avere dei filtri fatti meglio che almeno permettano di distinguere per monocristallino / policristallino, ecc, e tra mono e bifacciale (anche se so che al giorno d'oggi si commercializzano praticamente solo i bifacciali)».

Da studiare:
- quali campi hanno davvero i dati del catalogo (`catalog/`: la lista CEC, le schede lette, i file .PAN): tecnologia, tipo di cella (PERC, TOPCon, HJT, IBC), bifacciale e bifaccialità, potenza, dimensioni, efficienza, marca, data;
- che cosa manca e come ricavarlo;
- i filtri e l'interfaccia della finestra del catalogo (`ui/catalog_dialog.py`).

### F. Attese visibili
Daniel: «non è possibile mettere delle sorte di placeholder e caricamenti laddove sta renderizzando qualcosa?».

Da studiare:
- dove la finestra aspetta: avvio del 3D, posa, energia, sfondo della pianta, catalogo, PVGIS, relazione PDF; le misure sono in `docs/studio/12-revisione-ux-prestazioni.md` e in `docs/progetto.md` (appendice A, 23/10/2026);
- segnaposti a scheletro, indicatori sopra la zona che aspetta, barra di stato, valori vecchi segnati come «da aggiornare»;
- come farli in Qt senza costare tempo.

### G. Il perno della vista 3D
Daniel: «in vista 3d ci si sposta con ctrl all'interno del disegno, quando non si preme la vista si ancora su un punto centrale, che ci sta, ma sarebbe buono vedere un mirino che permetta di capire a cosa è ancorata la vista».

Oggi la fase 2 mostra una pallina sul perno durante l'orbita (`camera.py`, `ui/view3d.py`, `ui/qml/Scene.qml`). Da studiare:
- un mirino sempre visibile, oppure al passaggio, oppure solo durante l'orbita;
- come lo fanno FreeCAD, Revit, SketchUp, Blender e DIALux evo.

## Il piano alla fine dello studio

- I temi in ordine di valore per Daniel e di fatica.
- Per ogni raccomandazione, la bozza di un compito per una sessione cloud in `docs/compiti/` (passi, commit, test), da lanciare dopo la sua decisione.
