"""The check for a newer version by itself, in the Qt Quick window (r28): what ui/update_controller.py does for the
Widgets one. In the Windows package only (updates.checks_by_itself), a minute after the start, at most once a day,
when Settings > Privacy allows it (cfg.check_updates). A newer release is said in the status bar until something
else is said there, and remembered (cfg.pending_update) so that the next start says it again; Help > Check for
updates shows it, downloads it, verifies its SHA-256 and its signature and installs it (dialogs.py, files_part.py).
Nothing is installed from here."""
import os
import shutil
import threading
from datetime import date
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

from meridiana import config, log, updates
from meridiana.i18n import _

# developer aid, with updates.DEV_RELEASE_API only: the check after this many ms instead of a minute
DEV_DELAY = 'MERIDIANA_DEV_UPDATE_DELAY_MS'


class UpdateCheck(QObject):
    answered = Signal(object, str)

    def __init__(self, part):
        super().__init__(part)
        self.part = part
        self._closed = False
        self.answered.connect(self._answer)         # emitted by the thread of the request: queued to this one

    def start(self):
        trial = os.environ.get(updates.DEV_RELEASE_API)
        if not (updates.checks_by_itself() or trial):
            return
        cfg = self.part.cfg
        version = updates.remembered_version(cfg.pending_update)
        if version and updates.is_newer(version):
            QTimer.singleShot(3000, self, lambda: self._tell(version))
        elif cfg.pending_update:
            cfg.pending_update = {}
            self._save()
        delay = updates.CHECK_DELAY_MS
        if trial and os.environ.get(DEV_DELAY, '').isdigit():
            delay = int(os.environ[DEV_DELAY])
        QTimer.singleShot(delay, self, self._due)

    def close(self):
        self._closed = True

    def _save(self):
        try:
            config.save(self.part.cfg, Path(self.part.paths.config_file))
        except OSError as error:
            log.complain('update check', error)

    def _due(self):
        cfg = self.part.cfg
        today = date.today().isoformat()
        if self._closed or not updates.check_due(cfg.check_updates, cfg.last_update_check, today):
            return
        cfg.last_update_check = today
        self._save()
        # the installers of earlier updates: Setup has finished with them by now
        updates.clean_downloads()
        shutil.rmtree(Path(self.part.paths.cache) / 'updates', ignore_errors=True)
        threading.Thread(target=self._ask, name='update-check', daemon=True).start()

    def _ask(self):
        try:
            release, why = updates.latest_release(), ''
        except updates.NoRelease:
            release, why = None, ''
        except updates.UpdateError as error:
            release, why = None, str(error) or type(error).__name__
        if not self._closed:
            self.answered.emit(release, why)

    def _answer(self, release, why):
        if self._closed:
            return
        if release is None:
            if why:
                log.complain('update check', updates.UpdateError(why))
            return
        cfg = self.part.cfg
        if not updates.is_newer(release.version):
            if cfg.pending_update:
                cfg.pending_update = {}
                self._save()
            return
        cfg.pending_update = updates.remember_release(release)
        self._save()
        self._tell(release.version)

    def _tell(self, version):
        shell = getattr(self.part.host, 'shell', None)
        if not self._closed and shell is not None:
            shell.show_notice(_('Version {version} is available: Help > Check for updates.').format(version=version), 0)
