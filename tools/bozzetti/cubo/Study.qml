import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.Controls as M
import "../../../src/meridiana/gui/qml/Meridiana/View3D" as V

Window {
    id: root
    width: 420; height: 260
    visible: false
    property string variant: "A"
    property string stateName: "rest"
    color: Theme.colors.view
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: Theme.colors.d3.sky_top }
            GradientStop { position: 1; color: Theme.colors.d3.sky_bottom }
        }
    }
    // The actual toolbar is reused for A and B; C inserts the four menu actions.
    V.SceneToolbar {
        x: Theme.space.L; y: Theme.space.L
        visible: root.variant !== "C"
        viewport: QtObject {
            property var sceneBackend: ({viewTips: {fit: "Adatta al disegno", zoomIn: "Ingrandisci", zoomOut: "Riduci"}})
            function requestCommand(command) {}
        }
    }
    Rectangle {
        x: Theme.space.L; y: Theme.space.L
        visible: root.variant === "C"
        width: actions.width+Theme.space.S; height: actions.height+Theme.space.S
        color: Theme.colors.panel; border.color: Theme.colors.line; radius: Theme.radius.CONTROL
        Row {
            id: actions
            x: Theme.space.S/2; y: Theme.space.S/2; spacing: 1
            V.ViewButton { iconName: "house"; tip: qsTr("Go to Home") }
            V.ViewButton { iconName: "3d"; tip: qsTr("Parallel projection"); checkable: true; checked: true }
            V.ViewButton { iconName: "fit"; tip: qsTr("Fit to the drawing") }
            V.ViewButton { iconName: "pin"; tip: qsTr("Set this view as Home") }
            Rectangle { width: 1; height: 16; color: Theme.colors.line; anchors.verticalCenter: parent.verticalCenter }
            V.ViewButton { iconName: "zoom_in"; tip: qsTr("Zoom in") }
            V.ViewButton { iconName: "zoom_out"; tip: qsTr("Zoom out") }
        }
    }
    V.ViewCube {
        id: current
        x: root.width-width-Theme.space.S; y: Theme.space.S
        visible: root.variant === "A"
        compact: true
        hoverTarget: root.stateName === "arrow" || root.stateName === "menu" ? "menu"
            : readable.target ? "part:"+readable.target : ""
    }
    ReadableCube {
        id: readable
        x: current.x; y: current.y
        visible: root.variant !== "A"
        menuButton: root.variant === "B"
        stateName: root.stateName
    }
    M.NorthSign {
        x: current.x+(current.width-width)/2; y: current.y+current.height+Theme.space.S
        north: 30
    }
}
