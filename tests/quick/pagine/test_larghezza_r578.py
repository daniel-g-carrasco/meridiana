"""R578: every page of File and of the Settings stops at one width, Theme.layout.PAGE_WIDTH (design.Layout).

Daniel (11/11/2026, File > Apri): «guarda quanto cavolo è lunga questa casella… alle pagine in File e nelle
impostazioni ci deve essere un limite di larghezza complessivo». On a window 2200 px wide, every section that the
navigation of File and of the Settings lists (read from the page: a section added later is checked too) is shown,
and no text and no control of the page on the right ends past the page's margin plus PAGE_WIDTH (the scroll bars,
which keep to the window's side, aside).
"""
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtQuick import QQuickItem
from PySide6.QtCore import QObject, QPointF
from PySide6.QtTest import QTest

from meridiana.gui.style.design import Layout

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

SKIP = ('back', 'settingsBack', 'stretch', 'quit', 'preferences')


class PageWidth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.gui.backend.files_page import build_page
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.host = build_page('file', folder=Path(self.tmp.name))
        self.addCleanup(self.host.close)
        recent = Path(self.tmp.name) / 'Un_progetto_dal_nome_lungo_R03.meridiana'
        recent.write_text('{}')
        self.host.files.cfg.recent = [str(recent)]
        self.host.files.stateChanged.emit()
        self.window = self.host.window
        self.window.resize(2200, 900)
        self.window.show()
        QTest.qWait(300)

    def sections(self):
        names, pending = [], [self.window.contentItem()]
        while pending:
            item = pending.pop()
            pending.extend(c for c in item.childItems() if isinstance(c, QQuickItem))  # on Linux PySide hands back a child typed QMetaObject now and then: items only
            name = item.objectName()
            if name.startswith('fileNav_') and item.isVisible():
                entry = name.removeprefix('fileNav_')
                if not entry.startswith('rule') and entry not in SKIP:
                    names.append(entry)
        return names

    def overflow(self, right, limit):
        """The texts and the controls of the page that end past the limit (scene x), with where they end."""
        found, pending = [], list(right.childItems())
        while pending:
            item = pending.pop()
            if not item.isVisible() or item.opacity() <= 0 or item.width() <= 0:
                continue
            kind = item.metaObject().className()
            if 'ScrollBar' in kind:
                continue
            pending.extend(c for c in item.childItems() if isinstance(c, QQuickItem))  # on Linux PySide hands back a child typed QMetaObject now and then: items only
            if item.inherits('QQuickText') or item.inherits('QQuickTextInput') or item.inherits('QQuickControl'):
                end = item.mapToScene(QPointF(item.width(), 0)).x()
                if end > limit + .5:
                    found.append(f'{kind.split("_QML")[0]}:{item.objectName()}:{end:.0f}')
        return found

    def test_every_page_of_file_and_settings_stops_at_the_page_width(self):
        page = self.window.findChild(QObject, 'filePage')
        right = self.window.findChild(QObject, 'fileRight')
        margin = self.host.files.metrics['pageX']
        limit = right.mapToScene(QPointF(0, 0)).x() + 2 * margin + Layout.PAGE_WIDTH
        checked = []
        for prefix, first in (('', 'open'), ('preferences:', 'preferences:appearance')):
            self.host.files.selectSection(first)
            QTest.qWait(400)
            for entry in self.sections():
                section = prefix + entry
                self.host.files.selectSection(section)
                self.assertTrue(_setup.wait_until(self.app, lambda s=section: page.property('displayedSection') == s
                                                  and not page.property('changing')), section)
                QTest.qWait(250)
                self.assertFalse(self.overflow(right, limit), section)
                checked.append(section)
        self.assertGreaterEqual(len(checked), 12, checked)


if __name__ == '__main__':
    unittest.main()
