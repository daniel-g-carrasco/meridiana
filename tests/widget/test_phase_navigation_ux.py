"""Compact phase navigation keeps stable phase ids and native hidden-tab navigation."""
import unittest

import _setup

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from meridiana import phases as phase_model
from meridiana.ui import phasebar

setUpModule = _setup.keep_global_state


class PhaseNavigationUX(unittest.TestCase):
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
        self.widgets = []
        self.addCleanup(self.dispose)

    def dispose(self):
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.app.processEvents()

    def show(self, widget, width=1280, height=200):
        self.widgets.append(widget)
        widget.resize(width, height)
        widget.show()
        self.app.processEvents()
        return widget

    def phases(self):
        view = phasebar.Phases()
        for phase in phase_model.phases():
            index = view.add_phase(phase, QWidget())
            view.set_bar(index, phasebar.PhaseBar(phase, {}))
        host = QWidget()
        box = QVBoxLayout(host)
        box.addWidget(view.header)
        box.addWidget(view)
        self.show(host)
        return host, view

    def test_phase_hover_has_equal_insets_and_compact_height(self):
        bar = phasebar.PhaseTabBar()
        bar.addTab("1 Overview")
        bar.addTab("2 Measurement")
        self.show(bar, 600, 32)
        self.assertLessEqual(bar.tabSizeHint(0).height(), 32)
        rect = QRectF(bar.tabRect(1))
        ground = bar.hover_rect(1)
        self.assertAlmostEqual(ground.left() - rect.left(), rect.right() - ground.right())
        self.assertAlmostEqual(ground.top() - rect.top(), rect.bottom() - ground.bottom())
        self.assertEqual(phasebar.TAB_PAD[0], phasebar.TAB_PAD[1])

    def test_hidden_phase_cannot_be_selected_and_keeps_its_page_stale_state_and_id(self):
        _host, view = self.phases()
        view.set_stale("plant", True, "Recalculate")
        page = view.widget(1)
        view.set_phase_visible("plant", False)
        view.setCurrentIndex(1)
        self.assertNotEqual(view.currentIndex(), 1)
        self.assertFalse(view.tabBar().isTabVisible(1))
        self.assertEqual(view.phase_id(1), "plant")
        self.assertIs(view.widget(1), page)
        self.assertTrue(view.is_stale("plant"))
        self.assertEqual(view.tabBar().tabToolTip(1), "Recalculate")
        view.set_phase_visible("plant", True)
        view.setCurrentIndex(1)
        self.assertEqual(view.currentWidget(), page)
        self.assertEqual(view.bars.currentIndex(), 1)

    def test_hiding_current_phase_updates_page_and_bar_and_leaves_animation_valid(self):
        _host, view = self.phases()
        view.setCurrentIndex(1)
        view.set_phase_visible("plant", False)
        self.app.processEvents()
        index = view.currentIndex()
        self.assertNotEqual(index, 1)
        self.assertEqual(view.pages.currentIndex(), index)
        self.assertEqual(view.bars.currentIndex(), index)
        self.assertEqual(view.shown, index)
        self.assertEqual(view.header.tab_target(), QRectF(view.tab_bar.tabRect(index).translated(view.tab_bar.pos())))

    def test_revealing_a_phase_reclaims_available_header_width(self):
        host, view = self.phases()
        view.set_phase_visible("report", False)
        self.app.processEvents()
        view.set_phase_visible("report", True)
        self.app.processEvents()
        bar = view.tabBar()
        for width in (1280, 1440):
            host.resize(width, 200)
            self.app.processEvents()
            for index in range(bar.count()):
                self.assertGreaterEqual(bar.tabRect(index).width(), bar.tabSizeHint(index).width())
        host.resize(480, 200)
        self.app.processEvents()
        self.assertTrue(any(bar.tabRect(i).width() < bar.tabSizeHint(i).width() for i in range(bar.count())))

    def test_visibility_signal_reports_only_actual_changes_for_known_phase_ids(self):
        _host, view = self.phases()
        changes = []
        view.phaseVisibilityChanged.connect(lambda pid, visible: changes.append((pid, visible)))
        view.set_phase_visible("plant", False)
        view.set_phase_visible("plant", False)
        view.set_phase_visible("unknown", False)
        view.set_phase_visible("plant", True)
        self.assertEqual(changes, [("plant", False), ("plant", True)])

    def test_phase_digits_are_centred_on_their_visible_ink_at_every_density(self):
        bar = phasebar.PhaseTabBar()
        bar.addTab("1 Overview")
        self.show(bar, 240, 32)
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            bar.colours = phasebar._colours(self.theme.tokens)
            for number in ("1", "2", "3", "4", "5", "6"):
                bar.setTabText(0, number + " Overview")
                self.app.processEvents()
                rect = QRectF(bar.tabRect(0))
                cx = rect.left() + phasebar.TAB_PAD[0] + phasebar.BADGE / 2
                cy = rect.center().y()
                for scale in (1, 2, 2.5):
                    image = QImage(round(bar.width() * scale), round(bar.height() * scale),
                                   QImage.Format.Format_ARGB32_Premultiplied)
                    image.setDevicePixelRatio(scale)
                    image.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(image)
                    bar._draw(painter)
                    painter.end()
                    colour = QColor(self.theme.tokens["accent_fg"])
                    ground = QColor(self.theme.tokens["accent"])
                    def distance(pixel, target):
                        return sum(abs(a - b) for a, b in zip(pixel.getRgb()[:3], target.getRgb()[:3], strict=True))
                    points = [(x, y) for x in range(int((cx - 8) * scale), int((cx + 8) * scale))
                              for y in range(int((cy - 8) * scale), int((cy + 8) * scale))
                              if image.pixelColor(x, y).alpha() > 128
                              and distance(image.pixelColor(x, y), colour) < distance(image.pixelColor(x, y), ground)]
                    self.assertTrue(points)
                    xs, ys = zip(*points, strict=True)
                    with self.subTest(mode=mode, number=number, scale=scale):
                        self.assertAlmostEqual((min(xs) + max(xs) + 1) / (2 * scale), cx, delta=0.5 / scale + 0.01)
                        self.assertAlmostEqual((min(ys) + max(ys) + 1) / (2 * scale), cy, delta=0.5 / scale + 0.01)

    def test_phase_digits_stay_centred_with_small_and_large_text(self):
        from meridiana.ui import design
        original = design.text_size()
        self.addCleanup(design.set_text_size, original)
        for choice in ("small", "large"):
            design.set_text_size(choice)
            with self.subTest(text_size=choice):
                self.test_phase_digits_are_centred_on_their_visible_ink_at_every_density()
