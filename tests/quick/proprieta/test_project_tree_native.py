"""Native D3D11 tree gestures and tree photos (R389, R30, R136). Once beside the Widgets' tree; only the Quick is
left (r30, phase B)."""
import copy
import os
import unittest

import _setup
from _fixtures import capannone_rho
from PySide6.QtCore import QObject, QPoint, QUrl, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import i18n
from meridiana.app import jobs
from meridiana.core.model import model
from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.project_tree import ProjectTreeBackend
from meridiana.app.session import ProjectSession
from quick.aiuti.realwindow import FrameRecorder, native_app


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1', 'Native GPU evidence is opt-in')
class ProjectTreeNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        native_app()

    def setUp(self):
        i18n.setup('it')
        project = model.Project.from_json(copy.deepcopy(capannone_rho().to_json()))
        self.backend = ProjectTreeBackend(ProjectSession(project))
        results, keys, _laid = jobs.layout_of(project)
        self.backend.session.layout_done(self.backend.session.generation, results, keys)
        self.addCleanup(self.backend.close)
        self.engine = QQmlApplicationEngine()
        self.theme = install_controls(self.engine)
        self.engine.rootContext().setContextProperty('treeBackend', self.backend)
        self.warnings = []
        self.engine.warnings.connect(lambda messages: self.warnings.extend(str(m) for m in messages))
        self.engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.ProjectTree
Window {
    flags: Qt.Window | Qt.FramelessWindowHint
    width: 1366; height: 900; visible: true
    color: Theme.colors.panel
    ProjectTreePage { id: page; objectName: "tree-page"; width: 320; height: parent.height; backend: treeBackend }
}''', QUrl('tree-native.qml'))
        self.assertTrue(self.engine.rootObjects(), self.warnings)
        self.window = self.engine.rootObjects()[0]
        self.addCleanup(self.window.close)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.window.isExposed()))
        QTest.qWait(100)

    def row(self, kind, oid):
        found = self.visual(f'tree-row-{kind}-{oid}')
        self.assertIsNotNone(found, (kind, oid))
        return found

    def visual(self, name):
        stack = [self.window.contentItem()]
        while stack:
            item = stack.pop()
            if item.objectName() == name:
                return item
            stack.extend(item.childItems())
        return None

    def click(self, obj, button=Qt.LeftButton):
        point = obj.mapToScene(obj.boundingRect().center())
        QTest.mouseClick(self.window, button, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
        self.app.processEvents()

    def test_native_click_keyboard_context_rename_and_photos(self):
        self.assertFalse(self.warnings, self.warnings)
        self.click(self.row('building', 'b1'))
        self.assertEqual(self.backend.session.selection, ('building', 'b1'))
        QTest.keyClick(self.window, Qt.Key_Down)
        self.assertEqual(self.backend.session.selection, ('subfield', 's1'))
        self.backend.session.select('row', 's1/r1')
        self.assertTrue(self.row('subfield', 's1').property('selected'))
        self.click(self.row('building', 'b1'), Qt.RightButton)
        menu = self.window.findChild(QObject, 'project-tree-context-menu')
        self.assertTrue(_setup.wait_until(self.app, lambda: menu.property('opened')))
        QTest.keyClick(self.window, Qt.Key_Escape)
        QTest.keyClick(self.window, Qt.Key_F2)
        editor = self.window.findChild(QObject, 'project-tree-name-editor')
        self.assertTrue(_setup.wait_until(self.app, lambda: editor.property('opened')))
        for character in 'Capannone nuovo':
            QTest.keyClick(self.window, character)
        QTest.keyClick(self.window, Qt.Key_Return)
        self.assertEqual(self.backend.session.project.buildings[0].name, 'Capannone nuovo')
        QTest.keyClick(self.window, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(self.backend.session.project.buildings[0].name, 'Capannone')
        self.assertIsNone(self.visual('tree-mark-site-'))           # R604: no marks of the checks in the tree
        self.backend.select('subfield', 's1')
        QTest.mouseMove(self.window, QPoint(900, 700))
        out = _setup.ROOT / 'build' / 'quick-foto' / 'proprieta'
        out.mkdir(parents=True, exist_ok=True)
        scale = os.environ.get('QT_SCALE_FACTOR', '1')
        for dark in (False, True):
            self.theme.configure({'theme': 'dark' if dark else 'light'})
            for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
                self.window.resize(width, height)
                with FrameRecorder(self.window, names=('tree-page',)) as frames:
                    self.window.update()
                    self.assertTrue(_setup.wait_until(self.app, lambda: bool(frames.frames)))
                self.assertFalse(frames.unexpected_windows)
                shot = self.window.grabWindow()
                self.assertFalse(shot.isNull())
                self.assertEqual((self.window.width(), self.window.height()), (width, height))
                self.assertEqual((shot.width(), shot.height()),
                                 (round(width * shot.devicePixelRatio()), round(height * shot.devicePixelRatio())))
                stem = f'tree-{"dark" if dark else "light"}-{width}x{height}-scale{scale}'
                shot.save(str(out / (stem + '.png')))
        page = self.window.findChild(QObject, 'tree-page')
        page.setProperty('showVariants', True)
        self.app.processEvents()
        self.click(self.visual('tree-new-variant'))
        for character in 'Nuova':
            QTest.keyClick(self.window, character)
        QTest.keyClick(self.window, Qt.Key_Return)
        self.assertEqual(len(self.backend.variants), 2)
        first, second = [v['id'] for v in self.backend.variants]
        self.click(self.visual('tree-variant-' + first))
        self.assertEqual(self.backend.session.project.variant, first)
        self.click(self.visual('tree-variant-delete-' + second))
        self.assertEqual(len(self.backend.variants), 1)
        self.theme.configure({'textSize': 'large'})
        page.setWidth(240)
        self.window.resize(1366, 900)
        QTest.mouseMove(self.window, QPoint(900, 700))
        self.window.update()
        QTest.qWait(100)
        self.window.grabWindow().save(str(out / f'tree-narrow-large-scale{scale}.png'))
        page.setProperty('showVariants', False)
        page.setHeight(220)
        def add_buildings(project):
            for index in range(30):
                building = copy.deepcopy(project.buildings[0])
                building.id = f'b{index + 100}'
                building.name = f'Edificio {index + 1}'
                project.buildings.append(building)
        self.backend.session.edit('Many buildings', add_buildings)
        self.backend.session.select('building', 'b129')
        self.app.processEvents()
        tree_list = self.visual('project-tree-list')
        before_scroll = tree_list.property('contentY')
        self.assertGreater(before_scroll, 300)
        self.backend.rename('building', 'b129', 'Rinominato')
        self.app.processEvents()
        self.assertEqual(tree_list.property('contentY'), before_scroll)
        self.backend.session.select('building', 'b1')
        self.app.processEvents()
        self.assertLess(tree_list.property('contentY'), 100)
        self.assertFalse(self.warnings, self.warnings)


setUpModule = _setup.keep_global_state
