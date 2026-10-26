"""The plan editor: the site from above on its background, the buildings with their pitches, the
sub-fields, the exclusions, the modules once laid; drawing with the aids of snapping.py.

Scene units are metres. The scene's y grows downwards, so a plan point (x East, y North) sits at
(x, -y): North is up on the screen. Pens are cosmetic, one or two screen pixels at any zoom.

Gestures, as in the CAD tools Daniel uses: the wheel zooms on the cursor; the middle button, or Space
held, moves the view; a two-finger scroll on a touchpad moves it too. While drawing: a click places a
corner, Enter or a double click closes the outline, Backspace takes the last corner back, Esc cancels,
Ctrl held draws without guides (AltGr, which Windows sends as Ctrl+Alt on Italian keyboards, does not),
Shift held keeps the direction of the side being drawn, a number typed gives its length and
"length;angle" its length and its turn from the last side (the bearing from North for the first side; the
semicolon separates because the comma is the decimal mark). R switches rectangle mode: two corners give
a side, the third click (or a typed number) the depth.

Move (M; task 16b, study 16 B): a base point and a second point, both snapped, or a move typed («3», «3;2», Tab
for the direction); Ctrl held at the click, or C, makes a copy; R inside Move turns the selection (outside it R
is still the rectangle); the arrows nudge it. The plan collects the points and the keys, move.Gesture does the
sums and the window applies the change: one undo step.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QEvent, QLineF, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPolygonF,
                           QTransform)
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from .. import geo, move, navigation, roofs, sides, theme_colors, tiles, view_colours, viewaids
from . import plan_overlays, waiting
from ..i18n import _, ngettext, number
from .cards import round_corners
from . import design
from ..snapping import EXACT, Guide, Snap, Snapper, ortho
from .theme import symbol_font
from .tileloader import TileLoader

TOOLS = ("select", "building", "pitch", "subfield", "exclusion", "row", "move", "measure")
DRAWING = {"building", "pitch", "subfield", "exclusion"}
MOVABLE = ("building", "subfield", "exclusion", "row")   # what Move takes (task 16b; a row, task 16c)
ARROWS = {Qt.Key.Key_Left: "left", Qt.Key.Key_Right: "right", Qt.Key.Key_Up: "up", Qt.Key.Key_Down: "down"}
LEFT_WAIT_MS = 150             # how long a left press waits for the other button of a gesture (left + right)
TILE_UPDATE_MS = 120

Z_TILES, Z_BUILDING, Z_PITCH, Z_SUBFIELD, Z_EXCLUSION, Z_MODULES, Z_SELECTION = 0, 10, 12, 20, 25, 30, 40
Z_WIRING = 35
Z_VEIL = 1                      # over the tiles (0 and 0.5), under everything drawn
Z_UNDERLAY = 2                  # the images imported (underlay.py): over the veil, under the drawing
# the inputs of an inverter, told apart on the dark blue of the modules: light hues, each with a dark halo
INPUT_COLOURS = ["#ffd166", "#06d6a0", "#ff8fab", "#b8a1ff", "#ffa36b", "#8ee3ef", "#f2efe6", "#c5e063"]


def to_scene(x: float, y: float) -> QPointF:
    return QPointF(x, -y)


def from_scene(p: QPointF) -> tuple[float, float]:
    return p.x(), -p.y()


def polygon(ring) -> QPolygonF:
    return QPolygonF([to_scene(float(x), float(y)) for x, y in ring])


def _quad_at(quads, x: float, y: float) -> int:
    """The first of the convex quadrilaterals (N, 4, 2) that holds the point, or -1: the modules under the
    pointer found in numpy, not polygon by polygon."""
    if quads is None or not len(quads):
        return -1
    a = quads
    b = np.roll(quads, -1, axis=1)
    cross = (b[:, :, 0] - a[:, :, 0]) * (y - a[:, :, 1]) - (b[:, :, 1] - a[:, :, 1]) * (x - a[:, :, 0])
    inside = np.flatnonzero(np.all(cross >= 0.0, axis=1) | np.all(cross <= 0.0, axis=1))
    return int(inside[0]) if len(inside) else -1


def _quad_near(quads, x: float, y: float, reach: float) -> tuple[int, float]:
    """The closest quadrilateral within `reach` scene units, and its squared distance from the point."""
    if quads is None or not len(quads):
        return -1, math.inf
    quads = np.asarray(quads, dtype=float)
    a = quads
    b = np.roll(quads, -1, axis=1)
    edge = b - a
    point = np.array([x, y])
    length2 = np.sum(edge * edge, axis=2)
    along = np.divide(np.sum((point - a) * edge, axis=2), length2,
                      out=np.zeros_like(length2), where=length2 > 1e-18)
    closest = a + np.clip(along, 0.0, 1.0)[..., None] * edge
    distances = np.min(np.sum((point - closest) ** 2, axis=2), axis=1)
    i = int(np.argmin(distances))
    return (i, float(distances[i])) if distances[i] <= reach * reach else (-1, math.inf)


PICK_PX = 6.0


def _ctrl(modifiers) -> bool:
    """Ctrl held, and not AltGr: Windows sends AltGr as Ctrl+Alt, and an Italian keyboard writes @ and # with it."""
    return bool(modifiers & Qt.KeyboardModifier.ControlModifier) and not modifiers & Qt.KeyboardModifier.AltModifier


def _heading(bearing: float) -> float:
    """A bearing as it is written: 0 rather than 360 for North (359.97° rounds to 360.0 otherwise)."""
    b = round(bearing, 1) % 360.0
    return 0.0 if abs(b - 360.0) < 1e-9 else b




def degrees_text(value: float) -> str:
    """An angle as the plan writes it: 30, -12,5."""
    return number(value, 0 if abs(value - round(value)) < 1e-9 else 1)


def qcolour(colour) -> QColor:
    """A QColor from a token: "#rrggbbaa" is CSS's order, Qt reads eight digits as "#aarrggbb"."""
    return QColor(theme_colors.qt_hex(colour)) if isinstance(colour, str) else QColor(colour)


def cosmetic(colour, width: float = 1.5, style=Qt.PenStyle.SolidLine) -> QPen:
    pen = QPen(qcolour(colour), width, style)
    pen.setCosmetic(True)
    return pen


class ChipItem(QGraphicsItem):
    """A label on the plan: the design system's radius and font, the plan's colours and drawn window symbols."""

    def __init__(self, text: str, font: QFont, colour, state: str = "", colours: dict | None = None):
        super().__init__()
        self.text = text
        self._font = QFont(font)
        self.colour = QColor(colour)
        self.symbol_name = {"ok": "check", "check": "warning", "fail": "stop"}.get(state, "")
        self.colours = colours or {"label_bg": "#14161ac8", "label_fg": "#f2efe6"}
        self.radius = design.Radius.INNER
        fm = QFontMetrics(self._font)
        symbol = 16 if self.symbol_name else 0
        gap = 4 if self.symbol_name else 0
        self.rect = QRectF(0, 0, fm.horizontalAdvance(text) + symbol + gap + 12, max(fm.height(), 16) + 4)
        self.text_rect = QRectF(6, 2, fm.horizontalAdvance(text), self.rect.height() - 4)
        self.symbol_rect = QRectF(self.rect.width() - 18, (self.rect.height() - 16) / 2, 16, 16)
        self.offset = QPointF()

    def font(self) -> QFont:
        return QFont(self._font)

    def boundingRect(self) -> QRectF:
        return self.rect.translated(self.offset)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.save()
        painter.translate(self.offset)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolour(self.colours["label_bg"]))
        painter.drawRoundedRect(self.rect, self.radius, self.radius)
        painter.setFont(self._font)
        painter.setPen(self.colour)
        painter.drawText(self.text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text)
        if self.symbol_name:
            from . import symbols
            symbols.paint(painter, self.symbol_rect, self.symbol_name, dark=True)
        painter.restore()


def hints() -> dict:
    return {
        "select": _("Click the smallest object; a second click on the same row selects the row. Esc goes to the "
                    "container; Delete removes the selection."),
        "building": _("Building: click the corners of its outline. Enter or a double click closes it, Backspace "
                      "takes the last corner back, Esc cancels. Ctrl draws without guides; type a number for the "
                      "length of the side."),
        "pitch": _("Free pitch: draw its outline on a building, then choose its eave side and slope."),
        "subfield": _("Sub-field: draw the area where modules may go, on a roof or on the ground, or double-click "
                      "a pitch to take it whole. Modules are laid only when you ask, from its properties."),
        "exclusion": _("Exclusion: draw a skylight, a smoke vent, roof plant or a walkway; modules keep away "
                       "from it."),
        "row": _("Row: click where it starts in a sub-field, then where it ends, or type its length and Enter. It "
                 "takes the module, the gaps and the orientation of the sub-field; red, it goes beyond the edge or "
                 "onto an exclusion. Esc cancels."),
        "move": _("Move: click what to move (a building, a sub-field, an exclusion)."),
        "measure": _("Measure: click two points; the distance stays on screen until the next click."),
    }


class PlanView(QGraphicsView):
    polygonDrawn = Signal(str, list)       # tool, ring in local metres
    picked = Signal(str, str)              # kind ("building", "pitch", "subfield", "exclusion", ""), id
    moduleClicked = Signal(str, str)       # sub-field id, module key
    deleteRequested = Signal()
    hint = Signal(str)
    cursorInfo = Signal(str)
    edgePicked = Signal(str, str, str, int)    # purpose, kind, id, side picked
    sideClicked = Signal(str, str, int)         # kind, id, side: a double click on a side of the selected outline
    vertexMoved = Signal(str, str, int, float, float)   # kind, id, vertex, where it was dropped (metres)
    menuRequested = Signal(QPoint)                         # a right click held still, in the view's pixels
    wholePicked = Signal(str, float, float)                # a double click with no outline: the tool, the point
    markClicked = Signal(str, str)                         # the mark of the checks on an object: kind, id
    pointsPicked = Signal(str, list)                       # purpose, the points clicked (metres): pick_points
    # the strings in the Plant phase (task 16d; R114-R117): a click on a module chooses its string, a double click
    # draws it again; while a string is drawn, the modules clicked or dragged over in order ([[sub-field, key], ...]),
    # Enter or a double click closes it, Esc gives it up; the right button on a module (or anywhere while drawing)
    stringPicked = Signal(str, str)            # sub-field, key: a click on a module, not drawing
    stringRedraw = Signal(str, str)            # a double click on a module, not drawing: its string drawn again
    stringEscape = Signal()                    # Esc, not drawing: the string chosen let go
    stringMenu = Signal(list, QPoint)          # [sub-field, key] or [] (not on a module), where
    draftChanged = Signal(list)                # the modules of the string being drawn, after each change
    draftFinished = Signal(list)               # Enter or a double click: the string as drawn
    draftCancelled = Signal()                  # Esc while drawing
    # Move and Rotate (task 16b): kind, id and what to do, {"mode": "move", "dx", "dy"} or {"mode": "rotate", "cx",
    # "cy", "degrees"}, with "copy" (Ctrl held at the click, or C) and "nudge" (an arrow of the keyboard)
    transformRequested = Signal(str, str, object)
    toolLeft = Signal()                                    # Esc in Move: back to Select
    moveModeChanged = Signal(str)                          # "move" or "rotate": the button of the bar follows
    # the layout by hand (task 16c): a row drawn from a point to another (metres); the end of the selected row
    # dragged to a point ("<sub-field>/<row>", x, y); a double click on a module (sub-field, key), that turns it
    rowDrawn = Signal(list, list)
    rowResized = Signal(str, float, float)
    moduleDoubleClicked = Signal(str, str)

    def __init__(self, cache_dir, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        round_corners(self)                          # its four corners, inside its card (design 3.2)
        # the plan's own colours, the same whatever the theme (view_colours): on the light ground without imagery
        self.colours = view_colours.plan(False)
        self.drawn = None                            # (project, results) last drawn, to draw again in new colours
        self.setBackgroundBrush(qcolour(self.colours["bg"]))
        self.scene().setSceneRect(QRectF(-1e6, -1e6, 2e6, 2e6))
        # the orthophoto always darkened, the same in both themes, for the outlines to stand out (Daniel, 23/10/2026)
        self.veil_strength = view_colours.VEIL
        self.veil = self.scene().addRect(self.scene().sceneRect(), QPen(Qt.PenStyle.NoPen),
                                         QBrush(qcolour(view_colours.veil(self.veil_strength))))
        self.veil.setZValue(Z_VEIL)
        self.veil.setVisible(False)

        self.origin = geo.Origin(45.4642, 9.19)
        self.tool = "select"
        self.snapper = Snapper()
        self.chain: list[tuple[float, float]] = []
        self.snap = None
        self.typed = ""
        self.measure: list[tuple[float, float]] = []
        self.ctrl = False
        self.panning = None
        self.space = False
        self.navigator = navigation.Navigator()   # the mouse's style: pan, zoom, recentre as in the 3D view
        self.left_wait = None                       # a left press held back: (where, modifiers)
        self.left_timer = QTimer(self, singleShot=True, interval=LEFT_WAIT_MS)
        self.left_timer.timeout.connect(self._left_now)
        self.selection = ("", "")
        self.selected_module = ("", "")
        # the modules drawn, by sub-field: the layout they come from with its items (kept while the layout is the
        # same), and (keys, corners (N, 4, 2) in scene coordinates) for picking and outlining (task 18c, step 8)
        self.module_items: dict[str, dict] = {}
        self.module_corners: dict[str, tuple[list, np.ndarray]] = {}
        self.items_by_kind: dict = {}
        self.pending_fit: QRectF | None = None
        self.user_moved = False            # zoomed or moved by hand: a resize keeps the view as it is
        self.rect_mode = False             # R: three clicks make a rectangle
        self.wiring = None                 # energy/plant.Plant of the last strings laid
        self.wiring_on = True
        self.strings_mode = False          # the Plant phase: a click on a module is about its string
        self.draft: list | None = None     # the string being drawn: (sub-field, key) in order; None when none is
        self.draft_index = -1              # the string drawn again (its own modules are not another string's), -1
        self.draft_where = ""              # its inverter and input, for the hint («1.2»)
        self.draft_drag = False            # the left button held on a module while drawing: a drag takes modules
        self.draft_pointer: QPointF | None = None    # where the pointer is, for the line from the last module
        self.chosen_string = -1            # the string chosen, drawn wider and numbered
        self.string_tints: list = []       # the tints of the strings (theme_colors.string_tints)
        self.string_states: dict = {}      # the traffic light: state -> colour
        self.string_colours: list = []     # the tint of each string of the wiring, its neighbours' not (string_paths)
        self.router = None                 # string_paths.Router over the modules drawn, with their index
        self.router_of = None              # the module_corners it was made of
        self.module_index: dict = {}       # (sub-field, key) -> index into the router's modules
        self.lock_dir: tuple[float, float] | None = None     # Shift held: the direction kept
        self.snaps_on = True               # F3: the snaps, as in AutoCAD; Ctrl held lets one point go free
        self.ortho = False                 # F8: square to the first side (East and North before it)
        self.rings: dict = {}              # (kind, id) -> the outline drawn, for the sides' measures
        self.edge_pick = None              # (purpose, kind, id, ring) while a side is being picked
        self.point_pick = None             # (purpose, how many, the points so far, the hints) while points are
        self.edge_hover: int | None = None
        self.dragging = None               # (kind, id, vertex, ring) while a vertex of the selection is dragged
        self.drag_point: tuple[float, float] | None = None
        self.gesture: move.Gesture | None = None     # a Move or a Rotate in progress (task 16b)
        self.move_pointer: tuple[float, float] | None = None    # where it goes, snapped
        self.move_rings: list = []         # what moves with the selection, shown moving
        self.move_mods: set = set()        # the modifiers held, from the last event
        self.rotate_next = False           # Rotate chosen before a selection: the gesture starts turning
        self.grip_press: QPointF | None = None    # where a grip was pressed, while it may be dragged
        # the layout by hand (task 16c): the row tool's first point; what the window says of a row being drawn
        # (`row_preview(start, end)` -> (the modules' corners, beyond the edge or on an exclusion)) and of the row
        # selected (`row_info(oid)` -> {"ring": its outline, "end": the end of its front edge}); the row's end dragged
        self.row_start: tuple[float, float] | None = None
        self.row_preview = None
        self.row_info = None
        self.row_drag: tuple[float, float] | None = None
        self.row_count = 0                           # the modules of the row being drawn, for its label
        self.module_rows: dict[str, list] = {}       # sub-field id -> the row id of each module, as module_corners

        # the background (R36): the sources (the program's and the designer's, tiles.catalogue), the designer's choice
        # ("auto", a source, "none") and the source shown, the choice where it covers the site, else the best there
        self.sources: dict = dict(tiles.SOURCES)
        self.choice = tiles.AUTO
        self.source = "pcn"
        self.loader = TileLoader(cache_dir, self, self.sources)
        self.loader.tileReady.connect(self._tile_ready)
        self.tile_items: dict = {}
        self.target_zoom = None
        self.tile_timer = QTimer(self, singleShot=True, interval=TILE_UPDATE_MS)
        self.tile_timer.timeout.connect(self._update_tiles)
        self.mark_items: list = []              # the marks of the checks (study 12, C1)
        self.focused: tuple | None = None       # the object a check is about, the rest dimmed (C4)
        self.hovered = ("", "", "")             # what the click would select, outlined (study 12, V3)
        self.hover_item = None
        # children of the view, over its viewport: the viewport scrolls its children with what it shows when only
        # what changes is repainted (Select), and a pan took the arrow and the bar away with it (review, 23/10/2026)
        self.north = plan_overlays.NorthArrow(self)
        self.scale_bar = plan_overlays.ScaleBar(self)
        self.attribution = plan_overlays.Attribution(self)
        self.viewbar = None                         # the bar of the view's commands (ui/viewbar.py), set by the window
        # the arc of the layout under the north arrow, while the modules are laid past the threshold (study 16, F3)
        self.laying = waiting.Spinner(self, 24, backdrop=True, tip=_("Laying the modules…"))
        self.laying_wait = waiting.Delayed(self.laying, self)
        self._laying_colours()

        self.scale(10, 10)               # 10 px per metre to start with
        self.centerOn(0, 0)

    # the project

    def set_origin(self, lat: float, lon: float) -> None:
        if (lat, lon) != (self.origin.lat, self.origin.lon):
            self.origin = geo.Origin(lat, lon)
            self._clear_tiles()
            self._choose()                  # another site: the best source may be another one
        self._moved()

    def set_source(self, choice: str) -> None:
        """The designer's choice of background: "auto" (the best for the site), a source's key, or "none". A source
        that does not cover the site, or that this version does not know (a newer one's, or one gone), gives the
        best for the site, and the choice stays for the sites it covers."""
        self.choice = choice
        self._choose(force=True)

    def set_sources(self, custom: list) -> None:
        """The designer's sources (the settings' map_sources) with the program's; the loader shares the table."""
        self.sources.clear()
        self.sources.update(tiles.catalogue(custom))
        self.loader.keys.clear()
        self._choose(force=True)

    def background(self):
        """The source shown, None for none."""
        return self.sources.get(self.source) if self.source != tiles.NONE else None

    def _choose(self, force: bool = False) -> None:
        key = tiles.effective(self.choice, self.sources, self.origin.lon, self.origin.lat)
        if key == self.source and not force:
            return
        self.source = key
        self._credit()
        self._clear_tiles()
        self._moved()
        self._recolour()

    def _credit(self) -> None:
        """The attribution of the source shown, always on the plan (OpenStreetMap's policy: never behind a switch)."""
        shown = self.background()
        self.attribution.set_text(shown.credit() if shown else "", self.viewport().width())
        plan_overlays.place(self)

    def set_veil(self, strength: float) -> None:
        """How much the imagery is darkened, 0 to 1 (view_colours.VEILS)."""
        self.veil_strength = min(1.0, max(0.0, float(strength)))
        self.veil.setBrush(QBrush(qcolour(view_colours.veil(self.veil_strength))))
        self.veil.setVisible(self.source != "none" and self.veil_strength > 0)

    def set_marks(self, marks: list) -> None:
        """The marks of the checks: (x, y, level, count, (kind, id)) in metres; above everything but the guides."""
        from .marks import MarkItem
        for it in self.mark_items:
            self.scene().removeItem(it)
        self.mark_items = []
        for x, y, level, count, target in marks:
            it = MarkItem(level, count, target)
            it.setPos(to_scene(x, y))
            it.setZValue(Z_SELECTION + 5)
            it.setToolTip(target[0])
            self.scene().addItem(it)
            self.mark_items.append(it)

    def focus(self, target: tuple | None) -> None:
        """A check chosen in the list: its object as it is, everything else dimmed; None, all back."""
        self.focused = tuple(target) if target else None
        for kind, items in self.items_by_kind.items():
            if kind in ("selection", "arrows", "wiring", "underlays", "draft", "draft_band"):
                continue
            for it in items:
                mine = self.focused is None or (it.data(0) in (self.focused[0], "modules") and it.data(1) == self.focused[1])
                it.setOpacity(1.0 if mine else 0.3)
        self.viewport().update()

    def frame_target(self, target: tuple) -> None:
        """An object framed, its items found as `focus` finds them (the eye of a check, R127); the view stays so
        until the designer moves it."""
        rect = QRectF()
        for kind, items in self.items_by_kind.items():
            if kind in ("selection", "arrows", "wiring", "underlays", "draft", "draft_band"):
                continue
            for it in items:
                if it.data(0) in (target[0], "modules") and it.data(1) == target[1]:
                    rect = rect.united(it.sceneBoundingRect())
        if rect.isEmpty():
            return
        self.fit(rect)
        self.user_moved = True

    def set_laying(self, on: bool) -> None:
        """A layout on its way (on) or back (off): the arc in the top right corner, under the north arrow, only if it
        takes longer than the threshold, gone as soon as it comes back (study 16, F3; Daniel 23/10/2026)."""
        if on:
            self._place_laying()
            self.laying_wait.begin()
        else:
            self.laying_wait.end()

    def _laying_colours(self) -> None:
        """The arc on the chip of the north arrow, in its ink: the plan's own colours, the same in both themes (R16)."""
        c = self.colours
        self.laying.set_colours(arc=c["label_fg"], ring=c["label_fg"][:7] + "40", chip=c["label_bg"])

    def _place_laying(self) -> None:
        north = self.north.geometry()
        self.laying.move(north.center().x() - self.laying.width() // 2, north.bottom() + 1 + 6)

    def _moved(self) -> None:
        """The view moved or zoomed: the tiles a moment later, the scale bar now; the numbers of the string chosen
        thinned again to the zoom when it changed enough."""
        self.tile_timer.start()
        mpp = self.metres_per_pixel()
        self.scale_bar.set_scale(mpp)
        numbered = getattr(self, "numbered_at", 0.0)
        tagged = getattr(self, "tagged_at", 0.0)
        if ((self.chosen_string >= 0 or self.draft) and numbered and not 0.8 < mpp / numbered < 1.25) or                 (self.wiring is not None and tagged and not 0.8 < mpp / tagged < 1.25):
            self._draw_wiring()                     # the numbers thinned, the names that no longer overlap
            self._draw_draft()

    def _recolour(self) -> None:
        c = view_colours.plan(self.source != "none")
        self.veil.setVisible(self.source != "none" and self.veil_strength > 0)
        if c == self.colours:
            return
        self.colours = c
        self.setBackgroundBrush(qcolour(c["bg"]))
        for overlay in (self.north, self.scale_bar, self.attribution):
            overlay.set_colours(c)
        self._laying_colours()
        if self.drawn is not None:
            self.show_project(*self.drawn, force=True)
        self.viewport().update()

    def show_project(self, project, results: dict, force: bool = False) -> None:
        """Draw the project; `results` maps a sub-field id to its layout.Result (filled ones only). The modules
        of a sub-field whose layout is the one already drawn stay as they are: thousands of modules are the cost
        of this call, and a change of the project draws them again only when their layout comes back (task 18c,
        step 8). `force` draws everything again (new colours)."""
        scene = self.scene()
        self.drawn = (project, results)
        focused, self.focused = self.focused, None
        if self.hover_item is not None:
            scene.removeItem(self.hover_item)
        self.hover_item, self.hovered = None, ("", "", "")
        c = self.colours
        for kind, items in self.items_by_kind.items():
            if kind not in ("modules", "groups"):
                for it in items:
                    scene.removeItem(it)
        self.items_by_kind = {}
        kept = {} if force else self.module_items
        drawn: dict[str, dict] = {}
        segments = []

        self.rings = {}
        self.ridges = {}                         # building id -> its ridges, lit when the pointer passes (16a)

        def add(kind, oid, ring, pen, brush, z):
            self.rings[(kind, oid)] = [tuple(map(float, p)) for p in ring]
            # a line of two tones: the outline over a dark halo on the photo, a light one on the light ground,
            # so that it reads on a light roof and on a dark one
            halo = scene.addPolygon(polygon(ring), cosmetic(c["halo"], pen.widthF() + view_colours.WIDTHS["halo"]))
            halo.setZValue(z - 0.01)
            halo.setData(0, kind)
            halo.setData(1, oid)
            halo.setData(2, "halo")
            self.items_by_kind.setdefault("halos", []).append(halo)
            item = scene.addPolygon(polygon(ring), pen, brush)
            item.setZValue(z)
            item.setData(0, kind)
            item.setData(1, oid)
            self.items_by_kind.setdefault(kind, []).append(item)
            pts = [tuple(map(float, p)) for p in ring]
            segments.extend(zip(pts, pts[1:] + pts[:1], strict=True))
            return item

        from . import underlays
        for i, u in enumerate(getattr(project, "underlays", [])):
            if not u.visible or not u.image:
                continue
            item = scene.addPixmap(underlays.pixmap(u))
            item.setTransform(underlays.transform(u))
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setOpacity(u.opacity)
            item.setZValue(Z_UNDERLAY + 0.01 * i)
            item.setData(0, "underlay")
            item.setData(1, u.id)
            self.items_by_kind.setdefault("underlays", []).append(item)
        W = view_colours.WIDTHS                      # the strokes' widths (R35)
        for b in project.buildings:
            add("building", b.id, b.footprint, cosmetic(c["bld_stroke"], W["building"]), QBrush(qcolour(c["bld_fill"])),
                Z_BUILDING)
            for i, p in enumerate(b.pitches()):
                if p.tilt > 0:
                    add("pitch", f"{b.id}:{i}", p.ring, cosmetic(c["pitch"], W["pitch"]), QBrush(Qt.BrushStyle.NoBrush),
                        Z_PITCH)
                    self._slope_arrow(p, b.id)          # one for every face of the roof
            self.ridges[b.id] = roofs.ridges(b.pitches(), b.height)
        for e in project.exclusions:
            add("exclusion", e.id, e.ring, cosmetic(c["exclusion"], W["exclusion"]),
                QBrush(qcolour(c["exclusion"]), Qt.BrushStyle.BDiagPattern), Z_EXCLUSION)
        for sf in project.subfields:
            add("subfield", sf.id, sf.ring, cosmetic(c["sub_stroke"], W["subfield"], Qt.PenStyle.DashLine),
                QBrush(qcolour(c["sub_fill"])), Z_SUBFIELD)
            r = results.get(sf.id)
            if r is None or not r.modules:
                continue
            entry = kept.get(sf.id)
            if entry is None or entry["result"] is not r:
                entry = self._module_items(sf.id, r)
            else:
                for it in entry["items"]:
                    it.setOpacity(1.0)
            drawn[sf.id] = entry
        for sfid, entry in self.module_items.items():
            if drawn.get(sfid) is not entry:
                for it in entry["items"]:
                    scene.removeItem(it)
        self.module_items = drawn
        self.module_corners = {sfid: (e["keys"], e["corners"]) for sfid, e in drawn.items()}
        self.module_rows = {sfid: e["rids"] for sfid, e in drawn.items()}
        self.items_by_kind["modules"] = [e["items"][0] for e in drawn.values()]
        self.items_by_kind["groups"] = [it for e in drawn.values() for it in e["items"][1:]]
        self.snapper.set_references(segments)
        self._draw_wiring()
        self._draw_draft()
        self._restyle_selection()
        if focused is not None:
            self.focus(focused)

    def _module_items(self, sfid: str, r) -> dict:
        """The modules of one layout drawn: one path item for all of them, from the array of their corners the
        layout gives (no polygon per module), and the fire-brigade groups."""
        c = self.colours
        corners = r.corners if getattr(r, "corners", None) is not None else np.array([m.corners for m in r.modules],
                                                                                   dtype=float)
        keys = r.keys if getattr(r, "keys", None) is not None else [m.key for m in r.modules]
        quads = np.asarray(corners, dtype=float).reshape(-1, 4, 2) * (1.0, -1.0)       # scene: y downwards
        path = QPainterPath()
        for q in quads.tolist():
            path.moveTo(q[0][0], q[0][1])
            path.lineTo(q[1][0], q[1][1])
            path.lineTo(q[2][0], q[2][1])
            path.lineTo(q[3][0], q[3][1])
            path.closeSubpath()
        scene = self.scene()
        W = view_colours.WIDTHS                      # the strokes' widths (R35)
        item = scene.addPath(path, cosmetic(c["module_line"], W["module_line"]), QBrush(qcolour(c["module"])))
        # the modules drawn once per zoom and kept as an image (study 12, P2-B): panning 8,547 modules went
        # from 76 to 0.6 ms a step at the whole view, from 87 to 11 ms at 0.3 m per pixel (offscreen,
        # 22/10/2026), for some 16 MB
        item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        item.setZValue(Z_MODULES)
        item.setData(0, "modules")
        item.setData(1, sfid)
        items = [item]
        for g in r.groups:
            # the fire-brigade groups in the guides' colour: yellow is the warnings' (study 12, C6)
            gi = scene.addPolygon(polygon(g), cosmetic(c["guide"], W["guide"], Qt.PenStyle.DotLine))
            gi.setZValue(Z_MODULES + 1)
            items.append(gi)
        return {"result": r, "items": items, "keys": keys, "corners": quads, "rids": [m.rid for m in r.modules]}

    def _module_polygon(self, sfid: str, key: str) -> QPolygonF | None:
        """The outline of one module drawn, for the selection and the pointer."""
        keys, quads = self.module_corners.get(sfid, ([], None))
        if key not in keys:
            return None
        return QPolygonF([QPointF(x, y) for x, y in quads[keys.index(key)].tolist()])

    # the rows (task 16c): a click on a module selects it, a second one on its row selects the row

    def rid_of(self, sfid: str, key: str) -> str:
        """The id of the row a module drawn is in ("" when it is not drawn)."""
        keys, _quads = self.module_corners.get(sfid, ([], None))
        rids = self.module_rows.get(sfid, [])
        if key not in keys or len(rids) != len(keys):
            return ""
        return rids[keys.index(key)] or ""

    def _row_polygon(self, oid: str) -> QPolygonF | None:
        """The outline of a row: the window's (row_info), else the rectangle about its modules drawn."""
        ring = self._row_ring(oid)
        return polygon(ring) if ring else None

    def _row_ring(self, oid: str) -> list | None:
        sfid, _sep, rid = oid.partition("/")
        info = self.row_info(oid) if self.row_info is not None else None
        if info and info.get("ring"):
            return [tuple(map(float, q)) for q in info["ring"]]
        keys, quads = self.module_corners.get(sfid, ([], None))
        rids = self.module_rows.get(sfid, [])
        pts = [(x, -y) for q, r in zip(quads if quads is not None else [], rids, strict=False) if r == rid
               for x, y in q.tolist()]
        if not pts:
            return None
        from shapely.geometry import MultiPoint
        hull = MultiPoint(pts).minimum_rotated_rectangle
        return [(float(x), float(y)) for x, y in list(hull.exterior.coords)[:-1]] if hull.geom_type == "Polygon" else None

    def _row_end(self) -> tuple[float, float] | None:
        """The end of the selected row's front edge: the grip that lengthens or shortens it (Select)."""
        kind, oid = self.selection
        if kind != "row" or self.row_info is None:
            return None
        info = self.row_info(oid)
        return tuple(info["end"]) if info and info.get("end") is not None else None

    # strings

    def set_wiring(self, wiring) -> None:
        self.wiring = wiring
        self._draw_wiring()
        self._draw_draft()

    # the strings in the Plant phase (R114-R117): a click chooses one, a string is drawn module by module

    def set_strings_mode(self, on: bool) -> None:
        """The Plant phase: a click on a module chooses its string, a double click draws it again; off, the plan is
        as in the Model (and a string being drawn is given up, without a word)."""
        self.strings_mode = bool(on)
        if not on:
            self.end_draft()

    def choose_string(self, index: int) -> None:
        if index != self.chosen_string:
            self.chosen_string = index
            self._draw_wiring()

    def string_rect(self, index: int) -> QRectF | None:
        """The modules of string `index` on the plan (scene), None when they are not drawn."""
        strings = getattr(self.wiring, "strings", None) or []
        if not 0 <= index < len(strings):
            return None
        self._router()
        order = [self.module_index.get((sf, key), -1) for sf, key, _c in strings[index].modules]
        order = [m for m in order if m >= 0]
        if not order:
            return None
        pts = self.router.quads[order].reshape(-1, 2)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        return QRectF(float(lo[0]), float(lo[1]), float(hi[0] - lo[0]), float(hi[1] - lo[1]))

    def show_string(self, index: int) -> None:
        """String `index` brought into view: framed when it is not all in the view or is very small in it, else left
        where it is (a string chosen next to the last one does not move the plan under the pointer)."""
        rect = self.string_rect(index)
        if rect is None:
            return
        view = self.mapToScene(self.viewport().rect()).boundingRect()
        if view.contains(rect) and max(rect.width(), rect.height()) > 0.12 * max(view.width(), view.height()):
            return
        self.fit(rect)
        self.user_moved = True

    def start_draft(self, modules: list, index: int = -1, where: str = "") -> None:
        """A string drawn from now: `modules` its first ones, (sub-field, key) in order (those of string `index`
        when it is drawn again, hidden meanwhile); `where` its inverter and input, for the words."""
        self.draft = [tuple(m) for m in modules]
        self.draft_index = index
        self.draft_where = where
        self.draft_drag = False
        self.draft_pointer = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocus()
        self._draw_wiring()
        self._draw_draft()
        self.draftChanged.emit([list(m) for m in self.draft])

    def end_draft(self) -> None:
        """No string drawn any longer (closed, given up, the phase left): nothing said."""
        if self.draft is None:
            return
        self.draft, self.draft_index, self.draft_drag, self.draft_pointer = None, -1, False, None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._draw_draft()
        self._draw_wiring()

    def finish_draft(self) -> None:
        """Enter or a double click: the string as drawn goes to the window."""
        if self.draft is None:
            return
        modules = [list(m) for m in self.draft]
        self.end_draft()
        self.draftFinished.emit(modules)

    def cancel_draft(self) -> None:
        """Esc: the string being drawn given up."""
        if self.draft is None:
            return
        self.end_draft()
        self.draftCancelled.emit()

    def draft_pop(self) -> None:
        """Backspace: the last module out of the string being drawn."""
        if self.draft:
            self.draft.pop()
            self._draw_draft()
            self.draftChanged.emit([list(m) for m in self.draft])

    def owner(self, sfid: str, key: str) -> int:
        """The string a module is in, -1 none; while a string is drawn again its own modules are in none."""
        if self.wiring is None:
            return -1
        i = self.wiring.string_of(sfid, key)
        return -1 if i == self.draft_index else i

    def _draft_take(self, hit: tuple, move: bool) -> bool:
        """Module `hit` at the end of the string being drawn; refused, with the reason in the bar, when it is in it
        already or in another string (with Shift held it is moved from there)."""
        if hit in self.draft:
            if hit != self.draft[-1]:
                self.hint.emit(_("This module is already number {n} of the string you are drawing.").format(
                    n=self.draft.index(hit) + 1))
            return False
        other = self.owner(*hit)
        if other >= 0 and not move:
            self.hint.emit(_("This module is in string {name}: hold Shift and click it to move it into this one.").format(
                name=self.wiring.strings[other].label))
            return False
        self.draft.append(hit)
        self._draw_draft()
        self.draftChanged.emit([list(m) for m in self.draft])
        return True

    def _module_at(self, view_pos) -> tuple | None:
        kind, sfid, key = self._pick(self.mapToScene(view_pos.toPoint()))
        return (sfid, key) if kind == "module" else None

    def _past_centre(self, sfid: str, key: str, scene_pos: QPointF) -> bool:
        """Whether the pointer is near enough the middle of a module to take it («connect when the pointer passes
        their middle», Sunny Design): within 0.35 of its shorter side from its centre."""
        keys, quads = self.module_corners.get(sfid, ([], None))
        if quads is None or key not in keys:
            return False
        q = quads[keys.index(key)]
        centre = q.mean(axis=0)
        side = min(math.dist(q[0], q[1]), math.dist(q[1], q[2]))
        return math.dist(centre, (scene_pos.x(), scene_pos.y())) <= 0.35 * side

    def _string_press(self, event) -> bool:
        """A press in the Plant phase. Drawing: the left button on a module takes it (and a drag goes on taking),
        elsewhere it says what to do; the right one opens the drawing's menu. Not drawing: the left button on a
        module chooses its string, the right one opens the module's menu. Anywhere else the press goes on as usual
        (the navigation, the selection)."""
        hit = self._module_at(event.position())
        button = event.button()
        if self.draft is not None:
            if button == Qt.MouseButton.LeftButton and not self.space:
                if hit is None:
                    self.hint.emit(_("Click the modules in order: Enter or a double click closes the string, "
                                     "Backspace takes back the last one, Esc gives it up."))
                    return True
                self._draft_take(hit, bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
                self.draft_drag = True
                return True
            if button == Qt.MouseButton.RightButton:
                self.stringMenu.emit(list(hit) if hit else [], event.globalPosition().toPoint())
                return True
            return False
        if hit is None:
            return False
        if button == Qt.MouseButton.LeftButton and not self.space:
            self.stringPicked.emit(*hit)
            return True
        if button == Qt.MouseButton.RightButton:
            self.stringMenu.emit(list(hit), event.globalPosition().toPoint())
            return True
        return False

    def show_wiring(self, on: bool) -> None:
        self.wiring_on = on
        self._draw_wiring()

    def _router(self):
        """The router of the strings' lines over the modules drawn (string_paths), made again when a layout drawn
        changes; with the index of each module in it."""
        from .. import string_paths
        signature = tuple((sf, id(q)) for sf, (_keys, q) in self.module_corners.items())
        if self.router is None or self.router_of != signature:
            index: dict = {}
            quads = []
            for sf, (keys, q) in self.module_corners.items():
                if q is None or not len(q):
                    continue
                for key in keys:
                    index[(sf, key)] = len(index)
                quads.append(q)
            self.module_index = index
            self.router = string_paths.Router(np.vstack(quads) if quads else np.zeros((0, 4, 2)))
            self.router_of = signature
        return self.router

    def _string_paths(self, order: list[int], jumped: dict | None = None):
        """The modules of a string filled, its line from middle to middle between modules next to each other, and
        its jumps around the modules it skips (string_paths): three painter paths in the scene."""
        router = self.router
        fill, solid, jump = QPainterPath(), QPainterPath(), QPainterPath()
        for m in order:
            q = router.quads[m].tolist()
            fill.moveTo(q[0][0], q[0][1])
            for corner in q[1:]:
                fill.lineTo(corner[0], corner[1])
            fill.closeSubpath()
        pairs = list(zip(order, order[1:], strict=False))
        blocked = [jumped[p] for p in pairs] if jumped is not None else router.blocked(pairs)
        for (a, b), skipped in zip(pairs, blocked, strict=True):
            if skipped:
                pts = router.route(a, b)
                jump.moveTo(*pts[0])
                for p in pts[1:]:
                    jump.lineTo(*p)
            else:
                solid.moveTo(*map(float, router.centres[a]))
                solid.lineTo(*map(float, router.centres[b]))
        return fill, solid, jump

    def _string_items(self, order: list[int], colour: QColor, width: float, z: float, alpha: int,
                      jumped: dict | None = None, outline: bool = False) -> list:
        """The items of a string: its modules filled in its colour (the modules it skips are not), the line between
        the modules next to each other over a dark halo, the jumps around the others dashed (R117)."""
        scene = self.scene()
        W = view_colours.WIDTHS
        fill_path, solid, jump = self._string_paths(order, jumped)
        tint = QColor(colour)
        tint.setAlpha(alpha)
        pen = cosmetic(colour, 1.5) if outline else QPen(Qt.PenStyle.NoPen)
        fill = scene.addPath(fill_path, pen, QBrush(tint))
        fill.setZValue(z - 0.4)
        items = [fill]
        halo_colour = QColor(10, 12, 16, 200)
        # the line lighter than the fill it runs over, the same hue: it reads on its own modules and on the roof
        light = QColor.fromRgbF(*(0.45 * c + 0.55 for c in colour.getRgbF()[:3]))
        for path, style in ((solid, Qt.PenStyle.SolidLine), (jump, Qt.PenStyle.DashLine)):
            if path.isEmpty():
                continue
            halo = scene.addPath(path, cosmetic(halo_colour, width + W["halo"]))
            halo.setZValue(z)
            line = scene.addPath(path, cosmetic(light, width, style))
            line.setZValue(z + 0.1)
            items += [halo, line]
        return items

    def _number_items(self, order: list[int], z: float) -> list:
        """The modules of a string numbered in its order (R57): every one when they have room on screen, else one in
        five or ten, the first and the last always."""
        scene = self.scene()
        small = design.font(design.Type.CAPTION, design.Type.BOLD, self.font())
        mpp = self.metres_per_pixel()
        self.numbered_at = mpp
        pts = [tuple(map(float, self.router.centres[m])) for m in order]
        gaps = [math.dist(a, b) for a, b in zip(pts, pts[1:], strict=False)]
        spacing = (sorted(gaps)[len(gaps) // 2] / mpp) if gaps else 99.0
        step = 1 if spacing >= 20 else 5 if spacing * 5 >= 24 else 10
        items = []
        last = len(pts)
        for n, (mx, my) in enumerate(pts, 1):
            if n not in (1, last) and n % step:
                continue
            back = ChipItem(str(n), small, QColor("#ffffff"), colours=self.colours)
            half = QPointF(back.boundingRect().width() / 2, back.boundingRect().height() / 2)
            back.setPos(QPointF(mx, my) - half)
            back.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            back.setZValue(z)
            scene.addItem(back)
            items.append(back)
        return items

    def _draw_wiring(self) -> None:
        """Each string in a tint of its own (theme_colors.string_tints; a string touching another never has its
        tint, string_paths.colours): its modules filled, a line through their middles while they are next to each
        other and a dashed jump around the modules it skips, so that a module skipped is seen (R117); the one chosen
        wider, outlined and numbered; at its first module its name (inverter.input.string) with the traffic light as
        a drawn symbol of the window (R138, R143); the modules in no string with a red outline. A string whose modules
        are not all drawn
        waits for the next layout; the string being drawn again is left to the drawing."""
        from .. import string_paths
        scene = self.scene()
        for it in self.items_by_kind.pop("wiring", []):
            scene.removeItem(it)
        strings = list(getattr(self.wiring, "strings", None) or [])
        router = self._router()
        orders = [[self.module_index.get((sf, key), -1) for sf, key, _c in s.modules] for s in strings]
        tints = self.string_tints or INPUT_COLOURS
        # each string's own colour from its first module: deleting a string does not repaint the others
        import zlib
        seeds = [zlib.crc32(f"{s.modules[0][0]}/{s.modules[0][1]}".encode()) if s.modules else i
                 for i, s in enumerate(strings)]
        self.string_colours = [tints[c] for c in string_paths.colours([[m for m in o if m >= 0] for o in orders],
                                                                      router, len(tints), seeds)]
        if not self.wiring_on or self.wiring is None:
            return
        states = self.string_states or {"ok": theme_colors.STATUS["good"], "check": theme_colors.STATUS["warning"],
                                        "fail": theme_colors.STATUS["critical"]}
        items = []
        # the modules in no string: a red outline each (Sunny Design), one path for all of them
        laid = self.module_index
        left = [(sf, key) for sf, key, _c in (getattr(self.wiring, "left", None) or []) if (sf, key) in laid]
        if left:
            outline = QPainterPath()
            for sf, key in left:
                q = router.quads[laid[(sf, key)]].tolist()
                outline.moveTo(q[0][0], q[0][1])
                for corner in q[1:]:
                    outline.lineTo(corner[0], corner[1])
                outline.closeSubpath()
            item = scene.addPath(outline, cosmetic(states["fail"], 2.0))
            item.setZValue(Z_WIRING - 0.5)
            item.setToolTip(ngettext("{n} module in no string", "{n} modules in no string", len(left)).format(n=len(left)))
            items.append(item)
        shown = [i for i, o in enumerate(orders) if o and min(o) >= 0 and i != self.draft_index]
        pairs = [(o[k], o[k + 1]) for i in shown for o in (orders[i],) for k in range(len(o) - 1)]
        jumped = dict(zip(pairs, router.blocked(pairs), strict=True))
        self.tagged_at = self.metres_per_pixel()
        named: list = []                                # the names placed, in the view's pixels: none over another
        for i in sorted(shown, key=lambda k: k != self.chosen_string):
            r, order = strings[i], orders[i]
            colour = QColor(self.string_colours[i])
            chosen = i == self.chosen_string
            mine = self._string_items(order, colour, 4.5 if chosen else 2.5, Z_WIRING, 190 if chosen else 140, jumped,
                                      outline=chosen)
            state = getattr(r, "state", "check")
            why = getattr(r, "why", "")
            tip = _("String {name}: inverter {i}, input {m}, {n} modules").format(
                name=r.label, i=r.inverter, m=r.mppt, n=len(r.modules)) + (f"\n{why}" if why else "")
            for it in mine:
                it.setToolTip(tip)
            items += mine
            x, y = r.modules[0][2]
            font = design.font(design.Type.SMALL, design.Type.BOLD, self.font())
            tag = ChipItem(r.label, font, colour, state, self.colours)
            box = tag.boundingRect()
            lift = box.height() + 6                     # above the first module's middle: its number stays seen
            at = self.mapFromScene(to_scene(x, y))
            place = box.translated(at.x(), at.y() - lift).adjusted(-2, -2, 2, 2)
            if any(place.intersects(other) for other in named):
                continue                                # zoomed out: its colour says it, its tooltip names it
            named.append(place)
            tag.setPos(to_scene(x, y))
            tag.offset = QPointF(0, -lift)              # local pixels, not scene metres (ItemIgnoresTransformations)
            tag.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations)
            scene.addItem(tag)
            tag.setZValue(Z_WIRING + 1 + (0.5 if chosen else 0.0))
            tag.setToolTip(tip)
            tag.setData(0, "string")
            tag.setData(1, i)
            items.append(tag)
            if chosen:
                items += self._number_items(order, Z_WIRING + 0.8)
        self.items_by_kind["wiring"] = items

    def draft_colour(self) -> str:
        """The tint of the string being drawn: its own when drawn again, else one its neighbours have not."""
        tints = self.string_tints or INPUT_COLOURS
        if 0 <= self.draft_index < len(self.string_colours):
            return self.string_colours[self.draft_index]
        used = set(self.string_colours)
        n = len(getattr(self.wiring, "strings", None) or [])
        return next((c for c in tints[n % len(tints):] + tints[:n % len(tints)] if c not in used), tints[n % len(tints)])

    def _draw_draft(self) -> None:
        """The string being drawn, over the others: its modules filled and outlined in its colour, numbered in the
        order clicked, its line (jumps dashed, as the strings drawn), and a line from its last module to the
        pointer."""
        scene = self.scene()
        for it in self.items_by_kind.pop("draft", []):
            scene.removeItem(it)
        if self.draft:
            self._router()
            order = [m for m in (self.module_index.get(x, -1) for x in self.draft) if m >= 0]
            if order:
                items = self._string_items(order, QColor(self.draft_colour()), 3.5, Z_WIRING + 2, 200, outline=True)
                items += self._number_items(order, Z_WIRING + 2.8)
                self.items_by_kind["draft"] = items
        self._draw_band()

    def _draw_band(self) -> None:
        """The line from the last module of the string being drawn to the pointer, dashed."""
        scene = self.scene()
        for it in self.items_by_kind.pop("draft_band", []):
            scene.removeItem(it)
        if not self.draft or self.draft_pointer is None:
            return
        m = self.module_index.get(self.draft[-1], -1)
        if m < 0 or self.router is None:
            return
        a = QPointF(*map(float, self.router.centres[m]))
        line = scene.addLine(QLineF(a, self.draft_pointer), cosmetic(QColor(self.draft_colour()), 1.5,
                                                                     Qt.PenStyle.DashLine))
        line.setZValue(Z_WIRING + 2.5)
        self.items_by_kind["draft_band"] = [line]

    def _slope_arrow(self, pitch, bid) -> None:
        """An arrow down the slope, as roof drawings mark it, with the slope in degrees."""
        xs = [q[0] for q in pitch.ring]
        ys = [q[1] for q in pitch.ring]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        fx, fy = geo.facing_vector(pitch.azimuth)
        size = max(1.0, 0.25 * min(max(xs) - min(xs), max(ys) - min(ys)))
        a = to_scene(cx - fx * size / 2, cy - fy * size / 2)
        b = to_scene(cx + fx * size / 2, cy + fy * size / 2)
        path = QPainterPath(a)
        path.lineTo(b)
        ang = math.atan2(b.y() - a.y(), b.x() - a.x())
        for d in (2.6, -2.6):
            path.moveTo(b)
            path.lineTo(b.x() - 0.25 * size * math.cos(ang + d / 6), b.y() - 0.25 * size * math.sin(ang + d / 6))
        item = self.scene().addPath(path, cosmetic(self.colours["pitch"], 1.5))
        item.setZValue(Z_PITCH)
        self.items_by_kind.setdefault("arrows", []).append(item)

    # selection

    def set_selection(self, kind: str, oid: str) -> None:
        changed = (kind, oid) != self.selection
        if (kind, oid) != ("subfield", self.selected_module[0]):
            self.selected_module = ("", "")            # a module selected belongs to its sub-field's selection
        self.selection = (kind, oid)
        self._restyle_selection()
        if self.tool == "move" and (changed or self.gesture is None):
            self._drop_gesture()
            self.hint.emit(self._move_hint())

    def _restyle_selection(self) -> None:
        self.viewport().update()                  # the measures of the sides go with the selection, all over the view
        for it in self.items_by_kind.get("selection", []):
            self.scene().removeItem(it)
        self.items_by_kind["selection"] = []
        kind, oid = self.selection
        c = self.colours
        # the colour of the kind selected (R67: a building amber, a sub-field blue, an exclusion red), a halo under
        # a line and a light veil of it inside: it reads on the photo, on the modules and on the light ground
        sel = view_colours.kind_colour(kind)
        tint = qcolour(sel)
        tint.setAlpha(30)
        W = view_colours.WIDTHS
        for it in self.items_by_kind.get(kind, []):
            if it.data(1) == oid:
                for pen, brush, z in ((cosmetic(c["halo"], W["select"] + W["select_halo"]), QBrush(tint), 0.0),
                                      (cosmetic(sel, W["select"]), QBrush(Qt.BrushStyle.NoBrush), 0.1)):
                    halo = self.scene().addPolygon(it.polygon(), pen, brush)
                    halo.setZValue(Z_SELECTION + z)
                    self.items_by_kind["selection"].append(halo)
        sf, key = self.selected_module
        poly = self._module_polygon(sf, key) if key else None
        if kind == "row":
            ring = self._row_ring(oid)
            if ring:
                self.rings[(kind, oid)] = ring              # Move takes it as any outline
                poly = polygon(ring)
        if poly is not None:
            mod = view_colours.kind_colour("module")
            fill = qcolour(mod)
            fill.setAlpha(110)
            for pen, brush, z in ((cosmetic(c["halo"], W["select_module"] + W["select_halo"]),
                                   QBrush(Qt.BrushStyle.NoBrush), 0.0),
                                  (cosmetic(mod, W["select_module"]), QBrush(fill), 0.1)):
                halo = self.scene().addPolygon(poly, pen, brush)
                halo.setZValue(Z_SELECTION + z)
                self.items_by_kind["selection"].append(halo)

    def _pick(self, scene_pos: QPointF, pixels: float = 0.0):
        order = {"exclusion": 0, "modules": 1, "subfield": 2, "pitch": 3, "building": 4}
        # inside the outline, not inside the item's shape: with a dashed pen Qt's shape leaves out a band along the
        # edges (stroke and fill cancel out), and a click by the edge of a sub-field selected its building
        hits = [it for it in self.scene().items(scene_pos, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
                if it.data(0) in order and (it.data(0) == "modules" or
                                            it.polygon().containsPoint(scene_pos, Qt.FillRule.OddEvenFill))]
        hits.sort(key=lambda it: order[it.data(0)])
        for it in hits:
            if it.data(0) == "modules":
                keys, quads = self.module_corners.get(it.data(1), ([], None))
                i = _quad_at(quads, scene_pos.x(), scene_pos.y())
                if i >= 0:
                    return "module", it.data(1), keys[i]
            elif it.data(0) == "exclusion":
                return "exclusion", it.data(1), ""
        if pixels > 0.0:
            reach = pixels * self.metres_per_pixel()
            best = (-1, math.inf)
            found = ("", "")
            for sfid, (keys, quads) in self.module_corners.items():
                i, distance = _quad_near(quads, scene_pos.x(), scene_pos.y(), reach)
                if i >= 0 and distance < best[1]:
                    best, found = (i, distance), (sfid, keys[i])
            if found[0]:
                return "module", *found
        for it in hits:
            if it.data(0) != "modules":
                return it.data(0), it.data(1), ""
        return "", "", ""

    def selection_back(self) -> bool:
        """Escape: from a row or module to its sub-field, then to the building and the site."""
        kind, oid = self.selection
        project = self.drawn[0] if self.drawn is not None else None
        if kind == "row":
            target = ("subfield", oid.partition("/")[0])
        elif self.selected_module[0]:
            target = ("subfield", self.selected_module[0])
        elif kind in ("subfield", "exclusion") and project is not None:
            things = project.subfields if kind == "subfield" else project.exclusions
            thing = next((x for x in things if x.id == oid), None)
            target = ("building", thing.building) if thing is not None and thing.building else ("site", "")
        elif kind == "building":
            target = ("site", "")
        else:
            return False
        self.selected_module = ("", "")
        self.selection = target
        self._restyle_selection()
        self._hover("", "", "")
        self.picked.emit(*target)
        self.hint.emit(hints()["select"])
        return True

    # a side picked on the plan

    def pick_edge(self, purpose: str, kind: str, oid: str, ring) -> None:
        """Wait for a click on a side of `ring` (the eave of a roof, a side to measure); Esc gives up."""
        self.edge_pick = (purpose, kind, oid, [tuple(map(float, p)) for p in ring])
        self.edge_hover = None
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hint.emit(_("Click the side on the plan; Esc leaves it as it is."))
        self.viewport().update()

    def pick_points(self, purpose: str, hints: list[str]) -> None:
        """Wait for as many clicks on the plan as `hints` (each said before its click): two points of an image to
        put it in scale, where to move it from and to. Esc gives up; the views still pan and zoom meanwhile."""
        self.point_pick = (purpose, len(hints), [], list(hints))
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.hint.emit(hints[0])
        self.viewport().update()

    def _end_point_pick(self) -> None:
        self.point_pick = None
        self.setCursor(Qt.CursorShape.ArrowCursor if self.tool == "select" else Qt.CursorShape.CrossCursor)
        self.viewport().update()

    def _end_pick(self) -> None:
        self.edge_pick = None
        self.edge_hover = None
        self.setCursor(Qt.CursorShape.ArrowCursor if self.tool == "select" else Qt.CursorShape.CrossCursor)
        self.viewport().update()

    def _vertex_near(self, view_pos, pixels: float = 8.0) -> int | None:
        """The corner of the selected outline under the pointer, if any."""
        ring = self.rings.get(self.selection)
        if not ring or self.selection[0] not in ("building", "subfield", "exclusion"):
            return None
        here = from_scene(self.mapToScene(view_pos))
        reach = pixels * self.metres_per_pixel()
        best = min(range(len(ring)), key=lambda i: math.dist(ring[i], here))
        return best if math.dist(ring[best], here) <= reach else None

    def _side_near(self, ring, view_pos, pixels: float = 14.0) -> int | None:
        return sides.nearest(ring, from_scene(self.mapToScene(view_pos)), pixels * self.metres_per_pixel())

    # tools

    def set_tool(self, tool: str) -> None:
        self.tool = tool
        self.chain = []
        self.snap = None
        self.typed = ""
        self.measure = []
        self.row_start, self.row_drag = None, None
        self.snapper.reset()
        self._drop_gesture()
        self.rotate_next = False
        self.setCursor(Qt.CursorShape.ArrowCursor if tool == "select" else Qt.CursorShape.CrossCursor)
        # selecting, only what changes is drawn again (the outline under the pointer); drawing, the guides follow
        # the pointer over the whole view
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate if tool == "select" else
                                   QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._hover("", "", "")
        self.hint.emit(self._move_hint() if tool == "move" else hints()[tool])
        self.viewport().update()

    def _hover(self, kind: str, oid: str, key: str) -> None:
        """Outline what a click would select (study 12, V3): one item added or taken away, the plan not drawn again."""
        if (kind, oid, key) == self.hovered:
            return
        self.hovered = (kind, oid, key)
        if self.hover_item is not None:
            self.scene().removeItem(self.hover_item)
            self.hover_item = None
        if not kind:
            return
        poly = None
        if kind == "module":
            poly = self._module_polygon(oid, key)
        elif kind == "row":
            poly = self._row_polygon(oid)
        else:
            poly = next((it.polygon() for it in self.items_by_kind.get(kind, []) if it.data(1) == oid), None)
        if poly is None:
            return
        # the kind's colour, lighter, dashed over a halo (R67)
        W = view_colours.WIDTHS
        light = view_colours.kind_colour(kind, hover=True)
        pens = (cosmetic(self.colours["halo"], W["hover"] + W["select_halo"]),
                cosmetic(light, W["hover"], Qt.PenStyle.DashLine))
        items = [self.scene().addPolygon(poly, pen) for pen in pens]
        if kind in ("building", "pitch"):
            # the ridges of the roof, whole and thicker: where the ridge height of the Roof group stands (16a, A6)
            ridge_pen = cosmetic(light, W["hover"] + 2)
            for (ax, ay), (bx, by) in self.ridges.get(oid.split(":")[0], []):
                items.append(self.scene().addLine(QLineF(ax, -ay, bx, -by), ridge_pen))
        self.hover_item = self.scene().createItemGroup(items)
        self.hover_item.setZValue(Z_SELECTION - 1)

    def metres_per_pixel(self) -> float:
        return 1.0 / max(math.hypot(self.transform().m11(), self.transform().m21()), 1e-9)

    def drawing(self) -> bool:
        """An outline being drawn, with at least one point."""
        return self.tool in DRAWING and bool(self.chain)

    def close_outline(self) -> None:
        """«Close» of the drawing's menu: the outline as it is, closed back to its first point."""
        self._finish()

    def drop_last(self) -> None:
        """«Remove the last point» of the drawing's menu (Backspace)."""
        if self.chain:
            self.chain.pop()
            self.viewport().update()

    def cancel_outline(self) -> None:
        """«Cancel the drawing» (Esc): the points given so far go."""
        self.chain = []
        self.snap = None
        self.typed = ""
        self.snapper.reset()
        self.viewport().update()

    def _finish(self) -> None:
        if len(self.chain) >= 3:
            ring = list(self.chain)
            tool = self.tool
            self.chain = []
            self.snap = None
            self.typed = ""
            self.snapper.reset()
            self.polygonDrawn.emit(tool, ring)
        self.viewport().update()

    def _apply_typed(self) -> bool:
        """What was typed while drawing: "length" along the current direction, "length;angle" at that turn
        from the last side (positive to the left; for the first side the bearing from North), and in
        rectangle mode, after two corners, the depth on the side the pointer is."""
        if not self.typed or not self.chain:
            return False
        parts = self.typed.replace(",", ".").split(";")
        try:
            length = float(parts[0])
            angle = float(parts[1]) if len(parts) > 1 and parts[1].strip() not in ("", "-") else None
        except ValueError:
            self.typed = ""
            return False
        self.typed = ""
        last = self.chain[-1]
        here = self.snap.point if self.snap else last
        if self.rect_mode and len(self.chain) == 2:
            self.chain = self._rectangle(here, depth=length)
            self._finish()
            return True
        if angle is not None:
            if len(self.chain) >= 2:
                prev = self.chain[-2]
                theta = math.atan2(last[1] - prev[1], last[0] - prev[0]) + math.radians(angle)
            else:
                theta = math.radians(90.0 - angle)
            target = (last[0] + math.cos(theta), last[1] + math.sin(theta))
        else:
            target = here
            if math.dist(target, last) < 1e-9:
                if len(self.chain) >= 2:
                    prev = self.chain[-2]
                    target = (2 * last[0] - prev[0], 2 * last[1] - prev[1])
                else:
                    target = (last[0] + 1.0, last[1])
        d = math.dist(target, last)
        self.chain.append((last[0] + (target[0] - last[0]) / d * length, last[1] + (target[1] - last[1]) / d * length))
        return True

    def _end_row(self, end) -> None:
        """The second point of a row: the window lays it; the tool waits for the next row."""
        start = self.row_start
        self.row_start, self.typed, self.snap = None, "", None
        self.snapper.reset()
        self.rowDrawn.emit([float(start[0]), float(start[1])], [float(end[0]), float(end[1])])
        self.viewport().update()

    def _apply_typed_row(self) -> bool:
        """A length typed for the row being drawn: that many metres from its start towards the pointer."""
        if not self.typed or self.row_start is None:
            return False
        length = move.parse(self.typed)
        self.typed = ""
        if length is None or length <= 0:
            self.viewport().update()
            return False
        here = self.snap.point if self.snap else self._pointer()
        dx, dy = here[0] - self.row_start[0], here[1] - self.row_start[1]
        d = math.hypot(dx, dy)
        ux, uy = (dx / d, dy / d) if d > 1e-9 else (1.0, 0.0)
        self._end_row((self.row_start[0] + ux * length, self.row_start[1] + uy * length))
        return True

    def _row_pointer(self) -> tuple[float, float] | None:
        """Where the row being drawn ends now: the pointer snapped, or the length typed along it."""
        if self.row_start is None:
            return None
        here = self.snap.point if self.snap else None
        length = move.parse(self.typed) if self.typed else None
        if here is None:
            return None
        if length is not None and length > 0:
            dx, dy = here[0] - self.row_start[0], here[1] - self.row_start[1]
            d = math.hypot(dx, dy)
            ux, uy = (dx / d, dy / d) if d > 1e-9 else (1.0, 0.0)
            return (self.row_start[0] + ux * length, self.row_start[1] + uy * length)
        return here

    def _rectangle(self, point, depth: float | None = None) -> list[tuple[float, float]]:
        """The rectangle on the first two corners, as deep as `point` lies from their side (or `depth`, on
        the side of `point`)."""
        (ax, ay), (bx, by) = self.chain[0], self.chain[1]
        n = math.hypot(bx - ax, by - ay) or 1.0
        nx, ny = -(by - ay) / n, (bx - ax) / n
        h = (point[0] - bx) * nx + (point[1] - by) * ny
        if depth is not None:
            h = math.copysign(abs(depth), h if abs(h) > 1e-9 else 1.0)
        return [(ax, ay), (bx, by), (bx + nx * h, by + ny * h), (ax + nx * h, ay + ny * h)]

    def _depth(self, point) -> float:
        """How far a point lies from the line of the first side of the chain."""
        (ax, ay), (bx, by) = self.chain[0], self.chain[1]
        n = math.hypot(bx - ax, by - ay) or 1.0
        return abs((point[0] - ax) * (by - ay) - (point[1] - ay) * (bx - ax)) / n

    def toggle_rectangle(self) -> None:
        self.rect_mode = not self.rect_mode
        self.hint.emit(_("Rectangle mode: two corners give a side, the third click or a typed number the depth.")
                       if self.rect_mode else hints()[self.tool])
        self.viewport().update()

    # Move and Rotate (task 16b, study 16 B): the plan collects the points and the keys, move.Gesture does the sums,
    # the window applies the change as one step

    def _movable(self) -> bool:
        kind, oid = self.selection
        return self.tool == "move" and kind in MOVABLE and (kind, oid) in self.rings

    def _gesture(self) -> move.Gesture | None:
        """The gesture on the selection, made when it is first needed."""
        if not self._movable():
            return None
        kind, oid = self.selection
        if self.gesture is None or (self.gesture.kind, self.gesture.oid) != (kind, oid):
            project = self.drawn[0] if self.drawn is not None else None
            self.gesture = move.Gesture(kind, oid, self._middle())
            self.move_rings = ((move.moving(project, kind, oid) if project is not None else [])
                               or [list(self.rings[(kind, oid)])])
            if self.rotate_next:
                self.gesture.to_rotate(self._pointer(), self._near())
        return self.gesture

    def _drop_gesture(self) -> None:
        self.gesture = None
        self.grip_press = None
        self.move_pointer = None
        self.move_rings = []
        self.lock_dir = None
        self.snapper.reset()
        self.viewport().update()

    def _pointer(self) -> tuple[float, float]:
        """Where the pointer is on the plan: the last place it was seen, snapped, or the real one."""
        if self.move_pointer is not None:
            return self.move_pointer
        return from_scene(self.mapToScene(self.mapFromGlobal(self.cursor().pos())))

    def _near(self) -> float:
        """Eight pixels in metres: a pointer this close to the centre of a turn gives it no direction."""
        return 8.0 * self.metres_per_pixel()

    def start_rotate(self) -> None:
        """Rotate from the bar: Move turning the selection about its middle (or the next object picked)."""
        self.rotate_next = True
        g = self._gesture()
        if g is not None and g.mode != "rotate":
            g.to_rotate(self._pointer(), self._near())
        self.moveModeChanged.emit("rotate")
        self.hint.emit(self._move_hint())
        self.viewport().update()

    def _move_hint(self) -> str:
        if not self._movable():
            return hints()["move"]
        g = self.gesture
        if g is not None and g.mode == "rotate":
            return _("Rotate about the cross: click, or type the angle and Enter; steps of 15°, 5° with Ctrl, 90° "
                     "with Shift. C makes a copy, R goes back to Move, Esc leaves.")
        if g is not None and g.base is not None:
            return _("Click where it goes, or type the distance and Enter (3 is 3 m along the pointer, 3;2 is 3 m "
                     "East and 2 m North, Tab for the direction). Ctrl held at the click, or C, makes a copy.")
        return _("Move: click a base point, or type the move. R turns it (R is the rectangle only outside Move). "
                 "Arrows: 10 cm, 1 m with Shift, 1 cm with Ctrl. Esc leaves.")

    def _angle_step(self) -> float:
        return move.angle_step(self.move_mods) if self.snaps_on else 0.0

    def _move_cursor(self, scene_pos: QPointF) -> None:
        """The pointer in Move: what a click would take, with nothing to move; else the point it goes to, with the
        snaps from the base point, or Shift keeping the direction; turning, the pointer as it is."""
        cursor = from_scene(scene_pos)
        if not self._movable():
            self.snap, self.move_pointer = None, None
            kind, oid, key = self._pick(scene_pos, PICK_PX)
            self._hover(kind, oid, key)
            self.cursorInfo.emit(f"E {number(cursor[0])}  N {number(cursor[1])} m")
            self.viewport().update()
            return
        self._hover("", "", "")
        g = self.gesture
        if g is not None and g.mode == "rotate":
            self.snap, self.move_pointer = None, cursor
        else:
            chain = [g.base] if g is not None and g.base is not None else []
            if chain and self.lock_dir is not None:
                last = chain[-1]
                t = (cursor[0] - last[0]) * self.lock_dir[0] + (cursor[1] - last[1]) * self.lock_dir[1]
                point = (last[0] + t * self.lock_dir[0], last[1] + t * self.lock_dir[1])
                self.snap = Snapper._measure(Snap(point, "direction", [Guide(last, point, "polar", "⇧")]), chain)
            else:
                self.snap = self.snapper.snap(cursor, chain, self.metres_per_pixel(), free=not self.snaps_on)
            self.move_pointer = self.snap.point
        x, y = self.move_pointer
        info = f"E {number(x)}  N {number(y)} m"
        if g is not None and g.mode == "move" and g.base is not None:
            dx, dy = g.offset(self.move_pointer)
            info += f"   ·   ΔE {number(dx)}  ΔN {number(dy)} m"
        self.cursorInfo.emit(info)
        self.viewport().update()

    def _move_press(self, position: QPointF, modifiers) -> None:
        """A click in Move: the object to move, with nothing selected; the base point; where it goes."""
        mods = self._mods(modifiers)
        self.move_mods = mods
        scene_pos = self.mapToScene(position.toPoint())
        if not self._movable():
            kind, oid, _key = self._pick(scene_pos, PICK_PX)
            if kind == "module":
                kind = "subfield"
            elif kind == "pitch":
                kind, oid = "building", oid.split(":")[0]
            if kind in MOVABLE:
                self.selected_module = ("", "")
                self.selection = (kind, oid)
                self._restyle_selection()
                self.picked.emit(kind, oid)
                self.hint.emit(self._move_hint())
            return
        grip = self._grip_at(position)
        g = self.gesture
        if grip is not None and (g is None or g.mode == "move" and g.base is None and not g.typing):
            self._grip_press(grip, position)
            return
        self._move_cursor(scene_pos)
        g = self._gesture()
        if g.mode == "move" and g.base is None and not g.typing:
            g.base = self.move_pointer
            self.snapper.reset()
            self.hint.emit(self._move_hint())
            self.viewport().update()
            return
        self._apply_gesture(mods)

    def _transform_now(self) -> dict | None:
        """What the gesture would do with the pointer where it is: the move or the turn, as the window takes it."""
        g = self.gesture
        if g is None:
            return None
        pointer = self.move_pointer if self.move_pointer is not None else (g.base or g.middle)
        if g.mode == "rotate":
            about = g.about or g.middle
            return {"mode": "rotate", "cx": about[0], "cy": about[1], "degrees": g.angle(pointer, self._angle_step())}
        dx, dy = g.offset(pointer)
        return {"mode": "move", "dx": dx, "dy": dy}

    def _apply_gesture(self, mods: set) -> None:
        """The click that ends the gesture (or Enter): the window applies it as one step. Ctrl held makes a copy of
        a move; C, of anything."""
        g = self.gesture
        what = self._transform_now()
        if g is None or what is None:
            return
        what["copy"] = g.copy or (g.mode == "move" and "ctrl" in mods)
        kind, oid = g.kind, g.oid
        still = (abs(what["degrees"]) < 1e-9 if what["mode"] == "rotate"
                 else math.hypot(what["dx"], what["dy"]) < 1e-9)
        self._drop_gesture()
        self.moveModeChanged.emit("rotate" if self.rotate_next else "move")
        self.hint.emit(self._move_hint())
        if not still:
            self.transformRequested.emit(kind, oid, what)

    def _move_owns(self, event) -> bool:
        """The keys Move takes before the window's commands (a ShortcutOverride accepted)."""
        key, mods = event.key(), self._mods(event.modifiers())
        if key in ARROWS:
            return True
        if mods & {"ctrl", "alt"}:
            return False
        text = event.text()
        return key in (Qt.Key.Key_R, Qt.Key.Key_C, Qt.Key.Key_Tab, Qt.Key.Key_Backtab, Qt.Key.Key_Return,
                       Qt.Key.Key_Enter, Qt.Key.Key_Escape, Qt.Key.Key_Backspace) or \
            bool(text) and all(c.isdigit() or c in ",.-;" for c in text)

    def _move_key(self, event) -> bool:
        """A key in Move; False when it is not Move's (it goes on as usual)."""
        key, text = event.key(), event.text()
        mods = self._mods(event.modifiers())
        if key == Qt.Key.Key_Control:
            self.move_mods.add("ctrl")
        if key == Qt.Key.Key_Shift:
            self.move_mods.add("shift")
        g = self.gesture
        if key == Qt.Key.Key_Escape:
            if g is not None and g.typing:
                g.clear()
                self.viewport().update()
                return True
            self._drop_gesture()
            self.toolLeft.emit()
            return True
        if key == Qt.Key.Key_Space and g is not None and g.grip and not event.isAutoRepeat():
            g.cycle(self._pointer(), self._near())             # a grip hot: Space goes round the modes (AutoCAD)
            self.moveModeChanged.emit(g.mode)
            self.hint.emit(self._move_hint())
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return True
        if key == Qt.Key.Key_R and not mods & {"ctrl", "alt"}:
            g = self._gesture()
            if g is None:
                self.rotate_next = not self.rotate_next
            elif g.mode == "move":
                g.to_rotate(self._pointer(), self._near())
            else:
                g.to_move()
                self.rotate_next = False
            mode = g.mode if g is not None else ("rotate" if self.rotate_next else "move")
            self.moveModeChanged.emit(mode)
            self.hint.emit(self._move_hint())
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return True
        if not self._movable():
            return False
        if key in ARROWS:
            dx, dy = move.nudge(ARROWS[key], mods)
            kind, oid = self.selection
            self.transformRequested.emit(kind, oid, {"mode": "move", "dx": dx, "dy": dy, "copy": False,
                                                     "nudge": True})
            return True
        g = self._gesture()
        if key == Qt.Key.Key_Shift and g.mode == "move" and g.base is not None and self.snap and self.snap.length:
            d = math.dist(self.snap.point, g.base)
            self.lock_dir = ((self.snap.point[0] - g.base[0]) / d, (self.snap.point[1] - g.base[1]) / d)
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return True
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift):
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return True
        if key == Qt.Key.Key_C and not mods & {"ctrl", "alt"}:
            g.copy = not g.copy
            self.viewport().update()
            return True
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            g.tab()
        elif key == Qt.Key.Key_Backspace:
            g.backspace()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if g.grip and not g.typing:
                g.cycle(self._pointer(), self._near())
                self.moveModeChanged.emit(g.mode)
                self.hint.emit(self._move_hint())
            elif g.mode == "rotate" or g.base is not None or g.typing:
                self._apply_gesture(mods)
        elif not (text and g.type(text)):
            return False
        self.viewport().update()
        return True

    def _grips(self) -> dict:
        """The grips of the selection in Move (study 16, B3): in its middle one that moves it, on its outline (the middle
        of its northernmost side) one that turns it."""
        if not self._movable():
            return {}
        ring = self.rings[self.selection]
        sides_ = list(zip(ring, ring[1:] + ring[:1], strict=True))
        a, b = max(sides_, key=lambda s: (s[0][1] + s[1][1], -(s[0][0] + s[1][0])))
        return {"move": self._middle(), "rotate": ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)}

    def _middle(self) -> tuple[float, float]:
        """The middle of the selection (move.centre), or of its corners when the project drawn is not at hand."""
        ring = self.rings[self.selection]
        project = self.drawn[0] if self.drawn is not None else None
        found = move.centre(project, *self.selection) if project is not None else None
        return found or (sum(q[0] for q in ring) / len(ring), sum(q[1] for q in ring) / len(ring))

    def _grip_at(self, position: QPointF) -> str | None:
        """The grip under the pointer, within 8 pixels."""
        for name, point in self._grips().items():
            p = self.mapFromScene(to_scene(*point))
            if math.hypot(p.x() - position.x(), p.y() - position.y()) <= 8.0:
                return name
        return None

    def _grip_press(self, grip: str, position: QPointF) -> None:
        """A press on a grip: the gesture begins there, hot (Enter or Space go round Move and Rotate, as AutoCAD's
        grips); dragged, it ends at the release; clicked, at the next click."""
        self._drop_gesture()
        g = self._gesture()
        g.grip = True
        point = self._grips()[grip]
        if grip == "move":
            g.mode, g.base = "move", point
        else:
            g.mode = "move"
            g.to_rotate(point, self._near())
        self.grip_press = QPointF(position)
        self.move_pointer = point
        self.moveModeChanged.emit(g.mode)
        self.hint.emit(_("Drag the grip, or click where it goes; Enter or Space switch between Move and Rotate."))
        self.viewport().update()

    def _moved_rings(self) -> list:
        """The outlines that move with the selection, where the gesture puts them now."""
        g, what = self.gesture, self._transform_now()
        if what is None or (g.mode == "move" and g.base is None and not g.typing):
            return []
        f = (move.turn(what["cx"], what["cy"], what["degrees"]) if what["mode"] == "rotate"
             else move.shift(what["dx"], what["dy"]))
        return [[f(*q) for q in ring] for ring in self.move_rings]

    def _draw_move(self, painter: QPainter) -> None:
        """Move on the plan: the outlines where they would go, dashed, the base point and the vector, or the centre of
        the turn with where it started and where it is."""
        g = self.gesture
        c, W = self.colours, view_colours.WIDTHS
        accent, draw = qcolour(c["sel"]), qcolour(c["draw"])
        r = 5 * self.metres_per_pixel()
        for name, point in self._grips().items():           # the grips: a square that moves, a circle that turns
            p = to_scene(*point)
            hot = g is not None and g.grip and (name == "rotate") == (g.mode == "rotate")
            painter.setPen(cosmetic(c["halo"], 1.6 + W["halo"]))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            shape = QRectF(p.x() - r, p.y() - r, 2 * r, 2 * r)
            painter.drawRect(shape) if name == "move" else painter.drawEllipse(shape)
            painter.setPen(cosmetic(accent, 1.6))
            painter.setBrush(QBrush(accent) if hot else QBrush(qcolour(c["label_bg"])))
            painter.drawRect(shape) if name == "move" else painter.drawEllipse(shape)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if g is None or self.move_pointer is None:
            return
        for i, ring in enumerate(self._moved_rings()):
            poly = QPolygonF([to_scene(*q) for q in ring])
            painter.setPen(cosmetic(c["halo"], (W["draw"] if i == 0 else 1.2) + W["halo"]))
            painter.drawPolygon(poly)
            painter.setPen(cosmetic(accent, W["draw"] if i == 0 else 1.2, Qt.PenStyle.DashLine))
            painter.drawPolygon(poly)
        if g.mode == "rotate":
            about = g.about or g.middle
            centre = to_scene(*about)
            painter.setPen(cosmetic(qcolour(c["guide"]), 1, Qt.PenStyle.DashLine))
            if g.start is not None:
                painter.drawLine(QLineF(centre, to_scene(*g.start)))
            painter.setPen(cosmetic(draw, W["draw"]))
            painter.drawLine(QLineF(centre, to_scene(*self.move_pointer)))
            self._mark(painter, centre, draw, "intersection")
        elif g.base is not None:
            dx, dy = g.offset(self.move_pointer)
            a, b = to_scene(*g.base), to_scene(g.base[0] + dx, g.base[1] + dy)
            painter.setPen(cosmetic(c["halo"], W["draw"] + W["halo"]))
            painter.drawLine(QLineF(a, b))
            painter.setPen(cosmetic(draw, W["draw"], Qt.PenStyle.DashLine))
            painter.drawLine(QLineF(a, b))
            self._mark(painter, a, draw, "vertex")

    def _move_labels(self) -> list[str]:
        g = self.gesture
        what = self._transform_now()
        if g is None or what is None:
            return []
        if what["mode"] == "rotate":
            lines = [_("rotation {angle}°").format(angle=degrees_text(what["degrees"]))]
        elif g.base is None and not g.typing:
            return []
        else:
            lines = [_("{length} m").format(length=number(math.hypot(what["dx"], what["dy"]))),
                     _("E {dx} m, N {dy} m").format(dx=number(what["dx"]), dy=number(what["dy"]))]
        if g.typing:
            lines.insert(0, g.label())
        if g.copy or (g.mode == "move" and "ctrl" in self.move_mods):
            lines.append(_("a copy"))
        return lines

    # events

    def wheelEvent(self, event):
        pixel = event.pixelDelta()
        if not pixel.isNull() and not event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # a touchpad's two-finger scroll moves the view
            self.translate_view(pixel.x(), pixel.y())
            return
        steps = event.angleDelta().y() / 120.0 if not event.angleDelta().isNull() else pixel.y() / 60.0
        self.zoom_at(1.2 ** steps, event.position().toPoint())
        self._update_cursor(event.position().toPoint())

    def translate_view(self, dx: float, dy: float) -> None:
        s = self.transform().m11()
        self.translate(dx / s, dy / s)
        self.user_moved = True
        self._moved()

    def set_navigation(self, style: str) -> None:
        self.navigator.set_style(style)

    def _navigate(self, actions) -> None:
        """What the navigation style made of the mouse: the plan pans, zooms, recentres and fits; the orbit is
        the 3D view's and does nothing here."""
        for a in actions:
            if a.kind == "pan" and a.phase == "move":
                self.translate_view(a.dx, a.dy)
            elif a.kind == "pan" and a.phase == "begin":
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            elif a.kind in ("pan", "orbit", "zoom") and a.phase == "end":
                self.setCursor(Qt.CursorShape.ArrowCursor if self.tool == "select" else Qt.CursorShape.CrossCursor)
            elif a.kind == "zoom" and a.phase == "move":
                self.zoom_at(1.2 ** (-a.dy / 40.0), self.viewport().rect().center())
            elif a.kind == "recentre":
                self.centerOn(self.mapToScene(int(a.x), int(a.y)))
                self.user_moved = True
                self._moved()
            elif a.kind == "fit":
                self.fit()
            elif a.kind == "menu":
                self.menuRequested.emit(QPoint(int(a.x), int(a.y)))

    @staticmethod
    def _button(button) -> str:
        return {Qt.MouseButton.LeftButton: "left", Qt.MouseButton.MiddleButton: "middle",
                Qt.MouseButton.RightButton: "right"}.get(button, "")

    @staticmethod
    def _mods(modifiers) -> set:
        return {name for flag, name in ((Qt.KeyboardModifier.ControlModifier, "ctrl"),
                                        (Qt.KeyboardModifier.ShiftModifier, "shift"),
                                        (Qt.KeyboardModifier.AltModifier, "alt")) if modifiers & flag}

    def zoom_at(self, factor: float, view_pos) -> None:
        """Zoom by `factor` keeping the point under `view_pos` where it is."""
        current = math.hypot(self.transform().m11(), self.transform().m21())
        factor = max(0.02 / current, min(factor, 400.0 / current))
        before = self.mapToScene(view_pos)
        self.scale(factor, factor)
        after = self.mapToScene(view_pos)
        delta = after - before
        self.translate(delta.x(), delta.y())
        self.user_moved = True
        self._moved()

    def view_rotation(self) -> float:
        """The view's clockwise bearing, never a rotation of the project's coordinates."""
        return math.degrees(math.atan2(-self.transform().m21(), self.transform().m11())) % 360.0

    def rotate_view(self, degrees: float) -> None:
        centre = self.mapToScene(self.viewport().rect().center())
        self.rotate(degrees)
        self.centerOn(centre)
        self.north.set_rotation(self.view_rotation())
        self.user_moved = True
        self._moved()

    def reset_rotation(self) -> None:
        centre = self.mapToScene(self.viewport().rect().center())
        scale = math.hypot(self.transform().m11(), self.transform().m21())
        self.setTransform(QTransform().scale(scale, scale))
        self.centerOn(centre)
        self.north.set_rotation(0.0)
        self._moved()

    def align_to_side(self, ring, side: int) -> None:
        """Turn the view so side `side` of `ring` lies horizontally; the points in metres stay exactly as they are."""
        a, b = ring[side], ring[(side + 1) % len(ring)]
        bearing = math.degrees(math.atan2(b[0] - a[0], b[1] - a[1]))
        self.rotate_view(90.0 - bearing - self.view_rotation())

    def mousePressEvent(self, event):
        self.setFocus()
        if (self.strings_mode and self.edge_pick is None and self.point_pick is None and self.left_wait is None
                and not self.navigator.held and self._string_press(event)):
            return
        button = self._button(event.button())
        if self.left_wait is not None and button in ("middle", "right"):
            # the left button held back was the start of a gesture of both (AutoCAD's left + right pan)
            pos, mods = self.left_wait
            self.left_wait = None
            self.left_timer.stop()
            self.navigator.press("left", self._mods(mods), pos.x(), pos.y())
        if self.edge_pick is None and (button in ("middle", "right") or (button == "left" and self.navigator.held)):
            # the middle and the right buttons belong to the navigation style; the left one to the tools
            x, y = event.position().x(), event.position().y()
            self._navigate(self.navigator.press(button, self._mods(event.modifiers()), x, y))
            return
        if button == "left" and self.edge_pick is None and not self.space and self.navigator.chorded("left"):
            # held back a moment, where the left button makes a gesture with another one: pressed first, it
            # selected or drew a corner before the right one came for the pan (review, 23/10/2026). It acts
            # at its release, when the pointer moves or after LEFT_WAIT_MS, at the place it was pressed
            self.left_wait = (QPointF(event.position()), event.modifiers())
            self.left_timer.start()
            return
        self._left_press(event.position(), event.modifiers(), event.button())

    def _left_now(self) -> None:
        """The left button held back acts now, where it was pressed."""
        if self.left_wait is not None:
            pos, mods = self.left_wait
            self.left_wait = None
            self.left_timer.stop()
            self._left_press(pos, mods, Qt.MouseButton.LeftButton)

    def _left_press(self, position: QPointF, modifiers, qbutton) -> None:
        """A press for the tools: select, drag a corner, draw, measure, pick a side."""
        if qbutton == Qt.MouseButton.LeftButton and self.tool == "select":
            mark = next((it for it in self.items(position.toPoint()) if it.data(0) == "mark"), None)
            if mark is not None:
                kind, oid = mark.data(1)
                self.markClicked.emit(kind, oid)
                return
        if qbutton == Qt.MouseButton.LeftButton and self.space:
            self.panning = position
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if self.point_pick is not None:
            if qbutton == Qt.MouseButton.LeftButton:
                purpose, count, got, hints = self.point_pick
                got.append(from_scene(self.mapToScene(position.toPoint())))
                if len(got) < count:
                    self.hint.emit(hints[len(got)])
                    self.viewport().update()
                else:
                    self._end_point_pick()
                    self.pointsPicked.emit(purpose, got)
            else:
                self._end_point_pick()
                self.hint.emit("")
            return
        if self.edge_pick is not None:
            if qbutton == Qt.MouseButton.LeftButton and self.edge_hover is not None:
                purpose, kind, oid, _ring = self.edge_pick
                side = self.edge_hover
                self._end_pick()
                self.edgePicked.emit(purpose, kind, oid, side)
            elif qbutton == Qt.MouseButton.RightButton:
                self._end_pick()
            return
        if qbutton != Qt.MouseButton.LeftButton:
            return
        scene_pos = self.mapToScene(position.toPoint())
        if self.tool == "move":
            self._move_press(position, modifiers)
            return
        if self.tool == "select":
            vertex = self._vertex_near(position.toPoint())
            if vertex is not None:
                ring = self.rings[self.selection]
                self.dragging = (self.selection[0], self.selection[1], vertex, ring)
                self.drag_point = ring[vertex]
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                self.hint.emit(_("Drag the corner; it snaps to the other outlines, Ctrl drags it free."))
                return
            end = self._row_end()
            if end is not None:
                p = self.mapFromScene(to_scene(*end))
                if math.hypot(p.x() - position.x(), p.y() - position.y()) <= 8.0:
                    self.row_drag = end
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                    self.hint.emit(_("Drag the end of the row: it takes or gives back places, one module at a time."))
                    return
            kind, oid, key = self._pick(scene_pos, PICK_PX)
            rid = self.rid_of(oid, key) if kind == "module" else ""
            # a click on the row selected goes back to the module (below)
            if kind == "module" and rid and self.selection == ("subfield", oid) and \
                    self.selected_module[0] == oid and self.rid_of(*self.selected_module) == rid:
                # a second click on the same row: the row (the levels of selection of Draft and SketchUp, 16c)
                self.selected_module = ("", "")
                self.selection = ("row", f"{oid}/{rid}")
                self._restyle_selection()
                self.picked.emit("row", f"{oid}/{rid}")
                return
            if kind == "module":
                self.selected_module = (oid, key)
                self.selection = ("subfield", oid)
                self._restyle_selection()
                self.moduleClicked.emit(oid, key)
            else:
                self.selected_module = ("", "")
                self.selection = (kind, oid)
                self._restyle_selection()
                self.picked.emit(kind, oid)
            return
        # the guides of the place pressed, not of the last place the pointer rested on (a pen or a finger
        # presses without hovering first)
        self.ctrl = _ctrl(modifiers)
        self._update_cursor(position.toPoint())
        if self.tool == "measure":
            p = self.snap.point if self.snap else from_scene(scene_pos)
            self.measure = [p] if len(self.measure) != 1 else [self.measure[0], p]
            self.viewport().update()
            return
        if self.tool == "row":
            if self.typed and self._apply_typed_row():
                return
            p = self.snap.point if self.snap else from_scene(scene_pos)
            if self.row_start is None:
                self.row_start = p
                self.snapper.reset()
            elif math.dist(p, self.row_start) > 1e-6:
                self._end_row(p)
            self.viewport().update()
            return
        if self.tool in DRAWING:
            if self.typed and self._apply_typed():
                self.viewport().update()
                return
            p = self.snap.point if self.snap else from_scene(scene_pos)
            if self.rect_mode and len(self.chain) == 2:
                rect = self._rectangle(p)
                if math.dist(rect[1], rect[2]) > 0.05:
                    self.chain = rect
                    self._finish()
                return
            # the first point closes, with the snap or near enough without it (R41)
            near_first = len(self.chain) >= 3 and math.dist(p, self.chain[0]) <= 10 * self.metres_per_pixel()
            if (self.snap and self.snap.kind == "close") or near_first:
                self._finish()
                return
            if not self.chain or math.dist(p, self.chain[-1]) > 1e-6:
                self.chain.append(p)
            self._update_cursor(position.toPoint())

    def mouseDoubleClickEvent(self, event):
        self._left_now()
        if self.strings_mode and event.button() == Qt.MouseButton.LeftButton and not self.space:
            # the Plant phase: a double click closes the string being drawn, or draws again the string of the module
            if self.draft is not None:
                self.draft_drag = False
                self.finish_draft()
                return
            hit = self._module_at(event.position())
            if hit is not None:
                self.stringRedraw.emit(*hit)
                return
        if event.button() == Qt.MouseButton.MiddleButton:
            self._navigate(self.navigator.double("middle", self._mods(event.modifiers()), event.position().x(),
                                                 event.position().y()))
            return
        if self.tool in DRAWING and event.button() == Qt.MouseButton.LeftButton:
            if self.tool == "subfield" and len(self.chain) <= 2:
                # a double click without an outline: the pitch under it, whole (R64)
                x, y = from_scene(self.mapToScene(event.position().toPoint()))
                self.cancel_outline()
                self.wholePicked.emit(self.tool, x, y)
                return
            self._finish()
            return
        if self.tool == "select" and self.edge_pick is None and event.button() == Qt.MouseButton.LeftButton:
            kind, oid, key = self._pick(self.mapToScene(event.position().toPoint()), PICK_PX)
            if kind == "module":                    # the window selects a row of more, turns one on its own
                self.moduleDoubleClicked.emit(oid, key)
                return
        ring = self.rings.get(self.selection)
        if self.tool == "select" and self.edge_pick is None and ring and event.button() == Qt.MouseButton.LeftButton:
            side = self._side_near(ring, event.position().toPoint())
            if side is not None:
                self.sideClicked.emit(self.selection[0], self.selection[1], side)
                return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self.draft is not None:
            # a string being drawn: the line follows the pointer; with the left button held from a module, each module
            # the pointer passes the middle of is taken, as Sunny Design connects them
            self.draft_pointer = self.mapToScene(event.position().toPoint())
            if self.draft_drag:
                hit = self._module_at(event.position())
                if hit is not None and hit not in self.draft and self._past_centre(*hit, self.draft_pointer):
                    self._draft_take(hit, bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier))
            self._draw_band()
            if not self.navigator.held and self.panning is None:
                return
        if self.left_wait is not None and \
                (event.position() - self.left_wait[0]).manhattanLength() > navigation.CLICK_PX:
            self._left_now()                        # a drag of the left button: a corner dragged, a vertex drawn
        if self.navigator.held:
            self._navigate(self.navigator.move(event.position().x(), event.position().y(),
                                               self._mods(event.modifiers())))
            return
        if self.panning is not None:
            d = event.position() - self.panning
            self.panning = event.position()
            self.translate_view(d.x(), d.y())
            return
        if self.dragging is not None:
            self.ctrl = _ctrl(event.modifiers())
            cursor = from_scene(self.mapToScene(event.position().toPoint()))
            snap = self.snapper.snap(cursor, [], self.metres_per_pixel(), free=self.ctrl or not self.snaps_on)
            self.drag_point = snap.point if snap else cursor
            self.cursorInfo.emit(f"E {number(self.drag_point[0])}  N {number(self.drag_point[1])} m")
            self.viewport().update()
            return
        if self.row_drag is not None:
            self.row_drag = from_scene(self.mapToScene(event.position().toPoint()))
            self.cursorInfo.emit(f"E {number(self.row_drag[0])}  N {number(self.row_drag[1])} m")
            self.viewport().update()
            return
        if self.edge_pick is not None:
            hover = self._side_near(self.edge_pick[3], event.position().toPoint())
            if hover != self.edge_hover:
                self.edge_hover = hover
                self.viewport().update()
            return
        self.ctrl = _ctrl(event.modifiers())
        self.move_mods = self._mods(event.modifiers())
        self._update_cursor(event.position().toPoint())

    def mouseReleaseEvent(self, event):
        if self.draft is not None and self.draft_drag and event.button() == Qt.MouseButton.LeftButton:
            self.draft_drag = False
            return
        button = self._button(event.button())
        if button == "left":
            self._left_now()
        if button in self.navigator.held:
            self._navigate(self.navigator.release(button, self._mods(event.modifiers()), event.position().x(),
                                                  event.position().y()))
            return
        if self.grip_press is not None and event.button() == Qt.MouseButton.LeftButton:
            pressed, self.grip_press = self.grip_press, None
            if (event.position() - pressed).manhattanLength() > navigation.CLICK_PX:
                self.move_mods = self._mods(event.modifiers())
                self._move_cursor(self.mapToScene(event.position().toPoint()))
                self._apply_gesture(self.move_mods)        # a grip dragged: Ctrl held at the release copies
            return
        if self.row_drag is not None and event.button() == Qt.MouseButton.LeftButton:
            point, start = self.row_drag, self._row_end()
            self.row_drag = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.viewport().update()
            if start is not None and math.dist(point, start) > 1e-3 and self.selection[0] == "row":
                self.rowResized.emit(self.selection[1], float(point[0]), float(point[1]))
            return
        if self.dragging is not None and event.button() == Qt.MouseButton.LeftButton:
            kind, oid, vertex, ring = self.dragging
            point = self.drag_point
            self.dragging = None
            self.drag_point = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.viewport().update()
            if point is not None and math.dist(point, ring[vertex]) > 1e-3:
                self.vertexMoved.emit(kind, oid, vertex, float(point[0]), float(point[1]))
            return
        if self.panning is not None and event.button() == Qt.MouseButton.LeftButton:
            self.panning = None
            self.setCursor(Qt.CursorShape.ArrowCursor if self.tool == "select" else Qt.CursorShape.CrossCursor)

    def event(self, event):
        """In Move the keys of the gesture are the plan's, not the window's: R turns (it is the rectangle outside
        Move), the digits and the arrows, Tab goes from the distance to the direction, not to the next widget."""
        if event.type() == QEvent.Type.NativeGesture:
            kind = event.gestureType()
            if kind == Qt.NativeGestureType.ZoomNativeGesture:
                self.zoom_at(max(0.05, 1.0 + event.value()), event.position().toPoint())
            elif kind == Qt.NativeGestureType.RotateNativeGesture:
                self.rotate_view(event.value())
            elif kind in (Qt.NativeGestureType.BeginNativeGesture, Qt.NativeGestureType.EndNativeGesture):
                pass
            else:
                return super().event(event)
            event.accept()
            return True
        if getattr(self, "tool", "") == "move":         # events come before __init__ is through
            if event.type() == QEvent.Type.ShortcutOverride and self._move_owns(event):
                event.accept()
                return True
            if event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                self.keyPressEvent(event)
                return True
        return super().event(event)

    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()
        if self.tool == "move" and self._move_key(event):
            return
        if self.draft is not None and key in (Qt.Key.Key_Backspace, Qt.Key.Key_Return, Qt.Key.Key_Enter,
                                              Qt.Key.Key_Escape):
            # a string being drawn (R114): Backspace takes back the last module, Enter closes it, Esc gives it up
            {Qt.Key.Key_Backspace: self.draft_pop, Qt.Key.Key_Escape: self.cancel_draft}.get(key, self.finish_draft)()
            return
        if key == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        if key == Qt.Key.Key_Control:
            self.ctrl = _ctrl(event.modifiers() | Qt.KeyboardModifier.ControlModifier)
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return
        if key == Qt.Key.Key_Shift and self.tool in DRAWING and self.chain and self.snap and self.snap.length:
            last = self.chain[-1]
            d = math.dist(self.snap.point, last)
            self.lock_dir = ((self.snap.point[0] - last[0]) / d, (self.snap.point[1] - last[1]) / d)
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return
        if self.tool in DRAWING and key == Qt.Key.Key_R and not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier:
            self.toggle_rectangle()
            return
        if self.tool == "row":
            if text and (text.isdigit() or text in ",.") and self.row_start is not None:
                self.typed += text
                self.viewport().update()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._apply_typed_row()
                return
            if key == Qt.Key.Key_Backspace:
                self.typed = self.typed[:-1] if self.typed else ""
                self.viewport().update()
                return
            if key == Qt.Key.Key_Escape:
                if self.typed:
                    self.typed = ""
                else:
                    self.row_start = None
                    self.snapper.reset()
                self.viewport().update()
                return
        if self.tool in DRAWING or self.tool == "measure":
            if text and (text.isdigit() or text in ",.;-") and self.chain:
                self.typed += text
                self.viewport().update()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not self._apply_typed():
                    self._finish()
                self.viewport().update()
                return
            if key == Qt.Key.Key_Backspace:
                if self.typed:
                    self.typed = self.typed[:-1]
                elif self.chain:
                    self.chain.pop()
                self.viewport().update()
                return
            if key == Qt.Key.Key_Escape:
                if self.typed:
                    self.typed = ""
                else:
                    self.chain, self.measure = [], []
                    self.snapper.reset()
                self.viewport().update()
                return
        if self.strings_mode and self.draft is None and key == Qt.Key.Key_Escape and self.chosen_string >= 0:
            self.stringEscape.emit()
            return
        if key == Qt.Key.Key_Escape and self.edge_pick is not None:
            self._end_pick()
            self.hint.emit("")
            return
        if key == Qt.Key.Key_Escape and self.point_pick is not None:
            self._end_point_pick()
            self.hint.emit("")
            return
        if key == Qt.Key.Key_Escape and self.tool == "select" and self.selection_back():
            return
        if key == Qt.Key.Key_Delete and self.tool == "select":
            self.deleteRequested.emit()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.space = False
            self.setCursor(Qt.CursorShape.ArrowCursor if self.tool == "select" else Qt.CursorShape.CrossCursor)
            return
        if event.key() == Qt.Key.Key_Control:
            self.ctrl = False
            self.move_mods.discard("ctrl")
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return
        if event.key() == Qt.Key.Key_Shift:
            self.move_mods.discard("shift")
        if event.key() == Qt.Key.Key_Shift and self.lock_dir is not None:
            self.lock_dir = None
            self._update_cursor(self.mapFromGlobal(self.cursor().pos()))
            return
        super().keyReleaseEvent(event)

    def _update_cursor(self, view_pos) -> None:
        scene_pos = self.mapToScene(view_pos)
        cursor = from_scene(scene_pos)
        if self.tool == "move":
            self._move_cursor(scene_pos)
            return
        if self.tool == "select":
            # nothing on the plan follows the pointer while selecting but the outline of what is under it: only
            # that is drawn again. Repainting the whole plan at each move cost 15 ms on a roof and 60-70 ms with
            # 4,700 modules (22/10/2026)
            self.snap = None
            kind, oid, key = self._pick(scene_pos, PICK_PX) if self.edge_pick is None else ("", "", "")
            rid = self.rid_of(oid, key) if kind == "module" else ""
            if rid and self.selection == ("subfield", oid) and self.selected_module[0] == oid and \
                    self.rid_of(*self.selected_module) == rid:
                self._hover("row", f"{oid}/{rid}", "")          # the next click takes the row (16c)
            else:
                self._hover(kind, oid, key)
            if self.drawn is not None:
                from .properties import exclusion_names
                self.cursorInfo.emit(viewaids.under_text(self.drawn[0], kind, oid, key, cursor[0], cursor[1],
                                                         exclusion_names()))
            else:
                self.cursorInfo.emit(f"E {number(cursor[0])}  N {number(cursor[1])} m")
            return
        if self.tool in DRAWING:
            chain = self.chain
        elif self.tool == "row":
            chain = [self.row_start] if self.row_start is not None else []
        else:
            chain = self.measure[:1]
        if self.tool in DRAWING and self.lock_dir is not None and chain:
            last = chain[-1]
            t = (cursor[0] - last[0]) * self.lock_dir[0] + (cursor[1] - last[1]) * self.lock_dir[1]
            point = (last[0] + t * self.lock_dir[0], last[1] + t * self.lock_dir[1])
            self.snap = Snapper._measure(Snap(point, "direction", [Guide(last, point, "polar", "⇧")]), chain)
        elif self.tool in DRAWING or self.tool in ("measure", "row"):
            self.snap = self.snapper.snap(cursor, chain, self.metres_per_pixel(), free=self.ctrl or not self.snaps_on)
            if self.ortho and self.tool in DRAWING and chain and self.snap.kind not in EXACT:
                point = ortho(chain, cursor)
                self.snap = Snapper._measure(Snap(point, "direction", [Guide(chain[-1], point, "polar", "F8")]), chain)
            if self.tool in DRAWING and self.rect_mode and len(chain) == 2 and self._depth(self.snap.point) < 1e-6:
                # the third click of a rectangle gives its depth: a point snapped back onto the line of the
                # first side (an edge met by its extension) would give none, and a small rectangle never closed
                self.snap = self.snapper.snap(cursor, chain, self.metres_per_pixel(), free=True)
        else:
            self.snap = None
        x, y = self.snap.point if self.snap else cursor
        info = f"E {number(x)}  N {number(y)} m"
        if self.snap and self.snap.length:
            info += f"   ·   {number(self.snap.length)} m, {number(_heading(self.snap.bearing), 1)}° N"
        if self.snap and self.snap.area:
            info += f"   ·   {number(self.snap.area, 1)} m²"
        self.cursorInfo.emit(info)
        self.viewport().update()

    # drawing the overlay in screen pixels

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        accent = qcolour(self.colours["sel"])
        draw = qcolour(self.colours["draw"])        # the line being drawn: orange, as before phase 2
        W = view_colours.WIDTHS
        halo = cosmetic(self.colours["halo"], W["draw"] + W["halo"])
        guide = qcolour(self.colours["guide"])
        if self.tool in DRAWING and self.rect_mode and len(self.chain) == 2 and self.snap:
            rect = QPolygonF([to_scene(*q) for q in self._rectangle(self.snap.point)])
            painter.setPen(halo)
            painter.drawPolygon(rect)
            painter.setPen(cosmetic(draw, W["draw"], Qt.PenStyle.DashLine))
            painter.drawPolygon(rect)
        if self.tool in DRAWING and (self.chain or self.snap):
            pts = [to_scene(*p) for p in self.chain]
            if self.snap and self.chain:
                pts.append(to_scene(*self.snap.point))
            if len(pts) >= 2:
                painter.setPen(halo)                # a line of two tones: Daniel's case, a light roof (23/10/2026)
                painter.drawPolyline(QPolygonF(pts))
                painter.setPen(cosmetic(draw, W["draw"]))
                painter.drawPolyline(QPolygonF(pts))
                if len(self.chain) >= 2 and self.snap:
                    painter.setPen(cosmetic(draw, 1.2, Qt.PenStyle.DashLine))
                    painter.drawLine(QLineF(pts[-1], pts[0]))
            for p in pts[:-1] if self.snap and self.chain else pts:
                self._mark(painter, p, draw, "vertex")
        if self.snap and (self.tool in DRAWING or self.tool in ("measure", "move")):
            painter.setPen(cosmetic(guide, 1, Qt.PenStyle.DashLine))
            for g in self.snap.guides:
                a, b = to_scene(*g.a), to_scene(*g.b)
                d = b - a
                n = math.hypot(d.x(), d.y())
                if n > 1e-9:
                    ext = 4000 * self.metres_per_pixel() / n
                    painter.drawLine(QLineF(a - d * ext, b + d * ext) if g.kind == "tracking" else QLineF(a, b + d * ext))
            self._mark(painter, to_scene(*self.snap.point), guide, self.snap.kind)
        if self.tool == "measure" and self.measure:
            a = to_scene(*self.measure[0])
            b = to_scene(*(self.measure[1] if len(self.measure) == 2 else (self.snap.point if self.snap else self.measure[0])))
            painter.setPen(halo)
            painter.drawLine(QLineF(a, b))
            painter.setPen(cosmetic(draw, W["measure"]))
            painter.drawLine(QLineF(a, b))
        if self.tool == "row" and self.row_start is not None:
            self._draw_row(painter, draw, halo)
        end = self._row_end() if self.tool == "select" else None
        if end is not None:                         # the grip at the end of the selected row
            r = 5 * self.metres_per_pixel()
            p = to_scene(*end)
            shape = QRectF(p.x() - r, p.y() - r, 2 * r, 2 * r)
            painter.setPen(cosmetic(self.colours["halo"], 1.6 + W["halo"]))
            painter.drawRect(shape)
            painter.setPen(cosmetic(accent, 1.6))
            painter.setBrush(QBrush(accent) if self.row_drag is not None else QBrush(qcolour(self.colours["label_bg"])))
            painter.drawRect(shape)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.row_drag is not None:
                painter.setPen(cosmetic(draw, W["draw"], Qt.PenStyle.DashLine))
                painter.drawLine(QLineF(p, to_scene(*self.row_drag)))
        ring = self.rings.get(self.selection)
        if self.tool == "select" and ring and self.selection[0] in ("building", "subfield", "exclusion"):
            if self.dragging is not None and self.drag_point is not None:
                moved = list(ring)
                moved[self.dragging[2]] = self.drag_point
                painter.setPen(cosmetic(accent, 2, Qt.PenStyle.DashLine))
                painter.drawPolygon(QPolygonF([to_scene(*q) for q in moved]))
                ring = moved
            for q in ring:                    # the corners, to drag
                self._mark(painter, to_scene(*q), accent, "vertex")
        if self.tool == "move":
            self._draw_move(painter)
        if self.point_pick is not None:              # the points clicked so far
            for q in self.point_pick[2]:
                self._mark(painter, to_scene(*q), qcolour(self.colours["draw"]), "intersection")
        if self.edge_pick is not None:
            ring = self.edge_pick[3]
            pts = [to_scene(*q) for q in ring]
            for i, (a, b) in enumerate(zip(pts, pts[1:] + pts[:1], strict=True)):
                painter.setPen(cosmetic(accent, 5) if i == self.edge_hover else cosmetic(accent, 1.5, Qt.PenStyle.DashLine))
                painter.drawLine(QLineF(a, b))
        painter.restore()
        self._draw_sides(painter)
        self._draw_labels(painter)

    def _draw_row(self, painter: QPainter, draw: QColor, halo: QPen) -> None:
        """The row being drawn: the line from its start, and its modules where they would go, red when they go
        beyond the edge band or onto an exclusion (PV*SOL: «rows of modules in an invalid area are shown in red»)."""
        end = self._row_pointer()
        a = to_scene(*self.row_start)
        self._mark(painter, a, draw, "vertex")
        if end is None:
            return
        quads, bad = (self.row_preview(self.row_start, end) if self.row_preview is not None else ([], False))
        colour = qcolour(self.colours["exclusion"]) if bad else draw
        fill = QColor(colour)
        fill.setAlpha(70)
        for q in quads:
            poly = QPolygonF([to_scene(*c) for c in q])
            painter.setPen(cosmetic(colour, 1.2))
            painter.setBrush(QBrush(fill))
            painter.drawPolygon(poly)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(halo)
        painter.drawLine(QLineF(a, to_scene(*end)))
        painter.setPen(cosmetic(colour, view_colours.WIDTHS["draw"], Qt.PenStyle.DashLine))
        painter.drawLine(QLineF(a, to_scene(*end)))
        self.row_count = len(quads)

    def _draw_sides(self, painter: QPainter) -> None:
        """The length of each side of the selected outline, at its middle, outside it: a double click on a
        side changes it."""
        ring = self.edge_pick[3] if self.edge_pick is not None else self.rings.get(self.selection)
        if self.tool != "select" or not ring or len(ring) < 3:
            return
        painter.save()
        painter.resetTransform()
        font = design.font(design.Type.SMALL, design.Type.REGULAR, self.font())
        painter.setFont(font)
        fm = QFontMetrics(font)
        area = 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1], strict=True))
        for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1], strict=True)):
            pa, pb = self.mapFromScene(to_scene(*a)), self.mapFromScene(to_scene(*b))
            dx, dy = pb.x() - pa.x(), pb.y() - pa.y()
            n = math.hypot(dx, dy)
            if n < 40:                       # too short on screen for its measure
                continue
            # outwards: anticlockwise in metres the inside is on the left; the screen's y points down
            ox, oy = (dy / n, -dx / n) if area > 0 else (-dy / n, dx / n)
            text = _("{length} m").format(length=number(math.dist(a, b)))
            w, h = fm.horizontalAdvance(text) + 8, fm.height() + 2
            cx, cy = (pa.x() + pb.x()) / 2 + ox * h * 0.9, (pa.y() + pb.y()) / 2 + oy * h * 0.9
            box = QRectF(cx - w / 2, cy - h / 2, w, h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qcolour(self.colours["label_bg"]))
            painter.drawRoundedRect(box, design.Radius.INNER, design.Radius.INNER)
            painter.setPen(qcolour(self.colours["sel"] if i == self.edge_hover else self.colours["label_fg"]))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()

    def _mark(self, painter, p: QPointF, colour, kind: str) -> None:
        r = 5 * self.metres_per_pixel()
        painter.setPen(cosmetic(colour, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if kind in ("vertex", "close"):
            painter.drawRect(QRectF(p.x() - r, p.y() - r, 2 * r, 2 * r))
        elif kind == "midpoint":
            poly = QPolygonF([QPointF(p.x(), p.y() - r), QPointF(p.x() + r, p.y() + r), QPointF(p.x() - r, p.y() + r)])
            painter.drawPolygon(poly)
        elif kind == "intersection":
            painter.drawLine(QLineF(p.x() - r, p.y() - r, p.x() + r, p.y() + r))
            painter.drawLine(QLineF(p.x() - r, p.y() + r, p.x() + r, p.y() - r))
        elif kind in ("edge", "direction"):
            painter.drawEllipse(p, r, r)

    def _draw_labels(self, painter: QPainter) -> None:
        """The measures next to the cursor, in screen pixels: length, direction, turn, typed length."""
        lines = []
        anchor = None
        if self.snap and (self.tool in DRAWING or self.tool == "measure"):
            anchor = self.mapFromScene(to_scene(*self.snap.point))
            if self.snap.length:
                lines.append(_("{length} m").format(length=number(self.snap.length)))
                lines.append(_("direction {bearing}° from North").format(bearing=number(_heading(self.snap.bearing), 1)))
            if self.snap.turn is not None:
                lines.append(_("turn {turn}°").format(turn=number(abs(self.snap.turn), 1)))
            if self.snap.guides and self.snap.guides[0].label:
                lines.append(self.snap.guides[0].label)
        if self.typed:
            lines.insert(0, _("length: {value}_").format(value=self.typed))
        if self.tool == "measure" and len(self.measure) == 2:
            anchor = self.mapFromScene(to_scene(*self.measure[1]))
            lines = [_("{length} m").format(length=number(math.dist(*self.measure)))]
        if self.tool == "move" and self.gesture is not None and self.move_pointer is not None:
            anchor = self.mapFromScene(to_scene(*self.move_pointer))
            lines = self._move_labels()
        end = self._row_pointer() if self.tool == "row" else None
        if end is not None:
            anchor = self.mapFromScene(to_scene(*end))
            lines = ([_("length: {value}_").format(value=self.typed)] if self.typed else []) + [
                _("{length} m").format(length=number(math.dist(self.row_start, end))),
                ngettext("{n} module", "{n} modules", self.row_count).format(n=self.row_count)]
        if not lines or anchor is None:
            return
        painter.save()
        painter.resetTransform()
        font = QFont(self.font())
        fm = QFontMetrics(font)
        w = max(fm.horizontalAdvance(t) for t in lines) + 16      # 8 px each side and 5 above and below, as
        h = fm.height() * len(lines) + 10                           # the tooltips (R60, 24/10/2026)
        box = QRectF(anchor.x() + 16, anchor.y() + 16, w, h)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(qcolour(self.colours["label_bg"]))
        painter.drawRoundedRect(box, design.Radius.INNER, design.Radius.INNER)
        painter.setPen(qcolour(self.colours["label_fg"]))
        symbols = symbol_font(font)
        for i, t in enumerate(lines):
            painter.setFont(symbols if t in ("∥", "⊥", "⇧") else font)
            painter.drawText(QPointF(box.x() + 8, box.y() + 5 + fm.ascent() + i * fm.height()), t)
        painter.restore()

    # background tiles

    def _clear_tiles(self) -> None:
        for it in self.tile_items.values():
            self.scene().removeItem(it)
        self.tile_items = {}

    def _update_tiles(self) -> None:
        source = self.background()
        if source is None:
            return
        r = self.mapToScene(self.viewport().rect()).boundingRect()
        corners = [self.origin.to_lonlat(*from_scene(p)) for p in (r.topLeft(), r.bottomRight())]
        (lon_w, lat_n), (lon_e, lat_s) = corners
        dpr = self.devicePixelRatioF()
        z = max(source.min_zoom, tiles.zoom_for(self.metres_per_pixel() / dpr, self.origin.lat, source.max_zoom))
        self.target_zoom = z
        wanted = {(self.source, z, x, y) for x, y in tiles.tiles_for(lon_w, lat_s, lon_e, lat_n, z)}
        self.loader.keep_only(wanted)
        for t in wanted:
            if t not in self.tile_items:
                self.loader.request(*t)
        # tiles of other zooms stay until the screen is covered again, then go
        stale = [t for t in self.tile_items if t[1] != z and abs(t[1] - z) > 1]
        for t in stale:
            self.scene().removeItem(self.tile_items.pop(t))

    def _tile_ready(self, key, z, x, y, image) -> None:
        if key != self.source or (key, z, x, y) in self.tile_items:
            return
        from PySide6.QtGui import QPixmap
        item = QGraphicsPixmapItem(QPixmap.fromImage(image))
        quad = [to_scene(*p) for p in tiles.tile_quad(self.origin, z, x, y)]
        w, h = image.width(), image.height()
        src = QPolygonF([QPointF(0, 0), QPointF(w, 0), QPointF(w, h), QPointF(0, h)])
        transform = QTransform()
        if QTransform.quadToQuad(src, QPolygonF(quad), transform):
            item.setTransform(transform)
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        item.setZValue(Z_TILES + (0.5 if z == self.target_zoom else 0.0))
        self.scene().addItem(item)
        self.tile_items[(key, z, x, y)] = item

    def fit(self, rect: QRectF | None = None) -> None:
        """Frame the drawing. Before the view has its real size (a window not shown yet) the frame is
        kept and applied at the first real resize: framing a 40 m roof in a 100-pixel placeholder would
        leave the view zoomed out on a whole town."""
        if rect is None:
            items = [it for kind, its in self.items_by_kind.items() if kind not in ("selection", "arrows") for it in its]
            rect = QRectF()
            for it in items:
                rect = rect.united(it.sceneBoundingRect())
            if rect.isEmpty():
                rect = QRectF(-60, -60, 120, 120)
        if not self.isVisible() or self.viewport().width() < 120 or self.viewport().height() < 120:
            self.pending_fit = rect
            return
        self.pending_fit = None
        self.user_moved = False
        margin = max(rect.width(), rect.height()) * 0.15 + 5
        rotation = self.view_rotation()
        self.fitInView(rect.adjusted(-margin, -margin, margin, margin), Qt.AspectRatioMode.KeepAspectRatio)
        self.rotate_view(rotation)
        self.user_moved = False                 # fitting again is not a move by hand, rotation included
        self._moved()

    def resizeEvent(self, event):
        """Framed until the designer moves the view: a tiling compositor resizes a window a few times
        after showing it (niri gives it its column), and the drawing stays in frame through that."""
        super().resizeEvent(event)
        if self.source != tiles.NONE:
            self._credit()
        if self.pending_fit is not None:
            self.fit(self.pending_fit)
        elif not self.user_moved:
            self.fit()
        plan_overlays.place(self)
        self._place_laying()
        self._moved()

    def showEvent(self, event):
        super().showEvent(event)
        if self.pending_fit is not None:
            # with the view as the context: not called if the view is gone by then
            QTimer.singleShot(0, self, lambda: self.fit(self.pending_fit) if self.pending_fit is not None else None)
