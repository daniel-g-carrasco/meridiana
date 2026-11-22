"""Isolated QML scene for text command tests, never the desktop clipboard."""
import unittest

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

from meridiana.gui.backend.controls import install_controls


class TextScene(unittest.TestCase):
    def scene(self, kind, extra='', module='Controls'):
        self.app = _setup.quick_app()
        engine = QQmlEngine()
        install_controls(engine)
        component = QQmlComponent(engine)
        local = module.startswith('local:')
        imports = 'import QtQuick\n' + ('' if local else 'import Meridiana.' + module + ' as M\n')
        url = QUrl.fromLocalFile(str(_setup.ROOT / 'src/meridiana/gui/qml/Meridiana' / module[6:] / 'Fixture.qml')) if local else QUrl()
        component.setData((imports + ('' if local else 'M.') + kind + ' { width: 300; '
                           + ('' if kind in ('NumberField', 'Table', 'Formula', 'PedigreeFormula', 'Chart', 'MapNotice', 'BillsGrid') else 'text: "Alpha beta"; ')
                           + extra + ' }').encode(), url)
        self.assertFalse(component.isError(), str(component.errors()))
        root = component.create()
        self.assertIsNotNone(root, str(component.errors()))
        root.setParent(engine)
        window = QQuickWindow()
        window.resize(600, 500)
        root.setParentItem(window.contentItem())
        window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
        self.addCleanup(cleanup)
        return root, window

    def evaluate(self, root, code):
        expr = QQmlExpression(__import__('PySide6.QtQml', fromlist=['qmlContext']).qmlContext(root), root, code)
        result = expr.evaluate()
        self.assertFalse(expr.hasError(), expr.error().toString())
        return result[0] if isinstance(result, tuple) else result
