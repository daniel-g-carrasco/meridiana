import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as C
import Meridiana.Theme
import Meridiana.Controls as M

// The plan as a DXF (R513): in which coordinates and what goes in it, asked after the file. `frames` and `parts` come
// from the backend (dxf_export.frame_choices, part_names); a frame that cannot be used is off and says why.
M.Dialog {
    id: root
    objectName: "dxfOptions"
    property var frames: []
    property var parts: []
    property var words: ({})
    property string url: ""
    property string frame: "local"
    signal chosen(string url, string frame, var parts)
    parent: C.Overlay.overlay
    anchors.centerIn: parent
    modal: true
    width: Math.min(parent ? parent.width - 2 * Theme.space.XL : 600, 600)
    title: words.dxfTitle || ""
    acceptText: words.dxfExport || ""
    rejectText: words.cancel || ""
    function show(target, frameList, partList, labels) {
        root.url = target; root.frames = frameList; root.parts = partList; root.words = labels
        if (!frameList.some(f => f.key === root.frame && f.enabled)) root.frame = "local"
        open()
    }
    onAccepted: {
        let asked = []
        for (let i = 0; i < partRows.count; i++) {
            const row = partRows.itemAt(i)
            if (row && row.checked) asked.push(row.key)
        }
        chosen(root.url, root.frame, asked)
    }
    C.ButtonGroup { id: frameGroup }
    ColumnLayout {
        width: root.availableWidth
        spacing: Theme.space.S
        M.Label { Layout.fillWidth: true; text: root.words.dxfCoordinates || ""; textStyle: "strong" }
        Repeater {
            model: root.frames
            M.CheckBox {
                required property var modelData
                objectName: "dxfFrame-" + modelData.key
                Layout.fillWidth: true
                text: modelData.text + (modelData.enabled || !modelData.why ? "" : " (" + modelData.why + ")")
                enabled: modelData.enabled
                checked: modelData.key === root.frame
                C.ButtonGroup.group: frameGroup
                onToggled: if (checked) root.frame = modelData.key
            }
        }
        M.Label { Layout.fillWidth: true; text: root.words.dxfUnits || ""; wrapMode: Text.Wrap }
        M.Label { Layout.fillWidth: true; Layout.topMargin: Theme.space.M; text: root.words.dxfWhat || ""; textStyle: "strong" }
        Repeater {
            id: partRows
            model: root.parts
            M.CheckBox {
                required property var modelData
                property string key: modelData.key
                objectName: "dxfPart-" + modelData.key
                Layout.fillWidth: true
                text: modelData.text
                checked: true
            }
        }
    }
}
