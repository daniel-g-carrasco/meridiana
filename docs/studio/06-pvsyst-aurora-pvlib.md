# PVsyst 8.1, Aurora Solar, PVGIS and pvlib-python: function inventory and parity plan for Meridiana

Research report for **Meridiana**, an open-source desktop PV design program (Python, PySide6/Qt 6, GPL-3.0-or-later). Its goals are at least all of PVsyst's functions, with Aurora Solar as the UX and modelling reference and PVGIS as data source and cross-check.

Research date: 21 October 2026. The research was read-only: no accounts, no API keys, no installers, and no personal data sent anywhere.

## 0. Scope, sources and how to read this report

### 0.1 Versions checked

| Product | Version or status on 21 Oct 2026 | Source |
|---|---|---|
| PVsyst | **8.1.7**, released 30 Sep 2026. Earlier milestones: 8.1.0 (15 Apr 2026) and 8.0.0 (7 Nov 2024). The online help covers "PVsyst 8.1". | https://www.pvsyst.com/help/release-notes/index.html , https://www.pvsyst.com/help/index.html |
| pvlib-python | **v0.16.1**, 26 Sep 2026: a documentation fix, with the v0.16.0 feature release on the same day. Licence BSD-3-Clause; Python ≥ 3.11. | https://pvlib-python.readthedocs.io/en/stable/whatsnew.html , https://github.com/pvlib/pvlib-python |
| PVGIS | **5.3** in production since 25 Sep 2024, using SARAH3 2005–2023 for Italy. **PVGIS 6** is a public beta, with breaking API changes on 23 Jul and 19 Oct 2026. | https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en , https://photovoltaic-geographic-information-system.ec.europa.eu/api/release-notes |
| Aurora Solar | Cloud platform with Basic, Premium and Enterprise plans. Its Help Center articles are mostly dated 2025–2026. HelioScope is Aurora's separate commercial-scale product. | https://aurorasolar.com/pricing/ , https://help.aurorasolar.com/ |

### 0.2 Method

- **PVsyst.**
  - The full text of the official 8.1 online help (613 pages) came from the help's own MkDocs search index (https://www.pvsyst.com/help/search/search_index.json).
  - Every fact cites the public page `https://www.pvsyst.com/help/<path>` that carries the same text.
  - The version history comes from the release-notes page.
- **Aurora Solar.**
  - Sources: product pages and Help Center articles.
  - The Help Center's web pages return HTTP 403 to automated fetchers. The articles were read through the Help Center's public read-only article feed, which serves the same text; citations give the normal article URLs.
  - No account was used. The walkthrough in 2.9 is assembled from the documentation, not from a hands-on test.
- **PVGIS.**
  - Sources: the JRC user manual, the API documentation and the data and methods pages.
  - Two read-only API calls with a public Milan coordinate confirmed the endpoints and the output fields.
- **pvlib-python.**
  - Sources: the stable documentation (API reference, user guide, what's new) and the LICENSE and `pyproject.toml` files of the v0.16.1 tag.
  - Every function named in section 3 was checked against the current API reference.

### 0.3 Conventions

- **[unverified]**: the official pages do not confirm the point. **[not in help]**: the PVsyst 8.1 help does not mention it.
- **Analysis labels.** "IT relevance", "Meridiana note" and lines marked "(analysis)" are the researcher's analysis, not vendor documentation. Phase proposals are analysis too.
- **Quotes** are short and verbatim. Contradictions inside the PVsyst help are flagged where found; examples are the overload thresholds and the module-quality default.
- **Section 1** follows PVsyst's own organisation. Section 1.0 maps PVsyst's chapters to this report.
- **Azimuth conventions differ between tools:**
  - PVsyst and the PVGIS `aspect` parameter: south = 0°, west positive.
  - pvlib: north = 0°, clockwise, so south = 180°.

### 0.4 Executive summary

**PVsyst (section 1)**

1. **Current version and 8.x changes.** The current release is PVsyst 8.1.7 (30 Sep 2026). The 8.x line added:
   - **8.0:**
     - unlimited orientations that mix fixed planes and trackers;
     - a paid command-line interface (PVsystCLI);
     - a "power shifting" storage strategy (8.0.17).
   - **8.1.0:**
     - a weather-import assistant with automatic quality control;
     - sub-hourly simulation for grid and stand-alone systems;
     - a transient thermal model;
     - the Engerer2 decomposition and step-specific Perez coefficients;
     - NASA POWER as a data source;
     - a solar constant of 1361 W/m².
   - **8.1.2 to 8.1.6:**
     - CSV time series for albedo, soiling, export limit and unavailability;
     - PVCollada 2 import (8.1.5);
     - battery state of health reducing capacity (8.1.4).

   Details: 1.11.3.
2. **The physics is documented well enough to reimplement.** This covers:
   - the one-diode model with exponential Rsh and gamma(T), and PVsyst's default-parameter rules;
   - Hay and Perez transposition;
   - Fresnel IAM, the default since 6.67;
   - the Uc/Uv thermal model;
   - every loss default, for example mismatch 2 %, DC wiring 1.5 % at STC, module quality one quarter of the tolerance, and Uc 20 W/m²K for new projects;
   - the inverter model, with three-voltage efficiency curves and overload handled by moving the operating point;
   - the loss order, down to the variable names (EArrNom → EArrMPP → EOutInv → E_Grid).

   Sections: 1.1.13, 1.1.14.1, 1.10.
3. **PVsyst states its own limits.** Each one is an opportunity for Meridiana:
   - **Geometry and shading:**
     - no slope-aware backtracking;
     - bifacial only in 2-D, with no east-west or dome bifacial and no use of the 3D scene;
     - no strings mixing orientations, and no mixing of module models on one input;
     - Module Layout electrical shading only for crystalline modules, limited by default to 5 MWp.
   - **Storage and grid:**
     - storage only AC-coupled;
     - no tariff-driven dispatch;
     - only a fixed cos φ (no Q(U));
     - no cascaded transformers;
     - a single-line diagram that is "work in progress", without storage or undo.
   - **Workflow and platform:**
     - batch mode limited to one fixed orientation and yearly results;
     - advanced parameters not saved with the variant;
     - no per-sub-array results;
     - Windows only;
     - file formats "intended for internal use only".
   - **Content:**
     - no LeTID item;
     - no Italian load profiles, datasets or incentive schemes.

   Sections: 4.4 and the sections cited there.

**Aurora Solar (section 2)**

4. **What Aurora is.** A cloud tool for residential and small commercial rooftops, strongly US-centric; no Help Center article mentions Italy.
5. **Its modelling UX is the reference:**
   - one-letter modal tools;
   - SmartRoof, which infers the roof faces from a traced eave outline;
   - LIDAR fitting; AI roofs in about 10–15 seconds and AI trees in about 30 seconds (vendor figures);
   - an irradiance heat map with solar access, TOF and TSRF;
   - AutoDesigner and AutoStringer;
   - setbacks and fire pathways applied by jurisdiction;
   - live, non-blocking colour validation;
   - Milestone snapshots.

   See 2.9 and 2.10.
6. **Its engineering depth is far below PVsyst's:**
   - no bifacial gain;
   - no trackers (HelioScope Enterprise only);
   - P50 only, and a 1-hour step;
   - flat-percentage mismatch, wiring and soiling;
   - no PAN/OND import (HelioScope only), and no user weather or horizon import;
   - undocumented temperature and IAM models;
   - an SLD editor for European accounts only.

   See 2.7 and 2.11.

**pvlib-python (section 3)**

7. **The physics core is available.** pvlib 0.16.1 is BSD-3-Clause, which the FSF lists as GPL-compatible. It provides:
   - solar position (SPA) and Erbs decomposition;
   - Hay and Perez transposition;
   - physical (Fresnel), ASHRAE and interpolated IAM, with diffuse integration;
   - `calcparams_pvsyst` with `singlediode`, and `pvsyst_cell`;
   - First Solar spectral correction;
   - 2-D bifacial models (`infinite_sheds`, `ants2d`) and Deline rear mismatch;
   - `tracking.singleaxis` with slope-aware backtracking;
   - DC ohmic and transformer losses;
   - keyless PVGIS and NASA POWER fetchers;
   - a raw PAN/OND reader (`read_panond`).
8. **Meridiana must write the rest itself:**
   - the 3D scene, the near-shading engine and the electrical shading model;
   - the horizon effect;
   - an inverter model faithful to the OND file;
   - the loss ledger and the loss diagram;
   - PAN/OND mapping and the datasheet-to-parameters procedure;
   - Engerer2, the step-specific Perez sets and the hourly transient thermal model;
   - optimizers, self-consumption and storage dispatch;
   - economics, P50/P90, the report and batch runs;
   - stand-alone and pumping systems.

   pvlib APIs change often, so pin the version and call pvlib through Meridiana's own adapter layer. See 3.3.

**PVGIS (3.4)**

9. **The keyless default for Italy.** PVGIS 5.3 combines SARAH3 irradiance (2005–2023), ERA5 temperature and wind, and a DEM horizon at about 90 m. Its `PVcalc` yield is a ready-made cross-check: Muneer transposition, the Huld power model, Faiman temperature and a lumped 14 % loss.
10. **Version pitfalls.**
    - pvlib's PVGIS functions default to the unversioned endpoint. In 2024 the JRC announced it would serve 5.2 "for a limited period"; a test on 21 Oct 2026 found it returning the 5.3 data (SARAH3, 2005–2023).
    - Pass `https://re.jrc.ec.europa.eu/api/v5_3/` explicitly anyway, so results stay reproducible.
    - PVGIS 6 is still a beta with breaking changes, limited to 200 requests per hour per client.

**Plan (section 4)**

11. **The parity matrix** has 158 rows, split into three phases.
    - **Phase 1 (57 rows): a grid-connected rooftop study.** It comprises:
      - PVGIS weather and horizon;
      - roof tracing over an orthophoto, with 3D obstacles;
      - linear near shading with a strings-based electrical estimate;
      - PAN/OND import, the one-diode model, Fresnel IAM and the Uc/Uv thermal model;
      - a loss ledger in PVsyst order;
      - string and DC:AC checks;
      - self-consumption from 15-minute meter data and an export limit;
      - an Italian PDF report with the loss diagram;
      - a PVGIS cross-check.
    - **Phase 2 (69 rows): full grid-connected parity.** It adds:
      - trackers and bifacial;
      - module-level electrical shading and optimizers;
      - storage, transformers and power factor;
      - P50/P90 and economics;
      - batch runs and sub-hourly simulation.
    - **Phase 3 (32 rows)** covers stand-alone, pumping, DC-grid and specialist functions.

### 0.5 Contents

- 0. Scope, sources and how to read this report
  - 0.1 Versions checked
  - 0.2 Method
  - 0.3 Conventions
  - 0.4 Executive summary
- 1. PVsyst 8.1: complete function inventory
  - 1.0 How PVsyst is organised, and where each function is described
  - 1.1 Project design: common parts and grid-connected systems
  - 1.2 Project design: stand-alone systems
  - 1.3 Project design: pumping systems
  - 1.4 Project design: DC-grid systems
  - 1.5 Preliminary design (pre-sizing)
  - 1.6 Databases: weather data (meteo database)
  - 1.7 Databases: component database
  - 1.8 Tools
  - 1.9 Measured data analysis
  - 1.10 Physical models used
  - 1.11 Platform, files, validations and release notes
  - 1.12 Relevance for an Italian designer: summary by project segment
- 2. Aurora Solar: feature inventory and UX patterns
  - 2.1 Product overview and modes
  - 2.2 Site modelling
  - 2.3 Shading and irradiance
  - 2.4 Layout
  - 2.5 Electrical design
  - 2.6 Storage, self-consumption, consumption and rates
  - 2.7 Performance simulation
  - 2.8 Proposals and financials
  - 2.9 How it feels: a residential design from address to proposal
  - 2.10 UX patterns worth copying for Meridiana, and what Aurora does not do
  - 2.11 Aurora parity flags (for the parity matrix)
- 3. Mapping to pvlib-python (and PVGIS)
  - 3.1 pvlib-python: facts
  - 3.2 Mapping table: PVsyst model or function to pvlib
  - 3.3 Gaps: what PVsyst does that pvlib does not, and what Meridiana must write
  - 3.4 PVGIS as data source and cross-check
- 4. Prioritised feature list (parity matrix)
  - 4.1 How to read the matrix
  - 4.2 Matrix
  - 4.3 Phase 1 in practice: the minimum usable rooftop study (proposal)
  - 4.4 Where Meridiana can go beyond PVsyst (each tied to a limit PVsyst documents)
  - 4.5 Risks and open questions

---

## 1. PVsyst 8.1: complete function inventory

**Sources and method.** The inventory is based on the official PVsyst 8.1 online help. Its full text (613 pages) was read through the help's own MkDocs search index, https://www.pvsyst.com/help/search/search_index.json, downloaded on 21/10/2026. Every page cited below is the public page `https://www.pvsyst.com/help/<path>` that holds the same text. The release notes from 8.0.0 to 8.1.7 come from https://www.pvsyst.com/help/release-notes/index.html. The help describes itself as covering "PVsyst 8.1", "a PC software package for the study, sizing and data analysis of complete PV systems" (https://www.pvsyst.com/help/index.html).

**What each entry gives.**
- What the function does, its inputs (with PVsyst's stated defaults) and the models or algorithms behind it.
- Its outputs, including PVsyst's variable names, and the limits PVsyst itself states.
- An "IT relevance" note: relevance for an Italian designer of rooftop and ground systems from 3 kW to multi-MW.
- Optionally a "Meridiana note".

Both notes are analysis, not PVsyst documentation. Where the help contradicts itself, the text says so instead of choosing a side.

**Order.** The sections follow PVsyst's own organisation: project design (grid-connected, then stand-alone, pumping and DC-grid), preliminary design, databases, tools, measured data, and the physical models. Section 1.0 maps PVsyst's menus and help chapters to the sections of this report.

### 1.0 How PVsyst is organised, and where each function is described

Sources: https://www.pvsyst.com/help/index.html , https://www.pvsyst.com/help/project-design/index.html , https://www.pvsyst.com/help/preliminary-design/index.html , https://www.pvsyst.com/help/meteo-database/index.html , https://www.pvsyst.com/help/component-database/index.html , https://www.pvsyst.com/help/tools/index.html , https://www.pvsyst.com/help/measured-data/index.html , https://www.pvsyst.com/help/physical-models-used/index.html

**Object model.**
- A **project** (`.PRJ`) holds a geographic site (`.SIT`, with monthly data), a weather file (`.MET`, hourly or sub-hourly) and project settings.
- A project has up to 36 **variants** (`.VC0`…`.VCZ`). Each variant holds one system definition and its stored results.
- A variant is a grid-connected, stand-alone, pumping or DC-grid system.
- Around the projects sit the **databases** (weather, components), the **tools** and the **measured-data** module.
- The overview page groups them as "Project design and simulation", "Databases" (weather data, components) and "Utilities" (tools, measured data).

| PVsyst area (help chapter) | What it contains in 8.1 | This report |
|---|---|---|
| **Project design**: project definition | Site and weather link, project settings (albedo, design conditions, transposition model), variants, demo projects | 1.1.1 |
| Project design: orientations (new model in 8.0) | Fixed planes, sheds, domes, sun-shields, every tracker type, tracking strategies, mixed and average orientations, optimisation tools | 1.1.2 |
| Project design: bifacial systems; concentrating systems | 2-D bifacial model for sheds and trackers; high-concentration CPV | 1.1.3, 1.1.4 |
| Project design: shadings | Far shading (horizon); near shading 3D scene and imports; calculation models (linear, tables, iso-shading); electrical shading (module strings, Module Layout); backtracking strategy | 1.1.5–1.1.8, 1.1.2.4 |
| Project design: PV array electrical behaviour | Mismatch, shaded cells, heterogeneous arrays (didactic tools) | 1.1.8 |
| Project design: grid-connected system definition | Sub-arrays, sizing, multi-MPPT and power sharing, power factor, grid power limitation, single-line diagram, optimizers, self-consumption, storage | 1.1.9, 1.1.10, 1.1.12 |
| Project design: user's needs (load) | Load definitions for self-consumption, stand-alone and DC-grid | 1.1.11 |
| Project design: array and system losses | Thermal, ohmic (DC, AC, transformers), module quality, LID, mismatch, soiling, IAM, spectral, auxiliaries, unavailability, ageing, optimizers | 1.1.13 |
| Project design: simulation; results | Simulation process, advanced simulation, ageing tool, CSV output, on-line graphs, batch mode, sheds optimisation tool; report, loss diagram, PR, variables | 1.1.14, 1.1.15, 1.1.20 |
| Project design: economic evaluation; P50-P90; carbon balance; time-series parameters | Costs, financing, tariffs; uncertainty; CO₂ balance; CSV time series for several parameters | 1.1.16–1.1.19 |
| Project design: stand-alone, pumping, DC-grid system definitions | The three non-grid system types | 1.2, 1.3, 1.4 |
| **Preliminary design** | Monthly pre-sizing for grid, stand-alone and pumping systems | 1.5 |
| **Databases: weather data** | Sites, known-format imports, import assistant (8.1), quality control, synthetic generation, TMY generation, comparisons, sub-hourly data | 1.6 |
| **Databases: components** | PV modules (`.PAN`), grid inverters (`.OND`), optimizers, batteries (`.BTR`), controllers, back-up generators, pumps, pump controllers, prices | 1.7 |
| **Tools** | Solar parameters, transposition factor, monthly weather computation, electrical behaviour of arrays, array voltage optimisation | 1.8 |
| **Measured data** | Import, checks, transformations, comparison with simulation, elimination of bad data | 1.9 |
| **Physical models used** | Time, solar geometry, irradiation models, PV module one-diode model, grid inverter, batteries, pump | 1.10 |
| Getting started, glossary, validations, release notes, PVsystCLI | Platform, files, hidden parameters, printing; validation studies; version history; command-line interface | 1.11, 1.1.15.2, 1.1.20 |

### 1.1 Project design: common parts and grid-connected systems

Source: https://www.pvsyst.com/help/project-design/index.html and the sub-pages cited in each section.

This is the core of PVsyst. Sections 1.1.1 to 1.1.10 cover the project, orientations, bifacial and concentrating systems, shading and the grid system definition. Sections 1.1.11 to 1.1.20 cover loads, self-consumption and storage, losses, simulation, results and the report, economics, P50/P90, the carbon balance, time-series parameters and automation. The physical models behind them (irradiance, PV module, inverter, battery) are in 1.10.

#### 1.1.1 Project, site, variants, project settings

##### 1.1.1.1 Project / variant structure and design procedure
URLs: https://www.pvsyst.com/help/project-design/index.html , https://www.pvsyst.com/help/project-design/project-definition/index.html , https://www.pvsyst.com/help/project-design/project-definition/variants-system-definitions/index.html , https://www.pvsyst.com/help/project-design/project-definition/variants-system-definitions/variants-management.html

- **Project** = geographic site + weather file (+ optional albedo data). Stored in a `.PRJ` file. Creation steps: (1) file and project name, (2) project site, (3) weather file `*.MET`, (4) project settings, (5) one or more variants.
- **Variants** ("calculation versions") hold the system definition (orientations, PV components, array losses, shadings, user's needs) and, once saved after simulation, its results; files `<project>.VC0`, `.VC1`, ... Changing the weather file does not prompt a save, so the same variant can be re-simulated on different weather years for comparison.
- **Variant manager**: copy (new extension = next highest, e.g. VCC to VCD), edit comment, renumber extensions from VC0, reorder (up/down or drag and drop; reordering swaps file extensions), delete (recoverable from the workspace `UserRecycleBin` folder).
- **Recommended workflow** (PVsyst's own): first a rough variant with all defaults; then refine detailed losses (soiling, IAM, thermal, wiring, module quality, mismatch, unavailability), optional horizon, near shadings (3D), and module layout (electrical shading).
- **Validation feedback**: every parameter set is checked; orange = warning (simulation allowed), red = error (simulation blocked); the Simulation button runs only without red items; results open in the "Results"/Report dialog. "Save as" per variant is advised to keep comparisons.
- System types handled per variant: grid-connected, stand-alone, pumping, DC-grid. For grid systems the user's needs (load) are optional and only serve self-consumption.
- IT relevance (analysis): high for all project sizes; the project/variant split maps well onto Italian practice (alternatives for a client offer, "stato di fatto" vs "progetto").
- Meridiana note (analysis): keep project/variant, but make variants cheap (diffable, cloneable, named) and keep the green/orange/red validation as live inline feedback rather than a blocking dialog.

##### 1.1.1.2 Project site and link to weather data
URLs: https://www.pvsyst.com/help/project-design/project-definition/project-site.html , https://www.pvsyst.com/help/project-design/project-definition/available-meteo-files.html , https://www.pvsyst.com/help/glossary/meteo-data/altitude-corrections.html , https://www.pvsyst.com/help/glossary/meteo-data/climatic-distance.html , https://www.pvsyst.com/help/glossary/meteo-data/time-zone.html , https://www.pvsyst.com/help/glossary/meteo-data/generic-year-1990.html

- **Site** (`.SIT`): latitude/longitude (sun position for every time of the year) plus a fallback monthly weather set used for fast, rough calculations in the design dialogs (Orientation, System), plus a maximum search area for weather files.
- **Method 1**: load a site from the geographical-site database/interactive map, or create a new one with a monthly fallback from Meteonorm or NASA. PVsyst then lists all weather files found in the search area and selects the last used. If none exists, saving the project generates a synthetic hourly file from the Meteonorm DLL ("ready-to-use project").
- **Method 2**: import a downloaded weather file from any provider through the Weather data button; PVsyst converts it to `.MET` and builds the project site from it. (Weather sources and import formats: see 1.6.)
- **Required hourly data**: GHI, ambient temperature; DHI optional (modelled if missing); wind optional (module temperature).
- **Weather file list**: all files within the search radius around the site (radius set in Project settings > Preferences; keep it small for representativeness).
- **Altitude corrections**: when linking a weather file to the site, irradiation and temperature can be corrected for altitude. Based on Swiss Meteonorm monthly studies (Bremer 1986), not validated for hourly behaviour; not applied to diffuse.
- **Climatic distance** (Meteonorm definition): sqrt(horizontal distance^2 + (100 x altitude difference)^2); a station is considered representative up to about 20 km.
- **Time conventions**: PVsyst uses the winter (standard) time zone; non-measured data (monthly averages, synthetic, TMY/DRY) are labelled "generic year 1990".
- IT relevance (analysis): high. Italian sites are often hilly or mountainous, so altitude correction and climatic distance matter; the search-radius idea is useful when mixing PVGIS, Meteonorm and local station data.
- Meridiana note (analysis): show the distance and altitude difference of each candidate weather source on the map, and warn beyond the 20 km climatic distance.

##### 1.1.1.3 Project settings (per project)
URLs: https://www.pvsyst.com/help/project-design/project-definition/project-settings.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/design-temperatures.html , https://www.pvsyst.com/help/physical-models-used/irradiation-models/transposition-model.html , https://www.pvsyst.com/help/project-design/array-and-system-losses/ohmic-losses/ac-ohmic-loss-ref-power.html , https://www.pvsyst.com/help/physical-models-used/irradiation-models/albedo.html , https://www.pvsyst.com/help/physical-models-used/irradiation-models/albedo-usual-coefficients.html

Project settings apply to one project; "Advanced settings" (hidden parameters, 1.1.1.5) apply to the whole workspace and act as initial values.

| Tab / item | What it does | Inputs and defaults stated by PVsyst |
|---|---|---|
| Albedo (far albedo) | Albedo of the terrain in front of the array, used by the transposition: AlbInc = rho x GHI x (1 - cos(tilt))/2 | Yearly or monthly values; default 0.2; table of usual values (urban 0.14-0.22, grass 0.15-0.25, fresh snow 0.82, concrete 0.25-0.35, red tiles 0.33, aluminium 0.85, etc.). The ground albedo under the modules for bifacial is separate (1.1.3). |
| Design conditions: site-dependent design temperatures | Used only at design time (string sizing graphs, warnings), never in the simulation | TMin (lowest ambient temperature for the absolute Voc limit; default -10 deg C; IEC 62548-1 cited: lowest temperature ever observed; IEC TS 62738 cited as allowing relaxation for ground-mounted); TOperMin 20 deg C (max modules in series vs VmppMax); TOperMax 60 deg C (min modules in series vs VmppMin); TOper 50 deg C. Since 8.1.5, TMin is computed during TMY generation (min. temperature with irradiance > 10 W/m2). |
| Array max. voltage | Max admissible array voltage, Voc at TMin | Text cites IEC 1000 V and UL 600 V; modules usually 1000 V or 1500 V. |
| muVoc value | Option to use the manufacturer's muVoc derate instead of the one-diode model for Voc(TMin) | Off by default (model value). |
| Limit overload loss for design | Acceptable yearly inverter overload loss used by the sizing check | Max. 4% by default; raise it to allow strongly oversized arrays. Since 8.0.13 the "slightly/strongly undersized" warnings trigger above 2% and 4% and are no longer fatal (release notes). |
| Transposition model | Hay(-Davies) or Perez for this project | Perez default since v6 (Hay default up to v5); Perez typically 0-2% higher yearly. Global default in Preferences. |
| Circumsolar treatment | Circumsolar either merged with diffuse or treated separately (same shading/IAM as beam) | Separate treatment default since v7.0 (introduced 6.8.0); more precise for large tilts and vertical bifacial. |
| AC losses power reference | Reference power for a relative AC ohmic loss | PNomPV(ac) = STC array power x inverter efficiency (historical) or PNom(Inv) (inverter nominal output); choice per project since 7.2, default in Preferences. |
| Other limitations | Tolerances for 3D scene vs system consistency | Max. difference of each fixed table vs averaged orientation; max. area ratio between 3D fields and system modules. |
| Preferences | Weather-file search radius around the site | Keep low; increase only if no nearby data. |

- IT relevance (analysis): high. TMin drives the maximum string length (safety); Italian high-altitude (Alpine/Apennine) sites may need values below the -10 deg C default (PVsyst itself says lower for altitude/northern regions). The 1500 V vs 1000 V limit matters for utility projects.
- Meridiana note (analysis): put TMin, max system voltage and the overload threshold on the string-sizing panel itself, with the source of the value (TMY minimum, user, standard).

##### 1.1.1.4 Demo projects
URL: https://www.pvsyst.com/help/project-design/project-definition/demo.html

Four pre-configured demo projects (Load > Demo Projects) used as templates:

| Demo | Features shown |
|---|---|
| Residential | Self-consumption, storage for self-consumption, ageing losses |
| Commercial | Module layout, multi-MPPT, unbalanced MPPT, ageing tool, economic evaluation (new commercial demo in 8.0.13) |
| Utility | Storage peak shaving, storage weak grid, bifacial, AC circuit, power factor, CO2 balance |
| Trackers | Tracking, horizon, mixed orientation, backtracking on hills ("Collines"), economic evaluation |

- IT relevance (analysis): medium; useful as onboarding. Meridiana could ship Italian demo projects (residential pitched roof with two orientations, C&I flat-roof E/W, agrivoltaic tracker plant).

##### 1.1.1.5 Hidden / advanced parameters relevant to design
URLs: https://www.pvsyst.com/help/getting-started/hidden-parameters/index.html , https://www.pvsyst.com/help/getting-started/hidden-parameters/default-values-and-costs.html , https://www.pvsyst.com/help/glossary/pvsyst-use/advanced-parameters.html

- Settings > Edit advanced parameters: list of predefined values (physical constants, defaults, warning thresholds) with a "modified" checkbox and reset to PVsyst default; changes valid for the session or saved permanently; no validity check ("expert users").
- Categories: grid-connected presizing; stand-alone presizing; pumping presizing; specific presizing costs; system design parameters; detailed simulation verification conditions; PV modules; regulators and converters; miscellaneous.
- Caveat stated by PVsyst: modified advanced parameters are not stored with the variant, so re-running a variant with other values can change results "without notice" (to be addressed in a future version).
- Examples of design-relevant advanced parameters cited elsewhere in the help (one line each, URLs in the relevant sections): default design temperatures; default DC wiring loss 1.5% at STC; metal resistivity at 50 deg C; "Pitch RMS limit for bifacial 2D models"; "Max. tilt axis for the bifacial 2D model" (2 deg); module-layout thresholds and size limits (warning above 1 MWp, error above 5 MWp); horizon height above which the far-albedo contribution vanishes (20 deg); "Long term Pmp degradation Current sharing"; weather data distance for auto synthetic proposal (15 km); maximum allowed time shift in weather data; upper temperature reference for muPmpp default (45 deg C).
- IT relevance (analysis): medium. Reproducibility matters for bankable reports and for tender documents.
- Meridiana note (analysis): store every non-default parameter inside the project/variant and print the list of non-defaults in the report; this fixes a PVsyst weakness PVsyst itself acknowledges.

#### 1.1.2 Orientations and mounting types

##### 1.1.2.1 The PVsyst 8 orientation model and procedure
URLs: https://www.pvsyst.com/help/project-design/orientations-in-v8/index.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/orientations-procedure.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/system-and-3D-attributions.html , https://www.pvsyst.com/help/release-notes/index.html#exec-1--new-features_2

- **Concept** (new in 8.0.0, Nov 2024): an *orientation* is the central entity that connects electrical sub-arrays (System) with 3D-scene tables. Unlimited number of orientations per project; fixed planes and trackers (even trackers with different axes/strategies) can coexist; "unlimited sheds/trackers" orientations can coexist with 3D-defined ones; bifacial allowed in several orientations; stand-alone systems can now have several sub-arrays/orientations. In v7 there was a single orientation (except "fixed plane multi-orientation").
- **Procedure**: (1) define one or more orientations (dropdown of field types; auto-generated descriptive name optional; "Add orientation"; delete allowed if one remains); (2) define the electrical system, each sub-array linked to one (or two, "mixed") orientation; (3) optionally build 3D fields able to receive all modules of each orientation; (4) check with "System overview".
- **Sub-array definition** (for the orientation link): a group of identical strings in parallel on one inverter model; each string = one module model, optionally one optimizer model, NModSeries modules; Nmodules = Nstrings x NModSeries. One orientation can feed several sub-arrays.
- **3D attribution**: every 3D field (single table, tracker, array of tables/trackers) is automatically attributed an orientation (a new one is created if none matches, e.g. trackers when only a fixed orientation exists). Module count and area per orientation must match the system within tolerance; on leaving the 3D scene PVsyst checks consistency (small discrepancies tolerated, large ones block simulation). Field sizes "by modules" are advised for exact matching.
- **8.0.x additions** (release notes): "Create orientation from selection" via right-click in the 3D scene (8.0.7); add PV objects to an existing orientation by right-click (8.0.10); orientation management window (Shift+Ctrl+O) with tree of orientations > sub-arrays/3D fields, drag-and-drop reassignment, orphan list, analysis tab (details in 1.1.6).
- IT relevance (analysis): high. Italian residential roofs commonly have 2-4 roof faces feeding one inverter (2 MPPT), and C&I roofs often mix pitches and flat areas.
- Meridiana note (analysis): adopt the orientation-centric data model, but bind it to the 3D model by construction (modules placed in 3D are the system), so the area/module-count reconciliation PVsyst asks the user to do becomes automatic.

##### 1.1.2.2 Plane orientation modes (field types)
URLs: https://www.pvsyst.com/help/project-design/orientations-in-v8/plane-orientation-modes.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/orientations-procedure.html , https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/object-types/tracking-planes.html , https://www.pvsyst.com/help/glossary/3d-editor/dome.html , https://www.pvsyst.com/help/glossary/3d-editor/field.html

| Mode | What it models | Inputs | Notes / limits stated |
|---|---|---|---|
| Fixed tilted plane | Single fixed orientation | Tilt, azimuth (drag red dots in the dynamic diagram); in 3D, tables may have a base slope, making the real orientation differ | 3D fixed fields: single tables, arrays of tables, coplanar multi-rectangles (roofs with chimneys), custom polygons. Quick orientation-optimisation graph shown (1.1.2.6). |
| Domes | Two coupled orientations with opposite azimuth and base slope (usually E/W) | Tilt, azimuth | One 3D object, two orientations; yield almost independent of azimuth; very small row spacing (whole area covered); not suited for bifacial. Domes can be converted to fixed tables (8.0.5). |
| Seasonal tilt adjustment | Tilt changed twice a year | Winter tilt, summer tilt, months of each position | Grid limitation dispatched according to the seasonal tilt (fix 8.0.8). |
| Unlimited sheds | Regular rows with 2D mutual shading, no 3D scene | Number of sheds, pitch, sensitive width, top/bottom inactive bands (shows GCR and limit angle); optional electrical shading (partitions, cell width) | Continuous rows, no gaps, edge effects neglected; use for long rows. |
| Unlimited sun-shields | Façade sun-shields with 2D mutual shading | As sheds | Rarely used, not advised; only for exactly south facades. |
| Unlimited trackers (horizontal axis) | Regular N-S horizontal-axis tracker rows, 2D model, no 3D scene | Sheds parameters + Phi limits (mechanical stroke), backtracking, tracking calculation mode (astronomic or irradiance optimisation) | Electrical-shading parameters only visible without backtracking (backtracking is assumed to create no mutual shading). Animated sun/tracker view (drag the sun). |
| Tracking, tilted axis | Single-axis tracker with tilted axis (e.g. following a hill) | Axis tilt and azimuth, tracking limit angles, Phi limits, backtracking, calculation mode, wind stow | Phi = 0 when plane azimuth = axis azimuth; axis tilt should be <= latitude; arrays need a 3D scene (only way to compute mutual shading). |
| Tracking, horizontal N-S axis | Tilted axis with tilt = 0 (most common utility case) | Same as above | Changing axis tilt to/from 0 switches type automatically. |
| Tracking, horizontal E-W axis | Follows sun height (seasonal) | Phi = plane tilt, limits -90 (vertical north) to +90 (vertical south) | "Not advised" (very low gain). Backtracking needs several arrays. |
| Tracking, vertical axis | Fixed tilt, rotating with sun azimuth | Tilt, stroke | High latitudes, rotating "dish" carrying shed rows, floating trackers; a common axis can be defined in the scene (7.2.4). |
| Tracking sun-shields | Special case of horizontal E-W axis on facades | Stroke, backtracking | Backtracking "probably the only reasonable way" to operate. |
| Tracking, two axes | Plane always normal to the sun | Mechanical limits in tilt and azimuth | No backtracking for 2-axis trackers. Concentration (CPV) parameters live here (1.1.4). |
| Tracking 2-axis, frame N-S / frame E-W | Tables rotating within a rotating frame (same irradiance as 2-axis, different mutual shading) | Orientation parameters; frame size in the 3D field | Backtracking only table-to-table inside the frame, not between frames. |

- Stroke (mechanical) limits are part of every tracking dialog; the 3D construction dialog lets the user test all rotations, and a one-day shading animation helps optimise the layout by trial and error.
- IT relevance (analysis): fixed tilted plane and domes (E/W on flat industrial roofs) are the daily bread; unlimited sheds for flat-roof C&I and quick ground studies; horizontal/tilted single-axis trackers for utility and agrivoltaic plants (often on sloping terrain). Vertical-axis, E-W axis, sun-shields and 2-axis frames are niche in Italy.
- Meridiana note (analysis): offer the same type list but with geometry-first editing (draw rows on the site, read GCR/limit angle live).

##### 1.1.2.3 Tracking strategies
URL: https://www.pvsyst.com/help/project-design/orientations-in-v8/tracking-strategies.html

- **Astronomic**: angle minimising the incidence angle for the sun position (specific algorithm per tracker type).
- **Irradiance optimisation**: chooses the angle maximising POA irradiance; because sky diffuse transposes as (1 + cos(tilt))/2, the optimum under fully overcast sky is horizontal (Phi = 0). Available only for one-axis trackers (incl. unlimited). Search range/diffuse estimate corrected in 8.0.16.
- **Backtracking**: see 1.1.2.4.
- **Wind stow**: moves trackers to a stow angle above a wind threshold; requires weather files with hourly wind; only tilted-axis and horizontal N-S trackers; defaults 12 m/s and 0 deg, both user-editable. Since 8.1.6 wind stow and irradiance optimisation are also accounted for in the bifacial back-side model.
- IT relevance (analysis): medium-high for utility trackers; wind stow requires credible wind data (PVsyst itself says wind data is unreliable for thermal use).

##### 1.1.2.4 Backtracking (incl. hills, parameters, performance, cosine effect)
URLs: https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/index.html , https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/backtracking-on-a-hill.html , https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/backtracking-parameter-management.html , https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/backtracking-performance-ratio.html , https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/backtracking-performance.html , https://www.pvsyst.com/help/project-design/shadings/backtracking-strategy/cosine-effect.html , https://www.pvsyst.com/help/glossary/solar-geometry/base-slope.html

- **Principle**: when mutual shading would start, trackers rotate back to avoid it. Standard tracking loses energy through electrical mismatch under shading; backtracking loses through mis-orientation (cosine effect, P = I x A x cos(theta)) and higher IAM, and through reduced albedo but increased front diffuse. Main advantage: avoids the electrical shading effect.
- **Algorithm**: one common tracking angle for all trackers of an orientation group, computed each time step from a reference width/pitch ratio = "backtracking GCR" (by default the shading GCR). Trackers with smaller pitch than the reference get shaded (possible electrical losses); larger pitch start backtracking too early (irradiance loss). Requires a perfectly regular array on flat horizontal terrain for exactness.
- **Supported**: horizontal N-S axis; tilted axis if no misalignment within a group ("rectangular" arrays); sun-shields; horizontal E-W axis (needs several arrays); 2-axis frames (table-to-table within the frame only). **Not supported**: 2-axis trackers; slope-aware ("advanced") backtracking; per-tracker or AI-optimised angles; "tilt only when irradiation improves" strategies.
- **Backtracking management tool** (3D editor > Tools): lists trackers by decreasing pitch per orientation group. "Automatic" picks the highest GCR in the scene; "custom" lets the user pick another reference pair (trackers with higher GCR highlighted in red, warning; main/secondary reference marked green/orange since 8.0.21); "manual override" of pitch, width and inactive bands used only for the angle computation (e.g. narrower table to emulate half-backtracking; asymmetric inactive bands for different morning/afternoon behaviour on tilted terrain). Needed for imported scenes and filled zones, where trackers are independent tables. Since 8.0.10 backtracking is allowed on smaller patches of trackers, with a warning.
- **Hills**: with height differences no single angle is perfect (either shading or light lost to the ground). PVsyst's advice: activate electrical shading calculation (strings or module layout), compare with and without backtracking using energy (not PR), inspect with the shading animation, tune with the management tool. Tracker motor consumption is not modelled by default; it can be added as auxiliaries.
- **Diffuse/albedo**: backtracking only removes beam mutual shading; diffuse and albedo remain shaded by neighbours (albedo almost entirely lost except first/last rows), so a near-shading loss of about 2-3% remains.
- **PR caveat**: PR = E_Grid / (GlobInc x PnomPV); backtracking lowers GlobInc, which inflates PR. Compare systems by E_Grid or specific yield.
- **Published comparison** (PVsyst example): 400 kWp HSAT, 1-in-landscape vs 4-in-landscape, mono vs bifacial, Copenhagen vs Nairobi: backtracking matters little at low GCR and always helps at high GCR; gain larger for 1L, lower for bifacial and at low latitude. A Santiago example (+/-60 deg limits, 4L) shows mis-orientation loss slightly below "linear" shading loss without backtracking.
- **Base slope**: tables on sloped ground get a "true" tilt/azimuth that differs from nominal (e.g. tilt 1 deg + base slope 5 deg gives true azimuth 78.7 deg; tilt 20 deg gives 13.5 deg); 3D scene > Tool > "Orientation Understanding Education Tool" visualises it; tables are grouped by normal-vector tolerance (1 deg by default, user-adjustable, e.g. 20 deg to merge).
- IT relevance (analysis): high for Italian utility and agrivoltaic tracker plants, often on rolling terrain: PVsyst's lack of slope-aware backtracking (stated in its own help) is a real gap there.
- Meridiana note (analysis): pvlib.tracking.singleaxis already supports slope-aware (cross-axis tilt) backtracking (see section 3); per-row terrain-following backtracking would be a differentiator.

##### 1.1.2.5 Mixed and average orientations
URLs: https://www.pvsyst.com/help/project-design/orientations-in-v8/mixed-orientations.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/average-orientation.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/mixed-orientation-IVCurves.html , https://www.pvsyst.com/help/project-design/shadings/near-shadings-orientations/automatic-identification.html , https://www.pvsyst.com/help/release-notes/index.html

- **Mixed orientation sub-array**: a sub-array may get a second orientation (if >= 2 orientations exist and > 1 string); the user sets how many strings go to each. With several MPPT inputs: "All inverters mixed" (every MPPT gets strings of both orientations, to share inverter power over the day, e.g. domes) or "One inverter mixed" (MPPTs filled by single orientations, at most one "central" MPPT mixed). During simulation PVsyst combines the I/V curves of both orientations and books the mismatch on the loss diagram; parallel strings of similar voltage give negligible mismatch (< one or a few per mille per year).
- **Heterogeneous strings** (modules of different orientation in one string): not treated ("on our roadmap"), even with optimizers. Release 8.0.15 added "heterogeneous strings" for SolarEdge sub-arrays (see 1.1.10); whether that covers different orientations within a string is [unverified].
- **Average orientation**: an orientation can be "nominal" (user tilt/azimuth) or the area-weighted average of the true orientations of its tables (incl. base slope) for rotundas, close BIPV planes, tables following a hill. Simulation: mutual shading from the real table positions, but transposition for the single average orientation (an approximation on GlobInc). The help page says no tool evaluates that error yet, while release 8.0.8 lists a new Orientation-management tab estimating "the impact of table orientation dispersion on GlobInc" (inconsistency between pages).
- **Automatic grouping on 3D import / zones**: help page: grouped by nominal tilt and azimuth within 0.1 deg (base slope ignored), then average tilt/azimuth/base slope computed. Release notes: since 8.0.15 an import creates one single averaged orientation by default (option to re-enable automatic multi-orientation detection); since 8.0.19 grouping uses project-defined tolerances and existing orientations.
- **Mixed-orientation I/V tool** (Tools > Electrical behaviour of PV arrays, "heterogeneous arrays" tab): two sub-arrays in parallel with different orientation, module type or number; clear-day profile with adjustable amplitude and diffuse fraction, module temperatures from irradiance; a time-of-day slider shows the resulting I/V curve, the relative loss, the double maximum when voltages differ (risk of MPPT locking on the secondary peak) and the effect of missing blocking diodes.
- IT relevance (analysis): very high for residential (E + W roof faces on one MPPT, very common) and for hill-side ground plants (average orientation).
- Meridiana note (analysis): compute transposition per table (or per cluster) instead of one averaged plane; the cost is modest with vectorised pvlib calls and removes PVsyst's approximation.

##### 1.1.2.6 Orientation optimisation tools
URLs: https://www.pvsyst.com/help/project-design/orientations-in-v8/optimization-tools.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/orientation-optimization.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/shed-optimization.html , https://www.pvsyst.com/help/project-design/simulation/optimization-tool/index.html , https://www.pvsyst.com/help/project-design/simulation/optimization-tool/create-new-parametric-scan.html , https://www.pvsyst.com/help/project-design/simulation/optimization-tool/view-existing-scan.html , https://www.pvsyst.com/help/glossary/meteo-data/transposition-factor.html

| Tool | Where | What it computes | Inputs | Outputs / caveats |
|---|---|---|---|---|
| Quick orientation optimisation | Orientation dialog, fixed planes | Transposition factor around the chosen tilt/azimuth and the likely optimum | Site monthly weather; period year / winter / summer | Rough (monthly-value algorithm, may differ from the full simulation); e.g. Marseille 15 deg tilt = about 7.8% below yearly optimum |
| Transposition factor tool | Tools > Transposition factor | Table of monthly transposition factors (GlobInc/GlobHor) for a tilt x azimuth grid, any weather file (synthetic from monthly if needed), optional horizon | Weather file, azimuth min/max/step, tilt step, horizon | Stored as `*.TFT`; iso-transposition plot labelled with loss vs optimum; tables (period or monthly) incl. expected gains of usual tracking systems; optimisation period year/winter/summer/chosen months |
| Sheds tilt optimisation | Unlimited sheds > "Show Optimization" | Annual irradiation gain vs tilt at constant limit angle (GCR shrinks with tilt) | Site, weather (incl. diffuse, albedo) | Curves: transposition, after linear shading, electrical shading loss; GCR bars. Example optimum about 36 deg (transposition) vs about 31 deg (real yield). PVsyst advice: low tilts (5 deg vs 30 deg nearly doubles installable power for about 9% efficiency loss) and limit angle about 18-22 deg; frameless modules at low tilt |
| Optimisation tool (parametric scan) | Advanced simulation > Optimization tool | Full simulations over a parameter grid | Tilt and azimuth (fixed tilt or unlimited sheds), pitch and GCR (3D sheds only); min/max/steps; time estimate | Stored per variant; variables GlobInc, GlobEff, EArray, E_Grid; 1D curves or 2D colour maps, max marker, sliders for non-displayed parameters. The help states it is only available with 3D shed fields, but also lists tilt/azimuth for unlimited sheds (inconsistent pages). |

- IT relevance (analysis): high. Tilt/pitch trade-offs on flat roofs and ground plants, and limit-angle rules, are routine in Italian design; transposition maps help clients with non-south roofs.
- Meridiana note (analysis): replace the separate tools by one interactive "design space" view (tilt x azimuth x GCR heat map with the current design marked), computed by the same engine as the simulation.

##### 1.1.2.7 Sheds and sun-shield mutual shading (2D model) and its combination with 3D
URLs: https://www.pvsyst.com/help/project-design/orientations-in-v8/sheds-mutual-shadings.html , https://www.pvsyst.com/help/project-design/orientations-in-v8/sun-shields-mutual-shadings.html , https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/near-shadings-and-sheds.html , https://www.pvsyst.com/help/glossary/3d-editor/shed.html , https://www.pvsyst.com/help/glossary/solar-geometry/profile-angle.html , https://www.pvsyst.com/help/glossary/solar-geometry/transverse-incidence-angle.html

- **Model**: infinite-length rows; shading fraction as a function of the profile angle (transverse incidence angle) from collector width, tilt and pitch; applies to beam and diffuse (and albedo); first row unshaded, so the generic factor is multiplied by (n-1)/n ("linear" shading).
- **Electrical effect**: "partition model": a partition (part of a row) produces zero beam if its bottom cell row is fully shaded, otherwise proportional to the shaded fraction; requires number of partitions across the row width and the cell width. Thin-film modules with long cells placed transversally greatly reduce the effect. (Detailed partition/module-layout models: 1.1.8.)
- **Where the 2D model is used**: Orientation (unlimited sheds/trackers/sun-shields); Tools > Tables and graphs of solar parameters (geometry on a height/azimuth diagram); Tools > Monthly weather computations (quick yearly shading loss).
- **Sheds in 3D vs in Orientation**: never both at once (double counting). 3D sheds include edge effects and partitions; the computation grows with the square of the number of elements (several hundred rows may be unfeasible). Special mode for huge plants: unlimited sheds in Orientation + a horizontal plane in 3D representing the ground occupation, to account for surrounding obstacles approximately.
- **Sun-shields**: at best half of the diffuse reaches them (wall), strong beam shading at low latitude and for non-south facades; only the top row is a good collector.
- IT relevance (analysis): high (flat-roof C&I rows, quick ground studies); sun-shields (frangisole) low.

##### 1.1.2.8 System overview, consistency checks and GCR definitions
URLs: https://www.pvsyst.com/help/project-design/orientations-in-v8/system-overview-tool.html , https://www.pvsyst.com/help/project-design/shadings/near-shadings-orientations/matching-the-variant.html , https://www.pvsyst.com/help/glossary/meteo-data/gcr-ground-coverage-ratio.html , https://www.pvsyst.com/help/glossary/3d-editor/table.html

- **System overview** (button in several dialogs): four lists with warnings/errors: orientation parameters; System-vs-Shadings compatibility (orientations and areas); system parameters (sub-arrays, orientation, modules, inverters); shading-scene parameters (3D sub-fields, area, orientation).
- **Matching rules**: each orientation must be linked to a sub-array; active PV area and module count per orientation must match within tolerance (red error blocks; orange warning, e.g. module count mismatch, allows simulation).
- **GCR** (display only, not used directly in the simulation): GCR = PV area / ground area, with four definitions: GCRMod (module area only), GCRShd (area contributing to shading: modules, inter-module gaps and some inactive bands; table per system type), GCRBT (used for backtracking, default = GCRShd, overridable), GCRBifi (all inactive zones included). Ground area: pitch x row length for unlimited sheds/trackers; per array from pitch and length in 3D arrays (circulation areas excluded); for imported irregular scenes, average table-to-next distance excluding double pitches; no GCR for BIPV/sun-shields. Report labels "Backtracking GCR" and "Average GCR" since 8.0.0.
- IT relevance (analysis): high; GCR/land-use figures are needed for Italian ground-mounted and agrivoltaic permitting documents [analysis; specific Italian requirements not verified here].
- Meridiana note (analysis): always state which GCR definition a number uses (PVsyst needs four).

##### 1.1.2.9 Solar-geometry conventions used by orientations
URLs: https://www.pvsyst.com/help/glossary/solar-geometry/plane-azimuth.html , https://www.pvsyst.com/help/glossary/solar-geometry/plane-tilt.html , https://www.pvsyst.com/help/glossary/solar-geometry/incidence-angle.html , https://www.pvsyst.com/help/glossary/solar-geometry/longitudinal-incidence-angle.html , https://www.pvsyst.com/help/glossary/solar-geometry/profile-angle.html

- Plane azimuth: northern hemisphere south = 0, west = +90, east = -90, north = 180; southern hemisphere north = 0 (west +90, east -90). Tilt = angle with horizontal. Incidence angle = angle to plane normal. Profile angle = sun height in the vertical plane perpendicular to a given azimuth (used for all mutual-shading calculations). Transverse incidence angle (for horizontal-axis trackers = 90 deg - Phi); longitudinal incidence angle (to be minimised by single-axis trackers).
- Meridiana note (analysis): pvlib uses azimuth 180 = south (clockwise from north); Meridiana must convert and should show both conventions (Italian practice commonly uses south = 0 as in PVsyst/PVGIS [analysis]).

#### 1.1.3 Bifacial systems

URLs: https://www.pvsyst.com/help/project-design/bifacial-systems/index.html , https://www.pvsyst.com/help/project-design/bifacial-systems/2d-bifacial-model-conditions.html , https://www.pvsyst.com/help/project-design/bifacial-systems/bifacial-system-2-dimensional-unlimited-sheds.html , https://www.pvsyst.com/help/project-design/bifacial-systems/bifacial-system-2-dimensional-unlimited-trackers.html , https://www.pvsyst.com/help/project-design/bifacial-systems/bifacial-systems-nbofsheds.html , https://www.pvsyst.com/help/project-design/bifacial-systems/bifacial-systems-procedure.html , https://www.pvsyst.com/help/project-design/bifacial-systems/bifacial-systems-results.html , https://www.pvsyst.com/help/physical-models-used/irradiation-models/albedo.html , https://www.pvsyst.com/help/release-notes/index.html

##### 1.1.3.1 Model physics (2D view-factor model)
- **Bifaciality factor** (PAN parameter): rear/front nominal efficiency ratio; the rear side follows the same one-diode model; default upper limit 98% (8.0.12); small factors allowed for CdTe (8.0.0).
- **Ground irradiance** per ground point along a 2D cross-section: beam reaches the ground only between rows (recomputed every time step); sky diffuse acceptance per ground point by an isotropic integral over the visible sky (geometry only; once for fixed systems); for one-axis trackers ground integrals and view factors are pre-computed at 7 Phi positions and interpolated with cubic splines.
- **Shed transparent fraction**: extra ground light proportional to GHI x transparency (gaps between cells/modules; also a proxy for small gaps between tables).
- **Re-emission**: ground albedo (ground under the array, distinct from the project far albedo), Lambertian/isotropic, no specular reflection.
- **View factors**: rear-side and front-side view factors per ground point (computed once from geometry), IAM applied per ray; rear-side IAM always with the simple Fresnel model for glass without AR coating. Rear irradiance = ground irradiance x view factor x ground area / collector area.
- **Other rear contributions**: sky diffuse seen by the rear (DifSBak); beam on the rear (BeamBak: fixed rows in morning/evening, vertical E-W rows; never for trackers).
- **Structure shading factor** (rear): default 5% (projection-area approximation; "indirectly validated" by measurements).
- **Rear mismatch loss factor**: default 10% (no physical model; from comparisons with measurements), applied only to the rear contribution.
- **Electrical conversion**: rear irradiance x bifaciality factor is added to the front effective irradiance before the one-diode model.
- **Front-side ground reflection** (ReflFrt): reflection from the ground between rows onto the front side, IAM-weighted; exists in every system but is only computed when the bifacial model is active (crucial for vertical E-W bifacial).
- **Hypotheses summary**: isotropic diffuse, isotropic ground re-emission with given albedo, rear irradiance added to front before the one-diode model.

##### 1.1.3.2 Application models and validity conditions
- **Available**: 2D "unlimited sheds" (fixed rows) and 2D "unlimited trackers" (horizontal axis). A model based on the full 3D scene and a general 3D tracker treatment are announced for future versions ("next version", "ultimate version").
- **Orientation types accepted**: unlimited sheds, fixed tilted plane, unlimited trackers horizontal axis, tracking horizontal axis N-S, tracking tilted axis. The stated 3D-scene condition for trackers requires an average axis tilt below 2 deg (advanced parameter "Max. tilt axis for the bifacial 2D model"), so in practice only near-horizontal axes qualify [interpretation: the help does not say this explicitly for "tilted axis"].
- **With a 3D scene** PVsyst derives tilt/axis, table width, representative pitch and number of rows from the scene: pitch RMS deviation below 0.4 m (threshold = 4 x advanced parameter "Pitch RMS limit for bifacial 2D models"), table heights (fixed) or tracker widths homogeneous within 1 cm or 1%. Since 8.0.14 pitch irregularity and axis-tilt violations are warnings, not errors. The user can override number of rows and pitch (affects only rear and reflected irradiance). Other geometric values in the bifacial window are exploratory and reset on exit.
- **Height above ground** (bottom of sheds, or tracker axis) is not taken from the 3D scene: must be entered in the bifacial dialog.
- **Ignored**: other 3D objects and tables of other orientations for rear irradiance (only row-to-row shading + structure factor). Multiple orientations allowed since 8.0.0 but each must be spatially separate; domes and E-W fixed-tilt bifacial cannot be modelled (mutual shading between orientations neglected; PVsyst notes these have little rear irradiance except carports and does not detect the case automatically).
- **Few rows**: first-row front shading factor multiplied by (Nrows-1)/Nrows; first-row front reflection underestimated; last-row rear sees no terrain beyond and no "next row" sky shading; PVsyst discourages the 2D model for 2-3 row experimental systems (error scales as 1/Nrows); single vertical rows (e.g. noise barriers) give rear irradiance similar to a normal front calculation.
- **Trackers vs fixed**: bifacial gain slightly lower for trackers (less beam reaching the ground: e.g. 44% vs 60% beam fraction on ground on a clear June day at GCR 41%), partly compensated by better front gain and rear sky diffuse.

##### 1.1.3.3 Procedure (user inputs)
- In System, choose a module flagged bifacial; a "Bifacial system" button appears. Options: model Disabled / Unlimited sheds or trackers; **ground albedo**: None (disables the model) / Constant / Monthly / From file (hourly or sub-hourly time series via the shared CSV import, since 8.1.2).
- Model page: geometry pre-filled from orientation/3D (pitch, width, rows), height above ground (user).
- General simulation parameters page: indicators computed by the model (beam ground factor, diffuse ground factor, re-emission form factor; module bifaciality factor from the PAN) and user parameters (shed transparent fraction, ground albedo, structure shading factor 5%, mismatch loss factor 10%).
- Mixed-orientation sub-arrays need two independent bifacial models (dropdown); sub-arrays sharing an orientation share one bifacial model. User-specified pitch for the irradiance model possible since 8.0.0.
- Exploration window: row geometry, ground irradiance on clear days for chosen dates, monthly daily values, animated drawing (beam on ground, diffuse acceptance, re-emission), distributions along the ground.

##### 1.1.3.4 Results and variables
- Loss diagram: rear-side branch beside the front-side energy flow. Variables: GlobGnd (global on ground), ReflLss (1 - albedo), BkVFlss (view-factor loss), DifSBak, BeamBak, BackShd (structure shading), GlobBak (total rear, also as % of GlobEff), EArrNom (STC energy incl. rear x bifaciality), MismBak (rear mismatch, as % of total), ReflFrt (front ground reflection); DiffGnd exportable (8.0.12). Loss-diagram values exportable to Excel from the report editor.
- System bifaciality factor = power-weighted average over sub-arrays (monofacial orientations count as 0 since 8.1.1, which lowers the displayed average without changing end results). PRBifi (bifacial PR accounting for the bifaciality factor) in report and monthly tables since 8.0.12.
- Example in help (Demo Utility VC2): albedo 0.3 gives 70% ground reflection loss; 10% rear mismatch gives about 0.7% extra system loss.
- IT relevance (analysis): high for Italian utility and agrivoltaic plants (bifacial modules on trackers or elevated fixed structures, vertical E-W bifacial fences); white membranes on C&I flat roofs [analysis]. PVsyst's inability to model E-W/dome bifacial and to use the real 3D scene is a real gap for agrivoltaic layouts with irregular rows.
- Meridiana note (analysis): pvlib.bifacial.infinite_sheds implements a comparable 2D view-factor model (section 3); a 3D ray-traced rear-irradiance model on the actual scene would exceed PVsyst.

#### 1.1.4 Concentrating systems

URLs: https://www.pvsyst.com/help/project-design/concentrating-systems/index.html , https://www.pvsyst.com/help/project-design/concentrating-systems/defining-a-concentrating-system.html , https://www.pvsyst.com/help/release-notes/index.html#exec-1--version-808

- **Scope**: only high-concentration (about 500x) 2-axis CPV; accuracy "not quite established". Low concentration (CPC, 1-axis parabolic) not supported (would need detailed optics and irradiance distribution).
- **Optics in the 2-axis tracking dialog**: diffuse fraction accepted (usually near 0), acceptance half-angle for full efficiency, limit angle where efficiency reaches 0 (linear decrease in between, booked as tracking loss); CRmax(1-axis) = 1/sin(theta), CRmax(2-axis) = 1/sin^2(theta) (Kreith and Kreider 1978). Tracking errors not modelled.
- **Module**: CPV defined in the PV module "Size and Technology" page; treated as a flat module with sensitive area = optical aperture; STC at 850 W/m2 and 25 deg C; one-diode model used phenomenologically (manufacturer's Isc, Voc, Imp, Vmp; custom temperature coefficient); optical aberrations neglected; thermal loss factor U (Kc) from the manufacturer.
- **CPV Utilization Factor**: double-linear correction vs DNI, air mass and ambient temperature (spectral and mechanical effects), from manufacturer long-term measurements.
- Losses shown in the loss diagram: negligible diffuse acceptance and full loss at heliostat tracking limits. Diffuse and focal losses fixed in 8.0.8.
- IT relevance (analysis): negligible (CPV is practically absent from current Italian projects); phase 3 or never for Meridiana.

#### 1.1.5 Far shadings / horizon

**Sources:**
- https://www.pvsyst.com/help/project-design/shadings/index.html
- https://www.pvsyst.com/help/project-design/shadings/far-shadings-horizon/index.html
- https://www.pvsyst.com/help/project-design/shadings/far-shadings-horizon/importing-horizon-profiles.html
- https://www.pvsyst.com/help/project-design/shadings/far-shadings-horizon/importing-SolarAnywhere-horizon-profiles.html
- https://www.pvsyst.com/help/project-design/grid-connected-system-definition/project-design-tutorial.html (sections "Far shadings, Horizon profile", "Importing Horizon from Solmetric SunEye", "... Carnaval", "... Horiz'ON")
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/treatment-of-the-beam-component.html
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/treatment-of-the-diffuse-component.html
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/treatment-of-the-albedo-component.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/near-shadings-tutorial.html#horizon-far-and-near-shading-cumulation
- https://www.pvsyst.com/help/project-design/results/simulation-variables-meteo-and-irradiations.html
- https://www.pvsyst.com/help/getting-started/file-organisation/user-data/workspace/index.html#shadings-directory-shadings
- https://www.pvsyst.com/help/release-notes/index.html

**What it is and when it is valid**
- A horizon line (far shading) is for obstacles far enough to act on the whole field at once: the sun is either visible or not visible on the entire array.
- Rule of thumb: obstacles farther than about **10 times the PV field size**. Nearer obstacles must go in the near-shading 3D scene (1.1.6).
- A horizon whose heights are all **below 2°** is treated as insignificant. It is ignored in the simulation and not shown in the report.
- Horizon definition is also available in preliminary design (https://www.pvsyst.com/help/preliminary-design/index.html) and in the meteo/tools areas. See 1.5 (preliminary design), 1.6 (weather data) and 1.8 (tools) for those, and 1.6.13 for the help's note "Horizon in weather data".

**Horizon editor (inputs)**
- Data model: a broken line of (azimuth, height) points in degrees, any number of points, drawn over the sun-path diagram of the site.
- Editing:
  - drag the red points with the mouse, or type values in edit boxes;
  - right-click on empty space to add a point;
  - right-click on a point to delete it.
- On-site acquisition suggested by the help: compass plus clinometer or theodolite (land-surveyor instruments), detailed maps, panoramic or fish-eye photographs.
- Storage: `.HOR` files in the workspace `\Shadings` folder. The PVsyst `.HOR` format is "not an ASCII file" and cannot be exported to other software.

**Import sources and formats**

| Source | How PVsyst gets it | Notes from the help |
|---|---|---|
| PVsyst `.HOR` | From the workspace | Reuse across projects |
| Generic CSV/text | File import | Columns separated by comma, semicolon, tab or space. Any line with text is a comment; a comment such as "Latitude 25.3°, Longitude 44.1°" becomes the horizon's description. One line per point (azimuth, height in degrees). Before import the user sets the azimuth rotation direction (clockwise or counter-clockwise) and the North azimuth angle. |
| Meteonorm horizon files | File import | The file name carries the site coordinates. Since 8.1.0 the Meteonorm horizon import uses the local Meteonorm V9 DLL, with no internet needed; 8.1.2 fixed its azimuth handling (release notes). The import page also lists a "Meteonorm web service". |
| **PVGIS** ("PVGIS Horizon From WEB") | Direct web import, fully integrated (no manual download) | Worldwide, free. PVGIS 5.3 has been the default since 8.0.7; 8.0.17 fixed the loss of negative azimuths (release notes). |
| SolarAnywhere API | Direct web import, since 8.0.0 | Needs an API key entered in Settings > Network. The key comes with SolarAnywhere Sites or Typical Year Unlimited licences. The help warns that SolarAnywhere far-shading data **includes nearby objects** (trees, buildings). |
| Solmetric SunEye | File import | Use `ObstructionElevation.csv`, not the old `Sky0x_PVsyst.hor` made for PVsyst 4. Remove near objects from the record. |
| Carnaval (France and neighbouring countries, georeferenced with altimetry) | File import | Do not use Carnaval's near-objects option. Rename `YourProject.masque.txt` to drop ".masque", because PVsyst rejects file names with two dots. |
| Horiz'ON + "Camera Master" | File import | Panorama assembled from photos taken every 20° of azimuth; the horizon is drawn by mouse and the file is directly readable. |
| Horicatcher | - | [not in help]: no Horicatcher import is documented in 8.1. |

- **Location accuracy warning.** For gridded sources (PVGIS, Meteonorm, Carnaval) the coordinates must be precise. 1° of latitude is 111 km, the 2nd decimal about 1.1 km and the 4th decimal about 11 m, which "can still have a big impact" on steep slopes.

**Model in the simulation**
- **Beam and circumsolar: on/off.**
  - The sun is either above or below the horizon line.
  - With hourly data, PVsyst finds the exact time within the hour when the sun crosses the horizon and applies that fraction of the hour as a loss to beam and circumsolar, before transposition.
- **Diffuse.**
  - Modelled as the integral of isotropic radiance over the part of the sky the plane sees above the horizon line, assuming no radiance from behind obstacles.
  - The result is independent of the sun, so it is constant over the year.
  - In the simulation the far-shading, near-shading and IAM factors are multiplied direction by direction inside a single integral (plus soiling). This gives one constant loss factor for the "effective diffuse" (treatment-of-the-diffuse-component.html).
- **Albedo.**
  - Decreases linearly with horizon height and reaches zero for horizons above **20°**; the 20° value can be changed in the hidden/advanced parameters.
  - The user also chooses which fraction of the albedo to keep, depending on obstacle distance: near obstacles give almost no albedo.
- **Far and near shadings do not add up.** The beam is first set by the horizon (on/off) and the near-shading factor is then applied to what remains. A sun position already hidden by the horizon causes no further near-shading loss.
- **Caveat stated by PVsyst.** The diffuse and albedo hypotheses "require more experimental investigation". Their effect is small for low tilts and larger for steep or vertical planes.

**Outputs**
- Simulation variables:
  - `GlobHrz`: global on the collector after the horizon;
  - `FHrzBm = BeamHrz/BeamInc`;
  - `FHrzGl = GlobHrz/GlobInc` (simulation-variables-meteo-and-irradiations.html).
- The report shows a horizon plot; since 8.0.5 this also covers tracking orientations (release notes).
- The loss diagram has a far-shading (horizon) step. Its exact label is [unverified] here; see the results section.

**IT relevance:** high.
- Alpine and Apennine valleys, and hilly or coastal relief in the South and the islands, often have significant terrain horizons.
- The integrated PVGIS horizon (computed from a terrain elevation model) is the natural free default for Italy.
- In towns, a terrain horizon does not include buildings, so a 3D near-shading scene is still needed.
- A SolarAnywhere horizon already includes nearby objects, which risks counting them twice if the same objects are also built in 3D.

**Meridiana note (analysis):**
- Keep horizons in an open text format (CSV/JSON) rather than a binary `.HOR`.
- Overlay several sources (PVGIS, measured, Meteonorm) on the sun-path diagram for comparison.
- Warn when a horizon source includes near objects and a 3D scene is also defined.

#### 1.1.6 Near shadings: the 3D scene

**Sources:**
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/index.html, near-shadings-procedure.html, near-shadings-tutorial.html, near-shadings-and-sheds.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/global-referential-orientations.html, global-scene-building-tools.html, near-shadings-auto-save.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/construction-tools/object-positioning.html, object-selection.html, groups-of-objects.html, hand-drawing-objects.html, zones-of-tables.html, conversion-of-fixed-tables-to-trackers.html, conversion-single-tables-to-arrays-of-tables.html, conversion-single-tables-to-single-array-of-tables.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/object-types/elementary-objects.html, building-or-composed-objects.html, ground-objects.html, pv-fields.html, tracking-planes.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/view-tools/observer.html, shadows-drawing.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-advanced-selection/List-and-management-of-objects.html, Shadow-casting-options.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-import/pv-collada-file-format.html, sketchup-and-other-cad-software.html, helios-3d.html, ground-image-and-topography/index.html, ground-image-and-topography/csv-ground-data.html, ground-image-and-topography/ground-image-and-topography-import.html, ground-image-and-topography/ground-image/index.html, …/ground-image-control-principles.html, …/ground-image-control-usage.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-orientations/introduction.html, automatic-identification.html, list-of-orientations.html, matching-the-variant.html, orientation-management-window.html, use-case-checking-scene-validity.html, use-case-complex-pvsyst-scene.html, use-case-helios3d.html
- https://www.pvsyst.com/help/project-design/shadings/partial-shadings-and-calculations.html
- https://www.pvsyst.com/help/project-design/shadings/shadings-and-module-layout-vocabulary.html
- https://www.pvsyst.com/help/getting-started/file-organisation/user-data/workspace/index.html#shadings-directory-shadings
- https://www.pvsyst.com/help/external-contributions.html#avi-generation-tool
- https://www.pvsyst.com/help/release-notes/index.html

PVsyst itself calls near shadings "the most difficult part of the PVsyst software" (https://www.pvsyst.com/help/project-design/shadings/index.html).

##### Main dialog and procedure ("dashboard")

**Dashboard workflow**
1. **Construction/Perspective** opens the 3D editor.
2. On exit, PVsyst checks the scene against the variant:
   - the orientations of the 3D fields must match the "Orientation" part, and PVsyst offers to update that part;
   - the 3D sensitive area must be enough for the modules defined in "System".
3. **Table** computes the shading-factor table, together with the diffuse and albedo factors (constant over the year). The iso-shading diagram is then available (1.1.7).
4. **Use in simulation** offers:
   - *Linear (irradiance)*, fast (interpolated in the table) or slow (full computation at each step);
   - *According to module strings*, with the "Fraction for electrical effect";
   - *Detailed, according to Module Layout* (1.1.8).

**Recommended practice**
- Start with a simple variant and add complexity step by step.
- Module Layout comes last.
- With string partitions defined, two tables are computed at once: linear and according to strings.

**Storage and safety**
- The scene is stored inside the variant (`.VCi`), with no extra file.
- Optional files in the workspace `Shadings/` folder:
  - `.SHD`: complete scene, which "may also include the Shading Factor Table";
  - `.BLD`: building templates;
  - `.SHO`: collections of shading objects.
- **Auto-save**: one file per variant every 5 minutes, named `__auto__<variant>`, kept until PVsyst exits cleanly and recovered via File > Read scene. The tutorial admits the 3D tool "is not fully safe" and advises saving the scene periodically.

**Referential**
- Northern hemisphere: X = West, Y = South, Z = Zenith. Azimuth is measured from South, positive towards West (clockwise).
- Southern hemisphere: X = East, Y = North. Azimuth is measured from North, positive towards West.
- The scene can be built in the architect's or building's referential and then turned to geographic coordinates with **Rotate whole scene** (Ctrl+Alt+R).

##### Object types

| Object | What it is / inputs | Notes |
|---|---|---|
| **PV fields** | Single PV table (rectangular sensitive area plus inactive frame margins); **array of tables** (sheds/rows); **array of domes** (East-West back-to-back tables); **array of trackers**; **rectangular PV planes** (several non-overlapping rectangles in one plane, aimed at BIPV); **polygonal PV plane** (drawn with the mouse); **array of sun-shields** (tables stacked vertically on façades) | Field dialog pages: **Basic parameters** (tilt, number of tables, pitch, layout, "baseline slope" to follow terrain or a roof side, which changes the real orientation and leads to an *average orientation*); **Table size** ("By modules", recommended: area sized exactly for N modules with spacing; or "by sensitive area"; drag handles; frame sizes; in polygons, click to add a module and right-click to remove one); **Partition** (rectangles for electrical shading, 1.1.8). "Field" means the composite object and "Table" one element of it. |
| **Tracking planes** | Define the *Tracking Parameters* first: type, mechanical **stroke limits**, optional backtracking and concentration. **One-axis:** horizontal N-S axis; tilted axis (tilt ≤ latitude); vertical axis (azimuth tracking, e.g. rotating "dish" or floating); tracking sun-shields; horizontal E-W axis. **Two-axis:** full two-axis; frame with horizontal N/S axis; frame with horizontal E/W axis. | Arrays of trackers carry the axis pitch, and mutual shading depends on width/pitch (about the GCR). Two-axis trackers are laid out in rows and columns. A test tool runs through all rotations to check mechanical compatibility. Backtracking parameters are managed in **Tools > Backtracking management**; see 1.1.2 for trackers and backtracking. |
| **Elementary objects** | Library of shapes. **2D:** triangles, rectangle, trapezium, regular polygon, pseudo-circle sectors. **3D:** parallelepiped, square pyramid, triangular/hexagonal/octagonal prism, portion of cylinder. **Building elements:** house with 2-sided roof, tree, roof-like dihedral, 2-sided roof with gables, 4-sided roof, prism chimney. | Sized by parameters or by dragging points in orthogonal views. Colours are defined "at bright sun". Curves are approximated by broken lines (points and surfaces only). |
| **Building / composed objects** | Assembly of elementary objects, made in a secondary 3D window with the same tools | Can be saved as reusable models (`.BLD`). **Cannot contain PV planes**: these must be placed in the global scene. |
| **Ground objects** | Point mesh, from a Helios 3D import, topography download/import, or created | **No shadow casting by default.** Editor: point and rectangle selection, transversal cut view, invert normals; panels for *ground generation* (size, mesh complexity), *selection position*, *extended selection* (extend distance, weight, parabolic "accentuation"); 3-axis gizmo to move points. |
| **Electrical objects** (from PVCollada 2.0) | Inverters, AC/DC combiners, optimizers, transformers, cables | Imported and auto-named ("Inverter #1"...). Their effect is not described [unverified]. |
| Vocabulary | *PV-array/sub-array* = electrical set (N strings × M modules) at inverter inputs; *3D-field*; *Table / 3D subfield*; *Submodule* = cells protected by one bypass diode | shadings-and-module-layout-vocabulary.html |

**Best practices stated by the help (pv-fields.html)**
- Make tables as large as possible, and use arrays rather than individual tables.
- Never one table per module: very slow, and electrical losses come out wrong.
- A partition rectangle should represent one *string*, not one module.
- The bifacial 2D and backtracking models need **regular spacing** between tables.
- Terrain-following tables are grouped under an average orientation, which is a small approximation. Linear mutual shading is still computed table by table.

##### Construction and editing tools (with the documented shortcuts)

| Tool | What it does | Shortcut / notes |
|---|---|---|
| History | Undo / redo | Ctrl+Z / Ctrl+Y |
| Selection | Default (Esc); click (edges only in Technical view); **rectangle** and **lasso** selection (touching vs. fully inside); add with Shift, remove with Ctrl; select all; pick in the objects list | Rectangle Shift+Ctrl+R; lasso printed as "Ctrl+Ctrl+L" (sic); select all Ctrl+A |
| Point of view | Pan; rotate (middle button); perspective F2; top F3; front F4; side F5; **sun view F6** (view from the sun to understand shadows); zoom in F7 / out F8; zoom rectangle; zoom to fit | Zoom to fit Ctrl+F. **Observer** panel for exact "look at / look from" (height, azimuth, distance). |
| Render | **Technical** (wireframe) vs **Realistic** (lighting, custom colours, optional real-time shadows); orthogonal (default for building) vs perspective (for video/report); show Module Layout strings; anti-aliasing, real-time shadows, camera animation, back-faces | View / Render options |
| Measure | Distance; angle; Ctrl snaps to a vertex | Ctrl+L / Ctrl+K |
| Modify | Edit object; move/position; rotate; rotate whole scene | Ctrl+M; Ctrl+B; Ctrl+R; Ctrl+Alt+R |
| Positioning | Dialog plus on-scene gizmo (drag along 1 or 2 axes). Maths: translate, then rotate by azimuth, then tilt about the rotated OX′. Arrow keys with Ctrl move 1 cm, Shift 10 cm, Ctrl+Shift 1 m. | Leave a **small gap** between a PV plane and its support (tutorial: about 2 cm; Helios: ≥ 1 cm). Coincident points break the polygon operations, and a rectangle counts as shaded as soon as one point is shaded. |
| Hand-drawing | Draw with the mouse: triangle, parallelepiped, house, tree, **extruded polygon** (2D contour plus height), rectangular PV table; guided by tooltips | - |
| **Zones of tables** | Draw rectangular, polygonal or free-hand zones on the XOY plane, then **fill** them with tables placed at the correct altitude on underlying objects (e.g. a roof), optionally with **automatic tilt** taken from the support surface. Parameters: label, azimuth, pitch, table spacing, row alignment, distance from ground, automatic tilt, automatic length (one table per row stretched to fit). Tools: select the generated tables, add tables to a row, **slide a row**, **exclusion areas** (masks) | Refilling a zone discards manual row edits; changes are undoable. Filling is faster since 8.1.4. |
| Groups | Named groups (new, rename, delete, clear, insert objects or the selection, remove the selection, select all, "Modify all" opens the object list) | Group management reworked in 8.0.10 |
| Transform / convert | Fixed tables → **trackers** (choose type and parameters); single tables → arrays of tables (one per table); single tables → **one** array of tables (warns that tables may move and orientations get averaged); domes → fixed-tilt tables (8.0.5) | Since 8.0.0 the "Transform" menu holds all transform actions |
| **List and management of objects** | Table of every PV and shading object, with search on #, Type and Name; filter and sort per column; multi-select; **group editing** of cells; copy/paste, including **paste from Excel** (header plus #, Type, Name columns); show/hide columns; context menu; **CSV export**; change a field's orientation; set the number of partitions | Ctrl+G |
| **Shadow casting options** | Per-object switch for casting shadows. All objects cast by default except ground objects. A PV object with casting off still *receives* shadows. Uses: turn on terrain shadows, turn off far irrelevant objects, test an object's impact | Checkbox in each object form, in the tree menu, and in the object list |
| **Partial shading calculation** (subset) | Tools > Use partial shading calculations. Shadings are computed only for a group "Partial shadings selection" (PV fields only) and the resulting factors are **extrapolated** to the whole system. Other objects still cast shadows. | Works with the "linear" and "according to strings" modes only, **not Module Layout**. The report states the share of PV area used. Since 8.0.14 a warning appears below 5 % of the area or below 10 tables. |
| Other 3D Tools menu items | **Backtracking management** (see 1.1.2); **Trackers diffuse shadings definition** (1.1.7); **Thin Objects Analyze tool** (1.1.8); **Orientations management** | "Optimized shading calculation" was removed in 8.0.0 |

##### Visualising shadows
- **Shadows drawing**: shadows for any sun position or date and time. The button must be pressed again after each change.
- **Robustness fallback**: when the polygon intersection/union fails an internal check, PVsyst switches to a grid of points on the PV area. This is "less precise", but always gives reliable results.
- With string partitions, partially shaded partitions are shown in **yellow**, and the two shading factors (lower and upper bound) are displayed.
- **Shadow animation over one day**:
  - plays the shadows and plots the beam loss curve at the same time;
  - gives the daily beam loss for a clear day;
  - shows date, hour, sun position and shading factor for each step;
  - can be scrubbed with a scrollbar and **recorded as a video** (AVI per the external-contributions page; the 8.0.2 release notes fixed video recording).
- **Report view**: File > Save scene view > *Keep this view for the report*. Since 8.0.15, changing this view no longer invalidates the shading table.

##### Orientations in the 3D scene (PVsyst 8)

**Matching rules**
- Each variant orientation must be linked to an electrical sub-array.
- The active PV area and the number of modules per orientation must match the sub-arrays within a tolerance.
- A red error blocks the simulation; an orange warning (e.g. a module-count mismatch) does not.

**Automatic identification**
- The help pages are not fully aligned here:
  - The automatic-identification page groups imported fields by nominal tilt and azimuth within 0.1°, ignoring base slope.
  - The import dialog (default since 8.0.15) creates **one averaged orientation**. An optional "Create multiple orientations" mode groups fields whose nominal orientations differ by less than an "Angular difference between orientations" threshold.
  - Since 8.0.19 the grouping uses tolerances defined in the project.
- In zones, fields are grouped per zone and with other zones that share the same tilt and azimuth.
- For each group PVsyst computes the average tilt, azimuth and base slope.
- Since 8.1.4 the averaging is geometrically correct for varying tilt, azimuth and slope.

**Orientations management window** (Tools menu, Shift+Ctrl+O)
- Tree of orientations, each with its system sub-arrays and 3D fields.
- Add, modify, copy, delete and reorder orientations.
- **Drag and drop** fields between orientations. Deleting an orientation leaves its fields "orphaned" in a right-hand pane, from which they can be reassigned.
- When a field does not fit its orientation, the user chooses between updating the field and "set orientation as average".
- **Analysis** tab: orientation spread, deviation around the average, azimuth and tilt versus base slope.
- Since 8.0.8 a tab estimates the effect of orientation dispersion on GlobInc.
- Since 8.0.7 an orientation can be created from the current selection.

**Other**
- A list panel colours each orientation in the scene.
- Use cases in the help:
  - checking scene validity (area 160 m² vs 50 m² → red error, fixed by resizing);
  - a complex SketchUp scene on a hill, grouped manually with the lasso;
  - Helios3D: domes give two orientations; no limit on the number of orientations since 8.0.

##### Imports and ground

**3D scenes: 3DS, DAE, PVC/PVC2** (File > Import > Import a 3D scene)
- A summary dialog shows object, vertex and face counts.
- Input unit: metres; for DAE the unit is read from the file automatically.
- **Auto-translation** to the origin if the scene is more than 5 km away (editable X/Y/Z).
- Optional 180° rotation, on by default in the southern hemisphere.
- **Material selection** turns faces into PV fields, either fixed tables or trackers (with tracking parameters).
- Orientation rules for imported tables:
  - *Best azimuth*: closest to 0°, the default since 7.4.2;
  - *Longest edge*: the default before 7.4.2;
  - *East/West*: closest to ±90°, for domes.
- "Create multiple orientations" with an angular threshold; otherwise one averaged orientation, computed as the mean of the unit normals.
- Ground topography can come in through materials.
- **AutoCAD**: go through SketchUp → DAE (recommended), or the Autodesk FBX Converter (objects may end up misplaced).
- **Limit**: very detailed scenes make calculation time grow "exponentially". PVsyst does not simplify geometry, so the user should delete objects or turn off their shadow casting.

**PVCollada 2.0** (`.pvc2`, zipped `.pvz2`)
- Open community format based on **COLLADA 1.5**, with the PV data in `<extra>` elements so files stay valid COLLADA.
- **Import only (no export), since 8.1.5.**
- What is imported:
  - tables and trackers (`<instance_table>`, `<instance_tracker>`) with geometry, insets, module orientation, rows and columns, spacing, gaps, posts, nominal azimuth and tilt, and tracker rotation limits;
  - gaps that rotate with the tracker (motors) are imported **without** shadow casting, because PVsyst cannot rotate non-PV objects (8.1.7 recognises `rotate_with_tracker`);
  - electrical objects;
  - terrain (`<instance_terrain>`) as ground objects, without shadow casting;
  - any other geometry as shading objects;
  - component definitions, including PVsyst PAN/OND extensions, used for consistency checks;
  - metadata (latitude, longitude, altitude).
- Consistency checks:
  - distance to the project site;
  - match with the chosen module and inverter;
  - table size against modules × spacing.
- The electrical **circuit** description is not yet imported ("next on our agenda").
- Conventions: `<tracker_slope>` is mapped to the PVsyst tracker "tilt"; azimuths are converted to PVsyst's South = 0° convention.

**PVCollada 1.4.1** (`.pvc`, since 7.0, legacy)
- Created by PVsyst with PVcase on a *modified* COLLADA 1.4.1, so files are not valid COLLADA.
- Mesh extensions:
  - `<frame_parameters>` (module width and height in mm, x/y spacing, manufacturer, name);
  - `<tracker_parameters>` (the same, plus `tracker_type` single/dual, `axis_vertices`, `min/max_phi`, `min/max_theta`).

**Helios 3D** (`.h2p`)
- Tables with inactive bands and terrain-following base slope, which produces a *spread of orientations*.
- **Orientation analysing tool** (View / Plane orientation): a base slope deviates the azimuth by about 2 to 3 times the slope value.
- The spread does not affect the shading calculation. The irradiance is computed once for the average orientation, and the resulting small orientation loss is "not yet taken into account nor evaluated".

**Ground image and topography download** (new in 8.0; File > Import > Download a satellite ground image and/or ground data)
- Uses Bing Maps / Azure Maps for imagery and **gpxz.io** for elevation. The interactive map moved from Bing Maps to Azure Maps in 8.0.10, and OpenStreetMap is a preference option for the interactive map.
- Satellite or map view, limited to the project vicinity.
- The captured area equals the window size.
- "Also import topography data" brings in terrain matching the image, aligned and to scale.
- Crop later from the object tree.
- In 8.1.6 the imagery and topography now match the visible map area precisely, and the elevation API was updated.

**CSV ground data**
- One point per line, `X Y Z` in metres; separators tab, semicolon, comma or space.
- Three or more distinct points → **automatic triangulation** into a ground object.
- Options:
  - auto-translation when more than 5 km from the origin;
  - **180° rotation** proposed when UTM coordinates are detected in the northern hemisphere;
  - **simplification** when over 100,000 polygons (default target 50,000).

**GeoTIFF ground data**: converted to CSV and imported the same way (faster since 8.1.6).

**User ground image** (BMP or PNG, top-down)
- Visible only in top view.
- **Ground Image Control**: pick an origin X1 and a second point X2 on the X axis, then enter their distance. PVsyst translates, rotates and rescales the image.
- Apply/edit, opacity, show/hide, crop (the original is kept).
- The file is copied into the workspace. The help says the `Shadings` folder; since 8.1.0 it goes to a user images folder (release notes).
- Images over 15,000 px are refused (8.0.5).

##### Sheds in near shadings vs "unlimited sheds"

**Two ways to model mutual row shading**
- In the **Orientation** part, as "unlimited sheds": a 2D linear calculation that ignores edge effects (see 1.1.2).
- In the **3D scene**: includes edge effects and allows partitions.
- **Never both**, or shadings are counted twice.

**3D sheds**
- Calculation effort grows with the square of the number of elements (reduced since v6).
- "Several hundreds" of rows may be unfeasible.
- When sheds are in 3D, the Orientation part must be a fixed tilted plane or multi-orientation, not unlimited sheds.

**Hybrid mode for big plants**
- Unlimited sheds in Orientation, plus a horizontal plane in 3D representing the sheds' ground footprint.
- Surrounding objects shade that plane, giving a compromise shading factor.

##### IT relevance (per function)

| Function | IT relevance | Why (analysis) |
|---|---|---|
| Elementary/building objects, hand-drawing, positioning | High | Residential and C&I roofs: chimneys, dormers, parapets, lift rooms, neighbouring buildings, trees (dense historic centres) |
| PV fields: tables, arrays, **domes**, polygonal, sun-shields | High | Pitched-roof residential (polygonal/rectangular planes), flat-roof C&I with ballasted E-W (domes) or south rows, occasional BIPV façades |
| Tracking planes / arrays of trackers | High (ground) | Utility-scale ground plants and agrivoltaic systems commonly use single-axis trackers |
| Zones with exclusion areas, conversions | High | Fast layout of ground plants and large roofs; exclusion masks for skylights and setbacks |
| Topography download / CSV / GeoTIFF / ground image | High (ground) | Hilly sites; the design must follow the terrain. Italian national/regional DTM and orthophotos would be a natural alternative source [analysis; availability not verified here] |
| DAE/3DS/PVC/PVC2/Helios import | Medium–High | Layouts often come from AutoCAD, SketchUp or PVcase. PVC2 is the open interchange route |
| Orientation management, matching checks | High | Needed for any non-trivial roof with several faces |
| Partial calculation subset, shadow-casting flags | Medium | Multi-MW scenes, speed |
| Shadow animation / sun view / video | High (communication) | Explaining shading to clients and authorities |

**Meridiana note (analysis):**
- PVsyst's 3D editor is powerful but modal and shortcut-heavy, and its help admits robustness issues: coincident points, the polygon-boolean fallback.
- Candidate approach for Meridiana:
  - ray-cast or GPU shadow-map shading on per-module or per-sub-module sample grids, which avoids fragile polygon booleans;
  - keep PVsyst's useful concepts: zones with exclusion masks, auto-grouping of orientations, an object list with multi-edit and Excel paste, a partial-calculation subset, per-object shadow casting, auto-save, a saved report view;
  - support PVCollada 2.0 import/export as the open interchange format.

#### 1.1.7 Shading calculation models

**Sources:**
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/index.html, shading-factor-table.html, iso-shading-diagram.html, treatment-of-the-beam-component.html, treatment-of-the-diffuse-component.html, treatment-of-the-albedo-component.html, diffuse-losses-with-tracking-systems.html, electrical-shading-mismatch-loss.html
- https://www.pvsyst.com/help/glossary/shadings/shading-factor.html, shading-factor-table.html, linear-shadings.html, electrical-shading-loss.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/index.html, near-shadings-procedure.html, near-shadings-tutorial.html
- https://www.pvsyst.com/help/project-design/results/simulation-variables-meteo-and-irradiations.html, simulation-variables-grid-system.html, loss-diagram.html
- https://www.pvsyst.com/help/release-notes/index.html

**Treatment of each irradiance component**

| Component | Shading treatment | Electrical loss? |
|---|---|---|
| Beam | **Shading factor** depending on the sun position: the shaded fraction of the sensitive area | Yes (1.1.8) |
| Circumsolar | Optional since v7: Preferences > Physical Models > "Use new transposition" separates circumsolar from diffuse. It then gets the **same** far and near factors as beam | **No** |
| Diffuse | Integral of the shading factor over all sky directions seen by the plane (isotropic): **constant** over the year | No (diffuse assumed uniform on the array) |
| Albedo | Integral over the ground part of the sphere seen by the plane: **constant** | No |

**Shading factor (beam)**
- Definition: the shaded fraction of the PV field's sensitive area for a given sun direction (shading-factor-table.html).
- Note: the help is inconsistent on the scale. The table page uses 0 = no shade and 1 = fully shaded; the tutorial says the opposite.
- **Geometric algorithm** (treatment-of-the-beam-component.html):
  1. Rotate coordinates so that OZ′ points to the sun.
  2. For each sensitive element (table, shed, polygon, tracker), project every surrounding elementary surface onto the element's plane, keeping only the part in front of it.
  3. Intersect the projections with the element.
  4. **Union** the elementary shadows into one shade polygon.
  5. Divide shade area by element area, and repeat for every table.
- PVsyst calls this "exact" (purely geometric). It admits that polygon unions and intersections are hard to make robust, with tolerance and topology issues, so reliability "is not absolute". The fallback is a grid of points (1.1.6).
- **Performance history**:
  - v5 scaled with N² and became prohibitive above about 500 to 1,000 elements;
  - v6 added a pre-selection of potential obstacles (×10 or more);
  - since 6.40, further gains and multi-core use;
  - **8.0.0**: tables up to 2× faster single-thread and up to 6× multi-thread;
  - 8.0.13: faster on large scenes.

**Use in the simulation**
- The shading factor is evaluated for the sun direction at the **middle of the time step**.
- **Fast mode** interpolates in the shading-factor table. **Slow mode** computes the full factor at each step; the table is then not used for beam and circumsolar ("for not too big systems").

**Shading factor table**
- Precomputed in **sun height steps of 10° and azimuth steps of 20°**, interpolated for any direction.
- One table per **orientation** and per calculation stage: linear, according to strings (including electrical mismatch), thin objects.
- For **trackers**, tables are built for several tracker positions to evaluate diffuse shading.
- Uses:
  - diffuse and albedo factors;
  - the iso-shading diagram;
  - fast-mode interpolation.
- Sun positions behind the plane are shown in blue. The highest blue entry is extrapolated from the entries above it to avoid interpolation artefacts, and the others are marked "Behind".
- The help says "Some other software use this table (exported from PVsyst)", but the export mechanism is not described [unverified]. A `.SHD` file may include the table.
- Since 8.0.21 the diffuse shading-factor tables are stored to avoid recalculation.

**Iso-shading diagram**
- A graph of the shading-factor table: lines for **1 %, 5 %, 10 %, 20 %, 40 %** loss over the sun-path diagram.
- Blue lines mark the plane's tangential limits, where the sun's rays are parallel to the plane.
- The 1 % line marks the limit of shading.
- If the threshold is exceeded at every sun height for an azimuth, the line shows 89° there.
- The lines look irregular because of interpolation.
- The help reminds that the factor applies only to the *beam* on the plane, which is small at high incidence.
- Opened from the near-shadings dialog after the table is computed. Whether it is printed in the report is [unverified] in the help text read.

**Diffuse**
- Isotropic hypothesis. Circumsolar (a cone of about 5° around the sun) is normally included in measured diffuse, unless the new transposition option separates it.
- The **"shading factor for diffuse"** is the integral of the shading factor over the sky vault the plane sees (the "orange slice" between the collector plane and the horizontal plane).
  - It uses the table for **all directions**, not only real sun positions.
  - It depends only on geometry, not on latitude, and is computed once at the start.
- The final constant "effective diffuse" factor integrates, direction by direction, **far shading × near shading × IAM**, then soiling.

**Albedo**
- Near obstacles: integral of the shading factor at zero height over the sphere portion below the horizon, between the horizontal plane and the collector plane (an analogy with the Hay model); constant over the year.
- For **sheds** only the first row sees the albedo, so the albedo factor is (n−1)/n (help wording).
- A higher albedo raises GlobInc and therefore **lowers the PR** without changing the yield.
- Far obstacles: manual fraction, plus a linear decrease to zero for horizons above 20° (1.1.5).

**Diffuse shading for trackers** (diffuse-losses-with-tracking-systems.html)
- Diffuse and albedo factors are computed for a selection of tracker angles and **interpolated** during the simulation.
- The mode is chosen *per tracker orientation* (Tools > Trackers diffuse shadings definition):
  - **All trackers**: the default since 8.0.8, most precise, can be heavy;
  - **Central tracker**: automatic choice among the central trackers, picking the one with the most shading neighbours; shown green, with an orange "mask";
  - **Custom tracker**: picked by the user.
- Option since 8.0.15: also include the shading objects in the mask (on by default).
- A badly chosen representative tracker gives an error of order **1/N rows**.
- The mode used is printed in the report under General parameters > Near Shadings.
- History:
  - before 6.08 the diffuse loss for trackers was wrong; it was zero with backtracking, against a real 2 to 3 % of yearly yield;
  - 7.3.0 added a mode window;
  - 8.0.0 removed the "Automatic" mode;
  - 8.0.7 made the factors for E-W and two-axis frames more precise (diffuse loss changes of about 2 %, yield changes under 0.1 %).

**Outputs**
- Linear shading variables:
  - `ShdLoss`: total;
  - `ShdBLss`: beam;
  - `ShdCLss`: circumsolar;
  - `ShdDLss`: diffuse;
  - `ShdALss`: albedo.
- `ShdElec`: electrical shading loss.
- Optical chain: `GlobInc → GlobHrz → GlobShd → GlobIAM → GlobSlg → GlobEff`, with factors `FShdBm = BeamShd/BeamHrz` and `FShdGl = GlobShd/GlobHrz`.
- On the loss diagram, linear shading sits in the **irradiance** part and electrical shading in the **electrical/array** part.
- A dedicated "Near shadings" loss appears in the report.

**Not modelled**
- Gains from reflections on nearby (specular) surfaces "cannot be calculated by PVsyst"; the help argues they are negligible.
- No transparency or porosity attribute for shading objects is described [not in help].

**Calculation modes: summary**

| Mode | Where | Physics | Speed / accuracy |
|---|---|---|---|
| Unlimited sheds / trackers (2D analytic) | Orientation part | Linear plus a 2D electrical effect | Fast; no edge effects (see 1.1.2) |
| Linear, fast | Near shadings | Irradiance deficit, interpolated in the table | Fastest 3D; interpolation error |
| Linear, slow | Near shadings | Full geometry each step | Accurate; slow on big scenes |
| According to module strings (fast/slow) | Near shadings + partitions | Upper bound of electrical effect × fraction | About the cost of the linear mode |
| Module Layout | Near shadings + Module Layout | Sub-module I/V curves per MPPT at each step | Most accurate; warning above 1 MWp, error above 5 MWp by default |
| Partial subset, shadow-casting flags, representative tracker, multi-thread | Options | - | Speed levers |

**IT relevance:** high.
- Every Italian rooftop with obstacles needs at least the linear mode.
- Bankable utility-scale studies with trackers need the diffuse-shading modes; "All trackers" can be heavy at multi-MW scale.
- Fast-mode interpolation (10° × 20°) is coarse for small, close obstacles typical of residential roofs; slow mode exists "for not too big systems" (help).

**Meridiana note (analysis):**
- Compute beam shading by ray casting or shadow maps per sample point.
- Offer an exact per-step mode by default for small systems and a table mode with a finer, adaptive grid for large ones.
- Compute diffuse/albedo shading with explicit sky-dome sampling (for example a Tregenza-type patch set, [analysis]), combining far shading × near shading × IAM direction by direction, as PVsyst does.
- Show iso-shading lines interactively over the sun-path chart.

#### 1.1.8 Electrical shading effect and array electrical behaviour

**Sources:**
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/index.html, electrical-shading-mismatch-loss.html, detailed-electrical-losses.html
- https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-strings/index.html, partition-in-strings-of-modules.html, electrical-loss-effect-of-thin-objects.html
- https://www.pvsyst.com/help/project-design/shadings/electrical-shadings-module-layout/index.html, mechanical-definition.html, electrical-definition.html, automatic-string-modules-attribution.html, procedures-in-the-dialog.html, shadings-3d-calculation.html, effect-of-the-by-pass-diodes.html, i-v-curves-of-one-mppt-input.html, calculation-in-the-simulation.html
- https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/near-shadings-tutorial.html (electrical-effect sections)
- https://www.pvsyst.com/help/project-design/pv-array-electrical-behaviour/index.html, arrays-with-characteristics-mismatch.html, pv-module-array-with-a-shaded-cell.html, amorphous-degradation-and-array-voltage-sizing.html
- https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/pv-module-reverse-behaviour.html, pv-module-reverse-lowvoltage.html, pvmodule-structure/submodules.html, pvmodule-structure/hot-spot-and-submodules.html, pvmodule-structure/twin-half-cut-cells-and-shadings.html
- https://www.pvsyst.com/help/project-design/orientations-in-v8/mixed-orientation-IVCurves.html
- https://www.pvsyst.com/help/tools/index.html
- https://www.pvsyst.com/help/glossary/shadings/electrical-shading-loss.html
- https://www.pvsyst.com/help/release-notes/index.html

**Principles (as PVsyst states them)**
- **Linear** shading loss is the irradiance deficit actually visible on the array. **Electrical** shading loss is the extra mismatch loss on top of it: string current is set by the weakest cell, and shaded sub-modules are bypassed.
- Electrical loss applies **only to beam**. Diffuse is assumed uniform, circumsolar causes none, and PVsyst has "no means" to evaluate diffuse inhomogeneity.
- The **sub-module** (cells behind one bypass diode, usually 20 to 24 cells, 3 per 60/72-cell module) is the basic unit.
  - A shaded sub-module has an almost identical I/V curve however many of its cells are shaded.
  - **Twin half-cut** modules count as 6 half-cell sub-modules sharing 3 diodes: when the bottom half is shaded, the top half still delivers half the current. This helps in **portrait** only; in landscape they behave like standard modules.
- Module orientation (portrait or landscape) matters mainly for the electrical loss.
- Three calculation methods:
  1. 2D analytic, for unlimited sheds and trackers (Orientation part, see 1.1.2);
  2. partitions, "according to module strings";
  3. **Module Layout**.

##### Partition model ("according to module strings")

**Inputs**
- Rectangles (**partitions**) on each table, given by count in height and width or by size. A rectangle usually spans one module height or an integer fraction of it.
- Defined on the "Partition" tab of the field dialog.
- Can be extended to selected tables, all tables of the same size, or all tables, or cancelled. The count can also be set via Ctrl+G.

**Model**
- A partition reached by shade is shown in yellow and counted as **inactive for beam**.
- Electrical loss = yellow area − grey (linear) area.
- In the current model, each partition is split into a **central stripe** (shaded → maximum loss) and two **one-cell-wide side stripes** (loss proportional to shaded area). The help's model history describes different behaviour up to 7.3.4. Loss therefore grows linearly until one cell width is shaded, then plateaus. The bottom-cell size is also used when tables are computed from the Near shadings window (8.0.13).
- **Fraction for electrical effect** (0 to 100 %) scales the electrical part:
  - about **100 %** for regular row-to-row shading ("should be left as 100%");
  - about **60 to 80 %** for irregular objects such as chimneys, far buildings and trees (order of magnitude, help);
  - or calibrated by simulating a representative sub-system (e.g. one central inverter) with Module Layout and with partitions at 100 %, then taking the ratio of their electrical losses.
- A separate fraction applies to **thin objects**.
- Fast or slow mode, as for linear shading.
- Without enough partitions, the model gives an *upper bound*.

**Partition guidelines** (8.0 study against Module Layout)

| Case | Partitions in height |
|---|---|
| 1L | 2 |
| xL | x |
| xLU | x (overestimate, preferred because the fraction can correct it) |
| xP | x |
| xPU | Module Layout recommended |
| xT | 2x |
| xTU | x |

Key: rows spanned per MPPT; L = landscape (standard or half-cut); P = portrait (standard); T = half-cut portrait; U = strings over several rows (U-cabling). Before 8.0 (up to 7.4.8) the xLU recommendation was 3x.
- String inverters or single MPPTs with identical shading, and string optimizers: about one third loss when the bottom cell row is shaded, so model with 2 partitions per module row (case 1L).
- **Module-level optimizers**: partition = one module, or 2 modules if one optimizer serves 2.
- Little tables: a string spread over several tables is fine, as long as the tables sit side by side in rows.

**Caveats**
- Large diffuse fractions move the MPP outside the studied range.
- Irregular shading → upper bound.
- Validated against Module Layout, and against real systems "in the past".
- Model history: up to 7.2.21 the electrical loss was all-or-nothing; up to 7.3.4 it used a scene-level average shade height, which underestimated irregular shading.

##### Thin objects (partition model only)
- For wires, HV lines, handrails and fences that never cover a whole cell.
- **Thin-object ratio** = shade width / cell size. Example: a 300 mm² cable is about 20 mm wide on a 156 mm cell → 0.13, i.e. a 13 % current loss for the whole string, however many cells are touched.
- **Distance effect** from the sun's 0.53° apparent diameter: shade width W = D·sin(0.53°) + S. A cable 30 m above the array casts a trail about 30 cm wide.
- **Thin Objects Analyze tool** (3D editor > Tools):
  - inputs: object width, cell size, distance;
  - shows the trail and the per-cell shading as the sun moves;
  - the maximum per-cell value (e.g. 8.6 %) is used as that object's fraction for electrical effect.
- Effects of several wires are **not additive**.
- Not available in Module Layout.

##### Module Layout (detailed electrical shading)

**Prerequisites**
- A complete 3D scene and the System sub-arrays (modules and inverters). It is usually the last step of a study.

**Mechanical tab**
- 2D view of all tables of one orientation, with automatic row/column numbering and a compass.
- Places the System's modules on the tables, for the full system, the current orientation or a selection, with spacing, filling mode and **portrait/landscape**.
- Add a row or column (applies to the whole array); remove modules by right-click.
- "Match this table" / "Match all tables" resize the 3D tables to the modules; polygonal fields are for BIPV.

**Electrical tab**
- Assigns each module to a **string** of a given inverter/MPPT input. Colours follow the electronic colour code (1 brown … 0 dark grey).
- Manual assignment by click or drag; right-click un-assigns; drag mode moves or swaps assignments.
- **Auto attribution** strategies:
  - big tables: all of a string's modules on one row, on 2 rows ("U"), or on 3 to 5 rows; "remaining not attributed"; horizontal or vertical filling; any origin corner; left-to-right or back-and-forth;
  - little tables: a string spread over 1 to 5 tables, along a line or a column, from a chosen corner, left-to-right or back-and-forth;
  - **"Same row per MPPT"**, optimal with string inverters (2 to 3 strings per MPPT);
  - can be applied to selected tables or inverters, with manual fixes afterwards.
- With mixed orientations in a sub-array, only the strings of the chosen orientation are enabled. Since 8.0.10, I/V curves can also be shown for mixed-orientation MPPTs after the shading animation.

**Teaching tabs** (not needed for the simulation)
- **Shadings 3D**: clear-sky animation per inverter on any day, scrollable by quarter hour. Right-clicking a module shows its sub-module I/V composition.
- **I/V curves**: the full MPPT-input composition, clear sky only, not for simulated time steps.

**Other**
- A blue information panel says what to do next.
- Prints and BMP export; optional inclusion in the report, "as a reference wiring schema on site".

**Model at each time step, per MPPT input** (calculation-in-the-simulation.html, detailed-electrical-losses.html)
1. The 3D shade polygon on each table is applied to each **sub-module**, testing its 4 **corners**:
   - linear factor = shaded corners / 4;
   - one of 4 typical sub-module I/V curves (10 % of cells shaded for 1 corner, 1/3 for 2, 2/3 for 3, 100 % for 4).
2. Sub-module curves are added **in voltage** to form each string, and strings **in current** to form the MPPT input.
3. The inverter picks the global MPP. If V_MPP is below the MPPT minimum, PVsyst takes the better of the secondary (diffuse) MPP and the power at VmppMin.
4. `P_Elec = Pmpp(unshaded) − P_shaded − P_Linear`. The beam electrical factor is `P_Elec / (Pmpp · FracBeam)`, with `FracBeam = Beam/Global` and global including diffuse shading.
5. Diffuse and albedo get constant, homogeneous shading factors and keep the shaded strings at a minimum current.

**Further model details**
- Reverse cell characteristics are used. For IBC modules with very low reverse voltage, `Irev = Isc + Arev·Vrev²`, with `Arev` in the PAN "Secondary parameters"; a dedicated tool was added in 8.0.6.
- Twin half-cut modules have been fully supported since v7; curves are accumulated per module.
- Optimizers are handled: MPP choice under partial shading updated in 8.0.12; several modules in parallel fixed in 8.0.0.

**Advanced parameters (defaults)**

| Parameter | Default |
|---|---|
| Minimum shade area to count as shaded | 0.024 m² |
| Minimum shading fraction for electrical calculation | 1 % (below → P_Elec = 0) |
| Maximum shading fraction | 98 % (above → fully shaded, P_Elec = 0) |
| Fraction of bottom cell for no shading | 50 % (step at half a cell width) |
| Size tolerance between Module Layout and 3D tables | 2 % |
| **Warning** above | 1,000 kW |
| **Error (forbidden)** above | 5,000 kW (adjustable) |

**Limitations**
- **Crystalline only**: thin-film strip cells cannot be represented.
- **Thin, long shadows** (e.g. poles) are underestimated, so use partitions for them.
- Not compatible with the partial-calculation subset.
- For large plants: simulate a representative sub-system with Module Layout, derive the fraction, then run partitions on the whole plant.

##### What bypass diodes really do (didactic page)
- With **one string per MPPT** (or all strings shaded identically), loss is about the share of shaded sub-modules plus the diode drop. A V_MPP below the inverter minimum can wipe out that advantage, so a wide MPPT window matters.
- With **3 strings in parallel**, shading 1/3 of one string's sub-modules (the bottom row in landscape) already costs about **85 %** of that string in clear sky with 15 % diffuse: its *entire beam contribution* is lost, because the unshaded strings set the voltage.
- Recommendations:
  - put all modules of a string, and ideally of an MPPT, on the **same row**;
  - standard modules in **landscape**, twin half-cut modules in **portrait**.
- Tool: Tools > Electrical behaviour of PV arrays > Array with shaded cells > By-pass diode effect.

##### Recovery by optimizers (calculation-and-model/index.html)
- Module-level or, better, sub-module-level optimizers recover part of the mismatch, but not all of it:
  - a bypassed sub-module loses its remaining illuminated and diffuse production;
  - the diode drop (≲ 1 V × string current) is dissipated as heat.
- String-level optimizers help with mismatch between parallel strings in regular rows.
- Optimizer loss variables: `OP_Oper`, `OP_Pmin`, `OP_Pmax`, `OP_Vmin`, `OP_Vmax` (results page).

##### "PV array electrical behaviour" tools (Tools > Electrical behaviour of PV arrays)

| Tool | What it does | Inputs / model |
|---|---|---|
| Reverse characteristics | Shows a cell, a module without diode, and a module with bypass diode(s) under reverse bias. The diode limits reverse voltage to about −0.7 V per diode | Reverse cell coefficient `brev` (default usable); hot-spot explanation |
| **Arrays with characteristics mismatch** | Random dispersion of Isc and/or Voc (Gaussian or uniform between limits) over cells in a module, modules in an array (with bypass diodes), or **sorted** modules | Builds each I/V curve with the standard model and adds them point by point. Shows the mean curve and envelopes (2-RMS or extreme values), and the power loss at MPP and at fixed voltage. Results differ on every run (random) |
| **Module/array with a shaded cell** | Voltages, currents and power dissipated in one shaded or bad cell; resulting temperature (**hot spot**), with and without bypass diode | Irradiance, normal module temperature, shaded fraction of the cell |
| **Heterogeneous / mixed orientation arrays** | Two sub-arrays in parallel (different orientation, module type or count) over a clear day, with adjustable amplitude and diffuse share; module temperature follows irradiance | Shows near-additive behaviour for similar voltages, two maxima and large loss for different voltages, and why blocking diodes matter (orientations-in-v8/mixed-orientation-IVCurves.html) |
| Module mismatch evaluation | Estimates the constant mismatch loss from module dispersion (under 0.5 % for dispersions below 2 %) | See the array and system losses section (https://www.pvsyst.com/help/project-design/array-and-system-losses/array-mismatch-losses/index.html) |

- Note: the electrical-behaviour index says the reverse cell model is used "only" in these didactic tools, but the IBC page states that Module Layout uses the reverse characteristics. This is an inconsistency in the help.

**Amorphous degradation and voltage sizing**
- The simulation uses **stabilised** STC values.
- The initial Staebler–Wronski over-voltage (about +10 %) should be considered when sizing.
- Options: raise the low reference temperature for summer commissioning (e.g. +10 °C instead of −10 °C gives about −6 % Voc at −0.3 %/°C), or remove one module per string during the first months.

**Outputs**
- `ShdElec` in the hourly and monthly results.
- A separate electrical-shading step on the loss diagram, distinct from the linear one.
- Module Layout prints.
- 8.0.16: the "electrical shadings effect" line is no longer printed for backtracking with unlimited horizontal-axis trackers (release notes).

##### IT relevance (per function)

| Function | IT relevance | Why (analysis) |
|---|---|---|
| Module Layout + auto attribution | High (≤ ~1–5 MW) | Residential and C&I roofs with chimneys and parapets; mixed string inverters; the PVsyst default ceiling (5 MWp) covers most rooftop C&I |
| Partition model + fraction | High (ground) | Utility-scale rows and trackers; calibrated on a Module Layout sub-system |
| Bypass/portrait-landscape guidance, "same row per MPPT" | High | Common design choice for E-W domes and south rows on flat roofs |
| Optimizer handling | High (residential) | MLPE is widespread in residential systems [analysis] |
| Thin objects | Medium | Overhead lines, fences, railings; agrivoltaic structures with cables [analysis] |
| Didactic I/V tools | Medium | Training, explaining choices to clients |
| Amorphous sizing note | Low | Thin-film a-Si is rare today |

**Meridiana note (analysis):**
- Make the sub-module-level I/V composition, which PVsyst only uses in Module Layout up to 5 MWp, the *default* path, vectorised per MPPT input. The pvlib `bishop88` functions with a reverse-bias breakdown model can supply sub-module curves; see section 3 for the mapping.
- Expose the shade-on-module view as live feedback during stringing, the way Aurora shows string validity live.
- Keep a calibrated fast "partition" mode for very large plants.

#### 1.1.9 Grid-connected system definition

##### 1.1.9.1 Workflow: project, variants, status lights (project design tutorial)
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/project-design-tutorial.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/index.html

- **Objects.** A *project* (.PRJ: site, weather file, albedo, project settings) holds *variants* (.VC0, .VC1, ... "calculation version") with system definition and results. "Save As" creates a new variant; "Load" reopens one.
- **Recommended method.** (1) Define the project. (2) Build a first variant with the minimum inputs and PVsyst defaults, simulate, save. (3) Add one perturbation per variant (horizon, near shadings, detailed losses...), re-simulate and read the loss diagram each time.
- **Status buttons ("LED").** Red: missing or unacceptable parameters (simulation disabled). Orange: acceptable but not ideal. Green: defined and correct. Green-off: topic not used. "The Simulation will be enabled only when no button is red."
- **Variant steps in the tutorial.** Orientation (with "Show optimization" against the transposition-factor optimum; the optimum differs for grid vs stand-alone/pumping) → System (presizing help: desired power *or* available area; module list with "All modules"/"Favorites", sorting by manufacturer; inverter choice; "Show sizing") → Simulation (variant description) → Results → Report.
- **Report in the tutorial.** Described as 3 pages (parameters; main results with normalised graphs and monthly table; arrow loss diagram). This tutorial text is older than the 8.1 report, which has more pages (see 1.1.15).
- **Horizon in the tutorial.** Hand-drawn (drag points; right-click adds/deletes), Solmetric SunEye import (ObstructionElevation.csv), Carnaval (rename *.masque.txt*), Horiz'ON photo panoramas (details in 1.1.5).
- **Near shadings in the tutorial.** Simulate with "linear" shading (lower bound), then "according to module strings" (upper bound of the electrical effect); for the final report the tutorial suggests an intermediate electrical fraction, admitting no established value ("60 to 80% ???"). Near and far shadings do not cumulate on the beam component.
- **System vs 3D scene.** PVsyst checks only identical orientations and a sufficient sensitive area in the 3D scene; it "does not check the real physical (geometrical) compatibility" between the system definition and the module arrangement (tutorial text; the Module Layout tool in 1.1.8 adds explicit module positioning).
- **Detailed losses button** (thermal, wiring, module quality, mismatch, soiling, IAM): see 1.1.13.
- **IT relevance:** high. This is the daily workflow for every study, from a 3 kW roof to a utility plant.
- **Meridiana note (analysis):** replace the LED buttons with a live validation list (error/warning/info with "fix" links) and add a variant-to-variant diff view.

##### 1.1.9.2 Sub-arrays
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/sub-arrays.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/index.html

- **What it is.** The "system" is a list of sub-arrays (unlimited; add, copy, rename, move, delete). One sub-array = one PV module model + one inverter model + number of inverter inputs (whole inverters or MPPT inputs) + modules in series + number of strings + optional optimizer + one orientation (or a "mixed orientation" with 2 orientations on the same input).
- **Inputs for automatic proposal.** Desired nominal power *or* available area; module; inverter; optional optimizer. PVsyst chooses the number of inverters for a default PNomRatio of 1.25, then proposes modules in series and strings; checkboxes restore the automatic values after manual edits.
- **Homogeneity rule.** All strings on an inverter or MPPT input are identical (module, number in series, orientation). Mixing module models (e.g. power classes) on one input "is not possible in PVsyst in the present time".
- **Uneven strings per MPPT.** Accepted and distributed in the most balanced way (example: 10 strings on 3 MPPT → 3+3+4); warning when the imbalance is excessive (e.g. 2 vs 3 strings).
- **Simulation.** Each sub-array is simulated independently, but "only the energy and loss totals are available as outputs"; to study one sub-array you simulate it alone.
- **IT relevance:** high. Typical Italian roofs have 2-4 faces (one sub-array per face/MPPT); C&I and ground plants use many identical sub-arrays.
- **Meridiana note (analysis):** keep the sub-array concept but output per-sub-array and per-MPPT energies and losses (a PVsyst gap).

##### 1.1.9.3 String (voltage) sizing and design temperatures
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/array-voltage-sizing-according-to-inverter.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/design-temperatures.html , https://www.pvsyst.com/help/project-design/project-definition/project-settings.html , https://www.pvsyst.com/help/release-notes/index.html (8.1.5)

| Check | Temperature used (default) | Nature in PVsyst |
|---|---|---|
| Vmpp(TOperMax) ≥ inverter VmppMin | cell 60 °C | "fuzzy": if violated, operating voltage is clipped → IL_Vmin loss |
| Vmpp(TOperMin) ≤ inverter VmppMax | cell 20 °C | "fuzzy": → IL_Vmax loss |
| Voc(TMin) ≤ inverter VAbsMax | ambient −10 °C | mandatory (safety); main constraint on string length |
| Voc(TMin) ≤ module maximum system voltage | ambient −10 °C | mandatory (1000 V IEC / 600 V UL or 1500 V) |

- TOper (default 50 °C) is an intermediate value used in some displays/report.
- **TMin guidance.** Lowest temperature ever observed on site (IEC 62548-1, as cited by PVsyst), optionally with irradiance > 10 W/m²; *ambient*, not cell temperature, because the cold array can see sun while the inverter is still off (Voc). For ground-mounted systems the long-term average of the yearly minimum may be used (IEC TS 62738:2018 §7.2.1, as cited).
- **Updates.** Since 8.1.5, TMin is computed during TMY generation (minimum temperature with G > 10 W/m² over all source files); 8.1.5 also displays the MET-file minimum with a warning when it is below the project TMin.
- **Other design parameters (Project settings → Design conditions).** Array max voltage; option to use the manufacturer's muVoc instead of the one-diode Voc(T); "Limit overload loss for design" (see 1.1.9.4). Defaults for new projects in Hidden parameters → "System design parameters". These temperatures are used at design time only, never in the simulation.
- **Thin film.** Voltages are stabilised values; initial values may be 10-15 % higher during the first months (check VAbsMax and insulation).
- **Tool.** "Show sizing" graph: upper part = voltage conditions; lower part = power histogram (1.1.9.4).
- **IT relevance:** high. The TMin choice for Italian sites (Alpine and Apennine altitudes vs coast) directly sets the maximum string length.
- **Meridiana note (analysis):** fetch TMin automatically from the weather file / long-term series and show the margin to VAbsMax as a live gauge.

##### 1.1.9.4 Inverter power sizing: DC:AC ratio and overload
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/inverter-array-sizing.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/pnom-ratio-dc-ac.html , https://www.pvsyst.com/help/project-design/project-definition/project-settings.html , https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-output-parameters.html , https://www.pvsyst.com/help/release-notes/index.html (8.0.13)

- **Definition.** PNom ratio = PNom array at STC [kWp] / inverter PNom [kWac] (the "DC:AC ratio"). The PMax "bonus" of the inverter is not included.
- **Method.** Sizing by acceptable *overload (clipping) loss* over the year, estimated from a power-distribution histogram of a rough pre-simulation (green: potential array energy EArrPmpp; violet: energy limited at the inverter Pnom; loss = area between them).
- **Thresholds: inconsistent in the help.** The sizing page says 0.2-3 % = "slightly undersized" (orange) and > 3 % = "strongly undersized", which "prevents the simulation". Release notes 8.0.13: warnings now trigger at **2 % and 4 %** and "are not fatal anymore"; Project settings: "Limit overload loss for design" fixed at **max. 4 % by default**, user-adjustable for highly oversized arrays.
- **Typical outcome.** PNom ratio about 1.25-1.3 for well-oriented systems, > 2 for façades; higher if the inverter can reach PMax at low temperature.
- **Limits of the pre-evaluation.** It ignores PMax (inverter temperature unknown) and not all system losses, so it usually overestimates overload; "the reference result is, of course, the detailed simulation". Since 8.0.13 the overload estimate accounts for a power factor set in Energy management ("Overload loss, with PF").
- **Physics stated by PVsyst.** Modern inverters limit power by moving the operating point toward higher voltage; no excess power is dissipated, hence "no additional aging". Effective Pnom changes in operation: × PMax/Pnom with favourable temperature; × cos φ if Pnom is in kVA and a power factor is imposed.
- **IT relevance:** high (DC:AC choice for residential hybrids and C&I string inverters; export-limited connections, see 1.1.9.9).
- **Meridiana note (analysis):** show the clipping histogram and the expected clipping loss live while the user edits strings.

##### 1.1.9.5 Multi-MPPT inverters, power sharing, string inverters, unbalanced inputs
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/multi-mppt-inverters/index.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/multi-mppt-inverters/multi-mppt-more-examples.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/multi-mppt-inverters/power-sharing.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/multi-mppt-inverters/string-inverters-current-limiting.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-model-multi-mppt.html

- **Two inverter kinds.** "Normal" multi-MPPT (identical inputs) and "unbalanced" (two inputs of very different rating, main + secondary, e.g. SMA Tripower series).
- **Two definition modes (normal kind).** "Pnom sharing within the inverter" (you give the number of whole inverters; all MPPTs assumed used) or "Independent MPPT inputs" (you give the number of MPPTs; mandatory when one physical inverter has MPPTs in different sub-arrays, e.g. different string lengths). The number of physical inverters is derived and shown in the sub-array list.
- **Default model.** An inverter with N MPPT = N identical inverters of Pnom/N (manual per-input Pnom possible since 6.33). Unused MPPT inputs reduce the available power (a 10 kW, 2-MPPT inverter with one input used gives 5 kW in "independent" mode).
- **Power sharing window.** Sub-arrays with the *same inverter model* are grouped into "Inverter config." groups by drag-and-drop; "Auto-equal. Pnom" balances Pnom ratios, or shares are set manually; a needle-gauge button equalises more finely; eraser/trash/up-down buttons; since 7.2.15 no cap on the number of sub-arrays. A hidden parameter caps the sharing ratio. Worked example: 42 % / 29 % / 29 % for inputs with 3/2/2 strings.
- **Consistency checks (error messages).** Sharing between different inverter types; total MPPT inputs not a multiple of the inverter's MPPT count (all inputs must be used when sharing); MPPT count of a sub-array not a multiple of the number of inverters (ambiguous configuration; split into several configurations); sum of shares > 100 % or < 100 %. Identical sub-arrays are still treated as different.
- **Two orientations on one inverter ("domes", east-west).** "Daily sharing": at each time step the Pnom of each MPPT is re-allocated according to the incident energy of each orientation.
- **Mixed-orientation sub-array with several inverters.** Radio buttons choose the string distribution: minimise mismatch (one orientation per input set) or mix orientations on every input (dome-like); sharing then concerns whole inverters.
- **String inverters (8-12+ MPPT, ~10-15 A per input).** Recommended: *uncheck* "Use Multi-MPPT feature" so only the total inverter power is limited while the per-input current limit (from the OND "Input side", e.g. IMax_InMPPT / Vmpp_PMin) still applies. Worked example (120 kW, 10 MPPT, 15 A): overload often appears as power overload rather than current-limit loss.
- **Not enforced / not modelled.** Manufacturer limits on voltage/power difference between MPPTs (user must check); inverter derating caused by MPPT imbalance; per-MPPT maximum power is not in the database ("your responsibility").
- **Unbalanced inputs.** Design time: Pnom split by the maximum current of each input; simulation: Pnom re-assigned according to the PV power actually connected. "Adjust" can skip the secondary input. Tutorial: 155 × 250 Wp on 2 × 15 kW inverters (6×20 on main inputs, 18 and 17 modules on secondaries; requires raising the design overload limit).
- **IT relevance:** high. Residential and C&I string inverters with 2-12 MPPT and east-west or multi-face roofs are the Italian norm.
- **Meridiana note (analysis):** derive power-sharing groups automatically from the string-to-MPPT map drawn on the 3D/2D layout and check them against datasheet per-MPPT limits.

##### 1.1.9.6 Master/slave operation
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/master-slave-operation.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-model-multi-mppt.html

- Input: number of slaves NSlaves (0 = not used). One master tracks the MPP of the whole (paralleled) array and runs alone until the power exceeds a threshold (typically its own Pnom); gain 1-2 % at most, less with modern inverters; few inverters support it. Wiring: inputs in parallel only in M/S mode (otherwise never parallel MPPT inputs). "Internal Master/Slave" flag of large central inverters is informative only (simulated as one inverter).
- **IT relevance:** low (legacy/central inverters).

##### 1.1.9.7 Normalised grid voltages
Source: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/normalised-grid-voltages.html

- Informative page: Vpp = √3·Vpn; Europe Vpn = 230 V (+6 %/−10 % as stated by PVsyst), Vpp = 400 V; US variants listed with question marks ("we don't have precise information" for other regions). The inverter's AC nominal voltage is used for AC wiring loss currents (1.10.4).
- **IT relevance:** medium (230/400 V LV; MV handled through transformers, 1.1.13).

##### 1.1.9.8 Power factor and reactive energy
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-factor/index.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-factor/Impact-on-overload-conditions.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-factor/Setting%20up%20the%20simulation.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-factor/Simulation%20results.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-factor/lagging-and-leading.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-factor/night-reactive-energy-production.html , https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-output-parameters.html

- **Input.** Energy management → Power Factor tab: a single requested PF for the whole system, **yearly or monthly** values. Finer time resolution, constant-Q and **Q = f(U)** control are "considered for future versions" (not available).
- **Inverter capability.** From the OND "Output parameters": PF limits (cos φ or tan φ, lagging and leading) and whether Pnom is in kW (active) or kVA (apparent). If the request exceeds the capability, an information message is shown and the inverter uses its limit PF.
- **Effect on overload.** Pnom in kW → no effect on active energy. Pnom in kVA → Pnom(act) = Pnom(app)·cos φ, so clipping increases (the system dialog shows "Overload loss, with PF"). Since 7.3.3 each inverter uses its own OND definition; the "Force as apparent/active power" options remain for compatibility/testing only ("not recommended").
- **Outputs.** EReGrid = EOutInv·tan φ (computed at the inverter); EApGrid² = E_Grid² + EReGrid²; both shown at the bottom of the loss diagram and in advanced results, with an effective yearly cos φ at the injection point. Variable names: EApGrid [kVAh], EReGrid [kVArh], E_Grid [kWh].
- **Stated simplifications.** No reactive-energy change between inverter and injection point (no impedance/transformer reactive modelling); only active AC ohmic losses reduce P, so the PF at injection is slightly lower than at the inverter. Self-consumption takes only active power (PF at injection rises); batteries exchange only active power. Grid limitation clips active power before the inverter output, and Q follows the clipped P. Limits depending on grid voltage cannot be simulated (grid voltage unknown). Night-time reactive power (STATCOM-like) is out of scope.
- **Sign convention.** φ > 0 lagging (inductive; plant "produces" reactive energy); φ < 0 leading (capacitive; plant "consumes" reactive energy; loss diagram label "Reactive energy absorbed from the grid").
- **IT relevance:** medium-high for MV/large plants where the DSO imposes a power factor or Q(V) behaviour (Italian connection rules CEI 0-16 / CEI 0-21 include reactive-power requirements [to verify the exact requirements in the standards]); PVsyst only covers fixed yearly/monthly cos φ.
- **Meridiana note (analysis):** support cos φ(P) and Q(U) curves at least as an energy-budget approximation, and transformer reactive losses.

##### 1.1.9.9 Grid power limitation (export limit at the injection point)
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-power-limitation.html , https://www.pvsyst.com/help/release-notes/index.html (7.3, 8.0.10, 8.1.0)

- **Principle stated by PVsyst.** Excess power cannot be dissipated at the injection point; limitation is always realised by the inverter shifting the array operating point (clipping).
- **Inputs (Energy management button).** On/off; limit value as **active power [kW]** or **apparent power [kVA]** (then with a dedicated cos φ, yearly or monthly); limit applied **at inverter level** (inverter capped at the limit, injected power further reduced by auxiliaries, AC wiring, transformer) or **at injection point level** (grid receives exactly the limit; inverters deliver more to cover downstream losses); constant value or **time series from CSV** (8.1.0); option "Account as separate loss".
- **Algorithm (since 7.3).** At the start of each time step PVsyst pre-evaluates an effective Pnom for every MPPT, considering temperature and PF, predefined power sharing, N vs N+1 strings per input, simultaneous self-consumption or battery charging (added to the limit), orientation sharing on one inverter, kW vs kVA. If ΣPnom exceeds the limit, Pnom values are reduced **starting from the most loaded MPPTs (highest DC:AC)**; the simulation then runs normally and the excess is booked as "Inverter loss over nominal power".
- **Outputs.** With "Account as separate loss", the part due to the grid limit is reported separately as **EGrdLim** (help text also mentions **EUnused**); EOutInv then means "power that could be achieved if no grid limitation was present" (not the physically measured value). 8.0.10: the limitation at inverter level is no longer affected by auxiliary losses.
- **With storage (table in the help).** Limit at inverter level: with AC-coupled BESS the limitation happens before the battery; "separate losses" is disabled. Limit at injection: the per-MPPT pre-evaluation adds the battery charging power (power shifting: strategy power for that step; other strategies: max charging power); if the battery is fuller than forecast, excess → EUnused; EGrdLim becomes much smaller.
- **IT relevance:** high. Export limits (requested injection power lower than PV/inverter power, zero or reduced export behind the meter, utility plants with limited connection capacity) are common design constraints.
- **Meridiana note (analysis):** explain the split clipping/grid-limit loss graphically; allow a limit time series aligned with tariff or DSO curtailment periods.

##### 1.1.9.10 Single line diagram
Source: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/single-line-diagram.html

- **Status.** Introduced in 7.3.0, "still work in progress"; may fail on complex systems (error message). Grid-connected only (stand-alone and pumping "will follow"). Contains PV strings, MPPT nodes, inverters, combiner boxes (DC side only; 1-2 levels when DC cables come from the ohmic "Detailed computation"), MV transformers (groupable) and one HV transformer, cables, one injection point (top node). **Storage is not included.**
- **Inputs.** Generated automatically from the System dialog and the Detailed losses → Ohmic losses dialog (live update while either is open).
- **Editor tab.** Tree on the left (columns: sub-array, module/inverter type) and properties of the selected node's *outgoing* cable on the right; cables blue (DC) / red (AC), bold when defined in Detailed losses; shown as resistance or as length/cross-section/material. Operations: group, ungroup, "custom group" (N groups or N elements per group; e.g. 192 strings → 3×38 + 2×39). Automatic grouping of identical nodes (children included). **No undo.** Grouping may collapse back when string numbers change.
- **Viewer tab.** Paper A1-A4, US Letter/Legal, portrait/landscape; labels and legend toggles; zoom (wheel, slider); "Center on injection point"; 3 inverter symbols and 3 injection-point symbols; print preview with client logo; output to printer, PDF or clipboard; optional page in the PVsyst report (Report options → Final report option).
- **IT relevance:** medium. Useful as a report annex; not a substitute for the CEI-compliant single-line diagram of the executive design (no protections, no switchgear) [analysis].
- **Meridiana note (analysis):** generate the SLD from the same electrical model including protections, storage and MV/LV equipment, with export to DXF/SVG.

##### 1.1.9.11 Consistency checks and warnings (summary across the system definition)
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/index.html , https://www.pvsyst.com/help/project-design/project-definition/project-settings.html , pages cited in 1.1.9.2-1.1.9.10 and 1.1.10

- Checked: voltage windows and absolute voltages (1.1.9.3); overload thresholds (1.1.9.4); string imbalance across MPPT; power-sharing feasibility (1.1.9.5); optimizer/inverter/module compatibility (green/orange/red lists, hard-coded Huawei/SolarEdge/Sungrow rules, 1.1.10); PF request vs inverter capability; MET minimum temperature vs TMin (8.1.5); 3D scene vs system (same orientations within a tolerance, area ratio; Project settings → Other limitations); battery charge/discharge rates (1.10.5).
- Colour code: red = error (blocks the simulation), orange = advisory; shown in the warning panel and on the System LED.
- Explicitly *not* checked: real geometric placement (tutorial), MPPT voltage/power-difference rules, Huawei VAbsMax vs VStrMax margin (1.1.10), contractual ISC/array-power limits are only "may be contractual" (1.10.4).

#### 1.1.10 Power optimizers

Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/index.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/management-of-power-optimizers.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/optimizer-buck-boost-modes.html , brand pages cited in the table, https://www.pvsyst.com/help/project-design/results/simulation-variables-grid-system.html , https://www.pvsyst.com/help/release-notes/index.html

- **What PVsyst models.** Module-level (or sub-module-level) DC-DC converters with the constraint that all outputs in a string carry the same current; the output I/V curve extends the voltage range at which each module delivers its Pmpp.
- **Two operating modes.** *Buck-only*: below the module Vmpp the output follows the hyperbola I = Pmpp/U up to a maximum current; above Vmpp it follows the module I/V curve. *Buck-boost*: hyperbola on both sides of Vmpp (wider voltage range; useful with fixed-voltage inverters or few optimizers).
- **Stated benefits/limits.** Recovers mismatch (tolerances, uneven soiling, differential ageing) and partial-shading effects; ~1 % unavoidable conversion loss; local heating of nearby cells; module-level monitoring and shutdown (emergency responders); sometimes longer strings (voltage cap). With several strings in parallel, optimizers "cannot recover much" from partial shading of one string. Different orientations within one string are "not currently allowed".
- **Management.** No general user database: a closed list of devices defined by the manufacturers, not modifiable, users cannot add devices. Activated by "Uses Optimizers" in the System dialog; suitable devices are shown in green. The optimizer dialog has pages: Main parameters, Input modules (limits; sometimes several modules per optimizer), **Output I/V behaviour** (pedagogic I/V and P/V curves with adjustable shaded sub-modules; example of 4 optimizers in series), Efficiency profile (may depend on the "optimizing ratio"), Sizes.
- **Simulation variables.** OP_Oper (efficiency), OP_Pmin, OP_Pmax, OP_Vmin, OP_Vmax. Since 8.0.15 optimizer efficiency is applied after module-related losses and power clipping is handled better; electrical shading benefits require the **Module Layout** model (1.1.8); the "according to module strings" shading mode under-evaluates (SolarEdge page).

| Device family (help page) | Topology / mode | PVsyst-specific rules and handling |
|---|---|---|
| SolarEdge: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/solaredge-architecture.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/solaredge-system-design-procedure.html | 1-4 modules per optimizer; buck-boost; inverter input at **fixed voltage** (usually 350 V or 700 V), so strings act independently | Optimizer params POptMax (clear-sky power, not STC), VOptOutMax (e.g. 60 V), VOptOutMin (e.g. 5 V), IOptOutMax; inverter PmaxAC, PMaxDC, VinvNom, IDCMax. Only allowed pairs; min/max optimizers per string; max power per string; max PNom ratio per inverter (usually 1.35; 1.55 for HD-Wave). Each string type = one sub-array; "String configuration" builds the list of *physical* inverters and attributes strings (editable; "Adjust sub-arrays"; max strings per input and max PNom ratio for auto-build). Efficiency depends on the current boost ratio (best near 1). **Heterogeneous strings** (2-module and 1-module optimizers in one string) since 8.0.15. No mismatch loss with one module per optimizer. |
| Huawei: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/huawei-optimizer.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/huawei-system-procedure.html | Module-level buck-only; SUN2000-450W/600W-P2 (1 module), MERC 1100/1300 W (2 modules in series); inverter controls optimizers via DC line | Manufacturer rules **hard-coded since 7.4.4** (cannot be overridden): compatible inverter list (SUN2000, SUN5000); 1-2 strings per MPPT (more than 2 for compatible pairs since 8.1.5); min/max optimizers per string; max power per string; **max 2000 W difference between MPPTs**; min/max PNom ratio per number of MPPT used; **VStrMax** (optimizers boost to cap string Voc; strings up to 25 MERC optimizers). SUN5000 150 kW only with MERC optimizers; the help gives both "9 to 12" and "at least 8 ... up to 12" strings on 7 MPPT (inconsistent). PVsyst does **not** check the VAbsMax vs VStrMax low-temperature margin (example: +12.2 % needed). "String configuration" dialog for physical inverters. Not supported: modules without optimizers in an optimized string; mixed orientations in a string. |
| Sungrow: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/sungrow-optimizer.html | Module-level buck-only; SG/SH inverter series; inverter-controlled; module-level I/V scanning | Compatibility (inverters, min/max optimizers, max power per string) hard-coded and checked in the System dialog; same two limitations as Huawei. |
| Tigo TS4: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/tigo-optimizer.html | Buck-only; Cloud Connect Advanced + Access Points (≤ 700 optimizers per TAP) | Some devices cap voltage just above Vmpp (avoids low-temperature Voc limit → longer strings); otherwise normal string sizing. |
| Maxim Integrated: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/maxim-optimizer.html | **Sub-module** DC-DC (20-24 cells) replacing the bypass diode; buck-only; specific modules in the database | Mismatch loss should be set to zero; STC power already includes the optimizer inefficiency (no base loss in simulation); shading benefit only with Module Layout. |
| AMPT: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/ampt-optimizer.html | Module-level buck-boost; also "Dual String" current-boost string optimizers | Checks: sum of optimizer max voltages ≤ VAbsMax and ≤ 1000 V (IEC)/600 V (UL); 0.85 × max voltage ≥ VmppMin. String-level devices give no intra-string mismatch benefit. |
| AdvanSol: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/advansol-optimizer.html | Buck-only ("current boosting") | Variants -O (MPPT), -RO (+ rapid shutdown), -MRO (+ monitoring); normal string sizing. |
| AndSolar: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/andsolar-optimizer.html | Buck-only | Rated 1500 V; normal string sizing. |
| Sungo: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/sungo-optimizer.html | Buck-only | Normal string sizing. |
| Buck-only (generic concept page): https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/buckonly-optimizer.html | Buck-only | Module compatibility check (V, I, P); normal string sizing. |
| Generic, Generic Dual: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/power-optimizers/generic-optimizer.html | Buck-boost with V and I limits | No restriction on compatible inverters/cells; Dual = higher input current and power. |

- **Release-note items (8.x).** 8.0.0: new AdvanSol, Sungo and Generic optimizers, Huawei SUN5000 inverters. 8.0.15: SolarEdge heterogeneous strings; efficiency after module losses; better clipping. 8.0.16: AndSolar optimizers. 8.0.13: optimizers included in installation costs. 8.1.0: new Huawei optimizers; optimizer-level current clipping improved. 8.1.5: > 2 strings per MPPT for compatible Huawei pairs.
- **IT relevance:** high for residential and small C&I rooftops with partial shading (chimneys, dormers, multiple faces), where module-level electronics are widely used [analysis].
- **Meridiana note (analysis):** a generic, parameterised optimizer model (buck-only / buck-boost / fixed-voltage) with an open device library is better than PVsyst's closed list; vendor rule sets can be data files.

#### 1.1.11 User's needs (load) definition

| Mode | Description | Typical use |
|---|---|---|
| Unlimited load | Default for grid systems: the grid absorbs everything. | Grid |
| Fixed constant load | Constant power or yearly energy. | Grid, DC-grid |
| Monthly values | Constant within each month, set with a graphic tool. | Any |
| Daily profiles (hourly) | Constant over the year; **seasonal** (4 profiles: Jun-Aug, Sep-Nov, Dec-Feb, Mar-May); **monthly normalisation**; **weekly modulation** (working day and weekend, user-set working days). | Self-consumption |
| Probability profiles | 12 power classes with an hourly probability distribution. Constant, seasonal or weekly. | DC-grid (public transport) |
| Domestic appliances | Number, unit power and daily hours per appliance; standby. Year, seasonal or monthly modulation, plus weekend options. Three templates: basic SHS, enhanced SHS (about 2 kWh/day), household (12 kWh/day). | Stand-alone default |
| **CSV/ASCII load file** | Hourly or sub-hourly, e.g. 15 min. Converted to hourly on import: power is averaged, energy summed. Shows average, maximum and yearly total, with **rescaling** to a target yearly energy. | Self-consumption with metered data |

**Templates and storage**
- `LOADPROFILE_*` templates include **11 BDEW profiles** (household, commercial, agricultural), each normalised to 1 MWh/yr.
- Load models can be saved and loaded as **.LOD** files.
- "Store internally" (default) or "Read the file" at each run, from `UserHourlyParams`. The second option suits batch work.

URLs:
- https://www.pvsyst.com/help/project-design/users-needs-load/index.html
- https://www.pvsyst.com/help/project-design/users-needs-load/load-profile-ascii-file-definition.html
- https://www.pvsyst.com/help/project-design/users-needs-load/domestic-users-needs/index.html

**IT relevance: High** for self-consumption studies (residential, commercial and industrial rooftops).
- Quarter-hour meter exports can be imported as CSV.
- The bundled templates are German (BDEW). No Italian standard load profiles are bundled [verified absent from the list; whether Italian profiles exist elsewhere in PVsyst is unverified].
- The help page says sub-hourly loads are converted to hourly. Whether 8.1 sub-hourly simulations keep the sub-hourly load is [unverified].

#### 1.1.12 Self-consumption and grid-connected storage

##### 1.1.12.1 Self-consumption without storage
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/self-consumption.html , https://www.pvsyst.com/help/project-design/users-needs-load/index.html , https://www.pvsyst.com/help/project-design/results/simulation-variables-grid-system.html , https://www.pvsyst.com/help/release-notes/index.html (7.2.17)

- **Activation.** Self-consumption is computed as soon as a valid *user's needs* (load) profile is defined; an hourly profile is recommended. Load definition modes (detailed in 1.1.11): unlimited load (grid default), fixed constant load, monthly values, daily profiles in hourly values (constant, seasonal, monthly normalisation, weekly working days/week-ends), probability profiles (12 power classes, mainly DC-grid), daily household consumers, **load values from an ASCII/CSV file** (hourly or daily), templates (*.LOD) rescalable to power or annual energy.
- **Per-step energy balance.** E_Avail (inverter output after AC losses), E_User (load), E_Solar = E_User − EFrGrid (PV used on site), E_Grid (excess injected), EFrGrid (drawn from grid), SolFrac = E_Solar/E_User. "Net-metering" option = one meter, same price both directions. Grid re-injection can be **forbidden** (since 7.2.17); the surplus is then reported as unused energy (E_Unused).
- **Gap in the text.** The help mentions "several running modes" shown in the loss diagram, but they are only in a figure (not available as text) [unverified details].
- **IT relevance:** very high. Most Italian residential and C&I projects are justified by self-consumption; zero-export or reduced-export configurations also occur [analysis].

##### 1.1.12.2 Storage architecture implemented
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/index.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/grid-storage-system-architecture.html

- **Model.** Standard grid-connected PV system with usual solar inverters; **one centralised battery pack**; one generic **AC→DC charger** on the common AC bus at the inverter outputs and one **DC→AC battery inverter**, each defined by an efficiency curve vs power and a nominal power (losses CL_Chrg, CL_InvB in the loss diagram). Activated in the storage window; battery chosen in the storage pack tab (cells/modules in series and in parallel).
- **Architectures discussed but not implemented.** (A) shared PV array with master/slave inverters and DC-DC chargers; (B) common DC bus (directly at battery voltage, or via bidirectional DC-DC). Only (C) **common AC bus** (AC-coupled) is simulated. For other architectures PVsyst suggests matching the overall converter-chain efficiency (inverter × charger): "the overall system behavior cannot be significantly different".
- **Cost of stored energy.** A per-kWh figure from the battery-pack replacement cost and the maximum energy stored over its lifetime (the help's sentence states the ratio inverted); battery ageing (cycles, DOD, temperature) triggers replacements and feeds the economics.
- **IT relevance:** high. Behind-the-meter Li-ion storage is very common in Italian residential projects, often with **DC-coupled hybrid inverters**, which PVsyst only approximates through efficiencies [analysis].
- **Meridiana note (analysis):** implement both AC-coupled and DC-coupled (hybrid inverter) topologies explicitly.

##### 1.1.12.3 Strategies (4)
Sources: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/index.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/self-consumption-with-storage.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/storage-powers-peak-shaving.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/power-shifting-storage.html , https://www.pvsyst.com/help/project-design/grid-connected-system-definition/grid-systems-with-storage/storage-weak-grid-islanding.html , https://www.pvsyst.com/help/glossary/pv-system/bess.html , https://www.pvsyst.com/help/release-notes/index.html

| Strategy | Needs | Control logic (as documented) | Sizing aids / defaults | Main outputs |
|---|---|---|---|---|
| **Self-consumption** | Hourly load profile | Charge only when PV > load; discharge immediately to cover the load until empty; **battery never feeds the grid**; tariff-driven (time-of-use) dispatch "not yet implemented"; charge/discharge limited by PMaxCharge (charger) and PMaxDischarge (battery inverter) | Residential: PV should cover daily load most days; for effective grid independence battery ≥ 1-2 days of consumption, ideally 3-4; charge ≥ 3 h lead-acid, down to 1 h Li-ion; battery inverter ≥ peak load; discharge ≤ C3 (lead-acid) / ~C1 (Li-ion) | Stored vs direct energy, EBatCh − EBatDis (battery loss), CL_Chrg, CL_InvB, E_User, E_Solar, EFrGrid, SolFrac, E_Grid, E_Unused (when re-injection forbidden) |
| **Peak shaving** | Grid power limit | Store PV power above the injection limit; discharge later (daily cycles, discharged at end of night) | Dialog shows clear-sky max PV power; limit below it; charger power = max clear-sky PV − limit; battery inverter may be smaller; capacity ≈ clear-day excess energy | EBatDis, EBatCh − EBatDis, CL_Chrg, CL_InvB, EUnused (battery full or charger saturated), E_Grid |
| **Power shifting** (new in 8.0.17) | Charge/discharge schedule | Charging: *fraction of PV production* (applied to expected nominal EArray), *fixed charging power*, or *fixed grid export* (surplus to battery; acts as peak shaving); daily or hourly settings. Discharging: *specified hours* (fixed power per slot) or *during the night* (night from the MET file, with dusk/dawn fractions). Daily cycles; **not compatible with self-consumption** | Daily dial in half-hours (in hourly simulation a half-hour = half power over the hour), per-hour values, or **CSV time series** (8.1.0); clear summer/winter-day charging energy shown; discharge energy ≥ charge energy; capacity ≤ max daily charging energy; charger and battery-inverter defaults from the strategy, limited by battery ratings; grid limit should be set at injection point | Stored and direct energies at injection (basis of tariff economics), battery global loss (round-trip), CL_Chrg, CL_InvB, E_Grid, EGridLim (EUnused in peak shaving) |
| **Weak grid / islanding** | Load profile + grid availability profile | Surplus PV charges battery; if full → grid (if allowed) or lost; deficit covered by battery down to one SOC/DOD limit, with a second limit keeping a reserve for grid outages; during outage, switch opens and loads are fed by PV + battery via the stand-alone (battery) inverter; grid can recharge the battery | Unavailability: built-in **random generator** (fraction, min duration, max duration or number of periods, seed) or **CSV** (≤ 0.5 = unavailable); battery ≥ 1-2 days of average load, ideally covering max demand in the longest outage | EUnused, CL_Chrg, EBatCh, EBatLss, EBatDis, CL_InvB, E_User, E_Solar (can be negative when grid charges the battery), EFrGrid, **E_Miss** (unserved load), SolFrac, E_Grid |

- **Release-note items.** 8.0.17: power shifting. 8.0.15: revision of grid-storage operation calculations. 8.1.0: power-shifting charge/discharge from CSV. 8.1.2: updated battery model (consistent energy balance). 8.1.3: self-consumption energy-balance fix. 8.1.4: SOH reduces capacity. 8.1.6: weak-grid discharge fix.
- **Power factor interplay** (1.1.9.8): batteries exchange only active energy; PF at injection may vary.
- **IT relevance.** Self-consumption: very high (residential/C&I behind the meter). Peak shaving: medium-high for export-limited plants. Power shifting: medium (merchant/utility plants with hourly price spreads; tariff economics are outside PVsyst's dispatch logic) [analysis]. Weak grid: low in Italy except backup use.
- **Meridiana note (analysis):** add tariff-aware (time-of-use) dispatch for self-consumption, which PVsyst lacks, and explicit backup (EPS) behaviour.

#### 1.1.13 Array and system losses

##### 1.1.13.0 Loss chain, defaults and the "Detailed losses" dialog

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/index.html, https://www.pvsyst.com/help/project-design/array-and-system-losses/array-losses-general-considerations.html, https://www.pvsyst.com/help/project-design/grid-connected-system-definition/project-design-tutorial.html

- **What it is:** every loss parameter starts at a "reasonable default". PVsyst advises refining each one after the first simulation. All of them are edited in *System > Detailed losses*, which has tabs per loss (IAM, Ageing and others are named in the help).
- **Order on the Array Loss diagram**, as listed by PVsyst:
  1. IAM
  2. Soiling
  3. Irradiance (low-light) loss
  4. Thermal
  5. LID
  6. Light soaking (CIS/CIGS gain)
  7. Module quality
  8. Mismatch
  9. Module degradation
  10. Optimizers
  11. DC ohmic wiring
  12. AC ohmic wiring
  13. External transformer
  14. Auxiliaries
  15. Unavailability
- **Losses Graph button:** shows the effect of some losses on the array I/V curve under chosen operating conditions.
- **Outputs:** every loss is available as hourly, daily and monthly values and on the loss diagram (1.1.15).
- **Reference concept:**
  - Losses are measured against the STC nameplate. The ideal array gives 1 kWh per kWp for each kWh/m² of incident irradiation, which follows the JRC/Ispra Normalized Performance Index and PR.
  - Shading and IAM losses are inside the official PR definition. Whether horizon loss is also inside is "not clear" according to PVsyst.
- **MPP and regulation losses:**
  - MPP loss is neglected for grid inverters. It is computed for fixed-voltage operation (EArrMPP, EArUfix, MPPLoss).
  - "Regulation loss" (energy outside the inverter window or in overload) is counted as an inverter loss.
  - In stand-alone systems the equivalent is the excess energy with the battery full. In DC-grid systems it is the current above the load.
- **Help inconsistencies to be aware of:**
  - The general-considerations page still says electrical effects of partial shading are "not explicitly calculated". The Module Layout feature does compute them (see 1.1.8).
  - The tutorial still describes IAM through the ASHRAE parametrization and module quality as "half the lower tolerance". The dedicated pages (below) supersede both.
- IT: the same chain applies to a 3 kW roof and to a multi-MW plant; only the AC/MV items (transformer, auxiliaries, unavailability) are typically switched on for large plants.
- Meridiana (analysis): model the chain as an ordered, typed list of loss stages, each storing energy before and after the stage, so that the loss diagram, monthly tables and exports all come from one source.

##### 1.1.13.1 Summary table of loss items

| Loss item | Where it is defined | Model in PVsyst | Default stated by PVsyst | Main output variable(s) |
|---|---|---|---|---|
| IAM (reflection) | PAN file (*Additional data > Customized IAM*) or Detailed losses, IAM tab | Fresnel (default since 6.67), user profile, ASHRAE (deprecated), Sandia (deprecated) | Fresnel with the module's front-surface type | FIAMBm, FIAMGl, GlobIAM |
| Soiling | Detailed losses | Yearly or monthly %, or a CSV time series (8.1.0). Applied to beam, diffuse and albedo | None stated [unverified] | FSlgBm, FSlgGl, GlobSlg |
| Irradiance (low-light) | Intrinsic to the PV model | One-diode model: Rsh exponential, Rs | n/a | GIncLss (GIncLoss) |
| Thermal | Detailed losses (Uc, Uv); PAN (α, module weight) | Steady-state balance plus transient (Prilliman adaptation, 8.1) | Uc 20, Uv 0 for a new project; α 0.9 | TempLss, TArrSS, TArray |
| LID | Detailed losses (or PAN) | Constant % on Pmpp | None by default; 2 % suggested if used | LIDLoss |
| Light soaking (CIS/CIGS) | Detailed losses (or PAN) | Constant % gain | None (manufacturers claim 3–5 %) | LigSoak |
| Module quality | Detailed losses | Constant % on Pmpp | ¼ of the tolerance span | ModQual |
| Module mismatch | Detailed losses plus tools | Constant % | Depends on string length (table below) | MisLoss |
| String voltage mismatch | Detailed losses, "String Mismatch" tool | Constant % | Depends on strings per MPPT (table below) | [unverified: probably within MisLoss] |
| Degradation / ageing | Detailed losses, Ageing tab | Degraded one-diode module for the chosen year; Monte-Carlo mismatch | Off; Imp/Vmp sharing 80/20 | On the loss diagram [variable names unverified] |
| Optimizers | System definition | Efficiency curve plus clipping | From the optimizer definition | OP_Oper, OP_Pmin, OP_Pmax, OP_Vmin, OP_Vmax |
| DC ohmic | Detailed losses, Ohmic | One R per sub-array, R·I² at each time step | 1.5 % at STC | OhmLoss |
| AC ohmic | Detailed losses, Ohmic | R·I² per wire (×3 for three-phase), up to injection; MV and HV lines | From length, section and metal | EacOhmL |
| MV/HV transformer | Detailed losses, Ohmic | Constant iron loss plus copper R·I²; optional night disconnection | Iron loss 0.1 % of the reference Pnom | ETrfLss |
| Auxiliaries | Detailed losses | Day: constant above a threshold plus proportional (W/kW). Night: constant | Not applied unless checked | Aux_Lss |
| Unavailability | Detailed losses | Time fraction or days; fixed periods or up to 5 random ones; CSV time series (8.1.6) | None stated [unverified] | UnavLss |
| Spectral | Detailed losses | CREST (a-Si), Sandia (Sandia-DB modules), First Solar (opt-in, custom coefficients from 8.1.6) | First Solar off by default | SpctCor |

##### 1.1.13.2 Thermal losses (steady state, transient, NOCT, U-values)

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/array-thermal-losses/index.html, .../array-thermal-losses/steady-state-thermal-model.html, .../array-thermal-losses/transient-thermal-model.html, .../array-thermal-losses/noct-definition.html, .../array-thermal-losses/u-value-measurement.html, .../array-thermal-losses/discussion-particular-architecture.html (all under https://www.pvsyst.com/help/project-design/array-and-system-losses/), https://www.pvsyst.com/help/release-notes/index.html (8.1.0)

- **Two layers of model:** a steady-state thermal balance gives **TArrSS**; a thermal-inertia model then gives the actual **TArray**. Each sub-array and orientation has its own temperatures, and the outputs are averages.
- **Measured array temperature:** a measured temperature (TArrMes) can be imported through the custom weather import and used instead of the model.
- **Steady-state balance:** α·G·(1−η) = (Uc + Uv·Ws)·(T_SS − T_amb).
  - G is GlobEff, or GlobInc where GlobEff is not defined.
  - α = 0.9 by default; it can be changed in the PAN file for special modules.
  - Ws is the wind speed from the weather file (usually measured at 10 m).
  - η is iterated with the electrical model, starting from 20 %. Two or three iterations give accuracy below 0.1 °C. Tools outside the simulation use one pass at η = 20 %.
  - The cell and module temperatures are taken as equal (a 0–3 °C difference is judged to have under 0.5 % effect).
- **U-value defaults and proposals:**

| Mounting | Uc [W/m²K] | Uv [W·s/m³K] |
|---|---|---|
| Free-standing / open rack (PVsyst measurements) | 29 | 0 |
| Fully insulated back (integration) | 15 | 0 |
| Semi-integrated / air duct | between 15 and 29, preferably < 22 | 0 |
| **Default for any new project** (meant for typical rooftops) | **20** | 0 |
| Domes, 40–70 cm above ground (manufacturer measurement) | 27 | 0 |
| PVUSA correlation, open rack, with official wind data | 25 | 1.2 |

  - PVsyst gives no default Uv. Wind measured at collector level can be 35–50 % lower than at a 10 m mast.
  - U-values should be fitted on site from months of POA irradiance, ambient temperature (WMO-compliant), back-of-module temperature and, optionally, wind. A dedicated bilinear fitting tool is "intended" for a future version.
- **Transient model** (new in 8.1.0, used for both hourly and sub-hourly steps):
  - It adapts Prilliman et al. (2020). The inverse relaxation time is P = 0.0046 + 0.00046·Ws − 0.00023·m_u − 0.000016·Ws·m_u.
  - m_u is the module unit mass from the PAN area and weight. The default is 11 kg/m²; values of 20 kg/m² or more are treated as invalid.
  - The weighted moving-average cutoff is 3·τ_max instead of Prilliman's 20 min.
  - PVsyst converts Prilliman's start-of-interval temperature into an analytic average over the interval, to match its own time convention.
  - The stated effect on E_Grid is 0.1–0.3 % at hourly steps, and 1–3 % when the inverter works near its overvoltage limit.
- **NOCT:** it is not used as a PVsyst parameter, because it describes a bare module and ignores the mounting mode. The help gives the equivalence formula with U, and PVsyst can propose an "operating NOCT" derived from U.
- **Particular architectures:**
  - Floating PV: PVsyst has made no dedicated study. Use literature values or import measured temperature.
  - Tilted roof with an air duct: the temperature is inhomogeneous and PVsyst uses an average. Detailed duct modelling is "outside the scope of PVsyst".
- IT: the 20 W/m²K default suits many Italian residential roofs, but for large ground plants PVsyst itself expects about 29. Integrated and BIPV roofs are near 15. Choosing U is one of the largest single sensitivities in rooftop yield.
- Meridiana (analysis): offer mounting presets (open rack, ballasted flat roof, close-mount tilted roof, integrated, floating) that map to Uc/Uv and show the source. pvlib's `pvsyst_cell` covers the steady state; the transient adaptation has to be implemented (see section 3).

##### 1.1.13.3 Ohmic losses: DC wiring, AC wiring, reference power, ampacity, resistivity, optimisation tool

Sources (under https://www.pvsyst.com/help/project-design/array-and-system-losses/ohmic-losses/): index.html, array-ohmic-wiring-loss.html, ac-ohmic-loss-inverter-to-injections.html, ac-ohmic-loss-ref-power.html, admissible-current-in-wires.html, metal-resistivity.html, wiring-loss-optimisation.html

- **Principle:**
  - Ohmic loss is always Pw = Rw·I², with Rw = ρ·L/S. The real parameter is the **resistance**, even when the user enters a percentage.
  - A loss fraction only means something at a reference power. PVsyst offers PNomPV(ac) (STC array power × inverter efficiency, the pre-7.2 choice) or PNom(Inv). This is chosen per project in Project settings, with a global default under *Preferences > Physical models > AC Loss references*.
  - The annual wiring loss is usually about **60 %** of the nominal STC fraction (the tutorial says "one half to 60 %").
- **DC array wiring:**
  - There is one equivalent resistance per sub-array, as seen by all its MPPT inputs in parallel. It is applied to the sub-array's global Imp.
  - Default: **1.5 % of STC** power. This is editable in the advanced parameters ("Default Wiring Resistance loss ratio at STC").
  - Equivalent resistance, by stages: the strings into a junction box give R_strbox = (mean string-loop resistance)/N_str. The boxes into the inverter give Rw = (R_strbox + R_wbox)/N_box, valid for identical boxes. More combiner stages can be added.
  - In simulation the loss is either R·Imp², or Rw added to the module Rserie when another operating point is needed. Both give very close results.
  - PVsyst explicitly refuses a DC "voltage drop" input, because the inverter re-tracks the MPP. The loss can therefore only be a power loss.
- **AC wiring (inverter to injection point):**
  - Defined by distance, section and metal (Cu/Al) per circuit. Three-phase counts 3 wires (single-phase 2). The neutral is ignored (balanced phases assumed).
  - The program proposes the minimum section; undersized choices are shown in red. Alternatively a % loss at the reference power can be entered, and the help says the matching wire length and voltage drop then appear.
  - Can be defined per inverter (realistic wires) or globally.
  - With MV transformers: an MV line to the injection point (or to an HV transformer). For very large plants: an HV transformer and an HV line (> 100 kV).
  - Power factor: currents are multiplied by 1/cos φ. Reactive "losses" are not evaluated.
  - Weak grids: cable sizing up to the injection point affects grid-voltage-rise trips.
- **Admissible current (ampacity):**
  - Formula from IEC 364-5-523 (1983): Imax = Imax_Ref·S^0.625, with Imax_Ref = 13.5 A/mm² (Cu) or 10.5 A/mm² (Al).
  - Assumes the least constraining "C" mounting (wires in a duct at free air). The specific current is frozen above 300 mm² (editable). An installation-mode factor (default 1) exists in the advanced parameters.
  - Checking the real laying conditions is left to the user; PVsyst cites 70 °C for ducts in the sun, with about −40 % ampacity.
- **Metal resistivity:** ρ = ρ20·(1 + 0.0039·(T − 20)), at a default 50 °C. That gives 18.8 mΩ·mm²/m (Cu) and 31.5 mΩ·mm²/m (Al), editable as hidden parameters.
- **Wiring loss optimisation tool:**
  - A wiring schema has colour-coded circuits: string loops, box to inverter, optional group/combiner boxes.
  - Inputs are the average loop lengths. It proposes standard sections starting from the smallest one compatible with the current.
  - The help says "European Norm (CEI 364-5-523, 1983)" for ampacity. Here "CEI" is the French name of the IEC, not the Italian CEI.
  - Target: a maximum % loss at MPP, or a voltage drop for fixed-voltage systems. It minimises copper mass or cost (wire prices can be entered).
- IT: Italian designs must still document cable sizing and voltage drop to CEI 64-8 and the applicable CEI-UNEL ampacity tables (thresholds not checked here). PVsyst's ampacity is a generic 1983 IEC formula, not a substitute. The AC "voltage drop at reference power" readout helps reconcile the two.
- Meridiana (analysis): store circuits as real cable objects (length, section, metal, laying method), compute R for the simulation, and run a separate standards check (ampacity, voltage drop) with Italian tables. This makes the "loss vs voltage drop" distinction explicit in the UI.

##### 1.1.13.4 External MV/HV transformers and transformers in cascade

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/ohmic-losses/external-transformer-losses.html, https://www.pvsyst.com/help/project-design/array-and-system-losses/ohmic-losses/transfo-in-cascade.html, https://www.pvsyst.com/help/project-design/array-and-system-losses/ohmic-losses/ac-ohmic-loss-inverter-to-injections.html

- **Configurations:**
  - One or several MV transformers for the whole system (inverter output is shared equally), or one MV transformer per sub-array (each may differ).
  - An optional HV step-up transformer before injection.
- **Iron (no-load) loss:**
  - Constant while connected. Default **0.1 %** of the reference nominal power.
  - **Night disconnect** option (global for all transformers): without it, night-time iron loss gives a negative E_Grid at night.
- **Copper (resistive) loss:** a single equivalent resistance, loss = R·I².
- **Definition modes:**
  - Generic: % of the reference Pnom.
  - Datasheet (recommended): nominal power, no-load loss, and copper loss or global loss/efficiency at Pnom.
  - PVsyst converts datasheet values to its reference Pnom: iron % scales as P_iron/Pnom_ref, resistive as P_res·(Pnom_ref/PnomTrf)².
  - Worked example: a transformer of PNomTrf = 1.5 MW with 1.5 kW iron and 16.5 kW total loss, on a 1 MW (ac) system, gives 0.15 % iron and 0.66 % resistive.
- **Topology limit:** each MV transformer is assumed to reach the common point through its own "star" cable. Cascaded transformers on one bus are not implemented.
  - The workaround is to set equivalent lengths L_PVs = (L1·1 + L2·4 + L3·9)/3, squaring the upstream count. A detailed model is announced for "a future version".
- IT: relevant to any plant with its own MV/LV substation (MV-connected commercial and utility plants). The datasheet mode matches how Italian transformer data are usually given (no-load and load losses). Night disconnection is a real design choice with an energy and metering effect (not analysed here).
- Meridiana (analysis): model the AC side as a small radial network (cables, transformers, busbars), which handles cascaded transformers natively. That removes a documented PVsyst limitation.

##### 1.1.13.5 Module quality, LID, light soaking, irradiance loss

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/module-quality-losses.html, .../lid-loss.html, .../light-soaking-for-cigs.html, .../irradiance-loss.html (under https://www.pvsyst.com/help/project-design/array-and-system-losses/)

- **Module quality loss:**
  - The user's confidence in real module power versus the datasheet. It is a constant % on array Pmpp in all conditions.
  - The default is **one quarter of the tolerance span**: ±3 % gives 1.5 %; positive sorting 0/+3 % gives −0.75 % (a gain).
  - PVsyst calls the ¼ "a PVsyst choice". Flash-test accuracy is about ±3 %.
- **LID:**
  - Only p-type boron-doped wafers; typically 1–3 %.
  - **No default.** If enabled, 2 % is suggested.
- **LeTID:** not found anywhere in the 8.1 help (the search index has no occurrence) [not modelled as a distinct loss; any LeTID allowance would have to go into LID, module quality or degradation: unverified].
- **Light soaking (CIS/CIGS):** an optional gain; manufacturers claim 3–5 %. The simulation is then "not valid for the first production year", and how long the gain lasts is unknown.
- **Irradiance loss:**
  - Efficiency drop below 1000 W/m², an intrinsic result of the one-diode model (Rshunt exponential law, Rserie).
  - Low Rsh and high Rs ("poor quality") modules look better at low light relative to STC.
  - PVsyst uses this to explain why amorphous modules gave higher kWh/kWp in Central Europe.
- IT: module quality and LID are the classic "contractual" knobs in Italian EPC yield studies. LeTID-prone PERC products are common in the Italian installed base, so Meridiana should offer an explicit LeTID item.
- Meridiana (analysis): keep these as separate, labelled constants with a source field (datasheet tolerance, lab report, assumption) printed in the report.

##### 1.1.13.6 Mismatch losses (principles, module dispersion, string mismatch tool)

Sources (under https://www.pvsyst.com/help/project-design/array-and-system-losses/array-mismatch-losses/): index.html, mismatch-basic-principles.html, mismatch-between-strings.html, mismatch-loss-due-to-modules-dispersion.html

- **Definition:** mismatch = the sum of each sub-module's Pmpp minus the Pmpp of the combined array I/V curve. A sub-module is the cells behind one bypass diode, usually 3 per module.
- **Causes listed:**
  - Module spread: power classes of about 1.5–2 %, flash-test accuracy of ±3 % or worse.
  - LID spread, uneven ageing (Ageing tool), uneven soiling (assumed inside soiling).
  - Partial shading, which is handled in Module Layout as "electrical shading loss".
  - Bifacial rear inhomogeneity: a parameter exists but "no reliable data nor model".
  - String-voltage differences: wire lengths, temperature gradients, cloud passages (neglected), mixed orientations (usually negligible).
- **Default values:**

| Module mismatch | 1 module/string | 2 | 3 | > 3 |
|---|---|---|---|---|
| All technologies except thin film | 0 % | 0.5 % | 1 % | 2 % |
| Thin film | 0 % | 0.25 % | 0.5 % | 1 % |

| String voltage mismatch | 1 string/MPPT | 2 | 3–10 | > 10 |
|---|---|---|---|---|
| Default | 0 % | 0.05 % | 0.1 % | 0.15 % |

- **Tools:**
  - *Detailed computation*, also under *Tools > Electrical behaviour of PV arrays*: random module samples (Gaussian or square distribution of Isc/Voc) are combined series/parallel. A *Histogram* button repeats the sampling. Per-module flash data cannot be imported yet, but their RMS can be used.
  - *String Mismatch* (in Detailed losses): teaching views of voltage versus current mismatch.
    - Voltage example: a 500 m vs 0 m string of 2.5 mm² wire gives a 5.2 % voltage difference but only 0.38 % mismatch; a 10 °C difference gives 0.47 %.
    - Current example: one weak module, with a bypass threshold near an 18 % current deficit.
    - A configurable rectangular layout (tables, rows, inverter positions dragged with the mouse) gives the wire lengths and mismatch per MPPT input. Example: 0.03 % for 2 strings per input, 0.05 % with one central inverter.
- **In simulation:** a constant loss factor. Mismatch matters much more at fixed voltage than at MPP.
- IT: the default 2 % for usual string lengths is a significant, often unchallenged assumption in Italian yield reports. A tool that justifies a lower value (sorted modules, MLPE) has commercial value.
- Meridiana (analysis): pvlib's single-diode functions plus a series/parallel combiner can reproduce the Monte-Carlo tool. Expose the result as a recommended value with its distribution.

##### 1.1.13.7 Soiling (and snow)

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/soiling-loss.html, https://www.pvsyst.com/help/project-design/grid-connected-system-definition/project-design-tutorial.html, https://www.pvsyst.com/help/release-notes/index.html (8.1.0)

- **Input:** a constant or **monthly** soiling fraction. Since 8.1.0, also a **CSV time series** (see the shared "Import time series parameters" form, 1.1.19).
- **Model:** treated as an irradiance loss on beam, diffuse and albedo, after IAM (GlobSlg, then GlobEff).
- **Guidance:**
  - Under 1 % in moderately rainy residential areas; several % near industry or railway lines.
  - Moss and dust along frames at low tilt (frameless modules recommended); bird droppings under 2 %.
- **Snow:** not in the weather data. Model it as partial or full soiling in winter months (the tutorial suggests 50 % for a month with 15 days of cover).
- **Default:** the 8.1 help states no default value [unverified].
- IT: monthly soiling profiles suit agricultural and agrivoltaic sites, industrial roofs and low-tilt roofs. The snow-as-soiling workaround is relevant for Alpine and Apennine sites. A time-series input allows cleaning schedules.
- Meridiana (analysis): pvlib offers physical soiling models (HSU, Kimber) and snow models (see section 3). Meridiana can offer "monthly table", "time series" and "physical model" modes.

##### 1.1.13.8 IAM (incidence angle modifier)

Source: https://www.pvsyst.com/help/project-design/array-and-system-losses/array-incidence-loss-iam.html

- **Physics:**
  - The angular transmission loss normalised to normal incidence (the about 5 % normal reflection is already in STC).
  - Applied to beam directly, and to diffuse and albedo by integration over the visible hemisphere, assuming isotropic diffuse.
- **Models:**
  - **Fresnel** (default since 6.67): air-glass then glass-EVA interfaces; light trapping and cell or finger reflections are not modelled. Front surface types:
    - normal glass;
    - AR coating;
    - textured glass (currently identical to AR);
    - plastic (currently identical to normal glass);
    - "not defined" (legacy, uses ASHRAE).
  - **User-defined profile:** from measurements, "use with caution". For database modules PVsyst requires an independent indoor lab report.
  - **ASHRAE:** F = 1 − b0·(1/cos i − 1) with b0 = 0.05; deprecated.
  - **Sandia:** a 5th-order polynomial with default coefficients; deprecated.
  - The bifacial rear side always uses Fresnel for normal glass without AR coating.
- **Where defined:** in the PAN file by default. It can be overridden in Detailed losses (uncheck "Uses definition of the PV module").
- **Detailed Study tool:** compares models over a full year by beam, diffuse and albedo distributions.
  - Geneva examples: Fresnel normal glass −0.25 % vs ASHRAE; AR vs normal glass 0.75 %; unrealistic user profiles up to 2 %.
  - The help cites PVEL's 2024 IAM tests on 44 modules as consistent with Fresnel AR.
  - AR coating ageing is not modelled.
- IT: none specific beyond accuracy. Keep Fresnel AR as the default for modern modules.
- Meridiana (analysis): pvlib has `iam.physical`, `iam.ashrae`, `iam.interp` and `iam.marion_diffuse` (see section 3). Replicate PVsyst's hemispherical integration for diffuse and albedo, combined with horizon and near-shading factors (1.1.14.1).

##### 1.1.13.9 Spectral correction

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/spectral-correction.html, https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/firstsolar-spectral-correction.html, https://www.pvsyst.com/help/release-notes/index.html (8.1.6)

- **Models:**
  - **CREST** (Loughborough) parametrisation for amorphous silicon; applied automatically when spectral correction is active.
  - **Sandia** spectral correction for Sandia-database modules; automatic.
  - **First Solar** model: **disabled by default**, switched on in Detailed losses. It uses the coefficient set matching the module technology, or any set chosen by the user. **Custom coefficients** are accepted since 8.1.6, and since 8.1.6 a correction-factor graph is shown in the dialog and the report.
- **First Solar model inputs:** air mass (from altitude and sun position) and precipitable water, taken from the file or estimated from relative humidity. RH is always present in PVsyst synthetic files since 6.7.4.
- **Crystalline and CIS:** the spectral dependency is called "extremely weak" and neglected (physical-models page).
- **Reporting:** when used, the coefficient set is listed in the report and the loss diagram shows a "spectral losses" item (SpctCor).
- IT: mostly irrelevant for c-Si rooftops. Relevant only for CdTe utility plants.
- Meridiana (analysis): pvlib offers `spectral_factor_firstsolar` and other spectral models; CREST is absent from pvlib (section 3).

##### 1.1.13.10 Auxiliaries consumption

Source: https://www.pvsyst.com/help/project-design/array-and-system-losses/auxiliaries-consumption.html

- **What it is:** energy used to run the system (fans, air conditioning, electronics, lights), subtracted from the energy sold. It is defined globally and only applied when "Auxiliaries consumption defined" is checked.
- **Inputs:**
  - Day: a constant power that applies only above a production threshold. Example for 100 MW: 72 kW, active above 100 kW output.
  - Day, optionally: a proportional term in W/kW (for example cooling that tracks inverter heat).
  - Night: a constant power (13 kW in the example).
- **Output:** Aux_Lss (day and night). The inverter's own night consumption is separate (IL_Night, shown when > 0.01 %).
- **Inverter auxiliaries:** an auxiliary power defined in the OND can be used as the default here. Beware double counting if the fans are already inside the efficiency curve.
- **8.1.6 change:** night-time auxiliaries are no longer applied while the system is unavailable (release notes).
- IT: relevant for utility-scale plants (tracker motors, SCADA, conditioning of inverter and MV stations). Usually zero for residential.

##### 1.1.13.11 Unavailability

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/unavailability-loss.html, https://www.pvsyst.com/help/release-notes/index.html (8.1.6)

- **Input:**
  - A time fraction or a number of days, with specific OFF periods or up to **5 randomly generated** periods per year.
  - Since **8.1.6**, definitions are "more flexible" and can come from a CSV time series.
- **Model:** the system is OFF during those periods, so the energy loss depends on season and weather. The resulting loss is "only statistical" and a target annual loss value cannot be set directly (trial and error).
- **Output:** UnavLss.
- IT: maps onto availability guarantees in Italian O&M contracts. Meridiana (analysis) should allow a target energy-availability input, solved automatically, which PVsyst cannot do.

##### 1.1.13.12 Ageing and module degradation (Ageing tab, Monte-Carlo mismatch)

Sources (under https://www.pvsyst.com/help/project-design/array-and-system-losses/ageing-pv-modules-degradation/): index.html, ageing-use-of-the-dialog.html, module-performance-degradation.html; https://www.pvsyst.com/help/release-notes/index.html (8.0.0)

- **Concept:**
  - Simulate one chosen operating year with degraded modules plus a mismatch that grows with time.
  - Use an **average** degradation rate, not the warranty slope. For example, a −3 % initial / −20 % at 25 years warranty corresponds to a −0.68 %/yr guaranteed limit, while average measured rates are about −0.3 %/yr.
  - A graph of rates by Köppen-Geiger-PV climate zone is shown; hot humid climates reach about 1 %/yr.
- **Inputs (Ageing tab, "uses in simulation"):**
  - Simulation year, which is printed in the report.
  - Average degradation factor (%/yr).
  - Isc RMS and Voc RMS dispersion, used by the Monte-Carlo mismatch model (Gaussian, truncated at 2σ, constant rate per module).
  - Option to keep the calculated Monte-Carlo curves in the variant; save/load the model.
  - Warranty curve display.
- **Model:**
  - Values are evaluated once per year, at mid-year (year 10 uses 9.5 years).
  - The degraded one-diode module is built automatically. **Imp degradation sharing is 80 %** (Imp/Vmp; the default since v8, it was 50/50 in v7). The Imp factor is applied to Isc and Imp, the Vmp factor to Voc and Vmp, and Rsh/Rs are refitted.
  - A degraded module can also be built explicitly and saved as a PAN (*Additional data > Degradation*), for example to mix an old array with a new one.
- **Outputs:** module degradation loss and "evolutive mismatch" on the loss diagram.
- **Multi-year runs:** done with the Ageing Tool (1.1.14.3).
- IT: important for bankable studies over 20–30 years. The "pre-degraded PAN" feature directly supports revamping or extensions of existing Italian plants, where old and new modules share inverters.
- Meridiana (analysis): pvlib has no degradation module (section 3). Implement degradation as a time-varying modifier of the one-diode parameters with the same Imp/Vmp split, plus a Monte-Carlo mismatch helper.

##### 1.1.13.13 Optimizer losses

Sources: https://www.pvsyst.com/help/project-design/array-and-system-losses/optimizer-loss.html, https://www.pvsyst.com/help/project-design/results/simulation-variables-grid-system.html

- **Where it sits:** after the array losses and before DC wiring. Wiring between module and optimizer cannot be specified.
- **Normal operation:** the efficiency is a function of the duty cycle (output/input voltage ratio) and the input voltage.
- **Limits:** if input power, voltage or current exceeds the optimizer's limits, a new operating point is taken on the module I-V curve and the difference is stored as clipping. Variables: OP_Oper, OP_Pmin, OP_Pmax, OP_Vmin, OP_Vmax.
- Optimizer architectures and brands (SolarEdge, Huawei, Tigo and others) are covered in the grid-system part (1.1.10).
- IT: optimizers are common on Italian residential and commercial roofs with complex shading. The loss accounting has to coexist with Module Layout electrical shading.

##### 1.1.13.14 Electrical shading loss (cross-reference)

The electrical mismatch due to partial shading (ShdElec, from "according to module strings" or Module Layout) is applied in the PV-array stage, after temperature and spectral. It is documented with the shading models in 1.1.7 and 1.1.8. Source: https://www.pvsyst.com/help/project-design/simulation/simulation-process-irradiance-and-pv-array.html

#### 1.1.14 Simulation

##### 1.1.14.1 Simulation process: irradiance and PV array (common to all system types)

Source: https://www.pvsyst.com/help/project-design/simulation/simulation-process-irradiance-and-pv-array.html

- **Before the time loop:**
  - Input consistency has already been checked.
  - **Shading factor tables** are computed if near shadings exist.
  - **Diffuse and albedo attenuation factors** are computed by integrating horizon × near-shading table × IAM over the visible hemisphere. They are constant over the year.
- **At each time step, irradiance:**
  1. Read GlobHor, temperature, and if present DiffHor and wind. If DiffHor is missing, a diffuse model is used. Cap DiffHor at GlobHor. This gives GlobHor, DiffHor, BeamHor, T_Amb, WindVel.
  2. Transpose with **Hay or Perez** (user preference), using solar angles at the **middle of the time interval** from the weather file (with any time shift). This gives GlobInc, BeamInc, DiffInc, DiffSInc, AlbInc.
  3. Horizon on beam (ON/OFF), giving GlobHrz.
  4. Near-shading factor on beam, from the table or recalculated. This is the "linear" (irradiance-deficit) shading loss, giving GlobShd.
  5. IAM on beam; constant attenuation factors on diffuse and albedo, giving GlobIAM.
  6. Soiling on all components, giving **GlobEff** (with BeamEff, DiffEff, Alb_Eff).
  - Ratios available for display: Bm/Gl, Diff/Gl, DifS/Gl, Alb/Gl, FTransp, FIAMBm, FIAMGl, FShdBm, FShdGl, FIAMShd.
- **At each time step, PV array** (per sub-array and orientation):
  1. TArray from the thermal balance.
  2. The one-diode model gives the MPP at STC efficiency (EArrNom).
  3. Then the losses: irradiance, temperature, spectral (if any), electrical shading mismatch, module quality, LID, mismatch, array wiring. The result is **EArrMPP**, the virtual MPP energy.
  4. The system may move the operating point (MPPLoss) or be unable to use the energy (full battery or tank: EUnused). The energy actually used is **EArray**.
- **Mixed orientations on one input:** the weather chain is repeated per orientation and area-weighted. The I/V curves are combined electrically and the difference is **MixLoss**, usually close to 0.
- **Units convention:** all energies are average power over the step (kWh/h). The same formalism is kept for sub-hourly steps.
- IT: this order defines what "near shading loss" and "IAM loss" mean in Italian reports produced with PVsyst. Meridiana must reproduce it to make results comparable.

##### 1.1.14.2 Simulation process: grid system, and other system types (brief)

Sources: https://www.pvsyst.com/help/project-design/simulation/simulation-process-grid-system.html, .../simulation-process-stand-alone-system.html, .../simulation-process-dc-grid-system.html, .../simulation-process-pumping-system.html (under https://www.pvsyst.com/help/project-design/simulation/)

- **Grid system, inverter behaviour:**
  - Below the input threshold, the array is open circuit (I = 0, U = Voc).
  - Above nominal power, the inverter behaves as defined: **Limitation**, **Cut**, or **Cut until morning**.
    - Limitation means the inverter searches the I/V curve for the point at PNom(eff) by reducing current.
    - Cut means the array is open circuit and the power is zero.
    - Cut until morning (very old inverters) means it stays off until the next morning.
  - PNom(eff) may depend on inverter temperature and power factor.
  - At the MPP window limits, the voltage is clamped on the I/V curve. Otherwise the inverter runs at the MPP and its efficiency curve applies.
  - Each deviation from ideal MPP is accumulated separately (IL_* variables).
  - With a user load, self-consumed and re-injected energies are accounted. Main outputs: InvLoss, EArray, EOutInv, E_User.
  - The sub-hourly clipping correction is covered in physical models (1.10.4); its variable is ILPmxSH, grouped with IL_Pmax. Source: https://www.pvsyst.com/help/physical-models-used/grid-inverter/subhourly-clipping-correction.html
- **Stand-alone:**
  - Iterative current balance at the battery terminals between PV (MPPT converter or direct coupling on the I/V curve), battery (voltage a function of SOC, temperature and current), load and back-up generator.
  - Regulation states with hysteresis: PV disconnected when full, load disconnected at deep discharge, generator start at low SOC.
  - The exact threshold-crossing time inside a step is solved.
  - Since 8.0, several sub-arrays share one battery, with per-sub-array control and an end-of-step battery update (an approximation). Results include ESolar and direct use versus stored energy (demand-side-management hint).
- **DC-grid:** without a load profile, the array runs at the fixed supply voltage. With a load, a current balance runs with the PV-to-user and supply-to-user line resistances, plus overvoltage regulation when PV covers the load.
- **Pumping:** an iterative flow/head solution (friction, drawdown). Tank full and empty conditions are managed. User draw is constant over the day. Configuration-specific loss structure; outputs are water delivered and missing, unused PV energy, efficiency and PR.
- These system types are detailed in 1.2–1.4.

##### 1.1.14.3 Simulation dialog, advanced simulation, time steps

Sources: https://www.pvsyst.com/help/project-design/simulation/index.html, https://www.pvsyst.com/help/project-design/simulation/advanced-simulation.html, https://www.pvsyst.com/help/release-notes/index.html (8.1.0, 8.1.7)

- **Gating:** simulation is enabled only when all indicators are green or orange (no red errors). Since 8.0 it is also disabled until the partial-system modes for diffuse shading are chosen (release notes 8.0.0).
- **Run Simulation** button (quick) or **Advanced simulation**.
- **Time step:**
  - 1 h, or the sub-hourly step of the weather file. Sub-hourly simulation for grid and stand-alone systems is new in **8.1.0**.
  - Since **8.1.7**, predefined sub-hourly steps can be selected in Advanced simulation, so data can be run at coarser steps.
  - PVsyst advises hourly runs while iterating and sub-hourly once the design is final.
- **Advanced simulation contents:**
  - Variant title.
  - Simulation dates, restricted to the range of the weather file.
  - **Output File** (CSV export).
  - **Hourly data storage:** the variables kept at time-step resolution in the .VCi (about ten by default).
  - **Special graphs:** on-line graphs.
  - **Comparisons:** with measured data.
  - **Batch simulation**, **Optimization tool**, **Aging tool**.
- **Result storage:** in `<project>.VCi`, with i = 0..9 or A..Z (up to 36 variants per project). Simulation-versus-measurement runs are stored as `.CMi`.
- IT: none specific.
- Meridiana (analysis): replace the "LEDs" gate with inline validation, as in Aurora (section 2), and keep every variant's inputs and results in a versioned project file.

##### 1.1.14.4 Ageing Tool (multi-year simulation)

Source: https://www.pvsyst.com/help/project-design/simulation/ageing-tool.html

- **Purpose:** yield and PR evolution over the years, with module degradation and growing mismatch. **Grid-connected only.**
- **Inputs:**
  - Degradation parameters, initialised from Detailed losses.
  - Either one weather file (ideally a TMY), simulating some years and **interpolating** the rest (total years and step), or a series of real yearly files (full years only). Up to 2 groups at a time.
  - Optional per-year variants, reports (written to UserData) and hourly files (written to UserHourly).
- **Outputs:**
  - A table and 2 graphs: a chosen variable, and PR evolution with relative PR loss.
  - The reference PR is PR_ref = PR(1) + ½·[PR(1) − PR(2)].
  - Up to 3 extra variables. A **2-page report** section. "Copy the table" to Excel.
- **Lifecycle:** results are erased when the main simulation changes; the tool needs a successful main simulation first.
- IT: a degressive PR or yield guarantee (EPC) and long-term cash-flow inputs come from here.

##### 1.1.14.5 CSV output of time-step, daily or monthly values

Source: https://www.pvsyst.com/help/project-design/simulation/create-a-csv-file-of-hourly-daily-values.html

- **Where:** *Advanced simulation > Output file*. The variables must be chosen **before** the run.
- **The option resets after each run:** "File name" switches back to "No output", so it has to be re-enabled for the next simulation.
- **Format:**
  - The separator is usually ";", with optional fixed-width columns.
  - The decimal character, the date format (DD/MM/YY vs MM/DD/YY) and the units are chosen.
  - Values: simulation time step (sub-hourly if the simulation is), daily or monthly.
  - Variables are chosen from groups and can be reordered by drag-and-drop.
  - Templates can be saved and loaded for reuse across variants and projects.
- **Location:** the workspace `UserHourly` folder.
- **Quicker alternative for monthly data:** monthly tables can be exported or copied to the clipboard.
- Meridiana (analysis): make exports persistent presets, write Parquet or CSV with ISO 8601 timestamps and explicit interval convention, and avoid the locale traps PVsyst documents.

##### 1.1.14.6 On-line graphs ("special graphs")

Sources: https://www.pvsyst.com/help/project-design/simulation/on-line-graph-definition.html, https://www.pvsyst.com/help/project-design/simulation/advanced-simulation.html

- **Defined before the simulation** and accumulated during it: up to **30** plots, about 10 by default.
- **Types**, each daily or hourly with units:
  - **Time evolution** (own interval);
  - **Scatter** (e.g. input/output diagram);
  - **Value distribution histogram**: start, width and number of bins up to 400, with empty classes trimmed, a threshold on the first class, and accumulation in time or energy;
  - **Ordered values** (cumulative distribution).
- Definitions can be saved in a library. Default histograms rescale automatically; user histograms must be adapted to system size.
- Meridiana (analysis): with all time-series results stored, graphs can be built after the run. PVsyst's "define before simulating" constraint is an artefact to avoid.

##### 1.1.14.7 Simulation and comparison with measured data

Source: https://www.pvsyst.com/help/project-design/simulation/simulation-and-comparison.html (details in 1.9)

- Dates come from the measured data file and can be restricted. A *Comparison* definition maps simulation variables to measured channels, with constraints.
- Pairs of values are accumulated at time-step or daily resolution. Results are stored as `.CMi`. Report Preview can compare two projects or variants.

##### 1.1.14.8 Batch mode and parametric studies (brief; full detail in 1.1.20)

Sources: https://www.pvsyst.com/help/project-design/simulation/batch-mode-parametric-studies.html, https://www.pvsyst.com/help/getting-started/printing/pdf-file-generation-in-batch-mode.html

- **Workflow:**
  1. Choose the parameters to vary and the yearly output variables.
  2. PVsyst writes `<Project>_BatchParams_i.CSV`; the user fills one row per run in Excel or LibreOffice and closes the file.
  3. Run. Results go to `<Project>_BatchResults_i.CSV`.
  - The help names both `\UserBatch` and `\UserData` as the folder.
- **Variable parameters:**
  - Several weather files, or several sites. If no .MET exists within 15 km (default, a hidden parameter), PVsyst generates a synthetic one with the Meteonorm DLL.
  - Base .VCi, saving .VCi, hourly outputs, **Create PDF report** per run.
  - Plane tilt and azimuth: a **single fixed orientation only**, plus unlimited-shed pitch and electrical effect.
  - 3D sheds (pitch, collector width); trackers (pitch, backtracking, stroke limits).
  - Module type, modules in series and strings, module quality loss, inverter type and count.
- **Outputs:** yearly values only.
- IT: useful for tilt, pitch and DC:AC trade-off studies on Italian ground plants. The single-orientation limit makes it unusable for complex roofs.

##### 1.1.14.9 Sheds optimization tool (parametric scan)

Sources (under https://www.pvsyst.com/help/project-design/simulation/optimization-tool/): index.html, create-new-parametric-scan.html, view-existing-scan.html

- **Scope:** only for projects with **sheds** in the 3D scene, for now. A full simulation runs for each combination, unlike the approximate optimisation tools in the Orientation dialog.
- **Create a scan:**
  - Name.
  - Up to several parameters, each with min, max and number of steps:
    - **tilt** and **azimuth** (fixed tilt or unlimited sheds);
    - **pitch** or **GCR** (sheds in 3D).
  - Sketches show the ranges, with the current value in blue.
  - A time estimate based on the last run; impossible combinations (pitch too short) are skipped. Run/Abort; aborting loses the results.
- **View a scan:**
  - Scans are listed per variant and can be deleted.
  - Result variable: **GlobInc, GlobEff, EArray or E_Grid** (default E_Grid).
  - 1D curve or 2D colour map (blue to red).
  - Sliders for non-displayed parameters; maximum marked with a red dot and its values; full-range or adaptive scale.
- IT: directly relevant to ground-mounted and flat-roof row layouts (pitch versus yield versus land or roof use).
- Meridiana (analysis): generalise to any parameter (DC:AC, string length, tracker GCR, azimuth on roofs) and add economic objectives (LCOE, NPV) to the scan.

#### 1.1.15 Results and report

##### 1.1.15.1 Results dialog and result types

Source: https://www.pvsyst.com/help/project-design/results/index.html

- **Report:** a printable report with a full parameter table and a summary of the main results.
- **Monthly values for all variables**, stored in the .VCi:
  - **predefined tables** by theme;
  - a **custom table** of any 8 variables;
  - **custom monthly graphs** of up to 4 variables on one common axis.
- **Detailed time-step values** for the preselected variables: hourly, sub-hourly and daily plots with navigation through the year, and multiple variables.
- **On-line special graphs** (about 10 by default): detailed loss diagram, monthly/daily normalised yields, PR, input/output diagram, incident energy and array output distributions.
- **Economic evaluation** after simulation (see 1.1.16).
- **Other variants** of the project can be recalled for quick comparison.

##### 1.1.15.2 PDF report: contents, settings, preview, comparison, export

Sources: https://www.pvsyst.com/help/getting-started/printing/index.html, https://www.pvsyst.com/help/getting-started/printing/print-settings.html, https://www.pvsyst.com/help/getting-started/printing/preview-a-document.html, https://www.pvsyst.com/help/getting-started/printing/compare-reports.html, https://www.pvsyst.com/help/getting-started/printing/copying-document-pages-to-clipboard.html, https://www.pvsyst.com/help/getting-started/printing/pdf-file-generation-in-batch-mode.html, https://www.pvsyst.com/help/project-design/results/index.html, https://www.pvsyst.com/help/project-design/grid-connected-system-definition/single-line-diagram.html, https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/near-shadings-tutorial.html, https://www.pvsyst.com/help/getting-started/languages.html, https://www.pvsyst.com/help/getting-started/licensing/index.html, https://www.pvsyst.com/help/release-notes/index.html (7.1.0, 7.3.0, 8.0.0, 8.0.12, 8.0.13, 8.1.6)

- **Structure:**
  - Since the 7.1 overhaul the report is built from automatic, modular "blocks".
  - **Cover page:** fully customisable with image, text and contact data.
  - **Summary page:** project, variant and results.
  - **Table of contents**, bookmarked and linked in the PDF. Drawn at 600 DPI.
  - The tutorial's minimal description has 3 pages: parameters; main results with normalised graphs and the monthly table; the arrow loss diagram.
- **Documented content and optional pages:**
  - General parameters: system kind, orientations, trackers, GCRs ("Backtracking GCR" and "Average GCR" since 8.0.0), the diffuse-shading calculation mode for trackers, and the fast/slow shading calculation mode (7.4.1).
  - Horizon drawing and table; near-shading scene (the saved view via *File > Save scene view > Keep this view for the report*); Module Layout prints.
  - Detailed user needs.
  - **Single-line diagram**, selectable in *Report options > Final report option*.
  - Main results and the monthly table (selectable columns).
  - **Loss diagram**; predefined and special graphs (choosable and reorderable since 7.3).
  - P50/P90 values; **PR_Bifi** for bifacial (8.0.12); weather-corrected PR only if requested in *Report Preferences*.
  - The grid-limitation mode when applied (8.0.13); spectral coefficient set and correction graph (8.1.6).
  - Ageing tool (2 pages), carbon balance, economic evaluation.
  - The PAN file name when custom (8.0.13), and the PV module data origin ("original database" or "custom defined", release notes 6.39).
- **Print settings:** company logo, header title (company, name or custom text), two comment lines, date format (US format since 8.0), output **language**, colour or greyscale, set as default. A "Displayed data" tab selects the pages.
- **Preview:**
  - Report options, edit cover page, **save as PDF**, print, copy to clipboard.
  - **Export** to the results-export dialog. Loss-diagram values can be exported to Excel with explanations (*Export > Loss diagram values*, see the bifacial results page).
  - **Compare with another project or variant:** side by side, differences highlighted in yellow.
  - Page navigation and zoom.
  - Clipboard copy is per page as an image (100–600 DPI).
- **Batch:** a PDF report per run can be created ("Create PDF report").
- **PDF and licensing:**
  - Since 8.0.0 the PDF is no longer password-protected.
  - In Evaluation mode the report carries a watermark and components are limited to generic ones.
- **Language:** the UI exists in English (reference) and in French, German, Spanish, Portuguese, **Italian**, Turkish, Korean, Chinese, Japanese, Polish and Russian. The help says the document output language is selectable; the exact list of report languages is not stated [unverified for the report specifically].
- IT: the PDF report is the deliverable that clients, banks and technical advisors receive; that it fills this role in Italy is my analysis, not PVsyst text. An Italian-language report with a customisable cover and a single-line diagram is important.
- Meridiana (analysis): generate the report from the same structured result model (HTML to PDF), with "compare variants" diff highlighting as PVsyst does, and include an assumptions/sources table per loss, which PVsyst lacks.

##### 1.1.15.3 Loss diagram

Sources: https://www.pvsyst.com/help/project-design/results/loss-diagram.html, https://www.pvsyst.com/help/project-design/array-and-system-losses/index.html, https://www.pvsyst.com/help/project-design/results/simulation-variables-meteo-and-irradiations.html, https://www.pvsyst.com/help/project-design/results/simulation-variables-grid-system.html, https://www.pvsyst.com/help/physical-models-used/grid-inverter/subhourly-clipping-correction.html

- **What it is:**
  - An arrow diagram of the energy balance. It is **always** in the report for the full year, and available **per month** under *Detailed results > Predefined graphs*.
  - Each loss is a % **of the preceding energy**, so percentages are not additive.
  - In stand-alone systems it shows how much energy passes through the battery.
  - PVsyst admits some contributions cannot be isolated rigorously (for example ohmic loss in stand-alone systems), but the energies at the main steps are correct.
- **Entries for a grid system** (reconstructed from the variable pages and the loss-order list; the drawing itself is an image):

| Block | Entries (variable) |
|---|---|
| Irradiance | GlobHor → transposition (GlobInc) → far shadings/horizon (GlobHrz) → near shadings, irradiance loss (GlobShd) → IAM (GlobIAM) → soiling (GlobSlg) → **GlobEff**. Bifacial: ground and rear-side items (GlobGnd, ReflLss, BkVFLss, DifSBak, BmIncBk, BackShd, GlobBak, ReflFrt) |
| PV array | **EArrNom** (array nominal energy at STC efficiency) → irradiance level (GIncLss) → temperature (TempLss) → spectral (SpctCor) → light soaking (LigSoak) → electrical shading (ShdElec) → module quality (ModQual) → LID (LIDLoss) → degradation and evolutive mismatch (if ageing) → mismatch (MisLoss) → optimizers (OP_*) → DC ohmic (OhmLoss) → **EArrMPP** |
| Inverter | IL_Oper (efficiency), IL_Pmax (over nominal power, incl. sub-hourly clipping ILPmxSH), IL_Pmin (threshold), IL_Vmax, IL_Vmin (MPP window), IL_Night → **EOutInv**; grid limitation (EGrdLim) as a separate loss when chosen |
| After inverter | Auxiliaries (Aux_Lss), AC ohmic (EacOhmL), external transformer (ETrfLss), unavailability (UnavLss) → **E_Grid** (and E_Solar/E_User with self-consumption) |

- **Export:** loss-diagram units, decimals and DPI can be set (release notes 6.79, 7.0.1); values can be exported to Excel.
- IT: the loss diagram is what Italian reviewers check first in a PVsyst report, for example near shading on rooftops, overload clipping or IAM. That this is reviewers' habit is analysis, not PVsyst text.
- Meridiana (analysis): make the diagram interactive (click an arrow to open the parameter or the hourly series behind it) and show absolute kWh next to the %. This removes the non-additivity confusion PVsyst warns about.

##### 1.1.15.4 Performance ratio (PR, PR_Bifi, temperature-corrected PR)

Source: https://www.pvsyst.com/help/project-design/results/performance-ratio-pr.html

- **Definition (IEC EN 61724):** PR = energy effectively produced / (GlobInc × P_nom,PV), with P_nom,PV the STC nameplate.

| System | Energy in the numerator |
|---|---|
| Grid | E_Grid |
| Grid with self-consumption and/or storage | E_Grid + E_Solar |
| Stand-alone | E_User − E_BackUp |
| Pumping | E_PmpOp |

- **Interpretation:**
  - PR includes optical, array and system losses and is independent of module efficiency.
  - Trackers with backtracking have a higher PR than without.
  - Raising albedo raises GlobInc, which lowers PR for the same production: far albedo is only seen by the first row, with a shading factor of (n−1)/n.
  - With storage, time-step PR can exceed 1, so it should be aggregated.
- **Bifacial PR:**
  - PR_Bifi = E / ((GlobInc + φ·(GlobBak + BackShd))·P_nom), following IEC 61724-1 Ed. 2 (2021).
  - φ (bifaciality) is included **since 8.0.12**. GlobBak + BackShd approximates what a rear sensor measures.
  - Shown separately in the results and the report; always lower than PR. With mixed mono- and bifacial sub-arrays a system-level φ is used.
- **Weather-corrected (temperature) PR:**
  - PR_Temp = E_Grid / (P_nom·Σ[GlobInc/G_ref·(1 + μ_Pmpp·(T_array − T_array,weighted))]), with T_array,weighted (TArrWtd) the GlobInc-weighted yearly mean (NREL/TP-5200-57991; IEC 61724-1).
  - Implemented in 6.74. PVsyst finds it over-corrects sheds and is almost unusable for trackers, so it only appears in the report on request.
- IT: PR is the usual contractual KPI in EPC contracts; PVsyst itself says it "is often used as a contractual guarantee". Meridiana must compute PR, PR_Bifi and PR_Temp exactly as defined here.

##### 1.1.15.5 PR as a performance guarantee

Source: https://www.pvsyst.com/help/project-design/results/pr-warranty.html

- **Forecast versus measured:**
  - PVsyst's PR is referenced to GlobInc **before** horizon loss. Measured PR = EGrid_meas/(GlobP_meas·PNomPV).
  - Irradiance sources: satellite data (10–20 % hourly accuracy), a horizontal pyranometer plus transposition ("a better solution"), or a POA pyranometer, which avoids transposition. It must be unshaded and not mask the albedo, for example on top of the first shed.
  - Rear-side measurement has no consensus. Ambient temperature (or module temperature) must also be measured.
- **Accuracy:** a good pyranometer gives 1–2 %; transposition is under 1 % monthly.
  - Importing measured POA reconstructs GlobHor and DiffHor for the shading calculations.
- **Two comparison methods:** keep the guaranteed PR and correct the measurements; or **re-simulate with measured weather** and compare E_Grid. The second is more flexible with faults.
- **Corrections:**
  - Horizon: compare with a forecast PR based on GlobHrz when irradiance is measured on site.
  - Tracker-axis sensors: add the diffuse and albedo shading losses ShdDLss + ShdALss, exported from the simulation, back to the measured series.
  - Ageing: use a degressive guaranteed PR.
  - P50/P90: PR does not depend on the weather year.
- IT: directly applicable to Italian commissioning and acceptance tests and to EPC PR guarantees. Meridiana (analysis) can turn this page into a "guarantee test" workflow: import monitoring data, re-simulate, apply corrections, produce a test report.

##### 1.1.15.6 Normalised performance index (IEC 61724) and specific production

Sources: https://www.pvsyst.com/help/project-design/results/normalised-performance-index.html, https://www.pvsyst.com/help/project-design/results/simulation-variables-grid-system.html, https://www.pvsyst.com/help/project-design/results/simulation-variables-stand-alone-system.html

- **Yields and losses** (kWh/kWp/day):

| Quantity | Meaning |
|---|---|
| Yr | Reference yield = GlobInc in kWh/m²/day |
| Ya | Array yield |
| Yf | System yield |
| Lc = Yr − Ya | Collection (array) loss |
| Ls = Ya − Yf | System loss |
| PR = Yf/Yr | Performance ratio |
| Lu (stand-alone and limited-load systems) | Unused energy, with Ya = Yr − Lu − Lc |
| Yu, Lur, Lcr, Lsr (stand-alone variables page; Yu and Lu also for DC-grid) | Potential yield and loss ratios to incident energy |

- **Specific production** (kWh/kWp/year) on the main results page is the yearly Yf.
- **Unit remark:** kWh/m² of light and kWh/kWp of electricity are numerically equal by the STC definition.
- IT: specific production (kWh/kWp) is the headline figure in Italian residential offers. Yr, Ya and Yf graphs are standard in reports.

##### 1.1.15.7 Distributions, histograms, typical power distributions

Sources: https://www.pvsyst.com/help/project-design/results/distributions-histograms.html, https://www.pvsyst.com/help/project-design/results/typical-power-distributions.html

- **Histograms:**
  - Energy accumulated per power bin (for example a 590–600 kW bin).
  - Operating time per power bin.
  - **Cumulative distribution**: energy above each power. Example: 54 % of yearly energy above 600 kW for a 1.126 MWp / 1 MWac system.
- **Typical distributions** (Marseille 43.5° and Dakar; sheds 20°, domes, horizontal-axis trackers):
  - STC power is never reached; peak output is about 900 kW for 1.126 MWp.
  - Domes/sheds yield ratio is 84.9 % in Marseille and 94.6 % in Dakar. Tracking gain is 12.4 % and 14.2 %.
  - PVsyst's general rule: **DC:AC (PNom ratio) of 1.25–1.3** to avoid overload losses, nearly independent of system type and climate.
- IT: the Marseille case is climatically close to much of Italy. The power histogram is the right tool to justify DC:AC choices and grid-limitation sizing (power limits at the injection point).

##### 1.1.15.8 Simulation variables (main names)

Sources (under https://www.pvsyst.com/help/project-design/results/): simulation-variables-meteo-and-irradiations.html, simulation-variables-geometry.html, simulation-variables-grid-system.html, simulation-variables-stand-alone-system.html, simulation-variables-dc-grid-systems.html, simulation-variables-pumping-systems.html

- **Weather:**
  - GlobHor; DiffHor (capped to GlobHor); BeamHor; Tamb.
  - WindVel: if absent, the monthly value or a default of 1.5 m/s.
  - GlobHorCS and DiffHorCS (clear sky, Kasten 1996).
- **Transposition:**
  - GlobInc, BeamInc, DiffAInc (diffuse including albedo), DiffSInc (sky diffuse), AlbInc.
  - Ratios Bm/Gl, Diff/Gl, DifS/Gl, Alb/Gl.
- **Optical chain:**
  - GlobHrz, GlobShd, GlobIAM, GlobSlg, GlobEff, DiffEff.
  - Factors FTransp, FHrzBm, FHrzGl, FShdBm, FShdGl, FIAMBm, FIAMGl, FSlgBm, FSlgGl (diffuse and albedo factors are constant).
- **Bifacial:** GlobGnd, ReflLss, BkVFLss, BackShd, DifSBak, BmIncBk, BmSFBak, BeamBak, GlobBak, ReflFrt.
- **Array virtual energies:**
  - EArrRef = GlobInc × PNom nameplate, for PR; not in the report.
  - EArrNom = GlobEff × model Pmpp(STC), the start of the loss diagram.
- **Array losses and temperatures:**
  - GIncLss, TempLss, SpctCor, ModQual, MisLoss, OhmLoss, EArrMPP.
  - Tarray, DTArr, DTArrGl, TExtON (with TArrSS and TArray for the thermal model).
- **Geometry:** these are instantaneous values at mid-interval (hour + 30 min + time shift), and are not aggregated.
  - Sun: HSol, AzSol.
  - Incidence and profile angles: AngInc, AngProf.
  - Plane and tracker angles: PlTilt, PlAzimt, PhiAng, PhiInFr.
- **Grid system:**
  - Array: PNomArray, EArrRef, EArrNom, GIncLoss, TempLoss, SpctCor, LigSoak, ShdElec, ModQual, LIDLoss, MisLoss, OP_Oper/Pmin/Pmax/Vmin/Vmax, OhmLoss, EArrMPP, EArray, IArray, UArray.
  - Inverter: InvLoss, IL_Oper, IL_Pmin, IL_Pmax, IL_Vmin, IL_Vmax, IL_Night, Syst_ON, EOutInv.
  - After the inverter: Aux_Lss, EacOhmL, ETrfLss, UnavLss, E_Solar, E_User, E_Avail, E_Grid, EApGrid and ERegrid (when a power factor is defined), EGrdLim, SolFrac.
  - Efficiencies: EffArrR, EffArrC, EffSyR, EffSyC, EffInvB, EffInvR.
  - Normalised indices: Yr, Ya, Yf, Lc, Ls, PR.
- **Stand-alone:**
  - EArrMPP, EArUfix, EUnused, MPPLoss, EArray; converter losses CL_*.
  - Battery: EBatCh, EBatDis, ESOCBal, SOC (internal and "indicated"), EBatLss with IBEffL/IBGass/IBSelf, SOHBatt, AgeBatEff, NBatCyc, MGass.
  - Back-up: E_BkUp, FuelBU.
  - E_Avail, E_Load, E_User, E_Solar, SolFrac, E_Miss, T_LOL, Pr_LOL; normalised indices including Lu.
- **DC-grid:** EArrMPP, EArUfix, MPPLoss, EUnused, EArray, Esupply, LigLoss, E Avail, E Load, E User, SolFrac, U User.
- **Pumping** (configuration-dependent):
  - EPStart, EPmpThr, EPmpOvr, EPmpAv, ELowLev, ETkFull, EPmpOp.
  - Converter losses CL_*; battery-buffered variables.
  - Hydraulics: E_Hydro, P_Effic, H_Pump, H_Stat, H_Loss, H_DrawD, FlRate, WPumped, WStored, W_Used, W_Miss.
- Meridiana (analysis): adopting PVsyst-compatible variable names (or a documented mapping) makes Meridiana results directly comparable with PVsyst reports and exports, which Italian reviewers and banks will ask for.

#### 1.1.16 Economic evaluation (project design)

The evaluation is opened from the Project dialog after simulation and uses the simulated energy.

**Installation costs**
- Components (modules, inverters, batteries, pumps, controllers, generators; quantities filled automatically; optimizers included since 8.0.13).
- Studies, administration and fees: grid connection, bank, permits, taxes.
- Insurance, land, and "substitution credit and subsidies".
- Each item is costed "globally, by pieces, by installed Wc or by m²".
- **Depreciation** per asset: none, straight-line or declining balance, with salvage value and period.
- Cost lists can be saved and loaded as templates.

**Operating costs**
- Items: inspection, cleaning, insurance; for stand-alone also maintenance, fuel and battery replacement; for pumping also pump replacement.
- Scheduled every year, over a year range, or in specific years (since 8.1.5).
- **Replacement provisions** for inverters, batteries and pumps are computed from cost and lifetime.

**Currency**
- Any currency, with exchange rates that can be edited or downloaded.

**Financial parameters**
- Lifetime and start date.
- **Inflation** on running costs.
- **Discount rate**, used for LCOE and NPV.
- Module degradation: a linear rate, or taken from the ageing tool.
- **Income tax**, with a second rate allowed.
- Dividends.
- Financing from own funds, **subsidies** and up to **three loans**: fixed annuity, fixed amortisation, or interest-only bullet ("in-fine").

**Tariffs**
- **Fixed feed-in tariff** with contract duration, annual connection tax, progressive change and a post-contract change.
- **Peak and off-peak** rates, different in summer and winter.
- **Custom hourly or daily rates from CSV**.

**Self-consumption**
- A consumption tariff values self-consumed energy and can rise each year.
- A separate sale tariff applies to the surplus. Rates can vary by hour.
- The load must be stored at the time-step level.
- DST dates are needed only for hourly tariffs.
- Net metering is not described in the economic-evaluation pages. The self-consumption page mentions it only as a single-meter arrangement (see 1.1.12.1).

**Outputs**
- **LCOE**, **NPV**, **IRR**, **ROI**, **payback** ("undefined" if unprofitable).
- Annual and cumulative **cash-flow table**.
- Financial pages in the report (CLI report pages `econeval` and `financialbalance`).

URLs:
- https://www.pvsyst.com/help/project-design/economic-evaluation/index.html
- https://www.pvsyst.com/help/project-design/economic-evaluation/installation-and-operating-costs.html
- https://www.pvsyst.com/help/project-design/economic-evaluation/financial-parameters.html
- https://www.pvsyst.com/help/project-design/economic-evaluation/feed-in-tariff-and-self-consumption/index.html
- https://www.pvsyst.com/help/project-design/economic-evaluation/financial-results.html

**IT relevance: High** for client proposals, especially rooftop self-consumption.
- PVsyst documents only generic mechanisms. Italian schemes would have to be approximated with tariffs, CSV prices and subsidies. Examples are dedicated withdrawal, CER/collective self-consumption incentives and tax deductions; whether PVsyst models any of them explicitly is [unverified; not found in the help].
- VAT is not covered.

#### 1.1.17 P50-P90 evaluation

**Method**
- Annual yield is assumed **Gaussian**, centred on the simulation result.
- Independent uncertainties are combined **in quadrature** into σ. P90 is about **1.28 σ** below the mean.
- Generic P_xx values are also available.

**Inputs**
- Kind of weather data: monthly averages or TMY are treated as P50. A specific year or own measurements need a deviation from the long-term mean.
- **Weather annual variability**: from Meteonorm, from the TMY file, user-entered, or the default model (see 1.6.9).
- Model uncertainties: PV module model and parameters (the largest after weather), inverter (negligible), soiling and module quality, custom items.
- **Mean energy shift**, formerly "Climate change"; normally 0.

**Limits**
- Not available for stand-alone or pumping systems.
- No long-term bias of the data source is included; PVsyst advises comparing providers.
- Annual values only. Monthly values need 15 years or more; hourly "P90 series" made by scaling are wrong.
- Degradation is "not compatible" with the concept.

**Outputs**: a Gaussian or cumulative distribution plot, and P50/P90 on the report (`p50p90` page).

URL: https://www.pvsyst.com/help/project-design/p50-p90-evaluations.html

**IT relevance: High** for multi-MW, bank-financed plants. Medium for rooftops.

#### 1.1.18 Carbon balance tool

**Inputs**
- Annual E_Grid from the simulation, with degradation (default 1 %/yr).
- Lifetime.
- **Grid LCE**, chosen as:
  - Manual;
  - Country IEA (2010 values);
  - **Energy Mix**: 11 generation types with IPCC SRREN 2011 Annex II median factors and shares. Defaults exist "for several European countries" from Itten, Frischknecht and Stucki 2013 (PSI/ESU).
- **PV system LCE**, chosen as:
  - Manual;
  - Default (IPCC median 46 gCO₂/kWh);
  - **Detailed**: modules by technology per m², Wp or kWp, two transport legs in gCO₂/t·km, supports (steel, per kg), concrete, inverters (per unit), copper cabling, aluminium, maintenance, dismantling, other.

**Method**: avoided grid CO₂ minus PV life-cycle emissions.

**Outputs**: tCO₂ saved over the lifetime and per year, per kWp, and per kWp per year.

URLs:
- https://www.pvsyst.com/help/project-design/carbon-balance-tool/index.html
- https://www.pvsyst.com/help/project-design/carbon-balance-tool/detailed-system-lce.html
- https://www.pvsyst.com/help/project-design/carbon-balance-tool/grid-energy-mix.html

**IT relevance: Medium.** Used in ESG and permitting narratives. Whether Italy has a default energy-mix entry is [unverified].

#### 1.1.19 Import time-series parameters (shared CSV form)

**Parameters that accept a CSV time series**
- Load (user's needs).
- **Custom feed-in tariff**.
- **Grid power limitation** threshold (8.1.0).
- Grid storage **power shifting** charge and discharge, and grid unavailability or islanding.
- **Soiling** fraction (8.1.0).
- **Ground albedo** (8.1.2).
- **System unavailability** (8.1.6).

**Format**
- CSV with commas or semicolons, using a single separator type.
- `#` lines are comments.
- One header row, then one units row.
- Date and time in one column.
- A full year with a **regular step and no gaps**, hourly or sub-hourly (e.g. 15 min). The year is ignored.
- **ANSI** encoding.

URLs: https://www.pvsyst.com/help/project-design/Import-time-series-parameters.html, https://www.pvsyst.com/help/release-notes/index.html

**IT relevance: High.**
- Export limitation profiles and curtailment, for example a DSO-imposed limit [inference].
- Monthly or seasonal soiling.
- Time-of-use prices, for example hourly zonal prices for energy sales [inference].

#### 1.1.20 Batch / parametric simulation, optimisation tool, output files, PVsystCLI

**Batch mode (GUI)**
- Steps:
  1. Choose the input and output CSV files.
  2. Choose the parameters to vary.
  3. Choose the yearly result variables ("any simulation variable").
  4. Edit `MyProject_BatchParams_i.CSV` in Excel, one row per run.
  5. Run. PVsyst writes `MyProject_BatchResults_i.CSV`.
- Parameters that can be varied:
  - weather file per run (each year of a series);
  - **location**: the nearest weather file is used, or synthetic data is generated with the Meteonorm DLL;
  - base VCi;
  - saving the VCi and hourly files;
  - **tilt and azimuth** (one fixed orientation only);
  - unlimited sheds pitch and electrical effect;
  - 3D sheds pitch and width;
  - tracker pitch, backtracking and stroke;
  - **module type, modules in series, strings, module quality loss**;
  - **inverter type and number**.
- PVsyst says further parameters can be requested.
- Limits: a single fixed orientation; yearly results only; fixed file names; the CSV must be closed before running.
- Release notes: sub-hourly batch from 8.1.4; storage batch crash fixed in 8.0.10.

**Sheds optimisation tool**
- Runs "a full simulation for each of the parameter settings" for 3D shed fields.
- Graphs of variables against the scanned parameters. Two tabs: create scan and view scans.

**Output files**
- Results are stored in `.VCi`.
- "Output file" exports any variable at the simulation step, daily or monthly to `UserHourly`.
- Semicolon separator, dot or comma decimal, MM/DD/YY or DD/MM/YY dates.
- The option must be re-enabled before each run.
- Since 8.1.5, clear-sky GHI and DHI can be exported.

**PVsystCLI (since 8.0.0)**
- Command: `PVsystCLI.exe <command>`. Commands:
  - `run-simulation`: workspace, project, variant; `--time-step hour|subhour`; `--site` with optional `--synthetic-weatherdata-generation`; `--input-met-file`; `--batch-params-file`; `--batch-rvt-file`; `--output-csv-file`; `--start-date` and `--end-date`; `--report-pdf-file`; `--report-pages` (cover, summary, notes, params, horizon, shadings, usersneeds, results, econeval, circuit, losses, financialbalance, p50p90, carbonbalance, predefgraphs); `--report-language` with 12 languages **including `it`**; `--recompute-shadingfactors-tables`;
  - `convert-meteo`: CSV + MEF + SIT → MET, with a time shift of ±30;
  - `create-site`: name, latitude, longitude, monthly CSV with `GlobH` and `Temp` required plus `DiffH`, `WindVel`, `Linke`, `RelHum`; altitude, time zone and country auto-retrieved; albedo;
  - licence commands (`lic-activate`, `lic-sync`, `lic-deactivate`, `lic-info`), `version`, `export-logs`;
  - an options file with `name:value` lines.
- **Licensing**: needs an "active subscription". Trial of 60 days and 250 calls, counting `convert-meteo` and `run-simulation`. One machine per licence. Whether it is included in a GUI licence is not stated.

URLs:
- https://www.pvsyst.com/help/project-design/simulation/index.html
- https://www.pvsyst.com/help/project-design/simulation/batch-mode-parametric-studies.html
- https://www.pvsyst.com/help/project-design/simulation/optimization-tool/index.html
- https://www.pvsyst.com/help/project-design/simulation/create-a-csv-file-of-hourly-daily-values.html
- https://www.pvsyst.com/help/pvsyst-cli.html
- https://www.pvsyst.com/help-cli/
- https://www.pvsyst.com/help-cli/reference/index.html
- https://www.pvsyst.com/help-cli/licensing/index.html

**IT relevance: Medium-High.**
- For multi-MW layout optimisation (pitch, tilt, DC/AC ratio).
- For offices that standardise reports. The Italian report language is available.

### 1.2 Project design: stand-alone systems

**System classes described**
- Solar home systems, about 50-200 Wp: modules connected directly to the battery (36 or 72 cells).
- Medium systems, about 400 Wp-4 kWp: MPPT controller; DC loads, or AC loads through a small inverter.
- High-power systems, about 2 kWp to tens of kWp: MPPT solar chargers plus DC/AC battery inverters.
- **PVsyst does not model the stand-alone (battery) inverter.** Loads are entered as energy, and the needs must be raised to cover inverter losses.

**Procedure**
1. Orientation. Several sub-arrays and orientations are allowed since 8.0.0.
2. Needs.
3. Pre-sizing: autonomy (typically about 4 days), P_LOL, battery voltage.
4. Battery choice; the series/parallel layout is proposed.
5. Array and control strategy: direct coupling, MPPT or DC-DC. The universal controller is suggested first.
6. Diesel genset with its charging power.
7. Detailed losses.
8. Simulate. Large unused energy means the array is oversized; large loss of load means it is undersized. Reduce the battery until both rise.

**Simulation**
- A current balance at the battery terminals, iterated until it closes.
- Battery voltage is a function of SOC, temperature and current.
- Regulation states use hysteresis. Threshold crossings inside a step are timed exactly and the step is split.
- With several sub-arrays, each has its own controller and a battery share proportional to its PNom (an approximation).
- Main result: **ESolar**. Also PLOL, unused energy and the loss diagram; `T_LOL` is recorded since 8.0.6.
- Demand-side management is suggested to increase direct use.
- Sub-hourly stand-alone simulation is available since 8.1.0.

URLs:
- https://www.pvsyst.com/help/project-design/stand-alone-systems-definition/index.html
- https://www.pvsyst.com/help/project-design/stand-alone-systems-definition/stand-alone-system-procedure.html
- https://www.pvsyst.com/help/project-design/simulation/simulation-process-stand-alone-system.html

**IT relevance: Low.** Off-grid sites in Italy are few: mountain huts, telecom, agriculture. This is phase 3.

### 1.3 Project design: pumping systems

**Hydraulic layouts**
- Deep well to storage tank.
- Lake or river to storage tank.
- Pumping into a pressurised tank.
- Only **one sub-array**, but tracking is allowed.
- Grid-fed "conventional" pumping is not modelled; it is just a load.
- A pumping system cannot be linked to another PV system.

**Hydraulics**
- Static level HS, which can be a monthly profile.
- Pumping test values Qref and HDref.
- **Drawdown model**: the borehole is an "impervious tube" with diffusive refill, so drawdown is linear in flow at steady state. Specific drawdown HDref/Qref, with examples from 0.2 to 4.8 m per m³/h.
- **Hmax** is the stop level against dry running.
- Piping circuit, plus **friction loss factors** for fittings (e.g. standard 90° elbow 0.75, open gate valve 0.17).
- Water needs in m³/day (yearly, seasonal or monthly); tank volume.

**Configurations**
- Direct coupling (DC pumps).
- Direct coupling plus a **booster** (starting current).
- **Cascading** of several pumps.
- **Array reconfiguration** (series and parallel relays).
- **MPPT** or **fixed-voltage DC-DC converter**.
- AC pumps with an inverter.
- **Battery-buffered**.
- Pumps can be connected in parallel or series.

**Simulation**
- An hourly operating point found iteratively, because head depends on flow.
- Tank balance with constant user draw. The pump stops when the tank is full; needs go unmet when it is empty.
- Unused energy categories: below threshold, before flow starts, pump stopped.
- Outputs: water delivered, missing water, unused energy, PR and loss diagram, and the cost per m³ when economics are given.
- 8.0.0 adds a warning when the pump controller does not match the array voltage.

**Pre-sizing rules of thumb**
- About 6 h of equivalent full operation per good day.
- Pump efficiency about 50 % for positive displacement, 35-40 % for centrifugal.
- PV power about 20-30 % above the pump's nominal power.

URLs:
- https://www.pvsyst.com/help/project-design/pumping-systems/index.html
- https://www.pvsyst.com/help/project-design/pumping-systems/pumping-system-procedure/index.html
- https://www.pvsyst.com/help/project-design/pumping-systems/pumping-system-procedure/pumping-borehole-modelling.html
- https://www.pvsyst.com/help/project-design/pumping-systems/pumping-system-procedure/friction-loss-factors.html
- https://www.pvsyst.com/help/project-design/pumping-systems/pumping-system-configuration/index.html
- https://www.pvsyst.com/help/project-design/pumping-systems/pumping-system-sizing.html
- https://www.pvsyst.com/help/project-design/pumping-systems/pumping-results-examples.html
- https://www.pvsyst.com/help/project-design/simulation/simulation-process-pumping-system.html

**IT relevance: Low** (agricultural irrigation niche). This is phase 3.

### 1.4 Project design: DC-grid systems

**What it is**
- PV feeding public-transport DC networks in the "600 - 1500V range" directly, with no power conditioning.
- "very heavy safety disconnector devices" are needed.

**Inputs**
- Nominal power, line voltage and maximum grid voltage.
- **Line resistance** from PV to user, and from the conventional supply to user when a load is defined.
- Overvoltage regulation behaviour.
- Module choice. Series and parallel counts are proposed, but the program "cannot determine the exact optimum".
- Optional load, usually a probability profile.

**Simulation**
- Unlimited load: fixed nominal voltage.
- Defined load: a current balance at the user. When PV covers the demand, the line voltage follows the array I/V curve towards Voc, and overvoltage regulation applies.

URLs:
- https://www.pvsyst.com/help/project-design/dc-grid-system-definition/index.html
- https://www.pvsyst.com/help/project-design/simulation/simulation-process-dc-grid-system.html

**IT relevance: Low** (tram or metro feeders only). This is phase 3, or can be skipped.

### 1.5 Preliminary design (pre-sizing)

**Common workflow**
- Three buttons: *Location*, *System*, *Results*.
- Pre-sizing projects "do not support multiple variants".
- The site comes from the database, or is created or imported from Meteonorm or US TMY data. A horizon is optional.
- Evaluations are monthly, use "few general characteristics", and need no specific components. A rough cost estimate is included.
- URL: https://www.pvsyst.com/help/preliminary-design/index.html

| Function | Inputs | Model / algorithm | Outputs and limits | IT relevance |
|---|---|---|---|---|
| **Grid-connected pre-sizing** | Orientation, with an optimisation tool. Sizing anchor: active area, nominal power, or annual energy. Module type: Standard, "translucent custom" (cell spacing, filling ratio) or not defined. Technology, which sets a default efficiency. Mounting disposition, which is "not used in calculations". Ventilation, which slightly changes module temperature. | Plane irradiance from the Monthly Meteo algorithms; a "constant efficiency" plus correction coefficients, editable as hidden parameters. | Pnom, area, annual yield, graphs and tables, report, economic sheet. Accuracy "of the order of 10 - 20%", worst for façades. "mainly intended for architects". | Low-Medium. Early feasibility only. Italian designers use PVGIS for the same job. |
| **Stand-alone pre-sizing** | Orientation, optimised for winter. Appliances. Autonomy in days. Accepted P_LOL. System or battery voltage. | Monthly Meteo. A 365-day synthetic daily sequence from Collares-Pereira / Aguiar et al. (1988) Markov matrices, renormalised to monthly sums. A daily battery balance split into morning, day and evening. | Array STC power and battery capacity. Graphs of available energy against needs, battery SOC and monthly P_LOL. Monthly table including back-up energy. Rough cost. Accuracy about 10-20%. | Low. Niche uses only, such as mountain huts and off-grid farms. |
| **Pumping pre-sizing** | Water needs (yearly, seasonal or monthly). Nominal head. Optional pipe diameter and length. Pump technology (centrifugal or positive displacement). Array-pump coupling strategy. Tank volume or autonomy. P_LOL. | A "very simplified simulation" with daily values and the same Aguiar (1988) synthetic daily sequence, iterated over array and pump size until P_LOL is met. | Pump power, PV power, rough investment and cost of water, graphs, monthly table. | Low. Agricultural niche. |
| **Pre-sizing economics** | Default costs, editable via "Edit costs". | Mounting and maintenance cost = (Pnom / 5 kWp)^0.8 × base cost. Module and inverter costs scale with quantity. | Rough cost only. Assumptions vary by country. | Low. |

URLs:
- https://www.pvsyst.com/help/preliminary-design/grid-system-presizing/index.html
- https://www.pvsyst.com/help/preliminary-design/grid-system-presizing/grid-connected-system-preliminary-design.html
- https://www.pvsyst.com/help/preliminary-design/stand-alone-system-presizing/index.html
- https://www.pvsyst.com/help/preliminary-design/stand-alone-system-presizing/stand-alone-system-preliminary-design.html
- https://www.pvsyst.com/help/preliminary-design/pumping-system-preliminary-design.html
- https://www.pvsyst.com/help/preliminary-design/preliminary-design-economic-evaluation.html

### 1.6 Databases: weather data (meteo database)

Weather data is described as the starting point of a project and its main source of uncertainty. It is reached from `Databases` on the start page.
URL: https://www.pvsyst.com/help/meteo-database/index.html

#### 1.6.1 Data model: sites (.SIT) and weather files (.MET)

**.SIT (site, monthly data)**
- Required: name, country, region, latitude, longitude, altitude, time zone, monthly GHI, monthly mean temperature, data source.
- Optional: monthly DHI, wind, relative humidity, Linke turbidity.
- Manually entered monthly data should "never include horizon shading".
- In site lists, white rows are PVsyst sites, grey rows are user sites and green rows are favourites. Only user sites can be deleted, and they go to `UserRecycleBin`.

**.MET (hourly or sub-hourly series)**
- Covers up to one year. "Timestamps mark the start of each interval".
- Four kinds: TMY (imported or generated), Synthetic (from monthly data), Time series (one specific year), Imported (custom import).
- Required variables: `GlobHor`, `DiffHor`, `T_Amb`.
- Optional variables: `GIPMeas` (measured POA), `BeamNor`, `BeamHor`, `WindVel`, `TArrMes`, `PrecWat`, `RelHum`, `Linke`, `AoD`, `Albedo`, `T_DewPt`.

**.MEF**: a reusable column-mapping (format) file for custom imports.

URLs: https://www.pvsyst.com/help/meteo-database/index.html, https://www.pvsyst.com/help/meteo-database/geographical-sites/index.html

**IT relevance: High.** This is the data model every simulation rests on.

#### 1.6.2 Sources queried directly at site creation

| Source | What PVsyst gets | Cost and conditions |
|---|---|---|
| **Meteonorm** (embedded DLL) | Monthly values into .SIT, plus a synthetic hourly or 1-minute .MET. | Built in. Version mapping: 8.0 = Meteonorm 8.2; 8.1.0-8.1.4 = 9.0; 8.1.5+ = 9.0.10. Since 8.1.0 the Meteonorm horizon import uses the local V9 DLL with no internet. |
| **PVGIS TMY** (API) | Hourly TMY into .MET, with monthly averages into .SIT. | Free. Versions 5.3 and 5.2 offered; 5.1 deprecated. Since 8.0.7 PVGIS 5.3 is the default for TMY, time series and horizon import. |
| **NSRDB TMY** (API, NREL, renamed NLR in 8.1.5) | Hourly TMY. | Free. 8.1.5 added MSG and Polar resources for Europe, Africa and above 60°N. |
| **Solcast TMY (P50)** (API) | Hourly TMY. | Paid. Since 8.0.5, TMY is no longer available on free accounts. |
| **SolarAnywhere TGY** (API) | Hourly TGY. Since 8.0.12, choice of the "latest" or the 2023 TGY. | Paid. |
| **Solargis TMY** (API) | Hourly TMY. | Paid. |
| **NASA POWER** (API) | Monthly averages only (GHI, temperature, diffuse, wind, RH). Grid 0.5°×0.5°, typical period 2001-2020. | Free. Replaced NASA-SSE (1°, 1983-2005) in 8.1.0. |
| **ANE-NEDO** (web API, since 8.1.4) | Hourly statistical averages for Japan. | - |

- The help does not mention API-key entry [unverified how paid accounts are authenticated].
- Interactive map: since 8.0.10 Azure Maps replaced Bing. OpenStreetMap has been selectable since 8.0.0.

URLs:
- https://www.pvsyst.com/help/meteo-database/geographical-sites/import-tmy-data-from-apis.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/nasa-satellite-data/index.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/nsrdb-by-nlr/index.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/solcast-data/index.html
- https://www.pvsyst.com/help/meteo-database/synthetic-data-generation/synthetic-data-model.html
- https://www.pvsyst.com/help/release-notes/index.html

**IT relevance: High.**
- PVGIS (SARAH-based for Europe) and Meteonorm are the usual free or built-in references for Italy.
- Paid TMYs (Solargis, Solcast, SolarAnywhere) matter for bankable multi-MW projects.
- Whether PVsyst exposes PVGIS-SARAH3 by name: [unverified].

#### 1.6.3 "Known format" file imports

| Provider | Access and file | Data | Coverage as stated |
|---|---|---|---|
| Meteonorm program files | `xxxxMON.DAT` creates a .SIT; `xxxxHOUR.DAT` in "PVsyst output format" creates a .MET | Monthly and hourly | Worldwide |
| PVGIS-SARAH2 / -NSRDB / -ERA5 | Fetched online, "requires internet access" | Hourly TMY | SARAH2: Europe, Africa, Asia, S. America, 2005-2020. NSRDB: Americas. ERA5: worldwide. |
| NSRDB | SAM CSV files from the NSRDB viewer, plus the API. Legacy TMY2 and TMY3 files are accepted. | TMY and series; series at 15, 30 or 60 min | Mostly Americas, extended worldwide |
| Solargis | CSV in PVsyst format ("climData", hourly) and monthly "Prospect" files | Sub-hourly, hourly, monthly | Worldwide, 1994 to today |
| Solcast | TMY at site creation, plus CSV files; monthly values by copy/paste | Sub-hourly, hourly | Worldwide, 2007 to today |
| SolarAnywhere | TGY via API, .PXX files (direct since 8.0.0), horizon import (8.0.0) | Sub-hourly, hourly | 1998 to today |
| Vaisala / 3TIER | CSV | Sub-hourly, hourly | Worldwide, 1996 to today |
| SoDa HelioClim-3 | File in PVsyst format | Hourly | Europe and Africa, 2004 to today |
| 3E | CSV in PVsyst format | Sub-hourly, hourly | Worldwide |
| Vortex Solar | CSV | Hourly | Worldwide, 1997 to today |
| Reuniwatt | CSV; monthly by copy/paste | Hourly | Worldwide, 2004 to today |
| ASHRAE IWEC2 | TMY3 files | Hourly | US and Canada |
| Canadian EPW | EPW files | Hourly | As listed |
| Explorador Solar | SAM CSV | Hourly | Chile |
| ANE-NEDO | Web API | Hourly | Japan |
| SolarProspector | Decommissioned, but old files are still processed | Hourly | USA |
| Satellight, WRDC, STRÅNG | Sub-pages exist, but no details are given on the index | - | [unverified] |

The index page is partly outdated: it still lists NASA-SSE, although 8.1.0 switched to NASA POWER.

**PVGIS page**
- It also describes the legacy PVGIS-classic and CM-SAF datasets.
- It notes a PVGIS 5.2 coastal issue: zero temperature, wind or humidity can trigger "monthly average temperature is not defined for this site".

**Solargis page**
- Hourly files exclude terrain far-shading unless requested. Monthly Prospect files include it.
- Circumsolar diffuse is inside DHI, so the data is consistent with Perez.

URLs:
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/index.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/importing-data-from-meteonorm-program.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/pvgis-meteorological-data.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/solargis-data/index.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/solaranywhere-data/index.html

**IT relevance: High** for PVGIS, Meteonorm, Solargis, Solcast and SoDa. **Low** for the American and Japanese sources.
- No Italian national climatic dataset is listed as a known format, for example UNI 10349 monthly tables. Such data would have to be typed or pasted as custom monthly values in a .SIT.
- Whether the EPW reader accepts non-Canadian EPW files: [unverified].

#### 1.6.4 Custom file import: the weather data import assistant (new in 8.1.0)

The assistant has four steps.

**1. Source file**
- Accepts .CSV or .TXT with one time step per line, hourly or sub-hourly.
- The separator is "automatically" detected.
- An existing .MEF can be applied, or a new one defined.

**2. Site**
- Pick a site from the database, place one on the interactive map, or type coordinates.
- "Get from coordinates" fills in name, country, region, altitude and time zone.
- "Get from name" fills in latitude and longitude.

**3. Format file (.MEF), in tabs**
- *General*: time step, header lines to skip, separator.
- *Date*:
  - date type: reference year (1990), sequential from a start date, or read from the file using a pattern such as `YYYY|MM|DD|hh` or `YY/MM/DD hh/mm`;
  - time base: legal time or UTC;
  - time shift and record time label;
  - daylight saving correction. PVsyst's internal data has no DST. Defaults: Europe, last Sunday of March to last Sunday of October at 01:00; US rules; or custom dates.
- *Variable mapping*: column and unit for each variable.
- *Variables*: power or energy for steps under one hour (power is averaged, energy is summed), and the solarimeter orientation for POA data.
- Every change triggers an automatic reconversion. The status passes through "Loading source file" → "Processing weather data" → "Post-processing data" → "Data generated".
- Quality result colour: **green** OK, **orange** warnings, **red** "not fit for simulation".

**4. Save**
- Saves the .MET to the database. "Import another custom file" keeps the same site and MEF.

**Rules**
- "only POA or GHI can be imported at the same time".
- GHI-only data gets DHI from a diffuse model.
- POA-only data is retro-transposed to GHI and DHI, which shading needs. 8.1.0 improved the accuracy of the Hay reverse transposition.
- Missing T_amb can be synthesised, but a measurement is recommended.
- Albedo is importable as a ratio, % or ‰.

**Related release notes**
- 8.1.0: new DHI-from-GHI model with sub-hourly coefficients.
- 8.1.5: multi-year CSVs are split into one .MET per calendar year; files with critical errors are no longer saved.
- 8.1.6: diffuse-model coefficients refitted to the new solar constant (an EUPVSEC 2026 paper); legacy import removed from the assistant.

URLs:
- https://www.pvsyst.com/help/meteo-database/custom-meteo-files/index.html
- https://www.pvsyst.com/help/meteo-database/custom-meteo-files/procedure.html
- https://www.pvsyst.com/help/release-notes/index.html

**IT relevance: High.** This is how measured data, SCADA exports and non-supported providers come in. The step design (auto-detection, live conversion, traffic-light QC) is a good UX model.

#### 1.6.5 Automatic quality control of imported data (8.1.0+)

Checks raise warnings. Only unit errors in the MEF stop the import.

| Test family | Rule as documented |
|---|---|
| Basic range (hourly and sub-hourly) | GHI > extraterrestrial normal irradiance (ETN) marks the hour invalid. Night GHI > 5 W/m² marks it invalid. Daytime GHI ≤ 0 prompts a check for missing data. DHI > GHI is flagged. T_amb > 60 °C is flagged. Wind > 35 m/s is flagged (often km/h or mph). Ratio variables (RH, Linke, AOD, albedo) must lie in [0,1]. |
| KTcs: clearness on the best clear days against a clear-day model | Fatal if > 1.2 or < 0.85. Warning if > 1.1 or < 0.93. |
| BSRN limits (sub-hourly only) | "Extremely rare limits" flags `flagERLGHI`, `flagERLDIF`, `flagERLDNI`. "Physically possible limits" flags `flagPPL*`, for example DNI > ETN. |
| K-index tests (mostly GHI > 50 W/m²) | `flagKnKt`: consistency of Kn against Kt. `flagKn`: DNI too high, relaxed at altitude. `flagKt`: Kt ≥ 1.35. `flagKlowSZA`: K > 1.05 with SZA < 75°. `flagKhighSZA`: K > 1.10 with SZA ≥ 75°. `flagKKt`: K > 0.96 when Kt > 0.6, GHI > 150 W/m² and SZA < 85°. |

- BSRN closure and tracker-off tests are not implemented, because PVsyst cannot import GHI, DHI and DNI together.
- DHI above GHI is capped at simulation time.

**Gap filling**

| Gap | Treatment |
|---|---|
| Sub-hourly gaps under 1 h | Linear interpolation. Longer gaps are not filled. |
| 1-4 h gaps | Irradiance is not filled by day and is set to 0 at night. Missing daytime rows are shown yellow. DHI is recomputed from GHI. Other variables are linearly interpolated. |
| Gaps over 4 h | Temperature is synthesised from the site temperature and GHI. Wind, albedo, RH and Linke take the monthly site values. Module temperature is not replaced. |

URLs: https://www.pvsyst.com/help/meteo-database/custom-meteo-files/data-verification.html, https://www.pvsyst.com/help/meteo-database/custom-meteo-files/data-gaps.html

**IT relevance: Medium-High.** It matters most for O&M re-simulation and measured-data studies. The thresholds can be reused directly in a QC module.

#### 1.6.6 PVsyst standard CSV format (for clean data)

**Header**
- Lines start with `#`. The first line is, for example, `#TMY hourly data`.
- Each tag has a value in the next cell.
- Mandatory tags: Site, Country, Data Source, Time step, Latitude, Longitude (negative west), Altitude, Time Zone. Year is needed only if the data does not give it.
- Optional tags: Time reference (UT+X), Hour Shift, Time Shift (min), Plane tilt (for POA), yearly Albedo, summarisation period.

**Data**
- One row of column names, one row of units, then data.
- Year, Month, Day and Hour in separate columns, Minute optional.
- Timestamps mark the start of each interval. Solar geometry is computed at the interval's midpoint.
- Mandatory: GHI and Tamb. GPI (POA) can replace GHI.
- Optional: DHI, DNI, WindVel (at 10 m), RH, Pw, Linke, Aod (reserved).
- Generic or synthetic data uses the year 1990 or 2059.
- Real data includes 29 February; averaged or synthetic data never does.
- Night rows are mandatory: 8760 or 8784 lines.
- The separator follows the Windows locale (semicolon or comma); the decimal mark is a dot.

URL: https://www.pvsyst.com/help/meteo-database/import-meteo-data/pvsyst-standard-format.html

**IT relevance: Medium.** This is a documented exchange format that a new program can read and write.

#### 1.6.7 Synthetic hourly and sub-hourly generation (from monthly .SIT)

PVsyst uses the **Meteonorm 9.0 algorithm**, based on Collares-Pereira (irradiance) and Scartezzini (temperature), "but modernized".

| Variable | Method |
|---|---|
| Daily GHI | Aguiar et al. Markov chains using a clear-sky clearness index, for consistency with the ESRA clear-sky model. Matrices are 9×10×10, recalibrated on 121 stations. |
| Hourly GHI | TAG model (Aguiar and Collares-Pereira 1992): a deterministic profile plus AR(1). |
| Diffuse and direct split | Perez et al. (1990). Older versions used Erbs, which tended to overestimate diffuse in middle Europe. |
| Minute data | Remund model trained on 15 BSRN stations. It stores 20 measured minute profiles classified by wind (3 classes), cloud cover (10) and solar elevation (5). |
| Temperature | Daily mean from AR(1), keeping each month's mean and standard deviation. Hourly profile linked to the GHI sequence. |
| Wind | Deterministic-stochastic model with profiles for 7 terrain and climate classes. "not intended for wind power plant design". |
| Relative humidity | From dew point and temperature. Monthly RH is an input since 8.1.5 and is not renormalised. |
| Linke turbidity | Gueymard climatology (MODIS/MISR 2000-2015) plus a daily AR(1) term. |

- Results are renormalised to the monthly totals.
- The process is stochastic. No seed or reproducibility mechanism is documented [unverified].
- Time steps since 8.1.5: 1 min, 5 min, 15 min (resampled from 1-minute data) and 1 h.
- Triggers: automatically at site creation, or manually from "Execute generation".

URLs: https://www.pvsyst.com/help/meteo-database/synthetic-data-generation/index.html, https://www.pvsyst.com/help/meteo-database/synthetic-data-generation/synthetic-data-model.html

**IT relevance: Medium.** It needs a proprietary engine (Meteonorm). For Italy, a free alternative is to download PVGIS TMY or hourly series directly.

#### 1.6.8 TMY generation from multi-year series

**Input requirements**
- At least **10 consecutive full calendar years**, as .MET files from the same site and source.
- The year must be at the end of each file name.

**Methods**
- **ISO 15927-4:2005**.
- **Sandia** (TMY2).
- **NREL NSRDB** (TMY, with TGY and TDY variants).
- **Custom** with user weights.

**Outputs**
- Long-term monthly averages and the TMY monthly values.
- A comparison graph.
- CDF comparisons per month.
- The generated file stores the interannual variability, which P90 uses.

URL: https://www.pvsyst.com/help/meteo-database/tmy-data-generation/index.html

**IT relevance: Medium.** Useful for MW projects with purchased multi-year series. PVGIS also offers hourly series for Italy (2005-2020 per the PVsyst page) from which a TMY can be built.

#### 1.6.9 Comparing sources and interannual variability

**Compare weather data**
- Selects every .MET and .SIT file with the same site name. Items can be reordered and removed.
- Shows yearly GHI per source, as absolute or % difference.
- "Export table" sends the data to a spreadsheet.
- The "Histo and probabilities" option gives the year-to-year distribution of multi-year data.

**Interannual variability**
- Defined as the σ of annual irradiation, as a % of the mean.
- Sources: Meteonorm, stored by TMY generation, or computed from your own multi-year data.
- **Default model since 8.1.4**: a linear fit on GEBA data, about **5.1 % at 900 kWh/m²/yr** and **3.5 % at 1700 kWh/m²/yr**.
- Earlier default (Ineichen): 2.5 % at ≥1700 kWh/m², rising to 8 % at 900 kWh/m².

**Provider comparison page**
- Four free sources at nine sites. They "typically concur within 10% of the mean value".
- No ranking is given.

URLs:
- https://www.pvsyst.com/help/meteo-database/compare-meteo-data/index.html
- https://www.pvsyst.com/help/meteo-database/compare-meteo-data/annual-variability.html
- https://www.pvsyst.com/help/meteo-database/compare-meteo-data/data-source-comparison.html

**IT relevance: High** for P90 on multi-MW. Most Italian sites fall between the two anchor values (about 1,200-1,900 kWh/m²/yr GHI) [indicative, unverified].

#### 1.6.10 Tables, graphs, data-quality checks and time shift

**Tables and graphs**
- Any .MET variable at sub-hourly, hourly, daily or monthly resolution, plotted against a clear-sky model (blue).
- Derived values: beam, Kt, and GTI on a chosen plane. Since 8.0.20, the tilted-plane view applies the chosen albedo.
- Tables export to .csv. Missing daytime GHI rows are yellow.

**"Check data quality" tab**
- Monthly best clear-day time shift.
- Hourly Kt for mornings and evenings, with a **time-shift scrollbar**: the shift is right when the morning and afternoon peaks balance.
- Monthly best clear days.
- Sorted Ktcc for every day. On the best days it should be within about 5 % of clear sky, which checks sensor calibration.
- The clear-sky model is not named on these pages [unverified; the synthetic-data page refers to ESRA].

**Time shift**
- Checked visually; there is no numeric threshold.
- The shift is split into whole time steps plus a remainder. The remainder is stored in the .MET to correct sun position, for example 25 min with a 10-min step becomes 2×10 + 5.
- Since 8.1.0 there is no upper limit.
- Data stored in .MET is always winter (standard) time.
- A clock that drifts during the year cannot be corrected.

URLs:
- https://www.pvsyst.com/help/meteo-database/meteo-tables-and-graphs/index.html
- https://www.pvsyst.com/help/meteo-database/meteo-tables-and-graphs/check-data-quality.html
- https://www.pvsyst.com/help/meteo-database/custom-meteo-files/time-shift.html

**IT relevance: Medium-High.** Italian SCADA and datalogger exports are often in CET/CEST local time. The DST handling and visual time-shift tools are directly useful.

#### 1.6.11 Clear-sky weather file

- Generates a full-year clear-sky .MET from latitude, longitude and altitude, with optional Linke turbidity (default 3.5; about 2.0 for clean, dry air up to 5-6 for humid or polluted air).
- Use: behaviour under full sun during sizing. It "should not be used for a system yield yearly evaluation".
- 8.1.0 updated the solar constant to 1361 W/m², which slightly changes clear-sky-based sizing steps.

URL: https://www.pvsyst.com/help/meteo-database/import-meteo-data/clear-sky-file-generation.html

**IT relevance: Low-Medium**, mainly for inverter and cable sizing checks.

#### 1.6.12 Sub-hourly data and resampling (8.1)

**Simulation**
- Since 8.1.0, simulations run at the .MET time step, chosen with a radio button.
- Sub-hourly data comes from Meteonorm 9 minute data, a custom import, or synthetic generation.
- Adapted models:
  - transposition and GHI→DHI at sub-hourly scale;
  - a **transient thermal model** for module thermal inertia;
  - a **sub-hourly clipping correction** (since 8.0), which also works in hourly runs.
- "much faster" hourly runs are recommended for iterative design.
- 8.1.7 adds predefined sub-hourly steps in the advanced simulation dialog.

**Resampling**
- Averages to a coarser step that divides 60 min and is at most 1 h. A file can be resampled only once.
- It stores the min and max GHI and counts of steps above the average (`vitGHIMean`, `vitGHIMeanSH`). These let the clipping correction run on resampled files.
- Introduced in 8.1.5. Resampled files are not backward compatible.

URLs: https://www.pvsyst.com/help/meteo-database/sub-hourly-simulations.html, https://www.pvsyst.com/help/meteo-database/notes-on-meteo/meteonote4-resampling.html

**IT relevance: Medium-High** for high DC/AC ratio plants, where sub-hourly clipping is underestimated.

#### 1.6.13 Notes: horizon in weather files, averaging, daily import

**Horizon in weather files**
- Monthly database values are usually for an "unobstructed horizon".
- Station data may already include the station's own horizon.
- Five steps to remove it before applying the plant's horizon: generate hourly data, apply the station horizon, recompute the monthly values, remove the horizon effect, regenerate hourly data, then apply the plant horizon in the simulation.

**Averaging**
- "Only monthly weather data values may be averaged". Averaging hourly or daily data across years has "no physical meaning".
- Alternatives: average the monthly sums and generate synthetic data, or simulate each year and average the results.

**Daily import**
- A "legacy option that is not recommended anymore".
- Hourly values come from a clear-sky shape or from Markov matrices. Temperature is synthetic.

URLs:
- https://www.pvsyst.com/help/meteo-database/notes-on-meteo/meteonote1-horizon-in-meteo-files.html
- https://www.pvsyst.com/help/meteo-database/notes-on-meteo/meteonote2-data-averaging.html
- https://www.pvsyst.com/help/meteo-database/custom-meteo-files/daily-data-import.html

**IT relevance: Medium.** PVGIS data and horizon handling must avoid double counting, for example when PVGIS horizon import is combined with already-shaded data [inference].

### 1.7 Databases: component database

#### 1.7.1 Contents and management

**Contents**
- PV modules, grid inverters, batteries, stand-alone controllers, back-up generators, pumps, pumping controllers, sellers, user prices, favourites.
- Optimizers are "chosen in the database" from the grid system definition.

**Size and sources**
- About **12,500 modules** (above about 35 Wp for c-Si) and about **4,500 inverters** (100 W to 2.5 MW). The PHOTON page gives about 14,000 and 4,800.
- Until 2008-2009, data came from the PHOTON magazine survey. Since then manufacturers fill in a predefined **Excel template**, which PVsyst checks before inclusion.

**Updates and lifecycle**
- The database is refreshed with each release, roughly monthly. "There is no online update".
- "We never suppress old devices from the database". Obsolete devices are marked by retrieval year and can be filtered out.
- PVsyst does not guarantee the data. Users must check against current datasheets.

**User files**
- New or modified devices are saved as **.PAN or .OND** in the user workspace. The built-in database is a permanent file renewed at reinstall.
- To add a device, copy a similar one, edit it and save under a new name.

**Exchange**
- `Files > Import or Export Components`.
- **Excel row exchange** with the `Components.xls` workbook: "Export to Table" and "Paste from Table". Missing Rshunt and Rserie get defaults. This works for modules and inverters.

**Favourites**
- Shown green; they shorten every choice list.
- Set by right-click in the database, or with "Set Favorites".

**PHOTON import**: clipboard-based and dead since March 2016.

URLs:
- https://www.pvsyst.com/help/component-database/index.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/modules-in-the-database/index.html
- https://www.pvsyst.com/help/component-database/grid-inverters/inverters-in-the-database.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/modules-in-the-database/pv-module-in-tabular-form.html
- https://www.pvsyst.com/help/component-database/favorites.html
- https://www.pvsyst.com/help/component-database/photon-database.html
- https://www.pvsyst.com/help/project-design/grid-connected-system-definition/index.html

**IT relevance: High.** Every project needs the actual module and inverter. Meridiana needs PAN/OND import, a user library, favourites and data-quality flags.

#### 1.7.2 PV module definition (.PAN)

The dialog has sheets plus a Graphs tool.

**Basic data**
- Model, manufacturer, data source (manufacturer and year).
- File name, which is the primary key, e.g. `Manufacturer_Model.PAN`.
- **Pnom** (nameplate; sets the PR reference).
- **Tolerances**, the "default value for the Module Quality Loss parameter".
- Technology.
- Reference conditions Gref and Tref: STC, or outdoor conditions.
- Isc, Voc, Impp, Vmpp.
- **muIsc**: "about 0.05%/°C" if unknown.
- A model summary and an "internal model result tool" for any irradiance and temperature.
- An optional link to the **Sandia** model, with a Sandia-diode comparison.

**Sizes and technology**
- Module dimensions (the basis of efficiency).
- Cells in series (required). Cells in parallel (not used). Cell area (optional).
- Max array voltage, IEC and/or UL (1000, 600 or 1500 V).
- Number of bypass diodes, which define sub-modules.
- **Sub-module partition**, used by the module layout for electrical shading.
- Tile module (visible active area).
- CPV flag.
- **Bifacial** flag and bifaciality factor.

**Model parameters (one-diode)**
- **Rshunt**: default from (Isc−Impp)/Vmpp. **Exponential Rsh(G)** with exponent about 5.5 for c-Si and a-Si, about 3.0 for CdTe. Rsh(0)/Rsh is about 4 for c-Si and about 12 for a-Si.
- **Rserie**: "crucial" for low light. **RseriesApp** is the apparent value at Voc.
- Saturation current; **Gamma** with **muGamma** (linear in T).
- muVoc and muPmpp are model results. "Apply the correction" adjusts muGamma to match the specified muPmpp.
- Thin film: recombination term (d²MuTau) and spectral correction for a-Si and µc-Si.
- Manufacturer Rseries values above PVsyst's standard are accepted only with independent low-light certification.

**Additional data**
- **IAM**: an ASHRAE `b0` value or a custom profile. It must be selected in Detailed losses.
- Sandia parameters.
- Secondary parameters: reverse quadratic factor **Brev**, number of bypass diodes, diode direct voltage, diode max current (unused).
- Also listed: **LID loss**, absorptivity, **degradation**.

**Measured data**
- **Low-light efficiencies** at 4 or more irradiances (800, 600, 400 and 200 W/m²), entered as relative efficiencies or as Isc/Voc/Impp/Vmpp, then "optimizing the Rserie".
- **Measured I/V curve** import (e.g. pasted from Excel), fitting Rsh and Rs.

**Commercial data**: manufacturer, availability, prices.

**Related release notes**
- 8.0.0: module ageing split changed to 80 % current / 20 % voltage; small bifaciality allowed for CdTe.
- 8.0.5: lower Rserie limit updated for M12 cells.
- 8.0.14: Voc display precision fixed.

URLs:
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/index.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/pv-modules-basic-data/index.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/pv-modules-sizes-and-technology.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/pv-modules-model-parameters.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/pv-modules-additional-data/index.html
- https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/pv-modules-measured-data/index.html

**IT relevance: High.** Every Italian project specifies the exact module. Low-light and Rserie handling drives yield differences between tools.

#### 1.7.3 Grid inverter definition (.OND)

**Main parameters, DC input**
- **VmppMin and VmppMax**, sized at about 50 °C in summer and 20 °C in winter.
- **VAbsMax**, compared with Voc at the lowest temperature (example: −10 °C for middle Europe).
- **Pthresh** (about 1 % of Pnom if unknown).
- **Vmin_Pmax**: below it, current is limited.
- **IMax_InMPPT**; VmppNom.
- PNomPV, PMaxPV and IMaxPV: informative, or a blocking constraint in sizing if marked "Required".

**Main parameters, AC output**
- Mono or three-phase; 50 or 60 Hz.
- **VNomAC**, used for AC losses.
- **PNomAC**, the continuous limit.
- **PMaxAC**, temperature-dependent since 6.30.
- INomAC and IMaxAC are not used.

**Efficiency curve**
- Max and European/CEC efficiency.
- Up to **8 points for each of up to 3 input voltages**, entered as Pout=f(Pin) or as efficiency against Pout or Pin. Points can be typed or dragged.
- Simulation interpolates parabolically between the voltages.
- Physical shape: below Pthresh, no output; then output proportional to (Pin − Pthresh) minus quadratic ohmic losses; the peak is "usually around 50-60%" of nominal.
- European weights were proposed by **JRC Ispra on the Ispra (Italy) climate**: 3/6/13/10/48/20 % at 5/10/20/30/50/100 % Pnom.
- CEC weights: 4/5/12/21/53/5 % at 10/20/30/50/75/100 % Pnom.

**Additional parameters**
- **Multi-MPPT**: each input is treated as an independent fraction of the inverter, which is a stated PVsyst limitation.
- **Unbalanced MPPT** (main and secondary inputs), sized from the sub-array power share; max Isc per input.
- Number of DC inputs (informative); string-inverter flag.
- Transformer type: none, LF or HF.
- **Master/slave**, with a threshold for switching on the second unit.
- **Auxiliaries consumption**, which must be set in Detailed losses.
- Night consumption (values under 0.05 % do not show in the loss diagram).
- Informative fields: isolation monitoring, DC and AC switches, AC disconnect limits, ENS.

**Output parameters**
- **Power factor capability** as cos φ lagging/leading or tan φ limits, with **Pnom given as kW or kVA** (kVA limits the current). The operating PF is set at system level.
- **Pnom(T)**: PMax below one temperature, Pnom up to another, and two further derating steps.
- Reference temperature options: ambient; ambient plus a shift; or a fixed value plus a term proportional to irradiance.
- Guidance: a DC/AC ratio of about 1.25-1.30 gives negligible overload loss. PMax raises the effective Pnom; cos φ "reduce[s] the effective PNom".

**Measured data**: fit the efficiency curve to measured array and inverter energies, automatically or by dragging points, then save under a new name.

URLs:
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/index.html
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-main-parameters/index.html
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-efficiency-curve/index.html
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-efficiency-curve/european-or-cec-efficiency.html
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-additional-parameters/index.html
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-output-parameters.html
- https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/measured-data-adjusting-the-efficiency-curve.html

**IT relevance: High.**
- Italian connection rules require reactive-power capability and a PF set-point, so the PF and kVA fields matter. Requirements under CEI 0-16 and CEI 0-21 are outside the scope of this research [unverified].
- Temperature derating matters for southern sites.

#### 1.7.4 Power optimizers

- Optimizers are chosen from the database in the grid system definition. The definition page is part of 1.A.
- Release notes add brands and rules:
  - 8.0.0: AdvanSol, Sungo, Generic;
  - 8.0.15: SolarEdge heterogeneous strings;
  - 8.0.16: AndSolar;
  - 8.1.0: Huawei;
  - 8.1.5: more than 2 strings per MPPT for compatible Huawei combinations.
- The file format of optimizer definitions is [unverified].
- URLs: https://www.pvsyst.com/help/project-design/grid-connected-system-definition/index.html, https://www.pvsyst.com/help/release-notes/index.html

**IT relevance: Medium-High.** Optimizers are common on Italian residential roofs.

#### 1.7.5 Batteries (.BTR)

**Technologies**
- **Lead-acid** and **Li-ion**.
- Li-ion entries are **cells**, used as building blocks: modules such as "8S50P", then cabinets or racks, then containers where the rack count is set in the project.

**Parameters**
- Cells in series and in parallel.
- Nominal voltage.
- **Capacity at C10**, with a tool to convert datasheet C2 or C5 ratings that must be entered manually.
- Max charge and discharge currents. A general **C2 limit** applies to Li-ion.
- Internal resistance: default 16 mV per cell at C10.
- **Coulombic efficiency** "supposed to be 96%" for Li-ion.
- Self-discharge, temperature dependent above 30 °C.
- Reference temperature; sizes and weight.

**Detailed model**
- Open-circuit voltage set at 50 % SOC, with a slope by technology.
- Capacity depends on discharge rate (Peukert for Li-ion) and drops below 10 °C.
- Li-ion resistance follows Arrhenius ("Activation energy") and rises at high SOC.
- **Cycling ageing**: cycles against DOD follow the hyperbola `NbCycle = cycles@100%DOD / DOD`, as a 5-point profile with a "Set Hyperbola" helper.
- Calendar ageing on these pages: [unverified].

**Universal battery**: defined only by voltage and capacity, for early design and batch work.

**Related release notes**
- 8.1.2: battery model updated for energy balance.
- 8.1.4: state of health now reduces capacity in the simulation.

URLs:
- https://www.pvsyst.com/help/component-database/batteries/index.html
- https://www.pvsyst.com/help/component-database/batteries/batteries-dialog/index.html
- https://www.pvsyst.com/help/component-database/batteries/batteries-dialog/basic-data-li-ion.html
- https://www.pvsyst.com/help/component-database/batteries/batteries-dialog/detailed-model-params.html

**IT relevance: Medium-High.** Residential storage is widespread in Italy. Grid-storage models and dispatch are covered in 1.A.

#### 1.7.6 Stand-alone controllers (charge regulators and solar chargers)

**Operation**
- On/off only, "not with proportional or partial-field regulation".
- Starting and stopping thresholds on modelled battery voltage, or **on SOC**, with a SOC↔voltage tool.

**Parameters**
- Charging and discharging (load disconnect) thresholds.
- Linear temperature compensation, from an internal or external sensor.
- Max input and output currents, checked before simulation.
- Optional MPPT or DC-DC converter, set as "Technology".
- Some devices have two switchable battery voltages.
- Back-up generator thresholds; a wrong order of thresholds is rejected.

**Universal controller**
- Automatically adapts thresholds, temperature corrections, converter voltages, power and efficiency, maximum currents and genset control.
- Can be saved as `Manufacturer_Model.RLT`.

URLs:
- https://www.pvsyst.com/help/component-database/controllers-for-stand-alone-systems/index.html
- https://www.pvsyst.com/help/component-database/controllers-for-stand-alone-systems/controllers-main-interface/index.html
- https://www.pvsyst.com/help/project-design/stand-alone-systems-definition/universal-controller.html

**IT relevance: Low.**

#### 1.7.7 Back-up generator

- Modelled only as an "alternator+rectifier" that charges batteries.
- Inputs: nominal power, operating power, specific fuel consumption (volume per hour).
- No commercial generators are in the database.
- URL: https://www.pvsyst.com/help/component-database/back-up-generator.html

**IT relevance: Low.**

#### 1.7.8 Pumps

**Model**: a "black-box" with electrical inputs (V, I) and hydraulic outputs (head, flow). An integrated converter can be part of the pump definition.

**Dialog sheets**
- General data.
- Detailed parameters, including the choice of model by available data.
- Data curves: operating points with Voltage or Head as the curve parameter, cubic-interpolated. "Usually 4 or 5 points per curve and 3 or 4 curves are sufficient".
- Current thresholds, set graphically.
- Size and technology; commercial data; graphs and running conditions.

**Technologies**
- Centrifugal, including multistage: low head, high flow; flow depends quadratically on power above a threshold.
- Positive displacement (piston, membrane, progressive cavity, rotating): high head; may need inrush current.
- Installation: surface or submersible.

URLs:
- https://www.pvsyst.com/help/component-database/pump-definition/index.html
- https://www.pvsyst.com/help/component-database/pump-definition/pump-technologies.html
- https://www.pvsyst.com/help/component-database/pump-definition/pump-data-performance-curves.html

**IT relevance: Low** (agricultural niche).

#### 1.7.9 Pumping controllers and converters

- Hold the operating configuration and the absolute power, voltage and current limits.
- Stop the pump on a full tank or a low water level (dry running).
- Can include an **MPPT or a fixed-voltage DC-DC converter**, with DC or AC output.
- A **universal default controller** exists for each strategy, auto-adapted just before simulation. Commercial controllers can be defined for the final design.
- URL: https://www.pvsyst.com/help/component-database/controllers-for-pumping/index.html

**IT relevance: Low.**

#### 1.7.10 Commercial data, sellers and price list

- Prices are per component and **per seller**, with quantity discounts and the date set.
- Prices can be entered in the price list or from the economic evaluation ("Open component form").
- The database currency may differ from the evaluation currency.
- Commercial data is a reference only, because prices "vary from country to country".

URLs:
- https://www.pvsyst.com/help/component-database/pv-components-commercial-data.html
- https://www.pvsyst.com/help/component-database/price-list/index.html
- https://www.pvsyst.com/help/project-design/economic-evaluation/installation-and-operating-costs.html

**IT relevance: Medium** for an office price list.

### 1.8 Tools

| Toolbox | Tool | What it does |
|---|---|---|
| Solar | **Graph/Tables of solar parameters** | Solar geometry and clear-sky irradiation on planes. |
| Solar | **Transposition factor** | Helps optimise and evaluate field orientation. |
| Solar | **Monthly weather data computation** | A quick monthly evaluation including horizon, tilt, sheds, sun-shields and IAM. |
| Electrical | **Electrical behaviour of PV arrays** | Reverse characteristics of modules, mismatch, arrays with shaded cells, heterogeneous arrays. Documented under Project design; see 1.1.8. |
| Electrical | **Operating (array-coupling) voltage optimisation** | Yield of a PV array forced to a fixed voltage (e.g. battery charging), for a year or a season. |

**Monthly weather data computation, method**
- The hour-by-hour average of a month's days looks like a clear day with reduced amplitude. A mid-month clear day scaled to the monthly irradiation represents the whole month.
- Transposition, shading and IAM are applied on that day's geometry.
- Monthly diffuse comes from a correlation when unknown (about 5 % uncertainty).
- Yearly bias against hourly calculations for Geneva: under 1.3 % for south planes; up to 11 % for east or west planes at 90°.

**Operating voltage optimisation**
- Inputs: hourly weather, orientation, module type and series/parallel layout, diode drop, wiring resistance, the set of fixed voltages.
- Findings: the optimum is "very near from the average MPP voltage", and MPPT gains only about 1.5-2 % over a well-chosen fixed voltage.

Other tool-like functions sit elsewhere and are covered in their own sections: weather comparison, TMY, synthetic and clear-sky generation (1.6); the sheds optimisation tool and batch mode (1.1.20); the carbon balance (1.1.18); the ageing tool (1.1.14.4).

URLs:
- https://www.pvsyst.com/help/tools/index.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/meteo-monthly-calculations.html
- https://www.pvsyst.com/help/tools/array-coupling-voltage-optimisation.html

**IT relevance**
- **Medium**: transposition factor and orientation optimisation, which Italian roofs constrain anyway.
- **Low**: fixed-voltage optimisation.

### 1.9 Measured data analysis

**Purpose**: validate the model, detect "even minor malfunctions", and find the "real system parameters".
- The measured file (.DAM, hourly or sub-hourly) **replaces the weather file** of a variant. A project can hold several measured files, for example one per period.
- Near and far shadings and all losses are defined as in a normal project.

**Workflow and tools**
1. **Import** hourly or sub-hourly ASCII/CSV through the custom import, with legacy pages for measured data.
2. **Check** the data:
   - scrolling tables (monthly to sub-hourly);
   - control graphs (time evolution, histograms);
   - **input/output diagrams** (production against irradiation);
   - **normalised performance** graphs;
   - the **inverter modelisation analyser**, which overlays the library efficiency curve on measurements, fits it, and saves a new .OND;
   - the same time-definition (time-shift) check as for weather data.
3. **Transform** files: **merge** parameters from another file (e.g. weather from a nearby station), **cut** whole days, **link** two files with the same structure at a date. The files are not ASCII and "should never be modified in a text-editor".
4. **Predefine comparisons**: pair a measured variable with a simulated one, accumulated hourly, daily or monthly. Filters:
   - daytime only (GHI or POA > 20 W/m²);
   - cuts after sunrise or before sunset;
   - exclusion of breakdowns;
   - inverter running (grid) or array producing (stand-alone);
   - cuts on another measured variable or on about 70 simulated variables, e.g. the diffuse fraction.
5. **Simulate and compare**: stores measured/simulated pairs. Results are saved as **.CMi**.
6. **Eliminate erroneous data**:
   - limit lines on the comparison graphs, on the value, difference or ratio;
   - click to remove or restore a point; edits in tables.
   - Eliminations apply to all graphs of the variant and also drop the whole day from daily graphs.
   - They are saved in the .CMi or written back to the .DAM as breakdown flags.
- Statistics: mainly mean bias and standard deviation.

URLs:
- https://www.pvsyst.com/help/measured-data/index.html
- https://www.pvsyst.com/help/measured-data/measured-data-analysis-general-philosophy.html
- https://www.pvsyst.com/help/measured-data/checking-the-measured-data-files.html
- https://www.pvsyst.com/help/measured-data/transformations-of-data-files.html
- https://www.pvsyst.com/help/measured-data/predefinition-of-comparisons.html
- https://www.pvsyst.com/help/measured-data/cuts-of-erroneous-data.html
- https://www.pvsyst.com/help/project-design/simulation/simulation-and-comparison.html

**IT relevance: Medium.** Useful for O&M, performance disputes and post-commissioning verification of MW plants. Less relevant to design studies.

### 1.10 Physical models used

PVsyst's "Physical models used" chapter (https://www.pvsyst.com/help/physical-models-used/index.html) groups the meteorological models (solar geometry, irradiation) and the component models (PV module, grid inverter, batteries, pump). They are described here in that order. The losses applied around these models are in 1.1.13, and the simulation order is in 1.1.14.1.

#### 1.10.1 Time definition and solar geometry

Sources for this subsection:
- https://www.pvsyst.com/help/physical-models-used/time-definition-in-pvsyst.html
- https://www.pvsyst.com/help/physical-models-used/solar-geometry.html
- https://www.pvsyst.com/help/meteo-database/custom-meteo-files/time-shift.html
- https://www.pvsyst.com/help/meteo-database/notes-on-meteo/meteonote3-time-shift-in-meteo-files.html
- https://www.pvsyst.com/help/meteo-database/notes-on-meteo/meteonote4-resampling.html
- https://www.pvsyst.com/help/project-design/simulation/index.html
- https://www.pvsyst.com/help/glossary/meteo-data/time-zone.html
- https://www.pvsyst.com/help/glossary/meteo-data/generic-year-1990.html
- https://www.pvsyst.com/help/glossary/solar-geometry/plane-azimuth.html
- https://www.pvsyst.com/help/glossary/solar-geometry/profile-angle.html
- https://www.pvsyst.com/help/glossary/solar-geometry/transverse-incidence-angle.html
- https://www.pvsyst.com/help/glossary/solar-geometry/longitudinal-incidence-angle.html
- https://www.pvsyst.com/help/glossary/solar-geometry/base-slope.html
- https://www.pvsyst.com/help/release-notes/index.html (8.1.0, 8.1.5, 8.1.7)

##### Time conventions

| Item | PVsyst 8.1 behaviour | Source page |
|---|---|---|
| Reference time | Legal time of the site, set by the time zone (offset to GMT/UTC). **No daylight saving time**: the "basic time (usually winter time)" is used all year. For most of Europe, winter time is GMT+1. | time-definition-in-pvsyst; glossary time-zone |
| Time stamp | The label is the **beginning** of the interval, for hourly, daily and monthly values. 11:00 means the average over 11:00-12:00; in a 15-minute file, 12:00 means 12:00-12:15. | time-definition-in-pvsyst; time-shift |
| Sun position within a step | Computed at the **middle** of the interval (11:30 for the 11:00 step). In the sunrise interval it uses the midpoint between sunrise and the end of the interval; the sunset interval is handled the same way. | time-definition-in-pvsyst; meteonote3 |
| Time shift, 8.1.0 implementation | Import options in the Date tab: Universal Time base (converted to legal time; the site must be correct), DST dates, "Record time label -> interval end", and a residual "Time shift" that aligns the data with the clear-sky model. The total shift is split into (1) whole-timestamp shifts applied to the data in the .MET file and (2) a minimised remainder stored in the .MET and applied to the sun position during simulation. Examples: +25 min on 10-min data = 2 steps + 5 min; +19 min = 2 steps − 1 min. No upper limit since 8.1.0; the separate "hour shift" field was removed (an old +1 h is read as +60 min). | time-shift |
| Why the shift must be set at import | The import itself runs models that need the sun position (diffuse model, POA reverse transposition). A wrong time gives unphysical GHI in the morning and evening, which can reach several kW/m². | time-definition-in-pvsyst; meteonote3 |
| Time-shift diagnosis tools | "Monthly best clear days" (data against clear sky) and "Hourly Kt morning/afternoon" (aligning the two patterns gives the shift). | time-shift; meteonote3 |
| Legacy (hourly .MET before 8.1.0) | Time shift up to ±30 min (hidden parameter "Maximum allowed time shift"); an hour shift for larger offsets; the PVsyst standard CSV accepts the header lines `#Time shift`, `#Hour shift` and `#Time Reference` = UT. | meteonote3 |
| Generic year | Data that are not measurements of a real year (monthly averages, synthetic data, TMY, DRY) are labelled **1990**. The label cannot be changed, and outputs suppress the year. | time-definition-in-pvsyst; glossary generic-year-1990 |
| Simulation time step | 1 hour, or the sub-hourly step of the weather file. Sub-hourly simulation for grid-connected and stand-alone systems arrived in 8.1.0, and 8.1.7 lets the user pick predefined sub-hourly steps in "Advanced simulation". The help recommends hourly runs while iterating on the design and a sub-hourly run once the design is final. | simulation/index; release notes 8.1.0, 8.1.7 |
| Resampling | Only to a coarser step that is a multiple of the original step, a divisor of 60 min and at most 1 h (1→6 min allowed, 1→7 min not). Meteonorm synthetic files come at 1 min, 5 or 15 min (resampled from 1 min) and 1 h. | meteonote4-resampling; meteo-database/index.html#815-meteonorm-timesteps |

##### Solar geometry

- **Accuracy:** PVsyst uses "simplified expressions (accuracy within a few arc-minutes)" and points to the USNO website for more precise values. The help does not mention atmospheric refraction [not stated].
- **Equations as printed in the help (solar-geometry.html):**
  - Obliquity: Ecl = 23°26' (23.433°).
  - Declination: Decl = asin( sin(Ecl) · sin(2π·(NoDay − NoDayOrig)/NDaysY) ), with NoDayOrig = 79 + (Year mod 4)/4. For NoDay > 172 it adds 1.5·sin(2π·(NoDay − 173)/NDaysY).
  - Equation of time, with YAngle = 2π·(NoDay − 1)/365.25: TE = 0.0072·cos Y − 0.0528·cos 2Y − 0.0012·cos 3Y − 0.1229·sin Y − 0.1565·sin 2Y − 0.0041·sin 3Y [h].
  - Legal-to-solar time difference: DHLegHSol = TimeZone − Longitude/15 − TE. Then ST = legal time − DHLegHSol, and the hour angle is HA = 15°·(ST − 12).
  - Sun height: printed as sin(HSun) = **−**sin(Lat)·sin(Decl) + cos(Lat)·cos(Decl)·cos(HA). The textbook expression has **+**sin(Lat)·sin(Decl), so this is probably a typo in the help (analysis).
  - Sun azimuth: sin(AzSun) = cos(Decl)·sin(HA)/cos(HSun). It is measured from south in the northern hemisphere (from north in the southern), positive towards west.
  - Incidence angle: cos(IA) = cos(AzSun − AzimPl)·cos(HSun)·sin(TiltPl) + sin(HSun)·cos(TiltPl).
  - Profile angle: PrfAng = atan[ tan(HSun) / cos(AzSun − AzimPl) ]. It is the basis of all mutual-shading calculations (unlimited sheds and trackers, walls, balconies). The transverse and longitudinal incidence angles are defined on the profile plane; for horizontal-axis trackers the transverse angle is 90° − Phi.
- **Plane conventions:**
  - Tilt is measured from the horizontal.
  - Northern-hemisphere azimuth: 0 = south, +90 = west, −90 = east, 180 = north (opposite to the architects' convention). In the southern hemisphere 0 = north.
- **Base slope:**
  - A sloping table base changes the real tilt and azimuth. With a 5° base slope, a 1° nominal tilt gives a real azimuth of 78.7°, and a 20° tilt gives 13.5°.
  - In 3D scenes, orientations are identified by grouping table normals within a tolerance (1° by default). The user can raise it, for example to 20°, to merge orientations.
  - An "Orientation Understanding Education Tool" in the 3D scene shows the effect.
- **Tracker angles:**
  - The parameters are axis tilt, axis azimuth, Phi (rotation from the rest position) and the backtracking angle (the Phi at the limit of inter-tracker shading, which depends on the sun position).
  - A "N/S horizontal axis" tracks from east to west.

**IT relevance: high, for every project.**
- Italy is on UTC+1 in winter. PVsyst's no-DST legal time means Italian meter and load data recorded in local time with summer time need a DST conversion on import (analysis).
- PVGIS hourly series are in UTC (see 3.4). PVsyst's known-format imports are "usually" already corrected in their import protocol (meteonote3), but a custom import, or Meridiana's own, must convert them (analysis).

**Meridiana note:**
- pvlib's SPA (`solarposition.get_solarposition`) is more accurate than PVsyst's simplified formulas, so expect differences of the order of arc-minutes.
- Meridiana must write itself:
  - the mid-interval rule, including partial sunrise and sunset intervals;
  - the split time shift (timestamp shift plus residual minutes).
- PVsyst and PVGIS (`aspect`) measure azimuth from south, positive to the west; pvlib uses 180 = south. Put the conversion in one place.

#### 1.10.2 Irradiation models

Sources:
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/index.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/clearness-index.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/diffuse-irradiance-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/transposition-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/the-hay-transposition-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/perez-transposition-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/albedo.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/albedo-usual-coefficients.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/meteo-monthly-calculations.html
- https://www.pvsyst.com/help/glossary/solar-geometry/plane-orientation.html
- https://www.pvsyst.com/help/glossary/meteo-data/altitude-corrections.html
- https://www.pvsyst.com/help/glossary/meteo-data/diffuse-attenuation-factor.html
- https://www.pvsyst.com/help/glossary/meteo-data/transposition-factor.html
- https://www.pvsyst.com/help/meteo-database/import-meteo-data/clear-sky-file-generation.html
- https://www.pvsyst.com/help/meteo-database/synthetic-data-generation/synthetic-data-model.html
- https://www.pvsyst.com/help/meteo-database/custom-meteo-files/data-verification.html
- https://www.pvsyst.com/help/project-design/bifacial-systems/bifacial-systems-procedure.html
- https://www.pvsyst.com/help/release-notes/index.html (7.2.3, 8.1.0, 8.1.2, 8.1.6)

##### a) The irradiance chain (irradiation-models/index.html)

1. Monthly-only data are first turned into synthetic hourly GHI and ambient temperature (see 1.6.7).
2. **Decomposition** gives DHI and BHI. Here GHI = DHI + BHI and BHI = DNI·sin(SunHeight).
3. **Far shading** (horizon) is applied to the beam component.
4. **Transposition** gives the plane-of-array components: Gp = Dp + Bp + Ap (diffuse, beam, albedo).
5. **Near shadings** are applied to beam, diffuse and albedo, either "linear" or according to the electrical connections. Then the **IAM** is applied.
6. The result is **Geff**, the effective irradiance; Heff is the same quantity integrated over a period.

PVsyst variable names: GlobHor (GHI), DiffHor (DHI), BeamNorm (DNI), BeamHor (BHI).

| Available inputs | How DHI is obtained | How BHI is obtained |
|---|---|---|
| GHI only | Diffuse model | GHI − DHI |
| GHI + DHI | Input | GHI − DHI |
| GHI + DNI | GHI − BHI | DNI·sin(h) |
| DHI + DNI | Input | DNI·sin(h) |
| POA only | Reverse transposition (Hay) | Reverse transposition (Hay) |
| DNI only | Concentrating systems only; GHI approximated from the clear-sky model | DNI·sin(h) |

- POA data can only be imported alone.
- Reverse transposition uses the Hay model. The help calls it "recommended (and imposed since PVsyst 8.1.0)"; Hay's model has been used for all reverse transpositions since 7.2.3.
- The GHI recomputed from POA can be reused for other orientations only if they are close.
- On import, GHI is capped at a plausible value based on the clear-sky model.
- Sources: plane-orientation.html; meteonote3; release notes 7.2.3 and 8.1.0.

##### b) Extraterrestrial irradiance and clearness index (clearness-index.html)

- **Extraterrestrial irradiance:**
  - ENI = Esc·(1 + 0.033·cos θ), where θ is the orbital angle counted from 1 January.
  - The solar constant was **1367 W/m² until 8.1 and is 1361 W/m² from 8.1**. The 8.1.0 release note says this "has a slight effect" on all sizing steps based on the clear-sky model.
  - EHI = ENI·sin(HSol).
- **Clearness index:**
  - Kt = GHI/EHI.
  - Monthly Kt is expected between 0.12 and 0.82; the limits can be changed in Advanced parameters > "Size and Meteo".
  - Below a sun height of 2°, Kt = 0.
- **Cloud enhancement (Kt > 1):**
  - It is recognised as a real effect; the help cites GHI up to 1832 W/m².
  - High Kt sub-values are flagged on import. For example, the `flagKt` test in data-verification.html expects Kt < 1.35 whenever GHI > 50 W/m².

##### c) Diffuse (decomposition) models (diffuse-irradiance-model.html)

- **Which model is used where:**
  - **Custom weather imports:** **Erbs** up to version 8.0; **ENGERER2 with coefficients refitted by PVsyst** since 8.1, which introduced sub-hourly simulation.
  - Reverse transposition of POA-only data combines the diffuse model with the transposition model.
  - Meteonorm uses **DirInt** for its own data; the help notes it is also called the "Perez diffuse model".
- **Erbs:**

  | Kt range | DHI/GHI |
  |---|---|
  | Kt ≤ 0.22 | 1 − 0.09·Kt |
  | 0.22 < Kt ≤ 0.8 | 0.9511 − 0.1604·Kt + 4.388·Kt² − 16.638·Kt³ + 12.336·Kt⁴ |
  | Kt > 0.8 | 0.165 |

  - It was fitted on hourly data from 4 US sites, and its bias grows as the time step shrinks.
  - **PVsyst's own Erbs before 8.1 had a −4 W/m² bias (about 1-2 % of Geneva daytime GHI).** The cause was a timestamp inconsistency: the sun was computed at mid-interval instead of at the beginning, as the Erbs definition expects.
- **ENGERER2:**
  - DHI/GHI = C + (1 − C)/(1 + exp(β0 + β1·Kt + β2·AST + β3·θz + β4·ΔKtc)) + β5·Kde.
  - Inputs: GHI, latitude, longitude and timestamps, plus a clear-sky GHI.
  - Indicators: Ktc = GHIcs/EHI; ΔKtc = Ktc − Kt; Kde = max(0, 1 − GHIcs/GHI), which captures cloud enhancement. AST is the apparent solar time and θz the zenith angle.
  - Coefficients:
    - PVsyst refitted them on the IEA-PVPS dataset (1-minute GHI and DHI, 113 stations) to minimise the yearly bias worldwide.
    - Dedicated coefficients are used for sub-hourly steps (8.1.0 release note).
    - In 8.1.6 they were refitted again for the new solar constant; the release note cites an "EUPVSEC 2026 publication".
  - Comparison in the help: across time steps, ENGERER2 strongly reduces Erbs's sub-hourly bias and stays good at hourly steps.
- **8.1.6 fix:** the sun position in the GHI-to-DHI model for hourly GHI-only or POA imports was corrected. Before the fix, DHI values were shifted towards the afternoon.
- **Monthly-only data:** "the uncertainty of the monthly diffuse estimation correlation model (about 5%)" can add 1-4 % error (meteo-monthly-calculations.html).

##### d) Transposition models (transposition-model.html, the-hay-transposition-model.html, perez-transposition-model.html)

**Common to both models**
- The beam is purely geometric: BeamInc = BeamHor·cos(AngInc)/sin(HSol).
- The albedo is isotropic and Lambertian: AlbInc = ρ·GlobHor·(1 − cos θ)/2.
- Below a sun height of 2°, BeamInc = 0 and CircInc = 0.

**Hay (Hay-Davies)**
- Diffuse: DiffInc = DiffHor·(1 − Kb)·(1 + cos θ)/2.
- Circumsolar: CircInc = DiffHor·Kb·cos(AngInc)/sin(HSol), with Kb = BeamHor/EHI.
- The help describes it as "classic and robust", giving good results even when the diffuse is imperfectly known.
- In the old method (before V7), the circumsolar part was merged into DiffInc, with CircInc = 0.

**Perez (default since V6)**
- There are three diffuse components: isotropic, circumsolar and horizon band. The horizon band is included in DiffInc.
- DiffInc = DiffHor·[(1 − F1)·(1 + cos θ)/2 + F2·sin θ].
- CircInc = DiffHor·F1·cos(AngInc)/max(sin 5°, sin HSol).
- Fi(ε) = Fi1(ε) + Δ·Fi2(ε) + z·Fi3(ε), with 8 sky-clearness (ε) bins, i.e. **48 coefficients** (Perez et al. 1990).
- **Since 8.1.0, sub-hourly simulations use new 48-coefficient sets, one for each integer divisor of 60 minutes:**
  - They were fitted on the IEA-PVPS 113-site 1-minute dataset, using hourly transposed diffuse as the reference.
  - Their purpose is to remove the dependence of the result on the time step. The remaining discrepancy is attributed to the beam component.
  - Method: Oliosi et al., EUPVSEC 2023.

**Choice and validation**
- Where to set it: Preferences > Physical models (default for new projects) or Project settings > Design conditions. The model used can optionally be printed on the report.
- History:
  - Early validations on Swiss sites showed a systematic difference of 1.8-2.2 % between the two models (MBE).
  - Hay was the default up to V5.
  - Ineichen (2011) found Perez slightly better in RMSD in all cases, so Perez became the default from V6.
- Perez typically gives yearly sums 0-2 % above Hay.
- Circumsolar handling:
  - Up to V6.7.9, circumsolar was merged with the isotropic diffuse for shading and IAM.
  - V6.8.0 introduced separate treatment, which became the default in V7.0.
  - It changes linear shading and IAM losses slightly and matters most for large tilts, such as vertical bifacial systems.
- **Transposition factor** = GlobInc/GlobHor (hourly to yearly); it depends mainly on the diffuse share (glossary).

##### e) Albedo (albedo.html, albedo-usual-coefficients.html)

- **Two separate albedo parameters:**

  | Parameter | What it represents | Where it is set | Time resolution |
  |---|---|---|---|
  | Project ("far") albedo | Terrain in front of the array | Project settings | Yearly or monthly |
  | Bifacial ground albedo | Ground seen by the rear side | Bifacial System window | None (bifacial model off), Constant, Monthly, or a CSV **time series since 8.1.2** |

  - Monthly far-terrain albedo can also be set in the custom weather import (since 7.2.3).
  - .MET files can carry an hourly "Albedo" variable. The help does not say whether the transposition uses it [unverified].
  - Sources: bifacial-systems-procedure.html; release notes 7.2.3 and 8.1.2.
- **Contribution and default:**
  - The albedo contribution is (1 − cos θ)/2 of ρ·GHI: 50 % of it at 90° tilt, 14 % at 45°, 6.7 % at 30°, 3 % at 20° and 0.8 % at 10°.
  - The default ρ is 0.2.

  | Surface | Albedo |
  |---|---|
  | Urban | 0.14-0.22 |
  | Grass | 0.15-0.25 |
  | Fresh grass | 0.26 |
  | Fresh snow | 0.82 |
  | Wet snow | 0.55-0.75 |
  | Dry asphalt | 0.09-0.15 |
  | Wet asphalt | 0.18 |
  | Concrete | 0.25-0.35 |
  | Red tiles | 0.33 |
  | Aluminium | 0.85 |
  | Copper | 0.74 |
  | New galvanised steel | 0.35 |
  | Very dirty galvanised steel | 0.08 |
- **Shading of albedo:**
  - In rows of sheds or trackers only the first row sees the ground, so the albedo shading factor is (n − 1)/n (0.99 for 100 rows). This applies even with backtracking.
  - Near obstacles hide the far albedo: the factor is integrated over the "virtual" sphere portion below the horizon, only in azimuths without obstacles. It is constant over the year.
  - With a far horizon, the user chooses which fraction of the albedo in front of it to keep.
- **Effect on PR:** in sheds and trackers, a high albedo raises GlobInc but the extra albedo is almost all lost, so the PR falls while the yield stays the same.
- **Measurement:** an albedometer, measured over the long term. POA reference cells must "see" the albedo, so in tracker fields put them on an axis extension without neighbouring trackers; otherwise set ρ close to 0 when using that POA.

##### f) Clear-sky model

- The model depends only on the coordinates and altitude, modulated by the **Linke turbidity** (default 3.5; 2.0 for a very clean sky, 5-6 for humid or polluted air). Sites created from Meteonorm 9 carry Linke values.
- Uses: time-shift checks, clear-sky .MET files for sizing checks (not for yield), capping GHI on POA import, Ktc for ENGERER2, and sizing steps.
- The name of PVsyst's own clear-sky algorithm is not stated. The synthetic-data page refers to "the ESRA clear-sky model used elsewhere in the chain" [unverified for the simulation itself].
- Release notes:
  - 8.1.6 corrected the default Linke coefficients used for GlobHorCS and DiffHorCS when the SIT and MET files carry none.
  - 8.1.5 made GHI and DHI clear-sky values exportable.
- Sources: clear-sky-file-generation.html; synthetic-data-model.html; release notes.

##### g) Monthly calculations (meteo-monthly-calculations.html)

- **What it does:** a fast evaluation from the site's monthly values that covers horizon, tilt, rows, sun-shields and IAM without generating hourly data.
- **Method:** an "average day" for each month, built as a clear-day profile scaled to the monthly global (and diffuse) irradiation, using the solar geometry of the middle day of the month.
- **Accuracy against hourly calculation (Geneva), transposition MBE:**

  | Plane orientation | Tilt | Yearly MBE |
  |---|---|---|
  | South | 0-90° | < 1.3 % |
  | SE or SW | 45° | < 1.1 % |
  | SE or SW | 90° | < 4.1 % |
  | E or W | 45° | < 2.7 % |
  | E or W | 90° | < 11 % |

  - If only monthly GHI is known, the diffuse estimate adds 1-4 % error.

##### h) Other weather-related model items (glossary)

- **Altitude corrections:** applied to irradiation and temperature when a weather file is associated with a site at a different altitude. They are Swiss Meteonorm monthly correlations (Bremer 1986), not validated hourly, and are not applied to diffuse.
- **Diffuse attenuation factor:** the diffuse is treated as isotropic, so the near-shading and IAM factors for diffuse are integrated once over the visible sky and stay constant over the year. Trackers are recomputed for each position (see 1.1.7).

**IT relevance: high.**
- Perez/Hay and the albedo apply to every project.
- The decomposition model matters whenever local GHI-only data are imported (stations, monitoring) and for any POA-only monitoring data, where reverse transposition is involved.
- For rooftops at low tilt the albedo is negligible. It matters for façades or high tilts, and for bifacial modules on flat roofs with light membranes or gravel (the table gives only generic values).
- PVGIS uses a different transposition model (see 3.4), so cross-checks should tolerate a gap of a few percent (analysis).

**Meridiana note:**
- pvlib provides Erbs, Perez 1990, Hay-Davies, clearness index and extraterrestrial irradiance (pass `solar_constant=1361`).
- Meridiana must write itself:
  - ENGERER2 with PVsyst-like coefficients (or document a different decomposition);
  - Perez coefficient sets for sub-hourly steps (PVsyst's sets are not published in the help);
  - Hay reverse transposition;
  - the 2° cutoffs;
  - the separate circumsolar handling in shading and IAM.

#### 1.10.3 PV module model

Sources:
- https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/index.html, plus its sub-pages:
  - determination-of-parameters.html
  - parameters-besides-datasheets.html
  - rseries-and-rshunt-determination.html
  - rseries-determination-history.html
  - rshunt-exponential-behavior-vs-irradiance.html
  - temperature-behaviour-correction.html
  - rs-and-rsh-effects-on-low-light-efficiency.html
  - low-light-measurements-and-studies/ (index.html, isc-g-linearization.html, lowlight-analysing-tool.html, relative-efficiency.html, table-of-low-light-measured-points-in-excel.html)
  - model-for-thin-film-and-other-new-technologies/ (index.html, amorphous-modules-spectral-correction.html, spectral-characterization-average-photon-energy-ape.html, thin-film-modules-fit-on-input-values-of-rshunt.html, thin-film-modules-recombination-losses.html)
  - firstsolar-spectral-correction.html
  - sandia-model.html
  - pv-module-reverse-behaviour.html
  - reverse-characteristic-of-a-cell.html
  - pv-module-reverse-lowvoltage.html
  - pvmodule-model-graphs.html
  - pvmodule-structure/ (index.html, bi-facial-modules.html, cells-normalized-sizes.html, cells-size-determination.html, hot-spot-and-submodules.html, submodules-layout.html, submodules.html, twin-half-cut-cells-and-shadings.html)
- Supporting pages:
  - https://www.pvsyst.com/help/project-design/array-and-system-losses/spectral-correction.html
  - https://www.pvsyst.com/help/component-database/photovoltaics-modules/pv-modules-main-interface/index.html (model parameters as stored in the .PAN file; the full .PAN inventory is in 1.7.2)
  - https://www.pvsyst.com/help/release-notes/index.html (8.1.6)

##### a) Standard one-diode model (index.html)

- **Basic equation**, at reference conditions (usually STC: 1000 W/m², 25 °C, AM 1.5):
  - I = Iph,ref − I0,ref·[exp( q·(V + I·Rs) / (Ncs·γ·kB·Tc) ) − 1] − (V + I·Rs)/Rsh.
  - Five parameters: Iph,ref, I0,ref, Rs, Rsh, γ (diode quality factor, "theoretically between 1 and 2, often less").
  - Ncs is the number of cells in series. Constants: q = 1.602e-19 C, kB = 1.381e-23 J/K.
  - The equation is implicit and is solved by successive approximations.
- **Scope:**
  - All cells are assumed identical. PVsyst rejects the two-diode model as unjustified given the accuracy of manufacturer inputs.
  - The model suits all crystalline-Si technologies, and CIS "obeys quite well". Other thin films need the corrections in f).
- **Irradiance dependence:** Iph = (G/Gref)·[Iph,ref + μIsc·(Tc − Tc,ref)], with μIsc of the order of +0.05 %/°C. The photocurrent is assumed strictly proportional to irradiance.
- **Temperature dependence:**
  - I0 = I0,ref·(Tc/Tc,ref)³·exp[ q·EGap/(γ·kB)·(1/Tc,ref − 1/Tc) ].
  - EGap = 1.12 eV for c-Si, 1.03 eV for CIS, 1.7 eV for a-Si and 1.5 eV for CdTe.
- **Parameters stored in the .PAN file** (component-database main interface):
  - Rshunt, Rsh(G=0), RshExp, Rserie (model), Rserie max, Rserie app (apparent), Gamma, muGamma, IoRef, muVoc, muVocSpec, muPmpp, muPmppReq.
  - For a-Si and CdTe: d²mutau and the spectral-correction switch (Loughborough correlation, "Not suited for CdTe").
  - Secondary parameters: BRev (reverse characteristic) and the number of bypass diodes.

##### b) Determining the parameters (determination-of-parameters.html, rseries-and-rshunt-determination.html, parameters-besides-datasheets.html)

**With a full measured I/V curve**
1. Rsh is the inverse slope at Isc and is kept fixed.
2. The equations are written at the 3 points (0, Isc), (Vmp, Imp) and (Voc, 0).
3. Rs is scanned from 0 up to **RsMax**, the largest value that still has a solution.
4. The Rs that best fits the measured curve is kept. For good measurements the RMS error "is often as low as 0.4% of Isc".

**With the datasheet only**
- Default Rsh = Vmpp/(0.2·(Isc − Impp)).
- Default Rs: **chosen so that the relative efficiency at 200 W/m² is −3 % for crystalline modules** (default since 6.26).
- Default Rsh(0) = 4 × Rsh for crystalline and 12 × Rsh for thin film.
- RshExp = 5.5. The help also writes −5.5 and says it "should not be modified".
- Default procedure, applied when a .PAN file has no Rs or Rsh, or via the "default" buttons:
  1. Set Rsh to its default.
  2. Fit Rs to reach −3 % at 200 W/m².
  3. If impossible, raise Rsh, up to 4×.
  4. If still impossible, raise Voc by a small fraction of a percent.
  5. Check that μPmpp at −10 °C is not positive; if it is, increase RsMax again.

**Constraints**
- RsMax grows with Rsh only up to saturation.
- RsMax falls linearly and fast with the Vmp/Voc ratio: −50 % for +3 % in the ratio. **Vmp/Voc above about 84 % should be avoided**; PVsyst suspects some datasheets lower Voc to inflate the fill factor.
- When Rs approaches RsMax, IoRef becomes very small and γ can drop to about 0.92. Io is floored at 0.01 pA, which breaks the low-temperature behaviour (μPmpp changes sign).

**Laboratory 5-parameter fits (IEC 61853, 23 points)**
- PVsyst considers fitting Rs, Rsh, RshExp, Rsh0 and muGamma (or muPmpp) on 23 points ill-posed.
- Reasons given: measurement uncertainty, the non-linearity of the equations, averages over 3 modules, and the dependence on STC values.
- Such fits often give aberrant results, such as RshExp of 10-15.
- PVsyst's database method instead keeps RshExp, Rsh0 and muGamma at standard values and fits only Rs, possibly with Rsh, to the low-light points at 25 °C.

**History of the default Rs** (rseries-determination-history.html)

| Versions | Default rule |
|---|---|
| V5 | γ fixed at 1.30 (mono) / 1.35 (poly); known to underestimate yield |
| V6 to 6.25 | γ = 1.05 / 1.10 (from Sandia outdoor data on about 100 modules) |
| Since 6.26 (July 2014) | −3 % at 200 W/m² |

- Default γ for thin film, editable in Hidden parameters: a-Si 1.4, a-Si tandem 2.8, a-Si triple 4.2, CdTe 1.5, CIS 1.5, AsGa 1.3.
- High-efficiency and twin half-cut modules with low Rs may fall below −3 % at low light.

##### c) Rshunt exponential, low light and temperature

- **Rshunt as a function of irradiance:**
  - Rsh_eff = RshBase + (Rsh(0) − RshBase)·exp(−RshExp·G/Gref), with RshBase = (Rsh_STC − Rsh(0)·e^(−RshExp))/(1 − e^(−RshExp)).
  - RshExp = 5.5 for all technologies (about 3 for CdTe).
  - Rsh(0)/Rsh = 12 for amorphous and CdTe and about 4 for c-Si and CIS (flash tests suggest 8-10, with little effect).
  - A small tool fits Rsh(Gref) and Rsh(0) to several measured Rsh values: right-click to add points, then "Fit" (thin-film-modules-fit-on-input-values-of-rshunt.html).
- **How the resistances affect low light:**
  - Rs causes an Rs·I² loss. At equal STC power, a module with higher Rs has *better* relative low-light efficiency.
  - The exponential Rsh "recovers" low-light efficiency below about 400 W/m².
  - Raising Rsh, Rsh(0) or Rs all raise the low-light efficiency.
- **Temperature correction:**
  - γ = γ0 + muGamma·(Tmod − Tref), with muGamma set to reproduce the specified muPmpp.
  - Since 6.26 the target is the *secant* slope between 25 and 45 °C (before it was the tangent at 25 °C). This lowered the annual temperature loss by about 0.1-0.2 %.
  - The correction is small for c-Si (≤ 0.03-0.04 %/°C) and up to 0.12 % for thin film.
  - muVoc is a *result* of the model: the model cannot match both the specified muVoc and muPmpp.
  - For the maximum-voltage sizing check (Voc at Tmin), the manufacturer's **muVocSpec** can be stored in the .PAN file and selected in Project settings.
  - muVoc and muPmpp themselves vary with temperature. Curves can be discontinuous at very low temperature because of the Io floor.
- **Low-light studies and the LowLight analysing tool** (module dialog, "Additional data > Low-light data"):
  - Input:
    - IEC 61853 operating points: 1100, 1000, 800, 600, 400, 200 and 100 W/m² at 25 °C usually suffice.
    - Each point is defined as relative efficiency only, as Pmp only, or as full (Isc, Voc, Imp, Vmp) data.
    - An Excel paste is accepted: the top-left cell must read "Low-light data"; GRef, TRef and Pmp are mandatory, and Voc enables linearisation.
    - The measured STC point must be redefined with the lab's values.
  - Actions:
    - "Linearize Isc/G" corrects filter calibration errors; the help's example is +4 % at 100 W/m², moved to GRef of about 104 W/m².
    - "Optimize Rs" minimises the RMS error, about 0.5 % in the example.
  - The fitted low-light *curve* is then transferred to the "parent" datasheet module by refitting its Rs; the resistances themselves are not copied.
  - Relative efficiency = (Pmpp/Pmpp(1000)·1000/G) − 1.
  - Module efficiency = Pmpp/(G·area), using the gross area including the frame; the help notes several possible definitions.

##### d) Spectral corrections (index.html, firstsolar-spectral-correction.html, spectral-correction.html)

- **Not part of the one-diode model.** It is applied according to technology:

  | Technology | Spectral correction | Activation |
  |---|---|---|
  | Amorphous | CREST (Loughborough) correlation on air mass and Kt | Automatic when spectral correction is on |
  | c-Si and CIS | Neglected ("extremely weak") | - |
  | Modules from the Sandia database | Sandia spectral correction on air mass only, applied to the beam | Automatic when spectral correction is on |
  | CdTe | **FirstSolar model** (Lee & Panchula, IEEE PVSC 2016) | Optional, off by default, in "Detailed losses" |

- **FirstSolar model:**
  - It is a factor on effective irradiance computed from air mass and precipitable water. Air mass comes from altitude and sun position; precipitable water comes from the weather file or is estimated from relative humidity (Gueymard 1994).
  - Coefficient sets:
    - mono-Si, poly-Si, a-Si, CIGS and CdTe, with "pvlib.atmosphere" given as the source;
    - First Solar "Series 4-1 and earlier" and "4-2 and later".
  - **Since 8.1.6** custom coefficients are accepted, and the factor is plotted in the dialog and the report.
  - PVsyst says it "assumes no responsibility" for this model, which has not been validated independently.
  - The coefficient set follows the module technology unless overridden.
  - When used, it appears in the report and as "spectral losses" in the loss diagram.
- **Amorphous APE model:**
  - UF (utilisation factor) is a quadratic function of the Average Photon Energy (APE). APE is parametrised on air mass and Ktcs, the clear-sky-normalised clearness index, which PVsyst computes with its own clear-sky model.
  - UF ranges from about 0.5 (APE 1.45 eV) to 0.65 (APE 1.70 eV) and is renormalised to AM 1.5, i.e. APE 1.6 eV.
  - For c-Si, UF is 0.81-0.91, but applying the correction did not improve the model.

##### e) Sandia model option (sandia-model.html)

- About 40 parameters from outdoor measurements (SAND2004-3535). The Sandia database has about 500 entries but only about 100 measured modules.
- The model gives 5 points of the I/V curve. **PVsyst builds a one-diode curve through these 5 points** at each (G, T).
- If an equivalent Sandia module exists, it is listed in the module's remarks and the user may choose either model.
- A "Sandia-Diode compare" button compares the two, and the one-diode parameters can be adjusted to match Sandia.
- Agreement is good for c-Si and poor for amorphous modules, for reasons PVsyst does not fully understand.

##### f) Thin film and new technologies (model-for-thin-film-and-other-new-technologies/)

- **Research basis:**
  - A CUEPE / University of Geneva project funded by SIG-NER: 6 modules with I/V curves every 10 min for 3 months.
  - Even the c-Si reference module (Siemens M55) needed the Rsh exponential correction: the Pmax MBE fell from 6 % to 1.1 %.
  - The CIS module fitted very well (Pmax MBE 0.0 %, RMSE 2.1 %).
- **Corrections for amorphous modules:**
  1. The Rsh exponential.
  2. **Recombination losses** (Mertens et al. 1998):
     - Irec = Iph·di²/[μτeff·(Vbi − (V + I·Rs))], with Vbi ≈ 0.9 V and di²/μτeff ≈ 1.4 V.
     - The full equation becomes I = Iph − Iph·(di²/μτeff)/(Vbi − (V + I·Rs)) − Io·[exp(…) − 1] − (V + I·Rs)/Rsh.
     - On the SHR-17 module the Voc RMSE fell from 3.3 % to 0.7 %.
     - The d²mutau parameter should be about 80-90 % of its maximum.
  3. The CREST spectral correction.
- PVsyst does not model the Staebler-Wronski initial degradation; results apply to modules stabilised after 2-3 months.

##### g) Reverse characteristics (reverse-characteristic-of-a-cell.html, pv-module-reverse-behaviour.html, pv-module-reverse-lowvoltage.html)

- **Cell model:**
  - The reverse current is quadratic in voltage: IRev = Iph + aRev·(V + Rs·I)² for V < −Rs·I. The parameter is called BRev in the module dialog.
  - Avalanche starts around −30 V, but heat dissipation becomes destructive earlier.
  - The tool shows three cases: a single cell, a module without bypass diode, and a module with bypass diodes (about 0.7 V per diode).
- **IBC modules** (cells acting as their own bypass, about 2.5 V reverse):
  - Model: Irev = Isc + Arev·Vrev².
  - Example: Arev = 1100 mA/V² gives −2.5 V at +10 A. It is set in "Additional data > Secondary parameters".
  - The help states it is used in the "Module Layout" electrical-shading calculation, and expects no dramatic gain.
- **Inconsistency in the help (flagged):** the older cell page says reverse behaviour is used only in the educational tools, not in the simulation. The IBC page says Module Layout uses it.

##### h) Module structure (pvmodule-structure/)

**Bifacial modules**
- The bifaciality factor φ follows IEC 61724-1: the ratio of rear to front nominal efficiency, always below 1 (claims 0.8-0.9).
- Rear irradiance × φ is added to the front irradiance before the one-diode model. The same model is used for both sides.
- The rear-side IAM is that of "normal glass".
- φ is also used in the bifacial performance ratio.

**Cell sizes**
- Cells evolved from 156 to 166, 182 and 210 mm; the largest are used as halves or thirds. Module currents rose from below 10 A to 15-16 A.
- Cell size is used mainly for the bottom-cell width in electrical shading (half a cell for twin half-cut modules in portrait).
- Determination criteria: 0.56-0.57 V per cell, number of diodes, submodule layout, about 50 mm for edges, and cell area at 88-91 % of the module area. The value can be overridden by hand.

**Submodules and bypass diodes**
- A submodule is a group of cells protected by one diode, at most about 20-24 cells (3 diodes for 60/72 cells, 4 for 96).
- **The submodule is the basic unit of the electrical-shading calculation:** its I/V curve is almost the same however many of its cells are shaded.

**Submodule layouts in the .PAN file**

| Layout | Notes from the help | Module Layout calculation |
|---|---|---|
| In length | Classic 36/60/72-cell modules | Supported |
| In width | 96-cell modules | Supported |
| Twin half-cut cells | NCelS = 60 or 72 and NCelP = 2; diodes shared by pairs of submodules | Supported (fully since V7) |
| Twin third-cut cells, 5 rows | Cells in series divisible by 5 | Approximation |
| Twin third-cut cells, 6 rows | - | Not listed as supported ("All other structures are not suited") |
| Twin half-cut cells, 4 rows | Narrow modules, 2 diodes | Unclear: the help lists "twin half-cut" as implemented without distinguishing the 4-row variant [unverified] |
| Shingled | - | Not supported (stated explicitly) |
| Exotic | - | Not supported (stated explicitly) |
| Thin-film strips (in length or in width) | One diode; strips should be perpendicular to row shading, which avoids electrical shading loss | Not listed as supported |

**Twin half-cut modules in portrait**
- The upper half keeps working when the bottom is shaded.
- In unlimited sheds, approximate this by doubling the strings across the row height and halving the cell size (about 78 mm).
- In the "according to strings" mode, half-module rectangles are valid only for a single string of portrait modules.
- Busbar loss is divided by 4, which raises STC power but reduces the relative low-light performance. They are also more robust to cracks.

**Model graphs** (pvmodule-model-graphs.html)
- Families of curves: I/V, P/V, efficiency against irradiance, and efficiency against temperature. They can be parametric in G, T, Rs or Rsh.
- The "Module temperature according to irradiance" option uses Tmod = Tamb + (1/U)·Ginc·α·(1 − effic) and shows Vmpp nearly constant in real conditions.

**IT relevance:**
- The one-diode model, the default Rs/Rsh rules and the muVocSpec option are **high** for every project. Italian designers often have only datasheets, so the −3 % at 200 W/m² default governs low-light yield; Voc at Tmin governs string sizing.
- Half-cut and bifacial module structure: **high** (dominant module types) (analysis).
- FirstSolar spectral correction: **medium**, for CdTe utility plants (analysis).
- Thin-film recombination, amorphous spectral and Sandia: **low** for most Italian projects, since crystalline modules dominate (analysis).
- Reverse characteristics: **medium**, through Module Layout on rooftops with chimneys and dormers.

**Meridiana note:**
- pvlib's `calcparams_pvsyst` already implements Iph(G, T), Io(T, EGap), γ(T) through mu_gamma, and the Rsh exponential (R_sh_exp = 5.5).
- Meridiana must write itself:
  - the PVsyst default-parameter procedure (Rsh default, Rs at −3 % at 200 W/m², RsMax, the Voc nudge, the −10 °C check);
  - the muGamma fit on the 25-45 °C secant;
  - the LowLight tool;
  - the submodule and cell-size logic.
- pvlib's `bishop88` offers a reverse-bias breakdown model for electrical shading. It is a different formula from PVsyst's quadratic BRev (see section 3).

#### 1.10.4 Grid inverter physical model

Sources: https://www.pvsyst.com/help/physical-models-used/grid-inverter/index.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-model-efficiency.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-model-input-and-output.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-model-multi-mppt.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-operating-limits.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-pnom-as-f-voltage.html , https://www.pvsyst.com/help/physical-models-used/grid-inverter/subhourly-clipping-correction.html , https://www.pvsyst.com/help/component-database/grid-inverters/grid-inverters-main-interface/grid-inverters-output-parameters.html , https://www.pvsyst.com/help/glossary/pv-components/inverter-power-overcharging.html , https://www.pvsyst.com/help/glossary/pv-components/inverter-voltage-limits.html , https://www.pvsyst.com/help/project-design/results/simulation-variables-grid-system.html (OND file parameters: see 1.7.3)

- **Efficiency: four definitions.** (1) one curve η = f(P_in) with up to 8 points; (2) one curve built automatically from max + EURO or CEC efficiency and Pthresh; (3) **three curves at three input voltages**, up to 8 points each; (4) three automatic curves. The transfer function Pout = f(Pin) is linearly interpolated between points; with 3 curves the simulation does a **quadratic interpolation in input voltage** at every step.
- **Automatic profile algorithm.** AC output ∝ DC power minus the Pthresh "internal consumption"; quadratic resistive loss (R·I²) of output circuitry; the curve must match the specified maximum value at a DC power "arbitrarily fixed" at 60 % of Pnom; Pthresh must exceed 0.5 % of Pnom; the effective Pthresh (slope) is fitted to the EURO/CEC efficiency; the resistive share is set by a normalised resistance factor (default 3.0) proportional to max − EURO difference.
- **MPPT tracking loss.** Not modelled explicitly; assumed included in the manufacturer's efficiency profile (sub-hourly variability is not in hourly data).
- **Input side.** MPP tracking within VmppMin-VmppMax. Outside the window: "Limitation" mode clips the voltage (losses IL_Vmin, IL_Vmax) or "Cut" mode stops (old inverters). Start when MPP power > **Pthresh** (loss IL_Pmin, typically < 0.1 %/yr; 0.5 % Pnom ≈ 5 W/m²); no voltage threshold. Above PnomDC (= PnomAC/η): limitation by moving to higher voltage (IL_Pmax), or "Cut" / "Cut up to evening" for very old devices. **Current limit** given as "Maximum current per MPPT" or derived from VminPnom: Imax = PnomDC/VminPnom (IL_Imax). VmppNom is a "weak" sizing condition. VAbsMax must never be exceeded. Manufacturer array limits (max ISC, max array power) have "no real physical basis" but may be contractual.
- **Current vs power limit.** Current-limit losses are usually masked by power overload (the operating point moves to higher voltage/lower current); they appear only with low array voltage (few modules in series).
- **Pnom as function of voltage.** Datasheet curves (points B = VmppMin, C = minimum voltage for Pnom, D = VmppMax, E = VAbsMax; VmppMax/VAbsMax ≈ 85 %) are approximated: if the I/V curve passes right of D there is no valid operating point and **the inverter stops** (warning at each such step), whereas the datasheet would allow operation on D-E; at low voltage, B-C is treated as a current limit (loss booked as current loss). Effect "marginal" in well-sized systems; future improvement announced.
- **Pnom as function of temperature (OND output parameters).** Optional PMax with the maximum temperature for PMax and the temperature at which output falls back to PNom, plus two further derating levels at high temperature ("Allows overpower" requires a PMax value). Reference inverter temperature: ambient; ambient + shift; or fixed + linear increase with irradiance (indoor installations).
- **Output side.** PnomAC = maximum power to the grid; VnomAC used to compute AC wiring current/losses (the max output current is not used); grid voltage not simulated, so no voltage-dependent limits; output is active power (reactive: 1.1.9.8); external MV transformer defined in losses (1.1.13); auxiliaries (fans, from a power threshold) and night consumption from the OND become defaults in Detailed losses; transformer vs transformerless (transformer ≈ ≥ 1 % loss; transformerless "incompatible" with amorphous modules).
- **Multi-MPPT, unbalanced inputs, master/slave:** see 1.1.9.5-1.1.9.6 (N identical sub-inverters by default; per-input Pnom since 6.33; unbalanced main/secondary inputs re-shared at simulation time).
- **Sub-hourly clipping correction (since 8.0).** Problem: hourly-average I/V curves miss clipping caused by intra-hour fluctuations (both when the hourly mean is below the threshold but minutes exceed it, and vice versa). Model: minutes within an hour are re-ordered by irradiance and represented by **two linear segments** above and below the hourly mean; per hour only max GHI, min GHI and the number of minutes above/below the threshold are stored (Villoz, Wittmer, Mermoud, Oliosi, Bridel-Bertomeu, WCPEC-8, 2022, doi:10.4229/WCPEC-82022-4EO.2.2). 8.0: needs an hourly MET created from sub-hourly data with statistics. 8.1: applied automatically for hourly simulations with sub-hourly MET files and for resampled sub-hourly files; not applied to 1-minute simulations or to hourly 8.1 MET files. Output variable **ILPmxSH** ("Sub-hourly inverter clipping correction"), grouped with IL_Pmax in the loss diagram; can be disabled in advanced parameters (all projects). 8.1.5: 5/15-min Meteonorm synthetic files usable for this; 8.1.6: bug fix for files resampled from 1-minute data.
- **Simulation variables (inverter).** InvLoss, IL_Oper, IL_Pmin, IL_Pmax, IL_Vmin, IL_Vmax, IL_Imax (operating limits page), IL_Night, Syst_ON, EOutInv, EffInvB (threshold included), EffInvR (when operating).
- **Not to be confused** with stand-alone (battery) inverters: fixed DC input, output set by the load, cannot follow solar availability.
- **IT relevance:** high (every system). The three-voltage efficiency, PMax(T) and sub-hourly clipping matter most for high DC:AC C&I and utility plants.
- **Meridiana note (analysis):** pvlib's Sandia/ADR/PVWatts inverter models do not reproduce OND behaviour (operating-point displacement, 3-voltage curves, PMax(T)); Meridiana needs its own OND-faithful inverter model (see section 3).

#### 1.10.5 Battery physical model

Sources: https://www.pvsyst.com/help/physical-models-used/batteries/index.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/index.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/model-justification.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/open-circuit-voltage.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/operating-voltage.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/internal-resistance.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/battery-capacity.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/capacity-vs-discharge-rate.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/capacity-vs-temperature.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/state-of-charge.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/coulombic-efficiency.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/battery-efficiency.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/self-discharge.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/overcharging.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/operating-limits.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-model/battery-aging.html , https://www.pvsyst.com/help/physical-models-used/batteries/battery-technologies/index.html , https://www.pvsyst.com/help/glossary/pv-system/bess.html , https://www.pvsyst.com/help/release-notes/index.html (8.1.2, 8.1.4)

- **Scope.** Lead-acid and Li-ion only (no flow batteries, supercapacitors; NiCd "will probably not be implemented"). Battery file and database: see 1.7.5 (.BTR).
- **Design philosophy.** Deliberately simple, "explicit" datasheet parameters (technology, voltage, number of elements, nominal capacity, internal resistance, Faradic efficiency, ageing); secondary behaviours fixed per technology (Shepherd-type multi-parameter models rejected). Li-ion parameters fitted on a few manufacturers' curves; new batteries inherit secondary parameters from a cell of the same technology.
- **Structure.** Loss model + capacity model + ageing model. Controller: grid-connected storage is always **SOC-based**; stand-alone may be SOC- or voltage-based.
- **Voltage.** V = Voc(SOC) + ResInt·I (I > 0 charging). Voc linear in SOC around SOC = 0.5 (V_nom + α(SOC − 0.5)); quadratic deep-discharge drop below SOC ≈ 30 % (lead-acid) / 15 % (Li-ion) down to a minimum at SOC = 0. Temperature: −4 to −5.5 mV/°C per element for lead-acid; none on Voc for Li-ion (resistance corrected instead). Lead-acid adds a gassing voltage above the overcharge threshold. Polarisation not modelled.
- **Internal resistance.** Defaults: voltage drop of **40 mV at C10 (lead-acid)** and **16 mV at C10 (Li-ion)** (advanced parameters). Li-ion: Arrhenius temperature dependence (activation energy 30-40 kJ/mol; Lundgren 2016); exponential end-of-charge factor ResCorr = 1 + A·e^(−B(1−SOC)) above SOC 0.9 (≈ 15 at SOC = 1); similar correction below SOC 15 %. Lead-acid: temperature-independent.
- **Coulombic (Faradic) efficiency.** Applied to the charging current: ~97 % lead-acid; 96 % assumed for Li-ion (to approach 90-95 % energy efficiency); loss variable IBEffL.
- **Gassing (lead-acid).** I_gas = I0,gas·exp(Δ·dV_gas) with Δ ≈ 11.7 V⁻¹; dV_gas profile vs SOC from SOC 0.8; electrolyte consumption MGass.
- **Self-discharge.** Defaults 4 % (lead-acid) and 3 % (Li-ion) [time unit not stated in the text]; temperature profile (rises above 20 °C); applied **only in stand-alone systems**.
- **Capacity.** Nominal capacity always defined as **C10**; **Peukert** model with coefficient K (≈ 1.02 Li-ion; 1.12-1.13 lead-acid; lead-acid also via a rate profile, ~40 % C100/C10 vs ~4 % for Li-ion); temperature derating as a 5-point profile (Li-ion ≈ −20 % at −10 °C vs −40 % lead-acid). Capacity variation is "not a loss". Battery temperature options: fixed, fixed by month, ambient, average of ambient and a fixed value. Usable energy = nominal energy × allowed SOC range.
- **SOC (current definition).** ΔSOC = I·Δt / C_ref with C_ref = capacity at **C200** at reference temperature (constant), giving a robust energy balance; an *indicated* SOC = SOC − (1 − Capa/CapaRef) drives BMS events (end of discharge). Before this change (help: "Definition until PVsyst 8.1.0"), SOC was referred to the rate-dependent capacity (energy-balance drift issues); release notes 8.1.2 announce the updated battery model. In grid-connected systems, after an end-of-discharge event the battery inverter stays off until the next charging event.
- **Loss accounting.** EBatLss = EBatCh − EBatDis − ESOCBal; EffBatE = (EBatDis + ESOCBal)/EBatCh (meaningful only over long periods). Per-step order: overcharge loss (gassing / Li-ion ResInt rise), ohmic loss, Faradic loss, stored energy, self-discharge, ohmic loss on discharge.
- **Operating limits.** Lead-acid: design-time errors if charging faster than 2.5 h or discharging faster than 2 h (advanced parameters). Li-ion: min/max voltages never reached by the model; "Maximum current" from the datasheet used only for design warnings; minimum charge/discharge temperatures stored; maximum operating temperature not stored (not simulated).
- **Ageing.** *Static (calendar)*: effective age accumulates with Arrhenius factor (doubling per 10 °C above 25 °C, α = ln2/10); at the maximum calendar lifetime a **replacement** is triggered (does not reduce SOH). *Cycling*: SOH decreases by ΔN_cycle/N_cycle,max using the "cycles vs DOD" curve; a cycle = energy equal to Capa_ref·SOH·V_nom; end of life at SOH_EOL (typically 80 %) → replacement. Rate and temperature effects on cycle life are not modelled. Initial SOH and effective age can be set (pre-aged battery). Outputs: SOH, equivalent cycles, effective age (stand-alone variables also SOHBatt, AgeBatEff, NBatCyc, MGass). **Since 8.1.4 SOH reduces the capacity during the simulation**; before, "SOWcycle/SOWstatic" did not affect capacity.
- **Technologies (informative).** Li-ion device levels: cells (cylindrical/pouch/prismatic), modules and rack-mount modules, cabinets and racks, containers (not database components; defined as racks in series/parallel). Chemistries table (LTO 2.0 V, LFP 3.2 V, LMO 3.6 V, NMC, LCO, NCA) with qualitative properties; BMS and cell protections; lead-acid selection advice ("industrial and grid-connected systems ... always based on the Li-Ion technology").
- **IT relevance:** high for residential/C&I behind-the-meter Li-ion (LFP) storage economics (replacement year, SOH); lead-acid only for small off-grid cases.
- **Meridiana note (analysis):** this model is fully documented and datasheet-driven, so it can be re-implemented; pvlib has no battery model (section 3).

#### 1.10.6 Pump model

Sources:
- https://www.pvsyst.com/help/physical-models-used/pump-model-description/index.html
- https://www.pvsyst.com/help/physical-models-used/pump-model-description/pump-model-general-requirements.html
- https://www.pvsyst.com/help/physical-models-used/pump-model-description/pump-model-from-ip-and-flowr-as-fhead.html
- https://www.pvsyst.com/help/physical-models-used/pump-model-description/pump-model-from-fr-as-fpp-for-fixed-heads.html
- https://www.pvsyst.com/help/physical-models-used/pump-model-description/pump-model-from-head-and-p-as-ffr-fixed-u-or-speed.html
- https://www.pvsyst.com/help/physical-models-used/pump-model-description/pump-model-from-head-and-effic-as-ffr-fixed-u-or-speed.html

The system side of pumping (configurations, hydraulics, results) is in 1.3.

- **Variables:**
  - Up, Ip, Pp = Up·Ip: voltage, current and power at the pump.
  - Uc, Ic, Pc: values at the power converter input, if there is one.
  - FR: flow rate.
  - HT: total head = static head + dynamic head (friction, computed by the simulation from the flow rate).
- **Model structure:**
  - The pump is a surface Φ(Up, Ip, HT, FR) = 0 inside an operating domain. The domain is bounded by maximum voltage, power, current and head, and below by a head-dependent power threshold for non-zero flow.
  - Fundamental relations:
    - Ip = f(Up, HT), for the direct-coupling operating point;
    - FR = f(Pp, HT);
    - Pp = f(FR, HT), for sizing and efficiency.
  - The other relations come from numerical inversion, and threshold functions (power, voltage, current) are given as functions of head.
- **Phenomenological approach:**
  - There is no motor or pump physics: the model applies cubic interpolation between the given points and linear extrapolation to the domain limits.
  - General assumptions are used only when the data are too sparse.
  - It applies to the motor-pump assembly as a whole, without torque or speed.
- **Five accepted data sets:**

  | # | Data set | Typical use and assumptions |
  |---|---|---|
  | 1 | Ip and FR as f(Head) at fixed voltage | Positive-displacement pumps. With one voltage curve, efficiency is assumed constant with voltage (the help shows variations of about 15 % over 30-64 V); with two curves it is interpolated linearly. |
  | 2 | Pp and FR as f(Head) at fixed voltage | Equivalent to #1 |
  | 3 | FR as f(Pp) at fixed heads | Solar centrifugal pumps. **No I/V information, so a power converter is mandatory**; optional I/V data (Ip/Vp at 2 or more heads, or nominal V and I, ΔV/ΔI and ΔI/ΔH with linear assumptions) |
  | 4 | Head and Pp as f(FR) at fixed voltage or speed | Grid centrifugal pumps, using the "similarity laws" and a cubic-spline H(FR) |
  | 5 | Head and efficiency as f(FR) | Equivalent to #4 |

- **Similarity laws as printed:** FL1/FL0 = ω1/ω0; P1/P0 = (ω1/ω0)²; H1/H0 = (ω1/ω0)³. The textbook affinity laws are H ∝ ω² and P ∝ ω³, so the exponents look swapped in the help (analysis).
- **Validation:** a Solarjack SCS-160 pump (CIEMAT), modelled from 3 nominal points, fits well except at low flow.
- **General requirements:**
  - All 4 variables must be derivable from the other 3.
  - The I/V characteristic is needed for direct coupling.
  - The starting current peak needed by most positive-displacement pumps is listed as a requirement. The help does not say how the model represents it [unverified].
  - The model must cover centrifugal and positive-displacement pumps (piston, membrane or diaphragm, progressive cavity, rotating displacer) with AC or DC motors, including standard AC pumps on frequency converters.

**IT relevance: low and niche** (off-grid irrigation, livestock watering, remote sites) (analysis).

**Meridiana note:** this is phase 3. Nothing in pvlib covers it, so Meridiana would write the interpolation model and the hydraulic system itself.

### 1.11 Platform, files, validations and release notes

Sources: https://www.pvsyst.com/help/getting-started/requirements.html , https://www.pvsyst.com/help/validations/index.html , https://www.pvsyst.com/help/release-notes/index.html and the pages cited in each subsection.

#### 1.11.1 Platform, workspace, file formats, expert settings

**Requirements**
- PVsyst "runs only under Windows". Supported: Windows 8, 10 and 11, 32- or 64-bit, Home or Pro.
- It cannot be installed on Windows Server.
- Minimum hardware: 1 GB RAM, 2 GB free disk, a 1280×720 display, .NET Framework 4.7.2 and OpenGL 2.0.
- A licensed copy needs a correct system clock.
- The workspace must not sit on shared or remotely synced drives. The help names OneDrive, Google Drive and Dropbox.
- URL: https://www.pvsyst.com/help/getting-started/requirements.html

**Workspace and folders**
- The user data workspace defaults to `C:\Users\<user>\PVsyst8.1_Data`. It holds "every data created through PVsyst by the user: projects, PV components".
- It can be created, imported, exported as a backup, or switched.
- Folders named on various pages: `\Sites\`, `\Meteo\`, `\UserBatch`, `\UserHourly`, `\UserHourlyParams`, `\Templates`, `\UserRecycleBin`. Each format change in PVsyst's history got its own workspace folder (PVsyst6_Data, PVsyst640_Data, PVsyst660_Data, PVsyst680_Data, PVsyst8.1_Data).
- URLs: https://www.pvsyst.com/help/getting-started/file-organisation/index.html, https://www.pvsyst.com/help/getting-started/file-organisation/user-data/index.html

**File format**
- Up to version 6.39, all files were binary.
- From 6.40 they are text: `key=value` lines grouped in nested `PVObject_` blocks, each closed by "End of PVObject".
- From 6.80 they are UTF-8. The help names .PRJ, .VCi, .PAN and .OND as affected.
- PVsyst says the format is "intended for internal use only", gives no support for it, and says the files "should not be modified".
- URL: https://www.pvsyst.com/help/getting-started/file-organisation/user-data/format-of-pvsyst-files.html

**File extensions seen in the help**

| Extension | Content |
|---|---|
| .PRJ | Project |
| .VCi (i = 0..9, A..Z) | Variant, including its stored results |
| .CMi | Calculated variant with measured-data comparisons |
| .SIT | Site, with monthly data |
| .MET | Hourly or sub-hourly weather |
| .MEF | Weather import format |
| .PAN | PV module |
| .OND | Inverter |
| .BTR | Battery |
| .RLT | Controller saved from the universal controller |
| .LOD | Load template |
| .DAM | Measured-data file |
| `*_BatchParams_i.CSV`, `*_BatchResults_i.CSV` | Batch mode input and output |
| .RVT, .SFI | Result-variable and result files, named only in the CLI help |

Extensions for pumps, gensets and optimizers: [unverified].

**Export and import**
- `File > Export components` copies projects (all or selected variants, optionally with referenced files), components, weather files and shadings into a folder tree. A "Zip export folder..." button can compress it.
- PAN and OND files can also be exchanged with partners through `Files > Import or Export Components`.
- URL: https://www.pvsyst.com/help/getting-started/file-organisation/user-data/projects-and-pv-components/export-projects-and-components.html

**Hidden (advanced) parameters**
- Opened from `Settings > Edit advanced parameters`.
- Groups: Grid presizing, Stand-alone presizing, Pumping presizing, Presizing costs, System design parameters, Detailed simulation verification conditions, PV modules, Regulators and converters, Miscellaneous.
- Each value shows a modified flag and can be restored to its default.
- A change can apply to the session only or be saved permanently.
- PVsyst warns that "no validity checks" are made.
- URL: https://www.pvsyst.com/help/getting-started/hidden-parameters/index.html

**IT relevance: Medium.**
- Being Windows-only and refusing synced drives is a real limit for design offices. A cross-platform program can beat it here.
- Reading and writing PAN/OND (text PVObject format) is the key interoperability need. EPCs, manufacturers and lenders circulate these files [unverified: market practice, not stated by PVsyst].

#### 1.11.2 Validations

**Claims**
- "We are not aware of any third party validation measurements". Validation was done "in the context of the PVsyst software development".

**Studies cited**
- 1996, version 2: 7 Swiss grid-connected systems from 0.45 to 104 kWp, including sheds, roof and façade, mono, poly and a-Si.
  - Yearly accuracy "of the order of +/- 5%". Global accuracy about 2-3 % MBE, except amorphous modules.
  - Transposition and diffuse models were "the weakest link" (over 10 % differences on some datasets).
  - Array temperature error under 1 °C with k = 29 W/m²K.
- Geneva plants over 2-3 years: within ±5 %/yr.
- 2008, V4: a 10 kWp amorphous system, 1-2 % MBE over a year.
- Stand-alone systems and the battery model were "not validated" at the time.

**Uncertainty statements**
- Weather data is "usually known at 5-10%". Annual variability is about ±5 %.
- PVsyst recommends renormalising to actual weather before production warranties.

URLs: https://www.pvsyst.com/help/validations/index.html, https://www.pvsyst.com/help/validations/validations-of-old-versions-of-the-program.html

**IT relevance: Medium.** PVsyst's acceptance by lenders rests on habit more than on published validation. A new tool should publish open benchmarks, for example against PVsyst outputs and measured plants [inference].

#### 1.11.3 Release notes 8.0.0–8.1.7 (condensed)

The table concentrates on weather, components, economics, automation and other system types. Changes to orientations, the 3D scene, shading, losses and the simulation are cited in their own sections. Examples: 8.0.0 unlimited orientations and downloadable ground images in the 3D scene (1.1.2, 1.1.6); 8.1.5 PVCollada 2 (.pvc2/.pvz2) import (1.1.6); 8.1.7 faster simulation of projects with many sub-arrays (https://www.pvsyst.com/help/release-notes/index.html).

| Version (date) | Changes |
|---|---|
| **8.0.0** (7 Nov 2024) | PVsystCLI. Meteonorm 8.2. SolarAnywhere PXX and horizon import. Map choice of Bing or OpenStreetMap. NSRDB precipitable water. Sub-hourly irradiance for the clipping correction. AdvanSol, Sungo and Generic optimizers; Huawei SUN5000. Stand-alone sub-arrays. Pump-controller voltage warning. Module ageing split 80/20 (I/V). |
| 8.0.5-8.0.7 | Solcast free accounts lose TMY. Rserie lower limit for M12 cells. `T_LOL` recorded. Sungo optimizers. **PVGIS 5.3 API becomes the default** (TMY, time series, horizon). POA import diffuse fix. |
| 8.0.10-8.0.17 | Azure Maps. Economics provisions fixed. SolarAnywhere TGY choice. Economics: optimizers in costs, "Module degradation". SolarEdge heterogeneous strings. NSRDB PSM v4. AndSolar optimizers. **Power-shifting storage strategy** (8.0.17). |
| 8.0.20 | PDF tutorials for step-by-step, stand-alone and pumping. GTI tables apply albedo. |
| **8.1.0** (15 Apr 2026) | **Weather import assistant** with validation. **Sub-hourly simulation** (grid and stand-alone). **Meteonorm 9** DLL with offline horizon. Transient thermal model. Sub-hourly Perez coefficients. New GHI→DHI model. **NASA POWER API**. Solar constant 1361 W/m². CSV time series for grid limitation, soiling and power shifting. Huawei optimizers. Better Hay reverse transposition. |
| 8.1.2 | Albedo CSV time series. Battery model update. Genset trigger fix. |
| 8.1.4 | ANE-NEDO API. **New default variability model** (GEBA). SOH reduces battery capacity. GHI computed when missing. Sub-hourly batch. |
| 8.1.5 | 5- and 15-min Meteonorm synthetic files plus resampling. Multi-year CSV split per year. NSRDB MSG and Polar. OPEX scheduling. Clear-sky GHI and DHI export. Minimum T warning against the voltage limit. Huawei more than 2 strings per MPPT. |
| 8.1.6 | System unavailability CSV. Diffuse coefficients refitted. Meteonorm 9.0.10. Fix of DHI shifted to the afternoon in GHI-only imports. Legacy import removed. |
| 8.1.7 (30 Sep 2026) | Predefined sub-hourly time steps. Faster multi-subarray simulation. |

URL: https://www.pvsyst.com/help/release-notes/index.html

#### 1.11.4 Takeaways for Meridiana (analysis, not PVsyst documentation)

1. **Interoperability first.** Read and write `.PAN` and `.OND` (text `PVObject_` blocks, UTF-8), the PVsyst standard weather CSV, and the time-series CSV form. Keep PVsyst's parameter names (Rsh(0), RshExp, Gamma, muGamma, IAM b0, Brev, Pthresh, Vmin_Pmax...) so users can cross-check results.
2. **Weather.** PVGIS (TMY, hourly series and horizon), NASA POWER and the PVsyst-format CSV cover the free needs for Italy. Meteonorm synthetic generation is proprietary.
   - Copy the 8.1 assistant's UX: auto-detected separator, site from coordinates, live conversion, green/orange/red QC.
   - Copy its documented QC thresholds: range, KTcs, BSRN ERL/PPL and K-tests.
   - Copy its gap-filling rules and its DST and time-shift tools.
3. **Database.** PVsyst's library is manufacturer-fed through an Excel template and has no online update. Meridiana can combine PAN/OND import with open libraries. Add favourites, obsolescence flags and an "unverified data" badge.
4. **Economics and P90.** Both are formula-level features: loans, depreciation, tariffs, LCOE, NPV, IRR, payback, and Gaussian quadrature with the default variability model. They are cheap to reproduce. Add Italian scheme templates, which PVsyst lacks.
5. **Automation.** PVsyst batch is limited (one fixed orientation, yearly outputs), and the CLI is a paid, Windows-only subscription. A free Python API and CLI with full-parameter sweeps would be a clear advantage.
6. **Phase 3.** Stand-alone, pumping and DC-grid systems, and the measured-data module. They are documented well enough to replicate later: the battery hyperbola ageing, the controller hysteresis, the pump black-box curves and the borehole drawdown model.

### 1.12 Relevance for an Italian designer: summary by project segment

This table is analysis. It condenses the "IT relevance" notes of sections 1.1 to 1.11. The typical cases in the second column are assumptions of this report, not survey data. Italian rules (CEI 0-21 / 0-16 connection rules, CEI 64-8 cable sizing, fire-safety guidance for PV on roofs) are named but were not checked in this research.

| Segment | Typical Italian case (assumption) | PVsyst functions that matter most | Seldom needed |
|---|---|---|---|
| Residential, about 3–20 kW | Pitched roofs with 1–3 faces, often east and west on one inverter; chimneys and dormers; hybrid inverter with a battery; self-consumption | PVGIS weather and horizon (1.6.2, 1.1.5); 3D near shading with the electrical effect (1.1.6–1.1.8); two orientations on one MPPT (1.1.2.5); string sizing at TMin (1.1.9.3); PAN/OND (1.7); load profiles from meter data and self-consumption (1.1.11, 1.1.12); storage, which PVsyst models only as AC-coupled (1.1.12.2); optimizers (1.1.10); Italian report (1.1.15.2); economics (1.1.16) | Trackers, bifacial, MV transformers, P50/P90, auxiliaries |
| Commercial and industrial rooftops, about 20 kW to a few MW | Flat roofs with south rows or east-west domes; industrial sheds with skylights; LV or MV connection; export limits | Sheds and domes with mutual shading (1.1.2.2, 1.1.2.7); zones with exclusion areas (1.1.6); Module Layout electrical shading, up to 5 MWp by default (1.1.8); DC:AC sizing (1.1.9.4); multi-MPPT string inverters (1.1.9.5); export limitation (1.1.9.9); AC wiring and MV transformer when MV-connected (1.1.13.3, 1.1.13.4); self-consumption (1.1.12); PR and PR guarantee (1.1.15.4, 1.1.15.5); economics (1.1.16) | Trackers, pumping, stand-alone |
| Ground-mounted and agrivoltaic, about 1–100 MW | Fixed rows or single-axis trackers, often on hilly terrain; bifacial modules; MV or HV connection; bank financing | Trackers and backtracking (1.1.2.2–1.1.2.4); topography import (1.1.6); bifacial 2-D model (1.1.3); partition-based electrical shading (1.1.8); transformers, auxiliaries, unavailability, power factor, grid limitation (1.1.13, 1.1.9.8, 1.1.9.9); P50/P90 (1.1.17); ageing tool (1.1.14.4); sub-hourly clipping correction (1.10.4); batch and optimisation scans (1.1.20, 1.1.14.9) | Self-consumption, optimizers |
| Off-grid niche | Mountain huts, telecom sites, irrigation | Stand-alone and pumping systems (1.2, 1.3), batteries (1.10.5) | Most grid-side functions |

Gaps PVsyst leaves for Italian users are noted in the sections cited above:
- no Italian load profiles; the templates are German BDEW (1.1.11);
- no Italian climate datasets among the known import formats (1.6.3);
- no Italian incentive schemes in the economics (1.1.16);
- generic ampacity rules instead of CEI-UNEL tables (1.1.13.3);
- no slope-aware backtracking for hilly sites (1.1.2.4).

---

## 2. Aurora Solar: feature inventory and UX patterns

**How this section was researched (21/10/2026).** Official sources only: Aurora product pages (aurorasolar.com, helioscope.aurorasolar.com) and the Aurora Help Center (help.aurorasolar.com). The Help Center HTML pages return HTTP 403 to automated fetchers, so the articles were read through the Help Center's public read-only JSON endpoint (`https://help.aurorasolar.com/api/v2/help_center/en-us/articles/<id>.json`), which serves the same article bodies. The citations below give the normal human-readable article URLs. Most articles were updated in 2026. Anything that no official page confirms is marked **[unverified]**. Quotes are kept short.

Aurora is a cloud (browser) platform aimed mainly at **residential and small commercial rooftop sales and design**, with a strong US focus (NEC, AHJ, utility rates, US incentives). European coverage exists (imagery, LIDAR, Solcast weather, load profiles for DE/ES/FR, an SLD editor offered only to European tenants, UK MCS), but **no Help Center article mentions Italy**: a search for "Italy" returned zero results.

---

### 2.1 Product overview and modes

| Item | What Aurora offers | Sources |
|---|---|---|
| **Sales Mode** | Simplified, sales-rep-facing workspace. Aurora AI roof, automatic panel fill towards a target offset (default 100 %), automatic inverter choice (aims at DC:AC **1.2** with the fewest inverters), AutoStringer running in the background at "Finalize", live production update as each panel is toggled, storage, financing, web/PDF proposals. | [Designing in Sales Mode section](https://help.aurorasolar.com/hc/en-us/sections/12223289094931-Designing-in-Sales-Mode), [Inverters and Optimizers in Sales Mode](https://help.aurorasolar.com/hc/en-us/articles/26240805636755-Inverters-and-Optimizers-in-Sales-Mode), [Live Panel Toggling](https://help.aurorasolar.com/hc/en-us/articles/11973220458771-Live-Panel-Toggling) |
| **Design Mode** | A full CAD environment: SmartRoof, roof faces, obstructions, trees, LIDAR, irradiance maps, panels, stringing, storage, SLD, simulation, exports. The marketing page says you can "create, edit, and simulate your system design all from the same place". | [Design Mode page](https://aurorasolar.com/design-mode/), [Design with Aurora: A to Z guide](https://help.aurorasolar.com/hc/en-us/articles/21240604594963-Design-with-Aurora-A-to-Z-guide) |
| **Three ways to build the site model** | (1) Manual: SmartRoof or Roof face. (2) **Expert Design Service**: Aurora's own modellers build it in about 3 h (about 30 min expedited), with Nearmap HD included. (3) **Aurora AI**: automatic detection from HD imagery + LIDAR. | [3 Ways to model a roof](https://help.aurorasolar.com/hc/en-us/articles/21016351139859-3-Ways-to-model-a-roof) |
| **Aurora AI** | AI SmartRoof / AI Roof faces (roof models "in under 15 seconds"), AI Trees (about 30 s), AI Obstructions. Sold as an add-on. The help pages call the eligible plans "Custom Plans", "Business Plans" or "Enterprise", depending on the article. | [Aurora AI in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/8172307851411-Aurora-AI-in-Design-Mode), [How to use AI Tree Detection](https://help.aurorasolar.com/hc/en-us/articles/52672750497299-How-to-use-AI-Tree-Detection), [Obstructions](https://help.aurorasolar.com/hc/en-us/articles/44272536242067-Obstructions) |
| **Other modules** | Plan Sets service and Instant Plan Sets (US), Contract Manager (Docusign), financing integrations, storage, heat pumps and "energy optimizations", drone mapping, Milestones (design snapshots), Sync API and partner apps (racking, site survey, utility data). | [Help Center categories](https://help.aurorasolar.com/hc/en-us/categories/360004751574-Design), [Milestones in Aurora](https://help.aurorasolar.com/hc/en-us/articles/33070484271123-Milestones-in-Aurora) |
| **Commercial / large projects** | Inside Aurora Design Mode there are commercial-only tools: **Walkway (K)** and **Fill Zone (Z)**. A commercial SmartRoof defaults to a flat roof. Aurora's dedicated commercial product is **HelioScope** (Folsom Labs, acquisition announced August 2021). HelioScope covers rooftop, carport and ground-mount arrays plus storage. Its plan limits are 1.25 MWdc (Basic), 5 MWdc (Pro, which adds LIDAR, AI obstruction detection, independent tilt, P90/P95/P99) and 30 MWdc (Enterprise, which adds **single-axis trackers** and **export to PVsyst**). HelioScope also accepts uploads of **PAN files and of OND files for string inverters**; the files must come from PVsyst 6.4 or later. It claims "accuracy within 1% of PVsyst". | [Keyboard Shortcuts (System Design)](https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design), [SmartRoof Best Practices](https://help.aurorasolar.com/hc/en-us/articles/360034501014-SmartRoof-Best-Practices-and-Tips), [Aurora blog: Folsom Labs](https://aurorasolar.com/blog/better-together-aurora-solar-welcomes-folsom-labs/), [HelioScope pricing](https://helioscope.aurorasolar.com/pricing/), [HelioScope product](https://helioscope.aurorasolar.com/product-2/), [HelioScope: upload modules/inverters](https://help-center.helioscope.com/hc/en-us/articles/8536001728019-Upload-New-Modules-Inverters), [HelioScope: OND upload](https://help-center.helioscope.com/hc/en-us/articles/8644909281811-How-to-Upload-Inverters-via-OND-Files), [HelioScope: single-axis tracker workaround](https://help-center.helioscope.com/hc/en-us/articles/27531451942035-Single-Axis-Tracker-Modeling-Workaround) |
| **Pricing (official page)** | **Basic** $159 per user per month ($135/month billed annually): proposals, HD imagery, on-demand site models. **Premium** $259 per user per month ($220/month billed annually): adds LIDAR-assisted modelling, bankable shade reports and battery modelling (backup, self-consumption, arbitrage). **Enterprise** (custom, per project): adds AI site models, drone mapping and APIs. Add-ons include plan sets, PE stamps and expedited site models (standard site models "start at $9.99"). Some Help Center articles use other plan names ("Build, Grow, and Scale", "Foundation"). | [Pricing](https://aurorasolar.com/pricing/), [Drone Mapping](https://help.aurorasolar.com/hc/en-us/articles/48586751929235-Drone-Mapping) |

---

### 2.2 Site modelling

**Imagery**
- **Imagery sources:** Google Maps, **Google Maps HD**, Bing, **Nearmap HD** (add-on), **EagleView**, **Vexcel** (high-resolution 2D for Europe, introduced "to increase the accuracy of designs in Germany"), and custom uploads, including drone images.
- **Google HD resolution:** from 25 cm down to 10 cm.
- **Priority order:** an admin sets the order in which sources are tried. When one is missing for a site, Aurora falls back to the next one.
- **Map area:** the map image area can be resized.
- **Split View** shows the Map (angled, rotatable view) or Street View beside the model, to judge pitch, obstructions and shade.
- Sources: [Google HD and 3D imagery](https://help.aurorasolar.com/hc/en-us/articles/360025356834-Google-HD-and-3D-imagery), [Vexcel 2D and 3D Imagery](https://help.aurorasolar.com/hc/en-us/articles/17388462525075-Vexcel-2D-and-3D-Imagery), [Map Imagery Selection](https://help.aurorasolar.com/hc/en-us/articles/12110730000915-Map-Imagery-Selection), [Design settings – Account configuration](https://help.aurorasolar.com/hc/en-us/articles/4406930393875), [SmartRoof Best Practices](https://help.aurorasolar.com/hc/en-us/articles/360034501014-SmartRoof-Best-Practices-and-Tips).

**LIDAR**
- **Sources:** Aurora LIDAR, Google 3D (High or Medium) and Vexcel. Aurora picks the source automatically from the coverage area, and the user can switch source.
- **Coverage:** "many parts of the United States, Europe, and select international locations". A point-density map is provided: ≥ 4 is "good" and ≥ 10 "excellent" (the units are not stated in the text). Italy is not mentioned.
- **Viewer options:** Mesh or Point Cloud. The "Textured" toggle colours the data by irradiance or by map imagery. X/Y/Z offset fields align the data. A source date is shown.
- **"Fit Buildings to LIDAR"** fits the roof model to the data automatically.
- **Roof Face tool:** height and pitch adjust automatically to LIDAR when data is available. This is the closest thing to an "auto-pitch" (that exact term is not used).
- **Trees** are fitted to LIDAR automatically: Tree Height and Crown Height are set from the LIDAR points.
- Sources: [LIDAR](https://help.aurorasolar.com/hc/en-us/articles/225074608-LIDAR), [Where is LIDAR available in Aurora?](https://help.aurorasolar.com/hc/en-us/articles/115012796388-Where-is-LIDAR-available-in-Aurora), [Draw Roof Face](https://help.aurorasolar.com/hc/en-us/articles/360015777974-Draw-Roof-Face), [Fit Trees to Lidar](https://help.aurorasolar.com/hc/en-us/articles/360050816674-Fit-Trees-to-Lidar).

**Drone mapping** (Enterprise-type plans)
- **Input:** 40–90 JPG photos (minimum 10) with 60–80 % overlap, or a video.
- **Processing:** "usually takes 15–20 minutes".
- **Outputs:**
  - a custom **LIDAR surface**;
  - a **3D mesh**, measurable with the 3D ruler;
  - a scaled top-down map image.
- An expert roof model can be requested from the drone data.
- Sources: [Drone Mapping](https://help.aurorasolar.com/hc/en-us/articles/48586751929235-Drone-Mapping).

**Automatic roof detection (Aurora AI)**
- **Inputs:** HD imagery and LIDAR, which are loaded first. If either is missing, the user gets a warning and must draw manually.
- **Two outputs:**
  - **AI SmartRoof**, which infers the inner faces and is edited as a whole roof;
  - **AI Roof faces**, which are independent faces and more reliable on complex roofs.
- **Speed:** a vendor report gives an average generation time of 10.05 s over about 8,500 runs, measured on Aurora's servers.
- **Accuracy:** the same report measures it only as "relative accuracy" of panel counts against human designers. The AI was as good as or better than a human, or within a narrow margin, about 76 % of the time.
- **Sales Mode:** residential only, and models all structures inside the property lines.
- Sources: [Aurora AI in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/8172307851411-Aurora-AI-in-Design-Mode), [Creating a site model using Aurora AI in Sales Mode](https://help.aurorasolar.com/hc/en-us/articles/12290612935699-Creating-a-site-model-using-Aurora-AI-in-Sales-Mode), [Aurora AI accuracy and speed (vendor report)](https://resources.aurorasolar.com/ai-aurora-solar-2023-report/review-of-aurora-ais-accuracy-and-speed).

**Manual roof tools**
- **SmartRoof (R).**
  1. Click the first node on a roof corner and make the second edge parallel to the roof.
  2. Orange dotted guides give **90° snapping**.
  3. Closing the outline creates a pitched roof (flat for commercial projects) and **automatically enters Edit Roof mode**.
  4. Click a face to open the **Edge & Face** panel. There you can set pitch, eave (edge) height and length, and unpitch a face (button or Delete).
  5. **Folds:** flat, pitched, or vertical (Dutch gable).
  6. **Dormers:** shed (1 slope), gabled (2) or hipped (3). A dormer automatically takes the azimuth of the roof slope. **Convert To Roof** turns it into an independent structure.
  7. Internal lines are corrected by changing pitch or eave height, or by dragging the outer lines.
- **Roof Face tool.** Outlines a single plane and sets height to the roof base, number of stories and pitch. Each edge is typed as **eave, valley, ridge, rake or hip**; the edge type drives the setbacks.
- **Other roof operations:** merge two roofs, change roof heights, model new construction from uploaded roof plans.
- Sources: [SmartRoof Best Practices and Tips](https://help.aurorasolar.com/hc/en-us/articles/360034501014-SmartRoof-Best-Practices-and-Tips), [Design using edit roof mode](https://help.aurorasolar.com/hc/en-us/articles/21295970356243-Design-using-edit-roof-mode), [Draw Roof Face](https://help.aurorasolar.com/hc/en-us/articles/360015777974-Draw-Roof-Face), [Site Modeling & Imagery section](https://help.aurorasolar.com/hc/en-us/sections/360011838253-Site-Modeling-Imagery).

**Measuring**
- **Ruler.**
  - 2D mode follows the roof geometry and snaps to the model.
  - **3D Ruler** measures the straight line between any two 3D points, snapping to mesh, roof faces and panels.
  - Hold Ctrl to switch snapping off.
- **Street View Ruler.** Pitch mode (3 nodes) or distance mode (2 nodes): place nodes in the plan view, then match them in Street View. It measures heights of trees, buildings and obstructions, and pitches. It is "not available in all markets".
- Sources: [Ruler Tool](https://help.aurorasolar.com/hc/en-us/articles/1500013036161-Ruler-Tool), [Street View Ruler](https://help.aurorasolar.com/hc/en-us/articles/29846985292819-Street-View-Ruler).

**Obstructions**
- **Drawing:** Site > Obstructions, or the hotkeys **Q** (polygon), **W** (rectangle), **E** (circle).
- **Parameters:** height, width, length and diameter, edited in the inspector or with a slider. Nodes can be dragged and the shape rotated with a curved-arrow handle.
- **AI Obstructions** detects them on the 3D roof.
- **Effects:**
  - They affect the shading, so the irradiance must be re-run after a change.
  - Manual placement and AutoDesigner avoid them, and an overlap is flagged.
- They can be edited only in Design Mode.
- Sources: [Obstructions](https://help.aurorasolar.com/hc/en-us/articles/44272536242067-Obstructions), [Keyboard Shortcuts](https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design).

**Trees: four mutually exclusive methods**
1. **LIDAR shading** is the default. The point cloud itself casts shade, for trees and neighbouring buildings. Roof-surface obstructions are excluded and must be drawn.
2. **LIDAR cutout** draws areas to subtract from the LIDAR shading ("subtracts only").
3. **AI Tree Detection** places editable sphere or cone trees (location, canopy, height) in about 30 s. AI trees are shown in darker green.
4. **Manual trees (T)** are placed by hand and auto-fitted to LIDAR. This takes about 5–10 minutes per site.

The Help Center states an explicit **one-method rule**: running LIDAR shading together with AI or manual trees counts the same trees twice and understates production. It also notes that financiers may accept only some shading methods.
- Sources: [Choosing a tree shading method](https://help.aurorasolar.com/hc/en-us/articles/55125806815507-Choosing-a-tree-shading-method-LIDAR-shading-LIDAR-cutout-AI-Tree-Detection-and-manual-trees), [LIDAR Shading](https://help.aurorasolar.com/hc/en-us/articles/4409331096851-LIDAR-Shading), [Drawing Trees in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/42258116387475-Drawing-Trees-in-Design-Mode).

**Horizon / terrain (far shading)**
- **Automatic:** Aurora "collects over 1 million elevation measurements" around the site and builds a 360° horizon profile.
- **Effect:** the beam component is blocked when the sun is below the profile, and diffuse is reduced at all hours.
- **Data sources:** Mapzen and OpenStreetMap elevation data.
- **Setting:** "Use horizon shading" is on by default.
- **Reporting:** the loss appears as its own row in the loss diagram.
- **No horizon file import** is documented: the blog presents not needing one as an advantage.
- Sources: [Horizon Shading (blog)](https://aurorasolar.com/blog/top-10-things-you-didnt-know-aurora-can-do-9-horizon-shading/), [Data Sources used in Aurora for Shading Analysis](https://help.aurorasolar.com/hc/en-us/articles/360038205713-Data-Sources-used-in-Aurora-for-Shading-Analysis), [Performance simulation settings](https://help.aurorasolar.com/hc/en-us/articles/51881840062099-Performance-simulation-settings-Account-configuration).

**Ground mounts and terrain**
- **Drawing (P):** click the top-left corner, move right and click to set the columns, then move down and click to set the rows.
- **Sidebar:** rows, columns, spacing, tilt, height to base, string length.
- **Limits:**
  - Mounting posts are not represented.
  - Terrain slope handling is not documented **[unverified]**.
  - "Carport" appears in the P tool's name, but no carport workflow is documented **[unverified]**.
- Sources: [How to Design a Ground Mount System](https://help.aurorasolar.com/hc/en-us/articles/225423788-How-to-Design-a-Ground-Mount-System), [Adding Ground Mounts in Sales Mode](https://help.aurorasolar.com/hc/en-us/articles/14810144511379-Adding-Ground-Mounts-in-Sales-Mode).

---

### 2.3 Shading and irradiance

**Metrics**
- **Irradiance** in kWh/m²/yr.
- **Solar Access (SA)** = shaded ÷ unshaded incident energy.
- **TOF** (Tilt and Orientation Factor) = insolation at the actual tilt and azimuth ÷ insolation at the optimum.
- **TSRF** = insolation with both shading and TOF ÷ unshaded insolation at the optimum orientation.
- Sources: [Key Terms: Irradiance, Solar Access, TOF, and TSRF](https://help.aurorasolar.com/hc/en-us/articles/115005927847-Key-Terms-Irradiance-Solar-Access-TOF-and-TSRF).

**Method**
- **Calculation:** sun position plus "typical local weather data", repeated for every hour of the year. It includes beam, sky diffuse and **ground-reflected** components, and the diffuse is adjusted for all objects modelled on the site.
- **Time step:** 1 h (Solmetric uses 15 min).
- **Unshaded east/west planes:** Aurora gives 100 % because diffuse light always arrives, while Solmetric drops diffuse in hours without direct sun.
- **Non-linear effect:** solar access alone is a weak predictor of energy because the shading effect is non-linear. For this reason the irradiance engine is coupled to a circuit-level simulation.
- The ray-tracing/geometry algorithm, its spatial resolution and the sky-diffuse obstruction model are **not documented [unverified]**.
- Sources: [Solar Access](https://help.aurorasolar.com/hc/en-us/articles/220450127-Solar-Access), [What is Diffuse Irradiance?](https://help.aurorasolar.com/hc/en-us/articles/360026236194-What-is-Diffuse-Irradiance).

**Irradiance map (heat map)**
- **Running it:** toolbar button or the **`i`** key. Aurora's servers simulate the sun path for every daylight hour and compute irradiance and solar access on all roofs.
- **Colour scale:** yellow (high) to red or dark purple (low).
- **Hover readouts:** irradiance (kWh) plus SA, TOF and TSRF (%) in the top-right corner. Expanding the menu shows **monthly** values.
- **Re-run:** the map must be run again after obstructions change.
- The numeric legend and grid resolution are not documented.
- **Roof face panel** (in the System tab): click a face to see azimuth, pitch, area, number of modules, module area and % coverage. Shift-click several faces to get totals.
- Sources: [How to: leverage an irradiance map](https://help.aurorasolar.com/hc/en-us/articles/21137017211411-How-to-leverage-an-irradiance-map), [How to View Roof Face Characteristics](https://help.aurorasolar.com/hc/en-us/articles/360036998854-How-to-View-Roof-Face-Characteristics).

**Explanatory tools for the client** (Sales Mode, bottom corner)
- **LIDAR height view.**
- **Sunpath animation:** play it, or set the time by hand.
- **Irradiance analysis.**
- Sources: [Assessing Shading Threats in Sales Mode](https://help.aurorasolar.com/hc/en-us/articles/15453305274643-Assessing-Shading-Threats-in-Sales-Mode).

**Bankable Shade Report**
- **Generation:** Downloads > Shade Report. The irradiance and LIDAR must be run first, and the report is "not available for Basic license users".
- **Content:** project and system data plus **annual TOF, Solar Access and TSRF**. Monthly or per-array tables and sun-path charts are not documented **[unverified]**.
- **Third-party context:** at least one US incentive program (Energy Trust of Oregon) accepts remote tools when each array has TSRF ≥ 80 %.
- Sources: [Generating Bankable Shade Reports](https://help.aurorasolar.com/hc/en-us/articles/19700906181907-Generating-Bankable-Shade-Reports), [Energy Trust document (third-party)](https://insider.energytrust.org/wp-content/uploads/SLE_using_aurora_solar.pdf).

**Validation and accuracy claims**
- **NREL 2017 fact sheet NREL/FS-7A40-67790:** validated Aurora's *Envision* remote **measurements** (Street View based) on 15 Denver roofs. 27 of 28 slopes were within 5° and 32 of 32 lengths within 1.5 ft. This validates the geometry inputs, not the shade values.
- **Design Mode page:** claims shade values that are "statistically equivalent". No NREL report on Aurora's *shading* values was found on official pages **[unverified]**.
- **Help Center:** says "NREL validated Aurora's simulation engine", with output "comparable (and, in fact, is often better)" than other software. It does not give the numbers.
- Sources: [OSTI 1350501](https://www.osti.gov/biblio/1350501), [Design Mode page](https://aurorasolar.com/design-mode/), [Aurora Simulation Engine](https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine).

---

### 2.4 Layout

**Placing panels**
- **Opening the tool:** System > Panels > module (or **M**). The **"Place panels" inspector** shows the defaults.
- **Two modes**, chosen from a yellow banner at the top:
  - **Fill roof face**: click the faces to fill;
  - **Manually**: click one spot, or click-drag to place many.
- **Spacing:** panels snap to the default row and column spacing.
- **Saved settings:** they persist per user and per design. "Reset to setting defaults" restores them, and Esc exits.
- **Editing gestures:**
  - Double-click a module to rotate it 90°.
  - Drag the arrows to rotate.
  - Drag a box to multi-select.
- Sources: [Solar Panel Placement in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/19320214409747-Solar-Panel-Placement-in-Design-Mode), [Keyboard Shortcuts](https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design).

**Rule-driven placement** (admin defaults for AutoDesigner, fill and manual placement)
- **SAP min:** the minimum Solar Access % a panel position must have.
- **TSRF min.**
- **Pitched-face tilt threshold:** the tilt above which a face counts as pitched rather than flat.
- **Spacing, tilt and orientation:** set separately for pitched and flat faces (tilt is relative to the surface).
- **Panels-per-row minimum.**
- **Filler row:** a last row in the opposite orientation, used when it adds panels.
- **Target energy offset.**
- **Fire pathways** can be placed in the shadier areas ("may add up to 25 seconds" to the calculation).
- Sources: [Design settings – Account configuration](https://help.aurorasolar.com/hc/en-us/articles/4406930393875), [AutoDesigner Filler Row](https://help.aurorasolar.com/hc/en-us/articles/4420341196179-AutoDesigner-Filler-Row), [Default AutoDesigner Settings](https://help.aurorasolar.com/hc/en-us/articles/18043796104723-Default-AutoDesigner-Settings-in-Design-Mode).

**AutoDesigner (A)** has two target modes:
- **Energy:** a target kWh or offset. It requires a string inverter or microinverter, and it **strings automatically**.
- **Max Fit:** fills the roof and does not connect the panels.

Under Advanced settings there are row spacing, orientation (including "auto" for pitched and flat faces) and the filler row. Running AutoDesigner after storage has been placed clears the storage.
- Sources: [Stringing and Connecting](https://help.aurorasolar.com/hc/en-us/articles/13139582090131-Stringing-and-Connecting), [Step-by-step guide for designing a PV system](https://help.aurorasolar.com/hc/en-us/articles/21255453781139-Step-by-step-guide-for-designing-a-PV-system), [Adding storage in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/51222171450131-Adding-storage-in-Design-Mode).

**Flat roofs / tilted racks**
- Set the module tilt, rotation (180° for "reverse tilt") and spacing, then Fill Roof Face.
- Inter-row shading guidance, ballast, wind/snow loads and row-pitch optimisation are **not documented [unverified]**.
- Commercial-only tools: **Walkway (K)** and **Fill Zone (Z)**.
- Sources: [How to Design a Reverse Tilt Rack System](https://help.aurorasolar.com/hc/en-us/articles/225408788-How-to-Design-a-Reverse-Tilt-Rack-System), [Keyboard Shortcuts](https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design).

**Setbacks and design rules**
- **Defined by** admins under Database > Jurisdictions, as distances per roof-edge type.
- **Applied** automatically to new projects whose address falls inside the jurisdiction. More specific rules take precedence (city over state).
- **Dormers:** setbacks on dormers are an optional toggle.
- The **AHJ** (US only) is identified from the address. It holds codes, design temperatures and wind codes, and permitting data.
- Sources: [Creating Jurisdiction Setbacks](https://help.aurorasolar.com/hc/en-us/articles/9151144284691-Creating-Jurisdiction-Setbacks), [AHJ Identification and Database](https://help.aurorasolar.com/hc/en-us/articles/11243297648531-AHJ-Identification-and-Database).

**Fire pathways**
- **Auto-placement:** places the minimum pathways the AHJ fire code requires. The default width is 36 in. A "Fire sprinklers" toggle makes the placement less conservative.
- **Manual drawing:** click-click with edge and corner snapping. Pathways on a hip or valley are split half on each face, and intersecting pathways merge.
- **Overlap display:** panels that overlap a pathway turn **yellow**.
- **Sales Mode:** auto-placement runs before the panels are placed.
- Sources: [How to Place Fire Pathways](https://help.aurorasolar.com/hc/en-us/articles/13351033549715-How-to-Place-Fire-Pathways).

**Real-time validation**
- **Colours while placing:**
  - **yellow** = the panel overlaps a setback;
  - **red** = it overlaps another panel or an obstruction.
- **Non-blocking:** "you will still be able to finish your design and simulate".
- **Scope:** residential Design Mode only. It can be switched off in View settings.
- Sources: [Panel Overlap Validation](https://help.aurorasolar.com/hc/en-us/articles/11977025528595-Panel-Overlap-Validation).

**Racking and attachments**
- Handled through **racking partner apps** (IronRidge, Unirac, SunModo, EcoFasten, Pegasus, K2 Systems).
- They are launched from Design Mode and return a racking BOM (CSV/PDF), which is also available through the Sync API.
- Aurora itself does no structural or attachment calculations **[unverified]**. The Plan Sets service includes structural sheets.
- Sources: [How to Use Racking Apps in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/28454358892947-How-to-Use-Racking-Apps-in-Design-Mode), [Unirac Racking Design App](https://help.aurorasolar.com/hc/en-us/articles/35814018721043-Unirac-Racking-Design-App).

---

### 2.5 Electrical design

**Components**
- **Types:** panels, strings, combiner and re-combiner boxes, string inverters, microinverters and DC optimizers (attached to a panel, never placed alone), DC/AC disconnects, load centres, service panels, meters and batteries.
- **Service panel connection types:** breaker, dual breaker, supply-side tap, load-side tap.
- **MPPTs:** right-click an inverter to assign inputs to specific MPPTs.
- **Other MLPE:** selective optimizers (only on selected modules) and multi-input MLPE are supported.
- Sources: [Components](https://help.aurorasolar.com/hc/en-us/articles/220132668-Components), [Selective Optimizers](https://help.aurorasolar.com/hc/en-us/articles/230066407-Selective-Optimizers), [How to add Multi-Input MLPE](https://help.aurorasolar.com/hc/en-us/articles/8589759844627-How-to-add-Multi-Input-Module-Level-Power-Electronics-to-a-design).

**Component database**
- **Curation:** Aurora curates the database. Admins enable a favourite subset and may let users search beyond it.
- **Visibility filters:** by region, by financier Approved Vendor List (US TPO) and by "domestic content" flag.
- **Missing components:** you "submit a request" and Support adds them for all users.
- **Custom components:** use a fixed efficiency and **cannot** simulate global MPPT or bypass diodes.
- **PAN/OND import:** no Aurora Help Center article mentions it **[unverified, probably not supported]**. HelioScope does support it (see 2.1).
- Sources: [Enabling Solar Components](https://help.aurorasolar.com/hc/en-us/articles/6964101736083-Enabling-Solar-Components-Account-Configuration), [Managing Component Visibility Settings](https://help.aurorasolar.com/hc/en-us/articles/47772130030099-Managing-Component-Visibility-Settings), [Global MPPT and Bypass Diodes](https://help.aurorasolar.com/hc/en-us/articles/115001339907-Global-MPPT-and-Bypass-Diodes), [Inverter Efficiency Curves](https://help.aurorasolar.com/hc/en-us/articles/115001389928-Inverter-Efficiency-Curves).

**Stringing**
- **Manual:**
  1. Place the inverter (**V**). Its position does not affect the simulation.
  2. Choose **String/Connect (C)**.
  3. Click-hold and drag across the modules. The string is drawn **green** when its length is within the inverter's input voltage range and **red** when it is outside.
  4. Drag a string node to change the string's length.
  5. Click the inverter, then a string end, to connect them.
- **AutoStringer:** box-select the panels, choose Auto-String, pick the inverter, then run.
- **String sizing logic** (temperature-corrected Voc, design temperatures) is **not documented [unverified]**. The AHJ database stores minimum and maximum temperatures, but their use in AutoStringer is not stated.
- **Sales Mode:** inverters are chosen automatically, aiming at DC:AC 1.2 with the fewest inverters. Microinverters are preferred when the manufacturer makes both kinds, and optimizers are added only if required.
- Sources: [Stringing and Connecting](https://help.aurorasolar.com/hc/en-us/articles/13139582090131-Stringing-and-Connecting), [Inverters and Optimizers in Sales Mode](https://help.aurorasolar.com/hc/en-us/articles/26240805636755-Inverters-and-Optimizers-in-Sales-Mode).

**Simulation-side electrical checks**
- The simulation log warns of the **percentage of daylight hours when string voltage falls outside the inverter window**.
- It also reports **clipping energy**.
- Errors appear when efficiency data is missing.
- Sources: [Aurora Simulation Engine](https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine).

**Single-line diagram**
- **Availability:** the **SLD editor is "only available in Europe"**.
- **Generation:** the SLD is auto-generated from the design (panels, inverters and so on).
- **Additions:** load centres, disconnects, batteries, meters, grid connection, custom shapes (heat pumps, EV chargers) and text.
- **Wiring:** the wire type and size entered for each wire fill a **Conductor/Conduit Schedule**. No automatic sizing is described.
- **Export:** PDF with logo and customer data.
- **Templates:** admin-defined SLD templates are applied in Design Mode.
- **Limit:** storage does not appear in the SLD.
- Sources: [Single-Line Diagram Editor](https://help.aurorasolar.com/hc/en-us/articles/44152078845843-Single-Line-Diagram-Editor), [Single-Line Diagram Templates](https://help.aurorasolar.com/hc/en-us/articles/49230080924947-Single-Line-Diagram-Templates), [Storage system types and outputs](https://help.aurorasolar.com/hc/en-us/articles/51222623384851-Storage-system-types-and-outputs).

**Plan sets (US)**
- **Plan Sets service** (about 24 h; PE stamps optional):
  - title sheet with code references, site plan, mounting and structural sheets;
  - single-line and/or three-line diagrams, electrical calculation sheet, spec sheets.
- **Instant Plan Sets** ("in under 60 seconds" on the marketing page):
  - **scope:** US pitched-roof, grid-tied residential PV ≤ 25 kW AC;
  - **excluded:** flat roofs, ground mounts and 3-phase systems;
  - **code:** NEC 2026 support, with automatic conductor and OCPD sizing.
- **NEC validation reports:** the Design Mode page lists them.
- Sources: [Plan Sets section](https://help.aurorasolar.com/hc/en-us/sections/12124563121683-Plan-Sets), [Instant Plan Sets section](https://help.aurorasolar.com/hc/en-us/sections/41721922881171-Instant-Plan-Sets), [Advanced Solar Modeling page](https://www.aurorasolar.com/features/modeling), [Design Mode page](https://aurorasolar.com/design-mode/).

**BOM and CAD export**
- **Bill of Materials:**
  - downloadable (also from Milestone snapshots);
  - storage goes in its own BoM section, de-duplicated;
  - the racking BOM comes from the partner apps.
  - The exact columns of the native BOM are not documented **[unverified]**.
- **DXF export:** layers are selectable (roof outline and obstructions, module layout and strings, setbacks and property lines, conduit paths). It opens in AutoCAD.
- Sources: [Milestones in Aurora](https://help.aurorasolar.com/hc/en-us/articles/33070484271123-Milestones-in-Aurora), [Adding storage in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/51222171450131-Adding-storage-in-Design-Mode), [Exporting DXF files from Aurora](https://help.aurorasolar.com/hc/en-us/articles/115006194208-Exporting-DXF-files-from-Aurora).

---

### 2.6 Storage, self-consumption, consumption and rates

**Storage architectures**
- **AC-coupled:** storage-only inverter.
- **DC-coupled:** hybrid inverter.
- **Battery-integrated hybrid:** for example Powerwall 3, with up to 3 expansion units. It is modelled "like inverters" in the PV simulation.
- **Placement:** batteries are placed on the canvas and connected manually, or through AutoDesigner/AutoStringer.
- **Mixed battery types:** capacity is aggregated, so the results are approximate.
- Sources: [Storage system types and outputs](https://help.aurorasolar.com/hc/en-us/articles/51222623384851-Storage-system-types-and-outputs), [Adding storage in Design Mode](https://help.aurorasolar.com/hc/en-us/articles/51222171450131-Adding-storage-in-Design-Mode), [Running and interpreting storage simulations](https://help.aurorasolar.com/hc/en-us/articles/51222791731603-Running-and-interpreting-storage-simulations).

**Operating modes**
- **Backup:** yes/no plus a reserve %.
- **Self-consumption.**
- **Energy arbitrage:** approximates a "bill savings" controller.
  - The battery lifetime cost is "hardcoded at $0.15/kWh", and battery capacity degrades by 2 %/yr.
  - Aurora falls back to self-consumption when there is no benefit.
- **Self-consumption (min curtailment):** used together with a **grid export limit (kW)**. Exports go up to the limit early in the day, leaving room in the battery for surplus that would otherwise be curtailed.
- **Backup duration:** reported as a **P90** over all days of the year.
- Sources: [Understanding Storage Modeling for Energy Arbitrage](https://help.aurorasolar.com/hc/en-us/articles/28998198908563-Understanding-Storage-Modeling-for-Energy-Arbitrage), [Using Grid Export Limits](https://help.aurorasolar.com/hc/en-us/articles/48235022215571-Using-Grid-Export-Limits), [Backup Duration - Calculations](https://help.aurorasolar.com/hc/en-us/articles/360055738673-Backup-Duration-Calculations), [Simplified Battery Backup Configuration](https://help.aurorasolar.com/hc/en-us/articles/42159933057683).

**Outputs**
- **Self-sufficiency (autarky):** share of the load met by PV and battery, with grid-reliance monthly and daily charts. The charts show solar, battery charge and discharge, grid import and export, and curtailment, with a battery on/off comparison.
- **Bill savings** and **production**.
- **Time-step caveat (Aurora's own note):** hourly profiles mask grid imports by about 2–4 % compared with high-frequency data.
- Sources: [What is Autarky?](https://help.aurorasolar.com/hc/en-us/articles/45485868561427-What-is-Autarky).

**Consumption inputs**
- **Input methods:** monthly average, a 1–12 month estimate (extrapolated from OpenEI data in North America), an annual estimate, or **interval data** at 15, 30 or 60 min (pasted, or pulled through UtilityAPI). A bill upload can auto-fill the usage (US).
- **Hourly profile:** base load plus appliances (heating, hot water, lighting, AC, EV in miles/day, pool).
- **Lifestyle profiles:** for **California, Germany, Spain and France**, obtained by clustering a year of normalised hourly data.
- **"Energy optimizations":** heat pumps, EVs, and demand caps per hour.
- Sources: [Entering energy consumption in Aurora](https://help.aurorasolar.com/hc/en-us/articles/4402392992915-Entering-energy-consumption-in-Aurora), [Adding Interval Data](https://help.aurorasolar.com/hc/en-us/articles/18711855194131-Adding-Interval-Data-in-Aurora), [Lifestyle Consumption Patterns](https://help.aurorasolar.com/hc/en-us/articles/45641841706131-Lifestyle-Consumption-Patterns), [Energy Optimizations](https://help.aurorasolar.com/hc/en-us/articles/30792182860435-Energy-Optimizations).

**Rates and country methods**
- **Utility rates:** flat or TOU tariffs, net metering or net billing, monthly vs annual true-up, escalation defaults.
- **UK MCS:** the annual yield is kWp × Kk × shade factor (the shade factor comes from Aurora's own shading analysis). Self-consumption is read from the MCS tables. Aurora falls back to its own engine when the case is outside the MCS range.
- Sources: [Utility and Tax Rates](https://help.aurorasolar.com/hc/en-us/articles/360008783794), [Difference between monthly and annual billing](https://help.aurorasolar.com/hc/en-us/articles/115009716048), [MCS (UK only)](https://help.aurorasolar.com/hc/en-us/articles/50299304030099).

---

### 2.7 Performance simulation

**Engines.** "Auto" selects the **Aurora engine** when panels are connected to inverters. Otherwise it uses **PVWatts v6**, which also applies to AI-generated designs. UK tenants also have the **MCS** method.

**Aurora engine**
- **Approach:** circuit-level.
- **Module model:** the **De Soto five-parameter model**, solved from datasheet values.
- **Circuits:** a circuit per string, with the inverter's MPPT simulated to find the operating point. With MLPE, MPPT is tracked per module.
- **Shading engine (on by default):** per-module incident irradiance, which changes each module's I-V curve.
- **Sub-module (cell-string) simulation (optional):** only for modules whose internal layout Aurora has verified with the manufacturer, and only with global-MPPT inverters.
- **Global MPPT:**
  - flagged per inverter;
  - the inverter is assumed to sit at the global optimum for the whole **one-hour step**;
  - inverters without global MPPT stay at the local high-voltage point.
- **Bypass diodes:** about 0.7 V per diode, about 2.1 V per bypassed module.
- **PVWatts comparison:** PVWatts applies shading as a linear AC derate. Aurora calls this "generally not the case" for real shading.
- Sources: [Aurora Simulation Engine](https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine), [Submodule (Cell String)-Level Simulation](https://help.aurorasolar.com/hc/en-us/articles/115001340047-Submodule-Cell-String-Level-Simulation), [Global MPPT and Bypass Diodes](https://help.aurorasolar.com/hc/en-us/articles/115001339907-Global-MPPT-and-Bypass-Diodes), [PVWatts](https://help.aurorasolar.com/hc/en-us/articles/220132448-PVWatts), [Performance simulation settings](https://help.aurorasolar.com/hc/en-us/articles/51881840062099-Performance-simulation-settings-Account-configuration).

**Models and settings**
- **Transposition:** **Perez** (default), **Hay Davies** or **Reindl**.
- **Inverter:** CEC test data, fitted with a Sandia-based parabolic curve that depends on **power and voltage**, applied per MPPT. Without CEC data a fixed efficiency is used (the lowest datasheet value).
- **Clipping:** on by default and reported as a loss.
- **Other settings:** horizon shading (on by default), LIDAR shading, and use of the module's LID and annual-degradation data (on by default).
- **Not documented [unverified]:** the cell **temperature model** (only a combined "Environmental conditions" loss exists), the **IAM** model (an "Incidence Angle" row exists), an albedo input, a spectral correction and sub-hourly steps.
- Sources: [Performance simulation settings](https://help.aurorasolar.com/hc/en-us/articles/51881840062099-Performance-simulation-settings-Account-configuration), [Inverter Efficiency Curves](https://help.aurorasolar.com/hc/en-us/articles/115001389928-Inverter-Efficiency-Curves), [What is Inverter Clipping?](https://help.aurorasolar.com/hc/en-us/articles/115001504688-What-is-Inverter-Clipping), [System Loss Diagram](https://help.aurorasolar.com/hc/en-us/articles/235994088-System-Loss-Diagram).

**Loss inputs (defaults)**

| Group | Loss | Default |
|---|---|---|
| Irradiance | LID | 1.5 % |
| Irradiance | Shading: a manual factor, needed when the Shading Engine is disabled; when enabled, shading is simulated per module | 3 % |
| Irradiance | Snow (annual or monthly) | 0 % |
| Irradiance | Soiling (annual or monthly) | 2 % |
| DC | Nameplate | 0 % |
| DC | Mismatch (fixed %, skipped for MLPE) | 2 % |
| DC | Connections | 0.5 % |
| DC | Wiring | 2 % |
| AC | Age | 0 % |
| AC | Availability | 3 % |
| AC | Other | 0 % |

The losses multiply rather than add. The loss settings lock under TPO financing. Wiring is a flat percentage: no ohmic calculation from cable lengths is documented.
- Sources: [System Losses](https://help.aurorasolar.com/hc/en-us/articles/220450107-System-Losses).

**Loss diagram** (Simulate, then Advanced) has four sections:
- **Irradiance losses:** start from optimal tilt and orientation, then tilt, horizon, shade, soiling, snow, incidence angle.
- **DC losses:** environmental conditions (includes temperature), module rating, degradation, connections, mismatch, DC wiring.
- **AC losses:** DC/AC conversion, clipping.
- **Other losses:** age, availability, other.
- Sources: [System Loss Diagram](https://help.aurorasolar.com/hc/en-us/articles/235994088-System-Loss-Diagram).

**Weather data**
- **Datasets:** NREL **PSM3**, **TMY3**, **Solcast** (put first for Europe under "Best Available"), ASHRAE **IWEC2**, **CWEC** (Canada), **RMY** (Australia).
- **Station choice:** the user can pick among the 5 nearest stations.
- **Defaults:** set by the admin, with an override per design.
- **No user weather-file import is documented [unverified]**.
- Sources: [Aurora Simulation Engine](https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine), [Weather Datasets Default Settings](https://help.aurorasolar.com/hc/en-us/articles/14732199666195-How-to-Define-Weather-Datasets-Default-Settings-in-New-Aurora), [Solcast Weather Data](https://help.aurorasolar.com/hc/en-us/articles/17387837337747-Solcast-Weather-Data).

**P50/P90**
- Production is **P50 only**: "all of Aurora's supported datasets are TMY-based".
- There is **no native P90 for production**. The user must apply an external P50→P90 factor, typically 5–15 % lower.
- Sources: [What PXX values does Aurora use](https://help.aurorasolar.com/hc/en-us/articles/52845822086547-What-PXX-values-does-Aurora-use-for-energy-production-calculations).

**Outputs**
- Annual and monthly production, offset, yield and PR.
- A simulation log with warnings.
- **Hourly export:** Download > "Production Data", a CSV of **8760 hourly production values**. The columns are not documented.
- Sources: [Hourly Production Data Export](https://help.aurorasolar.com/hc/en-us/articles/7046096001299-Hourly-Production-Data-Export), [Running and interpreting storage simulations](https://help.aurorasolar.com/hc/en-us/articles/51222791731603-Running-and-interpreting-storage-simulations).

**Comparison with PVsyst**
- The Aurora Help Center contains no PVsyst comparison.
- HelioScope advertises "accuracy within 1% of PVsyst".
- Sources: [HelioScope pricing](https://helioscope.aurorasolar.com/pricing/).

**Bifacial**
- "Aurora simulations currently do not model rear side power gain for bifacial modules".
- Bifacial modules are not officially supported.
- Sources: [Bifacial modules](https://help.aurorasolar.com/hc/en-us/articles/37506465565203-Bifacial-modules).

**Trackers**
- A Help Center search for "tracker" returns only MPPT topics. There is no tracker design or simulation in Aurora **[unverified absence]**.
- In HelioScope, single-axis trackers are Enterprise-only.
- Sources: [HelioScope tracker workaround](https://help-center.helioscope.com/hc/en-us/articles/27531451942035-Single-Axis-Tracker-Modeling-Workaround).

---

### 2.8 Proposals and financials

**Proposals**
- **Web proposal:** one unique URL per design.
  - The client can pan and zoom the house, view the sun-path shading, and see savings over time, a bill comparison and the selected financing.
  - Aurora tracks when the link was sent, when it expires (60 days) and when it was last viewed. The client can request a follow-up, which notifies the rep.
- **PDF proposal:** a non-interactive download.
- **Other proposal features:** proposal templates and custom sections, side-by-side comparison of two financing options, TPO templates, loan applications through financing integrations, and contracts through Docusign.
- Sources: [Generate and Send a Web Proposal or PDF](https://help.aurorasolar.com/hc/en-us/articles/14883209518995-Generate-and-Send-a-Web-Proposal-or-PDF-in-Sales-Mode), [How to Compare Financing Options](https://help.aurorasolar.com/hc/en-us/articles/18555188954643), [Contract Manager (Docusign) section](https://help.aurorasolar.com/hc/en-us/sections/49176222735379-Contract-Manager-Docusign).

**Financial analysis**
- **Horizon:** "typically 25 years".
- **Metrics:** NPV, IRR, LCOE, payback and lifetime savings (nominal and NPV).
- **Inputs:** utility escalation, discount rate, degradation of about 0.5 %/yr, inverter replacement, incentives (SRECs, ITC), and depreciation for commercial projects (MACRS or straight-line, with an XLSX export).
- **Financing types:** cash, loan, lease and PPA.
- The tax and incentive logic is **US-specific**.
- Sources: [Financial analysis: Overview](https://help.aurorasolar.com/hc/en-us/articles/51752305485715), [Depreciation](https://help.aurorasolar.com/hc/en-us/articles/115005300048), [Discount rate](https://help.aurorasolar.com/hc/en-us/articles/115004875647), [Net Cost Values](https://help.aurorasolar.com/hc/en-us/articles/4457088360723).

---

### 2.9 How it feels: a residential design from address to proposal

The sequence below is assembled from the A-to-Z guide, the step-by-step guide, the keyboard reference and the tool articles cited above. It is not a hands-on test: no account was used. **[A]** marks steps that are automatic or one click; **[M]** marks manual drafting.

0. **One-time setup by an admin.**
   - Database: enable favourite modules, inverters and optimizers; add jurisdictions with their setbacks.
   - Settings: pricing (per W or flat), utility and tax rates and escalation.
   - Design defaults: SAP min, TSRF min, spacing, tilt and orientation for pitched and flat faces, filler row, fire-pathway behaviour.
   - Defaults for weather dataset and losses.
   - Everything here becomes a pre-filled default that the designer can override per design.
   - Sources: [A to Z guide](https://help.aurorasolar.com/hc/en-us/articles/21240604594963-Design-with-Aurora-A-to-Z-guide), [Design settings](https://help.aurorasolar.com/hc/en-us/articles/4406930393875).
1. **Create the project [M].**
   - "+ Project", type the address (GPS coordinates or Plus Codes also work), check the pin, Create.
   - On the dashboard, enter consumption (utility, monthly or annual kWh, bill upload, or 15/30/60-min interval data).
   - "+ New design" opens Design Mode on the imagery.
2. **Pick the imagery [A/M].** The source with the highest priority is loaded. You can switch to Google HD, Nearmap, Vexcel or EagleView, enlarge the map, or open Split View with Street View or the angled map.
3. **Build the roof.** Choose one path:
   - **[A] AI:** Site > Roof > AI SmartRoof. A 3D roof arrives in seconds. Inspect it in 3D, then edit.
   - **[M] SmartRoof:** press **R** and click the eave corners. Orange guides lock 90° angles. Closing the outline produces a hipped/pitched roof and drops you into Edit Roof mode. Click a face, type pitch and eave height in the Edge & Face panel, and add dormers or folds from the green banner.
   - **[M] Roof face:** for single planes. Set the edge types.
   - **[A] Expert request** (about 3 h).
4. **Calibrate to LIDAR [A/M].**
   - Press **L**. Switch to 3D by holding right-click and moving up.
   - Use Mesh or Point Cloud and nudge the X/Y/Z offsets.
   - Click **Fit Buildings to LIDAR**.
   - Check heights with the 3D ruler or the Street View ruler.
5. **Add obstructions and trees.**
   - **[M]** Obstructions: Q, W or E, with heights read from LIDAR.
   - **[A]** LIDAR shading is the default for trees and neighbours. Alternatives are **[A]** AI Trees (about 30 s) or **[M]** T with automatic fit to LIDAR, plus a LIDAR cutout for trees that have been removed.
6. **Run the irradiance [A].** Press **i**. A heat map appears on all roofs (yellow good, red or purple bad). Hovering anywhere shows solar access, TOF and TSRF; expand the panel for monthly values.
7. **Place fire pathways [A].** System > Fire pathways > Auto place. Confirm the AHJ; sprinklers optional. Jurisdiction setbacks are already drawn.
8. **Place panels.**
   - **[A]** **A** = AutoDesigner. Choose Energy target or Max Fit and run. The panels respect SAP min, TSRF min, setbacks and pathways, and in Energy mode they arrive already strung.
   - **[M]** **M**: Fill roof face, or click-drag. Double-click a panel to rotate it.
   - In both cases overlaps show live in red or yellow.
9. **Inverters and strings.**
   - **[M]** **V** places the inverter. **C** = String/Connect: drag across modules (green = voltage OK, red = not). Right-click the inverter to assign MPPTs.
   - **[A]** AutoStringer.
   - Optimizers and micros come attached to the panels.
10. **Simulate [A].** Click "Simulate system" (top right).
    - You get production, offset, yield, PR and bill savings.
    - "Advanced" opens the four-section loss diagram.
    - The log lists warnings (string voltage outside the window for X % of hours, clipping).
11. **Storage (optional) [M/A].** System > Storage, then place and connect the battery. Choose the mode (backup reserve, self-consumption, arbitrage, export limit) and re-simulate. Self-sufficiency charts appear.
12. **Outputs [A].** Downloads include:
    - Shade Report, Production Data (8760 CSV), BOM, DXF with chosen layers, SLD PDF (Europe);
    - from Sales Mode: proposal (web link or PDF), financing comparison, contract;
    - Milestone snapshot ("Sold"), then plan sets (US).

**Keyboard and mouse reference** (official list, updated 15/04/2026). Source: [Keyboard Shortcuts (System Design)](https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design), [How to: leverage an irradiance map](https://help.aurorasolar.com/hc/en-us/articles/21137017211411-How-to-leverage-an-irradiance-map).

| Input | Action | Input | Action |
|---|---|---|---|
| Ctrl/⌘+S | Save | R | SmartRoof |
| Ctrl/⌘+Z / Y | Undo / Redo | Q / W / E | Polygon / rectangle / circle obstruction |
| Ctrl/⌘+C / V | Copy / Paste | T | Tree |
| Middle mouse, or Space + left drag | Pan | L | LIDAR |
| Right-drag left/right | Rotate | G | Show/hide map |
| Right-drag up/down | 3D view (tilt) | M | Add modules |
| Shift+1 | Focus on all | P | Ground mount / carport |
| Shift+2 | Focus on selection | V | Inverter |
| Esc | Exit current mode | B | Combiner box |
| Hold Ctrl | Disable snapping | C | String/Connect |
| Delete | Delete selection | H | Show/hide system components |
| Double-click roof | Edit roof | A | AutoDesigner |
| Double-click module | Rotate 90° | K / Z | Walkway / Fill zone (commercial) |
| Drag box | Multi-select | i | Run irradiance map |

**Feel, in summary.**
- Every tool is a **modal tool on one letter**, with **Esc** to leave it.
- Selecting an object always opens a **right-hand inspector**. A multi-type selection gets **one tab per object type** plus a "Selected Objects" tab for bulk move, rotate, duplicate and delete.
- Automation (AI roof, AutoDesigner, AutoStringer, fire pathways, setbacks) produces **ordinary editable CAD objects** that the user then refines.
- Feedback is **immediate and colour-coded** and does not block the user.
- Heavy computations (irradiance, simulation) are **explicit one-click runs on the server**. Sales Mode adds **live production updates** on every panel toggle.
- Sources: [Multi-Object Selection](https://help.aurorasolar.com/hc/en-us/articles/24253418353555-Multi-Object-Selection-in-Design-Mode), [Live Panel Toggling](https://help.aurorasolar.com/hc/en-us/articles/11973220458771-Live-Panel-Toggling).

**Speed claims (vendor)**

| Task | Claimed time | Source |
|---|---|---|
| AI roof | under 15 s (average 10.05 s) | [AI report](https://resources.aurorasolar.com/ai-aurora-solar-2023-report/review-of-aurora-ais-accuracy-and-speed) |
| AI trees | about 30 s | [Choosing a tree shading method](https://help.aurorasolar.com/hc/en-us/articles/55125806815507-Choosing-a-tree-shading-method-LIDAR-shading-LIDAR-cutout-AI-Tree-Detection-and-manual-trees) |
| Manual trees | 5–10 min per site | [Choosing a tree shading method](https://help.aurorasolar.com/hc/en-us/articles/55125806815507-Choosing-a-tree-shading-method-LIDAR-shading-LIDAR-cutout-AI-Tree-Detection-and-manual-trees) |
| Expert model | about 3 h (about 30 min expedited) | [3 Ways to model a roof](https://help.aurorasolar.com/hc/en-us/articles/21016351139859-3-Ways-to-model-a-roof) |
| Drone processing | 15–20 min | [Drone Mapping](https://help.aurorasolar.com/hc/en-us/articles/48586751929235-Drone-Mapping) |
| Instant plan set | under 60 s | [Advanced Solar Modeling](https://www.aurorasolar.com/features/modeling) |
| Customer testimonial | proposals from "1–2 hours to under 20 minutes" | [Advanced Solar Modeling](https://www.aurorasolar.com/features/modeling) |

---

### 2.10 UX patterns worth copying for Meridiana, and what Aurora does not do

**Patterns to copy** (each pattern is tied to its source; how to adapt it for Meridiana is our proposal)
1. **One-letter modal tools**, Esc to exit, hold Ctrl to suspend snapping, Shift+1/Shift+2 to frame all or the selection, right-drag to orbit. In Qt this maps to QAction shortcuts on a single-key context. ([Keyboard Shortcuts](https://help.aurorasolar.com/hc/en-us/articles/220132608-Keyboard-Shortcuts-System-Design))
2. **Trace, infer, refine roofs.** Draw only the eave outline with 90° guides, let the program infer the faces, then edit pitch and eave height per face. Folds and dormers are parametric add-ons. ([SmartRoof Best Practices](https://help.aurorasolar.com/hc/en-us/articles/360034501014-SmartRoof-Best-Practices-and-Tips), [Edit roof mode](https://help.aurorasolar.com/hc/en-us/articles/21295970356243-Design-using-edit-roof-mode))
3. **Snap to measured data.** Roof faces take pitch and height from LIDAR, trees take height from LIDAR, and a "Fit buildings to LIDAR" command exists. For Italy, the national/regional LIDAR and DSM sources the author may use are to be checked separately. ([Draw Roof Face](https://help.aurorasolar.com/hc/en-us/articles/360015777974-Draw-Roof-Face), [Fit Trees to Lidar](https://help.aurorasolar.com/hc/en-us/articles/360050816674-Fit-Trees-to-Lidar), [LIDAR](https://help.aurorasolar.com/hc/en-us/articles/225074608-LIDAR))
4. **Automation that yields editable objects, not black boxes.** AI trees are normal tree objects in a distinct colour, and AutoDesigner output is ordinary panels and strings. ([AI Tree Detection](https://help.aurorasolar.com/hc/en-us/articles/52672750497299-How-to-use-AI-Tree-Detection))
5. **Irradiance heat map with hover readouts** of SA, TOF and TSRF, a monthly breakdown, and a one-key run (`i`). In Meridiana this would be a per-point/per-module heat map computed from the 3D scene. ([Irradiance map](https://help.aurorasolar.com/hc/en-us/articles/21137017211411-How-to-leverage-an-irradiance-map))
6. **Placement rules driven by solar resource** (SAP min, TSRF min, minimum panels per row, filler row), used by both the auto and the manual fill. ([Design settings](https://help.aurorasolar.com/hc/en-us/articles/4406930393875), [Filler Row](https://help.aurorasolar.com/hc/en-us/articles/4420341196179-AutoDesigner-Filler-Row))
7. **Live, non-blocking validation.**
   - Panels: red for an overlap with a panel or obstruction, yellow for a setback.
   - Strings: drawn green or red against the inverter's voltage window *while dragging*.
   - Meridiana could extend the same idea to Voc at Tmin, MPPT range, Isc and DC/AC ratio.
   - ([Panel Overlap Validation](https://help.aurorasolar.com/hc/en-us/articles/11977025528595-Panel-Overlap-Validation), [Stringing and Connecting](https://help.aurorasolar.com/hc/en-us/articles/13139582090131-Stringing-and-Connecting))
8. **Two-target auto-layout:** "Energy target / offset" vs "Max fit", followed by AutoStringer. ([AutoDesigner](https://help.aurorasolar.com/hc/en-us/articles/13139582090131-Stringing-and-Connecting))
9. **Rules by jurisdiction, applied by address, most specific rule wins.** For Italy this could become a rule library, for example fire-safety distances, roof-edge setbacks and regional obligations. The author defines the content. ([Jurisdiction Setbacks](https://help.aurorasolar.com/hc/en-us/articles/9151144284691-Creating-Jurisdiction-Setbacks), [Fire Pathways](https://help.aurorasolar.com/hc/en-us/articles/13351033549715-How-to-Place-Fire-Pathways))
10. **Simulation log with quantified warnings** (% of daylight hours outside the voltage window, clipping energy) plus a **loss diagram grouped into irradiance, DC, AC and other**, reached from the result panel. ([Simulation Engine](https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine), [Loss Diagram](https://help.aurorasolar.com/hc/en-us/articles/235994088-System-Loss-Diagram))
11. **Organisation defaults with per-design overrides**, for weather dataset, losses and AutoDesigner settings, plus "Reset to defaults". ([Weather defaults](https://help.aurorasolar.com/hc/en-us/articles/14732199666195-How-to-Define-Weather-Datasets-Default-Settings-in-New-Aurora), [Simulation settings](https://help.aurorasolar.com/hc/en-us/articles/51881840062099-Performance-simulation-settings-Account-configuration))
12. **Milestone snapshots.** A view-only, frozen design with its BOM and shade report (Offer, Sold, Change order, Revised, Installed). This fits a rule of never overwriting a revision. ([Milestones](https://help.aurorasolar.com/hc/en-us/articles/33070484271123-Milestones-in-Aurora))
13. **Instant feedback loop:** the production estimate updates on each panel toggle, with a full simulation on "Finalize". In Meridiana: cache per-module irradiance after the shading pass, then update linearly while editing and run the full electrical simulation on demand. ([Live Panel Toggling](https://help.aurorasolar.com/hc/en-us/articles/11973220458771-Live-Panel-Toggling))
14. **Explaining modelling choices in the UI**, for example the "one tree-shading method only" rule against double counting. ([Choosing a tree shading method](https://help.aurorasolar.com/hc/en-us/articles/55125806815507-Choosing-a-tree-shading-method-LIDAR-shading-LIDAR-cutout-AI-Tree-Detection-and-manual-trees))
15. **Interchange exports:** DXF with selectable layers and an 8760 CSV. ([DXF export](https://help.aurorasolar.com/hc/en-us/articles/115006194208-Exporting-DXF-files-from-Aurora), [Hourly export](https://help.aurorasolar.com/hc/en-us/articles/7046096001299-Hourly-Production-Data-Export))
16. **Measurement aids:** a 2D ruler that follows the roof surface vs a straight 3D ruler, a Street-View ruler for heights and pitch, and a split view with oblique or street imagery. ([Ruler](https://help.aurorasolar.com/hc/en-us/articles/1500013036161-Ruler-Tool), [Street View Ruler](https://help.aurorasolar.com/hc/en-us/articles/29846985292819-Street-View-Ruler))

**What Aurora does not do, confirmed by official pages** (each item is something PVsyst does)
- **Bifacial:** no rear-side gain. ([Bifacial modules](https://help.aurorasolar.com/hc/en-us/articles/37506465565203-Bifacial-modules))
- **P90 for production:** none; P50 only, from TMY data. ([PXX values](https://help.aurorasolar.com/hc/en-us/articles/52845822086547-What-PXX-values-does-Aurora-use-for-energy-production-calculations))
- **Sub-hourly simulation:** none; the step is 1 hour. ([Solar Access](https://help.aurorasolar.com/hc/en-us/articles/220450127-Solar-Access), [Global MPPT](https://help.aurorasolar.com/hc/en-us/articles/115001339907-Global-MPPT-and-Bypass-Diodes))
- **Mismatch, wiring, soiling, snow:** all are flat percentages. No ohmic calculation from cable data and no physical soiling or snow model. ([System Losses](https://help.aurorasolar.com/hc/en-us/articles/220450107-System-Losses))
- **Custom components:** cannot model global MPPT or bypass diodes. ([Global MPPT](https://help.aurorasolar.com/hc/en-us/articles/115001339907-Global-MPPT-and-Bypass-Diodes))
- **SLD outside Europe and storage in the SLD:** neither is available. ([SLD editor](https://help.aurorasolar.com/hc/en-us/articles/44152078845843-Single-Line-Diagram-Editor), [Storage types](https://help.aurorasolar.com/hc/en-us/articles/51222623384851-Storage-system-types-and-outputs))

**Not found in Aurora's documentation [unverified absence]**
- Trackers, both single-axis and dual-axis (HelioScope Enterprise has single-axis).
- PAN/OND import (HelioScope has it).
- Import of user weather files, and import of horizon files.
- Documented temperature, IAM and spectral models, and an albedo input.
- Stand-alone (off-grid), pumping and DC-grid systems.
- Batch or parametric simulations: no UI is documented; a Sync API exists.
- A PVsyst-style engineering simulation report: only the shade report, SLD, proposal and plan-set PDFs are documented.
- Ageing or degradation over a multi-year simulation: only a fixed 0.5 %/yr in the financials, and the module's annual degradation data in the settings.

---

### 2.11 Aurora parity flags (for the parity matrix)

Legend: **yes**, **partial**, **no** = confirmed by official pages; **[unverified]** = not documented either way, or only implied. "HS" = HelioScope, Aurora's commercial product.

| Function | Aurora | Note / source |
|---|---|---|
| 3D site model from imagery | yes | SmartRoof, roof faces ([SmartRoof](https://help.aurorasolar.com/hc/en-us/articles/360034501014-SmartRoof-Best-Practices-and-Tips)) |
| LIDAR (view, calibrate, fit) | yes | Premium tier and up; US, Europe, select international; Italy not mentioned ([LIDAR](https://help.aurorasolar.com/hc/en-us/articles/225074608-LIDAR)) |
| Drone photogrammetry to mesh/LIDAR | yes | Enterprise-type plans ([Drone Mapping](https://help.aurorasolar.com/hc/en-us/articles/48586751929235-Drone-Mapping)) |
| Automatic roof detection (AI) | yes | Add-on; residential ([Aurora AI](https://help.aurorasolar.com/hc/en-us/articles/8172307851411-Aurora-AI-in-Design-Mode)) |
| Obstruction modelling | yes | Polygon, rectangle, circle; AI obstructions ([Obstructions](https://help.aurorasolar.com/hc/en-us/articles/44272536242067-Obstructions)) |
| Trees (manual / AI / from LIDAR) | yes | ([Tree methods](https://help.aurorasolar.com/hc/en-us/articles/55125806815507-Choosing-a-tree-shading-method-LIDAR-shading-LIDAR-cutout-AI-Tree-Detection-and-manual-trees)) |
| Near shading from the 3D scene | yes | Per-module irradiance, hourly ([Simulation Engine](https://help.aurorasolar.com/hc/en-us/articles/220132468-Aurora-Simulation-Engine)) |
| Electrical shading effect / module-level mismatch | yes | String circuits, bypass diodes, optional cell-string, MLPE ([Global MPPT](https://help.aurorasolar.com/hc/en-us/articles/115001339907-Global-MPPT-and-Bypass-Diodes)) |
| Irradiance heat map | yes | ([Irradiance map](https://help.aurorasolar.com/hc/en-us/articles/21137017211411-How-to-leverage-an-irradiance-map)) |
| TSRF / TOF / solar access | yes | Plus a bankable shade report on Premium ([Key Terms](https://help.aurorasolar.com/hc/en-us/articles/115005927847-Key-Terms-Irradiance-Solar-Access-TOF-and-TSRF)) |
| Horizon / far shading | yes | Automatic from elevation data; file import [unverified] ([Horizon blog](https://aurorasolar.com/blog/top-10-things-you-didnt-know-aurora-can-do-9-horizon-shading/)) |
| Auto-layout (fill, target energy) | yes | AutoDesigner ([Stringing and Connecting](https://help.aurorasolar.com/hc/en-us/articles/13139582090131-Stringing-and-Connecting)) |
| Auto-stringing | yes | AutoStringer; sizing logic [unverified] |
| Inverter sizing / DC:AC | partial | Automatic DC:AC 1.2 target in Sales Mode; validation and clipping report ([Sales Mode inverters](https://help.aurorasolar.com/hc/en-us/articles/26240805636755-Inverters-and-Optimizers-in-Sales-Mode)) |
| Optimizers / microinverters | yes | Including selective optimizers and multi-input MLPE |
| BOM | yes | Columns [unverified]; racking BOM via partner apps |
| Single-line diagram | partial | Editor only for Europe; US via plan sets ([SLD editor](https://help.aurorasolar.com/hc/en-us/articles/44152078845843-Single-Line-Diagram-Editor)) |
| Cable / conduit schedule | partial | Manual entries in the SLD; automatic conductor sizing only in US Instant Plan Sets |
| Setbacks / fire pathways / design rules | yes | By jurisdiction, by edge type, AHJ fire code |
| Permit plan sets | yes (US only) | ([Instant Plan Sets](https://help.aurorasolar.com/hc/en-us/sections/41721922881171-Instant-Plan-Sets)) |
| Proposals (web / PDF) | yes | |
| Financial analysis | yes | US-centric: NPV, IRR, LCOE, payback |
| Self-consumption with load profile | yes | Hourly; interval data; DE/ES/FR/CA profiles |
| Batteries / storage dispatch | yes | Backup, self-consumption, arbitrage, export limit |
| Grid export (injection) limit | yes | ([Grid Export Limits](https://help.aurorasolar.com/hc/en-us/articles/48235022215571-Using-Grid-Export-Limits)) |
| Bifacial | no | ([Bifacial](https://help.aurorasolar.com/hc/en-us/articles/37506465565203-Bifacial-modules)) |
| Trackers | no [unverified] | HS Enterprise: single-axis |
| Ground mounts | yes | Fixed tilt; terrain [unverified] |
| Carports | partial [unverified] | P tool label only; HS: yes |
| PAN / OND import | no [unverified] | HS: yes (PVsyst ≥ 6.4 files) |
| Hourly export | yes | 8760 production CSV; columns undocumented |
| P50 / P90 | partial | P50 only for production; P90 only for backup duration; HS Pro: P90/P95/P99 |
| Engineering PDF report (PVsyst-like) | partial [unverified] | Shade report, SLD, proposal and plan-set PDFs |
| Loss diagram | yes | Four sections |
| Transposition model choice | yes | Perez, Hay Davies, Reindl |
| Temperature / IAM / spectral models | [unverified] | Loss rows exist; models not documented |
| Soiling / snow losses | partial | Flat %, annual or monthly |
| Degradation / ageing | partial | LID %, age %, module data; 0.5 %/yr in financials |
| Ohmic DC/AC wiring from cable data | no | Flat % |
| Inverter efficiency curves | yes | CEC data, power- and voltage-dependent |
| Clipping | yes | Hourly |
| Sub-hourly simulation | no | 1-h step |
| Weather data sources | partial | PSM3, TMY3, Solcast, IWEC2, CWEC, RMY (TMY only); user import [unverified] |
| Stand-alone / pumping / DC-grid | no [unverified] | |
| Batch / parametric runs | no [unverified] | API only |
| Design versioning / snapshots | yes | Milestones |
| CAD export | yes | DXF with layers |

---

## 3. Mapping to pvlib-python (and PVGIS)

Research date: 21 October 2026. pvlib documentation "stable" = **v0.16.1**. PVsyst side = PVsyst 8.1 online help (latest release 8.1.7, 30 Sep 2026, per the PVsyst release notes). Coverage legend used in the tables: **Yes** = pvlib implements the same or an equivalent model; **Partial** = building blocks only, or a different model for the same effect; **No** = nothing in pvlib. Items not confirmed on an official page are marked [unverified].

Base for all pvlib API links: https://pvlib-python.readthedocs.io/en/stable/reference/ (section pages) and https://pvlib-python.readthedocs.io/en/stable/reference/generated/ (single-function pages).

---

### 3.1 pvlib-python: facts

Sources: https://pvlib-python.readthedocs.io/en/stable/whatsnew.html ; https://raw.githubusercontent.com/pvlib/pvlib-python/v0.16.1/pyproject.toml ; https://raw.githubusercontent.com/pvlib/pvlib-python/v0.16.1/LICENSE ; https://pvlib-python.readthedocs.io/en/stable/index.html ; https://pvlib-python.readthedocs.io/en/stable/user_guide/getting_started/installation.html ; https://pvlib-python.readthedocs.io/en/stable/user_guide/extras/faq.html ; https://www.gnu.org/licenses/license-list.en.html ; https://github.com/pvlib/pvlib-python/tree/v0.16.1/pvlib

| Item | Value |
|---|---|
| Latest stable | **v0.16.1, 26 Sep 2026** (documentation-rendering fix only). The last feature release, **v0.16.0**, came out the same day. Earlier: 0.15.2 (16 Jun 2026), 0.15.1 (21 Apr 2026), 0.15.0 (3 Feb 2026), 0.14.0 (16 Jan 2026), 0.13.1 (24 Sep 2025), 0.13.0 (7 Jun 2025), 0.12.0 (19 Mar 2025). |
| Licence | **BSD 3-Clause** (LICENSE file: "BSD 3-Clause License"; copyright "2023 pvlib python Contributors", "2014 PVLIB python Development Team", "2013 Sandia National Laboratories"). pyproject `license = "BSD-3-Clause"`. |
| Compatibility with Meridiana (GPL-3.0-or-later) | FSF licence list: Modified BSD is "a lax, permissive non-copyleft free software license, compatible with the GNU GPL". Meridiana can depend on pvlib or vendor parts of it, keeping the BSD notice. |
| Python | `requires-python = ">=3.11"` (minimum raised in v0.16.0). The v0.15.0 notes mention Python 3.14 and pandas 3 only as testing and documentation changes. |
| Required dependencies | numpy >= 1.23.2, pandas >= 1.5.0, scipy >= 1.9.2, pytz, requests, h5py (Linke turbidity file), tzdata (added in 0.16.0). |
| Optional group `[optional]` | cython, ephem, nrel-pysam, numba >= 0.17.0, solarfactors >= 1.6.1, statsmodels. |
| What the optional packages enable | numba: `method='nrel_numba'` solar position. ephem: `pyephem` solar position. statsmodels: parameter fitting. solarfactors: `pvlib.bifacial.pvfactors.pvfactors_timeseries`. nrel-pysam: `pvlib.ivtools.sdm.fit_cec_sam` (uses the SAM SDK). Other groups: `doc`, `test`, `all`. |
| NREL SPA C code | The `spa_c` wrapper is unsupported because the NREL/NLR licence forbids redistribution. Use the built-in `nrel_numpy` instead. (The docs now write "NLR" where they used to write NREL; URLs moved from nrel.gov to nlr.gov in 0.15.1.) |
| Package layout (v0.16.1) | Modules: albedo, atmosphere, bifacial/, clearsky, iam, inverter, iotools/, irradiance, ivtools/, location, modelchain, pvarray, pvsystem, scaling, shading, singlediode, snow, soiling, solarposition, spa, spectrum/, temperature, tools, tracking, transformer. **No battery/storage, economics, degradation, report or 3D-geometry module.** |
| Governance | Started in 2013 as "a Python translation of the PVLIB for Matlab toolbox developed by Sandia". Now "maintained by a core group of PV modelers from a variety of institutions", with "code contributions from over a hundred individuals". A **NumFOCUS Affiliated Project**, funded through DOE, NumFOCUS and Google Summer of Code. Citation: Anderson et al., "pvlib python: 2023 project update", JOSS 8(92) 5994. |
| Positioning (FAQ) | It supports PVsyst/SAM-style weather-to-power modelling "through Python code instead of a GUI". It is "more a toolbox" than a fixed tool. It "does not prevent you from using models improperly". `ModelChain` and `PVSystem` handle **one inverter at a time**: for several different inverters you create one PVSystem and ModelChain each and sum the results. |

API changes since mid-2025 that matter for Meridiana. They are frequent and often breaking, so Meridiana should **pin the pvlib version** and wrap its calls behind its own adapter layer.
- **0.16.0**
  - Outputs that were OrderedDicts are now dicts.
  - `irradiance.king` is deprecated, and so are the non-polynomial options of `iam.interp`.
  - `parse_epw`, `parse_bsrn` and `parse_cams` are removed.
  - New: `bifacial.ants2d.get_irradiance`, `Array.get_iam_diffuse` and `PVSystem.get_iam_diffuse`, `schlick` IAM in ModelChain, `iotools.get_nsrdb_psm4_polar(_tmy)` and `get_surfrad`.
- **0.15.2**: `ghi_from_poa_driesse_2023` is renamed `ghi_from_poa_driesse_2024`, and `Location.pytz` is deprecated.
- **0.14.0**
  - The PSM3 functions are removed (use PSM4 instead), and the component columns of `perez`, `haydavies` and `perez_driesse` are renamed with a `poa_` prefix.
  - New: `get_era5`, `get_merra2`, `spectral_factor_polo`, `singlediode.batzelis`, `ivtools.sdm.fit_desoto_batzelis`, and `method='chandrupatla'` for the single-diode solvers.
- **0.13.0**: `get_pvgis_tmy` and `get_pvgis_hourly` now return only `(data, metadata)`.

---

### 3.2 Mapping table: PVsyst model or function to pvlib

Each row's API page is given in the last column.

#### A. Time, solar geometry, atmosphere

| PVsyst model / function | pvlib function(s) | Cov. | Differences vs PVsyst; what Meridiana must add | pvlib API page |
|---|---|---|---|---|
| **Time convention.** PVsyst uses legal standard time with no daylight saving. Values are labelled at the start of the interval, and the sun is computed at the middle of the interval (or at the middle of the lit part of the sunrise and sunset intervals). A user "Time shift" is set at import, and TMY and synthetic data use the generic year 1990. | `solarposition.get_solarposition` and `Location.get_solarposition` need a tz-aware `DatetimeIndex` ("Must be localized or UTC will be assumed"). | Partial | pvlib has **no notion of interval labels**. The gallery "Modeling with interval averages" shows the half-interval shift: at 60-minute steps the mean absolute error falls from 40.5 to 2.0 W/m². Meridiana must implement four things: the label convention, the sun position at mid-interval, the partial sunrise and sunset intervals, and a time-shift detection tool (as in PVsyst). | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.solarposition.get_solarposition.html ; https://pvlib-python.readthedocs.io/en/stable/gallery/irradiance-transposition/plot_interval_transposition_error.html |
| **Solar geometry** | `solarposition.get_solarposition` (methods `nrel_numpy` (default, SPA), `nrel_numba`, `ephemeris`, `pyephem`, `nrel_c`); `spa_python`; `sun_rise_set_transit_spa` / `_geometric` / `_ephem`; `hour_angle`; `equation_of_time_spencer71` / `_pvcdrom`; `declination_spencer71` / `_cooper69`; `solar_zenith_analytical`; `solar_azimuth_analytical`; `nrel_earthsun_distance` | Yes | PVsyst uses simplified expressions ("accuracy within a few arc-minutes", see 1.10.1); SPA is more accurate, so expect arc-minute differences. | https://pvlib-python.readthedocs.io/en/stable/reference/solarposition.html |
| **Extraterrestrial irradiance, clearness index** (PVsyst 8.1.0 set the solar constant to 1361 W/m²) | `irradiance.get_extra_radiation` (default `solar_constant=1366.1`); `irradiance.clearness_index`; `clearness_index_zenith_independent`; `clearsky_index` | Yes | Pass `solar_constant=1361` for PVsyst-8.1 parity. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_extra_radiation.html ; https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/clearness-index.html |
| **Clear-sky model.** PVsyst's synthetic generation (the Meteonorm 9 algorithm) is anchored to the **ESRA** clear-sky model. | `clearsky.ineichen` (+ `lookup_linke_turbidity`); `simplified_solis`; `haurwitz`; `bird`; `detect_clearsky` (Reno-Hansen); `Location.get_clearsky` | Partial | ESRA is **not** in pvlib. Ineichen-Perez is adequate for data quality checks and clear-day plots. | https://pvlib-python.readthedocs.io/en/stable/reference/clearsky.html |
| **Air mass, pressure, precipitable water.** PVsyst estimates PW from relative humidity for the First Solar spectral model. | `atmosphere.get_relative_airmass`; `get_absolute_airmass`; `alt2pres`; `pres2alt`; `gueymard94_pw` (PW from T and RH); `tdew_from_rh`; `rh_from_tdew`; `windspeed_powerlaw`; `location.lookup_altitude` | Yes | `gueymard94_pw` covers PVsyst's "PW estimated from RH": the PVsyst help cites the same source (Gueymard 1994, see 1.10.3). | https://pvlib-python.readthedocs.io/en/stable/reference/airmass_atmospheric.html ; https://pvlib-python.readthedocs.io/en/stable/reference/location.html |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/physical-models-used/time-definition-in-pvsyst.html
- https://www.pvsyst.com/help/release-notes/index.html
- https://www.pvsyst.com/help/meteo-database/synthetic-data-generation/synthetic-data-model.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/spectral-correction.html

#### B. Weather data processing

| PVsyst model / function | pvlib function(s) | Cov. | Differences; what to add | pvlib API page |
|---|---|---|---|---|
| **Decomposition, GHI to DHI/DNI.** PVsyst used **Erbs** up to v8.0 and uses **ENGERER2** with PVsyst-refitted coefficients since v8.1, for custom imports. Meteonorm uses DirInt. | `irradiance.erbs`, `erbs_driesse`, `disc`, `dirint`, `dirindex`, `boland`, `orgill_hollands`, `louche`, `campbell_norman` | Partial | Erbs is available, which gives parity with PVsyst up to 8.0. **Engerer2 is not in pvlib.** Whether PVsyst's refitted coefficients are published is [unverified]. | https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/decomposition.html |
| **Transposition.** PVsyst offers **Hay** (Hay-Davies) and **Perez** (default since v6; 1990 coefficients, 48 values).<br>• The Perez horizon band is merged into the isotropic term.<br>• Circumsolar is scaled by cos(AOI)/max(sin 5°, sin h).<br>• Beam and circumsolar are cut at h < 2°.<br>• **Sub-hourly Perez coefficient sets** for each integer divisor of 60 min were added in 8.1.<br>• POA-only imports use Hay. | `irradiance.get_total_irradiance(model='isotropic'\|'klucher'\|'haydavies'\|'reindl'\|'king'(deprecated)\|'perez'\|'perez-driesse', model_perez='allsitescomposite1990', diffuse_components=...)`; `perez(model=..., return_components=True)` returning `poa_isotropic`, `poa_circumsolar`, `poa_horizon`; `haydavies`; `isotropic`; `reindl`; `klucher`; `perez_driesse`; `get_sky_diffuse`; `beam_component`; `poa_components`; `aoi`; `aoi_projection` | Partial / Yes | Hay and Perez 1990 are available. Three differences:<br>• pvlib keeps the horizon band as a separate term.<br>• The low-sun cut-offs differ.<br>• `perez()` takes only **named** coefficient sets (a string), so PVsyst's sub-hourly sets would need Meridiana's own Perez implementation (and their publication is [unverified]).<br>The ModelChain default is `haydavies`, so set `'perez'` explicitly. | https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/transposition.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.perez.html ; https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/angle-of-incidence.html |
| **Reverse transposition (POA-only data)** | `irradiance.gti_dirint`; `irradiance.ghi_from_poa_driesse_2024` | Partial | These are different algorithms from PVsyst's Hay-based inversion. For parity, write a Hay inversion. | https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/reverse-transposition.html |
| **Albedo.** PVsyst uses monthly values and, since 8.1.2, a CSV time series. It also has a table of usual coefficients. | `irradiance.get_ground_diffuse(albedo, surface_type)` (`SURFACE_ALBEDOS`, whose sources include the PVsyst albedo help); `Array(albedo=...)`; ModelChain weather column `albedo`; `albedo.inland_water_dvoracek` | Yes | Time-varying albedo is supported through the weather DataFrame. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.irradiance.get_ground_diffuse.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.run_model.html |
| **Component closure and gap filling** | `irradiance.complete_irradiance` (GHI = DHI + DNI·cos z); `irradiance.dni` | Yes | The data-quality tools (plots, flags) must still be built. | https://pvlib-python.readthedocs.io/en/stable/reference/irradiance/other.html |
| **Synthetic hourly (and minute) data from monthly values.** This is the Meteonorm 9.0 algorithm:<br>• daily values from an Aguiar Markov chain;<br>• hourly values from the TAG AR(1) model;<br>• the beam/diffuse split by Perez;<br>• a stochastic temperature model;<br>• minute values from Remund. | none | No | Meridiana must write it if sites with only monthly data are to be supported. With PVGIS hourly data and a TMY available everywhere in Italy, this is a low priority. | (n/a) |
| **Weather import.** PVsyst imports Meteonorm, PVGIS, NASA (POWER API since 8.1), NSRDB, Solargis, Solcast, SolarAnywhere and others, and has a custom CSV assistant (new in 8.1). | **No key needed:**<br>• `get_pvgis_tmy`, `read_pvgis_tmy`, `get_pvgis_hourly`, `read_pvgis_hourly`, `get_pvgis_horizon`<br>• `get_nasa_power` (the docs do not mention a key)<br>• `get_surfrad`, `read_surfrad`, `get_srml`, `read_srml`, `read_midc`, `read_midc_raw_data_from_nrel`, `get_solrad`, `read_solrad`, `read_crn`<br>• `get_acis_*` (whether a key is needed is [unverified])<br>• file readers `read_tmy2`, `read_tmy3`, `read_epw`, `read_nsrdb_psm4`, `read_cams`, `read_bsrn`, `read_solaranywhere`, `read_panond`<br>**Free registration:**<br>• `get_cams`: SoDa account **e-mail**, 100 requests per day<br>• `get_nsrdb_psm4_*`: NLR API key + e-mail<br>• `get_era5`: CDS API key<br>• `get_merra2`: Earthdata username and password, with GESDISC access<br>• `get_bsrn`: FTP username and password<br>**Commercial key:**<br>• `get_meteonorm_tmy`, `_observation_*`, `_forecast_*`<br>• `get_solaranywhere`<br>• `get_solcast_tmy`, `_historic`, `_forecast`, `_live`<br>• `get_solargis` (31 days per request) | Partial | Not in pvlib:<br>• a generic CSV import assistant;<br>• a reader for PVsyst's own MET/SIT formats;<br>• Meteonorm or Solargis **file** readers [unverified].<br>`map_variables=True` gives pvlib names, but **timestamp conventions differ** between sources (NASA POWER: interval start; ERA5: interval end; Meteonorm: interval middle; PVGIS-SARAH: instantaneous at HH:MM). Meridiana must normalise them to its own convention. | https://pvlib-python.readthedocs.io/en/stable/reference/iotools.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_cams.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_nsrdb_psm4_tmy.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_era5.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_merra2.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_bsrn.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_meteonorm_tmy.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_solargis.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_solcast_tmy.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_solaranywhere.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_nasa_power.html |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/diffuse-irradiance-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/transposition-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/perez-transposition-model.html
- https://www.pvsyst.com/help/physical-models-used/irradiation-models/index.html
- https://www.pvsyst.com/help/meteo-database/synthetic-data-generation/synthetic-data-model.html

#### C. Shading

| PVsyst model / function | pvlib function(s) | Cov. | Differences; what to add | pvlib API page |
|---|---|---|---|---|
| **Far shading (horizon).** The horizon line is a set of azimuth/height points; profiles entirely below 2° are ignored. The effects:<br>• **beam** is on/off, weighted by the exact crossing time within the hour;<br>• **diffuse** is reduced by integrating the isotropic sky above the horizon (a constant factor);<br>• **albedo** decreases linearly with horizon height (zero above 20°), scaled by a user fraction.<br>Profiles can be imported from other tools and from the SolarAnywhere API. | `iotools.get_pvgis_horizon` (pandas Series of elevation by azimuth, north = 0, clockwise); the `horizon=` argument of `get_meteonorm_tmy`. The gallery example masks DNI with `np.interp`. | Partial | pvlib supplies **data only**. There is no horizon module, and the gallery code leaves DHI untouched. Meridiana must implement all four effects (beam with sub-interval crossing, diffuse sky-view factor, albedo attenuation, circumsolar treated like beam) plus a horizon editor and importers. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_pvgis_horizon.html ; https://pvlib-python.readthedocs.io/en/stable/gallery/shading/plot_simple_irradiance_adjustment_for_horizon_shading.html |
| **Near shading, 3D scene.** The shading factor is the shaded area divided by the sensitive area. It comes from a **table on a sun-position grid (10° height × 20° azimuth) with interpolation** ("Fast") or from a full calculation at every step ("Slow"). Diffuse and albedo shading factors are integrals. There are an iso-shading diagram, separate tables for tracker positions, and 3D import. | Only 2-D, infinite-row tools: `shading.shaded_fraction1d` (rows and trackers, terrain slope through `cross_axis_slope`), `projected_solar_zenith_angle`, `masking_angle`, `masking_angle_passias`, `sky_diffuse_passias`, `ground_angle` | **No** (3D) / Partial (regular rows) | **Meridiana must write the whole 3D engine:**<br>• scene model;<br>• shadow projection or ray casting;<br>• shading-factor tables and interpolation;<br>• the per-step "slow" mode;<br>• hemispherical integration for diffuse and albedo;<br>• iso-shading diagrams;<br>• tracker tables. | https://pvlib-python.readthedocs.io/en/stable/reference/effects_on_pv_system_output/shading.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.shading.shaded_fraction1d.html |
| **Unlimited sheds and unlimited trackers** (2-D analytic mutual shading) | `shading.shaded_fraction1d` + `sky_diffuse_passias` / `masking_angle`; `bifacial.infinite_sheds.get_irradiance` (returns `shaded_fraction_front` and the restricted sky view); `bifacial.ants2d.get_irradiance` | Yes / Partial | The geometry is equivalent (infinite rows). The electrical treatment (next row) must be added. | https://pvlib-python.readthedocs.io/en/stable/reference/bifacial.html |
| **Electrical shading.** PVsyst has two methods:<br>• **"According to module strings"**: an upper-limit estimate, scaled by a "fraction for electrical effect" (100% recommended for regular rows).<br>• **Module layout (detailed)**: shaded sub-module corners give the sub-module IV curve (10%, 1/3, 2/3, 100%). Curves are added in voltage along the string and in current at the MPPT input, and the MPP is searched on the combined curve. The irradiance and electrical losses are booked separately, and optimizers are modelled. | `shading.direct_martinez` (empirical loss from bypass-diode "blocks"); `singlediode.bishop88` (with reverse bias: `breakdown_factor`, `breakdown_voltage=-5.5`, `breakdown_exp=3.28`); `bishop88_i_from_v`, `bishop88_v_from_i`, `bishop88_mpp`; `pvsystem.scale_voltage_current_power` (ideal scaling only) | Partial | `combine_series` is **not a pvlib API**: it is defined inline in the gallery example "Calculating power loss from partial module shading". Meridiana must write:<br>• IV aggregation from cell or sub-module, through bypass diodes and string, to MPPT;<br>• the "according to strings" estimator;<br>• optimizer handling;<br>• loss bookkeeping.<br>`direct_martinez` can serve as a fast first estimate. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.shading.direct_martinez.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.singlediode.bishop88.html ; https://pvlib-python.readthedocs.io/en/stable/gallery/shading/plot_partial_module_shading_simple.html ; https://pvlib-python.readthedocs.io/en/stable/gallery/shading/plot_martinez_shade_loss.html |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/project-design/shadings/index.html
- https://www.pvsyst.com/help/project-design/shadings/far-shadings-horizon/index.html
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/index.html
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/shading-factor-table.html
- https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/detailed-electrical-losses.html

#### D. Orientations and tracking

| PVsyst model / function | pvlib function(s) | Cov. | Differences; what to add | pvlib API page |
|---|---|---|---|---|
| **Fixed tilted planes, unlimited orientations, fixed and trackers mixed** (PVsyst 8) | `pvsystem.Array` + `FixedMount`; `PVSystem(arrays=[...])`; ModelChain results are tuples per Array; weather can be given per Array | Yes | **One inverter per PVSystem** (FAQ). Meridiana must manage the sub-array to inverter and MPPT topology itself. | https://pvlib-python.readthedocs.io/en/stable/reference/classes.html ; https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/pvsystem.html |
| **Domes (east-west)** | two `Array`s | Yes | - | as above |
| **Seasonal tilt adjustment** | custom subclass of `pvsystem.AbstractMount` (gallery `SeasonalTiltMount`, 12 monthly tilts) | Partial | A trivial adapter. | https://pvlib-python.readthedocs.io/en/stable/gallery/irradiance-transposition/plot_seasonal_tilt.html |
| **Single-axis trackers**: horizontal N-S, tilted axis, horizontal E-W, with **backtracking**. | `tracking.singleaxis(apparent_zenith, solar_azimuth, axis_tilt=0, axis_azimuth=0, max_angle=90 or (min, max), backtrack=True, gcr=2/7, cross_axis_tilt=0)`; `calc_cross_axis_tilt`; `calc_axis_tilt`; `calc_surface_orientation`; `pvsystem.SingleAxisTrackerMount` | Yes | Slope-aware backtracking follows Anderson and Mikofski (2020); pvlib backtracks from `gcr` in 2-D. PVsyst computes one common backtracking angle per orientation group from a reference "backtracking GCR" (by default the shading GCR; a "Backtracking management" tool picks or overrides the reference pair in the 3D scene) and states that it has no slope-aware backtracking (see 1.1.2.4). pvlib's `cross_axis_tilt` therefore already goes beyond PVsyst. Choosing the reference rows from a 3D scene must be written by Meridiana. | https://pvlib-python.readthedocs.io/en/stable/reference/tracking.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.tracking.singleaxis.html |
| **Vertical-axis tracker, two-axis tracker, two axes with frame** | no function; custom `AbstractMount` (gallery `DualAxisTrackerMount`, "no rotation limits or backtracking") | Partial | Meridiana must add angle limits and the frame kinematics. | https://pvlib-python.readthedocs.io/en/stable/gallery/solar-tracking/plot_dual_axis_tracking.html |
| **Tracking strategies.** PVsyst offers irradiance-optimised (diffuse) tracking for one-axis trackers, and **wind stow** (default 12 m/s, stow angle 0°). | none | No | Meridiana must write both. | (n/a) |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/project-design/orientations-in-v8/plane-orientation-modes.html
- https://www.pvsyst.com/help/project-design/orientations-in-v8/tracking-strategies.html

#### E. PV module, IAM, spectral, thermal, bifacial

| PVsyst model / function | pvlib function(s) | Cov. | Differences; what to add | pvlib API page |
|---|---|---|---|---|
| **PVsyst one-diode model.** It covers:<br>• Iph proportional to G, corrected with muISC;<br>• Io(T) through Egap;<br>• **Gamma(T) = Gamma0 + muGamma·(T − Tref)**, with muGamma fitted to the datasheet muPmpp by the secant between 25 and 45 °C (since 6.26);<br>• **Rsh(G) exponential** with RshExp = −5.5 (−3 for CdTe);<br>• constant Rs;<br>• thin-film **d2MuTau / Vbi** recombination. | `pvsystem.calcparams_pvsyst(effective_irradiance, temp_cell, alpha_sc, gamma_ref, mu_gamma, I_L_ref, I_o_ref, R_sh_ref, R_sh_0, R_s, cells_in_series, R_sh_exp=5.5, EgRef=1.121, irrad_ref=1000, temp_ref=25)` ("PVsyst v6 model"); `pvsystem.singlediode(method='lambertw'\|'newton'\|'brentq'\|'chandrupatla')`; `i_from_v`; `v_from_i`; `max_power_point`; `singlediode.bishop88*(..., d2mutau, NsVbi)`; `ivtools.sdm.pvsyst_temperature_coeff` (dP/dT at MPP); `ModelChain(dc_model='pvsyst')` | Yes (c-Si) / Partial (thin film) | Three things are missing:<br>• d2MuTau and Vbi exist **only in the `bishop88*` functions**, not in `calcparams_pvsyst` or `pvsystem.singlediode`.<br>• The muGamma fit to muPmpp (secant) is not provided. `pvsyst_temperature_coeff` lets Meridiana write the fitting loop.<br>• The sign convention differs: pvlib takes `R_sh_exp=5.5`, while the PVsyst help writes −5.5 for the same exponential. | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/sdm.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.calcparams_pvsyst.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.singlediode.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.ivtools.sdm.pvsyst_temperature_coeff.html |
| **Model parameters from the datasheet or from measurements.** PVsyst determines Rs, Rsh, Rsh(0) and Gamma from STC data. Defaults: Rsh(STC) = Vmpp/(0.2·(Isc − Impp)) when no IV curve is available; Rsh(0)/Rsh ≈ 4 for c-Si and ≈ 12 for thin film. | `ivtools.sdm.fit_pvsyst_sandia` (from **IV curves**); `fit_pvsyst_iec61853_sandia_2025` (from an **IEC 61853-1 matrix**, non-iterative); `fit_desoto_batzelis` (datasheet to **De Soto**, not PVsyst); `fit_cec_sam` (datasheet to CEC, needs nrel-pysam); `fit_desoto`; `fit_desoto_sandia`; `ivtools.sde.fit_sandia_simple`; `ivtools.utils.rectify_iv_curve`; `astm_e1036` | Partial | There is **no datasheet-to-PVsyst routine**. Meridiana must implement PVsyst's procedure (Rs determination, Rsh defaults, Rsh(0)). The IEC 61853 path is a useful extra. | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/parameters.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.ivtools.sdm.fit_pvsyst_sandia.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.ivtools.sdm.fit_pvsyst_iec61853_sandia_2025.html |
| **.PAN / .OND files** | `iotools.read_panond(filename, encoding=None)` returns a nested dict built from 2-space indentation, with types inferred from the values. | Partial | The parser relies on "inferred logic" because no format documentation was available, and it may infer types wrongly. Reading the source (v0.16.1) shows that it:<br>• does **no mapping** to `calcparams_pvsyst` arguments;<br>• does **not** compute I_L_ref or I_o_ref;<br>• returns OND efficiency curves only as generic lists;<br>• never reads the file's last line.<br>FAQ: the user decides how to use the parameters. Meridiana must write a hardened parser and validator, the key mapping, the STC solve for I_L_ref and I_o_ref, curve extraction, and optionally a writer. The PVsyst format is undocumented, which is a risk. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.read_panond.html ; https://raw.githubusercontent.com/pvlib/pvlib-python/v0.16.1/pvlib/iotools/panond.py |
| **Component databases** (PVsyst PAN/OND library) | `pvsystem.retrieve_sam(name='CECMod'\|'SandiaMod'\|'CECInverter'\|'SandiaInverter'(returns CEC)\|'ADRInverter', path=...)`, sourced from the SAM GitHub libraries | Partial | These are US CEC and Sandia lists, not PAN/OND. Meridiana must build its own component library (import PAN/OND, datasheet entry, verification). | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.retrieve_sam.html |
| **IAM.** PVsyst's options:<br>• **Fresnel** is the default since 6.67: normal glass, AR coating, textured (= AR), plastic (= normal glass); it models the air-glass and glass-EVA interfaces.<br>• **ASHRAE** with b0 = 0.05 (deprecated) and **Sandia** (deprecated).<br>• A **user profile** or the **PAN profile**.<br>• Diffuse and albedo IAM are integrated over the visible directions, assuming isotropy.<br>• The rear side uses uncoated Fresnel. | `iam.physical(aoi, n=1.526, K=4.0, L=0.002, n_ar=None)` (typical `n_ar` 1.29); `iam.ashrae(b=0.05)` (cites the PVsyst help); `iam.sapm`; `iam.interp(theta_ref, iam_ref, method='linear'\|'quadratic'\|'cubic', normalize=True)` for user and PAN profiles; `iam.martin_ruiz`; `iam.schlick`; diffuse IAM: `iam.marion_diffuse` / `marion_integrate` (sky, horizon, ground), `martin_ruiz_diffuse`, `schlick_diffuse`; `iam.convert`; `iam.fit`; `Array.get_iam_diffuse` | Yes | Whether `iam.physical` (single cover plus optional AR) matches PVsyst's two-interface Fresnel numerically is [unverified]; Meridiana should check against the PVsyst profile plots. | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/iam.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iam.physical.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iam.interp.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iam.marion_diffuse.html |
| **Spectral correction.** PVsyst has three models:<br>• **CREST** for a-Si (automatic);<br>• **Sandia** for Sandia-database modules;<br>• **First Solar**: optional, uses PW (from the file or from RH) and air mass, with custom coefficients since 8.1.6. | `spectrum.spectral_factor_firstsolar(precipitable_water, airmass_absolute, module_type=None, coefficients=None, ...)`; `spectral_factor_sapm`; `spectral_factor_caballero`; `spectral_factor_jrc` (Huld et al. 2009, from JRC Ispra data); `spectral_factor_pvspec` (Pelland 2020); `spectral_factor_polo`; `spectrl2`; `calc_spectral_mismatch_field`; `get_reference_spectra`; `average_photon_energy`; `ModelChain(spectral_model='first_solar'\|'sapm'\|'no_loss')` | Partial | First Solar (including custom coefficients) and Sandia match. **CREST is not in pvlib.** | https://pvlib-python.readthedocs.io/en/stable/reference/effects_on_pv_system_output/spectrum.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.spectrum.spectral_factor_firstsolar.html |
| **Thermal model, steady state.** T = Tamb + α·G·(1 − η)/(Uc + Uv·Ws), with α = 0.9, η iterated from 20%, G = GlobEff, and wind at about 10 m. | `temperature.pvsyst_cell(poa_global, temp_air, wind_speed=1.0, u_c=29.0, u_v=0.0, module_efficiency=0.1, alpha_absorption=0.9)`; `TEMPERATURE_MODEL_PARAMETERS['pvsyst']` (freestanding 29/0, semi_integrated 20/0, insulated 15/0); `GenericLinearModel` (converts between faiman, pvsyst, noct_sam, sapm_module and generic_linear); also `faiman`, `faiman_rad`, `sapm_cell`, `sapm_module`, `noct_sam`, `fuentes`, `ross`, `generic_linear` | Yes | pvlib does **not iterate η**: it is a fixed parameter, so pass the module's real efficiency or iterate. Feed GlobEff (after IAM, soiling and shading) for PVsyst parity. | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/temperature.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.pvsyst_cell.html |
| **Transient thermal model** (PVsyst 8.1, hourly and sub-hourly). It adapts **Prilliman**:<br>• τ comes from the module unit mass (default 11 kg/m²; 20 or more is treated as invalid) and from wind;<br>• the cut-off is 3·τmax;<br>• the value is analytically averaged over the interval. | `temperature.prilliman(temp_cell, wind_speed, unit_mass=11.1, coefficients=None)` | Partial | pvlib implements the **original** model: it needs regular data at steps under 20 minutes, and "Input sampled at 20 minutes or more is returned unchanged". For hourly parity, Meridiana must write the PVsyst interval-averaged variant. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.prilliman.html |
| **Measured array temperature** (PVsyst TArrMes) | ModelChain weather columns `cell_temperature` and `module_temperature` (the latter only with `temperature_model='sapm'`) | Yes | - | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.run_model.html |
| **Cell reverse characteristic, hot spot, bypass diodes.** PVsyst uses a cell reverse curve with coefficient brev; bypass diodes clamp the reverse voltage to about 0.7 V per diode. | `singlediode.bishop88` breakdown terms (Bishop 1988) | Partial | This is a different reverse model from PVsyst's. The bypass-diode logic must be written. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.singlediode.bishop88.html |
| **Bifacial.** PVsyst models are **2-D**: unlimited sheds and unlimited trackers (7 rotation positions plus spline interpolation). Its assumptions:<br>• isotropic diffuse and a Lambertian ground;<br>• a bifaciality factor and a separate ground albedo;<br>• a structure shading factor and a transparency factor;<br>• **rear mismatch defaulting to 10%** (no model);<br>• uncoated Fresnel IAM at the rear.<br>A 3D bifacial model is "not yet available". | `bifacial.infinite_sheds.get_irradiance` / `get_irradiance_poa` (`model='isotropic'\|'haydavies'`, gcr, height, pitch, iam_front/back, `bifaciality=0.8`, `shade_factor=-0.02`, `transmission_factor=0`); `bifacial.ants2d.get_irradiance` (new in 0.16; Perez by default, non-uniform albedo, sloped ground, segmented rows and ground); `bifacial.pvfactors.pvfactors_timeseries` (needs solarfactors); `bifacial.utils.vf_*`; **`bifacial.power_mismatch_deline`** (rear non-uniformity loss, Deline 2020) | Yes (2-D) | pvlib can replace PVsyst's fixed 10% rear mismatch with Deline's model. Neither PVsyst nor pvlib has a 3D bifacial model coupled with the near-shading scene, which is a possible Meridiana differentiator in a later phase. | https://pvlib-python.readthedocs.io/en/stable/reference/bifacial.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.bifacial.infinite_sheds.get_irradiance.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.bifacial.ants2d.get_irradiance.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.bifacial.power_mismatch_deline.html |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/index.html
- https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/temperature-behaviour-correction.html
- https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/rshunt-exponential-behavior-vs-irradiance.html
- https://www.pvsyst.com/help/physical-models-used/pv-module-standard-one-diode-model/pv-module-reverse-behaviour.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/array-incidence-loss-iam.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/spectral-correction.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/array-thermal-losses/index.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/array-thermal-losses/steady-state-thermal-model.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/array-thermal-losses/transient-thermal-model.html
- https://www.pvsyst.com/help/project-design/bifacial-systems/index.html

#### F. Array and system losses, inverter, grid side

| PVsyst model / function | pvlib function(s) | Cov. | Differences; what to add | pvlib API page |
|---|---|---|---|---|
| **Soiling** (PVsyst: a yearly or monthly %) | `soiling.hsu` (PM2.5 and PM10 plus rain); `soiling.kimber` (rain plus a daily loss rate) | Partial | pvlib's models are physical. The PVsyst-style monthly profile is trivial to code and must be the default. | https://pvlib-python.readthedocs.io/en/stable/reference/effects_on_pv_system_output/soiling.html |
| **Snow** (PVsyst has no snow model: its help suggests entering snow as winter soiling, see 1.1.13.7) | `snow.coverage_nrel`; `fully_covered_nrel`; `dc_loss_nrel`; `loss_townsend` | Extra | Optional, beyond PVsyst (useful in the Alps). | https://pvlib-python.readthedocs.io/en/stable/reference/effects_on_pv_system_output/snow.html |
| **LID, light soaking (CIGS), module quality.** PVsyst uses fixed %: no default for LID, 2% suggested. LeTID does not appear anywhere in the PVsyst 8.1 help (see 1.1.13.5). | none (`pvsystem.pvwatts_losses` has a lumped `lid` term, 1.5% by default) | No | Meridiana must write these as loss factors in its own loss chain. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.pvwatts_losses.html |
| **Mismatch.** PVsyst applies a constant % depending on string length (c-Si 0 / 0.5 / 1 / 2%) and a string-voltage mismatch of 0–0.15%. It also has a Monte Carlo dispersion tool. | none for module mismatch; `bifacial.power_mismatch_deline` (only irradiance non-uniformity); `bishop88` for a custom Monte Carlo | No / Partial | Meridiana must write the defaults table, the dispersion tool and the string tool. | https://pvlib-python.readthedocs.io/en/stable/reference/bifacial.html |
| **DC ohmic wiring loss** (resistance derived from the loss fraction at STC) | `pvsystem.dc_ohms_from_percent(vmp_ref, imp_ref, dc_ohmic_percent, modules_per_string=1, strings=1)`; `pvsystem.dc_ohmic_losses(resistance, current)`; `Array.dc_ohms_from_percent`; `ModelChain(dc_ohmic_model='dc_ohms_from_percent')` | Yes | pvlib subtracts I²R. PVsyst applies either R·Imp² or adds the wiring resistance to the module Rserie when another operating point is needed, and says both give very close results (see 1.1.13.3). | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/system_models.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvsystem.dc_ohms_from_percent.html |
| **Ageing.** PVsyst applies a %/year degradation for the simulated year, averaged at mid-year (year 10 uses 9.5 years). It adds mismatch growth computed by Monte Carlo from the RMS spread of degradation rates. | none (`pvwatts_losses` has a lumped `age` term) | No | Meridiana must write it, including multi-year runs. | (n/a) |
| **Optimizers** (PVsyst: optimizer loss; SolarEdge, Huawei, AdvanSol, Sungo, generic) | none | No | Meridiana must write it. | (n/a) |
| **Grid inverter (OND).** PVsyst's model:<br>• efficiency defined by up to 8 points, at 1 or 3 input voltages: **linear in power, quadratic interpolation between the 3 voltage curves**;<br>• automatic curves from max, EURO or CEC efficiency plus Pthresh (at least 0.5% of Pnom, resistance factor 3.0);<br>• limits, each with its own loss: Pthreshold (IL_Pmin), **overload, which moves the operating point along the array IV curve** (IL_Pmax), Imax (IL_Imax), Vmin (IL_Vmin), Vmax (IL_Vmax);<br>• night consumption, multi-MPPT and power sharing;<br>• **sub-hourly clipping correction** (8.0, Villoz 2022; ILPmxSH). | `inverter.sandia(v_dc, p_dc, inverter)` (Paco, Pdco, Vdco, Pso, C0–C3, Pnt: AC clipped at Paco, below Pso the output is −Pnt, "no MPPT window or current limits"); `inverter.sandia_multi` (unbalanced MPPT inputs, Hansen 2022); `inverter.adr(v_dc, p_dc, inverter, vtol=0.1)` (Pacmax clip, NaN outside the voltage window ± vtol); `inverter.pvwatts`; `pvwatts_multi`; **`inverter.fit_sandia(ac_power, dc_power, dc_voltage, dc_voltage_level in {'Vmin','Vnom','Vmax'}, p_ac_0, p_nt)`**; `PVSystem.get_ac`; `ModelChain(ac_model='sandia'\|'adr'\|'pvwatts')` | Partial | pvlib clips **only on the AC side**. It has no displacement of the DC operating point on the IV curve, no Imax limit, no MPPT-window loss categories, no PVsyst curve interpolation and no loss bookkeeping. **Bridge:** feed OND efficiency points (3 voltages) to `fit_sandia` to get an approximate Sandia model. For parity, Meridiana must write an OND-faithful inverter model working on the array IV curve. | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/inverter.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.sandia.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.adr.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.fit_sandia.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.inverter.sandia_multi.html |
| **Sub-hourly simulation and clipping correction** (PVsyst 8.1 can simulate sub-hourly) | ModelChain is time-step agnostic; `scaling.wvm` (wavelet variability model, spatial smoothing); `scaling.latlon_to_xy` | Partial | pvlib can simply run at 1, 5 or 15 min. PVsyst's statistical correction for hourly runs must be written if wanted. | https://pvlib-python.readthedocs.io/en/stable/reference/scaling.html |
| **Power limitation at the injection point; reactive power** | none | No | PVsyst pre-evaluates an effective Pnom for every MPPT at the start of each step, reduces the most loaded MPPTs (highest DC:AC) first, and lets the inverter clip the excess by moving the operating point; the limit may be in kW or kVA, at the inverter or at the injection point, constant or from a CSV series (see 1.1.9.9). The power factor is a fixed yearly or monthly cos φ (see 1.1.9.8). Meridiana must write both. | (n/a) |
| **AC ohmic losses** (inverter to injection point, MV line) | none (the I²R formula of `dc_ohmic_losses` can be reused) | No | Meridiana must write the AC cable model (3-phase I²R with cos φ). | (n/a) |
| **External MV/HV transformer** (iron losses plus resistive losses; night disconnection option) | `transformer.simple_efficiency(input_power, no_load_loss, load_loss, transformer_rating)` (load loss quadratic in output power) | Partial / Yes | Same physics. The night-disconnection logic and the derivation from nameplate kVA and losses must be added. | https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.transformer.simple_efficiency.html |
| **Auxiliaries** (fixed, proportional and night consumption) | none | No | Meridiana must write it. | (n/a) |
| **Unavailability.** PVsyst uses a time fraction or periods, and since 8.1.6 a CSV time series; night auxiliaries are not applied while the system is unavailable. | none (`pvwatts_losses` has a lumped `availability` term) | No | Meridiana must write it. | (n/a) |
| **Lumped losses** (PVWatts-style) | `pvsystem.pvwatts_losses(soiling=2, shading=3, snow=0, mismatch=2, wiring=2, connections=0.5, lid=1.5, nameplate_rating=1, age=0, availability=3)`, compounded multiplicatively; `pvsystem.combine_loss_factors` | Partial | Useful for a "quick estimate" mode, not for PVsyst parity. | https://pvlib-python.readthedocs.io/en/stable/reference/effects_on_pv_system_output/loss-models.html |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/project-design/array-and-system-losses/index.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/lid-loss.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/array-mismatch-losses/index.html
- https://www.pvsyst.com/help/project-design/array-and-system-losses/ageing-pv-modules-degradation/index.html
- https://www.pvsyst.com/help/physical-models-used/grid-inverter/index.html
- https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-model-efficiency.html
- https://www.pvsyst.com/help/physical-models-used/grid-inverter/inverter-operating-limits.html
- https://www.pvsyst.com/help/physical-models-used/grid-inverter/subhourly-clipping-correction.html
- https://www.pvsyst.com/help/release-notes/index.html

#### G. Orchestration, outputs and other system types

| PVsyst model / function | pvlib function(s) | Cov. | Differences; what to add | pvlib API page |
|---|---|---|---|---|
| **Simulation chain** | `modelchain.ModelChain(system, location, clearsky_model='ineichen', transposition_model='haydavies', solar_position_method='nrel_numpy', airmass_model='kastenyoung1989', dc_model, ac_model, aoi_model, spectral_model, temperature_model, dc_ohmic_model='no_loss', losses_model='no_loss')` with `run_model`, `run_model_from_poa` and `run_model_from_effective_irradiance`. Valid keys:<br>• `dc_model`: sapm, desoto, cec, pvsyst, pvwatts<br>• `ac_model`: sandia, adr, pvwatts<br>• `aoi_model`: physical, ashrae, sapm, martin_ruiz, schlick, interp, no_loss<br>• `spectral_model`: sapm, first_solar, no_loss<br>• `temperature_model`: sapm, pvsyst, faiman, fuentes, noct_sam<br>• `dc_ohmic_model`: dc_ohms_from_percent, no_loss<br>• `losses_model`: pvwatts, no_loss<br>User functions can be plugged in. | Partial | ModelChain does not follow PVsyst's loss order and keeps no loss ledger. Meridiana will probably drive the pvlib functions directly, in its own PVsyst-ordered chain with a full energy ledger. | https://pvlib-python.readthedocs.io/en/stable/reference/modelchain.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.modelchain.ModelChain.html ; https://pvlib-python.readthedocs.io/en/stable/user_guide/modeling_topics/modelchain.html |
| **Loss diagram, PDF report, project and variant management, batch and parametric runs** | none | No | Meridiana must write them all. | (n/a) |
| **P50 / P90** (year-to-year variability plus an uncertainty budget) | none | No | Meridiana must write it. The inputs can come from PVGIS multi-year `seriescalc` and `SD_y` (see 3.4). | (n/a) |
| **Economic evaluation, carbon balance** | none | No | Meridiana must write it, with Italian tariffs and incentives as data. | (n/a) |
| **Self-consumption with load profiles; grid storage** (PVsyst 8.0.17 added a "power shifting" strategy; 8.1.4 makes battery SOH affect capacity) | none (no battery module in pvlib) | No | Meridiana must write the load-profile engine and the battery and dispatch model. | (n/a) |
| **Stand-alone, pumping and DC-grid systems; concentrating systems** | none | No | Meridiana must write them (phase 3). | (n/a) |
| **Measured-data analysis** (PVsyst: import, compare with simulation) | Building blocks: iotools readers, `clearsky.detect_clearsky`, `irradiance.gti_dirint`, `ivtools.utils.astm_e1036`, `inverter.fit_sandia`, `iam.fit`, `pvarray.fit_pvefficiency_adr` | Partial | Meridiana must write the import assistant and the comparison tool. | https://pvlib-python.readthedocs.io/en/stable/reference/iotools.html |
| **Extras with no PVsyst equivalent, useful for cross-checks** | `pvarray.huld(effective_irradiance, temp_mod, pdc0, k=None, cell_type='cSi'\|'CIS'\|'CdTe', k_version='pvgis5'\|'pvgis6')` (**the PVGIS power model**); `pvarray.pvefficiency_adr` + `fit_pvefficiency_adr` (the gallery fits ADR from PVsyst parameters and runs about 8,800 times faster in its test, with an RMS difference of 0.16 W); `pvsystem.pvwatts_dc` | Extra | ADR is a candidate "fast mode" for parametric sweeps and optimisation. | https://pvlib-python.readthedocs.io/en/stable/reference/pv_modeling/system_models.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvarray.huld.html ; https://pvlib-python.readthedocs.io/en/stable/gallery/adr-pvarray/plot_simulate_fast.html |

PVsyst help pages used for this table:
- https://www.pvsyst.com/help/project-design/index.html
- https://www.pvsyst.com/help/release-notes/index.html

---

### 3.3 Gaps: what PVsyst does that pvlib does not, and what Meridiana must write

Sources: the pvlib module list at https://github.com/pvlib/pvlib-python/tree/v0.16.1/pvlib , the API pages cited in 3.2, and the PVsyst help pages cited in 3.2.

**A. Not in pvlib at all (write from scratch).**

1. **3D near-shading engine.**
   - Scene model: buildings, roofs, trees, tables; import of 3D files.
   - Shadow computation: polygon projection or ray casting.
   - Shading-factor table on a sun-position grid with interpolation, plus a per-step "slow" mode.
   - Diffuse and albedo shading factors by hemispherical integration.
   - Iso-shading diagram; tables per tracker position.
   - pvlib covers only 2-D infinite rows (`shading.shaded_fraction1d`, `masking_angle`, `sky_diffuse_passias`, `ground_angle`).
2. **Electrical shading.**
   - The "according to strings" estimate, with the fraction for electrical effect.
   - The detailed module-layout calculation: IV curves through sub-modules with bypass diodes, strings and MPPT inputs.
   - Optimizers.
   - pvlib offers only building blocks: `bishop88` (reverse bias), `direct_martinez` and `scale_voltage_current_power`. Its `combine_series` exists only in a gallery example.
3. **Horizon effect computation** (beam crossing time, diffuse sky-view, albedo attenuation) and the horizon editor. pvlib only fetches PVGIS horizon data.
4. **Loss chain and loss diagram.** A complete energy ledger in PVsyst order, with each loss named, so that the report can show the diagram. ModelChain has no such ledger.
5. **Loss factors missing in pvlib:**
   - LID and module quality; light soaking; LeTID (absent from the PVsyst 8.1 help, so a Meridiana extra);
   - mismatch (defaults table, Monte Carlo dispersion tool, string-voltage mismatch);
   - ageing (year-N simulation, mismatch growth);
   - optimizer losses, auxiliaries, unavailability (including CSV series);
   - power limitation at the injection point; AC wiring losses; the transformer night disconnection.
6. **OND-faithful inverter model.**
   - Efficiency curves: 1 or 3 voltages, up to 8 points, linear in power, quadratic in voltage.
   - Automatic curves from max, EURO or CEC efficiency.
   - Pthreshold and night tare.
   - Overload by displacing the operating point along the array IV curve.
   - Imax, Vmin and Vmax limits, each with a loss category.
   - Multi-MPPT power sharing; Pnom as a function of voltage and of temperature (PMax plus two derating levels in the OND output parameters, see 1.10.4).
   - The sub-hourly clipping correction.
   - pvlib's `sandia`, `adr` and `pvwatts` only clip AC. `fit_sandia` can approximate OND curves.
7. **Module modelling around pvlib's one-diode solver.**
   - A PAN/OND parser and validator, the parameter mapping, and the solve for I_L_ref and I_o_ref.
   - PVsyst's datasheet-to-parameter procedure (Rs, Rsh, Rsh(0)) and the muGamma fit to muPmpp (secant 25–45 °C).
   - Thin-film d2MuTau and Vbi through `bishop88`.
   - Component library management: user database, sources, checks such as PVsyst's.
8. **Thermal.** The PVsyst-style transient model for hourly steps (pvlib's `prilliman` returns data at 20 minutes or more unchanged), and the iteration of η.
9. **Meteo.**
   - Engerer2 decomposition.
   - PVsyst's sub-hourly Perez coefficient sets (and an own Perez with injectable coefficients).
   - The ESRA clear-sky model.
   - Synthetic hourly and minute generation from monthly values.
   - A generic CSV import assistant with time-shift detection, unit checks and quality control.
   - A time convention normaliser for each source.
10. **System types and applications.**
    - Self-consumption with load profiles; storage and battery models with dispatch strategies (self-consumption, peak shaving, power shifting) and SOH.
    - Stand-alone systems, pumping systems, DC-grid systems.
11. **Results.**
    - Economics and carbon balance.
    - P50/P90 (interannual variability plus an uncertainty budget).
    - The PDF report.
    - Batch and parametric runs, variants and projects.
    - Measured-data import and comparison.
12. **Tracking strategies** beyond astronomical tracking with backtracking:
    - irradiance-optimised tracking;
    - wind stow;
    - vertical-axis trackers, and two-axis trackers with limits and frames.

**B. Partially covered: adapt or wrap pvlib.**

- **Transposition**: Hay and Perez 1990 are available. Check PVsyst's low-sun cut-offs and its horizon-band handling, and set `perez` explicitly.
- **Decomposition**: Erbs is available.
- **IAM**: Fresnel/physical, ASHRAE, interp and diffuse integration are all available. Verify Fresnel equivalence.
- **Spectral**: First Solar and Sandia are available; CREST is missing.
- **Thermal**: the steady-state `pvsyst_cell` is available.
- **One-diode model**: `calcparams_pvsyst` + `singlediode` are available.
- **Bifacial 2-D**: `infinite_sheds` and `ants2d` are available, plus Deline mismatch.
- **Single-axis trackers**: `singleaxis` with slope-aware backtracking.
- **DC ohmic losses**: `dc_ohms_from_percent` + `dc_ohmic_losses`.
- **Transformer**: `simple_efficiency`.
- **Albedo time series**: supported.
- **Weather fetchers**: PVGIS and NASA POWER are keyless. CAMS, NSRDB, ERA5, MERRA-2 and BSRN need free registration (CAMS and NSRDB require an **e-mail**, which is personal data: ask the user). Meteonorm, Solcast, SolarAnywhere and Solargis need commercial keys.

**C. Engineering notes.**

1. Wrap pvlib behind Meridiana's own adapter layer, because breaking changes happen in most minor releases.
2. Pin the pvlib version per Meridiana release.
3. Add parity tests: reference projects simulated with PVsyst 8.1, compared step by step on GlobInc, GlobEff, TArray, EArray and E_Grid.
4. Keep pvlib vectorised: whole-year arrays, no per-timestep Python loops. This matters for the shading and electrical-mismatch engines.

---

### 3.4 PVGIS as data source and cross-check

Sources:
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis_en
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/api-non-interactive-service_en
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/using-pvgis-5/pvgis-5-user-manual_en
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/data-sources-calculation-methods_en
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/updates-bug-fixes_en
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/general-information/frequently-asked-questions_en
- https://joint-research-centre.ec.europa.eu/photovoltaic-geographical-information-system-pvgis/pvgis-data-download_en
- https://photovoltaic-geographic-information-system.ec.europa.eu/api/
- https://photovoltaic-geographic-information-system.ec.europa.eu/api/release-notes
- https://pvgis.pages.code.europa.eu/pvgis/
- https://pvgis.pages.code.europa.eu/pvgis/web_api/security_and_access/
- https://code.europa.eu/pvgis/pvgis
- pvlib wrappers: https://pvlib-python.readthedocs.io/en/stable/reference/iotools.html and https://raw.githubusercontent.com/pvlib/pvlib-python/v0.16.1/pvlib/iotools/pvgis.py

Two read-only test calls were made with a public Milan coordinate (no personal data): `https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?...` and `.../v5_3/seriescalc?...`.

#### 3.4.1 Versions and status

| Item | PVGIS 5.3 (production) | PVGIS 6 |
|---|---|---|
| Status | "Current production version 5.3", released **25 Sep 2024**. | A "beta for testing" according to the JRC landing page, with a complete software update and a Python backend. The JRC landing gives the solar data period as 2014–2024; the API release note of 19 Oct 2026 extends the time series to 2025. |
| API base | `https://re.jrc.ec.europa.eu/api/v5_3/<tool>` (`v5_2` still available). The **unversioned** `https://re.jrc.ec.europa.eu/api/<tool>` was announced to serve "PVGIS 5.2 for a limited period" from 25 Sep 2024. A test on 21 Oct 2026 found it returning the 5.3 data (PVGIS-SARAH3, 2005–2023) for `PVcalc`, `seriescalc` and `tmy`. v5_1 is removed. | `https://photovoltaic-geographic-information-system.ec.europa.eu/api/v6/...`, built with FastAPI: Swagger at `/api/v6/docs`, ReDoc at `/api/v6/redoc`. Endpoint groups: Performance, Power, Meteorological, Solar-Position, Coverage, Topography. A TMY endpoint was added in Oct 2026. |
| Notable changes (5.3) / breaking changes (6) | Data fixes, none breaking:<br>• 2025-03-29: pressure.<br>• 2026-03-18: SARAH3 timestamps east of 40°E.<br>• 2025-09-05: "crystalline silicon (2025)" module option added. | • **23 Jul 2026**: JSON keys renamed to snake_case, "no transition period".<br>• **19 Oct 2026**: POST parameters moved to the request body; coverage extended to global land + 25 km of sea; time series to 2025; TMY endpoint (JSON, CSV, EPW) with default method **ISO-15927-4-ECDF** (Sandia and NSRDB-TMY also supported). |
| Code licence | (not stated) | **EUPL-1.2** (`code.europa.eu/pvgis/pvgis`, created 27 Apr 2026). The FSF says EUPL-1.2 is not GPL-compatible by itself but allows relicensing to GPLv3. Meridiana should call the API rather than copy code unless the licence path is checked. |
| Other | - | The JRC is developing an MCP-based "agentic" interface ("The new PVGIS will be AI-ready"). |

#### 3.4.2 Radiation databases (PVGIS 5.3)

| Database | Type, period | Coverage / notes |
|---|---|---|
| **PVGIS-SARAH3** | satellite (METEOSAT), 2005–2023 | Default for Europe, Central Asia, Africa and parts of South America. The **verified Milan call returned `radiation_db: PVGIS-SARAH3`, `meteo_db: ERA5`, years 2005–2023, `horizon_db: DEM-calculated`.** |
| PVGIS-ERA5 | reanalysis, 2005–2023 | Global. The manual gives about 25 km in one place and 0.28° in another. Generally less accurate than satellite data where both exist. |
| PVGIS-SARAH2 | satellite, 2005–2020 | Used in 5.2. |
| PVGIS-NSRDB | satellite, 2005–2015 | Americas; "only available with PVGIS 5.2". |
| PVGIS-SARAH | satellite, 2005–2016 | Not updated; SARAH3 recommended. PVGIS-COSMO and PVGIS-CMSAF are deprecated. |

Temperature, wind and humidity come from ERA5 / ERA5-Land (per the update notes). Terrain for the horizon is a DEM at "3 arc-seconds (about 90m)".

#### 3.4.3 Tools and endpoints (5.3)

All tools are GET only. Formats: `outputformat=csv` (default, with text), `basic` (raw CSV), `json` (recommended for integration), `epw` (TMY only). `browser=0` returns a stream, `browser=1` a file.

| Tool | Purpose | Main parameters |
|---|---|---|
| `PVcalc` | Grid-connected and tracking PV, long-term averages | Required: `lat`, `lon`, `peakpower` [kW], `loss` [%].<br>Options and defaults:<br>• `raddatabase`; `usehorizon=1`; `userhorizon` (heights from north, clockwise)<br>• `pvtechchoice` = crystSi (default) \| crystSi2025 \| CIS \| CdTe \| Unknown<br>• `mountingplace` = free \| building<br>• `angle`, and `aspect` (0 = south, 90 = west)<br>• `optimalinclination`, `optimalangles`<br>• tracking flags: `inclined_axis`, `inclined_optimum`, `inclinedaxisangle`, `vertical_axis`, `vertical_optimum`, `verticalaxisangle`, `twoaxis`<br>• economics: `pvprice`, `systemcost`, `interest`, `lifetime=25` |
| `SHScalc` | Off-grid with battery | `peakpower` [W], `batterysize` [Wh], `cutoff` [%], `consumptionday` [Wh], `hourconsumption` (24 fractions), `angle`, `aspect` |
| `MRcalc` | Monthly radiation | Flags: `horirrad`, `optrad`, `selectrad` + `angle`, `mr_dni`, `d2g`, `avtemp`; plus `startyear`, `endyear` |
| `DRcalc` | Daily profile per month | `month` (0 = all), `angle`, `aspect`, `global`, `glob_2axis`, `clearsky`, `clearsky_2axis`, `showtemperatures`, `localtime` |
| `seriescalc` | Hourly time series, with optional PV power | `startyear`, `endyear`, `pvcalculation` (needs `peakpower` and `loss`), `components`, `trackingtype` 0–5, `angle`, `aspect`, `optimalinclination`, `optimalangles`, `pvtechchoice`, `mountingplace` |
| `tmy` | Typical meteorological year | `startyear`/`endyear` (at least 10 years), `usehorizon`, `userhorizon`, `outputformat` (csv \| basic \| json \| epw) |
| `printhorizon` | Horizon profile from the DEM | `lat`, `lon`, `userhorizon` (to check how PVGIS reads a user horizon) |

`trackingtype` codes (`seriescalc`): 0 fixed, 1 single horizontal axis N-S, 2 two-axis, 3 vertical axis, 4 single horizontal axis E-W, 5 single inclined axis N-S.

**JSON output of PVcalc.** Verified call: Milan, 1 kWp, 30°, south, 14% loss.
- `outputs.monthly.fixed[]` holds `E_d`, `E_m`, `H(i)_d`, `H(i)_m`, `SD_m`.
- `outputs.totals.fixed` holds `E_y` = 1344.32 kWh/y, `H(i)_y` = 1735.54 kWh/m², `SD_y` = 61.74 kWh, `l_aoi` = −2.68 %, `l_spec` = "1.12" (**returned as a string**), `l_tg` = −8.48 % (temperature and low irradiance), `l_total` = −22.54 %.

**seriescalc hourly records.** Fields: `time`, `P`, `Gb(i)`, `Gd(i)`, `Gr(i)`, `H_sun`, `T2m`, `WS10m`, `Int`. The first timestamps for Milan are `20230101:0010`, `20230101:0110`, and so on: instantaneous SARAH values at HH:10. The exact meaning of `Int` is [unverified].

**Usage limits.**
- 5.3: **30 calls per second per IP**, "429 - Too Many Requests". Requests outside the optimal window are retried for 4–5 s, then "529 - Site is overloaded". GET only (other methods get 405). "access to PVGIS APIs via AJAX is not allowed", and CORS changes are refused.
- PVGIS 6: no authentication. **10 requests/s, 100/min, 200/h per client**, and a 10,000/day application-wide cap. Strict CORS.

#### 3.4.4 Models used by PVGIS (5.x)

- **Transposition**: Muneer (1990).
- **Reflection / IAM**: Martin & Ruiz (2001, 2013), typically a 2–4% loss.
- **Spectral**: only for c-Si and CdTe, from spectrally resolved satellite data.
- **PV power**: Huld et al. (2011), with coefficients k1–k6 for c-Si (original and 2025), CIS and CdTe. "Unknown" technology assumes an 8% temperature-related loss.
- **Module temperature**: Faiman, with U0/U1 values:

| Technology | Free-standing | Roof / BIPV |
|---|---|---|
| c-Si | 26.9 / 6.2 | 20.0 / 3.2 |
| CIGS | 22.64 / 3.6 | 20.0 / 2.0 |
| CdTe | 23.37 / 5.44 | 20.0 / 3.2 |

- **Horizon**: beam is removed when the sun is below the DEM horizon (diffuse only). User horizon files are accepted.
- **System loss**: a user input, with 14% suggested (inverter, cabling, mismatch, ageing). Losses are combined **multiplicatively** (FAQ). The ageing reference is about 0.5%/year (Jordan & Kurtz 2013).
- **Bifacial**: no specific calculation. A "Bifacial Nameplate Irradiance" value can be entered instead: P_BNPI = P_STC·(1 + φ·0.135), not for BAPV/BIPV or E-W facing.
- **Not modelled**: bifacial, snow, dust, partial shading, nearby objects.
- **Off-grid**: hourly battery simulation. Default cut-off is 40% (lead-acid). The fixed performance ratio is 0.67.
- **Timestamps**:
  - SARAH values are **instantaneous**, about 5–12 minutes past the hour depending on location (HH:10 for Milan).
  - ERA5 values are stamped HH:30 ("centred at the hour").
  - NSRDB values are at HH:00.
  - TMY files have carried an "Irradiance Time Offset (h)" header since 18 Dec 2024.
- **TMY selection (5.x)**: for each month, the "most typical" month over the full period is chosen, based on GHI, air temperature and RH.

#### 3.4.5 Terms of use

- The data download page says: "free for public use if the source is acknowledged". The credit line is **"PVGIS © European Communities, 2001-2026"**.
- No licence is named for API outputs. Explicit commercial-use terms are [unverified].
- A Huld, Müller & Gambardella (2012) citation was mentioned in a search snippet; its presence on the official page is [unverified].
- The PVGIS 6 documentation and code are EUPL-1.2.

#### 3.4.6 pvlib wrappers for PVGIS

- **`iotools.get_pvgis_tmy`**
  - Signature: `get_pvgis_tmy(latitude, longitude, outputformat='json', usehorizon=True, userhorizon=None, startyear=None, endyear=None, map_variables=True, url='https://re.jrc.ec.europa.eu/api/', timeout=30, roll_utc_offset=None, coerce_year=1990)`.
  - Returns `(data, metadata)`, with the months selected in the metadata.
  - Time is UTC unless `roll_utc_offset` is set. `endyear` must be at least 10 years after `startyear`.
- **`iotools.read_pvgis_tmy`**: reads a downloaded TMY file.
- **`iotools.get_pvgis_hourly`**
  - Signature: `get_pvgis_hourly(latitude, longitude, start=None, end=None, raddatabase=None, components=True, surface_tilt=0, surface_azimuth=180, outputformat='json', usehorizon=True, userhorizon=None, pvcalculation=False, peakpower=None, pvtechchoice='crystSi', mountingplace='free', loss=0, trackingtype=0, optimal_surface_tilt=False, optimalangles=False, url=..., map_variables=True, timeout=30)`.
  - **Input azimuth is in the pvlib convention** (south = 180) and converted for PVGIS, but the **metadata azimuth is not converted**.
  - "SARAH and SARAH2 give instantaneous values, while ERA5 gives hourly averages."
- **`iotools.read_pvgis_hourly`**: reads a downloaded hourly file.
- **`iotools.get_pvgis_horizon`**
  - Signature: `get_pvgis_horizon(latitude, longitude, url=..., **kwargs)`.
  - Returns a Series of elevation by azimuth, north = 0 and clockwise, whereas "The PVGIS website uses south=0".
- **Pitfall found in the source (v0.16.1).** The functions build `url + 'tmy'`, `url + 'seriescalc'` and `url + 'printhorizon'`, and the **default `url` is the unversioned endpoint**. In September 2024 the JRC announced that this endpoint would serve **PVGIS 5.2** for a limited period. A read-only test on 21 Oct 2026 (Milan, public coordinate) showed that the unversioned `PVcalc`, `seriescalc` and `tmy` now return the same data as `v5_3`: PVGIS-SARAH3 with ERA5, 2005–2023. Meridiana should still pass `url='https://re.jrc.ec.europa.eu/api/v5_3/'` explicitly and record the version used, so that results do not change silently when the JRC repoints the unversioned address.
- **Not wrapped by pvlib**: `PVcalc`, `MRcalc`, `DRcalc`, `SHScalc`, and all PVGIS 6 endpoints. Meridiana needs a small client of its own (requests) with caching, retry and backoff, and a version switch for 5.3 and 6.

#### 3.4.7 How Meridiana can use PVGIS

1. **Default keyless weather source for Italy.**
   - PVGIS 5.3 `tmy`, which uses SARAH3 for Italy.
   - The multi-year `seriescalc` (2005–2023) for interannual variability, for P50/P90 and for monthly or seasonal checks.
   - `MRcalc` for monthly summaries.
   - Normalise the timestamps: SARAH values are instantaneous at HH:MM, while the PVsyst convention is left-labelled hourly averages with the sun at mid-interval. Document the resampling or shift choice in the report.
2. **Default horizon.** Use `printhorizon` (DEM, about 90 m) as the far-shading profile, editable by the user. Store the source and date.
3. **Cross-check A, "PVGIS mode".**
   - Run Meridiana's chain with PVGIS's models, from the `seriescalc` POA components: `pvlib.pvarray.huld(k_version='pvgis5'` or `'pvgis6')` + `pvlib.temperature.faiman` (with the PVGIS U0/U1 above) + `pvlib.iam.martin_ruiz`.
   - Compare with PVGIS `P` to validate time handling and units.
   - Whether `crystSi2025` equals pvlib's `pvgis6` coefficients is [unverified].
   - API pages: https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.pvarray.huld.html ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.temperature.faiman.html (defaults u0=25.0, u1=6.84) ; https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iam.martin_ruiz.html (default a_r=0.16).
4. **Cross-check B, yield sanity.**
   - Show the PVGIS `PVcalc` `E_y`, `SD_y` and loss terms next to Meridiana's result, with the same kWp, tilt, azimuth and an equivalent lumped loss.
   - Explain the expected differences: Muneer vs Perez/Hay transposition, the lumped 14% vs a detailed ledger, the DEM horizon vs near shading, and the absence of bifacial in PVGIS.
5. **Operations.**
   - Respect the rate limits: 30/s for 5.3, and only 200/h per client for PVGIS 6.
   - Cache by (lat, lon, tool, params, version).
   - Support offline use with cached data.
   - Print the attribution "PVGIS © European Communities, 2001-2026" in reports.
   - Track the breaking changes of PVGIS 6 before switching to it.

---

## 4. Prioritised feature list (parity matrix)

Sources: every flag below comes from the sections cited in the "See" column, which carry the URLs (PVsyst help pages in section 1, Aurora Help Center articles in section 2, pvlib API pages and PVGIS pages in section 3). The phase proposal and the IT ratings are analysis, not vendor documentation.

### 4.1 How to read the matrix

- **PVsyst / Aurora**: yes, partial or no, as documented. "no" appears only for rows where another tool has the function or where Meridiana could go beyond PVsyst. [unverified] means the vendor documentation says nothing either way.
- **pvlib provides**: yes = a pvlib 0.16.1 function implements the same or an equivalent model; partial = building blocks or a different model; no = nothing usable; n/a = not a library concern.
- **Phase** (proposal):
  - **1** = needed for a first usable energy study of an Italian rooftop system: grid-connected, residential pitched roof or commercial flat roof, 3 kW to about 1 MW, with near shading and self-consumption, ending in a report a client or a reviewer can read.
  - **2** = full PVsyst parity for grid-connected systems, from rooftop to multi-MW ground and agrivoltaic plants.
  - **3** = stand-alone, pumping, DC-grid and advanced or specialist functions.
  - "1 / 2" means a basic form in phase 1 and the complete form in phase 2.
- **IT**: relevance for an Italian designer (H high, M medium, L low), analysis.
- **See**: the section of this report that documents the row ("3.2-A" means table A of section 3.2).

### 4.2 Matrix

#### A. Project, site and workflow

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| A1 | Projects with variants (alternative designs), save as, reorder | yes | yes (several designs per project) | no | 1 | H | 1.1.1, 2.9 |
| A2 | Frozen revisions / design snapshots | partial (saved variants) | yes (Milestones) | no | 1 | H | 1.1.1, 2.10 |
| A3 | Live validation of inputs (errors, warnings, how to fix) | yes (red blocks the simulation, orange warns) | yes (live, non-blocking colours) | no | 1 | H | 1.1.9.1, 1.1.9.11, 2.4 |
| A4 | Site from map or coordinates; altitude, time zone | yes | yes (address) | partial (`Location`, `lookup_altitude`) | 1 | H | 1.1.1.2, 1.6.1 |
| A5 | Design conditions: TMin, TOperMin/Max, maximum system voltage, overload limit | yes | [unverified] | no | 1 | H | 1.1.1.3, 1.1.9.3 |
| A6 | Advanced parameters | partial (global, not stored with the variant) | partial (organisation defaults, per-design overrides) | no | 1 (store every non-default in the project) | M | 1.1.1.5, 2.10 |
| A7 | Italian user interface and Italian report | yes | [unverified] | n/a | 1 | H | 1.1.15.2, 1.1.20 |
| A8 | Runs on Linux and Windows | no (Windows only) | yes (browser) | yes | 1 | H | 1.11.1, 2.1 |
| A9 | Demo and template projects | yes (4 demos) | partial (proposal and SLD templates) | no | 2 | L | 1.1.1.4, 2.5 |
| A10 | Preliminary design (monthly quick estimate) | yes (grid, stand-alone, pumping) | partial (Sales Mode on PVWatts) | partial (`pvwatts_dc`; PVGIS `PVcalc` outside pvlib) | 2 | L | 1.5, 2.7, 3.4 |

#### B. Weather data

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| B1 | PVGIS TMY and hourly series by API | yes (PVGIS 5.3 default since 8.0.7) | no | yes (`get_pvgis_tmy`, `get_pvgis_hourly`; pass the v5_3 URL) | 1 | H | 1.6.2, 3.4 |
| B2 | Time conventions: interval labels, sun at mid-interval, time shift, DST, UTC sources | yes | [unverified] | partial | 1 | H | 1.10.1, 1.6.10, 3.2-A |
| B3 | Weather tables and graphs (monthly to hourly, clear-sky overlay) | yes | no [unverified] | no | 1 / 2 | M | 1.6.10 |
| B4 | NASA POWER monthly data | yes | no | yes (`get_nasa_power`) | 2 | L | 1.6.2, 3.2-B |
| B5 | Known-format imports (Meteonorm files, Solargis, Solcast, SolarAnywhere, TMY2/3, EPW, PVsyst standard CSV; about 20 formats) | yes | no [unverified] | partial (several readers; no PVsyst MET or CSV reader) | 2 | M | 1.6.3, 1.6.6, 3.2-B |
| B6 | Custom CSV import assistant (columns, units, UTC or legal time, DST, time shift) | yes (8.1) | no [unverified] | no | 2 | M | 1.6.4 |
| B7 | Automatic quality control and gap filling | yes | no | partial (`detect_clearsky`, `complete_irradiance`) | 2 | M | 1.6.5 |
| B8 | Sub-hourly data and resampling | yes (8.1) | no | partial (any time step) | 2 | M | 1.6.12 |
| B9 | Comparison of sources; interannual variability | yes | no | no | 2 | M | 1.6.9 |
| B10 | Clear-sky weather file | yes | no | yes (`clearsky.ineichen`; ESRA absent) | 2 | L | 1.6.11, 3.2-A |
| B11 | Paid or registered APIs (Solargis, Solcast, SolarAnywhere, NSRDB, Meteonorm) | yes | partial (Solcast and NSRDB PSM3 built in) | yes (user keys) | 3 | M | 1.6.2, 2.7, 3.2-B |
| B12 | Meteonorm built in; synthetic hourly and minute data from monthly values | yes (Meteonorm 9 DLL) | no | no | 3 | L | 1.6.7 |
| B13 | TMY generation from 10 or more years (ISO 15927-4, Sandia, NREL, custom) | yes | no | no | 3 | L | 1.6.8 |

#### C. Irradiance models

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| C1 | Solar position | yes (simplified formulas, arc-minute accuracy) | yes | yes (SPA) | 1 | H | 1.10.1, 3.2-A |
| C2 | Decomposition GHI to DHI | yes (Erbs to 8.0, Engerer2 refitted since 8.1) | [unverified] | partial (Erbs, DISC, DIRINT and others; no Engerer2) | 1 (Erbs) / 2 (Engerer2) | M | 1.10.2, 3.2-B |
| C3 | Transposition: Hay and Perez | yes (Perez default) | yes (Perez, Hay-Davies, Reindl) | yes | 1 | H | 1.10.2, 2.7, 3.2-B |
| C4 | Albedo, yearly or monthly | yes | [unverified] | yes | 1 | M | 1.10.2, 3.2-B |
| C5 | Circumsolar treated like beam for shading and IAM | yes (default since 7.0) | [unverified] | partial (`return_components`) | 2 | M | 1.10.2, 1.1.7 |
| C6 | Step-specific Perez coefficients for sub-hourly runs | yes (8.1) | no | no (named sets only) | 3 | L | 1.10.2, 3.2-B |
| C7 | Reverse transposition of POA-only data | yes (Hay) | no | partial (`gti_dirint`, `ghi_from_poa_driesse_2024`) | 3 | L | 1.10.2, 3.2-B |

#### D. Orientations, mounting and trackers

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| D1 | Unlimited orientations; fixed planes and trackers in one project | yes (8.0) | partial (roof faces; no trackers) | yes (several `Array`s) | 1 | H | 1.1.2.1, 3.2-D |
| D2 | Two orientations on one sub-array or MPPT (I/V curves combined) | yes | [unverified] (implied by the per-module circuit model) | partial | 1 | H | 1.1.2.5, 1.1.9.5 |
| D3 | Domes (east-west back-to-back tables) | yes | partial (reverse-tilt racks) | yes (two arrays) | 1 | H | 1.1.2.2, 2.4 |
| D4 | Unlimited sheds: 2-D mutual shading, GCR, limit angle | yes | no [unverified] (3D scene instead) | yes (`shaded_fraction1d`, `infinite_sheds`) | 1 | H | 1.1.2.7, 3.2-C |
| D5 | System and 3D consistency (orientations, areas, module counts) | yes (System overview, tolerances) | yes (by construction: panels in 3D are the system) | no | 1 (by construction) | H | 1.1.2.8, 2.9 |
| D6 | Strings with modules in different orientations | no ("on our roadmap"; 8.0.15 only mixes 1- and 2-module SolarEdge optimizers in one string) | [unverified] | partial (`bishop88` building blocks) | 2 | M | 1.1.2.5, 1.1.10 |
| D7 | Terrain-following tables, base slope, average orientation | yes (one averaged transposition) | [unverified] | partial (per-table transposition is possible) | 2 | M | 1.1.2.5, 1.10.1 |
| D8 | Orientation tools: transposition-factor map, sheds tilt optimisation | yes | partial (TOF on the heat map) | partial | 2 | M | 1.1.2.6, 2.3 |
| D9 | Single-axis trackers (horizontal N-S, tilted axis) with backtracking | yes | no (HelioScope Enterprise only) | yes (`tracking.singleaxis`) | 2 | H | 1.1.2.2, 1.1.2.4, 3.2-D |
| D10 | Backtracking on sloped terrain (cross-axis slope) | no (stated in the help) | no | yes (`cross_axis_tilt`) | 2 | H | 1.1.2.4, 3.2-D |
| D11 | Backtracking management (reference GCR, manual override) | yes | no | partial (`gcr` argument) | 2 | M | 1.1.2.4 |
| D12 | Other trackers: vertical axis, two-axis, E-W axis, frames | yes | no | partial (custom mounts) | 3 | L | 1.1.2.2, 3.2-D |
| D13 | Tracking strategies: irradiance optimisation, wind stow | yes | no | no | 3 | M | 1.1.2.3 |
| D14 | Seasonal tilt; sun-shields (fixed and tracking) | yes | no [unverified] | partial | 3 | L | 1.1.2.2 |

#### E. Bifacial and concentration

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| E1 | Bifacial 2-D model (sheds and trackers; view factors, structure shading, transparency, rear mismatch) | yes | no | yes (`infinite_sheds`, `ants2d`, `power_mismatch_deline`) | 2 | H | 1.1.3, 2.7, 3.2-E |
| E2 | Ground albedo for bifacial as a time series | yes (8.1.2) | no | yes | 2 | M | 1.1.3.3 |
| E3 | Bifacial on the real 3D scene (irregular rows, E-W, carports) | no (announced for a future version) | no | no | 3 | M | 1.1.3.2 |
| E4 | Concentrating PV (2-axis CPV) | yes | no | no | 3 (or never) | L | 1.1.4 |

#### F. Site model and shading

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| F1 | Orthophoto or satellite underlay with scale | yes (map download, user image with scale control) | yes (Google, Nearmap, EagleView, Vexcel) | no | 1 | H | 1.1.6, 2.2 |
| F2 | Roof tracing: outline, inferred faces, pitch, eave height, dormers | partial (building objects, hand drawing) | yes (SmartRoof) | no | 1 | H | 1.1.6, 2.2 |
| F3 | 3D obstacles: buildings, chimneys, parapets, trees | yes | yes | no | 1 | H | 1.1.6, 2.2 |
| F4 | PV fields: tables, arrays, zones with exclusion areas, auto-fill | yes | yes (fill roof face, AutoDesigner, fill zone) | no | 1 | H | 1.1.6, 2.4 |
| F5 | Manual stringing on the layout; string-to-MPPT map | yes (Module Layout) | yes (String/Connect) | no | 1 | H | 1.1.8, 2.5 |
| F6 | Horizon from the PVGIS DEM | yes | yes (automatic, own elevation data) | partial (`get_pvgis_horizon`, data only) | 1 | H | 1.1.5, 2.2, 3.2-C |
| F7 | Horizon editor and file imports (CSV, Meteonorm, SunEye, Carnaval, Horiz'ON, SolarAnywhere) | yes | no | no | 1 (editor, CSV) / 2 | M | 1.1.5 |
| F8 | Horizon effect on beam, diffuse and albedo | yes | yes (beam and diffuse) | no | 1 | H | 1.1.5, 3.2-C |
| F9 | Beam shading factor (linear) plus diffuse and albedo shading integrals | yes | yes | no (2-D rows only) | 1 | H | 1.1.7, 3.2-C |
| F10 | Electrical shading "according to module strings" (partitions, fraction for electrical effect) | yes | n/a (full circuit model instead) | no | 1 | H | 1.1.8 |
| F11 | Shadow drawing, one-day animation, sun view | yes (also video) | yes (sun-path animation) | no | 1 | H | 1.1.6, 2.3 |
| F12 | Shading-factor table with interpolation ("fast" mode) | yes (10° × 20° grid) | [unverified] | no | 2 | M | 1.1.7 |
| F13 | Iso-shading diagram | yes | no | no | 2 | M | 1.1.7 |
| F14 | Detailed electrical shading: sub-module I/V, bypass diodes, strings, MPPT | yes (Module Layout; c-Si only, 5 MWp limit by default) | yes (string circuits, optional cell-string level) | partial (`bishop88`, `direct_martinez`) | 2 | H | 1.1.8, 2.7, 3.2-C |
| F15 | Automatic string attribution | yes | yes (AutoStringer) | no | 2 | M | 1.1.8, 2.5 |
| F16 | Irradiance heat map; per-module solar access, TOF, TSRF; shade report | no | yes | no | 2 | M | 2.3 |
| F17 | Placement rules: setbacks by jurisdiction, fire pathways, minimum solar access | no | yes | no | 2 | H | 2.4 |
| F18 | Auto-layout towards an energy target | no | yes (AutoDesigner) | no | 2 | M | 2.4 |
| F19 | 3D import: DAE, 3DS, PVCollada 1 and 2, Helios 3D | yes | no | no | 2 | M | 1.1.6 |
| F20 | DXF/DWG layout import | no (SketchUp to DAE route) | no [unverified] | no | 2 | H | 1.1.6 |
| F21 | Terrain: download, CSV or GeoTIFF import | yes | partial (LIDAR surface) | no | 2 | H | 1.1.6, 2.2 |
| F22 | LIDAR / DSM point clouds: view, fit roofs and trees | partial (terrain only) | yes | no | 2 | H | 1.1.6, 2.2 |
| F23 | Diffuse shading for trackers (all, central, custom tracker) | yes | no | partial (2-D) | 2 | M | 1.1.7 |
| F24 | Speed levers: partial-scene calculation, per-object shadow casting | yes | n/a | no | 2 | M | 1.1.6 |
| F25 | Thin objects (cables, fences) | yes | no | no | 3 | L | 1.1.8 |
| F26 | AI detection of roofs, trees and obstructions | no | yes | no | 3 | M | 2.2 |
| F27 | Drone photogrammetry to mesh | partial (mesh import) | yes | no | 3 | L | 1.1.6, 2.2 |

#### G. PV module models

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| G1 | PAN import, validation and mapping to the model | yes | no (HelioScope yes) | partial (`read_panond`, raw dict) | 1 | H | 1.7.2, 3.2-E |
| G2 | PVsyst one-diode model (exponential Rsh, gamma(T)) | yes | partial (De Soto) | yes (`calcparams_pvsyst`) | 1 | H | 1.10.3, 3.2-E |
| G3 | Datasheet to parameters (Rs for −3 % at 200 W/m², Rsh and Rsh(0) defaults, muVocSpec) | yes | partial (De Soto from the datasheet) | partial | 1 | H | 1.10.3, 3.2-E |
| G4 | IAM: Fresnel (glass, AR), ASHRAE, user profile; diffuse integration | yes | [unverified] | yes | 1 | H | 1.1.13.8, 3.2-E |
| G5 | Steady-state thermal model Uc/Uv with mounting presets | yes | [unverified] | yes (`pvsyst_cell`) | 1 | H | 1.1.13.2, 3.2-E |
| G6 | Module structure: sub-modules, bypass diodes, half-cut cells, cell size | yes | yes (verified modules only) | no | 2 | H | 1.10.3, 2.7 |
| G7 | Reverse characteristics (cells, IBC) | yes | partial (bypass-diode drop) | partial (`bishop88` breakdown) | 2 | M | 1.10.3, 3.2-E |
| G8 | Transient thermal model (hourly and sub-hourly) | yes (8.1) | no | partial (`prilliman`, steps under 20 min only) | 2 | M | 1.1.13.2, 3.2-E |
| G9 | Spectral correction: First Solar, Sandia | yes | [unverified] | yes | 2 | L | 1.1.13.9, 3.2-E |
| G10 | PAN export | yes | no | no | 2 | M | 1.7.2 |
| G11 | Specialist module models: low-light data and Rs optimisation, IEC 61853 fits, thin-film recombination and CREST, Sandia model option | yes | no | partial | 3 | L | 1.10.3 |
| G12 | Measured module temperature as an input | yes | no | yes | 3 | L | 1.1.13.2 |

#### H. Losses

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| H1 | Ordered loss chain with an energy ledger and a loss diagram | yes | yes (four sections) | no | 1 | H | 1.1.13.0, 1.1.15.3, 2.7 |
| H2 | Soiling, yearly or monthly | yes | partial (flat %, annual or monthly) | partial (`hsu`, `kimber`) | 1 | H | 1.1.13.7 |
| H3 | LID, module quality, light soaking | yes | partial (LID, nameplate %) | no | 1 | H | 1.1.13.5 |
| H4 | Module and string mismatch defaults | yes | partial (flat 2 %) | no | 1 | H | 1.1.13.6 |
| H5 | DC ohmic loss (resistance from % or from cable data) | yes | partial (flat %) | yes (`dc_ohms_from_percent`) | 1 | H | 1.1.13.3, 3.2-F |
| H6 | AC ohmic loss, inverter to injection point (LV) | yes | partial (flat %) | no | 1 | H | 1.1.13.3 |
| H7 | Soiling as a time series; physical soiling models | yes (CSV, 8.1) | no | partial (`hsu`, `kimber`) | 2 | M | 1.1.13.7, 1.1.19 |
| H8 | Mismatch Monte-Carlo tool (module dispersion) | yes | no | partial | 2 | M | 1.1.13.6 |
| H9 | MV/HV lines and transformers (iron, copper, night disconnection) | yes | no | partial (`simple_efficiency`) | 2 | H | 1.1.13.3, 1.1.13.4 |
| H10 | Cable sizing helper (ampacity, wiring-loss optimisation) | yes (generic IEC 1983 formula) | partial (US NEC in plan sets) | no | 2 | H | 1.1.13.3 |
| H11 | Auxiliaries (daytime threshold, proportional, night) | yes | no | no | 2 | M | 1.1.13.10 |
| H12 | Unavailability (fraction, periods, random, CSV) | yes | partial (flat availability %) | no | 2 | M | 1.1.13.11 |
| H13 | Ageing in year N (degradation, Monte-Carlo mismatch) | yes | partial (age %, module degradation data) | no | 2 | M | 1.1.13.12 |
| H14 | Optimizer models and losses (buck/boost; SolarEdge, Huawei, Tigo and others) | yes | yes | no | 2 | H | 1.1.10, 1.1.13.13, 2.5 |
| H15 | LeTID loss item | no | no | no | 2 | M | 1.1.13.5 |
| H16 | Snow loss | no (entered as soiling) | partial (flat %) | yes (`snow` module) | 3 | M | 1.1.13.7, 3.2-F |
| H17 | Cascaded transformers / radial AC network | no (workaround only) | no | no | 3 | M | 1.1.13.4 |

#### I. Inverter and grid connection

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| I1 | OND import and validation | yes | no (HelioScope yes) | partial (`read_panond`) | 1 | H | 1.7.3, 3.2-E |
| I2 | Inverter efficiency (1 or 3 voltage curves; automatic curve from Euro or CEC efficiency) | yes | yes (CEC data, power and voltage) | partial (`sandia`, `adr`, `fit_sandia`) | 1 | H | 1.10.4, 2.7, 3.2-F |
| I3 | Operating limits with loss categories (threshold, overload by operating-point shift, Imax, MPPT window) | yes | partial (clipping, voltage warnings) | partial (AC clipping only) | 1 | H | 1.10.4, 3.2-F |
| I4 | String sizing checks (Voc at TMin, Vmpp windows) | yes | partial (green/red strings; rule undocumented) | no | 1 | H | 1.1.9.3, 2.5 |
| I5 | DC:AC sizing aid (overload histogram, thresholds) | yes | partial (DC:AC 1.2 target in Sales Mode) | no | 1 | H | 1.1.9.4, 2.5 |
| I6 | Multi-MPPT inverters; string-to-MPPT assignment | yes | yes | partial (`pvwatts_multi`, `sandia_multi`) | 1 | H | 1.1.9.5, 2.5 |
| I7 | Export limit at the injection point (constant kW) | yes | yes | no | 1 | H | 1.1.9.9, 2.6 |
| I8 | Export limit in kVA or as a time series; per-MPPT pre-evaluation | yes | no [unverified] | no | 2 | M | 1.1.9.9 |
| I9 | Power sharing, unbalanced MPPT inputs, string-inverter current limit | yes | [unverified] | partial | 2 | M | 1.1.9.5 |
| I10 | Pnom as a function of temperature (PMax, derating) | yes | [unverified] | no | 2 | M | 1.10.4 |
| I11 | Power factor and reactive energy (fixed cos φ, kVA rating) | yes | no [unverified] | no | 2 | M | 1.1.9.8 |
| I12 | Single-line diagram | partial (automatic, no storage, "work in progress") | partial (Europe only, no storage) | no | 2 | H | 1.1.9.10, 2.5 |
| I13 | Bill of materials | partial (quantities in the economic evaluation) | yes | no | 2 | M | 1.1.16, 2.5 |
| I14 | CAD export of layout and strings (DXF) | partial (Module Layout prints) | yes (DXF by layer) | no | 2 | H | 1.1.8, 2.5 |
| I15 | Sub-hourly clipping correction | yes | no | no | 3 | M | 1.10.4 |
| I16 | Q(U) or cos φ(P) control | no | no | no | 3 | M | 1.1.9.8 |
| I17 | Master/slave inverters | yes | no | no | 3 | L | 1.1.9.6 |
| I18 | Permit plan sets | no | yes (US only) | no | 3 | M | 2.5 |

#### J. Consumption and storage

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| J1 | Load profiles (monthly, daily, weekly, 15-min meter CSV, templates) | yes | yes | no | 1 | H | 1.1.11, 2.6 |
| J2 | Self-consumption without storage; zero export | yes | yes | no | 1 | H | 1.1.12.1, 2.6 |
| J3 | Battery model (Li-ion, lead-acid; SOC, efficiency, ageing, SOH) | yes | partial (simpler model) | no | 2 | H | 1.10.5, 2.6 |
| J4 | Storage for self-consumption (AC-coupled) | yes | yes | no | 2 | H | 1.1.12, 2.6 |
| J5 | DC-coupled hybrid inverter topology | no (approximated through efficiencies) | yes | no | 2 | H | 1.1.12.2, 2.6 |
| J6 | Peak shaving, power shifting, weak grid and islanding | yes | partial (export-limit mode, backup) | no | 3 | M | 1.1.12.3, 2.6 |
| J7 | Tariff-aware (time-of-use) dispatch | no ("not yet implemented") | yes (arbitrage) | no | 3 | M | 1.1.12.3, 2.6 |
| J8 | Backup duration | partial (weak-grid strategy) | yes | no | 3 | L | 1.1.12.3, 2.6 |

#### K. Simulation, results and reporting

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| K1 | Hourly simulation of several sub-arrays and inverters | yes | yes | partial (one ModelChain per inverter) | 1 | H | 1.1.14.1, 3.2-G |
| K2 | Results: monthly tables, specific yield, PR, normalised yields | yes | partial (production, yield, PR) | no | 1 | H | 1.1.15, 2.7 |
| K3 | PDF report: parameters, results, loss diagram, horizon, scene view | yes | partial (shade report, proposal) | no | 1 | H | 1.1.15.2 |
| K4 | Time-series export (CSV of chosen variables) | yes | yes (8760 CSV) | n/a | 1 | H | 1.1.14.5, 2.7 |
| K5 | PVGIS cross-check (PVcalc side by side; "PVGIS mode" chain) | no | no | partial (`huld`, `faiman`, `martin_ruiz`; PVcalc not wrapped) | 1 | H | 3.4.7 |
| K6 | Results per sub-array and per MPPT | no (totals only) | [unverified] | partial | 2 | M | 1.1.9.2 |
| K7 | Side-by-side comparison of variant reports | yes | partial | no | 2 | M | 1.1.15.2 |
| K8 | Graphs: time evolution, scatter, histograms, power distributions | yes | partial | no | 2 | M | 1.1.14.6, 1.1.15.7 |
| K9 | PR variants (bifacial, temperature-corrected); PR guarantee test | yes | no | no | 2 | M | 1.1.15.4, 1.1.15.5 |
| K10 | P50/P90 | yes | no (P50 only; HelioScope Pro yes) | no | 2 | H | 1.1.17, 2.7 |
| K11 | Economic evaluation (costs, loans, tariffs, LCOE, NPV, IRR, payback) | yes | yes (US-centric) | no | 2 | H | 1.1.16, 2.8 |
| K12 | Multi-year ageing tool | yes | no | no | 2 | M | 1.1.14.4 |
| K13 | Sub-hourly simulation | yes (8.1) | no | partial | 2 | M | 1.1.14.3 |
| K14 | Batch and parametric runs; optimisation scans | yes (one fixed orientation, yearly outputs) | no [unverified] | n/a | 2 | M | 1.1.20, 1.1.14.9 |
| K15 | Command line and scripting API | yes (paid PVsystCLI) | partial (Sync API) | yes (library) | 2 | M | 1.1.20, 2.1 |
| K16 | Carbon balance | yes | [unverified] | no | 3 | L | 1.1.18 |
| K17 | Measured-data import and comparison; inverter curve fit from measurements | yes | no | partial (`fit_sandia` and readers) | 3 | M | 1.9, 3.2-G |
| K18 | Client proposals (web or PDF, financing) | no | yes | no | 3 | M | 2.8 |

#### L. Component databases

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| L1 | Module and inverter library: user entries, favourites, sources | yes | yes (curated; additions by request) | partial (CEC and Sandia via `retrieve_sam`) | 1 | H | 1.7.1, 2.5, 3.2-E |
| L2 | Data-quality flags, obsolescence, PAN/OND verification | yes | partial (curated) | no | 2 | M | 1.7.1 |
| L3 | Excel/CSV exchange of component rows | yes | no | no | 2 | L | 1.7.1 |
| L4 | Battery database | yes (.BTR) | yes | no | 2 | H | 1.7.5, 2.6 |
| L5 | Optimizer library | partial (closed list) | yes | no | 2 | H | 1.1.10, 2.5 |
| L6 | Prices and sellers | yes | yes (pricing settings) | no | 3 | L | 1.7.10, 2.8 |

#### M. Other system types

| # | Function | PVsyst | Aurora | pvlib | Phase | IT | See |
|---|---|---|---|---|---|---|---|
| M1 | Stand-alone systems (battery, controllers, genset, loss of load), with pre-sizing | yes | no | no | 3 | L | 1.2, 1.5 |
| M2 | Pumping systems, with pre-sizing | yes | no | no | 3 | L | 1.3, 1.5 |
| M3 | DC-grid systems | yes | no | no | 3 (or never) | L | 1.4 |
| M4 | Controllers, gensets, pumps and pump-controller databases | yes | no | no | 3 | L | 1.7.6–1.7.9 |

### 4.3 Phase 1 in practice: the minimum usable rooftop study (proposal)

Phase 1 rows: A1–A8, B1–B3, C1–C4, D1–D5, F1–F11, G1–G5, H1–H6, I1–I7, J1–J2, K1–K5, L1. The order below is one way to build them as a single working pipeline.

1. **Project and site** (A1–A6, B1–B2, F6).
   - Create a project from an address or coordinates.
   - Fetch PVGIS 5.3 TMY and horizon with the versioned URL, cache them and record the attribution.
   - Set the design conditions. TMin can come from the PVGIS multi-year series, as PVsyst 8.1.5 does from its own TMY generation (minimum temperature with irradiance above 10 W/m²).
   - Every value keeps its source, and non-default parameters are stored in the project.
2. **Site model** (F1–F4, D1–D5).
   - Orthophoto underlay with a scale.
   - Roof tracing (outline, faces, pitch, eave height), obstacles and trees.
   - PV fields with fill and exclusion areas, south rows and E-W domes on flat roofs.
   - Because modules placed in 3D are the system, the PVsyst-style reconciliation of areas and module counts is not needed.
3. **Electrical design** (G1, G3, I1, F5, I4–I6, L1).
   - Import PAN and OND files into a user library with favourites.
   - String on the layout and assign strings to MPPTs.
   - Live checks while editing: Voc at TMin against the maximum voltage, Vmpp against the MPPT window, Imax, and DC:AC with an overload estimate.
4. **Simulation** (C1–C4, F7–F10, G2, G4–G5, H1–H6, I2–I3, I7, J1–J2, K1).
   - The hourly chain in PVsyst order:
     - irradiance: transposition → horizon → near shading (linear, computed at every step for small scenes) → IAM → soiling → GlobEff;
     - array: one-diode model with Uc/Uv temperature → LID, quality and mismatch → DC ohmic → EArrMPP;
     - inverter with its limits → EOutInv;
     - grid side: AC ohmic and export limit → E_Grid;
     - self-consumption from a load profile or 15-minute meter data.
   - The electrical effect of partial shading is first bounded with the "according to strings" method (F10). The module-level model (F14) follows in phase 2.
5. **Outputs** (H1, K2–K5, A7).
   - Loss diagram, monthly table, PR and specific yield.
   - CSV export and an Italian PDF report.
   - PVGIS `PVcalc` side by side, with the expected differences explained.
6. **Verification.**
   - Parity tests on reference projects simulated with PVsyst 8.1, compared step by step: GlobInc, GlobEff, TArray, EArray, E_Grid.
   - Producing those reference runs needs access to a licensed PVsyst [availability unverified].
   - Add the PVGIS cross-check, and unit tests of the time conventions.

### 4.4 Where Meridiana can go beyond PVsyst (each tied to a limit PVsyst documents)

| Opportunity | PVsyst limit (as documented) | See |
|---|---|---|
| Transposition per table or per cluster on uneven terrain and on rotundas | One averaged orientation per group of tables | 1.1.2.5 |
| Slope-aware backtracking, using pvlib | "No slope-aware backtracking" | 1.1.2.4, 3.2-D |
| Advanced parameters saved with the project and listed in the report | Advanced parameters are not stored with the variant | 1.1.1.5 |
| Results per sub-array and per MPPT | Only system totals are available | 1.1.9.2 |
| Strings mixing orientations; different module models on one MPPT | Not possible ("on our roadmap"; mixing module models on one input "is not possible") | 1.1.2.5, 1.1.9.2 |
| DC-coupled hybrid inverters and tariff-aware dispatch | AC-coupled only; time-of-use dispatch "not yet implemented" | 1.1.12 |
| Reactive power: cos φ(P), Q(U), transformer reactive losses | Fixed yearly or monthly cos φ only | 1.1.9.8 |
| AC side as a radial network (cascaded transformers, MV rings) | Cascaded transformers not implemented | 1.1.13.4 |
| Target availability solved automatically | A target loss cannot be set, only trial and error | 1.1.13.11 |
| LeTID as an explicit loss item | Absent from the 8.1 help | 1.1.13.5 |
| Graphs built after the run from stored time series | On-line graphs must be defined before the simulation | 1.1.14.6 |
| Batch over any parameter, orientation and output resolution; free CLI and Python API | One fixed orientation, yearly results; CLI is a paid Windows subscription | 1.1.20 |
| Open formats: project files, horizons (text), PVCollada 2 export, DXF import/export | Files "internal use only", binary `.HOR`, PVCollada 2 import only | 1.11.1, 1.1.5, 1.1.6 |
| Italian content: load profiles, incentive and tariff templates, cable checks against Italian tables | German BDEW load templates only; generic economics; ampacity from a 1983 IEC formula | 1.1.11, 1.1.16, 1.1.13.3 |
| Bifacial on the 3D scene (later phase) | 2-D only; no domes or E-W bifacial | 1.1.3.2 |
| Linux support | Windows only; synced folders not allowed | 1.11.1 |
| Aurora-style live feedback: heat map, colour-coded strings, rules applied by address | PVsyst validates in dialogs, with a red state that blocks | 2.10, 1.1.9.1 |

### 4.5 Risks and open questions

1. **PAN/OND format.**
   - PVsyst calls its text format "intended for internal use only" (1.11.1), and pvlib's parser works on "inferred logic" (3.2-E).
   - Meridiana needs a hardened parser with a corpus of real files.
   - Whether writing PAN/OND files is acceptable to PVsyst is a question for the author, not answered here.
2. **Parity reference data.**
   - Engerer2 refitted coefficients and the step-specific Perez sets are not published in the PVsyst help (1.10.2).
   - Exact parity on those items may therefore be impossible. Document the choice instead.
3. **Weather licences.**
   - Meteonorm is proprietary (1.6.7). PVGIS is free with attribution (3.4.5).
   - Paid sources (Solargis, Solcast, SolarAnywhere) would need the user's own keys.
4. **PVGIS 6 transition.**
   - Breaking changes happened on 23 Jul and 19 Oct 2026, and the limit is 200 requests per hour (3.4.1).
   - Keep 5.3 as the default and use a version switch.
5. **pvlib API churn.** Pin the version and wrap the calls (3.1, 3.3-C).
6. **Italian geodata.**
   - Sources of orthophotos, LIDAR and DTM for Italy (national or regional) were not researched here [to research].
   - Aurora's LIDAR coverage does not mention Italy (2.2).
7. **Scale.**
   - PVsyst caps Module Layout at 5 MWp by default (1.1.8), and its shading table exists for speed (1.1.7).
   - Multi-MW scenes need a fast partition or table mode next to the exact module-level path.
8. **Aurora's AI features** depend on proprietary imagery and LIDAR. They are phase 3 at best for an open-source desktop program.
