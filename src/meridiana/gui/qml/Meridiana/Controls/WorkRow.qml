import QtQuick
import QtQuick.Layouts
import Meridiana.Theme

// R598 (study 48, chapter 4): the one row of a heavy job, the same in the status bar (Shell/WorkBar.qml), in its list
// and in a page or a dialog that shows its own job (`M.WorkRow { row: work.slots.ifc_read }`). The row comes worded
// from gui/backend/work.py: what the job is (title), the phase in hand (phase, "" when none), the bar (running
// without an end when the job has no total), the percentage, the time left once it is known, Cancel. Without a row
// (the job not there) it is hidden.
//
// R607 (Daniel 14/11/2026, «durante il caricamento gli elementi sono sballati»; among the sketches «il filo grigio (A)
// ma con le parole sopra e la barra sotto (tipo in C)»): the words above, the thread (M.ProgressBar) under them, as wide
// as the row. At the left what the job is doing: the title, then the phase, which takes the room left and is cut with
// the dots (whole in its tooltip); at the right, small, the percentage and the time left, each as wide as its widest
// words («100 %», work.texts.leftWidest) so that nothing moves while they change; the texts on one baseline. `inline`
// is the status bar's form, one line high (sketch C, first column): title, phase in a column of its own
// (ControlMetrics.workPhase), the thread taking the room left, percentage and time, Cancel. Inside a window whose own
// «Cancel» stops the job (M.Dialog's body, stopsJobs) the row draws no Cancel: one command stops a job.
ColumnLayout {
    id: line
    property var row: ({})
    // `named` gives the status bar's first row the names the tests and the guides look for
    property bool named: false
    // the status bar's form: one line, the thread between the words
    property bool inline: false
    readonly property var job: row || ({})
    // the jobs' bridge (`work`, backend/work.py) is in every window; the gallery has none and words Cancel itself
    readonly property bool jobs: typeof work !== "undefined" && work !== null
    property string cancelText: jobs ? work.texts.cancel : ""
    // the widest time left, in the words of the bridge (the gallery and the tests give their own)
    property string leftWidest: jobs ? work.texts.leftWidest || "" : ""
    // false inside a window that stops the job with its own «Cancel» (found by itself, see Component.onCompleted)
    property bool ownCancel: true
    Component.onCompleted: {
        for (let up = parent; up; up = up.parent) {
            if (up.stopsJobs === undefined) continue
            const body = up
            ownCancel = Qt.binding(() => !body.stopsJobs)
            return
        }
    }
    // the job that has shown a phase: in the status bar its column stays for the rest of the job
    property var phasedJob: undefined
    onJobChanged: if (job.phase) phasedJob = job.id
    readonly property bool phased: !!job.phase || (job.id !== undefined && phasedJob === job.id)
    // the widest the percentage can be: its number at a hundred, in the row's own words
    readonly property string widestPercent: (job.percent || "").replace(/\d+/, "100")
    readonly property string barName: named ? "statusProgressBar" : "workBar"
    // a column as wide as its widest words (TextMetrics: a measure that follows the font once it is in place; a
    // FontMetrics call was read once, before, and gave a pixel more until the text changed): the font's measure and the text's own differ by a fraction at some scales,
    // so the measure is rounded up with a hair to spare; only words wider still (more than 99 minutes) widen it
    function column(own, widest) {
        const room = Math.ceil(widest) + Theme.line.HAIR
        return own > room ? Math.ceil(own) : room
    }
    visible: job.id !== undefined
    spacing: ControlMetrics.progressGap
    RowLayout {
        objectName: "workWords"
        Layout.fillWidth: true
        spacing: Theme.space.S
        CopyLabel { objectName: line.named ? "statusProgressText" : "workText"; text: line.job.title || ""
            textStyle: "secondary"; Layout.alignment: Qt.AlignBaseline }
        CopyLabel { id: phase; objectName: line.named ? "statusProgressPhase" : "workPhase"; text: line.job.phase || ""
            visible: line.inline ? line.phased : true; textStyle: "caption"; elide: Text.ElideRight
            Layout.fillWidth: true; Layout.minimumWidth: 0
            Layout.preferredWidth: line.inline ? ControlMetrics.workPhase : implicitWidth
            Layout.maximumWidth: line.inline ? ControlMetrics.workPhase : Number.POSITIVE_INFINITY
            Layout.alignment: Qt.AlignBaseline
            HoverHandler { id: phaseHover }
            ToolTip { visible: phaseHover.hovered && phase.truncated; text: phase.text } }
        ProgressBar { objectName: line.inline ? line.barName : ""; visible: line.inline
            Layout.fillWidth: true; Layout.minimumWidth: Theme.size.PROGRESS; Layout.preferredWidth: Theme.size.PROGRESS
            Layout.alignment: Qt.AlignVCenter
            indeterminate: !line.job.determinate; value: line.job.fraction || 0 }
        CopyLabel { id: percent; objectName: line.named ? "statusProgressPercent" : "workPercent"; visible: !!line.job.determinate
            text: line.job.percent || ""; textStyle: "caption"; horizontalAlignment: Text.AlignRight
            readonly property real column: line.column(implicitWidth, widest.advanceWidth)
            Layout.preferredWidth: column; Layout.minimumWidth: column; Layout.maximumWidth: column
            Layout.alignment: Qt.AlignBaseline
            TextMetrics { id: widest; font: percent.font; text: line.widestPercent } }
        CopyLabel { id: leftText; objectName: line.named ? "statusProgressLeft" : "workLeft"
            // kept for a job with a total (the only one that gets a time left): the estimate that comes moves nothing;
            // at the left of its column, next to the percentage
            visible: text !== "" || !!line.job.determinate
            text: line.job.left ? "· " + line.job.left : ""; textStyle: "caption"; horizontalAlignment: Text.AlignLeft
            readonly property real column: line.column(implicitWidth, line.leftWidest ? leftMetrics.advanceWidth : 0)
            Layout.preferredWidth: column; Layout.minimumWidth: column; Layout.maximumWidth: column
            Layout.alignment: Qt.AlignBaseline
            TextMetrics { id: leftMetrics; font: leftText.font; text: "· " + line.leftWidest } }
        Button { objectName: line.named ? "statusProgressCancel" : "workCancel"; flat: true
            text: line.cancelText
            visible: line.ownCancel && !!line.job.cancellable && text !== ""; padding: Theme.space.S; Layout.alignment: Qt.AlignVCenter
            onClicked: if (line.jobs) work.cancel(line.job.id) }
    }
    // the thread under the words, as wide as the row
    ProgressBar { objectName: line.inline ? "" : line.barName; visible: !line.inline; Layout.fillWidth: true
        indeterminate: !line.job.determinate; value: line.job.fraction || 0 }
}
