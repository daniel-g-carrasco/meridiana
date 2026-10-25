"""The reading of an IFC model in a process of its own (study 20, section 4): the window starts it, reads its lines and
kills it at Cancel, past the time allowed or past the memory allowed. IfcOpenShell's C++ can loop or crash on a broken
model; here that ends this process, never the window.

    python -m meridiana.ifc_worker FILE [--mode direct|filtered|all|boxes]

stdout, one JSON object per line:
    {"progress": 0.42, "what": "roofs"}        while reading
    {"result": {...}}                          at the end: what ifc_read.read found
    {"error": "...", "kind": "file"}           a file that is not IFC (exit code 2), or another failure (exit code 3)
"""

from __future__ import annotations

import argparse
import json
import sys


def say(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, default=float) + "\n")
    sys.stdout.flush()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="meridiana.ifc_worker")
    ap.add_argument("file")
    ap.add_argument("--mode", default="direct")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    from . import ifc_read
    last = [-1.0]

    def progress(fraction: float, what: str) -> None:
        if fraction - last[0] >= 0.01 or fraction >= 1.0:
            last[0] = fraction
            say({"progress": round(float(fraction), 3), "what": what})
    try:
        result = ifc_read.read(args.file, mode=args.mode, progress=progress)
    except ifc_read.IfcError as error:
        say({"error": str(error), "kind": "file"})
        return 2
    except Exception as error:          # noqa: BLE001  the process's boundary: a damaged file is said, not a crash
        say({"error": f"{type(error).__name__}: {error}", "kind": "read"})
        return 3
    say({"result": result})
    return 0


if __name__ == "__main__":
    sys.exit(main())
