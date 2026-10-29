"""Review the actual revised screens with synthetic data and no network or user settings."""
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
from meridiana.ui import motion


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("theme", choices=("light", "dark"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    i18n.setup("it")
    app = _setup.qt_or_skip()
    case = unittest.TestCase()
    cfg = config.Config(theme=args.theme, text_size="large", background="none", language="it",
                        network_tiles=False, network_geocoding=False, network_pvgis=False, check_updates=False)
    win = _setup.window(case, capannone("Progetto dimostrativo"), cfg=cfg, size=(1280, 840))
    motion.set_reduced(True)
    try:
        _setup.wait_until(app, lambda: win.pool.activeThreadCount() == 0)
        win.file_page.open_page("new")
        _setup.turn_events(app, 100)
        win.grab().save(str(args.output / "nuovo-progetto.png"))
        win.file_page.close_page()
        win.show_phase("plant")
        _setup.turn_events(app, 100)
        win.grab().save(str(args.output / "impianto.png"))
        a = win.assistant
        a.reduced_motion = True
        a.set_bubble_size(460, 500)
        a.open_panel()
        a.answer("Posso mostrarti gli ingressi dell'inverter e spiegarti le verifiche delle stringhe.")
        _setup.turn_events(app, 100)
        win.grab().save(str(args.output / "meridio.png"))
        a.panel.grab().save(str(args.output / "meridio-pannello.png"))
        a.close_panel()
        from meridiana.ui import navigation_targets, spotlight
        navigation_targets.show(win, ("setting", "navigation.mouse_style"))
        if not _setup.wait_until(app, lambda: any(
                guide.isVisible() and 0.15 <= guide.progress < 0.7
                for guide in win.findChildren(spotlight.Spotlight))):
            raise RuntimeError("the requested setting was not visibly highlighted")
        win.grab().save(str(args.output / "impostazione-evidenziata.png"))
        print(args.output)
    finally:
        case.doCleanups()


if __name__ == "__main__":
    main()
