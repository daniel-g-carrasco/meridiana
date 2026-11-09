import QtQuick
import QtQuick.Templates as T
import Meridiana.Theme
T.ScrollBar {
    id: root
    implicitWidth: orientation === Qt.Vertical ? Theme.size.SCROLLBAR : Theme.size.CONTROL
    implicitHeight: orientation === Qt.Horizontal ? Theme.size.SCROLLBAR : Theme.size.CONTROL
    padding: Theme.space.XXS
    topPadding: orientation === Qt.Vertical ? Theme.radius.CARD : Theme.space.XXS
    bottomPadding: topPadding
    leftPadding: orientation === Qt.Horizontal ? Theme.radius.CARD : Theme.space.XXS
    rightPadding: leftPadding
    minimumSize: Math.min(1, Theme.size.CONTROL / Math.max(1, orientation === Qt.Vertical ? availableHeight : availableWidth))
    visible: size < 1
    // R520: what the content leaves at its right for the bar's lane while the bar is shown: a list, a table, a page
    // that scrolls ends its rows, its columns and its texts that far from its right side (ControlMetrics.scrollLane and
    // scrollGap), and the bar never covers them
    readonly property real room: visible && orientation === Qt.Vertical ? ControlMetrics.scrollLane + ControlMetrics.scrollGap : 0
    hoverEnabled: true
    policy: T.ScrollBar.AsNeeded
    // ui/fades.py on every area that scrolls: the bar brings them, the ground found under the list. False where the
    // list has its own (List, Tree, Table, ScrollPage) or is a popup's.
    property bool fades: true
    readonly property Item fadesOf: {
        if (!fades || orientation !== Qt.Vertical || !parent) return null
        if (parent.contentY !== undefined) return parent
        return parent.contentItem && parent.contentItem.contentY !== undefined ? parent.contentItem : null
    }
    property Item _fades: null
    // R489: the ground is the first opaque one under the list, a control's background before its parents' colour: the
    // conversation of Meridio is a ScrollView with its own white background inside a card of another colour, and its
    // veils were the card's colour, a tinted band over the white.
    function _ground() {
        const revision = Theme.revision
        for (let up = root.fadesOf ? root.fadesOf.parent : null; up; up = up.parent) {
            const own = up.background !== undefined && up.background !== null ? up.background.color : undefined
            if (own !== undefined && own.a > .99) return own
            if (up.color !== undefined && up.color.a > .99) return up.color
        }
        return Theme.colors.panel
    }
    function _attach() {
        if (_fades) { _fades.destroy(); _fades = null }
        if (fadesOf) _fades = fadeMaker.createObject(fadesOf, {flickable: fadesOf, barRoom: parent === fadesOf ? Theme.size.SCROLLBAR : 0})
    }
    onFadesOfChanged: _attach()
    // R530: the list the bar scrolls (its parent, unless the bar was moved out of it: then the list says it), with the
    // rebound at its ends (Rebound.qml)
    property Item flickable: orientation === Qt.Vertical && parent ? (parent.contentY !== undefined ? parent
        : parent.contentItem && parent.contentItem.contentY !== undefined ? parent.contentItem : null) : null
    property QtObject _rebound: null
    function _bounce() {
        if (_rebound) { _rebound.destroy(); _rebound = null }
        if (flickable && flickable.contentItem && flickable.boundsMovement !== undefined)
            _rebound = reboundMaker.createObject(flickable, {flickable: flickable})
    }
    onFlickableChanged: _bounce()
    Component { id: reboundMaker; Rebound { } }
    Component.onCompleted: { _attach(); _bounce() }
    Component { id: fadeMaker; EdgeFades { ground: root._ground(); page: root.fadesOf !== null && root.fadesOf.model === undefined } }
    contentItem: Rectangle {
        implicitWidth: Theme.size.THUMB; implicitHeight: Theme.size.THUMB
        radius: Theme.size.THUMB/2
        color: root.pressed ? Theme.colors.text2 : root.hovered ? Theme.colors.muted : Theme.colors.line
    }
}
