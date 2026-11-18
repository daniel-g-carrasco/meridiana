import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.ProgressBar {
    id: root
    implicitWidth: Theme.size.READING / 2
    implicitHeight: Theme.space.S
    component Skin: Item {
        property string part
        Row {
            anchors.fill: parent
            Repeater {
                model: ["left", "middle", "right"]
                Image {
                    required property string modelData
                    width: modelData === "middle" ? Math.max(0, parent.width - 6) : Math.min(3, parent.width / 2)
                    height: parent.height
                    smooth: false
                    source: "image://meridiana/progress:" + parent.parent.part + "-" + modelData + "/" + Theme.revision + "/" + Screen.devicePixelRatio + "/" + (root.enabled ? "on" : "off")
                }
            }
        }
    }
    background: Skin { part: "groove" }
    contentItem: Item { id: track; clip: true
        property real phase: 0
        NumberAnimation on phase { running: root.indeterminate && root.visible && !Theme.reducedMotion
            from: 0; to: 1; duration: Theme.motion.SLOW * 3; easing.type: Theme.motion.EASE_SWING; loops: Animation.Infinite }
        Skin { id: fill; objectName: "progressFill"; part: "fill"
            width: root.indeterminate ? parent.width / 3 : parent.width * root.visualPosition
            height: parent.height
            x: !root.indeterminate ? 0 : Theme.reducedMotion ? (root.width-width)/2 : track.phase * (root.width+width)-width
        }
    }
}
