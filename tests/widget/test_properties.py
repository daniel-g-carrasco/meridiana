"""The properties panel and the template dialog alone (ui/properties.py, ui/template_dialog.py): the pages fit a
narrow panel, the template draws its outline and refuses measures that make none, the whole-number fields send
once when confirmed; the page scrolled kept from one building to another, a value typed halfway not sent when the
page changes, the wheel over a field without the keyboard. PySide6 and a display (offscreen will do)."""

import unittest

import _setup
from _fixtures import capannone as sample

setUpModule = _setup.keep_global_state          # what the module changes of the process, put back after it


class NarrowPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()                  # the font and the sheet the window gives its panels

    def test_the_properties_fit_a_narrow_panel(self):
        from meridiana.ui.properties import Properties
        p = sample()
        props = Properties()
        props.show_subfield(p, p.subfields[0], p.fill(p.subfields[0]))
        self.assertLessEqual(props.widget().minimumSizeHint().width(), 330)
        props.show_building(p.buildings[0])
        self.assertLessEqual(props.widget().minimumSizeHint().width(), 330)

    def test_the_template_dialog_draws_the_outline_and_refuses_measures_that_make_none(self):
        from PySide6.QtWidgets import QDialogButtonBox

        from meridiana import templates
        from meridiana.ui.template_dialog import TemplateDialog
        d = TemplateDialog()
        self.assertEqual(d.kind.currentData(), "L")
        self.assertEqual(d.outline(), templates.footprint("L"))
        self.assertEqual(d.preview.ring, templates.footprint("L"))
        d.kind.setCurrentIndex(d.kind.findData("U"))
        self.assertEqual(sorted(d.measures()), ["arm", "base", "depth", "width"])
        d.fields["arm"].setValue(13.0)                      # two arms of 13 m in 24: no courtyard left
        self.assertIsNone(d.outline())
        self.assertFalse(d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        self.assertIn("courtyard", d.problem.text())
        d.fields["arm"].setValue(8.0)
        self.assertTrue(d.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        d.grab()                                            # the outline draws without complaint
        d.deleteLater()

    def test_whole_number_fields_send_once_when_confirmed(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QSpinBox

        from meridiana.ui.properties import Properties
        p = sample()
        b = p.buildings[0]
        b.roof.type = "mono"
        props = Properties()
        sent = []
        props.edited.connect(lambda kind, oid, changes: sent.append(changes))
        for show in (lambda: props.show_site(p, False), lambda: props.show_building(b),
                     lambda: props.show_subfield(p, p.subfields[0], None)):
            show()
            fields = props.widget().findChildren(QSpinBox)
            self.assertTrue(fields)
            for field in fields:                            # day, month, eave side, modules across and along
                self.assertFalse(field.keyboardTracking(), field.minimum())
        tables = next(f for f in props.widget().findChildren(QSpinBox) if f.maximum() == 200)
        tables.lineEdit().selectAll()
        QTest.keyClicks(tables, "12")
        self.assertEqual(sent, [])                          # nothing at each key
        QTest.keyClick(tables, Qt.Key.Key_Return)
        self.assertEqual(sent, [{"params.table_modules": 12}])


class PanelAlone(unittest.TestCase):
    """What the panel does on its own between two pages (they were window tests, study 18, D 6.1): the page scrolled
    from one building to another, a value typed halfway when the page changes, the wheel over a field without the
    keyboard. The window's own share (the edit that comes back, the undo) is in finestra/test_window.py."""

    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        cls.look = _setup.meridiana_look()                  # the font and the sheet the window gives its panels

    def setUp(self):
        from meridiana.ui.properties import Properties
        self.p = sample()
        self.props = Properties()
        self.addCleanup(_setup.dispose, self.props)
        self.sent = []
        self.props.edited.connect(lambda kind, oid, changes: self.sent.append((kind, oid, changes)))

    def turn(self, n: int = 3) -> None:
        for _ in range(n):
            self.app.processEvents()

    def test_a_panel_destroyed_before_the_refocus_gets_no_late_call(self):
        from unittest import mock

        from PySide6.QtCore import QCoreApplication, QEvent
        props = self.props
        props._pending_focus = 0
        props.show_building(self.p.buildings[0])
        errors = []
        with mock.patch("sys.excepthook", side_effect=lambda kind, value, tb:
                        errors.append(f"{kind.__name__}: {value}")):
            props.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            self.app.processEvents()
        self.assertEqual(errors, [])

    def test_from_one_building_to_another_the_page_stays_where_it_was_scrolled(self):
        from meridiana import model
        p, props = self.p, self.props
        p.buildings.append(model.Building(id=p.new_id("b"), name="Uffici", footprint=[[50, 0], [60, 0], [60, 8],
                                                                                      [50, 8]], height=6.0))
        props.resize(330, 160)
        props.show()
        props.show_building(p.buildings[0])
        self.turn(5)
        bar = props.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0, "the page fits: nothing to scroll")
        bar.setValue(bar.maximum() // 2)
        where = bar.value()
        props.show_building(p.buildings[1])
        self.turn()
        self.assertEqual(bar.value(), where)
        props.show_site(p, False)                           # another kind of object: from the top
        self.turn()
        self.assertEqual(bar.value(), 0)

    def test_a_value_typed_halfway_is_not_sent_when_the_page_changes(self):
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QFocusEvent
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QDoubleSpinBox
        p, props = self.p, self.props
        props.show()
        props.show_subfield(p, p.subfields[0], None)
        self.turn()
        gap = next(s for s in props.widget().findChildren(QDoubleSpinBox)
                   if s.maximum() == 1.0 and getattr(s, "unit", "") == "m")                          # between modules
        gap.selectAll()
        QTest.keyClicks(gap, "0")                           # the start of "0,07", not confirmed
        props.show_building(p.buildings[0])                 # another page meanwhile
        # the field of the old page loses the keyboard, as it does when the panel takes the focus back
        QApplication.sendEvent(gap, QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.OtherFocusReason))
        self.turn()                                         # the keyboard given back to the new page, as it settles
        self.assertEqual(self.sent, [])

    def test_the_wheel_over_a_field_without_the_keyboard_leaves_it_alone(self):
        from PySide6.QtCore import QPoint, QPointF, Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox

        from meridiana.ui import charts, wheel

        def notch(widget) -> bool:
            """A notch of the wheel over the middle of a widget, as Qt delivers it (accepted until refused)."""
            middle = QPointF(widget.width() / 2, widget.height() / 2)
            event = QWheelEvent(middle, widget.mapToGlobal(middle), QPoint(0, 0), QPoint(0, -120),
                                Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                Qt.ScrollPhase.NoScrollPhase, False)
            event.setAccepted(True)
            QApplication.sendEvent(widget, event)
            return event.isAccepted()
        wheel.guard(self.app)                               # as the window installs it
        p, props = self.p, self.props
        props.show()
        props.show_subfield(p, p.subfields[0], p.fill(p.subfields[0]))
        self.turn()
        page = props.widget()
        spin = next(s for s in page.findChildren(QDoubleSpinBox) if s.maximum() == 60)      # the module tilt
        combo = page.findChildren(QComboBox)[0]
        value, index = spin.value(), combo.currentIndex()
        self.assertFalse(notch(spin))                       # refused: the form under it scrolls instead
        self.assertFalse(notch(combo))
        self.assertEqual((spin.value(), combo.currentIndex(), self.sent), (value, index, []))
        self.assertEqual(spin.focusPolicy(), Qt.FocusPolicy.StrongFocus)   # a click gives it the keyboard
        chart = charts.Chart("Monthly")                     # a chart not drawn yet lets the page scroll too
        self.addCleanup(_setup.dispose, chart)
        chart.show()
        self.assertFalse(notch(chart.canvas))


if __name__ == "__main__":
    unittest.main()
