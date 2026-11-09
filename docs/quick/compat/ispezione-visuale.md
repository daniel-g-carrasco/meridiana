# Ispezione visuale campionata dei riferimenti Widgets

Data: 04/11/2026. Esaminate individualmente con `view_image` 38 immagini PNG:
i 35 stati del progetto vuoto, chiaro, scala 1, 1600 x 960, e tre stati popolati
di Rho, scuro, scala 2, 1920 x 1080. Nessuna tavola riassuntiva al posto delle
singole immagini. [V] Conteggi e dimensioni verificati anche nelle intestazioni
PNG: rispettivamente 35 file da 1600 x 960 pixel e tre da 3840 x 2160 pixel.
Il visualizzatore riduce le immagini grandi per mostrarle: non e un controllo
pixel per pixel delle rasterizzazioni a scala 2.

Questa ispezione riguarda il programma **Widgets**, usato come riferimento.
Le osservazioni non sono difetti attribuiti a Quick e non dimostrano parita con
Quick. Non certificano gli altri casi della matrice, i gesti, le transizioni,
i risultati dei calcoli o la correttezza normativa dei messaggi. Un'immagine
statica non puo escludere una finestra transitoria o un fotogramma vuoto.

## Progetto vuoto: tutti i 35 PNG del caso richiesto

Directory completa, comune ai file della tabella:

```text
C:\Users\Grasso\dev\meridiana-wt-r12-compat\build\riferimento\baseline-v1\empty-light-s1-1600x960
```

Ogni riga identifica un file effettivamente aperto e guardato. Le osservazioni
sono [V] limitatamente a quanto appare nei pixel.

| File guardato | Osservazione |
|---|---|
| `phase-model.png` | Pianta vuota e vista 3D del terreno affiancate; Progetto, Sito, Verifiche e Aiuto presenti. Nell'albero edifici, sottocampi ed esclusioni sono a zero. Il pannello destro scorre. |
| `phase-plant.png` | Pianta vuota a tutta la zona centrale, barra Impianto e pannello laterale presenti. Accumulo aperto con «Nessuna batteria». Le verifiche indicano l'assenza di un sottocampo. |
| `phase-production.png` | Indicatori senza risultati e messaggio «Scarica prima il meteo del sito». Controlli delle perdite visibili nel pannello destro; nessuna curva energetica presente in questo stato. |
| `phase-consumption.png` | Grafico mensile F1/F2/F3 popolato dai valori automatici: 2.700 kWh annui. Testo a destra spiega la stima domestica; non e una schermata priva di consumi soltanto perche il progetto e vuoto. |
| `phase-economics.png` | Indicatori senza risultati e area grafica con richiesta del meteo. Campi economici a destra leggibili; il lungo titolo dell'energia acquistata termina con puntini. Secondo grafico sotto la zona visibile, con scorrimento. |
| `phase-report.png` | Messaggio centrale che richiede il calcolo, pulsante Calcola e opzioni della relazione a destra. Capitoli in parte disabilitati. Nessuna anteprima di relazione generata: questa foto non verifica un PDF. |
| `model-building.png` | Ancora il progetto vuoto con le proprieta del Sito, senza edificio selezionato. Questo file non documenta una scheda Edificio popolata, nonostante il nome dello stato. |
| `plant-subfield.png` | Sezione Pannelli aperta con invito a selezionare o disegnare un sottocampo; nessun sottocampo presente. Posa e Svuota sono visivamente disabilitati nella barra. |
| `plant-inverters.png` | Sezione Inverter aperta, nessun inverter scelto, pulsanti di catalogo e scelta automatica, rapporto DC/AC 1,10. La sezione Stringhe mostra zero stringhe su zero ingressi e un ingresso indicato come libero. |
| `plant-storage.png` | Accumulo aperto con «Nessuna batteria» e comando Configura accumulatore; non documenta la configurazione di una batteria presente. |
| `plant-strings.png` | Sezione Stringhe visibile con zero stringhe su zero ingressi, riga MPPT 1 e comandi di creazione. Nessuna stringa reale nella pianta; questa foto non prova il disegno delle stringhe. |
| `file-new.png` | Nuovo progetto mostra ricerca del sito, coordinate, campi facoltativi disabilitati e mappa Natural Earth. La colonna dei dati ha una barra di scorrimento; i campi inferiori proseguono fuori dalla porzione visibile. |
| `file-open.png` | Due schede per progetto Meridiana e PVsyst, con pulsanti Scegli il file. Fra i recenti compare la fixture del primo caso `empty-light-s1-1366x900/isolated`: dettaglio della sessione di cattura, spiegato sotto. |
| `file-save.png` | Tre schede distinte per Salva, Salva con nome e Salva una revisione. Etichette e pulsanti visibili; nessuna finestra di selezione file aperta in questa foto. |
| `file-export.png` | Schede Relazione, Note per la relazione, Una revisione e Modello IFC4 disposte su due righe, senza sovrapposizioni visibili. La foto non verifica l'esecuzione dei comandi. |
| `file-catalogues.png` | Cinque schede: moduli, inverter, microinverter, ottimizzatori, batterie. Pulsanti Apri visibili; non sono aperti gli elenchi dei prodotti. |
| `file-help.png` | Manuale, scorciatoie, visita guidata, segnalazione problemi e informazioni presenti in cinque schede. Il resto della pagina e intenzionalmente libero in questo stato. |
| `file-registry.png` | Clienti e commesse vuoti, con ricerca, importazione/esportazione e pulsanti Nuovo cliente/Nuova commessa. I due elenchi sono contenitori vuoti, senza righe di dati. |
| `settings-appearance.png` | Tema Chiaro, Indaco, fondi Grigi, testo Medio 13 px e IBM Plex Sans condensato nella barra. Anteprima con elenco, pulsante e avviso presente; reset della disposizione e dei valori visibile. |
| `settings-navigation.png` | Stile AutoCAD, orbita Turntable e centro sotto il cursore. Descrizioni dei gesti e delle combinazioni leggibili, senza sovrapposizioni nella zona mostrata. |
| `settings-keyboard.png` | Tabella Comando/Tasti/Predefiniti e ricerca presenti. La cella Tasti di Ripeti e abbreviata con puntini, mentre la colonna Predefiniti mostra la combinazione piu completa. Elenco e comandi inferiori visibili. |
| `settings-assistant.png` | Opzioni di Meridio, modello locale e voce presenti. La ricerca dei modelli mostra ancora «Cerco i modelli locali su questo PC...»: questa foto documenta uno stato di attesa, non l'esito della ricerca. |
| `settings-report.png` | Nessun profilo scelto: campi di firma disabilitati, Nuovo profilo disponibile. Nome, indirizzo, contatti, colore e logo ordinati in colonna. |
| `settings-maps.png` | Sfondo iniziale Nessuno e liste delle sorgenti con attribuzioni/licenze. I testi lunghi vanno a capo; le sorgenti proseguono sotto il viewport, con barra di scorrimento. |
| `settings-privacy.png` | Caselle dei servizi di rete e degli aggiornamenti non selezionate; opzione di installazione automatica disabilitata. Testi esplicativi presenti e leggibili; la foto non verifica il traffico di rete. |
| `menu-file.png` | Menu completo entro la finestra, con Nuovo/Apri/Salva, importazioni, esportazioni, impostazioni ed Esci; scorciatoie nella colonna destra. |
| `menu-edit.png` | Menu breve con Annulla e Ripeti disabilitati, Elimina visibile. Non si osservano righe tagliate. |
| `menu-draw.png` | Menu lungo di disegno e posa, fino ad Agganci e Orto. Tutte le righe rientrano nella finestra; comandi di posa disabilitati nel progetto vuoto. |
| `menu-site.png` | Menu con la sola voce Trova il sito. Nessun dialogo del sito aperto in questa foto. |
| `menu-compute.png` | Calcola, meteo, inverter, stringhe, curva di carico, consumi e accumulo visibili. Completa ed Elimina tutte le stringhe disabilitati; il menu rientra nella finestra. |
| `menu-view.png` | Viste, fasi, testo della barra, pannelli, zoom, orientamento, stringhe e sfondo presenti. Le frecce dei sottomenu sono visibili, ma i sottomenu non sono aperti e non sono stati ispezionati. |
| `menu-variants.png` | Voci Nuova, Rinomina, Elimina e Confronta variante leggibili, con le scorciatoie mostrate. Non prova l'apertura del confronto. |
| `menu-catalogues.png` | Cinque famiglie di prodotti e importazioni PAN/OND visibili. Non sono aperti i dialoghi di catalogo o importazione. |
| `menu-help.png` | Aiuto sul campo, Che cos'e, Manuale, scorciatoie, aggiornamenti, visita, segnalazione e informazioni leggibili nel popup. |
| `meridio.png` | Fumetto sopra la vista 3D, con selezione del modello, Allegati e campo di domanda. Il testo della conversazione e in un'area scorrevole e la sua prima riga visibile e tagliata sul bordo superiore; non si deduce da questa foto se sia un difetto o la posizione di scorrimento. |

## Rho popolato: i tre PNG richiesti

Directory completa, comune ai tre file della tabella:

```text
C:\Users\Grasso\dev\meridiana-wt-r12-compat\build\riferimento\popolati-v1\rho-dark-s2-1920x1080
```

| File guardato | Osservazione |
|---|---|
| `plant-storage.png` | Tema scuro e pianta popolata: quattro edifici, due sottocampi, moduli e etichette delle stringhe. Barra con sette inverter e 57 stringhe; Accumulo mostra «Fixture AC200». Le etichette delle stringhe sono molto ravvicinate nel gruppo superiore. Le verifiche mostrano errori e avvisi: li si registra come contenuto della fixture, senza giudicarne il calcolo o le norme. |
| `phase-consumption.png` | Riepilogo dell'impianto calcolato con una batteria da 200,0 kWh utilizzabili. Consumo annuo 400.000 kWh, quote F1/F2/F3 e dodici barre mensili visibili. Legenda e unità presenti; il profilo nel selettore destro e abbreviato per la larghezza del controllo. La presenza dei numeri non e una loro validazione energetica. |
| `phase-economics.png` | Indicatori economici popolati, tra cui autoconsumo 62%, autosufficienza 66% e investimento 450.000 euro. Due grafici mensili disegnati con componenti di accumulo; il secondo prosegue sotto il viewport. Etichette, legende del primo grafico e controlli di scorrimento visibili. Nessuna verifica finanziaria dei valori eseguita qui. |

## Osservazioni trasversali e limiti

- [V] In piu pagine senza pianta, ad esempio `file-save.png`,
  `settings-navigation.png`, `phase-consumption.png` e `phase-economics.png`,
  la fascia inferiore conserva istruzioni di selezione e trascinamento della
  pianta. E il comportamento del riferimento Widgets catturato; non costituisce
  un difetto introdotto da Quick. Non e stata eseguita una correzione.
- [V] Il percorso recente del caso 1366 x 900 in `file-open.png` e compatibile
  con il banco: in `tools/quick_rif.py`, `worker` crea il percorso `isolated` e
  l'applicazione prima del ciclo `for theme, size in cases`. La stessa finestra
  viene riutilizzata per temi e misure dello stesso progetto e della stessa
  scala. L'isolamento e dal profilo personale, non una sessione nuova fra le
  misure. Dal percorso non si deduce una contaminazione del profilo utente.
- [V] Nel campione visto non ci sono immagini interamente vuote o pannelli
  accidentalmente assenti riconoscibili dai soli pixel. Vi sono stati vuoti
  dichiarati, campi disabilitati, titoli abbreviati e contenuti fuori dal
  viewport con scorrimento. Queste osservazioni non escludono difetti negli
  stati o nei fotogrammi non ispezionati.
- [V] I menu sono stati guardati aperti nei PNG; nessun comando e stato invocato
  durante questa ispezione. Le foto di File non provano l'assenza della
  finestrella transitoria R392. Non sono state misurate fluidita, geometrie a
  tolleranza 1 px, contrasto numerico, font risolti o accessibilita.
- Non sono stati guardati qui gli altri temi, dimensioni e scale del progetto
  vuoto, gli altri stati Rho, o le catture Rho originali ancora in lavorazione.
  L'elenco sopra e l'intero ambito di questa ispezione: 35 piu 3 file.
