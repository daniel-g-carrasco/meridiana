# Programma FV: requisiti normativi

21/10/2026. Che cosa chiedono norme e leggi a un progetto fotovoltaico e a un'analisi energetica, e quindi che cosa il programma deve saper chiedere, calcolare, verificare e produrre.

**Ambito.** Tutta Italia. Le varianti regionali sono segnate; la Lombardia è la prima, perché lì sono le commesse di Daniel e lì il metodo di calcolo energetico è regionale.

**Come è stato fatto.** Quattro ricerche parallele:
1. progetto elettrico;
2. CEI 82-25, parti 1, 2 e 3, lette per intero;
3. analisi energetica e obblighi sugli edifici;
4. prevenzione incendi, autorizzazioni, connessione e incentivi.

Si è cercato prima nell'archivio locale `l'archivio locale delle norme`, poi nelle librerie dell'ufficio, poi nelle fonti ufficiali in rete. Ogni requisito ha la fonte con edizione, articolo e pagina del PDF. I documenti collegati sono `01-confronto-approcci.md` e `03-architettura-e-prima-fase.md`, nella stessa cartella.

**Legenda**
- [V] = letto nel testo; [I] = dedotto, o preso da una fonte secondaria (TuttoNormel, FAQ, siti).
- Fasi del programma:
  - 1 = pannelli, stringhe, producibilità;
  - 2 = ostacoli, ombre, cavi, quadri, vincoli completi;
  - 3 = elaborati e pratiche;
  - fuori = non riguarda il programma.

**Abbreviazioni**

| Sigla | Significato |
|---|---|
| 64-8/x | CEI 64-8/x, 9a ed. 2024-07 |
| 0-21, 0-16 | edizioni 2026-07 |
| 0-2 | CEI 0-2:2025 consolidata |
| 82-25/1, /2, /3 | edizioni 2026-03, 2024-12, 2026-01 |
| 62305-x | 3a ed. 2025-02 |
| 35024-1, 35023 | CEI-UNEL, ed. 2020 |
| LG VVF | DCPREV 14030 del 01/09/2025 |
| TU FER | D.Lgs. 190/2024 vigente |
| DM 2015, DM 2025 | DM 26/06/2015 e DM 28/10/2025 (requisiti minimi) |
| All. H | Allegato H delle disposizioni lombarde (decreto 6437/2026) |
| p. | pagina del PDF |

## 1. In breve: che cosa cambia per il programma

1. **Due motori per l'energia (B01-B04).**
   - Per la relazione Legge 10, l'APE e le coperture % dell'obbligo rinnovabili si usa il **metodo convenzionale mensile**:
     - in tutta Italia, UNI/TS 11300-4 con i dati UNI 10349-1;
     - dove la regione ha regole proprie, il metodo regionale (in Lombardia l'All. H).
   - PVGIS è ammesso come stima di progetto, per la relazione energetica dei centri dati (dichiarandolo) e nelle diagnosi; non per i numeri di legge.
   - Il programma non sostituisce il software certificato (CENED+ in Lombardia, software CTI altrove): prepara i dati e ricontrolla.
2. **Una potenza per ogni scopo, sempre con il suo nome (D06, A11, A34, A41, C35).**

   | Potenza | Che cos'è | A che cosa serve |
   |---|---|---|
   | Po,cc | somma dei moduli in STC | fini amministrativi e incentivi |
   | Po,ca | minimo tra moduli e inverter | CEI 0-21, CEI 0-16, TICA, CCI, CACER, FER X |
   | PIR e potenza per la connessione | potenza in immissione richiesta; il massimo tra prelievo e immissione | connessione |
   | Potenza impegnata | il massimo tra contrattuale e autoproduzione | DM 37 (chi deve progettare) |

   Si scrive in kW, non in kWp.
3. **I vincoli antincendio diventano geometria (C06-C12, C16, C17).** Valgono per le attività soggette, e come buona pratica per le altre:
   - gruppi di moduli di al massimo 20 m, separati da corridoi di 2 m;
   - 1 m dal bordo della copertura;
   - 1 m da evacuatori di fumo (EFC), aperture e impianti tecnici;
   - 1 m dalle pareti di compartimentazione sottostanti;
   - regole proprie per gli shed e per le facciate;
   - niente componenti nelle vie d'esodo e nelle zone ATEX;
   - inverter con regole di posizione.
4. **L'archivio dei componenti è una lista di controllo (D14-D19, A05, C11, C21, C40, C41).**
   - Le Tabelle 5.1 e 5.2 della 82-25/2 dicono quali dati della scheda del modulo sono obbligatori.
   - Servono anche: certificazioni, classe di reazione al fuoco, Broof e C_FV; paese di produzione ed efficienza di cella (per iperammortamento e Conto Termico); per gli inverter, la Sezione A della dichiarazione di conformità CEI 0-21/0-16.
5. **Stringatura e protezioni c.c. con le formule della 712.** Uoc MAX e Isc MAX (A06-A08); stringhe in parallelo (A09); protezione e taglia di stringa (A14-A15); portata dei cavi (A16-A17).
6. **Temperature di progetto (A01, A03, D37).** Le norme non dicono da dove prendere la temperatura minima del sito né la massima per la finestra MPPT. Il programma la chiede e registra la fonte. Per i cavi distingue tre casi: retro dei moduli 70 °C, al sole fino a 80 °C, interni.
7. **Sovratensioni e fulmini (A28-A33).** Albero di decisione:
   - CRL e lunghezza critica per stabilire se servono gli SPD;
   - scelta degli SPD;
   - distanza di separazione s dall'LPS;
   - aste e calate dell'LPS come ostacoli che fanno ombra.
8. **Connessione (A34-A40, C33-C35).** Documenti per il distributore, regolamento di esercizio, tarature dell'SPI, limitazione dell'immissione (SLI), controllore centrale d'impianto (CCI, obbligatorio in MT da 100 kW).
9. **Regimi e pratiche (C03, C26-C29, C32, C34).**
   - VVF: SCIA o valutazione del progetto.
   - TU FER: attività libera, PAS o autorizzazione unica.
   - Modello unico fino a 200 kW, con trasmissione sulla piattaforma SUER.
10. **Simulazione oraria 8760 (C37, B30).** Serve per l'energia condivisa nelle CER e nelle configurazioni di autoconsumo, e per le diagnosi con i consumi misurati.
11. **Documenti (B14, B25, A42-A44, C20, C23).**
    - parte FV della relazione Legge 10;
    - relazione energetica dei centri dati;
    - progetto secondo DM 37 e CEI 0-2;
    - verifiche iniziali secondo 64-8/6;
    - cartelli;
    - piano di manutenzione VVF.
12. **Ciò che le norme non fissano** e il programma deve quindi rendere parametro dichiarato:
    - fonte della temperatura minima;
    - altezza del sole di progetto per la distanza tra le file;
    - perdite e Performance Ratio (le parti 4-6 della 82-25 non sono uscite);
    - limite di caduta di tensione (nessuno per il FV; 4% raccomandato per l'impianto utilizzatore);
    - rapporto c.c./c.a. (nessun limite).

## 2. Correzioni alla libreria R02 (per una R03)

La R02 (`<archivio aziendale>\LIBRERIE Impianti Elettrici\20-Fotovoltaico\Utilità Fotovoltaico_R02.xlsx`) non si tocca: le correzioni vanno in una R03, generata con gli script in `l'archivio locale delle norme\tools\utilita-fotovoltaico\`.

| Regola | Correzione | Fonte |
|---|---|---|
| N02, N03 | Il DM 37 guarda la **potenza impegnata** (il massimo tra contrattuale e nominale dell'autoproduzione), non la potenza FV. Mancano condomini, utenze domestiche oltre 400 m², altre utenze oltre 200 m², luoghi speciali, LPS in edifici oltre 200 m³ | A41: DM 37 artt. 1, 2, 5 [V] |
| N13 | Installare un FV su un'attività soggetta è **sempre** una modifica rilevante: SCIA ex art. 4 c.7 DM 7/8/2012 se c'è conformità integrale e nessun aggravio; altrimenti valutazione del progetto. Non "se del caso" | C03 [V] |
| N15 | L'esenzione per il solaio resistente al fuoco vale solo per la distanza dalle compartimentazioni, non per il metro da EFC, aperture e impianti tecnici. Il vetro-vetro B-s2,d0 è una misura compensativa per shed e pensiline, non un'alternativa generale al 4.2, che ha cinque vie. "Crv" è un errore di OCR per "C_FV" | C07, C08, C11 [V] |
| N17 | Manca che lo strato EI 30 va esteso a tutta la facciata | C12 [V] |
| N18 | Mancano le balaustre (LG 4.6) | C14 [V] |
| N23 | Va scritto "All. A sez. I", non "Allegato I"; le soglie sono "inferiore a 12 MW"; esiste il modello unico fino a 200 kW (DM 297/2022, TICA art. 6bis); il modello va trasmesso su SUER entro 5 giorni dall'esercizio (DM 15/07/2026, [I]); va citato il DL 175/2025 convertito dalla L. 4/2026 | C26, C32, C34 |
| N10 | Aggiungere le scadenze della ARERA 564/2025 per il CCI | C35 [V] |
| Stringatura, Tmin | Il -10 °C fisso viene da ABB QT10, non da una norma: diventa un dato con la sua fonte; senza dato, Uoc MAX = 1,2·Uoc STC | A01 [V] |
| Stringatura, MPPT | La verifica della finestra MPPT usa il coefficiente di Voc: va fatta con Vmpp e i coefficienti di Vmpp/Pmax, a NMOT | A10 [I] |
| Verifica 2 | Già noto: la verifica della tensione minima va fatta con la stringa più corta, non con la più lunga | memoria R02 |

**Per un progetto con attività soggetta e pensiline:** prima di usarne le note in un documento, ricontrollare N13 e N23.

## 3. Progetto elettrico (filone A)

Fonti lette per intero:
- 64-8/7 sez. 712 (p. 91-110), con gli articoli delle parti 1, 4, 5, 6 e 8 a cui rimanda;
- 35024-1 e 35023;
- 0-21 e 0-16 per schemi, SPI/DDI, misure, regolamento di esercizio, prove e SLI;
- 0-2;
- DM 37;
- 62305-1/-2/-3/-4 (parti FV) e CEI 81-29;
- 61730-1/-2 e CEI EN 50583-1;
- la checklist As-Built dell'ufficio.

Come modello è stata usata una relazione FV reale di progetto esecutivo (2025).

### Dati di ingresso

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A01 | Uoc MAX si calcola con la temperatura ambiente minima del sito, ma la norma non dice da dove prenderla. Senza Tmin o senza coefficiente: Uoc MAX = 1,2·Uoc STC. La R02 usa -10 °C fisso (da ABB QT10) | 64-8/7 All. B.1 p. 109 | V | sempre | Chiede Tmin e la sua fonte (dato climatico, PVGIS, UNI 10349); 1,2 come ripiego | 1 |
| A02 | I dati mancanti il progettista li presume e li fa approvare per iscritto al committente | 0-2 2.3 p. 8 | V | sempre | Registro dei dati con origine (fornito, da sopralluogo, presunto) e approvazione | 1/3 |
| A03 | Cavi scaldati dal retro dei moduli: almeno 70 °C. Al sole: CEI 20-21, oppure k1 = 0,70 (55 °C) in prima approssimazione; la 82-25/3 dice fino a 80 °C secondo il sito. k1 per isolante a 90 °C: 0,58 a 70 °C, 0,41 a 80 °C | 712.523.101 p. 101; 35024-1 2.7 p. 6, Tab. 3 p. 14; 82-25/3 9.3 p. 34 | V | lato c.c. | Ogni tratto ha un'esposizione (retro moduli, sole, interno, interrato) e il k1 si calcola da solo | 2 |
| A04 | Dati per SPD e protezioni: NG da rete di localizzazione (almeno 10 anni di dati, non più vecchi di 5); ambiente rurale, suburbano o urbano e lunghezze LP; attività dei casi a-d di 443.4; edificio residenziale, non residenziale o a terra; LPS e classe; TT o TN; dati dell'impianto esistente | 712.443.102 p. 98-99; 64-8/4 443.4-443.5 p. 61-63; 62858 4.3-4.5 p. 17; DM 37 art. 7 c.3 p. 6 | V | sempre | Scheda "sito ed edificio"; NG dalle coordinate, con fonte e periodo | 1 |

### Moduli, stringhe, inverter

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A05 | Dati di targa del modulo: Vsys, classe (II, 0, III), Voc, Isc, Pmax con tolleranze, MOD_MAX_OCPR (corrente massima della protezione da sovracorrente), coefficienti di temperatura, serie e parallelo massimi, connettori, classe al fuoco, altitudine massima. Moduli conformi a 61730-1 e 61215, inverter a 62109-1/-2 | 61730-1 4.5, 5.2.2-5.2.3 p. 30-35; 712.3.22 p. 93; 712.511 p. 99 | V | sempre | Archivio di moduli e inverter con campi obbligatori e certificati | 1 |
| A06 | Uoc MAX = KU·Uoc STC, con KU = 1 + (αUoc/100)(Tmin - 25), αUoc in %/°C (da mV/°C: 0,1·α/Uoc del modulo); per il silicio amorfo i valori iniziali | All. B.1 p. 109 | V | sempre | Calcolo per modulo, stringa, sottocampo e campo | 1 |
| A07 | Isc MAX = KI·Isc STC, con KI ≥ 1,25, da aumentare con riflessione o irraggiamento maggiore | All. B.2 p. 109 | V | sempre | KI modificabile; avviso con i bifacciali | 1 |
| A08 | Uoc MAX è la tensione nominale e Isc MAX la corrente d'impiego di ogni dispositivo del campo: Uoc MAX ≤ Vsys, ≤ Ue dei dispositivi, ≤ Ucpv degli SPD, ≤ ingresso massimo dell'inverter. SELV/PELV in c.c. solo con Uoc MAX ≤ 120 V; oltre 1500 V si è fuori dalla 64-8 | 712.512.1 p. 99; 712.533.101 p. 102; 712.534.102.3 p. 104; 712.414.101 p. 94; 64-8/1 11.2 p. 10 | V (inverter: I) | sempre | Verifica a semaforo per componente | 1 |
| A09 | Stringhe in parallelo con la stessa tensione nominale, cioè lo stesso numero di moduli equivalenti | 712.431.101 nota 2 p. 95 | V | parallelo | Verifica per ingresso MPPT | 1 |
| A10 | Finestra MPPT: Vmpp alla temperatura di cella massima ≥ minimo MPPT; Vmpp a Tmin ≤ massimo MPPT; Isc MAX ≤ massimo per ingresso; Pcc ≤ massimo. Sono limiti del costruttore, nessuna norma in archivio | schede costruttore | I | sempre | Calcolo con i coefficienti di Vmpp e Pmax e con NMOT (correzione rispetto alla R02) | 1 |
| A11 | Rapporto c.c./c.a.: nessun limite normativo. Potenza nominale per le soglie = min(inverter, ΣSTC), detto in chiaro solo per il Plug&Play. Con cosφ 0,9 a Pn: P ≤ 0,9·Sn | 0-21 3.54 nota, 3.61-3.62 p. 15-16, E.2 p. 250-251; 0-16 3.72-3.73 p. 20 | V (min() oltre P&P: I) | sempre | Rapporto c.c./c.a., stima del clipping e del taglio | 1 |
| A12 | Inverter monofase: al massimo 6 kW per fase (10 kW se il distributore lo concede); squilibrio entro il limite, altrimenti un automatismo stacca in 30 min o 1 min | 0-21 8.3-8.3.1.2 p. 65; G.3.1 h p. 263 | V | BT | Fase di ogni inverter e calcolo dello squilibrio | 1 |
| A13 | Inverter: capability triangolare fino a 11,08 kW, rettangolare oltre; in MT sotto 400 kW semicircolare limitata, cosφ ±0,90; componente continua ≤ 0,5% In; dichiarazione di conformità secondo All. C (taglia, SPI integrato o no, firmware) | 0-21 8.4.4.1-8.4.4.2 p. 75-77, All. C p. 244-246; 0-16 8.8.5.3 p. 125-126 | V | sempre | Campi d'archivio e controllo della taglia | 1 |

### Protezioni e cavi lato c.c.

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A14 | Protezione di stringa se Ns > 2 e 1,35·I_MOD_MAX_OCPR < (Ns-1)·Isc MAX; Ns si conta per ingresso MPPT se tra gli ingressi non circola corrente inversa | 712.431.101 p. 95 | V | Ns > 2 | Esito per ingresso | 1 |
| A15 | Taglia: stringa singola 1,1·Isc MAX ≤ In ≤ I_MOD_MAX_OCPR; gruppo di Np stringhe Np·1,1·Isc MAX ≤ In ≤ I_MOD_MAX_OCPR - (Np-1)·Isc MAX; su entrambe le polarità; fusibili gPV (60269-6) o interruttori bidirezionali con Ue ≥ Uoc MAX e potere di interruzione ≥ Isc MAX del campo; i diodi di blocco non sono una protezione | 712.431.102 p. 95-96; 712.432 p. 96; 712.533.101 p. 102; 712.512.101 p. 99 | V | protezione richiesta | Scelta automatica della taglia | 1/2 |
| A16 | Portata: cavo di stringa Iz ≥ Isc MAX; con Ns > 2 senza protezione Iz ≥ (Ns-1)·Isc MAX, con protezione Iz ≥ In; sottocampo con 1,1·Isc MAX ≤ In ≤ Iz; cavo di campo Iz ≥ Isc MAX del campo | 712.433.101-103 p. 97-98 | V | sempre | Verifica per tratto | 2 |
| A17 | Iz = Io·k1·k2 (35024-1 in aria, 35026 interrato); vale il tratto più severo; sezione minima 1,5 mm² Cu; per cavi fuori tabella CEI 20-21 o metodo dichiarato | 35024-1 2.1 p. 5; 64-8/5 523.1.2-523.1.3 p. 54, 523.7 e Tab. 52E p. 57; 82-25/3 9.3 p. 34 | V | sempre | Motore di portata con posa, k1, k2 | 2 |
| A18 | Classe II sul lato c.c.: la FAQ CEI del 03/03/2026 dice che l'H1Z2Z2-K basta fino a Uoc MAX 1500 V; altri cavi da 1,5 kV c.c. solo sotto 1125 V, oltre in tubi o canali isolanti o cavi da 4,5 kV c.c. | 712.410.102, 712.412.101 p. 94; 64-8/4 412.2.4.1 p. 23-24; FAQ CEI 03/03/2026 p. 1-2 (in `fonti\`) | V | lato c.c. | Verifica tipo di cavo e posa contro Uoc MAX | 2 |
| A19 | Posa: cavi non appoggiati sulla copertura; anelli di area minima con + e - e conduttore equipotenziale affiancati; cavi resistenti agli UV; connettori EN 62852 in coppie compatibili, apribili solo con attrezzo se accessibili | 712.521.101-102, 712.526 p. 101; 64-8/5 514.3.7 p. 33, 522.11.1 p. 53 | V | sempre | Area di spira per stringa dal tracciato 3D; verifica delle coppie di connettori | 2 |
| A20 | Controllo dell'isolamento sul lato c.c. (IMD 61557-8 o integrato nell'inverter); oltre 100 kWp raccomandata la localizzazione dei guasti (61557-9); un polo a terra solo con separazione galvanica, in un punto, con il dispositivo della Tab. 712.537 e conduttore ≥ 4 mm² | 712.421.101 p. 94-95; 712.537.2.2.103 p. 105; 712.538.101, 712.542.102-3.101 p. 106 | V | sempre | Verifica sulla scheda dell'inverter | 2 |
| A21 | Sezionamento: inverter sezionabile su c.c. e c.a. (la rete è la linea, il FV il carico); dispositivi senza potere di interruzione lucchettati; i semiconduttori non sezionano; ogni stringa escludibile e un organo generale in categoria DC-21A/B; il sezionatore a bordo inverter basta se manovrabile sotto carico o interbloccato con il c.a. (TNE) | 712.537.2 p. 105-106; 64-8/5 537.2.2-537.2.5 p. 117, 551.4.3.3.3 p. 154; 82-25/3 10.1 p. 34-35; TNE 2026-01 p. 11 | V (TNE: I) | sempre | Categoria d'impiego e simboli nello schema | 2 |
| A22 | Involucri esterni almeno IP44 e IK07; quadri 61439; cartello della Fig. 712.514.101 all'origine, ai contatori se lontani, al quadro dell'inverter; marcatura su ogni accesso al lato c.c. e sull'inverter; avvertenza per più alimentazioni o interblocco | 712.511.103-712.514.103 p. 99-101; 537.1.2 p. 116; 64-8/8 8.1.1.4 p. 83 | V | sempre | Elenco dei cartelli e posizione in pianta | 3 |

### Lato c.a., quadri e accumulo

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A23 | Linea c.a. dell'inverter: protezione sulla corrente massima del costruttore (o 1,1·In); IB ≤ In ≤ Iz e If ≤ 1,45·Iz; potere di interruzione ≥ Icc presunta, I²t ≤ K²S²; contributo dell'inverter al cortocircuito 110-120% In; Icc convenzionale al punto di connessione 6, 10 o 15 kA; cavo contatore-DG senza protezione al massimo 3 m | 712.433.104, 712.434.101 p. 98; 64-8/4 433.2 p. 49, 434 p. 51-53; 0-21 5.1.3 p. 28, 6.3 p. 33, 7.4.6.1 p. 44 | V | sempre | Calcolo delle linee c.a. e Icu minimo | 2 |
| A24 | Differenziale di tipo B sul lato c.a., salvo separazione semplice nell'inverter, trasformatore o dichiarazione del costruttore | 712.530.3.101 p. 102 | V | se c'è il differenziale | Tipo di differenziale dai dati dell'inverter | 2 |
| A25 | Generatore in parallelo alla rete: Icc e guasto a terra per ogni combinazione di sorgenti; generatore a monte delle protezioni dei circuiti terminali, altrimenti Iz ≥ In + Ig; protezione di interfaccia concordata con il distributore; interblocchi se c'è il backup | 64-8/5 551.2.2-551.7.7 p. 152-156 | V | sempre | Verifica topologica dello schema | 2 |
| A26 | Accumulo o backup: protezioni efficaci connesso e in isola, protezioni bidirezionali, sorgenti e accumuli al quadro principale, interblocchi EPS (schemi Fig. 12-16 della 0-21). La 712 non tratta l'accumulo | 64-8/8 8.1.1.1-8.1.3 p. 80-85; 712.1 p. 91; 0-21 8.2, 8.4.3 p. 55-71 | V | con accumulo | Verifiche per ogni modo di funzionamento | 2 |
| A27 | Caduta di tensione: nessun limite per il FV (712.525 ha solo il titolo); 4% raccomandato per l'impianto utilizzatore salvo indicazioni del committente; metodo 35023: c.c. 2R a 90 °C, c.a. k(R·cosφ + X·senφ) | 712.525 p. 101; 64-8/5 525 p. 59; 35023 §3-4 p. 4-5 | V | sempre | Limiti c.c. e c.a. configurabili; perdita di energia | 2 |

### Sovratensioni e fulmini

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A28 | SPD obbligatori nei casi 443.4 a-d; altrimenti CRL = fenv/(LP·Ng) con fenv 85 o 850 e LP = 2LPAL + LPCL + 0,4LPAH + 0,2LPCH (al massimo 1 km): se CRL < 1000 servono. Se la 443 li chiede: SPD in c.c., e in c.a. anche vicino all'inverter se dista oltre 10 m dall'origine. Se non li chiede: SPD in c.c. se L ≥ Lcrit = 115/Ng (residenziale), 200/Ng (a terra), 450/Ng (non residenziale), con L percorso massimo inverter-stringhe al netto dei tratti schermati | 64-8/4 443.4-443.5 p. 61-63; 712.443.101-103 p. 98-99; 712.534.103 p. 104 | V | sempre | Albero di decisione con L dal tracciato | 2 |
| A29 | SPD in c.c. secondo 61643-31; quelli interni all'inverter valgono solo se dichiarati; classe II con In ≥ 5 kA; classe I se c'è LPS e s non è rispettata (Iimp da IEC 61643-32 o almeno 12,5 kA); Ucpv ≥ Uoc MAX; ISCPV ≥ Isc MAX del campo; Up ≤ Uw (senza dati, Tab. 712.534: 1000 V → 6 kV, 1500 V → 8 kV) | 712.534.102-102.6 p. 102-104 | V | se servono | Verifica sulla scheda dell'SPD | 2 |
| A30 | SPD in c.c. vicino all'inverter, un secondo se l'ingresso del cavo nell'edificio dista oltre 10 m; collegamenti a+b+c ≤ 0,5 m (Up/f = Up + 1 kV/m); conduttori di terra Cu 6 mm² (classe II) o 16 mm² (classe I); tre casi tipici (senza LPS, LPS con s rispettata, LPS con s non rispettata) | 712.534.104-105 p. 104-105; 64-8/5 534.4.8-534.4.10 p. 98-100; 712 All. C p. 110 | V | se servono | Schema degli SPD e verifica di Up/f | 2 |
| A31 | Distanza di separazione dall'LPS: s = (ki/km)·kc·l (ki 0,08/0,06/0,04; km 1 in aria o 0,5; kc 1/0,66/0,44); se non rispettata, collegamento equipotenziale all'LPS, SPD di classe I e cavi schermati; in Italia non serve con struttura a telaio metallico o in c.a. continuo | 712.534.101 p. 102; 62305-3 6.3 Tab. 11-13 p. 53-55, nota naz. p. 17, 6.2.2 p. 50; 62305-4 F.1-F.3 p. 123-129 | V | con LPS | Calcolo di s su moduli, strutture e percorsi; elenco dei punti critici | 2 |
| A32 | Volume protetto con sfera rotolante (20-60 m), maglia o angolo; installazioni sul tetto da proteggere se alte oltre 0,3 m, più grandi di 1 m², più lunghe di 2 m o entro 1 m dal bordo; nessuna norma tratta le ombre di aste e calate | 62305-3 5.2.2 Tab. 2 p. 29, D.5.2.6.1 p. 90-91 | V | con LPS | Captatori come ostacoli che fanno ombra; verifica del volume protetto | 2 |
| A33 | Il FV e i circuiti in c.c. entrano nella valutazione del rischio; il progetto LPS va riconsiderato se cambiano struttura o servizi | 62305-1 5.1.2 p. 26; 62305-2 Tab. C.2 p. 81; 62305-3 p. 18 | V | edificio | Chiede esito ed edizione della valutazione e avvisa se va aggiornata | 3 |

### Connessione

Queste righe si aggiungono alle regole N04-N11 della R02.

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A34 | Una potenza per ogni soglia: nominale; in immissione richiesta (PIR); per la connessione = max(prelievo, PIR); accumulo incluso o escluso secondo la soglia (anche per il CCI) | 0-21 3.58, 3.61-3.62 p. 15-16, 7.4.4 p. 42; 0-16 All. O.2 nota 5 p. 486 | V | sempre | Tabella delle potenze, ciascuna con la sua soglia | 1 |
| A35 | Misure: M1 al punto di connessione; M2 vicino agli inverter, sezionabile, 4 fili; M3 con l'accumulo (Fig. 41-44); in MT M2 vicino al generatore | 0-21 12-12.5 p. 105-116; 0-16 12.1.2 p. 161-162 | V | sopra 1 kW | Contatori nello schema e in pianta | 2/3 |
| A36 | Tarature SPI: BT Tab. 13 (Tab. 14 sotto 800 W), MT Tab. 12; in MT TV dedicati, DDI ≤ 70 ms, logica OR, telescatto GSM da 100 kW, 67N se la rete in cavo supera l'80% della taratura 51N; DDI a contattore in AC3 | 0-21 8.6.2 p. 95-100, 8.2.2.3 p. 63; 0-16 8.8.3.1 p. 117, 8.8.6.5 p. 145, 8.8.7 p. 147-155, 8.5.12.2 p. 102-103 | V | sempre | Tabella delle tarature per relazione, regolamento e verbale | 3 |
| A37 | Documenti per il distributore. BT: unifilare definitivo, schemi funzionali, DiCo, dichiarazioni di conformità di inverter e SPI. MT: progetto della rete d'utenza, attestazione delle tarature (All. G), unifilare con interruttori, TA/TV, protezioni e cavi | 0-21 8.9 p. 102; 0-16 13.2 p. 175-176, All. G p. 295 | V | sempre | Elenco documenti e unifilare A3 | 3 |
| A38 | Regolamento di esercizio: BT oltre 11,08 kW All. G, fino a 11,08 kW Gbis (PIR, Pn, Icc, generatori con matricola e firmware, DDI, SPI, cosφ, P(U)); MT All. U con unifilare timbrato e Addendum tecnico | 0-21 8.7 p. 101, G.1-G.6 p. 261-271; 0-16 All. U p. 550-574 | V | sempre | Schede precompilate | 3 |
| A39 | Limitazione dell'immissione (SLI) se Pn > PIR: misuratore a valle del DG, funzione P(U)_115, rientro entro 3 s, errore ≤ 2,5%, prove L.5 e rapporto L.6 | 0-21 7.4.17 p. 53, L.1-L.6 p. 300-311; 0-16 6.5 p. 45-46 | V | Pn > PIR | Segnalazione e stima dell'energia tagliata | 1/3 |
| A40 | Prove dell'SPI: relè dedicato con cassetta (A.4.3), integrato con autotest (A.4.4); dichiarazione G.5; ripetizione ogni 5 anni oltre 11,08 kW; in MT prove con tarature definitive e rincalzo | 0-21 8.8 p. 102, A.4 p. 120-126, G.5 p. 266-270; 0-16 8.8.7 p. 147, E.5.2 p. 289 | V | da 800 W | Verbale precompilato | 3 |

### Progetto, elaborati, verifiche

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| A41 | Serve un professionista per: utenze condominiali; domestiche oltre 6 kW impegnati o oltre 400 m²; altre oltre 1000 V, oltre 6 kW o oltre 200 m²; luoghi speciali; LPS in edifici oltre 200 m³. Potenza impegnata = max(contrattuale, nominale dell'autoproduzione); il DM 37 comprende l'autoproduzione "fino a 20 kW nominale" | DM 37 artt. 1, 2 c.1 b) e), 5 c.1-2 p. 2-4 | V | sempre | Regola completa; N02 e N03 da correggere | 1 |
| A42 | Contenuti minimi: schemi, planimetrie, relazione, materiali, misure di sicurezza; su impianto esistente dichiarazione di compatibilità; allegati alla DiCo; deposito allo sportello unico entro 30 giorni | DM 37 art. 5 c.4 p. 5, art. 7 p. 6, All. I p. 9-10, art. 11 p. 7 | V | sempre | Sezioni della relazione ed elenchi automatici | 3 |
| A43 | CEI 0-2: livelli PFTE ed esecutivo, documenti obbligatori della Tab. 3-A; relazione specialistica (produzione e accumulo, fulmini, campi elettromagnetici, guasti serie, interruzione in caso d'incendio, sismica, accessi); calcoli per linea (corrente, lunghezza, cavo, posa, Iz, protezione, selettività, tarature di DG e SPI); schemi a blocchi e funzionali, unifilari con tabelle, piante quotate, elenco cavi con classe CPR; cartiglio, piano di manutenzione, CO2 evitata | 0-2 2.2-4 p. 8-32, Tab. 3-A p. 11-13, All. B p. 34-35; 64-8/5 514.5 p. 34-35 | V | sempre | Indice della relazione, elenco elaborati, cartiglio, tabelle dei circuiti | 3 |
| A44 | Verifica iniziale (64-8/6): esame a vista; continuità, isolamento (oltre 500 V prova a 1000 V c.c., almeno 1 MΩ, SPD scollegati), interruzione automatica, differenziali, prove funzionali (anche IMD), caduta di tensione; rapporto secondo 6.4.4; periodiche al massimo ogni 5 anni. Checklist interna: Voc e Isc per stringa, curve I-V, termografia, matrice stringhe-MPPT | 64-8/6 6.4.2.3-6.4.4 p. 8-14, 6.5.2.1 p. 16; 712.6.101 p. 107; checklist As-Built sez. 4 e 6 | V (checklist e 62446-1: I) | messa in servizio | Foglio prove con Voc e Isc attese per stringa e matrice delle stringhe | 1/3 |
| A45 | Producibilità secondo 82-25/3: coordinate, potenza, rendimento, profilo d'orizzonte, PVGIS citato; orientamento ottimo a Sud con orizzonte libero; distanza tra le file con l'angolo limite; albedo solo con i bifacciali; niente strutture solo zavorrate | 82-25/3 6.2 p. 8-9 | V | sempre | PVGIS con l'orizzonte dal modello 3D; distanza tra le file; avviso sulle zavorre | 1/2 |
| A46 | Metodo di stima, perdite, Performance Ratio e verifica tecnico-funzionale: assenti dalle parti 1-3 della 82-25 | 82-25/1 p. 1; 82-25/3 p. 1 | V (assenza) | sempre | Perdite dichiarate e modificabili | 1 |
| A47 | Fuori da questo filone: strutture, VVF, titoli autorizzativi, incentivi, officina elettrica | filoni B e C | - | - | Solo campi e rimandi | fuori |

## 4. CEI 82-25, parti 1, 2 e 3 (filone D)

Sono state lette per intero la 82-25/1:2026-03, la 82-25/2:2024-12 e la 82-25/3:2026-01. La 82-25/1:2026 ha lo stesso testo tecnico della 2022 (lo dice il frontespizio; confronto parola per parola): il documento 82-25/1;Ab abroga la 2022, la V1 e la CSV.

**Le parti 4, 5 e 6 non esistono ancora** [V, fonti CEI del 21/10/2026]:
- non sono pubblicate, non sono in inchiesta pubblica e non compaiono nel Programma nazionale di lavoro CEI 2026;
- la Parte 3 era passata in inchiesta come PRJ-3560 circa due mesi prima di uscire: conviene ricontrollare ogni tanto il servizio inchieste del CEI.

**Che cosa la guida dà e che cosa no.** Dà definizioni, dati da raccogliere e criteri qualitativi; formule poche, soglie quasi nessuna. Non contiene:
- correzioni in temperatura e definizione di NMOT;
- perdite di default;
- rapporto c.c./c.a.;
- dimensionamento di fusibili e SPD;
- limiti di caduta di tensione;
- monitoraggio.

Non dice nemmeno quali elaborati deve avere il progetto: sarà materia della Parte 4.

| ID | Requisito o dato | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| D01 | β = inclinazione sull'orizzontale; α = azimut misurato da Sud, negativo verso Est, positivo verso Ovest | 82-25/1 3.2.1.5-6 p. 10-11 | V | sempre | Una sola convenzione in ingresso, calcoli e testi (è anche quella di PVGIS) | 1 |
| D02 | STC: 1000 W/m², 25 ±2 °C, AM1,5. NOCT: 800 W/m², aria a 20 °C, vento 1 m/s, circuito aperto | 82-25/1 3.2.5.1 p. 29; 3.2.2.4 p. 16 | V | sempre | Costanti; archivio moduli con NOCT e NMOT (la Parte 2 chiede NMOT); la formula della temperatura di cella da IEC 61853 [I] | 1 |
| D03 | Potenza nominale del modulo = Pmax in STC; il simbolo "Wp" è sconsigliato | 82-25/1 3.2.5.2 p. 29 | V | sempre | Elaborati in W e kW | 3 |
| D04 | Efficienza del modulo = Pn / (1000 W/m² × area con cornice); del generatore ≈ Po / Σ aree | 82-25/1 3.2.5.3 p. 29; 3.2.5.5 p. 30 | V | sempre | Calcolo e confronto con la scheda | 1 |
| D05 | Po = Σ Pmax in STC; esclude il contributo posteriore dei bifacciali | 82-25/1 3.2.5.4 p. 29 | V | sempre | Calcolo di base | 1 |
| D06 | Po,cc = Po = potenza "ai fini amministrativi"; Po,ca = min(Po; Σ potenze degli inverter a una temperatura specificata), come CEI 0-21 3.61, CEI 0-16 3.72 e Comunicato ARERA 12/07/2022 | 82-25/1 3.2.5.6-8 p. 30 | V | sempre | Calcolarle e stamparle tutte e due con l'etichetta | 1 |
| D07 | Potenza del sistema di conversione = massima continuativa in un campo di temperatura ambiente | 82-25/1 3.2.5.21 p. 35 | V | sempre | Archivio inverter: Pac e temperatura di riferimento (declassamento) | 1 |
| D08 | Bifacciali: BNPI = 1000 + 135 W/m², BSI = 1000 + 300 W/m²; PmaxBIFI100 = PmaxSTC + BIFI·100; PmaxBIFI200 = PmaxSTC + BIFI·200; dati a STC e a BNPI, coefficienti di bifaccialità | 82-25/1 3.2.5.10-17 p. 31-33; 82-25/2 Tab. 5.1-5.2 p. 23-24 | V | bifacciali | Campi d'archivio; albedo e rapporto posteriore nella producibilità [I] | 1 |
| D09 | Soiling ratio = potenza con lo sporco / potenza a modulo pulito | 82-25/1 3.2.5.9 p. 31 | V | sempre | Perdita parametrica; la guida non dà valori | 1 |
| D10 | Gerarchia: cella, modulo, pannello, stringa, quadro di parallelo, sottocampo, campo = generatore FV (fino ai morsetti c.c. dell'inverter, strutture comprese), sezione, impianto. Il "generatore" della 82-25 non è quello della CEI 0-21 3.31 | 82-25/1 3.2.2-3.2.3 p. 15-26 | V | sempre | Modello dati con questi nomi | 1 |
| D11 | Tipologie: fisso, inseguitore a 1 o 2 assi, connesso, Plug&Play ≤ 350 W, BAPV, BIPV, agrivoltaico (anche "avanzato"), CPV | 82-25/1 3.2.4 p. 26-28 | V | sempre | Campo obbligatorio che attiva le regole | 1 |
| D12 | L'accumulo è sempre un generatore, anche lato c.c.; potenza per la connessione = Σ generatori + accumuli lato c.a. | 82-25/1 3.2.2.22 p. 21; 82-25/3 7.5.2 p. 18 | V | con accumulo | Bilancio delle potenze | 1 |
| D13 | Definizioni di revamping, repowering, componente rigenerato | 82-25/1 3.2.2.25, 3.2.5.22-23 p. 23, 35 | V | impianti esistenti | Domanda "tipo di intervento" e testo in relazione | 3 |
| D14 | Targa secondo EN 50380 (obbligatori: costruttore, tipo, serie, data e luogo di produzione, polarità, protezione massima da sovracorrente, tensione massima di sistema, classe di protezione, Pmax, Isc, Voc, Vmpp, Impp in STC con tolleranze); buona pratica: ente certificatore, norme, reazione al fuoco; marchi CE e RAEE | 82-25/2 5.1, Tab. 5.1 p. 22-23 | V | sempre | Campi obbligatori dell'archivio e controllo di completezza | 1 |
| D15 | Scheda tecnica, obbligatori anche: coefficienti di temperatura, sezione minima dei cavi, connettori, diodi, montaggio e carico massimo, fori di fissaggio ed equipotenziali, peso, certificazioni; buona pratica: NMOT, numero massimo di moduli in serie, reazione al fuoco | 82-25/2 Tab. 5.2 p. 24 | V il dato, I la verifica | sempre | Verifiche: sezione ≥ minima; moduli in serie ≤ massimo; connettore uguale; Voc di stringa ≤ Vmax; neve e vento ≤ carico ammesso | 1-2 |
| D16 | Documentazione in italiano, con installazione elettrica e meccanica, classe di qualifica, condizioni ambientali | 82-25/2 5.1 p. 22 | V | sempre | Controllo documentale | 3 |
| D17 | Omologazione CEI EN IEC 61215; sicurezza 61730-1/-2 (armonizzate, presunzione di conformità alla bassa tensione); marcatura CE | 82-25/2 5.2.1-5.2.2 p. 24-25; 5.7 p. 36-37 | V | sempre | Certificati con edizione in archivio; blocco se mancano | 1 |
| D18 | Certificato: numero e revisione, richiedente, produttore e stabilimenti, modelli, norme, test report, data, sorveglianza; organismo ISO/IEC 17065 accreditato, laboratori 17025; schema 1a (CB, senza sorveglianza) o 5 (con sorveglianza); edizione vecchia ritirata 36 mesi dopo la ratifica della nuova | 82-25/2 5.2.3-5.3 p. 25-30 | V | sempre | Lista di controllo "qualità del componente" | 3 |
| D19 | Produttore: ISO 9001, 14001, 45001; ispezione di fabbrica con il paese di stringatura, laminazione e prove (richiesto da alcuni incentivi) | 82-25/2 5.6 p. 33-36 | V | a richiesta | Campi facoltativi | 3 |
| D20 | Prove per ambienti particolari: nebbia salina 61701, ammoniaca 62716, neve non uniforme 62938, trasporto 62759-1, PID 62804, LID 63202-1, LeTID 63342 | 82-25/2 5.5 p. 31-32 | V la descrizione, I l'obbligo | costa, allevamenti, neve | Domande sul sito che fanno chiedere il certificato giusto | 1 |
| D21 | Tecnologie: PERC, TOPCon, HJT (bifaccialità fino a 95%), back contact, tandem, CdTe, amorfo, CIGS; celle tagliate a metà migliori con le ombre | 82-25/2 4 p. 5-22 | V | sempre | Campo "tecnologia" | 1 |
| D22 | RAEE: sotto 10 kW domestici (R4), da 10 kW professionali; produttore iscritto al Registro AEE | 82-25/2 5.8 p. 37-38 | V | sempre | Paragrafo sul fine vita secondo la potenza | 3 |
| D23 | Scatola di giunzione 62790 (≤ 1500 V, classe II); connettori 62852 (≤ 1500 V, 125 A per contatto, "non disconnettere sotto carico"); cavi EN 50618 (1,5 kV c.c., 90 °C) | 82-25/2 5.1 p. 22; 6 p. 39 | V | sempre | Archivio; verifica di tensione e corrente per contatto | 2 |
| D24 | Inclinazione e orientamento ottimali = massima energia annua; Sud se l'orizzonte è libero, altrimenti si segue il profilo reale; la riflessa conta solo con i bifacciali | 82-25/3 6.2 p. 8 | V | sempre | Ottimizzazione di β e α | 1 |
| D25 | Dati minimi per la simulazione: coordinate, potenza e rendimento, profilo d'orizzonte; PVGIS citato | 82-25/3 6.2 p. 9 | V | sempre | Dati obbligatori; orizzonte da PVGIS o dal modello 3D | 1 |
| D26 | Distanza tra file: αL = arctg(h/d); per una direzione ruotata di β, d' = d/cosβ; le file non devono darsi ombra sistematica | 82-25/3 6.2 Fig. 1 p. 10; 82-25/1 3.2.2.18 p. 20 | V | strutture inclinate | Calcolo di d con l'altezza del sole di progetto scelta (la guida non la dà) | 2 |
| D27 | Sui solai le NTC 2018 §7.2.4 non ammettono vincoli per solo attrito: la sola zavorra non basta; calcolo strutturale con NTC e Circolare 2019; CEI TR 82-74 per il vento, con 22 tipologie | 82-25/3 6.2 p. 9; 6.5 p. 13-14 | V | coperture e terreno | Domanda sul fissaggio; avviso bloccante con sola zavorra; scheda per lo strutturista | 2 |
| D28 | Inseguitori: la messa in sicurezza per vento può portare la resa sotto quella del fisso; IEC TR 63149; qualifica CEI EN 62817 | 82-25/3 6.3 p. 11 | V | inseguitori | Perdita parametrica; rapporto energia/suolo | 1 |
| D29 | BIPV: prodotti da costruzione (CPR, EN 50583-1/-2); categorie A/B tra 0° e 75°, C/D tra 75° e 90° (accessibili o no dall'interno), E strato esterno | 82-25/3 6.4 Tab. 1 p. 11-13 | V | BIPV | Categoria da β e accessibilità; richiesta della DoP | 3 |
| D30 | Ingressi dell'inverter: MPPT indipendenti per gruppi diversi (per esempio falde diverse); sezionatore; SPD; fusibili di stringa anche contro il ritorno dall'inverter | 82-25/3 7.1.1 p. 14 | V il dato, I la regola | sempre | Archivio MPPT; regola "orientamenti diversi su MPPT diversi" | 1 |
| D31 | Inverter senza trasformatore: non con moduli che richiedono un polo a terra (salvo trasformatore ad alta frequenza); inverter centrali con trasformatore BT/MT | 82-25/3 7.1.3 p. 15-16 | V | sempre | Campi "isolamento galvanico" e "polo a terra richiesto"; verifica | 2 |
| D32 | Tipi: microinverter, di stringa, ibrido, centralizzato, stazione; ottimizzatori | 82-25/3 7.2 p. 16; 8 p. 33 | V | sempre | Tipologia e ombre modulo per modulo | 1-2 |
| D33 | Conformità dell'inverter: bassa tensione + EMC (o RED); CEI EN 62109-1/-2; 62109-3 per micro e ottimizzatori; targa EN 50524; EMC secondo l'ambiente | 82-25/3 7.3-7.4 p. 17; 7.6.1 p. 31 | V | sempre | Campi d'archivio; domanda "ambiente residenziale o industriale" | 2 |
| D34 | Dichiarazione di conformità CEI 0-21/0-16, Sezione A: idoneità oltre 11,08 kW e limitazione della continua (BT), fino a o oltre 400 kW (MT) | 82-25/3 7.6.2-7.6.4 p. 21, 28, 31-33 | V | sempre | Campi d'archivio e coerenza con la taglia | 2 |
| D35 | Connessione: riassunto di 0-21 e 0-16 nelle edizioni 2025 | 82-25/3 7.5 p. 18-31 | V | sempre | Valori dalle edizioni 2026-07 (filone A) | fuori |
| D36 | Cavi c.c. H1Z2Z2-K; consigliati rosso per il + e nero per il -; con uccelli o roditori canali robusti e sigillati | 82-25/3 9.1 p. 33 | V | sempre | Archivio cavi; domanda "presenza di animali" | 2 |
| D37 | Portata con CEI-UNEL 35024-1 e 35026; caduta di tensione con 35023; tratti al sole fino a 80 °C; nessun limite di caduta | 82-25/3 9.3-9.4 p. 34 | V | sempre | Default 80 °C per i tratti esposti (vedi dubbio sui cavi) | 2 |
| D38 | Sezionamento c.c.: ogni stringa escludibile più un organo generale; interruttori di campo e sottocampo DC-21A/B (60947-3); sulle stringhe protette bastano sezionatori | 82-25/3 10.1 p. 34-35 | V | sempre | Categoria d'impiego in archivio e verifica | 2 |
| D39 | Lato c.a.: differenziale di tipo B con inverter senza trasformatore, salvo protezione contro l'immissione di continua; comando di emergenza e funzionale | 82-25/3 10.2-10.4 p. 35 | V | sempre | Regola sul tipo di differenziale; voci nello schema | 2 |
| D40 | Fulmini: 62305, Guida CEI 81-28, 712 All. C con tre casi | 82-25/3 11 p. 35-36 | V | sempre | Domande "LPS?" e "s rispettata?" | 2 |
| D41 | Quadri di parallelo e quadri c.c. secondo IEC 61439-2:2021; quadri c.a. 61439-1/-2 | 82-25/3 13-14 p. 36-37 | V | quadri | Lista di controllo del quadro | 2 |
| D42 | Trasformatori BT 61558, MT/BT serie 60076; cabine CEI EN 61936-1 e Guida CEI 99-4 | 82-25/3 12, 15 p. 36-37 | V | MT | Testo e archivio | 3 |
| D43 | Accumulo lato c.c. (ibrido o convertitore c.c./c.c.) o lato c.a.; carichi in isola con interblocco; litio con BMS necessario, sicurezza 62619 e 62933-5-2; dati BMS (tensioni, temperature, SOC/DOD, SOH, potenze, cicli) | 82-25/3 16 p. 38-40 | V | con accumulo | Archivio (chimica, accoppiamento, certificati, BMS); verifica "litio senza BMS" | 2 |
| D44 | Elenco dei riferimenti: leggi, ARERA, norme per 20 temi; norme non datate = ultima edizione; elenco non esaustivo e incompleto | 82-25/1 4 p. 36-48 | V | sempre | Le 20 categorie come scheletro dell'elenco in relazione, con le edizioni gestite dal programma | 3 |
| D45 | Reazione al fuoco secondo la guida VVF 2012 | 82-25/2 5.5.4 p. 32-33 | V | - | Superata dalla DCPREV 14030/2025 (filone C) | fuori |

**Le informazioni più interessanti** (secondo la lettura):
- le tre potenze con le loro fonti (D06);
- le Tabelle 5.1 e 5.2 della Parte 2 come lista di controllo della scheda modulo (D14-D15);
- i bifacciali (D08);
- come leggere un certificato di modulo (D18-D19);
- niente sola zavorra sui tetti piani e le 22 tipologie della CEI TR 82-74 (D27);
- i cavi al sole a 80 °C (D37);
- le categorie d'impiego DC-21A/B, il differenziale B e l'inverter senza trasformatore con moduli a polo a terra (D31, D38, D39);
- la Sezione A della dichiarazione di conformità dell'inverter (D34);
- le categorie BIPV ricavate dall'inclinazione (D29);
- la soglia RAEE a 10 kW (D22);
- le architetture dell'accumulo e i dati BMS (D43);
- i due significati di "generatore" (D10).

## 5. Analisi energetica e obblighi sugli edifici (filone B)

### La risposta alla domanda centrale

**(a) Relazione Legge 10 e requisiti minimi.**
- Il calcolo è mensile, con i metodi dell'art. 3 (UNI/TS 11300-1...6, UNI EN 15193) [V]:
  - DM 2025, All. 1, §1.1 b, p. 15: con gli stessi metodi si calcola l'energia rinnovabile prodotta nel confine del sistema;
  - art. 3, p. 12.
- I software devono restare entro ±5% dallo strumento di riferimento del CTI (DM 2015, art. 7, p. 7) [V].
- Dati climatici: UNI 10349-1 (All. 2, p. 51) [V nel testo, I sul contenuto].
- In Lombardia vale il metodo dell'All. H (disposizioni, 4.2, p. 5) [V]:
  - W = H_PV · W_pk · F_FV / I_ref, al netto degli ausiliari;
  - F_FV vale 0,70 per moduli non ventilati, 0,75 moderatamente ventilati, 0,80 molto ventilati;
  - se W_pk non è nota, W_pk = F_p · A (F_p 0,150 per il monocristallino);
  - H_PV dall'App. F (isotropo, albedo 0,2); Hb e Hd dei 12 capoluoghi lombardi dall'All. 1, Prospetto III;
  - le ombre vanno considerate (§11.11.1 p. 430-432; p. 482-489; p. 569-570).
- Grandezze, tutte mensili:
  - produzione FV;
  - quota usata per i servizi (stesso vettore e fino al fabbisogno del mese);
  - energia esportata;
  - EP ren, nren e tot, con fattori FV 0/1/1 e rete 1,95/0,47/2,42;
  - produzione dell'edificio di riferimento con efficienza 0,10.

**(b) APE.**
- Stesso metodo; quelli semplificati solo per il residenziale esistente fino a 200 m² [V].
- In Lombardia l'APE vale solo se fatto con CENED+2.0 o con un software autorizzato [V].
- Grandezze: EPgl,ren, riga "Solare fotovoltaico", energia esportata, potenza di picco.

**(c) Obbligo di integrazione delle rinnovabili** (D.Lgs. 199/2021, All. III vigente; ricostruito dalle note della GU 15/2026 e controllato con le modifiche dell'art. 29).
- P = k·S, con k = 0,05 per i nuovi e 0,025 per gli esistenti; +10% per gli edifici pubblici [V].
- Coperture dei consumi:
  - nuovi 60%;
  - ristrutturazione di 1° livello 40%;
  - 2° livello e ristrutturazione dell'impianto termico 15% (su H+C);
  - pubblici +5 punti.
- Il FV non conta per i servizi a effetto Joule, salvo l'unità in classe B o superiore [V].

**(d) Varianti lombarde e centri dati.**
- Lombardia:
  - coperture 60%, 65% dal 2027 per i nuovi, 50% per il 1° livello;
  - S = proiezione al suolo della copertura da foto aerea, esclusi i balconi non coperti;
  - k dal 2027 (già nella R02);
  - obbligo assolvibile su un edificio ospitante.
- Centri dati (DGR 6645 All. B):
  - superfici disponibili per tipo, con RS ≥ 60%;
  - potenza, produzione, quota coperta, REF;
  - il metodo di stima della producibilità è libero, ma va dichiarato con i calcoli [V].

**(e) Diagnosi.**
- La legge non prescrive un metodo per il FV.
- Contenuti attesi: energia prodotta, autoconsumata e ceduta, quota sui consumi [I].

**Dove PVGIS è ammesso** [I, dedotto da art. 3 e 7 del DM e dal 4.4 lombardo]:
- no per i numeri della Legge 10, dell'APE e delle coperture dell'All. III;
- sì come stima nella relazione FV di progetto, a sostegno dell'impossibilità tecnica o economica, nella relazione energetica dei centri dati (dichiarandolo) e nelle diagnosi.

### Matrice

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| B01 | Produzione FV mensile con i metodi dell'art. 3 (UNI/TS 11300-4/-5) | DM 2025 All. 1 §1.1 b p. 15; art. 3 p. 12 | V | a, b, c | Motore convenzionale distinto da PVGIS, 12 valori | 1 |
| B02 | Dati climatici UNI 10349-1 | DM 2025 All. 2 p. 51 | V (contenuto I) | a, b, c | Banca dati Hb e Hd versionata, caricata dall'utente che ha la norma; conversione sul piano inclinato | 1 |
| B03 | Lombardia: W = H_PV·W_pk·F_FV/I_ref; F_FV 0,70/0,75/0,80; F_p per tecnologia; ausiliari | All. H §11.11.1 p. 430-432 | V | Lombardia | Ingressi W_pk STC, ventilazione, tecnologia, ausiliari | 1 |
| B04 | Lombardia: H_PV con App. F (isotropo, albedo 0,2); Hb e Hd dei capoluoghi; comuni con i dati del capoluogo | All. H App. F p. 482-489; All. 1 p. 569-570; §3.3.5.1 p. 54 | V (comuni: I) | Lombardia | Prospetto III integrato nel programma; albedo modificabile | 1 |
| B05 | Ombreggiamenti sul piano dei moduli da considerare | All. H p. 431; App. C p. 472 | V (metodo: I) | a, b, d | Fattore mensile dal modello 3D, documentato | 2 |
| B06 | Fattori di conversione: FV 0/1/1; rete 1,95/0,47/2,42 | DM 2025 All. 1 Tab. 1 p. 16-17 | V | a, b, c | EP ren/nren della quota FV usata | 2 |
| B07 | Compensazione solo sullo stesso vettore e fino al fabbisogno mensile; niente tra mesi; niente effetto Joule | DM 2025 All. 1 §1.1 c-d p. 15-16 | V | a, b, c | Fabbisogni elettrici mensili per servizio; autoconsumo convenzionale; energia esportata | 2 |
| B08 | Impianti centralizzati: quote per servizio e per unità; potenza riferita all'intero edificio; in Lombardia ripartizione con i millesimi | DM 2025 §1.1 d.v p. 16, §3.4 p. 27; Lomb. 6.14 c p. 17 | V | più unità | Ripartizione per unità e servizio | 2 |
| B09 | Priorità di autoconsumo: FV, poi eolico, poi cogenerazione | All. H §11.4.2.1 p. 268 | V | APE Lombardia | Più generatori | 2 |
| B10 | Edificio di riferimento con gli stessi impianti; FV con η = 0,10 | DM 2025 App. A §1.2 c.2, Tab. 8 p. 40-41; Lomb. All. B Tab. 8 p. 5 | V | a | E_FV,rif = 0,10 × irradiazione × area dei moduli | 2 |
| B11 | Scala delle classi APE: riferimento senza rinnovabili | MASE pt. 5 p. 10; Lomb. 16.2 p. 34 | V | b | Avviso | 3 |
| B12 | Software entro ±5% dallo strumento CTI | DM 2015 art. 7 p. 7; LG APE §4.3 p. 85; MASE pt. 22 p. 15 | V | a, b | Esporta gli ingressi FV e confronta i risultati | 3 |
| B13 | Lombardia: APE solo con CENED+2.0; Legge 10 con l'All. H | Lomb. 4.2, 4.4 p. 5-6 | V | Lombardia | Scheda dati per CENED+ | 3 |
| B14 | Relazione tecnica: 5.2 descrizione e schemi; 6.d connessione, moduli, installazione, inclinazione, orientamento, potenza, % copertura; 6.e Edel, EPgl,ren, Eexp, EPgl,tot; ciò che manca va allegato | DM 2015 schemi All. 1 p. 54, 56; DM 2025 §2.2 p. 20 | V | a | Tabella e testo pronti | 3 |
| B15 | P = k·S anche per il 2° livello e per la ristrutturazione dell'impianto termico | All. III Sez. B p. 3 (GU 15/2026 p. 56); Lomb. 7.2 b p. 21, 8.8 p. 24, 8.10 p. 25 | V (nazionale: I) | c | Estendere N24 alle categorie | 1 |
| B16 | S lombarda: proiezione al suolo della copertura da foto aerea, esclusi i balconi non coperti; RET: la sagoma comprende gli aggetti oltre 1,50 m | Lomb. 6.14 c iii p. 17; Intesa All. A def. 8, 18 p. 58 | V | c, d | Poligono di copertura sull'ortofoto, con le opzioni | 1 |
| B17 | Edifici pubblici: +5 punti sulle coperture, +10% sulla potenza | Sez. B p. 5 p. 56; Lomb. 6.16 iv p. 18 | V | c, d | Dato "pubblico" | 1 |
| B18 | Coperture 60/65, 40/50, 15%; NZEB = requisiti + rinnovabili | Sez. B p. 1-2; Lomb. 6.14 c; DM 2025 §3.4 p. 27 | V | c | Contributo FV alla quota rinnovabile, con i dati del termotecnico | 2 |
| B19 | Posa su falda e su tetto piano secondo le regole della Sez. C (Lombardia 6.16 ii) | Sez. C p. 3; Lomb. 6.16 ii p. 18 | V | c | Verifica geometrica 3D (N20) | 1 |
| B20 | Valgono solo impianti su o nell'edificio o in pertinenza (≤ 3 volte l'impronta); il FV a terra conta per l'EP ma non per l'obbligo | Sez. C p. 2 p. 56; DM 2025 §1.1 d; Lomb. All. A def. 10 | V | c | Per ogni campo: "conta per l'obbligo" o "solo EP" | 1 |
| B21 | Impossibilità tecnica o economica: esame di tutte le opzioni; per nuovi e 1° livello EP_HCW,nren sotto il limite | Sez. D p. 56-57; D.Lgs. 5/2026 art. 13 p. 12; Lomb. 6.16 v-vii | V | c | Superfici escluse con motivo, potenza massima installabile, scarto, indicatori economici | 3 |
| B22 | Lombardia, edificio ospitante: dati in relazione, escluso dall'APE dell'obbligato, niente doppio conteggio | Lomb. 6.17-6.20 p. 18-19 | V | d | "Impianto ospitato" | 3 |
| B23 | Calcoli nella relazione ex art. 8 c.1 D.Lgs. 192/2005; copia al GSE | Sez. E p. 57; art. 26 c.5 p. 36 | V | c | Sezione rinnovabili esportabile | 3 |
| B24 | Centri dati: superfici disponibili per tipo; RS = Rimp/Sdisp ≥ 60%; superfici non usate motivate con relazione asseverata | DGR 6645 All. A §2.2 p. 8-9; L.R. 11/2026 art. 2 c.1 b p. 2 | V | d | Tabella superfici e RS dal modello | 1-2 |
| B25 | Relazione energetica dei centri dati: potenza, produzione, quota coperta, metodo di stima, planimetrie, calcoli; REF; anno di riferimento e ore equivalenti | DGR 6645 All. B p. 15-20; DGR 6814 Tab. 2.2/d1 p. 17-19 | V | d | Tabelle pronte, PVGIS dichiarato | 3 |
| B26 | Le soglie di 10 e 50 MW si riducono della potenza nominale FV installata nell'area | L.R. 11/2026 art. 5 c.12 p. 4 | V | d | Calcolo della potenza nominale FV | 1 |
| B27 | ERES-OS misurata (EN 50600-4-3); REF per centri dati da 500 kW IT | Reg. UE 2024/1364 art. 1 p. 3, All. II r p. 12, All. III d p. 15 | V | esercizio | Prevedere la misura | fuori |
| B28 | APE: energia esportata; raccomandazione FV con tempo di ritorno semplice | LG APE art. 4 c.4 p. 76-77, format p. 98-99; MASE pt. 20; Lomb. All. D | V | b | Campi e scheda di raccomandazione | 3 |
| B29 | Fattibilità dei sistemi ad alta efficienza nella relazione (nuovi e 1° livello) | DM 2025 §3.2 c.3 p. 23; Lomb. 4.16 p. 7 | V | a | Scheda di fattibilità FV | 3 |
| B30 | Diagnosi: dati misurati, profili di carico, costo sul ciclo di vita; rinnovabile prodotta, autoconsumata e ceduta | D.Lgs. 102/2014 art. 8 (Normattiva); linea guida ABI §3.8.2 | I | e | Import delle curve misurate; autoconsumo orario | 2-3 |
| B31 | Decorrenze secondo la data del titolo: DM dal 03/06/2026, All. III dal 03/08/2026 | Lomb. 4.7 p. 6; DM art. 11 p. 13 | V (03/08/2026: I) | tutti | Già nella R02 | 1 |
| B32 | Esclusioni: edifici temporanei, corpi armati, vincolati se incompatibile | art. 26 c.2, 3, 10 p. 36-37; Lomb. 6.26 | V | c | Dato di esclusione | 1 |

## 6. Prevenzione incendi, autorizzazioni, connessione, incentivi (filone C)

### Che cosa cambia rispetto alla guida VVF del 2012 [V]

La guida 2025 aggiorna la nota 1324/2012: i richiami del Codice alle note 1324 e 6334 vanno letti come riferiti alla guida nuova.

Novità della 2025:
- sottoinsiemi di 20 m, corridoi di 2 m, fascia di 1 m dal bordo;
- 1 m anche da aperture e impianti tecnici (nel 2012 valeva solo dagli EFC);
- regole per shed e facciate;
- classificazione BAPV, BIPV, pensiline e balaustre;
- regole per gli inverter e per gli accumuli;
- manutenzione: verifiche ogni 2 anni e termografia;
- progetto sempre obbligatorio.

È sparito il cartello a tutti i varchi di accesso dell'edificio.

Chi aveva già avviato il progetto al 01/09/2025 può completare con la guida 2012 (nota DCPREV 14668 del 10/09/2025).

| ID | Requisito | Fonte | V/I | Quando | Cosa fa il programma | Fase |
|---|---|---|---|---|---|---|
| C01 | La guida si applica a FV fino a 1500 V c.c. in attività soggette (All. I DPR 151) o al loro servizio; esclusi impianti a terra, plug&play, sotto 800 W, agrivoltaici oltre 100 m da edifici non soggetti, inseguitori a concentrazione; per le attività non soggette è un riferimento utile | LG 1.2 p. 5-6 | V | sempre | Chiede numero e categoria A/B/C dell'attività; profilo VVF obbligatorio o consigliato | 1 |
| C02 | Impianto "incorporato" se i moduli cadono anche in parte nel prisma verticale della pianta del fabbricato (aggetti e gronde compresi); "interferente" se una pensilina è dentro quel prisma, se inverter o tratti c.c. sono dentro, o se c'è rischio di propagazione per irraggiamento | LG 1.2 p. 2, 2.4 p. 8-9 | V | attività soggetta | Test geometrico tra moduli, inverter, quadri c.c. e impronta; classificazione di ogni porzione | 1 |
| C03 | Su un'attività soggetta esistente il FV è sempre una modifica rilevante: SCIA ex art. 4 c.7 DM 7/8/2012 se c'è conformità integrale e nessun aggravio; altrimenti, in categoria B/C, valutazione del progetto | LG cap. 6 p. 29; lettera di trasmissione p. 1-2; DM 7/8/2012 art. 4 c.6-7; DPR 151 artt. 3, 4 c.6 | V | attività soggetta | Albero di decisione; elenco dei documenti | 3 |
| C04 | Progetti avviati al 01/09/2025 (pratiche, contratti, progetto definitivo, lavori, preventivi con data certa) possono completare con la guida 2012 | Nota DCPREV 14668 del 10/09/2025 p. 2 (su I:) | V | avviati prima | Data di avvio; due set di regole, 2012 e 2025 | 1 |
| C05 | Il progetto parte dalla valutazione del rischio (obiettivi di 2.2, IEC TR 63226); disposizioni diverse ammesse se si dimostrano gli obiettivi | LG 2.2 p. 7-8; 3.3.5.1 p. 10; 4.2 p. 9; 4.3 p. 4 | V | sempre | Per ogni vincolo una "deroga motivata" con testo; capitolo "valutazione del rischio FV" | 3 |
| C06 | BAPV in copertura: sottoinsiemi di massimo 20 m in tutte le direzioni; corridoi di almeno 2 m senza componenti (cavi ammessi); fascia libera di almeno 1 m dal limite della copertura | LG 3.3.5.1, fig. 5, p. 15-16 | V | attività soggetta | Offset interno di 1 m; gruppi con lati ≤ 20 m e distanza ≥ 2 m; rapporto di verifica | 1 |
| C07 | Pannelli, condutture, inverter, quadri a più di 1 m (raggio) da EFC, altre aperture e impianti tecnici in copertura; sulle falde in proiezione orizzontale; l'impianto non deve ostacolare lo smaltimento del fumo | LG 3.3.4, 3.3.5.1, fig. 6-7, p. 15-17 | V | attività soggetta | Oggetti "apertura/EFC/impianto tecnico" con fascia di 1 m, anche per i cavi | 2 |
| C08 | Generatore a più di 1 m dalla proiezione delle pareti di compartimentazione sottostanti; non serve su solaio di copertura resistente al fuoco (eccezione solo per questa distanza) | LG 3.3.2, 3.3.5.1, p. 15-17 | V | attività soggetta | Linee REI disegnate; fascia di ±1 m, disattivabile con "copertura REI" | 2 |
| C09 | Shed: pannelli sulla falda opposta alle finestre, distanza ≥ 1 m dalle aperture (con fattore di vista), franco 0,1 m sulla falda contigua; 20 m, 2 m e 1 m; con zone libere sistematiche di 2 m in una direzione il limite sale a 30 m nell'altra; distanze riducibili con vetro-vetro B-s2,d0 e lucernari resistenti al fuoco | LG 3.3.5.1, fig. 8-10, p. 17-18 | V | shed | Tipo di copertura "shed" con le sue verifiche | 2 |
| C10 | Cavi mai direttamente sopra elementi di compartimentazione se non in passerelle; sopra muri tagliafuoco con protezioni, passerelle distanziate su supporti incombustibili; attraversamenti a tenuta | LG 3.3.2, fig. 4, p. 14-15 | V | attività soggetta | Allarme se il percorso attraversa linee REI; voci di computo | 2 |
| C11 | Sistema copertura-pannello BAPV, una di queste vie: 1) copertura A1; 2) strato EI 30 con strato continuo A1 su tutta la copertura o sull'area dei pannelli più 2 m per lato; 3a) moduli almeno classe E e Broof su tetto Broof, oppure prova CEI TS 82-89 con classe ≥ C_FV e posa uguale; 3b) analisi del rischio | LG 4.2, fig. 14-15, p. 22-24 | V | BAPV in copertura | Archivio moduli con reazione al fuoco, Broof, classe TS 82-89; stratigrafia; poligono "pannelli + 2 m" | 1-2 |
| C12 | Facciata BAPV: sottoinsiemi alti fino a 3 m e lunghi fino a 20 m; separazioni orizzontali incombustibili; 1 m dalle aperture; mai sulla verticale delle aperture senza elementi incombustibili; supporti A1 o strato EI 30+A1 su tutta la facciata; oltre 12 m di altezza antincendio V.13 o DCPREV 5043/2013 | LG 3.3.5.1, fig. 11; 4.3, p. 19, 24-25 | V | facciata | Modulo "facciata" con prospetti e aperture | 2 |
| C13 | BIPV: moduli 61730-2 e categoria EN 50583-1, classificati EN 13501-1; cappotti con EAD/ETA; facciate continue UNI EN 13830; edifici civili oltre 12 m: V.13 | LG 4.4, p. 25-26 | V | BIPV | Dati di prodotto obbligatori; avviso oltre 12 m | 1 |
| C14 | Pensiline, pergole e parcheggi con moduli BIPV come unica copertura: classe almeno B-s2,d0; balaustre FV almeno B-s2,d0; nessun requisito per BAPV sopra parcheggi non interferenti | LG 4.5-4.6, p. 26 | V | pensiline, balaustre | Verifica della classe secondo la struttura | 1 |
| C15 | Codice V.13 (edifici civili): con chiusura d'ambito SB o SC, involucro sotto il FV protetto (facciata A2-s1,d0 ed E 30-ef; copertura Broof o EI 30) e fasce di separazione ≥ 1,00 m; coperture SC protette per intero | Codice v10.6 (testo coordinato non ufficiale), V.13.3-V.13.5, p. 266-270 | V | Codice applicato | Dati per la classe SA/SB/SC; fasce come vincolo | 2 |
| C16 | Inverter all'aperto o in compartimento dedicato REI/EI 30; mai in locali piccoli senza ricircolo d'aria né in compartimenti di attività soggette; spazi liberi da manuale; più inverter non sulla stessa verticale; supporto A1 o EI 30+A1 | LG 3.2.2 e nota 1, 3.3.1.1, 3.3.2, p. 12-15 | V | attività soggetta | Oggetto inverter con zona di rispetto dalla scheda; controllo di allineamento verticale | 2 |
| C17 | Nessun componente FV nelle vie d'esodo né nei luoghi sicuri; parte c.c. e inverter fuori dalle zone ATEX | LG 3.3.3, 3.2.1, p. 11, 15 | V | attività soggetta | Strati di esclusione per esodo, luoghi sicuri, ATEX | 2 |
| C18 | Sezionamento di emergenza in posizione segnalata, protetta e accessibile ai soccorritori, che separa tutte le sorgenti compreso il FV; disattivazione descritta nel piano di emergenza | LG 3.3.5.2, p. 19-20; Codice S.10.5 c.2, S.10.6.1-2, p. 186-188 | V | attività soggetta | Voce di schema obbligatoria; posizione in pianta; tratti c.c. che restano in tensione; testo per il piano di emergenza | 2-3 |
| C19 | Protezioni del generatore contro sovracorrenti, guasti d'isolamento, guasti serie, sovratensioni e, se servono, correnti inverse | LG 3.3.5.3, p. 20 | V | attività soggetta | Lista di controllo dello schema | 3 |
| C20 | Cartello UV-resistente "ATTENZIONE: IMPIANTO FOTOVOLTAICO IN TENSIONE DURANTE LE ORE DIURNE (… Volt)" nell'area del generatore e ogni 10 m lungo le condutture c.c. | LG 3.3.5.4, fig. 13, p. 20-21 | V | attività soggetta | Cartelli d'area più ceil(L_cc/10) per tratto; posizioni in pianta | 3 |
| C21 | Moduli 61730-1/-2; valutare anche le classi "s" e "d" di reazione al fuoco | LG 3.2.1, 3.3.1, p. 11, 14 | V | sempre | Certificazioni obbligatorie nell'archivio | 1 |
| C22 | Accumulo: valutazione del rischio incendio ed esplosione; BESS in container in attività soggette: distanze esterna 20 m, di protezione 6 m, interna 4 m (6 m tra isole), dimezzabili con barriere; container ≤ 32 m²; recinzione ≥ 1,8 m | LG 2.1, 3.2.1.1, p. 7, 11-12; DCPREV 21021/2024 artt. 1, 3, Tit. IV tab. 1 (su I:) | V | accumulo | Oggetto BESS con tipo e fasce di distanza | 2-3 |
| C23 | Manutenzione: registro dei controlli (DM 1/9/2021); termografia periodica (IEC TS 62446-3); verifiche a ogni modifica e almeno ogni 2 anni; manuale d'uso e manutenzione | LG cap. 5, p. 27-28 | V | attività soggetta | Piano di manutenzione, modello di registro, planimetria degli accessi | 3 |
| C24 | Progetto FV sempre obbligatorio, firmato da tecnico abilitato; certificazioni del DM 7/8/2012 All. II | LG cap. 7, p. 30; DM 7/8/2012 All. II p. 12-13 | V | attività soggetta | Elenco documenti; omologazioni dei prodotti | 3 |
| C25 | Macchine elettriche con più di 1 m³ di liquido isolante combustibile (trasformatore in olio): attività n. 48 | DPR 151 All. I n. 48, p. 18 | V | cabina MT | Regola sul volume d'olio | 3 |
| C26 | Attività libera: a) sotto 12 MW integrati in copertura, stessa inclinazione e orientamento della falda, senza cambiare la sagoma, area ≤ copertura (anche in zona A); b) fuori zona A, sotto 12 MW su edifici e strutture, fino a 1 MW a terra adiacente all'edificio servito; c) a terra sotto 5 MW in aree industriali, commerciali, discariche, cave; d) strutture turistiche; accumuli fino a 10 MW | TU FER All. A sez. I, p. 19 | V | sempre | Dati: zona A, destinazione dell'area; complanarità (inclinazione e azimut rispetto alla falda); area moduli ≤ copertura | 1 |
| C27 | Si passa a PAS con beni culturali o paesaggistici (salvo commi 4-6), aree protette o Natura 2000, vincoli idrogeologici, difesa, sismici, prevenzione incendi; interferenze con opere pubbliche, fascia di rispetto stradale, accessi | TU FER art. 7 c.2, 4-8, p. 4 | V | sempre | Lista dei vincoli; distanza dalla strada; avviso per attività soggetta (dubbio 1 del filone) | 1-3 |
| C28 | Sempre: NTC e Codice della strada; compatibilità urbanistica; disponibilità della superficie; acque meteoriche; "progetto unico" con potenze sommate se stessa fonte, aree vicine e stesso centro di interessi | TU FER art. 6 c.3, 3-bis; art. 7 c.1, 7; p. 4 | V | sempre | Somma degli interventi collegati; superfici impermeabilizzate | 1-3 |
| C29 | PAS: sotto 10 MW su edifici fuori dai casi dell'All. A; sotto 12 MW in aree idonee; sotto 10 MW con rimozione dell'amianto; fino a 1 MW negli altri casi. Autorizzazione unica regionale da 1 a 300 MW. Documenti PAS; oltre 1 MW compensazioni dall'1 al 3% del valore della produzione | TU FER All. B sez. I, All. C sez. I a, art. 8 c.4; p. 5, 21, 23 | V | fuori dall'attività libera | Albero del regime; area occupata; valore della produzione | 3 |
| C30 | Modifiche in attività libera: a terra senza aumento d'area e altezza al più +50%; su edifici altezza mediana dei moduli non oltre la balaustra, angolo non aumentato; accumuli entro +20% potenza, +50% altezza, +30% volume | TU FER All. A sez. II a, n; p. 19-20 | V | revamping | Confronto stato di fatto e progetto | 2 |
| C31 | Aree idonee per legge: edifici e loro pertinenze, aree industriali, terziarie, logistiche e di centri dati, coperture di parcheggi; in area idonea parere paesaggistico non vincolante; a terra in zona agricola solo nei casi dell'art. 11-bis c.2; nei siti UNESCO solo All. A. Lombardia: L.R. 10/2026 | TU FER artt. 11-bis, 11-quater, 11-quinquies, 12 c.10, p. 12-15; L.R. 10/2026 [I] | V/I | sempre | Area idonea, zona di accelerazione, zona agricola, UNESCO, distanza dai ricettori | 3 |
| C32 | In attività libera il modello unico va trasmesso su SUER entro 5 giorni dall'esercizio ("Modello Unico Parte III", DM 15/07/2026) | TU FER art. 5 c.2, art. 7 c.10 [V]; DM 15/07/2026 [I] | V/I | attività libera | Scheda dati: potenze, componenti, coordinate, catasto, urbanistica | 3 |
| C33 | Richiesta di connessione TICA: potenze (immissione, nominale, prelievo, ausiliari, accumulo), POD, date, piano particellare, disponibilità del sito, unifilare firmato con DG, DDI, DDG e misure, destinazione dell'energia, incentivi; sotto 10 MW al distributore, oltre a Terna | TICA art. 6.1-6.3, p. 23-25 | V | sempre | Pacchetto dati e unifilare di connessione | 3 |
| C34 | Modello unico (DM 297/2022) fino a 200 kW, potenza = min(moduli STC, inverter), POD esistente non condiviso; il modello del DM 19/05/2015 esteso a 50 kW | TICA def. aaa) e art. 6bis, p. 14, 26-27; D.Lgs. 199/2021 art. 25 coordinato | V | fino a 200 kW | Regola di ammissibilità | 3 |
| C35 | MT con FV ≥ 100 kW (min tra moduli e inverter): CCI con funzione PF2 entro l'esercizio, altrimenti niente attivazione; impianti esistenti entro 31/12/2026 (≥ 1 MW), 31/12/2027 (500 kW-1 MW), 31/03/2028 (100-500 kW) | ARERA 385/2025 artt. 2-5, 8, p. 21-29; ARERA 564/2025 p. 22-23 | V | MT, ≥ 100 kW | Voce CCI nello schema con avviso | 1-3 |
| C36 | CACER: impianti fino a 1 MW, componenti nuovi, stessa cabina primaria per l'incentivo, linea diretta fino a 10 km, moduli certificati 61215/61730 e produttore iscritto al registro AEE, domanda entro 120 giorni | DM 414/2023 artt. 2-5, p. 12-15; Regole GSE §1.2.1, p. 11-15 | V | autoconsumo diffuso | POD e cabina primaria di ogni membro; verifica dei requisiti | 3 |
| C37 | Energia condivisa oraria = min(immessa, prelevata); tariffa incentivante con base e tetto secondo la potenza, +10 €/MWh al Nord, fattore F con contributi in conto capitale; quota d'obbligo P0 = k·S esclusa con il fattore (P - P0)/P | DM 414/2023 All. 1, p. 23-24; Regole GSE p. 15-16, 41-46 | V | autoconsumo diffuso | Simulazione oraria 8760 di produzione e prelievi; stima di incentivo e valorizzazione | 1-3 |
| C38 | Ritiro dedicato: prezzo zonale orario o prezzo minimo garantito (fino a 1 MW: 4,75 c€/kWh nel 2026 fino a 1,5 GWh l'anno); scambio sul posto chiuso | pagine GSE; TNE 2025-10 p. 12 | I | vendita | Energia immessa oraria per zona; ricavo annuo | 1 |
| C39 | FER X: potenza = min(moduli, inverter); accesso diretto fino a 1 MW, aste oltre; componenti nuovi; esercizio entro 36 mesi; criteri su origine e cybersicurezza nel decreto 2026 | TNE 2025-04 p. 1-6; fonti secondarie | I | incentivo | Origine dei componenti e date di cantiere | 3 |
| C40 | Iperammortamento 2026 (investimenti dal 01/01/2026 al 30/09/2028): moduli e celle prodotti nell'UE con efficienza di cella ≥ 23,5%, oppure celle bifacciali HJT o tandem UE ≥ 24,0%, iscritti al registro ENEA | L. 199/2025 c.427-429; DL 181/2023 art. 12; DL 19/2024 art. 38 | V | impresa | Paese di produzione di modulo e celle, efficienza, tecnologia, registro ENEA; regola di ammissibilità | 1 |
| C41 | Conto Termico 3.0: FV e accumulo solo con la sostituzione del riscaldamento con pompe di calore; da 2 kW a 1 MW; moduli con tolleranza solo positiva, carico ≥ 5400 Pa, coefficiente di temperatura non peggiore di -0,37 %/°C, garanzia ≥ 10 anni, rendimento ≥ 90% a 10 anni; inverter con rendimento europeo ≥ 97% | DM 07/08/2025 art. 5 c.1 h; All. 1, GU p. 33 e 45 [V]; regola del 105% [I] | V/I | PA e terziario | Filtro sull'archivio di moduli e inverter | 1-3 |
| C42 | Strutture: in attività libera si rispettano le NTC; NTC §8.2-8.3 per interventi impiantistici e valutazione della sicurezza; §3.4.3.1 accumulo di neve; LG 3.3.1 carico permanente dei componenti | TU FER p. 4; NTC 2018 p. 63, 294-296 (su I:); LG p. 13-14 | V | sempre | Carico aggiunto per campo; tabella per lo strutturista; zone di accumulo di neve | 2-3 |

## 7. Punti dubbi

Sono raccolti per tema, da tutti i filoni. Per ciascuno il programma deve dichiarare la scelta fatta.

**Energia e obblighi**
- Decorrenza dell'All. III: "180 giorni dall'entrata in vigore del presente decreto", ma non è chiaro di quale (D.Lgs. 199 o D.Lgs. 5/2026). La R02 assume il 03/08/2026.
- Tetti piani in Lombardia: la 6.16 ii impone solo moduli aderenti con l'inclinazione della falda e non ha la regola nazionale balaustra/30 cm. Serve un chiarimento della Regione.
- Effetto Joule: l'eccezione per la classe B o superiore c'è nel testo nazionale, non nella 6.16 i lombarda.
- Ampliamenti: per il MASE non sono soggetti agli obblighi rinnovabili. La Lombardia applica k alla parte ampliata e chiede la verifica, citando ancora il D.Lgs. 28/2011 abrogato.
- "Edificio pubblico" non è definito (di proprietà pubblica o a uso pubblico).
- S: la sagoma secondo il RET (aggetti oltre 1,50 m) non coincide con la copertura vista da foto aerea secondo la Lombardia. Restano aperti portici, pensiline attaccate, interrati sporgenti.
- All. H lombardo:
  - ammette il recupero tra mesi "nel rispetto della quota limite" senza dire quanto vale, mentre il DM lo vieta;
  - H_PV è definita giornaliera media mensile, ma il risultato è mensile;
  - i valori di F_FV vengono dalla UNI/TS 11300-4 del 2012.
  
  Da verificare con CENED+ e con la UNI/TS 11300-4:2016.
- Relazione tecnica: lo schema del 2015 riporta ancora P = (1/K)·S. Il nuovo format nazionale e l'All. C lombardo non sono usciti.
- Centri dati: non è chiaro se Rimp sia l'area dei moduli o l'impronta delle file, né se la potenza nominale della L.R. 11/2026 sia in c.c. o in c.a.
- Dati UNI 10349-1: protetti da licenza e la norma è in revisione (progetto UNI1616699). La banca dati climatica va versionata.

**Progetto elettrico e CEI 82-25**
- Tmin: la 712 non dice da dove prenderla, e nessuna norma dà la Tmax per la finestra MPPT. Da registrare la fonte; per chiudere serve la CEI EN IEC 62548-1.
- Cavi, tre temperature diverse: 70 °C sul retro dei moduli (712), 55 °C (35024-1), fino a 80 °C al sole (82-25/3).
- Portata dei cavi solari: la CEI-UNEL 35024-1:2020 §1.1 esclude i "cavi per impianti fotovoltaici" [V], mentre la 82-25/3 9.3 la indica.
  - Le schede H1Z2Z2-K in archivio danno portate a 60 °C ambiente e 120 °C sul conduttore, con coefficienti propri (per esempio `l'archivio locale delle norme\catalogs\Cavi\02-La-Triveneta-Cavi\schede-tecniche\NPE® SUN H1Z2Z2-K (Eca).pdf`).
  - Probabilmente vengono dalla EN 50618, che manca.
- H1Z2Z2-K e classe II: la FAQ CEI del 03/03/2026 porta il limite a 1500 V e prevale sul TNE 04/2025, che diceva 1125 V.
- Differenziale di tipo B, tre criteri: 712.530.3.101, 82-25/3 10.2, TNE 2025-11. Si applica la 712, che è la norma.
- 712.6.101 rimanda alla "EN 61215" per documentazione e collaudo: probabilmente è un refuso per EN 62446-1.
- CEI 0-21:2026, soglia 59.S2: 0,5 s in Tab. 13 (p. 97), 0,2 s in 8.5.2 a) (p. 89) e nella 82-25/3. Il programma stampa la Tab. 13 con un avviso; serve un quesito al CEI.
- Fulmini: la 712.443.102 usa NG, la 62305 3a ed. usa NSG ≈ 2·NG; per Lcrit si usa NG. La CEI 81-29:2020 va con la 62305:2013, applicabile fino al 31/10/2027: registrare l'edizione usata.
- DM 37: comprende l'autoproduzione "fino a 20 kW nominale"; oltre la situazione è grigia (TNE 2026-01, [I]).
- Potenze: la "potenza nominale" cambia significato con la soglia; squilibrio 6 o 10 kW; caso ambiguo a 11,08 kW esatti; in MT tra 11,08 e 30 kW non è chiaro quale norma valga.
- Accumulo: la 712 non lo tratta; servono 64-8/8-2, 551.8, 62485 e la 62485-5 (manca).
- Ambito della 64-8: la 64-8/1 11.4 esclude gli "impianti di produzione". Per i grandi impianti a terra non al servizio di un'utenza va verificato.
- 82-25:
  - NOCT (Parte 1) o NMOT (Parte 2), senza formula;
  - temperatura di riferimento di Po,ca non fissata;
  - la Parte 3 è scritta sulle edizioni 2025 di 0-21 e 0-16: due frasi da verificare sulle 2026 ("in MT fino a 11,08 kW nessuna norma di connessione, fino a 30 kW la 0-21"; "DG semplificato fino a 400 kW");
  - refusi nella Parte 1;
  - elenco di norme incompleto;
  - le sezioni 5.4 e 5.8 della Parte 2 sono superate.
- Stima della producibilità, Performance Ratio e verifica tecnico-funzionale (il classico Pcc > 0,85·Pnom·G/GSTC con G > 600 W/m², e Pca > 0,9·Pcc) si trovano solo nella bozza C.1005:2008 su I:. Valgono come riferimento storico [I].

**Prevenzione incendi e autorizzazioni**
- TU FER art. 7 c.2: con una lettura larga del "vincolo afferente la prevenzione incendi", ogni FV su attività soggetta finirebbe in PAS. Servono FAQ MASE o GSE; intanto il programma dà solo un avviso.
- "20 m in tutte le direzioni" (LG 3.3.5.1): lati del rettangolo ≤ 20 m (come fa pensare la fig. 5) o ingombro massimo? Proposta: lati ≤ 20 m, con un controllo più severo a scelta.
- Tensione da scrivere sul cartello: non specificata. Proposta: Uoc MAX del generatore.
- Potenza per le soglie del TU FER: non definita. Nel dubbio si usa Po,cc.
- Lombardia: la L.R. 10/2026 art. 4 toglie le semplificazioni nelle aree vincolate, mentre la legge nazionale rende idonei per legge tutti gli edifici. Da verificare sul BURL.
- Codice di prevenzione incendi: in archivio c'è solo il testo coordinato non ufficiale v10.6.
- Linee guida BESS: le distanze 20/6/4 m valgono per i container di tipo "c" nelle attività soggette, non per le batterie domestiche o a parete.
- Da confermare su testo ufficiale [I]: Modello Unico Parte III, FER X 2026, regola del 105% nel Conto Termico 3.0, prezzo minimo garantito 2026, decreto dell'iperammortamento, modifiche al TICA dopo la 361/2023.

## 8. Da procurare

**Norme CEI, IEC, EN a pagamento**, da chiedere a chi gestisce gli abbonamenti:
- Fase 1:
  - CEI EN IEC 62548-1 (progetto del campo FV; IEC 62548-1:2023 + AMD1:2025);
  - CEI EN 50380;
  - CEI EN IEC 61215 serie 2021;
  - CEI EN IEC 61853-1/-2/-3/-4;
  - CEI EN IEC 60891 e IEC TS 60904-1-2;
  - CEI EN 50530 e 50524;
  - IEC 61724-1:2021 (Performance Ratio e monitoraggio);
  - CEI TR 82-74;
  - IEC 61730 ed. 2023 (in archivio c'è la 2018).
- Fase 2:
  - CEI EN 50618 (CEI 20-91) e IEC 62930;
  - CEI-UNEL 35026;
  - CEI EN IEC 60947-3;
  - CEI EN 62852 e 62790;
  - Guida CEI 81-28 (verificare se in vigore);
  - CEI EN IEC 61643-31 e IEC 61643-32;
  - CEI EN 62109-1/-2 e IEC 62109-3;
  - CEI EN 62920;
  - CEI EN IEC 62619, 62933-1, 62933-5-2;
  - CEI EN IEC 62485-5;
  - CEI EN IEC 63112;
  - IEC 61439-8, quando sarà recepita.
- Fase 3:
  - CEI EN 62446-1 (CEI 82-56) con A1, e 62446-2;
  - IEC TS 62446-3;
  - CEI EN 50583-2;
  - CEI EN 61936-1 e Guida CEI 99-4;
  - serie CEI EN 60076;
  - CEI EN 62817;
  - IEC TR 63149;
  - CEI TS 82-89;
  - IEC TR 63226;
  - CEI EN 61082-1 e 81346-1;
  - CEI 0-23;
  - per ambienti particolari: 61701, 62716, 62938, IEC TS 62804-1.

**Norme UNI a pagamento**
- UNI/TS 11300-4 e -5:2016;
- UNI 10349-1:2016 con EC 1-2017 (in revisione);
- UNI EN 15316-4-3:2018;
- UNI CEI EN 16247-1/-2:2022;
- UNI EN 13501-5, UNI CEN/TS 1187, UNI CEN/TS 16459.

**Atti gratuiti da scaricare** in `l'archivio locale delle norme\laws`:
- NTC 2018 (DM 17/01/2018) e Circolare 21/01/2019 n. 7: c'è una copia su I:;
- D.Lgs. 49/2014 RAEE, testo vigente;
- L.R. Lombardia 10/2026 (aree idonee, BURL suppl. 22 del 25/05/2026);
- DGR XII/6153/2026;
- DGR XI/695/2018 (RET lombardo);
- All. C "Relazione tecnica" del decreto lombardo 18546/2019;
- DCPREV 5043/2013 (facciate);
- DM 15/07/2026 "Modello Unico Parte III";
- DM 297/2022;
- decreto FER X 2026;
- D.Lgs. 102/2014 e D.Lgs. 199/2021, testi vigenti consolidati.

**Già scaricata:** la FAQ CEI CT 82 "Cavi e condutture c.c. per impianti FV" del 03/03/2026, in `C:\Users\utente\Elettrico\output\programma-fv\fonti\`. Se va in archivio, Daniel decide dove.

## 9. Archivio: aggiunte del 21/10/2026 e anomalie

**Aggiunti in `l'archivio locale delle norme\laws`** dalle ricerche (verificati: si aprono, sono indicizzati):
- DM 26/06/2015, i tre decreti, testo originale;
- DM 28/10/2025;
- circolare MASE prot. 125135 del 18/06/2026;
- Allegati H, B e D delle disposizioni lombarde;
- D.Lgs. 190/2024: originale GU e testo vigente da Normattiva al 21/10/2026, impaginato da noi, non un PDF ufficiale;
- ARERA 564/2025;
- TICA testo integrato a 361/2023;
- DM MASE 414/2023 CACER, copia GSE;
- Regole operative GSE CACER del 16/07/2025;
- DM 07/08/2025 Conto Termico 3.0.

Daniel ha aggiunto in `standards\cei` la CEI 82-25/1:2026-03 e la 82-25/3:2026-01.

**Anomalie nei nomi dei file**, non toccate (rinominare solo con il via di Daniel):

| File | Che cosa contiene davvero |
|---|---|
| `standards\cei\CEI 0-2 - 2025-03.pdf` | la CEI 3-15:2005-03, identica byte per byte a `CEI 3-15 - 2005-03.pdf` (MD5 2f92b614...) [V] |
| `CEI 3-22 - 2025-03.pdf` e `CEI 3-23 - 2025-03.pdf` | edizioni 2005-03, secondo il filone A [I] |
| `CEI EN IEC 50583-1 - CEI 82-54 - 2016-07.pdf` | la CEI EN 50583-1, senza "IEC" [I] |
