"""Cached inspectors retain their fields and regain the viewport on activation."""
import unittest

import _setup
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # noqa: F401
from meridiana.quick.backend.parts import QML
from quick.gestures import pump


setUpModule = _setup.keep_global_state


class InactiveInspectorTest(unittest.TestCase):
    def test_hidden_geometry_stays_put_and_original_binding_returns(self):
        app = _setup.qt_or_skip()
        engine = QQmlApplicationEngine()
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        engine.addImportPath(str(QML.parent))
        engine.loadData(b'''import QtQuick
import Meridiana.Charts
Window { width: 900; height: 600; visible: true
 Item { id: box; objectName: "box"; width: 370; height: 500
  Loader { id: pane; objectName: "pane"; anchors.fill: parent
   sourceComponent: Rectangle { property string draft: "retained" }
  }
 }
 InactiveInspector { panel: pane }
}''', QUrl.fromLocalFile(str(QML / 'Charts/inactive-test.qml')))
        pump(200)
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        try:
            box = window.findChild(QObject, 'box')
            pane = window.findChild(QObject, 'pane')
            pump(80)
            pane.setVisible(False)
            box.setWidth(510)
            pump(30)
            self.assertEqual(pane.width(), 370)
            pane.setVisible(True)
            pump(30)
            self.assertEqual(pane.width(), 510)
            self.assertEqual(pane.property('item').property('draft'), 'retained')
        finally:
            window.close()
            engine.deleteLater()
            app.processEvents()
