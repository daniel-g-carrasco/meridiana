import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.DialogPreview

// The previews of «Edificio da modello» and «Pensilina per parcheggio»: the drawing is the item's (DialogPreview), the
// measures on it are the plan's sides' pills (M.LengthPill) where the item places them, and a click on one opens the
// plan's field (M.OverlayField) in its place, with the side's number and the unit, as on the plan (Plan/SideEditor).
// R555 (12) (Daniel 09/11/2026: «la casella per scrivere una misura compare in basso a destra senza motivo: va scritta
// dentro la pillola della misura già presente, e quelle pillole sono le stesse della pianta»): the pills were painted
// by the item in a look of their own, and the field was a common text field in a popup of its own, 120 px wide.
Item {
    id: root
    property var backend
    property string editingSide: ""
    readonly property var editingPill: drawing.pills.find(function(p) { return p.key === root.editingSide }) || null
    function closeField() { root.editingSide = "" }
    DialogPreview {
        id: drawing; anchors.fill: parent
        visible: root.backend && root.backend.kind !== "ifc"
        Image { anchors.fill: parent; source: drawing.source; cache: false; asynchronous: false }
        backend: root.backend
        deviceScale: Screen.devicePixelRatio
        colors: Theme.colors
        textFont: Qt.font({family: Theme.fontFamily, pixelSize: Theme.text.body.size})
        editingKey: root.editingSide
        onEditRequested: (key, value, x, y) => {
            root.editingSide = key
            field.edit(value)
        }
        Repeater {
            // one pill for each measure, kept while the view turns (the records change, the pills stay)
            model: drawing.pills.length
            delegate: M.LengthPill {
                required property int index
                readonly property var pill: drawing.pills[index] || ({})
                objectName: "previewPill_" + (pill.key || "")
                visible: pill.key !== root.editingSide
                x: pill.x || 0; y: pill.y || 0; width: pill.width || 0; height: pill.height || 0
                ground: drawing.pillColors.label_bg
                ink: pill.lit ? drawing.pillColors.sel : drawing.pillColors.label_fg
                value: pill.text || ""; badge: pill.badge || ""
            }
        }
        M.OverlayField {
            // the plan's field over a view (R534), where the pill was
            id: field
            objectName: "dialog_measure"
            colours: drawing.pillColors
            visible: root.editingPill !== null
            badge: root.editingPill ? root.editingPill.badge : ""
            unit: root.editingPill ? root.editingPill.unit : "m"
            sample: root.editingPill && root.editingPill.unit === "°" ? "00,0" : "00,00"
            x: root.editingPill ? Math.max(0, Math.min(root.width - width, root.editingPill.x)) : 0
            y: root.editingPill ? Math.max(0, Math.min(root.height - height, root.editingPill.y)) : 0
            onAccepted: {
                if (root.backend.editMeasure(root.editingSide, text)) root.closeField()
                else { input.forceActiveFocus(); input.selectAll() }
            }
            onCanceled: root.closeField()
            onFocusLost: root.closeField()
        }
    }
    IfcPreview { anchors.fill: parent; visible: root.backend && root.backend.kind === "ifc"; backend: root.backend }
}
