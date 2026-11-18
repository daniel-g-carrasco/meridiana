"""A page made the first time its phase is shown (ui/lazy_page.LazyPage): what the window tells it before is kept, the
last of each, and told when it is made, in the order it was last said; the page's signals reach what the window
connected to the stand-in; any widget asked of it makes it. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


def stub_page():
    """A page with what LazyPage needs of one: `centre`, `side`, `status`, the signals, and the calls it keeps."""
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QLabel, QScrollArea, QWidget

    class Stub(QWidget):
        edited = Signal(str, str, object)
        computeRequested = Signal()
        importRequested = Signal(str, str)

        def __init__(self):
            super().__init__()
            self.told = []
            self.centre = QScrollArea()
            self.side = QScrollArea()
            self.status = QLabel("")
            self.tiles = "the tiles"

        def show_project(self, project, ctx=None):
            self.told.append(("show_project", project, ctx))

        def show_results(self, load, error=""):
            self.told.append(("show_results", load, error))

        def show_basis(self, basis):
            self.told.append(("show_basis", basis))

        def set_computing(self, on):
            self.told.append(("set_computing", on))
    return Stub


class TheLazyPage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def make(self):
        from meridiana.ui.lazy_page import LazyConsumptionPage
        made = []
        stub = stub_page()
        page = LazyConsumptionPage(lambda: made.append(stub()) or made[-1])
        self.addCleanup(_setup.dispose, page)
        self.addCleanup(_setup.dispose, page.side_slot)
        return page, made

    def test_nothing_is_made_until_the_page_is_shown_or_asked_for_a_widget(self):
        page, made = self.make()
        page.show_project("p", "ctx")
        page.status.setText("computing")
        self.assertEqual((made, page.is_built()), ([], False))
        page.resize(400, 300)
        page.show()
        self.assertEqual(len(made), 1)
        self.assertTrue(page.is_built())
        again, made2 = self.make()
        self.assertEqual(again.tiles, "the tiles")                       # a widget asked for: made
        self.assertEqual(len(made2), 1)

    def test_what_was_told_before_is_told_when_it_is_made_the_last_of_each_in_the_order_it_was_last_said(self):
        page, made = self.make()
        page.show_results("first", "")
        page.show_project("p1")
        page.set_computing(True)
        page.show_results("second", "an error")             # the last results, and said after the project
        page.show_basis(None)
        page.status.setText("one")
        page.status.setText("two")
        page.show()
        real = made[0]
        self.assertEqual(real.told, [("show_project", "p1", None), ("set_computing", True),
                                     ("show_results", "second", "an error"), ("show_basis", None)])
        self.assertEqual(real.status.text(), "two")
        page.show_results("third")                                      # made: told at once
        self.assertEqual(real.told[-1], ("show_results", "third", ""))
        page.status.setText("three")
        self.assertEqual(real.status.text(), "three")

    def test_the_signals_of_the_page_reach_what_the_window_connected_to_the_stand_in(self):
        page, made = self.make()
        seen = []
        page.edited.connect(lambda *a: seen.append(("edited", *a)))
        page.computeRequested.connect(lambda: seen.append(("compute",)))
        page.importRequested.connect(lambda *a: seen.append(("import", *a)))
        page.show()
        real = made[0]
        real.edited.emit("consumption", "a.b", 3)
        real.computeRequested.emit()
        real.importRequested.emit("curve.csv", "kW")
        self.assertEqual(seen, [("edited", "consumption", "a.b", 3), ("compute",), ("import", "curve.csv", "kW")])

    def test_the_form_goes_into_the_slot_of_the_inspector_and_the_hooks_run_once_when_it_is_made(self):
        page, made = self.make()
        hooked = []
        page.when_built(hooked.append)
        self.assertEqual(hooked, [])
        page.show()
        self.assertEqual(hooked, [made[0]])
        self.assertIs(made[0].side.parentWidget(), page.side_slot)
        page.when_built(hooked.append)                                  # a hook after: at once
        self.assertEqual(len(hooked), 2)


if __name__ == "__main__":
    unittest.main()
