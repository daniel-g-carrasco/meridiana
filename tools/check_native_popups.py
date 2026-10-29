"""Expose one native combo popup for a bounded compositor capture, without taking focus or moving the pointer."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("light", "dark"), required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--opaque-capture", action="store_true", help="Brief bounded compositor inspection")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    os.environ["QT_QPA_PLATFORM"] = "windows"
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import QApplication, QComboBox, QLabel, QVBoxLayout, QWidget
    from meridiana.config import Config
    from meridiana.ui import popups
    from meridiana.ui.theme import Theme
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.GetForegroundWindow.argtypes = ()
    user.GetForegroundWindow.restype = wintypes.HWND
    foreground = user.GetForegroundWindow()
    app = QApplication([])
    theme = Theme(Config(theme=args.mode, background="none"), app=app)
    popups.set_motion(False)
    host = QWidget()
    host.setObjectName("native-popup-check")
    host.setStyleSheet(f'QWidget#native-popup-check {{ background-color: {theme.tokens["panel"]}; }}')
    host.setWindowTitle(f"Meridiana popup R209 {args.mode}")
    for flag in (Qt.WindowType.WindowDoesNotAcceptFocus, Qt.WindowType.WindowTransparentForInput):
        host.setWindowFlag(flag, True)
    host.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    opacity = 1.0 if args.opaque_capture else 0.02
    host.setWindowOpacity(opacity)
    dell = next(screen for screen in app.screens() if "DELL" in screen.name().upper())
    host.setScreen(dell)
    host.resize(500, 170)
    host.move(dell.availableGeometry().right() - host.width() - 12,
              dell.availableGeometry().bottom() - host.height() - 12)
    box = QVBoxLayout(host)
    box.addWidget(QLabel("Native popup: bounded width, native corners, independent theme surface."))
    combo = QComboBox()
    combo.addItems(["Light", "Dark", "Follow the system", "A longer choice with several words"])
    box.addWidget(combo)
    box.addStretch()
    popup = combo.view().window()
    for flag in (Qt.WindowType.WindowDoesNotAcceptFocus, Qt.WindowType.WindowTransparentForInput):
        popup.setWindowFlag(flag, True)
    popup.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
    host.show()
    result = {}

    def present():
        combo.showPopup()
        popup.setWindowOpacity(opacity)
        app.processEvents()
        result.update(mode=args.mode, platform=app.platformName(), screen=host.screen().name(),
                      dpr=host.devicePixelRatioF(), field_width=combo.width(), popup_width=popup.width(),
                      popup_height=popup.height(), foreground_unchanged=user.GetForegroundWindow() == foreground,
                      native_corners=popups.native_corners())
        result["popup_bg"] = theme.tokens["card"]
        hwnd = wintypes.HWND(int(popup.winId()))
        dwm = ctypes.WinDLL("dwmapi")
        dwm.DwmGetWindowAttribute.argtypes = (wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)
        dwm.DwmGetWindowAttribute.restype = ctypes.c_long
        for name, attribute in (("corner_preference", 33), ("immersive_dark", 20), ("border_colour", 34)):
            value = ctypes.c_int()
            result[name] = {"hr": dwm.DwmGetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)),
                            "value": value.value}
        popup.grab().save(str(out / "popup-qt-grab.png"))
        host.grab().save(str(out / "host-qt-grab.png"))
        (out / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result), flush=True)
        if not result["foreground_unchanged"]:
            combo.hidePopup()
            app.quit()

    QTimer.singleShot(700, present)
    timer = QTimer()
    timer.setInterval(250)
    timer.timeout.connect(lambda: app.quit() if (out / "finish").exists() else None)
    timer.start()
    QTimer.singleShot(90000, app.quit)
    code = app.exec()
    combo.hidePopup()
    host.hide()
    return code if result.get("foreground_unchanged") else 1


if __name__ == "__main__":
    raise SystemExit(main())
