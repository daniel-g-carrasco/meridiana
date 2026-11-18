"""Real core results from recorded PVGIS answers, shared by tests and photographs.

No test module or GUI is imported. All network answers are local recordings, and
the temporary cache is removed before the completed results leave this helper.
"""

import gzip
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch


def build_results() -> SimpleNamespace:
    """Compute a year, load, economy and sizing without network or user files.

    The result exposes sim, load, econ, pvgis, sizing, storage and settings.
    It is independent of temporary cache files after returning.
    """
    import requests

    from meridiana.energy import consumption, economics, meteo, pvgis
    from meridiana.energy.components import ModuleSpec
    from meridiana.energy.simulate import ArraySpec, simulate

    references = Path(__file__).resolve().parents[2] / "calcoli" / "riferimenti"
    out = SimpleNamespace()
    response = requests.Response()
    response.status_code = 200
    response._content = gzip.decompress((references / "pvgis53-tmy-rho.json.gz").read_bytes())
    with TemporaryDirectory(prefix="meridiana-quick-results-") as cache:
        with patch("requests.get", return_value=response):
            weather = meteo.typical_year(45.5226, 9.03, Path(cache))
        module = ModuleSpec("Test", "400 W", 400, 31, 400 / 31, 37, 14, -0.35, -0.27, 0.05, 108, 1.72, 1.13)
        out.sim = simulate(weather, [ArraySpec("south", "South", 25, 0, 25, module)])
        out.load = consumption.build(consumption.Consumption(annual_kwh=16000, profile="office"))
        out.settings = economics.Settings(years=4)
        out.econ = economics.evaluate(
            out.sim.hourly.e_kwh, out.load.hourly, out.sim.p_stc_kw, out.sim.p_ac_kw, out.settings
        )
        response._content = (references / "pvgis53-pvcalc-rho.json").read_bytes()
        with patch("requests.get", return_value=response):
            out.pvgis = pvgis.pvcalc(45.5226, 9.03, 10, 25, 0, 14, Path(cache))
    out.sizing = economics.sizing(
        out.sim.hourly.e_kwh,
        out.load.hourly,
        out.sim.p_stc_kw,
        out.sim.p_ac_kw,
        out.settings,
        factors=(0.5, 1, 1.5),
    )
    out.storage = economics.storage_sizing(
        out.sim.hourly.e_kwh,
        out.load.hourly,
        out.sim.p_stc_kw,
        out.sim.p_ac_kw,
        out.settings,
        factors=(0, 1, 2),
    )
    return out
