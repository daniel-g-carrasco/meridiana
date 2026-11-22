# Changelog

What changed in Meridiana, version by version, the newest first. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions
are `0.x`, development releases, published on GitHub as a signed Windows
installer (the installed program updates itself), and later as a Flatpak. The same notes, shorter, are in the app's metainfo, which
software centres show.

## [Unreleased]

### Added
- Optional gesture traces include the display refresh rate and the 3D camera. Camera snapshots stay on the GUI
  thread; the render thread records timing data without reading QML properties.
- Meridiana has its own icon: a blue half disc, a red gnomon standing on it and a small yellow sun, on the
  ivory square of the family; a drawing of its own for 16-24 pixels on Windows.

- Full English manual alongside the Italian edition, using the interface's command names. Meridio reads the
  program's language with Italian fallback for missing sections. Both editions ship with Windows and Flatpak;
  tests keep their structure, anchors, command explanations and interface terminology aligned.
- Full screen: View > Full screen, F11 by default (changeable in Settings > Keyboard), puts the window over the whole
  screen and F11 again takes it back as it was, maximized or at its place and size; the menu shows it on. Esc does
  not leave it, and a start is never full screen.
- Project-specific regulatory profiles, saved with an explicit timezone in project format 31. Existing projects
  retain the Italian profile and Europe/Rome timezone.
- An obstacle can stand above the roof or the ground: «Base height» in its properties (project format 32), for a
  duct on supports or a pipe rack. It casts its shadow from its base to its top (the sun passes under it), the 3D
  view, the IFC and the DXF show it there, the plan draws its outline dashed; the modules stay out of its outline as
  before. Projects without one open, compute and save as they did.
- An imported model's node in the Project tree can be renamed like a building (menu, F2, the Name field of its
  properties); the name is saved in the project (format 33) and used wherever the model is named. Inside the node
  only the bodies with a sub-field of yours or with room for at least 7 modules of the project are listed; the
  others are in «Other bodies».
- «Fill all» on the Checks row that stands for several sub-fields without modules: one change, one undo step.
- A minimal generic IEC calculation scope for declared equipment, manual strings, consumption and prices.
  Reports and assistance state that local obligations and regulatory conformity are not assessed; national
  incentives and automatic electrical sizing are unavailable in this scope.
- A new sign of North, the same in the plan, the 3D view and the report: a two-tone needle, its North half full. In
  the plan it is smaller than the old disc and says nothing while North is up; turned, the degrees stand under it on
  their own ground and a click brings North up again. The 3D view shows it under the view cube, turned with the
  camera; a click looks North. The report prints it 12 mm tall in black, with the «N» over its tip.

### Fixed

- Zooming the plan no longer loses resolution: the drawing under the fingers is drawn again as the zoom
  proceeds, instead of one picture stretched up to four times. Deep zooms on plants of thousands of modules
  have far fewer stalls; dashed sub-field outlines are real dashes near the modules, not a ragged line that
  took seconds to build.
- A pause while zooming the plan in and out no longer stops the window for half a second: the names of the
  strings keep their pills, and the strings' drawing for a new scale is prepared in the background and kept
  for the scales already seen, within the memory setting (Settings > Performance).
- Zooming near the modules of a large plant, the plan draws only the part in view, and its signals no longer
  lay the names of the strings out again when nothing changed: the longest stops while zooming in and out
  are about half as long.
- Zooming the plan no longer rebuilds the drawing of the strings at each change of scale: lines, fills, dots
  and names stay as they are, and only the arrowheads and the numbers follow the zoom. With the wheel, on a
  plant of 2000 modules, the stops while zooming in and out near the modules are almost gone.
- The window answers more readily while the program computes in the background: the keys of the text fields
  are now watched on the field being edited, not on every event of the program.
- The plan shows what can be read at each zoom: from far the modules lose their outlines and are drawn a row
  at a time, the colours of the strings fade out, the strings' lines come from the scale where they can be
  followed and a dot on every module only near the modules. Zooming across a plant of ten thousand modules
  is about twice as smooth.
- From far, the strings' names give way to one label for each inverter, in the middle of its strings: how many
  strings it has, or how many are to check, and their state.
- The corners and the side measures of what is selected show only while it is large enough on screen to read
  and to take them: no more heap of points and labels over a building of a few pixels.
- Il cambio di fase dissolve soltanto i contenuti: schede, bordi e fondo della barra restano in vista.
  Pianta, 3D e albero condivisi conservano il loro stato; i popup della fase uscente si chiudono.
  Con movimento ridotto il cambio è immediato. Il velo di File e Impostazioni resta invariato.

- A check's mark on the plan or in the 3D view shows the hand under the pointer and says the words of its checks in a
  tooltip; a click selects what it marks and shows its checks. In the 3D view the marks took no pointer at all.
- A split button of the bar with its tool on («Measure», «Building», «Pitch») is lit whole, no longer its first half
  alone, in two tones: the tool's half pressed, the arrow's half a step less, the change of tone the divider. Under
  the pointer the tool's half goes darker and the arrow's half rises over the tool's; with its menu open, more.
- Meridio is there over File and the Settings too: the status bar's «Meridio», «Ask Meridio» in a help bubble and
  Meridio taking you to a setting now open his conversation there (they did nothing before); he lights the setting
  he takes you to, says which page you are on and has questions ready for File and the Settings. Docked, he floats
  while File is open. A page fading in no longer makes him blink.
- While Meridio works on an answer, a short line in the place of the answer says what he is doing («Thinking…»,
  «Reading the checks…»), with a soft glint running across it; the first words take its place without moving the
  page. It replaces the three dots of the status line, which stepped and stalled.
- Meridio's answers no longer carry his name over each (27 px a one-line answer), nor do your messages carry «You»
  (27 px each); screen readers still say who speaks.
- Meridio's field no longer shows its scroll bar when its text fits: with some fonts and text sizes a written
  line is a pixel taller than the font's metrics say, and the field thought it had something to scroll.
- Meridio is a little larger (50 px, was 46) and the white border of his sticker look a little wider (3.0 px, was
  2.6). His size has one source, which the window and his drawing read.
- In a narrow window the column of the pages of File and of the Settings gives Meridio his room on its right, as
  long as it stays a reading column wide (440 px); narrower, he may stand over its edge.
- Meridio answers in the program's language: with the program in English nothing of what he is told is Italian but
  the quotations (the manual, the laws), which are marked as such with the language to answer in, and the rule is
  said again at the end of his instructions and with each question. His voice reads a text in its own language
  (Italian with the Italian voice, English with the English one), whatever the program's.
- Over File and the Settings Meridio stands on the free side of the page, right of its column, instead of over its
  words; back in the project he is where he was, and docked he is the panels' tab again. The «–» of his bubble only
  hides him: with Meridio low on the right of the window it could be taken by the bubble's resize grip and do
  nothing.
- Meridio's bubble: while its corner is dragged, its words, buttons and field follow the new size at every point,
  not only at the release; only the messages in view are laid out during the gesture, the others at the release. The
  corner's grip no longer keeps its cursor and its clicks over the whole bubble after a resize.
- The status bar's «Meridio» (and Ctrl+L) always brings Meridio back in view, inside the window and over the rest,
  also when the Settings had turned him off. Docked with his conversation open, hiding the right side (or every card)
  no longer leaves him nowhere: he floats until his side comes back.
- Meridio's bubble: no more «Binding loop» warnings in the log while the guided tour moves him.
- Plan and 3D view: the bars over a view stay over the drawing. On the plan the strings' names and discs passed
  over the pointer's coordinates, and the side highlighted from the properties over every bar; in the 3D view the
  checks' marks passed over the view cube and the tools. What stands over what is now one scale of the theme.
- Windows (dialogs): a window taller than the room left by the main window no longer runs out of its frame. Its
  content scrolls inside it, fading at the edges, while its title and its buttons stay where they are, at every size
  of the main window. The windows of File (Import an IFC model, New project, Site, the models, Shortcuts, Update,
  Report a problem, About) are now the same window as all the others, with their title and buttons in the same
  places.
- Windows (dialogs) can be moved by dragging their title. They stop at the edges of the main window and open again
  in the middle.
- While a window is open the title bar of the main window is shaded too, as the rest of the window, on Windows 11 and
  on Linux under Wayland where the program colours the bar itself. Windows 10 and the title bars drawn by the system
  (X11, server-side decorations) stay as they are.
- Measure: a second measure no longer starts from the first one. After a measure the dashed guide still left from
  its first point, followed the pointer and pulled the next click on to it, and that click showed nothing at all.
  Now the measure made stays until the next click, which starts a new one exactly where it is given (corners,
  midpoints and edges still snap), and the points of a measure are marked. Shift held between two measures no
  longer moves the start of the second.
- Every page of File and of the Settings stops at the same width, 760 px after its margin, as the Settings already
  did: on a wide window the recent projects, the tiles and the pages of New project and Clients and jobs no longer
  stretch across the whole window.
- What scrolls in a panel, a page or a list fades out right up to the edge of its box from the first step of the
  wheel: a line cut by the edge stood bare until the content had moved by the height of the fade, and pages stopped
  their text 6 px under a section's heading, leaving a sharp cut there. The project tree and the checks use the same
  fade as everything else.
- Arrows have two meanings, each drawn one way everywhere: a full grey arrow where a value is chosen (drop-down
  lists, buttons with a menu, submenus, the steps of a number, the order of a table column), drawn on whole pixels so
  it is sharp at every display scale (the arrow of drop-down lists was blurred), and the open arrow of the project
  tree, with its line, where a section or a group opens and closes (the checks, the groups of the panels, the
  catalogue, the trees and Meridio had thinner ones).
- The text of every input box stands in the middle of the box at every text size: the hint of an empty box (the
  address in New project, the search in Clients and jobs) sat higher than the text of a filled one, the unit of a
  number was not on the number's line, and numbers and drop-down lists started their text 2 px before text boxes.
- IFC import: the glazing of a shed or a lantern modelled as a sloping curtain wall becomes part of the roof, as a
  glazed roof already did, so the shed casts its shadow as one volume. Its mullions are no longer obstacles: each
  one stood as a wall from the roof to its top (up to 4 m for a mullion of 5 cm), taking a strip of modules and
  casting the shadow of a wall. Upright curtain walls, chimneys and parapets on a roof stay obstacles. A project
  imported before keeps its obstacles until the model is imported again.
- IFC import: a window or a wall in the facade of a taller body, above a lower roof in front of it, is no longer an
  obstacle of that lower roof when the taller body's roof stops short of its facade (three windows of one model
  stood as walls of 5.6 m); the taller body casts that shadow. Reimport the model to apply it.
- An IFC reading that runs past its three minutes stops at once and says what to export instead, without a second
  reading of the simple shapes that could not end either and only made the wait longer; the second reading stays
  after a crash of the reader. The model's 3D geometry is kept in the cache of the session's profile, like the other
  caches.
- Reading a large IFC model is about twice as fast (one model of 91 MB: from 120-170 s to 70-95 s), so it no
  longer runs past the three minutes allowed and ends with «the reading took more than 60 s and was stopped» at the
  first import; the window stays freer while it reads, an edge dragged just after opening such a project follows
  the pointer, and a crash of the program itself now leaves its trace in `fatal.log` next to the log.
- An imported IFC model's true geometry in the 3D view has its openings and its cuts: walls were drawn whole across
  their windows and doors, walls under a sloping or saw-tooth roof as full rectangles instead of following it, and
  steel members past the cut at their ends (on one model met, the walls beside the inclined glazing of a saw-tooth
  roof; on another, some 250 walls and members, 88 of them sticking out by up to 21 m). Cuts by half spaces, plain
  or bounded by an outline, and openings of any extruded or convex shape are made; the few cut by other solids are
  drawn as before. A model imported before keeps its old drawing until it is imported again.
- With an imported IFC model shown in the 3D view, the placement planes the import offers on its roofs are no longer
  drawn over the model's own roof, where the two flickered in jagged stripes; the planes stay selectable and their
  modules are drawn. Placement planes the designer adds are drawn as before.
- With an imported IFC model shown in the 3D view, the obstacles read from it are no longer drawn as upright prisms
  over the model: a sloping mullion of a saw-tooth glazing showed as a full wall several metres high. The obstacles
  stay in the layout and the calculations and remain selectable; obstacles the designer adds are drawn as before.

- Installing from source asks for Shapely 2.1 or later (it accepted 2.0, with which reading an IFC model stopped on
  a missing function); the Windows and Flatpak recipes ask for the same.
- An IFC roof whose planes come as many faces, in a model placed in national grid coordinates (millions of metres
  from the file's origin), comes in as its planes again: each triangle stood alone, so the roof showed lines fanning
  out from one corner in plan and in the import's preview, the narrow ones were left out, and a sub-field on one
  of them laid few modules or none (on the model met: the main roof's 158 pieces are now 127, its largest plane one
  pitch of 756 m2 with 204 modules where its slivers laid 0 to 71).
- Placing a large IFC model holds the window for less: the 3D view of a large project is made in the background
  after a change (the status bar says «Drawing the 3D view…» past a moment, the view before stays until then), the
  model's true geometry is read while it is being placed rather than after the click, and the model laid is selected
  once instead of twice. On the model met the longest wait after the click went from about 2 s to about 1.2 s.
- A building imported with a great many hand-drawn pitches or sides (158 pitches on 191 sides in the case met) no
  longer freezes the window a few seconds after the project opens, nor when it is chosen: beyond 12 pitches or 24 sides
  Properties says how many there are instead of listing them one by one.
- An imported IFC model's true geometry is drawn on its buildings in the 3D view: it was drawn about the scene's
  origin (26.5 m off and 8.1 m low on a real model), and its zero is now the ground floor in the model's own heights,
  not the storeys' Elevation attribute (which would have lifted it 84 m once placed). The import says the zero it
  took. Projects imported before open right without a new import; bodies made of the model's solids need one.
- An imported IFC model's true geometry no longer vanishes from the 3D view after the first change (an obstacle's
  height, a building moved, the modules laid): its pieces stay for as long as the same model is shown.
- An imported IFC model's true geometry no longer shows surfaces that are not in the file: faces shaped as an L or
  with a courtyard are closed inside their outline, holes (window frames, openings in a face) stay open, and an arc
  of a profile stays an arc instead of becoming its whole circle (a road's curve had become a disc 5.5 km wide). A
  model imported before keeps its old geometry until it is imported again.
- An IFC model's terrain (a toposolid, a C-TOPO layer, a «Terreno» material) is recognised: it no longer becomes an
  obstacle «tree» over the whole lawn, nor a body when the model's solids are taken, nor a shadow, and it is left out
  of the 3D and of its framing; the import offers to draw it in the 3D, off at first. Projects imported before are
  unchanged.
- An obstacle read from an IFC model has its element's plan: a wall in U or a railing around a roof keeps the
  modules out of itself only, instead of the whole convex area it encloses (a ring is cut in two pieces), and the
  windows and panels of a higher body's facade are no longer «poles» about 11 m tall on the lower roof beside it.
- On the plan the strings' names and discs no longer pass over the view bar, the compass, the scale and the notices;
  in a string's name the coloured dot stands in the centre of the round end, as the state's disc at the other end.
- On the plan the lines of the strings are no longer cut by the outline of a chosen sub-field: the outlines of what is
  chosen or under the pointer lie over the strings' fills and under their lines.

### Changed
- Meridio has smaller symmetric side flaps and rounder tips, and always uses the sticker appearance with a white
  border, including the status-bar icon. The drawing selector is removed from Settings; existing profiles migrate
  automatically.

- Meridio's field takes a longer message on many lines: Shift+Return breaks the line, Return sends. It grows by whole
  lines up to six, never past a third of the conversation, then its text scrolls inside it; after the send it is one
  line again. The wheel over it scrolls its text when it has some to scroll, else the conversation.
- Meridio's ready questions are gone (the rows under the conversation, their button and the keys 1, 2, 3): the
  conversation takes their room.
- The Project tree lists the sub-fields and the exclusions under their building, with the sub-fields and kWp of each
  building; buildings and groups close and open (arrow, click, Right and Left keys) and are remembered for each project
  in the user's settings; a selection made on the plan or in the 3D view opens its groups; names come in their natural
  order («Lastra 2» before «Lastra 10»). A project of 2 000 sub-fields shows the rows of its buildings only.

### Icon, 2026-11-17

- Meridiana has its own icon: on the square canvas shared by the apps of the same family, a blue half disc, a red gnomon
  standing on it and a small yellow sun at its tip, light on the left and shadow on the right. The symbolic icon, the
  drawing for 16-24 px and the Inkscape master (`docs/design/meridiana-icona.svg`) come with it. The canvas stands 480 of 512, as the family's disc with its thickness. On Windows the icon
  reaches the edge of its square, as the other programs' icons do in the taskbar; on Linux it keeps the theme's margin.

## [0.2.1] - 2026-11-09

### Catalogue, 2026-11-09

- Three products added from their official datasheets: the Sungrow SG150CX (V7) and SG15RT-P2 (V2) inverters and the
  Eurener MEPV NEXA DG bifacial glass-glass module, with its 480, 490 and 500 W classes (Italian sheet itagcg, 2026-06).

## [0.2.0] - 2026-11-09

The first release of Meridiana: everything below this line, with the Qt Quick window as the program's own.

### The Windows package of the Qt Quick window, 2026-11-09

- The Windows installer opens the Qt Quick window, with its QML, Quick 3D, the 3D props, Meridio and every module of
  the program; the window's workers (the computation, the tasks, the report) run as `Meridiana.exe -m ...`.
- The Qt Quick window speaks the language of Settings (the desktop's by default): English on an English Windows,
  its computation and its report too; the 3D view's menus, cube and sun bar no longer had Italian sources.
- The installed program checks for a newer version by itself once a day (Settings > Privacy), says it in the status
  bar, and Help > Check for updates downloads it, verifies its SHA-256 and its minisign signature, installs it for
  the user and starts the program again.
- Without a project on the command line the window opens an empty project (the sample of a checkout is not there).
- The installer speaks English unless Windows speaks Italian.

### Recovered from branches never merged, 2026-11-07

- R386: the cloud chat test initializes the optional cloud SDK before timing the fake answers and drains the
  window's workers before disposal; it fell 3 times in 6 offscreen, now 6 in 6 pass.
- R390, R391: new settings start with IBM Plex Sans, grey backgrounds and the indigo colour (Daniel, 04/11/2026).
  Saved settings keep what they have: every saved file has the three keys since format 3 (colours) and 26 (font),
  and the older formats keep Bronze, Meridiana's backgrounds and Inter through their migrations. No new format.

### The new technical report, 2026-11-06

- The report has the look of draft A5 of its study (R460): IBM Plex Sans Light, square tables with a grey head,
  a vertical scale of 6 pt, the cover with the plant's 3D view and the data in a column, the logo on the left of
  every header, «Contents» on two levels on a page of its own, justified text with Italian hyphenation. Its own
  warm greys, without blue: the profile's colour no longer reaches it. Charts in taupe and sand, the losses hatched.
- Results in boxes at the head of the summary and of the chapters of calculation; a 3D view in the shading section.
- Every step of a calculation with its formula on a line of its own and numbered, «where:» and the symbols with the
  digits on the decimal comma, the values put in on a line of their own and the result in evidence; the same layout
  in the Quick window's «How it is computed».
- The report can be exported as an editable ODT or DOCX (both windows): the same content, real styles, a contents
  that updates, the formulas editable (LibreOffice Math, Word equations), the fonts embedded.
- A project without modules says there is no plant to report on, instead of stopping on «cannot divide by zero»
  (R459).

### BIM import, 2026-11-05

- The project's site never moves by itself: a model comes in at the middle of the plan, a place in the file is only a
  proposal, with its distance, and only when it can be trusted. A site called «Default» is not believed.
- A roof of several levels comes in as bodies that meet, moved and turned as one (`Building.group`, format 26); slabs under
  the open sky on walls are roofs; beams and walls under a slope are no obstacles, which also removes false shadows.
- Walls rise to the roof wherever it bends and never above it; steps between pitches are closed (R408).
- A new import window in Quick, a Revit file says its version and what to do (study 32); dialogs take the height of their
  content, with one margin all round (R403). Ctrl+Z works in Modelling.
- `tools/ifc_banco.py`: reads and checks a private collection of models.

### Quick assistant integration, 2026-11-04

- Connect Meridio's conversation, attachments, provider setup, contextual help and guided tour to the live Quick session.
- Keep the character and bubble together during dragging, preserve the tail while resizing, and return from contextual help with Esc.
- Verify the port with synthetic providers, real Qt gestures and Widgets/Quick captures. The existing Widgets application is unchanged.
### Quick inspectors, 2026-11-05
- Connect complete Properties, Checks and Project panels to the Quick workbench's session.
  Match field inventories, grouped checks, correction previews, tree menus and undo with Widgets.
- Keep inspector content visible through selection changes; match section help, count pills,
  wrapped filter headers, continuous row cards and scrolling fades.

### Fire prevention activities and Meridio's answers, 2026-11-02

- Carry Annex I of DPR 151/2011 as data (the 80 activities, thresholds and categories, GU no. 221 of 22/09/2011).
  Choose the activity in the building's properties, by number or words; project format 24, older files stay valid
  with the activity not specified. Rule N13 cites the activity and its category.
- Meridio quotes thresholds and laws only from the sources the program carries and says which document is missing,
  answers first and then gives the grounds and the project data; the tool for the rules gives their whole text,
  a new tool searches the activities.

### Services and catalogues, 2026-10-29

- Optional signed updates, with a consent that can be withdrawn and protection of unsaved changes.
- Local PDF and text attachments in Meridio, a review of the products and a personal catalogue with comparison.
- AC and DC storage in Plant, with exact compatibility and documented limits; a structural audit of the catalogue.
- A guided tour that can be resumed, and draft reports of problems from the window and from the chat, never sent automatically.
- The graphical self-test fixed so that it shows the 3D view in narrow windows too.

### Electrical completion, 2026-10-29

- Compute connected strings from sampled cell-cohort I/V curves, bypass sections and shared MPPT operating
  points; enforce documented optimizer limits and calculate conversion and clipping per physical inverter.
  Missing topology, inferred cell geometry and unsupported architectures remain explicit modelling limits.
- Search inverter and string assignments across electrical constraints with a shared budget and cancellation;
  distinguish an incomplete search from proven infeasibility. Propose and Complete run outside the GUI thread.
- Edit physical single/dual optimizer groups, preserve them during string edits and save them in project schema 20.
  Model conditional MPPT limits separately from connector and whole-inverter current ratings.
- Include inverter DC/AC columns in hourly CSV and the corresponding annual report table. Quote arbitrary inverter
  names correctly in CSV. Keep selected hardware when applying a proposal that only changes wiring.
- Share item-view checkbox styling with the Qt template; verify Windows popup geometry and native graphics,
  and fix isolated installer checks so that deselected associations and shortcuts leave no unwanted entries.

### Added
- Shared Qt refinements from the updated template: uniform table selection, protected corners, continuous headers
  and final-row separators; compact phase navigation that skips hidden phases; native checkbox variant A with an
  unclipped focus ring; distinct row/title help controls and theme-aware File tile icons. Application-specific
  delegates, navigation trees, variants and scrolling-fade settings are preserved.
- Shared scrolling fades, growing wrapped labels and checkbox-gated sections (R192, R193, R194): a short, clear fade
  keeps content off card borders, form rows follow their labels in every theme and text size, and the CER, automatic
  LID and azimuth fields explain why they are disabled without losing their values.
- Save feedback and autonomous site climate (R195, R196): the status bar reports manual and automatic saves with their
  time. PVGIS's typical year and horizon download in the background on opening or after a site change when missing,
  without starting an energy year; they are stored inside the project file and refresh only after a move over 250 m,
  a database change or an explicit request.
- Meridio's polished bubble and immediate proposals (R197): his name stays opposite the resize grip, response options
  use the program's buttons and hover only between turns, and the model shows the proposal card at once instead of
  asking permission first.
- Touchpad, Space and the whole Equal Earth world (R189, R190, R191): an optional JSON Lines log records raw plan
  and 3D input events for diagnosis on Windows. Precision angle deltas and Wayland pixel deltas pan smoothly on both
  axes, native or Ctrl-wheel pinch zooms around the cursor, and touchpad rotation is off. Space follows the mouse
  with or without a button and ignores Windows auto-repeat releases. Beyond regional scale the plan becomes an
  Equal Earth map centred on the site, with every country offline, then returns to the local tiles.
- Inverter sizing and clear MPPT inputs (R187, R188): models of different powers from one brand are combined only
  when every module has a valid string, choosing fewer inverters, then fewer models, then the closest DC/AC ratio.
  Impossible counts explain the smallest module correction. Every input shows its series range, parallel limit,
  power and state; the plus draws equal parallel strings, with current and orientation checks.
- Reliable maps from roofs to the whole world (R131, R149, R173): valid tiles stay during every change, failed
  sources rest for three minutes and a visible strip offers Retry and Choose the background without changing the saved
  choice; Automatic uses OpenStreetMap afar and the best local orthophoto within 2 screen m/pixel. Low-zoom tiles bend
  in matching pieces. Beyond regional scale Natural Earth 1:110m (177 countries, 209,310 compressed bytes, public
  domain) draws the whole Equal Earth world with non-overlapping names and the project mark; the maximum zoom fits
  the viewport and zooming back restores the local plan.
- Meridio finds and opens local projects and remembers tasks (R151): a background index covers only linked job folders,
  with lexical and structured search, latest valid revisions and explained similar projects. Opening always shows path
  and revision and uses the normal unsaved-changes confirmation. Local tasks have due dates and are created or completed
  only after a click. Cloud providers receive no index, names, paths or job codes, never reserved rows, only filtered
  aliases; questions about reserved work stay local. Registry schema 3.
- Clients and jobs in the window (R150): File > Clients and jobs offers three columns for clients, jobs and details,
  with inline creation. New projects choose their client and job in the optional data; the client reaches the report,
  and a reserved job stops online search and tiles as soon as it is selected. Project format 18 carries job and series
  identity, so saving R02 and reopening R01 keeps the same link. Damaged registries open a warned temporary fallback.
- Local client and job registry (R150): SQLite stores clients, jobs, project series and linked folders with stable
  ids, textual five-digit job codes, foreign keys and a versioned schema. Immediate transactions, WAL and full
  synchronisation protect writes; a consistent .bak database is refreshed after every committed change.
- Folder manifests and registry exchange (R150): a linked folder writes .meridiana-commessa.json only after its own
  consent, revoking removes it and reserved jobs never have one. Folder consents stay local and never travel in the
  JSON exchange. Export and import show a preview, merge records by stable id, leave unrelated records in place and
  refuse conflicting codes, paths or malformed fields without partial writes. Folder failures are named and retried.
- Self-contained project files (R150): custom modules, inverters and optimizers already travel in the file; report
  attachments, the selected author's profile and logo, and the site's weather and horizon are now embedded too.
  Opening on another PC needs no catalogue, profile or weather cache. Missing external resources are named on opening.
  Re-saving preserves embedded attachments and a new site's weather never retains the old site's horizon. Format 17.
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
- Clear hand-drawn strings (R184, R185, R186): order numbers stay on their modules at every rotation, zoom and pan;
  every stringed module has an 8 px dot in its string's colour while its short side is at least 14 px on screen. Jumps
  are dashed and direct within a row, or orthogonal bridges through a free gap between nearby rows, with separate
  lanes or dash patterns when they overlap and no detours outside the row.
- Compact plan rotation commands (R183): Align to a side has its own symbol and stays icon-only even when the other
  view buttons show words. North up leaves the bar but keeps N, the compass click and the right-click menu.
- Phase-aware panels (R145): Project hides on Production, Consumption, Balance and Report, then returns on the
  graphical phases only if it was visible; the side panels share the width equally. No animation.
- Plan rotation (R146): alignment with a side of the selected outline and North up through the commands, not the
  touchpad. The round compass follows the view and reports its bearing and compass point; project coordinates never
  change.
- Touchpad navigation (R140, revised by R189): pinch zoom around the cursor in the plan and the 3D view, two-finger
  scrolling to pan on both axes with Windows and Wayland events, and Ctrl with two fingers to zoom. Touchpad rotation
  is off. Plus and minus, also with Ctrl, zoom both views; matching buttons are in each view's bar.
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
- The File page enters with a 180 ms crossfade and a 16 px slide from the File button (R178): the shared entrance
  paints two snapshots under an opaque veil, without effects or relayouts on each frame. Reduced motion shows the
  page at once; closing stays immediate. The previous unrolling mask is gone.
- The phase tools follow the order of the work (R180): Model separates drawing, editing, precision and module
  layout; Comparison has the same name and commands in the result phases; groups have two to five available tools.
  The rare automatic refill and Delete all strings stay in their menus and panels. Shortcuts are unchanged.
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
- Opening a project left out the maker chosen to size the inverters (R141) with a notice in English: the maker is
  kept, and the notice of keys left out is translated and says «1 key», not «1 keys».
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
