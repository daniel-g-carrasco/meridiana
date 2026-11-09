import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

// R375 (Daniel 05/11/2026 on the sketches docs/quick/inserimento-bozzetti.html, 07/11: «compare stranamente lontano
// dal pulsante Oggetto 3D… vorrei centralizzare il tutto»): the one tool «3D object». It hangs from its button
// (M.Popup) and holds the three ways of placing, in one strip of segments: «Choose and place» (a copy at every click,
// Esc ends), «Along a line» (two clicks, a copy every step; a fence, a hedge, a walkway follow the line as one
// object) and «Small family» (one click, a few with light differences: the radius, the variation). Under it the
// models of the catalogue, grouped (vehicles, people, plant and furniture, containers, trees, roof obstacles), each
// a tile with its preview (data/models/previews) and its name. A tile chosen tells the shell the kind and the way
// (shell.objectWanted) and the picker closes; the way and its numbers stay for the next time.
M.Popup {
    id: root
    property string mode: "place"
    property real step: 5
    property bool align: true
    property real radius: 6
    property real variation: 20
    readonly property var texts: shell.objectPickerTexts
    readonly property var modes: ["place", "line", "group"]
    width: M.ControlMetrics.pickerWidth
    padding: Theme.space.M
    function openFrom(item) { if (item) parent = item; open() }
    function choose(kind) {
        shell.objectWanted(kind, {mode: root.mode, step: root.step, align: root.align, radius: root.radius,
                                  variation: root.variation, repeat: root.mode === "place", seed: 0})
        close()
    }
    contentItem: ColumnLayout {
        spacing: Theme.space.S
        M.Segments { objectName: "objectModes"; Layout.fillWidth: true
            model: [root.texts.place, root.texts.line, root.texts.group]
            currentIndex: root.modes.indexOf(root.mode)
            onActivated: index => root.mode = root.modes[index] }
        M.Label { objectName: "objectHint"; Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "secondary"
            text: root.mode === "place" ? root.texts.placeHint : root.mode === "line" ? root.texts.lineHint : root.texts.groupHint }
        RowLayout { visible: root.mode === "line"; spacing: Theme.space.M
            M.Label { text: root.texts.step }
            M.NumberField { objectName: "objectStep"; Layout.preferredWidth: M.ControlMetrics.choiceWidth / 2
                value: root.step; minimum: .2; maximum: 200; decimals: 1; unit: "m"; stepSize: .5
                onValueEdited: value => root.step = value }
            M.CheckBox { text: root.texts.align; checked: root.align; onToggled: root.align = checked }
        }
        RowLayout { visible: root.mode === "group"; spacing: Theme.space.M
            M.Label { text: root.texts.radius }
            M.NumberField { objectName: "objectRadius"; Layout.preferredWidth: M.ControlMetrics.choiceWidth / 2
                value: root.radius; minimum: .5; maximum: 100; decimals: 1; unit: "m"; stepSize: 1
                onValueEdited: value => root.radius = value }
            M.Label { text: root.texts.variation }
            M.NumberField { objectName: "objectVariation"; Layout.preferredWidth: M.ControlMetrics.choiceWidth / 2
                value: root.variation; minimum: 0; maximum: 100; decimals: 0; unit: "%"; stepSize: 5
                onValueEdited: value => root.variation = value }
        }
        M.ScrollPage { objectName: "objectGroups"; Layout.fillWidth: true; leftMargin: 0
            Layout.preferredHeight: Math.min(M.ControlMetrics.menuTall, implicitHeight)
            Repeater { model: shell.objectGroups
                Column { required property var modelData; width: parent.width; spacing: Theme.space.XS
                    M.Label { text: parent.modelData.title; textStyle: "group"; condensed: true }
                    Flow { width: parent.width; spacing: Theme.space.XS
                        Repeater { model: parent.parent.modelData.kinds
                            M.Button { id: tile; required property var modelData; objectName: "objectTile_" + modelData.id
                                flat: true; width: M.ControlMetrics.modelTile; height: M.ControlMetrics.modelTile
                                padding: Theme.space.XS; tip: modelData.text
                                // a fence, a hedge or a walkway is one object along the line: it has no «small family»
                                enabled: root.mode !== "group" || !modelData.line
                                onClicked: root.choose(modelData.id)
                                contentItem: Column { spacing: Theme.space.XXS
                                    Image { anchors.horizontalCenter: parent.horizontalCenter
                                        width: M.ControlMetrics.modelPreview; height: M.ControlMetrics.modelPreview
                                        source: tile.modelData.preview; fillMode: Image.PreserveAspectFit; smooth: true; mipmap: true
                                        opacity: tile.enabled ? 1 : .4 }
                                    M.Label { width: parent.width; text: tile.modelData.text; textStyle: "caption"
                                        horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight; enabled: tile.enabled }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
