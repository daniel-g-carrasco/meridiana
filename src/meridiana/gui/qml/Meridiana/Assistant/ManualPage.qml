import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: root
    required property var service
    spacing: Theme.space.S
    M.ComboBox {
        id: chapters
        Layout.fillWidth: true
        model: root.service.chapters
        textRole: "title"; valueRole: "id"
        font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
        onActivated: root.service.openManual(currentValue)
        currentIndex: { for (let i = 0; i < count; ++i) if (valueAt(i) === root.service.manualChapter) return i; return 0 }
    }
    M.ScrollPage {
        id: scroll
        Layout.fillWidth: true; Layout.fillHeight: true
        M.TextArea {
            id: body; bare: true
            width: scroll.availableWidth
            readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap
            textFormat: TextEdit.MarkdownText
            text: root.service.manualText
            font.family: Theme.fontFamily; font.pixelSize: Theme.text.body.size
            color: Theme.colors.text
            onLinkActivated: link => root.service.followLink(link)
        }
    }
    Connections {
        target: root.service
        function onManualOpened() {
            Qt.callLater(function() {
                const pos = root.service.anchorPosition(root.service.manualAnchor)
                const rect = body.positionToRectangle(pos)
                scroll.contentItem.contentY = Math.max(0, Math.min(rect.y, body.height - scroll.height))
            })
        }
    }
}
