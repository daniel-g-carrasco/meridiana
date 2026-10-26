# Studio 20: iniziare un progetto, le mappe, clienti e commesse, Meridio

26/10/2026. R148, R149 con R131, R150 e R151 di `docs/richieste.md`.

**In breve.**

1. Il «Nuovo» deve portare subito sul posto: mappa e campo unico prima dei dati amministrativi, poi «Crea e disegna».
2. Mentre si scrive, i suggerimenti vengono da clienti, progetti ed elenchi locali; Nominatim resta solo su richiesta esplicita.
3. Il campo deve capire coordinate decimali, DMS, collegamenti e UTM con fuso dichiarato; il punto va sempre confermato sulla mappa.
4. La mappa stradale serve a trovare il sito, l'ortofoto a disegnare: non sono alternative, sono due passi dello stesso lavoro.
5. «Automatico» deve ripiegare su un'altra fonte con un avviso visibile; anno e risoluzione nativa restano accanto alla pianta.
6. La modalità mondo può essere offline con Natural Earth, confini e nomi degli stati; è per orientarsi, non per misurare.
7. Clienti e commesse stanno in un'anagrafica locale piccola, senza fatturazione, preventivi o un secondo gestionale.
8. Le cartelle attuali restano la fonte dei documenti; un manifesto collega codice, fase e progetti senza cambiare nomi o revisioni.
9. Meridio deve cercare e aprire con strumenti locali deterministici; il cloud non vede indice, percorsi né commesse riservate.
10. Prima conviene fare affidabilità delle mappe e inizio guidato, poi anagrafica, indice e strumenti di Meridio, infine le espansioni.


**Legenda.** **[V]** verificato nel codice, con una prova o su una fonte indicata. **[I]** deduzione, proposta o stima. I voti vanno da 1 a 10 e valutano l'utilità per Daniel, non la qualità generale del prodotto. Le giornate sono giornate di lavoro, prove comprese, non una data di consegna. **[I]**

**Esempi.** Tutti i clienti, le commesse, i progetti, gli indirizzi, i luoghi e i percorsi nei bozzetti e in questo documento sono inventati. Non descrivono lavori veri.

## 1. Il consiglio in una pagina

La raccomandazione è una sola architettura, non quattro funzioni isolate. **[I]**

1. **Una pagina «Nuovo progetto» centrata sul luogo.** Campo unico, suggerimenti locali e mappa con i posti possibili. Il committente, la commessa e la rete si completano nella stessa pagina o dopo, senza obbligare a compilare tutto. «Crea e disegna» crea il progetto, centra la pianta sul punto confermato e passa all'ortofoto.
2. **Un piccolo registro locale.** Clienti, commesse, attività e collegamenti ai `.meridiana`. Ogni commessa può avere un manifesto JSON nella cartella che Daniel già usa. Le fasi, le discipline, i nomi dei file e le revisioni non cambiano.
3. **Un indice locale derivato.** Contiene i dati necessari a cercare, non una seconda copia dei progetti. Lo ricostruisce dai file quando serve. Da esso vengono i suggerimenti del «Nuovo» e gli strumenti di Meridio.
4. **Fonti di mappa distinte per scopo.** Stradale per trovare, ortofoto per disegnare, mondo con stati per la vista globale. L'«Automatico» sceglie solo fra le ortofoto adatte al sito. Un eventuale passaggio a Sentinel-2 è dichiarato come basso dettaglio, mai presentato come foto per il disegno.
5. **Riservatezza prima del testo.** Se il progetto è riservato, niente indirizzo, nome dello stabilimento, coordinate, area della mappa o metadati della commessa vanno online. Il solo invio delle tessere rivela già una piccola zona. [V: il caricatore chiede le tessere dell'area inquadrata, `src/meridiana/ui/plan.py:2401-2415`; `config.py:243-247` distingue geocodifica, PVGIS e tessere]

La scelta non riapre le decisioni già prese: ambito nazionale con regole regionali come varianti, valori predefiniti utili senza obblighi iniziali, pagina File, Meridio locale come base e progetto riservato mai nel cloud. [V: `docs/progetto.md:27-46`; `assistant/privacy.py:1-12`]

## 2. Metodo e limiti delle verifiche

Ho letto `CLAUDE.md`, `docs/progetto.md`, il sistema grafico, gli studi 14 e 18 F, il registro R131 e i moduli indicati nell'incarico. Ho riletto il 26/10/2026 le regole ufficiali di Nominatim e delle tessere OSM, la documentazione di Photon, le condizioni ISTAT e Natural Earth e le pagine ufficiali di Aurora, OpenSolar e PVsyst citate in fondo. **[V]**

Non ho scaricato archivi cartografici né serie di tessere. Il guasto intermittente del PCN del 25/10 resta quindi un fatto verificato nell'analisi di quel giorno, non una nuova misura di oggi. **[V: `docs/richieste.md`, R131; `docs/compiti/21-mappe.md`]**

I tre bozzetti sono PNG a 1600 × 960, disegnati offscreen con Inter e i gettoni reali di Meridiana. Lo script `genera_bozzetti.py` li rifà. Sono proposte di interazione, non schermate del programma già funzionante. **[V: esecuzione dello script e lettura dei tre PNG]**

## 3. R148: iniziare dal posto

### 3.1 Che cosa c'è oggi

- «Trova il sito» è un dialogo modale con indirizzo, elenco dei risultati e due campi numerici. Non contiene una mappa. **[V: `src/meridiana/ui/site_dialog.py:16-55`]**
- La ricerca parte dal pulsante o da Invio, non durante la scrittura. Usa Nominatim, otto risultati, solo Italia e al massimo una richiesta al secondo. **[V: `site_dialog.py:48-79`; `services/geocoding.py:12-26,49-60`]**
- Il parser legge latitudine e longitudine decimali con punto, virgola italiana, virgola come separatore, punto e virgola o spazio. Non legge DMS, gradi e primi decimali, Plus Code, collegamenti o UTM. **[V: `geo.py:225-244`; casi provati in `tests/nucleo/test_geo.py:81-88`]**
- Le conversioni UTM esistono già per WGS84 e per i sistemi ETRS89, RDN2008 e IGM95 riconosciuti in `utm_of_crs`. Sono usate per IFC, non dal dialogo del sito. **[V: `geo.py:111-192`; `tests/nucleo/test_ifc_export.py:24-43`]**
- `model.Site` contiene solo latitudine, longitudine e indirizzo. `Project` ha nome, report con un cliente testuale, regole di connessione e il segno `reserved`; non ha un'anagrafica clienti né un id di commessa. **[V: `model.py:398-401,843-876`]**
- La pagina File apre, salva, importa, esporta e mostra i recenti. «Nuovo» è un comando immediato, non una pagina di composizione. **[V: `ui/file_page.py:226-260,350-386`]**
- I modelli di oggi sono forme di edifici, non modelli di progetto con committente e rete. **[V: `templates.py:14-86`; `ui/template_dialog.py`]**
- I recenti sono percorsi nelle impostazioni. Vengono filtrati solo se il file esiste; non sono raggruppati per commessa o revisione. **[V: `config.py:238`; `ui/file_page.py:350-382`]**

### 3.2 Che cosa fanno gli altri

- **Aurora** crea il progetto da un indirizzo supportato da Google Maps, chiede di verificare il segnaposto sull'edificio e poi mostra contatti, consumi e alternative di progetto. Accetta anche coordinate decimali e Plus Code. **[V: [Aurora, nuovo progetto](https://help.aurorasolar.com/hc/en-us/articles/12290229701523-Creating-a-New-Project), [Aurora, coordinate e Plus Code](https://help.aurorasolar.com/hc/en-us/articles/360057561913-How-to-Use-GPS-Coordinates-or-Plus-Codes-as-Your-Address-in-Aurora)]**
- **OpenSolar** inizia dall'indirizzo del cliente scelto in un elenco; il progetto riunisce poi contatto, stato, dati del distributore, disegno e documenti. **[V: [OpenSolar, flusso dell'applicazione](https://support.opensolar.com/hc/en-us/articles/13211447430799-Application-Flow)]**
- **PVsyst** lega latitudine e longitudine al sito e ai dati meteo. La sua documentazione distingue il sito geografico dai dati e conserva un insieme meteo mensile di riserva. **[V: [PVsyst, sito del progetto](https://www.pvsyst.com/help/project-design/project-definition/project-site.html)]**

Il principio riutilizzabile è il controllo visivo del segnaposto prima della creazione. Non serve copiare la dipendenza da un unico fornitore di mappe. **[I]**

### 3.3 Il percorso proposto, da «Nuovo» al disegno

1. **File > Nuovo apre una pagina, non una sequenza di finestre.** A sinistra il campo unico e i dati essenziali, a destra una mappa. Il nome può essere proposto da codice e stabilimento, ma resta modificabile. **[I]**
2. **Mentre si scrive partono solo ricerche locali.** Dopo due caratteri, senza attese sulla finestra: stabilimenti dei progetti noti, clienti e commesse, comuni e località inclusi nel programma. Ogni riga dichiara la provenienza. **[I]**
3. **I risultati diventano segni numerati sulla mappa.** La selezione nella lista e sulla mappa è la stessa. Un clic sposta il candidato, non crea ancora il progetto. Il testo libero non viene sostituito a sorpresa. **[I]**
4. **«Cerca online» è un gesto separato.** Mostra prima chi riceve il testo. Il servizio predefinito può essere Nominatim per una ricerca singola; Photon è un'alternativa configurabile per chi accetta le condizioni del suo server. **[I]**
5. **Coordinate o collegamento incollato sono riconosciuti nel campo.** Il programma mostra che cosa ha capito, il datum e la zona UTM prima di accettare. Un testo ambiguo non viene trasformato in un punto a caso. **[I]**
6. **Il punto va confermato sul tetto o sul terreno.** Si può trascinare il segno o cliccare la mappa. Il programma conserva indirizzo scritto e punto scelto come dati distinti: il geocodificatore non è un rilievo. **[I]**
7. **Committente, commessa e rete sono facoltativi in quel momento.** Si possono scegliere da anagrafica o creare. Il progetto riservato si marca prima di qualunque richiesta online. **[I]**
8. **«Crea e disegna» salva il punto e apre la fase Modello.** La pianta inquadra il sito e seleziona l'ortofoto migliore disponibile. Se non c'è una foto adatta, dice la risoluzione e offre stradale, immagine importata o disegno senza sfondo. Il modello di edificio resta un comando successivo. **[I]**

Il bozzetto è `bozzetti/01-nuovo-progetto.png`. Le tre linguette in alto sono una spiegazione del percorso, non l'invito a creare un wizard con pagine obbligatorie. **[I]**

### 3.4 Suggerimenti: regole e alternative

La policy del Nominatim pubblico vieta espressamente «Auto-complete search», anche se fosse il client a chiamarlo a ogni tasto. Chiede inoltre massimo una richiesta al secondo, identificazione, attribuzione e nessun dato personale o confidenziale. **[V: [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)]**

| Alternativa | Pro | Contro | Voto |
|---|---|---|---|
| **A. Indice locale + elenchi ISTAT durante la scrittura; ricerca online solo su pulsante** | Immediata, funziona offline, riusa i lavori di Daniel, nessun dato esce mentre scrive, compatibile con Nominatim | Non conosce ogni indirizzo o stabilimento nuovo; gli elenchi vanno aggiornati | **9** |
| **B. Photon pubblico durante la scrittura** | Progettato per search-as-you-type, tolleranza agli errori, restituisce GeoJSON | Il server dimostrativo non garantisce disponibilità, limita l'uso estensivo; ogni tasto può contenere dati riservati; OSM non copre tutto | **6** |
| **C. Nominatim pubblico durante la scrittura** | Già integrato per la ricerca singola | Vietato dalla policy per l'autocompletamento | **1** |
| **D. Geocodificatore commerciale con chiave** | Buoni servizi e condizioni professionali possibili | Chiave, costi, quota, privacy e termini da verificare per ciascun fornitore; non risolve l'offline | **6**, solo opzionale |
| **E. Photon o Nominatim in locale** | Controllo e ricerca locale completa | Java, banca dati, aggiornamenti e manutenzione; il solo database mondiale di Photon richiede circa 95 GB nel 2026 | **3** |

Fatti sulle alternative: Photon è Apache-2.0, supporta search-as-you-type e usa dati OSM. Il suo server pubblico ammette solo traffico ragionevole, può limitare o bloccare e non promette disponibilità. **[V: [Photon, repository e condizioni del demo](https://github.com/komoot/photon)]**

L'elenco ufficiale dei comuni ISTAT è distribuito con un permalink aggiornato; al 21/02/2026 conta 7.894 comuni. I contenuti ISTAT sono CC BY 4.0 salvo diversa indicazione e richiedono attribuzione e indicazione delle modifiche. **[V: [ISTAT, codici delle unità amministrative](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/), [ISTAT, note legali](https://www.istat.it/it/note-legali)]**

**Raccomandazione A.** Il pacchetto locale iniziale contiene comuni e, dove disponibili con coordinate verificate, frazioni e località. La versione e la data ISTAT compaiono nell'attribuzione. I nomi degli stabilimenti non si scaricano in blocco: arrivano dai progetti dell'utente o dalla ricerca online esplicita. **[I]**

### 3.5 Coordinate: che cosa accettare

| Forma | Esempio inventato | Regola proposta | Priorità [I] |
|---|---|---|---|
| Decimali | `45,5226; 9,0300` | Come oggi, latitudine prima; mostrare anche il formato normalizzato | Subito |
| Gradi, primi, secondi | `45°31'21,4"N 9°01'48,0"E` | Simboli e lettere di emisfero, minuti e secondi minori di 60; rifiutare ambiguità | Subito |
| Gradi e primi decimali | `45°31,357'N 9°1,800'E` | Stesse regole dei DMS | Seconda |
| Collegamento di una mappa | URL con `query=lat,lon` o parametri equivalenti | Leggere solo coordinate esplicite, mai aprire il collegamento né geocodificare il suo testo | Subito per formati provati |
| Plus Code | codice completo più località quando serve | Decodifica locale; nessuna chiamata Google | Seconda |
| UTM | `32T 500000 5040000` | Zona, emisfero, Est, Nord e datum espliciti; usare `geo.from_utm`, non indovinare | Subito per WGS84/ETRS89 |
| Foglio e particella | foglio, particella, comune catastale | Non sono coordinate: interrogare il catasto come servizio separato e mostrare l'area, non il solo centroide | Solo idea futura |

Il parser deve restituire punto, formato riconosciuto, sistema di riferimento e avvertenze. Gauss-Boaga ed ED50 non vanno fatti passare per WGS84: richiedono una trasformazione di datum esplicita e una dipendenza o implementazione verificata. **[I]**

### 3.6 I dati di rete: utili, non un modulo fiscale

| Dato | A che cosa serve in Meridiana | Obbligo all'inizio [I] |
|---|---|---|
| Distributore | Informazione della pratica, relazione, ricerca fra commesse; non sceglie da solo una norma | No |
| POD | Collega curva dei consumi e bollette; identificativo da non mostrare per intero negli elenchi | No |
| Connessione BT/MT/AT | Alimenta i dati di connessione già presenti in `Project.rules` | No, ma editabile subito |
| Potenza disponibile o impegnata | Dato della fornitura e confronto con i consumi; può contribuire alle regole già previste | No |
| Potenza richiesta per il nuovo impianto | Scenario di connessione e relazione; distinta dalla potenza disponibile attuale | No |
| Tensione e fasi della fornitura | Contesto elettrico e futuri schemi; non da dedurre automaticamente dalla potenza | No |
| Connessione esistente/nuova/modifica | Distingue il lavoro sulla fornitura senza presumere l'esito della pratica | No |

Questa separazione evita due errori: chiedere dati prima che Daniel li abbia e far credere che il distributore o il POD cambino il calcolo fisico del sole. I campi che oggi alimentano regole vanno riusati, non duplicati in una struttura parallela. **[I; struttura attuale verificata in `model.py:856-859`]**

### 3.7 Privacy del luogo

- **Progetto riservato:** solo indice locale, clic sulla mappa offline, coordinate, immagini importate e modello locale. Niente Nominatim, Photon, PVGIS o tessere online. **[I]**
- **Progetto non riservato, ricerca online consentita:** il testo dell'indirizzo va al geocodificatore scelto; le coordinate vanno a PVGIS solo quando richiesto; l'area inquadrata va al fornitore delle tessere. Sono tre destinatari e tre consensi distinti, come già nelle impostazioni. **[V: `config.py:243-247`; conseguenza d'uso [I]]**
- **Il nome del committente non serve a trovare il sito.** Non va aggiunto alla query online se l'utente ha scritto solo lo stabilimento. **[I]**
- **Un progetto può diventare riservato dopo.** Da quel momento l'indice cloud consentito viene escluso; cache e conversazioni già create non vanno presentate come cancellate dal server remoto. **[I]**

### 3.8 Alternative di interfaccia, lavoro e rischi

| Forma | Pro | Contro | Voto |
|---|---|---|---|
| Pagina unica con mappa, dati facoltativi e conferma | Il posto resta sempre visibile; pochi passaggi; adatta alla pagina File | Richiede un nuovo pannello e una mappa di anteprima | **9** |
| Wizard in tre pagine obbligatorie | Ordine chiaro per chi inizia | Ripete il blocco iniziale già evitato per decisione di Daniel; nasconde la mappa nei passi successivi | **5** |
| Dialogo attuale ampliato | Meno lavoro | Poco spazio, separa il sito dalla creazione e non integra clienti/commesse | **4** |
| Nuovo solo da anagrafica | Ottimo per lavori ripetuti | Scomodo per un sito nuovo e per il primo utilizzo | **6**, come scorciatoia aggiuntiva |

**Stima della raccomandazione R148:** 12-18 giorni. Comprende parser e prove, pagina Nuovo, anteprima, suggerimenti locali, ricerca esplicita, dati di rete, migrazione del formato e viaggio completo fino al disegno. Un eventuale indice ISTAT delle località coordinate può aggiungere 2-4 giorni secondo la qualità della fonte. **[I]**

**Rischi principali:** punto giusto per un indirizzo ma sbagliato sul tetto; conversione UTM con datum tacito; query online involontaria; elenco locale troppo vecchio; dati di rete duplicati. Le barriere sono conferma visiva, datum esplicito, consenso prima della richiesta, data dell'elenco e un'unica fonte dei campi. **[I]**

## 4. R149 e R131: mappe che non lasciano buchi muti

### 4.1 Che cosa c'è oggi

- `tiles.py` ha fonti XYZ, WMTS e WMS, copertura, licenza, anno o descrizione, zoom e classifica. L'«Automatico» sceglie la foto migliore che copre il sito; Sentinel-2 2016 garantisce un risultato mondiale. **[V: `tiles.py:81-107,255-437,593-620`]**
- Il catalogo contiene ortofoto nazionali e regionali, OpenStreetMap, OpenTopoMap e Sentinel-2. Le fonti personalizzate possono richiedere una chiave conservata nel portachiavi. **[V: stesso file; `ui/map_sources.py:93-167,262-290`]**
- Sentinel-2 è limitato a z14 e dichiarato a 10 m. Il limite è nella natura del dato, non un semplice limite di disegno. **[V: `tiles.py:418-422`; R131]**
- Il caricatore fa sei richieste alla volta, due tentativi dopo il primo, conserva la cache e segnala `tileFailed`. La pianta collega solo `tileReady`; non cambia fonte quando arriva il fallimento. **[V: `ui/tileloader.py:26-30,132-155`; `ui/plan.py:251-258,2421-2428`]**
- La pianta conserva per un po' tessere di altri zoom e mostra sempre l'attribuzione della fonte scelta. **[V: `ui/plan.py:317-321,2416-2419`]**
- Le Preferenze permettono sorgenti proprie e spiegano che «Automatico» ripiega su Sentinel-2 a 10 m, non la risoluzione effettiva sullo schermo accanto alla pianta. **[V: `ui/map_sources.py:59-89`]**

### 4.2 Che cosa fanno gli altri

- PVsyst 8 scarica l'immagine di terreno da Bing Maps o Azure Maps, permette di alternare «Satellite» e «Map» e importa l'immagine alla scala della vista. **[V: [PVsyst, immagine e topografia](https://www.pvsyst.com/help/project-design/shadings/near-shadings-import/ground-image-and-topography/ground-image-and-topography-import.html)]**
- Aurora chiede di verificare il segnaposto sulla vista satellitare prima di creare e offre sorgenti di immagini nei suoi servizi. **[V: pagine Aurora già citate]**
- Le regole delle tessere OSM richiedono attribuzione visibile, User-Agent proprio, rispetto della cache e vietano prelievo anticipato e archivi offline dal server standard. Non promettono disponibilità. **[V: [OSM Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)]**

### 4.3 Due predefiniti, non uno

| Momento | Predefinito raccomandato | Perché [I] |
|---|---|---|
| Cercare e riconoscere il posto | **Stradale OSM**, con nomi e vie | Un indirizzo e i riferimenti si riconoscono prima sulle strade; l'attribuzione resta sempre visibile |
| Disegnare | **Ortofoto automatica migliore**, con anno e risoluzione | Tetti, ostacoli e sagome si vedono sulla foto |
| Guardare il mondo | **Mappa mondiale con stati**, Natural Earth offline | Confini e nomi senza rete e senza fingere dettaglio locale |
| Nessuna foto adeguata | Stradale oppure nessuno, scelta esplicita | Sentinel-2 non deve apparire come se fosse sufficiente per posare moduli su un tetto |

«Automatico» rimane la scelta iniziale per il disegno. Il selettore nella pagina Nuovo parte invece da «Stradale». La transizione a «Ortofoto» dopo «Crea e disegna» è un cambio di scopo, non una preferenza contraddittoria. **[I]**

### 4.4 Ripiego visibile

1. Tenere le tessere valide già presenti, anche di uno zoom vicino, mentre le nuove falliscono. Non cancellare ciò che si vede. **[I]**
2. Distinguere errore singolo e fonte indisponibile. Dopo una soglia misurata sulla vista, per esempio tre tessere fallite dopo i tentativi, proporre e poi attuare il ripiego automatico. La soglia va provata, non è una costante già validata. **[I]**
3. Scegliere la fonte successiva per stesso scopo e copertura. Se la seconda ha altra data o risoluzione, dirlo. Non mescolare silenziosamente foto diverse nello stesso mosaico. **[I]**
4. Mostrare una striscia: «Ortofoto PCN non raggiungibile. Sto usando Ortofoto regionale 2023, 0,2 m/pixel». Comandi «Riprova» e «Scegli sfondo». **[I]**
5. In assenza di un'altra foto, usare lo stradale con avviso «Sfondo per orientarsi, non per misurare». Se rimane solo Sentinel-2, mostrare «10 m, dettaglio insufficiente per il disegno di un tetto». **[I]**
6. Ricordare per poco gli esiti negativi, senza ripetere richieste a ogni pan. Non trasformare un guasto temporaneo in una scelta permanente nelle preferenze. **[I]**

### 4.5 Dire la risoluzione senza confondere i numeri

Servono tre dati distinti. **[I]**

- **Risoluzione nativa dichiarata:** per esempio 0,5 m/pixel PCN o 10 m Sentinel-2. Va aggiunta ai metadati della fonte quando la fonte ufficiale la conferma.
- **Risoluzione della tessera allo zoom e latitudine attuali:** si calcola dalla formula Web Mercator già in `zoom_for`. È la densità del campionamento, non la precisione del rilievo. **[V: `tiles.py:43,625-630`; interpretazione [I]]**
- **Metri per pixel dello schermo:** dipende dallo zoom della pianta e dal rapporto pixel dello schermo. Ingrandire oltre il dato non aggiunge dettaglio. **[V: `ui/plan.py:2408-2410`; interpretazione [I]]**

La riga sintetica può dire «Ortofoto 2012 · dato 0,5 m/pixel · z18 · non è un rilievo». Anno e attribuzione vengono dalla fonte; quando l'anno non è noto, non va inventato. **[I]**

### 4.6 Il mondo con gli stati

Natural Earth offre dati vettoriali e raster in pubblico dominio, utilizzabili, modificabili e distribuiti anche commercialmente senza obbligo di attribuzione. **[V: [Natural Earth, Terms of Use](https://www.naturalearthdata.com/about/terms-of-use/)]**

| Alternativa | Pro | Contro | Voto |
|---|---|---|---|
| **Natural Earth 1:10m incluso, disegnato da Meridiana** | Offline, piccolo rispetto a un atlante di tessere, confini e nomi sotto controllo, stesso stile grafico | Scala adatta solo al mondo e ai continenti; toponomastica e confini contesi richiede cura | **9** |
| OSM a zoom basso online | Nomi e strade coerenti con la mappa locale | Richiede rete; niente uso offline pre-scaricato dal server standard; troppi dettagli inutili per un primo mondo | **7** |
| Sentinel-2 mondiale | Immagine fisica del pianeta, già nel catalogo | 10 m e nessun confine di stato; non risponde alla richiesta | **4** |
| Atlante mondiale commerciale | Buona qualità e servizio | Chiave, costi e condizioni; sproporzionato per questa vista | **5** |

**Raccomandazione:** paesi riempiti in modo sobrio, bordi, nomi, oceani e graticola. Un clic su uno stato inquadra il suo riquadro; poi OSM prende il posto quando si scende verso una nazione. Natural Earth resta una base cartografica semplificata, non una fonte per confini tecnici o misure. **[I]**

### 4.7 Fonti commerciali e riservatezza

Le fonti con chiave restano possibili come sorgenti personali, non come predefinito obbligatorio. Le condizioni di Esri, Google, Mapbox e altri non vanno generalizzate: conservazione, attribuzione, uso in altri programmi e stampa cambiano. Il catalogo attuale ha già il meccanismo per chiave e licenza. **[V: `tiles.py:10-16`; `ui/map_sources.py:129-164`; conseguenza [I]]**

Per un progetto riservato la modalità mondo offline è sempre disponibile. La cache già presente può essere letta solo nei limiti delle condizioni della fonte; non si aggiunge un «scarica zona per dopo» sul server OSM standard. **[I, sulla policy OSM verificata sopra]**

### 4.8 Alternative, lavoro e rischi

| Strategia | Pro | Contro | Voto |
|---|---|---|---|
| Due predefiniti + ripiego tra fonti + Natural Earth | Risponde a ricerca, disegno, guasti e mondo | Coordinamento fra stati della pianta e metadati | **9** |
| Solo Sentinel-2 mondiale sempre disponibile | Copertura semplice e uniforme | Non risolve R131 né il disegno su tetto | **2** |
| Una sola fonte commerciale molto dettagliata | Esperienza uniforme dove coperta | Chiave e termini per tutti, privacy, niente offline | **5** |
| Mosaico automatico per singola tessera | Massima probabilità di coprire lo schermo | Anni e risoluzioni diversi nello stesso tetto, rischio di lettura sbagliata | **3** |

**Stima:** 7-11 giorni per ripiego, stati visibili, metadati e prove; 3-5 giorni per il mondo Natural Earth; 1-2 giorni per integrare la scelta stradale nella pagina Nuovo. **[I]**

**Rischi:** fonte dichiarata migliore ma più vecchia; failover oscillante; cache oltre le condizioni; «m/pixel» scambiato per accuratezza; confini piccoli o contesi; foto non riutilizzabile nel PDF. Servono priorità spiegata, stato stabile per vista, rispetto delle licenze e dicitura «non è un rilievo». **[I]**

## 5. R150: clienti e commesse senza un secondo gestionale

### 5.1 Che cosa c'è oggi e che cosa fanno gli altri

Meridiana ha un cliente libero nei dati della relazione, i recenti e le revisioni `_Rnn`, ma nessuna entità cliente o commessa e nessun registro di attività. **[V: `model.py:867-870`; `ui/file_page.py:289-304,350-386`; `recovery.py`]**

OpenSolar mostra progetti recenti, attività future, stato, priorità, contatto, persona assegnata, documenti e azioni del flusso. Offre filtri e viste personalizzate. **[V: [OpenSolar, flusso dell'applicazione](https://support.opensolar.com/hc/en-us/articles/13211447430799-Application-Flow)]**

Per Daniel il nucleo utile è più piccolo: trovare il lavoro, sapere che cosa resta da fare e aprire la cartella o il progetto giusto. Fatture, vendite, campagne e permessi del team non servono in questa funzione. **[I]**

### 5.2 Il modello minimo

**Cliente:** id stabile, nome, tipo (impresa generale, sviluppatore, architettura, privato, altro), contatti facoltativi, dati per elaborati solo quando servono, note locali. Un cliente non viene cancellato se ha commesse: si archivia. **[I]**

**Commessa:** id stabile, codice di cinque cifre, nome breve, cliente, stato, fase, cartella, scadenze, attività, riservatezza, progetti collegati. Il codice viene mostrato come stringa, non come numero, così conserva eventuali zeri e non lo usa per calcoli. **[I]**

**Stati:** in attesa, in corso, consegnata, archiviata. **Fasi:** preliminare, definitivo, esecutivo, costruttivo. Stato e fase non sono sinonimi: una commessa consegnata può richiedere una revisione successiva. **[I]**

**Progetto collegato:** id stabile della serie, percorso attuale, titolo, commessa, data, ultima revisione nota. Le revisioni restano file distinti nella stessa serie. Il nome del file può cambiare; l'id no. **[I]**

**Attività:** testo, scadenza facoltativa, stato, commessa e progetto facoltativi. Niente commenti social o notifiche cloud. Una scadenza di consegna è un campo della commessa; le attività sono i passi personali. **[I]**

### 5.3 Dove stanno i dati

| Alternativa | Pro | Contro | Voto |
|---|---|---|---|
| **JSON locale versionato + manifesto JSON per commessa + indice derivato** | Leggibile, esportabile, coerente con scrittura atomica e `.bak`, niente servizio; il manifesto viaggia con la cartella | Va riscritto intero; conflitti se due PC modificano lo stesso manifesto | **9** |
| SQLite locale + manifesti | Query, transazioni e molti record senza riscrivere tutto | Formato meno leggibile; migrazioni e backup da gestire; ricerca semplice non lo richiede | **7** |
| Solo database sul server dello studio | Un solo registro condiviso | Non funziona offline o in proprio; server da amministrare; privacy e permessi | **4** |
| Solo dentro ogni `.meridiana` | Nessun altro file da salvare | Non trova clienti senza aprire tutto, attività senza progetto e cartelle senza Meridiana | **5** |

**Raccomandazione:** il registro principale resta nel profilo locale di Meridiana. Nella cartella della commessa, se Daniel lo permette, `.meridiana-commessa.json` ripete solo id, codice, nome, fase e collegamenti utili alla portabilità. Il documento è la fonte dei suoi dati; il registro è la fonte dei metadati amministrativi; l'indice è ricostruibile e non è mai la fonte. **[I]**

Le commesse riservate non hanno manifesto condiviso per impostazione predefinita. Se la cartella è già protetta e Daniel sceglie il manifesto, questa è una decisione esplicita, non un effetto collaterale dell'indicizzazione. **[I]**

### 5.4 Integrazione con le cartelle esistenti

1. «Collega cartella» sceglie una cartella già esistente e non sposta nulla. **[I]**
2. «Nuova commessa» propone codice e nome, ma non crea una gerarchia rigida senza conferma. La struttura per fase e disciplina già presente resta intatta. **[I]**
3. Il salvataggio propone la sottocartella coerente solo come convenzione configurabile. Non rinomina automaticamente i file né cambia i suffissi `_R01`, `_R02`. **[I]**
4. L'indicizzazione guarda solo le cartelle collegate, non tutto il disco e non altre cartelle personali. **[I]**
5. Se il server è spento, il registro locale mostra i dati noti e «cartella non raggiungibile». Non inventa progetti aggiornati. **[I]**
6. Alla riapertura, un conflitto fra manifesto e registro viene mostrato con data e valori. Non vince automaticamente l'ultimo file scritto. **[I]**

### 5.5 Importazione ed esportazione

- **JSON completo versionato:** clienti, commesse, attività, collegamenti e metadati. Anteprima, scelta fra unione e sostituzione, corrispondenza per id, riepilogo dei duplicati. **[I]**
- **CSV:** clienti, commesse e attività per foglio di calcolo. Il CSV è una vista, non conserva tutta la struttura; la reimportazione richiede intestazioni riconosciute e anteprima. **[I]**
- **Manifesti:** importazione di una singola commessa dalla sua cartella, senza importare automaticamente tutti i documenti. **[I]**
- **Esportazione riservata:** avviso prima di scrivere dati sensibili in un file non cifrato. Niente percorsi o dati riservati negli esempi pubblici e nei registri diagnostici. **[I]**

Il bozzetto `bozzetti/02-clienti-commesse.png` usa tre colonne: clienti, commesse, dettaglio. La ricerca unica attraversa codice, nome, cliente e progetto. **[I]**

### 5.6 Alternative di interfaccia, lavoro e rischi

| Forma | Pro | Contro | Voto |
|---|---|---|---|
| Registro nella pagina File con tre colonne | Integrato, tutto raggiungibile da ricerca, non invade il disegno | Vista meno adatta a centinaia di colonne, che però non servono | **9** |
| Piccole finestre separate per cliente e commessa | Più facili da aggiungere | Navigazione frammentata, contraria alla direzione della pagina File | **5** |
| CRM completo | Coprirebbe vendita, team e documenti | Molto lavoro, duplica altri strumenti, privacy maggiore | **2** |
| Solo elenco recenti migliorato | Minimo costo | Non gestisce clienti, stati, scadenze e cartelle | **4** |

**Stima:** 12-17 giorni per modello, registro locale, manifesti, pagina, attività, import/export e prove. L'indicizzazione iniziale delle cartelle collegate aggiunge 3-5 giorni ed è condivisa con Meridio. **[I]**

**Rischi:** due PC che cambiano lo stesso manifesto; collegamento al file sbagliato dopo uno spostamento; cancellazione di un cliente storico; codice commessa trattato come numero; dati personali esportati senza accorgersene. Le barriere sono id, conflitti visibili, archiviazione, stringhe, anteprime e permessi espliciti. **[I]**

## 6. R151: Meridio trova e apre, il modello aiuta dopo

### 6.1 Che cosa c'è oggi

- Meridio legge verifiche, progetto, selezione, risultati, calcoli e regole; va a un oggetto o a una fase e propone modifiche. Non ha strumenti per cercare fra file, elencare commesse, ricordare attività o aprire un altro progetto. **[V: `assistant/tools.py:53-138,823-826`]**
- Gli strumenti leggono sul thread della finestra; i fornitori lavorano su un thread separato. Il ciclo e i fornitori locali e Claude esistono già. **[V: `assistant/tools.py:12-24`; `assistant/providers.py:1-24`]**
- Il progetto riservato non può andare nel cloud. Per gli altri, nome, indirizzo e nome file vengono sostituiti e le coordinate arrotondate a circa 1 km. Il file intero non viene inviato. **[V: `assistant/privacy.py:1-12,107-127`; `tools.py:278-313`]**
- La pagina File sa aprire un percorso recente. Il comportamento di salvataggio del lavoro in mano appartiene al comando di apertura esistente, non a Meridio. **[V: `ui/file_page.py:384-386`]**

### 6.2 Confronto con altri programmi

OpenSolar offre recenti, attività, ricerca e filtri su stato, priorità e altri attributi. Questo verifica l'utilità di una base operativa, non una ricerca semantica fra progetti simili. **[V: fonte OpenSolar già citata]**

Non ho verificato in PVsyst, Aurora o OpenSolar una funzione che risponda a «trovami l'ultimo capannone simile» confrontando tipo, potenza, luogo e revisioni. Non la attribuisco quindi a quei programmi. **[V: limite della ricerca documentale di questo studio]**

### 6.3 Prima gli strumenti, poi il linguaggio

La richiesta «apri 26042» non richiede un modello linguistico. Nemmeno «che cosa devo fare questa settimana» o «mostra l'ultima revisione della serie». Devono funzionare anche senza modello, come comandi e filtri della stessa pagina. **[I]**

Strumenti proposti. **[I]**

| Strumento | Risultato deterministico | Azione consentita |
|---|---|---|
| `search_projects` | Righe dall'indice per testo, codice, cliente, tipo, potenza, distanza, data | Nessuna |
| `list_tasks` | Attività e scadenze, con filtri | Nessuna |
| `project_revisions` | Serie e revisioni ordinate, ultima valida | Nessuna |
| `similar_projects` | Punteggio spiegato e componenti della somiglianza | Nessuna |
| `prepare_open_project` | Percorso, titolo, commessa e stato del lavoro in mano | Prepara una scheda di conferma |
| `prepare_task` | Bozza di attività o modifica | Il progettista conferma |

Meridio non apre direttamente un file dopo una frase ambigua. La risposta mostra prima il percorso e la revisione. Il clic «Apri» passa dal normale flusso che chiede che cosa fare del lavoro non salvato. **[I]**

### 6.4 L'indice locale

L'indice contiene per ogni file: id di serie, percorso, nome, commessa e cliente se consentiti, coordinate, data del file e data interna, tipo prevalente (copertura, terreno, misto), potenza dei moduli posati, numero edifici e sottocampi, montaggi, inclinazioni, revisione e riservatezza. Non contiene il contenuto completo del progetto. **[I]**

È aggiornato in un lavoro in secondo piano dopo apertura, salvataggio, importazione e scansione richiesta. Un file illeggibile resta segnato con il motivo e non sparisce in silenzio. Dimensione, data e un'impronta del contenuto evitano di rileggere file invariati. L'indice si cancella e si ricostruisce. **[I]**

La «serie» non dipende solo dal suffisso: serve un id salvato nel progetto. Per i file esistenti senza id, la proposta di raggruppamento usa cartella, nome senza `_Rnn` e contenuto, ma mostra i casi dubbi. **[I]**

### 6.5 Che cosa significa «ultimo capannone simile»

Prima si filtra per compatibilità, poi si ordina per data. Non vince un progetto recentissimo ma diverso. **[I]**

Una prima regola semplice e spiegabile. **[I]**

1. Stesso tipo prevalente: copertura, non un campo a terra.
2. Potenza entro una fascia scelta, per esempio da metà al doppio, modificabile.
3. Somiglianza del montaggio e delle falde, poi vicinanza geografica.
4. Cliente solo se richiesto, non come filtro nascosto.
5. Fra i risultati, ultima revisione valida della serie più recente.

La risposta mostra perché: «copertura, 96 kWp contro 100, 12 km, stessa falda, revisione R04 del 22/10». Il punteggio è un aiuto alla ricerca, non una valutazione tecnica della bontà del progetto. Non serve un embedding vettoriale per iniziare. **[I]**

| Alternativa di ricerca | Pro | Contro | Voto |
|---|---|---|---|
| **Filtri strutturati + punteggio spiegabile** | Locale, verificabile, rapido, nessun modello da scaricare | Sinonimi e descrizioni libere meno flessibili | **9** |
| Testo libero + indice lessicale | Trova nomi, note e commesse | Non capisce da solo «simile» | **8**, da combinare |
| Embedding locali | Ricerca concettuale su note e descrizioni | Modello, memoria, indicizzazione, risultati meno spiegabili | **5**, dopo |
| Cloud su tutto l'archivio | Buon linguaggio e sintesi | Privacy, costo, trasferimento e necessità di redazione complessa | **2** |

Il bozzetto è `bozzetti/03-meridio-capannone-simile.png`. I dati mostrati sono inventati. **[I]**

### 6.6 Che cosa vede il modello

| Contenuto | Modello locale | Cloud, progetto non riservato e consenso | Cloud, progetto riservato |
|---|---|---|---|
| Domanda e riepilogo del progetto in mano | Sì | Sì, con la redazione già esistente | Mai |
| Risultati della ricerca non riservata | Sì | Solo le righe strettamente necessarie e dopo filtro locale | Solo se il progetto riservato resta fuori dal cloud |
| Nomi e percorsi completi | Sì | No: segnaposto e alias locali, mai il percorso | Mai |
| Clienti, commesse e attività non riservate | Sì | Solo se pertinenti alla domanda e redatte | Mai se il contesto è riservato |
| Progetti o commesse riservate | Sì | Mai, nemmeno l'esistenza o il conteggio | Mai |
| File `.meridiana` completo | Solo se uno strumento locale lo richiede davvero | No, come già dichiarato | Mai |

La regola importante è che il cloud non riceve l'indice per decidere da solo che cosa è privato. Il programma filtra prima. Una query come «cerca anche nei riservati» forza il modello locale; non viene redatta e inviata. **[I]**

La redazione attuale è una base, non basta da sola per un archivio: conosce il progetto in mano e campi aggiuntivi, ma non un intero elenco di clienti e percorsi. Servono alias per risultato e ripristino locale dei nomi solo nella risposta mostrata. **[V: `assistant/privacy.py:37-94`; conseguenza [I]]**

### 6.7 Ricordare che cosa c'è da fare

La memoria utile è strutturata: attività, scadenze, stato e collegamento al progetto. Meridio le legge e propone un ordine, ma non le completa da solo. All'apertura di una commessa può dire «mancano curva POD e verifica rete», perché viene dai dati, non da una presunta memoria del modello. **[I]**

Le note libere restano locali. Il cloud riceve solo il testo necessario alla domanda e solo per contenuti non riservati. Nessuna sincronizzazione automatica con un servizio esterno. **[I]**

### 6.8 Alternative, lavoro e rischi

| Forma | Pro | Contro | Voto |
|---|---|---|---|
| Strumenti deterministici su indice + modello per la frase | Affidabile anche offline, privacy chiara, poco lavoro sul modello | Serve progettare bene gli strumenti e le schede | **9** |
| Solo comandi a menu e filtri | Massima prevedibilità | Meno naturale per «trova un simile» | **7**, inclusi comunque |
| Agente libero sul filesystem | Potrebbe fare molte cose | Accesso eccessivo, percorsi sensibili, azioni difficili da verificare | **1** |
| Embedding locale subito | Ricerca più flessibile | Prima serve l'indice; costo e spiegabilità peggiori | **5** |

**Stima:** 9-14 giorni per indice, strumenti di ricerca/apertura, attività, privacy e prove; 3-5 giorni aggiuntivi per similarità completa e migrazione degli id delle serie. **[I]**

**Rischi:** apertura della revisione sbagliata; progetto simile scambiato per soluzione da copiare; perdita di file fuori dalle cartelle collegate; indice vecchio; fuga di metadati nel cloud; attività chiuse per errore. Le barriere sono conferma, spiegazione, indicazione dell'aggiornamento, filtro prima del modello e modifiche solo proposte. **[I]**

## 7. Il piano in ordine di valore per Daniel

Le stime includono test del nucleo e della finestra, migrazioni, traduzioni e verifica dei viaggi. Non includono l'acquisto di dati o servizi. **[I]**

| Passo | Contenuto | Valore e dipendenze | Stima [I] |
|---|---|---|---|
| **1** | Ripiego mappe, avvisi, anno e risoluzione | Risolve il guasto più visibile di R131 e rende affidabile il resto | 5-8 giorni |
| **2** | Parser coordinate, mappa nel Nuovo, viaggio «Crea e disegna» | Risponde al bisogno più forte di R148 senza aspettare anagrafica e ISTAT | 7-10 giorni |
| **3** | Stradale per cercare, ortofoto per disegnare, mondo Natural Earth | Chiude R149 con una scelta coerente | 4-7 giorni |
| **4** | Clienti, commesse, attività e collegamenti nel registro locale | Base per non rifare dati e per l'indice | 9-13 giorni |
| **5** | Manifesti, import/export e scansione delle cartelle collegate | Integra il modo di lavoro esistente senza spostare file | 5-8 giorni |
| **6** | Suggerimenti locali nel Nuovo, comuni ISTAT, committente e rete | Completa l'inizio intelligente usando il registro | 5-8 giorni |
| **7** | Indice, recenti per serie, ricerca e strumenti di apertura | R151 utile anche senza modello | 6-9 giorni |
| **8** | Attività con Meridio, progetti simili e filtri cloud | Completa R151 e la riservatezza dell'archivio | 5-8 giorni |
| **9** | Photon opzionale, Plus Code, altri fornitori, fogli catastali | Espansioni dopo la prova d'uso; il catasto resta un lavoro separato | secondo scelta |

**Totale dei passi 1-8:** 46-71 giorni, con sovrapposizioni possibili fra modelli e indice. Un primo pacchetto utile è formato dai passi 1-3, stimati in 16-25 giorni. Non consiglio di iniziare da embedding, CRM completo o download mondiali. **[I]**

### 7.1 Prove di accettazione proposte

1. Da File > Nuovo, scrivere uno stabilimento noto senza rete, scegliere il segno sulla mappa e arrivare a disegnare sul posto. **[I]**
2. Incollare decimali, DMS, UTM e ogni collegamento supportato; verificare il punto su riferimenti noti e rifiutare testi ambigui. **[I]**
3. Simulare metà tessere PCN in errore: niente buco muto, ripiego dichiarato, disegno sempre utilizzabile e nessuna raffica di richieste. **[I]**
4. Con rete spenta, aprire il mondo, selezionare uno stato e tornare all'Italia senza perdere il progetto. **[I]**
5. Creare cliente e commessa, collegare una cartella con revisioni, chiudere e riaprire senza server; tutti i dati noti restano e lo stato remoto è onesto. **[I]**
6. Importare due registri con lo stesso cliente e due commesse omonime: anteprima e unione per id, nessun doppione silenzioso. **[I]**
7. Chiedere a Meridio «ultimo capannone simile»: stessa serie contata una volta, motivo del risultato, conferma prima di aprire e salvataggio del lavoro in mano rispettato. **[I]**
8. Marcare un progetto riservato: nessuna richiesta di rete per sito, mappe o modello; nessun nome, percorso o conteggio riservato nei messaggi cloud. **[I]**

## 8. Decisioni lasciate a Daniel

Lo studio raccomanda, non decide. Le scelte che cambiano il lavoro futuro sono queste. **[I]**

1. Approvare il percorso «prima luogo, poi dati facoltativi» e il passaggio automatico stradale-ortofoto.
2. Accettare Nominatim solo su pulsante come servizio iniziale e Photon come opzione successiva, non come predefinito garantito.
3. Scegliere il pacchetto iniziale dei formati: decimali, DMS, collegamenti provati e UTM; Plus Code dopo.
4. Accettare Natural Earth offline come base del mondo.
5. Confermare il JSON locale con manifesti nelle cartelle, invece di SQLite o di un database sul server.
6. Stabilire se le commesse riservate possano mai avere un manifesto condiviso; la proposta predefinita è no.
7. Confermare che Meridio debba sempre mostrare percorso e revisione prima di aprire.
8. Decidere dopo una prova reale se la similarità strutturata basta o se servono embedding locali.

## 9. File dello studio

- `README.md`: questo documento.
- `genera_bozzetti.py`: generatore offscreen dei tre PNG con i gettoni del tema e Inter.
- `bozzetti/01-nuovo-progetto.png`: pagina Nuovo, suggerimenti e mappa.
- `bozzetti/02-clienti-commesse.png`: anagrafica e commesse.
- `bozzetti/03-meridio-capannone-simile.png`: ricerca locale e apertura confermata.

Comando per rifare i bozzetti dalla radice del repository. **[V: eseguito con successo in questo studio]**

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH=src \
  /var/home/daniel/fvtest/venv314/bin/python \
  docs/studio/20-inizio-progetto/genera_bozzetti.py
```
