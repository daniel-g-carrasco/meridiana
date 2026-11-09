"""Persistent result editors on the shared session; no work on continuous gestures."""
from __future__ import annotations

import copy
import math
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QRunnable, QThreadPool

from meridiana.energy import consumption as cons
from meridiana import log
from meridiana.i18n import _
from meridiana.session import set_path
from meridiana.energy.simulate import Losses
from .properties import PropertiesBackend, PropertyField
from . import charts_schema


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
    helpRequested = Signal(str)
    importRequested = Signal()

    def __init__(self, session, phase, parent=None):
        super().__init__(parent)
        self.session, self.phase = session, phase
        self._sections, self._fields, self._shape = [], {}, ()
        self._error, self._epoch, self._mode, self._curve_unit = '', 0, '', 'kWh'
        self._closed = False
        self._imports = set()
        self._import = None
        self._import_pending = False
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
    curveUnit = Property(str, lambda self: self._curve_unit, notify=changed)
    labels = Property('QVariantMap', lambda self: dict(search=_('Search'), total=_('Total'), compute=_('Compute'),
                      importTitle=_('Import a load curve'), cancel=_('Cancel')), constant=True)

    @Property('QVariantList', notify=changed)
    def bills(self):
        rows = self.session.project.consumption.get('monthly_bands_kwh') or []
        return [dict(rows[i]) if i < len(rows) else dict(F1=0, F2=0, F3=0) for i in range(12)]

    @Property('QVariantMap', notify=changed)
    def billTotals(self):
        return {b: sum(r.get(b, 0) for r in self.bills) for b in ('F1', 'F2', 'F3')}

    def field(self, key):
        return self._fields.get(key)

    def _infer_mode(self):
        c = self.session.project.consumption
        self._mode = ('measured' if c.get('measured') else 'bills' if c.get('monthly_bands_kwh') else
                      'bands' if any((c.get('bands_kwh') or {}).values()) else 'annual')

    def _on_change(self, topics):
        if self._closed:
            return
        if topics & {'file', 'restored', 'project:variants'}:
            self._epoch += 1
            self._infer_mode()
            self.epochChanged.emit()
        if topics & {'file', 'restored', 'project:variants', 'project:energy', 'energy', 'project:subfields'} or any(
            t.startswith('layout:') for t in topics
        ):
            self.refresh()

    def refresh(self):
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
        if not 0 <= month < 12 or band not in ('F1', 'F2', 'F3') or not math.isfinite(value) or not 0 <= value <= 1e9:
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

    @Slot(str)
    def help(self, topic):
        self.helpRequested.emit(topic)

    @Slot()
    def close(self):
        self._closed = True
        if self._on_change in self.session.listeners:
            self.session.listeners.remove(self._on_change)
