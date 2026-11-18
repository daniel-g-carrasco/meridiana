import QtQuick

ResultsPage {
    pageData: results.storage
    onActionRequested: action => results.requestAction(action)
}
