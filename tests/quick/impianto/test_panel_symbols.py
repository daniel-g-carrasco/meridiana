"""The shared icon is rasterized and placed on whole device pixels."""
import unittest

import _setup
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
from meridiana.gui.backend.controls import install_controls
from quick.gestures import pump

setUpModule = _setup.keep_global_state


class Symbols(unittest.TestCase):
    def test_fractional_layout_does_not_resample_the_icon(self):
        _setup.qt_or_skip()
        engine = QQmlEngine()
        install_controls(engine)
        component = QQmlComponent(engine)
        component.setData(b'''import QtQuick
import Meridiana.Controls as M
Item { width: 100; height: 100
    M.Icon { x: 10.25; y: 11.5; width: 14.4; height: 14.4; name: "symbol:ok" }
    M.ColorSwatch { x: 30.5; y: 40.25; width: 11; height: 11; color: "red" }
}''', QUrl())
        root = component.create()
        self.assertIsNotNone(root, [e.toString() for e in component.errors()])
        window = QQuickWindow()
        root.setParentItem(window.contentItem())
        window.resize(100, 100)
        window.show()
        try:
            pump(100)
            icon = root.childItems()[0]
            drawing = icon.childItems()[0]
            ratio = window.devicePixelRatio()
            position = drawing.mapToScene(QPointF(0, 0))
            for value in (position.x()*ratio, position.y()*ratio,
                          drawing.width()*ratio, drawing.height()*ratio):
                self.assertAlmostEqual(value, round(value), places=5)
            # The requested logical size must cover exactly the displayed drawing.
            size = drawing.property('sourceSize')
            self.assertEqual(size.width(), round(drawing.width()))
            self.assertEqual(size.height(), round(drawing.height()))
            self.assertFalse(window.grabWindow().isNull())
            provider = engine._meridiana_icons
            requested = list(provider._rendered)
            self.assertTrue(any(key[1:] == (round(drawing.width()*ratio), round(drawing.height()*ratio))
                                for key in requested), requested)
            self.assertFalse(drawing.property('smooth'))
            for name in ('plus', 'ellipsis', 'control:grip', 'sign:check'):
                icon.setProperty('name', name)
                pump(20)
                self.assertTrue(any(key[0].startswith(name+'/') for key in provider._rendered), name)
                if name == 'control:grip':
                    raster = next(image for key, (image, _) in provider._rendered.items()
                                  if key[0].startswith('control:grip/'))
                    self.assertEqual(max(raster.pixelColor(x, y).alpha() for x in range(raster.width())
                                         for y in range(raster.height())), 255, 'Grip dots must keep opaque centres')
            swatch = root.childItems()[1].childItems()[0]
            position = swatch.mapToScene(QPointF(0, 0))
            stroke, _ = QQmlExpression(engine.rootContext(), swatch, 'border.width').evaluate()
            for value in (position.x()*ratio, position.y()*ratio, swatch.width()*ratio,
                          swatch.height()*ratio, stroke*ratio):
                self.assertAlmostEqual(value, round(value), places=5)
        finally:
            window.close()
            root.setParentItem(None)
            from shiboken6 import delete
            delete(root)
            delete(window)
            delete(engine)
