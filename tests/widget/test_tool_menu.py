"""The divided button of the phase's bar (R333, Daniel 03/11/2026: «parte divisa»; study 26, G2 and section 4), a widget alone
with its actions: two parts, each its state, and the seven rules of what is on its face."""

import unittest

import _setup

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QContextMenuEvent, QIcon
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStackedWidget, QToolButton, QWidget

from meridiana import phases
from meridiana.ui import motion
from meridiana.ui.design import Bar, Space
from meridiana.ui.phasebar import PhaseBar, ToolButton, ToolMenuButton


setUpModule = _setup.keep_global_state


class Family(unittest.TestCase):
    """Two modes of drawing, in a group as the tools are, and a command run once."""

    def setUp(self):
        self.app = _setup.qt_or_skip()
        motion.set_reduced(True)
        self.addCleanup(motion.set_reduced, False)
        self.host = QWidget()
        self.addCleanup(self.host.deleteLater)
        self.host.resize(300, 120)
        self.group = QActionGroup(self.host)
        self.other = self.action("Select", checkable=True)
        self.area = self.action("Area", checkable=True, key="S")
        self.row = self.action("Row", checkable=True, key="L")
        self.once = self.action("Once")
        self.ran = []
        self.once.triggered.connect(lambda _c=False: self.ran.append("once"))
        self.area.triggered.connect(lambda _c=False: self.ran.append("area"))
        self.button = self.make([("area", "Area", self.area), ("row", "Row", self.row), ("once", "Once", self.once)])

    def action(self, text, checkable=False, key=""):
        a = QAction(text, self.host, checkable=checkable)
        a.setIcon(QIcon())
        a.setToolTip(f"{text} ({key})\nWhat it does" if key else text)
        if checkable:
            self.group.addAction(a)
        return a

    def make(self, family, **more):
        b = ToolMenuButton(family, parent=self.host, **more)
        b.fit(Bar.UNDER, 50, 64)
        self.host.show()
        self.app.processEvents()
        return b

    def menu_of(self, trigger, button=None):
        button = button or self.button
        seen = []

        def look():
            if button.commands.isVisible():
                seen.append([a.text() for a in button.commands.actions() if not a.isSeparator()])
            button.commands.close()
        QTimer.singleShot(50, look)
        trigger()
        self.app.processEvents()
        return seen


class TheTwoParts(Family):
    def nothing_under_the_pointer(self):
        """Offscreen the cursor stands at (10, 10), on the button of a window placed there."""
        for part in (self.button, self.button.face, self.button.strip):
            part.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, False)

    def test_the_strip_is_as_tall_as_the_button_and_of_its_own_width(self):
        self.assertEqual(self.button.strip.size().toTuple(), (Bar.STRIP, self.button.height()))
        self.assertEqual(self.button.face.width() + self.button.strip.width(), self.button.width())

    def test_a_click_on_the_face_runs_the_command_and_opens_nothing(self):
        QTest.mouseClick(self.button.face, Qt.MouseButton.LeftButton)
        self.assertEqual(self.ran, ["area"])
        self.assertFalse(self.button.commands.isVisible())

    def test_a_press_on_the_strip_opens_the_menu_and_runs_nothing(self):
        strip = self.button.strip
        seen = self.menu_of(lambda: QTest.mousePress(strip, Qt.MouseButton.LeftButton))
        self.assertEqual(seen, [["Area", "Row", "Once"]])
        self.assertEqual(self.ran, [])
        self.assertFalse(strip.isDown())

    def test_the_right_button_opens_the_menu_anywhere_on_the_button_and_runs_nothing(self):
        for part in (self.button.face, self.button.strip):
            at = part.rect().center()
            event = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, at, part.mapToGlobal(at))
            seen = self.menu_of(lambda p=part, e=event: QApplication.sendEvent(p, e))
            self.assertEqual(seen, [["Area", "Row", "Once"]], part.objectName())
        self.assertEqual(self.ran, [])

    def test_with_the_command_off_the_strip_stays_alive(self):
        self.area.setEnabled(False)
        self.app.processEvents()
        self.assertFalse(self.button.face.isEnabled())
        self.assertTrue(self.button.strip.isEnabled())
        seen = self.menu_of(lambda: QTest.mousePress(self.button.strip, Qt.MouseButton.LeftButton))
        self.assertEqual(seen, [["Area", "Row", "Once"]])

    def test_the_things_gone_are_gone(self):
        self.assertFalse(hasattr(ToolMenuButton, "arrow_rect"))
        self.assertFalse(hasattr(ToolMenuButton, "_still_usable"))
        self.assertEqual(self.button.face.popupMode(), QToolButton.ToolButtonPopupMode.DelayedPopup)
        self.assertIsNone(self.button.face.menu())              # no menu: a long press only presses

    def test_under_the_pointer_both_parts_light_and_only_their_difference_divides_them(self):
        """Offscreen a widget takes its hover from the mouse moved to it. Daniel, 03/11/2026: the layer on both parts,
        the one under the pointer a little different, the same when pressed, no line."""
        _setup.meridiana_look()
        self.host.resize(300, 120)
        self.button.fit(Bar.UNDER, 50, 64)
        self.app.processEvents()
        face_x, strip_x, y = 10, self.button.face.width() + 2, 3

        def colours():
            picture = self.button.grab().toImage()
            return picture.pixelColor(face_x, y).name(), picture.pixelColor(strip_x, y).name()

        def under(part, on):
            part.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, on)
        self.nothing_under_the_pointer()
        rest = colours()
        self.assertEqual(rest[0], rest[1])
        self.button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)
        self.addCleanup(self.button.setAttribute, Qt.WidgetAttribute.WA_UnderMouse, False)
        for part, mine in ((self.button.face, 0), (self.button.strip, 1)):
            under(part, True)
            over = colours()
            self.assertNotEqual(over[0], rest[0], part.objectName())
            self.assertNotEqual(over[1], rest[1], part.objectName())
            self.assertNotEqual(over[0], over[1], part.objectName())
            part.setDown(True)
            pressed = colours()
            part.setDown(False)
            under(part, False)
            self.assertNotEqual(pressed[mine], over[mine], part.objectName())
            self.assertEqual(pressed[1 - mine], over[1 - mine], part.objectName())
        # nothing is drawn between the two: going across the join the colour only goes from one part's to the other's
        under(self.button.face, True)
        self.addCleanup(under, self.button.face, False)
        picture = self.button.grab().toImage()
        join = self.button.face.width()
        for row in (10, 25, 40):
            across = [picture.pixelColor(x, row).lightness() for x in range(join - 4, join + 4)]
            self.assertEqual(across, sorted(across), row)

    def test_a_command_that_is_off_does_not_light_under_the_pointer(self):
        _setup.meridiana_look()
        self.host.resize(300, 120)
        self.button.fit(Bar.UNDER, 50, 64)
        self.area.setEnabled(False)
        self.app.processEvents()
        self.nothing_under_the_pointer()
        rest = self.button.grab().toImage()
        self.button.setAttribute(Qt.WidgetAttribute.WA_UnderMouse, True)
        self.addCleanup(self.button.setAttribute, Qt.WidgetAttribute.WA_UnderMouse, False)
        over = self.button.grab().toImage()
        self.assertEqual(over.pixelColor(10, 3).name(), rest.pixelColor(10, 3).name())
        strip_x = self.button.face.width() + 2
        self.assertNotEqual(over.pixelColor(strip_x, 3).name(), rest.pixelColor(strip_x, 3).name())


class TheRulesOfTheFace(Family):
    def test_rule_1_a_mode_chosen_goes_on_the_face_a_command_run_once_does_not(self):
        self.row.trigger()
        self.assertEqual(self.button.command, "row")
        self.assertIs(self.button.defaultAction(), self.row)
        self.assertEqual(self.button.text(), "Row")
        self.once.trigger()
        self.assertEqual(self.button.command, "row")
        self.assertIs(self.button.defaultAction(), self.row)

    def test_rule_1_a_mode_that_is_on_is_on_the_face_and_stays_when_it_goes_off(self):
        self.row.trigger()
        self.assertTrue(self.button.isChecked())
        self.other.trigger()
        self.assertFalse(self.button.isChecked())
        self.assertEqual(self.button.command, "row")            # the last mode used: the next click runs it

    def test_rule_2_what_deletes_never_changes_the_face_and_the_last_is_apart_in_red(self):
        erase = self.action("Erase", checkable=True)
        erase_all = self.action("Erase inverter", checkable=True)
        clear = self.action("Clear all")
        b = self.make([("erase", "Erase", erase), ("erase_all", "Erase inv.", erase_all), ("clear", "Clear all", clear)],
                      fixed=True, danger={"clear": "strings_clear"})
        erase_all.trigger()
        self.assertEqual(b.command, "erase")
        self.assertIs(b.defaultAction(), erase)
        self.assertTrue(b.strip.isChecked())                    # what is on shows on the strip, and says its name
        b._say()
        self.assertIn("Erase inv.", b.strip.toolTip())
        clear.trigger()
        self.assertEqual(b.command, "erase")
        menu = b.commands.actions()
        self.assertTrue(menu[-2].isSeparator())
        self.assertIs(menu[-1], clear)
        self.assertEqual(sum(a.isSeparator() for a in menu), 1)
        # in red: the row of «Clear all» has the danger colour, the row above it has not
        b.commands.danger_colour = b.commands.danger_colour.__class__("#ff0000")
        b.commands.resize(b.commands.sizeHint())
        picture = b.commands.grab().toImage()
        red = {a.text(): 0 for a in (erase, clear)}
        for a in (erase, clear):
            r = b.commands.actionGeometry(a)
            for y in range(r.top(), r.bottom()):
                for x in range(r.left(), r.right()):
                    c = picture.pixelColor(x, y)
                    red[a.text()] += c.red() > 180 and c.green() < 90 and c.blue() < 90
        self.assertGreater(red["Clear all"], 20)
        self.assertEqual(red["Erase"], 0)

    def test_the_plants_bar_has_its_deleting_family_as_the_rule_says(self):
        tool = next(t for t in phases.by_id("plant").tools() if t.command == "tool_erase_string")
        self.assertTrue(tool.fixed)
        self.assertEqual([t.command for t in tool.family() if t.danger], ["strings_clear"])
        self.assertEqual(tool.family()[-1].command, "strings_clear")

    def test_rule_3_never_by_itself(self):
        self.row.trigger()
        self.row.setEnabled(False)                              # gone off: it goes off on the face
        self.app.processEvents()
        self.assertEqual(self.button.command, "row")
        self.assertIs(self.button.defaultAction(), self.row)
        self.assertFalse(self.button.face.isEnabled())
        self.row.setEnabled(True)
        self.assertTrue(self.button.face.isEnabled())

    def test_rule_4_a_key_changes_the_face_only_for_a_mode(self):
        """A key is the action's trigger: the same action as from the menu, nothing else to look at."""
        self.area.trigger()
        self.once.trigger()                                     # by its key: a command run once
        self.assertEqual(self.button.command, "area")
        self.row.trigger()                                      # by its key: a mode, on, and it must show
        self.assertEqual(self.button.command, "row")

    def test_rule_5_the_same_place_and_the_same_width_with_a_short_fade(self):
        x, width = self.button.face.x(), self.button.width()
        motion.set_reduced(False)
        self.row.trigger()
        self.assertEqual((self.button.face.x(), self.button.width()), (x, width))
        self.assertTrue(self.button.face.findChildren(motion.Veil))     # the fade, over the command alone
        motion.set_reduced(True)
        self.area.trigger()                                     # less motion: at once
        self.assertFalse([v for v in self.button.face.findChildren(motion.Veil) if not v.gone and v.isVisible()])

    def test_rule_6_every_start_has_the_first_one(self):
        self.row.trigger()
        again = self.make([("area", "Area", self.area), ("row", "Row", self.row), ("once", "Once", self.once)])
        self.assertEqual(again.command, "area")

    def test_rule_7_the_tooltip_says_the_command_of_now_its_key_and_the_others(self):
        self.assertEqual(self.button.toolTip(), "Area (S). 2 more in the arrow\nWhat it does")
        self.row.trigger()
        self.assertEqual(self.button.toolTip(), "Row (L). 2 more in the arrow\nWhat it does")
        self.assertIn("Area, Row, Once", self.button.strip.toolTip())


class TheSizes(unittest.TestCase):
    """The rule of the widths (design.Bar) on real bars, with every action of a phase present."""

    def setUp(self):
        self.app = _setup.qt_or_skip()
        _setup.meridiana_look()

    def bar(self, pid):
        actions = {t.command: QAction(t.label or t.command) for t in phases.by_id(pid).tools(every=True)}
        self.keep = actions
        stack = QStackedWidget()                # the sheet's rules of the bar are for the bars in the window's stack
        stack.setObjectName("phase-bars")
        self.addCleanup(stack.deleteLater)
        bar = PhaseBar(phases.by_id(pid), actions)
        stack.addWidget(bar)
        return bar

    def test_the_rule(self):
        self.assertEqual(Bar.width(Bar.ICONS, 500), Bar.ICON_WIDTH)
        self.assertEqual(Bar.width(Bar.UNDER, 10), Bar.WORD_MIN)
        self.assertEqual(Bar.width(Bar.UNDER, 64 - Bar.PAD), 64)
        self.assertEqual(Bar.width(Bar.UNDER, 65 - Bar.PAD), 80)
        self.assertEqual(Bar.width(Bar.BESIDE, 40) % Bar.STEP[Bar.BESIDE], 0)

    def test_every_button_of_a_mode_has_one_height_and_one_icon_and_a_width_of_the_rule(self):
        for pid in phases.ids():
            bar = self.bar(pid)
            for mode in (Bar.UNDER, Bar.BESIDE, Bar.ICONS):
                bar.set_mode(mode)
                sizes = {(b.height(), b.iconSize().width()) for b in bar.buttons().values()}
                self.assertEqual(len(sizes), 1, (pid, mode, sizes))
                self.assertEqual(sizes.pop()[1], Bar.ICON[mode])
                for b in bar.buttons().values():
                    command = b.face.width() if isinstance(b, ToolMenuButton) else b.width()
                    if mode == Bar.ICONS:
                        self.assertEqual(command, Bar.ICON_WIDTH)
                    else:
                        self.assertEqual(command % Bar.STEP[mode], 0, (pid, mode, b.text(), command))

    def test_a_word_never_needs_more_than_its_button_has(self):
        from PySide6.QtGui import QFontMetrics
        for pid in phases.ids():
            bar = self.bar(pid)
            for mode in (Bar.UNDER, Bar.BESIDE):
                bar.set_mode(mode)
                for b in bar.buttons().values():
                    width = b.face.width() if isinstance(b, ToolMenuButton) else b.width()
                    room = width - 2 * Space.XS - 2 - (Bar.ICON[mode] + Bar.WORD_GAP if mode == Bar.BESIDE else 0)
                    for word in b.words():
                        self.assertLessEqual(QFontMetrics(b.font()).horizontalAdvance(word), room, (pid, mode, word))

    def test_the_width_asked_is_the_width_it_takes(self):
        bar = self.bar("plant")
        stack = bar.parentWidget()
        for mode in (Bar.UNDER, Bar.BESIDE, Bar.ICONS):
            bar.set_mode(mode)
            stack.resize(bar.width_in(mode) + 40, bar.height())
            stack.show()
            self.app.processEvents()
            ends = [g.geometry().right() for g in bar.groups]
            self.assertTrue(all(g.isVisible() for g in bar.groups), mode)
            self.assertLessEqual(max(ends), bar.width_in(mode), mode)
            stack.hide()

    def test_the_lines_are_as_tall_as_the_buttons_and_the_air_is_the_same(self):
        bar = self.bar("plant")
        for mode in (Bar.UNDER, Bar.BESIDE, Bar.ICONS):
            bar.set_mode(mode)
            height = next(iter(bar.buttons().values())).height()
            self.assertEqual({line.height() for line in bar.lines}, {height}, mode)
            stack = bar.parentWidget()
            stack.resize(bar.width_in(mode) + 40, bar.height())
            stack.show()
            self.app.processEvents()
            gaps = {b.geometry().left() - a.geometry().right() - 1 for a, b in zip(bar.groups, bar.groups[1:], strict=False)}
            self.assertEqual(gaps, {Bar.LINE + 2 * Bar.GROUP_AIR}, mode)
            stack.hide()

    def test_the_titles_go_only_with_the_words_beside(self):
        bar = self.bar("model")
        bar.set_mode(Bar.BESIDE)
        self.assertTrue(bar.groups[0].title.isHidden())
        self.assertLessEqual(bar.height(), 31)
        bar.set_mode(Bar.ICONS)
        self.assertFalse(bar.groups[0].title.isHidden())

    def test_a_plain_button_is_not_divided(self):
        bar = self.bar("model")
        self.assertIsInstance(bar.buttons()["tool_select"], ToolButton)
        self.assertIsInstance(bar.buttons()["tool_building"], ToolMenuButton)


if __name__ == "__main__":
    unittest.main()
