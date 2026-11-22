"""Autosave and recovery in the Qt Quick window (recovery.py; r30-struttura A2: what ui/window.py did for the Widgets
one). While the project has unsaved changes a copy goes to the state folder every two minutes, written on a thread of
its own (a large project takes a second: the window never waits); a save, or another project taken after the changes
were discarded, takes it away. A copy left by a Meridiana that stopped without saving is offered back: at the start
(main: the newest one, or only the copy of the project asked for by name) and when its project is opened from the
File page. «No» deletes the copy; the copies of a Meridiana still running are never offered (recovery.pending).

The window closed with changes nobody was asked about (the end of the session: closing_part.py asks in every other
case) keeps a fresh copy, offered at the next start; an answer to the question about the changes takes it away. Only the program's own start holds
the copies as its own (`claim`): the windows of the tests and of the tools write none at their end."""
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot
from PySide6.QtQml import QQmlComponent

from meridiana.app.platform import log
from meridiana.app.project import recovery
from meridiana.core.model import model
from meridiana.i18n import _

from .parts import Part, QML

AUTOSAVE_MS = 120_000           # a copy of the unsaved changes every two minutes
RECOVERED_MS = 8000             # «Recovered: save it to keep it» in the status bar


class RecoveryPart(QObject):
    changed = Signal()
    _written = Signal(object, object, object)       # from the writing thread: the copy, its project's file, the error

    def __init__(self, engine, session, host):
        super().__init__()
        self.engine, self.session, self.host = engine, session, host
        self.files = None
        self.owner = False              # this process holds the copies of its state folder (claim)
        self._copy = None               # the copy offered, until it is answered
        self._thread = None
        self._recovering = False
        self._closed = False
        self.timer = QTimer(self)
        self.timer.setInterval(AUTOSAVE_MS)
        self.timer.timeout.connect(self.autosave)
        self._written.connect(self._autosaved)
        engine.rootContext().setContextProperty('recoveryBackend', self)

    @property
    def state(self):
        return self.host.paths.state

    offered = Property(bool, lambda self: self._copy is not None, notify=changed)

    @Property(str, notify=changed)
    def question(self):
        if self._copy is None:
            return ''
        name = Path(self._copy['path']).name if self._copy['path'] else _('a new project')
        when = time.strftime('%d/%m/%Y %H:%M', time.localtime(self._copy['saved']))
        return _('Meridiana stopped without saving {name}: a copy of {when} is there. Recover it?').format(
            name=name, when=when)

    @Property('QVariantMap', constant=True)
    def words(self):
        return dict(title=_('Recover the changes'), yes=_('Yes'), no=_('No'))

    def bind(self, root):
        self.files = self.host.parts.controllers.get('files')
        if self.files is not None:
            self.files.saved.connect(self._saved)
            self.files.opened.connect(self._opened)
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML / 'Shell/RecoveryDialog.qml')))
        dialog = self.component.createWithInitialProperties({'parent': root.contentItem()}, self.engine.rootContext())
        if dialog is None:
            raise RuntimeError('\n'.join(e.toString() for e in self.component.errors()))
        dialog.setParent(root)          # handed to the window, never kept (a wrapper outlives its item)
        self.timer.start()

    # the copies of this start

    def claim(self):
        """This process's mark on the copies it writes (recovery.claim), from the program's start: another start
        neither offers nor deletes them while this one runs."""
        try:
            recovery.claim(self.state)
        except OSError as error:
            log.complain('claim the recovery copies', error)
        self.owner = True

    def release(self):
        """The mark let go at the end of the program, after the window closed."""
        recovery.release(self.state)
        self.owner = False

    # a copy left behind, offered back

    def offer(self, asked=None):
        """The newest copy left by a Meridiana that stopped without saving, asked about in the window; with a project
        `asked` for by name only its own copy (the copies of the other projects wait for a start without one). True
        when there is one to answer about."""
        if self._closed:
            return False
        if self._copy is None:
            copies = recovery.pending(self.state) if asked is None else recovery.pending(self.state, Path(asked))
            if not copies:
                return False
            self._copy = copies[0]
            self.changed.emit()
        return True

    @Slot(bool)
    def answer(self, recover):
        """«Yes»: the copy in hand, not saved yet, with the file it was a copy of; «No»: the copy deleted."""
        copy, self._copy = self._copy, None
        self.changed.emit()
        if copy is None:
            return
        if not recover:
            copy['file'].unlink(missing_ok=True)
            return
        try:
            project = model.Project.from_json(copy['project'])
        except Exception as error:      # noqa: BLE001  a copy written by hand or damaged: said, not a crash
            log.complain('recovery', error)
            copy['file'].replace(copy['file'].with_suffix('.unreadable'))       # set aside: not lost, not offered again
            self.host.shell.show_notice(_('The copy could not be read: {error}').format(error=error), 0, 'error')
            return
        previous = self.session.autosaved
        self.session.take(project, Path(copy['path']) if copy['path'] else None, saved=False)
        if previous is not None and previous != copy['file']:
            previous.unlink(missing_ok=True)        # the copy of the project that was in hand
        self.session.autosaved = copy['file']       # a save takes it away
        if self.files is not None:
            self._recovering = True
            try:
                self.files.opened.emit('')          # the pages closed, the views told, as for a new project
            finally:
                self._recovering = False
        self.host.shell.show_notice(_('Recovered: save it to keep it'), RECOVERED_MS)

    # the copy of the work in hand

    @Slot()
    def autosave(self):
        """A copy of the unsaved changes, if there are any, written on a thread of its own. True when one began."""
        session = self.session
        if self._closed or self._thread is not None or self._copy is not None or not session.dirty():
            return False
        # R598: the photo, a reference (recovery.write makes its project of a copy: the photo stays as it is)
        data, path, state = session.photo(), session.path, self.state

        def run():
            try:
                result = (recovery.write(state, path, data), None)
            except (OSError, ValueError) as error:
                result = (None, error)
            self._written.emit(result[0], path, result[1])
        self._thread = threading.Thread(target=run, name='meridiana-autosave')
        self._thread.start()
        return True

    @Slot(object, object, object)
    def _autosaved(self, written, path, error):
        self._thread = None
        if error is not None:
            log.complain('autosave', error)
            if not self._closed:
                self.host.shell.show_notice(_('The recovery copy could not be written: {error}').format(error=error))
            return
        session = self.session
        if self._closed:
            return                                  # close() decides about it
        if session.path != path or not session.dirty():
            written.unlink(missing_ok=True)         # saved, or another project in hand, while it was written
            return
        if session.autosaved is not None and session.autosaved != written:
            session.autosaved.unlink(missing_ok=True)       # the project got a file: the copy of the new one goes
        session.autosaved = written

    def wait(self, seconds=60.0):
        """The copy being written, written (the tests; close)."""
        if self._thread is not None:
            self._thread.join(seconds)

    def _saved(self, _path):
        self.session.drop_autosave(self.state)

    def _opened(self, path):
        """Another project in hand, its changes saved or discarded before: the copy of the old one goes. A project
        opened from its file with a copy left behind is offered it."""
        if self._recovering:
            return
        session = self.session
        if session.autosaved is not None:
            session.autosaved.unlink(missing_ok=True)
            session.autosaved = None
        if path:
            self.offer(Path(path))

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.timer.stop()
        self.wait()
        if self._copy is not None:
            return                                  # a copy offered and not answered: it stays as it is
        session = self.session
        try:
            asked = self.files is not None and self.files.quitting     # File > Quit: the changes were asked about
            if self.owner and not asked and session.dirty():
                # closed without a question about the changes: a fresh copy, offered at the next start
                session.autosave(self.state)
            else:
                session.drop_autosave(self.state)
        except (OSError, ValueError) as error:
            log.complain('autosave', error)


def install(engine, session, cache, window):
    controller = RecoveryPart(engine, session, window)
    return Part('recovery', controllers={'recovery': controller}, bind=controller.bind, close=controller.close)
