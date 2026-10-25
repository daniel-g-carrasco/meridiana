# Compito per una sessione cloud: le prestazioni, per algoritmo (revisione 18)

Bozza del 23/10/2026 dalla revisione completa (`docs/studio/18-revisione-completa.md`, sezione 2.C; il rapporto `docs/studio/18-prove/C-prestazioni.md` sezioni 6 e 7, con gli script `dispatch_varianti.py`, `energia_tempo.py`, `scalabilita.py`, `avvio.py` e `profilo_energia.py` da riusare come misure prima e dopo). Regole di `docs/compiti/fase-2.md`: ramo `prestazioni` da `lavoro`, un commit per passo con la misura prima/dopo nel messaggio, niente dipendenze nuove.

**Decisione di Daniel (R31, 23/10/2026):** niente numba, niente Rust; algoritmi e numpy. Gli obiettivi (C §2): avvio sotto 1 s; ogni gesto sotto 100 ms; il calcolo sotto 1 s per 200 moduli e sotto 10 s per 5.000; la posa sotto 1 s per 5.000.

## Parte A: il nucleo (subito, file del nucleo soltanto)
1. `economics.dispatch` a stato vettoriale per tutte le coppie (batteria, anno) in una passata (variante b di `dispatch_varianti.py`: 0,54 s -> 0,07 s), e il bilancio del primo anno che riusa l'anno 1 (`economics.py:204` e `:260` sono la stessa chiamata). Uguaglianza con il riferimento a 1e-9 come test.
2. `economics.evaluate` per array: le tre maschere delle fasce calcolate una volta (`:269, :207, :350-351`), il ciclo dei 25 anni come array 25 x 8.760, il registro del pedigree costruito solo per la valutazione principale (-0,3-0,4 s).
3. Una sola corsa di `simulate` per calcolo: i prodotti intermedi della prima conservati e l'effetto elettrico delle stringhe applicato a valle (`simulate.py:313-327`; oggi `window.py:187` e `:206` rifanno tutto: -0,13 s a caldo, -0,27 s a freddo).
4. `nearshade.shading` per cella, vettoriale: un solo `shapely.intersection` per piano su tutte le celle (`STRtree.query` vettoriale) o l'ombra per riga (`nearshade.py:239-272`): da 1,1 s a qualche decimo per 188 moduli, da 8-10 s a 1-2 s per 5.000-20.000 [I]; `_read` ed `electrical` con una lettura sola e `np.add.reduceat` (`:387-393, :345-364`).
5. `count_out_of_shadows` senza una posa intera in più per sottocampo (`window.py:218`).
6. La posa con i corner di tutti i moduli in numpy (rotazione e scala come una matrice 2 x 2), shapely solo per `usable` e per gli intervalli liberi (`layout.py:323-354`): da 0,4-0,9 s a circa 0,1 s per 5.000-20.000 [I].

## Parte B: la finestra (dopo `18b-sessione.md`)
7. `mesh.module_table` vettoriale (una moltiplicazione (N, 3, 3) per sottocampo) e stabile fra una selezione e l'altra: cambiano solo i colori (`mesh.py:296-302`, `window.py:1345-1346, 1642-1654`): -45-60 ms per clic sul progetto grande.
8. `_layout_done` in gran parte nel thread della posa: la tabella delle istanze e i corner dei moduli come array preparati lì; la pianta riceve un array, non N `QPolygonF` (`plan.py:330`); la pianta non ridisegnata due volte per modifica (`window.py:1564-1576`).
9. Le tessere decodificate fuori dal filo principale (`ui/tileloader.py:43-57`, `QThreadPool` o `QImageReader`).
10. Import pigri di pandas, matplotlib e pvlib (`energy/consumption.py:1-15`, `ui/charts.py:19-29`, `ui/window.py:25-32`): -0,7 s all'avvio; i grafici della prima apertura disegnati uno alla volta al ritorno nel ciclo degli eventi (`charts.py:136-148`).

## La chiusura
11. Le misure prima e dopo con gli script di `18-prove`, nel riassunto e nel diario; il bilancio della sezione C §2 aggiornato con i numeri nuovi.

## Da provare sul PC di Daniel
- Il calcolo di Rho a caldo e a freddo sullo schermo vero; l'avvio; la selezione sul progetto da 4.682 moduli.
