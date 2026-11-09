import QtQuick
import Meridiana.Controls as M

M.Menu {
    id: imageMenu
    required property var backend
    required property var imageData
    title: imageData.name
    M.MenuItem {
        text: backend.texts.show; checkable: true; checked: imageData.visible
        onTriggered: backend.action(imageData.id,"show",checked ? 1 : 0)
    }
    M.Menu {
        id: transparency; title: backend.texts.transparency
        Instantiator {
            model: [0,.2,.4,.6,.8]
            delegate: M.MenuItem {
                required property real modelData
                text: Math.round(modelData*100)+" %"; checkable: true
                checked: Math.abs(1-imageMenu.imageData.opacity-modelData)<.01
                onTriggered: backend.action(imageData.id,"opacity",1-modelData)
            }
            onObjectAdded: function(index, object) { transparency.insertItem(index,object) }
            onObjectRemoved: function(index, object) { transparency.removeItem(object) }
        }
    }
    M.MenuItem { text: backend.texts.scale; onTriggered: backend.action(imageData.id,"scale",0) }
    M.MenuItem { text: backend.texts.move; onTriggered: backend.action(imageData.id,"move",0) }
    M.MenuItem { text: backend.texts.rotate; onTriggered: backend.action(imageData.id,"rotate",0) }
    M.MenuItem { text: backend.texts.remove; onTriggered: backend.action(imageData.id,"remove",0) }
}
