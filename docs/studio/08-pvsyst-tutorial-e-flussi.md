# PVsyst 8 tutorials and user workflows: official PDFs, official videos and third-party practice, for Meridiana

Research report for **Meridiana**, an open-source desktop PV design program (Python, PySide6/Qt 6, pvlib, GPL-3.0-or-later). Meridiana aims to cover at least every PVsyst function, with Aurora Solar as the UX reference.

This report is the companion of `docs/studio/06-pvsyst-aurora-pvlib.md` (called **"06"** below).
- **06** inventories PVsyst 8.1 from its **online help**.
- **This report (08)** looks at the **tutorials**: how PVsyst SA teaches the program in its PDF tutorials and videos, and how practitioners in 12 languages actually use it. Forums are covered by a separate study.

It answers five questions:
- (a) In what order do users go through PVsyst's dialogs, task by task?
- (b) Which values do tutorials recommend?
- (c) Where do users get stuck, and what could a better tool automate?
- (d) Which tutorial steps does Meridiana already cover?
- (e) Which sources say so?

Research date: 22 October 2026. The research was read-only: no accounts, no logins, no forms, no installers, no API keys, and no personal data sent anywhere.

## 0. Scope, sources and how to read this report

### 0.1 Versions checked

| Item | Version or status on 22 Oct 2026 | Source |
|---|---|---|
| PVsyst | 8.1.7 (30 Sep 2026), as in 06 | https://www.pvsyst.com/help/release-notes/index.html |
| Official PDF tutorials | 21 PDFs listed for PVsyst 8.1, 8, 7 and 6, in English and French. The newest is the 160-page "Grid-connected - Comprehensive Overview" for 8.1, created 1 May 2026. Release 8.0.20 (4 Feb 2026) announced the step-by-step, stand-alone and pumping PDFs. | https://www.pvsyst.com/en/training/pdf-tutorials ; release notes 8.0.20 |
| Official videos | Main channel @PVsystOfficial: 102 videos in 23 playlists, from 29 May 2020 to 13 Oct 2026. Mirror channels in French, Spanish and Chinese. | https://www.youtube.com/@PVsystOfficial |
| New product | **PVsystBasic 1.0**: guided, offline software for solar pumping only, CHF 25 per year. Its playlist starts 25 Jun 2026. Not covered by 06. | https://www.pvsyst.com/en/products/pvsyst-basic |

### 0.2 Method

**Official PDFs.**
- The tutorial page links 21 PDFs: 11 for PVsyst 8 and 8.1, 9 for PVsyst 7 and 1 for PVsyst 6. All of them were found and checked.
- Language variants: only `-en` and `-fr` exist. The `-es`, `-it`, `-de`, `-zh`, `-cn` and `-pt` variants return HTTP 404.
- 26 files were downloaded into `l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\`, which lists them in its own `README.md`:
  - all 8 and 8.1 tutorials in English and French;
  - two PVsyst 7 tutorials that have no PVsyst 8 equivalent.
- Reading:
  - every English PVsyst 8 and 8.1 PDF was read in full with PyMuPDF;
  - the two archived PVsyst 7 tutorials and the PVsyst 7 meteo tutorial were read in full;
  - the other PVsyst 7 PDFs were checked against their PVsyst 8 successors.
- Page numbers cited as "p. N" are the PDF page numbers. They equal the printed page footers.

**Official videos.**
- Collected for every video of the main channel:
  - title, date, length and view count;
  - description and chapter list, from the public watch pages;
  - playlist membership;
  - the YouTube channel feed (`/feeds/videos.xml`), which gives exact dates.
- The French, Spanish and Chinese channels were listed the same way.
- **No video was downloaded.** Transcripts were not used: YouTube serves them only through an internal interface, not as public text.

**Third-party tutorials.**
- Four parallel research agents searched in each language:
  - Portuguese and Spanish;
  - Italian, French and German;
  - English;
  - Arabic, Chinese, Turkish and others.
- Each agent read PDFs and pages directly and recorded URL, date, version, steps, values and friction points.
- Spot checks: I re-read the numbers I rely on most against the original files or pages. These are the Italian VIA annexes, the Villoz slides, the Entergy appendix, the IEA PVPS summary, the Candela articles and the Arabic video descriptions. All matched.

**Limits.**
- **Search budget.** The shared web-search budget of this session ran out (200 calls). After that only known URLs were opened, and nothing was searched through other services. Section 6.6 lists what is therefore missing.
- **Blocked sites.** Sites that refused automated access were not worked around. Examples: HTTP 403 and 521, Cloudflare challenges, login walls. They are listed in section 6.5.

### 0.3 Conventions

- **Source IDs.**
  - `OFF-nn`: official PDF tutorials.
  - `W-nn`: official web pages.
  - `VID`: official videos, cited by YouTube id.
  - Third-party sources by language: `EN-`, `IT-`, `FR-`, `DE-`, `PT-`, `ES-`, `ZH-`, `AR-`, `TR-`, `VI-`, `ID-`, `JA-`.
  - Every ID resolves to a URL in section 6. Each subsection of section 2 also repeats the URLs it uses.
- **[unverified]** marks a statement made by only one unofficial source.
- **(analysis)** marks the researcher's own reasoning, not a source.
- **Wording.** Everything is paraphrased. Quotes are verbatim and at most 25 words.
- **Azimuth.** PVsyst's convention is used: south = 0°, west positive (as in 06).
- **Meridiana status** comes from `docs/funzionalita.md` (22/10/2026 morning):
  - ✔ exists;
  - ◐ partial;
  - ○ missing.

### 0.4 Executive summary

1. **PVsyst's official teaching path is short.** Every first project in an official tutorial follows the same skeleton (section 2.0):
   - project, site and weather;
   - project settings (albedo, design temperatures);
   - variant: Orientation, then System (pre-sizing by power or area, PVsyst proposes strings);
   - Simulation, Results, Report;
   - then, one at a time, horizon, near shading, detailed losses and economics, each saved as a new variant and compared through the loss diagram.

   Times stated:
   - official video "My First Project": 10 min 17 s;
   - official "My first project" PDF: 1 hour;
   - complete 8.1 manual: 5 hours;
   - third-party first-project videos: 10 to 30 min.

   Third-party sources describe 3D scenes, Module Layout and imports as the slow part: "hours or even days" [EN-44, vendor claim, https://www.youtube.com/watch?v=kWlcBDOoQ5s]. (Sources: OFF-01, OFF-12, VID yN9vi7uGFD4.)

2. **Most friction comes from describing the same geometry twice.** The Orientation dialog, the System sub-arrays, the 3D scene and the Module Layout must agree in four ways:
   - tilt and azimuth;
   - module count, within a tolerance;
   - sensitive area, within 8 % for imports;
   - exact module positions.

   When they disagree, buttons turn red, the simulation is blocked, or the user must disable the interpenetration check. Imports add their own steps (OFF-06):
   - rotate SketchUp scenes by 180°;
   - convert DAE units from inches;
   - make one export per orientation (Virto.CAD).

   Tutorials in every language spend time on these repairs (sections 2.2, 4.1). (analysis) Meridiana's single drawn model removes this whole class of errors. Plant owners still ask bidders for a PVsyst model with its version and inputs fixed "as bid" (EN-09, a US utility tender template), and vendors now push designs into PVsyst instead of replacing it (EN-44, PVcase, RatedPower, Virto.CAD). Export to PVsyst's 3D formats (PVC or PVCollada) is therefore worth keeping in the plan.

3. **The official documents contradict one another on defaults that users copy.**
   - Overload loss limit for design: 3 % in the 8 and 8.1 PDFs, 4 % in the help and release notes.
   - Partitions for landscape strings wired in U: 3x in the May 2026 PDF, x in the help, where 3x is marked as the pre-8.0 rule.
   - Electrical effect fraction: "60-80 %" as a general guess in the PVsyst 7 tutorial, against a 100 % default plus calibration in the 8.1 manual.
   - Module quality: half the lower tolerance (PVsyst 7 PDF) against a quarter of the tolerance spread (8.1).
   - Version changes that make old and new reports incomparable:
     - IAM default to Fresnel (6.67);
     - AC-loss reference (7.2);
     - PR_Bifi (8.0.12; in one 99 MWp case 93.56 % becomes 87.89 %);
     - ageing split 80/20 (8.0).

   (analysis) Every default should therefore carry its source and version, which matches Meridiana's pedigree principle. (Sections 1.3 and 3.)

4. **Typical values converge across about 150 tutorials.**
   - Far albedo 0.20.
   - Uc 29 / Uv 0 for free-standing arrays. Several Italian permitting reports leave the default 20 on trackers.
   - DC wiring 1.5 % at STC, which gives an annual loss of about 50 to 60 % of that.
   - Module quality about -0.8 %, or a quarter of the tolerance.
   - Mismatch 1 to 2 %.
   - LID 1 to 2 %, net of the warranty.
   - Soiling 1 to 3 %, higher in deserts.
   - Degradation 0.3 to 0.5 %/yr.
   - Transformer about 1 %.
   - DC/AC 1.1 to 1.3.
   - Unavailability set to 0 % in PVsyst and applied afterwards.
   - Resulting PR 78 to 86 %.

   Section 3 gives ranges, the most frequent value and sources.

5. **What tutorials do not cover is where Meridiana can lead.** Nobody has a usable PVsyst workflow for:
   - agrivoltaics: there is no crop-level light output, and the Italian MASE 2022 guideline indices are absent from the plants' PVsyst models;
   - east-west and dome bifacial;
   - carports;
   - LeTID;
   - tariff-driven storage. An Italian MSc thesis rejected PVsyst's storage logic for the Italian market, and users do dispatch and economics in their own tools;
   - P50/P90 plausibility. An Italian permitting report used 0.5 % interannual variability, which narrows P90 to 2.4 % below P50, and nothing warned.

   Meridiana already covers Italian economics, export limits and self-consumption. Agrivoltaic irradiance maps, input sanity checks on P50/P90 and tracker GCR, and a PVsyst export are the next differentiators (analysis). (Sections 2.5 to 2.10, 2.14 and 4.)

6. **Electrical shading is the most taught advanced topic.** The 8.1 manual adds three things:
   - a partition rule table;
   - Module Layout limits: crystalline modules only, warning above 1 MWp, error above 5 MWp, thin shadows underestimated;
   - an I/V example: with 3 strings per MPPT, shading one third of one string's sub-modules loses about 85 % of that string's output.

   Meridiana's bypass-diode model already works at Module-Layout level for every project, without manual string assignment. The tutorials provide ready validation cases: OFF-01 pp. 129-140; ZH-13 tracker strategies; ZH-16 half-cut cells, 6.53 % against 3.85 %; FR-01 roof, 5.3 % geometric plus 8.2 % electrical.

7. **Weather data handling is taught as a quality-control discipline**, not just as an import (OFF-03):
   - time stamps label the start of the interval;
   - check against the clear-sky curve, where daily points should not exceed it by more than 3 to 5 %;
   - best clear days within 5 %;
   - synthetic data vary by 0.5 to 1 % per year from one generation to the next.

   Third-party guides add vendor-specific traps: one year per file, local time against UTC, clearness limits hidden in advanced parameters, mandatory GHI. Meridiana's PVGIS-only path avoids most of them today. The other import formats and the quality checks are still open (○).

### 0.5 Contents

- 0. Scope, sources and how to read this report
- 1. The official learning material
  - 1.1 PDF tutorials
  - 1.2 Official videos, webinars, courses and PVsystBasic
  - 1.3 Where the tutorials add to, or contradict, the online help
- 2. The canonical PVsyst 8 workflow, task by task
  - 2.0 The skeleton common to every grid-connected project
  - 2.1 Residential rooftop
  - 2.2 Commercial rooftop with obstacles and a 3D near-shading scene
  - 2.3 Ground-mounted fixed sheds (including terrain)
  - 2.4 Single-axis trackers and backtracking
  - 2.5 Bifacial
  - 2.6 East-west and domes
  - 2.7 Carport
  - 2.8 Agrivoltaics
  - 2.9 Self-consumption and storage
  - 2.10 Grid power-injection limit
  - 2.11 Horizon import
  - 2.12 Weather import (PVGIS, Meteonorm, Solargis, NASA POWER, others)
  - 2.13 Batch simulation and parametric studies
  - 2.14 P50/P90
  - 2.15 Ageing
  - 2.16 Economic evaluation (and carbon balance)
  - 2.17 Reading the report and the loss diagram
  - 2.18 Module Layout
  - 2.19 Electrical shading effect (partition model)
  - 2.20 String sizing
  - 2.21 Cable and transformer losses
  - 2.22 Unavailability
  - 2.23 LID and LeTID
  - 2.24 Soiling and snow
  - 2.25 Albedo
  - 2.26 Spectral correction
  - 2.27 Components from datasheets (PAN and OND)
  - 2.28 Stand-alone and pumping (brief)
- 3. Typical values recommended across tutorials
- 4. UX friction points and what a better tool can automate or infer
- 5. Checklist: tutorial steps mapped to Meridiana
- 6. Sources
- Appendix A. Official video catalogue (main channel)

---

## 1. The official learning material

### 1.1 PDF tutorials

Source page: https://www.pvsyst.com/en/training/pdf-tutorials (W-01), with the French page https://www.pvsyst.com/fr/training/pdf-tutorials. The Spanish page links the English files. All files sit under `https://www.pvsyst.com/pdf/pdf-tutorials/`.

**How to read the table.**
- Dates are the creation dates in the PDF metadata. The HTTP `Last-Modified` header reads 12 Oct 2026 for every file: that is the date the site was redeployed.
- Durations are those printed on the tutorial page.
- "Arch." means archived in `l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\`.

| ID | Title (EN) | PVsyst | Path | Pages EN / FR | PDF date (EN) | Duration | Arch. | What it covers, and what it adds to 06 |
|---|---|---|---|---|---|---|---|---|
| OFF-01 | Grid-connected - Comprehensive Overview | 8.1 | pvsyst-8.1/pvsyst-tutorial-v8-1-grid-connected-en.pdf | 160 / 166 | 01/05/2026 | 5 h | yes | **Covers** every grid-connected dialog. **Adds:** partition rule table (pp. 104-106); Module Layout procedure and limits (ch. 11); I/V worked examples of bypass diodes (pp. 129-140); power shifting (pp. 52-55); economic and carbon formulas (ch. 12); project-settings tabs (pp. 13-14). Two pages (113-114) still carry French captions. |
| OFF-02 | Grid-connected | 8 | pvsyst-8/pvsyst-tutorial-v8-grid-connected-en.pdf | 83 / 88 | 14/11/2024 | 4 h | yes | **Covers** the 2024 edition of OFF-01. **Adds:** three spectral models (CREST, Sandia, First Solar; p. 32); transformer datasheet inputs (p. 25); horizon import from the web (p. 41). |
| OFF-03 | Meteorological data handling | 8 | pvsyst-8/pvsyst-tutorial-v8-meteorological-data-en.pdf | 28 / 32 | 31/10/2024 | 1 h | yes | **Covers** .SIT and .MET files, synthetic generation, PVGIS import and a step-by-step custom CSV import. **Adds** quality-control checks with thresholds (pp. 12-15, 27-28). |
| OFF-04 | Components databases | 8 | pvsyst-8/pvsyst-tutorial-v8-components-database-en.pdf | 13 / 14 | 31/10/2024 | 1 h | yes | **Covers** PAN and OND creation from datasheets, field by field: which datasheet values PVsyst ignores (NOCT, efficiency, nominal PV power), the 0.2 % Vmpp·Impp rule, and Pthresh ≥ 0.5 % Pnom. |
| OFF-05 | Import topography | 8 | pvsyst-8/pvsyst-tutorial-v8-import-topography-en.pdf | 15 / 15 | 31/10/2024 | 1 h | yes | **Covers** four routes: the v8 satellite image and terrain download; Google Earth path to GPS Visualizer, then CSV; DWG to DAE through SketchUp; SketchUp terrain. |
| OFF-06 | 3D scene export procedures | 8 | pvsyst-8/pvsyst-tutorial-v8-export-3d-scene-to-pvsyst-en.pdf | 48 / 46 | 31/10/2024 | 1 h | yes | **Covers** SketchUp, Archelios Pro, PVcase Ground and Roof, Virto.CAD, Helios 3D, and a multi-orientation PVC with domes. **Adds:** units, rotation and tolerance traps. |
| OFF-07 | Pseudo-sub-hourly simulation | 8 | pvsyst-8/pvsyst-tutorial-v8-pseudo-sub-hourly-simulation-en.pdf | 15 / 16 | 31/10/2024 | 1 h | yes | **Covers** splitting minute data into 60 hourly files with time shifts and running them in batch. Superseded by native sub-hourly simulation in 8.1.0 (06, 1.1.14.3). Its batch-file example is still the clearest official one. |
| OFF-08 | Standalone - My first project | 8 | pvsyst-8/pvsyst-tutorial-v8-stand-alone-en.pdf | 15 / 17 | 31/10/2024 | 1 h | yes | **Covers** a stand-alone system: user's needs (6 methods), storage, sub-array, back-up. |
| OFF-09 | Standalone - Battery isolated (step-by-step) | 8 | pvsyst-8/pvsyst-tutorial-v8-stand-alone-with-batteries-en.pdf | 72 / 72 | 30/09/2025 | 2 h | yes | **Covers** five variants as screenshots with numbered call-outs. This is the only official click-by-click tutorial. |
| OFF-10 | Pumping systems - My first project | 8 | pvsyst-8/pvsyst-tutorial-v8-pumping-system-en.pdf | 26 / 26 | 17/11/2025 | 1 h | yes | **Covers** pumping tests, wells, lakes, water needs, pump and controller. |
| OFF-11 | Pumping - Over the sun (step-by-step) | 8 | pvsyst-8/pvsyst-tutorial-v8-pumping-over-the-sun-en.pdf | 94 / 95 | 16/01/2026 | 2 h | yes | **Covers** five pumping variants, including economic evaluation. |
| OFF-12 | Grid-connected - Part 1/4 - My first project | 7 (7.2 screenshots) | pvsyst-7/pvsyst-tutorial-v7-grid-connected-1-en.pdf | 34 / 34 | 21/07/2022 | 1 h | yes | **Covers** the only official walkthrough of simulation, Results dialog and report, page by page. **Adds:** message colour code, variant saving, the 936-variant limit, horizon file traps. |
| OFF-13 | Grid-connected - Part 2/4 - Near shadings 3D scene | 7 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-2-en.pdf | 29 / 28 | 21/07/2022 | 1 h | yes | **Covers** the only official guided 3D exercise (the DEMO Geneva farm) and the "60-80 %" electrical-fraction advice. |
| OFF-14 | Grid-connected - Part 3/4 - Meteo data handling | 7 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-3-en.pdf | 30 / 31 | 21/07/2022 | 2 h | no (superseded by OFF-03) | **Adds** that Meteonorm hourly tables cannot be exported, for contractual reasons. |
| OFF-15 | Grid-connected - Part 4/4 - Component databases | 7 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-4-en.pdf | 14 / 14 | 21/07/2022 | 30 min | no (OFF-04) | Superseded. |
| OFF-16 | 3D Procedures - Ground and Topography | 7 | pvsyst-7/pvsyst-tutorial-v7-ground-and-topography-en.pdf | 9 / 10 | 24/04/2024 | 15 min | no (OFF-05) | Superseded. |
| OFF-17 | 3D Procedures - Export Procedures | 7 | pvsyst-7/pvsyst-tutorial-v7-export-to-pvsyst-en.pdf | 50 / 50 | 13/12/2023 | 2 h | no (OFF-06) | Superseded. |
| OFF-18 | Standalone system - My first project | 7 | pvsyst-7/pvsyst-tutorial-v7-standalone-en.pdf | 28 / 31 | 21/07/2022 | 1 h | no (OFF-08, OFF-09) | Superseded. |
| OFF-19 | Pumping - Part 1/2 - Hydraulic circuit | 7 | pvsyst-7/pvsyst-tutorial-v7-pumping-1-en.pdf | 8 / 8 | 21/07/2022 | 15 min | no (OFF-10 includes pumping tests) | Superseded. |
| OFF-20 | Pumping - Part 2/2 - My first project | 7 | pvsyst-7/pvsyst-tutorial-v7-pumping-2-en.pdf | 22 / 24 | 21/07/2022 | 40 min | no (OFF-10, OFF-11) | Superseded. |
| OFF-21 | Grid-connected - Comprehensive overview | 6 | pvsyst-6/pvsyst-tutorial-v6-grid-connected-en.pdf | EN only | not checked | 4 h | no | Superseded. |

**Style of the official material** (analysis):
- OFF-01 and OFF-02 are manuals of the windows; they are not exercises.
- The only guided exercises are:
  - the two PVsyst 7 parts (OFF-12, OFF-13): a 125 m² farm roof near Geneva, then its 3D scene;
  - the screenshot books for stand-alone and pumping (OFF-09, OFF-11).
- Grid-connected users who want a guided, current exercise depend on the videos (1.2) or on third parties.
- This explains why third-party tutorials are so numerous, and why so many still show PVsyst 6.x or 7.x screens.

### 1.2 Official videos, webinars, courses and PVsystBasic

**Channels**

| Channel | URL | Content on 22 Oct 2026 |
|---|---|---|
| PVsyst (main, English) | https://www.youtube.com/@PVsystOfficial (channel id UCMzsEWHk3f7XD_dg1lngmzg) | 102 videos in 23 playlists. The full list is in Appendix A. |
| PVsyst - Français | https://www.youtube.com/@pvsystofficial-fr | French versions of the PVsyst 7 and 8 tutorials, 17 playlists, among them "Comprendre les systèmes photovoltaïques". Also three French-only live classes: how a PV panel works, measuring the weather, what an inverter is (the latest about 4 weeks old). |
| PVsyst - Español | https://www.youtube.com/@pvsystofficial-es | 17 videos, 7 playlists: Spanish versions of the PVsyst 8 project series, the bifacial series and the CLI. |
| PVsyst - 中文 | https://www.youtube.com/@pvsystofficial-cn | 26 videos, 10 playlists: Chinese versions of the same series. Most have under 400 views. |

YouTube auto-translates titles and dubs audio for the viewer's language. A search from Italy or Germany therefore shows official or English videos under Italian or German titles. Both the IT/FR/DE and PT/ES research agents found this (sections 6.4, 6.5).

**Playlists of the main channel**

| Group | Playlists |
|---|---|
| Current, PVsyst 8 and 8.1 | "Creation of projects in PVsyst 8" (6 videos); "General & Novelties in PVsyst 8 (2025)" (7); "General & Novelties in PVsyst 8.1 (2026)" (3); "PVsystCLI" (2); "PVsystBasic" (2) |
| PVsyst 7 "Fundamentals", May 2022 | "Introduction" (3); "Site and Weather" (4); "PV Components" (6); "My First Shading Project" (8); "Losses and Results" (5) |
| PVsyst 7 thematic | "Creation of projects" (7); "Near Shadings" (8); "Module Layout" (4); "Storage & Self-Consumption" (4); "Bifacial & Tracking Systems" (6); "Advanced Tools" (6: optimisation, batch, P50-P90, carbon, ageing losses, ageing tool); "Meteo & Measured data" (4); "Economic Evaluation" (2); "Components Database" (3); "General" (4, including two PVPMC talks); "Thematic Tutorials" (52, a superset); two licence playlists |

**PVsyst 8 and 8.1 tutorials** (chapter lists as shown on the public pages; most read like YouTube's automatic chapters)

| Video | Date, length | Chapters |
|---|---|---|
| PVsyst 8 _ My First Project (Grid Connected System) `yN9vi7uGFD4` | 27/01/2025, 10:17 | Introduction; Workflow 2:08; Orientation 3:55; System 5:30; Inverter 6:40; Simulation 8:20 |
| PVsyst 8 _ Multi-MPPT (Power sharing and Multi-orientation daily sharing) `6QpgYVrLZus` | 02/06/2025, 8:45 | Multi-MPPT concept; Power sharing configuration 1:53; Complex inverter setups 4:37; Daily multi-orientation 6:44 |
| PVsyst 8 _ Detailed Losses `1FTEVIt9HWU` | 03/04/2025, 10:29 | Thermal 0:26; Ohmic and wiring 1:54; Module quality and soiling 4:11; Incidence and auxiliary 5:55; Degradation and reliability 6:54; Spectral 9:23 |
| PVsyst 8 _ Horizon (Far Shading) `dHBGsOrGw5o` | 26/08/2025, 5:21 | Far shading 0:20; Guidelines 1:01; Sun path diagram 1:41; Manual drawing 2:26; Importing 2:52; Location and simulation 3:40; Applying and saving 4:36 |
| PVsyst 8 _ Near Shadings (3D Scene) `fZB2qAW8_qo` | 09/10/2025, 10:16 | Electrical shading losses 1:28; Scene construction tools 2:03; Creating and editing objects 3:20; Transformation and view 5:07; PV zones and trackers 5:58; Managing objects 7:09; Orientation management 7:54; Shading animation 8:24; Calculation modes and tables 9:15 |
| PVsyst 8_Module Layout `3D8Ak3LaLis` | 28/07/2026, 6:51 | Understanding shading losses; Module layout basics 1:05; Spatial arrangement 2:36; Electrical configuration 3:40; Simulation and validation 4:46 |
| PVsyst 8 _ Orientations Novelties `KIxXYfEl_e8`; Near Shadings Novelties `CzwlfqrqTKw` | 13-14/11/2024, 3:29 and 3:00 | Orientation; Interactive Map |
| PVsyst 8 _ Battery energy storage systems strategy `VHo-d-PFDlE` | 21/11/2025, 13:25 | From the PVPMC 2025 talk: storage strategies 0:24; power shifting 3:12; use case 4:43; results and economics 7:45; battery degradation 10:25 |
| PVsyst 8.1_Sub-hourly simulation, weather data import and Novelties `W19FmnUzrkE` | 12/05/2026, 3:27 | (no chapters) |
| PVsystCLI _ Batch Mode `SX3dQ2PHh_4`; Presentation of PVsystCLI `586KBbVsFrA` | 09/01/2026 and 07/02/2025 | Required batch parameters; configuring batch files; scenarios; execution. Installation; running simulations; weather conversion. |

**Webinars**

| Webinar | Date | Content |
|---|---|---|
| Webinar No1 and No2 "Presentation of PVsyst 8 & PVsystCLI" (`pL3b9j2ZJT0`, `-VAqV6D3G08`) | 6 and 9 Dec 2024, about 60 min each | Multiple orientation modelling (1:22-12:14); simulation accuracy and tools; CLI automation; roadmap |
| Q&A video (`dQ4tr-zOW20`) | 20 Dec 2024, 12:46 | 18 chapters: topography sources and layers; bifacial for domes and vertical systems; floating PV; orientation management and errors; mixing orientations; sub-hourly simulation; clipping correction; limits of synthetic data; tracker diffuse modelling; generating tracker arrays |
| 2026 webinars N1 and N2 "PVsyst 8.1, CLI & PVsystBasic 1.0" (`Dtqv8sMczrs`, `Xz4f-pq1CzE`) | 5 and 7 May 2026, about 60 min each | Weather import (about 11-12 min); sub-hourly simulation (about 11-12 min); PVsystBasic; CLI; Q&A |

(analysis) The Q&A chapter titles are a good proxy for what users asked PVsyst staff in late 2024: topography, domes and vertical bifacial, orientation errors, sub-hourly clipping, trackers.

**Courses and paid support (W-03)**
- PVsyst sells online consulting sessions: 2 hours, CHF 700 per session, at most 5 participants. The vendor asks users to watch the tutorials first.
- The table of topics loads from the site's `/api/` path, which `robots.txt` disallows, so it was not read.
- Free courses and workshops:
  - the GIZ/ANME 4-day course in Tunisia, whose day 4 covers PVsyst, 3D layout, wiring, trackers, grid limitation and P50/P90 (FR-02);
  - a university workshop in Bangladesh (EN-42);
  - TAQA Academy in Arabic (AR-06);
  - a stand-alone course at UiTM, Malaysia (EN-32).
- Third-party paid courses exist (not bought):
  - INES (France), 2 days, about €1,000 [unverified, FR-13];
  - NEPSEN (France), 2 days, from €1,200 (FR-03);
  - SEI (US) CE524 (EN-31);
  - GSES (Australia) and GUtech (Oman), blocked (EN-S5, EN-S6);
  - Udemy courses in Arabic and Turkish (AR-07, TR-03).

**PVsystBasic 1.0** (W-04, https://www.pvsyst.com/en/products/pvsyst-basic ; help https://www.pvsyst.com/help-basic/ ; videos `G_u6F1Owf-U` of 25/06/2026 and `MznqfJwrplg` of 13/10/2026)
- PVsyst SA's first "simplified" product, limited to direct solar pumping.
- It guides the user "step-by-step in selecting components", runs offline and offers contextual help at every step.
- It comes with a library of didactic "technical tools" pages on electricity, photovoltaics and hydraulics.
- Price: CHF 25 per year, with a 30-day trial.
- (analysis) The vendor itself acknowledges that a guided, step-by-step flow is needed for a narrow use case. It does not apply this to grid-connected design.

Sources for courses:
- FR-02 https://energypedia.info/wiki/Article_sur_la_formation_PVSyst ; FR-03 https://www.actu-environnement.com/formations-professionnelles/photovoltaique-estimation-production-pvsyst-42140.html ; FR-13 https://www.ines-solaire.org/formation/!/formation/conception-et-simulation-des-systemes-pv-sur-pvsyst-/
- EN-31 https://solarenergytraining.org/course/info.php?id=1095 ; EN-32 https://solar.uitm.edu.my/wp-content/uploads/2024/03/Synopsis-SAPV-using-PVsyst.pdf ; EN-42 https://www.youtube.com/watch?v=AGEdjr0etR0 ; EN-S5 https://www.gses.com.au/?p=15805 ; EN-S6 https://www.gutech.edu.om/master-pvsyst-design-level-3-solar-pv-simulations
- AR-06 https://www.youtube.com/playlist?list=PLtpdYdedpNjri6aPAqKjdIHTyU8thbzmc ; AR-07 https://www.udemy.com/course/excel-pvsyst/ ; TR-03 https://www.udemy.com/course/pvsyst-egitimi-gunes-enerji-santrali-tasarm-ve-raporlama/

### 1.3 Where the tutorials add to, or contradict, the online help

06 is the reference for what the help says. The points below are what the tutorials say differently or in addition.

| Topic | Tutorial says | Help (as reported in 06) | Note |
|---|---|---|---|
| Overload loss limit for inverter design | Default 3 % (OFF-01 p. 13; OFF-02 p. 9) | Release notes 8.0.13: warnings at 2 % and 4 %; "Limit overload loss for design" max 4 % by default (06 §1.1.9.4) | The PDFs keep the older value. |
| Partitions, landscape strings wired in U (xLU) | 3x partitions (OFF-01 p. 105, May 2026) | x, an overestimate preferred because the fraction can correct it; 3x was the rule up to 7.4.8 (06 §1.1.8) | The 8.1 PDF still prints the pre-8.0 rule. Rendered page checked. |
| Electrical effect fraction | PVsyst 7: no good estimate; "a reasonable guess would be around 60-80%" for the customer report (OFF-13 p. 28). PVsyst 8.1: default 100 %, calibrate by Module Layout on a sub-system, e.g. 3 % / 4 % gives 75 %; "generally close to 100% for regular systems" (OFF-01 pp. 103, 110) | About 100 % for regular row shading, 60-80 % for irregular objects (06 §1.1.8) | Third-party files still use 80 % on regular tracker rows (IT-05). (analysis) Per OFF-01 that understates electrical loss on regular rows. |
| Module quality default | Half the lower tolerance (OFF-12 p. 26) | A quarter of the spread between low and high tolerance (OFF-01 p. 34; 06 §1.1.13.5) | 06 already flags the help-internal inconsistency. |
| Uc default | "From version 6 onwards the default is set to 20" (OFF-12 p. 24); 18 W/m²K measured for quasi-horizontal modules on a steel roof with 8 cm spacing (OFF-12 p. 24) | Uc 20 for new projects; 29 free-standing (06 §1.1.13.2) | The 18 W/m²K value appears only in the tutorial. |
| Soiling | "almost negligible in temperate-climate residential situations"; snow as 50 % soiling in a month with 15 days of cover (OFF-12 pp. 28-29) | No default stated (06 §1.1.13.7) | Two unofficial sources say the default was 3 % [unverified: EN-30 for 6.79; ZH-23]. |
| AC loss reference | PNomPV(ac) was the default before 7.2; now a choice per project, plus a preference for new projects (OFF-01 p. 34) | Same (06 §1.1.13.3) | SMA's French blog warns that pre-7.2 AC losses could distort yield (FR-04). |
| Transformer | Iron loss default 0.1 % of reference power; night disconnect; datasheet inputs recommended: nominal power, iron loss, copper loss (OFF-02 p. 25) | Same (06 §1.1.13.4) | (none) |
| Wiring loss | Annual effective loss "usually of the order of 50-60%" of the STC value (OFF-01 p. 32) | About 60 % (06) | (none) |
| Shading-factor table grid | Pre-computed every 10° of sun height and 20° of azimuth; "fast" mode interpolates, "slow" mode recomputes at each step (OFF-01 p. 67) | See 06 §1.1.7 | Meridiana uses 5° by 4° (funzionalita F). |
| 3D vs system area tolerance | 8 % on active-surface dimensions for imports (OFF-06 p. 15); warning when module area exceeds scene area, and when it is below it by a factor of 1.5 (OFF-13 p. 23) | Thresholds are hidden parameters | (none) |
| Gap between PV plane and support | Active surface drawn 1 cm above the frame in SketchUp, while PVsyst needs a 2-3 cm margin, hence "Deactivate verification of field interpenetration" (OFF-06 p. 14) | About 2 cm in the tutorial; Helios ≥ 1 cm (06 §1.1.6) | (none) |
| Weather search radius | A nearby meteo file within 20 km is proposed (OFF-12 p. 8) | Search radius in project preferences (06 §1.1.1.2) | (none) |
| Variants | Up to 936 variants per project; files VC0, VC1, ..., VCA; use "Save As" to avoid overwriting (OFF-12 pp. 6, 19) | (not in 06) | Matches Daniel's "revisioni mai sovrascrivere" rule. |
| Message colours | Black = information; orange = acceptable design imperfection; red = error that blocks simulation; grey button = not defined (OFF-12 p. 13) | Status LEDs (06 §1.1.9.1) | (none) |
| Meteonorm hourly export | Meteonorm hourly tables cannot be exported, for contractual reasons (OFF-14) | (not in 06) | Relevant if Meridiana ever reads Meteonorm-based PVsyst files. |
| Synthetic weather | Two generations from the same monthly data differ by 0.5-1 % in yearly grid results (OFF-03 p. 10) | Algorithm in 06 §1.6.7 | Source of "noise" in comparisons. |
| Carbon tool | Default annual degradation 1 % (OFF-01 p. 156); PV system LCE default 46 gCO₂/kWh (IPCC, 26 publications); transport 35 gCO₂/t/km by sea, 60 by truck (OFF-01 pp. 158-160) | 06 §1.1.18 | 1 %/yr contradicts the 0.3-0.5 %/yr OFF-01 itself recommends for ageing (p. 39). |
| Module Layout limits | Crystalline only; thin shadows underestimated; warning above 1 MWp, error above 5 MWp; min shade area 0.024 m²; electrical calculation skipped below 1 % and above 98 % shading; 50 % bottom-cell threshold; 2 % size tolerance (OFF-01 pp. 109-111) | 06 §1.1.8 has most of these | Single source with all thresholds together. |
| Seasonal tilt in 3D | The 3D scene accepts one tilt, so use the summer tilt; a seasonal tilt gives a red error [unverified, ZH-01, 6.x] | (not in 06) | (none) |

---

## 2. The canonical PVsyst 8 workflow, task by task

Each subsection gives:
- the official sequence of dialogs and buttons, as the tutorials teach it;
- the parameters set and the values recommended;
- where users get stuck;
- the time stated, where one is;
- Meridiana's status and the sources.

Physics and model details are in 06, cited by section number.

### 2.0 The skeleton common to every grid-connected project

**Official sequence** (OFF-01 pp. 7-30; OFF-12 pp. 4-19; video `yN9vi7uGFD4`):

1. **Home page, Project design and Simulation, Grid-connected.**
   - PVsyst opens the most recent project automatically. The setting is Settings > Preferences > Default values > Automatic project loading.
   - The dashboard toolbar offers New, Load, Import/Export and **Client**. The client's company data can be printed on the report (OFF-01 p. 13).
2. **Project, Site.** Two ways:
   - pick one of about 2,500 Meteonorm sites;
   - or click New and place the point on the interactive map ("Accept selected point").

   The *Geographical Coordinates* tab shows latitude, longitude, altitude, time zone and the sun paths (OFF-01 p. 15; OFF-09 pp. 3-4).
3. **Weather.**
   - When the site is created, data are imported from a provider: Meteonorm (included in the licence), PVGIS, Solcast, SolarAnywhere or Solargis. An internet connection is needed, and some providers need their own licence.
   - On OK, PVsyst asks to save the site and the synthetic hourly file. Non-measured data are labelled with the year **1990** (OFF-01 p. 16).
   - PVsyst 7: a weather file within 20 km is proposed; otherwise a synthetic one is generated (OFF-12 p. 8).
4. **Project settings.** Values that apply to this project only (OFF-01 pp. 13-14; OFF-12 pp. 8-9):

   | Tab | Settings | Default or advice |
   |---|---|---|
   | Albedo | Far albedo | 0.2, the "standard value"; 0.8 for months with snow |
   | Design conditions | Lowest temperature for the absolute voltage limit | -10 °C; "ideally" the minimum ever measured in daylight, lower in mountains |
   | Design conditions | Hot and cold operating temperatures for the sizing graphs | (none) |
   | Design conditions | Overload loss limit | 3 % in the PDFs; see 1.3 |
   | Other limitations | Orientation tolerance, averaging tolerance, 3D/system area ratio | (none) |
   | Preferences | Weather search radius | "keep this value low" |

   Settings > Advanced settings are separate: they apply to all projects in the workspace (OFF-01 p. 11).
5. **Save the project.** Use a simple file name, because it labels every variant (OFF-12 p. 10).
6. **Variant: Orientation.** The button stays red until defined (OFF-12 p. 10).
   - Choose the field type: fixed planes, one-axis or two-axis families.
   - Set tilt and azimuth. North hemisphere: south = 0°, west = +90°, east = -90°. South hemisphere: north = 0°.
   - A quick optimisation chart shows the yield loss against the optimum, for the year, summer or winter (OFF-01 p. 18).
   - Since PVsyst 8: "Add Orientation" defines several orientations in one variant (OFF-01 p. 18).
7. **Variant: System.**
   1. Optional *Pre-sizing help*: desired power **or** available area (OFF-01 p. 26).
   2. Choose the module. Lists: "All modules" or "Favorites", filter by manufacturer.
   3. PVsyst hints at the minimum inverter power. The PVsyst 7 example: "the total power should be 7 kW or more" for 50 m².
   4. Choose the inverter. PVsyst then proposes the number of inverters, modules in series and strings, e.g. 1 inverter with 2 × 15 modules (OFF-12 pp. 12-13).
   5. Read the blue message panel. Black means information, orange a tolerable imperfection, red an error that blocks the simulation (OFF-12 p. 13).
   6. Optional checks:
      - *Sizing* button: the array I/V curve inside the inverter window, and the yearly power distribution for overload (OFF-01 pp. 27-28);
      - *Multi-MPPT / Power sharing* (OFF-01 pp. 28-30).
8. **Optional buttons, grey until used:** Horizon, Near shadings, Module layout, Energy management, Self-consumption, Storage, Detailed losses, Economic evaluation (OFF-01 contents).
9. **Run Simulation** (OFF-12 pp. 14-15).
   - The dates are those of the weather file. "Do not modify them".
   - Skip the *preliminary definitions* (output files and special graphs) for a first run.
   - A progress bar runs, then OK opens **Results**:
     - a parameter summary;
     - six key values;
     - the daily input/output diagram. It should be "roughly a straight line" that saturates slightly; points deviating at high irradiance mean overload.
10. **Report.**
    - PVsyst 7: 6 pages for a simple variant, up to 11 with details (OFF-12 p. 16).
    - It can be printed or copied, with header comments and a logo (video `OenFkw3P_3Y`).
11. **Save the variant** with a meaningful title (OFF-12 p. 19).
    - Files are VC0, VC1, ..., VCA.
    - Use **Save As** to avoid overwriting.
    - Up to 936 variants per project (OFF-12 p. 6).
12. **Iterate one perturbation at a time** (OFF-12 pp. 7, 20, 31):
    - horizon;
    - near shading;
    - detailed losses;
    - economics.

    Simulate and save each step. Compare loss diagrams; the report highlights the differences.

**Third-party practice.**
- The same order appears in Portuguese, Spanish, Arabic, French, Vietnamese and Chinese courses: PT-14, ES-04, ES-01, AR-01, FR-01, VI-02.
- PT-14 (PVsyst 8.1 Básico, 2026) is the closest to current practice. Its lessons are: pre-sizing, site and weather, orientations, system, detailed losses, then loss diagram.
- Other complete walkthroughs with the same order:
  - EN-33 (PVsyst 7.4.8): site, orientation, system, detailed losses, near-shading scene, rooftop, ground mount, shading factor, simulation;
  - Portuguese video courses PT-15, PT-17, PT-19, PT-20, PT-24, PT-25;
  - Spanish ES-05, ES-07, ES-08, ES-10;
  - French FR-05, FR-06, FR-07, FR-09, FR-11, mostly from francophone Africa;
  - Arabic AR-05, AR-06, AR-08;
  - Turkish TR-01, TR-02.

**Times stated.**

| Source | Time |
|---|---|
| Official PVsyst 8 video | 10 min 17 s |
| PVsyst 7 Project 001 video | 9 min 13 s |
| PT-14 lessons | 13-21 min each |
| ES-04 | 15 min |
| AR-01 (6 kWp house, 3 parts) | 29 min |
| AR-01 (10 kWp in one video) | 15 min |
| ES-01 | "a few minutes" of computing |
| EN-12 [unverified] | 10-30 s for a residential simulation |
| ES-03 [unverified, competitor marketing] | 30-60 min residential; 2-4 h commercial; 8-20 h above 10 MW |

**Meridiana.**

| Step | Status |
|---|---|
| Site from address or coordinates, altitude, PVGIS TMY, Tmin | ✔ |
| Project-wide undo and autosave | ✔ |
| Revisions saved as name_Rnn, never overwritten | ✔ |
| Variants inside one project and comparison | ○ |
| Continuous checks page | ◐ (no "Correggi") |
| Automatic sizing when no inverter is chosen | ✔ |

Sources:
- OFF-01 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8.1/pvsyst-tutorial-v8-1-grid-connected-en.pdf
- OFF-09 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-stand-alone-with-batteries-en.pdf
- OFF-12 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-7/pvsyst-tutorial-v7-grid-connected-1-en.pdf
- Videos: https://www.youtube.com/watch?v=yN9vi7uGFD4 ; https://www.youtube.com/watch?v=b-5KeNTPK2s ; https://www.youtube.com/watch?v=OenFkw3P_3Y
- PT-14 https://www.youtube.com/watch?v=EM6H2hcIYdA
- ES-04 https://www.youtube.com/watch?v=5XI4smWnDSE
- ES-01 https://creapre.ujaen.es/bitstreams/0cc2bb63-900b-48d2-a02a-38275d1785d5/download
- AR-01 https://www.youtube.com/playlist?list=PLKni-m2Qe57m49bbwmmIxUJKraBFMG2y1
- FR-01 https://energypedia.info/images/3/3a/PVraccord%C3%A9_au_r%C3%A9seau_Electrique.pdf
- VI-02 https://pdfcoffee.com/huong-dan-su-dung-pvsyst-pdf-free.html
- EN-12 https://surgepv.com/hub/solar-designing/energy-simulation/
- ES-03 https://www.surgepv.com/es/pvsyst-que-es
- Other walkthroughs:
  - EN-33 https://www.youtube.com/watch?v=w6VfdiLdqDI
  - PT-15 https://www.youtube.com/watch?v=qaCdi10tdVQ ; PT-17 https://www.youtube.com/watch?v=PYgIqn4q6-E ; PT-19 https://www.youtube.com/watch?v=a-UdUIPM0uQ ; PT-20 https://www.youtube.com/watch?v=RPAI88UcXaU ; PT-24 https://www.youtube.com/watch?v=d52IGp8e1Ds ; PT-25 https://www.youtube.com/watch?v=uX7pDxp8wU0
  - ES-05 https://www.youtube.com/watch?v=2iaaCQkHU9o ; ES-07 https://www.youtube.com/watch?v=O_X0NHK4adA ; ES-08 https://www.youtube.com/watch?v=mqDvY_dEDqE ; ES-10 https://www.youtube.com/playlist?list=PLvkibXrfEBaX1lg4TezKhF0hsHThjkRk9
  - FR-05 https://www.youtube.com/watch?v=uvmujJEKAsk ; FR-06 https://www.youtube.com/watch?v=TYRAoZKMAfQ ; FR-07 https://www.youtube.com/watch?v=Pomqln7KHDo ; FR-09 https://www.youtube.com/watch?v=akGz-UpctPE ; FR-11 https://www.youtube.com/watch?v=voGyUCFIP_M
  - AR-05 https://www.youtube.com/playlist?list=PLyiEdrKX7c24qvKohwkiRgOYvIJPR23t_ ; AR-06 https://www.youtube.com/playlist?list=PLtpdYdedpNjri6aPAqKjdIHTyU8thbzmc ; AR-08 https://it-sharks.com/en/lesson/solar-energy-course7-lesson10
  - TR-01 https://www.youtube.com/playlist?list=PL83lI-L5u1G96g9iHjgom6vjipHvR1BYn ; TR-02 https://www.youtube.com/channel/UCwjwdjwrB9v6HJosootldbg/videos

### 2.1 Residential rooftop

**Sequence**, following the official farm example (OFF-12, OFF-13), FR-01 and AR-01:

1. **Orientation.**
   - Tilt from the drawing (25° in OFF-12).
   - Azimuth: from the drawing (20° west in OFF-12), or measured on Google Maps against south (AR-01).
2. **System by available area.** OFF-12's 50 m² of roof leads to 30 × 300 W modules on a 7.5 kW inverter. Then PVsyst raises "The inverter power is slightly undersized"; OFF-12 tells the user to acknowledge it and continue (p. 13).
3. **3D scene.** Detailed in 2.2. The official house exercise (OFF-13):
   1. Create > Building/Composed object, with two parallelepipeds (10 × 35 × 5 m and 10 × 25 × 5 m).
   2. Place them with the mouse, then type exact X, Y and azimuth.
   3. Add a "Two-sided roof + Gables" (base width 11 m, top length 30.5 m, tilt 25°, gable angle ±45°).
   4. Copy and paste it for the second wing.
   5. Close the object.
   6. Add a *Rectangular PV plane* (3.5 × 15.5 m, tilt 25°). PV planes cannot belong to building objects.
   7. Position it from the top view, then raise it in the front view so it sits **just above** the roof.
   8. Add a silo (cylinder, radius 3 m, height 12 m) and a tree whose shape is dragged by its red points.
   9. Rotate the whole scene to the real azimuth.
   10. Run the shadow animation for 21 June and 21 December.
4. **Near shadings, "Linear"**, then the shading-factor table, then the iso-shading diagram (OFF-13 pp. 23-25).
5. **Strings.**
   - "According to module strings": partition rectangles, each representing a **string**, not a module (OFF-13 p. 26).
   - Or **Module Layout**, which FR-01 calls "Calepinage":
     1. "Import de la scène 3D".
     2. "Déf tous modules".
     3. Put modules that are shaded at the same time into the same string.
     4. Choose "Détaillé, selon calepinage" and re-simulate.
6. **Detailed losses** (FR-01):
   - thermal: "semi-integrated" for modules over tiles;
   - ohmic: from cable lengths (10 m on the roof plus 2 × 20 m down to the inverter); AC ignored because the meter sits next to the inverter;
   - quality -1 %, i.e. a gain, with sorted modules;
   - mismatch 1 %;
   - LID 2 %.
7. **Self-consumption**, if relevant. AR-01 shows five ways to enter the load and calls the hourly CSV "the most professional". Details in 2.9.

**Values.**
- Tmin: set the site value instead of -10 °C. AR-01 makes this a step of its own; ZH-02 found that the -10 °C default flagged a 21-module string as too long.
- Albedo 0.2.
- Soiling negligible in temperate residential areas (OFF-12 p. 28).
- Uc 20 for semi-integrated mounting, 15 for integrated (OFF-01 p. 31).

**Where users get stuck.**
- **Drawing the scene.**
  - The scene must be drawn in the architect's frame, then rotated (OFF-13 p. 19).
  - The plane must not be below the roof, or it is "permanently shaded" (OFF-13 p. 16).
  - Objects must not interpenetrate (OFF-13 p. 11).
  - Selection works only by clicking an object's **edges** in technical view (OFF-13 p. 8).
- **Module fitting.** "Adjust to modules" must be pressed before going back to the basic tab (FR-01). The 8.1 manual recommends defining tables "By modules" from the start (OFF-01 p. 94).
- **Warnings.** Beginners are taught to bypass them: AR-01 part 1 promises "how to hide the warning messages" (إخفاء رسائل التحذير) and "bypassing the warnings" at 2:29.
- **Electrical loss can exceed the geometric loss.** FR-01: «L'ombrage réel n'est que de 5.3 % mais l'effet électrique de la mise en série des modules abaisse encore le rendement de -8.2 %».

**Time.**
- Official 3D exercise: 1 hour of reading (OFF-13).
- AR-01 3D house: about 5 minutes of video (3:38 to 8:18).
- Fundamentals videos `qJ0P7szS_jo` and `Ey4CIKcY0F8`: 9:18 plus 7:01.

**Meridiana.**

| Step | Status |
|---|---|
| Roof tracing with CAD guides, roof types, obstacles with heights | ✔ |
| Automatic layout under the VVF rules | ✔ |
| Strings drawn per row | ✔ |
| Electrical effect from bypass diodes | ✔ |
| Shadow animation | ◐ (no sun view) |
| Ridge and eave from an edge; dormers | ○ |

Sources:
- OFF-12 (above); OFF-13 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-7/pvsyst-tutorial-v7-grid-connected-2-en.pdf ; OFF-01 (above)
- FR-01 https://energypedia.info/images/3/3a/PVraccord%C3%A9_au_r%C3%A9seau_Electrique.pdf (slides 30/05/2015, PVsyst 6)
- AR-01 https://www.youtube.com/watch?v=_TrMEL0J6N4 (14/07/2026), https://www.youtube.com/watch?v=-PdCTtYueAM , https://www.youtube.com/watch?v=VvwgbohIX9g
- ZH-02 https://www.candela.cn/1811/
- Videos https://www.youtube.com/watch?v=qJ0P7szS_jo , https://www.youtube.com/watch?v=Ey4CIKcY0F8

### 2.2 Commercial rooftop with obstacles and a 3D near-shading scene

**Three strategies** (OFF-01 pp. 69-70):
1. Build the scene in PVsyst.
2. Import it in 3DS, DAE, PVC or H2P.
3. Import it, then add shading objects in PVsyst.

**Building in PVsyst (8.1)**
- **Field zones** (OFF-01 pp. 91-96):
  - draw a rectangular, polygonal or freehand zone on the X-Y plane;
  - open the table-field dialog: description, orientation, table size "By Modules" (portrait or landscape, count, spacing);
  - set pitch, table spacing, alignment, distance from the ground, *automatic tilt* (follow the surface), *automatic length* and *create trackers*;
  - press **Fill Zone**, then add or remove tables, slide them along their axis, and draw exclusion zones.
- **Automatic altitude** places tables on a roof or terrain at a set clearance (OFF-01 pp. 80-81).
- **List and manage objects** (Ctrl+G) (OFF-01 pp. 79-80):
  - filter and sort;
  - edit several objects as a group;
  - copy and paste to and from Excel, including the header row with the #, Type and Name columns;
  - export to CSV.
- **Drawing tools** (OFF-01 p. 91):
  - freehand triangle, parallelepiped, house, tree, cable, extruded polygon, rectangular PV table;
  - measuring distance (Ctrl+L) and angle (Ctrl+K), holding Ctrl to snap to vertices.
- **Views** (OFF-01 pp. 88-91):
  - F2 perspective, F3 top, F4 front, F5 side, F6 **sun view**;
  - orthogonal projection recommended while building;
  - real-time shadows optional.
- **Large scenes**: *Use partial shading calculations* computes shading on a subset of tables and extrapolates it. It is not compatible with Module Layout (OFF-01 pp. 86-88).
- **Advice**: keep the scene simple. "It is advised not to get too detailed": detail lengthens every calculation (OFF-01 p. 62).

**Importing**
- **SketchUp** (OFF-06 pp. 3-14):
  1. Give the active face a material named e.g. "PVmodule".
  2. Make the module a **component**.
  3. Export COLLADA (DAE), which PVsyst prefers as an open format.
  4. In PVsyst: Near shadings > Construction/Perspective > File > Import > "Import a 3D scene (3DS, DAE, PVC)", and tick the PV material.
  5. DAE units default to **inches**: leave them, PVsyst converts.
  6. The imported scene is **reversed by 180°**: fix it by shifting the reference azimuth.
  7. Tick **"Deactivate verification of field interpenetration"**. The active surface was drawn 1 cm above the frame, while PVsyst wants 2-3 cm.
- **Archelios Pro**: the plug-in assigns materials itself. Area tolerance 8 % (OFF-06 p. 15).
- **PVcase Roof Mount**: export PVC, then "click directly on Near shadings without defining Orientation nor System" (OFF-06 pp. 26-29).
- **Orientations on import.** Since 8.0.15, an imported scene becomes **one averaged orientation** by default; an option re-enables automatic detection of several orientations (release notes 8.0.15). For domes, set the orientation type "East/West" in the import window (OFF-06 p. 44).
- **Arka360**: exports two .3ds files, imported **one at a time** (EN-21).
- **HelioScope**: multi-file DAE scenes import starting from the file ending "_0.dae" [unverified, EN-S4 snippet].
- **Drone photogrammetry** (Agisoft Metashape), then import: PT-10, PT-13. PT-13 had no floor plans and measured with drone photos and tape.
- **Calibration**: PT-12 matched PVsyst's shadow view to dated field photos to fix tree and building heights.
- **Other import walkthroughs**:
  - EN-37: SketchUp import, with a chapter on "Error resolution";
  - EN-36: urban 3D scenes;
  - PT-23: processing a 3D model, 2026;
  - ES-09: PVsyst with AutoCAD and SketchUp;
  - FR-10: SketchUp with the Skelion plug-in.
- **Split workflow**: IT-03 designed a condominium in SOLergo, with wind loads to NTC 2018, and used PVsyst only for shading on a 3D model of the building.

**Checks before simulating**
- The Near shadings dialog compares the orientations, module count and sensitive area of the scene with the system, within tolerance (OFF-01 pp. 62-63; OFF-13 p. 23).
- If the orientation differs, a button offers to correct Orientation from the scene (OFF-13 p. 23).
- In PVsyst 6.x, a tilt mismatch between Orientation and the 3D scene turned the Near Shadings button red and blocked the run [unverified, ZH-02].

**Values reported**
- Near-shading loss 0.6 % (ES-02), 1.5 % (PT-12), and 3.73 % together with IAM (PT-13).
- Concrete roof albedo 0.25-0.35 (ZH-17).
- Flat factory roof with modules at 0°: IAM plus soiling 7.57 % (TR-05); horizontal modules soil more (analysis from TR-05).

**Where users get stuck**
- The scene is built in an external CAD tool, then simplified and fixed after import: units, 180° rotation, interpenetration, area tolerance, one file per orientation for Virto.CAD (OFF-06).
- ES-01: "El uso de esta aplicación requiere un mayor conocimiento y tiempo que el resto de las simulaciones", comparable to AutoCAD.
- PT-18 on the "table zones" tool: "nem todas as suas ferramentas são intuitivas".
- Fire-code layout is not checked by PVsyst (VI-01: the Vietnamese rule of 40 × 40 m groups, 1.5 m gaps and 2.5 m from roof edges).
- Video `dQ4tr-zOW20` has chapters on "Orientation error handling" and "Compatibility and bugs".

**Meridiana.**

| Step | Status |
|---|---|
| Orthophoto, tracing, exclusions with setbacks, obstacles with heights by type | ✔ |
| VVF automatic layout (DCPREV 14030/2025) | ✔ |
| Diffuse shading | ✔ |
| Shading-factor table | ◐ (iso-shading diagram ○) |
| Import of DXF, DAE or PVCollada | ○ |
| Terrain and DSM | ○ |
| Object list editable as a table | not listed in funzionalita (analysis: missing) |

Sources:
- OFF-01, OFF-13 (above); OFF-06 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-export-3d-scene-to-pvsyst-en.pdf
- Release notes 8.0.15 https://www.pvsyst.com/help/release-notes/index.html
- EN-36 https://www.youtube.com/watch?v=hyVYoOch2Nc ; EN-37 https://www.youtube.com/watch?v=OszWwipCrV0
- PT-23 https://www.youtube.com/watch?v=3jffxf9ltq0
- ES-09 https://www.youtube.com/watch?v=ZrZAOuIjvhw
- FR-10 https://www.youtube.com/watch?v=q_u7Kclsfhc
- IT-03 https://amslaurea.unibo.it/id/eprint/27701/
- EN-21 https://help.arka360.com/en/articles/5916042-pvsyst-3d-scene-import (10/12/2025)
- EN-S4 https://help-center.helioscope.com/hc/en-us/articles/4465905757843-HelioScope-vs-PVsyst
- PT-10 https://canalsolar.com.br/modelagem-3d-com-drones-em-projetos-de-geracao-solar/
- PT-12 https://rbens.emnuvens.com.br/rbens/article/download/411/311
- PT-13 https://repositorio.ifpb.edu.br/bitstream/177683/4230/1/Dimensionamento%20de%20um%20sistema%20fotovoltaico%20utilizando%20PVSYST%20-%20Iury%20Matheus%20de%20Lira%20Ursulino.pdf
- PT-18 https://www.youtube.com/watch?v=Qyrukwut008
- ES-01 (above); ES-02 https://biblus.us.es/bibing/proyectos/abreproy/95141/fichero/TFG-5141+Garc%C3%ADa+Rosales+de+Salamanca.pdf
- ZH-02 https://www.candela.cn/1811/ ; ZH-17 https://www.candela.cn/2a62b8e371/
- TR-05 https://dergipark.org.tr/tr/download/article-file/2378166
- VI-01 https://datsolar.com/wp-content/uploads/2023/03/20230109_BV_TE_112_Phuong-phap-thiet-ke-he-thong-dien-mat-troi-ap-mai_V2.pdf
- Video https://www.youtube.com/watch?v=dQ4tr-zOW20

### 2.3 Ground-mounted fixed sheds (including terrain)

**Preliminary: "Unlimited sheds" orientation, a 2-D model** (OFF-01 pp. 19-20; video `-rI9jhMrH0U`, PVsyst 7)
- Inputs:
  - number of rows (the first row is unshaded);
  - collector band width (1 m in landscape, 1.5 m in portrait for a 1 × 1.5 m module);
  - top and bottom inactive bands;
  - pitch.
- PVsyst shows the **GCR** and the **limit angle**, plus partitions for the electrical effect.
- The video walks through the shed parameters, the shading graph, the tilt graph, and "Optimal configuration" (7:01).
- Chinese practice: row count matters with unlimited sheds (ZH-07). 2-D sheds or trackers cannot be combined with a 3D scene in the same variant (ZH-03, ZH-06).

**Detailed: 3D table rows or zones, plus terrain**
- **v8 satellite download** (OFF-05 pp. 3-6):
  1. In the 3D scene: File > Import > "Download a satellite ground image and/or ground data".
  2. The interactive Bing map is limited to about 11 km × 11 km.
  3. Tick "Also import topography data".
  4. Crop the image, and delete the ground object to see it (Ctrl+Z restores).
- **Google Earth route**, the pre-v8 method and still documented (OFF-05 pp. 8-12):
  1. Draw a Path, not a polygon, because a polygon gives only corner elevations.
  2. Save it as KML.
  3. Convert it on GPS Visualizer: plain text, semicolon, "Best available source" DEM, UTM output.
  4. In Excel, keep easting, northing and altitude.
  5. Save as CSV and import ground data (CSV).
  6. In the northern hemisphere, the ground may need a 180° rotation.
- **SketchUp terrain**: "Add Location", "Grab", unlock and explode, export DAE, then "Transform to a ground object" (OFF-05 pp. 13-15).
- **PVcase Ground Mount** (OFF-06 pp. 18-25):
  - export "FRAMES" (tables and objects) or "TERRAIN AND FRAMES";
  - PVC format for PVsyst 7 and later, DAE for 6.8 and earlier;
  - tables on terrain may be averaged into a single orientation.
- **Virto.CAD**: topography need not be exported because it does not affect shading; separate exports per orientation (OFF-06 pp. 32-34).
- **Base slope**: tables on sloped ground change their real tilt and azimuth. The "Orientation understanding" tool computes them (OFF-01 pp. 18, 73-74; video `eq9pU5QWtpc`).
- **Heavy terrain**: meshes above about 200,000 faces take hours to import. Simplified meshes can push tables into the ground; raise all arrays slightly [ZH-10, a vendor selling a simplification tool].
- **Modelling the ground** under the arrays changed one result by 1.4 % (ZH-18).
- **PVsyst 8 makes topography and ground images easier to import**, according to a Turkish "8.0 novelties" video, which frames ground-mounted design around the Turkish grid operator and regulator (TR-02).

**Pitch and tilt studies**
- *Optimization Tool*, under Advanced simulation (PT-01; video `CGou9LUYuB8`):
  - choose tilt, azimuth, and pitch (pitch is available only for fields of several tables);
  - set min, max and steps;
  - Run shows the estimated time.
  - Example: pitch 3-15 m on 18 tables, with mutual shading falling sharply from about 5 m.
- Rules of thumb used outside PVsyst:
  - IDAE formula d = h / tan(61° - latitude) (ES-01);
  - CRESESB chart, 2.8 m (PT-12);
  - Chinese GB 50797 rule of no shade from 9:00 to 15:00 at the winter solstice, relaxed on slopes (ZH-11);
  - Meridiana uses CEI 82-25/3 §6.2.

**Values seen**

| Source | Values |
|---|---|
| IT-02 | 2-in-portrait tables of 32 modules, tilt 25°, pitch 4.5 m: yield 1449 kWh/kWp, PR 87.5 % (bifacial, Marche) |
| IT-01 | 30° at Bologna, pitch 6 m, height 2.1 m |
| AR-04 | 25°, pitch 8 m, 2-high portrait |
| ZH-19 | Strings routed row by row gain 0.35 % over C-shaped routing |

**Meridiana.**

| Step | Status |
|---|---|
| Rows with 2-D mutual shading, GCR, limit angle, CEI pitch | ✔ |
| Tables following the terrain | ○ |
| Tilt optimisation | ○ |
| Terrain, LIDAR, DSM | ○ |
| Orthophoto | ✔ (2012 national; recent regional ○) |

Sources:
- OFF-01 (above); OFF-05 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-import-topography-en.pdf ; OFF-06 (above)
- Videos https://www.youtube.com/watch?v=-rI9jhMrH0U , https://www.youtube.com/watch?v=eq9pU5QWtpc , https://www.youtube.com/watch?v=CGou9LUYuB8
- PT-01 https://canalsolar.com.br/tutorial-pvsyst-mapeamento-de-geracao-e-ferramenta-de-otimizacao/ ; PT-12 (above)
- ES-01 (above)
- ZH-03 https://www.candela.cn/pvsyst%e5%ae%9e%e7%94%a8%e9%97%ae%e7%ad%94%e4%bd%a0%e6%83%b3%e7%9f%a5%e9%81%93%e7%9a%84%e9%83%bd%e5%9c%a8%e8%bf%99%e9%87%8c%ef%bc%88%e7%ac%ac12%e6%9c%9f%ef%bc%89/ ; ZH-06 https://www.candela.cn/8685107e42/ ; ZH-07 https://www.candela.cn/2163707e7c/ ; ZH-10 https://www.candela.cn/%e8%87%aa%e5%8a%a8%e7%ae%80%e5%8c%96%e5%b1%b1%e4%bd%93%ef%bc%8c%e6%8f%90%e9%ab%98pvsyst%e5%9c%b0%e5%bd%a2%e5%af%bc%e5%85%a5%e9%80%9f%e5%ba%a6/ ; ZH-11 https://www.candela.cn/8a803f6ae3/ ; ZH-18 https://www.candela.cn/db20b789b0/ ; ZH-19 https://www.candela.cn/f9eb573f36/
- IT-01 https://amslaurea.unibo.it/id/eprint/38565/1/Tesi_Giuseppe_Bentivenga.pdf ; IT-02 https://tesi.univpm.it/bitstream/20.500.12075/20942/1/Tesi%20Alanis%20Casaccia.pdf
- AR-04 https://www.youtube.com/watch?v=P0KxNIVKx4w
- TR-02 https://www.youtube.com/channel/UCwjwdjwrB9v6HJosootldbg/videos

### 2.4 Single-axis trackers and backtracking

**Sequence** (OFF-01 pp. 20-22, 76-78, 84-86; videos `wgP9wrFVHkE`, `fZB2qAW8_qo` at 5:58)
1. **Orientation.**
   - "Unlimited trackers, horizontal axis" for 2-D parametric studies.
   - Or "Tracking, horizontal and tilted axis". Here "the construction in the 3D scene is mandatory" to compute mutual shading (OFF-01 p. 21).
2. **Inputs.**
   - Axis azimuth: 0 = N-S axis.
   - Phi min and max: the mechanical stroke.
   - Backtracking on or off.
   - Tracking mode: astronomic or *irradiance optimisation*, which maximises GlobInc.
   - Wind stow.
   - Electrical-shading parameters, visible only when backtracking is **off**.
   - "Drag the sun" animation to see the behaviour (OFF-01 pp. 20-21).
3. **3D.**
   - Create > Tracker row, or a zone with "Create Trackers".
   - Or Transform > "Convert Fixed Tables to Trackers" (OFF-01 pp. 72-73).
4. **Backtracking management**, needed for imported scenes and zones (OFF-01 pp. 84-86):
   - Automatic mode: picks the **highest GCR** in the scene.
   - Manual mode: pick another reference pair. Trackers with a higher GCR turn red, with a warning.
   - Custom values for the angle calculation only:
     - halve the width to emulate **half-backtracking**;
     - one-sided inactive bands for different morning and afternoon behaviour on slopes;
     - validate the result with the shading animation.
5. **Tracker diffuse shading** (Tools) (OFF-01 pp. 76-78):
   - *All trackers*: most accurate and slowest;
   - *Central tracker*: green, with its orange shading mask;
   - *Custom tracker*.
   - A badly chosen representative tracker gives an error of order 1/N rows.

**Values seen**

| Source | GCR | Rotation range | Other |
|---|---|---|---|
| IT-04, IT-05, IT-06 (Italian utility VIA reports) | 44.6-53.2 % | ±55° to ±60° | Backtracking limits ±57.6° to ±63.4°; pitch 5.0-9.4 m; widths 2.26-5.00 m |
| ZH-20 (Qinghai, PVsyst 6.70) | n/a | ±45° | Pitch 8 m |
| EN-11 [unverified] | 0.30-0.50; LCOE optimum about 0.35-0.42 | n/a | Bifacial 0.28-0.35 |

Tracking gain:
- 10-50 % (EN-28, PVsyst staff deck, 2017);
- about +15 % (PT-03) and +28.1 % (PT-28) [unverified];
- +26-33 % for a Hamburg micro case (DE-02).

**Where users get stuck**
- **"Linear" shading misleads the choice of strategy.** In ZH-13 (Candela, 4 Jun 2021):

  | Mode | Normal tracking | Backtracking |
  |---|---|---|
  | Linear shading | 1320.7 MWh | 1317.5 MWh |
  | According to strings | 1300.3 MWh | 1317.5 MWh |

  Compare strategies with electrical shading on.
- **Missing backtracking goes unnoticed.** IT-04 (51.7 MWp agrivoltaic, PVsyst 7.4.5) shows GCR 53.2 % and "Phi limits for BT ±57.6°", but no "Backtracking activated" line and a -11.32 % near-shading loss. (analysis) Backtracking was probably off, and nothing in the report flags it.
- **No backtracking:**
  - on mountain terrain (ZH-07);
  - for vertical-axis trackers (EN-28; DE-01 calls the algorithm "noch nicht ausgereift").
- **Slopes and variable pitch** make backtracking inefficient (EN-11; OFF-01 p. 86 offers the inactive-band trick).
- **Large tracker plants** need representative-tracker approximations for diffuse shading (OFF-01 pp. 76-78).
- **Imported tracker scenes.** RatedPower's guide: enable backtracking under Tools, set the string partition, and press "Update orientation parameters" after importing a PVCollada tracker scene [unverified, EN-S2 snippet].
- **Other tracker walkthroughs**: EN-38 (tracker with bifacial modules "in 20 minutes", PVsyst 7); EN-43 (single-axis tracking); DE-06 (backtracking for bifacial single-axis trackers and 90° bifacial rows) [unverified, snippet only].

**Meridiana.** Single-axis trackers with backtracking, also on slopes: ○ (phase 2; pvlib has them).

Sources:
- OFF-01 (above)
- Videos https://www.youtube.com/watch?v=wgP9wrFVHkE , https://www.youtube.com/watch?v=fZB2qAW8_qo
- IT-04 https://va.mite.gov.it/File/Documento/982964 ; IT-05 https://va.mite.gov.it/File/Documento/806253 ; IT-06 https://va.mite.gov.it/File/Documento/823985
- ZH-07 (above); ZH-13 https://www.candela.cn/746d5cddf9/ ; ZH-20 https://www.candela.cn/0939b35c99/
- EN-11 https://www.surgepv.com/blog/solar-backtracking ; EN-28 https://pvpmc.sandia.gov/download/4301
- DE-01 https://reposit.haw-hamburg.de/bitstream/20.500.12738/9114/1/SteffensElena_geschwaerzt.pdf ; DE-02 https://reposit.haw-hamburg.de/bitstream/20.500.12738/17072/1/BA_Sonnennachf%C3%BChrung%20von%20PV-Modulen.pdf
- PT-03 https://canalsolar.com.br/modelagem-e-simulacao-de-uma-usina-solar-com-modulo-bifaciais/ ; PT-28 https://abmproceedings.com.br/en/article/otimizao-de-um-sistema-fotovoltaico-utilizando-software-pvsyst
- EN-S2 https://knowledgebase.ratedpower.com/how-to-upload-a-pvcollada-tracker-scene-to-pvsyst ; EN-38 https://www.youtube.com/watch?v=x-LRzh9f6pg ; EN-43 https://www.youtube.com/watch?v=XFyOl67l6us
- DE-06 https://digitalcollection.zhaw.ch/items/2883b270-d55f-4c33-8b15-d06032fad941

### 2.5 Bifacial

**Sequence** (videos BTS001-006, PVsyst 7, May 2024; PT-02; ZH-05; EN-05)
1. **Module.** The PAN must be bifacial: tick "Bi-facial module" in *Size and technology* and enter the bifaciality factor (ZH-01). Since 8.0.12 the default upper limit is 98 % (06).
2. **System, Bifacial system.**
   - Choose "Unlimited sheds 2D" for fixed rows or "Unlimited trackers 2D" for trackers.
   - Enter:
     - ground albedo, yearly or monthly; since 8.1.2 also as a CSV time series (release notes 8.1.2);
     - height above ground: the lowest module edge for fixed racks, the axis for trackers (ZH-05);
     - structure transparency;
     - structure shading;
     - rear mismatch (PT-02, EN-05).
3. **3D conditions.** The 2-D model is used with a 3D scene only under conditions on the rows (video `_rmEpN-FlWQ` "Bifacial model conditions for 3D scene").
   - Domes "not suited for bi-facial systems" (OFF-01 p. 19).
   - PVsyst refuses bifacial on domed east-west arrays; the workaround is two fixed orientations (EN-34, PVsyst 8.1, 2026).
4. **Results.** BTS004 covers the educational tools (profile angle and its limit); BTS005 covers the results. The bifacial gain is obtained as the bifacial run minus a monofacial run (ZH-07).

**Values**

| Parameter | Values seen | Sources |
|---|---|---|
| Bifaciality | PERC 0.6-0.7 and n-type 0.7-0.9, with about 10 points of drift between batches; PERC 0.7-0.8 and HJT about 0.9; 0.70; 0.85 | EN-06; IT-02; PT-03; ZH-20 |
| Height | 0.5-1.5 m; 1 m; 1.5 m | PT-02; PT-03; ZH-20 |
| Ground albedo | Sand or gravel 30-35 % [unverified]; one-year measurements of white surface 55.6 %, gravel 29.5 %, grass 19.9 %, with bifacial gains of 15.7 %, 9.6 % and 7.3 % | PT-02; EN-07 (Soltec) |
| Structure shading | 8.1 % for a 2-in-portrait tracker; 27.4 % for a 4-in-landscape fixed rack. By element: torque tube 5.6 %, rails 4.9 %, frame 2.8 %, posts 1.0 % | EN-05 (PV Lighthouse ray tracing, PVsyst 7.4.6) |
| Rear mismatch | Usually below 0.2 % of the annual yield; the formula changed in 7.4.6. Other values: 10 % (ZH-20, 2018) [unverified]; 3 % scaled by the rear/front ratio (IT-04 narrative) | EN-05 |
| Realistic gain on trackers | 4-10 % with albedo 30 % and bifaciality 65 % | EN-06 |
| PVsyst against Bifacial PUB, same plant | +4.65 % against +8.42 % [unverified] | PT-03 |

**Where users get stuck**
- **Unmeasurable factors.** fA, fT, fS and the rear mismatch fMR need ray tracing or guesses (EN-05). Albedo is "the biggest source of uncertainty for bifacial gain" (EN-06).
- **PR_Bifi changed in 8.0.12.** It now includes the bifaciality factor (release notes 8.0.12). On a 99 MWp plant, 93.56 % becomes 87.89 % (ZH-08, 22 May 2025). Reports before and after 8.0.12 are not comparable.
- **No east-west or dome bifacial, no use of the real 3D scene** for the rear side (06 §1.1.3).
- **Pitch** [unverified, PT-02]: about 12 m is recommended for bifacial, against 5-7 m for monofacial.
- **Rear gain cannot be computed by multiplying the factors.** In one case the correct rear gain was 11.82 %, against 17.69 % from simple multiplication (ZH-22).
- **Finite rows.** The effect of finite row length must be added by hand as extra mismatch (EN-08).
- **DC/AC rule.** Bifacial DC/AC = monofacial ratio / (1 + bifacial gain), with the nameplate counting the front side only (EN-08).
- **Vendor webinar.** Huawei's bifacial webinar with a Greek engineering firm (EN-39).

**Meridiana.** 2-D bifacial model ○ (phase 2); bifacial on the 3D scene ○ (phase 3).

Sources:
- Videos https://www.youtube.com/watch?v=BLizHdUIOCI , https://www.youtube.com/watch?v=XkPGYnzjAFE , https://www.youtube.com/watch?v=wgP9wrFVHkE , https://www.youtube.com/watch?v=AfyjhCMhw4A , https://www.youtube.com/watch?v=_l-va15JR0g , https://www.youtube.com/watch?v=_rmEpN-FlWQ
- OFF-01 (above); release notes https://www.pvsyst.com/help/release-notes/index.html (8.0.12, 8.1.2)
- PT-02 https://canalsolar.com.br/modulos-bifaciais-com-pvsyst-fatores-a-considerar/ ; PT-03 (above)
- EN-05 https://downloads.pvlighthouse.com.au/white-papers/pvsyst-factors/Info0030%20-%20Extracting%20PVSyst%20inputs%20with%20SunSolve.pdf
- EN-06 https://www.firstsolar.com/-/media/First-Solar/Technical-Documents/Bifacial-Documents/CSA_Performance-Modeling-and-Testing-of-Bifacial-PV-Systems_Kyumin-Lee.ashx?la=en
- EN-07 https://www.pv-magazine-india.com/2020/01/25/the-long-read-all-about-albedo/
- EN-34 https://www.youtube.com/watch?v=5hPAfHoWKpU
- EN-08 https://www.pv-magazine.com/2019/11/27/webinar-qa-performance-modelling-for-accurate-energy-output-and-yield-prediction-of-bifacial-pv-systems/ ; EN-39 https://www.youtube.com/watch?v=Pk2OC6gF890
- ZH-22 https://www.candela.cn/7b95cf6909/
- ZH-01 https://www.candela.cn/pvsyst%E8%BD%AF%E4%BB%B6%E4%BD%BF%E7%94%A8%E7%AD%94%E7%96%91%E7%AC%AC%E4%BA%8C%E6%9C%9F/ ; ZH-05 https://www.candela.cn/13887363c5/ ; ZH-07 (above) ; ZH-08 https://www.candela.cn/8-0%e7%89%88pvsyst%e5%85%b3%e4%ba%8e%e5%8f%8c%e9%9d%a2%e7%b3%bb%e7%bb%9f%e6%95%88%e7%8e%87%e7%9a%84%e4%bf%ae%e6%ad%a3%e8%af%b4%e6%98%8e/ ; ZH-20 (above)
- IT-02, IT-04 (above)

### 2.6 East-west and domes

**Sequence**
- **Domes** (OFF-01 p. 19):
  - choosing the "Domes" field type creates the opposite orientation automatically;
  - Uc 27 W/m²K, measured by a manufacturer 40-70 cm above the ground (OFF-01 p. 31);
  - not suited for bifacial.
- **Importing domes.** In the import result window, set the PV objects' orientation type to "East/West". PVsyst then creates two orientations and fills them, which can be checked in *Orientation management* (Ctrl+Shift+O), colour-coded per orientation (OFF-06 pp. 42-48; OFF-01 pp. 81-83).
- **Without domes.** Define two orientations, e.g. 10° east and 10° west on a flat roof without a 3D scene (DE-03). Other names for the same: "Several orientations" (ES-01) and "Mixed #1 and #2" for symmetric roof faces (VI-02).
- **Same inverter input.** Mixed orientations on the same input are allowed in PVsyst 8, and the mismatch shows in the loss diagram (OFF-01 p. 26). "Multi-orientation daily sharing" is in video `6QpgYVrLZus` (6:44). PVsyst still "explicitly prevents" several orientations **within one string** (OFF-01 p. 26).

**Values**
- Porto Alegre: east and west faces at 15° give about 7 % less than facing north [unverified, PT-07].
- An east-west layout was chosen to avoid row spacing and to match self-consumption (DE-03).

**Meridiana.** East-west pairs ✔ (each side a field of its own). Two orientations on the same MPPT ○.

Sources:
- OFF-01, OFF-06 (above)
- DE-03 https://reposit.haw-hamburg.de/bitstream/20.500.12738/14545/1/BA_J%C3%B6rck_geschw%C3%A4rzt.pdf
- ES-01, VI-02 (above)
- PT-07 https://canalsolar.com.br/paineis-solares-orientados-norte/
- Video https://www.youtube.com/watch?v=6QpgYVrLZus

### 2.7 Carport

No tutorial in any language teaches a carport as such. PVsyst has no carport object.

**Practice found**
- Carports are modelled as tilted tables or rectangular PV planes on posts. Examples:
  - a 10° carport sub-field next to a 45° roof, at Jaén (ES-01, exercise 4);
  - three parking carports at 10°, with two-slope faces at 60° and -112° azimuth (ES-02, an 820 kWp self-consumption plant without export).
- **Bifacial.** 06 notes that PVsyst calls carports the exception where east-west or dome-type structures receive rear light, but does not model it (06 §1.1.3).

**Gaps.** None of the following is taught:
- post shading;
- edge effects for bifacial carports;
- clearance and height rules;
- carports for EV charging with load profiles.

**Meridiana.** Carport mounting ✔ (montaggio "pensilina").

Sources: ES-01, ES-02 (above); 06 §1.1.3.

### 2.8 Agrivoltaics

**Practice found**
- **Italian permitting reports** model agrivoltaic plants as ordinary trackers with a standard loss set (IT-04 Favara 51.7 MWp; IT-07 Ramacca, about 25 MW). Nothing agrivoltaic-specific enters the PVsyst model:
  - no crop shading;
  - no minimum height;
  - none of the indices of the Italian ministry (MASE) 2022 guidelines.
- **Ground irradiance.** PVsyst has no ground or crop irradiance output. The published workaround (EN-22, arXiv 2022):
  1. Place a horizontal PV "receiver" plane at crop height.
  2. Convert the real arrays into shading objects.
  3. For trackers, rebuild the scene for each hour.

  It matched the authors' own model with R² ≥ 0.9998.
- **Other material.** A Chinese paid book and course list agrivoltaics in their contents only (ZH-24, ZH-25).

**Meridiana** (analysis).
- Not in funzionalita.md.
- A crop-level irradiance map on the 3D ground, with the MASE 2022 indices, would be unique among the tools surveyed.
- The building blocks are partly in place: the shading engine and the 3D scene. Missing: tracker geometry, and irradiance on arbitrary surfaces.

Sources:
- IT-04, IT-07 https://va.mite.gov.it/File/Documento/896146
- EN-22 https://arxiv.org/abs/2208.04886
- ZH-24 https://www.candela.cn/e05aaf02c3/ ; ZH-25 https://www.candela.cn/pvsyst%E5%85%A8%E5%A5%97%E5%9F%B9%E8%AE%AD%E8%A7%86%E9%A2%91/

### 2.9 Self-consumption and storage

**Self-consumption: entering the load** (OFF-01 p. 48; OFF-08 pp. 7-9; videos `-PGRnnF1VuA`, `8im2MnQQjvw`)

Options:
- fixed constant consumption (power or yearly energy);
- **monthly values**, constant within each month;
- **daily profiles**: constant over the year, seasonal, monthly, or weekly (working days and weekend);
- **probability profiles**;
- **household appliances**: unit power × hours per day;
- **CSV hourly or daily file**, from a template that can be rescaled, or from the user's own file.

Rules for the CSV (OFF-01 p. 48):

| Rule | Value |
|---|---|
| Column 1 | Date with day, month, year, hour and minute |
| Column 2 | Load, with its unit written in row 2 |
| Separator | Semicolons |
| Time step | Sub-hourly values are converted to hourly |
| Calendar | A **365-day year**: a leap year "may cause errors" |

**Storage** (OFF-01 pp. 49-59)
1. **Choose the strategy:**
   - self-consumption;
   - power shifting (8.0.17);
   - peak shaving, which **requires** a self-consumption profile;
   - weak grid.
2. **Battery pack.** Pick the model and set the count in series and in parallel.
   - Initial state of wear, by cycles and static, both 100 % when new.
   - Initial state of charge, e.g. 50 %.
   - Operating temperature: +10 °C halves the "static" life.
   - The panel then shows the pack voltage, C10 capacity, energy at 80 % depth of discharge, weight, cycles at 50 % depth of discharge, and lifetime energy.
3. **Self-consumption with storage** (OFF-01 pp. 51-52):
   - charging stops at a state of charge of 95 % and discharging at 20 %;
   - PVsyst proposes the charger power from the clear-sky surplus;
   - a full lithium-ion charge in 1 hour is "the minimum reasonable";
   - discharge power is set from the load;
   - injecting the surplus into the grid can be allowed or forbidden.
4. **Power shifting** (OFF-01 pp. 52-55):
   - Charging, on a daily or hourly plan: a fraction of PV (applied to EArray), a fixed charging power, or a fixed export with the surplus going to the battery.
   - Discharging: at specified hours, or during the night.
   - Sizing rules:
     - daily discharge ≥ charge;
     - capacity ≤ the maximum daily charge;
     - charger and battery-inverter power above their target, because of losses.
   - Grid limits must be set at the injection point.
   - It "does not yet handle self-consumption".
5. **Peak shaving** (OFF-01 pp. 55-58):
   - set a grid limit below the clear-sky maximum PV power;
   - charger power = maximum PV power minus the limit;
   - the battery inverter may be smaller;
   - discharge "as soon as power is needed", after sunset, from a given hour, or within a period.
6. **Weak grid** (OFF-01 pp. 58-59): an unavailability schedule, random or from CSV. The capacity should cover the longest outage.

**Values.**

| Source | Values |
|---|---|
| ZH-12 (Candela, 9 Sep 2021) | 280 MWh/yr load, 367 kWp PV, 1138 kWh LFP battery on the AC side, monthly load, discharge to 20 % state of charge. Self-consumption 29 % → 65.8 %. No tariff-driven strategy in 2021. |
| ES-06 (MPV Solar Reference, PVsyst 8, Mar 2026) | Strategies covered: self-consumption with and without battery, zero injection, peak shaving, load shifting by time bands, Sankey sizing. |

**Where users get stuck**
- **CSV format errors.** ES-06 formats the load file (Date, P_Load, kW) "para que PVsyst no dé error".
- **Contradictory CSV rules.** EN-15 (AmpX, PVsyst 8) says: hourly steps, no gaps, decimal points, **no header**, a full year. That contradicts OFF-01, which wants the unit in row 2 [unverified, possibly a different template]. Loggers that record kVA instead of kW are a further trap.
- **Self-consumption rate.** PVsyst's table gives energies, and users compute the rate by hand (E_User / E_Avail) (EN-15).
- **All-in-one hybrid units** cannot be entered as such. The workaround is an .OND for the inverter plus a .BTR for the battery, built from the datasheet: "se atraganta con el almacenamiento moderno" (ES-06).
- **Price-based dispatch** for the Italian market: an MSc thesis rejected PVsyst's approach, "si è ritenuto che l'approccio adottato da PVsyst non fosse idoneo per effettuare un'analisi coerente" (IT-01, p. 41). Users size storage in their own Python or Excel tools (IT-01, DE-03).
- **Load entry methods.** AR-01 shows five ways to enter the load:
  - annual;
  - constant;
  - monthly from bills;
  - daily from appliances;
  - CSV.

**Meridiana.**

| Step | Status |
|---|---|
| POD data; ARERA F1/F2/F3 bands | ✔ |
| Measured curves (15-min or hourly, kW or kWh) | ✔ |
| Bills; ten profiles; automatic profile while data are missing | ✔ |
| Hourly self-consumption | ✔ |
| Storage from the catalogue | ✔ |
| Battery ageing | ○ |
| DC coupling | ○ |
| Zero export with battery, peak shaving, time-band discharge | ○ |

Sources:
- OFF-01 (above); OFF-08 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-stand-alone-en.pdf
- Videos https://www.youtube.com/watch?v=-PGRnnF1VuA , https://www.youtube.com/watch?v=Eq5ZC_un4UA , https://www.youtube.com/watch?v=49d5pAV907Y , https://www.youtube.com/watch?v=jZKdz248WJQ , https://www.youtube.com/watch?v=VHo-d-PFDlE
- ZH-12 https://www.candela.cn/6eb925db4b/
- ES-06 https://www.youtube.com/watch?v=q-WAWI8H6Vs , https://www.youtube.com/watch?v=O6nV7cJ9TpY
- EN-15 https://ampx.co/solar-self-consumption-analysis/
- IT-01 (above)
- DE-03 (above)
- AR-01 https://www.youtube.com/watch?v=VvwgbohIX9g

### 2.10 Grid power-injection limit

**Sequence**: Energy management > Grid power limitation (OFF-01 pp. 45-46; 06 §1.1.9.9).
1. Enter one value for the year (a CSV time series since 8.1.0, per 06).
2. Choose where the limit applies:
   - at the **inverter**: the injected power is further reduced by the losses after the inverter;
   - at the **injection point**: the inverter delivers more to compensate those losses.
3. Express it in **kW** (active) or **kVA** (apparent, with a yearly or monthly cos φ for the limit).
4. Optionally tick "Account as separate loss": the part due to the limit is then reported separately as EUnused or EGridLim.

With batteries, the limit must be set at the injection point (OFF-01 p. 55).

**Example: IT-05**, Calapricello, 70.48 MWp with trackers, annex printed by PVsyst 7.2.16:
- Grid power limit 65.80 MWac on 70.00 MWac of inverters ("Grid lim. Pnom ratio 1.071").
- The loss diagram shows 0.00 % for the export limit, with DC/AC 1.08.
- The variant name ends in "Limitazione".

**Other sources**
- Spanish zero-export self-consumption under RD 244/2019, with an anti-export device (ES-02); the PVsyst setting itself is not shown.
- The grid-injection limitation chapter of the PVPMC 2023 talk (video `el2T4stALT8` at 10:38).

**Meridiana.** Export limit at the connection point ✔, including zero export; clipped energy in the balance ✔. kVA limit with cos φ: ○ (power factor ○).

Sources:
- OFF-01 (above)
- IT-05 https://va.mite.gov.it/File/Documento/806253
- ES-02 (above)
- Video https://www.youtube.com/watch?v=el2T4stALT8

### 2.11 Horizon import

**Sequence** (OFF-01 pp. 60-61; OFF-02 pp. 40-42; OFF-12 pp. 20-22; video `dHBGsOrGw5o`)
1. Horizon button: the sun-path diagram opens.
2. **Draw by hand:**
   - drag the points;
   - right-click to add or delete a point;
   - or type azimuth and height in the table.
   - "Clear horizon" starts over.
   - Save the result as a .HOR file for reuse.
3. **Or import:**
   - a .HOR file;
   - a CSV of azimuth and height, setting the north reference and the direction of rotation;
   - a Meteonorm horizon (its file name carries the coordinates);
   - "PVGIS Horizon From WEB" or the Meteonorm web service: one click, internet needed.
4. Older instruments and programs (OFF-12 p. 21):
   - Solmetric SunEye: use `ObstructionElevation.csv`, not the obsolete `.hor`;
   - Carnaval: rename `*.masque.txt`, because two dots are refused;
   - Horiz'ON photo panoramas.

**Rules**
- Far obstacles only: at least **10 times** the PV field size away. Example: a 20 m field needs obstacles beyond 200 m (OFF-01 p. 60).
- For large plants, model the terrain in 3D instead (OFF-01 p. 60).
- The Horizon LED turns green when a point exceeds 2° (OFF-01 p. 60).
- Check the coordinates: 0.0001° is about 11 m, which "can significantly affect the horizon in uneven terrain" (OFF-01 p. 61).
- When the sun is below the horizon, beam is zero, so near shading adds nothing on beam at that moment. Diffuse is reduced only slightly (OFF-13 p. 28).

**Practice**

| Source | Practice |
|---|---|
| IT-04 | PVGIS 5 horizon: mean 2.6°, max 5°, 276 h/yr blocked, -0.45 % |
| AR-01 | PVGIS horizon import |
| EN-01 | Solargis .HOR via Horizon > Read/Import > "Horizon software" |
| DE-01 | Horizon copied from an earlier yield report |
| DE-05 (2015 forum) | PVsyst's horizon loss is lower than the same obstacle drawn as a 3D wall |
| ZH-06 | Terrain farther than about 10 times the array diameter must go in the horizon, or far shading reads 0 % |

**Meridiana.** PVGIS horizon ✔, applied to direct and diffuse ✔. Manual drawing, CSV import and SunEye import are not listed in funzionalita (analysis: missing).

Sources:
- OFF-01, OFF-02, OFF-12, OFF-13 (above)
- Video https://www.youtube.com/watch?v=dHBGsOrGw5o
- IT-04 (above); AR-01 https://www.youtube.com/watch?v=-PdCTtYueAM
- EN-01 https://kb.solargis.com/docs/solargis-data-in-pvsyst (16/07/2026)
- DE-01 (above); DE-05 https://www.photovoltaikforum.com/thread/104958-abweichende-prognosen-mit-pvgis-pvsyst-pv-sol-bei-schatten/
- ZH-06 (above)

### 2.12 Weather import (PVGIS, Meteonorm, Solargis, NASA POWER, others)

**Routes in PVsyst 8.1**
1. **At site creation**, from the provider list (2.0, step 3).
   - Meteonorm is synthetic, built from monthly averages. TMY files are hourly, built from at least 10 years (OFF-01 p. 16).
   - The interannual variability of GHI is shown for some sources and feeds P50/P90 (OFF-01 p. 16).
2. **Databases > Known format**: predefined formats such as Solargis, Vaisala, PVsyst standard CSV and Solcast.
   - Press F1 and "Information for importing", then follow the red messages (OFF-03 p. 16).
   - **PVGIS**: choose coordinates, then Import. This gives a 10+ year hourly series, one .MET per year. "Save Site" stores the monthly average, and "Synthetic gen." makes an averaged synthetic year (OFF-03 pp. 16-18).
3. **Databases > Custom file**, the "Conversion of custom (sub-)hourly weather files" dialog (OFF-03 pp. 19-26). This is the legacy conversion with .MEF format files. It stayed reachable from the 8.1 assistant until release 8.1.6, which "removed the legacy import from the assistant" (release notes 8.1.6). OFF-03 still teaches it.
   1. Choose the file and the site.
   2. Name the file: you "will not be able to change it after conversion".
   3. Create a format (.MEF):
      - *General*: (sub)hourly with the step, separator, number of header lines to skip;
      - *Date format*: "Dates read on the file" is preferred. "Reference year" and "Sequential dates" are fragile, because a missing line shifts every following one;
      - date pattern, e.g. `DD/MM/YY/hh/mm`, and whether the label marks the end or the start of the interval;
      - *Variables*: column numbers, a multiplier for units, and the plane orientation for POA data.
   4. Start Conversion.
   5. Check the result.
4. **8.1 import assistant**: Databases > "Import a custom file" (OFF-01 p. 9).
   - PT-14 order: file, site and coordinates, date and time format, column mapping (irradiance, temperature, wind), checks, create.
   - The 2026 webinars give it about 11 minutes each (`Dtqv8sMczrs` 3:33-14:28; `Xz4f-pq1CzE` 3:44-16:04).

**Quality control taught** (OFF-03 pp. 12-15, 24, 27-28)
- In PVsyst, an hourly value represents **the hour that follows** its time stamp. End-of-interval or mid-interval labels therefore cause a time shift.
- Hourly plot against the clear-sky line: the data must not be shifted towards morning or evening.
- Daily points must not exceed the clear-sky envelope "significantly (more than 3-5%)".
- *Check data quality* tab:
  - the estimated time shift should be about 0;
  - morning and afternoon clearness clouds should overlap;
  - "Monthly best clear days" should match the clear-sky curve;
  - the sorted Ktcs of the best days should be within 5 % of 1, as a sensor-calibration check.
- Synthetic files:
  - the "Region topology" options differ very little, so when unsure keep the default "Swiss Plateau, land, important mist";
  - two generations differ by 0.5-1 % in yearly results (OFF-03 pp. 10-11).
- Meteonorm hourly tables cannot be exported (OFF-14).

**Vendor-specific traps**

| Source | Trap |
|---|---|
| EN-01, Solargis (16/07/2026) | Known format "Solargis (Worldwide)" gives one hourly year per .MET. "Unrecognized file" appears if the wrong format is picked. Older versions need local-time (LTZ) files. Tropical sites can exceed PVsyst's clearness or diffuse limits: edit them under Preferences > Edit hidden parameters. A series starting in July must be edited first. The page warns it "may be outdated". |
| EN-02, Solcast (PVsyst 7.4) | The built-in "Solcast TMY" needs a commercial-tier account (errors "403 Invalid Role"). Otherwise use the PVsyst standard format. "This file is not a valid PVsyst Standard weather data file" appears when GHI is missing. |
| EN-03 and EN-04, Vaisala | Known format "Vaisala (Worldwide)". For time series: create the site, type its monthly values yourself (the Meteonorm or NASA values fetched by "Import" are called "incorrect"), then import with the ASCII protocol. One year at a time. |
| ZH-07, ZH-05 | After changing the source, recreate the .SIT and regenerate the .MET. Site altitude matters. |
| ZH-03 | The value labelled 10:00 covers 10:00-11:00. |
| PT-14 | PVGIS TMY and multi-year series fetched with **pvlib** outside PVsyst, then imported. |
| FR-01 (PVsyst 6) | PVGIS monthly values pasted from the clipboard, then synthetic hours. Now obsolete. |

**Which data independent engineers accept**: NSRDB and Meteonorm for preliminary studies only; SolarAnywhere at about $500 per site [unverified, EN-10].

**What practitioners use**
- Most permitting reports in Italy use PVGIS TMY (IT-04, IT-05) or Meteonorm (IT-06, IT-07).
- Some Italian VIA studies skip PVsyst altogether and compute yield with PVGIS plus a manual bifacial uplift (IT-09).
- TR-04 matched measured energy within 0.203 % with PVGIS inside PVsyst [single plant].
- Other walkthroughs:
  - EN-41: NASA and PVGIS import, PVsyst 7.0;
  - FR-06: PVsyst 7.1, "une dizaine de sources différentes ainsi que des données personnelles";
  - EN-37: choosing the weather database.

**Meridiana.**

| Step | Status |
|---|---|
| PVGIS 5.3 TMY with cache | ✔ |
| Time conventions | ✔ |
| Weather tables and graphs | ◐ |
| Other formats and import assistant | ○ |
| Quality control and gap filling | ○ |
| Multi-year series | ○ |
| Paid APIs | ○ (phase 3) |

Sources:
- OFF-01 (above); OFF-03 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-meteorological-data-en.pdf ; OFF-14 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-7/pvsyst-tutorial-v7-grid-connected-3-en.pdf
- Release notes 8.1.6 https://www.pvsyst.com/help/release-notes/index.html
- Videos https://www.youtube.com/watch?v=Dtqv8sMczrs , https://www.youtube.com/watch?v=Xz4f-pq1CzE , https://www.youtube.com/watch?v=W19FmnUzrkE
- EN-01 (above); EN-02 https://kb.solcast.com.au/pvsyst ; EN-03 https://energy.vaisala.com/en/support/solar-online-tools/how-do-i-input-csv-files-pvsyst ; EN-04 https://a2.energy.vaisala.com/en/support/solar-online-tools/how-can-i-input-time-series-data-pvsyst/ ; EN-10 https://www.buzzsprout.com/1361503/episodes
- PT-14 https://www.youtube.com/watch?v=oNN2ggOsvtk , https://www.youtube.com/watch?v=5bHYaiRr3HU
- ZH-03, ZH-05, ZH-07 (above)
- TR-04 https://dergipark.org.tr/tr/download/article-file/3874951
- FR-01 (above); FR-06 https://www.youtube.com/watch?v=TYRAoZKMAfQ
- IT-09 https://va.mite.gov.it/File/Documento/593419 ; IT-04, IT-05, IT-06, IT-07 (above)
- EN-37 https://www.youtube.com/watch?v=kTe6FizXb8A ; EN-41 https://www.youtube.com/watch?v=elwW9ehCyT8

### 2.13 Batch simulation and parametric studies

**Tools, from quick to automated**
1. **Orientation chart**: the tilt and azimuth optimum at a glance (OFF-01 p. 18). Unlimited sheds have their own "Optimal configuration" step (video `-rI9jhMrH0U`).
2. **Optimization Tool**, under Advanced simulation (PT-01; videos `CGou9LUYuB8`, `CsizS99dwho`):
   - pick the parameters (tilt, azimuth, pitch), their min, max and steps;
   - Run shows the estimated duration;
   - results come as tables and maps.
   - PT-07 ran 5,365 combinations for 5 Brazilian cities.
3. **Batch simulations** (OFF-07 pp. 10-12; videos `rbk7tpLW0TM`, `vCiPPuC8U1s`):
   1. Create a CSV parameter file from the variant.
   2. Each line starting with `SIM_` is one run.
   3. Columns hold the parameters to vary, e.g. the meteo file and the name of the hourly output file.
   4. Enable the output file before running.
   - Format example (ZH-14, PVsyst 6.86): `SIM_1;01.CSV;1;New simulation variant;`.
4. **PVsystCLI**, sold separately: batch mode from the command line (videos `SX3dQ2PHh_4`, `586KBbVsFrA`; 06 §1.1.20).

**Where users get stuck**
- **Albedo.** Varying it in batch has no effect while the "monthly data" box is ticked (ZH-05, PVsyst 7.2.4).
- **Tilt and the 3D scene.** Varying tilt in batch does not move the 3D geometry, so shading stays at the original tilt (ZH-14).
- **Speed.** More steps mean much longer runs (PT-01).
- **Multi-year output.** 25 years of monthly output needs the Aging tool, then 25 CSV files collected from the "UserHourly" folder (ZH-05).
- **Bifacial in batch.** Chapter list of EN-35 (PVsyst 8.0): Advanced Simulation, Batch Simulations, parameters, result variables, run.

**Other examples**
- A Malaysian university course teaches batch optimisation, and counting modules from the 3D scene or from a Google Maps image (EN-32).
- A Politecnico di Torino thesis ran a 50-configuration sensitivity study in PVsyst [unverified, IT-08 snippet].
- An optimisation for Campinas gave 23.8° tilt and 7.5° east, against the rule of thumb "tilt = latitude ± 15°" (PT-08).

**Meridiana.**

| Step | Status |
|---|---|
| Batch runs and variant comparison | ○ |
| Sizing sweep: PV from a quarter to 3× the power, storage from 0 to 2× the shiftable daily energy | ◐ |
| Tilt optimisation | ○ |

Sources:
- OFF-01, OFF-07 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-pseudo-sub-hourly-simulation-en.pdf
- Videos https://www.youtube.com/watch?v=CGou9LUYuB8 , https://www.youtube.com/watch?v=CsizS99dwho , https://www.youtube.com/watch?v=rbk7tpLW0TM , https://www.youtube.com/watch?v=vCiPPuC8U1s , https://www.youtube.com/watch?v=SX3dQ2PHh_4 , https://www.youtube.com/watch?v=-rI9jhMrH0U
- PT-01, PT-07 (above)
- ZH-05 (above); ZH-14 https://www.candela.cn/103c052627/
- EN-35 https://www.youtube.com/watch?v=IjMr59-kisU
- EN-32 https://solar.uitm.edu.my/wp-content/uploads/2024/03/Synopsis-SAPV-using-PVsyst.pdf
- IT-08 https://webthesis.biblio.polito.it/12356/1/tesi.pdf
- PT-08 https://canalsolar.com.br/como-determinar-o-angulo-de-inclinacao-dos-modulos-fotovoltaicos/

### 2.14 P50/P90

**Sequence**: Energy management > P50-P90 estimation (OFF-01 pp. 46-47; video `PGlsrCx1t8o`).
1. **Year-to-year variability.** Take it from a multi-year series: Databases > Compare weather data > select the yearly .MET files > "Histo and Probabilities", which gives the average and RMS.
   - TMY or average data: the simulation result is the P50.
   - Data for one specific year are **not** a P50.
2. **Other uncertainties.** Add the model, inverter, soiling, mismatch and degradation terms. They must represent **year-to-year** randomness, not absolute uncertainty (OFF-01 p. 47).
3. **Yearly values only.** "P90 for hourly or daily values ... doesn't provide meaningful results" (OFF-01 p. 47).

**Practice and values**

| Source | Inputs | Result |
|---|---|---|
| IT-06, STMG 4, 15 MWp, PVsyst 7.2.21 | Variability 0.5 %; module model 1 %; inverter 0.5 %; soiling and mismatch 1 %; degradation 1 %; combined 1.9 % | P50 24.09 GWh, P90 23.51 GWh, P95 23.34 GWh. (analysis) 0.5 % is 5 to 10 times below typical interannual variability (2.6-3.2 % in EN-25; about ±5 % in 06 §1.11.2), and nothing warned. |
| EN-25, Solargis (24/09/2025) | Irradiance model ±3.5 %; PV model ±5 %; year-to-year 2.6-3.2 %; combined by root-sum-square | P75 = P50 - 0.675σ, P90 = P50 - 1.282σ, P95 = P50 - 1.645σ; e.g. P50 1705, P90 1588 kWh/kWp |
| EN-24, IEA PVPS T13-18 (2020) | Bolzano round robin, 7 assessors, same inputs | P50 from 1095 to 1406 kWh/kWp (σ 9.7 %) against a measured 1275 kWh/kWp (2010-2019) |
| EN-12 | Typical σ 7-10 % | P90 = P50 × (1 - 1.28σ) |
| EN-13 | (wording) | "P90 is a 90% exceedance value under that model, not a guaranteed minimum" |
| PT-27, Brazil | EPE certification requires P50 and P90 over the contract plus hourly series; unavailability (TEIF and IP) is deducted after the certified P50 | (none) |

**Meridiana.** P50/P90 ○ (phase 2). (analysis) Warn when the year-to-year variability is below about 2 %, and show every uncertainty term with its source.

Sources:
- OFF-01 (above)
- Video https://www.youtube.com/watch?v=PGlsrCx1t8o
- IT-06 https://va.mite.gov.it/File/Documento/823985
- EN-12, EN-13 https://www.surgepv.com/blog/pvsyst-report-bankability-guide ; EN-24 https://iea-pvps.org/wp-content/uploads/2021/01/Executive-Summary-IEA-PVPS-T13-18_2020-Uncertainties-in-Yield-Assessments-and-PV-LCOE.pdf ; EN-25 https://solargis.com/blog/best-practices/how-to-calculate-p90-or-other-pxx-pv-energy-yield-estimates
- PT-27 https://anaiscbens.emnuvens.com.br/cbens/article/download/1459/1452

### 2.15 Ageing

**Sequence**
1. **Detailed losses > Aging** (OFF-01 pp. 38-39; video `lfzVPcNZ5qc`):
   - the simulation year;
   - the **average** degradation rate (not the warranty);
   - RMS dispersion of Imp and Vmp for the Monte-Carlo mismatch, with an option to keep the generated values and save them as a template.
2. **Aging Tool** for multi-year runs (video `Bbbfg1X1QOU`): parameters, simulation, analysis, multi-year data, export.
3. **Economic evaluation**: module degradation, either a fixed rate or the Aging Tool results (OFF-01 p. 150).

**Values (official)** (OFF-01 p. 39):
- average 0.3-0.5 %/yr "commonly used";
- Imp RMS 0.3-0.6 %/yr;
- Vmp RMS 0.1-0.4 %/yr.

The warranty is a lower limit for each module, "around 20% after 25 years" (OFF-12 p. 29).

**Values (practice)**

| Source | Value |
|---|---|
| EN-10 | 0.5 %/yr (0.4-0.7) |
| PT-13, PT-02 | 0.5 %/yr (glass-glass) |
| IT-07 | 98 % in year 1, then 0.55 %/yr |
| IT-04 | 0.30 %/yr |
| DE-01 | 10 % at 10 years, 20 % at 25 years (warranty points) |
| ZH-04 | "Generally ≤ 0.7 %/yr"; default 0.4 %/yr [unverified] |

**Where users get stuck**
- **The warranty used as the average** (OFF-12 p. 29).
- **Degradation lowers overload loss.**
  - ZH-21: at DC/AC 1.36, overload falls from 1.08 % in year 1 to 0.07 % in year 12.
  - ZH-17: 1.19 % without degradation, 0.82 % with it, at DC/AC 1.32.
  - Hence LID should not be estimated by comparing runs with and without it (ZH-04).
- **The carbon tool** uses 1 %/yr by default (OFF-01 p. 156), inconsistent with the above.

**Meridiana.** Degradation in the cash flows ✔. In the production of year N ○ (◐ overall).

Sources:
- OFF-01, OFF-12 (above)
- Videos https://www.youtube.com/watch?v=lfzVPcNZ5qc , https://www.youtube.com/watch?v=Bbbfg1X1QOU
- EN-10 (above)
- PT-02, PT-13 (above)
- IT-04, IT-07 (above)
- DE-01 (above)
- ZH-04 https://www.candela.cn/9909e437bb/ ; ZH-17 (above) ; ZH-21 https://www.candela.cn/c2772e132a/

### 2.16 Economic evaluation (and carbon balance)

**Sequence** (OFF-01 ch. 12; videos `rRw0GtcuZMQ`, `v3zAAzDL1kI`). Available only **after** a simulation (PT-04; OFF-01 p. 141).
1. **Costs.**
   - Entered globally, per unit, per Wp or per m², in any currency; "Rates" sets exchange rates, which can be downloaded.
   - Installation costs include components, studies, administrative costs (grid connection, permits, taxes), insurance, land, replacement credits and subsidies. Component quantities follow the simulation.
   - Each asset gets a depreciation method: none, straight-line or declining balance.
   - Cost lists can be saved and loaded as templates.
   - Component prices go in the "Component form" or in the database price list (OFF-01 pp. 141-149).
2. **Operating costs**, by system type: inspection, cleaning, insurance, battery replacement, generator fuel, pump replacement (OFF-01 pp. 147-148).
3. **Financial parameters** (OFF-01 pp. 150-151):
   - start and lifetime;
   - inflation (applied to operating costs);
   - discount rate;
   - module degradation;
   - corporate and additional income tax;
   - dividends;
   - financing: equity, subsidies, up to 3 loans (constant annuity, constant amortisation, bullet).
4. **Tariffs** (OFF-01 pp. 151-153):
   - fixed feed-in tariff, "typically 20 years", with a fee, a yearly variation and a price after the contract;
   - time-of-use with summer and winter periods;
   - an hourly or daily CSV;
   - self-consumption savings (internal tariff plus surplus tariff);
   - daylight-saving dates, because PVsyst simulates in standard time.
5. **Results** (OFF-01 pp. 149, 153-156):
   - NPV, payback, IRR ("often referred to as ROI in PVsyst"), ROI, LCOE (discounted);
   - a yearly table.
   - The tool warns that small production changes move the indicators a lot.
6. **Carbon balance** (OFF-01 pp. 156-160; video `yT5NoRiYhB0`):
   - grid emissions: manual, IEA country values from 2010, or energy mix (IPCC median of 296 publications; PSI shares);
   - PV system emissions: manual, IPCC default 46 gCO₂/kWh, or detailed by component (modules from Chinese grid electricity, transport 35 and 60 gCO₂/t/km, steel, concrete, inverters, copper from Chile).

**Practice**
- **PT-04**, Brazil (PVsyst 7): at R$5/Wp and R$0.75/kWh, payback 4.6 years and LCOE R$0.268/kWh with own funds. Brazil's net-metering credits are not modelled.
- **ES-01**, pre-sizing economics: support, transport and mounting costs cannot be edited. A 0-year loan at 0 % is treated as a 1-year loan; the workaround is a real duration at 0 %.
- **Economics done outside PVsyst** with national inputs:
  - Italy: PUN, FER X, ritiro dedicato or net metering, TICA connection costs (IT-02);
  - Germany: EEG period (DE-03).
- EN-14: PVsyst is "not a full financial model".

**Meridiana.**

| Step | Status |
|---|---|
| Savings per time band; RID; CER (DM 414/2023 and TRASE); 10-year tax deduction | ✔ |
| Cash flows, NPV, IRR, simple and discounted payback, LCOE | ✔ |
| CO₂ balance | ○ (phase 3) |
| Hourly GME zonal prices | ○ |

Sources:
- OFF-01 (above)
- Videos https://www.youtube.com/watch?v=rRw0GtcuZMQ , https://www.youtube.com/watch?v=v3zAAzDL1kI , https://www.youtube.com/watch?v=yT5NoRiYhB0
- PT-04 https://canalsolar.com.br/analise-economica-de-um-sistema-fotovoltaico-usando-pvsyst/
- ES-01 (above)
- IT-02 (above); DE-03 (above)
- EN-14 https://www.keentelengineering.com/pvsyst-v8-grid-connected-solar-simulation-guide

### 2.17 Reading the report and the loss diagram

**Official reading guide** (OFF-12 pp. 15-19, 31-33; videos `k8mftCOeq4U`, `EHlHeW-rExc`, `OenFkw3P_3Y`)

**Results dialog.** The six key values are for spotting obvious mistakes. In the daily input/output diagram, points off the line at high irradiance mean overload.

**Report, page by page.** PVsyst 7, simple variant: 6 pages. Details add pages up to 11. 06 §1.1.15 covers the 8.1 layout.

| Page | Content |
|---|---|
| 1 | Cover |
| 2 | Summary |
| 3 | Parameters |
| 4 | Main results: energy, specific production, PR, and the monthly table |
| 5 | Arrow loss diagram |
| 6 | Special graphs |

**Variables**
- In the monthly table: GlobHor, T_amb, GlobInc (plane of array, before optical losses), GlobEff (after far and near shading, IAM and soiling), EArray, E_Grid, EffArrR and EffSysR.
- Normalised yields (IEC 61836): Yr, Ya, Yf, Lc = Yr - Ya, Ls = Ya - Yf, and PR = Yf / Yr.

**Loss diagram**
- It runs GlobHor → GlobInc (the reference for PR) → optical losses → GlobEff × collector area → EArrNom → array losses → EArrMPP → inverter losses → EOutInv → AC losses → E_Grid.
- Outward arrows are losses; inward arrows marked "+" are gains, e.g. spectral +0.13 % in an example.

**Comparison.** Comparing variants from the report highlights the differences, e.g. horizon plus linear shading against a first run.

**Report options**: logo, monthly table frame, **units in the loss diagram**, comparison with another variant or project. "Save this view for the report" sets the 3D image (OFF-13 p. 22).

**Practice**
- **Reading order** in Italian and German reports: horizontal irradiation, then the loss chain, then monthly PR, then the iso-shading diagram (IT-02, IT-07, DE-04).
- **Losses multiply.** Each percentage relates to the preceding energy, so 2 % then 3 % make 4.94 % (EN-13). The product of the factors, leaving out the transposition gain, gives PR (ZH-02).
- **Name the energy boundary** (EArray, EOutInv, E_Grid) when quoting numbers (EN-13). Compare absolute MWh between tools, not percentages (EN-19).
- **PR in VIA annexes**: 78.2-90.5 % (IT-02, IT-04 to IT-07); about 0.8 in ES-01; 80.88 % in PT-13.

**Where users get stuck**
- **Stale simulation.** A report printed by 7.2.16 contained a simulation run with 6.8.8, without warning (IT-05).
- **Narrative against annex.** A VIA narrative states DC/AC 1.00 while its PVsyst annex says 1.232 (IT-04).
- **Translations.** Translated reports carry "Übersetzung ohne Garantie, nur der englische Text ist maßgeblich" (DE-03).
- **Fonts.** Chinese reports need the Arial Unicode MS font, or the text is garbled (ZH-06).
- **Field results against PVsyst.** Hespul audited plants in Mayotte with "différentiels importants entre la production réelle et le rapport de production issu du logiciel PVsyst", then redid the simulations (FR-12, 2023-2024).
- **Report-reading videos**: PT-21 (Portuguese). JA-01 only restates the official documentation.

**Meridiana.**

| Step | Status |
|---|---|
| PDF report with data, results, charts, strings, calculations in LaTeX, and the list of values still at default | ✔ |
| Loss chain with diagram | ✔ |
| Results per field or MPPT | ◐ |
| Comparison of variants | ○ |
| Hourly CSV export | ○ |

Sources:
- OFF-12, OFF-13 (above)
- Videos https://www.youtube.com/watch?v=k8mftCOeq4U , https://www.youtube.com/watch?v=EHlHeW-rExc , https://www.youtube.com/watch?v=OenFkw3P_3Y
- EN-13 (above); EN-19 https://pvcase.com/blog/precision-in-solar-simulations-pvcase-yield-and-pvsyst-loss-calculations
- ZH-02, ZH-06 (above)
- IT-02, IT-04, IT-05, IT-07 (above)
- DE-03 (above); DE-04 https://reposit.haw-hamburg.de/bitstream/20.500.12738/12416/1/RodionovaDaryaBA_geschw%C3%A4rzt.pdf
- ES-01, PT-13 (above)
- FR-12 https://www.hespul.org/fr/nos-projets/nos-projets-accompagnement-et-conseil/ ; PT-21 https://www.youtube.com/watch?v=TcYp012K1mk ; JA-01 https://www.lefixea.com/article/pvsyst_inspection17

### 2.18 Module Layout

**Prerequisites**: a finished 3D scene and System. Module Layout "is usually the final step", because any later change forces a revision (OFF-01 p. 107).

**Sequence** (OFF-01 ch. 11, pp. 107-140; videos `eeU2HmxJ8jk`, `wJB50QsR--w`, `h8BQGk0XsJg`, `SO6Tbso8Fqo`, `3D8Ak3LaLis`)
1. **Mechanical tab.** Press "Define all modules", then set module spacing, filling mode, and portrait or landscape (OFF-01 pp. 112-115).
   - Add rows or columns if modules are missing; this changes every table of the field.
   - Right-click to remove a module.
   - "Adjust selection" or "Adjust all tables" makes the tables match the modules.
   - Polygonal fields: fill, edit, then "Match to Table".
   - The blue panel says what to do next.
2. **Electrical tab.** Each inverter input and string has a colour (1 to 10).
   - **Automatic assignment** strategies (OFF-01 pp. 118-124):
     - **large tables**: all modules of a string in one row; or 2 rows ("U-shaped", not optimal for mutual shading); or 3-5 rows; or "remaining unassigned";
     - filling direction, origin, and left-to-right or back-and-forth;
     - **small tables**: a string over 1, 2, 3, 4 or 5 tables, filled in rows or columns;
     - "Same row per MPPT", the optimum for string inverters with 2-3 strings per MPPT.
   - Strategies can be applied to selected tables or inverters, then cleared and retried.
   - Manual mode: click or drag modules into a string, right-click to unassign, and use swap mode to move or swap assignments.
3. **Objective.** One string = one row:
   - standard modules (3 sub-modules along the length) in landscape;
   - half-cut ("twin") modules in portrait (OFF-01 p. 125).
4. **Outputs.**
   - Print or BMP images, which can go into the report "as reference wiring diagrams for the site" (OFF-01 pp. 109, 128).
   - Learning tabs: *3D Shading* (15-minute animation per inverter; right-click a module to see its I/V curve) and *I/V Curve* (MPPT input).
   - Worked example: a twin half-cut module loses 37.2 % in total, of which 7 % is linear shading and 30.2 % electrical (OFF-01 pp. 129-130).
5. **Simulation.** Near shadings > "Detailed electrical calculation (according to module layout)" (OFF-01 p. 65).

**Limits** (OFF-01 pp. 88, 109-111)
- Crystalline modules with rectangular cells only; not thin film.
- It "underestimates the impact of long and thin shadows" such as poles: use partitions instead.
- Warning above 1 MWp; error above 5 MWp (advanced settings).
- For larger plants: run a representative sub-system (e.g. one central inverter) with both models, derive the electrical-effect fraction, then simulate everything with partitions.
- Not compatible with partial shading calculations.

**Practice**
- **FR-01** ("Calepinage", PVsyst 6):
  1. "Import de la scène 3D".
  2. Zoom out.
  3. "Déf tous modules".
  4. Put modules shaded together into the same string.
- **AR-01** saves the string drawings for site work, and compares assignment options for cable savings.
- **DE-01** (PVsyst 6.68): strings could not join rows of two adjacent tables as in the real plant. 8.1 offers strings over 2-5 tables.

**Meridiana.**

| Step | Status |
|---|---|
| Strings on the plan: serpentine row by row, never across two fields | ✔ |
| Names inverter.input.string, colours per input; W shows or hides | ✔ |
| Modules outside strings flagged | ✔ |
| Electrical effect computed for every project from cell blocks drawn on each module | ✔ |
| I/V curve view per module or MPPT | ○ (analysis: not listed) |
| Strings over several small tables | (analysis: not stated) |

Sources:
- OFF-01 (above)
- Videos https://www.youtube.com/watch?v=eeU2HmxJ8jk , https://www.youtube.com/watch?v=wJB50QsR--w , https://www.youtube.com/watch?v=h8BQGk0XsJg , https://www.youtube.com/watch?v=SO6Tbso8Fqo , https://www.youtube.com/watch?v=3D8Ak3LaLis
- FR-01, AR-01, DE-01 (above)

### 2.19 Electrical shading effect (partition model)

**Sequence** (OFF-01 pp. 64-65, 100-106; OFF-13 pp. 25-28; video `fZB2qAW8_qo` at 1:28)
1. **Define the partitions.** In the 3D scene, double-click a table, open the *Partition* tab and set the divisions in height and width.
   - Transfer them to the selection, to tables of the same size, to all tables, or to tables of the same orientation.
   - In PVsyst 7, each partition rectangle is "the area of a complete string (not a module!)" (OFF-13 p. 26).
2. **Choose the mode.** Near shadings > *Use in simulation* > "According to module strings", then set the **Electrical effect fraction** (default 100 %).
3. **Compute the tables.** Two shading tables are computed, linear and by strings. The animation shows electrically lost partitions in **yellow**, next to the geometric shade in grey.
4. **Calibrate the fraction** with Module Layout on a sub-system (OFF-01 p. 103). Example: strings 4 %, layout 3 %, so the fraction is 75 %.

**Partition rules** (OFF-01 pp. 104-106; checked on the rendered pages)

Notation: x = number of rows of modules per MPPT; L = landscape; P = portrait; T = half-cut in portrait; U = U-shaped wiring over several rows.

| Case | Partitions in height (OFF-01, May 2026) | Help (06 §1.1.8) |
|---|---|---|
| 1L | 2 | 2 |
| xL | x | x |
| xLU | **3x** | x (3x until 7.4.8) |
| xP | x | x |
| xPU | Module Layout recommended | same |
| xT | 2x | 2x |
| xTU | x | x |

Use Module Layout instead when (OFF-01 p. 106):
- strings are irregular;
- tables are non-uniform;
- strings run in portrait over several rows in U;
- the plant is very large and mismatch is critical.

**Teaching cases worth reproducing** (OFF-01 pp. 132-140)
- **Three strings on one MPPT.** With 1/3 of one string's sub-modules shaded, the loss reaches "approximately 85%": only the diffuse part (about 15 %) survives in the shaded string.
- **One string per MPPT.** The loss stays close to the shaded fraction plus the bypass-diode drop. The advantage disappears if the inverter's minimum MPP voltage forces the operating point.
- **Same row per MPPT.** Concentrating shaded rows on one MPPT is optimal, but feasible only with 2-3 strings per MPPT.
- **Bottom cell.** Electrical loss is largest when only the bottom cell row is shaded. The graph sits under Tools > PV module electrical behavior > Array with shaded cells > Study of bypass diode effect.

**Practice**

| Source | Practice or value |
|---|---|
| IT-05 | Fraction 80 % on regular tracker rows |
| DE-05 (2015) | 100 % |
| ZH-03 (6.x) | "1 string per module" for standard modules, 3 for "smart" modules |
| ZH-16 (PVsyst 7.0) | Half-cut modules: 3.85 % shading loss against 6.53 % with full cells |
| ZH-13 | Strings mode needed to rank tracker strategies (2.4) |
| EN-29 (PVsyst staff, PVPMC 2022) | 2 to 6 partitions with optimizers, depending on the type |
| EN-12 [unverified] | Partitions instead of Module Layout underestimate partial-shade loss by 2-5 % |

**Optimizers.** Tigo's guide models them in PVsyst from 6.48 onwards (newer products from 7.2). It runs two variants and sets the module mismatch to 0 in the optimizer variant [unverified, EN-S1 snippet].

Thin objects such as cables and fences have their own tool and fraction (OFF-01 p. 75; 06 §1.1.8).

**Meridiana.**
- Electrical effect for strings ✔. It uses the Martinez-Moreno, Muñoz and Lorenzo model (2010, in pvlib), with cell blocks drawn on every module: three strips, two halves for half-cut cells.
- The PVsyst partition model was tested and discarded, because its own guide calls it an upper bound.
- It covers obstacle shading and row-to-row shading; diodes and half-cells come from the .PAN.
- (analysis) The OFF-01 85 % case, the 37.2 % module example and ZH-16 are ready validation tests.
- Thin objects ○ (analysis: not listed).

Sources:
- OFF-01, OFF-13 (above)
- Video https://www.youtube.com/watch?v=fZB2qAW8_qo
- IT-05, DE-05, ZH-03, ZH-13 (above)
- ZH-16 https://www.candela.cn/218a1b130c/
- EN-29 https://pvpmc.sandia.gov/download/3803 ; EN-12 (above)
- EN-S1 https://support.tigoenergy.com/hc/en-us/articles/215348938--GUIDE-Modeling-Tigo-in-PVsyst
- 06 §1.1.8

### 2.20 String sizing

**Sequence** (OFF-01 pp. 25-30; videos `lis_9F-f2pI`, `MhSqXGE_AvE`, `6QpgYVrLZus`)
1. **Constraints on the number of modules in series** (OFF-01 p. 27), with the defaults from *Project settings > Design conditions*:

   | Check | Temperature | Default |
   |---|---|---|
   | Stay above the inverter's minimum MPP voltage | Maximum module operating temperature | 60 °C |
   | Stay below the inverter's maximum MPP voltage | Minimum operating temperature | 20 °C |
   | Voc stays below the inverter's absolute maximum | Minimum temperature | -10 °C |
   | Do not exceed the module's maximum system voltage | (none) | (none) |

2. **Sizing button.**
   - Upper graph: the array I/V curve with the inverter's MPPT window and its voltage, current and power limits. "The little black dot should be within the safety limits."
   - Lower graph: the yearly distribution of output power, used to size the inverter for an acceptable overload. This typically gives a DC/AC of about **1.25** (OFF-01 pp. 27-28).
3. **Homogeneity rules** (OFF-01 pp. 25-26):
   - Each MPPT input has the same module, the same series count and the same orientation.
   - PVsyst forbids several orientations within one string.
   - Parallel strings with different orientations are acceptable.
   - Different module models on one input are "not supported".
   - The string count should be a multiple of the number of MPPTs, otherwise PVsyst spreads them and warns about imbalance.
4. **Multi-MPPT** (OFF-01 pp. 28-30):
   - "Pnom sharing within the inverter" (equal), or "Independent MPPT inputs" with **Power sharing** groups;
   - drag sub-arrays onto inverters;
   - "Auto-equalize Pnom", with a weight icon to balance and an eraser icon to reset.
5. **Temperature coefficients** (OFF-04 pp. 6-7):
   - PVsyst's muVoc is a model result used only for sizing. The manufacturer's value can be used through *Additional data* plus a project parameter.
   - muPmpp is "a fundamental parameter for the simulation".

**Practice and pitfalls**
- **-10 °C default.**
  - It caused a false over-voltage error on a 21-module string; set the local minimum (ZH-02).
  - The temperature step is taught explicitly (AR-01 10 kWp at 4:59; AR-03).
  - OFF-12: "ideally" the lowest daylight temperature ever measured; central Europe uses -10 °C, lower in mountains.
- **Unbalanced inputs.** They need two sub-arrays. The warning "The inverter is slightly oversized" is advisory. Merging inputs is allowed only if the manufacturer permits it (PT-05).
- **DC/AC per MPPT.** The "uses multi-MPPT" box changes the ratio per input when string counts differ. Master/slave inverters need two sub-arrays (ZH-06).
- **Voc correction and wide MPPT ranges** are explained in a Huawei webinar (PT-16).
- **The 70 °C point.** PT-09 reads the maximum-load current from the sizing graph at 70 °C to size cables.
- **Contractual limits.** "Nominal and Maximum PV power" in the OND block the simulation only when marked "Required" as contractual (OFF-04 p. 9).

**Values of DC/AC seen**

| Source | DC/AC |
|---|---|
| IT-05 | 1.07-1.08 |
| PT-13 | 1.09 |
| TR-07 | 1.11 |
| IT-06 | 1.20 |
| IT-04 | 1.23 |
| PT-07 | 1.26 |
| ZH-09 | 1.3 |
| ZH-17 | 1.32 |
| ZH-21 | 1.36 |
| ZH-03 | 1.42, with 1.1 % clipping |
| EN-S3 [unverified] | About 1.2 in northern Europe |
| OFF-01 | About 1.25 |

**Meridiana.**

| Step | Status |
|---|---|
| CEI 64-8/7:2024 checks: Uoc max at Tmin, Isc max, MPPT window hot and cold, string protection, SELV | ✔ |
| Automatic string proposal | ✔ |
| DC/AC ratio | ✔ |
| Overload histogram | ○ (◐ overall) |
| Overload loss limit as a design condition | ○ |
| Power sharing between MPPTs | ○ (analysis: not listed) |

Sources:
- OFF-01, OFF-04 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-components-database-en.pdf ; OFF-12 (above)
- Videos https://www.youtube.com/watch?v=lis_9F-f2pI , https://www.youtube.com/watch?v=MhSqXGE_AvE , https://www.youtube.com/watch?v=6QpgYVrLZus
- ZH-02, ZH-03, ZH-06 (above); ZH-09 https://www.candela.cn/1fd28ab5d5/
- AR-01 https://www.youtube.com/watch?v=OANr16Rh4fo ; AR-03 https://www.youtube.com/watch?v=kbJMo3FeIbc
- PT-05 https://canalsolar.com.br/pvsyst-inversor-com-multiplas-entradas-de-mppt/ ; PT-09 https://canalsolar.com.br/nbr-16690-queda-de-tensao-circuito-cc/ ; PT-16 https://www.youtube.com/watch?v=vgP5_F73CxA
- TR-07 http://kho.msu.edu.tr/akademIk/enstitu/Alp_SAVBEN_dergi/21(1)/1.pdf
- EN-S3 https://help.pvcase.com/en/articles/7936074-exporting-fixed-tilt-frames-to-pvsyst
- IT-04, IT-05, IT-06, PT-07, PT-13, ZH-17, ZH-21 (above)

### 2.21 Cable and transformer losses

**Sequence**: Detailed losses > Ohmic losses (OFF-01 pp. 32-34; OFF-02 p. 25; video `1FTEVIt9HWU` 1:54-4:11; video `V495ATFuLTM`).

**DC circuit**
- Default **1.5 % at STC**.
- *Detailed computation* tool: average lengths of string loops and of the runs from junction boxes to the inverter, plus a help for choosing wire sections.
- Alternatively a global wiring resistance from third-party software.
- The annual effect is "usually of the order of 50-60%" of the STC value, because the loss scales with I².
- Blocking diodes are obsolete; leave their voltage drop at 0 (OFF-01 p. 32).

**AC circuit**
- Distance from the inverter to the injection point. With a transformer, it becomes the distance from the inverter to the transformer.
- **Reference power**: PNomPV(ac), the default before 7.2, or PNom(Inv). Chosen per project, with a preference for new projects (OFF-01 p. 34).

**Transformers**
- Layouts: one or several MV transformers for the whole system (output shared equally), or one per sub-array; plus an optional HV transformer (OFF-01 p. 33).
- **Iron loss** default 0.1 % of the reference power.
- "Night disconnect", global, avoids a negative E_Grid at night.
- Copper loss as R·I².
- "Specify the actual parameters ... (recommended)": nominal power, iron (no-load) loss, copper loss (OFF-02 p. 25).

**Practice**

| Source | Practice or value |
|---|---|
| FR-01 | Lengths entered (10 m on the roof plus 2 × 20 m); AC ignored with the meter next to the inverter |
| PT-09 | Brazilian NBR 16690 recommends at most 3 % DC voltage drop at Vmpp STC. 6 mm² over 0.92 km at 11 A gives 4.25 %; PVsyst showed little gain from 10 mm², so more than 3 % was accepted. |
| ZH-06 | With several sub-arrays, use "apply to all sub-arrays", or the DC loss is wrong |
| VI-01 | Transformer losses are not included by default; add them when the meter is on the MV side |
| DE-01 | Transformer 1.0 %, "the value PVsyst recommends" [unverified] |
| IT-04, DE-04, EN-24, TR-07 | Transformer 0.86-1.38 %; MV 0.89 %, HV 0.86 %, MV cables 0.33 % (IT-04 narrative); MV transformer 0.9 % (EN-24); 1.10 % (TR-07) |
| IT-02 | Annual results: DC 0.19 %, AC 0.46 % |
| IT-01 | Using "1.5 % at STC" as a flat annual loss overestimates it |
| EN-09 (owner RFP template) | Bidders declare DC and AC losses at STC and the transformer's constant and peak-power losses **in W** |
| FR-04 (SMA France, 7.2.1) | AC losses can now use inverter power; compare inverters with their thermal derating; prefer OND files with three-voltage efficiency curves |

**Meridiana.**

| Step | Status |
|---|---|
| DC and AC wiring losses in the ordered loss chain | ✔ |
| MV transformers, lines, auxiliaries | ○ |
| Cable sizing aid | ○ |

Sources:
- OFF-01 (above); OFF-02 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-grid-connected-en.pdf
- Videos https://www.youtube.com/watch?v=1FTEVIt9HWU , https://www.youtube.com/watch?v=V495ATFuLTM
- FR-01 (above); FR-04 https://www.sma-sunny.com/fr/concevoir-son-projet-avec-pvsyst-3-choses-a-savoir-pour-une-utilisation-optimale-du-logiciel/
- PT-09, ZH-06, VI-01, DE-01, DE-04, IT-01, IT-02, IT-04, TR-07 (above)
- EN-09 https://entergyarkansas.com/wp-content/uploads/2025/06/Appendix-B-2-Solar-BOT-Scope-Book-Appendix-4-Energy-Model.docx ; EN-24 (above)

### 2.22 Unavailability

**Sequence**: Detailed losses > Unavailability (OFF-01 pp. 39-40; 06 §1.1.13.11).
- Express it as a fraction of time or a number of days.
- Define specific periods, or let PVsyst generate them at random. The result has "only a statistical meaning".
- A CSV series is possible since 8.1.6 (06).

**Practice**

| Source | Practice |
|---|---|
| EN-09 (owner and independent engineer) | Run PVsyst at **0 %** unavailability and apply availability in post-processing |
| EN-12 | 0.5-2 % |
| DE-01 | 99 % measured availability; PVsyst assumes 100 % unless set |
| IT-04 | 0 % |
| PT-27 (Brazil) | Forced and scheduled outages (TEIF, IP) deducted after the certified P50 |

**Meridiana.** Unavailability ✔ (in the loss chain). (analysis) Offer both modes: inside the simulation, or as a post-processing factor reported separately for lenders.

Sources:
- OFF-01 (above)
- EN-09, EN-12, DE-01, IT-04, PT-27 (above)

### 2.23 LID and LeTID

**LID** (OFF-01 pp. 34-35; OFF-12 p. 27)
- Not proposed by default because "not sufficiently established".
- When enabled, the proposed value is **2 %**; the range is 1-3 % "or even more".
- Only p-type boron-doped wafers; "n-type doped wafers are not affected".
- PVsyst 7 called 2 % "typical".

**Practice**

| Source | Value or rule |
|---|---|
| EN-09 | **Net LID** = year-1 warranty minus annual degradation, e.g. 2.00 - 0.45 = 1.55 %. "50% of the LID warranty rate or 1.0% have been accepted values in the past". |
| EN-16 (Anza) | 0.6 % without test data |
| EN-26 (Solargis) | 1-2 % in year 1, then 0.5-0.7 %/yr |
| EN-40 | Video tutorials on the LID loss and on PR for P50/P75/P90 |
| EN-10 | 1-3 % for p-type |
| IT-02, IT-05, IT-06, FR-01 | 0.4-2 % |
| ZH-04 | Do not estimate LID by comparing runs with and without it: LID also lowers the overload loss |

**LeTID**
- No tutorial found in any language.
- PVsyst has no LeTID item (06 §0.4).
- (analysis) Users can only fold it into LID or into the degradation rate.

**Meridiana.** LID ✔ (in the loss chain); LeTID ○.

Sources:
- OFF-01, OFF-12 (above)
- EN-09, EN-10 (above); EN-16 https://www.anzarenewables.com/blog/solar-pv-pan-files-explained/
- EN-26 https://kb.solargis.com/docs/system-unavailability-losses-long-term-degradation ; EN-40 https://www.youtube.com/watch?v=hzcolxpSaMk , https://www.youtube.com/watch?v=Y5OtBJ0SdSU
- IT-02, IT-05, IT-06, FR-01, ZH-04 (above)

### 2.24 Soiling and snow

**Sequence**: Detailed losses > Soiling (OFF-01 p. 35; OFF-12 pp. 28-29).
- A yearly or **monthly** value, for periodic cleaning or rainy seasons.
- An hourly CSV since 8.1.0.
- Snow can be modelled as soiling: PVsyst 7 suggests **50 %** for a winter month with 15 days of snow cover.

**Values**

| Source | Value |
|---|---|
| OFF-12 | "Almost negligible" in temperate residential areas |
| DE-01 | 0.5 % at steep tilt; Germany typically 1-3 % |
| IT-05 | 1 % "prudenziale" |
| IT-02 | 1-2 % |
| EN-23 | 2 % flat: "many EPC teams adopt a flat assumption, most often 2% annual loss" |
| TR-04, TR-06 | 3 % |
| EN-12 | 1-4 % |
| PT-12, citing literature | 1.5-6.2 % |
| AR-02 (Dubai, 2 MW, 30° south) | 0 % gives 1788 kWh/kWp; 3 % gives 1734; 10 % gives 1633; 15 % gives 1551 |
| EN-09 | Owners want a **monthly** soiling profile, later replaced by soiling-station measurements during the capacity test |

The claimed "3 % default" in older versions (EN-30, ZH-23) is [unverified]; the 8.1 help states none (06).

**Meridiana.** Yearly soiling ✔; monthly or time series ○; snow ○.

Sources:
- OFF-01, OFF-12 (above)
- DE-01, IT-02, IT-05 (above)
- EN-23 https://www.solarpowerworldonline.com/?p=110949 ; EN-12, EN-09 (above) ; EN-30 https://www.electroniclinic.com/pvsyst-software-getting-started-tutorial/
- TR-04 (above); TR-06 https://www.set-science.com/a/84297240-ef3e-47d3-a635-9c617c30a32f/pdf
- PT-12 (above)
- AR-02 https://www.youtube.com/watch?v=aKf0p-vm6Xk
- ZH-23 https://www.candela.cn/d86e10cc8c/

### 2.25 Albedo

**Sequence**
- Project settings > Albedo: the **far albedo**, yearly or monthly. "In general, you will never modify the Albedo factor": 0.2 is standard, with 0.8 for months with snow (OFF-12 p. 8).
- The ground albedo **under** bifacial modules is set separately in System (OFF-01 p. 13). Since 8.1.2 it can come from a CSV time series (release notes).

**Values**

| Source | Values |
|---|---|
| IT-04, IT-05, IT-06, DE-03, TR-07, EN-14, EN-20 | 0.20 in every PVsyst annex and guide |
| IT-04 narrative | MODIS monthly 14.8-20.1 %, mean 17.1 % |
| ZH-17 | Concrete roofs 0.25-0.35 |
| ZH-04 | Water about 0.1 (floating PV) |
| ES-01 | Urban 0.14-0.22; snow up to 0.8 |
| PT-02 | Gravel or sand 0.30-0.35 for bifacial |
| EN-07 | Grass 0.199, gravel 0.295, white surface 0.556 (Soltec, one year) |
| EN-09 | Owners want 12 monthly values |

**Pitfall.** A batch variation of albedo is ignored when the monthly box is ticked (ZH-05).

**Meridiana.** Yearly albedo ✔; monthly ○.

Sources:
- OFF-01, OFF-12 (above)
- IT-04, IT-05, IT-06, DE-03, TR-07, ZH-04, ZH-05, ZH-17, ES-01, PT-02, EN-07, EN-09, EN-14 (above)
- EN-20 https://knowledgebase.glintsolar.com/en/article/losses-in-glint-solar-vs-losses-in-pvsyst

### 2.26 Spectral correction

**Sequence**: Detailed losses > Spectral correction (OFF-01 p. 40; OFF-02 p. 32).

PVsyst has three models:

| Model | Applies to | Activation |
|---|---|---|
| CREST | Amorphous silicon | Automatic |
| Sandia database correction | Modules of the Sandia database | Automatic |
| First Solar | Any technology "at their discretion" | Off by default |

- The First Solar model needs precipitable water, or relative humidity to estimate it. Synthetic files made with 6.7.4 or later always contain relative humidity.
- When spectral correction is used, the report lists the coefficient set and the loss diagram gets a "spectral losses" arrow. One example shows a +0.13 % gain (OFF-12 p. 33).

**Practice.** Thin:
- EN-24 (IEA PVPS) best-practice table: spectral -1.0 %;
- EN-09: bidders declare "Spectral correction applied: Yes/No";
- AR-05 lists spectral correction among the PVsyst 7 novelties.

**Meridiana.** Spectral correction ○ (phase 2).

Sources:
- OFF-01, OFF-02, OFF-12 (above)
- EN-24, EN-09 (above)
- AR-05 https://www.youtube.com/playlist?list=PLyiEdrKX7c24qvKohwkiRgOYvIJPR23t_

### 2.27 Components from datasheets (PAN and OND)

**PV module** (OFF-04 pp. 3-7; videos `wICpYvHYZbU`, `uRXQXr8wAdQ`, `5MJo_9dqbBk`)
- **Start from a similar component** and save it under a new name: "much easier" than starting from scratch. Name the file "Manufacturer_Model.PAN"; the file name is the database key.
- **What PVsyst ignores**: efficiency at STC, NOCT ("never specified in PVsyst"), reverse current, and values at NOCT conditions.
- **Electrical checks**: Vmpp × Impp must match Pnom within **0.2 %**, otherwise set Impp = Pnom / Vmpp.
- **Size and technology tab**:
  - size, which gives the efficiency;
  - cells in series, which is mandatory;
  - cell size;
  - maximum IEC or UL voltage;
  - **number of bypass diodes**, used by Module Layout.
- **Model parameters**:
  - leave the Rs and Rsh defaults ticked;
  - leave the exponential Rsh defaults unless measured;
  - enter the Pmpp temperature coefficient, which is "fundamental".
- **Additional data**: secondary parameters; IAM profile; low-light data; a measured I/V curve to fit.
- **IAM warning.** An IAM profile above Fresnel triggers a warning when the PAN is opened. The fix is "Default Fresnel" (OFF-01 p. 37).

**Inverter** (OFF-04 pp. 8-13; video `ADgwnDSk92U`)
- **MPP window** ("Rated MPP voltage range"). At the limits PVsyst clips the operating voltage; behaviour outside the window is unknown.
- **"Minimum voltage for PNom"**: a current limit.
- **Absolute maximum PV voltage.**
- **Power threshold** ≥ 0.5 % of Pnom.
- **Efficiency curve**: maximum and EURO or CEC efficiency (example 98.2 % and 97.5 %). Tick "3 voltages" when such data exist.
- **Output parameters**: cos φ limits; Pnom given as kVA "most often"; PMax as a function of temperature.
- **"Behavior at limits"**: "never modified".

**Practice**

| Source | Practice |
|---|---|
| PT-06 (PVsyst 6.80) | Install a .PAN by copying it into a version-specific folder (`PVsyst680_data\ComposPV\PVmodules`) with PVsyst closed; user items show in grey |
| VI-01 | Manufacturers update database entries within 3-6 months; check them against the datasheet |
| AR-07 | Checks database entries against datasheets before use |
| EN-17 (Kiwa PVEL) | 22 test points (IEC 61853-1) on 3 modules; manufacturer PANs were 1.1-2.9 % more optimistic in low light |
| EN-18 (Black & Veatch, 2013) | Fitted PANs gave 2-5 % more energy, with non-physical parameters |
| EN-16 (Anza) | PAN validation checklist; ASHRAE b0 0.04-0.05 |

(analysis) The source of the PAN alone can move yield by 1-5 %.

**Meridiana.**

| Step | Status |
|---|---|
| Parameters from the datasheet (De Soto one-diode; full, half and quarter cells) | ✔ |
| 16,886 CEC modules; .PAN and .OND import with validation | ✔ |
| PVsyst one-diode with exponential Rsh | ○ |
| IAM from the .PAN | ○ (next step in funzionalita) |
| User items and favourites | ○ |

Sources:
- OFF-04, OFF-01 (above)
- Videos https://www.youtube.com/watch?v=wICpYvHYZbU , https://www.youtube.com/watch?v=uRXQXr8wAdQ , https://www.youtube.com/watch?v=5MJo_9dqbBk , https://www.youtube.com/watch?v=ADgwnDSk92U
- PT-06 https://canalsolar.com.br/saiba-como-adicionar-arquivos-pan-no-pvsyst/
- VI-01 (above)
- EN-16 (above); EN-17 https://www.kiwa.com/pvel/pqp/pan-iam ; EN-18 https://pvpmc.sandia.gov/download/4600
- AR-07 https://www.udemy.com/course/excel-pvsyst/

### 2.28 Stand-alone and pumping (brief)

Meridiana puts these in phase 3, so only the teaching pattern is recorded here.

- **OFF-09** (stand-alone, 72 pages) and **OFF-11** (pumping, 94 pages) are **click-by-click screenshot books**. The new site shows one call-out per action: "Accept selected point", "Save", "Yes" to create the synthetic file, "Rename the variant", and so on. They go through 5 variants each:
  - stand-alone: controller without MPPT, with MPPT, then 1.6 kW, 5.6 kW with 37 kWh, and 12 kW;
  - pumping: up to an economic evaluation.
- **OFF-09 example**: a 12 V 160 Ah sealed lead-acid battery, 2 in series × 2 in parallel; a 285-300 W module, 1 × 2; "Direct coupling" regulator; DC wiring left at 1.50 %.
- **OFF-08 and OFF-10** cover load definition (6 methods), storage, back-up generator, pumping tests, wells and lakes.
- **PVsystBasic** (1.2) is the vendor's separate guided product for pumping.

(analysis) The screenshot-book style is the format beginners need for grid-connected projects too; PVsyst does not offer it there.

Sources:
- OFF-08, OFF-09 (above); OFF-10 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-pumping-system-en.pdf ; OFF-11 https://www.pvsyst.com/pdf/pdf-tutorials/pvsyst-8/pvsyst-tutorial-v8-pumping-over-the-sun-en.pdf
- W-04 https://www.pvsyst.com/en/products/pvsyst-basic

---

## 3. Typical values recommended across tutorials

**How to read the table.**
- "Official" means PVsyst SA documents: OFF-xx, or the help as reported in 06.
- "Most often" is the modal value across the third-party sources in section 6. Where only one unofficial source gives a value, it is marked [unverified].
- Source URLs are in section 6. Each subsection of section 2 repeats the URLs for its task.

| Parameter | Official default or guidance | Range seen in tutorials and reports | Most often | Sources |
|---|---|---|---|---|
| Far albedo | 0.2, "standard"; 0.8 in months with snow | 0.10 (water) to 0.35 (concrete or gravel); measured 0.20 grass, 0.30 gravel, 0.56 white | **0.20** | OFF-12 p. 8; IT-04/05/06; DE-03; TR-07; EN-14; EN-20; ZH-04; ZH-17; ES-01; PT-02; EN-07 |
| Bifacial ground albedo | Set in System, monthly or CSV (8.1.2) | 0.20-0.35, 0.6 in the Qinghai desert [unverified] | 0.20-0.30 | PT-02; PT-03; ZH-20; EN-06 |
| Bifaciality factor | From the PAN; upper limit 98 % since 8.0.12 | 0.60-0.90 | 0.70 (PERC), 0.80-0.85 (n-type) | EN-06; IT-02; PT-03; ZH-20 |
| Bifacial height | Lowest edge for fixed racks, axis for trackers | 0.5-1.5 m | 1.0 m | PT-02; PT-03; ZH-05; ZH-20 |
| Bifacial structure shading | User input | 5-27 % depending on the rack | (none) | EN-05; ZH-20 |
| Rear mismatch | User input; formula changed in 7.4.6 | Below 0.2 % of the annual yield (EN-05); 3-10 % input values in older practice [unverified] | (none) | EN-05; IT-04; ZH-20 |
| Uc / Uv | 29/0 free-standing; 27 domes; 20 semi-integrated (default for new projects); 15 integrated; Uv = 0 recommended | Fitted 22.4/5.7 on site; 18 on a steel roof with 8 cm gap | **29/0** for ground and trackers; 20 for roofs | OFF-01 p. 31; OFF-12 p. 24; IT-01; IT-05; DE-01; EN-27; ZH-15 |
| Design minimum temperature | -10 °C, "ideally" the lowest daylight value ever; lower in mountains | Local value | Local value | OFF-01 p. 27; OFF-12 p. 9; ZH-02; AR-01 |
| Design maximum module temperature | 60 °C (minimum-voltage check); 20 °C for the maximum MPP voltage | (none) | 60 °C | OFF-01 p. 27 |
| Overload loss limit for design | 3 % (PDFs); 4 % (help, 8.0.13) | (none) | (none) | OFF-01 p. 13; 06 §1.1.9.4 |
| DC/AC (Pnom ratio) | About 1.25 from the overload rule; 06: 1.25-1.3 | 1.07-1.42 | **1.2-1.3** | OFF-01 p. 28; IT-04/05/06; PT-13; TR-07; ZH-03/09/17/21; EN-S3 |
| DC wiring loss at STC | 1.5 %; annual effect about 50-60 % of it | 1.0-1.5 % input; 0.19-0.8 % annual result; Brazil: at most 3 % voltage drop | **1.5 %** | OFF-01 p. 32; DE-01; DE-03; IT-04; IT-02; EN-24; PT-09 |
| AC wiring loss | From distance | 0-1 % input; 0.35-0.46 % result | About 0.5 % result | IT-02; TR-07; DE-01; EN-12 |
| MV transformer | Iron 0.1 % of reference; datasheet values recommended | 0.86-1.38 % total | **About 1 %** | OFF-01 p. 33; OFF-02 p. 25; DE-01; IT-04; DE-04; EN-24; TR-07 |
| Module quality | A quarter of the tolerance spread (8.1); half the lower tolerance (7) | -1 % to +0.8 % | **About -0.8 %** for 0/+x tolerance | OFF-01 p. 34; OFF-12 p. 26; IT-05; IT-06; FR-01; EN-09 |
| LID | No default; 2 % when enabled; 1-3 %; p-type only | 0.4-2 %; net LID = warranty minus annual degradation | **1-2 %** | OFF-01 pp. 34-35; EN-09; EN-10; EN-16; IT-02/05/06 |
| Module mismatch | 06: 2 % default | 0 % (optimizers) to 2 % | **1 %** (also 2 %) | FR-01; DE-01; IT-04/05/06; TR-04; EN-10 |
| String voltage mismatch | Neglected as a transient effect | 0.1-0.2 % | 0.1 % | OFF-01 p. 35; DE-01; IT-04; IT-06 |
| Soiling | No default (8.1); "almost negligible" in temperate residential areas; snow as 50 % in a month with 15 days of cover | 0.5-3 %; 15 % in Dubai sensitivity runs | **1-2 %** temperate; 3 % semi-arid | OFF-12 pp. 28-29; DE-01; IT-05; IT-02; EN-23; TR-04/06; AR-02; EN-12 |
| IAM | Fresnel default (since 6.67); warning if the PAN profile is above Fresnel | ASHRAE b0 0.04-0.05 in older PANs | Fresnel | OFF-01 p. 37; ZH-17; EN-16 |
| Degradation | 0.3-0.5 %/yr "commonly used"; RMS Imp 0.3-0.6, Vmp 0.1-0.4 %/yr; the carbon tool uses 1 %/yr | 0.3-0.7 %/yr | **0.5 %/yr** | OFF-01 pp. 39, 156; EN-10; PT-02; PT-13; IT-04; IT-07; ZH-04 |
| Unavailability | Fraction or days, random periods | 0-2 % | **0 % in PVsyst**, then applied afterwards (lenders) | OFF-01 p. 39; EN-09; EN-12; DE-01 |
| Near-shading electrical fraction | 100 % default; calibrate with Module Layout (e.g. 75 %); 60-80 % guess in PVsyst 7 | 80-100 % | 100 % for regular rows | OFF-01 p. 103; OFF-13 p. 28; IT-05; DE-05 |
| Partitions in height | 1L: 2; xL: x; xLU: 3x (PDF) or x (help); xP: x; xT: 2x; xTU: x | (none) | (none) | OFF-01 pp. 105-106; 06 §1.1.8 |
| Module Layout size | Warning at 1 MWp, error at 5 MWp | (none) | (none) | OFF-01 p. 111 |
| Horizon validity | Obstacles at least 10 × the field size away; LED above 2°; coordinates to 0.0001° (about 11 m) | Mean horizon 1.9-2.6°, loss 0.45-1.36 % in Italian and German plants | (none) | OFF-01 pp. 60-61; IT-04; IT-07; DE-01 |
| Shading table grid | 10° sun height × 20° azimuth ("fast") | (none) | (none) | OFF-01 p. 67 |
| Gap between PV plane and support | 2-3 cm margin needed | (none) | (none) | OFF-06 p. 14 |
| 3D area tolerance | 8 % for imports; warning when the scene is 1.5 × larger | (none) | (none) | OFF-06 p. 15; OFF-13 p. 23 |
| Weather QC | Daily values within 3-5 % of clear sky; best days Ktcs within 5 %; synthetic runs differ by 0.5-1 % | (none) | (none) | OFF-03 pp. 10, 15, 28 |
| Weather search radius | Nearby file within 20 km | (none) | (none) | OFF-12 p. 8 |
| Tracker GCR and range | (none) | GCR 0.30-0.53; ±45° to ±60°; backtracking limit ±57.6° to ±63.4° | **GCR about 0.45, ±55-60°** (Italian utility) | IT-04/05/06; ZH-20; EN-11 [unverified] |
| Fixed tilt and pitch, ground | Optimisation chart and tool | 25-30° tilt; 4.5-8 m pitch | Site specific | IT-01; IT-02; AR-04; PT-01 |
| Battery | Charging stops at 95 %, discharging at 20 %; full Li-ion charge in no less than 1 h; +10 °C halves static life | Discharge to 20 % | (none) | OFF-01 pp. 51-52; ZH-12 |
| Load CSV | Semicolons; 365-day year; unit in row 2 | Hourly, no gaps, decimal points (EN-15) | (none) | OFF-01 p. 48; EN-15 |
| P50/P90 | Gaussian; yearly only; variability from multi-year data | σ total 6.5-10 %; one report used 0.5 % variability | P90 = P50 - 1.282σ | OFF-01 pp. 46-47; EN-24; EN-25; EN-12; IT-06 |
| Feed-in contract | "Typically 20 years" | (none) | (none) | OFF-01 p. 152 |
| Carbon defaults | PV LCE 46 gCO₂/kWh; transport 35 (sea) and 60 (truck) gCO₂/t/km; IEA grid values from 2010 | (none) | (none) | OFF-01 pp. 158-160 |
| Inverter OND | Pthresh ≥ 0.5 % Pnom; Pnom usually kVA | Efficiency example: maximum 98.2 %, CEC 97.5 % | (none) | OFF-04 pp. 9-13 |
| PAN | Vmpp·Impp within 0.2 % of Pnom | Low-light optimism of manufacturer PANs 1.1-2.9 % | (none) | OFF-04 p. 4; EN-17 |
| Resulting PR | (none) | 78-90.5 % (bifacial and trackers at the top) | **About 80-85 %** | IT-02; IT-04 to IT-07; ES-01; PT-12; PT-13; TR-05; TR-07; EN-24 |
| Specific yield seen | (none) | 966 (Germany) to 1883 (Sicily, tracker) kWh/kWp | (none) | AR-04; IT-02; IT-05; DE-02 |

---

## 4. UX friction points and what a better tool can automate or infer

### 4.1 Friction catalogue

The "Automate or infer" column is analysis. "Meridiana today" follows funzionalita.md.

| # | Friction | Evidence | Automate or infer (analysis) | Meridiana today |
|---|---|---|---|---|
| F1 | **Geometry described twice.** The Orientation and System dialogs and the 3D scene must agree on tilt, azimuth, module count and area. A mismatch turns buttons red and blocks the run. | OFF-01 pp. 62-63; OFF-13 p. 23; ZH-02; video `dQ4tr-zOW20` ("Orientation error handling") | One model: orientations, module count and strings all come from the drawing | ✔ by design (fields drawn; orientations follow) |
| F2 | **Module Layout as a separate final pass.** Any later change to scene or system forces a revision. Manual assignment is "tedious" for large systems. | OFF-01 pp. 107, 124 | Keep strings live: re-string automatically when the layout changes, and keep manual overrides | ✔ (strings drawn automatically per row) |
| F3 | **Import repairs.** DAE in inches; 180° reversal after a SketchUp import; interpenetration check to disable; 8 % area tolerance; one export per orientation; multi-file scenes one at a time. | OFF-06 pp. 12-15, 34; EN-21; EN-S4 | Detect units, north and up axis on import; offset PV faces automatically; accept multi-orientation files | Import ○ |
| F4 | **Draw facing south, then rotate the whole scene.** Selection by edges; mouse placement, then typed values. | OFF-13 pp. 8-10, 19; FR-01 | Draw on a georeferenced orthophoto in true orientation; CAD guides and typed lengths | ✔ (orthophoto, CAD guides, "lunghezza;angolo") |
| F5 | **"Adjust to modules"** order; tables must match modules exactly. | FR-01; OFF-01 pp. 94, 114-115 | Tables always built from module counts | ✔ (layout from modules) |
| F6 | **Default Tmin of -10 °C** gives false string errors in warm sites and is unsafe in mountains. | ZH-02; OFF-12 p. 9; AR-01 | Infer Tmin from site climate (PVGIS/ERA5 daytime minimum), show its source, let the user override | ◐ (Tmin present; source per site not stated in funzionalita) |
| F7 | **Warnings taught as something to hide**; colour codes only. | AR-01 part 1 ("how to hide the warning messages"); OFF-12 p. 13 | Explain each warning, link the standard clause, offer a one-click fix ("Correggi") | ◐ (checks page with sources; "Correggi" ○) |
| F8 | **Linear shading misleads design choices** (tracker strategy, string routing); the electrical fraction is guessed (60-80 %). | ZH-13; OFF-13 p. 28; IT-05 | Electrical model always on; no fraction to guess | ✔ (bypass-diode model per string) |
| F9 | **High-GCR trackers without backtracking go unnoticed.** | IT-04 (analysis) | Warn when GCR > ~0.4 and backtracking is off | Trackers ○ |
| F10 | **Settings scattered across project settings, variant dialogs and global advanced parameters** (not saved with the project). | OFF-01 pp. 11, 13-14; 06 §1.1.1.5 | Per-project settings with provenance; nothing hidden that changes results | ✔ (only changed values saved; pedigree) |
| F11 | **Sub-array settings not propagated** (wiring loss must be applied to all sub-arrays). | ZH-06 | Loss settings per project with per-field overrides shown explicitly | (analysis: verify in Meridiana) |
| F12 | **Batch quirks**: albedo variation ignored when monthly is ticked; tilt variation does not move the 3D geometry; multi-year output through the UserHourly folder. | ZH-05; ZH-14 | Parametric studies recompute geometry; one results table | Batch ○; sizing sweep ◐ |
| F13 | **Version drift breaks comparisons**: IAM default (6.67), AC reference (7.2), PR_Bifi (8.0.12), ageing split (8.0); a report printed by 7.2.16 contains a 6.8.8 simulation. | ZH-17; FR-04; ZH-08; IT-05 | Stamp each result with engine version and model set; warn when re-opening older results | ✔ partly (pedigree per step); version stamp (analysis: check) |
| F14 | **Official documents disagree** (overload limit 3 % or 4 %; xLU 3x or x; electrical fraction; module quality). | Section 1.3 | Defaults documented once, with date and source | ✔ (pedigree, norm and page) |
| F15 | **Weather import traps**: wrong format; GHI mandatory; one year per file; UTC or local time; label at start of interval; clearness limits in hidden parameters; synthetic randomness 0.5-1 %; regenerate files after changing source. | OFF-03; EN-01 to EN-04; ZH-03; ZH-07 | Auto-detect format, time zone and labelling; run QC (clear-sky, Ktcs, time shift) and show it; deterministic TMY | PVGIS ✔; others ○; QC ○ |
| F16 | **Load CSV errors**: semicolons, 365 days, unit row, kVA instead of kW; self-consumption rate computed by hand. | OFF-01 p. 48; ES-06; EN-15 | Tolerant importer (portals, 15-min, kW or kWh); self-consumption and self-sufficiency rates computed | ✔ |
| F17 | **Hybrid or all-in-one storage** cannot be entered; tariff-driven dispatch missing; power shifting excludes self-consumption. | ES-06; IT-01; OFF-01 p. 52 | Storage as one component with DC or AC coupling; dispatch by ARERA time bands or GME prices | ✔ storage basics; DC coupling ○; time-band dispatch ○ |
| F18 | **Economics outside PVsyst** for national schemes (Italy, Brazil, Germany). | IT-02; PT-04; DE-03; EN-14 | Built-in national schemes | ✔ (Italian schemes) |
| F19 | **P50/P90 inputs unchecked** (0.5 % variability accepted). | IT-06; EN-24 | Sanity ranges per term; show σ composition | ○ |
| F20 | **Terrain**: Google Earth to GPS Visualizer to Excel to CSV (12 steps); heavy meshes take hours; the v8 download is limited to 11 × 11 km. | OFF-05; ZH-10 | DEM or DSM fetched by coordinates, simplified automatically | ○ |
| F21 | **Agrivoltaics, carports, east-west or dome bifacial**: no tool, only workarounds. | EN-22; EN-34; ES-01/02 | Ground irradiance map; carport object; bifacial from the 3D scene | ○ |
| F22 | **Learning curve.** "requiere un mayor conocimiento y tiempo"; "nem todas as suas ferramentas são intuitivas"; "still difficult to use"; PVsystBasic exists for pumping only. | ES-01; PT-18; EN-44; W-04 | Guided first project; defaults that compute immediately | ✔ (computes with defaults from the start) |
| F23 | **Windows-only, single user; PAN files copied into versioned folders.** | PT-06; 06 | Cross-platform; component copied into the project | ✔ (Linux and Windows; component copied into project) |
| F24 | **Translations and fonts**: translated reports carry a "without guarantee" disclaimer; Chinese reports need a specific font. | DE-03; ZH-06 | Native-language reports with embedded fonts | ✔ (Italian interface and report) |
| F25 | **Owners still require a PVsyst model "as bid"**; vendors build PVsyst exporters and connectors. | EN-09; EN-44; OFF-06 (vendor exporters) | Export to PVsyst (PVC or PVCollada scene, PAN and OND, settings sheet) | ○ (analysis: add to plan) |

### 4.2 What to automate or infer, by priority (analysis)

Priorities weigh the evidence of user pain in 4.1 against the effort in Meridiana's current architecture. They are proposals for Daniel, not decisions.

1. **Keep the single-model advantage (F1-F5) and make it visible.** Show users the checks PVsyst makes them do by hand: orientation match, module count, area, strings complete. Present them as "always consistent" badges, not as errors to fix.
2. **"Correggi" on every check (F7).** The tutorials show beginners learning to ignore or hide warnings. A fix button with the norm reference turns warnings into teaching. funzionalita already lists this as next step 1.
3. **Input sanity rules drawn from section 3 (F9, F13, F19).** Examples:
   - Uc 20 on free-standing rows;
   - P50/P90 variability below 2 %;
   - trackers at high GCR without backtracking;
   - soiling 0 % on a low-tilt industrial roof;
   - DC/AC above 1.4 without clipping review.

   Each rule cites its source, which fits the pedigree principle.
4. **Weather QC and other formats (F15).** Port PVsyst's taught checks: the clear-sky envelope, Ktcs on the best days, a time-shift estimate. Then add other formats (Meteonorm, EPW, Solcast or Solargis CSV) through one auto-detecting importer.
5. **PVsyst export (F25).** Write a PVC or PVCollada scene, the PAN and OND files, and a parameter sheet that lists every value in PVsyst's vocabulary. This lets Daniel hand a Meridiana design to a client, owner or lender who insists on PVsyst. It also gives a cross-check against PVsyst on the same geometry.
6. **Agrivoltaic and carport objects (F21).** Use the Italian MASE 2022 guideline indices for agrivoltaics. The 3D engine already computes shading; a ground-irradiance map is the missing output.
7. **Validation cases from the tutorials (F8).** Reproduce:
   - OFF-01's 3-strings-per-MPPT case (85 %);
   - the 37.2 % module example;
   - ZH-16 (half-cut cells);
   - ZH-13 (tracker strategy), once trackers exist.

   Put them in the test suite with their sources.
8. **Variant comparison (F13, F14).** PVsyst's teaching method is "add one perturbation, save a variant, compare loss diagrams" (OFF-12). Meridiana's revisions exist; a side-by-side loss-diagram comparison would match this habit.

---

## 5. Checklist: tutorial steps mapped to Meridiana

**How to read the table.**
- Status comes from `docs/funzionalita.md` (22/10/2026): **exists** ✔, **partial** ◐, **missing** ○.
- Where funzionalita.md does not mention a step, the status is marked "(analysis)".
- "Section" points to the funzionalita.md section (A to M).
- The "Tutorial step" column uses PVsyst's own dialog names.

| # | Tutorial step (PVsyst dialog) | Taught in | Meridiana | Section, note |
|---|---|---|---|---|
| **Project and site** | | | | |
| 1 | New project; site from map or coordinates | 2.0; OFF-01 p. 15 | exists ✔ | A: Nominatim, Italian-style coordinates |
| 2 | Site altitude and time zone | OFF-03 p. 7 | exists ✔ | A: altitude from PVGIS; B: Italian time conventions |
| 3 | Weather from a provider at site creation | OFF-01 p. 16 | partial ◐ | B: PVGIS 5.3 TMY ✔; Meteonorm, Solcast, Solargis and NASA POWER ○ |
| 4 | Project settings: far albedo (yearly or monthly) | OFF-12 p. 8 | partial ◐ | C: yearly ✔, monthly ○ |
| 5 | Design conditions: Tmin for Voc max | OFF-01 p. 27 | exists ✔ | A, I: Tmin for strings |
| 6 | Design conditions: maximum temperature and overload loss limit | OFF-01 p. 13 | partial ◐ | A: overload limit missing |
| 7 | Client data on the report | OFF-01 p. 13 | missing ○ (analysis) | Not listed |
| 8 | Save project; variants VC0, VC1, ... with "Save As" | OFF-12 pp. 6, 19 | partial ◐ | A: revisions _Rnn ✔; variants in one project ○ |
| 9 | Demo projects | OFF-01 p. 11 | missing ○ | A |
| 10 | Pre-sizing (quick monthly estimate) | OFF-01 p. 11 | missing ○ | A |
| **Orientation and mounting** | | | | |
| 11 | Fixed tilted planes, several orientations | 2.0 step 6 | exists ✔ | D |
| 12 | Orientation optimisation chart (tilt and azimuth against optimum) | OFF-01 p. 18 | missing ○ | D: tilt optimisation ○ |
| 13 | Unlimited sheds (2-D mutual shading, GCR, limit angle) | 2.3 | exists ✔ | D: CEI 82-25/3 §6.2 pitch |
| 14 | Domes and east-west | 2.6 | exists ✔ | D: east-west pairs |
| 15 | Seasonal tilt | OFF-01 p. 19 | missing ○ | D (phase 3) |
| 16 | Base slope and tables following terrain | OFF-01 pp. 18, 74 | missing ○ | D |
| 17 | Single-axis trackers, backtracking, wind stow, irradiance optimisation | 2.4 | missing ○ | D (phase 2) |
| 18 | Two-axis and vertical-axis trackers | OFF-01 pp. 22-23 | missing ○ | D (phase 3) |
| 19 | Carport | 2.7 | exists ✔ | D: "pensilina" |
| 20 | Sun-shields and façades | OFF-01 pp. 20, 22 | missing ○ | D: façade ○ |
| **System** | | | | |
| 21 | Pre-sizing help by power or area | OFF-01 p. 26 | exists ✔ | I: automatic inverter and strings; J: sizing sweep |
| 22 | Module and inverter choice from the database | OFF-12 p. 12 | exists ✔ | L: 73 + 16,886 modules; 94 + 2,343 inverters |
| 23 | Sizing tool: I/V curve in the MPPT window | OFF-01 p. 27 | partial ◐ | I: CEI checks ✔; graphical I/V view ○ (analysis) |
| 24 | Overload distribution graph and DC/AC | OFF-01 p. 28 | partial ◐ | I: ratio ✔, histogram ○ |
| 25 | Multi-MPPT, power sharing | OFF-01 pp. 28-30 | partial ◐ | I: string-to-MPPT map ✔; power sharing not listed (analysis) |
| 26 | Two orientations on one MPPT | OFF-01 p. 26 | missing ○ | D |
| 27 | Optimizers | 06 §1.1.10 | missing ○ | H: data present |
| 28 | Microinverters | (none) | exists ✔ | L: 31 from datasheets |
| **Horizon** | | | | |
| 29 | Horizon from PVGIS (web) | 2.11 | exists ✔ | B, F |
| 30 | Horizon drawn by hand or imported (CSV, .HOR, SunEye, Meteonorm) | 2.11 | missing ○ (analysis) | Not listed |
| 31 | Far shading on beam and diffuse | OFF-13 p. 28 | exists ✔ | F |
| **3D near shading** | | | | |
| 32 | Ground image, map | OFF-01 p. 96; OFF-05 | exists ✔ | F: 2012 national orthophoto, OSM |
| 33 | Building, roof, PV planes drawn | 2.1 | exists ✔ | F: roofs, CAD guides |
| 34 | Ridge, eave and hip from an edge; dormers | (none) | missing ○ | F |
| 35 | Elementary objects: trees, chimneys, silos, with heights | OFF-13 pp. 17-19 | exists ✔ | F: heights by type, editable |
| 36 | Field zones, fill zone, exclusion zones | OFF-01 pp. 91-96 | exists ✔ | F: automatic layout with VVF rules and setbacks |
| 37 | Add or remove a module or table | OFF-01 pp. 95-96, 114 | exists ✔ | F |
| 38 | List and manage objects (Ctrl+G), CSV and Excel round-trip | OFF-01 pp. 79-80 | missing ○ (analysis) | Not listed |
| 39 | Measure distance and angle | OFF-01 p. 91 | exists ✔ | F: measures beside the cursor |
| 40 | Copy, array, mirror | OFF-01 p. 73 | missing ○ | F |
| 41 | Import 3D scenes (DAE, 3DS, PVC, H2P) | 2.2 | missing ○ | F |
| 42 | Terrain from satellite or DEM; Google Earth route | 2.3 | missing ○ | F |
| 43 | Shading animation for a day; sun view (F6); video export | OFF-01 p. 99 | partial ◐ | F: animation ✔, sun view ○ |
| 44 | Shading-factor table; iso-shading diagram | OFF-01 pp. 66-68 | partial ◐ | F: table ✔, diagram ○ |
| 45 | Linear shading on beam, diffuse and albedo | OFF-01 p. 64 | partial ◐ | F: albedo shading ○ |
| 46 | Partial shading calculation for big scenes; representative tracker | OFF-01 pp. 76-78, 86-88 | missing ○ (analysis) | Not needed until trackers and utility scale |
| **Electrical shading and strings** | | | | |
| 47 | Partitions, "according to module strings", electrical fraction | 2.19 | exists ✔ (different model) | F: bypass-diode model; partitions deliberately not used |
| 48 | Module Layout: mechanical and electrical definition | 2.18 | exists ✔ | I: strings drawn; F: cell blocks per module |
| 49 | Automatic string assignment strategies | OFF-01 pp. 118-124 | partial ◐ | I: row-by-row serpentine ✔; alternative strategies (U, over tables, same row per MPPT) not listed (analysis) |
| 50 | String wiring printout for the site | OFF-01 p. 128 | partial ◐ | K: strings in the PDF report ✔; DXF export with strings ○ |
| 51 | I/V curves per module or MPPT (learning tabs) | OFF-01 pp. 128-132 | missing ○ (analysis) | Not listed |
| 52 | Thin objects (cables, fences) | OFF-01 p. 75 | missing ○ (analysis) | Not listed |
| **Detailed losses** | | | | |
| 53 | Thermal Uc/Uv by mounting | OFF-01 p. 31 | exists ✔ | G |
| 54 | Thermal transient model; measured array temperature | OFF-07 p. 13; 06 | missing ○ | G |
| 55 | DC wiring (1.5 % STC or detailed lengths) | OFF-01 p. 32 | exists ✔ (loss); sizing aid ○ | H |
| 56 | AC wiring; transformers MV and HV; night disconnect | OFF-01 pp. 32-34 | partial ◐ | H: AC ✔; transformers ○ |
| 57 | Module quality, LID, mismatch | OFF-01 pp. 34-35 | exists ✔ | H |
| 58 | Soiling yearly, monthly, CSV; snow | 2.24 | partial ◐ | H: yearly ✔; monthly, series, snow ○ |
| 59 | IAM: Fresnel, user profile, from PAN | OFF-01 pp. 36-37 | partial ◐ | G: ASHRAE ✔; Fresnel, user and PAN profile ○ (next step 4 in funzionalita) |
| 60 | Auxiliaries | OFF-01 pp. 37-38 | missing ○ | H |
| 61 | Ageing tab (simulation year, Monte-Carlo mismatch) and Aging Tool | 2.15 | partial ◐ | H: in cash flows only |
| 62 | Unavailability | 2.22 | exists ✔ | H |
| 63 | Spectral correction | 2.26 | missing ○ | G |
| 64 | Losses graph (I/V per loss effect) | OFF-01 pp. 40-41 | missing ○ (analysis) | Not listed |
| **Energy management** | | | | |
| 65 | Inverter temperature model and derating | OFF-01 pp. 42-43 | missing ○ | I |
| 66 | Power factor (cos φ), kVA limits | OFF-01 pp. 43-45 | missing ○ | I |
| 67 | Grid power limitation (inverter or injection point; separate loss) | 2.10 | exists ✔ | I: zero export too; clipped energy shown |
| 68 | P50/P90 | 2.14 | missing ○ | K |
| **Self-consumption and storage** | | | | |
| 69 | Load: constant, monthly, daily profiles, appliances, CSV | 2.9 | exists ✔ | J: CSV from portals, bills, 10 profiles, automatic |
| 70 | Self-consumption results | 2.9 | exists ✔ | J: hourly self-consumption, injection, withdrawal |
| 71 | Battery pack and self-consumption strategy | 2.9 | exists ✔ | J (phase 2 done) |
| 72 | Battery ageing (cycles, static, temperature) | OFF-01 pp. 50-51 | missing ○ | J |
| 73 | Peak shaving; power shifting; weak grid | OFF-01 pp. 52-59 | missing ○ | J: zero export, peak shaving, time-band discharge ○ |
| **Weather data** | | | | |
| 74 | Known-format and custom imports; 8.1 assistant | 2.12 | missing ○ | B |
| 75 | Tables and graphs | OFF-03 pp. 12-15 | partial ◐ | B |
| 76 | Quality checks (clear-sky, Ktcs, time shift) | OFF-03 pp. 27-28 | missing ○ | B |
| 77 | Multi-year series, compare weather data | OFF-01 p. 47 | missing ○ | B |
| 78 | Sub-hourly simulation | 06 §1.1.14.3; OFF-07 | missing ○ (analysis) | Not listed (Perez sub-hourly coefficients ○ in C) |
| **Simulation, results and report** | | | | |
| 79 | Run simulation (hourly) | 2.0 step 9 | exists ✔ | K |
| 80 | Results dialog: key values; daily input/output diagram | OFF-12 p. 15 | partial ◐ (analysis) | K: monthly results ✔; daily input/output diagram not listed |
| 81 | Report with loss diagram, PR, normalised yields | 2.17 | exists ✔ | K: PDF with LaTeX pedigree |
| 82 | Report options: logo, units, compare variants | OFF-12 p. 31; video `OenFkw3P_3Y` | partial ◐ (analysis) | Comparison ○ (K) |
| 83 | Hourly CSV output | ZH-01; OFF-07 | missing ○ | K: CSV export of hourly series ○ |
| 84 | Optimisation tool, batch simulations | 2.13 | missing ○ | K |
| 85 | PVGIS cross-check | (not in PVsyst) | exists ✔ | K: PVGIS PVcalc month by month |
| **Economics and other** | | | | |
| 86 | Economic evaluation (costs, finance, tariffs, NPV, IRR, LCOE) | 2.16 | exists ✔ | K: Italian schemes |
| 87 | Carbon balance | 2.16 | missing ○ | K (phase 3) |
| 88 | Components from datasheets (PAN, OND) | 2.27 | exists ✔ | G, L |
| 89 | User components, favourites, prices in database | OFF-04 p. 7 | missing ○ | L |
| 90 | Stand-alone and pumping projects | 2.28 | missing ○ | M (phase 3) |
| 91 | Measured-data comparison | OFF-01 p. 10 | missing ○ | K (phase 3) |
| 92 | Export to PVsyst for lenders | 4.1 F25 | missing ○ (analysis) | Not listed |

**Count.** Of the 92 steps:

| Status | Steps |
|---|---|
| Exists ✔ | 33 |
| Partial ◐ | 19, of which 2 are judged by analysis |
| Missing ○ | 40, of which 9 are marked "(analysis)" because funzionalita.md does not mention them |

(analysis) The missing steps cluster in four areas, matching phase 2 of the parity matrix in 06:
- trackers and terrain;
- weather beyond PVGIS;
- transformers, power factor and P50/P90;
- comparison and batch.

**Note on funzionalita.md** (analysis). Section D says the 2-D row model has "Effetto elettrico ○". Section F says the electrical string model also covers row-to-row shading ✔. The row in D may be out of date.

---

## 6. Sources

All URLs were accessed between 21 and 22 October 2026.

**Dates.** Dates are publication or last-update dates as shown by the source. Formats:
- dd/mm/yyyy or yyyy-mm-dd: the full date is known;
- month and year, or the year alone: only that is known;
- "undated": no date found.

**Versions.** "inferred" means the PVsyst version was deduced from screenshots, text or dates.

### 6.1 Official PDF tutorials (PVsyst SA)

Base URL: `https://www.pvsyst.com/pdf/pdf-tutorials/`. Each English file has a French twin, with `-fr` in place of `-en`. Section 1.1 gives dates, page counts and scope.

| ID | Path | Archived locally |
|---|---|---|
| OFF-01 | pvsyst-8.1/pvsyst-tutorial-v8-1-grid-connected-en.pdf | yes (EN, FR) |
| OFF-02 | pvsyst-8/pvsyst-tutorial-v8-grid-connected-en.pdf | yes |
| OFF-03 | pvsyst-8/pvsyst-tutorial-v8-meteorological-data-en.pdf | yes |
| OFF-04 | pvsyst-8/pvsyst-tutorial-v8-components-database-en.pdf | yes |
| OFF-05 | pvsyst-8/pvsyst-tutorial-v8-import-topography-en.pdf | yes |
| OFF-06 | pvsyst-8/pvsyst-tutorial-v8-export-3d-scene-to-pvsyst-en.pdf | yes |
| OFF-07 | pvsyst-8/pvsyst-tutorial-v8-pseudo-sub-hourly-simulation-en.pdf | yes |
| OFF-08 | pvsyst-8/pvsyst-tutorial-v8-stand-alone-en.pdf | yes |
| OFF-09 | pvsyst-8/pvsyst-tutorial-v8-stand-alone-with-batteries-en.pdf | yes |
| OFF-10 | pvsyst-8/pvsyst-tutorial-v8-pumping-system-en.pdf | yes |
| OFF-11 | pvsyst-8/pvsyst-tutorial-v8-pumping-over-the-sun-en.pdf | yes |
| OFF-12 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-1-en.pdf | yes |
| OFF-13 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-2-en.pdf | yes |
| OFF-14 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-3-en.pdf | no (superseded) |
| OFF-15 | pvsyst-7/pvsyst-tutorial-v7-grid-connected-4-en.pdf | no |
| OFF-16 | pvsyst-7/pvsyst-tutorial-v7-ground-and-topography-en.pdf | no |
| OFF-17 | pvsyst-7/pvsyst-tutorial-v7-export-to-pvsyst-en.pdf | no |
| OFF-18 | pvsyst-7/pvsyst-tutorial-v7-standalone-en.pdf | no |
| OFF-19 | pvsyst-7/pvsyst-tutorial-v7-pumping-1-en.pdf | no |
| OFF-20 | pvsyst-7/pvsyst-tutorial-v7-pumping-2-en.pdf | no |
| OFF-21 | pvsyst-6/pvsyst-tutorial-v6-grid-connected-en.pdf | no |

Local archive: `l'archivio locale delle norme\publications\pvsyst\tutorial-ufficiali\`, with `README.md` (26 PDFs, SHA-256 checksums).

### 6.2 Official web pages

| ID | Page | URL |
|---|---|---|
| W-01 | PDF tutorials (EN, FR, ES) | https://www.pvsyst.com/en/training/pdf-tutorials , https://www.pvsyst.com/fr/training/pdf-tutorials , https://www.pvsyst.com/es/training/pdf-tutorials |
| W-02 | Video tutorials (Flockler embeds of the YouTube channel) | https://www.pvsyst.com/en/training/video-tutorials |
| W-03 | Consulting (CHF 700 per 2-hour session) | https://www.pvsyst.com/en/training/consulting |
| W-04 | PVsystBasic product page | https://www.pvsyst.com/en/products/pvsyst-basic |
| W-05 | PVsystBasic help | https://www.pvsyst.com/help-basic/ |
| W-06 | Release notes (8.0.12 PR_Bifi; 8.0.15 averaged orientation on import; 8.0.20 new PDF tutorials; 8.1.2 ground-albedo CSV; 8.1.6 legacy import removed) | https://www.pvsyst.com/help/release-notes/index.html |
| W-07 | robots.txt (disallows /api/) and sitemap | https://www.pvsyst.com/robots.txt , https://www.pvsyst.com/sitemap.xml |
| W-08 | Help search index used by 06, re-used for cross-checks | https://www.pvsyst.com/help/search/search_index.json |

### 6.3 Official videos

**Channels**:
- main: https://www.youtube.com/@PVsystOfficial ; feed https://www.youtube.com/feeds/videos.xml?channel_id=UCMzsEWHk3f7XD_dg1lngmzg
- French: https://www.youtube.com/@pvsystofficial-fr
- Spanish: https://www.youtube.com/@pvsystofficial-es
- Chinese: https://www.youtube.com/@pvsystofficial-cn

Appendix A lists all 102 videos of the main channel with dates, lengths, views, playlists and chapter lists. Videos cited in the text are linked where cited.

### 6.4 Third-party sources

**English** (44 sources plus 8 seen only as search snippets)

| ID | Title | URL | Country | Date | Type | PVsyst |
|---|---|---|---|---|---|---|
| EN-01 | Solargis data in PVsyst | https://kb.solargis.com/docs/solargis-data-in-pvsyst | SK | 2026-07-16 | vendor KB | tested on 7.1 |
| EN-02 | Solcast: PVsyst | https://kb.solcast.com.au/pvsyst | AU | undated | vendor KB | "current as of 7.4" |
| EN-03 | Vaisala: input CSV files into PVsyst | https://energy.vaisala.com/en/support/solar-online-tools/how-do-i-input-csv-files-pvsyst | FI/US | undated | vendor FAQ | 6.79+ |
| EN-04 | Vaisala/3TIER: time series into PVsyst | https://a2.energy.vaisala.com/en/support/solar-online-tools/how-can-i-input-time-series-data-pvsyst/ | FI/US | undated | vendor FAQ | 6.x (inferred) |
| EN-05 | PV Lighthouse: PVsyst bifacial inputs with SunSolve | https://downloads.pvlighthouse.com.au/white-papers/pvsyst-factors/Info0030%20-%20Extracting%20PVSyst%20inputs%20with%20SunSolve.pdf | AU | 2024 | white paper (39 p.) | 7.4.6 |
| EN-06 | CSA Group (K. Lee), Performance modeling and testing of bifacial PV | https://www.firstsolar.com/-/media/First-Solar/Technical-Documents/Bifacial-Documents/CSA_Performance-Modeling-and-Testing-of-Bifacial-PV-Systems_Kyumin-Lee.ashx?la=en | US | 2019-07-03 | slides | 6.7.5 |
| EN-07 | pv magazine India, All about albedo | https://www.pv-magazine-india.com/2020/01/25/the-long-read-all-about-albedo/ | DE/IN | 2020-01-25 | article | n/a |
| EN-08 | pv magazine webinar Q&A on bifacial modelling | https://www.pv-magazine.com/2019/11/27/webinar-qa-performance-modelling-for-accurate-energy-output-and-yield-prediction-of-bifacial-pv-systems/ | intl | 2019-11-27 | Q&A | n/a |
| EN-09 | Entergy Arkansas, Solar BOT Scope Book, Appendix 4 Energy Model | https://entergyarkansas.com/wp-content/uploads/2025/06/Appendix-B-2-Solar-BOT-Scope-Book-Appendix-4-Energy-Model.docx | US | Rev. 0 2023-09-14, posted 2025-06 | owner RFP template | "as bid" |
| EN-10 | E3 Consulting podcast, PVsyst series | https://www.buzzsprout.com/1361503/episodes | n/a | 2025-04/05 | podcast notes | n/a |
| EN-11 | SurgePV, solar backtracking | https://www.surgepv.com/blog/solar-backtracking | n/a | 2026-06-30 | competitor blog | n/a |
| EN-12 | SurgePV hub, energy simulation | https://surgepv.com/hub/solar-designing/energy-simulation/ | n/a | 2026-03-13 | competitor guide | n/a |
| EN-13 | SurgePV, bankable PVsyst reports | https://www.surgepv.com/blog/pvsyst-report-bankability-guide | n/a | 2026-07-19 (upd. 09-30) | competitor blog | n/a |
| EN-14 | Keentel Engineering, PVsyst v8 grid-connected guide | https://www.keentelengineering.com/pvsyst-v8-grid-connected-solar-simulation-guide | US | 2025-08-06 | consultancy blog | 8 |
| EN-15 | AmpX, solar self-consumption analysis (blog and video) | https://ampx.co/solar-self-consumption-analysis/ ; https://www.youtube.com/watch?v=2dyp38A4zEc | ZA/DE | 2026-06-10; 2025-06-12 | tutorial | 8 |
| EN-16 | Anza, PAN files explained | https://www.anzarenewables.com/blog/solar-pv-pan-files-explained/ | US | 2023-03-07 | blog | n/a |
| EN-17 | Kiwa PVEL, PAN and IAM testing | https://www.kiwa.com/pvel/pqp/pan-iam | US | undated | lab page | 6.83+ PAN |
| EN-18 | Black & Veatch, PAN file creation (PVPMC 2013) | https://pvpmc.sandia.gov/download/4600 | US | 2013-05-01 | workshop deck | 5/6 |
| EN-19 | PVcase blog, PVcase Yield vs PVsyst losses | https://pvcase.com/blog/precision-in-solar-simulations-pvcase-yield-and-pvsyst-loss-calculations | LT | 2026-06-02 | vendor blog | n/a |
| EN-20 | Glint Solar KB, losses vs PVsyst | https://knowledgebase.glintsolar.com/en/article/losses-in-glint-solar-vs-losses-in-pvsyst | NO | undated | vendor KB | 7/8 (inferred) |
| EN-21 | Arka360, PVsyst 3D scene import | https://help.arka360.com/en/articles/5916042-pvsyst-3d-scene-import | IN | 2025-12-10 | vendor help | n/a |
| EN-22 | Zainali et al., shading factors for agrivoltaic layouts | https://arxiv.org/abs/2208.04886 | SE/IT | 2022-08-09 | preprint | n/a |
| EN-23 | Solar Power World, soiling losses in EPC and O&M | https://www.solarpowerworldonline.com/?p=110949 | US | 2025-09-25 | trade article | n/a |
| EN-24 | IEA PVPS T13-18:2020, uncertainties in yield assessments (summary) | https://iea-pvps.org/wp-content/uploads/2021/01/Executive-Summary-IEA-PVPS-T13-18_2020-Uncertainties-in-Yield-Assessments-and-PV-LCOE.pdf | intl | 2020-11 | report | n/a |
| EN-25 | Solargis, how to calculate P90 | https://solargis.com/blog/best-practices/how-to-calculate-p90-or-other-pxx-pv-energy-yield-estimates | SK | 2025-09-24 | blog | n/a |
| EN-26 | Solargis KB, unavailability and degradation | https://kb.solargis.com/docs/system-unavailability-losses-long-term-degradation | SK | 2026-07-23 | KB | n/a |
| EN-27 | Sandia PVPMC, PVsyst cell temperature model | https://pvpmc.sandia.gov/?p=396 | US | undated | modelling guide | defaults |
| EN-28 | PVsyst staff at PVPMC 2017, tracking simulation | https://pvpmc.sandia.gov/download/4301 | CH | 2017-12 | deck | 6.6 |
| EN-29 | PVsyst staff at PVPMC 2022, electrical shading | https://pvpmc.sandia.gov/download/3803 | CH | 2022-08 | deck | 7.2 |
| EN-30 | Electronic Clinic, PVsyst getting started | https://www.electroniclinic.com/pvsyst-software-getting-started-tutorial/ | PK | 2021-09-26 | blog tutorial | 6.79 |
| EN-31 | Solar Energy International, CE524 | https://solarenergytraining.org/course/info.php?id=1095 | US | undated | course page | n/a |
| EN-32 | UiTM, stand-alone PV with PVsyst (synopsis) | https://solar.uitm.edu.my/wp-content/uploads/2024/03/Synopsis-SAPV-using-PVsyst.pdf | MY | 2024-03-11 | course synopsis | 7.0+ |
| EN-33 | Consulting Technical Solutions, two complete tutorials | https://www.youtube.com/watch?v=w6VfdiLdqDI ; https://www.youtube.com/watch?v=1DdtNVs78dE | n/a | 2025-07-20; 2024-08-19 | video | 7.4.8 |
| EN-34 | Miss Monney, domed bifacial with two fixed orientations | https://www.youtube.com/watch?v=5hPAfHoWKpU | n/a | 2026-08-01 | video | 8.1 |
| EN-35 | Laxmikant Radkar, batch simulations for bifacial | https://www.youtube.com/watch?v=IjMr59-kisU | IN | 2024-12-15 | video | 8.0 |
| EN-36 | Pouria Ahmadi, urban 3D shading (3 videos) | https://www.youtube.com/watch?v=hyVYoOch2Nc ; https://www.youtube.com/watch?v=04VqgBeVSzg ; https://www.youtube.com/watch?v=21dos8T6Ky8 | n/a | 2024-12 to 2026-06 | video | n/a |
| EN-37 | TechBurst Solutions, SketchUp import and weather choice | https://www.youtube.com/watch?v=OszWwipCrV0 ; https://www.youtube.com/watch?v=kTe6FizXb8A | n/a | 2025-01 | video | n/a |
| EN-38 | SWS Realty, tracker with bifacial in 20 minutes | https://www.youtube.com/watch?v=x-LRzh9f6pg | n/a | 2022-01-04 | video | 7 (inferred) |
| EN-39 | Huawei FusionSolar with SKE Engineering, bifacial webinar | https://www.youtube.com/watch?v=Pk2OC6gF890 | GR | 2020-08-04 | webinar | n/a |
| EN-40 | Solar Design and Engineering85, LID and PR for P50/P75/P90 | https://www.youtube.com/watch?v=hzcolxpSaMk ; https://www.youtube.com/watch?v=Y5OtBJ0SdSU | n/a | 2026-06/07 | video | n/a |
| EN-41 | Minutes 2 Energy, importing NASA and PVGIS data | https://www.youtube.com/watch?v=elwW9ehCyT8 | IN | 2020-06-28 | video | 7.0 |
| EN-42 | EEE@IUB university workshop | https://www.youtube.com/watch?v=AGEdjr0etR0 | BD | 2020-08-31 | workshop | n/a |
| EN-43 | Govind Soni, single-axis tracking | https://www.youtube.com/watch?v=XFyOl67l6us | IN | 2020-05-22 | video | 6/7 (inferred) |
| EN-44 | Reslink Energy, PVsyst Connector | https://www.youtube.com/watch?v=kWlcBDOoQ5s | n/a | 2026-10-16 | product video | n/a |

Seen only as search snippets (all [unverified]):
- EN-S1, Tigo: https://support.tigoenergy.com/hc/en-us/articles/215348938--GUIDE-Modeling-Tigo-in-PVsyst
- EN-S2, RatedPower: https://knowledgebase.ratedpower.com/how-to-upload-a-pvcollada-tracker-scene-to-pvsyst
- EN-S3, PVcase help: https://help.pvcase.com/en/articles/7936074-exporting-fixed-tilt-frames-to-pvsyst
- EN-S4, HelioScope: https://help-center.helioscope.com/hc/en-us/articles/4465905757843-HelioScope-vs-PVsyst
- EN-S5, GSES: https://www.gses.com.au/?p=15805
- EN-S6, GUtech: https://www.gutech.edu.om/master-pvsyst-design-level-3-solar-pv-simulations
- EN-S7, uOttawa TOP-SET: https://top-set.uottawa.ca/Program/2020-Summer-School
- EN-S8, ARRAY Technologies: https://arraytechinc.com/resource/realistic-parameters-for-bifacial-modeling/

**Italian** (9)

| ID | Title | URL | Date | Type | PVsyst |
|---|---|---|---|---|---|
| IT-01 | Bentivenga, Modelling di sistemi fotovoltaici con accumulo per applicazioni utility scale (Univ. Bologna) | https://amslaurea.unibo.it/id/eprint/38565/1/Tesi_Giuseppe_Bentivenga.pdf | A.A. 2024/25 (PDF 2026-03-15) | MSc thesis | 7.4 or 8.0 (inferred) |
| IT-02 | Casaccia, bifacial modules on fixed and tracking structures (UNIVPM) | https://tesi.univpm.it/bitstream/20.500.12075/20942/1/Tesi%20Alanis%20Casaccia.pdf | A.A. 2023/24 (PDF 2025-02-07) | MSc thesis | 7.x (inferred) |
| IT-03 | Zanella, impianti in bassa tensione e autoconsumo collettivo (Univ. Bologna) | https://amslaurea.unibo.it/id/eprint/27701/ | 2023-02-03 | MSc thesis (abstract) | n/a |
| IT-04 | "Favara 1" agrivoltaic plant, yield report (VIA) | https://va.mite.gov.it/File/Documento/982964 | 2024-01-28 | permitting report with PVsyst annex | 7.4.5 |
| IT-05 | Calapricello solar park, yield and balances (VIA) | https://va.mite.gov.it/File/Documento/806253 | 2022-07-07 (simulation 2020-12-23) | permitting report | 7.2.16 print of a 6.8.8 run |
| IT-06 | "STMG 4" Poggio Imperiale, yield (VIA) | https://va.mite.gov.it/File/Documento/823985 | 2022-12-02 | permitting report with P50-P90 | 7.2.21 |
| IT-07 | Ramacca agrivoltaic plant, yield (VIA) | https://va.mite.gov.it/File/Documento/896146 | 2023-07 | permitting report | 7.3.4 |
| IT-08 | PoliTo thesis 12356, sensitivity on 50 configurations | https://webthesis.biblio.polito.it/12356/1/tesi.pdf | A.A. 2018/19 | thesis (snippet only) | unknown |
| IT-09 | VIA yield report computed with PVGIS only (contrast case) | https://va.mite.gov.it/File/Documento/593419 | 2020-2021 | permitting report | none |

**French** (13)

| ID | Title | URL | Date | Type | PVsyst |
|---|---|---|---|---|---|
| FR-01 | Villoz (Dynatex), Utilisation de PVsyst pour l'étude de systèmes couplés au réseau (GIZ/ANME course) | https://energypedia.info/images/3/3a/PVraccord%C3%A9_au_r%C3%A9seau_Electrique.pdf | 2015-05-30 | course slides, full worked case | 6.x |
| FR-02 | GIZ/ANME PVsyst course, Sfax | https://energypedia.info/wiki/Article_sur_la_formation_PVSyst | 2015-10 | course programme | n/a |
| FR-03 | NEPSEN, Photovoltaïque: estimation de la production, PVSYST | https://www.actu-environnement.com/formations-professionnelles/photovoltaique-estimation-production-pvsyst-42140.html | undated | syllabus | n/a |
| FR-04 | SMA France, Concevoir son projet avec PVsyst: 3 choses à savoir | https://www.sma-sunny.com/fr/concevoir-son-projet-avec-pvsyst-3-choses-a-savoir-pour-une-utilisation-optimale-du-logiciel/ | 2021-05-27 | vendor blog | 7.2.1 |
| FR-05 | CEED Burkina Faso, FORMATION PVSYST episodes 1-6 | https://www.youtube.com/watch?v=uvmujJEKAsk (ep. 1) | 2020-04 to 07 | video course | 6.8x/7.0 (inferred) |
| FR-06 | PHOTOVOLTAIC 4 you, PVsyst 7.1 interface and weather import; 10 MW design | https://www.youtube.com/watch?v=TYRAoZKMAfQ ; https://www.youtube.com/watch?v=jVp3QX9mM8Q | 2021-09-15; 2023-01-17 | video | 7.1 |
| FR-07 | Énergie Et Développement, dimensionnement avec PVsyst | https://www.youtube.com/watch?v=Pomqln7KHDo | 2022-01-13 | video | n/a |
| FR-08 | Fastri, Calepinage partie 2: pratique sur PVsyst | https://www.youtube.com/watch?v=JB_p2OeD15o | 2025-09-01 | video | 8.0 (inferred) |
| FR-09 | FmecaT, Vidéo N°349 Logiciel PVSYST | https://www.youtube.com/watch?v=akGz-UpctPE | 2023-04-10 | video | n/a |
| FR-10 | Bruno Folha Engineering, SketchUp, Skelion and PVsyst | https://www.youtube.com/watch?v=q_u7Kclsfhc | 2021-04-09 | video | n/a |
| FR-11 | Jeunes Acteurs de l'Energie, formation PVsyst séance 1 | https://www.youtube.com/watch?v=voGyUCFIP_M | 2024-05-07 | live class (3 h 14) | n/a |
| FR-12 | Hespul, projects (Électricité de Mayotte audit) | https://www.hespul.org/fr/nos-projets/nos-projets-accompagnement-et-conseil/ | 2023-2024 | case note | n/a |
| FR-13 | INES Solaire course PV13 and resources | https://www.ines-solaire.org/formation/!/formation/conception-et-simulation-des-systemes-pv-sur-pvsyst-/ | undated | course listing (snippet; 403) | n/a |

**German** (6)

| ID | Title | URL | Date | Type | PVsyst |
|---|---|---|---|---|---|
| DE-01 | Steffens, Ertragsoptimierung einer einachsig nachgeführten PV-Anlage (HAW Hamburg) | https://reposit.haw-hamburg.de/bitstream/20.500.12738/9114/1/SteffensElena_geschwaerzt.pdf | 2018-05-15 | BSc thesis, checked against meter | 6.68 |
| DE-02 | Schlecht, Sonnennachführung von PV-Modulen (HAW Hamburg) | https://reposit.haw-hamburg.de/bitstream/20.500.12738/17072/1/BA_Sonnennachf%C3%BChrung%20von%20PV-Modulen.pdf | 2023-08-10 | BSc thesis | 7.4 |
| DE-03 | Jörck, Auslegung stationärer Batteriespeicher (HAW Hamburg) | https://reposit.haw-hamburg.de/bitstream/20.500.12738/14545/1/BA_J%C3%B6rck_geschw%C3%A4rzt.pdf | 2021 | BSc thesis with German report | 6.77 |
| DE-04 | Rodionova, O&M contract parameters and PV KPIs (HAW Hamburg) | https://reposit.haw-hamburg.de/bitstream/20.500.12738/12416/1/RodionovaDaryaBA_geschw%C3%A4rzt.pdf | 2021-02-05 | BSc thesis | n/a |
| DE-05 | Photovoltaikforum, Abweichende Prognosen mit PVGIS, PVSYST, PV-Sol bei Schatten | https://www.photovoltaikforum.com/thread/104958-abweichende-prognosen-mit-pvgis-pvsyst-pv-sol-bei-schatten/ | 2015-01-16 | forum comparison | 6.x |
| DE-06 | ZHAW, HSAT and 90° bifacial yield optimisation | https://digitalcollection.zhaw.ch/items/2883b270-d55f-4c33-8b15-d06032fad941 | undated | report (snippet only) | n/a |

**Portuguese** (Brazil, 29)

| ID | Title | URL | Date | Type | PVsyst |
|---|---|---|---|---|---|
| PT-01 | Canal Solar, Tutorial PVSyst: mapeamento de geração e ferramenta de otimização | https://canalsolar.com.br/tutorial-pvsyst-mapeamento-de-geracao-e-ferramenta-de-otimizacao/ | 2020-04-20 (upd. 2024-09-27) | blog tutorial | 6.8/7.0 (inferred) |
| PT-02 | Canal Solar, Módulos bifaciais com PVSyst: fatores a considerar | https://canalsolar.com.br/modulos-bifaciais-com-pvsyst-fatores-a-considerar/ | 2021-07-29 (upd. 2025) | how-to | 7.x (inferred) |
| PT-03 | Canal Solar, modelagem de usina com módulos bifaciais | https://canalsolar.com.br/modelagem-e-simulacao-de-uma-usina-solar-com-modulo-bifaciais/ | 2021-08-31 | case | n/a |
| PT-04 | Canal Solar (Villalva), Análise econômica usando PVSyst | https://canalsolar.com.br/analise-economica-de-um-sistema-fotovoltaico-usando-pvsyst/ | 2020-07-10 | tutorial | 7 |
| PT-05 | Canal Solar (Villalva), inversor com múltiplas entradas de MPPT | https://canalsolar.com.br/pvsyst-inversor-com-multiplas-entradas-de-mppt/ | 2020-06-28 | tutorial | 7 |
| PT-06 | Canal Solar, adicionar arquivos PAN no PVSyst | https://canalsolar.com.br/saiba-como-adicionar-arquivos-pan-no-pvsyst/ | 2019-07-24 | tutorial | 6.80 |
| PT-07 | Canal Solar, painéis sempre para o Norte? | https://canalsolar.com.br/paineis-solares-orientados-norte/ | 2020-04-14 (upd. 2026-02-16) | parametric study | n/a |
| PT-08 | Canal Solar, ângulo de inclinação dos módulos | https://canalsolar.com.br/como-determinar-o-angulo-de-inclinacao-dos-modulos-fotovoltaicos/ | 2020-07-11 | article | n/a |
| PT-09 | Canal Solar, NBR 16690 e queda de tensão CC | https://canalsolar.com.br/nbr-16690-queda-de-tensao-circuito-cc/ | 2020-07-25 | article with PVsyst | n/a |
| PT-10 | Canal Solar, modelagem 3D com drones | https://canalsolar.com.br/modelagem-3d-com-drones-em-projetos-de-geracao-solar/ | 2020-11-16 | workflow article | n/a |
| PT-11 | Canal Solar, tutorial de instalação do PVSyst | https://canalsolar.com.br/tutorial-instalacao-pvsyst/ | 2019-07-24 | install tutorial | 6.8.3 |
| PT-12 | Esposito et al., modelos 3D na análise de sombreamento no PVsyst (RBENS) | https://rbens.emnuvens.com.br/rbens/article/download/411/311 | 2023-12 | journal paper | 7.x (inferred) |
| PT-13 | Ursulino, dimensionamento com PVSYST, cliente grupo A (IFPB) | https://repositorio.ifpb.edu.br/bitstream/177683/4230/1/Dimensionamento%20de%20um%20sistema%20fotovoltaico%20utilizando%20PVSYST%20-%20Iury%20Matheus%20de%20Lira%20Ursulino.pdf | 2025-03-06 | undergraduate thesis | 7.2 |
| PT-14 | João Frederico, PVsyst 8.1 Básico, Aulas 1-6 and extras | https://www.youtube.com/watch?v=EM6H2hcIYdA (Aula 1) | 2026-05-10 to 2026-09-29 | video series | 8.1 |
| PT-15 | CurSol (Barcelos), PVsyst 7.2 Perdas detalhadas, Aula #80 | https://www.youtube.com/watch?v=qaCdi10tdVQ | 2022-02-14 | video lesson | 7.2 |
| PT-16 | Huawei FusionSolar, webinar PVsyst para plantas | https://www.youtube.com/watch?v=vgP5_F73CxA | 2020-06-23 | vendor webinar | 6.8/7.0 (inferred) |
| PT-17 | Sungrow Brasil, Introdução ao PV syst | https://www.youtube.com/watch?v=PYgIqn4q6-E | 2020-09-17 | vendor webinar | inferred 6.8/7.0 |
| PT-18 | Canal Solar videos: perdas de cabeamento; table zones | https://www.youtube.com/watch?v=hbPaFBHRWMU ; https://www.youtube.com/watch?v=Qyrukwut008 | 2021-08-31; 2019-05-27 | short videos | n/a |
| PT-19 | Gadiel (Solforte), pré-dimensionamento | https://www.youtube.com/watch?v=a-UdUIPM0uQ | 2020-04-26 | video | n/a |
| PT-20 | Aryel Maia, PVsyst 7.0 Curso básico; importar irradiância | https://www.youtube.com/watch?v=RPAI88UcXaU ; https://www.youtube.com/watch?v=s9C14tUi_0M | 2020-06/07 | video | 7.0 |
| PT-21 | Vitor Pacheco, análise de relatório PVsyst | https://www.youtube.com/watch?v=TcYp012K1mk | 2020-07-08 | video | n/a |
| PT-22 | Solars Elétrica, viabilidade econômica no PVsyst | https://www.youtube.com/watch?v=-ceahWIMLNw | 2022-11-22 | video | n/a |
| PT-23 | Integradordevalor, processamento do modelo 3D no PVSYST | https://www.youtube.com/watch?v=3jffxf9ltq0 | 2026-04-13 | video | 8.x (inferred) |
| PT-24 | PPGEE UFERSA, Minicurso PVSyst parte 1 | https://www.youtube.com/watch?v=d52IGp8e1Ds | 2021-12-16 | mini-course (3 h) | n/a |
| PT-25 | Energia Plus Brasil, curso com PVsyst (11 aulas) | https://www.youtube.com/watch?v=uX7pDxp8wU0 | about 2019 | course | 6.x (inferred) |
| PT-26 | Ronilson di Souza, otimização para tipos de fixação | https://www.youtube.com/watch?v=nYkqv2mlwKE | 2018-04-25 | video | 6.x (inferred) |
| PT-27 | Andrade and Trigoso, garantia física das usinas (CBENS) | https://anaiscbens.emnuvens.com.br/cbens/article/download/1459/1452 | 2016-04 | conference paper | n/a |
| PT-28 | Agostinho et al., otimização com PVsyst (ABM Week) | https://abmproceedings.com.br/en/article/otimizao-de-um-sistema-fotovoltaico-utilizando-software-pvsyst | 2023 | paper (abstract) | n/a |
| PT-29 | Canal Solar podcast, usina performando adequadamente | https://canalsolar.com.br/como-saber-usina-performando-forma-adequada/ | 2025-05-13 | podcast page | n/a |

**Spanish** (10)

| ID | Title | URL | Date | Type | PVsyst |
|---|---|---|---|---|---|
| ES-01 | García Castro, Simulación de instalaciones fotovoltaicas con PVsyst (Univ. Jaén) | https://creapre.ujaen.es/bitstreams/0cc2bb63-900b-48d2-a02a-38275d1785d5/download | 2015-09 | final-year thesis, 7 exercises | 6.x (inferred) |
| ES-02 | García Rosales, planta FV 820 kWp autoconsumo sin excedente (Univ. Sevilla) | https://biblus.us.es/bibing/proyectos/abreproy/95141/fichero/TFG-5141+Garc%C3%ADa+Rosales+de+Salamanca.pdf | 2024 | final-year thesis | 7.x (inferred) |
| ES-03 | SurgePV, PVsyst qué es: guía completa 2026 | https://www.surgepv.com/es/pvsyst-que-es | 2026 | competitor page | n/a |
| ES-04 | Ingenieria Lagos, Cálculo ON GRID con PVSyst; con baterías | https://www.youtube.com/watch?v=5XI4smWnDSE ; https://www.youtube.com/watch?v=45VuXxvYmNg | 2021-12-05; 2023-05-27 | video | 7.x (inferred) |
| ES-05 | MPV Solar Reference, Curso gratis de PVSYST, sesiones 1-2 | https://www.youtube.com/watch?v=2iaaCQkHU9o ; https://www.youtube.com/watch?v=ZY3H29e249E | 2021-11 | course | 7.2 (inferred) |
| ES-06 | MPV Solar Reference, almacenamiento con PVSyst; cualquier BESS | https://www.youtube.com/watch?v=q-WAWI8H6Vs ; https://www.youtube.com/watch?v=O6nV7cJ9TpY | 2026-03-26/27 | masterclass | 8 |
| ES-07 | Academia Energía Solar, webinars and free courses | https://www.youtube.com/watch?v=O_X0NHK4adA ; https://www.youtube.com/watch?v=EkIWgflnViE ; https://www.youtube.com/watch?v=fRtCSY2-898 | 2021-2024 | webinars | 7.2 |
| ES-08 | Dominando la Energía Solar, primer proyecto; planta de 1 MW | https://www.youtube.com/watch?v=mqDvY_dEDqE ; https://www.youtube.com/watch?v=qf1MWuq6MUI | 2025-09-03; 2026-05-12 | video | 8.x (inferred) |
| ES-09 | Solar Design, ON GRID con PVSYST, AUTOCAD y SKETCHUP | https://www.youtube.com/watch?v=ZrZAOuIjvhw | 2022-04-29 | webinar | n/a |
| ES-10 | Mundo Renovable, curso PVsyst 7.2 (8 lessons) | https://www.youtube.com/playlist?list=PLvkibXrfEBaX1lg4TezKhF0hsHThjkRk9 | 2021-12 to 2022-02 | short course | 7.2 |

**Chinese** (27; 25 from Candela, a Beijing PV consultancy and trainer)

| ID | Title (English) | URL | Date | PVsyst |
|---|---|---|---|---|
| ZH-01 | Candela Q&A no. 2 | https://www.candela.cn/pvsyst%E8%BD%AF%E4%BB%B6%E4%BD%BF%E7%94%A8%E7%AD%94%E7%96%91%E7%AC%AC%E4%BA%8C%E6%9C%9F/ | 2018-04-03 | 6.64 |
| ZH-02 | Candela Q&A no. 8 | https://www.candela.cn/1811/ | 2018-04-03 (page) | 6.66/6.67 |
| ZH-03 | Candela Q&A no. 12 | https://www.candela.cn/pvsyst%e5%ae%9e%e7%94%a8%e9%97%ae%e7%ad%94%e4%bd%a0%e6%83%b3%e7%9f%a5%e9%81%93%e7%9a%84%e9%83%bd%e5%9c%a8%e8%bf%99%e9%87%8c%ef%bc%88%e7%ac%ac12%e6%9c%9f%ef%bc%89/ | 2018-05-18 | 6.x |
| ZH-04 | Candela Q&A no. 16 | https://www.candela.cn/9909e437bb/ | 2019-10-17 | 6.x |
| ZH-05 | Candela Q&A no. 17 | https://www.candela.cn/13887363c5/ | 2021-08-25 | 7.2.4 |
| ZH-06 | Candela Q&A no. 18 | https://www.candela.cn/8685107e42/ | 2021-10-26 | 7.2.7 |
| ZH-07 | Candela Q&A no. 19 | https://www.candela.cn/2163707e7c/ | 2022-06-10 | 7.x |
| ZH-08 | PVsyst 8.0 bifacial PR correction | https://www.candela.cn/8-0%e7%89%88pvsyst%e5%85%b3%e4%ba%8e%e5%8f%8c%e9%9d%a2%e7%b3%bb%e7%bb%9f%e6%95%88%e7%8e%87%e7%9a%84%e4%bf%ae%e6%ad%a3%e8%af%b4%e6%98%8e/ | 2025-05-22 | 8.0.12 |
| ZH-09 | Sub-hourly vs hourly simulation (parts 1 and 2) | https://www.candela.cn/1fd28ab5d5/ ; https://www.candela.cn/603889b480/ | 2024-12-31; 2025-01-03 | n/a |
| ZH-10 | Simplifying terrain for PVsyst import | https://www.candela.cn/%e8%87%aa%e5%8a%a8%e7%ae%80%e5%8c%96%e5%b1%b1%e4%bd%93%ef%bc%8c%e6%8f%90%e9%ab%98pvsyst%e5%9c%b0%e5%bd%a2%e5%af%bc%e5%85%a5%e9%80%9f%e5%ba%a6/ | 2025-08-15 | n/a |
| ZH-11 | Row spacing on east and west slopes | https://www.candela.cn/8a803f6ae3/ | 2024-03-14 | n/a |
| ZH-12 | PV plus storage sized to the load | https://www.candela.cn/6eb925db4b/ | 2021-09-09 | 7.x |
| ZH-13 | Backtracking yields less than normal tracking? | https://www.candela.cn/746d5cddf9/ | 2021-06-04 | n/a |
| ZH-14 | Adjustable tilt with batch mode | https://www.candela.cn/103c052627/ | 2020-06-30 | 6.86 |
| ZH-15 | Fitting thermal coefficients from measurements | https://www.candela.cn/c9a9194972/ | 2020-03-26 | n/a |
| ZH-16 | Half-cut modules under shading in PVsyst 7.0 | https://www.candela.cn/218a1b130c/ | 2020-06-02 | 7.0 |
| ZH-17 | Often-neglected simulation details | https://www.candela.cn/2a62b8e371/ | 2019-09-19 | 6.66+ |
| ZH-18 | Model the ground under the arrays | https://www.candela.cn/db20b789b0/ | 2019-12-19 | n/a |
| ZH-19 | String routing changes yield | https://www.candela.cn/f9eb573f36/ | 2018-05-30 | 6.x |
| ZH-20 | Bifacial on horizontal single-axis trackers | https://www.candela.cn/0939b35c99/ | 2018-04-24 | 6.70 |
| ZH-21 | Overload loss as modules degrade | https://www.candela.cn/c2772e132a/ | 2019-07-12 | 6.x |
| ZH-22 | Bifacial loss lines explained | https://www.candela.cn/7b95cf6909/ | 2018-02-06 | 6.x |
| ZH-23 | PVsyst results vs field data | https://www.candela.cn/d86e10cc8c/ | 2019-12-13 | n/a |
| ZH-24 | Chinese practical guide, 3rd edition (contents only, paid) | https://www.candela.cn/e05aaf02c3/ | 2019-04-17 | 6.7.9 |
| ZH-25 | Full video course (outline only) | https://www.candela.cn/pvsyst%E5%85%A8%E5%A5%97%E5%9F%B9%E8%AE%AD%E8%A7%86%E9%A2%91/ | 2016-08-27 | 6.x |
| ZH-26 | Unofficial "PVsyst Chinese site" (low quality) | https://www.pvsyst.net.cn/jiaocheng/pvsyst-bvdhvhs.html | 2025-2026 | 7.4 |
| ZH-27 | Goldk reseller tutorials (generic) | https://www.goldksoft.com/e/action/ShowInfo.php?classid=3&id=4360 | 2023-2024 | n/a |

**Arabic** (8)

| ID | Title (English) | URL | Date | PVsyst |
|---|---|---|---|---|
| AR-01 | FUTURE SOLAR TECHNOLOGY, residential grid-connected series (6 kWp parts 1-3, 10 kWp, near shading, shading analysis) | https://www.youtube.com/playlist?list=PLKni-m2Qe57m49bbwmmIxUJKraBFMG2y1 | 2026-07-11 to 28 | 8.x (inferred) |
| AR-02 | Same channel, dust impact on a 2 MW plant in Dubai | https://www.youtube.com/watch?v=aKf0p-vm6Xk | 2026-07-09 | 8.x (inferred) |
| AR-03 | Same channel, fixing PVsyst error messages | https://www.youtube.com/watch?v=kbJMo3FeIbc | 2026-07-04 | 8.x (inferred) |
| AR-04 | Same channel, utility preliminary design in 10 minutes | https://www.youtube.com/watch?v=P0KxNIVKx4w | 2023-04-08 | 7.x (inferred) |
| AR-05 | Ahmed Abdelbaqi, PVsyst 7 design course (6 episodes) | https://www.youtube.com/playlist?list=PLyiEdrKX7c24qvKohwkiRgOYvIJPR23t_ | 2021-11/12 | 7 |
| AR-06 | TAQA Academy, PV system design with PVsyst | https://www.youtube.com/playlist?list=PLtpdYdedpNjri6aPAqKjdIHTyU8thbzmc | 2021-02 | 7 |
| AR-07 | Tareq Samhouri, Master PVsyst (Udemy outline) | https://www.udemy.com/course/excel-pvsyst/ | updated 2021-12 | 7 (inferred) |
| AR-08 | Eng. Muhammad Eltahan, PVsyst part 1, orientation | https://it-sharks.com/en/lesson/solar-energy-course7-lesson10 | 2024-07-29 | n/a |

**Turkish** (7)

| ID | Title (English) | URL | Date | PVsyst |
|---|---|---|---|---|
| TR-01 | Hüseyin Aytumur, PV plant design, cost and feasibility with PVsyst (5 episodes) | https://www.youtube.com/playlist?list=PL83lI-L5u1G96g9iHjgom6vjipHvR1BYn | 2025-05 | n/a |
| TR-02 | Enerji İnovasyon, PVsyst series including PVsyst 8 | https://www.youtube.com/channel/UCwjwdjwrB9v6HJosootldbg/videos | 2022-08 to 2026-01 | 8.0 |
| TR-03 | Tolga Keçeci, PVsyst training (Udemy outline) | https://www.udemy.com/course/pvsyst-egitimi-gunes-enerji-santrali-tasarm-ve-raporlama/ | updated 2022-03 | 7 (inferred) |
| TR-04 | Şahin and Salihmuhsin, 1 MWp plant in PVsyst vs measured | https://dergipark.org.tr/tr/download/article-file/3874951 | 2024 | n/a |
| TR-05 | Turan, 1 MWp rooftop design and simulation | https://dergipark.org.tr/tr/download/article-file/2378166 | 2022 | 7.2 |
| TR-06 | Keskin, Martin, Boran, Niğde plant model | https://www.set-science.com/a/84297240-ef3e-47d3-a635-9c617c30a32f/pdf | 2019 | 6.78 trial |
| TR-07 | Yüzer, 1 MWp design in Hakkari | http://kho.msu.edu.tr/akademIk/enstitu/Alp_SAVBEN_dergi/21(1)/1.pdf | 2025 | n/a |

**Vietnamese, Indonesian, Japanese** (6)

| ID | Title (English) | URL | Date | PVsyst |
|---|---|---|---|---|
| VI-01 | DAT Group, rooftop PV design method V2 | https://datsolar.com/wp-content/uploads/2023/03/20230109_BV_TE_112_Phuong-phap-thiet-ke-he-thong-dien-mat-troi-ap-mai_V2.pdf | 2023-03 | n/a |
| VI-02 | Student group, PVsyst user guide (preview text) | https://pdfcoffee.com/huong-dan-su-dung-pvsyst-pdf-free.html | 2021-2022 (inferred) | 7.2 |
| VI-03 | LITHACO, PVsyst, SketchUp and Lumion guide | https://lithaco.vn/huong-dan-su-dung-pvsyst-sketchup-lumion | 2025-06-21 | n/a |
| ID-01 | Sartika et al., rooftop PV for a mosque | https://ejournal.undip.ac.id/index.php/transmisi/article/download/51252/pdf | 2023-01 | n/a |
| ID-02 | Harmiansyah et al., grid-connected PV for a dormitory | http://jurnal.utu.ac.id/jmekanova/article/view/8609 | 2024-01-03 | n/a |
| JA-01 | Lefixea, PVsyst system losses and reports (English copies) | https://www.lefixea.com/article/pvsyst_inspection17 | undated | n/a |

**Counts by language**

| Language | IDs |
|---|---|
| English | 44 (+8 snippets) |
| Portuguese | 29 |
| Chinese | 27 |
| French | 13 |
| Spanish | 10 |
| Italian | 9 |
| Arabic | 8 |
| Turkish | 7 |
| German | 6 |
| Vietnamese | 3 |
| Indonesian | 2 |
| Japanese | 1 |
| **Total** | **159 IDs in 12 languages** |

About 120 of them have substantive step or value content; the rest are titles, descriptions or outlines.

### 6.5 Sources tried but not usable

No block was worked around.

| Source | Problem |
|---|---|
| Tigo, PVcase and HelioScope help centres; GSES; GUtech; INES resources; Zhihu; chinapower.com.cn; mullinixelectro.com; jurnal.pnj.ac.id; UFPA, CEFET-MG and PUC-Rio repositories | HTTP 403 |
| CSDN | Anti-bot page (HTTP 521) |
| SolarEdge Japanese note | Cloudflare challenge |
| RatedPower knowledge base | Page renders "CSS Error" |
| ARRAY Technologies bifacial brief | Behind a download form |
| UPNA tracker thesis | Embargoed to 2027 |
| USM Chile thesis | Request form only |
| Comillas theses | HTTP 410 |
| PoliTo webthesis; ZHAW; UFMG and UFC repositories | Connection refused |
| Padova theses | DNS failure |
| unige.ch | HTTP 503 |
| Scribd copies (FR, ES, TR) | Summary only; also unofficial uploads |
| Baidu Wenku, solarbe, pdfcoffee copies of official manuals | Not used as sources of official content |
| 52pojie, ittel.cn, xzji.com, lapdienmattroi.com | Excluded: they link cracked PVsyst copies |
| Bilibili PVsyst 8 series | Video removed |
| Several YouTube results in Italian, German, Polish and Dutch | Auto-translated titles of English or Spanish videos |
| Udemy, SEI, NEPSEN, INES, Candela book, PVsyst consulting | Paid; outlines only |

### 6.6 Not covered, and why

1. **Search budget.** The shared WebSearch budget (200 calls) ran out during the research, and the rest was done from already known URLs only. Not reached as a result:
   - English third-party tutorials on carports, grid injection limits, LeTID, spectral correction, transformer night disconnection, string sizing and unavailability;
   - Russian, Persian, Korean, Thai, Greek, Polish and Hindi or Urdu sources;
   - more Italian blogs and courses;
   - French S21 and CRE tender practice.

   A follow-up session with a fresh budget, or with `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` raised, can fill these.
2. **Video transcripts.** Not used: YouTube serves them only through an internal interface, not as public text. Chapter lists and descriptions were used instead.
3. **PVsyst consulting topic list.** Not read: it loads from `/api/`, which `robots.txt` disallows.

---

## Appendix A. Official video catalogue (main channel @PVsystOfficial)

All 102 videos of https://www.youtube.com/@PVsystOfficial on 22 Oct 2026, newest first.

- Lengths in minutes:seconds; view counts as shown on the public watch pages.
- Playlist membership from the channel's 23 playlists.
- Chapter lists as published on each page. Several read like YouTube's automatic chapters; short videos without chapters are left blank.

| Date | Title | Length | Views (22/10/2026) | Playlists | Chapters (from the public page) | URL |
|---|---|---|---:|---|---|---|
| 2026-10-13 | PVsystBasic 1.0 _ My first project | 7:14 | 800 | PVsystBasic |  | https://www.youtube.com/watch?v=MznqfJwrplg |
| 2026-07-28 | PVsyst 8_Module Layout | 6:51 | 2,558 | Creation of projects in PVsyst 8 | 0:00 Understanding shading losses; 1:05 Module layout basics; 2:36 Defining spatial arrangement; 3:40 Electrical configuration; 4:46 Simulation and validation | https://www.youtube.com/watch?v=3D8Ak3LaLis |
| 2026-06-25 | Presentation of PVsystBasic V1 | 1:38 | 1,142 | PVsystBasic |  | https://www.youtube.com/watch?v=G_u6F1Owf-U |
| 2026-05-12 | PVsyst 8.1_Sub-hourly simulation, weather data import and Novelties in PVsyst 8.1 | 3:27 | 7,125 | General & Novelties in PVsyst 8.1 (2026) |  | https://www.youtube.com/watch?v=W19FmnUzrkE |
| 2026-05-07 | Presentation N1 of PVsyst 8 et PVsystCLI (2025) | 67:03 | 634 | (channel only) | 0:00 Webinar introduction; 5:15 New features in PVsyst 8; 22:29 PVsyst CLI overview; 35:05 Automated workflow examples; 50:49 Q&A session | https://www.youtube.com/watch?v=R6ZbUzNiyxw |
| 2026-05-07 | Webinare N2: PVsyst 8.1, CLI & PVsystBasic 1.0 - 07/05/2026 | 59:56 | 1,249 | General & Novelties in PVsyst 8.1 (2026) | 0:00 Webinar introduction; 3:44 Weather data import; 16:04 Sub-hourly simulation; 28:38 PVsyst CLI features; 36:00 PVsyst Basic presentation; 45:43 Q&A session | https://www.youtube.com/watch?v=Xz4f-pq1CzE |
| 2026-05-07 | Presentation N2 of PVsyst 8 & PVsystCLI (2025) | 61:15 | 318 | (channel only) |  | https://www.youtube.com/watch?v=uDJBDi60jqI |
| 2026-05-05 | Webinare N1: PVsyst 8.1, CLI & PVsystBasic 1.0 - 05/05/2026 | 58:09 | 1,627 | General & Novelties in PVsyst 8.1 (2026) | 0:00 Webinar introduction; 3:33 PVsyst 8.1: Weather import; 14:28 Sub-hourly simulation; 25:15 PVsyst basic overview; 31:44 PVsyst CLI presentation; 40:06 Q&A session | https://www.youtube.com/watch?v=Dtqv8sMczrs |
| 2026-01-09 | PVsystCLI _ Batch Mode | 5:39 | 1,307 | PVsystCLI | 0:00 Introduction to batch mode; 0:44 Required batch parameters; 1:20 Configuring batch files; 2:38 Defining simulation scenarios; 3:33 Executing batch simulations; 4:33 Resources and conclusion | https://www.youtube.com/watch?v=SX3dQ2PHh_4 |
| 2025-11-21 | PVsyst 8 _ Battery energy storage systems strategy | 13:25 | 4,897 | General & Novelties in PVsyst 8 (2025) | 0:00 Introduction; 0:24 Storage strategies overview; 3:12 Power shifting tool details; 4:43 Use case and workflow; 7:45 Results and economic analysis; 10:25 Battery degradation; 11:58 Conclusion | https://www.youtube.com/watch?v=VHo-d-PFDlE |
| 2025-10-09 | PVsyst 8 _ Near Shadings (3D Scene) | 10:16 | 13,458 | Creation of projects in PVsyst 8 | 0:00 Introduction to near shading; 1:28 Electrical shading losses; 2:03 Scene construction tools; 3:20 Creating and editing objects; 5:07 Scene transformation and view; 5:58 Defining PV zones and trackers; 7:09 Managing objects in scenes; 7:54 Orientation management; 8:24 Shading animation and results; 9:15 Calculation modes and tables | https://www.youtube.com/watch?v=fZB2qAW8_qo |
| 2025-08-26 | PVsyst 8 _ Horizon (Far Shading) | 5:21 | 3,901 | Creation of projects in PVsyst 8 | 0:00 Introduction to horizon; 0:20 Understanding far shading; 1:01 Guidelines for using tools; 1:41 Sun path diagram analysis; 2:26 Manual horizon drawing; 2:52 Importing horizon data; 3:40 Location and simulation; 4:36 Applying and saving changes | https://www.youtube.com/watch?v=dHBGsOrGw5o |
| 2025-06-02 | PVsyst 8 _ Multi-MPPT  (Power sharing and Multi-orientation daily sharing) | 8:45 | 13,398 | Creation of projects in PVsyst 8 | 0:00 Multi-MPPT concept; 1:53 Power sharing configuration; 4:37 Complex inverter setups; 6:44 Daily multi-orientation | https://www.youtube.com/watch?v=6QpgYVrLZus |
| 2025-04-03 | PVsyst 8 _ Detailed Losses | 10:29 | 8,003 | Creation of projects in PVsyst 8 | 0:00 Introduction to losses; 0:26 Thermal parameters; 1:54 Ohmic and wiring losses; 4:11 Module quality and soiling; 5:55 Incidence and auxiliary; 6:54 Degradation and reliability; 9:23 Spectral corrections and end | https://www.youtube.com/watch?v=1FTEVIt9HWU |
| 2025-02-07 | Presentation of PVsystCLI | 8:27 | 3,379 | PVsystCLI | 0:00 Introduction to PVsyst CLI; 0:56 Installation and setup; 2:17 Running simulations; 5:32 Weather data conversion; 7:21 Advanced usage and conclusion | https://www.youtube.com/watch?v=586KBbVsFrA |
| 2025-01-27 | PVsyst 8 _ My First Project (Grid Connected System) | 10:17 | 34,510 | Creation of projects in PVsyst 8 | 0:00 Introduction; 2:08 Workflow; 3:55 Orientation; 5:30 System; 6:40 Inverter; 8:20 Simulation | https://www.youtube.com/watch?v=yN9vi7uGFD4 |
| 2024-12-20 | PVsyst 7 - Project 007 - Storage definition (Grid Connected System) | 7:55 | 2,538 | (channel only) | 0:00 Introduction; 0:46 Storage strategy; 2:08 Selfconsumption strategy; 5:56 Weak grid | https://www.youtube.com/watch?v=9fmNq7upu-I |
| 2024-12-20 | Q&A - Webinars 1 & 2 | 12:46 | 2,011 | General & Novelties in PVsyst 8 (2025) | 0:00 Topography data sources; 0:35 Working with topography; 1:27 Importing topographic layers; 1:51 Bifacial modeling for domes; 2:54 Vertical bifacial systems; 3:22 Customizing row parameters; 3:50 PVsyst CLI overview; 4:53 CLI parameters and licensing; 5:28 Floating PV systems; 5:59 Orientation management; 7:11 Mixing orientations; 7:35 Orientation error handling; 8:42 Compatibility and bugs; 9:21 Sub-hourly simulation; 10:26 Clipping correction; 10:46 Synthetic data limitations; 11:13 Tracker diffuse modeling; 11:58 Generating tracker arrays | https://www.youtube.com/watch?v=dQ4tr-zOW20 |
| 2024-12-09 | Webinar No2 - Presentation of PVsyst 8 & PVsystCLI | 59:47 | 2,619 | General & Novelties in PVsyst 8 (2025) | 0:00 Introduction to PVsyst 8; 1:22 Multiple orientation modeling; 12:14 Simulation accuracy and tools; 15:45 Summary of PVsyst 8 features; 19:48 Introduction to PVsyst CLI; 32:03 CLI automation workflows; 44:21 Future CLI roadmap; 47:04 Questions and answers | https://www.youtube.com/watch?v=-VAqV6D3G08 |
| 2024-12-06 | Webinar No1 - Presentation of PVsyst 8 & PVsystCLI | 59:40 | 7,673 | General & Novelties in PVsyst 8 (2025) | 0:00 Introduction to PVsyst 8; 1:36 New features in PVsyst 8; 16:51 Introduction to PVsyst CLI; 29:40 Automated workflow examples; 37:43 Advanced CLI applications; 41:41 Q&A and roadmap | https://www.youtube.com/watch?v=pL3b9j2ZJT0 |
| 2024-11-14 | PVsyst 8 _ Near Shadings Novelties in PVsyst 8 | 3:00 | 5,588 | General & Novelties in PVsyst 8 (2025) | 0:00 Introduction; 0:29 Orientation; 1:07 Interactive Map | https://www.youtube.com/watch?v=CzwlfqrqTKw |
| 2024-11-13 | PVsyst 8 _ Orientations Novelties in PVsyst 8 | 3:29 | 4,264 | General & Novelties in PVsyst 8 (2025) |  | https://www.youtube.com/watch?v=KIxXYfEl_e8 |
| 2024-11-07 | Presentation of PVsyst | 2:23 | 46,498 | General & Novelties in PVsyst 8 (2025) | 0:00 Introduction to PVSYST; 0:22 Modeling and Analysis; 0:45 System Design Features; 1:00 Economic and Storage Analysis; 1:18 Simulation Flexibility; 1:48 Reporting and Conclusion | https://www.youtube.com/watch?v=raph-zB3Jis |
| 2024-07-17 | PVsyst 7 - Project 007- MPPT & Power Sharing | 7:19 | 10,237 | Thematic Tutorials; Creation of projects | 0:00 Introduction to MPPT; 0:59 Multi-MPPT technology; 1:39 Power sharing overview; 2:36 Configuring subarrays; 3:32 Power sharing setup; 5:10 Complex inverter example; 6:13 Finalizing configurations | https://www.youtube.com/watch?v=MhSqXGE_AvE |
| 2024-06-21 | PVsyst Version 8 will soon be available | 2:06 | 11,440 | (channel only) | 0:00 Introduction; 0:30 Key Enhancements; 0:55 Conclusion | https://www.youtube.com/watch?v=C_A-8IMqs50 |
| 2024-05-31 | PVsyst 7 - BTS006 - Bifacial model conditions for 3D scene | 3:08 | 7,401 | Thematic Tutorials; Bifacial & Tracking Systems |  | https://www.youtube.com/watch?v=_rmEpN-FlWQ |
| 2024-05-24 | PVsyst 7 - BTS005 - Results | 4:00 | 3,326 | Thematic Tutorials; Bifacial & Tracking Systems |  | https://www.youtube.com/watch?v=_l-va15JR0g |
| 2024-05-15 | PVsyst 7 - BTS004 - Educational and Analysis tools | 3:47 | 2,688 | Thematic Tutorials; Bifacial & Tracking Systems | 0:00 Introduction; 0:11 Model tab; 1:01 Profile angle; 1:25 Profile angle limit | https://www.youtube.com/watch?v=AfyjhCMhw4A |
| 2024-05-14 | PVsyst 7 - BTS003 - Definition of a Bifacial System with Unlimited Trackers | 3:45 | 3,868 | Thematic Tutorials; Bifacial & Tracking Systems |  | https://www.youtube.com/watch?v=wgP9wrFVHkE |
| 2024-05-07 | PVsyst 7 - BTS001 - Definition of a Bifacial System | 2:16 | 4,239 | Thematic Tutorials; Bifacial & Tracking Systems |  | https://www.youtube.com/watch?v=BLizHdUIOCI |
| 2024-05-07 | PVsyst 7 - BTS002 - Bifacial System Procedure (unlimited sheds) | 5:18 | 6,634 | Thematic Tutorials; Bifacial & Tracking Systems | 0:00 Introduction; 0:13 Project Demo Utility; 0:48 System Window; 3:05 Albo Window; 3:15 General Parameters | https://www.youtube.com/watch?v=XkPGYnzjAFE |
| 2024-02-06 | 16th annual PVPMC (PV Performance Modeling Collaborative) conference | 17:28 | 3,652 | Thematic Tutorials; General | 0:00 Introduction; 0:25 Overview; 6:14 Electrical shadings; 7:47 Simplified models; 9:37 Single line diagram; 10:38 Grid injection limitation; 12:01 Sub hourly clipping losses; 13:52 Upcoming developments; 16:28 Summary | https://www.youtube.com/watch?v=el2T4stALT8 |
| 2023-11-29 | PVsyst 7 - Shadings 008 - Base slope | 3:29 | 5,249 | Thematic Tutorials; Near Shadings |  | https://www.youtube.com/watch?v=eq9pU5QWtpc |
| 2023-09-29 | PVsyst 7 - Meteo 004 - TMY Generation | 4:29 | 3,258 | Thematic Tutorials; Meteo & Measured data |  | https://www.youtube.com/watch?v=e_PrvnMMGeM |
| 2023-09-27 | PVsyst 7 - Self Consumption (Grid Connected System) | 6:32 | 10,240 | Thematic Tutorials; Storage & Self-Consumption | 0:00 Introduction to concepts; 0:56 Defining user load profile; 2:23 Advanced profile options; 4:12 Simulation results analysis; 4:44 Importing custom CSV data | https://www.youtube.com/watch?v=-PGRnnF1VuA |
| 2023-08-28 | PVsyst 7 - Storage for Weak Grid Islanding (Grid Connected System) | 7:09 | 5,161 | Thematic Tutorials; Storage & Self-Consumption | 0:00 Introduction; 0:11 Background; 1:11 Tutorial; 5:54 Visualization | https://www.youtube.com/watch?v=jZKdz248WJQ |
| 2023-07-14 | PVsyst 7 _ One Diode Model | 10:10 | 6,018 | Thematic Tutorials; PV Components (Fundamentals) | 0:00 Introduction to PV modeling; 0:37 Defining the IV curve; 1:10 The one-diode model circuit; 1:56 Deriving the model equation; 9:20 Comparing model types; 10:06 Conclusion | https://www.youtube.com/watch?v=Xp6swgcvI6E |
| 2023-07-04 | PVsyst 7 _ Series resistance determination | 6:58 | 1,856 | Components Database; Thematic Tutorials | 0:00 PV model parameters; 0:39 Series resistance and efficiency; 2:10 Analyzing module quality; 3:22 Diode ideality factor; 4:39 Parameter determination | https://www.youtube.com/watch?v=5MJo_9dqbBk |
| 2023-07-03 | PVsyst 7 - Storage for Peak Shaving Strategy (Grid Connected System) | 10:16 | 13,521 | Thematic Tutorials; Storage & Self-Consumption | 0:00 Introduction; 1:18 Peak Shaving Strategy; 3:20 Storage Pack; 6:49 Peak Shaving Configuration | https://www.youtube.com/watch?v=49d5pAV907Y |
| 2023-06-27 | PVsyst 7 - Module Layout 004 - Calculation | 3:00 | 3,425 | Thematic Tutorials; Module Layout |  | https://www.youtube.com/watch?v=SO6Tbso8Fqo |
| 2023-06-27 | PVsyst 7 - Module Layout 001 - Functionalities | 3:28 | 10,519 | Thematic Tutorials; Module Layout |  | https://www.youtube.com/watch?v=eeU2HmxJ8jk |
| 2023-06-27 | PVsyst 7 - Module Layout 003 - Automatic string modules attribution | 4:18 | 5,292 | Thematic Tutorials; Module Layout |  | https://www.youtube.com/watch?v=h8BQGk0XsJg |
| 2023-06-27 | PVsyst 7 - Module Layout 002 - Mechanical & Electrical Definition | 6:41 | 6,004 | Thematic Tutorials; Module Layout | 0:00 Introduction to PV layout; 1:09 Mechanical table adjustment; 2:27 Polygonal fill optimization; 3:31 Inverter and string mapping; 5:22 Assigning modules to strings | https://www.youtube.com/watch?v=wJB50QsR--w |
| 2023-06-13 | PVsyst 7 - Project 003 - User's needs (Stand Alone system) | 4:34 | 13,554 | Thematic Tutorials; Creation of projects | 0:00 Defining device needs; 1:04 Setting hourly profiles; 2:13 Using monthly values; 3:07 Importing CSV data; 4:05 Selecting consumption models | https://www.youtube.com/watch?v=8im2MnQQjvw |
| 2023-05-05 | PVsyst 7 - Storage for Self-Consumption (Grid Connected System) | 9:47 | 15,315 | Thematic Tutorials; Storage & Self-Consumption | 0:00 Introduction; 1:21 Storage Strategy; 2:48 Battery Module; 6:19 Selfconsumption; 8:33 Energy flux | https://www.youtube.com/watch?v=Eq5ZC_un4UA |
| 2023-04-03 | PVsyst 7 - Tools 006 - Aging Tool | 8:14 | 4,709 | Advanced Tools; Thematic Tutorials | 0:00 Introduction to aging tool; 1:16 Configuring aging parameters; 2:13 Setting up the simulation; 4:25 Analyzing simulation results; 5:56 Multi-year data simulations; 7:03 Exporting simulation reports | https://www.youtube.com/watch?v=Bbbfg1X1QOU |
| 2023-03-23 | PVsyst 7 - Tools 005 - Aging losses | 7:28 | 4,223 | Advanced Tools; Thematic Tutorials | 0:00 Introduction; 1:44 PV modulating parameters; 3:20 Monte Carlo method; 5:01 Model warranty; 6:58 Module degradation | https://www.youtube.com/watch?v=lfzVPcNZ5qc |
| 2023-03-14 | PVsyst 7 - Meteo 003 -  Tables and Graphs | 7:46 | 3,184 | Thematic Tutorials; Meteo & Measured data | 0:00 Introduction; 0:35 Clear Sky Model; 1:18 Tables Graphs; 4:16 Graphs | https://www.youtube.com/watch?v=Be2e5F1oi64 |
| 2023-03-01 | PVsyst 7 - Project 006 - My First Simulation (Stand Alone system) | 8:02 | 30,673 | Thematic Tutorials; Creation of projects |  | https://www.youtube.com/watch?v=w06qCo9OTzA |
| 2023-01-18 | PVsyst 7 - Tools 004 - Carbon balance | 7:36 | 4,626 | Advanced Tools; Thematic Tutorials | 0:00 Introduction; 1:45 LCA Grid; 6:45 Results | https://www.youtube.com/watch?v=yT5NoRiYhB0 |
| 2023-01-12 | PVsyst 7 - Project 005 - Single Line Diagram | 4:29 | 20,282 | Thematic Tutorials; Creation of projects | 0:00 Introduction; 0:18 Single Line Diagram; 0:50 Functionality; 3:37 View Single Line Diagram | https://www.youtube.com/watch?v=V6GgR14_YyQ |
| 2022-11-09 | PVsyst 7 _ Help tools | 2:41 | 13,147 | Thematic Tutorials; General |  | https://www.youtube.com/watch?v=SMkzs3fH6bU |
| 2022-10-17 | PVsyst 7 _ Tool 003 _ P50 P90 estimation | 8:17 | 13,899 | Advanced Tools; Thematic Tutorials | 0:00 Introduction; 0:35 Gaussian Distribution; 2:16 Other uncertainties; 3:26 P50 P90 estimation | https://www.youtube.com/watch?v=PGlsrCx1t8o |
| 2022-09-22 | 15th annual PVPMC (PV Performance Modeling Collaborative) conference | 15:08 | 16,302 | Thematic Tutorials; General | 0:00 Introduction to shading; 1:21 Single module effects; 2:42 String and array mismatch; 3:55 Quantifying shading losses; 4:57 Role of power optimizers; 6:07 Optimizer mitigation theory; 7:03 Study methodology; 8:37 Modeling approach; 10:42 Initial study results; 11:43 Optimizer performance results; 13:33 Simplified model validation; 14:06 Conclusion and future work | https://www.youtube.com/watch?v=2zZ4rSZ2-2Q |
| 2022-08-04 | PVsyst 7 _ Presentation of the PVsyst Software | 5:55 | 138,481 | Thematic Tutorials; General | 0:00 Introduction; 0:26 Objectives; 0:45 System orientation; 2:00 Database; 3:14 Simulation; 5:16 Contact Support | https://www.youtube.com/watch?v=J4dyNv-PApM |
| 2022-05-16 | PVsyst 7 _ Unlimited Sheds | 9:28 | 21,285 | My First Shading Project (Fundamentals) | 0:00 Introduction; 0:26 Create a new project; 0:49 Set the orientation parameter; 1:23 Modify the shed parameters; 3:44 Shading graph; 4:48 Tilt graph; 7:01 Optimal configuration; 8:10 System parameters; 9:11 Summary | https://www.youtube.com/watch?v=-rI9jhMrH0U |
| 2022-05-16 | PVsyst 7 _ My First Shading Project _ Horizon | 2:40 | 17,359 | My First Shading Project (Fundamentals) | 0:00 Introduction; 0:27 Open Tutorial Project; 0:55 Residential Demo Project; 1:18 Horizon Shading; 1:46 Horizon Simulation | https://www.youtube.com/watch?v=2Fczt7qP2lA |
| 2022-05-16 | PVsyst 7 _ Workspace | 7:09 | 9,936 | Introduction (Fundamentals) | 0:00 Intro; 0:45 Workspace; 1:57 Toolbar; 2:29 Workspace Switch; 3:20 Workspace Import; 4:31 Workspace Export; 5:30 Export Components | https://www.youtube.com/watch?v=5QAjGx6rU_Q |
| 2022-05-16 | PVsyst 7 _ Horizon | 7:24 | 17,972 | My First Shading Project (Fundamentals) | 0:25 Horizon Shading; 2:26 Solar Path; 3:07 Manually Draw a Horizon Profile; 3:50 Import the Horizon; 4:02 Import Horizon Profiles | https://www.youtube.com/watch?v=5htnRyntTSs |
| 2022-05-16 | PVsyst 7 _ User Interface Walkthrough | 11:20 | 35,469 | Introduction (Fundamentals) | 0:00 Intro; 0:14 Menu Bar; 1:43 Tools; 2:30 Workspace; 3:22 Database; 5:07 Project; 6:05 Variants; 6:47 System Configuration; 8:12 Shading Analysis; 9:50 Simulation | https://www.youtube.com/watch?v=6_UI5waDnPI |
| 2022-05-16 | PVsyst 7 _ Optimization Tool | 6:30 | 5,474 | Losses and Results (Fundamentals) | 0:00 Introduction; 0:30 The Optimization Tool; 0:56 Creating the System; 1:40 Optimization Tool; 3:02 View Results; 4:21 Plot Display | https://www.youtube.com/watch?v=CsizS99dwho |
| 2022-05-16 | PVsyst 7 _ Working Principle of a Solar Cell | 5:39 | 14,932 | PV Components (Fundamentals) | 0:00 Introduction; 0:26 Energy Conversion; 2:48 Band Diagrams; 3:38 Band Gap Energy; 5:08 Summary | https://www.youtube.com/watch?v=DTvfcZeV1Oo |
| 2022-05-16 | PVsyst 7 _ Loss Diagram | 8:48 | 13,076 | Losses and Results (Fundamentals) | 0:18 Loss Diagram; 2:29 Energy Loss Arrows; 4:28 Pv Loss due to Temperature; 7:24 Bifacial System; 8:26 The Loss Diagram | https://www.youtube.com/watch?v=EHlHeW-rExc |
| 2022-05-16 | PVsyst 7 _ My First 3D Project _ Objects and Results | 7:01 | 18,660 | My First Shading Project (Fundamentals) | 0:00 Introduction; 0:06 Adding shading objects; 1:10 Modeling the tree; 1:49 Defining scene orientation; 2:29 Running shading animation; 3:36 Saving and exporting scenes; 4:22 Calculating shading factor; 5:16 Analyzing shading effects; 6:13 Reviewing simulation report | https://www.youtube.com/watch?v=Ey4CIKcY0F8 |
| 2022-05-16 | PVsyst 7 _ Site and Weather Management | 8:09 | 5,788 | Site and Weather (Fundamentals) |  | https://www.youtube.com/watch?v=Gun1heMwq8Q |
| 2022-05-16 | PVsyst 7 _ IV Curve | 10:04 | 7,209 | PV Components (Fundamentals) | 0:00 Intro; 0:38 Diode in the Dark; 2:45 Solar Cell Model; 3:52 Solar Cell IV Curve; 5:24 Three Important Points; 6:18 Fill Factor; 7:53 IV/PV Curves With Different Irradiance; 8:30 IV/PV Curves With Different Temperature | https://www.youtube.com/watch?v=KD_75SD_H8U |
| 2022-05-16 | PVsyst 7 _ Meteo Tables and Graphs | 8:06 | 3,603 | Site and Weather (Fundamentals) | 0:00 Introduction; 1:20 Tables and Graphs; 3:22 Time Shift; 4:14 Check Data Quality | https://www.youtube.com/watch?v=M66KE6QbmHw |
| 2022-05-16 | PVsyst 7 _ Irradiance and Air Mass | 7:35 | 6,255 | Site and Weather (Fundamentals) | 0:00 Introduction to irradiance; 0:34 Atmospheric effects on light; 2:42 Understanding air mass; 5:07 AM 1.5 standard spectrum; 6:08 Air mass in PV modeling; 7:06 Summary of irradiance concepts | https://www.youtube.com/watch?v=OdQqS5mi7v0 |
| 2022-05-16 | PVsyst 7 _ Report Options | 4:55 | 5,736 | Losses and Results (Fundamentals) | 0:13 General Options Tab; 0:52 Import a Logo; 1:45 Monthly Values Table Frame; 2:28 Units in the Loss Diagram; 4:08 Compare Two Reports from Two Different Variants; 4:13 Compare with another Project Variant | https://www.youtube.com/watch?v=OenFkw3P_3Y |
| 2022-05-16 | PVsyst 7 _ Project Organization | 8:51 | 16,525 | Introduction (Fundamentals) | 0:00 Introduction; 0:22 Projects and Variants; 1:59 Project Definition; 5:50 Parameters; 6:40 Simulations; 8:19 Conclusion | https://www.youtube.com/watch?v=QWPDycW7EOQ |
| 2022-05-16 | PVsyst 7 _ Light Structure | 7:14 | 5,607 | PV Components (Fundamentals) | 0:00 Introduction; 0:25 Wave particle duality of light; 1:08 Intensity of light; 2:13 Color of light; 4:32 Fundamental equation; 5:01 Electromagnetic spectrum | https://www.youtube.com/watch?v=STuEdBd2efs |
| 2022-05-16 | PVsyst 7 _ Mutual Shading | 7:42 | 17,466 | My First Shading Project (Fundamentals) | 0:00 Intro; 0:42 What is shed; 1:01 Design parameters; 2:27 Ground coverage ratio; 5:36 Shading limit angle; 6:16 Optimization | https://www.youtube.com/watch?v=XXIaRWXcpXs |
| 2022-05-16 | PVsyst 7 _ Meteo Data Management | 5:12 | 2,424 | Site and Weather (Fundamentals) | 0:03 Modify Existing Monthly Weather Data; 1:27 How To Create a New Site from Custom Data; 3:21 Synthetic Generation; 4:00 Create a Synthetic File | https://www.youtube.com/watch?v=bNeMezXCFRk |
| 2022-05-16 | PVsyst 7 _ Report Contents | 8:17 | 17,551 | Losses and Results (Fundamentals) | 1:49 Table of Contents; 2:49 Shading Characteristics; 3:12 Shading Scene; 5:13 Reference System Yield; 6:24 Performance Ratio; 7:01 The Loss Diagram | https://www.youtube.com/watch?v=k8mftCOeq4U |
| 2022-05-16 | PVsyst 7 _ Array sizing | 9:44 | 33,685 | My First Shading Project (Fundamentals) | 0:23 Array Sizing; 1:43 Voltage Constraints; 6:52 Overload Loss; 8:08 Pnom Ratio; 9:24 Array Sizing Tool | https://www.youtube.com/watch?v=lis_9F-f2pI |
| 2022-05-16 | PVsyst 7 _ PN Junction | 6:44 | 4,497 | PV Components (Fundamentals) | 0:00 Silicon and doping; 1:00 N-type doping; 1:56 P-type doping; 2:53 The pn junction; 4:08 Photovoltaic effect; 6:17 Summary | https://www.youtube.com/watch?v=mTMXQ4vjbEo |
| 2022-05-16 | PVsyst 7 _ My First 3D simulation _ Building and House | 9:18 | 27,951 | My First Shading Project (Fundamentals) | 0:00 Project setup; 0:37 Building construction; 2:07 Modeling the second wing; 4:14 Adding the roof; 6:33 Adding the PV array; 8:24 Finalizing the scene | https://www.youtube.com/watch?v=qJ0P7szS_jo |
| 2022-05-16 | PVsyst 7 _ Adding a PAN file | 11:18 | 25,826 | PV Components (Fundamentals) | 1:48 Module Description; 7:01 Model Parameters; 7:04 Model Parameters Page; 8:32 Temperature Coefficient; 9:50 Internal Model Result; 10:15 Graphs Page | https://www.youtube.com/watch?v=uRXQXr8wAdQ |
| 2022-05-16 | PVsyst 7 _ Batch Simulations | 9:42 | 5,967 | Losses and Results (Fundamentals) | 0:23 Batch Simulation; 1:04 Running a Batch Simulation; 3:25 Simulation Parameters Tab; 7:11 Create More Simulations | https://www.youtube.com/watch?v=vCiPPuC8U1s |
| 2022-05-16 | PVsyst 7 _ My First Simulation | 9:25 | 46,081 | My First Shading Project (Fundamentals) | 0:00 Intro; 0:24 Project Creation; 1:42 Saving the Project; 4:05 Defining the System; 6:18 The Report | https://www.youtube.com/watch?v=x9V_CrU9OOU |
| 2022-01-31 | PVsyst 7 - Project 004 - My First Simulation (Pumping System) | 4:01 | 22,448 | Thematic Tutorials; Creation of projects | 0:00 Introduction; 0:11 Hydraulic Circuit; 2:22 PV System | https://www.youtube.com/watch?v=eiLpWd2F9C8 |
| 2022-01-25 | PVsyst 7 - Shadings 007 - List and management of objects | 4:20 | 9,236 | Thematic Tutorials; Near Shadings | 0:00 Introduction; 0:16 Advanced selection; 3:37 Object management | https://www.youtube.com/watch?v=YinpazohEnQ |
| 2021-12-17 | PVsyst 7 - Tools 001 - Optimization Tool | 6:36 | 15,185 | Advanced Tools; Thematic Tutorials | 0:00 Introduction; 0:58 Creating the system; 1:42 Optimization tool; 3:04 View results; 4:22 Plot display; 5:58 Conclusion | https://www.youtube.com/watch?v=CGou9LUYuB8 |
| 2021-12-17 | PVsyst 7 - Tools 002 - Batch Simulations | 9:48 | 11,833 | Advanced Tools; Thematic Tutorials | 0:00 Introduction; 0:36 Options; 1:05 Procedure; 2:02 Demonstration | https://www.youtube.com/watch?v=rbk7tpLW0TM |
| 2021-10-22 | PVsyst 7 - Meteo 002 - Meteo Data Management | 5:24 | 16,395 | Thematic Tutorials; Meteo & Measured data | 0:00 Introduction to Site Files; 1:26 Creating a Custom Site; 3:24 Generating Synthetic Data | https://www.youtube.com/watch?v=fojcT6r8YQM |
| 2021-06-14 | PVsyst 7 - Meteo 001 - Create a new meteo site | 3:43 | 27,643 | Thematic Tutorials; Meteo & Measured data | 0:46 Geographic Coordinates Tab; 1:46 Monthly Weather Window; 2:09 Clearness Index | https://www.youtube.com/watch?v=_Zin--QDIh0 |
| 2021-05-05 | PVsyst 7 - Project 002 - Detailed Losses | 7:10 | 51,319 | Thematic Tutorials; Creation of projects | 0:00 Introduction; 0:11 Loss parameters; 0:38 Thermal behavior; 1:22 Wiring losses; 2:21 External transformer losses; 4:22 Incidence angle modifier; 4:52 Auxiliary consumption; 5:12 System unavailability; 5:33 Spectral correction | https://www.youtube.com/watch?v=V495ATFuLTM |
| 2021-01-22 | PVsyst 7 - Project 001 - My First Simulation (Grid Connected System) | 9:13 | 250,481 | Thematic Tutorials; Creation of projects | 0:00 Introduction; 0:10 Project creation; 5:55 Sizing tool | https://www.youtube.com/watch?v=b-5KeNTPK2s |
| 2020-08-12 | PVsyst 7 - Licence 002 - Transfert de licence | 1:49 | 3,669 | Licence (activation, transfert,...) |  | https://www.youtube.com/watch?v=mubLp2xm4HM |
| 2020-08-11 | PVsyst 7 - Licence 001 - Activation licence | 2:18 | 18,151 | Licence (activation, transfert,...) |  | https://www.youtube.com/watch?v=S-S1cRno2iY |
| 2020-07-08 | PVsyst 7 - Shadings 004 - Render options | 3:52 | 12,718 | Thematic Tutorials; Near Shadings | 1:09 Anti-Aliasing; 1:24 Real-Time Shadows; 2:12 Camera Animation; 3:12 Hide Cardinal Directions Grids | https://www.youtube.com/watch?v=N7AkDavN8UM |
| 2020-07-08 | PVsyst 7 - Shadings 005 - Create elementary objects | 2:25 | 12,350 | Thematic Tutorials; Near Shadings | 0:00 Intro; 0:34 Elementary objects; 0:50 Types of elementary objects; 1:16 Parameters; 1:36 Thin objects; 2:00 Object color | https://www.youtube.com/watch?v=o9RRSSNtQC4 |
| 2020-07-07 | PVsyst 7 - Shadings 003 - Point of view | 3:29 | 12,714 | Thematic Tutorials; Near Shadings |  | https://www.youtube.com/watch?v=QDdGSDLCMA4 |
| 2020-07-07 | PVsyst 7 - Shadings 002 - Objects selection | 2:12 | 12,556 | Thematic Tutorials; Near Shadings |  | https://www.youtube.com/watch?v=vuvslR9VX14 |
| 2020-07-06 | PVsyst 7 - Shadings 001 - User Interface | 3:06 | 32,381 | Thematic Tutorials; Near Shadings | 0:00 Interface overview; 1:00 Right panel functions; 1:47 Tools and panels; 2:05 Toolbar customization | https://www.youtube.com/watch?v=xj9I9K60snI |
| 2020-06-19 | PVsyst 7 - Shadings 006 - Import a 3D scene | 4:57 | 45,246 | Thematic Tutorials; Near Shadings | 0:00 Intro; 0:12 Import a 3D scene; 2:30 Import trackers; 3:38 Import H2P | https://www.youtube.com/watch?v=is44ZnQtOx0 |
| 2020-06-17 | PVsyst 7 - Components Database 002 - Grid Inverter | 7:28 | 29,173 | Components Database; Thematic Tutorials | 0:00 Introduction; 1:15 Parameters; 3:31 Efficiency; 4:07 Additional Data; 6:36 Field Specificities | https://www.youtube.com/watch?v=ADgwnDSk92U |
| 2020-06-03 | PVsyst 7 - License 001 - License activation | 2:11 | 108,637 | Thematic Tutorials; License (activation, transfert,...) | 0:00 Activation process; 0:51 Viewing license status; 1:06 Manual activation method | https://www.youtube.com/watch?v=Ul4RVFA-TcA |
| 2020-06-03 | PVsyst 7 - License 002 - License transfer | 2:01 | 26,427 | Thematic Tutorials; License (activation, transfert,...) |  | https://www.youtube.com/watch?v=oYsaSAh85OM |
| 2020-06-02 | PVsyst 7 - Components Database 001 - PV module | 8:21 | 53,113 | Components Database; Thematic Tutorials | 0:00 Introduction; 0:19 Datasheet; 0:50 Create new PV module; 1:13 Define basic data; 1:57 Main properties; 2:53 Sizes and technology; 5:09 Model parameters; 6:16 Temperature coefficient; 6:41 Additional data; 7:18 Results | https://www.youtube.com/watch?v=wICpYvHYZbU |
| 2020-05-29 | PVsyst 7 - Economic Evaluation 001- Components prices | 2:19 | 18,869 | Thematic Tutorials; Economic Evaluation |  | https://www.youtube.com/watch?v=rRw0GtcuZMQ |
| 2020-05-29 | PVsyst 7 - Economic Evaluation 002 - Global overview | 7:25 | 22,181 | Thematic Tutorials; Economic Evaluation | 0:00 Introduction; 0:11 Investment costs and charges; 2:52 Financial parameters; 4:58 Resale strategy; 6:23 Financial result | https://www.youtube.com/watch?v=v3zAAzDL1kI |

