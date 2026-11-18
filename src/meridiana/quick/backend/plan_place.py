"""The plan's «Place» mode for an imported IFC model (R454): the model's outlines follow the pointer or stand where the
import put them, turn with R or the wheel held with Shift, take the corners and the sides of the buildings already
drawn, go to coordinates; a click or Enter lays them, Esc gives the import up. Gestures only: the arithmetic is
`meridiana.ifc_place`, the change one `session.edit` made by the plan (PlanBackend.finish_placing)."""
from __future__ import annotations

from meridiana import ifc_place, move
from meridiana.i18n import number

from .plan_locale import _

NUDGE = move.NUDGE


class Placer:
    def __init__(self):
        self.cancel()

    def cancel(self):
        self.plan = self.place = None
        self.pl = None
        self.shapes = []
        self.follow = False
        self.snap = ifc_place.Snap()
        self.asking = []                # the buildings the model would fall on, while the question is open
        self.name = ''
        self.error = ''
        self.snaps_on = True

    @property
    def active(self):
        return self.plan is not None

    def start(self, plan, place=None, follow=True, name='', pl=None):
        self.cancel()
        self.plan, self.place, self.follow, self.name = plan, place, bool(follow), name
        self.pl = pl or ifc_place.start(plan)
        self.shapes = ifc_place.shapes(plan)

    @property
    def hint(self):
        if self.error:
            return self.error
        if self.asking:
            return _('The model falls on a building already drawn: choose what to do · Esc: go on placing')
        turn = _('R or Shift+wheel: turn · C: coordinates')
        if self.follow:
            return _('Place the model: click or Enter lays it · {turn} · Ctrl: no snaps · Esc: no import').format(turn=turn)
        return _('The model is where the file puts it: Enter lays it here · M: move it with the mouse · {turn} · Esc: no '
                 'import').format(turn=turn)

    def outlines(self):
        return ifc_place.moved(self.shapes, self.pl) if self.active else []

    def move(self, point, mods, mpp, project):
        """The pointer at `point`: the model under it (while it follows), snapped unless Ctrl or the snaps are off."""
        if not self.active or not self.follow or self.asking:
            return False
        self.error = ''
        pl = ifc_place.follow(self.plan, self.pl, point)
        self.snap = ifc_place.Snap()
        if self.snaps_on and 'ctrl' not in mods:
            rings = [r for k, r in ifc_place.moved(self.shapes, pl) if k == 'building']
            self.snap = ifc_place.snap(project, rings, ifc_place.SNAP_PX * mpp)
            pl = ifc_place.shifted(pl, self.snap.dx, self.snap.dy)
        self.pl = pl
        return True

    def turn(self, steps, mods):
        step = move.ANGLE_STEPS['shift' if 'shift' in mods else 'ctrl' if 'ctrl' in mods else '']
        self.pl = ifc_place.turned(self.plan, self.pl, step * steps)
        self.snap = ifc_place.Snap()

    def nudge(self, key, mods):
        step = NUDGE['shift' if 'shift' in mods else 'ctrl' if 'ctrl' in mods else '']
        dx, dy = {'Left': (-step, 0.0), 'Right': (step, 0.0), 'Up': (0.0, step), 'Down': (0.0, -step)}[key]
        self.pl = ifc_place.shifted(self.pl, dx, dy)
        self.follow = False                         # the arrows hold it: the mouse no longer moves it

    def placed(self):
        return ifc_place.placed(self.plan, self.pl)

    def card(self):
        """What the pointer's card says while the model is placed: the turn and the distance from the site."""
        if not self.active:
            return ''
        turn = ifc_place.turn_of(self.plan, self.pl)
        return _('turn {turn}° · {km} km from the site').format(turn=number(turn, 1),
                                                                    km=number(ifc_place.distance_km(self.plan, self.pl), 2))
