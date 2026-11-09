"""Prepare native Qt Shape paths once per layout, never on the render thread."""
from collections import defaultdict

from PySide6.QtCore import QPointF, QRectF, Qt, Property, Signal
from PySide6.QtGui import QPainterPath, QPainterPathStroker, QPolygonF
from PySide6.QtQml import qmlRegisterType
from PySide6.QtQuick import QQuickItem
from meridiana.view_colours import WIDTHS


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


def batches(modules, fill='#192d5a', stroke='#c6cbd6'):
    groups = defaultdict(list)
    for module in modules:
        points = [(p.x(), p.y()) if hasattr(p, 'x') else p for p in module['points']]
        if not points:
            continue
        path = 'M' + ' L'.join(f'{x:.8g},{y:.8g}' for x, y in points)
        if module.get('closed', True):
            path += ' Z'
        groups[(module.get('fill', fill), module.get('stroke', stroke), module.get('width', WIDTHS['module_line']),
                module.get('dashed', False))].append(path)
    # Bound each native path: large SVG paths hit Qt's path/vertex limits.
    return [dict(fill=f, stroke=s, width=w, dashed=d, path=' '.join(paths[start:start+1000]))
            for (f, s, w, d), paths in groups.items() for start in range(0, len(paths), 1000)]


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
        """Paths already joined by the controller: nothing to prepare here."""
        self._paths = value
        self.uploads += 1
        self.pathsChanged.emit()


_registered = False


def register_paths():
    global _registered
    if not _registered:
        qmlRegisterType(ModulePaths, 'Meridiana.Plan.Paths', 1, 0, 'ModulePaths')
        _registered = True
