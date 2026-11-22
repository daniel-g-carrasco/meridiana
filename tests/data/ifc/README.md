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

`r575-sintetico.ifc` (8 kB) is made by hand for Meridiana's tests (10/11/2026), no data of any real model: a site
placed at 84.409 m with a storey whose Elevation attribute is 0.26 m (its ground floor in the world is 84.669 m, its
terrain's top 84.369 m, the model's zero since R602), a
flat roof, and one element for each way the fast reading draws a shape wrong (a fan of an L, a hole, an arc, a frame,
a U wall, a terrain, a site with a shape). GPL-3.0-or-later, as Meridiana.

`r575-d9-tagli.ifc` (4 kB) is made by hand for Meridiana's tests (11/11/2026), no data of any real model: IFC2X3 in
metres, a wall with a window opening flush with its faces (`IfcOpeningElement`, `IfcRelVoidsElement`), a wall clipped
by a sloping plane (`IfcHalfSpaceSolid`) and a beam whose end is notched by a half space bounded by an L outline
(`IfcPolygonalBoundedHalfSpace`). Their areas and volumes are exact, and IfcOpenShell 0.9 gives the same. GPL-3.0-or-later,
as Meridiana.

`r575-falda-montante.ifc` (3 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a roof slab of 12 x 8 m whose plane falls towards no side of its outline (the import offers that plane as a
placement area of its own), a sloping mullion of 5 x 5 cm, 2.8 m long in plan, standing on it (a slender element
leaning over a roof: the import leaves it out, it made a wall that does not exist) and a chimney of 1 x 1 x 1.8 m away
from it (the import makes it the model's one obstacle). GPL-3.0-or-later, as Meridiana.

`vetrata-inclinata.ifc` (5 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a flat roof slab of 20 x 10 m at 6 m, a curtain wall of one glass plate sloping 35 degrees with two mullions
of 5 x 5 cm lying on it (a shed's glazing made as a curtain wall), an upright curtain wall 2 m tall with one mullion,
and a chimney 1.5 m tall. GPL-3.0-or-later, as Meridiana.

`finestra-facciata.ifc` (8 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a low flat roof at 4 m in front of the 0.4 m facade wall of a higher body whose roof, at 12 m, stops 0.6 m
behind that facade; in the facade a window (a curtain wall of two mullions and a transom, 6 to 7.5 m) above the low
roof; on the low roof a chimney and a machine 1 m in front of the wall. GPL-3.0-or-later, as Meridiana.

`parapetto-parziale.ifc` (4 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a flat roof slab of 12 x 8 m at 6 m with a parapet wall 1.1 m tall on three sides and, at the edge of the
fourth, a wall 2 m long and 4 m tall; far from it a second flat roof slab of 10 x 6 m at 6 m with only a wall 2 m
long and 0.6 m tall at its edge (the import makes the first a parapet of 1.1 m and the two walls obstacles).
GPL-3.0-or-later, as Meridiana.

`tirante-inclinato.ifc` (4 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a flat roof slab of 12 x 8 m at 6 m; on it a tie rod (`IfcMember`) of 20 x 20 mm, 5 m long, leaning 37 degrees
from the vertical with its foot on the roof (left out: a slender element leaning over a roof), a chimney 1.5 m tall and
a plate (`IfcBuildingElementProxy`) of 2 x 1 x 0.05 m whose 2 m side rises 35 degrees from the roof, its low side on it
(not slender: an obstacle 1.19 m tall). GPL-3.0-or-later, as Meridiana.

`ringhiera-sospesa.ifc` (8 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a flat roof slab of 12 x 8 m at 4 m; above it a railing (`IfcRailing`) 1 m tall and 6 m long whose bottom is
4 m above the roof, with nothing under it (since 14/11/2026 an obstacle raised by 4 m); a wall 1.2 m tall and one 2.2 m
tall standing on the roof, each with a railing 1 m tall on its top (raised by the height of their walls); three
segments of a mullion (`IfcMember`) of 0.15 x 0.15 x 2.3 m stacked one on the other from the roof to 6.9 m (one
obstacle 6.9 m tall, on the roof); a chimney 1.5 m tall. GPL-3.0-or-later, as Meridiana.

`ringhiera-scala.ifc` (3 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4 in
metres, a flat roof slab of 12 x 8 m at 4 m; above it a railing (`IfcRailing`) 1 m tall climbing a stair, its bottom
from 2.4 to 5.4 m above the roof along 6 m (left out: raised from its underside it would be a wall 4 m tall), and a
railing 1 m tall and 6 m long lying level 1.5 m above the roof (raised by 1.5 m). Written by a script of the local
study (r34). GPL-3.0-or-later, as Meridiana.

`mappato-ripetuto.ifc` (4 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, a flat roof slab of 12 x 8 m at 6 m and three IfcBuildingElementProxy (UNITA_A, UNITA_B, UNITA_C), instances of
one IfcRepresentationMap holding an IfcFacetedBrep, a box of 1 x 1 x 1 m standing on the roof, at three placements, the
third turned by 30 degrees by its IfcCartesianTransformationOperator3D (as a family placed many times by Revit). No
presentation layer. GPL-3.0-or-later, as Meridiana.

`piani-pari.ifc` (3 kB) is made by hand for Meridiana's tests (13/11/2026), no data of any real model: IFC4 in
metres, one flat roof at 6 m made of two slabs side by side, 6 x 8 m each, the first contained in the storey «Piano 6
ala est», the second in «Piano 7 ala ovest» (one body whose elements are as many in one storey as in the other).
GPL-3.0-or-later, as Meridiana.

`solai-interni.ifc` (6 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4 in
metres, one building without IfcRoof and five slabs: one of 10 x 8 m at 4 m under a ceiling (`IfcCovering` CEILING)
at 6.7 m, with a partition 2.7 m tall under it; one of 10 x 10 m at 8 m with three partitions 8 m long and 3 m tall
standing inside it and nothing over it; one of 3.6 x 5.8 m at 4 m in the recess of a U slab (12 x 10 m less a recess
of 4 x 6 m) at 7 m, whose convex hull covers it and whose plan does not; the highest, 10 x 10 m at 12 m, free, with a
chimney 1.5 m tall (the import keeps the U, the slab in its recess and the highest as roofs, leaves out the first as
a floor and raises the second to the top of its partitions, 11 m).
GPL-3.0-or-later, as Meridiana.

`terreno-interrato.ifc` (5 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4 in
metres, a building of 20 x 10 m with the storeys «Piano terra» at 0 and «Interrato» at -3 m; a flat roof slab at 6 m, a
ground floor slab, a basement slab from -3.2 to -3 m and a basement wall from -3 to 0 m; a terrain
(`IfcGeographicElement` TERRAIN) of 60 x 50 m whose top is at -0.6 m around the building and is dug to -3.2 m under it;
a parking slab (`IfcSlab` FLOOR) of 12 x 10 m beside the building, its top at -0.6 m, flush with the terrain (the import
takes the model's zero from the terrain, -0.6 m, and opens the lawn on the basement). `terreno-pavimenti.ifc` (4 kB)
is the same without the terrain (the zero comes from the parking slab). Both written by a script of the local study
(R602). GPL-3.0-or-later, as Meridiana.

`muro-strati.ifc` (6 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4 in metres,
two walls of 5 x 0.3 x 3 m each drawn as three extruded layers, a dark core (0.47) of 26 cm between two light skins
(0.93) of 2 cm, each layer with its `IfcStyledItem` (as a wall drawn layer by layer); the second with a window opening
of 1 x 2 m through all its layers; and a window as an `IfcRepresentationMap` of a frame and a pane of glass (60 %
transparent), each with its style (R608: each item keeps its colour in the 3D). GPL-3.0-or-later, as Meridiana.

`falda-mono-separata.ifc` (4 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4
in metres, one building with a flat roof slab of 10 x 10 m at 6 m and, against its east side, a mono-pitched roof slab
of 3 x 4 m, 3.6 m high on its south side and 3.4 m on its north side (R608: the body of that pitch alone falls north,
as the file's plane). GPL-3.0-or-later, as Meridiana.

`profilo-ellisse.ifc` (3 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4 in
metres, a pavement slab of 4 x 4 x 0.2 m whose outline is an `IfcCompositeCurve` of polylines and, at one corner, an
`IfcTrimmedCurve` on an `IfcEllipse` of semi-axes 1 and 1.0001 m trimmed from 0 to 90 degrees (R608: the outline is
read with its arc). GPL-3.0-or-later, as Meridiana.

`grigliati.ifc` (5 kB) is made by hand for Meridiana's tests (14/11/2026), no data of any real model: IFC4 in metres,
one building without roofs and three slabs of 10 x 10 m with their top at 6 m, each with a column 1.5 m tall in its
middle: a concrete slab 20 cm thick; a grating 4 cm thick named as Revit names one («Floor:S_FL_SF_Gratings-40mm»);
a platform 4 cm thick whose name says nothing and whose `IfcSlabType` is «Stahlgitterrost 30/30» (R608: a grating
is drawn opaque in a metal grey, casts its shadow, is never a roof, and what stands on it is no obstacle). GPL-3.0-or-later, as
Meridiana.
