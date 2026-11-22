"""R662 (Daniel 15/11/2026, the plan's menu: «ancora non ce la facciamo ad avere simmetria nei menu a comparsa. guarda
quanto spazio rimane a destra di "propose inverters...". Rimane quasi attaccato al bordo, quando a sinistra ci sono
5mm!! inoltre non c'entra nulla con il menu a comparsa che compare con freccia sotto nei pulsanti doppi»): every popup
menu of the program is the one component (M.Menu with M.MenuItem, M.MenuEntry, M.MenuSeparator) and is symmetric.

Two guards:
- in the QML, a menu is never written with another component: outside Meridiana/Controls every Menu, MenuItem and
  MenuSeparator is the one of Meridiana.Controls (through its alias), and QtQuick.Templates' Menu and MenuItem are
  used only by Controls/Menu.qml and Controls/MenuItem.qml;
- in the real window off screen, every menu found (each phase's, the bar's, the split buttons', the plan's, the 3D
  view's and the project tree's right button, the submenus) is opened and measured on its components: from the
  frame to the first ink at the left (the column of the marks when the menu has one, else the text) as far as from
  the widest entry's last ink (its text, its keys or its submenu's arrow) to the frame at the right, within 1 px, and
  that margin a step of design.Space; the hover's grey and the rules as far in on both sides. On r34-unita (aafa816c)
  the plan's menu had 26 px at the left and 8 at the right (an empty slot for a check that no entry had), the Checks'
  32 and 24 (the width of entries hidden)."""
import os
import re
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPointF
from shiboken6 import getCppPointer

import _setup
from _fixtures import capannone
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.style import design
from quick.gestures import pump

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = Path(__file__).resolve().parents[3] / 'src/meridiana/gui/qml/Meridiana'
NAMES = r'(?:Menu|MenuItem|MenuSeparator)'
# the files of Controls that are the component itself
TEMPLATES = {'Menu.qml': 'T.Menu', 'MenuItem.qml': 'T.MenuItem', 'MenuSeparator.qml': 'T.MenuSeparator'}
# the menus that must be among those measured: the right button of the plan, of the 3D view and of the project tree,
# a split button's, the bar's
MUST = ('planContextMenu', 'sceneContextMenu', 'project-tree-context-menu', 'tool_tool_buildingMenu', 'mainMenuPopup_0')


def project():
    """The shed of the fixtures, laid, two thirds of its modules in strings on two inverters, as in Daniel's capture
    (an entry «Propose inverters and strings for the modules in no string»)."""
    p = capannone()
    results, _keys, _ = jobs.layout_of(p)
    sid = p.subfields[0].id
    modules = results[sid].modules
    per = len(modules) // 6
    p.energy['strings'] = {'runs': [{'inverter': 1 + i // 2, 'mppt': 1,
                                     'modules': [sid + '/' + m.key for m in modules[i*per:(i+1)*per]]}
                                    for i in range(4)]}
    return p


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        try:
            pending.extend(node.childItems())
        except RuntimeError:            # an item of a page let go meanwhile
            pass
    return out


def key_of(o):
    """The C++ object's address: a wrapper found twice is not the same Python object."""
    return getCppPointer(o)[0]


def named(item, name):
    return next((c for c in item.childItems() if c.objectName() == name), None)


class StaticRule(unittest.TestCase):
    def test_every_menu_in_the_qml_is_the_common_one(self):
        wrong = []
        for path in sorted(QML.rglob('*.qml')):
            text = path.read_text(encoding='utf8')
            inside = path.parent.name == 'Controls'
            aliases = set(re.findall(r'^import\s+Meridiana\.Controls\s+as\s+(\w+)', text, re.M))
            for line_no, line in enumerate(text.splitlines(), 1):
                code = line.split('//')[0]
                for alias, name in re.findall(r'(?:(\w+)\.)?\b(' + NAMES + r')\s*\{', code):
                    if alias == 'T':
                        if not (inside and TEMPLATES.get(path.name) == f'T.{name}'):
                            wrong.append(f'{path.name}:{line_no}: T.{name} outside its own file')
                    elif alias and alias not in aliases:
                        wrong.append(f'{path.name}:{line_no}: {alias}.{name} is not Meridiana.Controls\' {name}')
                    elif not alias and not inside:
                        wrong.append(f'{path.name}:{line_no}: {name} without the alias of Meridiana.Controls')
        self.assertEqual(wrong, [])


class EveryMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.addClassCleanup(i18n.setup, i18n.language())
        cls.app = _setup.qt_or_skip()
        from meridiana.gui.application import QuickWindow, create_app
        create_app()
        i18n.setup('en')
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(project(), Path(cls.folder.name), real_views=True,
                               theme={'theme': 'light', 'reducedMotion': True})
        cls.session = cls.host.bridge.session
        results, keys, _ = jobs.layout_of(cls.session.project)
        cls.host.bridge.accept_layout(cls.session.generation, results, keys)
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1400, 900)
        pump(300)
        cls.measured, cls.failures, cls.others, cls.empty = {}, [], set(), []
        cls.walk()

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    # finding and opening

    @classmethod
    def menus(cls):
        """Every popup menu of the window: the QObject children of its items (a popup is a child of the item that
        declares it) and of the window."""
        found, seen = [], set()
        candidates = list(cls.win.findChildren(QObject))
        for item in items(cls.win.contentItem()):
            try:
                candidates.extend(item.children())
            except RuntimeError:
                pass
        while candidates:
            o = candidates.pop()
            try:
                key = key_of(o)
                if key in seen or not o.inherits('QQuickMenu'):
                    continue
                seen.add(key)
                if o.metaObject().indexOfProperty('measuredWidth') < 0:
                    cls.others.add(o.metaObject().className())
                    continue
                found.append(o)
                candidates.extend(o.findChildren(QObject))          # its submenus (an Instantiator's, a child's)
            except RuntimeError:
                pass
        return found

    @staticmethod
    def entries(menu):
        listed = menu.property('contentItem').property('contentItem').childItems()
        return sorted((e for e in listed if e.isVisible() and e.height() > 0), key=lambda e: e.y())

    @classmethod
    def place(cls, menu):
        """At the top left of the window; a menu whose item is not shown (a submenu, whose item is its parent menu's
        entry) hangs from the window's content for the time of the measure. The item it had, to give back."""
        parent = menu.property('parent')
        before = parent
        if parent is None or not parent.isVisible() or not parent.isEnabled():     # R659: unreachable, it closes
            parent = cls.win.contentItem()
            menu.setProperty('parent', parent)
        spot = parent.mapFromScene(QPointF(200, 80))
        menu.setProperty('x', spot.x())
        menu.setProperty('y', spot.y())
        return before

    @classmethod
    def open_and_measure(cls, name, menu, place=True):
        before = cls.place(menu) if place else False
        if place:
            QMetaObject.invokeMethod(menu, 'open')
        pump(250)
        try:
            if cls.entries(menu):
                key, n = name, 2
                while key in cls.measured:
                    key, n = f'{name}#{n}', n + 1
                cls.measured[key] = cls.measure(key, menu)
            else:
                cls.empty.append(name)
        finally:
            QMetaObject.invokeMethod(menu, 'close')
            pump(120)
            if before is not False and before is not menu.property('parent'):
                menu.setProperty('parent', before)

    @classmethod
    def walk(cls):
        done = set()
        win = cls.win
        win.showPhase('model')
        pump(1500)
        # the plan's right button on the sub-field (what Plan.navigate does with the gesture «menu»)
        plan = max((i for i in items(win.contentItem()) if i.metaObject().indexOfProperty('panX') >= 0
                    and i.metaObject().indexOfMethod('navigate(QVariant)') >= 0),
                   key=lambda i: i.width() * i.height())
        pump(300)
        middle = QPointF(plan.width() / 2, plan.height() / 2)
        QMetaObject.invokeMethod(plan, 'fit')
        pump(200)
        QMetaObject.invokeMethod(plan, 'navigate', Q_ARG('QVariant', [{'kind': 'menu', 'x': middle.x(),
                                                                       'y': middle.y()}]))
        menu = win.findChild(QObject, 'planContextMenu')
        done.add(key_of(menu))
        cls.open_and_measure('planContextMenu', menu, place=False)
        # the project tree's right button on the building
        tree = next(i for i in items(win.contentItem()) if i.objectName() == 'project-tree-page')
        QMetaObject.invokeMethod(tree, 'openMenu', Q_ARG('QVariant', 'building'),
                                 Q_ARG('QVariant', cls.session.project.buildings[0].id),
                                 Q_ARG('QVariant', 40), Q_ARG('QVariant', 120))
        menu = win.findChild(QObject, 'project-tree-context-menu')
        done.add(key_of(menu))
        cls.open_and_measure('project-tree-context-menu', menu, place=False)
        # the bar of the menus shown (Alt), with its menus
        win.setProperty('menuOpen', True)
        pump(400)
        for phase in ('model', 'plant', 'production', 'economics'):
            win.showPhase(phase)
            pump(1200)
            view = win.findChild(QObject, 'sceneContextMenu')
            if view is not None and key_of(view) not in done:
                cls.session.select('building', cls.session.project.buildings[0].id)
                pump(300)
                viewport = win.findChild(QObject, 'viewport3d')
                actions = viewport.property('sceneBackend').property('contextActions')
                view.setProperty('actions', actions)
                done.add(key_of(view))
                cls.open_and_measure('sceneContextMenu', view)
            for menu in cls.menus():
                try:
                    if key_of(menu) in done:
                        continue
                    done.add(key_of(menu))
                    if menu.objectName() in ('planContextMenu', 'project-tree-context-menu', 'sceneContextMenu'):
                        continue
                    cls.open_and_measure(menu.objectName() or menu.property('title') or
                                         f'{menu.property("parent").metaObject().className()}', menu)
                except RuntimeError as error:          # a page let go while it was walked
                    if 'already deleted' not in str(error):
                        raise
        win.setProperty('menuOpen', False)

    # measuring

    @classmethod
    def measure(cls, name, menu):
        frame = menu.property('background')
        fx, fw = frame.mapToScene(QPointF(0, 0)).x(), frame.width()

        def at(item, x=0.0):
            return item.mapToScene(QPointF(x, 0)).x() - fx
        lefts, rights = [], []
        # the column of the marks is content only when an entry has a mark: an icon, a check, or one it can take
        # (a rule or a title shows none, whatever its `checked`)
        marked = any(e.property('iconName') or e.property('checkable') or e.property('checked')
                     for e in cls.entries(menu) if e.property('contentItem') is not None
                     and not e.property('rule') and not e.property('heading'))
        for e in cls.entries(menu):
            ground = e.property('background')
            content = e.property('contentItem')
            if content is None:             # not an entry (an item of the list being let go, in a long suite)
                continue
            rule = named(content, 'menuRule') if content.objectName() != 'menuRule' else content
            if e.metaObject().indexOfProperty('caption') < 0 and rule is None:
                cls.failures.append(f'{name}: an entry that is not M.MenuItem nor M.MenuSeparator '
                                    f'({e.metaObject().className()})')
                continue
            if rule is not None and rule.isVisible():
                left, right = at(rule), fw - at(rule, rule.width())
                if abs(left - right) > 1:
                    cls.failures.append(f'{name}: a rule {left:.1f} px in at the left, {right:.1f} at the right')
                continue
            if ground is not None:
                left, right = at(ground), fw - at(ground, ground.width())
                if abs(left - right) > 1:
                    cls.failures.append(f'{name}: the hover\'s grey {left:.1f} px in at the left, {right:.1f} at the right')
            mark, word, keys = named(content, 'menuMark'), named(content, 'menuText'), named(content, 'menuKeys')
            if marked and mark is not None and mark.isVisible() and mark.width() > 0:
                lefts.append(at(mark))
            if word is not None and word.isVisible():
                lefts.append(at(word))
                rights.append(at(word, min(word.property('implicitWidth'), word.width())))
            if keys is not None and keys.property('text'):
                rights.append(at(keys, keys.width()))
            arrow = e.property('arrow')
            if arrow is not None and arrow.isVisible():
                rights.append(at(arrow, arrow.width()))
        if not lefts or not rights:
            cls.failures.append(f'{name}: no menuText, menuMark, menuKeys or menuArrow in its entries')
            return None
        left, right = min(lefts), fw - max(rights)
        if abs(left - right) > 1:
            cls.failures.append(f'{name}: {left:.1f} px from the frame to the content at the left, '
                                f'{right:.1f} from the widest entry to the frame at the right')
        if not any(abs(left - step) <= 1 for step in design.Space.SCALE):
            cls.failures.append(f'{name}: a margin of {left:.1f} px, not a step of design.Space')
        return round(left, 1), round(right, 1)

    # the guards

    def test_every_menu_is_the_common_component(self):
        self.assertEqual(self.others, set(), 'popup menus made with another component')

    def test_every_menu_is_symmetric(self):
        self.assertEqual(self.failures, [], self.measured)

    def test_the_guard_has_opened_the_menus_of_the_program(self):
        names = set(self.measured)
        self.assertGreaterEqual(len(names), 20, sorted(names))
        for name in MUST:
            self.assertIn(name, names)
        # and submenus, named by their title
        self.assertTrue(names & {'Coordinates of this point', 'Phases', 'Panels', 'Darken the imagery'},
                        (sorted(names), self.empty))


class TextMenus(unittest.TestCase):
    def test_shared_text_menu_has_the_same_symmetric_margins(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtTest import QTest
        from quick.aiuti.text_scene import TextScene
        scene = TextScene()
        self.addCleanup(scene.doCleanups)
        root, window = scene.scene('TextField')
        root.forceActiveFocus()
        QTest.mouseClick(window, Qt.RightButton, pos=QPoint(25, 12))
        self.assertTrue(_setup.wait_for(lambda: scene.evaluate(root, 'textActions.menuActive'), 500))
        pump(250)
        menu = next(o for o in root.findChildren(QObject) if o.objectName() == 'textContextMenu')
        class Meter:
            entries = staticmethod(EveryMenu.entries)
            failures = []
        measured = EveryMenu.measure.__func__(Meter, 'textContextMenu', menu)
        self.assertEqual(Meter.failures, [], measured)


if __name__ == '__main__':
    unittest.main()
