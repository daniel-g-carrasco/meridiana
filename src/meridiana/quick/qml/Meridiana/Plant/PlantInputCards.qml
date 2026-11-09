import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

// ui/plant_page.InputsGrid and InputCard (R298, study 23, B): the inputs of the inverter shown as cards in two columns,
// the cards of a row as tall as the tallest: its name and the mark of the worst of its states on the first row, its
// strings under it, «+» to draw a string on it when it takes more. A card is filled while a string is drawn on it.
GridLayout {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var units: backend.units
    readonly property var strings: backend.strings
    readonly property var inputs: backend.inputs
    required property var menu
    readonly property var inputRows: {
        const rows = root.inputs.filter(i => i.unit === backend.working)
        const lost = root.strings.filter(s => (s.inverter === backend.working || !root.units.some(u => u.number === s.inverter))
                                             && !root.inputs.some(i => i.unit === s.inverter && i.mppt === s.mppt)).map(s => s.index)
        return lost.length ? rows.concat([{unit: backend.working, mppt: 0, label: backend.tr("Without an input"), strings: lost, allowed: lost.length, level: "fail", room: false,
                                           tip: backend.tr("Strings whose inverter is gone: give them another from their menu, or Undo"), addTip: ""}]) : rows
    }
    columns: 2
    columnSpacing: Theme.space.S
    rowSpacing: Theme.space.S
    uniformCellWidths: true
    Repeater {
        model: root.inputRows
        Rectangle {
            id: input
            required property var modelData
            objectName: "plant-input-" + modelData.unit + "-" + modelData.mppt
            Layout.fillHeight: true; Layout.preferredWidth: (root.width - root.columnSpacing) / 2; Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.preferredHeight: column.implicitHeight + 2 * Theme.space.S
            readonly property bool drawing: (root.backend.draftInput[0] === modelData.unit && root.backend.draftInput[1] === modelData.mppt)
                || (root.backend.chosenInput[0] === modelData.unit && root.backend.chosenInput[1] === modelData.mppt)
            color: drawing ? Theme.colors.select_bg : Theme.colors.field
            radius: Theme.radius.CARD
            border.width: drawing ? Theme.line.HAIR : 0
            border.color: Theme.colors.accent
            HoverHandler { id: cardHover }
            TapHandler { onTapped: root.backend.selectInput(input.modelData.unit, input.modelData.mppt) }
            M.ToolTip { visible: cardHover.hovered && text !== ""; text: input.modelData.tip || "" }
            Column {
                id: column
                x: Theme.space.S; y: Theme.space.S; width: parent.width - 2 * x
                spacing: Theme.space.XXS
                Item {
                    width: parent.width
                    height: Math.max(title.implicitHeight, Theme.icon.CONTROL, add.visible ? add.height : 0)
                    M.Label { id: title; x: Theme.space.S; width: mark.x - Theme.space.XS - x; height: parent.height
                        text: input.modelData.label; textStyle: "strong"; elide: Text.ElideRight }
                    Item {
                        id: mark
                        // The mark takes 0.9 of its square, as ui/marks.MarkIcon.
                        x: (add.visible ? add.x - Theme.space.XS : parent.width) - width; y: (parent.height - height) / 2
                        width: Theme.icon.CONTROL; height: width
                        M.Icon { objectName: "plant-input-mark"; anchors.centerIn: parent; width: 14.4; height: 14.4; dimDisabled: false
                            iconName: "symbol:" + (input.modelData.level === "ok" ? "ok" : input.modelData.level === "warn" ? "warn" : input.modelData.level === "fail" ? "fail" : "info") }
                    }
                    M.Button {
                        id: add; objectName: "add-string"
                        x: parent.width - width; y: (parent.height - height) / 2
                        width: Theme.size.CONTROL; height: Theme.size.CONTROL; padding: 0; iconName: "plus"; flat: true
                        visible: input.modelData.room === true
                        tip: input.modelData.addTip || ""
                        onClicked: root.backend.draw(input.modelData.unit, input.modelData.mppt, -1)
                    }
                }
                Column {
                    width: parent.width; spacing: 0
                    Repeater {
                        model: input.modelData.strings
                        Item {
                            id: stringRow
                            required property int modelData
                            readonly property var info: root.strings[modelData] || ({})
                            readonly property bool chosen: root.backend.selected === modelData
                            objectName: "plant-string-row-" + modelData
                            width: parent.width; height: Theme.size.CHIP
                            Rectangle {
                                anchors.fill: parent; radius: Theme.radius.INNER
                                color: Theme.colors.select_bg
                                opacity: stringRow.chosen ? 1 : rowHover.hovered ? .45 : 0
                            }
                            Rectangle {
                                // ui/plant_page.swatch: a square of the string's colour, the radius of the marks, a thin dark line.
                                x: Theme.space.S + 2.5; y: (parent.height - height) / 2
                                width: Theme.icon.CONTROL - 5; height: width; radius: Theme.radius.MARK
                                color: root.backend.stringColours[String(stringRow.modelData)] || Theme.colors.overlay.string_none
                                border.width: 1; border.color: Qt.rgba(0, 0, 0, 60 / 255)
                            }
                            M.Label {
                                x: Theme.space.S + Theme.icon.CONTROL + Theme.space.S; width: count.x - Theme.space.S - x; height: parent.height
                                text: stringRow.info.label || ""; elide: Text.ElideRight
                            }
                            M.Label {
                                id: count
                                x: parent.width - Theme.space.S - implicitWidth; height: parent.height
                                text: String(stringRow.info.modules || 0); textStyle: "secondary"
                            }
                            HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                            M.ToolTip { visible: rowHover.hovered; text: stringRow.info.tip || "" }
                            TapHandler { onTapped: root.backend.selectString(stringRow.modelData)
                                onDoubleTapped: root.backend.draw(input.modelData.unit, input.modelData.mppt, stringRow.modelData) }
                            TapHandler { acceptedButtons: Qt.RightButton; onTapped: root.menu.popupFor(stringRow.modelData) }
                        }
                    }
                }
                M.Label { x: Theme.space.S; text: root.backend.tr("free"); textStyle: "secondary"; visible: input.modelData.strings.length === 0 }
            }
        }
    }
}
