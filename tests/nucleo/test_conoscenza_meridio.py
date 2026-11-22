"""The guard of what Meridio can know (study 50, 3.5; phase 0, point 5): what the program declares (its commands, its
settings, the fields Meridio may propose, its checks) against the texts that explain it. Meridio does not know: he reads
(3.1). An item without a text that explains it is a hole: he names it and invents the rest.

What counts as the item's text («voce»), until the program's chart of study 50 (phase 1) gives every item its own:
- a command, a setting: an aid of the Properties (app/interface/help.py), a paragraph of the manual or a step of the
  guided tour that holds every word of its Italian name (at least two words: a name of one word found in a text is a
  weak match, as in docs/studio/50-prove/A-programma.md), or, for a setting, the description the Settings write beside
  it. A tool that lists the names (read_navigation, go_to) is not a text: the study's «100 % of the commands deceives»;
- a field that propose_edit accepts: a name for the designer (app/interface/fields.field_label), not its key;
- a check of the strings (by its key) and a check of the panel (by its text): its why and its source.

Today's holes are the list DEBITI, by family, one id each: it can only get shorter. A new command, setting, field or
check without its text is red with its name; a hole closed whose id is still listed is red too («take it out»), as
DEBITI of tests/nucleo/test_strati.py. A setting of Config that is neither shown nor declared internal is red as well.
`python -m nucleo.test_conoscenza_meridio` from tests/ prints the holes of today, to compare.

The counts against the study's (50-prove/A-programma.md and B-verifiche-regole.md) are in the notes of DEBITI."""

import ast
import dataclasses
import sys
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _knowledge_text import fold, explained

SRC = Path(__file__).resolve().parents[2] / "src" / "meridiana"
# the panel's checks and the strings' checks are built in these files (study 50, B-verifiche.py); the generic profile's
# own strings are left out, as the study leaves them out
GENERIC_ONLY = {"core/energy/physical_strings.py", "core/rules/profiles/generic/profile.py"}
STRING_FILES = {"core/energy/stringing.py", "core/rules/profiles/it/electrical.py", "core/energy/optimizers.py",
                "core/energy/optimizer_strings.py", "core/energy/plant.py", "core/rules/profiles/it/market.py"}
EXPANDED = {"connector_": ("connector_imp", "connector_isc"),
            "connector__missing": ("connector_imp_missing", "connector_isc_missing"),
            "opt_": ("opt_fuses", "opt_toggle")}
# the settings shown as a table, which labels() does not name: their titles in the Settings
TABLE_TITLES = {"shortcuts": "Keyboard shortcuts", "report_profiles": "Designer's profile",
                "map_sources": "Map sources", "assistant_cloud_profiles": "Cloud profiles",
                "assistant_consent": "Consents"}


DEBITI: dict[str, tuple[str, ...]] = {
    # commands without a text that explains them (study 50, 3.2: 39 of 97 have a manual paragraph; here the aids and the tour count too). Paid by the chart of phase 1: 56 on 15/11/2026
    'commands': (
        'about',
        'assistant',
        'carport',
        'clean_screen',
        'compute',
        'default_layout',
        'delete',
        'empty',
        'export_csv',
        'export_dxf',
        'fill',
        'focus_checks',
        'manual',
        'measure_clear',
        'measure_distance',
        'measure_height',
        'new',
        'new_variant',
        'open',
        'ortho',
        'panel_checks',
        'panel_help',
        'panel_project',
        'panel_properties',
        'phase_consumption',
        'phase_model',
        'phase_plant',
        'phase_production',
        'phase_report',
        'preferences',
        'quit',
        'redo',
        'report_bug',
        'report_logo',
        'save',
        'save_as',
        'save_revision',
        'snaps',
        'tool_building',
        'tool_exclusion',
        'tool_measure',
        'tool_move',
        'tool_pitch',
        'tool_ridge',
        'tool_rotate',
        'tool_select',
        'tool_subfield',
        'toolbar_text',
        'undo',
        'view_3d',
        'view_align',
        'view_both',
        'view_plan',
        'whats_this',
        'zoom_in',
        'zoom_out',
    ),
    # settings shown in the Settings without an aid, a paragraph, a tour step or a description beside them (study 50, 3.2 counts go_to as a source, this guard does not): 27 after R699
    'settings': (
        'accent',
        'assistant_cloud_profiles',
        'assistant_consent',
        'assistant_height',
        'assistant_kokoro_dir',
        'assistant_kokoro_python',
        'assistant_voice',
        'assistant_voice_engine',
        'assistant_voice_name',
        'assistant_width',
        'background_year_wait_s',
        'backgrounds',
        'checks_view',
        'help_open',
        'map_sources',
        'memory_mode',
        'navigation',
        'orbit',
        'pivot',
        'pivot_hint',
        'reduced_motion',
        'report_profiles',
        'strings_view',
        'text_size',
        'theme',
        'toolbar_place',
        'veil',
    ),
    # fields propose_edit accepts without a name for the designer (study 50, 3.6: 49, every one of energy, consumption and economics): 49 on 15/11/2026
    'fields': (
        'consumption:annual_kwh',
        'consumption:contract_kw',
        'consumption:profile',
        'consumption:supply',
        'economics:battery_cost_per_kwh',
        'economics:battery_units',
        'economics:buy_f1',
        'economics:buy_f2',
        'economics:buy_f3',
        'economics:capex_per_kwp',
        'economics:capex_total',
        'economics:community',
        'economics:deduction_pct',
        'economics:degradation',
        'economics:discount',
        'economics:escalation',
        'economics:export_limit_kw',
        'economics:grant_pct',
        'economics:inverter_per_kw',
        'economics:inverter_year',
        'economics:opex_escalation',
        'economics:opex_per_kwp',
        'economics:pz',
        'economics:sell',
        'economics:shared_pct',
        'economics:storage_coupling',
        'economics:storage_efficiency_pct',
        'economics:trase',
        'economics:years',
        'economics:zone',
        'energy:dc_ac_ratio',
        'energy:inverter_maker',
        'energy:losses.ac_wiring',
        'energy:losses.albedo',
        'energy:losses.dc_wiring',
        'energy:losses.electrical_fraction',
        'energy:losses.electrical_shading',
        'energy:losses.iam_b0',
        'energy:losses.lid',
        'energy:losses.mismatch',
        'energy:losses.quality',
        'energy:losses.soiling',
        'energy:losses.transposition',
        'energy:losses.unavailability',
        'energy:losses.use_horizon',
        'energy:strings.auto',
        'energy:strings.n_series',
        'energy:strings.strategy',
        'energy:t_min',
    ),
    # checks of the strings without a why (study 50, 3.3: 39 of 64 keys): 40 on 15/11/2026
    'string_checks_without_why': (
        'connections',
        'connections_missing',
        'connector_imp',
        'connector_imp_missing',
        'connector_isc',
        'connector_isc_missing',
        'dcac',
        'generic_scope',
        'imbalance',
        'imp_missing',
        'imp_total',
        'isc_missing',
        'mlpe_count',
        'mlpe_energy',
        'mlpe_facings',
        'mlpe_groups',
        'mlpe_imp',
        'mlpe_inverter',
        'mlpe_isc',
        'mlpe_lengths',
        'mlpe_long_voc',
        'mlpe_mixed',
        'mlpe_parallel',
        'mlpe_partial',
        'mlpe_partial_parallel',
        'mlpe_partial_planes',
        'mlpe_partial_update',
        'mlpe_power',
        'mlpe_rules',
        'mlpe_spread',
        'mlpe_string_power',
        'mlpe_voc',
        'opt_orientations',
        'opt_pair_geometry',
        'opt_pairs',
        'opt_singles',
        'opt_suggested',
        'opt_unit_dc_max',
        'overload',
        'selv',
    ),
    # checks of the strings without a source on any of their places (study 50, 3.3: 22): 23 on 15/11/2026
    'string_checks_without_source': (
        'connections',
        'connections_missing',
        'connector_imp',
        'connector_imp_missing',
        'connector_isc',
        'connector_isc_missing',
        'dcac',
        'fuse',
        'fuserange',
        'generic_scope',
        'imbalance',
        'imp',
        'imp_missing',
        'isc',
        'isc_missing',
        'mlpe_groups',
        'mppt_high',
        'mppt_low',
        'overload',
        'range',
        'selv',
        'strings',
        'uoc',
    ),
    # checks of the panel without a why, their detail (study 50, 3.3: 7 of 39): 7 on 15/11/2026
    'panel_checks_without_why': (
        'core/rules/checks.py: String {name}: on no input of an inverter',
        'core/rules/checks.py: String {name}: {n} module is no longer laid (the layout changed)',
        'core/rules/checks.py: {inverter}, input {k}: {why}',
        'core/rules/checks.py: {n} modules in series, every check passed',
        'core/rules/checks.py: {n} string of power optimizers, every check passed',
        'core/rules/checks.py: {n} string on {m} inputs, every check passed',
        'core/rules/profiles/it/checks.py: Up to 11.08 kW the interface protection may be the one inside the inve',
    ),
    # checks of the panel without a source: the panel says «Meridiana» (study 50, 3.3: 17; here a text made in two places counts once): 16 on 15/11/2026
    'panel_checks_without_source': (
        "core/rules/checks.py: <energy.get('error_sim') or _('Compute the production to check the sha",
        'core/rules/checks.py: No sub-field yet: draw one on a roof or on the ground',
        'core/rules/checks.py: Prices and costs are indicative defaults: enter those of the bill and ',
        'core/rules/checks.py: String {name}: on no input of an inverter',
        'core/rules/checks.py: String {name}: {n} module is no longer laid (the layout changed)',
        'core/rules/checks.py: The consumption is guessed from the project: enter the bills or the PO',
        'core/rules/checks.py: The strings cannot be checked yet',
        'core/rules/checks.py: {inverter}, input {k}: {why}',
        'core/rules/checks.py: {name}: on two pitches, computed on pitch {n}',
        'core/rules/checks.py: {name}: rows by hand, not laid again by the automatic layout',
        'core/rules/checks.py: {name}: the layout could not be computed ({error})',
        'core/rules/checks.py: {name}: the modules are not laid yet',
        'core/rules/checks.py: {name}: {n} module set aside on an obstacle or off the roof',
        'core/rules/checks.py: {name}: {n} module taken out by hand is no longer in the layout',
        'core/rules/checks.py: {n} modules are in no string',
        'core/rules/profiles/it/checks.py: The inverter is sized by itself: choose one from the catalogue',
    ),
}


# ---------------------------------------------------------------- the AST, as the study's B-verifiche.py

def _name(func) -> str:
    return func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""


def _text(node) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "{..}" for v in node.values)
    if isinstance(node, ast.Call) and _name(node.func) in ("_", "N_", "ngettext") and node.args:
        return _text(node.args[0])
    if isinstance(node, ast.Call) and _name(node.func) in ("format", "replace") and isinstance(node.func, ast.Attribute):
        return _text(node.func.value)
    if isinstance(node, ast.IfExp):
        return _text(node.body) + " | " + _text(node.orelse)
    return "<" + ast.unparse(node) + ">"


def _arg(call, index, name):
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return call.args[index] if len(call.args) > index else None


def _empty(node) -> bool:
    return node is None or (isinstance(node, ast.Constant) and node.value in ("", None)) or (
        isinstance(node, ast.Tuple) and not node.elts)


def _core_files():
    for path in sorted((SRC / "core").rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        yield rel, ast.parse(path.read_text(encoding="utf-8"))


def panel_checks() -> dict[str, dict]:
    """The checks of the panel built in the code (rules.types.Item), the relays of other checks left out."""
    out = {}
    for rel, tree in _core_files():
        if rel in GENERIC_ONLY:
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and _name(node.func) == "Item") or len(node.args) < 3:
                continue
            text = _arg(node, 2, "text")
            words = ast.unparse(text) if text is not None else ""
            if "c.label" in words or "r.id" in words or words in ("note", "text") or "_(note)" in words:
                continue                # a check of the strings, a rule or a note relayed: judged where it is made
            key = f"{rel}: {_text(text)[:70]}"
            row = out.setdefault(key, {"source": True, "why": True})
            row["source"] &= not _empty(_arg(node, 3, "source"))
            row["why"] &= not _empty(_arg(node, 99, "detail"))
    return out


def _check_calls(tree, names=("Check", "_check", "add")):
    """The calls that make a check of the strings: a literal key first and at least four arguments."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _name(node.func) in names and len(node.args) >= 4 and isinstance(
                _arg(node, 0, "key"), (ast.Constant, ast.JoinedStr)):
            yield node


def string_checks() -> dict[str, dict]:
    """The checks of the strings by their key (the input's number left out): with a why, and with a source on at
    least one of the places that make it."""
    from meridiana.core.rules.profiles.it import checks as it_checks
    why = set(it_checks.string_why())
    out = {}
    for rel, tree in _core_files():
        if rel not in STRING_FILES:
            continue
        for node in _check_calls(tree):
            base = _text(_arg(node, 0, "key")).replace("{..}", "")
            for k in EXPANDED.get(base, (base,)):
                row = out.setdefault(k, {"source": False})
                row["source"] |= not _empty(_arg(node, 5, "source"))
                row["why"] = (k if k.startswith("opt_") else k.rstrip("0123456789")) in why
    return out


# ---------------------------------------------------------------- the settings, read from the Settings' schema

def _settings_schema():
    """SECTIONS, INTERNAL_FIELDS, the English labels and the keys with a description of gui/backend/settings_schema.py,
    read with the AST: the module imports the window's theme (Qt), this guard does not."""
    tree = ast.parse((SRC / "gui" / "backend" / "settings_schema.py").read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in (
                "SECTIONS", "INTERNAL_FIELDS"):
            found[node.targets[0].id] = ast.literal_eval(node.value)
        elif isinstance(node, ast.FunctionDef) and node.name == "labels":
            call = next(n for n in ast.walk(node) if isinstance(n, ast.Call) and _name(n.func) == "dict")
            found["labels"] = {kw.arg: _text(kw.value) for kw in call.keywords}
        elif isinstance(node, ast.FunctionDef) and node.name == "descriptions":
            mapping = next(n for n in ast.walk(node) if isinstance(n, ast.Dict))
            found["descriptions"] = {k.value for k in mapping.keys if isinstance(k, ast.Constant)}
    return found


# ---------------------------------------------------------------- the holes of today

def holes() -> dict[str, set[str]]:
    """Each family's items without their text, with the Italian catalogue loaded (the manual is Italian)."""
    from meridiana import i18n
    from meridiana.app.assistant import tools
    from meridiana.app.interface import help as helps, shortcuts, tour
    from meridiana.app.platform import config
    italian = i18n.translation_for("it")
    kept, i18n._translation = i18n._translation, italian
    try:
        manual = [fold(f"{heading} {text}") for _t, heading, text in tools.manual_passages(profile_id="it")]
        aids = [fold(f"{h.title} {h.short} {h.text}") for h in helps.texts(profile_id="it").values()]
        steps = [fold(" ".join([s.title, s.text, *s.points, s.hint])) for s in tour.steps(profile_id="it")]
        texts = manual + aids + steps
        commands = {c.id for c in shortcuts.commands() if not explained(c.text, texts)}
        schema = _settings_schema()
        settings = set()
        for keys in schema["SECTIONS"].values():
            for key in keys:
                label = italian.gettext(schema["labels"].get(key) or TABLE_TITLES.get(key, key))
                if key not in schema["descriptions"] and not explained(label, texts):
                    settings.add(key)
        shown = {k for keys in schema["SECTIONS"].values() for k in keys} | set(schema["INTERNAL_FIELDS"])
        undeclared = {f.name for f in dataclasses.fields(config.Config)} - shown
        fields = set()
        for kind in ("building", "subfield", "exclusion", *tools.SECTIONS):
            for path in tools.fields_of(kind, profile_id="it"):
                if tools.shown_label(kind, path) in (path, path.split(".")[-1]):
                    fields.add(f"{kind}:{path}")
    finally:
        i18n._translation = kept
    strings = string_checks()
    panel = panel_checks()
    return {
        "commands": commands,
        "settings": settings,
        "settings_undeclared": undeclared,
        "fields": fields,
        "string_checks_without_why": {k for k, v in strings.items() if not v["why"]},
        "string_checks_without_source": {k for k, v in strings.items() if not v["source"]},
        "panel_checks_without_why": {k for k, v in panel.items() if not v["why"]},
        "panel_checks_without_source": {k for k, v in panel.items() if not v["source"]},
    }


class Knowledge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.found = holes()

    def test_no_new_item_without_its_text(self):
        new = {family: sorted(ids - set(DEBITI.get(family, ()))) for family, ids in self.found.items()}
        new = {family: ids for family, ids in new.items() if ids}
        self.assertEqual(new, {}, "items without the text that explains them (see the docstring): write their aid, "
                                  "manual paragraph, name or source; never add them to DEBITI")

    def test_the_debts_paid_leave_the_list(self):
        paid = {family: sorted(set(ids) - self.found.get(family, set())) for family, ids in DEBITI.items()}
        paid = {family: ids for family, ids in paid.items() if ids}
        self.assertEqual(paid, {}, "debts paid: take these lines out of DEBITI")

    def test_a_new_command_and_a_new_field_without_their_text_are_seen(self):
        from unittest import mock
        from meridiana.app.assistant import tools
        from meridiana.app.interface import shortcuts
        real = shortcuts.commands
        extra = shortcuts.Command("spin_the_sun", "Fai girare il sole al contrario", (), "view")
        table = dict(tools.EDITABLE["subfield"], **{"params.wobble": tools.NUMBER})
        with mock.patch.object(shortcuts, "commands", lambda: [*real(), extra]), \
                mock.patch.dict(tools.EDITABLE, {"subfield": table}):
            found = holes()
        self.assertIn("spin_the_sun", found["commands"] - set(DEBITI["commands"]))
        self.assertIn("subfield:params.wobble", found["fields"] - set(DEBITI["fields"]))

    def test_every_file_that_makes_checks_of_the_strings_is_read(self):
        makers = {rel for rel, tree in _core_files() if any(_check_calls(tree, ("Check",)))}
        self.assertEqual(sorted(makers - STRING_FILES - GENERIC_ONLY), [], "add the file to STRING_FILES")

    def test_the_guard_sees_what_it_is_written_for(self):
        """The guard is not empty by construction: it reads every family, and a name without a text is seen."""
        from meridiana.app.interface import shortcuts
        self.assertGreater(len(shortcuts.commands()), 90)
        self.assertGreater(len(string_checks()), 50)
        self.assertGreater(len(panel_checks()), 30)
        self.assertGreater(sum(len(v) for v in _settings_schema()["SECTIONS"].values()), 50)
        self.assertFalse(explained("Rotazione bizzarra del cosmo", ["la rotazione del modello"]))
        self.assertTrue(explained("Ruota il modello", ["ruotare il modello di novanta gradi"]))
        self.assertFalse(explained("Annulla", ["annulla l'ultima modifica"]))     # one word: weak


def _print_holes() -> None:
    found = holes()
    print("DEBITI: dict[str, tuple[str, ...]] = {")
    for family, ids in found.items():
        print(f"    # {len(ids)}")
        print(f"    {family!r}: (")
        for i in sorted(ids):
            print(f"        {i!r},")
        print("    ),")
    print("}")


if __name__ == "__main__":
    if "--print" in sys.argv or len(sys.argv) == 1:
        _print_holes()
    else:
        unittest.main()
