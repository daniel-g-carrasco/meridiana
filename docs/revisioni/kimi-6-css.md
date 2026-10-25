# Revisione Kimi 6: il peso del foglio di stile

Data: 25/10/2026. Commit misurato: `45ab43d206f3e8e56663c9b453a10b6c89e222f9`.

## Conclusione

Il QSS **non spiega da solo le lentezze ordinarie della finestra**: disegnare venti widget comuni costa 2,056 ms con
il foglio e 1,936 ms con il solo `ScrollStyle`, una differenza mediana di 0,120 ms. Il foglio **costa invece molto
quando viene applicato a tutta l'applicazione**: 595,5 ms, coerenti con gli 0,4-0,9 s già misurati nello studio 13.

Quindi non propongo di togliere o ridurre il foglio per migliorare il disegno normale. Un cambio di tema è un caso
diverso: lì il costo globale è reale e non va nascosto. Non serve una proposta nuova per un selettore specifico:
`QScrollArea` pesa nella lucidatura, ma spiega solo una piccola parte dell'applicazione del foglio e non ha un effetto
misurato sul disegno ordinario.

## Ambiente e metodo

- Linux, Python 3.14.9, PySide6 e Qt 6.12.0, piattaforma `offscreen`, disegno raster.
- Finestra reale con il progetto di prova, 1600 x 960, 1.911 widget, 218 visibili. Timer e lavori periodici fermi;
  nessuna rete e solo cartelle temporanee.
- QSS generato da `ui/theme.style_sheet`, applicato con `QApplication.setStyleSheet`. Confronto A/B con la stringa
  vuota, conservando `ScrollStyle` come stile di base.
- Tempi con `time.perf_counter_ns`, mediane su molte ripetizioni, primo campione conservato separatamente. Nessuna
  finestra sullo schermo e nessuna modifica al codice di Meridiana.
- Per la lucidatura completa: `unpolish` su tutti i widget, poi il tempo del solo ciclo `polish`. Il tempo di
  `setStyleSheet` comprende invece tutto ciò che Qt fa alla chiamata; i due tempi non si sommano.
- Per gli eventi: filtro su ogni widget per `Polish`, `PolishRequest` e `StyleChange`, contando eventi e widget
  distinti. Per `tone` e `primary` ho anche contato le chiamate dirette a `unpolish` e `polish`.
- Per i selettori: una regola alla volta tolta dalle 161, prima una scansione completa, poi 9 coppie di misure sui
  candidati principali. Su `QScrollArea`, `QSlider:horizontal` e `QToolButton#rowfix` ho fatto altre 21, 21 e 15
  coppie per controllare il rumore.

## Quanto foglio c'è davvero

Il file `src/meridiana/ui/theme.py` occupa 40.966 byte, ma non è tutto QSS. Il foglio generato oggi, sia chiaro sia
scuro, ha queste misure:

| Misura | Valore |
|---|---:|
| caratteri | 15.058 |
| byte UTF-8 | 15.058 |
| regole | 161 |
| selettori, contando separatamente quelli separati da virgole | 230 |
| righe | 205 |

Il riferimento a «circa 42 KB di QSS» descrive quindi meglio il modulo sorgente che il testo effettivamente applicato.

## Applicazione, prima lucidatura e disegno

| Misura | Campioni | QSS, mediana | Solo stile, mediana | Differenza |
|---|---:|---:|---:|---:|
| `setStyleSheet`, alternanza chiaro/scuro | 23 | 595,499 ms | - | - |
| Prima lucidatura completa dopo `unpolish` | 9 per modo | 54,617 ms | 3,326 ms | +51,291 ms |
| Disegno di 20 widget comuni | 62 per modo | 2,056 ms | 1,936 ms | +0,120 ms, +6,2 % |

Altri dati utili:

- `setStyleSheet`: media 605,719 ms, minimo 576,093 ms, massimo 765,804 ms; primo campione 576,093 ms.
- Prima lucidatura: primo campione QSS 54,617 ms, solo stile 3,339 ms.
- Primo disegno: QSS 3,218 ms, solo stile 2,718 ms. I disegni successivi sono più veloci e molto meno rumorosi.
- La finestra contiene molti widget nascosti: tutti partecipano ai costi globali, non solo i 218 visibili.

Il pannello del disegno comprende etichetta, due pulsanti normali e uno primario, pulsante strumento, campo di testo,
campi numerici, elenco a tendina, data, casella, opzione, cursore, avanzamento, albero, elenco, tabella, linguette,
gruppo, testo lungo e area di scorrimento. Il confronto misura il disegno, non sostiene che i due aspetti siano uguali.

## Quanti widget vengono rilucidati

Qt non ha inviato eventi `Polish` o `PolishRequest` nelle sonde: il segnale osservabile è `StyleChange`.

| Operazione | Eventi `StyleChange` | Widget distinti |
|---|---:|---:|
| Prima applicazione scuro partendo dal solo stile | 1.983 | 1.878 |
| Cambi di tema successivi, cinque misure | 15.869 ogni volta | 1.911 ogni volta |
| Proprietà `tone` | 0 | 0 |
| Proprietà `primary` | 0 | 0 |

La prima applicazione non è identica ai cambi successivi: installa anche lo stile del foglio. I cinque cambi
successivi danno invece sempre lo stesso conteggio, tutti i 1.911 widget.

Per `tone`, `design.set_text` su un'etichetta lucidata ha prodotto esattamente una chiamata `unpolish` e una `polish`
sulla sola etichetta. Per `primary`, la stessa sequenza esplicita ha toccato solo il pulsante. La sola
`setProperty`, nel percorso misurato, non ha diffuso `StyleChange` ad altri widget. Il conteggio diretto è quindi un
widget, non l'intera finestra.

## Selettori più costosi

La scansione iniziale aveva dato anche `QSlider:horizontal` come candidato. Le ripetizioni successive lo hanno
smentito: la mediana dell'effetto è praticamente nulla. Questi sono i risultati confermati nella lucidatura completa.

| Selettore rimosso | Coppie | QSS intero, mediana | Senza, mediana | Effetto mediano |
|---|---:|---:|---:|---:|
| `QScrollArea` | 21 | 56,648 ms | 47,352 ms | **9,320 ms** |
| `QSlider:horizontal` | 21 | 56,790 ms | 57,125 ms | 0,000 ms |
| `QToolButton#rowfix` | 15 | 57,708 ms | 57,215 ms | 0,740 ms, rumoroso |

`QScrollArea` è quindi l'unico selettore con un costo rilevante e ripetibile trovato qui: circa il 16 % del ciclo di
lucidatura in questa misura, ma circa l'1,6 % del tempo mediano di `setStyleSheet`. Gli altri candidati della prima
scansione erano sotto 1 ms o variavano segno fra le ripetizioni. Nessun selettore spiega da solo i 595 ms.

## Che cosa fare

Nessuna modifica al codice in questo punto. Il QSS è piccolo in caratteri rispetto al suo costo di applicazione e il
disegno raster ordinario paga solo circa un decimo di millisecondo. Le cause già misurate altrove, impaginazione,
grafici, 3D e presentazione sullo schermo, restano candidate più forti per la fluidità ordinaria.

Se si vuole lavorare sul cambio di tema, il bersaglio da misurare è il numero di widget e le cascate di
`StyleChange`, non una riduzione indiscriminata delle regole. Prima di proporre una modifica a `QScrollArea` servono
misure sullo schermo vero e una spiegazione del suo costo dentro Qt; qui non ci sono elementi per una correzione
sicura. Le misure sullo schermo reale restano a Claude.
