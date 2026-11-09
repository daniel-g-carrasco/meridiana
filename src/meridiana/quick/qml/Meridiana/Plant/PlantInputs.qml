import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M

ListView {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var strings: backend.strings
    readonly property var inputs: backend.inputs
    property bool diagram: false
    spacing: Theme.space.M
    clip: true
    reuseItems: true
    model: root.inputs.filter(input => input.unit === backend.working)
    boundsBehavior: Flickable.StopAtBounds
    C.ScrollBar.vertical: M.ScrollBar { }
    delegate: Rectangle {
        id: input
        required property var modelData
        width: root.width
        height: content.implicitHeight + Theme.space.M * 2
        color: Theme.colors.card
        radius: Theme.radius.CARD
        border.width: Theme.line.HAIR
        border.color: Theme.colors.line
        ColumnLayout {
            id: content
            x: Theme.space.M; y: Theme.space.M
            width: parent.width - 2 * x
            spacing: Theme.space.S
            RowLayout {
                Layout.fillWidth: true
                M.Label { text: input.modelData.label; textStyle: "title"; Layout.fillWidth: true }
                M.Label { text: input.modelData.power + " kWp"; textStyle: "secondary" }
                M.Button { text: "+"; flat: true; tip: root.backend.tr("Draw a string")
                    onClicked: root.backend.draw(input.modelData.unit, input.modelData.mppt, -1) }
            }
            M.Label {
                Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "secondary"
                text: root.backend.tr("Modules in series") + ": " + input.modelData.series.join("–")
                    + " · " + root.backend.tr("Strings") + ": " + input.modelData.strings.length + " / " + input.modelData.allowed
            }
            Repeater {
                model: input.modelData.strings
                Rectangle {
                    id: run
                    required property int modelData
                    readonly property var info: root.strings[modelData] || ({})
                    Layout.fillWidth: true
                    height: Math.max(Theme.size.CONTROL, words.implicitHeight + Theme.space.S * 2)
                    color: root.backend.selected === modelData ? Theme.colors.press : "transparent"
                    RowLayout {
                        anchors.fill: parent
                        spacing: Theme.space.S
                        Item {
                            visible: root.diagram
                            Layout.preferredWidth: 78
                            Layout.fillHeight: true
                            Rectangle { x: 6; width: 1; height: parent.height; color: Theme.colors.muted }
                            Rectangle { x: 6; y: parent.height / 2; width: 60; height: 1; color: Theme.colors.muted }
                            Rectangle { x: 36; y: parent.height / 2 - 7; width: 26; height: 14; radius: 2
                                color: Theme.colors.panel; border.color: Theme.colors.muted }
                        }
                        Rectangle { width: 6; height: 6; radius: 3; color: root.backend.statusColors[run.info.state] || Theme.colors.muted }
                        ColumnLayout {
                            id: words
                            Layout.fillWidth: true
                            spacing: 0
                            M.Label { text: (run.info.label || "") + " · " + (run.info.modules || 0) + " " + root.backend.tr("Modules"); textStyle: "strong" }
                            M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: run.info.voltages || ""; textStyle: "secondary" }
                        }
                    }
                    TapHandler { onTapped: { root.backend.selectString(run.modelData); root.forceActiveFocus() }
                        onDoubleTapped: root.backend.draw(input.modelData.unit, input.modelData.mppt, run.modelData) }
                }
            }
            M.Label { Layout.fillWidth: true; visible: input.modelData.strings.length === 0
                text: root.backend.tr("no strings"); textStyle: "secondary" }
            M.Label { Layout.fillWidth: true; visible: text !== ""; text: input.modelData.why; wrapMode: Text.Wrap; textStyle: "secondary" }
        }
    }
}
