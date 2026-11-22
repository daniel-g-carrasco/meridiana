"""The actual right panel with a real session, independent of workbench loading."""
import _setup
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from shiboken6 import delete
from meridiana.app import jobs
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.plant import create_page
from meridiana.gui.backend.controls import install_controls
from quick.gestures import pump, wait_for

QML = b'''import QtQuick
import Meridiana.Theme
import Meridiana.Controls as M
import Meridiana.Plant as P
Rectangle {
    width: 620; height: 1100; color: Theme.colors.panel
    QtObject { id: commands; property string stringsView: "cards"
        property var commandWords: ({}); property string selectedSubfield: "" }
    M.ScrollPage { objectName: "panel-scroll"; anchors.fill: parent
        P.PlantInverters { width: parent.width; backend: plantBackend; actions: commands }
    }
}'''


class PanelFixture:
    def __init__(self, project, theme='light', qml_path=None):
        self.app = _setup.qt_or_skip()
        self.session = ProjectSession(project)
        self.session.results, self.session.layout_keys, _ = jobs.layout_of(project)
        self.engine = QQmlEngine()
        install_controls(self.engine, {'theme': theme})
        self.backend = create_page(self.engine, self.session)
        if qml_path is not None:
            self.engine.addImportPath(str(Path(qml_path)))
        self.component = QQmlComponent(self.engine)
        self.component.setData(QML, QUrl())
        self.root = self.component.create()
        assert self.root is not None, [e.toString() for e in self.component.errors()]
        self.window = QQuickWindow()
        self.window.resize(620, 1100)
        self.root.setParentItem(self.window.contentItem())
        self.window.show()
        self.settle()

    def settle(self):
        wait_for(lambda: not self.backend.busy and self.backend.units, 60)
        pump(250)

    def close(self):
        self.backend.close()
        self.window.close()
        self.root.setParentItem(None)
        delete(self.root)
        delete(self.window)
        delete(self.engine)
