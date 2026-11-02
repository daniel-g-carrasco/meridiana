"""One empty state for every card with nothing to show (R321, Daniel 02/11/2026: the report's «Calcola la producibilità
per vedere la relazione: i suoi capitoli sono fatti dei risultati» stood half way down a blank card, against its left
edge). `ui/style.EmptyState`: the words in the middle of the card, secondary text, no wider than `Size.READING`, the
command that fills the card below them. The report's preview and every chart (`Chart.message`) use it. PySide6 and
a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state

TEXT = "Compute the production to see the report: its chapters are made of the results."


class EmptyStates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def shown(self, widget, size=(900, 400)):
        widget.resize(*size)
        widget.show()
        self.addCleanup(widget.deleteLater)
        _setup.turn_events(self.app, 50)
        return widget

    def test_the_words_stand_in_the_middle_no_wider_than_reading_with_their_command(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtGui import QAction

        from meridiana.ui.design import Size, Text
        from meridiana.ui.style import EmptyState
        state = EmptyState(TEXT)
        fired = []
        action = QAction("&Compute", state)
        action.triggered.connect(lambda: fired.append(1))
        state.set_action(action)
        self.shown(state)
        words = state.words
        middle = words.mapTo(state, QPoint(words.width() // 2, words.height() // 2))
        self.assertLessEqual(abs(middle.x() - state.width() / 2), 2)             # centred across
        self.assertLess(abs(middle.y() - state.height() / 2), words.height() + 40)   # and down the card
        self.assertLessEqual(words.width(), Size.READING)
        self.assertGreater(words.width(), Size.READING // 2)                     # not Qt's narrow guess
        self.assertEqual(words.font().pixelSize(), Text.SECONDARY.size)
        self.assertEqual(words.property("tone"), "text2")
        self.assertEqual(state.button.text(), "Compute")                         # without the accelerator
        state.button.click()
        self.assertEqual(fired, [1])
        state.set_action(None)
        self.assertFalse(state.button.isVisibleTo(state))

    def test_the_report_and_the_charts_use_it(self):
        from PySide6.QtGui import QAction

        from meridiana.ui.charts import Chart
        from meridiana.ui.report_page import ReportPage
        from meridiana.ui.style import EmptyState
        actions = {cid: QAction(cid) for cid in ("export_report", "compare_variants", "save_revision",
                                                 "copy_notes", "compute")}
        page = self.shown(ReportPage(actions))
        page.set_ready(False)
        self.assertIsInstance(page.empty, EmptyState)
        self.assertTrue(page.empty.isVisible())
        self.assertTrue(page.empty.button.isVisible())
        self.assertGreater(page.empty.height(), page.height() // 2)            # the card, not a line at its top
        chart = self.shown(Chart("Months"), (600, 300))
        chart.message("Nothing to compute yet.")
        self.assertIsInstance(chart.note, EmptyState)
        self.assertIs(chart.stack.currentWidget(), chart.note)
        self.assertEqual(chart.note.text(), "Nothing to compute yet.")


if __name__ == "__main__":
    unittest.main()
