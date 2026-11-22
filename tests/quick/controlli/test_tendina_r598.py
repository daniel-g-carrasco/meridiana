"""R598: the list of M.ComboBox is made at its first opening, and kept.

Every form of the Properties and of the results has many drop-downs, and each one made its list at birth (an M.Popup
with its frame, shadow, search field, list view and entries): 9-11 ms per drop-down measured off screen on 14/11/2026,
the largest share of the forms made ahead when a large model's project opens. Qt defers a ComboBox's `popup` until
something reads it; M.ComboBox reads it nowhere before it opens (its arrow, tooltip and wheel ask `listShown`), and the
list is a file of its own (ComboList.qml), since Qt makes a deferred object at once when it or a child of it has an
id in the ComboBox's file. What the person meets is the same: hover, focus and the wheel with the focus do not make
the list; the click, Space and Alt+Down open it with its entries and the current one checked; the keyboard walks it,
skips nothing that is enabled, and the choice arrives; closed and opened again it is the same list.
"""
import unittest

import _setup

from PySide6.QtCore import QObject, QPoint, QPointF, QUrl, Qt
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.gui.backend.controls import install_controls

OPTIONS = '''[{label: "Uno", value: "a"}, {label: "Due", value: "b"}, {label: "Tre", value: "c", enabled: false},
              {label: "Quattro", value: "d"}]'''


def setUpModule():
    _setup.keep_global_state()


def lists_of(combo):
    """The lists made for `combo`: the popups among its children that are not its tooltip."""
    return [o for o in combo.findChildren(QObject) if o.inherits('QQuickPopup') and not o.inherits('QQuickToolTip')]


def entries(popup):
    """The entries shown by the list, in order: (text, checked, enabled)."""
    view = next(o for o in popup.findChildren(QObject) if o.metaObject().className().startswith('QQuickListView'))
    items = [i for i in view.property('contentItem').childItems() if i.metaObject().className().startswith('MenuItem')]
    items.sort(key=lambda i: i.y())
    return [(i.property('text'), i.property('checked'), i.property('enabled')) for i in items]


class DropDownListOnDemand(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['tendina-test'])

    def scene(self, body):
        engine = QQmlEngine()
        install_controls(engine, dict(theme='light', reducedMotion=True))
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        component = QQmlComponent(engine)
        component.setData(('import QtQuick\nimport Meridiana.Controls as M\nItem { width: 400; height: 300\n'
                           + body + '\n}').encode(), QUrl())
        self.assertFalse(component.isError(), '\n'.join(e.toString() for e in component.errors()))
        root = component.create()
        self.assertIsInstance(root, QQuickItem, '\n'.join(e.toString() for e in component.errors()))
        root.setParent(engine)
        window = QQuickWindow()
        window.resize(400, 300)
        root.setParentItem(window.contentItem())
        window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(window))

        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
            self.assertEqual(warnings, [])
        self.addCleanup(cleanup)
        return root.findChild(QObject, 'combo'), window

    @staticmethod
    def middle(combo):
        p = combo.mapToScene(QPointF(combo.width() / 2, combo.height() / 2))
        return QPoint(int(p.x()), int(p.y()))

    def test_made_at_the_first_opening_then_kept_and_used_as_before(self):
        combo, window = self.scene(f'''M.ComboBox {{ objectName: "combo"; x: 20; y: 20; width: 180; tip: "Il tipo"
            options: {OPTIONS}; value: "b"; property string picked: ""
            onChosen: v => {{ picked += v; value = v }} }}''')
        self.assertEqual(lists_of(combo), [], 'the list is not made at birth')
        self.assertEqual(combo.property('displayText'), 'Due')
        # the pointer over it and the focus (its tooltip, its arrow) do not make the list; the wheel with the focus
        # steps over the enabled options without it
        QTest.mouseMove(window, self.middle(combo))
        self.assertTrue(_setup.wait_for(lambda: combo.property('hovered'), 2000))
        combo.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        self.assertEqual(combo.property('picked'), 'd', 'Down skips the disabled option')
        QTest.keyClick(window, Qt.Key.Key_Up)
        self.assertEqual(combo.property('picked'), 'db')
        self.assertEqual(lists_of(combo), [], 'hover, focus and the arrows do not make the list')
        # the click opens it: its entries, the current one checked, the disabled one disabled
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=self.middle(combo))
        made = lists_of(combo)
        self.assertEqual(len(made), 1)
        popup = made[0]
        self.assertTrue(_setup.wait_for(lambda: popup.property('visible') and len(entries(popup)) == 4, 3000))
        self.assertTrue(combo.property('listShown'))
        self.assertEqual(entries(popup), [('Uno', False, True), ('Due', True, True), ('Tre', False, False),
                                          ('Quattro', False, True)])
        # the keyboard walks the list from the current entry and the choice arrives
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(combo.property('picked'), 'dbd')
        self.assertTrue(_setup.wait_for(lambda: not popup.property('visible'), 3000))
        self.assertFalse(combo.property('listShown'))
        # opened again (Space, Alt+Down), it is the same list, and Esc closes it without a choice
        QTest.keyClick(window, Qt.Key.Key_Space)
        self.assertTrue(_setup.wait_for(lambda: popup.property('visible'), 3000))
        self.assertEqual(lists_of(combo), [popup])
        self.assertTrue(_setup.wait_for(lambda: entries(popup)[3][1], 3000), 'the current one is checked')
        QTest.keyClick(window, Qt.Key.Key_Escape)
        self.assertTrue(_setup.wait_for(lambda: not popup.property('visible'), 3000))
        QTest.keyClick(window, Qt.Key.Key_Down, Qt.KeyboardModifier.AltModifier)
        self.assertTrue(_setup.wait_for(lambda: popup.property('visible'), 3000))
        self.assertEqual(lists_of(combo), [popup])
        QTest.keyClick(window, Qt.Key.Key_Escape)
        self.assertEqual(combo.property('picked'), 'dbd')

    def test_searchable_list_filters_when_made(self):
        combo, window = self.scene(f'''M.ComboBox {{ objectName: "combo"; x: 20; y: 20; width: 180; searchable: true
            searchHint: "Cerca"; options: {OPTIONS}; value: "a"; property var picked: null; onChosen: v => picked = v }}''')
        self.assertEqual(lists_of(combo), [])
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=self.middle(combo))
        popup = lists_of(combo)[0]
        self.assertTrue(_setup.wait_for(lambda: popup.property('visible') and len(entries(popup)) == 4, 3000))
        for char in 'qua':
            QTest.keyClick(window, char)
        self.assertTrue(_setup.wait_for(lambda: [e[0] for e in entries(popup)] == ['Quattro'], 3000))
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(combo.property('picked'), 'd')

    def test_qt_model_opens_and_picks_by_the_pointer(self):
        combo, window = self.scene('''M.ComboBox { objectName: "combo"; x: 20; y: 20; width: 180
            model: ["First", "Second", "Third"]; property int activations: 0; onActivated: activations++ }''')
        self.assertEqual(lists_of(combo), [])
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=self.middle(combo))
        popup = lists_of(combo)[0]
        self.assertTrue(_setup.wait_for(lambda: popup.property('visible') and len(entries(popup)) == 3, 3000))
        view = next(o for o in popup.findChildren(QObject) if o.metaObject().className().startswith('QQuickListView'))
        third = max((i for i in view.property('contentItem').childItems()
                     if i.metaObject().className().startswith('MenuItem')), key=lambda i: i.y())
        p = third.mapToScene(QPointF(third.width() / 2, third.height() / 2))
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(int(p.x()), int(p.y())))
        self.assertEqual(combo.property('currentIndex'), 2)
        self.assertEqual(combo.property('activations'), 1)
        self.assertTrue(_setup.wait_for(lambda: not popup.property('visible'), 3000))


if __name__ == '__main__':
    unittest.main()
