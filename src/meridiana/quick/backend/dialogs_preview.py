"""QPainter dialog previews with the Widgets projection, face order and dimension pills.

Only the paint device and input transport differ. No QWidget is instantiated.
"""
import math
from types import SimpleNamespace
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QObject, Property, QRectF, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPalette, QPen, QPolygonF
from PySide6.QtQuick import QQuickItem
from PySide6.QtQml import qmlRegisterType
from meridiana import canopies
from meridiana.i18n import _, number
from meridiana.ui import design
from meridiana.ui.preview3d import Preview3D, HINT_FLAGS, _mix
# r24-fasi (studio 41, S8): the Widgets' dialogs (template_dialog, canopy_dialog: 0.17 s of imports) are read when a
# preview first draws one, not when DialogsBackend registers this type at every opening


class DialogPreview(QQuickItem):
    changed = Signal()
    sourceChanged = Signal()
    editRequested = Signal(str, str, float, float)

    # Geometry and pill placement are exactly the existing Widgets algorithms.
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
    _layout_pills = Preview3D._layout_pills
    _draw_pills = Preview3D._draw_pills
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
        self._timer = QTimer(self, singleShot=True)
        self._timer.timeout.connect(self._render_image)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        self.widthChanged.connect(self.schedule)
        self.heightChanged.connect(self.schedule)

    source = Property(str, lambda self: self._source, notify=sourceChanged)

    @Property(float, notify=changed)
    def deviceScale(self):
        return self._scale

    @deviceScale.setter
    def deviceScale(self, value):
        self._scale = max(1., value)
        self.schedule()

    def schedule(self, *_args):
        self._timer.start(0)

    @Slot()
    def _render_image(self):
        # A Python QQuickPaintedItem.paint would run on the render thread and
        # deadlock with the GUI thread holding the GIL. Qt only uploads this image.
        if self._kind not in ('template', 'canopy') or self.width() < 1 or self.height() < 1:
            return
        dpr = self._scale
        frame = QImage(round(self.width()*dpr), round(self.height()*dpr), QImage.Format.Format_ARGB32_Premultiplied)
        frame.setDevicePixelRatio(dpr)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        self.paint(painter)
        painter.end()
        data = QByteArray()
        stream = QBuffer(data)
        stream.open(QIODevice.OpenModeFlag.WriteOnly)
        frame.save(stream, 'PNG')
        stream.close()
        self._source = 'data:image/png;base64,' + bytes(data.toBase64()).decode('ascii')
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
            from meridiana.ui.template_dialog import sides_of
            self.highlight = sides_of(self._backend.state['shape'], key) if key else set()
        elif self._kind == 'canopy':
            self.highlight = {'bay_width': {1, 3}, 'stalls': {1, 3}, 'depth': {2, 4},
                              'clearance': {'clearance'}, 'tilt': {'tilt'}}.get(key, set())
        self.schedule()

    def show_scene(self, faces=(), guides=(), pills=()):
        self.faces, self.guides, self._pills = list(faces), list(guides), list(pills)
        self._rects = {}
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
            from meridiana.ui.template_dialog import TemplateDialog
            TemplateDialog._draw(SimpleNamespace(preview=self, turn=lambda: state['turn']), state['ring'] or None)
        elif self._backend.kind == 'canopy':
            self.hint = _('Drag to turn · click a side to write its length · N is North once on the plan')
            try:
                spec = self._backend.canopy_spec()
            except ValueError:
                return  # The form reports the invalid values; keep the last valid preview.
            building = canopies.building(spec, (0, 0))
            from meridiana.ui.canopy_dialog import CanopyDialog
            CanopyDialog._draw(SimpleNamespace(preview=self, ring=building.footprint), spec, building)
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
                self.editRequested.emit(str(key), number(pill.value, 1 if pill.unit == '°' else 2), rect.center().x(), rect.center().y())
        self._press = None
        event.accept()

    def hoverMoveEvent(self, event):
        self.hover = self.key_at(event.position())
        self.setCursor(Qt.CursorShape.PointingHandCursor if self.hover is not None else Qt.CursorShape.OpenHandCursor)
        self.schedule()

    def hoverLeaveEvent(self, event):
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
        for pill in self._pills:
            if pill.key in lit:
                self._polyline(painter, [at(p) for p in pill.points], QPen(c["accent"], design.Line.FOCUS))
        self._draw_pills(painter, at, mid, c, lit)
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
