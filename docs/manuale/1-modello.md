# 1. Modello

Il Modello è il disegno: il sito, gli edifici con le coperture, i sottocampi dove vanno i moduli, le esclusioni. Si disegna in pianta con gli strumenti della barra della fase e si controlla nella vista 3D. Le proprietà dell'oggetto selezionato stanno nel pannello di destra; il riquadro d'aiuto in fondo spiega il campo in cui sei.

Gli strumenti hanno una lettera (predefinita, si cambia in File > Impostazioni > Tastiera): Seleziona V, Edificio B, Falda P, Sottocampo S, Esclusione X, Fila L, Sposta M (con Ruota dentro), Misura D, Rettangolo per tre clic R, Squadra gli angoli Q; F3 gli agganci e F8 l'orto, come in AutoCAD. Le lettere non agiscono mentre scrivi in un campo.

## Il sito

Il sito è l'origine del disegno, con latitudine e longitudine. Il sole, il meteo da PVGIS e le regole della regione partono da lì. «Trova il sito…» cerca un indirizzo (OpenStreetMap, servizio Nominatim) o accetta le coordinate. Il sito si sposta solo prima di disegnare: il disegno si misura da esso. La regione si legge dall'indirizzo trovato: oggi solo la Lombardia ha regole proprie, altrove valgono quelle nazionali.

### Passo delle file dal sole

Il giorno e le ore si scelgono nel sottocampo, sotto «Passo delle file», quando il passo è «Dal sole». In quel giorno, tra quelle ore, nessuna fila fa ombra alla successiva: da qui viene il passo dei sottocampi a file inclinate, e da qui vengono le ombre che «Fuori dalle ombre degli ostacoli» evita. Le norme lasciano la scelta al progettista: la CEI 82-25/3, 6.2 dà solo l'angolo limite (riferimento citato in `checks.py`).

#### Giorno e ore del sottocampo

Il predefinito del progetto è il 21 dicembre, dalle 10 alle 14 in tempo solare vero, controllato ogni 10 minuti (valori predefiniti di Meridiana, `sun.py`, `DesignWindow`). Finché il sottocampo usa «Predefinito del progetto», segue questi valori; cambiando giorno o ore si crea la sua finestra propria. «Usa per tutti i sottocampi» copia la finestra mostrata nel predefinito del progetto e toglie le finestre proprie degli altri sottocampi, in un solo passo di Annulla. Il 21 dicembre ha il sole più basso dell'anno: le ombre sono le più lunghe e il passo il più largo. Un giorno più vicino all'equinozio dà un passo più corto e più moduli, con un po' d'ombra tra le file d'inverno al mattino e alla sera; la perdita si legge in Producibilità, tra le perdite (ombre tra le file).

### Connessione e obblighi

Ciò che le regole chiedono oltre al disegno. Le regole che ne seguono stanno nelle [Verifiche](verifiche.md) e nelle note per la relazione.

- **Connessione.** «Automatica dalla potenza» sceglie la bassa tensione fino a 100 kW, la media fino a 10 MW e l'alta oltre (CEI 0-16:2026-07, 6.3, Tab. 4, p. 43, citata in `rules.py`: tra 6 e 10 MW media o alta). Decide il distributore: se il preventivo di connessione dice altro, sceglilo qui.
- **Potenza minima da rinnovabili.** Per un edificio nuovo o con una ristrutturazione rilevante, l'obbligo P = k × S del D.Lgs. 199/2021 (art. 26 e allegato III; regola N24), con S l'impronta a terra degli edifici; edificio pubblico +10 %. In Lombardia k cresce per i titoli richiesti dal 01/01/2027 (regola N25). Il valore di P e il confronto con l'impianto sono nelle Verifiche.
- **Potenza impegnata, superficie dell'unità, unità immobiliare, maggior rischio.** Decidono chi può progettare secondo il DM 37/2008, art. 5 comma 2 (p. 4; regole N02 e N03): serve un professionista iscritto all'albo sopra 6 kW di potenza impegnata, sopra 200 m² per produzione, commercio e servizi, sopra 400 m² per un'abitazione, sempre per i condomini, per le forniture sopra 1000 V e per gli ambienti a maggior rischio di incendio, a uso medico o con pericolo di esplosione. Negli altri casi può progettare il responsabile tecnico dell'installatore (art. 5 comma 1). Senza questi dati Meridiana considera dovuto il professionista, e lo dice.

## Gli edifici

L'edificio si disegna come impronta (strumento Edificio, Rettangolo per tre clic, o Disegna > «Edificio da modello…»). L'altezza di gronda e la copertura (piana, a una falda, a due falde, a padiglione, falde disegnate a mano) danno le falde su cui stanno i sottocampi e le ombre che l'edificio fa sugli altri. Sulla copertura a una falda si sceglie il lato di gronda, anche con «Scegli in pianta» e un clic sul lato. Sulla copertura piana il parapetto, alto quanto scritto lungo tutto il contorno, fa ombra ai moduli vicini.

### Tetto

Il gruppo Tetto delle Proprietà dell'edificio. I tetti a due falde e a padiglione seguono qualsiasi impronta (L, T, U, trapezio...): ogni lato di gronda ha la sua falda, tutte con la stessa pendenza, e colmi, displuvi e compluvi vengono da soli (lo scheletro dritto, studio 16, tema A). Per ogni lato si sceglie «Gronda» o «Testata»: la testata è un lato con il muro che sale fino al tetto, il timpano. Un tetto a due falde nuovo ha le testate alle estremità dei bracci; un padiglione non ne ha. «Scegli in pianta» e un clic su un lato lo cambia da gronda a testata e viceversa. Un lato accanto a un angolo rientrante che non può fare da testata resta gronda, e il gruppo lo dice.

La copertura propone la pendenza: tegole marsigliesi 35 %, coppi 30 % (pendenza minima, manuale ANDIL *Coperture in laterizio* 2025, p. 7), lamiera o pannelli 7 % (schede dei produttori, studio 16 A.8). La pendenza resta modificabile in gradi e in percento. La «Quota del colmo», se scritta, decide la pendenza: il punto più alto del tetto sta a quella quota, e la pendenza si ricalcola e si mostra; scrivere di nuovo la pendenza la fa tornare a decidere.

Passando con il mouse sull'edificio, in pianta si accendono i colmi. I file salvati prima del formato 9 con un tetto a falde su un'impronta non rettangolare si aprono con un avviso: il tetto ora segue l'impronta, i sottocampi sono messi sulla falda che sta sotto il loro centro, e vanno controllati.

### Edificio da modello

Disegna > «Edificio da modello…» (o il pulsante Modello nella barra della fase): rettangolo, L, T, U o trapezio con le sue quote e una rotazione, con il disegno del contorno; «Mettilo in pianta» e un clic dove va l'angolo a sud-ovest. Dopo, i lati si cambiano uno per uno nel gruppo Lati.

### Dal modello dell'architetto (IFC)

File > «Importa un modello IFC…» (o la pagina File, Importa): un file .ifc o .ifczip, IFC2X3 o IFC4. Meridiana legge solo ciò che serve al fotovoltaico: le coperture e ciò che sta sopra (camini, lucernari, impianti, parapetti, alberi), il sito e il nord; di un edificio senza copertura i solai, o le pareti. La lettura va in un processo a parte: la barra in basso dice a che punto è, «Annulla» la ferma, e si ferma da sola oltre tre minuti o oltre metà della memoria del PC. Se succede, fai esportare all'architetto solo l'edificio, senza arredi e impianti.

Poi un riquadro dice dove vanno gli edifici: dove li mette il file, intorno al sito del progetto; il sito spostato sul modello (proposto quando il progetto è vuoto o il modello è lontano); oppure nell'origine del sito, l'unica scelta se il file non è georiferito. Se la conversione di mappa e il TrueNorth del file non dicono lo stesso nord, scegli tu. Sotto, gli edifici visti dall'alto e che cosa è preso, approssimato e lasciato fuori. Gli edifici entrano con il tetto riconosciuto: piano, a una falda, a due falde o a padiglione con le testate, altrimenti a falde libere; le esclusioni con la loro altezza, il parapetto sui tetti piani. È una sola modifica: Ctrl+Z la toglie. Le altezze partono dal piano a quota zero dell'edificio: controlla l'altezza di gronda se il modello ha i piani interrati o le quote assolute.

File > «Esporta il modello in IFC4…» fa il contrario: il progetto come modello georiferito, con ogni modulo posato e la sua stringa, per l'architetto o il coordinatore BIM.

### Lati

Ogni lato del contorno con la sua lunghezza, per edifici, sottocampi ed esclusioni. Una lunghezza nuova sposta l'estremo del lato e ciò che segue, come lo stiramento dei programmi CAD; un doppio clic sulla quota di un lato in pianta fa lo stesso.

### Spostare e ruotare

Sposta (M) prende l'oggetto selezionato, o quello che clicchi: un punto base e poi il punto dove va, con gli agganci (F3); oppure scrivi lo spostamento e Invio: «3» sono 3 m verso il puntatore, «3;2» 3 m a Est e 2 a Nord, Tab passa alla direzione dal Nord. Dentro Sposta, R ruota attorno al centro (o al punto base già cliccato) a passi di 15°, 5° con Ctrl, 90° con Maiusc, o dell'angolo scritto; fuori da Sposta R resta il rettangolo. Ctrl tenuto al clic, o C, fa una copia. Le frecce spostano di 10 cm, 1 m con Maiusc, 1 cm con Ctrl. Al centro dell'oggetto c'è una maniglia che sposta trascinando, sul lato più a nord una che ruota; Esc esce.

Un edificio porta con sé i suoi sottocampi, le esclusioni e le falde libere; un sottocampo resta sulla sua falda e, ruotato, ruota l'orientamento delle file se è scritto. Nella vista 3D, con Sposta attivo, l'oggetto ha le frecce Est e Nord, il quadratino del piano e l'anello per ruotare; una cifra scritta apre il campo dei valori accanto.

### Prevenzione incendi

Per un'attività soggetta al controllo dei Vigili del Fuoco valgono le linee guida DCPREV 14030/2025 (regole N13 e N15 di `rules.py`). Per i moduli sopra la copertura (BAPV) Meridiana applica da sola, nella posa, i punti del paragrafo 3.3.5.1 (p. 13-16):

- una fascia libera di almeno 1 m dal bordo della copertura;
- gruppi di moduli non più grandi di 20 m in ogni direzione, separati da corridoi di almeno 2 m;
- almeno 1 m in più intorno a evacuatori di fumo, altre aperture e impianti sulla copertura.

I tre valori sono quelli della posa (`layout.py`, `fire_edge`, `fire_group`, `fire_corridor`). La linea guida chiede anche 1 m dalle pareti di compartimento sottostanti, salvo sulle coperture resistenti al fuoco (punto 5): la casella «Solaio di copertura resistente al fuoco» lo registra, ma la posa oggi non disegna quelle pareti. Il resto della linea guida (sezionamento d'emergenza, cartelli, registro dei controlli) va nella relazione: le note sono nelle Verifiche, pronte da copiare.

## Il sottocampo

Il sottocampo è l'area disegnata per i moduli, su una falda o a terra. Meridiana posa i moduli al suo interno con il montaggio, le distanze e le regole di prevenzione incendi dell'edificio su cui sta. «Posa i moduli» avvia la posa; sotto i pulsanti compaiono i moduli posati con la potenza Po,cc, l'azimut e l'inclinazione, per le file inclinate il passo, la distanza libera e l'angolo limite, e i gruppi di prevenzione incendi. «Togli i moduli» li toglie e lascia il contorno.

### Le file a mano

La posa automatica è la proposta; le file si correggono a mano (studio 16, tema C). Lo strumento Fila (L) disegna una fila in un sottocampo: un clic dove comincia il suo bordo davanti, uno dove finisce, oppure la lunghezza scritta e Invio; prende il modulo, gli spazi, le tavole e l'orientamento del sottocampo, e mentre la disegni la vedi rossa se esce dalla fascia dal bordo o copre un'esclusione (resta comunque: decidi tu). In un sottocampo vuoto la fila disegnata è la posa.

Un clic su un modulo lo seleziona, un secondo clic sulla stessa fila seleziona la fila. La fila selezionata si toglie con Canc, si sposta con Sposta (anche con il gizmo nel 3D) dentro il suo sottocampo, si accorcia o si allunga trascinando il quadrato al suo estremo. Il menu del tasto destro aggiunge una fila in coda, un passo dietro l'ultima, ed esplode una fila (o tutte quelle del sottocampo) nei suoi moduli: ognuno diventa una fila di un posto, si sposta da solo e gira di 90° con il doppio clic, come in Aurora. I moduli tengono il loro nome («fila:posto»), così le stringhe a mano e i moduli tolti restano su di loro.

Il primo gesto rende il sottocampo «a mano»: le sue file restano come sono, e un passo o dei margini nuovi non le spostano. Le regole che la posa automatica rispetta diventano verifiche: gruppi oltre i 20 m e corridoi sotto i 2 m con le regole dei Vigili del Fuoco, moduli sulle esclusioni o oltre la fascia dal bordo, moduli in ombra nel giorno di progetto. «Riposa in automatico» (pulsante del sottocampo, gruppo Posa, menu, Verifiche) chiede prima e si annulla: come avverte PVsyst, le modifiche a mano si perdono. Un modulo nuovo con le misure entro 2 cm da quello di prima adatta le file da solo; altrimenti Meridiana chiede se adattarle o riposare.

### Montaggio

Come i moduli stanno sulla superficie: complanari alla falda, integrati nella copertura (BIPV), su file inclinate ancorate o zavorrate, a coppie est-ovest, su file a terra, su una pensilina o un carport. Il montaggio decide l'inclinazione e se il passo tra le file lo dà il sole. Complanare, integrato e pensilina sono montaggi «a filo» (`layout.py`, `FLUSH`): le file non si fanno ombra e la distanza tra le file è un valore. Con le file zavorrate su un solaio le Verifiche ricordano che la zavorra da sola non trattiene i moduli (NTC 2018 7.2.4; CEI 82-25/3 6.2, in `checks.py`).

### Moduli per tavola, in altezza

Quanti moduli stanno uno sopra l'altro in una tavola, di traverso alla fila: con i moduli in verticale, 2 è la «2V» dei montaggi a terra. Più moduli in altezza fanno una fila più alta, quindi un passo più lungo dal sole. «Moduli per tavola, in lunghezza» divide invece la fila in tavole (0: file continue), con la distanza «Tra le tavole».

### Distanze e margini

Le distanze tra i moduli, dal bordo dell'area, tra le file e tra le tavole. I predefiniti sono 2 cm tra i moduli (i morsetti), 0,5 m dal bordo, 2 cm tra le file a filo e 0,3 m tra le tavole (valori predefiniti di Meridiana, `layout.py`, `Params`). Se l'edificio è soggetto al controllo dei Vigili del Fuoco, Meridiana tiene da sola almeno 1 m dal bordo e aggiunge i corridoi tra i gruppi (vedi [Prevenzione incendi](#prevenzione-incendi)).

#### Dal bordo dell'area

Una fascia libera lungo il contorno dell'area, dove i moduli non vanno: per la manutenzione e per le regole dei Vigili del Fuoco. Con l'attività soggetta vale almeno 1 m (DCPREV 14030/2025, 3.3.5.1, regola N15): Meridiana usa il maggiore tra il valore scritto e 1 m.

#### Tra le file

Sulla falda i moduli sono complanari e le file non si fanno ombra: la distanza è un valore, per i morsetti e per passare. Sulle file inclinate e a terra il passo lo dà invece il sole: vedi [Passo delle file](#passo-delle-file).

### Passo delle file

Per le file inclinate e a terra:

- **Dal sole**: il passo più corto per cui nessuna fila fa ombra alla successiva nel giorno scelto, tra le ore del sottocampo (vedi [Giorno e ore del sottocampo](#giorno-e-ore-del-sottocampo)). È il predefinito (`layout.py`, `pitch_mode`).
- **Passo assegnato**: una distanza scelta da te, da fila a fila.
- **Rapporto di copertura (GCR)**: la profondità dei moduli di traverso alla fila divisa per il passo; 0,5 per impostazione (`layout.py`, `gcr`).

La CEI 82-25/3, 6.2 dà l'angolo limite, non il giorno: la scelta del giorno e delle ore resta al progettista.

### Fuori dalle ombre degli ostacoli

Nessun modulo dove parapetti, impianti, camini, alberi e gli altri edifici fanno ombra nel giorno di progetto, tra le ore del sito: la stessa regola del passo tra le file. Quando gli ostacoli tolgono più del 3 % dell'irraggiamento di un campo (soglia di Meridiana, `checks.py`, `OBSTACLE_SHADE`), le Verifiche propongono di attivarlo e dicono quanti moduli costa.

## Le esclusioni

Un'esclusione tiene fuori i moduli dal suo contorno e dalla sua distanza aggiuntiva: lucernari, evacuatori di fumo (EFC), aperture, impianti, camini, alberi, passerelle. Con un'altezza è anche un ostacolo che fa ombra; l'altezza predefinita di ogni tipo è indicativa e va misurata sul posto. Evacuatori, aperture e impianti sulla copertura prendono da soli 1 m in più dove valgono le regole dei Vigili del Fuoco (DCPREV 14030/2025, 3.3.5.1, regola N15).
