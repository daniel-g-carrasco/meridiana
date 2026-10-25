"""What Meridiana does with a project file that is not what it expects (theme G, section 5).

Two rounds, both offscreen and without the network:
- model.Project.load on crafted files: which exception comes out, and whether the window's handler
  (`except (OSError, ValueError)` in MainWindow.open_path) would catch it;
- the same files given to a real MainWindow (QT_QPA_PLATFORM=offscreen, background "none", message boxes
  recorded instead of shown): what the designer would see, and what happens to the plan and the 3D view after.

Usage: QT_QPA_PLATFORM=offscreen python prova_file_progetto.py <repo root> <work dir>
"""

from __future__ import annotations

import base64
import json
import os
import struct
import sys
import time
import traceback
import zlib
from pathlib import Path

ROOT = Path(sys.argv[1])
WORK = Path(sys.argv[2])
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("LANGUAGE", "en")

from meridiana import model  # noqa: E402

FORMAT = {"format": "meridiana-project", "version": model.FORMAT_VERSION}


def png_bytes(width: int, height: int, rgb=(200, 200, 200)) -> bytes:
    """A PNG of one colour, written chunk by chunk (no Pillow): big in pixels, small on disk."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    row = b"\x00" + bytes(rgb) * width
    comp = zlib.compressobj(level=6)
    idat = bytearray()
    for _ in range(height):
        idat += comp.compress(row)
    idat += comp.flush()
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", bytes(idat)) + chunk(b"IEND", b""))


def write(name: str, data, raw: str | None = None) -> Path:
    path = WORK / f"{name}.meridiana"
    path.write_text(raw if raw is not None else json.dumps(data), encoding="utf-8")
    return path


def base() -> dict:
    return {**FORMAT, "name": "Prova", "site": {"lat": 45.5226, "lon": 9.03, "address": "Rho"},
            "buildings": [{"id": "b1", "name": "Capannone", "footprint": [[0, 0], [40, 0], [40, 20], [0, 20]],
                           "height": 9.5, "roof": {"type": "flat"}, "fire": {}}],
            "subfields": [{"id": "s1", "name": "Sud", "ring": [[1, 1], [39, 1], [39, 19], [1, 19]], "building": "b1",
                           "params": {"tilt": 15.0}, "filled": True}],
            "exclusions": [], "underlays": []}


t0 = time.perf_counter()
big = png_bytes(20000, 20000)
mid = png_bytes(6000, 6000)
print(f"PNG 20000x20000: {len(big) / 1e6:.2f} MB on disk; 6000x6000: {len(mid) / 1e6:.2f} MB; "
      f"made in {time.perf_counter() - t0:.1f} s")

cases = {
    "garbage": write("garbage", None, raw="this is not json {"),
    "wrong_format": write("wrong_format", {"format": "something-else", "version": 6}),
    "version_string": write("version_string", {**base(), "version": "6"}),
    "version_zero": write("version_zero", {**base(), "version": 0}),
    "version_future": write("version_future", {**base(), "version": 99}),
    "building_is_string": write("building_is_string", {**base(), "buildings": ["x"]}),
    "building_without_id": write("building_without_id", {**base(), "buildings": [{"name": "a", "footprint": []}]}),
    "footprint_is_text": write("footprint_is_text", {**base(), "buildings": [{"id": "b1", "name": "a", "footprint": "abc"}]}),
    "site_nan": write("site_nan", None, raw=json.dumps(base()).replace("45.5226", "NaN")),
    "site_absurd": write("site_absurd", {**base(), "site": {"lat": 1e308, "lon": -1e308, "address": ""}}),
    "height_absurd": write("height_absurd", None, raw=json.dumps({**base(), "buildings": [
        {**base()["buildings"][0], "height": 1e300}]})),
    "sun_window_garbage": write("sun_window_garbage", {**base(), "sun_window": {"foo": 1}}),
    "unknown_keys": write("unknown_keys", {**base(), "foo": 1, "site": {"lat": 45.5, "lon": 9.0, "bar": 2}}),
    "module_without_size": write("module_without_size", {**base(), "modules": {"m1": {"manufacturer": "X", "model": "Y"}},
                                 "subfields": [{**base()["subfields"][0], "module": "m1"}]}),
    "variants_empty_list": write("variants_empty_list", {**base(), "variants": [], "variant": "v9"}),
    "variants_not_dicts": write("variants_not_dicts", {**base(), "variants": ["v1"], "variant": "v1"}),
    "name_with_path": write("name_with_path", {**base(), "name": "..\\..\\evil"}),
    "underlay_huge": write("underlay_huge", {**base(), "underlays": [
        {"id": "u1", "name": "../../x.png", "image": base64.b64encode(big).decode("ascii"), "width": 20000,
         "height": 20000, "x": 0.0, "y": 0.0, "scale": 0.01}]}),
    "underlay_6000": write("underlay_6000", {**base(), "underlays": [
        {"id": "u1", "name": "mid.png", "image": base64.b64encode(mid).decode("ascii"), "width": 6000,
         "height": 6000, "x": 0.0, "y": 0.0, "scale": 0.01}]}),
    "underlay_not_image": write("underlay_not_image", {**base(), "underlays": [
        {"id": "u1", "name": "x.png", "image": base64.b64encode(b"MZ\x90\x00" * 100).decode("ascii"), "width": 10,
         "height": 10}]}),
}

print()
print("ROUND 1: model.Project.load (what the window's `except (OSError, ValueError)` would catch is marked HANDLED)")
for name, path in cases.items():
    t = time.perf_counter()
    try:
        project, notice = model.Project.load(path)
        dt = time.perf_counter() - t
        extra = ""
        if name == "unknown_keys":
            saved = project.to_json()
            extra = f"; 'foo' kept on save: {'foo' in saved}; site 'bar' kept: {'bar' in saved['site']}"
        if name == "name_with_path":
            extra = f"; default save name would be {str(Path.home() / (project.name + '.meridiana'))!r}"
        if name == "site_nan":
            extra = f"; site.lat={project.site.lat!r}"
        print(f"  {name:22} loaded in {dt * 1000:7.1f} ms (notice={notice!r}){extra}")
    except Exception as error:  # noqa: BLE001 (that is what we measure)
        handled = isinstance(error, (OSError, ValueError))
        print(f"  {name:22} {type(error).__name__}: {str(error)[:90]!r}  -> {'HANDLED' if handled else 'NOT HANDLED (crash of the slot)'}")

print()
print("ROUND 2: what the core does after a file that loads with absurd numbers")
from meridiana import geo, sun, tiles  # noqa: E402

for lat in (float("nan"), 1e308):
    try:
        z = tiles.zoom_for(0.1, lat, 20)
        print(f"  tiles.zoom_for(lat={lat!r}) = {z}")
    except Exception as error:  # noqa: BLE001
        print(f"  tiles.zoom_for(lat={lat!r}) -> {type(error).__name__}: {error}")
    try:
        o = geo.Origin(lat, 9.0)
        print(f"  geo.Origin({lat!r}).to_lonlat(10, 10) = {o.to_lonlat(10, 10)}")
    except Exception as error:  # noqa: BLE001
        print(f"  geo.Origin({lat!r}) -> {type(error).__name__}: {error}")
    try:
        from datetime import datetime, timezone
        p = sun.position(lat, 9.0, datetime(2026, 12, 21, 11, tzinfo=timezone.utc))
        print(f"  sun.position(lat={lat!r}) = elevation {p.elevation!r}")
    except Exception as error:  # noqa: BLE001
        print(f"  sun.position(lat={lat!r}) -> {type(error).__name__}: {error}")

print()
print("ROUND 3: the window (offscreen, background none, dialogs recorded)")
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from meridiana import config  # noqa: E402
from meridiana.paths import Paths  # noqa: E402
from meridiana.ui import tileloader  # noqa: E402

tileloader.TileLoader._pump = lambda self: None            # no network, whatever the plan asks
app = QApplication.instance() or QApplication([])
dialogs: list = []
for kind, answer in (("question", QMessageBox.StandardButton.Discard), ("information", QMessageBox.StandardButton.Ok),
                     ("warning", QMessageBox.StandardButton.Ok)):
    setattr(QMessageBox, kind, staticmethod(lambda *a, k=kind, r=answer, **kw: (dialogs.append((k, a[1:3])), r)[1]))

paths = Paths(config=WORK / "config", state=WORK / "state", data=WORK / "data", cache=WORK / "cache")
from meridiana.ui.window import MainWindow  # noqa: E402

t = time.perf_counter()
win = MainWindow(paths, config.Config(background="none"))
win.show()
app.processEvents()
print(f"  window built in {time.perf_counter() - t:.1f} s; 3D view status: {win.view3d.status()}")

import tracemalloc  # noqa: E402


def pump(seconds: float = 0.5) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


for name in ("version_string", "version_zero", "building_is_string", "building_without_id", "footprint_is_text",
             "site_nan", "site_absurd", "sun_window_garbage", "module_without_size", "variants_not_dicts",
             "underlay_not_image", "underlay_6000", "underlay_huge"):
    dialogs.clear()
    path = cases[name]
    print(f"  --- {name}")
    tracemalloc.start()
    t = time.perf_counter()
    step = "open_path"
    try:
        win.open_path(path)
        pump(0.3)
        step = "plan._update_tiles"
        win.plan._update_tiles()
        step = "_show_3d"
        win._show_3d()
        step = "_start_layout + wait"
        win._start_layout()
        for _ in range(60):
            pump(0.1)
            if not win.relayout_timer.isActive() and win.pool.activeThreadCount() == 0:
                break
        step = "edit (undo snapshot)"
        win.edit("nothing", lambda p: None)
        pump(0.2)
        print(f"      ok through {step}: dialogs {dialogs}; results: "
              f"{ {k: (type(v).__name__ + ': ' + str(v)[:60] if isinstance(v, Exception) else getattr(v, 'count', v)) for k, v in win.results.items()} }")
    except Exception as error:  # noqa: BLE001
        print(f"      UNHANDLED in {step}: {type(error).__name__}: {str(error)[:120]!r}; dialogs {dialogs}")
        traceback.print_exc(limit=2, file=sys.stdout)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"      {time.perf_counter() - t:.2f} s; Python heap peak {peak / 1e6:.0f} MB (Qt's pixmaps are not counted)")
    if name.startswith("underlay"):
        from meridiana.ui import underlays
        u = win.project.underlays[0] if win.project.underlays else None
        if u is not None:
            t2 = time.perf_counter()
            pix = underlays.pixmap(u)
            print(f"      underlays.pixmap: null={pix.isNull()} size={pix.width()}x{pix.height()} in "
                  f"{time.perf_counter() - t2:.2f} s; base64 in the file: {len(u.image) / 1e6:.1f} MB; "
                  f"project.to_json() takes {time.perf_counter() - t2:.2f} s")
            t3 = time.perf_counter()
            snap = win.snapshot()
            print(f"      window.snapshot() (every edit makes two): {time.perf_counter() - t3:.3f} s, "
                  f"{len(json.dumps(snap)) / 1e6:.1f} MB of JSON")

win.close()
print("done")
