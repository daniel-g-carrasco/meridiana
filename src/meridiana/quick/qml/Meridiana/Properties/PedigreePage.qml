import QtQuick
import QtQuick.Controls as C
import QtQuick.Templates as T
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    property var backend: null
    color: Theme.colors.card
    M.Label {
        anchors.fill: parent
        anchors.margins: Theme.space.L
        visible: !root.backend || !root.backend.rows.length
        text: root.backend ? root.backend.labels.empty : ""
        verticalAlignment: Text.AlignTop
        wrapMode: Text.Wrap
    }
    ListView {
        id: list
        objectName: "pedigreeList"
        anchors.fill: parent
        anchors.margins: Theme.space.L
        clip: true
        model: root.backend ? root.backend.rows : []
        spacing: Theme.space.S
        boundsBehavior: Flickable.StopAtBounds
        cacheBuffer: 0
        C.ScrollBar.vertical: M.ScrollBar { id: scrollBar }
        delegate: Item {
            id: rowItem
            required property var modelData
            width: list.width - scrollBar.room
            height: content.implicitHeight
            readonly property bool inViewport: root.visible && y + height > list.contentY
                && y < list.contentY + list.height
            Loader {
                id: content
                width: parent.width
                sourceComponent: rowItem.modelData.kind === "formula" ? formulaRow
                    : rowItem.modelData.kind === "quantity" ? quantityRow
                    : rowItem.modelData.kind === "header" ? headerRow : textRow
            }
            Component {
                id: formulaRow
                PedigreeFormula {
                    backend: root.backend
                    formula: rowItem.modelData.text
                    active: rowItem.inViewport
                }
            }
            Component {
                id: quantityRow
                PedigreeQuantity {
                    backend: root.backend
                    row: rowItem.modelData
                    active: rowItem.inViewport
                }
            }
            Component {
                id: textRow
                M.Label {
                    text: (rowItem.modelData.kind === "limit" ? "• " : "") + rowItem.modelData.text
                    textStyle: rowItem.modelData.kind === "record" ? "heading"
                        : rowItem.modelData.kind === "step" ? "strong"
                        : rowItem.modelData.kind === "reference" ? "secondary" : "body"
                    topPadding: rowItem.modelData.kind === "record" ? Theme.space.M : 0
                    wrapMode: Text.Wrap
                }
            }
            Component {
                id: headerRow
                RowLayout {
                    implicitHeight: width >= 600 ? Theme.size.CONTROL : 0
                    visible: width >= 600
                    spacing: Theme.space.S
                    M.Label { text: root.backend.labels.symbol; textStyle: "label"; Layout.preferredWidth: rowItem.width * .12 }
                    M.Label { text: root.backend.labels.quantity; textStyle: "label"; Layout.fillWidth: true }
                    M.Label { text: root.backend.labels.value; textStyle: "label"; Layout.preferredWidth: rowItem.width * .2; horizontalAlignment: Text.AlignRight }
                    M.Label { text: root.backend.labels.source; textStyle: "label"; Layout.preferredWidth: rowItem.width * .32 }
                }
            }
        }
    }
}
