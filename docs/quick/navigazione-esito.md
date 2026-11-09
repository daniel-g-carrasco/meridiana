# Navigazione della vista 3D Quick

04/11/2026. Ambito: R389, R166, R190 e instradamento della rotella/touchpad di R242.

## Implementazione

- `CameraMath.js`: port numerico di `meridiana.camera`, assi Qt (Est, alto, Sud), quaternioni `(w, x, y, z)`. Ogni movimento restituisce uno stato nuovo; non modifica quello ricevuto.
- `Navigation.js`: port della macchina a stati `meridiana.navigation.Navigator`. Il navigatore riceve dal backend le tabelle del nucleo, non contiene una seconda copia dei 14 stili. Conserva click, soglia di trascinamento, accordi di pulsanti, modificatori, doppio clic e rilascio da assorbire. I gesti universali Spazio e Maiusc sono applicati dopo quelli dello stile, come nel nucleo.
- Entrambi sono librerie JavaScript QML: nessun callback Python per il calcolo di un fotogramma di navigazione.
- Nucleo e interfaccia Widgets non modificati.

## Contratto per la vista

Stato camera: `{position: [x,y,z], rotation: [w,x,y,z], target: [x,y,z], fov: 60, ortho: false}`.

Funzioni geometriche: `create`, `copy`, `look`, `forward`, `right`, `up`, `bearing`, `elevation`, `halfHeight`, `ray`, `project`, `ground`, `pivot`, `keepInView`, `pixelSize`, `zoomPoint`. Le coordinate e dimensioni della vista sono pixel logici. `ray` restituisce `[origine, direzione]`; un'intersezione o proiezione assente è `null`.

Movimenti: `orbit(state, dx, dy, pivot, mode)`, `pan(state, dx, dy, w, h, depthPoint)`, `zoom(state, steps, point)`, `recentre(state, point)`, `fit(state, centre, radius, aspect)`, `view(state, name, centre, radius, aspect)`, `orient(state, bearing, elevation)`. `orient` conserva bersaglio e distanza. `between(a, b, t)` interpola come il nucleo, con attenuazione cubica e slerp. `ANIMATION_MS` vale 240.

Navigatore: `create(style)` e poi `press(nav, button, mods, x, y)`, `move(nav, x, y, mods)`, `release(nav, button, mods, x, y)`, `doubleClick(nav, button, mods, x, y)`, `wheel(nav, steps, mods, x, y)`. Queste funzioni modificano solo il navigatore e restituiscono liste `{kind, phase, x, y, dx, dy, mods}`. `reset`, `setStyle`, `drags`, `chorded`, `previewsOrbit` completano il contratto.

Lo stile ricevuto usa `pan`, `orbit`, `zoom`, `select` come liste di coppie `[pulsanti, modificatori]`, entrambe liste di stringhe. Mantiene i nomi del nucleo `middle_click`, `middle_double`, `right_click`. Le liste sono quelle proprie dello stile, senza aggiungere i gesti universali prima di serializzarle: serve a mantenere la precedenza dei gesti propri.

`wheelAction(angle, pixel, phased, synthesized, ctrl, touchpad)` restituisce `[azione, dx, dy]`. Conserva i pixel anche se nulli negli eventi con fasi, come `navigation.wheel_action`.

La vista conserva il pick all'inizio del gesto e il piano del pan. Spazio da solo deve azzerare il pick precedente. Per l'orbita il pivot è quello alla pressione, oppure il centro/centro della selezione secondo la preferenza; viene passato a `keepInView`. La durata e i marker sono responsabilità della vista.

## Verifiche

[V] Otto test in `tests/quick/vista3d/test_navigation.py`, eseguiti con PySide6 6.12 e QJSEngine su Windows, verdi in 0,916 s:

- tutti i 14 stili, ogni gesto proprio e universale, click e doppio clic di ogni pulsante con Ctrl/Maiusc/Alt, cambio modificatori durante il movimento;
- accordi di pulsanti rilasciati in entrambi gli ordini, senza avviare il gesto indesiderato dopo il rilascio;
- Spazio senza pulsanti in ogni stile, soglia di click, anteprima dell'orbita;
- 320 passi combinati di orbita, pan e zoom confrontati numericamente con il nucleo, turntable e arcball, prospettiva e ortogonale;
- raggi, proiezioni, terreno, pivot, dimensione del pixel, campo visibile: anche al polo superiore/inferiore e vicino all'orizzonte;
- viste standard, adattamento, ricentramento, orientamento e animazione;
- limite della distanza minima e clipping ortogonale; punto sotto il cursore invariato prima del limite;
- eventi rotella e touchpad, inclusi scroll con fasi e pixel nulli.

[V] `ruff check --select F,E9,B tests/quick/vista3d/test_navigation.py` e `qmllint` sui due JavaScript: nessuna segnalazione.

[V] I test sono stati eseguiti prima delle librerie: fallivano per i due file mancanti. Il successivo confronto è verde. Nessuna soglia numerica è stata allargata.

## Limiti e prove della vista

[V] Al limite estremo dello zoom ortogonale il punto può spostarsi: `zoom` limita la distanza euclidea a 0,5 m, `half_height` limita invece la profondità a 0,5 m. Nel campione del test lo scarto orizzontale è circa 31 px. Il comportamento è identico al nucleo Python. Il test verifica sia questa parità sia la permanenza del punto fuori dal limite; non modifica il nucleo durante il port.

Le prove numeriche non dimostrano la consegna degli eventi Qt, i pixel del cubo, la fluidità o il numero di callback Python della vista integrata. Sono responsabilità delle prove `Viewport.qml` del ramo. Non sono state prodotte immagini in questo sottocompito, che contiene solo matematica e macchina dei gesti.

## Gizmo: spostamento, rotazione e altezze

04/11/2026, estensione dello stesso port. `GizmoMath.js` importa `CameraMath.js` e porta tutte le operazioni del nucleo `gizmo.py`: presa delle maniglie e dei vertici, intersezione asse/raggio e piano/raggio, misura degli angoli, trascinamenti e scatti. Nessuna modifica ai Widgets o al nucleo.

Contratto:

- `length(cam, centre, h)`: lunghezza della freccia in metri, corrispondente a 90 px.
- `pick(cam, px, py, w, h, centre, size, tolerance)`: `x`, `y`, `xy`, `rz` oppure stringa vuota; `z` non è una maniglia attiva.
- `along(cam, px, py, w, h, origin, axis)`, `onPlane(...)`, `angleOn(..., centre, zero)`: stesse semantiche del nucleo, `null` se il gesto non dà un valore.
- `begin(handle, cam, px, py, w, h, centre)`: stato `{handle, centre, start, value}` oppure `null`.
- `update(drag, cam, px, py, w, h, mods, snaps)`: aggiorna `drag.value` e restituisce `[Est, Nord, gradi]`. Il valore precedente resta se la nuova posizione è degenere.
- `offset(drag)`: spostamento nei tre assi Qt; `rotation(degrees)`: quaternione della rotazione di anteprima.
- `beginHeight(cam, px, py, w, h, origin)`: stato `{origin, start, value}` oppure `null`; `updateHeight(drag, cam, px, py, w, h, mods, snaps)`: aggiorna e restituisce lo spostamento verticale in metri.
- `pickPoints(cam, px, py, w, h, points, tolerance)`: indici dei vertici vicini, ordinati per distanza e indice.
- `ringPoints`, `squarePoints`, `step`, `stepped`: geometria e quantizzazione riusabili. `mods` è una lista di stringhe, `snaps` è booleano. I default di `update` e `updateHeight` sono modificatori vuoti e scatti attivi.

[V] Sei test aggiuntivi in `tests/quick/vista3d/test_gizmo.py`, verdi con QJSEngine su Windows (7,149 s):

- geometria e dimensioni confrontate con `mesh.py` e `gizmo.py`;
- presa di frecce, anello e piano, sul segno e fuori di 4/13 px, con otto camere: Home, Top, Est, Sud, prospettiva e ortogonale;
- ogni maniglia attiva e due inattive, aggiornamenti successivi con scatti normali, Maiusc e scatti spenti; conservazione dell'ultimo valore quando cambia la camera e il gesto diventa degenere;
- trascinamento delle altezze e degenerazione della verticale nella vista Top;
- vertici coincidenti e vertici distinti: presa, ordinamento e soglie;
- scatti positivi e negativi, inclusi valori esattamente a metà passo: arrotondamento al pari come Python, invece di `Math.round`.

[V] `ruff` sul test e `qmllint` sul JavaScript: nessuna segnalazione. Prima dell'implementazione i sei test fallivano per l'assenza della libreria.

[V] Un primo campione usava i punti equidistanti dell'anello come vertici: JavaScript e NumPy ordinavano diversamente due distanze simmetriche, a causa degli ultimi bit delle funzioni trigonometriche. La verifica dei vertici usa ora angoli di tetto distinti e punti esattamente coincidenti, che provano anche la precedenza dell'indice a pari distanza. La prova di presa dell'anello resta completa; non sono state allargate tolleranze né introdotte approssimazioni nel codice di presa.

Anteprima, copia con Ctrl, conferma in `session.edit()`, annullamento con Esc e scelta dei vertici appartengono alla vista/backend. La libreria restituisce solo la geometria del gesto e non scrive il progetto.

## Selezione e annullamento gerarchico

04/11/2026. Port nei soli metodi di presa e selezione di `scene.py`, con `tests/quick/vista3d/test_selection.py`.

- Il secondo clic su un modulo della stessa fila seleziona la fila. Un clic successivo torna al modulo. L'appartenenza viene dal `rid` di `layout.PlacedModule`, senza dedurla dal testo della chiave.
- La presa di un punto della scena segue la priorità Widgets: oggetto/esclusione, modulo, sottocampo, falda, edificio. La geometria viene dalle impronte del nucleo, dai moduli calcolati e dalle falde di `Building.pitches()`. Il sottocampo si prende anche quando non è riempito.
- Come `window._picked`, un clic sulla falda seleziona il suo edificio. Questo copre anche una falda libera fuori dall'impronta. Non introduce una selezione della falda diversa dal programma attuale.
- Se la scena ha colpito `buildings` e la pianta non trova nulla, si prende l'impronta più vicina entro 0,5 m, come `_building_near` dei Widgets. Una presa vuota seleziona il sito.
- Esc da modulo o fila torna al sottocampo, poi all'edificio ospitante e al sito. Oggetti ed esclusioni a terra tornano direttamente al sito. Una selezione esterna di tipo `pitch` può tornare al suo edificio.

Contratto QML: `sceneBackend.escapeSelection(moveMode)` restituisce una stringa. È invocabile anche senza argomenti, con `moveMode=false`.

| Risultato | Effetto |
|---|---|
| `edit` | Annullata anteprima, trasformazione o saldatura in attesa. Se era un gesto dei vertici, sono liberati nello stesso colpo, come `vertexLeft` dei Widgets. |
| `vertices` | Liberati i vertici scelti, conservato l'oggetto. |
| `tool` | Nessun gesto in corso: QML esce da Sposta impostando `moveMode=false`. La selezione resta. |
| `selection` | Risalito un livello nella gerarchia. |
| stringa vuota | Già sul sito, nulla da consumare. |

Prima della chiamata QML ferma il timer dell'anteprima e libera i propri drag locali. Non chiama prima `cancelEdit`: toglierebbe il livello che deve consumare questo Esc. La selezione passa da `session.select`, non modifica il progetto e non aggiunge undo. Le normali prese e risalite aggiornano solo la selezione, senza ricostruire la geometria.

[V] Otto test offscreen verdi in 0,811 s, senza finestra Quick3D e senza GPU: modulo/fila, outline della fila confrontato con `viewaids.outline`, presa di modulo tramite il suo punto, sottocampo vuoto, esclusione, falda libera, muro e limite di distanza, catena Esc, uscita da Sposta, annullamento anteprima con geometria e progetto ripristinati, vertici liberati e nessun undo aggiunto.

[V] Un test istanzia `PlanView` dei Widgets senza mostrarla: confronta le prese di cinque punti, inclusi oggetto sovrapposto e sottocampo vuoto, e quattro passi di `selection_back` direttamente con il nuovo backend. Nessun codice Widgets importato dall'implementazione Quick.

[V] Prima delle modifiche sei prove fallivano: tre per `escapeSelection` assente, tre per modulo/riga, superficie vuota e falda esterna. Lint F/E9/B del backend e del test verde. Nessuna modifica a `Viewport.qml`, `scene_host.py`, nucleo o metodi delle trasformazioni in questo sottocompito.
