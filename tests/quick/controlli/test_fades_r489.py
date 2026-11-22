"""R489: the veils at the edges of Meridio's conversation (and of any area that scrolls with the bar's veils).

Daniel (06/11/2026, photo meridio-messaggi.png): «le velature non vengono come dovrebbero, sono buggate»: over the
conversation's white a grey band stood at the top, behind «Tu». The conversation is a ScrollView whose ground is its
own background (Theme.colors.view) inside a card of another colour, with a padding of 7 px and the bar outside the
list. The veils are measured here on a copy of that structure: they take the colour of the ground they lie on, they
cover only the edges (the list's top and bottom band, the padding above and below it included, never the border or
the bar), and they come in with the scrolling, without a jump.

R624 (Daniel 15/11/2026: «la sfumatura deve essere una trasparenza gradiente del contenuto», «mantenerla ben
centralizzata») took the veils away: the soft ends are the content's own transparency (Controls/EdgeFades.qml, a
shader), drawn and judged in quick.controlli.test_dissolvenza_r624. What stays true here, with Qt's software renderer
(offscreen, where no shader is drawn): the bar paints no band of colour over the edges any more, the content is whole.
"""
import os
import unittest

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView

from meridiana.gui.backend.controls import install_controls
from quick.gestures import pump

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = b'''
import QtQuick
import QtQuick.Controls
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 320; height: 260; color: "#d0c8b0"          // the card around: another colour than the list's ground
    property alias flick: scroll.contentItem
    ScrollView {
        id: scroll
        objectName: "scroll"
        x: 20; y: 20; width: 280; height: 220
        clip: true; contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical: M.ScrollBar { parent: scroll; x: parent.width-width; y: 7; height: parent.height-14
            orientation: Qt.Vertical; policy: ScrollBar.AlwaysOn }
        padding: 7; rightPadding: 7+Theme.size.SCROLLBAR
        background: Rectangle { color: "#ffffff"; radius: 6; border.color: "#888888" }
        Column {
            width: scroll.availableWidth
            Repeater { model: 30
                Rectangle { width: parent.width; height: 20; color: "#202020" } }
        }
    }
}
'''


def setUpModule():
    _setup.keep_global_state()


class ConversationVeils(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.view = QQuickView()
        install_controls(cls.view.engine(), dict(theme='light', reducedMotion=True))
        import tempfile
        cls.file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
        cls.file.write(QML)
        cls.file.close()
        cls.view.setSource(QUrl.fromLocalFile(cls.file.name))
        assert cls.view.rootObject() is not None, cls.view.errors()
        cls.view.show()
        pump(300)

    @classmethod
    def tearDownClass(cls):
        cls.view.close()
        cls.view.deleteLater()
        pump(20)
        os.unlink(cls.file.name)

    def at(self, y):
        flick = self.view.rootObject().property('flick')
        flick.setProperty('contentY', y)
        pump(120)
        image = self.view.grabWindow()
        dpr = image.devicePixelRatio() or 1
        return lambda x, yy: image.pixelColor(int(x * dpr), int(yy * dpr))

    def test_no_veil_is_painted_over_the_edges_r624(self):
        from PySide6.QtQuick import QSGRendererInterface
        if self.view.rendererInterface().graphicsApi() != QSGRendererInterface.GraphicsApi.Software:
            self.skipTest("a graphics API draws the content's fade (EdgeFades): quick.controlli.test_dissolvenza_r624")
        pixel = self.at(200)
        x = 20 + 7 + 100                                      # in the list, clear of the bar
        # the content (dark) reaches the list's edge as it is: no band of the list's ground, nor of the card's
        for y in (20 + 7 + 2, 260 - 20 - 7 - 3):
            self.assertLess(pixel(x, y).lightness(), 60, f'the edge at {y} is the content, not a veil')
        self.assertLess(pixel(x, 130).lightness(), 60)
        # one pixel of scrolling changes nothing at the edge
        before = self.at(0)(x, 20 + 7 + 3).lightness()
        after = self.at(1)(x, 20 + 7 + 3).lightness()
        self.assertLess(abs(after - before), 60, (before, after))

if __name__ == '__main__':
    unittest.main()
