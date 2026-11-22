"""QPainter dialog previews: the projection, the order of the faces and the place of the measures are preview3d's.

This item is the paint device and the input's transport. The measures are not painted here: the item says where
they go (`pills`) and the QML draws them with the plan's sides' pill, M.LengthPill, and opens the plan's field,
M.OverlayField, in the one clicked (R555 12).
"""
import itertools
import math
import threading
from functools import partial
from PySide6.QtCore import QObject, Property, QRectF, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtQuick import QQuickImageProvider, QQuickItem
from PySide6.QtQml import qmlEngine, qmlRegisterType
from meridiana.core.model import canopies
from meridiana.app.interface import theme_colors, view_colours
from meridiana.i18n import _, number
from meridiana.gui.style import design
from meridiana.gui.backend.preview3d import HINT_FLAGS, Preview3D, _mix, canopy_scene, sides_of, template_scene


class PreviewFrames(QQuickImageProvider):
    """The last frame of each preview, by key; the QML asks image://dialogpreview/<key>/<n> (n changes with every
    frame, so that the Image asks again). Written on the window's thread, read where Qt asks, under a lock."""
    NAME = 'dialogpreview'

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._images: dict[str, QImage] = {}
        self._lock = threading.Lock()
        self._keys = itertools.count(1)

    def key(self) -> str:
        return str(next(self._keys))

    def put(self, key: str, image: QImage) -> None:
        with self._lock:
            self._images[key] = image

    def drop(self, key: str, *_args) -> None:
        with self._lock:
            self._images.pop(key, None)

    def requestImage(self, identifier, size, requestedSize):
        with self._lock:
            image = self._images.get(identifier.split('/')[0])
        if image is None:
            image = QImage(1, 1, QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)
        size.setWidth(image.width())
        size.setHeight(image.height())
        return image


class DialogPreview(QQuickItem):
    changed = Signal()
    sourceChanged = Signal()
    pillsChanged = Signal()
    editingChanged = Signal()
    editRequested = Signal(str, str, float, float)

    # Geometry and pill placement: preview3d's, as they were drawn in the Widgets' dialogs.
    _axes = Preview3D._axes
    _all_points = Preview3D._all_points
    _fit = Preview3D._fit
    hint_rect = Preview3D.hint_rect
    _room = Preview3D._room
    project = Preview3D.project
    _projector = Preview3D._projector
    _colours = Preview3D._colours
    drawn = Preview3D.drawn
    _polyline = staticmethod(Preview3D._polyline)
    _anchor = staticmethod(Preview3D._anchor)
    pill_size = staticmethod(Preview3D.pill_size)
    _layout_pills = Preview3D._layout_pills
    _place_pills = Preview3D._place_pills
    _draw_north = Preview3D._draw_north
    key_at = Preview3D.key_at
    pill = Preview3D.pill

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend = None
        self._colors = {}
        self._font = QFont('IBM Plex Sans')
        self._font.setPixelSize(13)
        self.faces, self.guides, self._pills, self._rects = [], [], [], {}
        self.azimuth, self.elevation = 225., 30.
        self.hint = ''
        self.highlight = set()
        self.hover = self.editing = None
        self._press = None
        self._kind = ''
        self._source = ''
        self._scale = 1.
        self._key, self._shown = None, 0
        self._placed: list[dict] = []
        self._timer = QTimer(self, singleShot=True)
        self._timer.timeout.connect(self._render_image)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        self.widthChanged.connect(self.schedule)
        self.heightChanged.connect(self.schedule)

    source = Property(str, lambda self: self._source, notify=sourceChanged)
    pills = Property('QVariantList', lambda self: self._placed, notify=pillsChanged)

    @Property('QVariantMap', constant=True)
    def pillColors(self):
        """The plan's colours of what it writes over itself (label_bg, label_fg, sel), as the plan and the 3D view
        give them to their pills and fields: the preview's measures are the same pills (R555 12)."""
        if not hasattr(self, '_pill_colors'):
            self._pill_colors = {k: theme_colors.qt_hex(v) for k, v in view_colours.PHOTO.items()}
        return self._pill_colors

    @Property(str, notify=editingChanged)
    def editingKey(self):
        """The key of the measure whose field is open ("" when none): lit as the side being written on the plan."""
        return "" if self.editing is None else str(self.editing)

    @editingKey.setter
    def editingKey(self, value):
        key = next((p.key for p in self._pills if str(p.key) == value), None) if value else None
        if key != self.editing:
            self.editing = key
            self.editingChanged.emit()
            self.schedule()

    @Property(float, notify=changed)
    def deviceScale(self):
        return self._scale

    @deviceScale.setter
    def deviceScale(self, value):
        self._scale = max(1., value)
        self.schedule()

    def schedule(self, *_args):
        # one frame for all that changed in the same turn of the event loop (a timer restarted at every mouse move
        # was pushed on and on)
        if not self._timer.isActive():
            self._timer.start(0)

    def _frames(self):
        """This engine's store of the previews' frames, made the first time a preview draws."""
        engine = qmlEngine(self)
        if engine is None:
            return None
        frames = getattr(engine, '_meridiana_preview_frames', None)
        if frames is None:
            frames = PreviewFrames()
            engine.addImageProvider(PreviewFrames.NAME, frames)
            engine._meridiana_preview_frames = frames
        return frames

    @Slot()
    def _render_image(self):
        # A Python QQuickPaintedItem.paint would run on the render thread and
        # deadlock with the GUI thread holding the GIL. Qt only uploads this image.
        # R555 (Daniel 13/11/2026: «manipolare la vista la ridisegna di continuo durante il movimento»): the frame goes
        # to the Image as it is, through the engine's image provider. It went through a PNG, written, put in base64 and
        # read back at every step of a drag (28 ms a step for the canopy, three quarters of it the PNG); the scene's
        # faces are made once per change of the form, a turn of the view only projects and paints them again.
        if self._kind not in ('template', 'canopy') or self.width() < 1 or self.height() < 1:
            return
        frames = self._frames()
        if frames is None:
            return
        dpr = self._scale
        frame = QImage(round(self.width()*dpr), round(self.height()*dpr), QImage.Format.Format_ARGB32_Premultiplied)
        frame.setDevicePixelRatio(dpr)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        self.paint(painter)
        painter.end()
        if self._key is None:
            self._key = frames.key()
            self.destroyed.connect(partial(frames.drop, self._key))
        frames.put(self._key, frame)
        self._shown += 1
        self._source = f'image://{PreviewFrames.NAME}/{self._key}/{self._shown}'
        self.sourceChanged.emit()

    def font(self):
        return self._font

    def palette(self):
        palette = QPalette()
        for key, role in [('card', QPalette.Base), ('text', QPalette.Text), ('accent', QPalette.Accent),
                          ('line', QPalette.Mid), ('muted', QPalette.PlaceholderText)]:
            palette.setColor(role, QColor(self._colors.get(key, '#ffffff' if key == 'card' else '#333333')))
        return palette

    @Property('QVariantMap', notify=changed)
    def colors(self):
        return self._colors

    @colors.setter
    def colors(self, value):
        self._colors = value
        self.schedule()

    @Property(QFont, notify=changed)
    def textFont(self):
        return self._font

    @textFont.setter
    def textFont(self, value):
        self._font = value
        self.schedule()

    @Property(QObject, notify=changed)
    def backend(self):
        return self._backend

    @backend.setter
    def backend(self, value):
        if self._backend is not None:
            self._backend.changed.disconnect(self.refresh)
            self._backend.fieldHighlighted.disconnect(self.highlight_field)
        self._backend = value
        if value is not None:
            value.changed.connect(self.refresh)
            value.fieldHighlighted.connect(self.highlight_field)
        self.refresh()

    @Slot(str)
    def highlight_field(self, key):
        if self._kind == 'template':
            self.highlight = sides_of(self._backend.state['shape'], key) if key else set()
        elif self._kind == 'canopy':
            self.highlight = {'bay_width': {1, 3}, 'stalls': {1, 3}, 'depth': {2, 4},
                              'clearance': {'clearance'}, 'tilt': {'tilt'}}.get(key, set())
        self.schedule()

    def show_scene(self, faces=(), guides=(), pills=()):
        self.faces, self.guides, self._pills = list(faces), list(guides), list(pills)
        self._rects = {}
        if not self._pills and self._placed:
            self._placed = []
            self.pillsChanged.emit()
        self.schedule()

    @Slot()
    def refresh(self):
        if self._backend is None:
            return
        state = self._backend.state
        if self._kind != self._backend.kind:
            self._kind = self._backend.kind
            self.azimuth, self.elevation = 225., 18. if self._kind == "canopy" else 30.
        if self._backend.kind == 'template':
            self.hint = _('Drag to turn · click a side to write its length · N is North once on the plan')
            template_scene(self, state['turn'], state['ring'] or None)
        elif self._backend.kind == 'canopy':
            self.hint = _('Drag to turn · click a side to write its length · N is North once on the plan')
            try:
                spec = self._backend.canopy_spec()
            except ValueError:
                return  # The form reports the invalid values; keep the last valid preview.
            building = canopies.building(spec, (0, 0))
            canopy_scene(self, building.footprint, spec, building)
        else:
            self.show_scene()

    def mousePressEvent(self, event):
        self._press = event.position()
        self._view_at_press = self.azimuth, self.elevation
        self._dragging = False
        event.accept()

    def mouseMoveEvent(self, event):
        if self._press is not None:
            moved = event.position() - self._press
            if self._dragging or math.hypot(moved.x(), moved.y()) > 4:
                self._dragging = True
                self.azimuth = (self._view_at_press[0] + moved.x() * .5) % 360
                self.elevation = min(80., max(10., self._view_at_press[1] + moved.y() * .4))
                self.schedule()
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._press is not None and not self._dragging:
            key = self.key_at(event.position())
            pill = self.pill(key)
            if pill is not None:
                rect = self._rects[key]
                self.editRequested.emit(str(key), number(pill.value, 1 if pill.unit == '°' else 2), rect.x(), rect.y())
        self._press = None
        event.accept()

    def hoverMoveEvent(self, event):
        # drawn again only when the measure under the pointer changes (every move drew it again, the same)
        hover = self.key_at(event.position())
        self.setCursor(Qt.CursorShape.PointingHandCursor if hover is not None else Qt.CursorShape.OpenHandCursor)
        if hover != self.hover:
            self.hover = hover
            self.schedule()

    def hoverLeaveEvent(self, event):
        if self.hover is not None:
            self.hover = None
            self.schedule()

    def paint(self, painter):
        c = self._colours()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = QRectF(self.boundingRect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(c["line"], design.Line.HAIR))
        painter.setBrush(c["base"])
        painter.drawRoundedRect(frame, design.Radius.VIEW, design.Radius.VIEW)
        at, depth, d, mid = self._projector()
        lit = self.highlight | {k for k in (self.hover, self.editing) if k is not None}
        for guide in self.guides:
            if guide.kind in ("ground", "dashed"):
                self._polyline(painter, [at(p) for p in guide.points], QPen(c["muted"], 1, Qt.PenStyle.DashLine))
        for _layer, _depth, face, n, facing in self.drawn():
            if face.kind in ("wall", "structure"):
                length = math.hypot(n[0], n[1]) or 1.0
                light = (n[0] * -0.6 + n[1] * -0.8) / length      # the faces turned South-West are the lighter
                fill = c["structure"] if face.kind == "structure" else _mix(c["wall"], c["wall2"], 0.5 - light / 2)
            else:
                fill = c["roof"] if (facing if n[2] >= 0 else -facing) >= 0 else c["under"]     # its top or under
            painter.setPen(QPen(c["edge"], design.Line.HAIR))
            painter.setBrush(fill)
            painter.drawPolygon(QPolygonF([at(p) for p in face.points]))
        for guide in self.guides:
            if guide.kind == "ridge":
                self._polyline(painter, [at(p) for p in guide.points], QPen(c["edge"], design.Line.FOCUS))
        # R617: the field lit is the plan's lit side (Controls/LitSide.qml): its selection's colour, design.Highlight.SIDE
        lit_pen = QPen(QColor(self.pillColors['sel']), design.Highlight.SIDE)
        lit_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        for pill in self._pills:
            if pill.key in lit:
                self._polyline(painter, [at(p) for p in pill.points], lit_pen)
        placed = self._place_pills(at, mid, lit)
        if placed != self._placed:
            self._placed = placed
            self.pillsChanged.emit()
        self._draw_north(painter, c)
        if self.hint:
            painter.setFont(design.text_font(design.Text.CAPTION, self.font()))
            painter.setPen(c["muted"])
            painter.drawText(self.hint_rect(), HINT_FLAGS, self.hint)


_registered = False


def register():
    global _registered
    if not _registered:
        qmlRegisterType(DialogPreview, 'Meridiana.DialogPreview', 1, 0, 'DialogPreview')
        _registered = True
