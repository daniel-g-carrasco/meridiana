"""Fetch the pinned, redistributable TU Wien IFC corpus. Existing models are verified, never overwritten."""
import argparse
import hashlib
from pathlib import Path
import urllib.request

LICENSE = 'https://creativecommons.org/licenses/by/4.0/'
MODELS = [
    dict(key='tuwien-zdb-reale', filename='RealWorldTestModel-EscapeRouteAnalysis-ZDB-v2.ifc',
         url='https://researchdata.tuwien.ac.at/records/wzp90-dmf60/files/RealWorldTestModel-EscapeRouteAnalysis-ZDB-v2.ifc?download=1',
         sha256='759c5e5f516eb23eb4a9a5f113e626e35e995029ca153ee759ac94a59043652e',
         attribution='Fischer, Schranz, Urban, Pfeiffer, Flamm (TU Wien), Real-World Test Model for Escape Route '
                     'Analysis in IFC format, v2.0.0 (2024), DOI 10.48436/wzp90-dmf60. CC BY 4.0.'),
    dict(key='tuwien-zdb-prova', filename='Custom-Escape-Route-Test-Model-ZDB.ifc',
         url='https://researchdata.tuwien.ac.at/records/ra5g9-tbb65/files/Custom-Escape-Route-Test-Model-ZDB.ifc?download=1',
         sha256='6622b5ba4c71d36af71251bdbcae555bcae34318cd2d79e0056a03e56da6b7de',
         attribution='Fischer, Schranz, Urban, Pfeiffer (TU Wien), Custom Escape Route Test Model in IFC format, '
                     'v1.0.0 (2023), DOI 10.48436/ra5g9-tbb65. CC BY 4.0.'),
]


def fetch(folder):
    folder = Path(folder)
    for item in MODELS:
        target = folder/item['key']/item['filename']
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            data = target.read_bytes()
        else:
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'Meridiana-open-IFC/1.0'})
            with urllib.request.urlopen(request, timeout=120) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError(f"SHA-256 mismatch: {item['key']}")
        if not target.exists():
            with target.open('xb') as stream:
                stream.write(data)
        note = target.with_suffix('.LICENSE.txt')
        if not note.exists():
            with note.open('x', encoding='utf-8', newline='\r\n') as stream:
                stream.write(item['attribution']+'\n'+LICENSE+'\nSource: '+item['url']+'\nSHA-256: '+item['sha256']+
                             '\nMeridiana derivatives add photovoltaic layouts; the original IFC is unchanged.\n')
        print(f"{item['key']}: verified {len(data)} bytes")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    fetch(p.parse_args().out)
