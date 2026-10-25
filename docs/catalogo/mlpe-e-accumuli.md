# Microinverter, ottimizzatori e accumuli: banca dati curata per Meridiana

> Nel programma i dati sono in `src/meridiana/catalog/data/microinverters_curated.json, optimizers_curated.json e batteries_curated.json`. Le schede PDF scaricate durante la raccolta non sono nel repository (sono dei costruttori): ogni record porta l'indirizzo `datasheet_url` da cui riaprirle. I riferimenti alla cartella di lavoro della raccolta sono stati tolti.

Data di raccolta: 21/10/2026 (campo `retrieved` di ogni record). Tutti i valori vengono dalle schede tecniche ufficiali
dei costruttori, letti dal PDF scaricato; dove un valore non è stampato il campo è `null`.

## File

| File | Record | Marche |
|---|---|---|
| (cartella di lavoro della raccolta) | 31 | Enphase 5, Hoymiles 16, APsystems 6, TSUN 4 |
| (cartella di lavoro della raccolta) | 21 | SolarEdge 12, Huawei 4, Tigo 4, Sungrow 1 |
| (cartella di lavoro della raccolta) | 54 | BYD 14, Huawei 9, Pylontech 7, Sungrow 6, GoodWe 5, ZCS Azzurro 3, sonnen 3, Growatt 3, SolarEdge 2, Enphase 1, Dyness 1 |

- PDF scaricati (60, solo PDF): (cartella di lavoro della raccolta)
- Testo estratto dai PDF, pagine HTML usate per trovare i link, immagini di controllo:
  (cartella di lavoro della raccolta)
  (`txt`, `html`, `png`). Gli script sono in `mlpe_work\tools` (download, estrazione) e `mlpe_work\build`
  (`batteries.py`, `micro.py`, `optimizers.py` con i record; `merge_validate.py` rigenera i tre JSON e ripete i controlli:
  `python -I "(cartella di lavoro della raccolta)).
- Ogni record cita nelle `notes` il file PDF locale e la pagina da cui vengono i valori.

## Regole seguite

1. **Solo documenti ufficiali** del costruttore (scheda tecnica; per garanzie, compatibilità e CEI 0-21 anche lettere di
   garanzia, liste di compatibilità e dichiarazioni pubblicate sul sito del costruttore, citate nelle notes). Nessun
   valore da distributori, cataloghi di terzi o memoria.
2. **Valori come stampati.** Nessun calcolo: se la scheda dà solo correnti, la potenza resta `null` (es. BYD, Pylontech,
   Sungrow SBR/SBH, ZCS). Conversioni solo di scala esatta (kW→W, Wh→kWh, g→kg). Qualificatori stampati (`>=`, `+`,
   "fino a") nelle notes.
3. **Tabelle a celle unite**: lette con le coordinate delle parole (PyMuPDF), non con `pdftotext -layout` che sposta i
   valori tra le righe; dove la tabella era ambigua ho guardato l'immagine della pagina (Huawei LUNA2000-S1, Pylontech
   Force-H3, sonnenBatterie 10, SolarEdge S-series, P-series, P850/P950/P1100, APsystems DS3 peso, TSUN 4-in-1). Due PDF sono
   solo immagine e sono stati letti a vista: SolarEdge Home Battery 400V IT e Dyness DL5.0C.
4. **Una riga per configurazione vendibile** (es. HVS 5.1/7.7/10.2/12.8); le configurazioni intermedie non stampate non
   sono state ricostruite.

### Significato di alcuni campi

- `cei_0_21`: `true` solo se il documento del costruttore cita la CEI 0-21 per quel modello (scheda, oppure dichiarazione
  di conformità citata nelle notes, come per ZCS e Dyness). `false` = **non citata**, non "non conforme". Per le batterie
  la conformità CEI 0-21 riguarda il sistema inverter+accumulo: le notes dicono con quale inverter.
- Microinverter: `ac_power_max_va` = potenza massima continua in uscita in VA (picco nelle notes); `ac_power_nominal_w`
  solo se stampata in W. Hoymiles e APsystems stampano solo VA, TSUN solo W. `dc_power_max_per_input_w` è un numero se
  la scheda dà la potenza massima d'ingresso (Enphase), altrimenti una stringa con la potenza modulo consigliata come
  stampata (Hoymiles, APsystems, TSUN). `efficiency_weighted_pct`: rendimento europeo (Enphase ηEU, TSUN "EU
  efficiency"); Hoymiles e APsystems non stampano un rendimento pesato.
- Ottimizzatori: `rapid_shutdown` = `true` se la scheda dichiara spegnimento rapido (Tigo UL 1741 PVRSE, Sungrow 30 V in
  20 s) o tensione di sicurezza in uscita a inverter spento (SolarEdge 1 V "SafeDC", Huawei 0 V / 1 V): le notes dicono
  quale dei due. Per SolarEdge S440/S500/S500B la potenza nominale è quella "dopo il 1° aprile 2024" (l'altra nelle notes).
  Dal compito 22 (25/10/2026) i SolarEdge della serie S hanno anche `max_input_current_a` (corrente d'ingresso continua
  massima, 15 A per S440, S500, S500B, S650B, S1000, S1200; `null` dove la scheda non la stampa) e i residenziali
  `max_input_isc_home_hub_a` (16,5 A con l'inverter Home Hub, DS-000091-IT p. 2).
- Batterie: `modules_min`/`modules_max` = intervallo di moduli ammesso per una torre o pacco come stampato (es. HVS 2-5);
  il numero di moduli della configurazione è scritto nelle notes ("Configurazione: N moduli"); torri in parallelo nelle
  notes. `voltage_class` = `LV` se la tensione nominale è <= 60 V, altrimenti `HV` (`null` per sonnen, che non stampa la
  tensione di batteria). `depth_of_discharge_pct` solo se stampata come specifica (non quando compare solo nelle condizioni
  di prova). `cycles_warranted` solo se garantiti (Enphase 5P: 6000 cicli); la "cycle life" di progetto è nelle notes.
  `end_of_warranty_capacity_pct` solo da scheda o lettera di garanzia ufficiale (Pylontech, Enphase).

## Controlli fatti (21/10/2026)

- I tre JSON si caricano; campi tutti presenti e nell'ordine richiesto; tipi coerenti; `retrieved` = "2026-10-21".
- Batterie: energia utilizzabile <= nominale dove ci sono entrambe; `voltage_class` coerente con la tensione nominale;
  `modules_min` <= `modules_max`.
- Microinverter: MPPT min < MPPT max <= tensione DC max. Ottimizzatori: MPPT min < MPPT max <= tensione d'ingresso max.
- Tracciabilità: ogni file citato nelle notes esiste in `datasheets_mlpe` e **ogni valore numerico di ogni record è stato
  ritrovato nel testo del PDF** (anche nelle forme 3,5 kW / 3500 W, 720 g / 0,72 kg), tranne i due PDF solo immagine
  controllati a vista. Il controllo testuale non vede gli scambi di colonna: per questo le tabelle a celle unite sono state
  controllate anche sull'immagine.
- Nessun indirizzo e-mail nei JSON. Nessun dato personale inviato ai siti (solo download anonimi).

## Archivi locali controllati prima di andare in rete

- `l'archivio locale delle norme\catalogs`: ABB, Blindosbarre, BTicino, Cavi, Eaton, Pogliano BusBar, Schneider
  Electric, Siemens. Nessun microinverter, ottimizzatore o accumulo FV.
- `<archivio aziendale>\LIBRERIE Impianti Elettrici\01-Cataloghi` (33 costruttori) e `<archivio aziendale>\LIBRERIE Impianti Elettrici\20-Fotovoltaico`
  (solo fogli di calcolo, estratti Guida Blu, CME): nessuna scheda di questi prodotti.
- Ricerca per nome file su `C:\Users\utente\Elettrico` e `<archivio aziendale>\LIBRERIE Impianti Elettrici`: solo una scheda BYD HVM 19.3
  di commessa, precedente alla versione BCU2.0
  (`C:\Users\utente\Elettrico\mcm\projects\22040 - Cinema Massimo\SpecTecniche\Accumulo BYD HVM 19.3.pdf`) e il
  `<archivio aziendale>\LIBRERIE Impianti Elettrici\02-Normative\Libro-Bianco-ANIE-RSE-sui-sistemi-di-accumulo.pdf` (non è una scheda).
  Per questo le schede sono state scaricate dai siti dei costruttori.
- Se Daniel vuole tenerle nell'archivio, il posto coerente con le regole di `reference` sarebbe una cartella per
  costruttore in `l'archivio locale delle norme\catalogs` con `README_INDICE.md`; non l'ho fatto.

## Come ho valutato le marche più usate in Europa e in Italia

Il punto di partenza è l'elenco di marche richiesto. Ho cercato conferme pubbliche e verificabili:

- **Wood Mackenzie, 10/07/2025**, "Global PV inverter shipments grew by 10% in 2024 to 589 GWac": Huawei e Sungrow primi
  due al mondo per il decimo anno; Huawei forte anche in Europa, Sungrow secondo dopo Huawei in Cina ed Europa; mercato
  europeo residenziale e commerciale in calo nel 2024.
  https://www.woodmac.com/press-releases/global-pv-inverter-shipments-grew-by-10-in-2024-to-589-gwac/
- **Wood Mackenzie, 11/06/2026**, "2026 Global Solar Inverter Manufacturer Ranking": Sungrow e Huawei in testa, SMA terza,
  GoodWe ed Enphase tra i primi cinque, Hoymiles e APsystems per la prima volta tra i primi dieci (classifica di qualità
  del costruttore, non di quote di mercato).
  https://www.woodmac.com/press-releases/solar-inverter-manufacture-ranking-2026/
- **Wood Mackenzie, 05/01/2026**, classifica H1 2025 (Huawei e Sungrow in testa).
  https://www.woodmac.com/press-releases/solar-inverter-ranking-h1-2025/
- **ITALIA SOLARE su dati Gaudì di Terna al 30/06/2026**: 943.797 accumuli in Italia per 19.334 MWh; nel primo semestre
  2026 60.068 nuovi accumuli abbinati al FV per 914 MWh (in media circa 15 kWh per sistema, mio calcolo), residenziale in
  calo. Ho quindi privilegiato le configurazioni da 5 a 20 kWh.
  https://www.italiasolare.eu/comunicati-stampa/fotovoltaico-e-accumuli-nel-primo-semestre-2026-connessi-31-gw-di-nuova-potenza-solare-e-135-gwh-di-capacita-di-storage/
- **Presenza documentata in Italia sui siti ufficiali**: scheda in italiano o sito italiano (Enphase, Hoymiles HMS-2T,
  APsystems, SolarEdge, Huawei, BYD HVM, Pylontech US5000, GoodWe Lynx D G2, Tigo, ZCS Azzurro, sonnen), CEI 0-21 citata
  in scheda (Enphase, APsystems, sonnen, Dyness) o in una dichiarazione del costruttore (ZCS con batterie Weco, Dyness con
  inverter Solis), liste di compatibilità ufficiali (BYD HVS/HVM V2.22 del 10/10/2026;
  Pylontech HV Ver.2.45 e LV Ver.2.46 del 2026) che mostrano gli inverter con cui queste batterie si usano in Europa.

**Limite dichiarato**: non ho trovato quote di mercato per marca di microinverter, ottimizzatori o batterie **in Italia**
verificabili su fonte pubblica: i comunicati ITALIA SOLARE/Terna non riportano le marche e, a metà lavoro, il limite di
ricerche web della sessione si è esaurito. La scelta delle marche è quindi qualitativa (elenco richiesto + presenza
ufficiale in Italia + classifiche Wood Mackenzie), non una classifica di vendite.

## Fonti usate (pagine e PDF ufficiali)

Le URL dei PDF sono nei campi `datasheet_url`; qui, per marca, le pagine da cui sono state prese e i documenti accessori.

### Microinverter
- **Enphase**: documentazione italiana https://enphase.com/it-it/installers/resources/documentation (ricerca documenti del
  sito); schede IT IQ8MC/IQ8AC/IQ8HC (DSH-00067-4.0-IT-2025-11-21), IQ8P (DSH-00503-3.0-IT-2025-05-20), IQ8X
  (DSH-00423-2.0-IT-2026-03-30).
- **Hoymiles**: https://www.hoymiles.com/downloads.html; schede HMS-1T (Europe V202408), HMS-2T in italiano (Europa
  V202408), HMS-4T (Europe V202402), HMT-4T (EMEA & APAC V202302); garanzia: "Hoymiles Microinverter & DTU Warranty Terms &
  Conditions - Europe" (https://w3oss.hoymiles.com/uploadfile/1/202608/3a1b0e5726.pdf): 12 anni, estendibile a 25 per i
  modelli senza Wi-Fi integrato.
- **APsystems**: libreria https://emea.apsystems.com/resources/library/ (file su apsystems.filecloudonline.com); schede IT
  DS3 (2025/01/06 Rev1.3), QT2 (2025/09/17 Rev1.3), EZ1 (2024/12/13 Rev1.0).
- **TSUN**: https://www.tsun-ess.com/downloads.html; schede GEN3 2-in-1 e 4-in-1 (nessuna revisione stampata).

### Ottimizzatori
- **SolarEdge**: pagine prodotto https://www.solaredge.com/it/prodotti/residenziali/ottimizzatori-di-potenza e
  knowledge center (sitemap del sito); schede IT S440/S500/S500B/S650B (DS-000091-IT, 14/09/2026), S1000/S1200
  (DS-000105-IT, 01/12/2025, etichetta Isc controllata sulla versione inglese
  https://knowledge-center.solaredge.com/sites/kc/files/se-s-series-commercial-power-optimizer-datasheet-eng-eu.pdf),
  S1400 (DS-000205-EU, 08/01/2024), P401/P505 (DS-000047-ITA, 15/02/2022), P850/P950/P1100 (DS-000012-ENG, 29/12/2022).
- **Huawei**: https://solar.huawei.com/it/products/SUN2000-450W-P2-600W-P/support/ e pagina MERC del sito italiano.
- **Tigo**: https://www.tigoenergy.com/product/ts4-a-o , /ts4-a-f , /ts4-a-s (schede IT).
- **Sungrow**: https://www.sungrowpower.com/it/it/products/MLPE/SP600S (scheda V8).

### Batterie
- **BYD**: https://bydbatterybox.com/downloads ; schede HVS BCU2.0 EN e HVM BCU2.0 IT (V1.0 250328), LVS EN (V1.0 240626);
  liste "HVS&HVM Compatible Inverter List V2.22" (2026-10-10) e "LVS Minimum Configuration List V1.12" (2025-05-16), file
  `BYD_BBOX_HVS-HVM_BCU2.0_Compatible_Inverter_List_V2.22_261010.pdf` e `BYD_BBOX_LVS_Minimum_Configuration_List_V1.12_250516.pdf`.
- **Huawei**: https://solar.huawei.com/it/products/LUNA2000-7-14-21-S1/support/ e
  https://solar.huawei.com/it/products/LUNA2000-5-10-15-S0/support/ (schede IT; S1 versione 01-202509).
- **Pylontech**: area download https://www.pylontech.it/service/downloads (file su storage OSS di Pylontech); schede Force-H2,
  Force-H3 EN-SD-250519, US5000 IT-SD-260507; garanzie "Force H serie V1.2 EU24WFHS100527" e "US serie V1.2
  EU22WUSS100302 Europe"; liste di compatibilità HV Ver.2.45 e LV Ver.2.46.
- **Sungrow**: https://www.sungrowpower.com/it/it/products (pagine SBR e SBH, schede V5 e V4).
- **SolarEdge**: https://www.solaredge.com/it/prodotti/residenziali/batterie-di-accumulo-e-backup ; schede IT Home Battery 48V
  (DS-000141-IT) e 400V.
- **Enphase**: scheda ITALIA IQ Battery 5P (IQB-5P-DSH-00248-2.0-IT-INT-IT-2024-04-04).
- **GoodWe**: https://en.goodwe.com/download-lynx-f-g2-series e https://en.goodwe.com/download-lynx-d-g2-series .
- **ZCS Azzurro**: https://www.zcsazzurro.com/it/inverters/lv-batteries e pagine "documentazione" (ZBT 5K, Weco, ZCS Azzurro
  box); dichiarazione CEI 0-21 HYD 5000-20000 ZSS con batterie Pylontech/Weco/Smart (file
  `ZCS_Dichiarazione_CEI-0-21_HYD5000-20000-ZSS_Batterie.pdf`).
- **sonnen**: https://www.sonnen.it/sistema-di-accumulo/sonnenbatterie-10 (scheda IT del 20/06/2024).
- **Dyness**: https://www.dyness.com/download ; dichiarazione CEI 0-21 Solis + serie DL (file
  `Dyness_CEI021_DL-Series_with_Solis-RHI-S6_CERT.pdf`).
- **Growatt**: https://en.growatt.com/support/download/datasheet?keyword=ARK (scheda ARK 2.5H-A2 202506).

## Cosa non è stato possibile verificare o è stato escluso

| Prodotto | Motivo |
|---|---|
| Fronius Reserva | fronius.com respinge i download automatici ("Request Rejected"), anche via fetch: scheda non letta, escluso |
| SMA Home Storage | l'area download di sma-italia.com si carica via script e il file non è stato trovato; la pagina prodotto riporta solo FAQ (moduli da 3,28 kWh, da 1 a 4 moduli con Sunny Boy Smart Energy e da 2 a 5 con Sunny Tripower Smart Energy, 10 anni con registrazione, 7,2 MWh per kWh utile, EoL 60%): non è una scheda, escluso |
| Tesla Powerwall 3 | tesla.com risponde 403 a ogni richiesta automatica: escluso |
| LG RESU Prime | il sito LG ES per l'Europa non risponde (la home rimanda al sito USA): escluso |
| Weco (sito del marchio) | area download di wecobatteries.com non leggibile senza script: il 5K3 XP è inserito dalla scheda ZCS che lo vende |
| Enphase IQ8 trifase | esiste solo la scheda IQ8P-3P per USA/America Latina (208 V, UL 1741): nessuna scheda EU, escluso; in Europa gli IQ8 monofase si collegano su IQ Cable 3L+N |
| NEP | sul sito ufficiale solo schede USA (BDM-800 NC0136-US-T, 60 Hz): escluso |
| Pylontech US3000C | nessuna scheda attuale nell'area download: escluso; la chimica non è stampata nelle schede Pylontech (campo `null`) |
| Huawei LUNA2000-12/17/19-S1 | configurazioni miste 5+7 kWh non incluse; garanzia, rendimento e tensione nominale non stampati |
| Garanzie | BYD: sul sito c'è solo la lettera per la Germania (capacità a fine garanzia non riportata); Sungrow SBR, Huawei, GoodWe, Dyness: garanzia non stampata nella scheda |
| SolarEdge P401/P505/P850/P950/P1100 | schede del 2022: la disponibilità nel 2026 va verificata (le schede recenti sono serie S) |
| Hoymiles e TSUN CEI 0-21 | non citata nelle schede (`false`): eventuali certificati separati non cercati |
| Huawei MERC | numero di moduli per unità non stampato (`null`) |
| Tigo TS4-A-O | la riga "Corrente massima 15 A/20 A" non dice se è Imp/Isc: Isc lasciata `null` |
| Quote di mercato in Italia | non trovate su fonte pubblica verificabile (vedi sopra) |

## Avvertenze per l'uso in Meridiana

- I record descrivono il prodotto come da scheda alla data indicata: le schede cambiano (es. SolarEdge S440 440/490 W prima e
  dopo il 1° aprile 2024). Prima di un progetto esecutivo controllare la revisione corrente e la compatibilità
  inverter-batteria sulle liste ufficiali citate.
- La compatibilità degli ottimizzatori SolarEdge e Huawei è limitata agli inverter dello stesso costruttore; Tigo e
  Sungrow come da scheda.
- Le potenze di carica/scarica `null` vanno lette con le correnti riportate nelle notes e con i limiti dell'inverter.
