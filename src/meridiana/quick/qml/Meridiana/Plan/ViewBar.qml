import QtQuick
import QtQuick.Shapes
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
                spacing: 1
                Item {
                    visible: index>0 && backend.viewTools[index-1].group!==modelData.group
                    width: visible ? 1 : 0; height: 19+2*Theme.space.XS
                    Rectangle { width: 1; height: 16; anchors.centerIn: parent; color: Theme.colors.line }
                }
                Rectangle {
                    objectName: "planView-"+modelData.command
                    width: 19+2*Theme.space.S+(modelData.command==="background" ? Theme.space.XL+2-Theme.space.S : 0)
                    height: 19+2*Theme.space.XS
                    radius: Theme.radius.INNER
                    property bool checked: modelData.command==="snaps" ? backend.snapsEnabled :
                        modelData.command==="ortho" ? backend.orthoEnabled : modelData.command==="view_"+bar.viewMode
                    readonly property bool menuShown: modelData.command==="background" && !!bar.backgroundMenu && bar.backgroundMenu.visible
                    property bool menuAtPress: false
                    color: click.pressed || checked || menuShown ? Theme.colors.press : click.containsMouse ? Theme.colors.hover : "transparent"
                    M.Icon { x: Theme.space.S+1; anchors.verticalCenter: parent.verticalCenter; width: 16; height: 16; name: modelData.icon; color: Theme.colors.text }
                    Shape { visible: modelData.command==="background"; anchors.right: parent.right; anchors.rightMargin: Theme.space.XS
                        anchors.verticalCenter: parent.verticalCenter; width: 8; height: 8
                        preferredRendererType: Shape.CurveRenderer
                        ShapePath { fillColor: "transparent"; strokeColor: Theme.colors.text; strokeWidth: .7
                            PathSvg { path: "M1,3 L4,6 L7,3" } }
                    }
                    MouseArea {
                        id: click; anchors.fill: parent; hoverEnabled: true
                        onPressed: parent.menuAtPress = modelData.command==="background" && !!bar.backgroundMenu &&
                                   (bar.backgroundMenu.visible || Date.now() - bar.backgroundMenu.closedAt < 400)
                        onClicked: {
                            plan.forceActiveFocus()
                            if (modelData.command==="background") { if (parent.menuAtPress) bar.backgroundMenu.close(); else bar.backgroundRequested() }
                            else backend.viewAction(modelData.command)
                        }
                    }
                    M.ToolTip { visible: click.containsMouse && !parent.menuShown; pressed: click.pressed; text: modelData.tip }
                }
            }
        }
    }
}
