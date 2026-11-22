import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    objectName: "sceneToolbar"
    required property var viewport
    property bool showViews: false
    property bool orthographic: false
    signal homeRequested()
    signal orthographicRequested(bool enabled)
    signal fitRequested()
    signal setHomeRequested()
    signal viewRequested(string mode)
    implicitWidth: row.width + 6
    width: Math.min(implicitWidth, parent ? Math.max(0, parent.width - 2*x) : implicitWidth)
    height: row.height + 6
    color: Theme.colors.panel
    border.color: Theme.colors.line
    radius: Theme.radius.CONTROL
    // As the phase toolbar: scroll horizontally when the view cannot hold the row.
    M.HorizontalStrip {
        objectName: "sceneToolbarScroll"
        x: 3; y: 3
        width: Math.max(0, root.width - 6); height: row.height
        contentWidth: row.width
        Row {
            id: row
            spacing: 1
            Row {
                visible: root.showViews; spacing: 1
                ViewButton { iconName: "plan"; tip: qsTr("Plan"); onClicked: root.viewRequested("plan") }
                ViewButton { iconName: "3d"; tip: qsTr("3D"); checked: true; onClicked: root.viewRequested("3d") }
                ViewButton { iconName: "both"; tip: qsTr("Side by side"); onClicked: root.viewRequested("both") }
                Rectangle { width: 1; height: 16; color: Theme.colors.line; anchors.verticalCenter: parent.verticalCenter }
            }
            ViewButton { objectName: "sceneHome"; iconName: "house"; tip: qsTr("Go to Home") + " (Home)"; onClicked: root.homeRequested() }
            ViewButton {
                objectName: "sceneParallel"; iconName: "3d"; tip: qsTr("Parallel projection")
                checkable: true; checked: root.orthographic
                // State belongs to the camera, including changes made outside this button.
                onClicked: root.orthographicRequested(!root.orthographic)
            }
            ViewButton { objectName: "sceneFit"; iconName: "fit"; tip: qsTr("Fit to the drawing") + " (F)"; onClicked: root.fitRequested() }
            ViewButton { objectName: "sceneSetHome"; iconName: "pin"; tip: qsTr("Set this view as Home"); onClicked: root.setHomeRequested() }
            Rectangle { width: 1; height: 16; color: Theme.colors.line; anchors.verticalCenter: parent.verticalCenter }
            ViewButton { objectName: "sceneZoomIn"; iconName: "zoom_in"; tip: root.viewport.sceneBackend.viewTips.zoomIn; onClicked: root.viewport.requestCommand("zoom_in") }
            ViewButton { objectName: "sceneZoomOut"; iconName: "zoom_out"; tip: root.viewport.sceneBackend.viewTips.zoomOut; onClicked: root.viewport.requestCommand("zoom_out") }
        }
    }
}
