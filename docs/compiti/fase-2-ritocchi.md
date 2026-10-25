# Compito per una sessione cloud: i ritocchi decisi da Daniel il 23/10/2026

Cose decise e chiare, da fare. Le regole di lavoro sono quelle di `docs/compiti/fase-2.md` («Come lavorare»):
- ramo `fase-2-ritocchi` da `lavoro`;
- richiesta di unione in bozza verso `lavoro`, con i passi come caselle;
- un commit per pezzo, con i suoi test, lint e suite verdi, spinto subito;
- `docs/richieste.md` aggiornato nello stesso commit della richiesta che chiude (i numeri R sono di quel file);
- alla fine un riassunto in italiano.

**Prima di cominciare** controlla che `lavoro` contenga le correzioni di `docs/compiti/fase-2-correzioni.md` (ramo `fase-2-correzioni` unito). Se non ci sono, fermati e dillo nella richiesta di unione: i due lavori toccano gli stessi file.

## 1. La pianta e il 3D tornano leggibili (R16, la priorità)

Daniel: «i tratti devono essere distinguibili in qualche modo dalla foto, questo ha la priorità, ma il tema chiaro non risolve il problema e forse lo accentua […] Non capisco come mai hai fatto tutta questa fatica nel portare i colori del tema anche nella modellazione 2d e 3d. Ora in quella 3d sembra sempre notte, e le belle linee visibili che c'erano prima (forse arancioni?) ora a malapena si vedono. Io per tema intendevo sull'interfaccia e al massimo in bottoni che ci sono in modellazione. Lo sfondo dell'ortofoto lo manterrei sempre scuro».

- **Il tema vale per l'interfaccia** (finestre, pannelli, campi, pulsanti, barre) e per i pulsanti che stanno sopra le viste. **La pianta e il 3D hanno colori propri**, uguali in tema chiaro e scuro.
- **Base:** i colori della pianta e del 3D prima della fase 2, cioè quelli del commit `9cc8314` (`ui/plan.py`, `mesh.py`, `ui/qml/Scene.qml`, `ui/view3d.py`): le linee arancioni, il cielo di giorno.
- **Ortofoto sempre scurita**, uguale nei due temi:
  - una velatura scura regolabile, predefinita intorno al 40%;
  - tratti chiari e saturi con un alone scuro a due toni, così si leggono sia sui tetti chiari sia su quelli scuri.

  La schermata di Daniel del 23/10, una linea di disegno quasi invisibile su un tetto chiaro, è il caso di prova.
- **Senza ortofoto:** il fondo chiaro di prima.
- **Il 3D:** il cielo di giorno e le linee ben visibili di prima, in tutti e due i temi.
- **La selezione nel 3D (R29).** Daniel: «quando si seleziona un qualsiasi oggetto in modellazione 3d, questo si schiarisce solamente per farti capire quale è selezionato, ma è poco visibile. Andrebbero invece evidenziati i bordi esterni o trovato un modo più furbo. Hai visto come fa freecad in 3d?».
  - FreeCAD (studio 15, sezione 3.3) colora l'elemento sotto il cursore e quello selezionato in una tinta satura propria, non lo schiarisce: giallo e verde nella 1.1, due azzurri nella 26.3, scelti apposta per vedersi in tutti i temi.
  - Lo studio 15 propone in più un contorno, per non affidarsi al solo colore.
  - Qui: l'oggetto selezionato in una tinta satura distinta dagli avvisi, con il contorno esterno marcato; quello sotto il cursore in una tinta vicina e più leggera; la stessa logica in pianta.
  - In Qt Quick 3D il contorno si fa con un secondo disegno dei bordi (linee o una copia appena ingrandita dietro), oppure con un effetto di post-produzione. Prova le strade, misura il costo e scegli; la scelta va nella richiesta di unione.
- Le prove fatte sul tema per pianta e 3D in `test_theme.py` e negli altri test vanno adattate: la pianta e il 3D non cambiano con il tema, l'interfaccia sì.
- Lo studio 13 va aggiornato (sezioni 3 e 12): una riga che dice la regola nuova e perché.

## 2. I comandi delle viste dentro le viste (R14, R27)

Daniel:
- «sarebbe da spostare gli elementi di controllo del disegno che ora stanno alla barra estrema bassa del programma perché siano inclusi nelle aree di disegno. Inoltre questa barra non ha margini / padding esterni»;
- «le modalità di visione "pianta", "3d", "affiancata" devono stare da altra parte ed essere visualizzate in altro modo o comunque distinte dal resto degli strumenti. Ciò che riguarda le viste non può stare nelle viste?».

- **Una barra sottile dentro ogni vista**, in un angolo che non copre il disegno, come la barra dei comandi di vista di Revit:
  - Pianta, 3D e Affiancate come un selettore a tre;
  - «Inquadra»;
  - nella pianta, agganci (F3) e orto (F8) come interruttori con il loro stato.
- I tasti restano gli stessi. Questi comandi escono dalla barra degli strumenti e dalla barra di stato.
- **La barra di stato** ha margini interni ed esterni come il resto della finestra.
- Test: i comandi esistono una volta sola; i tasti funzionano; lo stato degli interruttori si vede.

## 3. Strumenti con le sole icone (R19, prima parte)

Daniel: «gli strumenti quando messi su un fianco devono vedersi solo le icone (e ci deve essere opzione per vedere solo quelle in generale, che forse metterei di default)».

- In Preferenze › Aspetto, «Barra degli strumenti: solo icone / icone e testo», con **predefinito solo icone**. Una barra messa su un fianco mostra sempre solo le icone.
- Ogni pulsante ha il suggerimento con il nome e il tasto.
- Dove stare (sotto le schede o altrove) è nello studio 17: qui non si sposta.

## 4. La navigazione spiegata (decisione 1 del 23/10)

Daniel: «metti autocad di default. nelle impostazioni deve essere spiegato bene cosa fa uno e cosa fa l'altro».

- «AutoCAD» resta il predefinito.
- In Preferenze › Navigazione, per lo stile scelto, una tabella in parole: pan, orbita, zoom, ricentra, adatta, selezione, menu. Accanto, una riga su a chi conviene (per esempio: «come AutoCAD e Revit: per chi disegna in AutoCAD»). Le tabelle vengono da `navigation.py` e non sono scritte due volte.
- Test: ogni stile ha la sua spiegazione; la tabella cambia con lo stile.

## 5. L'assistente anche nelle barre laterali (R17)

Daniel: «ci starebbe che si potesse mettere anche sulle barre laterali essendo che di solito è lì dove dà meno fastidio».

- Un'opzione «Aggancia ai pannelli»: la conversazione diventa un pannello agganciabile come Progetto e Proprietà, con il personaggio in testa. Con l'opzione spenta torna flottante.
- La conversazione è la stessa nei due modi.
- La scelta si ricorda.
- Test: il passaggio da flottante ad agganciato e ritorno conserva la conversazione e il testo scritto.

## 6. Lo sfondo della pianta e le immagini (R21)

Daniel: «all'interno del 2D non c'è possibilità di cambiare mappa, di non mostrare l'ortofoto, di cambiare ortofoto, di importare immagini (con visualizzazione con trasparenze e possibilità di metterlo in scala)».

- **Nella barra della pianta**, un menu «Sfondo»:
  - le sorgenti che `tiles.py` sa già usare (ortofoto PCN, OpenStreetMap), più quelle libere e lecite che trovi documentate, con la licenza e l'attribuzione;
  - «Nessuno»;
  - la velatura del passo 1.
- **«Importa un'immagine…»** (PNG, JPG e la prima pagina di un PDF, con PyMuPDF se c'è già, altrimenti solo immagini):
  - si posa sotto il disegno con una trasparenza regolabile;
  - si mette in scala con due punti e la distanza vera, digitata;
  - si sposta e si ruota;
  - si può nascondere;
  - è salvata nel progetto, con la versione del formato e la migrazione.
- Test:
  - la messa in scala con due punti dà la scala giusta;
  - salvato e riaperto, lo sfondo resta uguale;
  - un progetto vecchio si apre senza immagini.

## 7. Il catalogo mostra tutto (R25)

Daniel: «la finestra per selezione del modulo fotovoltaico arriva solo a 400 righe. Secondo me c'è un bug».

- Oggi mostra le prime 400 righe di 16.959, di proposito, per la velocità. La tabella diventa un modello (`QAbstractTableModel` con `QSortFilterProxyModel`) che mostra tutte le righe senza costruirle una per una, con l'ordinamento per colonna e il conteggio «N moduli».
- I filtri nuovi sono il compito `16e-filtri-catalogo.md`; questo passo prepara solo il modello su cui si appoggeranno.
- Test: con 16.959 righe la finestra si apre e filtra in meno di 200 ms (misura nel test con un margine largo); l'ultima riga si raggiunge.

## 8. I pulsanti in italiano (R26)

In una schermata di Daniel la finestra del catalogo ha «OK» e **«Cancel»**: le traduzioni di Qt non sono caricate.
- Caricare `qtbase_it` dal percorso delle traduzioni di Qt (`QLibraryInfo`) accanto a quelle di Meridiana.
- Controllare che ci sia nel pacchetto Windows e nel Flatpak.
- Test: con la lingua italiana, il pulsante standard Annulla di una `QDialogButtonBox` dice «Annulla».

## 9. I filtri delle Verifiche (R13, la parte che è un difetto)

Daniel: «sembra che i tasti di "mostra ciò..." non funzionino alla grande».

- Prova i pulsanti di filtro del pannello Verifiche e i conteggi della barra di stato, con un progetto che ha voci di tutti i livelli.
- Scrivi nella richiesta di unione che cosa non va.
- Correggi quello che è un difetto, con i test.
- Come presentare meglio le voci è nello studio 17: qui non si ridisegna.

## 10. Il segno sull'albero (R30, la parte che è un difetto)

Daniel: «di fianco a Sito: ... c'è una "i" dentro un cerchietto con un numero che sono piccolissimi e renderizzati male e non si capisce cosa sono. Quando ci si passa sopra con il mouse non succede nulla».

- Il segno delle verifiche nell'albero (`ui/marks.py`, `icon`) va:
  - disegnato alla densità dello schermo (`devicePixelRatio`), non in un'immagine di 22 × 20 punti allargata;
  - grande quanto il testo della riga;
  - con il numero leggibile.
- Al passaggio del mouse, un suggerimento dice che cosa è: «3 da sapere, 1 da controllare in questo oggetto e dentro»; un clic apre il pannello Verifiche filtrato su quell'oggetto.
- La presentazione dell'albero (spaziature, sezioni, gerarchia) è nello studio 17: qui non si ridisegna.
- Test: il suggerimento c'è e dice i conteggi giusti; il clic filtra le verifiche.
