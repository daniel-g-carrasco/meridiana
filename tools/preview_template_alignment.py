"""Capture the adapted components in Meridiana with invented data and no network, offscreen only."""
import argparse
import os
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import _setup
from _fixtures import capannone
from meridiana import config, i18n

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("theme", choices=("light", "dark"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    i18n.setup("it")
    case = unittest.TestCase()
    app = _setup.qt_or_skip()
    cfg = config.Config(theme=args.theme, background="none", language="it", assistant=False,
                        network_tiles=False, network_pvgis=False, network_geocoding=False, check_updates=False)
    win = _setup.window(case, capannone("Progetto sintetico"), cfg=cfg)
    try:
        win.resize(1360, 900)
        _setup.wait_until(app, lambda: win.pool.activeThreadCount() == 0)
        _setup.turn_events(app, 100)
        win.grab().save(str(args.output / "modello.png"))
        win.open_file_page()
        win.file_page.show_section("open")
        if not _setup.wait_until(app, lambda: win.file_page.entrance is None, seconds=10):
            raise RuntimeError("File entrance did not finish")
        win.file_page.raise_()
        _setup.turn_events(app, 100)
        win.grab().save(str(args.output / "file.png"))
        win.resize(950, 750)
        _setup.turn_events(app, 300)
        win.file_page.raise_()
        win.grab().save(str(args.output / "file-stretto.png"))
        print("Captured", args.output, "DPR", win.devicePixelRatioF())
    finally:
        case.doCleanups()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
