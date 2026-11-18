import QtQuick
import QtQuick.Controls as C
import QtQuick.Layouts
import QtQuick.Dialogs as D
import Meridiana.Theme
import Meridiana.Controls as M

// The import of a BIM model: what was read, where it goes, what was left out. The height is the content's: the page never
// asks more of the window than it has to say, and the lists scroll inside it when they are long.
ColumnLayout {
    id: root
    objectName: "ifcImportPage"
    property var backend
    readonly property var state: backend ? backend.state : ({})
    readonly property var labels: backend ? backend.labels : ({})
    readonly property bool read: !!state.ifcRead
    readonly property bool rvt: !!state.rvtInfo
    spacing: Theme.space.L

    function pickFile() { importFile.open() }

    // before a file is chosen, and when the reading failed
    ColumnLayout {
        Layout.fillWidth: true
        visible: !root.read && !root.rvt && !(root.backend && root.backend.busy)
        spacing: Theme.space.M
        M.Label {
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            text: root.labels.ifcLead || ""
        }
        M.Button {
            objectName: "ifcChooseFile"
            text: root.labels.chooseFile || ""
            onClicked: root.pickFile()
        }
    }

    // while it reads
    ColumnLayout {
        Layout.fillWidth: true
        visible: !!(root.backend && root.backend.busy)
        spacing: Theme.space.S
        M.Label { Layout.fillWidth: true; text: root.state.fileName || ""; wrapMode: Text.WrapAnywhere; textStyle: "secondary" }
        M.Label { Layout.fillWidth: true; text: root.state.ifcStage || ""; wrapMode: Text.WordWrap }
        M.ProgressBar {
            Layout.fillWidth: true
            indeterminate: !root.backend || !root.state.progress
            value: root.state.progress || 0
        }
    }

    // a Revit file: what it says of itself, and what to do
    RowLayout {
        Layout.fillWidth: true
        visible: root.rvt
        spacing: Theme.space.L
        Rectangle {
            Layout.preferredWidth: 128; Layout.preferredHeight: 128; Layout.alignment: Qt.AlignTop
            visible: !!(root.state.rvtInfo && root.state.rvtInfo.preview)
            color: Theme.colors.hover; radius: Theme.radius.CONTROL
            Image { anchors.fill: parent; anchors.margins: Theme.space.XS; fillMode: Image.PreserveAspectFit; source: root.state.rvtInfo ? root.state.rvtInfo.preview : "" }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space.S
            M.Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "strong"; text: root.state.rvtInfo ? root.state.rvtInfo.headline : "" }
            Repeater {
                model: root.state.rvtInfo ? root.state.rvtInfo.lines : []
                M.Label { required property var modelData; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: modelData }
            }
        }
    }
    M.Button {
        visible: root.rvt
        objectName: "ifcChooseAnother"
        text: root.labels.chooseIfc || ""
        onClicked: root.pickFile()
    }

    // what was read
    RowLayout {
        Layout.fillWidth: true
        visible: root.read
        spacing: Theme.space.L
        Rectangle {
            Layout.preferredWidth: 220; Layout.preferredHeight: 220; Layout.alignment: Qt.AlignTop
            color: Theme.colors.hover; radius: Theme.radius.CONTROL
            IfcPreview { anchors.fill: parent; backend: root.backend }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.alignment: Qt.AlignTop
            spacing: Theme.space.XS
            M.Label { Layout.fillWidth: true; wrapMode: Text.WrapAnywhere; textStyle: "strong"; text: root.state.ifcFile || "" }
            M.Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "secondary"; text: root.state.fileDescription || "" }
            Repeater {
                model: root.state.ifcFacts || []
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true; spacing: Theme.space.M
                    M.Label { text: modelData.label; textStyle: "secondary"; Layout.preferredWidth: 96; wrapMode: Text.WordWrap; Layout.alignment: Qt.AlignTop }
                    M.Label { text: modelData.value; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
            }
        }
    }

    // where it goes
    ColumnLayout {
        Layout.fillWidth: true
        visible: root.read
        spacing: Theme.space.XS
        M.Label { text: (root.labels.whereTitle || "").toUpperCase(); textStyle: "label" }
        Repeater {
            model: root.read ? root.backend.fields : []
            ColumnLayout {
                id: group
                required property var modelData
                Layout.fillWidth: true; spacing: Theme.space.XS
                M.Label { visible: group.modelData.key !== "how"; text: group.modelData.label; textStyle: "secondary" }
                Repeater {
                    // r22-ifc: the storeys, ticked one by one; every other field a choice of one
                    model: group.modelData.kind === "checks" ? group.modelData.options : []
                    M.CheckBox {
                        required property var modelData
                        objectName: "ifcCheck_" + modelData.value
                        Layout.fillWidth: true
                        text: modelData.label
                        checked: (root.state[group.modelData.key] || []).indexOf(modelData.value) >= 0
                        onToggled: {
                            const now = (root.state[group.modelData.key] || []).filter(v => v !== modelData.value)
                            if (checked)
                                now.push(modelData.value)
                            root.backend.setValue(group.modelData.key, now)
                        }
                    }
                }
                Repeater {
                    model: group.modelData.kind === "checks" ? [] : group.modelData.options
                    M.RadioButton {
                        id: radio
                        required property var modelData
                        objectName: "ifcChoice_" + modelData.value
                        Layout.fillWidth: true
                        text: modelData.label
                        checked: root.state[group.modelData.key] === modelData.value
                        onClicked: root.backend.setValue(group.modelData.key, modelData.value)
                    }
                }
            }
        }
        M.Label {
            objectName: "ifcPlaceNote"
            Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "secondary"
            visible: text !== ""
            text: root.state.ifcPlaceNote || ""
        }
    }

    // what was approximated and left out; long lists scroll here, the buttons stay in sight
    M.ScrollPage {
        leftMargin: 0; air: 0; groundAbove: true
        id: lists
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(150, details.implicitHeight)
        visible: root.read && (root.state.ifcLists || []).length > 0
        Column {
            id: details
            width: lists.availableWidth
            spacing: Theme.space.S
            Repeater {
                model: root.state.ifcLists || []
                Column {
                    required property var modelData
                    width: details.width; spacing: 2
                    M.Label { text: modelData.title; textStyle: "strong" }
                    Repeater {
                        model: modelData.items
                        M.Label { required property var modelData; width: details.width; text: "· " + modelData; wrapMode: Text.WordWrap; textStyle: "secondary" }
                    }
                }
            }
        }
    }

    M.Label {
        objectName: "ifcStatus"
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        visible: text !== "" && !(root.backend && root.backend.busy)
        text: root.backend ? root.backend.status : ""
    }

    D.FileDialog {
        id: importFile
        nameFilters: [root.labels.bimFilter || "BIM (*.ifc *.IFC *.ifczip *.ifcZIP *.rvt *.RVT)"]
        onAccepted: root.backend.readFile(selectedFile.toString())
    }
}
