import QtQuick
import QtQuick.Window
import QtQuick.Controls.Basic as C
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.DialogPreview

Item {
    id: root
    property var backend
    property string editingSide: ""
    DialogPreview {
        id: drawing; anchors.fill: parent
        visible: root.backend && root.backend.kind !== "ifc"
        Image { anchors.fill: parent; source: drawing.source; cache: false; asynchronous: false }
        backend: root.backend
        deviceScale: Screen.devicePixelRatio
        colors: Theme.colors
        textFont: Qt.font({family: Theme.fontFamily, pixelSize: Theme.text.body.size})
        onEditRequested: (key, value, x, y) => {
            root.editingSide = key; measure.text = value
            edit.x = Math.max(0, Math.min(root.width - edit.width, x - edit.width / 2))
            edit.y = Math.max(0, Math.min(root.height - edit.height, y - edit.height / 2))
            edit.open(); measure.forceActiveFocus(); measure.selectAll()
        }
    }
    IfcPreview { anchors.fill: parent; visible: root.backend && root.backend.kind === "ifc"; backend: root.backend }
    // R21-F2: the field over a side of the drawing, in the common popup without its frame, where the click was
    M.Popup {
        id: edit; width: 120; padding: 0; modal: false; focus: true; framed: false
        closePolicy: C.Popup.CloseOnEscape | C.Popup.CloseOnPressOutside
        onAboutToShow: { x = Math.max(0, Math.min(root.width - width, x)); y = Math.max(0, Math.min(root.height - height, y)) }
        contentItem: M.TextField {
            id: measure; objectName: "dialog_measure"
            onAccepted: if (root.backend.editMeasure(root.editingSide, text)) edit.close()
            Keys.onEscapePressed: edit.close()
        }
    }
}
