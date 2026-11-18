"""The texts the window shows hold only characters Inter draws, or are in the font of the symbols
(theme.mark, theme.symbol_font): the first character Qt has to look for in another font costs it 1-2 s on
Windows, once a process (23/10/2026). The characters the font has are read from its file with QRawFont; the
font of the symbols is set as on Windows, where it matters. PySide6 and a display (offscreen will do)."""

import unittest
from unittest import mock

import _setup

from meridiana import paths

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

SYMBOLS = "Segoe UI Symbol"


def texts_of(widget) -> list[tuple[str, str, bool]]:
    """(where, text, rich) for what a widget and its children show."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QAbstractButton, QComboBox, QDockWidget, QGroupBox, QLabel, QLineEdit, QTabBar,
                                   QTableView, QTableWidget, QTextEdit, QTreeWidget, QWidget)
    out = []
    for w in [widget] + widget.findChildren(QWidget):
        name = type(w).__name__
        if w.toolTip():
            out.append((name + " tooltip", w.toolTip(), True))
        if isinstance(w, QLabel):
            out.append((name, w.text(), "<" in w.text()))
        elif isinstance(w, QAbstractButton) and w.font().family() != SYMBOLS:
            out.append((name, w.text(), False))
        elif isinstance(w, QLineEdit):
            out += [(name, w.text(), False), (name + " placeholder", w.placeholderText(), False)]
        elif isinstance(w, QGroupBox):
            out.append((name, w.title(), False))
        elif isinstance(w, QDockWidget):
            out.append((name, w.windowTitle(), False))
        elif isinstance(w, QTabBar):
            out += [(name, w.tabText(i), False) for i in range(w.count())]
        elif isinstance(w, QComboBox):
            out += [(name, w.itemText(i), False) for i in range(w.count())]
        elif isinstance(w, QTextEdit):
            out.append((name, w.toHtml(), True))
        elif isinstance(w, QTreeWidget):
            stack = [w.topLevelItem(i) for i in range(w.topLevelItemCount())]
            while stack:
                it = stack.pop()
                out += [(name, it.text(c), False) for c in range(w.columnCount()) if it.font(c).family() != SYMBOLS]
                stack += [it.child(i) for i in range(it.childCount())]
        elif isinstance(w, QTableView) and not isinstance(w, QTableWidget) and w.model() is not None:
            m = w.model()                                   # a model's table: its header and the rows first seen
            for c in range(m.columnCount()):
                out.append((name + " header", str(m.headerData(c, Qt.Orientation.Horizontal) or ""), False))
                out += [(name, str(m.index(r, c).data() or ""), False) for r in range(min(m.rowCount(), 400))]
        elif isinstance(w, QTableWidget):
            for c in range(w.columnCount()):
                head = w.horizontalHeaderItem(c)
                if head is not None:
                    out.append((name + " header", head.text(), False))
                for r in range(w.rowCount()):
                    if w.item(r, c) is not None:
                        out.append((name, w.item(r, c).text(), False))
    return out


def shown(text: str, rich: bool) -> str:
    """The characters drawn in the font of the window: those in the symbols' font are left out."""
    if not rich:
        return text
    from PySide6.QtGui import QTextDocument
    doc = QTextDocument()
    doc.setHtml(text)
    out = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            families = frag.charFormat().fontFamilies() or []
            if SYMBOLS not in families:
                out.append(frag.text())
            it += 1
        block = block.next()
    return "".join(out)


class Glyphs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QRawFont
        cls.app = _setup.qt_or_skip()
        cls.font = QRawFont(str(paths.shipped("fonts", "inter", "Inter-Regular.ttf")), 12)
        if not cls.font.isValid():
            raise unittest.SkipTest("Inter is not there")

    def setUp(self):
        patcher = mock.patch("meridiana.ui.theme.SYMBOL_FAMILY", SYMBOLS)    # as on Windows
        patcher.start()
        self.addCleanup(patcher.stop)

    def lacking(self, widget) -> dict:
        """where -> the characters Inter lacks, in what the widget shows in it."""
        out: dict = {}
        for where, text, rich in texts_of(widget):
            missing = {ch for ch in shown(text, rich) if ord(ch) > 127 and not ch.isspace() and ch != "\ufffc"
                       and not self.font.supportsCharacter(ord(ch))}             # (U+FFFC: an image's place)
            if missing:
                out.setdefault(where, set()).update(missing)
        return out

    def test_the_window_with_the_plant_and_the_stringing_and_then_a_layout_that_failed_with_its_checks(self):
        from _fixtures import capannone, inverter_record
        from _setup import wait_until
        p = capannone()
        p.energy["inverters"] = [{"record": inverter_record(), "count": 2, "name": ""}]
        win = _setup.window(self, p, size=(1200, 800))
        sid = win.project.subfields[0].id
        # the Plant phase with its inverters, the strings proposed and one being drawn by hand
        win.show_phase("plant")
        win._select("subfield", sid)
        self.assertTrue(wait_until(self.app, lambda: not win.plant_pending() and win.plant_state is not None))
        win.strategy_actions["serpentine"].trigger()
        self.assertTrue(wait_until(self.app, lambda: not win.plant_pending() and bool(win.plant_state.strings)))
        win.commands["strings_manual"].trigger()
        self.assertIsNotNone(win.plan.draft)
        self.app.processEvents()
        self.assertEqual(self.lacking(win), {})
        win.commands["strings_manual"].trigger()                    # off again: the string given up
        self.assertIsNone(win.plan.draft)
        # the model with a layout that failed and its checks
        win.show_phase("model")
        win._layout_done(win.generation, {sid: ValueError("no room")}, 0.0, dict(win.layout_keys))
        win._select("subfield", sid)
        self.app.processEvents()
        self.assertEqual(self.lacking(win), {})

    def test_the_comparison_of_the_variants(self):
        from PySide6.QtCore import QThreadPool

        from meridiana.ui.variants import VariantsDialog
        pool = QThreadPool()
        dialog = VariantsDialog([("v1", "Base"), ("v2", "Est")], lambda vid: {"error": "none"}, "v1", pool=pool)
        pool.waitForDone()
        self.app.processEvents()
        self.addCleanup(_setup.dispose, dialog)
        self.assertEqual(self.lacking(dialog), {})
        self.assertFalse(dialog.table.horizontalHeaderItem(0).icon().isNull())     # the variant in hand

    def test_the_catalogue_with_a_module_chosen(self):
        from meridiana import catalog
        from meridiana.ui.catalog_dialog import CatalogDialog
        catalog.prepare("modules")                          # read: the list at once (the first reading waits)
        dialog = CatalogDialog("modules")
        self.addCleanup(_setup.dispose, dialog)
        dialog.show()
        self.app.processEvents()
        self.assertTrue(dialog.records)
        self.assertIn("Pmax", dialog.detail.toPlainText())  # γ Pmax among the figures of the module chosen
        self.assertEqual(self.lacking(dialog), {})

    def test_the_steps_of_a_calculation(self):
        from meridiana.energy.pedigree import Quantity, Record, Step
        from meridiana.ui.pedigree import PedigreeView
        rec = Record("Modello del modulo")
        rec.add(Step("sdm", "Il circuito equivalente", "", "Cinque parametri.",
                     [Quantity("R_s", "series resistance", 0.312, "Ω")], Quantity("R_{sh}", "shunt resistance", 412.0,
                                                                                  "Ω")))
        view = PedigreeView()
        self.addCleanup(_setup.dispose, view)
        view.show()
        view.show_records([rec])
        self.app.processEvents()
        self.assertIn("Ω", view.toPlainText())
        self.assertEqual(self.lacking(view), {})


if __name__ == "__main__":
    unittest.main()
