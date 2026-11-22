import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// A command of the window in a panel (ui/style.wrap_button): its own words and tooltip, one under the other on more
// lines rather than widen a narrow panel.
M.Button {
    id: root
    required property string command
    required property var actions
    readonly property var words: actions.commandWords[command] || ({})
    text: words.text || ""
    tip: words.tip || ""
    implicitHeight: Math.max(Theme.size.CONTROL, word.contentHeight + 2 * Theme.space.XS)
    height: implicitHeight
    contentItem: M.Label {
        id: word
        text: root.text; font: root.font; enabled: root.enabled
        wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
}
