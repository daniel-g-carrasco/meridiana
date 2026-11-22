import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as T
import Meridiana.Theme
import Meridiana.Controls as M

// R631: the body of every side panel (M.PanelPage)
M.PanelPage {
    id: inspector
    ColumnLayout {
        width: inspector.availableWidth; spacing: Theme.space.M
        M.CopyLabel { Layout.fillWidth: true; text: backend.selection.kind === "site" ? L.site : backend.selection.name
            textStyle: "strong" }
        GridLayout {
            columns: 2; Layout.fillWidth: true; columnSpacing: Theme.space.M; rowSpacing: Theme.space.S
            M.CopyLabel { text: L.name }
            M.TextField {
                textActions.identity: backend.selection.oid
                id: nameField; objectName: "nameField"; Layout.fillWidth: true
                property string draftId: ""
                text: backend.selection.name || ""; enabled: backend.selection.editable
                onActiveFocusChanged: if(activeFocus) draftId=backend.selection.oid
                onCommitRequested: if(draftId===backend.selection.oid) backend.rename(text)
                Connections { target: backend; function onSelectionChanged() {
                    nameField.text=backend.selection.name || ""; nameField.draftId=backend.selection.oid
                } }
                Accessible.name: L.name
            }
            M.CopyLabel { text: L.height; visible: backend.selection.kind === "building" }
            M.TextField {
                textActions.identity: backend.selection.oid
                textActions.numericPolicy: ({unit:"m", kind:"length", minimum:0.01, maximum:500, decimals:2, locale:Qt.locale()})
                id: heightField; objectName: "heightField"; Layout.fillWidth: true
                property string draftId: ""
                visible: backend.selection.kind === "building"
                text: Number(backend.selection.height || 0).toLocaleString(Qt.locale(),'f',2)
                validator: DoubleValidator { bottom: 0.01; top: 500; locale: Qt.locale().name }
                invalid: !acceptableInput
                rightPadding: Theme.space.XXL
                M.CopyLabel { anchors.right: parent.right; anchors.rightMargin: Theme.space.S; anchors.verticalCenter: parent.verticalCenter
                    text: "m"; textStyle: "secondary" }
                onActiveFocusChanged: if(activeFocus) draftId=backend.selection.oid
                onCommitRequested: if(acceptableInput && draftId===backend.selection.oid)
                    backend.setHeight(Number.fromLocaleString(Qt.locale(),text))
                Connections { target: backend; function onSelectionChanged() {
                    heightField.text=Number(backend.selection.height || 0).toLocaleString(Qt.locale(),'f',2)
                    heightField.draftId=backend.selection.oid
                } }
                Accessible.name: L.height
            }
            Repeater {
                model: backend.selection.kind === "site" ? [L.latitude,shell.site.latitude,L.longitude,shell.site.longitude,L.address,shell.site.address] : []
                M.CopyLabel { required property string modelData; required property int index
                    text: modelData; Layout.fillWidth: index%2===1; elide: Text.ElideRight }
            }
        }
        M.ReadableText { Layout.fillWidth: true; text: backend.error; visible: text.length>0
            color: Theme.colors.danger; wrapMode: Text.WordWrap }
        Item { Layout.fillHeight: true }
    }
}
