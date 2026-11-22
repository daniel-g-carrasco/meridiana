"""R654 (Daniel 15/11/2026: «quando ho il puntatore sopra la barra di scorrimento e questa va in hover, non posso
muoverla facendo scrolling con due dita»): the wheel and the touchpad over a scroll bar (M.ScrollBar), its thumb or its
lane, scroll the list the bar belongs to as much as over the list itself: a panel's page (the bar in the card's margin,
outside the page), a list with its bar inside it, a list with its bar moved into the card's margin as the Project
tree's and the Checks' (R637).

    python -m unittest quick.controlli.test_rotella_barra_r654
"""
import os
import tempfile
import unittest

QML = '''
import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle { width: 740; height: 300; color: Theme.colors.panel
  M.PanelPage { objectName: "page"; x: 12; y: 12; width: 300; height: 276
    Repeater { model: 40; Rectangle { width: parent.width; height: 20; color: index % 2 ? Theme.colors.text : Theme.colors.field } } }
  ListView { id: list; objectName: "list"; x: 360; y: 12; width: 300; height: 276; clip: true; model: 80
    delegate: Rectangle { width: list.width - bar.room; height: 20; color: index % 2 ? Theme.colors.text : Theme.colors.field }
    C.ScrollBar.vertical: M.ScrollBar { id: bar; objectName: "listBar" } }
  // as the Project tree and the Checks (R637): the bar moved out of its list, into the card's margin at its right
  ListView { id: tree; objectName: "tree"; x: 680; y: 12; width: 28; height: 276; clip: true; model: 80
    delegate: Rectangle { width: tree.width; height: 20; color: index % 2 ? Theme.colors.text : Theme.colors.field }
    C.ScrollBar.vertical: M.ScrollBar { objectName: "treeBar"; parent: tree.parent; flickable: tree
      inMargin: true; x: tree.x + tree.width; y: tree.y; height: tree.height } } }'''


def setUpModule():
    import _setup
    _setup.keep_global_state()


class OverTheBar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import _setup
        cls.app = _setup.qt_or_skip()

    def wheel(self, window, point, angle=-120, pixels=0):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QWheelEvent
        from quick.gestures import pump
        self.app.sendEvent(window, QWheelEvent(point, window.mapToGlobal(point), QPoint(0, pixels), QPoint(0, angle),
                                               Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                               Qt.ScrollPhase.NoScrollPhase, False))
        pump(400)

    def scrolled(self, window, view, point, **kw):
        from quick.gestures import pump
        view.setProperty('contentY', 0)
        pump(50)
        self.wheel(window, point, **kw)
        return view.property('contentY')

    def test_a_page_and_a_list_scroll_from_their_bars_as_from_their_content(self):
        from PySide6.QtCore import QObject, QPointF, QUrl
        from PySide6.QtQuick import QQuickView
        from meridiana.gui.backend.controls import install_controls
        from quick.gestures import pump
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
        flick = page.property('contentItem')
        lst = root.findChild(QObject, 'list')
        tree = root.findChild(QObject, 'tree')
        bars = {'page': next(c for c in page.childItems() if 'ScrollBar' in c.metaObject().className()),
                'list': root.findChild(QObject, 'listBar'), 'tree': root.findChild(QObject, 'treeBar')}
        for name, scrolled, content in (('page', flick, QPointF(100, 100)), ('list', lst, QPointF(400, 100)),
                                        ('tree', tree, QPointF(690, 100))):
            bar = bars[name]
            thumb = bar.mapToScene(QPointF(bar.width() / 2, bar.property('topPadding') + 4))
            lane = bar.mapToScene(QPointF(bar.width() / 2, bar.height() - 20))      # where the thumb is not
            with self.subTest(name):
                on_content = self.scrolled(view, scrolled, content)
                self.assertGreater(on_content, 0)
                self.assertAlmostEqual(self.scrolled(view, scrolled, thumb), on_content, delta=1, msg='a notch over the thumb')
                self.assertAlmostEqual(self.scrolled(view, scrolled, lane), on_content, delta=1, msg='a notch over the lane')
                self.assertAlmostEqual(self.scrolled(view, scrolled, thumb, angle=-30, pixels=-25), 25, delta=.5,
                                       msg="the touchpad's pixels at once")
                # at the top a notch upwards moves nothing and the rebound answers once
                scrolled.setProperty('contentY', 0)
                pump(50)
                self.wheel(view, thumb, angle=120)
                self.assertEqual(scrolled.property('contentY'), 0)


if __name__ == '__main__':
    unittest.main()
