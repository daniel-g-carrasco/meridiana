"""Read-only Rho sample and recorded weather, never the user's application cache."""
import gzip
import json
from pathlib import Path

from meridiana.energy import meteo

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = Path.home() / 'dev' / 'meridiana-prove' / 'Prova capannone Rho.meridiana'


def recorded_weather(project, cache):
    """Use the repository's recorded PVGIS year only at its actual coordinates."""
    if abs(project.site.lat - 45.5226) > .0001 or abs(project.site.lon - 9.03) > .0001:
        return False
    path = ROOT / 'tests/calcoli/riferimenti/pvgis53-tmy-rho.json.gz'
    if not path.is_file():         # the Windows package has no tests: PVGIS is asked, as for any site
        return False
    raw = json.loads(gzip.decompress(path.read_bytes()))
    names = {'temp_air': 'T2m', 'relative_humidity': 'RH', 'ghi': 'G(h)', 'dni': 'Gb(n)',
             'dhi': 'Gd(h)', 'wind_speed': 'WS10m', 'pressure': 'SP'}
    data = {'meta': {'inputs': raw['inputs']}, 'fetched': '2026-10-21',
            'columns': {k: [float(row[v]) for row in raw['outputs']['tmy_hourly']] for k, v in names.items()}}
    target = meteo._cache_file(cache, 'tmy', project.site.lat, project.site.lon)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data), encoding='utf-8')
    return True
