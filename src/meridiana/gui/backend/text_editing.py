"""Shared GUI text commands. No project or assistant state belongs here."""
import math
import re

from PySide6.QtCore import Q_ARG, QCoreApplication, QEvent, QMetaObject, QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication, QInputMethodEvent, QKeySequence, QTextDocument
from shiboken6 import isValid

from meridiana.i18n import _


class _ShortcutGuard(QObject):
    """Qt's read-only TextInput declines ShortcutOverride before its QML Keys handler.

    Claim editing keys once, before window/project shortcuts. Actual editor operations still use
    TextActions; no duplicate QShortcut objects are installed.

    R706: the filter is on what the keys are for and nothing else: the text item that has the focus (a
    key goes to it first, ShortcutOverride included) and, while a text menu is open, the windows (the
    focus may then be anywhere). It was on the application: every event of every object of the program
    (timers, repaints, queued calls, the pointer) entered Python, and each waited for the interpreter
    whenever a Python thread was at work: 1.8 s of the window's thread in a zoom of a 10 000-module plan.
    """
    def __init__(self, app):
        super().__init__(app)
        self.actions = self.menu = None
        self._item = None               # the text item watched: the one with the focus
        self._windows = []              # the windows watched while a text menu is open
        app.focusObjectChanged.connect(self._follow)
        self._follow(app.focusObject())

    def _follow(self, focus):
        """Watch the item with the focus when it is a text item of ours, and no other."""
        if self._item is not None and isValid(self._item):
            self._item.removeEventFilter(self)
        self._item = focus if focus is not None and focus.property('textKeysEnabled') is not None else None
        if self._item is not None:
            self._item.installEventFilter(self)

    def watch_windows(self, on: bool) -> None:
        """While a text menu is open its keys are claimed wherever the focus is: at the windows."""
        for window in self._windows:
            if isValid(window):
                window.removeEventFilter(self)
        self._windows = list(QGuiApplication.allWindows()) if on else []
        for window in self._windows:
            window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() not in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            return False
        focus = QGuiApplication.focusObject()
        editor = focus is not None and focus.property('textKeysEnabled') is True
        active = self.actions is not None and isValid(self.actions) and self.menu is not None and isValid(self.menu)
        if self._windows and not active:
            self.watch_windows(False)       # the menu went without saying so
        if not editor and not active:
            return False
        command = next((name for key, name in (
            (QKeySequence.StandardKey.Undo, 'undo'), (QKeySequence.StandardKey.Redo, 'redo'),
            (QKeySequence.StandardKey.Cut, 'cut'), (QKeySequence.StandardKey.Copy, 'copy'),
            (QKeySequence.StandardKey.Paste, 'paste'), (QKeySequence.StandardKey.SelectAll, 'selectAll'))
            if event.matches(key)), None)
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            command = 'delete'
        if command is None:
            return False
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True
        if active:
            actions, menu = self.actions, self.menu
            QMetaObject.invokeMethod(actions, 'execute', Q_ARG('QVariant', command))
            if isValid(menu):
                QMetaObject.invokeMethod(menu, 'close')
            event.accept()
            return True
        return False


def _guard():
    app = QGuiApplication.instance()
    if not hasattr(app, '_text_shortcut_guard'):
        app._text_shortcut_guard = _ShortcutGuard(app)
    return app._text_shortcut_guard


class TextEditing(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._guard = _guard()
        QGuiApplication.clipboard().dataChanged.connect(self.changed)

    @Slot(QObject, QObject)
    def activateMenu(self, actions, menu):
        self._guard.actions, self._guard.menu = actions, menu
        self._guard.watch_windows(True)

    @Slot(QObject)
    def deactivateMenu(self, menu):
        if self._guard.menu == menu:
            self._guard.actions = self._guard.menu = None
            self._guard.watch_windows(False)

    @Property('QVariantMap', notify=changed)
    def labels(self):
        return dict(description=_("Copy description"), name=_("Copy name"), cell=_("Copy cell"),
                    close=_("Close"), noPageText=_("This page has no selectable text"),
                    rows=_("Copy selected rows"), values=_("Copy values"), formula=_("Copy formula (LaTeX)"),
                    page=_("Copy page text"), readPage=_("Read page text\u2026"),
                    undo=_("Undo"), redo=_("Redo"), cut=_("Cut"), copy=_("Copy"),
                    paste=_("Paste"), delete=_("Delete"), selectAll=_("Select all"),
                    whole=_("Copy all"), message=_("Copy message"), markdown=_("Copy as Markdown"))

    @Slot(str, result=str)
    def shortcut(self, command):
        keys = dict(undo='Undo', redo='Redo', cut='Cut', copy='Copy', paste='Paste',
                    delete='Delete', selectAll='SelectAll')
        key = keys.get(command)
        if not key:
            return ''
        bindings = QKeySequence.keyBindings(getattr(QKeySequence.StandardKey, key))
        return bindings[0].toString(QKeySequence.SequenceFormat.NativeText) if bindings else ''

    @Property(bool, notify=changed)
    def canPaste(self):
        mime = QGuiApplication.clipboard().mimeData()
        return bool(mime and (mime.hasText() or mime.hasImage() or mime.hasUrls()))

    @Slot(result=str)
    def clipboardText(self):
        return QGuiApplication.clipboard().text()

    @Slot(str)
    def copy(self, text):
        QGuiApplication.clipboard().setText(text)

    @Slot(QObject, str)
    def replaceSelection(self, editor, text):
        event = QInputMethodEvent()
        event.setCommitString(text)
        QCoreApplication.sendEvent(editor, event)

    @Slot(QObject, int, result='QVariantMap')
    def modelRow(self, model, row):
        if not 0 <= row < model.rowCount():
            return {}
        index = model.index(row, 0)
        return {bytes(name).decode(): model.data(index, role) for role, name in model.roleNames().items()}

    @Slot(str, result=str)
    def plainHtml(self, text):
        document = QTextDocument()
        document.setHtml(text)
        return document.toPlainText()

    @Slot(str, str, str, float, float, int, result='QVariantMap')
    def numeric(self, text, unit, kind, minimum, maximum, decimals):
        from meridiana.app.interface import quantity
        raw = text.replace('\u00a0', ' ').replace('\u2212', '-').strip()
        try:
            if '\n' in text or '\r' in text:
                raise ValueError('multiline')
            if kind:
                value = quantity.parse(raw, kind, unit)
            else:
                if unit and raw.endswith(unit):
                    raw = raw[:-len(unit)].rstrip()
                if not re.fullmatch(r'[+-]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][+-]?\d+)?', raw):
                    raise ValueError('number')
                if re.fullmatch(r'[+-]?[1-9]\d{0,2}\.\d{3}', re.split('[eE]', raw)[0]):
                    raise ValueError('ambiguous')
                value = float(raw.replace(',', '.'))
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValueError('range')
            if not kind and not math.isclose(value, round(value, max(0, decimals)), rel_tol=0, abs_tol=1e-12):
                raise ValueError('precision')
            shown = f'{value:.{max(0, min(15, decimals))}f}'.rstrip('0').rstrip('.') if decimals else str(round(value))
            return {'ok': True, 'text': shown, 'value': value}
        except (ValueError, OverflowError):
            return {'ok': False, 'text': text, 'error': _("Invalid number or incompatible unit")}


def install(engine):
    if not hasattr(engine, '_text_editing'):
        engine._text_editing = TextEditing(engine)
        engine.rootContext().setContextProperty('textEditing', engine._text_editing)
