# Programma FV: architettura e prima fase

21/10/2026. Proposta per il programma di progettazione fotovoltaica di Daniel, valida **qualunque interfaccia si scelga**: il confronto delle interfacce è in `01-confronto-approcci.md`, i requisiti normativi in `02-requisiti-normativi.md` (stessa cartella, `C:\Users\utente\Elettrico\output\programma-fv\`). Legenda: [V] verificato, [I] dedotto.

**Ambito: tutta Italia.**
- Quasi tutte le regole sono nazionali e valgono ovunque: CEI, guida VVF, D.Lgs. 199/2021 e 190/2024, ARERA, GSE.
- Per regione cambiano solo tre cose:
  - il metodo di calcolo energetico degli edifici, per Legge 10 e APE;
  - alcuni dettagli dell'obbligo rinnovabili;
  - i dati territoriali (rilievi degli edifici, ortofoto).
- Il programma usa quindi le regole nazionali come base e le varianti regionali come moduli aggiuntivi.
- La prima variante è la Lombardia, per due motivi:
  - ci sono le commesse di Daniel di questo periodo;
  - lì il metodo energetico è regionale, con i dati climatici pubblicati nel decreto (quindi utilizzabili).

## 1. I principi

Dalle regole di casa (`C:\Users\utente\dev\app-template\docs\01-filosofia.md`) e da quello che lo studio normativo ha mostrato:

1. **Un core in Python, senza interfaccia, coperto dai test.** La finestra mostra e innesca, non decide. Il core è lo stesso con Qt, con Electron o con GTK, quindi la scelta dell'interfaccia resta reversibile.
2. **Motori provati, non riscritti.** PVGIS (JRC) per la producibilità realistica, shapely/GEOS per la geometria, pvlib o PySAM per i calcoli orari. Fanno eccezione i metodi di legge (Allegato H lombardo, UNI/TS 11300-4): sono formule prescritte e si implementano come scritte, con test sui valori del testo.
3. **Ogni numero ha una provenienza.** Per i dati PVGIS: versione, banca dati, anni, data della chiamata e parametri. Per i metodi di legge: edizione e paragrafo. Tutto è salvato nel progetto, perché un progetto riaperto dopo un anno deve dare gli stessi numeri.
4. **Ogni regola ha una fonte e una validità.** Come nella libreria R02: id, condizione, testo in italiano e inglese, fonte (norma, edizione, articolo, pagina), [V]/[I]. In più le date di validità, perché le regole cambiano con la data del titolo o dell'avvio del progetto: guida VVF 2012 o 2025, Allegato III dal 03/08/2026, k lombardo dal 01/01/2027.
5. **Il programma prepara e verifica; firma il progettista.** Per la Legge 10 e l'APE restano obbligatori i software certificati (CENED+ in Lombardia, software CTI altrove) [V]. Il programma prepara i dati del FV e fa il calcolo di controllo.
6. **I dati dell'utente prima di tutto.** Il progetto si salva in modo atomico, con il file precedente come `.bak`. Le uscite non sovrascrivono mai: revisione nuova = file nuovo `_Rnn`. Ai servizi esterni vanno solo le coordinate.

## 2. Gli strati

```
interfaccia      Qt + WebEngine | Qt Quick 3D | Electron | GTK      (mostra e innesca)
-----------------------------------------------------------------------------------------
core Python
  model          progetto, sito, edifici, falde, ostacoli, campi FV, componenti, stringhe
  geo            WGS84 <-> metri locali, tile, convenzioni di azimut, geocodifica
  geometry       piani e poligoni (shapely), posa dei moduli, vincoli VVF, superficie S
  sun            posizione del sole; (fase 2) orizzonte vicino dagli ostacoli
  energy         PVGIS (client con cache) | metodo convenzionale (All. H, UNI/TS 11300-4)
                 | (fase 2-3) simulazione oraria 8760 con pvlib o PySAM
  electrical     stringatura; (fase 2) cavi, protezioni, quadri
  catalog        moduli e inverter con i dati normativi; (fase 2) cavi e quadri
  rules          requisiti, verifiche e note con le fonti; regimi (VVF, TU FER, TICA, CCI)
  reports        note IT/EN per capitoli, Word sul format dell'ufficio, Excel, DXF, PDF
-----------------------------------------------------------------------------------------
servizi          PVGIS 5.3, tile OSM ed Esri, DBGT Lombardia (WFS), Overpass, Nominatim,
                 (opzionale) Google Solar API
```

Ogni servizio esterno ha queste regole:
- un client proprio, con timeout e ritentativi ad attesa crescente;
- una cache su disco;
- un User-Agent proprio, senza dati personali;
- i limiti d'uso rispettati: PVGIS 30 chiamate al secondo; OSM con cache di almeno 7 giorni e niente scarico massivo; Overpass circa 10.000 richieste al giorno [V];
- gli errori spiegati a parole.

## 3. Il modello dei dati

- **Coordinate.** Origine nel punto del sito (latitudine e longitudine WGS84); assi locali in metri: x verso Est, y verso Nord, z in alto. Su qualche centinaio di metri l'errore è di millimetri [I].
- **Angoli: la convenzione della CEI 82-25/1:2026, 3.2.1.5-6** [V]. β è l'inclinazione sull'orizzontale. α è l'azimut misurato da Sud: negativo verso Est, positivo verso Ovest. È anche quella di PVGIS.
  - La stessa convenzione vale in ingresso, nei calcoli e nei testi.
  - Le conversioni verso le altre convenzioni si fanno ai bordi, ciascuna con il suo test, perché qui gli errori sono facili [V]:

  | Dove | Convenzione |
  |---|---|
  | PVGIS, `aspect` | 0 = Sud, 90 = Ovest, -90 = Est |
  | PVGIS, uscita di `printhorizon` | stessa convenzione di `aspect` |
  | PVGIS, ingresso di `userhorizon` | da Nord, in senso orario |
  | Google Solar API | 0 = Nord, 180 = Sud |

- **Edificio.**
  - Geometria: impronta, quote (piede, gronda, colmo) e tipo di copertura (piana, a falde, a shed). Le falde sono poligoni piani in 3D: inclinazione e azimut si ricavano dalla loro normale.
  - Dati per le norme:
    - attività soggetta VVF, con numero e categoria A/B/C;
    - copertura resistente al fuoco sì/no, e linee di compartimentazione sottostanti;
    - EFC, lucernari, aperture e impianti tecnici, come oggetti;
    - nuovo o ristrutturazione e di quale livello; pubblico o privato;
    - regione e data del titolo;
    - superficie S secondo la regola che si applica: in Lombardia la proiezione al suolo della copertura da foto aerea, nel resto d'Italia la sagoma secondo il RET.
- **Campo FV.**
  - Composizione: falda + modulo + tipo di posa (complanare; inclinata su tetto piano, con angolo e interfila; facciata; pensilina; a terra) + regole (fasce, gruppi, corridoi) + esclusioni.
  - Disposizione: calcolata, più le modifiche a mano (moduli tolti o aggiunti).
  - Classificazione VVF automatica: BAPV in copertura o in facciata, BIPV, pensilina interferente o no, impianto "incorporato" nel prisma verticale dell'edificio.
- **Componenti.**
  - Moduli: dati STC e NMOT, coefficienti di temperatura, dimensioni; certificazioni IEC 61215 e 61730, classe di applicazione, tensione massima di sistema; reazione al fuoco, Broof, classe C_FV della CEI TS 82-89; paese di produzione di modulo e celle, efficienza di cella e di modulo, iscrizione al registro ENEA. Gli ultimi servono per iperammortamento, Conto Termico e CACER.
  - Inverter: finestra MPPT, tensione e correnti massime per ingresso, potenza c.a., rendimenti, SPI e DDI integrati.
- **Potenze, con i nomi della CEI 82-25/1 (3.2.5.4-8)** [V]:
  - Po,cc: somma delle Pmax dei moduli in STC, esclusi i bifacciali sul retro. È la potenza "ai fini amministrativi".
  - Po,ca: minimo tra Po,cc e la somma delle potenze degli inverter alla temperatura dichiarata. È la potenza di CEI 0-21, CEI 0-16 e TICA.
  - Si scrivono in kW: la guida sconsiglia "kWp".
  - Il programma le calcola e le stampa sempre tutte e due, con l'etichetta; non scrive mai "potenza" senza qualifica.
  - Ogni regola dice quale usa. ARERA, GSE, TICA, CACER e FER X usano il minimo [V]. Per le soglie del TU FER, finché non c'è un chiarimento, si usa la scelta prudente, cioè Po,cc.
- **Ostacoli (fase 2).** Prismi, cilindri, alberi; edifici vicini dal DBGT o da OSM.
- **Risultati in cache**, con la loro provenienza.
- **File.** Il progetto è una cartella con un JSON a schema versionato, salvato in modo atomico. Le uscite stanno accanto, con `_Rnn`.

## 4. Due motori per l'energia

Lo studio normativo (`02`, filone B) cambia l'architettura su un punto: **PVGIS non basta**.

| Motore | Per che cosa | Note |
|---|---|---|
| **PVGIS 5.3** | producibilità realistica nella relazione FV di progetto; relazione energetica dei centri dati (DGR 6645: il metodo è libero, ma va dichiarato); diagnosi | orizzonte da DEM a 90 m più il nostro `userhorizon`, calcolato dagli ostacoli; toglie solo la diretta [V]. Anno tipo orario per i calcoli 8760. Citazione "PVGIS © European Communities, 2001-2026" [V] |
| **Metodo convenzionale mensile** | numeri per la Legge 10, per l'APE e per le coperture % dell'obbligo FER | **Regola nazionale, per tutta Italia:** DM 26/06/2015 aggiornato dal DM 28/10/2025, con la UNI/TS 11300-4 e i dati climatici della UNI 10349-1 [V]. Le UNI sono a pagamento e i loro dati non possono stare nel repository pubblico: chi ha la norma li carica in locale. **Dove la regione ha regole proprie, vale il metodo regionale.** La Lombardia le ha [V]: Allegato H, §11.11.1. Formula W = H_PV · W_pk · F_FV / I_ref; F_FV vale 0,70, 0,75 o 0,80 secondo la ventilazione dei moduli; H_PV con il modello isotropo dell'App. F e albedo 0,2; Hb e Hd dei 12 capoluoghi dall'All. 1, Prospetto III. Sono dati scritti nel decreto, quindi usabili. Per le altre regioni e le province autonome va verificato, una per una, se hanno regole proprie |
| **Simulazione oraria 8760** (fase 2-3) | autoconsumo, energia condivisa CACER (minimo orario tra immessa e prelevata), ritiro dedicato, diagnosi con i consumi misurati | pvlib o PySAM, con l'anno tipo PVGIS e i profili di prelievo |

**Ombre.**
- Il modello 3D produce un orizzonte vicino per ogni campo, che va a PVGIS (`userhorizon`).
- Per il metodo convenzionale produce un fattore mensile di ombreggiamento, documentato. Il filone B lo chiede come B05: l'Allegato H vuole che le ombre si considerino, ma il metodo esatto è da chiarire.

## 5. Regole, verifiche e note

- **Partenza:** le 27 regole di `l'archivio locale delle norme\tools\utilita-fotovoltaico\note_R02.py`. Testi e fonti si riprendono tali e quali; le condizioni si riscrivono da formule Excel a funzioni Python.
- **Correzioni** già trovate dal filone C, da fare anche nella R03 della libreria Excel: N13, N15, N17, N18, N23, N10. Il dettaglio è in `02`.
- **Requisiti nuovi:** ogni riga delle matrici di `02` diventa una regola. Il tipo dice cosa produce: verifica con esito, vincolo geometrico, dato da chiedere, voce di schema, testo di relazione, documento di pratica.
- **Esiti mostrati:**
  - verifiche, con esito "conforme", "attenzione" o "non conforme" e la fonte;
  - dati mancanti;
  - note per la relazione, divise in capitoli, in italiano e inglese;
  - elenco di documenti e pratiche.
- **Test:**
  - ogni regola ha i suoi;
  - per le regole che non cambiano, un test di parità con l'Excel R02 sulle combinazioni di `prova_R02.ps1`.

## 6. Interfaccia

Valgono qualunque sia il toolkit.

- **Viste:**
  - Sito: la mappa;
  - Pianta: il lavoro 2D su ortofoto, OSM o DXF;
  - 3D;
  - Componenti;
  - Verifiche;
  - Note;
  - Risultati.
- **La maggior parte del lavoro si fa in pianta:** disegnare falde ed esclusioni, posare i moduli, vedere i vincoli.
- **Il 3D entra in due tempi:**
  1. prima di sola visione: controllare e vedere il sole e le ombre;
  2. poi modificabile.

## 7. La prima fase: "dalla falda ai numeri"

L'obiettivo di Daniel per la prima fase: posare i pannelli e ricavarne inclinazione e orientamento. Con lo studio normativo questo diventa: posare i pannelli rispettando i vincoli, e avere subito numeri e verifiche. La fase si divide in tre rilasci piccoli; ognuno chiude con test, CI verde e una prova di Daniel.

**0.1: il nucleo** (si può cominciare prima di scegliere l'interfaccia)
- **Progetto:** cartella, JSON e salvataggio atomico; il sito da coordinate (si incolla "45.5226, 9.0300").
- **Falde a numeri:**
  - un poligono in metri, con inclinazione e azimut;
  - oppure due quote (gronda e colmo) più la distanza in pianta;
  - oppure la pendenza in %.
- **Archivio di moduli e inverter**, con i campi normativi della sezione 3.
- **Posa automatica** dei moduli in una falda:
  - verticale o orizzontale;
  - fasce dal bordo;
  - per le attività soggette, i vincoli VVF: 1 m dal bordo, gruppi di al massimo 20 m, corridoi di 2 m;
  - sui tetti piani, file inclinate con interfila ricavata dall'altezza del sole di riferimento;
  - il risultato: Po,cc, Po,ca, l'area dei moduli e l'efficienza del generatore.
- **Energia:**
  - PVGIS: PVcalc per campo e printhorizon, con cache e provenienza;
  - metodo convenzionale per campo: quello nazionale, con i dati UNI caricati dall'utente, e la variante lombarda, con i dati del decreto.
- **Obblighi:** potenza minima P = k × S (nazionale e Lombardia), con S calcolata dal modello.
- **Stringatura di base** (`02`, righe A01, A06-A10, A14-A15, D06, D30):
  - Uoc MAX = KU·Uoc STC, con Tmin dichiarata e con la sua fonte; senza dato, 1,2·Uoc STC;
  - Isc MAX = KI·Isc STC, con KI ≥ 1,25;
  - verifica di Uoc MAX contro Vsys, i dispositivi e l'inverter;
  - stringhe in parallelo uguali;
  - protezione di stringa quando serve, con la taglia;
  - finestra MPPT con Vmpp a NMOT e a Tmin;
  - orientamenti diversi su MPPT diversi.
- **Regole e note:** la R03, cioè la R02 portata in Python e corretta.
- **Uscita:** un riepilogo Word o PDF con le note in italiano e inglese, e un JSON dei risultati.
- **Interfaccia:** da riga di comando più il riepilogo, se il toolkit non è ancora deciso.

**0.2: mappa, vista satellitare e modellazione dell'edificio**
- **Ricerca del sito:** per indirizzo (Nominatim) o per coordinate.
- **Sfondo aereo**, da scegliere nelle preferenze:
  - ortofoto nazionale PCN 2012: senza chiave e sempre disponibile, ma datata [V];
  - Esri World Imagery: recente, con la chiave gratuita dell'utente [V];
  - qualunque WMS o XYZ a cui l'utente abbia diritto;
  - OSM per orientarsi.
- **Dove il rilievo 3D dell'edificio esiste già:**
  - dove la regione pubblica il rilievo 3D con licenza aperta. In Lombardia il DBGT dà impronta, altezze e falde (WFS, CC BY 4.0) [V]; per le altre regioni i geoportali vanno verificati uno per uno;
  - in opzione, Google Solar API, che propone le falde con inclinazione e azimut. Richiede una chiave con fatturazione e si interroga solo per coordinate [V].
- **Dove il 3D non c'è, l'edificio si modella sulla foto** (richiesta di Daniel del 21/10/2026):
  1. si ricalca il contorno della copertura;
  2. si danno le quote: gronda e colmo, oppure altezza e pendenza;
  3. si sceglie il tipo di tetto: piano, a una falda, a capanna, a padiglione, a shed;
  4. il programma costruisce le falde e ne ricava inclinazione e azimut, con l'azimut preso dal lato di gronda.
  
  Nelle ortofoto normali i tetti degli edifici alti sono un po' spostati rispetto alla base, perché la foto è raddrizzata sul terreno. Per il FV conta il contorno del tetto, ed è quello che si ricalca [I].
- **Esclusioni:** EFC, lucernari, impianti tecnici, linee REI, ciascuno con la sua fascia di 1 m.
- **DXF della posa** sui layer standard dell'ufficio, per i disegni.

**0.3: il 3D di visione**
- Edificio, falde, moduli e ostacoli semplici.
- Sole per data e ora, con le ombre a video.
- Controllo visivo dei vincoli.
- Da qui comincia la fase 2.

**Fuori dalla prima fase**
- **Fase 2:**
  - ombre calcolate: orizzonte vicino verso PVGIS e fattore mensile per l'Allegato H;
  - cavi, protezioni e quadri;
  - shed e facciate;
  - simulazione oraria e CACER.
- **Fase 3:**
  - regimi autorizzativi completi;
  - pratiche VVF;
  - relazione completa sul format dell'ufficio;
  - piano di manutenzione e cartellonistica;
  - IFC.

## 8. Test e verifiche

- **Test per modulo.** Le conversioni di coordinate e di azimut, la geometria, le regole, la parità con la R02.
- **PVGIS.** Test su risposte registrate, più una prova dal vivo separata.
- **Allegato H.** Test sui valori calcolati a mano dal testo del decreto.
- **Un progetto di prova sintetico**, mai una commessa vera. Si confronta con PVGIS online e, se Daniel ha accesso, con Solarius PV o PVsyst.
- **Prima di dire "stabile":** la verifica indipendente in una chat separata, come per Spola.

## 9. Rischi

| Rischio | Come si tiene a bada |
|---|---|
| Norme che cambiano: parti 4-6 della CEI 82-25 in arrivo, UNI 10349 in revisione, decorrenze dell'Allegato III | regole datate e versionate; un registro delle fonti con l'edizione; la matrice di `02` come lista di copertura |
| Licenze dei dati | solo fonti verificate (OSM, PCN, Esri con la chiave dell'utente, DBGT CC BY), con le attribuzioni a video. Nel repository pubblico niente tabelle UNI né testi CEI: chi ha la norma carica i dati in locale |
| Licenze del software | programma GPLv3; componenti AGPL solo per una scelta esplicita (vedi `01`, sezione 8) |
| Servizi esterni lenti o saturi (Overpass oggi, PVGIS) | cache, ritentativi, lavoro possibile senza rete sui dati già scaricati |
| Numeri di legge sbagliati | test sul testo del decreto e confronto con il software certificato; avviso che il programma non sostituisce CENED+ |
| Dati di commessa | restano in locale; ai servizi esterni vanno solo le coordinate |

## 10. Decisioni, una alla volta

1. **L'interfaccia** (`01`, sezione 9), dopo le prove brevi.
2. **Il nome dell'app** (le regole sono in `docs\02-guida.md` del template).
3. **La licenza:** proposta GPLv3, che accetta tutte le librerie trovate tranne le AGPL (`01`, sezione 8).
4. **Account Esri** gratuito per le ortofoto recenti (ogni utente il suo) e, se interessa, **chiave Google** per la Solar API.
5. **Norme da comprare** (`02`): servono se il programma deve lavorare fuori dalla Lombardia o oltre la prima fase.
