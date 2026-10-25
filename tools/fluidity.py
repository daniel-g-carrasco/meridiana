"""How fluid the real window is: a fixed sequence of gestures on the sample project, each measured until the window is
idle again, and every time the window's loop stops answering for more than 30 ms (a "block": at 60 frames a second
a frame lasts 16 ms). The reference measures of 25/10/2026 and how to read them: docs/prestazioni/README.md.

    python tools/fluidity.py --out docs/prestazioni/AAAA-MM-GG/<name>.json [--on-screen] [--no-3d] [--sequence all]

- The real Windows platform (never offscreen: it draws in another way), temporary folders, the sample project
  (%USERPROFILE%\\dev\\meridiana-prove\\Prova capannone Rho.meridiana or --project).
- Without --on-screen the window stands out of every screen: it measures the program's own work, not what it costs
  the system to show the window. With --on-screen it opens on the primary screen (only with Daniel's leave: it covers
  his work for a minute; do not touch the mouse over it meanwhile).
- --no-3d puts a plain widget in place of the 3D view (the QQuickWidget): the A/B test of the 3D view's weight.
- Sequences: "base" (phases, File, panels' edges, wheels, 3D and plan dragged, a field typed in, the window
  resized), "charts" (Production, Consumption, Economics: their tabs, the pointer over a chart, the wheel, the right
  edge, the window resized), "edges" (the two panels' edges and the window resized, in the Model and the
  Consumption phases: half a minute, for trying a setting), "all" base and charts."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STALL_MS = 30
STEP_S = 0.016                      # one frame at 60 Hz between two moves of a drag


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--on-screen", action="store_true")
    ap.add_argument("--no-3d", action="store_true")
    ap.add_argument("--maximized", action="store_true",
                    help="the window maximised (Niri: as Super+M); on a tiling Wayland desktop a new window is a column "
                         "half the screen wide, where the window shows the plan alone")
    ap.add_argument("--no-vsync", action="store_true", help="the windows' surfaces with swap interval 0")
    ap.add_argument("--sequence", choices=("base", "charts", "edges", "all"), default="all")
    ap.add_argument("--project", type=Path,
                    default=Path.home() / "dev" / "meridiana-prove" / "Prova capannone Rho.meridiana")
    args = ap.parse_args()

    root = Path(tempfile.mkdtemp(prefix="meridiana-fluidity-"))
    for k in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        os.environ[k] = str(root / k.lower())
    sys.path.insert(0, str(ROOT / "src"))

    from PySide6.QtCore import QEvent, QEventLoop, QObject, QPoint, QPointF, Qt, QTimer
    from PySide6.QtGui import QMouseEvent, QWheelEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QLineEdit, QTabWidget, QWidget

    if args.no_vsync:
        from PySide6.QtGui import QSurfaceFormat
        fmt = QSurfaceFormat.defaultFormat()
        fmt.setSwapInterval(0)
        QSurfaceFormat.setDefaultFormat(fmt)
    app = QApplication(["fluidity"])
    left = min(s.geometry().left() for s in app.screens())

    class Away(QObject):
        def eventFilter(self, obj, event):
            if event.type() in (QEvent.Type.Show, QEvent.Type.Resize) and getattr(obj, "isWindow", lambda: False)():
                x, y = left - obj.frameGeometry().width() - 400, 20
                if (obj.x(), obj.y()) != (x, y):
                    obj.move(x, y)
            return False

    if not args.on_screen:
        away = Away(app)
        app.installEventFilter(away)
    from meridiana import config, i18n
    from meridiana.paths import Paths
    i18n.setup("it")
    from meridiana.ui import qt_translations
    qt_translations.install(app, "it")
    if args.no_3d:
        from unittest import mock

        from meridiana.ui import view3d

        class Plain(QWidget):
            """The 3D view's place without the QQuickWidget; whatever the window asks of it answers nothing."""

            def __init__(self, *a, **_k):
                super().__init__(a[0] if a else None)
                self._mock = mock.MagicMock()

            def __getattr__(self, name):
                if name.startswith("__") or name == "_mock":
                    raise AttributeError(name)
                return getattr(self._mock, name)

        view3d.View3D = Plain
    from meridiana.ui.window import MainWindow

    beat = [time.perf_counter()]
    now_measuring = {"name": "", "stalls": []}

    def tick():
        t = time.perf_counter()
        gap = (t - beat[0]) * 1000
        beat[0] = t
        if gap > STALL_MS and now_measuring["name"]:
            now_measuring["stalls"].append(round(gap, 1))

    heart = QTimer()
    heart.setInterval(2)
    heart.timeout.connect(tick)
    heart.start()

    def pump(sec):
        loop = QEventLoop()
        QTimer.singleShot(int(sec * 1000), loop.quit)
        loop.exec()

    def idle(quiet_ms=150, limit=8.0):
        t0 = last = time.perf_counter()
        seen = len(now_measuring["stalls"])
        while time.perf_counter() - t0 < limit:
            pump(0.01)
            if len(now_measuring["stalls"]) != seen:
                seen, last = len(now_measuring["stalls"]), time.perf_counter()
            if (time.perf_counter() - last) * 1000 > quiet_ms and (time.perf_counter() - beat[0]) * 1000 < 10:
                break

    results = []

    def measure(name, action):
        now_measuring["name"], now_measuring["stalls"] = name, []
        t0 = time.perf_counter()
        action()
        acted = (time.perf_counter() - t0) * 1000
        idle()
        total = (time.perf_counter() - t0) * 1000 - 150
        s = now_measuring["stalls"]
        now_measuring["name"] = ""
        row = {"gesture": name, "action_ms": round(acted, 1), "until_idle_ms": round(total, 1), "blocks": len(s),
               "worst_ms": max(s) if s else 0.0, "blocked_ms": round(sum(s), 1)}
        results.append(row)
        print(f"{name:44s} action {acted:7.1f} ms  idle after {total:7.1f} ms  blocks {len(s):3d}  "
              f"worst {row['worst_ms']:6.1f} ms  blocked {row['blocked_ms']:7.1f} ms", flush=True)

    def mouse(widget, kind, pos, button, buttons, mods=Qt.KeyboardModifier.NoModifier):
        app.sendEvent(widget, QMouseEvent(kind, QPointF(pos), QPointF(widget.mapToGlobal(pos)), button, buttons, mods))

    def drag(widget, start, end, steps, button=Qt.MouseButton.LeftButton, mods=Qt.KeyboardModifier.NoModifier):
        mouse(widget, QEvent.Type.MouseButtonPress, start, button, button, mods)
        for i in range(1, steps + 1):
            p = start + (end - start) * i / steps
            mouse(widget, QEvent.Type.MouseMove, QPoint(round(p.x()), round(p.y())), Qt.MouseButton.NoButton, button,
                  mods)
            pump(STEP_S)
        mouse(widget, QEvent.Type.MouseButtonRelease, end, button, Qt.MouseButton.NoButton, mods)

    def wheel(widget, pos, notches, dy=-120):
        for _ in range(notches):
            app.sendEvent(widget, QWheelEvent(QPointF(pos), QPointF(widget.mapToGlobal(pos)), QPoint(0, 0), QPoint(0, dy),
                                              Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                              Qt.ScrollPhase.NoScrollPhase, False))
            pump(STEP_S)

    def hover(widget, steps=60):
        y = widget.height() // 2
        for i in range(steps):
            mouse(widget, QEvent.Type.MouseMove, QPoint(10 + (widget.width() - 20) * i // steps, y),
                  Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
            pump(STEP_S)

    def resize_window():
        if args.maximized:                  # a maximised window is not resized by the program
            return
        for i in range(15):
            win.resize(1600 - 20 * i, 960)
            pump(STEP_S)

    def edge(dock, outward: int):
        """The gap beside a docked card, half way down, dragged by `outward` px and back."""
        g = dock.geometry()
        x = g.right() + 4 if outward > 0 else g.left() - 4
        y = g.center().y()
        return QPoint(x, y), QPoint(x + outward, y)

    cfg = config.Config(theme="light", background="none", check_updates=False)
    paths = Paths(config=root / "config", state=root / "state", data=root / "data", cache=root / "cache")
    t0 = time.perf_counter()
    win = MainWindow(paths, cfg)
    built = (time.perf_counter() - t0) * 1000
    win.resize(1600, 960)
    if args.on_screen:
        win.move(80, 40)
    project = root / "progetto.meridiana"
    shutil.copy(args.project, project)
    win.open_path(project)                  # as app.main: the project opened, then the window shown
    painted = []

    class FirstPaint(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Paint and obj is win and not painted:
                painted.append((time.perf_counter() - t0) * 1000)
            return False

    first = FirstPaint()
    win.installEventFilter(first)
    if args.maximized:
        win.showMaximized()
    else:
        win.show()
    win.raise_()
    win.activateWindow()
    year = None
    while time.perf_counter() - t0 < 20 and (not painted or year is None):
        pump(0.01)
        if year is None and win.session.good_results():
            year = (time.perf_counter() - t0) * 1000
    win.removeEventFilter(first)
    opened = {"window_built_ms": round(built), "first_paint_ms": round(painted[0]) if painted else None,
              "year_ms": round(year) if year is not None else None}
    print("dpr", win.devicePixelRatioF(), "from the window made (ms):", opened,
          "(off the screen Windows paints late: the first paint counts only with --on-screen)", flush=True)
    pump(4)                                 # everything settled before the gestures
    win._view_mode("both")
    pump(2)

    if args.sequence in ("base", "all"):
        for pid in ("model", "plant", "production", "consumption", "economics", "report", "plant", "model"):
            measure(f"phase {pid}", lambda pid=pid: win.show_phase(pid))
            pump(0.3)
        for _ in range(2):
            measure("File: open", lambda: win.open_file_page("open"))
            pump(0.3)
            measure("File: close (Esc)", lambda: QTest.keyClick(win.file_page, Qt.Key.Key_Escape))
            pump(0.3)
        win.show_phase("model")
        pump(1)
        a, b = edge(win.docks[0], 160)
        measure("left panel: edge dragged", lambda: drag(win, a, b, 40))
        measure("left panel: edge back", lambda: drag(win, b, a, 40))
        a, b = edge(win.docks[1], -160)
        measure("right panel: edge dragged", lambda: drag(win, a, b, 40))
        measure("right panel: edge back", lambda: drag(win, b, a, 40))
        ct = win.checks_page.tree.viewport()
        measure("checks: wheel down 10", lambda: wheel(ct, QPoint(100, 40), 10))
        measure("checks: wheel up 10", lambda: wheel(ct, QPoint(100, 40), 10, dy=120))
        tv = win.tree.viewport()
        measure("project tree: wheel 10", lambda: wheel(tv, QPoint(60, 60), 10))
        v = win.view3d
        c = QPoint(v.width() // 2, v.height() // 2)
        measure("3D: wheel 10", lambda: wheel(v, c, 10))
        measure("3D: orbit, 40 steps", lambda: drag(v, c, c + QPoint(200, 60), 40, Qt.MouseButton.MiddleButton,
                                                    Qt.KeyboardModifier.ShiftModifier))
        measure("3D: pan, 40 steps", lambda: drag(v, c, c + QPoint(-150, 0), 40, Qt.MouseButton.MiddleButton))
        pv = win.plan.viewport()
        c = QPoint(pv.width() // 2, pv.height() // 2)
        measure("plan: wheel 10", lambda: wheel(pv, c, 10))
        measure("plan: pan, 40 steps", lambda: drag(pv, c, c + QPoint(-150, 40), 40, Qt.MouseButton.MiddleButton))
        fields = [f for f in win.findChildren(QLineEdit) if f.isVisible() and f.isEnabled() and not f.isReadOnly()]
        if fields:
            fields[0].setFocus()
            measure("a field: 12 keys", lambda: QTest.keyClicks(fields[0], "12,5", delay=40))
        measure("window: resized, 15 steps", resize_window)
        if not args.maximized:
            win.resize(1600, 960)
        pump(0.5)

    if args.sequence == "edges":
        for pid in ("model", "consumption"):
            win.show_phase(pid)
            pump(1.5)
            for name, dock, out in (("left", win.docks[0], 160), ("right", win.docks[1], -160)):
                a, b = edge(dock, out)
                measure(f"{pid}: {name} edge dragged", lambda a=a, b=b: drag(win, a, b, 40))
                measure(f"{pid}: {name} edge back", lambda a=a, b=b: drag(win, b, a, 40))
            measure(f"{pid}: window resized, 15 steps", resize_window)
            if not args.maximized:
                win.resize(1600, 960)
            pump(0.5)

    if args.sequence in ("charts", "all"):
        from meridiana.ui.charts import Chart
        for pid in ("production", "consumption", "economics"):
            measure(f"{pid}: phase opened", lambda pid=pid: win.show_phase(pid))
            pump(1.5)
            tabs = [t for t in win.findChildren(QTabWidget) if t.isVisible() and t.count() > 1]
            for t in tabs[:1]:
                for k in [*range(1, t.count()), 0]:
                    measure(f"{pid}: chart tab {k}", lambda t=t, k=k: t.setCurrentIndex(k))
                    pump(0.3)
            charts = [c for c in win.findChildren(Chart) if c.isVisible() and c.width() > 100]
            if charts:
                view = max((w for w in charts[0].findChildren(QWidget) if w.isVisible()),
                           key=lambda w: w.width() * w.height(), default=charts[0])
                measure(f"{pid}: pointer over a chart, 60 steps", lambda view=view: hover(view))
                measure(f"{pid}: wheel on a chart 10",
                        lambda view=view: wheel(view, QPoint(view.width() // 2, view.height() // 2), 10))
            a, b = edge(win.docks[1], -160)
            measure(f"{pid}: right edge dragged", lambda a=a, b=b: drag(win, a, b, 40))
            measure(f"{pid}: right edge back", lambda a=a, b=b: drag(win, b, a, 40))
            measure(f"{pid}: window resized, 15 steps", resize_window)
            if not args.maximized:
                win.resize(1600, 960)
            pump(0.5)

    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"], capture_output=True,
                                text=True, check=False).stdout.strip()
    except OSError:
        commit = ""
    screen = app.primaryScreen()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "when": time.strftime("%Y-%m-%d %H:%M"), "commit": commit, "on_screen": args.on_screen, "no_3d": args.no_3d,
        "no_vsync": args.no_vsync, "maximized": args.maximized, "platform": app.platformName(),
        "sequence": args.sequence, "screen": f"{screen.name()} {screen.size().width()}x{screen.size().height()} "
                                            f"@ {screen.devicePixelRatio():g}",
        "machine": platform.processor() or platform.machine(), "qt": __import__("PySide6").__version__,
        "opened": opened, "stall_ms": STALL_MS,
        "environment": {k: v for k, v in os.environ.items() if k.startswith(("QT_", "QSG_"))},
        "results": results}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print("written", args.out, flush=True)
    sys.stdout.flush()
    os._exit(0)                     # without tearing the window down: the measures are written


if __name__ == "__main__":
    sys.exit(main())
