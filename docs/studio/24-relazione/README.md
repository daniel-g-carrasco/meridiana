# Studio 24: la relazione da un foglio bianco

Fable FR, 02/11/2026, ramo `r10-relazione`. Solo studio: nessun codice del programma. Daniel dopo V (R291) e R311:
«si notano poco, sembra quella di prima leggermente diversa». Qui si riparte dall'impostazione, non dai ritocchi.

Cosa c'è nella cartella:

- `README.md`: lettori e ordine delle cose, che cosa non va oggi, riferimenti del settore, domande aperte.
- `motore.md`: il motore di impaginazione (oggi QTextDocument) con prove misurate e voti.
- `bozzetti.html`: tre impostazioni davvero diverse a misura A4, con una pagina di oggi accanto. Si apre nel browser;
  `?only=A|B|C|oggi` mostra una sola serie. Foto in `foto/bozzetto-A.png`, `-B.png`, `-C.png`, `-oggi.png`.
- `foto/oggi-*.png`: le pagine di oggi (dal lavoro di V, 30/10).

## 1. Chi legge e che cosa gli serve, in che ordine

Tre lettori, tre modi di leggere lo stesso documento.

| Lettore | Che cosa cerca | Dove deve trovarlo | Che cosa salta |
|---|---|---|---|
| Committente (titolare, direttore di stabilimento) | quanto produce, quanto costa, quando rientra, che cosa gli mettono sul tetto | **prima pagina**, in un minuto: 4 numeri, pianta piccola, verifiche «tutte conformi» | tutto il resto; al più guarda l'economia |
| Autorizzazioni (Comune, distributore, GSE, VVF se serve) | dati di targa, sito, schema, norme applicate, chi firma | copertina con i dati formali; capitolo verifiche con **norma, articolo, esito** per ogni riga; allegati | producibilità ed economia |
| Installatore / impresa | moduli, stringhe per ingresso, passo delle file, distanze, tensioni di stringa, dove stanno gli inverter | pianta grande e leggibile, tabelle di posa e stringhe, schede dei componenti | economia, metodi di calcolo |
| Chi controlla il calcolo (Daniel stesso, un collega, il perito di parte) | **da dove viene ogni numero** | la fonte accanto al numero (riga del registro, norma, dato di catalogo), non in fondo | niente |

Ordine che ne segue (modello **Completa**): copertina formale con i 4 numeri di testa -> scheda di sintesi (una pagina,
leggibile da sola) -> sito e clima -> coperture e posa (pianta grande qui, una volta sola) -> impianto elettrico ->
producibilità e perdite -> consumi e bilancio -> economia -> verifiche e norme -> parametri e metodi -> allegati
(schede componenti, registro dei calcoli, PDF allegati). È l'ordine di oggi con due cambi: la **scheda di sintesi**
è una pagina sola, chiusa, e la **pianta** sta nella posa (oggi è nella Sintesi e la posa resta mezza vuota, foto
`oggi-completa-05.png`). Il modello **Sintetica** = scheda di sintesi + energia per mese + moduli e stringhe +
parametri, senza copertina separata (come oggi, R61).

In allegato, non nel corpo: schede dei componenti, registro dei calcoli riga per riga (oggi è un CSV: diventa un
allegato impaginato, così «R-040.07» nel testo porta a una riga precisa), PDF allegati dal progettista.

## 2. Che cosa non va oggi (foto in `foto/`)

Verificato sulle foto di V (`V-dopo-*`, 30/10):

1. **Non ha una gerarchia visiva**: tutto è grigio chiaro su bianco con un titolo nero; i numeri che contano (331 kWp,
   420 MWh, PR) hanno la stessa taglia di «Rapporto DC/AC». Un committente non trova niente in un minuto
   (`oggi-completa-03.png`, `oggi-sintetica-01.png`).
2. **Pagine vuote per due terzi**: salto pagina a ogni capitolo con contenuti corti (`oggi-completa-05.png`:
   una tabella di una riga e due paragrafi, poi bianco).
3. **Copertina vuota al centro**, contatti del profilo in alto a destra come una lettera, titolo a metà pagina senza
   nulla intorno (`oggi-completa-01.png`).
4. **Le fonti non si vedono**: «ogni numero dice da dove viene» oggi vive nel registro CSV e nel capitolo Metodi, non
   accanto al numero. Le didascalie dei grafici sono in inglese finché il `po` non è aggiornato (`oggi-completa-12.png`).
5. **Grafici da notebook** (matplotlib con assi, griglia, colore blu di serie), non da documento: stessa pagina.
6. Tecnico, ma pesa: una riga di tabella si spezza fra due pagine (QTextDocument; misurato in `motore.md`).

## 3. Riferimenti del settore

Tre ricerche web (02/11/2026); nessun campione ufficiale aperto, quanto segue è **dedotto** dagli estratti dei
risultati, non verificato su un PDF originale.

- **PVsyst**: struttura costante nei report caricati in rete: copertina; riassunto progetto e risultati; parametri
  generali; caratteristiche del campo e perdite di sistema; ombre vicine (diagramma iso-ombre); **risultati
  principali** (energia, kWh/kWp/anno, PR, grafico delle produzioni normalizzate, tabella dei bilanci mensili);
  **diagramma delle perdite** dal globale orizzontale all'energia immessa; grafici speciali; P50-P90; bilancio CO₂.
  Fonti: esempi caricati su Scribd e nei fascicoli del Camden Council, es.
  https://camdocs.camden.gov.uk/CMWebDrawer/Record/7351402/file/document e
  https://edbodmer.com/wp-content/uploads/2024/07/MCV-OnGrid-System.VC0-Report.pdf (dedotto dagli estratti).
  Lezione: due pagine valgono tutto il resto, i risultati principali e la cascata delle perdite; il PR è il numero di
  confronto fra progettisti.
- **PV*SOL premium**: il report «project report» copre dati di sistema, simulazione e redditività, logo e contenuti a
  scelta, esportazione Word o PDF; dal 2026 c'è una **presentazione per il cliente** separata, in PDF o DOCX.
  Fonti: https://valentin-software.com/en/products/pvsol-premium ,
  https://valentin-software.com/en/product-news-blog-en/pvsol-premium-2026-available-now/ . Lezione: il documento
  tecnico e quello per il cliente sono due cose; da noi sono i due modelli (Completa e Sintetica) o, meglio, la scheda
  di sintesi che apre la Completa e vive da sola nella Sintetica.
- **HelioScope (Aurora)**: report da modelli («Report Templates» nelle Libraries, formato pagina e orientamento a
  scelta), report di produzione e ombre separati dalle proposte. Fonte:
  https://help-center.helioscope.com/hc/en-us/categories/17530782764819-Reports . Di Aurora Solar non ho trovato
  un campione pubblico. Lezione: il modello è un oggetto che l'utente sceglie, non un'impostazione nascosta.

Le relazioni di Daniel (es. SolarEdge) restano un riferimento, non il default (R61, R81): la colonna delle fonti del
bozzetto A è la nostra differenza rispetto a tutti e tre.

## 4. I tre bozzetti (`bozzetti.html`)

Stesso impianto in tutti: 331,2 kWp, 736 moduli × 450 Wp, 2 inverter × 100 kW, 420.700 kWh/anno, 1.270 kWh/kWp,
PR 78,1 %, Rho (MI); dati illustrativi coerenti fra loro (PR = 1.270 / 1.626; i mesi sommano a 420.700).

| | A, Registro | B, Scheda | C, Dossier |
|---|---|---|---|
| Idea | la colonna sinistra porta etichette, fonti e note; a destra il contenuto | la prima pagina è una scheda che si legge in un minuto; colore per tipo di dato | documento d'ingegneria: serif giustificato, numeri a spaziatura fissa, colonna laterale |
| Carattere | Inter (in `data/fonts`) | Titillium Web (in `data/fonts`, PA italiana) | Source Serif 4 + IBM Plex Mono (OFL, da aggiungere, ~1,2 MB) + Inter |
| Colore | un blu-inchiostro | ambra energia, azzurro impianto, verde economia, ardesia | un rosso-ruggine per rubriche e fonti |
| Fonti | colonna «Fonte» in ogni tabella, note in margine | nota piccola sotto ogni blocco | colonna laterale con codice del registro |
| Per chi | autorizzazioni, installatori, chi controlla | committente, GSE, sportello | chi firma e chi legge con calma |
| Fattibile con QTextDocument? | sì, con tabelle per la griglia | in parte (riquadri sì, cascata e pillole con immagini) | no: niente sillabazione, colonne, giustificazione buona |

**Raccomandazione**: **A come ossatura della Completa**, con la **prima pagina di B** come scheda di sintesi (pagina 2
della Completa e tutta la Sintetica). I tre lettori sono serviti nell'ordine in cui arrivano; la colonna delle fonti
rende visibile la regola del programma. C è il più bello su carta ma costa due famiglie di caratteri e un motore
con sillabazione, e sullo schermo (anteprima) rende meno. Decide Daniel.

## 5. Domande aperte (poche)

1. **Motore**: restare su QTextDocument (A fattibile, B a metà, righe che si spezzano) o passare a Typst (29 MB, tutto
   fattibile, anteprima dal PDF con QtPdf già in uso)? La mia raccomandazione è Typst: vedi `motore.md`.
2. **La colonna delle fonti** nelle tabelle: codice del registro («R-040.07») o testo breve («PVGIS 5.3»)? Propongo il
   codice, con la legenda nell'allegato del registro: corto, non va a capo, e porta a una riga precisa.
3. **Colore**: la Completa in un colore solo (A) o con i tre colori di B anche nei capitoli? Propongo un colore
   d'accento scelto nel profilo di firma (il blu di A per default), e i tre colori solo nella scheda di sintesi.
4. **Grafici**: rifarli nello stile del documento (barre piene, niente assi e griglia, didascalia numerata, fonte)
   invece del matplotlib di oggi; con Typst si disegnano in Typst stesso (nessuna immagine). Propongo di sì.

## 6. Secondo giro: tre vie di mezzo fra B e C (`bozzetti-2.html`)

Daniel (02/11): via di mezzo B-C, senza la barra blu in alto, header e footer completi con il posto per il logo,
contenitori e grafici arrotondati, pianta ampia come in C, rendering 3D grande in copertina «come SolarEdge».
Foto: `foto/bozzetto2-V1.png`, `-V2.png`, `-V3.png` (4 pagine ciascuna: copertina, sintesi, perdite, pianta).
Solo Inter e Titillium Web (in `data/fonts`), niente Google Fonts. Logo finto e neutro (tetto con tre moduli).

| | V1 Cornice | V2 Filetto | V3 Lavagna |
|---|---|---|---|
| Copertina | rendering in cornice arrotondata, titolo e 4 riquadri sotto | rendering a tutta larghezza che sfuma nel bianco, titolo e meta a due colonne | rendering a tutta pagina, pannello scuro in basso con i 4 numeri |
| Header | logo a sinistra, titolo e committente al centro, codice/rev/data a destra, filetto azzurro | riga di meta in alto, titolo del capitolo sotto un filetto rosso, logo a destra | pillola col codice, titolo del capitolo, logo a destra |
| Footer | tre colonne su filetto: progettista, codice/rev/data, pagina n di N | progettista e committente al centro, codice a sinistra, pagina a destra | fascia grigio chiaro a tre colonne |
| Contenitori | pieni grigio chiaro, bordo colorato in alto | solo il bordo (stampa in bianco e nero) | bordo colorato a sinistra |
| Carattere | Titillium | Inter | Titillium |
| In Typst | sì, tutto (griglie, riquadri arrotondati con `box(radius:)`, testatine con `page(header:)`, immagine) | sì, tutto | sì; il pannello scuro è un `rect` con `fill` sopra l'immagine (`place`) |
| In QTextDocument | riquadri sì (tabelle con sfondo, **senza angoli arrotondati**: `border-radius` non c'è), header e footer sì (QPainter come oggi), barre dei grafici come immagini; copertina sì con QPainter | come V1; i bordi a filo sì | copertina sì con QPainter; i riquadri con il bordo colorato a sinistra sì (`border-left` su `td`), angoli no |

Il limite di QTextDocument per questi disegni è uno: niente angoli arrotondati né `break-inside`; i grafici
arrotondati vanno disegnati come immagini (matplotlib con `FancyBboxPatch`, o QPainter). Tutto il resto si fa.

### Il rendering 3D: che cosa dà il programma oggi

Le immagini `foto/render-base-south_east.png` e `-south_west.png` sono **foto vere del programma, non ritoccate**:
`ui/report_3d.py` (la scena della relazione `ReportScene.qml`, `QQuickRenderControl` senza finestra, GPU vera) su un
progetto di prova simile ai bozzetti (capannone 120 × 40 m, file a 30°, palazzina uffici accanto; 693 moduli posati
dall'automatismo), 2200 × 1440 px, 2 viste in 0,85-1,0 s. Script: `prove/FR-render-3d.py` (nessuna finestra aperta,
nessun file di Daniel toccato).

Oggi la scena ha: camera assonometrica (ortografica), MSAA «VeryHigh», un sole con ombre morbide (PCF8, mappa
«VeryHigh») più tre luci di cielo, sfondo e terreno bianchi, edifici neutri con gli spigoli disegnati, moduli blu
navy. È un **disegno tecnico pulito**, non un rendering: niente prospettiva, niente cielo, materiali piatti, molto
bianco intorno. Provata l'**ambient occlusion** (`aoStrength` 70 e 100, `aoDistance` 5 e 400 su una copia del QML,
senza toccare il programma): immagine **identica al byte**, sia con distanza piccola sia grande; con la camera
ortografica a `clipNear -20000 / clipFar 20000` il buffer di profondità non lascia all'AO nulla da fare (dedotto;
non indagato oltre per il budget).

Per un rendering «figo» alla SolarEdge servirebbero, in ordine di resa per lavoro:
1. una **camera prospettica** per la copertina (la `PerspectiveCamera` c'è già nella vista della finestra, `Scene.qml`),
   da un punto di vista basso a 3/4: mezza giornata;
2. **cielo e terreno**: `SceneEnvironment` con `lightProbe` (HDRI libero, es. Poly Haven CC0, 1-2 MB) per riflessi e
   luce d'ambiente, un terreno con texture leggera o un gradiente: una giornata;
3. **materiali**: vetro dei moduli con `metalness`/`roughness` bassi e cornice in alluminio, pareti con una tinta,
   spigoli meno marcati: mezza giornata;
4. **post-produzione**: `ExtendedSceneEnvironment` (Qt Quick 3D Helpers) con tonemapping, bloom leggero, vignetta,
   depth of field; costa poco in codice ma va provato sulla GPU di Daniel e sul laptop: mezza giornata;
5. il ritaglio automatico del bianco intorno (già fatto per i bordi: `_on_white`), così l'immagine riempie la cornice.
Il tutto resta dentro Qt Quick 3D, senza dipendenze nuove, e si rende in meno di un secondo.

Limiti di questo studio: i bozzetti sono HTML, non l'uscita del programma; le pagine di impianto elettrico, verifiche
e metodi non sono disegnate (seguono le regole di A2/C2: tabelle con fonte, righe di gruppo); i caratteri di C arrivano
da Google Fonts nel browser (senza rete si vedono Georgia e Consolas). Edge non è più sul PC (resta solo la cartella
della versione): le foto sono fatte con Chrome headless, stessi argomenti.
