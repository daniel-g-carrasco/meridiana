"""Raster regressions for table edges, current rows and header scroll geometry."""

from __future__ import annotations

import math
import os
import unittest

import _setup

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEvent, QObject, QPoint, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QPalette, QPixmap, QRegion, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QAbstractItemView, QTableView, QTreeView, QWidget

from meridiana.ui import fades, shared_tables as tables
from meridiana.ui.design import Radius, Space
from meridiana.config import Config
from meridiana.ui.theme import Theme

setUpModule = _setup.keep_global_state


def pixel(image, x, y):
    """Sample the middle of a logical pixel in Qt's device-pixel grab."""
    ratio = image.devicePixelRatio()
    return image.pixelColor(int((x + 0.5) * ratio), int((y + 0.5) * ratio))


class TableUxTests(unittest.TestCase):
    def setUp(self):
        self.app = QApplication.instance() or QApplication([])
        self.theme = Theme(Config(theme=os.environ.get("MERIDIANA_TABLE_TEST_THEME", "light")), app=self.app)
        self.theme.apply()
        fades.set_colour(self.theme.tokens["panel"])

    def dispose(self, view):
        view.close()
        view.deleteLater()
        self.app.processEvents()

    def settle(self):
        self.app.processEvents()
        self.app.processEvents()

    def make_view(self, cls=QTreeView, *, soft_edges=True):
        view = cls()
        self.addCleanup(self.dispose, view)
        model = QStandardItemModel(view)
        model.setHorizontalHeaderLabels(["Code", "Amount"])
        for row in range(60):
            model.appendRow([QStandardItem(str(row)), QStandardItem("111,11")])
        view.setModel(model)
        if isinstance(view, QTreeView):
            view.setRootIsDecorated(False)
        else:
            view.verticalHeader().hide()
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        view.resize(430, 232)
        tables.install(view, soft_edges=soft_edges)
        view.show()
        self.settle()
        return view

    def test_fades_cover_every_boundary_pixel_with_the_table_base(self):
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            fades.set_colour(self.theme.tokens["panel"])
            for cls in (QTreeView, QTableView):
                with self.subTest(mode=mode, view=cls.__name__):
                    view = self.make_view(cls)
                    view.selectAll()
                    bar = view.verticalScrollBar()
                    bar.setValue(bar.maximum() // 2)
                    self.settle()
                    image = view.grab().toImage()
                    port = view.viewport().geometry()
                    base = view.palette().color(QPalette.ColorRole.Base).name()
                    for y in (port.top(), port.bottom()):
                        # Boundary content must be fully faded. Native rounded frame
                        # corners are tested separately and must never become Base.
                        near_corner = y < Radius.CONTROL or y >= view.height() - Radius.CONTROL
                        left = max(port.left(), Radius.CONTROL) if near_corner else port.left()
                        right = min(port.right(), view.width() - Radius.CONTROL - 1) if near_corner else port.right()
                        ratio = image.devicePixelRatio()
                        # At fractional DPR the outermost physical pixel may straddle
                        # the header: inspect all pixels fully inside the viewport.
                        device_y = math.ceil(port.top() * ratio) if y == port.top() else math.floor((y + 1) * ratio) - 1
                        colours = {image.pixelColor(x, device_y).name()
                                   for x in range(math.ceil(left * ratio), math.floor((right + 1) * ratio))}
                        self.assertEqual(colours, {base}, (mode, cls.__name__, y, colours))

    def test_navigation_fades_keep_the_panel_colour_when_base_is_transparent_black(self):
        self.theme.cfg.theme = "dark"
        self.theme.apply()
        fades.set_colour(self.theme.tokens["panel"])
        view = QTreeView()
        self.addCleanup(self.dispose, view)
        model = QStandardItemModel(60, 1, view)
        view.setModel(model)
        view.resize(240, 180)
        view.show()
        palette = view.viewport().palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#000000"))
        view.viewport().setPalette(palette)
        controller = fades.attach(view)
        self.settle()
        bottom = controller.edges[1]
        self.assertTrue(bottom.isVisible())
        image = bottom.grab().toImage()
        colour = image.pixelColor(image.width() // 2, image.height() - 3)
        panel = QColor(self.theme.tokens["panel"])
        self.assertGreater(colour.alpha(), 0)
        self.assertLessEqual(max(abs(a - b) for a, b in zip(colour.getRgb()[:3], panel.getRgb()[:3], strict=True)), 1)

    def test_frame_paint_does_not_reenter_the_parent_widget_painter(self):
        class ObservedFrame(tables.TableFrame):
            painting = False

            def paintEvent(self, event):
                self.painting = True
                try:
                    super().paintEvent(event)
                finally:
                    self.painting = False

        class Observer(QObject):
            reentries = 0

            def eventFilter(self, watched, event):
                if event.type() == QEvent.Type.Paint and frame.painting:
                    self.reentries += 1
                return False

        view = self.make_view()
        view.findChild(tables.TableStyle).frame.hide()
        frame = ObservedFrame(view)
        observer = Observer(view)
        view.installEventFilter(observer)
        frame.follow()
        self.settle()
        frame.repaint()
        self.assertEqual(observer.reentries, 0, "Rendering the parent during its child's paint reenters Qt")

    def test_outside_the_round_frame_keeps_the_real_parent_background(self):
        for cls in (QTreeView, QTableView):
            host = QWidget()
            self.addCleanup(self.dispose, host)
            host.setObjectName("frame-test-host")
            host.setStyleSheet("QWidget#frame-test-host { background: #537681; }")
            host.resize(450, 252)
            view = self.make_view(cls)
            view.setParent(host)
            view.move(10, 10)
            host.show()
            view.show()
            view.selectAll()
            view.verticalScrollBar().setValue(view.verticalScrollBar().maximum() // 2)
            self.settle()
            image = host.grab().toImage()
            outside = pixel(image, 5, 5)
            for x in (view.x(), view.x() + view.width() - 1):
                for y in (view.y(), view.y() + view.height() - 1):
                    self.assertEqual(pixel(image, x, y), outside, (cls.__name__, x, y))

    def test_current_row_has_one_flat_selection_without_a_coloured_left_marker(self):
        for cls in (QTreeView, QTableView):
            view = self.make_view(cls, soft_edges=False)
            view.activateWindow()
            view.setFocus(Qt.FocusReason.TabFocusReason)
            view.setCurrentIndex(view.model().index(2, 0))
            self.settle()
            image = view.viewport().grab().toImage()
            row = view.visualRect(view.model().index(2, 0))
            reference = pixel(image, row.right() - 15, row.center().y()).name()
            for x in (0, 1, row.right() - 15):
                colours = {pixel(image, x, y).name() for y in range(row.top() + 2, row.bottom() - 1)}
                self.assertEqual(colours, {reference}, (cls.__name__, x, colours, reference))

    def test_reserved_scrollbar_gutter_starts_below_header_and_keeps_width(self):
        for cls in (QTreeView, QTableView):
            view = self.make_view(cls)
            port = view.viewport().geometry()
            bar = view.verticalScrollBar()
            self.assertEqual(bar.mapTo(view, QPoint()).y(), port.top())
            self.assertEqual(bar.height(), port.height())
            view.model().removeRows(1, 59)
            self.settle()
            self.assertEqual(view.viewport().width(), port.width())
            self.assertEqual(bar.maximum(), 0)
            header = view.header() if isinstance(view, QTreeView) else view.horizontalHeader()
            header.hide()
            self.settle()
            self.assertEqual(bar.mapTo(view, QPoint()).y(), view.viewport().y())

    def test_sort_arrow_has_space_before_the_section_divider(self):
        view = self.make_view()
        header = view.header()
        header.setStretchLastSection(False)
        header.resizeSection(0, 180)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.settle()
        before = header.grab().toImage()
        header.setSortIndicator(0, Qt.SortOrder.DescendingOrder)
        self.settle()
        after = header.grab().toImage()
        changed = [x for x in range(header.sectionSize(0)) for y in range(header.height())
                   if pixel(before, x, y) != pixel(after, x, y)]
        self.assertTrue(changed, "The native indicator must still change with sort order")
        self.assertGreaterEqual(header.sectionSize(0) - 1 - max(changed), Space.S)

    def test_only_the_last_data_row_closes_the_column_lines(self):
        for cls in (QTreeView, QTableView):
            view = self.make_view(cls)
            header = view.header() if isinstance(view, QTreeView) else view.horizontalHeader()
            header.setStretchLastSection(False)
            view.model().removeRows(3, 57)
            self.settle()
            last = view.model().index(2, 0)
            image = view.viewport().grab().toImage()
            bottom = view.visualRect(last).bottom()
            line = view.palette().color(QPalette.ColorRole.Mid)
            self.assertEqual(pixel(image, 60, bottom), line)
            self.assertNotEqual(pixel(image, 60, view.visualRect(view.model().index(1, 0)).bottom()), line)
            self.assertNotEqual(pixel(image, 250, bottom), line, "No rule through unused space or gutter")
            view.model().removeRows(2, 1)
            self.settle()
            image = view.viewport().grab().toImage()
            new_bottom = view.visualRect(view.model().index(1, 0)).bottom()
            self.assertEqual(pixel(image, 60, new_bottom), line)
            self.assertNotEqual(pixel(image, 60, bottom), line, "The old closure must be erased")
            view.model().removeRows(0, 2)
            self.settle()
            self.assertNotEqual(pixel(view.viewport().grab().toImage(), 60, new_bottom), line)

    def test_last_row_rule_follows_expansion_and_only_appears_at_scroll_end(self):
        view = self.make_view()
        view.model().removeRows(2, 58)
        parent = view.model().item(1, 0)
        parent.appendRow([QStandardItem("Child"), QStandardItem("1")])
        view.expand(parent.index())
        self.settle()
        line = view.palette().color(QPalette.ColorRole.Mid)
        child_bottom = view.visualRect(parent.child(0).index()).bottom()
        self.assertEqual(pixel(view.viewport().grab().toImage(), 60, child_bottom), line)
        view.collapse(parent.index())
        self.settle()
        parent_bottom = view.visualRect(parent.index()).bottom()
        self.assertEqual(pixel(view.viewport().grab().toImage(), 60, parent_bottom), line)
        self.assertNotEqual(pixel(view.viewport().grab().toImage(), 60, child_bottom), line)
        for row in range(50):
            view.model().appendRow([QStandardItem(str(row)), QStandardItem("1")])
        self.settle()
        first_bottom = view.visualRect(view.model().index(0, 0)).bottom()
        self.assertNotEqual(pixel(view.viewport().grab().toImage(), 60, first_bottom), line)
        view.scrollToBottom()
        self.settle()
        last_bottom = view.visualRect(view.model().index(51, 0)).bottom()
        self.assertEqual(pixel(view.viewport().grab().toImage(), 60, last_bottom), line)

    def test_last_row_rule_follows_a_replaced_filtered_and_sorted_model(self):
        for cls in (QTreeView, QTableView):
            view = self.make_view(cls)
            source = view.model()
            proxy = QSortFilterProxyModel(view)
            proxy.setSourceModel(source)
            proxy.setFilterRegularExpression("^(0|1|2)$")
            view.setModel(proxy)
            proxy.sort(0, Qt.SortOrder.DescendingOrder)
            self.settle()
            line = view.palette().color(QPalette.ColorRole.Mid)
            bottom = view.visualRect(proxy.index(2, 0)).bottom()
            self.assertEqual(pixel(view.viewport().grab().toImage(), 60, bottom), line)
            proxy.setFilterRegularExpression("^1$")
            self.settle()
            new_bottom = view.visualRect(proxy.index(0, 0)).bottom()
            self.assertEqual(pixel(view.viewport().grab().toImage(), 60, new_bottom), line)
            self.assertNotEqual(pixel(view.viewport().grab().toImage(), 60, bottom), line)
            view.setColumnHidden(0, True)
            self.settle()
            self.assertEqual(pixel(view.viewport().grab().toImage(), 60, new_bottom), line)

    def test_content_and_fades_preserve_all_four_native_frame_corners(self):
        for mode in ("light", "dark"):
            self.theme.cfg.theme = mode
            self.theme.apply()
            fades.set_colour(self.theme.tokens["panel"])
            for cls in (QTreeView, QTableView):
                for position in ("empty", "start", "middle", "end", "no-header"):
                    with self.subTest(mode=mode, view=cls.__name__, position=position):
                        view = self.make_view(cls)
                        header = view.header() if isinstance(view, QTreeView) else view.horizontalHeader()
                        header.setStretchLastSection(True)
                        if position == "empty":
                            view.model().removeRows(1, 59)
                        view.selectAll()
                        if position == "no-header":
                            header.hide()
                        self.settle()
                        bar = view.verticalScrollBar()
                        bar.setValue(bar.maximum() if position == "end" else
                                     bar.maximum() // 2 if position in ("middle", "no-header") else 0)
                        self.settle()
                        image = view.grab().toImage()
                        # Render the real Qt frame alone as a reference. Left/right curves
                        # have different raster rounding, so mirroring is not an oracle.
                        scale = view.devicePixelRatioF()
                        frame = QPixmap(view.size() * scale)
                        frame.setDevicePixelRatio(scale)
                        frame.fill(Qt.GlobalColor.transparent)
                        view.render(frame, QPoint(), QRegion(), QWidget.RenderFlag.DrawWindowBackground)
                        expected = frame.toImage()
                        radius = round(Radius.CONTROL * scale)
                        width, height = image.width(), image.height()
                        for x in (*range(radius), *range(width - radius, width)):
                            for y in (*range(radius), *range(height - radius, height)):
                                centre_y = radius if y < radius else height - radius
                                centre_x = radius if x < radius else width - radius
                                distance = math.hypot(x + 0.5 - centre_x, y + 0.5 - centre_y)
                                if distance >= radius - 0.5 * scale:
                                    self.assertEqual(image.pixelColor(x, y), expected.pixelColor(x, y),
                                                     (mode, cls.__name__, position, x, y))


if __name__ == "__main__":
    unittest.main()
