"""Preferences > Appearance (study 13, 12.1): the theme, the colour (the nine ready-made ones, the system's, or
another one from the colour dialog), the backgrounds, and a preview with a selection, a button, a warning and
the assistant, the contrast and a word when Meridiana moved the colour. The preview changes at once; the window
follows when the choice settles (250 ms without changes), because setting the style sheet again costs 0.4-0.9 s
(study 13, 8)."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QColorDialog, QComboBox, QFormLayout, QFrame, QHBoxLayout, QLabel,
                               QListWidget, QPushButton, QVBoxLayout, QWidget)

from .. import theme_colors
from ..i18n import _, number
from .cards import default_tokens
from .theme import Theme, background_names, mark, colour_names, qpalette, theme_names
from .style import Group

SETTLE_MS = 250


def toolbar_names() -> dict:
    """The bar of the phase (task 17b, design C1): the words under the icons, or the icons alone."""
    return {"text": _("Words under the icons"), "icons": _("Icons only")}


def place_names() -> dict:
    return {"top": _("Under the row of the phases"), "left": _("On the left side, icons only")}


class Character(QWidget):
    """The assistant as a dot in its colour, until its drawing comes (study 14)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.colour = QColor(default_tokens()["assistant"])
        self.setFixedSize(28, 28)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#24211d"), 1.3))
        p.setBrush(self.colour)
        p.drawEllipse(QRectF(3, 3, 22, 22))


class Preview(QFrame):
    """A small piece of the window in the colours chosen, with its own palette."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        box = QVBoxLayout(self)
        self.items = QListWidget()
        for text in (_("Building 1"), _("Sub-field South"), _("Sub-field East")):
            self.items.addItem(text)
        self.items.setCurrentRow(1)
        self.items.setFixedHeight(76)
        self.items.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        box.addWidget(self.items)
        row = QHBoxLayout()
        self.button = QPushButton(_("Lay the modules"))
        self.button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        row.addWidget(self.button)
        row.addStretch(1)
        self.character = Character()
        row.addWidget(self.character)
        box.addLayout(row)
        self.warning = QLabel()
        box.addWidget(self.warning)

    def show_tokens(self, t: dict, dark: bool) -> None:
        self.setPalette(qpalette(theme_colors.palette(t, dark)))
        from .design import Radius, Space, padding
        # the sample of the primary button, as the sheet draws it (ui/theme.style_sheet)
        self.button.setStyleSheet(f"QPushButton {{ background: {t['accent']}; color: {t['accent_fg']}; "
                                  f"border: none; border-radius: {Radius.CONTROL}px; "
                                  f"{padding(Space.XS, Space.L, 0)} }}")
        ink = theme_colors.STATUS["warning"] if dark else theme_colors.WARNING_INK
        self.warning.setText(f"<span style='color:{ink}'>{mark('⚠')}</span> " + _("To check: the row pitch is below the "
                                                                          "limit angle"))
        self.character.colour = QColor(t["assistant"])
        self.character.update()


class Appearance(QWidget):
    """The page; `settled` (theme, colour, backgrounds) when the choice has stopped changing for a moment."""

    settled = Signal(str, str, str)

    def __init__(self, cfg, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.custom = cfg.accent if theme_colors.valid_hex(cfg.accent) else ""
        box = QVBoxLayout(self)
        form = QFormLayout()
        self.mode = QComboBox()
        for key, text in theme_names().items():
            self.mode.addItem(text, key)
        self.mode.setCurrentIndex(max(0, self.mode.findData(cfg.theme)))
        form.addRow(_("Theme"), self.mode)
        self.colour = QComboBox()
        self._fill_colours(cfg.accent)
        form.addRow(_("Colour"), self.colour)
        self.backgrounds = QComboBox()
        for key, text in background_names().items():
            self.backgrounds.addItem(text, key)
        self.backgrounds.setCurrentIndex(max(0, self.backgrounds.findData(cfg.backgrounds)))
        form.addRow(_("Backgrounds"), self.backgrounds)
        self.toolbar = QComboBox()
        for key, text in toolbar_names().items():
            self.toolbar.addItem(text, key)
        self.toolbar.setCurrentIndex(max(0, self.toolbar.findData(cfg.toolbar)))
        self.toolbar.setToolTip(_("In a window lower than 900 px the icons stay alone by themselves; the titles of "
                                  "the groups stay in both cases"))
        form.addRow(_("Bar of the phase"), self.toolbar)
        self.place = QComboBox()
        for key, text in place_names().items():
            self.place.addItem(text, key)
        self.place.setCurrentIndex(max(0, self.place.findData(cfg.toolbar_place)))
        self.place.setToolTip(_("On the left side the bar shows the icons alone, the groups as separators"))
        form.addRow(_("Where"), self.place)
        box.addLayout(form)
        group = Group(_("Preview"))
        gbox = QVBoxLayout(group)
        self.preview = Preview()
        gbox.addWidget(self.preview)
        self.contrast = QLabel()
        self.contrast.setWordWrap(True)
        gbox.addWidget(self.contrast)
        self.note = QLabel()
        self.note.setWordWrap(True)
        gbox.addWidget(self.note)
        box.addWidget(group)
        box.addStretch(1)
        self.timer = QTimer(self, singleShot=True, interval=SETTLE_MS)
        self.timer.timeout.connect(lambda: self.settled.emit(*self.choice()))
        self.mode.currentIndexChanged.connect(lambda _i: self._changed())
        self.colour.activated.connect(self._colour_chosen)
        self.backgrounds.currentIndexChanged.connect(lambda _i: self._changed())
        self._show()

    def _fill_colours(self, current: str) -> None:
        self.colour.blockSignals(True)
        self.colour.clear()
        for key, text in colour_names().items():
            seed = theme_colors.seed_for(key, self.theme.system_accent)
            self.colour.addItem(text, key)
            self.colour.setItemData(self.colour.count() - 1, QColor(seed), Qt.ItemDataRole.DecorationRole)
        if self.custom:
            self.colour.addItem(self.custom, self.custom)
            self.colour.setItemData(self.colour.count() - 1, QColor(self.custom), Qt.ItemDataRole.DecorationRole)
        self.colour.addItem(_("Another colour…"), "other")
        self.colour.setCurrentIndex(max(0, self.colour.findData(current)))
        self.colour.blockSignals(False)

    def _colour_chosen(self, _index: int) -> None:
        if self.colour.currentData() == "other":
            start = QColor(theme_colors.seed_for(self.custom or "bronze"))
            chosen = QColorDialog.getColor(start, self, _("Another colour"))
            if chosen.isValid():
                self.choose_custom(chosen.name())
            else:
                self._fill_colours(self.custom or "bronze")
        self._changed()

    def choose_custom(self, hex_: str) -> None:
        self.custom = hex_.lower()
        self._fill_colours(self.custom)
        self._changed()

    def choice(self) -> tuple[str, str, str]:
        accent = self.colour.currentData()
        return self.mode.currentData(), accent if accent != "other" else (self.custom or "bronze"), \
            self.backgrounds.currentData()

    def _changed(self) -> None:
        self._show()
        self.timer.start()

    def _show(self) -> None:
        mode, accent, backgrounds = self.choice()
        derived = self.theme.preview(mode, accent, backgrounds)
        dark = self.theme.is_dark(mode)
        self.preview.show_tokens(derived.tokens, dark)
        r = derived.report
        self.contrast.setText(_("Text on the colour {a}:1, the colour on the view {b}:1 (at least 4.5:1).").format(
            a=number(r.on_accent, 1), b=number(r.on_view, 1)))
        self.note.setText(theme_colors.retouch_note(r, dark) or _("The colour is used as it is."))
