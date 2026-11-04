"""Prepare only the sample site's temporary weather cache from recorded PVGIS answers.

The responses were recorded on 24 October 2026; see tests/calcoli/riferimenti/README.md.
No HTTP request leaves this process. The normal app readers and cache writers are used.
"""

import gzip
import hashlib
import json
from pathlib import Path
import sys
from unittest import mock

import requests


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from meridiana.energy import meteo  # noqa: E402


fixtures = ROOT / "tests/calcoli/riferimenti"
cache = ROOT / "build/speed/weather-R01"
receipts = []
receipt_path = Path(__file__).parent / "weather-cache_R01.json"
if receipt_path.exists():
    previous = json.loads(receipt_path.read_text(encoding="utf-8"))
    raw = json.loads(meteo._cache_file(cache, "tmy", 45.5226, 9.03).read_text(encoding="utf-8"))
    assert meteo.usable(raw, 45.5226, 9.03)
    assert hashlib.sha256(json.dumps(raw["columns"], sort_keys=True).encode()).hexdigest() == previous[
        "hourly_columns_sha256_after"]
    for item in previous["receipts"]:
        assert hashlib.sha256((fixtures / item["fixture"]).read_bytes()).hexdigest() == item["sha256"]
    print("Retained verified weather cache and its original receipt")
    raise SystemExit(0)


def get(url, params=None, **kwargs):
    assert url.endswith(("/tmy", "/printhorizon")), url
    assert (params["lat"], params["lon"]) == (45.5226, 9.03), params
    name = "pvgis53-tmy-rho.json.gz" if url.endswith("/tmy") else "pvgis53-printhorizon-rho.json"
    data = (fixtures / name).read_bytes()
    receipts.append({"fixture": name, "sha256": hashlib.sha256(data).hexdigest(), "params": params})
    response = requests.Response()
    response.status_code = 200
    response._content = gzip.decompress(data) if name.endswith(".gz") else data
    response.encoding = "utf-8"
    response.headers["Content-Type"] = "application/json"
    response.url = url
    return response


with mock.patch.object(requests, "get", side_effect=get):
    year = meteo.typical_year(45.5226, 9.03, cache)
    horizon = meteo.horizon(45.5226, 9.03, cache)
assert len(year.data) == 8760
assert (year.latitude, year.longitude) == (45.5226, 9.03)
raw_cache = json.loads(meteo._cache_file(cache, "tmy", 45.5226, 9.03).read_text("utf-8"))
before = hashlib.sha256(json.dumps(raw_cache["columns"], sort_keys=True).encode()).hexdigest()
metadata_alias = raw_cache["meta"]["inputs"]["meteo_data"]["radiation_db"]
raw_cache["meta"]["inputs"]["meteo_data"]["radiation_db"] = "SARAH-3"
meteo._cache_file(cache, "tmy", 45.5226, 9.03).write_text(json.dumps(raw_cache), encoding="utf-8")
assert meteo.usable(raw_cache, 45.5226, 9.03)
after = hashlib.sha256(json.dumps(raw_cache["columns"], sort_keys=True).encode()).hexdigest()
assert before == after
metadata = {"hours": len(year.data), "horizon_directions": len(horizon.azimuth), "receipts": receipts,
            "usable_as_embedded_by_current_reader": meteo.usable(raw_cache, 45.5226, 9.03),
            "metadata_alias_normalisation": {"from": metadata_alias, "to": "SARAH-3"},
            "hourly_columns_sha256_before": before, "hourly_columns_sha256_after": after,
            "provenance": "PVGIS 5.3 responses recorded on 2026-10-24; cache prepared offline on 2026-11-04."}
receipt_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps(metadata, indent=2))
