"""A number field that takes a quantity with its unit and arithmetic: «2 m + 30 cm», «150 mm», «2*1,134», «17°».
Enter computes it, and the field shows the value back as the language of the window writes it, with its unit
(«2,30 m»). What cannot be read is said (the `refused` signal, with the reason) and the value stays as it was.
The reading is quantity.parse, in the core; the wheel works as for every spin box (wheel.py)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QDoubleSpinBox

from .. import quantity
from ..i18n import _, number


class QuantityField(QDoubleSpinBox):
    refused = Signal(str)                   # why what was typed was not taken

    def __init__(self, kind: str, unit: str, lo: float, hi: float, value: float, decimals: int = 2,
                 step: float = 0.1, parent=None):
        super().__init__(parent)
        self.kind, self.unit = kind, unit
        self.setDecimals(decimals)
        self.setRange(lo, hi)
        self.setSingleStep(step)
        self.setKeyboardTracking(False)     # valueChanged only when confirmed
        self.setValue(value)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)    # as the mockups of C2
        self.setToolTip(_("Type a value or a calculation, with units: «2 m + 30 cm», «150 mm», «2*1,134»; "
                          "Enter computes it"))

    def textFromValue(self, value: float) -> str:
        return f"{number(value, self.decimals())} {self.unit}" if self.unit != "°" else \
            f"{number(value, self.decimals())}°"

    def _read(self, text: str) -> tuple[float | None, str]:
        """The value of `text`, or None and why not."""
        try:
            value = quantity.parse(text, self.kind, self.unit)
        except quantity.QuantityError as error:
            return None, str(error)
        if not self.minimum() <= round(value, self.decimals()) <= self.maximum():
            return None, _("{value} is out of the range, from {lo} to {hi}").format(
                value=self.textFromValue(value), lo=self.textFromValue(self.minimum()),
                hi=self.textFromValue(self.maximum()))
        return value, ""

    def valueFromText(self, text: str) -> float:
        value, _why = self._read(text)
        return self.value() if value is None else value

    def validate(self, text: str, pos: int):
        # anything may be on its way to a valid expression: only what reads fully is Acceptable
        value, _why = self._read(text)
        return (QValidator.State.Acceptable if value is not None else QValidator.State.Intermediate), text, pos

    def fixup(self, text: str) -> str:
        """Called when the text is confirmed and cannot be taken: say why; the field goes back to its value."""
        value, why = self._read(text)
        if value is None and text.strip():
            self.refused.emit(why)
        return text
