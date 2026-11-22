"""Immutable plant computations, with cancellation and queued GUI delivery."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QRunnable, Signal

from meridiana.app.session import project_from
from meridiana.core.energy import plant, sizing, stringing


class Signals(QObject):
    done = Signal(object, object)


class PlantJob(QRunnable):
    def __init__(self, kind, snapshot, results, key, layout_keys, **options):
        super().__init__()
        self.kind, self.snapshot, self.results = kind, snapshot, dict(results)
        self.key, self.layout_keys, self.options = key, dict(layout_keys), options
        self.cancelled = threading.Event()
        self.enough = threading.Event()     # R522 «Stop»: the search ends now with the best proposal found
        self.signals = Signals()

    def interrupt(self):
        self.cancelled.set()

    def run(self):
        try:
            project = project_from(self.snapshot)       # the session's photo (R598), made a project here
            if self.kind == 'makers':
                from meridiana.data import catalog
                records = list(catalog.load('inverters'))
                names = sorted({str(r.get('manufacturer', '')) for r in records})
                sizable = {str(r.get('manufacturer', '')) for r in records if not sizing.missing_fields(r)}
                result = [dict(label=n, sizable=n in sizable,
                               reason='' if n in sizable else '\n'.join(sizing.alternatives(n, records))) for n in names]
            elif self.kind in ('sizing', 'sizing_free'):
                candidates = self.options['candidates']
                if candidates is None:
                    from meridiana.data import catalog
                    maker = self.options['maker'].casefold()
                    candidates = [r for r in catalog.load('inverters')
                                  if str(r.get('manufacturer', '')).casefold() == maker
                                  and float(r.get('ac_power_nominal_w') or r.get('pac') or 0) > 0]
                if self.kind == 'sizing_free':
                    # R522: only the modules in no string, the designer's strings and inverters kept
                    result = sizing.choose_free(project, plant.groups_of(project, self.results), candidates,
                                                self.options['ratio'], self.options['keep'],
                                                cancelled=self.cancelled.is_set, enough=self.enough.is_set)
                else:
                    result = sizing.choose(project, plant.groups_of(project, self.results),
                                           candidates, self.options['ratio'],
                                           cancelled=self.cancelled.is_set)
            else:               # 'proposal' (the plant after a change is a job of the mechanism: app/plant_job.py)
                budget = stringing.SearchBudget(limit=100000, cancelled=self.cancelled.is_set)
                result = plant.proposal(project, self.results, search=budget,
                                        **{k: v for k, v in self.options.items() if k != 'maker'})
        except Exception as error:  # Worker boundary: the backend reports the error.
            result = error
        self.signals.done.emit(self, result)
