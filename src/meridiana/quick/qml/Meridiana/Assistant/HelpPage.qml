import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

M.ScrollPage {
    id: root
    required property var service
    leftMargin: 0; air: 0
    ColumnLayout {
        width: root.pageWidth
        spacing: Theme.space.M
        M.Label { text: root.service.content.title || ""; textStyle: "title"; Layout.fillWidth: true; wrapMode: Text.Wrap }
        M.Label { text: root.service.content.text || ""; Layout.fillWidth: true; wrapMode: Text.Wrap }
        M.Label {
            text: (root.service.content.sources || []).join("; ")
            textStyle: "caption"; Layout.fillWidth: true; wrapMode: Text.Wrap
            visible: text.length > 0
        }
        M.Button {
            text: root.service.labels.manual; iconName: "book-open"
            visible: !!root.service.content.manual
            onClicked: root.service.openManual(root.service.content.manual)
        }
        M.Button { text: root.service.labels.ask; onClicked: root.service.ask() }
        M.Button {
            text: root.service.labels.how; visible: !!root.service.content.pedigree
            onClicked: root.service.how()
        }
    }
}
