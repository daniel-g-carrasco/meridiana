"""Opt-in, shared treatment of data tables; application delegates stay intact.

install(view) combines column lines, alternate rows, rounded headers, native sort
arrows, hover and selection, tabular figures and soft viewport edges. Compact
rows, page margins and initial focus are explicit choices for the caller.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import QApplication, QTableView, QTreeView, QWidget

from . import fades
from .. import theme_colors
from .design import Radius, Space, Text

HEADER_CONTRAST = 3.0
ROW_CONTRAST = 1.15


def _role(palette: QPalette, name: str) -> str:
    return palette.color(getattr(QPalette.ColorRole, name)).name()


def separator_colour(palette: QPalette) -> str:
    """A visible resize boundary, derived only from the supplied palette."""
    ground, line, ink = (_role(palette, role) for role in ("Window", "Mid", "PlaceholderText"))
    for step in range(11):
        colour = theme_colors.mix(line, ink, step / 10)
        if theme_colors.contrast(colour, ground) >= HEADER_CONTRAST:
            return colour
    return ink


def band_colour(palette: QPalette) -> str:
    """An alternate row surface visible in either theme."""
    ground, alternate, ink = (_role(palette, role) for role in ("Base", "AlternateBase", "Text"))
    for step in range(21):
        colour = theme_colors.mix(alternate, ink, step / 100)
        if theme_colors.contrast(colour, ground) >= ROW_CONTRAST:
            return colour
    return alternate


def tabular_font(base: QFont | None = None) -> QFont:
    """A copy with equal-width figures, leaving family, size and weight intact."""
    result = QFont(base if base is not None else QApplication.font())
    result.setFeature(QFont.Tag("tnum"), 1)
    return result


def table_margins() -> tuple[int, int]:
    """Horizontal and vertical page margins for a data table."""
    return Space.M, Space.S


def set_page_margins(layout) -> None:
    horizontal, vertical = table_margins()
    layout.setContentsMargins(horizontal, vertical, horizontal, vertical)


def focus_table(view: QTreeView | QTableView) -> None:
    """Give initial focus to data without removing toolbar controls from Tab order."""
    view.setFocus(Qt.FocusReason.OtherFocusReason)


def table_sheet(palette: QPalette, compact: bool = False) -> str:
    """Local rules only; the application's global typography stays in Python."""
    from .theme import arrows

    ground, text, line, selected = (_role(palette, name)
                                   for name in ("Window", "Text", "Mid", "Highlight"))
    hover = theme_colors.mix(_role(palette, "Base"), text, theme_colors.HOVER)
    selection = selected
    for step in range(12, -1, -1):
        candidate = theme_colors.mix(selected, text, step / 100)
        if theme_colors.contrast(candidate, text) >= 4.5:
            selection = candidate
            break
    inner = max(0, Radius.CONTROL - 1)
    sheet = (
        "QHeaderView { background: transparent; border: none; }"
        f"QHeaderView::section {{ background: {ground}; color: {text}; border: none;"
        f" border-right: 1px solid {separator_colour(palette)};"
        f" border-bottom: 1px solid {separator_colour(palette)}; }}"
        f"QHeaderView::section:first {{ border-top-left-radius: {inner}px; }}"
        f"QHeaderView::section:last {{ border-top-right-radius: {inner}px; }}"
        f"QHeaderView::section:only-one {{ border-top-left-radius: {inner}px;"
        f" border-top-right-radius: {inner}px; }}"
        "QHeaderView::section:last, QHeaderView::section:only-one { border-right: none; }"
        f"QHeaderView::section:hover {{ background: {_role(palette, 'Midlight')}; }}"
        f"QTreeView, QTableView {{ background: {_role(palette, 'Base')}; alternate-background-color: {band_colour(palette)}; }}"
        f"QTreeView::item, QTableView::item {{ border-right: 1px solid {line}; }}"
        f"QTreeView::item:hover:!selected, QTableView::item:hover:!selected {{ background: {hover}; }}"
        f"QTreeView::item:selected, QTableView::item:selected {{ background: {selection}; color: {text}; }}"
    )
    assets = arrows(_role(palette, "PlaceholderText"))
    if assets:
        sheet += (
            f"QHeaderView::up-arrow {{ image: url({assets['up']}); width: 8px; height: 6px; }}"
            f"QHeaderView::down-arrow {{ image: url({assets['down']}); width: 8px; height: 6px; }}"
        )
    if compact:
        sheet += (f"QTreeView::item, QTableView::item {{ padding: {Space.XXS // 2}px 0;"
                  f" min-height: {Text.SECONDARY.size + Space.XS}px; }}")
    return sheet


class CurrentMarker(QWidget):
    """A narrow overlay at the row's left edge, independent of custom delegates."""

    def __init__(self, view):
        super().__init__(view.viewport())
        self.view = view
        self._selection = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.bind()
        for bar in (view.verticalScrollBar(), view.horizontalScrollBar()):
            bar.valueChanged.connect(lambda *_: self.update())
        if isinstance(view, QTreeView):
            view.expanded.connect(lambda *_: self.update())
            view.collapsed.connect(lambda *_: self.update())
        self.follow()

    def bind(self) -> None:
        selection = self.view.selectionModel()
        if selection is not None and selection is not self._selection:
            self._selection = selection
            selection.currentChanged.connect(lambda *_: self.update())

    def follow(self) -> None:
        self.bind()
        self.setGeometry(0, 0, Space.XXS, self.view.viewport().height())
        self.raise_()
        self.show()
        self.update()

    def row_rect(self) -> QRect:
        return self.view.visualRect(self.view.currentIndex())

    def paintEvent(self, event) -> None:
        rect = self.row_rect()
        if rect.isValid():
            painter = QPainter(self)
            painter.setPen(QPen(QColor(_role(QApplication.palette(), "Accent")), Space.XXS))
            painter.drawLine(0, rect.top(), 0, rect.bottom())


class TableStyle(QObject):
    """A view-owned treatment; no model, delegate, settings or application state."""

    def __init__(self, view, compact: bool = False, soft_edges: bool = True):
        super().__init__(view)
        self.view = view
        self.compact = compact
        self._original_sheet = view.styleSheet()
        self._normal_height = None
        self._normal_minimum = None
        if isinstance(view, QTableView):
            header = view.verticalHeader()
            self._normal_height = header.defaultSectionSize()
            self._normal_minimum = header.minimumSectionSize()
            view.setShowGrid(False)
        view.destroyed.connect(self._detach)
        self.marker = CurrentMarker(view)
        self.fades = fades.attach(view) if soft_edges else None
        view.setAlternatingRowColors(True)
        view.setMouseTracking(True)
        view.installEventFilter(self)
        view.viewport().installEventFilter(self)
        self.refresh()

    def _detach(self, *_args) -> None:
        self.fades = None
        self.marker = None
        self.view = None

    def refresh(self) -> None:
        sheet = self._original_sheet + table_sheet(QApplication.palette(), self.compact)
        if self.view.styleSheet() != sheet:
            self.view.setStyleSheet(sheet)
        font = tabular_font(self.view.font())
        font.setPixelSize(Text.SECONDARY.size if self.compact else Text.BODY.size)
        if self.view.font() != font:
            self.view.setFont(font)
        if isinstance(self.view, QTableView):
            header = self.view.verticalHeader()
            minimum = Text.SECONDARY.size + Space.XS + Space.XXS
            header.setMinimumSectionSize(minimum if self.compact else self._normal_minimum)
            header.setDefaultSectionSize(minimum if self.compact else self._normal_height)
        self.marker.follow()

    def set_compact(self, compact: bool) -> None:
        self.compact = bool(compact)
        self.refresh()

    def eventFilter(self, watched, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.PaletteChange and watched is self.view:
            wanted = self._original_sheet + table_sheet(QApplication.palette(), self.compact)
            if self.view.styleSheet() != wanted:
                QTimer.singleShot(0, self.view, self.refresh)
        elif kind in (QEvent.Type.Resize, QEvent.Type.Show):
            self.marker.follow()
        return False


def install(view: QTreeView | QTableView, *, compact: bool = False,
            soft_edges: bool = True) -> TableStyle:
    """Install once, preserving custom delegates and the model's sorting contract."""
    if not isinstance(view, (QTreeView, QTableView)):
        raise TypeError("A QTreeView or QTableView is required")
    existing = view.findChild(TableStyle)
    return existing if existing is not None else TableStyle(view, compact, soft_edges)


def install_data_tables(root: QWidget, *, excluded: tuple[str, ...] = ()) -> tuple[TableStyle, ...]:
    """Treat data tables with headers, leaving single-column navigation alone."""
    controllers = []
    for view in root.findChildren(QWidget):
        if not isinstance(view, (QTreeView, QTableView)) or view.objectName() in excluded:
            continue
        model = view.model()
        header = view.header() if isinstance(view, QTreeView) else view.horizontalHeader()
        if model is None or model.columnCount() < 2 or header.isHidden():
            continue
        controllers.append(install(view))
    return tuple(controllers)
