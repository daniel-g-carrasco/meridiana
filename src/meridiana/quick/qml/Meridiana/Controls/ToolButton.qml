import QtQuick
import Meridiana.Theme
Button {
    id: root
    property string mode: "under"
    flat: true
    padding: ControlMetrics.toolPad
    topPadding: Theme.space.XXS
    bottomPadding: Theme.space.XXS
    focusPolicy: Qt.NoFocus
    implicitWidth: mode === "icons" ? Theme.bar.ICON_WIDTH : mode === "under"
        ? Math.ceil(Math.max(Theme.bar.WORD_MIN, word.implicitWidth + Theme.bar.PAD) / Theme.bar.STEP.under) * Theme.bar.STEP.under
        : Math.ceil((word.implicitWidth + symbol.width + Theme.bar.WORD_GAP + Theme.bar.PAD) / Theme.bar.STEP.beside) * Theme.bar.STEP.beside
    implicitHeight: mode === "under" ? symbol.height + word.implicitHeight + Theme.bar.PAD : Theme.bar.HEIGHT
    contentItem: Item {
        Icon { id: symbol; name: root.iconName; width: Theme.bar.ICON[root.mode]; height: width
            // QToolButton fixes the under-icon top and uses integral icon boxes.
            x: root.mode === "beside" ? 2 : Math.floor((parent.width-width)/2)
            y: root.mode === "under" ? 2 : Math.floor((parent.height-height)/2)
            color: root.enabled ? Theme.colors.text : Theme.disabledText }
        Label { id: word; text: root.text; textStyle: "secondary"; condensed: true; enabled: root.enabled
            visible: root.mode !== "icons"
            x: root.mode === "beside" ? symbol.width + Theme.bar.WORD_GAP : (parent.width-width)/2
            y: root.mode === "under" ? (parent.height-symbol.height-word.implicitHeight-Theme.space.XXS)/2 + symbol.height + Theme.space.XXS : (parent.height-height)/2 }
    }
}
