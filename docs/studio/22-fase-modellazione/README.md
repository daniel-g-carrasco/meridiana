# Studio 22: la fase Modellazione

30/10/2026, agente «Fable X» (sigla X, ripresa R07). Daniel, dopo una prova sul Duomo di Milano, ha chiesto sei cose
(R274, R275, R276, R277, R281, R282 in `docs/richieste.md`): una **prima fase dedicata solo alla modellazione**, con
strumenti suoi; la posa dei pannelli spostata nella fase **Impianto**, in ordine pannelli, inverter, accumulo; la
falda a mano con angolo, quota o punto di colmo, punto di arrivo e scambio gronda/colmo; il tetto ipotetico dal solo
colmo; le lunghezze dei lati modificabili cliccando l'etichetta in pianta, con il numero del lato visibile; la
pensilina che disegna solo la struttura, con la posa dei moduli semplificata dopo; le finestrelle di modellazione con
un'anteprima 3D semplice e cliccabile sui lati.

Questo studio non tocca il codice: dà lo stato di oggi con le foto, come fanno i programmi del settore, la proposta
con i bozzetti, che cosa cambia nei dati, i rischi, i lotti e le domande per Daniel. I bozzetti sono generati da
`bozzetti.py` (SVG + PNG, Qt offscreen); le foto di oggi sono dei widget veri, offscreen, con il look di Meridiana.

**Legenda.** [V] letto nel codice o nella documentazione citata; [V, foto] widget vero fotografato offscreen;
[I] dedotto; [D] proposta da confermare. Costi in giorni di lavoro di una sessione, test compresi.

## 1. Lo stato di oggi [V]

### 1.1 Le fasi e le barre

`src/meridiana/phases.py` descrive sei fasi, «luoghi, non tappe» (design 2.1): 1 Modello, 2 Impianto,
3 Producibilità, 4 Consumi, 5 Bilancio ed economia, 6 Relazione; Ctrl+1…6, Ctrl+Tab. La barra di **Modello** ha
quattro gruppi (R205): Modifica (Seleziona V, Sposta M, Ruota), Disegna (Edificio B, Modello…, Pensilina…, Falda P,
Esclusione X), **Posa** (Sottocampo S, Fila L, Est-ovest, **Posa** come pulsante principale, Svuota), Precisione
(Misura D, Squadra Q, Rettangolo R). La barra di **Impianto** ha Inverter (Catalogo, Dimensiona), Accumulo
(Configura), Stringhe (Proponi, Completa, Disegna, Ricomincia); il suo pannello destro è `PlantInspector`
(gli inverter, C10), non le proprietà. È esattamente l'incoerenza che Daniel segnala in R277: i pannelli si posano in
Modello, l'impianto comincia dagli inverter.

Bozzetto del prima e dopo: `fasi-e-barre.png`.

### 1.2 La falda a mano (R274)

`window.py` 2335-2352: lo strumento Falda (P) disegna un anello dentro un edificio; il tetto diventa di tipo «free» e
l'anello entra in `roof.free_pitches` con `eave_side = 0`, `eave = altezza di gronda dell'edificio`, `tilt` proposto
dal manto (35 % tegole, `roofs.proposed_tilt`). **Dopo il disegno non c'è alcun campo per cambiare inclinazione,
gronda o quota di una falda libera**: `properties._roof_group` tratta solo `mono`, `gable`, `hip`, `flat`; per
`free` mostra il solo tipo («Falde disegnate a mano»); in `window.py` nessun punto scrive `free_pitches[i]` dopo la
creazione (verificato con grep, non provato a mano). Il lato di gronda è sempre il primo disegnato. Daniel ha
ragione su tutti e quattro i punti: niente angolo, niente quota di colmo, niente punto di arrivo, niente scambio
gronda/colmo.

Per i tetti `gable` e `hip` invece c'è già molto (formato 9, task 16a): ogni lato è gronda o testata, con «Scegli
sulla pianta»; la **quota del colmo** scritta dà la pendenza (`ridge_written`, rifiutata sotto la gronda); lo
scheletro dritto (`skeleton.py`, verificato sulle 306 piante CGAL) fa colmi, displuvi e compluvi su qualsiasi pianta.
Foto: `oggi-proprieta-edificio.png` (gruppo Tetto e gruppo Lati di un capannone a L).

### 1.3 I lati (R276)

La pianta scrive già la lunghezza di ogni lato dell'oggetto selezionato, al centro del lato, fuori dall'anello
(`plan._draw_sides`), e il **doppio clic** sul lato apre un `QInputDialog` con la nuova lunghezza
(`window._side_clicked`, `sides.stretch`). Il **numero del lato non compare** in pianta; le Proprietà (gruppo Lati)
dicono «Lato 1 … Lato 6» e il gruppo Tetto dice «Lato 2: testata» senza che si veda quale sia. I dialoghi Modello e
Pensilina numerano i lati nella loro anteprima 2D (`template_dialog.Outline`), ma la pianta no. Quindi R276 è per
metà fatto (misura e modifica), per metà no (numero, un clic, pillola scrivibile).

### 1.4 La pensilina (R281)

`ui/canopy_dialog.py` + `canopies.py`: sette campi (posti per fila, disposizione a una o due file, larghezza posto,
profondità, altezza minima del piano di posa, pendenza, rotazione), anteprima 2D del contorno, nota «Crea superfici di
posa e moduli; pilastri, travi, sagoma libera e verifiche strutturali non sono modellati». Il risultato sono **uno o
due sottocampi** `mounting='canopy'` con un `SupportPlane` e `filled=True`: i moduli compaiono subito, la struttura
non esiste (in 3D e in IFC i piani galleggiano). Foto: `oggi-pensilina.png`. Daniel: «ha un sacco di opzioni e si
intuisce male a cosa servono».

### 1.5 Le finestrelle (R282)

Modello e Pensilina hanno un'anteprima **2D** (pianta, lati numerati) non cliccabile. La falda non ha finestra.
Foto: `oggi-modello-edificio.png`.

## 2. Come fanno gli altri (solo ciò che serve)

La tabella A.3 dello studio 16 (fonti con URL e data in fondo a quel file) resta valida; qui solo i punti che
decidono le scelte di questo studio, con le verifiche fatte oggi.

| Programma | Che cosa insegna qui | Fonte |
|---|---|---|
| Revit, «Roof by footprint» | Il tetto nasce dal contorno più un attributo per lato: «To change the slope definition of a line, select the line and, on the Properties palette, click Defines Roof Slope. You can then change the slope value»; un simbolo accanto al lato dice che definisce pendenza. È il modello che Meridiana ha già (gronda/testata): il colmo di R275 è un altro modo di scriverlo | help.autodesk.com, Revit LT 2020, «Create a Roof by Footprint» (letta 30/10/2026) |
| Easy-PV Quick Roof (UK) | Le misure si scrivono **sul modello**: «The dimensions can also be adjusted directly from the model by clicking on the corners and inputting the length»; maniglie per spezzare un lato; «Input roof dimensions: width, height, pitch and orientation». Conferma la direzione di R276 | help.easy-pv.co.uk, «Introduction to Quick Roof design mode» (letta 30/10/2026) |
| Aurora | Spigoli tipizzati e colorati (gronda, colmo, displuvio, compluvio, testata), pendenza per faccia, facce interne dedotte (studio 16). Per i parcheggi: la pensilina è una «ground mount» con il tasto P; «mounting posts aren't shown», si consiglia un albero senza chioma come ripiego per l'ombra del palo | API pubblica del centro assistenza, articolo 225423788 «How to Design a Ground Mount System», aggiornato 30/07/2026 (letto 30/10/2026) |
| OpenSolar Quick Roof | Spilli sugli angoli, «Complete the roof shape to generate the structure», spigoli a colori; i moduli si orientano da soli verso la gronda (studio 16) | studio 16, A.3 |
| PV\*SOL premium | Linea di colmo disegnata per il padiglione; le piante non rettangolari si compongono a blocchi; nessun oggetto pensilina nell'indice della guida 3D (oggetti: camini, abbaini, alberi, case) | 3d-help.valentin-software.com, «3D Planning» (letta 30/10/2026); studio 16 |
| PVsyst | Oggetti elementari («House + 2-sided roof», «2-sided roof + gables», «4-sided roof») quotati nelle viste ortogonali; la scena 3D è una tappa separata dalla definizione del sistema | studio 16, A.3 (la pagina della guida PVsyst cercata oggi dà 404) |
| DIALux evo | Nove tipi di tetto adattati al contorno del piano, pendenze calcolate da sole | studio 16, A.3 |

Che cosa ne ricaviamo [I]: (1) tutti separano il **modello** (contorno, falde, ostacoli) dalla **posa**: Revit e
DIALux non posano affatto; PVsyst e PV\*SOL hanno la scena 3D come tappa a sé; Aurora e OpenSolar «completano il tetto»
prima di posare. La fase Modellazione di Daniel segue la pratica. (2) Il colmo disegnato esiste in PV\*SOL (solo
padiglione) e Aurora (spigolo «ridge»), mai da solo su piante a L: lì serve lo scheletro, che Meridiana ha. (3) Le
misure scritte sul disegno (Easy-PV, OpenSolar) sono lo standard; la pillola col numero manca a tutti, ed è utile
perché le Proprietà di Meridiana parlano per numero. (4) Nessuno dei programmi FV modella la struttura della pensilina
(Aurora lo dice apertamente): disegnarla è un vantaggio per la relazione, il 3D e l'IFC, purché resti semplice
(pilastri, trave, piano).

## 3. La proposta

### 3.1 Le fasi [D]

Restano sei, stessi tasti; cambia il nome della prima e il contenuto delle prime due (`fasi-e-barre.png`):

| N. | Fase | Che cosa si fa | Pannello destro |
|---|---|---|---|
| 1 | **Modellazione** | sito, edifici, tetti, pensiline (strutture), ostacoli, misure | Proprietà (come oggi) |
| 2 | **Impianto** | **Pannelli** (sottocampi, file, posa, svuota, posa su pensilina) → **Inverter** → **Accumulo** → Stringhe | Proprietà dell'oggetto selezionato quando c'è una selezione in pianta; pagina Impianto (inverter, accumulo) altrimenti (vedi domanda 2) |
| 3-6 | come oggi | | |

In `phases.py` il gruppo `layout` esce da `model` ed entra per primo in `plant` come `modules`; `inspector` di
`plant` diventa «properties+plant». Le tre domande per Meridio di Modellazione cambiano («Il tetto è plausibile?»,
«Manca qualche ostacolo per le ombre?», «Le quote sono coerenti con la foto?»); quelle della posa passano a Impianto.
Il tour iniziale (R06) e la guida vanno riletti dove dicono «posa in Modello».

### 3.2 La barra di Modellazione [D]

| Gruppo | Comandi (tasto) | Note |
|---|---|---|
| Modifica | Seleziona (V), Sposta (M), Ruota | come oggi |
| Edifici | Edificio (B), Da modello… (E), **Pensilina…** (T) | la pensilina è un edificio «leggero»: struttura sola |
| Tetto | Falda (P), **Colmo** (C), Tipo… | «Tipo…» seleziona l'edificio e apre il gruppo Tetto delle proprietà |
| Ostacoli | Esclusione (X), **Oggetto 3D** (O) | gli oggetti 3D (alberi, auto, persone) sono il lavoro affidato a Kimi il 30/10 |
| Precisione | Misura (D), Squadra (Q), Rettangolo (R), agganci, orto | come oggi |

C, E, O, T sono liberi in `shortcuts.py` (usati: A B D F L M N P Q R S V W X). Nessun pulsante «principale» in
Modellazione: il gesto principale è disegnare.

### 3.3 La barra di Impianto [D]

| Gruppo | Comandi | Note |
|---|---|---|
| Pannelli | Sottocampo (S), Fila (L), Est-ovest, **Su pensilina**, **Posa** (principale), Svuota | quelli di oggi più la posa semplificata sulla pensilina |
| Inverter | Catalogo…, Dimensiona | come oggi |
| Accumulo | Configura… | come oggi |
| Stringhe | Proponi, Completa, Disegna, Ricomincia | come oggi |

L'ordine dei gruppi è l'ordine del lavoro chiesto da Daniel: pannelli, inverter, accumulo; le stringhe chiudono perché
hanno bisogno di entrambi.

### 3.4 La falda a mano (R274): il flusso [D]

Bozzetto `falda-a-mano.png`.

1. **Due clic: la gronda.** Il primo e il secondo punto sono la linea di gronda (agganci come oggi). Quota di gronda
   predefinita = gronda dell'edificio.
2. **Il puntatore sale: la falda si forma** come rettangolo dalla gronda; un numero digitato è la profondità (come
   oggi «lunghezza» mentre si disegna, `plan._typed`). Accanto al puntatore la **scheda Falda**, che oggi è la misura
   che segue il cursore (`_draw_labels`), con quattro righe: Profondità, Inclinazione (° e %), Quota colmo, Gronda.
   Tre modi di chiudere, uno solo alla volta, gli altri si ricalcolano: scrivere l'**inclinazione** (la profondità
   resta, il colmo sale: gronda + profondità × tan α); scrivere la **quota del colmo** (l'inclinazione segue;
   rifiutata sotto la gronda, come `ridge_written`); cliccare il **punto di arrivo** sulla pianta (un colmo, un muro,
   un aggancio: la profondità è la distanza dalla gronda).
3. **Tab scambia gronda e colmo** senza ridisegnare: la quota di gronda resta all'edificio, la falda si ribalta.
   Invio o terzo clic chiude.
4. **Dopo**: la falda libera ha finalmente la sua pagina nelle Proprietà (Gronda: lato e quota, Inclinazione, Quota
   colmo, Profondità, pulsante «Scambia gronda e colmo», «Scegli il lato di gronda sulla pianta» già esistente per
   mono); i lati si tirano come gli altri.

Dati: nessun formato nuovo; `ring`, `eave_side`, `eave`, `tilt` bastano, la quota del colmo è derivata.

### 3.5 Il colmo che genera il tetto (R275) [D]

Bozzetto `colmo-tetto.png`.

- Strumento **Colmo (C)**, dentro un edificio: un segmento (rettangolo) o una spezzata (L, T) con Invio. Ogni
  segmento si **aggancia all'asse** del rettangolo o alla direzione dei lati vicini.
- Alla chiusura il programma scrive ciò che oggi si fa lato per lato: i lati toccati dai capi del colmo diventano
  **testate**, gli altri gronde (`roof.edges`); chiede la **quota del colmo** nella scheda accanto al puntatore (prevalore
  gronda + metà larghezza × tan 35 %) → `ridge_height`; il tipo diventa `gable`. Il tetto è lo scheletro dritto che c'è
  già: sulla L il compluvio viene da sé.
- Il colmo disegnato resta nel modello (`roof.ridge_line`) per spostarlo o riquotarlo; in pianta è la linea ambra
  del tetto (già disegnata da `roofs.ridges`), trascinabile.
- **Colmo fuori asse** (falde di larghezza diversa = due pendenze): è lo scheletro pesato, che non c'è. Primo lotto:
  il colmo si aggancia all'asse e l'avviso lo dice; secondo lotto: asimmetrico (studio 16, A5, 2-3 giorni).

Prova che decide: sulle 306 piante di `16-prove/scheletro-riferimento.json`, con il colmo centrato, le falde devono
coincidere con quelle del `gable` con le stesse testate.

### 3.6 I lati cliccabili (R276) [D]

Bozzetto `lati-e-anteprima-3d.png`, a sinistra.

- In pianta la pillola di ogni lato dell'oggetto selezionato diventa «③ 12,00 m»: numero cerchiato e misura.
- **Un clic sulla pillola** (non sul lato: il lato resta per la selezione e il trascinamento) apre il campo
  nella pillola stessa; Invio tira il lato (`sides.stretch`), Esc rinuncia. Il doppio clic sul lato resta per
  abitudine; il `QInputDialog` sparisce.
- Il passaggio sul campo «Lato 3» delle Proprietà (Lati e Tetto) accende il lato 3 in pianta, e il passaggio sulla
  pillola accende il campo: la stessa evidenza che oggi ha `edge_hover`.
- Nelle anteprime dei dialoghi i numeri sono gli stessi della pianta.

Dati: nessun cambiamento.

### 3.7 La pensilina: struttura in Modellazione, posa in Impianto (R281) [D]

Bozzetto `pensilina-struttura-posa.png`.

**In Modellazione, «Pensilina…» (T)** crea solo la struttura: pilastri, trave di colmo o di bordo, piano di
copertura a una falda o a due falde opposte. Campi: posti per fila, file (una, falda unica / due, falde opposte),
larghezza posto, profondità, altezza libera (sotto trave), pendenza, pilastri (a sbalzo su una fila oppure due file;
numero), rotazione. L'anteprima 3D (3.8) mostra la struttura e si aggiorna. «Mettila in pianta» e il clic la piazza
(come oggi `pick_points("carport")`). **Nessun modulo appare.**

**In Impianto, «Su pensilina»**: con una pensilina selezionata, crea un sottocampo per falda che copre tutta la falda,
con tre o quattro campi soltanto: orientamento dei moduli (lungo la falda / di traverso), file di moduli (prevalore:
quelle che riempiono la profondità), sporto oltre la struttura, bordo. Niente passo tra le file, niente altezza dal
piano, niente corridoi: la pendenza e la quota sono della struttura. Il sottocampo porta `canopy = id` come oggi
porta `pitch`.

### 3.8 Le anteprime 3D nelle finestrelle (R282) [D]

Bozzetto `lati-e-anteprima-3d.png`, a destra.

- Un widget `ui/preview3d.py` **in QPainter**: assonometria (vista da sud-ovest, 30° di elevazione), facce in due
  grigi e il verde delle falde, spigoli neri, pillole con le misure sui lati «parlanti». Niente Qt Quick 3D: la vista
  3D del programma è già disegnata in immagine per non appesantire la finestra (`view3d.py`, docstring), e una scena
  per dialogo costerebbe centinaia di millisecondi e la scelta dei lati per raggio. L'assonometria ridisegna in
  meno di un millisecondo e si prova offscreen.
- **Trascinare** gira la vista (azimut, ±elevazione); la rotella no (il dialogo scorre).
- **Clic su un lato o su una pillola**: il campo corrispondente del modulo prende il fuoco e si accende; la misura si
  scrive nel campo, oppure in una pillola che si apre sul lato (stessa pillola della pianta, 3.6). Passaggio sul campo
  → lato acceso, e viceversa.
- Dove serve: **Da modello** (prisma della pianta con tetto piano, lati numerati), **Pensilina** (struttura),
  **Falda** (la scheda accanto al puntatore resta 2D in pianta: il 3D è nella vista 3D stessa, non in un popup).
  Il `template_dialog.Outline` 2D resta come scheda alternativa «Pianta» per chi vuole i numeri senza prospettiva.

### 3.9 Che cosa cambia nei dati (`.mer`) e nella migrazione [D]

Formato 20 → **21** (`model.py`, una migrazione sola per i tre punti):

| Dato | Nuovo | Migrazione 20 → 21 |
|---|---|---|
| `Roof.ridge_line: list \| None` | i punti del colmo disegnato (metri assoluti) | `None` per tutti i tetti di prima; `edges` e `ridge_height` restano com'erano |
| `Project.canopies: list[Canopy]` | `id, name, origin, turn, bays, bay_width, rows, depth, clearance, tilt, pillars {mode: "cantilever" \| "two_rows", count}, beam` | **ricavata** dai sottocampi `mounting == 'canopy'`: dall'anello larghezza, profondità, rotazione; dall'`SupportPlane` pendenza e altezza libera; due sottocampi adiacenti con azimut opposti → una pensilina a due file; pilastri predefiniti a sbalzo; avviso nel registro delle migrazioni |
| `SubField.canopy: str \| None` | la pensilina a cui il sottocampo appartiene (come `pitch`) | assegnato dalla migrazione sopra; il `support` resta per i file che non si riconoscono |
| falda libera | nessuno | nessuna |
| fasi, barre | nessuno nel file | nessuna; le scorciatoie nuove sono nel config, non nel progetto |

Fixture nuova `tests/formati/file/project-v21.mer` accanto alle altre, le vecchie intatte. Mesh e IFC: pilastri e
travi come parallelepipedi (`IfcColumn`, `IfcBeam`), piano come `IfcRoof`; le ombre dei pilastri sui moduli
restano fuori (Aurora fa lo stesso; da dire nella relazione).

### 3.10 Rischi

- **Spostare la posa** tocca `window.py` (fasi, pannello destro, comandi abilitati per fase), la guida, il tour R06,
  `po/it.po`, i test di finestra; va fatto per primo e da solo, quando nessun altro agente lavora su `window.py`.
- **Tab** durante il disegno: nessun uso in `plan.py` oggi (grep), ma Qt usa Tab per il fuoco tra widget: va preso
  nella pianta solo mentre si disegna una falda.
- **Un clic sulla pillola** può rubare clic a chi voleva selezionare: la pillola è fuori dall'anello e piccola; se
  disturba, resta il doppio clic (domanda 5).
- **Colmo**: agganci dei segmenti e riconoscimento delle testate su piante storte (trapezio); il colmo asimmetrico è un
  algoritmo nuovo (scheletro pesato).
- **Pensilina**: la migrazione «ricavata» può sbagliare su file con sottocampi modificati a mano; il ripiego è
  lasciare il sottocampo senza struttura e dirlo. Le prove di oggi (`test_canopies.py`, `test_canopy_workflow.py`)
  cambiano tutte.
- **Anteprima 3D**: scelta dei lati per vicinanza allo spigolo proiettato (6 px), tema scuro, DPI 2,5 del Dell;
  gli angoli dell'assonometria possono nascondere un lato (la rotazione col trascinamento lo risolve).

### 3.11 I lotti e il costo

| Lotto | Contenuto | Giorni |
|---|---|---|
| L1 | Fasi: Modellazione e Impianto (pannelli → inverter → accumulo), pannello destro di Impianto, guida, tour, po, test | 1,5-2 |
| L2 | Lati numerati e pillola cliccabile in pianta, evidenza incrociata con le Proprietà (R276) | 1 |
| L3 | Falda a mano: scheda con profondità/inclinazione/quota colmo, punto di arrivo, Tab, pagina Proprietà della falda libera (R274) | 2-3 |
| L4 | Widget anteprima 3D (`preview3d.py`) e suo uso in Da modello e Pensilina (R282) | 2-3 |
| L5 | Pensilina: oggetto `Canopy`, dialogo struttura, mesh e IFC, formato 21 e migrazione, «Su pensilina» in Impianto (R281) | 4-6 |
| L6 | Colmo → tetto, centrato (R275) | 2-3 |
| L6b | Colmo fuori asse (scheletro pesato), se Daniel lo vuole | 2-3 |
| | **Totale senza L6b** | **12,5-18** |

Ordine consigliato: L1, L2, L3, L4, L5, L6: ogni lotto lascia il programma usabile, L4 prima di L5 perché il dialogo
della pensilina nasce già con l'anteprima.

## 4. Domande per Daniel (una per scelta, con la mia raccomandazione)

1. **Nome della fase 1**: «Modellazione» o restare «Modello»? Consiglio **Modellazione**: è l'azione che si fa lì,
   come «Impianto» e «Relazione» sono ciò che si produce; «Modello» rischia di confondersi con «Da modello».
2. **Pannello destro in Impianto**: (a) le Proprietà quando c'è una selezione in pianta e la pagina Impianto altrimenti;
   (b) due linguette fisse «Oggetto» e «Impianto»; (c) una pagina Impianto con tre sezioni (Pannelli, Inverter, Accumulo)
   che apre la sezione del comando usato e mostra la scheda del sottocampo selezionato dentro Pannelli. Consiglio **(c)**:
   una pagina sola che racconta l'impianto nell'ordine chiesto; (a) è più veloce da fare se il tempo manca.
3. **Tasto per scambiare gronda e colmo** mentre si disegna: Tab o un altro? Consiglio **Tab**, preso dalla pianta solo
   durante il disegno della falda; F è già usato.
4. **Colmo fuori asse**: primo lotto agganciato all'asse con avviso, asimmetrico dopo; oppure subito asimmetrico?
   Consiglio **agganciato prima**: copre i tetti reali più comuni con lo scheletro già verificato, e l'asimmetrico si
   decide vedendo se serve.
5. **Clic sul lato in pianta**: un clic sulla pillola apre il campo (il doppio clic sul lato resta), oppure solo il
   doppio clic ma con il numero? Consiglio **un clic sulla pillola**: è il gesto che ha descritto, e la pillola è
   fuori dall'anello.
6. **Anteprima 3D**: assonometria in QPainter o la vera scena Qt Quick 3D in piccolo? Consiglio **QPainter**: istantanea,
   cliccabile, provabile offscreen; la scena vera è già nella vista 3D, che resta il posto dove guardare il modello.
7. **Pilastri della pensilina**: a sbalzo (una fila di pilastri) o due file, con quale predefinito? Consiglio la
   **scelta a due voci con «a sbalzo» predefinito** (il parcheggio tipico), numero di pilastri proposto dalla larghezza
   (uno ogni due posti).
8. **Pensiline nei file di oggi (formato 20)**: ricavare la struttura dai sottocampi nella migrazione, o lasciarli
   senza struttura con avviso? Consiglio **ricavarla** e scriverlo nel registro delle migrazioni: il file resta coerente
   con il nuovo modello; chi non torna resta sottocampo semplice.
9. **Posa su pensilina**: un comando dedicato con tre o quattro campi (proposta) oppure la posa generale con un profilo
   «pensilina» che nasconde i campi inutili? Consiglio il **comando dedicato** che usa dentro la posa generale: meno
   da imparare per chi disegna, lo stesso motore per chi mantiene.
10. **Oggetto 3D in Ostacoli**: entra nella barra di Modellazione appena arriva il lavoro di Kimi, oppure resta nel
    menu finché non è integrato? Consiglio **nella barra solo quando c'è** (`planned` in `phases.py`, come per gli altri
    comandi futuri).

**Decisione di Daniel (30/10/2026 sera): tutte e dieci le raccomandazioni.** Si procede con i lotti nell'ordine L1-L6 (L6b solo se servirà).

## File

- `README.md` (questo), `bozzetti.py` (genera gli SVG e i PNG).
- Bozzetti: `fasi-e-barre.svg/png`, `falda-a-mano.svg/png`, `colmo-tetto.svg/png`, `lati-e-anteprima-3d.svg/png`,
  `pensilina-struttura-posa.svg/png`.
- Foto di oggi (offscreen, look Meridiana): `oggi-pensilina.png`, `oggi-modello-edificio.png`,
  `oggi-proprieta-edificio.png`.
