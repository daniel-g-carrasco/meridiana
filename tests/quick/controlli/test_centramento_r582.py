"""R582: the text of every field stands on the field's middle, at every size of the text.

Daniel (11/11/2026, File > Nuovo progetto): «ci sono dei problemi nel centramento del testo in queste caselle di
input»: the hint of the empty address field stood 1.5 px over the numbers of Latitudine and Longitudine, and the
number and the combo started 2 px before the text field. Measured on the drawn image: the ink of capitals and digits
(«4520 HMN») is centred on the field's middle within half a pixel, in the text field, its hint, the number with its
unit, the combo, a taller field and the field over the views; the text fields, the number and the combo start their
text at the same distance from the left edge.
"""
import os
import tempfile
import unittest

import _setup
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQuick import QQuickItem, QQuickView

from meridiana.gui.backend.controls import install_controls
from quick.gestures import pump
from quick.aiuti.caratteri import glyph

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = b'''
import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
Rectangle {
    width: 300; height: 330; color: Theme.colors.panel
    Column { x: 10; y: 10; spacing: 8; width: 280
        M.TextField { objectName: "text"; width: 280; text: "4520 HMN" }
        M.TextField { objectName: "hint"; width: 280; placeholderText: "4520 HMN" }
        M.NumberField { objectName: "number"; width: 280; value: 4520; decimals: 0; unit: "MW" }
        M.ComboBox { objectName: "combo"; width: 280; model: ["4520 HMN"] }
        M.TextField { objectName: "tall"; width: 280; height: 40; text: "4520 HMN" }
        M.OverlayField { objectName: "overlay"; text: "4520"; unit: "M" }
    }
}
'''
NAMES = ('text', 'hint', 'number', 'combo', 'tall', 'overlay')
INSET = ('text', 'hint', 'number', 'combo', 'tall')


def setUpModule():
    _setup.keep_global_state()


class FieldTextCentred(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.file = tempfile.NamedTemporaryFile('wb', suffix='.qml', delete=False)
        cls.file.write(QML)
        cls.file.close()

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.file.name)

    def measure(self, size):
        view = QQuickView()
        install_controls(view.engine(), dict(theme='light', reducedMotion=True, textSize=size))
        view.setSource(QUrl.fromLocalFile(self.file.name))
        self.assertIsNotNone(view.rootObject(), view.errors())
        view.show()
        pump(250)
        image = view.grabWindow()
        dpr = image.width() / view.width()
        found = {}
        for name in NAMES:
            item = view.rootObject().findChild(QQuickItem, name)
            p = item.mapToScene(QPointF(0, 0))
            ground = image.pixelColor(int((p.x() + item.width() * .75) * dpr),
                                      int((p.y() + item.height() / 2) * dpr)).lightness()
            rows, cols = [], []
            x0, x1 = int((p.x() + 3) * dpr), int((p.x() + item.width() * .6) * dpr)
            for y in range(int((p.y() + 3) * dpr), int((p.y() + item.height() - 3) * dpr)):
                hit = [x for x in range(x0, x1) if abs(image.pixelColor(x, y).lightness() - ground) > 60]
                if hit:
                    rows.append(y)
                    cols.append(hit[0])
            self.assertTrue(rows, f'{size} {name}: no text drawn')
            centre = (rows[0] + rows[-1] + 1) / 2 / dpr
            found[name] = (centre - p.y() - item.height() / 2, min(cols) / dpr - p.x())
        view.close()
        view.deleteLater()
        pump(20)
        return found

    def test_the_capitals_stand_on_the_middle_and_start_at_the_same_inset(self):
        for size in ('small', 'medium', 'large'):
            found = self.measure(size)
            for name, (offset, _) in found.items():
                self.assertLessEqual(abs(offset), glyph(.5), f'{size} {name}: the text is {offset:+.2f} px off the middle')
            insets = [found[name][1] for name in INSET]
            self.assertLessEqual(max(insets) - min(insets), glyph(.5), f'{size}: the text starts at {insets}')


if __name__ == '__main__':
    unittest.main()
