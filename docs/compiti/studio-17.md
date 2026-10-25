# Compito per una sessione cloud: lo studio 17, l'interfaccia

23/10/2026. Uno studio con i bozzetti, non codice del programma. Daniel ha usato la versione con la fase 2 e chiede un'interfaccia più chiara e più bella. Le scelte le fa lui guardando i bozzetti; poi si scrivono i compiti.

## Come lavorare

Come lo studio 16 (`docs/compiti/studio-16.md`, «Come lavorare»):
- ramo `studio-17` da `lavoro`, richiesta di unione in bozza;
- un commit per tema, spinto subito;
- tutte le alternative con pro, contro, fatica e voti, le prove dove decidono, la raccomandazione;
- le fonti con URL e data;
- `docs/richieste.md` aggiornato (i numeri R sono di quel file).

**I bozzetti**
- Sono pagine HTML che si aprono da sole nel browser, in `docs/studio/17-prove/`: niente librerie esterne né rete, colori come variabili CSS, tema chiaro e scuro.
- Per ogni tema almeno tre direzioni diverse, una accanto all'altra nella stessa pagina, disegnate sul layout vero di Meridiana: barra dei menu, schede, barra degli strumenti, pannelli Progetto e Proprietà, pianta e 3D affiancate, pannello Verifiche, barra di stato.
- La direzione estetica scelta da Daniel è «Meridiana» (studio 13, sezione 7: Titillium Web, bronzo come colore di partenza, fondi calce e notte). I colori vengono da `theme_colors.py` e dalla tabella dello studio 13, sezione 12.
- Dove serve, un bozzetto si prova anche in Qt con una piccola finestra offscreen e la sua schermata (`QWidget.grab()`), per controllare che quello che si propone si possa fare con Fusion e un foglio di stile, e quanto costa.

Il risultato è `docs/studio/17-interfaccia.md`, con l'indice dei bozzetti e, alla fine, le domande per Daniel e le bozze dei compiti in `docs/compiti/17*.md`.

## I temi

### A. Distinguere le parti dell'interfaccia (R18)
Daniel: «sarebbe da migliorare la distinzione tra le varie sezioni dell'interfaccia. Non c'è grande distinzione tra menu e sottomenu (strumenti, proprietà, barre laterali, verifiche)».

Da studiare:
- livelli di superficie (finestra, barre, pannelli, viste) con fondi diversi;
- intestazioni dei pannelli;
- separatori;
- come lo fanno DIALux evo, GNOME (libadwaita), Revit, VS Code, Blender.
- l'albero del progetto (R30): Daniel non ama come è presentato, «senza spaziatura tra le sezioni, il tutto poco chiaro»; proposte per sezioni, spaziature, intestazioni, icone e segni delle verifiche (il segno piccolo e il suggerimento sono già in `fase-2-ritocchi.md`, passo 10).

### B. Dove stanno gli strumenti (R19, seconda parte)
Daniel: «mi chiedo se inoltre non debbano stare loro sotto il menù con scritto "modello, producibilità, consumi, ecc." essendo che loro sono controlli della modellazione».

Da studiare:
- la barra degli strumenti sotto le schede e legata alla scheda Modello;
- la barra laterale a icone;
- la barra dentro la vista;
- le fasi alla DIALux.

I comandi delle viste sono già decisi: vanno dentro le viste (`docs/compiti/fase-2-ritocchi.md`, passo 2).

### C. Pulsanti, campi e gruppi (R22)
Daniel: «il design di tasti e bottoni non è il massimo. Vorrei proposte per cambiarlo. Le caselle di input non si distinguono bene dallo sfondo (almeno in modalità scura) e sarebbe buono dare alle varie sottosezioni un contorno più evidente (mi riferisco tipo a "distanze e margini, ecc..."). Anche i contorni all'interno dei risultati di "consumi", "bilancio ed economia", "producibilità", non si leggono. In tutti i casi citati sopra, non è possibile usare un approccio alla gnome nel quale sottosezioni e tasti non solo hanno contorno ma riempimento come il contorno?».

Da studiare:
- pulsanti: pieni, tonali, a contorno, piatti, e quando usare ognuno;
- campi con fondo proprio e bordo in tutti e due i temi;
- gruppi come schede piene alla libadwaita («boxed lists», «preferences groups»);
- i riquadri dei risultati;
- i contrasti misurati (WCAG 1.4.11 per i bordi dei controlli, 3:1).

### D. Grafici interattivi (R23)
Daniel: «i grafici non sono dinamici, non visualizzano nulla al passaggio del mouse, non è possibile controllarli. Negli sketch negli artefatti era possibile far più cose e il tutto era più carino. come mai qua non è così?».

Rispondere alla domanda: oggi i grafici sono immagini di matplotlib, mentre la tela usava HTML e SVG.

Da studiare:
- matplotlib con gli eventi del mouse (valore al passaggio, zoom, scelta delle serie);
- pyqtgraph;
- Qt Graphs (2D, nella stessa Qt 6.12);
- una vista web con una libreria JavaScript;
- per ognuno: licenza, peso, velocità misurata su un anno di valori orari, resa, esportazione nella relazione PDF, lavoro per portare i grafici di oggi (`ui/charts.py`, `energy_pages.py`).

Un prototipo del grafico mensile e di quello orario con la strada raccomandata.

### E. Aiuti accanto alle cose (R24)
Daniel: «non ci sono helper di fianco ai risultati o nelle varie sezioni che li spiegano, che spiegano come utilizzare i comandi, cosa vogliano dire determinate cose».

Da studiare:
- il «?» accanto ai titoli con un riquadro breve;
- i suggerimenti estesi;
- le frasi d'aiuto sotto i campi;
- la barra di stato che spiega lo strumento (c'è già);
- un pannello d'aiuto;
- il collegamento al manuale e al «Come è calcolato» che esiste già.

Il contenuto: chi lo scrive, dove sta (un file di testi tradotti), come resta aggiornato. Esempi scritti per le sezioni principali: Proprietà del sottocampo, Producibilità, Bilancio, Verifiche.

### F. Il pannello Verifiche (R13)
Daniel: «è di sicuro da migliorarne il modo in cui vengono esposti tutti gli elementi perché siano più comprensibili».

Da studiare:
- raggruppamenti per oggetto, per livello o per area;
- frasi brevi con il dettaglio a richiesta;
- il pulsante Correggi;
- il legame con le viste;
- come lo fanno PVsyst, Revit (avvisi), VS Code (pannello Problemi), Aurora.

I difetti dei filtri sono in `fase-2-ritocchi.md`, passo 9.

### G. Meridio e la sua chat (R15)
Daniel: «sarà da migliorarne l'estetica, renderlo magari dinamico, e migliorare anche l'estetica della chat con qualche animazione in apertura / chiusura, mentre sta parlando l'assistenza, possibilità di ridimensionare la chat, vista delle risposte consigliate più chiara con elenco».

Da studiare:
- il personaggio animato: respiro lento, sguardo, «pensa»;
- le animazioni di apertura e chiusura;
- l'indicatore mentre risponde;
- il ridimensionamento;
- le domande pronte come elenco;
- il costo in Qt, con l'opzione «meno movimento» sempre rispettata.

Il disegno di partenza è in `src/meridiana/assistant.py`.
