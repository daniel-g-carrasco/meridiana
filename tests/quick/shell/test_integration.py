"""One real workbench journey across the installed parts and their commands."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, Qt

from _fixtures import capannone
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, key, mouse, point, pump, wait_for


class IntegrationTest(unittest.TestCase):
    maxDiff = None
    def test_installed_pages_share_state_and_all_catalogue_commands_have_handlers(self):
        app = create_app()
        with tempfile.TemporaryDirectory() as temporary:
            host = QuickWindow(capannone(), Path(temporary), real_views=True)
            try:
                win, session = host.window, host.bridge.session
                def ready():
                    controller = host.engine.incubationController()
                    wait_for(lambda: controller.incubatingObjectCount() == 0, seconds=10)
                win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
                win.show()
                pump(250)
                self.assertEqual(set(host.shell.commands_known())-host.shell._handlers.keys(), set())
                self.assertIs(host.parts.controllers['assistant_help'].cfg, host.cfg)
                self.assertGreater(point(item(win, 'assistantCharacter')).y(), 120, 'The character must not cover File')
                from PySide6.QtCore import QRectF
                scene = item(win, 'viewport3d')
                scene_rect = QRectF(point(scene, 0, 0), point(scene, scene.width(), scene.height()))
                wait_for(lambda: scene_rect.contains(point(item(win, 'assistantCharacter'))), seconds=5)
                self.assertTrue(scene_rect.contains(point(item(win, 'assistantCharacter'))),
                                'Meridio starts inside the 3D view without changing phase')
                first = item(win, 'propertiesPartLoader').property('item')
                self.assertIsNotNone(first)
                settings = host.parts.controllers['settings']
                settings.setValue('menu_bar', True)
                self.assertTrue(win.property('menuAlways'))
                host.shell.trigger('menu_bar')
                self.assertFalse(host.cfg.menu_bar)
                host.shell.trigger('toolbar_text')
                self.assertEqual(host.cfg.toolbar, 'icons')
                host.shell.trigger('toolbar_text')
                self.assertEqual(host.cfg.toolbar, 'text')
                host.shell.trigger('focus_checks')
                pump(20)
                self.assertTrue(item(win, 'checks-list').hasActiveFocus())
                dialogs = host.parts.controllers['dialogs']
                dialogs.open('shortcuts')
                self.assertTrue(dialogs.assignShortcut('phase_plant', 'Ctrl+9'))
                self.assertTrue(dialogs.accept())
                key(app, win, Qt.Key.Key_9, modifiers=Qt.KeyboardModifier.ControlModifier)
                wait_for(lambda: win.property('phase') == 'plant', 5)   # r21-f6c: the phase changes a frame later
                self.assertEqual(win.property('phase'), 'plant')
                host.shell.trigger('phase_model')
                for phase in ('plant', 'production', 'consumption', 'economics', 'report', 'model'):
                    host.shell.trigger('phase_' + phase)
                    wait_for(lambda: win.property('phase') == phase, 5)
                    pump(50)
                    ready()
                    self.assertEqual(win.property('phase'), phase)
                self.assertTrue(first.isVisible())
                arrow = item(win, 'tool_tool_buildingArrow')
                mouse(app, win, QEvent.Type.MouseButtonPress, point(arrow), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
                pump(30)
                button = item(win, 'tool_tool_building')
                self.assertTrue(button.property('menuOpened'), 'The strip opens on press, not release')
                entry = item(win, 'phaseMenu_tool_building')
                self.assertEqual(entry.property('shortcutText'), 'B')
                self.assertIn('\n', entry.property('tip'))
                mouse(app, win, QEvent.Type.MouseButtonRelease, point(arrow), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
                button.dismissMenu()
                host.shell.trigger('browse_modules')
                self.assertTrue(host.parts.controllers['filePart'].catalogVisible)
                pump(40)
                ready()
                key(app, win, Qt.Key.Key_Escape)
                self.assertFalse(host.parts.controllers['filePart'].catalogVisible)
                session.select('subfield', session.project.subfields[0].id)
                host.shell.trigger('empty')
                self.assertFalse(session.project.subfields[0].filled)
                host.shell.trigger('undo')
                self.assertTrue(session.project.subfields[0].filled)
                host.shell.trigger('tool_building')
                self.assertEqual(host.plan.tool, 'building')
                host.shell.escape()
                self.assertEqual(host.plan.tool, 'select')
                host.shell.trigger('object_3d')
                pump(20)
                host.shell.trigger('about')
                pump(20)
                self.assertEqual(host.parts.controllers['dialogs'].kind, 'about')
                host.parts.controllers['filePart'].dismissDialog()
                host.shell.trigger('compare_variants')
                wait_for(lambda: not host.tasks.busy, seconds=60)
                self.assertEqual(len(host.tasks.rows), 15)
                item(win, 'shellCommandDialog').close()
                host.tasks.variantAction('new')
                pump(20)
                item(win, 'variantName').setProperty('text', 'Alternative')
                item(win, 'variantDialog').accept()
                self.assertEqual(len(session.project.variants), 2)
                host.tasks.commitVariant('rename', 'Renamed')
                self.assertEqual(session.project.current_variant()['name'], 'Renamed')
                host.tasks.commitVariant('delete', session.project.variants[0]['id'])
                self.assertEqual(len(session.project.variants), 1)
                win.setProperty('fileOpen', True)
                pump(300)
                self.assertTrue(win.property('fileShown'))
                wait_for(lambda: not item(win, 'fileTransition').property('running'), seconds=5)
                win.setProperty('fileOpen', False)
                wait_for(lambda: not win.property('fileShown') and not item(win, 'fileTransition').property('running'), seconds=5)
                self.assertFalse(win.property('fileShown'))
                self.assertEqual(host.warnings, [])
            finally:
                host.close()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                app.processEvents()
