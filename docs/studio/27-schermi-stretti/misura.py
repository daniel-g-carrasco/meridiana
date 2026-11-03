"""Study 27: the window as it is today at the sizes of the real cases, offscreen. One process per case, with a virtual
screen of that size (the first widths of the panels depend on the screen). Photographs in foto/, numbers in misure.json.

From the repository's root, with the environment of the tests (PYTHONPATH=tests;src, QT_QPA_PLATFORM unset here: the
script sets it per case):  python docs/studio/27-schermi-stretti/misura.py <folder of a compiled locale>
Nothing of the program is changed; the 3D view does not draw offscreen (it is an empty rectangle in the photographs)."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = (("A-1920x1080", 1920, 1080), ("B-1366x768", 1366, 768), ("C-1080x1920", 1080, 1920),
         ("D-1280x800", 1280, 800), ("E-800x1280", 800, 1280), ("F-960x1040", 960, 1040),
         ("G-683x728", 683, 728))
PHOTOS = ("model", "plant", "production", "report")


def one(name: str, w: int, h: int, locale: str) -> dict:
    os.environ["LANGUAGE"] = "it"
    import _setup
    from _fixtures import capannone
    from meridiana import config, i18n, phases
    i18n._locale_dirs = lambda: [Path(locale)]
    i18n.setup("it")
    from PySide6.QtWidgets import QAbstractButton, QDockWidget, QToolButton

    class Case(unittest.TestCase):
        def runTest(self):
            pass

    case = Case()
    cfg = config.Config(background="none", network_pvgis=False, accent="indigo", language="it", theme="light")
    win = _setup.window(case, capannone(), cfg=cfg, size=(w, h))
    app = _setup.qt_or_skip()
    out = {"case": name, "asked": [w, h], "screen": app.primaryScreen().size().toTuple(), "phases": {}}
    _setup.wait_settled(app, lambda: win.size().toTuple())
    out["minimum_hint"] = win.minimumSizeHint().toTuple()
    out["got"] = win.size().toTuple()
    out["narrow"] = win.narrow
    out["bars_text"] = win.bars_mode != "icons"
    for pid in phases.ids():
        i = win.tabs.index_of_phase(pid)
        win.tabs.setCurrentIndex(i)
        _setup.wait_settled(app, lambda: (win.size().toTuple(), win.centralWidget().size().toTuple()))
        _setup.turn_events(app, 250)
        bar = win.tabs.bar(i)
        ext = bar.findChild(QToolButton, "qt_toolbar_ext_button")
        hint = sum(g.sizeHint().width() for g in bar.groups) + len(bar.lines) * 1 + 8
        visible_buttons = [b for b in win.findChildren(QAbstractButton) if b.isVisible()]
        small = sum(1 for b in visible_buttons if min(b.width(), b.height()) < 40)
        docks = {}
        for d in win.findChildren(QDockWidget):
            if d.isVisible():
                docks[d.objectName() or d.windowTitle()] = dict(rect=d.geometry().getRect(),
                                                                minimum=d.minimumSizeHint().toTuple())
        cut = [g.group.id for g in bar.groups if g.geometry().right() > bar.width() or not g.isVisible()]
        out["phases"][pid] = {
            "window": win.size().toTuple(), "minimum_hint": win.minimumSizeHint().toTuple(),
            "header_h": win.tabs.header.height(), "header_min_w": win.tabs.header.minimumSizeHint().width(),
            "central": win.centralWidget().geometry().getRect(),
            "bar_w": bar.width(), "bar_h": bar.height(), "bar_needs_w": hint, "overflow_button": bool(ext and ext.isVisible()),
            "groups_cut": cut, "row_w": win.tabs.tab_bar.width(), "row_needs_w": win.tabs.tab_bar.sizeHint().width(),
            "row_tabs": [win.tabs.tab_bar.tabRect(t).width() for t in range(win.tabs.count())],
            "corner_w": win.tabs.corner_box.geometry().width(), "docks": docks,
            "plan_visible": win.plan.isVisible(), "plan_rect": win.plan.geometry().getRect() if win.plan.isVisible() else None,
            "status_h": win.statusBar().height(), "status_min_w": win.statusBar().minimumSizeHint().width(),
            "buttons": len(visible_buttons), "buttons_under_40": small,
        }
        if pid in PHOTOS:
            win.grab().save(str(HERE / "foto" / f"{name}-{pid}.png"))
    # how narrow and how low the window lets itself go, phase by phase
    out["smallest"] = {}
    for pid in phases.ids():
        win.tabs.setCurrentIndex(win.tabs.index_of_phase(pid))
        win.resize(300, 300)
        _setup.wait_settled(app, lambda: win.size().toTuple())
        out["smallest"][pid] = win.size().toTuple()
    case.doCleanups()
    return out


def main() -> None:
    if len(sys.argv) > 2:                       # a child: one case
        name, w, h, locale, target = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
        Path(target).write_text(json.dumps(one(name, w, h, locale), indent=1), encoding="utf-8")
        return
    locale = sys.argv[1]
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, w, h in CASES:
            screen = Path(tmp) / f"{name}.json"
            screen.write_text(json.dumps({"synchronousWindowSystemEvents": True, "windowFrameMargins": False, "screens": [
                {"name": "s", "x": 0, "y": 0, "width": w, "height": h, "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}),
                encoding="utf-8")
            target = Path(tmp) / f"{name}.out.json"
            # relative: a colon in the value would end the platform's argument
            env = {**os.environ, "QT_QPA_PLATFORM": f"offscreen:configfile={os.path.relpath(screen)}"}
            r = subprocess.run([sys.executable, __file__, name, str(w), str(h), locale, str(target)], env=env, timeout=240,
                               capture_output=True, text=True, check=False)
            if r.returncode or not target.exists():
                print(name, "FAILED", r.returncode, r.stdout[-500:], r.stderr[-1500:])
                continue
            print(name, "ok")
            results.append(json.loads(target.read_text(encoding="utf-8")))
    (HERE / "misure.json").write_text(json.dumps(results, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
