"""A resumable non-modal tour using real navigation targets, without editing the project."""
from PySide6.QtCore import QTimer

from .. import tour
from ..i18n import _
from . import navigation_targets, spotlight
from .guide_card import GuideCard


class TourDialog(GuideCard):
    def __init__(self, window, resume=False, invitation=False):
        super().__init__(_("Meridio: guided tour"), window, invitation=invitation)
        self.host = window
        self.assistant_was_enabled = window.cfg.assistant
        self.items = tour.steps()
        self.index = max(0, min(window.cfg.tour_step, len(self.items)-1)) if resume else 0
        self.invitation = invitation
        self.setObjectName("guided-tour")
        self.previous.clicked.connect(self.back)
        self.next.clicked.connect(self.advance)
        self.skip.clicked.connect(self.reject)
        self.finished.connect(self._finished)
        if invitation:
            self.progress.setText(_("Welcome"))
            self.heading.setText(_("Let Meridio show you around"))
            self.description.setText(_("A short tour introduces the phases, tools and settings. You can stop at any time and resume from Help or by asking Meridio. Your project stays unchanged."))
            self.previous.hide()
            self.next.setText(_("Start tour"))
        else:
            self.present()

    def present(self):
        item = self.items[self.index]
        self.host.cfg.tour_status = "active"
        self.host.cfg.tour_step = self.index
        self.host._save_config()
        self.progress.setText(_("Step {current} of {total}").format(current=self.index+1, total=len(self.items)))
        self.heading.setText(item.title)
        self.description.setText(item.text)
        self.previous.show()
        self.previous.setEnabled(self.index > 0)
        self.next.setText(_("Finish") if self.index == len(self.items)-1 else _("Next"))
        self.skip.setText(_("Pause tour"))
        try:
            self._show_target(item.target)
        except (ValueError, AttributeError):
            self.description.setText(item.text + "\n\n" + _("This area is not available in the current workspace."))

    def _show_target(self, target):
        win = self.host
        if target[0] == "file":
            win.file_page.close_page()
            win.open_file_page("open")
            widget = win.file_page
        elif target[0] == "views":
            navigation_targets.show(win, ("phase", "model"))
            widget = win.plan.viewbar
        elif target[0] == "checks":
            win.file_page.close_page()
            win.checks_dock.show()
            win.checks_dock.raise_()
            widget = win.checks_page
        elif target[0] == "assistant":
            win.file_page.close_page()
            win._show_assistant(True)
            win.assistant.open_panel()
            widget = win.assistant
        else:
            navigation_targets.show(win, target)
            return
        QTimer.singleShot(250, widget, lambda: spotlight.reveal(widget) if widget.isVisible() else None)

    def advance(self):
        if self.invitation:
            self.invitation = False
        elif self.index == len(self.items)-1:
            self.host.cfg.tour_status = "done"
            self.host._save_config()
            self.accept()
            return
        else:
            self.index += 1
        self.present()

    def back(self):
        self.index = max(0, self.index-1)
        self.present()

    def _finished(self, _result):
        self.host._show_assistant(self.assistant_was_enabled)
        if self.invitation:
            self.host.cfg.tour_status = "skipped"
        elif self.host.cfg.tour_status != "done":
            self.host.cfg.tour_status = "paused"
        self.host._save_config()
