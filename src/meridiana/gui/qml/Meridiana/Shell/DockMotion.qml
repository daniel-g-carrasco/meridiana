import QtQuick
import Meridiana.Theme

// One clock and curve for cards, the space around them and their landing picture.
Behavior {
    property bool settling: true
    enabled: settling
    NumberAnimation {
        duration: Theme.reducedMotion ? 0 : Theme.motion.CAREFUL
        easing.type: Theme.motion.EASE
    }
}
