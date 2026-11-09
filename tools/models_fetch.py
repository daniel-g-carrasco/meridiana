"""Download the pinned public originals as data, checking every SHA256.

This is optional preparation; models_bake.py itself is completely offline.
Existing files are verified and reused, never overwritten. No archive or script
is executed. Originals live under build/, separate from shipped static arrays.
"""

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request


def fetch(manifest, destination):
    destination = Path(destination).resolve()
    for source in json.loads(Path(manifest).read_text(encoding="utf8"))["sources"]:
        for item in source["files"]:
            path = (destination / item["path"]).resolve()
            if destination not in path.parents:
                raise ValueError("Destination outside asset root")
            if path.exists():
                content = path.read_bytes()
            else:
                request = urllib.request.Request(
                    item["url"], headers={"User-Agent": "Mozilla/5.0"}
                )
                with urllib.request.urlopen(request, timeout=60) as response:
                    content = response.read()
            if hashlib.sha256(content).hexdigest() != item["sha256"]:
                raise ValueError("Checksum mismatch: " + item["path"])
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            print(item["path"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/models/sources.json")
    )
    parser.add_argument(
        "--destination", type=Path, default=Path("build/models-originals")
    )
    args = parser.parse_args()
    fetch(args.manifest, args.destination)
