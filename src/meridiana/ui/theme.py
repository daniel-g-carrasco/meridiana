"""The look of the window (study 13, «Meridiana», with the colour chosen of section 12): the Fusion style on every
system, a full palette made from theme_colors.derive (every role, in the Active, Inactive and Disabled groups,
Accent included), a small global style sheet without fonts, and Inter loaded from its files (R95), in the styles of
the catalogue (design.Text, R121) for the kinds of widget that have one of their own (`class_fonts`). The scroll bars
are drawn by the application's style, ui/scrollbars.ScrollStyle (R100).

- «System», «Light» and «Dark» are Meridiana's palettes: with the portal's theme on Niri setColorScheme does
  nothing (study 13, 8), so the palette is chosen here and made again when colorSchemeChanged comes.
- The windows11 style is never used: with a palette of its own it left white text on light menus.
- The system's accent: on Windows the Highlight of the platform's palette, read before Meridiana sets its own;
  on Linux the portal (org.freedesktop.appearance, accent-color), read with gdbus because PySide's QtDBus
  cannot read the (ddd) it answers, and read again on SettingChanged. Without one, bronze.
- The plan, the 3D view and the charts take their colours from `tokens` when `changed` comes."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from .. import log, paths, theme_colors
from ..i18n import _

PORTAL = ("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop", "org.freedesktop.portal.Settings")
# Inter since 25/10/2026 (R95: Daniel chose it at 14 px on the real window at 200 %; Titillium Web, before it, read
# thin and small)
FONT_DIR = "inter"
FONT_FILES = ("Inter-Regular.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf")
FONT_WEIGHTS = dict(zip(FONT_FILES, (400, 600, 700), strict=True))
# The checks' marks (✔ ⚠ ✘ ℹ ⟳ ✕) and the snaps' signs (∥ ⊥ ⇧) are not all in Inter, nor all in Segoe UI.
# The first character Qt has to look for elsewhere costs it 1-2 s on Windows, whatever the font engine
# (23/10/2026): at the start, with the checks' panel, or later, freezing the page that first shows one. So these
# are drawn in a font that has them, where they appear; on Linux fontconfig finds them at once.
SYMBOL_FAMILY = "Segoe UI Symbol" if sys.platform == "win32" else ""


def mark(symbol: str) -> str:
    """A mark for rich text, in a font that has it."""
    return f"<span style=\"font-family: '{SYMBOL_FAMILY}'\">{symbol}</span>" if SYMBOL_FAMILY else symbol


_RAW: list = []         # the text's font as read from its file: which characters it draws


def in_font(ch: str) -> bool:
    """Whether the text's font draws `ch`; anything when its file is not there (there is no choice then)."""
    if not _RAW:
        from PySide6.QtGui import QRawFont
        f = paths.shipped("fonts", FONT_DIR, FONT_FILES[0])
        raw = QRawFont(str(f), 12) if f is not None and f.exists() else None
        _RAW.append(raw if raw is not None and raw.isValid() else None)
    return _RAW[0] is None or _RAW[0].supportsCharacter(ord(ch))


def marked(text: str) -> str:
    """Rich text (escaped already) with each character the text's font lacks in mark(): «γ Pmax», «412 Ω». Where
    the symbols need no font of their own (Linux), as it is."""
    if not SYMBOL_FAMILY:
        return text
    return "".join(mark(ch) if ord(ch) > 127 and not in_font(ch) else ch for ch in text)


def symbol_font(font: QFont) -> QFont:
    """`font` in the family that has the marks, for a text that is a mark."""
    out = QFont(font)
    if SYMBOL_FAMILY:
        out.setFamily(SYMBOL_FAMILY)
    return out


def theme_names() -> dict:
    return {"system": _("As the system"), "light": _("Light"), "dark": _("Dark")}


def colour_names() -> dict:
    """The ready-made colours of section 12.1, in the order of the menu."""
    return {"system": _("System"), "bronze": _("Bronze"), "terracotta": _("Terracotta"), "olive": _("Olive"),
            "forest": _("Forest"), "petrol": _("Petrol"), "blue": _("Blue"), "indigo": _("Indigo"),
            "plum": _("Plum"), "graphite": _("Graphite")}


def background_names() -> dict:
    return {"meridiana": _("Meridiana: lime and night"), "tinted": _("From the colour"), "grey": _("Grey")}


def qpalette(roles: dict) -> QPalette:
    pal = QPalette()
    for group, colours in roles.items():
        g = getattr(QPalette.ColorGroup, group)
        for role, hex_ in colours.items():
            pal.setColor(g, getattr(QPalette.ColorRole, role), QColor(hex_))
    return pal


def veil(t: dict, dark: bool, alpha: float) -> str:
    """The tonal veil of the controls (study 17, C2) at `alpha`, in Qt's order: the text over the light floors,
    black over the dark ones."""
    return theme_colors.qt_hex(("#000000" if dark else t["text"]) + f"{round(alpha * 255):02x}")


ARROWS = {"up": ("M2 9L8 3L14 9", 16, 12), "down": ("M2 3L8 9L14 3", 16, 12), "open": ("M2 4L8 10L14 4", 16, 14)}


def arrows(colour: str) -> dict:
    """The small arrows of the fields (C2: ▴▾ of a number, ⌄ of a list) in `colour`, as SVG files a style sheet
    can name: written once per colour in the temporary folder, drawn at twice their size for the screens at 200 %.
    name -> the file's path with forward slashes; {} when the folder cannot be written (the fields keep no arrow,
    as before)."""
    folder = Path(tempfile.gettempdir()) / "meridiana-style"
    out = {}
    try:
        folder.mkdir(exist_ok=True)
        for name, (d, w, h) in ARROWS.items():
            f = folder / f"{name}-{colour.lstrip('#')}.svg"
            if not f.exists():
                f.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                             f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="2" stroke-linecap="round" '
                             f'stroke-linejoin="round"/></svg>', encoding="utf-8")
            out[name] = f.as_posix()
    except OSError as e:
        log.complain("arrows", e)
        return {}
    return out


def style_sheet(t: dict, dark: bool = False) -> str:
    """The global rules, every measure from the design system (ui/design.py) and every colour a token
    (theme_colors). Three floors: the window's (the bars, the tabs, the status bar), the panels' (the cards drawn
    by ui/cards.py, the pages of the phases), the view's (the dialogs' lists). Every button and field 28 px high
    (Button.PUSH) with its text 8 px from its edge: buttons and fields tonal on the `field` veil, the fields' border
    at 3:1 under the pointer and the accent's when focused, one `primary` button full of accent per page; the chips,
    pills and tabs 24 px (Button.CHIP), the tabs of every bar as the segments of the variants (R109, R121); groups
    with a frame and a filled header (C3, ui/style.py); tiles and strips full of the veil without a border; the
    little windows (menus, lists, popups, tooltips) rounded by the system where it can (ui/popups.py). The texts'
    colours by their style's tone (`tone`, design.set_text).

    No font here: the fonts are the catalogue's (design.Text), set by code (`load_fonts`, `class_fonts`,
    design.set_text); but for the tab bar of a tab widget, which under a style sheet takes its tab widget's font
    whatever is set on it (QStyleSheetStyle::updateStyleSheetFont, the «natural children» named qt_...), unless a
    rule of the sheet gives it one. No scroll bar either: ui/scrollbars.ScrollStyle draws them, and a rule reaching a QScrollBar
    would make Qt draw it with its arrows (R100). The accent (R104) only for what is in hand or the one action of
    the page: the primary button, the focus, the File page open; the selection, the chosen tabs and pills, the key
    tile, the state «to make again» and the rows' «Correggi» are neutral."""
    from .design import Button, Layout, Line, Radius, Size, Space, Text, padding
    from .popups import native_corners
    hover, press = veil(t, dark, 0.35 if dark else 0.14), veil(t, dark, 0.5 if dark else 0.2)
    faded = theme_colors.faded_text(t)
    a = arrows(t["muted"])
    up = f"image: url({a['up']}); width: 8px; height: 6px;" if a else ""
    down = f"image: url({a['down']}); width: 8px; height: 6px;" if a else ""
    drop = f"image: url({a['open']}); width: 9px; height: 7px;" if a else ""
    S, R = Space, Radius
    # the little windows (R60): on Windows 11 the system rounds them and draws their border (ui/popups.py)
    edge = "border: none;" if native_corners() else f"border: 1px solid {t['line']}; border-radius: {R.CARD}px;"
    # a control: 28 px high whole (the border included), its text 8 px in; the height as the content's least
    # height, which the style sheet adds the padding and the border to
    control = padding(S.XS, Line.TEXT_INSET)                  # «padding: 3px 7px;»
    control_focus = padding(S.XS, Line.TEXT_INSET, Line.FOCUS)
    inner = Button.PUSH[0] - 2 * S.XS                          # 20: the line of text inside a control
    button = padding(S.XS, S.L)
    button_focus = padding(S.XS, S.L, Line.FOCUS)
    chip_inner = Button.CHIP[0] - 2                            # 22: a chip's inside, its border around
    pill = Radius.pill(Size.CHIP)
    small_inner = Button.SMALL[0] - 2
    return f"""
QMainWindow {{ background: {t['window']}; }}
QTabBar {{ background: transparent; }}
*[tone="text2"] {{ color: {t['text2']}; }}
*[tone="muted"] {{ color: {t['muted']}; }}
QMenuBar, QStatusBar {{ background: transparent; }}
QMenuBar[revealed="true"] {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: {R.CARD}px;
                             padding: {S.XXS}px; }}
QMenuBar::item {{ padding: {S.XS}px {S.M}px; border-radius: {R.INNER}px; background: transparent; }}
QMenuBar::item:selected, QMenuBar::item:pressed {{ background: {hover}; }}
QMenu {{ background: {t['card']}; {edge} padding: {S.XS}px; }}
QMenu::item {{ padding: {S.S}px {S.XXL}px {S.S}px {S.M}px; border-radius: {R.INNER}px; }}
QMenu::item:selected {{ background: {t['select_bg']}; color: {t['select_fg']}; }}
QMenu::separator {{ height: 1px; background: {t['line']}; margin: {S.XS}px {S.M}px; }}
QComboBox QAbstractItemView {{ background: {t['card']}; color: {t['text']}; {edge} padding: {S.XS}px; outline: 0;
                              selection-background-color: {t['select_bg']}; selection-color: {t['select_fg']}; }}
QComboBox QAbstractItemView::item {{ padding: {S.S}px {S.M}px; border: none; border-radius: {R.INNER}px; }}
QFrame#help-popup {{ background: {t['card']}; {edge} }}
QFrame#help-note {{ background: {t['panel']}; }}
QFrame#gizmoField {{ background: {t['card']}; border: 1px solid {t['line']}; border-radius: {R.CARD}px; }}
QToolTip {{ background: {t['tooltip_bg']}; color: {t['tooltip_fg']}; border: none; padding: {S.XS}px {S.M}px; }}
QToolBar {{ background: {t['window']}; border: none; spacing: {S.XXS}px; padding: {S.XXS}px; }}
QStatusBar {{ border: none; }}
QStatusBar QLabel {{ color: {t['text2']}; }}
QMainWindow::separator {{ width: {S.M}px; height: {S.M}px; background: transparent; }}
QDockWidget {{ background: {t['window']}; border: none; }}
QDockWidget::title {{ background: {t['header']}; color: {t['muted']}; padding: {S.S}px {S.M}px; text-align: left; }}
QTreeView, QListView {{ background: {t['card']}; border: 1px solid {t['card_line']}; border-radius: {R.CONTROL}px;
                        outline: 0; }}
QDockWidget QTreeView, QDockWidget QListView {{ background: transparent; border: none; }}
QTreeView::item {{ padding: {S.XXS}px 0; }}
QTreeView#checks-tree {{ outline: 0; show-decoration-selected: 0; }}
QLabel#report-page {{ border: 1px solid {t['line']}; background: #ffffff; }}
QTreeView#checks-tree::item {{ padding: {S.XS}px {S.XXS}px; border: none; }}
QTreeView#checks-tree::item:selected, QTreeView#checks-tree::item:hover {{ background: transparent;
    color: {t['text']}; }}
QToolButton#rowfix {{ background: {t['field']}; color: {t['text']}; border: none; border-radius: {Button.SMALL[1]}px;
                      padding: 0 {S.M}px; min-height: {Button.SMALL[0]}px; max-height: {Button.SMALL[0]}px; }}
QToolButton#rowfix:hover {{ background: {hover}; }}
QToolButton#roweye {{ border: 1px solid {t['line']}; border-radius: {Button.SMALL[1]}px; padding: 0 {S.XS}px;
                      min-height: {small_inner}px; max-height: {small_inner}px; }}
QTreeView#project-tree {{ outline: 0; }}
QTreeView#project-tree::item {{ padding: {S.XS}px {S.XS}px; border: none; }}
QTreeView#project-tree::item:selected, QTreeView#project-tree::item:hover {{ background: transparent;
    color: {t['select_fg']}; }}
QTreeView#project-tree::item:hover:!selected {{ color: {t['text']}; }}
QHeaderView::section {{ background: transparent; color: {t['muted']}; border: none;
                       border-bottom: 1px solid {t['line']}; padding: {S.XS}px {S.M}px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget#qt_scrollarea_viewport {{ background: transparent; }}
QScrollArea > QWidget#qt_scrollarea_viewport > QWidget {{ background: transparent; }}
QTabWidget::pane {{ border: none; }}
QStackedWidget#phase-pages > QWidget {{ background: {t['panel']}; border: 1px solid {t['card_line']};
                                         border-radius: {R.CARD}px; }}
QStackedWidget#phase-pages > QSplitter {{ padding: {Layout.PAD}px; }}
QStackedWidget#phase-pages > QSplitter::handle {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: {S.M}px; }}
QSplitter::handle:vertical {{ height: {S.M}px; }}
QTabWidget > QTabBar {{ font-size: {Text.CONTROL.size}px; font-weight: {Text.CONTROL.weight}; }}
QTabBar::tab {{ border: 1px solid transparent; border-radius: {pill:g}px; padding: 0 {S.L - 1}px;
               min-height: {chip_inner}px; max-height: {chip_inner}px;   /* 24 px whole: Qt drops a radius over half the height */
               margin: {S.XS}px {S.XXS}px {S.XS}px 0; color: {t['text2']}; background: {t['field']}; }}
QTabBar::tab:hover:!selected {{ background: {hover}; color: {t['text']}; }}
QTabBar::tab:selected {{ background: {t['panel']}; color: {t['text']}; border-color: {t['line']}; }}
QTabBar#phases {{ background: transparent; }}
QStackedWidget#phase-bars, QWidget#phase-card {{ background: transparent; }}
QStackedWidget#phase-bars QToolBar {{ padding: 0; spacing: {S.S}px; border: none; background: transparent; }}
QStackedWidget#phase-bars QToolButton {{ padding: 1px {S.XS}px; }}
QStackedWidget#phase-bars QToolButton[primary="true"] {{ background: {t['accent']}; color: {t['accent_fg']}; }}
QStackedWidget#phase-bars QToolButton[primary="true"]:hover {{ background: {t['accent_hover']}; }}
QStackedWidget#phase-bars QToolButton[primary="true"]:disabled {{ background: {t['field']}; color: {faded}; }}
QStackedWidget#phase-bars QLabel#group-title {{ color: {t['muted']}; }}
QStackedWidget#phase-bars QFrame#bar-line {{ background: {t['line_soft']}; margin: {S.XS}px {S.M}px; }}
QPushButton {{ background: {t['field']}; border: 1px solid transparent; border-radius: {Button.PUSH[1]}px; {button}
              min-height: {inner}px; color: {t['text']}; }}
QPushButton:hover {{ background: {hover}; }}
QPushButton:pressed {{ background: {press}; }}
QPushButton:focus {{ border: {Line.FOCUS}px solid {t['accent']}; {button_focus} }}
QPushButton:disabled {{ background: transparent; border-color: transparent; color: {faded}; }}
QPushButton[primary="true"] {{ background: {t['accent']}; color: {t['accent_fg']}; border-color: {t['accent']}; }}
QPushButton[primary="true"]:hover, QPushButton[primary="true"]:pressed {{ background: {t['accent_hover']};
                                                                        border-color: {t['accent_hover']}; }}
QPushButton[primary="true"]:focus {{ border: {Line.FOCUS}px solid {t['text']}; }}
QPushButton[primary="true"]:disabled {{ background: {t['field']}; color: {faded}; border-color: transparent; }}
QPushButton[destructive="true"] {{ color: {t['danger']}; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: {Button.TOOL[1]}px;
              padding: {S.XS - 1}px; }}
QToolButton:hover {{ background: {hover}; }}
QToolButton:pressed {{ background: {press}; }}
QToolButton:checked {{ background: {t['select_bg']}; color: {t['select_fg']}; border-color: {t['line']}; }}
QToolButton:focus {{ border-color: {t['accent']}; }}
QToolButton[popupMode="2"] {{ padding-right: {S.XL}px; }}
QToolButton::menu-indicator {{ {drop} subcontrol-origin: padding; subcontrol-position: center right; right: {S.XS}px; }}
QToolButton#filter, QToolButton#count {{ border: 1px solid {t['line']}; border-radius: {pill:g}px;
    padding: 0 {S.L - 1}px; min-height: {chip_inner}px; max-height: {chip_inner}px; color: {t['text']};
    background: transparent; }}
QToolButton#count {{ padding-left: {S.M - 1}px; }}
QToolButton#filter:hover, QToolButton#count:hover {{ background: {hover}; }}
QToolButton#filter:pressed, QToolButton#count:pressed {{ background: {press}; }}
QToolButton#filter:checked {{ background: {t['select_bg']}; color: {t['select_fg']}; }}
QToolButton#filter[popupMode="2"] {{ padding-right: {S.XXL}px; }}
QToolButton#count:disabled {{ color: {t['muted']}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit, QDateEdit, QTimeEdit {{
    background: {t['field']}; border: 1px solid transparent; border-radius: {R.CONTROL}px; {control}
    color: {t['text']}; selection-background-color: {t['select_bg']}; selection-color: {t['select_fg']}; }}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit {{ min-height: {inner}px;
    max-height: {inner}px; }}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QTextEdit:hover, QPlainTextEdit:hover,
QDateEdit:hover, QTimeEdit:hover {{ border: 1px solid {t['field_line']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus,
QDateEdit:focus, QTimeEdit:focus {{ border: {Line.FOCUS}px solid {t['accent']}; {control_focus} }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled, QTextEdit:disabled,
QPlainTextEdit:disabled, QDateEdit:disabled, QTimeEdit:disabled {{ border-color: transparent; color: {faded}; }}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    border: none; background: transparent; width: {S.XL}px; subcontrol-origin: border; }}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; margin: {S.XS}px 3px 0 0; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; margin: 0 3px {S.XS}px 0; }}
QAbstractSpinBox::up-arrow {{ {up} }}
QAbstractSpinBox#grid-field::up-button, QAbstractSpinBox#grid-field::down-button {{ width: 0px; margin: 0; }}
QAbstractSpinBox#grid-field::up-arrow, QAbstractSpinBox#grid-field::down-arrow {{ image: none; width: 0px;
                                                                                 height: 0px; }}
QAbstractSpinBox::down-arrow {{ {down} }}
QComboBox::drop-down {{ border: none; width: {Size.COMPACT}px; subcontrol-origin: padding;
                       subcontrol-position: center right; }}
QComboBox::down-arrow {{ {drop} }}
QDateEdit::drop-down {{ border: none; width: {Size.COMPACT}px; subcontrol-origin: padding;
                       subcontrol-position: center right; }}
QDateEdit::down-arrow {{ {drop} }}
QCalendarWidget {{ background: {t['card']}; {edge} }}
QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: transparent; padding: {S.XS}px {S.XS}px 0 {S.XS}px; }}
QCalendarWidget QToolButton {{ color: {t['text']}; background: transparent; border: none; border-radius: {R.INNER}px;
                               padding: {S.XXS}px {S.S}px; }}
QCalendarWidget QToolButton:hover {{ background: {hover}; }}
QCalendarWidget QToolButton::menu-indicator {{ image: none; width: 0; }}
QCalendarWidget QAbstractItemView {{ background: {t['card']}; color: {t['text']}; outline: 0; border: none;
                                     border-radius: {R.INNER}px;      /* the little window's 8 less the 4 around */
                                     margin: 0 {S.XS}px {S.XS}px {S.XS}px;
                                     selection-background-color: transparent; selection-color: {t['text']}; }}
QSlider:horizontal {{ min-height: {Size.COMPACT}px; }}
QSlider::groove:horizontal {{ height: 4px; background: {t['line']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ height: 4px; background: {t['muted']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: {t['card']}; border: 1px solid {t['field_line']}; width: 14px; height: 14px;
                              margin: -6px 0; border-radius: 8px; }}
QSlider::handle:horizontal:hover {{ border-color: {t['text2']}; }}
QFrame#tile, QFrame#strip, QFrame#ftile {{ background: {t['field']}; border: none; border-radius: {R.CARD}px; }}
QFrame#tile QPushButton, QFrame#strip QPushButton, QFrame#ftile QPushButton {{ background: {t['panel']}; }}
QFrame#tile QPushButton:hover, QFrame#strip QPushButton:hover, QFrame#ftile QPushButton:hover {{ background: {hover}; }}
QFrame#tile QPushButton[primary="true"] {{ background: {t['accent']}; color: {t['accent_fg']}; }}
QFrame#tile QPushButton[primary="true"]:hover {{ background: {t['accent_hover']}; }}
QTableView, QTableWidget {{ background: {t['card']}; border: 1px solid {t['card_line']}; border-radius: {R.CONTROL}px;
                           gridline-color: {t['line_soft']}; selection-background-color: {t['select_bg']};
                           selection-color: {t['select_fg']}; }}
QTableView QHeaderView::section {{ background: {t['field']}; color: {t['text2']}; border: none;
                                  border-bottom: 1px solid {t['line_soft']}; padding: {S.XS}px {S.M}px; }}
QTableView QTableCornerButton::section {{ background: {t['field']}; border: none; }}
QLabel#state-done, QLabel#state-stale, QLabel#state-todo, QLabel#state-unavailable, QLabel#state-planned {{
    border: 1px solid transparent; border-radius: {pill:g}px; padding: 0 {S.M}px; min-height: {chip_inner}px;
    max-height: {chip_inner}px; }}
QLabel#state-done {{ background: {t['select_bg']}; color: {t['select_fg']}; }}
QLabel#state-stale {{ background: transparent; color: {t['text']}; border-color: {t['field_line']}; }}
QLabel#state-todo {{ background: {t['line_soft']}; color: {t['text2']}; }}
QLabel#state-unavailable, QLabel#state-planned {{ background: {t['line_soft']}; color: {t['muted']}; }}
QFrame#chart-card {{ background: transparent; border: 1px solid {t['line_soft']}; border-radius: {R.CARD}px; }}
QFrame#chart-card QTabWidget::pane {{ border: none; border-top: 1px solid {t['line_soft']}; top: 0px; }}
QToolButton#file-chip {{ background: {t['field']}; color: {t['text']}; border: 1px solid transparent;
                        border-radius: {Button.PUSH[1]}px; padding: {S.XXS}px {S.L - 2}px {S.XXS}px {S.M}px; }}
QToolButton#file-chip:hover {{ background: {hover}; }}
QToolButton#file-chip:checked {{ background: {t['accent']}; color: {t['accent_fg']}; border-color: {t['accent']}; }}
QFrame#variant-bar {{ background: {t['field']}; border: none; border-radius: {pill + S.XXS:g}px; }}
QToolButton#variant-pill, QToolButton#variant-add, QToolButton#variant-more {{ border: 1px solid transparent;
    border-radius: {pill:g}px; padding: 0 {S.L - 1}px; min-height: {chip_inner}px; max-height: {chip_inner}px;
    color: {t['text2']}; background: transparent; }}
QToolButton#variant-add, QToolButton#variant-more {{ padding: 0 {S.S - 1}px; }}
QToolButton#variant-pill:hover, QToolButton#variant-add:hover, QToolButton#variant-more:hover {{
    background: {hover}; color: {t['text']}; }}
QToolButton#variant-pill:checked {{ background: {t['panel']}; color: {t['text']}; border-color: {t['line']}; }}
QToolButton#variant-more::menu-indicator {{ image: none; width: 0; }}
QFrame#row-line {{ background: {t['line_soft']}; border: none; }}
QLabel#row-detail, QLabel#grid-row {{ color: {t['text2']}; }}
QLabel#row-empty, QLabel#grid-head {{ color: {t['muted']}; }}
QLabel#row-problem {{ color: {t['danger']}; }}
QLabel#problem {{ color: {t['danger']}; }}
QFrame#card {{ background: {t['panel']}; border: 1px solid {t['card_line']}; border-radius: {R.CARD}px; }}
QFrame#file-page {{ background: {t['panel']}; border: 1px solid {t['card_line']}; border-radius: {R.CARD}px; }}
QFrame#file-nav {{ background: transparent; border: none; border-right: 1px solid {t['line_soft']}; }}
QFrame#file-rule {{ background: {t['line_soft']}; margin: 0 {S.M}px; }}
QToolButton#file-item {{ text-align: left; padding: 0 {S.M}px; border-radius: {Button.NAV[1]}px; color: {t['text']}; }}
QToolButton#file-item:checked {{ background: {t['select_bg']}; color: {t['select_fg']}; border-color: transparent; }}
QLabel#file-keys {{ color: {t['muted']}; background: transparent; }}
QToolButton#recent-item {{ border-radius: {Button.NAV[1]}px; }}
QLabel#recent-folder {{ color: {t['muted']}; background: transparent; }}
QLabel#recent-name {{ background: transparent; }}
QLabel#fpage-title {{ color: {t['text']}; }}
QLabel#fpage-lead, QLabel#ftile-text {{ color: {t['text2']}; }}
QLabel#fpage-section {{ color: {t['muted']}; }}
QLabel#ftile-format {{ color: {t['text2']}; border: 1px solid {t['line']}; border-radius: {Radius.pill(18):g}px;
                       padding: 0 {S.S}px; }}
QToolButton#help-button {{ padding: 0; border: 1px solid {t['line']}; border-radius: {Button.HELP[1]}px;
                           color: {t['muted']}; background: transparent; }}
QToolButton#help-button:hover {{ color: {t['text']}; border-color: {t['text']}; }}
QToolButton#help-pin, QToolButton#help-detach {{ border-radius: {Button.SMALL[1]}px; padding: 0; }}
QToolButton#help-pin:checked {{ background: {t['select_bg']}; border-color: transparent; }}
"""


class SystemAccent(QObject):
    """What the system says for the look, one reader for the application (a child of it): the accent and whether
    it asks for less motion. On Windows the Highlight of the platform's palette, read before Meridiana sets its own
    (#0078d4 on Daniel's PC), and SPI_GETCLIENTAREAANIMATION; on Linux the portal's accent-color and
    reduced-motion, read with gdbus (PySide's QtDBus cannot read the (ddd) the portal answers) without waiting,
    and again on SettingChanged."""

    changed = Signal(str)
    motion = Signal(bool)            # True: less motion, please

    def __init__(self, app):
        super().__init__(app)
        self.value = ""
        self.reduced_motion = False
        self._processes: dict = {}
        if sys.platform == "win32":
            self.value = QGuiApplication.palette().color(QPalette.ColorRole.Highlight).name()
            self.reduced_motion = _windows_reduced_motion()
        elif sys.platform.startswith("linux"):
            self._listen()
            self.read()
            self.read("reduced-motion")

    @classmethod
    def of(cls, app) -> "SystemAccent":
        found = app.findChild(cls)
        return found if found is not None else cls(app)

    def _listen(self) -> None:
        try:
            from PySide6.QtCore import SLOT
            from PySide6.QtDBus import QDBusConnection
        except ImportError:
            return
        bus = QDBusConnection.sessionBus()
        if bus.isConnected():
            bus.connect("", PORTAL[1], PORTAL[2], "SettingChanged", self, SLOT("_setting_changed(QDBusMessage)"))

    @Slot("QDBusMessage")
    def _setting_changed(self, message) -> None:
        args = message.arguments()
        if len(args) >= 2 and args[0] == "org.freedesktop.appearance" and args[1] in ("accent-color", "reduced-motion"):
            self.read(args[1])

    def read(self, key: str = "accent-color") -> None:
        if key in self._processes:
            return
        process = QProcess(self)
        process.finished.connect(lambda _code, _status: self._answered(key, process))
        process.errorOccurred.connect(lambda _e: self._answered(key, process))
        self._processes[key] = process
        process.start("gdbus", ["call", "--session", "--dest", PORTAL[0], "--object-path", PORTAL[1], "--method",
                                PORTAL[2] + ".ReadOne", "org.freedesktop.appearance", key])

    def _answered(self, key: str, process: QProcess) -> None:
        if self._processes.get(key) is not process:
            return                                  # an answer already taken (an error, then the end)
        del self._processes[key]
        text = bytes(process.readAllStandardOutput()).decode("utf-8", "replace")
        process.deleteLater()
        if key == "reduced-motion":
            reduced = theme_colors.gdbus_number(text) == 1
            if reduced != self.reduced_motion:
                self.reduced_motion = reduced
                self.motion.emit(reduced)
            return
        accent = theme_colors.gdbus_accent(text)
        if accent != self.value:
            self.value = accent
            self.changed.emit(accent)


def _windows_reduced_motion() -> bool:
    """Windows' «Animation effects» switched off (SPI_GETCLIENTAREAANIMATION): less motion."""
    try:
        import ctypes
        on = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0):
            return not on.value
    except (AttributeError, OSError):
        pass
    return False


class Theme(QObject):
    """One per window. `apply` sets the palette and the style sheet of the application; `preview` only computes
    (the preferences' sample changes at once, the window when the choice settles)."""

    changed = Signal()

    def __init__(self, cfg, parent=None, app: QApplication | None = None):
        super().__init__(parent)
        self.app = app or QApplication.instance()
        self.cfg = cfg
        self.tokens: dict = {}
        self.report = None
        self.dark = False
        self.applied: tuple | None = None
        system = SystemAccent.of(self.app)
        self.system_accent = system.value
        system.changed.connect(self._system_accent)
        if "Fusion" in QStyleFactory.keys():
            from . import scrollbars
            # once (setting a style polishes every widget again): Fusion, with Meridiana's scroll bars (R100)
            self.scroll_style = scrollbars.install(self.app)
        # after the style: setting one gives the lists, the menus, the tooltips and the status bar the platform's
        # font again (Segoe UI 9 pt on Windows: the project's tree and the checks were 12 px, R121)
        self.family = load_fonts()
        class_fonts(self.app)
        from .style import shared
        self.style = shared()                       # the groups' and the menus' style (ui/style.py)
        from . import popups
        popups.install(self.app)                    # the little windows: one way of coming, rounded (R60)
        popups.set_motion(not system.reduced_motion)
        system.motion.connect(lambda reduced: popups.set_motion(not reduced))
        from . import motion
        motion.set_reduced(system.reduced_motion)     # the pages' fades and the sections' slides (R75)
        system.motion.connect(motion.set_reduced)
        self.app.styleHints().colorSchemeChanged.connect(self._scheme_changed)
        # now, before the window builds its widgets: set after them, the palette and the style sheet polish
        # every widget once more (about 1,000 at start)
        self.apply()

    def _system_accent(self, accent: str) -> None:
        self.system_accent = accent
        if self.cfg.accent == "system" and self.applied is not None:
            self.apply()

    # the choice

    def is_dark(self, theme: str | None = None) -> bool:
        theme = theme or self.cfg.theme
        if theme in ("light", "dark"):
            return theme == "dark"
        return self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark

    def preview(self, theme: str | None = None, accent: str | None = None,
                backgrounds: str | None = None) -> theme_colors.Derived:
        dark = self.is_dark(theme)
        seed = theme_colors.seed_for(accent if accent is not None else self.cfg.accent, self.system_accent)
        b = backgrounds if backgrounds in theme_colors.BACKGROUNDS else (
            self.cfg.backgrounds if self.cfg.backgrounds in theme_colors.BACKGROUNDS else "meridiana")
        return theme_colors.derive(seed, dark, b)

    def apply(self) -> None:
        """The palette and the style sheet of the settings, on the whole application; `changed` for the rest."""
        derived = self.preview()
        dark = self.is_dark()
        key = (dark, derived.tokens["accent"], self.cfg.backgrounds, self.cfg.theme)
        self.tokens, self.report, self.dark = derived.tokens, derived.report, dark
        self.style.tokens = self.tokens
        if getattr(self, "scroll_style", None) is not None:
            self.scroll_style.tokens = self.tokens
        from . import popups
        popups.set_colours(self.tokens)
        if key == self.applied:
            return
        self.applied = key
        scheme = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(self.cfg.theme,
                                                                                 Qt.ColorScheme.Unknown)
        if sys.platform == "win32" and getattr(self.app, "_meridiana_scheme", None) != scheme:
            # only when the request changes: colorScheme() never answers Unknown, so asking at every apply set
            # it again each time, and colorSchemeChanged made every theme apply once more
            self.app._meridiana_scheme = scheme
            self.app.styleHints().setColorScheme(scheme)          # the title bar of Windows follows
        # set only what differs: a style sheet set again polishes every widget of the application (0.4-0.9 s,
        # study 13, 8), and a second window with the same settings would pay it for nothing
        pal = qpalette(theme_colors.palette(self.tokens, dark))
        if pal != self.app.palette():
            self.app.setPalette(pal)
        sheet = style_sheet(self.tokens, dark)
        if sheet != self.app.styleSheet():
            self.app.setStyleSheet(sheet)
        # again: the first style sheet sets a style (QStyleSheetStyle), and with it the platform's fonts
        class_fonts(self.app)
        self.changed.emit()

    def _scheme_changed(self, _scheme) -> None:
        if self.cfg.theme == "system":
            # a moment later: on Windows the signal comes while the palette is still the old one (study 13, 8)
            QTimer.singleShot(0, self.apply)


_FAMILY: list = []          # the family loaded, once per process


BODY_PX = 13                # the text's size at least, in logical pixels (Daniel, 25/10/2026: Inter, then 13 px, R123)


def class_fonts(app=None) -> None:
    """The kinds of widget whose text has a style of its own in the catalogue (design.Text): the push buttons, the
    tabs, the tool buttons (chips, pills, tools), the headers of the tables and the status bar; and the kinds the
    platform gives a font of its own (Windows: Segoe UI 9 pt for the lists, the menus, the tooltips, the message
    boxes), in the text's. Again after any setStyle, which takes the platform's fonts back."""
    from .design import Text, text_font
    app = app or QApplication.instance()
    if app is None:
        return
    base = app.font()
    styles = {"QPushButton": Text.STRONG, "QTabBar": Text.CONTROL, "QToolButton": Text.CONTROL,
              "QHeaderView": Text.SECONDARY, "QStatusBar": Text.SECONDARY,
              "QAbstractItemView": Text.BODY, "QListView": Text.BODY, "QMenu": Text.BODY, "QMenuBar": Text.BODY,
              "QTipLabel": Text.BODY, "QMessageBox": Text.BODY, "QMessageBoxLabel": Text.BODY,
              "QComboMenuItem": Text.BODY, "QComboLineEdit": Text.BODY, "QDockWidgetTitle": Text.TITLE,
              "QMdiSubWindowTitleBar": Text.TITLE, "QSmallFont": Text.SECONDARY, "QMiniFont": Text.CAPTION}
    for name, style in styles.items():
        f = text_font(style, base)
        if QApplication.font(name) != f:
            app.setFont(f, name)


def load_fonts() -> str:
    """Inter from its files (data/fonts), as the application's font at the system's size; the charts
    get it too. Once per process. The family as Qt names it, "" when the files are not there."""
    if _FAMILY:
        return _FAMILY[0]
    folder = paths.shipped("fonts", FONT_DIR)
    family = ""
    for name in FONT_FILES if folder is not None else ():
        f = folder / name
        fid = QFontDatabase.addApplicationFont(str(f)) if f.exists() else -1
        families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
        if not families:
            log.complain("fonts", OSError(f"{f} could not be loaded"))
            continue
        family = family or families[0]
        _CHART_FONTS.append((f, families[0], FONT_WEIGHTS[name]))
    _FAMILY.append(family)
    app = QApplication.instance()
    if family and app is not None and app.font().family() != family:
        font = QFont(app.font())
        font.setFamily(family)
        # at least 13 px: Windows asks for 9 pt, 12 px (Daniel, 25/10/2026: Inter at 14 px, R95, then «da 14 a 13»,
        # R123); a larger system size stays as it is
        screen = QGuiApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen is not None else 96.0
        if font.pointSizeF() > 0 and font.pointSizeF() * dpi / 72 < BODY_PX - 0.1:
            font.setPointSizeF(BODY_PX * 72 / dpi)
        app.setFont(font)
    return family


_CHART_FONTS: list = []     # (file, family, weight): given to matplotlib at its first figure or formula
_MATPLOTLIB_READY: list = []


def matplotlib_fonts() -> None:
    """The program's fonts given to matplotlib and its list cut (lean_chart_fonts), before its first figure or
    formula: done at the start, with matplotlib's import, they cost the window 0.8 s before it showed (R120)."""
    if _MATPLOTLIB_READY:
        return
    _MATPLOTLIB_READY.append(True)
    for path, family, weight in _CHART_FONTS:
        _register_for_charts(path, family, weight)
    try:
        lean_chart_fonts()
    except (AttributeError, TypeError, RuntimeError) as error:
        log.complain("fonts for the charts", error)


def lean_chart_fonts() -> int:
    """matplotlib's list of fonts cut to its own (DejaVu, the STIX and Computer Modern of the formulas) and the
    program's: each font it looks for is scored against every font of the list, and with Windows' ~1800 the first
    formulas of «How it is computed» cost 0.65 s (R120, 25/10/2026). The fonts left; nothing changes on paper."""
    try:
        import matplotlib
        from matplotlib import font_manager
    except ImportError:
        return 0
    import os
    shipped = paths.shipped("fonts")
    # the folders as text, compared as text: resolving 1800 paths on the disk cost half a second
    keep = tuple(os.path.normcase(os.path.abspath(str(k))) + os.sep
                 for k in [matplotlib.get_data_path(), *([shipped] if shipped is not None else [])])
    manager = font_manager.fontManager

    def ours(entry) -> bool:
        return os.path.normcase(os.path.abspath(entry.fname)).startswith(keep)
    before = len(manager.ttflist)
    manager.ttflist = [f for f in manager.ttflist if ours(f)]
    manager.afmlist = [f for f in manager.afmlist if ours(f)]
    cached = getattr(manager, "_findfont_cached", None)
    if cached is not None:
        cached.cache_clear()
    return before - len(manager.ttflist)


def _register_for_charts(path, family: str, weight: int) -> None:
    """The font in matplotlib's list as an entry made here: its addfont reads every name table of the file,
    half a second each (measured on 22/10/2026), for what is already known."""
    try:
        from matplotlib import font_manager
        font_manager.fontManager.ttflist.append(font_manager.FontEntry(
            fname=str(path), name=family, style="normal", variant="normal", weight=weight, stretch="normal",
            size="scalable"))
        cached = getattr(font_manager.fontManager, "_findfont_cached", None)     # a font looked up before
        if cached is not None:
            cached.cache_clear()
    except (ImportError, AttributeError, TypeError) as error:
        log.complain("fonts for the charts", error)
