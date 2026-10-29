"""The window's commands and their keys, in one place: an id, the text of the menu, the keys it starts with. The
keys the designer changes are kept in the settings (config.Config.shortcuts), only where they differ from these.

The map is the one of study 12, section 5, decided on 22/10/2026 (study 12a, 1.11):
- one family per category: panels and checks as in the IDEs (VS Code), drawing aids, mouse and aliases as in
  AutoCAD, tools on single letters as in Aurora, HelioScope and SketchUp;
- never a command only on an F key: on the Framework 13 the F keys are media keys without Fn, and every command
  is in a menu as well;
- never Ctrl+Alt (AltGr on Italian keyboards: Ctrl+Alt+E writes €), Alt+letter (the menus), Super, the
  characters written with AltGr, Shift+?, Ctrl+Shift+/, Ctrl+Space;
- single letters work in the whole window but not while writing in a field (Qt does that), and can be changed
  (WCAG 2.1.4).

Keys are written as Qt writes them (QKeySequence.toString with PortableText): «Ctrl+Shift+P», «F8», «Del». No Qt
here: the window makes its QActions from COMMANDS, and the editor of the keys asks `clashes` and `problem` while
the designer types."""

from __future__ import annotations

from dataclasses import dataclass

from .i18n import _, pgettext


@dataclass(frozen=True)
class Command:
    id: str
    text: str                   # as in the menu, with the & of its access key
    keys: tuple = ()            # the keys it starts with, most important first
    group: str = ""


MODIFIERS = ("Meta", "Ctrl", "Alt", "Shift")       # Qt's order in PortableText
# written with AltGr on an Italian keyboard, or kept away by Microsoft's rules
ALTGR = set("[]{}@#~`\\")


def groups() -> dict:
    return {"file": _("File"), "edit": _("Edit"), "draw": _("Draw"), "view": _("View"), "phases": _("Phases"),
            "panels": _("Panels"), "compute": _("Computation"), "variants": _("Variants"), "help": _("Help")}


def commands() -> list[Command]:
    """Every command of the window that a key can start, in the order of the menus."""
    c = Command
    return [
        c("new", _("&New"), ("Ctrl+N",), "file"),
        c("open", _("&Open…"), ("Ctrl+O",), "file"),
        c("save", _("&Save"), ("Ctrl+S",), "file"),
        c("save_as", _("Save &as…"), ("Ctrl+Shift+S",), "file"),
        # was Ctrl+Alt+S: Ctrl+Alt is AltGr on an Italian keyboard (study 12a, 1.9)
        c("save_revision", _("Save as a new &revision"), ("Ctrl+Shift+R",), "file"),
        c("import_pvsyst", _("&Import a PVsyst project…"), ("Ctrl+I",), "file"),
        # the buildings of an architect's model (study 20), and the project as a model for the architect (study 15)
        c("import_ifc", _("Import an IFC &model…"), (), "file"),
        c("export_report", _("&Export the report (PDF)…"), ("Ctrl+E",), "file"),
        c("export_csv", _("Export the &hourly series (CSV)…"), (), "file"),
        c("export_ifc", _("Export the model as IF&C4…"), (), "file"),
        c("copy_notes", _("Copy the notes for the &report"), (), "file"),
        c("preferences", _("&Settings…"), ("Ctrl+,",), "file"),
        c("quit", _("&Quit"), ("Ctrl+Q",), "file"),
        c("undo", _("&Undo"), ("Ctrl+Z",), "edit"),
        c("redo", _("&Redo"), ("Ctrl+Y", "Ctrl+Shift+Z"), "edit"),
        c("delete", _("&Delete"), ("Del",), "edit"),
        c("tool_select", _("Select"), ("V",), "draw"),
        c("tool_building", _("Building"), ("B",), "draw"),
        c("tool_pitch", pgettext("roof", "Pitch"), ("P",), "draw"),
        c("tool_subfield", _("Sub-field"), ("S",), "draw"),
        c("tool_exclusion", _("Exclusion"), ("X",), "draw"),
        # a row of modules drawn by hand (task 16c): L was free (design 2.2)
        c("tool_row", _("Row of modules"), ("L",), "draw"),
        # M moves (and R inside Move turns), D measures: study 16, B; Daniel, 23/10/2026 (config version 14 moves a
        # Measure on M to D)
        c("tool_move", _("Move"), ("M",), "draw"),
        c("tool_rotate", _("Rotate"), (), "draw"),
        c("tool_measure", _("Measure"), ("D",), "draw"),
        c("rectangle", _("&Rectangle by three clicks"), ("R",), "draw"),
        c("square", _("S&quare the corners"), ("Q",), "draw"),
        c("building_template", _("Building from a &template…"), (), "draw"),
        c("carport", _("Parking canopy…"), (), "draw"),
        c("layout_east_west", _("East-west layout"), (), "draw"),
        c("snaps", _("S&naps"), ("F3",), "draw"),
        c("ortho", _("&Ortho"), ("F8",), "draw"),
        c("fill", _("&Lay the modules"), (), "draw"),
        c("empty", _("Take the modules &out"), (), "draw"),
        c("refill", _("Lay a&gain automatically"), (), "draw"),
        c("view_plan", _("Plan"), ("Ctrl+Shift+2",), "view"),
        c("view_3d", _("3D"), ("Ctrl+Shift+3",), "view"),
        c("view_both", _("Side by side"), (), "view"),
        c("fit", _("&Fit to the drawing"), ("F",), "view"),
        c("zoom_in", _("Zoom &in"), ("+", "Ctrl++"), "view"),
        c("zoom_out", _("Zoom &out"), ("-", "Ctrl+-"), "view"),
        # A and N (R174, Daniel 26/10/2026: «non bisognerebbe andare sul menu su alt per aprirlo»)
        c("view_align", _("&Align the view to a side…"), ("A",), "view"),
        c("view_north", _("&North up"), ("N",), "view"),
        c("strings", _("&Strings on the plan"), ("W",), "view"),
        c("toolbar_text", _("&Text under the icons"), (), "view"),
        # the menu bar hidden until Alt, or always there (R53; Daniel, 24/10/2026)
        c("menu_bar", _("&Menu bar"), (), "view"),
        # the phases by their numbers (Daniel, 24/10/2026: «le fasi con Ctrl+numero», Properties to Ctrl+P), and in
        # turn with Ctrl+Tab and Ctrl+PgDown as the browsers and the IDEs; Shift+Tab reaches Qt as Backtab
        c("phase_model", _("Model"), ("Ctrl+1",), "phases"),
        c("phase_plant", _("Plant"), ("Ctrl+2",), "phases"),
        c("phase_production", _("Production"), ("Ctrl+3",), "phases"),
        c("phase_consumption", _("Consumption"), ("Ctrl+4",), "phases"),
        c("phase_economics", _("Balance and economics"), ("Ctrl+5",), "phases"),
        c("phase_report", _("Report"), ("Ctrl+6",), "phases"),
        c("next_phase", _("Next phase"), ("Ctrl+Tab", "Ctrl+PgDown"), "phases"),
        c("previous_phase", _("Previous phase"), ("Ctrl+Shift+Backtab", "Ctrl+PgUp"), "phases"),
        c("panel_project", _("Project"), ("Ctrl+B",), "panels"),
        c("panel_properties", _("Properties"), ("Ctrl+P",), "panels"),
        c("panel_checks", _("Checks"), ("Ctrl+J",), "panels"),
        c("panel_help", _("Help"), (), "panels"),
        c("focus_checks", _("Go to the checks"), ("Ctrl+Shift+M",), "panels"),
        c("fix_check", _("Fix the check in hand"), ("Ctrl+.",), "panels"),
        c("assistant", _("Assistant"), ("Ctrl+L",), "panels"),
        c("clean_screen", _("Only the drawing"), ("Ctrl+0",), "panels"),
        c("default_layout", _("Restore the default layout"), (), "panels"),
        # the commands of the phases of the results (design 2.4-2.6): F5 as «recompute», and in the Compute menu
        c("compute", _("&Compute"), ("F5",), "compute"),
        c("fetch_pvgis", _("Fetch the weather from &PVGIS"), (), "compute"),
        c("inverter_catalog", _("Add an &inverter from the catalogue…"), (), "compute"),
        c("inverter_auto", _("Si&ze the inverter by itself"), (), "compute"),
        # the strings of the Plant phase (task 16d; R114-R116): proposed by Meridiana only when asked, completed for
        # the modules left out, drawn by hand on the plan, all deleted
        c("strings_auto", _("P&ropose the strings"), (), "compute"),
        c("strings_complete", _("Co&mplete the strings"), (), "compute"),
        c("strings_manual", _("&Draw a string"), (), "compute"),
        c("strings_clear", _("Delete all the stri&ngs"), (), "compute"),
        c("import_curve", _("Import a load c&urve…"), (), "compute"),
        c("consumption_base", _("&Base of the consumption"), (), "compute"),
        c("battery_catalog", _("Choose a ba&ttery from the catalogue…"), (), "compute"),
        c("new_variant", _("&New variant from this one…"), ("Ctrl+Shift+N",), "variants"),
        c("compare_variants", _("&Compare the variants…"), ("Ctrl+Shift+C",), "variants"),
        # help next to things (design C7): F1 on the field with the keyboard, Shift+F1 «What's this?» on what is
        # clicked next, both in the Help menu as well; Ctrl+? stays the list of the keys
        c("context_help", _("&Help on this field"), ("F1",), "help"),
        c("whats_this", _("What's &this?"), ("Shift+F1",), "help"),
        c("manual", _("&Manual"), (), "help"),
        c("shortcuts", _("&Keyboard shortcuts"), ("Ctrl+?",), "help"),
        c("check_updates", _("Check for &updates…"), (), "help"),
        c("about", _("&About Meridiana"), (), "help"),
    ]


def plain(text: str) -> str:
    """The text of a menu without the & of its access key."""
    return text.replace("&&", "\0").replace("&", "").replace("\0", "&")


def normalize(keys: str) -> str:
    """One way of writing keys: modifiers in Qt's order and capitalised, a letter in capitals. «shift+ctrl+p»
    is «Ctrl+Shift+P»; chords («Ctrl+K, Ctrl+S») each on their own."""
    return ", ".join(_chord(c) for c in keys.split(", ") if c.strip())


def _chord(chord: str) -> str:
    mods, key = _parts(chord.strip())
    key = key.strip()
    key = key.upper() if len(key) == 1 else {"delete": "Del", "escape": "Esc", "enter": "Return"}.get(
        key.lower(), key[:1].upper() + key[1:])
    return "+".join([m for m in MODIFIERS if m in mods] + [key])


def _mod(text: str) -> str:
    return {"ctrl": "Ctrl", "control": "Ctrl", "shift": "Shift", "alt": "Alt", "meta": "Meta", "super": "Meta",
            "win": "Meta"}.get(text.strip().lower(), "")


def _parts(chord: str) -> tuple[set, str]:
    """The modifiers and the key of one chord; «Ctrl++» has the plus as its key."""
    if chord.endswith("++") or chord == "+":
        head, key = chord[:-2] if chord != "+" else "", "+"
    elif "+" in chord:
        head, _plus, key = chord.rpartition("+")
    else:
        head, key = "", chord
    return {m for m in (_mod(p) for p in head.split("+")) if m}, key


def problem(keys: str) -> str:
    """Why these keys should not start a command (study 12a, 1.9 and 1.11), or ""."""
    for chord in normalize(keys).split(", "):
        mods, key = _parts(chord)
        if "Meta" in mods:
            return _("The Super (Windows) key belongs to the system and to Niri")
        if {"Ctrl", "Alt"} <= mods:
            return _("Ctrl+Alt is AltGr on an Italian keyboard: Ctrl+Alt+E writes €")
        if "Alt" in mods and (len(key) == 1 and key.isalnum()):
            return _("Alt with a letter or a digit opens the menus")
        if key in ALTGR:
            return _("«{key}» is written with AltGr on an Italian keyboard").format(key=key)
        if key == "?" and "Shift" in mods:
            return _("Shift+? needs Shift twice on an Italian keyboard")
        if key == "/" and {"Ctrl", "Shift"} <= mods:
            return _("Ctrl+Shift+/ needs Shift twice on an Italian keyboard")
        if key == "Space" and "Ctrl" in mods:
            return _("Ctrl+Space switches the input method on some systems")
        if key == "U" and {"Ctrl", "Shift"} <= mods:
            return _("Ctrl+Shift+U types a Unicode character on Linux")
        if mods == {"Alt"} and key == "F4":
            return _("Alt+F4 closes the window")
    return ""


def single(keys: str) -> bool:
    """A key without modifiers that writes a character: it works only while no field is being written in."""
    mods, key = _parts(normalize(keys))
    return ", " not in normalize(keys) and not mods and len(key) == 1


def only_f_key(keys) -> bool:
    """All the keys are F keys: on a laptop without Fn lock they are media keys."""
    def f(k):
        _mods, key = _parts(normalize(k))
        return key[:1] == "F" and key[1:].isdigit()
    return bool(keys) and all(f(k) for k in keys)


def bindings(user: dict) -> dict:
    """id -> the keys in use: the defaults, with what the designer changed (`user`: id -> list of keys)."""
    out = {c.id: [normalize(k) for k in c.keys] for c in commands()}
    for cid, keys in (user or {}).items():
        if cid in out and isinstance(keys, list):
            out[cid] = [normalize(k) for k in keys if isinstance(k, str) and k.strip()]
    return out


def differences(current: dict, saved: dict | None = None) -> dict:
    """What differs from the defaults, to keep in the settings: a key given back to its default leaves them.
    The commands of `saved` (the settings as read) that this version does not know keep their keys: after a
    return to an older version, saving the settings took away what the newer one had been given."""
    defaults = bindings({})
    out = {cid: keys for cid, keys in current.items() if cid in defaults and keys != defaults[cid]}
    out.update({cid: keys for cid, keys in (saved or {}).items() if cid not in defaults})
    return out


def settle(user: dict) -> tuple[dict, list]:
    """The keys in use, and what had to be settled: a key the designer chose that a command added later has
    by default stays the designer's, and that command is left without it (Qt runs neither of two commands with
    the same key, and says nothing). The notes are (keys, the designer's commands, the commands that lost it);
    keys the designer gave to two commands are noted with nobody losing them: only the designer can choose."""
    keys = bindings(user)
    chosen = {cid for cid in (user or {}) if cid in keys}
    notes = []
    for k, holders in conflicts(keys).items():
        mine = [cid for cid in holders if cid in chosen]
        others = [cid for cid in holders if cid not in chosen]
        if len(mine) == 1 and others:
            for cid in others:
                keys[cid] = [x for x in keys[cid] if x != k]
            notes.append((k, mine, others))
        elif len(mine) > 1:
            notes.append((k, mine, []))
    return keys, notes


def clashes(current: dict, cid: str, keys: str) -> list[str]:
    """The other commands that already answer to `keys`: they would stop working with them."""
    k = normalize(keys)
    return [other for other, ks in current.items() if other != cid and k in ks]


def conflicts(current: dict) -> dict:
    """keys -> the commands that share them, when more than one does."""
    holders: dict = {}
    for cid, ks in current.items():
        for k in ks:
            holders.setdefault(k, []).append(cid)
    return {k: ids for k, ids in holders.items() if len(ids) > 1}
