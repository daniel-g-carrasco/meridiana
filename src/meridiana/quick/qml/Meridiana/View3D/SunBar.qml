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
    readonly property real barHeight: Math.max(28, Theme.measureText("00:00").height + 10) + 6
    implicitHeight: barHeight
    color: surfaceColor
    function commitHour() { backend.setSun(sun.year, sun.month, sun.day, hour.value / 6) }
    onVisibleChanged: if (!visible) playing = false
    onPlayingChanged: backend.playSun(playing)
    Timer { interval: 80; running: root.playing && root.visible && root.enabled; repeat: true; onTriggered: root.backend.stepSun() }
    Timer { id: sunRest; interval: 80; onTriggered: root.commitHour() }
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8; anchors.rightMargin: 8; anchors.topMargin: 3; anchors.bottomMargin: 3
        spacing: Theme.space.M
        ViewButton {
            objectName: "sunPlay"; iconName: root.playing ? "pause" : "play"; checkable: true; checked: root.playing
            implicitWidth: M.ControlMetrics.viewButton
            tip: qsTr("Play the day: the sun from dawn to sunset, ten minutes a step")
            onClicked: root.playing = checked
        }
        M.Button {
            id: day
            objectName: "sunDay"
            Layout.preferredWidth: Math.round(Math.max(...Array.from({length:12}, (_,m) => Theme.measureText("28 " + Qt.locale().monthName(m, Locale.ShortFormat)).width))) + 42
            Layout.preferredHeight: 28
            tip: qsTr("The day of the year")
            text: new Date(root.sun.year,root.sun.month-1,root.sun.day).toLocaleDateString(Qt.locale(), "d MMM")
            contentItem: Item {
                M.Label { text: day.text; anchors.verticalCenter: parent.verticalCenter }
                M.Icon { name: "field:down"; width: 10; height: 6; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter }
            }
            onClicked: { calendar.month = root.sun.month-1; calendar.year=root.sun.year; calendar.open() }
            Keys.onUpPressed: root.backend.shiftSunDay(1)
            Keys.onDownPressed: root.backend.shiftSunDay(-1)
        }
        Basic.Slider {
            id: hour; objectName: "sunHour"
            Layout.fillWidth: true; Layout.minimumWidth: Math.min(80, Math.max(0, root.width-16-day.Layout.preferredWidth-Theme.space.S)); Layout.preferredHeight: 22
            from: 0; to: 143; stepSize: 1; value: root.sun.hour * 6; snapMode: T.Slider.SnapAlways
            padding: 0
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
            M.ToolTip { parent: hour; text: qsTr("The hour on the site's clock"); visible: hour.hovered }
        }
        M.Label { objectName: "sunClock"; visible: root.width-16-day.Layout.preferredWidth-80-27-3*Theme.space.S >= Layout.preferredWidth; Layout.preferredWidth: Theme.measureText("00:00").width+4; text: root.sun.clock }
        M.Label {
            id: shortText; objectName: "sunPosition"
            Layout.preferredWidth: Math.min(Math.max(0,root.width-16-54-day.Layout.preferredWidth-Theme.measureText("00:00").width-4-80-40),
                Math.max(Theme.measureText(qsTr("h 88,8° · az -188,8°")).width,Theme.measureText(qsTr("sole sotto l'orizzonte")).width)+4)
            Layout.minimumWidth: 0; Layout.fillWidth: false; elide: Text.ElideRight
            text: root.sun.short
            MouseArea { id: shortHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
            M.ToolTip { parent: shortText; pressed: shortHover.pressed; text: root.sun.description; visible: shortHover.containsMouse }
        }
        ViewButton {
            objectName: "sunDesign"; iconName: "sun"
            visible: root.width-16-day.Layout.preferredWidth-80-2*Theme.space.S >= M.ControlMetrics.viewButton
            implicitWidth: M.ControlMetrics.viewButton
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
                ViewButton { iconName: "chevron-left"; tip: qsTr("Mese precedente"); onClicked: calendar.turn(-1) }
                Item { Layout.fillWidth: true }
                M.Button { text: Qt.locale().standaloneMonthName(calendar.month); flat: true; Layout.preferredWidth: 87
                    font.weight: Font.Normal
                    menu: months }
                M.Button { text: calendar.year; flat: true; visible: !yearEdit.visible; Layout.preferredWidth: 88
                    font.weight: Font.Normal
                    onClicked: { yearEdit.visible=true; yearEdit.forceActiveFocus(); yearEdit.selectAll() } }
                M.TextField { id: yearEdit; visible: false; text: calendar.year; Layout.preferredWidth: 88
                    validator: IntValidator { bottom: 1900; top: 2100 }
                    onEditingFinished: { if (acceptableInput) calendar.year=Number(text); visible=false } }
                Item { Layout.fillWidth: true }
                ViewButton { iconName: "chevron-right"; tip: qsTr("Mese successivo"); onClicked: calendar.turn(1) }
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
