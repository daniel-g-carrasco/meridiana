# Seconda passata: integrazione e fedeltà (04/11/2026)

Leggi `docs/quick/CONTESTO.md` e `docs/quick/da-sistemare.md`, poi questo file. Vale per tutti i rami `r13-*`.

## Cosa è successo

La prima passata ha prodotto molto codice, ma Daniel ha aperto il programma e ha scritto:

> «ci sono parecchie cose da sistemare»

> «anche il modo in cui sono fatti i rounding, come sono disposti gli strumenti, come si muove meridio, il suo fumetto (non ha contenuti a parte l'aiuto!), il modo di come tra fasi cambiano schede, i loro contenuti, il modo in cui si controlla la modellazione, i tasti, i sottomenu, i tooltip, quelli che si aprono con il lato destro, ecc ecc. Guarda che schifo come sono fatte le linguette delle fasi e come interagiscono quando si passa a file, come rimangono decentrate. Il modo in cui evidenzia gli oggetti selezionati (con contorni evidenziati per i quali si vede anche dietro). C'è un botto di roba che non va.»

> «le barre degli strumenti all'interno delle modellazioni sono parecchie diverse. l'esc non fa tornare al seleziona, le verifiche non sono racchiuse tra sottogruppi... alcune selezioni tipo dei sottocampi non sono centrate, e la modellazione in 2d sembra tutta più lenta»

Le sue schermate sono in `docs/quick/schermate-daniel/`. La sua regola resta: «la ripetizione estetica e di comportamento deve essere accurata nei limiti del possibile. Ma ciò che è semplificabile anche nella struttura estetica ben venga!».

**Tradotto: oggi il nuovo programma somiglia al vecchio. Deve diventare il vecchio, con una tecnica diversa sotto, e non deve essere più lento.** Daniel ha passato settimane a limare ogni margine, raggio, colore, animazione e tasto: quel lavoro sta nel codice dei Widgets e nelle 400 righe di `docs/richieste.md`, e non va reinventato.

## Il metodo: si copia dal vecchio, non si ricostruisce a memoria

1. **Leggi il codice Widgets di ciò che porti, riga per riga, prima di toccare il QML:** `paintEvent`, QSS di `ui/theme.py` e `ui/style.py`, costanti, `sizeHint`, stati, tempi, gestori di eventi, testi. La geometria si prende da lì: stessa matematica dei percorsi, stessi raggi, stessi spessori, stessi colori per ogni stato.
2. **Apri i due programmi nello stesso stato,** finestra vera Direct3D 11, stessa misura, stesso progetto: `tools/quick_widgets_reference.py`, `tools/quick_shell_capture.py`, `tools/quick_rif.py`, `tools/quick_comparison.py`. Se lo strumento non basta, migliora quello.
3. **Confronta per zone, ritagli ingranditi a 200 %**: una linguetta, un pulsante in ogni stato, un angolo di scheda. Guarda ogni ritaglio. Non basta che la pagina intera sembri simile: è esattamente così che è stata mancata la prima volta. Tieni i confronti in `docs/quick/confronto/<ramo>/`, con un `index.html` che Daniel possa aprire.
4. **Comportamento: stessa lista di gesti del vecchio.** Ogni tasto, sottomenu, menu del tasto destro, tooltip (testo e posizione), passaggio del mouse, stato disattivato, doppio clic, trascinamento, animazione (stesso token, stessa curva). Elencali dal codice Widgets e dalle prove in `tests/widget` e `tests/finestra`, e provali.
5. **Niente di provvisorio** in ciò che è tuo. Niente segnaposto, testi inglesi, pulsanti senza effetto. Se qualcosa non si può fare, scrivilo chiaramente nello stato, con il motivo.
6. **Semplificazioni:** ben vengano, ma solo se il risultato per Daniel è uguale o migliore. Ognuna va scritta con la foto prima e dopo in `docs/quick/stato/<ramo>.md`, sezione «Semplificazioni». Nel dubbio, com'è nel vecchio.

**Non dichiarare «fatto» se la foto non è indistinguibile a occhio al 100 %,** salvo differenze scritte. Daniel la guarda, e ha già detto cosa pensa di «simile».

## Usa i due programmi davvero, come li userebbe Daniel

Le prove su un componente isolato non bastano: i difetti che Daniel ha visto in un minuto li ha visti usando il programma. Quindi, per ogni cosa che porti, **fai il percorso a mano su entrambi, uno dopo l'altro, e guarda ogni passo**: apri il progetto di Rho, passa col puntatore su un pulsante, clicca, disegna, premi Esc, apri un menu e un sottomenu, cambia fase, ridimensiona. Se nel vecchio succede una cosa, nel nuovo deve succedere la stessa.

Strumento: `tools/quick_pilot.py`, lo scrive `r13-shell` nei suoi primi commit e lo documenta in `docs/quick/stato/parti-pronte.txt`. Stesso copione per i due programmi: finestra vera Direct3D 11 sul desktop separato, puntatore che si muove a piccoli passi con eventi veri (passaggio del mouse e tooltip compresi), clic e tasti sui controlli veri trovati per testo, e una foto dei due programmi affiancati dopo ogni passo. Un copione per ogni percorso, in `tests/quick/percorsi/`: restano come prove.

Limite noto: sul desktop separato non si vedono il puntatore vero del sistema né i tempi di presentazione al monitor. Quelli li provano Claude e Daniel a schermo vero.

## Regole di lavoro

- Base comune: tutti i rami partono dalla versione unita `r12-quick`, dove ogni pezzo c'è già. Ogni commit deve lasciare funzionante `python -m meridiana.quick "<progetto>"` e le prove `tests/quick/sistema`.
- Lavora da solo, senza aprire altri agenti: la quota è una sola, e la seconda è già stata usata.
- Commit piccoli e frequenti, almeno ogni venti minuti di lavoro, con `git add` e `git commit` separati. Stato aggiornato a ogni traguardo.
- Per le parti degli altri: `git merge r13-<ramo>` quando ti serve, soprattutto `r13-shell` e `r13-controlli`. Non scrivere nelle loro parti; se serve, «Chiesto agli altri» nello stato e un adattatore tuo.
- Le prove restano: compatibilità con `tests/quick/parity/`, foto vere, eventi Qt veri. Aggiungine per ogni difetto corretto, così non torna.

| Ramo | Cosa | Parti sue |
|---|---|---|
| `r13-shell` | Finestra, fasi, File, disposizione, schede per fase, barra di stato, comandi, aggancio di tutte le pagine | `quick/app.py`, `quick/backend/{shell,parts}*.py`, `qml/Meridiana/Shell/`, `tests/quick/shell/` |
| `r13-controlli` | Ogni controllo identico: raggi, stati, misure, menu, tooltip | `qml/Meridiana/{Controls,Theme}/`, `quick/backend/{controls,tokens}*.py`, `tests/quick/controlli/` |
| `r13-pianta` | Pianta: velocità, aspetto, selezione, strumenti, tasti, menu, navigazione | `quick/backend/plan*.py`, `qml/Meridiana/Plan/`, `tests/quick/pianta/` |
| `r13-vista3d` | Vista 3D: barre, sole, terreno, cubo, navigazione, selezione | `quick/backend/scene*.py`, `qml/Meridiana/View3D/`, `tests/quick/vista3d/` |
| `r13-proprieta` | Proprietà, Verifiche, albero del Progetto | `quick/backend/{properties,checks,project_tree}*.py`, `qml/Meridiana/{Properties,Checks,ProjectTree}/`, `tests/quick/proprieta/` |
| `r13-fasi` | Impianto, Produzione, Consumi, Economia, Accumulo, grafici | `quick/backend/{plant,catalog,charts}*.py`, `qml/Meridiana/{Plant,Catalog,Charts}/`, `tests/quick/{impianto,grafici}/` |
| `r13-file` | File, Impostazioni, Nuovo progetto, Relazione, finestre di dialogo | `quick/backend/{files,settings,report,dialogs}*.py`, `qml/Meridiana/{File,Settings,Report,Dialogs}/`, `tests/quick/pagine/` |
| `r13-meridio` | Meridio, fumetto con la conversazione vera, aiuto, tour | `quick/backend/assistant*.py`, `qml/Meridiana/Assistant/`, `tests/quick/meridio/` |

**Aggancio:** `r13-shell` crea per primo, nei suoi primi commit, un registro delle parti (`quick/backend/parts.py`): ogni parte ha una funzione che riceve motore, sessione, cartella cache e finestra, si installa e dice cosa mette in quale posto della finestra. Scrive subito in `docs/quick/stato/parti-pronte.txt` come si usa. Ogni altro ramo ci aggancia la sua parte con un solo file suo, `quick/backend/<parte>_part.py`, e controlla il risultato nella finestra vera, non in una finestra di prova a parte.

Esito finale di ogni ramo: `docs/quick/<ramo>-fedelta.md`, con il confronto, le differenze rimaste e cosa non è stato verificato.
