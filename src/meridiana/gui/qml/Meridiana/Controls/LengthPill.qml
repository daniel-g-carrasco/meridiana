import QtQuick
import QtQuick.Controls as C
import Meridiana.Theme
import "PillPlace.js" as Place

// The pill of a length written on a view (R472, R555 points 12 and 14, study 46): the sides' measures of the plan
// (Plan/SidePills.qml), the measuring tool's spans and totals (Measure/MeasureLayer.qml), the measures of the dialogs'
// previews (Dialogs/GeometryPreview.qml) and the strings' names and numbers (Plan/StringLabels.qml) are this one
// drawing. The ground of what the plan writes over itself (an M.Pill "view"), round ends, the small type; a disc at the
// start (`badge`, the side's number in it; `badgeShown` with `badgeFill` and `badgeLine`, a string's colour), a line
// below (`below`, smaller), «≈» before the number when it is about (`approx`), room for a sign at the end (`end`, its
// width: the host puts the sign at `endX`, as far from the end as the disc from the start). `ground` and `ink` are the
// view's (the plan's label_bg and label_fg); the host places it (x, y), its size is its own unless the host gives one
// (the sides' layout does). It gives way in one manner only: `whole` false, the disc alone (a side too short for it, a
// string at a zoom too far for its name). The clicks go through to the view, as every "view" pill.
Pill {
    id: root
    TextActions { id: measureCopy; target: root; readOnly: true; wholeText: root.shown + (root.below ? "\n" + root.below : "") }
    C.ContextMenu.menu: TextMenu { actions: measureCopy }
    variant: "view"
    property real direction: 0
    rotation: Place.readable(direction)
    property string value: ""
    property string below: ""
    property bool approx: false
    property string badge: ""
    property bool badgeShown: badge !== ""
    property color badgeFill: ink
    property color badgeLine: "transparent"
    property real badgeWidth: line - 2*Theme.space.XXS
    property string badgeName: ""
    property real end: 0
    property bool whole: true                   // the value shown; false, the disc alone (a side too short for it)
    readonly property string shown: approx && value.indexOf("≈") !== 0 ? "≈" + value : value
    readonly property real line: Place.height(metrics.height, 0, Theme.annotation.LABEL_PAD)
    readonly property real textX: badgeShown ? Theme.space.XXS + badgeWidth + Theme.space.XS : Theme.space.S
    readonly property real endX: width - Theme.space.XXS - end
    implicitHeight: Place.height(metrics.height, below !== "" ? metrics.height : 0, Theme.annotation.LABEL_PAD)
    // from its texts as laid out (no second measuring of the same text)
    implicitWidth: whole ? Place.width(valueText.implicitWidth, below !== "" ? belowText.implicitWidth : 0,
                                       badgeShown ? badgeWidth : 0, Theme.space.XXS, Theme.space.XS, Theme.space.S, end)
                         : badgeWidth + 2*Theme.space.XXS
    radius: line/2
    FontMetrics { id: metrics; font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE }
    Rectangle {
        objectName: root.badgeName
        visible: root.badgeShown
        x: Theme.space.XXS; y: Theme.space.XXS
        width: root.badgeWidth; height: root.line-2*Theme.space.XXS; radius: height/2
        color: root.badgeFill
        border.color: root.badgeLine; border.width: root.badgeLine.a > 0 ? Theme.line.HAIR : 0
        Text { anchors.fill: parent; text: root.badge
            visible: root.badge !== ""
            color: root.ground
            verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter
            font.family: Theme.fontFamily; font.pixelSize: Theme.annotation.LABEL_SIZE; font.weight: Theme.annotation.WEIGHT }
    }
    Text {
        id: valueText
        objectName: "lengthPillValue"
        x: root.textX; height: root.line
        visible: root.whole; text: root.shown; color: root.ink; textFormat: Text.PlainText
        verticalAlignment: Text.AlignVCenter; font: metrics.font
    }
    Text {
        id: belowText
        objectName: "lengthPillBelow"
        x: root.textX; y: root.line - Theme.space.XXS
        visible: root.whole && root.below !== ""; text: root.below; color: root.ink; textFormat: Text.PlainText
        font: metrics.font
    }
}
