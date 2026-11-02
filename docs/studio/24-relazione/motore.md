# Il motore di impaginazione della relazione

Oggi: HTML composto da `report_chapters.py` -> `QTextDocument` (`report.py`, `_layout`) -> `QPdfWriter`, copertina e
testatine dipinte con QPainter, immagini da matplotlib. Il disegno di A e B chiede: righe di tabella e figure intere,
griglia a due colonne, numeri grandi, intestazioni di tabella ripetute, pagina «n di N», fonti in colonna. C chiede
anche sillabazione e giustificazione buona.

## Prove fatte (02/11/2026, PC di Daniel, offscreen)

Stesso contenuto per tutti: 40 righe di tabella di 3-4 linee ciascuna, Inter da `data/fonts`, A4 con margini 2 cm.
Script e risultati in `build/claude-r07/FR-prova-*.py`, `.pdf`, `-p1.png`, `-p2.png` (cartella fuori da git);
copia degli script e del confronto al salto pagina in `prove/` qui accanto (`prove/FR-prova-confronto-salto-pagina.png`:
a sinistra QTextDocument, al centro WebEngine, a destra Typst; sopra la fine di p. 1, sotto l'inizio di p. 2).

| Motore | Tempo | PDF | La riga a cavallo delle pagine | Peso aggiunto al programma |
|---|---|---|---|---|
| QTextDocument (oggi) | 119 ms, 3 pagine | 31 kB | **spezzata**: riga 15 con due linee a p. 1 e una a p. 2 (intestazione ripetuta, questo sì) | 0 |
| Qt WebEngine, `printToPdf`, `tr { break-inside: avoid }` | 1.810 ms dall'import (app pronta a 268 ms) | 39 kB | intera: riga 11 a p. 1, riga 12 a p. 2 | `Qt6WebEngineCore.dll` 195 MB nel venv; wheel 132 MB (nota in `requirements.txt`) |
| Typst 0.15 (`typst` da PyPI, venv di prova) | import 6-8 ms; prima compilazione 60-98 ms, seconda 10-12 ms | 69 kB con Inter incorporato | **spezzata al primo colpo** (Typst 0.11+ spezza le righe), intera con una riga di stile: `#show table.cell: it => block(breakable: false, it)` | wheel 29,4 MB, 60 MB installato |

Non provati (pesati soltanto, `pip download`): ReportLab 5.1.0 (2,0 MB, BSD); WeasyPrint 70.0 (0,33 MB + pydyf,
tinycss2, cssselect2, pyphen 2,1 MB, fonttools, Pillow, **più Pango, HarfBuzz e fontconfig di sistema**: su Windows
vanno portati a mano, è il suo punto debole noto). QPainter con impaginatore nostro: nessuna prova, è lavoro, non
rischio.

## Confronto (voti 1-5, 5 è il meglio; «lavoro» 5 = poco lavoro)

| Motore | Tipografia | Righe e figure intere | Peso e licenza (GPL) | Windows e Flatpak | Lavoro | Note |
|---|---|---|---|---|---|---|
| **QTextDocument** (oggi) | 2 | 2 | 5 | 5 | 4 | sottoinsieme CSS povero: niente griglia, colonne, sillabazione, `break-inside`; le righe si spezzano (misurato); il nostro `keep_together` regge solo blocchi, non celle. A è fattibile con tabelle per la griglia, C no |
| QPainter + impaginatore nostro | 3 | 5 | 5 | 5 | 1 | tutto a mano: flusso del testo, celle, vedove, indice; mesi di lavoro per arrivare dove Typst è già |
| Qt WebEngine `printToPdf` | 4 | 4 | 1 | 3 | 3 | CSS pieno, ma niente `counter(page)` nelle testatine (Chromium): pagine «n di N» da fare in JS; +300 MB nel pacchetto Windows, escluso apposta da `requirements.txt`; su Flatpak il runtime KDE e la BaseApp PySide lo portano già (dedotto, non verificato) |
| ReportLab | 3 | 5 | 5 | 5 | 2 | BSD, puro Python; tabelle che si spezzano solo fra le righe, `KeepTogether`; API a oggetti (platypus): riscrivere i 1.049 righe di `report_chapters.py`; giustificazione e sillabazione così così |
| WeasyPrint | 4 | 5 | 3 | 2 | 3 | tiene l'HTML di oggi; CSS paged media completo (testatine con `running()`, `counter(page)`, `break-inside`); ma Pango su Windows (installatore GTK o MSYS2, 30-40 MB, trappole di PATH); su Flatpak va da sé |
| **Typst** | 5 | 5 | 4 | 5 | 2-3 | Apache-2.0 (compilatore e `typst-py`), un wheel senza librerie di sistema, Windows x64, Linux x64 e aarch64 (da PyPI, non provato qui su ARM); sillabazione italiana, giustificazione, numeri tabulari, `table.header` ripetuto, testatine e «n di N» nativi, figure numerate, grafici disegnabili in Typst stesso; 10-100 ms a compilazione (anteprima viva); la riscrittura di `report_chapters.py` è da HTML a markup Typst, stessa taglia |

## Raccomandazione

**Typst**, per tre ragioni misurate: le righe restano intere con una riga di stile, il PDF esce in 10-100 ms con il
carattere incorporato, non porta librerie di sistema (un wheel da 29 MB, contro i 300 MB di WebEngine). Il costo è
la riscrittura dei capitoli (da stringhe HTML a stringhe Typst: stesso schema, stesse funzioni `table()`,
`facts()`, `figure()`), e un pezzo di `report.py` sparisce: niente `_layout`, `_chapter_pages`, `keep_together`,
disegno pagina per pagina; l'**anteprima** si fa dal PDF con `QPdfDocument` (già dipendenza, lo usano gli allegati) e
l'indice con i numeri di pagina lo fa Typst (`outline`). I grafici si disegnano in Typst (rettangoli e testo) o
restano PNG di matplotlib in una prima fase. Tutti e tre i bozzetti sono fattibili.

Se Daniel non vuole dipendenze nuove: **QTextDocument con il bozzetto A** (griglia a tabelle, colonna delle fonti,
numeri grandi) e per le righe spezzate una misura a monte: spezzare noi le tabelle lunghe in blocchi misurati
(`blockBoundingRect` della prima cella di ogni riga, salto pagina prima della riga che non ci sta), come già fa
`keep_together` per le figure. Funziona, ma è una stampella da tenere a ogni cambio di stile.

Scartati: WebEngine (peso, già escluso dal progetto), WeasyPrint (Pango su Windows), QPainter nostro (mesi),
ReportLab (stesso lavoro di Typst con metà del risultato tipografico).

## Che cosa serve per decidere (verificato / dedotto)

- Verificato: i tempi, i pesi e le foto della tabella; il wheel Typst si installa e compila su questo PC (venv di
  prova nello scratchpad, niente nel progetto).
- Dedotto, da verificare prima di implementare: wheel Typst per Linux aarch64 e il suo funzionamento nel Flatpak
  (`python3-requirements.json` con il wheel come sorgente); la resa dei glifi dei segni delle verifiche (✔ ⚠ ✘) in
  Typst con Inter (Typst cerca da solo nei font indicati: va aggiunto un font con i simboli, es. Noto Sans Symbols 2,
  OFL).
