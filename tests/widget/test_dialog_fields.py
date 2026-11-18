"""Every dialog of the program gives its number fields the text inset of the design system (R283, Daniel
30/10/2026: in the canopy dialog «i valori delle caselle di input non rispettano nessun margine»). The sheet's
padding never reaches the line edit inside a QAbstractSpinBox; `ui/style.pad_fields` did, but only where it was
called (the window once, the properties' pages, the gallery): a dialog built later had nothing. Now the shared
style pads every spin box the application polishes (`style._watch_fields`), and this test opens each dialog with
fields and measures them. PySide6 and a display (offscreen will do)."""

import unittest

import _setup

setUpModule = _setup.keep_global_state


def dialogs():
    """Every dialog of ui/ with number or text fields, built as the program builds it, without the network."""
    from meridiana import model
    from meridiana.ui.canopy_dialog import CanopyDialog
    from meridiana.ui.catalog_dialog import CatalogDialog
    from meridiana.ui.catalog_editor import CatalogEditor
    from meridiana.ui.feedback import FeedbackDialog
    from meridiana.ui.optimizer_groups import OptimizerGroupsDialog
    from meridiana.ui.site_dialog import SiteDialog
    from meridiana.ui.template_dialog import TemplateDialog
    return [("canopy", CanopyDialog()), ("template", TemplateDialog()),
            ("site", SiteDialog(model.Site(), network=False)), ("catalog", CatalogDialog("modules")),
            ("catalog editor", CatalogEditor("modules")),
            ("optimizer groups", OptimizerGroupsDialog(["M1", "M2", "M3", "M4"], 2)),
            ("feedback", FeedbackDialog(summary="x"))]


class DialogFields(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def test_every_number_field_of_every_dialog_has_the_text_inset_of_the_design_system(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QLineEdit
        from meridiana.ui.style import FIELD_TEXT
        reference = QLineEdit()                     # a plain field under the sheet: where its text starts
        self.addCleanup(reference.deleteLater)
        reference.show()
        self.app.processEvents()
        plain = reference.cursorRect().left()       # the cursor's rect starts a few px left of the text (5 for 8)
        self.assertGreaterEqual(plain, 4)           # the sheet's padding (Line.TEXT_INSET) reached it
        counted = 0
        for name, dialog in dialogs():
            self.addCleanup(dialog.deleteLater)
            dialog.show()
            self.app.processEvents()
            for spin in dialog.findChildren(QAbstractSpinBox):
                edit = spin.findChild(QLineEdit)
                self.assertIsNotNone(edit, name)
                self.assertEqual(edit.textMargins().left(), FIELD_TEXT, f"{name}: {spin.objectName() or spin}")
                counted += 1
            # every field, plain, in a list or in a number field: the text starts where the plain field's does,
            # measured in the field (the spin box's inner edit is frameless: its cursor rect sits 2 px further)
            for edit in dialog.findChildren(QLineEdit):
                if not edit.isVisible():
                    continue
                parent = edit.parentWidget()
                field = parent if isinstance(parent, (QAbstractSpinBox, QComboBox)) else edit
                edit.setCursorPosition(0)
                start = edit.mapTo(field, QPoint(edit.cursorRect().left(), 0)).x()
                self.assertTrue(plain - 2 <= start <= plain + 1, f"{name}: {type(field).__name__} text at {start}")
            dialog.close()
        self.assertGreaterEqual(counted, 12)       # the canopy's 6, the template's, the site's two, the catalogue's

    def test_a_spin_box_made_after_the_style_is_padded_when_it_is_shown_without_any_call(self):
        from PySide6.QtWidgets import QDoubleSpinBox, QLineEdit, QWidget
        from meridiana.ui.style import FIELD_TEXT
        holder = QWidget()
        self.addCleanup(holder.deleteLater)
        field = QDoubleSpinBox(holder)
        self.assertEqual(field.findChild(QLineEdit).textMargins().left(), 0)     # before: on the edge
        holder.show()
        self.app.processEvents()
        self.assertEqual(field.findChild(QLineEdit).textMargins().left(), FIELD_TEXT)


if __name__ == "__main__":
    unittest.main()
