import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M

// The small panel of the sun map (study 45, package 5), attached to its button in the plan's bar: what to show (the
// loss, the kWh/m², the hours of sun), what to colour (decision 2: automatic, the roofs, the modules) and the day of the
// hours of sun. Each choice is the backend's (SunMap): changing what is shown computes nothing again.
M.Popup {
    id: panel
    property var sun: null
    readonly property var texts: sun ? sun.texts : ({})
    function indexOf(list, value) { for (let i = 0; i < (list || []).length; i++) if (list[i].value === value) return i; return 0 }
    contentItem: Column {
        objectName: "sunMapPanel"
        spacing: Theme.space.S
        padding: Theme.space.S
        M.CopyLabel { text: panel.texts.title || ""; textStyle: "strong" }
        M.CopyLabel { text: panel.texts.quantity || ""; textStyle: "secondary" }
        M.Segments {
            id: quantities; objectName: "sunMapQuantity"
            model: panel.texts.quantities || []
            currentIndex: panel.sun ? panel.indexOf(panel.texts.quantities, panel.sun.quantity) : 0
            onActivated: index => panel.sun.setQuantity(panel.texts.quantities[index].value)
        }
        M.CopyLabel { text: panel.texts.colour || ""; textStyle: "secondary" }
        M.Segments {
            objectName: "sunMapColour"
            model: panel.texts.colours || []
            currentIndex: panel.sun ? panel.indexOf(panel.texts.colours, panel.sun.colour) : 0
            onActivated: index => panel.sun.setColour(panel.texts.colours[index].value)
        }
        M.CopyLabel { text: panel.texts.day || ""; textStyle: "secondary" }
        M.ComboBox {
            objectName: "sunMapDay"
            width: quantities.implicitWidth   // as wide as the widest choice above it (a Column takes its width from its children)
            enabled: !!panel.sun && panel.sun.quantity === "hours"
            options: panel.texts.days || []
            value: panel.sun ? panel.sun.day : ""
            onChosen: day => panel.sun.setDay(day)
        }
    }
}
