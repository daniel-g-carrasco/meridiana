"""Nothing in a card is wider than the card (Daniel, 02/11/2026, on the Settings > Assistant page at about 1000 px:
«c'è qualche problema di impaginazione e nel mostrare tasti (e quel rettangolino tra le due barre di scorrimento) ...
verifichiamo bene di non aver fatto altre cavolate»). A long checkbox held the page wider than its scroll area: a
horizontal bar, the corner square between the two bars, the texts cut on the right, the arrow of a list out of sight.

The window at 1000 x 980 and at 1366 x 768, in English and in Italian (longer: the catalogue compiled in locale/,
else that half is skipped), every section of File, every section of the Settings and every phase with its columns:
- no scroll area that fits its page to its width shows a horizontal bar;
- no wrapped label goes past the right edge of the scroll area it stands in;
- no label, checkbox or button on one line is narrower than its text (cut, or elided by Qt where nobody chose it).
A failure names the place, the widget and the widest thing inside it."""

import unittest

import _setup
from _fixtures import capannone

setUpModule = _setup.keep_global_state

SIZES = ((1000, 980), (1366, 768))
PHASES = ("model", "plant", "production", "consumption", "economics", "report")


def name(widget) -> str:
    text = getattr(widget, "text", None)
    text = text() if callable(text) else ""
    return f"{type(widget).__name__}{'#' + widget.objectName() if widget.objectName() else ''} {text[:50]!r}"


def widest(root):
    """The visible widget under `root` that asks for the most width: the one to look at first."""
    from PySide6.QtWidgets import QWidget
    best = None
    for w in root.findChildren(QWidget):
        if w.isVisible() and (not w.findChildren(QWidget) or w.layout() is None):
            need = max(w.minimumSizeHint().width(), w.minimumWidth())
            if best is None or need > best[0]:
                best = (need, name(w))
    return best


def problems(win, where: str) -> list:
    from PySide6.QtCore import QPoint
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QAbstractButton, QLabel, QScrollArea, QSizePolicy, QToolButton
    # what a page took away and left to deleteLater is still there, shown, until the loop deletes it: the program's
    # loop does at once, processEvents never does
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    found = []
    for area in win.findChildren(QScrollArea):
        page = area.widget()
        if not area.isVisible() or not area.widgetResizable() or page is None:
            continue
        port = area.viewport()
        if area.horizontalScrollBar().isVisible() or page.width() > port.width() + 1:   # a bar always off: cut
            found.append((where, "page wider than its card", name(area.parentWidget() or area), page.width(),
                          port.width(), widest(page)))
        for label in page.findChildren(QLabel):
            if label.isVisible() and label.wordWrap():
                right = label.mapTo(port, QPoint(label.width(), 0)).x() - page.mapTo(port, QPoint(0, 0)).x()
                if right > port.width() + 1:
                    found.append((where, "label past its card", name(label), right, port.width()))
    for w in win.findChildren(QLabel) + win.findChildren(QAbstractButton):
        if not w.isVisible() or isinstance(w, QToolButton) or not w.text().strip():
            continue
        if isinstance(w, QLabel) and (w.wordWrap() or w.pixmap() is not None and not w.pixmap().isNull()):
            continue
        if w.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Ignored:
            continue                # cut by choice: the status bar's texts never keep the window from narrowing
        need = w.minimumSizeHint().width()
        if w.width() + 1 < need:
            found.append((where, "cut", name(w), w.width(), need))
    return found


class PageFit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def sweep(self) -> list:
        win, found = self.win, []
        for width, height in SIZES:
            win.resize(width, height)
            _setup.turn_events(self.app, 60)
            for phase in PHASES:
                win.show_phase(phase)
                _setup.turn_events(self.app, 60)
                found += problems(win, f"{width}x{height} {phase}")
            win.open_file_page("open")
            _setup.turn_events(self.app, 60)
            page = win.file_page
            keys = [k for k in page.sections if k != "preferences"]
            keys += ["preferences:" + k for k in page.settings._widgets()]
            for key in keys:
                page._select_section(key)
                _setup.turn_events(self.app, 60)
                found += problems(win, f"{width}x{height} file:{key}")
            page.close_page()
            _setup.turn_events(self.app, 60)
        return found

    def test_english(self):
        _setup.window(self, capannone())
        self.assertEqual(self.sweep(), [])

    def test_italian(self):
        import gettext

        from meridiana import i18n
        if type(i18n.translation_for("it")) is gettext.NullTranslations:
            self.skipTest("no Italian catalogue in locale/ (tools/compile_po.py)")
        i18n.setup("it")
        _setup.window(self, capannone())
        self.assertEqual(self.sweep(), [])


if __name__ == "__main__":
    unittest.main()
