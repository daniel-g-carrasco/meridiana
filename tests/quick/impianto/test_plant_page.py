"""R394/R395/R396: native Quick page, real keyboard and pointer events."""
import time
import unittest

import _setup  # noqa: F401  isolate the user's profile before loading Qt
from _fixtures import capannone, inverter_record
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

from meridiana import jobs
from meridiana.session import ProjectSession
from meridiana.quick.backend.plant import create_page, PAGE_URL


class PlantPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        p = capannone()
        p.energy = {'inverters': [{'record': inverter_record(), 'count': 1, 'name': ''}]}
        self.session = ProjectSession(p)
        self.session.results, self.session.layout_keys, _laid = jobs.layout_of(p)
        self.engine = QQmlEngine()
        self.backend = create_page(self.engine, self.session)
        self.warnings = []
        self.engine.warnings.connect(lambda warnings: self.warnings.extend(e.toString() for e in warnings))
        self.component = QQmlComponent(self.engine, PAGE_URL)
        self.assertFalse(self.component.isError(), [e.toString() for e in self.component.errors()])
        self.root = self.component.create()
        self.assertIsInstance(self.root, QQuickItem, [e.toString() for e in self.component.errors()])
        self.window = QQuickWindow()
        self.window.resize(1366, 900)
        self.root.setParentItem(self.window.contentItem())
        self.root.setWidth(1366)
        self.root.setHeight(900)
        self.window.show()
        QTest.qWaitForWindowExposed(self.window)
        self.addCleanup(self.cleanup)
        self.settle()

    def settle(self):
        deadline = time.monotonic() + 30
        while self.backend.busy and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        QTest.qWait(80)
        self.assertFalse(self.backend.busy)

    def cleanup(self):
        self.backend.close()
        self.window.close()
        delete(self.root)
        delete(self.window)
        delete(self.engine)
        self.assertEqual(self.warnings, [])

    def item(self, name):
        item = self.root.findChild(QQuickItem, name)
        if item is None:
            pending = [self.root]
            while pending:
                candidate = pending.pop()
                if candidate.objectName() == name:
                    item = candidate
                    break
                pending.extend(candidate.childItems())
        self.assertIsNotNone(item, name)
        return item

    def click(self, name):
        item = self.item(name)
        point = item.mapToScene(item.boundingRect().center())
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, pos=QPoint(round(point.x()), round(point.y())))
        QTest.qWait(30)

    def test_r394_empty_table_has_action_and_native_pixels(self):
        self.assertTrue(self.item('stringsEmpty').isVisible())
        self.assertFalse(self.window.grabWindow().isNull())
        requests = []
        self.backend.drawRequested.connect(lambda *args: requests.append(args))
        self.click('drawString')
        self.assertEqual(requests, [(1, 1, -1)])

    def test_r396_calculate_and_layout_are_commands_without_false_dot(self):
        events = []
        self.backend.calculateRequested.connect(lambda: events.append('calculate'))
        self.backend.layoutRequested.connect(lambda: events.append('layout'))
        self.click('calculate')
        self.click('layout')
        self.assertEqual(events, ['calculate', 'layout'])
        self.assertFalse(self.item('calculateDot').isVisible())
        self.assertFalse(self.item('layoutDot').isVisible())

    def test_string_selection_delete_undo_with_real_keyboard(self):
        keys = [f's1/{m.key}' for m in self.session.results['s1'].modules][:20]
        self.backend.commitString(1, 1, keys, -1)
        self.settle()
        self.click('viewTable')
        self.click('stringRow0')
        self.assertEqual(self.backend.selected, 0)
        QTest.keyClick(self.window, Qt.Key.Key_Delete)
        self.settle()
        self.assertEqual(self.backend.runs(), [])
        # Ctrl+Z belongs to the window's catalogue, not to this page (D08: test_native_correzioni.test_d08).
        self.backend.undo()
        self.settle()
        self.assertEqual(self.backend.runs()[0]['modules'], keys)

    def test_storage_and_proposal_stay_inside_single_window(self):
        before = len(self.app.topLevelWindows())
        self.click('storageTab')
        self.assertTrue(self.item('storagePanel').isVisible())
        self.click('stringsTab')
        self.click('proposalOptions')
        self.assertTrue(self.item('proposalPanel').isVisible())
        self.assertEqual(len(self.app.topLevelWindows()), before)
        QTest.keyClick(self.window, Qt.Key.Key_Escape)


if __name__ == '__main__':
    unittest.main()
