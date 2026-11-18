"""Plan commands, preferences and status in the shared workbench."""
from PySide6.QtCore import QTimer

from .parts import Part


def install(engine, session, cache, window):
    controller = window.plan

    # R23 F6 (docs/studio/39-contratto-backend-qml.md): the plan's status comes from Workbench.qml (shell.planStatus),
    # its view mode is bound there (PlanHost.viewMode); the window's state is asked with the shell's request signals
    def bind(root):
        def phase():
            controller.setPhase(root.property('phase'))
            status()

        def status():
            visible = root.property('phase') in ('model', 'plant') and not root.property('fileOpen')
            text = window.shell.planStatus if visible else ''
            if window.shell._notice != text:
                window.shell._notice = text
                window.shell.changed.emit()

        def command(name):
            if name == 'propose_free':
                actions = window.parts.controllers.get('plantActions')
                if actions is not None:
                    actions.sizingFree()
            elif name in ('view_plan', 'view_3d', 'view_both'):
                window.shell.viewModeRequested.emit(name[5:])
            elif name == 'properties':
                window.shell.panelRequested.emit('properties')
            # R538: the plan's Fit, + and - act on the plan alone (they zoomed the 3D view as well)

        controller.viewCommand.connect(command)
        controller.notice.connect(lambda text: window.shell.show_notice(text, 6000))    # R487
        window.shell.planStatusChanged.connect(status)
        root.phaseChanged.connect(phase)
        root.fileOpenChanged.connect(status)
        phase()
        # The shell installs fallback zoom handlers after Parts.bind. Keep the
        # plan's centre anchor and fitted flag when those commands reach it.
        def view_command(name):
            # R538: a shortcut acts on the view that has the focus, the plan or the 3D view, never on both
            scene = window.parts.controllers.get('sceneControls')
            if scene is not None and scene.viewFocused:          # the 3D view shown with the keyboard (View3DHost)
                scene.fit() if name == 'fit' else scene.zoom(1 if name == 'zoom_in' else -1)
            else:
                controller.viewAction(name)

        def register_view_commands():
            for name in ('fit', 'zoom_in', 'zoom_out'):
                window.shell.register_command(name, lambda n=name: view_command(n))
        QTimer.singleShot(0, register_view_commands)

        def open_preferences(section):
            window.shell.fileOpenRequested.emit(True)
            files = window.parts.controllers.get('files') or window.parts.controllers.get('file')
            if files is not None and hasattr(files, 'selectSection'):
                files.selectSection('preferences:' + section)
        controller.preferencesRequested.connect(open_preferences)

        settings = window.parts.controllers.get('settings')
        if settings is not None:
            def setting(key, value):
                if key in ('background', 'veil', 'map_sources'):
                    controller.configureMaps({{'background': 'source', 'map_sources': 'sources'}.get(key, key): value})
                elif key == 'network_tiles':
                    controller.configureMaps({'offline': not value or session.project.reserved})
            settings.changed.connect(setting)
            for key in ('background', 'veil', 'map_sources', 'network_tiles'):
                setting(key, getattr(settings.cfg, key))
            controller.mapPreferencesChanged.connect(lambda options: [settings.setValue(
                {'source': 'background', 'sources': 'map_sources'}.get(k, k), v) for k, v in options.items()
                if k in ('source', 'sources', 'veil')])

    commands = {name: lambda n=name: controller.viewAction(n)
                for name in ('snaps', 'ortho', 'strings', 'view_align', 'fit', 'zoom_in', 'zoom_out')}
    commands['view_north'] = lambda: controller.viewCommand.emit('north')
    commands['rectangle'] = lambda: controller.setRectangle(not controller.drawing.rectangle)
    return Part('plan-interaction', commands=commands, bind=bind)
