"""Native D3D11 tree gestures and Widgets/Quick tree photos (R389, R30, R136)."""
import copy
import os
from pathlib import Path
import tempfile
import unittest

import _setup
from _fixtures import capannone_rho
from PySide6.QtCore import QObject, QPoint, QUrl, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import config, i18n
from meridiana.paths import Paths
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.project_tree import ProjectTreeBackend
from meridiana.session import ProjectSession
from quick.parity.realwindow import FrameRecorder, native_app


@unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1', 'Native GPU evidence is opt-in')
class ProjectTreeNativeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        native_app()

    def setUp(self):
        i18n.setup('it')
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        folder = Path(temp.name)
        paths = Paths(**{k: folder / k for k in ('config', 'state', 'data', 'cache')})
        cfg = config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex', background='none')
        self.widgets = _setup.window(self, capannone_rho(), paths=paths, cfg=cfg)
        self.widgets.tree.setFixedWidth(320)
        self.backend = ProjectTreeBackend(ProjectSession(copy.deepcopy(self.widgets.project)))
        self.backend.set_checks(self.widgets.checks_page.items)
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

    def test_native_click_keyboard_context_rename_marks_and_photos(self):
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
        marks = []
        self.backend.checksRequested.connect(lambda *args: marks.append(args))
        mark = self.visual('tree-mark-site-')
        if mark.property('visible'):
            from meridiana.ui import status_pill
            from meridiana.ui.design import Text, text_font
            count = next(row['markCount'] for row in self.backend.rows if row['kind'] == 'site')
            font = text_font(Text.LABEL, self.widgets.tree.font())
            self.assertEqual(mark.width(), status_pill.size_hint(str(count), font, 24).width())
            self.click(mark)
            self.assertEqual(marks[-1][:2], ('site', ''))
        self.backend.select('subfield', 's1')
        self.widgets._select('subfield', 's1')
        QTest.mouseMove(self.window, QPoint(900, 700))
        import json
        geometry = []
        root_item = self.widgets.tree.topLevelItem(0)
        stack = [root_item]
        while stack:
            item = stack.pop(0)
            kind, oid = item.data(0, Qt.UserRole)
            rect = self.widgets.tree.visualItemRect(item)
            quick_row = self.row(kind, oid)
            geometry.append(dict(kind=kind, oid=oid, widgets=[rect.y(), rect.height()],
                                 quick=[quick_row.y(), quick_row.height()]))
            self.assertLessEqual(abs(rect.y() - quick_row.y()), 1, (kind, oid, geometry[-1]))
            self.assertLessEqual(abs(rect.height() - quick_row.height()), 1, (kind, oid, geometry[-1]))
            stack[0:0] = [item.child(i) for i in range(item.childCount())]
        out = _setup.ROOT / 'build' / 'quick-foto' / 'proprieta'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'tree-geometry.json').write_text(json.dumps(geometry, indent=2), encoding='utf-8')
        scale = os.environ.get('QT_SCALE_FACTOR', '1')
        for dark in (False, True):
            self.theme.configure({'theme': 'dark' if dark else 'light'})
            self.widgets.theme.cfg.theme = 'dark' if dark else 'light'
            self.widgets.theme.applied = None
            self.widgets.theme.apply()
            self.widgets._show_tree()
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
                quick = shot.copy(0, 0, round(320 * shot.devicePixelRatio()), shot.height())
                old_window = self.widgets.grab().toImage()
                origin = self.widgets.tree.mapTo(self.widgets, QPoint(0, 0))
                dpr = old_window.devicePixelRatio()
                old = old_window.copy(round(origin.x() * dpr), round(origin.y() * dpr),
                                      round(self.widgets.tree.width() * dpr), round(self.widgets.tree.height() * dpr))
                old_ground = old.pixelColor(round(100 * dpr), round(300 * dpr))
                new_ground = quick.pixelColor(round(100 * quick.devicePixelRatio()), round(300 * quick.devicePixelRatio()))
                self.assertEqual(old_ground.name(), new_ground.name())
                comparison = QImage(quick.width() + old.width(), max(quick.height(), old.height()), QImage.Format_ARGB32)
                comparison.fill(Qt.GlobalColor.white)
                painter = QPainter(comparison)
                old.setDevicePixelRatio(1); quick.setDevicePixelRatio(1)
                painter.drawImage(0, 0, old); painter.drawImage(old.width(), 0, quick); painter.end()
                comparison.save(str(out / (stem + '-widgets-quick.png')))
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
