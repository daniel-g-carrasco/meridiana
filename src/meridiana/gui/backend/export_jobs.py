"""The IFC4 and DXF exports as jobs on the global pool (File > Export): the layouts in hand (those missing laid in
the job), the strings proposed or the designer's, then the file. Moved here from the Widgets window (R542)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Signal

from meridiana.app import jobs
from meridiana.app.platform import log
from meridiana.app.session import project_from
from meridiana.core.energy import plant as plant_model

from . import tell


class IfcSignals(QObject):
    step = Signal(float, str)
    done = Signal(object)


class ExportIfcJob(QRunnable):
    """The project written as IFC4 (ifc_export.py) away from the window's thread: the layouts in hand (those missing laid
    here), the strings proposed or the designer's, then the file. Each step is told (the bar); `interrupt` (Cancel)
    stops it at the next one, and nothing is written."""

    def __init__(self, snapshot: dict, known: dict, path: Path, state: str = "", what: str = "all"):
        super().__init__()
        self.snapshot, self.known, self.path, self.state = snapshot, known, path, state
        self.what = what                    # "all", or "plant": the plant alone (R453)
        self.signals = IfcSignals()
        self.interrupted = False

    def interrupt(self) -> None:
        self.interrupted = True

    def _step(self, fraction: float, what: str) -> None:
        from meridiana.app.exchange import ifc_export
        if self.interrupted:
            raise ifc_export.Interrupted()
        tell(self.signals.step, fraction, what)

    def run(self):
        from meridiana.app.exchange import ifc_export
        try:
            p = project_from(self.snapshot)
            results, _keys, _laid = jobs.layout_of(p, self.known)
            plant = None
            try:
                plant = plant_model.build(p, results, check=False)
                strings = {(sf, key): s.label for s in plant.strings for sf, key, _c in s.modules}
            except Exception as error:      # noqa: BLE001  the strings are a property: the model goes without them
                log.complain("ifc strings", error)
                strings = {}
            if self.what == "original":     # r22-ifc: the plant added to the architect's own file
                from meridiana.app.exchange import ifc_append
                out = ifc_append.append(p, results, ifc_append.original_of(p), self.path, strings, plant, self._step)
            else:
                out = ifc_export.export(p, results, self.path, strings=strings, progress=self._step, what=self.what,
                                        plant=plant)
        except ifc_export.Interrupted:
            out = None
        except Exception as error:          # noqa: BLE001  a thread's boundary: said, not lost
            if not isinstance(error, OSError):
                log.complain("ifc export", error)
            out = error
        tell(self.signals.done, out)


class ExportDxfJob(QRunnable):
    """The plan written as a DXF (dxf_export.py, R513) away from the window's thread: the layouts in hand (those missing
    laid here), the strings proposed or the designer's, then the file, in the coordinates `frame` with the `parts`
    asked. The steps are told as the IFC's (the same bar); `interrupt` stops it at the next one, and nothing is
    written."""

    def __init__(self, snapshot: dict, known: dict, path: Path, state: str = "", frame: str = "local",
                 parts: tuple = ()):
        super().__init__()
        self.snapshot, self.known, self.path, self.state = snapshot, known, path, state
        self.frame, self.parts = frame, tuple(parts)
        self.signals = IfcSignals()
        self.interrupted = False

    def interrupt(self) -> None:
        self.interrupted = True

    def _step(self, fraction: float, what: str) -> None:
        from meridiana.app.exchange import dxf_export
        if self.interrupted:
            raise dxf_export.Interrupted()
        tell(self.signals.step, fraction, what)

    def run(self):
        from meridiana.app.exchange import dxf_export
        try:
            out = dxf_export.export_project(project_from(self.snapshot), self.path,
                                            self.known, self.frame, self.parts or dxf_export.PARTS, self._step)
        except dxf_export.Interrupted:
            out = None
        except Exception as error:          # noqa: BLE001  a thread's boundary: said, not lost
            if not isinstance(error, (OSError, ValueError)):
                log.complain("dxf export", error)
            out = error
        tell(self.signals.done, out)
