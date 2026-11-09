# Controlli Quick: API

04/11/2026. Import: `import Meridiana.Controls as M`.

```python
from meridiana.quick.backend.controls import install_controls

theme = install_controls(engine, theme=None)
```

Installare prima di caricare QML. Il servizio aggiunge Theme e provider SVG una sola volta per motore,
conserva i riferimenti Python e restituisce ThemeTokens. I colori, font e misure seguono il tema vivo.
Le icone provengono da `ui.icons.svg`, senza copie. Il prefisso `symbol:` usa `ui.symbols.paint`:
`symbol:fail`, `symbol:warn`, `symbol:info`, `symbol:ok`, oppure i nomi della libreria simboli.
Questi simboli mantengono i loro colori di stato, seguono il tema chiaro/scuro; `Icon.inactive`
(o enabled=false) li rende grigi. Nessuna ricostruzione locale degli SVG. Le dimensioni sono logiche: Icon richiede al provider
la risoluzione fisica del monitor, senza scalare due volte il layout.

## Testo e comandi

| Tipo | API |
|---|---|
| Label | `text`, `textStyle` dal catalogo Theme.text, `condensed`; altre proprieta Qt Text. PlainText di default. |
| Icon | `iconName` oppure alias `name`, `color`; dimensioni implicite Theme.icon.CONTROL. |
| Button | `text`, `iconName`, `tip`, `flat`, `active`; API Qt Button, `clicked()`, checkable/checked. |
| ToolButton | API Button, `mode`: under/beside/icons; font condensato, misure Theme.bar. |
| SplitButton | `text`, `iconName`, `tip`, `mode`, `model` di `{text, icon, enabled}`; `clicked()` principale e `chosen(index)` dal menu. `menu` espone open/close. |
| Menu | API Qt Menu, contenuto dichiarativo MenuItem; larghezza secondo le voci, popup nello stesso QuickWindow. |
| MenuItem | API Qt MenuItem, `iconName`, checkable/checked, triggered(); segno di spunta condiviso con CheckBox. |
| ToolTip | `text`, `visible`, API Qt ToolTip; sola opacita, 90/60 ms in ControlMetrics. Attesa iniziale Theme.motion.DWELL, passaggio immediato dopo il primo. |

I flag groupHovered/groupMember di Button sono interni al pulsante diviso R364.
La parte sotto il puntatore ha uno stato piu evidente della parte accanto, senza divisorio.
I menu e il dialogo non generano una seconda finestra di sistema.

## Campi e selezioni

| Tipo | API |
|---|---|
| TextField | API Qt TextField; `invalid` segnala errore. Placeholder disegnato dal controllo. |
| NumberField | `value`, `minimum`, `maximum`, `decimals`, `unit`, `stepSize`, `valueEdited(value)`. |
| ComboBox | API Qt ComboBox; model di stringhe o ruoli, textRole/valueRole, activated(index). |
| CheckBox | API Qt CheckBox, anche checkState parziale e tristate. |
| Segments | `model` array di `{text,id}` oppure stringhe; `currentIndex`, `activated(index)`; frecce, Home, End. |
| Tabs | Stessa API Segments, altezza Theme.size.TAB e margine Theme.space.XS su quattro lati. |

NumberField usa il locale italiano: virgola decimale e raggruppamento locale. Invio e fine modifica
confermano solo valori validi; il testo non valido resta visibile con bordo errore e non altera value.
Le frecce incrementano/decrementano entro i limiti. Nessun incremento da ruota involontaria.
Le etichette di scopo e Accessible.name/description dei campi sono responsabilita del chiamante.

Segments misura ogni parola e aggiunge 12 px per lato (Theme.space.L), come ui/segments.py.
Alla larghezza implicita ogni segmento segue il testo; con piu spazio distribuisce l'eccedenza,
con meno spazio riduce le larghezze in proporzione. La selezione scorre interamente in QML, senza callback Python
per fotogramma. `currentIndex` segue una selezione interna finche il chiamante non lo imposta:
se e collegato a un modello esterno, `activated(index)` deve aggiornare quel modello. Il controllo
non assegna currentIndex e non spezza il binding. Per un indice iniziale non controllato usare `Component.onCompleted: choose(1)`. Con meno movimento la durata segue Theme.motion e diventa zero.

## Contenitori

| Tipo | API |
|---|---|
| Card | `title`, `closable`, `closeTip`, `closed()`. Default `content` aggiunge figli a `contentItem` entro i margini; `headerExtra` aggiunge elementi al Flow prima della croce. |
| Section | `title`, `collapsible` (true), `expanded` (true), `toggled(expanded)`; default `content` in una Column. Click e Spazio sul titolo aprono/chiudono con altezza e opacita animate. |
| Badge | `text`, `tone` nome colore Theme.colors. |
| EmptyState | `title`, `description`, `iconName`, `actionText`, `triggered()`. |
| Dialog | API Qt Dialog, `title`, `acceptText`, `rejectText`, accepted()/rejected(); contenuto/default Qt. Modale, Esc annulla. Pulsanti vuoti nascosti. |
| ProgressBar | API Qt ProgressBar: from/to/value, indeterminate. Anche l'indeterminato rispetta meno movimento. |
| ScrollBar | API Qt ScrollBar; attaccare `T.ScrollBar.vertical: M.ScrollBar {}` al Flickable. Overlay, visibile solo se size < 1. |
| SplitHandle | Per `SplitView.handle`; `orientation` indica il verso della linea (Qt.Vertical predefinito). Trascinamento gestito dal SplitView Qt. |

Section.expanded segue lo stato interno di default. Se collegato dall'esterno, gestire `toggled(value)`
aggiornando il modello esterno, come per Segments. Il contenuto resta istanziato quando chiuso.

Card.closed() notifica: il chiamante decide se nascondere o rimuovere la scheda.
Dialog richiede testi tradotti espliciti per i pulsanti: non usa etichette Qt di sistema.

## Elenchi, albero e tabella

`List`: model di stringhe, oggetti o QAbstractListModel; `textRole` (text), `iconRole` (icon),
`currentIndex`, count in lettura, `activated(index)` e `view` per accesso al ListView.
Click, frecce, Home/End e Invio selezionano; le righe sono virtualizzate.

`Tree`: modello annidato di `{id, text, children?}` con id stabili e unici; `expandedIds`, `currentIndex`,
count in lettura, `activated(node)`. Freccia destra espande, sinistra richiude, su/giu selezionano;
il chevron e il doppio click espandono. Un QAbstractItemModel gerarchico va adattato al modello annidato.
Lo scorrimento e virtualizzato; l'appiattimento delle sole diramazioni aperte avviene in QML.

`Table` (R394): model di oggetti oppure QAbstractListModel con ruoli, columns di
`{title, key, unit?, weight?, numeric?}`, `total` come oggetto con le stesse chiavi, oppure null.
I numeri arrivano gia formattati dal chiamante: nessuna precisione numerica viene persa dal controllo.
Le colonne occupano tutta la larghezza in proporzione a weight (predefinito 1).
`currentIndex`, count in lettura, `rowActivated(index)`, `view` come ListView.
Click, frecce, Home/End e Invio selezionano una riga. Testata e totale sono fissi;
solo separatori orizzontali, nessun numero riga/angolo, scrollbar sovrapposta quando serve.
Con model vuoto spariscono testata e totale: `emptyTitle`, `emptyDescription`, `emptyActionText`
e segnale `emptyTriggered()` compongono lo stato vuoto con comando.
La prima versione e di sola lettura, con selezione singola, senza ordinamento incorporato.
Un QAbstractTableModel va adattato a ruoli per riga oppure a un array.

## Galleria e prove

`python -m meridiana.quick.gallery` apre la galleria interattiva.
Opzioni: `--shot percorso.png`, `--theme light|dark`, `--large-text`, `--width`, `--height`,
`--state normal|hover|pressed|focus|tooltip|menu|dialog|empty|disabled|collapsed`.
`--matrix build/quick-foto/controlli/matrice` genera 48 immagini in processi separati:
DPR 1/2, chiaro/scuro, dieci stati a 1366x900, normali a 1600x960 e 1920x1080.
La cattura impone la dimensione minima richiesta e verifica quella ottenuta: Windows altrimenti puo ridurre
una finestra piu grande del desktop disponibile. Il vincolo e applicato solo con --shot.
A DPR 2 usa anche il testo grande. Tutti i testi della galleria sono in Python e passano da i18n;
le stringhe nuove hanno un fallback italiano locale alla galleria fino all'aggiornamento cataloghi Linux.

`tests/quick/sistema/test_controls.py`: eventi reali, focus, menu, dialogo, numero, albero,
modello Python vivo, trascinamento divisore, pixel hover R364 e totale invariato R394.

## Passata di fedeltà r13: aggiunte compatibili

I nomi e i segnali precedenti restano disponibili. Le misure seguono il riferimento Widgets.
`Tabs` misura 32 px (24 di linguetta e 4 sopra/sotto); `Theme.size.TAB` rimane 36 per le fasi.

- `Slider`: API Qt Slider, anche orientamento verticale, tastiera e trascinamento. La ruota
  agisce soltanto col focus. Pista e maniglia sono quelle del QSlider Widgets del sole.
  `pageStep` aggiunge il passo del clic sulla pista e di Pagina su/giù; Home/End vanno agli estremi.
- `CountPill`: `level` (`fail`, `warn`, `info`, `ok`), `text`, `tip`; API Qt Button con
  `checkable=true`, `checked`, `clicked`. Disegno P3, larghezza riservata per due cifre,
  zero attenuato. Colori e misure provengono da `ui/status_pill.py`.
- `Badge.state`: `done`, `stale`, `todo`, `unavailable`, `planned`, oppure vuoto. `tone`
  resta disponibile. Tipografia CONTROL, raggio 6, come le etichette di stato Widgets.
- `MenuSeparator`: separatore orizzontale nello stesso menu. `MenuItem.shortcutText`
  mostra la scorciatoia a destra; in assenza di valore esplicito legge Action.shortcut o
  la parte di text dopo un tab. L'attivazione della scorciatoia resta compito dell'Action.
  `MenuItem.tip` aggiunge il tooltip. I sottomenu si dichiarano come figli `Menu` con `title`.
- `SplitButton.mainEnabled`: disabilita il comando lasciando disponibile il menu;
  `active` segue il comando. Anche il tasto destro apre il menu.
- `Section.helpId`, `helpTip`, `helpRequested(helpId)`: il «?» separato dal titolo.
  `nested` è ricavato dagli antenati Section, e può essere specificato: sezione annidata
  senza un'altra scheda, titolo su una linea. `collapsible=false` mantiene leggibile il titolo.
- `List.framed` e `Tree.framed`: cornice autonoma (default true); false quando la cornice
  è già del contenitore. `rowHeight` può essere specificata per righe specializzate.
- `Icon.dimDisabled` (true): i simboli di stato possono mantenerne i colori anche quando
  il comando è disattivato. `inactive` resta disponibile.
- `Dialog.acceptOnReturn` (true): Invio conferma, oppure annulla se il pulsante Annulla
  ha il focus. Mettere false se il contenuto deve ricevere Invio, per esempio un editor
  multilinea. Un contenuto che possiede già il focus lo conserva all'apertura.
- `TextField`: Tab seleziona il testo; uscendo dal campo stretto torna visibile l'inizio
  del testo. La selezione con il puntatore e lo scorrimento durante la modifica restano attivi.

`ProgressBar` riusa le due superfici statiche Fusion dei Widgets, ciascuna divisa
in estremità e centro per mantenere nitidi i pixel anche a DPR 2. Il tratto mobile
e la sua animazione rimangono in Quick: nessuna chiamata Python durante i fotogrammi.
Le immagini seguono tema, abilitazione e rapporto di pixel dello schermo.

I tooltip riusano `ui/popups.tip_html` e le misure di QTextDocument: massimo 340 px,
8 px orizzontali e 6 verticali. Il punto di comparsa è quello del puntatore, congelato
all'apertura; le transizioni restano esclusivamente di opacità secondo R379.
Il testo usa il rasterizzatore nativo anche in Quick. Il provider delle icone riusa inoltre
`symbols.sign` per la spunta e la geometria delle frecce di `ui/theme.py`.

Confronto riproducibile: `PYTHONPATH=tests;src python -m quick.controlli.capture_pairs`.
`--theme dark`, `QT_SCALE_FACTOR=2`, `--large`, `--controls` e `--states` restringono la matrice.
Indice al 200 % in `docs/quick/confronto/controlli/index.html`.


## Sfumature comuni, R161 e R192

`EdgeFades`: `flickable` è il Flickable/ListView sorvegliato; `ground` è il colore
sottostante (default `Theme.colors.panel`); `page=false`, `table=false`.
La variante normale conserva gli angoli tondi; `page=true` usa PAGE_STOPS e bordi
rettilinei; `table=true` usa STOPS su un viewport rettilineo. Le costanti provengono
da `ui/fades.py`, senza nuove scelte di colore o intensità.

Dichiararlo come fratello del Flickable, dentro il contenitore della sua area visibile:

```qml
Item {
    Flickable { id: viewport; anchors.fill: parent; clip: true }
    M.EdgeFades { flickable: viewport; page: true; ground: Theme.colors.panel }
}
```

Non metterlo nel contenuto che scorre. Gli anchor seguono il viewport; il chiamante
riserva i margini della pagina (AIR di `ui/fades.py`) e lascia fuori cornici e barra.
Per la tabella usare `ground: Theme.colors.card`. List, Tree e Table lo applicano già.
Le altre pagine devono agganciarlo ai propri Flickable: questa aggiunta non modifica
automaticamente i contenitori degli altri moduli. Non intercetta clic, tasti o ruota.
Le immagini cambiano solo per misura, tema e DPR; lo scorrimento non chiama Python.
