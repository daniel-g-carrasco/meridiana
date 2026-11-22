"""Window-level actions that join the installed pages and the shared session."""
from PySide6.QtCore import QObject, QTimer

from meridiana.app.interface import layout_commands, phases
from meridiana.core.layout import manual
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
                'measure_distance': lambda: self.measure('distance'),
                'measure_height': lambda: self.measure('height'),
                'measure_clear': self.plan.measure.removeAll,     # the tool in hand stays; none made: nothing
                # R564: the area of the automatic layout, in Layout's menu as in the roof's (layout_commands.AREA)
                'fill_area': lambda: self.activate('tool_' + layout_commands.AREA[0], dict(layout_commands.AREA[1])),
            }.items():
                self.shell.register_command(cid, handler)
            if 'plan-interaction' not in host.parts.installed:
                for cid, handler in {'snaps': lambda: self.toggle_aid('F3'), 'ortho': lambda: self.plan.viewAction('ortho'),
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
        checks = controllers.get('checks')
        if checks is not None:
            self.shell.checks_provider = checks
            checks.changed.connect(self.shell.checksCounted)
            self.shell.register_command('copy_notes', checks.copyNotes)
            self.shell.register_command('fix_check', lambda: checks.requestFix(checks.currentIndex))
            self.shell.register_command('focus_checks', self.focus_checks)
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
        sf = session.subfield(oid) if kind in ('row', 'subfield') else None
        if sf is None:
            self.host.tasks.tell(_('Select a sub-field first: the modules are laid in it.'))
            return
        session.select('subfield', oid)
        if command == 'refill':
            provider = self.host.parts.controllers.get('properties')
            if provider:
                provider.trigger('relayout')        # after its question
            return
        # R564: on a sub-field already full «Fill» did nothing and said nothing (it went through the panel, which had
        # no such button for it); now it acts by itself, with the change and the name of the menus, or says why not
        if command == 'fill':
            can, _note, why = layout_commands.fill_state(sf)
            if not can:
                self.host.tasks.tell(why)
                return
        elif not sf.filled:
            self.host.tasks.tell(_('«{name}» is already empty.').format(name=sf.name or sf.id))
            return
        session.edit(layout_commands.text(command), manual.fill(session.project, oid, command == 'fill'))

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
        self.plan.activateTool(command.removeprefix('tool_'), options or {})

    def measure(self, mode):
        """The menu of Measure (study 46): the tool in hand, then the mode chosen (it stays until another is chosen).
        Its 15° guides are the plan's Ortho (the view bar's button, F8), not an entry of this menu."""
        self.activate('tool_measure')
        self.plan.measure.setMode(mode)

    def place_object(self, kind, options=None):
        """R375: the three ways of the picker, one tool each: «Choose and place» (prop, a copy at every click while
        `repeat`), «Along a line» (prop_series: a copy every `step` between two clicks; a fence, a hedge or a walkway
        is one object along the line, prop_line), «Small family» (prop_group: a few with light differences)."""
        from meridiana.core.geometry import props
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
