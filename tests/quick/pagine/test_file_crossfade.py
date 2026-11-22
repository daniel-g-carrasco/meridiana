"""R471, R378, R630: in File and in the Settings a new section crosses the old one, frame by frame (offscreen).

Since R630 the two pages are both alive (each section's page is made once and kept): the one that goes fades out while
the one asked for fades in, no picture of the old one (grabToImage, a frame on the graphics card read back) any more."""
import os
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QObject, Qt
from PySide6.QtTest import QTest

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def pages(right):
    """The kept pages of the right side (one Loader each)."""
    return [item for item in right.childItems() if item.metaObject().className().startswith('QQuickLoader')]


class CrossFadeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.gui.backend.files_page import build_page
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.host = build_page('file', folder=Path(self.tmp.name))
        self.addCleanup(self.host.close)
        self.window = self.host.window
        self.window.show()
        QTest.qWait(300)

    def test_r471_the_old_page_fades_out_as_the_new_one_fades_in(self):
        right = self.window.findChild(QObject, 'fileRight')
        page = self.window.findChild(QObject, 'filePage')
        frames = []

        def frame():
            shown = sorted((p.opacity() for p in pages(right) if p.isVisible()), reverse=True)
            frames.append((time.perf_counter(), page.property('arrival'), shown))
        self.window.frameSwapped.connect(frame, Qt.ConnectionType.DirectConnection)
        self.addCleanup(self.window.frameSwapped.disconnect, frame)
        for section in ('save', 'preferences:appearance', 'preferences:navigation', 'open'):
            frames.clear()
            self.host.files.selectSection(section)
            self.assertTrue(_setup.wait_until(self.app, lambda s=section: page.property('displayedSection') == s
                                              and not page.property('changing') and page.property('arrival') == 1))
            QTest.qWait(50)
            moving = [f for f in frames if f[1] < 1 or len(f[2]) > 1]
            # on r17-unita the new page dipped to opacity 0 in the middle; on r34-unita the old one was a picture
            self.assertGreaterEqual(len(moving), 4, f'{section}: a cross-fade, not a jump ({len(moving)} frames)')
            self.assertTrue(any(len(f[2]) == 2 for f in moving), f'{section}: the old page is there while the new comes')
            self.assertGreaterEqual(min(sum(f[2]) for f in moving), .85, f'{section}: it dipped to the ground')
            still = sum(1 for a, b in zip(moving, moving[1:], strict=False) if (a[1], a[2]) == (b[1], b[2]))
            self.assertLessEqual(still, 1, f'{section}: {still} frames stood still')
            span = moving[-1][0] - moving[0][0]
            self.assertLess(span, .45, f'{section}: {span:.2f} s, a long movement')
            self.assertEqual(1, sum(1 for p in pages(right) if p.isVisible()), 'the old page goes once the new is in')

    def test_r630_reduced_motion_changes_at_once(self):
        page = self.window.findChild(QObject, 'filePage')
        right = self.window.findChild(QObject, 'fileRight')
        self.host.theme.configure({'reduced_motion': True})
        self.addCleanup(self.host.theme.configure, {'reduced_motion': False})
        self.host.files.selectSection('export')
        # at once: the page asked for is in, the other gone, before any frame
        self.assertEqual('export', page.property('displayedSection'))
        self.assertEqual(1, page.property('arrival'))
        self.assertFalse(page.property('changing'))
        self.assertEqual(1, sum(1 for p in pages(right) if p.isVisible()))


if __name__ == '__main__':
    unittest.main()
