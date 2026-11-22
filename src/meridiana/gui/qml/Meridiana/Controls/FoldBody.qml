import QtQuick
import Meridiana.Theme

// The common section motion: lay out the full body, reveal it without squeezing.
Item {
    id: root
    property bool expanded: true
    property real contentHeight: childrenRect.height
    property real progress: expanded ? 1 : 0
    Behavior on progress { NumberAnimation { duration: Theme.reducedMotion ? 0 : Theme.motion.NORMAL; easing.type: Theme.motion.EASE } }
    height: Math.round(contentHeight * progress)
    opacity: progress
    visible: height > 0
    enabled: expanded
    clip: true
}
