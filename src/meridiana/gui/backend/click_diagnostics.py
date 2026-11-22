"""Observe clicks taken by overlays in drawing views, without intercepting their gestures."""
from PySide6.QtCore import QEvent, QObject, Qt

from meridiana.app.platform import log


class ClickDiagnostics(QObject):
    def __init__(self, window, tool):
        super().__init__(window)
        self.window, self.tool = window, tool
        self.start = None
        window.installEventFilter(self)

    def eventFilter(self, watched, event):
        kind = event.type()
        if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self.start = event.position()
        elif kind == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            start, self.start = self.start, None
            # A drag is navigation or editing, not a point rejected by a tool.
            if start is None or (start - event.position()).manhattanLength() > 6:
                return False
            tool = self.tool()
            if not tool or tool == "select":
                return False
            owner = self.window.mouseGrabberItem()
            if owner is None or owner.objectName() in {"planMouse", "sceneInput"}:
                return False
            # Use only the static Qt type, never an object name containing a project ID.
            receiver = owner.metaObject().className().split("_QML")[0]
            parent = owner
            while parent is not None:
                if parent.objectName() in {"plan", "viewport3d"}:
                    view = "plan" if parent.objectName() == "plan" else "3d"
                    log.note(f"tool-click rejected tool={tool} view={view} reason=other-item receiver={receiver}")
                    return False
                parent = parent.parentItem()
            # Floating siblings (for example the assistant) can also cover a view: the views the window names
            # (Workbench.planItem, sceneItem), not looked for in its tree (rule 7 of the reordering)
            for name, view in (("planItem", "plan"), ("sceneItem", "3d")):
                item = self.window.property(name)
                if item is not None and item.isVisible() and item.contains(item.mapFromScene(event.position())):
                    log.note(f"tool-click rejected tool={tool} view={view} reason=other-item receiver={receiver}")
                    break
        return False
