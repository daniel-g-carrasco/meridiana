import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic as Base
import Meridiana.Theme
import Meridiana.Controls as M
Window {
    id: window
    width: 1366; height: 900; visible: true
    title: galleryText.title
    color: Theme.colors.window
    function showMenu() { split.menu.open() }
    function showDialog() { dialog.open() }
    M.Dialog { id: dialog; x: (window.width-width)/2; y: (window.height-height)/2
        title: galleryText.dialogTitle; acceptText: galleryText.confirm; rejectText: galleryText.cancel
        contentItem: M.Label { text: galleryText.description; wrapMode: Text.WordWrap }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: Theme.space.XXL; spacing: Theme.space.L
        M.Label { text: galleryText.title; textStyle: "display" }
        M.Label { text: galleryText.description; textStyle: "description" }
        GridLayout {
            enabled: galleryState !== "disabled"
            columns: 3; columnSpacing: Theme.space.L; rowSpacing: Theme.space.L
            Layout.fillWidth: true; Layout.fillHeight: true
            M.Card {
                title: galleryText.commands; Layout.fillWidth: true; Layout.columnSpan: 2; Layout.preferredHeight: 166
                Column { spacing: Theme.space.L
                    Row { spacing: Theme.space.M
                        M.Button { objectName: "normalButton"; text: galleryText.normal; tip: galleryText.tip }
                        M.Button { text: galleryText.active; checkable: true; checked: true }
                        M.Button { text: galleryText.disabled; enabled: false }
                        M.Button { text: galleryText.save; iconName: "save" }
                    }
                    Row { spacing: Theme.space.M
                        M.ToolButton { text: galleryText.draw; iconName: "building" }
                        M.ToolButton { text: galleryText.measure; iconName: "measure"; mode: "beside" }
                        M.ToolButton { text: galleryText.save; iconName: "save"; mode: "icons" }
                        M.SplitButton { id: split; objectName: "split"; text: galleryText.draw; iconName: "building"; model: [
                            {text: galleryText.draw, icon: "building"}, {text: galleryText.measure, icon: "measure"},
                            {text: galleryText.disabled, enabled: false}] }
                    }
                }
            }
            M.Card {
                title: galleryText.fields; Layout.fillWidth: true; Layout.preferredWidth: 350; Layout.preferredHeight: 166
                Column { width: parent.width; spacing: Theme.space.S
                    M.TextField { width: parent.width; placeholderText: galleryText.name }
                    Row { width: parent.width; spacing: Theme.space.M
                        M.NumberField { width: (parent.width-parent.spacing)/2; value: 12.5; unit: galleryText.unit; minimum: 0; maximum: 100 }
                        M.ComboBox { width: (parent.width-parent.spacing)/2; model: galleryText.items; textRole: "text" }
                    }
                    M.CheckBox { text: galleryText.check; checked: true }
                }
            }
            M.Card {
                title: galleryText.data; Layout.columnSpan: 2; Layout.fillWidth: true; Layout.fillHeight: true
                M.Table { anchors.fill: parent; selectionMode: "multiple"; columns: galleryText.columns; model: galleryState === "empty" ? [] : galleryText.rows
                    total: galleryText.total; emptyTitle: galleryText.emptyTitle; emptyDescription: galleryText.emptyDescription; emptyActionText: galleryText.compute }
            }
            M.Card {
                title: galleryText.navigation; Layout.fillWidth: true; Layout.fillHeight: true
                Column { anchors.fill: parent; spacing: Theme.space.L
                    M.Segments { width: parent.width; model: galleryText.segments; Component.onCompleted: choose(1) }
                    M.Tabs { width: parent.width; model: galleryText.segments }
                    M.Section { title: galleryText.tree; width: parent.width
                        expanded: galleryState !== "collapsed"; onToggled: value => expanded = value
                        M.Tree { width: parent.width; height: Theme.size.NAV * 5; model: galleryText.nodes; expandedIds: ["project", "building"]; currentIndex: 2 }
                    }
                }
            }
            M.Card {
                title: galleryText.listing; Layout.fillWidth: true; Layout.preferredWidth: 350; Layout.preferredHeight: 190
                M.List { anchors.fill: parent; model: galleryText.items; currentIndex: 0 }
            }
            M.Card {
                title: galleryText.cards; Layout.fillWidth: true; Layout.preferredWidth: 350; Layout.preferredHeight: 190
                closable: true; closeTip: galleryText.close
                M.EmptyState { anchors.fill: parent; title: galleryText.emptyTitle; description: galleryText.emptyDescription; actionText: galleryText.compute }
            }
            M.Card {
                title: galleryText.status; Layout.fillWidth: true; Layout.preferredHeight: 190
                Column { width: parent.width; spacing: Theme.space.L
                    Row { spacing: Theme.space.M
                        M.Pill { text: galleryText.ready }
                        M.Button { text: galleryText.dialog; onClicked: dialog.open() }
                    }
                    M.ProgressBar { width: parent.width; value: 0.65 }
                    Base.SplitView { width: parent.width; height: Theme.size.NAV; orientation: Qt.Horizontal
                        handle: M.SplitHandle { }
                        M.Label { text: galleryText.normal; Base.SplitView.preferredWidth: 120 }
                        M.Label { text: galleryText.active; Base.SplitView.fillWidth: true }
                    }
                }
            }
        }
    }
}
