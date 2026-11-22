<a id="2-impianto"></a>

# 2. Plant

Plant is the phase for inverters and strings: what connects the modules laid to the grid.

- **Inverters** are chosen from the catalogue (Computation > Add an inverter from the catalogue…) or sized by Meridiana at the DC/AC ratio entered on the Production page (Computation > Size the inverter by itself). An automatically sized inverter is reported in Checks, under To know.
- **Strings** are checked against CEI 64-8/7:2024 (string checks in `checks.py`, calculation in `energy/stringing.py`): the maximum string open-circuit voltage at the coldest cell against the inverter's and modules' maximum voltage; the maximum-power voltage at temperature extremes against the MPPT window; the maximum short-circuit current, with the standard's margin, against the input's capacity; protection of each string when three or more share the same input. Each failed check says why and what to do.
- **Lowest temperature of the site** (-10 °C by default on the Production page) determines the highest voltage. Take it from the site's climate data.

<a id="il-pannello-di-destra"></a>

## The panel on the right

Manage the whole plant from the panel on the right of the phase; there is nothing above the plan.

The inverter selected in the **Strings** menu, including by selecting one of its strings on the plan, shows all
its details. Other inverters take one row: number, short name, power, strings / used inputs and status symbol.
Click a heading to open its card; click the same heading to close it. Cards with errors stay open.
The Strings menu continues to show every input of the selected inverter. Card folds belong to the view and are
not saved in the project.

To change the order, drag an inverter's number: grip dots appear under the pointer and a line previews the
destination. With the card focused, **Alt+Up** and **Alt+Down** move it one place, including repeated commands.
Each move can be undone with **Ctrl+Z**. Strings follow their inverter and take names based on its new number.

- **Inverters**: the list (how many of each, from the catalogue or PVsyst .OND files with Import from PVsyst… in the catalogue, with the return symbol to go back to those Meridiana proposes), Add an inverter from the catalogue…, Size the inverter by itself, the DC/AC ratio; for a SolarEdge inverter, the optimizers.
- **Strings**: each inverter and input has its strings, each with its colour on the plan, modules and state (symbol and word). An input without strings says so. Selecting a row selects the string on the plan and fits it to the drawing. **Delete** deletes it; a **double click** redraws it; right-click opens its menu (reverse direction, redraw, move to another input, delete). The **+** to the right of an input draws a new string on that input. Below the list: Propose the strings, Complete the strings, Delete all the strings.
- **Proposal and checks**: the strategy and modules in series the next proposal will use (they do not change the current strings), the Lowest temperature of the site and Conditions of the checks.
- **String chosen**: the selected string's checks, with the sources of the temperatures.
- **Sub-field selected**: the inverter and input to which the proposal sends that sub-field's strings.

<a id="le-stringhe-sono-tue"></a>

## The strings are yours

Meridiana never creates or recreates strings by itself. Adding or removing an inverter, changing a module or laying a sub-field again creates and moves no strings (a string stays on its inverter even when the list renumbers it). Modules outside a string remain **unstrung**, with a red border on the plan, and Checks report them. Their fix is Complete the strings. Warning: an unstrung module in the real plant does not produce, whereas the production calculation counts it as connected.

- **Propose the strings** (bar or panel, with the PVsyst strategies menu: Back and forth along the rows, One row per string, U on two rows, One row per MPPT): Meridiana strings all modules laid once, replacing the existing strings. If strings already exist, it asks first. One Undo step.
- **Complete the strings**: Meridiana proposes strings only for unstrung modules, first on inputs without strings, then on those that accept more strings of the same length as yours. Your strings stay as they are. One Undo step.
- **Delete all the strings**: after a question, all modules become unstrung again. One Undo step.
- Projects saved before format 14, whose strings were proposed automatically, keep them unchanged when opened: they become yours without questions or marking the project as changed.

<a id="disegnare-una-stringa-a-mano"></a>

## Drawing a string by hand

1. Press the **+** of the input you want in the list on the right, or Draw on the bar (the selected string's input, or the first free one).
2. Click modules in string order, or drag over them: a module is taken when the pointer passes its centre. Sequence numbers appear on modules. The strip at the top says how many modules you have and how many the input requires ("2 missing (7 to 25)").
3. **Backspace** removes the last module; **Enter** or a **double click** finishes the string (one Undo step); **Esc** cancels it without changing anything.
4. A module already in another string is rejected and the bar says which string. Hold **Shift** while clicking to move it into the string you are drawing (the bar then says which string it came from).

Right-click while drawing to open Close the string (Enter), Take back the last module (Backspace), Give up the string (Esc). On a module in a string it opens Skip this module, The string starts here, ends here, reverse, redraw, move, delete; on an unstrung module, New string from this module.

<a id="sulla-pianta"></a>

## On the plan

Each string has its own tint (neighbouring strings, including in the next row, never have the same one; deleting one does not recolour the others), the name inverter.input.string above its first module with its state indicator, drawn with the program's symbols (white tick on green: correct; yellow triangle: to be checked; red stop symbol: out of the window or without input), and modules filled with its colour. The line goes from one module's centre to the next when they are close. When the string **skips** modules, the line goes around the skipped modules along their edges, **dashed**, and the skipped modules remain uncoloured. A skip is always visible, both while drawing and afterwards. The selected string is highlighted and numbered. Its compact labels follow the string's direction and stay upright, with normal text weight. Counters, including those in Checks, are round with one digit and widen as more digits are added. From far away, names that would overlap are hidden (the colour stays; the name is in the tooltip). [Production](3-producibilita.md) summarises the plant and computes the year for all inverters together.
