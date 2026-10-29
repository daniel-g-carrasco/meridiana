"""Read-only verification of adapted source and consumer hashes in a format-2 alignment manifest."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "template-sync-qt_R01.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest["format"] != 2:
        raise ValueError("This verifier expects an adapted format-2 manifest")
    failed = []
    for row in manifest["files"]:
        for base, key, checksum in ((args.upstream, "source", "upstream_sha256"),
                                    (ROOT, "target", "target_sha256")):
            path = base / row[key]
            if digest(path) != row[checksum]:
                failed.append(str(path))
    for row in manifest.get("additional_consumer_files", []):
        if digest(ROOT / row["target"]) != row["target_sha256"]:
            failed.append(row["target"])
    for row in manifest.get("not_applicable", []):
        if digest(args.upstream / row["source"]) != row["upstream_sha256"]:
            failed.append(row["source"])
    if failed:
        print("Changed since alignment:", *failed, sep="\n")
        return 1
    print(f"Verified {len(manifest['files'])} adapted mappings at {manifest['upstream_version']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
