"""Update policy and persistent notifications, separate from the main window."""
from datetime import date

from PySide6.QtCore import QObject, QTimer

from .. import __version__, log, updates
from ..i18n import _
from .update_dialog import CheckJob, UpdateDialog


class UpdateController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.dialog = None

    def startup(self):
        if updates.distribution_channel() == "flatpak":
            return
        version = updates.remembered_version(self.window.cfg.pending_update)
        if version and updates.is_newer(version):
            self.notify(version)
        elif self.window.cfg.pending_update:
            self.window.cfg.pending_update = {}
            self.window._save_config()

    def notify(self, version):
        self.window.tell(_("Version {version} is available: Help > Check for updates.").format(version=version), 0)

    def daily(self):
        win = self.window
        today = date.today().isoformat()
        if not updates.check_due(win.cfg.check_updates, win.cfg.last_update_check, today):
            return
        win.cfg.last_update_check = today
        win._save_config()
        updates.clean_downloads()
        win.check_updates(manual=False)

    def check(self, manual):
        win = self.window
        if self.dialog is not None:
            if manual:
                self.dialog.show()
                self.dialog.raise_()
                self.dialog.activateWindow()
            return
        if updates.distribution_channel() == "flatpak":
            if manual:
                win.tell(_("Flatpak updates are managed by your desktop software centre. Open it to check the installed Flatpak remote."), 0)
            return
        if win.update_job is not None:
            return
        job = CheckJob(manual)
        job.signals.done.connect(win._update_answer)
        win.update_job = job
        if manual:
            win.tell(_("Checking for updates…"), 10)
        win.pool.start(job)

    def answer(self, release, why, manual):
        win = self.window
        win.update_job = None
        if release is None:
            if manual:
                win.tell(_("The check for updates failed: {error}").format(error=why))
            else:
                log.complain("update check", updates.UpdateError(why))
            return
        if not updates.is_newer(release.version):
            win.cfg.pending_update = {}
            win._save_config()
            if manual:
                win.tell(_("Meridiana {version} is the latest version.").format(version=__version__))
            return
        win.cfg.pending_update = updates.remember_release(release)
        win._save_config()
        self.notify(release.version)
        if manual:
            win.show_update(release)
        else:
            dirty = win.session.dirty()
            if not updates.automatic_install_allowed(
                    enabled=win.cfg.check_updates, opted_in=win.cfg.auto_install_updates,
                    channel=updates.distribution_channel(), signed_installer=updates.installer_of(release) is not None,
                    dirty=dirty):
                if dirty and win.cfg.auto_install_updates:
                    win.tell(_("An update is available. Save your project before installing it: Help > Check for updates."), 0)
                return
            # Non-modal: the designer can work and cancel throughout the download.
            dialog = UpdateDialog(release, win, before_install=self._can_install)
            self.dialog = dialog
            dialog.finished.connect(self._closed)
            dialog.show()
            QTimer.singleShot(0, dialog, dialog._download)

    def _can_install(self):
        win = self.window
        return updates.automatic_install_allowed(
            enabled=win.cfg.check_updates, opted_in=win.cfg.auto_install_updates,
            channel=updates.distribution_channel(), signed_installer=True, dirty=win.session.dirty())

    def _closed(self, _result):
        if self.dialog is not None:
            self.dialog.deleteLater()
            self.dialog = None
