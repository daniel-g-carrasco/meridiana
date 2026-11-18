import QtQuick
import QtQuick.Layouts
import QtQuick.Templates as T
import Meridiana.Theme
import Meridiana.Controls as M

M.Card {
    id: root
    required property var backend
    property var modules: []
    property int per: 1
    property var joined: []
    property int runIndex: -1
    readonly property var sizes: {
        let result = []
        for (let i = 0; i < modules.length; ++i) {
            if (i && joined[i]) result[result.length - 1]++
            else result.push(1)
        }
        return result
    }
    readonly property bool valid: sizes.every(n => n <= per)
    function prepare(keys, maximum, partition, index) {
        modules = keys; per = maximum; runIndex = index
        let starts = [0], at = 0
        for (const size of partition) { at += size; starts.push(at) }
        joined = keys.map((key, i) => per === 2 && i > 0 && !starts.includes(i))
        visible = true
    }
    function preset(size) { joined = modules.map((key, i) => i > 0 && i % size !== 0) }
    title: backend.tr("Modules on each optimizer")
    // R518: in a window the buttons are the window's (M.Dialog), which calls apply()
    function apply() { if (valid && backend.setOptimizerGroups(runIndex, sizes)) visible = false }
    closable: true
    onClosed: visible = false
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.space.S
        M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap; textStyle: "description"
            text: root.backend.tr("Check a module to connect it to the same optimizer as the previous module. Modules on one optimizer share its MPPT and must have the same type, orientation and tilt.") }
        ListView {
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; reuseItems: true; model: root.modules
            T.ScrollBar.vertical: M.ScrollBar { id: groupsBar }
            delegate: RowLayout {
                required property int index
                required property string modelData
                width: ListView.view.width - groupsBar.room
                M.CheckBox { objectName: "joinModule" + index; Layout.fillWidth: true
                    text: root.backend.tr("Module {n}").replace("{n}", String(index + 1))
                    checked: !!root.joined[index]; enabled: index > 0 && root.per === 2
                    onToggled: { let next = root.joined.slice(); next[index] = checked; root.joined = next } }
                M.Label { text: String(root.joined.slice(0, index + 1).filter(value => !value).length); textStyle: "secondary" }
            }
        }
        RowLayout {
            M.Button { text: root.backend.tr("One module each"); onClicked: root.preset(1) }
            M.Button { text: root.backend.tr("Pairs in string order"); enabled: root.per === 2; onClicked: root.preset(root.per) }
        }
        M.Label { Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.valid ? root.backend.tr("{n} optimizers for {m} modules").replace("{n}", root.sizes.length).replace("{m}", root.modules.length)
                : root.backend.tr("An optimizer cannot take more than {n} modules.").replace("{n}", root.per) }
        RowLayout {
            visible: !root.bare
            M.Button { objectName: "applyGroups"; text: root.backend.tr("Apply"); enabled: root.valid
                onClicked: { if (root.backend.setOptimizerGroups(root.runIndex, root.sizes)) root.visible = false } }
            M.Button { text: root.backend.tr("Cancel"); onClicked: root.visible = false }
        }
    }
}
