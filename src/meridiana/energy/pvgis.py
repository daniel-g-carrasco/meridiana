"""PVGIS as a second opinion: its own estimate of the yearly production of one plane (the PVcalc service),
to set beside Meridiana's. PVGIS models the module with its own empirical model and puts every system loss
in one figure, so the two never agree to the kWh: a difference of a few percent is the difference of the
models, a larger one is a sign to look at the inputs. PVGIS uses the same azimuth convention as the CEI
82-25 (from South, positive towards West).

PVGIS is asked for the crystalline-silicon technology of its 2025 model (pvtechchoice=crystSi2025) and for
the horizon only when the project's loss chain applies it (usehorizon follows Losses.use_horizon), so that
the two estimates see the same sky. PVGIS averages the years of its radiation database (2005-2023 for
SARAH3), Meridiana computes the typical year."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

from .. import atomic
from ..i18n import _
from .meteo import PVGIS_URL, MeteoError
from .pedigree import Source


@dataclass
class PVGISEstimate:
    yearly_kwh: float
    monthly_kwh: list[float]
    loss_pct: float
    source: Source


def params_of(lat: float, lon: float, peak_kw: float, tilt: float, azimuth: float, loss_pct: float,
              building: bool = False, horizon: bool = True) -> dict:
    """The query of the PVcalc service; its values also name the cache file."""
    return {"lat": f"{lat:.5f}", "lon": f"{lon:.5f}", "peakpower": f"{peak_kw:.3f}", "loss": f"{loss_pct:.2f}",
            "angle": f"{tilt:.1f}", "aspect": f"{azimuth:.1f}", "mountingplace": "building" if building else "free",
            "pvtechchoice": "crystSi2025", "usehorizon": 1 if horizon else 0, "outputformat": "json"}


def pvcalc(lat: float, lon: float, peak_kw: float, tilt: float, azimuth: float, loss_pct: float, cache_dir: Path,
           building: bool = False, timeout: float = 60, network: bool = True, horizon: bool = True) -> PVGISEstimate:
    params = params_of(lat, lon, peak_kw, tilt, azimuth, loss_pct, building, horizon)
    path = Path(cache_dir) / "pvgis" / ("pvcalc_" + "_".join(str(v) for v in params.values()) + ".json")
    raw = None
    if path.exists():
        try:
            raw, _notice = atomic.read_json(path)
        except (OSError, ValueError):
            raw = None
    if raw is None and not network:
        raise MeteoError(_("PVGIS's estimate is not in the cache yet"))
    if raw is None:
        import requests
        try:
            answer = requests.get(PVGIS_URL + "PVcalc?" + urlencode(params), timeout=timeout,
                                  headers={"User-Agent": "Meridiana (PV design; https://github.com/daniel-g-carrasco/meridiana)"})
            answer.raise_for_status()
            raw = {"answer": answer.json(), "fetched": date.today().isoformat()}
        except (requests.RequestException, ValueError) as error:
            raise MeteoError(f"PVGIS: {error}") from error
        atomic.write_json(path, raw, keep_backup=False)
    try:
        out = raw["answer"]["outputs"]
        monthly = [float(m["E_m"]) for m in out["monthly"]["fixed"]]
        yearly = float(out["totals"]["fixed"]["E_y"])
        db = raw["answer"]["inputs"]["meteo_data"]["radiation_db"]
    except (KeyError, TypeError, ValueError) as error:
        raise MeteoError(f"PVGIS answered something unexpected: {error}") from error
    label = _("PVGIS 5.3 PVcalc ({db}), system losses {loss}%, fetched {date}").format(
        db=db, loss=f"{loss_pct:g}", date=raw["fetched"])
    return PVGISEstimate(yearly, monthly, loss_pct, Source("data", label, PVGIS_URL + "PVcalc"))


def as_json(estimate: PVGISEstimate) -> str:
    return json.dumps({"yearly_kwh": estimate.yearly_kwh, "monthly_kwh": estimate.monthly_kwh})
