"""Persistent result editors on the shared session; no work on continuous gestures."""
from __future__ import annotations

import copy
import math
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QRunnable, QThreadPool

from meridiana.core.energy import consumption as cons
from meridiana.core.rules import registry
from meridiana.app.platform import log
from meridiana.i18n import _
from meridiana.app.session import set_path
from meridiana.core.energy.simulate import Losses
from .properties import PropertiesBackend, PropertyField
from . import charts_schema
from meridiana.gui.backend.profiles import registry as profiles

# the topics the result pages' fields follow (the production's also the layouts, `layout:<id>`)
PRODUCTION = frozenset({'file', 'restored', 'project:variants', 'project:regulatory_profile', 'project:site',
                        'project:consumption', 'project:economics', 'project:energy', 'energy', 'project:subfields'})


class CurveSignals(QObject):
    done = Signal(object, object, str)


class CurveJob(QRunnable):
    def __init__(self, path, unit, epoch):
        super().__init__()
        self.path, self.unit, self.epoch = path, unit, epoch
        self.signals = CurveSignals()

    def run(self):
        rows, error = None, ''
        try:
            rows = cons.read_curve(self.path, self.unit)
        except (ValueError, OSError) as exc:
            error = str(exc)
        except Exception as exc:  # Worker boundary: report unexpected parser failures as well.
            log.complain('load curve import', exc)
            error = f'{type(exc).__name__}: {exc}'
        self.signals.done.emit(self, rows, error)


class ResultEditor(QObject):
    sectionsChanged = Signal()
    epochChanged = Signal()
    changed = Signal()
    actionRequested = Signal(str)
    importRequested = Signal()
    shownChanged = Signal()

    def __init__(self, session, phase, parent=None):
        super().__init__(parent)
        self.session, self.phase = session, phase
        self._sections, self._fields, self._shape = [], {}, ()
        # R598: the fields are made again only while the inspector is on show (its page says so, `shown`); a change
        # that comes meanwhile leaves them to be made when it is shown next. Nobody said (no page: a test, a pilot):
        # made at every change, as before. 40 sub-fields filled at once held the window 7-11 s off screen for the
        # Production inspector's form, behind another phase (docs/quick/stato/r35-albero.md).
        self._watched, self._shown, self._stale = False, True, False
        self._error, self._epoch, self._mode, self._curve_unit = '', 0, '', 'kWh'
        self._identity = registry.identity(session.project)
        self._closed = False
        self._imports = set()
        self._import = None
        self._import_pending = False
        self._bills_cache = None
        self._made_of = None            # _inputs() of the fields made last (the consumption's, the economics')
        session.subscribe(self._on_change)
        self._infer_mode()
        self.refresh()

    sections = Property('QVariantList', lambda self: self._sections, notify=sectionsChanged)
    epoch = Property(int, lambda self: self._epoch, notify=epochChanged)
    error = Property(str, lambda self: self._error, notify=changed)
    mode = Property(str, lambda self: self._mode, notify=changed)
    phaseId = Property(str, lambda self: self.phase, constant=True)

    def _meteo(self):
        """The weather in two short lines and the two boxes of the shadows, as in the bar of the Widgets (R313)."""
        energy = self.session.energy or {}
        text = energy.get('meteo_text') or _('Not fetched yet.')
        first, second = energy.get('meteo_brief') or (text, '')
        losses = Losses.from_dict((self.session.project.energy or {}).get('losses'))
        return dict(text=text, first=first, second=second, horizon=losses.use_horizon, near=losses.use_near,
                    horizonLabel=_('Shading of the far horizon'), nearLabel=_('Shading of the obstacles of the scene'),
                    nearTip=_('Exclusions with a height, parapets and the other buildings cast their shadows on the modules'))
    meteo = Property('QVariantMap', _meteo, notify=changed)
    status = Property(str, lambda self: '\n'.join(self.session.energy['sim'].notes)
                      if self.phase == 'production' and self.session.energy.get('sim') else '', notify=changed)
    importPending = Property(bool, lambda self: self._import_pending, notify=changed)
    busy = Property(bool, lambda self: self._import is not None, notify=changed)
    ready = Property(bool, lambda self: not self._stale, notify=changed)
    curveUnit = Property(str, lambda self: self._curve_unit, notify=changed)
    labels = Property('QVariantMap', lambda self: dict(search=_('Search'), total=_('Total'), compute=_('Compute'),
                      importTitle=_('Import a load curve'), cancel=_('Cancel')), constant=True)

    def _bill_data(self):
        # One policy read and one pass over the twelve rows per publication.
        # QML reads the columns, rows and totals independently on changed.
        if self._bills_cache is None:
            project = self.session.project
            policy = profiles.get(project.regulatory_profile)
            columns = list(policy.bill_columns(project))
            source = project.consumption.get('monthly_bands_kwh') or []
            rows = [policy.bill_row(dict(source[i])) if i < len(source) else {code: 0 for code in columns}
                    for i in range(12)]
            totals = {code: sum(row.get(code, 0) for row in rows) for code in columns}
            self._bills_cache = columns, rows, totals
        return self._bills_cache

    billColumns = Property('QStringList', lambda self: self._bill_data()[0], notify=changed)
    bills = Property('QVariantList', lambda self: self._bill_data()[1], notify=changed)
    billTotals = Property('QVariantMap', lambda self: self._bill_data()[2], notify=changed)

    def _set_shown(self, shown):
        shown = bool(shown)
        self._watched = True
        if shown == self._shown:
            return
        self._shown = shown
        self.shownChanged.emit()
        if shown and self._stale and not self._closed:
            # Reuse the window's common after-frame and pieces contract. The phase
            # first draws its wait; an obsolete callback never publishes old fields.
            def prepare():
                if not self._closed and self._shown and self._stale:
                    self.refresh()

            def after_frame():
                if self.session.pieces is not None:
                    self.session.pieces('phase.inspector.' + self.phase, prepare)
                else:
                    prepare()
            if self.session.later is not None:
                self.session.later(after_frame)
            else:
                prepare()

    shown = Property(bool, lambda self: self._shown, _set_shown, notify=shownChanged)

    def field(self, key):
        if self._stale and not self._closed:        # asked from Python while the page is behind another: made now
            self.refresh()
        return self._fields.get(key)

    def _made_again(self):
        """The fields made again for a change: now while the inspector is on show (or nobody watches), when it is
        shown next otherwise; what is read live (the weather's lines, the notes, the bills) is told at once."""
        if self._watched and not self._shown:
            self._stale = True
            self.changed.emit()
            return
        self.refresh()

    def _infer_mode(self):
        c = self.session.project.consumption
        self._mode = ('measured' if c.get('measured') else 'bills' if c.get('monthly_bands_kwh') else
                      'bands' if any((c.get('bands_kwh') or {}).values()) else 'annual')

    def _on_change(self, topics):
        if self._closed:
            return
        identity = registry.identity(self.session.project)
        context_changed = identity != self._identity
        if context_changed or topics & {'file', 'restored', 'project:variants', 'project:consumption',
                                        'project:regulatory_profile'}:
            self._bills_cache = None
        self._identity = identity
        if context_changed or topics & {'file', 'restored', 'project:variants'}:
            self._epoch += 1
            self._infer_mode()
            self.epochChanged.emit()
        whole = context_changed or topics & {'file', 'project:variants'}
        if self.phase == 'production':
            if topics & PRODUCTION or any(t.startswith('layout:') for t in topics):
                self._made_again()
        elif topics & PRODUCTION:
            # what the consumption's and the economics' fields are made of (profiles/*/charts.py): neither shows the
            # sub-fields nor the modules laid, and «project:energy» also says the strings realigned on a layout, so
            # they are made again only when what they show differs (r35: 6 calls of the editors in one Canc, 4 of them
            # of these two pages, for nothing they show)
            inputs = self._inputs()
            if whole or inputs != self._made_of:
                self._made_again()

    def _inputs(self):
        """What the fields of the consumption's or the economics' page are made of, by value (a copy kept when they
        are made: comparing costs no copy when nothing changed)."""
        p = self.session.project
        if self.phase == 'consumption':
            return (p.consumption, (self.session.energy or {}).get('context'), p.regulatory_profile, self._mode,
                    self._curve_unit)
        return p.economics, p.regulatory_profile

    def refresh(self):
        self._bills_cache = None
        self._stale = False
        if self.phase != 'production':
            settings, *rest = self._inputs()         # the year's context is read-only once published
            self._made_of = (copy.deepcopy(settings), *rest)
        schema = charts_schema.build(self)
        shape = tuple((s['key'], tuple(f['id'] for f in s['fields'])) for s in schema)
        if shape == self._shape:
            for section in schema:
                for field in section['fields']:
                    self._fields[field['id']].update(field)
        else:
            previous = self._fields
            self._fields, self._sections = {}, []
            for section in schema:
                fields = [previous.get(data['id']) or PropertyField(data, self) for data in section['fields']]
                for field, data in zip(fields, section['fields'], strict=True):
                    field.update(data)
                    self._fields[data['id']] = field
                self._sections.append({**section, 'fields': fields})
            self._shape = shape
            self.sectionsChanged.emit()
            for key, field in previous.items():
                if key not in self._fields:
                    field.deleteLater()
        self.changed.emit()

    def _refuse(self, error):
        self._error = _('Not changed: {why}').format(why=error)
        self.changed.emit()
        return False

    @Slot(str, 'QVariant', int, result=bool)
    def commit(self, key, value, epoch):
        field = self.field(key)
        if epoch != self._epoch or field is None or not field.data['enabled']:
            return False
        if field.data['kind'] not in ('number', 'text', 'check', 'choice'):
            return False
        try:
            value = PropertiesBackend._read(self, field.data, value)
            if key == 'mode':
                self._mode = value
                def mode(p):
                    c = p.consumption
                    if value != 'measured':
                        c['measured'] = []
                    if value in ('annual', 'bands'):
                        c['monthly_bands_kwh'] = []
                    if value == 'annual':
                        c['bands_kwh'] = {}
                    if value == 'bills' and not c.get('monthly_bands_kwh'):
                        load = self.session.energy.get('load')
                        c['monthly_bands_kwh'] = ([{b: round(v) for b, v in r.items()} for r in load.monthly_by_band()]
                                                  if load else self.bills)
                self.session.edit(_('Change consumption'), mode)
            elif key == 'curve_unit':
                self._curve_unit = value
            else:
                section = 'energy' if self.phase == 'production' else self.phase
                if key == 'pod':
                    value = value.upper().replace(' ', '')
                if key == 'strings.per_mppt':
                    value = [int(v) for v in value.replace(',', ';').split(';') if v.strip()]
                    if any(v < 0 for v in value):
                        raise ValueError(_('Whole numbers separated by ; are expected, one per input: 2; 2; 1'))
                if key == 'lid_auto':
                    key, value = 'losses.lid', None if value else 1.
                self.session.edit(_('Change energy settings'), lambda p: set_path(getattr(p, section), key, value))
        except (TypeError, ValueError, KeyError) as error:
            return self._refuse(str(error))
        self._error = ''
        self.refresh()
        return True

    @Slot(int, str, float, result=bool)
    def setBill(self, month, band, value):
        if not 0 <= month < 12 or band not in self.billColumns or not math.isfinite(value) or not 0 <= value <= 1e9:
            return False
        rows = copy.deepcopy(self.bills)
        rows[month][band] = value
        self.session.edit(_('Change consumption'), lambda p: p.consumption.update(monthly_bands_kwh=rows))
        return True

    @Slot(QUrl, result=bool)
    def importCurve(self, url):
        if self._closed or not url.isLocalFile():
            return False
        job = CurveJob(Path(url.toLocalFile()), self._curve_unit, self._epoch)
        self._import = job
        self._imports.add(job)
        job.signals.done.connect(self._curve_done)
        QThreadPool.globalInstance().start(job)
        self.changed.emit()
        return True

    @Slot(object, object, str)
    def _curve_done(self, job, rows, error):
        self._imports.discard(job)
        if self._closed or self._import is not job:
            return
        self._import = None
        if job.epoch != self._epoch:
            self.changed.emit()
            return
        if error:
            self._refuse(error)
            return
        self._mode = 'measured'
        self.session.edit(_('Import a load curve'), lambda p: p.consumption.update(measured=rows))
        self._error = ''
        self.refresh()

    @Slot()
    def openImport(self):
        self._import_pending = True
        self.changed.emit()
        self.importRequested.emit()

    @Slot()
    def dismissImport(self):
        self._import_pending = False
        self.changed.emit()

    @Slot(str)
    def trigger(self, action):
        if action == 'remove_battery':
            self.session.edit(_('No battery'), lambda p: p.economics.update(battery=None))
        elif action == 'import_consumption':
            self.openImport()
        else:
            self.actionRequested.emit(action)

    @Slot()
    def close(self):
        self._closed = True
        if self._on_change in self.session.listeners:
            self.session.listeners.remove(self._on_change)
