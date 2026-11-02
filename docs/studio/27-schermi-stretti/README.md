# Studio 27: Meridiana su schermi stretti e piccoli

Opus OB, 02/11/2026, ramo `r10-barra`, R334. Daniel: «un modo affinché Meridiana si veda bene su schermi stretti o più piccoli (tipo
tablet o monitor tenuti in verticale). Riposizionamenti dinamici? Versioni dei tasti e delle schede compatti? Tipo lato sinistro
che si vedono solo più simboli? Va ragionato secondo le regole di una buona UX». Solo studio: nessun codice del programma.

- `bozzetti.html`: tabella delle soglie e finestre intere della proposta (Modellazione e Impianto a 1366 x 768, 1080 x 1920,
  800 x 1280, più 960 x 1040 con la scheda aperta). `?z=1` al 100 %, `?only=m800` una sola.
- `foto/A...G-*.png`: **come appare oggi**, finestra vera offscreen. `foto/proposta-*.png`, `foto/z-soglie.png`: i bozzetti.
- `misura.py`, `misure.json`: le misure, ripetibili. `genera.py`: i bozzetti. Barra dallo studio 26.

Convenzione: **[V]** verificato (come), **[D]** dedotto, **[N]** non verificato.

## 1. I casi e le misure di oggi

[V] `misura.py`: la `MainWindow` vera (`tests/_setup.py`), progetto di prova Capannone, in italiano, tema chiaro, in un processo per
caso con uno schermo virtuale della stessa misura (le prime larghezze dei pannelli dipendono dallo schermo). Fase Modellazione,
pixel logici. La vista 3D offscreen non disegna il modello.

| Caso | Barra | Area centrale | Pianta | Colonne (min) | Verifiche | Cosa si rompe |
|---|---|---|---|---|---|---|
| A 1920 x 1080 | parole, 69 | 1204 x 675 | 652 x 653 | 320 e 380 | 1532 x 247 | niente: è il riferimento |
| B 1366 x 768 portatile | icone, 47 | 810 x 385 | 435 x 363 | 240 e 300 | 1058 x 247 | **altezza**: le Verifiche prendono il 32 % della finestra; niente parole con 880 px liberi nella barra |
| D 1280 x 800 tablet | icone, 47 | 724 x 417 | 386 x 395 | 240 e 300 | 972 x 247 | come B |
| C 1080 x 1920 verticale | parole, 69 | 524 x 1515 | **186 x 1493** | 240 e 300 | 772 x 247 | **pianta e 3D affiancate in un'area alta il triplo della larghezza** |
| F 960 x 1040 metà schermo | parole, 69 | 652 x 635 | 626 x 613 | linguette, 300 | 652 x 247 | Impianto: il gruppo **Stringhe** sparisce nel troppo-pieno; 3D via da solo |
| E 800 x 1280 tablet | parole, 69 | 520 x 875 | 494 x 853 | linguette, 284 | 520 x 247 | nomi delle fasi tagliati («Modella…», «Im…», «Co…»), variante «B…»; **Precisione** e **Stringhe** spariscono |
| G 683 x 728 metà portatile | icone, 47 | 438 x 345 | 412 x 323 | linguette, 272 | 438 x 247 | tutto stretto e basso, Verifiche illeggibili («128 mod…») |

Altre misure [V]:
- **Minimi di oggi**: la finestra non scende sotto 778 x 565 in Modellazione se larga più di 1000; nello stato stretto (sotto 1000,
  `NARROW`) 624 x 565 in Modellazione, 469 x 543 in Impianto, 612 x 543 nelle altre. Il minimo cambia con la fase: stretta su
  Impianto a 500 px, passando a Modellazione la finestra verrebbe allargata [D].
- **Riga delle fasi**: chiede 788 px, più «File» e variante: circa 960 [D, somma]. A 960 è già a 777 su 788.
- **Barra**, larghezza che chiede: parole Modellazione 799, Impianto 950 più la striscia (il commento in `phases.py` dice 1400),
  Relazione 549, Producibilità 333; icone 442, 512, 280, 169. Il modo lo decide **solo l'altezza** (`_fit_bars`, `LOW_WINDOW` 900):
  a 800 x 1280 le parole restano e chiedono 799 su 756 disponibili, mentre le icone ne chiederebbero 442. Per questo Precisione sparisce.
- **Troppo-pieno**: quello di `QToolBar` esiste ma è un puntino quasi invisibile in fondo alla barra (`foto/F-960x1040-plant.png`).
- **Sotto 1000 px** (`_adapt`): i pannelli diventano linguette, resta la pianta sola.
- **Bersagli**: pulsanti visibili sotto i 40 px: 64 su 75 con le parole, 75 su 75 a icone sole (stesso criterio dello studio 21).
- **Griglie**: i riquadri passano già da soli a due colonne (`E-800x1280-production.png`, `Tiles`, R309): nessun lavoro.

Perché si rompe, in una riga: **ci sono due sole risposte, una per l'altezza della barra e una a 1000 px di larghezza, e nessuna
guarda la forma dello spazio che resta**. Il verticale e il portatile hanno il problema opposto e oggi nessuno dei due è visto.

## 2. I principi

1. **Priorità del contenuto.** Ogni fase ha ciò che non deve mai sparire (tabella sotto). Si riduce per primo ciò che si guarda meno.
2. **Soglie sulla larghezza disponibile, non sul dispositivo.** Una finestra a metà di un 4K è un tablet. Nessun «se è un tablet».
3. **Prevedibilità.** Lo stesso comando resta nello stesso posto e nello stesso ordine: fasi, gruppi, strumenti non si riordinano mai.
   Si tolgono da destra, sempre nello stesso ordine; una colonna che si riduce tiene l'ordine delle sue voci.
4. **Mai a sorpresa.** Un cambio solo quando si passa una soglia, con 40 px di isteresi per non oscillare, non durante un
   trascinamento (attesa di 150 ms, come `relayout_timer`). Quando accade, un messaggio nella barra di stato con «Annulla» per
   qualche secondo (il meccanismo di R294 c'è già).
5. **Divulgazione progressiva.** Il compatto mostra simbolo e conteggio; un clic mostra tutto. Nessun comando esiste solo nel largo.
6. **Scelta dell'utente che prevale e si ricorda.** Le disposizioni si salvano per forma (larga, media, verticale): girare il monitor
   riporta la disposizione lasciata in verticale. Una scheda «Tieni aperta» resta tale.
7. **Transizioni.** Regola del sistema grafico: mai muovere una pagina intera. Le schede sopra scorrono in `Motion.NORMAL`; il cambio
   di disposizione è una dissolvenza con `motion.Veil`. Zero con «riduci animazioni».
8. **Tipografia invariata.** Le dimensioni del testo non cambiano con la finestra (R133 resta all'utente). Compatto vuol dire meno
   cose, non cose più piccole.
9. **Bersagli del tocco.** Quello che nasce nuovo (striscia 44 px, maniglia del foglio) nasce già da dito. Il resto è il lotto tocco.

| Fase | Mai via | Si riduce | Prima a ridursi |
|---|---|---|---|
| 1 Modellazione | pianta, strumenti Modifica e Disegna, proprietà della selezione a un clic, riga delle fasi | 3D, Aiuto | Verifiche, albero |
| 2 Impianto | pianta, Pannelli (Posa), stato stringhe a parole | albero, gruppi secondari della barra | Verifiche, striscia di stato |
| 3 Producibilità | Calcola, riquadro chiave, grafico | Dati | Verifiche, Aiuto |
| 4 Consumi | grafico, Base e Curva | Dati | Verifiche, Aiuto |
| 5 Bilancio | Calcola, riquadri, grafico | Dati | Verifiche, Aiuto |
| 6 Relazione | anteprima, Esporta | Elaborati | Verifiche, Aiuto |

## 3. Le proposte

Voti da 1 a 5: beneficio, costo (5 = poco), prevedibilità. Costo in Qt Widgets: XS mezza giornata, S un giorno, M due o tre, L
una settimana [D, stime]. In Quick: [D], per un'interfaccia che non è ancora scritta.

| | Proposta | Benef. | Costo | Prev. | Tot. | Pro | Contro | Widgets | Quick |
|---|---|---|---|---|---|---|---|---|---|
| V1 | **Pianta e 3D una sopra l'altra** quando l'area è più alta che larga | 5 | 5 | 4 | **14** | a 1080 x 1920 la pianta passa da 186 a circa 500 px di larghezza | cambia l'orientamento del divisore | XS: `split.setOrientation` in `_adapt` | XS |
| B1 | **Il modo della barra guarda anche la larghezza** | 4 | 5 | 5 | **14** | Precisione e Stringhe tornano; nessun disegno nuovo | a parole sparite, servono i suggerimenti (ci sono) | XS: `_fit_bars` | XS |
| H | **Verifiche chiuse sotto i 900 di altezza**, conteggio nella barra di stato | 5 | 4 | 4 | **13** | a 1366 x 768 la pianta da 363 a circa 590 di altezza (+60 %) | le verifiche si vedono meno: resta il segno col numero | XS chiudere il pannello; S scheda sopra | S |
| V2 | Una vista alla volta sotto i 480 px (i pulsanti Pianta, 3D, Entrambe ci sono già) | 3 | 5 | 5 | 13 | c'è quasi | non si vedono insieme | XS, oggi `auto_plan` | XS |
| F | **Riga delle fasi compatta**: numeri, titolo della corrente | 3 | 5 | 4 | 12 | sparisce «Im…»; la linguetta che scorre già interpola la larghezza | non si legge il nome delle altre: suggerimento, Ctrl+numero | S: `tabSizeHint`, `_draw` | S |
| B2 | **Parole accanto alle icone, senza titolini**, barra 31 px, per chi è basso e largo | 4 | 4 | 4 | 12 | a 1366 si recuperano le parole e 16 px; legge chi non ricorda le icone | un modo in più della barra | S: `ToolButtonTextBesideIcon` in `set_mode` | S |
| S | **Foglio in basso in verticale**: pannelli a linguette in basso | 5 | 3 | 3 | 11 | sfrutta l'altezza; form larghi | i pannelli cambiano lato | M con i dock veri in basso e tabificati; la maniglia è il separatore. Tre altezze a scatto dopo | M, dock da scrivere comunque |
| C1 | **Colonna che diventa striscia di simboli**, scheda sopra al clic | 4 | 2 | 4 | 10 | è l'idea di Daniel; +196 px alla vista; simbolo e conteggio | due stati per ogni pannello; la scheda copre la vista | L: `Rail` nuovo, scheda sopra la vista, passaggio dock/scheda | M: `Drawer`, naturale |
| B3 | Gruppi in tendina con il loro titolo, poi troppo-pieno | 3 | 3 | 4 | 10 | sotto i 522 px nessun gruppo si perde | serve solo molto stretti | M: layout della barra proprio | S |
| C2 | Colonne a scomparsa (nascoste, nessuna striscia) | 3 | 4 | 2 | 9 | c'è quasi (Ctrl+0, pulsanti delle schede) | sparisce anche l'informazione: si deve sapere | XS | XS |
| G | Griglie di riquadri | - | - | - | - | già fatto (R309) | | 0 | da rifare |
| T | Tipografia | - | - | - | - | principio 8, nessun lavoro | | 0 | 0 |

**Striscia di simboli: uno per pannello o uno per sezione?** Daniel diceva «lato sinistro che si vedono solo più simboli». Propongo una
voce per sezione dell'albero (Sito, Edifici, Sottocampi, Esclusioni) con il conteggio: dice qualcosa già da chiusa, mentre un simbolo
«Progetto» unico è un pulsante e basta, e doppierebbe i pulsanti delle schede nella barra di stato. La colonna di destra, se si
riduce, ha una voce per scheda (Proprietà, Aiuto). Da decidere.

## 4. Qt Widgets o Qt Quick

R334 vale in entrambi. **Non cambia**: principi, priorità, soglie, tabella delle fasi: decisioni di UX. **Cambia** [D]:
- In Quick le animazioni delle schede sono gratis e sulla scheda video, gli stati si dichiarano, `Drawer` è la scheda sopra. In Widgets
  una scheda che scivola costa e i dock non si animano (`dock_motion.py` lavora con fotografie).
- In Quick i dock non esistono: spostare i pannelli col trascinamento va riscritto, e quindi anche il foglio in basso. In Widgets lo
  si ottiene già coi dock.
- **Per non rifare il lavoro due volte**: la decisione in una funzione pura, senza Qt, provabile con le tabelle della `bozzetti.html`,
  `arrangement(larghezza, altezza, fase, scelte) -> disposizione` (per esempio `meridiana/arrangement.py`); Widgets o Quick la eseguono soltanto.
  Se si passa a Quick presto, conviene fermarsi al passo 2 sotto e non costruire C1 in Widgets.

## 5. Raccomandazione a passi

1. **Subito, mezza giornata o un giorno, senza nessun elemento nuovo: V1, B1, H (la versione che chiude il pannello).** Il miglior
   rapporto in assoluto: tre righe in `_adapt` e `_fit_bars`, e il verticale e il portatile cambiano faccia. Prova: `misura.py` rifatto.
2. **Poi, due giorni: F, B2, funzione `arrangement`, isteresi, disposizioni ricordate per forma, messaggio con Annulla.** Da qui si è a
   posto da 1100 px in su e in verticale il minimo è decente.
3. **S, il foglio in basso, coi dock veri.** Due o tre giorni. Chiude i casi 1080 x 1920 e 800 x 1280.
4. **C1, la striscia di simboli con la scheda sopra.** Una settimana. Solo per la fascia fra 800 e 1100 px: ha senso se Daniel lavora
   davvero a metà schermo. Se si va verso Quick, aspettare.
5. **B3**, gruppi in tendina, quando serve sotto i 522 px. Probabilmente mai su un portatile.
6. **Il tocco è un lotto a sé**: gesti, bersagli, densità, assenza di passaggio in `docs/studio/21-arm-tablet/README.md`, sezione 4.
   Questo studio ne è il presupposto ma non lo sostituisce: una finestra che si dispone bene non fa ancora funzionare le due dita.

## 6. Non verificato

- I bozzetti sono HTML: larghezze e altezze delle proposte sono tarate sulle misure vere ma non provate in Qt. I numeri «circa 590» e
  «circa 500» vengono dal disegno.
- Orientamento verticale del divisore con la vista 3D (`QQuickWidget`): non provato. Sul 4K la vista 3D pesa sull'intera finestra
  (`docs/prestazioni`): una vista più grande può pesare di più [D].
- Offscreen non c'è il gestore delle finestre: su Windows la barra del titolo toglie circa 32 px, e l'altezza utile è ancora minore di
  quelle della tabella [D]. Nessuna prova su tablet o monitor veri, né sul Dell.
- Le foto di oggi sono su un progetto piccolo: con molti oggetti albero e proprietà sono più lunghi, non più larghi.
- Le stime di costo sono mie.
