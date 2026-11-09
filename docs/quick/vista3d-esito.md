# Vista 3D Quick e modelli liberi: esito

04/11/2026, ramo `r12-vista3d`. R365, R374, R375, R376, R389.

[V] Realizzati il componente 3D nativo, il backend sulla sessione comune, il bake e il catalogo
dei modelli, le prove differenziali, le fotografie D3D11 e i tre bozzetti d'inserimento.
Il tema e i controlli sono uniti da `r12-sistema`, fino a `61cb0eb`.
Nessun file del nucleo o di `src/meridiana/ui/` è stato modificato.

**Non è dichiarato raggiunto il limite di 30 ms:** la scena con 200 auto, 200 persone intere,
128 moduli e ombre complete lo supera sul desktop separato. Il test conserva la soglia originaria
come `expectedFailure`. L'inserimento nella Shell completa appartiene a `r12-sistema`:
il componente è montabile sulla stessa sessione, con contratto in `stato/r12-vista3d.md`.

## Scena e comportamento

[V] `Meridiana.View3D.Viewport` contiene direttamente un `View3D`, camera prospettica/ortografica,
tre luci di riempimento e il sole, terreno, edifici, ostacoli, moduli e modelli di contesto.
Mantiene materiali e illuminazione della scena esistente: MSAA High, ombre VeryHigh, PCF8,
due split CSM. Il mondo resta illuminato nello stesso modo nei temi chiaro e scuro.

[V] Camera, ray casting matematico, pan, zoom, orbita turntable/arcball, scelta del pivot,
Space, rotella, touchpad e animazioni sono lato QML/JavaScript. I 14 profili sono ricavati da
`navigation.STYLES`; le sequenze sono confrontate contro il nucleo Python.
Il cubo offre facce, spigoli e vertici, lettere cardinali, frecce, Home, imposta Home,
inquadra e cambio proiezione. Ha anche il formato compatto.

[V] Selezione con picking nativo delle istanze, alternanza modulo/fila, oggetti e sottocampi;
Esc risale la gerarchia come nei Widgets. Il backend usa la stessa `ProjectSession`.
Le anteprime dei vertici e dello spostamento lavorano su copie del progetto; rilascio e quota scritta
passano da `session.edit()` e producono un solo passo di undo. Esc ripristina la geometria.
Le istanze dei moduli seguono il trascinamento rigido di edificio, sottocampo e fila.
Durante la variazione delle quote dei vertici la posa viene rifatta al rilascio, come nei Widgets:
il tetto che sale può temporaneamente coprire i moduli ancora alla quota precedente.

[V] Quote assolute e relative su più vertici, selezione a rettangolo, stacca, salda e riporta su piano,
conversione a tetto libero, vertici coincidenti selezionabili a turno; gizmo, rotazione, passi di
aggancio, frecce e campo numerico. La data e l'ora del sole usano `sun.position` e Europe/Rome.
Sito sostituito o modificato aggiorna anche il sole. Modi ombreggiato, fil di ferro e trasparente.

[V] `SceneLayouts` serve solo al banco autonomo: snapshot su `QThreadPool.globalInstance()`,
debounce, risultati obsoleti scartati, nessuna energia sul thread grafico. La Shell deve mantenere
il proprio scheduler già collegato alla sessione, evitando un secondo calcolo.

## Istanze Python e render loop

[V] Il checkout di partenza usa già `QuickImage` per i Widgets, non più `QQuickWidget`.
Il problema storico documentato nel repository riguarda una virtuale Python di
`QQuick3DInstancing` richiamata dal thread di rendering mentre il thread GUI attende quel thread.

[V] Il nuovo percorso non implementa `getInstanceBuffer` né `updateSpatialNode` in Python.
`SceneGeometry` invia i buffer sul thread GUI; `FileInstancing` legge tabelle binarie native Qt.
Il formato Qt 6.12 v1 è verificato sul sorgente Qt: header `QtIR`, versione 1, stride 80,
offset 20, conteggio istanze e righe da 20 float32 little endian. Gli stessi byte della tabella
del nucleo sono verificati nel test. I file hanno nome SHA256 e restano disponibili finché il
renderer li usa. Non viene forzato il render loop `basic`.

[V] Finestra reale con `QSG_RENDER_LOOP=threaded`, Direct3D11 e scale 1/2: nessun blocco nelle
prove. I contatori includono anche i getter Python. Una lettura ripetuta delle preferenze è stata
trovata e rimossa: copie JavaScript dei dati numerici evitano che i wrapper QVariant richiamino
Python durante il gesto. Le misure finali riportano **zero chiamate Python durante l'orbita**.

Fonti: [FileInstancing Qt 6.12](https://doc.qt.io/qt-6/qml-qtquick3d-fileinstancing.html),
[instancing](https://doc.qt.io/qt-6/quick3d-instancing.html),
[sorgente delle tabelle](https://github.com/qt/qtquick3d/blob/6.12/src/quick3d/qquick3dinstancing.cpp),
[scene graph e thread](https://doc.qt.io/qtforpython-6/overviews/qtquick-visualcanvas-scenegraph.html),
[PinchHandler](https://doc.qt.io/qt-6/qml-qtquick-pinchhandler.html).

## Modelli e calcolo

[V] 26 originali con licenza individuale verificata CC0 producono 34 mesh statiche:
31 attive e tre tenute da parte. Tutti gli oggetti scelti da Daniel sono nel catalogo.
Street Lamp 01 e le due biciclette CC0 restano `active=false`; esclusi Power Lines di Chase W.
e Bicycle di Google. Otto persone, ciascuna in piedi e in cammino. Casual conserva
**5.776 triangoli per posa**, senza riduzione. Dettagli, fonti, conteggi e verifiche in
`modelli-esito.md` e `data/models/catalog.json`.

[V] `tools/models_bake.py` lavora fuori dal programma. Risultato: posizioni, normali e colori RGBA
per vertice, con texture base-colour campionate prima della distribuzione. Materiali PBR, normal map
e trasparenza non sono distribuiti. Le scritte sottili del container non sono riprodotte fedelmente
con questo formato. Fonti, hash e licenze sono accanto ai dati; `catalog()` è l'elenco per Informazioni.

[V] Un modello viene caricato una volta e riusato. 200 auto e 200 persone: due `SceneGeometry`,
due `FileInstancing`, 200 righe ciascuna. L'indicizzazione condivide solo vertici identici per
posizione, normale e colore. Il test ricostruisce tutti i triangoli dagli indici e li confronta
esattamente con il bake: non è una riduzione della mesh.

[V] Le sostituzioni sono esclusivamente visive. Una prova usa sette moduli con inverter/stringhe,
8.760 ore sintetiche, produzione positiva e ombre degli oggetti non nulle. Caricando il catalogo,
disabilitando/riabilitando le decorazioni e cambiandole completamente, restano identici:
`props.shadow_solid`, solidi del sistema, serie orarie e mensili, energia annuale, potenza, PR,
risultati delle stringhe, snapshot, chiave energetica e undo. Nessun numero di produzione cambia.

## Fotografie e confronto differenziale

[V] Foto native in `build/quick-foto/r12-vista3d/`, da `QQuickWindow.grabWindow()`, senza usare
mouse o tastiera reali. Matrice della scena: 1366×900, 1600×960 e 1920×1080 logici, chiaro/scuro,
scale 1 e 2. Controllati i pixel cambiati togliendo moduli e ombre separatamente, oltre alla
lettura del backend D3D11. Foto dei trascinamenti, selezione, modi vista e sole.

[V] Confronto con il vecchio `View3D` reale, stesso progetto e stessa camera, in
`confronto/vista3d.md`: scarto massimo dei limiti del tetto **0 px logici**, oltre **99,4% dei pixel
centrali identici** alle due scale. Non è dichiarata uguaglianza completa: rimangono differenze
isolate di antialiasing/ombra e gli overlay hanno un disegno QML proprio.
Il fit automatico nuovo include anche i moduli: corregge gli impianti a terra lontani dall'origine;
nel campione sposta l'inquadratura di circa 3–5,5 px rispetto al fit vecchio.

[V] Bozzetti R375: `inserimento-bozzetti.html`, autonomo, con libreria a miniature, inserimenti
ripetuti e disposizione lungo una linea con variazioni. Provato a 1440 e 600 px. Sono proposte
da scegliere: non sono state aggiunte queste modalità al programma.

## Misura della scena con 400 oggetti

[V] `tools/models_scene_benchmark.py`, 1600×960 logici, render loop threaded, 240 fotogrammi circa;
scartati i primi 30. Fotografie prima e dopo l'orbita, da lontano e da vicino. Tutti i modelli
restano interi, con ombre e 128 moduli presenti.

| Prova finale | Fotogrammi misurati | Mediana | P95 | Massimo | Oltre 30 ms | Chiamate Python nel gesto |
|---|---:|---:|---:|---:|---:|---:|
| Scala 1, chiaro | 214 | 33,33 ms | 34,42 ms | 50,72 ms | 207 | 0 |
| Scala 2, scuro, 3200×1920 reali | 212 | 49,88 ms | 50,63 ms | 83,74 ms | 212 | 0 |

File: `stress-s1-final/timing.json` e `stress-s2-exact/timing.json` nella cartella foto.
Lettura e preparazione iniziale: 2,97 s e 2,15 s nelle stesse esecuzioni.

[V] Una prima cattura a scala 2 era stata limitata da Windows a 3004×1902 pixel, nonostante la
dimensione richiesta. Il banco ora impone la dimensione minima prima di mostrare la finestra e
controlla dimensioni logiche e pixel con asserzioni. La riga scala 2 usa la nuova misura esatta;
la precedente `stress-s2-final` resta come traccia della diagnosi, non come prova a 3200×1920.
Anche la matrice nativa finale viene acquisita in `native-exact`, fino a 3840×2160 pixel reali.

[V] Tentativi conservati: prima dell'indicizzazione, mediana 49,90 ms a scala 1;
senza ombre, diagnostica soltanto, 24,25 ms. Una prova indicizzata precedente misurava 30,57 ms
a scala 1 e 38,78 ms a scala 2. Non viene scelto il risultato più favorevole come esito finale.
Sono state eliminate anche le ricreazioni dei delegate del cubo e degli overlay a ogni camera update.

**Limite aperto:** il criterio «nessun fotogramma sopra 30 ms» fallisce. Le prove strutturali
passano separatamente; `test_performance.py` conserva il criterio temporale come `expectedFailure`.
Questi sono intervalli QML in una finestra D3D11 vera sul desktop separato. Non misurano la
presentazione al monitor fisico di Daniel. Altri processi sono presenti sulla macchina condivisa;
non vengono terminati per ottenere un numero migliore. Il controllo sul monitor resta alla sessione locale.

## Verifiche e riproduzione

[V] Cataloghi compilati con `tools/compile_po.py --python`. Gruppo `formati`: **96 prove verdi**.
Lint dell'intero repository `ruff check --select F,E9,B .`: verde.
Suite vista3d: **78 prove, otto saltate perché native**, nessun errore.
Le prove aggiunte dopo quella esecuzione sono rilanciate nei gruppi mirati indicati nello stato finale.
Revisione indipendente: dieci regressioni aggiunte e corrette, incluse quote multiple, undo
della topologia, sole al cambio sito, bounds, cambio selezione durante preview e saldatura rifiutata.

Comandi dalla radice del ramo, Python della venv comune in sola lettura:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='tests;src'
$env:QT_QPA_PLATFORM='offscreen'
C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe -m unittest discover -s tests/quick/vista3d -v

$env:QT_QPA_PLATFORM='windows'
$env:QSG_RENDER_LOOP='threaded'
$env:QT_SCALE_FACTOR='1' # ripetere con 2
$env:MERIDIANA_QUICK_3D_NATIVE='1'
C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe -m unittest discover -s tests/quick/vista3d -p test_native.py -v
```

Banco autonomo, senza salvataggio del progetto:

```powershell
C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe -m meridiana.quick.backend.scene_host <progetto.meridiana>
```

## Confini della consegna

- [V] Componente e adattatore pronti nelle parti assegnate. La Shell e la scelta Pianta/3D/entrambe
  restano del ramo sistema; nessuna modifica al suo `app.py` è stata anticipata.
- [V] I modelli senza un corrispondente tipo già presente sono pronti nel catalogo e nella galleria.
  Il selettore di inserimento dipende dalla scelta R375, quindi non è stato inventato.
- [V] Il limite temporale di 30 ms resta aperto. Non sono ridotti i personaggi per superarlo.
- [V] Il confronto completo degli overlay entro 1 px e la presentazione sul monitor fisico non sono certificati.
- [V] Nessun push, tag o release. Aggiornamento del registro richieste richiesto a r12-compat nello stato del ramo.
