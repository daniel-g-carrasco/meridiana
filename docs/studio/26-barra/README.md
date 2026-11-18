# Studio 26: la barra degli strumenti e i pulsanti raggruppati

Opus OB, 02/11/2026, ramo `r10-barra`, R333. Daniel: «dei draft di come rifare i vari pulsanti nella barra degli strumenti in
alto, in particolare i tasti raggruppati in unico». Solo studio: nessun codice del programma.

- `bozzetti.html`: autonoma, si apre nel browser. Sette disegni del pulsante raggruppato (oggi più sei) sulle barre vere delle sei
  fasi, ciascuno nei cinque stati, in altezza piena e bassa; il resto della barra; la proposta intera, anche in scuro. Le barre
  sono vive: passaggio, clic sulla freccia, tasto destro, scelta di una voce. `?only=g2` (g0...g6, r, p) mostra una sezione.
- `foto/`: le sezioni fotografate con Chrome headless, 1620 px, guardate una per una.
- `estrai.py`, `barre.json`: parole, tasti, icone e gettoni letti da una finestra vera, offscreen, in italiano.
  `barra_html.py`, `genera.py`, `foto.py`: disegnano e fotografano. Servono anche allo studio 27.

Convenzione: **[V]** verificato (come), **[D]** dedotto, **[N]** non verificato.

## 1. Com'è oggi

[V, letto in `ui/phasebar.py`, `phases.py`, `ui/theme.py`] `ToolMenuButton` (R306): clic sull'icona esegue l'ultima voce; la
freccetta in alto a destra (`ARROW` = 16 px, sopra la riga della parola) o il tenere premuto aprono il `QMenu`. Larghezza ferma
sulla parola più lunga. La faccia cambia con `use()` a **ogni** `triggered` dell'azione, quindi anche per un tasto o da un altro
menu, e `_still_usable` la cambia **da sola** quando il comando si spegne (perché un `QToolButton` spento non apre il menu).

Le famiglie non sono dello stesso tipo, ed è il punto del disegno [V, `phases.py`, `shortcuts.py`; il tipo è una mia lettura, D]:

| Pulsante | Voci | Che cosa sono |
|---|---|---|
| Edificio | Edificio, Modello, Da IFC | un modo di disegno e due finestre: tre vie d'ingresso, non varianti |
| Falda | Falda, Colmo | due modi di disegno: uno vale l'altro |
| Sottocampo | Sottocampo, Fila, Est-ovest, Pensilina | due modi di disegno e due comandi |
| Automatico | Automatico, Completa | due comandi una tantum |
| Elimina stringa | Elimina stringa, Inv. + stringhe, Elimina inv., Cancella tutte | **distruttivi**, di portata crescente |

Oggi «Cancella tutte» resta sulla faccia dopo l'uso: il clic seguente chiede conferma, ma il pulsante dice una cosa molto più
pesante di quella che aveva un minuto prima.

Trovato strada facendo [V]: nel programma in italiano la parola sotto l'icona è **«Pitch»**: `pgettext("roof", "Pitch")` in
`shortcuts.py` e nessun `msgctxt "roof"` in `po/it.po` (la voce senza contesto dice «Passo»). Nei bozzetti ho scritto «Falda».
Da correggere a parte.

## 2. I disegni

Larghezza dei gruppi senza striscia, misurata dal browser su `bozzetti.html` (dati della riga `data-measured`) [V]; il riferimento
G0 dà 806 e 996 contro 799 e 950 misurati nel programma vero: il disegno sbaglia di poco, per eccesso.

| | Disegno | Modell. piena | Impianto piena | Modell. bassa | Impianto bassa | Pro e contro in una riga | Voto |
|---|---|---|---|---|---|---|---|
| G0 | oggi | 806 | 996 | 437 | 534 | c'è già; freccia piccola e senza passaggio suo, faccia che cambia da sola | 2 |
| G1 | angolo alla AutoCAD | 774 | 948 | 405 | 486 | il più stretto e pulito; 7 px di segno, si scopre solo sapendolo | 3 |
| **G2** | **parte divisa: comando e striscia** | 802 | 988 | 429 | 522 | si vede sempre e ha due bersagli chiari, funziona a ogni altezza; 14 px per gruppo | **5** |
| G3 | faccia fissa, tendina con anteprime | 790 | 973 | 429 | 522 | mai un errore, si legge tutto; due clic sempre, rallenta il disegno di serie | 3 |
| G4 | fila a scomparsa sopra i vicini | 786 | 964 | 417 | 504 | parole in vista, la scelta è dove si guarda; copre i vicini, niente clic singolo | 3 |
| G5 | gruppo a pista | 798 | 957 | 487 | 674 | linguaggio delle viste, nulla di nascosto; vale solo per i modi, non per i comandi | 3 |
| G6 | pila di piccoli | 865 | 1157 | 495 | 696 | tutto visibile, un clic; la barra più larga, sparisce il comando normale | 2 |

## 3. Come si scopre che è un gruppo

| | A riposo | Al passaggio | Altro |
|---|---|---|---|
| G1 | triangolino 7 px sull'icona | l'angolo prende lo strato `hover` | va saputo |
| **G2** | chevron su una striscia alta tutto il pulsante | filo fra le parti, ognuna col suo strato | suggerimento: «Sottocampo (S). Altri 3 nella freccia» |
| G3 | chevron accanto alla parola | tutto il pulsante | il clic apre sempre: si scopre al primo uso |
| G4 | chevron verso destra | tutto il pulsante | il clic apre sempre |
| G5, G6 | le voci si vedono | ciascuna la sua | nulla da scoprire |

In tutti: **il tasto destro apre le voci** (oggi la barra ha `PreventContextMenu`, [V]). È il gesto che chi prova fa per primo e non
esegue nulla, quindi è sicuro. La tastiera è già a posto: il menu mostra i tasti.

## 4. Come non sbagliare comando quando il pulsante cambia faccia

Il rischio vero: la memoria dei muscoli clicca nel posto giusto e parte un altro comando. Regole, in ordine di importanza [D, mio
ragionamento sulle famiglie della sezione 1]:

1. **Cambia faccia solo un modo di disegno scelto dal menu.** Falda e Colmo, Sottocampo e Fila: restano accesi durante l'uso, e il
   pulsante deve dire cosa è acceso. I comandi una tantum («Modello», «Da IFC», «Est-ovest», «Pensilina», «Completa») si eseguono e
   la faccia resta quella.
2. **I distruttivi non cambiano mai faccia.** «Elimina stringa» resta davanti; «Cancella tutte» sta in fondo, separata e in rosso
   (`danger`), come già ora le azioni distruttive nei pulsanti (`destructive`).
3. **Mai da sola.** Via `_still_usable`: se la voce si spegne si spegne la parte comando, la striscia resta viva e apre il menu.
   Con G2 il problema per cui era nata non c'è più.
4. **Un tasto non cambia la faccia** salvo che il comando sia un modo (allora è giusto: è acceso, si deve vedere).
5. **La parola cambia con l'icona, nello stesso posto e con la stessa larghezza** (già oggi), e il cambio ha una dissolvenza di
   `Motion.FAST`: lo si nota con la coda dell'occhio. Con «riduci animazioni» subito.
6. **All'avvio torna la voce di base.** La faccia dura la sessione, non il progetto: ogni mattina la barra è quella che si conosce.
7. **Il suggerimento dice sempre il comando di ora**, con il tasto, e che ce ne sono altri.

Una voce attiva è sempre sulla faccia, per la regola 1: non esiste uno strumento acceso nascosto in un menu.

## 5. Cosa fanno gli altri (3 ricerche web, 02/11/2026)

Ho letto i risultati della ricerca, non le pagine intere.

- **AutoCAD** [V, documentazione Autodesk]: il pulsante a scomparsa ha un piccolo triangolo nell'angolo in basso a destra; il
  comando scelto diventa il pulsante attivo; una proprietà «Use Own Button» dei pulsanti decide se la faccia è sempre la stessa o
  l'ultimo usato: anche loro le tengono distinte. Fonti: [About Flyout Toolbars](https://help.autodesk.com/cloudhelp/2018/ENU/AutoCAD-LT/files/GUID-C3524378-3295-4708-9855-CF1353706A80.htm),
  [Create and Edit Toolbars](https://documentation.help/AutoCAD-ACG/WS73099cc142f4875513fb5cd10c4aa30d6b-7cd4.htm),
  [CADmep toolbar](https://help.autodesk.com/cloudhelp/2016/ENU/Fabrication-UsersGuide/files/GUID-4F123CD1-E0C5-49B9-B60F-A1FCFFA91AE9.htm).
- **Revit** [N sul pulsante diviso, non trovato; D a memoria: pulsante diviso con riga e freccia, ultima voce davanti]. Trovato [V]
  l'elenco «Recent Commands» col tasto destro, cinque comandi: [Revit help](https://help.autodesk.com/cloudhelp/2014/ENU/Revit/files/GUID-B0C50D1C-6A4C-4F9A-A418-0AEE07BC940B.htm).
  Vicino di casa [V]: in Inventor il tipo di pulsante si chiama `SplitButtonMRU`, distinto da quello fisso: [forum Autodesk](https://forums.autodesk.com/t5/inventor-programming-forum/custompanel-flyout/m-p/9319408).
- **Figma** [V]: «Click the arrow next to the Rectangle to open the menu», freccia accanto all'icona: [Shape tools](https://figma-signup.helpjuice.com/shape-tools).
  Che l'icona prenda l'ultima forma usata [D, a memoria]: non confermato dalle fonti. Una richiesta sul forum di aprire il menu col
  tasto destro [V, è una richiesta, non documentazione]: [forum Figma](https://forum.figma.com/t/right-click-to-activate-dropdown-options-in-top-toolbar/58497). Conferma il tasto destro della sezione 3.
- **SketchUp** [V, post sul forum, non documentazione ufficiale]: ha pulsanti a scomparsa fissi nella barra Getting Started, non
  creabili dall'utente: [forum SketchUp](https://forums.sketchup.com/t/ux-have-the-large-toolset-displayed-by-default-instead-of-getting-started/60723);
  barre: [help SketchUp](https://help.sketchup.com/en/sketchup/toolbars). L'ultimo usato davanti [N].

Sintesi [D]: pulsante con ultimo usato e segno piccolo è la norma nei CAD, che però hanno utenti addestrati. Autodesk tiene una
scelta fra faccia fissa e ultimo usato: è la regola 1 qui, decisa per famiglia invece che per utente.

## 6. Il resto della barra (sezione `r` dei bozzetti)

| | Oggi | Consigliato | Perché |
|---|---|---|---|
| Pulsante semplice | largo quanto la parola | **S2**: minimo 48 px | tiene insieme le parole corte; i valori restano quelli di `Button.TOOL` |
| Primario (Posa, Calcola) | uguale agli altri: R158 ha tolto l'accento senza mettere altro | **P2**: velo `field` e parola `strong`, nessun accento; spento senza velo | è il pulsante normale del sistema grafico (`PUSH`), rispetta R104 e R158 |
| Titolini | `GROUP` 10 px maiuscole | **T1**, invariati; via solo con le parole accanto | spiegano i gruppi; nelle parole accanto sono doppi e costano 16 px |
| Separatori | `line_soft` alto tutta la barra | **L2**: alto quanto i pulsanti | il titolino resta aria, il gruppo si legge di più |

Altezze: piena 69 px, bassa 47 px [V, misurate]; **nuova** con le parole accanto e senza titolini, 31 px [D: 28 di pulsante, 3 di
margini, come `set_text`]. La regola di quando usarle è nello studio 27.

## 7. Raccomandazione

**G2 per tutte le famiglie, con le regole della sezione 4, S2, P2, T1, L2.** È il solo disegno che resta chiaro in tutte e tre le
altezze e che risolve il comando spento; sta nella larghezza di oggi (4 e 8 px in meno, nel disegno). Se Daniel vuole il linguaggio delle piste anche qui: **G5 solo per Falda e Colmo**, l'unica famiglia di due modi pari; ho
il dubbio che due piste sole diverse da tutto stonino, si vede in `foto/g5.png`. Decide Daniel.

## 8. Cosa cambierebbe nel codice (dedotto, non fatto)

- `ToolMenuButton`: un widget con due zone, comando e striscia. Un `QToolButton` solo non basta: `setDefaultAction` di un'azione
  spenta spegne anche la freccia. Via `_still_usable`, `arrow_rect`, la regola `[grouped="true"]::menu-indicator` e la pressione lunga
  (restano striscia e tasto destro).
- `phases.Tool`: chi è un modo si ricava dall'azione (`isCheckable`); un campo `stays` se non basta. `use()` chiamato solo dal menu.
- Foglio di stile: `[primary="true"]` con il velo (`test_the_accent_...` da controllare), `min-width` di `TOOL`, margini di `#bar-line`.
- Una costante in più per l'altezza con le parole accanto. Da portare nel modello `qt-app-template`: pulsante diviso, primario col
  velo, separatore, regole della sezione 4 nel sistema grafico.

## 9. Non verificato

Disegnato in HTML, non in Qt: le misure sono del browser con Inter o Segoe UI, tarate su G0. Regole 1-7 non provate da un utente. Il
tasto destro della barra non è stato provato con il resto dei menu del programma. Il tema scuro è guardato solo in `foto/p.png`.
