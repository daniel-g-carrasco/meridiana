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
    nextText: service.tourStep.number === service.tourStep.total ? service.labels.start : service.labels.next
    laterText: ""
    canPrevious: service.tourIndex > 0
    onPrevious: service.previous()
    onNext: service.next()
    onLater: service.pauseTour()
    headingExtra: RowLayout {
        M.Button {
            text: root.progress; flat: true
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
        M.Button { text: root.service.labels.pause; flat: true; onClicked: root.service.pauseTour() }
    }
}
