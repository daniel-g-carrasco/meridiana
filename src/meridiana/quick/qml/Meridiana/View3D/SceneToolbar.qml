import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    objectName: "sceneToolbar"
    required property var viewport
    property bool showViews: false
    signal viewRequested(string mode)
    width: row.width + 6
    height: row.height + 6
    color: Theme.colors.panel
    border.color: Theme.colors.line
    radius: Theme.radius.CONTROL
    Row {
        id: row
        x: 3; y: 3; spacing: 1
        Row {
            visible: root.showViews; spacing: 1
            ViewButton { iconName: "plan"; tip: qsTr("Pianta"); onClicked: root.viewRequested("plan") }
            ViewButton { iconName: "3d"; tip: qsTr("3D"); checked: true; onClicked: root.viewRequested("3d") }
            ViewButton { iconName: "both"; tip: qsTr("Affiancate"); onClicked: root.viewRequested("both") }
            Rectangle { width: 1; height: 16; color: Theme.colors.line; anchors.verticalCenter: parent.verticalCenter }
        }
        ViewButton { objectName: "sceneFit"; iconName: "fit"; tip: root.viewport.sceneBackend.viewTips.fit; onClicked: root.viewport.requestCommand("fit") }
        ViewButton { objectName: "sceneZoomIn"; iconName: "zoom_in"; tip: root.viewport.sceneBackend.viewTips.zoomIn; onClicked: root.viewport.requestCommand("zoom_in") }
        ViewButton { objectName: "sceneZoomOut"; iconName: "zoom_out"; tip: root.viewport.sceneBackend.viewTips.zoomOut; onClicked: root.viewport.requestCommand("zoom_out") }
    }
}
