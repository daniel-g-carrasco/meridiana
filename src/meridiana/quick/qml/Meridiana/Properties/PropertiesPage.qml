import QtQuick
import QtQuick.Controls as C
import Meridiana.Controls as M
import Meridiana.Theme

Rectangle {
    id: root
    required property var backend
    property var sectionStates: ({})
    property int transitionCount: 0
    property int leavingCount: 0
    property bool transitioning: leavingCount > 0
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
    // the one leaving stays on top for the crossfade as it is, nothing is built twice (R377: never an empty Loader).
    ListModel { id: formsModel }
    function addForm(key) { formsModel.append({key: key}) }
    Component.onCompleted: { for (const key of backend.formKeys) addForm(key) }
    // R21 F1: the page of the house, its bar's room always kept (R100) and its veils (EdgeFades in place of the
    // ScrollEdges of this page)
    M.ScrollPage {
        id: scroll
        objectName: "propertiesScroll"
        anchors.fill: parent
        // the 12 px of QScrollArea's bar (Widgets parity): the lane and its gap, as M.ScrollBar.room
        leftMargin: 0; rightMargin: Theme.space.XXS; air: 0
        Column {
            id: content
            width: scroll.pageWidth
            spacing: Theme.space.S
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
                        readonly property bool shown: root.backend.currentForm === key
                        property bool leaving: false
                        width: forms.width
                        height: form.height
                        color: root.color
                        visible: shown || leaving
                        z: leaving ? 1 : 0
                        layer.enabled: leaving
                        function place() { if (shown) forms.height = form.height }
                        onShownChanged: {
                            if (shown) { place(); return }
                            if (Theme.reducedMotion) return
                            fade.stop()
                            leaving = true
                            root.leavingCount += 1
                            root.transitionCount += 1
                            fade.start()
                        }
                        onHeightChanged: place()
                        Component.onCompleted: place()
                        PropertyForm {
                            id: form
                            // The kept forms do not follow the width (R470): only the one on show, or leaving.
                            width: holder.shown || holder.leaving ? parent.width : form.width
                            sections: root.backend.formSections(holder.key)
                            backend: root.backend
                            stateOwner: root
                            interactive: holder.shown
                        }
                        MouseArea { anchors.fill: parent; visible: holder.leaving; acceptedButtons: Qt.AllButtons; onWheel: wheel => { wheel.accepted = true } }
                        NumberAnimation {
                            id: fade
                            target: holder
                            property: "opacity"
                            from: 1; to: 0
                            duration: Theme.motion.NORMAL
                            easing.type: Theme.motion.EASE
                            onFinished: { holder.leaving = false; holder.opacity = 1; root.leavingCount = Math.max(0, root.leavingCount - 1) }
                        }
                    }
                }
            }
            M.Label {
                objectName: "propertiesError"
                visible: text !== ""
                width: parent.width - 2 * Theme.space.M
                x: Theme.space.M
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
        parent: C.Overlay.overlay
        anchors.centerIn: parent
        width: Math.min(M.ControlMetrics.dialogWidth.normal, parent ? parent.width - 2 * M.ControlMetrics.dialogEdge : M.ControlMetrics.dialogWidth.normal)
        visible: root.backend.confirmation.action !== undefined
        title: root.backend.confirmation.title || ""
        rejectText: root.backend.labels.cancel
        acceptText: root.backend.confirmation.action === "module" ? root.backend.labels.again : root.backend.labels.accept
        actions: root.backend.confirmation.action === "module" ? [{text: root.backend.labels.adapt}] : []
        onActionTriggered: root.backend.confirm("adapt")
        onAccepted: root.backend.confirm(root.backend.confirmation.action === "module" ? "again" : "accept")
        onClosed: if (root.backend.confirmation.action !== undefined) root.backend.confirm("cancel")
        contentItem: M.Label { text: root.backend.confirmation.text || ""; wrapMode: Text.Wrap }
    }
}
