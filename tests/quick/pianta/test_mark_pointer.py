"""R641 (Daniel 15/11/2026, the warning's mark over a building in the 3D view: «sti tasti di errore, ecc, non sono
cliccabili, non hanno tooltip. Prima almeno appariva il cursore a manina»): a check's mark on a view, on the plan and in
the 3D view alike (Controls/MarkArea.qml), shows the hand under the pointer, says the words of its checks in the house
tooltip, and a click on it selects what it marks and shows its checks.

In the 3D view the marks lay in the scene's canvas, under the view's input (R616): the arrow, no tooltip, the click to the
scene; on the plan the hand and the click were there, the tooltip was not."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPointF, Qt

import _setup
from _fixtures import capannone
from meridiana import i18n
from meridiana.app import jobs
from meridiana.app.view import viewaids
from meridiana.core.rules.checks import Item
from quick.gestures import click, mouse, pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(node.childItems())
    return out


class MarkTip(unittest.TestCase):
    """The words a mark says: its checks' texts, the worst first, the same once, and how many more past three."""

    def test_the_worst_first_the_same_once_and_how_many_more(self):
        tip = viewaids.mark_tip([('warn', 'Low tilt'), ('fail', 'Too close to the edge'), ('warn', 'Low tilt')])
        self.assertEqual(tip, 'Too close to the edge\nLow tilt')
        tip = viewaids.mark_tip([('warn', f'w{n}') for n in range(5)])
        self.assertEqual(tip.split('\n')[:3], ['w0', 'w1', 'w2'])
        self.assertEqual(len(tip.split('\n')), 4, 'three texts and how many more')
        self.assertIn('2', tip.split('\n')[3])


class MarkPointer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        from meridiana.gui.application import QuickWindow, create_app
        create_app()
        i18n.setup('en')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.session = cls.host.bridge.session
        results, keys, _ = jobs.layout_of(cls.session.project)
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1400, 860)
        pump(200)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def show_mark(self):
        """A warning on the building, shown and still there (the checks computed again replace the items shown)."""
        checks = self.host.parts.controllers['checks']
        inspectors = self.host.parts.controllers['inspectors']
        building = self.session.project.buildings[0].id
        extra = Item('warn', 'roof', 'Roof detail', target=('building', building))
        for _ in range(6):
            wait_for(lambda: not checks.busy, 15)
            checks.show_items([*[i for i in checks.items if i is not extra], extra])
            pump(800)
            if extra in checks.items and any(m['oid'] == building for m in inspectors.marks3d):
                return building
        self.fail('the checks\' mark never stayed')

    def point_at(self, mark):
        """The pointer brought onto the mark's middle from beside it, and left there for the tooltip's wait."""
        middle = mark.mapToScene(QPointF(mark.width() / 2, mark.height() / 2))
        for at in (middle + QPointF(40, 40), middle):
            mouse(self.app, self.win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
            pump(60)
        return middle

    def check_mark(self, find, building):
        mark = find()
        self.assertIsNotNone(mark, 'the mark is on the view')
        middle = self.point_at(mark)
        self.assertEqual(self.win.cursor().shape(), Qt.CursorShape.PointingHandCursor, 'the hand over the mark')
        tip = mark.findChildren(QObject, 'markTip')
        self.assertEqual(len(tip), 1)
        wait_for(lambda: tip[0].property('visible'), 5)
        self.assertIn('Roof detail', tip[0].property('text'))
        self.session.select('', '')
        checks = self.host.parts.controllers['checks']
        checks.showSubset([])
        pump(60)
        click(self.app, self.win, middle)
        pump(300)
        self.assertEqual(self.session.selection[:2], ('building', building), 'the click selects what it marks')
        self.assertEqual(checks._subset, ('building', building), 'and shows its checks')
        # away from the mark the view's own pointer comes back
        mouse(self.app, self.win, QEvent.Type.MouseMove, middle + QPointF(60, 60), Qt.MouseButton.NoButton,
              Qt.MouseButton.NoButton)
        pump(60)
        self.assertNotEqual(self.win.cursor().shape(), Qt.CursorShape.PointingHandCursor)

    def test_on_the_plan(self):
        self.win.setProperty('viewMode', 'plan')
        self.win.showPhase('model')
        pump(300)
        building = self.show_mark()
        plan = next(i for i in items(self.win.contentItem()) if i.objectName() == 'plan')
        wait_for(lambda: bool(self.host.plan.marks), 5)

        def find():
            found = [i for i in plan.childItems() if i.metaObject().className().startswith('PlanSymbol') and i.isVisible()]
            return found[0] if found else None
        wait_for(lambda: find() is not None, 10)
        self.check_mark(find, building)

    def test_in_the_3d_view(self):
        self.win.showPhase('model')
        self.win.setProperty('viewMode', '3d')
        pump(400)
        view = next(i for i in items(self.win.contentItem()) if i.objectName() == 'viewport3d')
        building = self.show_mark()

        def find():
            found = [i for i in items(view) if i.objectName() == 'scene-mark-building-' + building and i.isVisible()]
            return found[0] if found else None
        wait_for(lambda: find() is not None, 10)
        self.check_mark(find, building)


if __name__ == '__main__':
    unittest.main()
