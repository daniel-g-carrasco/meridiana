"""R663 (Daniel 16/11/2026, after a click on a check's mark: «cos'è questa nuova evidenziatura, contornino quadrato, che
non è possibile togliere in nessun modo tipo esc, click fuori, e non è possibile muovere con tab?»; and: «come mai per
l'evidenziatura non hai fatto cambio del colore di riempimento?»). The check opened from a mark stays filtered to its
object («This object», kept by Daniel's choice), and is selected as a row of the program's lists: the ground
`select_bg`, no line round it. Esc and a click on an empty place of the list let it go; Tab moves it to the next
check."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QKeyEvent

import _setup
from meridiana.app import jobs
from meridiana.core.rules.types import Item
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import click, pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


class CheckOpened(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        project = connected_fixture()
        results, keys, _laid = jobs.layout_of(project)
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project, Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.host.bridge.accept_layout(cls.host.bridge.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        # Offscreen clamps the initial show to its screen (318 px at scale 2.5).
        # Resize after showing, as the other window fixtures do.
        cls.win.resize(1180, 820)
        pump(800)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def items(self):
        out, pending = [], [self.win.contentItem()]
        while pending:
            o = pending.pop()
            if o.isVisible():
                out.append(o)
                pending.extend(o.childItems())
        return out

    def opened(self):
        return [o for o in self.items() if o.objectName() == 'checkOpened']

    def key(self, key):
        for kind in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            self.app.sendEvent(self.win, QKeyEvent(kind, key, Qt.KeyboardModifier.NoModifier))
        pump(150)

    def open_from_mark(self):
        self.host.plan.markClicked.emit('site', '')         # what a click on a mark asks of the checks
        wait_for(lambda: len(self.opened()) == 1, 5)

    def test_selected_ground_and_its_ways_out(self):
        self.host.bridge.request_checks()
        wait_for(lambda: not self.host.bridge.checks_feed.busy())
        self.host.shell.trigger('phase_plant')
        pump(800)
        self.win.runCommand('focus_checks')
        pump(500)
        checks = self.host.parts.controllers['checks']
        self.assertEqual(self.opened(), [])
        self.open_from_mark()
        self.assertTrue(checks.objectOnly, 'the click on a mark keeps its filter (Daniel 16/11/2026)')
        ground = self.opened()[0]
        self.assertEqual(QColor(ground.property('color')).name(),
                         QColor(self.host.engine.rootContext().contextProperty('themeTokens').property('colors')
                                ['select_bg']).name(), 'the selection\'s ground of the lists')
        # Esc lets it go
        list_item = next(o for o in self.items() if o.objectName() == 'checks-list')
        list_item.forceActiveFocus()
        pump(50)
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(self.opened(), [], 'Esc lets it go')
        # back, then a click on an empty place of the list
        self.open_from_mark()
        below = list_item.mapToScene(QPointF(list_item.width() / 2, list_item.height() - 4))
        if list_item.property('contentHeight') < list_item.height() - 8:
            click(self.app, self.win, below)
            pump(150)
            self.assertEqual(self.opened(), [], 'a click where there is no row lets it go')
        # Tab moves it to the next check, when there is one
        self.open_from_mark()
        rows = [r for r in checks.rows if not r['header']]
        list_item.forceActiveFocus()
        pump(50)
        current = checks.currentIndex
        self.key(Qt.Key.Key_Tab)
        if len(rows) > 1:
            self.assertNotEqual(checks.currentIndex, current, 'Tab goes to the next check')
            self.assertEqual(len(self.opened()), 1, 'the selection moved with it')

    def test_selection_covers_edges_and_title_keeps_body_weight(self):
        self.host.bridge.request_checks()
        wait_for(lambda: not self.host.bridge.checks_feed.busy())
        self.host.shell.trigger('phase_plant')
        pump(800)
        self.win.runCommand('focus_checks')
        pump(500)
        checks = self.host.parts.controllers['checks']
        checks.show_items([Item('warn', 'layout', 'Fixture check', '', ('building', 'b1'), detail='Fixture detail')])
        checks.showRelated('building', 'b1')
        self.host.plan.markClicked.emit('building', 'b1')
        wait_for(lambda: len(self.opened()) == 1, 5)
        ground = self.opened()[0]
        row = ground
        while not row.objectName().startswith('checks-row-'):
            row = row.parentItem()
        index = row.objectName().removeprefix('checks-row-')
        title = next(o for o in self.items() if o.objectName() == 'checks-text-' + index)
        tokens = self.host.engine.rootContext().contextProperty('themeTokens')
        normal = tokens.property('text')['body']['weight']
        pump(80)
        self.assertTrue(any(r.get('related') for r in checks.rows), 'exercise the related title too')
        for expanded in (False, True):
            data = next(r for r in checks.rows if not r['header'] and str(r['itemIndex']) == index)
            if bool(data['expanded']) != expanded:
                checks.toggleDetail(int(index))
                pump(80)
            self.assertEqual(title.property('font').weight(), normal)
        result = row.grabToImage()
        ready = []
        result.ready.connect(lambda: ready.append(True))
        wait_for(lambda: bool(ready))
        image = result.image()
        ratio = image.width() / row.width()
        selected = QColor(tokens.property('colors')['select_bg'])
        radius = tokens.property('radius')['CONTROL']
        for x in (radius + 1, row.width() - radius - 2):
            for y in (0, row.height() - 1):
                with self.subTest(x=x, y=y):
                    self.assertEqual(image.pixelColor(int((x+.5)*ratio), int((y+.5)*ratio)), selected)
        eye = next(o for o in self.items() if o.objectName() == 'checks-eye-' + index)
        self.assertEqual(eye.width(), eye.height(), 'the common square icon button')
        self.assertEqual(eye.height(), tokens.property('size')['CHIP'])
        self.key(Qt.Key.Key_Escape)
        self.assertEqual(title.property('font').weight(), normal, 'Esc changes no font weight')


if __name__ == '__main__':
    unittest.main()
