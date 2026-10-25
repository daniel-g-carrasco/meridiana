# Compito 23: la stringatura che si usa a mano (R114-R119)

Richieste di Daniel del 25/10/2026, dopo averla provata: «La stringatura fa semplicemente schifo in tutti i sensi. Non
si riesce a fare […] Il programma non è in grado di uscire dalla stringatura automatica» (R114); il riepilogo con i
tasti strani, la scelta che non porta alla stringa, Canc che non cancella, il «+» deforme che non fa nulla (R115);
«Il “rifai” come al solito non serve a nulla» (R116); il pannello saltato che non si vede (R117); le stringhe fatte da
sole aggiungendo un inverter (R118); le schede degli inverter sopra la mappa (R119). Fatto il 25/10/2026 nel ramo
`stringhe` (da `grafica`, 94130ba).

## Prima: che cosa non andava (prova d'uso sul codice di partenza)

Prova sulla finestra vera (piattaforma Windows, finestra fuori da ogni schermo, cartelle temporanee, progetto di prova
«Prova capannone Rho» copiato), schermate `prima-01`...`prima-10` con le didascalie e le note:

- le stringhe erano automatiche e restavano automatiche: nessun comando per spegnerle o per cancellarle tutte; ogni
  cambiamento (un inverter, un modulo, un sottocampo) le rifaceva;
- aggiunto un secondo inverter, Meridiana rifaceva tutto e metteva 7 stringhe sul secondo (R118);
- «A mano» apriva le schede degli inverter sopra la pianta, 270 x 465 px che coprivano i moduli quando si
  ingrandiva (R119);
- il «+» aveva un bordo tratteggiato arrotondato, deformato a 200 %, e cambiava solo il testo della barra di stato;
- scegliere una stringa nel riepilogo non spostava la pianta; Canc non faceva niente (R115);
- tre clic sui moduli 1, 3 e 4 di una fila: la nuova stringa aveva lo stesso colore di quella accanto (le tinte si
  ripetevano dopo 8 stringhe), il modulo 2 restava nella stringa automatica e la sua linea ci passava sopra: il salto
  non si vedeva (R117); le etichette si coprivano fra loro e coprivano i numeri;
- ogni clic toglieva il modulo dalla stringa automatica, ma l'avviso era coperto subito dal messaggio della posa
  («188 moduli posati in 0 ms»);
- ogni clic era un passo di annulla; Invio e Backspace non facevano niente;
- «Rifai» era acceso all'apertura e non faceva niente; dopo una stringa a mano riportava tutto all'automatico (R116).

## Che cosa fa adesso

**Le stringhe sono del progettista.** Nient'altro le fa, le rifà o le sposta: un inverter aggiunto lascia i suoi
ingressi liberi e lo dice; un inverter tolto lascia le sue stringhe «senza ingresso» (le Verifiche lo dicono); quando la
numerazione degli inverter cambia (un altro dello stesso modello in mezzo all'elenco) ogni stringa resta sullo stesso
inverter con il suo numero nuovo (`plant.renumber`). I moduli fuori stringa hanno il bordo rosso e una verifica con
«Correggi» = «Completa le stringhe».

**Comandi** (barra Impianto, menu Calcolo, pannello di destra), ognuno un passo di annulla:

- **Proponi le stringhe**: il menu delle quattro strategie di PVsyst; la scelta propone tutte le stringhe una volta
  sola, al posto di quelle che ci sono, e chiede prima se ce ne sono. È un menu e basta: un pulsante che proponeva al
  clic e sceglieva con la freccia faceva una cosa o l'altra a seconda di dove si cliccava.
- **Completa le stringhe**: propone solo per i moduli fuori stringa, prima sugli ingressi senza stringhe, poi su quelli
  che ne prendono altre lunghe come quelle che hanno (stringhe uguali per MPPT, come PVsyst: completare non crea
  avvisi); quelle del progettista restano prime e uguali.
- **Disegna una stringa**: una stringa nuova sull'ingresso della stringa scelta, o sul primo libero.
- **Elimina tutte le stringhe**: dopo una domanda.
- **Rifai** non c'è più (R116).

**Il disegno di una stringa** (`ui/plan.py`, la «bozza»): «+» su un ingresso dell'elenco o «Disegna»; clic sui moduli
in ordine o trascinamento (un modulo si prende quando il puntatore ne passa il centro); i numeri d'ordine sui moduli
(tutti quando c'è spazio, altrimenti uno ogni 5 o 10 e sempre il primo e l'ultimo); una linea tratteggiata dall'ultimo
modulo al puntatore; nella striscia della barra i moduli contro quelli che l'ingresso vuole («nuova stringa 1.2: 5
moduli, ne mancano 2 (da 7 a 25)»); Backspace toglie l'ultimo, Invio o doppio clic chiudono (un passo di annulla), Esc
annulla senza cambiare nulla; un modulo già in un'altra stringa è rifiutato con il motivo nella barra, Maiusc+clic lo
sposta (alla chiusura la barra dice da quale stringa). Il doppio clic su una stringa (sulla pianta o nell'elenco) la
ridisegna partendo dai suoi moduli. Il tasto destro: durante il disegno chiudi, togli l'ultimo, annulla; su un modulo
di una stringa salta, comincia qui, finisce qui, inverti, ridisegna, sposta su un altro ingresso, elimina; su un
modulo fuori stringa «Nuova stringa da questo modulo».

**Sulla pianta** (R117, `string_paths.py`): i moduli di una stringa sono pieni del suo colore; quelli saltati no. Fra
due moduli che si seguono la linea va da centro a centro quando la retta non attraversa altri moduli (vicini di lato o
d'angolo); altrimenti gira intorno ai moduli saltati lungo i loro bordi, tratteggiata: il percorso più corto fra gli
spigoli dei moduli vicini (A* sui vertici visibili, con i moduli ristretti del 4 % del lato corto perché la linea possa
correre sui bordi in comune, poi riportata sugli spigoli veri). Un salto attraverso più di 120 moduli resta una retta
tratteggiata [I: raro; i moduli sotto restano senza colore, quindi il salto si vede comunque]. La linea è più chiara
del riempimento, con l'alone scuro. Due stringhe vicine, anche in file vicine (entro una volta e mezza il lato corto), non hanno mai la stessa tinta (`string_paths.colours`:
ogni stringa ha la sua tinta, ricavata dal suo primo modulo, così eliminarne una non ridipinge le altre; la seguente
libera se una vicina ce l'ha). Il nome sta sopra il primo modulo, così il
numero 1 si vede; da lontano i nomi che si coprirebbero non si disegnano (resta il colore, il nome è nel
suggerimento), e la pianta li ridisegna quando lo zoom cambia di un quarto. Voce «salto tra moduli» nella legenda.

**Il pannello di destra** (R115, R119): niente più schede sopra la pianta. Il gruppo «Stringhe» ha l'elenco
(`plant_page.StringList`, come l'albero del progetto: sezioni maiuscole per inverter e ingresso con il numero di
stringhe in parole, «+» a destra di ogni sezione come pulsante strumento con l'icona Lucide `plus`, senza bordo suo;
sotto ogni ingresso le stringhe con il quadratino del colore, il nome, i moduli, lo stato in parola e con il segno
delle Verifiche; un ingresso libero lo dice). Una riga scelta sceglie la stringa sulla pianta e la inquadra se non è
già tutta in vista (o se è piccolissima); Canc la elimina (il tasto Canc della finestra, nella fase Impianto, elimina
solo la stringa scelta: mai un modulo o un sottocampo); doppio clic la ridisegna; tasto destro il suo menu. Sotto:
Proponi, Completa, Elimina tutte. Poi «Proposta e verifiche» (strategia e moduli in serie della prossima proposta,
temperatura minima, condizioni delle verifiche), «Stringa scelta», «Sottocampo selezionato» (inverter e ingresso della
proposta). La striscia della barra ha le parole davanti alla legenda larghe almeno 44 caratteri (prima finivano
tagliate a «1 x» e «8 s»).

**Formato 14** (`model._to_14`): fino al 13 una variante senza «auto» falso aveva la proposta automatica; dal 14 «auto»
vero vuol dire soltanto «la proposta di Meridiana di un progetto di prima, da scrivere come stringhe del progettista».
La migrazione mette «auto» vero esplicito dove la proposta c'era; la finestra, alla prima posa completa
(`MainWindow._adopt_proposal`), scrive le stringhe che vede come stringhe del progettista, senza passo di annulla e
senza segnare il progetto modificato (`Session.amend`), e lo dice nella barra. Le stesse stringhe di prima, nello
stesso ordine. Un'importazione da PVsyst (numeri di stringhe, non moduli) usa la stessa strada. Un progetto nuovo non
ha stringhe finché il progettista non le chiede. File congelato `tests/formati/file/progetto-v14.meridiana`. Un
Meridiana più vecchio rifiuta un file del 14 (leggerebbe come automatiche le stringhe di un progetto che non ne ha).

**Altro corretto strada facendo**: la verifica dei moduli fuori stringa diceva che «non producono nella simulazione»,
mentre la producibilità li conta come collegati (`simulate.py` non li toglie): ora il dettaglio lo dice; un cambio che
non posa niente di nuovo (una stringa) non copre più il messaggio della barra con «N moduli posati».

## Le parti del codice (per l'unione)

- `src/meridiana/string_paths.py` (nuovo): percorsi delle linee e colori.
- `src/meridiana/energy/plant.py`: docstring del modulo, `Plant.auto` falso di base, `build` (auto falso di base),
  `_propose` (ingressi occupati, lunghezze uguali), `_propose_optimized` (potenza già caricata), `propose`,
  `unit_keys`, `renumber`, `delete_run`, `set_run`, `touched` (toglie «auto»), `runs_of`.
- `src/meridiana/model.py`: `FORMAT_VERSION = 14`, `_to_14`, la riga di `MIGRATIONS`, il commento delle migrazioni.
- `src/meridiana/session.py`: `Session.amend`.
- `src/meridiana/checks.py`: `left_detail`, `plant_items` (correzione «Completa», niente più «Rifai»).
- `src/meridiana/settings.py`: `Strings.auto` falso di base e la docstring.
- `src/meridiana/pvsyst/mapping.py`: «auto» vero nelle stringhe importate.
- `src/meridiana/shortcuts.py`, `src/meridiana/phases.py`, `src/meridiana/ui/icons.py`: i comandi
  `strings_auto` (Proponi), `strings_complete`, `strings_manual` (Disegna), `strings_clear`; `strings_redo` tolto;
  icona `list-plus` in `data/icons/lucide` (README, ATTRIBUTIONS).
- `src/meridiana/ui/plan.py`: segnali delle stringhe (in testa alla classe), stato delle stringhe in `__init__`,
  `focus`, `_moved`, `show_project` (`_draw_draft` dopo `_draw_wiring`), tutta la sezione «strings» (da `set_wiring` a
  `_draw_band`, prima di `_slope_arrow`), `mousePressEvent`, `mouseDoubleClickEvent`, `mouseMoveEvent`,
  `mouseReleaseEvent`, `keyPressEvent`.
- `src/meridiana/ui/plant_page.py`: import, docstring del modulo, `summary`, `Legend` (voce «salto»), `PlantPage`
  (striscia, niente pannelli), `PlantInspector` (gruppi Stringhe e Proposta e verifiche, segnali, `show_plant`,
  `_inputs` tolto), `InverterPanels` tolto, `StringList` e `swatch` nuovi.
- `src/meridiana/ui/window.py`: import di `input_name`, stato in `__init__`, segnali della pianta, comandi del menu
  Calcolo e le loro icone, `_build_phases`, `_theme_changed`, `_session_changed`, `_delete_key`, `_fix`,
  `_layout_done`, `_lend_plan`, `_return_plan`, `_show_inspector`, `_plant_done`, `_add_inverter`,
  `_size_inverters`, `_entries_edit`, tutto il blocco delle stringhe (da `_runs` a `_runs_changed`, al posto di
  `_confirm_redo`...`_string_gesture`), `_save_window`.
- `src/meridiana/ui/report_chapters.py`: la frase delle stringhe del progettista.
- `po/it.po`: 74 voci nuove in fondo, a mano (msgmerge riordinava l'intero file: 21.550 righe cambiate).

## Come è stato provato

- [V] Prova d'uso «dopo» sulla finestra vera, con gli stessi accorgimenti della prova «prima»: eventi veri di mouse e
  tastiera sulla pianta, clic veri sui pulsanti e sulle righe dell'elenco, Canc, Ctrl+Z e Ctrl+Y dalle scorciatoie
  della finestra, il catalogo vero; 22 schermate `dopo-01`...`dopo-22` con le didascalie, guardate una per una: apertura
  di un progetto del formato 13 (le 8 stringhe uguali, non modificato, nessun passo di annulla), elimina tutte, tre
  stringhe a mano (una con un modulo saltato, una a serpentina con trascinamento e doppio clic, una sul secondo
  inverter con un clic rifiutato), scelta nell'elenco (la pianta da 183 a 27 m sulla stringa), Canc, «+», Ctrl+Z e
  Ctrl+Y, un terzo inverter (nessuna stringa nuova, la stringa del 20 kW resta sul 20 kW che diventa il numero 3),
  Completa (12 stringhe aggiunte, le mie uguali, nessun avviso di stringhe diverse), salva e riapri (stringhe uguali),
  Proponi dal menu della barra con domanda, salva e riapri.
- [V] Test: `nucleo/test_string_paths.py` (8: linee dritte fra vicini, giri senza entrare in moduli altrui con file
  attaccate e distanziate, salto lungo dritto, 8.000 moduli sotto i 3 s, colori dei vicini anche nella fila accanto,
  colori che restano), `calcoli/test_stringing.py`
  (classe `OnlyWhenAsked`, 5: niente stringhe da sole, inverter aggiunto e rinumerazione, Proponi e Completa, Completa
  senza ingressi liberi, elimina e ridisegna), `formati/test_project_files.py` (formato 14 e migrazione), `nucleo/test_session.py` (`amend`),
  `widget/test_string_list.py` (2: sezioni, «+» del sistema grafico, scelta, doppio clic, tasto destro),
  `finestra/test_window.py` (classe `Stringing` rifatta: disegno con numeri, Backspace, Esc, Invio, salto tratteggiato
  e modulo saltato senza colore, rifiuto e Maiusc, ridisegno, elenco che inquadra, Canc, progetto di prima scritto
  senza passo), `finestra/test_glyphs.py`; i test che si aspettavano la proposta automatica la chiedono ora
  esplicitamente.
- Non verificato: il trascinamento con un mouse vero (gli eventi sono veri ma mandati dal programma, non dal sistema);
  il tema scuro; lo schermo verticale a 2,5x; un impianto grande (centinaia di stringhe) a mano, oltre la prova sui
  tempi del percorso; gli ottimizzatori SolarEdge disegnati a mano sulla finestra vera (provati dai test).

## Domande per Daniel

1. **Modulo di un'altra stringa mentre disegni**: ora è rifiutato e Maiusc+clic lo sposta. In alternativa si potrebbe
   spostarlo sempre, con l'avviso. Consiglio: tenere il rifiuto, è più difficile sbagliare.
2. **Dopo Invio**: il disegno finisce e la stringa nuova resta scelta. In alternativa ne potrebbe cominciare subito
   un'altra sullo stesso ingresso. Consiglio: lasciare così, «+» è a un clic.
3. **La proposta** sceglie i moduli in serie che lasciano meno moduli fuori sulle file, non quelli che riempiono meglio
   gli ingressi: sul capannone di prova «Una fila per stringa» fa stringhe da 8 e lascia 28 moduli fuori, mentre
   stringhe da 16 ne lascerebbero meno. È il comportamento di prima (non toccato qui). Consiglio: rivederlo in un
   compito a parte, contando anche quante stringhe prendono gli ingressi.
4. **Colori**: il colore di una stringa viene dal suo primo modulo (non cambia se se ne elimina un'altra, cambia se la
   si ridisegna partendo da un altro modulo); le tinte sono le 8 del colore scelto, quindi stringhe lontane possono
   avere lo stesso colore. Consiglio: va bene così; un colore scelto dal progettista per stringa andrebbe salvato nel
   file.
