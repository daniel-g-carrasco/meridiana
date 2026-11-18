import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as T
import Meridiana.Theme
import Meridiana.Controls as M

M.ScrollPage {
    id: inspector
    leftMargin: 0; air: 0
    ColumnLayout {
        width: inspector.availableWidth; spacing: Theme.space.M
        M.Label { Layout.fillWidth: true; text: backend.selection.kind === "site" ? L.site : backend.selection.name
            textStyle: "strong" }
        GridLayout {
            columns: 2; Layout.fillWidth: true; columnSpacing: Theme.space.M; rowSpacing: Theme.space.S
            M.Label { text: L.name }
            M.TextField {
                id: nameField; objectName: "nameField"; Layout.fillWidth: true
                property string draftId: ""
                text: backend.selection.name || ""; enabled: backend.selection.editable
                onActiveFocusChanged: if(activeFocus) draftId=backend.selection.oid
                onEditingFinished: if(draftId===backend.selection.oid) backend.rename(text)
                Connections { target: backend; function onSelectionChanged() {
                    nameField.text=backend.selection.name || ""; nameField.draftId=backend.selection.oid
                } }
                Accessible.name: L.name
            }
            M.Label { text: L.height; visible: backend.selection.kind === "building" }
            M.TextField {
                id: heightField; objectName: "heightField"; Layout.fillWidth: true
                property string draftId: ""
                visible: backend.selection.kind === "building"
                text: Number(backend.selection.height || 0).toLocaleString(Qt.locale("it_IT"),'f',2)
                validator: DoubleValidator { bottom: 0.01; top: 500; locale: "it_IT" }
                invalid: !acceptableInput
                rightPadding: Theme.space.XXL
                M.Label { anchors.right: parent.right; anchors.rightMargin: Theme.space.S; anchors.verticalCenter: parent.verticalCenter
                    text: "m"; textStyle: "secondary" }
                onActiveFocusChanged: if(activeFocus) draftId=backend.selection.oid
                onEditingFinished: if(acceptableInput && draftId===backend.selection.oid)
                    backend.setHeight(Number.fromLocaleString(Qt.locale("it_IT"),text))
                Connections { target: backend; function onSelectionChanged() {
                    heightField.text=Number(backend.selection.height || 0).toLocaleString(Qt.locale("it_IT"),'f',2)
                    heightField.draftId=backend.selection.oid
                } }
                Accessible.name: L.height
            }
            Repeater {
                model: backend.selection.kind === "site" ? [L.latitude,shell.site.latitude,L.longitude,shell.site.longitude,L.address,shell.site.address] : []
                M.Label { required property string modelData; required property int index
                    text: modelData; Layout.fillWidth: index%2===1; elide: Text.ElideRight }
            }
        }
        M.Label { Layout.fillWidth: true; text: backend.error; visible: text.length>0
            color: Theme.colors.danger; wrapMode: Text.WordWrap }
        Item { Layout.fillHeight: true }
    }
}
