<a id="manuale-di-meridiana"></a>

# Meridiana manual

The manual is available in Italian (`docs/manuale`) and English
(`docs/manuale/en`). Every change must be made in both languages. Tests check
the structure, anchors, commands and interface terminology.

The manual accompanies the program. Open it from Help > Manual and the Manual › links in the help box, which lead to the right paragraph. There is one chapter per phase, in the order of the phase row (move between phases with a click on a tab or with the mouse wheel over the tabs). Checks have their own chapter because they apply to every phase.

Draft of 24/10/2026 (task 17d), written from the program's calculations and rules. Daniel still needs to review the technical substance and sources.

<a id="come-chiedere-aiuto"></a>

## How to ask for help

- **The help box**, at the bottom of the panel on the right in every phase: it explains the panel field with focus, or the result tile under the pointer. Three lines of text, the source and three links: Manual › (this manual, at the right paragraph), How it is computed › (the calculations page, at the right step), Ask Meridio › (the assistant, with the question already entered). Click the title to collapse or reopen it; it stays as you leave it. If the panel is less than 480 px high, the box hides automatically and the ? buttons open the same text in a popup.
- **The ?** beside the title of a Properties group or a result tile opens the help box at that item.
- **F1** explains the field with keyboard focus, throughout the window.
- **Shift+F1** (What's this?) turns the pointer into a question mark: the next click explains what it touches.
- **Ctrl+?** opens the keyboard shortcuts list.

The three commands are also in the Help menu. An F key is never the only route (on laptops F keys are often media keys).

**View > Full screen** (F11) fills the screen without the window frame and taskbar. F11 again restores the window as it was, maximised or in its position. Esc does not leave full screen, because tools use it. The window never starts in full screen.

<a id="menu-del-testo"></a>

## Text menus

In a field, open the menu with the right mouse button, the Menu key or Shift+F10.
A long press is available when the platform recognises it. The menu offers Undo,
Redo, Cut, Copy, Paste, Delete and Select all; unavailable commands are disabled.
Delete applies to the selection. While editing, shortcuts act on the text;
opening the menu keeps the draft. Passwords cannot be copied.

In reading text you can select an extract. Copy uses the selection, or the whole
text when there is no selection. With a partial selection, Copy all or Copy message
is also available. Shortened values are copied in full. In Meridio bubbles Copy
produces readable text; Copy as Markdown appears only when the message has a
formatted source and copies the whole message already shown. The text is fixed
when the menu opens, even while a response is still arriving.

For numbers, Paste and Ctrl+V accept a decimal comma or point and the field's unit
suffix. Unit conversions, such as centimetres to metres, and expressions are
available in quantity fields that already support them. An ambiguous value such
as 1.500, an incompatible unit, multiple lines or an out-of-range number is rejected
without changing the field. A valid paste can be undone with one Undo.

Tables copy a cell with its unit or selected rows as TSV, in the displayed order.
Charts copy the active point with its series and units; formulas offer Copy formula
(LaTeX). Checks retain Ask Meridio; copying a row includes its detail and source,
without duplicates.

<a id="impostazioni"></a>

## Settings

**File > Settings** brings together Appearance, Navigation, Keyboard, Assistant, Report, Maps and Privacy in the main window. Every change applies and saves immediately. **Undo the last change** goes back; **Restore defaults for this section** asks for confirmation on the page, without modal dialogs. The command also opens with Ctrl+,.

<a id="clienti-e-commesse"></a>

## Clients and jobs

**File > Clients and jobs** shows three columns: clients, jobs and details with linked projects and folders. **New client** and **New job** add them without separate windows. The job code has five digits and stays text, preserving leading zeros. The register is a SQLite database on the PC, with transactions and a `.bak` copy updated after every write. If the database cannot open, Meridiana warns without overwriting it and uses a temporary register, so projects remain usable.

In **File > New**, under optional data, choose a client and job. The client name goes into the report. A reserved job stops online search and tiles as soon as you select it. On saving, Meridiana links the file to the job and writes the series IDs into the project, from format 18. Saving R02 and reopening R01 preserves the same link.

**File > Open** opens a Meridiana project (.mer) or a PVsyst project (.PRJ, also with Ctrl+I). The PVsyst project and its variants become a new project; Meridiana first says what it approximated or could not find. Other files are imported where needed: the IFC model in Modelling (Building button dropdown, From IFC), PVsyst modules (.PAN) and inverters (.OND) from their catalogues in Plant (Import from PVsyst…), the PVGIS typical year and horizon in Production, the load curve in Consumption, an image under the drawing from the Background menu on the plan bar.

<a id="posa-pensiline-e-modello-bim"></a>

## Layout, canopies and BIM model

The **Modelling** phase is only for the model: Edit, Draw (building, from a template, canopy, pitch, ridge, exclusion) and Precision. Modules are laid in the **Plant** phase, in the order modules, inverters, storage. The Modules group has one button, **Lay** (S), which draws the sub-field with its modules. Its menu also has **Row of modules** (L), **Area with automatic layout** (an area filled by automatic layout with margins, fire brigade rules and target power, the same entry as right-clicking a roof), **Fill** and **Empty** (for the selected sub-field, as in its menu).

For East-west pairs, choose the East-west pairs mounting in the sub-field's Properties, then **Fill** or **Row of modules**. The electrical proposal separates the two orientations.

**Canopy** draws the structure: spaces per row, one or two rows, space width and depth, clear height, slope, rotation and columns (cantilevered on one row, or on two rows). Columns and beams appear in the 3D view, shadows, report and IFC. Lay the modules afterwards in Plant by right-clicking the canopy (on the plan or in the 3D view): **Modules on a canopy…**. Structural checks are not included.

The **Auxiliary support plane** can also be enabled on an existing sub-field: centre elevation, tilt and azimuth are independent of the received model's edges. When disabled, they remain stored and the original building/pitch reference applies again. Moving and rotating the sub-field also moves the plane. During IFC import, surfaces that cannot be represented exactly by the pitch boundary generate explicit auxiliary areas in the summary, initially without modules.

The exported IFC4 retains module identifiers, types and catalogue/layout/plant properties. Auxiliary planes are virtual references, separate from built elements. IFC properties do not automatically amount to native Revit parametric families. The `.mer` project embeds data and resources; schema 20 preserves BIM identities, support planes and physical groups of modules on optimizers.

<a id="dimensionamento-e-limiti-del-calcolo"></a>

## Sizing and calculation limits

**Size** searches for inverters and strings in a cancellable task. If you change the project meanwhile, the previous proposal is not applied. The criterion prefers fewer inverters, then fewer models, then the closest DC/AC ratio. The search checks the global assignment within the supplied constraints and catalogue, with a declared budget. If it does not finish, it neither applies a choice as optimal nor declares a solution impossible. **Propose** and **Complete** also run in cancellable tasks and keep connections until the new search finishes and is verified. If inputs are insufficient, they can connect some modules and report how many remain disconnected; **Size** instead requires a solution for all modules. MPPT count, physical connector pairs and shared current limits are distinct information. Inputs on the same MPPT share the operating voltage. Limits conditional on string count are applied when present in the model's datasheet.

An unconnected module does not contribute to production. Shade affects the string's common current: it does not switch off all modules after the shaded one. The calculation combines sampled current-voltage curves of cell groups, bypasses, strings and MPPTs. Where the manufacturer's internal diagram is missing, cell positions and connections are declared assumptions. Hot spots, reverse avalanche and proprietary firmware are not simulated; numerical comparisons do not replace experimental measurements.

Two modules on one optimizer share its MPPT. In the string menu, **Modules on each optimizer** distinguishes pairs and single modules. Groups are preserved after removals and string reversal. Supported SolarEdge models apply documented hourly input and output limits. Missing data and unsupported architectures are reported. Each inverter has its own conversion and limitation: spare capacity on another unit does not compensate for its clipping. The report and CSV give results per inverter; assumptions remain in **How it is computed > What the model does not include**.

<a id="profili-della-relazione"></a>

## Report profiles

As well as Full and Compact, choose **Client presentation**, **Electrical design review** or **Energy and assumptions**, then adjust the chapters. The three new profiles retain checks. Tables repeat their header across pages and the ledger states formulas, inputs, units, sources and results.

On the register page, **Link folder…** adds an existing folder to the job without moving files. Each folder has its checkbox. Only when enabled does Meridiana write and update `.meridiana-commessa.json`. Disabling it removes the manifest and its copy. A reserved job never has a manifest. If a folder is unreachable, the error is displayed and the operation is retried on the next write without stopping other folders.

**Export registry…** creates a JSON of clients, jobs, projects and folders. If it contains reserved jobs, Meridiana warns that the file is not encrypted before writing it. Folder consents do not travel in the file: they stay local and an imported folder always starts without a manifest. Changing path or job requires new consent. **Import registry…** first shows new, updated, unchanged and conflicting records. **Apply import** merges by ID and keeps records absent from the file. Invalid codes, paths or fields block everything, without silent duplicates or partial writes.

<a id="meridio-lassistente"></a>

## Meridio, the assistant

Meridio always has the sticker appearance, with a white border. Settings no longer offer a drawing choice; older profiles also use the sticker.

- **Ctrl+L**, or a click on the character, opens the conversation. Meridio reads the project (checks, results, rules, manual) and answers with sources. If a figure comes from a default or estimate, it says so. It changes nothing by itself: it proposes, and you apply the proposal with a click and undo it with Ctrl+Z.
- **Where it gets standards and thresholds**: only from sources bundled with the program, namely rules and checks with their sources, the 80 activities in Allegato I of DPR 151/2011, this manual and documents you attach. It answers the question first, then says what it relies on and which project data it read. If the answer depends on missing data, it explains each case and asks for those data. If no source has the answer, it says so and names the document that would provide it. It does not write a figure from memory.
- **Where it thinks**: with the PC's local model (the default: nothing leaves the PC) or Claude, if you choose it, with your key and consent. A project marked reserved always stays on the PC.

<a id="progetti-e-attività-locali"></a>

### Local projects and tasks

- Meridio searches `.mer` files in folders linked to jobs. The index stays on the PC and updates in the background. Search by text, job, client, type, power, date or distance. "The latest similar shed" shows only one valid revision per series and explains type, power, mounting, tilt, distance and revision. It helps you search; it is not a technical assessment.
- Before opening, Meridio shows a card with the path and revision. Only **Open** proceeds, with the usual prompt to save or discard unsaved work. **Cancel** in that prompt keeps both project and card.
- **List tasks** reads text, due date and state from the local register. Creation and completion always go through a confirmation card. Meridio does not complete tasks by itself.
- Claude does not receive the index, reserved projects, names, paths or job codes. The program filters first and uses aliases; a question about reserved items goes to the local model. Switching from a local conversation to Claude starts a new conversation: local history is not exported.

<a id="un-modello-locale-in-pochi-passi"></a>

### A local model in a few steps

File > Settings > Assistant > **Local models on this PC** automatically finds model-serving programs (Ollama, LM Studio, llama.cpp, Jan, Lemonade, Docker Model Runner, any OpenAI-compatible server). It says which are running and which are only installed, lists models and recommends a lightweight model that can use tools: among suitable models it prefers one that fits in graphics memory or leaves more RAM free.
- **Use it** puts the server, model and server type into the fields. The choice applies and saves immediately.
- **Test** asks a short question: it must return a tool call, like those Meridio uses. The first time, the model loads from disk; this may take a minute.
- **If nothing is installed**, the page gives steps with commands to copy: install Ollama (from ollama.com/download, or `winget install Ollama.Ollama`) and download the model suited to the PC, for example `ollama pull qwen3.5:9b` on a PC with 32 GB RAM and an 8 GB graphics card. Ollama needs no other setup: Meridiana requests the context and disabled reasoning itself.
- If you prefer llama.cpp: `winget install llama.cpp`, then `llama-server -hf unsloth/Qwen3.5-9B-GGUF:Q4_K_M -c 16384` (port 9931 is Meridio's default).
- If the local model does not respond while you ask a question, Meridio finds another model on the PC and offers it with a click.

- The default recommendation is **Qwen3.5-9B**, a download of about 6.6 GB, estimated to fit an 8 GB graphics card; with little memory it suggests the 4B. An explicit saved choice is preserved. Larger models remain available to select.
- Opening Meridio or focusing the question field prepares the local model in the background if it is not already loaded. **Preparing the model…** appears in the field: you can type and send; the question waits for preparation. If free memory is insufficient or cannot be read, preparation is skipped and the field explains why; you can still send a question.
- **Prepare Meridio when the program starts**, in Settings > Assistant, is off by default. When enabled, work starts three seconds after the window opens, at low priority in the job queue, with the same free-memory check.
- Windows share the model on the same server. Ollama keeps it loaded for 30 minutes; closing Meridiana does not unload it because another window may be using it.

<a id="i-capitoli"></a>

## The chapters

1. [Model](1-modello.md): the site, buildings, sub-fields, exclusions, module layout.
2. [Plant](2-impianto.md): inverters and strings.
3. [Production](3-producibilita.md): the year hour by hour, results, losses.
4. [Consumption](4-consumi.md): where consumption comes from and its shape.
5. [Balance and economics](5-bilancio.md): self-consumption, bill, cash flows.
6. [Report](6-relazione.md): deliverables.
7. [Checks](verifiche.md): levels, sources, Fix.

<a id="installare-e-aggiornare"></a>

## Installing and updating

- **Windows**: the `meridiana-setup-vX.Y.Z-windows-x64.exe` installer from releases on GitHub installs the program only for you, without administrator rights, and opens `.mer` files with Meridiana. The portable zip is the same program in a folder. Settings stay in `%APPDATA%\Meridiana`, recovery copies and caches in `%LOCALAPPDATA%\Meridiana`: uninstalling does not touch them.
- **Updates**: once a day, one minute after startup, the Windows program asks GitHub whether a newer version is available (it sends nothing about you or your projects). Help > Check for updates… asks immediately. If one exists, a window says what it brings. The installed program downloads the installer, checks it against GitHub's published checksum and the project's signature (minisign), asks you to save the project and starts it. Meridiana closes and reopens updated. The portable zip opens the release page. Turn the check off in File > Settings > Privacy, Updates.
- **Linux**: Flatpak, built from the source manifest until a repository publishes it; its updates will come through the desktop's software centre.
- **What leaves the PC**: nothing about you, and never project files. The searched address goes to OpenStreetMap's Nominatim, site coordinates to PVGIS, the visible area to map servers, the release query to GitHub, each with its switch in File > Settings > Privacy. Meridio sends questions to Anthropic only if you choose Claude, provide your key and consent. In a reserved project, names and addresses never leave and Meridio stays local. Maps and PVGIS receive coordinates only after consent specific to that project.

<a id="come-leggere-i-numeri"></a>

## How to read the numbers

Every number says where it comes from, with one of six source types: a value you entered; a Meridiana default, identified as such; data (PVGIS, a datasheet, a catalogue); a standard with edition, article and page; a published model (Perez 1990, the PVsyst thermal model); the result of a previous step. How it is computed, on every results page, shows steps with formulas. The PDF report includes them and lists values still at their defaults at the end.

In this manual, defaults name the program file that sets them; standards name the rule in `rules.py` or check in `checks.py` that cites them. Numbers given as an order of magnitude are not standard values: they help you recognise an unusual result.


<a id="aggiornamenti-documenti-e-assistenza"></a>

## Updates, documents and support

In Settings > Privacy you can allow update checks and, on installed Windows, automatic installation of signed updates. A project with unsaved changes blocks installation; you can cancel the download or withdraw consent. Portable and source versions are updated manually. Flatpak follows the configured repository and the system's software centre: a new version number on GitHub does not prove an installable Flatpak exists.

Meridio accepts text PDFs and UTF-8 TXT/MD/CSV files, also by drag and drop: at most four files, 10 MB per file, 40 pages per PDF and 60,000 characters overall. Extraction is local; scans need OCR first. Text is sent only with the message. Cloud use requires specific consent even when a later message resends documents already in the conversation. Reserved projects stay local. When a conversation contains documents, tools acting on the project are disabled: start a new conversation to use them again. A proposed card remains a draft to review.

Meridio also sees images (PNG, JPEG, WebP, GIF): use Attach…, drag them into the chat or paste with Ctrl+V in the field. The image button beside Attach… shows it the phase view as you see it, without the bubble and windows. Before sending, the image is reduced on the PC (longest side 1568 px, no metadata, at most 5 MB). The cloud asks for consent every time: a screenshot may show addresses and names that aliases do not cover. Local use needs models with vision (Gemma 4, Qwen VL, LLaVA); if the model cannot see, Meridio says so.

Catalogue windows let you add personal products, copy one to correct it and compare two to four rows. Each personal record requires essential data and a source. Human review does not inherit a previous attestation that values were verified. Additional technical fields are currently editable in JSON with explicit units. An inconsistent record cannot be selected.

Configure storage in Plant, beside the inverters. AC coupling requires its own converter; DC coupling requires a hybrid inverter, a documented pairing and voltage, current, power and quantity limits. Brand alone does not prove compatibility. Parallel quantities require a declared limit. Apply records one undoable change. Results stay in the energy and economic balance. The current model uses an AC-bus equivalent and an overall efficiency entered by the designer: it does not recover PV energy lost to clipping on the DC side.

From Help or File > Help you can start the guided tour and prepare an issue report. Meridio also recognises "Start the guided tour" and "Report a bug" without connecting to a model. The tour can be skipped, paused and resumed; it does not change the project. To try it without the menu: `meridiana --tour 5` opens it at the fifth step (the number or name of the step); `meridiana --tour nuovo` simulates first startup. They use temporary settings and do not touch yours. The issue report shows an editable draft, with optional system data, context and selected diagnostic lines. The preview masks recognised paths and credentials: always check it. Open GitHub draft opens a public form without sending the report. You can instead copy or save the draft in a new file.
