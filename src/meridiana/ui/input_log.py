"""Raw pointer, wheel, gesture and key events, written only when explicitly requested."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QEvent, QObject

from .. import log

VARIABLE = "MERIDIANA_INPUT_LOG"
WHEEL = QEvent.Type.Wheel
GESTURES = {QEvent.Type.NativeGesture, QEvent.Type.Gesture, QEvent.Type.GestureOverride}
KEYS = {QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.ShortcutOverride}
MOUSE = {QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.MouseButtonDblClick,
         QEvent.Type.MouseMove}


def _flags(value) -> str:
    return getattr(value, "name", str(value))


def _point(value) -> dict | None:
    return None if value is None else {"x": value.x(), "y": value.y()}


def _delta(value) -> dict:
    return {"x": value.x(), "y": value.y()}


class InputLog(QObject):
    def __init__(self, widget, surface: str, path: Path):
        super().__init__(widget)
        self.surface = surface
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        widget.installEventFilter(self)

    def eventFilter(self, watched, event) -> bool:
        kind = event.type()
        if kind not in GESTURES | KEYS | MOUSE and kind != WHEEL:
            return False
        record = {
            "time": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "surface": self.surface,
            "type": kind.name,
            "angleDelta": None,
            "pixelDelta": None,
            "phase": None,
            "modifiers": _flags(event.modifiers()) if hasattr(event, "modifiers") else "NoModifier",
            "source": None,
            "position": _point(event.position()) if hasattr(event, "position") else None,
            "globalPosition": _point(event.globalPosition()) if hasattr(event, "globalPosition") else None,
        }
        if hasattr(event, "pointingDevice"):
            device = event.pointingDevice()
            if device is not None:
                record["device"] = _flags(device.type())
        if kind == WHEEL:
            record.update(angleDelta=_delta(event.angleDelta()), pixelDelta=_delta(event.pixelDelta()),
                          phase=_flags(event.phase()), source=_flags(event.source()), inverted=event.inverted())
        elif kind == QEvent.Type.NativeGesture:
            record.update(gesture=_flags(event.gestureType()), value=event.value())
        elif kind in GESTURES and hasattr(event, "gestures"):
            record["gestures"] = [_flags(g.gestureType()) for g in event.gestures()]
        elif kind in KEYS:
            from PySide6.QtCore import Qt
            record.update(key=Qt.Key(event.key()).name, text=event.text(), autoRepeat=event.isAutoRepeat(),
                          count=event.count())
        elif kind in MOUSE:
            record.update(button=_flags(event.button()), buttons=_flags(event.buttons()))
        try:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
        except OSError as error:
            log.complain("input log", error)
        return False


def attach(widget, surface: str) -> InputLog | None:
    name = os.environ.get(VARIABLE, "").strip()
    if not name:
        return None
    try:
        return InputLog(widget, surface, Path(name).expanduser())
    except OSError as error:
        log.complain("input log", error)
        return None
