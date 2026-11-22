import QtQuick
import QtQuick.Layouts
import Meridiana.Theme
import Meridiana.Controls as M

// R598 (study 48, chapter 4): the one bar of the jobs in the status bar, where the year's progress was (ui/waiting.py
// Progress). Past Theme.motion.PATIENCE only: the first job's row (M.WorkRow: what the job is, its phase, its bar,
// the percentage, the time left once it is known, Cancel). With more jobs: the first, and a pill with the number of
// the others that opens their list, each the same row. The rows come worded from backend/work.py. In the footer's
// row it takes no more than its words and gives way before the counts and the buttons: the first row's phase is cut.
RowLayout {
    id: bar
    objectName: "statusProgress"
    spacing: Theme.space.S
    Layout.fillWidth: true
    Layout.maximumWidth: implicitWidth
    readonly property var rows: work.rows
    readonly property bool busy: rows.length > 0
    property bool waited: false
    visible: busy && waited
    onBusyChanged: { waited = false; if (busy) wait.restart(); else wait.stop() }
    onRowsChanged: if (rows.length < 2) others.close()
    Timer { id: wait; interval: Theme.motion.PATIENCE; onTriggered: bar.waited = true }

    M.WorkRow { row: bar.rows.length ? bar.rows[0] : ({}); named: true; inline: true; Layout.fillWidth: true
        Layout.alignment: Qt.AlignVCenter }
    M.Pill {
        id: more
        objectName: "statusProgressMore"
        variant: "count"; level: "info"; checkable: false
        visible: bar.rows.length > 1
        text: String(Math.max(0, bar.rows.length - 1)); tip: work.texts.others
        Layout.alignment: Qt.AlignVCenter
        onClicked: others.opened ? others.close() : others.open()
        M.Popup {
            id: others
            objectName: "statusProgressList"
            above: true
            // sized from its list: M.Popup does not follow its contentItem's implicit size (it stayed 8 x 8, unseen)
            width: list.implicitWidth + leftPadding + rightPadding
            height: list.implicitHeight + topPadding + bottomPadding
            // the list is laid out once shown: placed again with its size, above the pill
            onWidthChanged: if (visible) place()
            onHeightChanged: if (visible) place()
            contentItem: Column {
                id: list
                spacing: Theme.space.XS
                Repeater {
                    model: bar.rows.slice(1)
                    M.WorkRow { required property var modelData; row: modelData; inline: true }
                }
            }
        }
    }
}
