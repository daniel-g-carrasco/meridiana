"""R389 command-boundary differential tests, never a substitute for gesture tests.

Adapters call the existing frontends' handlers. An unsupported command or observation
is a missing capability, never implemented here with a core mutation. Other branches
can register their real handlers in ``commands`` and their observations in ``observe``.
Project snapshots are the complete save payload, except the wall-clock ``modified``.
They do not claim that Quick has actually saved a file: that is a separate capability.
"""
from __future__ import annotations

import dataclasses
import json
import math
from collections.abc import Mapping
from datetime import date, datetime
from pathlib import Path

import _setup


class MissingCommand(RuntimeError):
    """A frontend has no implemented command or observable result."""


def connected_fixture():
    """Common input, not a command: recorded-weather journey must produce nonzero energy."""
    from _fixtures import capannone, inverter_record
    from meridiana import jobs
    project = capannone()
    results, _, _ = jobs.layout_of(project)
    keys = [f"s1/{m.key}" for m in results["s1"].modules]
    project.energy = {"inverters": [{"record": inverter_record(), "count": 2, "name": "Test"}],
                      "strings": {"auto": False, "runs": [
                          {"inverter": 1 + i // 2, "mppt": 1 + i % 2, "modules": keys[i * 20:(i + 1) * 20]}
                          for i in range(4)]}}
    project.consumption = {"annual_kwh": 40000.}
    project.economics = {"capex_total": 45000., "battery": {
        "manufacturer": "Fixture", "model": "AC20", "usable_energy_kwh": 20.,
        "max_charge_power_w": 10000., "max_discharge_power_w": 10000., "round_trip_efficiency_pct": 90.}}
    return project


def normalized(value):
    """Make numerical result objects JSON-compatible without dropping fields."""
    import numpy as np
    import pandas as pd
    if isinstance(value, pd.Index):
        return [normalized(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return {"index": [str(i) for i in value.index], "columns": list(value.columns),
                "values": normalized(value.to_numpy())}
    if isinstance(value, pd.Series):
        return {"index": [str(i) for i in value.index], "values": normalized(value.to_numpy())}
    if dataclasses.is_dataclass(value):
        return normalized({f.name: getattr(value, f.name) for f in dataclasses.fields(value)})
    if isinstance(value, Mapping):
        return {str(k): normalized(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, np.ndarray)):
        return [normalized(v) for v in value]
    if isinstance(value, (set, frozenset)):
        return sorted((normalized(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True))
    if hasattr(value, "__geo_interface__"):
        return normalized(value.__geo_interface__)
    if isinstance(value, np.generic):
        return normalized(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return {"nonfinite": str(value)}
    if isinstance(value, Path):
        return str(value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"No parity serializer for {type(value).__name__}")


def canonical_project(project):
    data = project.to_json()
    data.pop("modified", None)  # Each real save stamps its own wall-clock time.
    return normalized(data)


def compare(left, right, path="$", *, relative=1e-10, absolute=1e-9):
    """All differences, including missing keys and list order; tolerances in SI units."""
    if isinstance(left, dict) and isinstance(right, dict):
        out = []
        for key in sorted(left.keys() | right.keys()):
            at = f"{path}.{key}"
            if key not in left or key not in right:
                out.append({"path": at, "widgets": left.get(key), "quick": right.get(key),
                            "missing": "Widgets" if key not in left else "Quick"})
            else:
                out.extend(compare(left[key], right[key], at, relative=relative, absolute=absolute))
        return out
    if isinstance(left, list) and isinstance(right, list):
        out = []
        if len(left) != len(right):
            out.append({"path": path + ".length", "widgets": len(left), "quick": len(right)})
        for i, (a, b) in enumerate(zip(left, right, strict=False)):
            out.extend(compare(a, b, f"{path}[{i}]", relative=relative, absolute=absolute))
        return out
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) \
            and not isinstance(left, bool) and not isinstance(right, bool):
        equal = math.isclose(left, right, rel_tol=relative, abs_tol=absolute)
    else:
        equal = type(left) is type(right) and left == right
    return [] if equal else [{"path": path, "widgets": left, "quick": right}]


def undo_snapshot(session):
    undo = session.undo
    return {"undo": undo.undo_text(), "redo": undo.redo_text(), "index": undo.index,
            "count": undo.count(), "canUndo": undo.can_undo(), "canRedo": undo.can_redo()}


class Adapter:
    def __init__(self, name, commands, observe, settle=lambda: None):
        self.name, self.commands = name, dict(commands)
        self.observe, self.settle = observe, settle

    def execute(self, command, **arguments):
        if command not in self.commands:
            raise MissingCommand(f"{self.name}:{command}")
        result = self.commands[command](**arguments)
        self.settle()
        return result


def run_scenario(scenario, widgets, quick):
    """Run both sides only when both support the complete journey; record each step.

    Preflight prevents a missing early gesture from making later steps meaningless.
    A caller must treat ``missing``, ``different`` and ``error`` as incomplete parity.
    """
    result = {"scenario": scenario["id"], "status": "equal", "steps": [], "missing": []}
    for step in scenario["steps"]:
        for side in (widgets, quick):
            if step["command"] not in side.commands:
                missing = f"{side.name}:{step['command']}"
                if missing not in result["missing"]:
                    result["missing"].append(missing)
    if result["missing"]:
        result["status"] = "missing"
        return result
    for step in scenario["steps"]:
        try:
            for side in (widgets, quick):
                side.execute(step["command"], **step.get("args", {}))
            left, right = widgets.observe(), quick.observe()
            differences = []
            for key in scenario.get("observations", ["project", "undo"]):
                if key not in left or key not in right:
                    for side, snapshot in ((widgets, left), (quick, right)):
                        if key not in snapshot:
                            result["missing"].append(f"{side.name}:observation:{key}")
                else:
                    differences.extend(compare(left[key], right[key], f"$.{key}"))
            result["steps"].append({"command": step["command"], "differences": differences})
            if differences:
                result["status"] = "different"
        except MissingCommand as error:
            result["missing"].append(str(error))
            break
        except Exception as error:  # Evidence must retain the real failing frontend exception.
            result.update(status="error", error=f"{type(error).__name__}: {error}")
            return result
    if result["missing"]:
        result["status"] = "missing"
    return result


class QuickAdapter(Adapter):
    """Current QML Bridge slots, including its actual asynchronous worker."""
    def __init__(self, project, cache, app):
        from meridiana.quick.bridge import Bridge
        self.bridge = Bridge(project, cache)
        self.session, self.app = self.bridge.session, app
        bridge = self.bridge
        super().__init__("Quick", {
            "select": lambda kind, oid: bridge.select(kind, oid, ""),
            "rename": bridge.rename, "height": bridge.setHeight,
            "building": bridge.rectangle, "resize": bridge.resizeRectangle,
            "undo": bridge.undo, "redo": bridge.redo, "calculate": bridge.recompute,
        }, self.snapshot, self.wait)

    def wait(self):
        if not _setup.wait_until(self.app, lambda: not self.bridge.busy, 90):
            raise TimeoutError("Quick layout, checks or year did not finish")

    def snapshot(self):
        out = {"project": canonical_project(self.session.project), "undo": undo_snapshot(self.session),
               "messages": {"error": self.bridge.error}, "checks": normalized(self.bridge.checkRows)}
        if self.session.energy:
            out["year"] = normalized(self.session.energy)
        return out

    def close(self):
        self.bridge.close()


class WidgetsAdapter(Adapter):
    """Existing MainWindow command handlers. No mirrored implementation of edits."""
    def __init__(self, window, app):
        self.window, self.session, self.app = window, window.session, app
        w = window
        super().__init__("Widgets", {
            "select": w._select,
            "rename": lambda value: w._rename(*w.selection, name=value),
            "height": lambda value: w._edited(*w.selection, {"height": value}),
            "building": lambda x1, y1, x2, y2: w._drawn("building", [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]),
            "resize": lambda oid, x1, y1, x2, y2: w._edited("building", oid, {
                "footprint": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]}),
            # Properties._roof_group sends retyped(): slope/covering and edge reset too.
            "roof": lambda oid, kind: w._edited("building", oid, w.project.building(oid).retyped(kind)),
            "subfield": lambda ring: w._drawn("subfield", ring),
            "exclusion": lambda ring: w._drawn("exclusion", ring),
            "layout": lambda: w._fill_selected(True),
            "row": w._row_drawn,
            "move": lambda kind, oid, dx, dy: w._transform(kind, oid, {"mode": "move", "dx": dx, "dy": dy}),
            "rotate": lambda kind, oid, cx, cy, degrees: w._transform(kind, oid, {
                "mode": "rotate", "cx": cx, "cy": cy, "degrees": degrees}),
            "undo": w.undo.undo, "redo": w.undo.redo,
            "calculate": self.calculate,
            "automatic_strings": w._strings_propose,
            "manual_strings": self.manual_strings,
            "inverters": self.inverters,
            "variants": self.variant,
            "battery": lambda value: w._energy_edited("economics", "battery", value),
            "consumption": lambda value: w._energy_edited("consumption", "annual_kwh", value),
            "economics": lambda value: w._energy_edited("economics", "capex_total", value),
            "report": w._report_data,
            "save": self.save,
        }, self.snapshot, self.wait)

    def wait(self):
        w = self.window
        if not _setup.wait_until(self.app, lambda: w._layouts_settled() and not w.plant_pending()
                                 and w.string_proposal_job is None, 90):
            raise TimeoutError("Widgets layout or plant did not finish")
        # Energy is an explicit journey; do not accidentally launch a second year between edits.
        w.energy_timer.stop()

    def calculate(self):
        w = self.window
        w._compute_energy(False)
        if not _setup.wait_until(self.app, lambda: bool(w.session.energy) and not w.session.energy_stale(), 90):
            raise TimeoutError("Widgets year did not finish")

    def variant(self, name):
        from unittest.mock import patch
        from PySide6.QtWidgets import QInputDialog
        # Supply only the dialog answer; execute the real variant command.
        with patch.object(QInputDialog, "getText", return_value=(name, True)):
            self.window._new_variant()

    def inverters(self, count):
        from _fixtures import inverter_record
        from meridiana.i18n import _
        self.window._add_inverter(inverter_record(), _("Add an inverter from the catalogue"))
        self.window._inverter_count(0, count)

    def manual_strings(self, unit, mppt, count):
        modules = [[sid, m.key] for sid, layout in self.session.good_results().items() for m in layout.modules][:count]
        if len(modules) != count:
            raise ValueError("The scenario needs more laid modules")
        self.window._new_string(unit, mppt)
        if self.window.draft_target is None:
            raise RuntimeError("Widgets did not enter manual string drawing")
        self.window._draft_finished(modules)

    def save(self, path):
        target = Path(path)
        if target.exists():
            raise FileExistsError(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.window.path = target
        if not self.window._save():
            raise OSError("Widgets save was refused")

    def snapshot(self):
        w = self.window
        out = {"project": canonical_project(self.session.project), "undo": undo_snapshot(self.session),
               "checks": normalized(w.checks_page.items),
               "messages": {"status": w.statusBar().currentMessage(), "hint": w.hint.text()},
               "report": normalized(w._report_data())}
        if self.session.energy:
            out["year"] = normalized(self.session.energy)
        return out


def _scenario(name, command=None, args=None, *, steps=None, observations=None):
    return {"id": name, "requests": ["R389"],
            "steps": steps or [{"command": command or name, "args": args or {}}],
            "observations": observations or ["project", "undo"]}


COMMAND_SCENARIOS = [
    _scenario("building", args={"x1": 60., "y1": 0., "x2": 75., "y2": 12.}),
    _scenario("roof", args={"oid": "b1", "kind": "gable"}),
    _scenario("subfield", args={"ring": [[2, 2], [15, 2], [15, 10], [2, 10]]}),
    _scenario("layout", steps=[{"command": "subfield", "args": {"ring": [[2, 2], [15, 2], [15, 10], [2, 10]]}},
                               {"command": "select", "args": {"kind": "subfield", "oid": "s2"}},
                               {"command": "layout"}]),
    _scenario("exclusion", args={"ring": [[18, 8], [20, 8], [20, 10], [18, 10]]}),
    _scenario("row", args={"start": [4., 4.], "end": [15., 4.]}),
    _scenario("move", args={"kind": "building", "oid": "b1", "dx": 3., "dy": 2.}),
    _scenario("rotate", args={"kind": "building", "oid": "b1", "cx": 20., "cy": 10., "degrees": 15.}),
    _scenario("undo_redo", steps=[{"command": "select", "args": {"kind": "building", "oid": "b1"}},
                                  {"command": "height", "args": {"value": 11.5}},
                                  {"command": "undo"}, {"command": "redo"}]),
    _scenario("variants", args={"name": "Alternativa Est"}),
    _scenario("automatic_strings", steps=[{"command": "inverters", "args": {"count": 2}},
                                           {"command": "automatic_strings", "args": {"strategy": "serpentine"}}]),
    _scenario("manual_strings", steps=[{"command": "inverters", "args": {"count": 2}},
                                        {"command": "manual_strings", "args": {"unit": 1, "mppt": 1, "count": 20}}]),
    _scenario("inverters", args={"count": 2}),
    _scenario("battery", args={"value": {"manufacturer": "Fixture", "model": "AC20", "usable_energy_kwh": 20.,
                                          "max_charge_power_w": 10000., "max_discharge_power_w": 10000.,
                                          "round_trip_efficiency_pct": 90.}}),
    _scenario("consumption", args={"value": 40000.}),
    _scenario("economics", args={"value": 45000.}),
    _scenario("recorded_year", "calculate", observations=["project", "checks", "year", "messages"]),
    _scenario("report", observations=["report"]),
    _scenario("save", args={"path": "parity-output.mer"}),
]


def write_evidence(path, results):
    """Write a new evidence file; never silently replace an earlier run."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump({"scope": "frontend command boundary, not mouse/keyboard gestures", "results": results},
                  stream, ensure_ascii=False, indent=2, allow_nan=False)
