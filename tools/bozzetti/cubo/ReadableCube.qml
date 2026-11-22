import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M
import "../../../src/meridiana/gui/qml/Meridiana/View3D/CubeMath.js" as CubeMath

// Disposable proposal: production geometry and controls, stronger local feedback.
Item {
    id: root
    width: 76; height: 76
    property bool menuButton: true
    property string stateName: "rest"
    property string hoverTarget: ""
    property var cells: CubeMath.cells(30, -35, 64)
    readonly property color panelTone: Theme.colors.panel
    readonly property color inkTone: Theme.colors.text
    property var names: [qsTr("Top"), qsTr("Bottom"), "N", "S", "E", "W"]
    readonly property string target: hoverTarget || sampleTarget()
    function sampleTarget() {
        let count = stateName === "face" ? 1 : stateName === "edge" ? 2 : stateName === "corner" ? 3 : 0;
        let list = cells.filter(c => c.part.filter(v => v !== 0).length === count);
        return list.length ? list[Math.floor(list.length/2)].part.join(",") : "";
    }
    function path(polygon) {
        let points = polygon.map(p => Qt.point(width/2+p[0], height/2+p[1]));
        points.push(points[0]); return points;
    }
    function selected(cell) { return cell.part.join(",") === target; }
    function shade(cell) {
        // All nine patches of a plane receive the same light direction.
        let share = cell.normal === 0 ? 0 : cell.normal === 3 ? 0.09 : 0.17;
        return Theme.mix(root.panelTone, root.inkTone, share);
    }
    Repeater {
        model: root.cells
        Shape {
            id: patch
            required property var modelData
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                fillColor: root.selected(patch.modelData) ? Theme.colors.accent : root.shade(patch.modelData)
                strokeColor: root.selected(patch.modelData) ? Theme.colors.accent
                    : Theme.mix(root.panelTone, root.inkTone, 0.32)
                strokeWidth: root.selected(patch.modelData) ? Theme.line.FOCUS : 0.8
                PathPolyline { path: root.path(patch.modelData.polygon) }
            }
        }
    }
    Repeater {
        model: root.cells
        Text {
            required property var modelData
            visible: modelData.face
            property var xs: modelData.polygon.map(p => p[0])
            property var ys: modelData.polygon.map(p => p[1])
            x: root.width/2+Math.min(...xs); y: root.height/2+Math.min(...ys)
            width: Math.max(...xs)-Math.min(...xs); height: Math.max(...ys)-Math.min(...ys)
            text: root.names[modelData.normal]
            color: root.selected(modelData) ? Theme.colors.accent_fg : Theme.colors.text
            font.family: Theme.fontFamily
            font.pixelSize: Theme.text.label.size
            font.weight: Theme.text.label.weight
            font.capitalization: Font.AllUppercase
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
        }
    }
    MouseArea {
        anchors.fill: parent; hoverEnabled: true
        onPositionChanged: mouse => {
            let part = CubeMath.pick(root.cells, mouse.x-root.width/2, mouse.y-root.height/2);
            root.hoverTarget = part ? part.join(",") : "";
        }
        onExited: root.hoverTarget = ""
    }
    Item {
        x: root.width-Theme.size.CHIP; y: root.height-Theme.size.CHIP+Theme.space.XS
        width: Theme.size.CHIP; height: Theme.size.CHIP
        visible: root.menuButton
        M.SplitGround {
            anchors.fill: parent; split: 0; commandEnabled: false
            arrowHovered: arrow.containsMouse || root.stateName === "arrow"
            menuOpen: menu.visible
        }
        M.Chevron { anchors.centerIn: parent; active: arrow.containsMouse || root.stateName === "arrow" || menu.visible }
        MouseArea { id: arrow; anchors.fill: parent; hoverEnabled: true; onClicked: menu.popup() }
        M.ToolTip { visible: arrow.containsMouse; text: qsTr("View options") }
    }
    M.Menu {
        id: menu
        x: root.width-width; y: root.height+Theme.space.XS
        M.MenuItem { text: qsTr("Go to Home") }
        M.MenuItem { text: qsTr("Parallel projection"); checkable: true }
        M.MenuItem { text: qsTr("Fit to the drawing") }
        M.MenuItem { text: qsTr("Set this view as Home") }
    }
    onStateNameChanged: { if (stateName === "menu" && visible && menuButton) menu.open(); else menu.close(); }
}
