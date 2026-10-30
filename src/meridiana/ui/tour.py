"""A resumable non-modal tour using real navigation targets, without editing the project."""
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QSizePolicy

from .. import tour
from ..i18n import _
from . import navigation_targets, spotlight
from .guide_card import GuideCard


class TourDialog(GuideCard):
    def __init__(self, window, resume=False, invitation=False):
        super().__init__(_("Meridio: guided tour"), window, invitation=invitation)
        self.host = window
        self.assistant_was_open = window.assistant.opened
        self.finished_once = False
        avatar = window.assistant
        avatar.setProperty("guidedTourActive", True)
        self._show_meridio()
        avatar.set_docked(False)
        self.setParent(avatar.panel, Qt.WindowType.Widget)
        self.setMaximumWidth(16777215)
        self.description.setMinimumWidth(0)
        self.description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.layout().setContentsMargins(0, 4, 0, 4)
        self.progress.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        # both wrap: their height follows the bubble's width (height for width), the stretch below takes the rest
        self.layout().insertStretch(3, 1)
        avatar.panel.layout().insertWidget(1, self, 1)
        avatar.chat_content.hide()
        avatar.open_panel()
        avatar.openedChanged.connect(self._panel_changed)
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
        self.next.setText(_("Start") if self.index == len(self.items)-1 else _("Next"))
        self.skip.setText(_("Pause tour"))
        try:
            self._show_target(item.target)
        except (ValueError, AttributeError):
            self.description.setText(item.text + "\n\n" + _("This area is not available in the current workspace."))
        avatar = self.host.assistant
        if not avatar.docked:                   # docked by hand during the tour, the character stays away
            avatar.show()
            avatar.raise_()
            avatar.bubble.raise_()

    def _show_target(self, target):
        win = self.host
        if target[0] == "new":
            if win.file_page.isVisible():
                win.file_page.show_section("new")
            else:
                win.open_file_page("new")
            widget = win.file_page
        elif target[0] == "file":
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
            self._show_meridio()
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
            if self.host.file_page.isVisible():
                self.host.file_page.show_section("new")
            else:
                self.host.open_file_page("new")
            self.host.statusBar().showMessage(_("Now it is time to start designing. Choose the site for your new project."), 12000)
            self.accept()
            return
        else:
            self.index += 1
        self.present()

    def back(self):
        self.index = max(0, self.index-1)
        self.present()

    def _show_meridio(self):
        """Meridio shown for the tour; the setting stays the designer's, saved as it was if the window closes now."""
        enabled = self.host.cfg.assistant
        self.host._show_assistant(True)
        self.host.cfg.assistant = enabled

    def _panel_changed(self, opened):
        if not opened and not self.finished_once:
            self.reject()

    def _finished(self, _result):
        if self.finished_once:
            return
        self.finished_once = True
        avatar = self.host.assistant
        avatar.openedChanged.disconnect(self._panel_changed)
        avatar.setProperty("guidedTourActive", False)
        avatar.panel.layout().removeWidget(self)
        self.hide()
        avatar.chat_content.show()
        if not self.assistant_was_open:
            avatar.close_panel()                # closed before docking again: the panel never flashes open
        # the settings as they are now: the designer may have docked or switched Meridio during the tour
        avatar.set_docked(self.host.cfg.assistant_docked)
        self.host._show_assistant(self.host.cfg.assistant)
        if self.invitation:
            self.host.cfg.tour_status = "skipped"
        elif self.host.cfg.tour_status != "done":
            self.host.cfg.tour_status = "paused"
        self.host._save_config()
