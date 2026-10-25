# Meridiana: il progetto dell'interfaccia

Documento di progetto del 23/10/2026, scritto per il tema E della revisione completa (`docs/compiti/18-revisione-completa.md`). Raccoglie in un disegno solo le decisioni degli studi 12-17 e del registro `docs/richieste.md`, dice dove si contraddicono e propone una via. Il programma non si tocca: questo è il punto di partenza dei compiti, non una schermata.

**Legenda.** [D] deciso da Daniel, con la fonte (una riga della tabella «Decisioni prese» o una richiesta Rn del registro, oppure la sezione dello studio); [P] proposta di questo documento, da confermare; [V] letto nel codice o nei documenti del repository.

**Vocabolario**, perché la parola «scheda» oggi vuol dire tre cose diverse:
- **fase**: una delle sei voci della riga in alto (Modello, Impianto, ...), oggi `QTabWidget`;
- **pannello**: Progetto, Proprietà, Verifiche, Meridio agganciato, oggi `QDockWidget`;
- **scheda**: una superficie arrotondata che galleggia sul fondo (A3 per i pannelli, R2 per i risultati); mai per le fasi;
- **gruppo**: un insieme di campi con il titolo dentro le Proprietà (Sottocampo, Distanze e margini);
- **sezione**: un blocco di righe con intestazione in un elenco (le sezioni dell'albero T2, i livelli nelle Verifiche F2);
- **barra della fase**: la barra alla ribbon sotto le fasi (B4); **barra della vista**: la barra dentro la pianta e il 3D (R27).

## 1. Chi la usa e che cosa deve uscire

### 1.1 Le persone

- **Daniel**: progettista elettrico in uno studio piccolo, lavora in AutoCAD e Revit, usa Windows in ufficio e Linux con Niri sul portatile, tastiera italiana. Vuole valori predefiniti buoni e nessun blocco all'inizio (decisione del 21/10, `docs/progetto.md` sezione 1), ogni numero con la sua fonte, un'interfaccia da CAD (studio 12, sezione 5).
- **Un progettista elettrico italiano come lui**: fa relazioni, schemi, elenchi e pratiche; conosce PVsyst (spesso lo subisce), AutoCAD, i portali dei distributori e del GSE; non vuole un programma da imparare per settimane. Non è un fisico del fotovoltaico: le formule gli servono per la relazione, non per la giornata.
- **Chi legge i risultati senza usare il programma**: il collega che apre il file dopo una settimana, il committente che legge la relazione, l'installatore che monta con l'elenco delle stringhe in mano.

### 1.2 Gli impianti

Da 6 kW su un tetto a falde a qualche MW a terra: abitazioni, capannoni con tetti piani e lucernari, pensiline, campi a terra; con o senza accumulo; in rete, spesso con l'autoconsumo e le CER. Il caso tipico è il capannone di Rho del progetto di prova (188 moduli); il caso grande da reggere è 5.000 moduli (studio 12, appendice A: 4.682 moduli già misurati).

### 1.3 Che cosa deve uscire, per chi

| Destinatario | Che cosa gli serve | Dove nasce in Meridiana |
|---|---|---|
| Committente | Relazione tecnica con producibilità, bilancio, economia; pianta con i moduli; immagini 3D; confronto delle varianti | Fasi 3, 4, 5, 6 |
| Installatore | Pianta dei moduli quotata (DXF), elenco moduli e stringhe con il codice inverter.ingresso.stringa, schema unifilare, elenco materiali, fasce e corridoi VVF | Fasi 1, 2, 6 |
| Distributore (CEI 0-21, CEI 0-16) | Potenza, fasi, livello di tensione, protezioni (SPI, DDI), schema unifilare, dati di moduli e inverter | Fasi 2, 6; le regole già in `rules.py` e `checks.py` |
| GSE (ritiro dedicato, CER) | Potenza, POD, configurazione, dati dell'impianto | Fasi 4, 5, 6 |
| Comune, SUAP | Regime amministrativo, planimetria, relazione | Fase 6 (regime: `funzionalita.md`, D.Lgs. 190/2024 ancora ○) |
| Vigili del Fuoco | Pianta con distanze, gruppi e corridoi (DCPREV 14030/2025, già nella posa) | Fasi 1, 6 |
| Banca, committente che pretende PVsyst | Esportazione verso PVsyst (studio 08, attrito F25), P50/P90 | Fase 6 (○) |

I contenuti precisi degli allegati per distributore e GSE si prendono dai modelli ufficiali e dalle norme nell'archivio di Daniel: qui non si elencano a memoria (regola di `CLAUDE.md`).

### 1.4 Le regole che valgono per tutta l'interfaccia

1. **Un modello solo.** Il disegno dà orientamenti, moduli, stringhe e scena d'ombra: le quattro coerenze che PVsyst fa fare a mano (studio 08, 4.1 F1-F5) qui non esistono. L'interfaccia non deve mai chiederle.
2. **Calcola sempre, non blocca mai.** Valori predefiniti marcati come tali; ricalcolo in background; i valori vecchi restano, in grigio (16f, [D] 23/10).
3. **Ogni numero dice da dove viene** («Come è calcolato», pedigree, relazione).
4. **Le verifiche non fermano**: errore, avviso, informazione (studio 12a, 3.5), con «Correggi» e la fonte.
5. **Mai un comando solo su un tasto F; niente Ctrl+Alt; lettere singole rimappabili** (studio 12, sezione 5, [D] 22/10).
6. **Il tema vale per l'interfaccia; pianta e 3D hanno colori propri** (R16 [D]).

## 2. Il percorso dal sito alla relazione: le sei fasi

### 2.1 Il percorso in breve

[D] Le fasi sono quelle di B4 (studio 17, B.4; «bella la suddivisione in fasi», registro 23/10): **1 Modello, 2 Impianto, 3 Producibilità, 4 Consumi, 5 Bilancio ed economia, 6 Relazione**. La fase 2 è la scheda «Impianto» dello studio 16 (D.4, nome [D] 23/10). La fase 6 non esiste ancora: oggi la relazione è File > Esporta la relazione.

[P] **Le fasi sono luoghi, non tappe.** Lo studio 17 (B.4) obietta a B4 che «Meridiana non è un flusso a tappe: si torna al modello dopo aver visto i consumi». È vero, e la via è questa: ogni fase è sempre apribile, nessuna chiede di avere finito la precedente; i numeri dicono l'ordine naturale del lavoro, come i passi di HelioScope e i modi di DIALux evo. Che cosa manca per andare avanti lo dicono le Verifiche (per esempio «Nessun inverter scelto: Meridiana ne dimensiona uno», livello da sapere) e i valori grigi «da aggiornare», non un blocco.

```
  sito e sfondo -> edifici, tetti, esclusioni -> sottocampi e posa     [1 Modello]
      -> inverter e stringhe                                           [2 Impianto]
      -> meteo, perdite, calcolo orario, PVGIS a fianco                [3 Producibilità]
      -> POD, curva o bollette o profilo                               [4 Consumi]
      -> prezzi, CER, accumulo, investimento, VAN                      [5 Bilancio ed economia]
      -> capitoli, allegati, esportazioni, revisione                   [6 Relazione]
  in ogni fase: Verifiche (Ctrl+J), Meridio (Ctrl+L), annulla, varianti, palette (Ctrl+Maiusc+P)
```

Quello che c'è in tutte le fasi: la barra dei menu, la riga delle fasi con «Variante» nell'angolo destro, i pannelli Progetto e Proprietà (o l'ispettore della fase), le Verifiche in basso, Meridio, la barra di stato, l'annulla, il salvataggio automatico.

Il confronto con i programmi di riferimento, sui percorsi e non sull'aspetto, è nella sezione 8.

### 2.2 Fase 1, Modello

**Oggetti**: Sito (indirizzo, coordinate, quota, livello di tensione, giorno e ore di progetto); Sfondo (ortofoto PCN, OSM, OpenTopoMap, nessuno, velatura; le sorgenti configurabili di R36 quando saranno studiate); Immagine importata (R21 [D]); Edificio con il Tetto (piano, una falda, due falde, padiglione, falde libere; dal 16a su piante qualsiasi con i lati «gronda o testata» e la quota del colmo); Falda; Esclusione con la fascia (lucernario, evacuatore, impianto, camminamento) e Ostacolo con l'altezza (camino, parapetto, albero, edificio vicino); Sottocampo con i parametri di posa; Fila e Modulo (16c: file come oggetti, moduli esplosi).

**Azioni e tasti** (studio 12, sezione 5 [D]; studio 16 [D] per M e D):

| Azione | Tasto | Dove |
|---|---|---|
| Seleziona, Edificio, Falda, Sottocampo, Esclusione | V, B, P, S, X | gruppo Disegna e Modifica della barra della fase, menu Disegna |
| Fila (16c) | L, fissata nel registro `shortcuts.py` (compito 16c, 24/10/2026) | gruppo Disegna |
| Sposta (con Ruota dentro il comando, «R» o grip), Misura | M, D | gruppo Modifica |
| Rettangolo con tre clic, Squadra | R, Q | gruppo Modifica |
| Edificio da modello (rettangolo, L, T, U, trapezio; 16a) | menu | gruppo Disegna |
| Posa i moduli (il pulsante pieno della fase), Svuota, Riposa in automatico (16c) | pulsante | Proprietà del sottocampo e gruppo Posa |
| Agganci, orto, lunghezze vicino al cursore | F3, F8, F12 (mai soli: anche nella barra della vista e nel menu) | barra della vista |
| Ctrl tenuto: niente agganci; Maiusc: blocca la direzione; Ctrl al rilascio di Sposta: copia | | pianta e 3D |
| Esc, Invio, Backspace, Canc, F2 | esce o annulla il segmento; conferma o ripete; toglie l'ultimo punto; elimina (solo con Seleziona); rinomina | |
| Inquadra, zoom finestra, estensione, nord in alto, vista iniziale | F, Z, Maiusc+Z, N, Inizio | barra della vista, cubo |
| Solo pianta, solo 3D, affiancate | Ctrl+Maiusc+2, Ctrl+Maiusc+3 | barra della vista |
| Mostra le stringhe | W | menu Vista |
| Mouse | stile «AutoCAD» predefinito (centrale pan, Maiusc+centrale orbita, rotella verso il cursore, doppio clic centrale adatta, destro trascinato orbita, destro fermo menu) [D] 23/10 | pianta e 3D |

**Pannelli**: Progetto (T2: sezioni EDIFICI · n, SOTTOCAMPI · n, ESCLUSIONI · n; [P] anche IMMAGINI · n per le immagini importate, oggi raggiungibili solo dal menu Sfondo); Proprietà dell'oggetto selezionato (gruppi di oggi: Sottocampo, Distanze e margini, Vigili del fuoco, Passo dal sole, Lati, Connessione e obblighi; dal 16a il gruppo Tetto con i lati e la quota del colmo; dal 16c il Risultato della posa con lo stato «file a mano»); Verifiche delle aree posa, ombre, regole, import; Meridio con le tre domande del Modello.

**Verifiche prodotte**: note della posa (file tolte per i corridoi VVF, moduli fuori dalle ombre con il costo in moduli), fasce e distanze, ombre degli ostacoli nel giorno di progetto, con il 16c anche «gruppo oltre 20 m», «corridoio sotto 2 m», «n moduli sull'esclusione», tetto che non segue più la pianta (16a, avviso all'apertura).

**Esce**: la pianta e il 3D (per la relazione: un «Salva immagine» con dimensione e sfondo, studio 15, 3.11 [P]); l'elenco degli edifici e delle falde (pendenza, azimut, area); per ogni sottocampo moduli, kWp, passo, note.

### 2.3 Fase 2, Impianto (studio 16, tema D [D])

**Oggetti**: Inverter (modello dal catalogo o dimensionato da solo, quantità, MPPT e ingressi); Stringa (nome inverter.ingresso.stringa, i moduli nell'ordine, lo stato); i moduli fuori stringa; più avanti ottimizzatori e microinverter ([D] dopo).

**Azioni**: Aggiungi un inverter dal catalogo; Dimensiona da solo (rapporto DC/AC, inverter uguali); Stringhe automatiche con le strategie di PVsyst (una fila per stringa, a U, avanti e indietro, una fila per MPPT); la **modalità di stringatura** (R12 [D]): un pulsante della fase, con un pannello flottante per ogni inverter sopra la pianta che mostra ingressi e MPPT, le stringhe accettate, quelle collegate e il loro stato con colore, icona e parola; nella modalità si clicca o si trascina sui moduli, il clic destro toglie, l'estremo si allunga, Esc chiude la stringa; «Rifai in automatico» con conferma. W è sempre acceso in questa fase.

**Pannelli**: Progetto con le sezioni INVERTER · n e STRINGHE · n [P]; Proprietà dell'inverter (modello, quantità, ingressi) o della stringa (moduli, ingresso, verifiche); le Verifiche dell'area stringhe e connessione; Meridio con domande sulle stringhe («Questa stringa regge a -10 °C?»). [P] L'elenco degli inverter con gli MPPT, che la bozza 16d mette «a destra» dentro la pagina, va nel pannello di destra come ispettore della fase (una disposizione sola, studio 12 N2 [D]): a destra non ci devono essere due colonne.

**Verifiche prodotte**, in diretta a ogni gesto (`stringing.plan` in pochi millisecondi): Uoc alla minima, Isc, finestra MPPT a caldo e a freddo (condizioni PVsyst 60/20/-10 °C prima della simulazione [D]), protezioni di stringa, SELV, rapporto DC/AC per inverter, sbilanciamento tra ingressi, moduli fuori stringa; le soglie CEI 0-21 (monofase, SPI, rincalzo) già in `checks.connection`.

**Esce**: l'elenco delle stringhe per inverter e ingresso con i moduli, la mappa delle stringhe sulla pianta (anche in DXF, fase 6), i dati per lo schema unifilare.

### 2.4 Fase 3, Producibilità

**Oggetti**: Meteo del sito (anno tipo e orizzonte PVGIS, in cache); i Campi per orientamento (dalla posa); l'Inverter come rimando all'Impianto («2 × SUN2000-10KTL, cambia…», 16d); le Perdite (sporcamento, LID, qualità, mismatch, cavi DC e AC, indisponibilità); il limite di immissione; il giorno di progetto per le ombre.

**Azioni**: Calcola (il pulsante pieno della fase; F5 ricalcola subito); Scarica da PVGIS; PVGIS a fianco; Confronta le varianti (Ctrl+Maiusc+C).

**Pannelli**: a destra l'ispettore dei Risultati (variante in mano e le sue cifre, come oggi `Inspector`); Progetto per scegliere il sottocampo di cui leggere i numeri [P: i risultati per campo sono ◐ in `funzionalita.md`]; Verifiche delle aree produzione e ombre; Meridio con le domande sulla resa.

**Grafici** (D2, pyqtgraph [D] «forse»): Mesi (Meridiana e PVGIS), Perdite (catena), Giorno tipo, «Come è calcolato». I risultati come schede piene R2: il numero chiave (energia annua) nel velo d'accento, poi resa specifica, PR, potenza STC e AC, PVGIS.

**Verifiche prodotte**: stime al posto dei dati (meteo non scaricato, inverter dimensionato da solo), resa fuori dall'intervallo atteso (da scrivere con le fonti), perdite al valore predefinito.

**Esce**: tabella mensile, resa, PR, catena delle perdite con i kWh per voce, confronto PVGIS mese per mese.

### 2.5 Fase 4, Consumi

**Oggetti**: Punto di fornitura (POD, fornitura, potenza impegnata); Consumi (curva misurata CSV a 15 minuti o oraria, bollette per mese e fascia, kWh annui per fascia, kWh annui, uno dei dieci profili tipici); le fasce F1, F2, F3 con i festivi.

**Azioni**: Importa una curva…; scegli la base dei consumi; i campi del POD.

**Pannelli**: ispettore dei Risultati; Verifiche dell'area consumi (profilo sintetico in uso, fornitura dedotta dalla taglia); Meridio.

**Grafici**: Mesi, Giorno tipo, Settimana, Durata, «Come è calcolato»; i riquadri R2 con consumo annuo per fascia, carico di base, fattore di carico.

**Esce**: la diagnosi dei consumi (fasce, mesi, settimana media, curva di durata) per la relazione.

### 2.6 Fase 5, Bilancio ed economia

**Oggetti**: Energia acquistata (prezzi per fascia, tutto compreso); Energia immessa (ritiro dedicato); Comunità energetica (DM 414/2023, TRASE); Accumulo dal catalogo; Investimento e costi di esercizio; Parametri finanziari (tasso, anni, detrazione).

**Azioni**: scegli la batteria dal catalogo; Calcola; Confronta le varianti.

**Pannelli**: ispettore dei Risultati; Verifiche dell'area economia (prezzi ancora predefiniti, TRASE a zero); Meridio.

**Grafici**: Bilancio, Bolletta, Flusso di cassa, Anno per anno, Taglia, Accumulo, «Come è calcolato»; i riquadri R2 con autoconsumo, autosufficienza, VAN, tempo di ritorno, costo livellato.

**Esce**: i KPI, i flussi di cassa anno per anno, le tabelle di taglia e accumulo.

### 2.7 Fase 6, Relazione [P, nuova]

La fase è il posto dove si prepara la consegna: oggi i suoi pezzi stanno sparsi (File > Esporta la relazione, Varianti > Confronta, «Copia le note» nelle Verifiche, «Salva come nuova revisione»).

**Oggetti**: la Relazione (intestazione, committente, progettista, data, revisione; i capitoli con una casella ciascuno); gli Allegati (elenco moduli e stringhe, schema unifilare, pianta in DXF, modello IFC4, serie orarie in CSV, allegati per distributore e GSE quando ci saranno); le Varianti da confrontare.

**Azioni**: Esporta la relazione (Ctrl+E); Esporta DXF, IFC4 (dipende dalla decisione su ifcopenshell, registro «Da decidere»), CSV; Copia le note per la relazione; Confronta le varianti (Ctrl+Maiusc+C); Salva come nuova revisione (Ctrl+Maiusc+R [D]).

**Pannelli**: Progetto come indice dei capitoli con le caselle; al centro l'anteprima della relazione (lo stesso `QTextDocument` di `report.py`, in un `QTextBrowser` con le pagine) e sopra i campi dell'intestazione; a destra l'ispettore «Elaborati» con un pulsante per ciascuno e lo stato (fatto, da rifare perché il progetto è cambiato); in basso le Verifiche nel modo «pronto per la consegna»: tutto ciò che è «da correggere», i valori ancora predefiniti (la tabella finale di `report.py`), le stime in uso.

**Esce**: il PDF e gli allegati della sezione 7.

## 3. La struttura della finestra

### 3.1 Lo schema

```
+--------------------------------------------------------------------------------------------+
| File  Modifica  Disegna  Vista  Cataloghi  Sito  Varianti  Aiuto               Tema  Colore|
| (1) Modello   (2) Impianto   (3) Producibilita   (4) Consumi   (5) Bilancio   (6) Relazione |
|                                                                        Variante: Base  v   |
| [ Disegna: Edificio  Modello  Falda  Sottocampo  Esclusione  Fila ] [ Modifica: Seleziona  |
|   Sposta  Ruota  Misura  Squadra ] [ Posa: Posa i moduli  Svuota ]      <- barra della fase|
+------------+-------------------------------------------------------+-----------------------+
| PROGETTO   | .-------------------------------------.  .----------. | PROPRIETA             |
| EDIFICI 2  | | Pianta 3D Affiancate | Inquadra    |  | 3D  cubo | | Sottocampo        ?   |
|  Uffici    | | F3 F8 | Sfondo                  N  |  |          | |  Nome   ...           |
|  Magazzino | |                                    |  |          | | Distanze e margini ?  |
| SOTTOCAMPI | |         pianta                     |  |          | |  ...                  |
|  Cop. Sud  | |                                    |  |   sole   | | Risultato della posa  |
| ESCLUSIONI | | scala                       fonte  |  | 21 dic   | |  [Posa i moduli]      |
|  Lucernario| '-------------------------------------'  '----------' | ? Aiuto: Tra le file  |
+------------+-------------------------------------------------------+-----------------------+
| VERIFICHE  1 da correggere  2 da controllare  2 da sapere              Per livello  v       |
|  DA CORREGGERE (1)  ...   DA CONTROLLARE (2)  ...   DA SAPERE (2) ...   SUPERATE (1) chiuse |
+--------------------------------------------------------------------------------------------+
| Sottocampo: disegna l'area...    calcolo...   x1 !2   12,4 x 8,6 m   E 12,36 N 8,40   Meridio|
+--------------------------------------------------------------------------------------------+
```

Meridio fluttua sopra l'area centrale (in basso a destra sulla 3D nel Modello, in basso a sinistra in Producibilità, in basso a destra altrove; studio 14, 7.3 [D]) con la chat che si apre come fumetto (R33 [D]).

### 3.2 Le superfici: A3, pannelli come schede [D]

[D] Studio 17 A3 («mi piacciono molto», registro 23/10): pannelli e viste come schede arrotondate sul fondo della finestra, 8 px di spazio, i titoli dentro la scheda; l'albero T2.

Quello che la prova impone (studio 17, A.5 [V]): in chiaro la scheda sta a 1,07:1 dal pannello e in scuro a 1,00:1. Quindi un token `card` nuovo (in scuro un velo bianco al 6-8 % sopra il pannello, in chiaro il bianco della vista con un bordo di 1 px `line`), l'ombra disegnata e non `QGraphicsDropShadowEffect`, un pannello trascinato fuori che perde la scheda. Costo 3-4 giorni (compito 17a, già riscritto su A3).

[P] Regole di profondità, per non sommare cornici (Apple: «nested boxes»):
- una scheda non sta mai dentro un'altra scheda: i gruppi C3 delle Proprietà stanno nella scheda del pannello, i riquadri R2 stanno nella pagina della fase;
- raggi decrescenti: 8 px la scheda, 6 px il gruppo, 4 px pulsanti e campi;
- la linea di 1 px `line` tra le parti resta anche con A3 (è ciò che in chiaro fa vedere la scheda);
- le viste (pianta e 3D) con gli angoli arrotondati di 4 px dentro il loro contenitore, senza ombra;
- il bordo di 2 px d'accento sulla vista attiva (l'idea di Lucciola nello studio 13, 11, ancora aperta) solo come indicatore del fuoco da tastiera (F6), mai come decorazione.

### 3.3 La riga delle fasi e la barra della fase (B4) [D]

[D] B4 con i gruppi; il testo sotto le icone resta, con l'opzione per toglierlo e rimetterlo (registro 23/10, seconda risposta); «Variante» nell'angolo destro della riga delle fasi (bozza 17b); su un fianco sempre solo icone (R19 [D]).

[P] I gruppi per fase (le etichette sotto i gruppi; i nomi dei comandi nei suggerimenti con il tasto):

| Fase | Gruppi |
|---|---|
| 1 Modello | Disegna (Edificio, Edificio da modello, Falda, Sottocampo, Esclusione, Fila); Modifica (Seleziona, Sposta, Ruota, Misura, Squadra, Rettangolo); Posa (Posa i moduli, Svuota, Riposa in automatico) |
| 2 Impianto | Inverter (Aggiungi dal catalogo, Dimensiona da solo); Stringhe (Automatiche con le strategie, Stringatura a mano, Rifai in automatico) |
| 3 Producibilità | Calcolo (Calcola, Scarica da PVGIS); Confronto (PVGIS a fianco, Confronta le varianti) |
| 4 Consumi | Dati (Importa una curva, Base dei consumi) |
| 5 Bilancio ed economia | Componenti (Batteria dal catalogo); Calcolo (Calcola); Confronto (Confronta le varianti) |
| 6 Relazione | Esporta (Relazione, DXF, IFC4, CSV); Varianti (Confronta, Nuova revisione); Appunti (Copia le note) |

Non ci sono i gruppi «Sole» e «Sfondo» del bozzetto B4: il sole sta nella barra sotto la 3D e lo sfondo nella barra della pianta, perché «ciò che riguarda le viste sta nelle viste» (R27 [D]); vedi la contraddizione C5.

[P] La barra c'è in tutte le fasi, anche dove ha due gruppi: una riga che compare e sparisce fa saltare le viste di 70 px a ogni cambio di fase (NN/g: gli elementi sempre nello stesso posto). La bozza 17b dice «solo nelle schede che hanno strumenti»: è un'inferenza del redattore, non una decisione.

[P] Le fasi si aprono con Ctrl+1…6, secondo il loro numero (decisione di Daniel del 24/10/2026, che supera C8); Proprietà passa a Ctrl+P, Ctrl+0 resta lo schermo pulito [D], Ctrl+Maiusc+2 e 3 sono le viste [D], Alt+cifra è vietato. Le fasi si cambiano anche con Ctrl+Tab, Ctrl+PagGiù e Ctrl+PagSu [D] e dalla palette («Vai a: Impianto»).

[P] In Qt: la riga delle fasi resta il `QTabWidget` (stile a riga d'accento, il punto davanti alla fase attiva dello studio 13); la barra della fase è una `QToolBar` non spostabile per fase in un `QStackedWidget` sotto la riga, costruita da un modulo del nucleo `phases.py` (id, titolo, numero, gruppi e comandi, ispettore, aree delle verifiche, domande di Meridio), così `window.py` smette di ragionare con `index == 0` e `TABS[index]` ([V] `_tab_changed`, `_show_inspector`). La preferenza «Strumenti: in alto / a sinistra» (B2) resta come variante: a sinistra, solo icone, i gruppi come separatori.

L'altezza della barra è la scelta aperta 5.3.

### 3.4 Le viste

- **Dentro ogni vista, in alto a sinistra, la sua barra** (R27 [D]): Pianta, 3D, Affiancate come selettore a tre; Inquadra; nella pianta anche agganci (F3), orto (F8) e il menu Sfondo (R21 [D]). Vedi la contraddizione C6 per la convivenza con la barra della fase.
- **Pianta**: freccia del nord in alto a destra, barra di scala 1-2-5 in basso a sinistra, fonte dello sfondo in basso a destra (studio 12, 6 [D]; fatti in fase 2); contorno tratteggiato sotto il cursore; quote e misura rapida nella barra di stato; dal 16c i moduli e le file come oggetti; dal 16d le stringhe colorate con il semaforo.
- **3D**: il cubo in alto a destra con Alto, N, E, S, O, frecce, bussola, Home e menu (fatto); la barra del sole sotto (giorno, ora, riproduzione; [P] «vista dal sole» come voce del cubo e della palette, studio 12, 6); il mirino a tre anelli del perno (16g [D]); il gizmo di Sposta e Ruota (16b [D]).
- **Colori**: pianta e 3D hanno colori propri, uguali nei due temi (R16 [D]); l'ortofoto sempre velata (40 % predefinito); il fondo senza foto è lo stesso grigio scuro #2b2f33 (registro, ultima decisione del 23/10 [D]; la riga dello studio 13, 3.7 e di `funzionalita.md` sul fondo chiaro è superata: il chiaro resta nel codice per una preferenza futura); selezione magenta con il contorno a nastri e il passaggio in magenta chiaro (R29 [D]); tratti e contorni «con un buono spessore» (R35, da tarare sulle schermate [D]).
- **Navigazione**: gli stili di FreeCAD più «AutoCAD» e «SketchUp», predefinito AutoCAD (registro 23/10 [D]), spiegati in Preferenze > Navigazione (fatto).

### 3.5 Il pannello Progetto (T2) [D]

Sezioni con intestazione in maiuscoletto attenuato e conteggio (EDIFICI · 2), 8 px d'aria sopra, la freccina per aprire e chiudere, i conteggi dei moduli attenuati accanto al nome, i segni delle verifiche come pillole leggibili (✘ 1, ⚠ 2) che filtrano le Verifiche al clic (R30 [D]). [P] Sezioni per fase: nel Modello EDIFICI, SOTTOCAMPI, ESCLUSIONI, IMMAGINI; nell'Impianto anche INVERTER e STRINGHE; nella Relazione i capitoli. Menu contestuale come oggi (Proprietà, Inquadra, Posa o Togli, Rinomina, Duplica, Squadra, Elimina). [P] Il menu a discesa dell'Annulla con i nomi dei passi (studio 15, 3.5, voto 4) al posto del pannello Cronologia proposto nello studio 12 (N1), che non è mai nato.

### 3.6 Il pannello Proprietà

- **Campi C2** [D]: velo tonale (in scuro il nero al 22 %), bordo di 1 px a 3:1 o più, a fuoco il bordo d'accento di 2 px, numeri allineati a destra; i campi con unità e aritmetica che ci sono già.
- **Pulsanti C2** [D]: tonali senza bordo; un solo pulsante pieno d'accento per fase (Posa i moduli nel Modello, Calcola in Producibilità e in Bilancio); «Svuota» tonale con il testo nel colore degli errori.
- **Gruppi C3** [D]: cornice e intestazione piena per Sottocampo, Distanze e margini, Risultato della posa e gli altri; [P] cornice di 1 px `line` (non 1,5) e raggio 6 dentro la scheda A3, per la regola di profondità della 3.2.
- **L'ispettore per fase** (studio 12, N2, strada B [D]): nel Modello e nell'Impianto le Proprietà; in Producibilità, Consumi e Bilancio le cifre della variante; nella Relazione gli Elaborati. Il titolo del pannello cambia (Proprietà, Risultati, Elaborati), il pannello no; Ctrl+P lo mostra e lo nasconde (era Ctrl+1 fino al 24/10/2026) [D].
- **Il riquadro d'aiuto E3** [D] (registro 23/10: «confermato come riquadro in fondo alle Proprietà»): in fondo al pannello di destra, in ogni fase; spiega il campo che ha il fuoco o il riquadro di risultato sotto il mouse; tre righe al massimo con la fonte e i tre collegamenti (Manuale, Come è calcolato, Chiedi a Meridio); si chiude e si riapre; i «?» accanto ai titoli dei gruppi e ai riquadri dei risultati lo aprono sul punto giusto (E1 come scorciatoia, non come secondo sistema). I testi in `help.py` (17d). Lo spazio che costa è la contraddizione C3.
- **Selezione multipla** [P, studio 12a 4.7]: proprietà comuni, «varia» dove differiscono, filtro per tipo con il numero.

### 3.7 I risultati (R2) e i grafici (D2)

- **R2** [D]: schede piene senza bordi, il numero chiave nel velo d'accento, l'unità piccola, la fonte e «Come è calcolato» sotto; in scuro reggono solo con il token `card` più chiaro del pannello (studio 17, C.5 [V]).
- **D2, pyqtgraph** [D] «forse», dipendenza accettata nella bozza 17c: mirino con la lettura dei valori, legenda che accende e spegne, zoom con la rotella e il trascinamento sugli orari, doppio clic che inquadra, «Tabella» che resta, esportazione SVG e PNG, il tema applicato (fondo, assi, griglia, Titillium Web, le serie dai token). La relazione resta a matplotlib (`report.py`). Quali interazioni contano è la scelta aperta 5.2.

### 3.8 Il pannello Verifiche (F2) [D]

- Un pannello in basso in tutte le fasi, Ctrl+J; Ctrl+Maiusc+M ci porta la tastiera e le frecce scorrono con le viste che seguono; Ctrl+. applica «Correggi» (studio 12, 5 [D]).
- **Per livello** come vista predefinita (F2 [D]): sezioni DA CORREGGERE, DA CONTROLLARE, DA SAPERE, SUPERATE (chiusa), con i conteggi; per oggetto e per area dal menu nella testa; la frase breve con il dettaglio a richiesta (che cosa, perché, che cosa fare: il campo `detail` di 17e); «Correggi» e l'occhio sulla riga; la fonte con il nome di `rules.py`.
- [P] Con le sezioni per livello i quattro pulsanti di filtro per livello diventano doppi (lo nota lo stesso studio 17, F.4): i conteggi nella testa del pannello e nella barra di stato portano alla sezione; i filtri restano «per fase» («Solo questa fase») e «per oggetto» (dal segno sull'albero, R30), che sono le due domande vere.
- [P] Nella fase Relazione il pannello ha il modo «pronto per la consegna» (2.7).

### 3.9 Meridio

- [D] Un personaggio solo per la finestra, fluttua sopra le viste, si clicca per un parere, si sposta da solo con la fase e ricorda il posto trascinato (studio 14, 7.3); Ctrl+L apre con il cursore nel campo, Esc torna al personaggio; nella barra di stato il personaggio piccolo con il nome; tre domande pronte per fase.
- [D] Le animazioni di G2 (raggi lenti, un giro al minuto, fermi dopo qualche secondo con la chat chiusa; la chat che scivola; il testo che scorre quando arriverà lo streaming) con battito di ciglia, piccoli movimenti e smorfie casuali; le domande numerate di G3 scelte con 1, 2, 3; la base G3 con «meno movimento» (registro 23/10; R15).
- [D] R33: mai coperto dalla chat; la chat come fumetto con la coda verso il personaggio; la faccia nel tema chiaro oggi troppo scura. [D] R34: una versione pixelata. [D] R17: agganciabile nei pannelli laterali, con la stessa conversazione.
- [P] Regole del fumetto: si apre dal lato libero del personaggio (verso il centro della vista), mai sopra la selezione, il punto in disegno, le finestre di dialogo, i pannelli flottanti degli inverter (16d); se non c'è posto, il personaggio scivola nell'angolo libero e poi apre; ridimensionabile dall'angolo opposto alla coda (`QSizeGrip`), misura ricordata; agganciato nei pannelli il fumetto non c'è: il personaggio sta in testa al pannello e la conversazione sotto (già così, R17).
- [P] La versione pixelata è uno stile del personaggio in Preferenze > Assistente (liscio o pixel), stessa macchina a stati; nel pixel i raggi non girano per gradi ma a scatti di 8 fotogrammi predisegnati, altrimenti sfarfallano a 46 px.

### 3.10 La barra di stato

Come oggi [V]: il suggerimento dello strumento a sinistra; a destra il lavoro in corso, i conteggi «da correggere» e «da controllare» cliccabili, la misura rapida della selezione, le coordinate con la quota, il pulsante di Meridio. [P] La barra di avanzamento con Annulla per PVGIS e PDF (16f [D]) sta qui; il suggerimento e i messaggi temporanei non si coprono (studio 12, N8): i messaggi a destra del suggerimento.

### 3.11 Tastiera, mouse, palette

La mappa è quella dello studio 12, sezione 5 [D], con M Sposta e D Misura (studio 16 [D]), Ctrl+Maiusc+R per la revisione [D], Ctrl+L per Meridio (studio 14 [D]); l'editor delle scorciatoie con i conflitti c'è già. [P] La palette dei comandi (Ctrl+Maiusc+P [D], ancora ○ in `funzionalita.md`) elenca comandi, oggetti del progetto, fasi, impostazioni e gli alias di AutoCAD (ZE, ZW, ZP), e se il testo non è un comando propone «Chiedi a Meridio: …» (studio 14, 7.2). Il contesto da tastiera: le lettere singole in tutta la finestra tranne nei campi di testo [D].

### 3.12 Le attese e gli stati (16f [D])

Niente sotto 300 ms; l'arco nella zona che aspetta (pianta durante la posa, pagina durante il calcolo, catalogo alla prima lettura); i valori vecchi in grigio con il segno nel titolo della fase («Producibilità ·»); lo scheletro solo per la 3D all'avvio; barra con percentuale e Annulla solo per PVGIS e PDF; mai una finestra modale; tutto fermo con «meno movimento».

### 3.13 Il tema

Direzione «Meridiana» (studio 13 [D]), stile Fusion ovunque, palette calcolata dal colore scelto, bronzo di partenza [D], fondi Meridiana, Titillium Web, icone Lucide; il tema vale per finestre, pannelli, campi, pulsanti, barre, cubo, Meridio e grafici; non per pianta e 3D (R16 [D]). I token nuovi: `card`, `field`, `field_line` (17a).

## 4. Le contraddizioni e la via proposta

| N. | Contraddizione | Fonti | Via proposta [P] |
|---|---|---|---|
| C1 | **B4 con il testo sotto le icone** contro **R19 «solo icone», forse predefinito** (fatto nei ritocchi, passo 3, impostazioni versione 7) e contro lo studio 13 (regola 5: icona con il testo accanto) | registro 23/10 B4 seconda risposta; R19; studio 13, 3; `fase-2-ritocchi.md` passo 3 | La decisione più recente vince: nella barra della fase il testo sotto le icone è il predefinito; l'opzione «Testo sotto le icone» nel menu Vista e in Preferenze > Aspetto la porta alle sole icone; su un fianco e nelle barre delle viste sempre solo icone. La preferenza «Barra degli strumenti: solo icone / icone e testo» dei ritocchi cambia significato (etichette sotto sì o no) con una migrazione delle impostazioni; «icone e testo accanto» non esiste più |
| C2 | **A3, pannelli come schede** con dentro i **gruppi C3 a cornice** e i **campi C2 con il bordo**: tre contorni annidati, il «busy» che Apple e lo stesso studio 17 (C.4) sconsigliano | registro 23/10 (A3, C3, C2); studio 17, A.4, C.3, C.5 | Regole di profondità (3.2): raggi 8, 6, 4; una sola linea di 1 px per livello; la cornice del gruppo in `line`, non in `text2`; nessuna scheda dentro una scheda; i riquadri R2 fuori dai gruppi. Da guardare sulle schermate di 17a prima di chiudere 17a |
| C3 | **E3 fisso in fondo alle Proprietà** contro lo **spazio**: 70-90 px sempre (studio 17, E.4), sopra una colonna che con A3 perde 16-24 px in larghezza e con B4 70 px in altezza; il modulo Sottocampo scorre già (studio 12, K1) | registro 23/10 (E3 «forse», poi riquadro confermato); studio 17, E.4; studio 12, K1 | Il riquadro c'è ma si piega: al massimo tre righe più il titolo (circa 64 px), richiudibile con lo stato ricordato, si nasconde da solo se il pannello è più basso di 480 px e allora i «?» aprono lo stesso testo come riquadro a comparsa (E1); il testo segue il fuoco nel pannello, non in tutta la finestra (il fuoco che salta con Tab lo cambierebbe a ogni tasto) |
| C4 | **G2, raggi che girano** contro **«meno movimento»** e le fonti dello studio 17 (G.3: il movimento continuo in periferia distrae); Daniel stesso: «sì, meglio come dici tu» | registro 23/10 (G2); R15; studio 17, G.3, G.6 | Raggi a un giro al minuto, fermi dopo pochi secondi con la chat chiusa e sempre fermi con «meno movimento» o con «Meridio animato» spento; le smorfie a cadenza lenta (una ogni uno o due minuti); da provare un'ora di lavoro sul PC prima di chiudere 17f |
| C5 | **I gruppi «Sole» e «Sfondo» nella barra B4** contro **R27 «ciò che riguarda le viste sta nelle viste»** (barra del sole sotto la 3D, menu Sfondo nella barra della pianta, R21, fatti) | studio 17, B.4 (bozzetto B4); R21, R27; ritocchi passi 2 e 6 | Niente gruppi Sole e Sfondo nella barra della fase: restano nelle viste; il giorno e le ore di progetto restano nelle Proprietà (Passo dal sole); la barra della fase porta solo ciò che agisce sul progetto |
| C6 | **La barra della vista in alto a sinistra** (R27, «barra delle viste in alto a sinistra» fra i punti accettati) sotto la **barra della fase B4**: due barre impilate nello stesso angolo | registro 23/10 (punti lasciati dai ritocchi); R27; B4 | Tenere l'alto a sinistra come deciso, ma su superfici diverse: la barra della fase sul fondo della finestra a tutta larghezza, la barra della vista dentro la scheda della vista (A3) con 8 px di rientro, icone più piccole (16 px) e fondo semitrasparente. In più una schermata di confronto con la barra della vista in basso a sinistra (Revit, Fusion), accanto alla barra di scala: la scelta è di Daniel |
| C7 | **Ctrl+?**: nello studio 12 e in `funzionalita.md` è l'elenco delle scorciatoie (fatto); la bozza 17d lo dà al riquadro d'aiuto | studio 12, 5; `funzionalita.md` A; `17d-aiuti.md` | Ctrl+? resta alle scorciatoie. Il riquadro d'aiuto si apre con F1 sul campo che ha il fuoco (è «guida» ovunque e contiene «Chiedi a Meridio», che chiude anche l'alias F1 dello studio 14, 7.2) e con Maiusc+F1 come «Che cos'è?» sul puntatore |
| C8 | **Le fasi numerate 1-6** suggeriscono Ctrl+cifra, ma Ctrl+1 e Ctrl+0 sono pannelli e Ctrl+Maiusc+2/3 le viste [D] | studio 12, 5; B4 | Superata il 24/10/2026 (R52): Ctrl+1…6 aprono le fasi, Proprietà passa a Ctrl+P |
| C9 | **F2 per livello** più i **quattro pulsanti di filtro per livello** (ritocchi passo 9) e i **conteggi** nella barra di stato: lo stesso filtro in tre posti | registro 23/10 (F2); studio 17, F.4; ritocchi passo 9 | Le sezioni assorbono i filtri per livello (3.8); restano i filtri «questa fase» e «questo oggetto» |
| C10 | **La scheda Impianto con l'elenco degli inverter «a destra»** (bozza 16d) contro **una sola disposizione, il pannello di destra cambia con la scheda** (studio 12, N2 strada B [D]) | `16d-impianto-e-stringhe.md` passo 3; studio 12, 4.5 | L'elenco degli inverter è l'ispettore della fase Impianto nel pannello di destra; i pannelli per inverter (R12) galleggiano sopra la pianta solo nella modalità di stringatura |
| C11 | **Fondo della pianta senza ortofoto**: chiaro nello studio 13 (3.7) e in `funzionalita.md`, grigio scuro #2b2f33 nell'ultima decisione | studio 13, 3.7; `funzionalita.md` A; registro 23/10 ultima riga | Non è una contraddizione da risolvere: vale la decisione; da aggiornare studio 13 e `funzionalita.md` nel primo compito che tocca la pianta |
| C12 | **R33 «chat come fumetto»** contro **R17 «agganciabile nei pannelli»** e contro i posti fissi per fase dello studio 14 | R17, R33; studio 14, 7.3 | Due modi, già così: flottante con il fumetto, agganciato senza; i posti per fase restano quelli del personaggio, il fumetto si apre dal lato libero (3.9) |
| C13 | **R12 pannelli flottanti per inverter** sopra la pianta contro **B3 «una sola barra galleggiante per vista»** (studio 17, B.6) e contro Meridio flottante nello stesso spazio | R12; studio 17, B.6; studio 14, 7.3 | I pannelli degli inverter esistono solo nella modalità di stringatura, in colonna sul lato destro della pianta; Meridio in quella modalità va nell'angolo in basso a sinistra |

## 5. Le tre scelte ancora aperte

### 5.1 Il manuale: nel repository o in rete [P: nel repository, letto dentro il programma]

- In `docs/manuale/`, un capitolo per fase, in Markdown, con le àncore che `help.py` usa e che un test controlla (17d).
- Aperto **dentro Meridiana** (un `QTextBrowser` con `setMarkdown`, Aiuto > Manuale e i collegamenti del riquadro d'aiuto), non con `QDesktopServices` su un file `.md`: su Windows l'associazione dei `.md` è casuale (lo stesso dubbio in 17d, «da lasciare alla sessione locale»).
- Motivi: funziona senza rete (il modello locale di Meridio legge il manuale e lo cerca sul disco, studio 14, passo 4); versionato con il codice, quindi le àncore non si rompono; il repository è privato e la pagina in rete non esiste ancora. Quando il repository sarà pubblico, gli stessi file si pubblicano in rete (GitHub Pages) e «Manuale in rete» diventa una seconda voce.

### 5.2 Quali interazioni dei grafici contano di più [P, in quest'ordine]

1. **Il valore al passaggio**, con tutte le serie del grafico: il progettista legge i numeri per scriverli nella relazione e nelle mail; è l'interazione che oggi manca del tutto (R23) e costa 2-4 ms con pyqtgraph.
2. **La legenda che accende e spegne**: serve per confrontare Meridiana e PVGIS, le varianti, le voci della catena.
3. **Lo zoom solo sulle serie orarie e settimanali** (rotella sull'asse x, rettangolo, doppio clic per tornare): sui dodici mesi non serve.
4. **L'esportazione in SVG e PNG** con il tema chiaro, per la relazione e per le mail.
5. Più avanti: il clic su un'ora che mostra le ombre di quel momento nel 3D (studio 12, 6; OpenSolar).

«Tabella» resta: è la via da tastiera e per copiare i numeri.

### 5.3 L'altezza della barra della fase con il testo [P: 68 px con le etichette dei gruppi, 44 px senza testo]

- Con il testo: icone di 24 px, etichetta di una riga a 12 px, 6 px di aria, poi l'etichetta del gruppo a 11 px sotto: 68 px (il bozzetto ne usa 76 con il margine). Mai etichette su due righe: i nomi lunghi si accorciano («Edif. modello» no: «Modello», con il nome intero nel suggerimento).
- Senza testo: icone di 22 px, i gruppi come separatori con l'etichetta del gruppo che resta a 11 px (è la parte che spiega): 44 px.
- La barra passa da sola alle sole icone quando l'altezza utile della finestra scende sotto 900 px (il portatile e una colonna di Niri), come fa la NavigationView di WinUI con la larghezza; la preferenza può forzare l'uno o l'altro.
- Il conto sullo schermo del portatile (circa 1000 px logici): menu 28, fasi 34, barra 68, stato 24, Verifiche 200: restano circa 650 px per le viste, che con le sole icone diventano 674. Sullo schermo verticale di Daniel (1920 px) non c'è problema.

## 6. Che cosa si tiene, che cosa si rifà, in che ordine

### 6.1 Si tiene (è già giusto o costa poco adattarlo)

- La struttura `QMainWindow` con i pannelli agganciabili (Progetto, Proprietà, Verifiche, Meridio agganciato) e il `QTabWidget` centrale, che diventa la riga delle fasi.
- Le barre dentro le viste (R27), la freccia del nord, la scala, il cubo, gli stili di navigazione, la macchina di stati del mouse, la camera.
- Il registro delle scorciatoie con l'editor e i conflitti; i campi con unità; il catalogo a modello con l'ordinamento.
- Il tema (Fusion, palette dal colore, Titillium Web, icone Lucide) e `theme_colors`; i colori propri di pianta e 3D.
- Il modello delle verifiche (`checks.Item`, conteggi, `about`, `show_related`), i segni sugli oggetti e sull'albero, «Correggi».
- L'annulla a istantanee, i lavori in thread con la generazione, il salvataggio automatico, le varianti e le revisioni.
- Il contenuto delle pagine energetiche (i gruppi e i grafici che ci sono), «Come è calcolato», il guscio di Meridio (un widget solo, i posti per fase, Ctrl+L), `report.py` come base della fase Relazione.

### 6.2 Si rifà (sopra la stessa base)

1. La barra degli strumenti: da barra del `QMainWindow` a barra della fase con i gruppi (B4).
2. Le superfici: schede A3, token `card`, `field`, `field_line`; i gruppi C3, i campi e i pulsanti C2, i riquadri R2; l'albero T2.
3. Il pannello Verifiche: sezioni per livello, dettaglio, «Correggi» e occhio sulla riga.
4. Il riquadro d'aiuto E3 e i «?»; i testi in `help.py`; il manuale.
5. I grafici su pyqtgraph.
6. Meridio: fumetto, animazioni, domande numerate, versione pixel, la faccia in chiaro.
7. La fase Impianto (nuova) e la fase Relazione (nuova), con l'ispettore per fase da `phases.py`.
8. La relazione e gli elaborati (sezione 7).

### 6.3 L'ordine proposto [P]

| Ordine | Compito | Perché qui |
|---|---|---|
| 1 | 17a superfici e controlli (A3, T2, C2, C3, R2) | Tutti gli altri disegnano sopra queste superfici e questi token (studio 17, domanda 8, non contestata) |
| 2 | 17b, riscritto: fasi e barra della fase, `phases.py`, la fase Relazione come guscio | 16b, 16c, 16d aggiungono strumenti e una fase: senza la barra della fase si costruirebbero due volte |
| 3 | 16d Impianto | La cosa che Daniel non ha trovato (studio 16, piano); usa la fase e l'ispettore del punto 2 |
| 4 | 16a tetti, poi 16b sposta e ruota, poi 16c posa manuale | L'ordine dello studio 16 (A prima perché più rischioso; C dopo B) |
| 5 | 17e Verifiche, 17d aiuti, 17f Meridio, in parallelo con il punto 4 dove i file sono diversi | Dipendono solo da 17a |
| 6 | 17c grafici | Indipendente; per ultimo perché la dipendenza è «forse» |
| 7 | 16e filtri, 16f attese, 16g perno | Brevi, in parallelo quando capita |
| 8 | Fase Relazione piena (sezione 7) e 14 Meridio che risponde | Dopo lo studio 16, come deciso per il 14 (registro 23/10) |

### 6.4 I compiti, uno per uno

| Compito | Verdetto | Che cosa cambia e perché |
|---|---|---|
| 16a tetti a falde | confermato | Solo nomi: «Edificio da modello…» nel gruppo Disegna della barra della fase e nel menu Disegna; il gruppo Tetto nelle Proprietà con lo stile C3 |
| 16b sposta e ruota | confermato | Sposta e Ruota nel gruppo Modifica; la «R» dentro Sposta è contestuale (R fuori dal comando resta il rettangolo): va scritto nel suggerimento |
| 16c posa manuale | confermato, da modificare | Lo strumento Fila nel gruppo Disegna; lo stato «file a mano» visibile nel Risultato della posa e come voce da sapere nelle Verifiche; il tasto della Fila va fissato nel registro delle scorciatoie (L è libera) |
| 16d impianto e stringhe | confermato, da modificare | La fase è la 2 della riga; l'elenco degli inverter nell'ispettore di destra (C10); i pannelli per inverter solo nella modalità di stringatura (C13); `_show_inspector` e `TABS` passano da `phases.py` (si fa nel 17b riscritto) |
| 16e filtri del catalogo | confermato | Nessun cambiamento: è una finestra a sé |
| 16f attese | confermato | Il segno «da aggiornare» va sul titolo della fase nella riga delle fasi; l'arco sulla pianta e nelle pagine come scritto |
| 16g perno della 3D | confermato | Nessun cambiamento |
| 17a superfici e controlli | da modificare | È già riscritto su A3, T2, C2, C3, R2; aggiungere le regole di profondità (3.2 e C2), le viste arrotondate, lo spazio riservato al riquadro d'aiuto, le intestazioni delle Verifiche con lo stesso delegato di T2 |
| 17b strumenti | da sostituire | I passi sono scritti su B1 e il blocco «Deciso» dice B4: va riscritto da capo come «fasi e barra della fase»: `phases.py` nel nucleo, `QStackedWidget` di barre, gruppi con le etichette, testo sotto le icone con l'opzione e il passaggio automatico sotto 900 px, «Variante» nell'angolo, la fase 6 come guscio, Sole e Sfondo fuori (C5), la variante «a sinistra» a sole icone, la migrazione della preferenza dei ritocchi (C1) |
| 17c grafici | confermato | Aggiungere l'ordine delle interazioni (5.2); «clic sull'ora, ombre nel 3D» in coda |
| 17d aiuti | da modificare | Il blocco «Deciso» dice E3 ma i passi costruiscono E1: riscrivere il passo 3 sul riquadro in fondo al pannello di destra con le regole di C3; F1 e Maiusc+F1 al posto di Ctrl+? (C7); il manuale letto dentro il programma (5.1); i testi di `help.py` restano |
| 17e verifiche | da modificare | Il blocco «Deciso» dice F2 ma i passi costruiscono F1: la vista predefinita per livello con le sezioni; i filtri per livello tolti (C9) e sostituiti da «questa fase» e «questo oggetto»; il modo «pronto per la consegna» per la fase 6 |
| 17f Meridio | da modificare | Il blocco «Deciso» è già G2 + G3 + R33 + R34: i passi 2, 3 e 5 vanno riscritti sul fumetto con la coda, i raggi lenti che si fermano, le smorfie casuali, le domande numerate, lo stile pixel come preferenza; in più la faccia in chiaro (R33) |
| 14 Meridio che risponde | confermato | Dopo lo studio 16 [D]; il testo che scorre nel fumetto, «Ferma», «Chiedi a Meridio» dal riquadro d'aiuto e dalle righe delle Verifiche |

## 7. Gli elaborati

### 7.1 Che cosa produce oggi `ui/report.py` [V]

Un documento HTML impaginato da `QTextDocument` e stampato in A4 con `QPdfWriter` a 300 dpi, con i grafici disegnati da matplotlib a 200 dpi (chiari anche con il tema scuro):
1. titolo del progetto, variante con la nota, indirizzo e coordinate, «Relazione fatta da Meridiana v il giorno»;
2. Produzione: potenza STC e AC, energia annua, resa specifica, PR, PVGIS come secondo parere; il grafico mensile (Meridiana e PVGIS); il diagramma della catena delle perdite con le percentuali;
3. Stringhe (CEI 64-8/7): moduli in serie e stringhe per ingresso, la tabella delle verifiche con il segno, l'elenco delle stringhe (nome, sottocampo, numero di moduli);
4. Consumi: annuo e per fascia F1, F2, F3 con la base dei dati;
5. Bilancio ed economia: autoconsumo, autosufficienza, immissione, risparmio, vendita e incentivi, investimento, VAN, TIR, ritorno, costo livellato; il grafico del flusso di cassa cumulato;
6. Taglia dell'impianto e dell'accumulo: le due tabelle;
7. Verifiche: segno, area, testo, fonte;
8. Note per la relazione tecnica: i paragrafi delle regole con la fonte (`rules.notes`);
9. Come è calcolato: i record con le formule in immagine, i valori e le fonti;
10. Valori ancora predefiniti: la tabella finale.

### 7.2 Che cosa manca per una relazione da consegnare

| Manca | Che cosa serve | Da dove | Fatica [P] |
|---|---|---|---|
| Intestazione e committente | Progettista, committente, indirizzo del sito, data, numero di revisione, logo (studio 08, checklist 7) | fase 6, campi del progetto | S |
| Indice e numeri di pagina, capitoli a scelta | Le caselle dei capitoli, l'indice in testa | `report.py` | S |
| Il modello | Elenco edifici e falde (pendenza, azimut, area, tipo di tetto), ostacoli ed esclusioni con le altezze e le fasce; la pianta con i moduli e il 3D come immagini | fase 1, «Salva immagine» | M |
| Elenco moduli e stringhe | Per sottocampo: modello, numero, kWp; per inverter e ingresso: ogni stringa con i moduli nell'ordine (il codice inverter.ingresso.stringa.modulo che i programmi di riferimento usano su tavole ed etichette, studio 05, 5.15); i moduli fuori stringa | 16d | M |
| Inverter | Modello, quantità, MPPT e ingressi, rapporto DC/AC, verifiche per ingresso con le temperature usate | 16d | S |
| Tabella delle perdite | Per ogni voce della catena i kWh e la percentuale (oggi solo il diagramma), con la fonte di ogni valore | `simulate.py` | S |
| Ombre | Tabella dei fattori d'ombra (esiste), diagramma di iso-ombra (○), l'elenco degli ostacoli con la perdita | fase 3 | M |
| Consumi | Diagnosi: per mese e fascia, carico di base, settimana media, durata (esistono nei grafici, non nel PDF) | fase 4 | S |
| Economia | I flussi anno per anno in tabella, le ipotesi (prezzi, tasso, detrazione) con la fonte | fase 5 | S |
| Verifiche con le fonti | Il dettaglio (perché, che cosa fare) di 17e; le fonti con articolo e pagina dove `rules.py` le ha | 17e | S |
| Confronto delle varianti | La tabella del confronto nel PDF (oggi solo nella finestra) | `compare.py` | S |
| Schema unifilare | Dall'impianto: moduli e stringhe per ingresso, inverter, quadri DC e AC, contatore, SPI e DDI; in SVG e DXF | 16d, fase 6 | L |
| Disegni DXF | Pianta con edifici, falde, esclusioni, moduli, stringhe, quote, fasce VVF, su layer con lo standard di layer dell'ufficio (studio 05, 5.8) | fase 6 | M |
| IFC4 | Il prototipo dello studio 15 (5.2): sito georiferito, edifici, falde, 188 moduli con i Pset; serve ifcopenshell (decisione aperta) | fase 6 | M (3-4 giorni) |
| Serie orarie | CSV delle ore (produzione, consumo, immissione, prelievo, batteria) | fase 6 | S |
| Allegati per distributore, GSE, Comune, VVF | I dati dell'impianto nel formato dei modelli ufficiali; i contenuti si leggono dai modelli e dalle norme nell'archivio di Daniel (tema F della revisione) | fase 6 | da studiare |
| Esportazione verso PVsyst | Scena 3D, PAN e OND, foglio dei parametri (studio 08, F25) | fase 6 | L |

### 7.3 Come la fase Relazione li tiene insieme [P]

- Ogni elaborato ha una voce nell'ispettore «Elaborati» con lo stato: fatto (con la data), da rifare (il progetto è cambiato dopo: la stessa generazione dei risultati di 16f), non disponibile (con il motivo: «nessun inverter scelto»).
- La relazione si compone dai capitoli; i capitoli vengono dalle fasi e usano gli stessi record del pedigree; i grafici del PDF restano quelli di matplotlib, chiari, come oggi.
- Le immagini di pianta e 3D si rifanno a ogni esportazione dalle viste (stesse inquadrature salvate con il progetto).
- Un'esportazione scrive accanto al progetto una cartella con il nome del progetto e la revisione; mai sopra un file esistente senza chiederlo (regola di Daniel).

## 8. Il confronto con i programmi di riferimento, sui percorsi

| Programma | Il suo percorso | Che cosa Meridiana prende o evita |
|---|---|---|
| PVsyst 8 | Progetto e sito, meteo, orientamento, sistema (modulo, inverter, stringhe proposte), scena 3D, module layout, simulazione, relazione; una perturbazione per variante e il confronto dei diagrammi delle perdite (studio 08, 2.0) | Il modello unico toglie le quattro coerenze da rifare a mano; le fasi 1-2 fanno orientamento, sistema, scena e layout insieme; le varianti e «Confronta» riproducono il metodo «una perturbazione alla volta»; da evitare gli avvisi da nascondere (08, F7): qui hanno «Correggi» |
| Aurora | Modalità di progetto: sito e tetto, ostruzioni, moduli, sistema (inverter, stringhe trascinate), simulazione, proposta; verifiche a colori che non bloccano | Le fasi 1, 2, 3, 6; le stringhe trascinate sui moduli e il semaforo; le criticità nelle viste |
| HelioScope | Quattro passi numerati: sito, layout meccanico, progetto elettrico, simulazione e rapporto | È il modello più vicino a B4: passi numerati che restano sempre apribili |
| PV*SOL premium | Pagine in sequenza a sinistra: tipo di impianto, clima, consumi, moduli e 3D, inverter, cavi, perdite, simulazione, risultati e relazione | Lo stesso ordine delle fasi, con i consumi dopo la producibilità invece che prima; gli spigoli numerati e il codice unico dei moduli per gli elaborati |
| DIALux evo | Modi sopra la vista CAD (Project, Construction, Light, Calculation objects, Export, Documentation), strumenti a sinistra, risultati a destra | L'origine di B4 e della fase Relazione («Documentation»); lo strumento che spiega i suoi passi nel pannello |
| FreeCAD | Workbench per compito, pannello attività con OK e Annulla, albero del documento, ricalcolo dei soli oggetti toccati | Le fasi sono i workbench con un ordine; il pannello attività per gli strumenti a più passi (studio 15, 3.1) è ancora da fare; la palette dei comandi è dove Meridiana può fare meglio |
| Revit | Ribbon per disciplina con le schede contestuali, barra delle opzioni dello strumento, View Control Bar sotto la vista, Proprietà e Browser di progetto | La barra della fase è la ribbon con i gruppi; la barra della vista; i due pannelli laterali; «Show Related Warnings» è il clic sul segno dell'oggetto |

## 9. Fonti

- `docs/richieste.md`: tabella «Decisioni prese» (22/10 e 23/10) e richieste R12-R36.
- `docs/studio/12-revisione-ux-prestazioni.md` (sezioni 5, 6, 7), `12a-convenzioni-ux.md` (1.11, 2.10, 3.5, 4.7, 5.6).
- `docs/studio/13-studio-estetico.md` (sezioni 3, 7, 11, 12), `14-assistente-agente.md` (1, 7, 9), `15-freecad-riferimento.md` (2.6, 3, 6, 7), `16-modellazione.md` (A-G e il piano), `17-interfaccia.md` (A-G e il piano), `05-stato-dell-arte-ux.md`, `05a-disegno-cad-dettaglio.md` (7, 8), `08-pvsyst-tutorial-e-flussi.md` (0.4, 2.0, 4, 5).
- `docs/studio/17-prove/*.html` (i bozzetti A-G), `docs/funzionalita.md`, `docs/progetto.md`.
- `docs/compiti/16a-g`, `17a-f`, `14-assistente-prototipo.md`, `fase-2-ritocchi.md`.
- `src/meridiana/ui/window.py` (menu, barra, pannelli, fasi, barra di stato, `_tab_changed`, `_show_inspector`), `ui/inspector.py`, `ui/report.py`, `ui/energy_pages.py` e `ui/properties.py` (i gruppi), `checks.py` (`area_names`).
