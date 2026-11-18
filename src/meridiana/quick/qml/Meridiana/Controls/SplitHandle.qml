import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
Rectangle {
    property int orientation: Qt.Vertical
    implicitWidth: Theme.space.M
    implicitHeight: Theme.space.M
    color: "transparent"
    HoverHandler { cursorShape: parent.orientation === Qt.Vertical ? Qt.SplitHCursor : Qt.SplitVCursor }
}
