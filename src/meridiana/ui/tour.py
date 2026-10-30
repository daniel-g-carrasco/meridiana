"""A resumable non-modal tour using real navigation targets, without editing the project.

Meridio conducts it in his bubble (R264). At every step he and the bubble keep off what the step points at (the
spotlight) and, when they can, off the content around it: the nearest free place among his corners and sides,
reached with his own slide (R293). His words are laid out as a short title, a paragraph, two or three points and
the key to try, with «step n of m» above (R293)."""
from PySide6.QtCore import QPoint, QRect, QSize, QTimer, Qt
from PySide6.QtWidgets import QSizePolicy

from .. import assistant as core, tour
from ..i18n import _
from . import navigation_targets, spotlight
from .design import Space, Text, Type, set_text
from .guide_card import GuideCard

TOUR_BUBBLE = (340, 560)        # the bubble while the tour runs: room for a whole step (the designer's size after)
CLEAR_MARGIN = Space.M          # between him or the bubble and what the step points at
CLEAR_POLL_MS = 60              # how often he looks for the spotlight of the step
CLEAR_POLLS = 20                # and for how long (a spotlight may follow another, the views' after the phase's)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def step_html(item: tour.Step, muted: str, extra: str = "") -> str:
    """The body of a step: the text, its points as a list, the key to try in the semibold weight."""
    parts = [f"<p>{_escape(item.text)}</p>"]
    if item.points:
        rows = "".join(f"<li>{_escape(point)}</li>" for point in item.points)
        parts.append(f'<ul style="margin-left: 0px; -qt-list-indent: 1;">{rows}</ul>')
    if item.hint:
        parts.append(f'<p><span style="color: {muted};">{_escape(_("Try:"))}</span> '
                     f'<span style="font-weight: {Type.SEMIBOLD};">{_escape(item.hint)}</span></p>')
    if extra:
        parts.append(f'<p><span style="color: {muted};">{_escape(extra)}</span></p>')
    return "".join(parts)


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
        self.description.setTextFormat(Qt.TextFormat.RichText)
        self.description.setOpenExternalLinks(False)
        set_text(self.heading, Text.TITLE)
        set_text(self.progress, Text.CAPTION)
        self.progress.setStyleSheet(f"color: {avatar.colours['muted']};")
        self.layout().setContentsMargins(0, 4, 0, 4)
        self.layout().setSpacing(Space.S)
        self.progress.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        # both wrap: their height follows the bubble's width (height for width), the stretch below takes the rest
        self.layout().insertStretch(3, 1)
        avatar.panel.layout().insertWidget(1, self, 1)
        avatar.chat_content.hide()
        # the bubble sized for a whole step, the designer's size put back at the end
        self.saved_dims = avatar.bubble_dims
        avatar.set_bubble_size(*TOUR_BUBBLE)
        # the bubble keeps off what the step points at, as it keeps off the selection (R33)
        self.keep_off: list[tuple[int, int, int, int]] = []
        self.window_avoid = avatar.avoid
        avatar.avoid = lambda: list(self.window_avoid()) + self.keep_off
        self.moved_tabs: dict[str, core.Anchor | None] = {}    # tab -> his anchor before the tour moved him
        self.set_anchors: dict[str, core.Anchor] = {}          # tab -> the anchor the tour gave him
        self.cleared_for = None                                 # the spotlight he last kept off
        self.clear_polls = 0
        self.clear_timer = QTimer(self, interval=CLEAR_POLL_MS)
        self.clear_timer.timeout.connect(self._keep_clear)
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
            self.description.setText(step_html(tour.Step(
                "welcome", "", _("I am Meridio, the small sun of this program. In thirteen short stops I show you "
                                 "the phases, the tools and the settings, and what each one is for. Stop whenever "
                                 "you like and pick up again from Help, or by asking me. Your project stays as it "
                                 "is."), (),
                (_("About three minutes, at your pace."), _("Previous and Next move between the stops."),
                 _("Pause tour keeps your place for next time."))), avatar.colours["muted"]))
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
        muted = self.host.assistant.colours["muted"]
        self.description.setText(step_html(item, muted))
        self.previous.show()
        self.previous.setEnabled(self.index > 0)
        self.next.setText(_("Start") if self.index == len(self.items)-1 else _("Next"))
        self.skip.setText(_("Pause tour"))
        self.keep_off = []
        self.cleared_for = None
        try:
            self._show_target(item.target)
        except (ValueError, AttributeError):
            self.description.setText(step_html(item, muted, _("This area is not available in the current workspace.")))
        avatar = self.host.assistant
        if not avatar.docked:                   # docked by hand during the tour, the character stays away
            avatar.show()
            avatar.raise_()
            avatar.bubble.raise_()
        self.clear_polls = 0
        self.clear_timer.start()

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

    # off what the step points at (R293)

    def _keep_clear(self):
        """The spotlight of the step found: he and the bubble move off it, to the nearest free place."""
        self.clear_polls += 1
        if self.clear_polls > CLEAR_POLLS or self.finished_once:
            self.clear_timer.stop()
            return
        avatar = self.host.assistant
        lights = [s for s in self.host.findChildren(spotlight.Spotlight) if s.isVisible()]
        if not lights or lights[0] is self.cleared_for:
            return
        light = lights[0]
        self.cleared_for = light
        if avatar.docked or self.items[self.index].target[0] == "assistant":
            return                              # pointing at himself, or no character to move
        keep = light.geometry()                 # the spotlight's parent is the window, as his area
        if light.parentWidget() is not avatar.area:
            keep = QRect(light.mapTo(avatar.area, QPoint(0, 0)), light.size())
        keep = keep.adjusted(-CLEAR_MARGIN, -CLEAR_MARGIN, CLEAR_MARGIN, CLEAR_MARGIN)
        self.keep_off = [(keep.x(), keep.y(), keep.width(), keep.height())]
        goal = self.clear_place(keep)
        if goal is None:
            if avatar.opened:
                avatar.place_bubble()           # at least the bubble keeps off it, when it can
            return
        top, w, h = avatar.free()
        anchor = core.anchor_of((goal.x(), goal.y() - top), avatar.size_now(), (w, h))
        if avatar.tab not in self.moved_tabs:
            self.moved_tabs[avatar.tab] = avatar.places.get(avatar.tab)
        self.set_anchors[avatar.tab] = anchor
        avatar.places[avatar.tab] = anchor
        avatar.reposition(animate=True)         # his own slide (SLIDE_MS, R155), at once with less motion

    def clear_place(self, keep: QRect) -> QPoint | None:
        """Where he stands so that neither he nor his bubble covers `keep` (area coordinates): where he is when
        that is already so, else the nearest of his corners and sides that is; None when none is."""
        avatar = self.host.assistant
        top, w, h = avatar.free()
        size = QSize(*avatar.size_now())
        m = core.MARGIN

        def clear(pos: QPoint) -> bool:
            if QRect(pos, size).intersects(keep):
                return False
            shape = avatar.bubble_shape(pos)
            if shape is None:
                return False
            return not QRect(shape.x, shape.y + top, shape.width, shape.height).intersects(keep)

        now = avatar.pos()
        if clear(now):
            return None
        middle = top + (h - size.height()) // 2
        candidates = [QPoint(m, top + m), QPoint(w - size.width() - m, top + m),
                      QPoint(m, top + h - size.height() - m), QPoint(w - size.width() - m, top + h - size.height() - m),
                      QPoint(m, middle), QPoint(w - size.width() - m, middle)]
        good = [avatar.off_band(c) for c in candidates if clear(avatar.off_band(c))]
        if not good:
            return None
        return min(good, key=lambda c: (c - now).manhattanLength())

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
        self.clear_timer.stop()
        avatar = self.host.assistant
        avatar.openedChanged.disconnect(self._panel_changed)
        avatar.setProperty("guidedTourActive", False)
        avatar.panel.layout().removeWidget(self)
        self.hide()
        avatar.chat_content.show()
        if not self.assistant_was_open:
            avatar.close_panel()                # closed before docking again: the panel never flashes open
        # what the tour changed of him, put back: the bubble's size, what it keeps off, and his places in the
        # phases where the tour moved him (unless the designer dragged him there since)
        avatar.avoid = self.window_avoid
        avatar.set_bubble_size(*self.saved_dims)
        for tab, before in self.moved_tabs.items():
            if avatar.places.get(tab) == self.set_anchors.get(tab):
                if before is None:
                    avatar.places.pop(tab, None)
                else:
                    avatar.places[tab] = before
        # the settings as they are now: the designer may have docked or switched Meridio during the tour
        avatar.set_docked(self.host.cfg.assistant_docked)
        self.host._show_assistant(self.host.cfg.assistant)
        if not avatar.docked:
            avatar.reposition(animate=True)
        if self.invitation:
            self.host.cfg.tour_status = "skipped"
        elif self.host.cfg.tour_status != "done":
            self.host.cfg.tour_status = "paused"
        self.host._save_config()
