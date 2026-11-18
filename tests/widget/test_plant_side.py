"""The Plant's right panel (R277, R296, R337), offscreen: a section closed is as tall as its header, an open one as tall
as what it holds, and the space below them stays empty, outside the frame; the free text of a section (the hint of
Panels, the line of Storage) never touches the frame's edge."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


class PlantSideSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look("light")

    def setUp(self):
        from PySide6.QtGui import QAction

        from meridiana.ui import motion
        from meridiana.ui.plant_page import PlantInspector, PlantSide
        from meridiana.ui.style import _FOLDED

        class Actions(dict):
            def __missing__(self, key):
                self[key] = QAction(key)
                return self[key]

        _FOLDED.clear()
        self.addCleanup(_FOLDED.clear)
        self.addCleanup(motion.set_reduced, False)
        motion.set_reduced(True)                        # every fold at once
        self.side = PlantSide(PlantInspector(Actions()), Actions(), lambda: None)
        self.addCleanup(_setup.dispose, self.side)
        self.side.resize(365, 600)
        self.side.show()
        _setup.turn_events(self.app, 100)

    def heights(self):
        return {sid: s.height() for sid, s in self.side.sections.items()}

    def test_a_section_closed_is_as_tall_as_its_header_and_the_space_stays_below(self):
        from meridiana.ui.style import MeridianaStyle
        side = self.side
        header = MeridianaStyle.head(side.sections["panels"]) + 1
        self.assertGreater(side.sections["panels"].height(), header + 20)   # open: its text under its header
        side.sections["panels"].set_expanded(False, 0)                  # a click on its header
        _setup.turn_events(self.app, 100)
        for sid, section in side.sections.items():
            self.assertLessEqual(section.height(), header + 2, f"{sid}: {self.heights()}")
        last = side.sections["storage"]
        self.assertLess(last.geometry().bottom(), side.height() - 200)      # the empty space is below the frame

    def test_the_section_open_is_as_tall_as_it_holds_and_the_others_their_headers(self):
        side = self.side
        for sid, least in (("inverter", 300), ("storage", 40), ("panels", 40)):
            side.open(sid, ms=0)
            _setup.turn_events(self.app, 100)
            h = self.heights()
            self.assertGreater(h[sid], least, h)
            self.assertTrue(all(v <= 30 for k, v in h.items() if k != sid), h)

    def test_the_free_text_of_a_section_is_off_the_frame(self):
        from PySide6.QtCore import QPoint

        from meridiana.ui.design import Space
        side = self.side
        side.open("storage", ms=0)
        _setup.turn_events(self.app, 100)
        for section, label in ((side.sections["panels"], side.panels_hint),
                               (side.sections["storage"], side.storage_text)):
            section.set_expanded(True, 0)
            _setup.turn_events(self.app, 100)
            x = label.mapTo(section, QPoint(0, 0)).x() + label.contentsMargins().left()
            self.assertGreaterEqual(x, Space.M, f"{label.text()[:20]}: {x}")
            self.assertLessEqual(x, Space.M + 4, f"{label.text()[:20]}: {x}")      # and not twice the margin


if __name__ == "__main__":
    unittest.main()
