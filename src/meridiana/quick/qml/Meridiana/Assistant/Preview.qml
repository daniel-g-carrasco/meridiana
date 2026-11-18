import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Assistant

ApplicationWindow {
    id: window
    visible: true; width: 1366; height: 900
    title: "Meridio Quick"
    color: Theme.colors.window
    Rectangle {
        anchors.fill: parent; anchors.margins: 12
        color: Theme.colors.view; radius: Theme.radius.CARD
        M.Label { x: 24; y: 24; text: assistantText.name; textStyle: "heading" }
        Rectangle {
            id: propertyCard
            x: parent.width - width - 16; y: 60
            width: 280; height: Math.max(120, parent.height - 160)
            color: Theme.colors.panel; radius: Theme.radius.CARD; border.color: Theme.colors.line
            M.Label { x: 12; y: 12; text: assistantText.properties; textStyle: "title" }
            HelpButton { x: parent.width - width - 12; y: 8; helpId: "phase.production"; targetItem: propertyCard; assistantLayer: layer }
        }
    }
    AssistantLayer {
        id: layer
        anchors.fill: parent
        chat: assistantChat; helpService: assistantHelp
        opened: true
        avatarX: window.width - 380
        avatarY: window.height - 90
        page: assistantPage === "meridio" ? "conversation" : assistantPage
    }
}
