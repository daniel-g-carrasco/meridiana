"""Meridio in the window (study 17, theme G; design 3.9): the same widget and conversation across the tabs, his place
above the sun bar and the bubble off the selection on the plan, a place dragged kept after a restart; Ctrl+L, the
button of the status bar, the size of the bubble and the dock remembered, the dock's own button, the questions that
give way in a low panel; the preferences that dock him, choose his movements and drawing, and switch him off. Meridio
alone is in widget/test_assistant_widget.py. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone
from _setup import wait_until

from meridiana import assistant, config

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class InTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, cfg=config.Config(background="none", theme="light"))
        self.win.assistant.reduced_motion = True            # the place at once, not after 130 ms
        self.app.processEvents()

    def again(self):
        """The window closed and made again on the same folders: what was saved comes back."""
        from meridiana.ui.window import MainWindow
        _setup.dispose(self.win)
        self.win = MainWindow(self.paths, self.cfg)
        self.addCleanup(_setup.dispose, self.win)
        from _fakes import nothing_local, offline
        self.win.assistant_chat.make_local = offline        # no local model here: said at once (_setup.window)
        self.win.assistant_chat.survey = nothing_local
        self.win.resize(1200, 800)
        self.win.show()
        self.assertTrue(wait_until(self.app, lambda: not self.win.assistant_chat.surveying))
        self.win.assistant.reduced_motion = True
        self.app.processEvents()
        return self.win

    def answered(self, a) -> bool:
        return wait_until(self.app, lambda: a.mood.state == assistant.IDLE and a.messages
                          and a.messages[-1][0] != "you", 5)

    def test_across_the_tabs_the_same_widget_above_the_sun_bar_off_the_selection_and_dragged_places_kept(self):
        from PySide6.QtCore import QPoint

        from meridiana import assistant as core
        win, a = self.win, self.win.assistant
        # the same widget and the same conversation on every tab
        a.open_panel()
        a.ask("Che ne pensi?")
        self.assertTrue(self.answered(a))
        a.field.setText("a question written halfway")
        for index in (1, 2, 3, 0):
            win.tabs.setCurrentIndex(index)
            self.app.processEvents()
            self.assertIs(win.assistant, a)
            self.assertIs(a.parent(), win)                  # over every card (Daniel, 24/10/2026)
            self.assertTrue(a.isVisible() and a.opened and a.bubble.isVisible())
        self.assertEqual(a.field.text(), "a question written halfway")
        self.assertIn("Che ne pensi?", a.conversation.toPlainText())
        a.close_panel()
        # on the model above the sun bar, in the corner of the views' card; the bubble never over the phases
        sun, home = win.sunbar, win._assistant_home()
        self.assertEqual(a.x() + a.width(), home.right() + 1 - core.MARGIN)
        self.assertEqual(a.y() + a.height(), home.bottom() + 1 - core.MARGIN - sun.height())
        win.commands["assistant"].trigger()
        self.app.processEvents()
        self.assertGreaterEqual(a.bubble.y(), a.top())
        a.close_panel()
        # the bubble keeps off the selection on the plan, on the model only
        file = self.paths.data / "prova.meridiana"
        file.parent.mkdir(parents=True, exist_ok=True)
        capannone().save(file)
        win.open_path(file)
        self.app.processEvents()
        self.assertEqual(win._assistant_avoid(), [])
        win._select("building", win.project.buildings[0].id)
        self.app.processEvents()
        [(_x, _y, w, h)] = win._assistant_avoid()
        self.assertTrue(w > 0 and h > 0)
        win.show_phase("production")
        self.assertEqual(win._assistant_avoid(), [])
        win.show_phase("model")
        # dragged on the model, even over the tree's card: kept there, and after a restart
        a.move(QPoint(100, 150))
        self.assertLess(a.x() + a.width(), win.docks[0].x() + win.docks[0].width())       # over the tree
        a.dropped()
        win.tabs.setCurrentIndex(3)
        self.app.processEvents()
        win.tabs.setCurrentIndex(0)
        self.app.processEvents()
        self.assertEqual((a.x(), a.y()), (100, 150))
        win._save_window()
        win.session.mark_saved()
        win = self.again()
        for _ in range(3):                                   # the cards' gaps settle after the state is restored
            self.app.processEvents()
        top = win.assistant.top()                            # under the phases' header
        self.assertEqual(win.assistant.places["model"], ("left", "top", 100, 150 - top))
        self.assertEqual((win.assistant.x(), win.assistant.y()), (100, 150))

    def test_ctrl_l_the_size_of_the_bubble_and_the_dock_are_kept_and_the_dock_has_its_own_button(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtGui import QKeySequence
        from PySide6.QtTest import QTest
        win, a = self.win, self.win.assistant
        # Ctrl+L opens and closes him, the button of the status bar follows
        action = win.commands["assistant"]
        self.assertEqual(action.shortcut(), QKeySequence("Ctrl+L"))
        action.trigger()
        self.assertTrue(a.opened and win.assistant_button.isChecked())
        action.trigger()
        self.assertFalse(a.opened or win.assistant_button.isChecked())
        # the bubble resized: kept in the settings and after a restart
        win.checks_dock.hide()                              # room to grow
        a.open_panel()
        self.app.processEvents()
        g = a.bubble.grip
        centre = g.rect().center()
        QTest.mousePress(g, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre)
        QTest.mouseMove(g, centre + QPoint(-40, -30))
        QTest.mouseRelease(g, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, centre + QPoint(-40, -30))
        self.app.processEvents()
        after = a.bubble.geometry()
        self.assertEqual((self.cfg.assistant_width, self.cfg.assistant_height), (after.width(), after.height()))
        win._save_config()
        win = self.again()
        win.checks_dock.hide()
        win.assistant.open_panel()
        a = win.assistant
        self.assertEqual((a.bubble.width(), a.bubble.height()), (after.width(), after.height()))
        # docked and back: the conversation and the text being typed stay
        a.ask("Quanto produce a dicembre?")
        self.assertTrue(self.answered(a))
        a.field.setText("e a giugno")
        talk = a.conversation.toPlainText()
        a.dock_button.click()                               # into the panels
        dock = win.assistant_dock
        self.assertTrue(self.cfg.assistant_docked)
        self.assertIs(dock.widget(), a.panel)
        self.assertTrue(dock.isVisible() and a.panel.isVisible())
        self.assertFalse(a.isVisible() or a.bubble.isVisible())           # no floating character, no bubble
        self.assertTrue(a.small.isVisible())                # the character at the head of the panel
        self.assertEqual((a.conversation.toPlainText(), a.field.text()), (talk, "e a giugno"))
        self.assertTrue(win.assistant_button.isChecked())
        a.dock_button.click()                               # floating again
        self.assertFalse(self.cfg.assistant_docked)
        self.assertIs(a.panel.parentWidget(), a.bubble)
        self.assertFalse(dock.isVisible())
        self.assertTrue(a.isVisible() and a.bubble.isVisible() and a.opened)
        self.assertEqual((a.conversation.toPlainText(), a.field.text()), (talk, "e a giugno"))
        # docked, Ctrl+L and the panel's close button
        a.close_panel()
        win._dock_assistant(True)
        self.assertFalse(dock.isVisible())                  # closed, as it was
        win.commands["assistant"].trigger()
        self.assertTrue(dock.isVisible() and a.opened)
        dock.close()                                        # the panel's own button
        self.assertFalse(a.opened)
        self.assertFalse(win.assistant_button.isChecked())
        # docked in a low panel the questions give way to the conversation
        from meridiana.ui.assistant import QUESTIONS_HEIGHT
        a.open_panel()
        win.docks[1].hide()                                 # the panel alone on the right: tall
        win.checks_dock.hide()
        self.app.processEvents()
        self.assertGreaterEqual(a.panel.height(), QUESTIONS_HEIGHT)
        self.assertTrue(a.questions_box.isVisibleTo(a.panel))
        win.docks[1].show()                                 # with Properties and the Checks, a low panel
        win.checks_dock.show()
        self.assertTrue(wait_until(self.app, lambda: not win.assistant_chat.surveying))
        win.assistant_chat._drop_survey()
        self.app.processEvents()
        win.resizeDocks([win.assistant_dock], [QUESTIONS_HEIGHT // 2], Qt.Orientation.Vertical)
        self.app.processEvents()
        self.assertLess(a.panel.height(), QUESTIONS_HEIGHT)
        self.assertFalse(a.questions_box.isVisibleTo(a.panel))
        self.assertTrue(a.field.isVisibleTo(a.panel) and a.conversation.isVisibleTo(a.panel))
        # a card there (the guide «Give Meridio a model»: no model answers here) scrolls in the low panel instead of
        # keeping it tall (R07, review H): it is there, shorter than itself, and the field stays under it
        cards = a.cards_area
        self.assertTrue(cards.isVisibleTo(a.panel))
        self.assertLess(cards.height(), a.cards.height())
        self.assertGreater(cards.verticalScrollBar().maximum(), 0)
        self.assertLessEqual(cards.geometry().bottom(), a.field.geometry().top())
        # the choice to dock him is remembered; an old layout does not bring an empty panel back
        win.resize(1200, 800)
        win._save_window()
        win = self.again()
        self.assertTrue(win.assistant.docked)
        self.assertFalse(win.assistant.isVisible())
        self.assertIs(win.assistant_dock.widget(), win.assistant.panel)
        win._dock_assistant(False)
        win._save_window()
        win = self.again()
        self.assertFalse(win.assistant.docked)
        self.assertFalse(win.assistant_dock.isVisible())
        self.assertTrue(win.assistant.isVisible())
        # Ctrl+L puts the cursor in the field: with the keyboard on the window (said when there is none)
        _setup.keyboard_or_skip(self, win)
        win.commands["assistant"].trigger()
        self.app.processEvents()
        self.assertTrue(win.assistant.field.hasFocus())

    def test_the_preferences_dock_him_choose_his_movements_and_drawing_and_switch_him_off(self):
        self.win._preferences("assistant")
        settings = self.win.file_page.settings
        self.assertFalse(settings.assistant_docked.isChecked())
        self.assertTrue(settings.assistant_animated.isChecked())
        self.assertEqual(settings.assistant_style.currentData(), "smooth")
        settings.assistant_docked.setChecked(True)
        settings.assistant_animated.setChecked(False)
        settings.assistant_style.setCurrentIndex(settings.assistant_style.findData("pixel"))
        self.assertTrue(self.cfg.assistant_docked and self.win.assistant.docked)
        self.assertEqual((self.cfg.assistant_animated, self.cfg.assistant_style), (False, "pixel"))
        self.assertEqual((self.win.assistant.animated, self.win.assistant.style), (False, "pixel"))
        self.assertFalse(self.win.assistant.timer.isActive())
        win = self.again()
        self.assertEqual((win.assistant.animated, win.assistant.style), (False, "pixel"))
        win._dock_assistant(False)
        self.assertTrue(win.assistant.isVisible() and win.assistant_button.isVisible())
        win.assistant.open_panel()
        self.app.processEvents()

        win._preferences("assistant")
        settings = win.file_page.settings
        self.assertEqual(settings.pages.tabText(settings.pages.indexOf(settings.assistant_page)), "Assistant")
        settings.assistant.setChecked(False)
        self.assertFalse(self.cfg.assistant)
        self.assertFalse(win.assistant.isVisible() or win.assistant_button.isVisible()
                         or win.assistant.bubble.isVisible())
        self.assertFalse(win.commands["assistant"].isEnabled())
        win = self.again()                                  # off stays off
        self.assertFalse(win.assistant.isVisible())


if __name__ == "__main__":
    unittest.main()
