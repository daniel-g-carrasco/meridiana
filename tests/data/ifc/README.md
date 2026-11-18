# Public IFC samples for the import tests

`Building-Architecture.ifc` (142 kB) and `Building-Hvac.ifc` (111 kB) are buildingSMART's certification samples
«Simple-Scene» in IFC4, taken unchanged on 25/10/2026 from https://github.com/buildingSMART/Sample-Test-Files
(folder `IFC 4.0.2.1 (IFC 4 ADD2 TC1)/Simple-Scene`, commit 80d976a9b193a26a8e928c3e79bff67af1de68a8).

- Copyright (C) buildingSMART International Ltd., licensed under the Creative Commons Attribution 4.0
  International License: https://creativecommons.org/licenses/by/4.0/ . No change was made.
- SHA-256:
  - `Building-Architecture.ifc` 8790a1e193e82b8e7e7f337ec2633cd40f2120590317a1443503a25b079e2e80
  - `Building-Hvac.ifc` 2c17ecad2b0fbd3335420ee42ba48963b5a395294e86bcdcfc786ee559f9a344

What the tests read in them (study 20, `docs/studio/20-ifc-importazione.md`):

- `Building-Architecture.ifc`, written by «IFC manager for SketchUp»: millimetres, a gable roof of two IfcSlab without
  PredefinedType in an IfcRoof hung on a second IfcSite (not in the building), no RefLatitude, an IfcMapConversion on
  EPSG:32760 with a scale of 0,001 and its X axis turned by 60 degrees while the TrueNorth says +Y.
- `Building-Hvac.ifc`: the installations only, no roof, no slab, no wall: nothing a building can be made of.

The larger samples of the study (Duplex, Clinic, Schependomlaan, Esplanades, the files of IfcOpenShell that crash it)
are not committed: `docs/studio/20-prove/campioni.json` says where they come from and under which licence.
