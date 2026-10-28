"""Compare the scrolling fades in a real hidden window (R192)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools"))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from real_tour import Tour

from meridiana import i18n
from meridiana.ui import fades

VARIANTS = {
    "r161": (16, ((0.0, 0.85), (0.18, 0.64), (0.5, 0.24), (1.0, 0.0))),
    "r177": (16, ((0.0, 1.0), (0.18, 0.75), (0.5, 0.28), (1.0, 0.0))),
    "middle": (12, ((0.0, 1.0), (0.16, 0.42), (0.5, 0.10), (1.0, 0.0))),
}


class FadeTour(Tour):
    def run(self) -> None:
        try:
            self.win.resize(1280, 850)
            self.wait(500)
            places = (
                ("inverter", "plant", self.win.plant_inspector),
                ("bilancio", "economics", self.win.economics_page.centre),
                ("elenco", "model", self.win.tree),
            )
            for variant, (height, stops) in VARIANTS.items():
                fades.HEIGHT = height
                fades.STOPS = stops
                for place, phase, area in places:
                    self.click_phase(phase)
                    bar = area.verticalScrollBar()
                    if bar.maximum() > 0:
                        bar.setValue(bar.maximum() // 2)
                    self.wait(100)
                    for theme, italian in (("light", "chiaro"), ("dark", "scuro")):
                        self.set_theme(theme)
                        self.shot(f"kimi24-sfumature-{variant}-{place}-{italian}", area)
            self.note("confronto delle sfumature completato")
            code = 0
        except Exception:
            import traceback
            traceback.print_exc()
            code = 1
        finally:
            self.win.close()
            self.app.exit(code)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    os.environ.setdefault("PYTHON_KEYRING_BACKEND", "keyring.backends.null.Keyring")
    i18n.setup("it")
    app = QApplication(sys.argv[:1])
    tour = FadeTour(app, argparse.Namespace(toolbars="", file_proposals=False))
    QTimer.singleShot(0, tour.run)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
