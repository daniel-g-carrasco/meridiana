import QtQuick
import QtQuick.Dialogs as D
import QtQuick.Layouts
import QtQuick.Templates as T
import Meridiana.Theme
import Meridiana.Controls as M

// R21-F2: the editor of a product is a window (M.Dialog): its title in the header, «Cancel» and «Save» in its bar
M.Dialog {
    id: root
    required property var backend
    objectName: "catalogEditor"
    width: Math.min(M.ControlMetrics.dialogWidth.page, parent.width - 2 * M.ControlMetrics.dialogEdge)
    // As tall as what it holds, up to the window: no empty band under the buttons.
    height: Math.min(parent.height - 2 * M.ControlMetrics.dialogEdge, implicitHeight)
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    title: backend.texts.copy
    rejectText: backend.texts.cancel
    acceptText: backend.texts.save
    acceptOnReturn: false
    onRejected: backend.cancelEdit()
    onAccepted: { if (backend.needsDestination) backend.setDestination(destination.text); backend.saveEditor() }
    visible: backend.editing
    onClosed: { if (backend.editing) backend.cancelEdit() }
    function chooseFile(pvsyst) {
        sheetFile.pvsyst = pvsyst
        sheetFile.nameFilters = pvsyst ? ["PVsyst (*.PAN *.pan *.OND *.ond)"] : ["PDF (*.pdf *.PDF)"]
        sheetFile.open()
    }
    D.FileDialog {
        id: sheetFile
        property bool pvsyst: false
        onAccepted: pvsyst ? root.backend.importPvsystInto(selectedFile.toString()) : root.backend.readDatasheet(selectedFile.toString())
    }
    contentItem: ColumnLayout {
        id: layout
        spacing: Theme.space.M
        Rectangle {
            id: dropZone
            objectName: "catalogDropZone"
            Layout.fillWidth: true
            implicitHeight: dropRow.implicitHeight + 2 * Theme.space.M
            radius: Theme.radius.CONTROL
            color: drop.containsDrag ? Theme.colors.select_bg : Theme.colors.view
            border.color: drop.containsDrag ? Theme.colors.accent : Theme.colors.line
            border.width: Theme.line.HAIR
            RowLayout {
                id: dropRow
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: Theme.space.M }
                spacing: Theme.space.M
                ColumnLayout {
                    Layout.fillWidth: true; spacing: Theme.space.XXS
                    M.Label { text: root.backend.texts.dropTitle; textStyle: "strong"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    M.Label { text: root.backend.texts.dropHelp; textStyle: "caption"; color: Theme.colors.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                }
                M.Button { objectName: "catalogChooseSheet"; text: root.backend.texts.chooseFile; onClicked: root.chooseFile(false) }
                M.Button { text: root.backend.texts.importPvsyst; visible: ["modules", "inverters"].includes(root.backend.kind); onClicked: root.chooseFile(true) }
            }
            DropArea {
                id: drop
                anchors.fill: parent
                keys: ["text/uri-list"]
                onDropped: event => {
                    if (!event.hasUrls || event.urls.length === 0) return
                    const url = event.urls[0].toString()
                    if (/\.(pan|ond)$/i.test(url)) root.backend.importPvsystInto(url)
                    else root.backend.readDatasheet(url)
                    event.accept()
                }
            }
        }
        M.Label { text: root.backend.editorNote || root.backend.texts.note; textStyle: "secondary"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true; visible: root.backend.editorProposals.length > 1; spacing: Theme.space.M
            M.Label { text: root.backend.texts.pick }
            CatalogChoice {
                objectName: "catalogProposal"
                Layout.fillWidth: true
                model: root.backend.editorProposals
                textRole: "model"; valueRole: "index"
                onActivated: root.backend.useProposal(currentValue)
            }
        }
        M.ScrollPage {
            leftMargin: 0; air: 0; spacing: 0; groundAbove: true
            id: scroller
            objectName: "catalogEditorFields"
            Layout.fillWidth: true
            Layout.fillHeight: true
            implicitHeight: body.implicitHeight
            Layout.minimumHeight: Math.min(160, body.implicitHeight)
            ColumnLayout {
                id: body
                width: scroller.width - Theme.space.L
                spacing: Theme.space.L
                Repeater {
                    model: root.backend.editorGroups
                    ColumnLayout {
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Theme.space.S
                        M.Label { text: modelData.title; textStyle: "title"; Layout.fillWidth: true }
                        GridLayout {
                            Layout.fillWidth: true
                            columns: 2
                            columnSpacing: Theme.space.XL
                            rowSpacing: Theme.space.S
                            Repeater {
                                model: parent.parent.modelData.fields
                                ColumnLayout {
                                    id: fieldBox
                                    required property var modelData
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    Layout.columnSpan: modelData.key === "notes" || modelData.key === "datasheet_url" || modelData.key === "compatible_inverters" ? 2 : 1
                                    visible: modelData.visible
                                    spacing: Theme.space.XXS
                                    M.Label {
                                        Layout.fillWidth: true
                                        text: fieldBox.modelData.label + (fieldBox.modelData.unit ? " (" + fieldBox.modelData.unit + ")" : "") + (fieldBox.modelData.required ? " *" : "")
                                        textStyle: "secondary"; wrapMode: Text.WordWrap
                                    }
                                    Loader {
                                        Layout.fillWidth: true
                                        sourceComponent: fieldBox.modelData.type === "choice" ? choiceField : fieldBox.modelData.type === "yesno" ? yesField : textField
                                        property var field: fieldBox.modelData
                                    }
                                    M.Label {
                                        Layout.fillWidth: true
                                        visible: text !== ""
                                        text: fieldBox.modelData.hint || ""
                                        textStyle: "caption"; color: Theme.colors.muted; wrapMode: Text.WordWrap
                                    }
                                    M.Label {
                                        objectName: "catalogSource_" + fieldBox.modelData.key
                                        Layout.fillWidth: true
                                        visible: text !== ""
                                        text: fieldBox.modelData.sourceText ? root.backend.texts.fromSheet + ": " + fieldBox.modelData.sourceText : ""
                                        textStyle: "caption"
                                        color: fieldBox.modelData.confidence === "high" ? Theme.colors.muted : Theme.colors.warn_text || Theme.colors.text2
                                        wrapMode: Text.WordWrap
                                        M.ToolTip { visible: sourceHover.hovered && fieldBox.modelData.line !== ""; text: fieldBox.modelData.line || "" }
                                        HoverHandler { id: sourceHover }
                                    }
                                }
                            }
                        }
                    }
                }
                ColumnLayout {
                    id: classes
                    Layout.fillWidth: true
                    visible: root.backend.kind === "modules"
                    spacing: Theme.space.S
                    M.Label { text: root.backend.texts.classes; textStyle: "title"; Layout.fillWidth: true }
                    M.Label { text: root.backend.texts.classesHelp; textStyle: "caption"; color: Theme.colors.muted; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 7
                        columnSpacing: Theme.space.S
                        rowSpacing: Theme.space.XS
                        visible: root.backend.editorClasses.length > 0
                        Repeater {
                            model: ["W", "Vmp (V)", "Imp (A)", "Voc (V)", "Isc (A)", "η (%)", ""]
                            M.Label { required property string modelData; text: modelData; textStyle: "secondary"; Layout.fillWidth: true; Layout.preferredWidth: 1 }
                        }
                        Repeater {
                            model: root.backend.editorClasses.length * 7
                            Loader {
                                id: classCell
                                required property int index
                                readonly property int row: Math.floor(index / 7)
                                readonly property int column: index % 7
                                readonly property string key: ["pmax", "vmp", "imp", "voc", "isc", "efficiency_pct", ""][column]
                                Layout.fillWidth: true
                                Layout.preferredWidth: 1
                                sourceComponent: column === 6 ? classRemove : classField
                            }
                        }
                    }
                    M.Button { objectName: "catalogAddClass"; text: root.backend.texts.addClass; onClicked: root.backend.addEditorClass() }
                }
            }
        }
        Component {
            id: textField
            M.TextField {
                objectName: "catalogField_" + parent.field.key
                text: parent.field.value
                placeholderText: parent.field.required ? root.backend.texts.required2 : ""
                invalid: parent.field.required && text.trim() === ""
                Accessible.name: parent.field.label
                onTextEdited: root.backend.setEditorField(parent.field.key, text)
            }
        }
        Component {
            id: choiceField
            CatalogChoice {
                objectName: "catalogField_" + parent.field.key
                model: parent.field.choices
                currentIndex: Math.max(0, parent.field.choices.findIndex(o => o.key === parent.field.value))
                Accessible.name: parent.field.label
                onActivated: root.backend.setEditorField(parent.field.key, currentValue)
            }
        }
        Component {
            id: yesField
            M.CheckBox {
                objectName: "catalogField_" + parent.field.key
                checked: parent.field.value === "yes"
                text: parent.field.label
                onToggled: root.backend.setEditorField(parent.field.key, checked ? "yes" : "no")
            }
        }
        Component {
            id: classField
            M.TextField {
                objectName: "catalogClass_" + parent.row + "_" + parent.key
                text: (root.backend.editorClasses[parent.row] || {})[parent.key] || ""
                onTextEdited: root.backend.setEditorClass(parent.row, parent.key, text)
            }
        }
        Component {
            id: classRemove
            M.Button { text: root.backend.texts.removeClass; flat: true; onClicked: root.backend.removeEditorClass(parent.row) }
        }
        ColumnLayout {
            objectName: "catalogChecks"
            Layout.fillWidth: true
            visible: root.backend.editorChecks.length > 0
            spacing: Theme.space.XXS
            Repeater {
                model: root.backend.editorChecks
                M.Label {
                    required property var modelData
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    textStyle: "secondary"
                    text: modelData.text
                    color: modelData.level === "error" ? Theme.colors.danger : Theme.colors.text2
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            visible: root.backend.needsDestination
            spacing: Theme.space.XXS
            M.Label { text: root.backend.texts.destination; Layout.fillWidth: true }
            M.Label { text: root.backend.destinationFolder; textStyle: "caption"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
            M.TextField {
                id: destination
                objectName: "catalogDestination"
                Layout.fillWidth: true
                text: root.backend.destination
                onEditingFinished: root.backend.setDestination(text)
                Accessible.name: root.backend.texts.destination
            }
        }
        M.Label { text: root.backend.error; visible: text.length > 0; color: Theme.colors.danger
            wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
