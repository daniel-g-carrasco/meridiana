# Compito per una sessione cloud: i filtri del catalogo dei moduli (studio 16, tema E)

**Fatto il 24/10/2026 nel ramo `catalogo`** (vedi `docs/progetto.md`, appendice A, e la riga R10 di `docs/richieste.md`); restano la parte per il PC e la bifaccialità stimata nel pedigree e nella relazione. Bozza del 23/10/2026, da lanciare dopo la decisione di Daniel. Lo studio è `docs/studio/16-modellazione.md`, sezione E; la prova in `docs/studio/16-prove/catalogo_filtri.py`. Regole di lavoro come in `docs/compiti/fase-2.md`: ramo `filtri-catalogo` da `lavoro`, richiesta di unione in bozza verso `lavoro`, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano. Prima il test, poi il codice.

**Deciso da Daniel il 23/10/2026** («Tutti i punti proposti vanno bene!»): la bifaccialità stimata entra nel catalogo, segnata come stimata; un filtro «policristallino» proprio; lo strumento per aggiornare la lista CEC. Nessuna libreria nuova: CGAL resta fuori dal programma, come oracolo delle prove.

**Decisioni di Daniel da leggere prima** (E.6): i valori stimati di bifaccialità nel catalogo (marcati) o no; se «policristallino» ha un filtro proprio; se la lista CEC si aggiorna con uno strumento.

1. `catalog.py`: il campo `cell_family` per ogni modulo, calcolato una volta in `load` (in cache) dal testo di tecnologia, modello, serie e note con le regole della prova (`FAMILIES`: TOPCon; HJT, HIT, heterojunction; back contact, ABC, HPBC, IBC, BC; PERC; film sottile; policristallino; monocristallino; «non detto»); `bifacial` sempre booleano; `efficiency_pct` ricavata da potenza e dimensioni dove manca e ci sono le dimensioni (marcata «ricavata»).
   - Test in `test_catalog.py`: le schede lette danno TOPCon 48, back contact 13, HJT 9, non detto 3; la CEC in uso dà monocristallino 15.310, policristallino 1.409, film sottile 166, HJT 1; un record con «TOPCon» nelle note e «Mono-c-Si» in tecnologia è TOPCon; il caricamento con la classificazione resta sotto 300 ms.
2. Le schede lette prendono il campo `cell_family` scritto (`tools/` o a mano in `modules_curated.json`, con la regola come controllo: un test che il campo scritto e quello dal testo coincidano dove entrambi ci sono).
3. `catalog.search` prende i filtri nuovi: `family`, `bifacial` (None, True, False), `manufacturer`, `efficiency_min`, `length_max`; ordinamento a scelta.
   - Test: ogni filtro da solo e insieme; il tempo sotto 10 ms su tutto il catalogo.
4. `ui/catalog_dialog.py`: sopra la tabella le faccette (famiglia della cella, bifacciale, marca dell'origine scelta, potenza da-a, efficienza minima, lunghezza massima, origine), il conteggio «n di N» che c'è già, l'ordinamento cliccando le colonne (`setSortingEnabled` sui dati, non sul testo), la colonna «Famiglia» al posto di «Tecnologia» con la tecnologia nella scheda; la ricerca resta viva (200 ms).
   - Test offscreen: scegliere «bifacciale: sì» riduce il conteggio e ogni riga mostrata è bifacciale; l'ordinamento per W è numerico; i filtri si ricordano tra due aperture nella stessa sessione.
5. (se deciso) `tools/update_cec.py`: rilegge `CEC Modules.csv` di SAM (https://raw.githubusercontent.com/NREL/SAM/develop/deploy/libraries/CEC%20Modules.csv, BSD-3 già in `LICENSE-NREL-SAM.txt`) con `Length`, `Width`, `Bifacial`, `Version` e `Date`, e scrive `modules_cec.json.gz`; la relazione cita la versione della lista. Test: un estratto di dieci righe dà dieci record con i campi attesi.
6. (se deciso) La bifaccialità stimata per famiglia (PERC 0,70; TOPCon e HJT 0,80) dove manca, marcata «stimata» nel pedigree e nella relazione.
7. Documenti e traduzioni: `docs/catalogo/moduli.md`, `funzionalita.md`, `CHANGELOG.md`, `progetto.md`, `po/it.po`.

**Da lasciare alla sessione locale**: la larghezza delle colonne e le faccette a 100 % e 200 %, la velocità della prima apertura sul PC.
