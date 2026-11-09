"""Standalone page host. The application shell can reuse build_page's providers.

Run ``python -m meridiana.quick.backend.files_page file``. All data belongs to a
private temporary folder unless --folder is explicitly supplied. The production
shell supplies its existing session, configuration and paths to the backends.
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from meridiana import config, i18n, model
from meridiana.paths import Paths
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.files import FilesBackend
from meridiana.session import ProjectSession


class PageHost:
    """Own providers until their QML consumers are destroyed; no global config writes."""
    def __init__(self, name, folder=None, options=None, width=1366, height=900, project=None):
        self.temp = tempfile.TemporaryDirectory(prefix='meridiana-page-') if folder is None else None
        root = Path(self.temp.name) if self.temp else Path(folder)
        root.mkdir(parents=True, exist_ok=True)
        self.paths = Paths(*(root / part for part in ('config', 'state', 'data', 'cache')))
        fresh = not self.paths.config_file.exists()
        self.cfg = config.load(self.paths.config_file)
        if fresh:
            self.cfg.theme, self.cfg.accent, self.cfg.backgrounds, self.cfg.font = 'light', 'indigo', 'grey', 'plex'
            self.cfg.background = 'none'
            self.cfg.network_geocoding = self.cfg.network_pvgis = self.cfg.network_tiles = False
        theme_options = dict(theme=self.cfg.theme, accent=self.cfg.accent, backgrounds=self.cfg.backgrounds,
                             font=self.cfg.font, textSize=self.cfg.text_size,
                             reducedMotion=bool(self.cfg.extra.get('reduced_motion', False)))
        theme_options.update(options or {})
        self.session = ProjectSession(project or model.Project())
        self.engine = QQmlApplicationEngine()
        self.warnings = []
        self.engine.warnings.connect(lambda messages: self.warnings.extend(m.toString() for m in messages))
        self.theme = install_controls(self.engine, theme_options)
        from meridiana.registry import Registry
        self.paths.data.mkdir(parents=True, exist_ok=True)
        self.registry = Registry(self.paths.data / 'registry.sqlite3')
        self.files = FilesBackend(self.session, self.cfg, self.paths, registry=self.registry)
        self.settings = self.dialogs = self.report = None
        if name == 'settings' or name.startswith('settings:'):
            from meridiana.quick.backend.settings import SettingsBackend
            self.settings = SettingsBackend(self.cfg, self.paths.config_file, self.theme)
            self.settings.setDataDirectory(self.paths.data)
            self.files.selectSection('preferences:' + (name.partition(':')[2] or 'appearance'))
        if name in ('dialogs', 'new', 'registry', 'site', 'canopy', 'canopy-layout', 'ifc', 'pvsyst', 'shortcuts', 'template', 'update'):
            self._dialogs()
            self.dialogs.open('new' if name == 'dialogs' else name)
        if name == 'report':
            from meridiana.quick.backend.report import ReportBackend
            self.report = ReportBackend(self.session, self.cfg, self.paths)
        self.files.commandRequested.connect(self.dispatch)
        self.files.sectionChanged.connect(self._section)
        context = self.engine.rootContext()
        context.setContextProperty('filesPageBackend', self.files)
        context.setContextProperty('settingsPageBackend', self.settings)
        context.setContextProperty('dialogsPageBackend', self.dialogs)
        context.setContextProperty('reportPageBackend', self.report)
        context.setContextProperty('pageName', name)
        context.setContextProperty('pageWidth', width)
        context.setContextProperty('pageHeight', height)
        self.engine.load(QUrl.fromLocalFile(str(Path(__file__).parents[1] / 'qml/Meridiana/File/PageHost.qml')))
        if not self.engine.rootObjects():
            self.close()
            raise RuntimeError('\n'.join(self.warnings))
        self.window = self.engine.rootObjects()[0]

    def _dialogs(self):
        if self.dialogs is None:
            from meridiana.quick.backend.dialogs import DialogsBackend
            self.dialogs = DialogsBackend(self.session, self.cfg, self.paths)
            self.dialogs.set_registry(self.registry)
            self.dialogs.created.connect(self.files.createProject)
            self.dialogs.projectReady.connect(self.files.replaceProject)
            self.dialogs.commandRequested.connect(self.dispatch)
        return self.dialogs

    def _section(self):
        section = self.files.section
        if section.startswith('preferences') and self.settings is None:
            from meridiana.quick.backend.settings import SettingsBackend
            self.settings = SettingsBackend(self.cfg, self.paths.config_file, self.theme)
            self.settings.setDataDirectory(self.paths.data)
            self.engine.rootContext().setContextProperty('settingsPageBackend', self.settings)
        elif section in ('new', 'registry'):
            self._dialogs()
            self.engine.rootContext().setContextProperty('dialogsPageBackend', self.dialogs)

    def dispatch(self, command):
        """Standalone routing; the production shell connects these same command IDs."""
        if command in ('import_pvsyst', 'import_ifc', 'shortcuts', 'about', 'update', 'template'):
            dialog = self._dialogs()
            dialog.open({'import_pvsyst': 'pvsyst', 'import_ifc': 'ifc'}.get(command, command))
            self.engine.rootContext().setContextProperty('dialogsPageBackend', dialog)
            self.engine.rootContext().setContextProperty('pageName', 'dialogs')     # PageHost.activePage binds it (R23 F6)
        elif command == 'export_report':
            if self.report is None:
                from meridiana.quick.backend.report import ReportBackend
                self.report = ReportBackend(self.session, self.cfg, self.paths)
                self.engine.rootContext().setContextProperty('reportPageBackend', self.report)
            self.engine.rootContext().setContextProperty('pageName', 'report')
        elif command == 'quit':
            self.window.close()
        else:
            self.files._fail(i18n._('This command is provided by the application window: {command}').format(command=command))

    def close(self):
        from shiboken6 import delete
        if getattr(self, 'window', None):
            self.window.close()
        for provider in (self.report, self.dialogs, self.settings, self.files):
            if provider is not None and hasattr(provider, 'close'):
                provider.close()
        if self.engine:
            delete(self.engine)
            self.engine = None
        self.registry.close()
        if self.temp:
            self.temp.cleanup()


def build_page(name='file', *, folder=None, options=None, width=1366, height=900, project=None):
    i18n.setup('it')
    return PageHost(name, folder, options, width, height, project)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', nargs='?', default='file')
    parser.add_argument('--folder', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--shot', type=Path)
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--large-text', action='store_true')
    args = parser.parse_args(argv)
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication.instance() or QGuiApplication(['meridiana-page'])
    project = model.Project.load(args.project)[0] if args.project else None
    host = build_page(args.page, folder=args.folder, options=dict(theme=args.theme,
                      textSize='large' if args.large_text else 'medium'), width=args.width, height=args.height,
                      project=project)
    if args.shot:
        def capture():
            args.shot.parent.mkdir(parents=True, exist_ok=True)
            image = host.window.grabWindow()
            if image.isNull() or not image.save(str(args.shot)):
                print(f'Capture failed: {args.shot}')
                app.exit(1)
                return
            print(f'{args.shot}: {host.window.rendererInterface().graphicsApi()}, DPR={image.devicePixelRatio()}')
            if host.warnings:
                print('\n'.join(host.warnings))
            app.exit(1 if host.warnings else 0)
        QTimer.singleShot(1000, capture)
    result = app.exec()
    host.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
