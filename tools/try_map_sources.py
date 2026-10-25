#!/usr/bin/env python3
"""Ask a few tiles of each map source of the program, as the plan would, and say what came back (R36).

  python tools/try_map_sources.py                 every source of tiles.SOURCES, two tiles each
  python tools/try_map_sources.py fr-ign ch-swisstopo     only these
  python tools/try_map_sources.py --zoom 17 --keep FOLDER     another zoom; the tiles kept in FOLDER

Each source is tried at its `sample`, a public square of its area (tiles.Source.sample: never a project's site), at
zoom 18 or the source's highest if lower: the tile of the square and the one east of it. The request is the plan's
(Source.tile_url) with the plan's User-Agent (ui/tileloader.USER_AGENT, written out here to need no Qt). A tile is
good when the answer is 200 with an image (the first bytes of a JPEG or a PNG) of some size: a blank tile of a
server that has nothing there weighs a few hundred bytes, and is said. It is the trial of docs/compiti/21-mappe.md,
made again when a source changes; the suite never asks the network (tests/nucleo/test_tiles.py checks the addresses).
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from meridiana import __version__, geo, tiles  # noqa: E402

USER_AGENT = f"Meridiana/{__version__} (+https://github.com/daniel-g-carrasco/meridiana)"
SMALL = 1000                    # bytes: below this an image is probably blank


def kind_of(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return ""


def try_source(s: tiles.Source, zoom: int, keep: Path | None) -> list[str]:
    lat, lon = s.sample
    z = max(s.min_zoom, min(zoom, s.max_zoom))
    x, y = geo.tile_of(lon, lat, z)
    lines = []
    for tx in (x, x + 1):
        url = s.tile_url(z, tx, y)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=30) as reply:
                status, mime, data = reply.status, reply.headers.get("Content-Type", ""), reply.read()
        except urllib.error.HTTPError as error:
            status, mime, data = error.code, error.headers.get("Content-Type", ""), error.read()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            lines.append(f"  z{z} {tx}/{y}: no answer ({error})")
            continue
        ms = (time.perf_counter() - t0) * 1000
        image = kind_of(data)
        verdict = ("good" if status == 200 and image and len(data) >= SMALL else
                   "blank?" if status == 200 and image else "NOT AN IMAGE")
        lines.append(f"  z{z} {tx}/{y}: {status} {mime} {len(data)} B {image or '-'} {ms:.0f} ms -> {verdict}")
        if keep is not None and image:
            keep.mkdir(parents=True, exist_ok=True)
            (keep / f"{s.key}-{z}-{tx}-{y}.{image}").write_bytes(data)
        time.sleep(0.3)         # a light hand on the servers
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("keys", nargs="*", help="the sources to try (all when none)")
    parser.add_argument("--zoom", type=int, default=18)
    parser.add_argument("--keep", type=Path, help="a folder to keep the tiles in")
    args = parser.parse_args()
    chosen = [tiles.SOURCES[k] for k in args.keys] if args.keys else list(tiles.SOURCES.values())
    print(f"{time.strftime('%Y-%m-%d %H:%M')} User-Agent: {USER_AGENT}")
    bad = 0
    for s in chosen:
        lat, lon = s.sample
        print(f"{s.key} ({s.kind}) at {lat:.4f}, {lon:.4f}")
        lines = try_source(s, args.zoom, args.keep)
        bad += sum("good" not in line for line in lines)
        print("\n".join(lines))
    print(f"{len(chosen)} sources, {bad} tiles not good")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
