import QtQuick
import Meridiana.Properties

PropertiesPage {
    objectName: "properties-page"
    backend: propertiesBackend
    function requestHelp() { backend.help(backend.kind === "prop" ? "phase.model" : backend.kind) }
}
