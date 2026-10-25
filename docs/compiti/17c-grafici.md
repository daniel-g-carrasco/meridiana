# Compito per una sessione cloud: i grafici interattivi con pyqtgraph (studio 17, tema D)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel sulla dipendenza. Lo studio è `docs/studio/17-interfaccia.md`, sezione D; il bozzetto `docs/studio/17-prove/D-grafici.html` (D2); la prova `grafici_prova.py` con `grafici_prova-risultati.txt`. Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»): ramo `grafici` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano alla fine.

**Decisioni di Daniel da leggere prima di cominciare** (dallo studio, D.7): pyqtgraph (MIT) come dipendenza; quali interazioni contano; «Tabella» resta. Se la dipendenza non è accettata, il compito diventa D1 (matplotlib con il blitting: il valore al passaggio, il clic sulla legenda) e i passi 1 e 2 si riducono a `charts.py`.

**Deciso da Daniel il 23/10/2026:** **D2**, pyqtgraph («forse»): la dipendenza nuova (MIT, puro Python, +14 MB) è accettata. Dal browser D2 e D3 sembravano uguali: la differenza sta nel programma (widget Qt nativo, 1-4 ms, contro una vista web da 111-126 MiB con un processo del browser e un secondo modo di disegnare per il PDF). «Tabella» resta. Le interazioni della bozza (valore al passaggio, zoom sull'orario, serie dalla legenda) non sono state contestate.

**Modifiche dalla revisione completa del 23/10/2026** (`docs/design/interfaccia.md`, sezione 6.4; `docs/studio/18-revisione-completa.md`, sezione 4): confermato; aggiungere l'ordine delle interazioni del progetto dell'interfaccia (5.2): valore al passaggio, legenda, zoom sugli orari, esportazione; «clic sull'ora, ombre nel 3D» in coda.

## Passo 1: `Chart` su pyqtgraph

1. `requirements.txt` e `tools/cloud-setup.sh` con `pyqtgraph>=0.14` (CLAUDE.md: se cambia il primo cambia anche il secondo); `pyproject` e il pacchetto di Windows (build-aux) con la dipendenza; `docs/progetto.md` sezione 1 con la decisione e il perché (i numeri della prova).
2. `ui/charts.py`: `Chart` sopra `pyqtgraph.PlotWidget` con le stesse quattro funzioni (`bars` anche impilate, `changes`, `heatmap`, `line`), `message`, il pulsante «Tabella» e `Table`; `set_theme` imposta fondo, assi, griglia, carattere (Titillium Web) e i colori delle serie dai token `chart` di `theme_colors`; antialiasing acceso (misurato: nessuna differenza che conti); le serie orarie con `clipToView` e `autoDownsample`; il ridisegno al cambio di tema (`LIVE`, `redraw`) come oggi; `Canvas` e il rinvio del ridisegno non servono più.
   - Test in `test_charts.py`: ogni tipo di grafico si disegna offscreen con i dati del progetto d'esempio senza errori e `grab()` sotto 50 ms; la tabella contiene gli stessi numeri; il cambio di tema ridisegna con i colori nuovi; un grafico nascosto si disegna alla prima apertura (`when_shown`); `ui/report.py` non cambia e i suoi PNG restano uguali (il test della relazione già presente).
3. `energy_pages.py` e il confronto delle varianti usano `Chart` senza altre modifiche; i test della finestra restano verdi.

## Passo 2: le interazioni

4. Il mirino con la lettura dei valori: una linea verticale e un'etichetta con «mese: valore unità» o «ora: valore» (con tutte le serie per i grafici a più serie), aggiornati da `sigMouseMoved` con un `SignalProxy` a 60 al secondo; sul mensile la barra sotto il puntatore si evidenzia.
   - Test: un evento di movimento simulato sul widget mette nell'etichetta il valore del punto più vicino, con il formato di `number()`.
5. Lo zoom: la rotella sull'asse x sui grafici orari e settimanali (gli altri non si ingrandiscono), il trascinamento a rettangolo, il doppio clic che inquadra tutto; i limiti dell'asse y restano quelli dei dati.
   - Test: la rotella cambia l'intervallo x e non quello y; il doppio clic torna all'intervallo intero.
6. La legenda che accende e spegne le serie con il clic (le voci spente attenuate); l'esportazione «Salva come SVG…» e «Salva come PNG…» dal menu contestuale (`pyqtgraph.exporters`), con il tema chiaro anche se la finestra è scura.
   - Test: il clic sulla voce nasconde la serie; il file SVG esportato contiene il titolo del grafico.
7. Documenti: `docs/funzionalita.md` (i grafici), `CHANGELOG.md`, `docs/progetto.md` appendice A, `docs/richieste.md` (R23 chiusa); `po/it.po` e `msgfmt --check`.

**Da lasciare alla sessione locale**: la resa a occhio dei sedici grafici in chiaro e in scuro, il passaggio del mouse sul portatile, l'installazione su Windows con la dipendenza nuova.
