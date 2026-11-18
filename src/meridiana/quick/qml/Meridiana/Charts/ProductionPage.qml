import QtQuick

ResultsPage {
    pageData: results.production
    onActionRequested: action => results.requestAction(action)
    onHelpRequested: topic => results.help(topic)
}
