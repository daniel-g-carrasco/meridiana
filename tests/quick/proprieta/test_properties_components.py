"""Reusable rows, sections and editable grids use the real Quick controls."""
import unittest

import _setup
from PySide6.QtCore import QObject, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana.quick.backend.controls import install_controls


class ComponentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_grid_totals_edit_signal_and_section(self):
        engine = QQmlApplicationEngine()
        install_controls(engine)
        warnings = []
        engine.warnings.connect(lambda messages: warnings.extend(str(m) for m in messages))
        engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Properties
import Meridiana.Controls as M
Window { visible: true; width: 500; height: 600
 Column { width: parent.width
  RowList { width: parent.width; rows: [["Short", "Long value"], ["B", "20"]] }
  FieldGrid { id: grid; objectName: "grid"; width: parent.width; rowNames: ["Jan", "Feb"]; columns: ["F1", "F2"]
    values: [{"F1": 12, "F2": 4}, {"F1": 8, "F2": 6}]; totalLabel: "Total"
    property int edits: 0; onEdited: edits += 1 }
  M.Section { objectName: "section"; width: parent.width; title: "Details"; density: "form"
    RowList { width: parent.width; rows: [["Value", "42"]] } }
 }
}''')
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        QTest.qWait(120)
        grid = window.findChild(QObject, 'grid')
        grid.editCell(1, 'F1', 10)
        self.assertEqual(grid.property('edits'), 1)
        self.assertEqual(grid.property('values').toVariant()[1]['F1'], 10)
        section = window.findChild(QObject, 'section')
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier,
                         section.mapToScene(section.boundingRect().topLeft()).toPoint() + __import__('PySide6.QtCore', fromlist=['QPoint']).QPoint(40, 15))
        self.assertTrue(section.property('collapsed'))
        self.assertFalse(warnings, warnings)
        window.close()
        from shiboken6 import delete
        delete(window)
        delete(engine)


if __name__ == '__main__':
    unittest.main()
