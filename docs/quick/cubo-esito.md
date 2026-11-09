# Cubo Quick e bozzetti di inserimento

04/11/2026. Parte del ramo `r12-vista3d`, R359, R375, R389 e R395.

## Fatto

- `ViewCube.qml`: cubo completo da 112 px, compatto da 76 px, geometria del cubo da 64 px. Sei facce, dodici spigoli e otto vertici cliccabili; bussola N/E/S/O, quattro frecce da 45°, Home, menu, proiezione parallela, inquadratura, memorizzazione della vista iniziale. Nel compatto Home passa nel menu. Un doppio clic su una parte chiede anche l'inquadratura.
- Il componente riceve `bearing`, `elevation`, `compact`, `dark`, `orthographic` e i colori. Emette `orientRequested`, `homeRequested`, `setHomeRequested`, `orthographicRequested`, `fitRequested`. La proiezione e il picking sono JavaScript QML, senza Python per movimento del puntatore o aggiornamento della camera.
- `CubeMath.js` riprende gli assi e le celle di `navicube.py`: x est, y alto, z sud, elevazione negativa guardando verso il basso. Su Alto/Basso conserva il quarto di giro più vicino. Il cubo resta ortografico anche con scena prospettica, come nei Widgets; il menu cambia la camera della scena.
- `inserimento-bozzetti.html`: tre bozzetti autonomi, senza rete, con miniature disegnate per alberi, luci, recinzioni e auto. Posa ripetuta, serie con due estremi e passo, gruppo con variazione riproducibile di scala e rotazione. Anteprima, conferma, annullamento, Esc, vista stretta. Nessuna modalità d'inserimento è stata aggiunta al prodotto.

## Prove

- [V] Test inizialmente rossi per i componenti mancanti, poi verdi. `test_cube.py` confronta le 26 direzioni con il nucleo Widgets, compresi i quarti di giro; confronta il picking su 40 orientamenti; invia veri clic Qt a tutte le 26 parti. Verifica frecce, Home, doppio clic, proiezione e Home nel menu compatto.
- [V] Otto prove verdi su Windows, Direct3D 11, render loop threaded, compresa la prima cattura nativa. Dopo l'aggiunta della prova del menu compatto: otto verdi offscreen, una prova nativa esplicitamente saltata. Il test nativo si esegue solo su Windows senza piattaforma offscreen e avvia `tools/models_scene_probe.py` in un processo isolato.
- [V] La prima cattura integrata ha rivelato un difetto del Canvas: lettere presenti, celle e comandi assenti. Dimensioni 112×112, `visible` e `available` erano corretti; un repaint successivo rendeva visibili le forme. La versione finale usa `Shape` e `PathPolyline`, senza texture Canvas asincrona. Il test sui pixel misura 0 pixel di faccia nella foto difettosa e 1388 nella foto corretta, contro una soglia di 600. La soglia esclude lettere e sfondo.
- [V] Immagini Direct3D 11 ispezionate: `build/quick-foto/r12-vista3d/cube-shapes/1366x900-s1-light.png` e `1366x900-s2-dark.png`, scala 1 e 2. Nessun warning QML nelle catture. Ritagli ingranditi `crop.png` e `crop-dark-s2.png`.
- [V] Bozzetti aperti e fotografati in Qt WebEngine, a larghezza 1440 e 600 px. Clic nel primo riquadro: da quattro a cinque copie; conferma serie: copie posate; variazione e conferma gruppo: sette copie posate. Immagini in `build/quick-foto/r12-vista3d/inserimento-bozzetti*.png`. In questo desktop isolato Qt WebEngine richiede `QTWEBENGINE_DISABLE_SANDBOX=1` per il processo di prova; il file HTML non richiede impostazioni speciali in un browser normale.
- [V] Ruff F/E9/B sul test: verde. Il test di pixel è specifico della regressione osservata, non una misura di fluidità a monitor.

## Differenze e integrazione

- Le celle, gli assi, le hitbox, le dimensioni e i gesti conservano il riferimento Widgets. Le scritte usano il carattere ereditato dal controllo, senza famiglia sostitutiva: Alto/Basso in maiuscolo iniziale, mentre il disegno Widgets applica lo stile LABEL tutto maiuscolo. Questa differenza è intenzionale per mantenere il carattere e la misura del testo scelti nell'applicazione.
- Colori esposti come proprietà, per collegare i token del tema senza vincolare il cubo a un singleton quando usato da solo. Il menu eredita font e palette. Tooltip con dissolvenza 90/60 ms; il passaggio immediato fra tooltip dipende dal futuro controllo condiviso del sistema.
- Le fotografie della scena completa alle altre dimensioni e il confronto complessivo con i Widgets appartengono alla verifica del ramo. Non è stata certificata un'identità pixel a pixel del testo del cubo.
- La scelta fra i bozzetti R375 resta di Daniel. Proposta illustrata nel file: unica libreria, strumenti Posa e Lungo una linea; Gruppo con variazioni come opzione secondaria.

## Comandi

```powershell
$env:PYTHONPATH = 'src;tests'
$env:QT_QPA_PLATFORM = 'windows'
$env:QSG_RENDER_LOOP = 'threaded'
& C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe -m unittest discover -s tests/quick/vista3d -p test_cube.py
& C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe -m ruff check --select F,E9,B tests/quick/vista3d/test_cube.py
```
