import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC
import Meridiana.Theme
import Meridiana.Controls as MC

Rectangle {
    id: page
    objectName: "mapSources"
    required property var backend
    property bool showApply: true
    // R518: inside its window the button «Applica» is the window's, on the row of «Chiudi»
    property bool embedded: false
    readonly property var words: backend.texts
    readonly property var source: backend.currentSource
    readonly property bool editing: backend.currentIndex >= 0
    implicitWidth: MC.ControlMetrics.pageSize.mapSources.width
    implicitHeight: MC.ControlMetrics.pageSize.mapSources.height
    color: embedded ? "transparent" : Theme.colors.card

    // R518, R525: the program's combo (its entries are the menus' ones, its arrow drawn)
    component Choice: MC.ComboBox {
        textRole: "name"
        valueRole: "key"
    }
    component Sources: Column {
        required property var rows
        spacing: 0
        Repeater {
            model: rows
            delegate: Column {
                id: sourceRow
                required property var modelData
                width: parent.width
                padding: 0
                MC.Label {
                    width: parent.width
                    height: implicitHeight + Theme.space.XS * 2
                    text: sourceRow.modelData.name
                    wrapMode: Text.Wrap
                    HoverHandler { id: rowHover }
                    MC.ToolTip { visible: rowHover.hovered; text: sourceRow.modelData.tip }
                }
                MC.Label {
                    width: parent.width
                    text: sourceRow.modelData.licence
                    color: Theme.colors.muted
                    wrapMode: Text.Wrap
                    bottomPadding: Theme.space.XS
                }
                Rectangle { width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line }
            }
        }
    }
    component Field: ColumnLayout {
        required property string field
        required property string label
        spacing: Theme.space.XS
        Layout.fillWidth: true
        MC.Label { text: label; Layout.fillWidth: true; wrapMode: Text.Wrap }
        MC.TextField {
            objectName: "mapSource-" + field
            Layout.fillWidth: true
            enabled: page.editing
            text: field === "url" && page.source.kind !== "xyz"
                ? (page.source.capabilities || page.source.url || "") : (page.source[field] || "")
            onTextEdited: page.backend.updateField(field, text)
            onEditingFinished: page.backend.updateField(field, text.trim())
        }
    }

    MC.ScrollPage {
        leftMargin: 0; air: 0; spacing: 0; implicitHeight: 0; groundAbove: true
        id: scroll
        objectName: "mapSourceScroll"
        anchors.fill: parent
        anchors.bottomMargin: apply.visible ? apply.height+Theme.space.M : 0
        // R520, R489, R530: M.ScrollPage brings the program's bar, in its lane, with the fades at the ends and the rebound
        Column {
            id: body
            x: Theme.space.M; bottomPadding: Theme.space.M
            width: scroll.width - Theme.space.M*2 - Math.max(scroll.bar.room, MC.ControlMetrics.scrollLane + MC.ControlMetrics.scrollGap)
            spacing: Theme.space.L
            MC.Section {
                width: parent.width
                nested: page.embedded         // R518: sections inside a window: a title on a line
                title: page.words.title
                MC.Label { text: page.words.start; width: parent.width }
                Choice {
                    objectName: "mapDefault"
                    width: parent.width
                    model: page.backend.defaultOptions
                    currentIndex: (model || []).findIndex(o => o.key === page.backend.defaultChoice)      // indexOfValue is read once, before the model
                    onActivated: page.backend.setDefault(currentValue)
                }
                MC.Label { width: parent.width; text: page.words.automaticHelp; wrapMode: Text.Wrap; color: Theme.colors.muted }
            }
            MC.Section {
                width: parent.width
                nested: page.embedded         // R518: sections inside a window: a title on a line
                title: page.words.site
                visible: page.backend.siteSources.length > 0
                Sources { width: parent.width; rows: page.backend.siteSources }
            }
            MC.Section {
                width: parent.width
                nested: page.embedded         // R518: sections inside a window: a title on a line
                MC.Button {
                    id: allButton
                    text: page.words.all
                    checkable: true
                    flat: true
                }
                Sources { width: parent.width; rows: page.backend.allSources; visible: allButton.checked }
            }
            MC.Section {
                width: parent.width
                nested: page.embedded         // R518: sections inside a window: a title on a line
                title: page.words.own
                RowLayout {
                    width: parent.width
                    Choice {
                        objectName: "mapCustomChooser"
                        Layout.fillWidth: true
                        model: page.backend.customRows
                        currentIndex: page.backend.currentIndex
                        onActivated: page.backend.select(currentIndex)
                    }
                    MC.Button { objectName: "mapAdd"; text: page.words.new; onClicked: page.backend.add() }
                    MC.Button { objectName: "mapRemove"; text: page.words.remove; enabled: page.editing; onClicked: page.backend.remove() }
                }
                ColumnLayout {
                    width: parent.width
                    visible: page.editing
                    spacing: Theme.space.M
                    Field { field: "name"; label: page.words.name }
                    MC.Label { text: page.words.type }
                    Choice {
                        objectName: "mapSourceKind"
                        Layout.fillWidth: true
                        enabled: page.editing
                        model: [{key:"xyz",name:page.words.xyz},{key:"wms",name:page.words.wms},{key:"wmts",name:page.words.wmts}]
                        currentIndex: Math.max(0, (model || []).findIndex(o => o.key === (page.source.kind || "xyz")))
                        onActivated: page.backend.updateField("kind",currentValue)
                    }
                    Field { field: "url"; label: page.words.address }
                    MC.Button {
                        objectName: "mapRead"
                        text: page.words.read
                        enabled: page.editing && page.source.kind !== "xyz" && !page.backend.busy
                        onClicked: page.backend.readCapabilities()
                    }
                    MC.Label { Layout.fillWidth: true; text: page.backend.readState; visible: text.length > 0; wrapMode: Text.Wrap }
                    MC.Label { text: page.words.layer; visible: page.source.kind !== "xyz" }
                    Choice {
                        objectName: "mapSourceLayer"
                        Layout.fillWidth: true
                        visible: page.source.kind !== "xyz"
                        enabled: page.editing && page.backend.layers.length > 0
                        model: page.backend.layers
                        currentIndex: (model || []).findIndex(o => o.key === (page.source.layer || ""))      // indexOfValue is read once, before the model
                        onActivated: page.backend.chooseLayer(currentValue)
                    }
                    Field { field: "attribution"; label: page.words.attribution }
                    Field { field: "licence"; label: page.words.licence }
                    Field { field: "licence_url"; label: page.words.licenceUrl }
                    RowLayout {
                        Layout.fillWidth: true
                        MC.Label { text: page.words.imagery }
                        Choice {
                            Layout.fillWidth: true
                            enabled: page.editing
                            model: [{key:"photo",name:page.words.photo},{key:"map",name:page.words.map}]
                            currentIndex: (model || []).findIndex(o => o.key === (page.source.imagery || "photo"))      // indexOfValue is read once, before the model
                            onActivated: page.backend.updateField("imagery",currentValue)
                        }
                        MC.Label { text: page.words.zoom }
                        MC.TextField {
                            objectName: "mapSourceZoom"
                            Layout.preferredWidth: Theme.size.CONTROL*2
                            enabled: page.editing
                            text: String(page.source.max_zoom || 19)
                            validator: IntValidator { bottom: 1; top: 24 }
                            inputMethodHints: Qt.ImhDigitsOnly
                            onEditingFinished: page.backend.updateField("max_zoom",text)
                        }
                    }
                    MC.Label {
                        Layout.fillWidth: true
                        text: page.backend.keyState
                        visible: page.editing
                        wrapMode: Text.Wrap
                    }
                    MC.Button {
                        objectName: "mapSetKey"
                        text: page.words.setKey
                        enabled: page.backend.needsKey
                        onClicked: keyDialog.open()
                    }
                    MC.Label {
                        objectName: "mapSourceProblems"
                        Layout.fillWidth: true
                        text: page.backend.problems
                        color: Theme.colors.danger
                        wrapMode: Text.Wrap
                        visible: text.length > 0
                    }
                }
                MC.Label { width: parent.width; text: page.words.customHelp; wrapMode: Text.Wrap; color: Theme.colors.muted }
            }
        }
    }
    MC.Button {
        id: apply
        objectName: "mapApply"
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        text: page.words.apply
        visible: page.showApply && !page.embedded
        onClicked: page.backend.apply()
    }
    MC.Dialog {
        id: keyDialog
        objectName: "mapKeyDialog"
        title: page.words.keyTitle
        anchors.centerIn: parent
        width: Math.min(page.width-24, 480)
        acceptText: "OK"; rejectText: page.words.cancel || "Annulla"
        ColumnLayout {
            width: parent.width
            MC.Label { text: page.words.keyHelp; Layout.fillWidth: true; wrapMode: Text.Wrap }
            MC.TextField {
                id: secret
                objectName: "mapSecret"
                Layout.fillWidth: true
                echoMode: TextInput.Password
                onAccepted: keyDialog.accept()
            }
        }
        onOpened: secret.forceActiveFocus()
        onAccepted: page.backend.setKey(secret.text)
        onClosed: secret.clear()
    }
}
