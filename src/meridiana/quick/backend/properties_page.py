"""Independent page host, importable by the shared meridiana.quick.page launcher.

Until the shell registers these pages: python -m meridiana.quick.backend.properties_page properties
No user configuration is loaded or written, and the sample is never saved.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import QLocale, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from meridiana import i18n, model
from meridiana.quick.backend.controls import install_controls
from meridiana.session import ProjectSession


PAGES = {'properties': ('Properties', 'PropertiesPage'), 'checks': ('Checks', 'ChecksPage'),
         'project_tree': ('ProjectTree', 'ProjectTreePage'), 'pedigree': ('Properties', 'PedigreePage')}
ALIASES = {'proprieta': 'properties', 'verifiche': 'checks', 'progetto': 'project_tree', 'project': 'project_tree'}


def page_backend(name, session):
    if name == 'properties':
        from .properties import PropertiesBackend
        return PropertiesBackend(session)
    if name == 'checks':
        from .checks import ChecksBackend
        return ChecksBackend(session)
    if name == 'project_tree':
        from .project_tree import ProjectTreeBackend
        return ProjectTreeBackend(session)
    if name == 'pedigree':
        from .properties_pedigree import PedigreeBackend
        return PedigreeBackend()
    raise ValueError(name)


def build_page(name='properties', session=None, *, options=None, width=1366, height=900, frameless=False):
    """Return engine/window/backend/theme. The caller retains all four until closed."""
    name = ALIASES.get(name, name)
    module, component = PAGES[name]
    session = session if session is not None else ProjectSession()
    backend = page_backend(name, session)
    engine = QQmlApplicationEngine()
    theme = install_controls(engine, options)
    engine.rootContext().setContextProperty('pageBackend', backend)
    engine.rootContext().setContextProperty('pageWidth', width)
    engine.rootContext().setContextProperty('pageHeight', height)
    engine.rootContext().setContextProperty('pageFrameless', frameless)
    engine._page_backend = backend
    source = f'''import QtQuick
import QtQuick.Window
import Meridiana.Theme
import Meridiana.{module}
Window {{
    width: pageWidth; height: pageHeight; visible: true
    flags: pageFrameless ? Qt.FramelessWindowHint | Qt.Window : Qt.Window
    color: Theme.colors.panel
    {component} {{ objectName: "standalonePage"; anchors.fill: parent; backend: pageBackend }}
}}'''
    engine.loadData(source.encode('utf-8'))
    if not engine.rootObjects():
        if hasattr(backend, 'close'):
            backend.close()
        raise RuntimeError(f'Could not load {module}.{component}')
    return engine, engine.rootObjects()[0], backend, theme


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name', choices=sorted(set(PAGES) | set(ALIASES)), nargs='?', default='properties')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--selection', default='site:')
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--large-text', action='store_true')
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--shot', type=Path)
    args = parser.parse_args(argv)
    app = QGuiApplication.instance() or QGuiApplication(['meridiana-properties'])
    i18n.setup('it')
    QLocale.setDefault(QLocale('it_IT'))
    project = model.Project.load(args.project)[0] if args.project else model.Project()
    session = ProjectSession(project)
    kind, _, oid = args.selection.partition(':')
    session.select(kind, oid)
    engine, window, backend, theme = build_page(args.name, session, options=dict(
        theme=args.theme, textSize='large' if args.large_text else 'medium'), width=args.width,
        height=args.height, frameless=bool(args.shot))
    if args.shot:
        def capture():
            args.shot.parent.mkdir(parents=True, exist_ok=True)
            if not window.grabWindow().save(str(args.shot)):
                raise OSError(args.shot)
            print(f'{args.shot}: {window.rendererInterface().graphicsApi()}, DPR={window.devicePixelRatio()}')
            app.quit()
        QTimer.singleShot(1000, capture)
    result = app.exec()
    window.close()
    if hasattr(backend, 'close'):
        backend.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
