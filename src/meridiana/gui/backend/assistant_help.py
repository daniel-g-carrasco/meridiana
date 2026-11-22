"""Help, internal manual and guided-tour content for the Quick assistant.

Geometry belongs to AssistantLayer.qml. This service only changes on a command,
never during a pointer move, layout animation or the spotlight's arrival.
"""
from __future__ import annotations

from dataclasses import asdict

from PySide6.QtCore import QObject, Property, Signal, Slot

from meridiana.app.interface import help as helps, tour
from meridiana.i18n import _


class AssistantHelp(QObject):
    changed = Signal()
    requested = Signal()
    manualOpened = Signal()
    tourChanged = Signal()
    askRequested = Signal(str)
    howRequested = Signal(str)
    navigateRequested = Signal(list)
    dismissed = Signal()

    def __init__(self, parent=None, *, cfg=None, save=lambda: None):
        super().__init__(parent)
        self.cfg, self.save = cfg, save
        self._content = {}
        self._manual = ''
        self._chapter = ''
        self._anchor = ''
        self._index = 0
        self._active = False
        self._invitation = False         # the welcome before the first step, offered at the first start
        self._chapters = []
        for chapter in helps.CHAPTERS:
            sections = helps.manual_sections(chapter)
            if sections:
                self._chapters.append({'id': chapter, 'title': sections[0][1]})

    @Property('QVariantMap', notify=changed)
    def content(self):
        return self._content

    @Property('QVariantList', constant=True)
    def chapters(self):
        return self._chapters

    @Property(str, notify=changed)
    def manualText(self):
        return self._manual

    @Property(str, notify=changed)
    def manualChapter(self):
        return self._chapter

    @Property(str, notify=changed)
    def manualAnchor(self):
        return self._anchor

    @Property('QVariantMap', constant=True)
    def labels(self):
        return dict(manual=_('Manual'), ask=_('Ask Meridio'), how=_('How it is computed'),
                    previous=_('Previous'), next=_('Next'), later=_('Later'), finish=_('Finish'),
                    close=_('Close'), source=_('Source'), tour=_('Guided tour'), pause=_('Pause tour'),
                    start=_('Start'), steps=_('Jump to another step of the tour'), tryHint=_('Try:'),
                    startTour=_('Start tour'))

    @Property('QVariantList', constant=True)
    def tourSteps(self):
        return [dict(index=i, title=f'{i+1}. {step.title}') for i, step in enumerate(tour.steps(profile_id=self._profile_id()))]

    def _profile_id(self):
        session = getattr(self.parent(), "session", None)
        return session.project.regulatory_profile if session is not None else "it"

    def sync_profile(self):
        key = self._content.get("id", "")
        if key and not self.request(key):
            self._content = {}
            self.changed.emit()

    @Slot(str, result=bool)
    def request(self, key):
        item = helps.get(key, profile_id=self._profile_id())
        if item is None:
            return False
        self._content = {**asdict(item), 'id': key, 'sources': helps.sources(item, profile_id=self._profile_id())}
        self.changed.emit()
        self.requested.emit()
        return True

    @Slot()
    def ask(self):
        item = helps.get(self._content.get('id', ''), profile_id=self._profile_id())
        if item:
            self.askRequested.emit(helps.question(item))

    @Slot()
    def how(self):
        if self._content.get('pedigree'):
            self.howRequested.emit(self._content['pedigree'])

    @Slot(str, result=bool)
    def openManual(self, reference):
        chapter, anchor = helps.split(reference)
        chapter = chapter or self._chapter or 'README.md'
        text = helps.manual_text(chapter)
        if not text:
            return False
        self._manual = text
        self._chapter, self._anchor = chapter, anchor
        self.changed.emit()
        self.manualOpened.emit()
        return True

    @Slot(str, result=int)
    def anchorPosition(self, anchor):
        """Approximate text offset for Quick TextEdit.positionToRectangle.

        QTextDocument supplies the exact rendered character positions to QML;
        this method uses the same Markdown parser to avoid raw-source offsets.
        """
        from PySide6.QtGui import QTextDocument
        doc = QTextDocument()
        doc.setMarkdown(self._manual)
        for (_level, heading), slug in zip(helps.headings(self._manual), helps.anchors(self._manual), strict=True):
            if slug == anchor:
                found = doc.find(heading)
                return found.selectionStart() if not found.isNull() else 0
        return 0

    @Slot(str, result=bool)
    def followLink(self, reference):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        url = QUrl(reference)
        if url.scheme() in ('https', 'http'):
            return QDesktopServices.openUrl(url)
        return self.openManual(reference)

    @Property(bool, notify=tourChanged)
    def tourActive(self):
        return self._active

    @Property(bool, notify=tourChanged)
    def tourInvitation(self):
        return self._invitation

    @Property(int, notify=tourChanged)
    def tourIndex(self):
        return self._index

    @Property('QVariantMap', notify=tourChanged)
    def tourStep(self):
        items = tour.steps(profile_id=self._profile_id())
        if self._invitation:
            return dict(id='welcome', title=_('Let Meridio show you around'), progress=_('Welcome'),
                        text=_('I am Meridio, the small sun of this program. In thirteen short stops I show you the '
                               'phases, the tools and the settings, and what each one is for. Stop whenever you '
                               'like and pick up again from Help, or by asking me. Your project stays as it is.'),
                        points=[_('About three minutes, at your pace.'), _('Previous and Next move between the stops.'),
                                _('Pause tour keeps your place for next time.')],
                        hint='', target=[], number=0, total=len(items))
        step = items[self._index]
        return {**asdict(step), 'points': list(step.points), 'target': list(step.target),
                'number': self._index + 1, 'total': len(items),
                'progress': _('Step {current} of {total}').format(current=self._index + 1, total=len(items))}

    def _save_tour(self, status):
        if self.cfg is not None:
            self.cfg.tour_status, self.cfg.tour_step = status, self._index
            self.save()

    def _show_step(self):
        self._save_tour('active')
        self.tourChanged.emit()
        self.navigateRequested.emit(list(tour.steps(profile_id=self._profile_id())[self._index].target))

    @Slot(result=bool)
    def offerTour(self):
        """The first start (tour_status «new»): Meridio opens with a welcome, «Start tour» or «Later» (r29's TourDialog
        with invitation=True). «Later» marks the tour skipped: it is not offered again,
        it stays in Help and in Meridio's menu. True when the welcome is shown."""
        if self.cfg is None or getattr(self.cfg, 'tour_status', 'new') != 'new' or self._active:
            return False
        self._invitation = self._active = True
        self.tourChanged.emit()
        return True

    @Slot(bool)
    def startTour(self, resume=False):
        self._index = min(max(0, int(getattr(self.cfg, 'tour_step', 0))) if resume else 0, len(tour.steps(profile_id=self._profile_id())) - 1)
        self._invitation = False
        self._active = True
        self._show_step()

    @Slot(int)
    def goToStep(self, index):
        if 0 <= index < len(tour.steps(profile_id=self._profile_id())):
            self._invitation = False
            self._index = index
            self._active = True
            self._show_step()

    @Slot()
    def next(self):
        if not self._active:
            return
        if self._invitation:
            self.startTour(False)
            return
        if self._index == len(tour.steps(profile_id=self._profile_id())) - 1:
            self._active = False
            self._save_tour('done')
            self.tourChanged.emit()
            self.dismissed.emit()
        else:
            self._index += 1
            self._show_step()

    @Slot()
    def previous(self):
        if self._active and self._index and not self._invitation:
            self._index -= 1
            self._show_step()

    @Slot()
    def pauseTour(self):
        if self._active:
            self._active = False
            self._save_tour('skipped' if self._invitation else 'paused')
            self._invitation = False
            self.tourChanged.emit()
            self.dismissed.emit()
