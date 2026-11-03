"""The design system: the closed scales every widget takes its measures from (Daniel, 24/10/2026: «dai massima
priorità all'armonizzazione estetica e di stile… l'obiettivo è avere un template facilmente riutilizzabile per altri
programmi»). One place for the numbers; the style sheet (ui/theme.py), the cards (ui/cards.py), the drawn widgets and
the gallery (ui/gallery.py) read them here. The colours are not here: they are the theme's tokens
(theme_colors.derive), made from one accent and one choice of backgrounds.

The rules, in docs/design/sistema-grafico.md with the reasons:
- spacing on a scale of 2, 4, 6, 8, 12, 16, 24, 32: nothing in between;
- four radii by depth: 8 a card, a tile, a little window; 6 a view inside its card and a control
  (button, field, list, group, table, tool button, a track of segments); 4 what stands inside a control or a row (a
  menu's item, a selection inside a card, a small button on a row, a segment); no shape round at its ends, no «pill»
  (R322, R328, Daniel 02/11/2026: «tutti i tasti devono essere portati su questo stile di rettangolo con angoli
  arrotondati, anziché su quello di rettangoli con due cerchi alle estremità»), but for the plan's labels of the sides,
  round again at Daniel's word (R336, `Radius.PLAN_LABEL`);
- one line of 1 px per depth, 2 px for the focus;
- the text in a closed catalogue of named styles (`Text`, R121 of 25/10/2026): six sizes (11, 12, 13 the text
  since R123, 14, 18, 22) and two weights, each style with its colour's token; nothing else in the window;
- the buttons in a closed set of kinds (`Button`), each with one height and one radius;
- the controls 28 px high, their text 8 px from their edge; the icons at 16 in a control, 18 in a list, 22 in a
  bar, 24 in a tile;
- the scroll bars 10 px wide, their room always kept (R100);
- three durations, with less motion they are nought.

No Qt at import: `font` and `text_font` build a QFont when asked for one, so the scales can be read by tools and
tests."""

from __future__ import annotations

from dataclasses import dataclass


class Space:
    """Spacing, in logical pixels."""
    XXS = 2
    XS = 4
    S = 6
    M = 8
    L = 12
    XL = 16
    XXL = 24
    XXXL = 32
    SCALE = (0, 2, 4, 6, 8, 12, 16, 24, 32)


class Radius:
    CARD = 8            # a card, a tile, a page, a little window (menu, popup, tooltip's frame)
    VIEW = 6            # a view (plan, 3D) 6 px inside its card (R77): a control's corners
    CONTROL = 6         # a button, a field, a list, a group, a table, a tool button, a track, a state, a label
    INNER = 4           # inside a control or a row: a menu's item, the selection in a card, a row's small button
    MARK = 2            # a swatch, a tick of a legend
    PLAN_LABEL = 10     # the plan's labels of the sides (the pill with its disc and the field that opens from it, R336):
                        # round at the ends, half of their usual height; Qt keeps it to half the height of a smaller one


class Type:
    """The text's sizes in logical pixels and its two weights. The styles made of them are `Text`: a size or a
    weight is never chosen on its own."""
    TINY = 10           # the names of the bar's groups alone (R159, Daniel 25/10/2026: «più leggeri, piccoli»)
    CAPTION = 11        # captions, the ticks of a chart, the labels in capitals, a count in a pill
    SMALL = 12          # secondary text: notes, the status bar, the words under the tools, the axes' titles
    BODY = 13           # the text (Inter, R95; 13 px since R123, Daniel 25/10/2026: «da 14 a 13»)
    TITLE = 14          # the title of a card, of a tile of the File page
    HEADING = 18        # a heading inside a page or a dialog
    DISPLAY = 22        # a page's title, the figure of a result
    SCALE = (TINY, CAPTION, SMALL, BODY, TITLE, HEADING, DISPLAY)
    CONTROL = BODY      # the word of a button, a tab, a segment: the text's size (the tabs were 15, R121)
    REGULAR, SEMIBOLD = 400, 600
    BOLD = SEMIBOLD     # one weight for what stands out: a bold asked for is the semibold (R121)
    LETTER_SPACING = 4  # percent, for the labels in capitals
    MICRO = CAPTION     # the name before 25/10/2026 of the labels in capitals (10 px then)


@dataclass(frozen=True)
class TextStyle:
    """One style of text: its size, its weight, the token of its colour, in capitals or not."""
    name: str
    size: int
    weight: int
    tone: str = "text"          # the theme's token: text, text2 or muted
    caps: bool = False          # in capitals, with Type.LETTER_SPACING

    @property
    def key(self) -> tuple:
        """What a font must have to be this style: size, weight, capitals."""
        return (self.size, self.weight, self.caps)


class Text:
    """The catalogue of the window's texts (R121, Daniel 25/10/2026: «alcune differenze ci devono essere ma non
    devono essere troppe e devono avere un senso, e devono essere salvate come stile»), on the text at 13 px (R123).
    Every text of the window is one of these; docs/design/sistema-grafico.md says where each is used,
    tests/finestra/test_design_system.py checks that no other font is on screen."""
    DISPLAY = TextStyle("display", Type.DISPLAY, Type.SEMIBOLD)              # a page's title, a result's figure
    HEADING = TextStyle("heading", Type.HEADING, Type.SEMIBOLD)              # a heading inside a page or dialog
    TITLE = TextStyle("title", Type.TITLE, Type.SEMIBOLD)                    # a card, a tile of the File page
    STRONG = TextStyle("strong", Type.BODY, Type.SEMIBOLD)                   # a group, a row's name, a button
    BODY = TextStyle("body", Type.BODY, Type.REGULAR)                        # the text, fields, lists, menus
    DESCRIPTION = TextStyle("description", Type.BODY, Type.REGULAR, "text2")  # a sentence that explains
    CONTROL = TextStyle("control", Type.CONTROL, Type.REGULAR)               # a tab, a segment, a state
    SECONDARY = TextStyle("secondary", Type.SMALL, Type.REGULAR, "text2")    # notes, status bar, tools, axes
    CAPTION = TextStyle("caption", Type.CAPTION, Type.REGULAR, "muted")      # ticks, formats, sources
    LABEL = TextStyle("label", Type.CAPTION, Type.SEMIBOLD, "muted", True)   # sections, counts
    GROUP = TextStyle("group", Type.TINY, Type.REGULAR, "muted", True)       # the names of the bar's groups (R159)
    ALL = (DISPLAY, HEADING, TITLE, STRONG, BODY, DESCRIPTION, CONTROL, SECONDARY, CAPTION, LABEL, GROUP)
    BUTTON = STRONG             # the word of a push button, the phase in hand: what stands out

    @classmethod
    def keys(cls) -> set:
        """The fonts allowed in the window: (size, weight, capitals)."""
        return {s.key for s in cls.ALL}


# the size of the text (R133, Daniel 26/10/2026: «farei 12, 13 e 14 come piccolo, medio e grande»): the whole scale a
# pixel smaller or larger, the text at 12, 13 or 14 px. Chosen in Preferences > Appearance and set at the start,
# before any widget is built: a size is read when a font is made (on a screen at 100 % the 13 px of the text are 13
# pixels, at 200 % they are 26: R171)
TEXT_SIZES = {"small": -1, "medium": 0, "large": 1}
_SIZES = {name: getattr(Type, name) for name in ("TINY", "CAPTION", "SMALL", "BODY", "TITLE", "HEADING", "DISPLAY")}
_STYLES = {name: getattr(Text, name) for name in ("DISPLAY", "HEADING", "TITLE", "STRONG", "BODY", "DESCRIPTION",
                                                  "CONTROL", "SECONDARY", "CAPTION", "LABEL", "GROUP")}


def set_text_size(choice: str) -> None:
    """The type scale and the styles of `Text` for the size chosen (a key of TEXT_SIZES; any other is the medium)."""
    import dataclasses
    step = TEXT_SIZES.get(choice, 0)
    for name, px in _SIZES.items():
        setattr(Type, name, px + step)
    Type.SCALE = tuple(getattr(Type, name) for name in _SIZES)
    Type.CONTROL = Type.BODY
    Type.MICRO = Type.CAPTION
    for name, style in _STYLES.items():
        setattr(Text, name, dataclasses.replace(style, size=style.size + step))
    Text.ALL = tuple(getattr(Text, name) for name in _STYLES)
    Text.BUTTON = Text.STRONG


def text_size() -> str:
    """The size of the text in use: a key of TEXT_SIZES."""
    step = Type.BODY - _SIZES["BODY"]
    return next((k for k, v in TEXT_SIZES.items() if v == step), "medium")


class Size:
    CONTROL = 28        # a button, a field, a list closed, a tool button with its icon alone
    COMPACT = 22        # the drop-down part of a list, a swatch's row
    CHIP = 24           # a segment (a tab, a view, a count), a state's label, a filter
    TAB = 36            # a tab of the phases
    NAV = 34            # an item of a list of places (the File page)
    SCROLLBAR = 10      # the scroll bar's room, always kept (R100); its thumb THUMB wide
    THUMB = 6
    CHART_MIN_HEIGHT = 160
    PANEL_MIN = 120     # a panel docked and shown, narrower (or lower, at the bottom) than this at the start, goes back
                        # to its first size (R323): below it a panel is open and not to be seen
    READING = 440       # a text alone in a wide card goes in a column this wide, about 70 characters at 13 px
                        # (an empty state, R321)
    PLACEHOLDER = 160   # a card dropped across the window (a band above or below it, above or below a panel as wide):
                        # its slot this tall, not the card's own height, the central card not jumping (R317)
    # Meridio's bubble (R363, measured on photos)
    BUBBLE_MIN_WIDTH = 280      # about 30 characters of his words in the conversation: less, and they wrap at each word
    BUBBLE_MIN_HEIGHT = 240     # the head, the status, 6 lines of conversation and the field, in the low arrangement
    BUBBLE_NARROW = 300         # a panel narrower than this: where he thinks as its icon alone
    BUBBLE_LOW = 300            # a panel lower than this: no name (it is on him), «Attach» in a menu at the head
    BUBBLE_STATUS = 18          # the status line (the phase, the dots, the cost): this tall, even empty
    BUBBLE_READING = 64         # the conversation keeps this much (3 lines) before the suggestions give way


class Button:
    """The kinds of buttons (R121: «deve includere tutti i tasti»), each one height and one radius: (height,
    radius). The text is Text.STRONG on the push buttons, Text.CONTROL on the others (docs/design/sistema-grafico.md,
    §4)."""
    PUSH = (Size.CONTROL, Radius.CONTROL)   # a command («Calcola», «Esporta…»), primary (accent) or destructive
    TOOL = (Size.CONTROL, Radius.CONTROL)   # a tool with its icon alone; with its word under it, as tall as both
    CHIP = (Size.CHIP, Radius.CONTROL)      # a small button with its word: the tour's steps (a choice between views is
                                            # a track of segments, ui/segments.py)
    SMALL = (20, Radius.INNER)              # on a title: the card's cross, the help's pin (a row's fix and eye are
                                            # CHIP tall, R124)
    HELP = (16, Radius.INNER)               # the «?» of a group or a tile
    NAV = (Size.NAV, Radius.CONTROL)        # an item of a list of places (the File page)


class Icon:
    CONTROL = 16
    LIST = 18
    BAR = 22
    TILE = 24
    STROKE = 1.7        # the drawings' line (the mockups)


class Line:
    HAIR = 1            # a card's line, a divider
    FOCUS = 2           # the focus, the accent's
    TEXT_INSET = 8      # a control's text from its edge (border included)


class Bar:
    """The buttons of a phase's bar (R333, Daniel 03/11/2026: «armonizzare le dimensioni dei tasti, renderli più
    congruenti tra loro»), one height and one icon per mode of the bar for all of them. The width is a rule, not the
    word's own: the least width that holds the word, on steps, so that a bar has three or four widths and not one
    per word. A button with a menu is the same button plus its strip. docs/design/sistema-grafico.md, §4."""
    UNDER, BESIDE, ICONS = "under", "beside", "icons"       # the word under the icon, beside it, the icon alone
    ICON = {UNDER: Icon.TILE, BESIDE: Icon.CONTROL, ICONS: Icon.BAR}
    HEIGHT = Size.CONTROL       # beside and icons alone; under the icon, the icon and the word's line
    WORD_MIN = 48               # the word under the icon (study 26, S2)
    STEP = {UNDER: Space.XL, BESIDE: Space.M}       # beside the icon the word is one part of the width: finer steps
    ICON_WIDTH = Space.XXXL     # the icon alone
    PAD = 2 * Space.XS + 2 + Space.XXS              # around what the button holds: the sheet's padding and border, air
    WORD_GAP = Space.XS         # between an icon and the word beside it
    STRIP = Space.L + Space.XXS                     # the strip of a button with a menu, every mode
    GAP = Space.XXS             # between two buttons of a group
    GROUP_AIR = Space.M         # between a group and the line beside it
    LINE = Line.HAIR

    @classmethod
    def width(cls, mode: str, word: int) -> int:
        """The command's width in a mode, for a word `word` pixels long (the widest of its menu)."""
        if mode == cls.ICONS:
            return cls.ICON_WIDTH
        step = cls.STEP[mode]
        need = word + cls.PAD + (cls.ICON[mode] + cls.WORD_GAP if mode == cls.BESIDE else 0)
        least = cls.WORD_MIN if mode == cls.UNDER else 0
        return max(least, (need + step - 1) // step * step)


class Motion:
    """Durations in milliseconds; with less motion they are nought (Motion.of)."""
    FAST = 110          # a little window comes, a hover
    QUICK = 130         # Meridio's bubble goes (Daniel, 25/10/2026: «130 ms»; his slide is his own, 320, R155)
    NORMAL = 180        # a page changes, a section opens
    SLOW = 240          # something large moves (a panel slides), the 3D camera glides to a view
    CAREFUL = 360       # a delicate movement: the cards making room for a panel carried over them, the panel
                        # settling into its slot (R312: «un po' di lentezza nelle animazioni»)
    DWELL = 280         # a wait, not a movement: a drop zone answers the panel carried over it only after it;
                        # passing over the cards does not make them dance (R312). Kept with less motion
    TYPING_MS = 24      # text that comes as in a chat (motion.TypeOut): one step every so many ms...
    TYPING_CHARS = 4    # ...of at least so many characters (more when the text is long: it takes TYPING_MAX_MS at most)
    TYPING_MAX_MS = 1800

    @staticmethod
    def of(ms: int, reduced: bool) -> int:
        return 0 if reduced else ms


class Layout:
    """The window as cards on a floor (study 17, A3; the target of 24/10/2026)."""
    GAP = Space.M       # between two cards, and from the bars above and below
    EDGE = Space.L      # from the window's sides
    PAD = Space.S       # inside a card, around its content
    TITLE_X = Space.L   # a card's title from its left edge
    PAGE = (Space.XXL + 4, Space.XXL - 2)   # a page's inside (the File page): 28 at the sides, 22 above and below


def font(size: int | None = None, weight: int = Type.REGULAR, base=None):
    """The application's font at `size` logical pixels (the text's, Type.BODY, by default) and `weight` (a QFont;
    `base` the font to start from). Prefer text_font with a style of `Text`."""
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication
    f = QFont(base if base is not None else QApplication.font())
    f.setPixelSize(int(Type.BODY if size is None else size))
    f.setWeight(QFont.Weight(min(int(weight), Type.SEMIBOLD)))
    return f


def text_font(style: TextStyle | None = None, base=None):
    """The QFont of a style of the catalogue (Text.BODY by default; `base` the font to start from: its family)."""
    from PySide6.QtGui import QFont
    style = style or Text.BODY
    f = font(style.size, style.weight, base)
    f.setCapitalization(QFont.Capitalization.AllUppercase if style.caps else QFont.Capitalization.MixedCase)
    f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + (Type.LETTER_SPACING if style.caps else 0))
    return f


def set_text(widget, style: TextStyle):
    """`widget` in a style of the catalogue: its font, and its colour through the global sheet (the property
    `tone`, read by ui/theme.style_sheet). The widget, for chaining."""
    widget.setFont(text_font(style, widget.font()))
    tone = "" if style.tone == "text" else style.tone
    if (widget.property("tone") or "") != tone:
        widget.setProperty("tone", tone or None)
        from PySide6.QtCore import Qt
        if widget.testAttribute(Qt.WidgetAttribute.WA_WState_Polished):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
    return widget


def free_text(label, style: TextStyle | None = None):
    """A text that stands alone in a section whose layout has no margins (a section that holds cards and pages
    of its own, the Plant's): its sides inset as the text of a control (R296), so that it never touches the frame.
    Set on the label, not on the section: the groups inside a section keep their own margins. In `style` of the
    catalogue when given. The label, for chaining."""
    label.setContentsMargins(Space.M, Space.XS, Space.M, Space.XS)
    return label if style is None else set_text(label, style)


def set_text_all(root, style: TextStyle) -> None:
    """`root` and every widget inside it in a style of the catalogue (a bar of small words: the status bar). A
    font set on a widget does not reach its children under the global sheet."""
    from PySide6.QtWidgets import QWidget
    set_text(root, style)
    for w in root.findChildren(QWidget):
        w.setFont(text_font(style, w.font()))


def css(style: TextStyle) -> str:
    """The style's size and weight for rich text (an inline «style» or a document's default sheet)."""
    caps = " text-transform: uppercase;" if style.caps else ""
    return f"font-size: {style.size}px; font-weight: {style.weight};{caps}"


def strong(text: str) -> str:
    """Rich text that stands out: Text.STRONG's semibold, not the bold of «<b>» (700, a third weight)."""
    return f"<span style='font-weight: {Type.SEMIBOLD}'>{text}</span>"


def semibold(rich: str) -> str:
    """Rich text with its «<b>» made the semibold (a translated sentence that carries the tags)."""
    return rich.replace("<b>", f"<span style='font-weight: {Type.SEMIBOLD}'>").replace("</b>", "</span>")


def padding(vertical: int, horizontal: int, border: int = Line.HAIR) -> str:
    """A style sheet's padding that puts the content `vertical` and `horizontal` pixels from the outer edge of a
    control whose border is `border` wide: «padding: 2px 7px;» for (3, 8)."""
    return f"padding: {max(0, vertical - border)}px {max(0, horizontal - border)}px;"
