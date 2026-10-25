# Moduli FV curati per Meridiana: leggimi

> Nel programma i dati sono in `src/meridiana/catalog/data/modules_curated.json`. Le schede PDF scaricate durante la raccolta non sono nel repository (sono dei costruttori): ogni record porta l'indirizzo `datasheet_url` da cui riaprirle. I riferimenti alla cartella di lavoro della raccolta sono stati tolti.

Cartella: (cartella di lavoro della raccolta)
Dati raccolti il 21/10/2026 (campo `retrieved`).

## File

- `modules_curated.json`: 73 moduli di 26 marchi, un record per modello e una sola classe di potenza per record.
  È un array JSON in UTF-8 (senza BOM), con unità SI e i numeri scritti come numeri. Le note (`notes`) sono in inglese.
- `datasheets_modules\<Marca>\`: copie delle schede ufficiali scaricate (non nel repository).
  - Per LONGi la scheda è la pagina HTML ufficiale: il PDF del sito viene generato nel browser.
  - Ci sono anche schede di varianti consultate ma non usate (all-black, gamme di potenza vicine), utili per ampliare l'archivio.
  - Sono file scaricati: non vanno eseguiti.

## Marchi e record

| Marchio | N. | Modelli (classe scelta) |
|---|---|---|
| Jinko Solar | 4 | JKM475N-48QL6-DB, JKM535N-54QL6-DV, JKM620N-66HL4M-BDV, JKM660N-66QL6-BDV |
| LONGi | 3 | LR7-54HVH-495M, LR7-72HVH-655M, LR8-66HYD-655M |
| Trina Solar | 3 | TSM-465NEG9R.28, TSM-620NEG19RC.20, TSM-715NEG21C.20 |
| JA Solar | 4 | JAM54D40-450/LB, JAM54S40-450/LR, JAM72D40-595/MB, JAM66D45-620/LB |
| Tongwei | 3 | TWMNH-48HW470, TWMNH-66HD645, TWMNF-66HD745 |
| Canadian Solar | 3 | CS6.2-48TD-460, CS6.2-66TB-645, CS7N-740TB-AG |
| Astronergy (Chint) | 3 | CHSM48RN(DG)/F-BH 465, CHSM66RN(DG)/F-BH 640, CHSM66N(DG)/F-BH 730 |
| DAS Solar | 3 | DAS-DH108NA 440, DAS-DH96NE.A 460, DAS-DH132NE 645 |
| Risen Energy | 3 | RSM96-11-465BNDG, RSM132-11-630BNDG, RSM132-8-730BHDG |
| Aiko | 4 | AIKO-A470-MCE54Mb, AIKO-A535-MCE60Mb, AIKO-A670-MDE72Dw, AIKO-A675-MDE72Mw |
| Huasun | 3 | HSN-210R-B96DS455, HSN-210R-B132DSN615, HSN-210-B132DSN715 |
| GCL SI | 3 | GCL-NT12R/48GDF 465, GCL-NR10R/54GDF 495, GCL-NT12R/66GDF 640 |
| DMEGC Solar | 2 | DM475G12RT-G48HBB, DM655G12RT-B66HSW |
| REC | 2 | REC420AA PURE-R, REC470AA Pure-RX |
| Qcells | 2 | Q.TRON S-G3R.12+ / MFG 465, Q.TRON M-G3R.12+ / BFG 505 |
| SunPower (ex Maxeon fuori dagli USA) | 3 | SPR-P7-450-BLK-1500, SPR-BE54-HD495, SPR-BE66-GD605 |
| Aleo Solar | 1 | L64S435 |
| SoliTek | 3 | SOLID Semi-Clear Framed 455 W, MAGNUS 510 W, FORZA 730 W |
| Axitec | 3 | AC-455TGBL/108WB, AC-465TGM/96WB, AC-635TGB/132WS |
| Sonnenstromfabrik (CS Wismar) | 1 | Professional Glass/Glass M108 495 Wp |
| Bauer Solar | 3 | BS-465-96G12HBT-GG, BS-485-108M10BCBB-GG, BS-625-132M12RHSW-GG |
| FuturaSun | 3 | FU 430 MV, FU 455 M, FU 580 MV |
| Peimar | 3 | SA485MN (BF), SA585MN, OR12H715MNDB |
| Sunerg Solar | 3 | XMTC3450CBDBW, XMTC3455EBDW, XMTG1595EBDW |
| 3Sun | 3 | 3SHBGA-AF-470, 3SHBGH-AD-585-610 (600 Wp class), 3SHBGH-CC-625 |
| Trienergia | 2 | TRI420VP-WB, COE-430M10EF |

Composizione dell'archivio:
- potenze da 420 a 745 W; 47 moduli bifacciali e 58 vetro-vetro;
- tecnologie: 41 TOPCon, 9 HJT, 13 back contact (HPBC 2.0, ABC, GPC, BC, BC a celle sovrapposte, MWT) e 10 "n-type" senza architettura dichiarata.

## Regole usate per i dati

- **Fonti.** Solo schede ufficiali del costruttore, con l'URL in `datasheet_url` e la copia locale in
  `datasheet_file`. Nessun valore viene da distributori, ENF, PVsyst o dalla memoria. Un valore che la scheda non
  stampa è `null`: niente stime, niente calcoli.
- **Classe di potenza.** Si prende la classe centrale della scheda; con un numero pari di classi, la più alta delle
  due centrali. `power_classes_w` elenca tutte le classi della scheda.
- **Valori elettrici.** STC del lato frontale; mai le colonne BNPI o di guadagno posteriore.
- **Campi aggiunti** rispetto alla richiesta:
  - `noct_c`: la NOCT, quando la scheda dà solo quella (in quel caso `nmot_c` resta `null`);
  - `power_after_years`: l'anno (25 o 30) a cui si riferisce `power_after_25_or_30_years_pct`;
  - `datasheet_file`: la copia locale della scheda.
- **`technology`.** È l'etichetta della scheda.
  - Se la scheda dice solo "n-type" (Qcells, DMEGC, Axitec, FuturaSun), il valore è `n-type (architecture not stated)`.
  - Per JA Solar e DAS Solar "TOPCon" viene dalla pagina prodotto del costruttore, e la nota lo dice.
- **`model`.** Dove la scheda stampa solo la famiglia, il codice è famiglia + classe. Vale per:
  - Jinko, con la regola di denominazione del costruttore;
  - Astronergy, DAS, GCL SI, Qcells, SoliTek, Sonnenstromfabrik e 3Sun B60, con la nota che lo dice.
- **`max_series_fuse_a`.** La scheda non sempre dà il fusibile massimo:
  - Qcells, Aleo, Axitec, Sonnenstromfabrik e FuturaSun: è la corrente inversa (IR) stampata;
  - DMEGC: è l'"Overcurrent Protection Rating";
  - SoliTek: il "Max current" stampato è ambiguo, quindi il campo resta `null`.
- **`markets`.** La prova è a livello di marchio, non di singolo modello:
  - `global`: marchio venduto nel mondo;
  - `EU`: scheda, sito o distribuzione europea;
  - `IT`: marchio italiano, sito o scheda in italiano, oppure un distributore italiano (Qcells: catalogo VP Solar).

## Verifiche fatte

- **Validità e coerenza.** Il JSON si carica con `json` di Python. Il controllo (`check_modules.py`) dà 0 errori su 73 record.
  - Vmp × Imp scarta al massimo dello 0,18 % da Pmax (il limite richiesto è il 2 %).
  - Voc > Vmp e Isc > Imp in tutti i record.
  - L'efficienza stampata differisce da Pmax/(L×W) di 0,08 punti al massimo (il limite è 0,5).
  - Tipi e segni dei coefficienti di temperatura sono corretti.
- **Confronto con le schede.** Il testo è stato estratto di nuovo da ogni scheda e ogni valore numerico cercato nel testo. Per Vmp, Imp, Voc, Isc ed efficienza si è controllata anche la colonna della classe scelta.
  - Le schede senza testo o con testo illeggibile sono state ricontrollate a vista sulle pagine: JA Solar (4), GCL SI (3), SoliTek SOLID e MAGNUS, Risen RSM96.
  - Nessun errore di trascrizione trovato.
- **URL.** Il 21/10/2026 tutti gli URL restituiscono il PDF, tranne tre casi:
  - Tongwei e Huasun: serve come referer la pagina download ufficiale (senza moduli né registrazione);
  - eu.longi.com: risponde 403 agli script, nel browser si apre.

## Cosa non si è potuto verificare

- **Valori non stampati, lasciati `null`:**
  - NMOT/NOCT, in 21 record: Jinko, Tongwei, Astronergy, Aiko, GCL SI, Qcells S-G3R, SunPower P7, Aleo, Trienergia COE;
  - fattore di bifaccialità, in 11 moduli bifacciali. Le schede danno solo valori BNPI o tabelle di guadagno: LONGi Hi-MO 9, Aiko Stellar 3N+72, GCL NR10R, SunPower Origin COM, SoliTek (3), FuturaSun Duetto, Peimar OR12H, Sunerg "Europei" (2);
  - classe di reazione al fuoco: Trina, Tongwei, Astronergy, DAS, Risen, Huasun, GCL SI, SoliTek;
  - potenza garantita a 25/30 anni: LONGi, Canadian Solar, SunPower, Peimar, Sonnenstromfabrik.
- **Valori letti da grafici:** garanzia Huasun, primo anno Risen, garanzia prodotto Canadian Solar (da un'icona). Il ">99 %" di Bauer non è stato registrato.
- **Stessi valori STC su marchi diversi**, quasi certamente stessa piattaforma OEM. Sono registrati come stampati:
  - Tongwei TWMNH-48HW = Qcells Q.TRON S-G3R.12+ = Axitec AC-xxxTGM/96WB;
  - FuturaSun FU 430 MV = Trienergia COE-430M10EF.
- **Dubbi della scheda, registrati come stampati e segnalati nelle note:**
  - Trienergia COE-430M10EF ha coefficienti di temperatura da PERC su un modulo TOPCon;
  - 3Sun B60 LE stampa un coefficiente di Voc più alto di quello di Pmax.
- **Mercato italiano:** provato per marchio, non per modello.

## Marchi e modelli esclusi

- **Meyer Burger:** non vende più moduli. Le società tedesche sono in insolvenza e il curatore ha venduto impianti e brevetti a
  Swift Solar ([pv magazine, 12/03/2026](https://www.pv-magazine.de/2026/03/12/swift-solar-uebernimmt-meyer-burger-produktionsanlagen-zwei-gigawatt-zellfertigung-gehen-in-die-usa/)).
- **VP Solar:** non ha una linea propria, è un distributore. Il catalogo moduli elenca 3SUN, AIKO, BISOL, DMEGC, Hyundai, Jinko,
  Kioto-Sonnenkraft, Q CELLS e Trina ([vpsolar.com](https://www.vpsolar.com/categoria-prodotto/moduli-fotovoltaici/)).
- **Maxeon:** fuori dagli USA i moduli a marchio SunPower li vende TCL SunPower. Maxeon ha ceduto a TCL l'organizzazione
  di vendita EMEA/APAC/LATAM e si concentra sugli USA ([PV Tech, 26/11/2024](https://pv-tech.org/maxeon-to-focus-on-us-market-sells-non-us-assets-to-parent-company-tcl-group)).
  Per questo i record hanno costruttore "SunPower" e schede © TCL SunPower.
- **Aleo Solar:** la produzione a Prenzlau è in dismissione dal 2025
  ([pv magazine, 10/03/2025](https://www.pv-magazine.com/2025/03/10/aleo-solar-to-halt-production-at-pv-module-factory-in-germany/)).
  Il LEO-N ha un solo record ed è da considerare a esaurimento.
- **Altri modelli non usati:**
  - Sonnenstromfabrik: tutte le serie tranne la Professional BC hanno schede 2020-2023;
  - Trina Vertex S+/N G3: schede "Preliminary";
  - Trina NEG18R.28: la scheda e la pagina prodotto non concordano;
  - Trienergia TRI-xxxLW: coefficienti incoerenti, origine non stampata;
  - Canadian CS6.2-66TM: non è sul sito EMEA;
  - Jinko 72HL4/78HL4: non più a listino EU.

## Come sono stati scelti marchi e modelli

- **Marchi:** sono quelli dell'elenco della richiesta (leader mondiali, marchi forti in Europa, marchi italiani). Riscontri esterni consultati:
  - classifica Wood Mackenzie "Global Solar Module Manufacturer Rankings 2025" (dati 2024, ordinata per punteggio e non per volumi), riportata da [PV Tech l'11/06/2025](https://www.pv-tech.org/top-ten-solar-manufacturers-ship-500gw-modules-in-2024/). L'ordine è: 1 Jinko, 2 JA, 3 LONGi, 4 Canadian Solar e Trina, 5 DMEGC, 6 Astronergy, 7 Boviet, 8 Risen e Qcells, 9 Adani, 10 TCL Solar e Tongwei (le coppie sono a pari merito);
  - per l'Italia, il catalogo del distributore VP Solar citato sopra.
- **Fonti non consultate:** la quota di ricerche web della sessione si è esaurita durante la raccolta delle schede. Restano da verificare in una prossima sessione le classifiche per volumi 2025 (InfoLink, PV Tech), Sinovoltaics, l'indice prezzi pvXchange e i dati Italia Solare.
- **Possibili aggiunte:** Hyundai (HJT) e BISOL, distribuiti in Italia; TCL Solar, Boviet e Adani, presenti nella classifica.
- **Modelli:** è la serie di punta attuale sul sito europeo o globale del costruttore. Per ogni marchio di norma:
  - un residenziale (1722-1800 × 1134 mm, 420-500 W);
  - un commerciale o utility (2278/2382 × 1134 o 2384 × 1303 mm, 550-745 W);
  - la versione bifacciale vetro-vetro, dove è la scelta corrente.

  Le vendite per modello non sono pubbliche: "più usato" vuol dire serie di punta a catalogo, non quota di mercato.

## Strumenti

Gli script stanno in (cartella di lavoro della raccolta):
- `check_modules.py`: controllo dei campi e della coerenza;
- `verify_values.py`: confronto dei valori con il testo delle schede;
- `merge_modules.py`: unione delle parti e uniformazione di etichette e note.

Si lanciano con `python -I <script> <file>`.

## Nel programma: famiglia della cella, filtri, stime

Dal 24/10/2026 (compito 16e). Questi campi non sono nelle schede dei costruttori: li aggiunge il programma e li segna.

- **`cell_family`**, la famiglia della cella: `topcon`, `hjt`, `back_contact`, `perc`, `thin_film`, `poly`, `mono`, `unknown`.
  - Per le 73 schede è scritta in `modules_curated.json` a partire dall'etichetta `technology` della scheda: 41 `topcon`, 13 `back_contact`, 9 `hjt`, 10 `unknown` (le «n-type (architecture not stated)»).
  - Per la lista CEC è letta dalle parole di tecnologia e modello (`catalog.family_of`): «Mono-c-Si» dà `mono`, «Multi-c-Si» `poly`, CdTe, CIGS, a-Si e film sottile `thin_film`; un nome che dice HJT dà `hjt` (un solo modulo, «Heliene 66M-360 HJT»).
  - `mono` e `poly` da soli dicono il silicio e non la cella: il filtro li chiama «Monocristallino, cella non indicata» e «Policristallino».
  - Una frase che dice che una cosa non è stampata («TOPCon is not printed», «cell technology (TOPCon/other) not stated») non nomina nessuna famiglia: sette schede la usano. Parole come «mono-facial», «mono-glass», «monoassiali», «multilayer», «polymer» non sono il silicio.
  - Un test confronta il campo scritto con la regola su tutte le 73 schede: una scheda nuova che la regola legge diversamente si guarda, non si crede.
- **`efficiency_pct`**: per le schede è quella stampata. Dove manca e il modulo ha potenza e dimensioni (5.669 moduli della lista CEC) è Pmax / (lunghezza × larghezza) e `efficiency_derived` è `true`: la scheda del catalogo scrive «ricavata da potenza e dimensioni».
- **`bifaciality_estimated`** (%): il valore tipico della famiglia per un modulo bifacciale la cui scheda non dà la bifaccialità: PERC 70, TOPCon e HJT 80 (PV*SOL: «usually 70-80 %»; predefinito di pvlib 0,8). Nelle schede lette riguarda 6 moduli TOPCon (SoliTek ×3, Peimar OR12H, Sunerg ×2). Contatti posteriori, film sottile e famiglia non indicata non hanno stima: restano senza valore. **Non è mai in `bifaciality`**, che resta quello della scheda (o vuoto), perché niente scambi una stima per un dato. Il modello energetico oggi non calcola il lato posteriore; quando lo farà, deve leggere `bifaciality_estimated` solo dove `bifaciality` manca e dire «stimata» nel pedigree e nella relazione.
- **La lista CEC** (`modules_cec.json.gz`, 21.640 moduli) è quella di NREL/SAM, versione 2026.7.3 del 23/06/2026; ogni record porta `list_version` e `list_date`. Si ricostruisce con `python tools/update_cec.py` (scarica «CEC Modules.csv» dall'indirizzo di NREL, oppure `--file` per una copia sul disco; `--dry-run` dice che cosa cambierebbe senza scrivere). 36 nomi compaiono due volte nel file con valori diversi (NOCT, γ): si tiene l'ultima riga e lo strumento lo dice. La riga «Heliene 60M305» non ha le celle in serie ed è esclusa.
