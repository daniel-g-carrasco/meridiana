"""R555 (Daniel 08-09/11/2026: «non so se hai compreso la mia esigenza di avere tutto ben coordinato e simmetrico»),
measured on the window as it is drawn (off screen, scale 1; the scripts of r34-armonia measured 2 and the dark theme):

(1) what is written over the views stands on one ground (Theme.colors.overlay.glass): compass, scale, coordinates,
    the map's credit and notice, the legends; D5: the credit leaves the coordinates' room; D4: a label of the drawing
    gives way to the plan's chrome (Plan.clearOfChrome).
(2) the open phase tab: the outline to the disc, the disc to the name's ink and the name's ink to the outline, equal
    within a device pixel.
(3) File's hover and press: the same top and height as a tab's hover, the same margin at both sides.
(7) the box's focus ring: the same distance from the box on its four sides, shown for the keyboard only, grey.
(10) the check opened from an object's mark stands on the selection's ground in the checks.
"""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

import _setup
from meridiana import i18n
from meridiana.app import jobs
from meridiana.app.interface import theme_colors
from meridiana.gui.application import QuickWindow, create_app
from meridiana.gui.capture import grab
from quick.aiuti.differential import connected_fixture
from quick.gestures import pump

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def far(a, b, limit=60):
    return abs(a.red() - b.red()) + abs(a.green() - b.green()) + abs(a.blue() - b.blue()) > limit


class Harmony(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        create_app()
        i18n.setup('it')
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1180, 820)
        cls.win.show()
        cls.host.shell.trigger('phase_model')
        pump(800)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.host.shell.trigger('phase_model')
        pump(500)

    def items(self, root=None, hidden=False):
        out, pending = [], [root or self.win.contentItem()]
        while pending:
            o = pending.pop()
            if not hidden and not o.isVisible():
                continue
            out.append(o)
            pending.extend(o.childItems())
        return out

    def find(self, name, hidden=False):
        return next((o for o in self.items(hidden=hidden) if o.objectName() == name), None)

    def scene_rect(self, item):
        p = item.mapToScene(QPointF(0, 0))
        return p.x(), p.y(), item.width(), item.height()

    def away(self):
        QTest.mouseMove(self.win, self.win.contentItem().mapToScene(QPointF(10, 790)).toPoint())
        pump(200)

    def test_1_what_is_written_over_the_views_stands_on_one_ground(self):
        glass = QColor(theme_colors.qt_hex(theme_colors.OVERLAY['glass']))
        compass = self.find('compass')
        grounds = {'compass': compass.property('background')}
        for name in ('scaleBar', 'planCursor', 'mapCredit', 'mapNotice', 'optimizerLegend', 'sunMapLegend'):
            item = self.find(name, hidden=True)
            self.assertIsNotNone(item, name)
            grounds[name] = item.property('color')
        self.assertEqual({k: v.name(QColor.NameFormat.HexArgb) for k, v in grounds.items() if v != glass}, {})

    def test_1_the_credit_leaves_the_coordinates_room_and_labels_give_way_to_the_chrome(self):
        plan = self.find('compass').parentItem()
        p = plan.mapToScene(QPointF(plan.width() / 2, plan.height() / 2)).toPoint()
        QTest.mouseMove(self.win, p)
        pump(300)
        cursor, credit = self.find('planCursor'), self.find('mapCredit')
        self.assertTrue(cursor.isVisible())
        a, b = self.scene_rect(cursor), self.scene_rect(credit) if credit is not None else (1e9, 0, 0, 0)
        self.assertLessEqual(a[0] + a[2], b[0], 'the credit covers the coordinates')
        self.away()
        compass = self.find('compass')
        at = compass.mapToItem(plan, QPointF(0, 0))
        clear = plan.metaObject().indexOfMethod('clearOfChrome(QVariant,QVariant,QVariant,QVariant)')
        self.assertGreaterEqual(clear, 0)
        from PySide6.QtCore import Q_RETURN_ARG, QMetaObject, Q_ARG
        def asks(x, y, w, h):
            return QMetaObject.invokeMethod(plan, 'clearOfChrome', Q_RETURN_ARG('QVariant'), Q_ARG('QVariant', x),
                                            Q_ARG('QVariant', y), Q_ARG('QVariant', w), Q_ARG('QVariant', h))
        self.assertFalse(asks(at.x() + 4, at.y() + 4, 40, 18))
        self.assertTrue(asks(plan.width() / 2, plan.height() / 2, 40, 18))

    def open_tab_gaps(self, image):
        tab = self.find('modelTab')
        row = next(c for c in tab.childItems() if c.metaObject().className().startswith('QQuickRow'))
        disc, label = row.childItems()[0], row.childItems()[1]
        d = image.devicePixelRatio()
        tx, ty, tw, th = self.scene_rect(tab)
        dx, _dy, dw, _dh = self.scene_rect(disc)
        lx, ly, lw, lh = (round(v * d) for v in self.scene_rect(label))
        ground = image.pixelColor(lx, ly)
        cols = [x for x in range(lx, lx + lw) if any(far(image.pixelColor(x, y), ground, 90) for y in range(ly, ly + lh))]
        return dx * d - (tx + 1) * d, cols[0] - (dx + dw) * d, (tx + tw - 1) * d - (cols[-1] + 1)

    def test_2_the_open_tab_has_the_same_room_round_the_disc_and_the_name(self):
        self.away()
        left, middle, right = self.open_tab_gaps(grab(self.win))
        self.assertLessEqual(max(left, middle, right) - min(left, middle, right), 1.0, (left, middle, right))

    def test_3_files_hover_is_a_tabs_hover(self):
        self.away()
        file_button, hover = self.find('fileButton'), self.find('plantTabHover', hidden=True)
        fx, fy, fw, fh = self.scene_rect(file_button)
        hx, hy, hw, hh = self.scene_rect(hover)
        self.assertEqual((round(fy), round(fh)), (round(hy), round(hh)))
        image = grab(self.win)
        d = image.devicePixelRatio()
        x0, y0, x1, y1 = round(fx * d), round(fy * d), round((fx + fw) * d), round((fy + fh) * d)
        ground = image.pixelColor(x0 + 1, y1 - 2)
        cols = [x for x in range(x0, x1) if any(far(image.pixelColor(x, y), ground, 90) for y in range(y0, y1))]
        self.assertLessEqual(abs((cols[0] - x0) - (x1 - 1 - cols[-1])), 1, (cols[0] - x0, x1 - 1 - cols[-1]))

    def test_7_the_boxs_ring_is_centred_grey_and_for_the_keyboard_only(self):
        c = QQmlComponent(self.host.engine)
        c.setData(b'import QtQuick\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n'
                  b'Rectangle { width: 200; height: 60; color: Theme.colors.panel; z: 10000\n'
                  b'  M.CheckBox { objectName: "ringBox"; x: 20; y: 16; text: "Casella"; checked: true }\n'
                  b'  M.CheckBox { objectName: "otherBox"; x: 120; y: 16; text: "Altra" } }', 'file:///ring.qml')
        board = c.create()
        self.assertIsNotNone(board, c.errorString())
        board.setParentItem(self.win.contentItem())
        board.setParent(self.win.contentItem())
        board.setPosition(QPointF(300, 400))
        self.board = board
        import shiboken6
        self.addCleanup(lambda: shiboken6.isValid(board) and board.deleteLater())
        box = next(o for o in self.items(board) if o.objectName() == 'ringBox')
        def measure():
            image = grab(self.win)
            d = image.devicePixelRatio()
            indicator = box.property('indicator')
            p = indicator.mapToScene(QPointF(0, 0))
            side = indicator.width()
            inner = [(v + (side - 16) / 2) * d for v in (p.x(), p.y())] + [(v + (side + 16) / 2) * d for v in (p.x(), p.y())]
            ground = image.pixelColor(round((p.x() - 8) * d), round((p.y() + side / 2) * d))
            cy, cx = round((p.y() + side / 2) * d), round((p.x() + side / 2) * d)
            row = [x for x in range(round((p.x() - 6) * d), round((p.x() + side + 6) * d)) if far(image.pixelColor(x, cy), ground)]
            col = [y for y in range(round((p.y() - 6) * d), round((p.y() + side + 6) * d)) if far(image.pixelColor(cx, y), ground)]
            gaps = (inner[0] - row[0], row[-1] + 1 - inner[2], inner[1] - col[0], col[-1] + 1 - inner[3])
            return image, row, cy, gaps
        box.forceActiveFocus(Qt.FocusReason.MouseFocusReason)
        pump(300)
        _image, _row, _cy, gaps = measure()
        self.assertLess(max(gaps), 1.0, ('the ring shows after a click', gaps))
        next(o for o in self.items(board) if o.objectName() == 'otherBox').forceActiveFocus(Qt.FocusReason.MouseFocusReason)
        pump(100)
        box.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        pump(300)
        image, row, cy, gaps = measure()
        self.assertGreater(min(gaps), 1.0, ('no ring with the keyboard', gaps))
        self.assertLessEqual(max(gaps) - min(gaps), 1.0, gaps)
        ring_ink = image.pixelColor(row[0], cy)
        accent = QColor(self.host.engine.rootContext().contextProperty('themeTokens').property('colors')['accent'])
        self.assertGreater(abs(ring_ink.hueF() - accent.hueF()) + abs(ring_ink.saturationF() - accent.saturationF()), 0.2,
                           'the ring is still the accent')

    def test_10_the_check_opened_from_a_mark_is_marked(self):
        from quick.gestures import wait_for
        self.host.bridge.request_checks()
        wait_for(lambda: not self.host.bridge.checks_feed.busy())
        self.host.shell.trigger('phase_plant')
        pump(800)
        # what the click on a sub-field's mark asks of the checks (Plan.qml's mark -> plan.markClick -> markClicked)
        self.win.runCommand('focus_checks')
        pump(500)
        self.assertEqual(self.find('checkOpened'), None)
        self.host.plan.markClicked.emit('site', '')
        pump(800)
        opened = [o for o in self.items() if o.objectName() == 'checkOpened']
        self.assertEqual(len(opened), 1)


if __name__ == '__main__':
    unittest.main()
