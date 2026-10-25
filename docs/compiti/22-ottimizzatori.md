# Compito 22: gli ottimizzatori di potenza (SolarEdge) nella fase Impianto

Richiesta di Daniel del 24/10/2026 (R57): «gli ottimizzatori (SolarEdge) dopo»; fatto il 25/10/2026 nel ramo
`ottimizzatori` (da `grafica`, c99a6f5), registrato come R92 in `docs/richieste.md`. Daniel progetta impianti SolarEdge
per lavoro: ogni regola viene dai documenti ufficiali di SolarEdge, con codice, data e pagina, e i casi che sono una
lettura di Meridiana sono segnati [I].

## Che cosa fa

- **Inverter a tensione di stringa fissa.** Un inverter SolarEdge (nessun MPPT, la stringa tenuta a 380 V monofase o
  750 V trifase) è riconosciuto dal suo record (`dc_architecture`, oppure produttore SolarEdge senza finestra MPPT, per i
  progetti salvati prima) e ha **ottimizzatori di potenza**: quelli scelti nel catalogo («Ottimizzatori…» nella sua
  riga dell'ispettore Inverter, uno o due moduli ciascuno dove l'ottimizzatore li accetta, ✕ per tornare alla proposta)
  oppure quelli che Meridiana propone per il modulo (il più piccolo della serie S che lo accetta; sugli inverter
  commerciali due moduli su un S1000, S1400 o S1200), detti «proposti da Meridiana». Gli ingressi sono le unità Synergy
  (SE50K: 2, SE90K e SE100K: 3), uno per gli altri.
- **Proposta delle stringhe.** Lungo il percorso della strategia scelta (avanti e indietro, una fila per volta),
  stringhe il meno numerose possibile e il più possibile uguali; entro la potenza che la stringa porta in continuo
  quando la potenza CA dell'inverter la supera (niente taglio nei picchi), poi entro il limite della tabella, senza mai
  scendere sotto il minimo di ottimizzatori; un sottocampo troppo piccolo per una stringa sua si unisce agli altri dello
  stesso inverter (due falde est-ovest di 6 moduli fanno una stringa di 12). Le stringhe si distribuiscono sulle unità
  Synergy, la meno carica per prima. La stringatura a mano resta com'era.
- **Verifiche** (pannello Verifiche, area stringhe, con la fonte di ciascuna; dettagli con perché e che cosa fare): il
  modulo sul suo ottimizzatore, la stringa, l'inverter (sezione seguente). Lo stato della stringa (semaforo) viene da
  queste; non c'è più la regola di PVsyst delle stringhe identiche sullo stesso ingresso (SolarEdge ammette stringhe di
  lunghezze e orientamenti diversi).
- **Barra della fase.** Con una stringa scelta, al posto delle tensioni: ottimizzatori contro minimo e massimo, i moduli
  (con due per ottimizzatore), la potenza contro quella ammessa e quella portata, la tensione di stringa. Pannelli
  flottanti e ispettore dicono «Unità Synergy k» o «Stringhe», e per ingresso «stringhe da 14 a 30 ottimizzatori, fino
  a 18,50 kW ciascuna, 13,50 kW portati, 4 coppie d'ingresso».
- **Producibilità** (`simulate.py`, «Come è calcolato» con formula e fonti): sui moduli dietro un ottimizzatore nessun
  mismatch fra i moduli soli sul loro (due su uno lo conservano); effetto elettrico delle ombre degli ostacoli contato
  ottimizzatore per ottimizzatore; il rendimento pesato dell'ottimizzatore come passo della catena («Ottimizzatori di
  potenza»); la stringa tagliata oltre la potenza che porta (corrente d'uscita degli ottimizzatori per la tensione fissa
  dell'inverter, passo «Stringhe di ottimizzatori oltre la loro potenza continua», con la nota oltre lo 0,5 %); i cavi
  in continua con la corrente che segue la potenza (tensione fissa).
- **Relazione.** Nel capitolo Impianto elettrico, per ogni inverter con ottimizzatori: quali (e se proposti), la
  tensione di stringa, la tabella di SolarEdge con documento e pagina, per unità Synergy stringhe, moduli, ottimizzatori,
  kWp e stato, le verifiche di ogni tipo di stringa con la fonte, quelle dell'inverter; negli allegati i dati
  dell'ottimizzatore; il modello Sintetica scrive la frase degli ottimizzatori.
- **Meridio** legge stringhe di ottimizzatori con limiti e fonti (`read_results`, sezione stringhe; corretto anche un
  difetto che faceva fallire quella sezione: usava il piano dell'ultimo ingresso al posto dell'impianto).

## Le regole e le loro fonti

I PDF sono archiviati in `%USERPROFILE%\Elettrico\reference\catalogs\SolarEdge` (cartelle `optimizers`, `inverters`,
`application-notes`) con `README_INDICE.md` e `SHA256SUMS.csv`. Le tabelle di progetto sono state lette anche
sull'immagine della pagina (celle unite).

| Regola | Valore | Fonte |
|---|---|---|
| Potenza del modulo a STC entro la potenza CC nominale d'ingresso dell'ottimizzatore | S440 490 W, S500 550 W, S500B e S650B 650 W, S1000 1100 W, S1200 1300 W, S1400 1400 W; «sono permessi moduli con tolleranza di potenza fino al +5 %» | DS-000091-IT (14/09/2026) p. 2 nota 1; DS-000105-IT (01/12/2025) p. 2 nota 2; DS-000205-EU (08/01/2024) p. 2 nota 1 |
| Voc del modulo alla temperatura minima entro la tensione d'ingresso massima assoluta | 60 V (S440, S500), 125 V (S500B, S1000, S1200, S1400), 85 V (S650B); Voc a Tmin con KU della CEI 64-8/7 B.1, la stessa formula della nota | stesse schede p. 2; Power Optimizer Compatibility with PV Modules v1.0 (01/2025) p. 3 |
| Due moduli in serie su un ottimizzatore | potenza e Voc ×2 («multiply all values by 2») | Power Optimizer Compatibility with PV Modules v1.0 p. 3 |
| Isc del modulo entro quella ammessa | 15 A (S440-S650B), 16,5 A con Home Hub, 20 A (S1000, S1200, S1400); bifacciali: solo il lato anteriore | DS-000091-IT p. 2; DS-000105-IT p. 2; DS-000205-EU p. 2 nota 2; Bi-facial Modules v1.5 (01/2022) p. 1-2 |
| Imp oltre la corrente d'ingresso continua (15 A) | avviso: l'ottimizzatore limita la corrente | Power Optimizer Compatibility with PV Modules v1.0 p. 2 |
| Lunghezza delle stringhe, residenziali S | minimo 8, 9, 16, 18 (S440, S500) e 6, 8, 14, 14 (S500B, S650B), massimo 25, 20, 50, 50 per monofase, trifase a stringa corta, trifase 230/400 V, trifase 277/480 V | DS-000091-IT p. 3 |
| Potenza per stringa, residenziali S | continua 5.700, 5.625, 11.250, 12.750 W; collegata: con potenza CA ≤ continua quanto la potenza CC massima dell'inverter, altrimenti 6.000 W monofase (6.800 con CA ≥ 8.000 W e due o più stringhe; 6.000 dal 1/1/2025), 13.500 e 15.000 W trifase; con più stringhe la massima solo se differiscono al più di 2.000 W | DS-000091-IT p. 3 note 9-10 |
| Stringhe parallele di lunghezze o orientamenti diversi | ammesse | tutte le tabelle (DS-000091-IT p. 3, DS-000105-IT p. 3, DS-000205-EU p. 3) |
| Serie S e serie P | mai nella stessa stringa (qui un modello per inverter) | DS-000091-IT p. 3 nota 7 |
| S1000, S1200 per inverter (SE25K, SE27.6K, SE30K, SE33.3K, SE40K e unità Synergy di pari potenza) | minimo 14-15 ottimizzatori e 27-29 moduli, massimo 30 e 60; continua 13.500-17.000 W; collegata con 1 stringa (o fino a 2) e con più (es. S1000 su SE25K: 15.750 e 18.500 W); al più 5 ottimizzatori fra la stringa più corta e la più lunga della stessa unità; 11 kW STC almeno; un modulo da solo su un ottimizzatore se tutti 1:1 o se è l'unico | DS-000105-IT p. 3 |
| S1400 | come sopra con le sue colonne (SE20K-SE40K, continua 18.000-20.400 W, collegata fino a 30.400 W); non con inverter a fusibili CC integrati | DS-000205-EU p. 3 e p. 2 nota 4; S1400/S1500 inverter inter-compatibility v1.1 (06/2025) p. 1 |
| S1200 su SE33.3K | tensione di stringa a 850 V, commutabile in SetApp solo in Australia, Brasile, India, Israele, Sudafrica, Thailandia, Taiwan (l'Italia non c'è): avviso | DS-000105-IT p. 3 nota 11; Toggle Fixed String Voltage v1.1 (12/2025) p. 1 |
| Serie P di prima (P401, P505, P850, P950, P1100) | le loro tabelle, con la regola dei 2.000 W | DS-000047-ITA (15/02/2022) p. 2; DS-000012-ENG (29/12/2022) p. 3 |
| Potenza CC massima dell'inverter (moduli a STC) | SE3000H 6.000 W, SE5000H 10.000 W, SE6000H 12.000 W, Home Hub SE8000H 16.000 W, SE10000H 20.000 W, SE10K 15.000 W, SE12.5K 18.750 W, SE16K 21.600 W, SE17K 22.950 W, SE50K 87.500 W, SE90K 157.500 W, SE100K 175.000 W | DS-000094-EU p. 2; DS-000279-ROW p. 2; DS-000145-EU p. 2; DS-000150-EU p. 2; DS-000297 EU p. 2 |
| Tensione di stringa fissa | 380 V monofase, 750 V trifase | schede degli inverter p. 2 («Nominal DC Input Voltage»); Single String Design Guidelines v1.1 p. 2-3 (5,7 kW = 15 A × 380 V; 11,25 kW = 15 A × 750 V) |
| Home Hub | solo ottimizzatori 1:1 | DS-000279-ROW p. 3 |
| Potenza troncata | una stringa porta al più la potenza continua; SolarEdge consiglia di evitarlo oltre 5,7 kW monofase e 11,25 kW trifase | Single String Design Guidelines v1.1 p. 4-5 |
| Più potenza per stringa | con SolarEdge Designer («progettare il progetto usando SolarEdge Designer»): oltre la tabella commerciale la verifica è un avviso, non un errore | DS-000105-IT p. 3 note 6 e 13; DS-000205-EU p. 3 nota 11 |

### Letture di Meridiana [I]

- La tolleranza del +5 %: è quella dichiarata del modulo, non un 5 % di potenza oltre l'ottimizzatore.
- Con più stringhe distanti più di 2.000 W il limite di ciascuna torna la potenza continua (le note 7 e 8 della serie P lo
  dicono così; la tabella della serie S dice solo che la massima vale entro i 2.000 W).
- La serie S residenziale sugli inverter commerciali e Synergy segue la colonna «trifase per rete da 230/400 V», che non
  pone un limite di potenza dell'inverter.
- Tensione di stringa 775 V (SE27.6K) e 850 V (SE30K, SE40K, SE90K): dedotta da potenza continua / corrente d'uscita
  delle tabelle commerciali (13.950/18, 15.300/18, 17.000/20, 20.400/24), non stampata; serve solo ai cavi in continua.
- Mismatch zero sui moduli soli sul loro ottimizzatore: la scheda dice che l'ottimizzatore «riduce tutti i tipi di
  perdite dovuti al disaccoppiamento dei moduli, dalla tolleranza di fabbricazione all'ombreggiatura parziale»
  (DS-000091-IT p. 1); è il modello di Meridiana, non quello di PVsyst, e non è confrontato con misure. Due moduli su un
  ottimizzatore tengono il mismatch delle perdite, dalla parte della sicurezza.
- Effetto elettrico delle ombre per ottimizzatore: la formula di Martinez-Moreno applicata a ogni ottimizzatore con i
  blocchi dei suoi moduli (con il +1 della formula): una stima, come per le stringhe.
- Il taglio della stringa ora per ora usa la potenza media dei moduli del campo (non segue l'ombra di ciascun modulo).
- La proposta tiene le stringhe entro la potenza continua quando il minimo lo permette anche sugli inverter commerciali,
  le cui tabelle ammetterebbero di più: meno energia tagliata, qualche stringa in più (vedi le domande).

## Formato del progetto 13

Una voce di `energy["inverters"]` può avere `optimizer` (il record del catalogo) e `per_optimizer` (1 o 2). Il formato
12 si apre senza cambi (`MIGRATIONS[12]` è l'identità): il formato nuovo serve perché un Meridiana di prima riscrive
l'elenco degli inverter al primo cambio di quantità e perderebbe gli ottimizzatori in silenzio; così rifiuta il file.
File congelato `tests/formati/file/progetto-v13.meridiana` (SE5000H con S500). Gli altri agenti hanno i formati 14-15:
la migrazione è indipendente, il numero si riallinea all'unione se serve.

## Catalogo

- Inverter SolarEdge: i campi `dc_architecture`, `string_voltage_v`, `optimizer_grid`, `dc_input_pairs`, `synergy_units`,
  `optimizer_unit_model`; aggiunti SE8000H e SE10000H (Home Hub), SE12.5K, SE16K, SE17K, SE90K dalle schede.
- Ottimizzatori SolarEdge serie S: `max_input_current_a` (15 A) e `max_input_isc_home_hub_a` (16,5 A).

## Come è stato verificato

- Test nuovi: `tests/calcoli/test_optimizers.py` (tabelle, modulo, esempi della nota sulla singola stringa, proposta,
  anno, pipeline, formule disegnabili, Meridio), `tests/nucleo/test_catalog.py` (record SolarEdge),
  `tests/formati/test_project_files.py` (formato 13), `tests/widget/test_report.py` (relazione),
  `tests/finestra/test_window.py` (fase Impianto con ottimizzatori, scelta dal catalogo, barra, Ctrl+Z).
- Esempio a mano (nota «Progettazione a singola stringa» v1.1, p. 2): SE5000H, 24 moduli da 415 W su S440. Modulo:
  415 W ≤ 490 W; Voc a -10 °C 40,1 × (1 + 0,0025 × 35) = 43,6 V ≤ 60 V; Isc 14,1 A ≤ 15 A; Imp 13,4 A ≤ 15 A. Stringa:
  24 ottimizzatori fra 8 e 25; 24 × 415 = 9.960 W ≤ 10.000 W (CA 5.000 W ≤ 5.700 W: vale la potenza CC massima
  dell'inverter, sovradimensionamento del 200 %); oltre 5.700 W i picchi sono tagliati entro il limite dell'inverter
  (da sapere). Il programma dà gli stessi numeri e una stringa «corretta». Con 27 moduli da 370 W (stessa nota, p. 3)
  propone due stringhe (13 e 14) e una stringa a mano di 27 è un errore (massimo 25).
- Esempio Synergy: SE50K, 128 moduli da 450 W su S1000 a due moduli: 64 ottimizzatori; con 5 stringhe sarebbero 12-13
  ottimizzatori (sotto i 14), con 4 stringhe 32 moduli = 14.400 W, sopra i 13.500 W continui ma entro i 18.500 W della
  tabella con due stringhe per unità: Meridiana propone 4 stringhe da 16 ottimizzatori, due per unità Synergy, tutte
  corrette. Nell'anno: mismatch -1,0 % (due moduli per ottimizzatore), ottimizzatori -1,2 % (rendimento pesato 98,8 %),
  nessun taglio di stringa.
- Anno: con un ottimizzatore per modulo il passo del mismatch è 0 e quello degli ottimizzatori esattamente -1,4 %
  (98,6 %); una stringa di 9 kW su 5,7 kW continui non supera mai i 5,7 kW in uscita; i cavi in continua seguono il
  quadrato della potenza; `with_strings` dà esattamente lo stesso anno di una simulazione intera.

## Domande per Daniel

1. Proposta: stringhe entro la potenza continua quando il minimo lo permette (oggi), o il minor numero di stringhe che
   la tabella ammette (meno cavi, qualche picco tagliato)?
2. Due moduli su un ottimizzatore: tenere tutto il mismatch delle perdite (oggi) o ridurlo?
3. S1200 su SE33.3K o SE100K in Italia: SolarEdge consente la tensione di stringa a 850 V? La nota non elenca l'Italia;
   oggi è un avviso e la proposta sceglie S1000 o S1400.
4. Oltre la tabella commerciale, «con SolarEdge Designer»: serve un limite dichiarato dal progettista (con la fonte
   «SolarEdge Designer, progetto del …»)?
5. Ottimizzatori su inverter con MPPT (Huawei SUN2000-450W-P e MERC, Tigo TS4, Sungrow SP600S, già nel catalogo):
   servono, e con quali documenti?
6. Catalogo: aggiungere SE25K-SE33.3K singoli e Nexis 3ph? Le loro schede europee non sono state trovate al primo
   tentativo sul Knowledge Center.

## Cosa resta

- Microinverter (il catalogo c'è: Enphase, Hoymiles, APsystems, TSUN).
- Ottimizzatori su inverter con MPPT (Huawei, Tigo, Sungrow): regole loro, da scaricare.
- Il taglio della stringa con la potenza di ciascun modulo (ombra per modulo) invece della media del campo.
- La scelta di quali due moduli vanno su un ottimizzatore (oggi due consecutivi nella stringa).
- Più modelli di ottimizzatore per inverter (ampliamenti e sostituzioni, tabelle di intercompatibilità archiviate).
- L'anno per inverter e per ingresso (compito 18d).
- La riga della stringa nella barra è troncata quando la finestra è stretta (come quella delle tensioni): il testo
  intero è nel suggerimento.

## Da provare sul PC di Daniel

- La fase Impianto con un SE5000H e con un SE50K del catalogo: la proposta, «Ottimizzatori…» (il catalogo si apre su
  SolarEdge), il menu uno o due moduli, ✕, Ctrl+Z.
- La stringatura a mano con S1000 a due moduli: stringhe sotto 27 moduli, differenza di più di 5 ottimizzatori.
- La relazione PDF (Completa e Sintetica) con gli ottimizzatori.
- Un suo progetto SolarEdge reale contro SolarEdge Designer: le stesse stringhe valide e non valide? (Nessun dato delle
  sue relazioni SolarEdge è stato usato qui.)
- Schermate offscreen in
  `%TEMP%\meridiana\per-daniel\ottimizzatori`.
