"""Create/check the Widgets-to-Quick backlog and print completion per phase."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "src")]

from quick.parity import registry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true", help="Create the initial inventories, refusing existing files")
    parser.add_argument("--refresh", action="store_true", help="Explicitly refresh source inventories, preserving editorial work")
    parser.add_argument("--check", action="store_true", help="Check all source items and evidence (default)")
    args = parser.parse_args()
    if args.create or args.refresh:
        document = registry.write_initial_or_refresh(refresh=args.refresh)
    else:
        document = registry.load_registry()
    errors = registry.validate(document) + registry.validate_csv_inventories()
    manifests = registry.runtime_manifests()
    for path, manifest in manifests:
        errors.extend(f"{path.relative_to(ROOT)}: {error}"
                      for error in registry.validate_runtime_commands(manifest))
    for error in errors:
        print(error, file=sys.stderr)
    print(json.dumps({"items": len(document["items"]), "requests": len(registry.read_csv("richieste.csv")),
                      "widget_tests": len(registry.read_csv("prove.csv")), "runtime_manifests": len(manifests),
                      "completion": registry.completion(document),
                      "errors": len(errors)}, indent=2, ensure_ascii=False))
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(main())
