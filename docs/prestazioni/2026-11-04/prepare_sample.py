"""Make an explicit format-13 copy of the sole authorised sample, for the old reader.

The original is read only. The old model validates and serialises the copy; all keys
it does not understand are recorded. This is a benchmark fixture, never a user file.
"""

import copy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "build/speed/base-92c760e/src"))
from meridiana.model import Project  # noqa: E402


sample = Path.home() / "dev/meridiana-prove/Prova capannone Rho.meridiana"
raw = sample.read_bytes()
data = json.loads(raw)
original_version = data["version"]
data["version"] = 13
unknown = []
project = Project.from_json(copy.deepcopy(data), unknown=unknown)
for variant in data["variants"]:
    variant.get("design", {}).get("energy", {}).pop("inverter_maker", None)
project = Project.from_json(data)
out = ROOT / "build/speed/sample-v13-R02.meridiana"
out.write_text(json.dumps(project.to_json(), ensure_ascii=False, indent=2), encoding="utf-8")
loaded, notice = Project.load(out)
assert notice is None
assert len(loaded.subfields) == len(project.subfields) == 2
metadata = {"original_sha256": hashlib.sha256(raw).hexdigest(), "original_version": original_version,
            "copy_sha256": hashlib.sha256(out.read_bytes()).hexdigest(), "copy_version": 13,
            "unknown_keys": unknown, "buildings": len(project.buildings),
            "subfields": len(project.subfields), "variants": len(project.variants)}
(Path(__file__).parent / "sample-conversion_R02.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps(metadata, indent=2))
