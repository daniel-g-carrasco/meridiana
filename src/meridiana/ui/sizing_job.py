"""Cancellable inverter search on an immutable project snapshot, outside the GUI thread."""
from PySide6.QtCore import QObject, QRunnable, Signal

from . import tell


class Signals(QObject):
    done = Signal(object)


class SizingJob(QRunnable):
    def __init__(self, snapshot, results, candidates, ratio, maker, state):
        super().__init__()
        self.snapshot, self.results, self.candidates = snapshot, results, candidates
        self.ratio, self.maker, self.state = ratio, maker, state
        self.interrupted = False
        self.signals = Signals()

    def interrupt(self):
        self.interrupted = True

    def run(self):
        from .. import model
        from ..energy import plant, sizing
        try:
            project = model.Project.from_json(self.snapshot, check=False)
            result = sizing.choose(project, plant.groups_of(project, self.results), self.candidates,
                                   self.ratio, cancelled=lambda: self.interrupted)
        except Exception as error:
            result = error
        tell(self.signals.done, (self, result))


class StringProposalJob(QRunnable):
    def __init__(self, snapshot, results, strategy, keep, t_cell_max, state, layout_keys):
        super().__init__()
        self.snapshot, self.results, self.strategy = snapshot, results, strategy
        self.keep, self.t_cell_max, self.state = keep, t_cell_max, state
        self.layout_keys = dict(layout_keys)
        self.interrupted = False
        self.signals = Signals()

    def interrupt(self):
        self.interrupted = True

    def run(self):
        from .. import model
        from ..energy import plant, stringing
        try:
            project = model.Project.from_json(self.snapshot, check=False)
            budget = stringing.SearchBudget(limit=100000, cancelled=lambda: self.interrupted)
            result = plant.proposal(project, self.results, strategy=self.strategy, keep=self.keep,
                                    t_cell_max_year=self.t_cell_max, search=budget)
        except Exception as error:
            result = error
        tell(self.signals.done, (self, result))
