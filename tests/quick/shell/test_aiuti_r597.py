"""The help without Meridio (R596, R597, Daniel 13/11/2026; study 47, P1-P3): the «?» opens its bubble anchored to it,
one at a time, closed by a second click, Esc, the scroll of its panel and the change of phase; F1 opens the help of
the field with the keyboard beside it; «Open in the manual» waits for the manual in the File page."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest

import _setup
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from meridiana.gui.backend import help_part
from quick.gestures import item, pump, wait_for
from quick.aiuti.differential import connected_fixture

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def descendants(root):
    out, stack = [], [root]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(node.childItems())
    return out


class HelpBubble(unittest.TestCase):
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
        cls.session = cls.host.bridge.session
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.resize(1600, 960)
        cls.win.show()
        cls.host.shell.trigger('phase_model')
        pump(400)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def setUp(self):
        self.session.select('site', '')
        self.host.shell.trigger('phase_model')
        pump(300)

    def tearDown(self):
        QTest.keyClick(self.win, Qt.Key.Key_Escape)
        pump(200)

    def click(self, target):
        p = target.mapToScene(QPointF(target.width() / 2, target.height() / 2))
        QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, pos=p.toPoint())
        pump(250)

    def shown(self):
        return [m for m in descendants(self.win.contentItem())
                if m.metaObject().indexOfProperty('helpMark') >= 0 and m.property('shown')]

    def test_one_bubble_at_a_time_and_a_second_click_closes_it(self):
        site, network = item(self.win, 'section-help:site'), item(self.win, 'section-help:site.network')
        self.click(site)
        self.assertEqual(self.shown(), [site])
        bubble = site.findChild(QObject, 'helpBubble')
        self.assertTrue(bubble.findChild(QObject, 'helpBubbleText').property('text'))
        self.click(network)
        self.assertEqual(self.shown(), [network], 'the other one closed')
        self.click(network)
        self.assertEqual(self.shown(), [], 'a second click on its «?» closes it')

    def test_it_points_at_its_mark_over_the_section_title(self):
        mark = item(self.win, 'section-help:site.network')
        self.click(mark)
        bubble = mark.findChild(QObject, 'helpBubble')
        wait_for(lambda: bubble.property('opacity') == 1)
        self.assertEqual(bubble.property('placedSide'), 'above')
        tip = next(c for c in descendants(bubble.property('background')) if c.objectName() == 'popupPointer')
        centre = tip.mapToScene(QPointF(tip.width() / 2, tip.height() / 2))
        middle = mark.mapToScene(QPointF(mark.width() / 2, mark.height() / 2))
        self.assertLessEqual(abs(centre.x() - middle.x()), 1, 'the pointer on the «?»')
        self.assertLess(centre.y(), middle.y())
        frame = bubble.property('background').mapToScene(QPointF(0, 0))
        self.assertEqual((frame.x(), frame.y()), (round(frame.x()), round(frame.y())), 'on the whole pixel')

    def test_esc_the_scroll_and_the_phase_close_it(self):
        mark = item(self.win, 'section-help:site')
        self.click(mark)
        QTest.keyClick(self.win, Qt.Key.Key_Escape)
        pump(200)
        self.assertEqual(self.shown(), [])
        self.click(mark)
        flick = mark.parentItem()
        while flick is not None and flick.metaObject().indexOfProperty('contentY') < 0:
            flick = flick.parentItem()
        self.assertIsNotNone(flick, 'the properties scroll')
        flick.setProperty('contentY', flick.property('contentY') + 1)
        pump(200)
        self.assertEqual(self.shown(), [], 'the scroll of its panel closes it')
        flick.setProperty('contentY', 0)
        self.click(mark)
        self.host.shell.trigger('phase_plant')
        pump(300)
        self.assertEqual(self.shown(), [])

    def test_the_foot_has_ask_meridio_and_no_manual_until_the_file_page_has_it(self):
        self.assertFalse(help_part.MANUAL_PAGE, 'P4 is not done: the switch stays off')
        mark = item(self.win, 'section-help:site')
        self.click(mark)
        bubble = mark.findChild(QObject, 'helpBubble')
        self.assertFalse(bubble.findChild(QObject, 'helpBubbleManual').property('visible'))
        self.assertTrue(bubble.findChild(QObject, 'helpBubbleAsk').property('visible'))
        self.assertEqual(self.host.parts.controllers['help'].entry('site')['manual'], '')

    def test_f1_opens_the_help_of_the_field_beside_it(self):
        subfield = self.session.project.subfields[0]
        self.session.select('subfield', subfield.id)
        pump(500)
        editor = next((e for e in descendants(self.win.contentItem())
                       if e.metaObject().indexOfProperty('helpId') >= 0 and e.property('helpId') == 'subfield.mounting'
                       and e.isVisible() and e.metaObject().indexOfProperty('helpMark') < 0), None)
        self.assertIsNotNone(editor, 'the field «Mounting» of the sub-field')
        inner = next(c for c in descendants(editor) if c.metaObject().indexOfProperty('activeFocusOnTab') >= 0
                     and c.property('activeFocusOnTab') and c.isVisible())
        inner.forceActiveFocus()
        pump(100)
        self.win.runCommand('context_help')
        pump(300)
        bubble = editor.findChild(QObject, 'helpBubble')
        self.assertIsNotNone(bubble, 'the bubble on the field')
        self.assertIn(bubble.property('placedSide'), ('left', 'right'))
        self.assertTrue(inner.hasActiveFocus(), 'the keyboard stays in the field')

    def test_the_mark_has_no_line_on_any_ground(self):
        # Daniel 14/11/2026: «mi piace senza il bordino»: no line round the disc on the section band, the tile's field
        # or the card's panel, in both themes (it took a hair line on the grey grounds, R596)
        # read on the pixels (a Rectangle without a border still says border.width 1): the disc's outermost pixels, at
        # its four cardinal points, stand between the disc's grey and the ground's, as a line of its own colour would not
        def no_line(mark, what):
            disc = next(c for c in descendants(mark) if c.objectName() == 'helpDisc')
            image = self.win.grabWindow()
            dpr = image.devicePixelRatio()
            top_left = disc.mapToScene(QPointF(0, 0))
            x0, y0, size = top_left.x(), top_left.y(), disc.width()
            cx, cy = x0 + size / 2, y0 + size / 2

            def grey(x, y):
                c = image.pixelColor(int(x * dpr), int(y * dpr))
                return (c.red() + c.green() + c.blue()) / 3
            inside, ground = grey(x0 + 3.5, cy), grey(cx, y0 - 1.5)
            low, high = min(inside, ground) - 4, max(inside, ground) + 4
            for x, y in ((x0 + 0.5, cy), (x0 + size - 0.5, cy), (cx, y0 + 0.5), (cx, y0 + size - 0.5)):
                self.assertTrue(low <= grey(x, y) <= high, f'{what}: a line round the disc at ({x}, {y}): '
                                f'{grey(x, y):.0f}, disc {inside:.0f}, ground {ground:.0f}')
        try:
            for theme in ('light', 'dark'):
                self.host.theme.configure({'theme': theme})
                pump(300)
                self.host.shell.trigger('phase_model')
                pump(300)
                no_line(item(self.win, 'section-help:site'), f'{theme}: on the section band')
                self.host.shell.trigger('phase_production')
                pump(500)
                card = item(self.win, 'propertiesHelp')
                self.assertTrue(card.isVisible())
                self.assertEqual(card.property('helpKey'), 'phase.production')
                tiles = [m for m in descendants(self.win.contentItem()) if m.metaObject().indexOfProperty('helpMark') >= 0
                         and m.property('helpPlace') == 'tile' and m.isVisible()]
                self.assertTrue(tiles, 'the tiles of the results have their «?»')
                for mark in [card] + tiles:
                    no_line(mark, f'{theme}: {mark.property("helpPlace")}')
        finally:
            self.host.theme.configure({'theme': 'light'})
            pump(300)


if __name__ == '__main__':
    unittest.main()
