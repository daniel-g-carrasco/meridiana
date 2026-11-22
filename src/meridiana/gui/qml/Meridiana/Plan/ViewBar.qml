import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: bar
    required property var plan
    required property var backend
    property string viewMode: "both"
    signal backgroundRequested()
    // R480: the background's menu, so that its button stays pressed while it is open and a second click closes it
    property var backgroundMenu: null
    // the sun map (study 45, package 5): its button turns it on and off, its arrow opens its panel; shown only where
    // the window has a map (plan.sun)
    property var sunPanel: null
    width: buttons.implicitWidth+6
    height: buttons.implicitHeight+6
    radius: Theme.radius.CONTROL
    color: Theme.colors.panel
    border.color: Theme.colors.line
    Row {
        id: buttons
        x: 3; y: 3; spacing: 1
        Repeater {
            model: backend.viewTools
            delegate: Row {
                required property var modelData
                required property int index
                readonly property bool sunMap: modelData.command==="sun_map"
                readonly property bool arrowed: modelData.command==="background" || sunMap
                visible: !sunMap || !!bar.plan.sun
                spacing: 1
                Item {
                    visible: index>0 && backend.viewTools[index-1].group!==modelData.group
                    width: visible ? 1 : 0; height: 19+2*Theme.space.XS
                    Rectangle { width: 1; height: 16; anchors.centerIn: parent; color: Theme.colors.line }
                }
                Loader {
                    sourceComponent: arrowed ? splitControl : plainControl
                }
                Component {
                    id: splitControl
                    M.SplitButton {
                        objectName: "planView-" + modelData.command
                        compact: true; text: modelData.tip
                        checked: sunMap && !!bar.plan.sun && bar.plan.sun.on
                        iconName: modelData.icon
                        tip: sunMap && bar.plan.sun ? bar.plan.sun.texts.tip : modelData.tip
                        menu: sunMap ? bar.sunPanel : bar.backgroundMenu
                        commandOpensMenu: !sunMap
                        onClicked: {
                            bar.plan.forceActiveFocus()
                            if (sunMap) bar.plan.sun.toggle()
                        }
                    }
                }
                Component {
                    id: plainControl
                    M.Button {
                        objectName: "planView-" + modelData.command
                        flat: true; compact: true
                        width: M.ControlMetrics.viewPlainWidth; height: M.ControlMetrics.viewButton
                        padding: 0; iconName: modelData.icon; tip: modelData.tip
                        checked: modelData.command === "snaps" ? backend.snapsEnabled
                            : modelData.command === "ortho" ? backend.orthoEnabled
                            : modelData.command === "view_" + bar.viewMode
                        onClicked: { bar.plan.forceActiveFocus(); backend.viewAction(modelData.command) }
                    }
                }
            }
        }
    }
}
