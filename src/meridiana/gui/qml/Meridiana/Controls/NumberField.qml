import QtQuick
import Meridiana.Theme
TextField {
    id: root
    textActions.numericPolicy: ({unit: unit, kind: "", minimum: minimum, maximum: maximum, decimals: decimals, locale: numbers})
    property real value: 0
    property real minimum: -1e12
    property real maximum: 1e12
    property int decimals: 2
    property string unit: ""
    property real stepSize: 1
    // As QSpinBox.specialValueText: said in place of the minimum, which then means «chosen by Meridiana» («proposto»).
    property string specialValueText: ""
    signal valueEdited(real value)
    // the window's language (create_app sets Qt's locale): 12,50 in Italian, 12.50 in English (r35-segni: it was Italian
    // whatever the language)
    readonly property var numbers: Qt.locale()
    readonly property bool showsSpecial: specialValueText !== "" && text === specialValueText
    readonly property real currentValue: showsSpecial ? minimum : acceptableInput ? Number.fromLocaleString(numbers, text) : value
    function shown(number) { return specialValueText !== "" && number === minimum ? specialValueText : number.toLocaleString(numbers, 'f', decimals) }
    text: shown(value)
    validator: DoubleValidator { bottom: root.minimum; top: root.maximum; decimals: root.decimals; locale: root.numbers.name; notation: DoubleValidator.StandardNotation }
    rightPadding: suffix.implicitWidth + Theme.space.M + Theme.space.XL + 3
    horizontalAlignment: TextInput.AlignLeft
    inputMethodHints: Qt.ImhFormattedNumbersOnly
    invalid: !acceptableInput && !showsSpecial
    onValueChanged: if (!activeFocus) text = shown(value)
    onActiveFocusChanged: if (!activeFocus && !textActions.menuActive && (showsSpecial || text === "") && specialValueText !== "") text = shown(value)
    onCommitRequested: commit()
    function commit() {
        if (acceptableInput) {
            const next = Number.fromLocaleString(numbers, text)
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
    Steppers { x: root.width-width-3; y: Theme.space.XS; height: root.height-2*Theme.space.XS     // R592
        upEnabled: root.currentValue < root.maximum; downEnabled: root.currentValue > root.minimum
        onStepped: direction => root.step(direction) }
    Label { id: suffix; text: root.unit; enabled: root.enabled; x: Math.min(root.leftPadding + root.contentWidth + 3, root.width-root.rightPadding)
        verticalAlignment: Text.AlignTop; anchors.baseline: parent.baseline }   // R582: on the number's baseline
}
