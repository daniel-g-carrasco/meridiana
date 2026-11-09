"""R553 (Daniel 08/11/2026, lucciola, 1422 x 854, Production: «guarda anche sta schifezza. Sti controlli inoltre vorrei
che stessero all'interno di un gruppo allo stesso modo che facciamo in impianto»): the weather's source and the two
shadows at the end of the Production bar were cut by the bar (the second line of the weather) and the second shadow
went out of it onto the card below. Now they are a group as the Plant's summary (M.InfoGroup) and never taller than
their room: side by side in the low bar, one above the other above the views or in the bar with the words.

R552 (the same evening: «questa scritta si nasconde dietro i pannelli»): the credit of the plan's background is above
the project's drawing, on a full dark ground.

    python -m unittest quick.grafici.test_testata_produzione_r553
"""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

from meridiana import i18n, jobs
from meridiana.quick.app import QuickWindow, create_app
from quick import confini
from quick.gestures import item, pump, wait_for
from quick.parity.differential import connected_fixture

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

NAMES = ('productionStrip', 'meteoState', 'useHorizon', 'useNear')


def shown(window, name):
    pending = [window.contentItem()]
    while pending:
        node = pending.pop()
        if node.objectName() == name and node.isVisible():
            return node
        pending.extend(node.childItems())
    return None


def rect(node):
    corner = node.mapToScene(QPointF(0, 0))
    return corner.x(), corner.y(), corner.x() + node.width(), corner.y() + node.height()


class ProductionHead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        pump(300)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def inside(self, inner, outer, why):
        a, b = rect(inner), rect(outer)
        self.assertTrue(a[0] >= b[0] - .5 and a[1] >= b[1] - .5 and a[2] <= b[2] + .5 and a[3] <= b[3] + .5,
                        (why, inner.objectName(), a, outer.objectName(), b))

    def test_r553_the_shadows_stay_in_their_group_and_the_group_in_its_room(self):
        self.host.shell.trigger('phase_production')
        wait_for(lambda: shown(self.win, 'productionStrip') is not None, 30)
        for size, mode in (((1422, 828), 'auto'), ((1422, 828), 'under'), ((1422, 828), 'beside'), ((1600, 960), 'beside'), ((1600, 960), 'auto'), ((1000, 700), 'auto'),
                           ((800, 560), 'auto')):
            self.win.setProperty('toolbarMode', mode)
            self.win.resize(*size)
            pump(900)
            strip = shown(self.win, 'productionStrip')
            self.assertIsNotNone(strip, (size, mode))
            room = item(self.win, 'phaseTrailing') if item(self.win, 'phaseTrailing').isVisible() else item(self.win, 'viewsTrailing')
            self.inside(strip, room, (size, mode))
            for name in ('useHorizon', 'useNear'):
                self.inside(shown(self.win, name), strip, (size, mode))
            meteo = shown(self.win, 'meteoState')
            if meteo is not None:                       # it goes first when the room is short
                self.inside(meteo, strip, (size, mode))
            found = [str(f) for f in confini.audit(self.win) if any(n in f.where for n in NAMES)]
            self.assertEqual(found, [], (size, mode))
        self.win.setProperty('toolbarMode', 'auto')
        self.win.resize(1600, 960)
        pump(600)

    def test_r552_the_credit_of_the_background_is_above_the_drawing_on_a_full_ground(self):
        self.host.shell.trigger('phase_model')
        pump(400)
        credit = item(self.win, 'mapCredit')
        world = item(self.win, 'worldLayer')
        self.assertIs(credit.parentItem(), world.parentItem())
        siblings = credit.parentItem().childItems()
        self.assertGreater(siblings.index(credit), siblings.index(world), 'drawn after the project, so above it')
        self.assertEqual(QColor(credit.property('color')).alpha(), 255)


if __name__ == '__main__':
    unittest.main()
