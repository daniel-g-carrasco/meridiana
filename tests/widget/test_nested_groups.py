"""Groups inside groups, and scroll areas inside groups, offscreen with the real theme: a fold never leaves its fields
squeezed (photo 51, R341), the bars inside a group are the program's (R339), a group inside a group is no card (R343),
a section is as tall as its content and opens as one movement (R337, R338), nothing is cut at the right at any width
of the panel (R341), the three sections alike (R342)."""

import unittest

import _setup
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtWidgets import (QFormLayout, QLabel, QListWidget, QPushButton, QScrollArea, QStyle, QVBoxLayout,
                               QWidget)

setUpModule = _setup.keep_global_state


def look(theme="light"):
    _setup.meridiana_look(theme)
    return _setup.qt_or_skip()


class Actions(dict):
    """Every command the panel asks for, with its long words where the width is what is tried."""

    def __init__(self):
        super().__init__()
        for cid in ("strings_auto", "strings_manual", "strings_clear", "battery_catalog"):
            self[cid]

    def __missing__(self, key):
        from PySide6.QtGui import QAction
        self[key] = QAction(key + " with the long words of a command")
        return self[key]


class FoldLeavesNoLayoutBehind(unittest.TestCase):
    """Photo 51: the group's fields laid out in the closed group when its body was shown, and held there."""

    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def setUp(self):
        from meridiana.ui import motion
        from meridiana.ui.style import Group
        motion.set_reduced(False)
        self.addCleanup(motion.set_reduced, False)
        self.page = QWidget()
        self.addCleanup(_setup.dispose, self.page)
        box = QVBoxLayout(self.page)
        self.group = Group("Strings")
        inner = QVBoxLayout(self.group)
        words = QLabel("A sentence long enough to be wrapped onto more than one line of the group")
        words.setWordWrap(True)                 # the group's layout then has a height for a width, as the Strings'
        inner.addWidget(words)
        self.rows = [words]
        for k in range(5):
            b = QPushButton(f"Command {k}")
            inner.addWidget(b)
            self.rows.append(b)
        box.addWidget(self.group)
        box.addStretch(1)
        self.page.resize(300, 500)
        self.page.show()
        _setup.turn_events(self.app, 50)

    def spread(self):
        return [b.geometry().top() for b in self.rows], [b.height() for b in self.rows]

    def test_closed_and_opened_the_fields_are_back_where_they_were(self):
        before = self.spread()
        self.group.set_expanded(False)
        _setup.turn_events(self.app, 300)
        self.group.set_expanded(True)
        _setup.turn_events(self.app, 300)
        self.assertEqual(self.spread(), before)

    def test_while_it_opens_the_fields_stand_at_their_places_and_only_the_edge_moves(self):
        before = self.spread()
        self.group.set_expanded(False)
        _setup.turn_events(self.app, 300)
        self.group.set_expanded(True)
        seen = []
        timer = QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: seen.append(self.spread()))
        timer.start()
        _setup.turn_events(self.app, 120)
        timer.stop()
        self.assertTrue(seen)
        for frame in seen:
            self.assertEqual(frame, before)


class FoldInTheWindow(unittest.TestCase):
    """Photo 51 itself: the Strings' group closed and opened in the Plant's panel of the window. Showing the body asked
    the group's own layout first, which pressed the body into the closed group: the fields were laid out there, in
    118 px of 248, and the layout held them there through the movement and after it."""

    def test_the_rows_of_the_strings_come_back_whole_and_stand_still_while_it_opens(self):
        from _fixtures import capannone

        from meridiana.ui import motion
        self.app = _setup.qt_or_skip()
        _setup.window(self, capannone(), size=(1600, 900))
        motion.set_reduced(False)
        self.addCleanup(motion.set_reduced, False)
        self.win.show_phase("plant")
        _setup.turn_events(self.app, 300)
        side = next(w for w in self.app.allWidgets() if type(w).__name__ == "PlantSide")
        side.open("inverter")
        _setup.turn_events(self.app, 300)
        panel = side.inverters
        g = panel.strings_group
        rows = [panel.state, panel.working_inverter, panel.list] + list(panel.string_buttons.values())
        before = [r.geometry().getRect() for r in rows]
        g.set_expanded(False)
        _setup.turn_events(self.app, 300)
        g.set_expanded(True)
        self.assertEqual([r.geometry().getRect() for r in rows], before)        # at once, under the edge that moves
        _setup.turn_events(self.app, 300)
        self.assertEqual([r.geometry().getRect() for r in rows], before)
        self.assertGreaterEqual(panel.list.height(), panel.list.sizeHint().height())


class ScrollBarsInsideGroups(unittest.TestCase):
    """R339: a style set on a group goes down to everything inside it under a global sheet."""

    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def test_an_area_inside_a_group_has_the_programs_bar_and_keeps_its_room(self):
        from meridiana.ui.design import Size
        from meridiana.ui.style import Group
        top = QWidget()
        self.addCleanup(_setup.dispose, top)
        outer = QVBoxLayout(top)
        group = Group("Outer")
        inner = QVBoxLayout(group)
        area = QScrollArea()
        listed = QListWidget()
        inner.addWidget(area)
        inner.addWidget(listed)
        outer.addWidget(group)
        top.resize(300, 400)
        top.show()
        _setup.turn_events(self.app, 50)
        self.assertEqual(area.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)     # keep_room
        for view in (area, listed):
            bar = view.verticalScrollBar()
            extent = bar.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent, None, bar)
            self.assertLessEqual(extent, Size.SCROLLBAR + 8, type(view).__name__)
            self.assertNotEqual(extent, 14)                             # Fusion's
        # the plain area alone in the window measures the same
        alone = QScrollArea()
        self.addCleanup(_setup.dispose, alone)
        alone.show()
        _setup.turn_events(self.app, 20)
        self.assertEqual(area.verticalScrollBar().width(), alone.verticalScrollBar().width())

    def test_the_groups_style_is_the_applications_with_the_groups_drawn(self):
        from meridiana.ui.scrollbars import ScrollStyle
        from meridiana.ui.style import MeridianaStyle
        self.assertTrue(issubclass(MeridianaStyle, ScrollStyle))


class NestedGroupsAreNoCards(unittest.TestCase):
    """R343: one rule, in Group."""

    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def setUp(self):
        from meridiana.ui import motion
        from meridiana.ui.style import Group, _FOLDED
        _FOLDED.clear()
        self.addCleanup(_FOLDED.clear)
        motion.set_reduced(True)
        self.addCleanup(motion.set_reduced, False)
        self.top = QWidget()
        self.addCleanup(_setup.dispose, self.top)
        outer = QVBoxLayout(self.top)
        self.parent_group = Group("Parent")
        parent_box = QVBoxLayout(self.parent_group)
        self.parent_text = QLabel("Parent's text")
        parent_box.addWidget(self.parent_text)
        self.child = Group("Child")
        child_form = QFormLayout(self.child)
        child_form.setContentsMargins(8, 4, 8, 8)          # as the Properties' lead does: the rule goes over it
        self.child_text = QLabel("Child's text")
        child_form.addRow(self.child_text)
        parent_box.addWidget(self.child)
        outer.addWidget(self.parent_group)
        outer.addStretch(1)
        self.top.resize(400, 400)
        self.top.show()
        _setup.turn_events(self.app, 60)

    def test_only_the_inner_group_is_nested(self):
        self.assertFalse(self.parent_group.nested)
        self.assertTrue(self.child.nested)

    def test_its_content_stands_on_the_parents_text_with_no_margin_of_its_own(self):
        left = self.parent_text.mapTo(self.top, QPoint(0, 0)).x()
        self.assertEqual(self.child_text.mapTo(self.top, QPoint(0, 0)).x(), left)
        self.assertEqual(self.child.mapTo(self.top, QPoint(0, 0)).x(), left)

    def test_no_frame_no_band_a_strong_title_and_a_thin_line(self):
        from PySide6.QtGui import QColor

        from meridiana.ui.style import MeridianaStyle, shared
        t = shared().tokens
        image = self.child.grab().toImage()
        h = MeridianaStyle.head(self.child)
        ground = self.top.grab().toImage().pixelColor(2, 2)
        # no band behind the title, no frame on the sides or at the foot
        for x, y in ((self.child.width() // 2, 3), (self.child.width() - 40, h // 2), (0, h + 8),
                     (self.child.width() - 1, h + 8), (self.child.width() // 2, self.child.height() - 1)):
            colour = image.pixelColor(x, y)
            self.assertNotEqual(colour.name(), QColor(t["line_soft"]).name(), (x, y))
            self.assertNotEqual(colour.name(), QColor(t["line"]).name(), (x, y))
        # the line under the title, the whole width
        self.assertEqual(image.pixelColor(self.child.width() // 2, h - 1).name(), QColor(t["line"]).name())
        self.assertIsNotNone(ground)
        # the parent keeps its card
        parent = self.parent_group.grab().toImage()
        self.assertEqual(parent.pixelColor(self.parent_group.width() // 2, 3).name(), QColor(t["line_soft"]).name())

    def test_it_folds_with_its_chevron_and_the_header_alone_stays(self):
        from meridiana.ui.style import MeridianaStyle
        self.child.set_expanded(False, 0)
        _setup.turn_events(self.app, 30)
        self.assertLessEqual(self.child.height(), MeridianaStyle.head(self.child) + 1)
        self.child.set_expanded(True, 0)

    def test_taken_out_of_the_group_it_is_a_card_again_with_the_margins_it_had(self):
        self.child.setParent(None)
        self.addCleanup(_setup.dispose, self.child)
        self.child.show()
        _setup.turn_events(self.app, 30)
        self.assertFalse(self.child.nested)
        m = self.child.layout().contentsMargins()
        self.assertEqual((m.left(), m.top(), m.right(), m.bottom()), (8, 4, 8, 8))

    def test_inside_a_scroll_area_inside_a_group_it_is_nested_all_the_same(self):
        from meridiana.ui.style import Group
        area = QScrollArea()
        area.setWidgetResizable(True)
        page = QWidget()
        box = QVBoxLayout(page)
        deep = Group("Deep")
        QVBoxLayout(deep).addWidget(QLabel("x"))
        box.addWidget(deep)
        area.setWidget(page)
        self.parent_group.layout().addWidget(area)
        _setup.turn_events(self.app, 60)
        self.assertTrue(deep.nested)
        self.assertEqual(deep.layout().contentsMargins().left(), 0)


def inspector_with_side(app, width=300, height=700):
    from meridiana.ui.plant_page import PlantInspector, PlantSide
    side = PlantSide(PlantInspector(Actions()), Actions(), lambda: None)
    side.resize(width, height)
    side.show()
    _setup.turn_events(app, 80)
    return side


class SectionsAsTallAsTheirContent(unittest.TestCase):
    """R337, R338, R342."""

    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def setUp(self):
        from meridiana.ui import motion
        from meridiana.ui.style import _FOLDED
        _FOLDED.clear()
        self.addCleanup(_FOLDED.clear)
        self.addCleanup(motion.set_reduced, False)
        motion.set_reduced(True)
        self.side = inspector_with_side(self.app)
        self.addCleanup(_setup.dispose, self.side)

    def test_a_short_section_leaves_the_rest_of_the_panel_out_of_every_frame(self):
        side = self.side
        for sid in ("panels", "storage"):
            side.open(sid, ms=0)
            _setup.turn_events(self.app, 60)
            section = side.sections[sid]
            self.assertLess(section.height(), 160, sid)
            bottom = max(s.geometry().bottom() for s in side.sections.values())
            self.assertLess(bottom, side.height() - 300, sid)

    def test_a_section_taller_than_the_panel_takes_the_panel_and_scrolls(self):
        side = self.side
        side.resize(300, 320)
        side.open("inverter", ms=0)
        _setup.turn_events(self.app, 80)
        total = max(s.geometry().bottom() for s in side.sections.values())
        self.assertLessEqual(total, side.height())
        self.assertGreater(side.inverters.verticalScrollBar().maximum(), 0)
        self.assertLessEqual(side.sections["storage"].height(), 30)     # closed, still its header

    def test_a_section_that_fits_does_not_scroll_and_follows_what_it_holds(self):
        side = self.side
        side.resize(300, 1200)
        side.open("inverter", ms=0)
        _setup.turn_events(self.app, 80)
        insp = side.inverters
        self.assertEqual(insp.verticalScrollBar().maximum(), 0)
        before = side.sections["inverter"].height()
        insp.strings_group.set_expanded(False, 0)
        _setup.turn_events(self.app, 60)
        self.assertLess(side.sections["inverter"].height(), before - 40)
        self.assertEqual(insp.verticalScrollBar().maximum(), 0)

    def test_the_three_sections_have_the_same_margins_text_and_buttons(self):
        from meridiana.ui.design import Text
        side = self.side
        side.resize(320, 900)
        lefts, rights = {}, {}
        widgets = {"panels": side.panels_hint, "inverter": side.inverters.totals, "storage": side.storage_text}
        for sid, label in widgets.items():
            side.open(sid, ms=0)
            _setup.turn_events(self.app, 60)
            section = side.sections[sid]
            x = label.mapTo(section, QPoint(0, 0)).x() + label.contentsMargins().left()
            lefts[sid] = x
            rights[sid] = section.width() - x - (label.width() - label.contentsMargins().left())
        self.assertEqual(len(set(lefts.values())), 1, lefts)
        self.assertEqual(len(set(rights.values())), 1, rights)
        side.open("storage", ms=0)
        _setup.turn_events(self.app, 60)
        self.assertEqual(side.configure.width(), side.storage_text.width())       # the whole width, as the others'
        side.open("inverter", ms=0)
        _setup.turn_events(self.app, 60)
        self.assertEqual(side.inverters.inverter_buttons["inverter_auto"].width(), side.inverters.totals.width())
        fonts = {side.panels_hint.font().pixelSize(), side.storage_text.font().pixelSize(),
                 side.inverters.totals.font().pixelSize()}
        self.assertEqual(len(fonts), 1)
        self.assertEqual(side.panels_hint.property("text-tone"), side.inverters.totals.property("text-tone"))
        self.assertEqual(side.storage_text.property("text-tone"), side.inverters.totals.property("text-tone"))
        self.assertIsNotNone(Text.DESCRIPTION)

    def test_no_title_twice_in_the_inverter_section(self):
        from PySide6.QtWidgets import QGroupBox
        side = self.side
        titles = [g.title() for g in side.sections["inverter"].findChildren(QGroupBox)]
        self.assertNotIn(side.sections["inverter"].title(), titles)


class OpeningIsOneMovement(unittest.TestCase):
    """R338, frame by frame."""

    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def setUp(self):
        from meridiana.ui import motion
        from meridiana.ui.style import _FOLDED
        _FOLDED.clear()
        self.addCleanup(_FOLDED.clear)
        self.addCleanup(motion.set_reduced, False)
        motion.set_reduced(True)
        self.side = inspector_with_side(self.app, 300, 900)
        self.addCleanup(_setup.dispose, self.side)

    def record(self, sid):
        from meridiana.ui import motion
        side = self.side
        motion.set_reduced(False)
        frames = []
        timer = QTimer()
        timer.setInterval(8)
        timer.timeout.connect(lambda: frames.append({k: (s.y(), s.height()) for k, s in side.sections.items()}))
        timer.start()
        side.open(sid)
        _setup.turn_events(self.app, 330)
        timer.stop()
        motion.set_reduced(True)
        return frames

    def test_the_headers_only_go_up_or_down_once_and_the_section_grows_from_its_header(self):
        for first, second in (("panels", "inverter"), ("inverter", "storage"), ("storage", "panels"),
                              ("inverter", "panels")):
            self.side.open(first, ms=0)
            _setup.turn_events(self.app, 60)
            frames = self.record(second)
            self.assertGreater(len(frames), 5)
            for sid in self.side.sections:
                ys = [f[sid][0] for f in frames]
                steps = [b - a for a, b in zip(ys, ys[1:]) if b != a]
                self.assertTrue(all(s > 0 for s in steps) or all(s < 0 for s in steps),
                                f"{first}->{second} {sid} goes back and forth: {ys}")
            heights = [f[second][1] for f in frames]
            self.assertEqual(heights, sorted(heights), f"{first}->{second}: {heights}")
            # never past the panel's foot, and the last frame is the height at rest
            for frame in frames:
                self.assertLessEqual(max(y + h for y, h in frame.values()), self.side.height())
            _setup.turn_events(self.app, 60)
            self.assertEqual(frames[-1][second][1], self.side.sections[second].height())

    def test_a_section_taller_than_the_panel_opens_to_the_room_there_is(self):
        self.side.resize(300, 340)
        self.side.open("panels", ms=0)
        _setup.turn_events(self.app, 60)
        frames = self.record("inverter")
        heights = [f["inverter"][1] for f in frames]
        self.assertEqual(heights, sorted(heights), heights)
        self.assertLessEqual(max(y + h for y, h in frames[-1].values()), 340)


class NothingCutAtTheRight(unittest.TestCase):
    """R341: the page never wider than the panel lets it."""

    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def test_from_the_panels_minimum_up_the_page_fits_and_the_rows_keep_their_height(self):
        from meridiana import i18n
        from meridiana.ui import motion
        from meridiana.ui.style import _FOLDED
        _FOLDED.clear()
        self.addCleanup(_FOLDED.clear)
        motion.set_reduced(True)
        self.addCleanup(motion.set_reduced, False)
        self.addCleanup(i18n.setup, i18n.language())
        i18n.setup("it")
        side = inspector_with_side(self.app, 300, 900)
        self.addCleanup(_setup.dispose, side)
        side.open("inverter", ms=0)
        _setup.turn_events(self.app, 60)
        insp = side.inverters
        floor = side.minimumSizeHint().width()
        self.assertLessEqual(floor, 200)
        for width in (floor, 200, 240, 276, 320, 420):
            side.resize(width, 900)
            _setup.turn_events(self.app, 60)
            self.assertLessEqual(insp.widget().width(), insp.viewport().width(), width)
            for b in list(insp.inverter_buttons.values()) + list(insp.string_buttons.values()):
                self.assertGreaterEqual(b.height(), b.heightForWidth(b.width()), f"{width}: {b.text()}")
                self.assertLessEqual(b.mapTo(insp.widget(), QPoint(b.width(), 0)).x(), insp.viewport().width())


class WrappedButton(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = look()

    def test_a_long_command_goes_onto_two_lines_and_keeps_its_whole_text(self):
        from meridiana.ui.style import wrap_button
        top = QWidget()
        self.addCleanup(_setup.dispose, top)
        box = QVBoxLayout(top)
        b = QPushButton("Choose the inverters automatically and much more")
        wrap_button(b)
        box.addWidget(b)
        box.addStretch(1)
        one = b.sizeHint().height()
        self.assertLess(b.minimumSizeHint().width(), b.fontMetrics().horizontalAdvance(b.text()) / 2)
        top.resize(140, 300)
        top.show()
        _setup.turn_events(self.app, 40)
        self.assertGreater(b.height(), one)
        self.assertEqual(b.text(), "Choose the inverters automatically and much more")
        wide = b.heightForWidth(1000)
        self.assertEqual(wide, one)


if __name__ == "__main__":
    unittest.main()
