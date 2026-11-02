"""The panels dragged by their titles (R312): the card carried by the pointer as a picture, the drop zones that answer
after a dwell, the slot and the cards sliding aside, the flight into the slot on release, Esc and a release with no
zone flying it home; the central widget never a destination and never dragged; no panel ever out of sight (R294)."""

import unittest

import _setup
from PySide6.QtCore import QAbstractAnimation, QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QWidget

from meridiana.ui import motion
from meridiana.ui.cards import CardDock
from meridiana.ui.design import Motion, Space

setUpModule = _setup.keep_global_state
DIRECT = Qt.FindChildOption.FindDirectChildrenOnly


class DockDragging(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.meridiana_look()
        motion.set_reduced(False)
        self.host = QMainWindow()
        self.addCleanup(_setup.dispose, self.host)
        self.centre = QLabel("Workspace")
        self.host.setCentralWidget(self.centre)
        self.docks = []
        for i, area in enumerate((Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea,
                                  Qt.DockWidgetArea.BottomDockWidgetArea)):
            dock = CardDock(f"Panel {i}", self.host)
            dock.setObjectName(f"panel_{i}")
            body = QLabel("Content\n" * 3)
            body.setMinimumSize(140, 80)
            dock.setWidget(body)
            self.host.addDockWidget(area, dock)
            self.docks.append(dock)
        self.host.resize(1000, 700)
        self.host.show()
        self.settle()

    def tearDown(self):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier:
            QTest.keyRelease(self.host, Qt.Key.Key_Alt)
        motion.set_reduced(False)

    def alt(self, down: bool):
        """Alt pressed (`down`) or let go, at the window, as the keyboard sends it."""
        if down:
            QTest.keyPress(self.host, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier)
        else:
            QTest.keyRelease(self.host, Qt.Key.Key_Alt)

    def settle(self):
        self.assertTrue(_setup.wait_settled(self.app, lambda: [(d.geometry(), d.minimumSize()) for d in self.docks]))

    def lifts(self):
        from meridiana.ui.dock_motion import Lift
        return [lift for lift in self.host.findChildren(Lift, options=DIRECT) if lift.isVisible()]

    def layers(self):
        from meridiana.ui.dock_motion import Reflow
        return [layer for layer in self.host.findChildren(Reflow, options=DIRECT) if layer.isVisible()]

    def take(self, source, grip=None):
        """`source` pressed at `grip` (its title's pixels) and moved past the drag distance: its drag and its title."""
        title = source.title_bar
        grip = grip if grip is not None else title.rect().center()
        QTest.mousePress(title, Qt.MouseButton.LeftButton, pos=grip)
        QTest.mouseMove(title, grip + QPoint(QApplication.startDragDistance() + 4, 0))
        self.assertIsNotNone(source.drag_motion.solver)
        return source.drag_motion, title

    def hover(self, title, at):
        """The pointer moved to `at` (window pixels) and the zone's dwell waited for."""
        drag = title.findChild(type(self.docks[0].drag_motion))
        QTest.mouseMove(title, title.mapFromGlobal(self.host.mapToGlobal(at)))
        self.assertTrue(_setup.wait_until(self.app, lambda: not drag.waiting, 3))

    def quiet(self):
        """Every drag over: no layer, no carried picture, no grab, no solver."""
        self.assertTrue(_setup.wait_until(self.app, lambda: not self.layers() and not self.lifts(), 5))
        self.assertIsNone(QWidget.mouseGrabber())
        self.assertTrue(all(d.drag_motion.solver is None for d in self.docks))

    def all_in_sight(self):
        from meridiana.ui.dock_motion import lost_panels
        self.settle()
        self.assertEqual(lost_panels(self.host), [])
        for dock in self.docks:
            self.assertFalse(dock.isHidden(), dock.objectName())
            self.assertFalse(dock.isFloating(), dock.objectName())
            tabbed = any(not t.isHidden() and self.host.rect().intersects(t.geometry())
                         for t in self.host.tabifiedDockWidgets(dock))
            self.assertTrue(self.host.rect().intersects(dock.geometry()) or tabbed, dock.objectName())

    def card_in_window(self, dock) -> QRect:
        return dock.card_rect().translated(dock.pos())

    # the card taken

    def test_the_card_taken_is_carried_by_the_pointer_from_its_grip_and_nothing_else_moves(self):
        source = self.docks[0]
        before = {d: d.geometry() for d in self.docks}
        state = bytes(self.host.saveState())
        grip = QPoint(40, 10)
        drag, title = self.take(source, grip)
        lift = drag.lift
        self.assertEqual(self.lifts(), [lift])
        self.assertEqual(lift.home, self.card_in_window(source))
        self.assertTrue(_setup.wait_until(self.app, lambda: lift.run is None, 3))          # the rise is over
        self.assertAlmostEqual(lift.scale, lift.SCALE)
        self.assertLess(lift.opacity, 1.0)
        self.assertIsNotNone(lift.cached)                                   # moved as a blit afterwards
        taken = self.host.mapFromGlobal(title.mapToGlobal(grip))
        for at in (QPoint(500, 300), QPoint(620, 410), QPoint(300, 500)):
            QTest.mouseMove(title, title.mapFromGlobal(self.host.mapToGlobal(at)))
            # the grip stays under the pointer: the card's frame moved by exactly the pointer's travel
            self.assertEqual(lift.frame.topLeft(), lift.home.topLeft() + (at - taken))
            self.assertTrue(lift.geometry().contains(at), (lift.geometry(), at))
            self.assertEqual(lift.width(), round(lift.frame.width() * lift.SCALE))
        self.assertEqual({d: d.geometry() for d in self.docks}, before)       # the live panels did not move
        self.assertEqual(bytes(self.host.saveState()), state)
        layer = drag.layer
        self.assertIs(layer.preview_source, source)                           # its home slot shows under it
        self.assertEqual(layer.preview_rect, before[source])
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    def test_the_picture_is_painted_without_a_shadow_and_a_little_larger(self):
        source = self.docks[0]
        drag, title = self.take(source)
        lift = drag.lift
        self.assertTrue(_setup.wait_until(self.app, lambda: lift.run is None, 3))
        picture = lift.grab()
        # the corners outside the rounded card stay clear (no shadow painted around it)
        image = picture.toImage()
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertEqual(image.pixelColor(image.width() - 1, image.height() - 1).alpha(), 0)
        self.assertGreater(lift.width(), lift.frame.width())
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    # the zones

    def test_a_zone_answers_only_after_its_dwell_and_the_cards_make_room(self):
        from meridiana.ui.dock_motion import target_at
        source, anchor = self.docks[0], self.docks[1]
        drag, title = self.take(source)
        at = anchor.geometry().center()
        self.assertIsNotNone(target_at(self.host, source, at))
        home = QRect(anchor.geometry())
        QTest.mouseMove(title, title.mapFromGlobal(self.host.mapToGlobal(at)))
        self.assertIsNone(drag.target)                                        # not yet: the dwell
        self.assertTrue(drag.waiting)
        self.assertEqual(drag.layer.ends[anchor], home)
        _setup.turn_events(self.app, Motion.DWELL // 3)
        self.assertIsNone(drag.target)                                        # a pass over it: nothing dances
        self.assertTrue(_setup.wait_until(self.app, lambda: drag.target is not None, 3))
        self.assertFalse(drag.target.tab)                                     # never a tab without Alt (R317)
        layer = drag.layer
        self.assertIs(layer.preview_source, source)
        self.assertEqual(layer.animation.duration(), Motion.CAREFUL)          # the slow movement
        self.assertNotEqual(layer.preview_rect, drag.lift.home)              # the slot is the zone's
        self.alt(True)
        self.hover(title, at)
        self.assertTrue(drag.target.tab)
        # a tab target: the slot takes the anchor's place and the anchor lies under it, where it is (Qt parks the
        # tab behind at -1500, -625: its picture must not fly there and back)
        self.assertEqual(layer.preview_rect, layer.ends[anchor])
        self.assertTrue(self.host.rect().intersects(layer.ends[anchor]))    # not parked off the window
        # leaving the zone for the middle of the centre: after the dwell everything is back
        self.hover(title, self.centre.geometry().center())
        self.assertIsNone(drag.target)
        self.assertEqual(layer.ends[anchor], home)
        self.assertEqual(layer.preview_rect, source.geometry())
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    def move(self, title, at):
        QTest.mouseMove(title, title.mapFromGlobal(self.host.mapToGlobal(at)))

    def test_a_zone_is_left_only_once_the_pointer_is_well_inside_the_next(self):
        from meridiana.ui.dock_motion import INERTIA
        self.assertEqual(INERTIA, Space.M)
        source, anchor = self.docks[0], self.docks[1]
        drag, title = self.take(source)
        y = anchor.geometry().center().y()
        edge = anchor.geometry().left()
        self.hover(title, QPoint(edge - 40, y))                               # over the centre: no zone
        self.assertIsNone(drag.target)
        self.move(title, QPoint(edge + INERTIA // 2, y))                      # on the panel, by less than INERTIA
        self.assertFalse(drag.waiting)
        self.assertIsNone(drag.pending)
        self.move(title, QPoint(edge + INERTIA + 2, y))                       # well inside: its dwell begins
        self.assertTrue(drag.waiting)
        self.assertIs(drag.pending.anchor, anchor)
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    def test_within_one_panel_the_half_changes_at_once_another_panel_waits(self):
        source, anchor = self.docks[0], self.docks[1]
        drag, title = self.take(source)
        r = anchor.geometry()
        self.hover(title, QPoint(r.center().x(), r.top() + r.height() // 3))
        self.assertTrue(drag.target.before)                                   # above it
        above = QRect(drag.layer.preview_rect)
        self.move(title, QPoint(r.center().x(), r.bottom() - r.height() // 3))
        self.assertFalse(drag.waiting)                                        # the same panel: no dwell...
        self.assertIs(drag.target.anchor, anchor)
        self.assertFalse(drag.target.before)                                  # ...below it, at once
        self.assertNotEqual(drag.layer.preview_rect, above)
        self.move(title, self.docks[2].geometry().center())                   # another panel: its dwell
        self.assertTrue(drag.waiting)
        self.assertIs(drag.target.anchor, anchor)
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    def test_a_split_zone_slides_the_card_in_its_way_aside(self):
        source, anchor = self.docks[0], self.docks[1]
        drag, title = self.take(source)
        home = QRect(anchor.geometry())
        self.hover(title, QPoint(anchor.geometry().center().x(), anchor.geometry().bottom() - 10))
        self.assertFalse(drag.target.tab)
        self.assertEqual(drag.target.orientation, Qt.Orientation.Vertical)
        moved = drag.layer.ends[anchor]
        self.assertLess(moved.height(), home.height())                        # made room below itself
        self.assertEqual(drag.layer.preview_rect.top() > moved.bottom() - 2, True)
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    # tabs only with Alt (R317)

    def grid(self, dock):
        """Points over `dock` away from the window's bands: its quarters and its middle alike."""
        from meridiana.ui.design import Space
        r = dock.geometry().intersected(self.host.rect()).adjusted(Space.XXL + 2, Space.XXL + 2,
                                                                   -Space.XXL - 2, -Space.XXL - 2)
        return [QPoint(r.left() + r.width() * i // 6, r.top() + r.height() * j // 6)
                for i in range(1, 6) for j in range(1, 6)]

    def test_without_alt_a_panel_splits_in_halves_never_a_tab(self):
        from meridiana.ui.dock_motion import target_at
        source, anchor = self.docks[0], self.docks[1]
        for at in self.grid(anchor):
            target = target_at(self.host, source, at)
            self.assertIs(target.anchor, anchor, at)
            self.assertFalse(target.tab, at)
        # the half nearest the point, on the dominant axis of its normalized distances
        r = anchor.geometry()
        cases = ((QPoint(r.center().x(), r.top() + r.height() // 3), Qt.Orientation.Vertical, True),
                 (QPoint(r.center().x(), r.bottom() - r.height() // 3), Qt.Orientation.Vertical, False),
                 (QPoint(r.left() + r.width() // 3, r.center().y()), Qt.Orientation.Horizontal, True))
        for at, orientation, before in cases:
            target = target_at(self.host, source, at)
            self.assertEqual((target.orientation, target.before), (orientation, before), at)

    def test_with_alt_the_whole_panel_is_a_tab_and_the_bands_do_not_change(self):
        from meridiana.ui.dock_motion import target_at
        source, anchor = self.docks[0], self.docks[1]
        for at in self.grid(anchor) + [QPoint(anchor.geometry().left() + 4, anchor.geometry().center().y())]:
            target = target_at(self.host, source, at, tabs=True)
            self.assertEqual((target.anchor, target.tab), (anchor, True), at)
        for at in (QPoint(4, 300), QPoint(500, 4), QPoint(500, self.host.height() - 4)):
            self.assertEqual(target_at(self.host, source, at, tabs=True), target_at(self.host, source, at), at)

    def test_alt_pressed_or_let_go_mid_drag_changes_the_zone_after_its_dwell(self):
        source, anchor = self.docks[0], self.docks[1]
        drag, title = self.take(source)
        at = anchor.geometry().center()
        self.hover(title, at)
        self.assertFalse(drag.target.tab)
        self.alt(True)                                                        # the pointer still
        self.assertTrue(drag.waiting)
        self.assertTrue(drag.pending.tab)
        self.assertFalse(drag.target.tab)                                     # not yet: the dwell
        self.assertTrue(_setup.wait_until(self.app, lambda: not drag.waiting, 3))
        self.assertTrue(drag.target.tab)
        self.alt(False)
        self.assertTrue(drag.waiting)
        self.assertTrue(_setup.wait_until(self.app, lambda: not drag.waiting, 3))
        self.assertFalse(drag.target.tab)
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    def test_alt_during_a_drag_does_not_show_the_menus_and_the_status_bar_says_it(self):
        from PySide6.QtWidgets import QMenuBar, QVBoxLayout
        from meridiana.i18n import _
        from meridiana.ui.menubar import AltMenus
        status = self.host.statusBar()
        status.show()
        bar = QMenuBar()
        bar.addMenu("&File").addAction("Open")
        holder = QWidget()
        home = QVBoxLayout(holder)
        menus = AltMenus(self.host, bar, home)
        menus.set_always(False)
        self.settle()
        source = self.docks[0]
        drag, title = self.take(source)
        self.assertEqual(status.currentMessage(), _("Alt: as tabs"))
        self.alt(True)
        self.alt(False)                                                       # Alt alone: the menus' key, not now
        self.app.processEvents()
        self.assertFalse(menus.shown)
        self.assertFalse(menus.alone)
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()
        self.assertEqual(status.currentMessage(), "")
        self.alt(True)                                                        # after the drag: the menus' again
        self.assertTrue(menus.alone)                                          # (a release would show them)
        menus.alone = False
        self.alt(False)

    # one target where a band of the window and a panel's side are the same place (R317)

    def test_a_band_over_a_panel_docked_there_is_that_panel_s_outer_side(self):
        from meridiana.ui.design import Space
        from meridiana.ui.dock_motion import DockTarget, target_at
        h = self.host.height()
        bottom, left = self.docks[2], self.docks[0]
        cases = ((self.docks[0], QPoint(500, h - 4), QPoint(500, h - Space.XXL - 4),
                  DockTarget(Qt.DockWidgetArea.BottomDockWidgetArea, bottom, Qt.Orientation.Vertical)),
                 (self.docks[1], QPoint(4, 300), QPoint(Space.XXL + 4, 300),
                  DockTarget(Qt.DockWidgetArea.LeftDockWidgetArea, left, Qt.Orientation.Horizontal, before=True)))
        for source, band, inside, wanted in cases:
            self.assertEqual(target_at(self.host, source, band), wanted, band)
            self.assertEqual(target_at(self.host, source, inside), wanted, inside)     # the same, a step inside
        # an empty band stays the band: nothing at the top, and the right holds only the card carried
        self.assertEqual(target_at(self.host, self.docks[0], QPoint(500, 4)),
                         DockTarget(Qt.DockWidgetArea.TopDockWidgetArea))
        self.assertEqual(target_at(self.host, self.docks[1], QPoint(self.host.width() - 4, 300)),
                         DockTarget(Qt.DockWidgetArea.RightDockWidgetArea))

    def test_crossing_from_the_band_to_the_panel_s_side_does_not_move_the_slot(self):
        from meridiana.ui.design import Space
        source = self.docks[0]
        drag, title = self.take(source)
        h = self.host.height()
        self.hover(title, QPoint(500, h - 4))
        shown, layer = drag.target, drag.layer
        retargets = []
        layer.animation.stateChanged.connect(lambda *a: retargets.append(a))
        for y in (h - Space.XXL - 4, h - 3, h - Space.XXL + 1, h - Space.XXL - 1, h - 6):
            QTest.mouseMove(title, title.mapFromGlobal(self.host.mapToGlobal(QPoint(500, y))))
            self.assertIs(drag.target, shown, y)
            self.assertFalse(drag.waiting, y)                                 # nothing waits, nothing slides
        _setup.turn_events(self.app, Motion.DWELL + Motion.CAREFUL)
        self.assertEqual([state for state in retargets
                          if state[0] == QAbstractAnimation.State.Running], [])
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    # the release

    def test_released_the_picture_flies_into_the_slot_and_the_layout_changes_only_then(self):
        source, anchor = self.docks[0], self.docks[1]
        state = bytes(self.host.saveState())
        drag, title = self.take(source)
        self.hover(title, QPoint(anchor.geometry().center().x(), anchor.geometry().bottom() - 10))
        slot = drag.layer.card_rect(drag.layer.ends[source])
        lift, layer = drag.lift, drag.layer
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.assertIsNone(drag.solver)
        self.assertIsNone(QWidget.mouseGrabber())
        self.assertEqual(lift.animation.state(), QAbstractAnimation.State.Running)
        self.assertEqual(lift.animation.duration(), Motion.CAREFUL)
        self.assertEqual(lift.run[1], slot)                                   # flying into the slot shown
        self.assertEqual(bytes(self.host.saveState()), state)                 # not yet committed
        self.assertTrue(layer.isVisible())
        self.assertIs(layer.preview_source, source)                           # the slot stays until it lands
        self.assertTrue(_setup.wait_until(self.app, lambda: bytes(self.host.saveState()) != state, 3))
        self.assertEqual(lift.scale, 1.0)                                     # landed: the layout committed...
        self.assertEqual(lift.run[5], 0.0)                                    # ...and the picture dissolving
        self.quiet()
        self.all_in_sight()
        # no jump: the real card lies where the picture came to rest
        landed = self.card_in_window(source)
        for value, wanted in zip(landed.getRect(), slot.getRect(), strict=True):
            self.assertLessEqual(abs(value - wanted), 2, (landed, slot))
        self.assertLess(anchor.geometry().bottom(), source.geometry().top())

    def test_a_release_before_the_dwell_goes_where_the_slot_was_not_where_the_pointer_passed(self):
        source, anchor = self.docks[0], self.docks[1]
        state = bytes(self.host.saveState())
        drag, title = self.take(source)
        QTest.mouseMove(title, title.mapFromGlobal(anchor.mapToGlobal(anchor.rect().center())))
        self.assertTrue(drag.waiting)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)                  # let go at once: home it flies
        self.quiet()
        self.assertEqual(bytes(self.host.saveState()), state)
        self.all_in_sight()

    def test_escape_flies_the_card_home_and_leaves_everything_as_it_was(self):
        source, anchor = self.docks[0], self.docks[1]
        state = bytes(self.host.saveState())
        before = {d: d.geometry() for d in self.docks}
        visibility = []
        for dock in self.docks:
            dock.visibilityChanged.connect(visibility.append)
        drag, title = self.take(source)
        self.hover(title, anchor.geometry().center())
        lift, layer = drag.lift, drag.layer
        QTest.keyClick(title, Qt.Key.Key_Escape)
        self.assertIsNone(drag.solver)
        self.assertEqual(lift.run[1], layer.card_rect(before[source]))         # home
        self.assertEqual(layer.ends[anchor], before[anchor])                  # the cards slide back
        self.assertEqual(layer.animation.duration(), Motion.CAREFUL)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()
        self.assertEqual(bytes(self.host.saveState()), state)
        self.assertEqual({d: d.geometry() for d in self.docks}, before)
        self.assertEqual(visibility, [])

    def test_a_release_over_no_zone_is_a_cancel(self):
        source = self.docks[0]
        state = bytes(self.host.saveState())
        drag, title = self.take(source)
        self.hover(title, self.centre.geometry().center())
        self.assertIsNone(drag.target)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()
        self.assertEqual(bytes(self.host.saveState()), state)
        self.all_in_sight()

    # the centre

    def test_the_central_area_is_never_a_destination(self):
        from meridiana.ui.dock_motion import target_at
        source = self.docks[0]
        r = self.centre.geometry()
        for at in (r.center(), QPoint(r.left() + 40, r.center().y()), QPoint(r.center().x(), r.top() + 40),
                   QPoint(r.right() - 40, r.bottom() - 40)):
            self.assertIsNone(target_at(self.host, source, at), at)
        drag, title = self.take(source)
        self.hover(title, r.center())
        self.assertIsNone(drag.target)
        self.assertEqual(drag.layer.preview_rect, source.geometry())          # only its home slot
        QTest.keyClick(title, Qt.Key.Key_Escape)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    def test_the_central_card_cannot_be_dragged(self):
        from meridiana.ui.dock_motion import DockDrag
        self.assertFalse(hasattr(self.centre, "drag_motion"))
        self.assertEqual(self.centre.findChildren(DockDrag), [])
        state = bytes(self.host.saveState())
        QTest.mousePress(self.centre, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        QTest.mouseMove(self.centre, QPoint(200, 200))
        QTest.mouseRelease(self.centre, Qt.MouseButton.LeftButton, pos=QPoint(200, 200))
        self.app.processEvents()
        self.assertEqual(self.layers(), [])
        self.assertEqual(self.lifts(), [])
        self.assertEqual(bytes(self.host.saveState()), state)
        # a dock set as the central widget would refuse too
        extra = CardDock("Centre", self.host)
        extra.setObjectName("centre_dock")
        extra.setWidget(QLabel("x"))
        self.host.setCentralWidget(extra)
        self.centre = extra
        self.settle()
        title = extra.title_bar
        QTest.mousePress(title, Qt.MouseButton.LeftButton, pos=title.rect().center())
        QTest.mouseMove(title, title.rect().center() + QPoint(60, 60))
        self.assertIsNone(extra.drag_motion.origin)
        self.assertIsNone(extra.drag_motion.solver)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.assertEqual(self.lifts(), [])

    # nothing disappears (R294)

    def test_every_drop_leaves_every_panel_in_sight_and_the_saved_layout_valid(self):
        from meridiana.ui.dock_motion import lost_panels
        cases = (("tab", 0, lambda a: a.geometry().center()),
                 ("split before", 0, lambda a: QPoint(a.geometry().left() + 10, a.geometry().center().y())),
                 ("bottom band", 1, lambda a: QPoint(self.host.width() // 2, self.host.height() - 4)),
                 ("top band", 2, lambda a: QPoint(self.host.width() // 2, 4)),
                 ("left band", 1, lambda a: QPoint(4, self.host.height() // 2)))
        initial = self.host.saveState()
        for name, index, where in cases:
            with self.subTest(name):
                self.host.restoreState(initial)
                self.settle()
                source = self.docks[index]
                anchor = self.docks[(index + 1) % 3]
                drag, title = self.take(source)
                self.alt(name == "tab")
                self.hover(title, where(anchor))
                self.assertIsNotNone(drag.target, name)
                self.assertEqual(drag.target.tab, name == "tab", name)
                QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
                self.alt(False)
                self.quiet()
                self.all_in_sight()
                state = self.host.saveState()
                self.assertTrue(self.host.restoreState(state))
                self.settle()
                self.assertEqual(lost_panels(self.host), [])

    def test_a_drop_that_would_lose_a_panel_is_not_kept(self):
        from unittest import mock
        from meridiana.ui import dock_motion
        source, anchor = self.docks[0], self.docks[1]
        state = bytes(self.host.saveState())
        drag, title = self.take(source)
        self.hover(title, anchor.geometry().center())
        real = dock_motion.lost_panels
        answers = iter([[anchor]])
        with mock.patch.object(dock_motion, "lost_panels", lambda w: next(answers, None) or real(w)):
            QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
            self.quiet()
        self.assertEqual(bytes(self.host.saveState()), state)                 # the layout before the drop
        self.all_in_sight()

    def test_cancel_drags_takes_the_picture_away_too(self):
        from meridiana.ui.dock_motion import cancel_drags
        source = self.docks[0]
        drag, title = self.take(source)
        cancel_drags(self.host)
        self.app.processEvents()
        self.assertEqual(self.lifts(), [])
        self.assertEqual(self.layers(), [])
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.quiet()

    # less motion

    def test_with_less_motion_the_card_is_still_carried_and_lands_at_once(self):
        motion.set_reduced(True)
        source, anchor = self.docks[0], self.docks[1]
        drag, title = self.take(source)
        lift = drag.lift
        self.assertIsNotNone(lift)
        self.assertIsNone(lift.run)                                           # no rise played
        self.alt(True)
        self.hover(title, anchor.geometry().center())                         # the dwell is kept
        self.assertTrue(drag.target.tab)
        QTest.mouseRelease(title, Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertEqual(self.host.tabifiedDockWidgets(source), [anchor])      # landed in the same turn
        self.quiet()
        self.all_in_sight()

    def test_the_durations_are_named_and_slower_than_the_others(self):
        self.assertGreater(Motion.CAREFUL, Motion.SLOW)
        self.assertGreater(Motion.DWELL, Motion.NORMAL)
