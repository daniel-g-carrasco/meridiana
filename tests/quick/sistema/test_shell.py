"""R389/R381: the real shell, keyboard and panel gestures on a QQuickWindow."""
import tempfile
import sys
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QGuiApplication

from _fixtures import capannone
from meridiana import jobs
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.capture import grab
from quick.gestures import click, drag, item, key, mouse, point, pump, wait_for


class ShellTest(unittest.TestCase):
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
        results, keys, _ = jobs.layout_of(self.host.bridge.session.project)
        self.host.bridge.accept_layout(0, results, keys)
        pump(100)
        item(self.win, 'plan').fit()

    def tearDown(self):
        warnings = self.host.warnings[:]
        self.host.close()
        self.app.processEvents()
        self.temp.cleanup()
        self.assertEqual(warnings, [])

    def test_six_phases_have_real_shortcuts_and_variants_use_undo(self):
        key(self.app, self.win, Qt.Key.Key_3, modifiers=Qt.KeyboardModifier.ControlModifier)
        wait_for(lambda: self.win.property('phase') == 'production', 5)     # r21-f6c: the phase changes once the frame is photographed (a frame after the gesture)
        self.assertEqual(self.win.property('phase'), 'production')
        click(self.app, self.win, point(item(self.win, 'modelTab')))
        wait_for(lambda: self.win.property('phase') == 'model', 5)
        self.assertEqual(self.win.property('phase'), 'model')
        click(self.app, self.win, point(item(self.win, 'variantAdd')))
        self.assertEqual(len(self.host.bridge.session.project.variants), 2)
        self.host.bridge.undo()
        self.assertEqual(len(self.host.bridge.session.project.variants), 1)

    def test_real_drawing_command_and_persistent_property_edit(self):
        click(self.app, self.win, point(item(self.win, 'tool_tool_building')))
        plan = item(self.win, 'plan')
        self.assertEqual(plan.property('tool'), 'rectangle')
        before = len(self.host.bridge.session.project.buildings)
        start = point(plan, 90, 90)
        drag(self.app, self.win, start, start+QPointF(100, 60), steps=4)
        self.assertEqual(len(self.host.bridge.session.project.buildings), before+1)
        field = item(self.win, 'nameField')
        click(self.app, self.win, point(field))
        key(self.app, self.win, Qt.Key.Key_A, modifiers=Qt.KeyboardModifier.ControlModifier)
        for char in 'Edificio':
            key(self.app, self.win, ord(char.upper()), char)
        key(self.app, self.win, Qt.Key.Key_Return)
        self.assertEqual(self.host.bridge.selection['name'], 'Edificio')
        self.host.bridge.select('building', 'b1', '')
        self.assertIs(item(self.win, 'nameField'), field)

    def test_panel_edges_and_meridio_drag_have_no_python_callbacks(self):
        for edge, delta, panel_name in [('left',QPointF(50,0),'leftPanel'),
                                         ('right',QPointF(-50,0),'rightPanel'),
                                         ('bottom',QPointF(0,-50),'checksPanel')]:
            panel = item(self.win, panel_name)
            before = panel.height() if edge == 'bottom' else panel.width()
            handle = item(self.win, edge+'ResizeHandle')
            start = point(handle)
            self.host.bridge.calls.clear()
            calls = []
            def profile(frame, event, arg, calls=calls):
                if event == 'call' and '/meridiana/quick/' in frame.f_code.co_filename.replace('\\','/'):
                    calls.append(frame.f_code.co_name)
            pump(500)     # the arrangement the resize of setUp left pending goes first: only the drag is measured here
            previous = sys.getprofile()
            sys.setprofile(profile)
            try:
                drag(self.app, self.win, start, start+delta, steps=5)
            finally:
                sys.setprofile(previous)
            after = panel.height() if edge == 'bottom' else panel.width()
            self.assertGreater(after, before+40)
            self.assertEqual(sum(self.host.bridge.calls.values()), 0, (edge, dict(self.host.bridge.calls)))
            self.assertEqual(calls, [], (edge, calls))
        mascot = item(self.win, 'meridio')
        before = mascot.x()
        start = point(mascot)
        drag(self.app, self.win, start, start-QPointF(80,60), steps=5)
        self.assertLess(mascot.x(), before-60)

    def test_panel_closure_reopening_and_drag_drop_preserve_content(self):
        panel = item(self.win, 'leftPanel')
        tree = item(self.win, 'projectList')
        self.win.runCommand('panel_project')
        self.assertFalse(panel.isVisible())
        self.win.runCommand('panel_project')
        self.assertTrue(panel.isVisible())
        self.assertIs(tree, item(self.win, 'projectList'))
        title = item(self.win, 'projectTitleDrag')
        workspace = item(self.win, 'workspace')
        start = point(title)
        end = point(workspace, workspace.width()/2, workspace.height()/2)
        drag(self.app, self.win, start, end, steps=8)
        self.assertEqual(panel.property('zone'), 'floating')
        self.assertIs(tree, item(self.win, 'projectList'))
        self.win.runCommand('default_layout')
        pump(400)
        self.assertEqual(panel.property('zone'), 'left')

    def test_alt_pushes_content_and_file_creates_no_transient_window(self):
        top = point(item(self.win, 'workspace'),0,0).y()
        key(self.app, self.win, Qt.Key.Key_Alt)
        pump(220)
        self.assertTrue(self.win.property('menuOpen'))
        self.assertGreater(point(item(self.win, 'workspace'),0,0).y(), top)
        windows = set(QGuiApplication.topLevelWindows())
        click(self.app, self.win, point(item(self.win, 'fileButton')))
        for _ in range(8):
            pump(16)
            self.assertEqual(set(QGuiApplication.topLevelWindows()), windows)
            self.assertFalse(grab(self.win).isNull())
        self.assertTrue(self.win.property('fileOpen'))
        self.win.showPhase('model')
        wait_for(lambda: not self.win.property('fileOpen'), 5)     # r21-f6c: the phase changes once the frame is photographed (a frame after the gesture)
        self.assertFalse(self.win.property('fileOpen'))

    def test_live_theme_font_size_and_dark_pixels_without_rebuild(self):
        field = item(self.win, 'nameField')
        self.host.theme.configure(dict(theme='dark',font='inter',textSize='large',reducedMotion=True))
        pump(30)
        self.assertEqual(field.property('font').family(), 'Inter')
        self.assertEqual(field.property('font').pixelSize(), 14)
        self.assertIs(field, item(self.win, 'nameField'))
        image = grab(self.win)
        dpr = image.devicePixelRatio()
        self.assertLess(image.pixelColor(int(2*dpr),int(150*dpr)).lightness(), 60)

    def test_height_commits_with_tab_and_alt_works_in_file(self):
        self.host.bridge.select('building', 'b1', '')
        field = item(self.win, 'heightField')
        click(self.app, self.win, point(field))
        key(self.app, self.win, Qt.Key.Key_A, modifiers=Qt.KeyboardModifier.ControlModifier)
        key(self.app, self.win, Qt.Key.Key_9, '9')
        key(self.app, self.win, Qt.Key.Key_Tab)
        self.assertEqual(self.host.bridge.session.project.buildings[0].height, 9)
        self.win.runCommand('preferences')
        click(self.app, self.win, point(item(self.win, 'fontChoice')))
        key(self.app, self.win, Qt.Key.Key_Escape)
        key(self.app, self.win, Qt.Key.Key_Alt)
        self.assertTrue(self.win.property('menuOpen'))
        key(self.app, self.win, Qt.Key.Key_Alt, modifiers=Qt.KeyboardModifier.ControlModifier)
        self.assertTrue(self.win.property('menuOpen'), 'AltGr must not toggle the menu')

    def test_group_drop_waits_then_keeps_both_panels_and_help_returns(self):
        left, right = item(self.win, 'leftPanel'), item(self.win, 'rightPanel')
        title = item(self.win, 'projectTitleDrag')
        start, end = point(title), point(right)
        mouse(self.app,self.win,QEvent.Type.MouseButtonPress,start,Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton)
        mouse(self.app,self.win,QEvent.Type.MouseMove,end,Qt.MouseButton.NoButton,Qt.MouseButton.LeftButton)
        workspace = item(self.win,'workspace')
        self.assertEqual(workspace.property('targetZone'),'')
        wait_for(lambda: workspace.property('targetZone')=='right',seconds=2)
        mouse(self.app,self.win,QEvent.Type.MouseButtonRelease,end,Qt.MouseButton.LeftButton,Qt.MouseButton.NoButton)
        pump(400)
        self.assertEqual(left.property('zone'),'right')
        self.assertTrue(left.isVisible())
        self.assertFalse(right.isVisible())
        item(self.win,'workspace').selectPanel('properties')
        self.assertTrue(right.isVisible())
        self.assertFalse(left.isVisible())
        mascot = item(self.win,'meridio')
        before = QPointF(mascot.x(),mascot.y())
        self.win.runCommand('context_help')
        pump(300)
        self.assertNotEqual(QPointF(mascot.x(),mascot.y()),before)
        key(self.app,self.win,Qt.Key.Key_Escape)
        pump(300)
        self.assertAlmostEqual(mascot.x(),before.x(),delta=1)
        self.assertAlmostEqual(mascot.y(),before.y(),delta=1)

    def test_variant_selection_follows_new_variant_after_user_clicked_base(self):
        add = item(self.win,'variantAdd')
        click(self.app,self.win,point(add))
        pump(30)
        bar = item(self.win,'variantBar')
        click(self.app,self.win,point(bar,20,bar.height()/2))
        pump(30)
        self.assertEqual(bar.property('currentIndex'),0)
        click(self.app,self.win,point(add))
        pump(30)
        index = next(i for i,v in enumerate(self.host.shell.variants) if v['id']==self.host.shell.currentVariant)
        self.assertEqual(bar.property('currentIndex'),index)
