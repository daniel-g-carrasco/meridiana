# Confronti geometrici e fotogrammi nativi

## Contratto tra i due alberi

`quick.parity.geometry.capture_quick` legge gli elementi visivi QML, compresi i
delegati che non compaiono nell'albero QObject. Il riferimento e la cattura Quick
usano `schema: 1`, `meta` e `widgets`. Le coordinate sono logiche, relative al
contenuto della finestra; la scala del dispositivo rimane in `meta.dpr`.

Ogni elemento confrontato deve avere un'identita esplicita. Per Quick e
`objectName`, univoco. Un file JSON di corrispondenze associa ID Widgets e QML:

```json
{
  "nomeWidgets": {
    "id": "nameField",
    "colors": {"Text": "text"}
  }
}
```

La mappa dichiara l'ambito del confronto. Un elemento mancante fallisce; elementi
non inclusi nella mappa non sono coperti. Duplicati e mappe vuote sono errori.
`rect` e `margins` ammettono al massimo 1 px logico. Font, colori e testo sono
esatti. Le palette Widgets e i colori Quick usano `#aarrggbb`. I margini QML sono
il padding del contenuto, non `anchors.margins`: quest'ultimo e gia riflesso nel
rettangolo. Nessun accoppiamento automatico per posizione o somiglianza.

Le misure dei font dei due alberi sono risolte con `QFontInfo`: famiglia,
punti e pixel descrivono il font effettivo, anche quando l'origine specifica
soltanto pixel o soltanto punti. Ogni riga mappata richiede `rect`, `margins`
e `colors`. Rettangoli e margini contengono quattro numeri finiti; le dimensioni
non sono negative. Un font presente richiede tutte le metriche valide; un
elemento con `text` deve avere un font. Un contenitore senza testo puo ometterlo,
ma la presenza su un solo lato rimane una differenza. Dati mancanti, NaN,
infinito o tipi errati sono errori di cattura, anche se uguali sui due lati.

Le deroghe in `differenze.json` richiedono `scenario`, `reference`, `quick`,
`field`, `before`, `after`, `request` e `reason`. Esempio di struttura, non deroga
approvata: `request: "R390"`, `field: "font"`, con entrambi i font completi.
Niente wildcard. Una deroga vale solo per quei due valori esatti. Il registro
iniziale e vuoto: le lacune del prototipo non sono semplificazioni approvate.

Il generatore `tools/quick_rif_compare.py` riceve `--widgets-json`, `--quick-json`,
`--widgets-image`, `--quick-image`, `--mapping` e `--output`. Produce HTML autonomo
con immagini affiancate e differenza RGB assoluta, senza ridimensionamento dei
pixel, piu le differenze geometriche non approvate. Le immagini devono avere
uguali dimensioni fisiche e DPR; un confronto a scale diverse e rifiutato.
Codice di uscita 1 se vi sono differenze non approvate. File esistenti rifiutati.

## Banco di prova delle finestre vere

`tests/quick/parity/realwindow.py` e riusabile dai rami Quick. Prima di creare
l'applicazione impostare `MERIDIANA_QUICK_NATIVE=1`, togliere
`QT_QPA_PLATFORM=offscreen` e chiamare `native_app()`. Su Windows forza Direct3D
11 solo in questo percorso nativo. Offscreen e minimal saltano esplicitamente:
non costituiscono prova della scheda video. Le prove native devono partire in
un processo separato dal gruppo che usa QApplication/offscreen.

```python
from quick.parity.realwindow import FrameRecorder, PythonCalls, assert_frames, wait_frames

with FrameRecorder(window, names=['leftPanel', 'rightPanel']) as recorder:
    wait_frames(recorder, 2)
    with PythonCalls() as calls:
        # Eventi sintetici al QQuickWindow con quick.gestures, mai puntatore fisico.
        perform_gesture()
    wait_frames(recorder, len(recorder.frames) + 1)
calls.assert_no_calls()
recorder.assert_valid(stable={'leftPanel': 1, 'rightPanel': 1},
                      regions={'properties': (1200, 100, 300, 400)})
recorder.save('build/quick-foto/compat/nuova-prova')
```

Le regioni devono contenere testo o disegno in ogni fotogramma: almeno lo 0,5%
di pixel deve differire dal colore dominante. La soglia e esplicita e adatta
anche al tema scuro. Le regioni uniformi intenzionali non vanno dichiarate come
contenuto obbligatorio. `stable` dichiara gli oggetti che devono rimanere presenti
e il massimo spostamento fra due fotogrammi, in pixel logici. Gli oggetti che
si animano intenzionalmente richiedono un contratto diverso.

R392: il filtro degli eventi intercetta `Show` per ogni QWindow non presente
all'inizio. Anche una finestra mostrata e nascosta fra due fotogrammi rimane nel
registro. Solo finestre intenzionali note possono entrare in `allowed_windows`.
Il registro e cumulativo e viene riportato nei fotogrammi successivi.
`recorder.assert_valid` controlla anche gli eventi successivi all'ultimo
fotogramma, per non perdere una finestra mostrata e subito nascosta.

`PythonCalls` usa il profiler Python sul thread dell'interfaccia e registra le
entrate effettive nei moduli `meridiana`, senza dipendere dai contatori del
bridge. Racchiudere soltanto la parte continua del gesto: il rilascio che
conferma una modifica puo chiamare Python e si misura separatamente. Il probe
rifiuta di sovrascrivere un profiler gia attivo.

## Limiti delle prove

La cattura viene richiesta dal segnale `frameSwapped` e letta sul thread GUI
con `grabWindow`, che sincronizza un nuovo rendering. Non e la copia esatta
del buffer gia presentato: uno stato cambiato prima del readback puo apparire
nell'immagine successiva. I segnali sono bloccati durante il readback per non
ricatturare ricorsivamente il rendering aggiunto dalla cattura. Per transizioni
critiche i passi di prova attendono una cattura fra due mutazioni.

Il readback rallenta il ciclo: gli intervalli registrati non dimostrano la
fluidita a monitor ne il limite dei 30 ms. Servono una misura separata senza
cattura e la verifica della presentazione sul monitor. Questo banco dimostra
contenuto GPU, geometria e finestre osservate nel processo, non certifica ogni
fotogramma presentato da Windows.

Le prove di guasto in `test_realwindow.py` introducono un fotogramma uniforme,
una regione scomparsa, un salto, una finestra inattesa e chiamate Python. La
prova nativa introduce anche una finestra QQuickWindow aggiuntiva e nasconde
contenuto vero. Passare queste prove dimostra che i controlli reagiscono ai
difetti; non chiude R392 nell'applicazione finche la pagina File Quick non esiste.
