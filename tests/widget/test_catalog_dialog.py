"""The catalogue's window shows every record (Daniel, R25: «arriva solo a 400 righe»): all 16,959 modules
through a model and a proxy, sorted by the column clicked, the count «N modules», opened and filtered without
making the cells of every row (only those drawn: what keeps it quick), the last row reachable; and the filters of
study 16 theme E: cell family, bifacial, maker, power, efficiency, length, origin, remembered from one opening to
the next. The time itself (200 ms asked) is measured in esterni/test_tempi.py, not here: a busy machine would fail
it with the program unchanged (study 18, D 5.2). PySide6 and a display (offscreen will do)."""

import unittest
from unittest import mock

import _setup

from meridiana import catalog

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it

CATALOGUE = _setup.ROOT / "locale" / "it" / "LC_MESSAGES" / "meridiana.mo"
# the rows a view may make the cells of besides those on screen: QHeaderView.resizeContentsPrecision, 1000 by default,
# when the columns are sized to their contents at the first search
SIZED_ROWS = 1000


class DialogCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        catalog.prepare("modules")                          # the file read once, as at the second opening

    def setUp(self):
        from meridiana.ui import catalog_dialog
        catalog_dialog.forget_filters()                     # what a test leaves is not for the next one
        self.addCleanup(catalog_dialog.forget_filters)

    def opened(self, kind="modules"):
        """The window of a kind, with its list: at the first opening of a kind the catalogue is read in a worker
        (study 16, F3, widget/test_waits.py), and the list comes when it is."""
        from meridiana.ui.catalog_dialog import CatalogDialog
        dialog = CatalogDialog(kind)
        dialog.show()
        self.app.processEvents()
        _setup.wait_until(self.app, lambda: not dialog.reading, 20)
        self.addCleanup(_setup.dispose, dialog)
        return dialog, None

    def cells_made(self):
        """(a patch, the rows): while the patch is on, the rows of the model whose text was asked for, that is whose
        cells were made to be drawn or measured."""
        from PySide6.QtCore import Qt

        from meridiana.ui.catalog_dialog import CatalogModel
        rows: set = set()
        original = CatalogModel.data

        def counted(model, index, role=Qt.ItemDataRole.DisplayRole):
            if role == Qt.ItemDataRole.DisplayRole and index.isValid():
                rows.add(index.row())
            return original(model, index, role)
        return mock.patch.object(CatalogModel, "data", counted), rows


class CatalogueWindow(DialogCase):
    def test_every_module_is_in_the_list_and_the_count_says_how_many(self):
        patch, made = self.cells_made()
        with patch:
            dialog, _took = self.opened()
            dialog.grab()                                   # drawn: the rows on screen made their cells
        total = len(catalog.load("modules"))
        self.assertGreater(total, 16000)
        self.assertEqual(dialog.rows.rowCount(), total)
        self.assertEqual(dialog.count.text(), f"{total:,} modules")
        self.assertIn(0, made)
        self.assertLessEqual(len(made), SIZED_ROWS + 100)   # not the 16,959: a cell is made only when drawn
        self.assertEqual(dialog.record_at(0)["source"], "curated")      # the catalogue's order until a click

    def test_the_last_row_can_be_reached_and_chosen(self):
        dialog, _took = self.opened()
        last = dialog.rows.rowCount() - 1
        dialog.table.scrollToBottom()
        dialog.table.selectRow(last)
        self.app.processEvents()
        self.assertTrue(dialog.table.visualRect(dialog.rows.index(last, 0)).isValid())
        self.assertEqual(dialog.chosen(), dict(dialog.record_at(last)))
        self.assertEqual(dialog.chosen(), dict(catalog.search("modules", limit=None)[-1]))

    def test_a_search_filters_quickly_and_the_count_follows(self):
        patch, made = self.cells_made()
        with patch:                                         # on before the dialog is made: PySide keeps its override
            dialog, _took = self.opened()
            dialog.grab()
            dialog.query.setText("jinko")
            made.clear()
            dialog._search()
            self.app.processEvents()
            dialog.grab()
        self.assertTrue(made)
        self.assertLessEqual(len(made), 100)                # the rows on screen, the columns already sized
        found = catalog.search("modules", "jinko", limit=None)
        self.assertEqual(dialog.rows.rowCount(), len(found))
        self.assertGreater(len(found), 400)                         # more than the old cut
        self.assertTrue(dialog.count.text().startswith(f"{len(found):,} modules of "))
        self.assertTrue(all("jinko" in dialog.record_at(i)["manufacturer"].casefold()
                            for i in range(dialog.rows.rowCount())))
        dialog.query.setText("")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), len(catalog.load("modules")))

    def test_a_click_on_a_column_sorts_by_it_and_the_selection_follows(self):
        from PySide6.QtCore import Qt
        dialog, _took = self.opened()
        dialog.query.setText("jinko")
        dialog._search()
        dialog.table.selectRow(3)
        picked = dialog.chosen()
        dialog.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)         # W
        powers = [dialog.record_at(i)["pmax"] for i in range(dialog.rows.rowCount())]
        self.assertEqual(powers, sorted(powers, reverse=True))
        self.assertEqual(dialog.chosen(), picked)
        dialog.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)          # Model
        models = [str(dialog.record_at(i)["model"]).casefold() for i in range(dialog.rows.rowCount())]
        self.assertEqual(models, sorted(models))

    def test_nothing_found_says_so_and_chooses_nothing(self):
        dialog, _took = self.opened()
        dialog.query.setText("nessun modulo si chiama così")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), 0)
        self.assertTrue(dialog.count.text().startswith("0 modules"))
        self.assertIsNone(dialog.chosen())
        self.assertFalse(dialog.ok.isEnabled())

    def test_the_other_kinds_open_with_their_words(self):
        for kind, word in (("inverters", "inverters"), ("batteries", "batteries")):
            dialog, _took = self.opened(kind)
            with self.subTest(kind):
                self.assertIn(word, dialog.count.text())
                self.assertEqual(dialog.rows.rowCount(), len(catalog.load(kind)))


class CatalogueFilters(DialogCase):
    """Above the table: cell family, bifacial, maker, power, efficiency, length and origin (task 16e, step 4)."""

    def choose(self, combo, data):
        combo.setCurrentIndex(combo.findData(data))
        self.assertEqual(combo.currentData(), data)

    def pick(self, dialog, name):
        dialog.maker.setCurrentIndex(dialog.maker.findText(name))
        self.assertEqual(dialog.maker_name(), name)

    def shown(self, dialog):
        return [dialog.record_at(i) for i in range(dialog.rows.rowCount())]

    def test_the_facets_of_the_modules_and_what_the_other_kinds_keep(self):
        dialog, _took = self.opened()
        for name in ("family", "bifacial", "maker", "efficiency", "length", "origin", "low", "high", "clear"):
            self.assertIsNotNone(getattr(dialog, name), name)
        self.assertEqual([dialog.family.itemData(i) for i in range(dialog.family.count())],
                         ["", "topcon", "hjt", "back_contact", "perc", "thin_film", "poly", "mono", "unknown"])
        self.assertEqual([dialog.bifacial.itemData(i) for i in range(dialog.bifacial.count())], ["", "yes", "no"])
        other, _took = self.opened("inverters")
        self.assertIsNone(other.family)
        self.assertIsNone(other.bifacial)
        self.assertIsNone(other.efficiency)
        self.assertIsNone(other.length)
        self.assertIsNotNone(other.maker)

    def test_the_table_shows_the_family_and_the_card_keeps_the_technology(self):
        dialog, _took = self.opened()
        self.assertEqual([dialog.model.columns[i][0] for i in range(dialog.model.columnCount())],
                         ["manufacturer", "model", "pmax", "cell_family", "source"])
        self.choose(dialog.family, "topcon")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), 41)
        self.assertEqual({dialog.rows.index(i, 3).data() for i in range(dialog.rows.rowCount())}, {"TOPCon"})
        self.assertIn("n-type TOPCon", dialog.detail.toPlainText())             # the datasheet's own label
        self.assertIn("Cell family", dialog.detail.toPlainText())

    def test_an_efficiency_worked_out_says_so_on_the_card_and_a_declared_one_does_not(self):
        dialog, _took = self.opened()
        self.choose(dialog.origin, "cec")
        dialog.length.setValue(4.0)                                     # the CEC modules that have a size
        dialog._search()
        self.assertTrue(dialog.rows.rowCount())
        self.assertIn("Efficiency (%)", dialog.detail.toPlainText())
        self.assertIn("worked out from power and size", dialog.detail.toPlainText())
        self.choose(dialog.origin, "curated")
        dialog.length.setValue(0)
        dialog._search()
        self.assertIn("Efficiency (%)", dialog.detail.toPlainText())
        self.assertNotIn("worked out", dialog.detail.toPlainText())

    def test_the_card_says_when_the_bifaciality_is_an_estimate_and_when_it_is_the_datasheets(self):
        dialog, _took = self.opened()
        self.choose(dialog.origin, "curated")
        dialog.query.setText("solitek magnus")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), 1)
        text = dialog.detail.toPlainText()
        self.assertIn("Bifaciality, estimated (%)", text)
        self.assertIn("80", text)
        self.assertIn("estimated from the cell family, not on the datasheet", text)
        self.assertNotIn("Bifaciality (%)", text)
        dialog.query.setText("jinko JKM620N")
        dialog._search()
        text = dialog.detail.toPlainText()
        self.assertIn("Bifaciality (%)", text)
        self.assertNotIn("estimated", text)

    def test_bifacial_yes_cuts_the_count_and_every_row_shown_is_bifacial(self):
        dialog, _took = self.opened()
        total = dialog.rows.rowCount()
        self.choose(dialog.bifacial, "yes")
        dialog._search()
        yes = dialog.rows.rowCount()
        self.assertTrue(0 < yes < total)
        self.assertTrue(all(r["bifacial"] is True for r in self.shown(dialog)))
        self.assertTrue(dialog.count.text().startswith(f"{yes:,} modules of {total:,}"))
        self.choose(dialog.bifacial, "no")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), total - yes)
        self.assertTrue(all(r["bifacial"] is False for r in self.shown(dialog)))

    def test_the_makers_are_those_of_the_origin_and_one_of_them_filters(self):
        dialog, _took = self.opened()
        everyone = dialog.maker.count()
        self.assertEqual(everyone, len(catalog.brands("modules")))
        self.choose(dialog.origin, "curated")
        self.assertEqual(dialog.maker.count(), len(catalog.brands("modules", "curated")))
        self.assertLess(dialog.maker.count(), everyone)
        self.pick(dialog, "Jinko Solar")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), 4)                              # Jinko's four datasheets
        self.assertEqual({r["manufacturer"] for r in self.shown(dialog)}, {"Jinko Solar"})
        self.choose(dialog.origin, "")
        self.assertEqual(dialog.maker_name(), "Jinko Solar")                     # still there in the longer list
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), len(catalog.search("modules", manufacturer="Jinko Solar", limit=None)))

    def test_a_maker_typed_in_full_filters_and_a_part_of_one_does_not(self):
        dialog, _took = self.opened()
        dialog.maker.setCurrentText("longi")
        dialog._search()
        self.assertEqual({r["manufacturer"] for r in self.shown(dialog)}, {"LONGi"})
        dialog.maker.setCurrentText("lon")
        dialog._search()
        self.assertEqual(dialog.rows.rowCount(), len(catalog.load("modules")))

    def test_every_filter_together_gives_what_the_search_gives(self):
        dialog, _took = self.opened()
        dialog.query.setText("solar")
        self.choose(dialog.origin, "curated")
        self.choose(dialog.family, "topcon")
        self.choose(dialog.bifacial, "yes")
        dialog.low.setValue(400)
        dialog.high.setValue(700)
        dialog.efficiency.setValue(22.0)
        dialog.length.setValue(2.5)
        dialog._search()
        expected = catalog.search("modules", "solar", "curated", 400, 700, family="topcon", bifacial=True,
                                  efficiency_min=22.0, length_max=2.5, limit=None)
        self.assertTrue(expected)
        self.assertEqual([r["id"] for r in self.shown(dialog)], [r["id"] for r in expected])

    def test_sorting_by_watts_is_by_value_under_the_filters(self):
        from PySide6.QtCore import Qt
        dialog, _took = self.opened()
        self.choose(dialog.family, "mono")
        dialog._search()
        dialog.table.sortByColumn(2, Qt.SortOrder.DescendingOrder)
        powers = [r["pmax"] for r in self.shown(dialog)]
        self.assertGreater(len(powers), 1000)
        self.assertEqual(powers, sorted(powers, reverse=True))
        self.assertGreater(powers[0], powers[-1])

    def test_the_watts_sort_by_value_and_not_by_the_text_shown(self):
        from PySide6.QtCore import Qt
        from meridiana.ui.catalog_dialog import CatalogModel
        model = CatalogModel([("model", "Model"), ("pmax", "W")])
        model.set_records([{"model": "a", "pmax": 99.0}, {"model": "b", "pmax": 1000.0}, {"model": "c", "pmax": 450.0}])
        model.sort(1, Qt.SortOrder.AscendingOrder)
        self.assertEqual([r["pmax"] for r in model.records], [99.0, 450.0, 1000.0])
        self.assertEqual(model.index(0, 1).data(), "99")            # as text, «1,000» and «450» would come first
        model.sort(1, Qt.SortOrder.DescendingOrder)
        self.assertEqual([r["pmax"] for r in model.records], [1000.0, 450.0, 99.0])

    def test_sorting_by_family_follows_the_order_of_the_filter(self):
        from PySide6.QtCore import Qt
        dialog, _took = self.opened()
        dialog.table.sortByColumn(3, Qt.SortOrder.AscendingOrder)
        families = []
        for r in self.shown(dialog):
            if not families or families[-1] != r["cell_family"]:
                families.append(r["cell_family"])
        self.assertEqual(families, ["topcon", "hjt", "back_contact", "thin_film", "poly", "mono", "unknown"])
        dialog.table.sortByColumn(3, Qt.SortOrder.DescendingOrder)
        self.assertEqual(dialog.record_at(dialog.rows.rowCount() - 1)["cell_family"], "unknown")

    def test_the_filters_are_remembered_between_two_openings(self):
        first, _took = self.opened()
        first.query.setText("jin")
        self.choose(first.origin, "curated")
        self.pick(first, "Jinko Solar")
        self.choose(first.family, "topcon")
        self.choose(first.bifacial, "yes")
        first.low.setValue(500)
        first.high.setValue(700)
        first.efficiency.setValue(21.5)
        first.length.setValue(2.4)
        first._search()
        seen = [r["id"] for r in self.shown(first)]
        first.reject()
        second, _took = self.opened()
        self.assertEqual(second.query.text(), "jin")
        self.assertEqual(second.origin.currentData(), "curated")
        self.assertEqual(second.maker_name(), "Jinko Solar")
        self.assertEqual(second.family.currentData(), "topcon")
        self.assertEqual(second.bifacial.currentData(), "yes")
        self.assertEqual((second.low.value(), second.high.value()), (500, 700))
        self.assertAlmostEqual(second.efficiency.value(), 21.5)
        self.assertAlmostEqual(second.length.value(), 2.4)
        self.assertEqual([r["id"] for r in self.shown(second)], seen)
        self.assertTrue(second.count.text().startswith(f"{len(seen)} module"))

    def test_each_kind_remembers_its_own_filters(self):
        modules, _took = self.opened()
        self.choose(modules.family, "hjt")
        modules._search()
        modules.reject()
        inverters, _took = self.opened("inverters")
        self.assertEqual(inverters.rows.rowCount(), len(catalog.load("inverters")))
        self.assertEqual(inverters.maker_name(), "")
        again, _took = self.opened()
        self.assertEqual(again.family.currentData(), "hjt")

    def test_clear_the_filters_gives_the_whole_list_back(self):
        dialog, _took = self.opened()
        dialog.query.setText("jinko")
        self.choose(dialog.family, "topcon")
        self.choose(dialog.bifacial, "yes")
        dialog.efficiency.setValue(23.0)
        dialog._search()
        self.assertLess(dialog.rows.rowCount(), 20)
        dialog.clear.click()
        self.assertEqual(dialog.rows.rowCount(), len(catalog.load("modules")))
        self.assertEqual(dialog.query.text(), "")
        self.assertEqual(dialog.family.currentData(), "")
        self.assertEqual(dialog.bifacial.currentData(), "")
        self.assertEqual(dialog.efficiency.value(), 0)
        self.assertEqual(dialog.count.text(), f"{len(catalog.load('modules')):,} modules")

    def test_the_search_stays_live_a_facet_asks_for_a_new_search_in_200_ms(self):
        dialog, _took = self.opened()
        self.assertEqual(dialog.timer.interval(), 200)
        for change in (lambda: self.choose(dialog.family, "hjt"), lambda: self.choose(dialog.bifacial, "no"),
                       lambda: dialog.efficiency.setValue(20.0), lambda: dialog.length.setValue(2.0),
                       lambda: self.pick(dialog, "LONGi"), lambda: dialog.query.setText("x")):
            dialog.timer.stop()
            change()
            self.assertTrue(dialog.timer.isActive())
        dialog.timer.stop()
        dialog.clear.click()
        self.choose(dialog.family, "hjt")
        self.assertTrue(dialog.timer.isActive())
        self.assertTrue(_setup.wait_until(self.app, lambda: not dialog.timer.isActive(), 2))
        self.assertEqual(dialog.rows.rowCount(), len(catalog.search("modules", family="hjt", limit=None)))

    def test_what_a_filter_leaves_out_for_lack_of_data_is_said(self):
        dialog, _took = self.opened()
        self.assertTrue(dialog.hint.isHidden())
        dialog.length.setValue(2.0)
        dialog._search()
        lacking = len([r for r in catalog.load("modules") if not r.get("length")])
        self.assertFalse(dialog.hint.isHidden())
        self.assertIn(f"{lacking:,} modules without this data", dialog.hint.text())
        self.choose(dialog.family, "hjt")
        dialog._search()
        self.assertTrue(dialog.hint.isHidden() or "without this data" in dialog.hint.text())
        dialog.length.setValue(0)
        dialog._search()
        self.assertTrue(dialog.hint.isHidden())

    def test_a_search_with_every_filter_stays_quick_and_nothing_found_says_so(self):
        patch, made = self.cells_made()
        with patch:                                         # on before the dialog is made: PySide keeps its override
            dialog, _took = self.opened()
            dialog.grab()
            self.assertTrue(made)
            self.choose(dialog.family, "thin_film")
            self.choose(dialog.bifacial, "yes")
            dialog.efficiency.setValue(30.0)
            made.clear()
            dialog._search()
            self.app.processEvents()
            dialog.grab()
        self.assertEqual(made, set())                       # nothing left to show: no cell made
        self.assertEqual(dialog.rows.rowCount(), 0)
        self.assertTrue(dialog.count.text().startswith("0 modules"))
        self.assertIsNone(dialog.chosen())
        self.assertFalse(dialog.ok.isEnabled())


@unittest.skipUnless(CATALOGUE.exists(), "tools/compile_po.py first")
class CatalogueInItalian(DialogCase):
    def test_the_filters_speak_italian(self):
        from PySide6.QtCore import Qt
        from meridiana import i18n
        before = i18n._translation
        self.addCleanup(lambda: setattr(i18n, "_translation", before))
        i18n.setup("it")
        dialog, _took = self.opened()
        families = [dialog.family.itemText(i) for i in range(dialog.family.count())]
        self.assertEqual(families, ["Qualsiasi cella", "TOPCon", "HJT (eterogiunzione)", "Contatti posteriori", "PERC",
                                    "Film sottile", "Policristallino", "Monocristallino, cella non indicata",
                                    "Cella non indicata"])
        self.assertEqual([dialog.bifacial.itemText(i) for i in range(dialog.bifacial.count())],
                         ["Monofacciali e bifacciali", "Solo bifacciali", "Solo monofacciali"])
        self.assertEqual(dialog.clear.text(), "Azzera i filtri")
        self.assertEqual(dialog.model.headerData(3, Qt.Orientation.Horizontal), "Famiglia della cella")
        self.assertEqual(dialog.maker.lineEdit().placeholderText(), "Tutte le marche")
        self.assertEqual(dialog.efficiency.specialValueText(), "qualsiasi efficienza")
        self.assertEqual(dialog.length.prefix(), "lunghezza fino a ")
        dialog.family.setCurrentIndex(dialog.family.findData("hjt"))
        dialog._search()
        self.assertEqual(dialog.rows.index(0, 3).data(), "HJT (eterogiunzione)")
        dialog.length.setValue(2.0)
        dialog._search()
        dialog.family.setCurrentIndex(0)
        dialog._search()
        self.assertIn("moduli senza questo dato sono esclusi", dialog.hint.text())
        self.assertIn("moduli su", dialog.count.text())
        dialog._clear()
        dialog.query.setText("solitek magnus")
        dialog._search()
        self.assertIn("Bifaccialità stimata (%)", dialog.detail.toPlainText())
        self.assertIn("stimata dalla famiglia della cella, non è sulla scheda tecnica", dialog.detail.toPlainText())


if __name__ == "__main__":
    unittest.main()
