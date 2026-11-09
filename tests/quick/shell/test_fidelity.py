"""R388/R392: shell regressions driven on the native Quick window."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Qt

from _fixtures import capannone
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import click, item, key, point, pump


class FidelityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.host = QuickWindow(capannone(), Path(self.temp.name))
        self.win = self.host.window
        self.win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.win.show()
        self.win.resize(1600, 960)
        pump(120)

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        self.app.processEvents()
        self.temp.cleanup()
        self.assertEqual(warnings, [])

    def test_file_occupies_toolbar_space_and_chip_is_checked(self):
        normal = point(item(self.win, 'workspace'), 0, 0).y()
        self.assertTrue(item(self.win, 'modelTab').property('selected'))
        self.win.setProperty('fileOpen', True)
        pump(220)
        page = item(self.win, 'filePage')
        self.assertLess(point(page, 0, 0).y(), normal-50)
        self.assertTrue(item(self.win, 'fileButton').property('checked'))
        self.assertFalse(item(self.win, 'phaseToolbar').isVisible())
        self.assertFalse(item(self.win, 'phaseOutline').isVisible())
        self.assertFalse(item(self.win, 'modelTab').property('selected'))
        key(self.app, self.win, Qt.Key.Key_Escape)
        pump(220)
        self.assertTrue(item(self.win, 'modelTab').property('selected'))
        self.assertFalse(item(self.win, 'fileButton').property('checked'))

    def test_side_toolbar_keeps_split_actions(self):
        self.win.setProperty('toolbarPosition', 'left')
        pump(250)
        button = item(self.win, 'sideTool_tool_building')
        self.assertTrue(button.isVisible())
        self.assertEqual((button.width(), button.height()), (33, 33))
        self.assertEqual(point(item(self.win, 'leftPanel'), 0, 0).x(), 49)
        arrow = item(self.win, 'sideTool_tool_buildingArrow')
        click(self.app, self.win, point(arrow))
        pump(50)
        self.assertTrue(button.property('menuOpened'))
        self.assertTrue(item(self.win, 'phaseMenu_tool_building').isVisible())
        key(self.app, self.win, Qt.Key.Key_Escape)

    def test_panels_match_reference_and_project_returns(self):
        left, right = item(self.win, 'leftPanel'), item(self.win, 'rightPanel')
        field = item(self.win, 'nameField')
        self.assertAlmostEqual(left.width(), 310, delta=2)
        self.assertAlmostEqual(right.width(), 370, delta=2)
        self.win.showPhase('production')
        pump(30)
        self.assertFalse(left.isVisible())
        self.win.showPhase('model')
        pump(30)
        self.assertTrue(left.isVisible())
        # Result fallbacks also have a nameField. Check the visible borrowed
        # editor, rather than QObject.findChild's first hidden namesake.
        pending, visible = [self.win.contentItem()], []
        while pending:
            child = pending.pop()
            pending.extend(child.childItems())
            if child.objectName() == 'nameField' and child.isVisible():
                visible.append(child)
        self.assertEqual(visible, [field], 'The borrowed inspector must stay alive')
        self.win.runCommand('panel_project')
        self.win.showPhase('production')
        self.win.showPhase('model')
        self.assertFalse(left.isVisible(), 'Closing a panel is remembered across phases')

    def test_status_has_three_panel_controls_and_help(self):
        for name in ('statusPanelLeft', 'statusPanelBottom', 'statusPanelRight', 'statusHelp', 'statusWarnings'):
            self.assertTrue(item(self.win, name).isVisible())
        self.win.showPhase('production')
        pump(30)
        self.assertTrue(item(self.win, 'tool_compute').property('flat'), 'R396: Calculate has no fixed background')

    def test_dark_cards_have_one_opaque_surface(self):
        self.host.theme.configure({'theme': 'dark', 'backgrounds': 'grey'})
        pump(120)
        picture = self.win.grabWindow()
        ratio = picture.devicePixelRatio()
        def color(x, y):
            return picture.pixelColor(int((x+.5)*ratio), int((y+.5)*ratio)).name()
        for pos in ((1500, 80), (400, 80), (25, 600)):
            self.assertEqual(color(*pos), '#252525', 'Toolbar and panel share the Widgets dark surface')
        self.assertEqual(color(5, 80), '#151515')

    def test_alt_focuses_first_menu_and_arrows_open_the_next(self):
        key(self.app, self.win, Qt.Key.Key_Alt)
        pump(220)
        self.assertTrue(self.win.property('menuOpen'))
        self.assertTrue(item(self.win, 'mainMenu_0').hasActiveFocus())
        key(self.app, self.win, Qt.Key.Key_Right)
        self.assertTrue(item(self.win, 'mainMenu_1').hasActiveFocus())
        key(self.app, self.win, Qt.Key.Key_Down)
        pump(40)
        self.assertTrue(item(self.win, 'mainMenu_1').property('menuOpened'))
        key(self.app, self.win, Qt.Key.Key_Escape)
        pump(120)
        self.assertFalse(item(self.win, 'mainMenu_1').property('menuOpened'))

    def test_narrow_layout_returns_to_user_sizes_and_clean_screen_toggles(self):
        workspace = item(self.win, 'workspace')
        workspace.setProperty('leftExtent', 330)
        self.win.resize(850, 1000)
        pump(450)
        self.assertEqual(item(self.win, 'leftPanel').property('zone'), 'right')
        self.win.resize(1600, 960)
        pump(600)
        self.assertAlmostEqual(item(self.win, 'leftPanel').width(), 330, delta=1)

        self.win.runCommand('clean_screen')
        self.assertFalse(item(self.win, 'leftPanel').isVisible())
        self.win.runCommand('clean_screen')
        pump(400)
        self.assertTrue(item(self.win, 'leftPanel').isVisible())
        self.assertAlmostEqual(item(self.win, 'leftPanel').width(), 330, delta=1)

    def test_toolbar_uses_measured_width_before_switching_to_icons(self):
        self.win.resize(800, 1000)
        pump(400)
        self.assertEqual(item(self.win, 'phaseBar').property('barMode'), 'icons')
        self.win.resize(1600, 800)
        pump(400)
        self.assertEqual(item(self.win, 'phaseBar').property('barMode'), 'beside')

    def test_restore_again_recovers_the_previous_layout(self):
        workspace = item(self.win, 'workspace')
        workspace.setProperty('leftExtent', 350)
        item(self.win, 'checksPanel').setProperty('opened', False)
        self.win.runCommand('default_layout')
        pump(400)
        self.assertAlmostEqual(item(self.win, 'leftPanel').width(), 310, delta=1)
        self.assertTrue(item(self.win, 'checksPanel').isVisible())
        self.win.runCommand('default_layout')
        pump(400)
        self.assertAlmostEqual(item(self.win, 'leftPanel').width(), 350, delta=1)
        self.assertFalse(item(self.win, 'checksPanel').isVisible())

    def test_restart_restores_sizes_grouping_and_closed_panels(self):
        workspace = item(self.win, 'workspace')
        workspace.setProperty('rightExtent', 410)
        item(self.win, 'leftPanel').setProperty('zone', 'right')
        item(self.win, 'checksPanel').setProperty('opened', False)
        workspace.arrangementChanged.emit()
        self.host.close()
        pump(30)
        self.assertTrue((Path(self.temp.name)/'quick-profile/state/quick-shell.json').exists())
        self.host = QuickWindow(capannone(), Path(self.temp.name))
        self.win = self.host.window
        self.win.show()
        # r22-unita: the window's size is not part of quick-shell.json; offscreen the screen is 800 x 800, so R430
        # brings the new window to 796 and the right column to 34 % of it (284). The size of setUp, as on a desktop.
        self.win.resize(1600, 960)
        pump(450)
        self.assertEqual(item(self.win, 'workspace').property('rightExtent'), 410)
        self.assertAlmostEqual(item(self.win, 'rightPanel').width(), 410, delta=1)
        # R549: every start shows Project on the left and Properties on the right (shell_state.at_start), and the
        # Checks as the window's height wants them (960 px: open)
        self.assertEqual(item(self.win, 'leftPanel').property('zone'), 'left')
        self.assertTrue(item(self.win, 'checksPanel').isVisible())
