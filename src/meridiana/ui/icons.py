"""Lucide's icons (ISC, data/icons/lucide) and Meridiana's own (data/icons/meridiana, the drawings of the
mockups Daniel chose, preferred to Lucide's of the same name), drawn in the colour of the theme when they are
painted: an icon engine that puts the palette's text colour in place of «currentColor», so the icons follow a
change of theme without being made again (study 13, rule 4 and section 8). Every icon with the mockups' stroke of
1.7 px (Lucide's files say 2: Daniel, 24/10/2026, «i simboli nel programma non sono belli come quelli in draft»)."""

from __future__ import annotations

from PySide6.QtCore import QByteArray, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from .. import log, paths

# what each icon is in the window, and Lucide's name for it
NAMES = {"undo": "undo-2", "redo": "redo-2", "select": "mouse-pointer-2", "building": "warehouse", "pitch": "triangle",
         "subfield": "grid-3x3", "exclusion": "square-x", "measure": "ruler", "plan": "map", "3d": "box",
         "both": "columns-2", "fit": "scan", "zoom_in": "plus", "zoom_out": "minus",
         "site": "map-pin", "snaps": "magnet", "ortho": "triangle-right",
         "view_align": "rotate", "view_north": "compass",
         "dock": "panel-right", "background": "layers", "eye": "eye",
         # the bars of the phases (task 17b): by the command's id
         "rectangle": "rectangle-horizontal", "square": "square", "fill": "layout-grid", "empty": "eraser",
         "inverter_catalog": "zap", "inverter_auto": "wand", "compute": "play", "fetch_pvgis": "cloud-download",
         "compare_variants": "git-compare", "import_curve": "file-input", "consumption_base": "sliders-horizontal",
         "battery_catalog": "battery-charging", "export_report": "file-text", "save_revision": "copy-plus",
         "export_csv": "rows-3",
         "copy_notes": "clipboard-copy",
         # the strings of the Plant phase (task 16d)
         "strings_auto": "spline", "strings_complete": "list-plus", "strings_manual": "route", "strings_clear": "eraser",
         # the building templates (task 16a)
         "building_template": "shapes",
         # Move and Rotate (task 16b)
         "move": "move", "rotate": "rotate-ccw",
         # the layout by hand (task 16c)
         "row": "rows-3", "refill": "refresh-ccw-dot",
         # the report's attachments: before, after, out
         "up": "arrow-up", "down": "arrow-down", "remove": "x",
         # the IFC models (study 20)
         "import_ifc": "warehouse", "export_ifc": "box"}
STROKE = b'stroke-width="1.7"'
_SVG: dict = {}
_DRAWN: dict = {}           # (name, colour, width, height): the icon drawn


def svg(name: str) -> bytes:
    """The SVG text of an icon, read once; b"" when the file is not there."""
    if name not in _SVG:
        f = paths.shipped("icons", "meridiana", name + ".svg")
        if f is None or not f.exists():
            f = paths.shipped("icons", "lucide", NAMES.get(name, name) + ".svg")
        try:
            _SVG[name] = f.read_bytes().replace(b'stroke-width="2"', STROKE) if f is not None else b""
        except OSError as error:
            log.complain(f"icon {name}", error)
            _SVG[name] = b""
    return _SVG[name]


class ThemedIcon(QIconEngine):
    def __init__(self, name: str, fixed: str = ""):
        super().__init__()
        self.name = name
        self.fixed = fixed              # a colour of its own (the icon on the accent), or the palette's

    def colour(self, mode) -> str:
        if self.fixed and mode != QIcon.Mode.Disabled:
            return self.fixed
        pal = QApplication.palette()
        group = QPalette.ColorGroup.Disabled if mode == QIcon.Mode.Disabled else QPalette.ColorGroup.Active
        role = QPalette.ColorRole.HighlightedText if mode == QIcon.Mode.Selected else QPalette.ColorRole.ButtonText
        return pal.color(group, role).name()

    def paint(self, painter: QPainter, rect: QRect, mode, state) -> None:
        device = painter.device()
        dpr = device.devicePixelRatioF() if device is not None else 1.0
        pix = QPixmap(self._drawn(QSize(round(rect.width() * dpr), round(rect.height() * dpr)), mode))
        pix.setDevicePixelRatio(dpr)
        painter.drawPixmap(rect, pix)

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        return QPixmap(self._drawn(size, mode))

    def _drawn(self, size: QSize, mode) -> QPixmap:
        """The icon drawn once per size and colour: rendered from the SVG at every paint, the toolbar's icons
        cost a tenth of each step of a splitter dragged (23/10/2026)."""
        colour = self.colour(mode)
        key = (self.name, colour, size.width(), size.height())
        pix = _DRAWN.get(key)
        if pix is None:
            pix = QPixmap(size)
            pix.fill(Qt.GlobalColor.transparent)
            renderer = QSvgRenderer(QByteArray(svg(self.name).replace(b"currentColor", colour.encode("ascii"))))
            if renderer.isValid():
                p = QPainter(pix)
                renderer.render(p, QRectF(0, 0, size.width(), size.height()))
                p.end()
            _DRAWN[key] = pix
        return pix

    def clone(self) -> "ThemedIcon":
        return ThemedIcon(self.name, self.fixed)


def icon(name: str, colour: str = "") -> QIcon:
    """The icon `name` of NAMES, in the theme's text colour or in `colour`; an empty icon when its file is missing
    (the text stays on the button)."""
    return QIcon(ThemedIcon(name, colour)) if svg(name) else QIcon()
