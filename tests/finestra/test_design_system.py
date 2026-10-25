"""The design system and the pieces made with it on 24/10/2026 (docs/design/sistema-grafico.md): the closed scales and
the sheet that keeps to them, the line between two cards, the soft ends, the little windows, the fades; in the
window the File page, the menu bar that Alt shows, the variants' segmented control, the cards' buttons and the help
card that takes its room. Since 25/10/2026 (R100, R104, R121): the catalogue of the texts, closed in the window;
the scroll bars that keep their room; the accent only for what is in hand. PySide6 and a display (offscreen will
do)."""

import re
import unittest

import _setup
from _fixtures import capannone

from meridiana import config, theme_colors

setUpModule = _setup.keep_global_state


class Scales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_the_scales_are_closed_and_the_sheet_keeps_to_them(self):
        from meridiana.ui import design
        from meridiana.ui.design import Radius, Size, Space, Type
        from meridiana.ui.theme import style_sheet
        self.assertEqual(Space.SCALE, (0, 2, 4, 6, 8, 12, 16, 24, 32))
        for name in ("XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"):
            self.assertIn(getattr(Space, name), Space.SCALE)
        self.assertEqual(Radius.VIEW, Radius.CONTROL)                      # 6 px inside the card (R77)
        self.assertLess(Radius.INNER, Radius.CONTROL)
        self.assertLess(Radius.CONTROL, Radius.CARD)
        sizes = [Type.MICRO, Type.CAPTION, Type.SMALL, Type.BODY, Type.TITLE, Type.HEADING, Type.DISPLAY]
        self.assertEqual(sizes, sorted(sizes))
        self.assertEqual(design.padding(Space.XS, 8), "padding: 3px 7px;")  # 8 px from the outer edge
        pills = {Radius.pill(Size.CHIP), Radius.pill(Size.CHIP) + Space.XXS, Radius.pill(18)}
        allowed = {Radius.CARD, Radius.VIEW, Radius.CONTROL, Radius.INNER, Radius.MARK, 3} | pills
        for dark in (False, True):
            sheet = style_sheet(theme_colors.derive("#8b5a12", dark).tokens, dark)
            radii = {float(r) for r in re.findall(r"border-radius:\s*([0-9.]+)px", sheet)}
            self.assertLessEqual(radii, allowed, "a radius off the scale")

    def test_the_catalogue_of_the_texts_is_closed_and_each_style_has_its_place(self):
        """R121 (Daniel, 25/10/2026: «alcune differenze ci devono essere ma non devono essere troppe e devono avere
        un senso, e devono essere salvate come stile»): ten named styles on six sizes and two weights; the text at 13
        (R123), the tabs and the buttons too, the cards' titles at 14; capitals only for the labels; a bold asked for
        is the semibold."""
        from PySide6.QtGui import QFont, QFontInfo

        from meridiana.ui import theme
        from meridiana.ui.design import Text, Type, text_font
        theme.load_fonts()
        names = [s.name for s in Text.ALL]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(len(Text.ALL), 10)
        self.assertEqual({s.size for s in Text.ALL}, set(Type.SCALE))
        self.assertEqual(len(Type.SCALE), 6)
        self.assertEqual({s.weight for s in Text.ALL}, {Type.REGULAR, Type.SEMIBOLD})
        self.assertEqual([s.name for s in Text.ALL if s.caps], ["label"])
        self.assertEqual(Text.BODY.size, 13)                               # R123: «da 14 a 13»
        self.assertLessEqual(Text.CONTROL.size, Text.BODY.size)            # the tabs no larger than the text (R121)
        self.assertEqual((Text.BUTTON.size, Text.BUTTON.weight), (Text.CONTROL.size, Type.SEMIBOLD))
        self.assertGreater(Text.TITLE.size, Text.STRONG.size)              # the cards' titles above the groups'
        self.assertEqual(Type.BOLD, Type.SEMIBOLD)
        for style in Text.ALL:
            with self.subTest(style.name):
                f = text_font(style)
                info = QFontInfo(f)
                self.assertEqual((info.pixelSize(), f.weight(), f.capitalization() == QFont.Capitalization.AllUppercase),
                                 style.key)
                self.assertIn(style.tone, ("text", "text2", "muted"))

    def test_the_accent_of_the_sheet_only_for_what_is_in_hand_and_the_one_action(self):
        """R104 (Daniel, 25/10/2026: «lo vorrei un po' meno presente in tutto Meridiana il colore di accento»): in
        the sheet the accent fills the primary button and the File page open, and draws the focus; the selection,
        the chosen tabs and pills, the tools on and the key tile are neutral."""
        from meridiana.ui.theme import style_sheet
        for dark in (False, True):
            t = theme_colors.derive("#8b5a12", dark).tokens
            accent = t["accent"].lower()
            sheet = style_sheet(t, dark)
            for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", sheet):
                if accent not in body.lower():
                    continue
                for one in selector.split(","):
                    one = one.strip()
                    with self.subTest(dark=dark, selector=one):
                        self.assertTrue('primary="true"' in one or ":focus" in one or "file-chip:checked" in one, one)
            self.assertNotIn(theme_colors.qt_hex(t["accent_soft"]).lower(), sheet.lower())
            self.assertGreaterEqual(theme_colors.contrast(t["text"], t["select_bg"]), 7)
            self.assertLess(theme_colors.lch(t["select_bg"])[1], 0.02)    # a grey that leans to the hue

    def test_a_scroll_bar_that_comes_or_goes_moves_nothing(self):
        """R100 (Daniel, 25/10/2026: «le varie barre di scorrimento, quando compaiono, spostano tutti i contenuti in
        modo fastidioso»): the room of the bar is kept whether it scrolls or not, the bar thin, drawn only when
        there is something to scroll."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QLabel, QScrollArea, QTextBrowser, QTreeWidget, QTreeWidgetItem

        from meridiana.ui.design import Size
        from meridiana.ui.scrollbars import ScrollStyle
        _setup.meridiana_look()
        self.assertIsInstance(self.app._scroll_style, ScrollStyle)          # under the style sheet's
        area = QScrollArea()
        self.addCleanup(area.deleteLater)
        area.setWidgetResizable(True)
        text = QLabel("una riga")
        area.setWidget(text)
        area.resize(240, 160)
        area.show()
        self.app.processEvents()
        bar = area.verticalScrollBar()
        self.assertEqual(area.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.assertEqual(bar.width(), Size.SCROLLBAR)
        before = area.viewport().width()
        empty = bar.grab().toImage()
        colours = {empty.pixelColor(x, y).name() for x in range(empty.width()) for y in range(empty.height())}
        self.assertEqual(len(colours), 1, colours)                          # nothing drawn: nothing to scroll
        text.setText("\n".join(f"riga {i}" for i in range(60)))
        self.assertTrue(_setup.wait_until(self.app, lambda: bar.maximum() > 0, 2))
        self.assertEqual(area.viewport().width(), before)                   # the content did not move
        full = bar.grab().toImage()
        colours = {full.pixelColor(x, y).name() for x in range(full.width()) for y in range(full.height())}
        self.assertGreater(len(colours), 1)                                 # the thumb
        # a list and a text to read keep it too; a field one types into does not
        for view in (QTreeWidget(), QTextBrowser()):
            self.addCleanup(view.deleteLater)
            if isinstance(view, QTreeWidget):
                QTreeWidgetItem(view, ["uno"])
            view.show()
            self.app.processEvents()
            self.assertEqual(view.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn, type(view).__name__)

    def test_the_little_windows_and_the_fades_follow_less_motion(self):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication, QWidget

        from meridiana.ui import motion, popups
        popups.install(self.app)
        self.assertFalse(QApplication.isEffectEnabled(Qt.UIEffect.UI_FadeTooltip))     # Qt's stutter off
        self.assertFalse(QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateMenu))
        area = QWidget()
        self.addCleanup(area.deleteLater)
        area.resize(200, 100)
        area.show()
        changed = []
        motion.set_reduced(True)
        try:
            motion.crossfade(area, lambda: changed.append(1))
            self.assertEqual(changed, [1])
            self.assertEqual(area.findChildren(motion.Veil), [])            # nothing over it with less motion
        finally:
            motion.set_reduced(False)
        motion.crossfade(area, lambda: changed.append(2))
        self.assertEqual(changed, [1, 2])
        veil, = area.findChildren(motion.Veil)                              # the picture of before, held
        self.assertIsNone(veil.after)
        self.assertTrue(veil.testAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent))   # nothing under it repainted
        self.assertTrue(_setup.wait_until(self.app, lambda: veil.after is not None, 2))   # playing, next turn
        self.assertTrue(_setup.wait_until(self.app, lambda: not area.findChildren(motion.Veil), 3))
        # a change while a veil plays: one veil, the new one
        motion.crossfade(area, lambda: None)
        self.assertTrue(_setup.wait_until(self.app, lambda: area.findChildren(motion.Veil)[0].after is not None, 2))
        motion.slide(area, lambda: None, -1)
        self.app.processEvents()
        playing = lambda: [v for v in area.findChildren(motion.Veil) if not v.gone]    # noqa: E731
        self.assertEqual(len(playing()), 1)
        self.assertTrue(_setup.wait_until(self.app, lambda: playing() and playing()[0].shift < 0, 2))

    def test_a_list_that_goes_on_has_a_soft_end_only_where_there_is_more(self):
        from PySide6.QtWidgets import QLabel, QScrollArea

        from meridiana.ui import fades
        area = QScrollArea()
        self.addCleanup(area.deleteLater)
        area.setWidgetResizable(True)
        text = QLabel("\n".join(f"riga {i}" for i in range(80)))
        area.setWidget(text)
        area.resize(200, 150)
        area.show()
        f = fades.attach(area)
        self.assertIs(fades.attach(area), f)                                # once per area
        self.app.processEvents()
        top, bottom = f.edges
        self.assertFalse(top.isVisible())                                   # at the start nothing above
        self.assertTrue(bottom.isVisible())
        area.verticalScrollBar().setValue(area.verticalScrollBar().maximum())
        self.app.processEvents()
        self.assertTrue(top.isVisible())
        self.assertFalse(bottom.isVisible())


class InTheWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone(), cfg=config.Config(background="none", theme="light"), size=(1400, 900))

    def visible_fonts(self, root) -> list:
        """(what, size, weight, capitals) of every text shown under `root`, the marks' font left out."""
        from PySide6.QtGui import QFont, QFontInfo
        from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSpinBox, QComboBox, QGraphicsView,
                                       QGroupBox, QLabel, QLineEdit, QTabBar, QTextEdit, QTreeWidget)

        from meridiana.ui.theme import SYMBOL_FAMILY
        win = self.win
        out = []

        def key(f, what):
            info = QFontInfo(f)
            if SYMBOL_FAMILY and info.family() == SYMBOL_FAMILY:
                return
            out.append((what, info.pixelSize(), f.weight(), f.capitalization() == QFont.Capitalization.AllUppercase))

        for w in [root] + root.findChildren(QLabel) + root.findChildren(QAbstractButton) + \
                root.findChildren(QLineEdit) + root.findChildren(QAbstractSpinBox) + root.findChildren(QComboBox) + \
                root.findChildren(QTabBar) + root.findChildren(QGroupBox) + root.findChildren(QAbstractItemView) + \
                root.findChildren(QTextEdit):
            if not w.isVisible() or w.width() < 2:
                continue
            if any(w is v or v.isAncestorOf(w) for v in (win.plan, win.view3d)) or isinstance(w, QGraphicsView):
                continue                                                    # the drawings keep their own
            text = getattr(w, "text", None)
            if isinstance(w, QLabel) and not w.text():
                continue
            what = f"{type(w).__name__} {w.objectName()} {text() if callable(text) else ''}"[:70]
            key(w.font(), what)
            if isinstance(w, QTreeWidget):
                for i in range(min(10, w.topLevelItemCount())):
                    it = w.topLevelItem(i)
                    for c in range(w.columnCount()):
                        if it.text(c):
                            key(it.font(c), f"{what} item {it.text(c)}"[:70])
        return out

    def test_every_text_of_the_window_is_a_style_of_the_catalogue(self):
        """R121: «deve includere tutti i tasti e tutti i testi»; every phase, the File page, and what the window
        paints itself (the cards' titles, the phases' tabs, the sections, the marks' counts, the plan's labels)."""
        from PySide6.QtGui import QFontInfo, QPainter

        from meridiana.ui.design import Text
        from meridiana.ui.theme import SYMBOL_FAMILY
        allowed = Text.keys()
        win = self.win
        painted = []
        draw = QPainter.drawText

        def spy(painter, *args, **kwargs):
            import sys
            from pathlib import Path
            code = sys._getframe(1).f_code
            where = Path(code.co_filename)
            if where.parent.name == "ui" and where.stem not in ("plan", "marks", "view3d", "report", "report_3d"):
                f = painter.font()
                info = QFontInfo(f)
                if not (SYMBOL_FAMILY and info.family() == SYMBOL_FAMILY):
                    painted.append((f"{where.stem}.{code.co_name}", info.pixelSize(), f.weight(),
                                    f.capitalization() == f.Capitalization.AllUppercase))
            return draw(painter, *args, **kwargs)

        seen = []
        QPainter.drawText = spy
        try:
            for pid in ("model", "plant", "production", "consumption", "economics", "report"):
                win.show_phase(pid)
                self.app.processEvents()
                seen += [(pid, *k) for k in self.visible_fonts(win)]
                win.grab()
            win.open_file_page("export")
            self.app.processEvents()
            seen += [("file", *k) for k in self.visible_fonts(win.file_page)]
            win.grab()
            win.file_page.close_page()
        finally:
            QPainter.drawText = draw
        self.assertGreater(len(seen), 300)
        self.assertGreater(len(painted), 20)
        off = sorted({(where, what, size, weight, caps) for where, what, size, weight, caps in seen
                      if (size, weight, caps) not in allowed})
        self.assertEqual(off, [], "a text off the catalogue")
        off = sorted({p for p in painted if p[1:] not in allowed})
        self.assertEqual(off, [], "a text painted off the catalogue")
        # the lists, the menus and the tooltips in the text's font, not the platform's (Windows gave them Segoe UI
        # 9 pt, 12 px, after the style was set: the project's tree and the checks looked smaller than the help)
        from PySide6.QtWidgets import QApplication
        for name in ("QAbstractItemView", "QMenu", "QTipLabel", "QMessageBox"):
            f = QApplication.font(name)
            self.assertEqual((QFontInfo(f).pixelSize(), f.weight()), (Text.BODY.size, Text.BODY.weight), name)
        self.assertEqual(QFontInfo(win.tree.font()).family(), QFontInfo(win.help_box.view.text.font()).family())
        self.assertEqual(QFontInfo(win.tree.font()).pixelSize(), Text.BODY.size)
        for name, style in (("QPushButton", Text.BUTTON), ("QTabBar", Text.CONTROL), ("QToolButton", Text.CONTROL)):
            f = QApplication.font(name)
            self.assertEqual((QFontInfo(f).pixelSize(), f.weight()), (style.size, style.weight), name)

    def test_every_list_and_form_keeps_the_room_of_its_scroll_bar(self):
        """R100: the Properties, the project's tree, the checks, the help, the pages of the phases: the vertical bar
        always there, so its coming moves nothing; the plan pans and keeps none."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QAbstractScrollArea

        from meridiana.ui.scrollbars import keeps_room
        win = self.win
        for pid in ("model", "production"):
            win.show_phase(pid)
            self.app.processEvents()
            areas = [a for a in win.findChildren(QAbstractScrollArea) if a.isVisible()]
            self.assertGreater(len(areas), 4)
            for a in areas:
                with self.subTest(pid=pid, area=f"{type(a).__name__} {a.objectName()}"):
                    if a is win.plan:
                        self.assertEqual(a.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                    elif keeps_room(a) or a.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOn:
                        self.assertEqual(a.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        for a in (win.tree, win.checks_page.tree, win.props):
            self.assertEqual(a.verticalScrollBarPolicy(), Qt.ScrollBarPolicy.ScrollBarAlwaysOn, type(a).__name__)
        # the window narrower and wider: the Properties' content as wide as its viewport, which never jumps by a bar
        props = win.props
        widths = set()
        for w in (1400, 1250, 1400):
            win.resize(w, 900)
            self.assertTrue(_setup.wait_settled(self.app, lambda: props.viewport().width()))
            widths.add(props.viewport().width() - props.width())
        self.assertEqual(len(widths), 1, widths)                            # the bar's room the same at every width

    def stray_accents(self, allowed) -> list:
        from PySide6.QtGui import QColor

        win = self.win
        accent = QColor(win.theme.tokens["accent"])
        image = win.grab().toImage()
        ratio = image.devicePixelRatio()

        def is_accent(x, y):
            c = image.pixelColor(x, y)
            return abs(c.red() - accent.red()) + abs(c.green() - accent.green()) + abs(c.blue() - accent.blue()) < 24

        stray = []
        for y in range(0, win.height(), 3):
            for x in range(0, win.width(), 3):
                px, py = int((x + 0.5) * ratio), int((y + 0.5) * ratio)
                neighbours = ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1))
                if is_accent(px, py) and any(0 <= nx < image.width() and 0 <= ny < image.height()
                                             and is_accent(nx, ny) for nx, ny in neighbours):
                    if not any(r.contains(x, y) for r in allowed):
                        stray.append((x, y, win.childAt(x, y).__class__.__name__ if win.childAt(x, y) else ""))
        return stray

    def test_the_accent_shows_only_on_the_phase_in_hand_and_the_one_action(self):
        """R104: on the window at rest the accent is the disc of the phase in hand and the primary button; the
        drawings (plan and 3D) keep their colours. No chosen tool, tab or pill in the accent."""
        from PySide6.QtCore import QPoint, QRect
        from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QApplication, QComboBox, QLineEdit

        win = self.win
        win.show_phase("model")
        self.app.processEvents()
        win.setFocus()
        self.app.processEvents()
        allowed = [QRect(win.plan.mapTo(win, QPoint(0, 0)), win.plan.size()),
                   QRect(win.view3d_box.mapTo(win, QPoint(0, 0)), win.view3d_box.size())]
        bar = win.tabs.tabBar()
        tab = bar.tabRect(bar.currentIndex())
        allowed.append(QRect(bar.mapTo(win, tab.topLeft()), tab.size()))
        for b in win.findChildren(QAbstractButton):
            if b.isVisible() and (b.property("primary") or b.hasFocus()):
                allowed.append(QRect(b.mapTo(win, QPoint(0, 0)), b.size()).adjusted(-2, -2, 2, 2))
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QAbstractSpinBox, QComboBox)):
            allowed.append(QRect(focus.mapTo(win, QPoint(0, 0)), focus.size()).adjusted(-2, -2, 2, 2))
        stray = self.stray_accents(allowed)
        self.assertEqual(stray[:10], [], f"{len(stray)} points in the accent outside its places")

    def test_an_accent_label_is_still_found(self):
        from PySide6.QtWidgets import QLabel

        label = QLabel("Wrong accent", self.win)
        label.setStyleSheet(f"color: {self.win.theme.tokens['accent']};")
        label.setGeometry(600, 400, 200, 30)
        label.show()
        label.raise_()
        self.app.processEvents()
        stray = self.stray_accents([])
        self.assertTrue(any(label.geometry().contains(x, y) for x, y, _w in stray))

    def test_no_dashed_line_between_the_cards(self):
        """Daniel, 25/10/2026: «togli le linee tratteggiate che compaiono quando si vuole ridimensionare delle schede.
        Sono proprio brutte» (R113): the pointer's shape alone tells where the cards are resized, and the window no
        longer looks for its cards at every move of the mouse."""
        import importlib.util
        self.assertFalse(hasattr(self.win, "separator_hint"))
        self.assertIsNone(importlib.util.find_spec("meridiana.ui.separators"))

    def test_no_widget_hides_qt_s_own_window(self):
        """25/10/2026: the sun's bar kept its design day in `window`, and the menus that Alt shows, asking every widget
        for its `window()`, stopped with «'DesignWindow' object is not callable» at every key."""
        from PySide6.QtWidgets import QWidget
        for w in self.win.findChildren(QWidget):
            self.assertTrue(callable(w.window), type(w).__name__)

    def test_the_sun_bar_draws_its_knob_whole_and_its_month_in_the_theme(self):
        """Daniel, 25/10/2026: the hour's knob cut at the top, the calendar without the theme's corners, Qt's black
        arrows; the play button the theme's icon."""
        from PySide6.QtCore import QDate, QPoint, Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionSlider
        from meridiana.ui.day_picker import DayPicker
        bar = self.win.sunbar
        self.win.show_phase("model")
        self.app.processEvents()
        opt = QStyleOptionSlider()
        bar.hour.initStyleOption(opt)
        knob = bar.hour.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle,
                                              bar.hour)
        self.assertTrue(bar.hour.rect().contains(knob), (bar.hour.rect(), knob))
        self.assertIsInstance(bar.day.calendarWidget(), DayPicker)
        self.assertFalse(bar.play.icon().isNull())
        if not bar.day.isVisible():
            return
        d = bar.day
        d.setDate(QDate(2026, 12, 21))
        QTest.mouseClick(d, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(d.width() - 8, d.height() // 2))
        self.assertTrue(_setup.wait_until(self.app, lambda: QApplication.activePopupWidget() is not None, 2))
        pop = QApplication.activePopupWidget()
        self.addCleanup(pop.close)
        cal = d.calendarWidget()
        self.assertGreaterEqual(pop.height(), cal.minimumHeight())          # the last week whole
        img = pop.grab().toImage()
        accent = self.win.theme.tokens["accent"].lower()
        colours = {img.pixelColor(x, y).name() for x in range(0, img.width(), 3) for y in range(0, img.height(), 3)}
        self.assertNotIn(accent, colours)                                   # no accent (R103)

    def test_the_file_page_opens_over_the_panels_and_esc_brings_the_project_back(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win = self.win
        page = win.file_page
        self.assertFalse(page.isVisible())
        win.tabs.header.file_button.click()
        self.assertTrue(_setup.wait_until(self.app, page.isVisible, 3))
        self.assertTrue(win.tabs.header.file_button.isChecked())
        self.assertFalse(win.tabs.bars.isVisible())                         # the bar of the phase under it
        self.assertIsNone(win.tabs.header.tab_now())                        # no phase marked as open (R99)
        self.assertTrue(win.tabs.tab_bar.file_open)
        for key in ("open", "import", "export", "catalogues", "help"):
            page.show_section(key)
            self.assertIs(page.body.currentWidget(), page.sections[key])
            self.assertTrue(page.items[key].isChecked())
        page.show_section("open")                                           # the project just opened is there
        self.app.processEvents()
        QTest.keyClick(page, Qt.Key.Key_Escape)
        self.assertFalse(page.isVisible())
        self.assertTrue(win.tabs.bars.isVisible())
        self.assertFalse(win.tabs.header.file_button.isChecked())
        self.assertIsNotNone(win.tabs.header.tab_now())                     # the phase marked again
        self.assertEqual(win.cfg.recent[0], str(self.file))                 # the project opened, first

    def test_choosing_another_variant_keeps_the_pills_still(self):
        """R101: the same pills, another one checked, the same widths: nothing made again, nothing jumps."""
        from meridiana.ui.variant_bar import VariantBar
        from PySide6.QtGui import QAction
        bar = VariantBar(QAction("+"), [])
        self.addCleanup(bar.deleteLater)
        variants = [("v1", "Base"), ("v2", "Pensiline"), ("v3", "Est-ovest")]
        bar.set_variants(variants, "v1")
        bar.show()
        self.app.processEvents()
        pills = list(bar.pills)
        widths = [p.width() for p in pills]
        bar.set_variants(variants, "v2")
        self.app.processEvents()
        self.assertEqual(bar.pills, pills)                                  # the same objects
        self.assertEqual([p.isChecked() for p in pills], [False, True, False])
        self.assertEqual([p.width() for p in pills], widths)                # no heavier weight, no wider pill
        bar.set_variants(variants + [("v4", "Nuova")], "v4")               # another set: made again
        self.assertEqual(len(bar.pills), 4)

    def test_the_tab_of_the_phase_slides_to_the_new_one_and_meets_the_card_with_inverse_corners(self):
        """R83: the page and the tools change at once, the tab is held while the window works, then slides; R84:
        two inverse corners where the tab meets the card."""
        from PySide6.QtCore import QPointF

        from meridiana.ui import motion
        from meridiana.ui.cards import RADIUS
        win = self.win
        header = win.tabs.header
        self.app.processEvents()
        start = header.tab_now()
        win.show_phase("production")
        self.assertIs(win.tabs.currentWidget(), win.tabs.widget(win.tabs.index_of_phase("production")))
        self.assertEqual(header.tab_now(), start)                           # held where it was
        self.assertEqual(win.tabs.bars.findChildren(motion.Veil), [])      # the tools change at once
        self.assertTrue(_setup.wait_until(self.app, lambda: header.slide.state() == header.slide.State.Running, 2))
        self.assertTrue(_setup.wait_until(self.app, lambda: header.slide_from is None, 3))
        self.assertEqual(header.tab_now(), header.tab_target())
        self.assertGreater(header.tab_now().left(), start.left())
        # the inverse corners: the hollow's edge filled near the tab, its middle not
        header.repaint()
        path, tab = header.shape(), header.tab_now()
        top = header.card.geometry().top() + 0.5
        for x, outward in ((tab.left() + 0.5, -1), (tab.right() - 0.5, 1)):
            self.assertTrue(path.contains(QPointF(x + outward * 1.0, top - 1.0)))
            self.assertFalse(path.contains(QPointF(x + outward * (RADIUS - 1.5), top - RADIUS + 1.5)))
        # back: from the left; with less motion, at once
        win.show_phase("model")
        self.assertTrue(_setup.wait_until(self.app, lambda: header.slide.state() == header.slide.State.Running, 2))
        self.assertLess(header.tab_now().left(), header.slide_from.left() + 1)
        motion.set_reduced(True)
        try:
            win.show_phase("plant")
            self.app.processEvents()
            self.assertIsNone(header.slide_from)
            self.assertEqual(header.tab_now(), header.tab_target())
        finally:
            motion.set_reduced(False)

    def test_alt_shows_the_menu_bar_and_its_letters_open_their_menu(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        win = self.win
        bar = win.menuBar()
        self.assertFalse(bar.isVisible())                                   # hidden by default (R53)
        win.setFocus()
        self.app.processEvents()
        target = self.app.focusWidget() or win
        QTest.keyPress(target, Qt.Key.Key_Alt, Qt.KeyboardModifier.AltModifier)
        QTest.keyRelease(target, Qt.Key.Key_Alt, Qt.KeyboardModifier.NoModifier)
        self.assertTrue(bar.isVisible())
        self.assertIsNotNone(bar.activeAction())                            # the first menu open
        bar.activeAction().menu().close()
        self.assertTrue(_setup.wait_until(self.app, lambda: not bar.isVisible(), 2))
        # Alt and a menu's letter: that menu
        from meridiana.ui.menubar import mnemonic
        wanted = next(a for a in bar.actions() if a.menu() is not None and mnemonic(a.text()) not in ("", "f"))
        letter = mnemonic(wanted.text())
        QTest.keyClick(target, letter, Qt.KeyboardModifier.AltModifier)
        self.assertIs(bar.activeAction(), wanted)
        wanted.menu().close()
        # always shown: in its place above the phases
        win.menu_bar_action.trigger()
        self.assertTrue(win.cfg.menu_bar)
        self.assertTrue(bar.isVisible())
        self.assertIs(bar.parentWidget(), win.menuWidget())
        win.menu_bar_action.trigger()
        self.assertFalse(bar.isVisible())

    def test_the_variants_are_pills_one_click_away(self):
        win = self.win
        bar = win.variant_bar
        self.assertEqual([b.text() for b in bar.pills], ["Base"])
        base = win.project.variant
        win.edit("a second variant", lambda p: p.add_variant("Senza batteria"))
        self.app.processEvents()
        self.assertEqual([b.text() for b in bar.pills], ["Base", "Senza batteria"])
        self.assertEqual(bar.currentText(), "Senza batteria")
        bar.pills[0].click()                                                # back to the base
        self.assertEqual(win.project.variant, base)
        self.assertEqual(bar.currentText(), "Base")
        self.assertTrue(bar.pills[0].isChecked())

    def test_a_card_closed_or_covered_comes_back_from_its_button(self):
        win = self.win
        project = win.docks[0]
        button = win.panel_buttons.buttons[project]
        self.assertIn("Close", button.toolTip())
        project.close()
        self.app.processEvents()
        self.assertIn("Open", button.toolTip())
        button.click()
        self.assertTrue(project.isVisible())
        button.click()                                                      # on screen: the button closes it
        self.assertFalse(project.isVisible())
        button.click()

    def test_the_help_card_guides_the_gesture_in_hand_and_a_pin_keeps_its_subject(self):
        """R43 and R44: the steps of the tool in hand, the step at hand marked; a «?» pins its subject."""
        win, box = self.win, self.win.help_box
        win._set_tool("building")
        self.assertEqual(box.guide, ("building", 0))
        self.assertTrue(box.subject.text().startswith("Drawing a building · step 1 of 4"))
        win.plan.chain = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0)]               # three corners: closing is next
        win._guide()
        self.assertEqual(box.guide, ("building", 2))
        self.assertIn("first point", box.view.text.text())
        win.plan.chain = []
        win._set_tool("select")
        self.assertIsNone(box.guide)                                        # back to the context
        box.request("subfield")                                             # a «?»: pinned
        self.assertTrue(box.pinned and box.pin_button.isChecked())
        win._set_tool("exclusion")
        self.assertIsNone(box.guide)                                        # the pinned subject stays
        self.assertEqual(box.hid, "subfield")
        box.pin_button.click()
        self.assertFalse(box.pinned)
        box.detach()
        self.assertEqual(len(box.notes), 1)
        box.notes[0].close()
        win._set_tool("select")

    def test_the_help_card_gives_its_text_the_room_it_has(self):
        box = self.win.help_box
        self.assertTrue(box.view.fill)
        lines = box.view.fontMetrics().lineSpacing() * box.LINES + 4
        self.assertGreater(box.view.scroll.maximumHeight(), 0)
        box.show_help("subfield")
        self.app.processEvents()
        self.assertTrue(box.view.scroll.maximumHeight() >= min(lines, box.view.text.height()) or
                        box.view.scroll.maximumHeight() > lines)          # never held to three lines
