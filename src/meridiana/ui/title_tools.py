"""The controls of a card that live on its title's line (R345; Daniel, 03/11/2026: «questi elementi sarebbe bello
riuscire a farli stare sulla stessa riga in alto ... vorrei trovare un modo per occupare meno spazio e darne di più al
contenuto»): the Checks' views, counts and filters stand beside the title and its cross instead of in two rows of
their own, and the room they took goes to the list.

`TitleTools` lays its widgets out in order, left to right, and wraps them when the card is narrow: a widget that does
not fit what is left of the row goes to the next row at its own width; one wider than a whole row is reduced down to
its least size (a track of segments cuts its words with the dots, its tooltip says them whole). Nothing is ever cut
by the card's edge nor stands on another. A widget added with `align="end"` stands against the right end of its
row, one added with `align="tail"` is kept on the first row, at its end, beside the card's cross.

The card's title bar (ui/cards.CardTitle.set_tools) gives it the room: its width, how far the first row starts from
the left (the title's words) and how tall that row is at least. Alone, in a page, it is a plain row on top."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, QSize, Signal
from PySide6.QtWidgets import QSizePolicy, QWidget

from .design import Space

GAP = Space.M           # between two widgets of a row
ROW_GAP = Space.XS      # between two rows


class TitleTools(QWidget):
    changed = Signal()      # the room it asks for has changed (a widget grew): the card asks the layout again

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("title-tools")
        self.items: list[tuple[QWidget, str]] = []
        self.indent = 0         # how far from the left the first row starts (the card's title stands there)
        self.first = 0          # the first row at least this tall (the title's line)
        self.planned = (None, None)     # the last plan and what it was for: asked dozens of times at a step of an edge (R372)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        policy.setHeightForWidth(True)          # alone in a page's layout the rows ask for their height by the width
        self.setSizePolicy(policy)

    def add(self, widget: QWidget, align: str = "start") -> QWidget:
        if align not in ("start", "end", "tail"):
            raise ValueError(f"align {align!r}")
        widget.setParent(self)
        self.items.append((widget, align))
        return widget

    # ----- the plan

    def plan(self, width: int, indent: int = 0, first: int = 0) -> tuple[list[tuple[QWidget, QRect]], list[int]]:
        """Where each visible widget stands in a room `width` wide, the first row starting `indent` from the left and
        at least `first` tall, and the height of each row."""
        tail = [w for w, a in self.items if a == "tail" and not w.isHidden()]
        flow = [(w, a) for w, a in self.items if a != "tail" and not w.isHidden()]
        tail_width = sum(w.sizeHint().width() for w in tail) + GAP * len(tail)
        first_right = max(0, width - tail_width)        # the first row's right end; the others', the card's
        rows: list[list[list]] = [[]]                   # per row: [widget, align, width]
        x = indent
        for w, align in flow:
            pref = w.sizeHint().width()
            least = min(pref, w.minimumSizeHint().width())
            right = first_right if len(rows) == 1 else width
            if x + pref > right and (rows[-1] or len(rows) == 1):
                rows.append([])                         # to the next row, at its own width
                x, right = 0, width
            size = pref if x + pref <= right else max(least, right - x)
            rows[-1].append([w, align, size])
            x += size + GAP
        placed: list[tuple[QWidget, QRect]] = []
        heights: list[int] = []
        y = 0
        for i, row in enumerate(rows):
            tall = [w.sizeHint().height() for w, _a, _s in row]
            if i == 0:
                tall += [first] + [t.sizeHint().height() for t in tail]
            height = max(tall, default=0)
            right = first_right if i == 0 else width
            x = indent if i == 0 else 0
            for w, align, size in row:
                left = x if align != "end" else max(x, right - size)
                h = w.sizeHint().height()
                placed.append((w, QRect(left, y + (height - h) // 2, size, h)))
                x = left + size + GAP
            if i == 0:
                at = width
                for t in reversed(tail):
                    w, h = t.sizeHint().width(), t.sizeHint().height()
                    at -= w
                    placed.append((t, QRect(at, y + (height - h) // 2, w, h)))
                    at -= GAP
            heights.append(height)
            y += height + ROW_GAP
        return placed, heights

    def kept_plan(self, width: int, indent: int = 0, first: int = 0) -> tuple[list[tuple[QWidget, QRect]], list[int]]:
        """The plan, worked out again only when the room, a widget's being shown or a widget's size has changed (a widget
        that changes size tells its parent with a LayoutRequest, see `event`)."""
        key = (width, indent, first, tuple(w.isHidden() for w, _a in self.items))
        if self.planned[0] != key:
            self.planned = (key, self.plan(width, indent, first))
        return self.planned[1]

    def height_for(self, width: int, indent: int = 0, first: int = 0) -> int:
        heights = self.kept_plan(width, indent, first)[1]
        return sum(heights) + ROW_GAP * (len(heights) - 1)

    def first_row(self, width: int, indent: int = 0, first: int = 0) -> int:
        """The height of the first row, where the title and the cross stand."""
        return self.kept_plan(width, indent, first)[1][0]

    # ----- the widget

    def sizeHint(self) -> QSize:
        wide = sum(w.sizeHint().width() for w, _a in self.items if not w.isHidden())
        shown = sum(1 for w, _a in self.items if not w.isHidden())
        m = self.contentsMargins()
        width = wide + GAP * max(0, shown - 1) + self.indent
        return QSize(width + m.left() + m.right(), self.height_for(width, self.indent, self.first) + m.top() + m.bottom())

    def heightForWidth(self, width: int) -> int:
        m = self.contentsMargins()
        return self.height_for(max(0, width - m.left() - m.right()), self.indent, self.first) + m.top() + m.bottom()

    def minimumSizeHint(self) -> QSize:
        return QSize(0, self.sizeHint().height())

    def room(self) -> int:
        m = self.contentsMargins()
        return max(0, self.width() - m.left() - m.right())

    def relayout(self) -> None:
        m = self.contentsMargins()
        placed, _heights = self.kept_plan(self.room(), self.indent, self.first)
        for w, rect in placed:
            w.setGeometry(rect.translated(m.left(), m.top()))
            w.show()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.relayout()

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.LayoutRequest:
            self.planned = (None, None)
            self.relayout()
            self.changed.emit()
        return super().event(event)
