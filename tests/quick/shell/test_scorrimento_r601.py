"""R601 (Daniel 14/11/2026, the window «Importa un modello IFC»):

A. «Sta roba delle sezioni in cui si scorre in verticale dentro altre sezioni in cui si scorre in verticale bisogna
   togliersela»: nothing that scrolls vertically inside something else that scrolls vertically, in every phase, every
   section of File and of the settings, Meridio and every window of the program; measured on the window as it is drawn
   (the items that scroll and their ancestors), with lists long enough to need it.
B. «Se mi trovo in basso, dopo un po' totalmente a caso mi riporta su da solo»: a window scrolled to its bottom stays
   there when the backend says something changed with nothing new, and when the focus comes back by itself (the window
   active again after another program); the keyboard's Tab still brings a control into sight.

    python -m unittest quick.shell.test_scorrimento_r601
"""
import os
import tempfile
import unittest
from pathlib import Path

import shiboken6
from PySide6.QtCore import QMetaObject, QObject, QPointF, Qt
from PySide6.QtGui import QWindow
from PySide6.QtQml import qmlContext
from PySide6.QtTest import QTest

import _setup
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from meridiana.gui.backend import settings_schema
from quick.aiuti.differential import connected_fixture
from quick.gestures import pump

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

SAMPLE = Path(__file__).resolve().parents[2] / 'data' / 'ifc' / 'Building-Architecture.ifc'
# The nests left for Daniel to decide (R601: «se in un posto l'annidamento è davvero necessario... lascialo, elencalo»),
# written as (outer, inner) by object name and file. None: Settings > Keyboard, the last, opens the shortcuts' window
# of its own instead of scrolling their list inside the page (r35-segni, Daniel 14/11/2026: «Toglilo»).
LEFT_FOR_DANIEL = set()
NOTES = [{'title': 'Lasciato fuori', 'items': [f'{n * 37} elementi non su una copertura (gruppo {n})' for n in range(1, 60)]}]


def where(o):
    c = qmlContext(o)
    url = c.baseUrl().toString() if c is not None else ''
    return url.split('/Meridiana/')[-1] if url else ''


def scrolls_vertically(o):
    """A Flickable of its own (a page, a list, a table, a text area) that the user can move up and down."""
    meta = o.metaObject()
    if meta.indexOfProperty('contentY') < 0 or meta.indexOfProperty('flickableDirection') < 0:
        return False
    if o.property('interactive') is False:
        return False
    if meta.indexOfProperty('orientation') >= 0:
        try:
            if int(getattr(o.property('orientation'), 'value', o.property('orientation'))) == 1:
                return False            # a horizontal list
        except RuntimeError:
            pass
    return not (o.property('contentWidth') > o.property('width') + 1
                and o.property('contentHeight') <= o.property('height') + 1)


def named(o):
    """The name of a scrolling item: its own, or its ScrollPage's, or its component's."""
    for node in (o, o.parentItem()):
        if node is not None and node.objectName():
            return node.objectName()
    return o.metaObject().className().split('_QML')[0]


class Window(unittest.TestCase):
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
        cls.win.resize(1100, 700)
        cls.win.show()
        pump(400)
        ctx = cls.host.engine.rootContext()
        cls.part = ctx.contextProperty('filePart')
        cls.dialogs = ctx.contextProperty('filesDialogsBackend')
        cls.actions = ctx.contextProperty('plantActions')

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def items(self, root=None):
        out, pending = [], [root or self.win.contentItem()]
        while pending:
            o = pending.pop()
            if not o.isVisible():
                continue
            out.append(o)
            pending.extend(o.childItems())
        return out

    def find(self, name):
        return next((o for o in self.items() if o.objectName() == name), None)

    def read_ifc(self, notes=True):
        self.part.openDialog('ifc')
        pump(300)
        self.dialogs.readFile(str(SAMPLE))
        for _ in range(1200):
            if not self.dialogs.busy:
                break
            pump(50)
        self.assertFalse(self.dialogs.busy, 'the sample was not read in 60 s')
        if notes:
            self.dialogs._state['ifcLists'] = NOTES
            self.dialogs.changed.emit()
        pump(500)

    def close_file_window(self):
        self.dialogs.cancel()
        self.part.dismissDialog()
        pump(300)


class Nested(Window):
    """A. No scroll inside a scroll."""

    def nests(self, scene, found):
        pending = [(self.win.contentItem(), None)]
        while pending:
            o, outer = pending.pop()
            if not o.isVisible() or o.width() <= 0 or o.height() <= 0:
                continue
            here = outer
            if scrolls_vertically(o):
                if outer is not None:
                    key = (named(outer), where(outer), named(o), where(o))
                    if key not in LEFT_FOR_DANIEL:
                        found.setdefault(key, []).append(scene)
                here = o
            pending.extend((c, here) for c in o.childItems())

    def test_nothing_scrolls_inside_something_that_scrolls(self):
        found = {}
        for phase in ('model', 'plant', 'production', 'consumption', 'economics', 'report'):
            self.host.shell.trigger('phase_' + phase)
            pump(900)
            self.nests('phase ' + phase, found)
        self.win.runCommand('assistant')
        pump(600)
        self.nests('Meridio', found)
        self.win.runCommand('assistant')
        self.part.show_file('open')
        pump(600)
        sections = [o.objectName()[len('fileNav_'):] for o in self.items() if o.objectName().startswith('fileNav_')]
        for key in [k for k in sections if k not in ('quit', 'back', 'preferences')] + [
                'preferences:' + k for k in settings_schema.SECTIONS]:
            self.part.show_file(key)
            pump(600)
            self.nests('File ' + key, found)
        self.win.setProperty('fileOpen', False)
        pump(400)
        # the windows of File, with the lists that were scrolling inside them made long
        self.read_ifc()
        self.nests('window ifc', found)
        self.close_file_window()
        for kind, filler in (('update', {'releaseNotes': '\n\n'.join(f'- note {n}' for n in range(80)), 'currentVersion': '0'}),
                             ('pvsyst', {'summary': [f'riga {n}' for n in range(60)]}),
                             ('canopy', {}), ('template', {}), ('shortcuts', {}), ('registry', {}), ('about', {})):
            self.part.openDialog(kind)
            pump(300)
            self.dialogs._state.update(filler)
            self.dialogs.changed.emit()
            pump(500)
            self.nests('window ' + kind, found)
            self.close_file_window()
        self.host.shell.trigger('phase_plant')
        pump(600)
        for kind in ('clear', 'sizing', 'storage', 'proposal', 'catalog'):
            self.actions.open(kind)
            pump(700)
            self.nests('plant window ' + kind, found)
            self.actions.dismiss()
            pump(300)
        every = [o for r in self.host.engine.rootObjects() for o in r.findChildren(QObject)]
        for o in every:
            if not shiboken6.isValid(o) or o.property('acceptOnReturn') is None:
                continue
            name = o.objectName() or str(o.property('title'))
            if name in ('fileDialogOverlay', 'dxfOptions', 'fileCatalogDialog') or name.startswith('plant-'):
                continue
            QMetaObject.invokeMethod(o, 'open')
            pump(500)
            self.nests('window ' + name, found)
            QMetaObject.invokeMethod(o, 'close')
            pump(300)
        self.assertEqual({' > '.join(k): v for k, v in found.items()}, {})

    def test_the_keyboard_settings_open_the_shortcuts_window_and_nothing_nests_in_a_low_window(self):
        # it nested only when the window was low: the list kept at least 360 points in a page shorter than that
        self.win.resize(1100, 460)
        self.addCleanup(self.win.resize, 1100, 700)
        self.part.show_file('preferences:keyboard')
        pump(600)
        found = {}
        self.nests('File preferences:keyboard, low', found)
        self.assertEqual({' > '.join(k): v for k, v in found.items()}, {})
        self.assertIsNone(self.find('settingsShortcutTable'))
        page = self.find('settingsScroll')
        opener = self.find('settingsOpenShortcuts')
        self.assertIsNotNone(opener)
        # the section is short: its button in view without scrolling the page
        bottom = opener.mapToItem(page, QPointF(0, opener.height())).y()
        self.assertLessEqual(bottom, page.height())
        QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, pos=opener.mapToScene(
            QPointF(opener.width() / 2, opener.height() / 2)).toPoint())
        pump(600)
        self.addCleanup(self.close_file_window)
        self.assertEqual(self.dialogs.kind, 'shortcuts')
        # the window of its own: its search in view, its list the only thing that scrolls in it
        search = self.find('dialogShortcutSearch')
        self.assertIsNotNone(search)
        self.assertTrue(search.isVisible())
        self.assertGreater(len(self.dialogs.state['shortcuts']), 90)
        self.nests('window shortcuts, low', found)
        self.assertEqual({' > '.join(k): v for k, v in found.items()}, {})
        # what the page did is done there: the search in sight and working, a shortcut changed, all put back
        body = self.find('dialogView')
        top = search.mapToItem(body, QPointF(0, 0)).y()
        self.assertGreaterEqual(top, 0)
        self.assertLessEqual(top + search.height(), body.height())
        table = self.find('dialogShortcutTable')
        rows = lambda: table.property('model').property('length').toInt()  # noqa: E731  (a JS array)
        every = rows()
        search.forceActiveFocus()
        for char in 'salva':
            QTest.keyClick(self.win, char)
        pump(300)
        shown = rows()
        self.assertTrue(0 < shown < every, (shown, every))
        command = self.dialogs.state['shortcuts'][0]['id']
        self.assertTrue(self.dialogs.assignShortcut(command, 'Ctrl+Shift+F9'))
        self.assertEqual(self.dialogs.bindings[command], ['Ctrl+Shift+F9'])
        self.dialogs.resetShortcut('')
        from meridiana.app.interface import shortcuts
        self.assertEqual(self.dialogs.bindings, shortcuts.bindings({}))


class Stays(Window):
    """B. A window scrolled to its bottom stays there."""

    def setUp(self):
        self.read_ifc()
        self.body = self.find('dialogView')
        self.assertIsNotNone(self.body)
        self.assertGreater(self.body.property('contentHeight'), self.body.property('height') + 200,
                           'the window must be taller than its room for the test to mean something')
        # a box ticked with the mouse at the top: it keeps the focus while the wheel takes the window down
        self.box = next(o for o in self.items() if o.objectName().startswith('ifcCheck_'))
        p = self.box.mapToScene(QPointF(10, self.box.height() / 2))
        QTest.mouseClick(self.win, Qt.MouseButton.LeftButton, pos=p.toPoint())
        pump(300)
        # (the tick is a change: the window builds its boxes again, the one under the mouse takes the focus back)
        self.box = next(o for o in self.items() if o.objectName().startswith('ifcCheck_'))
        self.box.forceActiveFocus(Qt.FocusReason.MouseFocusReason)
        pump(200)
        self.bottom = self.body.property('contentHeight') - self.body.property('height')
        self.body.setProperty('contentY', self.bottom)
        pump(300)

    def tearDown(self):
        self.close_file_window()

    def test_a_notice_with_nothing_new_rebuilds_nothing_and_moves_nothing(self):
        lists = self.find('ifcLists')
        rows = [o for o in self.items(lists) if o.metaObject().indexOfProperty('text') >= 0]
        self.dialogs.changed.emit()
        pump(600)
        self.assertAlmostEqual(self.body.property('contentY'), self.bottom, delta=1)
        self.assertTrue(all(shiboken6.isValid(o) for o in rows + [self.box]), 'the window built its content again')

    def test_the_plan_made_again_adds_nothing_above_and_moves_nothing(self):
        # R598 with R601: a choice made again plans again (the dialog busy, as while it reads); the reading's row
        # (M.WorkRow) is only for the reading, so nothing comes in above what was read and the body stays down
        page = self.find('ifcLists').parentItem()
        self.assertIsNotNone(page.findChild(QObject, 'ifcReading'))
        storeys = self.box.objectName()[len('ifcCheck_'):]
        key = next(f['key'] for f in self.dialogs.fields if f.get('kind') == 'checks')
        now = list(self.dialogs.state.get(key) or [])
        seen = []

        def look():
            reading = page.findChild(QObject, 'ifcReading')
            seen.append((self.dialogs.busy, reading is not None and reading.isVisible()))
        self.dialogs.changed.connect(look)
        try:
            self.dialogs.setValue(key, [v for v in now if v != storeys] if storeys in now else now + [storeys])
            pump(0)
            look()
        finally:
            self.dialogs.changed.disconnect(look)
        self.assertTrue(any(busy for busy, _v in seen), f'the choice did not plan again: {seen}')
        for _ in range(200):
            if not self.dialogs.busy:
                break
            pump(50)
        pump(400)
        self.assertFalse(self.dialogs.busy)
        self.assertEqual([v for _b, v in seen if v], [], 'the reading row came in while planning')
        # the plan gives its own notes (shorter than the test's): the body stays at the bottom of what is there now
        bottom = min(self.bottom, self.body.property('contentHeight') - self.body.property('height'))
        self.assertGreater(bottom, 0)
        self.assertAlmostEqual(self.body.property('contentY'), bottom, delta=1)

    def test_the_focus_that_comes_back_by_itself_does_not_scroll(self):
        self.assertTrue(self.box.hasActiveFocus())
        other = QWindow()
        other.resize(60, 60)
        other.show()
        other.requestActivate()
        pump(300)
        self.win.requestActivate()
        pump(500)
        other.destroy()
        self.assertTrue(self.box.hasActiveFocus())
        self.assertAlmostEqual(self.body.property('contentY'), self.bottom, delta=1)

    def test_the_tab_still_brings_a_control_into_sight(self):
        self.find('dialogAccept').forceActiveFocus(Qt.FocusReason.MouseFocusReason)
        pump(200)
        self.box.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        pump(300)
        top = self.box.mapToItem(self.body.property('contentItem'), QPointF(0, 0)).y()
        self.assertLessEqual(self.body.property('contentY'), top + 1)


if __name__ == '__main__':
    unittest.main()
