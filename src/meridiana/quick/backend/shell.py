"""Catalogue-driven shell and coarse-grained commands over the shared session."""
from dataclasses import asdict
from PySide6.QtCore import QLocale, QObject, Property, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QPainterPath

from meridiana import arrangement, checks, help as help_catalog, i18n, model, phases, props, shortcuts
from meridiana.i18n import _, ngettext, number
from meridiana.ui import phasebar
from meridiana.ui.design import Motion, Size, Space
from meridiana.ui.theme import background_names, colour_names
from meridiana.ui.appearance import font_names


def labels():
    """All shell copy is translated in Python, through the existing catalogue."""
    words = {key: _(value) for key, value in dict(
        title='Meridiana', file='File', model='Modelling', production='Production',
        project='Project', properties='Properties', checks='Checks', name='Name', height='Height',
        undo='Undo', redo='Redo', rectangle='Rectangle', select='Select', fit='Fit', calculate='Compute',
        all='All', fail='To fix', warn='To check', ok='Passed', info='To know', calculating='Computing…',
        ready='Select, inspect, change', modules='modules', year='Production', daily='Energy, kWh',
        empty='Nothing selected', meridio='Meridio',
        plan='Plan', view3d='3D', both='Plan and 3D side by side', close='Close', closeCard='Close the panel; View > Panels brings it back',
        altTabs='Alt: as tabs',
        zoomIn='Zoom in', zoomOut='Zoom out', help='Help', panels='Panels',
        plant='Plant', deliverables='Deliverables', data='Data',
        site='Site', buildings='Buildings', subfields='Sub-fields', exclusions='Exclusions',
        latitude='Latitude', longitude='Longitude', address='Address',
        byLevel='By level', byObject='By object', byArea='By area', thisPhase='This phase',
        thisObject='This object', base='Base', newVariant='New variant', settings='Settings',
        appearance='Appearance', theme='Theme', light='Light', dark='Dark', accent='Accent colour',
        font='Font', textSize='Size of the text', small='Small (12 px)', medium='Medium (13 px)', large='Large (14 px)',
        reducedMotion='Less motion', restore='Restore the default layout',
        dock='Dock', float='Float', group='Group', ungroup='Ungroup', cancel='Cancel',
        noSelection='Nothing selected', noResults='Nothing computed yet.',
        placeholder='not available', guide='Help',
        system='System', backgrounds='Backgrounds',
        selectHint='Click: select · Wheel: zoom · Middle button: pan',
        drawHint='Drag: rectangle · Esc: select',
        saveAs='Save as…', unsaved='Changes not saved yet: Ctrl+S saves them',
    ).items()}
    locale = QLocale('it_IT') if i18n.language() == 'it' else QLocale('en_GB')
    words.update(jan=locale.monthName(1), dec=locale.monthName(12))
    return words


class ShellController(QObject):
    closeRequested = Signal()
    changed = Signal()
    commandEnabledChanged = Signal()
    catalogChanged = Signal()
    commandRequested = Signal(str)
    toolRequested = Signal(str)
    panelRequested = Signal(str)
    phaseRequested = Signal(str)
    objectRequested = Signal(str)
    # R375: a kind with the way to place it (ObjectPicker.qml): {mode: place | line | group, step, align, radius,
    # variation, asset, repeat}
    objectWanted = Signal(str, 'QVariantMap')
    escapeRequested = Signal()
    fileRequested = Signal(bool)
    helpRequested = Signal(str)
    variantRequested = Signal(str)
    checkLevelRequested = Signal(str)
    # R23 F6 (docs/studio/39-contratto-backend-qml.md): what the backend asks of the window, answered by Workbench.qml in
    # its Connections on `shell`; the backend never looks an item up nor writes its properties. panelRequested(id)
    # opens the panel and brings it forward; focusRequested(name) gives the keyboard to the item so named (the visit by
    # name is made in QML, Workbench.findNamed); menuBarRequested(open, always), `always` only when it is not null.
    viewModeRequested = Signal(str)
    fileOpenRequested = Signal(bool)
    focusRequested = Signal(str)
    toolbarModeRequested = Signal(str)
    toolbarPositionRequested = Signal(str)
    menuBarRequested = Signal(bool, 'QVariant')
    projectDirtyChanged = Signal()
    planStatusChanged = Signal()

    def __init__(self, bridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self._project_dirty = False
        self._plan_status = ''
        self._commands = {command.id: command for command in shortcuts.commands()}
        self.command_ids = tuple(self._commands)
        self._bindings = shortcuts.bindings({})
        self._handlers = dict(undo=bridge.undo, redo=bridge.redo, compute=bridge.recompute,
                              new_variant=self._new_variant)
        self._notice = ''
        self._notice_kind = ''          # R537: 'busy', 'done', 'error' or '' (a plain sentence)
        self._notice_fading = False
        self._notice_of = ''            # the sentence the kind belongs to
        self.checks_provider = None
        from .shell_tips import tips
        self.tips = tips()
        bridge.stateChanged.connect(self.changed)
        if hasattr(bridge, 'progressChanged'):
            bridge.progressChanged.connect(self.changed)
        if hasattr(bridge, 'noticed'):
            bridge.noticed.connect(lambda text: self._tell(text, 20000))
        bridge.objectsChanged.connect(self.changed)
        bridge.checksChanged.connect(self.changed)
        bridge.selectionChanged.connect(self.changed)
        self._command_enabled = None
        self.changed.connect(self._enabled_changed)

    def _enabled_state(self):
        session = self.bridge.session
        kind, oid = session.selection
        sfid = oid.partition('/')[0] if kind in ('subfield', 'row') else ''
        sf = next((s for s in session.project.subfields if s.id == sfid), None)
        return (sf is not None, sf is not None and sf.filled, session.undo.can_undo(), session.undo.can_redo())

    def _enabled_pair(self):
        state = self._enabled_state()
        return state, dict(fill=state[0], empty=state[1], refill=state[1], undo=state[2], redo=state[3])

    def _enabled_changed(self):
        """The 300 tools and menu entries bound to commandEnabled re-read it only when what it says changes."""
        pair = self._enabled_pair()
        if self._command_enabled is None or self._command_enabled[0] != pair[0]:
            self._command_enabled = pair
            self.commandEnabledChanged.emit()

    def commands_known(self):
        return list(self._commands)

    @Slot(str, int, int, str, result=float)
    def glyphCenter(self, family, size, weight, text):
        font = QFont(family)
        font.setPixelSize(size)
        font.setWeight(QFont.Weight(weight))
        path = QPainterPath()
        path.addText(0, 0, font, text)
        return path.boundingRect().center().y()

    @Slot(str, int, int, str, float, result=str)
    def glyphPath(self, family, size, weight, text, disc):
        """The same unhinted outline the Widgets phase disc fills."""
        font = QFont(family)
        font.setPixelSize(size)
        font.setWeight(QFont.Weight(weight))
        path = QPainterPath()
        path.addText(0, 0, font, text)
        center = path.boundingRect().center()
        path.translate(disc/2-center.x(), disc/2-center.y())
        commands, index = [], 0
        while index < path.elementCount():
            element = path.elementAt(index)
            if element.isCurveTo():
                points = [path.elementAt(index+i) for i in range(3)]
                commands.append('C'+' '.join(f'{p.x:.4f},{p.y:.4f}' for p in points))
                index += 3
            else:
                commands.append(('M' if element.isMoveTo() else 'L')+f'{element.x:.4f},{element.y:.4f}')
                index += 1
        return ' '.join(commands)

    @Slot('QVariantMap', 'QVariantMap', bool, result='QVariantMap')
    def arrangedSay(self, was, new, remembered):
        """ui/window.py _say_arranged: a line with what changed. The fields, for its Undo."""
        before, now = arrangement.from_dict(was), arrangement.from_dict(new)
        if before is None or now is None:
            return dict(fields=[])
        fields = arrangement.changes(before, now)
        if remembered:
            self._tell(_('The arrangement you left for this shape of the window is back.'))
        elif fields:
            what = {'checks_open': _('Checks closed, the count stays in the status bar') if not now.checks_open else _('Checks open again'),
                    'views': {'side': _('plan and 3D side by side'), 'stacked': _('plan and 3D one above the other'),
                              'one': _('one view at a time')}[now.views],
                    'panels': _('the side panels together') if now.panels == 'together' else _('the side panels apart'),
                    'bar': {'under': _('the words under the icons'), 'beside': _('the words beside the icons'),
                            'icons': _('the icons alone')}[now.bar]}
            self._tell(_('The window changed shape: {what}.').format(what=', '.join(what[f] for f in fields)))
        return dict(fields=list(fields))

    @Slot('QVariantMap', 'QVariantMap', 'QVariantList', result='QVariantMap')
    def arrangePinned(self, pins, was, fields):
        return arrangement.pinned(pins, arrangement.from_dict(was), tuple(fields))

    @Slot()
    def arrangeBack(self):
        self._tell(_('Back as it was: this shape of the window stays so until «Restore the default layout».'))

    def _tell(self, text, ms=15000):
        self._notice = text
        self.changed.emit()

        def clear():
            if self._notice == text:
                self._notice = ''
                self.changed.emit()
        QTimer.singleShot(ms, self, clear)

    @Slot(int, int, str, 'QVariantMap', result='QVariantMap')
    def layoutFor(self, width, height, phase, options):
        """Same responsive policy as Widgets, called only after a settled resize."""
        previous = arrangement.from_dict(options.get('previous', {}))
        choices = arrangement.Choices(previous=previous, pins=options.get('pins', {}),
                                      toolbar=options.get('toolbar', 'text'),
                                      needs=options.get('needs', {}), bar_sides=phasebar.BAR_SIDES,
                                      columns=tuple(options.get('columns', [310, 370])),
                                      checks=options.get('checks', 220))
        return asdict(arrangement.arrangement(width, height, phase, choices))

    def register_command(self, command, handler):
        """A page installs its real implementation once, never once per frame."""
        if command not in self._commands:
            raise KeyError(command)
        self._handlers[command] = handler
        self.catalogChanged.emit()

    def register_menu_action(self, command, handler):
        """Plain Widgets menu actions have no entry in the editable key catalogue."""
        self._handlers[command] = handler
        self.catalogChanged.emit()

    def set_bindings(self, overrides):
        self._bindings = shortcuts.settle(overrides)[0]
        self.catalogChanged.emit()

    @Slot()
    def escape(self):
        self.escapeRequested.emit()

    # R537: something to save (the dot on File), measured by app.py once per change; Workbench.projectDirty binds it
    @Property(bool, notify=projectDirtyChanged)
    def projectDirty(self):
        return self._project_dirty

    def _get_plan_status(self):
        return self._plan_status

    def _set_plan_status(self, text):
        if self._plan_status != (text or ''):
            self._plan_status = text or ''
            self.planStatusChanged.emit()

    # QML -> Python: the plan's status line (PlanHost.statusText), written by Workbench.qml; plan_part reads it
    planStatus = Property(str, _get_plan_status, _set_plan_status, notify=planStatusChanged)

    def set_project_dirty(self, dirty):
        if self._project_dirty != bool(dirty):
            self._project_dirty = bool(dirty)
            self.projectDirtyChanged.emit()

    @Property('QVariantList', constant=True)
    def objectKinds(self):
        names = model.prop_names()
        return [dict(title=_(title), kinds=[dict(id=k, text=names[k]) for k in kinds])
                for title, kinds in [('Trees', props.TREE_KINDS),
                                     ('Roof obstacles', tuple(k for k in props.OBSTACLE_KINDS if k != 'opening')),
                                     ('People', props.PERSON_KINDS), ('Cars', props.CAR_KINDS)]]

    @Property('QVariantList', constant=True)
    def objectGroups(self):
        """R374, R375: the picker's groups, every active model of the catalogue reachable (models3d.GROUPS)."""
        from .models3d import groups
        return groups()

    @Property('QVariantMap', constant=True)
    def objectPickerTexts(self):
        return dict(place=_('Choose and place'), line=_('Along a line'), group=_('Small family'),
                    placeHint=_('Click the plan to place a copy at each click; Esc ends.'),
                    lineHint=_('Click the start and the end of the line: a copy every step. A fence, a hedge and a walkway follow the line drawn.'),
                    groupHint=_('Click the plan: a small group with light differences in size and turn.'),
                    step=_('Step'), align=_('Turn along the line'), radius=_('Radius'), variation=_('Variation'))

    @Slot(str, result=str)
    def helpText(self, phase):
        topic = help_catalog.texts().get('phase.' + phase)
        return topic.text if topic else ''

    @Property('QVariantList', constant=True)
    def accents(self):
        return [dict(id=key, text=text) for key, text in colour_names().items()]

    @Property('QVariantList', constant=True)
    def fonts(self):
        return [dict(id=key, text=text) for key, text in font_names().items()]

    @Property('QVariantList', constant=True)
    def backgrounds(self):
        return [dict(id=key, text=text) for key, text in background_names().items()]

    @Slot(str, 'QVariantList', str, bool, bool, result='QVariantList')
    def checkGroups(self, by, levels, phase, phase_only, object_only):
        rows = [checks.Item(**r) for r in self.bridge._checks]
        names = {(row['kind'], row['oid']): row['name'] for row in self.bridge._objects}
        names['site', ''] = self.bridge.session.project.name
        selected = self.bridge.session.selection
        if phase_only:
            rows = [row for row in rows if checks.shown_in_phase(row, phase)]
        if object_only:
            rows = [row for row in rows if tuple(row.target[:2]) == selected]
        if levels:
            rows = [row for row in rows if row.level in levels]
        return [dict(key=':'.join(g.key), text=g.name, level=g.level, closed=g.closed,
                     rows=[vars(rows[n]) for n in g.items]) for g in checks.grouped(rows, by, names)]

    @Slot(str, str, bool, bool, result=str)
    def panelTip(self, command, title, seen, covered):
        """What a click on a card's button does, said as it is: hidden or shown, never closed."""
        what = _('Hide the {card} panel') if seen else _('Bring back the {card} panel') if covered else _('Show the {card} panel')
        keys = self._bindings.get(command, ())
        what = what.format(card=title)
        return f'{what} ({keys[0]})' if keys else what

    @Slot(str, 'QVariant', result=str)
    def sideTip(self, edge, cards):
        """R549: a side's button says the side and what stands there now («Left side: Project»), or, hidden, what a
        click brings back; the left side with its key (Ctrl+B, as in VS Code)."""
        cards = cards.toVariant() if hasattr(cards, 'toVariant') else dict(cards or {})
        side = {'left': _('Left side'), 'bottom': _('Bottom side'), 'right': _('Right side')}[edge]
        names = ', '.join(cards.get('titles') or ())
        what = (_('{side}: {cards}') if cards.get('shown') else _('{side}, hidden: {cards}')).format(side=side, cards=names)
        keys = self._bindings.get('side_left', ()) if edge == 'left' else ()
        return f'{what} ({keys[0]})' if keys else what

    @Property('QVariantList', notify=changed)
    def checkCounts(self):
        words = checks.level_names()
        counts = self.checks_provider.counts if self.checks_provider else {
            level: sum(r['level'] == level for r in self.bridge._checks) for level in checks.LEVELS}
        return [dict(id=level, text=words[level], count=counts.get(level, 0),
                     tip=_('{n} {level}: a click leads to their section in the Checks panel').format(n=counts.get(level, 0), level=words[level]))
                for level in checks.LEVELS]

    @Property('QStringList', notify=changed)
    def stalePhases(self):
        return ['production', 'consumption', 'economics'] if self.bridge.session.energy_outdated() else []

    @Property('QVariantMap', notify=changed)
    def yearState(self):
        """R437: one state of the numbers, the same everywhere: `none`, `current`, `stale`, with what changed."""
        session = self.bridge.session
        if not session.energy:
            return dict(state='none', text='', fingerprint='')
        if not session.year_outdated():
            return dict(state='current', text=_('Up to date: the numbers answer for the plant as it is now.'), fingerprint=session.year_fingerprint())
        changes = session.year_changes()
        text = (_('Not up to date: {what} changed after this computation. The numbers are those of before.').format(what=', '.join(changes))
                if changes else _('Not up to date: the project changed after this computation. The numbers are those of before.'))
        updating = bool(getattr(self.bridge, 'updating', False))
        if updating:            # R461
            text = _('Updating in the background: {what} changed. The numbers are those of before.').format(
                what=', '.join(changes) or _('the project'))
        return dict(state='stale', text=text, fingerprint=session.year_fingerprint(), updating=updating)

    @Property(str, constant=True)
    def yearComputing(self):
        return _('Computing: until it ends the numbers are those of before.')

    @Property(str, constant=True)
    def staleTip(self):
        return _('To update: the project changed after this computation; «Compute» (F5) computes it again')

    @Slot(bool)
    def layoutRestored(self, previous):
        self._notice = (_('The panels are back as they were before.') if previous else
                        _('The panels are back as at the first start. {keys} again within {seconds} seconds brings back the arrangement before.').format(
                            keys=', '.join(self._bindings.get('default_layout', ())), seconds=15))
        self.changed.emit()
        notice = self._notice

        def clear():
            if self._notice == notice:
                self._notice = ''
                self.changed.emit()
        QTimer.singleShot(15000, self, clear)

    @Slot(str)
    def show_notice(self, text, ms=15000, kind=''):
        """A sentence of a part in the status bar for a while (QStatusBar.showMessage): one line. R537: `kind`
        'busy' (a save going on), 'done' (the save done: it fades out at its end, Theme.motion.SLOW), 'error' or
        'error-open' (they stay until closed, a plain sentence of another part does not cover them); `ms` 0: until
        replaced. The kind belongs to its sentence: another one written in its place (_tell) has none."""
        if self._kind().startswith('error') and not kind:
            return
        self._notice = self._notice_of = ' · '.join(line for line in str(text).splitlines() if line)
        self._notice_kind = kind
        self._notice_fading = False
        self.changed.emit()
        notice = self._notice
        if not ms:
            return
        fade = Motion.SLOW if kind == 'done' else 0

        def fading():
            if self._notice == notice:
                self._notice_fading = True
                self.changed.emit()

        def clear():
            if self._notice == notice:
                self._notice, self._notice_kind, self._notice_fading = '', '', False
                self.changed.emit()
        if fade:
            QTimer.singleShot(max(0, ms - fade), self, fading)
        QTimer.singleShot(ms, self, clear)

    @Slot()
    def dismissNotice(self):
        """The cross of a notice that stays (R537: an error of a save)."""
        self._notice, self._notice_kind, self._notice_fading = '', '', False
        self.changed.emit()

    def _kind(self):
        return self._notice_kind if self._notice and self._notice == self._notice_of else ''

    noticeKind = Property(str, _kind, notify=changed)
    noticeFading = Property(bool, lambda self: self._notice_fading and bool(self._kind()), notify=changed)

    @Slot(str, result=bool)
    def available(self, command):
        return command in self._handlers

    @Property('QVariantMap', notify=commandEnabledChanged)
    def commandEnabled(self):
        if self._command_enabled is None:       # the first read: no emit inside a binding (a binding loop)
            self._command_enabled = self._enabled_pair()
        return self._command_enabled[1]

    def _tool(self, tool):
        command = self._commands.get(tool.command)
        label = tool.label or (command.text.replace('&', '') if command else tool.command)
        tip = command.text.replace('&', '') if command else label
        if command and self._bindings.get(command.id):
            tip += ' (' + ', '.join(self._bindings[command.id]) + ')'
        explanation = self.tips.get(tool.command)
        if explanation:
            tip += '\n' + explanation
        family = [self._tool(t) for t in tool.more]
        strip = _('All of them: {names} (the right button too)').format(names=', '.join([label, *(t['label'] for t in family)]))
        face_tip = tip
        if family:
            head, separator, rest = tip.partition('\n')
            face_tip = head + '. ' + ngettext('{n} more in the arrow', '{n} more in the arrow', len(family)).format(n=len(family)) + (separator+rest if rest else '')
        return dict(command=tool.command, label=label, icon=tool.icon or tool.command, tip=tip,
                    title=command.text.replace('&', '') if command else label,
                    keys=list(self._bindings.get(tool.command, ())), faceTip=face_tip, stripTip=strip,
                    enabled=self.available(tool.command), more=family,
                    danger=tool.danger, fixed=tool.fixed, primary=tool.primary)

    @Property('QVariantList', notify=catalogChanged)
    def phases(self):
        return [dict(id=p.id, number=p.number, title=p.title, inspector=p.inspector,
                     groups=[dict(id=g.id, title=g.title,
                                  tools=[self._tool(t) for t in g.tools if not t.planned]) for g in p.groups])
                for p in phases.phases()]

    @Property('QVariantList', notify=catalogChanged)
    def menus(self):
        def action(cid, title):
            return dict(id=cid, text=title.replace('&', ''), keys=list(self._bindings.get(cid, ())),
                        tip=self.tips.get(cid, ''), enabled=self.available(cid))

        def commands(group):
            rows = [action(c.id, c.text) for c in self._commands.values() if c.group == group]
            if group == 'variants':
                rows[1:1] = [action('variant_rename', _('Rename the variant…')), action('variant_delete', _('Delete a variant…'))]
            elif group == 'site':
                rows = [action('find_site', _('Find the site…'))]
            elif group == 'catalogues':
                from meridiana.ui.catalog_dialog import kind_titles
                rows = [action('browse_' + kind, title+'…') for kind, title in kind_titles().items()]
                rows += [action('product_module', _('Import a module from PVsyst (.PAN)…')),
                         action('product_inverter', _('Import an inverter from PVsyst (.OND)…'))]
            return rows
        titles = {key: _(title) for key, title in dict(file='&File', edit='&Edit', draw='&Draw', view='&View',
                  catalogues='&Catalogues', site='&Site', compute='Co&mpute', variants='V&ariants', help='&Help').items()}
        return [dict(id=group, title=title.replace('&', ''),
                     mnemonic=title.partition('&')[2][:1], commands=commands(group),
                     submenus=[dict(title=shortcuts.groups()[g], commands=commands(g)) for g in ('phases', 'panels')]
                     if group == 'view' else []) for group, title in titles.items()]

    @Property('QVariantList', notify=catalogChanged)
    def keyCommands(self):
        return [dict(id=cid, keys=keys) for cid, keys in self._bindings.items() if keys and self.available(cid)]

    @Property('QVariantMap', constant=True)
    def metrics(self):
        return dict(tabHeight=phasebar.TAB_HEIGHT, tabPad=list(phasebar.TAB_PAD), badge=phasebar.BADGE,
                    tall=phasebar.TALL, low=phasebar.LOW, cardPad=list(phasebar.CARD_PAD),
                    lowWindow=phasebar.LOW_WINDOW, headerGap=Space.XXS,
                    leftWidth=310, rightWidth=370,
                    checksHeight=230,
                    titleHeight=Size.CONTROL+Space.S)

    @Property('QVariantList', notify=changed)
    def variants(self):
        return [dict(id=v['id'], text=_(v['name']) if v['name'] == 'Base' else v['name'])
                for v in self.bridge.session.project.variants]

    @Property(str, notify=changed)
    def currentVariant(self):
        return self.bridge.session.project.variant

    @Property(str, notify=changed)
    def notice(self):
        return self._notice

    @Property(bool, notify=changed)
    def canRedo(self):
        return self.bridge.session.undo.can_redo()

    @Property('QVariantMap', notify=changed)
    def site(self):
        p = self.bridge.session.project
        return dict(name=p.name, latitude=number(p.site.lat, 6), longitude=number(p.site.lon, 6),
                    address=p.site.address)

    @Slot(str, result=bool)
    def trigger(self, command):
        handler = self._handlers.get(command)
        if handler is None:
            self._notice = _('not available')
            self.changed.emit()
            return False
        if self._notice and not self._kind().startswith('error'):      # R537: an error stays until closed
            self._notice, self._notice_kind = '', ''
            self.changed.emit()
        handler()
        self.commandRequested.emit(command)
        return True

    def _new_variant(self):
        session = self.bridge.session
        session.edit(_('New variant'), lambda p: p.add_variant(
            _('Variant {n}').format(n=len(session.project.variants))))

    @Slot(str)
    def chooseVariant(self, vid):
        if vid == self.currentVariant:
            return
        if not any(v['id'] == vid for v in self.variants):
            raise ValueError('Unknown variant: ' + vid)
        session = self.bridge.session
        session.edit(_('Change variant'), lambda p: p.switch_variant(vid))
