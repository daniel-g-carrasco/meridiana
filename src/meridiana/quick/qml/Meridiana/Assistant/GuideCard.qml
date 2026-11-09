import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

ColumnLayout {
    id: root
    property string title: ""
    property string progress: ""
    property string description: ""
    property var points: []
    property string hint: ""
    property string previousText: ""
    property string nextText: ""
    property string laterText: ""
    property bool canPrevious: true
    property Component headingExtra: null
    property bool animateText: false
    readonly property string wholeText: [description].concat(points).concat([hint]).join("\n")
    property int shownChars: wholeText.length
    property double began: 0
    function startText() {
        began = Date.now()
        shownChars = animateText && !Theme.reducedMotion ? 0 : wholeText.length
    }
    function piece(text, index) {
        const pieces = [description].concat(points).concat([hint])
        let offset = 0
        for (let i=0; i<index; ++i) offset += pieces[i].length+1
        return text.slice(0, Math.max(0, shownChars-offset))
    }
    onWholeTextChanged: startText()
    onAnimateTextChanged: startText()
    Connections { target: Theme; function onReducedMotionChanged() { if (Theme.reducedMotion) root.shownChars = root.wholeText.length } }
    Timer {
        interval: 24; repeat: true; running: root.visible && root.shownChars < root.wholeText.length
        onTriggered: {
            let count = Math.min(root.wholeText.length, Math.floor((Date.now()-root.began)/24)*Math.max(4, Math.ceil(root.wholeText.length/75)))
            while (count < root.wholeText.length && !/\s/.test(root.wholeText[count-1]) && !/\s/.test(root.wholeText[count])) ++count
            root.shownChars = count
        }
    }
    signal previous()
    signal next()
    signal later()
    spacing: Theme.space.S
    Loader { sourceComponent: root.headingExtra; visible: !!root.headingExtra; Layout.fillWidth: true }
    M.Label { text: root.progress; textStyle: "caption"; visible: !root.headingExtra; Layout.fillWidth: true; wrapMode: Text.Wrap }
    M.ScrollPage {
        id: scroll
        Layout.fillWidth: true; Layout.fillHeight: true
        leftMargin: 0; air: 0
        ColumnLayout {
            width: scroll.availableWidth; spacing: Theme.space.M
            M.Label { text: root.title; textStyle: "title"; Layout.fillWidth: true; wrapMode: Text.Wrap }
            M.Label { text: root.piece(root.description, 0); Layout.fillWidth: true; wrapMode: Text.Wrap }
            Repeater {
                model: root.points
                M.Label { required property string modelData; required property int index; text: "• " + root.piece(modelData, index+1); visible: root.piece(modelData, index+1).length > 0; Layout.fillWidth: true; wrapMode: Text.Wrap }
            }
            M.Label { text: root.piece(root.hint, root.points.length+1); textStyle: "strong"; Layout.fillWidth: true; wrapMode: Text.Wrap }
        }
    }
    Flow {
        Layout.fillWidth: true; spacing: Theme.space.XS
        M.Button { text: root.previousText; enabled: root.canPrevious; onClicked: root.previous() }
        M.Button { text: root.nextText; onClicked: root.next() }
        M.Button { text: root.laterText; visible: text.length > 0; onClicked: root.later() }
    }
}
