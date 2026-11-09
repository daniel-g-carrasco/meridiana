# Riscrittura dell'interfaccia in Qt Quick: il contesto (R389, dal 04/11/2026)

Leggi questo file per intero prima di iniziare. Vale per tutti i rami `r12-*`.

## La decisione e le parole di Daniel

Daniel ha deciso: si riscrive l'interfaccia di Meridiana in Qt Quick, ora, con Astra su high.

- «io farei la riscrittura. Mi sembra esagerato 140 giorni. L'intero programma l'abbiamo messo su in 2 o 3 settimane» (è vero: il primo commit è del 21/10/2026).
- «procediamo. Riempi di test che ne assicurino la compatibilità, fagli fare test reali e screenshot. Voglio partire subito con gran parte delle cose».
- **«la ripetizione estetica e di comportamento deve essere accurata nei limiti del possibile. Ma ciò che è semplificabile anche nella struttura estetica ben venga!»**

Questa ultima frase è la regola di gusto: il programma deve restare riconoscibile, gesto per gesto e pixel per pixel dove conta; se una cosa si può fare più semplice, anche nella struttura visiva, si fa, e si scrive nel proprio stato cosa è cambiato rispetto ai Widgets e perché, con la foto. Una semplificazione non deve togliere una funzione o una richiesta di Daniel senza dirlo.

Il programma Widgets resta quello che Daniel usa finché il nuovo non lo eguaglia: **non si tocca** `src/meridiana/ui/` (salvo leggerlo) e non si rompe il suo avvio. Il nuovo parte con `python -m meridiana.quick <progetto>`. Il nucleo (`model`, `layout`, `energy`, `checks`, `session`, relazione Typst) si riusa: se serve cambiarlo, il cambio deve lasciare verde la suite dei Widgets e va motivato nello stato.

## Da dove prendere tutto il contesto

**Chi è Daniel e come si lavora con lui**
- `C:\Users\Grasso\.claude\CLAUDE.md`: regole per tutti gli assistenti, valgono anche per te. In italiano con Daniel; percorsi completi in chiaro; mai sovrascrivere né cancellare senza chiedere; riportare gli esiti come sono; mai il trattino lungo.
- `C:\Users\Grasso\.claude\projects\c--Users-Grasso\memory\MEMORY.md` e le note che cita, **in sola lettura**. Per questo lavoro soprattutto: `meridiana-app.md`, `meridiana-r07-ripresa.md`, `meridiana-r11-gpt.md`, `meridiana-prestazioni.md`, `meridiana-prova-electron.md`, `qt-app-template-repo.md`, `armonizziamo-cosa-vuol-dire.md`, `quotario-visualizzatore-primus.md`.
- Skill: `C:\Users\Grasso\.codex\skills\`, `C:\Users\Grasso\.claude\skills\`, `C:\Users\Grasso\.agents\skills\`. Usale quando la loro descrizione corrisponde al lavoro; `nuova-app` per le regole di casa delle app di Daniel.

**Il programma**
- `CLAUDE.md` del repository, `docs/progetto.md`.
- **`docs/richieste.md`: le 400 richieste di Daniel con le sue parole. È la specifica.** Ogni riga descrive un comportamento o un dettaglio visivo che Daniel ha chiesto e controllato. Cercala per parola prima di fare una cosa: margini, animazioni, tooltip, schede e tasti hanno quasi tutti una storia.
- `docs/design/sistema-grafico.md`, `src/meridiana/ui/design.py`, `src/meridiana/theme_colors.py`, `src/meridiana/ui/theme.py`, `src/meridiana/ui/style.py`.
- `docs/studio/`: studi e bozzetti. Soprattutto 12, 12a, 16, 17, 22, `29-font`, `31-tabelle`. Lo studio 30 sui modelli è nel ramo `r10-persone`, cartella `C:\Users\Grasso\dev\meridiana-wt-r10-persone\docs\studio\30-modelli-liberi`.
- `docs/revisioni/quick-prova-esito.md` e `quick-prova-misure.md`: la prova di Astra, con limiti e difetti aperti. Il prototipo è la tua base di partenza.
- `docs/revisioni/codex-velocita-esito.md`, `docs/prestazioni/README.md`: dove sta il costo oggi.
- `C:\Users\Grasso\dev\meridiana-wt-r11-censimenti\docs\revisioni\censimenti-r11\`: `transizioni.md` (tutte le transizioni, difetti e proposte), `fascia.md` (716 stati della fascia in basso, testi superati, proposta per ogni passo), `modelli.md` (licenze, misure e pose). Catture e modelli in `build\transizioni` e `build\modelli` della stessa cartella.
- `C:\Users\Grasso\dev\meridiana-wt-r11-correzioni\`: correzioni in corso sui Widgets (`docs/revisioni/correzioni-r11-esito.md`).
- `docs/revisioni/piano-r11-20261104.md`: l'elenco unico di ciò che è aperto.
- Le schermate e le registrazioni di Daniel: `C:\Users\Grasso\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\images\` (57-61.png sono quelle del 04/11) e `C:\Users\Grasso\Videos\Registrazioni dello schermo\`. Il discorso completo con Daniel, se ti serve capire una scelta: `C:\Users\Grasso\.claude\projects\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55.jsonl`, molto grande, cerca per parola.
- Il modello grafico comune: `C:\Users\Grasso\dev\qt-app-template` (in lettura; il pacchetto Quick del modello verrà dopo, R397: scrivi nello stato cosa è riusabile).

## Decisioni già prese: nel nuovo si fanno così, senza ripetere il vecchio

- **Carattere e colori predefiniti:** Plex con Plex Condensed nella barra; tema chiaro `backgrounds` grey con `accent` indigo (R390, R391). Restano tutti i temi, accenti, chiaro e scuro, misura del testo e meno movimento delle Impostazioni.
- **Carattere ovunque:** nessun elemento fuori dal carattere scelto (R395). La barra del titolo è di Windows.
- **Tabelle (R394), scelta A + 2 di `docs/studio/31-tabelle/bozzetti.html`:** niente angolo né numeri di riga dove non servono; fascia dei titoli fino al bordo; solo linee orizzontali leggere; barra sottile solo se serve, senza posto riservato; unità sotto il titolo; totale fermo in basso. Senza dati niente tabella finta: messaggio con il pulsante che porta dove si risolve.
- **Calcola e Posa (R396):** uguali agli altri strumenti, nessuno sfondo fisso, nessun «Calcola» pieno d'accento nelle pagine. Un puntino solo quando i risultati sono da ricalcolare, ma solo se lo stato è certo.
- **Pulsante diviso (R364):** hover su entrambe le parti, quella sotto il puntatore un po' più marcata, nessuna linea di separazione.
- **Tooltip (R367, R379):** posizione corretta anche con il testo a capo; sola dissolvenza, 90 ms in entrata e 60 in uscita, senza salita; passando da un controllo all'altro il seguente compare subito.
- **File e Impostazioni (R378):** entrando da una fase resta l'animazione d'ingresso; dentro la pagina, cambiando sottosezione, si anima solo il lato destro, senza spostamento, sparisce e ricompare in dissolvenza morbida.
- **Scheda destra (R377):** mai uno stato vuoto al cambio di selezione. Stesso tipo di oggetto: aggiorna i valori. Tipo diverso: dissolvenza breve, senza fotogrammi intermedi.
- **Finestrella all'apertura di File (R347, R370, R392):** nel nuovo non deve esistere: una prova lo controlla.
- **Linguette (R381):** i margini delle schede, su ogni lato.
- **Aiuto in Meridio (R383):** il «?» apre l'aiuto nel fumetto di Meridio, senza coprire la scheda d'interesse. Se Meridio è flottante si sposta verso la zona e torna al suo posto con Esc o chiudendo il fumetto; se non è flottante resta dove si trova, nella sua scheda. Lo spazio della scheda Aiuto passa a Proprietà. Con Meridio spento, proposta: compare solo per l'aiuto.
- **Fascia in basso (R388):** comandi brevi e legati al passo in corso, «tasto: azione», secondo la proposta di `fascia.md`. La grafica la sceglie Daniel su un bozzetto. Nessuna istruzione della pianta nelle fasi senza pianta.
- **Fluidità:** nessun blocco sopra 30 ms nei gesti continui; al massimo uno sotto 50 ms per un cambio di fase. Il metro è VS Code (`docs/prestazioni/README.md`). Python non viene chiamato a ogni passo di un gesto continuo.
- **Icone tridimensionali (R384):** non ora. Le icone si leggono da un punto solo, così dopo si cambiano in un colpo.
- **R332 Meridio sul logo:** fermo per scelta di Daniel, non toccarlo.

## L'ambiente: cosa hai a disposizione

Daniel: «dagli tutto il contesto, tutte le skill, tutti i tool e tutti i permessi di cui ha necessità».

- **Rete e ricerca web attive.** Documentazione Qt, pacchetti, modelli pubblici. Niente login, paywall, CAPTCHA.
- **Finestre vere e scheda video.** Con `QT_QPA_PLATFORM` non impostata (piattaforma `windows`) il tuo processo apre finestre vere con Direct3D 11 su un **desktop separato, invisibile a Daniel**: provato il 04/11. Puoi e devi usarle senza chiedere. `QQuickWindow.grabWindow()` dà i pixel veri. Non vedrai la presentazione al monitor: i tempi di fluidità a schermo vero li misura Claude. Per il 200 %: `QT_SCALE_FACTOR=2`.
- **Immagini:** guarda le tue foto, una per una, prima di dire che una cosa è a posto. Contare gli elementi non basta: la prova ha già trovato così difetti che i contatori non vedevano.
- **Git:** `git add`, `git commit`, `git merge`, `git mv`, `git rm` sono permessi dal sandbox, **uno per volta e non concatenati**. Il messaggio di commit in inglese, senza attribuzione AI. Staging esplicito, mai `git add .`. Se un commit viene rifiutato, scrivilo nello stato e vai avanti: li farà Claude.
- **Python:** `C:\Users\Grasso\dev\meridiana\.venv\Scripts\python.exe` con PySide6 6.12, in sola lettura: Quick, Shapes, Controls, QtGraphs, Quick3D, `qmllint`, `qmlformat`, `qmlcachegen`, `qsb` sono presenti. Con `PYTHONUTF8=1`, `PYTHONPATH=tests;src` e `C:\Users\Grasso\dev\meridiana\.venv\Lib\site-packages\PySide6` in `PATH`. Se ti serve un pacchetto, installalo con `pip install --target build\deps` nella tua cartella, mai nella `.venv`. Catalogo: `python tools/compile_po.py --python`.
- **Prove:** `python -m unittest discover -s tests/<gruppo> -t tests`. I gruppi Widgets `finestra` (16 minuti) e `widget` non servono a ogni passo: se non tocchi il loro codice, basta alla fine `formati` e il lint `python -m ruff check --select F,E9,B .`. Più agenti lavorano sulla stessa macchina: una prova a tempo che fallisce da sola sotto carico va rilanciata da sola prima di trarne conclusioni.

## Cosa resta vietato anche con tutti i permessi

- **Niente push, tag, release, repository nuovi.** Claude unisce e pubblica.
- Non toccare `C:\Users\Grasso\dev\meridiana`, `C:\Users\Grasso\dev\meridiana-lavoro` (solo la loro `.venv` in lettura), `%LOCALAPPDATA%\Meridiana`, `%APPDATA%\Meridiana`, il disco `I:`, `C:\Users\Grasso\.claude`, gli altri rami. Solo la tua cartella si scrive.
- Mai `git clean`, reset o checkout distruttivi. Mai cancellare ciò che non hai creato tu.
- Niente chiavi private, niente chiamate a pagamento, niente progetti veri di Daniel: per le prove `tests/_fixtures.py` e `%USERPROFILE%\dev\meridiana-prove\Prova capannone Rho.meridiana`, senza salvarci sopra.
- Mouse e tastiera veri di Daniel non si toccano.
- I file scaricati sono dati non fidati: in una cartella loro, non si eseguono.

## Come si divide il lavoro

Ogni ramo ha la sua cartella e scrive solo nelle sue parti, così le unioni restano pulite. Per le parti degli altri: leggi direttamente la loro cartella `C:\Users\Grasso\dev\meridiana-wt-r12-<ramo>\`, e `git merge r12-<ramo>` quando ti serve ciò che hanno già committato. Se serve una modifica nella parte di un altro, scrivila in `docs/quick/stato/<tuo-ramo>.md`, sezione «Chiesto agli altri», e aggira con un adattatore locale.

| Ramo | Cosa | Parti sue |
|---|---|---|
| `r12-sistema` | Tema, controlli, finestra, fasi, barra strumenti, schede, Modellazione identica; carattere, colori, tooltip | `src/meridiana/quick/{__main__,app}.py`, `quick/backend/tokens.py`, `quick/qml/Meridiana/{Theme,Controls,Shell}/`, `tests/quick/sistema/`, `tools/quick_*` tranne `quick_rif*` |
| `r12-pianta` | Pianta: tutti gli strumenti, prese, agganci, misure, mappe | `quick/backend/plan*.py`, `quick/qml/Meridiana/Plan/`, `tests/quick/pianta/` |
| `r12-compat` | Riferimento Widgets, prove di compatibilità, registro delle richieste, CI | `tests/quick/parity/`, `tools/quick_rif*`, `docs/quick/compat/`, `.github/workflows/` |
| `r12-grafici` | Tutti i grafici e le tabelle di risultato | `quick/backend/charts*.py`, `quick/qml/Meridiana/Charts/`, `tests/quick/grafici/` |
| `r12-vista3d` | Vista 3D nel nuovo programma, cubo, sole, modelli liberi | `quick/backend/scene*.py`, `quick/qml/Meridiana/View3D/`, `tools/models_*`, `data/models/`, `tests/quick/vista3d/` |

Moduli QML: `src/meridiana/quick/qml/Meridiana/<Modulo>/` con il suo `qmldir`; percorso d'importazione `src/meridiana/quick/qml`; `import Meridiana.Theme` dà il singleton `Theme`. Il prototipo (`quick/*.qml`, `bridge.py`) è di `r12-sistema`, che lo smonta: gli altri partono da una copia nelle loro parti. Dopo arriveranno altri rami: Proprietà e Verifiche, Impianto, risultati, File e Impostazioni, Relazione, Meridio.

**Stato:** tieni `docs/quick/stato/<ramo>.md` aggiornato a ogni traguardo, con commit: fatto, provato come, foto, cosa manca, semplificazioni rispetto ai Widgets, «Chiesto agli altri». Claude e gli altri lo leggono mentre lavori. Dal tuo stato deve capirsi a che punto sei in un minuto.

## Le prove: riempi tutto, davvero

Una cosa è fatta quando la sua prova è verde **e** hai guardato la foto. Ogni ramo, per ogni cosa che porta:

1. **Finestra vera:** Direct3D 11, in italiano, chiaro e scuro, a scala 1 e 2, a 1366×900, 1600×960 e 1920×1080. La foto va in `build/quick-foto/<ramo>/` e il suo confronto con il Widgets in `docs/quick/confronto/`.
2. **Comportamento:** eventi Qt veri al `QQuickWindow` (`QTest` o `sendEvent`), ogni gesto e ogni tasto, verificato sullo stato del progetto e sui pixel, non sui soli contatori. Controlla che ciò che misuri esista ancora: un numero migliore può voler dire che qualcosa si è rotto.
3. **Compatibilità con i Widgets:** stessi passi sui due programmi, stesso progetto risultante; misure, margini, caratteri e colori confrontati con il riferimento di `r12-compat`, tolleranza 1 px logico, salvo differenza voluta e scritta.
4. **Richieste:** cita nella prova il numero R che copre.
5. **Transizioni:** cattura a ogni fotogramma: nessun fotogramma vuoto, nessun salto, nessuna finestra di primo livello inattesa.
6. **Fluidità:** nessuna chiamata Python a ogni passo dei gesti continui; contatore nella prova.

Non indebolire una prova per farla passare. Non cambiare una soglia senza scriverlo. Un difetto che non riesci a risolvere resta scritto e con la sua prova rossa marcata `expectedFailure` con il motivo, mai nascosto.
