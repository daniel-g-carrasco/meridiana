"""Shared short section motion, scroll conventions and dock preview regressions."""
import unittest
import _setup
from PySide6.QtCore import QAbstractAnimation, Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QScrollArea, QVBoxLayout, QWidget
from meridiana.ui import motion, fades
from meridiana.ui.cards import CardDock, PAD

setUpModule = _setup.keep_global_state


class SharedMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def tearDown(self):
        motion.set_reduced(False)

    def test_section_height_is_intermediate_reversible_and_preserves_bounds(self):
        host = QWidget()
        self.addCleanup(_setup.dispose, host)
        layout = QVBoxLayout(host)
        section = QLabel('Line\n' * 10)
        section.setMinimumHeight(40)
        section.setMaximumHeight(400)
        layout.addWidget(section)
        layout.addStretch()
        host.resize(300, 400)
        host.show()
        self.app.processEvents()
        full = section.height()
        controller = motion.collapse(section, False)
        controller.animation.setCurrentTime(controller.animation.duration() // 2)
        self.app.processEvents()
        self.assertGreater(section.height(), 0)
        self.assertLess(section.height(), full)
        self.assertFalse(section.isHidden())
        self.assertIs(motion.collapse(section, True), controller)
        self.assertTrue(_setup.wait_until(self.app, lambda: not controller.running))
        self.assertFalse(section.isHidden())
        self.assertEqual((section.minimumHeight(), section.maximumHeight()), (40, 400))
        motion.collapse(section, False)
        self.assertTrue(_setup.wait_until(self.app, section.isHidden))
        motion.collapse(section, True)
        self.assertTrue(_setup.wait_until(self.app, lambda: not controller.running))
        self.assertFalse(section.isHidden())

    def test_reduced_motion_finishes_an_active_section_and_updates_tree(self):
        from PySide6.QtWidgets import QTreeWidget
        tree = QTreeWidget()
        self.addCleanup(_setup.dispose, tree)
        motion.animate_tree(tree)
        self.assertTrue(tree.isAnimated())
        section = QLabel('Line\n' * 10)
        self.addCleanup(_setup.dispose, section)
        section.show()
        self.app.processEvents()
        controller = motion.collapse(section, False)
        motion.set_reduced(True)
        self.assertEqual(controller.animation.state(), QAbstractAnimation.State.Stopped)
        self.assertTrue(section.isHidden())
        self.assertFalse(tree.isAnimated())
        motion.set_reduced(False)
        self.assertTrue(tree.isAnimated())

    def test_new_scroll_wrappers_get_fades_and_thumb_inset_matches_docked_form(self):
        from PySide6.QtWidgets import QStyle, QStyleOptionSlider
        _setup.meridiana_look()
        host = QMainWindow()
        self.addCleanup(_setup.dispose, host)
        centre = QScrollArea()
        centre.setWidget(QLabel('Line\n' * 100))
        host.setCentralWidget(centre)
        dock = CardDock('Data', host)
        dock.setObjectName('data')
        side = QScrollArea()
        side.setWidget(QLabel('Line\n' * 100))
        dock.setWidget(side)
        host.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        host.resize(900, 600)
        host.show()
        self.app.processEvents()
        self.assertIsNotNone(centre.findChild(fades.Fades))
        self.assertIsNotNone(side.findChild(fades.Fades))
        gaps = []
        for area, border in ((centre, centre.rect()), (side, dock.card_rect())):
            bar = area.verticalScrollBar()
            opt = QStyleOptionSlider()
            bar.initStyleOption(opt)
            rect = bar.style().subControlRect(QStyle.ComplexControl.CC_ScrollBar, opt,
                                             QStyle.SubControl.SC_ScrollBarSlider, bar)
            right = bar.mapTo(centre if area is centre else dock, rect.topRight()).x()
            gaps.append(border.right() - right)
        self.assertEqual(gaps[0], gaps[1])
        self.assertGreaterEqual(gaps[0], PAD)

    def test_automatic_fades_leave_an_explicit_variant_alone_in_either_order(self):
        # The help card asks for plain fades: its height is its text's, and the AIR margins the shared polish
        # gives a page made two lines that fit scroll by 12 px (review of R249, 30/10/2026).
        _setup.meridiana_look()
        for explicit_first in (True, False):
            area = QScrollArea()
            self.addCleanup(_setup.dispose, area)
            area.setWidget(QLabel('Line\n' * 40))
            if explicit_first:
                fades.attach(area)
            area.resize(240, 160)
            area.show()
            self.app.processEvents()
            if not explicit_first:
                self.assertEqual(area.viewportMargins().top(), fades.AIR)       # a page by default
                fades.attach(area)
            for _again in range(2):
                margins = area.viewportMargins()
                self.assertEqual((margins.top(), margins.bottom()), (0, 0), explicit_first)
                self.assertFalse(any(edge.page for edge in area.findChild(fades.Fades).edges), explicit_first)
                self.app._scroll_style.polish(area)                             # a theme polishes again
        page = QScrollArea()
        self.addCleanup(_setup.dispose, page)
        page.show()
        self.app.processEvents()
        fades.attach(page, air=True)
        self.assertEqual(page.viewportMargins().top(), fades.AIR)

    def _overlay(self):
        host = QWidget()
        self.addCleanup(_setup.dispose, host)
        area = QLabel('File', host)
        area.setAutoFillBackground(True)
        area.setGeometry(10, 10, 220, 160)
        host.resize(260, 200)
        host.show()
        self.app.processEvents()
        return host, area

    def test_entering_again_while_leaving_keeps_one_veil(self):
        # qt-app-template caught two pictures on screen when File opened again during its short exit (R252).
        import shiboken6
        host, area = self._overlay()
        leaving = motion.leave(area, area.hide)
        self.assertIsNotNone(leaving)
        entering = motion.enter(area, area.show, 'slide')
        self.assertIsNotNone(entering)
        self.assertEqual([e for e in host.findChildren(motion.Entrance) if e.isVisible()], [entering])
        _setup.turn_events(self.app, 40)            # the pending frame of the replaced exit must not come back
        self.assertFalse(shiboken6.isValid(leaving) and
                         (leaving.isVisible() or leaving.animation.state() == QAbstractAnimation.State.Running))
        self.assertTrue(_setup.wait_until(self.app, lambda: not any(
            e.isVisible() for e in host.findChildren(motion.Entrance))))
        self.assertTrue(area.isVisible())
        motion.leave(area, area.hide)
        area.show()
        again = motion.leave(area, area.hide)       # a second exit replaces the first one too
        self.assertEqual([e for e in host.findChildren(motion.Entrance) if e.isVisible()], [again])
        self.assertTrue(_setup.wait_until(self.app, lambda: not any(
            e.isVisible() for e in host.findChildren(motion.Entrance))))

    def test_a_cancelled_veil_never_plays_nor_shows_again(self):
        # qt-app-template's twin (T, 30/10/2026): stopping and hiding a veil from outside let its pending play show it
        import shiboken6
        host, area = self._overlay()
        for make in (lambda: motion.enter(area, area.show), lambda: motion.leave(area, area.hide)):
            gone = []
            veil = make()
            self.assertIsNotNone(veil)
            self.assertTrue(veil.isVisible())
            veil.finished.connect(lambda g=gone: g.append(1))
            veil.cancel()
            self.assertTrue(veil.done)
            self.assertFalse(veil.isVisible())
            self.assertEqual(gone, [1])
            area.show()                                 # back before the play is due
            _setup.turn_events(self.app, 40)
            self.assertFalse(shiboken6.isValid(veil) and
                             (veil.isVisible() or veil.animation.state() == QAbstractAnimation.State.Running))

    def test_less_motion_switched_on_and_off_before_the_exit_plays_leaves_no_veil(self):
        import shiboken6
        host, area = self._overlay()
        leaving = motion.leave(area, area.hide)
        motion.set_reduced(True)
        motion.set_reduced(False)
        _setup.turn_events(self.app, 40)
        self.assertFalse(shiboken6.isValid(leaving) and
                         (leaving.isVisible() or leaving.animation.state() == QAbstractAnimation.State.Running))

class DockMotion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.meridiana_look()
        motion.set_reduced(False)
        self.host = QMainWindow()
        self.addCleanup(_setup.dispose, self.host)
        self.host.setCentralWidget(QLabel('Workspace'))
        self.docks = []
        for i, area in enumerate((Qt.DockWidgetArea.LeftDockWidgetArea,
                                  Qt.DockWidgetArea.RightDockWidgetArea,
                                  Qt.DockWidgetArea.BottomDockWidgetArea)):
            dock = CardDock(f'Panel {i}', self.host)
            dock.setObjectName(f'panel_{i}')
            body = QLabel('Content\n' * 3)
            body.setMinimumSize(140, 80)
            dock.setWidget(body)
            self.host.addDockWidget(area, dock)
            self.docks.append(dock)
        self.host.resize(1000, 700)
        self.host.show()
        self.assertTrue(_setup.wait_settled(self.app, lambda: [
            (d.geometry(), d.minimumSize()) for d in self.docks]))

    def tearDown(self):
        motion.set_reduced(False)

    def test_collapse_uses_intermediate_card_geometry_and_reverses(self):
        from meridiana.ui.dock_motion import reflow
        dock = self.docks[1]
        before = dock.geometry()
        layer = reflow(self.host, dock.hide, edge='right')
        self.assertTrue(dock.isHidden())
        self.assertTrue(_setup.wait_until(self.app, lambda: layer.animation.state() ==
                                        QAbstractAnimation.State.Running))
        layer.animation.setCurrentTime(layer.animation.duration() // 2)
        visual = layer.rectangles()[dock]
        self.assertGreater(visual.width(), 0)
        self.assertLess(visual.width(), before.width())
        restored = reflow(self.host, dock.show, edge='right')
        self.assertIs(restored, layer)
        self.assertTrue(_setup.wait_until(self.app, lambda: not restored.isVisible()))
        self.assertFalse(dock.isHidden())
        self.assertEqual(dock.width(), before.width())

    def test_preview_does_not_touch_real_layout_and_matches_final_geometry(self):
        from meridiana.ui.dock_motion import DockTarget, LayoutPreview, apply_target
        source, anchor = self.docks[:2]
        state = bytes(self.host.saveState())
        geometry = {d: d.geometry() for d in self.docks}
        preview = LayoutPreview(self.host, source)
        self.addCleanup(preview.close)
        target = DockTarget(Qt.DockWidgetArea.RightDockWidgetArea, anchor, Qt.Orientation.Vertical)
        predicted = preview.solve(target)
        self.assertEqual(bytes(self.host.saveState()), state)
        self.assertEqual({d: d.geometry() for d in self.docks}, geometry)
        self.assertGreater(predicted[source].height(), 80)
        self.assertLess(predicted[anchor].height(), geometry[anchor].height())
        apply_target(self.host, source, target)
        self.app.processEvents()
        for widget in (*self.docks, self.host.centralWidget()):
            actual, expected = widget.geometry(), predicted[widget]
            for value, wanted in zip(actual.getRect(), expected.getRect(), strict=True):
                self.assertLessEqual(abs(value - wanted), 2, (widget.objectName(), actual, expected))

    def test_reduced_motion_collapse_has_no_overlay(self):
        from meridiana.ui.dock_motion import reflow
        motion.set_reduced(True)
        dock = self.docks[1]
        self.assertIsNone(reflow(self.host, dock.hide, edge='right'))
        self.assertTrue(dock.isHidden())

    def _check_prediction(self, target):
        from meridiana.ui.dock_motion import DockTarget, LayoutPreview, apply_target
        source, anchor = self.docks[:2]
        preview = LayoutPreview(self.host, source)
        try:
            # Hover several mutually different targets before accepting one. A cancelled
            # tab preview must never leave a stale tab group in the measuring layout.
            preview.solve(DockTarget(Qt.DockWidgetArea.RightDockWidgetArea, anchor, tab=True))
            preview.solve(DockTarget(Qt.DockWidgetArea.TopDockWidgetArea))
            expected = preview.solve(target)
            apply_target(self.host, source, target)
            self.assertTrue(_setup.wait_settled(self.app, lambda: [d.geometry() for d in self.docks]))
            actual = source.geometry()
            for value, wanted in zip(actual.getRect(), expected[source].getRect(), strict=True):
                self.assertLessEqual(abs(value - wanted), 2, (actual, expected[source]))
        finally:
            preview.close()

    def test_split_before_prediction_matches_accepted_layout(self):
        from meridiana.ui.dock_motion import DockTarget
        self._check_prediction(DockTarget(Qt.DockWidgetArea.RightDockWidgetArea, self.docks[1],
                                          Qt.Orientation.Horizontal, before=True))

    def test_tab_prediction_matches_accepted_layout(self):
        from meridiana.ui.dock_motion import DockTarget
        self._check_prediction(DockTarget(Qt.DockWidgetArea.RightDockWidgetArea, self.docks[1], tab=True))

    def test_top_edge_prediction_matches_accepted_layout(self):
        from meridiana.ui.dock_motion import DockTarget
        self._check_prediction(DockTarget(Qt.DockWidgetArea.TopDockWidgetArea))

    def test_bottom_edge_prediction_matches_accepted_layout(self):
        from meridiana.ui.dock_motion import DockTarget
        self._check_prediction(DockTarget(Qt.DockWidgetArea.BottomDockWidgetArea))

    def test_drag_escape_cancels_preview_without_live_visibility_or_layout_changes(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication
        from meridiana.ui.dock_motion import Reflow
        source, anchor = self.docks[:2]
        original = bytes(self.host.saveState())
        visibility = []
        for dock in self.docks:
            dock.visibilityChanged.connect(visibility.append)
        title = source.title_bar
        QTest.mousePress(title, Qt.MouseButton.LeftButton, pos=title.rect().center())
        at = anchor.mapToGlobal(QPoint(20, anchor.height() - 30))
        QTest.mouseMove(title, title.mapFromGlobal(at))
        self.assertIsNotNone(title.findChild(type(source.drag_motion)).solver)
        layer = self.host.findChild(Reflow)
        self.assertIsNotNone(layer)
        self.assertIs(layer.preview_source, source)
        self.assertGreater(layer.preview_rect.width(), 0)
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.assertIsNone(source.drag_motion.solver)
        self.assertTrue(_setup.wait_until(self.app, lambda: not layer.isVisible()))
        self.assertEqual(bytes(self.host.saveState()), original)
        self.assertEqual(visibility, [])
        self.assertIsNone(QWidget.mouseGrabber())
        self.assertIsNotNone(QApplication.instance())

    def _start_drag(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest
        source, anchor = self.docks[:2]
        title = source.title_bar
        QTest.mousePress(title, Qt.MouseButton.LeftButton, pos=title.rect().center())
        QTest.mouseMove(title, title.mapFromGlobal(anchor.mapToGlobal(QPoint(20, anchor.height() - 30))))
        self.assertIsNotNone(source.drag_motion.solver)
        return source, title

    def _no_live_layer(self):
        from meridiana.ui.dock_motion import Reflow
        return _setup.wait_until(self.app, lambda: not any(
            layer.isVisible() for layer in self.host.findChildren(Reflow)), 3)

    def test_a_floating_panel_is_not_painted_into_the_reflow(self):
        from meridiana.ui.dock_motion import reflow
        floating = self.docks[0]
        floating.setFloating(True)
        floating.move(self.host.mapToGlobal(self.host.rect().center()))
        self.assertTrue(_setup.wait_settled(self.app, lambda: [d.geometry() for d in self.docks]))
        layer = reflow(self.host, self.docks[1].hide, edge='right')
        self.assertNotIn(floating, layer.pictures)
        self.assertTrue(_setup.wait_until(self.app, lambda: layer.animation.state() ==
                                          QAbstractAnimation.State.Running))
        self.assertNotIn(floating, layer.pictures)
        self.assertNotIn(floating, layer.rectangles())

    def test_a_page_over_the_cards_takes_the_change_at_once(self):
        # File over the panels: a layer raised over it cut the page into the cards' pictures (review, 30/10/2026)
        from meridiana.ui.cards import arena
        from meridiana.ui.dock_motion import Reflow, reflow
        page = QLabel('File', self.host)
        page.setAutoFillBackground(True)
        page.setGeometry(arena(self.host).adjusted(8, 8, -8, -8))
        page.show()
        page.raise_()
        self.assertIsNone(reflow(self.host, self.docks[2].hide, edge='bottom'))
        self.assertTrue(self.docks[2].isHidden())
        self.assertEqual([layer for layer in self.host.findChildren(Reflow) if layer.isVisible()], [])
        page.setGeometry(arena(self.host).center().x(), arena(self.host).center().y(), 80, 80)   # a little overlay
        self.assertIsNotNone(reflow(self.host, self.docks[2].show, edge='bottom'))
        self.assertTrue(self._no_live_layer())

    def test_hiding_the_window_or_changing_its_pixel_ratio_cancels_a_drag(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtTest import QTest
        state = bytes(self.host.saveState())
        source, title = self._start_drag()
        self.host.hide()
        self.assertIsNone(source.drag_motion.solver)
        self.assertIsNone(QWidget.mouseGrabber())
        self.host.show()
        self.assertTrue(self._no_live_layer())
        self.assertEqual(bytes(self.host.saveState()), state)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        source, title = self._start_drag()
        QCoreApplication.sendEvent(self.host, QEvent(QEvent.Type.DevicePixelRatioChange))
        self.assertIsNone(source.drag_motion.solver)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.assertTrue(self._no_live_layer())
        self.assertEqual(bytes(self.host.saveState()), state)

    def test_a_panel_toggled_during_a_drag_cancels_the_preview_first(self):
        from PySide6.QtCore import QPoint
        from PySide6.QtTest import QTest
        from meridiana.ui.dock_motion import reflow
        source, title = self._start_drag()
        reflow(self.host, self.docks[2].hide, edge='bottom')
        self.assertIsNone(source.drag_motion.solver)
        self.assertIsNone(QWidget.mouseGrabber())
        QTest.mouseMove(title, title.rect().center() + QPoint(5, 5))       # no move on a deleted layer
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.assertIsNone(source.drag_motion.solver)
        self.assertTrue(self._no_live_layer())
        self.assertTrue(self.docks[2].isHidden())

    def test_escape_cancels_a_drag_before_a_window_shortcut_takes_it(self):
        from PySide6.QtGui import QAction, QKeySequence
        from PySide6.QtTest import QTest
        fired = []
        action = QAction(self.host)
        action.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        action.triggered.connect(lambda: fired.append(True))
        self.host.addAction(action)
        self.host.activateWindow()
        state = bytes(self.host.saveState())
        source, title = self._start_drag()
        QTest.keyClick(title, Qt.Key.Key_Escape)
        self.assertIsNone(source.drag_motion.solver)
        self.assertEqual(fired, [])
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.assertTrue(self._no_live_layer())
        self.assertEqual(bytes(self.host.saveState()), state)
        QTest.keyClick(title, Qt.Key.Key_Escape)                            # outside a drag the shortcut is free
        self.assertEqual(fired, [True])

class TreeSections(unittest.TestCase):
    def test_checks_group_uses_shared_short_motion_while_details_remain_immediate(self):
        from PySide6.QtWidgets import QTreeWidgetItem
        from meridiana.ui.checks_page import ChecksTree
        app = _setup.qt_or_skip()
        _setup.meridiana_look()
        motion.set_reduced(False)
        self.addCleanup(motion.set_reduced, False)
        tree = ChecksTree()
        self.addCleanup(_setup.dispose, tree)
        group = QTreeWidgetItem(tree, ['Group'])
        for i in range(5):
            row = QTreeWidgetItem(group, [f'Row {i}'])
            QTreeWidgetItem(row, ['Detail'])
        tree.resize(400, 400)
        tree.show()
        app.processEvents()
        tree.tree_motion.set_expanded(group, True)
        self.assertTrue(group.isExpanded())
        veil = tree.viewport().findChild(motion.SectionVeil)
        self.assertIsNotNone(veil)
        self.assertTrue(_setup.wait_until(app, lambda: veil.after is not None))
        from meridiana.ui.design import Motion
        self.assertEqual(veil.animation.duration(), Motion.FAST)
        self.assertEqual(tree.state(), tree.State.NoState)
        self.assertTrue(_setup.wait_until(app, lambda: not tree.viewport().findChildren(motion.SectionVeil)))
        self.assertFalse(tree.isAnimated())
        tree.tree_motion.set_expanded(group.child(0), True)
        self.assertTrue(group.child(0).isExpanded())
        self.assertEqual(tree.state(), tree.State.NoState)
        self.assertEqual(tree.viewport().findChildren(motion.SectionVeil), [])
