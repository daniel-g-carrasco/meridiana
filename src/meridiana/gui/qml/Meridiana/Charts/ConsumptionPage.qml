import QtQuick

ResultsPage {
    pageData: results.consumption
    onActionRequested: action => results.requestAction(action)
}
