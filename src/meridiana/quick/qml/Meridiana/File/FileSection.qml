import QtQuick
import QtQuick.Controls.Basic as C
import Meridiana.Theme
import Meridiana.Controls as M

M.ScrollPage {
    leftMargin: 0; air: root.backend.metrics.pageY; airInside: true; spacing: 0; implicitHeight: 0; groundAbove: true
    id: root
    required property var backend
    required property string section
    property var info: backend.sections[section] || ({title: "", description: "", tiles: []})
    property int columns: Math.max(1, Math.min(3, Math.floor((width - 2 * backend.metrics.pageX + Theme.layout.GAP) / (280 + Theme.layout.GAP))))
    function groups() {
        var names = []
        for (var tile of info.tiles) if (names.indexOf(tile.group) < 0) names.push(tile.group)
        return names
    }
    function rows(group) {
        var tiles = info.tiles.filter(t => t.group === group)
        // Bindings can be evaluated before columns receives its initial value.
        var count = Math.ceil(tiles.length / Math.max(1, root.columns)), result = [], at = 0
        for (var i = 0; i < count; ++i) {
            var size = Math.floor(tiles.length / count) + (i < tiles.length % count ? 1 : 0)
            result.push(tiles.slice(at, at + size)); at += size
        }
        return result
    }
    Column {
        id: column
        x: root.backend.metrics.pageX
        width: root.width - 2*x; spacing: 0
        M.Label { objectName: "fileSectionTitle"; text: root.info.title; textStyle: "display" }
        M.Label { width: Math.min(parent.width, 760); text: root.info.description; textStyle: "description"; wrapMode: Text.WordWrap }
        Item { width: 1; height: Theme.space.S }
        Repeater {
            model: root.groups()
            delegate: Column {
                id: group
                required property string modelData
                width: column.width; spacing: Theme.space.M
                Item { width: 1; height: Theme.space.M }
                M.Label { text: group.modelData; textStyle: "label" }
                Repeater {
                    model: root.rows(group.modelData)
                    delegate: Row {
                        id: row
                        required property var modelData
                        width: column.width; spacing: Theme.layout.GAP
                        property real tallest: {
                            var height = 0
                            for (var i = 0; i < children.length; ++i)
                                if (children[i] instanceof FileTile) height = Math.max(height, children[i].implicitHeight)
                            return height
                        }
                        Repeater {
                            model: row.modelData
                            delegate: FileTile {
                                required property var modelData
                                tile: modelData
                                width: (column.width - Theme.layout.GAP * (root.columns - 1)) / Math.max(1, root.columns)
                                height: row.tallest
                                onTriggered: action => root.backend.request(action)
                            }
                        }
                    }
                }
            }
        }
        Column {
            width: parent.width; spacing: Theme.space.S; visible: root.section === "open"
            Item { width: 1; height: Theme.space.M }
            M.Label { width: Math.min(parent.width, 760); text: root.backend.words.elsewhere; textStyle: "secondary"; wrapMode: Text.WordWrap }
            Item { width: 1; height: Theme.space.M }
            M.Label { text: root.backend.words.recent; textStyle: "label" }
            M.Label { text: root.backend.words.noRecent; visible: root.backend.recent.length === 0; textStyle: "description" }
            Repeater {
                model: root.backend.recent
                delegate: M.Button {
                    required property var modelData
                    required property int index
                    objectName: "fileRecent_" + index
                    width: parent.width; height: Theme.size.NAV; flat: true
                    text: modelData.name; tip: modelData.path
                    contentItem: Row {
                        spacing: Theme.space.L
                        M.Label { text: modelData.name; textStyle: "body" }
                        M.Label { text: modelData.folder; textStyle: "secondary" }
                    }
                    onClicked: root.backend.openChosen(modelData.path)
                }
            }
        }
    }
}
