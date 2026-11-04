"""Prepare immutable source snapshots used for R372, without Git worktree metadata writes."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compile", action="store_true")
args = parser.parse_args()
revisions = {"base-92c760e": "92c760e", "3b1d8c8": "3b1d8c8", "9dce421": "9dce421",
             "96dc22f-parent": "96dc22f^", "96dc22f": "96dc22f", "6042b8a": "6042b8a"}
manifest = []
for name, revision in revisions.items():
    commit = subprocess.check_output(["git", "rev-parse", revision], cwd=ROOT, text=True).strip()
    destination = ROOT / "build/speed" / name
    if not destination.exists():
        destination.mkdir(parents=True)
        archive = subprocess.check_output(["git", "archive", commit], cwd=ROOT)
        tarfile.open(fileobj=io.BytesIO(archive)).extractall(destination, filter="data")
    files = {}
    for filename in ("src/meridiana/ui/window.py", "src/meridiana/model.py", "src/meridiana/ui/cards.py"):
        expected = subprocess.check_output(["git", "show", f"{commit}:{filename}"], cwd=ROOT)
        actual = (destination / filename).read_bytes()
        normalized = actual.replace(b"\r\n", b"\n")
        assert normalized == expected.replace(b"\r\n", b"\n"), (revision, filename)
        files[filename] = {"archive_sha256": hashlib.sha256(actual).hexdigest(),
                           "git_blob_sha256": hashlib.sha256(expected).hexdigest(),
                           "lf_sha256": hashlib.sha256(normalized).hexdigest(),
                           "normalisation": "CRLF to LF only"}
    if args.compile:
        subprocess.run([sys.executable, str(destination / "tools/compile_po.py"), "--python"], check=True,
                       stdout=subprocess.DEVNULL)
    manifest.append({"directory": name, "revision": revision, "commit": commit, "checked_files": files})
out = Path(__file__).parent / "archives.json"
out.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print("Verified", len(manifest), "snapshots")
