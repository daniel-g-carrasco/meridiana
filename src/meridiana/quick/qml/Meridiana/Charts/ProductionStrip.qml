import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// What stands at the right of the Production bar: the weather's source and the two shadows. R553 (Daniel 08/11/2026:
// «guarda anche sta schifezza. Sti controlli inoltre vorrei che stessero all'interno di un gruppo allo stesso modo che
// facciamo in impianto»): in a group as the Plant's summary (M.InfoGroup: the field's surface, the card's radius), and
// never taller or wider than the room it is given. Two lines high the shadows stand one above the other, one line high
// side by side; the weather keeps the lines it has room for, the rest in its tooltip, and goes first when the room is
// short; then the names of the shadows are cut (their tooltip says them whole). `need` is the width it asks to show
// everything (PhaseHeader.trailing; where there are views it goes above them with less).
M.InfoGroup {
    id: root
    objectName: "productionStrip"
    readonly property real unit: Theme.type.BODY / 13
    readonly property real pad: Theme.space.S
    readonly property real line: Math.ceil(Theme.measureText("Hg", "body").height)
    readonly property bool stacked: height >= 2 * line + 3 * Theme.space.XXS
    readonly property real rowHeight: stacked ? Math.floor((height - 2 * Theme.space.XXS) / 2) : Math.min(height, Theme.size.CONTROL)
    readonly property real checksWidth: stacked ? Math.max(horizon.implicitWidth, near.implicitWidth)
                                                : horizon.implicitWidth + Theme.space.L + near.implicitWidth
    readonly property real meteoLeast: 140 * unit
    readonly property real need: 2 * pad + meteoLeast + Theme.space.L + checksWidth
    readonly property real inner: Math.max(0, width - 2 * pad)
    readonly property bool meteoShown: inner - checksWidth - Theme.space.L >= meteoLeast
    readonly property real checksRoom: meteoShown ? checksWidth : inner
    // the shadows' widths: whole when there is room, cut in proportion when not
    function shadowWidth(box) {
        if (stacked || checksRoom >= checksWidth) return box.implicitWidth
        return Math.max(0, (checksRoom - Theme.space.L) * box.implicitWidth / (horizon.implicitWidth + near.implicitWidth))
    }
    implicitHeight: 2 * Theme.size.CONTROL + 2 * Theme.space.XXS + 2 * pad
    Column {
        id: meteo
        visible: root.meteoShown
        x: root.pad; anchors.verticalCenter: parent.verticalCenter
        width: Math.max(0, Math.min(44 * Theme.type.BODY * .55, root.inner - Theme.space.L - checks.width))
        M.Label { objectName: "meteoState"; width: parent.width; text: productionEditor.meteo.first; elide: Text.ElideRight }
        M.Label { width: parent.width; text: productionEditor.meteo.second; textStyle: "secondary"; elide: Text.ElideRight
            visible: text !== "" && root.height >= 2 * root.line }
        HoverHandler { id: meteoHover }
        M.ToolTip { text: productionEditor.meteo.text; visible: meteoHover.hovered }
    }
    Grid {
        id: checks
        columns: root.stacked ? 1 : 2
        columnSpacing: Theme.space.L
        x: root.width - root.pad - width; anchors.verticalCenter: parent.verticalCenter
        M.CheckBox { id: horizon; objectName: "useHorizon"; text: productionEditor.meteo.horizonLabel; checked: productionEditor.meteo.horizon
            width: root.shadowWidth(horizon); height: root.rowHeight
            Component.onCompleted: { contentItem.wrapMode = Text.NoWrap; contentItem.elide = Text.ElideRight; contentItem.verticalAlignment = Text.AlignVCenter }
            onToggled: { productionEditor.commit("losses.use_horizon", checked, productionEditor.epoch); checked = Qt.binding(() => productionEditor.meteo.horizon) }
            M.ToolTip { text: horizon.text; visible: horizon.hovered && horizon.width < horizon.implicitWidth } }
        M.CheckBox { id: near; objectName: "useNear"; text: productionEditor.meteo.nearLabel; checked: productionEditor.meteo.near
            width: root.shadowWidth(near); height: root.rowHeight
            Component.onCompleted: { contentItem.wrapMode = Text.NoWrap; contentItem.elide = Text.ElideRight; contentItem.verticalAlignment = Text.AlignVCenter }
            onToggled: { productionEditor.commit("losses.use_near", checked, productionEditor.epoch); checked = Qt.binding(() => productionEditor.meteo.near) }
            M.ToolTip { text: (near.width < near.implicitWidth ? near.text + "\n" : "") + productionEditor.meteo.nearTip; visible: near.hovered } }
    }
}
