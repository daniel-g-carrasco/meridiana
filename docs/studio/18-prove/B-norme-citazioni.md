# B6. Le citazioni normative nel codice di Meridiana, verificate sull'archivio locale

Prova della sezione B (correttezza dei calcoli) dello studio 18, tema B6: ogni citazione di norma, legge, delibera o documento tecnico presente in `src/meridiana` e in `po/it.po`, confrontata con il testo della fonte nell'archivio `l'archivio locale delle norme` (norme CEI in `standards\cei`, leggi in `laws`, TuttoNormel in `publications\tuttonormel`). Verifica fatta il 23/10/2026 sul ramo `revisione-completa`, senza modifiche al programma e all'archivio.

Marche: **[V]** verificata sul testo (frase della norma, articolo, pagina del PDF nel nome del file); **[X]** sbagliata o imprecisa (con quello che dice davvero la fonte); **[?]** non verificabile in locale (documento o pagina assente); **[I]** dedotta, cioè una lettura mia che il testo non dice con quelle parole.

## 0. Metodo

- Inventario: `rg` su `src/meridiana` e `po/it.po` con le parole CEI, D.Lgs, DM, DCPREV, ARERA, GSE, UNI, IEC, EN, NTC, Terna, TICA, RIGEDI, PVGIS, Codice, TNE, Allegato, Tabella. Esclusi i dati di catalogo (`catalog/data/*.json`: certificati di prodotto dichiarati dai costruttori, non verificabili qui).
- Ricerca nel testo e lettura delle pagine con `python "C:/Users/utente/Elettrico/reference/tools/cerca_norme.py" "<parole>" --in "<file>"` e `--leggi "<file>" --pagine <n>` (con `PYTHONIOENCODING=utf-8`, altrimenti lo strumento si ferma sui caratteri fuori cp1252: trappola da annotare). Le due tabelle dei livelli di tensione (CEI 0-21 Tab. 5, CEI 0-16 Tab. 4) sono state anche rese in immagine con PyMuPDF e lette a video, perché il testo estratto ne perde le righe.
- Edizioni usate (le più recenti in archivio): CEI 0-21:2026-07 (338 pag.), CEI 0-16:2026-07 (628 pag.), CEI 64-8 9a ed. 2024-07 (parti `_1` e `_7`), CEI 82-25/1:2026-03, CEI 82-25/3:2026-01, DM 37/2008 testo integrato con il DM 130/2025 (copia TuttoNormel, 12 pag.), DCPREV 14030 del 01/09/2025 (scansione con OCR imperfetto: letta per pagine intere), D.Lgs. 199/2021 testo vigente Normattiva al 22/10/2026 e D.Lgs. 5/2026 (GU n. 15 del 20/01/2026), D.Lgs. 190/2024 testo vigente al 21/10/2026, ARERA 385/2025/R/eel, ARERA 181/06 Tabella 1, DGR Lombardia XII/6153/2026 e XII/6645/2026, allegato al decreto Lombardia 6437/2026, L.R. Lombardia 11/2026, DM MASE 414/2023, Regole operative GSE CACER del 16/07/2025, TNE 2026-01. Il Codice di prevenzione incendi non è in `reference`: per il punto S.10.6.2 ho letto la copia `Codice-prevenzione-incendi_10.6.pdf` su `<archivio aziendale>\LIBRERIE Antincendio\Normativa\Legislazione Italiana\_Codice di Prevenzione incendi` (sola lettura).
- I numeri di pagina nel rapporto sono quelli del PDF (quelli che `cerca_norme.py` stampa), che per le norme CEI coincidono con la numerazione stampata; per la DCPREV la pagina stampata è la pagina PDF meno 2.
- Non ho cercato nulla su internet. I documenti che mancano in archivio sono segnalati come [?].

## 1. Inventario

86 citazioni distinte in 20 file. Per fonte: CEI 0-21 (18), CEI 0-16 (9), CEI 64-8 (16), CEI 82-25 (7), DM 37/2008 (6), DCPREV 14030/2025 (16), D.Lgs. 199/2021 e 5/2026 (9), D.Lgs. 190/2024 (6), ARERA (5), Lombardia (7), DM 414/2023 e GSE (3), altre (IEC 61724-1, IEC 62109, CEI TS 82-89, EN 61730-2, EN 50583-1, UNI EN 13501-1, NTC 2018, Codice di prevenzione incendi, DPR 151/2011, DPR 380/2001, DM 19/05/2015, Reg. (UE) 2024/1364, Terna, GAUDÌ, PVGIS). I file: `rules.py` (quasi tutte le regole N01-N27), `checks.py` (soglie e voci della pagina Verifiche), `energy/stringing.py` (verifiche delle stringhe), `energy/components.py`, `energy/bands.py`, `energy/economics.py`, `energy/consumption.py`, `energy/simulate.py`, `layout.py`, `sun.py`, `geo.py`, `model.py`, `roofs.py`, `energy/nearshade.py`, `pvsyst/mapping.py`, `pvsyst/project.py`, `ui/properties.py`, `ui/energy_pages.py`, `ui/report.py`, `ui/plan_overlays.py`, `ui/catalog_dialog.py`, più le traduzioni in `po/it.po`.

Esito in sintesi, sulle 101 righe della tabella del §2 (una citazione che compare in più file è una riga sola; due righe sono punti della CEI 0-21 non citati dal codice, messi in tabella perché mancano): 92 confermate [V] alla prima lettura; 7 con un riferimento sbagliato o impreciso [X] (2 da sole, 5 annotate accanto a un [V]), tutte di numero di allegato, paragrafo o figura, nessuna soglia numerica sbagliata; 7 non verificabili in locale [?]; 5 letture dedotte [I] annotate accanto alla citazione, sui punti dove il codice interpreta la fonte.

## 2. Tabella delle citazioni

### 2.1 CEI 0-21:2026-07 (connessione BT)

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| 3.61 Potenza nominale, p. 16 | `rules.py:6-8, 80`; `checks.py:46-47` | La potenza nominale di un impianto FV è la minore tra la potenza degli inverter e la somma delle potenze STC dei moduli; le soglie 6, 11,08, 20 e 100 kW si confrontano con questa | [V] p. 16: «Nel caso di generatori FV, la potenza attiva massima erogabile è limitata dalla potenza nominale dell'inverter, qualora questa sia minore della somma delle potenze STC dei moduli FV»; 3.62 (plug&play) usa esplicitamente «il valore minore tra» | Stessa definizione in ARERA 385/2025 art. 2.2 g) (p. 22). [I] La norma usa per le soglie parole diverse: «potenza complessiva» (8.2.2.2, 8.3, 8.6.2), «potenze dell'impianto» (8.2.2.4), «potenza in immissione richiesta» (6.3, Tab. 5): usare min(Pdc, Pac) per tutte è una scelta coerente ma va detta |
| 8.2.2.2 Schemi impiegabili, p. 62 | `rules.py:209-211` (N04), `225-227` (N05), `245-249` (N08) | Fino a 11,08 kW più SPI, al limite uno per DDI; DDI di norma unico; oltre 11,08 kW fino a tre DDI con propria PI senza OR, oltre tre in OR; più DDI comandati da un unico SPI | [V] p. 62, testo identico nel contenuto | |
| 8.2.2.3 Dispositivi ammessi come DDI, p. 63 | `rules.py:215-217` (N04), `228-229` (N05) | Inverter fino a 11,08 kW con DDI interno: due dispositivi, almeno un contattore AC1 con distanze in aria della IEC 62109; il DDI è un interruttore idoneo al sezionamento o un contattore onnipolare AC3 | [V] p. 63 (IEC 62109-1 §7.3.7 e 62109-2 §4.4.4.15.2.1) | Manca: l'alternativa «interruttore di manovra-sezionatore» e il caso inverter ≤ 11,08 kW senza trasformatore, in cui entrambi i dispositivi sono AC1 (p. 63) |
| 8.2.2.4 Rincalzo, p. 63-64 | `rules.py:232-239` (N06); `checks.py:20, 79-81` | Oltre 20 kW rincalzo al DDI (eventualmente il DG/DGL), comando ritardato al massimo 0,5 s, ripristino solo manuale; l'inverter con DDI interno elettromeccanico può fare da rincalzo se riceve il segnale ritardato dall'SPI esterno; sempre almeno due dispositivi | [V] p. 63-64, parola per parola | La traduzione `it.po:1928` scrive «DG o DGL», più fedele dell'inglese «main switch». La norma aggiunge: nessun rincalzo per utenti MT sotto 30 kW (non riguarda la BT) |
| 8.3 Connessione monofase/trifase, p. 65 | `checks.py:19, 63-72` | Produzione monofase fino a 6 kW; il DSO può elevare a 10 kW | [V] p. 65 | Manca 8.3.1: impianto trifase con generatori monofase (microinverter), squilibrio tra fasi entro il LSP (6 kW, o 10) e automatismo oltre (A.4.11). `connection()` tratta solo `phases == 1` |
| 6.3, Tabella 5, p. 33 | `checks.py:21, 59-62`; `consumption.py:139, 147`; `rules.py:240-244` (N07) | Fino a 100 kW BT; oltre 100 kW il DSO può proporre la MT | [V] p. 33: «per richieste di potenza superiori a 100 kW, è facoltà del DSO proporre la connessione in MT»; Tab. 5: ≤ 100 kW BT; > 100 ÷ ≤ 200 kW «BT o MT» (letta a immagine) | Oltre 200 kW la tabella non prevede la BT; nota (1): generatori direttamente connessi oltre 200 kVA sempre da verificare con la CEI 0-16. Le potenze di Tab. 5 sono «in immissione» |
| 7.4.10 Locali per la trasformazione MT/BT, p. 46 | `rules.py:241-244` (N07) | Oltre 100 kW il distributore può proporre la MT (TICA) | [V] p. 46: «Il limite oltre il quale il DSO ha facoltà di proporre al richiedente la sola fornitura MT è fissato in 100 kW (TIC e TICA)» | Manca una conseguenza di progetto: chi resta in BT oltre 100 kW deve mettere a disposizione, a richiesta del DSO, un locale per una cabina secondaria (circa 16 m²), CEI EN 61936-1 e 50522 (p. 46) |
| 8.6.2 Sistema di protezione di interfaccia, p. 96 | `checks.py:18, 73-78`; `rules.py:212-214` (N04), `220-222` (N05) | SPI relè dedicato oltre 11,08 kW; integrato nell'inverter o dedicato fino a 11,08 kW; verifica in campo A.4.3 (dedicato) e A.4.4 autotest (integrato) | [V] p. 96 | Il titolo 8.6.2 è a p. 95; la frase citata è a p. 96. A p. 95, nota (1): se l'SPI è sul lato BT di un'utenza MT con produzione oltre 30 kW si applica la CEI 0-16 |
| 8.6.2.1, Tabella 14, p. 97 | `rules.py:216-217` (N04) | Sotto 800 W regolazioni fisse, non modificabili dall'utente | [V] per la Tabella 14 (p. 97: «ad esclusione degli impianti di potenza inferiore a 800 W per i quali si applicano le regolazioni indicate in Tabella 14») | [X] lieve: «non regolabile dall'utente» non sta in 8.6.2.1 ma nell'Allegato D D.1 (p. 249, «sistema in esecuzione fissa non regolabile dall'utente») e in Bbis (p. 174, «intervallo fisso (non regolabile)») |
| Allegato G | `rules.py:229-231` (N05) | Il regolamento di esercizio segue l'Allegato G (impianti oltre 11,08 kW in parallelo con la rete BT) | [V] p. 5 e p. 261: «Allegato G (normativo) Regolamento di esercizio di impianti di produzione di potenza maggiore di 11,08 kW in parallelo con rete BT del DSO» | Manca in N04 l'**Allegato Gbis** (p. 272): regolamento per impianti fino a 11,08 kW connessi tramite inverter; e per gli impianti sotto 800 W il «Modulo semplificato di notifica» e il regolamento ≤ 0,8 kW (8.7, p. 101) |
| Allegato A.4.3, A.4.4 | `rules.py:213-214, 218, 221` | Prove in campo dell'SPI dedicato (A.4.3) e autotest dell'integrato (A.4.4) | [V] p. 96; p. 117 elenca le prove in campo (A) e D) di A.4.3.1, A.4.3.3.2, A.4.3.3.3) | |
| Allegato Nbis | `rules.py:375-377, 380` (N22) | I convertitori con accumulo sono provati secondo l'Allegato Nbis della CEI 0-21 (o della CEI 0-16 in MT) | **[X]** Nella CEI 0-21:2026-07 non esiste un Allegato Nbis (elenco allegati p. 5-6: A, B, **Bbis «Prove sui sistemi di accumulo» p. 166**, Bter, C, D, E, F, G, Gbis, Gter, H, I, L, X). Nbis è l'allegato della **CEI 0-16** (p. 111: «nell'Allegato Nbis per i sistemi di accumulo») | Bbis.1 (p. 166): si applica anche quando l'accumulo condivide l'inverter con il generatore FV; prove in campo non richieste sotto 800 W. Correggere in «Allegato Bbis della CEI 0-21 (Nbis della CEI 0-16 in MT)» |
| FAQ CEI del 07/06/2017 | `rules.py:223-224, 231` (N05) | La soglia di 11,08 kW riguarda la potenza complessiva dell'impianto, accumulo compreso | **[?]** La FAQ non è in archivio (l'unica FAQ CEI presente è quella del CT 82 sui cavi, 03/03/2026). La norma 2026 non definisce «potenza complessiva» nel cap. 3 (cercato: compare solo a p. 62 e 65) | Sostenibile con la norma stessa: 8.4.1 (p. 65) tratta l'accumulo come parte del gruppo di generazione e Bbis (p. 166) copre l'inverter condiviso; conviene citare queste pagine e non la FAQ |
| 8.4.4.2 Potenza reattiva, Tab. 10, p. 76-77 | nessuna | (non citata) | [V] letta: capability triangolare fino a 11,08 kW, rettangolare oltre; cosφ = 1 in condizioni normali, il DSO può chiedere altro; oltre 11,08 kW comandi remoti di reattivo (Allegato E) | Regola mancante (vedi §4) |
| Allegato L, SLI, p. 300 | nessuna (`economics.py:79` ha `export_limit_kw`) | (non citata) | [V] letta: il SLI limita l'immissione alla PIR concordata; indipendentemente dalla PIR valgono i limiti di 6.3 e 8.3 | Regola mancante (vedi §4) |

### 2.2 CEI 0-16:2026-07 (connessione MT e AT)

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| 6.3, Tabella 4, p. 43 | `rules.py:22-24, 47-49`; `checks.py:57`; `ui/properties.py:431-432` | BT fino a 0,1 MW; MT fino a 6 MW per la produzione; 6-10 MW MT o AT; oltre 10 MW AT | [V] p. 43 (letta a immagine): ≤ 0,1 BT; 0,1-0,2 BT/MT; 0,2-3 MT «limite superiore elevato a 6 MW per la connessione di impianti di produzione»; 3-10 MT/AT «limite inferiore elevato a 6 MW per la produzione»; > 10 AT | `auto_level` sceglie MT fino a 10 MW: tra 6 e 10 MW la tabella dice «MT o AT», decide il DSO. Le potenze sono in immissione |
| 1 Oggetto e scopo, p. 7 | `rules.py:267-269, 273` (N11) | La CEI 0-16 copre le reti di distribuzione oltre 1 kV fino a 150 kV e, sopra 35 kV, solo utenti in antenna da cabina primaria | [V] p. 7 | |
| 8.8 Regole per gli utenti attivi, p. 111 | `rules.py:251-252, 258` (N09) | Per potenze di generazione fino a 30 kW valgono le prescrizioni della CEI 0-21 | [V] p. 111: «si devono rispettare le prescrizioni della Norma CEI 0-21 per gli utenti con potenza complessiva dei gruppi di produzione fino a 30 kW»; nota (1): le disposizioni dell'articolo non si applicano fino a 11,08 kW | |
| Allegato N (prove sui generatori statici), p. 111 e 323 | `rules.py:254-255, 258` (N09) | Gli inverter sono provati secondo l'Allegato N | [V] p. 111 («Allegato N per generatori statici, eolici FC e DFIG, Nbis per i sistemi di accumulo, Nter per sincroni e asincroni»), titolo a p. 323 | Impianto FV con accumulo sul bus DC rimovibile: prove N e Nbis sui due sistemi (p. 111) |
| 8.8.3 Dispositivi previsti, p. 116-117 | `rules.py:253-255` (N09), `247-249` (N08) | DDI e DDG: due interruttori in serie, o un interruttore e un contattore, nell'impianto dell'utente; con più generatori DDI di norma unico, ammessi più DDI comandati da un unico SPI | [V] p. 116 (8.8.3) e p. 117 (8.8.3.1) | [X] lieve: la frase sui più DDI è in 8.8.3.1, non 8.8.3. A p. 117 anche: più PI ammesse solo con logica OR; fino a tre DDI senza OR solo per impianti esistenti connessi da almeno un anno con generatori ≤ 1000 kW |
| 8.8.7.3 Rincalzo, p. 152 | `rules.py:256-258` (N09) | Oltre 400 kW rincalzo con ritardo al massimo 1 s e ripristino manuale | [V] p. 152 («per impianti attivi con potenze superiori a 400 kW ... ritardo non eccedente 1 s ... ripristino ... solo manualmente»; soluzione approvata dal DSO) | |
| Allegati O e T (CCI), p. 484 e 516 | `rules.py:262-265` (N10) | CCI secondo gli Allegati O e T, con funzione PF2 | [V] p. 484 «Allegato O (normativo) Controllore Centrale di Impianto (CCI)»; p. 516 e 550: requisiti di comunicazione nell'Allegato T | |

### 2.3 CEI 64-8/7:2024-07, sezione 712, e CEI 64-8/1

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| Sezione 712, p. 91-110 | `rules.py:189` (N01) | La sezione 712 occupa le pagine 91-110 | [V] 712.1 a p. 91; Allegato C (ultimo della sezione) a p. 110; 713 inizia a p. 111 | |
| 712.512.1.1 e 712.512.1.2, p. 99 | `rules.py:179-181` (N01) | Dispositivi c.c. scelti per Uoc MAX (tensione nominale) e Isc MAX (corrente di impiego), metodo dell'Allegato B | [V] p. 99 | |
| Allegato B.1, p. 109 | `rules.py:182-183`; `stringing.py:4-6, 87-90, 123, 146` | Uoc MAX = KU · Uoc STC, KU = 1 + (aUoc/100)(Tmin − 25); senza Tmin o coefficiente, Uoc MAX = 1,2 Uoc STC | [V] p. 109, formula e frase identiche | `ku()` ritorna 1,2 anche se manca solo il coefficiente: conforme («In assenza di informazioni sulla temperatura minima ... o del coefficiente») |
| Allegato B.2, p. 109 | `rules.py:180-181`; `stringing.py:7, 168-173` | Isc MAX = KI · Isc STC, KI minimo 1,25 | [V] p. 109 («Il valore minimo di KI è 1,25», da aumentare con riflessioni o irraggiamento maggiore) | |
| 712.431.101, p. 95 | `rules.py:185-186`; `stringing.py:8-9, 192-206` | Con più di due stringhe in parallelo, protezione di stringa dove 1,35 · I_MOD_MAX_OCPR < (Ns − 1) · Isc MAX; con una o due stringhe nessuna protezione | [V] p. 95; NOTA 1: con MPPT indipendenti Ns è il numero di stringhe sul singolo ingresso (il codice lavora per ingresso: coerente) | |
| 712.431.102, p. 95 | `stringing.py:9-10, 196-203` | Corrente nominale della protezione: 1,1 · Isc MAX ≤ In ≤ I_MOD_MAX_OCPR | [V] p. 95 | Il caso di un solo dispositivo per Np stringhe (Np · 1,1 Isc MAX ≤ In ≤ I_MOD_MAX_OCPR − (Np − 1) Isc MAX) non è trattato dal codice |
| 712.433.101, p. 97 | `stringing.py:10-11` (solo docstring) | Il cavo di stringa porta Isc MAX, o (Ns − 1) Isc MAX senza protezione, o In con protezione | [V] p. 97 | Dichiarato ma **non calcolato**: Meridiana non ha i cavi. Da dire nella relazione |
| 712.414.101, p. 94 | `stringing.py:5-6, 149-150` | SELV o PELV sul lato c.c. solo con Uoc MAX fino a 120 V | [V] p. 94 | |
| 712.412, p. 94 | `stringing.py:150` | Altrimenti isolamento doppio o rinforzato | [V] p. 94 (712.410.102 e 712.412.101: classe II o equivalente fino ai morsetti c.c. del convertitore) | |
| 712.523, p. 101 | `rules.py:183` (N01) | Cavi soggetti al riscaldamento dei moduli dimensionati per 70 °C | [V] p. 101, 712.523.101 («temperatura ambiente almeno pari a 70 °C») | |
| 712.537.2.101 e 712.537.2.2.101, p. 105 | `rules.py:184-185` (N01) | Sezionamento del convertitore lato c.c. e c.a.; sul lato c.c. sezionatore o interruttore idoneo | [V] p. 105 | |
| 712.443 e 712.534, p. 98 e 102-104 | `rules.py:187-188` (N01) | SPD lato c.c. scelti secondo 712.443 e 712.534 | [V] p. 98 (712.443.101-102: SPD c.c. quando la Sez. 443 li richiede, altrimenti valutazione L ≥ Lcrit con Tab. 712.102), p. 102-104 (712.534.102: CEI EN 61643-31, classe II di norma, Ucpv ≥ Uoc MAX, In ≥ 5 kA, Iscpv ≥ Isc MAX) | Nessuna di queste regole è calcolata (vedi §4) |
| 712.514, p. 99-101 | `rules.py:188` (N01) | Cartelli e marcature della presenza del FV | [V] p. 100-101 (cartello all'origine, ai contatori, sul quadro; marcatura dei punti di accesso c.c.; commento: ulteriore cartello in alluminio secondo VVF e Guida CEI 82-25) | |
| 712.3.22, p. 93 | `components.py:49` | I_MOD_MAX_OCPR è la massima protezione contro le sovracorrenti del modulo | [V] p. 93 («MOD_MAX_OCPR: valori massimi di protezione contro le sovracorrenti di un modulo FV, vedi EN 61730-2») | |
| CEI 64-8/1, 11.2, p. 10 | `rules.py:204-207` (N12) | La CEI 64-8 copre impianti fino a 1500 V in c.c. | [V] p. 10 («1 000 V c.a. e 1 500 V c.c.») | |
| CEI 64-8/7:2024 come fonte delle voci stringhe | `checks.py:178-182`; `ui/report.py:122`; `ui/energy_pages.py:211` | | [V] | Le voci portano solo «CEI 64-8/7:2024» senza articolo: la relazione dovrebbe riportare l'articolo di ogni verifica (il `Record` lo ha) |

### 2.4 CEI 82-25 (guida), parti 1 e 3

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| CEI 82-25/1:2026, 3.2.1.5-6, p. 10-11 | `geo.py:8-9`; `sun.py:29`; `layout.py:59, 120`; `roofs.py:3`; `nearshade.py:98`; `simulate.py:84, 435`; `pvsyst/mapping.py:118`; `pvsyst/project.py:68`; `plan_overlays.py:43-44` | Inclinazione β dall'orizzontale; azimut α da Sud, negativo verso Est, positivo verso Ovest | [V] p. 10 (3.2.1.5 angolo di inclinazione) e p. 11 (3.2.1.6: NOTA 1 misurato rispetto al Sud nell'emisfero settentrionale; NOTA 2 negativi verso Est, positivi verso Ovest) | Il piè di pagina del PDF dice «CEI 82-25/1:2022-08»: il file 2026-03 riprende quelle pagine |
| CEI 82-25/1:2026, 3.2.1.15-18, p. 13-14 | `simulate.py:438-439` | Termini della radiazione: globale, diretta, diffusa, riflessa (Wh/m²) | [V] p. 13-14 | |
| CEI 82-25/1, 3.2.2 «sottocampo» | `model.py:8` | Il sottocampo è il 3.2.2 della guida | **[X]** È il **3.2.3.2** (p. 24: «sottocampo fotovoltaico: sottoinsieme elettrico di un Campo FV formato da stringhe FV e dai componenti necessari al loro funzionamento»); 3.2.2 è un'altra voce | Stessa definizione in CEI 64-8/7 712.3.6 (p. 92) |
| CEI 82-25/3:2026, 6.2, Figura 1, p. 8-10 | `sun.py:9-11, 128, 142`; `layout.py:12, 137`; `ui/properties.py:405-406` | Angolo limite αL = arctg(h/d); per osservazione ruotata di β, d' = d/cos β; la guida non fissa il giorno e le ore di progetto | [V] p. 9-10 (formula e d' = d/cosβ); 6.2 «Strutture fisse inclinate» inizia a p. 8 | p. 9 cita PVGIS come simulatore gratuito della Commissione europea |
| NTC 2018 7.2.4 richiamato dalla CEI 82-25/3 6.2 | `layout.py:12-13, 44`; `checks.py:130` | Su un solaio l'attrito non è un vincolo: le zavorre da sole non bastano, servono vincoli rigidi o flessibili | [V] p. 9: «non consente che le strutture ... montate su solai siano vincolati alla costruzione contando sull'effetto dell'attrito (come, ad esempio, strutture bloccate solo con zavorre) ... La prescrizione è riportata nelle NTC nel Cap.07 ... paragrafo 7.2.4» | Le NTC 2018 non sono in archivio: verificate per il tramite della guida [V per interposta fonte] |

### 2.5 DM 37/2008 (testo integrato con il DM 130/2025)

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| Art. 5 c. 2 lett. a) e c), p. 4 | `rules.py:191-193` (N02) | Progetto di un professionista iscritto: utenze alimentate in MT, o in BT con potenza impegnata oltre 6 kW o superficie oltre 200 m²; domestiche oltre 6 kW | [V] p. 4: lett. c) «tensione superiore a 1000 V, inclusa la parte in bassa tensione, o ... bassa tensione aventi potenza impegnata superiore a 6 kW o qualora la superficie superi i 200 m2»; lett. a) utenze condominiali e domestiche con potenza impegnata > 6 kW o superficie > 400 m² | [I] La condizione del codice (`p_nominal_kw > 6 or level != "BT"`) usa la potenza dell'impianto FV come surrogato della **potenza impegnata dell'utenza**: non è la stessa grandezza (vedi §4). Manca la lett. d): locali a maggior rischio di incendio, uso medico, pericolo di esplosione (sempre con progetto) |
| Art. 5 c. 1, p. 4 | `rules.py:199-202` (N03) | Negli altri casi il progetto può essere del responsabile tecnico dell'impresa installatrice | [V] p. 4 | |
| Art. 5 c. 4, p. 5 | `rules.py:194-195` (N02) | Il progetto contiene schemi, disegni planimetrici e relazione tecnica | [V] p. 5 | |
| Art. 7, p. 6 | `rules.py:195, 200-202` (N02, N03) | A fine lavori l'impresa rilascia la dichiarazione di conformità, sempre dovuta | [V] p. 6 (c. 1: della DiCo fanno parte la relazione sui materiali e il progetto dell'art. 5; c. 2: se progetta l'installatore basta lo schema) | Manca l'art. 8 c. 3 (p. 6): la DiCo va consegnata al distributore entro 30 giorni dall'allacciamento o dall'aumento di potenza che raggiunge le soglie dell'art. 5 c. 2 o comunque 6 kW: pratica di connessione |
| Art. 11 c. 2, p. 7 | `rules.py:195-196` (N02) | Se l'impianto rientra in un titolo edilizio il progetto si deposita con il progetto edilizio | [V] p. 7 | |
| «DM 37/2008 (testo integrato DM 130/2025)» | `rules.py:197`; `it.po:1872` | | [V] Il file dell'archivio è il testo integrato TuttoNormel con le note sul DM 130/2025 (GU n. 216 del 17/09/2025) | |

### 2.6 DCPREV 14030 del 01/09/2025 (linee guida VVF per il FV) e Codice di prevenzione incendi

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| 1.2 Campo di applicazione, p. 5-6 | `rules.py:204-207` (N12), `276-278` (N13), `293-296` (N14), `318-320` (N18), `354-356` (N21) | Impianti con tensione c.c. fino a 1500 V in attività soggette o a loro servizio, su edifici, pergole, tettoie, pensiline; pensiline «interferenti»; esclusi gli impianti a terra; riferimento utile anche per attività non soggette (punto 4, pag. stampata 4) | [V] p. 5 (1.2 punti 1-3) e p. 6 (punto 4) | 1.2 punto 3 esclude anche plug&play, impianti sotto 800 W, agrivoltaico oltre 100 m dagli edifici, concentrazione: non sono in `rules.py`. «sect. 1.2 p. 2» in N18 è ambiguo (punto 2, non pagina 2) |
| 2.1 Componenti, p. 7 | `rules.py:378-380` (N22) | L'accumulo fa parte dell'impianto ai fini antincendio | [V] p. 7 (2.1 punto 2) | Il seguito di N22 («ventilazione, rivelazione off-gas, distanze» per il litio) è [I]: la DCPREV 3.2.1.1 (p. 12) chiede una valutazione del rischio incendio ed esplosione secondo il DM 07/08/2012 e rimanda alla circolare **DCPREV 21021 del 23/12/2024** (BESS), non in archivio |
| 2.2 Obiettivi, p. 7-8 | `rules.py:279-281` (N13) | L'installazione modifica le condizioni di sicurezza antincendio e può aggravare il rischio | [V] p. 7 (2.2 punto 1) | |
| 2.3 Regola dell'arte, p. 8 | `rules.py:289-291` (N13), `294-295` (N14) | Regola dell'arte: CEI 64-8 e guida CEI 82-25 | [V] p. 8 (2.3: le norme CEI sono presunzione di regola dell'arte); CEI 64-8 e 82-25 nominate in 3.3.5.2 p. 20 e nel cap. 5 p. 27 | |
| Codice di prevenzione incendi S.10.6.2 | `rules.py:280-281, 291` (N13) | Si applica anche il punto S.10.6.2 del Codice | [V] DCPREV p. 20 (3.3.5.2 punto 3: «prescrizioni ... di cui al punto S.10.6 ed in particolare ... S.10.6.1 e S.10.6.2 dell'allegato al DM 3.08.2015») e p. 11 (3.2.1 punto 4); testo del Codice v10.6 p. 188: materiali e soluzioni che limitino innesco e propagazione, sicurezza di manutentori e soccorritori | Il codice lo colloca dopo il par. 2.2: la DCPREV lo richiama in 3.2.1 e 3.3.5.2. Il Codice non è in `reference` (copia su I:) |
| 3.3.5.1 Accessibilità e distanze (BAPV), p. 15-19 | `rules.py:298-303` (N15); `layout.py:14-16, 94-97, 107`; `ui/properties.py:520-521, 760-761` | Sottoinsiemi non oltre 20 m per lato, corridoi liberi di almeno 2 m, fascia libera di almeno 1 m dal bordo copertura; 1 m in proiezione orizzontale da aperture, lucernari, EFC e compartimentazioni sottostanti salvo solai resistenti al fuoco; shed: con zone libere di 2 m il lato può arrivare a 30 m | [V] p. 15-16 (punti 2-3, figure 5-6), p. 17 (punti 4-5, figura 7), p. 18 (punti 7-8, figure 9-10) | [X] lieve: N15 cita «figure 7-9»; la regola generale è nelle figure 5-6, le 7 e 8-10 sono tetti a falda con aperture e shed. Non implementati in `layout.py`: estensione a 30 m sugli shed, franco di 0,1 m tra pannelli e aperture sugli shed (punto 6), distanza di 1 m dalle compartimentazioni verticali (punti 5 e 3.3.2), soluzioni diverse con analisi del rischio (punto 10) |
| 3.3.5.2 Sezionamento di emergenza, p. 19-20 | `rules.py:282-283` (N13) | Dispositivo di sezionamento segnalato, protetto dall'incendio, accessibile ai soccorritori, verso tutte le sorgenti compreso il FV | [V] p. 19-20 | |
| 3.3.5.3 Dispositivi di protezione, p. 20 | `rules.py:284-285` (N13) | Protezioni contro sovracorrenti, guasti di isolamento, guasti serie, sovratensioni, correnti inverse | [V] p. 20 | |
| 3.3.5.4 Segnaletica, p. 20-21 | `rules.py:285-288` (N13) | Cartello «ATTENZIONE: IMPIANTO FOTOVOLTAICO IN TENSIONE DURANTE LE ORE DIURNE (... Volt)» nell'area del generatore e ogni 10 m lungo le condutture c.c. | [V] p. 20-21 (punto 2: «ogni 10 m per i tratti di condutture elettriche in corrente continua») | |
| 4.2 BAPV su coperture, p. 22-24 | `rules.py:304-307` (N15) | Classe di comportamento al fuoco secondo 4.2 (prove CEI TS 82-89, non inferiore a Crv); in alternativa soluzioni compensative come pannelli vetro-vetro B-s2,d0 | [V] per CEI TS 82-89 e Crv (p. 23-24, punti 7-8). **[X]** lieve: il vetro-vetro B-s2,d0 come misura compensativa è in 3.3.5.1 punto 6 (p. 17, riduzione delle distanze sugli shed), non in 4.2. Il 4.2 offre: caso 1 copertura incombustibile A1; caso 2 strato EI 30 con layer A1 esteso di 2 m oltre i pannelli; caso 3a accoppiamento modulo almeno classe E + Broof(T1-T4) con copertura Broof(T3, T4), oppure CEI TS 82-89 ≥ Crv; caso 3b analisi del rischio | N15 cita solo la via TS 82-89: incompleta |
| 4.4 BIPV, p. 25 | `rules.py:309-313` (N16) | Moduli conformi a CEI EN 61730-2 e, per la categoria di montaggio, CEI EN 50583-1; classificati al fuoco secondo UNI EN 13501-1; edifici civili con altezza antincendio oltre 12 m coerenti con il cap. V.13 del Codice | [V] p. 25 (4.4 punti 2 e 4; anche lettera circolare DCPREV 5043/2013, in archivio) | CEI EN 50583-1 è in archivio (`CEI EN IEC 50583-1 - CEI 82-54 - 2016-07`); UNI EN 13501-1 e CEI TS 82-89 no |
| 4.5 Pensiline, tettoie, parcheggi, p. 26 | `rules.py:315-320` (N18) | Se i pannelli sono l'unico elemento di copertura (BIPV vetro-vetro) classe almeno B-s2,d0 secondo EN 13501-1; nessun requisito per BAPV sopra coperture di parcheggi non interferenti | [V] p. 26 (4.5 punti 2-3; anche pensiline di distributori di carburante in materiale incombustibile) | |
| Cap. 5 Manutenzione, p. 27 | `rules.py:289-291` (N13) | Manutenzione nel registro dei controlli antincendio, verifiche ogni due anni, termografia periodica | [V] p. 27 (punto 1 registro del DM 01/09/2021; punto 4 termografia IEC TS 62446-3; punto 6 verifiche ogni due anni e a ogni modifica) | |

### 2.7 D.Lgs. 199/2021 (testo vigente, con D.Lgs. 5/2026) e D.Lgs. 192/2005

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| Art. 26, Allegato III Sez. B punto 3, p. 53 | `rules.py:137-147, 160-173` (N24); `checks.py:92-105` | P = k · S, k = 0,05 nuova costruzione, 0,025 esistenti; S superficie in pianta al livello del terreno, pertinenze escluse ma utilizzabili | [V] p. 53 (Sez. B punto 3) | `checks.py:105` cita «Sez. B p. 3»: punto 3, corretto |
| Sez. B punto 5: edifici pubblici +10% | `rules.py:147, 166-167` | Per gli edifici pubblici la potenza è aumentata del 10% | [V] p. 53 («gli obblighi di cui al punto 3 ... sono incrementati del 10%»; le quote termiche di cinque punti) | |
| Sez. C punto 2, p. 53 | `rules.py:169-171, 349-356` (N19, N21) | Impianti sull'edificio o nelle pertinenze; pertinenza = impronta dei fabbricati più un'area confinante non oltre il triplo; il FV a terra non concorre | [V] p. 53 | |
| Sez. C punto 3, p. 53 | `rules.py:344-347` (N20) | Tetti a falda: moduli aderenti o integrati con stessa inclinazione e orientamento; tetti piani: asse mediano non oltre la balaustra, o 30 cm senza balaustra | [V] p. 53 | |
| Art. 26 c. 4 e c. 5; art. 8 c. 1 D.Lgs. 192/2005 | `rules.py:172-173` | Inosservanza = diniego del titolo edilizio; calcoli e verifiche nella relazione dell'art. 8 c. 1 del D.Lgs. 192/2005 | [V] art. 26 c. 4-5 p. 20; D.Lgs. 192/2005 art. 8 c. 1 p. 13-14 (relazione tecnica depositata con la domanda del titolo) | Manca: copia della relazione al GSE (art. 26 c. 5; All. III Sez. E) e la Sez. D (impossibilità tecnica o economica: EP limite) |
| «come modificato dal D.Lgs. 5/2026 per i titoli richiesti dal 03/08/2026» | `rules.py:162-163`; `it.po:1828` | Il nuovo Allegato III vale per le richieste di titolo edilizio dal 03/08/2026 | [V] la regola dei 180 giorni: D.Lgs. 5/2026 art. 29 (p. 23) e All. III Sez. A punto 1 (p. 53): «richiesta del titolo edilizio presentata decorsi centottanta giorni dall'entrata in vigore del presente decreto». **[I]** la data: il decreto (GU n. 15 del 20/01/2026) non ha nel testo in archivio una clausola di entrata in vigore; con la vacatio ordinaria di 15 giorni (in vigore il 04/02/2026) i 180 giorni scadono il 03/08/2026 | Da scrivere nel codice come deduzione, o da confermare su Normattiva |
| Art. 25 c. 3, p. 19 | `rules.py:364-366` (N23) | Il modello unico del DM 19/05/2015 è esteso agli impianti fino a 50 kW | [V] p. 19 (c. 3 lett. b: «esteso agli impianti fotovoltaici di potenza fino a 50kW»; lett. a: anche il ritiro dedicato) | In archivio c'è il DM MASE 223/2026 (Modello Unico Parte III, impianti in attività libera, artt. 5 e 7 D.Lgs. 190/2024): il codice non lo cita |
| «GU n. 15 del 20/01/2026» | `rules.py:323, 347, 352, 368` | | [V] è il file `DLgs 5-2026 ... GU n.15 del 20-01-2026.pdf` | |

### 2.8 D.Lgs. 190/2024 (Testo unico FER, testo vigente)

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| «Annex I»: attività libera fino a 12 MW su edifici esistenti fuori zona A, senza vincoli | `rules.py:359-361, 367-368` (N23); `it.po:2128` | | [V] nei contenuti: Allegato A Sez. I lett. a) (< 12 MW integrati su coperture con stessa inclinazione e orientamento) e b.1) (< 12 MW su strutture o edifici esistenti fuori dalla zona A del DM 1444/1968), p. 19. **[X]** nel nome: il decreto lo chiama **Allegato A, Sezione I** (p. 19 «(Articolo 7) Allegato A Interventi in attività libera»); «Allegato I» è il titolo che TNE 2026-01 dà alla propria tabella (p. 9) | `layout.py:9-10` scrive correttamente «All. A sez. I a» |
| Art. 7: modello unico sulla piattaforma SUER | `rules.py:362-363` (N23) | | [V] art. 7 c. 10 (p. 5: modello unico riveduto per includere nella piattaforma SUER gli interventi dell'articolo); TNE 2026-01 p. 2: l'onere di presentare il modello è passato dal gestore di rete all'utente; il modello per l'attività libera non era ancora pubblicato a gennaio 2026 | Oggi c'è il DM MASE 223/2026 (in archivio) |
| «aggiornato dal D.Lgs. 178/2025» | `rules.py:359-360` | | [V] p. 1-4 del vigente (note «D.Lgs. 178/2025, D.L. 175/2025 conv. L. 4/2026») | |
| A terra: 5 MW in zone industriali, artigianali, commerciali; 1 MW in adiacenza all'edificio servito fuori zona A | `rules.py:370-373` (N27) | | [V] p. 19: lett. c) «inferiore a 5 MW installati a terra ... industriale, artigianale e commerciale, discariche, cave»; lett. b.2) «fino a 1 MW, se collocati a terra in adiacenza agli edifici esistenti cui sono asserviti» | |
| Art. 1 c. 1: i regimi valgono anche per gli accumuli | `rules.py:376-377, 380` (N22) | | [V] p. 2 («ivi compresi quelli di accumulo e gli elettrolizzatori») | Anche All. A Sez. I lett. t): accumulo elettrochimico fino a 10 MW in attività libera (p. 20) |
| TNE 2026-01 come fonte | `rules.py:367, 373` | | [V] file `TNE 2026-01 - FV in attività libera - Nuovi CAM - Rinvio CCI.pdf`, p. 2-3 e 9-10 | È un commento, non la fonte: citare il decreto |

### 2.9 ARERA, GSE, DM 414/2023 (energia e incentivi)

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| ARERA 385/2025/R/eel art. 2 | `rules.py:260-261` (N10) | FV ≥ 100 kW connesso in MT: procedura RIGEDI dell'Allegato A.72 al Codice di rete | [V] art. 2.1 (p. 21-22: impianti eolici e FV, esistenti e nuovi, ≥ 100 kW connessi o da connettere alle reti MT); art. 2.2 g) potenza nominale FV = minimo tra pannelli STC e inverter | Il titolo N10 «100 kW or more» e la condizione `>= 100` sono coerenti |
| ARERA 385/2025 artt. 3.1 e 4.1 | `rules.py:262-265` (N10) | CCI con PF2 «limitazione della potenza attiva su comando esterno del DSO», installato e attivo all'entrata in esercizio | [V] art. 2.3 (PF2 prestazione obbligatoria), 3.1 (produttori responsabili di CCI e PF2 secondo Allegati O e T), 4.1 (impianti nuovi: entro l'entrata in esercizio, comunicazione al distributore entro l'attivazione TICA), 4.2 (altrimenti connessione sospesa), p. 23 | [?] Le proroghe della delibera 564/2025 (aggiornata dalla 23/2026, in archivio) non le ho lette in dettaglio: riguardano gli esistenti, non la regola per i nuovi |
| ARERA 181/06, Tabella 1 | `bands.py:1-8, 18`; `economics.py:212, 303`; `consumption.py:359` | F1 lun-ven 8-19; F2 lun-ven 7-8 e 19-23, sabato 7-23; F3 lun-ven 23-7, domenica e festivi; festività elencate | [V] p. 1 (elenco festivi identico: 1 e 6 gennaio, lunedì di Pasqua, 25 aprile, 1 maggio, 2 giugno, 15 agosto, 1 novembre, 8, 25 e 26 dicembre) | [I] Il sabato 0-7 e 23-24 in F3 è una deduzione del codice (la tabella non lo scrive): corretta per esclusione |
| TICA (ARERA 99/08) | `rules.py:242-244, 365-366` | Connessione richiesta secondo il TICA | [V] CEI 0-21 7.4.10 p. 46 «(TIC e TICA)»; il TICA è in archivio (All. A ARG/elt 99/08 aggiornato alla 361/2023), non letto | |
| DM MASE 414/2023, Allegato 1 | `economics.py:7, 27, 41-49, 318-322` | TIP = 60/70/80 + max(0; 180 − Pz) con tetti 100/110/120 €/MWh per potenze > 600, 200-600, ≤ 200 kW; +10 Nord, +4 Centro; con contributo in conto capitale fattore F lineare fino a 0,50 al 40% | [V] p. 23-24, formule e tabella delle regioni identiche (NORD e CENTRE in `economics.py:24-26` coincidono con la tabella) | |
| GSE, Regole operative CACER e TIAD 16/07/2025, §2.2.2.2.2, p. 45-46 | `economics.py:28, 313-322` | Restituzione della componente TRASE (CUAf) sull'energia condivisa | [V] p. 46 (CUAfa),m = parte unitaria variabile della tariffa di trasmissione TRASE per le utenze BT) | Per i gruppi di autoconsumatori c'è anche la componente BTAU e le perdite evitate (p. 46), non modellate |
| Ritiro dedicato al prezzo zonale | `economics.py:5-6, 305` | L'energia immessa è venduta al GSE con il ritiro dedicato | [?] La delibera ARERA 280/07 non è in archivio; D.Lgs. 199 art. 25 c. 3 lett. a) (p. 19) conferma il ritiro dedicato via modello unico | |
| «famiglia tipo delle tabelle ARERA, 2.700 kWh con 3 kW» | `consumption.py:136-144`; `it.po:431` | | [?] Nessun documento ARERA sui prezzi per il cliente tipo in archivio | |
| «TRASE dell'anno (ARERA)» | `economics.py:75`; `ui/energy_pages.py:649` | | [?] tabella ARERA dell'anno non in archivio (il valore è un input) | |

### 2.10 Lombardia

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| DGR XII/6153 del 11/05/2026; decreto 6437/2026 punto 6.27 | `rules.py:142-144, 325-330, 334` (N25) | Dal 01/01/2027 k = 0,08 per centri dati (Reg. delegato (UE) 2024/1364) e logistica oltre 3 ha; 0,06 per logistica fino a 3 ha e grandi strutture di vendita; 0,05 altrimenti | [V] DGR 6153 p. 6 e 10; allegato al decreto 6437 p. 20 (6.27 lett. a e b, con l.r. 15/2024 per la logistica e d.lgs. 114/1998 art. 9 per le grandi strutture di vendita); ampliamenti: k sulla proiezione della parte ampliata | |
| Punto 4.7 | `rules.py:331-332` | Valgono le regole alla data della richiesta del titolo abilitativo | [V] p. 6 | |
| Punto 6.14 lett. c) iv: 65% | `rules.py:332-333` | Per le nuove costruzioni quota termica da FER al 65% | [V] p. 17 (dal 01/01/2027, limitatamente alle nuove costruzioni, i punti i e ii sono incrementati al 65%) | |
| Punto 6.16 v | `rules.py:333` | L'esenzione per impossibilità tecnica o economica è motivata nella relazione | [V] 6.16 inizia a p. 17; il punto v non l'ho letto per intero (p. 18): verifica parziale | |
| L.R. 11/2026 art. 2 c. 1 lett. b), art. 4 c. 5 | `rules.py:336-338, 342` (N26) | Massimo impiego tecnicamente possibile delle superfici disponibili; relazione energetica con le soluzioni per massimizzare la produzione in sito | [V] p. 2 (art. 2 c. 1 b) e p. 3 (art. 4 c. 5 lett. a-e) | |
| DGR XII/6645 del 03/08/2026, Allegato A par. 2.2; Allegato B | `rules.py:336-342` (N26) | RS tra superficie occupata e disponibile almeno 60%; superfici non usate motivate con relazione asseverata; relazione energetica dell'Allegato B | [V] p. 8-9 (2.2 Priorità b): RS ≥ 60%, relazione tecnica asseverata) e p. 14 (Allegato B Relazione energetica, art. 4 c. 5-6 L.R. 11/2026) | |
| Reg. delegato (UE) 2024/1364 | `rules.py:326` | Definizione di centro dati | [V] DGR 6153 p. 6; L.R. 11/2026 art. 1 c. 3 (p. 2) | Il regolamento non è in archivio: citato per il tramite degli atti lombardi |

### 2.11 Altre citazioni

| Citazione | file:riga | Che cosa afferma il codice | Esito | Note |
|---|---|---|---|---|
| IEC 61724-1:2021 (performance ratio) | `simulate.py:631-633`; `ui/energy_pages.py:367` | PR = (E/P0)/(Hi/Gref), «la norma non è nell'archivio locale» | [?] Confermato assente; la CEI 82-25/1:2026 ne riprende alcune definizioni (p. 11-14: 3.12 irradiance, 3.26 irradiation) | Il codice lo dichiara onestamente |
| IEC 61215 (coefficiente gamma) | `components.py:7` | Il coefficiente di temperatura della potenza è misurato secondo IEC 61215 | [?] Non in archivio (in archivio CEI EN IEC 61730-1/-2) | |
| IEC 62109 | `rules.py:216` | Distanze in aria dei contattori AC1 | [V] per il tramite della CEI 0-21 p. 63 | |
| CEI TS 82-89, UNI EN 13501-1 | `rules.py:304-306, 310-311, 316` | | [V] per il tramite della DCPREV p. 23-26; i documenti non sono in archivio | |
| Codice di prevenzione incendi cap. V.13 | `rules.py:311-313` (N16) | Edifici civili oltre 12 m: coerenza con V.13 | [V] DCPREV p. 25; il V.13 non l'ho letto nel Codice | |
| DPR 151/2011 | `model.py:101`; `ui/properties.py:513` | Attività soggetta ai controlli VVF | [V] in archivio; la DCPREV 1.1 (p. 5) ricorda che il FV non è di per sé un'attività soggetta | |
| DM 19/05/2015, DPR 380/2001, GAUDÌ, Codice di rete Terna (STMG) | `rules.py:267-273, 362-366` | | DM 19/05/2015 [V] via D.Lgs. 199 art. 25 c. 3; DPR 380/2001 [V] generico; GAUDÌ e Codice di rete Terna [?] (non in archivio) | |
| PVGIS (azimut, anno tipo, PVcalc) | `energy/meteo.py`, `energy/pvgis.py`, `geo.py:8` | Convenzione degli azimut uguale alla CEI 82-25 | [V] per la CEI 82-25/1 p. 11; la convenzione PVGIS non è verificabile in archivio | |
| «CEI 0-21 citata» nei dati di catalogo | `ui/catalog_dialog.py:41`; `catalog/data/*.json` | Certificati dichiarati dai costruttori | non verificati (dati di prodotto) | |

## 3. Le soglie numeriche e la loro fonte

| Soglia | Dove nel codice | Fonte verificata | Esito |
|---|---|---|---|
| 350 W potenza nominale plug&play | assente | CEI 0-21 3.62 p. 16 | regola mancante (fuori dal campo della DCPREV, 1.2 p. 5) |
| 800 W | `rules.py:216-217` | CEI 0-21 8.6.2.1 Tab. 14 p. 97; Allegato D D.1 p. 249; 8.7 p. 101 (modulo semplificato di notifica); DCPREV 1.2 punto 3 c) p. 5 (esclusi dalle linee guida) | [V]; sotto 800 W le regole N04 e N13 andrebbero adattate |
| 6 kW (monofase) | `checks.py:19, 63-72` | CEI 0-21 8.3 p. 65 (il DSO può elevare a 10 kW) | [V] |
| 6 kW, 200 m², 400 m² (progetto del professionista) | `rules.py:190-202` | DM 37/2008 art. 5 c. 2 lett. a) e c) p. 4 | [V] per i numeri; [I] la grandezza è la potenza impegnata dell'utenza, non la potenza del FV |
| 11,08 kW | `checks.py:18, 73-78`; `rules.py:209-231` | CEI 0-21 8.2.2.2 p. 62, 8.2.2.3 p. 63, 8.4.4.2 p. 76-77, 8.6.2 p. 96, 8.7 p. 101, Allegati G e Gbis p. 261 e 272 | [V] |
| 20 kW (rincalzo BT) | `checks.py:20, 79-81`; `rules.py:232-239` | CEI 0-21 8.2.2.4 p. 63-64 | [V] |
| 30 kW (CEI 0-21 anche in MT) | `rules.py:251-252` | CEI 0-16 8.8 p. 111; CEI 0-21 8.6.2 nota (1) p. 95; 8.2.2.4 p. 63 | [V] |
| 100 kW (BT/MT) | `checks.py:21, 59-62`; `rules.py:22, 47-49, 240-244`; `consumption.py:147` | CEI 0-21 6.3 Tab. 5 p. 33 e 7.4.10 p. 46; CEI 0-16 6.3 Tab. 4 p. 43 (0,1 MW) | [V]; potenze in immissione |
| 100 kW (RIGEDI, CCI) | `rules.py:259-265` | ARERA 385/2025 art. 2.1 p. 22 | [V] |
| 200 kW («BT o MT») | assente | CEI 0-21 Tab. 5 p. 33 | non usata: oltre 200 kW la tabella non prevede la BT |
| 400 kW (rincalzo MT) | `rules.py:256-258` | CEI 0-16 8.8.7.3 p. 152 | [V] |
| 6 MW e 10 MW (MT/AT) | `rules.py:23, 47-49`; `ui/properties.py:431-432` | CEI 0-16 Tab. 4 p. 43 | [V]; 6-10 MW «MT o AT» |
| 1500 V c.c. | `rules.py:203-207` | CEI 64-8/1 11.2 p. 10; DCPREV 1.2 p. 5 | [V] |
| 120 V (SELV/PELV) | `stringing.py:149-150` | CEI 64-8/7 712.414.101 p. 94 | [V] |
| KU = 1,2; KI ≥ 1,25 | `stringing.py:87-90, 128`; `rules.py:180-183` | CEI 64-8/7 Allegato B p. 109 | [V] |
| 1,35 e 1,1 (protezioni di stringa) | `stringing.py:195-203` | CEI 64-8/7 712.431.101-102 p. 95 | [V] |
| 70 °C (cavi sotto i moduli) | `rules.py:183` | CEI 64-8/7 712.523.101 p. 101 | [V] |
| 1 m bordo, 20 m gruppo, 2 m corridoio, 1 m da EFC/aperture/impianti | `layout.py:94-97, 107`; `rules.py:298-300`; `ui/properties.py:520-521, 760-761` | DCPREV 3.3.5.1 punti 2-3, p. 15-16 | [V] |
| 30 m (shed con zone libere di 2 m); 0,1 m franco; 1 m dalle compartimentazioni | `rules.py:301-303` (solo testo) | DCPREV 3.3.5.1 punti 5-6 e 8, p. 17-18; 3.3.2 punto 3 p. 15 | [V] nel testo di N15; non in `layout.py` |
| 10 m (cartelli lungo le condutture c.c.) | `rules.py:285-286` | DCPREV 3.3.5.4 punto 2 p. 21 | [V] |
| 12 m (altezza antincendio, V.13) | `rules.py:311-313` | DCPREV 4.3 punto 3 e 4.4 punto 4, p. 24-25 | [V] |
| 2 anni (verifiche antincendio) | `rules.py:290` | DCPREV cap. 5 punto 6 p. 27 | [V] |
| k = 0,05 e 0,025; +10% pubblici; 3 volte l'impronta; 30 cm | `rules.py:137-147, 344-352` | D.Lgs. 199/2021 All. III Sez. B punti 3 e 5, Sez. C punti 2-3, p. 53 | [V] |
| 180 giorni (decorrenza del nuovo All. III), 03/08/2026 | `rules.py:162-163` | D.Lgs. 5/2026 art. 29 p. 23; All. III Sez. A punto 1 p. 53 | [V] i 180 giorni; [I] la data |
| k = 0,06 e 0,08; 3 ha; 01/01/2027; 65% | `rules.py:142-144, 325-333` | Allegato al decreto Lombardia 6437/2026, 6.27 p. 20 e 6.14 c) iv p. 17; DGR 6153 p. 6 | [V] |
| RS ≥ 60% | `rules.py:339-340` | DGR XII/6645/2026 All. A 2.2 p. 8-9 | [V] |
| 12 MW, 5 MW, 1 MW (attività libera); 10 MW accumulo | `rules.py:359-373` | D.Lgs. 190/2024 All. A Sez. I lett. a), b), c), t), p. 19-20 | [V] |
| 50 kW (modello unico) | `rules.py:364-365` | D.Lgs. 199/2021 art. 25 c. 3 lett. b) p. 19 | [V] |
| 60/70/80, 100/110/120, 180 €/MWh; 200 e 600 kW; +4, +10; 0,50 al 40% | `economics.py:41-49` | DM 414/2023 All. 1 p. 23-24 | [V] |
| Fasce F1/F2/F3 e festivi | `bands.py` | ARERA 181/06 Tab. 1 p. 1 | [V] |
| 2.700 kWh, 3 kW (famiglia tipo) | `consumption.py:141-144` | ARERA (non in archivio) | [?] |

## 4. Regole incomplete, mancanti o da correggere

In ordine di gravità per chi deve firmare una relazione.

### 4.1 Da correggere (riferimenti sbagliati)

1. **N22, Allegato «Nbis» della CEI 0-21** (`rules.py:375-380`, `it.po:2152, 2160`): nella CEI 0-21:2026-07 le prove dei sistemi di accumulo sono nell'**Allegato Bbis** (p. 166); Nbis è della CEI 0-16 (p. 111). Da scrivere: «Allegato Bbis della CEI 0-21 (Allegato Nbis della CEI 0-16 in MT)».
2. **model.py:8, «CEI 82-25/1 3.2.2»**: il sottocampo è il **3.2.3.2** (p. 24).
3. **N15** (`rules.py:300, 304-306`): «figure 7-9» va in «figure 5-10» o meglio senza numeri; il vetro-vetro B-s2,d0 è la misura compensativa di 3.3.5.1 punto 6 (p. 17) per ridurre le distanze sugli shed, non un'alternativa del 4.2; il 4.2 va riassunto nei suoi casi (A1; EI 30 + layer A1; accoppiamento classe E + Broof; TS 82-89 ≥ Crv; analisi del rischio).
4. **N23, «Annex I» / «Allegato I»** (`rules.py:361, 367`, `it.po:2128, 2148`): nel D.Lgs. 190/2024 è l'**Allegato A, Sezione I** (p. 19). «TNE 2026-01» va tolto dalle fonti: è un commento.
5. **N05, «FAQ CEI del 07/06/2017»** (`rules.py:223-224, 231`): non verificabile in locale; sostituire con CEI 0-21 8.4.1 (p. 65) e Allegato Bbis.1 (p. 166), che trattano l'accumulo come parte dell'impianto e coprono l'inverter condiviso.
6. **N04, «non modificabili dall'utente (8.6.2.1, Tabella 14)»** (`rules.py:216-217`): la Tabella 14 è in 8.6.2.1, la frase sulla non regolabilità è in Allegato D D.1 (p. 249) e Bbis (p. 174).
7. **N08, «CEI 0-16 8.8.3»**: il punto esatto è 8.8.3.1 (p. 117).
8. **N13**: il richiamo a S.10.6.2 va attribuito a DCPREV 3.2.1 punto 4 e 3.3.5.2 punto 3, non al par. 2.2.
9. **N24, data 03/08/2026**: va marcata come dedotta (180 giorni dall'entrata in vigore del D.Lgs. 5/2026, GU 20/01/2026) o confermata.

### 4.2 Regole il cui innesco non segue la fonte

10. **N02/N03 (DM 37/08)**: l'art. 5 c. 2 guarda la **potenza impegnata dell'utenza** e la **superficie** (200 m² per attività produttive, commerciali, terziario; 400 m² e condomini per il domestico) e la lett. d) impone il progetto nei luoghi a maggior rischio di incendio, a uso medico, con pericolo di esplosione. Il codice usa `p_nominal_kw > 6`: un FV da 5 kW su un capannone da 2.000 m² o su un'attività soggetta ai VVF farebbe scattare N03 («può progettare l'installatore»), che è falso. Proposta: N02 anche quando `f.fire is True`, quando l'edificio non è residenziale (`use != "other"` o superficie > 200 m²), e in ogni caso chiedere la potenza impegnata della fornitura (dato che `consumption.py` ha già come `contract_kw`).
11. **Soglie CEI 0-21 e grandezza di riferimento**: `connection()` e `auto_level()` usano min(Pdc, Pac) (3.61) anche per Tab. 5 e Tab. 4, che parlano di potenza **in immissione**: con un SLI (Allegato L) la PIR può essere inferiore alla potenza nominale e il livello di tensione cambia. Da dire nella relazione, e da collegare a `export_limit_kw` di `economics.py`.
12. **8.3.1 squilibrio tra fasi**: un impianto trifase fatto di inverter monofase o microinverter deve rispettare il LSP di 6 kW (o 10) tra le fasi, con automatismo oltre (p. 65); `connection()` guarda solo `phases == 1`.

### 4.3 Regole mancanti rispetto a quello che le norme chiedono a un progettista FV

CEI 0-21:2026-07
13. **Potenza reattiva e rifasamento** (8.4.4.2, Tab. 10, p. 76-77): capability triangolare fino a 11,08 kW e rettangolare oltre; cosφ = 1 di norma, il DSO può chiedere altro all'atto della connessione; oltre 11,08 kW l'inverter riceve comandi remoti di reattivo (Allegato E). Il modello energetico lavora a cosφ = 1 e la scelta dell'inverter non ne tiene conto (dimensionamento in kVA, non in kW).
14. **SLI, Allegato L** (p. 300): limitazione dell'immissione alla PIR; da regola quando `export_limit_kw ≥ 0`.
15. **Sotto 800 W** (Tab. 14 p. 97, 8.7 p. 101 modulo di notifica e regolamento ≤ 0,8 kW; DCPREV esclusi): N04 e N13 non distinguono.
16. **Allegato Gbis** per gli impianti fino a 11,08 kW (p. 272) in N04.
17. **BT oltre 100 kW: locale per la cabina del DSO** (7.4.10 p. 46), da dire in N07.
18. **Plug&play ≤ 350 W** (3.62 p. 16) e Allegato X (infrastrutture di ricarica, p. 325): fuori dall'oggetto di Meridiana, da escludere esplicitamente.

CEI 64-8/7:2024-07
19. **Cavi**: 712.433.101 (stringa), 712.433.103 (campo, p. 98), 712.433.104 (cavo c.a.: corrente di impiego = massima c.a. del costruttore o 1,1 In, p. 98). Oggi dichiarati nel docstring e non calcolati.
20. **SPD c.c.**: 712.443.102 Tab. 712.102 (Lcrit = 115/Ng residenziale, 200/Ng a terra, 450/Ng non residenziale, p. 98) e 712.534.102 (Ucpv ≥ Uoc MAX, In ≥ 5 kA, Iscpv ≥ Isc MAX, p. 104): calcolabili con Ng e la lunghezza dei cavi.
21. **RCD di tipo B** sul lato c.a. salvo separazione semplice o dichiarazione del costruttore (712.530.3.101, p. 102); **IMD** sul lato c.c. (712.421.101.1, p. 94); **diodi di blocco** 2 · Uoc MAX e 1,1 Isc MAX (712.512.101, p. 99); **IP44/IK07** all'esterno (712.512.102, p. 99); Tabella 712.534 per Uw (p. 103); Tabella 712.537 per il dispositivo del collegamento funzionale (p. 105).
22. **712.431.102 con un dispositivo per Np stringhe** (p. 95-96): il codice tratta solo la protezione per singola stringa.

DCPREV 14030/2025
23. **Collocazione degli inverter**: all'aperto o in compartimenti dedicati REI/EI 30 con accesso dall'esterno o porta tagliafuoco, mai in compartimenti di attività soggette (3.2.2 punto 2, p. 12); supporti A1 o strato EI 30 (3.3.1.1, p. 14). Il modello non ha la posizione degli inverter.
24. **Compartimentazioni**: 1 m dalla proiezione delle pareti tagliafuoco salvo solaio resistente (3.3.2 punto 3, 3.3.5.1 punto 5); cavi sopra i muri tagliafuoco solo su passerelle protette (3.3.2 punto 1). `Building.fire.roof_fire_resistant` esiste, le pareti di compartimento no.
25. **Shed**: estensione a 30 m con zone libere di 2 m (punto 8), franco di 0,1 m (punto 6).
26. **Esodo ed EFC** (3.3.3, 3.3.4): componenti fuori dalle vie di esodo e dai luoghi sicuri; non ostacolare gli EFC (il modello ha gli EFC come esclusioni, non le vie di esodo).
27. **Procedimenti e documentazione** (cap. 6 e 7, p. 29-30, non letti in dettaglio): aggiornamento della pratica VVF, elaborati; e per i BESS la circolare **DCPREV 21021 del 23/12/2024** (3.2.1.1 punto 4, p. 12), da scaricare in `reference\laws`.
28. **Esclusioni di 1.2**: plug&play, < 800 W, agrivoltaico a più di 100 m, concentrazione.

DM 37/2008
29. **Art. 8 c. 3**: DiCo al distributore entro 30 giorni dall'allacciamento o dall'aumento di potenza (6 kW o soglie dell'art. 5 c. 2): pratica di connessione dell'utente attivo.

D.Lgs. 199/2021
30. **Sez. B punto 1** (quote termiche 60/40/15%, p. 53) e **Sez. D** (impossibilità tecnica o economica: EP limite): non sono FV ma stanno nella stessa relazione dell'art. 8 c. 1; **copia al GSE** (art. 26 c. 5; Sez. E). Il nuovo campo di applicazione (Sez. A punto 1) include gli «interventi di ristrutturazione dell'impianto termico»: per questi non è chiaro se P = 0,025 · S si applichi (domanda per Daniel).

D.Lgs. 190/2024 e pratiche
31. **DM MASE 223/2026** (Modello Unico Parte III, in archivio): la fonte attuale per il modello unico dell'attività libera, da citare in N23 al posto di TNE. **All. A Sez. I lett. t)** per l'accumulo fino a 10 MW in N22.

ARERA
32. **Delibera 564/2025 e 23/2026** (proroghe CCI): da leggere e citare in N10 per gli impianti esistenti; **N11** (Terna, STMG, GAUDÌ) resta non verificabile in locale.

## 5. Giudizio

**Si possono mettere in relazione oggi** (testo verificato parola per parola sulle fonti in archivio, con l'articolo e la pagina):
- N01 (CEI 64-8/7 sez. 712) e le verifiche delle stringhe di `stringing.py` (Uoc MAX con B.1, Isc MAX con B.2, protezioni 712.431.101-102, SELV 712.414.101, finestra MPPT), dicendo che i cavi e gli SPD **non** sono verificati.
- N04, N05, N06, N07, N08 (CEI 0-21: 8.2.2.2-8.2.2.4, 8.3, 8.6.2, 6.3 Tab. 5, 7.4.10) e le quattro soglie di `checks.py`, con le due correzioni di testo di §4.1 (punti 5 e 6) e l'Allegato Gbis in N04.
- N09 (CEI 0-16 8.8, 8.8.3, 8.8.7.3, Allegato N) e N10 (ARERA 385/2025 artt. 2-4; CEI 0-16 Allegati O e T).
- N13, N14, N16, N18, N21 (DCPREV 14030/2025) e le distanze di `layout.py` (1 m, 20 m, 2 m, 1 m dagli EFC), dichiarando che shed, compartimentazioni e inverter non sono trattati.
- N24, N19, N20 (D.Lgs. 199/2021 All. III: k, S, pertinenze, +10%, tetti a falda e piani), con la data del 03/08/2026 presentata come deduzione.
- N25, N26 (Lombardia: DGR 6153, decreto 6437 punti 4.7, 6.14, 6.27; L.R. 11/2026; DGR 6645 All. A 2.2 e All. B).
- Le fasce F1-F3 di `bands.py` e la tariffa premio TIP di `economics.py` (DM 414/2023 All. 1, GSE 16/07/2025 §2.2.2.2.2).
- Le convenzioni geometriche (CEI 82-25/1 3.2.1.5-6, 3.2.1.15-18; CEI 82-25/3 6.2 e il richiamo alle NTC 2018 7.2.4).

**Da correggere prima** di metterle in una relazione: N22 (Bbis, non Nbis), N15 (figure e alternative del 4.2), N23/N27 (Allegato A Sez. I, fonte DM 223/2026), N02/N03 (innesco sulla potenza impegnata e sulla lett. d, non sulla potenza del FV), `model.py:8` (3.2.3.2), N05 (via la FAQ), N08 (8.8.3.1), la collocazione di S.10.6.2 in N13.

**Mancano** (nell'ordine in cui pesano per un impianto FV italiano): potenza reattiva e cosφ (CEI 0-21 8.4.4.2), SLI e PIR (Allegato L), squilibrio tra fasi con inverter monofase (8.3.1), locale per la cabina del DSO oltre 100 kW in BT (7.4.10), cavi e SPD e RCD della sez. 712 (712.433, 712.443.102, 712.534.102, 712.530.3.101), collocazione degli inverter e compartimentazioni della DCPREV (3.2.2, 3.3.1.1, 3.3.2), shed a 30 m, BESS (DCPREV 21021/2024, da archiviare), DiCo al distributore (DM 37/08 art. 8 c. 3), quote termiche e copia al GSE del D.Lgs. 199/2021, sotto 800 W e plug&play come casi esclusi. Nessuna delle 86 citazioni contiene una **soglia numerica sbagliata**: gli errori trovati sono di riferimento (numero di allegato o di paragrafo, figura, nome dell'allegato) e di innesco della regola.

**Da fare sul PC di Daniel** o da decidere: confermare su Normattiva l'entrata in vigore del D.Lgs. 5/2026 (per la data 03/08/2026); scaricare in `reference\laws` la circolare DCPREV 21021 del 23/12/2024 (BESS) e, se gratuita, la FAQ CEI del 07/06/2017, altrimenti toglierla dal codice; leggere la delibera ARERA 564/2025 per N10; decidere se gli «interventi di ristrutturazione dell'impianto termico» entrano nell'obbligo di potenza (All. III Sez. A punto 1).

## 6. Fonti lette (file in `l'archivio locale delle norme`, pagine del PDF)

- `standards\cei\CEI 0-21 - 2026-07.pdf`: p. 5-6, 16, 33 (anche a immagine), 46, 62-65, 76-78, 95-98, 101, 117, 166, 249, 261, 272, 300.
- `standards\cei\CEI 0-16 - 2026-07.pdf`: p. 7, 43 (anche a immagine), 111, 116-117, 152, 323, 484, 516, 550.
- `standards\cei\CEI 64-8_7 - 9 ed. - 2024-07.pdf`: p. 91-105, 109-111; `CEI 64-8_1 - 9 ed. - 2024-07.pdf`: p. 10.
- `standards\cei\CEI 82-25_1 - 2026-03.pdf`: p. 10-14, 24; `CEI 82-25_3 - 2026-01.pdf`: p. 8-10, 13.
- `laws\DM 37-08. Testo integrato con le modifiche introdotte dal DM 130-25.pdf`: p. 4-7.
- `laws\DCPREV 14030 - 2025-09-01 - Linee guida di prevenzione incendi per impianti FV.pdf`: p. 4-12, 14-27.
- `laws\DLgs 199-2021 - Fonti rinnovabili - testo vigente Normattiva al 22-10-2026.pdf`: p. 19-21, 53-54; `laws\DLgs 5-2026 ... GU n.15 del 20-01-2026.pdf`: p. 23, 44, 56.
- `laws\DLgs 190-2024 - Testo unico regimi amministrativi FER - testo vigente Normattiva al 21-10-2026.pdf`: p. 1-5, 19-21.
- `laws\DLgs 192-2005 - Rendimento energetico in edilizia - testo vigente Normattiva al 22-10-2026.pdf`: p. 13-14.
- `laws\ARERA - Delibera 385-2025-R-eel.pdf`: p. 13-24; `laws\ARERA - Delibera 181-06 Tabella 1 ...pdf`: p. 1.
- `laws\DGR Lombardia XII-6153 ...pdf`: p. 6, 10; `laws\Disposizioni efficienza energetica edifici Lombardia - allegato al decreto 6437 ...pdf`: p. 6, 17-18, 20; `laws\LR Lombardia 11-2026 ...pdf`: p. 2-3; `laws\DGR Lombardia XII-6645 ...pdf`: p. 4-5, 8-9, 14.
- `laws\DM MASE 414-2023 ...pdf`: p. 23-24; `laws\GSE - Regole operative CACER e TIAD (Allegato 1) - versione del 16-07-2025.pdf`: p. 45-46.
- `publications\tuttonormel\TNE 2026-01 - FV in attività libera - Nuovi CAM - Rinvio CCI.pdf`: p. 2-3, 9-10.
- Fuori da `reference`: `<archivio aziendale>\LIBRERIE Antincendio\Normativa\Legislazione Italiana\_Codice di Prevenzione incendi\Codice-prevenzione-incendi_10.6.pdf`, p. 188 (S.10.6.2).
- Assenti in archivio, segnalati [?]: FAQ CEI 07/06/2017, IEC 61724-1:2021, IEC 61215, CEI TS 82-89, UNI EN 13501-1, NTC 2018, Codice di rete Terna (A.72, STMG), GAUDÌ, ARERA 280/07 (ritiro dedicato), tabelle ARERA dei prezzi e del TRASE, Reg. delegato (UE) 2024/1364, circolare DCPREV 21021/2024.
