"""R489: the veils at the edges of Meridio's conversation (and of any area that scrolls with the bar's veils).

Daniel (06/11/2026, photo meridio-messaggi.png): «le velature non vengono come dovrebbero, sono buggate»: over the
conversation's white a grey band stood at the top, behind «Tu». The conversation is a ScrollView whose ground is its
own background (Theme.colors.view) inside a card of another colour, with a padding of 7 px and the bar outside the
list. The veils are measured here on a copy of that structure: they take the colour of the ground they lie on, they
cover only the edges (the list's top and bottom band, the padding above and below it included, never the border or
the bar), and they come in with the scrolling, without a jump.
"""
import os
import unittest

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQuick import QQuickView

from meridiana.quick.backend.controls import install_controls
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

    def test_veils_take_the_lists_ground_cover_the_padding_and_come_in_without_a_jump(self):
        # scrolled well inside: the content (dark) is veiled to the list's white at the very edge, padding included
        pixel = self.at(200)
        x = 20 + 7 + 100                                      # in the list, clear of the bar
        for y in (20 + 2, 20 + 7, 260 - 20 - 3, 260 - 20 - 7):
            self.assertGreater(pixel(x, y).lightness(), 235, f'the edge at {y} is the list\'s ground, not the content')
        # the veil's colour is the white of the list, not the card's: no tinted band
        tint = pixel(x, 20 + 7 + 2)
        self.assertLess(abs(tint.red() - tint.blue()), 6, tint.name())
        # the middle of the list is not veiled
        self.assertLess(pixel(x, 130).lightness(), 60)
        # one pixel of scrolling: the veil comes in by as much, not at once
        before = self.at(0)(x, 20 + 7 + 3).lightness()
        after = self.at(1)(x, 20 + 7 + 3).lightness()
        self.assertLess(abs(after - before), 60, (before, after))


if __name__ == '__main__':
    unittest.main()
