import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as T
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: checks
    property string phase: "model"
    property int count: backend.checkRows.length
    property int orderMode: 0
    property var levels: []
    property bool phaseOnly: false
    property bool objectOnly: false
    property int revision: 0
    property var groups: { const r=revision; return shell.checkGroups(["level","object","area"][orderMode], levels, phase, phaseOnly, objectOnly) }
    Connections { target: backend
        function onChecksChanged() { checks.revision++ }
        function onSelectionChanged() { checks.revision++ }
        function onObjectsChanged() { checks.revision++ }
    }
    spacing: Theme.space.XS
    Flow {
        Layout.fillWidth: true; spacing: Theme.space.XS
        M.Segments { model: [{text:L.byLevel},{text:L.byObject},{text:L.byArea}]
            onActivated: index => checks.orderMode=index }
        Repeater {
            model: shell.checkCounts
            M.Button { required property var modelData
                objectName: "filter_" + modelData.id; flat: true; text: modelData.text
                checked: checks.levels.includes(modelData.id)
                tip: modelData.text; textShown: false
                contentItem: Row { spacing: Theme.space.XS
                    M.Icon { iconName: "symbol:"+modelData.id
                        color: modelData.id==="warn" ? Theme.status.warning : modelData.id==="fail" ? Theme.colors.danger : Theme.colors.muted }
                    M.Label { text: modelData.count; textStyle: "secondary" }
                }
                onClicked: checks.levels=checked ? checks.levels.filter(v=>v!==modelData.id) : checks.levels.concat([modelData.id])
            }
        }
        M.Button { text: L.thisPhase; flat: true; checked: checks.phaseOnly; onClicked: checks.phaseOnly=!checks.phaseOnly }
        M.Button { text: L.thisObject; flat: true; checked: checks.objectOnly; enabled: backend.selection.editable
            onClicked: checks.objectOnly=!checks.objectOnly }
    }
    M.ScrollPage {
        leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0; groundAbove: true
        id: rows; objectName: "checksList"
        Layout.fillWidth: true; Layout.fillHeight: true
        Column {
            id: groupsColumn; width: parent.width; spacing: Theme.space.XS
            Repeater {
                model: checks.groups
                Column {
                    id: group; required property var modelData
                    property bool expanded: !modelData.closed
                    width: groupsColumn.width
                    M.Button { width: parent.width; flat: true
                        contentItem: Row { spacing: Theme.space.S
                            M.Icon { iconName: "chevron-right"; rotation: group.expanded ? 90 : 0 }
                            M.Label { text: group.modelData.text; textStyle: "label" }
                            M.Pill { text: group.modelData.rows.length }
                        }
                        onClicked: group.expanded=!group.expanded }
                    Repeater {
                        model: group.expanded ? group.modelData.rows : []
                        M.Button {
                            id: checkRow; required property var modelData
                            property bool detailOpen: false
                            width: group.width; flat: true
                            contentItem: Column { spacing: Theme.space.S
                                M.Label { width: checkRow.width-2*Theme.space.M; text: checkRow.modelData.text; elide: Text.ElideRight }
                                M.Label { width: checkRow.width-2*Theme.space.M; visible: checkRow.detailOpen
                                    text: checkRow.modelData.detail + "\n" + checkRow.modelData.source
                                    textStyle: "description"; wrapMode: Text.WordWrap }
                            }
                            tip: modelData.detail || modelData.source
                            onClicked: {
                                detailOpen=!detailOpen
                                if(modelData.target.length>1 && modelData.target[0]!=="phase") backend.select(modelData.target[0],modelData.target[1],"")
                                else if(modelData.target[0]==="phase") shell.trigger("phase_"+modelData.target[1])
                            }
                        }
                    }
                }
            }
        }
        M.Label { width: parent.width; horizontalAlignment: Text.AlignHCenter; text: L.noResults; visible: checks.groups.length===0; textStyle: "description" }
    }
}
