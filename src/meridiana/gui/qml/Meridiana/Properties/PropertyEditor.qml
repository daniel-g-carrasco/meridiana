import QtQuick
import QtQuick.Layouts
import Meridiana.Controls as M
import Meridiana.Theme

Item {
    id: root
    required property var field
    required property var backend
    property bool interactive: true
    property real labelWidth: 0
    property var labelHint: ({width: 0, wrapped: false})
    property var companion: null
    property bool omitLabel: false
    readonly property var spec: field.data
    // the key of the field's help: the help key on it opens its bubble beside it (Workbench.contextHelp, Help.show)
    readonly property string helpId: spec.help || ""
    readonly property bool hasLabel: !omitLabel && spec.label !== "" && spec.kind !== "check" && spec.kind !== "action"
    readonly property real companionWidth: !companion ? 0 : companion.data.kind === "number" ? 70 : Math.max(60, Math.ceil(Theme.measureText(companion.data.label, "strong").width) + 26)
    readonly property real fieldMinimum: (labelHint.minimum || (spec.kind === "choice" ? 124 : 80))
                                        + (companion ? companionWidth + Theme.space.S : 0)
    readonly property bool inlineField: hasLabel && labelWidth + fieldMinimum + Theme.space.S < width
    implicitHeight: body.implicitHeight
    height: implicitHeight
    function send(value, epoch) { return interactive && backend.commit(spec.id, value, epoch) }
    GridLayout {
        id: body
        width: parent.width
        columns: root.inlineField ? 2 : 1
        columnSpacing: Theme.space.S
        rowSpacing: Theme.space.S
        Item {
            visible: root.hasLabel
            implicitHeight: label.implicitHeight
            Layout.preferredWidth: root.inlineField ? root.labelWidth : -1
            Layout.maximumWidth: root.inlineField ? root.width - root.fieldMinimum - Theme.space.S : root.width
            Layout.fillWidth: !root.inlineField
            M.Label {
                id: label
                text: root.spec.label
                width: Math.min(parent.width, root.labelHint.width || parent.width)
                wrapMode: Text.Wrap
                // Centre the painted letters, including descenders, rather than the font's line box.
                y: parent.height / 2 - M.ControlMetrics.textMiddleOffset(label)
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.space.S
          Loader {
            id: loader
            Layout.fillWidth: true
            Layout.minimumWidth: root.inlineField ? 60 : 0
            sourceComponent: root.spec.kind === "number" || root.spec.kind === "text" ? editorComponent :
                root.spec.kind === "choice" ? choiceComponent : root.spec.kind === "check" ? checkComponent :
                root.spec.kind === "action" ? actionComponent : noteComponent
          }
          M.CopyLabel { visible: root.companion !== null && root.spec.id === "window.day"; text: "/" }
          Loader {
            id: paired
            active: root.companion !== null
            visible: active
            Layout.preferredWidth: root.companionWidth
            // the companion is found again whenever a field of the section tells a change (its binding reads them
            // all): made again only when it is another field (R598: a tip of «Fill» changed remade «Empty»)
            property var loadedFor: undefined
            function loadCompanion() {
                if (root.companion === loadedFor) return
                loadedFor = root.companion
                if (root.companion) setSource("PropertyEditor.qml", {field: root.companion,
                    backend: root.backend, interactive: root.interactive, omitLabel: true})
                else source = ""
            }
            Component.onCompleted: loadCompanion()
            Connections { target: root; function onCompanionChanged() { paired.loadCompanion() } }
            // R629: a kept form is made hidden (not interactive) and shown later; its companion follows, or «Catalogue…»,
            // «Automatic» and «Empty» beside their fields were dead buttons ("previous:") on the form on show
            Binding { target: paired.item; property: "interactive"; value: root.interactive; when: paired.item !== null }
          }
        }
    }
    Component {
        id: editorComponent
        M.TextField {
            id: input
            objectName: (root.interactive ? "editor:" : "previous:") + root.spec.id
            width: loader.width
            enabled: root.spec.enabled
            placeholderText: root.spec.mixed === true ? root.spec.mixedText : ""
            textActions.numericPolicy: root.spec.kind === "number" ? ({unit: root.spec.unit || "", kind: root.spec.unit === "m" ? "length" : root.spec.unit === "\u00b0" ? "angle" : "", minimum: root.spec.minimum, maximum: root.spec.maximum, decimals: root.spec.decimals, locale: Qt.locale()}) : null
            textActions.description: root.spec.tip
            textActions.identity: root.backend.epoch
            property bool dirty: false
            property int draftEpoch: root.backend.epoch
            property bool rejected: false
            invalid: rejected || textActions.pasteError !== ""
            Accessible.name: root.spec.label
            Accessible.description: root.spec.tip
            function sync(force) {
                if (force || !dirty) {
                    text = root.spec.display
                    dirty = false
                    rejected = false
                    textActions.pasteError = ""
                    draftEpoch = root.backend.epoch
                }
            }
            function confirm() {
                if (!dirty) return
                dirty = false
                const ok = root.send(text, draftEpoch)
                sync(true)
                rejected = !ok
            }
            function step(direction) {
                confirm()
                root.send(Math.max(root.spec.minimum, Math.min(root.spec.maximum, root.spec.value + direction * root.spec.step)), root.backend.epoch)
                sync(true)
            }
            rightPadding: root.spec.kind === "number" ? 22 : Theme.space.M
            // R592: the number's steps, as M.NumberField's; R598: made only for a number (a text field had them hidden)
            Loader {
                active: root.spec.kind === "number"
                anchors.right: parent.right; anchors.rightMargin: 3; y: Theme.space.XS; height: parent.height - 2 * Theme.space.XS
                sourceComponent: M.Steppers { onStepped: direction => input.step(direction) }
            }
            WheelHandler { enabled: input.activeFocus && root.spec.kind === "number"
                onWheel: event => { input.step(event.angleDelta.y > 0 ? 1 : -1); event.accepted = true } }
            Component.onCompleted: sync(true)
            onTextEdited: { dirty = true; rejected = false }
            onActiveFocusChanged: {
                if (activeFocus && !textActions.menuActive && !textActions.closingMenu) { draftEpoch = root.backend.epoch; selectAll() }
                if (root.spec.side >= 0 && root.interactive) root.backend.highlightSide(activeFocus || hover.hovered ? root.spec.side : -1)
            }
            onCommitRequested: confirm()
            Keys.onEscapePressed: event => { sync(true); event.accepted = true }
            Keys.onUpPressed: event => {
                if (root.spec.kind === "number") {
                    confirm()
                    root.send(Math.min(root.spec.maximum, root.spec.value + root.spec.step), root.backend.epoch)
                    sync(true)
                    event.accepted = true
                }
            }
            Keys.onDownPressed: event => {
                if (root.spec.kind === "number") {
                    confirm()
                    root.send(Math.max(root.spec.minimum, root.spec.value - root.spec.step), root.backend.epoch)
                    sync(true)
                    event.accepted = true
                }
            }
            Keys.onPressed: event => {
                if (event.key === Qt.Key_F1 && root.helpId !== "") { M.Help.show(root.helpId, root); event.accepted = true }
            }
            Connections { target: root.field; function onChanged() { input.sync(false) } }
            Connections { target: root.backend; function onEpochChanged() { input.sync(true) } }
            HoverHandler {
                id: hover
                onHoveredChanged: if (root.spec.side >= 0 && root.interactive) root.backend.highlightSide(hovered || input.activeFocus ? root.spec.side : -1)
            }
            // R598: made only for a field that has a tip
            Loader { active: root.spec.tip !== ""
                sourceComponent: Item { M.ToolTip { parent: input; text: root.spec.tip; visible: hover.hovered && text !== "" } } }
        }
    }
    Component {
        id: choiceComponent
        M.ComboBox {
            objectName: (root.interactive ? "editor:" : "previous:") + root.spec.id
            width: loader.width
            options: root.spec.options
            value: root.spec.value
            emptyText: root.spec.mixed === true ? root.spec.mixedText : ""
            searchable: root.spec.searchable === true
            searchHint: root.backend.labels.search
            enabled: root.spec.enabled
            accessibleName: root.spec.label
            onChosen: value => root.send(value, root.backend.epoch)
        }
    }
    Component {
        id: checkComponent
        M.CheckBox {
            objectName: (root.interactive ? "editor:" : "previous:") + root.spec.id
            width: loader.width
            checkState: root.spec.mixed === true ? Qt.PartiallyChecked : root.spec.value ? Qt.Checked : Qt.Unchecked
            text: root.spec.label
            enabled: root.spec.enabled
            implicitHeight: Math.max(Theme.size.CONTROL, contentItem.implicitHeight + 4)
            // in the middle of the row, as the box beside it (Daniel 17/11/2026: the box sat lower than its words)
            contentItem: M.Label { text: root.spec.label; wrapMode: Text.Wrap; leftPadding: Theme.icon.CONTROL + Theme.space.M
                verticalAlignment: Text.AlignVCenter }
            onClicked: root.send(checked, root.backend.epoch)
        }
    }
    Component {
        id: actionComponent
        M.Button {
            // the label is the button's words, not a selectable text: a click on it is the button's (R683 made it a
            // ReadableText, which took the click; the words are copied from the button's own menu)
            // ui/style.wrap_button: on more lines rather than widen the panel; the height from the lines laid out.
            implicitHeight: Math.max(Theme.size.CONTROL, word.contentHeight + 2 * Theme.space.XS)
            objectName: (root.interactive ? "action:" : "previous:") + root.spec.id
            width: loader.width
            text: root.spec.label
            enabled: root.spec.enabled
            tip: root.spec.tip
            contentItem: M.Label { id: word; text: root.spec.label; wrapMode: Text.Wrap; textStyle: "strong"; horizontalAlignment: Text.AlignHCenter }
            onClicked: if (root.interactive) root.backend.trigger(root.spec.id)
        }
    }
    Component {
        id: noteComponent
        M.ReadableText {
            width: loader.width
            text: root.spec.display
            textStyle: root.spec.kind === "heading" ? "strong" : "body"
            wrapMode: Text.Wrap
        }
    }
}
