# Compito per una sessione cloud: la revisione completa di Meridiana (studio 18)

Bozza del 23/10/2026, da lanciare nell'ambiente «Meridiana studi» (rete Completo) con lo sforzo massimo, dopo l'unione dei ritocchi della fase 2 (d6d336b) e prima dei compiti dello studio 16 e dello studio 17. Lo studio che ne esce è `docs/studio/18-revisione-completa.md`, con le prove in `docs/studio/18-prove/`.

**Che cosa ha chiesto Daniel (23/10/2026):** «una revisione completa del programma da tutti i punti di vista e anche una riscrittura totale o quasi se necessaria e un rifacimento della UX». La risposta concordata: la revisione si fa adesso, da tutti i punti di vista; **la riscrittura è una conclusione possibile della revisione, non una premessa**, e si decide modulo per modulo con le prove in mano; il rifacimento dell'interfaccia parte da un progetto scritto (chi la usa, il percorso dal sito alla relazione, che cosa deve uscire), non dalle schermate di oggi.

**Il punto di partenza.** Meridiana ha due giorni di vita: primo commit del 21/10, circa 150 commit, 18.800 righe di Python in 78 file, 7.500 righe di test in 50 file, 637 test. È stata scritta di corsa e l'interfaccia è stata aggiustata a fasi (fase 1, fase 2, correzioni, ritocchi) sopra un'impostazione mai progettata davvero. Gli studi 12-17 e i compiti già decisi (`docs/compiti/16a-g`, `17a-f`, `14-assistente-prototipo.md`) sono il materiale: non si riaprono le decisioni prese (`docs/richieste.md`, tabella «Decisioni prese»), ma la revisione può dire che un compito va rifatto su fondamenta diverse, con il motivo.

## Come lavorare

Valgono le regole di `docs/compiti/fase-2.md` («Come lavorare»): identità git di Daniel, nessuna attribuzione, ramo `revisione-completa` da `lavoro`, richiesta di unione in bozza verso `lavoro` con le caselle dei temi, un commit per tema spinto subito, messaggi in inglese, mai `main`. In più:
- **Questo è uno studio, non un compito di codice.** Il programma non si tocca. Le prove (script, misure, confronti) stanno in `docs/studio/18-prove/` con i risultati in file `-risultati.txt`; i test del programma si lanciano, non si cambiano.
- **Ogni affermazione è marcata [V] (verificata, con come) o [I] (dedotta).** Le misure riportano il comando, la macchina (offscreen, Xvfb) e i numeri; i confronti con le fonti esterne riportano URL e data. Le norme italiane (CEI 0-21, 0-16, 64-8, DM 37/08, DCPREV) non sono raggiungibili dal cloud: le citazioni di `rules.py` e di `checks.py` si elencano per la verifica locale, senza inventarne il contenuto.
- **Il registro `docs/richieste.md`** si legge prima e si aggiorna alla fine (le righe R31, R32, R35, R36 e quelle che la revisione tocca).
- Lo studio è in italiano, con la struttura degli studi precedenti (metodo, temi con direzioni e voti, prove, raccomandazione, piano, fonti). Mai il trattino lungo.
- Lo sforzo è massimo: leggere tutto il codice, non campionarlo. Il tempo previsto è di ore; se la sessione viene interrotta, ogni tema spinto sta in piedi da solo.

## I temi

Per ogni tema: che cosa è stato guardato e come, i difetti trovati in ordine di gravità (con file e riga), il verdetto per modulo (**tieni**, **rifai**, **sostituisci**, con il motivo e la prova), la raccomandazione.

### A. Architettura e modello dei dati
- La separazione nucleo/interfaccia: che cosa del nucleo importa Qt, che cosa della finestra contiene logica (`window.py` ha 2.200 righe). Il flusso dei dati da `model.py` alle viste e ai lavori in thread (`LayoutJob`, `EnergyJob`); l'annulla (`edit()`, le impronte dello stato); la coerenza tra pianta, 3D, Proprietà e Verifiche.
- Il formato del file `.meridiana` (versione 6) e le migrazioni; le impostazioni (`config.py`, versione 8) e lo stato; le scritture atomiche.
- Il modello geometrico: edifici, falde (`roofs.py` sul rettangolo minimo, da rifare nel 16a), sottocampi, esclusioni, moduli; che cosa lo studio 16 richiede che il modello di oggi non regge.
- Verdetto: l'architettura obiettivo in una pagina (moduli, confini, dipendenze), e per ogni modulo di `src/meridiana` tieni/rifai/sostituisci.

### B. Correttezza dei calcoli (il tema più importante)
- `energy/simulate.py` contro `pvlib.modelchain.ModelChain` sullo stesso anno sintetico di `tests/_energy.py`: scarti ora per ora e annuali, con i motivi di ogni differenza.
- Il confronto con PVGIS: per un sito, una falda e un modulo, la produzione annua di Meridiana contro la stima di PVGIS (API `PVcalc`), e la resa specifica; studio 11 e `docs/studio/06-pvsyst-aurora-pvlib.md` dicono che cosa ci si aspetta.
- Il confronto con PVsyst: i progetti pubblici su GitHub elencati nello studio 11 (campioni con rapporto e risultati), per almeno due casi: PR, perdite per voce, energia annua; dove Meridiana non può fare lo stesso (bifacciale, mismatch, trasformatore) va detto.
- `energy/nearshade.py`: un caso analitico (un muro di altezza nota a sud, a mezzogiorno del solstizio) con l'ombra calcolata a mano; la frazione d'ombra e la perdita elettrica per stringa.
- `energy/economics.py`, `energy/consumption.py`, `bands.py`: le formule contro una definizione citata (VAN, tempo di ritorno, fasce ARERA F1-F3); `dispatch` della batteria con un caso a mano.
- `rules.py` e `checks.py`: l'elenco di tutte le citazioni normative con articolo e pagina, da verificare in locale (Daniel ha le norme), e le regole che sembrano sbagliate o incomplete con il perché.
- Verdetto: quali numeri di Meridiana si possono mettere in una relazione oggi, e quali no.

### C. Prestazioni, con un bilancio da rispettare
- Gli obiettivi proposti: avvio sotto 1 s, ogni gesto dell'interfaccia sotto 100 ms, il calcolo energetico sotto 1 s per 200 moduli e sotto 10 s per 5.000, la posa dei moduli sotto 1 s per 5.000.
- Le misure di oggi sul cloud (offscreen, `cProfile`): dove va il tempo. La misura locale del 23/10 (R31): calcolo di 3,55 s su 188 moduli, di cui 2,3 s nel solo ciclo `dispatch` (8.760 ore per 156 chiamate, Python puro), 0,95 s in numpy e pandas; lo script `docs/studio/18-prove/profilo_energia.py` la ripete.
- **La prova decisiva per R31:** `dispatch` riscritto in tre modi (numpy senza ciclo dove possibile, `numba` in un ambiente a parte, un'estensione in Rust con PyO3 e maturin in un ambiente a parte), con i tempi e il costo di distribuzione di ognuno (wheel per Windows e Linux, dimensione, dipendenze). Niente entra nel programma: è una misura per la decisione di Daniel («da verificare l'effettivo beneficio»).
- La scalabilità: un progetto da 5.000 e uno da 20.000 moduli (generati), posa, ombre, 3D (`mesh.py`), pianta (`plan.py`: quanti elementi grafici, come si disegnano).
- Verdetto: che cosa si compila, che cosa si riscrive, che cosa basta vettorializzare.

### D. I test
- Che cosa coprono e che cosa no (nucleo contro finestra; i calcoli; i file; le migrazioni); i test fragili (quelli che dipendono dallo schermo, dalla scala, dai tempi); i 6,5 minuti della suite su Windows e come scendere (quante finestre vere si aprono, quante servono).
- Il metodo con cui i test descrivono il comportamento (i nomi come frasi) va tenuto; proporre la struttura della suite dopo la revisione.

### E. Il progetto dell'interfaccia (il rifacimento della UX)
- **Il documento di progetto dell'interfaccia** (`docs/design/interfaccia.md`, nuovo): chi usa Meridiana (Daniel e un progettista elettrico italiano come lui), il percorso dal sito alla relazione, le fasi (B4 dello studio 17: Modello, Impianto, Producibilità, Consumi, Bilancio ed economia, Relazione), che cosa deve uscire (relazione, schemi, elenchi, esportazioni), e per ogni fase gli oggetti, le azioni, i pannelli e le verifiche. Le decisioni degli studi 12-17 vanno raccolte lì in un disegno coerente; dove due decisioni si contraddicono, va detto e proposta una via.
- Il confronto con i programmi di riferimento già studiati (PVsyst, Aurora, Helioscope, PV*SOL, FreeCAD, DIALux evo, Revit) sui percorsi, non sull'aspetto.
- Gli elaborati: che cosa produce oggi `report.py` e che cosa manca per una relazione da consegnare (schema unifilare, elenco moduli e stringhe, tabella delle perdite, verifiche con le fonti, disegni in DXF e IFC).
- Le tre scelte rimaste aperte dello studio 17 (il manuale nel repository o in rete; quali interazioni dei grafici contano; l'altezza della barra B4 con il testo): una proposta con il motivo.
- Verdetto: che cosa dell'interfaccia di oggi si tiene, che cosa si rifà, in che ordine; i compiti `17a-f` vanno confermati, modificati o sostituiti.

### F. Il lato professionale
- Che cosa serve a un progettista elettrico italiano e manca: scelta dell'inverter e stringatura (16d), accumulo, pratiche (CEI 0-21 allegati, GSE, Comune, VVF con la DCPREV 14030/2025), DM 37/08, catasto, il formato PVsyst (studio 10). Una lista in ordine di valore.
- Il confronto con i programmi italiani e non (PVsyst, PV*SOL, Solarius PV, Blusol, SunnyDesign, Helioscope, Aurora): che cosa fanno che Meridiana non fa, con la fonte.
- **Le sorgenti delle mappe (R36):** le famiglie elencate nel registro (PCN, regioni, WMS del Catasto dell'Agenzia delle Entrate, geoportali europei, servizi mondiali a chiave, sagome degli edifici aperte), con per ognuna l'indirizzo del servizio, la licenza letta sulla fonte, i limiti d'uso, se si può conservare l'immagine nel progetto; la proposta di sorgenti configurabili (WMS, WMTS, XYZ) con alcune predefinite.

### G. Qualità del codice e sicurezza
- Lettura di tutto `src/meridiana`: duplicazioni, funzioni troppo lunghe, nomi, `except` che tacciono, errori non mostrati all'utente, testi senza `_()`, log. La stima di quante righe sono «da tenere com'è», «da pulire», «da rifare».
- Sicurezza e riservatezza: i file di progetto (JSON? cosa succede con un file malformato o malevolo), la rete (PVGIS, tasselli, aggiornamenti: che cosa parte e quando), le chiavi future (studio 14), le immagini dentro il progetto.
- Le licenze: pvlib, Qt (LGPL), matplotlib, shapely, i dati (CEC, OSM, OpenTopoMap, PCN), i font e le icone in `data/`.

### H. Pacchetti e rilascio
- `build-aux/windows/meridiana.spec` e il manifest Flatpak descrivono ancora un'app GTK (nota dei ritocchi): che cosa va rifatto per PySide6 (PyInstaller con Qt Quick 3D e le traduzioni `qtbase_it.qm`, Flatpak con il runtime KDE), la dimensione attesa, l'aggiornatore, la firma con minisign (le altre app di Daniel la usano), il CI (oggi fermo per la fatturazione: proporre un flusso che consumi meno minuti).
- La documentazione: `docs/progetto.md`, `docs/funzionalita.md`, il manuale (E dello studio 17).

## Il piano

- **Il verdetto complessivo**, in una pagina: tenere e migliorare modulo per modulo, oppure rifare quasi tutto. Se è «rifare», come: codice nuovo accanto al vecchio, un modulo alla volta, i test portati, mai una riscrittura di getto.
- **Le bozze dei compiti** `docs/compiti/18a-…` nell'ordine proposto, con fatica e dipendenze; dove un compito già scritto (16a-g, 17a-f, 14) resta valido lo si dice; dove cambia, si scrive che cosa cambia.
- **Le domande a cui solo Daniel può rispondere**, numerate.
- **Da provare sul PC di Daniel**: tutto quello che il cloud non può vedere o misurare (schermo vero, GPU, le norme nell'archivio, i tempi su Windows).

## La chiusura
- Richiesta di unione fuori bozza, con il riassunto in italiano: i difetti più gravi trovati, il verdetto, l'ordine dei compiti.
- Il registro aggiornato; una riga nel diario di `docs/progetto.md` (appendice A); l'indice degli studi in `CLAUDE.md`.
