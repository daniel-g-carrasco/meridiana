"""The card of the charts in the three energy pages (ui/energy_pages.chart_card): the pills centred in their band
and every sub-tab's content at the same distance from the line (R284, R285, Daniel 30/10/2026), and the row of the
calculation's basis on all three pages, first (R246, R292). The rule is in docs/design/sistema-grafico.md
(«Scheda dei grafici e sue sottoschede»). PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


class ChartTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def pages(self):
        from meridiana.ui.energy_pages import ConsumptionPage, EconomicsPage, EnergyPage
        for kind in (EnergyPage, ConsumptionPage, EconomicsPage):
            page = kind()
            self.addCleanup(_setup.dispose, page)
            self.addCleanup(self.app.processEvents)     # hidden and settled before it is deleted (the tables'
            self.addCleanup(page.hide)                  # header follower runs on the events of the deletion)
            page.resize(980, 760)
            page.show()
            self.app.processEvents()
            yield page

    def test_the_pills_have_the_same_air_above_and_below_in_every_page(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QTabWidget
        from meridiana.ui.design import Space
        for page in self.pages():
            tabs = page.findChild(QTabWidget)
            card, bar = tabs.parentWidget(), tabs.tabBar()
            slot = bar.tabRect(0)                   # the pill with the bar's XS margins above and below it
            top = bar.mapTo(card, slot.topLeft()).y() + Space.XS
            pane_line = tabs.widget(0).mapTo(card, QPoint(0, 0)).y() - Space.M - 1     # the line, M above the content
            above = top - 1                                         # the card's own line is 1 px
            below = pane_line - (top + slot.height() - 2 * Space.XS)
            self.assertEqual((above, below), (Space.M, Space.M), type(page).__name__)
            self.assertEqual(slot.height() - 2 * Space.XS, 24, type(page).__name__)        # Button.CHIP

    def test_every_sub_tab_starts_its_content_at_the_same_distance_from_the_line(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QTabWidget
        from meridiana.ui.charts import Chart
        from meridiana.ui.design import Space
        for page in self.pages():
            tabs = page.findChild(QTabWidget)
            card = tabs.parentWidget()
            bar_bottom = tabs.tabBar().mapTo(card, QPoint(0, tabs.tabBar().height())).y()
            tops = {}
            for i in range(tabs.count()):
                tabs.setCurrentIndex(i)
                self.app.processEvents()
                content = tabs.widget(i)
                tops[tabs.tabText(i)] = content.mapTo(card, QPoint(0, 0)).y() - bar_bottom
                # a chart's title stands where the content starts, a stacked tab's first chart too (no Qt margins)
                first = content if isinstance(content, Chart) else content.findChild(Chart)
                if first is not None:
                    self.assertEqual(first.title.mapTo(card, QPoint(0, 0)).y(), content.mapTo(card, QPoint(0, 0)).y(),
                                     f"{type(page).__name__}: {tabs.tabText(i)}")
                    self.assertEqual(first.mapTo(card, QPoint(0, 0)).x(), content.mapTo(card, QPoint(0, 0)).x())
            self.assertEqual(set(tops.values()), {Space.XS + 1 + Space.M}, f"{type(page).__name__}: {tops}")

    def test_the_stacked_tabs_keep_l_between_their_charts(self):
        from meridiana.ui.design import Space
        from meridiana.ui.energy_pages import EconomicsPage
        page = EconomicsPage()
        self.addCleanup(_setup.dispose, page)
        for first in (page.prod_split, page.size_share, page.store_share):
            box = first.parentWidget().layout()
            self.assertEqual(box.spacing(), Space.L)
            self.assertEqual(box.contentsMargins().top(), 0)

    def test_the_basis_row_is_first_on_all_three_pages_and_says_the_same(self):
        from meridiana.energy.calculation_basis import CalculationBasis
        basis = CalculationBasis(("Maker INV-20",), 1, 60, 1, "Maker B10", 10, 3.5)
        texts = set()
        for page in self.pages():
            page.show_basis(basis)
            self.app.processEvents()
            self.assertTrue(page.plant_context.isVisible(), type(page).__name__)
            self.assertEqual(page.results_box.indexOf(page.plant_context), 0, type(page).__name__)
            self.assertLess(page.results_box.indexOf(page.plant_context), page.results_box.indexOf(page.tiles))
            texts.add(page.plant_context.text())
        self.assertEqual(len(texts), 1)             # one wording on the three pages
        self.assertIn("1 inverter", texts.pop())


if __name__ == "__main__":
    unittest.main()
