<a id="6-relazione"></a>

# 6. Report

Report collects the deliverables. The panel on the right lists them with their state: done (with the file and time), to make again because the project changed, to make, not available (and why), not yet (which task will provide it).

- **The PDF report** (File > Export the report (PDF)…, Ctrl+E): production, strings, consumption and economics with every calculation, formula and source; at the end, values still at their defaults, to replace, and what the model does not calculate.
- **Notes for the report** (File > Copy the notes for the report): the paragraphs of the rules that apply to the plant, with their sources, to paste into the technical report. Rules come from Daniel's "Utilità Fotovoltaico R02" library (`rules.py`).
- **Who signs the report**: enter author profiles (name and title, professional register, practice, address, contacts, logo) once in File > Settings > Report. The program contains no person's name, and profiles stay in the PC's settings. When you save, the current profile and its logo also enter the project file: the recipient sees the same signature without needing your settings.
- **Which profile signs this project**: choose in the right column of the Report phase, under Signed by. Default is the profile selected in Settings > Report, under For the projects that choose none. The first profile you create becomes the default. If only one profile exists, a project without a choice uses it. Nobody leaves only the project and date, and stays that way until you change it. As it was saved is the profile already in the project file, when no other has been chosen on the PC. If the PC has a profile with the same name, the one in Settings applies.
- **The logo, from the Report bar**: in the Signature group, **Logo** asks for the file and puts it in the profile signing the project (if nobody signs, in the default; if no profile exists, it creates My profile and opens it for you to complete). The preview updates at once. **Profile** opens Settings > Report at the current profile. The Back button returns to Report. The same commands are in the File menu. With several profiles and none in use, Meridiana first asks you to choose one in Signed by.
- **Logo formats**: PNG, JPEG, GIF, WebP and SVG. An unreadable or damaged file is rejected with a message, and the profile stays as it was.
- **If the logo is missing**: check in Signed by which profile signs the project. When you put a logo in a profile the project does not use, Meridiana says so in a line and offers Use it for this project. The selected signature does not change by itself. A choice pointing to a renamed or removed profile appears in Signed by as "(not in the Settings)".
- **PDF attachments** are embedded in the project when you save it. You can then move or send the `.mer` file alone without losing datasheets and certificates; on opening, Meridiana restores them in its cache. If an attachment was never embedded and its original file can no longer be found, the warning says so clearly.
- **Variants compared** (Variants > Compare the variants…, Ctrl+Shift+C): production, self-consumption and economics of each variant, side by side.

Before delivery, [Checks](verifiche.md) in Ready for delivery mode collect what needs fixing and checking, defaults and estimates still in use. Other deliverables (dimensioned plan, DXF, IFC4, CSV lists) will come with their tasks.

<a id="navigare-nellanteprima"></a>

## Navigating the preview

Contents beside the sheets lists chapters and paragraphs. Click an entry to
reach the start of its page. Scrolling highlights the entry in view. The tree
arrows expand or collapse paragraphs. The cross closes Contents; the Contents
button reopens it. The program remembers this choice across restarts.

The fixed bar shows Page n of N. Enter a number from 1 to N in the adjacent field
and press Enter. With the preview focused, Page Up/Page Down reach the previous
or next page. Home/End and Ctrl+Home/Ctrl+End reach the first or last page.
The wheel and touchpad scroll as before; Ctrl+wheel changes the zoom. These
navigation keys belong to the preview: in text fields they keep editing text.
After a rebuild, the chapter or paragraph in view is restored at its new page.
If it was removed, the enclosing chapter or nearest page is used.

<a id="copiare-il-testo-di-una-pagina"></a>

## Copying a page's text

On a report sheet, the right mouse button, Menu or Shift+F10 offers Copy page text
and Read page text… The first copies the page's text; the second opens selectable
text so you can choose an extract, without changing the clipboard. Extraction runs
in the background. If you close or change the preview, an old result is not copied.

An image-only page may contain no selectable text: the program says so and disables
copy after checking. It does not perform OCR. The extracted order depends on the
PDF: tables and formulas may need checking against the sheet. Report exports
remain available.

<a id="ambito-del-profilo-normativo"></a>

## Scope of the regulatory profile

The regulatory profile is saved in the project and is separate from the professional profile signing the report. Changing language or signature does not change calculations. Projects in earlier formats use Italy.

With the Generic IEC profile the report states: "Generic IEC profile: physical calculations and declared data; local obligations and regulatory compliance not assessed". Electrical checks concern only known physical data. Missing data are flagged and do not give a positive compliance result.

The generic profile retains the common geometry, sun, shadows, simulation, storage and financial calculations. It requires manual strings and declared equipment data. Without explicit consumption it uses zero. Declared totals are distributed evenly over the actual hours, while an imported hourly curve is retained. It uses a single ALL band and, without an explicit time zone, UTC. It does not add national holidays or fire setbacks.

Undeclared prices and costs are zero: enter the bill and offer before assessing the investment. It does not apply national CER, TRASE, grants or tax deductions, even if those values are retained in the file. IEC references are bibliographic; the report does not certify compliance with them or permission to build. Local obligations must be checked separately. No new profile selector has been introduced.
