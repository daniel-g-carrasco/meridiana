# Catalogo inverter di rete per Meridiana

> Nel programma i dati sono in `src/meridiana/catalog/data/inverters_curated.json`. Le schede PDF scaricate durante la raccolta non sono nel repository (sono dei costruttori): ogni record porta l'indirizzo `datasheet_url` da cui riaprirle. I riferimenti alla cartella di lavoro della raccolta sono stati tolti.

File: (cartella di lavoro della raccolta)
(UTF-8, array JSON, dati scaricati il 21/10/2026).

**94 modelli di 15 marche**: 59 inverter di stringa e 35 ibridi; 38 monofase e 56 trifase. Ogni numero viene da una
scheda tecnica ufficiale del costruttore, scaricata e letta in testo. Se un dato non è stampato, il campo vale `null`.
Nessun valore è stimato o calcolato.

## Marche e modelli

| Marca | N | Modelli | Fonte ufficiale |
|---|---|---|---|
| Huawei | 9 | SUN2000-3/5/6KTL-L1 (ibridi), -10KTL-M1 (ibrido), -20K-MB0 (ibrido), -20KTL-M5, -50KTL-M3, -100KTL-M2, -150K-MG0 | solar.huawei.com |
| SMA | 9 | SB3.0/5.0/6.0-1AV-41, SBSE6.0-50 (ibrido), STP10.0-3SE-40 (ibrido), Sunny Tripower X STP 20-50, 25-50, 50-80, CORE2 STP 110-60 | files.sma.de |
| Sungrow | 8 | SG3.0RS, SG6.0RS, SH5.0RS (ibrido), SG10RT, SG20RT, SH10RT-20 (ibrido), SG50CX-P2, SG125CX-P2 | info-support.sungrowpower.com |
| SolarEdge | 13 | SE3000H, SE5000H, SE6000H (Home Wave), SE6000H, SE8000H, SE10000H (Home Hub), SE10K (Home Wave trifase), SE12.5K, SE16K, SE17K (trifase), SE50K, SE90K, SE100K (Synergy) | knowledge-center.solaredge.com |
| GoodWe | 7 | GW3K-DNS-G40, GW5K-DNS-G40, GW6000N-EH (ibrido), GW10K-ET-20 (ibrido), GW10K-SDT-EU30, GW20K-SDT-30, GW50K-SDT-C30 | it.goodwe.com (schede EMEA in italiano) |
| Solis | 7 | S6-GR1P3K/5K/6K, S5-GR3P10K, S6-GC3P50K04-NV-ND, S6-EH1P6K-L-PLUS (ibrido), S6-EH3P10K-H-EU (ibrido) | solisinverters.com (schede italiane) |
| Fronius | 6 | Primo GEN24 3.0/5.0/6.0 Plus, Symo GEN24 10.0 Plus (ibridi), Tauro 50-3-D, Tauro ECO 100-3-D | fronius.com |
| Growatt | 6 | MIN 3000/5000/6000TL-X, MOD 10KTL3-X, MAX 50KTL3 LV, MAX 100KTL3-X LV | en.growatt.com |
| SolaX | 6 | X1-BOOST-3K-G4, X1-BOOST-6K-G4, X1-HYBRID-5.0-D (ibrido), X3-HYBRID-10.0-D (ibrido), X3-PRO-20K-G2, X3-MGA-50K-G2 | solaxpower.com, it.solaxpower.com |
| ZCS Azzurro | 6 | 1PH 3000TLM-V3, 1PH 6000TLM-V3, 3PH 11KTL-V3, 3PH 20000TL-V3, 1PH HYD6000 ZSS (ibrido), 3PH HYD10000 ZSS (ibrido) | zcsazzurro.com (schede italiane) |
| SOFAR | 6 | SOFAR 3KTLM-G3, ESI 6K-S1 (ibrido), SOFAR 11KTLX-G3, 20KTLX2-G3P, 50KTLX-G3, 100KTLX-G4 | sofarsolar.com |
| Deye | 5 | SUN-5K/6K-SG04LP1-EU, SUN-10K/20K-SG01HP3-EU-AM2, SUN-50K-SG01HP3-EU-BM4 (tutti ibridi) | deyeinverter.com |
| FIMER | 4 | PVS-10-TL, PVS-20-TL, PVS-50-TL, PVS-100-TL | fimer.com |
| Kostal | 4 | PLENTICORE MP G3 M 5.0 (monofase), PLENTICORE plus G2 5.5 e 10, PLENTICORE G3 L 20 (tutti ibridi) | kostal-solar-electric.com |
| Ingeteam | 4 | INGECON SUN 10TL M2, 20TL M2, 50TL M4, 110TL M9 (3Play) | ingeteam.it (sito ufficiale Ingeteam Italia) |

Taglie: monofase 3, 5 (4,6 dove manca il 5) e 6 kW; trifase 10, 20, 50 e 100 kW, o la taglia più vicina che esiste
(11 kVA per il "10 kW" di ZCS e SOFAR, 110 kW per SMA CORE2 e Ingeteam, 125 kW per Sungrow, 150 kW per Huawei).
L'URL esatto di ogni PDF è nel campo `datasheet_url`; la revisione stampata è in `datasheet_revision`.

## Regole usate per i campi

- Valori come stampati. Sono ammessi solo: kW in W, decimali con il punto, dimensioni riordinate in [L, A, P] secondo
  l'etichetta della scheda (Fronius stampa A x L x P, ZCS "A*L*P"), scelta di 230 V (monofase) o 400 V concatenati
  (trifase) da un elenco stampato. Valori diversi per paese (Italia, Germania) e valori a 380 V o 480 V sono in `notes`.
- `dc_power_max_w`: massima potenza del campo FV stampata. Quando la scheda stampa anche una "max PV input power"
  diversa, o la potenza è solo "raccomandata", `notes` lo dice. È `null` in 22 record (GoodWe DNS/SDT e SOFAR stampano
  solo una percentuale di sovradimensionamento; ZCS solo una "potenza DC tipica" che per sua nota non è un massimo).
- MPPT: se la scheda stampa solo l'intervallo a potenza nominale, quello va in `mppt_voltage_min/max_v` e il minimo
  anche in `full_power_mppt_min_v` (FIMER, Kostal, Fronius Tauro). SolarEdge lavora con ottimizzatori: i campi MPPT sono
  `null` e le correnti d'ingresso sono in `notes`.
- SolarEdge, i campi delle regole degli ottimizzatori (compito 22, 25/10/2026, `energy/optimizers.py`):
  `dc_architecture` = "fixed_string_voltage" (inverter a tensione di stringa fissa, senza MPPT), `string_voltage_v`
  (380 V monofase e 750 V trifase come stampati nelle schede; 850 V per l'SE90K dedotto dalla tabella dell'S1000,
  detto in `notes`), `optimizer_grid` (la colonna della tabella residenziale di DS-000091-IT p. 3), `dc_input_pairs`
  (coppie MC4 d'ingresso, per unità Synergy), `synergy_units` e `optimizer_unit_model` (la colonna delle tabelle
  commerciali che vale per un'unità Synergy di pari potenza). Sei modelli aggiunti dalle schede DS-000279-ROW
  (29/04/2026) e DS-000150-EU (29/09/2024) e dalla scheda Synergy DS-000297 EU (05/04/2026); i PDF sono archiviati in
  `%USERPROFILE%\Elettrico\reference\catalogs\SolarEdge` con il loro `README_INDICE.md`.
- `type` = "hybrid" se l'inverter ha un ingresso batteria in c.c., anche opzionale o da attivare (Huawei L1/M1, Kostal,
  SolarEdge Home Wave monofase 2024).
- `cei_0_21` = true solo se la CEI 0-21 è citata nella scheda o in un certificato o dichiarazione sul sito ufficiale (in
  quel caso URL in `notes`). Per i modelli da 30 kW in su `notes` dice se è citata la CEI 0-16.
- `afci` = true solo se di serie; "opzionale" dà `null` con nota. `backup_or_eps` = true anche quando serve un
  accessorio del costruttore (detto in `notes`).
- `warranty_years`: garanzia base stampata; `null` quando la scheda non la stampa o stampa solo il totale con
  estensione a registrazione (ZCS). SMA 5 (10 con registrazione), Kostal 5 (+5 con registrazione), SolarEdge 12
  (minimo dell'intervallo "12-25").
- `markets`: "IT" se il modello è sul sito o su una scheda italiana del costruttore, oppure se è citata la CEI 0-21;
  "EU" per sito o scheda europea o codici di rete europei; "global" per la scheda internazionale.
- `notes` in italiano: ambiguità, accessori, batterie compatibili, scelte fatte.

## Come ho giudicato le marche più usate in Europa e in Italia

L'elenco delle marche viene dalla richiesta. L'ho confrontato con queste fonti, lette sui siti degli editori il
21/10/2026:

- Wood Mackenzie, 10/07/2025, "Global PV inverter shipments grew by 10% in 2024 to 589 GWac": Huawei e Sungrow primi e
  secondi per il decimo anno (insieme il 55% del mercato mondiale), Ginlong Solis terza, Growatt quarta; spedizioni in
  Europa (residenziale e commerciale) in forte calo nel 2024.
  https://www.woodmac.com/press-releases/global-pv-inverter-shipments-grew-by-10-in-2024-to-589-gwac/
- Wood Mackenzie, 05/01/2026, classifica dei costruttori del primo semestre 2025: Huawei e Sungrow primi.
  https://www.woodmac.com/press-releases/solar-inverter-ranking-h1-2025/
- Wood Mackenzie, 11/06/2026, "2026 Global Solar Inverter Manufacturer Ranking": Sungrow e Huawei in testa, SMA terza,
  GoodWe ed Enphase fra i primi cinque. È un punteggio di affidabilità del costruttore (assistenza, R&S, filiera, ESG),
  non una quota di mercato.
  https://www.woodmac.com/press-releases/solar-inverter-manufacture-ranking-2026/
- EUPD Research, sigillo "Top Brand PV" (sondaggio fra installatori, PV InstallerMonitor): per gli inverter in Italia
  risultano Sungrow (2023, 2024, 2025), Growatt (2022, 2024), SolaX (2022), FoxESS (2022), Deye e Afore (2026).
  L'elenco contiene solo i marchi che hanno ottenuto il sigillo: non è una classifica di vendite.
  https://eupd-group.com/product/pv/
- Presenza ufficiale in Italia, controllata marca per marca: sito o schede in italiano (Huawei, SMA, Fronius, GoodWe,
  Solis, SolaX, ZCS Azzurro, Ingeteam Italia), certificati CEI 0-21 sui siti ufficiali. ZCS Azzurro e FIMER sono marchi
  italiani.

Non ho trovato quote di mercato **per marca in Italia** da una fonte pubblica verificabile; il limite di ricerche web
della sessione si è esaurito durante il lavoro. La scelta delle marche è quindi l'elenco richiesto, confermato dalle
classifiche mondiali e dalla presenza ufficiale in Italia, non una classifica di vendite italiana.

## Verifiche fatte

- Script di controllo su ogni record: il JSON si carica; campi e tipi; le liste MPPT hanno `mppt_count` elementi;
  `mppt_voltage_min_v < mppt_voltage_max_v <= dc_voltage_max_v`; rendimento europeo <= massimo; controlli incrociati
  (corrente c.a. contro potenza e tensione, Isc >= corrente, temperature, tensione nominale c.c. nel campo MPPT).
  Esito: 0 errori.
- Ogni valore numerico dei 94 record (potenze, tensioni, correnti, rendimenti, pesi, dimensioni, temperature) è stato
  cercato nel testo estratto dalla sua scheda: tutti trovati. Questo esclude i numeri inventati, non gli scambi di
  colonna: per quelli serve la rilettura sotto.
- Rilettura di ogni record colonna per colonna sulla scheda, con le posizioni delle parole nella pagina o l'immagine
  della pagina dove la tabella ha celle unite.
- Controlli a campione rifatti da me sui PDF: SMA STP 20-50 (corrente max 36,6 A), Fronius Primo GEN24 6.0 (MPPT
  65-480 V, Isc 41,25/22 A), Sungrow SH5.0RS (13.000 Wp in nota), Solis S6-EH1P (rendimenti in cella unica), Kostal
  MP G3 M (32 A dell'hardware M), GoodWe ET 10K, Deye 20K, SolarEdge SE3000H, Growatt MAX 50KTL3 LV, SOFAR 100KTLX-G4,
  dimensioni ZCS: tutti corretti.
- Restano 4 avvisi spiegati: i SolarEdge monofase ibridi non stampano l'intervallo di tensione della batteria.

## Cosa non è stato possibile verificare

- **SOFAR**: CEI 0-21 non citata né nelle schede né nell'elenco certificati del sito ufficiale, e manca un sito
  italiano: `cei_0_21` nullo e `markets` senza "IT". Da chiedere al costruttore prima dell'uso in Italia.
- **Ingeteam**: ingeteam.com rifiuta le connessioni; schede italiane 04-2025 prese da ingeteam.it; dimensioni lette dal
  disegno quotato.
- **Huawei**: support.huawei.com non scaricabile; la scheda M1 del sito italiano è solo immagine (usata la scheda globale
  "High Current" 01-202411); la SUN2000-20KTL-M2 non è più negli elenchi IT/EU (usata la 20K-MB0); la 100KTL-M2 non
  cita CEI 0-21 né CEI 0-16; per la 150K-MG0 la scheda italiana (99 kg) e quella globale "Preliminary" (102 kg)
  differiscono.
- **Fronius**: le schede stampano solo la corrente c.a. nominale (`ac_current_max_a` nullo); per la Symo GEN24 10.0
  Plus la batteria è 160-700 V nelle schede EN e DE e 160-531 V in quella IT (usata EN, conflitto in nota); Tauro ECO
  100-3-D ha sul sito solo il certificato CEI 0-16.
- **SolarEdge**: SE50K e SE100K senza peso e dimensioni complessive (la scheda li dà per unità Synergy, in nota); la
  Home Wave monofase è "hybrid" per l'ingresso batteria Home Battery 400V; la Home Hub ha il modello
  "SE6000H (Home Hub)" per distinguerla dalla Home Wave con lo stesso nome stampato.
- **ZCS e SOFAR**: le stesse misure (349x344x164 mm, 430x385x182 mm) sono stampate come A*L*P da ZCS e come W×H×D da
  SOFAR: ordine reale da verificare sul manuale. ZCS: Isc dalla riga "massima corrente assoluta per MPPT".
- **Modelli esclusi**: Growatt MIN TL-XH2 (schede solo immagine), SolaX X3-FORTH 100 kW (9 o 12 MPPT a scelta),
  Deye 100-125 kW e SG02HP3 (schede "Preliminary"). Quindi SolaX e Deye non hanno un 100 kW.
- **Da tenere d'occhio**: SMA CORE2 non compare più nei menu prodotto (forse sostituito da STP 125-70); SMA STP 50-80
  ha l'AFCI "disponibile da Q4/2026"; SBSE6.0-50 ha la CEI 0-21 fra i certificati "planned" della scheda, ma c'è la
  dichiarazione CEI 0-21 sul sito SMA Italia.
- Campi spesso nulli perché non stampati: garanzia (58 record), revisione della scheda (27, la revisione è solo nel
  nome del file), potenza batteria (72, compresi gli inverter di stringa).

## File di lavoro

- PDF: (cartella di lavoro della raccolta)
  (115 PDF, 151 MB, una cartella per marca: 71 usati come fonte, gli altri sono versioni in altre lingue o precedenti,
  certificati CEI e manuali usati per i confronti). Non contengono nulla da eseguire.
- Regole, testi estratti, file per marca e script (`check_inverters.py`, `merge_inverters.py`, `pdf2txt.py`):
  (cartella di lavoro della raccolta).
  Il file `inverters_full.json` lì dentro ha in più, per ogni record, il PDF e il testo da cui viene.
