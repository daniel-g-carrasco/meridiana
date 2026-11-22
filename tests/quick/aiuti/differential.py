"""Project snapshots and their comparison, for the Quick's tests (once R389's Widgets/Quick parity helpers).

Project snapshots are the complete save payload, except the wall-clock ``modified``. An adapter calls the real
handlers of the Quick; a command it does not have is a ``MissingCommand``, never a core mutation done here.
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
    from meridiana.app import jobs
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
    raise TypeError(f"No snapshot serializer for {type(value).__name__}")


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
                out.append({"path": at, "left": left.get(key), "right": right.get(key),
                            "missing": "left" if key not in left else "right"})
            else:
                out.extend(compare(left[key], right[key], at, relative=relative, absolute=absolute))
        return out
    if isinstance(left, list) and isinstance(right, list):
        out = []
        if len(left) != len(right):
            out.append({"path": path + ".length", "left": len(left), "right": len(right)})
        for i, (a, b) in enumerate(zip(left, right, strict=False)):
            out.extend(compare(a, b, f"{path}[{i}]", relative=relative, absolute=absolute))
        return out
    if isinstance(left, (int, float)) and isinstance(right, (int, float)) \
            and not isinstance(left, bool) and not isinstance(right, bool):
        equal = math.isclose(left, right, rel_tol=relative, abs_tol=absolute)
    else:
        equal = type(left) is type(right) and left == right
    return [] if equal else [{"path": path, "left": left, "right": right}]


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


class QuickAdapter(Adapter):
    """Current QML Bridge slots, including its actual asynchronous worker."""
    def __init__(self, project, cache, app):
        from meridiana.gui.bridge import Bridge
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
