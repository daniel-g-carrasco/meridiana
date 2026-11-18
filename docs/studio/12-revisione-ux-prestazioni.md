# Revisione UX e prestazioni

22/10/2026. Daniel ha provato Meridiana e ha notato:
- la navigazione tra schede e finestre è a scatti e lenta, a volte non prende input, a volte la rotella non scorre;
- chiuso il pannello Proprietà, non si capisce come riaprirlo;
- lato UX e velocità non sembra pensato alla grande.

Ha chiesto una revisione completa: tutte le criticità, le proposte di miglioramento, scorciatoie come nei CAD (Ctrl+B per la barra laterale, Ctrl+1 per le proprietà), funzioni nelle viste 2D e 3D per navigare e modellare, per capire dov'è il nord, per mettere in risalto le criticità.

Codice esaminato: 327a3bc, quello che Daniel ha provato. [V] = misurato o letto nel codice, [I] = dedotto.

## In breve

1. **Il calcolo che torna blocca la finestra 2-3 secondi** [V].
   - A ogni modifica il calcolo dell'energia riparte in background e dopo 3-5 s torna.
   - A quel punto la finestra ridisegna 177 formule (244 sul progetto grande) e tutti i grafici, anche quelli nascosti, e per 2-3 s non risponde.
   - Per questo l'input «a volte» si perde: dipende da quando torna il calcolo.
   - Con una cache delle formule e i grafici disegnati solo quando si vedono il blocco scende a 0,06-0,24 s [V, prova].
2. **La rotella cambia i valori invece di scorrere** [V].
   - Sopra un campo numerico o una lista, la rotella cambia il valore anche se il campo non ha il focus, e la pagina non scorre più.
   - Ogni valore cambiato così è una modifica vera: un passo di annullamento e un calcolo che poi blocca.
   - Sopra i grafici la pagina non scorre.
3. **Un valore digitato a metà finisce nel progetto** [V].
   - Il pannello Proprietà si ricostruisce da 2 a 4 volte per ogni modifica.
   - Se in quel momento si sta scrivendo nel campo successivo, il campo viene distrutto e il valore scritto a metà viene salvato: «0,07» è diventato 0,0, su Windows e su Linux.
   - È un errore sui dati, non solo di comodità.
4. **Il pannello chiuso non si ritrova** [V].
   - Nessun menu lo riapre: si riapre solo col clic destro sulla barra degli strumenti, e il programma lo ricorda chiuso alla riapertura.
   - Lo stato salvato di Daniel ha proprio Proprietà nascosto e la vista solo pianta.
5. **La pianta si ridisegna tutta a ogni movimento del mouse** [V].
   - Costo: 14-17 ms sul progetto di prova, 60-70 ms su un progetto di 4.682 moduli (circa 15 immagini al secondo).
   - Senza ridisegno al passaggio si scende al limite del refresh dello schermo [V, prova].
6. **I risultati arrivano tardi** [V].
   - Il calcolo dell'energia impiega 3-5 s. Quasi la metà è il punto di massima potenza dei moduli, calcolato con il metodo più lento di pvlib.
   - Con il metodo vettoriale lo stesso calcolo passa da 1,8 s a 0,02 s, con risultati identici (differenza 2·10⁻¹³ W).

Le correzioni dei punti 1-6 sono piccole e misurabili: sono la fase 1 del piano (sezione 7). Il resto (scorciatoie, pannelli, nord, criticità nelle viste) è la fase 2.

## 1. Come è stata fatta

- **Lettura del codice dell'interfaccia.** window.py, plan.py, properties.py, view3d.py con Scene.qml, energy_pages.py, charts.py, pedigree.py, checks_page.py, sunbar.py, tileloader.py, catalog_dialog.py, più gli studi già fatti (05-stato-dell-arte-ux, 05a).
- **Misure con la finestra vera** guidata da eventi simulati, senza toccare il puntatore.
  - Gli script sono fuori dal repository, in `C:\Users\utente\dev\meridiana-prove\ux-2026-10-22`: probe.py per la finestra, micro.py per le prove mirate, energy_profile.py per il calcolo.
  - Risultati e screenshot di ogni giro sono in `misure\`.
  - Un timer da 1 ms misura ogni intervallo in cui la finestra non risponde («blocco»).
  - Ogni funzione dell'interfaccia è cronometrata.
  - Due progetti:
    - quello di prova (capannone di Rho, 188 moduli);
    - uno grande: 1.394 moduli sul tetto e 3.288 a terra, 4.682 in tutto.
- **Windows**: il PC dell'ufficio, con le finestre sullo schermo secondario (1080×1920, scala 1, 60 Hz). La vista 3D usa Direct3D 11.
- **Linux**: il laptop con Niri (Wayland, OpenGL), per controllare che i comportamenti siano gli stessi.
- **Prove delle correzioni**: tre correzioni applicate solo nello script, misurate prima e dopo.
- **Limiti**:
  - Sul laptop il calcolo dell'energia non parte: per Python 3.15 non esiste h5py, che pvlib richiede.
  - La rotella simulata non risale ai widget genitori come quella vera. Il comportamento è quindi dedotto da cosa fa ogni widget con l'evento (se lo «accetta», Qt non lo passa all'area che scorre) [V per l'accettazione, I per lo scorrimento].

## 2. I tre problemi che hai visto, spiegati

### 2.1 Scatti, lentezza, input che non arriva

| Cosa succede | Quanto [V] | Perché |
|---|---|---|
| Torna il calcolo dell'energia, 3-5 s dopo ogni modifica | finestra ferma 2,0-2,2 s sul progetto di prova, 2,5-3,1 s su quello grande, più un secondo blocco di 0,7-1,0 s | `_energy_done` aggiorna tre pagine. La genealogia del calcolo («Come si calcola») disegna ogni formula come immagine con matplotlib: 177 immagini, 1,5-2,1 s. I grafici (16 e più) si rifanno da zero, anche nelle schede nascoste: 1,5-2,0 s. La genealogia della produzione si disegna due volte (`show_results` e poi `show_strings`). |
| Movimento del mouse sulla pianta | 14-17 ms per movimento sul progetto di prova, 60-70 ms (p95 93 ms) su quello grande | `PlanView` ridisegna tutto il viewport (`FullViewportUpdate`, plan.py:103) e `_update_cursor` chiede il ridisegno a ogni movimento (plan.py:678), anche con lo strumento Seleziona, dove nulla segue il puntatore. Pesano i poligoni dei moduli: senza ortofoto il costo è quasi lo stesso (64 contro 69 ms). |
| Apertura del progetto | due blocchi di 1,1-1,5 s | 0,9-1,0 s sono di `expandAll` dell'elenco delle verifiche (checks_page.py:93): con l'a capo attivo e righe di altezza diversa, su un albero non ancora visibile. La stessa operazione su un albero visibile, o con righe uguali, costa 7-9 ms. |
| Prima apertura di Consumi e Bilancio | 80-185 ms | i grafici si disegnano lì a misura (matplotlib, `layout="constrained"`); le volte dopo 15-40 ms. |
| Una modifica sul progetto grande, nella scheda Modello | 0,35-0,53 s per finire, blocchi di 85-150 ms | la pianta si ridisegna due volte (`_show_all` e `_layout_done`), la scena 3D si ricostruisce tutta (48 ms), le proprietà si rifanno, le tre pagine dell'energia si riempiono anche se non si vedono. |
| Il riquadro della correzione «fuori dalle ombre» | 30-40 ms sul progetto di prova, sul thread della finestra | `checks.gather` rifà la posa del sottocampo (`_count_out_of_shadows`, checks.py:210) a ogni posa e a ogni calcolo, solo per scrivere «102 moduli invece di 188». Sul progetto grande una posa costa 0,3-0,4 s. |

La finestra non si ferma «a caso». Si ferma quando torna un lavoro partito prima (posa o energia), ed è per questo che sembra imprevedibile. Durante il blocco le pressioni dei tasti restano in coda e arrivano dopo; i clic invece arrivano su una finestra che nel frattempo è cambiata.

### 2.2 La rotella che non scorre

| Widget sotto il puntatore | Cosa fa la rotella senza focus [V] |
|---|---|
| campo numerico (QDoubleSpinBox, QSpinBox) | cambia il valore di un passo e trattiene l'evento: la pagina non scorre |
| lista a discesa (QComboBox) | cambia la voce scelta e trattiene l'evento |
| grafico (matplotlib) | trattiene l'evento senza fare nulla: la pagina non scorre |
| testo, cursore a slitta | lascia passare l'evento: la pagina scorre |

Le pagine Produzione, Consumi, Bilancio e il pannello Proprietà sono quasi tutti campi: appena il puntatore passa sopra un campo, lo scorrimento si ferma e il valore cambia.
- Misurato nella pagina Produzione: la rotella sopra «Sporcamento» lo ha portato da 2,5 a 2,4, la pagina non si è mossa, e nell'annullamento è comparso un passo «Cambia sporcamento».
- Poi è ripartito il calcolo, con il suo blocco di 2-3 s.
- Su Linux lo stesso.

### 2.3 Il pannello Proprietà

- I due pannelli («Progetto» e «Proprietà») si chiudono con la crocetta, ma nessun menu li riapre: la funzione `toggleViewAction` di Qt non è usata.
- L'unica via è il menu del clic destro sulla barra degli strumenti, che Qt crea da sé e nessuno conosce.
- Alla chiusura la disposizione viene salvata: alla riapertura il pannello resta chiuso.
- Lo stato salvato sul PC di Daniel (letto da window.json) ha Proprietà nascosto e la vista «Pianta».

## 3. Tutte le criticità

Gravità: A alta (perde dati o blocca), M media, B bassa. Costo: S poche ore, M un giorno o due, L di più.

### 3.1 Prestazioni

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| P1 | Il ritorno del calcolo blocca 2-3 s (formule e grafici, anche nascosti) [V] | A | Cache delle immagini delle formule (stesso testo, colore, dimensione); grafici e genealogia disegnati quando si vedono; una sola genealogia per risultato. Provato: 0,06-0,24 s [V]. | S |
| P2 | La pianta si ridisegna tutta a ogni movimento del mouse [V] | A sui progetti grandi | Con Seleziona nessun ridisegno al passaggio (provato [V]); con gli strumenti di disegno solo il rettangolo della sovrimpressione; moduli, edifici e ortofoto in un'immagine messa da parte e rifatta solo quando cambiano o si sposta la vista. | S + M |
| P3 | Apertura: 1 s per l'elenco delle verifiche [V] | M | Righe di altezza uniforme, oppure riempire l'albero quando la scheda si apre (micro-prova: da 969 a 7-9 ms [V]). | S |
| P4 | La correzione «fuori dalle ombre» rifà la posa sul thread della finestra [V] | M, A sul grande | Contare i moduli nel lavoro di posa (in background) e passare il numero alle verifiche. | S |
| P5 | Ogni modifica rifà tutto: pianta 2 volte, albero 2, proprietà 2-4, pagine dell'energia anche nascoste, scena 3D intera, verifiche [V] | M | Aggiornare solo ciò che è cambiato; le pagine nascoste si aggiornano quando si aprono; le proprietà cambiano i valori senza ricostruire (vedi I1). | M |
| P6 | Il calcolo dell'energia impiega 3-5 s; il punto di massima potenza è calcolato con `brentq` elemento per elemento (components.py:97) [V] | M | `max_power_point(..., method="chandrupatla")`: 26 ms contro 1.805 ms su 8.760 punti, risultato uguale a 2·10⁻¹³ W [V]. Poi le curve «cosa succede se» (taglia e accumulo, 17 bilanci annuali) calcolate dopo i risultati principali, o quando si apre la loro scheda. I cicli in Python puro nel thread di calcolo tengono il GIL e rallentano anche la finestra, mentre numpy e pvlib lo rilasciano: meglio vettoriali, o in un processo a parte (12a, 5.2). | S |
| P7 | Nessun segno che si sta calcolando, nessun annullamento: un risultato vecchio resta come se fosse nuovo [V] | M | Barra di stato: «Calcolo in corso…» con un pulsante per annullare; «risultati da aggiornare» quando il progetto è cambiato dopo l'ultimo calcolo. | S |
| P8 | Le tessere dell'ortofoto si leggono dal disco sul thread della finestra (tileloader.py:54): 86 ms all'apertura [V] | B | Lettura in un thread del pool. | S |
| P9 | Ogni modifica serializza tutto il progetto in JSON tre volte: due istantanee e la chiave «modificato» del titolo (`_state_key`) [V] | B oggi | Lo stato «salvato» dall'`isClean()` della pila di annullamento. | S |
| P10 | La vista 3D in QQuickWidget fa aspettare il refresh dello schermo a ogni ridisegno della finestra (16,5 ms contro 10-14 senza 3D) [V]. QQuickWidget disattiva il render loop a thread, quindi il 3D condivide il thread della finestra: un motivo in più per non bloccarlo (12a, 5.4). | B | Tenerla. La vista in una finestra nativa (createWindowContainer) è stata provata: con il rendering in un thread si blocca, perché la geometria e l'istanziazione scritte in Python vengono chiamate da quel thread; con il rendering sul thread principale va peggio (67 ms al passaggio, cambi di scheda fino a 330 ms) [V]. Ha anche bug aperti su Wayland e sul focus. | - |

### 3.2 Input e dati

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| I1 | Un valore scritto a metà viene salvato quando il pannello si ricostruisce («0,07» diventa 0,0) [V]. Succede perché `_page` sposta il focus sul pannello prima di togliere la pagina vecchia (properties.py:112-118): il campo perde il focus e conferma quello che contiene. | A | Subito: bloccare i segnali dei campi della pagina vecchia prima di spostare il focus. Provato [V]: nessun valore spurio, e la pagina si ricostruisce 2 volte invece di 4. Il testo che si stava scrivendo però si perde ancora, quindi poi: non ricostruire la pagina se cambia solo un valore, e non toccare un campo che ha il focus con testo non confermato. | S, poi M |
| I2 | La rotella cambia i valori senza focus [V] | A | Un filtro di eventi per tutta l'applicazione: su campi numerici e liste, la rotella cambia il valore solo se il campo ha il focus, altrimenti passa all'area che scorre. Il focus si prende col clic, non con la rotella. Provato [V]: il valore resta e l'evento passa oltre. | S |
| I3 | Sopra i grafici la pagina non scorre [V] | M | Il grafico lascia passare la rotella (non la usa). | S |
| I4 | Tenendo premuta la freccia di un campo, il campo viene ricostruito sotto il mouse: la ripetizione si ferma e il focus salta [I, dal meccanismo misurato in I1] | M | Come I1, aggiornamento senza ricostruire. | M |
| I5 | Ogni clic sulle frecce di un campo è una modifica completa: un passo di annullamento, una posa, un calcolo [V] | M | Raccogliere i clic ravvicinati sullo stesso campo in un solo passo (`mergeWith` della pila) e far partire posa e calcolo dopo una breve pausa (300-500 ms). | S |
| I6 | Il campo «Elimina» del menu Modifica non ha scorciatoia; Canc funziona solo se la pianta ha il focus [V] | B | Canc come scorciatoia dell'azione, attiva nelle viste e nell'albero. | S |

### 3.3 Pannelli, menu, comandi

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| N1 | I pannelli chiusi non si riaprono dai menu [V] | A | Menu Vista > Pannelli con Progetto (Ctrl+B), Proprietà (Ctrl+1), Verifiche (Ctrl+J), Cronologia; Schermo pulito (Ctrl+0); «Ripristina la disposizione predefinita». | S |
| N2 | Nelle schede dei risultati restano i pannelli del modello, che tolgono circa 600 px e mostrano proprietà che lì non servono [V, screenshot] | M | Il pannello di destra diventa un ispettore che cambia con la scheda: nei risultati periodo, variante, filtri, legenda. L'albero resta, per filtrare per sottocampo e variante. Niente pannelli che spariscono da soli, che disorientano; per avere spazio bastano Ctrl+0, Ctrl+B, Ctrl+1 (12a, 4.2 e 4.7). | M |
| N3 | Albero del progetto: si ricostruisce a ogni modifica (perde scorrimento e selezione), non mostra cosa è selezionato, le esclusioni si chiamano e1, e2, e3, non ha icone né menu contestuale [V] | M | Aggiornamento senza ricostruire; selezione sincronizzata con pianta e 3D; nomi per tipo («Lucernario 1»); icone; menu contestuale con Rinomina, Elimina, Duplica, Inquadra. | M |
| N4 | Nessun menu contestuale su pianta, 3D e albero [V] | M | Clic destro: Proprietà (Ctrl+1), Inquadra, Posa moduli o Togli, Squadra, Elimina, e per un modulo «Togli dalla posa». | M |
| N5 | Barra degli strumenti di sole parole e tutta su una riga: annulla, strumenti, modi di vista, variante [V] | M | Icone con testo breve; gruppi separati (Disegno, Vista, Calcolo); suggerimenti con la scorciatoia («Edificio (B)»). | M |
| N6 | Le scorciatoie si scoprono solo leggendo i menu; gli aiuti al disegno (lunghezze digitate, R, Maiusc, Ctrl, Spazio) solo nel suggerimento in basso [V] | M | Elenco delle scorciatoie con ricerca (Ctrl+?, F1) e una tabella stampabile; ricerca dei comandi (sezione 5). | S |
| N7 | Solo la pagina Produzione dice che si sta calcolando; dal Modello non si vede [V] | M | Indicatore nella barra di stato (P7). | S |
| N8 | Il suggerimento e i messaggi temporanei usano la stessa riga della barra di stato e si coprono [V] | B | Messaggi temporanei a destra, o come avviso che si chiude da sé. | S |
| N9 | Scelte già indicate nello studio 05 e non ancora fatte: pannello «Problemi» agganciabile, ricerca dei comandi, cronologia degli annullamenti, interruttori degli agganci e scala nella barra di stato, avvisi con «Annulla» al posto delle conferme [V] | M | Fasi 2 e 3. | M |

### 3.4 Pianta (2D)

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| V1 | Niente indica il nord: la pianta è sempre col nord in alto, ma non lo dice (con lo sfondo «nessuno» non c'è altro riferimento) [V] | M | Freccia del nord in alto a destra, sempre della stessa grandezza; il giorno in cui si potrà ruotare la pianta (allineata all'edificio) ruoterà con lei. | S |
| V2 | Niente barra di scala né griglia [V] | M | Barra di scala in basso a sinistra (1-2-5 × 10ⁿ m); griglia attivabile. | S |
| V3 | Nessuna evidenza di cosa si selezionerà al passaggio del mouse [V] | M | Contorno più chiaro dell'oggetto sotto il puntatore, con il nome in un suggerimento. È anche ciò che fa capire cosa si può cliccare. | S |
| V4 | Livelli non regolabili: ortofoto, moduli, stringhe, quote, esclusioni, ombre [V; solo le stringhe hanno W] | M | Pannello o menu «Livelli», con visibilità e trasparenza dell'ortofoto. | M |
| V5 | La misura sparisce al clic successivo; nessuna quota che resta [V] | B | Quote che restano, come annotazioni da togliere o stampare. | M |
| V6 | Le ombre e la direzione del sole non si vedono in pianta [V] | M | Freccia del sole nell'ora scelta e, a richiesta, le ombre del giorno di progetto sovrapposte (le stesse che la posa usa per «fuori dalle ombre»). | M |
| V7 | Il nome e i kWp dei sottocampi non sono scritti in pianta; le quote solo sull'oggetto selezionato [V] | B | Etichette con nome, moduli e kWp, attivabili. | S |
| V8 | La lunghezza di un lato si cambia in una finestra di dialogo [V] | B | Campo in sovrimpressione sul lato stesso, come le lunghezze digitate mentre si disegna. | M |
| V9 | Zoom e inquadrature: solo F (adatta) | B | Inquadra la selezione; zoom con + e −; ritorno alla vista precedente. | S |

### 3.5 Vista 3D

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| T1 | Niente indica il nord né l'orientamento; niente viste standard [V] | A per la richiesta | Cubo di vista in alto a destra con N, E, S, O sulle facce e sugli spigoli: un clic porta alla vista da quella parte. Rosa dei venti sul terreno attorno alla scena. Viste dall'alto, da sud, da est, da ovest, da nord, assonometria. | M |
| T2 | Si possono scegliere solo i moduli: clic su edifici e sottocampi non fa nulla (il segnale `buildingPicked` non è collegato) [V] | M | Selezione di edifici, falde, sottocampi ed esclusioni anche in 3D, la stessa della pianta. | M |
| T3 | L'orbita gira attorno a un punto fisso: niente zoom verso il puntatore, niente perno sulla selezione [V] | M | Zoom verso il punto sotto il puntatore; perno sulla selezione; doppio clic per centrare. | M |
| T4 | Nessuna evidenza al passaggio, nessuna etichetta [V] | B | Come V3. | M |
| T5 | Il sole si muove nell'ora scelta, ma il suo percorso non si vede [V] | M | Arco del percorso del sole nel giorno scelto, con le ore. | M |
| T6 | Ombre ad altissima qualità sempre attive (mappa «VeryHigh», PCF8, MSAA alta) [V] | B | Qualità regolabile (buona, alta), utile sul laptop. Oggi il 3D è veloce: 0,2-1 ms di disegno, 45-57 fotogrammi al secondo in orbita [V]. | S |

### 3.6 Criticità nelle viste

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| C1 | Le verifiche stanno solo nella loro scheda; nelle viste non c'è nulla [V] | A per la richiesta | Un segno sull'oggetto (⚠ o ✘ con il numero), in pianta e in 3D, che porta alla voce. | M |
| C2 | I moduli hanno un solo colore (più le stringhe) [V] | M | Colori per modulo a scelta: perdita per ombra, stringa, fuori stringa, irraggiamento; con la legenda. È ciò che fanno Aurora e HelioScope (studio 05). | M |
| C3 | Il numero delle criticità c'è solo nel titolo della scheda [V] | M | Contatore nella barra di stato, cliccabile; Ctrl+Maiusc+M porta all'elenco e le frecce scorrono le voci, con le viste che seguono (o F8, se Daniel lo vuole lì: sezione 5). | S |
| C4 | Nell'elenco un clic singolo non mostra nulla: serve il doppio clic, che cambia scheda [V] | B | Clic: l'oggetto si evidenzia nelle viste. Doppio clic: ci si va. | S |
| C5 | Le note della posa compaiono solo in fondo alle proprietà [V] | B | Anche come segno sull'oggetto (C1). | S |
| C6 | In pianta la selezione (#ffb000) e l'avviso (#fab219) sono lo stesso giallo: distanza OKLab 0,9 [V, studio 13] | M | Colori diversi per selezione e criticità; selezione con un alone a due toni, che resta visibile anche sull'ortofoto (studio 13). | S |

### 3.7 Chiarezza e coerenza

| N. | Criticità | Gr. | Correzione | Costo |
|---|---|---|---|---|
| K1 | Moduli lunghi senza sezioni comprimibili né ricerca (Produzione: 917 px da scorrere) [V] | B | Sezioni comprimibili che ricordano lo stato; i valori diversi dal predefinito evidenziati (KDE HIG: arancione per i valori non predefiniti). | M |
| K2 | Proprietà e pagine dell'energia mostrano campi senza dire se il valore è predefinito o scelto | B | Come K1, con «ripristina il predefinito» accanto al campo. | M |
| K3 | Alcuni comandi esistono solo in un posto: «Pick on the plan» nelle proprietà, il doppio clic sul lato in pianta | B | Menu contestuale e ricerca dei comandi (N4, sezione 5). | S |
| K4 | Su Niri «Chiaro» e «Scuro» delle impostazioni non fanno nulla: con il tema del portale che app.py imposta, `setColorScheme()` non ha effetto. Se il sistema cambia tema a programma aperto, la palette resta quella vecchia [V, studio 13] | M | Stile Fusion con una palette completa scelta da Meridiana, rifatta al segnale `colorSchemeChanged`; provato nei due versi su Linux e su Windows (studio 13). Va fatto insieme al tema nuovo. | S |

### 3.8 Cosa funziona bene, da tenere

- Annulla e ripeti per istantanee del progetto: semplice ed esatto.
- La posa in un thread, con il numero di generazione che scarta i risultati vecchi.
- La vista 3D: un'unica geometria per gli edifici, i moduli per istanze, disegno su richiesta. Disegnare costa 0,2-1 ms e l'orbita va a 45-57 fotogrammi al secondo anche con 4.682 moduli [V].
- Gli aiuti al disegno: agganci, lunghezze e angoli digitati, rettangolo da tre clic, Maiusc per tenere la direzione, Ctrl per disegnare libero.
- Le verifiche con la fonte e il pulsante «Correggi».
- I modi di vista (pianta, 3D, affiancate) che cambiano in 4-9 ms su Windows [V].

## 4. Le scelte, con le alternative

Voti da 1 a 5 per efficacia, rischio (5 = poco) e costo (5 = poco).

**4.1 Il blocco al ritorno del calcolo (P1, P6)**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A. Cache delle formule, grafici e genealogia disegnati quando si vedono, punto di massima potenza vettoriale | 5 | 5 | 5 | provata: 2-3 s diventano 0,06-0,24 s [V] |
| B. Disegnare grafici e formule in un thread e mostrare immagini | 4 | 2 | 3 | matplotlib non è fatto per più thread; più codice |
| C. Cambiare libreria dei grafici delle schede: pyqtgraph (MIT, veloce), con matplotlib solo per il PDF | 4 | 3 | 2 | grafici interattivi più rapidi, ma va rifatta la palette validata. Qt Charts è deprecato dalla 6.10, Qt Graphs 2D vive solo in QML (12a, 5.5) |

**Raccomandazione: A subito**; C solo se dopo A i grafici restano il collo di bottiglia.

**4.2 La pianta (P2)**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A. Nessun ridisegno al passaggio con Seleziona; con gli strumenti solo la sovrimpressione | 4 | 5 | 5 | provata per Seleziona [V] |
| B. Strato statico (ortofoto, edifici, moduli) in un'immagine rifatta solo quando serve | 5 | 4 | 3 | il disegno di 4.682 moduli si paga una volta per inquadratura |
| C. Viewport OpenGL per la QGraphicsView | 3 | 2 | 4 | si aggiunge un'altra superficie RHI accanto a quella del 3D |

**Raccomandazione: A subito, B nella fase 2.**

**4.3 Il pannello Proprietà (I1, I4, P5)**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A. Bloccare i segnali della pagina vecchia prima di spostare il focus | 3 | 5 | 5 | provata: chiude l'errore sui dati [V], non la perdita del testo che si sta scrivendo |
| B. Aggiornare i valori senza ricostruire; ricostruire solo se cambia l'oggetto o la forma del modulo (per esempio il tipo di tetto) | 5 | 4 | 3 | risolve anche focus, ripetizione, scatti |
| C. Un modello dati con legami ai campi (stile model/view) | 5 | 3 | 2 | più ordinato, ma più lungo |

**Raccomandazione: A subito, B subito dopo.**

**4.4 La vista 3D: QQuickWidget o finestra nativa (P10)**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A. Tenere QQuickWidget | 4 | 5 | 5 | 16,5 ms per ridisegno della finestra, accettabile dopo P1-P2 |
| B. QQuickView con createWindowContainer | 2 | 1 | 2 | provata: blocco con il rendering in un thread, più lenta con quello principale; in più scorciatoie e focus da gestire a parte [V] |

**Raccomandazione: A** [V].

**4.5 Dove vanno i pannelli nelle schede dei risultati (N2)**

| Strada | Efficacia | Rischio | Costo | Note |
|---|---|---|---|---|
| A. Ogni scheda ricorda i suoi pannelli visibili | 4 | 3 | 4 | i pannelli che si spostano da soli disorientano (Visual Studio); Apple chiede di non nascondere la barra laterale |
| B. Una sola disposizione: il pannello di destra cambia contenuto con la scheda (proprietà nel Modello, impostazioni e legenda nei risultati), l'albero filtra i risultati | 5 | 4 | 3 | come gli ispettori di Microsoft e Apple |
| C. Lasciare com'è | 1 | 5 | 5 | |

**Raccomandazione: B**, con Ctrl+0, Ctrl+B e Ctrl+1 per chi vuole tutto lo spazio.

## 5. Scorciatoie

La ricerca completa, con le fonti, è in `12a-convenzioni-ux.md`, sezione 1. Copre:
- AutoCAD, Revit, SketchUp, Blender, FreeCAD, QGIS;
- i programmi fotovoltaici e DIALux;
- VS Code e JetBrains;
- i conflitti con Windows 11, GNOME, Niri, la tastiera italiana e i tasti funzione del Framework 13.

**Principi**
1. **Una famiglia per categoria**, così i conflitti fra programmi si risolvono con una regola:
   - pannelli, ricerca dei comandi e verifiche come negli IDE (VS Code);
   - ausili al disegno, mouse e alias come in AutoCAD;
   - strumenti a lettera singola come Aurora, HelioScope e SketchUp.
2. **Mai un comando solo su un tasto F.** Sul Framework 13, senza Fn bloccato, i tasti F sono multimediali: F11 è Stamp, che su Niri apre lo screenshot. Ogni comando sta anche in un menu e nella ricerca dei comandi.
3. **Tasti vietati:**
   - Super (Niri, GNOME, Windows);
   - Alt+lettera (apre i menu);
   - qualsiasi Ctrl+Alt: su Windows è AltGr, e Ctrl+Alt+E scrive €;
   - i caratteri che sulla tastiera italiana si scrivono con AltGr ([ ] { } @ #);
   - Maiusc+?, Ctrl+Spazio.
4. **Lettere singole:**
   - attive in tutta la finestra tranne mentre si scrive (Qt lo fa già);
   - rimappabili, come chiede WCAG 2.1.4;
   - mostrate nei menu, nei suggerimenti e nella ricerca dei comandi.
   - Le cifre restano alle lunghezze digitate.

**Mappa proposta**

| Gruppo | Tasto | Comando | Precedente |
|---|---|---|---|
| Pannelli | Ctrl+B | Progetto sì/no | VS Code, chiesto da Daniel |
| Pannelli | Ctrl+1 | Proprietà sì/no | AutoCAD, Revit, chiesto da Daniel |
| Pannelli | Ctrl+J | Verifiche, in basso, sì/no | VS Code |
| Pannelli | Ctrl+Maiusc+M | Verifiche con il focus: le frecce scorrono le voci, le viste seguono | VS Code, Solibri |
| Pannelli | Ctrl+0 | schermo pulito, solo il disegno | AutoCAD |
| Pannelli | menu | Vista > Pannelli > Ripristina la disposizione | JetBrains, VS Code |
| Schede | Ctrl+Tab, Ctrl+PagGiù / Ctrl+PagSu | scheda successiva / precedente | Windows, AutoCAD |
| Viste | Ctrl+Maiusc+2 / Ctrl+Maiusc+3 | solo pianta / solo 3D; ripremuto torna ad affiancate | Esplora file (Ctrl+Maiusc+cifra = stile di vista); sostituisce F2, F3, F4 |
| Comandi | Ctrl+Maiusc+P | ricerca dei comandi, con gli alias di AutoCAD (ZE, ZW, ZP) | VS Code |
| Aiuto | Ctrl+? (Ctrl+Maiusc+' sulla tastiera italiana), ? nella vista, F1 | elenco delle scorciatoie con ricerca; guida | GNOME, GTK |
| Verifiche | Ctrl+. | applica «Correggi» | VS Code |
| Disegno | F3, F8, F12, F7 | agganci, orto, lunghezze vicino al cursore, griglia; anche come pulsanti nella barra di stato | AutoCAD |
| Modifica | F2 | rinomina | Windows, Qt |
| Calcolo | F5 | ricalcola subito | Windows |
| Strumenti | V B P S X M W R Q, Esc, Invio, Canc | come oggi; Esc torna a Seleziona; Invio a vuoto ripete l'ultimo strumento | AutoCAD, Aurora |
| Mouse | rotella, centrale, Maiusc+centrale, doppio clic centrale | zoom sul cursore, pan, orbita, estensione | AutoCAD, Revit |
| Mouse | destro trascinato / destro fermo | orbita / menu contestuale | Onshape, Aurora; utile sul touchpad |
| Navigazione | F, Maiusc+Z, Z | inquadra la selezione (tutto se non c'è), estensione, zoom a finestra | Blender, SketchUp |
| Navigazione | N | nord in alto in pianta, camera verso nord in 3D | ArcGIS, MapLibre |
| Navigazione | Inizio; tasti Indietro e Avanti del mouse | vista iniziale; vista precedente e successiva | ViewCube, QGIS |
| 3D | frecce, Maiusc+frecce | orbita di 15°, di 90° | Onshape, FreeCAD |
| 3D | tastierino 7, 1, 3, Ctrl+1, Ctrl+3, 5, 0 | dall'alto, da sud, da est, da nord, da ovest, prospettiva o parallela, vista dal sole | Blender, PVsyst (F6 «vista dal sole») |

**Decise da Daniel il 22/10/2026**
1. **F8 è l'orto**, come in AutoCAD. Le criticità si scorrono con Ctrl+Maiusc+M e le frecce.
2. **Ricerca dei comandi su Ctrl+Maiusc+P.**
3. **Modi di vista su Ctrl+Maiusc+2 e Ctrl+Maiusc+3.** F2, F3 e F4 si liberano.
4. **Lettere singole attive in tutta la finestra**, con l'editor per rimapparle.
5. **Mouse nel 3D come FreeCAD**, con gli stessi stili di navigazione tra cui scegliere. Oggi si orbita col sinistro (il controller standard di Qt).
   - **Risposta dello studio su FreeCAD** (`15-freecad-riferimento.md`, sezione 2.1) [V]: lo stile predefinito di FreeCAD, «CAD», non fa come AutoCAD, perché l'orbita è il centrale tenuto più il sinistro. Fa come AutoCAD lo stile «Revit» (centrale = pan, Maiusc+centrale = orbita, rotella verso il cursore), con quattro differenze:
     - il doppio clic centrale non adatta la vista;
     - il perno è al centro della finestra;
     - l'orbita è libera, non Turntable;
     - la selezione aggiunge con Ctrl.
   - **Proposta** (15, 2.6): gli stessi stili di FreeCAD, ognuno come tabella di dati, più «AutoCAD» (lo stile Revit con il doppio clic centrale per adattare la vista) e «SketchUp»; 3-4 giorni in fase 2.
   - **Il predefinito lo sceglie Daniel**: «AutoCAD» per avere le mani di AutoCAD, «CAD» per quelle di FreeCAD.

Da provare sul posto, su Windows e su Niri con la tastiera italiana: Ctrl+?, ?, Ctrl+Maiusc+2 e Ctrl+Maiusc+3. Leggendo il sorgente di Qt dovrebbero funzionare.

## 6. Le viste: navigazione, nord, criticità

Le fonti sono in `12a-convenzioni-ux.md`, sezioni 2 e 3.

### Pianta
- **Freccia del nord** piccola, in alto a destra, nello stesso angolo del cubo di vista del 3D, così l'orientamento si cerca sempre lì.
  - Se un giorno la pianta si potrà ruotare lungo l'asse dell'edificio (il «nord di progetto» di Revit), la freccia ruoterà con lei e indicherà l'angolo. Un clic, o N, rimette il nord in alto.
  - I calcoli restano sempre sul nord vero.
- **Barra di scala** in basso a sinistra, con valori tondi 1-2-5 in metri.
- **Freccia e barra come widget sovrapposti al viewport**, non disegnati in `drawForeground`: lì lascerebbero strisce durante il pan, appena la pianta smette di ridisegnarsi tutta (P2).
- **Il passaggio del mouse** evidenzia l'oggetto che il clic selezionerebbe.
- **Menu contestuale.**
- **Livelli:** ortofoto con trasparenza, moduli, stringhe, quote, nomi, ombre.
- **Il sole:** la sua direzione nell'ora scelta e, a richiesta, le ombre del giorno di progetto.
- **Azimut:** accanto a ogni valore la convenzione («da sud, + ovest», come PVsyst e PVGIS); dentro il programma resta quella di pvlib.

### 3D
- **Cubo di vista** in alto a destra:
  - facce Alto, N, E, S, O al posto di fronte e retro, perché nel fotovoltaico «da sud» è il prospetto che serve;
  - spigoli e vertici cliccabili;
  - anello della bussola e tasto Home;
  - un menu: prospettiva o parallela, «Imposta questa vista come iniziale», adatta;
  - semitrasparente quando non serve.
  - Qt Quick 3D non ne ha uno pronto: si fa in QML sopra la scena.
- **Bussola a terra** con N, E, S, O attorno al modello, come Revit e Ladybug.
- **Orbita:** perno sotto il cursore (con `View3D.pick`), visibile mentre si gira; con una selezione, perno sulla selezione. Zoom verso il cursore.
- **Passaggi tra le viste animati** in 250-300 ms, disattivabili, e a zero se il sistema chiede meno movimento.
- **Il sole:**
  - il percorso del giorno come in Revit: il sole si trascina sull'arco per cambiare ora, l'arco per cambiare data;
  - «vista dal sole» (F6 di PVsyst);
  - data predefinita il 21 dicembre;
  - un clic su un'ora nei grafici della produzione mostra le ombre di quel momento (OpenSolar).
- **Selezione** di tutti gli oggetti, sincronizzata con la pianta.

### Criticità
- **Tre livelli**, ognuno con icona e forma oltre al colore (WCAG 1.4.1):
  - errore: il risultato non vale;
  - avviso: si può procedere;
  - informazione.
- **Controllo dal vivo, che non blocca**, come Aurora:
  - moduli gialli in una fascia di rispetto e rossi se si sovrappongono, con tratteggio o icona;
  - distanza violata disegnata come una quota rossa, con il valore misurato e il minimo.
- **Segno sull'oggetto**, in pianta e in 3D, con il numero se le criticità sono più d'una.
- **Stringhe:** un colore numerato per stringa (PVsyst); i moduli fuori stringa evidenziati (HelioScope).
- **Elenco e viste legati nei due sensi.**
  - Ogni voce ha già il suo oggetto (`Item.target`).
  - Un clic nell'elenco evidenzia l'oggetto e attenua il resto (Navisworks, PVsyst). Dall'oggetto si arriva alle sue voci («Show Related Warnings» di Revit).
  - Filtri per gravità.
- **Conteggi** nella barra di stato, cliccabili; segni sull'albero del progetto, che risalgono al genitore.
- **Mappe per modulo** (ombra, irraggiamento) con il valore al passaggio del mouse e la legenda. Colori dalla scala sequenziale già validata per i grafici, non il giallo-rosso.
- **Risultati da aggiornare:** una fascia fissa, non un avviso che compare e sparisce.

## 7. Piano

**Fase 1: velocità e dati sicuri** (1-2 giorni, in quest'ordine)
1. I1: segnali bloccati sulla pagina vecchia delle proprietà.
2. I2, I3: la rotella.
3. P1: cache delle formule, grafici e genealogia disegnati quando si vedono, genealogia una volta.
4. P6: punto di massima potenza con «chandrupatla».
5. P2-A: niente ridisegno al passaggio.
6. P3: elenco delle verifiche.
7. P4: il conteggio «fuori dalle ombre» nel lavoro di posa.
8. P7: indicatore del calcolo.
9. N1: menu Vista > Pannelli con Ctrl+B, Ctrl+1, Ctrl+J, Ctrl+0 e «Ripristina la disposizione».
10. I5: clic ravvicinati in un passo.

Ogni punto con il suo test nella suite (sezione 8).

**Fase 1 fatta la sera del 22/10/2026**, con 13 test nuovi (350 in tutto, tutti verdi su Windows). Misure dopo, stesso PC e stessi progetti [V]:
- **Blocco al ritorno del calcolo:** 50-93 ms sul progetto di prova (prima 2.000-2.250), 100-246 ms su quello grande (prima 2.500-3.100).
- **Dalla modifica alla fine del calcolo:** 2,4-3,2 s sul progetto di prova, prima circa 6 s.
- **Passaggio del mouse sulla pianta con Seleziona:** nessun ridisegno; resta l'attesa del refresh dello schermo, 16,5 ms.
- **Rotella e valori scritti a metà:**
  - la rotella sopra un campo non lo cambia più e non lascia passi di annullamento;
  - un valore scritto a metà non entra più nel progetto;
  - il pannello si ricostruisce 2 volte invece di 4.
- **Pannelli:** Proprietà si trova in Vista > Pannelli, con Ctrl+1.

Restano per la fase 2:
- P5, gli aggiornamenti senza ricostruire, che tolgono anche la perdita del testo che si sta scrivendo;
- la prima apertura di Consumi e Bilancio, 130-180 ms;
- all'avvio circa 1 s, la prima accensione della vista 3D.
- Non è ancora fatto il punto di N1 sul pannello Verifiche (Ctrl+J), che nasce con il pannello in fase 2.

**Fase 2: chiarezza e navigazione** (circa una settimana)
- P5 e I4: aggiornamenti senza ricostruire.
- P2-B: strato statico della pianta.
- N2: ispettore che cambia con la scheda.
- N3-N6: albero, menu contestuali, barra con icone, mappa delle scorciatoie della sezione 5 con il loro elenco.
- V1-V3, V9: nord, scala, evidenza al passaggio, zoom.
- T1-T3: cubo di vista, viste standard, selezione e zoom in 3D.
- C1, C3, C4: criticità nelle viste.
- Il tema scelto dallo studio estetico (13), con il colore a scelta (13, sezione 12).
- Da FreeCAD (studio 15, sezione 7):
  - gli stili di navigazione come tabelle di dati, più «AutoCAD»; clic centrale che ricentra, perno sotto il cursore con l'indicatore, orbita Turntable; cubo con la struttura del NaviCube;
  - campi con unità e aritmetica («2 m + 30 cm»), per I1-I4;
  - coordinate dell'oggetto sotto il cursore nella barra di stato e misura rapida della selezione, per V3 e T4;
  - editor delle scorciatoie con i conflitti in diretta, per N6;
  - per P5, il ricalcolo dei soli oggetti toccati, con i segni «da ricalcolare» ed «errore».

**Fase 3**
- Ricerca dei comandi e pannello «Problemi» agganciabile.
- Livelli (V4), ombre e sole in pianta (V6, T5), colori per modulo (C2).
- Quote che restano (V5), modifica dei lati in sovrimpressione (V8).
- Sezioni comprimibili (K1, K2).
- L'assistente (studio 14): un personaggio che fluttua, uno solo per la finestra (14, sezione 7.3).
- Da FreeCAD (studio 15):
  - esportazione IFC4, poi lettura degli IFC dell'architetto (5.5);
  - pannello delle attività con OK e Annulla legati all'istantanea, piano di lavoro sulla falda, «chiarisci selezione»;
  - le segnalazioni a FreeCAD dei cinque problemi trovati, se Daniel vuole.

## 8. Come si verifica

**Criteri, sullo stesso PC e con gli stessi due progetti:**
- nessun blocco oltre 100 ms dopo una modifica, compreso il ritorno del calcolo;
- passaggio del mouse sulla pianta entro il refresh dello schermo anche con 4.682 moduli;
- prima apertura di una scheda entro 100 ms;
- risultati dell'energia entro 1,5 s dalla modifica sul progetto di prova.

**Test automatici nuovi** in tests/test_window.py, perché le regressioni si vedano nel CI:
- la rotella sopra un campo senza focus non cambia il valore;
- un valore scritto a metà non entra nel progetto quando il pannello si aggiorna;
- un pannello chiuso si riapre da Vista > Pannelli e con la sua scorciatoia;
- il ritorno del calcolo non disegna i grafici nascosti (si contano i disegni).

**Le misure** si rifanno con lo stesso script della revisione (`meridiana-prove\ux-2026-10-22\probe.py`), da portare in tools/ con la fase 1.

## 9. In parallelo

- Lo studio estetico è in `13-studio-estetico.md`, con la tela degli artefatti. Copre:
  - lo stile minimal alla DIALux evo;
  - i temi chiaro e scuro;
  - i richiami a GNOME, Niri e Lucciola;
  - la verifica in Qt.
  Raccomanda la direzione «Meridiana».
- Lo studio dell'assistente in chat (fornitori cloud e locali, modello locale sul laptop, addestramento) è in 14-assistente-agente.md.
- FreeCAD come riferimento e come programma gemello (navigazione, modellazione, compatibilità con prove IFC e .FCStd) è in 15-freecad-riferimento.md.

## Appendice: le misure [V]

Windows, schermo secondario 1080×1920 a 60 Hz, finestra 1900×999, Direct3D 11. In millisecondi.

| Misura | Progetto di prova (188) | Progetto grande (4.682) | Con le tre correzioni provate* |
|---|---|---|---|
| Blocco al ritorno del calcolo | 2.030-2.250 (+750-980) | 2.520-3.100 (+700-940) | 57-97 (prova), 221-241 (grande) |
| Di cui formule della genealogia | 1.530-1.740 (177 immagini) | 2.040-2.610 (244 immagini) | quasi zero dopo la prima volta |
| Di cui grafici matplotlib | 1.510-1.750 | 1.730-2.040 | solo quelli visibili |
| Passaggio del mouse sulla pianta, mediana | 14-17 | 60-69 (p95 93) | 16,5 (attesa del refresh, nessun ridisegno) |
| Apertura: blocchi | 1.100-1.470 | 1.140-1.590 | (correzione P3 non nello script; micro-prova 969 → 7-9) |
| Prima apertura Consumi / Bilancio | 78-94 / 130-177 | 79-117 / 115-122 | invariata |
| Cambio di scheda successivo | 15-40 | 15-65 | 15-65 |
| Modifica nella scheda Modello, fino alla fine | 51-64 | 358-531 | |
| Calcolo dell'energia (in background) | 2.600-3.900 | 2.500-5.300 | punto di massima potenza: da 1.805 a 26 per chiamata, due chiamate per calcolo |
| Disegno 3D / orbita | 0,2-0,3 per immagine, 55 fps | 0,4-1,0 per immagine, 45-55 fps | |

\* Cache delle formule, grafici e genealogia disegnati solo quando visibili, niente ridisegno della pianta al passaggio con Seleziona.

**Linux** (laptop, Niri, OpenGL):
- La rotella, il valore scritto a metà e il pannello che non si riapre si comportano come su Windows.
- Mostrare la vista 3D dopo averla nascosta costa 113-117 ms.
- Il calcolo dell'energia non si è potuto misurare (h5py).
