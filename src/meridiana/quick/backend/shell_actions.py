"""Window-level actions that join the installed pages and the shared session."""
from PySide6.QtCore import QObject, QTimer

from meridiana import phases
from meridiana.i18n import _


class ShellActions(QObject):
    def __init__(self, host):
        super().__init__(host.engine)
        self.host = host
        self.root = host.window
        self.shell = host.shell
        self.plan = host.plan
        # R461: a phase that shows the year gives its computation all the power
        if hasattr(self.shell.bridge, 'yearWanted'):
            self.root.phaseChanged.connect(self.year_phase)
        if self.plan is not None:
            if 'plan-interaction' not in host.parts.installed:
                self.root.phaseChanged.connect(self.phase_changed)
            self.shell.objectRequested.connect(self.place_object)
            self.shell.objectWanted.connect(self.place_object)
            self.shell.escapeRequested.connect(lambda: self.plan.key('Escape'))
            for cid, handler in {
                'delete': lambda: self.plan.key('Delete'),
                'square': lambda: self.plan._run(lambda: self.plan.editor.apply_command({'type': 'square'})),
                'object_3d': self.root.openObjects,
                'view_north': self.root.northUp,
                'layout_east_west': lambda: self.activate('layout_east_west'),
            }.items():
                self.shell.register_command(cid, handler)
            if 'plan-interaction' not in host.parts.installed:
                for cid, handler in {'snaps': lambda: self.toggle_aid('F3'), 'ortho': lambda: self.toggle_aid('F8'),
                                     'rectangle': self.rectangle, 'view_align': lambda: self.plan.pickAnyEdge('align')}.items():
                    self.shell.register_command(cid, handler)
            self.phase_changed()
        controllers = host.parts.controllers
        if 'dialogs' in controllers:
            controllers['dialogs'].shortcutsChanged.connect(self.shell.set_bindings)
        if 'filePart' in controllers:
            files = controllers['filePart']
            self.shell.register_menu_action('find_site', lambda: files.openDialog('site'))
            for kind in ('modules', 'inverters', 'microinverters', 'optimizers', 'batteries'):
                self.shell.register_menu_action('browse_' + kind, lambda k=kind: self.catalog(k))
            for kind in ('module', 'inverter'):
                self.shell.register_menu_action('product_' + kind, lambda k=kind: self.catalog(k+'s', importing=True))
            for action in ('rename', 'delete'):
                self.shell.register_menu_action('variant_' + action, lambda a=action: host.tasks.variantAction(a))
        if 'sceneControls' in controllers:
            # Meridio's home once the window is exposed: Assistant/AssistantHost.qml (settleHome), R23 F6
            self.shell.register_command('fit', self.fit)
            for command in ('zoom_in', 'zoom_out'):
                self.shell.register_command(command, lambda cmd=command: self.root.runCommand(cmd))
        for command in ('fill', 'empty', 'refill'):
            self.shell.register_command(command, lambda cmd=command: self.layout(cmd))
        self.shell.register_command('consumption_base', self.consumption)
        if 'consumptionEditor' in controllers:
            self.shell.register_command('import_curve', self.import_curve)
        self.shell.register_command('whats_this', self.root.pickHelp)
        if 'assistant_help' in controllers:
            self.shell.helpRequested.connect(controllers['assistant_help'].request)
        checks = controllers.get('checks')
        if checks is not None:
            self.shell.checks_provider = checks
            checks.changed.connect(self.shell.changed)
            self.shell.register_command('copy_notes', checks.copyNotes)
            self.shell.register_command('fix_check', lambda: checks.requestFix(checks.currentIndex))
            self.shell.register_command('focus_checks', self.focus_checks)
            self.shell.checkLevelRequested.connect(self.show_level)
        settings = controllers.get('settings')
        if settings is not None:
            settings.changed.connect(self.setting_changed)
            self.shell.register_command('menu_bar', lambda: settings.setValue('menu_bar', not host.cfg.menu_bar))
            self.shell.register_command('toolbar_text', lambda: settings.setValue('toolbar', 'text' if host.cfg.toolbar == 'icons' else 'icons'))
            for key in ('toolbar', 'toolbar_place', 'shortcuts', 'menu_bar'):
                self.setting_changed(key, getattr(host.cfg, key))

    def focus_checks(self):
        self.root.runCommand('focus_checks')
        self.shell.focusRequested.emit('checks-list')
        checks = self.host.parts.controllers['checks']
        if checks.currentIndex < 0:
            checks.takeFirst()

    def show_level(self, level):
        self.focus_checks()
        self.host.parts.controllers['checks'].goTo(level)

    def fit(self):
        self.root.property('planItem').fit()
        self.host.parts.controllers['sceneControls'].fit()

    def catalog(self, kind, importing=False):
        files = self.host.parts.controllers['filePart']
        command = {'modules': 'module', 'inverters': 'inverter', 'batteries': 'battery'}.get(kind, kind)
        files.dispatch('catalog_' + command)
        if importing:
            files.catalog.requestImport()

    def layout(self, command):
        session = self.host.bridge.session
        kind, oid = session.selection
        if kind == 'row':
            oid = oid.partition('/')[0]
        if kind not in ('row', 'subfield') or not any(s.id == oid for s in session.project.subfields):
            self.host.tasks.tell(_('Select a sub-field first: the modules are laid in it.'))
            return
        session.select('subfield', oid)
        provider = self.host.parts.controllers.get('properties')
        if provider:
            provider.trigger('relayout' if command == 'refill' else command)

    def consumption(self):
        self.root.showPhase('consumption')
        self.root.runCommand('focus_properties')
        editor = self.host.parts.controllers.get('consumptionEditor')
        if editor is not None:
            self.shell.focusRequested.emit('consumption-mode-' + editor.mode)

    def import_curve(self):
        self.consumption()
        QTimer.singleShot(0, self, self.host.parts.controllers['consumptionEditor'].openImport)

    def phase_changed(self):
        self.plan.setPhase(self.root.property('phase'))

    def year_phase(self):
        if self.root.property('phase') in ('production', 'consumption', 'economics', 'report'):
            self.shell.bridge.yearWanted()

    def activate(self, command, options=None):
        phase = self.root.property('phase')
        home = phases.home(command, phase)
        if home != phase:
            self.root.showPhase(home)
        self.plan.activateTool('east_west' if command == 'layout_east_west' else command.removeprefix('tool_'), options or {})

    def place_object(self, kind, options=None):
        """R375: the three ways of the picker, one tool each: «Choose and place» (prop, a copy at every click while
        `repeat`), «Along a line» (prop_series: a copy every `step` between two clicks; a fence, a hedge or a walkway
        is one object along the line, prop_line), «Small family» (prop_group: a few with light differences)."""
        from meridiana import props
        options = dict(options or {})
        mode = options.pop('mode', 'place')
        self.root.showPhase('model')
        if kind in props.PATH_KINDS:
            tool = 'prop_line'
        elif mode == 'line':
            tool = 'prop_series'
        elif mode == 'group':
            tool = 'prop_group'
        else:
            tool = 'prop'
        self.plan.activateTool(tool, {'kind': kind, **options})

    def rectangle(self):
        self.plan.drawing.set_rectangle(not self.plan.drawing.rectangle)
        self.plan._overlays()
        self.plan.stateChanged.emit()

    def toggle_aid(self, key):
        self.plan.drawing.key(key)
        self.plan._overlays()
        self.plan.stateChanged.emit()

    def setting_changed(self, key, value):
        if key == 'toolbar':
            self.shell.toolbarModeRequested.emit({'icons': 'icons', 'beside': 'beside'}.get(value, 'auto'))
        elif key == 'toolbar_place':
            self.shell.toolbarPositionRequested.emit(value)
        elif key == 'shortcuts':
            self.shell.set_bindings(value)
        elif key == 'menu_bar':
            self.shell.menuBarRequested.emit(bool(value), bool(value))
