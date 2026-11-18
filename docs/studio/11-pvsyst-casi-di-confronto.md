# PVsyst cases for comparing Meridiana with PVsyst

Research of 22/10/2026. Public PVsyst simulation reports (PDF) collected to test Meridiana's production chain (`src/meridiana/energy/simulate.py`) against PVsyst on real projects.

Legend:
- **[V]** read in the report or in Meridiana's source.
- **[I]** my inference or proposal.

The PDFs and the extracted data stay **outside the repository**, for local validation only: `C:\Users\utente\dev\meridiana-prove\pvsyst-report-pubblici\` (`pdf\`, `casi.json`, `README.md` with sources, dates and SHA-256). This note cites the public URLs and a few headline figures; it does not reproduce the reports.

---

## 0. In brief

1. **27 cases** with full inputs and outputs: 25 from PVsyst 7.x and 8.x (7.2.5 to 8.0.20), plus 2 small rooftops from PVsyst 6 kept as extras. Three are PVsyst 8 (8.0.2, 8.0.18, 8.0.20); one report is in Italian, two in German.
2. **Sources:** the Ministry's EIA portal va.mite.gov.it (14 cases), the Emilia-Romagna EIA portal (3), GOV.UK (1), the London Borough of Camden (2), the Greek Ministry of Sports (1), Enabel (1), a Research Square preprint (1), university repositories (4). No World Bank, IFC or ADB document with a full PVsyst report was found.
3. **Types** (one case can fall in two groups):
   - ground fixed: 6 monofacial, 2 bifacial;
   - east-west: 2, one on the ground and one on a factory roof;
   - commercial size, 380 to 590 kWp: 3 (two on roofs, one of them the east-west factory);
   - small systems: 3 (22.9 kWp on a school; 5.9 and 8.8 kWp on London roofs, the latter with optimizers);
   - single-axis trackers: 4 monofacial (one vertical-axis, two on tilted terrain) and 8 bifacial.

   **No public report with storage** was found: the agrivoltaic projects with batteries do not simulate them in PVsyst.
4. **Every case checks out [V]:** monthly sums equal the Year row, the loss chain recomputed between the energy nodes matches the printed nodes, and PR recomputed from E_Grid, GlobInc and the nameplate matches the printed PR, all within 0.2 %.
5. **Best three for an automatic test** (simple geometry, no 3D near shading, full loss table): `gr-peaki-fixed-commercial`, `sa-neom-fixed`, `es-lafact-two-orientations-roof` (section 4.1).
6. **Best two with near shading:** `it-montescaglioso-fixed` (rows, linear) and `uk-pelham-fixed` (rows, electrical effect) (section 4.2).
7. **Today Meridiana can only run the fixed, monofacial cases.** Trackers, bifacial, MV transformers, auxiliaries, ageing and MPPT-level clipping are not in its chain yet (section 5.3), and its only weather source is the PVGIS typical year (section 4.3).

---

## 1. How the cases were collected

- **Searches** (22/10/2026) on the Ministry's EIA portal, the regional EIA portals, municipal tenders, university theses, development banks and planning portals, in Italian, English, Spanish, French, German and Portuguese.
- **Downloads** with curl and its own user agent, without accounts, forms or keys: 61 files, 152 MB in all, of which 26 PDFs (62 MB) were kept as cases.
- **Refusals, not worked around** (full list in the README of the local folder):
  - storage.mtender.gov.md (Moldovan rooftop reports of 30, 50 and 91 kWp, PVsyst 7.2.5) reset every connection;
  - the PVGIS API answered 403 with a maintenance page;
  - the Politecnico di Torino and Padova thesis servers and repositorio.ufc.br did not answer;
  - Scribd and CliffsNotes need an account and were not tried.
- **Reading:** PyMuPDF rebuilds each page as rows of text with positions. Labels and values side by side meet again whatever the PDF writer (one report was printed through another writer, with values before labels). Labels are matched in English, Italian and German. Every case was then compared with the page text and corrected by hand where needed: several inverter models, multi-array systems, coordinates in degrees and minutes, the shading attenuation factors printed only inside the iso-shading picture.

---

## 2. The cases

Horizon and near shading are the loss-diagram steps; "el." is the electrical shading step. E_Grid is the energy injected in the first year.

| # | Case id | PVsyst | Weather | Horizon | Near shading | E_Grid (MWh) | kWh/kWp | PR (%) |
|---|---|---|---|---|---|---|---|---|
| 1 | `it-altamura-sheds-cigs` | 7.2.13 | Meteonorm 8.0 | -0.45 % | linear -0.95 % | 2258.3 | 1435 | 84.51 |
| 2 | `it-rotello-fixed-tables` | 7.2.8 | Meteonorm 8.0 | -1.45 % | linear -5.93 % | 70023.0 | 1336 | 80.11 |
| 3 | `it-campomarino-fixed-bifacial` | 7.3.1 | Solcast synthetic | -0.79 % | strings -5.80 %, el. -3.31 % | 72475.0 | 1510 | 83.04 |
| 4 | `it-apricena-sheds-bifacial` | 7.2.5 | Meteonorm 8.0 | flat | mutual sheds, step 0.00 % | 182975.0 | 1512 | 88.35 |
| 5 | `it-montescaglioso-fixed` | 7.2.11 | Meteonorm 8.0 | -0.55 % | linear -2.20 % | 8065.0 | 1429 | 85.50 |
| 6 | `it-montescaglioso-tracker-bifacial` | 7.2.11 | Meteonorm 8.0 | -1.47 % | linear -1.53 % | 9117.0 | 1718 | 89.19 |
| 7 | `uk-pelham-fixed` | 7.4.5 | Meteonorm 8.0 | -0.42 % | strings -2.92 %, el. -0.42 % | 55578.6 | 1056 | 85.17 |
| 8 | `sa-neom-fixed` | 7.4.0 | Meteonorm 8.1 | flat | none | 10602.2 | 2121 | 84.07 |
| 9 | `gr-peaki-fixed-commercial` | 7.4.8 | PVGIS TMY (API) | flat | none | 615.5 | 1551 | 85.28 |
| 10 | `de-stahl-eastwest` | 7.2.16 | not printed | flat | strings -0.77 %, el. -0.39 % | 719.3 | 914 | 85.83 |
| 11 | `de-stahl-south` | 7.2.16 | not printed | flat | strings -3.24 %, el. -2.79 % | 774.9 | 984 | 82.10 |
| 12 | `id-pabrik-eastwest-roof` | 7.4.8 | Meteonorm 8.1 | flat | linear -0.80 % | 523.4 | 1379 | 78.55 |
| 13 | `es-lafact-two-orientations-roof` | 7.3.4 | Meteonorm 8.1 | flat | none | 754.6 | 1279 | 86.85 |
| 14 | `ps-albakri-school-module-layout` | 7.3.1 | Meteonorm 8.1 | flat | module layout -1.29 %, el. -1.01 % | 38.5 | 1686 | 83.12 |
| 15 | `uk-camden-wildcourt-roof-v6` | 6.67 | Meteonorm 7.1 | flat | module layout -1.60 %, el. -2.70 % | 5.2 | 877 | 87.21 |
| 16 | `uk-camden-bloo-optimizers-v6` | 6.52 | Meteonorm 7.1 | flat | strings -9.60 %, el. -5.40 % | 6.9 | 785 | 75.00 |
| 17 | `it-militello-tracker-tilted-axis` | 7.3.2 | Solargis TMY | -0.11 % | strings -2.83 %, el. -3.30 % | 58031.0 | 1824 | 81.71 |
| 18 | `it-agrosolar3-tracker` | 7.4.5 | Meteonorm 8.1 | flat | linear -3.46 % | 53826.0 | 1893 | 87.21 |
| 19 | `it-mezzojuso-tracker-horizon` | 7.4.0 | PVGIS TMY (API) | -2.47 % | linear -6.59 % | 90706.0 | 1726 | 78.16 |
| 20 | `it-risicone-vertical-axis-tracker` | 7.4.4 | Meteonorm 8.1 | flat | none | 78603.6 | 2094 | 84.69 |
| 21 | `it-velletri-tracker-bifacial` | 7.3.1 | Meteonorm 8.0 | -0.15 % | strings -1.59 %, el. -0.59 % | 36050.0 | 1553 | 84.27 |
| 22 | `it-viterbo-tracker-bifacial` | 7.4.5 | Meteonorm 8.1 | flat | linear -3.03 % | 109133.4 | 1804 | 91.53 |
| 23 | `it-brindisi-tracker-bifacial` | 7.2.21 | Meteonorm 8.0 | flat | linear -2.14 % | 31030.0 | 1743 | 87.80 |
| 24 | `it-copparo-tracker-bifacial` | 7.2.8 | Meteonorm 8.0 | flat | linear -2.42 % | 39478.0 | 1538 | 90.66 |
| 25 | `it-portomaggiore-tracker-bifacial-v8` | 8.0.18 | PVGIS TMY (API) | flat | linear -2.10 % | 41852.0 | 1675 | 85.56 |
| 26 | `it-foiano-tracker-bifacial-v8` | 8.0.2 | PVGIS TMY 5.2 | -0.70 % | none | 59206.0 | 2022 | 92.91 |
| 27 | `it-conselice-tracker-bifacial-v8-italian` | 8.0.20 | Meteonorm 8.2 | flat | linear -2.50 % | 262980.0 | 1574 | 86.50 |

Sources (one URL per report; cases 5 and 6 share a PDF):

| # | URL |
|---|---|
| 1 | https://va.mite.gov.it/File/Documento/648660 |
| 2 | https://va.mite.gov.it/File/Documento/733996 |
| 3 | https://va.mite.gov.it/File/Documento/907358 |
| 4 | https://va.mite.gov.it/File/Documento/824461 |
| 5, 6 | https://va.mite.gov.it/File/Documento/744498 (pages 2-10 fixed, 11-19 tracker) |
| 7 | https://assets.publishing.service.gov.uk/media/6602762fa6c0f7bb15ef9294/SE-PELHAM-PVsyst-VC4_691191698.1_.pdf |
| 8 | https://assets-eu.researchsquare.com/files/rs-7001662/v1/acdb8c0b2d116b3d640a5031.pdf |
| 9 | https://minsports.gov.gr/wp-content/uploads/2026/06/6._%CE%A0%CE%B1%CF%81%CE%AC%CF%81%CF%84%CE%B7%CE%BC%CE%B1-I_%CE%A4%CE%B5%CF%87%CE%BD%CE%BF%CE%BF%CE%B9%CE%BA%CE%BF%CE%BD%CE%BF%CE%BC%CE%B9%CE%BA%CE%AE-%CE%9C%CE%B5%CE%BB%CE%AD%CF%84%CE%B7-%CE%A6%CE%92.pdf |
| 10 | https://campuas.frankfurt-university.de/pluginfile.php/337589/mod_resource/content/1/Stahl-GmbH_MN_15-OW-Report.pdf |
| 11 | https://campuas.frankfurt-university.de/pluginfile.php/337593/mod_resource/content/1/Stahl-GmbH_MN_15-S-Report.pdf |
| 12 | https://publikasi.mercubuana.ac.id/index.php/jte/article/download/32135/12258/90981 |
| 13 | https://upcommons.upc.edu/bitstreams/d48523ab-71da-4969-bca0-aa3039e9934d/download |
| 14 | https://www.enabel.be/app/uploads/2026/07/Annex-9-PV-System-report_p.pdf |
| 15 | https://camdocs.camden.gov.uk/CMWebDrawer/Record/8180061/file/document |
| 16 | https://camdocs.camden.gov.uk/CMWebDrawer/Record/7351402/file/document |
| 17 | https://va.mite.gov.it/File/Documento/871175 |
| 18 | https://va.mite.gov.it/File/Documento/1057410 |
| 19 | https://va.mite.gov.it/File/Documento/1153682 |
| 20 | https://va.mite.gov.it/File/Documento/1006273 |
| 21 | https://va.mite.gov.it/File/Documento/840288 |
| 22 | https://va.mite.gov.it/File/Documento/1059995 |
| 23 | https://va.mite.gov.it/File/Documento/943524 |
| 24 | https://serviziambiente.regione.emilia-romagna.it/viavasweb/progettoIniziale/scaricaAllegato/651160/6973 |
| 25 | https://serviziambiente.regione.emilia-romagna.it/viavasweb/progettoIniziale/scaricaAllegato/647700/6824 |
| 26 | https://va.mite.gov.it/File/Documento/1210841 |
| 27 | https://serviziambiente.regione.emilia-romagna.it/viavasweb/progettoIniziale/scaricaAllegato/649749/6902 |

---

## 3. What each case tests and what it lacks

**Missing from every case [V]:**
- the hourly weather file (Meteonorm, Solcast and Solargis are not public; the PVGIS ones can be fetched again, in principle);
- the module and inverter files (.PAN, .OND): only manufacturer, model and nominal power are printed;
- the PVsyst project itself;
- the 3D scene, where there is one: it is only a picture.

Each case's own gaps follow.

| # | Case | Tests | Also missing or odd |
|---|---|---|---|
| 1 | Altamura sheds | Fixed sheds 30° at 10 m pitch (GCR 24 %), thin-film CIGS 115 Wp (STC efficiency 12.2 %), horizon profile (PVGIS), linear shading of a scene that includes wind turbines, ASHRAE b0 0.05, 2 central inverters, auxiliaries 3 W/kW, MV transformer, ageing year 1. | Nothing beyond the common gaps. The twin report without turbines (648661) differs by 0.1 MWh. |
| 2 | Rotello | 52 MWp fixed tables 25° on a hill, horizon 4.2°, linear near shading -5.9 %, user IAM profile, 260 string inverters, grid limit 42.92 MWac, ageing. | Hill geometry only as a picture. |
| 3 | Campomarino | Fixed bifacial (φ 0.90), GCR 68 %, near shading by strings with electrical effect 100 %, horizon, grid limit, user IAM, ageing 30 years, P50/P90. | **T_Amb is 0.00 °C from August to December** in the monthly table (yearly mean 9.12 °C): the weather file looks broken. |
| 4 | Apricena | 121 MWp unlimited sheds 30° (GCR 43 %), bifacial φ 0.80 on albedo 0.30, 4 inverter models (1995, 1500, 998, 300 kWac), DC/AC 1.26 (clipping -1.2 %), unavailability 0.5 %. | Near-shading step printed as 0.00 % although mutual shading of sheds is declared: to be understood before use. |
| 5 | Montescaglioso fixed | 20 identical rows 20° at 7.5 m pitch, linear shading -2.20 %, horizon profile, user IAM, auxiliaries, MV transformer. | Summary energy rounded to whole GWh (use the monthly table). |
| 6 | Montescaglioso tracker | Same site and weather as case 5 with N-S trackers ±55° and backtracking, bifacial φ 0.70. | As case 5. |
| 7 | Pelham | 52.6 MWp fixed tables 20° at 51.9°N, horizon profile, near shading by strings with electrical effect 50 % (fast table), DC/AC 1.40 (clipping -0.61 %), auxiliaries 2 W/kW plus 2 kW at night. | The scene includes terrain and hedgerows, not only rows. |
| 8 | NEOM | 5 MWp fixed 30°, no shading, hot desert climate (T_amb 26.3 °C, temperature step -11.3 %), user IAM, Uc 20. | Generic components; PVsyst "classroom" licence. |
| 9 | PEAKI | 397 kWp fixed 25°, no shading, PVGIS TMY, Fresnel AR IAM, Uc 20, 4 x 100 kWac. | Mounting not stated (Uc 20 suggests a roof or a closed back). No soiling, LID or AC losses. 49 strings on 40 MPPT inputs explain an overload step of -1.94 % at DC/AC 0.99 [I]. |
| 10 | Stahl east-west | 15/+90 and 15/-90 in rows on the ground, near shading by strings (100 %), mixed-orientation mismatch, ASHRAE. | **No site page:** latitude, longitude and weather source are not printed (the sun path suggests about 51-52°N [I]). |
| 11 | Stahl south | Same plant facing south in 23 rows at 9.18 m (GCR 74 %): near -3.24 % and electrical -2.79 %. | As case 10. |
| 12 | Pabrik Karton | 380 kWp east-west roof at -6.2° latitude, 30 MPPT inputs with strings of 22-24 modules, linear shading, Uc 15, temperature step -11.4 %, spectral correction, ageing. | Mismatch 0.2 % and quality 0 % as set by the author. |
| 13 | LaFact | 590 kWp roof with two planes, 10/+86 and 20/180 (north-facing in PVsyst's convention), no shading, user IAM, 6 x 100 kWac, voltage-threshold step -0.25 %. | PVsyst DEMO; the thesis calls the north-facing array "east". |
| 14 | Al-Bakri | 22.9 kWp on a school: two module fields among the building volumes, detailed electrical shading by module layout (-1.29 % and -1.01 %), two inverters at 50 % MPPT share. | Scene dimensions not printed (declared "sheds on ground"). |
| 15 | Wild Court | 5.9 kWp flat roof 6°, azimuth -45°, module-layout electrical shading (-1.6 % and -2.7 %), London. | PVsyst 6.67; scene only as a picture. |
| 16 | BLOO Array B | 8.8 kWp pitched roof 13°, 27 modules each on a SolarEdge P500, near shading -9.6 % and electrical -5.4 %, PR 75 %. | PVsyst 6.52; monthly table without DiffHor. |
| 17 | Militello | Trackers on terrain (average axis tilt -2.4°), ±60° with backtracking, near shading by strings with wind turbines (-2.83 % and -3.30 %), Solargis TMY, 7 + 1 central inverters. | Terrain only as a picture. |
| 18 | Agrosolar 3 | N-S trackers ±60° without backtracking, one module wide at 5.5 m pitch (GCR 23.7 %), linear shading -3.46 %, unavailability 2 % of time (-1.64 % of energy). | No soiling, LID or AC losses. |
| 19 | Mezzojuso | Trackers on hills (axis tilt -2.8°), irradiance optimization, horizon 6.6° (-2.47 %), linear shading -6.59 %, PVGIS TMY, spectral correction. | No horizon profile page; monthly table without E_Grid; the loss diagram stops at the inverter output. |
| 20 | Risicone | Vertical-axis (azimuth) tracking with the plane at 60° (GlobInc +47 %), soiling 5 %, voltage-threshold step -1.99 %. | PVsyst evaluation mode (TRIAL watermark), generic components. |
| 21 | Velletri | 2P bifacial trackers (5.03 m) at 8 m pitch, irradiance optimization, near shading by strings, bifacial φ 0.50, 2 inverter models, grid limit, auxiliaries, ageing. | Nothing beyond the common gaps. |
| 22 | Viterbo | Trackers limited to ±38°, backtracking, linear shading -3.03 %, bifacial φ 0.80, Uc 20, Fresnel smooth glass. | No soiling and no losses after the inverter. |
| 23 | Brindisi | N-S trackers ±55°, bifacial φ 0.70, user IAM, soiling 0.3 %, unavailability 1 %, auxiliaries, MV transformer -1.76 %. | Nothing beyond the common gaps. |
| 24 | Copparo | N-S trackers ±60°, bifacial φ 0.80, linear shading -2.42 %, Po valley weather (GHI 1331 kWh/m²), grid limit 22.5 MWac. | PVsyst 7.2.8 although filed in 2026. |
| 25 | Portomaggiore | PVsyst 8.0.18, N-S trackers ±50°, bifacial φ 0.70 on albedo 0.30, PVGIS TMY, Uc 20, AC ohmic 3.53 % at STC. | PVsyst 8 prints the effective irradiation as GlobEff + φ·GlobBak, so GlobEff comes from the monthly table. |
| 26 | Foiano | PVsyst 8.0.2, unlimited trackers with axis azimuth 14°, no near shading, horizon profile, bifacial φ 0.80, PVGIS TMY 5.2, DC ohmic step -3.3 %, 7 central inverters. | Nothing beyond the common gaps. |
| 27 | Conselice | PVsyst 8.0.20 **report in Italian**, 167 MWp, N-S trackers ±90°, bifacial φ 0.70, linear shading, auxiliaries, 38 MV transformers, percentages printed with one decimal. | No inverter block on the PV array page: model and count (452) come from the AC wiring section; inverter unit power missing. |

---

## 4. Cases for an automatic comparison test

### 4.1 Three without near shading

**1. `gr-peaki-fixed-commercial` (PVsyst 7.4.8): the best start.**
- **Why:** one fixed plane (25°, south), no 3D scene, no horizon, and **PVGIS TMY weather**, the only weather Meridiana can fetch today.
- **Inputs:**
  - modules: 735 Luxor LX-540M/182-144+ (540 Wp), 49 strings of 15;
  - Uc 20 (Meridiana's "semi" case);
  - IAM: Fresnel AR, 9 printed points that fit `ModuleSpec.iam_profile`;
  - DC wiring 1.5 % at STC, quality -0.8 %, mismatch 2 %;
  - no soiling, LID or AC losses.
- **Compare:**
  - GlobInc 1818.5 kWh/m² (+14.0 %), IAM -2.10 %, GlobEff 1780.4;
  - EArrNom 707 MWh, irradiance level -0.65 %, temperature -6.76 %, EArrMPP 640 MWh;
  - E_Grid 615.5 MWh, PR 85.28 %.
- **Caveat:** 49 strings on 40 MPPT inputs give some inputs 16.2 kWp on 10 kWac, hence the -1.94 % overload step at DC/AC 0.99 [I]. Meridiana pools the DC power and will not see it: compare up to EArrMPP strictly, then the inverter separately.

**2. `sa-neom-fixed` (7.4.0): the temperature model in a hot climate.**
- **Why:** one fixed plane (30°, south), no shading, no horizon. Hot desert climate: T_amb 26.3 °C, temperature step -11.26 %.
- **Inputs:** 10203 modules of 490 Wp (generic LR5-66HPH-490M), 537 strings of 19, user IAM profile, Uc 20, DC wiring 1.5 %, quality -0.8 %, mismatch 2 % and 0.2 %, 5 central inverters (875 kWac, DC/AC 1.14, no clipping).
- **Compare:**
  - GlobInc 2522.5 (+11.6 %), GlobEff 2484.2;
  - EArrNom 12443 MWh, EArrMPP 10805 MWh;
  - E_Grid 10602 MWh, PR 84.07 %.
- **Caveat:** Meteonorm 8.1 weather. The weather must be matched month by month (4.3).

**3. `es-lafact-two-orientations-roof` (7.3.4 DEMO): two planes, odd azimuths.**
- **Why:** two fixed planes, no shading. Array 1 is 10° at +86° (306 kWp). Array 2 is 20° at 180°, facing north (284 kWp). Transposition is tested away from south, and two arrays are summed.
- **Inputs:** 1180 JA Solar 500 Wp modules (strings of 17 and 18), 6 Fronius Tauro Eco 100 kWac, user IAM, Uc 20, DC wiring 1.5 %, quality -0.3 %, mismatch 2 % and 0.2 %.
- **Compare:**
  - GlobInc 1472.6 (-7.75 %), IAM -3.08 %;
  - EArrNom 843.4 MWh, EArrMPP 770.2 MWh;
  - E_Grid 754.6 MWh, PR 86.85 %.
- **Caveat:** Meteonorm 8.1 weather, as case 2.

Next in line:
- `it-foiano-tracker-bifacial-v8`: PVsyst 8, PVGIS TMY 5.2, no near shading, full table, as soon as Meridiana has trackers and bifacial.
- `uk-camden-wildcourt-roof-v6`: small, but shaded.

### 4.2 Two with near shading

**1. `it-montescaglioso-fixed` (7.2.11): rows, linear.**
- **Why:** 20 identical straight rows on flat ground, which is exactly Meridiana's rows model (`ArraySpec.rows`, `pitch`, `slant`):
  - tilt 20°, south, pitch 7.50 m, collector width 4.79 m (GCR 63.8 %);
  - linear shading -2.20 %;
  - printed horizon profile (PVGIS, -0.55 %).
- **Comparable factors [V]:** the iso-shading picture gives the diffuse attenuation 0.044 and the albedo attenuation 0.769, to set against Meridiana's Passias sky masking.
- **Also:** the tracker twin in the same PDF (case 6) will test trackers later on the same weather.
- **Caveats:**
  - Meteonorm 8.0 weather;
  - user IAM;
  - auxiliaries and the MV transformer to be left out of the comparison (Meridiana has neither).

**2. `uk-pelham-fixed` (7.4.5): rows with the electrical effect.**
- **Why:** tables 20° (azimuth -2°) at 8.69 m pitch, width 4.60 m (GCR 52.9 %), at 51.9°N, where the rows shade each other a lot. Near shading by strings with electrical effect 50 %: irradiance -2.92 %, electrical -0.42 %.
- **Other inputs:** printed PVGIS horizon profile (-0.42 %), ASHRAE b0 0.05 (Meridiana's default law), full loss table down to E_Grid.
- **Comparable factors [V]:** diffuse attenuation 0.036, albedo attenuation 0.826.
- **Caveats:**
  - the scene also has terrain and hedgerows, so a rows-only model is an approximation;
  - PVsyst applies its electrical effect at 50 % (a user fraction of the string partition model), while Meridiana's Martinez-Moreno blocks have no such knob: compare the sum of the irradiance and electrical steps first.

**Runners-up:**
- `de-stahl-south` and `de-stahl-eastwest`: strong electrical row shading (-3.24 % and -2.79 %), but the site is not printed.
- `ps-albakri-school-module-layout`: module-layout electrical shading among school buildings, closest to Meridiana's obstacles with strings, but the scene must be redrawn from a picture.
- `it-altamura-sheds-cigs`: flat rows; its twin shows the wind turbines change nothing.

### 4.3 How a comparison test could work [I]

1. **Weather.**
   - For the PVGIS cases (9, 19, 25, 26): fetch the typical year at the printed coordinates. Before comparing anything else, check the monthly GlobHor, DiffHor and T_Amb against the report's table (yearly GHI within 1 %).
   - For Meteonorm, Solcast and Solargis: scale a PVGIS typical year month by month, so that monthly GHI and DHI and the mean temperature equal the report. This needs a small constructor for `Meteo`. The hourly shapes still differ, so transposition will not be exact.
2. **Inputs from casi.json.**
   - tilt, azimuth (PVsyst's convention is Meridiana's: 0 south, + west), rows, pitch and width;
   - Uc and Uv, mapped to Meridiana's three thermal cases (29, 20, 15);
   - the IAM profile points (into `iam_profile`; the ASHRAE b0 otherwise);
   - soiling, quality, LID, mismatch (module + strings), DC and AC wiring, unavailability;
   - inverter AC power. The weighted efficiency can be taken as 1 minus the printed "inverter loss during operation" [I].
3. **Compare node to node, not step to step.**
   - The nodes: GlobInc, GlobEff, EArrNom, EArrMPP, EOutInv, E_Grid. In casi.json the steps also carry `meridiana`, the key of the matching chain step.
   - Steps are relative to the previous energy and come in a different order in the two programs (5.2), so single percentages are not comparable one to one.
   - Ratios between nodes are less sensitive to the weather than absolute values.
4. **Tolerances to start with** (to be tightened once the weather is matched):
   - GlobInc ±1.5 %;
   - GlobEff/GlobInc ±0.5 points;
   - irradiance level plus temperature ±1 point;
   - EArrMPP/EArrNom ±1.5 points;
   - E_Grid ±3 %, PR ±2 points;
   - near shading ±1 point.

---

## 5. PVsyst's loss diagram and Meridiana's chain

### 5.1 Meridiana's chain [V]

`simulate()` builds `Simulation.chain` (simulate.py, lines 360-380) as a list of `ChainStep`, each with `key`, `kind` ("irradiance" in kWh/m², "energy" in kWh), the value after the step, and `change`. `change` is the % against the previous value of the same kind, None for the starts `ghi` and `nominal`: the same convention as PVsyst's arrows.

The keys, in order:
1. **Irradiance:** `ghi`, `poa`, `far`, `near`, `iam`, `soiling`.
2. **Energy:** `nominal`, `irradiance_level`, `temperature`, `quality`, `lid`, `mismatch`, `electrical` (only when a string effect was computed), `dc_wiring`, `inverter`, `clipping`, `ac_wiring`, `unavailability`.

PR divides the energy by the plane irradiation before the horizon (`poa`), as PVsyst divides by GlobInc.

### 5.2 Step by step

`casi.json` uses the keys in the second column.

| PVsyst step (English report) | Key | Meridiana | Notes |
|---|---|---|---|
| Global horizontal irradiation | globhor | `ghi` | Start. |
| Global incident in coll. plane | transposition | `poa` | Both Perez by default; PVsyst treats circumsolar separately and the reports print the diffuse model ("Perez, Meteonorm" or "Imported"). |
| Far Shadings / Horizon | far_shading | `far` | PVsyst cuts the beam and scales diffuse and albedo by the "Diffuse Factor" and "Albedo Factor" printed with the horizon (in casi.json). Meridiana cuts beam and circumsolar and scales the sky diffuse by the dome factor, but leaves the ground-reflected part whole. |
| Near Shadings: irradiance loss | near_shading | `near` | Linear (beam). PVsyst also attenuates diffuse and **albedo** with constant factors from the iso-shading table (albedo attenuation 0.65-0.83 for the rows above). Meridiana masks the sky diffuse (Passias) but **does not shade the ground-reflected part**, so it should lose a little less on rows. The (n-1)/n first-row rule is in both. |
| IAM factor on global | iam | `iam` | ASHRAE, Fresnel or user profile in PVsyst. Meridiana takes ASHRAE b0 or a point profile joined as PVsyst joins it, integrated for diffuse (Marion). |
| Soiling loss factor | soiling | `soiling` | Same place, on the irradiance. |
| Ground reflection on front side, rear-side branch | ground_reflection_front, global_on_ground, ground_reflection_loss, rear_view_factor, rear_sky_diffuse, rear_beam, rear_shading, rear_global | none | Bifacial, not in Meridiana (`ModuleSpec.bifaciality` is stored but unused). |
| Effective irradiation on collectors | glob_eff | value after `soiling` | Node. |
| Array nominal energy (at STC effic.) | array_nominal | `nominal` | Both are Pnom × GlobEff / 1000 for monofacial arrays; PVsyst adds φ·GlobBak for bifacial ones. |
| Module Degradation Loss (year n) | degradation | none | Ageing tool, not in Meridiana. |
| PV loss due to irradiance level | irradiance_level | `irradiance_level` | PVsyst: one-diode model of the .PAN (exponential Rsh). Meridiana: De Soto fit to the datasheet at 25 °C. Larger gaps are expected for thin film (case 1) and dull climates. |
| PV loss due to temperature | temperature | `temperature` | Same thermal model (Uc, Uv, α 0.9, efficiency). PVsyst's temperature behaviour comes from the one-diode model; Meridiana uses the datasheet γ. |
| Spectral correction, light soaking | spectral | none | Cases 12 and 19 use the spectral correction (+0.02 % and -0.06 %). |
| Shadings: Electrical Loss (acc. to strings / detailed module calc.) | electrical_shading | `electrical` | **Order differs:** PVsyst puts it right after temperature, before quality, LID and mismatch; Meridiana puts it after mismatch. PVsyst's "according to strings" is a partition model (an upper bound by its own help) scaled by the electrical-effect %. Meridiana uses Martinez-Moreno blocks. |
| Module quality loss | module_quality | `quality` | Input -0.8 % prints as +0.75 % in PVsyst (applied inside the model, [V] in cases 2, 4, 9). Meridiana applies the input exactly. |
| LID | lid | `lid` | Same. |
| Mismatch loss, modules and strings | mismatch | `mismatch` | PVsyst merges the module (e.g. 2 % at MPP) and string (0.1 %) mismatch into one step (-2.06 % to -2.15 %); give Meridiana the combined figure. |
| Mismatch for back irradiance, mixed orientations, ageing | mismatch_rear, mismatch_orientation, mismatch_ageing | none | Bifacial, multi-orientation (case 10: -0.01 %) and ageing. |
| Optimizer efficiency loss | optimizer | none | Case 16 (SolarEdge, 0.0 %). |
| Ohmic wiring loss | ohmic | `dc_wiring` | Both give a % at STC that grows with current. |
| Array virtual energy at MPP | array_mpp | value after `dc_wiring` | Node. |
| Inverter Loss during operation | inverter_efficiency | `inverter` | PVsyst: the .OND efficiency curve. Meridiana: PVWatts curve scaled to the weighted efficiency. |
| Inverter Loss over nominal inv. power | inverter_over_power | `clipping` | PVsyst clips per MPPT or inverter as wired (case 9); Meridiana clips the pooled AC power. |
| Max input current, over voltage, power and voltage thresholds, night consumption | inverter_max_current, inverter_over_voltage, inverter_power_threshold, inverter_voltage_threshold, night_consumption | none | Usually 0 to -0.05 %; -0.25 % in case 13 and -1.99 % in case 20 (voltage threshold). |
| Available Energy at Inverter Output | inverter_output | value after `clipping` | Node. |
| Auxiliaries | auxiliaries | none | Constant or proportional (e.g. 3 W/kW); -0.13 to -0.5 % in the cases. |
| AC ohmic loss | ac_ohmic | `ac_wiring` | PVsyst gives the fraction "at STC". Meridiana gives it at the nominal AC power, so with a DC/AC ratio other than 1 the input must be rescaled [I]. |
| Medium voltage transfo loss, MV and HV line | mv_transformer, mv_line, hv_line | none | Iron and copper fractions are in casi.json (`losses.transformer`). Typical step -1.0 to -1.8 %. |
| Unused energy (grid limitation) | grid_limitation | none in `simulate()` | Meridiana's export limit lives in economics.py (self-consumption balance), not in the production chain. |
| System unavailability | unavailability | `unavailability` | PVsyst draws random outage periods from a time fraction, so the energy loss is smaller than the input (2 % gives -1.64 %, 1 % gives -0.81 %, 0.5 % gives -0.40 %, cases 18, 23, 4). Meridiana applies the input as an energy fraction. |
| Energy injected into grid | e_grid | value after `unavailability` | End. |

### 5.3 What Meridiana lacks to run the other cases [V]

- **Trackers** (horizontal N-S, tilted axis, vertical axis, backtracking, rotation limits). `ArraySpec` has a fixed tilt and azimuth: cases 6 and 17-27 cannot run.
- **Bifacial** (rear-side irradiance and its mismatch): cases 3, 4, 6, 21-27.
- **MV transformer, MV and HV lines, auxiliaries, night consumption:** most utility cases.
- **Ageing (degradation per year, ageing mismatch):** cases 1-3, 12, 14, 21, 23. **Spectral correction:** cases 12 and 19.
- **Inverter details:** clipping by MPPT input or by inverter as wired, threshold and voltage-window losses, grid limitation in the production chain.
- **Shading of the ground-reflected part** by rows and obstacles, and the albedo factor of the horizon.
- **Weather other than the PVGIS typical year:** Meteonorm, Solcast and Solargis files, or a typical year rebuilt from monthly values.
