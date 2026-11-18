"""Help, internal manual and guided-tour content for the Quick assistant.

Geometry belongs to AssistantLayer.qml. This service only changes on a command,
never during a pointer move, layout animation or spotlight pulse.
"""
from __future__ import annotations

from dataclasses import asdict

from PySide6.QtCore import QObject, Property, Signal, Slot

from meridiana import help as helps, tour
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
        self._chapters = []
        root = helps.manual_dir()
        if root:
            for chapter in helps.CHAPTERS:
                path = root / chapter
                if path.is_file():
                    self._chapters.append({'id': chapter, 'title': helps.chapter_title(path.read_text(encoding='utf-8'))})

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
                    start=_('Start'), steps=_('Jump to another step of the tour'), tryHint=_('Try:'))

    @Property('QVariantList', constant=True)
    def tourSteps(self):
        return [dict(index=i, title=f'{i+1}. {step.title}') for i, step in enumerate(tour.steps())]

    @Slot(str, result=bool)
    def request(self, key):
        item = helps.get(key)
        if item is None:
            return False
        self._content = {**asdict(item), 'id': key, 'sources': helps.sources(item)}
        self.changed.emit()
        self.requested.emit()
        return True

    @Slot()
    def ask(self):
        item = helps.get(self._content.get('id', ''))
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
        root = helps.manual_dir()
        if not root or chapter not in helps.CHAPTERS:
            return False
        path = root / chapter
        if not path.is_file():
            return False
        self._manual = path.read_text(encoding='utf-8')
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

    @Property(int, notify=tourChanged)
    def tourIndex(self):
        return self._index

    @Property('QVariantMap', notify=tourChanged)
    def tourStep(self):
        items = tour.steps()
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
        self.navigateRequested.emit(list(tour.steps()[self._index].target))

    @Slot(bool)
    def startTour(self, resume=False):
        self._index = min(max(0, int(getattr(self.cfg, 'tour_step', 0))) if resume else 0, len(tour.steps()) - 1)
        self._active = True
        self._show_step()

    @Slot(int)
    def goToStep(self, index):
        if 0 <= index < len(tour.steps()):
            self._index = index
            self._active = True
            self._show_step()

    @Slot()
    def next(self):
        if not self._active:
            return
        if self._index == len(tour.steps()) - 1:
            self._active = False
            self._save_tour('done')
            self.tourChanged.emit()
            self.dismissed.emit()
        else:
            self._index += 1
            self._show_step()

    @Slot()
    def previous(self):
        if self._active and self._index:
            self._index -= 1
            self._show_step()

    @Slot()
    def pauseTour(self):
        if self._active:
            self._active = False
            self._save_tour('paused')
            self.tourChanged.emit()
            self.dismissed.emit()
