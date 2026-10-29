<h1 align="center">Meridiana</h1>

<p align="center">
  Photovoltaic design: map, building model, sun path, module layout and Italian standards.<br>
  <a href="https://github.com/daniel-g-carrasco/meridiana">github.com/daniel-g-carrasco/meridiana</a>
</p>

Meridiana is a desktop program for designing photovoltaic systems, for Windows and Linux. It is free software
(GPL-3.0-or-later) and under development: the results carry their pedigree, but check them before a real project.
PVsyst is the reference for the functions, Aurora for the modelling and the use, PVGIS for the weather data; the
standards are the Italian ones, for the whole country.

What it does today:

- the site from an address or coordinates, on the national orthophoto or OpenStreetMap;
- buildings traced with CAD-like drawing aids (guides, typed lengths and angles, rectangles, squaring),
  flat and pitched roofs, exclusions; sub-fields with their own mounting, tilt, orientation and margins;
- the modules laid on request or row by row by hand, keeping the margins, the fire-brigade rules (DCPREV
  14030/2025) and the row pitch the sun asks for; plan and 3D views side by side;
- the hourly production of a PVGIS typical year with every loss on the way (pvlib), PVGIS's own estimate
  beside it, the shading of the horizon, between rows and of the obstacles;
- strings checked against CEI 64-8/7, the connection against CEI 0-21;
- the consumption of the supply point (profiles, bills, measured curves, ARERA bands), self-consumption
  with or without a battery, the economics (saving, dedicated withdrawal, renewable energy communities,
  NPV, IRR, payback, LCOE);
- a product catalogue: modules, inverters, microinverters, optimizers, batteries;
- a PDF report where every calculation shows its formula, its values and their origin;
- Meridio, an assistant that answers about the project with a model on the computer (or, if you choose it and
  give your key, with Claude);
- a manual inside the program (Help > Manual, F1 on a field), in Italian, also readable here in
  [`docs/manuale`](docs/manuale/README.md).

The full list of functions and their state is in `docs/funzionalita.md` (in Italian); the design studies are in
`docs/studio/`.

## Install

### Windows

From the [releases](https://github.com/daniel-g-carrasco/meridiana/releases), Windows 10 or 11, 64 bit:

- `meridiana-setup-vX.Y.Z-windows-x64.exe`, the installer: for your user only, no administrator rights; it
  opens the `.mer` project files with Meridiana. Once a day at start the program asks GitHub whether a
  newer version is out (Preferences > Privacy turns it off; Help > Check for updates asks at once) and offers to
  install it.
- `meridiana-vX.Y.Z-windows-x64-portable.zip`, the same program in a folder: unzip it and start
  `Meridiana.exe`. It does not update itself: the newer version's page opens instead.

Each file has its signature (`.minisig`, [minisign](https://jedisct1.github.io/minisign/)): see
[CODE_SIGNING.md](CODE_SIGNING.md) for the key and the command that checks a download. The installer is not
signed with Authenticode: Windows SmartScreen warns the first time («More info», then «Run anyway»).

The settings stay in `%APPDATA%\Meridiana`, the program's own files (recovery copies, caches) in
`%LOCALAPPDATA%\Meridiana`: uninstalling leaves them.

### Flatpak

The Flatpak is built from `build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml` on the KDE runtime 6.11
with the PySide BaseApp; it is not published in a repository yet. To build and install it:

```bash
flatpak install --user flathub org.kde.Sdk//6.11 io.qt.PySide.BaseApp//6.11
flatpak-builder --user --install --force-clean build-dir build-aux/flatpak/io.github.daniel_g_carrasco.meridiana.yaml
flatpak run io.github.daniel_g_carrasco.meridiana
```

### From the sources

Needs Python 3.12 or newer (3.12 is the one the packages are built with).

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt     # on Windows: .venv\Scripts\pip ...
.venv/bin/python tools/compile_po.py          # the Italian catalogue (without it the window is in English)
.venv/bin/python bin/meridiana
```

`meridiana --self-test [REPORT]` checks the program without a screen and without touching your settings: it
lays and computes a sample project offscreen and exits with 0 when every check passed.

## What leaves the computer

Nothing about you, and never your project files. Four services receive what they need to answer, each with its
switch in Preferences > Privacy: OpenStreetMap's Nominatim (the address you type to find a site), the European
Commission's PVGIS (the site's coordinates, for the weather and the horizon), the map servers (the area in view)
and, in the Windows program, GitHub (whether a newer version is out). Meridio sends questions to Anthropic only if
you choose Claude, give your key and consent.

## Development

```bash
python -m ruff check src tests tools                          # lint
python tools/compile_po.py                                    # the catalogues the tests load
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests  # the tests (the window's need a display:
                                                              # offscreen will do)
python tools/compile_po.py --update                           # refresh po/meridiana.pot and po/*.po (on Linux)
```

The logic (coordinates, sun, roof pitches, layout, drawing aids, energy, checks, the project file) is plain
Python without Qt, in `src/meridiana/`, covered by the tests in `tests/`; the window (`src/meridiana/ui/`) only
displays and collects the gestures. How the packages are built and released is in `docs/progetto.md`, section 4
(in Italian).

## License

GPL-3.0-or-later, see [LICENSE](LICENSE); the third-party data and assets are listed in
[ATTRIBUTIONS.md](ATTRIBUTIONS.md). Qt Quick 3D, which draws the 3D view, is available under the GPL v3 or a
commercial licence: the program as a whole is GPL v3.
