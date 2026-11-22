"""Report navigation over synthetic pages, using the real Quick controls."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup
from _fixtures import capannone
from PySide6.QtCore import QObject, QPointF, Qt, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

from meridiana.app.platform import config
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.report import ReportBackend


setUpModule = _setup.keep_global_state


class Navigation(unittest.TestCase):
    def setUp(self):
        self.app = _setup.quick_app()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cfg = config.Config()
        self.config_path = Path(self.temp.name) / "config.json"
        self.backend = ReportBackend(ProjectSession(capannone()), self.cfg,
                                     paths={"cache": self.temp.name, "config_file": self.config_path})
        self.addCleanup(self.backend.close)
        self.backend._pages = [{"source": "", "ratio": 1.4, "page": str(i)} for i in range(1, 9)]
        self.backend._count = 8
        self.backend._outline = [dict(title="Overview", level=1, page=2),
                                 dict(title="Site", level=2, page=3),
                                 dict(title="Production", level=1, page=5)]
        self.view = QQuickView()
        self.addCleanup(self.view.close)
        self.theme = install_controls(self.view.engine())
        self.view.setInitialProperties({"backend": self.backend, "showInspector": False})
        with patch.object(ReportBackend, "setActive"):
            self.view.setSource(QUrl.fromLocalFile(str(
                _setup.ROOT / "src/meridiana/gui/qml/Meridiana/Report/ReportPage.qml")))
        self.assertEqual(self.view.status(), QQuickView.Status.Ready,
                         [e.toString() for e in self.view.errors()])
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.resize(1100, 760)
        self.view.show()
        self.assertTrue(_setup.wait_for(self.view.isExposed, 3000))
        self.root = self.view.rootObject()
        _setup.turn_events(self.app, 80)

    def item(self, name):
        item = self.root.findChild(QObject, name)
        self.assertIsNotNone(item, name)
        return item

    def click(self, item):
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
        QTest.mouseClick(self.view, Qt.LeftButton, Qt.NoModifier, point)

    def test_outline_click_scroll_follow_and_remember_closed(self):
        tree = self.item("reportOutline")
        self.assertEqual(tree.property("count"), 3)
        # The real shared tree's keyboard activation goes to the paragraph's page.
        tree.forceActiveFocus()
        QTest.keyClick(self.view, Qt.Key_Home)
        QTest.keyClick(self.view, Qt.Key_Down)
        preview = self.item("reportPreview")
        self.assertTrue(_setup.wait_for(lambda: preview.property("currentPage") == 3, 2000))
        animation = next(o for o in self.root.findChildren(QObject) if o.property("property") == "contentY")
        self.assertTrue(_setup.wait_for(lambda: not animation.property("running"), 2000))
        point = tree.mapToScene(QPointF(60, tree.property("rowHeight") * 2.5)).toPoint()
        QTest.mouseClick(self.view, Qt.LeftButton, Qt.NoModifier, point)
        self.assertTrue(_setup.wait_for(lambda: preview.property("currentPage") == 5, 2000),
                        (preview.property("currentPage"), tree.property("currentIndex"), point,
                         tree.property("rowHeight"), tree.height()))
        flick = preview.property("contentItem")
        flick.setProperty("contentY", 5 * 900)
        self.assertTrue(_setup.wait_for(lambda: tree.property("currentIndex") == 2, 2000))
        panel = self.item("reportOutlinePanel")
        panel.closed.emit()
        self.assertFalse(panel.property("visible"))
        self.assertFalse(config.load(self.config_path).report_outline_open)
        self.click(self.item("reportOutlineToggle"))
        self.assertTrue(panel.property("visible"))
        self.assertTrue(config.load(self.config_path).report_outline_open)

    def test_chapter_click_lights_its_row_at_once_and_jumps_in_one_go(self):
        """Daniel 21/11/2026: «il cambio di capitolo produce strani movimenti dell'evidenziatura, ed è lento». Before,
        the preview scrolled through the pages between with an animation: the light went through every chapter on
        its way and every page swept was asked to be drawn. Now the click lights its row and the page comes in the
        same turn of the window."""
        import time
        tree = self.item("reportOutline")
        preview = self.item("reportPreview")
        lit, pages = [], []
        tree.currentIndexChanged.connect(lambda: lit.append(tree.property("currentIndex")))
        preview.currentPageChanged.connect(lambda: pages.append(preview.property("currentPage")))
        asked = []
        self.backend.pageAsked.connect(asked.append)
        point = tree.mapToScene(QPointF(60, tree.property("rowHeight") * 2.5)).toPoint()
        started = time.perf_counter()
        QTest.mouseClick(self.view, Qt.LeftButton, Qt.NoModifier, point)
        spent = time.perf_counter() - started
        self.assertEqual(asked, [5])
        self.assertEqual(tree.property("currentIndex"), 2)
        self.assertEqual(preview.property("currentPage"), 5)
        self.assertEqual(lit, [2], "the light went through other rows on its way")
        self.assertEqual(pages, [5], "the preview walked through the pages between")
        self.assertLess(spent, 0.1, spent)
        # the paragraph of a chapter starting on the same page as another keeps the row chosen
        self.backend._outline = [dict(title="Overview", level=1, page=2),
                                 dict(title="Site", level=2, page=2),
                                 dict(title="Production", level=1, page=5)]
        self.backend.pagesChanged.emit()
        _setup.turn_events(self.app, 20)
        tree.select(1)
        self.assertEqual(preview.property("currentPage"), 2)
        _setup.turn_events(self.app, 20)
        self.assertEqual(tree.property("currentIndex"), 1)

    def test_page_field_and_preview_keys(self):
        field = self.item("reportGoToPage")
        preview = self.item("reportPreview")
        field.forceActiveFocus()
        field.selectAll()
        QTest.keyClick(self.view, Qt.Key_5)
        QTest.keyClick(self.view, Qt.Key_Return)
        self.assertTrue(_setup.wait_for(lambda: preview.property("currentPage") == 5, 2000))
        self.assertIn("5", self.item("reportPageNumber").property("text"))
        field.forceActiveFocus()
        QTest.keyClick(self.view, Qt.Key_Home)
        self.assertEqual(preview.property("currentPage"), 5)
        field.selectAll()
        QTest.keyClick(self.view, Qt.Key_0)
        self.assertFalse(field.property("acceptableInput"))
        QTest.keyClick(self.view, Qt.Key_Return)
        self.assertEqual(preview.property("currentPage"), 5)
        preview.forceActiveFocus()
        for key, modifiers, page in [(Qt.Key_PageDown, Qt.NoModifier, 6),
                                     (Qt.Key_PageUp, Qt.NoModifier, 5),
                                     (Qt.Key_End, Qt.NoModifier, 8),
                                     (Qt.Key_Home, Qt.NoModifier, 1),
                                     (Qt.Key_End, Qt.ControlModifier, 8),
                                     (Qt.Key_Home, Qt.ControlModifier, 1)]:
            QTest.keyClick(self.view, key, modifiers)
            self.assertTrue(_setup.wait_for(lambda page=page: preview.property("currentPage") == page, 2000), page)
        self.assertEqual(field.property("text"), "1")
        self.theme.configure({"reducedMotion": True})
        QTest.keyClick(self.view, Qt.Key_End)
        self.assertEqual(preview.property("currentPage"), 8)

    def test_new_preview_keeps_the_paragraph_when_its_page_moves(self):
        tree = self.item("reportOutline")
        tree.forceActiveFocus()
        QTest.keyClick(self.view, Qt.Key_Home)
        QTest.keyClick(self.view, Qt.Key_Down)
        preview = self.item("reportPreview")
        self.assertTrue(_setup.wait_for(lambda: preview.property("currentPage") == 3, 2000))
        old_outline = list(self.backend.outline)
        self.backend._incoming_outline = [dict(title="Preface", level=1, page=2),
                                          dict(title="Overview", level=1, page=5),
                                          dict(title="Site", level=2, page=6),
                                          dict(title="Production", level=1, page=8)]
        self.backend._swap = (list(self.backend.pages), 0, 8, Path(self.temp.name))
        self.backend._swap_step()
        self.assertEqual(self.backend.outline, old_outline)
        self.assertTrue(_setup.wait_for(lambda: self.backend._swap is None, 3000))
        self.assertTrue(_setup.wait_for(lambda: preview.property("currentPage") == 6, 2000))
        self.assertEqual(tree.property("currentIndex"), 2)
        self.backend._incoming_outline = [dict(title="Preface", level=1, page=2),
                                          dict(title="Overview", level=1, page=5),
                                          dict(title="Production", level=1, page=8)]
        self.backend._swap = (list(self.backend.pages), 0, 8, Path(self.temp.name))
        self.backend._swap_step()
        self.assertTrue(_setup.wait_for(lambda: self.backend._swap is None, 3000))
        self.assertTrue(_setup.wait_for(lambda: preview.property("currentPage") == 5, 2000))
        self.assertEqual(tree.property("currentIndex"), 1)
        # A different project must not inherit the old chapter or scroll position.
        self.backend._session_changed({"file"})
        self.assertTrue(_setup.wait_for(lambda: tree.property("count") == 0, 2000))
        self.assertTrue(_setup.wait_for(
            lambda: preview.property("contentItem").property("contentY") == 0, 2000))

    def test_navigation_is_translated_in_italian(self):
        from meridiana import i18n
        self.addCleanup(i18n.setup, i18n.language())
        i18n.setup("it")
        self.assertEqual(self.backend.labels["closeContents"], "Chiudi indice")
        self.assertEqual(self.backend.labels["goToPage"], "Vai alla pagina")
        self.assertEqual(self.backend.labels["pageOf"].format(n=3, total=8), "Pagina 3 di 8")

    def test_collapsing_the_current_paragraph_selects_its_chapter(self):
        tree = self.item("reportOutline")
        tree.forceActiveFocus()
        QTest.keyClick(self.view, Qt.Key_Home)
        QTest.keyClick(self.view, Qt.Key_Down)
        self.assertTrue(_setup.wait_for(lambda: self.item("reportPreview").property("currentPage") == 3, 2000))
        tree.toggle(0)
        self.assertEqual(tree.property("currentIndex"), 0)

    @unittest.skipUnless(os.environ.get("MERIDIANA_NAV_CAPTURE"), "opt-in offscreen photographs")
    def test_capture_synthetic_preview(self):
        from PySide6.QtGui import QFont, QPainter, QPdfWriter
        from meridiana.gui.backend import report_pages
        path = Path(self.temp.name) / "synthetic.pdf"
        writer = QPdfWriter(str(path))
        writer.setResolution(72)
        painter = QPainter(writer)
        for i in range(1, 9):
            if i > 1:
                writer.newPage()
            painter.setFont(QFont("Arial", 11))
            painter.drawText(40, 45, "MERIDIANA  /  SYNTHETIC EXAMPLE")
            painter.setFont(QFont("Arial", 22))
            painter.drawText(40, 110, {2: "Overview", 3: "Site", 5: "Production"}.get(i, "Technical report"))
            painter.setFont(QFont("Arial", 12))
            for line, text in enumerate(["Navigation example with invented data.",
                                         "Chapters and paragraphs follow the preview.",
                                         "No customer, project or professional profile is used."]):
                painter.drawText(40, 160 + 24 * line, text)
            painter.drawText(40, 740, f"Page {i} of 8")
        painter.end()
        self.backend._pages = report_pages.publish([
            dict(path=str(path), index=i, ratio=297 / 210, page=str(i + 1)) for i in range(8)])
        self.backend._data = {"sim": {}}
        self.backend.session.energy = {"sim": {}}
        self.backend.session.energy_key_computed = self.backend.session.expected_key()
        self.backend._state = None
        self.backend.contentChanged.emit()
        self.backend.changed.emit()
        self.backend.pagesChanged.emit()
        self.view.resize(1366, 900)
        _setup.turn_events(self.app, 100)
        tree = self.item("reportOutline")
        tree.forceActiveFocus()
        QTest.keyClick(self.view, Qt.Key_Home)
        QTest.keyClick(self.view, Qt.Key_Down)
        self.assertTrue(_setup.wait_for(lambda: self.item("reportPreview").property("currentPage") == 3, 2000))
        self.assertTrue(_setup.wait_for(lambda: bool(report_pages.drawn), 5000))
        folder = _setup.ROOT / "build/r36-relazione-indice"
        folder.mkdir(parents=True, exist_ok=True)
        scale = os.environ.get("QT_SCALE_FACTOR", "1")
        for mode in ("light", "dark"):
            self.theme.configure({"theme": mode})
            # Deliver a fresh preview in each theme. The image provider hands each
            # drawing over once; a second high-DPI offscreen grab can request it again.
            self.backend._pages = report_pages.publish([
                dict(path=str(path), index=i, ratio=297 / 210, page=str(i + 1)) for i in range(8)])
            self.backend.pagesChanged.emit()
            _setup.turn_events(self.app, 500)
            image = self.view.grabWindow()
            self.assertFalse(image.isNull())
            self.assertTrue(image.save(str(folder / f"report-{mode}-s{scale}.png")))

