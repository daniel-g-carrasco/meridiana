# Compito per una sessione cloud: attese visibili (studio 16, tema F)

Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione F; la prova in `docs/studio/16-prove/attese.py`. Regole di lavoro come in `docs/compiti/fase-2.md`: ramo `attese` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano. Prima il test, poi il codice.

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): soglia di 300 ms; l'arco anche sulla pianta durante la posa; i valori vecchi in grigio, non barrati, finché arrivano i nuovi. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima** (F.6): la soglia (300 ms proposta); l'arco anche sulla pianta durante la posa; i valori «da aggiornare» barrati o solo grigi con il segno nel titolo.

Regole fisse: niente sotto la soglia; arco nella zona interessata da 300 ms a 10 s con il testo nella barra di stato; barra con percentuale e Annulla solo per PVGIS e PDF; i valori vecchi restano visibili e segnati; mai una finestra modale; tutto fermo con «meno movimento» (la preferenza già letta).

1. `ui/waiting.py`: `Spinner` (l'arco della prova, 24 e 48 px, colore d'accento, fermo con meno movimento) e `Stale` (lo stile «da aggiornare»: grigio del tema e, se deciso, barrato); un `Delayed` che mostra un widget dopo la soglia e lo nasconde subito alla fine (`QTimer.singleShot`), così sotto la soglia non compare nulla.
   - Test in `test_panels.py`: un lavoro di 100 ms non mostra l'arco; uno di 600 ms lo mostra dopo la soglia e lo toglie alla fine; con meno movimento l'arco è fermo (un solo fotogramma).
2. Valori «da aggiornare» (P7 dello studio 12): quando il progetto cambia dopo l'ultimo calcolo dell'energia (`generation` diversa da quella del risultato), le pagine Producibilità, Consumi, Bilancio e le Verifiche prendono lo stile `Stale` sui valori e un segno nel titolo della scheda («Producibilità ·»), tolto al ritorno del risultato; «Ricalcola» (F5) già c'è.
   - Test offscreen: modificare l'altezza di un edificio segna i valori; il ritorno del calcolo li pulisce; annulla fino allo stato calcolato li pulisce (stessa chiave).
3. L'arco nella zona che aspetta: sulla pianta in alto a destra durante la posa (sui sottocampi «da posare di nuovo»), sulla pagina dell'energia durante il calcolo (al posto del solo testo nella barra di stato, che resta), nel catalogo durante la prima lettura (`catalog.load` spostato in un lavoro del pool con la finestra che apre subito vuota con l'arco).
   - Test: la finestra del catalogo apre prima che il catalogo sia letto e mostra l'arco; la posa mostra l'arco solo oltre la soglia.
4. Lo scheletro della 3D all'avvio: sopra il `QQuickWidget` un widget `QPainter` con cielo, terreno e i contorni degli edifici dalla pianta nei colori del tema, tolto al primo fotogramma (`sceneGraphInitialized` o il primo `afterRendering` del `quickWindow()`), con un limite di 3 s dopo cui si toglie comunque e si dice il motivo nel log.
   - Test offscreen: il segnaposto c'è prima del primo fotogramma e non c'è dopo; immagine offscreen in chiaro e in scuro.
5. Barra di avanzamento con Annulla nella barra di stato per PVGIS (passi: anno tipo, orizzonte, PVcalc) e per la relazione PDF (pagine): `QProgressBar` permanente con il pulsante; Annulla scarta il risultato (generazione) e per PVGIS interrompe tra una richiesta e l'altra (`requestInterruption` letto nel lavoro).
   - Test: un PVGIS finto di tre passi muove la barra; Annulla a metà lascia il progetto com'era e la barra sparisce.
6. Documenti e traduzioni: `funzionalita.md`, `CHANGELOG.md`, `progetto.md` (appendice A con le misure della prova), `po/it.po`.

**Da lasciare alla sessione locale**: lo scheletro sopra la 3D vera con la GPU (il segnale del primo fotogramma), la leggibilità dell'arco sull'ortofoto, la misura della soglia a occhio sul PC.
