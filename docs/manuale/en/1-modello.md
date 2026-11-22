<a id="1-modellazione"></a>

# 1. Modelling

Modelling is the drawing: the site, the buildings and their roofs, the canopies and the exclusions. Sub-fields and modules are then laid in the Plant phase. Draw on the plan with the tools on the bar of the phase and check in the 3D view. The selected object's properties are in the panel on the right. The help box at the bottom explains the field you are in. When you move between objects with the same fields, the page and its scroll position stay still and only the values change.

The tools have a letter (a default you can change in File > Settings > Keyboard): Select V, Building B, Pitch P, Lay S, Exclusion X, Row L, Move M (with Rotate inside it), Measure D, Rectangle by three clicks R, Square the corners Q; F3 for snaps and F8 for orthogonal mode, as in AutoCAD. The letters do not act while you type in a field.

The view cube at the top right of the 3D view stays compact. Click a face, edge or corner to orient the view; double-click to fit the drawing. Hover uses the common neutral overlay and keeps the labels readable. Its commands are on the 3D toolbar, in this order: Go to Home (house), Parallel projection (cube), Fit to the drawing (frame), Set this view as Home (pin), then the two zoom buttons. Parallel projection stays pressed while active. Home and F remain available in the view and appear in the tooltips. When there is too little room beside the cube, the toolbar moves below it. When it exceeds the view's width, it scrolls horizontally like the phase toolbar.

Drawing and measurement lines use a thin stroke, with the same light halo on light and dark backgrounds, and small points. Length pills follow the line with normal text weight and stay upright. In the 3D view, solids cover measurements and the span being drawn: a fully hidden measurement also hides its pill; when a sufficiently long portion remains visible, the pill sits on that portion.

<a id="il-sito"></a>

## The site

The site is the drawing's origin, with latitude and longitude. The sun, the weather from PVGIS and the region's rules start there. You can move the site only before drawing: the drawing is measured from it. The region is read from the address found. At present only Lombardy has its own rules; elsewhere the national rules apply.

**File > New** starts with the place. In the single field you can enter an address, a municipality, coordinates or a map link. While you type, suggestions come only from the ISTAT municipalities included in the program and recent projects on the PC. **Search** queries OpenStreetMap's Nominatim only when you press it. Accepted formats are decimal degrees, degrees-minutes-seconds, degrees and decimal minutes, Google Maps, OpenStreetMap and Apple links, UTM WGS84 or ED50, and Gauss-Boaga Roma40. The recognised format and datum appear below the field; ambiguous text is rejected with a reason. Check the marker on the map or click the point, then press **Create and draw**.

Optional data open below the field: project name, distributor, POD, voltage, phases, connection level and type, powers and application code. The voltage proposes the technical rule CEI 0-21 or 0-16; these data do not change the sun or the weather. A **Reserved project** never sends names or addresses to Nominatim and does not use Claude. Its coordinates stay on the PC until you give two separate consents, for map tiles and PVGIS weather, on the New page or in the site's Properties. **Find the site…**, in an existing project, follows the same rule.

<a id="passo-delle-file-dal-sole"></a>

### Row pitch from the sun

Choose the day and hours in the sub-field, under Row pitch, when the pitch is From the sun. On that day, between those hours, no row shades the next. This determines the pitch of sub-fields with tilted rows and the shadows that Out of the obstacles' shadows avoids. The standards leave the choice to the designer: CEI 82-25/3, 6.2 gives only the limiting angle (reference cited in `checks.py`).

<a id="giorno-e-ore-del-sottocampo"></a>

#### Day and hours of the sub-field

The Project default is 21 December, from 10 to 14 in true solar time, checked every 10 minutes (Meridiana defaults, `sun.py`, `DesignWindow`). As long as the sub-field uses Project default, it follows these values. Changing the day or hours creates its own window. Use for all sub-fields copies the displayed window to the project default and removes the other sub-fields' own windows, in one Undo step. On 21 December the sun is lowest: shadows are longest and the pitch is widest. A day nearer the equinox gives a shorter pitch and more modules, with some shading between rows on winter mornings and evenings. Read the loss in Production, under losses (shading between rows).

<a id="connessione-e-obblighi"></a>

### Connection and obligations

What the rules require beyond the drawing. The resulting rules are in [Checks](verifiche.md) and the notes for the report.

- **Connection.** Automatic from the power chooses low voltage up to 100 kW, medium voltage up to 10 MW and high voltage above (CEI 0-16:2026-07, 6.3, Tab. 4, p. 43, cited in `rules.py`: between 6 and 10 MW, medium or high). The distributor decides: if the connection offer says otherwise, choose it here.
- **Minimum renewable capacity.** For a new building or a major renovation, the obligation P = k × S of D.Lgs. 199/2021 (art. 26 and allegato III; rule N24), where S is the buildings' footprint; public building +10%. In Lombardy k increases for permit applications from 01/01/2027 (rule N25). The value of P and the comparison with the plant are in Checks.
- **Contracted power, Floor area of the premises, Premises, higher risk.** These determine who may design under DM 37/2008, art. 5 comma 2 (p. 4; rules N02 and N03): a registered professional is required above 6 kW of contracted power, above 200 m² for production, commerce and services, above 400 m² for a dwelling, always for condominiums, for supplies above 1000 V and for premises with a higher fire risk, medical use or explosion hazard. In other cases the installer's technical manager may design (art. 5 comma 1). Without these data Meridiana assumes a professional is required and says so.

<a id="gli-edifici"></a>

## The buildings

Draw the building as a footprint (Building tool, Rectangle by three clicks, or Draw > Building from a template…). The Eave height and roof (flat, mono-pitch, gable, hip, pitches drawn by hand) give the pitches on which sub-fields lie and the shadows the building casts on others. On a mono-pitch roof choose the eave side, also with Pick on the plan and a click on the side. On a flat roof the parapet, at the entered height all around the outline, shades nearby modules.

<a id="tetto"></a>

### Roof

The Roof group in the building's Properties. Gable and hip roofs follow any footprint (L, T, U, trapezoid...): each eave side has its pitch, all with the same slope. Ridges, hips and valleys are generated automatically (the straight skeleton, study 16, topic A). Choose Eave or Gable end for each side. A gable end is a side whose wall rises to the roof. A new gable roof has gable ends at the ends of its arms; a hip roof has none. Pick on the plan and a click on a side toggles between eave and gable end. A side next to a re-entrant corner that cannot be a gable end stays an eave, and the group says so.

The Covering proposes the Slope: Marseille tiles 35%, clay pantiles 30% (minimum slope, ANDIL manual *Coperture in laterizio* 2025, p. 7), sheet metal or panels 7% (manufacturers' datasheets, study 16 A.8). The slope remains editable in degrees and percent. Ridge height, if entered, determines the slope: the roof's highest point is at that elevation, and the slope is recalculated and displayed. Entering the slope again makes it the controlling value.

Hover over the building to highlight the ridges on the plan. Files saved before format 9 with a pitched roof on a non-rectangular footprint open with a warning: the roof now follows the footprint, sub-fields are placed on the pitch below their centre, and you must check them.

<a id="edificio-da-modello"></a>

### Building from a template

Draw > Building from a template… (or the Template button on the bar of the phase): rectangle, L, T, U or trapezoid with its dimensions and a rotation, and a drawing of the outline. Place it on the plan, then click where the south-west corner goes. Afterwards, change sides individually in the Sides group.

<a id="dal-modello-dellarchitetto-ifc"></a>

### From the architect's model (IFC)

In Modelling, the Building button's dropdown, From IFC (or File > Import an IFC model… in the menu bar, Alt): an .ifc or .ifczip file, IFC2X3 or IFC4. Meridiana reads only what photovoltaic design needs: roofs and what is above them (chimneys, skylights, equipment, parapets, trees), the site and north; for a building without a roof, slabs or walls. Reading runs in a separate process. The bar at the bottom shows progress, Cancel stops it, and it stops automatically after three minutes or above half the PC's memory. If this happens, ask the architect to export only the building, without furniture and equipment.

A box then says where the buildings go: where the file puts them, around the project site; move the site to the model (proposed when the project is empty or the model is far away); or at the site origin, the only option if the file is not georeferenced. If the map conversion and the file's TrueNorth disagree, you choose. Below are the buildings seen from above and what is taken, approximated and left out. Buildings enter with the recognised roof: flat, mono-pitch, gable or hip with gable ends, otherwise free pitches. Exclusions keep their height, and flat roofs their parapet. It is one change: Ctrl+Z removes it. Heights start from the building's zero level: check the eave height if the model has basements or absolute elevations.

File > Export the model as IFC4… does the reverse: the project as a georeferenced model, with every module laid and its string, for the architect or BIM coordinator.

<a id="lati"></a>

### Sides

Each side of the outline with its length, for buildings, sub-fields and exclusions. A new length moves the far end of the side and everything after it, as the stretch command in CAD programs does. A double click on a side's dimension on the plan does the same.

<a id="spostare-e-ruotare"></a>

### Moving and rotating

Move (M) picks up the selected object or the one you click: a base point then the destination, with snaps (F3). Or enter the displacement and press Enter: "3" means 3 m towards the pointer; "3;2" means 3 m east and 2 m north; Tab switches to the direction from north. Inside Move, R rotates around the centre (or the base point already clicked) in steps of 15°, 5° with Ctrl, 90° with Shift, or by the entered angle. Outside Move, R remains the rectangle. Hold Ctrl when clicking, or press C, to make a copy. Arrow keys move by 10 cm, 1 m with Shift, 1 cm with Ctrl. A handle at the object's centre moves it by dragging; one on the northernmost side rotates it. Esc exits.

A building takes its sub-fields, exclusions and free pitches with it. A sub-field stays on its pitch and, when rotated, rotates the row orientation if one is set. In the 3D view, with Move active, the object has east and north arrows, a plane square and a rotation ring. Typing a digit opens the value field beside it.

<a id="prevenzione-incendi"></a>

### Fire brigade

A photovoltaic system is not itself an activity subject to fire control (DCPREV 14030/2025, par. 1.1 punto 1, p. 3). The building is, if it houses one of the 80 activities in Allegato I of DPR 151/2011 (GU n. 221 del 22/09/2011, pp. 5-20; Meridiana uses the 2011 text).

In the Fire brigade group of the building's properties choose the activity from the list. Type its number or a few words ("49", "autorimesse") and the list finds the rows. The activity's threshold and the Gazzetta page appear below. In Category, each entry says what falls into A, B or C for that activity. Categories the activity does not have are disabled. Meridiana does not know the activity's staff, kW or square metres, so you choose; if there is only one category, it selects it automatically. Choosing an activity enables the activity subject to fire control checkbox. No activity subject to control clears it and removes the category. In a project before format 24, a checked box remains valid and the list says Subject, activity not specified. The activity and category go into the report notes (rule N13).

For an activity subject to control by the Vigili del Fuoco, the DCPREV 14030/2025 guidelines apply (rules N13 and N15 in `rules.py`). For modules above the roof (BAPV), Meridiana automatically applies the points of paragraph 3.3.5.1 (p. 13-16) during layout:

- a free band of at least 1 m from the roof edge;
- groups of modules no larger than 20 m in any direction, separated by corridors at least 2 m wide;
- at least 1 m extra around smoke vents, other openings and equipment on the roof.

These three values are those of the layout (`layout.py`, `fire_edge`, `fire_group`, `fire_corridor`). The guideline also requires 1 m from compartment walls below, except on fire-resistant roofs (punto 5). The Fire-resistant roof slab checkbox records this, but the layout does not currently draw those walls. The rest of the guideline (emergency isolation, signs, inspection register) belongs in the report. The notes are in Checks, ready to copy.

<a id="il-sottocampo"></a>

## The sub-field

The Sub-field is the area drawn for modules, on a pitch or on the ground. With **Lay** (S), the sub-field is created with its modules and its outline tight around them. With **Area with automatic layout** (in the Lay menu, or by right-clicking the roof), you draw an empty area. **Fill** fills it with the mounting, distances and fire brigade rules of its building. Fill is disabled for a full sub-field and says why. Below the buttons are the modules laid with their power Po,cc, azimuth and tilt; for tilted rows, the pitch, free gap and limiting angle; and the fire brigade groups. **Empty** removes the modules and leaves the outline.

<a id="le-file-a-mano"></a>

### Rows by hand

Automatic layout is the proposal; you can adjust rows by hand (study 16, topic C). The Row tool (L) draws a row in a sub-field: click where its front edge begins and ends, or enter the length and press Enter. It takes the sub-field's module, gaps, tables and orientation. While drawing, it appears red if it extends into the edge band or covers an exclusion (it still stays: you decide). In an empty sub-field the row you draw is the layout.

Click a module to select it; click the same row again to select the row. Delete removes the selected row. Move moves it within its sub-field (also with the 3D gizmo). Drag the square at its end to shorten or lengthen it. The right-click menu adds a row at the end, one pitch behind the last, and explodes a row (or all rows of the sub-field) into its modules. Each becomes a row with one position, moves independently and turns by 90° with a double click, as in Aurora. Modules keep their name ("row:position"), so manual strings and removed modules stay attached to them.

The first gesture makes the sub-field manual: its rows stay as they are, and a new pitch or margins do not move them. Rules followed by automatic layout become checks: groups above 20 m and corridors below 2 m under the fire brigade rules, modules over exclusions or beyond the edge band, modules shaded on the design day. Lay again automatically (sub-field button, Layout group, menu, Checks) asks first and can be undone: as PVsyst warns, manual changes are lost. A new module whose dimensions are within 2 cm of the previous one adapts the rows automatically. Otherwise Meridiana asks whether to adapt them or lay them again.

<a id="montaggio"></a>

### Mounting

How modules stand on the surface: flush with the pitch, integrated in the roof (BIPV), on anchored or ballasted tilted rows, in East-west pairs, on ground-mounted rows, on a canopy or carport. Mounting determines the tilt and whether the sun sets the row pitch. Flush, integrated and canopy are flush mountings (`layout.py`, `FLUSH`): rows do not shade each other and Between rows is an entered value. For ballasted rows on a slab, Checks remind you that ballast alone does not restrain the modules (NTC 2018 7.2.4; CEI 82-25/3 6.2, in `checks.py`).

<a id="moduli-per-tavola-in-altezza"></a>

### Modules per table, across

How many modules stand one above another in a table, across the row. With modules in portrait, 2 is the "2V" of ground mounts. More modules across make a taller row, so a longer pitch from the sun. Modules per table, along instead divides the row into tables (0: continuous rows), with the Between tables gap.

<a id="la-posa-dei-moduli"></a>

### Module placement

How rows stand relative to each other: **Aligned** (one grid, straight columns, the origin that fits the most modules; a sloping side leaves part of a module's space), **Staggered by half a module** (a row may move half a module from its neighbour, like bricks, where this fits more) or **Free** (each row uses all its space; rows may stand further apart than the pitch where needed, fitting more modules). New sub-fields start Aligned. A sub-field saved before this choice stays **As it was saved**, with the same modules, until you change it. When you change mode, manually removed modules stay removed at their positions wherever the new mode has a module.

<a id="potenza-richiesta"></a>

#### Power asked

Optional, in kWp. The sub-field lays the number of modules closest to this power, including above it; for equal differences, the one that does not exceed it (45 kWp with 475 W modules: 94.7, so 95 modules and 45.13 kWp). Modules are in adjacent rows, the last partly filled, starting with the least shaded rows. Shadows are estimated from the obstacles' shadow areas in the pitch design window and on the same day with two extra hours on each side, without an hourly calculation. For equal shading, the first row comes first. Tables stay whole, as do modules at the same position. If they do not fit, the card says how many are missing and the most the sub-field can hold. Manually removed modules do not count.

<a id="distanze-e-margini"></a>

### Gaps and margins

The gaps between modules, from the area edge, between rows and between tables. Defaults are 2 cm between modules (the clamps), 0.5 m from the edge, 2 cm between flush rows and 0.3 m between tables (Meridiana defaults, `layout.py`, `Params`). If the building is subject to control by the fire brigade, Meridiana automatically keeps at least 1 m from the edge and adds corridors between groups (see [Fire brigade](#prevenzione-incendi)).

<a id="dal-bordo-dellarea"></a>

#### From the edge of the area

A free band along the area's outline where no modules go, for maintenance and the fire brigade rules. For an activity subject to control, at least 1 m applies (DCPREV 14030/2025, 3.3.5.1, rule N15). Meridiana uses the greater of the entered value and 1 m.

<a id="tra-le-file"></a>

#### Between rows

On a pitch, modules lie flush and rows do not shade each other. The gap is an entered value for clamps and access. For tilted and ground-mounted rows the sun sets the pitch instead: see [Row pitch](#passo-delle-file).

<a id="passo-delle-file"></a>

### Row pitch

For tilted and ground-mounted rows:

- **From the sun**: the shortest pitch at which no row shades the next on the chosen day, between the sub-field's hours (see [Day and hours of the sub-field](#giorno-e-ore-del-sottocampo)). This is the default (`layout.py`, `pitch_mode`).
- **Given pitch**: a distance you choose from row to row.
- **Ground cover ratio** (GCR): the module depth across the row divided by the pitch; 0.5 by default (`layout.py`, `gcr`).

CEI 82-25/3, 6.2 gives the limiting angle, not the day. The designer chooses the day and hours.

<a id="fuori-dalle-ombre-degli-ostacoli"></a>

### Out of the obstacles' shadows

No module where parapets, equipment, chimneys, trees and other buildings cast shadows on the design day, between the site's hours: the same rule as for row pitch. When obstacles remove more than 3% of an array's irradiation (Meridiana threshold, `checks.py`, `OBSTACLE_SHADE`), Checks propose enabling it and say how many modules it costs.

<a id="le-esclusioni"></a>

## The exclusions

An Exclusion keeps modules outside its outline and extra clearance: skylights, smoke vents (EFC), openings, equipment, chimneys, trees, walkways. With a height it is also an obstacle that casts shadows. Each type's default height is indicative and must be measured on site. Smoke vents, openings and equipment on the roof automatically get an extra 1 m where the fire brigade rules apply (DCPREV 14030/2025, 3.3.5.1, rule N15).
