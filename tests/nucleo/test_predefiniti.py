"""The defaults of the computations have one definition each (revision r30, finding 10).

What a country decides sits in its profile's table (core/rules/profiles/<id>/defaults.py, study 44); what is the same
everywhere in core/rules/profiles/common.py; the defaults of the energy side that no profile chooses (the loss chain,
the DC/AC ratio, the strategy of the strings, the design cold, the light-induced degradation) in the schema,
core/model/settings.py. Two guards: every path that reads a default (the schema, the classes of the computation, the
profile, the assistant, the plant's page) gives the same value; and no source writes again one of those numbers next
to the key it belongs to."""

import ast
import dataclasses
import unittest
from pathlib import Path

import _setup  # noqa: F401

from meridiana.core.model import settings
from meridiana.core.rules import registry

SRC = Path(__file__).resolve().parents[2] / "src" / "meridiana"


def _initial(kls) -> dict:
    return {f.name: (f.default if f.default is not dataclasses.MISSING else f.default_factory())
            for f in dataclasses.fields(kls) if f.name != "defaults"}


class EveryPathTheSameValue(unittest.TestCase):
    def test_the_profiles_share_the_common_table(self):
        from meridiana.core.rules.profiles import common
        for pid in registry.ids():
            for section, table in (("economics", common.ECONOMICS), ("consumption", common.CONSUMPTION)):
                values = registry.get(pid).defaults(section)
                self.assertEqual({k: values[k] for k in table}, table, (pid, section))

    def test_schema_computation_and_profile_agree(self):
        from meridiana.core.energy import consumption, economics, simulate
        self.assertEqual(_initial(settings.Losses), _initial(simulate.Losses))
        self.assertEqual(dataclasses.asdict(simulate.Losses.from_dict({})), _initial(settings.Losses))
        for pid in registry.ids():
            profile = registry.get(pid)
            for section, kls, runtime in (("consumption", settings.ConsumptionSettings, consumption.Consumption),
                                          ("economics", settings.EconomicsSettings, economics.Settings)):
                wanted = profile.defaults(section)
                self.assertEqual(settings.initial_values(kls, pid), wanted, (pid, section))
                read = dataclasses.asdict(settings.from_dict(kls, {}, profile_id=pid))
                self.assertEqual(read, {**_initial(kls), **wanted}, (pid, section))
                got = dataclasses.asdict(runtime.from_dict({}, profile_id=pid))
                got.pop("defaults", None)
                self.assertEqual(got, read, (pid, section))

    def test_the_energy_side_reads_the_schema(self):
        from meridiana.core.energy import components, plant, simulate, stringing, system
        from meridiana.core.model import model
        ratio = settings.EnergySettings.dc_ac_ratio
        self.assertEqual(ratio, settings.EnergySettings().dc_ac_ratio)
        p = model.Project()
        spec = system.inverters_of(p, 50000.0)[0]
        self.assertEqual(spec.pac, components.InverterSpec.sized_for(50000.0, ratio).pac)
        self.assertEqual(spec.pac, components.InverterSpec.sized_for(50000.0).pac)
        from meridiana.i18n import number
        self.assertIn(number(ratio, 2), system.describe({}))
        self.assertEqual(plant.DESIGN_COLD, settings.DESIGN_COLD)
        self.assertEqual(plant.Plant().t_min, settings.DESIGN_COLD)
        self.assertEqual(plant.Plant().strategy, settings.Strings.strategy)
        self.assertEqual(plant.conditions(p).t_min, settings.DESIGN_COLD)
        self.assertEqual(simulate.lid_pct(simulate.Losses()), settings.LID_FALLBACK)
        self.assertIs(stringing.DESIGN_COLD, settings.DESIGN_COLD)

    def test_the_assistant_reads_the_profile_defaults_as_the_schema(self):
        """The assistant's fields (their kind from the default) take the defaults of settings.initial_values."""
        from meridiana.app.assistant import tools
        source = Path(tools.__file__).read_text(encoding="utf-8")
        self.assertNotIn('.defaults("economics")', source)
        self.assertNotIn('.defaults("consumption")', source)
        for pid in registry.ids():
            fields = tools._section_fields("economics", profile_id=pid)
            self.assertEqual(fields["years"], tools.WHOLE)
            self.assertEqual(fields["discount"], tools.NUMBER)


# a default written again, by its key: a dictionary read with a number after it, the number of the schema
WRITTEN_AGAIN = {"dc_ac_ratio": settings.EnergySettings.dc_ac_ratio, "dc_ac": settings.EnergySettings.dc_ac_ratio,
                 "t_min": settings.DESIGN_COLD, "strategy": settings.Strings.strategy}
# where a value of the common table or of the schema may be written: its own home
HOMES = {"core/model/settings.py", "core/rules/profiles/common.py"}


def written_again(source: str, profile: bool = True) -> list[tuple[int, str]]:
    """`x.get("key", value)`, `x.get("key") or value`, `key: type = value` and `key=value` defaults with the schema's
    value for one of WRITTEN_AGAIN; and, in a profile (`profile`), the keys of the common table with its value."""
    from meridiana.core.rules.profiles import common
    shared = {**common.ECONOMICS, **common.CONSUMPTION}
    out = []

    def same(node, value) -> bool:
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            return isinstance(node.operand.value, (int, float)) and -node.operand.value == value
        return isinstance(node, ast.Constant) and type(node.value) is not bool and node.value == value

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" \
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value in WRITTEN_AGAIN:
            key = node.args[0].value
            if len(node.args) > 1 and same(node.args[1], WRITTEN_AGAIN[key]):
                out.append((node.lineno, key))
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or) and len(node.values) == 2:
            first = node.values[0]
            if isinstance(first, ast.Call) and isinstance(first.func, ast.Attribute) and first.func.attr == "get" \
                    and first.args and isinstance(first.args[0], ast.Constant) \
                    and first.args[0].value in WRITTEN_AGAIN and same(node.values[1], WRITTEN_AGAIN[first.args[0].value]):
                out.append((node.lineno, first.args[0].value))
        if isinstance(node, ast.arguments):
            names = node.posonlyargs + node.args
            for arg, default in zip(names[len(names) - len(node.defaults):], node.defaults, strict=True):
                if arg.arg in ("ratio", "strategy", "t_min") and same(
                        default, {"ratio": WRITTEN_AGAIN["dc_ac_ratio"], "strategy": WRITTEN_AGAIN["strategy"],
                                  "t_min": WRITTEN_AGAIN["t_min"]}[arg.arg]):
                    out.append((default.lineno, arg.arg))
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None \
                and node.target.id in ("strategy", "t_min", "dc_ac_ratio") and same(
                    node.value, WRITTEN_AGAIN[node.target.id]):
            out.append((node.lineno, node.target.id))
        if profile and isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values, strict=True):
                if isinstance(k, ast.Constant) and k.value in shared and same(v, shared[k.value]):
                    out.append((node.lineno, k.value))
        if profile and isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "update":
            for kw in node.keywords:
                if kw.arg in shared and same(kw.value, shared[kw.arg]):
                    out.append((node.lineno, kw.arg))
    return out


class NoCopyInTheSources(unittest.TestCase):
    FOLDERS = ("core/energy", "core/rules", "core/model", "app/assistant", "app/report", "app/profiles",
               "gui/backend")

    def test_no_default_is_written_again(self):
        stray = []
        for folder in self.FOLDERS:
            for path in sorted((SRC / folder).rglob("*.py")):
                rel = path.relative_to(SRC).as_posix()
                if rel in HOMES:
                    continue
                stray += [f"{rel}:{line}: {key}" for line, key in written_again(
                    path.read_text(encoding="utf-8-sig"), rel.startswith("core/rules/profiles/"))]
        self.assertEqual(stray, [], "\n" + "\n".join(stray))

    def test_the_guard_sees_the_copies_it_was_written_for(self):
        """Controprova: the code of before r32-centrale is red."""
        before = '''
def settings(e, s):
    return dict(strategy=s.get('strategy', 'serpentine'), dc_ac=e.get('dc_ac_ratio') or 1.1, t_min=e.get('t_min', -10))
def proposed(options):
    return ('dc_ac_ratio', options.get('dc_ac', 1.1))
def sized_for(cls, dc_stc_w, ratio=1.1):
    pass
ECONOMICS = {'years': 25, 'discount': 4.0, 'inverter_year': 12}
values.update(years=25, discount=4.0, escalation=2.0, export_limit_kw=-1.0)
'''
        self.assertEqual(sorted(k for _l, k in written_again(before)),
                         sorted(["strategy", "dc_ac_ratio", "t_min", "dc_ac", "ratio", "years", "discount",
                                 "inverter_year", "years", "discount", "escalation", "export_limit_kw"]))


if __name__ == "__main__":
    unittest.main()
