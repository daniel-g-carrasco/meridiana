"""The question «Save the changes to <name>?» when the window is closed with unsaved changes (Daniel, 10/11/2026: «vorrei
che lo chiedesse»), however it is closed: its cross, Alt+F4, the taskbar, Quit from the File page or a command.
«Save» writes the project (a project without a file asks where first, and the window closes only when the save
succeeds), «Don't save» closes, «Cancel» leaves everything as it was; without changes the window closes at once. The
answers go through the File page's own (FilesBackend.resolveChanges), as the Widgets window's question did.

When the system ends the session (a shutdown, a log-off, the installer closing the program to update it: Windows sends
WM_QUERYENDSESSION, Qt says commitDataRequest) nobody is asked: the window closes and the recovery part keeps a fresh
copy of the changes, offered at the next start, so that a dialog never holds the shutdown up."""
from pathlib import Path

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent

from meridiana.i18n import _

from .parts import Part, QML


class ClosingPart(QObject):
    changed = Signal()

    def __init__(self, engine, session, host):
        super().__init__()
        self.engine, self.session, self.host = engine, session, host
        self.files = None
        self.root = None
        self._asking = False
        self.ending = False             # the system is ending the session: nobody is asked
        self.forced = False             # QuickWindow.close: the program takes the window apart
        self._closed = False
        engine.rootContext().setContextProperty('closingBackend', self)

    asking = Property(bool, lambda self: self._asking, notify=changed)

    @Property(str, notify=changed)
    def question(self):
        path = self.session.path
        name = Path(path).name if path is not None else _('the new project')
        return _('Save the changes to {name}?').format(name=name)

    @Property('QVariantMap', constant=True)
    def words(self):
        return dict(title=_('Unsaved changes'), save=_('Save'), discard=_("Don't save"), cancel=_('Cancel'))

    def bind(self, root):
        self.root = root
        self.files = self.host.parts.controllers.get('files')
        app = QGuiApplication.instance()
        if app is not None:
            app.commitDataRequest.connect(self.session_ends)
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(QML / 'Shell/CloseDialog.qml')))
        dialog = self.component.createWithInitialProperties({'parent': root.contentItem()}, self.engine.rootContext())
        if dialog is None:
            raise RuntimeError('\n'.join(e.toString() for e in self.component.errors()))
        dialog.setParent(root)          # handed to the window, never kept (a wrapper outlives its item)

    @Slot(result=bool)
    def mayClose(self):
        """Asked by the window when something closes it: True closes it now; False keeps it open and asks."""
        if self._closed or self.ending or self.forced or not self.session.dirty():
            return True
        if self.files is not None and self.files.quitting:
            return True                 # the question was answered already (here, or on the File page)
        if not self._asking:
            self._asking = True
            self.changed.emit()
        return False

    @Slot(str)
    def answer(self, choice):
        """«save», «discard» or «cancel»: the File page's own answers. Saving or discarding ends with its Quit."""
        if not self._asking:
            return
        self._asking = False
        self.changed.emit()
        if choice not in ('save', 'discard') or self.files is None:
            return
        self.files._pending = ('quit', None)
        self.files._confirmation = True
        self.files.resolveChanges(choice)

    def session_ends(self, _manager=None):
        """The system ends the session (QGuiApplication.commitDataRequest): no question, the recovery copy instead."""
        self.ending = True
        if self._asking:
            self._asking = False
            self.changed.emit()

    def close(self):
        if self._closed:
            return
        self._closed = True
        app = QGuiApplication.instance()
        if app is not None:
            try:
                app.commitDataRequest.disconnect(self.session_ends)
            except (RuntimeError, TypeError):
                pass


def install(engine, session, cache, window):
    controller = ClosingPart(engine, session, window)
    return Part('closing', controllers={'closing': controller}, bind=controller.bind, close=controller.close)
