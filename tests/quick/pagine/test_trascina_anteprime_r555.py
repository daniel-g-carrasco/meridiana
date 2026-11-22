"""R555 (Daniel 13/11/2026: «manipolare la vista la ridisegna di continuo durante il movimento»): the previews of the
canopy and of the building from a template, turned with a drag, as the windows show them (GeometryPreview.qml). The
faces of the scene are made once per change of the form, never by the drag; the pointer passing over the drawing
without reaching a measure draws nothing; a step of the drag draws one frame, and that frame costs little more than
its painting. Before: 29 frames for 30 moves of the pointer that changed nothing, and a frame of the canopy's drag
cost 15,7 ms for 3,2 ms of painting (the frame went through a PNG, written, put in base64 and read back)."""
import time
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

import _setup
from meridiana.app.session import ProjectSession
from meridiana.gui.backend import dialogs_preview
from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.dialogs import DialogsBackend
from quick.gestures import pump

setUpModule = _setup.keep_global_state
ROOT = Path(__file__).resolve().parents[3]
PREVIEW = ROOT / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana' / 'Dialogs' / 'GeometryPreview.qml'


class Counted:
    """Counts the calls of a function of a module or a class, and the time they take."""

    def __init__(self, test, owner, name):
        self.calls, self.spent = 0, 0.
        original = getattr(owner, name)

        def wrapper(*args, **kwargs):
            self.calls += 1
            start = time.perf_counter()
            try:
                return original(*args, **kwargs)
            finally:
                self.spent += time.perf_counter() - start
        setattr(owner, name, wrapper)
        test.addCleanup(setattr, owner, name, original)

    def reset(self):
        self.calls, self.spent = 0, 0.


class TheDragTurnsTheViewOnly(unittest.TestCase):
    def setUp(self):
        _setup.qt_or_skip()
        dialogs_preview.register()
        self.backend = DialogsBackend(ProjectSession())
        self.addCleanup(self.backend.close)
        self.view = QQuickView()
        self.addCleanup(self.view.close)
        install_controls(self.view.engine(), dict(theme='light', reducedMotion=True))
        self.view.resize(520, 380)
        component = QQmlComponent(self.view.engine(), QUrl.fromLocalFile(str(PREVIEW)))
        self.root = component.createWithInitialProperties({'backend': self.backend})
        self.assertIsNotNone(self.root, component.errorString())
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.setContent(QUrl(), component, self.root)
        self.view.show()
        self.drawing = next(c for c in self.root.childItems() if c.metaObject().className().startswith('DialogPreview'))
        self.frames = 0
        self.drawing.sourceChanged.connect(self.count)

    def count(self):
        self.frames += 1

    def test_a_drag_projects_the_same_faces_again_and_a_pass_of_the_pointer_draws_nothing(self):
        for kind, scene in (('canopy', 'canopy_scene'), ('template', 'template_scene')):
            with self.subTest(kind=kind):
                rebuilt = Counted(self, dialogs_preview, scene)
                painted = Counted(self, dialogs_preview.DialogPreview, 'paint')
                framed = Counted(self, dialogs_preview.DialogPreview, '_render_image')
                self.backend.open(kind)
                pump(300)
                self.assertTrue(self.drawing.property('source'), 'the preview shows a frame')
                # the pointer over the middle of the drawing, where there is no measure: nothing to draw again
                centre = QPoint(260, 170)
                QTest.mouseMove(self.view, centre)
                pump(50)
                self.frames = 0
                for i in range(30):
                    QTest.mouseMove(self.view, centre + QPoint(i % 3, 0))
                    pump(5)
                self.assertEqual(self.frames, 0, f'{kind}: frames drawn while nothing changed')
                rebuilt.reset(), painted.reset(), framed.reset()
                self.frames = 0
                start = self.drawing.azimuth
                QTest.mousePress(self.view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
                for i in range(1, 21):
                    QTest.mouseMove(self.view, centre + QPoint(4 * i, i))
                    pump(10)
                QTest.mouseRelease(self.view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                                   centre + QPoint(80, 20))
                pump(100)
                self.assertNotEqual(self.drawing.azimuth, start, f'{kind}: the drag turned the view')
                self.assertEqual(rebuilt.calls, 0, f'{kind}: the scene\'s faces made again by a drag')
                self.assertGreaterEqual(self.frames, 10, f'{kind}: the drawing follows the drag')
                self.assertLessEqual(self.frames, 21, f'{kind}: more than a frame a step')
                # a frame is its painting and little else (the PNG of before was three times the painting)
                self.assertLess(framed.spent, 2 * painted.spent,
                                f'{kind}: {1000 * framed.spent / framed.calls:.1f} ms a frame, '
                                f'{1000 * painted.spent / painted.calls:.1f} ms of it painting')


if __name__ == '__main__':
    unittest.main()
