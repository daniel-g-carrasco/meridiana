import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
// R555 (15), R607 (Daniel 14/11/2026, among the sketches of r35-pillole: «mi piace il filo grigio (A) ma con le parole
// sopra e la barra sotto (tipo in C)»): the bar of a job is a thread, ControlMetrics.progressThread high with round
// ends: its track in the theme's soft line, what is done in the grey of the secondary text, no accent. A job without a
// total runs a piece a quarter long along it. The words go above it (M.WorkRow), never inside.
T.ProgressBar {
    id: root
    implicitWidth: Theme.size.READING / 2
    implicitHeight: ControlMetrics.progressThread
    background: Rectangle { objectName: "progressGroove"; radius: height / 2; color: Theme.colors.line_soft }
    // R555 (15) (Daniel 09/11/2026: «nelle finestre flottanti i bordi delle barre restano tagliati»): no clip: the piece
    // is the part of its run that lies on the track, with its own round ends, shorter at the two ends of the track.
    // D6: the pieces read their track by its id, never `parent`, which is null while the window is taken apart
    contentItem: Item { id: track
        property real phase: 0
        NumberAnimation on phase { running: root.indeterminate && root.visible && !Theme.reducedMotion
            from: 0; to: 1; duration: Theme.motion.SLOW * 3; easing.type: Theme.motion.EASE_SWING; loops: Animation.Infinite }
        // the run: where the piece would be on an endless track
        readonly property real runWidth: root.indeterminate ? width / 4 : width * root.visualPosition
        readonly property real runX: !root.indeterminate ? 0 : Theme.reducedMotion ? (width-runWidth)/2
                                     : phase * (width+runWidth)-runWidth
        Rectangle { id: fill; objectName: "progressFill"
            x: Math.max(0, track.runX)
            width: Math.max(0, Math.min(track.width, track.runX + track.runWidth) - x)
            height: track.height; radius: height / 2
            color: root.enabled ? Theme.colors.text2 : Theme.disabledText
            visible: width > 0
        }
    }
}
