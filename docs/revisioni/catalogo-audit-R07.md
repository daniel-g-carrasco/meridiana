# Audit del catalogo (R238), ripresa R07

30/10/2026, agente G della ripresa R07. Completa il lavoro parziale di F (29/10, notte) descritto nel passaggio
`docs/revisioni/PASSAGGIO-CLAUDE-20261030-R01.md`, sezione «F: R238 cataloghi, lavoro parziale». Nessun dato del
catalogo è stato modificato: questo documento verifica e documenta, le incoerenze sono elencate con la fonte.

Convenzione: [V] verificato (con quale prova o misura), [D] dedotto, [NV] non verificato.

## 1. Che cosa dice questo rapporto, in breve

- [V] I 21.640 moduli CEC distribuiti sono identici, campo per campo, ai record che `tools/update_cec.py` ricava
  dal «CEC Modules.csv» del commit SAM `cba319ded1c32a7f5b3ac76545a29e1f7181d238` (NatLabRockies/SAM, 01/07/2026,
  «New PV Module and Inverter Libraries for 2026 (#2233)»); nessun record mancante, in più o doppio.
- [V] I 2.343 inverter CEC coincidono con il «CEC Inverters.csv» dello stesso commit, dopo le trasformazioni
  dell'import (arrotondamenti a 1 o 2 o 3 decimali, NaN tenuto come dato mancante, `markets = ["US"]` aggiunto):
  non è un'identità bit a bit del CSV, è l'identità dei record che l'import produce.
- [V] Le 4 incoerenze Imp > Isc (12,46 A > 12,27 A) sono già nella riga della fonte, identica per i 4 modelli:
  LENERGY POWER INC LP-505-144M-B e -W, Sonali Energees USA LLC SS-505-144M-B e -W. Restano nel file e la finestra
  del catalogo rifiuta di sceglierli («Product not selected: inconsistent data. imp > isc»).
- [V] Le schede curate: 189 URL distinti, 157 PDF scaricati, 29 errori (28 HTTP 403, 1 HTTP 404), 3 pagine HTML;
  l'archivio locale contiene 160 file con l'hash SHA-256 del manifesto (160 su 160 ricontrollati oggi).
- [V] I 34 campi marcati `field_sources` (30 su 6 batterie Huawei LUNA2000-S1, 4 sull'inverter Huawei
  SUN2000-20K-MB0) sono tutti uguali alla tabella a pagina 2 del PDF locale.
- [V] Campione di 33 voci curate di altri costruttori (13 moduli, 14 inverter, 1 batteria, 3 ottimizzatori, 1
  microinverter; circa 620 confronti di campo): nessun valore numerico diverso dalla scheda. Due campi booleani non
  sono sostenuti dalla scheda citata: `cei_0_21 = true` per SolaX X3-PRO-20K-G2 e per ZCS Azzurro 3PH 11KTL-V3.
  Quattro record senza `datasheet_revision` (Growatt MOD 10KTL3-X, Solis S5-GR3P10K, ZCS 3PH 11KTL-V3, Huawei
  SUN2000-100KTL-M2).
- [NV] Tutto il resto: 24.262 record hanno passato un controllo strutturale (unità, segni, ordinamenti), non una
  rilettura della scheda. Le 24.262 schede NON sono state rilette; 178 voci curate su 279 non hanno avuto un
  confronto di campo; i 29 URL che rispondono 403/404 non sono stati verificati in rete.

## 2. Fonti e file

| Che cosa | Dove |
|---|---|
| Strumento di confronto con la fonte CEC | `tools/audit_catalog_sources.py` (nuovo, non committato) |
| Prove | `tests/nucleo/test_catalog_sources.py` (7 prove, tutte verdi) |
| Risultato dell'audit CEC rifatto oggi | `build/overnight-r07/g-cec-audit-R01.json` (identico a `f-cec-audit-R01.json` del 29/10) |
| Confronto di campo delle schede (Huawei e campione) | `build/overnight-r07/g-verifica-campione-R01.json` |
| CSV della fonte, bloccati per commit e hash | `C:\Users\Grasso\Elettrico\reference\catalogs\CEC-SAM\audit-20261029-R01\` |
| Schede curate scaricate (160 file + manifesto) | `C:\Users\Grasso\Elettrico\reference\catalogs\Meridiana-audit-20261029-R01\` |
| Copie Huawei con nome leggibile (stesso hash) | `C:\Users\Grasso\Elettrico\reference\catalogs\Huawei\batteries\` e `...\inverters\` |
| Schede SolarEdge (archiviate il 25/10/2026) | `C:\Users\Grasso\Elettrico\reference\catalogs\SolarEdge\` |
| Script di scarico del 29/10 (F) | `build/overnight-r07/f-fetch-sources.py` |

Hash SHA-256 della fonte CEC (verificati oggi con `verify_payload`, uguali a quelli scritti nello strumento):

- `CEC Modules.csv`: `a28cf8956a839ed98bb941809b439e4907f5b4c237bd9299bc123fb502c29aff` (6.274.198 byte), URL
  `https://raw.githubusercontent.com/NatLabRockies/SAM/cba319ded1c32a7f5b3ac76545a29e1f7181d238/deploy/libraries/CEC%20Modules.csv`
- `CEC Inverters.csv`: `0c1b2188415dad6928f91f1a4c9a820dadc80962549f903d57d9282ba3753760` (389.761 byte), stesso
  commit, `.../CEC%20Inverters.csv`
- file distribuiti: `modules_cec.json.gz` `5b624a3c92f80c170a42e08107785eeec8fbd2df9e2998365fefea4fbffbf854`,
  `inverters_cec.json.gz` `bef7e358f0642cde670b06a0f384e618468996ad9724e78bd064af7b94461b2d`.

Nota: `tools/update_cec.py` scarica da `NREL/SAM` ramo `develop`; la fonte bloccata è `NatLabRockies/SAM` (il
repository SAM ha cambiato organizzazione). Lo strumento di audit lavora solo su file locali e rifiuta un CSV con
hash diverso, quindi non c'è ambiguità sulla versione confrontata: lista «2026.7.3» del 23/06/2026 per tutti i
21.640 moduli.

## 3. Parte A: dataset CEC/SAM, verificato con la fonte

Comando (Git Bash, venv di Meridiana):

```
python tools/audit_catalog_sources.py --reference "C:/Users/Grasso/Elettrico/reference/catalogs/CEC-SAM/audit-20261029-R01" --output build/overnight-r07/g-cec-audit-R01.json
```

Esito: `{"modules": true, "inverters": true}`, exit 0; il JSON prodotto è identico a quello di F.

- [V] Moduli: attesi 21.640 dal CSV (dopo `update_cec.parse`), presenti 21.640; mancanti 0, in più 0, id doppi 0,
  differenze di campo 0. Il confronto appiattisce anche i campi annidati (`sdm.*`) e la versione della lista. 37 righe
  del CSV non diventano record, come documenta `module_exclusions`: 36 nomi che compaiono due volte (è tenuta
  l'ultima riga, come fa `update_cec.py`; per esempio Hanwha Qcells (Qidong) HSL60P6-PC-3-250...265, Tangshan Haitai
  HTM395MH5-54(1500)...) e 1 riga con `N_s` vuoto (Heliene 60M305).
- [V] Inverter: attesi 2.343, presenti 2.343, nessuna differenza. La regola di precisione è quella dell'import e
  non una tolleranza: potenze e tensioni a 1 decimale, correnti a 2, `Pso` e `Pnt` a 3, coefficienti `C0..C3`
  esatti; `NaN` resta `null`; `efficiency_cec_pct` è sempre `null` (non c'è nel CSV); `markets = ["US"]` è una
  classificazione nostra. 8 inverter Guangzhou Sanjing (H2-5K/76K/96K/114K, 208 V e 240 V) hanno `Pnt` mancante già
  nella fonte.
- [V] Le 4 incoerenze. Riga della fonte (CEC Modules.csv, righe 8701, 8702, 15866, 15867, colonne `I_sc_ref` e
  `I_mp_ref`): `... ,72,12.27,48.4,12.46,40.5, ...` cioè Isc 12,27 A, Voc 48,4 V, Imp 12,46 A, Vmp 40,5 V, 505 W,
  Mono-c-Si, lista 2026.7.3. I quattro modelli (LENERGY LP-505-144M-B, LP-505-144M-W, Sonali SS-505-144M-B,
  SS-505-144M-W) hanno la riga identica fra loro, parametri del modello a un diodo compresi: è un errore della
  fonte, non dell'import. Non sono stati corretti: non si inventa un valore.
- [V] Blocco in selezione: `CatalogDialog.accept` (`src/meridiana/ui/catalog_dialog.py`, righe 601-613) chiama
  `audit_record` sul record scelto e, se ci sono `issues`, scrive il suggerimento e non chiude. Provato offscreen con
  uno script (finestra non mostrata): `catalog.search("modules", text="LP-505-144M", source="cec")` trova i 2
  LENERGY con imp 12,46 e isc 12,27; `audit_record` sul record normalizzato dà `['imp > isc']`; la finestra con
  21.713 righe caricate, riga LP-505-144M-B selezionata, `accept()` lascia `result() == 0` e `hint.text() ==
  "Product not selected: inconsistent data. imp > isc"`.
- [NV] La scelta automatica dell'inverter (R267) e gli altri percorsi che leggono il catalogo senza la finestra non
  sono stati controllati per questo blocco: il filtro è nella finestra, non in `catalog.search`.
- [D] Un record personale con imp > isc è rifiutato all'origine da `catalog/personal.py` riga 49 (letto, non provato).

## 4. Parte B: schede curate, disponibilità delle fonti

Dal manifesto `manifest-R01.json` (scritto da `f-fetch-sources.py` il 29/10, con User-Agent dichiarato, 15 s di
timeout, nessun login): 189 URL distinti per 279 record curati (73 moduli, 100 inverter, 31 microinverter, 21
ottimizzatori, 54 batterie; un URL copre spesso più modelli).

| Stato | URL | Note |
|---|---|---|
| `pdf_downloaded_unreviewed` | 157 | PDF salvati come `<sha256(url)[:16]>.pdf` |
| `fetch_failed` | 29 | SolarEdge 12 (403), Hoymiles 4 (403), Tongwei 3 (403), LONGi 3 (403), Huasun 3 (403), Deye 3 (403), DMEGC DM655G12RT-B66HSW 1 (404) |
| `html_or_other_not_datasheet_verified` | 3 | APsystems DS3-L/DS3/DS3-H, EZ1-M/EZ1-H, QT2: la pagina di download, non il PDF |

- [V] Integrità: 160 file su disco, per tutti il SHA-256 ricalcolato oggi è quello del manifesto (0 diversi, 0
  mancanti). Le due copie in `reference\catalogs\Huawei\` hanno lo stesso hash dei file d'archivio.
- [V] Le 12 schede SolarEdge bloccate in rete (403) hanno copie locali in `reference\catalogs\SolarEdge\`
  (scaricate il 25/10/2026, con codice DS e data nel nome): due sono state usate per il campione (sezione 6).
- [NV] Per Hoymiles, Tongwei, LONGi, Huasun, Deye e DMEGC non c'è copia locale: i loro 17 record restano
  `source_declared` senza PDF in archivio. I 3 record APsystems hanno solo la pagina HTML.
- Avere il PDF non è verificare i campi: lo stato del manifesto resta `unreviewed` per tutto ciò che non è nelle
  sezioni 5 e 6.

## 5. Parte C: i 34 campi Huawei, confronto con il PDF locale

Letti con PyMuPDF (`fitz`, Python di sistema), testo della pagina 2 di ciascun PDF.

### Batterie LUNA2000-S1 (30 campi)

File `2194bc6c42e4f205.pdf` (URL `https://solar.huawei.com/dam/asset/view/8ab57198f55f4643a1b933163b460d6a.pdf`,
copia `Huawei - LUNA2000-S1 - 01-202509 IT.pdf`, SHA-256 `a7214ee2a14d133a...`), scheda in italiano «Smart String
Energy Storage System», modello LUNA2000/5/7/10/12/14/15/17/19/21-S1, «Versione n.: 01-202509» stampata a p.1 e
p.2 (= `datasheet_revision` del catalogo). Tabella «Specifiche tecniche», p.2, con 9 colonne (configurazioni).

| Modello | Campo | Catalogo | Scheda p.2 | Esito |
|---|---|---|---|---|
| LUNA2000-5-S1 | usable_energy_kwh | 5 | «1(5)»: 5 kWh | [V] uguale |
| LUNA2000-7-S1 | usable_energy_kwh | 6,9 | «1(7)»: 6,9 kWh | [V] uguale |
| LUNA2000-10-S1 | usable_energy_kwh | 10 | «2(5+5)»: 10 kWh | [V] uguale |
| LUNA2000-14-S1 | usable_energy_kwh | 13,8 | «2(7+7)»: 13,8 kWh | [V] uguale |
| LUNA2000-15-S1 | usable_energy_kwh | 15 | «3(5+5+5)»: 15 kWh | [V] uguale |
| LUNA2000-21-S1 | usable_energy_kwh | 20,7 | «3(7+7+7)»: 20,7 kWh | [V] uguale |
| 5-S1, 7-S1 | max_charge_power_w, max_discharge_power_w | 3500 | «Potenza di carica e scarica max» 3.5 kW (1 modulo) | [V] uguale, unico valore stampato per carica e scarica |
| 10-S1, 14-S1 | idem | 7000 | 7 kW (2 moduli) | [V] uguale |
| 15-S1, 21-S1 | idem | 10500 | 10.5 kW (3 moduli) | [V] uguale |
| tutti e 6 | voltage_range_by_phases_v | {"1": [350, 560], "3": [600, 980]} | «Intervallo di tensione di esercizio (sistema monofase) 350-560 V», «(sistema trifase) 600-980 V» | [V] uguale |
| tutti e 6 | coupling | dc | non stampato come parola | [D] dedotto dagli intervalli di tensione CC e dall'elenco di inverter ibridi compatibili sulla stessa pagina |

Unità: la scheda stampa kWh e kW, il catalogo kWh e W (× 1000, senza arrotondamento). Le 3 configurazioni miste
(12, 17, 19 kWh) non sono nel catalogo, come dicono le `notes` del record.

### Inverter SUN2000-20K-MB0 (4 campi)

File `29fab2bd39e9f7b8.pdf` (URL
`https://solar.huawei.com/admin/asset/v1/pro/view/c3ba89c365cb42ce92d9ba3c366253f1.pdf`, copia
`Huawei - SUN2000-12-25K-MB0 - 01-202504 EN.pdf`, SHA-256 `b4ff15fa45b150c5...`), «Version No.: 01-202504», tabella
«Technical Specification», p.2, colonna SUN2000-20K-MB0, blocco «Smart String Energy Storage System Terminal».

| Campo | Catalogo | Scheda p.2 | Esito |
|---|---|---|---|
| battery_charge_power_max_w | 21000 | «Max. charging power 21 kW (Single string) / 25 kW (Two strings)» | [V] uguale al valore a una stringa; la scelta conservativa è dichiarata in `storage_limit_notes` |
| battery_discharge_power_max_w | 22000 | «Max. discharge power ... 22.0 kW» (colonna 20K) | [V] uguale |
| battery_current_max_a | 26,25 | «Max. operating current 26.25 A (per string)» | [V] uguale |
| battery_voltage_range_v | [600, 980] | «Operating voltage range 600 V ~ 980 V» | [V] uguale |

[V] In più, i 24 campi dello stesso record che il catalogo classifica solo `source_declared` sono tutti uguali
alla stessa pagina: 20.000 W, 22.000 VA, 31,9 A a 400 V, 30.000 Wp raccomandati, 1.100 V, 600 V nominali, avvio
200 V, MPPT 200-1000 V, pieno carico da 480 V, 2 MPPT, 4 ingressi, 30 A con due stringhe / 20 A con una, Isc 40 A,
98,4 % / 98,1 %, IP66, -25...+60 °C, 21 kg, 546×460×228 mm, «CEI 0-21:2020-12 V1», «Arc fault protection: Yes».

## 6. Parte D: campione di 33 voci curate di altri costruttori

Scelta: costruttori diversi, schede in inglese, italiano e tedesco, record con e senza bifacialità, inverter di
stringa e ibridi da 10 a 100 kW, una batteria, tre ottimizzatori, un microinverter, due schede SolarEdge dalla
copia locale (URL 403). Per ogni voce: record del catalogo senza note, testo della pagina della scheda con il
modello, confronto a occhio campo per campo; JA Solar (PDF senza strato di testo) e la tabella Solis (celle unite
su più colonne) lette sull'immagine della pagina resa a 110 dpi. Dettagli per voce, con file, hash, pagine e
numero di campi confrontati, in `build/overnight-r07/g-verifica-campione-R01.json`.

Moduli (13): Aiko AIKO-A675-MDE72Mw, Jinko JKM620N-66HL4M-BDV, Trina TSM-465NEG9R.28, Canadian Solar
CS6.2-66TB-645, JA Solar JAM54D40-450/LB, REC REC470AA Pure-RX, Qcells Q.TRON M-G3R.12+ / BFG 505, SunPower
SPR-P7-450-BLK-1500, FuturaSun FU 455 M, Peimar SA585MN, Astronergy CHSM66RN(DG)/F-BH 640, 3Sun 3SHBGA-AF-470,
DAS Solar DAS-DH108NA 440.
Inverter (14): SMA STP 20-50, Fronius Symo GEN24 10.0 Plus, FIMER PVS-50-TL, Sungrow SG50CX-P2, Growatt MOD
10KTL3-X, GoodWe GW10K-ET-20, SolaX X3-PRO-20K-G2, Solis S5-GR3P10K, Kostal PLENTICORE plus G2 10, SOFAR
11KTLX-G3, Ingeteam INGECON SUN 50TL M4, ZCS Azzurro 3PH 11KTL-V3, Huawei SUN2000-100KTL-M2, SolarEdge SE10K.
Altri (6): BYD Battery-Box Premium HVS 10.2, Tigo TS4-A-O, Sungrow SP600S, SolarEdge S440, Enphase IQ8HC-72-M-INT,
più i 24 campi non marcati del Huawei SUN2000-20K-MB0 (sezione 5).

### 6.1 Esito

- [V] Valori numerici (Pmax, Vmp, Imp, Voc, Isc, rendimento, coefficienti di temperatura, tensione di sistema,
  fusibile, dimensioni, peso, celle, NOCT/NMOT, bifacialità, degrado, garanzie; potenze CA e CC, tensioni, correnti
  per MPPT, Isc per MPPT, numero di MPPT e stringhe, rendimenti, IP, temperature, pesi, dimensioni, tensioni e
  potenze batteria): nessuna differenza in nessuna delle 33 voci. Dove la scheda stampa unità diverse (kW, kWp, kVA,
  g) il catalogo converte in W, VA, kg senza arrotondamento. `datasheet_revision` coincide con la versione stampata
  in 29 voci su 33.
- Differenze trovate (campi non numerici, non sostenuti dalla scheda citata):
  1. SolaX X3-PRO-20K-G2, `cei_0_21 = true`: la riga «Certifications» a p.2 della scheda V2.8 elenca VDE4105, EN
     50549, AS 4777.2, IEC 61727, IEC 62116, IEC 61683, IEC 60068, EN 50530, NB/T 32004, IEC/EN 62109-1/-2: nessuna
     CEI 0-21.
  2. ZCS Azzurro 3PH 11KTL-V3, `cei_0_21 = true`: la scheda (rev. 2026-09-21 nell'URL) dice solo «Certificati e
     standard di connessione disponibili su www.zcsazzurro.com».
  In entrambi i casi la conformità può essere vera (certificati pubblicati altrove), ma la fonte dichiarata nel
  record non la prova: o si cita il certificato, o il campo va a `null`. Decisione di Daniel.
- Campi vuoti dove la scheda ha il dato (nessun errore, un'incompletezza): `datasheet_revision` di Growatt MOD
  10KTL3-X (nessuna versione stampata, URL «2026.5 Update»), Solis S5-GR3P10K (URL «V2,0»), ZCS 3PH 11KTL-V3 (URL
  «rev.2026-09-21»), Huawei SUN2000-100KTL-M2 (URL «20230506»); `warranty_years` di ZCS (10 anni stampati);
  `dc_power_max_w` di FIMER PVS-50-TL (52.000 W «max recommended») e ZCS 11KTL-V3 (13.200 W); `strings_per_mppt`
  di Solis (2 MPPT / 2 stringhe); corrente massima di batteria di Fronius 10.0 Plus (22 A) e GoodWe GW10K-ET-20
  (40 A).
- Scelte conservative o di lettura, coerenti ma da conoscere:
  - FIMER PVS-50-TL: `mppt_voltage_min/max` 480-800 V è l'intervallo «a Pacr»; l'intervallo operativo è 0,7×Vstart
    ... 950 V (min 300 V). Le 5 stringhe per MPPT valgono per le versioni SX/SX2 (la standard ha 1 ingresso).
  - Kostal PLENTICORE plus G2 10: 405-720 V è il «MPP range at rated output»; l'intervallo di lavoro è 120-900 V.
    Garanzia stampata «10 (5 + 5)» con attivazione in linea; catalogo 5.
  - GoodWe GW10K-ET-20: `battery_power_max_w` 11.000 è la potenza massima di scarica; la carica è 15.000 W.
  - SunPower SPR-P7-450: 30 anni di garanzia solo con registrazione, altrimenti 25 (nota 1); catalogo 30.
  - REC470AA Pure-RX: garanzia prodotto 20 anni (<25 kW) o 25 (25-500 kW); catalogo 20. Le celle sono dette
    «bifacciali» ma il modulo è vetro-backsheet senza dato di bifacialità: catalogo `bifacial = false`.
  - Enphase IQ8HC: `ac_power_max_va` 380 è la Sac,max; la potenza di picco 384 W sta nelle note.
  - SMA STP 20-50: il file si chiama `STPxx-50-DS-en-24` ma il piè di pagina di p.4 dice `en-23`; «Last revision
    02/2026» come nel catalogo.
  - 3Sun 3SHBGA-AF-470: l'URL dice rev.2.3-13052026, la scheda stampa 13042026; il catalogo segue la scheda.

## 7. Che cosa è solo strutturale, che cosa non è verificato

`src/meridiana/catalog/audit.py` (`audit_catalogue`) sui file distribuiti: 24.262 record (moduli 21.713 = 21.640
CEC + 73 curati; inverter 2.443 = 2.343 + 100; microinverter 31; ottimizzatori 21; batterie 54). Stati:
`structurally_checked` 24.258, `inconsistent` 4. Campi: `provenance_dataset` 478.267, `unknown` 36.713,
`source_declared` 8.102, `verified_field` 34.

- Strutturale significa: numeri finiti, nessun rating negativo, percentuali in 0..100, ordinamenti (Vmp ≤ Voc,
  Imp ≤ Isc, MPPT min ≤ max ≤ Vdc max, utile ≤ nominale, moduli min ≤ max). Non dice nulla sulla corrispondenza
  con la scheda.
- [V] con la fonte: i 23.983 record CEC rispetto al CSV (sezione 3); i 34 campi Huawei (sezione 5); le 33 voci del
  campione per i campi elencati (sezione 6), cioè 40 record curati su 279 hanno avuto almeno un confronto di campo
  con il PDF (le 6 batterie e l'inverter Huawei, le 33 del campione). I campi di questi 40 record che non sono stati
  confrontati sono quelli di testo lungo (`notes`, `certifications`, `compatible_inverters`, `fire_rating` in parte).
- [NV]: 239 record curati non confrontati con la scheda; `efficiency_cec_pct` e `markets` dei CEC (non nel CSV);
  la correttezza delle schede stesse (una scheda può essere superata da una revisione più nuova: il catalogo
  dichiara la revisione letta, non l'ultima pubblicata); le pagine HTML di APsystems; i 17 record senza PDF in
  archivio (Hoymiles, Tongwei, LONGi, Huasun, Deye, DMEGC); la compatibilità inverter-batteria oltre le coppie
  Huawei già coperte da `accumulo-audit-20261029-R01` e `-review-R02`.
- Non dichiarato: che le 24.262 schede siano state rilette. Non lo sono state.

## 8. Prove e comandi

```
export PYTHONUTF8=1 QT_QPA_PLATFORM=offscreen PYTHONPATH="tests;src" PATH="/c/Users/Grasso/dev/meridiana/.venv/Lib/site-packages/PySide6:$PATH"
python -m unittest tests.nucleo.test_catalog_sources -v      # 7 prove, OK in 5,5 s
python -m ruff check --select F,E9,B tools/audit_catalog_sources.py tests/nucleo/test_catalog_sources.py   # All checks passed
python tools/audit_catalog_sources.py --reference ".../CEC-SAM/audit-20261029-R01" --output build/overnight-r07/g-cec-audit-R01.json
```

Prove nuove in `tests/nucleo/test_catalog_sources.py` (classe `BundledData`), per fissare i risultati:

- `test_the_four_cec_inconsistencies_are_kept_and_flagged`: 21.640 moduli nel file, esattamente i 4 id con imp >
  isc, valori (12,46, 12,27), `audit_record` li marca `inconsistent` con `imp > isc`.
- `test_the_verified_fields_are_the_34_huawei_ones_with_page_and_revision`: 34 campi, solo Huawei, i 7 modelli,
  pagina 2, revisione 01-202509 o 01-202504, fonte su solar.huawei.com, `verified` 2026-10-29, e `audit_record` li
  classifica `verified_field`.
- `test_bundle_matches_the_pinned_source_when_it_is_on_the_disk`: esegue l'audit vero contro i CSV bloccati se
  sono sul disco (cartella di Daniel o `MERIDIANA_CEC_REFERENCE`), altrimenti salta dicendolo: 21.640 e 2.343
  coincidono, le 4 incoerenze, la lista 2026.7.3 del 23/06/2026.

Il blocco nella finestra (sezione 3) è provato con uno script offscreen e non con una prova in `tests/widget`
(file non miei): proposta per Claude in `build/claude-r07/G-rapporto.md`.

## 9. Proposte (nessuna applicata)

1. SolaX X3-PRO-20K-G2 e ZCS 3PH 11KTL-V3: `cei_0_21` a `null` oppure citare il certificato (per ZCS la pagina
   certificati del sito; per SolaX la dichiarazione o il certificato CEI 0-21 del modello). Decide Daniel.
2. Riempire `datasheet_revision` dei 4 record che ne sono privi con la data o versione dell'URL, dicendo che è
   l'unica traccia (la scheda non stampa una versione).
3. Una prova in `tests/widget` che apre `CatalogDialog("modules")`, seleziona LP-505-144M-B e verifica che
   `accept()` non chiuda e scriva il suggerimento (oggi solo script).
4. Per i 17 record senza PDF (403/404): scaricarli a mano dal browser quando servono e archiviarli in
   `reference\catalogs\<Costruttore>\`, come già fatto per SolarEdge e Huawei; poi aggiungere `field_sources` solo
   ai campi effettivamente confrontati.
5. `tools/update_cec.py` punta a `NREL/SAM`: valutare `NatLabRockies/SAM` come URL predefinito, con l'hash della
   versione letta scritto nel rapporto di aggiornamento.

## 10. Limiti di questo lavoro

- Il confronto del campione è a occhio su testo estratto; l'estrazione di PyMuPDF spezza le tabelle in colonne di
  numeri e la corrispondenza colonna-modello è stata ricostruita dall'ordine e, per Solis e JA Solar, dall'immagine.
  Un errore di lettura mio è possibile sui campi di tabelle larghe; i valori «di cardine» (Pmax, Vmp, Imp, Voc, Isc,
  potenze e correnti degli inverter) sono stati controllati nella colonna del modello e in quelle accanto.
- Nessuna chiamata in rete oggi: tutto da archivio locale. Gli URL non sono stati riprovati; i 29 errori sono
  quelli del 29/10.
- Non ho letto le `notes` di ogni record per confrontarle con la scheda (sono descrizioni, non dati usati dal
  calcolo).
