<h1 align="center">Meridiana</h1>

<p align="center">
  Photovoltaic design on the desktop: map, building model, sun, module layout, energy, economics and the Italian standards.<br>
  <a href="https://github.com/daniel-g-carrasco/meridiana">github.com/daniel-g-carrasco/meridiana</a>
</p>

Meridiana is a desktop program for designing photovoltaic plants, for Windows and Linux. It is written in Python
with Qt (PySide6) and is free software under the GPL-3.0-or-later.

It is made for designers who work with the Italian rules: CEI 0-21 and CEI 0-16 for the connection, CEI 64-8 and
CEI 82-25 for the plant and its strings, the fire brigade rules for the distances on the roof (DCPREV
14030/2025), the ARERA time bands for the consumption. The scope is the whole country; regional rules, where
they exist, are options and never the default. The interface is in Italian and English; the manual is in Italian.

> [!NOTE]
> Meridiana is under development and has no published release yet. Every result carries its pedigree (the
> formula, the values, their source), but check the numbers before using them in a real project.

## What it does

The work follows six phases, shown as a bar at the top of the window; each phase has its tools and its page of
results.

1. **Modelling.** The site from an address or coordinates, on the national orthophoto, OpenStreetMap or other
   public map sources. Buildings traced with CAD-like aids (guides, typed lengths and angles, rectangles,
   squaring, snapping), flat and pitched roofs, canopies, exclusions and obstacles for the shadows. Plan and 3D
   view side by side.
2. **Plant.** Panels first: sub-fields with their own mounting, tilt, orientation and margins, laid automatically or
   row by row by hand, keeping the margins, the fire brigade distances and the row pitch the sun asks for. Then
   the inverter (from the catalogue or sized by the program), the storage (AC or DC battery), and the strings:
   proposed, completed or drawn by hand, checked against CEI 64-8/7 and the inverter's limits, with optimizers
   where they are used.
3. **Production.** The hourly production of a PVGIS typical meteorological year with every loss on the way
   (pvlib): horizon, shading between rows and from obstacles, soiling, mismatch, cables, inverter efficiency and
   clipping. PVGIS's own estimate beside it. Variants to compare layouts.
4. **Consumption.** The loads of the supply point: standard profiles, bills, measured curves, ARERA time bands.
5. **Balance and economics.** Self-consumption with or without a battery, savings, dedicated withdrawal,
   renewable energy communities, NPV, IRR, payback, LCOE.
6. **Report.** A PDF report where every calculation shows its formula, its values and their origin, with the
   datasheets attached; exports to IFC4 (for the architect or a BIM coordinator) and CSV of the hourly values;
   numbered revisions of the project.

Across the phases:

- a **Checks** panel that lists what is not yet right against the standards and the plant's own limits;
- a **product catalogue** of modules, inverters, microinverters, optimizers and batteries: the NREL CEC lists, a
  curated set read from the manufacturers' datasheets, and a personal catalogue;
- the import of **PVsyst** projects and variants (read only);
- **Meridio**, an assistant that answers questions about the open project with a language model running on the
  computer or, if you choose it and give your own key, with Claude;
- a **manual** inside the program (Help > Manual, F1 on any field), in Italian, also readable in
  [`docs/manuale`](docs/manuale/README.md).

The full list of functions and their state is in [`docs/funzionalita.md`](docs/funzionalita.md) (in Italian).

### In development

The phase names and the order of the tools are being reorganised as described above (Modelling, then Plant with
panels, inverter and storage): some builds may still show the previous names. 3D objects for the shadows (trees,
cars), the module layout on canopies, a DXF export and a published Flatpak are planned and not yet available.

## Install

### Windows

Windows 10 or 11, 64 bit. When a release is published on the
[releases page](https://github.com/daniel-g-carrasco/meridiana/releases) it has two files:

- `meridiana-setup-vX.Y.Z-windows-x64.exe`, the installer: for your user only, no administrator rights, opens
  the `.mer` project files with Meridiana. Once a day the program asks GitHub whether a newer version is out
  (Preferences > Privacy turns it off; Help > Check for updates asks at once) and offers to install it.
- `meridiana-vX.Y.Z-windows-x64-portable.zip`, the same program in a folder: unzip and start `Meridiana.exe`.
  It does not update itself: it opens the page of the newer version instead.

Each file has a [minisign](https://jedisct1.github.io/minisign/) signature (`.minisig`); the key and the command
that checks a download are in [CODE_SIGNING.md](CODE_SIGNING.md). The installer is not signed with Authenticode,
so Windows SmartScreen warns the first time ("More info", then "Run anyway").

Settings stay in `%APPDATA%\Meridiana`, caches and recovery copies in `%LOCALAPPDATA%\Meridiana`; uninstalling
leaves them.

### Linux (Flatpak)

The Flatpak is built from `build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml` on the KDE runtime 6.11
with the PySide BaseApp. It is not published in a repository yet; to build and install it locally:

```bash
flatpak install --user flathub org.kde.Sdk//6.11 io.qt.PySide.BaseApp//6.11
flatpak-builder --user --install --force-clean build-dir build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml
flatpak run io.github.daniel_g_carrasco.meridiana
```

In the Flatpak, Meridio speaks with the system's voice (the Kokoro voice is not packaged).

### From the sources

Python 3.12 or newer (the packages are built with 3.12). Qt comes as three wheels (Essentials, Addons, Pdf), so
the download stays small.

```bash
git clone https://github.com/daniel-g-carrasco/meridiana.git
cd meridiana
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # on Windows: .venv\Scripts\pip ...
.venv/bin/python tools/compile_po.py          # the Italian catalogue (without it the window is in English)
.venv/bin/python bin/meridiana
```

Optional parts, imported only when used: `ifcopenshell` for the IFC4 export and import, `anthropic` and
`keyring` for Meridio with Claude, `kokoro-onnx` for Meridio's natural voice (its model is downloaded separately).

`meridiana --self-test [REPORT]` checks the program without a screen and without touching your settings: it lays
out and computes a sample project offscreen, writes a report and exits with 0 when every check passed.

## What leaves the computer

Nothing about you, and never your project files. A few services receive only what they need to answer, each with
its own switch in Preferences > Privacy:

| Service | What it receives | What for |
|---|---|---|
| Nominatim (OpenStreetMap) | the address you type | finding the site |
| PVGIS (European Commission, JRC) | the site's coordinates | weather year, horizon, reference estimate |
| Map tile servers | the area in view | the background map or orthophoto |
| GitHub (Windows program only) | a version request | checking for updates |
| Anthropic (only if you choose Claude for Meridio) | your questions and the project context you allow | the assistant's answers |

## Development

```bash
python -m ruff check src tests tools                              # lint (rules F, E9, B in pyproject.toml)
python tools/compile_po.py                                        # the catalogues the tests load
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests    # the whole suite, offscreen
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests/nucleo -t tests   # one group
python tools/compile_po.py --update                               # refresh po/meridiana.pot and po/*.po (Linux)
```

The tests are grouped in packages under `tests/`:

| Group | What it covers |
|---|---|
| `nucleo/` | the core without Qt: geometry, sun, roofs, layout, rules, checks, project file |
| `calcoli/` | the energy pipeline against recorded PVGIS answers (`calcoli/riferimenti/`) |
| `formati/` | project files of every format version, frozen (a new format adds a file, never rewrites one) |
| `widget/` | one widget at a time, offscreen |
| `finestra/` | the main window, driven along journeys of steps |
| `esterni/` | what needs real PVsyst files or an idle machine; run only on request |

The CI (`.github/workflows/test.yml`) runs lint and the suite on Linux offscreen on every push; the Windows bundle,
installer and self-test run on a `v*` tag or by hand.

### Repository layout

```
bin/               the launcher
src/meridiana/     the core, plain Python without Qt: coordinates, sun, roofs, layout, drawing aids, rules,
                   checks, session, project file; energy/ (meteo, simulation, strings, storage, economics),
                   catalog/, pvsyst/ (reading PVsyst files), assistant/ (Meridio)
src/meridiana/ui/  the window: it displays and collects the gestures, every computation lives in the core
tests/             the suite, by group
po/, locale/       translations (gettext)
data/              fonts, icons, ISTAT municipalities, Natural Earth outlines, Meridio's drawings
build-aux/         Windows (PyInstaller, Inno Setup) and Flatpak packaging
docs/              the manual, the function list, the design studies and the project diary (in Italian)
tools/             helper scripts: catalogues, translations, icons, map coverage, PVsyst comparison
```

How the packages are built and released is in `docs/progetto.md`, section 4 (in Italian).

## Data, services and credits

Meridiana stands on the work of others. The libraries (Qt for Python, pvlib, shapely, numpy, scipy, pandas,
matplotlib, pyqtgraph, pypdf, IfcOpenShell), the fonts (Inter, Titillium Web), the Lucide icons, the NREL CEC
module and inverter lists, the ISTAT municipalities, the Natural Earth outlines and every map source with its
attribution are listed with their licences in [ATTRIBUTIONS.md](ATTRIBUTIONS.md). The squaring of a traced
outline is ported from the OpenStreetMap editor iD. PVGIS, OpenStreetMap, OpenTopoMap and the national and
regional orthophoto services are used under their own terms: check them before a commercial use.

The references for the functions are PVsyst (what a PV design program computes), Aurora (the modelling and the
use) and PVGIS (the weather data). Comparisons with PVGIS and PVsyst are in `docs/validazione-pvgis.md` and
`docs/validazione-pvsyst.md`.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). Qt Quick 3D, which draws the 3D view, is available under the GPL v3 or a
commercial licence: the program as a whole is GPL v3.
