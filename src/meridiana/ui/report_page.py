"""The Report phase (R61, docs/compiti/19r-relazione.md): in the middle the commands of the phase and the preview of
the pages as they will come out; on the right, above the deliverables, what the designer chooses for the report
(`ReportSide`): the template, the author's profile, the client and the revision, whether the site's address is
written, whether the register of the calculations goes beside the PDF, the chapters of the template, each with its
box, greyed with the reason when its data are not there, and the attachments (PDF files after the last chapter:
their names, their pages or why they are left out, their order).

The preview is made by the window a step at a time (report.preview_steps), as the PDF: the pages shown stay until
the new ones are ready, with how far it is above them."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLayout, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

from .. import reports, shortcuts
from ..i18n import _, ngettext
from . import icons
from .design import Icon, Space, Text, set_text

PAGE_WIDTH_MAX = 820          # logical pixels: a page of the preview no wider than this
PREVIEW_RESIZE_MS = 80


def _note(text: str) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("muted")
    return label


class Flow(QLayout):
    """Widgets in a row that goes on the next line when the room ends: the commands of the phase in a narrow window
    (a column of niri) instead of a minimum width that keeps the window from narrowing."""

    def __init__(self, parent=None, spacing: int = Space.M):
        super().__init__(parent)
        self.items: list = []
        self.setSpacing(spacing)

    def addItem(self, item) -> None:
        self.items.append(item)

    def count(self) -> int:
        return len(self.items)

    def itemAt(self, index: int):
        return self.items[index] if 0 <= index < len(self.items) else None

    def takeAt(self, index: int):
        return self.items.pop(index) if 0 <= index < len(self.items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._place(QRect(0, 0, width, 0), False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._place(rect, True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self.items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _place(self, rect: QRect, move: bool) -> int:
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line = area.x(), area.y(), 0
        for item in self.items:
            hint = item.sizeHint()
            if x + hint.width() > area.right() + 1 and line > 0:
                x, y, line = area.x(), y + line + self.spacing(), 0
            if move:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self.spacing()
            line = max(line, hint.height())
        return y + line - rect.y() + m.bottom()


class Preview(QScrollArea):
    """The pages one under the other, as wide as the room allows (PAGE_WIDTH_MAX at most), each on its thin edge."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("report-preview")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        inside = QWidget()
        inside.setObjectName("report-pages")
        self.column = QVBoxLayout(inside)
        self.column.setContentsMargins(Space.XL, Space.L, Space.XL, Space.XL)
        self.column.setSpacing(Space.XL)
        self.column.addStretch(1)
        self.setWidget(inside)
        self.images: list = []
        self.labels: list[QLabel] = []
        self._fit = QTimer(self)
        self._fit.setSingleShot(True)
        self._fit.setInterval(PREVIEW_RESIZE_MS)
        self._fit.timeout.connect(self._scale)

    def show_pages(self, images: list, total: int | None = None) -> None:
        """The pages, each with its number in the PDF as its tooltip (the image's text "page", else its place);
        `total`: the PDF's pages, when the preview does not show them all (the attachments' beyond the first few)."""
        for label in self.labels:
            self.column.removeWidget(label)
            label.deleteLater()
        self.images, self.labels = list(images), []
        total = total or len(self.images)
        for n, image in enumerate(self.images):
            label = QLabel()
            label.setObjectName("report-page")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            label.setToolTip(_("Page {n} of {total}").format(n=image.text("page") or n + 1, total=total))
            self.column.insertWidget(n, label, 0, Qt.AlignmentFlag.AlignHCenter)
            self.labels.append(label)
        self._scale()

    def width_for_pages(self) -> int:
        room = self.viewport().width() - 2 * Space.XL
        return max(160, min(PAGE_WIDTH_MAX, room))

    def _scale(self) -> None:
        w = self.width_for_pages()
        ratio = self.devicePixelRatioF()
        for image, label in zip(self.images, self.labels, strict=True):
            pix = QPixmap.fromImage(image).scaledToWidth(round(w * ratio), Qt.TransformationMode.SmoothTransformation)
            pix.setDevicePixelRatio(ratio)
            label.setPixmap(pix)
            label.setFixedSize(QSize(w + 2, round(pix.height() / ratio) + 2))     # the page's edge, 1 px a side

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.images:
            self._fit.start()


class ReportPage(QWidget):
    """Phase 6: the commands of today in a row, what the preview is doing, the pages."""

    def __init__(self, actions: dict, parent=None):
        super().__init__(parent)
        self.buttons: dict = {}
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        head = QWidget()
        row = Flow(head)
        row.setContentsMargins(Space.XL, Space.L, Space.XL, Space.S)
        for cid, why in (("export_report", _("The technical report as a PDF, as the preview shows it")),
                         ("compare_variants", _("Every variant computed and compared, the best of each row in bold")),
                         ("save_revision", _("A new file with the suffix _R01, _R02...; the previous one stays")),
                         ("copy_notes", _("The paragraphs of the rules that apply, with their sources"))):
            b = QPushButton(shortcuts.plain(actions[cid].text()))
            b.clicked.connect(actions[cid].trigger)
            b.setToolTip(why)
            if cid == "export_report":
                b.setProperty("primary", True)
            self.buttons[cid] = b
            row.addWidget(b)
        box.addWidget(head)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setContentsMargins(Space.XL, 0, Space.XL, 0)
        set_text(self.status, Text.SECONDARY)
        box.addWidget(self.status)
        self.preview = Preview()
        box.addWidget(self.preview, 1)
        self.empty = _note(_("Compute the production to see the report: its chapters are made of the results."))
        self.empty.setContentsMargins(Space.XL, Space.L, Space.XL, 0)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        box.addWidget(self.empty)
        self.set_ready(False)

    def set_ready(self, ready: bool) -> None:
        """Whether there is a report to show: without the year, a line that says what to do instead of pages."""
        self.preview.setVisible(ready)
        self.empty.setVisible(not ready)
        if not ready:
            self.status.setText("")

    def set_progress(self, fraction: float, what: str) -> None:
        self.status.setText(_("Updating the preview: {what} ({p} %)").format(what=what, p=round(100 * fraction)))

    def show_pages(self, images: list, total: int | None = None) -> None:
        self.set_ready(True)
        self.preview.show_pages(images, total)
        self.status.setText(_("{n} pages, as the PDF will have them").format(n=total or len(images)))


class ReportSide(QWidget):
    """What the designer chooses for the report, above the deliverables: each change is an edit of the project
    (`changed(key, value)`, undoable), the profiles are the preferences' (`profilesAsked`)."""

    changed = Signal(str, object)
    profilesAsked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.loading = False
        box = QVBoxLayout(self)
        box.setContentsMargins(0, 0, 0, Space.L)
        box.setSpacing(Space.M)
        title = set_text(QLabel(_("Report")), Text.STRONG)
        box.addWidget(title)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(Space.L)
        form.setVerticalSpacing(Space.M)
        # a field that does not fit beside its label goes under it: the panel was 29 px narrower than the form, and
        # its right edge (the «Profiles…» button, the deliverables' states) was cut (25/10/2026)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.template = QComboBox()
        self.template.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.template.setMinimumContentsLength(8)
        for tid, t in reports.templates().items():
            self.template.addItem(t.name, tid)
        self.template.currentIndexChanged.connect(lambda _i: self._send("template", self.template.currentData()))
        form.addRow(_("Template"), self.template)
        self.template_note = _note("")
        form.addRow(self.template_note)
        signer = QHBoxLayout()
        signer.setSpacing(Space.S)
        self.profile = QComboBox()
        self.profile.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.profile.setMinimumContentsLength(8)
        self.profile.currentIndexChanged.connect(lambda _i: self._send("profile", self.profile.currentData()))
        signer.addWidget(self.profile, 1)
        manage = QPushButton(_("Profiles…"))
        manage.setToolTip(_("Settings > Report: who signs the reports, with the logo and the contacts"))
        manage.clicked.connect(self.profilesAsked.emit)
        signer.addWidget(manage)
        form.addRow(_("Signed by"), signer)
        self.client = QLineEdit()
        self.client.setPlaceholderText(_("as the cover will say it"))
        self.client.editingFinished.connect(lambda: self._send("client", self.client.text().strip()))
        form.addRow(_("Client"), self.client)
        self.revision = QLineEdit()
        self.revision.setPlaceholderText(_("for example Rev. 0"))
        self.revision.editingFinished.connect(lambda: self._send("revision", self.revision.text().strip()))
        form.addRow(_("Revision"), self.revision)
        box.addLayout(form)
        self.address = QCheckBox(_("The site's address"))
        self.address.setToolTip(_("On the cover and in the site's chapter; the coordinates are always there"))
        self.address.toggled.connect(lambda on: self._send("address", bool(on)))
        box.addWidget(self.address)
        self.register = QCheckBox(_("Export the register of the calculations too"))
        self.register.setToolTip(_("Beside the PDF: the typical year hour by hour as a CSV file, and «How it is "
                                   "computed» as a PDF of its own"))
        self.register.toggled.connect(lambda on: self._send("register", bool(on)))
        box.addWidget(self.register)
        heading = set_text(QLabel(_("Chapters")), Text.STRONG)
        box.addWidget(heading)
        self.chapters_box = QVBoxLayout()
        self.chapters_box.setSpacing(Space.XS)
        box.addLayout(self.chapters_box)
        self.boxes: dict[str, QCheckBox] = {}
        self.off: list = []
        heading = set_text(QLabel(_("Attachments")), Text.STRONG)
        box.addWidget(heading)
        box.addWidget(_note(_("PDF files after the last chapter, each behind a page that names it: the datasheets "
                              "of the modules and of the inverters, the certificates.")))
        self.attachments_box = QVBoxLayout()
        self.attachments_box.setSpacing(Space.S)
        box.addLayout(self.attachments_box)
        self.add_button = QPushButton(_("Add PDF files…"))
        self.add_button.setToolTip(_("The files stay where they are: the project keeps their place, relative to its "
                                     "own file"))
        self.add_button.clicked.connect(self._add_attachments)
        box.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.items: list[dict] = []              # the attachments as the settings have them
        self.rows: list[QWidget] = []
        self.folder = ""                         # where the file dialog opens: the project's folder

    def _send(self, key: str, value) -> None:
        if not self.loading:
            self.changed.emit(key, value)

    def show_settings(self, project, data: dict, profiles: list, default: str, folder: str = "") -> None:
        """The project's choices, the profiles of the preferences («the preferences' one» first), the chapters of its
        template with what each needs, the attachments read now; `folder`: where the file dialog opens."""
        s = reports.settings(project)
        self.folder = folder
        self.loading = True
        try:
            self.template.setCurrentIndex(max(0, self.template.findData(s["template"])))
            self.template_note.setText(reports.templates()[s["template"]].note)
            self.profile.clear()
            names = [p["name"] for p in (reports.clean_profile(x) for x in profiles) if p]
            self.profile.addItem(_("Default: {name}").format(name=default or _("nobody")), None)
            self.profile.setItemData(0, _("The profile Settings > Report gives the projects that choose none"),
                                     Qt.ItemDataRole.ToolTipRole)
            self.profile.addItem(_("Nobody: only the project and the date"), "")
            for name in names:
                self.profile.addItem(name, name)
            self.profile.setCurrentIndex(max(0, self.profile.findData(s["profile"])) if s["profile"] is not None
                                         else 0)
            if not self.client.hasFocus():
                self.client.setText(s["client"])
            if not self.revision.hasFocus():
                self.revision.setText(s["revision"])
            self.address.setChecked(s["address"])
            self.register.setChecked(s["register"])
            self.off = list(s["off"])
            for b in self.boxes.values():
                self.chapters_box.removeWidget(b)
                b.deleteLater()
            self.boxes = {}
            every = reports.chapters()
            labels = {"sim": _("the production"), "results": _("modules laid"), "plant": _("inverters"),
                      "load": _("the consumption"), "econ": _("the economics"), "checks": _("checks")}
            for n, cid in enumerate(reports.templates()[s["template"]].chapters, 1):
                c = every[cid]
                lacking = reports.missing(c, data)
                b = QCheckBox(f"{n}. {c.title}")
                b.setChecked(cid not in s["off"])
                tip = c.note
                if lacking:
                    b.setEnabled(False)
                    tip += "\n" + _("Left out: it needs {what}.").format(what=", ".join(labels.get(k, k) for k in lacking))
                b.setToolTip(tip)
                b.toggled.connect(lambda on, cid=cid: self._toggle(cid, on))
                self.chapters_box.addWidget(b)
                self.boxes[cid] = b
            self._show_attachments(project, s["attachments"])
        finally:
            self.loading = False

    # the attachments

    def _show_attachments(self, project, items: list) -> None:
        from .report import attachments
        for row in self.rows:
            self.attachments_box.removeWidget(row)
            row.deleteLater()
        self.items, self.rows = [dict(a) for a in items], []
        for i, a in enumerate(attachments(project)):
            row = AttachmentRow(a, self.items[i]["title"], i == 0, i == len(items) - 1)
            row.retitled.connect(lambda text, i=i: self._retitle(i, text))
            row.moved.connect(lambda step, i=i: self._move(i, step))
            row.removed.connect(lambda i=i: self._remove(i))
            self.attachments_box.addWidget(row)
            self.rows.append(row)

    def _set_attachments(self, items: list) -> None:
        if items != self.items:
            self.items = items
            self._send("attachments", items)

    def _add_attachments(self) -> None:
        names, _filter = QFileDialog.getOpenFileNames(self, _("Add attachments"), self.folder, _("PDF files (*.pdf)"))
        there = {str(Path(a["path"])) for a in self.items}
        new = [{"path": str(Path(n)), "title": ""} for n in names if str(Path(n)) not in there]
        if new:
            self._set_attachments(self.items + new)

    def _retitle(self, i: int, text: str) -> None:
        items = [dict(a) for a in self.items]
        items[i]["title"] = text.strip()
        self._set_attachments(items)

    def _move(self, i: int, step: int) -> None:
        j = i + step
        if 0 <= j < len(self.items):
            items = list(self.items)
            items[i], items[j] = items[j], items[i]
            self._set_attachments(items)

    def _remove(self, i: int) -> None:
        self._set_attachments([a for k, a in enumerate(self.items) if k != i])

    def _toggle(self, cid: str, on: bool) -> None:
        off = [c for c in self.off if c != cid] + ([] if on else [cid])
        self.off = off
        self._send("off", off)


class AttachmentRow(QWidget):
    """An attachment in the Report phase: its name in the report (a field, the file's name as its hint); under it
    the buttons that move it and take it away, and its file with its pages or why it is left out."""

    retitled = Signal(str)
    moved = Signal(int)
    removed = Signal()

    def __init__(self, a, title: str, first: bool, last: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("attachment")
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(Space.XXS)
        grid.setVerticalSpacing(Space.XXS)
        self.title = QLineEdit(title)
        self.title.setPlaceholderText(Path(a.path).stem)
        self.title.setToolTip(_("The attachment's name in the contents and on the page before it") + chr(10) + a.path)
        self.title.editingFinished.connect(lambda: self.retitled.emit(self.title.text()))
        grid.addWidget(self.title, 0, 0, 1, 4)
        if a.problem:
            text = _("Left out: {why}").format(why=a.problem)
        else:
            text = ngettext("{file}, {n} page", "{file}, {n} pages", a.pages).format(file=Path(a.path).name, n=a.pages)
            if a.protected:
                text += " · " + _("protected: its pages go in as images")
        self.detail = QLabel(text)
        self.detail.setObjectName("row-problem" if a.problem else "row-detail")
        self.detail.setWordWrap(True)
        self.detail.setContentsMargins(Space.XS, 0, 0, 0)
        self.detail.setToolTip(a.path)
        grid.addWidget(self.detail, 1, 3)
        self.buttons = {}
        # the buttons first on their line: a narrow panel cuts its right edge, never them
        for col, (key, tip, slot) in enumerate((
                ("up", _("Before the one above"), lambda: self.moved.emit(-1)),
                ("down", _("After the one below"), lambda: self.moved.emit(1)),
                ("remove", _("Take it out of the report: the file stays where it is"), self.removed.emit))):
            b = QToolButton()
            b.setIcon(icons.icon(key))
            b.setIconSize(QSize(Icon.CONTROL, Icon.CONTROL))
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.clicked.connect(slot)
            b.setEnabled(not ((key == "up" and first) or (key == "down" and last)))
            grid.addWidget(b, 1, col, Qt.AlignmentFlag.AlignTop)
            self.buttons[key] = b
        grid.setColumnStretch(3, 1)
