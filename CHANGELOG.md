# Changelog

What changed in Meridiana, version by version, the newest first. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions
are `0.x`, development releases, published on GitHub as a Windows installer
and a portable zip, signed (the installed program updates itself), and later
as a Flatpak. The same notes, shorter, are in the app's metainfo, which
software centres show.

## [Unreleased]

### Added
- New projects start from their place (R148): one field reads decimal, DMS and decimal-minute coordinates, Google Maps,
  OpenStreetMap and Apple links, UTM WGS84 or ED50 and Gauss-Boaga Roma40. Local ISTAT and recent-project suggestions
  work while typing; Nominatim is asked only by Search. Check the point and choose Create and draw. Optional grid data
  stay with the project and select CEI 0-21 or 0-16 from the supply voltage. Reserved projects never send names or
  addresses and never use Claude; map and PVGIS coordinates require separate per-project consents. Project format 16.
- Reliable maps from roofs to continents (R131, R149, R173): valid tiles stay during every change, failed sources rest
  for three minutes and a visible strip offers Retry and Choose the background without changing the saved choice;
  Automatic uses OpenStreetMap afar and the best local orthophoto within 2 screen m/pixel. The local plan zooms out to
  25,000 m/pixel, bends low-zoom tiles in matching pieces, keeps the site's hemisphere only and marks the project.
  Natural Earth 1:110m (177 countries, 209,310 compressed bytes, public domain) draws oceans, borders, names and a
  graticule below the tiles and alone offline or with no background.
- Reused Properties pages (R2): switching between objects of the same kind and shape updates only the values and keeps
  the scroll position. Unconfirmed text never leaks into the next object. On the large generated project, median
  switches fell from 57.370 to 1.773 ms between sub-fields, 24.354 to 0.843 ms between buildings and 44.541 to
  1.495 ms between coplanar sub-fields.
- Sub-field sun windows (R172): the design day and solar hours moved from Site to Sub-field, under Row pitch when it
  is computed from the sun. Each sub-field follows the project default until changed; Use for all sub-fields updates
  that default and clears individual windows in one undoable step. Layouts, shading checks and the assistant read the
  sub-field's effective window.
- Settings inside File (R133): the former Preferences window is now a page with Appearance, Navigation, Keyboard,
  Assistant, Report, Maps and Privacy. Every choice applies and is saved at once; Undo the last change and restore a
  section's defaults with an inline confirmation. Size of the text: Small, Medium or Large moves the whole type scale
  a pixel down or up, the text at 12, 13 or 14 px, at once in the open window (settings format 21).
- Dialog symbols (R169): Discard has a bin on red and Cancel an arrow going back on grey, in every dialog;
  No and Close keep the cross.
- Separate lanes for overlapping string jumps (R134): routes that share corners or segments move apart by a
  screen-constant distance where there is room, or take different vertices around the skipped modules. Where touching
  modules leave no free lane, distinct dash patterns keep the jumps distinguishable. Single and separate strings keep
  their original paths.
- Live string drawing context (R142, R181): a card in the plant's strip, where the legend was, names the inverter and
  input with its colour, counts the modules against the accepted range with the string state symbols, and shows the
  finish, undo and cancel keys; nothing covers the plan. The input is highlighted in the right panel until the draft
  ends; optimised inverters show the count without a judgement.
- Turning the plan without the menus (R174): Align and North up in the plan's bar (A and N), «Align the view to this
  side» on a right click near a side, and a click on the compass for North up; the compass's N turns with its arrow.
- Meridio can offer Undo and Redo as cards naming the history step; only the designer applies them. Project fields
  are read with the names and values shown in the Properties panel as well as the keys needed for proposals (R170).
- Inverter sizing (R141): choose the manufacturer first, remembered in the project; the model and quantity together
  follow the requested DC/AC ratio, and the result names both.
- Harmonised plan labels (R143, R138): rounded string names and module numbers in the catalogue font and the plan's
  colours, with the window's drawn check, warning and stop symbols instead of font glyphs.
- Phase-aware panels (R145): Project hides on Production, Consumption, Balance and Report, then returns on the
  graphical phases only if it was visible; the side panels share the width equally. No animation.
- Plan rotation (R146): native rotation, alignment with a side of the selected outline, and North up. The round
  compass follows the view and reports its bearing and compass point; project coordinates never change.
- Touchpad navigation (R140): pinch zoom in the plan and the 3D view, two-finger scrolling to pan, Ctrl with two
  fingers to zoom, Shift with two fingers to orbit in 3D, and native rotation where Qt supplies it. Plus and minus,
  also with Ctrl, zoom both views; matching buttons are in each view's bar.
- Power optimizers (task 22): a SolarEdge inverter, at a fixed string voltage, takes power optimizers from the
  catalogue («Optimizers…», one or two modules on each) or the ones Meridiana proposes for the module; its
  inputs are its Synergy units. The strings are proposed as few and as alike as SolarEdge's limits allow and
  checked by SolarEdge's own tables, each check with its document and page: the module on its optimizer, the
  fewest and the most optimizers, the power connected and carried by a string, the 2000 W rule, the inverter's
  maximum DC power. The year follows the architecture: no mismatch among modules alone on an optimizer, the
  shade's electrical effect optimizer by optimizer, the optimizer's weighted efficiency as a step of the chain,
  the string cut above its continuous power, the DC wiring at the fixed voltage. The strip, the report and
  Meridio say them. Six SolarEdge inverters added to the catalogue. Project format 13.
- IFC models (R91, studies 15 and 20). File > Export the model as IFC4 writes the project georeferenced (the site to
  the millionth of a second, an IfcMapConversion on WGS 84 / UTM), a storey for each building with its walls, roof
  slabs, parapets and obstacles, and every module laid as an IfcSolarDevice of a shared type with its property set
  (sub-field, row, tilt, azimuth, power, string), grouped by sub-field and by string; it runs in a job with its bar and
  Cancel, and the file is replaced only when whole. File > Import an IFC model reads an architect's model (.ifc,
  .ifczip, IFC2X3 or IFC4) for what the PV design needs only: the roofs and what stands on them, the slabs or the walls
  of a building without a roof, the site and where north is. The reading runs in a process of its own, with its bar
  and Cancel, stopped past three minutes or half the PC's memory, so a model that makes IfcOpenShell crash or loop
  never touches the window; then a dialog says where the buildings go (where the file places them around the site,
  the site moved to the model, or the site's origin), asks where north is when the map and the TrueNorth disagree,
  shows them from above and lists what is taken, approximated and left out. The buildings come in with their roofs
  recognised (flat, mono-pitch, gable or hip with their gable ends, else free pitches), the obstacles as exclusions
  with their heights, as one change that Ctrl+Z takes away. IfcOpenShell (LGPL-3.0-or-later) is an optional
  dependency, imported only when used.
- Packages (task 18f): the Windows program as a PyInstaller bundle with an Inno Setup installer for the user
  alone, which opens the `.meridiana` files and is updated over the running program; a portable zip; the
  Flatpak on the KDE runtime with the PySide BaseApp. `meridiana --self-test` checks a build without a screen
  and without touching the settings: a sample project laid, computed and reported offscreen.
- Updates: once a day at start the Windows program asks GitHub whether a newer version is out (Preferences >
  Privacy turns it off; Help > Check for updates asks at once); the installed program downloads the installer,
  checks it against GitHub's checksum and the project's minisign signature, asks to save the project and starts
  it; the portable zip opens the release page.
- Map sources beyond Italy (R36, task 21): XYZ, WMTS and WMS sources as data, each with its area, zooms, attribution
  and licence; 36 of them need no key and were tried with real tiles: Italy's national orthophoto and the open
  ones of South Tyrol, Trentino, Tuscany and Friuli Venezia Giulia, France, Spain, Portugal, the Netherlands,
  Flanders, Wallonia, Brussels, Luxembourg, Switzerland, Austria, Czechia, Poland, Slovenia, thirteen German
  Länder, the United States, Sentinel-2 cloudless 2016 for the world, OpenStreetMap, OpenTopoMap and basemap.de.
  The Background menu offers the best source for the site and those that cover it; the attribution of the one in
  use is always on the plan. Preferences > Maps lists them with their licences and takes the designer's own: an XYZ
  template, or a WMS or WMTS read from its capabilities, with its attribution and a key kept in the system's
  keyring. Settings format 19: the background «auto» and the designer's sources.
- The layout by hand (task 16c): the automatic layout makes rows as objects, and the modules have stable ids
  («row:place» with the row's id). The Row tool (L) draws a row in a sub-field with two clicks or a typed
  length, with the sub-field's module, gaps and tables, red while it goes beyond the edge band or onto an
  exclusion. A second click on a module selects its row: Delete, Move (also with the 3D gizmo), the end
  dragged to shorten or lengthen it; the menu adds a row at the back, explodes a row (or every row) into its
  modules, which keep their ids, and turns a module on its own by 90 degrees (also with a double click). The
  first gesture makes the sub-field «by hand», said in the bar; «Lay again automatically» asks first. A new
  module within 2 cm adapts the rows, a larger one asks. By hand the fire-brigade rules, the exclusions, the
  edge band and the shadows of the design day become checks. Project format 10: older files open with the
  same modules taken out and the same strings by hand.
- Move and Rotate (task 16b): on the plan a base point and a second point with the snaps, or a move typed
  («3», «3;2», Tab for the direction); R inside Move turns the selection in steps of 15 degrees (5 with Ctrl,
  90 with Shift) or by an angle typed; grips in the middle and on the outline; Ctrl held at the click, or C,
  makes a copy; the arrows nudge by 10 cm, 1 m with Shift, 1 cm with Ctrl. In the 3D view a gizmo as in
  DIALux evo: arrows East and North, the square of the plane, the ring, with a preview and a field for the
  values. A building takes its sub-fields, exclusions and free pitches with it; a sub-field turns its
  azimuth and stays on its pitch; only the layouts that change are made again; each move is one undo step.
- Gable and hip roofs on any outline (task 16a): the straight skeleton, exact, the same faces as CGAL on 306
  reference footprints; a pitch for each eave with its ridges, hips and valleys; each side an eave or a gable
  end, also clicked on the plan, the gable ends of a new roof on its arms; the ridge height sets the slope;
  the covering proposes it (35 % for tiles, ANDIL 2025 p. 7); one arm of an L shades the other. The ridges
  light up on the plan when the pointer passes. Project format 9: older files open with the same roofs on
  rectangles and a notice elsewhere.
- «Building from a template…»: rectangle, L, T, U or trapezoid with its measures, placed with a click.
- Interactive charts (study 17, D2): the value under the pointer with every series, a click on the legend
  turns a series off and on, the hourly and weekly series zoom on x (wheel, a dragged band, a double click
  to see all), the context menu saves a chart as SVG or PNG in the light theme with its title.
- Qt 6 window: plan on the orthophoto, 3D view, properties, project tree; everything undoable; adapts to
  narrow windows (niri); dark theme on Linux desktops Qt has no theme for.
- Drawing aids: guides, typed length and angle, rectangle by three clicks, Shift to keep the direction,
  Q to square a traced outline.
- Production: PVGIS typical year and horizon, the loss chain as PVsyst lays it out, shading between rows,
  PVGIS PVcalc beside the result, "How it is computed" with every formula.
- Strings and their checks of CEI 64-8/7:2024.
- Consumption of the POD with ARERA's bands, profiles, bills and measured curves; balance with storage;
  economics with the renewable energy communities of DM 414/2023.
- Product catalogue (datasheets and the CEC list) and the PDF report.
- Italian translation of the whole window.
- Obstacles with a height (chimneys, roof plant, trees, parapets, the other buildings): their shadows on the
  modules in the loss chain, with their record, and in 3D.
- The sun of the 3D view through a chosen day, played from dawn to sunset, with sharp shadows.
- The strings drawn on the plan, by inverter, input and string.
- Export limit at the injection point; the checks of CEI 0-21:2026 for the connection.
- A page of checks gathering what needs attention, each with its source.
- The user guessed from the project until the bills come; the size of the system and of the battery
  against self-consumption, self-sufficiency and net present value.
- Autosave with recovery after an unexpected stop; new revisions saved as _R01, _R02 next to the file.
- The electrical effect of the obstacles' shade, by string (Martinez-Moreno 2010), on the blocks of each
  module.
- Modules and inverters imported from PVsyst's .PAN and .OND files, with the module's own IAM profile
  joined as PVsyst joins it.
- An energy audit of the consumption: base load, load factor, average week, load duration curve; the bill
  month by month without the system and with it.
- The report lists the strings on the modules, the sizes and the checks.
- The rules that apply to the system, from Daniel's library R02: one line each among the checks, their
  paragraphs with sources in the report and in the clipboard; the connection level from CEI 0-16
  Tab. 4, the minimum renewable capacity of D.Lgs. 199/2021 for the building.
- «Fix» on the checks page applies what an item proposes, and can be undone.
- The eave of a mono-pitch roof, and the eave a gable's ridge runs along, picked by clicking the side on
  the plan; the sides of the selected outline measured on the plan and changed after drawing (a double
  click, or the properties), stretched as CAD programs do.
- The corners of the selected outline dragged on the plan, snapping to the other outlines.
- tools/compare_pvsyst.py: Meridiana beside public PVsyst reports, node by node (docs/validazione-pvsyst.md).
- PVsyst projects opened as Meridiana projects: File > Import a PVsyst project, the variants chosen, what
  was read, approximated, left out or missing said first and kept among the checks.
- When PVGIS 5.3 does not answer, the typical year and the horizon come from PVGIS 6, the service's new
  API (a beta, said in the source).
- A sub-field can keep its modules out of the obstacles' shadows on the design day, between its hours;
  the checks offer it as a fix and say how many modules it costs.
- Variants in the same project, as in PVsyst: the site is shared, each variant keeps its sub-fields,
  modules, inverter, losses and economics; compared side by side, computed in the background.
- View > Panels: the project's tree (Ctrl+B) and the properties (Ctrl+1) shown or hidden from a menu,
  «Only the drawing» (Ctrl+0, as AutoCAD's clean screen) and «Restore the default layout».
- The status bar says while the production is being computed, from any page.
- The pivot of the 3D view is a cross-hair of three rings and a dot, 16 px wide at any distance, over everything
  (study 16, G): shown while orbiting; on passing over, with the orbit's key of the mouse style held and the
  mouse moving, on the point that would become the pivot (Preferences > Navigation, «Show the pivot on passing
  over»); for a second after a middle click that recentres; always on the target when the pivot is the middle
  of the view. A pivot that left the view comes back to its middle at the same depth.
- Waits made visible (study 16, theme F): nothing under 300 ms; past it an arc where the window waits (the plan
  while the modules are laid, the energy pages while the year is computed, the catalogue at its first reading,
  which now opens at once), still with less motion; the values of the last computation greyed, with a mark after
  their phase's name, while the project has changed since; the 3D view's skeleton until its first frame; a bar
  with its percentage and Cancel in the status bar for PVGIS and the PDF report, which is written a step at a
  time and leaves no file when stopped. Never a modal window.
- Meridio opens his conversation as a speech bubble beside him, never over him, resizable from the corner
  opposite the tail, with the three questions ready numbered (1, 2, 3 send them) and «Stop» while he answers;
  he blinks, glances, follows the pointer, turns his rays slowly and makes a face now and then, all of it off
  with «less motion» or with «Meridio animated» unticked; a pixel drawing of him in Preferences > Assistant.
- Meridio has a character of his own (R106): one text of instructions for every model he talks through, the local
  one and Claude, with his name, a friendly and brief manner, «I don't know» when no tool says it, the figures
  that rest on a default or an estimate said as such, never a number guessed, the next step offered («Vuoi che te
  lo proponga?»). The first time his bubble opens he presents himself, also aloud when his voice is on; an empty
  conversation has his greeting.
- The questions ready follow the conversation (R108): after each answer two or three that make sense for what
  was just said and for the project (an offer at the end gives «Sì, proponimelo», a proposal shown «Perché
  proprio questa modifica?», the worst check open its fix, the year not computed «Che cosa manca per calcolare
  l'anno?»), made on the PC by rules, at once and with any model or none; nothing leaves the PC to make them.
- Local models made simple (R105, study 14a): Meridiana finds by itself what serves models on this PC (Ollama,
  LM Studio, llama.cpp's llama-server, Jan, Lemonade, Docker Model Runner, any OpenAI-compatible server) and
  what is installed but not running, lists their models and chooses one that calls tools well and fits the PC's
  memory, saying why. Preferences > Assistant > «Local models on this PC»: «Use it», «Search again», «Test» (a
  short question that must come back as a call of a tool); with nothing on the PC, the steps with their commands
  to copy (Ollama and the model for this PC: on 32 GB with a card of 8, `ollama pull qwen3.6:35b-a3b`). When the
  local server does not answer, Meridio looks for another and offers it in a card. With Ollama Meridiana uses its
  own API, with a context of 16.384 tokens and the reasoning off at each request (its OpenAI-compatible API stays
  at 4.096 tokens below 24 GiB of video memory and would cut his instructions). Settings version 20.
- The Checks panel (study 17, F2): the items in sections by level (TO FIX, TO CHECK, TO KNOW, PASSED closed),
  by object or by area from a menu in the head; each item one short sentence, the arrow opens its detail (why,
  and what to do, also where there is no fix); «Fix» and an eye on the row where they serve; the filters «This
  phase» and «This object», the counts in the head and in the status bar lead to the section; a view «Ready
  for delivery» with what is to fix and to check, the values still at their default and the estimates in use.
- Filters in the module catalogue: cell family (TOPCon, HJT, back contact, PERC, thin film, polycrystalline,
  monocrystalline, not stated), monofacial or bifacial, maker, power, minimum efficiency, maximum length, origin;
  the column of the family sorts by the order of the filter; the filters are kept from one opening to the next
  and "Clear filters" gives the whole list back. A module whose efficiency or size is unknown is left out of a
  filter on it, and the window says how many.
- The cell family of the 73 datasheets read is written in the file from each datasheet's own label (7 that say the
  architecture is not printed are "not stated"); the efficiency of a CEC module is worked out from power and size
  where the list has its size, and the card says so.
- tools/update_cec.py rebuilds the CEC list of modules from NREL's "CEC Modules.csv" (21,640 modules, list
  2026.7.3 of 23 June 2026, 5,669 with their size, version and date on every record).
- A typical bifaciality for bifacial PERC (70 %), TOPCon and HJT (80 %) modules whose datasheet gives none,
  kept apart from the datasheet's value and shown on the card as an estimate.
- Help next to things (R24): a help box at the foot of the right panel, in every phase, says what the field
  of the panel with the keyboard or the result tile under the pointer means, in three lines with its source
  and the links to the manual, to "How it is computed" at its step and to Meridio with the question written;
  it folds and stays folded, and in a panel lower than 480 px the «?» open the same text as a pop-up. A «?»
  beside the titles of the groups and the pages of the properties and in each result tile; Help > Help on
  this field (F1), What's this? (Shift+F1) and Manual, the manual (docs/manuale, a chapter per phase) read
  inside the program at the right heading.
- The Plant phase (task 16d): several inverters, each with how many, from the catalogue or a .OND file, in
  the right panel with their inputs and strings; a sub-field sent to an inverter and an input; «Size it by
  itself» takes as many alike as the DC/AC ratio asks; Production keeps a reference with «Go to the Plant».
- The strings proposed with PVsyst's strategies (back and forth, one row per string, U on two rows, one row
  per MPPT), identical on an input and spread as PVsyst does (10 strings on 3 MPPT: 3 + 3 + 4).
- Stringing by hand (R12): a floating panel for each inverter with its inputs, the strings each takes and
  their state; clicks and drags on the modules, the right click takes one out, a drag from a string's end
  lengthens it, Esc closes it, every gesture undone one by one; «Redo automatically» asks first.
- A tint for each string from the colour chosen, the traffic light (correct, to be checked, out of the window
  or without input) and the red outline of the modules in no string, with a legend.
- The checks of the strings at each gesture, at PVsyst's design conditions (60, 20 and -10 °C) until the
  year is computed; for each inverter the DC/AC ratio, the energy lost beyond its nominal power and the
  balance of its inputs; the report lists the strings by inverter and input with their modules.

### Changed
- The strings are the designer's (task 23; R114-R119, Daniel's usage of 25/10/2026): nothing makes or rewrites them by
  itself any longer. «Propose the strings» (with PVsyst's strategies in its menu) and «Complete the strings» (only the
  modules in no string, on the free inputs first, the designer's strings kept) run once when asked, each one undo
  step, Propose asking first over existing strings; «Delete all the strings» asks first; «Redo» is gone. An inverter
  added leaves its inputs free and the strings stay on their inverters when the numbering changes. A string drawn by
  hand: «+» on an input of the list or «Draw», clicks or a drag over the modules with the order numbered on them,
  Backspace, Enter or a double click, Esc; a module of another string refused with the reason, Shift moves it; its
  modules against the input's range in the strip while drawing. On the plan a string's modules are filled with its
  colour, the line never passes over a module that is not its own: a skip goes round the skipped modules along their
  edges, dashed (string_paths.py), so a module skipped is seen; strings side by side or in the next row never share a colour,
  and a string keeps its colour when another is deleted; names that
  would overlap are hidden when zoomed out. The list of the strings in the right panel chooses a string and frames
  it, Del deletes it, a double click draws it again, the right button has its menu, «+» is the design system's tool
  button with Lucide's plus. The inverter cards over the plan are gone: the whole plant is managed in the right
  panel. Project format 14: an older project's automatic strings are written down as the designer's at its first
  layout, the same strings, without an undo step and without asking to save; a PVsyst import keeps its counts the
  same way.
- Every text of the window is one of ten named styles (R121; docs/design/sistema-grafico.md): six sizes (11, 12,
  13, 14, 18, 22) and two weights, each with its colour, on the text at 13 px (R123). The tabs (phases, charts,
  panels put together, Preferences), the pills and the buttons at the text's 13 px (the tabs were 15); the cards'
  titles at 14 semibold, the groups', the rows' and the buttons' words at 13 semibold; the status bar, the notes
  and the plan's labels at 12; the bold of the rich text, of the manual and of Meridio's answers is the semibold.
  The project's tree, the Checks, every list, menu, tooltip and message box were in Windows' Segoe UI at 12 px (Qt
  gave them the platform's font back when the style was set): now in Inter like the rest. The headings of the
  manual and of the release notes in the catalogue's sizes.
- Every button and field is 28 px high (the buttons were 25, the number and date fields 30); chips, pills and tabs
  24, the small buttons of rows and titles 20 (design.Button).
- The tabs of every bar look like the pills of the panels put together; the Checks' chips and counts are rules of
  the global sheet; the counts of the status bar carry the drawn marks.
- Less accent (R104): the selection, the tools on, the chosen tabs and pills are a grey that leans to the accent's
  hue; the key tile, the rows' «Fix», the view bar's and the cube's hover, the waiting arc and the help's links no
  longer in the accent; the File button is full of accent only while its page is open.
- The scroll bars keep their room (R100): a thin thumb of 6 px in a room of 10 px that every list, form and text
  keeps whether it scrolls or not, so nothing moves when a bar comes or goes (the window resized, a panel narrower).
- M is Move and Measure is D (study 16, B): the settings move a Measure kept on M to D (settings version 14).
- Meridio's face is lighter in the light theme (the disc at a lightness of 0,80; it was 0,58, too dark).
- The charts of the window are drawn by pyqtgraph (a new dependency, MIT): 6-7 ms at the pointer on a year
  of hours where matplotlib redrew in 150-190 ms; «Table» stays; the PDF report keeps matplotlib.
- The lists of the properties no longer repeat their choice in a tooltip; "Out of the obstacles' shadows"
  and "Between rows" say what they do in a phrase under them.
- The look of the window (study 17, A3 and C2): three floors apart, the panels as rounded cards with the
  title inside, the phases' pages and the views rounded, buttons and fields tonal with a readable border, one
  button full of accent per page, groups with a frame and a filled header, the result tiles as cards with the
  key number in the accent's tint; the project's tree and the Checks panel with sections («BUILDINGS · 2»)
  and the marks as pills; thicker strokes on the plan and in 3D.
- The window answers while a computation comes back: the formulas of «How it is computed» are drawn once
  and kept, charts and formulas are drawn when they come on screen. The freeze after each change went from
  2-3 s to 0.05-0.25 s (docs/studio/12-revisione-ux-prestazioni.md).
- The production is computed about twice as fast: the modules' maximum power point over the whole year at
  once (pvlib's chandrupatla), the same power within 1e-13 W.
- The plan is not repainted at each move of the pointer while selecting (60-70 ms a move with 4,700
  modules); the list of checks opens without the second it took at start.
- Plan alone and 3D alone on Ctrl+Shift+2 and Ctrl+Shift+3, pressed again side by side; F2, F3 and F4 are
  free (rename, AutoCAD's snaps, the F keys of laptops).
- The wheel scrolls the forms: a number or a list changes with the wheel only once it has the keyboard
  (a click). Before, it changed the field under the pointer, and stopped the scrolling there.
- The arrows of a field clicked again and again make one undo step, and the modules are laid once.
- A change is followed only by what reads it: a building renamed lays out nothing and computes no year
  (36 ms instead of 328 on twenty buildings); a height lays out again only the sub-fields of that building.
- The project file (format 7) keeps every variant with its design, the one in hand too; a setting the
  program does not know is said with its path when the file is opened.
- The undo stack keeps 200 steps; a change that fails leaves the project as it was.
- The project file is at format 8: the inverters as a list and the strings as objects; a file of before
  opens with its inverter as the first of the list and gives the same year.

### Fixed
- A click on a building's wall in 3D selects the building (R175): the point hit lies on the outline, often just
  outside it, and the plan found nothing there.
- The calendar's month bar was cut at the top by the little window's corners (R176).
- What scrolls in a page (Balance and the other phases) stopped on the card's line (R177): it now stops a little
  short of it and fades out whole before it.
- The words under the tools were cut at the bottom with the larger text (R179): the buttons take the height they ask.
- The string legend in the plant's strip is gone (R181): the plan's colours already say what it said.
- Scroll bars sit the same in every page, close to the card's right edge, and the thumb stays off the rounded
  corners (R182).
- Meridio's checks distinguish filtered from project counts and filter by object. Obstacle shade is aggregated over
  all the arrays of a sub-field, its irradiance basis is explicit, solar hours are clock times, and the proposed fix
  states its module cost and when that cost exceeds the shade loss (R170).
- Selecting modules and rows on a touchpad (R147): the plan takes the nearest module within 6 logical pixels of its
  edge, the second click selects its row in both views, and Esc goes back through the selection levels.
- The checks said that the modules in no string produce nothing in the simulation: they are counted as if connected;
  the detail now says so, and that in the real plant they produce nothing.
- A change that lays out nothing again (a string) no longer covers the bar's message with «N modules laid».
- The Balance's data went past the right edge of their card: a group's long title widened the column («Energia
  acquistata (tutti i costi variabili, imposte comprese)») and the battery's two buttons side by side made the form
  wider than the card. A group's title is shortened now, and those buttons (and the inverter's in the Production)
  stand one under the other.
- A value typed halfway in the properties went into the project when a layout came back and rebuilt the
  panel ("0,07" saved as 0).
- A closed panel could be opened again only from the right-click menu of the toolbar.
- A row could stay empty in a sub-field drawn at an angle: the front edge, rotated, left a sliver that
  forbade the whole row.
- The row in front hid too little sky: Passias' formula, with the masking angle from the horizontal, gave
  0.9% where the row's view factor gives 4.5% (PVsyst's scene 4.4%). The view factor is used now, and the
  light reflected by the ground is lost too, as pvlib's infinite sheds compute it. Found by comparing with
  PVsyst reports.
- The design day and hours set for the site did not reach the row pitch: the default ones were used.
- A table of two or more modules across counted one module per column.
- Typing a value in the properties and pressing Enter could bring the program down.
- The third click of a small rectangle could give it no depth.
- The 3D view lost its sun to Qt Quick 3D's limit of four directional lights; its shadows were a faint
  smudge (settings made for centimetres in a scene in metres).

## [0.1.0] - 2026-10-21

### Added
- The skeleton of the author's app template, before Meridiana (a sample
  window that counted the files of a folder). Never published: the first
  release of Meridiana itself will be 0.2.0.

[Unreleased]: https://github.com/daniel-g-carrasco/meridiana/commits/main
