"""Numeric clipboard policy, shared by every numeric editor."""
import unittest
import _setup
from meridiana.gui.backend.text_editing import TextEditing

class NumericPaste(unittest.TestCase):
    def setUp(self):
        self.app = _setup.quick_app()
        self.service = TextEditing()

    def test_decimal_suffix_and_quantity(self):
        for raw, unit, kind, value in [('1e1', 'kWh', '', '10'), ('12,5', 'kWh', '', '12.5'), ('12.5 kWh', 'kWh', '', '12.5'),
                                       ('150 cm', 'm', 'length', '1.5'), ('2 m + 30 cm', 'm', 'length', '2.3'),
                                       ('\u22122,5\u00a0\u00b0C', '\u00b0C', '', '-2.5')]:
            with self.subTest(raw=raw):
                result = self.service.numeric(raw, unit, kind, -100, 100, 3)
                self.assertTrue(result['ok'], result)
                self.assertEqual(result['text'], value)

    def test_rejected_without_guessing(self):
        for raw in ['1.500', '1.300,5', 'NaN', 'inf', '2\n3', '10 kg', '101', '1 + 2', '12.555', '1.500e1']:
            with self.subTest(raw=raw):
                self.assertFalse(self.service.numeric(raw, 'kWh', '', -100, 100, 2)['ok'])


class PropertyDraft(unittest.TestCase):
    def test_menu_preserves_draft_until_real_exit(self):
        from _fixtures import capannone
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression, qmlContext
        from PySide6.QtTest import QTest
        from shiboken6 import delete
        from meridiana.app.session import ProjectSession
        from meridiana.gui.backend.properties import PropertiesBackend, install_properties
        app = _setup.quick_app()
        session = ProjectSession(capannone())
        building = session.project.buildings[0]
        session.select('building', building.id)
        backend = PropertiesBackend(session)
        self.addCleanup(backend.close)
        engine = QQmlApplicationEngine()
        install_properties(engine, backend)
        engine.loadData(b"""import QtQuick
import QtQuick.Window
import Meridiana.Properties
import Meridiana.Controls as M
Window { visible: true; width: 500; height: 800
 PropertiesPage { anchors.fill: parent; backend: propertiesBackend }
 M.TextField { objectName: "outside"; x:400; y:700; width:80 }
}""")
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        self.addCleanup(delete, engine)
        self.addCleanup(window.close)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        def find():
            pending = [window.contentItem()]
            while pending:
                item = pending.pop()
                if item.objectName() == 'editor:name': return item
                pending.extend(item.childItems())
        self.assertTrue(_setup.wait_for(lambda: find() is not None, 1000))
        QTest.qWait(150)
        field = find()
        field.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
        for char in 'Synthetic name':
            QTest.keyClick(window, char)
        self.assertEqual(field.property("text"), "Synthetic name", str((field.isVisible(), field.hasActiveFocus(), field.property("dirty"))))
        previous = building.name
        point = field.mapToScene(field.boundingRect().center()).toPoint()
        QTest.mousePress(window, Qt.RightButton, pos=QPoint(point))
        QTest.mouseRelease(window, Qt.RightButton, pos=QPoint(point))
        self.assertEqual(building.name, previous)
        self.assertEqual(field.property('text'), 'Synthetic name')
        expression = QQmlExpression(qmlContext(field), field, 'textActions.menuActive')
        self.assertTrue(expression.evaluate()[0])
        QTest.keyClick(window, Qt.Key_Down)
        self.assertEqual(session.project.buildings[0].name, previous)
        QTest.keyClick(window, Qt.Key_Escape)
        self.assertTrue(_setup.wait_for(lambda: field.hasActiveFocus(), 500))
        self.assertEqual(field.property('text'), 'Synthetic name')
        self.assertEqual(building.name, previous)
        from PySide6.QtCore import QObject
        window.findChild(QObject, "outside").forceActiveFocus()
        app.processEvents()
        self.assertEqual(session.project.buildings[0].name, 'Synthetic name')
