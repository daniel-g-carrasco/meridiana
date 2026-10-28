"""The weather of the site: a typical year from PVGIS (the European Commission's service, no key needed)
and the profile of the far horizon. Both are kept raw inside the project and mirrored in the cache: once fetched,
the project opens and computes without the network, and the source with its date stays in the pedigree.

The typical year is asked without the horizon (usehorizon=0): the horizon is applied by Meridiana, as its
own step of the loss chain, so the far shading shows as a loss and not as less sun. PVGIS gives the
irradiance of each hour at a representative instant a few minutes after the full hour (the
"irradiance_time_offset" of its metadata, about 0.18 h for SARAH-3): the sun is placed at that instant.

When PVGIS 5.3 does not answer (on 22/10/2026 it answered "This url is blocked" from Daniel's office) the
typical year and the horizon come from PVGIS 6, the new API of the same service (a beta, said in the
source). Its hourly values are means of the hour that starts at their time stamp (checked against the clear
sky: the best match), so the sun is placed half an hour later; it gives the direct normal and the global,
and the diffuse is their difference.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from .. import atomic
from ..i18n import _
from .pedigree import Source

if TYPE_CHECKING:
    import pandas as pd             # imported where it is used: 0,4 s at the window's start otherwise (task 18c)

PVGIS_URL = "https://re.jrc.ec.europa.eu/api/v5_3/"
PVGIS6_URL = "https://photovoltaic-geographic-information-system.ec.europa.eu/api/v6/"
COLUMNS = ("ghi", "dni", "dhi", "temp_air", "wind_speed", "pressure", "relative_humidity")
MOVE_M = 250.0                    # below PVGIS's meaningful spatial resolution, no new download (R196)
DATABASES = {"SARAH-3", "SARAH-2", "ERA5", "synthetic"}


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a, b = math.radians(lat1), math.radians(lat2)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 6371000.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def usable(raw: dict | None, lat: float, lon: float, kind: str = "tmy") -> bool:
    """Whether embedded or cached data still belong to this site and a database Meridiana knows."""
    if not isinstance(raw, dict):
        return False
    try:
        if kind == "tmy":
            inputs = raw["meta"]["inputs"]
            place = inputs["location"]
            metadata = inputs.get("meteo_data", {})
            databases = {metadata.get("radiation_db"), metadata.get("meteo_db")} - {None}
            return (distance_m(float(place["latitude"]), float(place["longitude"]), lat, lon) <= MOVE_M
                    and bool(databases) and databases <= DATABASES)
        return True
    except (KeyError, TypeError, ValueError):
        return False


def capture(project, cache_dir: Path) -> None:
    """Put the site's downloaded raw data in the project, so the file is autonomous (R150, R196)."""
    climate = dict(getattr(project, "climate", {}) or {})
    for kind in ("tmy", "horizon"):
        path = _cache_file(cache_dir, kind, project.site.lat, project.site.lon)
        if path.exists():
            raw, _notice = atomic.read_json(path)
            climate[kind] = raw
    project.climate = climate


class MeteoError(Exception):
    """The weather could not be had: no network, the service refused, a damaged cache."""


@dataclass
class Meteo:
    data: pd.DataFrame          # 8760 hours, UTC, of a non-leap year; COLUMNS
    latitude: float
    longitude: float
    elevation: float
    time_offset_h: float
    source: Source
    fetched: str                # ISO date of the download

    @property
    def summary(self) -> dict:
        d = self.data
        return {"ghi_kwh_m2": float(d.ghi.sum() / 1000), "t_mean": float(d.temp_air.mean()),
                "t_min": float(d.temp_air.min()), "t_max": float(d.temp_air.max())}


@dataclass
class Horizon:
    azimuth: np.ndarray         # degrees from North, clockwise
    elevation: np.ndarray       # degrees above the horizontal
    source: Source

    def at(self, azimuth) -> np.ndarray:
        """The horizon's height in the direction(s) given, interpolated round the circle."""
        az = np.asarray(self.azimuth, dtype=float)
        el = np.asarray(self.elevation, dtype=float)
        order = np.argsort(az)
        az, el = az[order], el[order]
        az = np.concatenate([az - 360, az, az + 360])
        el = np.concatenate([el, el, el])
        return np.interp(np.mod(azimuth, 360.0), az, el)

    def diffuse_factor(self, tilt: float, surface_azimuth: float) -> float:
        """The share of the isotropic sky a tilted plane still sees with this horizon (1: nothing hidden).
        The sky's radiance is taken uniform: the diffuse on the plane is the integral of cos(theta) over the
        visible dome (solid angle cos(el) del daz), and the mountains take the part below their profile."""
        b, g = np.radians(tilt), np.radians(surface_azimuth)
        n = np.array([np.sin(b) * np.sin(g), np.sin(b) * np.cos(g), np.cos(b)])
        az = np.radians(np.arange(0.5, 360.0, 1.0))
        el = np.radians(np.arange(0.25, 90.0, 0.5))
        aa, ee = np.meshgrid(az, el)
        cos_t = np.cos(ee) * np.sin(aa) * n[0] + np.cos(ee) * np.cos(aa) * n[1] + np.sin(ee) * n[2]
        w = np.clip(cos_t, 0.0, None) * np.cos(ee)
        hidden = np.radians(self.at(np.degrees(aa))) > ee
        total = w.sum()
        return float(1.0 - w[hidden].sum() / total) if total > 0 else 1.0

    @classmethod
    def flat(cls) -> Horizon:
        return cls(np.array([0.0, 180.0]), np.array([0.0, 0.0]), Source("default", _("horizon not considered")))


def _cache_file(cache_dir: Path, kind: str, lat: float, lon: float) -> Path:
    return Path(cache_dir) / "pvgis" / f"{kind}_{lat:.4f}_{lon:.4f}.json"


def cached(lat: float, lon: float, cache_dir: Path, kind: str = "tmy") -> bool:
    return _cache_file(cache_dir, kind, lat, lon).exists()


def _tmy_source(meta: dict) -> Source:
    inputs = meta.get("inputs", {}) if isinstance(meta, dict) else {}
    md = inputs.get("meteo_data", {})
    years = f"{md.get('year_min', '?')}-{md.get('year_max', '?')}"
    if meta.get("version") == "6":
        label = _("PVGIS 6 (beta), typical year from {radiation} + {weather}, months of {years}").format(
            radiation=md.get("radiation_db", "?"), weather=md.get("meteo_db", "?"), years=years)
        return Source("data", label, PVGIS6_URL + "meteorological/typical-meteorological-year")
    label = _("PVGIS 5.3, typical year from {radiation} + {weather}, {years}").format(
        radiation=md.get("radiation_db", "?"), weather=md.get("meteo_db", "?"), years=years)
    return Source("data", label, PVGIS_URL + "tmy")


def _from_cache(raw: dict) -> Meteo:
    import pandas as pd
    try:
        index = pd.date_range("1990-01-01 00:00", periods=8760, freq="h", tz="UTC")
        data = pd.DataFrame({c: np.asarray(raw["columns"][c], dtype=float) for c in COLUMNS}, index=index)
        meta = raw["meta"]
        loc = meta["inputs"]["location"]
        return Meteo(data=data, latitude=float(loc["latitude"]), longitude=float(loc["longitude"]),
                     elevation=float(loc["elevation"]), time_offset_h=float(loc.get("irradiance_time_offset", 0.0)),
                     source=_tmy_source(meta), fetched=raw["fetched"])
    except (KeyError, TypeError, ValueError) as error:
        raise MeteoError(f"damaged weather cache: {error}") from error


def typical_year(lat: float, lon: float, cache_dir: Path, refresh: bool = False, timeout: float = 60,
                 embedded: dict | None = None) -> Meteo:
    """The PVGIS typical year of the site, from the project, the cache or the service."""
    if embedded is not None:
        return _from_cache(embedded)
    path = _cache_file(cache_dir, "tmy", lat, lon)
    if path.exists() and not refresh:
        try:
            raw, _notice = atomic.read_json(path)
            return _from_cache(raw)
        except (OSError, ValueError, MeteoError):
            pass                                  # fetched again below
    import requests
    from pvlib.iotools import get_pvgis_tmy
    try:
        data, meta = get_pvgis_tmy(lat, lon, usehorizon=False, url=PVGIS_URL, timeout=timeout, coerce_year=1990)
    except requests.RequestException as error:
        try:
            data, meta = _tmy_v6(lat, lon, timeout)
        except (requests.RequestException, MeteoError, KeyError, TypeError, ValueError) as error6:
            raise MeteoError(f"PVGIS 5.3: {error}; PVGIS 6: {error6}") from error6
    if len(data) != 8760 or any(c not in data.columns for c in COLUMNS):
        raise MeteoError(f"PVGIS answered {len(data)} hours with columns {list(data.columns)}")
    raw = {"meta": meta, "fetched": date.today().isoformat(),
           "columns": {c: [round(float(v), 3) for v in data[c].to_numpy()] for c in COLUMNS}}
    atomic.write_json(path, raw, keep_backup=False)
    return _from_cache(json.loads(json.dumps(raw)))


def _get_json(url: str, params: dict, timeout: float):
    import requests
    r = requests.get(url, params=params, timeout=timeout,
                     headers={"User-Agent": "Meridiana (PV design; https://github.com/daniel-g-carrasco/meridiana)"})
    r.raise_for_status()
    return r.json()


def _tmy_v6(lat: float, lon: float, timeout: float) -> tuple[pd.DataFrame, dict]:
    """The typical year from PVGIS 6, as PVGIS 5.3 gives it: 8760 hours of 1990 in UTC, the columns of
    COLUMNS, and metadata saying where it came from and that the sun belongs half an hour later."""
    import pandas as pd
    import pvlib
    raw = _get_json(PVGIS6_URL + "meteorological/typical-meteorological-year",
                    {"latitude": lat, "longitude": lon}, timeout)
    tmy = raw["typical_meteorological_year"]
    names = {"ghi": "mean_global_horizontal_irradiance", "dni": "mean_direct_normal_irradiance",
             "temp_air": "mean_dry_bulb_temperature", "wind_speed": "mean_wind_velocity",
             "pressure": "mean_surface_pressure", "relative_humidity": "mean_relative_humidity"}
    stamps = pd.to_datetime(tmy[names["ghi"]]["time"])
    frame = pd.DataFrame({c: np.asarray(tmy[k]["values"], dtype=float) for c, k in names.items()})
    frame["month"], frame["day"], frame["hour"] = stamps.month, stamps.day, stamps.hour
    frame = frame[~((frame.month == 2) & (frame.day == 29))].sort_values(["month", "day", "hour"])
    index = pd.date_range("1990-01-01 00:00", periods=8760, freq="h", tz="UTC")
    if len(frame) != 8760:
        raise MeteoError(f"PVGIS 6 answered {len(frame)} hours")
    data = frame[list(names)].set_axis(index).interpolate(limit=3).fillna(0.0)
    elevation = float(_get_json(PVGIS6_URL + "topography/elevation", {"latitude": lat, "longitude": lon},
                                timeout).get("elevation", 0.0))
    sun = pvlib.solarposition.get_solarposition(index + pd.Timedelta(minutes=30), lat, lon, altitude=elevation)
    cos_z = np.clip(np.cos(np.radians(sun.zenith.to_numpy())), 0.0, None)
    data["dni"] = np.clip(data.dni.to_numpy(), 0.0, None)
    data["ghi"] = np.clip(data.ghi.to_numpy(), 0.0, None)
    data["dhi"] = np.clip(data.ghi.to_numpy() - data.dni.to_numpy() * cos_z, 0.0, data.ghi.to_numpy())
    years = [int(y) for y in (raw.get("source_years") or {}).values()] or [0]
    meta = {"version": "6", "inputs": {
        "location": {"latitude": lat, "longitude": lon, "elevation": elevation, "irradiance_time_offset": 0.5},
        "meteo_data": {"radiation_db": "SARAH-3", "meteo_db": "ERA5", "year_min": min(years), "year_max": max(years)}}}
    return data[list(COLUMNS)], meta


def horizon(lat: float, lon: float, cache_dir: Path, refresh: bool = False, timeout: float = 30,
            embedded: dict | None = None) -> Horizon:
    """The far horizon seen from the site, from the project, the cache or PVGIS."""
    path = _cache_file(cache_dir, "horizon", lat, lon)
    raw = embedded
    if raw is None and path.exists() and not refresh:
        try:
            raw, _notice = atomic.read_json(path)
        except (OSError, ValueError):
            raw = None
    if raw is None:
        import requests
        from pvlib.iotools import get_pvgis_horizon
        try:
            series, _meta = get_pvgis_horizon(lat, lon, url=PVGIS_URL, timeout=timeout)
            raw = {"fetched": date.today().isoformat(), "azimuth": [float(a) for a in series.index],
                   "elevation": [float(e) for e in series.to_numpy()]}
        except requests.RequestException as error:
            try:
                profile = _get_json(PVGIS6_URL + "topography/horizon-profile",
                                    {"latitude": lat, "longitude": lon, "angle_output_units": "Degrees"},
                                    timeout)["horizon_profile"]
                raw = {"fetched": date.today().isoformat(), "version": "6",
                       "azimuth": [float(a) for a in profile["azimuth"]],
                       "elevation": [float(e) for e in profile["horizon_height"]]}
            except (requests.RequestException, KeyError, TypeError, ValueError) as error6:
                raise MeteoError(f"PVGIS 5.3: {error}; PVGIS 6: {error6}") from error6
        atomic.write_json(path, raw, keep_backup=False)
    try:
        az, el = np.asarray(raw["azimuth"], float), np.asarray(raw["elevation"], float)
    except (KeyError, TypeError, ValueError) as error:
        raise MeteoError(f"damaged horizon cache: {error}") from error
    if len(az) < 2 or len(az) != len(el) or not all(math.isfinite(v) for v in el):
        raise MeteoError(_("damaged horizon profile"))
    if raw.get("version") == "6":
        return Horizon(az, el, Source("data", _("PVGIS 6 (beta), horizon from the terrain model, fetched {date}").format(
            date=raw["fetched"]), PVGIS6_URL + "topography/horizon-profile"))
    return Horizon(az, el, Source("data", _("PVGIS 5.3, horizon from the terrain model, fetched {date}").format(
        date=raw["fetched"]), PVGIS_URL + "printhorizon"))
