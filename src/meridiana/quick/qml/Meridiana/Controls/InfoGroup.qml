import QtQuick
import Meridiana.Theme

// A group of figures to read at once (R419): the tile's surface and radius (ui/design: Radius.CARD on the field's colour,
// as an inverter's card), columns of «label value» in the small text, a hair between them. As many rows as its height
// holds; what does not fit is in the column's tooltip. Its size comes from outside and never from what it says, so that
// the figures change under the pointer without anything moving. The words come ready: a column is {key, title, tip,
// rows: [{label, value, tone, strong, mark}]}, and an empty column keeps its place.
Rectangle {
    id: root
    property var columns: []
    property var shares: []
    color: Theme.colors.field
    radius: Theme.radius.CARD
    FontMetrics { id: small; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
    readonly property real rowHeight: Math.floor(small.lineSpacing)
    readonly property real pad: Theme.space.S
    readonly property int rowsShown: Math.max(1, Math.floor((height - Theme.space.XXS) / rowHeight))
    readonly property real blockHeight: rowsShown * rowHeight
    Row {
        x: root.pad; y: (root.height - root.blockHeight) / 2
        Repeater {
            model: root.columns.length
            Item {
                id: slot
                required property int index
                readonly property var info: root.columns[index] || ({})
                readonly property real share: root.shares[index] || 1 / root.columns.length
                readonly property var lines: (info.title ? [{label: "", value: info.title, tone: "text", strong: true}] : []).concat(info.rows || []).slice(0, root.rowsShown)
                readonly property real labelWidth: {
                    const revision = Theme.revision
                    let widest = 0
                    for (const line of (info.rows || [])) if (line.label) widest = Math.max(widest, Theme.measureText(line.label, "secondary").width)
                    return Math.ceil(widest)
                }
                objectName: "info-" + (info.key || index)
                width: (root.width - 2 * root.pad) * share; height: root.blockHeight
                Rectangle {
                    visible: slot.index > 0 && slot.info.rows !== undefined
                    x: -Theme.line.HAIR; width: Theme.line.HAIR; height: parent.height; color: Theme.colors.line
                }
                Repeater {
                    model: slot.lines
                    Item {
                        id: entry
                        required property var modelData
                        required property int index
                        readonly property bool titled: modelData.label === ""
                        readonly property real start: (slot.index > 0 ? Theme.space.M : 0) + (titled || slot.labelWidth === 0 ? 0 : slot.labelWidth + Theme.space.S)
                        y: index * root.rowHeight; width: slot.width; height: root.rowHeight
                        Label {
                            visible: !entry.titled
                            x: slot.index > 0 ? Theme.space.M : 0; width: slot.labelWidth; height: parent.height
                            text: entry.modelData.label; textStyle: "secondary"; color: Theme.colors.muted
                        }
                        Label {
                            id: value
                            objectName: "info-value"
                            x: entry.start; width: Math.max(0, parent.width - x - Theme.space.S - (entry.modelData.mark ? 13 + Theme.space.XS : 0)); height: parent.height
                            text: entry.modelData.value; textStyle: "secondary"; elide: Text.ElideRight
                            font.weight: entry.modelData.strong ? Theme.text.strong.weight : Theme.text.body.weight
                            color: entry.modelData.tone === "muted" ? Theme.colors.muted : Theme.colors.text
                        }
                        Icon {
                            id: mark
                            // After the figure, so that the figures of a column stay aligned.
                            visible: !!entry.modelData.mark
                            x: value.x + Math.min(value.contentWidth, value.width) + Theme.space.XS; y: (parent.height - height) / 2; width: 13; height: 13; dimDisabled: false
                            iconName: entry.modelData.mark ? "symbol:" + entry.modelData.mark : ""
                        }
                    }
                }
                HoverHandler { id: hover }
                ToolTip { visible: hover.hovered && !!slot.info.tip; text: slot.info.tip || "" }
            }
        }
    }
}
