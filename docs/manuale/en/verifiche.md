<a id="verifiche"></a>

# Checks

Checks collect what needs attention from every part of the project: layout notes, obstacle shading, string checks, connection requirements, production notes, estimates still used instead of data, and applicable rules. The panel is at the bottom in every phase (Ctrl+J). Ctrl+Shift+M gives it keyboard focus; arrow keys move through items and the views follow.

Each item is a short sentence with its symbol and source. The arrow opens the detail (why, and what to do). A click shows the object in the views with everything else dimmed; a double click goes to the object or page. By level is the default view. Use the header menu to group By object, By area or Ready for delivery. The This phase and This object filters keep only items for the open phase or selected object.

<a id="i-segni"></a>

## The symbols

Each level has its symbol, the same in the panel, project tree, over the plan and 3D, beside strings and in the PDF report: a red circle with a white bar for To fix, a yellow triangle with an exclamation mark for To check, a blue circle with an "i" for To know, a green circle with a tick for Passed. They are flat, with one colour and a white symbol, readable on any background: the plan, orthophoto, dark theme. They are never font characters. Colour is not the only cue, because each level also has a different shape.

<a id="da-correggere"></a>

## To fix

Something the standard or layout does not allow: do not deliver the project like this. Examples: a layout that cannot be computed, a string above the inverter's maximum voltage, a single-phase connection above 6 kW. Fix applies the proposed change (Ctrl+. on the current item), and Undo takes it back.

<a id="da-controllare"></a>

## To check

A loss or risk, not a prohibition: you decide. Examples: obstacles removing more than 3% of an array's irradiation, modules left outside strings, ballast alone on a slab. Read the detail below the row, then fix it or leave it as it is.

<a id="da-sapere"></a>

## To know

A fact the report will cite: a threshold exceeded (for example, above 11.08 kW the interface protection is a dedicated relay: CEI 0-21:2026-07, 8.6.2, rule N05), an applicable rule, a value still at its default. Nothing to fix. File > Copy the notes for the report copies the rule paragraphs with their sources.

<a id="superate"></a>

## Passed

Passed checks, each with its source: what Meridiana checked and found correct. The section is collapsed by default to put what needs attention first.

<a id="fonte"></a>

## Source

Each item says where it comes from: a standard with edition, article and page; a law; the calculation model; or Meridiana when it is the program's interpretation rather than a rule (for example the 3% shading threshold). Rules come from Daniel's "Utilità Fotovoltaico R02" library (21/10/2026), whose texts were checked against the archive documents (`rules.py`).
