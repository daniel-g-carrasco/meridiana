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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("point", choices=("r142",))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "revisioni" / "foto")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.point == "r142":
        r142(args.out)


if __name__ == "__main__":
    main()
