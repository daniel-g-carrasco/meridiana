"""Plan behaviour in the real workbench, including its global shortcuts and settings."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QPoint, Qt
from PySide6.QtTest import QTest

from meridiana.core.model import model
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import item, pump, wait_for

APP = None


def setUpModule():
    global APP
    APP = create_app()


class Installed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.host = QuickWindow(model.Project(), Path(cls.temp.name), real_views=True)
        cls.root, cls.c = cls.host.window, cls.host.plan
        cls.root.resize(1600, 960)
        cls.root.show()
        wait_for(cls.root.isExposed)
        cls.plan = item(cls.root, 'plan')
        pump(100)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        APP.processEvents()
        cls.temp.cleanup()

    def setUp(self):
        self.c.setTool('select')
        self.c.calls.clear()

    def test_shell_escape_does_not_bypass_drawing_and_status_reaches_footer(self):
        self.host.shell.trigger('tool_building')
        p = self.plan.mapToScene(self.plan.boundingRect().center()).toPoint()
        QTest.mouseClick(self.root, Qt.LeftButton, Qt.NoModifier, p)
        QTest.keyClick(self.root, Qt.Key_1)
        QTest.keyClick(self.root, Qt.Key_2)
        self.assertEqual(self.c.drawing.typed, '12')
        self.assertEqual(self.host.shell._notice, self.c.hint)
        QTest.keyClick(self.root, Qt.Key_Escape)
        self.assertEqual(self.c.tool, 'building')
        self.assertTrue(self.c.drawing.points)
        self.assertFalse(self.c.drawing.typed)
        QTest.keyClick(self.root, Qt.Key_Escape)
        self.assertEqual(self.c.tool, 'building')
        self.assertFalse(self.c.drawing.points)
        QTest.keyClick(self.root, Qt.Key_Escape)
        self.assertEqual(self.c.tool, 'select')
        self.assertFalse(self.host.warnings, self.host.warnings)

    def test_the_menu_of_measure_chooses_the_mode_and_ortho_gives_the_guides(self):
        """Study 46: Measure's button holds Distance, Height and «Remove all», each a command of the shell; the 15°
        guides are no entry of it (Daniel 14/11/2026): they follow the plan's Ortho, the window's command of F8."""
        model_phase = next(p for p in self.host.shell.phases if p['id'] == 'model')
        button = next(t for g in model_phase['groups'] for t in g['tools'] if t['command'] == 'tool_measure')
        self.assertEqual([(t['command'], t['enabled']) for t in button['more']],
                         [('measure_distance', True), ('measure_height', True), ('measure_clear', True)])
        bridge = self.c.measure
        self.addCleanup(bridge.setMode, 'distance')
        self.host.shell.trigger('measure_height')
        self.assertEqual((self.c.tool, bridge.mode), ('measure', 'height'))
        self.assertEqual(self.c.hint, bridge.hint)
        # the mode chosen is in the hint: the height's foot, in the catalogue's language or in the source's
        self.assertTrue(any(word in self.c.hint for word in ('foot', 'piede')), self.c.hint)
        self.host.shell.trigger('tool_measure')                          # the button itself keeps the mode
        self.assertEqual(bridge.mode, 'height')
        polar = bridge.polar
        self.assertEqual(polar, self.c.drawing.orthogonal)
        self.host.shell.trigger('ortho')                                 # F8, the view bar's button: one setting
        self.addCleanup(lambda: self.c.drawing.orthogonal == polar or self.c.viewAction('ortho'))
        self.assertEqual((bridge.polar, self.c.orthoEnabled, self.c.drawing.orthogonal), (not polar,) * 3)
        self.host.shell.trigger('ortho')
        self.assertEqual((bridge.polar, self.c.drawing.orthogonal), (polar, polar))
        self.host.shell.trigger('measure_distance')
        self.assertEqual((self.c.tool, bridge.mode), ('measure', 'distance'))
        self.assertFalse(self.host.warnings, self.host.warnings)

    def test_remove_all_measurements_from_the_menu_and_the_project_stays_clean(self):
        """Study 46, 3.6 (Daniel's choice 3): the measures are of the session; «Remove all measurements» in Measure's
        menu takes them away; making and removing them never touches the project, its undo or the window's title."""
        session, bridge = self.host.bridge.session, self.c.measure
        session.mark_saved()
        title, steps = self.root.title(), (len(session.undo.steps), session.undo.index)
        self.host.shell.trigger('tool_measure')
        for x, y in ((10, 10), (60, 10)):
            bridge.click('plan', x, y, 0, 1.0)
        bridge.key('Enter', '', 0)
        self.host.shell.trigger('tool_select')
        self.assertEqual(bridge.count, 1)
        self.host.shell.trigger('measure_clear')
        self.assertEqual((bridge.count, self.c.tool), (0, 'select'))     # the tool in hand stays
        self.host.shell.trigger('measure_clear')                        # none made: nothing happens
        self.assertEqual(bridge.count, 0)
        pump(20)
        self.assertFalse(session.dirty())
        self.assertEqual((len(session.undo.steps), session.undo.index), steps)
        self.assertEqual(self.root.title(), title)
        self.assertNotIn('*', self.root.title())
        self.assertFalse(self.host.warnings, self.host.warnings)

    def test_preferences_and_view_commands_act_on_the_installed_plan(self):
        settings = self.host.parts.controllers['settings']
        settings.setValue('navigation', 'touchpad')
        self.assertEqual(self.c.navigationStyle['middle_click'], '')
        self.c.chooseMapOptions({'source': 'none', 'veil': .6})
        self.assertEqual(settings.cfg.background, 'none')
        self.assertEqual(settings.cfg.veil, .6)
        self.assertEqual(self.c.maps.choice, 'none')
        self.plan.fit()
        self.plan.setProperty('panX', self.plan.property('panX')+87)
        self.plan.setProperty('panY', self.plan.property('panY')-31)
        before = self.plan.world(self.plan.width()/2, self.plan.height()/2)
        zoom = self.plan.property('zoom')
        self.host.shell.trigger('zoom_in')
        after = self.plan.world(self.plan.width()/2, self.plan.height()/2)
        self.assertAlmostEqual(self.plan.property('zoom'), zoom*1.2)
        self.assertAlmostEqual(before.x(), after.x())
        self.assertAlmostEqual(before.y(), after.y())
        self.assertFalse(self.plan.property('fitted'))
        panel = item(self.root, 'rightPanel')
        self.c.viewAction('properties')
        self.c.viewAction('properties')
        self.assertTrue(panel.property('opened'))

    def test_escape_during_a_sweep_cancels_without_committing_on_release(self):
        a = self.plan.mapToScene(self.plan.boundingRect().center()).toPoint()
        QTest.mousePress(self.root, Qt.LeftButton, Qt.NoModifier, a)
        QTest.mouseMove(self.root, a+QPoint(60, 60))
        self.assertTrue(item(self.root, 'selectionOverlay').property('sweeping'))
        QTest.keyClick(self.root, Qt.Key_Escape)
        QTest.mouseRelease(self.root, Qt.LeftButton, Qt.NoModifier, a+QPoint(60, 60))
        self.assertEqual(self.c.calls['sweep'], 0)
        self.assertFalse(item(self.root, 'selectionOverlay').property('sweeping'))
