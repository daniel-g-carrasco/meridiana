"""Plant commands and dialogs installed on the real workbench's session."""
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QTimer

from meridiana import shortcuts
from meridiana.energy import plant as core, system
from .parts import Part, QML
from .plant import PlantBackend
from .plant_summary import PlantSummary, module_words
from .catalog import CatalogBackend
from .properties import PropertiesBackend
from .plant_i18n import _


class PlantActions(QObject):
    changed = Signal()
    helpRequested = Signal(str)

    def __init__(self, plant, catalog, host, parent=None):
        super().__init__(parent)
        self.plant, self.catalog, self.host = plant, catalog, host
        self._section, self._dialog, self._purpose, self._entry = 'panels', '', '', -1
        self._battery, self._replace = {}, True
        self._storage_revision = 0
        self._proposal_scope = 0
        self._only_free = False         # R522: the sizing on the modules in no string only
        self._import_record, self._import_text = {}, ''
        self._strings_view = 'cards'
        self._review_listener = None
        catalog.chosen.connect(self.chosen)
        catalog.importRequested.connect(self.importRequested)
        plant.catalogRequested.connect(self.openCatalog)
        plant.drawRequested.connect(self.draw)
        plant.showStringRequested.connect(self.select)
        plant.wiringChanged.connect(self._wired)
        self._plan = host.plan
        if self._plan is not None:
            self._plan.overlayChanged.connect(self.follow_selection)
        self._selection = None
        plant.session.subscribe(self._changed)

    section = Property(str, lambda self: self._section, notify=changed)
    dialog = Property(str, lambda self: self._dialog, notify=changed)
    battery = Property('QVariantMap', lambda self: self._battery, notify=changed)
    replace = Property(bool, lambda self: self._replace, notify=changed)
    storageRevision = Property(int, lambda self: self._storage_revision, notify=changed)
    importKind = Property(str, lambda self: self._purpose, notify=changed)
    importText = Property(str, lambda self: self._import_text, notify=changed)
    proposalScope = Property(int, lambda self: self._proposal_scope, notify=changed)
    onlyFree = Property(bool, lambda self: self._only_free, notify=changed)
    stringsView = Property(str, lambda self: self._strings_view, notify=changed)

    @Slot(str)
    def setStringsView(self, view):
        if view not in ('cards', 'diagram', 'table') or view == self._strings_view:
            return
        from meridiana import config
        self._strings_view = view
        if getattr(self.host, 'cfg', None) is not None:
            self.host.cfg.strings_view = view
            config.save(self.host.cfg, self.host.paths.config_file)
        self.changed.emit()

    @Property(str, notify=changed)
    def storageSummary(self):
        e = self.plant.session.project.economics
        battery = e.get('battery') or {}
        name = f"{battery.get('manufacturer', '')} {battery.get('model', '')}".strip()
        if not name:
            return _('No battery')
        units = int(e.get('battery_units') or 1)
        coupling = {'ac': _('AC: independent storage converter'), 'dc': _('DC: hybrid inverter')}.get(
            e.get('storage_coupling') or '', '')
        text = f'{units} × {name}' if units > 1 else name
        return f'{text}\n{coupling}' if coupling else text

    @Slot(str)
    def help(self, key):
        self.helpRequested.emit(key)

    @Slot(str, result=str)
    def helpTip(self, key):
        """The tooltip of a «?»: the short sentence of its help (ui/help_box.HelpButton)."""
        from meridiana import help as helps
        found = helps.get(key)
        return found.short if found is not None else ''

    @Property('QVariantMap', constant=True)
    def commandWords(self):
        """The words and tooltip of a window's command on a panel's button, as the actions of the Widgets give them."""
        shell = self.host.shell
        words = {}
        for cid in ('inverter_catalog', 'inverter_auto', 'strings_auto', 'strings_manual', 'strings_clear', 'battery_catalog'):
            command = shell._commands.get(cid)
            text = shortcuts.plain(command.text) if command is not None else cid
            tip = shell.tips.get(cid, '')
            words[cid] = dict(text=text, tip=f'{text}\n{tip}' if tip else text)
        return words
    selectedModules = Property('QVariantList', lambda self: [f'{s}/{k}' for s, k in self._plan.editor.swept]
                               if self._plan else [], notify=changed)
    selectedSubfield = Property(str, lambda self: self.plant.session.selection[1] if self.plant.session.selection[0] == 'subfield' else '',
                                notify=changed)
    subfield = Property(str, lambda self: self.plant.session.selection[1] if self.plant.session.selection[0] == 'subfield'
                         else self.plant.session.selection[1].partition('/')[0] if self.plant.session.selection[0] == 'row'
                         else '', notify=changed)

    def _changed(self, topics):
        selection = self.plant.session.selection
        if selection != self._selection:
            self._selection = selection
            if selection[0] in ('row', 'subfield'):
                self._set_section('panels')
        if 'file' in topics:
            self._dialog = ''
            self._set_section('panels')
            self.catalog.dispose()
        self.changed.emit()

    def _set_section(self, section):
        """The section open, and with it what a click on a module of the plan does (R529): it chooses a string only
        while Inverter or Storage is open; with Panels open, or none, it selects the module. Before, closing Inverter
        (R507) or a sub-field chosen in the tree left the plan choosing strings, and no module could be selected."""
        self._section = section
        if self._plan is not None:
            self._plan.editor.strings_mode = section in ('inverter', 'storage')

    @Slot(str)
    def openSection(self, section):
        if section in ('panels', 'inverter', 'storage'):
            self._set_section(section)
            self.changed.emit()

    @Slot(str)
    def toggleSection(self, section):
        """A click on a head (R507): the open one closes, the string chosen stays lit; another opens."""
        if section == self._section:
            self._set_section('')
            self.changed.emit()
        else:
            self.openSection(section)

    @Slot(str)
    def open(self, dialog):
        self.host.shell.trigger('phase_plant')
        if dialog == 'catalog':
            self.openCatalog('inverters', -1)
            return
        self.openSection('storage' if dialog == 'storage' else 'inverter')
        if dialog == 'sizing':
            self.plant.loadMakers()
            # R522: on by itself when some modules are in strings and others are left
            self._only_free = self.plant.freeModules > 0
        if dialog == 'storage':
            self._battery = dict(self.plant.storage.get('battery') or {})
            self._storage_revision += 1
        self._dialog = dialog
        self.changed.emit()

    @Slot()
    def dismiss(self):
        self._dialog = ''
        self.changed.emit()

    def _catalog_context(self, kind, entry):
        """What the catalogue opens for (R421): the module and the inverter in hand, the coldest temperature, the product in
        use. Only what the project already says: nothing here changes it."""
        project = self.plant.session.project
        energy = project.energy or {}
        entries = system.inverter_entries(energy)
        inverter = entries[entry].get('record') if 0 <= entry < len(entries) else entries[0].get('record') if entries else None
        module = None
        for sf in project.subfields:
            if sf.module in project.modules and (not self.subfield or sf.id == self.subfield):
                module = project.modules[sf.module]
                break
        if module is None and project.modules:
            module = next(iter(project.modules.values()))
        module = module if module and module.get('vmp') else None
        context = {'t_min': core.conditions(project).t_min}
        current = ''
        if kind == 'optimizers':
            context.update(module=module, inverter=inverter)
            optimizer = entries[entry].get('optimizer') if 0 <= entry < len(entries) else None
            current = str((optimizer or {}).get('id') or '')
        elif kind in ('inverters', 'microinverters'):
            context.update(module=module)
            current = str((inverter or {}).get('id') or '') if entry >= 0 else ''
        elif kind == 'modules':
            context.update(inverter=inverter)
            sf = next((sf for sf in project.subfields if sf.id == self.subfield), None)
            current = str(sf.module) if sf is not None else ''
        elif kind == 'batteries':
            context.update(inverter=inverter)
            current = str((self.plant.storage.get('battery') or {}).get('id') or '')
        return {k: v for k, v in context.items() if v is not None}, current

    def reviewProposal(self, identifier, kind, record, chat):
        """Meridio's card: the plant's catalogue on the kind, its review window on the proposal."""
        self.host.shell.trigger('phase_plant')
        self._purpose, self._entry = kind, -1
        self.catalog.setKind(kind)
        self._dialog = 'catalog'
        self.changed.emit()
        if self._review_listener is not None:
            self.catalog.reviewFinished.disconnect(self._review_listener)
        self._review_listener = chat.catalogReviewFinished
        self.catalog.reviewFinished.connect(self._review_listener)
        sheet = record.pop('__datasheet', None)
        self.catalog.reviewProposal(identifier, kind, record)
        if sheet:
            self.catalog.readDatasheet(sheet)

    @Slot(str, int)
    def openCatalog(self, kind, entry=-1):
        self.host.shell.trigger('phase_plant')
        self._purpose, self._entry = kind, entry
        context, current = self._catalog_context(kind, entry)
        self.catalog.setContext(kind, context, current)
        self._dialog = 'catalog'
        if kind != 'batteries':
            self.openSection('panels' if kind == 'modules' else 'inverter')
        self.changed.emit()

    @Slot(str, 'QVariantMap')
    def chosen(self, kind, record):
        if kind in ('inverters', 'microinverters'):
            self.plant.addInverter(record)
        elif kind == 'optimizers':
            verdict = self.catalog._model.verdicts.get(record.get('id'), {})
            per = verdict.get('perUnit') or (2 if (record.get('modules_per_unit') or 1) >= 2 else 1)
            self.plant.setOptimizer(self._entry, record, per)
        elif kind == 'batteries':
            self._battery = dict(record)
            self._dialog = 'storage'
            self.changed.emit()
            return
        elif kind == 'modules':
            from meridiana import catalog
            sfid = self.subfield
            mid = str(record.get('id') or f"pan:{record.get('manufacturer', '')} {record.get('model', '')}")
            def put(p):
                p.modules[mid] = catalog.for_project(record)
                sf = next((sf for sf in p.subfields if sf.id == sfid), None)
                if sf is not None:
                    sf.module = mid
            self.plant.session.edit(_('Choose a module'), put)
        self.dismiss()

    @Slot(str)
    def importRequested(self, kind):
        self._purpose = kind
        self._dialog = 'pvsyst_file'
        self.changed.emit()

    @Slot(QUrl)
    def readPvsyst(self, url):
        if not url.isLocalFile():
            return
        from meridiana.catalog import panond
        path = Path(url.toLocalFile())
        reader = panond.module if self._purpose == 'modules' else panond.inverter
        self._dialog = 'catalog'
        def done(result):
            self._import_record, notes = result
            name = f"{self._import_record.get('manufacturer', '')} {self._import_record.get('model', '')}".strip()
            self._import_text = _('Read from {file}: {name}.\n\n{what}.\n\nUse it?').format(
                file=path.name, name=name, what=';\n'.join(notes))
            self._dialog = 'pvsyst_review'
            self.changed.emit()
        self.catalog._submit(lambda: reader(path), done)
        self.changed.emit()

    @Slot()
    def acceptPvsyst(self):
        if self._import_record:
            self.chosen(self._purpose, self._import_record)
            self._import_record = {}

    @Slot(bool)
    def proposal(self, replace=True):
        self._proposal_scope = 0
        # R522: with strings there and modules left, «only the modules in no string» comes chosen
        self._replace = replace and not self.plant.freeModules
        self.open('proposal')

    @Slot()
    def sizingFree(self):
        """R522, the plan's menu in Plant: the sizing window with «Only the modules in no string» on (the brand is
        chosen there: the favourites first)."""
        self.open('sizing')
        if not self._only_free:
            self._only_free = True
            self.changed.emit()

    @Slot(int)
    def proposalForUnit(self, unit):
        self._proposal_scope, self._replace = unit, True
        self.open('proposal')

    @Slot()
    def drawNew(self):
        self.openSection('inverter')
        target = self._input_for_new_string()
        if target is None:
            self.plant.tell(_("No inverter's input to draw a string on: add an inverter from the catalogue first."))
        else:
            self.draw(*target, -1)

    def _input_for_new_string(self):
        """The chosen string's input, otherwise a free input of the working inverter, then its first input."""
        state = self.plant.state
        if state is None or not state.inputs:
            return None
        chosen = self.plant.selected
        if 0 <= chosen < len(state.strings):
            string = state.strings[chosen]
            if (string.inverter, string.mppt) in state.inputs:
                return string.inverter, string.mppt
        working = self.plant.working
        inputs = {slot: value for slot, value in state.inputs.items() if not working or slot[0] == working}
        free = [slot for slot, value in sorted(inputs.items()) if not value.strings]
        return free[0] if free else min(inputs) if inputs else None

    @Slot(int, int, int)
    def draw(self, unit, mppt, index):
        plan = self._plan
        if plan is None:
            self.plant.tell(_('The plan is not available.'))
            return
        self.host.shell.trigger('phase_plant')
        self.openSection('inverter')
        plan.setTool('string')
        plan.editor.start_draft(unit, mppt, index=index)
        plan._overlays()
        plan.stateChanged.emit()

    @Slot(object)
    def _wired(self, state):
        if self._plan is not None:
            tips, default, fitted = module_words(state)
            states = {s.run: s.state for s in getattr(state, 'strings', []) if getattr(s, 'run', -1) >= 0}
            # the optimizers of the inverters with MPPT on the plan too (R456), those on some modules only by module
            for u in getattr(state, 'units', []):
                if getattr(u, 'mlpe', None) is not None and u.mlpe.family.function == 'optimizer':
                    fitted.setdefault(u.number, u.mlpe.per)
            partial = {u.number: u.partial for u in getattr(state, 'units', []) if getattr(u, 'partial', None)}
            self._plan.set_string_details(tips, default, fitted, states, partial)

    @Slot(int)
    def groups(self, index):
        """«Modules on each optimizer…» of a string's menu."""
        self.select(index)
        self.open('groups')

    @Slot(int)
    def select(self, index):
        if self._plan is not None and self._plan.chosenString != index:
            self._plan.chooseString(index)
        if index >= 0:
            self.openSection('inverter')

    @Slot()
    def follow_selection(self):
        colours = {str(label['run']): label['colour'] for label in self._plan._labels
                   if label.get('kind') == 'name' and 'run' in label}
        draft = list(self._plan.editor.draft_target[:2]) if self._plan.editor.draft_target else []
        target = self._plan.editor.draft_target
        tint = next((d['colour'] for d in self._plan._dots if d.get('draft')), '')
        self.plant.show_appearance(colours, draft, self.plant.draft_card(
            target, self._plan.editor.draft or [], tint) if target else None)
        if self._plan.chosenString != self.plant.selected:
            self.plant.selectString(self._plan.chosenString)

    def close(self):
        if self._changed in self.plant.session.listeners:
            self.plant.session.listeners.remove(self._changed)
        if self._plan is not None:
            self._plan.overlayChanged.disconnect(self.follow_selection)
            self._plan = None


def install(engine, session, cache, window):
    plant = PlantBackend(session, engine)
    catalog = CatalogBackend(session, engine)
    actions = PlantActions(plant, catalog, window, engine)
    summary = PlantSummary(plant, session, window.plan, engine)
    # A local Properties adapter borrows the existing sub-field editor, not its state.
    panels = PropertiesBackend(session, engine, defaults=True)     # R523: the defaults when no sub-field is selected

    def keep_in_profile():
        """«Keep in the profile» (R523): the defaults of this project for the new ones, in the user's settings."""
        cfg, paths = getattr(window, 'cfg', None), getattr(window, 'paths', None)
        if cfg is None or paths is None:
            return
        from meridiana import config, model
        cfg.layout_defaults = model.profile_defaults(session.project)
        try:
            config.save(cfg, paths.config_file)
        except OSError as error:
            window.shell.show_notice(_('The settings could not be saved: {error}').format(error=error))
            return
        window.shell.show_notice(_('Kept in the profile: a new project starts from these defaults.'))

    def panel_action(action, _kind, _oid):
        if action == 'catalog_module':
            actions.openCatalog('modules')
        elif action == 'defaults_profile':
            keep_in_profile()
        else:
            window.shell.trigger(action)
    panels.actionRequested.connect(panel_action)
    panels.helpRequested.connect(actions.help)
    QTimer.singleShot(1200, panels.warmForms)       # the sub-field form, soon after the opening (R465, R499)
    controllers = dict(plant=plant, plantActions=actions, catalog=catalog, plantPanels=panels, plantSummary=summary)
    for name, controller in dict(plantBackend=plant, plantActions=actions, catalogBackend=catalog, plantPanels=panels,
                                plantSummary=summary).items():
        engine.rootContext().setContextProperty(name, controller)
    plant.calculateRequested.connect(window.bridge.recompute)
    plant.layoutRequested.connect(lambda: window.shell.trigger('fill'))
    plant.messageChanged.connect(lambda: window.shell.show_notice(plant.message))    # the status bar, as the window's

    def bind(root):
        # the stale marks of compute and fill: Shell/PhaseHeader.qml makes them (staleMark), R23 F6
        properties = window.parts.controllers.get('properties')
        if properties is not None:
            properties.actionRequested.connect(lambda action, _kind, _oid: actions.openCatalog('modules')
                                               if action == 'catalog_module' else None)
        if getattr(window, 'cfg', None) is not None:
            from meridiana import config
            actions._strings_view = window.cfg.strings_view if window.cfg.strings_view in ('cards', 'diagram', 'table') else 'cards'
            actions.changed.emit()
            plant.setFavourites(window.cfg.inverter_brand_favourites)
            def favourites(values):
                window.cfg.inverter_brand_favourites = list(values)
                config.save(window.cfg, window.paths.config_file)
            plant.favouritesChanged.connect(favourites)

    def close():
        summary.close()
        actions.close()
        panels.close()
        catalog.dispose()
        plant.close()

    return Part('plant', sources={'plant': QML / 'Plant/PlantSide.qml', 'plantTrailing': QML / 'Plant/PlantStrip.qml'}, controllers=controllers, bind=bind, close=close,
                commands={'inverter_catalog': lambda: actions.open('catalog'),
                          'inverter_auto': lambda: actions.open('sizing'),
                          'battery_catalog': lambda: actions.open('storage'),
                          'strings_auto': lambda: actions.proposal(True),
                          'strings_complete': lambda: actions.proposal(False),
                          'strings_manual': actions.drawNew,
                          'strings_clear': lambda: actions.open('clear')})
