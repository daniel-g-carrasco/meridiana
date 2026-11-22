"""Prepare native Qt Shape paths once per layout, never on the render thread."""
from PySide6.QtCore import QPointF, QRectF, Qt, Property, Signal
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPainterPathStroker, QPolygonF
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick import QQuickItem, QQuickPaintedItem
from meridiana.app.interface.view_colours import PHOTO, WIDTHS
from meridiana.app.view.plan_wiring import joined


def drawing_bounds(scene):
    """Match PlanView.fit's stroked scene bounds, calculated only on scene changes."""
    if not scene['objects'] and not scene['modules']:
        return [-60., -60., 120., 120.]
    bounds = QRectF(*scene['bounds'])
    stroker = QPainterPathStroker()
    stroker.setJoinStyle(Qt.BevelJoin)
    for obj in scene['objects']:
        if obj['kind'] not in ('building', 'pitch', 'subfield', 'exclusion', 'prop'):
            continue
        path = QPainterPath()
        path.addPolygon(QPolygonF([QPointF(*p) for p in obj['points']]))
        path.closeSubpath()
        stroker.setWidth(obj['width']+WIDTHS['halo'])
        bounds = bounds.united(stroker.createStroke(path).boundingRect())
    return list(bounds.getRect())


def row_outlines(modules):
    """One rectangle for each row of modules, around its modules (R707: what the plan fills instead of every module
    when a module is a few pixels): the row's direction from its first module to its last."""
    import numpy as np
    rows = {}
    for module in modules:
        rows.setdefault((module['oid'], module.get('rid')), []).append(module['points'])
    out = []
    for quads in rows.values():
        points = np.asarray(quads, dtype=float).reshape(-1, 2)
        along = points[-4:].mean(axis=0) - points[:4].mean(axis=0)
        if float(np.hypot(*along)) < 1e-9:              # one module: along its first side
            along = points[1] - points[0]
        length = float(np.hypot(*along))
        u = along / length if length > 1e-12 else np.array([1., 0.])
        v = np.array([-u[1], u[0]])
        s, t = points @ u, points @ v
        out.append(dict(points=[[float(a * u[0] + b * v[0]), float(a * u[1] + b * v[1])]
                                for a, b in ((s.min(), t.min()), (s.max(), t.min()), (s.max(), t.max()), (s.min(), t.max()))]))
    return out


def batches(modules, fill='#192d5a', stroke='#c6cbd6'):
    """The rows of a layer joined in native paths (plan_wiring.joined, the one way to do it)."""
    return joined(modules, fill, stroke)


class ModulePaths(QQuickItem):
    """A data object only. Qt owns all drawing nodes and their lifetimes."""
    modulesChanged = Signal()
    pathsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modules = []
        self._paths = []
        self.uploads = 0

    @Property('QVariantList', notify=modulesChanged)
    def modules(self):
        return self._modules

    @modules.setter
    def modules(self, value):
        if value == self._modules:
            return
        self._modules = value
        self._paths = batches(value)
        self.uploads += 1
        self.modulesChanged.emit()
        self.pathsChanged.emit()

    @Property('QVariantList', notify=pathsChanged)
    def paths(self):
        return self._paths

    @Property('QVariantList', notify=pathsChanged)
    def preset(self):
        return self._paths

    @preset.setter
    def preset(self, value):
        """Paths already joined by the controller: nothing to prepare here; the same paths again draw nothing anew (a
        layer told with the others that did change, R598)."""
        if value == self._paths:
            return
        self._paths = value
        self.uploads += 1
        self.pathsChanged.emit()


class SoftwareHatch(QQuickPaintedItem):
    """Qt's software Shape renderer has no fillItem. Paint the same screen-space brush."""
    polygonsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._polygons = []
        self.setSmooth(False)

    @Property('QVariantList', notify=polygonsChanged)
    def polygons(self):
        return self._polygons

    @polygons.setter
    def polygons(self, values):
        self._polygons = values
        self.polygonsChanged.emit()
        self.update()

    def paint(self, painter):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(PHOTO['exclusion']), Qt.BDiagPattern))
        for points in self._polygons:
            painter.drawPolygon(QPolygonF([QPointF(*point) for point in points]))


_registered = False


def register_paths():
    global _registered
    if not _registered:
        qmlRegisterType(ModulePaths, 'Meridiana.Plan.Paths', 1, 0, 'ModulePaths')
        qmlRegisterType(SoftwareHatch, 'Meridiana.Plan.Paths', 1, 0, 'SoftwareHatch')
        _registered = True
