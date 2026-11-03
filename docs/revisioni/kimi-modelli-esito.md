ESITO: verde

# Modelli 3D, R348-R351

## R348 Pino

**Fatto.** Nuovo `pine`, pino domestico a ombrello: tronco nudo con inclinazione e ramificazioni alte, tre lobi di chioma larga e appiattita. Predefinito 14 m di altezza, 10 m di chioma e 9,5 m di tronco. Nome, ingombro ottagonale, ombra e galleria compresi.

**Commit:** `03dbf24 Add the Italian stone pine model (R348)`.

**Verificato:** `nucleo.test_props` e `nucleo.test_props_project`, misure, mesh chiusa, orientamento, ombre e scena. Foto aperte in `foto/modelli-R01/dettagli/alberi-chiaro-*.png`: pino e conifera sono distinti a colpo d'occhio.

## R349 Modelli e intersezioni

**Fatto.** Auto con cofano e bagagliaio distinti, abitacolo vetrato, montanti, tetto, ruote a 16 lati, cerchi, mozzi, fari e fanali. Il limite della famiglia passa da 300 a 850 triangoli: il modello ne usa 816 per mostrare questi elementi senza superare il budget.

**Fatto.** La base degli oggetti su falda usa il punto più alto del loro ingombro, non più soltanto il centro: il caso misurato del camino che affondava è corretto.

**Lasciato.** Persone, chioma degli altri alberi, camini, sfiati, macchine, lucernari e vani scala conservano il modello esistente. Nelle foto aperte non mostrano intersezioni visibili; restano volutamente minimal. Non è stato dimostrato che ogni possibile configurazione di tetti e parapetti sia priva di intersezioni.

**Commit:** `587e09f Improve car geometry and roof contact (R349)`.

**Verificato:** prova automatica della base su falda e controlli di tutte le mesh. Auto fotografate da tre lati in `foto/modelli-R01/dettagli/auto-chiaro-*.png`. Confronto prima/dopo aperto in `foto/modelli-R01/prima/` e `dopo/`.

## R350 Spezzate

**Fatto.** `Prop.path` contiene i vertici; `width` resta la larghezza. Siepi e camminamenti si disegnano con il tracciamento dei lati: clic, agganci, lunghezza digitata, Invio o doppio clic, Esc. Un unico buffer raccordato alimenta pianta, selezione, spostamento, rotazione, duplicazione, maniglie, ombre, 3D, IFC e relazione. Gli oggetti `walkway` entrano nelle esclusioni del layout attraverso la strada già esistente dei `Prop`: non è stato aggiunto un secondo tipo di esclusione.

**Fatto.** Formato 25 con migrazione e `tests/formati/file/progetto-v25.meridiana`. Una siepe o un camminamento vecchio diventa una spezzata di due punti.

**Commit:** `56a3798 Draw hedges and walkways as continuous paths (R350, R351)`.

**Verificato:** `nucleo.test_linear_props`, formati e flusso finestra. Foto aperte in `foto/modelli-R01/dettagli/lineari-chiaro-*.png`: angoli continui, nessun buco visibile.

## R351 Camminamenti senza corrimano

**Fatto.** Il predefinito è una membrana da 0,02 m, poco più scura del tetto, appoggiata alla falda e senza ombra. «Con corrimano» aggiunge i parapetti e l'ombra. La migrazione conserva il corrimano sui progetti vecchi.

**Commit:** compreso in `56a3798`.

**Verificato:** la prova finestra controlla predefinito, ombra, modifica di un vertice e tre annulla consecutivi. Le foto mostrano lo stesso percorso su falda con e senza corrimano.

## Prove finali

- `ruff check src tests tools`: verde.
- 72 prove mirate di oggetti, percorsi e formati: verdi, una IFC saltata perché `ifcopenshell` non è installato.
- `finestra.test_props_workflow`: 4 prove verdi, compresa la nuova spezzata.
- Gruppi `nucleo`, `formati` e `widget`: i primi run hanno trovato test italiani rossi perché il catalogo non era compilato. Dopo `tools/compile_po.py`, gli 8 casi incriminati ripetuti sono verdi.
- Gruppo `finestra` completo: 325 prove, una rossa e una saltata. `test_nothing_comes_by_itself_and_a_string_is_drawn_numbered_taken_back_closed_and_given_up` attendeva «all 4 strings cleared» e ha trovato «The project changed during string search» (`tests/finestra/test_window.py:1759`), ambito stringhe non toccato.
- Prova reale con `tools/real_session.sh`: galleria e dettagli prodotti e aperti. `tools/real_tour.py` ha visitato e fotografato tutte le fasi, poi si è fermato a `tools/real_tour.py:161` con `KeyError: 'import'` sulla pagina File, fuori dai file dell'incarico. Le foto preesistenti sovrascritte sono state ripristinate.
- `findmnt /run/user/1000/doc` conferma il montaggio del portale documenti intatto.

## Nuovi msgid

`po/it.po` non è stato modificato.

| msgid | msgstr |
|---|---|
| Stone pine | Pino domestico |
| {what}: click each corner; Enter or a double click finishes, Esc cancels | {what}: fai clic su ogni angolo; Invio o doppio clic per finire, Esc per annullare |
| Draw a linear 3D object | Disegna un oggetto 3D lineare |
| With railing | Con corrimano |
| Click each corner; Enter or a double click finishes, Backspace removes the last point, Esc cancels. Type a number for the length of a segment. | Fai clic su ogni angolo; Invio o doppio clic per finire, Backspace elimina l'ultimo punto, Esc annulla. Scrivi un numero per la lunghezza di un tratto. |

## Rimasto

Niente nei quattro punti. La verifica su Windows resta a Claude, come previsto. Il difetto del giro automatico sulla pagina File resta fuori da questo incarico.
