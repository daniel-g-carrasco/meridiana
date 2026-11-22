import QtQuick

ResultsPage {
    pageData: results.economics
    onActionRequested: action => results.requestAction(action)
}
