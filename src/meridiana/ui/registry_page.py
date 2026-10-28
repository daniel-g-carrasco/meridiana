"""The local clients and jobs registry inside the File page (R150)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout, QWidget)

from ..i18n import _
from ..registry import RegistryError
from .design import Space, Text, set_text


class RegistryPage(QWidget):
    changed = Signal()

    def __init__(self, registry, host=None, parent=None):
        super().__init__(parent)
        self.registry, self.host = registry, host
        outer = QVBoxLayout(self)
        outer.setContentsMargins(Space.XXXL, Space.XXL, Space.XXXL, Space.XXL)
        outer.setSpacing(Space.M)
        title = QLabel(_("Clients and jobs"))
        set_text(title, Text.DISPLAY)
        outer.addWidget(title)
        lead = QLabel(_("Choose a client and a job, or add them here. Everything stays on this PC."))
        set_text(lead, Text.DESCRIPTION)
        lead.setWordWrap(True)
        outer.addWidget(lead)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Search by client, job code or name"))
        outer.addWidget(self.search)
        columns = QHBoxLayout()
        columns.setSpacing(Space.XL)
        outer.addLayout(columns, 1)
        clients, self.new_client, self.client_list = self._column(_("Clients"), _("New client"))
        jobs, self.new_job, self.job_list = self._column(_("Jobs"), _("New job"))
        columns.addWidget(clients, 1)
        columns.addWidget(jobs, 1)
        right = QVBoxLayout()
        self.detail = QLabel(_("Choose a client or a job."))
        set_text(self.detail, Text.BODY)
        self.detail.setWordWrap(True)
        self.detail.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        right.addWidget(self.detail)
        self.client_editor, client_form = self._editor()
        self.client_name = QLineEdit()
        client_form.addRow(_("Client name"), self.client_name)
        self.save_client = QPushButton(_("Save client"))
        client_form.addRow(self.save_client)
        right.addWidget(self.client_editor)
        self.job_editor, job_form = self._editor()
        self.job_code = QLineEdit()
        self.job_code.setMaxLength(5)
        self.job_code.setPlaceholderText(_("Five digits"))
        job_form.addRow(_("Job code"), self.job_code)
        self.job_name = QLineEdit()
        job_form.addRow(_("Job name"), self.job_name)
        self.job_client = QComboBox()
        job_form.addRow(_("Client"), self.job_client)
        self.job_reserved = QPushButton(_("Reserved job"))
        self.job_reserved.setCheckable(True)
        job_form.addRow(self.job_reserved)
        self.save_job = QPushButton(_("Save job"))
        job_form.addRow(self.save_job)
        right.addWidget(self.job_editor)
        self.error = QLabel("")
        set_text(self.error, Text.SECONDARY)
        self.error.setWordWrap(True)
        right.addWidget(self.error)
        right.addStretch(1)
        columns.addLayout(right, 1)
        self.client_editor.hide()
        self.job_editor.hide()
        self.search.textChanged.connect(self.refresh)
        self.new_client.clicked.connect(self._new_client)
        self.new_job.clicked.connect(self._new_job)
        self.save_client.clicked.connect(self._save_client)
        self.save_job.clicked.connect(self._save_job)
        self.client_list.currentRowChanged.connect(self._selection_changed)
        self.job_list.currentRowChanged.connect(self._selection_changed)
        self.refresh()

    def _column(self, title, button):
        group = QGroupBox(title)
        box = QVBoxLayout(group)
        new = QPushButton(button)
        listing = QListWidget()
        box.addWidget(new)
        box.addWidget(listing)
        return group, new, listing

    def _editor(self):
        group = QGroupBox(_("New record"))
        form = QFormLayout(group)
        return group, form

    @staticmethod
    def _put(listing, records, text):
        selected = listing.currentItem().data(Qt.ItemDataRole.UserRole) if listing.currentItem() else None
        listing.clear()
        for record in records:
            item = QListWidgetItem(text(record))
            item.setData(Qt.ItemDataRole.UserRole, record["id"])
            listing.addItem(item)
            if record["id"] == selected:
                listing.setCurrentItem(item)
        if listing.currentRow() < 0 and listing.count():
            listing.setCurrentRow(0)

    def refresh(self):
        text = self.search.text()
        self._put(self.client_list, self.registry.list_clients(text), lambda row: row["name"])
        self._put(self.job_list, self.registry.list_jobs(text), lambda row: f"{row['code']}  {row['name']}")
        self._selection_changed()
    def _selected_client(self):
        item = self.client_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def _selection_changed(self):
        client = self.registry.client(self._selected_client()) if self._selected_client() else None
        item = self.job_list.currentItem()
        job = self.registry.job(item.data(Qt.ItemDataRole.UserRole)) if item else None
        if job is not None:
            client = self.registry.client(job["client_id"])
            folders = self.registry.list_folders(job["id"])
            projects = self.registry.list_projects(job["id"])
            statuses = {"waiting": _("Waiting"), "in_progress": _("In progress"),
                        "delivered": _("Delivered"), "archived": _("Archived")}
            phases = {"preliminary": _("Preliminary"), "definitive": _("Definitive"),
                      "executive": _("Executive"), "construction": _("Construction")}
            self.detail.setText(_("Job {code}: {name}\nClient: {client}\nStatus: {status}\nPhase: {phase}\n"
                                  "Reserved: {reserved}\nProjects: {projects}\nFolders: {folders}").format(
                code=job["code"], name=job["name"], client=client["name"],
                status=statuses.get(job["status"], job["status"]), phase=phases.get(job["phase"], job["phase"]),
                reserved=_("yes") if job["reserved"] else _("no"), projects=len(projects), folders=len(folders)))
        elif client is not None:
            self.detail.setText(_("Client: {name}\nKind: {kind}\n{notes}").format(
                name=client["name"], kind=client["kind"], notes=client["notes"]))
        else:
            self.detail.setText(_("Choose a client or a job."))

    def _new_client(self):
        self.job_editor.hide()
        self.error.clear()
        self.client_name.clear()
        self.client_editor.show()
        self.client_name.setFocus()

    def _save_client(self):
        try:
            self.registry.create_client(self.client_name.text())
        except RegistryError as error:
            self._show_error(error)
            return
        self.client_editor.hide()
        self.refresh()
        self.changed.emit()

    def _new_job(self):
        clients = self.registry.list_clients()
        if not clients:
            self._new_client()
            return
        self.client_editor.hide()
        self.error.clear()
        self.job_client.clear()
        for client in clients:
            self.job_client.addItem(client["name"], client["id"])
        current = self._selected_client()
        self.job_client.setCurrentIndex(max(0, self.job_client.findData(current)))
        codes = [int(job["code"]) for job in self.registry.list_jobs(include_archived=True)]
        self.job_code.setText(f"{max(codes, default=0) + 1:05d}")
        self.job_name.clear()
        self.job_reserved.setChecked(False)
        self.job_editor.show()
        self.job_name.setFocus()

    def _save_job(self):
        try:
            self.registry.create_job(self.job_code.text(), self.job_name.text(), self.job_client.currentData(),
                                     status="in_progress", reserved=self.job_reserved.isChecked())
        except RegistryError as error:
            self._show_error(error)
            return
        self.job_editor.hide()
        self.refresh()
        self.changed.emit()
