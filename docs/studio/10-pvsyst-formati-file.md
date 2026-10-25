# PVsyst file formats: what they hold, and how Meridiana can open them

Research of 22/10/2026 for **Meridiana** (Python, PySide6/Qt 6, pvlib, GPL-3.0-or-later). Daniel's request:
"it would be nice if Meridiana could open PVsyst's files". This study continues study 06
(`06-pvsyst-aurora-pvlib.md`), which listed PVsyst's file types from the online help; here the files
themselves are read. Study 11 (`11-pvsyst-casi-di-confronto.md`, written the same day) collects public
PVsyst reports to compare results; this study is about the files.

Legend:
- **[H]** high confidence: seen in several real files from different authors and versions, or stated by
  the official PVsyst help and consistent with the files.
- **[M]** medium: seen in one or two real files, or a consistent inference from them.
- **[L]** low: a guess from a single example.
- **[unverified]**: supported only by one unofficial source (another program's notes or code).
- **(analysis)**: my own reasoning or proposal, not a fact from a source.
- Quotes are short and verbatim; everything else is in my own words. Sample files are cited by an
  identifier (S1, S2...) defined in section 1.2, which gives their URLs.

---

## 0. In short

**Text or binary** (versions 6.40 and later, unless stated):

| Format | Kind | Encoding seen | Real samples found | Can Meridiana read it? (analysis) |
|---|---|---|---|---|
| `.PRJ` project | text, "PVObject" tree | UTF-8 with BOM, CRLF | 18 (7.3.4 to 8.1.2) | yes [H] |
| `.VCi` variant (VC0...VCZ, then VDi...) | text, PVObject tree; hourly results in base-62 records | UTF-8 with BOM, CRLF | 22 (7.3.4 to 8.0.21) | yes for the design, the losses, the scene geometry and the results [H]; partly for parametric 3D objects |
| `.CMi` comparison variant | probably as `.VCi` [L] | | 0 | not needed |
| `.SIT` site | text, PVObject | UTF-8 with BOM | 2 | yes [H] |
| `.MET` weather | **text**, PVObject header and base-62 hourly records (the help still says binary) | UTF-8 with BOM | 7 | yes, decoded and checked [H] |
| `.MEF`, `.TFT`, `.DAF`, `.DAM` | unknown | | 0 | not needed |
| `.HOR` horizon | unknown; the help says "not an ASCII file" | | 0 | open: needs the trial |
| `.SHD` scene (also `.BLD`, `.SHO`) | text, PVObject | UTF-8 with BOM | 1 SHD, plus 12 scenes stored in variants | yes for positions and sizes; the parameters of elementary objects need the trial |
| `.PAN`, `.OND` | text, PVObject (6.40+); binary or hybrid before | UTF-8 (6.80+) or ASCII (6.40 to 6.79) | 7 PAN, 6 OND, plus 2 in `tests/data` | already read by `catalog/panond.py` |
| `.BTR` battery | text, PVObject | UTF-8 with BOM | 1 | yes [H] |
| optimizers | built-in database only; `.DCC` named by the PVCollada extension [unverified] | | 0 | by name only |
| `.PMP`, `.RLT`, `.RLP`, `.GEN`, `.REV`, `.PRI` | unknown | | 0 | not needed for a grid design |
| `.LOD` load | text, PVObject | UTF-8 with BOM | 1 | yes |
| `.SFI` output format, `.RVT` variable list | text (PVObject; one line `ResultVars=`) | UTF-8 with BOM | 1 SFI | yes |
| hourly CSV results | CSV, locale-dependent separators and labels | cp1252 up to 8.0.19; UTF-8 with BOM in 8.1.7 | 5 loose, 12 in a zip | yes [H] |
| batch CSV (`_BatchParams_`, `_BatchResults_`) | CSV | ASCII / cp1252 | 2 | yes [H] |
| PVsyst standard weather CSV | CSV with `#` header tags | cp1252 | 1 (+ the help's specification) | yes [H] |
| PDF report | PDF (Synopse engine); 7.x RC4 encrypted with an empty user password, 8.x not encrypted | | 11 loose, 12 in a zip | text and bookmarks readable: results summary yes |
| PVCollada 2.0 (`.pvc2`, `.pvz2`) | XML, valid COLLADA 1.5 | UTF-8 | 9 | yes: the best open route for layouts [H] |
| PVCollada 1.4.1 (`.pvc`) | XML, modified COLLADA 1.4.1 | | 2 | possible |
| Helios 3D (`.h2p`) | text blocks (Helios documentation) | | 0 | possible [M] |
| `.DAE`, `.3DS` | generic 3D formats | | 0 | as plain obstacles only |

**Feasibility** (analysis). Opening a `.PRJ` with a chosen variant is feasible now. The text format is
regular enough for a tolerant reader, and every real file found (68 PVObject files, 6.53 to 8.1.2) parses
with the same rules. What can be read, with the evidence:
- the site, the project settings and the monthly climate;
- the hourly weather of the `.MET`, decoded and checked against PVsyst's own monthly values (section 2.4);
- the orientations: fixed planes, sheds and trackers, read as data;
- the sub-arrays: module and inverter file names, modules in series, strings, inverters, MPPT topology;
- the main losses, each checked against the same project's PDF report;
- the 3D scene: PV tables and sheds with positions and sizes, buildings and obstacles as parametric
  objects;
- the results, monthly and hourly, equal to the report to the kWh.

What is missing:
1. The module and inverter parameters: a variant names the `.PAN` and `.OND` files and does not contain
   them. They must travel with the project (PVsyst's export with referenced files), or come from
   Meridiana's catalogue, or be chosen by the designer.
2. The horizon: no public variant has one, and `.HOR` was found nowhere.
3. Storage, the detailed module layout, optimizer settings, monthly soiling and sub-hourly weather:
   no real sample, only one unofficial source.
4. The meaning of the `Params` list of each elementary 3D object (house, roofs, chimney, tree...).
5. Whatever Meridiana does not model: trackers, bifacial gain, MV transformers, auxiliaries, reactive
   power, economics in PVsyst's form.

The PVsyst 8 trial can close points 2 to 4 (section 8).

---

## 1. Method and sources

### 1.1 Method
1. **PVsyst 8.1 online help.** I read the full text of every page through the help's own search index,
   the same one used for study 06. Pages are cited by URL under `https://www.pvsyst.com/help/`.
2. **Real files.** Public files from 20 sources: 61.7 MB, PVsyst 6.53 to 8.1.7. They are kept outside
   the repository in `C:\Users\utente\dev\meridiana-prove\pvsyst-campioni\`, whose `README.md` gives
   each source's URL, licence, date and the SHA-256 of every file.
3. **Own readers.** I wrote these readers for this study from the files alone:
   - a tolerant PVObject parser;
   - a decoder of the base-62 records;
   - a reader of PDF text and bookmarks.

   I ran them with `python -I` from another folder. They live in
   `C:\Users\utente\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\formati\`:
   `pvobj.py`, `vcdecode.py`, `metprobe.py`, `pdftext.py`, `pdftoc.py`. No downloaded file was executed or
   opened with PVsyst.
4. **Cross-checks.** I compared the values in the variant files with the PDF report and the hourly CSV
   that PVsyst wrote for the same project.
5. **Other parsers.** Public parsers, and two unofficial "MCP" projects that automate PVsyst, read
   read-only through the GitHub API.
6. **Legal texts.** PVsyst's General Conditions of Use and subscription contract (PDF), EUR-Lex,
   Normattiva, Fedlex.

### 1.2 Sample sources (URLs; full list of files and hashes in the samples README)

| Id | Source (commit) | Licence | PVsyst | Content used |
|---|---|---|---|---|
| S1 | https://github.com/jdnewmil/BifiOutboard/tree/f9d0db69bf25753b24bfb2f2a4c313479ab05026/data | MIT | 7.3.4 | two exported projects (bifacial fixed sheds VC0 to VC4, single-axis tracker VC0 to VC2) with MET; hourly CSV and report of each VC0; an SFI |
| S2 | https://github.com/luko12/PV-design/tree/6a05964f19d229bb37615463648ded4b91206715 | none | 8.0.11 | PRJ; VC0 without results; VC1 with results (E-W trackers, ageing, unavailability, auxiliaries, grid limit, MV transformers) |
| S3 | https://github.com/karlolesonche/PVsyst_Seattle_Residential_Project/tree/98e8d2d799b3b2d3ae8c92e37654617b2d24874e | none | 7.4.2 | PRJ, rooftop SHD (house, roofs, chimney, trees), MET (NREL TMY), report |
| S4 | https://github.com/youefkh05/PV_plant_model/tree/d85c364fad64d75d0649ad405c36068d9976cca4/Simulation | Apache-2.0 | 7.4.6 | PRJ, VC0, MET, SIT, LOD, report |
| S5 | https://github.com/vivekmohanlohar/pvsystprojects/tree/d1eeef9a26e95c1e22b33c70b5a02bc1ba1c00f0 | none | 8.0.7 | six projects (residential, unlimited sheds, pumping...), MET, reports (trial) |
| S6 | https://github.com/sabya169/PVsyst/tree/f79644e6bb1c42ffe29c25af93dab05edcfc5ba6 | none | 7.4.0 | PRJ, VC0, MET, SIT, report (trial) |
| S7 | https://github.com/kathirvel13/Rooftop_Solar_Grid_Planning_PVsyst/tree/fce80ba2238c4228bd11d3b493fd763edfa2de28 | none | 7.4.7 | PRJ, VC0 with tables on a building, daily load, economics; MET, OND, report |
| S8 | https://github.com/Abdelhamid-ElSharnouby/Utility-Scale-Grid-Connected-PV-System/tree/337290fb40486e13b1f85fa88da080b73281918a/pvsyst | none | 8.0.19 | PRJ and a 14-page report (trial) |
| S9 | https://github.com/nmori613/Solar-PV-Design-and-DER-Projects/tree/27ea9d056bcf8c6989e8a467d81104ac697ed8b1 | none | 8.0.5 | rooftop with SolarEdge optimizers, 3 orientations, 9 tables and a 14-object building; bifacial sheds farm with load, economics, loans |
| S10 | https://github.com/IKH-116/kuwait-university-grid-connected-pv-system/tree/a23904a6af01b249c81af35d9981dcb9ccbd63cd | none | 8.0.21 | exported project zip (PRJ, MET, VC0) and report |
| S11 | https://github.com/Yegane-001/10MW-Solar-Power-Plant-PVsyst/tree/894845fe8dc2022c564c759efe99a23400753685 | none | 8.1.2 | PRJ |
| S12 | https://github.com/Carnatie/Arquivos-de-Simula-o-Deye-para-PVSyst-Biblioteca-T-cnica/tree/02b536879eecd6f6661033b9a437965d741e7bea | MIT | 7.4.6 | BTR, two OND |
| S13 | https://github.com/frivollier/pvsyst_tools/tree/f6e8e4b9e181586208fcb797b89df8a36bf1f705 | none | 6.53 to 6.84 | six PAN, two OND |
| S14 | https://github.com/plantpredict/python-sdk/tree/14965d971cde4af70eb0193b36ed6ca989addb02 | MIT | 7.211, 6.64 | CdTe PAN, OND |
| S15 | https://github.com/sijinwnag/25_09_02_Bomen_bifacial_gain_2021/tree/522ec387521f467ead6b111e8da52ace6e768e5a | none | 8.0.x | BatchParams and BatchResults CSV |
| S16 | https://github.com/Albertoscimonelli/PV_SOLAR_OPTIMIZATION/tree/695b12cc44604ffba840a9128317c88c1477aeb7 | none | 8.0.19 | hourly CSV written in Italian |
| S17 | https://github.com/twj0/air-conditioning-design/tree/6ffbd073c7a5ad7e33fe8961ca5da3d35a171940 | WTFPL (data from climate.onebuilding.org, no licence stated) | | PVsyst standard weather CSV (`.pvsyst`) |
| S18 | https://github.com/Angelthebestone/PVSYST-MCP/tree/e3c994de7126a6f1e6c24a5d6d43e1f8699975f1 | Apache-2.0 | 8.1.7 | unofficial notes; synthetic PRJ/VC0/PAN/OND written by its author; CSV and PDF written by PVsystCLI 8.1.7 (trial) |
| S19 | https://zenodo.org/records/18109134 | CC-BY-4.0 | 8.0.17, 8.0.18 | 12 hourly CSVs and 12 reports (PVGIS SARAH3 2023 weather) |
| S20 | https://github.com/pvlib/pvcollada/tree/68ad4388e6b6e3b3f8646767eb74c954312650af | BSD-2-Clause (LICENSE); docs say MIT | | PVCollada 1.4.1 and 2.0 samples and schemas |
| S21 | `tests/data/pvsyst/` in this repository (from pvlib's test data) | BSD-3-Clause | 7.2 | one PAN, one OND |

Unofficial sources used for hints only, always marked [unverified]:
- U1 https://github.com/Anonymousnake/pvsyst-cli-mcp (MIT, documentation in Chinese, PVsyst 8.1.6);
- U2 the notes of S18 (`docs/pvsyst_format.md`, `PVSYST_CLI_REFERENCE.md`).

Searched and **not found** in public: any `.HOR`; any real variant with storage, a horizon or a module
layout; any 6.x project or variant; `.MEF`, `.PRI`, `.RLT`, `.GEN`, `.PMP`, `.CMi`, `.DAM`, `.BLD`,
`.SHO`; Helios `.h2p` files; PVsyst's template files (`METEO_PVsyst_Standard_Geneva_GHI.CSV`,
`PARAMS_Hourly_Template.CSV`, `LOADPROFILE_*`). GitHub code search skips binary files and files above
about 384 KB, so variants with results (over 1 MB) are found only through repository trees.

---

## 2. The common text format ("PVObject")

### 2.1 History and encoding
- The official history (https://www.pvsyst.com/help/getting-started/file-organisation/user-data/format-of-pvsyst-files.html) [H]:
  - up to 6.39 every file was binary;
  - from 6.40 every file is text;
  - in 6.60 the variant format was improved;
  - from 6.80 the files are UTF-8.

  Each change made the files unreadable by older versions, hence one workspace folder per format
  (`PVsyst6_Data`, `PVsyst640_Data`, `PVsyst660_Data`, `PVsyst680_Data`, `PVsyst8.1_Data`).
- The same page calls the format "intended for internal use only", gives "no support" and says the
  files "should not be modified" [H].
- Encoding observed [H]: every real PRJ, VCi, SIT, MET, SHD, BTR, LOD and SFI (7.3.4 to 8.1.2) starts
  with the UTF-8 BOM (`EF BB BF`) and uses CRLF.
- PAN and OND [M]:
  - 6.53 to 6.79 are plain ASCII without BOM (S13);
  - 6.84 has the BOM (S13);
  - some 7.x copies have none (S21).
- Since 7.0.10 PVsyst can save PAN and OND "in old format using ANSI encoding", readable by 6.40 to 6.79
  (https://www.pvsyst.com/help/release-notes/index.html , 7.0.10) [H].
- Non-ASCII text is kept in UTF-8 inside the file, while file names are made ASCII: site
  `Jalīb ash Shuyūkh`, file `Jal_b ash Shuy_kh_MN82_SYN.MET` (S10) [M].
- Pre-6.40 binary PAN files are a hybrid of ASCII header lines and 6-byte Delphi `Real48` numbers,
  according to S18's notes [unverified]. The only example is synthetic.

### 2.2 Lines and structural markers
One item per line. Indentation is two spaces per level as written, but it is **not reliable**: inside the
3D PV objects a run of keys (`NElemChamps` to `ModuleOrient`) is written two columns to the left of its
object (S1, S3, S7, S9) [H]. A reader must follow the markers.

| Construct | Opener | Closer | Examples | Conf. |
|---|---|---|---|---|
| root object | `PVObject_=<type>` | `End of PVObject <type>` | `PVObject_=pvProject` | [H] |
| child object | `PVObject_<role>=<type>` | `End of PVObject <type>` | `PVObject_SiteSimul=pvSite` | [H] |
| list | `<Name>, list of=<n> <TItem>` | `End of <Name>`, `End of the List <Name>` or `End of List <Name>` | `ListeObjets, list of=4 TShdObject`; `VarMeteo, list of=5 TVarSimul` | [H] |
| counted list | `<Name>, Count=<n>` then `Str_i=` or `Err_i=` lines | `End of <Name>` | `Remarks, Count=3`; `ErrorList, Count=1` | [H] |
| typed record | `<Key>=T<Type>` with deeper lines below | `End of T<Type>` or `EndTags` | `IAMProfile=TCubicProfile`; `SFTable=TInterpole2D`; `PrintSettings=TPrintSettings` ... `EndTags` | [H] |
| group | `<Key>=Start` | `<Key>=End` or `EndTags` | `BaseNode=Start` ... `BaseNode=End`; `SubArrays=Start` ... `EndTags` | [H] |
| circuit node | `<Node> Start;` | `<Node> End;` | `InverterNode Start;`, `MPPTNode Start;`, `Empty NodeNode Start;` | [H] |
| list item record | `<ItemType>=<i>` with deeper lines | `EndTags` | `InvestmentCost=1` | [M] |
| variable | `VarSimul_<i>=<name>` | `End of VarSimul=vi<name>`, after `End of Data` | `VarSimul_6=GlobHor` | [H] |

Irregular closers, seen in every file of the versions that have them [H]:
- `End of TInterpolenD` closes `TInterpole2D`;
- `End of TSimulFich` closes the object `PVObject_SimulFich=pvSimulFile`;
- `End of TOrientGroup` closes a `PVObject_=pvOrient` list item;
- `End of TAgeing` closes `pvAgeing`;
- `End of TPipe` closes a pipe record.

An empty remark may lose its `=` (`Str_3` alone) [M]. A root key can follow a nested object at the same
indentation (`Albedo=` after `End of PVObject pvSite` in the PRJ) [H].

### 2.3 Values
- Decimal point always `.`, in every file of the corpus, whose authors are in the US, Canada, India, Kuwait,
  Iran and Brazil [H].
- Lists:
  - comma-separated with a trailing comma [H];
  - site monthly lists have 12 months plus the year (13 values); the project's monthly albedo has 12 [H].
- Booleans and flags:
  - booleans are `True`/`False` [H];
  - bit fields are Delphi hexadecimal (`Flags=$0006083F`) and their meaning is not documented [H].
- Enumerations carry a type prefix [H]:
  - `mtSiMono`, `moPortrait`, `moLandScape`, `oeTree`;
  - `foLinear`, `osPVsyst`, `refGeographical`;
  - `ltFixedAnnuity`, `uiW`, `slTwinHalfCells`.
- Dates are `DD/MM/YY HH:MM` in every file, including files from US users whose CSV output is MM/DD
  (S1) [H]. Year 1990 (or 2059) marks generic TMY or synthetic data
  (https://www.pvsyst.com/help/meteo-database/import-meteo-data/pvsyst-standard-format.html) [H].
- Some values carry their unit: `Resistance=3.72431897329082 mΩ`, `OutputVoltage=34.5 kV` [H].
- `Comment=` is free text [H]:
  - sites separate fields with `;` (`Sacramento/McClellan Park;United States;North_America;`);
  - components separate them with TAB (`Deye<TAB>BOS-G 12 - 61.44 kWh<TAB>Datasheet 2023`).
- Long values are split [H]: the first line ends with `contd,` (lists) or `+contd+` (records), and the rest
  follows on `<Key>_contd=` lines. Examples: `VarIdentWr_contd`, `ValuesX_contd`, `Accum_contd`,
  `Err_1_contd`.
- **Default values are not written** [M]:
  - a fixed plane facing south has no `AzimPlR`;
  - a wind factor Uv of 0 leaves out `UVFactor` (S7: the report says "Uv 0.0");
  - a circuit node with one element leaves out `NElements`.

  (analysis) This is Delphi's streaming rule, which skips a property equal to its declared default. A
  reader needs the defaults: they must be collected with the trial, by moving each value away from its
  default.
- **Units differ key by key** and follow PVsyst's dialogs. `SoilingLoss=0.030` is 3 % (a fraction),
  `LIDLoss=1.00` is 1 % (a percentage), `RSCablageCh=3.724` is in mΩ. Each was checked against the
  report (section 3.2) [H].

### 2.4 Compact numeric records (weather and results), decoded and checked
- **Day records** [H]:
  - one line per day, `Day_DDMM=+v1+v2+...+v24` for hourly data, ordered by month and day (`Day_0101`
    to `Day_3112`);
  - each token is a sign followed by base-62 digits in the order `0-9A-Za-z`, most significant first;
    `+0` is zero.
- **Value** = integer / `WRFactor` (a key of each variable), in PVsyst's internal unit [H]:
  - irradiation per hour in MJ/m² (`WRFactor=2777.778`, so a step of 0.1 W/m²);
  - energy in MJ (`WRFactor=17.36111` in S1, a step of 16 Wh);
  - angles in radians (`572.9579`, a step of 0.1°);
  - temperature in °C and wind in m/s (`100`, a step of 0.01);
  - relative humidity as a fraction (`2000`).
- **Checks**, run with my decoder on S1:
  1. The monthly sums and means of the decoded `.MET` equal the monthly values PVsyst wrote in the same
     file: T_Amb 7.0, 9.1, 12.6, 15.3 °C; GlobHor 61.4 kWh/m² in January; DiffHor 32.8. [H]
  2. The decoded hourly values of the variant VC0 equal the hourly CSV that PVsyst wrote in the same
     run: T_Amb within 0.0004 °C; TArray within 0.006 °C; GlobHor with a constant ratio of 0.0036
     (MJ/m² to W/m²). [H]
  3. The decoded monthly E_Grid of VC0 equals the report: 196,038 kWh in January, 4,436,353 kWh a year;
     GlobInc 90.6 kWh/m² in January. [H]
- **Other numeric records** [H unless marked]:
  - `Point_k=x,y` in `TCubicProfile` curves (IAM, inverter efficiency, battery curves);
  - `Line_k=` comma lists in `TInterpole2D` shading tables: 19 azimuth bins from -180° to 180° by 20°,
    10 sun heights from 0° to 90° by 10°;
  - `ValuesX`, `ValuesY` and `ValuesZ` of the stored plots: a count, probably a scale, then base-62
    tokens [L];
  - `Accum=` histogram bins [M].
- **Other sources**: the two unofficial MCP projects also describe the `.MET` records as base-62 text
  (S18 notes, U1) [unverified]. Neither decodes them, and no public decoder was found.

### 2.5 Rules for a reader (analysis)
1. **Decoding.** Decode as UTF-8 with BOM, then plain UTF-8, then cp1252. Accept CRLF and LF.
2. **Structure.** Build the tree from the explicit markers of 2.2 with a stack. Close an object by name,
   and the irregular closers by a short whitelist. Use indentation only to tell a typed record
   (`Key=TType` followed by deeper lines, or closed at once by `EndTags` when empty, as
   `Custom_LCE_Definitions=TEnergyMixSet`) from a value that starts with T, such as `Varident=TArray`.
3. **Keys.** Keep every key, unknown ones included, and keep duplicates in order (`PVModule=` appears once
   per sub-array). Join the `_contd` lines.
4. **Large blocks.** Parse the `Day_` and `Line_` records lazily: a variant has 15,000 to 18,000 of them.
5. **Integrity.** Report anomalies (unclosed objects, unknown closers) with their line numbers, and do not
   fail on them. My parser, built this way, reads all 68 real PVObject files of the corpus into a single
   root each, with no unmatched closer; the only lines without `=` are empty remarks.
6. **Never write PVsyst files.** The help asks that they not be modified, and a wrong write could
   corrupt a user's project.

---

## 3. The formats one by one

### 3.1 Workspace, project folder and export
- **Workspace folders** (https://www.pvsyst.com/help/getting-started/file-organisation/user-data/workspace/index.html) [H]:
  - the user workspace (`C:\Users\<user>\PVsyst8.1_Data` by default) holds `Projects\` (PRJ, VCi, CMi,
    PSG/PSS/PSP), `Sites\` (SIT), `Meteo\` (MET, MEF, TFT), `Shadings\` (HOR, SHD, BLD, SHO) and
    `Models\` (LOD, SPL, SFI, RVT);
  - `ComposPV\` holds one folder per component type: PVModules (PAN), Inverters (OND), Batteries (BTR),
    Pumps (PMP), Regulators (RLT), RegulPmp (RLP), Gensets (GEN), Sellers (REV);
  - the remaining folders are `DataMeas\`, `UserData\`, `Templates\` and `PVsystCLI-Demo\`.
- **Built-in components.** The components of the built-in database live in the installation's read-only
  data, not in the workspace. The bundled `*DB.csv` databases are not plain text according to S18's
  notes [unverified].
- **Variant files.** A variant shares the project's name: `<Project>.VC0` to `.VC9`, then `.VCA` to
  `.VCZ` [H], and since 6.40 beyond that (`VDi`...): "Number of Calculation variants now illimited (VCi,
  VDi, etc)" (release notes 6.40) [H]. The `.PRJ` does not list its variants: they are found by name in
  the same folder (analysis, consistent with S1, S2, S5).
- **Export.** "File > Export components" copies a project, all or some of its variants, and optionally
  its "referenced files", into a folder tree, which can then be zipped
  (https://www.pvsyst.com/help/getting-started/file-organisation/user-data/projects-and-pv-components/export-projects-and-components.html) [H].
  - The exported zips found (S1, S10) are flat and hold PRJ, MET and VCi, but no PAN, OND or SIT,
    although their modules and inverters came from the built-in database [H].
  - Whether an export can include built-in components as files is unknown: trial case N.

### 3.2 Project (`.PRJ`) [H]
The project holds the site, the weather file's name and the project settings. Example (S1, 7.3.4, shortened):

```
PVObject_=pvProject
  Comment=Test Bifi Sheds                          <- project name
  Version=7.3.4
  Flags=$00080010
PrintSettings=TPrintSettings                       <- report options; 8.1 adds CoverPagePJNameText, PrintedSections
  PrintCoverPage=True
  ClientDesignation=Client
  UserDesignation=Author
  EnergyUnit=uikWh
EndTags
MeteoFileName=Sacramento_McClellan Park_MN81_SYN.MET
PVObject_SitePrj=pvSite                            <- the site, as in a .SIT (3.4)
  Latitude=38.6700
  Longitude=-121.4000
  Altitude=18
  TimeZone=-8.0
  GlobalH=61.4,83.2,...,1799.4,                    <- 12 months + year
  ...
End of PVObject pvSite
Albedo=0.200,0.200,0.200,0.200,0.200,0.200,0.200,0.200,0.200,0.200,0.200,0.200,   <- monthly "far albedo"
DesignTempMin=-10
TempOper=50
TempOperMin=20
TempOperMax=60
LimOverloadLoss=3.00
DiscrOrientDiff=1.00
SpreadMaxDiff=10.00
MaxSystem_ShdRatio=2.50
RegionMeteo=1
CorrAlttemp=-0.0055
SiteMeteoMaxDistForList=10
TranspositionAlgorithm=CircSolSeparate
ACLossesRef=STC
End of PVObject pvProject
```

Meaning of the settings, from the project settings page
(https://www.pvsyst.com/help/project-design/project-definition/project-settings.html) and the key names
(analysis where marked):
- `Albedo`: the monthly far albedo [H].
- `DesignTempMin`: the minimum site temperature for the absolute-voltage warning [M].
- `TempOper`, `TempOperMin`, `TempOperMax`: the reference temperatures for array sizing [M].
- `LimOverloadLoss`: the acceptable overload loss for sizing, in % [M].
- `SpreadMaxDiff` and `MaxSystem_ShdRatio`: the tolerances between the 3D scene and the system (averaged
  orientation, area ratio) [L].
- `SiteMeteoMaxDistForList`: the search radius for weather files, in km [M].
- `TranspositionAlgorithm=CircSolSeparate`: Perez with the circumsolar part treated separately; the
  reports print "Perez ... Circumsolar separate" [H].

Version notes: the 6.40 example on the help page has the same layout, plus `MeteoFileDate`. PRJ 8.1.2
(S11) adds `PrintedSections=proCoverPage,proVCSummary,proVCParams,proVCShadings,...` and
`SourceType=Meteonorm90DLL` in the site [H].

### 3.3 Variant (`.VCi`) [H]
A variant holds one system definition and, after a simulation, its results. It is 16 KB without results
(S2 VC0) and 1.2 to 1.7 MB with them [H]. Layout of a variant with results (S1, S7, S9, S10):

```
PVObject_=pvVCalcul                         Comment=<variant name>, Version, DateDebS/DateFinS (period),
                                            DateCalcul, VersionSimul, SimDuration, SystemKind ("Tables on a
                                            building", "Unlimited sheds", ...), TranspositionAlgorithm
  PVObject_SiteSimul=pvSite                 copy of the site used
  PVObject_MeteoSimul=pvMeteo               copy of the weather file's header (no hourly data)
  7.x: PVObject_EnIncidente=pvEnIncid > PVObject_PlanCapteurs=pvCollPlane     one orientation
  8.x: Orientations, list of=n TOrientGroup > PVObject_=pvOrient ... End of TOrientGroup   n orientations
  PVObject_PVMainArray=pvMainArray          array-level losses, bifacial (7.x), ageing, AC/MV wiring
    PVObject_SystemCircuit=pvCircuit        single-line diagram: inverters, MPPT inputs, strings, cables
    SubArrays=Start
      PVObject_=pvSubArray                  one per sub-array: module, inverter, strings, losses, IAM
    EndTags
  PVObject_System=pvSystem                  system type, grid limit, power factor, auxiliaries, unavailability
  PVObject_Ombrage=pvShading                the 3D scene and its shading factor tables (3.8)
  PVObject_UserNeeds=pvLoad                 user's needs (load)
  EconomicEval=TEcoEvaluation, P50_P90=TP50_P90, PVObject_CarbonBalance=pvCarbonBalance
  PVObject_SimulFich=pvSimulFile            hourly output settings (as an SFI file, 3.13)
  SimulPlots=Start ... EndTags              the report's predefined plots, with their values
  VarList, list of=n TVarSimul              every simulation variable: monthly values, hourly records
  ErrorList, Count=n                        warnings of the run
End of PVObject pvVCalcul
```

**Orientation, 7.x** (`pvCollPlane`) [H]:
- `FieldType`: `FixedPlane` or `TrackHorizNSAxis` in the samples.
- Fixed plane: `InclPlR` (tilt), `AzimPlR` (azimuth, omitted when 0).
- Trackers: `InclAxe`, `AzimAxe` (axis), `AzimMin`, `AzimMax`, `InclMin`, `InclMax` (limits),
  `NSheds`, `Pitch`, `LargCapt`, `LargHaut`, `LargBas`, `LargCell`, `NStringLarg`.
- Checked against S1's tracker report:
  - `AzimMin=-60`/`AzimMax=60` print as "Phi min / max. -/+ 60.0°";
  - `Pitch=5.000` is the "Tracker Spacing";
  - `LargCapt=2.465` is the "Collector width";
  - `NSheds=49` is the "Nb. of trackers";
  - `Flags=$0400` goes with "Backtracking activated".

**Orientation, 8.x** (`pvOrient`, one per orientation) [H]:
- Common: `NoOrient`, `FieldType`, `FieldTilt`, `FieldAzim`, `BaseSlope`, `UsesTiltAver`,
  `UsesAzimAver`, `UsesSlopeAver`.
- Sheds: `NSheds`, `Pitch`, `CollectorWidth`, `InactiveBandWidth1/2`, `UsesElectricalEffect`,
  `FracShadingFactor`, `NModInWidth`, `CellWidth`.
- Trackers: `AxisAzim`, `MinTilt`, `MaxTilt`, `PitchSlope`, `UsesBacktracking`.
- Each orientation carries its own linear shading table (`PVObject_ShdTableLin=pvShdFTable`) and, when
  bifacial, its `pvBiFacial` block (S9, 8.0.5).
- `FieldType` values seen [H]: `FixedPlane`, `Sheds`, `TrackHorizNSAxis`, `TrackHorizAxis`.
- Values listed by U1 [unverified]: `SeasonalTilt` (with `SummerTilt`, `WinterTilt`, `WinterMonths`),
  `Dome`, `SunShields`, `UnlimTracking`, `TrackTiltedAxis`, `TrackVertAxis`, `TrackSunShield`,
  `TrackTwoAxis`, `TrackFrameNS`, `TrackFrameEW`.

**Array level** (`pvMainArray`) [H unless marked]:

| Key | Meaning | Unit | Check against the report |
|---|---|---|---|
| `UFactor` | thermal Uc | W/m²K | 25.0 and 29.0 print as "Uc (const) 25.0 / 29.0" (S1, S7) |
| `UVFactor` | thermal Uv; omitted when 0 | W/m²K/(m/s) | 1.2 prints as "Uv (wind) 1.2"; absent prints "0.0" |
| `Alpha` | absorption coefficient | fraction | (0.9 in all samples) |
| `UFAverEffic` | module efficiency used by the thermal model [L] | % | |
| `SoilingLoss` | yearly soiling | **fraction** | 0.030 prints as "Array Soiling Losses 3.0 %" (S7) |
| `UseSpectralCorr` | spectral correction on/off | | |
| `NoYearSimul`, `DegradLossFactor`, `DegradMismFactor`, `PVObject_Ageing=pvAgeing` (`ModuleDegradFactor` %/year, `ImpDegradSharing`, `ModuleYearWarr`, `ModuleWarranty`) | ageing tool | | S2; the report of S3 prints "Module Degradation Loss (for year #30)" [M] |
| `ACWireNoSect`, `ACWireLength`, `ACWireMetal`, `VOutTransfo`, `MVWire*`, `MVNbTransfos`, `TrfIronLossFrac`, `TrfResLossFrac` | AC and MV wiring, transformers | m, V, fraction | S2 [M] |
| `PVObject_Bifacial=pvBiFacial` (7.x here; 8.x inside `pvOrient`) | `BifacialModel` (`Sheds2D`, `Trackers2D`), `GroundAlbedo`, `BiFacialityFactor`, `RearShdFactor`, `MismatchLossFactor`, with `pvBiFacialSheds` or `pvBiFacialTrackers` (`HeightGr`) | fractions, m | S1 VC1 to VC4, S9 |
| `SEInverterList=TSEInverterList` | SolarEdge inverter inputs | | S9 [M] |

**Sub-array** (`pvSubArray`, one per sub-array; S9 has three) [H unless marked]:

| Key | Meaning | Unit | Check against the report |
|---|---|---|---|
| `Comment`, `SubArrayId` | sub-array name and id | | |
| `PVModule` | module file name (`.PAN`) | | the report prints the model; parameters are **not** in the variant |
| `GInverter` | inverter file name (`.OND`) | | as above |
| `Optimizer`, `OptIN_NModSerie`, `OptIN_NModParall`, `NOptSerie` | optimizer by name, modules per optimizer input, optimizers per string | | S9 [M] |
| `NModSerie`, `NStringCh` | modules in series, strings | | "245 Strings x 18 In series" (S1) |
| `NStrOrient<k>`, `NoOrientation` | strings on orientation k; orientation of the sub-array | | S9, S10 |
| `NInverter`, `NInvMPPT`, `PNomAC_InMPPT`, `PowerSharingInverterId` | inverters, MPPT share, AC power of the share (kW) | | S7: `NInvMPPT=2`, `PNomAC_InMPPT=12.50` print as "2 * MPPT 50%" on a 25 kW inverter [M] |
| `PQualityModU/I/P` | module quality loss | % | -0.75 prints as "-0.8 %"; 0.50 as "0.5 %" |
| `PMismMPP` | module mismatch | % | 1.00 prints as "1.0 % at MPP" |
| `PMismString` | string mismatch; omitted when 0 | % | 0.15 prints as "0.2 %"; 0.05 as "0.1 %" |
| `PMismUFixe` | mismatch at fixed voltage [L] | % | |
| `LIDLoss` | LID | **%** | 1.00 prints as "1.0 %"; 1.50 as "1.5 %" |
| `LightSoaking` | light soaking | % | |
| `RSCablageCh`, `RSCablagePC` | DC wiring: global resistance, loss at STC | mΩ, % | "Global array res. 3.7 mΩ, Loss Fraction 1.5 % at STC" |
| `VDiodeSerie` | series diode drop | V | |
| `VInitDegrad`, `AreaSizing`, `PNomSizing` | sizing helpers | | |
| `PVObject_IAM=pvIAM` | `IAMMode` (`FresnelSmooth`, `FresnelAR`, `Default` with `B0_IAM`, `UserProfile`), `N_Glass`, `N_EVA`, `N_ARCoating`, `DGlass`, `DArCoating`, and a 9-point `TCubicProfile` | | the 9 points print in the report's IAM table (S1, S7) |
| `ACWireNoSect`, `ACWireLength` | AC wiring of the sub-array | | |
| `Controller`, `MPPTEfficMax`, `MPPTEfficEuro`, `VMinMPPTUser`, `VMaxMPPTUser` | pumping controller | | S5 |

**Circuit** (`pvCircuit`, the single-line diagram) [M]:
- The node tree is: `InjectionPointNode` > optional `TransformerNode` (`OutputVoltage`, `STCRefPower`,
  iron and copper loss fractions) > optional `Empty NodeNode` > `InverterNode` > optional `MPPTNode` >
  `StringNode` (with `CableDefinition`, `Resistance` in mΩ).
- `NElements` counts the repetitions of a node and is omitted when 1.
- Checks:
  - S7: 1 inverter, `MPPTNode NElements=2`, `StringNode NElements=2`, giving 4 strings (`NStringCh=4`);
  - S10: `InverterNode NElements=2`, `MPPTNode NElements=6`, one string each, giving 12 strings
    (`NStringCh=12`).
- This is where the **assignment of strings to MPPT inputs** is written.

**System** (`pvSystem`) [M]:
- `SystemType`: `Grid`, `Pumping` [H].
- `TanPhi`: reactive power; 0.329 corresponds to cos φ 0.95.
- `PLimGrid`: grid injection limit, in kW (60,000 for a plant of about 71 MWp, S2).
- `AuxPower_Const`, `AuxPower_CThresh`, `AuxPower_Night`: auxiliaries [L on units].
- Unavailability [M]:
  - `UnavTotDuration`, in days (7.30);
  - `UnavNbPeriods` (3);
  - `UnavDuration`, in hours per period (58, 58, 58);
  - `UnavBegDate`, the start of each period.

  Three periods of 58 h are 7.25 days, consistent with the total (analysis). Grid outages in 8.1 use
  `PVObject_GridUnavail=pvUnavail` according to U1 [unverified].
- Pumping keys: well and tank geometry (S5).

**Storage** (no real sample). Key names given by S18 and U1 [unverified]:
- in `pvSystem`: `BatteryFile`, `NBattSerie`, `NBattParall`;
- in a `pvGridStorage` block: `Strategy` (`SelfConsumption`, `PeakShaving`, `WeakGrid`),
  `ChargingStrategy`, `DischStrategy`, `BattSoCInit`, `SOCChDecl`, `SOCDischDecl`, `SOCDischSelf`,
  `PMaxCharge`, `PMaxDisch` (kW), `BattRectMaxEffic`, `BattRectEuroEffic`, `BattInvMaxEffic`,
  `BattInvEuroEffic` (%).

Trial case J.

**Monthly soiling, albedo series, other 8.1 additions**:
- U1 describes a `Soiling=Soiling` block in `pvMainArray`, with `IsYearly`, `IsMonthly`, `IsFromFile`,
  `YearlyValue`, `MonthlyValue` (12 fractions), closed by `EndTags`. It replaces the single `SoilingLoss`
  seen in 7.x and 8.0 [unverified].
- Imported time series (load, soiling, albedo, unavailability, tariffs) are stored inside the variant:
  "it will display the time series as recorded in the variant" when the CSV is missing
  (https://www.pvsyst.com/help/project-design/Import-time-series-parameters.html) [H].

**Load** (`pvLoad`) [M]:
- `LoadType`: `Constant`, `DailyProfile`, `WaterNeeds`.
- `ConstantLoad`.
- `ValHour_1`: 24 hourly values.
- `Energy Units`: a key with a space.
- `UsesModul`: `Yearly`, ...
- The same object is the `.LOD` file (3.11).

**Results** [H]:
- `VarList` has one `TVarSimul` per variable (120 to 137 in the samples):
  - `Varident`, `VarAcc`, `VarType`, `VarMode`;
  - `VarStore` (`Simul` keeps hourly records, `Show` only monthly values);
  - `WRFactor`, `ValMonth` (12 monthly values);
  - the `Day_` records.
- 37 variables are kept hourly in S1's VC0 and 48 in its bifacial VC1. They are decoded as in 2.4. The
  report's monthly table (GlobHor, DiffHor, T_Amb, GlobInc, GlobEff, EArray, E_Grid, PR) can be rebuilt
  from them exactly (section 2.4, check 3).
- `ErrorList` holds the run's warnings as `Err_i=<when>;<level>;<code>;<text>`. Example:
  `ewSAG_VocNotDegraded_GT_VMax`.

**Economics, P50/P90, CO2** [M]:
- `TEcoEvaluation`: `Currency`, `ProjectLife`, `InvestmentCosts`, `OperatingCosts`, `Loans`, tariffs.
- `TP50_P90`: the variabilities.
- `pvCarbonBalance`: life-cycle emissions.
- These are outside the scope of a design import (analysis).

**Components are referenced, not embedded** [H]:
- The variant names the PAN and OND files.
- The scene keeps only the module's name and size: `PanneauPVName=HT78-18X-580 Bifacial;1.134;2.465`,
  that is model, width and height in m.

### 3.4 Comparison variant (`.CMi`)
"Variant of a simulation-measured data comparison, similar to the simulation variant" (workspace page).
No sample; outside Meridiana's needs.

### 3.5 Site (`.SIT`) [H]
`PVObject_=pvSite` with:
- identity: `Site`, `Country`, `Region`, `Source`, `SourceType` (`Meteonorm81DLL`, `Meteonorm82DB`,
  `Meteonorm90DLL`, `NREL_NSRDBTMY`...);
- position: `Latitude`, `Longitude` (east positive), `Altitude` (m), `TimeZone` (hours from UTC), `HLeg`
  (legal time);
- display and climate: `UnitsDisp`, `Albedo`, `DateBeg`, `DateEnd`;
- monthly lists (12 months plus the year): `GlobalH`, `DiffuseH` (kWh/m² a month), `TAmb` (°C),
  `WindVel` (m/s), `Linke`, `RelHum` (fraction), `Extraterr`;
- `YrToYrVar`, the year-to-year variability in % (S4, S6).

The same object sits inside the PRJ, the MET and the variant. PVsystCLI can create a `.SIT` from a CSV
of 14 rows (names, units, 12 months), with `GlobH` and `Temp` required
(https://www.pvsyst.com/help-cli/reference/index.html) [H].

### 3.6 Weather (`.MET`) [H]
- **Contradiction.** The help's workspace page describes `.MET` as "in binary format". All seven real
  files (7.3.4 to 8.0.21) are UTF-8 text.
- **Header** (`pvMeteo`):
  - `SiteM`, `SourceM`, `TypeM` (`Synthetic`, `TMY`), `NomFSource`, `NomFormat`, `SourceTypeOrig`,
    `SourceTypeFmt`;
  - `UsesPerez`, `DateDebF`, `DateFinF`, `IsSourceUt`;
  - `HourShift`, `TimeShift`, `TimeShiftImported`;
  - `PasAccum` (minutes per step: 60) and `FirstRandomSeed`;
  - the nested `pvSite`;
  - `VarMeteo, list of=n TVarSimul`, with `GlobHor`, `DiffHor`, `T_Amb`, `WindVel`, `RelHum` and their
    `Day_` records (2.4).
- **Variables.** A `.MET` may hold GlobHor, DiffHor and T_Amb (required), and also GIPMeas, BeamNor,
  BeamHor, WindVel, TArrMes, PrecWat, RelHum, Linke, AoD, Albedo and T_DewPt
  (https://www.pvsyst.com/help/meteo-database/index.html) [H].
- **Time.** Time labels are the start of the interval, and data are stored in winter (standard) time
  (help, weather data pages; study 06, section 1.6) [H].
- **Sub-hourly** (8.1). PVsyst 8.1 simulates at the `.MET`'s step. Sub-hourly files presumably have
  `PasAccum` below 60 and more tokens per day [unverified]: trial case L.
- **Meteonorm.** Files named `*_MN81_SYN.MET` and `*_MN82_SYN.MET` are Meteonorm synthetic data. See the
  legal note (9.1) on exporting Meteonorm data.

### 3.7 Weather and time-series files on the import side
- **PVsyst standard format CSV**
  (https://www.pvsyst.com/help/meteo-database/import-meteo-data/pvsyst-standard-format.html) [H]:
  - Header lines start with `#`. The first line is `#Weather data hourly data` or `#TMY hourly data`.
  - Required tags: `#Site`, `#Country`, `#Data Source`, `#Time step`, `#Year` (when not in the data),
    `#Latitude`, `#Longitude` (west negative), `#Altitude`, `#Time Zone`.
  - Optional tags: `#Time reference; UT+X`, `#Hour Shift`, `#Time Shift`, `#Plane tilt`, `#Albedo`,
    `#Summarization period`.
  - Then a row of column names, a row of units, and the data. The date is in separate `Year`, `Month`,
    `Day`, `Hour`, `Minute` columns, with the time at the start of the interval. The data columns are
    `GHI`, `Tamb` or `GPI`, plus optional `DHI`, `DNI`, `WindVel`, `RH`, `Pw`, `Linke`, `Aod`.
  - Year 1990 or 2059 means generic data. The separator is `;` or `,`, with a decimal point.
  - The TMYx sample (S17, cp1252) runs `Hour` from 1 to 24 with `Minute=30`, an EnergyPlus habit
    [M]. A reader must accept both conventions.
- **Time-series parameters** (load, storage, soiling, albedo, unavailability, tariffs)
  (https://www.pvsyst.com/help/project-design/Import-time-series-parameters.html) [H]:
  - CSV "saved in ANSI encoding (not UTF-8)"; `#` comment lines;
  - a header row and a units row; one date and time column;
  - a whole year with a regular step; the year itself is ignored.
- **Load profiles** in CSV, with `LOADPROFILE_*.CSV` templates (BDEW). "Store internally" keeps the values
  in the variant; "Read the file" copies the CSV to `UserHourlyParams`
  (https://www.pvsyst.com/help/project-design/users-needs-load/load-profile-ascii-file-definition.html) [H].
- **Custom imports** use a `.MEF` format file built by the import assistant
  (https://www.pvsyst.com/help/meteo-database/custom-meteo-files/Legacy-pages/formats/general-format.html).
  No sample was found; Meridiana does not need it (analysis).
- **Horizon CSV**: one azimuth and height per line, with comment lines; the direction of rotation and the
  azimuth of North are chosen at import
  (https://www.pvsyst.com/help/project-design/shadings/far-shadings-horizon/importing-horizon-profiles.html) [H].
- **Ground data**: CSV of `X Y Z` points in metres, or GeoTIFF
  (https://www.pvsyst.com/help/project-design/shadings/near-shadings-import/ground-image-and-topography/csv-ground-data.html) [H].

### 3.8 Near-shading scene: `.SHD` and the scene inside the variant [H]
- **Where it is stored.**
  - The scene used by the simulation is stored inside the variant and needs no other file. A `.SHD` is
    an optional copy, which "may also include the Shading Factor Table"
    (https://www.pvsyst.com/help/project-design/shadings/near-shadings-main-dialog/index.html ;
    workspace page).
  - An autosave `__auto__<variant>` is written to `Shadings\` every 5 minutes
    (https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/near-shadings-auto-save.html).
  - `.BLD` (building templates) and `.SHO` (groups of objects) exist (workspace page); no sample.
- **Format.** The `.SHD` (S3, 7.4.2) has the same `pvShading` object as the variant (S1, S7, S9). The
  6.81 release notes mention "reading of .SHD file in binary format (written with v6.3.9 or earlier)".
- **Scene keys:**
  - `FracOmbreMod` is the "Fraction for electrical effect": 0.7 prints as "Electrical effect 70 %", S1;
  - `FracOmbreThin`, `Precision`, `OrientTolerance`, `IsBacktracking`, `Pitch`, `LargCapt`, `GCROffset`,
    `DisplayedRef` (`refGeographical`);
  - `ReportView=TShdReportView`, the camera of the report's picture (S9).
- **Objects** (`ListeObjets, list of=n TShdObject`):

  | Object type | What it is | Specific keys |
  |---|---|---|
  | `pvShdArrayRect` | rectangular PV field | `LongA`, `LargA` (length and slant height), `XOrig`, `YOrig` |
  | `pvShdArrayTable` | PV table | `LongShed`, `LargShed`, `Cadre` (4 frame widths), `TypeOrigine` |
  | `pvShdArrayShed` | field of sheds | `NElemChamps` (number of rows), `PitchNS`, `PitchEW`, `LongShed`, `LargShed`, `DXModule` |
  | `pvShdArrayTracking` | array of trackers | as sheds, plus `AxisOrig` and a nested `pvCollPlane` with the tracking limits |
  | `pvShdBuilding` | building made of elementary objects | `ListeObjetsElem, list of=n TShdObject` |
  | `pvShdElemObject` | elementary object | `ObjetElemType`, `Params` (a list of dimensions) |

- **Keys common to all objects**: `DOrigine=x,y,z` (m), `DInclin` (tilt), `DAzimut`, `BaseSlope`,
  `NoObjCreated`, `Comment`, colours, `Source=osPVsyst`.
- **PV objects** add:
  - `PanneauPVName=<model>;<width>;<height>`, `ModSpacingX`, `ModSpacingY`;
  - `NModInHeight`, `NModInWidth`, `ModuleOrient` (`moPortrait`, `moLandScape`);
  - `NoOrient`: the orientation index in 8.x, -1 in 7.x.
- **Sizes check exactly** [H]:
  - S7: 4 × 1.133 + 3 × 0.02 = 4.592 = `LongShed`; 2 × 2.272 + 0.02 = 4.564 = `LargShed`;
  - S3: 11 × 1.037 + 10 × 0.02 = 11.607 = `LongA`; 3 × 1.762 + 2 × 0.02 = 5.326 = `LargA`.
- **Geometry convention** (https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/global-referential-orientations.html,
  object-positioning.html) [H]:
  - in the northern hemisphere, X points West, Y South and Z to the zenith, with azimuths from South,
    positive towards West;
  - in the southern hemisphere, X points East and Y North, with azimuths from North, positive towards
    West;
  - an object is translated, then rotated by its azimuth, then tilted about its rotated X axis.

  That `DOrigine`, `DAzimut` and `DInclin` are these three steps is consistent with the samples: S9's
  tables have `DAzimut=10.0` on an orientation of azimuth 10° [M]. Trial cases D and O confirm it.
- **Elementary objects.** Types seen: `oeHouse`, `oeAsymHouse`, `oeFour_sided_Roof`,
  `oeOne_Sided_Roof_Gables`, `oeParallelepipede`, `oePrism_Chimney`, `oeTree` [H].
  - `Params` holds 3 to 6 numbers whose order depends on the type. Example: a parallelepiped
    `Params=2.000,10.060,1.970` is probably width, length and height [L]; a tree
    `Params=3.000,8.000,8.000,0.000,5.000,7.000` is not readable without the dialog.
  - The help lists more shapes: triangles, rectangles, trapezium, regular polygon, circle sectors; square
    pyramid, triangular, hexagonal and octagonal prisms, portion of cylinder; roof-like dihedral, 2-sided
    roof with gables
    (https://www.pvsyst.com/help/project-design/shadings/near-shadings-3d-construction/object-types/elementary-objects.html).
  - Trial case D decodes them.
- **Shading factor tables** (`pvShdFTable`):
  - `FOCalcul` is `foLinear` (irradiance) or `foModules` (according to strings), with `InclP`/`AzimP` and
    a `TInterpole2D` grid of 19 azimuths × 10 heights;
  - cells behind the plane hold 1.0001 in S1 [M];
  - tracker variants also carry a nested `pvShading` named "Central active tracker", with tables for
    tracker positions (`PhiP`) [M].
  - The help explains the table
    (https://www.pvsyst.com/help/project-design/shadings/calculation-and-model/shading-factor-table.html).
- **A third-party writer.** The JavaScript tool natalieepearson/PVSyst-Converter writes `.SHD` files
  (`Version=6.83`, `pvShdArrayTracking` items with a nested `PVObject_PlanSuiv=pvCollPlane`) from
  HelioScope DXF drawings (https://github.com/natalieepearson/PVSyst-Converter/blob/master/src/converter.js,
  MIT) [unverified: no proof that PVsyst accepts them].

### 3.9 Horizon (`.HOR`, and inside the variant)
- **What the help says.**
  - A horizon is a line of azimuth and height points; heights all below 2° are ignored.
  - It is saved in `Shadings\` as `.HOR`, and "a file with PVsyst format is not an ASCII file and cannot
    be exported to other software"
    (https://www.pvsyst.com/help/project-design/shadings/far-shadings-horizon/index.html) [H for the
    statement].
  - Imports come from the workspace, a text or CSV file, Meteonorm, PVGIS, or SolarAnywhere (with an API
    key) (importing-horizon-profiles.html) [H].
- **What the samples show.** None of the 22 variants has a horizon block, and all 11 reports say "Free
  Horizon"; no `.HOR` exists in any public repository searched [H].
- **What U1 describes** [unverified]:
  - a `PVObject_Horizon=pvHorizon` block directly in `pvVCalcul`;
  - `HorizonLine=TCubicProfile` (up to 100 `Point_k=azimuth,height` points);
  - `FracAlbedo`, and the diffuse factors `FHHDiffus`, `FHPDiffus`, `FHPAlbedo`.
- **To be settled** by trial case C: whether `.HOR` is binary or PVObject text, and the azimuth
  convention of its points.

### 3.10 Module layout (detailed electrical shading)
- Stored in the variant: the 8.0.8 release note says "the module layout is no longer invalidated after
  running the simulation" [H].
- The partition of fields in strings and rectangles is part of the 3D field dialog since 7.2 (release
  notes 7.2.0) [H].
- No sample; trial case D.

### 3.11 Components and other files
- **PAN, OND.** Already read by `src/meridiana/catalog/panond.py`; the grammar is the one of section 2.
  - Roots `pvModule` and `pvGInverter`, with `pvCommercial` (manufacturer, model, size, price date,
    `Remarks, Count=n`).
  - Curves: `IAMProfile` and `ProfilPIO` (`TCubicProfile`), `OperPoints, list of=n tOperPoint`
    (S13, S14) [H].
  - Versions in the corpus: 6.53 to 7.4.7 [H].
  - The keys depend on the technology more than on the version: CdTe lacks `SubModuleLayout` and
    `muGamma` (S14) [M].
- **BTR, battery** (S12, 7.4.6) [H]:
  - root `PVObject_=pvBattery`;
  - keys `BattTechnol=Li_LFP`, `Category=Rack`, `NCellSerie`, `NCellParall`, `NBlockSerie`,
    `NBlockParall`, `CapNomC10` (Ah), `VNomCell` (V), `PeukertCoeff`, `ResInterne`, `EfficI`, `SOCLD`,
    `SOCLG`, `VMax_Charge`, `VMinDischarge`, `IMaxCharge`, `IMaxDischarge`, `TempMinCharge`,
    `IAutoDech`, `DureeVie20`;
  - three curves: capacity against temperature, self-discharge against temperature, cycles against depth
    of discharge.
  - Check: 16 cells × 12 blocks × 3.2 V × 100 Ah = 61.44 kWh, the energy in the model's name [M].
- **Optimizers.** The variant names them without an extension (`Optimizer=SolarEdge_S500_Worldwide`,
  S9) [H]. The PVsyst extension of PVCollada 2.0 calls optimizer files `.DCC` (S20 schema)
  [unverified].
- **Pumps, controllers, gensets, sellers** (`.PMP`, `.RLT`, `.RLP`, `.GEN`, `.REV`): named by the
  workspace page; a pumping variant references `PumpFile=Grundfos_SP1A_9_90.PMP` (S5); no sample of the
  files.
- **Price list `.PRI`**: imported and exported from the price list dialog
  (https://www.pvsyst.com/help/component-database/price-list/price-list-main-dialog.html). No sample.
- **`Components.xls`** in `UserData\`: a tabular export of sites, modules and inverters (workspace page).
- **`.LOD`, load** (S4) [H]: `PVObject_=pvLoad` with `Comment`, `UsesModul`, `Energy Units`.

### 3.12 Hourly results CSV (`UserHourly\`)
- **Settings.** The output is defined in the variant (`pvSimulFile`) or in a reusable `.SFI`
  (https://www.pvsyst.com/help/project-design/simulation/create-a-csv-file-of-hourly-daily-values.html) [H]:
  - file name;
  - variables (`VarIdentWr=viGlobHor,viDiffHor,...`);
  - units (`Units=uiW,uiW_m2,...`);
  - `TypeValW` (`Hour`, `Day`, `Month`);
  - `Separator=$002C` (the code of `,`), `DecimalSep=$002E` (`.`), `DatesFmt` (2 gave MM/DD/YY in S1).
- **Layout** [H]:

  ```
  PVSYST 7.3.4
  ,File,File date,Description
  Project,Test Bifi Sheds_Project.PRJ,12/28/23 15h52,Test Bifi Sheds,
  Geographical Site,Sacramento/McClellan Park,...
  Meteo data,Sacramento_McClellan Park_MN81_SYN.MET,...        ("Weather data" in the 8.0.17+ samples)
  Simulation variant,Test Bifi Sheds_Project.VC0,12/28/23 18h19,FT30 Az0 (mono),
  Simulation date,,12/28/23 18h33

  Simulation:,Hourly values, from 01/01/90, to 12/31/90
  
  date,GlobHor,DiffHor,BeamHor,T_Amb,...
      ,W/m²,W/m²,W/m²,°C,...
  
  01/01/90 00:00,0,0,0,7.9303,...
  ```

- **Variations** [H]:
  - Encoding: cp1252 up to 8.0.19, so `²` and `°` are single bytes (S1, S16, S19); UTF-8 with BOM in the
    PVsystCLI 8.1.7 output (S18).
  - Separator: `,` (S1, S19) or `;` (S16, S18). Decimal: `.` (S1, S16, S19) or `,` (S18).
  - Dates: MM/DD/YY (S1) or DD/MM/YY (S16, S18, S19). The year is 90 for generic years, or the real year
    (S19: 2023).
  - Labels follow the program's language. Italian (S16): `Progetto`, `Luogo geografico`, `Dati meteo`,
    `Variante di simulazione`, `Valori orari; dal ...; al ...`, with the first column `data`.
  - Units are the ones the user chose: W, kW, ratio.
- **A reader** (analysis) finds the header row (first field `date`, `data`...), takes the next row as
  units, and detects the separator, the decimal mark and the date order from the data. It should not count
  fixed rows: a copy edited in Excel added a line (S16).

### 3.13 Output templates, batch mode and PVsystCLI
- **SFI.** A `PVObject_=pvSimulFile` object, closed by `End of TSimulFich` (S1) [H]. The help calls the
  format "proprietary" and says it "should not be generated outside PVsyst"
  (https://www.pvsyst.com/help/glossary/pv-system/sfi-file-format.html).
- **RVT.** A plain text file with one line, `ResultVars=Var1;Var2;...`
  (https://www.pvsyst.com/help/glossary/pv-system/rvt-file-format.html) [H, documentation only].
- **Batch mode**
  (https://www.pvsyst.com/help/project-design/simulation/batch-mode-parametric-studies.html) [H].
  `<Project>_BatchParams_i.CSV` (S15, comma-separated, ASCII) holds:
  - the title lines `PVsyst simulations Batch mode`, `Simulation parameters definition` and
    `File created on ...`;
  - `Project,,,<file>.PRJ` and `Variants based on,,VC3,<comment>`;
  - three instruction lines, one saying that only the lines beginning with `SIM_` will be executed;
  - three header rows: group, sub-title and unit (`Ident, Save VCi, Create hourly file, Thermal Uc fact,
    ..., Simul Comment`, with units `Y/N`, `[W/m2K]`);
  - one `SIM_n` row per run.

  `<Project>_BatchResults_i.CSV` repeats the parameters, adds an `Error` column and the chosen yearly
  variables with a units row, in cp1252.
  - The varied parameters are limited to one fixed orientation, sheds or tracker geometry, module and
    inverter types and counts, quality loss, thermal factors, weather files and sites.
  - PVsystCLI's example names are `BatchsParams_0.csv` and `BatchsResults_0.csv`, a naming difference
    with the GUI help.
- **PVsystCLI** (8.0 and later, paid; https://www.pvsyst.com/help-cli/reference/index.html) [H]:
  - Commands: `run-simulation`, `convert-meteo`, `create-site`, `export-logs`, `version`, `lic-*`.
  - `run-simulation` options:
    - workspace `-w`, project `-p`, variant `-v`;
    - `-ts hour|subhour`; `-s` SIT with `-swg`; `-imf` MET;
    - `-irf` RVT, `-isf` SFI, `-ipf` advanced parameters;
    - `-bpf` batch CSV, `-brf` batch RVT;
    - `-ocf` output CSV, `-rpf` PDF, `-rp` report pages, `-rl` language (12, `it` included);
    - `-sd`/`-ed` dates.
  - `convert-meteo` turns a CSV with a MEF and a SIT into a MET.
  - The documentation describes the format of the site CSV only, not of the batch CSV, RVT, SFI, MEF or
    output CSV.
  - S18 adds that the exit code is always 0 and success is read from the console text [unverified].

### 3.14 PDF report [H]
- **Producer and protection** (all 11 loose reports, S1 to S10, S18):
  - the producer is "Synopse PDF engine" (a Delphi PDF library);
  - the 7.x reports are encrypted with RC4 128-bit, with permissions and an empty user password;
  - the 8.x reports are not encrypted.

  PyMuPDF opens and reads all of them.
- **Sections.** The bookmarks give a stable list of section identifiers with their titles:
  - `Cover page`;
  - `PrjSummary` (Project and results summary);
  - `VCSimParams` (General parameters, PV Array Characteristics, System losses);
  - `VCACWiringLosses`;
  - `VCShadings` (Near shading definition, iso-shadings diagram);
  - `VCMainRes` (Main results);
  - `VCLossDiagram`;
  - `VCPredefPlot`;
  - `VCAgingResult`;
  - `VCP50P90`;
  - `VCCircuitDiagram`;
  - `VCEconomicEval`;
  - `VCFinancialBalance`;
  - `VCCarbonBalance`.

  The same pages are selected by PVsystCLI's `--report-pages` (`cover`, `summary`, `notes`, `params`,
  `horizon`, `shadings`, `usersneeds`, `results`, `econeval`, `circuit`, `losses`, `financialbalance`,
  `p50p90`, `carbonbalance`, `predefgraphs`) and by the PRJ's `PrintedSections` [H].
- **Text.** The text is extractable:
  - project, variant, site, coordinates;
  - module, inverter, strings, losses;
  - the monthly table "Balances and main results" (GlobHor, DiffHor, T_Amb, GlobInc, GlobEff, EArray,
    E_Grid, PR);
  - the yearly production, the specific yield and the PR.
- **More reports.** Study 11 keeps 27 public reports (PVsyst 6 to 8.0.20) in
  `C:\Users\utente\dev\meridiana-prove\pvsyst-report-pubblici\` and reads their text by position, in
  English, Italian and German (`11-pvsyst-casi-di-confronto.md`, section 1).
- **Trial watermark.** Trial reports carry "PVsyst TRIAL" (or "PVsystCLI TRIAL") and show the module and
  inverter manufacturers as "Generic", even when the variant references a real database model (S5, S6;
  the reports of S3 and S8 look the same) [H].

### 3.15 Formats PVsyst imports from other tools
- **PVCollada 2.0** (`.pvc2`, zipped `.pvz2`), imported since 8.1.5 and never exported
  (https://www.pvsyst.com/help/project-design/shadings/near-shadings-import/pv-collada-file-format.html) [H]:
  - Specification and samples: https://github.com/pvlib/pvcollada (S20), linked from https://pvcollada.org/.
  - A valid COLLADA 1.5 document, with the PV data in `<extra><technique profile="PVCollada-2.0">`:
    - `geographic_location` (latitude, longitude, altitude);
    - components (`module` with power, size and electrical data; `inverter`);
    - a circuit tree (transformer, combiner, inverter, MPPT, string, `module_layout` with row, column and
      position in string);
    - racks (`rack_type` fixed_tilt or tracker, `module_rows`, `module_columns`, `module_orientation`,
      `tilt`, `azimuth`, tracker limits);
    - a terrain mesh.
  - Conventions: a local East-North-Up frame; azimuth clockwise from North (180 = South); module sizes in
    mm.
  - A PVsyst extension (`technique profile="PVCollada-2.0-PVsyst"`) embeds `pan_file_content` and
    `ond_file_content` as CDATA, and names optimizers by `dcc_file_name`.
  - PVsyst converts azimuths to its own convention and ignores the circuit for now (help).
  - Confidence: [H] for the specification; [M] for the samples, which were read with my own XML outline.
- **PVCollada 1.4.1** (`.pvc`, 7.0 and later, made with PVcase) [H]:
  - not valid COLLADA;
  - `<mesh>` carries either `<frame_parameters>` (module width, height, spacings, manufacturer, name) or
    `<tracker_parameters>` (the same, plus `tracker_type`, `axis_vertices`, `min_phi`, `max_phi`,
    `min_theta`, `max_theta`) (help).
  - The two samples (S20) use the `<unit>` of the file, inches in one of them, not the millimetres the
    help states [M].
  - PVcase's own help (https://help.pvcase.com/) refused automated access (HTTP 403) and was not read.
- **Helios 3D** (`.h2p`): a text file between `START` and `END`, according to Helios's help
  (https://helpcenter.helios3d.com/en/output-ribbon/) [M]. It holds:
  - `TABLE` blocks: size, overhangs, module columns and rows, spacings, module name;
  - `INSERT` blocks: x, y, z, azimuth, slope, module inclination;
  - `DGM` terrain triangles.

  PVsyst has read Helios 3D files since at least 5.41 (2011), trackers since 7.0.0 and negative tilts
  since 7.2.5 (release notes). No public sample.
- **DAE and 3DS** (SketchUp, AutoCAD through SketchUp or the FBX converter). PV faces are chosen by
  material at import, with three orientation rules (best azimuth, longest edge, east/west)
  (https://www.pvsyst.com/help/project-design/shadings/near-shadings-import/sketchup-and-other-cad-software.html) [H].
- **Ground**: CSV points, GeoTIFF, or a downloaded image and topography in 8.0 and later (help pages
  of 3.7).

---

## 4. Differences between versions 6, 7 and 8

No 6.x project or variant was found in public, so the 6.x column rests on the help and the release notes.
The 7.x and 8.x columns rest on the samples (7.3.4 to 8.1.2) as well.

| Item | 6.x | 7.x | 8.0 | 8.1 | Conf. and source |
|---|---|---|---|---|---|
| Storage | binary up to 6.39; text from 6.40 | text | text | text | [H] format page |
| Encoding | ANSI text 6.40 to 6.79; UTF-8 from 6.80 | UTF-8 with BOM; PAN/OND can be saved "in old format" (ANSI) since 7.0.10 | UTF-8 with BOM | UTF-8 with BOM | [H] format page, release notes, samples |
| Workspace | `PVsyst6_Data`, `PVsyst640_Data`, `PVsyst660_Data`, `PVsyst680_Data` | `PVsyst7.0_Data` (S7) | not seen; the help still names `PVsyst8.0_Data` | `PVsyst8.1_Data` | [H] for 6.x and 8.1; [M] for 7.x and 8.0 |
| Variants | unlimited since 6.40 (VCi, VDi...); format improved in 6.60 | same | same | same | [H] release notes 6.40, format page |
| Orientation in the variant | as 7.x (presumably) [L] | `pvEnIncid` > `pvCollPlane` (`InclPlR`, `AzimPlR`, tracker limits) | `Orientations, list of=n TOrientGroup` > `pvOrient` (`FieldTilt`, `FieldAzim`, `BaseSlope`, ...); "orientations at the heart" of the project | as 8.0 | [H] samples 7.3.4 to 7.4.7 against 8.0.5 to 8.0.21; release notes 8.0.0 |
| Shading factor tables | | in `pvShading` (`TableOmbrLin#k`, `TableOmbrMod#k`) | one `ShdTableLin` per orientation, inside `pvOrient` | as 8.0 | [M] samples |
| Bifacial | sheds model since 6.60 | `pvBiFacial` in `pvMainArray` | `pvBiFacial` in `pvOrient` | as 8.0 | [M] samples (S1, S9) |
| 3D PV fields | | defined by the number of modules since 7.2 (`PanneauPVName`, `NModInHeight`, `NModInWidth`) | same | same | [M] release notes 7.2.0, samples |
| Circuit (`pvCircuit`) | | present (7.3.4 to 7.4.7 samples); MV/HV transformers since 7.0 | same, with `Empty NodeNode` | same | [M] samples, release notes 7.0.0 |
| Soiling | | one yearly `SoilingLoss` | one yearly `SoilingLoss` | `Soiling` block: yearly, monthly or from file | [H] samples for 7.x and 8.0; [unverified] U1 for 8.1 |
| Albedo | monthly in the PRJ | same | same | plus a CSV time series (8.1.2) | [H] samples, release notes 8.1.2 |
| Weather | hourly | hourly | hourly | sub-hourly (8.1.0); Meteonorm 9 (`MN90`, `Meteonorm90DLL`) | [H] release notes 8.1.0; S11 |
| `.SHD` | binary up to 6.39, readable again since 6.81 | text | text | text | [H] release notes 6.81; S3 |
| PRJ print settings | | `PrintCoverPage`, `ClientDesignation`, ... | same | adds `CoverPagePJNameText`, `PrintedSections` | [M] S1, S11 |
| Hourly CSV | | cp1252, "Meteo data" | cp1252, "Weather data" (8.0.17+) | UTF-8 with BOM (CLI 8.1.7) | [M] S1, S16, S18, S19 |
| PDF report | | RC4 encrypted, empty user password | not encrypted | not encrypted | [H] 11 samples |
| 3D imports | Helios 3D since 5.x (5.41, 2011); DAE since 6.60 | PVC (PVCollada 1.4.1) since 7.0; Helios trackers 7.0 | ground image and topography download | PVC2 since 8.1.5 | [H] help and release notes |
| Batch and automation | batch mode; started "from a script" (6.40) | batch, PDF per run | PVsystCLI (8.0.0), batch via CLI (8.0.12) | `create-site` (8.1.0) | [H] release notes, CLI help |

Consequences for a reader (analysis):
1. Branch on the presence of `Orientations` or `pvEnIncid`, not on the version number.
2. Accept `pvBiFacial` and the shading tables in either place.
3. Refuse files of 6.39 or earlier: they are binary. Say how to convert them: open and save in a newer
   PVsyst.
4. Accept unknown keys and blocks of newer versions, and list them in the import summary.

---

## 5. Mapping: PVsyst keys to Meridiana concepts

Meridiana's side, as of 22/10/2026:
- `model.Project` holds the shared site, buildings, exclusions, consumption and rules, plus `variants`;
  each variant has its own `subfields`, `modules`, `energy` and `economics` (the `DESIGN` fields).
- `layout.Params` describes a sub-field's mounting.
- `energy.simulate.Losses` holds the loss settings.
- `energy` also holds `inverter`, `inverter_count`, `t_min`, `strings` (`n_series`, `per_mppt`) and
  `thermal`.
- `economics.Settings` holds `battery`, `battery_units`, `export_limit_kw` and `degradation`.
- `energy.meteo.Meteo` and `Horizon` hold the weather and the horizon.

A PVsyst project maps naturally onto a Meridiana project, and each chosen `.VCi` onto a Meridiana
variant (analysis).

Status: **direct** (same meaning, unit converted), **approx.** (an approximation that the import must
state), **no** (Meridiana has no such concept: listed as not imported).

| PVsyst (file, object, key) | Meridiana | Conversion | Status |
|---|---|---|---|
| PRJ `pvProject.Comment` | `Project.name` | text | direct |
| `pvSite.Latitude`, `Longitude` | `Project.site.lat`, `lon` | same signs (east and north positive) | direct |
| `pvSite.Site`, `Country` | `Project.site.address` | text | approx. |
| `pvSite.Altitude` | `Meteo.elevation` (only when the weather is imported) | m | approx. |
| `pvSite.TimeZone`, `HLeg` | none: Meridiana computes in Europe/Rome time (`simulate.TIMEZONE`) | | no; outside Italy, warn |
| `pvSite` monthly `GlobalH`, `DiffuseH`, `TAmb`, `WindVel`, `Linke`, `RelHum` | none | | no; shown next to PVGIS as a cross-check |
| PRJ `Albedo` (12 months) | `Losses.albedo` (one value) | mean of the 12, said | approx. |
| PRJ `DesignTempMin` | `energy["t_min"]` | °C | direct |
| PRJ `TempOper*`, `LimOverloadLoss`, `SpreadMaxDiff`... | none | | no |
| PRJ or VCi `TranspositionAlgorithm` (`CircSolSeparate`; Hay in old projects) | `Losses.transposition` (`perez`, `haydavies`) | | direct |
| MET hourly `GlobHor`, `DiffHor`, `T_Amb`, `WindVel`, `RelHum` | `Meteo.data` (`ghi`, `dhi`, `temp_air`, `wind_speed`, `relative_humidity`); `dni` computed; `pressure` from the altitude | decode (2.4); MJ/m² per hour × 1000/3.6 = W/m²; stored in standard time of `TimeZone`, label at the start of the hour, sun at mid-hour: index in UTC, `time_offset_h` = 0.5 plus `TimeShift` (analysis) | direct, except Meteonorm data (9.1): offer PVGIS instead |
| VCi 7.x `pvCollPlane FieldType=FixedPlane`, `InclPlR`, `AzimPlR` (default 0); 8.x `pvOrient FieldTilt`, `FieldAzim` | `layout.Params.tilt`, `azimuth`; the array's tilt and azimuth | same convention in the northern hemisphere; in the southern one, azimuth = 180 - PVsyst azimuth, wrapped to ±180 (analysis from the help's convention) | direct |
| Sheds (8.x `FieldType=Sheds`: `Pitch`, `CollectorWidth`, `NSheds`; 3D `pvShdArrayShed`: `PitchNS`, `LargShed`, `NElemChamps`, `NModInHeight`, `ModuleOrient`) | `layout.Params`: `mounting` (`ground`, `tilted_anchored` or `tilted_ballasted`), `pitch_mode="value"`, `pitch`, `stack`, `portrait` | m; `moPortrait` sets `portrait=True` | direct; the module count re-laid by Meridiana may differ and is compared |
| `InactiveBandWidth1/2`, `Cadre`, `ModSpacingX/Y` | `gap`, `stack_gap` | m | approx. |
| `BaseSlope` (tables on a slope) | none (flat ground) | | no |
| Trackers (`TrackHorizNSAxis`, `TrackHorizAxis`, others) with their limits and backtracking | none | | no: imported as data and listed |
| `SeasonalTilt`, `SunShields` | none | | no |
| `Dome` (east-west) | `mounting="east_west"` | | approx. |
| 3D PV objects (`pvShdArrayTable`, `pvShdArrayRect`, `pvShdArrayShed`): `DOrigine`, `DAzimut`, `DInclin`, `LongShed`/`LongA`, `LargShed`/`LargA` | a `SubField` ring: the plan projection of each field, on a building pitch when it lies on one, with `filled=True` | scene frame (northern hemisphere): Meridiana x = -X, y = -Y (X West, Y South); the slant width × cos(tilt) gives the plan depth | approx.: Meridiana re-lays the modules |
| `pvShdBuilding` with `oeHouse`, `oeAsymHouse`, `oeFour_sided_Roof`, `oeOne_Sided_Roof_Gables`, `oeParallelepipede` | `Building` (footprint, eave height, `Roof` `gable`, `hip`, `mono`, `flat`, tilt) | needs the `Params` order of each type (trial case D) | approx. after the trial; before it, prisms |
| `oeTree`, `oePrism_Chimney`, other shapes | `ExclusionItem` (`kind="tree"`, `"chimney"`, `"other"`) with `height` | `Params` order (trial) | approx. |
| Ground objects, terrain | none | | no |
| `pvShdFTable` shading factor tables | none (Meridiana computes its own table, `nearshade`) | | no; kept for comparison |
| `FracOmbreMod` (fraction for electrical effect) | none: Meridiana computes the electrical effect by strings | | no; listed |
| `pvSubArray.PVModule` (`.PAN` name) | `Project.modules[...]` through `panond.module()`, `SubField.module` | file found next to the project, in a PVsyst workspace the designer points to, or in the catalogue by model name; `PanneauPVName` gives the size | direct when the file is found |
| `pvSubArray.GInverter` (`.OND` name), `NInverter` | `energy["inverter"]` through `panond.inverter()`, `energy["inverter_count"]` | as above | direct when the file is found |
| `NModSerie`, circuit `MPPTNode` and `StringNode` `NElements` | `energy["strings"] = {"n_series", "per_mppt"}` | strings on each input of one inverter | direct [M] |
| `NInvMPPT`, `PNomAC_InMPPT`, `PowerSharingInverterId` (MPPT shared between sub-arrays) | none: whole inverters only | | no |
| `Optimizer` and its counts | none | | no |
| `pvBiFacial` (bifaciality, ground albedo, height) | `ModuleSpec.bifaciality` exists, with no bifacial gain model | | no; listed |
| `UFactor`, `UVFactor` | the thermal case of the sub-field (`energy["thermal"]`: open 29/0, semi 20/0, integrated 15/0) | nearest case, said; or a new `uc`, `uv` pair in `Losses` (analysis) | approx. |
| `Alpha` | fixed 0.9 in `simulate` | | direct when 0.9 |
| `SoilingLoss` | `Losses.soiling` | fraction × 100 = % | direct |
| 8.1 monthly soiling [unverified] | `Losses.soiling` | mean of the 12, said | approx. |
| `LIDLoss` | `Losses.lid` | % | direct |
| `PQualityModP` | `Losses.quality` | %, negative for a gain in both | direct |
| `PMismMPP` | `Losses.mismatch` | % | direct |
| `PMismString` | none | could be added to the mismatch, said | approx. |
| `RSCablagePC` | `Losses.dc_wiring` | % at STC in both | direct |
| `RSCablageCh` | none | mΩ, shown for information | no |
| AC wiring (`ACWireNoSect`, `ACWireLength`, `ACWireMetal`) | `Losses.ac_wiring` (% at nominal power) | needs the report's loss fraction or a calculation | approx. |
| MV transformers (`MVNbTransfos`, `TrfIronLossFrac`, `TrfResLossFrac`) | none | | no |
| IAM `Default` with `B0_IAM` | `Losses.iam_b0` | | direct |
| IAM `FresnelSmooth`, `FresnelAR`, `UserProfile` (9 points of `TCubicProfile`) | `ModuleSpec.iam_profile` (`theta`, `iam`) | the 9 points; Meridiana joins them as PVsyst does (`simulate.profile_iam`) | direct; PVsyst sets IAM per sub-array, Meridiana per module: the first one is kept and the rest said |
| `UnavTotDuration` (days) and periods | `Losses.unavailability` (%) | days / 365 × 100 | approx. |
| `AuxPower_*` | none | | no |
| `PLimGrid` (kW) | `economics.export_limit_kw` | kW | direct [M] |
| `TanPhi` | none | | no |
| Ageing (`pvAgeing.ModuleDegradFactor`, %/year) | `economics.degradation` | %/year | direct [M] |
| `UseSpectralCorr` | none | | no |
| `pvLoad`: `LoadType=Constant` (`ConstantLoad`, kW), `DailyProfile` (`ValHour_1`, 24 values) | `Project.consumption` (`annual_kwh`, or `measured` hourly) | kW × 8760 h; the profile repeated over the year | approx. |
| Storage: `BatteryFile` (`.BTR`), `NBattSerie`, `NBattParall`, `pvGridStorage` [unverified] | `economics.battery` (`usable_energy_kwh`, `max_charge_power_w`, `max_discharge_power_w`, `round_trip_efficiency_pct`), `battery_units` | energy = cells × blocks × V × Ah; usable from the SOC limits | approx. after the trial |
| `TEcoEvaluation` (costs, loans, tariffs), `pvCarbonBalance`, `TP50_P90` | `economics` only in part (`capex_total`, `opex`, `years`) | different method and incentives | no, or approx. on request |
| Results `VarList` (monthly and hourly `GlobHor`, `GlobInc`, `GlobEff`, `EArray`, `E_Grid`, PR) | none: a "PVsyst results" table next to Meridiana's own | decoded (2.4) | comparison only |

---

## 6. Proposed import design for Meridiana (analysis)

### 6.1 Principles
- **Read only.** Never write or modify PVsyst files (help: they "should not be modified").
- **Show first.** Show what was read, and how, before anything is used: as `catalog/panond.py` does with
  its `(record, said)` pair.
- **Refuse rather than guess.** A file that does not parse, or lacks what a design needs, is refused and
  the missing parts are named. A partly understood file is imported with a list of what was left out.
- **Logic without Qt.** Everything is tested in `tests/` with `unittest` (repository rules in
  `CLAUDE.md`). The disk work runs off the window's thread.

### 6.2 Modules
1. **`src/meridiana/pvsyst/pvobject.py`**: the tolerant reader of section 2.5.
   - Returns `Node(type, role, attrs, children, line)`, with `attrs` as an ordered list of `(key, value)`.
   - Joins the `_contd` lines.
   - Records anomalies.
   - Has no knowledge of PV.
   - `catalog/panond.py` can later use it too.
2. **`src/meridiana/pvsyst/records.py`**: decodes the `Day_` records into NumPy arrays (base 62, sign,
   `WRFactor`, unit). It checks 24 values a day for hourly data, and the length against `DateBeg` and
   `DateEnd`.
3. **`src/meridiana/pvsyst/project.py`**: plain dataclasses.
   - `read_project(prj)` returns the site, the settings, the weather file name and the variants found
     next to it, each with its comment, version, `SystemKind`, date, and whether it has results.
   - `read_variant(vci)` returns the orientations, sub-arrays, losses, circuit, system, load, scene and
     results summary, plus the keys and blocks not understood.
   - `read_met(met)` returns the hourly weather with its source.
   - `read_sit(sit)` returns the site.
4. **`src/meridiana/pvsyst/outputs.py`**: hourly CSV, batch CSV, the PVsyst standard weather CSV, and
   optionally the PDF report (bookmarks and the monthly table), for comparisons.
5. **`src/meridiana/pvsyst/mapping.py`**: from the dataclasses to a Meridiana `Project` draft. It returns
   `(draft, said, approximated, not_imported, missing_files)`, as lists of sentences in the program's
   language.

### 6.3 Steps seen by the designer
1. **File > Import from PVsyst...** picks a `.PRJ`. Meridiana lists the variants found
   (`<name>.VC0`...), with their names, versions, system kinds and simulation dates. The designer ticks
   one or more.
2. **Components.** For each `.PAN` and `.OND` named, Meridiana looks in this order:
   - next to the PRJ and in `ComposPV\PVModules` or `ComposPV\Inverters` beside it (an exported folder);
   - in a PVsyst workspace folder the designer points to once (remembered in the settings);
   - in Meridiana's catalogue, by manufacturer and model;
   - otherwise the designer chooses a file, a catalogue entry, or the generic module, said to be generic.
3. **Weather.**
   - If the `.MET` is present and its `SourceType` is not Meteonorm, offer to use its hourly data.
   - Otherwise propose PVGIS for the same coordinates, as Meridiana already does, and show PVsyst's
     monthly values beside PVGIS's.
4. **Scene.**
   - The PVsyst scene is not georeferenced (except PVC2 or ground-image imports). Show it in plan over
     the map at the site origin, and let the designer move and rotate it once before confirming.
   - Fields become sub-fields; buildings and obstacles become buildings and exclusions.
   - In Meridiana, buildings are shared by all variants, while PVsyst stores a scene in each variant. If
     the chosen variants have different scenes, the first one's is kept and the difference is said.
5. **Summary dialog**, before anything is created. Four sections:
   - **Read**: each value with PVsyst's value and unit, and Meridiana's;
   - **Approximated**: for example "monthly albedo 0.20 to 0.40, mean 0.28 used"; "Uc 25, Uv 1.2:
     free-standing case Uc 29 used";
   - **Not imported**: for example "trackers", "bifacial gain", "MV transformers", "economics";
   - **Missing files**.

   Buttons: "Create a new project" (saved as a new file, never over another), and "Add as variants of
   the open project" when the site is the same within 100 m (analysis).
6. **Afterwards.**
   - The pedigree of each value says it came from PVsyst file X, key Y.
   - The report can show "PVsyst results" (monthly E_Grid, GlobInc, PR from the variant) next to
     Meridiana's simulation, with the differences.

### 6.4 Versions and errors
- Root `Version`:
  - 6.40 to 8.1.x are the tested range;
  - newer versions are read with a warning that they are newer than tested;
  - binary files (no `PVObject_` on the first line) are refused with the explanation of 6.39 and earlier.
- Unknown keys and blocks do not stop the import; they are counted and listed under "not understood".
- A variant without results is accepted. The results table is simply not shown.

### 6.5 Effort, order and what waits for the trial
1. **Parser, records and readers**, with tests on the corpus: about one week. It is doable now.
2. **Mapping** for fixed planes, sheds, sub-arrays, losses, weather and results: about one week. Doable
   now.
3. **Scene to sub-fields and buildings.**
   - Fields can be done now.
   - Elementary objects wait for the `Params` decoding (trial case D).
4. **Horizon, storage, module layout and monthly soiling** wait for the trial files.
5. **Later**: PVCollada 2.0 import as a separate, open route for layouts (no trial needed), and
   PVCollada 2.0 export from Meridiana, which PVsyst 8.1.5+ imports. This would be the clean way to send
   a Meridiana layout to PVsyst, instead of writing PVsyst's internal files.

---

## 7. Test plan with the samples (analysis)

The samples cannot enter the repository (most have no licence: see their README). The tests therefore
work in two layers:
1. **Repository fixtures** in `tests/data/pvsyst/`: small files written by hand from the grammar of
   section 2. They are not copies of the samples. They cover the markers, the irregular closers, the
   `_contd` lines, the default omissions, an empty typed record, a 2-day `Day_` record with known values,
   a cp1252 file, a binary file to refuse, and a "newer version".
2. **Corpus tests**, skipped when the folder is missing. They read
   `MERIDIANA_PVSYST_SAMPLES` or default to `C:\Users\utente\dev\meridiana-prove\pvsyst-campioni`, and
   run every real file.

The expected values come from the files and from PVsyst's own reports and CSVs. They were all checked
during this study.

| # | Test | Sample | Expected |
|---|---|---|---|
| 1 | every PVObject file parses to one root, every opener is closed, no unknown closer | all 68 real files (S1 to S14, S21) | pass; empty `Str_i` remarks tolerated |
| 2 | encodings: BOM with CRLF; ASCII 6.70 PAN; cp1252 fallback | S1, S13, a fixture | same keys read |
| 3 | PRJ site and settings | S1 sheds PRJ | lat 38.67, lon -121.40, altitude 18, time zone -8, albedo 12 × 0.20, `DesignTempMin` -10, MET file name |
| 4 | PRJ 8.1 additions | S11 | `PrintedSections` list; monthly albedo 0.40 |
| 5 | MET decoding against its own monthly values | S1 MET | GlobHor 61.4, 83.2, 133.6, 176.1, 231.1, 234.9, 241.8, 217.5, 172.8, 119.1, 76.5, 51.3 kWh/m² (±0.05); T_Amb means 7.00, 9.10, 12.60, 15.30 °C (±0.01); 8,760 values |
| 6 | the same on an imported TMY | S3 MET (NREL) | monthly sums equal its pvSite |
| 7 | VCi hourly records against PVsyst's CSV of the same run | S1 sheds VC0 and SAT VC0 with their CSVs | max difference: GlobHor 0.011 W/m², GlobInc 0.11 W/m², T_Amb 0.0005 °C, TArray 0.006 °C, E_Grid 25 W on 2.2 MW, HSol 0.05° |
| 8 | VCi monthly results against the report | S1 sheds VC0 | E_Grid 196,038 kWh in January, 4,436,353 kWh a year; GlobInc 90.6 kWh/m² in January |
| 9 | 7.x orientation and sheds | S1 sheds VC0 | fixed plane, tilt 30, azimuth 0 (absent key); 49 sheds, pitch 5.00 m, width 2.465 m, 90 modules a row, portrait, 1 high |
| 10 | trackers read and declared unsupported | S1 SAT VC0 | `TrackHorizNSAxis`, phi ±60°, pitch 5.00 m, 49 trackers, backtracking; the mapping lists "trackers: not imported" |
| 11 | 8.x orientation list, optimizers, building | S9 Cameron Heights VC0 | 3 orientations, 3 sub-arrays, SolarEdge optimizer by name, 9 tables, 1 building of 14 elementary objects |
| 12 | 8.x bifacial inside the orientation | S9 Casselman VC0 | sheds, bifaciality 0.80, ground albedo 0.30, height 1.50 m; mapping lists "bifacial gain: not imported" |
| 13 | sub-array losses against the report | S7 VC0 | Uc 29, Uv 0 (absent key), soiling 3.0 % (0.030), LID 1.5 %, quality 0.5 %, mismatch 2.0 %, string mismatch 0.05 %, wiring 1.5 % at STC and 176 mΩ, IAM FresnelAR (0.99892 at 30°) |
| 14 | circuit to strings per MPPT | S7 and S10 VC0 | S7: 1 inverter, inputs [2, 2]; S10: 2 inverters, inputs [1, 1, 1, 1, 1, 1] |
| 15 | system keys | S2 VC1 | grid limit 60,000 kW, tan φ 0.329, unavailability 7.30 days in 3 periods, MV transformers 18 |
| 16 | scene from a `.SHD` | S3 SHD | 1 rectangular field (3 × 11 SLG 370HC, 1.037 × 1.762 m, 11.607 × 5.326 m), 1 building of 8 elementary objects, 2 trees; plan positions after x = -X, y = -Y |
| 17 | sizes of PV objects | S7 tables, S1 sheds | `LongShed` = n × width + (n - 1) × spacing, and the same for `LargShed`, within 1 mm |
| 18 | battery | S12 BTR | Li-LFP, 16 cells × 12 blocks, 100 Ah, 3.2 V: 61.44 kWh |
| 19 | LOD and SFI | S4 LOD, S1 SFI | keys read; the SFI's variables list joined across `_contd` lines |
| 20 | hourly CSV in four dialects | S1 (`,`, `.`, MM/DD), S19 (`,`, `.`, DD/MM, real year), S16 (Italian, `;`), S18 (UTF-8 BOM, `;`, `,`) | same column names and float values; units row read |
| 21 | batch files | S15 | the parameter header (3 rows), the `SIM_n` rows, 123 result columns with units |
| 22 | PVsyst standard weather CSV | S17 | header tags read; 8,760 rows; Hour 1 to 24 with Minute 30 placed as hour 0 to 23 |
| 23 | PDF report | S1, S8, S18 PDFs | bookmarks `PrjSummary`, `VCSimParams`, `VCMainRes`...; yearly E_Grid read from the text equals the variant's |
| 24 | refusals and warnings | fixtures: a binary PAN (S18's synthetic one, or one written by the test); `Version=9.0.0` | binary refused with the 6.39 explanation; newer version read with a warning |
| 25 | the import end to end | S1 sheds PRJ with VC0, PAN and OND from `tests/data` standing in for the missing ones | a Meridiana project with one variant; nothing written beside the PVsyst files; saving and reopening keeps every value |
| 26 | Meteonorm weather is not imported by default | S1 MET (`SourceType=Meteonorm81DB`) | the import proposes PVGIS and says why |
| 27 | PVCollada 2.0, when implemented | S20 samples 01 to 07 and the PVsyst-extension ones | tables, trackers, modules and the embedded PAN/OND read |

When the trial files exist (section 8), the same tests extend to the cases they cover: horizon,
storage, module layout, monthly soiling, sub-hourly weather, the elementary objects' `Params`, and the
southern hemisphere.

---

## 8. What to create with the PVsyst 8 trial (30 days)

### 8.1 Before starting
- **Installation.** Install the latest PVsyst 8.1 from pvsyst.com on the Windows PC. The evaluation runs
  30 days, then PVsyst switches to DEMO mode, which can open files but not save them, so save as you go.
  Whether the download asks for a registration was not checked: this study created no account.
- **Workspace.** The workspace must not sit on OneDrive or another synced drive
  (https://www.pvsyst.com/help/getting-started/requirements.html). Keep the default
  `C:\Users\utente\PVsyst8.1_Data` if it is not synced, or create `C:\PVsyst8.1_Data`.
- **Generic components only** [H]. GCU 2.4 says "Only generic components can be used in projects
  created under this mode"; the help says the evaluation mode has "full features except for the usage
  of components limited to generic ones"
  (https://www.pvsyst.com/help/getting-started/licensing/index.html).
  - Plan every case with generic modules and inverters (`Generic_Mono_300W.PAN`, `Generic_3kW.OND` and
    the like, as in S5).
  - On day 1, try to import `tests\data\pvsyst\ET-M772BH550GL.PAN` and the CPS `.OND`, and note
    whether PVsyst accepts them.
- **Weather.** Use an Italian site with PVGIS weather imported inside PVsyst ("PVGIS TMY" in site
  creation): Milan, 45.4642 N, 9.19 E (Meridiana's default site).
  - Meteonorm data must not be exported to other software (GCU 1.3, section 9.1), and Meridiana would
    import the `.MET`.
  - Use Meteonorm only in case L, where the synthetic generation itself is the object.
- **Distinctive values.** Give every value a distinctive figure (27.3 rather than 29), so that each key
  can be found in the files without doubt.
- **Record sheet.** Note, for every case, the dialog, the field and the value set, in a simple sheet
  `registro-prove.csv` (case; variant; dialog; field; value). Screenshots of the dialogs help.
- **Files to keep from every case:**
  - the PRJ, all VCi, the SIT and the MET;
  - the `.SHD`, `.BLD`, `.SHO` and `.HOR` saved explicitly;
  - the hourly CSV (with the variables of 8.3) and the PDF report with all pages.
- **Saving.** At the end of each week, use File > Workspace > Export to a zip. Copy everything to
  `C:\Users\utente\dev\meridiana-prove\pvsyst-trial\` (outside the repository).

### 8.2 The cases
| Case | Project / variant | What to set (distinctive values) | What it settles | Days |
|---|---|---|---|---|
| A | `M00_base` VC0 | Milan, PVGIS TMY; fixed plane tilt 30, azimuth 0; one generic 300-400 W module, 2 strings × 10; one generic inverter; no shading; every loss left at its default | the defaults that are omitted from the files; the baseline for B | 1 to 2 |
| B1 | `M00_base` VC1 | Uc 27.3, Uv 1.7; yearly soiling 2.7 %; LID 1.3 %; module quality -0.4 %; mismatch 1.7 %; string mismatch 0.13 %; DC wiring 1.9 % at STC; AC wiring 37 m of 16 mm² copper; spectral correction on | the loss keys and their units | 3 |
| B2 | `M00_base` VC2, and a copy of the project `M00_albedo` | in VC2, monthly soiling 1.1, 1.2 ... 2.2 %; in `M00_albedo` (the far albedo is a project setting, shared by all variants), far albedo 0.11, 0.12 ... 0.22 | the 8.1 soiling block; the monthly albedo in the PRJ | 3 |
| B3 | `M00_base` VC3 | unavailability 5.5 days in 3 periods with given dates; auxiliaries 123 W constant, 45 W at night; grid limit 85 % of Pac; power factor cos φ 0.95; ageing 0.45 %/year over 10 years; IAM user profile (0°: 1, 30°: 0.998, 50°: 0.98, 60°: 0.95, 70°: 0.88, 75°: 0.80, 80°: 0.66, 85°: 0.42, 90°: 0); in VC4, IAM ASHRAE b0 0.047 | system keys, ageing, IAM modes | 4 |
| C | `M00_base` VC5 to VC7 | VC5 a horizon of 8 points drawn by hand (azimuth -120: 5°, -60: 12°, -20: 3°, 0: 7°, 20: 4°, 60: 15°, 90: 9°, 150: 2°), saved as `manuale.HOR`; VC6 the PVGIS horizon, saved; VC7 a horizon imported from a small CSV file of azimuth and height pairs | the `.HOR` format (text or binary) and the horizon block in the variant | 5 to 6 |
| D | `M01_tetto` VC0 and VC1 | one building per elementary shape, each alone with its own distinct dimensions (3.1, 4.3, 5.7, 7.9, 11.3, 13.7 where there are fields): house with 2-sided roof, asymmetric house, 4-sided roof, 2-sided roof with gables, 1-sided roof with gables, parallelepiped, pyramid, prisms, cylinder, chimney, tree, plus the 2D shapes. One object at X = 10, Y = 0, another at X = 0, Y = 20; rotate the whole scene by +20°. PV: a rectangular plane on a pitch, a polygonal field, an array of tables, portrait and landscape, two orientations (east and west pitches). Partition in strings; in VC1, the detailed module layout. Save the scene as `.SHD`, a building as `.BLD`, a group as `.SHO` | the `Params` order of every shape; the axes and rotations; the module layout block; the string partition; multi-orientation | 7 to 12 |
| O | `M02_sud` | case D's scene again at Sydney (-33.87, 151.21) | the southern-hemisphere axes and azimuth convention | 12 |
| E | `M03_sheds` VC0 to VC2 | VC0 unlimited sheds (pitch 6.0, collector width 2.27, 10 rows, inactive bands 0.02, electrical effect on); VC1 a 3D shed field of 5 rows × 20 modules, 2 high in landscape, pitch 7.3; VC2 bifacial sheds (2D model, ground albedo 0.31, height 1.27, bifaciality 0.71) | sheds keys in 8.1; bifacial | 13 to 14 |
| F | `M04_tracker` VC0 to VC5 | VC0 a 3D array of 12 horizontal N-S axis trackers, backtracking, phi ±55°, pitch 6.2; VC1 unlimited trackers; VC2 tilted axis; VC3 two-axis; VC4 vertical axis; VC5 bifacial trackers | the tracker field types and their keys | 15 to 16 |
| G | `M05_varie` VC0, VC1 | VC0 east-west domes, tilt 10°; VC1 seasonal tilt: summer 15°, winter 45°, winter October to March | `Dome`, `SeasonalTilt` | 16 |
| H | `M06_mppt` VC0 to VC2 | VC0 two sub-arrays with different generic modules on one inverter with 2 MPPT (power sharing); VC1 one inverter with 6 MPPT, uneven strings if allowed; VC2 one sub-array on two orientations | `NInvMPPT`, `PNomAC_InMPPT`, circuit nodes, `NStrOrient<k>` | 17 to 18 |
| I | `M06_mppt` VC3 | a generic optimizer (and SolarEdge, if generic ones exist) | optimizer keys; whether an optimizer file exists | 19 |
| J | `M07_accumulo` VC0 to VC2 | VC0 self-consumption storage: a generic Li-ion battery saved as `Prova_batteria.BTR` with a distinctive capacity; SOC limits 0.21 and 0.89; initial 0.47; charge 3.3 kW, discharge 3.7 kW; load from a CSV. VC1 peak shaving with an injection limit. VC2 weak grid with random outages | the storage block and the `.BTR` written by PVsyst 8.1 | 20 to 21 |
| K | `M07_accumulo` VC3 to VC5 | load: constant 1.23 kW; a daily profile; a CSV hourly profile kept "internally", then "read the file" | `pvLoad` and the stored time series | 22 |
| L | `M08_meteo` | import of a PVGIS hourly series through the custom import (keep the `.MEF`); a small PVsyst standard CSV (hand-written, 2 days); a 15-minute series and a sub-hourly simulation; a synthetic Meteonorm file from a `.SIT` | `.MEF`; sub-hourly `.MET` (`PasAccum`, tokens per day); the standard CSV path | 23 to 25 |
| M | `M00_base` batch | batch with 5 runs varying tilt, azimuth, Uc, module quality and modules in series; hourly files for two runs; "Create PDF report"; save the result template (RVT) and the output format (SFI) | `_BatchParams_`, `_BatchResults_`, RVT, SFI in 8.1 | 26 |
| N | export | File > Export components: `M01_tetto` with "referenced files", then "Zip export folder"; export the generic PAN, OND and BTR used; save a PAN and an OND "in old format"; export a price list (`.PRI`) after setting one price | whether built-in components are exported as files; the old PAN/OND format; `.PRI` | 27 |
| P | `M00_base` VC8 | economic evaluation with one loan, CO2 balance, P50/P90 on | keys for completeness | 28 |
| Q | `M09_reale` | an Italian rooftop already drawn in Meridiana (for example `Prova capannone Rho.meridiana` in `meridiana-prove`), rebuilt in PVsyst; if time allows, one of study 11's public cases rebuilt from its report (with generic components, so for the files only) | an end-to-end check: import into Meridiana and both simulations | 29 to 30 |

### 8.3 Settings common to all cases
- **Hourly output** (Advanced simulation > Output file): GlobHor, DiffHor, T_Amb, WindVel, GlobInc,
  GlobEff, ShdLoss, IAMLoss, EArrNom, EArray, TArray, EOutInv, E_Grid, HSol, AzSol. In case J add the
  battery variables; in case E add the rear-side ones. Save it once as an SFI template.
- **Report:** all pages, in English, and once in Italian (case A), to see the translated labels.
- **Simulation:** run every variant, so that the results are in the files.
- **PVsystCLI** has its own trial (250 runs in 60 days, GCU 2.4). It is not needed for the formats; it
  would be useful later only for automatic regression tests against PVsyst.

---

## 9. Legal note (facts with sources, not advice)

What Meridiana would do: read data files that a user saved with a licensed PVsyst, in order to import a
design. It would not decompile, disassemble or otherwise inspect PVsyst's programs.

### 9.1 PVsyst's own terms
1. **The binding texts.** They are the "General Conditions of Use" (GCU, dated 01.06.2026, covering
   PVsyst 8, PVsystCLI and PVsystBasic) and the "Subscription contract" (dated 02.10.2026). The French
   text of the GCU prevails (GCU 2.2).
   - https://www.pvsyst.com/pdf/common/general-conditions-of-use-english.pdf
   - https://www.pvsyst.com/pdf/common/general-conditions-of-use-french.pdf
   - https://www.pvsyst.com/pdf/common/subscription-contract-english.pdf
2. **Software.** GCU 6.2: "It is strictly forbidden to reproduce, modify, edit, translate, decompile, or
   recompile the Software." The contract (art. 11) keeps all intellectual property on the Software with
   PVsyst SA.
3. **Generated files.** GCU section 8, "Results and files generated by the Software", says:
   - no guarantee on results (8.1);
   - the licensee's name on reports (8.2);
   - the user must "quote PVsyst in the event of publication of images or tables generated by the
     Software" (8.4).

   Neither text, in the English or the French version, mentions file formats, reading generated files
   with other programs, or interoperability (a reading of both PDFs for this study). GCU 7.3 says the customer "is solely
   responsible for the backup of his own data".
4. **Meteonorm.** GCU 1.3: "By contract with Meteotest AG, the export of data from Meteonorm to other
   software is not permitted." This concerns the `.SIT` and `.MET` built from Meteonorm (`*_MN81_SYN.MET`
   and the like).
5. **Evaluation.**
   - GCU 2.4 sets a 30-day EVALUATION mode in which "Only generic components can be used", followed by
     DEMO mode.
   - PVsystCLI's evaluation is 250 runs within 60 days.
   - The contract (3.2) says the evaluation lets the customer "test all the software functionalities".
6. **Applicable law.** GCU 12 and the contract (art. 13): Swiss law, courts of Geneva.
7. **What the help says about the files.** These are help statements, not licence clauses.
   - The format is "intended for internal use only. We provide no support regarding this format", and
     the files "should not be modified"
     (https://www.pvsyst.com/help/getting-started/file-organisation/user-data/format-of-pvsyst-files.html).
   - The SFI is "a proprietary file format which should not be generated outside PVsyst"
     (https://www.pvsyst.com/help/glossary/pv-system/sfi-file-format.html).

### 9.2 European Union
8. **Directive 2009/24/EC** on the legal protection of computer programs, codified version (OJ L 111,
   5.5.2009; https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32009L0024):
   - art. 1(2): ideas and principles, including those underlying interfaces, are not protected;
   - art. 5(3): a person entitled to use a program may "observe, study or test the functioning of the
     program" while loading, running or storing it;
   - art. 6(1): decompilation is allowed without authorisation only where "indispensable to obtain the
     information necessary to achieve the interoperability" of an independently created program, under
     conditions (a) to (c); art. 6(2) limits the use of what is obtained;
   - art. 8, second paragraph: "Any contractual provisions contrary to Article 6 or to the exceptions
     provided for in Article 5(2) and (3) shall be null and void."
   - The Italian text is archived locally:
     `l'archivio locale delle norme\laws\Direttiva 2009-24-CE - Tutela giuridica dei programmi per elaboratore (versione codificata) - GUUE L 111 del 05-05-2009.pdf`
     (articles 5, 6 and 8 on page 4).
9. **Court of Justice, C-406/10, SAS Institute v World Programming** (Grand Chamber, 2 May 2012,
   ECLI:EU:C:2012:259; https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:62010CJ0406):
   - neither the functionality of a program, nor its programming language, nor "the format of data files
     used in a computer program in order to exploit certain of its functions" is protected as a computer
     program (paras 39 and 46, ruling point 1);
   - copying the source or object code that implements a format could still be a partial reproduction
     (para 43);
   - in that case there was no decompilation: the defendant had observed, studied and tested the program
     (para 44);
   - a file format may still be protected as a work under Directive 2001/29 if it is its author's own
     intellectual creation (para 45);
   - a licensee may observe, study and test within the acts its licence allows, and contract clauses
     contrary to art. 5(3) are void (paras 50 to 62, ruling point 2).

### 9.3 Italy and Switzerland
10. **Italy, Law 633/1941.**
    - Art. 64-ter, paragraph 3: observe, study and test; it ends "Le clausole contrattuali pattuite in
      violazione del presente comma e del comma 2 sono nulle"
      (https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1941-04-22;633~art64ter).
    - Art. 64-quater: decompilation, with the same nullity of contrary clauses (paragraph 3)
      (https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:1941-04-22;633~art64quater).
    - The law is not in the local archive (`reference\laws`, checked with `cerca_norme.py`); Normattiva's
      PDF could not be downloaded automatically.
11. **Switzerland, Copyright Act** (LDA/URG, SR 231.1; https://www.fedlex.admin.ch/eli/cc/1993/1798_1798_1798/it#art_21):
    - art. 21 allows a person entitled to use a program to obtain, by decoding its code, the information
      needed to interface with independently developed programs, and limits its use;
    - unlike art. 24 paragraph 2 (backup copy), art. 21 does not say that contractual waivers are
      excluded.

### 9.4 What could not be read
EUR-Lex returned an automated check page; the Directive and the judgment were read from the EU
Publications Office's machine-readable copies (https://publications.europa.eu/resource/celex/32009L0024
and .../62010CJ0406), with no fake browser identity. EUR-Lex remains the reference to cite. PVcase's help
(https://help.pvcase.com/) answered HTTP 403. These facts are not legal advice.

---

## 10. Open points
1. **`.HOR`.** Its format and the horizon block in the variant: case C.
2. **`Params` order** of every elementary 3D object: case D.
3. **Storage.** The storage keys of 8.1 and a `.BTR` written by 8.1: case J.
4. **8.1 keys** for monthly soiling and albedo series, sub-hourly `.MET` and the module layout: cases B2,
   L and D.
5. **Built-in components.** Whether an export with referenced files carries the built-in modules and
   inverters as `.PAN`/`.OND`: case N. If it does not, the import depends on Meridiana's catalogue and on
   the designer.
6. **Old files.** No 6.x project or variant was found. Accepting them rests on the help's statement that
   6.40 and later are text; a 6.x example would still be welcome.
7. **Units.** The units of a few keys (`AuxPower_*`, `UFAverEffic`, `PMismUFixe`) and the meaning of the
   `Flags` bit fields: they matter little for a design import.

## Appendix: scripts written for this study
All are in
`C:\Users\utente\AppData\Local\Temp\claude\c--Users-Grasso-Elettrico\ac24d128-fcc4-4bd8-9c13-8ce732bbae55\scratchpad\formati\`
and were run with `python -I`:
- `pvobj.py`: outline, key inventory and markers of PVObject files;
- `vcdecode.py`, `vcmonthly.py`, `vccheck.py`: the base-62 records and the checks of 2.4 and 7;
- `metprobe.py`: the first decoding trials;
- `pdftext.py`, `pdftoc.py`, `pdfmeta.py`: reports;
- `safezip.py`: safe listing and extraction;
- `helpsearch.py`, `helpdump.py`: the PVsyst help index;
- `ghsearch.py`, `fetch.py`: paced GitHub searches and downloads with hashes.

They are a study's tools, not code for Meridiana. The import of section 6 should be written anew in
`src/meridiana/pvsyst/`, with its tests.
