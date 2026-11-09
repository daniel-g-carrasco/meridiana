import QtQuick
import Meridiana.Controls as M

M.HelpMark {
    objectName: "assistantHelpButton"
    focusPolicy: Qt.StrongFocus     // as before: the help it opens follows the focus (F1 the same)
    property string helpId: ""
    property Item targetItem: parent
    required property var assistantLayer
    onClicked: assistantLayer.showHelpFor(helpId, targetItem)
}
