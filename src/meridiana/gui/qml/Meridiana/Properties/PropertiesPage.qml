import QtQuick
import QtQuick.Controls as C
import Meridiana.Controls as M
import Meridiana.Theme

Rectangle {
    id: root
    required property var backend
    property var sectionStates: ({})
    color: Theme.colors.panel
    implicitWidth: M.ControlMetrics.pageSize.properties.width
    implicitHeight: M.ControlMetrics.pageSize.properties.height
    clip: true
    function closed(key) { return sectionStates[key] === true }
    function toggle(key) {
        let states = Object.assign({}, sectionStates)
        states[key] = !closed(key)
        sectionStates = states
    }
    // One form for each shape the backend has shown, built once and kept (06/11/2026): the current one is shown,
    // replaced only when its successor is ready, never both at once (R677, R377: never an empty Loader).
    ListModel { id: formsModel }
    function addForm(key) { formsModel.append({key: key}) }
    Component.onCompleted: { for (const key of backend.formKeys) addForm(key) }
    // R598: a new form's items are made a slice at a time on the window's turns (an asynchronous Loader): the form
    // on show stays until the one asked for is made, never an empty page; `shownForm` is the one on show.
    property string shownForm: ""
    property var readyForms: ({})
    function formMade(key) {
        let ready = Object.assign({}, readyForms)
        ready[key] = true
        readyForms = ready
        follow()
    }
    function follow() { if (readyForms[backend.currentForm] === true) shownForm = backend.currentForm }
    Connections { target: root.backend; function onFormChanged() { root.follow() } }
    // R631: the body of every side panel (M.PanelPage): its margins, its one scroll with the bar's room always kept
    // (R100) and its veils (EdgeFades)
    M.PanelPage {
        id: scroll
        objectName: "propertiesScroll"
        anchors.fill: parent
        Column {
            id: content
            width: scroll.pageWidth
            spacing: M.ControlMetrics.panelGap
            Item {
                id: forms
                objectName: "currentForm"
                width: parent.width
                height: 0
                Repeater {
                    model: formsModel
                    delegate: Rectangle {
                        id: holder
                        required property string key
                        readonly property bool shown: root.shownForm === key
                        width: forms.width
                        height: made.item ? made.item.height : 0
                        color: root.color
                        visible: shown
                        function place() { if (shown && made.item) forms.height = made.item.height }
                        onShownChanged: place()
                        onHeightChanged: place()
                        Component.onCompleted: place()
                        Loader {
                            id: made
                            // GPU forms, including the selected one, are made between frames.
                            // Software incubation can stall; retain its existing synchronous fallback.
                            asynchronous: GraphicsInfo.api !== GraphicsInfo.Software
                            // no size of its own: the form keeps its width (a Loader with a width would impose it)
                            sourceComponent: PropertyForm {
                                id: form
                                // The kept forms do not follow the width (R470): only the one on show.
                                width: holder.shown ? holder.width : form.width
                                sections: root.backend.formSections(holder.key)
                                backend: root.backend
                                stateOwner: root
                                interactive: holder.shown
                            }
                            onLoaded: { holder.place(); root.formMade(holder.key) }
                        }

                    }
                }
            }
            M.ReadableText {
                objectName: "propertiesError"
                visible: text !== ""
                width: parent.width
                text: root.backend.error
                color: Theme.colors.danger
                wrapMode: Text.Wrap
            }
        }
    }
    Connections {
        target: root.backend
        function onFormAdded(key) { root.addForm(key) }
        function onEpochChanged() {
            // The same subject keeps its scroll; a new kind starts at the top.
            if (root.lastKind !== root.backend.kind) scroll.contentItem.contentY = 0
            root.lastKind = root.backend.kind
        }
    }
    property string lastKind: backend.kind
    // R21-F2: the question before a change that moves the rows is a window (M.Dialog): the title in its header, its
    // buttons in its bar («Adapt» at the left of the bar, as the window's other action, R518)
    M.Dialog {
        id: confirmation
        visible: root.backend.confirmation.action !== undefined
        title: root.backend.confirmation.title || ""
        rejectText: root.backend.labels.cancel
        acceptText: root.backend.confirmation.action === "module" ? root.backend.labels.again : root.backend.labels.accept
        actions: root.backend.confirmation.action === "module" ? [{text: root.backend.labels.adapt}] : []
        onActionTriggered: root.backend.confirm("adapt")
        onAccepted: root.backend.confirm(root.backend.confirmation.action === "module" ? "again" : "accept")
        onClosed: if (root.backend.confirmation.action !== undefined) root.backend.confirm("cancel")
        M.ReadableText { text: root.backend.confirmation.text || ""; wrapMode: Text.Wrap }
    }
}
