import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// R667 (Daniel 16/11/2026: «il caricamento della risposta di meridio deve essere mostrato in modo carino direttamente in
// chat, nel punto in cui comparirà la risposta», «non come quello che c'è adesso... brutto e scattoso»): where his answer
// will come, a short line of what he is doing («Thinking…», «Reading the checks…»), muted, with a soft glint that runs
// across it. The old sign, three dots in the status row, was moved by a Timer of the window's thread (a step every
// 300 ms): it jumped by design and stopped while the window was busy laying out the answer. Here everything that moves
// is an Animator (XAnimator, OpacityAnimator), run by the thread that draws: smooth while the text comes. With less
// motion the line stands still. It comes in with a fade; when the first words come it leaves its place to them at
// once, in the same place and as tall as a line of an answer (`lineHeight`, `lineLeft`, `lineTop`: Conversation.qml
// measures them on an answer of one line), so nothing moves; a wait that ends without words fades out.
Item {
    id: root
    property string text
    property bool shown: false
    property bool answered: false           // the first words came: the place is theirs at once
    property real lineHeight: 0
    property real lineLeft: 0
    property real lineTop: 0
    readonly property bool moving: !Theme.reducedMotion && visible && !answered
    implicitHeight: (shown || opacity > 0) && !answered ? lineHeight : 0
    height: implicitHeight
    opacity: shown ? 1 : 0
    visible: (shown || opacity > 0) && !answered
    Behavior on opacity { OpacityAnimator { duration: Theme.motion.NORMAL; easing.type: Theme.motion.EASE } }
    M.Label { id: words; x: root.lineLeft; y: root.lineTop; text: root.text; color: Theme.colors.muted }
    // the glint: the same words in the text's colour seen through windows that run across them, each narrower than the
    // one before and drawn over it, so the light is strongest in its middle and fades to its edges; each window goes
    // right while the words in it go left as much, so they stay on the muted ones
    readonly property real band: Math.max(Theme.space.XXXL, words.width * 0.4)
    readonly property real from: words.x - band / 2         // the middle of the light, from before the words...
    readonly property real to: words.x + words.width + band / 2    // ...to after them
    readonly property int layers: 5
    Repeater {
        model: root.layers
        Item {
            id: glint
            required property int index
            readonly property real span: root.band * (index + 1) / root.layers
            x: root.from - span / 2; y: words.y
            width: span; height: words.height
            clip: true
            M.Label { id: lit; x: words.x - glint.x; text: root.text; color: Theme.colors.text; opacity: 0.3 }
            // an Animator takes its ends when it starts: started again when the words change (their width came after)
            readonly property real path: root.to - root.from + span
            onPathChanged: if (sweep.running) sweep.restart()
            SequentialAnimation {
                id: sweep
                running: root.moving && words.width > 0; loops: Animation.Infinite
                ParallelAnimation {
                    XAnimator { target: glint; from: root.from - glint.span / 2; to: root.to - glint.span / 2
                        duration: Theme.motion.SHIMMER; easing.type: Theme.motion.EASE_SWING }
                    XAnimator { target: lit; from: words.x - root.from + glint.span / 2; to: words.x - root.to + glint.span / 2
                        duration: Theme.motion.SHIMMER; easing.type: Theme.motion.EASE_SWING }
                }
                PauseAnimation { duration: Theme.motion.SHIMMER_REST }
            }
        }
    }
}
