"""Native Quick input and R377 rendered-frame regression tests."""
import unittest
from pathlib import Path

import _setup
from _fixtures import capannone
from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana.quick.backend.properties import PropertiesBackend, install_properties
from meridiana.session import ProjectSession


class PropertiesQmlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.session = ProjectSession(capannone())
        self.session.select('building', self.session.project.buildings[0].id)
        self.backend = PropertiesBackend(self.session)
        self.engine = QQmlApplicationEngine()
        self.theme = install_properties(self.engine, self.backend)
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Properties
Window { visible: true; width: 380; height: 900
    PropertiesPage { objectName: "page"; anchors.fill: parent; backend: propertiesBackend }
}''')
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.page = self.window.findChild(QObject, 'page')
        QTest.qWait(150)

    def tearDown(self):
        from shiboken6 import delete
        if hasattr(self, 'window'):
            self.window.close()
            delete(self.window)
        delete(self.engine)
        self.backend.close()

    def editor(self, key):
        def find(item):
            if item.objectName() == 'editor:' + key:
                return item
            for child in item.childItems():
                found = find(child)
                if found is not None:
                    return found
            return None
        return find(self.window.contentItem())

    def click(self, item):
        point = item.mapToScene(item.boundingRect().center()).toPoint()
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)

    def type_into(self, item, text):
        self.click(item)
        QTest.keyClick(self.window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        for character in text:
            QTest.keyClick(self.window, character)

    def test_typing_confirms_once_and_esc_cancels(self):
        field = self.editor('height')
        self.assertIsNotNone(field)
        original = self.session.project.buildings[0].height
        self.type_into(field, '12')
        self.assertEqual(self.session.project.buildings[0].height, original)
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        self.assertEqual(self.session.project.buildings[0].height, 12)
        self.assertEqual(self.session.undo.count(), 1)
        self.type_into(field, '17')
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        self.assertEqual(self.session.project.buildings[0].height, 12)
        self.assertFalse(self.warnings, self.warnings)

    def test_selection_drops_draft_and_same_shape_keeps_editor(self):
        import copy
        other = copy.deepcopy(self.session.project.buildings[0])
        other.id, other.height = 'other', 20
        self.session.project.buildings.append(other)
        field = self.editor('height')
        self.type_into(field, '11')
        self.session.select('building', 'other')
        QTest.qWait(10)
        self.assertIs(self.editor('height'), field)
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        self.assertEqual(other.height, 20)
        self.assertEqual(self.session.undo.count(), 0)

    def test_r377_every_rendered_frame_contains_form_content(self):
        from quick.parity.realwindow import FrameRecorder, wait_frames
        with FrameRecorder(self.window) as recorder:
            for kind, oid in [('subfield', self.session.project.subfields[0].id), ('site', ''),
                              ('building', self.session.project.buildings[0].id)]:
                self.session.select(kind, oid)
                wait_frames(recorder, len(recorder.frames) + 12)
        recorder.assert_valid()
        frames = [frame.image for frame in recorder.frames]
        self.assertGreater(len(frames), 15)
        out = Path('build/quick-foto/proprieta')
        out.mkdir(parents=True, exist_ok=True)
        for n, frame in enumerate(frames):
            frame.save(str(out / f'properties-r377-frame-{n:03}.png'))
        # Every real frame must contain text/control ink, not merely a coloured card.
        for n, image in enumerate(frames):
            dpr = image.devicePixelRatio()
            dark = 0
            for y in range(int(24*dpr), min(image.height(), int(350*dpr)), max(1, int(dpr))):
                for x in range(int(20*dpr), min(image.width(), int(330*dpr)), max(1, int(dpr))):
                    if image.pixelColor(x, y).lightness() < 150:
                        dark += 1
            self.assertGreater(dark, 160, f'empty form frame {n}')
        frames[-1].save(str(out / 'properties-r377-last.png'))


if __name__ == '__main__':
    unittest.main()
