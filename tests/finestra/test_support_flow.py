import copy
import unittest
from unittest.mock import patch

import _setup
from _setup import wait_until
from meridiana import config, tour

setUpModule = _setup.keep_global_state


class SupportFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_invitation_resume_all_targets_and_no_project_changes(self):
        _setup.window(self, cfg=config.Config(background="none", tour_status="new"))
        win = self.win
        before = copy.deepcopy(win.project.to_json())
        win._offer_tour()
        invitation = win.tour_dialog
        self.assertTrue(invitation.invitation)
        self.assertIs(invitation.parentWidget(), win.assistant.panel)
        self.assertTrue(win.assistant.property("guidedTourActive"))
        self.assertTrue(win.assistant.bubble.isVisible())
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        self.app.sendEvent(invitation, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier))
        invitation.reject()
        self.assertEqual(win.cfg.tour_status, "skipped")
        win._offer_tour()
        self.assertIsNone(win.tour_dialog)
        win._assistant_command("Avvia la visita guidata")
        dialog = win.tour_dialog
        for index, item in enumerate(tour.steps()):
            dialog.index = index
            dialog.present()
            # Exercise each registered destination directly: missing controls cannot be hidden by fallback text.
            dialog._show_target(item.target)
            self.app.processEvents()
            self.assertNotIn("not available", dialog.description.text())
            if item.id == "start":
                self.assertTrue(win.file_page.isVisible())
                self.assertTrue(win.file_page.sections["new"].isVisible())
        dialog.index = 3
        dialog.present()
        dialog.reject()
        self.assertEqual(win.cfg.tour_status, "paused")
        win._start_tour()
        self.assertEqual(win.tour_dialog.index, 3)
        win.tour_dialog.index = len(tour.steps())-1
        win.tour_dialog.advance()
        self.assertEqual(win.cfg.tour_status, "done")
        self.assertTrue(win.file_page.sections["new"].isVisible())
        self.assertFalse(win.assistant.property("guidedTourActive"))
        self.assertEqual(win.project.to_json(), before)

    def test_every_step_of_the_tour_is_read_whole_in_the_bubble(self):
        # the description was held to its size hint (vertical policy Maximum) and lost its last line in the bubble
        _setup.window(self, cfg=config.Config(background="none", tour_status="paused"))
        win = self.win
        win._start_tour()
        dialog = win.tour_dialog
        for index, item in enumerate(tour.steps()):
            dialog.index = index
            dialog.present()
            self.app.processEvents()
            for label in (dialog.heading, dialog.description):
                self.assertGreaterEqual(label.height(), label.heightForWidth(label.width()), (item.id, label.text()))
            self.assertTrue(win.assistant.bubble.rect().contains(
                dialog.next.mapTo(win.assistant.bubble, dialog.next.rect().bottomRight())), item.id)
        dialog.reject()

    def test_a_tour_shows_meridio_without_turning_him_on_in_the_settings(self):
        _setup.window(self, cfg=config.Config(background="none", tour_status="paused", assistant=False))
        win = self.win
        self.assertFalse(win.assistant.isVisible())
        win._start_tour()
        dialog = win.tour_dialog
        self.assertTrue(win.assistant.bubble.isVisible())
        for index in (0, [s.id for s in tour.steps()].index("assistant")):
            dialog.index = index
            dialog.present()
            self.app.processEvents()
            # closing the window now saves the configuration: the designer's choice, not the tour's
            self.assertFalse(win.cfg.assistant)
            self.assertFalse(config.load(win.paths.config_file).assistant)
        dialog.reject()
        self.assertFalse(win.assistant.isVisible())
        self.assertFalse(win.assistant_button.isVisible())

    def test_an_interrupted_tour_gives_the_conversation_back_as_it_was(self):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        _setup.window(self, cfg=config.Config(background="none", tour_status="paused", assistant_docked=True))
        win = self.win
        win.assistant.messages = [("you", "Quanto produce?"), ("assistant", "Circa 1200 kWh per kWp.")]
        win.assistant._show_messages()

        def ended(how):
            win._start_tour()
            dialog = win.tour_dialog
            self.assertFalse(win.assistant.docked)
            self.assertFalse(win.assistant.chat_content.isVisible())
            dialog.index = 4
            dialog.present()
            self.app.processEvents()
            how(dialog)
            self.app.processEvents()
            self.assertTrue(wait_until(self.app, lambda: win.tour_dialog is None), how)
            self.assertEqual(win.cfg.tour_status, "paused")
            self.assertFalse(win.assistant.property("guidedTourActive"))
            self.assertTrue(win.assistant.docked)
            self.assertFalse(win.assistant.opened)
            self.assertTrue(win.assistant.chat_content.isVisibleTo(win.assistant.panel))
            self.assertEqual(win.assistant.messages[0], ("you", "Quanto produce?"))

        ended(lambda d: self.app.sendEvent(d, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape,
                                                        Qt.KeyboardModifier.NoModifier)))
        ended(lambda d: win.assistant.close_button.click())
        ended(lambda d: (win.show_phase("production"), d.skip.click()))
        # docked by hand during the tour: the designer's latest choice is kept, the character not left floating
        win._start_tour()
        dialog = win.tour_dialog
        win.assistant.dock_button.click()
        self.app.processEvents()
        self.assertTrue(win.cfg.assistant_docked is win.assistant.docked)
        dialog.index = 2
        dialog.present()
        if win.assistant.docked:
            self.assertFalse(win.assistant.isVisible())
        dialog.reject()
        self.app.processEvents()
        self.assertEqual(win.assistant.docked, win.cfg.assistant_docked)

    def test_after_the_whole_tour_meridio_opens_without_overlapping_rows(self):
        # seen in the photos of the review: after the thirteen steps the setup card came into a bubble fitted to
        # the tour, card, suggestions and attach button drawn over each other
        _setup.window(self, cfg=config.Config(background="none", tour_status="new"))
        win, a = self.win, self.win.assistant
        a.reduced_motion = True
        win._offer_tour()
        dialog = win.tour_dialog
        for _step in range(len(tour.steps()) + 1):          # Start tour, twelve Next, Start
            dialog.next.click()
            self.app.processEvents()
        self.assertTrue(wait_until(self.app, lambda: win.tour_dialog is None))
        win.file_page.close_page()
        a.open_panel()
        self.assertTrue(wait_until(self.app, lambda: not a.questions_timer.isActive()))
        self.app.processEvents()
        layout = a.chat_content.layout()
        shown = [layout.itemAt(i).widget() for i in range(layout.count())]
        shown = [w for w in shown if w is not None and w.isVisibleTo(a.panel)]
        for upper, lower in zip(shown, shown[1:], strict=False):
            self.assertLess(upper.geometry().bottom(), lower.geometry().top(), (upper, lower))

    def test_the_last_step_with_file_already_open_lands_on_new_project(self):
        _setup.window(self, cfg=config.Config(background="none", tour_status="paused"))
        win = self.win
        win.open_file_page("open")
        self.app.processEvents()
        win._start_tour()
        dialog = win.tour_dialog
        dialog.index = len(tour.steps()) - 1
        dialog.present()
        self.app.processEvents()
        self.assertTrue(win.file_page.isVisible())
        self.assertTrue(win.file_page.sections["new"].isVisible())
        self.assertEqual(dialog.next.text(), "Start")
        dialog.next.click()
        self.app.processEvents()
        self.assertEqual(win.cfg.tour_status, "done")
        self.assertTrue(win.file_page.isVisible())
        self.assertTrue(win.file_page.sections["new"].isVisible())
        self.assertTrue(wait_until(self.app, lambda: win.tour_dialog is None))

    def test_issue_preview_opens_only_after_deliberate_click(self):
        _setup.window(self)
        win = self.win
        self.assertTrue(win._assistant_command("Segnala un bug"))
        dialog = win.feedback_dialog
        opened = []
        dialog.opener = lambda url: opened.append(url.toString()) or True
        self.assertFalse(dialog.open.isEnabled())
        dialog.title.setText("Wrong count")
        dialog.description.setPlainText("Expected 4, saw 5")
        self.assertEqual(opened, [])
        self.assertNotIn("Subfields", dialog.preview.toPlainText())
        dialog.diagnostics.setPlainText('File "C:\\Users\\Daniel\\client\\secret.py", line 4\n"api_key": "private-value"')
        self.assertNotIn("secret.py", dialog.preview.toPlainText())
        dialog.include_diagnostics.setChecked(True)
        self.assertIn("secret.py", dialog.preview.toPlainText())
        self.assertNotIn("Daniel", dialog.preview.toPlainText())
        self.assertNotIn("private-value", dialog.preview.toPlainText())
        dialog.context.setChecked(True)
        self.assertIn("Subfields", dialog.preview.toPlainText())
        dialog.open.click()
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0].startswith("https://github.com/"))
        dialog.reject()
        self.assertTrue(wait_until(self.app, lambda: win.feedback_dialog is None))

    def test_storage_configuration_is_one_undoable_edit(self):
        from PySide6.QtWidgets import QDialog
        from meridiana.ui.storage_page import StoragePage
        _setup.window(self)
        win = self.win
        before = copy.deepcopy(win.project.economics)
        battery = dict(manufacturer="Test", model="AC unit", coupling="ac", usable_energy_kwh=10,
                       max_charge_power_w=5000, max_discharge_power_w=5000)

        def configure(dialog):
            page = dialog.findChild(StoragePage)
            self.assertIsNotNone(page)
            page._battery = battery
            page.efficiency.setValue(90)
            page._refresh()
            self.assertTrue(page.apply_button.isEnabled())
            page.apply_button.click()
            return QDialog.DialogCode.Accepted

        with patch.object(QDialog, "exec", configure):
            win._choose_battery()
        self.assertEqual(win.project.economics["battery"]["model"], "AC unit")
        self.assertEqual(win.project.economics["storage_coupling"], "ac")
        win.undo.undo()
        self.assertEqual(win.project.economics, before)
