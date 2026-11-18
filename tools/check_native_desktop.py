"""Measure the native Windows renderer on an isolated sample without taking focus or pointer input."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time
import unittest
from unittest import mock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "tests"))
    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ["QML_DISABLE_DISK_CACHE"] = "1"
    os.environ["QT_DISABLE_SHADER_DISK_CACHE"] = "1"
    os.environ.pop("MERIDIANA_TEST_SCREEN", None)
    import _setup
    from _fixtures import capannone
    from PySide6.QtCore import QEventLoop, QTimer, Qt
    from meridiana.ui import motion
    from meridiana.ui.window import MainWindow
    app = _setup.qt_or_skip()
    case = unittest.TestCase()
    show = MainWindow.show

    def quiet_show(window):
        window.setWindowFlag(Qt.WindowType.WindowTransparentForInput, True)
        window.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        window.setWindowOpacity(0.02)
        dell = next(screen for screen in app.screens() if "DELL" in screen.name().upper())
        window.setScreen(dell)
        window.move(dell.availableGeometry().topLeft())
        window.setWindowTitle("Meridiana native desktop verification")
        show(window)

    beat = []
    last = [time.perf_counter()]

    def tick():
        now = time.perf_counter()
        beat.append((now - last[0]) * 1000)
        last[0] = now

    timer = QTimer()
    timer.setInterval(2)
    timer.timeout.connect(tick)
    timer.start()

    def pump(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    rows = []
    try:
        with mock.patch.object(MainWindow, "show", quiet_show):
            window = _setup.window(case, capannone(), size=(1600, 900))
        motion.set_reduced(False)
        window._view_mode("both")
        pump(1000)
        quick = window.view3d
        result = {"platform": app.platformName(), "screens": [
            {"name": screen.name(), "width": screen.geometry().width(), "height": screen.geometry().height(),
             "dpr": screen.devicePixelRatio()} for screen in app.screens()],
            "opacity": window.windowOpacity(), "gpu_drawn": quick.drawn(), "errors": [str(e) for e in quick.errors()]}
        result["window_screen"] = window.screen().name()
        if quick.rhi is not None:
            info = quick.rhi.driverInfo()
            result["backend"] = str(quick.rhi.backend())
            result["driver"] = {name: str(getattr(info, name)) for name in ("deviceName", "deviceId", "vendorId", "deviceType")}
        result["gpu_image"] = [quick.image.width(), quick.image.height()]
        if not quick.image.isNull():
            quick.image.save(str(out / "gpu-frame.png"))
        window.grab().save(str(out / "native-window.png"))

        def measure(name, action, duration=350):
            beat.clear()
            last[0] = time.perf_counter()
            started = time.perf_counter()
            action()
            action_ms = (time.perf_counter() - started) * 1000
            pump(duration)
            gaps = list(beat)
            rows.append({"name": name, "action_ms": round(action_ms, 3), "ticks": len(gaps),
                         "worst_ms": round(max(gaps, default=0), 3), "over_30_ms": sum(gap > 30 for gap in gaps)})
            print(json.dumps(rows[-1]), flush=True)

        for repeat in range(3):
            measure(f"File open {repeat + 1}", lambda: window.open_file_page("open"))
            measure(f"File close {repeat + 1}", window.file_page.close_page)
        for index in (1, 0, 2, 0):
            measure(f"Phase {index}", lambda index=index: window.tabs.setCurrentIndex(index))
        window._view_mode("both")
        pump(600)
        camera = window.view3d.backend.camera
        before_size = [quick.image.width(), quick.image.height()]
        before = bytes(quick.image.bits()) if not quick.image.isNull() else b""
        camera.orbit(35, 10, camera.target)
        window.view3d.backend.cameraChanged.emit()
        measure("Orbit redraw", quick._changed, 700)
        after = bytes(quick.image.bits()) if not quick.image.isNull() else b""
        result["gpu_frame_changes"] = before != after
        result["orbit_image_sizes"] = [before_size, [quick.image.width(), quick.image.height()]]
        quick.image.save(str(out / "gpu-frame-after-orbit.png"))
        result["measures"] = rows
        (out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result["gpu_drawn"] and result["gpu_frame_changes"] and not result["errors"] else 1
    finally:
        timer.stop()
        case.doCleanups()


if __name__ == "__main__":
    raise SystemExit(main())
