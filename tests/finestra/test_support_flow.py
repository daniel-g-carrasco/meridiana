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
        self.assertIs(invitation.window(), invitation)
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
        dialog.index = 3
        dialog.present()
        dialog.reject()
        self.assertEqual(win.cfg.tour_status, "paused")
        win._start_tour()
        self.assertEqual(win.tour_dialog.index, 3)
        win.tour_dialog.index = len(tour.steps())-1
        win.tour_dialog.advance()
        self.assertEqual(win.cfg.tour_status, "done")
        self.assertEqual(win.project.to_json(), before)

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
