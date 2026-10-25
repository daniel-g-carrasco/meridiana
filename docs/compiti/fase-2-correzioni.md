# Compito per una sessione cloud: i difetti trovati nella revisione della fase 2

23/10/2026. Due revisioni del lavoro del ramo `fase-2` (già su `lavoro`) hanno trovato questi difetti, verificati leggendo il codice e, dove indicato, con prove. Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»): ramo `fase-2-correzioni` da `lavoro`, richiesta di unione in bozza verso `lavoro` con i punti come caselle, un commit per punto con il suo test, lint e suite verdi, spinto subito, riassunto in italiano alla fine.

Per ogni punto: **prima il test che fallisce**, poi la correzione.

## Dati e Proprietà

1. **Un valore scritto dopo un Annulla dalla barra si perde o va all'altra variante** (`ui/properties.py`, `_typing` e `put`, intorno alle righe 98-114).
   - Scenario: Altezza mostra 10; si scrive «1»; un clic su Annulla nella barra (i pulsanti non prendono il fuoco) riporta il progetto a 8; il campo è saltato perché ha testo non confermato; si finisce di scrivere «10» e Invio: `valueChanged` non scatta (10 è uguale al valore interno vecchio) e il progetto resta 8.
   - Se il passo annullato era un cambio di variante, il sottocampo con lo stesso id dell'altra variante riceve il testo.
   - Correzione: a `editingFinished` emettere quando il valore del campo differisce dal valore del progetto legato (non dal valore interno della casella); dopo un `restore()` (annulla, ripeti, variante) ricostruire la pagina o lasciar cadere il testo a metà.
2. **Duplicando un edificio con falde libere, le falde della copia restano sull'originale** (`model.py`, intorno alle righe 239-246): `free_pitches[*]["ring"]` ha coordinate assolute e non viene spostato. Effetti: tetto 3D fuori posto, falda sbagliata per i sottocampi disegnati sulla copia, ombre di falde inesistenti che cambiano la posa «fuori dalle ombre» degli altri sottocampi. Correzione: lo stesso spostamento sugli anelli delle falde; e `copy.deepcopy` invece di `dict(thing.params)` (oggi `params["window"]` è condiviso).
3. **Canc vale in tutta la finestra** (`shortcuts.py` riga 61, `ui/window.py` intorno a 1185): durante il disegno di un sottocampo, Canc cancella l'edificio selezionato con i suoi sottocampi. Correzione: in `_delete` ignorare il tasto se lo strumento non è Seleziona o se c'è una catena di punti aperta.
4. **Nei campi interi (`QSpinBox`: giorno, `stack`, lato di gronda, `tables`) il testo scritto a metà viene sovrascritto** quando torna un calcolo, e `stack`, `side`, `tables` mandano una modifica a ogni tasto. Correzione: `setKeyboardTracking(False)` su ogni `QSpinBox` di quelle pagine.
5. **Il campo Nome può mostrare un nome diverso dal progetto** (`ui/properties.py` righe 102-103 e intorno a 396): `isModified()` resta vero dopo Invio; svuotato il nome e premuto Invio, il progetto tiene il vecchio nome ma il campo resta vuoto finché ha il fuoco (lo stesso con gli spazi tolti). Correzione: `setModified(False)` dopo l'emissione.
6. **Scorciatoie salvate** (`ui/window.py` riga 754, `shortcuts.bindings`/`differences`): un tasto scelto dall'utente non è confrontato con le scorciatoie predefinite arrivate dopo (se «fit» era su Ctrl+L prima che l'assistente lo prendesse, Qt li vede ambigui e nessuno dei due scatta, senza dirlo); e dopo un ritorno a una versione vecchia, OK nelle Preferenze cancella i tasti dei comandi che quella versione non conosce. Correzione: `conflicts()` al caricamento con un avviso; tenere gli id sconosciuti.
7. **`quantity.py`, casi limite**: «1.500» e «1,500» diventano 1,5 senza avviso (per un italiano «1.500» è 1500: rifiutare un punto seguito da esattamente tre cifre senza decimali, con un messaggio chiaro); `"9"*400` dà `inf` e `inf-inf` dà `nan` senza errore (rifiutarli); 400 parentesi annidate danno `RecursionError` (limitare la profondità e dare `QuantityError`); il meno Unicode U+2212 è rifiutato (leggerlo come «-»).

## Viste

8. **Freccia del nord e barra di scala scivolano via in modalità Seleziona** (`ui/plan.py` righe 168-170, 475, 612, 1096, 1105-1107): sono figlie del viewport, e con `MinimalViewportUpdate` `scrollContentsBy` sposta anche loro; un clic centrale 300 px a destra le sposta di 300 px. Il test di `test_plan_aids.py` (righe 47-50) ha tolleranze troppo larghe per vederlo. Correzione: `place()` dopo `scrollContentsBy`, oppure figlie della vista e non del viewport; `place()` dopo `fit()` in `resizeEvent`.
9. **La vista dall'alto perde l'orientamento** (`camera.py` righe 100-103): `bearing()` dà 180 per ogni `look(b, -90)`, perché la direzione ha x e z esattamente nulle. Effetti: cliccando Alto già in Alto la pianta si gira con il Sud in alto (`navicube.py` 51-53); in Alto le frecce destra/sinistra vanno sempre a 135°/225° e «giù» va dal lato nord (`navicube.py` 57-69). Correzione: con la camera dritta in giù o in su, la direzione da `up()`.
10. **Il doppio clic centrale nel 3D non adatta la vista**: `QQuickWidget` trasforma il doppio clic in premi, rilascia, premi, doppio clic, rilascia, e la `MouseArea` passa il secondo premi; il navigatore (`navigation.py` 179-208) dà `['recentre', 'fit', 'recentre']` e l'ultimo ricentra ferma l'animazione dell'adatta (`ui/view3d.py` 313-345). Il test chiama solo `doubleClick`. Correzione: in `double()` sopprimere il clic al rilascio successivo; test con la sequenza vera.
11. **La vista parallela usa le formule della prospettiva** (`camera.py` 110-134 e 168-176): `ray`, `project`, `ground` e `pan` ignorano `ortho`. In parallela a 20 m dal centro un segno a terra è disegnato 31 px fuori posto, un punto sopra la camera dà `None` e il suo segno sparisce (`ui/marks.py` 104); lo zoom con la rotella senza nulla sotto il cursore punta a 2,9 m di distanza (`ui/view3d.py` 339); pan, perno e ricentra hanno lo stesso errore. Correzione: i raggi paralleli in parallela; test numerici per ognuna delle quattro funzioni.
12. **Passando sopra un modulo la quota è 0** (`viewaids.height_at` non ha il caso `"module"`, righe 46-70; `ui/plan.py` 865): la barra di stato dice «Sud, module r1c2 … z 0.00 m». Correzione: trattare `module` come `subfield`.
13. Minori:
    - stile AutoCAD: in un pan con sinistro+destro, rilasciando prima il sinistro parte un'orbita (`navigation.py` 189);
    - in pianta, se il sinistro è premuto per primo va agli strumenti e seleziona o aggiunge un vertice invece di cominciare il pan (`ui/plan.py` 646);
    - `ViewCube.paintEvent` calcola `navicube.faces()` 7 volte, circa 5 ms a ogni fotogramma: una volta sola;
    - con l'area centrale sotto circa 244 px, l'assistente aperto (minimo 220 px) taglia il campo di testo.

## Caratteri fuori dal font

14. Il primo carattere che Titillium Web non ha costa a Qt 1-2 s su Windows, una volta per processo (misurato il 23/10/2026; succede anche con Segoe UI e con ogni motore dei font). I segni delle verifiche, degli agganci e dei simboli sono già disegnati con `theme.mark()` e `theme.symbol_font()` (Segoe UI Symbol su Windows). Restano:
    - il « ✘» nel nome del sottocampo nell'albero quando la posa fallisce (`ui/window.py`, costruzione dell'albero): un'icona di `ui/marks.py` invece del carattere, e il test di `test_window.py` che oggi controlla `endswith("✘")` va aggiornato;
    - «●» delle varianti (`ui/variants.py` 49) e α, β, γ nel catalogo (`ui/catalog_dialog.py`): `symbol_font` o `mark()`.
    - Test: un controllo che nessun testo mostrato dalla finestra contenga caratteri fuori dalla tabella di Titillium Web senza `mark()`/`symbol_font` (un elenco dei caratteri ammessi letto dal file del font con `QRawFont`, o un elenco scritto a mano dei caratteri usati).
