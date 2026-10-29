"""The local clients and jobs registry inside the File page (R150)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget)

from ..i18n import _
from ..registry import RegistryError, read_exchange
from .design import Space, Text, set_text


class RegistryPage(QWidget):
    changed = Signal()

    def __init__(self, registry, host=None, parent=None):
        super().__init__(parent)
        self.registry, self.host = registry, host
        self._pending_import = None
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
        exchange = QHBoxLayout()
        self.import_registry = QPushButton(_("Import registry…"))
        self.export_registry = QPushButton(_("Export registry…"))
        self.apply_import = QPushButton(_("Apply import"))
        exchange.addWidget(self.import_registry)
        exchange.addWidget(self.export_registry)
        exchange.addWidget(self.apply_import)
        exchange.addStretch(1)
        outer.addLayout(exchange)
        self.search = QLineEdit()
        self.search.setPlaceholderText(_("Search by client, job code or name"))
        outer.addWidget(self.search)
        self.import_preview = QLabel("")
        set_text(self.import_preview, Text.DESCRIPTION)
        self.import_preview.setWordWrap(True)
        self.import_preview.hide()
        outer.addWidget(self.import_preview)
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
        self.folders_group = QGroupBox(_("Linked folders"))
        folders = QVBoxLayout(self.folders_group)
        self.folder_box = QVBoxLayout()
        folders.addLayout(self.folder_box)
        self.link_folder = QPushButton(_("Link folder…"))
        folders.addWidget(self.link_folder)
        right.addWidget(self.folders_group)
        self.folders_group.hide()
        self.error = QLabel("")
        set_text(self.error, Text.SECONDARY)
        self.error.setWordWrap(True)
        right.addWidget(self.error)
        right.addStretch(1)
        columns.addLayout(right, 1)
        self.client_editor.hide()
        self.job_editor.hide()
        self.apply_import.hide()
        self.search.textChanged.connect(self.refresh)
        self.new_client.clicked.connect(self._new_client)
        self.new_job.clicked.connect(self._new_job)
        self.save_client.clicked.connect(self._save_client)
        self.save_job.clicked.connect(self._save_job)
        self.import_registry.clicked.connect(self._import_registry)
        self.export_registry.clicked.connect(self._export_registry)
        self.apply_import.clicked.connect(self._apply_import)
        self.link_folder.clicked.connect(self._link_folder)
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
        if self.registry.manifest_errors:
            details = "; ".join(message for _path, message in self.registry.manifest_errors.values())
            self.error.setText(_("Some job files could not be written or removed: {errors}").format(errors=details))
        else:
            self.error.clear()

    def _selected_client(self):
        item = self.client_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def _selection_changed(self):
        client = self.registry.client(self._selected_client()) if self._selected_client() else None
        item = self.job_list.currentItem()
        job = self.registry.job(item.data(Qt.ItemDataRole.UserRole)) if item else None
        while self.folder_box.count():
            widget = self.folder_box.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self.folders_group.setVisible(job is not None)
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
            for folder in folders:
                consent = QCheckBox(folder["path"])
                consent.setToolTip(_("Write and update {file} in this folder. Reserved jobs never have one.").format(
                    file=".meridiana-commessa.json"))
                consent.blockSignals(True)
                consent.setChecked(folder["manifest_consent"] and not job["reserved"])
                consent.setEnabled(not job["reserved"])
                consent.blockSignals(False)
                consent.toggled.connect(lambda allowed, folder_id=folder["id"]:
                                        self._manifest_consent(folder_id, allowed))
                self.folder_box.addWidget(consent)
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

    def _link_folder(self):
        item = self.job_list.currentItem()
        job_id = item.data(Qt.ItemDataRole.UserRole) if item else ""
        if not job_id:
            self.error.setText(_("Choose a job before linking a folder."))
            return
        start = self.host.cfg.last_folder if self.host is not None else ""
        folder = QFileDialog.getExistingDirectory(self, _("Link a job folder"), start)
        if not folder:
            return
        try:
            self.registry.link_folder(job_id, folder)
        except (RegistryError, OSError) as error:
            self._show_error(error)
            return
        self.error.clear()
        self.refresh()
        self.changed.emit()

    def _manifest_consent(self, folder_id, allowed):
        try:
            self.registry.set_manifest_consent(folder_id, allowed)
        except (RegistryError, OSError) as error:
            self._show_error(error)
        else:
            self.error.clear()
            self.changed.emit()
        self.refresh()

    def _import_registry(self):
        start = self.host.cfg.last_folder if self.host is not None else ""
        path, _selected = QFileDialog.getOpenFileName(self, _("Import the client and job registry"), start,
                                                      _("JSON files (*.json)"))
        if not path:
            return
        try:
            data = read_exchange(path)
            preview = self.registry.preview_import(data)
        except (RegistryError, OSError) as error:
            self._pending_import = None
            self.apply_import.hide()
            self.import_preview.hide()
            self._show_error(error)
            return
        self._pending_import = data
        self.error.clear()
        text = _("Import preview: {new} new, {updated} updated, {unchanged} unchanged. Existing records are merged "
                 "by id; records absent from the file stay here.").format(
            new=preview["new"], updated=preview["updated"], unchanged=preview["unchanged"])
        if preview["conflicts"]:
            text += "\n" + _("Conflicts, nothing can be imported: {conflicts}").format(
                conflicts="; ".join(preview["conflicts"]))
        self.import_preview.setText(text)
        self.import_preview.show()
        self.apply_import.setVisible(not preview["conflicts"])

    def _apply_import(self):
        if self._pending_import is None:
            return
        try:
            preview = self.registry.import_data(self._pending_import)
        except (RegistryError, OSError) as error:
            self._show_error(error)
            return
        self._pending_import = None
        self.apply_import.hide()
        self.import_preview.setText(_("Imported: {new} new, {updated} updated, {unchanged} unchanged.").format(
            new=preview["new"], updated=preview["updated"], unchanged=preview["unchanged"]))
        self.refresh()
        self.changed.emit()

    def _export_registry(self):
        start = self.host.cfg.last_folder if self.host is not None else ""
        path, _selected = QFileDialog.getSaveFileName(self, _("Export the client and job registry"), start,
                                                      _("JSON files (*.json)"))
        if not path:
            return
        if any(job["reserved"] for job in self.registry.list_jobs(include_archived=True)):
            answer = QMessageBox.warning(
                self, _("Export reserved jobs"),
                _("The registry contains reserved jobs. The JSON file is not encrypted and includes their names, "
                  "contacts, project paths and folder paths. Write it only where these data may be stored."),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            self.registry.export(path)
        except (RegistryError, OSError) as error:
            self._show_error(error)
            return
        self.error.setText(_("Registry exported to {path}").format(path=path))

    def _show_error(self, error):
        text = str(error)
        messages = {
            "a client needs a name": _("A client needs a name."),
            "a job needs a name": _("A job needs a name."),
            "a job code is five digits": _("The job code must be exactly five digits."),
            "unknown job status or phase": _("The job status or phase is not valid."),
            "a reserved job never writes a folder manifest": _("A reserved job never writes a folder manifest."),
            "the folder has not consented to a job manifest": _("This folder has not consented to a job manifest."),
            "the folder is already linked to another job": _("This folder is already linked to another job."),
        }
        if "UNIQUE constraint failed: jobs.code" in text:
            text = _("This job code is already used.")
        elif "UNIQUE constraint failed: projects.path" in text:
            text = _("This project path is already linked.")
        elif "UNIQUE constraint failed: folders.path" in text:
            text = _("This folder is already linked.")
        self.error.setText(messages.get(text, text))
