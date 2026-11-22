"""R655 (Daniel 15/11/2026, the thumb of the scroll bar in the cards' margin, variant 3 of his board): a bar standing in
a card's margin (M.ScrollBar.inMargin: M.PanelPage's, the Project tree's, the Checks') takes the pointer over the whole
margin, its thumb centred, ControlMetrics.marginThumb wide at rest and marginThumbHover under the pointer and while
dragged; every other bar keeps its lane (Theme.size.SCROLLBAR) and since r39 the same thumbs, as GNOME's (the kit).

    python -m unittest quick.controlli.test_cursore_margine_r655
"""
import os
import tempfile
import unittest

QML = '''
import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle { width: 720; height: 300; color: Theme.colors.panel
  M.PanelPage { objectName: "page"; x: 12; y: 12; width: 300; height: 276
    Repeater { model: 40; Rectangle { width: parent.width; height: 20; color: Theme.colors.field } } }
  ListView { id: list; objectName: "list"; x: 360; y: 12; width: 300; height: 276; clip: true; model: 80
    delegate: Rectangle { width: list.width - bar.room; height: 20; color: Theme.colors.field }
    C.ScrollBar.vertical: M.ScrollBar { id: bar; objectName: "listBar" } } }'''


def setUpModule():
    import _setup
    _setup.keep_global_state()


class ThumbInTheMargin(unittest.TestCase):
    def test_the_thumb_at_rest_under_the_pointer_and_dragged(self):
        import _setup
        from PySide6.QtCore import QEvent, QObject, QPointF, Qt, QUrl
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtQuick import QQuickView
        from meridiana.gui.backend.controls import install_controls
        from quick.gestures import pump
        app = _setup.qt_or_skip()
        view = QQuickView()
        install_controls(view.engine(), dict(theme='dark', reducedMotion=True))
        with tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False) as file:
            file.write(QML.encode())
        self.addCleanup(os.unlink, file.name)
        view.setSource(QUrl.fromLocalFile(file.name))
        self.assertIsNotNone(view.rootObject(), view.errors())
        view.show()
        pump(200)
        self.addCleanup(view.close)
        root = view.rootObject()
        page = root.findChild(QObject, 'page')
        bar = next(c for c in page.childItems() if 'ScrollBar' in c.metaObject().className())
        thumb = next(c for c in bar.childItems() if c.width() > 0)
        flick = page.property('contentItem')

        def mouse(kind, at, buttons):
            button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
            app.sendEvent(view, QMouseEvent(kind, at, at, QPointF(view.mapToGlobal(at.toPoint())), button, buttons,
                                            Qt.KeyboardModifier.NoModifier))
            pump(60)

        def placed():
            at = thumb.mapToItem(bar, QPointF(0, 0)).x()
            return round(at, 2), round(thumb.width(), 2), round(bar.width() - at - thumb.width(), 2)
        # the whole margin takes the pointer: from the page's right side to the card's (12)
        self.assertEqual(bar.width(), 13)   # R704: 12 of air and the card's line
        self.assertAlmostEqual(bar.mapToItem(page, QPointF(0, 0)).x(), flick.width(), delta=.01)
        self.assertEqual(placed(), (4, 4, 5), 'at rest: 4 wide, centred in the 12 of air')
        mouse(QEvent.Type.MouseMove, bar.mapToScene(QPointF(1, 40)), Qt.MouseButton.NoButton)     # the margin's edge
        self.assertTrue(bar.property('hovered'))
        self.assertEqual(placed(), (2, 8, 3), 'under the pointer: 8 wide as GNOME, centred')
        centre = thumb.mapToScene(QPointF(thumb.width() / 2, 10))
        mouse(QEvent.Type.MouseButtonPress, centre, Qt.MouseButton.LeftButton)
        mouse(QEvent.Type.MouseMove, centre + QPointF(0, 30), Qt.MouseButton.LeftButton)
        self.assertTrue(bar.property('pressed'))
        self.assertEqual(placed(), (2, 8, 3), 'dragged: 8 wide')
        self.assertGreater(flick.property('contentY'), 0, 'the drag moves the page')
        mouse(QEvent.Type.MouseButtonRelease, centre + QPointF(0, 30), Qt.MouseButton.NoButton)
        mouse(QEvent.Type.MouseMove, QPointF(200, 150), Qt.MouseButton.NoButton)
        self.assertEqual(placed(), (4, 4, 5), 'back at rest')
        # any other bar as before: its lane and its thumb
        other = root.findChild(QObject, 'listBar')
        other_thumb = next(c for c in other.childItems() if c.width() > 0)
        self.assertEqual((other.width(), other_thumb.width()), (10, 4))   # every bar as GNOME's: thin at rest


if __name__ == '__main__':
    unittest.main()
