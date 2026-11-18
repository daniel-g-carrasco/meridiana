"""Autonomous properties adapter: stable fields, transactional edits and guarded drafts."""
from __future__ import annotations

import copy
import datetime
import math
from dataclasses import replace

from PySide6.QtCore import QTimer, QObject, Property, QLocale, Signal, Slot, Qt
from PySide6.QtGui import QFont, QFontMetrics

from meridiana import manual, props, quantity, roofs, sides
from meridiana import vvf_activities as vvf
from meridiana.fields import field_label
from meridiana.i18n import _, language, number
from meridiana.quick.backend.properties_schema import build_schema, common_schema, support_now, support_reference


class PropertyField(QObject):
    """One persistent field. Value updates never destroy the editor or its draft."""
    changed = Signal()

    def __init__(self, data, parent):
        super().__init__(parent)
        self._data = data

    @Property('QVariantMap', notify=changed)
    def data(self):
        return self._data

    def update(self, data):
        if self._data != data:
            self._data = data
            self.changed.emit()

    @Slot(QFont, result='QVariantMap')
    def labelHint(self, font):
        """QLabel's plain-text size hint, without constructing a QWidget.

        Qt's QLabelPrivate::sizeForWidth tries 80, 40, then 20 average
        characters for a wrapped label. ui/style.py wraps labels over 28.
        This keeps QFormLayout's label column without guessing a fixed width.
        """
        text, metrics = self._data['label'], QFontMetrics(font)
        wrapped = len(text) > 28
        flags = Qt.TextFlag.TextWordWrap if wrapped else Qt.TextFlag.TextSingleLine
        width = metrics.averageCharWidth() * 80 if wrapped else 2000
        rect = metrics.boundingRect(0, 0, width, 2000, flags, text)
        if wrapped and rect.height() < 4 * metrics.lineSpacing() and rect.width() > width / 2:
            rect = metrics.boundingRect(0, 0, width // 2, 2000, flags, text)
        if wrapped and rect.height() < 2 * metrics.lineSpacing() and rect.width() > width / 4:
            rect = metrics.boundingRect(0, 0, width // 4, 2000, flags, text)
        return dict(width=rect.width(), height=rect.height(), wrapped=wrapped)

    @Slot(QFont, result=int)
    def editorMinimum(self, font):
        """Qt's range-dependent minimum, with Meridiana's control style.

        QAbstractSpinBox measures both range ends, not the current value.
        Its two cursor pixels and our styled frame/buttons add 59 px.
        The eight-character combo includes the icon and styled arrow (60 px).
        Differential tests compare these dimensions with the actual Widgets.
        """
        data, metrics = self._data, QFontMetrics(font)
        if data['kind'] == 'choice':
            return 8 * metrics.horizontalAdvance('X') + 60
        if data['kind'] != 'number':
            return 80
        texts = []
        for value in (data['minimum'], data['maximum']):
            unit = data['unit']
            if unit in ('m', '°'):
                text = number(value, data['decimals']) + ('' if unit == '°' else ' ') + unit
            else:
                text = QLocale().toString(float(value), 'f', data['decimals'])
            texts.append(text[:18] + ' ')
        texts.append(data.get('special', ''))
        return max(metrics.horizontalAdvance(text) for text in texts) + 59


class PropertiesBackend(QObject):
    sectionsChanged = Signal()
    formAdded = Signal(str)         # a form of a new shape built: its key, for QML to make its items once
    formChanged = Signal()          # which form is the current one
    epochChanged = Signal()
    changed = Signal()
    confirmationChanged = Signal()
    actionRequested = Signal(str, str, str)
    helpRequested = Signal(str)
    errorOccurred = Signal(str)

    def __init__(self, session, parent=None, defaults=False):
        super().__init__(parent)
        self.session = session
        # R523: the Plant's panel shows the defaults of the next sub-fields when no sub-field is selected
        self._defaults = defaults
        self._sections, self._previous = [], []
        self._fields, self._shape = {}, ()
        # One form kept alive for each shape ever shown (the key and kinds of its fields), its QML items with it:
        # choosing a building again changes the values of fields already built, nothing is made from scratch
        # (06/11/2026, the Quick's slowness: 0.4-1.2 s to rebuild the form at every edit and selection).
        self._forms, self._current = {}, ''
        self._epoch, self._error = 0, ''
        self._subject, self._kind, self._oid = None, 'site', ''
        self._many = []
        self._pending, self._confirmation = None, {}
        self._closed = False
        session.subscribe(self._on_change)
        session.undo.listeners.append(self._undo_changed)
        self.refresh()

    def close(self):
        if not self._closed:
            self._closed = True
            if self._on_change in self.session.listeners:
                self.session.listeners.remove(self._on_change)
            if self._undo_changed in self.session.undo.listeners:
                self.session.undo.listeners.remove(self._undo_changed)

    def _undo_changed(self):
        self.changed.emit()

    @Property('QVariantList', notify=sectionsChanged)
    def sections(self):
        return self._sections

    @Property('QVariantList', notify=sectionsChanged)
    def previousSections(self):
        return self._previous

    @Property(str, notify=formChanged)
    def currentForm(self):
        return self._current

    @Property('QStringList', notify=formAdded)
    def formKeys(self):
        return [key for key, _sections, _fields in self._forms.values()]

    @Slot(str, result='QVariantList')
    def formSections(self, key):
        """The sections of the form `key`, their fields the same objects for as long as the backend lives."""
        for found, sections, _fields in self._forms.values():
            if found == key:
                return sections
        return []

    @Property(int, notify=epochChanged)
    def epoch(self):
        return self._epoch

    @Property(str, notify=changed)
    def kind(self):
        return self._kind

    @Property(str, notify=changed)
    def objectId(self):
        return self._oid

    @Property(str, notify=changed)
    def heading(self):
        """What the form changes, said above it (R523): the defaults of the next sub-fields, or the sub-field."""
        if self._kind == 'defaults':
            return _('Defaults for the next sub-fields')
        if self._many:
            return _('{n} sub-fields selected').format(n=len(self._many))
        target = self._target()
        return _('Sub-field «{name}»').format(name=target.name) if self._kind == 'subfield' and target else ''

    @Property(str, notify=changed)
    def error(self):
        return self._error

    @Property(bool, notify=changed)
    def canUndo(self):
        return self.session.undo.can_undo()

    @Property(bool, notify=changed)
    def canRedo(self):
        return self.session.undo.can_redo()

    @Property('QVariantMap', notify=confirmationChanged)
    def confirmation(self):
        return self._confirmation

    @Property('QVariantMap', constant=True)
    def labels(self):
        return dict(undo=_('Undo'), redo=_('Redo'), cancel=_('Cancel'), help=_('Help'),
                    adapt=_('Adapt the rows'), again=_('Lay again automatically'),
                    accept=_('Yes'), search=_('Number or words of the activity'))

    def field(self, key):
        return self._fields.get(key)

    def _target(self):
        p, kind, oid = self.session.project, self._kind, self._oid
        if kind == 'building':
            return p.building(oid)
        if kind == 'subfield':
            return self.session.subfield(oid)
        if kind == 'exclusion':
            return next((e for e in p.exclusions if e.id == oid), None)
        if kind == 'prop':
            return p.prop(oid)
        return p                                # the site, and the defaults of the next sub-fields (R523)

    def _thing(self, oid):
        keep, self._oid = self._oid, oid
        try:
            return self._target()
        finally:
            self._oid = keep

    def _on_change(self, topics):
        if 'restored' in topics or 'file' in topics:
            self._epoch += 1
            self.epochChanged.emit()
        if getattr(self, '_warm', False) and any(t.startswith('layout:') for t in topics):
            QTimer.singleShot(600, self.warmForms)
        if any(t.startswith('project:') or t.startswith('layout:') for t in topics) or topics & {'selection', 'restored', 'file'}:
            self.refresh()

    @Slot()
    def refresh(self):
        kind, oid = self.session.selection
        if kind == 'row':
            kind, oid = 'subfield', oid.partition('/')[0]
        if kind not in ('building', 'subfield', 'exclusion', 'prop'):
            kind, oid = 'site', ''
        if self._defaults and kind != 'subfield':
            kind, oid = 'defaults', ''
        self._kind, self._oid = kind, oid
        obj = self._target()
        if obj is None:
            self._kind, self._oid, obj = ('defaults' if self._defaults else 'site'), '', self.session.project
        self._many = self.session.selected_many() if self._kind not in ('site', 'defaults') else []
        subject = self._kind, self._oid, tuple(self._many), self.session.project.variant
        if subject != self._subject:
            self._subject = subject
            self._epoch += 1
            self._error = ''
            self.epochChanged.emit()
        schema = (common_schema(self.session, self._kind, [self._thing(oid) for oid in self._many]) if self._many else
                  build_schema(self.session, self._kind, obj))
        # Labels/options may change without changing the control's shape.
        shape = self._shape_of(schema)
        if shape == self._shape:
            for section in schema:
                for data in section['fields']:
                    self._fields[data['id']].update(data)
        else:
            # The preceding form stays alive, as every form of a shape already seen: QML crossfades to the next one
            # without passing through an empty Loader (R377) and without building anything twice.
            self._previous = self._sections
            form = self._form_for(shape, schema)
            self._current, self._sections, self._fields = form
            self._shape = shape
            self.formChanged.emit()
            self.sectionsChanged.emit()
        self.changed.emit()

    def _form_for(self, shape, schema):
        """The form of this shape, made now (its QML items with it, through formAdded) or found with its values
        brought up to date."""
        form = self._forms.get(shape)
        if form is None:
            fields, sections = {}, []
            for section in schema:
                own = [PropertyField(data, self) for data in section['fields']]
                fields.update((f.data['id'], f) for f in own)
                sections.append({**section, 'fields': own})
            added = f'form{len(self._forms)}'
            form = self._forms[shape] = (added, sections, fields)
            self.formAdded.emit(added)
        else:
            for section in schema:
                for data in section['fields']:
                    form[2][data['id']].update(data)
        return form

    @staticmethod
    def _shape_of(schema):
        return tuple((section['key'], tuple((f['id'], f['kind']) for f in section['fields'])) for section in schema)

    @Slot()
    def warmForms(self):
        """The forms a selection will show first (a building, a sub-field: the project's first ones) built while the
        window is idle after the opening (R465): the first selection of each kind no longer pays 0,3-0,5 s for the
        form's items. One form per call, the next scheduled after it, so the window stays free in between."""
        if self._closed:
            return
        self._warm = True
        p = self.session.project
        # A sub-field's form depends on its layout: built once the layout is there (and again when it comes).
        laid = [sf for sf in p.subfields if not isinstance(self.session.results.get(sf.id), (type(None), Exception))]
        for kind, things in (('building', p.buildings), ('subfield', laid)):
            for thing in things:            # every object: the shapes repeat, each distinct one is built once
                schema = build_schema(self.session, kind, thing)
                shape = self._shape_of(schema)
                if shape not in self._forms:
                    self._form_for(shape, schema)
                    QTimer.singleShot(400, self.warmForms)
                    return

    def _refuse(self, why):
        self._error = _('Not changed: {why}').format(why=why)
        self.changed.emit()
        self.errorOccurred.emit(self._error)
        return False

    def _read(self, data, value):
        if data['kind'] == 'number':
            if isinstance(value, bool):
                raise ValueError(_('Enter a number'))
            if isinstance(value, str):
                if data['special'] and value.strip() == data['special']:
                    return data['minimum']
                unit = data['unit']
                if unit in ('m', '°'):
                    value = quantity.parse(value, 'length' if unit == 'm' else 'angle', unit)
                else:
                    text = value.strip()
                    if unit and text.endswith(unit):
                        text = text[:-len(unit)].strip()
                    # The numeric Widgets use the application's Italian locale.
                    locale = QLocale('it_IT' if language() == 'it' else 'en_US')
                    group = locale.groupSeparator()
                    # QDoubleSpinBox accepts a grouping separator even when CLDR
                    # would omit it for four digits (Italian 1.000). QuantityField
                    # deliberately follows its stricter core parser instead.
                    if group in text:
                        if text.startswith(group) or text.endswith(group) or group * 2 in text:
                            raise ValueError(_('Enter a number'))
                        text = text.replace(group, '')
                    value, valid = locale.toDouble(text)
                    if not valid:
                        raise ValueError(_('Enter a number'))
            value = float(value)
            if not math.isfinite(value):
                raise ValueError(_('Enter a number'))
            value = round(value, data['decimals'])
            if not data['minimum'] <= value <= data['maximum']:
                raise ValueError(_('{value} is out of the range, from {lo} to {hi}').format(
                    value=number(value), lo=number(data['minimum']), hi=number(data['maximum'])))
            return int(value) if not data['decimals'] else value
        if data['kind'] == 'choice':
            if not any(type(value) is type(o['value']) and value == o['value'] and o['enabled'] for o in data['options']):
                raise ValueError(_('Choose an item from the list'))
            return value
        if data['kind'] == 'check':
            if not isinstance(value, bool):
                raise ValueError(_('Choose an item from the list'))
            return value
        return str(value).strip()

    @Slot(str, 'QVariant', result=bool)
    @Slot(str, 'QVariant', int, result=bool)
    def commit(self, key, value, epoch=-1):
        field = self.field(key)
        if epoch >= 0 and epoch != self._epoch:
            return False
        if field is None or not field.data['enabled'] or field.data['kind'] not in ('text', 'number', 'choice', 'check'):
            return False
        try:
            value = self._read(field.data, value)
            if self._kind == 'defaults':
                self._commit_default(key, value)
            elif self._many:
                self._commit_many(key, value)
            else:
                changes = self._changes(key, value)
                if changes is not None:
                    self._apply(changes)
        except (ValueError, KeyError, TypeError) as error:
            return self._refuse(str(error))
        self._error = ''
        self.changed.emit()
        return True

    def _changes(self, key, value):
        p, target = self.session.project, self._target()
        if key == 'name':
            return {'name': value or target.name}
        if self._kind == 'site':
            if key.startswith('network.'):
                return {'network': replace(p.network, **{key.split('.')[1]: value})}
            if key.startswith('rules.'):
                return {'rules': {**(p.rules or {}), key.split('.')[1]: value}}
            if key.startswith('consent.'):
                consent = dict(p.network_consent)
                service = key.split('.')[1]
                if value:
                    consent[service] = datetime.date.today().isoformat()
                else:
                    consent.pop(service, None)
                return {'network_consent': consent}
        if key.startswith('side.'):
            path = 'footprint' if self._kind == 'building' else 'ring'
            return {path: sides.stretch(getattr(target, path), int(key.split('.')[1]), value)}
        if self._kind == 'building':
            if key == 'roof.type':
                return target.retyped(value)
            if key == 'on':                     # R352: on a building, the base goes to its roof under this outline
                host = p.building(value) if value else None
                if host is None:
                    return {'on': '', 'base': 0.0}
                from meridiana.model import roof_z
                base = round(max(roof_z(host, target.footprint)), 3)
                if base >= target.wall_top() - 0.1:
                    raise ValueError(_('the roof of {name} stands above this body ({h} m)').format(name=host.name, h=number(base)))
                return {'on': host.id, 'base': base}
            if key == 'base':
                if value >= target.wall_top() - 0.1:
                    raise ValueError(_('the base must stand under the roof ({h} m)').format(h=number(target.wall_top())))
                return {'base': round(value, 3)}
            if key.startswith('saddles.'):
                return {'roof.saddles': {**roofs.saddle_spec(target.roof.saddles), key.split('.')[1]: float(value)}}
            if key == 'roof.covering':
                return {'roof.covering': value, 'roof.tilt': roofs.proposed_tilt(value),
                        **({'roof.ridge_height': None} if target.roof.ridge_height is not None else {})}
            if key in ('roof.tilt', 'roof.percent'):
                return target.slope_written(math.degrees(math.atan(value / 100)) if key.endswith('percent') else value)
            if key == 'height':
                return target.eave_written(value)
            if key == 'roof.keep_ridge':
                return {'roof.keep_eave': not value}
            if key == 'roof.ridge_height':
                if value <= target.height + .01:
                    raise ValueError(_('the ridge must stand above the eave ({h} m)').format(h=number(target.height)))
                return {key: round(value, 3)}
            if key == 'roof.eave_side':
                return {key: value - 1}
            if key.startswith('edge.'):
                return {'roof.edges': target.with_side(int(key.split('.')[1]), value)}
            if key.startswith('free.'):
                prefix, index, part = key.split('.')
                pitches = copy.deepcopy(target.roof.free_pitches)
                pitch = pitches[int(index)]
                if part == 'eave_side':
                    value -= 1
                elif part == 'percent':
                    part, value = 'tilt', math.degrees(math.atan(value / 100))
                elif part == 'ridge':
                    part, value = 'tilt', roofs.free_tilt(pitch['ring'], pitch['eave_side'], pitch['eave'], value)
                    pitch[part] = value         # the ridge written: the slope goes to it from the eave, whatever is kept
                    part = None
                elif part == 'eave_shown':
                    part = 'eave'
                if part in ('eave', 'tilt') and not target.roof.keep_eave:
                    kept = roofs.free_keeping_ridge(pitch['ring'], pitch['eave_side'], pitch['eave'], pitch['tilt'],
                                                    **{'new_eave' if part == 'eave' else 'new_tilt': value})
                    pitch['eave'], pitch['tilt'] = kept
                elif part is not None:
                    pitch[part] = value
                pitch.pop('z', None)
                return {'roof.free_pitches': pitches}
            if key == 'fire.activity':
                return {'fire.' + k: v for k, v in vvf.chosen(value, target.fire.category).items()
                        if getattr(target.fire, k) != v}
            if key == 'fire.subject' and not value:
                return {'fire.' + k: v for k, v in vvf.chosen(0).items() if getattr(target.fire, k) != v}
            if key == 'fire.category':
                return {k: v for k, v in {key: value, **({'fire.subject': True} if value else {})}.items()
                        if getattr(target.fire, k.split('.')[1]) != v}
        if self._kind == 'subfield':
            if key == 'automatic':
                return {'params.azimuth': None if value else self.field('params.azimuth').data['value']}
            if key.startswith('support.'):
                support = support_now(p, target)
                x, y = support_reference(p, target)
                values = {'x0': x, 'y0': y, 'z0': support.surface().z(x, y), key.split('.')[1]: value}
                return {'support': replace(support, **values)}
            if key.startswith('window.'):
                window = p.fill_params(target).window
                return {'params.window': {k: value if k == key.split('.')[1] else getattr(window, k)
                                          for k in ('day', 'month', 'start', 'end')}}
            if key == 'params.alignment' and target.removed and not target.manual:
                return {key: value, 'removed': manual.removed_on_alignment(
                    p, target, value, self.session.results.get(target.id))}
            if key == 'module' and target.manual and value != target.module:
                if manual.needs_asking(p, self._oid, value):
                    self._ask('module', value, _('A module of other sizes'),
                              _('The new module differs by more than 2 cm from the one the rows by hand were drawn with. '
                                'Adapt the rows (the same places and modules, the gaps kept), or lay the sub-field again automatically?'))
                else:
                    self.session.edit(_('Change {what}').format(what=field_label('module', 'subfield')),
                                      manual.change_module(p, self._oid, value))
                return None
        if self._kind == 'prop':
            if key == 'kind':
                return {'kind': value, 'asset': None, **({'height': None, 'width': None, 'length': None}
                                                        if props.family(value) != props.family(target.kind) else {})}
            if key == 'asset':
                from .models3d import ASSET_FOR_KIND
                return {'asset': None if value == ASSET_FOR_KIND.get(target.kind) else value}
            if key == 'rotation':
                return {key: value % 360.}
        return {key: value}

    def _commit_default(self, key, value):
        """A field of the defaults of the next sub-fields changed (R523): one undo step on the project's
        layout_defaults, only what differs from the program's kept; no sub-field moves."""
        from meridiana import layout
        from meridiana.quick.backend.properties_schema import defaults_values
        p = self.session.project
        defaults = copy.deepcopy(p.layout_defaults)
        params = dict(defaults.get('params') or {})
        base = layout.Params()
        if key == 'module':
            defaults['module'] = value
        elif key == 'fire_bands':
            defaults['fire_bands'] = value
        elif key == 'automatic':
            if value:
                params.pop('azimuth', None)
            else:
                params['azimuth'] = 0.
        elif key.startswith('window.'):
            _raw, shown = defaults_values(p)
            window = {k: getattr(shown.window, k) for k in ('day', 'month', 'start', 'end')}
            window[key.split('.')[1]] = value
            params['window'] = window
        elif key.startswith('params.'):
            name = key.split('.')[1]
            default = (layout.NEW_ALIGNMENT if name == 'alignment' else '' if name == 'mounting'
                       else getattr(base, name))
            if value == default:
                params.pop(name, None)
            else:
                params[name] = value
        else:
            raise KeyError(key)
        if params.get('window') == p.sun_window:
            params.pop('window')                # the project's window: nothing of their own
        defaults['params'] = params
        if not params:
            defaults.pop('params')
        if defaults.get('module') == 'generic-450':
            defaults.pop('module')
        if defaults.get('fire_bands') is not True:
            defaults.pop('fire_bands', None)

        def apply(project):
            project.layout_defaults = defaults
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        what = (_('fire-brigade bands') if key == 'fire_bands' else field_label(
            'params.window' if key.startswith('window.') else 'params.azimuth' if key == 'automatic' else key))
        self.session.edit(_('Change the defaults: {what}').format(what=what), apply,
                          ('field', 'defaults', '', key) if numeric else None)

    def _commit_many(self, key, value):
        """One change for all that is selected together (R439), computed for each and applied in one undo step: one
        that cannot take it refuses it for all."""
        p, keep, plans = self.session.project, self._oid, []
        try:
            for oid in self._many:
                self._oid = oid
                target = self._target()
                if key == 'module' and target.manual and value != target.module:
                    if manual.needs_asking(p, oid, value):
                        raise ValueError(_('{name} has rows by hand of another size: change its module on its own').format(
                            name=target.name))
                    plans.append(manual.change_module(p, oid, value))
                else:
                    plans.append((target, dict(sorted(self._changes(key, value).items()))))
        finally:
            self._oid = keep

        def apply(p):
            for plan in plans:
                if callable(plan):
                    plan(p)
                else:
                    self._write(p, *plan)
        paths = sorted({path for plan in plans if not callable(plan) for path in plan[1]}) or [key]
        numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
        self.session.edit(_('Change {what}').format(what=', '.join(field_label(k, self._kind) for k in paths)), apply,
                          ('field', self._kind, tuple(self._many), key) if numeric else None)

    def _write(self, p, target, changes):
        for path, value in changes.items():
            head, _sep, tail = path.partition('.')
            if not tail:
                setattr(target, head, value)
                if target is p and head == 'network':
                    p.sync_network()
            elif head == 'params':
                if tail == 'azimuth' and value is None:
                    target.params.pop('azimuth', None)
                else:
                    target.params[tail] = value
            else:
                setattr(getattr(target, head), tail, value)

    def _apply(self, changes):
        # The Widgets' Signal(..., dict) crosses QVariantMap, whose keys arrive
        # sorted. Keep the same field order in undo labels as that real handler.
        changes = dict(sorted(changes.items()))
        if changes.get('in_group') is False:        # taken out of its model: this body moves alone from now on
            changes = {'group': ''}
        kind, oid = ('project' if self._kind == 'site' else self._kind), self._oid
        target = self._target()

        def apply(p):
            self._write(p, target, changes)
        merge = None
        if len(changes) == 1:
            path, value = next(iter(changes.items()))
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                merge = ('field', kind, oid, path)
        self.session.edit(_('Change {what}').format(what=', '.join(field_label(k, kind) for k in changes)), apply, merge)

    def _ask(self, action, value, title, text):
        self._pending = (action, value, self._kind, self._oid, self.session.state_key())
        self._confirmation = dict(action=action, title=title, text=text)
        self.confirmationChanged.emit()

    @Slot(str, result=bool)
    def confirm(self, choice):
        pending, self._pending = self._pending, None
        self._confirmation = {}
        self.confirmationChanged.emit()
        if pending is None or choice == 'cancel':
            return False
        action, value, kind, oid, state = pending
        if (kind, oid) != (self._kind, self._oid) or state != self.session.state_key():
            return self._refuse(_('The project changed; review the operation again.'))
        if action == 'module' and choice in ('adapt', 'again'):
            self.session.edit(_('Change {what}').format(what=field_label('module', 'subfield')),
                              manual.change_module(self.session.project, oid, value, choice == 'adapt'))
        elif action == 'relayout' and choice == 'accept':
            self.session.edit(_('Lay again automatically'), manual.relayout(self.session.project, oid))
        else:
            return False
        return True

    @Slot(str)
    def trigger(self, action):
        field = self.field(action)
        if field is None or field.data['kind'] != 'action' or not field.data['enabled']:
            return
        if action == 'default_height':
            self._apply({'height': None})
        elif action == 'default_measures':
            self._apply({'height': None, 'width': None, 'length': None})
        elif action.startswith('free.') and action.endswith('.swap'):
            i = int(action.split('.')[1])
            f = self._target().roof.free_pitches[i]
            self._apply(self._changes(f'free.{i}.eave_side', roofs.opposite_side(f['ring'], f['eave_side']) + 1))
        elif action == 'flatten':              # R455: the inclined flat roof level again
            self._apply({'roof.plane': None})
        elif action == 'bodies_as_one':         # R440: the bodies of the imported model are this building
            target = self._target()
            ids = [x.id for x in self.session.project.buildings if x.group == target.group and x.id != target.id]

            def apply(p):
                for x in p.buildings:
                    if x.id in ids:
                        x.part_of = target.id
            self.session.edit(_('The bodies of the model are one building'), apply)
        elif action == 'sun_all':
            window = self.session.project.fill_params(self._target()).window
            values = {k: getattr(window, k) for k in ('day', 'month', 'start', 'end')}

            def apply(p):
                p.sun_window = values
                for sf in p.subfields:
                    sf.params.pop('window', None)
            self.session.edit(_('Use the sun window for all sub-fields'), apply)
        elif action in ('fill', 'empty'):
            def apply(p):
                sf = next(s for s in p.subfields if s.id == self._oid)
                sf.filled = action == 'fill'
                if sf.filled and not sf.manual:
                    sf.removed = []
            self.session.edit(_('Lay the modules') if action == 'fill' else _('Take the modules out'), apply)
        elif action == 'defaults_reset':
            self.session.edit(_("Defaults back to the program's"), lambda p: setattr(p, 'layout_defaults', {}))
        elif action == 'defaults_take':
            values = self.session.project.defaults_of(self._target())
            self.session.edit(_('Use as defaults'), lambda p: setattr(p, 'layout_defaults', values))
        elif action == 'defaults_apply':
            try:
                self.session.edit(_('Apply the defaults'), manual.apply_defaults(self.session.project, self._oid))
            except ValueError as error:
                self._refuse(str(error))
        elif action == 'relayout':
            self._ask(action, None, _('Lay again automatically'),
                      _('The rows by hand give way to the automatic layout, and the modules taken out by hand come back. '
                        'Undo brings them back. Go on?'))
        else:
            self.actionRequested.emit(action, self._kind, self._oid)

    @Slot(int)
    def highlightSide(self, side):
        self.actionRequested.emit('light_side:' + (str(side) if side >= 0 else ''), self._kind, self._oid)

    @Slot(str)
    def help(self, hid):
        if hid:
            self.helpRequested.emit(hid)

    @Slot()
    def undo(self):
        self.session.undo.undo()

    @Slot()
    def redo(self):
        self.session.undo.redo()


def install_properties(engine, backend, theme=None):
    from meridiana.quick.backend.controls import install_controls
    tokens = install_controls(engine, theme)
    engine.rootContext().setContextProperty('propertiesBackend', backend)
    engine._properties_backend = backend
    return tokens
