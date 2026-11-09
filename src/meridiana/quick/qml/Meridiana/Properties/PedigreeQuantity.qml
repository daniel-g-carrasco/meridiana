import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Column {
    id: root
    property var backend: null
    property var row: ({})
    property bool active: false
    readonly property bool narrow: width < 600
    readonly property string origin: (row.sourceKind || "")
        + (row.sourceLabel ? ": " + row.sourceLabel : "")
        + (row.sourceRef ? " (" + row.sourceRef + ")" : "")
    spacing: Theme.space.XS
    RowLayout {
        width: parent.width
        spacing: Theme.space.S
        PedigreeFormula {
            backend: root.backend
            formula: root.row.symbol || ""
            active: root.active
            Layout.preferredWidth: root.narrow ? 45 : root.width * .12
            Layout.alignment: Qt.AlignTop
            textSize: Theme.text.caption.size
        }
        M.Label {
            text: root.row.text || ""
            textStyle: root.row.result ? "strong" : "body"
            wrapMode: Text.Wrap
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
        }
        M.Label {
            text: root.row.value || ""
            textStyle: root.row.result ? "strong" : "body"
            wrapMode: Text.WrapAnywhere
            horizontalAlignment: Text.AlignRight
            Layout.preferredWidth: root.width * (root.narrow ? .3 : .2)
        }
        M.Label {
            visible: !root.narrow
            text: root.origin
            textStyle: "secondary"
            wrapMode: Text.Wrap
            Layout.preferredWidth: root.width * .32
        }
    }
    M.Label {
        visible: root.narrow && text.length > 0
        width: parent.width
        text: root.origin
        textStyle: "secondary"
        wrapMode: Text.Wrap
    }
    Rectangle { width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line }
}
