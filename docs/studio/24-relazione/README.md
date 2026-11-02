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

Limiti di questo studio: i bozzetti sono HTML, non l'uscita del programma; le pagine di impianto elettrico, verifiche
e metodi non sono disegnate (seguono le regole di A2/C2: tabelle con fonte, righe di gruppo); i caratteri di C arrivano
da Google Fonts nel browser (senza rete si vedono Georgia e Consolas). Edge non è più sul PC (resta solo la cartella
della versione): le foto sono fatte con Chrome headless, stessi argomenti.
