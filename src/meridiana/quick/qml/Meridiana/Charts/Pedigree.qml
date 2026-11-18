import QtQuick
import Meridiana.Theme
import Meridiana.ChartBackend 1.0

// «How it is computed» (R460): each step laid out as the report lays it out (report_typst/steps.py gives both the
// same blocks): the formula on a line of its own with its number, «where:» and the symbols with their values on the
// decimal comma and their sources, the result in evidence, the hour of the example and the formula again with the
// numbers in place of the symbols (R479), the reference.
// The window's colours and font.
Column {
    id: root
    property var records: []
    property var sourceKinds: ({})
    property var limits: []
    property string limitsTitle: ""
    property string limitsIntro: ""
    property Flickable viewport: null
    property bool renderingEnabled: true
    spacing: Theme.space.XL
    ChartServices { id: services }

    function intersects(item) {
        if (!root.visible || !renderingEnabled) return false
        if (!viewport) return true
        // The explicit contentY dependency keeps this binding live while scrolling.
        const offset = viewport.contentY
        let position = 0
        let ancestor = item
        while (ancestor && ancestor !== viewport.contentItem) {
            position += ancestor.y
            ancestor = ancestor.parent
        }
        return position + item.height >= offset && position < offset + viewport.height
    }
    component Copy: Text {
        width: parent.width
        textFormat: Text.PlainText
        wrapMode: Text.Wrap
        font.family: Theme.fontFamily
        font.pixelSize: Theme.type.BODY
        color: Theme.colors.text
    }
    // the symbols of a step: symbol, quantity, the value in two columns (the whole and the rest, so the commas line
    // up), the source; the result's row in evidence
    component QuantityTable: Column {
        id: table
        required property var quantities
        required property var result
        width: parent.width; spacing: 0
        readonly property var widths: [.10, .30, .12, .14, .34]
        function cellX(i) { let x = 0; for (let k = 0; k < i; ++k) x += table.widths[k] * table.width; return x }
        Rectangle {
            width: parent.width; height: heading.implicitHeight + Theme.space.S; color: Theme.colors.field
            border.width: Theme.line.HAIR; border.color: Theme.colors.line
            Item { id: heading; width: parent.width; y: Theme.space.XS; implicitHeight: headSymbol.implicitHeight
                Copy { id: headSymbol; x: table.cellX(0); width: table.width * table.widths[0]; leftPadding: Theme.space.XS
                    text: services.labels.symbol; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold }
                Copy { x: table.cellX(1); width: table.width * table.widths[1]; leftPadding: Theme.space.XS
                    text: services.labels.quantity; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold }
                Copy { x: table.cellX(2); width: table.width * (table.widths[2] + table.widths[3]); rightPadding: Theme.space.S
                    horizontalAlignment: Text.AlignRight
                    text: services.labels.value; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold }
                Copy { x: table.cellX(4); width: table.width * table.widths[4]; leftPadding: Theme.space.XS
                    text: services.labels.source; font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold }
            }
        }
        Repeater { model: table.quantities.concat(table.result ? [table.result] : [])
            Rectangle {
                id: row
                required property var modelData
                required property int index
                readonly property bool isResult: table.result !== null && table.result !== undefined
                                                 && index === table.quantities.length
                width: table.width; height: Math.max(cells.implicitHeight, symbol.height) + Theme.space.S
                color: isResult ? Qt.alpha(Theme.colors.accent, Theme.dark ? 0.22 : 0.10) : "transparent"
                Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: Theme.line.HAIR; color: Theme.colors.line }
                Rectangle { visible: row.isResult; width: 2; height: parent.height; color: Theme.colors.accent }
                Formula { id: symbol; x: Theme.space.XS; y: Theme.space.XS; fit: true; pointSize: 11
                    tex: row.modelData.symbol || ""; inViewport: root.intersects(row) }
                Item { id: cells; width: parent.width; y: Theme.space.XS; implicitHeight: Math.max(label.implicitHeight, source.implicitHeight)
                    Copy { id: label; x: table.cellX(1); width: table.width * table.widths[1]; leftPadding: Theme.space.XS
                        rightPadding: Theme.space.XS; text: row.modelData.label || ""; font.pixelSize: Theme.type.SMALL
                        font.weight: row.isResult ? Font.DemiBold : Font.Normal }
                    // a number: the whole on the left of the comma, right aligned; the decimals and the unit after it
                    Copy { x: table.cellX(2); width: table.width * table.widths[2]; horizontalAlignment: Text.AlignRight
                        text: row.modelData.int !== "" ? row.modelData.int : row.modelData.value
                        font.pixelSize: Theme.type.SMALL; font.weight: row.isResult ? Font.DemiBold : Font.Normal
                        wrapMode: Text.NoWrap; elide: row.modelData.int !== "" ? Text.ElideNone : Text.ElideLeft }
                    Copy { x: table.cellX(3); width: table.width * table.widths[3]; rightPadding: Theme.space.S
                        text: row.modelData.int !== "" ? row.modelData.rest : ""
                        font.pixelSize: Theme.type.SMALL; font.weight: row.isResult ? Font.DemiBold : Font.Normal }
                    Copy { id: source; x: table.cellX(4); width: table.width * table.widths[4]; leftPadding: Theme.space.XS
                        rightPadding: Theme.space.XS; text: row.modelData.source || ""
                        color: Theme.colors.text2; font.pixelSize: Theme.type.SMALL }
                }
            }
        }
    }
    Repeater {
        model: root.records
        delegate: Column {
            id: record
            required property var modelData
            required property int index
            objectName: "pedigree-record-" + index
            width: root.width
            spacing: Theme.space.L
            Copy {
                text: record.modelData.title || ""
                font.pixelSize: Theme.type.HEADING
                font.weight: Font.DemiBold
            }
            Copy {
                visible: !!record.modelData.explanation
                text: record.modelData.explanation || ""
            }
            Repeater {
                model: (record.modelData.messages || []).concat(record.modelData.sources || [])
                delegate: Copy { required property var modelData; text: String(modelData) }
            }
            Repeater {
                model: record.modelData.view || []
                delegate: Column {
                    id: step
                    required property var modelData
                    required property int index
                    objectName: "pedigree-step-" + record.index + "-" + index
                    width: record.width
                    spacing: Theme.space.S
                    Copy { text: step.modelData.title || ""; font.weight: Font.DemiBold }
                    Copy { text: step.modelData.explanation || ""; visible: text.length > 0 }
                    // the equation on a line of its own, in the middle, its number on the right
                    Item {
                        objectName: "pedigree-equation-" + record.index + "-" + step.index
                        visible: !!step.modelData.tex
                        width: parent.width
                        height: visible ? Math.max(equation.height, number.implicitHeight) + Theme.space.S : 0
                        Formula {
                            id: equation
                            y: Theme.space.XS
                            width: parent.width - number.implicitWidth - Theme.space.M
                            centred: true
                            tex: step.modelData.tex || ""
                            inViewport: root.intersects(step)
                        }
                        Text {
                            id: number
                            objectName: "pedigree-number"
                            anchors.right: parent.right
                            anchors.verticalCenter: equation.verticalCenter
                            text: step.modelData.eq ? "(" + step.modelData.eq + ")" : ""
                            font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL; color: Theme.colors.text2
                        }
                    }
                    Copy {
                        visible: (step.modelData.inputs || []).length > 0 || !!step.modelData.result
                        text: services.labels.where; color: Theme.colors.text2
                        font.pixelSize: Theme.type.SMALL; font.weight: Font.DemiBold
                    }
                    QuantityTable {
                        visible: (step.modelData.inputs || []).length > 0 || !!step.modelData.result
                        quantities: step.modelData.inputs || []
                        result: step.modelData.result || null
                    }
                    // the hour of the example, then the formula again with the numbers in place of the symbols, each
                    // line ending in its result, in evidence (R479: the same lines as the report's)
                    Copy {
                        objectName: "pedigree-example"
                        visible: (step.modelData.worked || []).length > 0 && !!step.modelData.example
                        text: step.modelData.example || ""
                        color: Theme.colors.text2
                        font.pixelSize: Theme.type.SMALL
                    }
                    Rectangle {
                        objectName: "pedigree-worked"
                        visible: (step.modelData.worked || []).length > 0
                        width: parent.width
                        height: visible ? lines.implicitHeight + 2 * Theme.space.S : 0
                        color: Qt.alpha(Theme.colors.accent, Theme.dark ? 0.22 : 0.10)
                        Rectangle { width: 2; height: parent.height; color: Theme.colors.accent }
                        Column {
                            id: lines
                            x: Theme.space.M; y: Theme.space.S
                            width: parent.width - Theme.space.M - Theme.space.S
                            spacing: Theme.space.S
                            Repeater {
                                model: step.modelData.worked || []
                                delegate: Formula {
                                    required property var modelData
                                    objectName: "pedigree-worked-line"
                                    width: lines.width
                                    pointSize: 12
                                    tex: modelData
                                    inViewport: root.intersects(step)
                                }
                            }
                        }
                    }
                    Copy {
                        visible: !!step.modelData.reference
                        text: services.labels.reference + ": " + (step.modelData.reference || "")
                        font.pixelSize: Theme.type.CAPTION
                        color: Theme.colors.text2
                    }
                }
            }
        }
    }
    Column {
        width: root.width
        spacing: Theme.space.L
        visible: root.limits.length > 0
        Copy { text: root.limitsTitle; font.pixelSize: Theme.type.HEADING; font.weight: Font.DemiBold }
        Copy { text: root.limitsIntro }
        Repeater {
            model: root.limits
            delegate: Copy { required property var modelData; text: "• " + modelData }
        }
    }
}
