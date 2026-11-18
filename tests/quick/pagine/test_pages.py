"""R378/R392: native pages, actual Qt events and top-level window registry."""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtTest import QTest
from quick.parity.realwindow import FrameRecorder, native_app, wait_frames


class PagesNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = native_app()

    def setUp(self):
        from meridiana.quick.backend.files_page import build_page
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.host = build_page('file', folder=Path(self.tmp.name))
        self.addCleanup(self.host.close)
        self.window = self.host.window
        self.assertTrue(QTest.qWaitForWindowExposed(self.window))
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.window.grabWindow().isNull()))

    def click(self, name):
        from quick.parity.geometry import capture_quick
        items = capture_quick(self.window)['widgets']
        item = next(i for i in items if i['id'] == name)
        x, y, w, h = item['rect']
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(round(x + w / 2), round(y + h / 2)))

    def test_r378_right_only_and_r392_no_extra_window(self):
        with FrameRecorder(self.window, names=['fileNavigation', 'fileRight']) as recorder:
            wait_frames(recorder, 2)
            self.click('fileNav_save')
            self.assertTrue(_setup.wait_until(self.app, lambda: self.host.files.section == 'save'))
            QTest.qWait(260)
            self.window.update()
            wait_frames(recorder, len(recorder.frames) + 1)
        recorder.assert_valid(stable={'fileNavigation': 0, 'fileRight': 0},
                              regions={'navigation': (8, 8, 240, 400)})
        self.assertFalse(recorder.unexpected_windows)
        page = self.window.findChild(QObject, 'filePage')
        self.assertEqual('save', page.property('displayedSection'))
        self.assertEqual(1.0, self.window.findChild(QObject, 'fileRight').opacity())
        self.assertEqual([], self.host.warnings)
        if os.environ.get('MERIDIANA_QUICK_CAPTURE') == '1':
            recorder.save(str(_setup.ROOT / 'build/quick-foto/pagine/frames-file'))

    def test_opening_file_entrance_uses_only_host_window(self):
        page = self.window.findChild(QObject, 'filePage')
        with FrameRecorder(self.window, names=['fileNavigation', 'fileRight']) as recorder:
            page.enter()
            wait_frames(recorder, 3)
            QTest.qWait(220)
            self.window.update()
            wait_frames(recorder, len(recorder.frames) + 1)
        self.assertFalse(recorder.unexpected_windows)
        self.assertEqual(0.0, page.property('entranceOffset'))
        self.assertFalse(self.window.grabWindow().isNull())

    def test_settings_changes_right_only_and_reduced_motion_is_immediate(self):
        self.host.files.selectSection('preferences:appearance')
        page = self.window.findChild(QObject, 'filePage')
        self.assertTrue(_setup.wait_until(self.app, lambda: page.property('displayedSection') == 'preferences:appearance'
                                        and not page.property('changing')))
        with FrameRecorder(self.window, names=['fileNavigation', 'fileRight']) as recorder:
            self.click('fileNav_navigation')
            self.assertTrue(_setup.wait_until(self.app, lambda: page.property('displayedSection') == 'preferences:navigation'
                                            and not page.property('changing')))
            self.window.update()
            wait_frames(recorder, len(recorder.frames) + 1)
        recorder.assert_valid(stable={'fileNavigation': 0, 'fileRight': 0}, regions={'navigation': (8, 8, 240, 260)})
        self.host.settings.setValue('reduced_motion', True)
        self.click('fileNav_privacy')
        self.assertEqual('preferences:privacy', page.property('displayedSection'))
        self.assertFalse(page.property('changing'))
        self.assertEqual([], self.host.warnings)


if __name__ == '__main__':
    unittest.main()
