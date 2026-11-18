import QtQuick
import QtQuick.Shapes
import Meridiana.Theme
import Meridiana.Controls as M

// ui/plant_page.MiniDiagram (R298, study 23, C): one row per input, each string a bar as long as its modules, in its
// colour on the plan, its name on it; the mark of the input's worst state at the row's end. A click on a bar chooses
// the string, a double click draws it again, the right button opens its menu; a click on a free input's dotted box
// draws a string on it.
Column {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var strings: backend.strings
    readonly property var inputs: backend.inputs
    required property var menu
    readonly property int longest: Math.max(1, ...root.strings.map(s => s.modules))
    readonly property real label: 56
    spacing: 0
    Repeater {
        model: root.inputs.filter(i => i.unit === root.backend.working)
        Item {
            id: input
            required property var modelData
            width: root.width; height: Theme.size.CHIP + Theme.space.XS
            readonly property bool drawing: root.backend.draftInput[0] === modelData.unit && root.backend.draftInput[1] === modelData.mppt
            Rectangle { anchors.fill: parent; anchors.margins: .5; radius: Theme.radius.INNER; color: "transparent"; visible: input.drawing
                border.width: Theme.line.HAIR; border.color: Theme.colors.accent }
            M.Label { x: Theme.space.XS; width: root.label - Theme.space.XS; height: parent.height; text: input.modelData.label; textStyle: "caption"; color: Theme.colors.muted; elide: Text.ElideRight }
            Rectangle { x: root.label; y: parent.height - 2; width: Math.max(0, parent.width - root.label - Theme.icon.CONTROL - Theme.space.S); height: Theme.line.HAIR; color: Theme.colors.muted }
            Row {
                x: root.label; y: (parent.height - 16) / 2; spacing: Theme.space.XS
                Repeater {
                    model: input.modelData.strings
                    Rectangle {
                        id: run
                        required property int modelData
                        readonly property var info: root.strings[modelData] || ({})
                        objectName: "plant-diagram-bar-" + modelData
                        width: Math.max(24, Math.max(40, input.width - root.label - Theme.icon.CONTROL - 2 * Theme.space.S) * (info.modules || 0) / root.longest * .5)
                        height: 16; radius: Theme.radius.MARK
                        color: root.backend.stringColours[String(modelData)] || Theme.colors.overlay.string_none
                        border.width: root.backend.selected === modelData ? 1.5 : 0; border.color: Theme.colors.text
                        M.Label { anchors.centerIn: parent; text: run.info.label || ""; textStyle: "caption"; color: run.color.hslLightness > .6 ? "black" : "white"; visible: implicitWidth + 4 <= parent.width }
                        TapHandler { onTapped: root.backend.selectString(run.modelData); onDoubleTapped: root.backend.draw(input.modelData.unit, input.modelData.mppt, run.modelData) }
                        TapHandler { acceptedButtons: Qt.RightButton; onTapped: root.menu.popupFor(run.modelData) }
                        HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
                        M.ToolTip { visible: hover.hovered; text: run.info.tip || "" }
                    }
                }
                Item {
                    id: adder
                    objectName: "plant-diagram-free-" + input.modelData.mppt
                    width: 24; height: 16
                    visible: input.modelData.room === true
                    Shape {
                        anchors.fill: parent
                        ShapePath {
                            strokeWidth: Theme.line.HAIR; strokeColor: Theme.colors.muted; fillColor: "transparent"
                            strokeStyle: ShapePath.DashLine; dashPattern: [1, 2]
                            PathRectangle { x: .5; y: .5; width: 23; height: 15; radius: Theme.radius.MARK }
                        }
                    }
                    M.Label { anchors.centerIn: parent; text: "+"; textStyle: "caption"; color: Theme.colors.muted }
                    TapHandler { onTapped: root.backend.draw(input.modelData.unit, input.modelData.mppt, -1) }
                    HoverHandler { id: addHover; cursorShape: Qt.PointingHandCursor }
                    M.ToolTip { visible: addHover.hovered; text: input.modelData.addTip || "" }
                }
            }
            M.Icon {
                x: parent.width - Theme.icon.CONTROL - Theme.space.XS; y: (parent.height - height) / 2; width: Theme.icon.CONTROL; height: width; dimDisabled: false
                iconName: "symbol:" + (input.modelData.level === "ok" ? "ok" : input.modelData.level === "warn" ? "warn" : input.modelData.level === "fail" ? "fail" : "info")
            }
        }
    }
}
