import QtQuick
import QtQuick.Layouts
import Meridiana.Controls as M

GuideCard {
    id: root
    required property var service
    animateText: true
    title: service.tourStep.title
    progress: service.tourStep.progress
    description: service.tourStep.text
    points: service.tourStep.points
    hint: service.tourStep.hint ? service.labels.tryHint + " " + service.tourStep.hint : ""
    previousText: service.labels.previous
    nextText: service.tourInvitation ? service.labels.startTour
              : service.tourStep.number === service.tourStep.total ? service.labels.start : service.labels.next
    laterText: service.tourInvitation ? service.labels.later : ""
    canPrevious: service.tourIndex > 0 && !service.tourInvitation
    onPrevious: service.previous()
    onNext: service.next()
    onLater: service.pauseTour()
    // R612: at every step (opened, Next, Previous, a step chosen, taken up again after the pause) the keyboard on Next;
    // a turn later, once the step's words and buttons are there
    Connections { target: root.service; function onTourChanged() { Qt.callLater(root.focusNext) } }
    Component.onCompleted: Qt.callLater(root.focusNext)
    headingExtra: RowLayout {
        M.Button {
            text: root.progress; flat: true; enabled: !root.service.tourInvitation
            tip: root.service.labels.steps
            onClicked: steps.open()
            M.Menu {
                id: steps
                Repeater {
                    model: root.service.tourSteps
                    M.MenuItem {
                        required property var modelData
                        text: modelData.title; checkable: true; checked: root.service.tourIndex === modelData.index
                        onTriggered: root.service.goToStep(modelData.index)
                    }
                }
            }
        }
        Item { Layout.fillWidth: true }
        M.Button { text: root.service.labels.pause; flat: true; visible: !root.service.tourInvitation
                   onClicked: root.service.pauseTour() }
    }
}
