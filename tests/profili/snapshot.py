"""Explicit acquisition and exact verification of the pre-extraction Italian outputs.

Acquire once, before changing src: python -m profili.snapshot --capture
Tests only read references. Numeric comparisons use exact equality in this environment.
No list of modules, checks, paragraphs or chapters is sorted for comparison.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
import importlib.metadata
import importlib
import io
import hashlib
import json
import math
from pathlib import Path
import platform
from types import SimpleNamespace
import subprocess
import sys
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd
import _setup  # noqa: F401
from _fixtures import clear_sky_meteo, write_cache
from profili import fixtures as F
from profili import leaks

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = Path(__file__).parent / "riferimenti" / "it"


class Encoder:
    def __init__(self):
        self.arrays = {}

    def encode(self, value):
        if isinstance(value, np.ndarray):
            if value.dtype.kind == "O":
                return {"object_array": self.encode(value.tolist()), "shape": list(value.shape)}
            key = f"array_{len(self.arrays):05d}"
            self.arrays[key] = value
            return {"array": key, "shape": list(value.shape), "dtype": str(value.dtype)}
        if isinstance(value, pd.DataFrame):
            return {"index": self.encode(value.index), "columns": list(value.columns),
                    "data": [self.encode(value[c].to_numpy()) for c in value.columns]}
        if isinstance(value, pd.Series):
            return {"index": self.encode(value.index), "name": value.name, "data": self.encode(value.to_numpy())}
        if isinstance(value, pd.DatetimeIndex):
            return {"timestamp_ns": self.encode(value.asi8), "timezone": str(value.tz),
                    "local_iso": [t.isoformat() for t in value]}
        if isinstance(value, pd.Index):
            return self.encode(value.tolist())
        if isinstance(value, np.generic):
            return self.encode(value.item())
        if isinstance(value, float) and not math.isfinite(value):
            return {"nonfinite": str(value)}
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, dict):
            if all(isinstance(k, str) for k in value):
                return {k: self.encode(v) for k, v in value.items()}
            return {"mapping": [[self.encode(k), self.encode(v)] for k, v in value.items()]}
        if isinstance(value, (list, tuple)):
            return [self.encode(v) for v in value]
        if isinstance(value, (set, frozenset)):
            return {"set": [self.encode(v) for v in sorted(value)]}
        if is_dataclass(value):
            return {f.name: self.encode(getattr(value, f.name)) for f in fields(value)
                    if not (type(value).__name__ == "Facts" and f.name == "profile_id")
                    and not (type(value).__name__ == "ModuleSpec" and f.name == "declared_inputs")
                    and not (type(value).__name__ == "_Pass" and f.name == "profile_id")
                    and not (type(value).__name__ == "Load" and f.name in ("profile_id", "timezone"))
                    # R605: the key of a message that repeats is no answer of a profile; the members of a row that
                    # stands for several objects are recorded when there are some
                    and not (type(value).__name__ == "Item" and (f.name == "same" or (
                        f.name == "members" and not value.members)))}
        if hasattr(value, "__geo_interface__"):
            return self.encode(value.__geo_interface__)
        raise TypeError(f"No snapshot encoding for {type(value)!r}")


def rule_output(f):
    from meridiana.core.rules import rules, checks
    applying = rules.applying(f)
    return {"facts": f, "nominal_kw": f.p_nominal_kw, "design": rules.design(f), "minimum": rules.minimum(f),
            "rules": [{"id": r.id, "title": rules.title(r, f), "source": r.source(), "level": r.level,
                       "paragraphs": r.paragraphs(f), "in_document": rules.in_document(r, f)} for r in applying],
            "items": checks.rule_items(f), "notes": [(title, [(r.id, text) for r, text in chapter])
                                                      for title, chapter in rules.notes(f)],
            "notes_text": rules.notes_text(f), "document_items": checks.for_document(checks.rule_items(f))}


def rules_bank():
    from meridiana.core.rules import checks, rules, vvf_activities as vvf
    out = {name: rule_output(f) for name, f in F.fact_cases()}
    active = {r["id"] for row in out.values() for r in row["rules"]}
    expected = {r.id for r in rules.RULES}
    if active != expected:
        raise AssertionError(f"Rules not exercised: {expected - active}")
    out["connections"] = [checks.connection(p, phases, chosen, level, auto)
                          for p in (0, 5.999999, 6, 6.000001, 11.08, 20, 100, 100.000001, 10000, 10000.000001)
                          for phases in (None, 1, 3) for chosen in (False, True)
                          for level in ("BT", "MT", "AT") for auto in (False, True)]
    out["activities"] = [vvf.as_dict(a) for a in vvf.search("")]
    return out


def layouts_bank():
    from meridiana.app import jobs
    from meridiana.core.rules import checks, rules
    out = {}
    for name, p in F.projects():
        results, _keys, _laid = jobs.layout_of(p)
        out[name] = {"project": p.to_json(), "params": [p.fill_params(sf) for sf in p.subfields],
                     "results": results, "guides": p.fire_guides(), "bands": p.fire_bands(),
                     "facts": rule_output(rules.facts(p, results)), "checks": checks.gather(p, results, None),
                     "manual": [checks.manual_items(p, sf, results[sf.id]) for sf in p.subfields]}
    return out


def electrical_bank():
    from meridiana.core.energy import stringing
    from meridiana.app.assistant import design_rules
    plans = []
    for temp in (None, -15.0, -10.0):
        for changes in ({}, {"beta_voc": None}, {"max_system_voltage_v": None}, {"max_series_fuse_a": None}):
            for n, parallel in ((12, [1, 1]), (30, [1, 0]), (12, [2, 0]), (12, [3, 0]), (1, [1, 0]), (12, [0, 0])):
                m, inv = F.module(**changes), F.inverter()
                plans.append(stringing.plan(m, inv, n, parallel, temp, 70.0))
    return {"plans": plans, "suggestions": [stringing.suggest(F.module(), F.inverter(), n, -10.0, 70.0)
                                            for n in (0, 12, 24, 40, 80)],
            "market": [design_rules.search(q) for q in ("S1200 SE33.3K", "SolarEdge S1000", "Huawei", "fire brigade")]}


def optimizers_bank():
    from meridiana.core.energy import optimizers as O
    from meridiana.data import catalog
    inverters = {r["model"]: r for r in catalog.search("inverters", manufacturer="SolarEdge", limit=None)}
    opts = {r["model"]: r for r in catalog.search("optimizers", manufacturer="SolarEdge", limit=None)}
    out = {}
    for inv_name in ("SE5000H", "SE10K", "SE100K", "SE50K"):
        for opt_name in ("S440", "S1000", "S1200", "P401"):
            opt, inv = O.Optimizer.from_record(opts[opt_name]), O.fixed_voltage(inverters[inv_name])
            policy, reason = O.rules_for(opt, inv)
            plans = []
            if policy is not None:
                for per in (1, 2):
                    for count in (8, 24, 48):
                        for strings in (1, 2, 3):
                            plans.append(O.string_plan(F.module(), opt, per, inv, policy, count, strings, 0, -10.0))
            out[f"{inv_name}_{opt_name}"] = {"rules": policy, "reason": reason, "plans": plans,
                                             "module_checks": O.module_checks(F.module(), opt, 1, None, inv)}
    return out


def calendar_bank():
    from meridiana.core.energy import consumption as C, bands, economics as E
    index = C._index()
    contexts = [C.Context(p_stc_kw=p, production_kwh=production)
                for p in (0, 6, 6.000001, 100, 100.000001) for production in (None, 12345.0)]
    cases = {"auto": {}, "annual": {"annual_kwh": 12345.0}, "monthly": {"monthly_kwh": list(range(100, 1300, 100))},
             "bands": {"bands_kwh": {"F1": 3000, "F2": 2000, "F3": 1000}},
             "monthly_bands": {"monthly_bands_kwh": [{"F1": 100 + i, "F2": 200, "F3": 300} for i in range(12)]},
             "measured": {"measured": {"start": index[0].isoformat(), "values": [1.5] * 8760}}}
    loads = {name: C.build(C.Consumption.from_dict(raw), contexts[-1]) for name, raw in cases.items()}
    prod = pd.Series(np.where((index.hour >= 10) & (index.hour < 16), 10.0, 0.0), index=index)
    load = pd.Series(np.full(8760, 0.5), index=index)
    money = {}
    for community in (False, True):
        for zone in ("north", "centre", "other"):
            for storage in (False, True):
                raw = {"community": community, "zone": zone, "grant_pct": 20.0, "trase": 0.01,
                       "deduction_pct": 50.0, "buy_f1": 0.30, "buy_f2": 0.20, "buy_f3": 0.15}
                if storage:
                    raw["battery"] = {"usable_energy_kwh": 10, "max_charge_power_w": 5000,
                                      "max_discharge_power_w": 5000, "round_trip_efficiency_pct": 90}
                s = E.Settings.from_dict(raw)
                money[f"{community}_{zone}_{storage}"] = {"settings": s, "result": E.evaluate(prod, load, 20.0, 18.0, s)}
    return {"index": index, "utc": index.tz_convert("UTC"), "bands": bands.band_of(index),
            "holidays": {str(y): sorted(bands.holidays(y)) for y in (2024, 2025, 2026)},
            "guesses": [C.guess(c) for c in contexts], "shapes": {p: C.shape(p, index) for p in C.profile_names()},
            "loads": {n: {"load": l, "bands": l.by_band(), "monthly": l.monthly_by_band(), "figures": l.figures(),
                           "duration": l.duration(), "week": l.week()} for n, l in loads.items()},
            "money": money, "sizing": E.sizing(prod, load, 20, 18, E.Settings.from_dict({})),
            "storage_sizing": E.storage_sizing(prod, load, 20, 18, E.Settings.from_dict({})),
            "defaults": E.Settings.from_dict({}),
            "pod": [C.valid_pod(s) for s in ("", "IT001E12345678", "IT001E123456789", "invalid")]}


def pipeline_bank():
    from _fixtures import capannone
    from meridiana.app import jobs, pipeline
    from meridiana.core.model import model
    from meridiana.data import catalog
    out = {}
    with tempfile.TemporaryDirectory() as folder:
        write_cache(clear_sky_meteo(), Path(folder))
        for connected in (False, True):
            for shade in (False, True):
                p = F.fixed(capannone())
                if shade:
                    p.exclusions.append(model.ExclusionItem(id="e1", ring=[[18, 9], [20, 9], [20, 11], [18, 11]],
                                                            kind="chimney", building="b1", height=2.5))
                if connected:
                    rec = next(iter(catalog.search("inverters", "SCA100K-T-US-480")))
                    p.energy["inverters"] = [{"record": rec, "count": 1, "name": ""}]
                    p.energy["strings"] = {"auto": True}
                results, _keys, _laid = jobs.layout_of(p)
                result = pipeline.compute(p, results, Path(folder), fetch=False)
                if result.error_sim:
                    raise AssertionError(result.error_sim)
                if connected and result.sim.energy_kwh <= 0:
                    raise AssertionError("A connected parity bank must produce energy")
                out[f"{connected}_{shade}"] = {"project": p.to_json(), "result": result,
                                                "report": reports_bank(p, results, result.as_dict())}
    return out


def reports_bank(p, results, energy):
    compose = importlib.import_module("meridiana.app.report.compose")
    from meridiana.core.rules import rules, checks
    data = {**energy, "results": results, "rules_facts": rules.facts(p, results, energy),
            "checks": checks.gather(p, results, energy)}
    out = {}
    for template in ("complete", "compact"):
        p.report = {"template": template}
        with patch.object(compose, "date", F.FixedDate):
            composed = compose.compose(p, data)
        out[template] = {"document": composed.document, "chapters": composed.chosen,
                         "images": list(composed.makers)}
    return out


def interface_bank():
    from meridiana import i18n
    from meridiana.app import jobs
    from meridiana.app.session import ProjectSession
    from meridiana.gui.backend import properties_schema
    from meridiana.app.assistant import tools, persona, design_rules
    from meridiana.app.interface import help as H
    from meridiana.core.rules import rules
    p = F.fixed(next(F.projects())[1])
    results, _keys, _laid = jobs.layout_of(p)
    session = ProjectSession(p)
    f = rules.facts(p, results)
    f.premises = "domestic"
    f.floor_m2 = 120.0
    f.contracted_kw = 3.0
    f.obligation = "new"
    f.footprint_m2 = 800.0
    host = F.host(p, results, f)
    return {"schemas": {kind: properties_schema.build_schema(session, kind, obj) for kind, obj in
                        (("site", None), ("building", p.buildings[0]), ("subfield", p.subfields[0]), ("defaults", None))},
            "tools": tools.specs(), "rules": tools.read_rules(host, tools.State()),
            "individual_rules": [tools.read_rules(host, tools.State(), f"N{i:02d}") for i in range(1, 28)],
            "activities": tools.vvf_activities(host, tools.State()), "persona": persona.system(lang=i18n.language()),
            "passages": design_rules.passages(), "help": H.texts()}


def charts_bank():
    from meridiana.app.session import ProjectSession
    from meridiana.gui.backend import charts_schema
    p = F.fixed(next(F.projects())[1])
    session = ProjectSession(p)
    out = {}
    for phase in ("consumption", "economics"):
        for mode in ("annual", "bands", "bills", "measured") if phase == "consumption" else ("annual",):
            for community in (False, True):
                p.economics = {"community": community}
                editor = SimpleNamespace(session=session, phase=phase, mode=mode, curveUnit="kWh")
                out[f"{phase}_{mode}_{community}"] = charts_schema.build(editor)
    return out


def reports_geometry_bank():
    from meridiana.app import jobs
    return {name: reports_bank(p, jobs.layout_of(p)[0], {}) for name, p in F.projects()}


def pdf_bank():
    from meridiana.app import jobs
    from meridiana.app.report import engine
    from meridiana.core.rules import rules, checks
    from pypdf import PdfReader
    compose = importlib.import_module("meridiana.app.report.compose")
    if not engine.available():
        return {"renderer_missing": "typst"}
    p = F.fixed(next(F.projects())[1])
    results = jobs.layout_of(p)[0]
    data = {"results": results, "rules_facts": rules.facts(p, results), "checks": checks.gather(p, results, None)}
    out = {}
    for template in ("complete", "compact"):
        p.report = {"template": template}
        with patch.object(compose, "date", F.FixedDate):
            composed = compose.compose(p, data)
        with engine.Build() as build:
            for name, make in composed.makers.items():
                build.add(name, make())
            pdf = build.compile(composed.document).pdf
        out[template] = [page.extract_text() for page in PdfReader(io.BytesIO(pdf)).pages]
    return out


def persistence_bank():
    from meridiana.core.model import model
    out = {}
    for path in sorted((ROOT / "tests" / "formati" / "file").iterdir()):
        if path.name == "progetto-v31.meridiana":
            continue  # Added after the frozen legacy capture; exercised by the format suite.
        if path.suffix not in (".json", ".meridiana", ".mer"):
            continue
        if not path.name.startswith("progetto-"):
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            p = model.Project.from_json(raw)
        except (ValueError, UnicodeError) as exc:
            out[path.name] = {"error_type": type(exc).__name__, "error": str(exc)}
            continue
        p = F.fixed(p)
        out[path.name] = {"project": p.to_json(), "reopened": F.fixed(model.Project.from_json(p.to_json())).to_json()}
    if not out:
        raise AssertionError("No historical project captured")
    return out


BANKS = {"rules": rules_bank, "layouts": layouts_bank, "electrical": electrical_bank,
         "calendar": calendar_bank, "pipeline": pipeline_bank, "interface": interface_bank,
         "persistence": persistence_bank, "charts": charts_bank, "reports_geometry": reports_geometry_bank,
         "pdf": pdf_bank, "optimizers": optimizers_bank}


def encoded(bank, lang):
    from meridiana import i18n
    from meridiana.app.assistant import design_rules
    before = i18n.language()
    i18n.setup(lang)
    design_rules.passages.cache_clear()
    try:
        encoder = Encoder()
        data = encoder.encode(BANKS[bank]())
        return data, encoder.arrays
    finally:
        design_rules.passages.cache_clear()
        i18n.setup(before)


def capture(selected=None):
    """Refuse to overwrite any acquired reference; reacquisition needs a new location/review."""
    destination = REFERENCE
    destination.mkdir(parents=True, exist_ok=True)
    for bank in selected or BANKS:
        for lang in ("it", "en"):
            path = destination / f"{bank}-{lang}.json"
            if path.exists() or path.with_suffix(".json.gz").exists():
                raise FileExistsError(path)
            print(f"Capturing {bank}/{lang}", flush=True)
            subprocess.run([sys.executable, "-m", "profili.worker", bank, lang, str(destination)],
                           check=True, cwd=ROOT, timeout=300)
    if not all((REFERENCE / f"{bank}-{lang}.json").exists() for bank in BANKS for lang in ("it", "en")):
        return
    debts = [{**row, "reason": "Initial census on 236dcc12: pending extraction of policy, text or compatibility data at this exact symbol."}
             for row in leaks.scan()]
    for name in ("debiti-iniziali.json", "debiti.json"):
        path = REFERENCE.parent / name
        if path.exists():
            continue
        with path.open("x", encoding="utf-8") as stream:
            json.dump(debts, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    historical = REFERENCE.parent / "historical-sha256.json"
    if not historical.exists():
        hashes = {}
        for fixture in sorted((ROOT / "tests/formati/file").iterdir()):
            if fixture.is_file():
                raw = fixture.read_bytes()
                if not raw.startswith(b"PK\x03\x04"):
                    raw = raw.replace(b"\r\n", b"\n")
                hashes[fixture.name] = hashlib.sha256(raw).hexdigest()
        with historical.open("x", encoding="utf-8") as stream:
            json.dump(hashes, stream, indent=2)
            stream.write("\n")
    meta = {"base": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "python": platform.python_version(), "platform": platform.platform(),
            "versions": {n: importlib.metadata.version(n) for n in ("numpy", "pandas", "pvlib", "shapely", "PySide6")},
            "languages": ["it", "en"], "command": "python -m profili.snapshot --capture",
            "normalization": ["project.name (synthetic)", "project.bim_id", "project.created", "project.modified",
                              "report date.today fixed to 2026-11-11"],
            "comparison": "Exact JSON equality and numpy array_equal, no numeric tolerance on this environment."}
    path = REFERENCE / "metadata.json"
    if not path.exists():
        path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] != "--capture" or any(b not in BANKS for b in sys.argv[2:]):
        raise SystemExit("Use --capture [bank ...] explicitly; tests never acquire references")
    capture(sys.argv[2:])
