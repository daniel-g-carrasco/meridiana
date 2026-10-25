# Attributions

Meridiana is free software under the GNU General Public License, version 3 or later (`LICENSE`). It stands
on the work of others: the libraries it runs on, the fonts, icons and product data it carries, and the
services it asks for maps and weather. This file lists each with its licence, as read in the package
metadata or in the licence file kept beside the data (the path is in the last column). The versions are the
ones of `requirements.txt` and of the development environment on 23/10/2026.

Help, About Meridiana shows a short version of this list; the full one is this file, which has to travel with
every distribution (source, installer, Flatpak: the packages are being rebuilt for Qt, theme H of study 18).

## Libraries the program runs on

| Component | Version | Licence |
|---|---|---|
| Qt for Python: PySide6, shiboken6, PySide6_Essentials, PySide6_Addons, PySide6_Pdf | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| Qt Quick 3D (inside PySide6_Addons) | 6.12 | GPL-3.0 or commercial: the program uses it under the GPL-3.0 |
| pvlib python | 0.16.1 | BSD-3-Clause |
| shapely | 2.2.0 | BSD-3-Clause |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| scipy | 1.18.1 | BSD |
| matplotlib | 3.11.2 | the matplotlib licence (PSF-style, BSD-compatible) |
| pyqtgraph | 0.14.0 | MIT |
| pypdf (the report's attachments, merged into its PDF) | 6.21.2 | BSD-3-Clause |
| pandas | 3.0.6 | BSD-3-Clause |
| requests | 2.34.2 | Apache-2.0 |
| anthropic (Claude's SDK, for Meridio in the cloud: optional, imported only when used) | 2.3.0 | Apache-2.0 |
| keyring (the cloud key in the system's keyring: optional, imported only when used) | 25.7.0 | MIT |
| kokoro-onnx (Meridio's natural voice, in a process of its own: optional) | 0.6.1 | MIT |
| onnxruntime (runs the voice's model) | 1.31.0 | MIT |
| phonemizer, espeakng-loader (the voice's phonemes, with espeak-ng) | 3.4.0, 0.2.4 | GPL-3.0, GPL-3.0 (espeak-ng) |
| IfcOpenShell (the IFC models, export and import: optional, imported only when used; the reading runs in a process of its own) | 0.9.0.post1 | LGPL-3.0-or-later |
| lark, isodate (brought by IfcOpenShell) | 1.3.1, 0.7.2 | MIT, BSD |

What these bring along (h5py, contourpy, cycler, fonttools, kiwisolver, pillow, pyparsing, python-dateutil,
pytz, tzdata, urllib3, idna, charset-normalizer, certifi, colorama; for anthropic and keyring: httpx2, httpcore2,
anyio, h11, sniffio, pydantic, pydantic-core, jiter, docstring-parser, truststore, opentelemetry-api, the jaraco
packages, more-itertools) is under BSD, MIT, MIT-CMU, Apache-2.0 or, for certifi, MPL-2.0 licences; each package carries its own licence file in the installed environment.
pyqtgraph carries colour maps as data the program does not use: the CET ones under CC-BY 4.0, viridis and its
kin under CC0, with their notices in `pyqtgraph/colors/maps`. PyInstaller (GPL-2.0-or-later with the bootloader exception) and Inno
Setup are build tools and are not distributed.

## Code adapted from other projects

| Component | Licence | Where |
|---|---|---|
| The squaring of a traced outline (`Q` on the plan), ported from the OpenStreetMap editor iD: `modules/actions/orthogonalize.ts` and `modules/geo/ortho.ts`, copyright (c) iD Contributors | ISC | `src/meridiana/squaring.py` (the notice is at the top of the file) |

## Fonts, icons and data carried in the program

| Component | Licence | Where |
|---|---|---|
| Inter (Regular, SemiBold, Bold), by Rasmus Andersson and the Inter Project Authors: the text's font since 25/10/2026 | SIL Open Font License 1.1 | `data/fonts/inter/OFL.txt` |
| Titillium Web (Regular, SemiBold, Bold), by the Accademia di Belle Arti di Urbino: the text's font until 25/10/2026, kept for a return | SIL Open Font License 1.1 | `data/fonts/titillium-web/OFL.txt` |
| Lucide icons (the 72 SVG files in `data/icons/lucide`), copyright (c) Lucide Icons and Contributors; some derive from Feather, copyright (c) Cole Bemis, MIT | ISC (MIT for the Feather ones) | `data/icons/lucide/LICENSE` |
| The CEC lists of PV modules and inverters, as NREL publishes them with the System Advisor Model (SAM), copyright (c) Alliance for Energy Innovation, LLC (modules: list 2026.7.3 of 23 June 2026, rebuilt with `tools/update_cec.py` from `CEC Modules.csv`) | BSD-3-Clause: the notice must go with every distribution | `src/meridiana/catalog/data/LICENSE-NREL-SAM.txt` |
| The curated catalogue (modules, inverters, microinverters, optimizers, batteries) | Technical data read from the manufacturers' datasheets, each record with the datasheet's address and the date it was read; the manufacturers' names and models are theirs | `src/meridiana/catalog/data/*_curated.json` |
| The application icon (`data/icons/hicolor`) | A placeholder drawn by the author for the template Meridiana started from, to be replaced by the program's own icon | `data/icons/hicolor/` |
| The outlines of the areas the map sources cover (countries, Italian provinces, Belgian provinces, German Länder, minor islands), simplified by `tools/map_coverage.py` | Natural Earth 1:10m, public domain (https://www.naturalearthdata.com/about/terms-of-use/) | `src/meridiana/mapcoverage.py` |
| Meridio, the assistant's character: the smooth drawing on a grid of 24 and the pixel one on a grid of 17 (R34), drawn for the program; the reference SVG files carry the default colours, the program draws them in the theme's colours from `src/meridiana/assistant/__init__.py` | GPL-3.0-or-later, as the program | `data/meridio/` |

The voice's model, Kokoro 1.0 (hexgrad, Apache-2.0, the files of kokoro-onnx: `kokoro-v1.0.onnx`,
`voices-v1.0.bin`), is not carried by the program: the designer puts it on the PC (assistant/speech.py).

The tests read two of buildingSMART's IFC4 samples, «Simple-Scene» `Building-Architecture.ifc` and
`Building-Hvac.ifc`, copyright (C) buildingSMART International Ltd., under the Creative Commons Attribution 4.0
International License, unchanged (`tests/data/ifc/README.md`); they are not part of the program.

## Services the program asks (nothing of them is in the project file)

These are requested while the program runs, kept in the cache folder of the user's disk, and never saved in
a project. Their own terms apply: check them before a commercial use.

| Service | What for | Terms |
|---|---|---|
| PVGIS, European Commission, Joint Research Centre | typical meteorological year, horizon and the production estimate shown beside Meridiana's | the JRC's terms for PVGIS |
| OpenStreetMap tile servers | background map, with the attribution "© OpenStreetMap contributors" on screen | data under the ODbL, and the tile usage policy |
| OpenTopoMap | topographic background, with the attribution "© OpenStreetMap contributors, SRTM, © OpenTopoMap (CC-BY-SA)" on screen | CC-BY-SA 3.0 |
| Geoportale Nazionale, Ministero dell'Ambiente e della Sicurezza Energetica (MASE), national orthophoto 2012 (PCN, AGEA) | background orthophoto | declared without access constraints or fees |
| The other map sources of `src/meridiana/tiles.py` (R36): the orthophotos of South Tyrol, Trentino, Tuscany, Friuli Venezia Giulia, France (IGN), Spain (PNOA), Portugal (DGT), the Netherlands (PDOK), Flanders, Wallonia, Brussels (UrbIS), Luxembourg, Switzerland (swisstopo), Austria (basemap.at), Czechia (ČÚZK), Poland (GUGiK), Slovenia (GURS), thirteen German Länder, the United States (USGS), EOX's Sentinel-2 cloudless 2016, basemap.de | background orthophotos and maps, each with its attribution on the plan | the licence of each source, with the address where it was read on 25/10/2026: in the source itself and in `docs/compiti/21-mappe.md` (CC BY 4.0, CC0, dl-de/zero-2-0, dl-de/by-2-0, Licence Ouverte 2.0, IODL 2.0, CC BY 2.5 IT, public domain, viewing services) |
| Nominatim, OpenStreetMap | search of an address | the ODbL and the Nominatim usage policy |

## How to keep this file true

A new dependency goes in `requirements.txt`, in `pyproject.toml` and here, with its licence; a new font, icon
or data file goes here with the path of its licence file. `tests/test_release.py` does not check this yet.
