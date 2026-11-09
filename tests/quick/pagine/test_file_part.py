"""File, report and dialogs must act on the workbench session, R389/R392."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QThreadPool, QTimer, Qt
from PySide6.QtTest import QTest

from meridiana.model import Project
from quick.parity.realwindow import native_app


def wait_frame(milliseconds):
    """Run the actual event loop: QTest.qWait stalls this threaded native scene."""
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


class FilePartTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana.quick.app import create_app
        create_app()
        cls.app = native_app()

    def setUp(self):
        from meridiana.quick.app import QuickWindow
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.host = QuickWindow(Project(), Path(self.temp.name), real_views=True)
        self.addCleanup(self.close_host)
        self.host.window.show()
        wait_frame(100)

    def close_host(self):
        self.host.close()
        QThreadPool.globalInstance().waitForDone(10000)
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_registered_pages_share_session_and_real_commands(self):
        self.assertIn('files', self.host.parts.controllers)
        files = self.host.parts.controllers['files']
        report = self.host.parts.controllers['report']
        self.assertIs(files.session, self.host.bridge.session)
        self.assertIs(report.session, files.session)
        for command in ('new', 'open', 'save', 'save_as', 'save_revision', 'preferences',
                        'import_ifc', 'import_pvsyst', 'shortcuts', 'check_updates', 'report_profile',
                        'carport', 'canopy_layout', 'building_template', 'export_report'):
            self.assertTrue(self.host.shell.available(command), command)
        self.host.shell.trigger('report_profile')
        self.assertTrue(self.host.window.property('fileOpen'))
        self.assertEqual('preferences:report', files.section)
        wait_frame(250)
        from quick.pagine.test_fidelity import find_item
        self.assertIsNotNone(find_item(self.host.window.contentItem(), 'fileNavigation'))
        settings = self.host.parts.controllers['settings']
        self.assertEqual('plex', settings.cfg.font)
        self.assertEqual('indigo', settings.cfg.accent)
        settings.setValue('toolbar_place', 'left')
        self.assertEqual('left', self.host.window.property('toolbarPosition'))
        settings.undoLast()
        self.assertEqual('top', self.host.window.property('toolbarPosition'))
        settings.setShortcut('save', ['Ctrl+Shift+9'])
        self.assertEqual(['Ctrl+Shift+9'], next(c['keys'] for c in self.host.shell.keyCommands if c['id'] == 'save'))
        settings.undoLast()
        self.assertEqual(['Ctrl+S'], next(c['keys'] for c in self.host.shell.keyCommands if c['id'] == 'save'))
        QTest.keyClick(self.host.window, Qt.Key.Key_Escape)
        self.assertFalse(self.host.window.property('fileOpen'))
        self.host.window.showPhase('report')
        wait_frame(150)
        self.assertIsNotNone(find_item(self.host.window.contentItem(), 'reportTemplate'))
        report.setSetting('client', 'Client from Quick')
        self.assertEqual('Client from Quick', files.session.project.report['client'])
        files.session.undo.undo()
        self.assertNotEqual('Client from Quick', files.session.project.report.get('client'))

    def test_dialog_cancel_stays_in_window_and_keeps_project(self):
        self.assertIn('dialogs', self.host.parts.controllers)
        before = self.host.bridge.session.state_key()
        windows = set(self.app.topLevelWindows())
        self.host.shell.trigger('shortcuts')
        wait_frame(80)
        self.assertEqual('shortcuts', self.host.parts.controllers['dialogs'].kind)
        self.assertEqual(windows, set(self.app.topLevelWindows()))
        QTest.keyClick(self.host.window, Qt.Key.Key_Escape)
        wait_frame(30)
        self.assertEqual(before, self.host.bridge.session.state_key())
        self.assertFalse(self.host.parts.controllers['filePart'].dialogVisible)
        self.assertFalse(self.host.warnings, self.host.warnings)

    def test_dialogs_are_rendered_in_real_window_and_placement_is_undoable(self):
        part = self.host.parts.controllers['filePart']
        before = self.host.bridge.session.state_key()
        folder = Path('build/quick-foto/r13-file/dialogs')
        folder.mkdir(parents=True, exist_ok=True)
        for kind in ('template', 'canopy', 'canopy-layout', 'site', 'ifc', 'pvsyst', 'shortcuts', 'update', 'about', 'report_bug'):
            part.openDialog(kind)
            wait_frame(120)
            self.assertTrue(part.dialogVisible, kind)
            self.assertTrue(self.host.window.grabWindow().save(str(folder / (kind + '.png'))))
            QTest.keyClick(self.host.window, Qt.Key.Key_Escape)
            wait_frame(20)
            self.assertFalse(part.dialogVisible, kind)
            self.assertEqual(before, self.host.bridge.session.state_key(), kind)
        part.openDialog('template')
        self.assertTrue(part.dialogs.accept())
        self.assertFalse(part.dialogVisible)
        self.host.plan.pointsPicked.emit('file-template', [(10., 20.)])
        self.assertEqual(1, len(self.host.bridge.session.project.buildings))
        self.host.bridge.session.undo.undo()
        self.assertEqual(0, len(self.host.bridge.session.project.buildings))
        self.assertFalse(self.host.warnings, self.host.warnings)


if __name__ == '__main__':
    unittest.main()
