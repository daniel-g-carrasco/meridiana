"""Mount the 3D component on an existing Quick session, or open the isolated verification window."""
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlApplicationEngine

from .scene import SceneBackend
from .scene_jobs import SceneLayouts
from .controls import install_controls
from .tokens import install_theme

QML_ROOT = Path(__file__).resolve().parents[1] / 'qml'


def install(engine, session, cache):
    """Called before loading the shell: the view receives sceneBackend and shares its session."""
    engine.addImportPath(str(QML_ROOT))
    install_controls(engine)
    backend = SceneBackend(session, cache)
    engine.rootContext().setContextProperty('sceneBackend', backend)
    engine.rootContext().setContextProperty('sceneBackendObject', backend)
    return backend


class SceneWindow:
    """A real QQuickWindow for deterministic D3D11 input and pixel tests, no Widgets embedding."""
    def __init__(self, session, cache, width=1366, height=900, dark=False):
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        self.backend = install(self.engine, session, cache)
        self.layouts = SceneLayouts(session, self.backend)
        self.layouts.error.connect(self.backend._say)
        self.layouts.begin()
        self.theme = install_theme(self.engine, {'theme': 'dark' if dark else 'light'})
        self.component = QQmlComponent(self.engine)
        source = '''import QtQuick
import QtQuick.Window
import Meridiana.View3D
Window {
    visible: false
    title: "Meridiana: vista 3D Quick"
    property Item view: viewport
    Viewport { id: viewport; anchors.fill: parent; sceneBackend: sceneBackendObject }
}'''
        # A different context name avoids the component property's name shadowing it.
        self.engine.rootContext().setContextProperty('sceneBackendObject', self.backend)
        self.component.setData(source.encode(), QUrl.fromLocalFile(str(QML_ROOT / 'SceneHost.qml')))
        self.window = self.component.create()
        if self.window is None:
            raise RuntimeError('\n'.join(e.toString() for e in self.component.errors()))
        self.window.resize(width, height)
        self.view = self.window.property('view')        # the view of the window this host made (studio 39, 2.4)

    def close(self):
        self.layouts.close()
        self.window.close()
        self.backend.close()
        self.window.deleteLater()
        self.engine.deleteLater()


def main():
    """Standalone native viewport, useful while the application shell is integrated."""
    import argparse
    import tempfile
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    from PySide6.QtQuickControls2 import QQuickStyle
    from meridiana import i18n, model
    from meridiana.session import ProjectSession
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication([])
    i18n.setup('it')
    project, notice = model.Project.load(args.project)
    with tempfile.TemporaryDirectory(prefix='meridiana-scene-') as cache:
        host = SceneWindow(ProjectSession(project), cache, dark=args.dark)
        if notice:
            host.backend._say(notice)
        host.window.show()
        result = app.exec()
        host.close()
        from PySide6.QtCore import QCoreApplication, QEvent
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
