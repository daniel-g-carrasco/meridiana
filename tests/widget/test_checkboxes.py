"""Native checkboxes keep their focus ring inside the allocated indicator at every density."""
import unittest

import _setup

from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QCheckBox, QStyle, QStyleOptionButton, QVBoxLayout, QWidget

from meridiana.ui import design

setUpModule = _setup.keep_global_state


class CheckboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.theme = _setup.meridiana_look()
        original_mode = self.theme.cfg.theme
        def restore_theme():
            self.theme.cfg.theme = original_mode
            self.theme.apply()
        self.addCleanup(restore_theme)
        self.host = QWidget()
        layout = QVBoxLayout(self.host)
        self.box = QCheckBox("Include in estimate")
        self.next = QCheckBox("Next option")
        layout.addWidget(self.box)
        layout.addWidget(self.next)
        self.host.show()
        self.host.activateWindow()
        QTest.qWait(20)
        self.addCleanup(self.dispose)

    def dispose(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def indicator(self, state, scale=1):
        side = design.Icon.CONTROL + design.Space.S
        margin = design.Space.XS
        image = QImage(round((side + 2 * margin) * scale), round((side + 2 * margin) * scale),
                       QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(scale)
        image.fill(Qt.GlobalColor.transparent)
        opt = QStyleOptionButton()
        self.box.initStyleOption(opt)
        opt.rect = QRect(margin, margin, side, side)
        opt.state = state
        painter = QPainter(image)
        self.theme.scroll_style.drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                                              opt, painter, self.box)
        painter.end()
        return image, margin, side

    def test_native_metrics_reserve_focus_space_without_growing_the_square(self):
        for metric in (QStyle.PixelMetric.PM_IndicatorWidth, QStyle.PixelMetric.PM_IndicatorHeight):
            self.assertEqual(self.box.style().pixelMetric(metric, None, self.box),
                             design.Icon.CONTROL + design.Space.S)
        self.assertGreaterEqual(self.box.sizeHint().height(), design.Size.CONTROL)

    def test_checkboxes_inside_field_groups_use_the_same_style(self):
        from meridiana.ui import style
        group = style.Group("Fields", self.host)
        inside = QCheckBox("Grouped option", group)
        QVBoxLayout(group).addWidget(inside)
        self.host.layout().addWidget(group)
        self.app.processEvents()
        self.assertEqual(inside.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, None, inside),
                         design.Icon.CONTROL + design.Space.S)

    def test_wrapped_checkbox_keeps_the_native_indicator_focus_and_label_gesture(self):
        from meridiana.ui.properties import WrappedCheck
        from meridiana.ui.style import Group

        text = "Allow online maps: the area shown leaves this PC " * 3
        group = Group("Fields", self.host)
        self.host.layout().addWidget(group)
        box = QCheckBox(text)
        wrapped = WrappedCheck(box)
        QVBoxLayout(group).addWidget(wrapped)
        self.host.resize(250, 300)
        self.app.processEvents()
        self.assertEqual(box.accessibleName(), text)
        self.assertTrue(wrapped.label.wordWrap())
        self.assertGreater(wrapped.label.height(), box.height())
        self.assertEqual(box.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorWidth, None, box), 22)
        self.assertGreaterEqual(box.height(), 28)
        box.setFocus(Qt.FocusReason.TabFocusReason)
        self.assertTrue(box.hasFocus())
        QTest.mouseClick(wrapped.label, Qt.MouseButton.LeftButton, pos=QPoint(8, 8))
        self.assertTrue(box.isChecked())
        box.setEnabled(False)
        QTest.mouseClick(wrapped.label, Qt.MouseButton.LeftButton, pos=QPoint(8, 8))
        self.assertTrue(box.isChecked())

    def test_focus_raster_is_complete_and_contained_at_100_200_250_percent(self):
        flags = QStyle.StateFlag
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            for scale in (1, 2, 2.5):
                with self.subTest(mode=mode, scale=scale):
                    image, margin, side = self.indicator(flags.State_Enabled | flags.State_On
                                                        | flags.State_HasFocus, scale)
                    pixels = [(x, y) for y in range(image.height()) for x in range(image.width())
                              if image.pixelColor(x, y).alpha()]
                    left, right = min(x for x, _ in pixels), max(x for x, _ in pixels)
                    top, bottom = min(y for _, y in pixels), max(y for _, y in pixels)
                    self.assertGreaterEqual(left, margin * scale)
                    self.assertGreaterEqual(top, margin * scale)
                    self.assertLess(right, (margin + side) * scale)
                    self.assertLess(bottom, (margin + side) * scale)
                    self.assertEqual(left, top)
                    self.assertEqual(right, bottom)
                    self.assertLessEqual(abs(left - (image.width() - 1 - right)), 1)
                    # A real widget painted at its minimum size has the same whole ring.
                    self.box.setChecked(True)
                    self.box.setFocus(Qt.FocusReason.TabFocusReason)
                    self.box.resize(self.box.sizeHint())
                    opt = QStyleOptionButton()
                    self.box.initStyleOption(opt)
                    indicator = self.box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator,
                                                                opt, self.box)
                    self.assertTrue(self.box.rect().contains(indicator))
                    self.assertTrue(self.box.hasFocus())
                    actual = QImage(round(self.box.width() * scale), round(self.box.height() * scale),
                                    QImage.Format.Format_ARGB32_Premultiplied)
                    actual.setDevicePixelRatio(scale)
                    actual.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(actual)
                    self.box.render(painter, QPoint())
                    painter.end()
                    accent = self.theme.tokens["accent"]
                    coloured = [(x, y) for y in range(actual.height()) for x in range(actual.width())
                                if actual.pixelColor(x, y).name() == accent]
                    self.assertTrue(coloured, "The native checkbox must paint its keyboard focus")
                    self.assertGreater(min(x for x, _ in coloured), 0)
                    self.assertGreater(min(y for _, y in coloured), 0)
                    self.assertLess(max(x for x, _ in coloured), actual.width() - 1)
                    self.assertLess(max(y for _, y in coloured), actual.height() - 1)

    def test_states_use_distinct_canonical_signs_and_theme_colours(self):
        flags = QStyle.StateFlag
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            images = []
            for state in (flags.State_Enabled, flags.State_Enabled | flags.State_On,
                          flags.State_Enabled | flags.State_NoChange,
                          flags.State_Enabled | flags.State_On | flags.State_MouseOver,
                          flags.State_On, flags.State_NoChange):
                image, _, _ = self.indicator(state)
                images.append(bytes(image.constBits()))
            self.assertEqual(len(set(images)), len(images))
            image, margin, _ = self.indicator(flags.State_Enabled | flags.State_On)
            self.assertEqual(image.pixelColor(margin + 10, margin + 6).name(), self.theme.tokens["select_bg"])

    def test_space_tab_label_click_partial_and_disabled_remain_native(self):
        self.box.setFocus(Qt.FocusReason.TabFocusReason)
        QTest.keyClick(self.box, Qt.Key.Key_Space)
        self.assertTrue(self.box.isChecked())
        QTest.mouseClick(self.box, Qt.MouseButton.LeftButton, pos=QPoint(80, self.box.height() // 2))
        self.assertFalse(self.box.isChecked())
        self.box.setTristate(True)
        self.box.setCheckState(Qt.CheckState.PartiallyChecked)
        QTest.keyClick(self.box, Qt.Key.Key_Space)
        self.assertEqual(self.box.checkState(), Qt.CheckState.Checked)
        QTest.keyClick(self.box, Qt.Key.Key_Tab)
        self.assertTrue(self.next.hasFocus())
        self.box.setEnabled(False)
        QTest.mouseClick(self.box, Qt.MouseButton.LeftButton)
        self.assertEqual(self.box.checkState(), Qt.CheckState.Checked)


if __name__ == "__main__":
    unittest.main()
