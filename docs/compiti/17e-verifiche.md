# Compito per una sessione cloud: il pannello Verifiche (studio 17, tema F)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/17-interfaccia.md`, sezione F; il bozzetto `docs/studio/17-prove/F-verifiche.html`. Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»): ramo `verifiche` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano alla fine. Dopo i ritocchi della fase 2 (passo 9, i filtri) e `17a` (il delegato delle intestazioni e delle pillole).

**Decisioni di Daniel da leggere prima di cominciare** (dallo studio, F.6): la vista predefinita (per oggetto o per livello); «Correggi» sulla riga o solo sotto; le «superate» nascoste. La bozza è scritta su: per oggetto, «Correggi» sulla riga, superate chiuse.

**Deciso da Daniel il 23/10/2026:** **F2**, per livello in schede, come vista predefinita; per oggetto (F1) e per area (F3) dal menu nella testa del pannello. «Correggi» sulla riga e le «superate» chiuse per impostazione (bozza, non contestata).

**Modifiche dalla revisione completa del 23/10/2026** (`docs/design/interfaccia.md`, sezione 6.4; `docs/studio/18-revisione-completa.md`, sezione 4): da modificare: il blocco «Deciso» dice F2 ma i passi costruiscono F1: la vista predefinita per livello con le sezioni DA CORREGGERE, DA CONTROLLARE, DA SAPERE, SUPERATE; i quattro filtri per livello tolti e sostituiti da «questa fase» e «questo oggetto»; il modo «pronto per la consegna» per la fase Relazione.

**Fatto il 24/10/2026** sul ramo `verifiche` (sessione locale offscreen), secondo il blocco «Modifiche» qui sopra: per livello come vista predefinita, per oggetto e per area dal menu, «Pronto per la consegna» come quarta vista, i filtri «Questa fase» e «Questo oggetto» al posto dei quattro per livello; i dettagli delle regole in `checks.py` e il primo paragrafo di ogni regola di `rules.py`. Resta alla sessione sul PC quanto scritto in fondo.

## Passo 1: il nucleo

1. `checks.Item` prende `detail: str` (il perché e che cosa fare, due o tre frasi, anche quando non c'è una correzione); le verifiche che lo sanno lo scrivono (`checks.py`, `energy/stringing.py`, le regole dei Vigili del Fuoco, la connessione, i prezzi). Le frasi secondo le regole dello studio: una frase, il problema prima della causa, il numero che conta, la fonte con il nome di `rules.py`; mai «per favore».
   - Test in `test_checks.py`: ogni elemento di livello `fail` o `warn` del progetto d'esempio ha un `detail` non vuoto; nessun `text` supera i 90 caratteri.
2. `checks.grouped(items, by)` con `by` in («object», «level», «area»): per oggetto usa `target` (nome dell'oggetto dal progetto, il sito per ciò che non ha oggetto), i gruppi ordinati per il livello peggiore; per livello nell'ordine di `LEVELS`; per area come oggi.
   - Test: i tre raggruppamenti sui dati d'esempio, con i conteggi per gruppo.

## Passo 2: il pannello

3. `ui/checks_page.py`: il menu «Per oggetto ⌄» nella testa (la scelta in `config.py`, `CONFIG_VERSION + 1`); i gruppi come intestazioni con l'icona del tipo e i conteggi; le righe con il segno, la frase, la fonte; la freccia che apre il dettaglio come riga figlia a tutta larghezza e a capo (delegato); «Correggi» e l'occhio come pulsanti nella riga (`setItemWidget`) solo dove servono; le «superate» in un gruppo chiuso; i filtri per livello con il segno **e il numero**; i conteggi nella barra di stato (un'etichetta cliccabile che apre il pannello).
   - Test offscreen: cambiare vista conserva la selezione; aprire una riga mostra il `detail`; «Correggi» sulla riga emette `fix` con l'elemento; l'occhio emette il segnale che le viste già ascoltano (`show_related` al contrario, la selezione dell'oggetto); i conteggi nei filtri e nella barra di stato sono quelli di `checks.counts`.
4. «Copia le note per la relazione» resta e usa l'ordine per area; il doppio clic porta all'oggetto come oggi.
5. Documenti: `docs/funzionalita.md` (le Verifiche), `CHANGELOG.md`, `docs/progetto.md` appendice A, `docs/richieste.md` (R13 chiusa); `po/it.po` e `msgfmt --check`.

**Da lasciare alla sessione locale**: la lettura dei dettagli da parte di Daniel (le fonti e gli articoli), il pannello con un progetto vero da trenta verifiche.
