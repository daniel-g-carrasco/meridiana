import QtQuick
import QtQuick.Controls as C
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Item {
    id: root
    property var backend
    RowLayout {
        anchors.fill: parent
        spacing: Theme.space.XL
        ColumnLayout {
            Layout.preferredWidth: root.backend && root.backend.kind === "new" ? 350 : Math.min(420, root.width * 0.46)
            Layout.minimumWidth: Math.min(340, root.width * 0.4)
            Layout.maximumWidth: root.backend && root.backend.kind === "new" ? 460 : 420
            Layout.fillWidth: false
            Layout.fillHeight: true
            M.ScrollPage {
            Layout.fillWidth: true
            Layout.fillHeight: true
            leftMargin: 0; air: 0
            Column {
                width: parent.width
                spacing: Theme.space.M
                RowLayout {
                    width: parent.width
                    M.TextField {
                        objectName: "site_query"
                        Layout.fillWidth: true
                        text: root.backend ? root.backend.state.query : ""
                        placeholderText: root.backend ? root.backend.labels.queryHint : ""
                        onTextEdited: root.backend.setValue("query", text)
                        onAccepted: root.backend.search()
                    }
                    M.Button {
                        text: root.backend ? root.backend.labels.search : ""
                        enabled: root.backend && !root.backend.state.reserved
                        onClicked: root.backend.search()
                    }
                }
                RowLayout {
                    width: parent.width
                    ColumnLayout {
                        Layout.fillWidth: true
                        M.Label {
                            text: root.backend ? root.backend.labels.latitude : ""
                            textStyle: "secondary"
                        }
                        M.TextField {
                            id: latitudeField
                            Layout.fillWidth: true
                            objectName: "site_latitude"
                            placeholderText: "45.5226"
                            Binding { target: latitudeField; property: "text"; value: root.backend ? String(root.backend.state.latitude) : ""; when: !latitudeField.activeFocus; restoreMode: Binding.RestoreNone }
                            onTextEdited: root.backend.setValue("latitude", text)
                        }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true
                        M.Label {
                            text: root.backend ? root.backend.labels.longitude : ""
                            textStyle: "secondary"
                        }
                        M.TextField {
                            id: longitudeField
                            Layout.fillWidth: true
                            objectName: "site_longitude"
                            placeholderText: "9.0300"
                            Binding { target: longitudeField; property: "text"; value: root.backend ? String(root.backend.state.longitude) : ""; when: !longitudeField.activeFocus; restoreMode: Binding.RestoreNone }
                            onTextEdited: root.backend.setValue("longitude", text)
                        }
                    }
                }
                M.Label {
                    width: parent.width
                    text: root.backend ? root.backend.labels.coordinatesHelp : ""
                    textStyle: "secondary"; wrapMode: Text.WordWrap
                }
                M.Label {
                    width: parent.width
                    text: root.backend ? root.backend.labels.privacy : ""
                    textStyle: "secondary"
                    wrapMode: Text.WordWrap
                }
                Repeater {
                    model: root.backend ? root.backend.state.localPlaces : []
                    delegate: M.Button {
                        required property var modelData
                        required property int index
                        width: parent.width
                        text: modelData.label
                        flat: true
                        onClicked: root.backend.choosePlace(index, false)
                    }
                }
                Repeater {
                    model: root.backend ? root.backend.state.onlinePlaces : []
                    delegate: M.Button {
                        required property var modelData
                        required property int index
                        width: parent.width
                        text: modelData.label
                        flat: true
                        onClicked: root.backend.choosePlace(index, true)
                    }
                }
                M.CheckBox {
                    visible: root.backend && root.backend.kind === "new"
                    text: root.backend ? root.backend.labels.optional : ""
                    checked: root.backend ? root.backend.state.optional : false
                    onToggled: root.backend.setValue("optional", checked)
                }
                FormFields {
                    width: parent.width
                    backend: root.backend
                    visible: root.backend && root.backend.kind === "new" && root.backend.state.optional
                }
            }
            }
            M.Button {
                objectName: root.backend && root.backend.kind === "new" ? "dialog_accept" : "new_accept_unused"
                Layout.alignment: Qt.AlignHCenter
                visible: root.backend && root.backend.kind === "new"
                text: root.backend ? root.backend.labels.create : ""
                enabled: root.backend && root.backend.state.valid && !root.backend.busy
                onClicked: root.backend.accept()
            }
        }
        SiteMap {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumWidth: 220
            backend: root.backend
        }
    }
}
