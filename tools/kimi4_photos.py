#!/usr/bin/env python3
"""Offscreen photographs for review task 4, on the tests' shed and with their mocked dialogs."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "src"))

import _setup  # noqa: E402
from finestra.test_window import Stringing  # noqa: E402


def r142(out: Path) -> None:
    _setup.keep_global_state()
    Stringing.setUpClass()
    case = Stringing("test_nothing_comes_by_itself_and_a_string_is_drawn_numbered_taken_back_closed_and_given_up")
    case.setUp()
    try:
        case.zoom_on_row()
        case.win.plant_inspector.list.adders[(1, 2)].click()
        for i in (0, 1, 3, 4):
            case.click(case.points(6)[i][1])
        case.app.processEvents()
        case.win.grab().save(str(out / "kimi4-r142-dopo.png"))
        case.win.plan.draft_chip.hide()
        case.win.plant_inspector.list.show_draft()
        case.win.plant_page.show_draft("")
        case.app.processEvents()
        case.win.grab().save(str(out / "kimi4-r142-prima.png"))
        case.win.plan.cancel_draft()
        if case.dialogs:
            raise RuntimeError(f"Unexpected dialogs: {case.dialogs}")
    finally:
        case.doCleanups()


def r134(out: Path) -> None:
    from PySide6.QtCore import QRectF

    from meridiana.string_paths import Router

    _setup.keep_global_state()
    Stringing.setUpClass()
    case = Stringing("test_another_string_refused_moved_drawn_again_the_list_and_an_older_proposal")
    case.setUp()
    try:
        rows = [case.points(3, row=row) for row in range(3)]
        keys = [[row[i][0] for i in range(3)] for row in rows]
        runs = [{"inverter": 1, "mppt": 1, "modules": modules} for modules in
                ([keys[1][0], keys[1][2]], [keys[0][1], keys[2][1]], [keys[0][0], keys[2][2]])]
        case.win._strings_put("Photograph overlapping string jumps", runs)
        case.plant(lambda p: len(p.strings) == 3)
        modules = [m for row in rows for m in row]
        scene = [case.win.plan.mapToScene(point) for _key, point in modules]
        rect = QRectF(min(p.x() for p in scene) - 2, min(p.y() for p in scene) - 2,
                      max(p.x() for p in scene) - min(p.x() for p in scene) + 4,
                      max(p.y() for p in scene) - min(p.y() for p in scene) + 4)
        case.win.plan.fit(rect)
        case.app.processEvents()
        together = Router.legs_together
        Router.legs_together = lambda self, strings, gap: ([self.legs(order) for order in strings], [0] * len(strings))
        try:
            case.win.plan._draw_wiring()
            case.app.processEvents()
            case.win.plan.grab().save(str(out / "kimi4-r134-prima.png"))
        finally:
            Router.legs_together = together
        case.win.plan._draw_wiring()
        case.app.processEvents()
        case.win.plan.grab().save(str(out / "kimi4-r134-dopo.png"))
        if case.dialogs:
            raise RuntimeError(f"Unexpected dialogs: {case.dialogs}")
    finally:
        case.doCleanups()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("point", choices=("r142", "r134"))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "revisioni" / "foto")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.point == "r142":
        r142(args.out)
    else:
        r134(args.out)


if __name__ == "__main__":
    main()
