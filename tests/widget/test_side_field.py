"""The field of a side's length stands in the side's pill, in its measures (R324, Daniel 02/11/2026: «non è impaginata
bene, è tutta spostata in alto storta»: a black box of 28 px over a pill of 16, the number lifted, the unit off its
line). The same height, font and disc as the pill (`PlanView._side_pills`), the disc where the pill's was, the number
where the pill's length was written and on the same baseline, the unit on that line too, at any zoom. PySide6 and a
display (offscreen will do)."""

import unittest

import _setup
import widget.test_plan as plan_tests            # the module, not its classes: unittest would run them here too

setUpModule = _setup.keep_global_state


class SideField(plan_tests.PlanCase):
    project, pills = plan_tests.Sides.project, plan_tests.Sides.pills
    pill_click, mouse_move = plan_tests.Sides.pill_click, plan_tests.Sides.mouse_move

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        _setup.meridiana_look()

    def opened(self, side=1):
        from PySide6.QtCore import QPoint, QPointF
        self.project()
        self.view.set_tool("select")
        self.view.set_selection("building", "b1")
        self.app.processEvents()
        box = self.pills()[side][0]
        self.pill_click(side)
        self.app.processEvents()
        editor = self.view.side_editor
        self.assertTrue(editor.isVisible())
        offset = QPointF(self.view.viewport().mapTo(self.view, QPoint(0, 0)))
        return editor, box.translated(offset)

    def check(self, editor, pill):
        from PySide6.QtGui import QFontMetrics

        from meridiana.ui import design
        self.assertEqual(editor.height(), round(pill.height()))                # the pill's height
        self.assertLessEqual(abs(editor.x() - pill.left()), 1)               # its disc where the pill's was
        self.assertLessEqual(abs(editor.y() - pill.top()), 1)
        field = editor.field.geometry()
        self.assertTrue(editor.rect().contains(field), (field, editor.rect()))  # the field inside the pill
        self.assertEqual(editor.field.font().pixelSize(), design.Type.SMALL)  # the pill's font
        fm = QFontMetrics(editor.field.font())
        pill_baseline = design.Space.XXS + fm.ascent()                     # the pill's text, centred on its line
        self.assertLessEqual(abs(editor.baseline() - pill_baseline), 1)
        x0 = design.Space.XXS + editor.disc() + design.Space.XS             # where the pill's length began
        self.assertLessEqual(abs(field.x() - x0), 1)

    def test_the_field_stands_in_the_pill_in_its_measures(self):
        editor, pill = self.opened()
        self.check(editor, pill)
        editor.cancel()

    def test_and_so_at_another_zoom(self):
        self.project()
        self.view.scale(2.5, 2.5)
        self.app.processEvents()
        editor, pill = self.opened(0)
        self.check(editor, pill)
        editor.cancel()


if __name__ == "__main__":
    unittest.main()
