"""A newer version (updates.py; task 18f): what it brings, and its installer downloaded, checked against the SHA-256
GitHub publishes and against the project's minisign signature, and started (the installed build); or the release's
page opened (the portable zip, the sources, a release without a signed installer). The checks and the downloads run
in the thread pool and come back with signals: the window never waits."""

from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QLabel, QProgressBar, QPushButton, QTextBrowser,
                               QVBoxLayout)

from .. import APP_NAME, __version__, updates
from ..i18n import _
from . import tell


class CheckSignals(QObject):
    done = Signal(object, str)          # the latest release (None when the check failed), and why it failed


class CheckJob(QRunnable):
    """The latest release, asked of GitHub away from the window's thread."""

    def __init__(self):
        super().__init__()
        self.signals = CheckSignals()

    def run(self):
        try:
            release = updates.latest_release()
        except updates.UpdateError as error:
            tell(self.signals.done, None, str(error))
            return
        tell(self.signals.done, release, "")


class DownloadSignals(QObject):
    progress = Signal(int, int)
    done = Signal(str)
    failed = Signal(str)


class DownloadJob(QRunnable):
    """The installer, downloaded and checked (updates.download), away from the window's thread."""

    def __init__(self, asset: updates.Asset):
        super().__init__()
        self.asset = asset
        self.signals = DownloadSignals()
        self.cancelled = threading.Event()

    def run(self):
        try:
            dest = updates.download_folder() / self.asset.name
            updates.download(self.asset, dest, lambda done, total: tell(self.signals.progress, done, total),
                             self.cancelled)
        except Exception as error:      # noqa: BLE001  whatever it is, said: never a dialog stuck on «Downloading…»
            tell(self.signals.failed, str(error))
            return
        tell(self.signals.done, str(dest))


class UpdateDialog(QDialog):
    """`installer`: the asset to install (by default the release's signed installer, for the installed build only);
    `before_install()`: False keeps Setup from starting (the window asks to save the project); `start(args)` starts
    Setup (subprocess.Popen; the tests give their own)."""

    def __init__(self, release: updates.Release, parent=None, installer: updates.Asset | None = None,
                 before_install: Callable[[], bool] | None = None, start: Callable[[list], object] | None = None):
        super().__init__(parent)
        self.setWindowTitle(_("Update"))
        self.resize(520, 420)
        self.release = release
        self.installer = installer if installer is not None else (
            updates.installer_of(release) if updates.installed_build() else None)
        self.before_install = before_install
        self.start = start or (lambda args: subprocess.Popen(args, close_fds=True))
        self.job: DownloadJob | None = None
        box = QVBoxLayout(self)
        heading = QLabel(_("Version {version} is available").format(version=release.version))
        from .design import Text, set_text
        set_text(heading, Text.HEADING)
        box.addWidget(heading)
        box.addWidget(QLabel(_("You are using version {version}.").format(version=__version__)))
        if release.notes.strip():
            notes = QTextBrowser()
            notes.setOpenExternalLinks(True)
            notes.setMarkdown(release.notes.strip()[:4000])
            from .help_box import dress
            dress(notes.document())             # the headings in the catalogue's styles (R121)
            box.addWidget(notes, 1)
        self.page = QLabel(_("The release and its signed files: <a href=\"{url}\">{url}</a>").format(url=release.url))
        self.page.setTextFormat(Qt.TextFormat.RichText)
        self.page.setOpenExternalLinks(True)
        self.page.setWordWrap(True)
        box.addWidget(self.page)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        box.addWidget(self.progress)
        self.status = QLabel()
        self.status.setWordWrap(True)
        box.addWidget(self.status)
        buttons = QDialogButtonBox()
        later = buttons.addButton(_("Later"), QDialogButtonBox.ButtonRole.RejectRole)
        later.clicked.connect(self.reject)
        if self.installer is not None:
            self.action = QPushButton(_("Download and install"))
            self.action.clicked.connect(self._download)
            self.status.setText(_("The installer is checked against the checksum GitHub publishes and against the "
                                  "project's signature before it starts: one that does not match is never started. "
                                  "{app} closes while the new version is installed, and opens again.").format(
                app=APP_NAME))
        else:
            self.action = QPushButton(_("Open the release page"))
            self.action.clicked.connect(self._open_page)
        self.action.setDefault(True)
        buttons.addButton(self.action, QDialogButtonBox.ButtonRole.AcceptRole)
        box.addWidget(buttons)
        self.action.setFocus()

    def _open_page(self) -> None:
        QDesktopServices.openUrl(QUrl(self.release.url))
        self.accept()

    def _download(self) -> None:
        self.action.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.status.setText(_("Downloading…"))
        self.job = DownloadJob(self.installer)
        self.job.signals.progress.connect(self._progress)
        self.job.signals.done.connect(self._downloaded)
        self.job.signals.failed.connect(self._failed)
        QThreadPool.globalInstance().start(self.job)

    def _progress(self, done: int, total: int) -> None:
        if total:
            self.progress.setRange(0, total)
            self.progress.setValue(min(done, total))
            self.progress.setFormat(f"{done / 1e6:.1f} / {total / 1e6:.1f} MB")

    def _failed(self, why: str) -> None:
        self.progress.setVisible(False)
        self.status.setText(_("Download failed: {error}").format(error=why))
        self.action.setEnabled(True)

    def _downloaded(self, path: str) -> None:
        if self.job is None or self.job.cancelled.is_set():
            return                      # «Later» once the last piece was in: not started (gone at the next start)
        if self.before_install is not None and not self.before_install():
            self.progress.setVisible(False)
            self.status.setText(_("Not installed: the project is still open with its changes. Save it, then try again."))
            self.action.setEnabled(True)
            return
        self.status.setText(_("Starting the installer…"))
        try:
            # Setup closes the program, replaces its files and starts it again; its progress shows
            self.start(updates.installer_command(Path(path)))
        except OSError as error:
            self._failed(_("Cannot start the installer: {error}").format(error=error.strerror or error))

    def done(self, result: int) -> None:
        if self.job is not None:
            self.job.cancelled.set()
        super().done(result)
