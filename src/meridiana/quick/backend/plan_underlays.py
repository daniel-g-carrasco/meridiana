"""Imported plan backgrounds: the same operations and collectors as the Widgets menu."""
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from meridiana import quantity, underlay
from .plan_locale import _


class Underlays(QObject):
    changed = Signal()
    prompt = Signal(str, str)

    def __init__(self, plan):
        super().__init__(plan)
        self.plan = plan
        self.pending = None
        plan.sceneChanged.connect(self.changed)
        plan.pointsPicked.connect(self.picked)

    @Property('QVariantList', notify=changed)
    def images(self):
        return [dict(id=u.id, name=u.name or _('Image {n}').format(n=n), visible=u.visible, opacity=u.opacity)
                for n, u in enumerate(self.plan.session.project.underlays, 1)]

    @Property('QVariantMap', constant=True)
    def texts(self):
        return dict(importImage=_('Import an image or PDF…'), show=_('Show'), transparency=_('Transparency'),
                    scale=_('In scale with two points…'), move=_('Move with two points…'), rotate=_('Rotate…'),
                    remove=_('Remove'), filter=_('Images and PDF (*.png *.jpg *.jpeg *.bmp *.webp *.pdf)'),
                    distance=_('True distance between the two points (m):'), angle=_('Rotation, anticlockwise (°):'))

    def change(self, uid, label, operation):
        old = next((u for u in self.plan.session.project.underlays if u.id == uid), None)
        if old is None:
            return
        new = operation(old)
        self.plan.session.edit(label, lambda p: setattr(p, 'underlays',
                               [new if u.id == uid else u for u in p.underlays]))

    @Slot(QUrl, float, float, float)
    def importImage(self, url, x, y, across):
        def add():
            from meridiana.ui.underlays import read_image
            path = Path(url.toLocalFile())
            data, w, h = read_image(path)
            image = underlay.placed(self.plan.session.project.new_id('u'), path.name, data, w, h, (x, y), across)
            self.plan.session.edit(_('Import an image'), lambda p: p.underlays.append(image))
        try:
            add()
        except (ValueError, OSError) as error:
            self.plan._layout_error(str(error))

    @Slot(str, str, float)
    def action(self, uid, action, value=0):
        if action == 'show':
            self.change(uid, _('Show or hide an image'), lambda u: replace(u, visible=bool(value)))
        elif action == 'opacity':
            self.change(uid, _('Change an image transparency'), lambda u: replace(u, opacity=value))
        elif action == 'remove':
            self.plan.session.edit(_('Remove an image'), lambda p: setattr(p, 'underlays',
                                   [u for u in p.underlays if u.id != uid]))
        elif action == 'rotate':
            self.pending = ('rotate', uid, [])
            self.prompt.emit(self.texts['rotate'], self.texts['angle'])
        elif action in ('scale', 'move'):
            hints = ([_('First point of the known distance'), _('Second point, then enter the distance')]
                     if action == 'scale' else [_('First point of the image'), _('Where that point goes')])
            self.plan.pickPoints(action+':'+uid, hints)

    def picked(self, purpose, points):
        action, _separator, uid = purpose.partition(':')
        if action not in ('scale', 'move') or len(points) != 2:
            return
        a, b = points
        if action == 'move':
            self.change(uid, _('Move an image'), lambda u: u.moved(b[0]-a[0], b[1]-a[1]))
        else:
            self.pending = (action, uid, points)
            self.prompt.emit(self.texts['scale'], self.texts['distance'])

    @Slot(str, result=bool)
    def accept(self, text):
        if not self.pending:
            return False
        action, uid, points = self.pending
        try:
            value = quantity.parse(text, 'angle' if action == 'rotate' else 'length')
            self.change(uid, _('Rotate an image') if action == 'rotate' else _('Put an image in scale'),
                        lambda u: u.rotated(value) if action == 'rotate' else u.scaled(*points, value))
        except ValueError as error:
            self.plan._layout_error(str(error))
            return False
        self.pending = None
        self.plan._layout_error('')
        return True
