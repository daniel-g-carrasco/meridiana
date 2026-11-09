import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// ui/plant_page.ClipScale (R62, R353): the plant's DC/AC ratio and the energy the inverter cuts, a line each, then the
// energy on a track from 0 to 6 % of the year, the span in the state's colour, a tick at each threshold. Before the
// computation no track: a pale band read as a figure.
Column {
    id: root
    required property var backend
    // The lists of the backend read and converted once for this component, not at every binding (06/11/2026)
    readonly property var plantData: backend.data
    readonly property var loss: root.plantData.clippingPct
    readonly property bool computed: loss !== null && loss !== undefined
    readonly property real end: 6
    readonly property color spanColor: !computed || loss < 1 ? backend.statusColors.ok : loss <= 3 ? backend.statusColors.check : backend.statusColors.fail
    FontMetrics { id: small; font.family: Theme.fontFamily; font.pixelSize: Theme.type.SMALL }
    spacing: 0
    Repeater {
        model: [{label: root.backend.tr("DC/AC now"), value: root.plantData.ratio || "", strong: false, tone: Theme.colors.text},
                {label: root.backend.tr("Energy cut"), value: root.computed ? root.plantData.clipping : root.backend.tr("after the computation"), strong: root.computed, tone: root.computed ? Theme.colors.text : Theme.colors.muted}]
        Item {
            required property var modelData
            width: root.width; height: Math.ceil(small.lineSpacing)
            M.Label { width: parent.width - value.width - Theme.space.S; height: parent.height; text: modelData.label; textStyle: "secondary"; color: Theme.colors.muted; elide: Text.ElideRight }
            M.Label { id: value; anchors.right: parent.right; height: parent.height; text: modelData.value; textStyle: "secondary"; color: modelData.tone; font.weight: modelData.strong ? Theme.text.strong.weight : Theme.text.body.weight }
        }
    }
    Item {
        objectName: "plant-clip-track"
        width: root.width; height: Theme.space.XS + 2 * 2 + 6; visible: root.computed
        readonly property real trackY: Theme.space.XS + 2
        Rectangle { y: parent.trackY; width: parent.width; height: 6; radius: 3; color: Theme.colors.line; opacity: .35 }
        Rectangle { objectName: "plant-clip-span"; y: parent.trackY; width: Math.max(6, parent.width * Math.min(root.loss, root.end) / root.end); height: 6; radius: 3; visible: root.loss > 0; color: root.spanColor }
        Repeater { model: [1, 3]; Rectangle { required property real modelData; x: Math.round(root.width * modelData / root.end); y: Theme.space.XS; width: Theme.line.HAIR; height: 10; color: Theme.colors.text; opacity: .6 } }
    }
    HoverHandler { id: hover }
    M.ToolTip { visible: hover.hovered; text: root.computed ? root.backend.tr("Energy cut beyond the inverter's nominal power: green under 1 %, yellow to 3 %, red beyond (the same thresholds as the checks)") : root.backend.tr("The energy the inverter cuts shows once the production is computed") }
}
