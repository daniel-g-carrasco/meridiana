import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

// Settings > Keyboard. R601 (Daniel 14/11/2026: «se proprio troppo lungo, diventerà una sottopagina o una finestra a
// sé stante»): the list of the shortcuts is about a hundred rows (98 commands, some 2 700 points at a row each), three
// or four screens: in the page that scrolls it was a list scrolling inside it, and drawn whole its search field and
// the field of the new keys would be a few screens apart. It is in the window of its own that File > Help opens
// (Dialogs/ShortcutsPage.qml: the search above, the list the only thing that scrolls, the new keys under it, the
// verdict on a conflict); here a sentence, the button that opens it and the restore of all the keys.
ColumnLayout {
    id: root
    required property var backend
    spacing: Theme.space.M
    M.ReadableText { Layout.fillWidth: true; text: root.backend.keyboardLead; wrapMode: Text.WordWrap }
    Flow {
        Layout.fillWidth: true
        spacing: Theme.space.S
        M.Button { objectName: "settingsOpenShortcuts"; text: root.backend.text.openShortcuts; onClicked: root.backend.requestCommand("shortcuts") }
        M.Button { text: root.backend.text.allDefaults; onClicked: root.backend.restoreDefaults("keyboard") }
    }
    M.ReadableText { Layout.fillWidth: true; text: root.backend.text.keyboardNote; wrapMode: Text.WordWrap; color: Theme.colors.muted }
}
