"""The key of the energy year is made in one place, app/year_key.py (revision r30, finding 3).

Two guards. The paths the program takes to the key (the session, the layouts' job, the fingerprint of the kept year
and of the report, what changed) give the same key on the same project. And in the sources the bricks of the key are
made only in their module: the layout keys of the filled sub-fields and the year's inputs in app/year_key.py, what
casts the shadows in Project.shadow_casters. A property of the window that built the key by itself again (as
charts_controller and energy_outdated did before) makes the second one red, with its file and line."""

import ast
import copy
import unittest
from pathlib import Path

import _setup  # noqa: F401
from _fixtures import capannone

SRC = Path(__file__).resolve().parents[2] / "src" / "meridiana"
YEAR_KEY = "app/year_key.py"
MODEL = "core/model/model.py"


def _names(node) -> set[str]:
    """The attribute and plain names read inside a node."""
    return {n.attr if isinstance(n, ast.Attribute) else n.id for n in ast.walk(node)
            if isinstance(n, (ast.Attribute, ast.Name))}


def _calls(node) -> set[str]:
    return {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
            for n in ast.walk(node) if isinstance(n, ast.Call)}


def bricks(source: str) -> list[tuple[int, str]]:
    """Where a source makes a brick of the year's key: (line, which)."""
    out = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name != "layout_state":
            # the layout key of every filled sub-field, by a comprehension or by a loop (layout_state: one sub-field)
            if "layout_key" in _calls(node) and "filled" in _names(node):
                out.append((node.lineno, "layout keys of the filled sub-fields"))
        if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            calls, names = _calls(node), _names(node)
            if "geometry_key" in calls and "buildings" in names:
                out.append((node.lineno, "the buildings that cast shadows"))
            if "ELECTRICAL" in names and "get" in calls:
                out.append((node.lineno, "the wiring of the sub-fields"))
        if isinstance(node, ast.List) and len(node.elts) == 4 and all(isinstance(e, ast.Attribute) for e in node.elts) \
                and [e.attr for e in node.elts] == ["ring", "kind", "height", "building"]:
            out.append((node.lineno, "the obstacles that cast shadows"))
        if isinstance(node, ast.Call):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if name == "fingerprint_of":
                out.append((node.lineno, "the mark of a key"))
            if name == "energy_key" and (node.args or node.keywords):
                out.append((node.lineno, "the key on layout keys made by the caller"))
    return out


# where each brick belongs: its one place
HOME = {"layout keys of the filled sub-fields": {YEAR_KEY}, "the wiring of the sub-fields": {YEAR_KEY},
        "the mark of a key": {YEAR_KEY}, "the key on layout keys made by the caller": {"app/session.py"},
        "the buildings that cast shadows": {MODEL}, "the obstacles that cast shadows": {MODEL}}


class OnePlaceInTheSources(unittest.TestCase):
    def test_the_bricks_of_the_key_are_made_only_in_their_module(self):
        stray, found = [], {}
        for path in sorted(SRC.rglob("*.py")):
            rel = path.relative_to(SRC).as_posix()
            for line, which in bricks(path.read_text(encoding="utf-8-sig")):
                found.setdefault(which, []).append(rel)
                if rel not in HOME[which]:
                    stray.append(f"{rel}:{line}: {which} (its place: {', '.join(sorted(HOME[which]))})")
        self.assertEqual(stray, [], "\n" + "\n".join(stray))
        # each brick is still made at home: the guard looks at the right thing
        self.assertEqual({k: set(v) for k, v in found.items()}, HOME)

    def test_the_guard_sees_the_copies_it_was_written_for(self):
        """Controprova: the code of before r32-centrale (charts_controller, session.energy_outdated, the worker that
        keeps the year, checks.in_shade) is red."""
        before = '''
def inputs_changed(self):
    keys = {sf.id: project.layout_key(sf) for sf in project.subfields if sf.filled}
    return self._session.energy_key(keys) != self._computed_key

def worker(session, cache, fingerprint):
    year_store.write(cache, fingerprint, session.energy_key(session._expected_keys()))

def in_shade(project, sf):
    return [project.layout_key(sf), [b.geometry_key() for b in project.buildings],
            [[e.ring, e.kind, e.height, e.building] for e in project.exclusions]]

def mark(text):
    return year_store.fingerprint_of(text)
'''
        self.assertEqual(sorted(w for _l, w in bricks(before)),
                         sorted(["layout keys of the filled sub-fields", "the key on layout keys made by the caller",
                                 "the key on layout keys made by the caller", "the buildings that cast shadows",
                                 "the obstacles that cast shadows", "the mark of a key"]))


class TheSameKeyByEveryPath(unittest.TestCase):
    def test_the_paths_to_the_key_agree_on_one_project(self):
        from meridiana.app import jobs, year_key
        from meridiana.app.session import ProjectSession
        from meridiana.data import year_store
        session = ProjectSession(capannone())
        p = session.project
        expected = year_key.expected(p)
        # the layouts' job gives the keys the year is asked on
        results, keys, _laid = jobs.layout_of(copy.deepcopy(p))
        self.assertTrue(keys)
        self.assertEqual(keys, year_key.layout_keys(p))
        self.assertEqual(keys, session.expected_layout_keys())
        self.assertEqual(session.expected_key(), expected)
        self.assertEqual(session.energy_key(keys), expected)
        session.layout_done(session.generation, results, keys)
        self.assertEqual(session.energy_key(), expected)            # on the layouts in hand
        # the mark: the kept year's name (shell_compute), the report's (report.py), the yearState's
        self.assertEqual(session.year_fingerprint(), year_key.fingerprint(expected))
        self.assertEqual(session.year_fingerprint(), year_store.fingerprint_of(expected))
        # a year asked and come back answers for the project: up to date, nothing changed, the same parts
        generation = session.energy_asked(session.expected_layout_keys())
        self.assertTrue(session.energy_done(generation, {"sim": None}))
        self.assertEqual(session.energy_key_computed, expected)
        self.assertFalse(session.energy_outdated())
        self.assertFalse(session.energy_stale())
        self.assertEqual(session.year_changes(), [])
        self.assertEqual(session._year_parts(), year_key.parts(p, keys))
        # a copy of the project (the computation's process) gives the same key
        self.assertEqual(year_key.expected(copy.deepcopy(p)), expected)
        # what casts the shadows is the same brick in the layout's key, the year's and the checks'
        self.assertEqual({k: v for k, v in year_key.inputs(p, keys)["shade"].items() if k in ("buildings", "obstacles")},
                         p.shadow_casters())
        # and a change of the plant changes them all together
        p.buildings[0].height += 1.0
        self.assertTrue(session.energy_outdated())
        self.assertNotEqual(session.expected_key(), expected)
        self.assertNotEqual(session.year_fingerprint(), year_key.fingerprint(expected))


if __name__ == "__main__":
    unittest.main()
