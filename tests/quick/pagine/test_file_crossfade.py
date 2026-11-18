"""R471, R378: in File and in the Settings a new section crosses the old one, frame by frame (offscreen)."""
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


class CrossFadeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.quick.backend.files_page import build_page
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.host = build_page('file', folder=Path(self.tmp.name))
        self.addCleanup(self.host.close)
        self.window = self.host.window
        self.window.show()
        QTest.qWait(300)

    def test_r471_the_old_page_fades_out_as_the_new_one_fades_in(self):
        right = self.window.findChild(QObject, 'fileRight')
        leaving = self.window.findChild(QObject, 'fileLeaving')
        page = self.window.findChild(QObject, 'filePage')
        frames = []

        def frame():
            frames.append((time.perf_counter(), right.opacity(), leaving.opacity() if leaving else 0.0,
                           bool(leaving and leaving.isVisible())))
        self.window.frameSwapped.connect(frame, Qt.ConnectionType.DirectConnection)
        self.addCleanup(self.window.frameSwapped.disconnect, frame)
        for section in ('save', 'preferences:appearance', 'preferences:navigation', 'open'):
            frames.clear()
            self.host.files.selectSection(section)
            self.assertTrue(_setup.wait_until(self.app, lambda s=section: page.property('displayedSection') == s
                                              and not page.property('changing') and right.opacity() == 1))
            QTest.qWait(50)
            moving = [f for f in frames if f[1] < 1 or f[3]]
            # on r17-unita: no picture of the old page, the new one dipped to opacity 0 in the middle
            self.assertIsNotNone(leaving, 'the old page is kept as a picture while the new one comes')
            self.assertGreaterEqual(len(moving), 4, f'{section}: a cross-fade, not a jump ({len(moving)} frames)')
            self.assertGreaterEqual(min(f[1] + f[2] for f in moving), .85, f'{section}: it dipped to the ground')
            still = sum(1 for a, b in zip(moving, moving[1:], strict=False) if (a[1], a[2]) == (b[1], b[2]))
            self.assertLessEqual(still, 1, f'{section}: {still} frames stood still')
            span = moving[-1][0] - moving[0][0]
            self.assertLess(span, .45, f'{section}: {span:.2f} s, a long movement')
            self.assertFalse(leaving.isVisible(), 'the picture goes once the new page is in')
