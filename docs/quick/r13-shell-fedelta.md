# r13-shell: esito della passata, 05/11/2026

La finestra unita usa tutte le parti registrate e tutti i comandi del catalogo.
File sostituisce l'area sotto le fasi; la disposizione delle schede si conserva
anche al riavvio. Il calcolo si annulla alla chiusura. I Widgets e il nucleo
non sono stati modificati da questo ramo.

La passata della shell e implementata e verificata nei limiti qui descritti.
**Non dichiaro indistinguibile l'intero programma, ne superata la fluidita al
monitor.** Restano differenze nei contenuti degli altri rami e prove rosse
nella raccolta unita. Il registro di compatibilita resta conservativo:
un comando registrato non equivale alla certificazione di tutti i suoi casi.

## Cosa e stato portato

| Parte | Risultato e prova |
|---|---|
| Registro | [V] `backend/parts.py`, pubblicato per primo in `31d0bc6`: installazione, posti, controller, comandi, bind e chiusura inversa idempotente. Pianta e 3D passano dal registro. Contratto in `stato/parti-pronte.txt`; test collisioni e ciclo di vita. |
| Pilot | [V] `tools/quick_pilot.py`, primo copione in `43a17c7`. Stessi gesti nei due processi, puntatore mosso con eventi Qt locali, ricerca dei controlli visibili, foto e JSON a ogni passo. Gli stati attesi fanno fallire il percorso se diversi. |
| Linguette | [V] Percorsi, raccordi, dischi, colori e misure da `ui/phasebar.py`. CurveRenderer con antialiasing; numero da QPainterPath, come nei Widgets; scorrimento OutCubic di 110 ms. File accende il suo pulsante e spegne tutte le fasi. Nessuna seconda linea della barra sotto File. |
| Strumenti | [V] Gruppi, separatori, parole e misure dal catalogo originale. Tre modi, barra in alto o a sinistra. Menu alla pressione della freccia e al tasto destro, scorciatoie, separatori e comandi distruttivi. 74 spiegazioni copiate dal riferimento. Calcola e Posa rispettano R396. |
| Barra laterale | [V] Misurata nel QToolBar vero: 37 px, controlli 33 x 33 e margine 2 px. Stessi ingombri nella Quick, nessuna scheda aggiunta intorno. I pulsanti con opzioni conservano una freccia e il menu anche qui. |
| Fasi e schede | [V] Politica di `arrangement`, pagine lazy conservate, editor prestati senza ricrearli; Progetto 310 px e Proprietà 370 px. Gruppi con linguette dentro i margini, trascinamento con immagine e anteprima, aggancio, flottanti, chiusura e riapertura dal piede. Ripristino annullabile per 15 s, schermo pulito reversibile. |
| Persistenza | [V] Test chiude e ricrea la finestra: ritrova 410 px a destra, Progetto raggruppato a destra e Verifiche chiuse. Stato atomico con copia precedente, validazione e segnalazione degli errori. Il primo ripristino non anima da misure intermedie. |
| Stato | [V] Fascia dei comandi in fondo, testo esposto dalla pianta; nessuna istruzione della pianta nelle altre fasi. Conteggi dal controller delle Verifiche, senza zero isolato, tre pulsanti pannelli, aiuto e Meridio. |
| File | [V] Contenuto del ramo File, a tutta pagina sotto le fasi. Transizione a due catture come `motion.enter/leave`, 180/110 ms, niente finestra di primo livello nuova. Meno movimento elimina la transizione. |
| Menu e tasti | [V] Catalogo completo registrato; Alt mette il fuoco sul primo menu, frecce, Giu, Invio, Esc e mnemoniche. Modifica di una scorciatoia dalle Impostazioni verificata nella finestra. Menu Cataloghi, Sito, Varianti e sottogruppi Vista/Pannelli agganciati. |
| Comandi lunghi | [V] Layout, anno, confronto, meteo ed export separati e annullabili. Chiusura durante il calcolo verificata sotto 750 ms. IFC riaperto con dispositivi solari; CSV confrontato byte per byte. Annullare un export non distrugge il file gia esistente. |
| Aggancio Meridio | [V] Loader con dimensioni conservate dopo il riparentamento; casa dentro il 3D al primo fotogramma esposto. Il collegamento Python al frame si scollega dopo il primo uso. Nessun personaggio sopra File. |

## Confronto dei due programmi

Aprire `confronto/r13-shell/index.html`. La revisione corrente e R06;
le precedenti sono conservate e dichiarate come tali.

- [V] `shell-matrix.json`: 14 passi, tutte le sei fasi, File, ritorno al
  progetto, Alt, 1600 x 960, 1920 x 1080, 1366 x 900. Quattro matrici:
  chiaro/scuro e scala 1/2. 56 stati per programma, 112 ritagli accoppiati
  al 200 %. Le immagini Widgets sono il riferimento R04 con lo stesso
  progetto, impostazioni e preparazione; R06 ripete il lato Quick dopo le unioni.
- [V] `shell-menu.json`: hover, tooltip, menu del tasto destro, Esc, Alt,
  nei due programmi. `shell-large.json`: cinque passi con testo grande,
  scuro, 1366 x 900; lo stesso percorso verifica anche i modi della barra.
- [V] Rho e letto dalla cartella di prova, mai salvato sul file originale.
  Il meteo registrato e la posa sono preparati allo stesso modo; conteggi
  iniziali uguali. Questi copioni della shell non aspettano l'anno energetico
  e **non certificano i risultati numerici delle pagine**.
- [V] Nella matrice scura, campioni liberi da testo di barra e Progetto:
  #252525 in entrambi; fondo #151515 in entrambi. Test sui pixel nel ramo.
  Non e riprodotto il doppio riempimento segnalato nella foto precedente.
- [V] In File il contorno della barra non viene disegnato, tutte le linguette
  hanno disco neutro e File e premuto. Il test controlla anche il ritorno con
  Esc e lo stato accessibile della fase.

Il pilot usa finestre Windows vere e Direct3D 11 sul desktop separato, con
render loop threaded. Non misura la presentazione al monitor o il mouse del
sistema. I tempi ottenuti mentre altri rami lavorano non sono benchmark.

## Differenze volute e differenze rimaste

- **R396:** Calcola e Posa senza fondo permanente e senza enfasi tipografica.
  Le vecchie foto Widgets conservano il trattamento precedente; non va copiato.
- **R383:** Aiuto nel fumetto di Meridio, la colonna destra va tutta a Proprietà.
- **R388:** messaggi brevi e contestuali della pianta nel piede. Le foto Widgets
  possono mostrare la vecchia frase lunga o il messaggio transitorio della posa.
- **Barra a sinistra:** stessi ingombri; le frecce rendono disponibili anche
  le opzioni dei pulsanti divisi. Il QToolBar Widgets copia solo l'azione
  principale di quei pulsanti. Differenza esplicita per conservare le funzioni.
- [V] Rasterizzazione del testo e degli SVG diversa a scala 1: bordi colorati
  del testo Quick e qualche bordo piu morbido rispetto al raster Widgets.
  I numeri delle fasi usano ora lo stesso contorno vettoriale, ma non si
  dichiara identita pixel per pixel. Icone comuni: responsabilita Controlli.
- [V] Restano piccoli scarti di margine nelle schede e nella quota superiore
  delle Verifiche. I contenuti hanno ulteriori differenze visibili: stringhe
  in Modellazione, inquadratura/terreno 3D, righe e ritorni a capo delle
  Verifiche. Sono visibili nelle coppie intere e appartengono alle rispettive
  parti; non sono stati coperti con correzioni nei loro file.
- [V] Gli stati disabilitati seguono ora registrazione e selezione effettive.
  La prova integrata copre i percorsi principali e la presenza dei gestori,
  non ogni combinazione di dati di tutti i 90 comandi.

## Verifiche della versione unita

Ricevute in `confronto/r13-shell/verifiche/`. Le raccolte hanno processi
separati per evitare di mescolare QApplication e QGuiApplication.

| Raccolta | Esito osservato |
|---|---|
| Shell | [V] 19 prove passate: stato, File, menu, disposizione, riavvio, integrazione, cancellazione, export e registro. |
| Sistema | [V] 46 prove passate. |
| Registro | [V] 10 prove passate; inventario di 752 elementi, 400 righe richieste, 1196 prove Widgets e 50 manifesti. Nessun errore di inventario. |
| Parita completa, prima dell'ultima unione grafici | [V] 70 prove passate, 7 saltate e 2 fallimenti attesi. Non trasformate in certificazione globale delle 752 righe. |
| Formati | [V] 96 prove passate. |
| Pianta | [V] 196 prove passate, 1 saltata e 1 fallimento atteso, dopo preparazione QApplication. I precedenti errori della raccolta mista restano nei log storici. |
| Vista 3D | [V] 102 prove passate, 17 saltate, nella raccolta unita precedente. |
| Meridio | [V] 63 prove passate nella raccolta unita precedente; la parte pubblica anche le sue ricevute successive. |
| Pagine | [V] 73 prove passate, 3 saltate, con loop basic. Il banco threaded resta bloccato in QTest.qWait di test_file_part; il pilot threaded e i percorsi shell proseguono. Non chiamato un blocco del programma normale. |
| Grafici, ultima unione | [V] 68 prove, 1 fallita e 1 saltata. test_loss_steps_keep_readable_rows_in_a_short_page misura 0 invece di almeno 16 px/riga. Isolata misura -1,9167: non e la stessa misura, resta rossa. Segnalata al ramo fasi. |
| Proprieta | [V] Raccolta precedente: 51 prove, 2 fallimenti. Separatore decimale dipendente dalla lingua precedente e pillola nativa 36 contro 34 px. Successive correzioni del proprietario integrate, senza dichiarare retroattivamente verde quel log. |
| Lint e traduzioni | [V] Ruff F/E9/B e compilazione Python dei cataloghi passati. |

La suite Widgets completa e stata eseguita una volta: 1242 nucleo, 294
calcoli, 96 formati, 810 widget e 388 finestra. Calcoli e formati verdi;
12 fallimenti negli altri gruppi. Ripetuti isolatamente, 11 passano;
resta il caricamento del catalogo a 0,425 s contro 0,4 s. Nessuna soglia
modificata e nessun file Widgets corretto per ottenere il verde.

Un avviso diverso resta possibile chiudendo molto presto un catalogo che
sta creando i delegati: `Object or context destroyed during incubation`,
visto anche in ChecksPage. Il precedente ciclo di `visible` era prodotto
dal banco che chiamava direttamente `closeCatalog`: con Esc reale non si
riproduce. Il percorso ordinario attende la pagina pronta e non filtra avvisi.

## Avvio e riuso

`python -m meridiana.quick "<progetto>"` avvia la versione separata.
Il profilo e `build/quick-runtime`, cambiabile con `--profile <cartella>`.
La disposizione sta in `quick-profile/state/quick-shell.json`; preferenze
e cache non usano il profilo Widgets. Aprire un progetto non lo salva.

Riutilizzabili per R397: registro con install/bind/close, catalogo dei comandi,
persistenza della disposizione, transizione File, pilot e confronto con
validazione degli stati. I nomi delle fasi, i testi e le parti fotovoltaiche
restano specifici di Meridiana. Nessuna modifica al template in questa passata.

Nessun push, tag o release. Le nuove schermate e `da-sistemare.md` forniti
dall'altra sessione restano fuori dai commit della shell.
