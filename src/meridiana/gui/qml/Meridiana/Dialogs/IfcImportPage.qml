import QtQuick
import QtQuick.Controls as C
import QtQuick.Layouts
import QtQuick.Dialogs as D
import Meridiana.Theme
import Meridiana.Controls as M

// The import of a BIM model: what was read, where it goes, what was left out. The height is the content's: the page never
// asks more of the window than it has to say; when it is taller than the room, the window's body scrolls (and only it).
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

    // before a file is chosen, and when the reading failed; R607: «Choose the file…» is the window's, on its row of
    // buttons (DialogWindow), with «Choose an IFC…» after a Revit file
    M.ReadableText {
        objectName: "ifcLead"
        Layout.fillWidth: true; wrapMode: Text.WordWrap
        visible: !root.read && !root.rvt && !(root.backend && root.backend.busy)
        text: root.labels.ifcLead || ""
    }

    // while it reads: the reading is a job of the window (R598), its row the common one (title, phase, bar; R607: the
    // window's «Cancel» stops it, the file's name is the window's subtitle). Only while it reads: the plan made again
    // after a choice (busy too) adds nothing above what was read, so the window's body scrolled down stays where it is
    // (R601)
    ColumnLayout {
        objectName: "ifcReading"
        Layout.fillWidth: true
        visible: !!(root.backend && root.backend.busy) && !root.read
        spacing: Theme.space.S
        M.WorkRow {
            objectName: "ifcReadRow"
            Layout.fillWidth: true
            row: typeof work !== "undefined" && work !== null ? work.slots.ifc_read : ({})
        }
    }

    // a Revit file: what it says of itself, and what to do
    RowLayout {
        Layout.fillWidth: true
        visible: root.rvt
        spacing: Theme.space.L
        Rectangle {
            Layout.preferredWidth: M.ControlMetrics.dialogParts.rvtPreview; Layout.preferredHeight: M.ControlMetrics.dialogParts.rvtPreview
            Layout.alignment: Qt.AlignTop
            visible: !!(root.state.rvtInfo && root.state.rvtInfo.preview)
            color: Theme.colors.hover; radius: Theme.radius.CONTROL
            Image { anchors.fill: parent; anchors.margins: Theme.space.XS; fillMode: Image.PreserveAspectFit; source: root.state.rvtInfo ? root.state.rvtInfo.preview : "" }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.space.S
            M.ReadableText { Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "strong"; text: root.state.rvtInfo ? root.state.rvtInfo.headline : "" }
            Repeater {
                model: root.state.rvtInfo ? root.state.rvtInfo.lines : []
                M.ReadableText { required property var modelData; Layout.fillWidth: true; wrapMode: Text.WordWrap; text: modelData }
            }
        }
    }

    // what was read
    RowLayout {
        Layout.fillWidth: true
        visible: root.read
        spacing: Theme.space.L
        Rectangle {
            Layout.preferredWidth: M.ControlMetrics.dialogParts.ifcPreview; Layout.preferredHeight: M.ControlMetrics.dialogParts.ifcPreview
            Layout.alignment: Qt.AlignTop
            color: Theme.colors.hover; radius: Theme.radius.CONTROL
            IfcPreview { anchors.fill: parent; backend: root.backend }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.alignment: Qt.AlignTop
            spacing: Theme.space.XS
            M.ReadableText { Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "secondary"; text: root.state.fileDescription || "" }
            Repeater {
                model: root.state.ifcFacts || []
                RowLayout {
                    required property var modelData
                    Layout.fillWidth: true; spacing: Theme.space.M
                    M.ReadableText { text: modelData.label; textStyle: "secondary"; Layout.preferredWidth: M.ControlMetrics.dialogParts.factLabel; wrapMode: Text.WordWrap; Layout.alignment: Qt.AlignTop }
                    M.ReadableText { text: modelData.value; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
            }
        }
    }

    // where it goes
    ColumnLayout {
        Layout.fillWidth: true
        visible: root.read
        spacing: Theme.space.XS
        M.CopyLabel { text: (root.labels.whereTitle || "").toUpperCase(); textStyle: "label" }
        Repeater {
            model: root.read ? root.backend.fields : []
            ColumnLayout {
                id: group
                required property var modelData
                Layout.fillWidth: true; spacing: Theme.space.XS
                M.CopyLabel { visible: group.modelData.key !== "how"; text: group.modelData.label; textStyle: "secondary" }
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
        M.ReadableText {
            objectName: "ifcPlaceNote"
            Layout.fillWidth: true; wrapMode: Text.WordWrap; textStyle: "secondary"
            visible: text !== ""
            text: root.state.ifcPlaceNote || ""
        }
    }

    // what was approximated and left out, whole: R601 (Daniel 14/11/2026, «sezioni in cui si scorre in verticale dentro
    // altre sezioni in cui si scorre in verticale bisogna togliersela»), only the window's body scrolls, the buttons
    // stay in sight under it
    Item {
        id: lists
        objectName: "ifcLists"
        Layout.fillWidth: true
        Layout.preferredHeight: details.implicitHeight
        visible: root.read && (root.state.ifcLists || []).length > 0
        Column {
            id: details
            width: lists.width
            spacing: Theme.space.S
            Repeater {
                model: root.state.ifcLists || []
                Column {
                    required property var modelData
                    width: details.width; spacing: Theme.space.XXS
                    M.CopyLabel { text: modelData.title; textStyle: "strong" }
                    Repeater {
                        model: modelData.items
                        M.ReadableText { required property var modelData; width: details.width; text: "· " + modelData; wrapMode: Text.WordWrap; textStyle: "secondary" }
                    }
                }
            }
        }
    }

    M.ReadableText {
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
