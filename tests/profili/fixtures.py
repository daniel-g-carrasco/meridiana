"""Deterministic projects and inputs, with no real client data or network access."""

from datetime import date
from types import SimpleNamespace

import _setup  # noqa: F401
from _fixtures import capannone, capannone_rho, casa_a_falde, tetto_con_lucernario
from meridiana.core.model import model
from meridiana.core.rules import rules
from meridiana.core.energy.components import ModuleSpec, InverterSpec


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 11)


def fixed(project):
    project.name = "Synthetic plant"
    project.bim_id = "00000000-0000-4000-8000-000000000001"
    project.created = project.modified = "2026-11-11T00:00:00+00:00"
    return project


def projects():
    for name, make in (("shed", capannone), ("fire_shed", capannone_rho),
                       ("skylight", lambda: tetto_con_lucernario(fire=True)), ("gable", casa_a_falde)):
        p = fixed(make())
        for sf in p.subfields:
            sf.filled = True
        yield name, p
        manual = model.Project.from_json(p.to_json(), check=False)
        sf = manual.subfields[0]
        sf.rows = [{"id": "manual1", "x": 3.0, "y": 3.0, "azimuth": 0.0, "places": [0.0, 1.2, 2.4]},
                   {"id": "manual2", "x": 3.0, "y": 7.0, "azimuth": 0.0, "places": [0.0, 1.2]}]
        sf.manual = True
        yield name + "_manual", manual


def facts(**kw):
    f = rules.Facts(p_dc_kw=10.0, p_ac_kw=10.0, installs={"BAPV"}, fire=False)
    for k, v in kw.items():
        setattr(f, k, v)
    if "level" not in kw:
        f.level = rules.auto_level(f.p_nominal_kw)
    return f


def fact_cases():
    yield "default", facts()
    for threshold in (6.0, 11.08, 20.0, 100.0, 10000.0):
        for delta in (-0.000001, 0.0, 0.000001):
            power = threshold + delta
            for dc, ac in ((power, power), (power, power * 2), (power * 2, power)):
                yield f"power_{threshold}_{delta}_{dc}_{ac}", facts(p_dc_kw=dc, p_ac_kw=ac, inverters=2)
    for premises, area in (("productive", 200), ("domestic", 400)):
        for delta in (-0.000001, 0.0, 0.000001):
            for contracted in (0.0, 6.0, 6.000001):
                yield f"premises_{premises}_{delta}_{contracted}", facts(
                    premises=premises, floor_m2=area + delta, contracted_kw=contracted)
    for obligation in ("", "none", "new", "renovation"):
        for public in (False, True):
            for region in ("", "Lombardia"):
                for permit in (False, True):
                    for use in ("other", "data_centre", "large_retail", "logistics_big", "logistics_small"):
                        yield f"minimum_{obligation}_{public}_{region}_{permit}_{use}", facts(
                            obligation=obligation, public=public, region=region, permit_2027=permit,
                            footprint_m2=1000.0, use=use)
    for install in ("BAPV", "BIPV", "canopy", "ground"):
        for fire in (None, False, True):
            for storage in (False, True):
                for activity in (0, 70):
                    yield f"installation_{install}_{fire}_{storage}_{activity}", facts(
                        installs={install}, fire=fire, storage=storage,
                        fire_activities=[("Synthetic building", activity, "B")] if fire else [])
    for kw in ({"uoc_max": 1580.0}, {"risk": True}, {"level": "MT"}, {"level": "AT"},
               {"level": "BT", "p_dc_kw": 150, "p_ac_kw": 150},
               {"premises": "condominium"}, {"p_dc_kw": 12000, "p_ac_kw": 12000},
               {"obligation": "new", "installs": {"canopy"}}):
        yield "special_" + repr(kw), facts(**kw)


def module(**kw):
    data = {"manufacturer": "Acme", "model": "450", "pmax": 450, "vmp": 33.6, "imp": 13.4,
            "voc": 40.1, "isc": 14.1, "beta_voc": -0.25, "alpha_isc": 0.046, "gamma_pmax": -0.30,
            "cells": 108, "length": 1.762, "width": 1.134, "max_system_voltage_v": 1500,
            "max_series_fuse_a": 25}
    return ModuleSpec.from_record({**data, **kw})


def inverter(**kw):
    data = {"manufacturer": "Acme", "model": "10K", "ac_power_nominal_w": 10000,
            "efficiency_euro_pct": 97.5, "dc_voltage_max_v": 1100, "mppt_voltage_min_v": 180,
            "mppt_voltage_max_v": 1000, "mppt_count": 2, "dc_current_max_per_mppt_a": [16, 16],
            "dc_isc_max_per_mppt_a": [20, 20]}
    return InverterSpec.from_record({**data, **kw})


def host(project, results, f):
    return SimpleNamespace(project=project, results=results, rules_facts=lambda: f)
