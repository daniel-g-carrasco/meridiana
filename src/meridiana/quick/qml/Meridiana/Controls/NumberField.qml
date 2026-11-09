import QtQuick
import Meridiana.Theme
TextField {
    id: root
    property real value: 0
    property real minimum: -1e12
    property real maximum: 1e12
    property int decimals: 2
    property string unit: ""
    property real stepSize: 1
    // As QSpinBox.specialValueText: said in place of the minimum, which then means «chosen by Meridiana» («proposto»).
    property string specialValueText: ""
    signal valueEdited(real value)
    readonly property var italian: Qt.locale("it_IT")
    readonly property bool showsSpecial: specialValueText !== "" && text === specialValueText
    readonly property real currentValue: showsSpecial ? minimum : acceptableInput ? Number.fromLocaleString(italian, text) : value
    function shown(number) { return specialValueText !== "" && number === minimum ? specialValueText : number.toLocaleString(italian, 'f', decimals) }
    text: shown(value)
    validator: DoubleValidator { bottom: root.minimum; top: root.maximum; decimals: root.decimals; locale: "it_IT"; notation: DoubleValidator.StandardNotation }
    rightPadding: suffix.implicitWidth + Theme.space.M + Theme.space.XL + 3
    leftPadding: padding
    horizontalAlignment: TextInput.AlignLeft
    inputMethodHints: Qt.ImhFormattedNumbersOnly
    invalid: !acceptableInput && !showsSpecial
    onValueChanged: if (!activeFocus) text = shown(value)
    onActiveFocusChanged: if (!activeFocus && (showsSpecial || text === "") && specialValueText !== "") text = shown(value)
    onEditingFinished: commit()
    function commit() {
        if (acceptableInput) {
            const next = Number.fromLocaleString(italian, text)
            if (isFinite(next) && next >= minimum && next <= maximum) {
                value = next
                text = shown(value)
                valueEdited(value)
            }
        }
    }
    function step(direction) {
        const typed = currentValue
        value = Math.max(minimum, Math.min(maximum, (isFinite(typed) ? typed : value) + stepSize * direction))
        text = shown(value)
        valueEdited(value)
    }
    Keys.onUpPressed: step(1)
    Keys.onDownPressed: step(-1)
    WheelHandler { enabled: root.activeFocus
        onWheel: event => {
            if (event.angleDelta.y !== 0) { root.step(event.angleDelta.y > 0 ? 1 : -1); event.accepted = true }
        }
    }
    Repeater { model: 2
        Button { required property int index; x: root.width-width-3; y: index === 0 ? Theme.space.XS : root.height-height-Theme.space.XS
            width: Theme.space.XL; height: (root.height-2*Theme.space.XS)/2; padding: 0; flat: true; focusPolicy: Qt.NoFocus
            enabled: root.enabled && (index === 0 ? root.currentValue < root.maximum : root.currentValue > root.minimum)
            autoRepeat: true
            contentItem: Item { Icon { anchors.centerIn: parent; name: index === 0 ? "field:up" : "field:down"; width: 8; height: 6; color: Theme.colors.muted } }
            background: Item {}
            onClicked: root.step(index === 0 ? 1 : -1)
        }
    }
    Label { id: suffix; text: root.unit; enabled: root.enabled; x: Math.min(root.leftPadding + root.contentWidth + 3, root.width-root.rightPadding); anchors.verticalCenter: parent.verticalCenter }
}
