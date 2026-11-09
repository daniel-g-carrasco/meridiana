import QtQuick
import "CameraMath.js" as Cam

Item {
    id: overlay
    required property var viewport
    readonly property var cam: viewport.cameraState
    function project(p) { return Cam.project(cam,p,width,height) }
}
