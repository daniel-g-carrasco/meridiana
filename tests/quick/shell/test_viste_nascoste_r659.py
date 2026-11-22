"""R659 (Daniel 15/11/2026, Balance, «How it is computed»: a module's tooltip of the plan, «Module 10 of 15 / String
6.2.1 ...», over the NPV formula: «come mai succede questo???? grave»). The plan and the 3D stay up under the pages of
the phases without them, disabled and with opacity 0 (Workbench, `views`, since cb71f3b4 of 08/11/2026). A MouseArea
disabled under the pointer keeps its containsMouse, and a tooltip lives in Qt's overlay: the plan's module tooltip,
open when the phase changed from the keyboard, stayed over the page. Reproduced on c6f4c5a5, fda58ea6, a65bf0a7,
8636d85b and aafa816c with a probe (the window shown off screen, the pointer left on a module, the phase changed):
the tooltip visible after the change; not after this fix. In this test's run the stale hover does not always survive the
change, so the test checks the outcome over the pages and asks the tooltip open itself.

The rule now (ToolTip, Popup, Menu): a popup of an item out of reach closes and does not open. Here: in every phase
without the plan, and with File over the plan, the pointer over the page meets no tooltip, menu or cursor of the plan or
of the 3D, and a click changes no selection."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPointF, Qt

import _setup
from _fixtures import capannone
from meridiana.app import jobs
from quick.gestures import click, mouse, pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def project():
    """The shed of the fixtures, laid, with six strings: its modules have words for the tooltip."""
    p = capannone()
    results, _keys, _ = jobs.layout_of(p)
    sid = p.subfields[0].id
    modules = results[sid].modules
    per = len(modules) // 6
    p.energy['strings'] = {'runs': [{'inverter': 1 + i // 3, 'mppt': 1,
                                     'modules': [sid + '/' + m.key for m in modules[i*per:(i+1)*per]]}
                                    for i in range(6)]}
    return p


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(node.childItems())
    return out


class PopupsOutOfReach(unittest.TestCase):
    """The rule itself, on a small scene: a tooltip, a menu and a panel of an item disabled (as the views under a page)
    do not open when asked, close when it is disabled, and open again once it is enabled. (On this small scene Qt alone
    already closes them at the change; the window's case, a binding asking again later, is the probe's of 15/11.)"""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_tooltip_menu_and_panel(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QColor
        from PySide6.QtQml import QQmlComponent, QQmlEngine
        from PySide6.QtQuick import QQuickWindow
        from shiboken6 import delete

        from meridiana.gui.backend.controls import install_controls
        engine = QQmlEngine()
        theme = install_controls(engine, dict(theme="light", reducedMotion=True))
        component = QQmlComponent(engine)
        component.setData(b'import QtQuick\nimport Meridiana.Controls as M\n'
                          b'Item { width: 400; height: 300\n'
                          b'  Item { objectName: "view"; width: 300; height: 200\n'
                          b'    M.ToolTip { objectName: "tip"; text: "Module 10 of 15" }\n'
                          b'    M.Menu { objectName: "menu"; M.MenuItem { text: "Delete" } }\n'
                          b'    M.Popup { objectName: "panel"; width: 80; height: 40 } } }', QUrl())
        self.assertFalse(component.isError(), "\n".join(e.toString() for e in component.errors()))
        root = component.create()
        root.setParent(engine)
        window = QQuickWindow()
        window.setColor(QColor(theme.colors["panel"]))
        window.resize(400, 300)
        root.setParentItem(window.contentItem())
        window.show()
        self.addCleanup(lambda: (window.close(), delete(root), delete(window), delete(engine)))
        pump(100)
        view = next(i for i in items(root) if i.objectName() == 'view')
        popups = [o for o in view.findChildren(QObject) if o.objectName() in ('tip', 'menu', 'panel')]
        self.assertEqual(len(popups), 3)
        for popup in popups:
            with self.subTest(popup=popup.objectName()):
                popup.setProperty('visible', True)
                wait_for(lambda p=popup: p.property('visible'), 3)      # a tooltip after its wait
                self.assertTrue(popup.property('visible'), 'open while its item is in reach')
                view.setEnabled(False)
                pump(60)
                self.assertFalse(popup.property('visible'), 'closed when its item goes out of reach')
                popup.setProperty('visible', True)
                pump(1200)
                self.assertFalse(popup.property('visible'), 'never opened while out of reach')
                view.setEnabled(True)
                popup.setProperty('visible', True)
                wait_for(lambda p=popup: p.property('visible'), 3)
                self.assertTrue(popup.property('visible'), 'opens again in reach')
                popup.setProperty('visible', False)
                pump(60)


class HiddenViews(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        from meridiana.gui.application import QuickWindow, create_app
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.session = cls.host.bridge.session
        results, keys, _ = jobs.layout_of(cls.session.project)
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1400, 860)
        pump(200)
        cls.win.setProperty('viewMode', 'plan')

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def find(self, name):
        return next((i for i in items(self.win.contentItem()) if i.objectName() == name), None)

    def move(self, at):
        mouse(self.app, self.win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
        pump(25)

    def views_popups(self, known=None):
        """The tooltips, menus and panels of the plan and of the 3D view on screen (among `known`, the list of them
        found once, or all of them looked for again)."""
        if known is None:
            known = self.popups_of_views()
        shown = []
        for name, o in known:
            try:
                if o.property('visible'):
                    shown.append(f'{name}: {o.objectName() or o.metaObject().className()}')
            except RuntimeError:        # a delegate's popup made again meanwhile (the plan's marks, its strings)
                continue
        return shown

    def popups_of_views(self):
        found = []
        # every item of those names: a page of the results may hold one called «plan» too
        for view in [i for i in items(self.win.contentItem()) if i.objectName() in ('plan', 'viewport3d')]:
            name = view.objectName()
            if view is not None:
                # every Qt Quick popup (a tooltip, a menu, a panel): it has `opened` and `closePolicy`
                found += [(name, o) for o in view.findChildren(QObject)
                          if o.metaObject().indexOfProperty('closePolicy') >= 0
                          and o.metaObject().indexOfProperty('opened') >= 0]
        return found

    def hover_a_module(self):
        """The Plant, the pointer on a module until the plan's tooltip says its words."""
        self.win.showPhase('plant')
        pump(2500)                  # the plan made again for the Plant (its pieces) before the pointer comes
        for _attempt in range(3):
            try:
                plan = self.find('plan')
                tip = next(o for o in plan.findChildren(QObject) if o.objectName() == 'moduleTip')
                for gx in range(5, 95, 3):
                    for gy in range(5, 95, 3):
                        self.move(plan.mapToScene(QPointF(plan.width() * gx / 100, plan.height() * gy / 100)))
                        if tip.property('text'):
                            wait_for(lambda t=tip: t.property('visible'), 5)
                            pump(900)           # the tooltip open and settled, as the pointer rests
                            if tip.property('visible'):
                                return tip
            except RuntimeError:                # the plan made again under the pointer: once more
                pump(1000)
        self.fail('no module\'s tooltip on the plan')

    def sweep(self, label):
        """The pointer over a grid of the window's middle: no popup and no cursor of the views."""
        central = self.find('centralPanel')
        known = self.popups_of_views()
        self.assertTrue(known, 'the views\' popups are found')
        cursors = set()
        for gx in range(1, 10):
            for gy in range(1, 8):
                self.move(central.mapToScene(QPointF(central.width() * gx / 10, central.height() * gy / 8)))
                self.assertEqual(self.views_popups(known), [], f'{label}: a popup of a view over the page at {gx},{gy}')
                cursors.add(self.win.cursor().shape())
        # the plan's and the 3D's own cursors (a tool's cross, the corners' arrows, a mark's hand) never over the page
        self.assertFalse(cursors & {Qt.CursorShape.CrossCursor, Qt.CursorShape.SizeAllCursor}, label)

    def test_the_views_under_the_pages_answer_nothing(self):
        for phase in ('production', 'consumption', 'economics', 'report'):
            with self.subTest(phase=phase):
                self.hover_a_module()
                self.win.showPhase(phase)                        # from the keyboard: the pointer has not moved
                pump(1500)
                self.assertEqual(self.views_popups(), [], f'{phase}: the module\'s tooltip went with the plan')
                self.sweep(phase)
                # whether the stale hover survives the change depends on the order of the window's turns (the probe
                # of 15/11 kept it, a run here may not): what its binding did, asking the module's tooltip open while
                # the plan is out of sight, is asked directly, and the tooltip does not stay
                for _attempt in range(3):
                    try:
                        tips = [o for _name, o in self.popups_of_views() if o.objectName() == 'moduleTip']
                        self.assertTrue(tips)
                        tips[0].setProperty('visible', True)
                        break
                    except RuntimeError:        # the plan's items made again meanwhile
                        pump(300)
                pump(100)
                self.assertEqual(self.views_popups(), [], f'{phase}: the module\'s tooltip asked open over the page')
                before = tuple(self.session.selection)
                central = self.find('centralPanel')
                click(self.app, self.win, central.mapToScene(QPointF(central.width() / 2, central.height() * .6)))
                pump(200)
                self.assertEqual(tuple(self.session.selection), before, f'{phase}: a click on the page selects nothing')

    def test_file_over_the_views(self):
        self.hover_a_module()
        self.win.setProperty('fileOpen', True)
        pump(600)
        self.addCleanup(lambda: self.win.setProperty('fileOpen', False))
        self.assertEqual(self.views_popups(), [])
        self.sweep('File')


if __name__ == '__main__':
    unittest.main()
