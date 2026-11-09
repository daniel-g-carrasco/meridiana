# Da sistemare nella versione unita (`r12-quick`)

Daniel, 04/11/2026, dopo aver aperto la versione unita: «ci sono parecchie cose da sistemare. guarda gli screenshoots». Le sue schermate: `docs/quick/schermate-daniel/20261104-*.png`. Riferimento Widgets: `build/quick-foto/riferimento/` nel ramo `r12-sistema`. Regola di gusto: «la ripetizione estetica e di comportamento deve essere accurata nei limiti del possibile. Ma ciò che è semplificabile anche nella struttura estetica ben venga!».

È l'elenco di partenza della passata di integrazione e di fedeltà. Si spunta solo con la prova verde e la foto guardata accanto a quella dei Widgets.

## Da agganciare: scritti nei rami, non ancora nella finestra

- [ ] Proprietà complete, Verifiche, albero del Progetto (`Meridiana.Properties`, `Checks`, `ProjectTree`).
- [ ] Fase Impianto, cataloghi (`Meridiana.Plant`, `Catalog`).
- [ ] Produzione, Consumi, Economia, Accumulo e tutti i grafici (`Meridiana.Charts`).
- [ ] File, Impostazioni con tutte le categorie, Relazione, finestre di dialogo (`Meridiana.File`, `Settings`, `Report`, `Dialogs`).
- [ ] Meridio, conversazione, aiuto nel fumetto (`Meridiana.Assistant`).
- [ ] Tutti i comandi della barra: oggi molti sono grigi perché nessuno li ha ancora registrati (Pensilina, Oggetto 3D, Squadra, Catalogo, Scegli in automatico, Configura, Disegna e altri). I `tool_*` passano già a `PlanController.setTool`, ma quelli con opzioni vanno su `activateTool`.

## Difetti visti

### File e Impostazioni (`20261104-impostazioni.png`)
- [ ] Aprendo File resta la barra strumenti: nei Widgets la pagina prende tutto sotto le fasi, da «Torna al progetto» in giù.
- [ ] La linguetta «File» non si evidenzia, e quella di «Modellazione» resta spezzata: restano due pezzetti di curva e il numero perde il disco.
- [ ] Una sola categoria, «Aspetto»: mancano Torna al progetto, Torna a File e le altre categorie, le icone, il titolo con la sua frase, Annulla e Ripristina in fondo.
- [ ] La scheda arriva al bordo destro della finestra, senza il suo margine.

### Modellazione (`20261104-modellazione.png`)
- [ ] **Fascia dei comandi (R388):** sta in una banda bianca dentro la pianta. Va nella barra di stato in fondo, dove nei Widgets, e deve seguire lo strumento. La pianta deve arrivare ai bordi della sua scheda.
- [ ] **Inquadratura:** a finestra più grande il progetto resta piccolo al centro. Nei Widgets la vista resta inquadrata finché il progettista non la muove: `Plan.qml`, `fitted`.
- [ ] **Barra strumenti della pianta:** nei Widgets sta sopra la pianta con vista, adatta, zoom, agganci e livelli. Qui mancano quasi tutti i pulsanti.
- [ ] **Colori delle stringhe:** in Modellazione i moduli appaiono a strisce multicolori e con le etichette `7.4.1`. Controlla sui Widgets con lo stesso progetto se in questa fase devono esserci.
- [ ] **3D:** i pulsanti Inquadra, Vertici, Sposta, Agganci, Ombreggiata e Ombre sono provvisori, senza icone e con la tendina bianca. Il pulsante di vista della finestra copre «Inquadra». Nei Widgets: pulsanti tondi adatta, più e meno.
- [ ] **Sole:** nei Widgets è una barra sotto il 3D con play, giorno, cursore, ora e altezza; qui è una scatola sopra la scena, con il cursore a due colori e la data in un campo diverso.
- [ ] **Terreno del 3D:** qui è un rettangolo che finisce nel vuoto; nei Widgets arriva all'orizzonte.
- [ ] **Cubo:** lettere e punti cardinali si sovrappongono («Alto» sopra «E»); confronta con il cubo dei Widgets.
- [ ] **Proprietà:** il «?» è troppo grande e stacca dalla croce; il titolo «Sito» non è una sezione apribile.
- [ ] **Verifiche:** «Ancora niente di calcolato» è tagliato sotto la riga dei filtri; conteggi e filtri non sono le pillole e la pista dei Widgets; manca «Pronto per la consegna»; mancano copia e il numero nel titolo.
- [ ] **Progetto:** mancano conteggi, avviso con il numero, icone colorate, «Esclusioni».
- [ ] **Larghezze dei pannelli:** nei Widgets Progetto circa 310 px e Proprietà circa 370; qui circa 230 e 290.
- [ ] **Aiuto:** il pannello Aiuto sparisce (R383), ma va verificato che il «?» apra il fumetto.

### Impianto (`20261104-impianto.png`)
- [ ] Barra: i gruppi sono giusti, ma quasi tutto è grigio: vedi sopra, comandi da registrare.

## Detti poi da Daniel

- [ ] **Velocità: «la modellazione in 2d sembra tutta più lenta».** Viene prima di tutto. Il ramo della pianta ha chiesto `QSG_RENDER_LOOP=basic` per un nodo del grafo di scena scritto in Python: così il disegno sta sul filo della finestra, con l'attesa del monitor a ogni fotogramma. Va provato il render loop a thread, o una tecnica che non lo richieda. Nei Widgets: spostare la pianta 721 ms, rotella 192 ms sull'HP.
- [ ] **«le barre degli strumenti all'interno delle modellazioni sono parecchie diverse»:** quelle sopra la pianta e sopra il 3D. Devono essere quelle dei Widgets, stessi pulsanti, stessi gruppi, stesso aspetto.
- [ ] **«l'esc non fa tornare al seleziona»:** nei Widgets Esc lascia lo strumento e torna a Seleziona, nei suoi stati: `plan.py` 3587-3597 e 3616-3628.
- [ ] **«le verifiche non sono racchiuse tra sottogruppi»:** gruppi apribili per livello, oggetto, area, consegna, come in `checks_page.py`.
- [ ] **«alcune selezioni tipo dei sottocampi non sono centrate»:** contorni di selezione sfalsati rispetto all'oggetto.
- [ ] **Evidenziazione: «contorni evidenziati per i quali si vede anche dietro»:** la selezione deve essere quella dei Widgets, sia in pianta sia in 3D.
- [ ] **Rounding** ovunque: raggi e forme uguali ai Widgets.
- [ ] **Come sono disposti gli strumenti.**
- [ ] **Come si muove Meridio; il fumetto «non ha contenuti a parte l'aiuto!»:** deve avere la conversazione vera.
- [ ] **Come tra le fasi cambiano le schede e i loro contenuti:** disposizione per fase, schede prestate, ricordo delle misure (`window.py`, `arrangement`).
- [ ] **Come si controlla la modellazione, i tasti, i sottomenu, i tooltip, i menu del tasto destro.**
- [ ] **Linguette delle fasi: «Guarda che schifo come sono fatte le linguette delle fasi e come interagiscono quando si passa a file, come rimangono decentrate».** Forma, centratura e passaggio a File come in `ui/phasebar.py`.

- [ ] **Controlli dei pannelli: «i controlli dei pannelli, nascondi laterali non è come l'originale».** Nella barra di stato dei Widgets: avvisi con il numero, tre pulsanti per pannello sinistro, sotto e destro, «?», Meridio. Oggi annulla, ripeti e un solo pulsante. Vedi `panel_buttons.py`.
- [ ] **Verifiche vuote: «i contenuti in verifiche quando non c'è nulla»:** «Ancora niente di calcolato» è tagliato a metà altezza (`docs/quick/schermate-daniel/20261104-verifiche-vuote.png`). Va il messaggio vuoto dei Widgets, intero e al suo posto.

- [ ] **Rounding granulosi e sfumature: «i rounding di alcune schede tipo quella degli strumenti in alto con la sua linguetta delle fasi sono brutti e granulosi rispetto a quelli per dire di "progetto". Inoltre le loro sfumature non sono ancora fatte bene come le nostre, come se ripetessero gli errori delle sfumature diffuse su cui ci eravamo inciampati»** (`docs/quick/schermate-daniel/20261104-rounding.png`). Il `Shape` di `PhaseHeader.qml` non ha antialiasing né renderer a curve, a differenza dei `Rectangle` con raggio. Le regole ci sono già: «vai con niente ombre» (`docs/design/sistema-grafico.md`, riga 17), R38, R69 (ombre tagliate e bordi sbiaditi), R161 (sfumatura sopra i bordi).

## Visti da Claude a campione nelle foto dei rami (04/11, 18:20)

- [ ] **Terreno del 3D a strisce ondulate (moiré)**, su tutta la scena: `r13-vista3d/pilot-final-light-1/20-quick.png`. Nei Widgets è un verde uniforme. (`r13-vista3d`)
- [ ] **Moduli di colore sbagliato in pianta:** fuori stringa nei Widgets sono rossi, in Quick blu a griglia: `r13-proprieta/pilot-r04/16-pair.png`. Prese d'angolo quadrate e blu contro tonde e magenta; numeri dei lati senza disco. (`r13-pianta`)
- [ ] **Il tema predefinito non è quello deciso:** in più foto Quick ha accento bronzo e sezioni beige, i Widgets indaco e grigio. R390, R391. (`r13-shell`, `r13-controlli`)
- [ ] **Testo inglese:** «No checks to show.» nelle Verifiche; «Computation» nel menu ad Alt. (`r13-proprieta`, `r13-shell`)
- [ ] **Verifiche, riga dei titoli:** a 1920 px «Pronto per la conseg» è tagliato e le pillole gli stanno sopra. Icona copia fuori posto, sotto i filtri. Nei Widgets Questa fase e Questo oggetto vanno su una riga loro quando manca spazio, e il pulsante premuto ha un altro aspetto. (`r13-proprieta`)
- [ ] **Tendine e campi tagliati a sinistra:** «on indicata» al posto di «non indicata», «non in...» e «non indi...» dove nei Widgets si legge tutto: la colonna dei campi è troppo stretta. (`r13-controlli`, `r13-proprieta`)
- [ ] **«?» accanto al titolo «Proprietà» e «Dati» troppo grande**, già segnalato da Daniel e ancora lì. (`r13-shell`)
- [ ] **Meridio fuori posto:** fermo in mezzo alle Verifiche o sopra l'angolo della barra di stato, dove copre «Meridio»: nei Widgets sta in basso a destra nel 3D. (`r13-meridio`, `r13-shell`)
- [ ] **Barra di stato:** un «0» senza icona accanto ai pulsanti dei pannelli; messaggi di Meridio al posto della fascia dei comandi. (`r13-shell`)
- [ ] **Coppia che non confronta la stessa cosa:** `r13-shell/matrix-light1/13-pair.png` ha a sinistra File e a destra Modellazione. Controlla tutte le coppie: uno stato diverso non prova nulla. (`r13-shell`)
- [ ] **Grafici:** punti molto marcati sulla linea rispetto ai Widgets, e la linea sembra spezzata fra i punti. (`r13-fasi`)

- [ ] **Sottoschede delle Verifiche: «anche le sotto schede in verifiche.... guarda che brutte... Forme a caso e contorni spezzati. E manca la sfumatura...»** (`docs/quick/schermate-daniel/20261104-sottoschede-verifiche.png`). Porta esattamente il disegno delle righe di `ui/checks_page.py`: rettangolo, raggi, contorno continuo, spazi tra le righe, freccia, occhio. R51. **Sfumatura:** quasi certamente è quella ai bordi delle aree che scorrono: `ui/fades.py` e R161, in entrambi i temi e sopra il contenuto senza coprire i bordi. Vale per ogni area che scorre, in tutto il programma: va fatta come controllo comune.

- [ ] **Icone: «a vedere dalle sue immagini i simboli sono tutti più sfocati».** Confrontale a pixel con i Widgets, al 100 %, a scala 1 e 2. `Controls/Icon.qml` carica un'immagine con `sourceSize` e la campiona sulla scheda video, i Widgets disegnano l'SVG direttamente. Da controllare: posizioni non intere, fattore di scala, campionamento. Prova sui pixel: stessi bordi netti delle icone Widgets.

- [ ] **Tema scuro: «in modalità scura disegna una sorta di doppio sfondo»** (`docs/quick/schermate-daniel/20261105-doppio-sfondo.png`). Schede e barra hanno due toni sovrapposti. Controlla se due livelli dipingono lo stesso sfondo, se un colore con trasparenza si somma, e confronta sui pixel con i Widgets scuri: un solo `panel` su un solo fondo.

- [ ] **Spazio 2D: «verificare che i bordi dello spazio 2d siano correttamente arrotondati»** (`docs/quick/schermate-daniel/20261105-bordi-spazio-2d.png`). Il disegno della pianta deve seguire il raggio della sua scheda, senza angoli vivi o tela che esce dal bordo. Prova: ritaglio al 200 % dei quattro angoli accanto ai Widgets, anche in tema scuro.

- [ ] **Linguetta e File: «che non ci sia questo doppio bordo sotto modellazione»** (`docs/quick/schermate-daniel/20261105-file-linguetta.png`). Sotto la linguetta attiva si vede una doppia linea tra la fascia e la scheda: la linguetta deve fondersi con la scheda, un solo bordo, come nei Widgets. Prova: ritaglio al 200 % in Modellazione e in File, tema chiaro e scuro.

- [ ] **Linguetta attiva in File: «la linguetta di modellazione non sia attiva quando si è in File, ma lo sia File».** Aprendo File si accende File e si spegne la fase; tornando al progetto si riaccende la fase di prima. Prova: test sullo stato delle linguette e foto nei due stati.

## Prova vera di Daniel su r13-unita, 05/11/2026: si parte da qui

Provati con il suo mouse sulla finestra vera. Le prove automatiche passavano: **ogni voce si riproduce prima con input nativo del sistema (mouse vero o `SendInput`, finestra Direct3D), non con eventi sintetici di Qt**, e la prova che resta deve fallire prima della correzione. Prima cerca se hanno una causa comune: menu che non si chiudono, tooltip fermi e hover fermi potrebbero essere lo stesso problema (ipotesi, non verificata).

- [x] **Menu di Meridio:** «la finestrella che si dovrebbe aprire premendo su Locale su meridio rimane dal fumetto sovrapposta» (`docs/quick/schermate-daniel/20261105-prova-meridio-locale.png`): il menu resta sotto il fumetto. Deve stare sopra e leggersi tutto. *(r14-correzioni: test_provider_menu_is_above_the_bubble)*
- [x] **Cambio fase lento:** «lo spostamento tra fasi è molto lento» (`docs/quick/schermate-daniel/20261105-prova-fasi-hover.png`). Misura sullo schermo vero, anche a calcolo fermo, e confronta con i Widgets. *(r14-correzioni: prima visita da 0,9-2,2 s a 0,1-0,6 s sul desktop separato, seconda 0,1-0,4 s; a schermo vero lo dirà Daniel)*
- [x] **Hover fermo, ovunque:** «rimangono i pulsanti già premuti con l'hover attivato»; «il problema dell'hover che compare al passaggio del mouse e rimane nel caso si selezioni il pulsante c'è anche altrove (problema generalizzato) tipo nella barretta strumenti all'interno di vista 2d e 3d». Linguette delle fasi, barre di pianta e 3D e ogni altro pulsante. *(r14-correzioni: test_native, test_d02_d03)*
- [x] **Tooltip:** «grossi problemi con tooltip che rimangono impressi, non compaiono dove dovrebbero, non hanno animazioni» (`docs/quick/schermate-daniel/20261105-prova-tooltip.png`: «Ingrandisci» e «Riduci» restano uno sopra l'altro). Stesso aspetto, posizione e comportamento dei Widgets (R379: sola dissolvenza, 90 ms e 60 ms). *(r14-correzioni: test_d04, test_r379, test_r367)*
- [x] **Menu delle mappe:** «non corrisponde a quanto c'era prima: è troppo elevata, inoltre non serve a nulla. Le mappe sono nere dall'inizio, e non è possibile selezionarle» (`docs/quick/schermate-daniel/20261105-prova-menu-mappe.png`). Riporta la struttura del menu dei Widgets; le mappe devono comparire davvero, da subito. *(r14-correzioni: test_d09, D10 389x314 px come i Widgets)*
- [x] **Tutti i menu a comparsa (`Controls/Menu.qml`):** «rimane in sovraimpressione, cliccando su un'opzione, cliccando fuori, o premendo esc non succede nulla»; «è un problema generalizzato per questo tipo di finestra». Provali tutti: opzione, clic fuori, Esc, sottomenu. *(r14-correzioni: test_d05_d06, cinque tipi di menu)*
- [x] **Simboli:** «buona parte dei simboli sono sfocati». Confronto a pixel con i Widgets. *(r14-correzioni: nessuna icona fuori pixel, test_d13, dpr 1)*
- [x] **Vista 3D sfocata:** «ciò che c'è all'interno della vista 3d è sfocato». Confronta nitidezza e campionamento con i Widgets, alla scala del monitor. *(r14-correzioni: pixel interi a dpr 1, test_d12; al monitor lo dirà Daniel)*
- [x] **Terreno 3D:** «il campo verde del 3d rimane grosso all'inverosimile». Stessa estensione dei Widgets. *(r14-correzioni: test_d11)*

- [x] **Tabelle:** «ci sono anche grossi problemi con le tabelle, non hanno hover, non rispondono bene in modo dinamico». Provale tutte confrontandole con i Widgets: hover sulle righe, selezione, ridimensionamento di pannello e finestra, colonne, scorrimento, aggiornamento dei valori (R394, A + 2). Il senso esatto di «in modo dinamico» non è stato precisato: descrivi cosa trovi. *(r14-correzioni: D14, D15, D16; PlantTable resta a r14-impianto)*

- [x] **Trascinamento delle schede:** «fai verifiche anche sul trascinamento delle schede». Con cursore vero e confronto con i Widgets: da un lato all'altro, a gruppo, flottante, ritorno, disposizione ricordata. *(r14-correzioni: test_d20 con messaggi nativi; col cursore vero lo dirà Daniel)*
- [ ] **Prove di modellazione:** «prove di modellazione che includano falde, posizionamento pannelli e stringatura nei modi più disparati». Percorsi interi sui due programmi: falde di ogni tipo e pendenza, sottocampi, orientamenti, esclusioni, posa automatica e a mano, stringatura automatica e a mano, più ingressi, annulla e ripeti. Confronta risultati e verifiche, non solo l'aspetto.

- [x] **Menu a comparsa, aspetto e movimento (`Controls/Menu.qml`):** «quello andrà poi animato (si srotola verso il basso), da verificare margini interni, simmetria destra / sinistra». Apertura che si srotola verso il basso, come nei Widgets se c'è; rispetta il movimento ridotto. Prova: ritaglio al 200 % con i margini misurati a sinistra e a destra, e fotogrammi dell'apertura. Vale anche per i sottomenu. *(r14-correzioni: test_menu_unrolls_downward; margini 12 e 12 px, larghezza 389 come i Widgets)*

- [x] (`r14-ifc`, studio 32, banco `tools/ifc_banco.py`) **Importazione IFC (R399, R400; il lettore è comune ai due programmi):** «Che lo metta al centro e che dia la possibilità di spostarlo. Da rivedere la finestra di importazione perché sia fatta come si deve»; «l'import non è andato bene» (`docs/quick/schermate-daniel/20261105-ifc-*.png`, la terza è come doveva venire). «deve essere super robusto». Causa misurata delle punte: `mesh.py:210` prolunga all'infinito tutti i piani per i vertici del contorno fuori dai lati di falda, pareti fino a 50,86 m contro 12,44 m di tetto; lettore e falde salvate sono giusti. Sito del file: Revit «Default», da riconoscere.
- [x] **Vertici in 3D (R401):** «i pallini che indicano i vertici vengono mostrati anche [se] si trovano dietro il solido, mentre devono essere coperti come le linee». Anche nei Widgets. *(r14-correzioni: solo Quick, test_r401; nei Widgets da fare)*

- [x] **Viste in Impianto (R402, decisione di Daniel):** «in impianto manterrei la possibilità di avere vista 3d e divisa (tant'è che nella barretta strumenti ci sono i due tasti)». In Quick: togliere il vincolo in `Shell/Workbench.qml:411` e `:425`, provare la stringatura accanto al 3D. *(r14-correzioni: test_r402_views_in_plant)*
- [x] (`r14-ifc`: `Controls/Dialog.qml`, `Dialogs/DialogLayer.qml`, finestre di Pianta portate sul controllo comune) **Finestre di dialogo (R403):** «non hanno i giusti spazi / margini dai lati, hanno spesso dimensioni troppo grandi per i contenuti che contengono e gli esce una sorta di doppio mento». Controllo comune (`Controls/Dialog.qml`): margini uguali, altezza dal contenuto, un solo bordo in fondo. Provale tutte, con foto.

- [x] **Barra in basso (R405):** «i tasti per collassare le schede in basso a destra in quick rimangono stretti (sono deformati)». *(r14-correzioni: test_r405)*
- [x] **Confini (R406, ramo `r14-impianto`, `docs/quick/r14-impianto-esito.md`):** «a volte i testi nella scheda a destra sforano fino a sovrapporsi al punto più basso dell'intera finestra. In particolare andrebbe fatto un controllo di confini, come avevamo fatto in versione non quick».
- [x] **Scheda destra di Impianto (R407, ramo `r14-impianto`):** «sembra non centrare nulla con quella non quick». Spiega perché e riportala com'era.
- [x] **Riepilogo nella barra di Impianto (R419, ramo `r14-impianto`):** moduli e kWp, collegati e scollegati, inverter, ingressi, ottimizzatori, e accanto i dati della selezione, in tempo reale.
- [x] **Ottimizzatori sulla pianta (R424, ramo `r14-impianto`):** un quadratino per unità, la stringa da unità a unità, cavi sottili ai moduli.
- [x] **Tooltip del modulo sotto il cursore (R425, ramo `r14-impianto`):** segue il modulo, cambia subito, sparisce uscendo. Va con la correzione dell'hover di `r14-correzioni`.

- [ ] **Doppia falda (R408):** «si apre questa finestra nell'edificio [...] una strana granulometria sulle pareti e ombreggiamenti a righine strane» (`20261105-doppia-falda-finestra.png`, `20261105-pareti-granulose.png`).
- [ ] **Simbolo Falda (R409):** «ha una freccetta verso il basso in più che non ci deve essere» (`20261105-simbolo-falda.png`).
- [ ] **Colmo (R410):** «il colmo non viene posizionato dove lo disegno ma in centro all'edificio».
- [ ] **Vertice singolo (R411, supera R357):** muove solo quel vertice senza cambiare tipo di copertura; su un rettangolo piano i contigui salgono un po' e l'opposto resta fermo; tutti e quattro si muovono solo se selezionati tutti.
- [ ] **Più vertici (R412):** «se tengo premuto ctrl per premere più vertici allora devo vedere un più vicino al cursore. Maiusc non funziona perché attiva il gizmo di rotazione (da correggere il messaggio di help)».

- [ ] **Gronda, colmo e pendenza (R413):** «se cambio altezza di gronda non viene cambiata la pendenza. Ci deve essere un coso a spunta che ti fa decidere, quando si cambia la pendenza di una falda, se mantenere intatta l'altezza di colmo o quella di gronda. Secondo me ha priorità quella di colmo (default)».

- [ ] **Posa (R417, R418):** potenza obiettivo («voglio 45kw di picco»); allineati (predefinito), sfalsati di mezzo modulo, liberi migliorata (`20261105-posa-disallineata.png`).

- [ ] **Lato del sottocampo:** «se premo sul lato del sottocampo allora mi permette di ridimensionarlo mantenendolo un rettangolo o quello che è». Comportamento da mantenere e provare in Quick, con i moduli che si ridispongono secondo R418.

## Dalla versione unita (r13-unita, 05/11/2026)

Suite Quick in `r13-unita`: 600 prove, 9 fallite, 34 saltate, 2 fallimenti attesi. Cinque erano dovute al catalogo italiano assente all'avvio e passano rifatte con il catalogo. Ne restano quattro, su tre problemi:

- [x] **Tabelle:** `tests/quick/grafici/test_tables.py:163` vuole il titolo di colonna a peso 400, ora è 500. Confronta con i Widgets sui pixel (R394, A + 2), poi correggi il controllo o la prova. *(r14-correzioni: titolo a peso 400, come QHeaderView dei Widgets (Text.SECONDARY))*
- [x] **Pannelli:** `tests/quick/sistema/test_shell.py:91`, trascinando il bordo destro parte una chiamata a `shell.layoutFor`, sempre una, dal timer di `Workbench.qml:84`. Trova cosa lo riavvia (`layoutNeeds` della fascia?) e toglila dal trascinamento. *(r14-correzioni: la chiamata era il riordino rimasto dal resize di setUp, non il trascinamento; test_shell passa)*
- [ ] **Registro di compatibilità:** `tools/quick_rif_registry.py --check` dà 126 errori e `tests/quick/parity/test_registry.py` ne segnala 242 nell'inventario, perché le fonti sono cambiate con la passata. Rigenera le righe delle fonti senza perdere gli stati; nessuna voce va segnata fatta senza prova.

Viste sulle foto:

- [x] **Icona di Meridio** nella barra di stato: ingranaggio in tema chiaro, puntino in tema scuro, e le icone vicine si spostano. Deve essere la stessa nei due temi. *(r14-correzioni: il disegno dei Widgets in entrambi i temi, foto guardata)*
- [x] **Catalogo italiano:** `locale/` non è in git. In un albero nuovo `i18n.setup('it')` non lo trova e il programma resta in inglese senza dire nulla, e le prove sui numeri falliscono con messaggi fuorvianti. Serve un errore chiaro o la compilazione all'avvio delle prove. *(r14-correzioni: tests/_setup.py lo compila se manca)*
- [ ] **Peso delle prove:** `docs/quick/confronto` e le altre foto pesano circa 200 MB. Vanno fuori da git, con un modo per rifarle, prima di qualsiasi unione in `main`.

## Da chiudere o misurare

- [x] **Chiusura durante il calcolo:** in una prova la finestra non si è chiusa entro 150 s: probabilmente aspetta la fine dell'anno. Deve chiudersi subito, annullando il calcolo. *(r14-correzioni: test_closing_during_a_year_does_not_wait_for_it, meno di 1,5 s)*
- [ ] **Fluidità a schermo sul Dell al 200 %:** con `tools/quick_fluidity.py --on-screen --real-views --plan-renderer geometry`, contro i Widgets: spostare la pianta deve stare almeno sui 720 ms misurati sull'HP.

## Richieste arrivate durante r14-correzioni

Le parti che valgono solo per i Widgets sono in `docs/quick/stato/r14-correzioni.md`.

- [ ] **R408, grana sulle pareti:** in Quick `shadowBias` 1: la grana sul muro sparisce, foto a 200 % guardata (pixel con bordo da 5,87 % a 5,26 %). Le righine a terra della foto di Daniel non le ho riprodotte, né prima né dopo: da rivedere con Daniel. Widgets da fare.
- [x] **R409, freccia in più su Falda:** in Quick non c'è, foto guardata. Widgets da fare.
- [x] **R410, colmo dove è disegnato:** `test_r410`, `tests/nucleo/test_roof_ridge_kept.py`; solo contorni a quattro lati e colmo di un segmento, gli altri restano sull'asse. Widgets da fare.
- [x] **R411, un vertice di un tetto piano:** `tests/nucleo/test_roof_vertices.py`, vale per i due programmi. Da confermare con Daniel: l'interpretazione è nello stato.
- [x] **R412, Ctrl per più vertici:** `test_r412`, in 3D. In 2D la selezione di più vertici non esiste: niente da mostrare. Widgets da fare.
- [x] **R413, colmo fermo:** `tests/quick/proprieta/test_ridge_kept.py`. Solo Quick, calcolo nel nucleo.
- [x] **R430, parte bassa sotto la barra:** `test_r430`, su desktop separato, senza barra di Windows vera: da rivedere con la mano di Daniel. Quick non salva la geometria della finestra.
- [x] **R431, la pianta non si sposta:** `test_r431`, selezione, sezioni di Impianto, bordo del pannello.
- [x] **R437, calcoli conservati e stato unico:** `tests/quick/shell/test_year_kept.py`, `tests/quick/percorsi/test_native_year.py`.

