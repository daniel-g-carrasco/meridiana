"""Real control states, compared with the authoritative Widgets palette and geometry."""
import unittest

from PySide6.QtCore import QPoint, QUrl, Qt
from PySide6.QtGui import QColor
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana.quick.backend.controls import install_controls
from meridiana.quick.capture import grab


class FidelityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['control-fidelity'])

    def scene(self, body, dark=False):
        engine = QQmlEngine()
        theme = install_controls(engine, dict(theme='dark' if dark else 'light', reducedMotion=True))
        errors = []
        engine.warnings.connect(lambda messages: errors.extend(e.toString() for e in messages))
        component = QQmlComponent(engine)
        component.setData(('import QtQuick\nimport Meridiana.Theme\nimport Meridiana.Controls as M\n' + body).encode(), QUrl())
        self.assertFalse(component.isError(), '\n'.join(e.toString() for e in component.errors()))
        root = component.create()
        self.assertIsInstance(root, QQuickItem)
        root.setParent(engine)
        window = QQuickWindow()
        window.setColor(QColor(theme.colors['panel']))
        window.resize(640, 460)
        root.setParentItem(window.contentItem())
        window.show()
        window.requestActivate()
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        # Offscreen reuses the global cursor position across successive windows.
        # An actual enter/leave pair clears hover even at the same final point.
        QTest.mouseMove(window, QPoint(10, 10))
        QTest.mouseMove(window, QPoint(620, 440))
        QTest.qWait(40)

        def cleanup():
            window.close()
            delete(root)
            delete(window)
            delete(engine)
            self.assertEqual(errors, [])
        self.addCleanup(cleanup)
        return root, window, theme

    @staticmethod
    def pixel(window, x, y):
        image = grab(window)
        dpr = image.devicePixelRatio()
        return image.pixelColor(int((x + .5) * dpr), int((y + .5) * dpr)).name()

    def test_field_border_only_on_hover_and_focus(self):
        for dark in (False, True):
            with self.subTest(dark=dark):
                field, window, theme = self.scene('M.TextField { width: 180; text: "Nome" }', dark)
                self.assertEqual(self.pixel(window, 90, 0), theme.colors['field'])
                QTest.mouseMove(window, QPoint(90, 14))
                QTest.qWait(30)
                self.assertEqual(self.pixel(window, 90, 0), theme.colors['field_line'])
                field.forceActiveFocus(Qt.FocusReason.TabFocusReason)
                QTest.qWait(30)
                self.assertEqual(self.pixel(window, 90, 0), theme.colors['accent'])

    def test_icons_keep_widgets_edges_at_screen_scale(self):
        from itertools import product
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QIcon, QImage, QPainter
        from meridiana import theme_colors
        from meridiana.ui.icons import icon
        from meridiana.ui.theme import qpalette

        palette = QApplication.palette()

        # A second DPR multiplication resamples the SVG and blurs its edges.
        for dark in (False, True):
            for name, side, enabled in product(('building', 'select', 'compute'), (16, 20, 24), (True, False)):
                with self.subTest(dark=dark, name=name, size=side, enabled=enabled):
                    self.addCleanup(QApplication.setPalette, palette)
                    root, window, theme = self.scene(
                        f'M.Icon {{ width: {side}; height: {side}; name: "{name}"; enabled: {str(enabled).lower()} }}', dark)
                    QApplication.setPalette(qpalette(theme_colors.palette(theme.colors, dark)))
                    actual = grab(window)
                    ratio = actual.devicePixelRatio()
                    extent = round(side * ratio)
                    expected = QImage(extent, extent, QImage.Format.Format_ARGB32_Premultiplied)
                    expected.setDevicePixelRatio(ratio)
                    expected.fill(QColor(theme.colors['panel']))
                    painter = QPainter(expected)
                    icon(name, theme.colors['text']).paint(painter, QRect(0, 0, side, side),
                                                          Qt.AlignmentFlag.AlignCenter,
                                                          QIcon.Mode.Normal if enabled else QIcon.Mode.Disabled)
                    painter.end()
                    difference = max(abs(a - b)
                                     for y in range(extent) for x in range(extent)
                                     for a, b in zip(actual.pixelColor(x, y).getRgb()[:3],
                                                     expected.pixelColor(x, y).getRgb()[:3], strict=True))
                    self.assertLessEqual(difference, 1)
                    self.doCleanups()

    def test_toolbar_icon_position_and_edges_match_widgets(self):
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QImage, QPainter
        from meridiana.ui.icons import icon

        # Measured from the real QToolButton in phasebar, 64 by 52, Plex medium.
        # Odd widths retain the same integral left edge, as QWidget geometry does.
        for mode, x, y, side in (('under', 20, 4, 24), ('beside', 7, 18, 16), ('icons', 21, 15, 22)):
            for width in (64, 65):
                with self.subTest(mode=mode, width=width):
                    root, window, theme = self.scene(
                        f'M.ToolButton {{ width: {width}; height: 52; text: "Edificio"; iconName: "building"; mode: "{mode}" }}')
                    actual = grab(window)
                    ratio = actual.devicePixelRatio()
                    expected = QImage(round(width * ratio), round(52 * ratio), QImage.Format.Format_ARGB32_Premultiplied)
                    expected.setDevicePixelRatio(ratio)
                    expected.fill(QColor(theme.colors['panel']))
                    painter = QPainter(expected)
                    icon('building', theme.colors['text']).paint(painter, QRect(x, y, side, side))
                    painter.end()
                    difference = max(abs(a - b)
                                     for py in range(round(y * ratio), round((y + side) * ratio))
                                     for px in range(round(x * ratio), round((x + side) * ratio))
                                     for a, b in zip(actual.pixelColor(px, py).getRgb()[:3],
                                                     expected.pixelColor(px, py).getRgb()[:3], strict=True))
                    self.assertLessEqual(difference, 1)
                    self.doCleanups()

    def test_field_takes_focus_on_pointer_press(self):
        field, window, theme = self.scene('M.TextField { width: 180; text: "Nome" }')
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(70, 14))
        QTest.qWait(20)
        self.assertTrue(field.hasActiveFocus())
        self.assertEqual(self.pixel(window, 90, 0), theme.colors['accent'])
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(70, 14))

    def test_tab_into_field_selects_text_like_line_edit(self):
        root, window, theme = self.scene('''Row {
            M.Button { objectName: "first"; text: "Salva" }
            M.TextField { objectName: "field"; width: 180; text: "Capannone" }
        }''')
        root.findChild(QQuickItem, 'first').forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Tab)
        field = root.findChild(QQuickItem, 'field')
        self.assertTrue(field.hasActiveFocus())
        self.assertEqual(field.property('selectedText'), 'Capannone')

    def test_disabled_button_has_no_ground(self):
        root, window, theme = self.scene('M.Button { width: 120; text: "Salva"; enabled: false }')
        self.assertEqual(self.pixel(window, 60, 4), theme.colors['panel'])

    def test_narrow_field_returns_to_start_when_focus_leaves(self):
        root, window, theme = self.scene('''Row {
            M.TextField { objectName: "field"; width: 80; text: "non indicata"
                property real beginningX: { const cursor = cursorRectangle; return positionToRectangle(0).x }
            }
            M.Button { objectName: "next"; text: "Salva" }
        }''')
        field = root.findChild(QQuickItem, 'field')
        field.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_End)
        self.assertLess(field.property('beginningX'), 8)
        root.findChild(QQuickItem, 'next').forceActiveFocus()
        QTest.qWait(20)
        # TextInput reports the text origin without the control's left padding.
        self.assertEqual(field.property('beginningX'), 0)

    def test_push_button_checked_ground_and_mouse_focus_match_qss(self):
        root, window, theme = self.scene('M.Button { width: 120; text: "Salva"; checkable: true; checked: true }')
        self.assertEqual(self.pixel(window, 60, 4), theme.colors['field'])
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(60, 14))
        QTest.qWait(30)
        self.assertTrue(root.hasActiveFocus())
        self.assertEqual(self.pixel(window, 60, 0), theme.colors['accent'])

    def test_checkbox_reserves_focus_and_checked_ground(self):
        root, window, theme = self.scene('M.CheckBox { width: 200; text: "Ombre"; checked: true }')
        indicator = root.property('indicator')
        self.assertEqual(indicator.width(), 22)
        self.assertEqual(self.pixel(window, 6, 11), theme.colors['select_bg'])

    def test_section_draws_header_and_keeps_closed_children_out_of_tab(self):
        root, window, theme = self.scene('''M.Section { width: 300; title: "Sito"
            M.TextField { width: parent.width; text: "Nome" }
        }''')
        self.assertEqual(self.pixel(window, 240, 8), theme.colors['line_soft'])
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(120, 12))
        QTest.qWait(30)
        self.assertFalse(root.property('expanded'))
        self.assertLess(root.height(), 35)

    def test_tooltip_width_and_corner_match_widgets(self):
        root, window, theme = self.scene('''Item { width: 600; height: 400
            M.ToolTip { objectName: "tip"; text: "Salva (Ctrl+S)\\nConserva la copia precedente e salva tutte le modifiche al progetto nella cartella scelta."; visible: true; delay: 0 }
        }''')
        QTest.qWait(40)
        from PySide6.QtCore import QObject
        tip = root.findChild(QObject, 'tip')
        self.assertLessEqual(tip.property('width'), 340)
        self.assertEqual(tip.property('background').property('radius'), 4)

    def test_slider_keyboard_and_track(self):
        slider, window, theme = self.scene('M.Slider { width: 240; from: 0; to: 100; value: 50; stepSize: 1 }')
        slider.forceActiveFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(window, Qt.Key.Key_Right)
        self.assertEqual(slider.property('value'), 51)
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(122, 11))
        QTest.mouseMove(window, QPoint(210, 11))
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(210, 11))
        self.assertGreater(slider.property('value'), 80)

    def test_slider_track_click_steps_one_page_like_qslider(self):
        slider, window, theme = self.scene('M.Slider { width: 240; from: 0; to: 100; value: 50; stepSize: 1 }')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(25, 11))
        self.assertEqual(slider.property('value'), 40)
        QTest.keyClick(window, Qt.Key.Key_PageDown)
        self.assertEqual(slider.property('value'), 30)
        QTest.keyClick(window, Qt.Key.Key_Home)
        self.assertEqual(slider.property('value'), 0)
        QTest.keyClick(window, Qt.Key.Key_End)
        self.assertEqual(slider.property('value'), 100)

    def test_slider_held_track_stops_at_pointer_like_qslider(self):
        slider, window, theme = self.scene('M.Slider { width: 240; from: 0; to: 100; value: 50; stepSize: 1 }')
        QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(180, 11))
        self.assertEqual(slider.property('value'), 60)
        QTest.qWait(850)
        self.assertEqual(slider.property('value'), 77)
        QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(180, 11))

    def test_list_reserves_thumb_room_and_thumb_is_not_clipped(self):
        root, window, theme = self.scene('''M.List { width: 300; height: 150
            model: Array.from({length: 40}, (_, i) => "Riga " + i)
            property real viewportWidth: view.width
        }''')
        self.assertEqual(root.property('viewportWidth'), 288)
        # The bar's ink is in the reserved room, outside the clipped viewport.
        self.assertEqual(self.pixel(window, 294, 18), theme.colors['line'])

    def test_lists_select_on_press_before_release_like_widgets(self):
        for control, model in (('List', '["Capannone", "Uffici"]'),
                               ('Tree', '[{id:"a",text:"Capannone"},{id:"b",text:"Uffici"}]'),
                               ('Table', '[{name:"Capannone"},{name:"Uffici"}]')):
            with self.subTest(control=control):
                root, window, theme = self.scene(f'M.{control} {{ width: 300; height: 100; model: {model} }}')
                point = QPoint(50, 62 if control == 'Table' else 10)
                QTest.mousePress(window, Qt.MouseButton.LeftButton, pos=point)
                self.assertEqual(root.property('currentIndex'), 0)
                QTest.mouseRelease(window, Qt.MouseButton.LeftButton, pos=point)

    def test_count_pill_toggles_and_preserves_zero_width(self):
        pill, window, theme = self.scene('M.Pill { variant: "count"; level: "warn"; text: "12" }')
        width = pill.width()
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(14, 12))
        self.assertTrue(pill.property('checked'))
        pill.setProperty('text', '0')
        self.assertEqual(width, pill.width())

    def test_dialog_return_accepts_default_button(self):
        from PySide6.QtCore import QObject, QMetaObject
        root, window, theme = self.scene('''Item { width: 500; height: 300; property bool accepted: false
            M.Dialog { objectName: "dialog"; acceptText: "Conferma"; rejectText: "Annulla"
                onAccepted: parent.accepted = true
                contentItem: M.Label { text: "Confermare?" }
            }
        }''')
        dialog = root.findChild(QObject, 'dialog')
        QMetaObject.invokeMethod(dialog, 'open')
        QTest.qWait(30)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertTrue(root.property('accepted'))

    def test_number_arrows_are_live_and_clamped(self):
        field, window, theme = self.scene('M.NumberField { width: 180; minimum: 0; maximum: 2; value: 1; decimals: 1 }')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(169, 8))
        self.assertEqual(field.property('value'), 2)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(169, 8))
        self.assertEqual(field.property('value'), 2)
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(169, 21))
        self.assertEqual(field.property('value'), 1)

    def test_menu_shortcuts_submenu_separator_and_keyboard(self):
        from PySide6.QtCore import QObject, QMetaObject
        root, window, theme = self.scene('''Item { width: 600; height: 400; property int invoked: 0
            M.Menu { id: menu; objectName: "menu"; x: 20; y: 20
                M.MenuItem { text: "Salva"; shortcutText: "Ctrl+S" }
                M.MenuSeparator {}
                M.Menu { title: "Altre viste"; objectName: "sub"
                    M.MenuItem { text: "Pianta"; onTriggered: invoked++ }
                }
            }
        }''')
        menu = root.findChild(QObject, 'menu')
        QMetaObject.invokeMethod(menu, 'open')
        QTest.qWait(30)
        QTest.keyClick(window, Qt.Key.Key_Down)
        self.assertEqual(menu.property('currentIndex'), 0)
        # QMenu highlights keyboard selection with the hover ground, without an accent frame.
        self.assertNotEqual(self.pixel(window, 65, 24), theme.colors['accent'])
        QTest.keyClick(window, Qt.Key.Key_Down)
        self.assertEqual(menu.property('currentIndex'), 2)
        QTest.keyClick(window, Qt.Key.Key_Right)
        QTest.qWait(30)
        self.assertTrue(root.findChild(QObject, 'sub').property('visible'))
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(root.property('invoked'), 1)

    def test_submenu_pointer_waits_then_opens_and_escape_closes(self):
        from PySide6.QtCore import QObject, QMetaObject
        root, window, theme = self.scene('''Item { width: 600; height: 400
            property var entry: menu.itemAt(0)
            M.Menu { id: menu; objectName: "menu"; x: 20; y: 20
                M.Menu { title: "Viste"; objectName: "sub"; M.MenuItem { text: "Pianta" } }
            }
        }''')
        QMetaObject.invokeMethod(root.findChild(QObject, 'menu'), 'open')
        QTest.qWait(30)
        entry = root.property('entry')
        point = entry.mapToScene(entry.boundingRect().center()).toPoint()
        QTest.mouseMove(window, point)
        QTest.qWait(80)
        self.assertFalse(root.findChild(QObject, 'sub').property('visible'))
        QTest.qWait(250)
        self.assertTrue(root.findChild(QObject, 'sub').property('visible'))
        QTest.keyClick(window, Qt.Key.Key_Escape)
        self.assertFalse(root.findChild(QObject, 'sub').property('visible'))

    def test_tooltip_above_pointer_at_bottom_and_stays_still(self):
        from PySide6.QtCore import QObject
        root, window, theme = self.scene('''Item { width: 640; height: 460
            M.Button { x: 520; y: 420; width: 110; text: "Salva"
                tip: "Salva (Ctrl+S)\\nConserva la copia precedente e salva tutte le modifiche al progetto nella cartella scelta." }
        }''')
        QTest.mouseMove(window, QPoint(580, 435))
        QTest.qWait(900)            # the first tooltip after 700 ms (R468)
        tip = root.findChild(QObject, 'controlTip')
        parent = tip.property('parent')
        point = parent.mapToScene(QPoint(0, 0))
        self.assertLessEqual(point.y()+tip.property('y')+tip.property('height'), 431)
        old = (tip.property('x'), tip.property('y'))
        QTest.mouseMove(window, QPoint(590, 435))
        QTest.qWait(30)
        self.assertEqual(old, (tip.property('x'), tip.property('y')))

    def test_step_uses_number_being_edited(self):
        field, window, theme = self.scene('M.NumberField { width: 180; value: 12; minimum: 0; maximum: 100 }')
        field.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(window, '2')
        QTest.keyClick(window, '7')
        QTest.keyClick(window, Qt.Key.Key_Up)
        self.assertEqual(field.property('value'), 28)

    def test_number_arrow_uses_edited_bound_and_wheel_requires_focus(self):
        from PySide6.QtCore import QPointF
        from PySide6.QtGui import QWheelEvent
        field, window, theme = self.scene('M.NumberField { width: 180; value: 0; minimum: 0; maximum: 100 }')

        def wheel():
            event = QWheelEvent(QPointF(70, 14), QPointF(window.mapToGlobal(QPoint(70, 14))),
                                QPoint(), QPoint(0, 120), Qt.MouseButton.NoButton,
                                Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
            self.app.sendEvent(window, event)

        wheel()
        self.assertEqual(field.property('value'), 0)
        field.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(window, '2')
        QTest.keyClick(window, '7')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(169, 21))
        self.assertEqual(field.property('value'), 26)
        wheel()
        self.assertEqual(field.property('value'), 27)

    def test_split_right_click_keeps_menu_alive_when_command_is_disabled(self):
        root, window, theme = self.scene('''M.SplitButton { width: 150; height: 55; text: "Edificio"
            mainEnabled: false; model: [{text:"Edificio"},{text:"Copertura"}]
            property bool menuVisible: menu.visible
            property int commands: 0; property int choice: -1
            onClicked: commands++; onChosen: index => choice = index
        }''')
        QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(40, 20))
        self.assertEqual(root.property('commands'), 0)
        QTest.mouseMove(window, QPoint(144, 20))
        QTest.qWait(20)
        self.assertEqual(self.pixel(window, 40, 4), theme.colors['panel'])
        QTest.mouseClick(window, Qt.MouseButton.RightButton, pos=QPoint(40, 20))
        QTest.qWait(20)
        self.assertTrue(root.property('menuVisible'))
        QTest.keyClick(window, Qt.Key.Key_Down)
        QTest.keyClick(window, Qt.Key.Key_Return)
        self.assertEqual(root.property('choice'), 0)

    def test_tree_left_returns_to_parent_and_end_reaches_last_row(self):
        tree, window, theme = self.scene('''M.Tree { width: 240; height: 180
            model: [{id:"b",text:"Edificio",children:[{id:"r",text:"Copertura"}]},{id:"u",text:"Uffici"}]
            expandedIds: ["b"]; currentIndex: 0
        }''')
        tree.forceActiveFocus()
        QTest.keyClick(window, Qt.Key.Key_Right)
        self.assertEqual(tree.property('currentIndex'), 1)
        QTest.keyClick(window, Qt.Key.Key_Left)
        self.assertEqual(tree.property('currentIndex'), 0)
        QTest.keyClick(window, Qt.Key.Key_Left)
        self.assertEqual(tree.property('count'), 2)
        QTest.keyClick(window, Qt.Key.Key_End)
        self.assertEqual(tree.property('currentIndex'), 1)
        QTest.keyClick(window, Qt.Key.Key_Home)
        self.assertEqual(tree.property('currentIndex'), 0)

    def test_scroll_fades_follow_viewport_and_do_not_intercept_clicks(self):
        for dark in (False, True):
            root, window, theme = self.scene('''Item { width: 240; height: 100
                property int clicks: 0
                Flickable { id: port; objectName: "port"; anchors.fill: parent; contentHeight: 300; clip: true
                    Rectangle { width: 240; height: 300; color: Theme.colors.accent
                        TapHandler { onTapped: root.clicks++ } }
                }
                M.EdgeFades { flickable: port; page: true }
            }'''.replace('Item { width:', 'Item { id: root; width:', 1), dark)
            port = root.findChild(QQuickItem, 'port')
            top = root.findChild(QQuickItem, 'topFade')
            bottom = root.findChild(QQuickItem, 'bottomFade')
            self.assertFalse(top.isVisible())
            self.assertTrue(bottom.isVisible())
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(120, 97))
            self.assertEqual(root.property('clicks'), 1)
            port.setProperty('contentY', 100)
            QTest.qWait(30)
            self.assertTrue(top.isVisible())
            self.assertTrue(bottom.isVisible())
            port.setProperty('contentY', 200)
            QTest.qWait(30)
            self.assertTrue(top.isVisible())
            self.assertFalse(bottom.isVisible())
            port.setProperty('contentHeight', 100)
            port.setProperty('contentY', 0)
            QTest.qWait(30)
            self.assertFalse(top.isVisible())
            self.assertFalse(bottom.isVisible())

    def test_progress_keeps_fusion_scanlines_at_screen_scale(self):
        from PySide6.QtCore import QSize
        from PySide6.QtGui import QImage, QPainter
        from meridiana.quick.backend.controls import IconProvider
        root, window, theme = self.scene('M.ProgressBar { width: 240; value: 0.5 }', True)
        actual = grab(window)
        dpr = actual.devicePixelRatio()
        expected = QImage(round(32*dpr), round(6*dpr), QImage.Format.Format_ARGB32_Premultiplied)
        expected.fill(QColor(theme.colors['panel']))
        provider = IconProvider(theme)
        painter = QPainter(expected)
        for part in ('groove', 'fill'):
            skin = provider.requestImage(f'progress:{part}/0/{dpr}/on', QSize(), QSize())
            skin.setDevicePixelRatio(1)
            painter.drawImage(0, 0, skin)
        painter.end()
        for y in range(expected.height()):
            self.assertEqual(actual.pixelColor(round(50*dpr), y), expected.pixelColor(round(12*dpr), y), y)

    def test_segment_frames_do_not_call_python_control_providers(self):
        import sys
        from pathlib import Path
        root, window, theme = self.scene('''M.Segments { width: 360; model: ["Pianta", "Vista 3D", "Entrambe"]
            M.ProgressBar { y: 60; width: 240; indeterminate: true }
            Flickable { id: port; y: 120; width: 240; height: 80; contentHeight: 300
                contentY: 20
                NumberAnimation on contentY { from: 20; to: 120; duration: 1000; loops: Animation.Infinite }
            }
            M.EdgeFades { flickable: port; page: true }
        }''')
        theme.configure({'reducedMotion': False})
        QTest.qWait(150)
        raised = root.findChild(QQuickItem, 'segmentSelection')
        fill = root.findChild(QQuickItem, 'progressFill')
        calls = []

        def profile(frame, event, arg):
            if event == 'call' and Path(frame.f_code.co_filename).name in ('tokens.py', 'controls.py'):
                calls.append(frame.f_code.co_name)

        previous = sys.getprofile()
        positions = []
        progress_positions = []
        windows = len(self.app.topLevelWindows())
        sys.setprofile(profile)
        try:
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=QPoint(310, 14))
            QTest.mouseMove(window, QPoint(620, 440))
            for _ in range(12):
                QTest.qWait(10)
                positions.append(raised.x())
                progress_positions.append(fill.x())
                image = grab(window)
                self.assertFalse(image.isNull())
        finally:
            sys.setprofile(previous)
        self.assertEqual(root.property('currentIndex'), 2)
        self.assertGreater(len(set(positions)), 1)
        self.assertGreater(len(set(progress_positions)), 1)
        self.assertEqual(calls, [])
        self.assertEqual(len(self.app.topLevelWindows()), windows)


if __name__ == '__main__':
    unittest.main()
