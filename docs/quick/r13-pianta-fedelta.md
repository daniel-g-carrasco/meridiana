# Pianta Quick: esito della passata di fedeltà

05/11/2026, ramo `r13-pianta`. Riferimenti: `PASSATA-FEDELTA.md`,
`da-sistemare.md`, R388 e R389. Nucleo e `ui/` non modificati.

## Risultato e limiti della consegna

[V] La pianta usa nodi grafici nativi con render loop `threaded`. Non registra
più il vecchio `ModuleGeometry.updatePaintNode` Python. La finestra unita usa
la stessa sessione, i comandi globali e la barra di stato della shell.

[V] Corrette barra, selezione, hover, prese, campo dei lati, inquadratura al
ridimensionamento, colori per fase, Esc, zoom dei comandi globali, doppio clic
sui lati, scorrimento touchpad a fasi e scheda Sposta/Ruota. Le correzioni
comportamentali hanno prove riproducibili; quelle visive hanno anche foto.

Non dichiaro una parità totale: restano differenze dei componenti condivisi,
una parte dell'inventario storico e la misura della presentazione sul monitor.
L'elenco sotto separa questi limiti dalle parti verificate.

## Rendering: alternative provate

Stesso progetto di Rho, 778 moduli, finestra nativa Direct3D 11, scala 1.
Numeri in millisecondi, mediane di dieci passi del banco isolato.
La colonna GPU comprende `grabWindow`: è lettura della GPU, non latenza al monitor.

| Tecnica | Lavoro GUI | Frame con lettura GPU | Esito |
|---|---:|---:|---|
| Shape raggruppate, CurveRenderer | 1,620 | 33,051 | Scelta: tratti cosmetici, colori e contorni completi |
| Shape raggruppate, GeometryRenderer asincrono | 2,116 | 26,446 | Alternativa `triangles`; gestione dei tratti meno adatta alla fedeltà |
| Una Shape per modulo | 1,816 | 90,464 | Più nodi e costo grafico |
| Canvas | 13,792 | 48,768 | Ridisegno sul gesto, sfavorevole al filo GUI |
| QQuick3DGeometry nativa caricata una volta | 1,662 | 12,261 | Prototipo funzionante dei soli riempimenti |
| FileInstancing nativo | 2,181 | 16,542 | Prototipo funzionante dei soli riempimenti |
| FileInstancing con CustomMaterial shader | non valido | non valido | Moduli assenti nei campioni: prova fallita, non risultato di velocità |

[V] La geometria caricata e FileInstancing disegnano anche 20.000 moduli:
rispettivamente 1,339/11,648 e 1,765/10,865 ms GUI/GPU. Non includono gli
stessi contorni, prese e sovrapposizioni della pianta: non sono un confronto
della finestra completa. Restano esperimenti, non opzioni incomplete esposte
al progettista. Lo shader negativo è conservato con l'assert che rileva i
moduli mancanti.

[V] Un solo PathSvg di 20.000 moduli risultava vuoto. Suddividere per stile e
al massimo ogni 1.000 poligoni elimina il difetto. Verificati sui pixel i
moduli 0, 8192, 10922, 16384 e 19999. Il cambio della camera non carica di nuovo
le geometrie; rinomina e navigazione conservano i percorsi nativi.

[V] Spessore e tratteggio sono cosmetici. Il solo `cosmeticStroke` non bastava
a mantenere la lunghezza dei trattini: la prova sui pixel confronta due zoom.
Il ricalcolo del dash riguarda solo i percorsi tratteggiati, non ogni modulo.

Fonti tecniche consultate: [Qt ShapePath](https://doc.qt.io/qt-6/qml-qtquick-shapes-shapepath.html),
[Qt WheelHandler](https://doc.qt.io/qt-6/qml-qtquick-wheelhandler.html),
[Qt MouseArea](https://doc.qt.io/qt-6/qml-qtquick-mousearea.html).
L'assenza di callback Python di disegno è verificata sul codice e nelle prove;
non è dedotta dalle sole impostazioni del render loop.

## Misure della finestra unita

`tools/quick_fluidity.py` supporta `--real-views`, `--layout-only`, finestra
nativa, renderer scelto e render loop esplicito. Attende le 778 pose reali,
verifica che siano ancora presenti dopo il gesto e conserva hash del progetto,
del misuratore e dei sorgenti Quick, compresi backend e QML nelle sottocartelle.

| Giro, desktop separato | Pan, 40 passi | Rotella, 10 passi |
|---|---:|---:|
| `r13-fluidity-layout-01.json` | 669,20 | 174,81 |
| `r13-fluidity-layout-02.json` | 696,96 | 186,03 |
| `r13-fluidity-final.json` | 680,10 | 209,43 |
| `r13-fluidity-final-02.json` | 677,98 | 193,58 |
| `r13-fluidity-final-03.json` | 703,48 | 266,01 |
| `r13-fluidity-final-04.json` | 699,80 | 680,75 |
| `r13-fluidity-final-05.json` | 736,65 | 823,71 |
| Riferimento Widgets comunicato, HP | 721 | 192 |

[V] I primi due giri sono sotto il riferimento. Gli ultimi non lo sono sempre:
non basta scegliere il migliore per dichiarare raggiunto l'obiettivo. Durante
gli ultimi giri erano presenti numerosi processi Python concorrenti; [I] il
loro contributo al peggioramento non è stato isolato. Le prove non avvengono
sul monitor di Daniel e non certificano né il Dell al 200 % né la latenza reale.

[V] Pan e rotella non passano per `pointer` Python. Una notifica `viewSettled`
arriva dopo la pausa del gesto; nei giri con stalli arriva anche durante una
pausa intermedia. Rimossi i rifacimenti degli overlay di stringhe nascoste o
con scala invariata, e la notifica delle mappe quando i dati esposti non cambiano.
La prova controlla che il passaggio alla vista del mondo resti notificato.

Il giro `--layout-only` comprende entrambe le viste e pose reali, ma non un anno
energetico. Il tentativo iniziale con anno completo ha superato 180 s: nessun
risultato dell'anno è dichiarato. Lo smaltimento delle FileInstancing prima
della cancellazione della cache temporanea è verificato.

## Confronto visivo

Aprire `docs/quick/confronto/r13-pianta/index.html`. Coppie Widgets/Quick con
ritagli al 100 % e 200 %, manifest delle coordinate e hash delle immagini.
Stesso progetto, stesso copione, stesso formato finestra. Matrice: chiaro a
scala 1, scuro a scala 2, scuro a scala 1, chiaro a scala 2 con testo grande;
finestra 1366 × 900, 1600 × 960, 1800 × 1000 e 1920 × 1080 nei rispettivi percorsi.
Il progetto di Rho non viene salvato né modificato sul disco.

- [V] Barra: 345 × 33 px logici, con tutti i rettangoli dei pulsanti e separatori
  confrontati senza tolleranza con un ViewBar Widgets reale. Vista, adatta,
  più, meno, allinea, agganci, orto, sfondo e relativa freccia.
- [V] Selezione: stesso colore per tipo, alpha 30 per gli oggetti, 110 per il
  modulo, 150 per la selezione multipla; contorno 2,6/2,2 e alone. Hover sotto
  la selezione, come `Z_SELECTION - 1`, senza secondo riempimento. La prova
  controlla sia il pixel interno sia la continuità del contorno al passaggio.
- [V] Fila: rettangolo minimo ruotato sui moduli della fila, non un rettangolo
  allineato agli assi. Prese dei vertici tonde, trasparenti e magenta, centrate.
- [V] Pillole e campo dei lati: disco invertito del numero, colori opachi,
  dimensioni, font e unità; tacca con lati corti, assenza di sovrapposizioni,
  vista ruotata. Il pilota asserisce che il doppio clic apra davvero il campo.
- [V] Sposta/Ruota: scheda con le stesse righe del metodo Widgets, angolo
  applicato coerente, copia, vettore, centro e linea iniziale, sagome tratteggiate.
- [V] In Impianto i moduli non assegnati sono rossi anche prima della prima
  stringa. In Modellazione stringhe e nomi seguono il comando W.
- [V] Adatta include i contorni e resta attivo durante il resize fino al primo
  gesto manuale. Zoom da tastiera e barra conserva il punto centrale della vista.
- [V] Bussola, scala, tratteggio esclusioni, simboli, ombre e sfondi hanno prove
  proprie. Esclusioni con tratteggio di 8 px a due zoom; immagini importate con
  spostamento, rotazione, scala, trasparenza, visibilità, cancellazione e undo.

Differenze scritte, non dichiarate indistinguibili:

1. Larghezze dei pannelli e dimensioni utili della pianta dipendono dalla shell;
   producono inquadrature leggermente diverse pur seguendo la stessa regola.
2. Il menu condiviso Quick ha ancora angoli arrotondati rispetto al menu Widgets.
   Font e antialiasing producono piccole differenze nei ritagli.
3. Meridio può coprire un angolo della barra in alcuni passi: posizione della
   shell/assistente, non nascosto nel confronto.
4. Nei Widgets appena aperti `wiring_on` è vero mentre il comando Stringhe è
   spento. Dopo Impianto -> Modellazione si allineano. Il confronto di Modellazione
   usa questo stato comune; il Quick segue il comando fin dall'avvio.
5. Il simbolo warning condiviso misura 56 px contro 60 del disco a taglia 64.
   La prova resta `expectedFailure`, non allargata per passare.

## Comandi e prove

[V] Viaggi nella finestra unita per Esc in tre stati, focus dopo i comandi,
zoom globale, passaggio di fase, menu e campo del lato. La scorciatoia Esc
della shell prima scavalcava la pianta: ora `ShortcutOverride` protegge il gesto.
Il testo delle istruzioni passa alla barra di stato; rimossa la fascia interna.

[V] Menu per sito, edificio, sottocampo, modulo e fila confrontati con i Widgets;
azioni di disegno, file manuali, riempimento, svuotamento, esplosione, copie,
eliminazioni e annullamento. Rifare automaticamente le file manuali richiede
la stessa conferma: Annulla conserva il progetto, accetta e Undo lo ripristinano.

[V] Gesti Qt reali: tre clic del rettangolo, lunghezza e angolo digitati,
Maiusc, Ctrl, Tab, Backspace, agganci, ciclo delle prese, spostamenti a freccia,
copia C e Ctrl, rotazione prima della scelta, vertici, fila, lazo e sottrazione,
stringhe e cancellazione. I confronti degli strumenti verificano lo snapshot
del progetto, non solo i contatori delle chiamate.

[V] Navigazione: 14 stili confrontati con il nucleo e clic/trascinamento centrale
nella finestra, corda sinistro/destro durante il disegno, Space con auto-repeat,
rotella normale, precision touchpad, fasi Begin/Update/End, pinch nativo ancorato
e rotazione nativa ignorata. `WheelHandler` correggeva la perdita di ScrollUpdate:
prima pan 254, dopo 260, con la stessa sequenza di eventi.

Limite specifico: QML non espone `QWheelEvent.source()`. Il caso artificiale
con device Mouse, delta angolare senza fase e source SynthesizedBySystem
resta diverso dal percorso TouchPad nativo. È conservato tra i contratti parziali;
non si spaccia il test del device TouchPad per la stessa prova.

Inventario: `docs/quick/stato/pianta-prove.md`, generato da AST e confrontato
con il registro comune. 234 metodi storici: 73 sostituiti, 159 da portare o
parziali, 2 relativi ai soli QGraphicsItemGroup non validi per Quick. Il perimetro
include tutti i metodi dei moduli che citano la pianta, anche viaggi di finestra,
pannelli e servizi condivisi. **Non è una migrazione completa delle 234 prove.**
Ogni riga parziale conserva gli assert mancanti e la prova Quick già disponibile.

Verifiche generali eseguite: lint F/E9/B verde; 96 prove formati verdi;
46 prove sistema verdi. Compatibilità generale: 70 prove, una rossa nel registro
comune, 7 saltate e 2 fallimenti attesi. `test_registry` segnala 132 fonti cambiate,
a partire da R390: va rigenerato dal proprietario dopo l'unione dei rami. I file
del registro e le richieste altrui non sono stati riscritti per nascondere il rosso.

## Riproduzione e consegna a Claude

Preparazione PowerShell nella cartella del ramo:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='tests;src'
$env:QSG_RENDER_LOOP='threaded'
$python='C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe'
& $python tests/quick/pianta/run.py
& $python tests/quick/pianta/review.py
& $python tests/quick/pianta/gallery.py
& $python tests/quick/pianta/inventory.py
```

Comando **da eseguire sul monitor da Claude**, senza altri test o catture in corso:

```powershell
$env:QT_SCALE_FACTOR='2'
$env:MERIDIANA_TEST_SCREEN='1'
& $python tools/quick_fluidity.py --out build/r13-pianta-monitor-2x.json --on-screen --real-views --sequence plan --layout-only --render-loop threaded --plan-renderer batched --expect-modules 778
```

Prima verificare che il secondo monitor sia presente e che la finestra sia sul
Dell richiesto. `MERIDIANA_TEST_SCREEN` è letto dai test, non è una garanzia di
posizionamento del misuratore: questo apre a 80,40 sul desktop corrente.
Confrontare pan 40 e rotella 10 con 721/192 ms e controllare tutti i 778 moduli.
Togliere `--layout-only` per la prova separata con l'anno completo.

Al proprietario della shell/controlli: differenze di menu, pannelli e Meridio;
al proprietario della compatibilità: registro delle fonti e prove ancora parziali.
Nessun push, tag o pubblicazione eseguito. Nessuna semplificazione funzionale
autorizzata o introdotta.
