"""R711 (21/11/2026): the Impianto inspector makes only the view of the strings that is shown (cards, diagram or
table, PlantInverters.qml) and keeps it once made. The three made together were 1141 items at the first strings of a
plant of 2000 modules (721 of the table, which shows every row: R631), and the first entry into Impianto held the
window 4,2-7,4 s offscreen; with the cards alone 290 items and 1,9-2,7 s (tools/fasi_probe.py, synthetic plant of
tests/_fixtures.synthetic_plant, two runs on a PC in use). The limit below has twice that room."""
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from _fixtures import synthetic_plant

ENTRY_LIMIT_S = 5.5             # the longest gap of the window's thread entering Impianto (measured 1,9-2,7 s)


def items_by_view(window):
    """The items made under each of the three views of the strings, by their QML type."""
    counts, todo = {}, [(window.contentItem(), None)]
    while todo:
        item, owner = todo.pop()
        kind = item.metaObject().className().split('_QML')[0]
        if kind in ('PlantInputCards', 'PlantDiagram', 'PlantTable'):
            owner = kind
        if owner:
            counts[owner] = counts.get(owner, 0) + 1
        todo.extend((child, owner) for child in item.childItems())
    return counts


class OnlyTheViewShown(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QTimer
        from meridiana.gui.application import QuickWindow, create_app
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(synthetic_plant(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.window = cls.host.window
        cls.window.resize(1600, 960)
        cls.window.show()
        session = cls.host.bridge.session
        cls.host.bridge._ask_layout()
        _setup.wait_until(cls.app, lambda: cls.host.bridge._layout is None and not session.telling()
                          and session.layout_keys == session.expected_layout_keys(), 180)
        _setup.turn_events(cls.app, 1500)
        # the window's thread watched from now: the longest gap while Impianto is entered the first time
        cls.beat, cls.gaps = [time.perf_counter()], []

        def tick():
            now = time.perf_counter()
            cls.gaps.append(now - cls.beat[0])
            cls.beat[0] = now
        cls.heart = QTimer()
        cls.heart.setInterval(5)
        cls.heart.timeout.connect(tick)
        cls.heart.start()
        cls.plant = cls.host.engine.rootContext().contextProperty('plantBackend')
        cls.window.showPhase('plant')
        cls.entered = _setup.wait_until(cls.app, lambda: len(cls.plant.strings) == 80 and not cls.plant.busy
                                        and items_by_view(cls.window).get('PlantInputCards', 0) > 0, 120)
        _setup.turn_events(cls.app, 1500)
        cls.heart.stop()
        cls.first = items_by_view(cls.window)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def test_1_the_first_entry_makes_the_cards_alone_and_does_not_hold_the_window(self):
        self.assertTrue(self.entered, items_by_view(self.window))
        self.assertGreater(self.first.get('PlantInputCards', 0), 50)
        self.assertNotIn('PlantTable', self.first)              # 721 items before, for a view not shown
        self.assertNotIn('PlantDiagram', self.first)
        self.assertLess(sum(self.first.values()), 600, self.first)
        self.assertLess(max(self.gaps, default=0), ENTRY_LIMIT_S, sorted(self.gaps, reverse=True)[:5])

    def test_2_a_view_is_made_when_chosen_and_kept(self):
        actions = self.host.engine.rootContext().contextProperty('plantActions')
        if actions is None or not hasattr(actions, 'setStringsView'):
            self.skipTest('the views are chosen through the plant page actions')
        actions.setStringsView('table')
        _setup.wait_until(self.app, lambda: items_by_view(self.window).get('PlantTable', 0) > 0, 20)
        now = items_by_view(self.window)
        self.assertGreater(now.get('PlantTable', 0), 0)
        self.assertGreater(now.get('PlantInputCards', 0), 0)    # kept: changing back is at once
        actions.setStringsView('cards')
        _setup.turn_events(self.app, 300)
        self.assertGreater(items_by_view(self.window).get('PlantTable', 0), 0)


if __name__ == '__main__':
    unittest.main()
