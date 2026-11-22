"""The report's attachments read off the window's thread (the Quick report page, report.py): their pages counted, or
the reason one cannot be read, from the session's photo made a project in the job (R598: no copy of the project on the
window's thread)."""
from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal

from meridiana.app.platform import log
from meridiana.app.report import reports
from meridiana.app.session import project_from


class AttachmentSignals(QObject):
    done = Signal(int, object)


class AttachmentRead(QRunnable):
    def __init__(self, generation, photo, signals):
        super().__init__()
        self.generation, self.photo, self.signals = generation, photo, signals

    def run(self):
        from meridiana.gui.paper.report import attachments
        project = None
        try:
            project = project_from(self.photo)
            rows = [vars(a) for a in attachments(project)]
        except Exception as error:  # the page displays the reason, including unexpected PDF failures
            if project is None:     # the photo did not make a project (never seen): said in the log
                log.complain("report attachments", error)
            rows = [{**a, "pages": 0, "problem": str(error)}
                    for a in reports.settings(project)["attachments"]] if project is not None else []
        self.signals.done.emit(self.generation, rows)
