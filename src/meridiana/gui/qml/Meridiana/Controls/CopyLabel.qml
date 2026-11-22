import QtQuick
import QtQuick.Controls as C

// Compact semantic values retain label layout and copy their complete source, never the elision.
Label {
    id: root
    property string copyText: textFormat === Text.PlainText ? text : textEditing.plainHtml(text)
    property alias textActions: commands
    activeFocusOnTab: true
    TextActions { id: commands; target: root; readOnly: true; wholeText: root.copyText }
    C.ContextMenu.onRequested: position => root.forceActiveFocus(Qt.PopupFocusReason)
    C.ContextMenu.menu: TextMenu { actions: commands }
    Keys.onShortcutOverride: event => { event.accepted = event.matches(StandardKey.Copy) }
    Keys.onPressed: event => {
        if (event.matches(StandardKey.Copy)) { commands.execute("copy"); event.accepted = true }
        else if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) {
            C.ContextMenu.menu.popup(root, 0, root.height); event.accepted = true
        }
    }
}
