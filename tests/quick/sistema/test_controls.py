"""Real Qt events on shared controls: R364, R379, R394, R395."""
import time
import unittest

import _setup

from PySide6.QtCore import QAbstractListModel, QMetaObject, QObject, QPoint, QSize, QUrl, Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

from meridiana.quick.backend.controls import IconProvider, install_controls
from meridiana.quick.capture import grab


class ControlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['controls-test'])

    def scene(self, body, context=None):
        engine = QQmlEngine()
        install_controls(engine)
        for key, value in (context or {}).items():
            engine.rootContext().setContextProperty(key, value)
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        component = QQmlComponent(engine)
        component.setData(('import QtQuick\nimport Meridiana.Controls as M\n' + body).encode(), QUrl())
        self.assertFalse(component.isError(), '\n'.join(e.toString() for e in component.errors()))
        root = component.create()
        self.assertIsInstance(root, QQuickItem, '\n'.join(e.toString() for e in component.errors()))
        root.setParent(engine)
        window = QQuickWindow()
        window.resize(600, 400)
        root.setParentItem(window.contentItem())
        window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        QTest.qWait(30)
        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
            self.assertEqual(warnings, [])
        self.addCleanup(cleanup)
        return root, window

    @staticmethod
    def visual_items(root):
        for child in root.childItems():
            yield child
            yield from ControlsTest.visual_items(child)

    def test_button_keyboard_and_disabled(self):
        root, window = self.scene('''M.Button { width: 140; text: "Run"
            property int count: 0; onClicked: count++; focus: true }''')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Space)
        self.assertEqual(root.property('count'), 1)
        root.setEnabled(False)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(40, 12))
        self.assertEqual(root.property('count'), 1)

    def test_number_field_italian_commit_and_validation(self):
        root, window = self.scene('''M.NumberField { width: 180; value: 12.5
            minimum: 0; maximum: 100; unit: "kW"; decimals: 2 }''')
        self.assertEqual(root.property('text'), '12,50')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        for char in '27,75':
            QTest.keyClick(window, char)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(root.property('value'), 27.75)
        root.setProperty('text', '101,00')
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(root.property('value'), 27.75)
        self.assertFalse(root.property('acceptableInput'))

    def test_initial_types_load(self):
        for name in ('Label', 'Icon', 'Button', 'ToolButton', 'SplitButton', 'MenuItem',
                     'TextField', 'NumberField', 'CheckBox', 'Card', 'Section', 'Pill'):
            with self.subTest(name=name):
                self.scene('M.' + name + ' { width: 200 }')

    def test_remaining_types_load(self):
        for name in ('ComboBox', 'Segments', 'Tabs', 'ScrollBar', 'SplitHandle',
                     'Table', 'Tree', 'List', 'EmptyState', 'ProgressBar'):
            with self.subTest(name=name):
                self.scene('M.' + name + ' { width: 300; height: 120 }')
        self.scene('Item { M.Dialog { title: "Confirm" } M.ToolTip { text: "Help" } }')

    def test_segments_keyboard_selection(self):
        root, window = self.scene('''M.Segments { width: 300
            model: [{text: "First", id: "a"}, {text: "Second", id: "b"}]
            property int chosen: -1; onActivated: index => chosen = index }''')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Right)
        self.assertEqual(root.property('currentIndex'), 1)
        self.assertEqual(root.property('chosen'), 1)

    def test_table_row_selection_and_total_stays_fixed(self):
        root, window = self.scene('''M.Table { width: 550; height: 220
            columns: [{title: "Module", key: "name"}, {title: "Power", unit: "kW", key: "power"}]
            model: Array.from({length: 40}, (_, i) => ({name: "Row " + i, power: i}))
            total: ({name: "Total", power: 780})
            property int chosen: -1; onRowActivated: index => chosen = index }''')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(90, 65))
        self.assertEqual(root.property('currentIndex'), 0)
        self.assertEqual(root.property('chosen'), 0)
        root.forceActiveFocus()
        QTest.qWait(30)
        before = grab(window)
        QTest.keyClick(window, Qt.Key.Key_End)
        self.assertEqual(root.property('currentIndex'), 39)
        footer = root.findChild(QQuickItem, 'tableTotal')
        self.assertEqual(footer.y() + footer.height(), root.height())
        QTest.qWait(30)
        after = grab(window)
        ratio = before.devicePixelRatio()
        area = (int(4*ratio), int((footer.y()+4)*ratio), int((root.width()-8)*ratio), int((footer.height()-8)*ratio))
        self.assertEqual(before.copy(*area), after.copy(*area))

    def test_split_menu_keyboard_and_main_command(self):
        root, window = self.scene('''M.SplitButton { width: 140; height: 55; text: "Building"; iconName: "building"
            model: [{text: "First"}, {text: "Second"}, {text: "Disabled", enabled: false}]
            property int mainCount: 0; property int choice: -1
            onClicked: mainCount++; onChosen: index => choice = index }''')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(40, 20))
        self.assertEqual(root.property('mainCount'), 1)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(133, 20))
        QTest.qWait(40)
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(root.property('choice'), 0)
        self.assertEqual(root.property('mainCount'), 1)

    def test_combo_keyboard_selects_and_escape_closes(self):
        root, window = self.scene('''M.ComboBox { width: 180; model: ["First", "Second", "Third"] }''')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        self.assertEqual(root.property('currentIndex'), 1)
        QTest.keyClick(window, Qt.Key.Key_Space)
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(root.property('currentIndex'), 2)
        QTest.keyClick(window, Qt.Key.Key_Space)
        QTest.keyClick(window, Qt.Key.Key_Escape)
        self.assertEqual(root.property('currentIndex'), 2)

    def test_tree_expands_and_selects_by_keys(self):
        root, window = self.scene('''M.Tree { width: 300; height: 220
            model: [{text: "Building", id: "b", children: [{text: "Roof", id: "r"}]}]
            property string chosen: ""; onActivated: node => chosen = node.id }''')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Right)
        self.assertEqual(root.property('count'), 2)
        QTest.keyClick(window, Qt.Key.Key_Down)
        self.assertEqual(root.property('chosen'), 'r')
        QTest.keyClick(window, Qt.Key.Key_Up)
        QTest.keyClick(window, Qt.Key.Key_Left)
        self.assertEqual(root.property('count'), 1)

    def test_tooltips_have_only_opacity_and_every_one_waits(self):
        # R550 (Daniel 08/11/2026): the next tooltip waits as the first did; no warm hand-off (R468) any more
        root, window = self.scene('''Row { spacing: 20
            M.Button { width: 120; text: "First"; tip: "First help" }
            M.Button { x: 140; width: 120; text: "Second"; tip: "Second help" }
        }''')
        tips = root.findChildren(QObject, 'controlTip')
        self.assertEqual(len(tips), 2)
        QTest.mouseMove(window, QPoint(50, 14))
        QTest.qWait(400)
        self.assertFalse(tips[0].property('visible'), 'R468: the first tooltip waits 700 ms, as QToolTip')
        QTest.qWait(500)
        self.assertTrue(tips[0].property('visible'))
        QTest.mouseMove(window, QPoint(180, 14))
        start = time.monotonic()
        self.assertTrue(_setup.wait_for(lambda: tips[1].property('visible'), 3000))
        self.assertGreater(time.monotonic() - start, .65, 'R550: the next one waits too')
        QTest.qWait(110)
        self.assertEqual(tips[1].property('opacity'), 1)

    def test_focus_moves_by_tab_and_checkbox_uses_space(self):
        root, window = self.scene('''Row {
            M.Button { objectName: "first"; text: "Save" }
            M.CheckBox { objectName: "check"; text: "Shadows" }
            M.TextField { objectName: "field" }
        }''')
        root.findChild(QQuickItem, 'first').forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Tab)
        checkbox = root.findChild(QQuickItem, 'check')
        self.assertTrue(checkbox.hasActiveFocus())
        QTest.keyClick(window, Qt.Key.Key_Space)
        self.assertTrue(checkbox.property('checked'))
        QTest.keyClick(window, Qt.Key.Key_Tab)
        self.assertTrue(root.findChild(QQuickItem, 'field').hasActiveFocus())

    def test_split_hover_marks_both_parts_and_pointer_part_more(self):
        root, window = self.scene('M.SplitButton { width: 150; height: 55; text: "Building"; iconName: "building" }')
        def lightness(x):
            image = grab(window)
            ratio = image.devicePixelRatio()
            return image.pixelColor(int((x+.5)*ratio), int(7.5*ratio)).lightness()
        QTest.mouseMove(window, QPoint(350, 250))
        QTest.qWait(30)
        plain = lightness(140)
        QTest.mouseMove(window, QPoint(40, 20))
        QTest.qWait(30)
        self.assertLess(lightness(140), plain)
        self.assertLess(lightness(10), lightness(140))
        QTest.mouseMove(window, QPoint(142, 20))
        QTest.qWait(30)
        self.assertLess(lightness(140), lightness(10))

    def test_card_close_and_empty_action(self):
        root, window = self.scene('''M.Card { width: 400; height: 250; title: "Results"; closable: true
            property int closes: 0; property int actions: 0; onClosed: closes++
            M.EmptyState { anchors.fill: parent; title: "No data"; actionText: "Compute"; onTriggered: actions++ }
        }''')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(381, 15))
        self.assertEqual(root.property('closes'), 1)
        # Locate the actual action's bounds instead of assuming a text-dependent y.
        buttons = [item for item in root.findChildren(QQuickItem) if item.property('text') == 'Compute'
                   and item.metaObject().indexOfSignal('clicked()') >= 0]
        self.assertEqual(len(buttons), 1)
        point = buttons[0].mapToScene(buttons[0].boundingRect().center()).toPoint()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(root.property('actions'), 1)

    def test_dialog_escape_and_accept(self):
        root, window = self.scene('''Item { width: 500; height: 300
            property int accepts: 0; property int rejects: 0
            M.Button { text: "Open"; onClicked: dialog.open() }
            M.Dialog { id: dialog; objectName: "dialog"; title: "Confirm"; acceptText: "OK"; rejectText: "Cancel"
                x: 30; y: 60; onAccepted: parent.accepts++; onRejected: parent.rejects++
                contentItem: M.Label { text: "Details" }
            }
        }''')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(20, 12))
        QTest.keyClick(window, Qt.Key.Key_Escape)
        self.assertEqual(root.property('rejects'), 1)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(20, 12))
        dialog = root.findChild(QObject, 'dialog')
        action = next(item for item in dialog.findChildren(QQuickItem) if item.property('text') == 'OK'
                      and item.metaObject().indexOfSignal('clicked()') >= 0)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=action.mapToScene(action.boundingRect().center()).toPoint())
        self.assertEqual(root.property('accepts'), 1)

    def test_table_accepts_live_qabstractlistmodel_roles(self):
        class Model(QAbstractListModel):
            def __init__(self):
                super().__init__()
                self.entries = ['Roof A', 'Roof B']
            def rowCount(self, parent=None):
                return 0 if parent is not None and parent.isValid() else len(self.entries)
            def roleNames(self):
                return {Qt.ItemDataRole.UserRole + 1: b'name'}
            def data(self, index, role):
                if index.isValid() and role == Qt.ItemDataRole.UserRole + 1:
                    return self.entries[index.row()]
                return None
        model = Model()
        root, window = self.scene('''M.Table { width: 500; height: 220; model: liveModel
            columns: [{title: "Roof", key: "name"}] }''', {'liveModel': model})
        self.assertEqual(root.property('count'), 2)
        self.assertTrue(any(item.property('text') == 'Roof B' for item in self.visual_items(root)))
        model.entries[1] = 'Changed roof'
        model.dataChanged.emit(model.index(1), model.index(1), [Qt.ItemDataRole.UserRole + 1])
        QTest.qWait(20)
        self.assertTrue(any(item.property('text') == 'Changed roof' for item in self.visual_items(root)))
        self.addCleanup(lambda: model)

    def test_split_handle_drag_changes_panel_width(self):
        root, window = self.scene('''import QtQuick.Controls.Basic as Base
            Base.SplitView { width: 500; height: 220; orientation: Qt.Horizontal
                handle: M.SplitHandle { }
                Rectangle { objectName: "left"; Base.SplitView.preferredWidth: 180; Base.SplitView.minimumWidth: 80 }
                Rectangle { Base.SplitView.fillWidth: true }
            }''')
        left = root.findChild(QQuickItem, 'left')
        self.assertEqual(left.width(), 180)
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(183, 100))
        QTest.mouseMove(window, QPoint(243, 100), 30)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(243, 100))
        QTest.qWait(30)
        self.assertGreater(left.width(), 220)

    def test_progress_remains_visible_with_reduced_motion_and_returns_to_value(self):
        root, window = self.scene('''import Meridiana.Theme
            M.ProgressBar { width: 240; value: 0.5; indeterminate: true
                function reduce() { Theme.configure({reducedMotion: true}) }
            }''')
        fill = root.findChild(QQuickItem, 'progressFill')
        QTest.qWait(120)
        QMetaObject.invokeMethod(root, 'reduce')
        QTest.qWait(20)
        self.assertEqual(fill.x(), 80)
        self.assertEqual(fill.width(), 80)
        root.setProperty('indeterminate', False)
        QTest.qWait(20)
        self.assertEqual(fill.x(), 0)
        self.assertEqual(fill.width(), 120)

    def test_segments_keep_external_binding_after_user_activation(self):
        root, window = self.scene('''Item { width: 400; height: 200
            property int externalIndex: 0
            M.Segments { objectName: "segments"; width: 300
                model: [{text: "Base"}, {text: "Variant"}, {text: "New"}]
                currentIndex: parent.externalIndex
                onActivated: index => parent.externalIndex = index
            }
        }''')
        segments = root.findChild(QQuickItem, 'segments')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(150, 14))
        self.assertEqual(root.property('externalIndex'), 1)
        root.setProperty('externalIndex', 2)
        self.assertEqual(segments.property('currentIndex'), 2)

    def test_section_collapses_and_expands_with_real_clicks(self):
        root, window = self.scene('''M.Section { width: 300; title: "Properties"
            M.TextField { text: "Roof" }
            M.NumberField { value: 12.5 }
        }''')
        expanded_height = root.height()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(90, 14))
        QTest.qWait(400)
        self.assertFalse(root.property('expanded'))
        self.assertLess(root.height(), expanded_height)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(90, 14))
        QTest.qWait(400)
        self.assertTrue(root.property('expanded'))
        self.assertEqual(root.height(), expanded_height)

    def test_segment_animation_keeps_selection_painted_without_extra_windows(self):
        root, window = self.scene('''M.Segments { width: 360
            model: [{text: "First"}, {text: "Second"}, {text: "Third"}]
        }''')
        before_windows = len(QGuiApplication.topLevelWindows())
        raised = root.findChild(QQuickItem, 'segmentSelection')
        expected = QColor(root.parent()._meridiana_theme_tokens.colors['panel'])
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(300, 14))
        QTest.mouseMove(window, QPoint(500, 300))
        positions = []
        for _ in range(18):
            QTest.qWait(16)
            image = grab(window)
            point = raised.mapToScene(raised.boundingRect().topLeft())
            ratio = image.devicePixelRatio()
            color = image.pixelColor(int((point.x()+10.5)*ratio), int((point.y()+3.5)*ratio))
            self.assertEqual(color, expected)
            positions.append(raised.x())
        self.assertGreater(len(set(positions)), 1)
        self.assertEqual(len(QGuiApplication.topLevelWindows()), before_windows)

    def test_status_icons_share_widgets_symbols_and_render_nonempty(self):
        provider = IconProvider()
        for name in ('fail', 'warn', 'info', 'ok'):
            for theme in ('light', 'dark'):
                with self.subTest(name=name, theme=theme):
                    size = QSize()
                    image = provider.requestImage(f'symbol:{name}/%23000000/{theme}/on', size, QSize(32, 32))
                    self.assertEqual(size, QSize(32, 32))
                    opaque = sum(image.pixelColor(x, y).alpha() > 0 for x in range(32) for y in range(32))
                    self.assertGreater(opaque, 300)
        self.scene('M.Icon { iconName: "symbol:warn"; width: 24; height: 24 }')
