"""The help next to things, without Meridio (R596, R597; study 47): what the bubble of a «?» says and what its two
buttons do. The texts are app/interface/help.py's, by key; the bubble is Controls/HelpBubble.qml, opened by the one
entry Controls/Help.qml (`Help.show(key, mark)`) from the sections, the result tiles, the card's «?», the help key and «What's
this?». This backend never looks for an item of the window: the QML asks it for an entry and binds `cardKey`.

«Open in the manual» waits for the manual in the File page (study 47, P4): until then MANUAL_PAGE is False and the
entries carry no manual section, so the bubble does not show the button. «Ask Meridio» opens the conversation with
the key's question written in its field, and is not offered while Meridio is off in the settings."""
from PySide6.QtCore import QObject, Property, Signal, Slot

from meridiana.app.interface import help as helps
from meridiana.i18n import _

from .parts import Part

# P4 (study 47): the manual read in the File page, with its index and its search. The one switch of «Open in the
# manual»: off, no entry names a section and the button is not drawn.
MANUAL_PAGE = False

# the card's «?» (the panel on the right): what is selected in Modelling, else the phase
CARD_KINDS = ('site', 'building', 'subfield', 'exclusion')


class HelpBook(QObject):
    changed = Signal()
    manualRequested = Signal(str)

    def __init__(self, session, window):
        super().__init__()
        self.session, self.window = session, window
        self._phase = 'model'
        self._card_key = 'phase.model'
        self.chat = None
        session.subscribe(self._session_changed)

    def _session_changed(self, topics):
        if 'selection' in topics or 'file' in topics:
            self._update_card()

    def _update_card(self):
        kind = self.session.selection[0]
        key = kind if self._phase == 'model' and kind in CARD_KINDS else helps.for_phase(self._phase)
        if key != self._card_key:
            self._card_key = key
            self.changed.emit()

    def _get_phase(self):
        return self._phase

    def _set_phase(self, phase):
        if phase != self._phase:
            self._phase = phase
            self._update_card()

    # the phase shown, written by Workbench.qml (a Binding): the card's «?» explains it
    phase = Property(str, _get_phase, _set_phase, notify=changed)

    @Property(str, notify=changed)
    def cardKey(self):
        return self._card_key

    @Property(bool, notify=changed)
    def canAsk(self):
        """«Ask Meridio» is offered: Meridio is installed and on in the settings."""
        cfg = getattr(self.window, 'cfg', None)
        return self.chat is not None and bool(getattr(cfg, 'assistant', True))

    @Property('QVariantMap', constant=True)
    def labels(self):
        return dict(manual=_('Open in the manual'), ask=_('Ask Meridio'))

    @Slot(str, result=str)
    def tip(self, key):
        """The tooltip of a «?»: the short sentence of its help."""
        found = helps.get(key, profile_id=self.session.project.regulatory_profile)
        return found.short if found is not None else ''

    @Slot(str, result='QVariantMap')
    def entry(self, key):
        """What the bubble shows for `key`: the text, the source line when there is one, the manual's section when
        the manual can be opened (MANUAL_PAGE); empty for a key without help, said in the status bar."""
        found = helps.get(key, profile_id=self.session.project.regulatory_profile)
        if found is None:
            self.window.shell.show_notice(_('No help for this item.'))
            return {}
        sources = helps.sources(found, profile_id=self.session.project.regulatory_profile)
        return dict(key=key, text=found.text,
                    source=_('Source') + ': ' + '; '.join(sources) if sources else '',
                    manual=found.manual if MANUAL_PAGE else '')

    @Slot(str)
    def ask(self, key):
        """«Ask Meridio»: the conversation opens with the key's question in its field."""
        found = helps.get(key, profile_id=self.session.project.regulatory_profile)
        if found is None or self.chat is None:
            return
        self.chat.openRequested.emit()
        self.chat.setDraft(helps.question(found))

    @Slot(str)
    def openManual(self, section):
        """«Open in the manual» (shown only with MANUAL_PAGE): the File page opens the section (P4)."""
        self.manualRequested.emit(section)

    def bind(self, root):
        controllers = self.window.parts.controllers
        self.chat = controllers.get('assistant')
        settings = controllers.get('settings')
        if settings is not None:
            settings.changed.connect(self._settings_changed)
        self._update_card()
        self.changed.emit()

    def _settings_changed(self, key, _value):
        if key == 'assistant':
            self.changed.emit()

    def close(self):
        if self._session_changed in self.session.listeners:
            self.session.listeners.remove(self._session_changed)


def install(engine, session, cache, window):
    book = HelpBook(session, window)
    engine.rootContext().setContextProperty('helpBook', book)
    return Part('help', controllers={'help': book}, bind=book.bind, close=book.close)
