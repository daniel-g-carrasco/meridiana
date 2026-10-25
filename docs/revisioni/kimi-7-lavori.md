# Lavori della revisione Kimi, incarico 2

Data: 25/10/2026. Rami: `kimi-revisione` in entrambe le cartelle. Nessun push, merge, rebase o modifica fuori dai due
repository e dalle cartelle temporanee delle prove.

## Parte 1: Meridiana

1. **`a3d2e49`, rapporti.** Scritti i cinque rapporti indipendenti, il riepilogo e l'incarico, solo documenti. Le
   verifiche iniziali avevano mostrato i problemi di attese e catalogo poi corretti nei punti seguenti.
2. **`eecf4e6`, isolamento della home delle prove.** `HOME` e `USERPROFILE` temporanei per tutta la suite e
   `MERIDIANA_KOKORO_DIR` rimossa. Prima tre scenari senza motore trovavano il Kokoro reale; dopo gli stessi tre test
   non lo vedono e non avviano il suo processo.
3. **`d4f1045`, fumetto.** La prova usa `nothing_local`, attende la fine della ricerca e toglie la scheda prima del
   ridimensionamento. Prima il risultato dipendeva dalla ricerca ancora in corso; dopo il pannello resta sotto 260 px,
   con domande nascoste e campo e conversazione visibili.
4. **`bb6f0b8`, accento.** Un pixel conta solo con un vicino accento; il fuoco è ammesso sui campi di inserimento e
   non sui contenitori. Il pixel subpixel isolato non dà più falsi allarmi; una nuova etichetta realmente accento è
   ancora trovata.
5. **`cae3eb2`, immagini 3D della relazione.** Lo skip richiede entrambe le diagnosi GLSL e pipeline. Prima il
   renderer poteva essere escluso con una condizione più larga; dopo solo il guasto confermato è saltato e gli altri
   risultati restano valutati.
6. **`509420b`, chiusura con relazione in corso.** `closeEvent` cancella relazione e anteprima e ferma il timer. La
   nuova prova, prima con il `.part` ancora presente, dopo verifica generatori chiusi, timer fermo e nessun `.part`.
7. **`8d66249`, timer con contesto.** `TileLoader`, Proprietà e `Theme` passano il proprietario a
   `QTimer.singleShot`. Tre nuove prove distruggono ciascun oggetto prima dello scatto: prima errori differiti, dopo
   nessun errore.
8. **`b0662d9`, aggiornamenti e IFC.** Stato nei job e risposte a metodi legati, non lambda che catturano la finestra.
   Le nuove prove di risposta dopo la distruzione falliscono prima e passano dopo, senza errori Qt.
9. **`3a5405d`, QuickImage.** `_fit` e `resizeEvent` escono se `quick` è già rilasciato. Le due nuove prove passano
   dopo la guardia; accessori, timer dello screenshot e `SystemAccent` non toccati.
10. **`6f7ac61`, messaggi della posa.** Aggiunto `N_`, marcate le note memorizzate e tradotto l'errore dell'area al
    `raise`. Prima i messaggi restavano in inglese; dopo Verifiche, Proprietà ed errore sono provati in italiano.
11. **`47c0035`, altri errori utente.** Tradotti solo progetto, versione più nuova, file PVsyst, sottofondo e
    orizzonte, con segnaposto nominati. Le nuove prove, prima in inglese, verificano i messaggi italiani e i numeri di
    formato; le validazioni interne escluse restano invariate.
12. **`e8052e2`, catalogo obsoleto.** Un parser delle voci complete, non tagli testuali, ha rimosso esattamente 105
    chiavi assenti dai sorgenti, comprese quelle adiacenti senza riga vuota. Il catalogo compilato conserva tutte le
    altre traduzioni invariato contenuto; `msgfmt --check` e suite verdi.
13. **`6e836d0`, «Posa».** Il `msgid` condiviso `Layout` e le domande di Meridio usano «Posa»; «Disposizione» resta
    per finestre e orientamento. Le nuove prove lessicali falliscono prima e passano dopo.
14. **`45ab43d`, armonia senza cambiare un pixel.** Colori di stato da `STATUS`, fallback da `default_tokens()`,
    misure equivalenti dalle scale, un solo `CHART_MIN_HEIGHT`, palette della relazione in `report_style.py` e nomi
    locali dei timer. La nuova prova era rossa sul rosso critico ancora letterale; dopo è verde. Nessun catalogo
    `Timing`, nessuna decina di nomi usati una volta, nessun `STATUS["info"]`, nessuna corrispondenza solo numerica o
    colore di pianta e 3D cambiato.
15. **`153ceb5`, non svolto da me.** Fatto da Claude come disposto: `Motion.QUICK = 130` per Meridio e camera in
    `Motion.SLOW`. Non ho ritoccato quei file per questo scopo.
16. **`d7fb14b`, non svolto da me.** Fatto da Claude come disposto: margini delle pagine energia e bordo `danger`.
    Le sole modifiche equivalenti del punto 14 alle tessere e al minimo dei grafici sono nel commit precedente.

## Parte 2: il modello grafico

17. **`20c7817`, rapporto `kimi-template.md`.** Otto riscontri con file, riga, gravità, prova, correzione e rischio:
    timer, accento, fallback, misure, duplicazione, origine, API inutilizzata ed esempi specifici. Base verificata:
    54 prove verdi e `ruff` prima del documento.
18. **Correzioni e semplificazioni, separate per argomento.**
    - **`ada33d4`, timer di `Theme`.** La nuova prova di distruzione dava `RuntimeError: Signal source has been
      deleted`; con il contesto passa. Tutte le 55 prove verdi.
    - **`36a74bc`, accento.** Il pixel isolato era trovato come difetto `[(3, 3)]`; con i vicini sparisce, mentre
      l'etichetta testuale resta rilevata e il campo attivo ha il suo anello consentito. Tutte le 57 prove verdi.
    - **`adeb7f4`, armonia.** Fallback e misure dai token esistenti, `WARM_UP_MS`; la prova falliva su `#5f5a52`
      contro `text2 = #514c44`. Tutte le 58 prove verdi. Le gallerie prima e dopo, generate dalla base `efdb5be` e
      dal nuovo codice nello stesso ambiente, sono identiche pixel per pixel in chiaro e scuro.
    - **`2e6596f`, `FilePage.command`.** Prima `then` non veniva chiamato; dopo la delegazione passa e la pagina si
      chiude prima dell'azione come prima. Tutte le 59 prove verdi.
    - **`479eb4b`, origine e residui.** `SOURCE` e provenienza aggiornati, esempi neutrali, esclusioni documentate e
      conteggio delle prove aggiornato. `Motion.QUICK` non è stato aggiunto perché Meridio e camera non esistono nel
      modello; il punto 16 non si applica. `popups.motion()` resta perché toglierla cambierebbe l'API pubblica.

## Parte 3: il peso del foglio di stile

19. **`d3beaa4`, misura del QSS, nessuna modifica al programma.** Il foglio applicato ha 15.058 caratteri, 161
    regole e 230 selettori, non 42 KB di testo QSS. Sulla finestra reale (1.911 widget), `setStyleSheet` costa una
    mediana di 595,499 ms; la lucidatura completa dopo `unpolish` costa 54,617 ms contro 3,326 ms con il solo stile.
    Il disegno raster di 20 widget costa invece 2,056 ms contro 1,936 ms, +0,120 ms. Un cambio di tema raggiunge
    tutti i 1.911 widget; `tone` e `primary` ne rilucidano uno solo. `QScrollArea` è l'unico selettore con effetto
    rilevante ripetibile, 9,320 ms nella lucidatura, ma non spiega il costo globale né quello ordinario. Dettagli e
    limiti sono in `kimi-6-css.md`; nessuna proposta applicata.

## Verifica finale

`ruff check src tests tools` in Meridiana e `ruff check .` nel modello: verdi. Catalogo italiano compilato prima
della suite. Ogni gruppo di Meridiana in un processo separato, offscreen.

| Gruppo | Prove eseguite | Saltate | Esito |
|---|---:|---:|---|
| Meridiana `nucleo` | 786 | 4 | verdi |
| Meridiana `calcoli` | 175 | 0 | verdi |
| Meridiana `formati` | 59 | 0 | verdi |
| Meridiana `esterni` | 6 | 6 | nessuna prova esterna abilitata |
| Meridiana `widget` | 282 | 1 | verdi |
| Meridiana `finestra` | 123 | 0 | verdi |
| **Meridiana, totale** | **1431** | **11** | **1420 verdi** |
| Modello, intera suite | 59 | 0 | verdi |

La prima esecuzione completa del punto 14 si era fermata in `widget` con 20 errori Qt di tipo e durata non
riproducibili; senza alcuna modifica, il gruppo isolato è poi risultato interamente verde (282 prove, una saltata).
Tutti gli altri gruppi erano già verdi. L'esito non è stato contato come verde finché la ripetizione non è passata.

## Limiti e lavoro lasciato

- Nessuna finestra aperta sullo schermo e nessuna cartella reale di Daniel usata. La fluidità, l'aspetto e le misure
  del QSS sullo schermo vero restano da ripetere a Claude; qui sono verificati solo il rendering offscreen e i
  comportamenti automatizzati.
- I punti 15 e 16 sono di Claude, come richiesto. Le modifiche che cambiano aspetto o interfaccia del modello sono
  rimaste nel rapporto, in particolare la rimozione di `popups.motion()`.
- Non sono stati introdotti `Timing`, nuovi ruoli di stato o semplificazioni oltre quelle approvate. Il timer dello
  screenshot e `SystemAccent` non sono stati cambiati.
