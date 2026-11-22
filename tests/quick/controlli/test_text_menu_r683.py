"""Real pointer and keyboard text commands."""
import unittest
import _setup
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from quick.aiuti.text_scene import TextScene


class TextMenu(TextScene):
    def test_commands_change_only_selection_and_keep_undo(self):
        root, window = self.scene('TextField')
        root.forceActiveFocus()
        self.evaluate(root, 'select(0, 5); textActions.execute("cut")')
        self.assertEqual(self.app.clipboard().text(), 'Alpha')
        self.assertEqual(root.property('text'), ' beta')
        self.evaluate(root, 'textActions.execute("undo")')
        self.assertEqual(root.property('text'), 'Alpha beta')
        self.evaluate(root, 'textActions.execute("redo")')
        self.assertEqual(root.property('text'), ' beta')
        self.evaluate(root, 'deselect(); textActions.execute("delete")')
        self.assertEqual(root.property('text'), ' beta')

    def test_readonly_whole_and_secret_never_export(self):
        for extra in ('readOnly: true', 'echoMode: TextInput.Password'):
            root, window = self.scene('TextField', extra)
            self.app.clipboard().setText('sentinel')
            self.evaluate(root, 'textActions.execute("whole")')
            self.assertEqual(self.app.clipboard().text(), 'Alpha beta' if extra.startswith('read') else 'sentinel')

    def test_shift_f10_and_menu_preserve_selection(self):
        root, window = self.scene('TextField')
        root.forceActiveFocus()
        self.evaluate(root, 'select(0, 5)')
        QTest.keyClick(window, Qt.Key_F10, Qt.ShiftModifier)
        self.assertTrue(_setup.wait_for(lambda: self.evaluate(root, 'textActions.menuActive'), 300))
        self.assertEqual(root.property('selectedText'), 'Alpha')
        QTest.keyClick(window, Qt.Key_Escape)
        self.assertTrue(_setup.wait_for(lambda: root.hasActiveFocus(), 500))

    def test_right_click_opens_for_each_family(self):
        for kind in ('TextField', 'NumberField', 'TextArea', 'GrowingField', 'OverlayField'):
            with self.subTest(kind=kind):
                root, window = self.scene(kind)
                root.forceActiveFocus()
                QTest.mouseClick(window, Qt.RightButton, pos=QPoint(25, 12))
                self.assertTrue(_setup.wait_for(lambda root=root: any(
                    o.objectName() == 'textContextMenu' and o.property('visible')
                    for o in root.findChildren(__import__('PySide6.QtCore', fromlist=['QObject']).QObject)
                ), 300), kind + ': right click did not open a text menu')

    def test_only_the_keys_of_a_text_reach_the_shortcut_guard(self):
        """R706: the guard that claims the editing keys watches the text that has the focus (and the windows while
        a text menu is open), not the application: the pointer over the window, a click, timers and repaints never
        enter it. On the application, every event of the program entered Python, and waited for the interpreter
        whenever a Python thread was at work."""
        from PySide6.QtCore import QEvent
        root, window = self.scene('TextField')
        guard = self.app._text_shortcut_guard
        inner, seen = guard.eventFilter, []

        def counting(watched, event):
            seen.append(event.type())
            return inner(watched, event)
        guard.eventFilter = counting
        self.addCleanup(lambda: guard.__dict__.pop('eventFilter', None))
        window.contentItem().forceActiveFocus()
        for x in range(320, 560, 40):
            QTest.mouseMove(window, QPoint(x, 300))
        QTest.mouseClick(window, Qt.LeftButton, pos=QPoint(450, 300))
        _setup.turn_events(self.app, 80)
        self.assertEqual(seen, [], 'no text has the focus: nothing enters the guard')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        seen.clear()
        for x in range(320, 560, 40):
            QTest.mouseMove(window, QPoint(x, 300))
        _setup.turn_events(self.app, 80)
        pointer = {QEvent.Type.MouseMove, QEvent.Type.HoverMove, QEvent.Type.MouseButtonPress, QEvent.Type.UpdateRequest}
        self.assertFalse(pointer & set(seen), 'the pointer elsewhere in the window does not enter it either')
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        self.assertIn(QEvent.Type.ShortcutOverride, seen, 'the keys of the text do')
        self.assertEqual(self.app.clipboard().text(), 'Alpha beta')

    def test_text_keys_precede_window_shortcuts(self):
        root, window = self.scene('TextField', 'property int projectCommands: 0; Shortcut { sequence: StandardKey.Copy; onActivated: projectCommands++ } Shortcut { sequence: StandardKey.Undo; onActivated: projectCommands++ }')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        self.assertEqual(self.app.clipboard().text(), 'Alpha beta')
        self.assertEqual(root.property('projectCommands'), 0)
        QTest.keyClick(window, 'x')
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
        self.assertEqual(root.property('text'), 'Alpha beta')
        self.assertEqual(root.property('projectCommands'), 0)

    def test_menu_return_never_submits_growing_field(self):
        root, window = self.scene('GrowingField', 'property int sends: 0; onAccepted: sends++')
        self.evaluate(root, 'area.forceActiveFocus()')
        QTest.keyClick(window, Qt.Key_F10, Qt.ShiftModifier)
        self.assertTrue(_setup.wait_for(lambda: self.evaluate(root, 'textActions.menuActive'), 300))
        QTest.keyClick(window, Qt.Key_Down)
        QTest.keyClick(window, Qt.Key_Return)
        self.assertEqual(root.property('sends'), 0)

    def test_changed_identity_rejects_menu_edits(self):
        root, window = self.scene('TextField', 'property int epoch: 1; textActions.identity: epoch')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        QTest.mouseClick(window, Qt.RightButton, pos=QPoint(25, 12))
        self.app.clipboard().setText('replacement')
        self.evaluate(root, 'epoch = 2; textActions.execute("paste")')
        self.assertEqual(root.property('text'), 'Alpha beta')

    def test_empty_and_readonly_fields_keep_project_commands_out(self):
        for extra in ('readOnly: true', 'text: ""'):
            # An empty value is set after creation so the common fixture keeps one text declaration.
            state = 'readOnly: true;' if extra.startswith('readOnly') else ''
            root, window = self.scene('TextField', state + 'property int projectCommands:0; Shortcut { sequence: StandardKey.Undo; onActivated: projectCommands++ } Shortcut { sequence: "Del"; onActivated: projectCommands++ }')
            if not state: root.setProperty('text', '')
            root.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
            QTest.keyClick(window, Qt.Key_Delete)
            self.assertEqual(root.property('projectCommands'), 0)

    def test_copy_shortcut_in_open_menu_uses_frozen_text(self):
        root, window = self.scene('ReadableText', 'property int projectCopies:0; Shortcut { sequence:StandardKey.Copy; onActivated:projectCopies++ }')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_F10, Qt.ShiftModifier)
        root.setProperty('text', 'Later text')
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        self.assertEqual(root.property('projectCopies'), 0)
        self.assertEqual(self.app.clipboard().text(), 'Alpha beta')

    def test_common_handler_precedes_consumer_bindings(self):
        root, window = self.scene('TextField', 'property int escapes: 0; Keys.onPressed: event => { event.accepted = false }; Keys.onEscapePressed: escapes++')
        root.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_F10, Qt.ShiftModifier)
        self.assertTrue(self.evaluate(root, 'textActions.menuActive'))
        QTest.keyClick(window, Qt.Key_Escape)
        self.assertEqual(root.property('escapes'), 0)

    def test_platform_long_press_opens_text_menu(self):
        root, window = self.scene('TextField')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        QTest.keyClick(window, 'z')
        QTest.mousePress(window, Qt.LeftButton, pos=QPoint(25, 12))
        QTest.qWait(self.app.styleHints().mousePressAndHoldInterval() + 80)  # wait: the press held past Qt's press-and-hold
        QTest.mouseRelease(window, Qt.LeftButton, pos=QPoint(25, 12))
        self.assertTrue(self.evaluate(root, 'textActions.menuActive'))
        self.assertEqual(root.property('text'), 'z')

    def test_ime_preedit_survives_menu(self):
        from PySide6.QtCore import QCoreApplication
        from PySide6.QtGui import QInputMethodEvent
        root, window = self.scene('TextField')
        root.forceActiveFocus()
        QCoreApplication.sendEvent(root, QInputMethodEvent('compose', []))
        self.assertEqual(root.property('preeditText'), 'compose')
        QTest.keyClick(window, Qt.Key_F10, Qt.ShiftModifier)
        self.assertEqual(root.property('preeditText'), 'compose')

    def test_empty_disabled_readonly_and_clipboard_states(self):
        root, window = self.scene('TextField')
        self.evaluate(root, 'text = ""')
        self.app.clipboard().clear()
        self.assertFalse(self.evaluate(root, 'textActions.allowed("copy")'))
        self.assertFalse(self.evaluate(root, 'textActions.allowed("paste")'))
        self.assertFalse(self.evaluate(root, 'textActions.allowed("selectAll")'))
        self.app.clipboard().setText('caf\u00e9 \U0001f600')
        self.assertTrue(self.evaluate(root, 'textActions.allowed("paste")'))
        self.evaluate(root, 'textActions.execute("paste")')
        self.assertEqual(root.property('text'), 'caf\u00e9 \U0001f600')
        root.setEnabled(False)
        self.assertFalse(self.evaluate(root, 'textActions.allowed("copy")'))
        root.setEnabled(True)
        root.setProperty('readOnly', True)
        self.assertFalse(self.evaluate(root, 'textActions.allowed("paste")'))
        self.evaluate(root, 'textActions.execute("copy")')
        self.assertEqual(self.app.clipboard().text(), 'caf\u00e9 \U0001f600')

    def test_numeric_paste_at_cursor_partial_selection_and_undo(self):
        root, window = self.scene('NumberField', 'value: 12.5; unit: "kWh"; decimals: 2; minimum: 0; maximum: 100')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        self.app.clipboard().setText('27,75 kWh')
        QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
        self.assertIn(root.property('text'), ('27.75', '27,75'))
        self.assertEqual(root.property('value'), 12.5)
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
        self.assertIn(root.property('text'), ('12.50', '12,50'))
        self.evaluate(root, 'select(0, 2)')
        self.app.clipboard().setText('9')
        QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
        self.assertIn(root.property('text'), ('9.5', '9,5'))
        before = root.property('text')
        self.evaluate(root, 'selectAll()')
        self.app.clipboard().setText('1.500')
        QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
        self.assertEqual(root.property('text'), before)

    def test_numeric_menu_paste_keeps_one_local_undo_and_no_project_commit(self):
        root, window = self.scene('NumberField', 'value: 12.5; unit:"kWh"; minimum:0; maximum:100; property int commits:0; onValueEdited:commits++')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        self.app.clipboard().setText('27,75 kWh')
        QTest.keyClick(window, Qt.Key_Menu)
        self.assertTrue(_setup.wait_for(lambda: self.evaluate(root, 'textActions.popup && textActions.popup.shown >= .99'), 1500))
        paste = self.evaluate(root, 'textActions.popup.itemAt(7)')
        self.assertEqual(paste.property('text'), 'Paste')
        point = paste.mapToScene(paste.boundingRect().center()).toPoint()
        QTest.mouseClick(window, Qt.LeftButton, pos=point)
        self.assertIn(root.property('text'), ('27.75', '27,75'))
        self.assertEqual(root.property('value'), 12.5)
        self.assertEqual(root.property('commits'), 0)
        self.assertTrue(_setup.wait_for(lambda: root.hasActiveFocus(), 500))
        QTest.keyClick(window, Qt.Key_Z, Qt.ControlModifier)
        self.assertIn(root.property('text'), ('12.50', '12,50'))
        self.assertEqual(root.property('commits'), 0)

    def test_plain_fields_with_numeric_validators_share_paste(self):
        root, window = self.scene('TextField', 'validator: DoubleValidator { bottom:0; top:100; decimals:2 }')
        root.forceActiveFocus()
        self.evaluate(root, 'selectAll()')
        self.app.clipboard().setText('12,5')
        QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
        self.assertTrue(root.property('acceptableInput'))
        self.assertIn(root.property('text'), ('12.5', '12,5'))
        self.evaluate(root, 'selectAll()')
        self.app.clipboard().setText('1.500')
        QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier)
        self.assertIn(root.property('text'), ('12.5', '12,5'))

    def test_keyboard_copy_and_password(self):
        for extra, expected in (('', 'Alpha beta'), ('readOnly: true', 'Alpha beta'),
                                ('echoMode: TextInput.Password', 'sentinel')):
            root, window = self.scene('TextField', extra)
            self.app.clipboard().setText('sentinel')
            root.forceActiveFocus()
            QTest.keyClick(window, Qt.Key_A, Qt.ControlModifier)
            QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
            self.assertEqual(self.app.clipboard().text(), expected)


if __name__ == '__main__':
    unittest.main()
