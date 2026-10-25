# Compito per una sessione cloud: la fase 2 della revisione

22/10/2026. Un lavoro di più ore, da fare in autonomia, passo dopo passo, su tutto quello che gli studi 12, 12a, 13, 14 e 15 hanno deciso o proposto. Daniel lo rivede alla fine.

## Come lavorare

**Prima di cominciare**
- `git config user.name "Daniel Grasso"` e `git config user.email code@danielgrasso.com` nel clone.
- Leggi `CLAUDE.md`, poi gli studi nelle sezioni che ogni passo indica. Le decisioni prese lì non si riaprono.

**Ramo e richiesta di unione**
- Un ramo solo, `fase-2`, partito da `lavoro`.
- Dopo il primo commit apri una richiesta di unione **in bozza** verso `lavoro`. Nella descrizione metti i passi di questo file come caselle e spuntali man mano. Aggiungi due sezioni: «Da decidere per Daniel» e «Da provare sul PC di Daniel».
- Alla fine togli la bozza. Mai `main`, mai riscrivere la storia.

**Ogni commit**
- È piccolo e sta in piedi da solo.
- Ha lint e suite completa verdi, con la finestra offscreen, e i test nuovi per quello che fa.
- Va spinto subito dopo: la macchina può essere ripresa e il lavoro non spinto si perde.
- Messaggio in inglese, come gli altri del repository.

**Regole**
- Prima la logica nel nucleo senza Qt, con i test; poi la finestra, che mostra e raccoglie i gesti.
- Niente dipendenze Python nuove. Dati nuovi (icone, font) solo con la loro licenza, in `data/`.
- Non toccare versione, CHANGELOG e metainfo: le release le decide Daniel.
- Il formato del file `.meridiana` resta com'è. Se un passo lo richiede davvero: versione nuova, migrazione e test.
- Impostazioni nuove in `config.py`: campi con il loro valore predefinito, `CONFIG_VERSION + 1` con la migrazione e il suo test.
- Testi nuovi con `_()`, tradotti in `po/it.po` (`tools/compile_po.py --update`, poi `msgfmt --check po/it.po`).
- Il diario: per ogni passo una riga nell'appendice A di `docs/progetto.md`, con [V] e come l'hai verificato; `docs/funzionalita.md` se cambia quello che il programma fa.

**Quando qualcosa non torna**
- Manca una decisione: prendi quella raccomandata dagli studi, scrivila in «Da decidere per Daniel» e vai avanti. Non fermarti a chiedere.
- Un passo è molto più grande del previsto: fai la parte che sta in piedi da sola, annota il resto nella richiesta di unione e passa al successivo.
- Quello che offscreen non si può vedere (resa grafica, sensazione del mouse, prestazioni vere) va in «Da provare sul PC di Daniel».
- Se la conversazione viene riassunta, rileggi `CLAUDE.md`, questo file e la descrizione della richiesta di unione prima di continuare.

**Alla fine**, un riassunto in italiano per Daniel:
- che cosa è fatto, commit per commit;
- che cosa è verificato e come;
- che cosa resta da provare con la finestra vera;
- le decisioni aperte;
- i passi non fatti, con il perché.

## I passi, in quest'ordine

### 1. Proprietà aggiornate senza ricostruire
Studio 12: P5 e I4 (sezioni 3.1, 3.2 e 7). Studio 15, sezione 3.6.
- Oggi `ui/properties.py` (`Properties`, `show_site`, `show_building`, `show_subfield`, `show_exclusion`) ricostruisce la pagina a ogni aggiornamento: costa, e fa perdere il testo che si sta scrivendo.
- Se l'oggetto mostrato è lo stesso e cambiano solo dei valori, aggiorna i campi che ci sono, a segnali bloccati e senza togliere il fuoco a quello in modifica. Ricostruisci solo quando cambia l'oggetto o la struttura della pagina.
- Test:
  - il testo scritto a metà resta mentre arriva un risultato del calcolo;
  - si contano le ricostruzioni;
  - nessun passo di annullamento in più.
- Commit a parte, se sta in piedi: come in FreeCAD, i risultati che dipendono da una modifica hanno i segni «da ricalcolare» ed «errore», e si ricalcola solo quello che è cambiato.

### 2. Campi con unità e calcoli
Studio 15, sezione 3.2; studio 12, I1-I4.
- Modulo del nucleo `quantity.py`, con i test sui casi buoni e su quelli sbagliati. Legge:
  - espressioni come «2 m + 30 cm», «1,5», «17°», «150 mm», «2*1,134», con la virgola decimale e anche il punto;
  - le unità ammesse per tipo di campo: lunghezze mm, cm, m, km; angoli °, deg, rad; potenze W, kW, kWp; percentuali;
  - gli errori, con un messaggio chiaro.
- Mai `eval` di Python.
- Un widget per i campi numerici di Proprietà (lunghezze, angoli):
  - si scrive l'espressione e Invio la calcola;
  - il valore resta scritto all'italiana;
  - la rotella si comporta come in `ui/wheel.py`.
- Test del widget.

### 3. Scorciatoie
Studio 12, sezione 5 e decisioni del 22/10; studio 12a, sezione 1; studio 15, sezione 3.9.
- Un registro centrale delle azioni: id, testo, scorciatoia predefinita. Le scorciatoie scelte dall'utente stanno in `config.py`. Oggi le azioni nascono in `ui/window.py` con `act(...)`.
- La mappa della sezione 5 dello studio 12:
  - F8 orto;
  - F3 agganci sì/no;
  - Ctrl+J il pannello Verifiche agganciabile, che nasce qui (il punto di N1 rimasto aperto);
  - lettere singole in tutta la finestra, quando il fuoco non è in un campo di testo;
  - Ctrl+Maiusc+2/3 ci sono già.
- «Scorciatoie da tastiera»:
  - Ctrl+? apre l'elenco con la ricerca;
  - l'editor mostra i conflitti mentre si digita;
  - i conflitti si calcolano nel nucleo, con i test.
- Niente Ctrl+Alt, che è AltGr sulle tastiere italiane. Nessun comando solo su un tasto F (12a).

### 4. Il tema con il colore a scelta
Studio 13, sezioni 3, 7, 8, 9 e 12. Il calcolo dei colori c'è già: `src/meridiana/theme_colors.py`.
- `ui/theme.py`:
  - stile Fusion anche su Windows;
  - una palette completa da `theme_colors.derive`: tutti i ruoli, gruppi Active, Inactive e Disabled, `Accent` compreso;
  - un foglio di stile globale piccolo e senza font;
  - Sistema, Chiaro e Scuro, che seguono `colorSchemeChanged` anche su Niri con il tema del portale (sezione 8).
- Preferenze › Aspetto:
  - il tema;
  - il colore: i nove pronti, «Sistema», «Un altro colore» con `QColorDialog`;
  - i fondi: Meridiana, Dal colore, Grigi;
  - un'anteprima con selezione, pulsante e avviso, il contrasto, e una nota se il colore è stato ritoccato.
- Il colore del sistema:
  - su Windows è l'`Highlight` della palette della piattaforma, letto prima di mettere la nostra;
  - su Linux viene dal portale: `org.freedesktop.appearance`, chiave `accent-color`, letto con QtDBus, ascoltando `SettingChanged`;
  - se manca si usa il bronzo;
  - la lettura della risposta del portale è una funzione con i suoi test.
- Quando si cambia colore: l'anteprima cambia subito, la finestra intera al rilascio o dopo 250 ms, perché il foglio di stile costa 0,4-0,9 s.
- Pianta, 3D e grafici prendono i colori dal tema:
  - nel 3D in binding dal `Backend`, mai impostati da Python;
  - la selezione con un alone a due toni, diversa dall'avviso (C6).
- Font Titillium Web (OFL) in `data/fonts`, con la licenza, caricato all'avvio, se lo puoi scaricare da github.com/google/fonts. Se non puoi, annotalo.
- Test:
  - ogni ruolo della palette è impostato;
  - i contrasti tengono;
  - lo stile windows11 non torna;
  - un cambio di tema non lascia colori vecchi.

### 5. Navigazione come FreeCAD, più «AutoCAD»
Studio 15, sezioni 2.1-2.6; studio 12, sezione 6; studio 12a, sezione 2.
- `navigation.py` nel nucleo:
  - gli stili di FreeCAD come tabelle di dati (gesto → azione), più «AutoCAD» (lo stile Revit con il doppio clic centrale per adattare la vista) e «SketchUp»;
  - una sola macchina di stati per pianta e 3D;
  - test per ogni stile, presi dalla tabella della sezione 2.2.
- Predefinito provvisorio «AutoCAD»: la scelta è di Daniel, quindi va in «Da decidere».
- La telecamera nel nucleo, con test numerici:
  - orbita Turntable, con la verticale che resta verticale, e Arcball a scelta;
  - perno sotto il cursore, con ripiego sul piano del terreno;
  - zoom verso il cursore;
  - clic centrale breve che ricentra;
  - animazioni di 250 ms, nessuna se il sistema chiede meno movimento.
- Nel 3D la telecamera guidata da questo modulo prende il posto di `OrbitCameraController` in `ui/qml/Scene.qml`, con i valori in binding. Un indicatore mostra il perno durante l'orbita.
- In pianta valgono pan e zoom dello stile; i gesti d'orbita non fanno nulla.
- Preferenze › Navigazione: lo stile, il tipo di orbita, il perno.

### 6. Pianta: orientamento e misure
Studio 12, sezione 6 «Pianta», V1-V3 e V9; studio 15, sezioni 3.3 e 3.11.
- La freccia del nord in alto a destra e la barra di scala 1-2-5 in basso a sinistra:
  - sono widget sovrapposti al viewport di `PlanView`, non disegnati in `drawForeground`;
  - i valori della scala si calcolano nel nucleo, con i test.
- Il passaggio del mouse evidenzia l'oggetto che il clic selezionerebbe, senza ridisegnare tutta la pianta.
- Nella barra di stato:
  - le coordinate dell'oggetto sotto il cursore;
  - la misura rapida della selezione: lunghezza, area, moduli, kWp.
- Se sta in piedi, lo strato statico della pianta in cache (P2-B).

### 7. Vista 3D: il cubo e le viste
Studio 12, sezione 6 «3D», T1-T3; studio 15, sezioni 2.5 e 2.6.
- Il cubo di vista in alto a destra:
  - facce Alto, N, E, S, O;
  - spigoli e vertici cliccabili;
  - frecce, anello della bussola, Home;
  - «orientamento più vicino», e il doppio clic che centra;
  - un menu: prospettiva o parallela, adatta, imposta come vista iniziale;
  - semitrasparente quando non serve.
- La matematica (orientamento più vicino, viste standard) sta nel nucleo, con i test.
- La selezione nel 3D è legata a quella della pianta; c'è lo zoom sulla selezione.

### 8. Criticità nelle viste
Studio 12, sezione 6 «Criticità», C1, C3 e C4; studio 13, regola 3.1.
- Un segno sull'oggetto, in pianta e nel 3D: un triangolo, con il numero se le criticità sono più d'una. Tre livelli, ognuno con icona e forma oltre al colore.
- Elenco e viste legati nei due sensi:
  - un clic su una voce evidenzia l'oggetto e attenua il resto;
  - dall'oggetto si arriva alle sue voci;
  - filtri per gravità;
  - segni sull'albero, che risalgono al genitore;
  - conteggi cliccabili nella barra di stato.

### 9. Pannelli e comandi
Studio 12, N2-N5; studio 13, regola 4.
- L'ispettore che cambia con la scheda (N2).
- L'albero del progetto con i segni (N3).
- I menu contestuali su oggetti della pianta, del 3D e dell'albero (N4).
- La barra con icona e testo (N5):
  - icone Lucide (ISC) in `data/icons/lucide` con la licenza, solo quelle usate;
  - ricolorate dal tema.

### 10. Se resta tempo: il guscio dell'assistente, senza modello
Studio 14, sezioni 7.3 e 8.
- Il personaggio è Meridio (la preferenza di Daniel, da confermare), su griglia 24:
  - raggi, orizzonte e linea del mezzogiorno nel colore del testo del tema, tratto 1,3: `M5.1 10.2H3.4M6.02 6.75L4.55 5.9M8.55 4.22L7.7 2.75M12 3.3V1.6M15.45 4.22L16.3 2.75M17.98 6.75L19.45 5.9M18.9 10.2H20.6M3 19.4H21M12 16.9V21.8`;
  - il disco: cerchio di centro (12; 10,2) e raggio 5,3. È riempito con il colore dell'assistente, portato a L 0,58-0,72 e C 0,07-0,15 in OKLCH, uguale in chiaro e in scuro, con contorno #24211d di tratto 1,3;
  - il sorriso: `M10.2 12.1Q12 13.5 13.8 12.1`, #24211d, tratto 1,2;
  - gli occhi: cerchi #24211d di raggio 0,9 in (10,1; 9,5) e (13,9; 9,5);
  - lo stato «pensa»: occhi 0,8 più in alto e tre puntini di raggio 0,75 in (19,2; 3,6), (21,2; 3,6) e (23,2; 3,6), nel colore del testo.
- Un solo widget figlio della finestra, sopra l'area centrale:
  - posizioni per scheda: Modello sopra la barra del sole, a sinistra di Proprietà; Producibilità in basso a sinistra; le altre in basso a destra;
  - scivola con `QPropertyAnimation` in 320 ms, senza animazione se il sistema chiede meno movimento;
  - si trascina e ricorda il posto per ogni scheda.
- Ctrl+L apre e chiude, con il cursore nel campo; Esc lo riduce al personaggio.
- Un elemento nella barra di stato; un interruttore in Preferenze che nasconde tutto.
- La chat dice «Assistente non ancora collegato».
- Test:
  - cambiando scheda resta lo stesso widget, con la conversazione;
  - le posizioni;
  - Ctrl+L ed Esc.
