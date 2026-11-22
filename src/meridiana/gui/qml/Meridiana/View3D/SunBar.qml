import QtQuick
import QtQuick.Controls as T
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

Rectangle {
    id: root
    objectName: "sunBar"
    required property var backend
    property var sun: backend.sunData
    property bool playing: false
    property color surfaceColor: Theme.colors.window
    // R555 (Daniel 13/11/2026: «in una vista stretta il testo dell'altezza del sole va sotto il pulsante col sole»):
    // one rule for the whole row. Every control is `row` tall with the same air above and below; the sides keep
    // `side`. What does not fit gives way in one order: the sun's text gets shorter (elided, the whole sentence in
    // its tooltip), then goes, then the clock goes (the slider's tooltip then says both), then the slider gets
    // shorter than its least; the play button, the day and the sun's button stay.
    readonly property real row: Math.max(Theme.size.CONTROL, Math.ceil(Theme.measureText("00:00").height) + 2 * Theme.space.XS)
    readonly property real air: Theme.space.XS
    // Daniel 14/11/2026 (R555, 6: «non avesse bordo basso così alto e fosse uguale al suo bordo alto verso la vista 3d»):
    // what lies under the bar in its own ground (the frame's room under the 3D, View3DHost) is room below it too, so
    // the same goes above it: the controls stand as far from the 3D drawing as from the frame's edge
    property real roomBelow: 0
    readonly property real airAbove: air + roomBelow
    readonly property real side: Theme.space.M
    readonly property real gap: Theme.space.M
    readonly property real square: M.ControlMetrics.viewButton
    // the slider's least: three of the bar's squares, room for the handle to travel
    readonly property real sliderLeast: 3 * square
    readonly property real clockWidth: Math.ceil(Theme.measureText("00:00").width) + Theme.space.XS
    // the widest the sun's text can be, so that playing the day does not move the bar
    readonly property real textFull: Math.ceil(Math.max(Theme.measureText(qsTr("h 88,8° · az -188,8°")).width,
                                                        Theme.measureText(qsTr("sun below the horizon")).width)) + Theme.space.XS
    // below this the text says too little to be worth its room: the height alone and the ellipsis
    readonly property real textLeast: Math.ceil(Theme.measureText("h 88,8°…").width)
    // what is left once the play button, the day, the slider at its least, the sun's button and their gaps are in
    readonly property real spare: width - 2 * side - (2 * square + dayWidth + sliderLeast + 3 * gap)
    readonly property bool clockShown: spare >= gap + clockWidth
    readonly property real textRoom: spare - (clockShown ? gap + clockWidth : 0) - gap
    readonly property bool textShown: clockShown && textRoom >= textLeast
    readonly property real textWidth: textShown ? Math.floor(Math.min(textFull, textRoom)) : 0
    // the day keeps the width of its longest month (the day button's own line)
    readonly property real dayWidth: day.Layout.preferredWidth
    implicitHeight: row + airAbove + air
    color: surfaceColor
    // R688 (Daniel 16/11/2026): the slider in minutes, so a drag is fine and smooth; the wheel moves ten minutes a
    // notch, as the play button steps
    // The wheel writes the slider's value from here, which cuts its binding to the sun: once the hour is told, the
    // binding comes back, or Play, another day or another project would no longer move the knob (Daniel 17/11/2026)
    function commitHour() {
        backend.setSun(sun.year, sun.month, sun.day, hour.value / 60)
        hour.value = Qt.binding(function() { return Math.round(root.sun.hour * 60) })
    }
    // Daniel 17/11/2026: ten minutes, not one («al minuto è troppo granulare»). A touchpad sends fractions of a
    // notch: they add up until they make ten minutes
    property real wheelCarry: 0
    function wheelHour(event) {
        wheelCarry += (event.angleDelta.y !== 0 ? event.angleDelta.y : event.angleDelta.x) / 120 * 10
        var steps = wheelCarry > 0 ? Math.floor(wheelCarry / 10) : Math.ceil(wheelCarry / 10)
        if (steps === 0) return
        wheelCarry -= steps * 10
        hour.value = Math.max(hour.from, Math.min(hour.to, Math.round(hour.value / 10) * 10 + steps * 10))
        if (!sunRest.running) sunRest.start()
    }
    onVisibleChanged: if (!visible) playing = false
    onPlayingChanged: backend.playSun(playing)
    Timer { interval: 80; running: root.playing && root.visible && root.enabled; repeat: true; onTriggered: root.backend.stepSun() }
    Timer { id: sunRest; interval: 80; onTriggered: root.commitHour() }
    RowLayout {
        id: line
        objectName: "sunRow"
        anchors.fill: parent
        anchors.leftMargin: root.side; anchors.rightMargin: root.side; anchors.topMargin: root.airAbove; anchors.bottomMargin: root.air
        spacing: root.gap
        ViewButton {
            objectName: "sunPlay"; iconName: root.playing ? "pause" : "play"; checkable: true; checked: root.playing
            Layout.preferredWidth: root.square; Layout.minimumWidth: root.square; Layout.preferredHeight: root.row
            tip: qsTr("Play the day: the sun from dawn to sunset, ten minutes a step")
            onClicked: root.playing = checked
        }
        M.Button {
            id: day
            objectName: "sunDay"
            Layout.preferredWidth: Math.round(Math.max(...Array.from({length:12}, (_,m) => Theme.measureText("28 " + Qt.locale().monthName(m, Locale.ShortFormat)).width))) + 42
            Layout.minimumWidth: Layout.preferredWidth
            Layout.preferredHeight: root.row
            tip: qsTr("The day of the year")
            text: new Date(root.sun.year,root.sun.month-1,root.sun.day).toLocaleDateString(Qt.locale(), "d MMM")
            contentItem: Item {
                M.Label { text: day.text; anchors.verticalCenter: parent.verticalCenter }
                M.Arrow { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; active: day.hovered }
            }
            onClicked: { calendar.month = root.sun.month-1; calendar.year=root.sun.year; calendar.open() }
            Keys.onUpPressed: root.backend.shiftSunDay(1)
            Keys.onDownPressed: root.backend.shiftSunDay(-1)
        }
        Basic.Slider {
            id: hour; objectName: "sunHour"
            // the only one that still gets shorter once the text and the clock have gone
            Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: root.sliderLeast; Layout.preferredHeight: root.row
            // the drag runs smooth and rests on the nearest ten minutes when the knob is let go
            from: 0; to: 1430; stepSize: 10; value: Math.round(root.sun.hour * 60); snapMode: T.Slider.SnapOnRelease
            padding: 0
            wheelEnabled: false
            WheelHandler { objectName: "sunHourWheel"; onWheel: function(event) { root.wheelHour(event) } }
            onMoved: { if (!pressed) root.commitHour(); else if (!sunRest.running) sunRest.start() }
            onPressedChanged: if (!pressed) { sunRest.stop(); root.commitHour() }
            background: Rectangle {
                x: hour.leftPadding; y: (hour.height-height)/2; width: hour.availableWidth; height: 4; radius: 2
                color: Theme.colors.line
                Rectangle { width: hour.visualPosition * parent.width; height: 4; radius: 2; color: Theme.colors.muted }
            }
            handle: Rectangle {
                x: hour.visualPosition * (hour.width-width); y: (hour.height-height)/2
                width: 16; height: 16; radius: 8; color: Theme.colors.card
                border.color: hour.hovered ? Theme.colors.text2 : Theme.colors.field_line
            }
            hoverEnabled: true
            // with the sun's text gone, the slider says it whole (the hour, the clock and where the sun is)
            M.ToolTip { parent: hour; text: root.textShown ? qsTr("The hour on the site's clock") : root.sun.description; visible: hour.hovered }
        }
        M.CopyLabel { objectName: "sunClock"; visible: root.clockShown
            Layout.preferredWidth: root.clockWidth; Layout.minimumWidth: root.clockWidth; Layout.fillHeight: true
            verticalAlignment: Text.AlignVCenter; text: root.sun.clock }
        M.CopyLabel {
            id: shortText; objectName: "sunPosition"
            visible: root.textShown
            Layout.preferredWidth: root.textWidth; Layout.minimumWidth: root.textWidth; Layout.maximumWidth: root.textWidth
            Layout.fillHeight: true; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
            text: root.sun.short
            copyText: root.sun.description || text
            textActions.description: root.sun.description || ""
            MouseArea { id: shortHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
            M.ToolTip { parent: shortText; pressed: shortHover.pressed; text: root.sun.description; visible: shortHover.containsMouse }
        }
        ViewButton {
            objectName: "sunDesign"; iconName: "sun"
            Layout.preferredWidth: root.square; Layout.minimumWidth: root.square; Layout.preferredHeight: root.row
            tip: qsTr("Back to the day and the solar noon the row pitch is computed with")
            onClicked: root.backend.designSun()
        }
    }
    // R21-F2: the calendar is the common popup, hung over the day's button (`above`), the frame and the opening of the menus
    M.Popup {
        id: calendar
        objectName: "sunCalendar"
        focus: true
        parent: day
        above: true
        property int month: 11
        property int year: 2026
        width: 7 * (Math.round(Math.max(...Array.from({length:7},(_,d)=>Theme.measureText(Qt.locale().dayName(d,Locale.ShortFormat)).width)))+16) + 8
        height: 224; padding: 4
        function turn(delta) { let d = new Date(year,month+delta,1); month=d.getMonth();year=d.getFullYear() }
        contentItem: ColumnLayout {
            spacing: Theme.space.XXS
            RowLayout {
                Layout.topMargin: 2
                spacing: 0
                ViewButton { iconName: "chevron-left"; tip: qsTr("Previous month"); onClicked: calendar.turn(-1) }
                Item { Layout.fillWidth: true }
                M.Button { text: Qt.locale().standaloneMonthName(calendar.month); flat: true; Layout.preferredWidth: 87
                    font.weight: Font.Normal
                    menu: months }
                M.Button { text: calendar.year; flat: true; visible: !yearEdit.visible; Layout.preferredWidth: 88
                    font.weight: Font.Normal
                    onClicked: { yearEdit.visible=true; yearEdit.forceActiveFocus(); yearEdit.selectAll() } }
                M.TextField { id: yearEdit; visible: false; text: calendar.year; Layout.preferredWidth: 88
                    validator: IntValidator { bottom: 1900; top: 2100 }
                    onCommitRequested: { if (acceptableInput) calendar.year=Number(text); visible=false } }
                Item { Layout.fillWidth: true }
                ViewButton { iconName: "chevron-right"; tip: qsTr("Next month"); onClicked: calendar.turn(1) }
            }
            T.DayOfWeekRow { locale: Qt.locale(); Layout.fillWidth: true
                delegate: M.Label { required property string shortName; text: shortName; horizontalAlignment: Text.AlignHCenter; color: Theme.colors.muted } }
            T.MonthGrid {
                id: grid; month: calendar.month; year: calendar.year; locale: Qt.locale()
                spacing: 0; padding: 0
                Layout.fillWidth: true; Layout.fillHeight: true
                Layout.bottomMargin: 6
                delegate: Item {
                    required property var model
                    Rectangle { anchors.fill: parent; anchors.margins: 2; radius: Theme.radius.INNER
                        color: model.day===root.sun.day && model.month===root.sun.month-1 && model.year===root.sun.year ? Theme.colors.line : "transparent"
                        border.width: model.today ? 1 : 0; border.color: Theme.colors.line }
                    HoverHandler { id: cellHover }
                    Rectangle { anchors.fill: parent; anchors.margins: 2; radius: Theme.radius.INNER
                        visible: cellHover.hovered; color: Theme.colors.hover }
                    M.Label { anchors.centerIn: parent; text: model.day; color: model.month===calendar.month ? Theme.colors.text : Theme.colors.muted }
                }
                onClicked: date => { root.backend.setSun(date.getFullYear(),date.getMonth()+1,date.getDate(),root.sun.hour); calendar.close() }
            }
        }
        M.Menu { id: months
            Repeater { model: 12
                M.MenuItem { required property int index; text: Qt.locale().standaloneMonthName(index)
                    onTriggered: calendar.month=index }
            }
        }
    }
}
