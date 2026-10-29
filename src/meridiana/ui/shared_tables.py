"""Opt-in, shared treatment of data tables; application delegates stay intact.

install(view) combines column lines, alternate rows, rounded headers, native sort
arrows, hover and selection, tabular figures and soft viewport edges. Compact
rows, page margins and initial focus are explicit choices for the caller.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QObject, QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QFont, QPainter, QPainterPath, QPalette, QPixmap
from PySide6.QtWidgets import QApplication, QStyle, QStyleOption, QTableView, QTreeView, QWidget

from . import fades, scrollbars
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
        f"QHeaderView::section:only-one {{ border-top-left-radius: {inner}px;"
        " border-top-right-radius: 0; }"
        f"QWidget#table-gutter-header {{ background: {ground}; border: none;"
        f" border-top-right-radius: {inner}px; border-bottom: 1px solid {separator_colour(palette)}; }}"
        "QHeaderView::section:last, QHeaderView::section:only-one { border-right: none; }"
        f"QHeaderView::section:hover {{ background: {_role(palette, 'Midlight')}; }}"
        f"QTreeView, QTableView {{ background: {_role(palette, 'Base')};"
        f" alternate-background-color: {band_colour(palette)}; outline: 0; }}"
        f"QTreeView::item, QTableView::item {{ border-right: 1px solid {line}; }}"
        f"QTreeView::item:hover:!selected, QTableView::item:hover:!selected {{ background: {hover}; }}"
        f"QTreeView::item:selected, QTableView::item:selected {{ background: {selection}; color: {text}; }}"
    )
    assets = arrows(_role(palette, "PlaceholderText"))
    if assets:
        sheet += (
            f"QHeaderView::up-arrow {{ image: url({assets['up']}); width: 8px; height: 6px; right: {Space.S}px; }}"
            f"QHeaderView::down-arrow {{ image: url({assets['down']}); width: 8px; height: 6px; right: {Space.S}px; }}"
        )
    if compact:
        sheet += (f"QTreeView::item, QTableView::item {{ padding: {Space.XXS // 2}px 0;"
                  f" min-height: {Text.SECONDARY.size + Space.XS}px; }}")
    return sheet


class TableFrame(QWidget):
    """Restore the native frame above rectangular viewport children with an antialiased inner edge."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self._cache = None
        self._key = None
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.show()

    def follow(self) -> None:
        self.setGeometry(self.view.rect())
        self.raise_()
        self.update()

    def paintEvent(self, event) -> None:
        ancestors = []
        widget = self.view
        while widget is not None:
            ancestors.append(widget)
            widget = widget.parentWidget()
        key = (self.size(), self.devicePixelRatioF(),
               tuple((id(widget), widget.size(), widget.palette().cacheKey(), widget.styleSheet(),
                      self.view.mapTo(widget, QPoint())) for widget in ancestors))
        if key != self._key:
            # QWidget.render() here reenters the parent's painter and layout. Draw the
            # native stylesheet primitives directly, including the surfaces behind the
            # table: filling Base outside the curve would leave square white corners.
            frame = QPixmap(self.size() * self.devicePixelRatioF())
            frame.setDevicePixelRatio(self.devicePixelRatioF())
            ground = (self.view.palette().color(QPalette.ColorRole.Base) if self.view.isWindow()
                      else ancestors[-1].palette().color(ancestors[-1].backgroundRole()))
            frame.fill(Qt.GlobalColor.transparent)
            painter = QPainter(frame)
            painter.fillRect(self.rect(), ground)
            for widget in reversed(ancestors):
                painter.save()
                painter.translate(-self.view.mapTo(widget, QPoint()))
                if widget.autoFillBackground():
                    painter.fillRect(widget.rect(), widget.palette().brush(widget.backgroundRole()))
                option = QStyleOption()
                option.initFrom(widget)
                widget.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, widget)
                painter.restore()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
            width = self.view.frameWidth()
            inner = QPainterPath()
            inner.addRoundedRect(QRectF(self.rect()).adjusted(width, width, -width, -width),
                                 max(0, Radius.CONTROL - width), max(0, Radius.CONTROL - width))
            painter.fillPath(inner, Qt.GlobalColor.black)
            painter.end()
            self._cache, self._key = frame, key
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self._cache)


class LastRowLine(QWidget):
    """Close the column separators at the last visible data row, without changing delegates."""

    def __init__(self, view):
        super().__init__(view.viewport())
        self.view = view
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for bar in (view.verticalScrollBar(), view.horizontalScrollBar()):
            bar.valueChanged.connect(self.follow)
        if isinstance(view, QTreeView):
            view.expanded.connect(self.follow)
            view.collapsed.connect(self.follow)
        else:
            view.verticalHeader().sectionResized.connect(self.follow)
        header = view.header() if isinstance(view, QTreeView) else view.horizontalHeader()
        header.sectionResized.connect(self.follow)
        header.sectionMoved.connect(self.follow)
        self.follow()
        self.show()

    def follow(self, *_args) -> None:
        self.setGeometry(self.view.viewport().rect())
        self.raise_()
        self.update()

    def _last_index(self) -> QModelIndex:
        view, model = self.view, self.view.model()
        if model is None:
            return QModelIndex()
        parent = view.rootIndex()
        if isinstance(view, QTableView):
            rows = view.verticalHeader()
            for visual in range(rows.count() - 1, -1, -1):
                row = rows.logicalIndex(visual)
                if not view.isRowHidden(row):
                    return model.index(row, 0, parent)
            return QModelIndex()
        last = QModelIndex()
        while True:
            child = next((model.index(row, 0, parent)
                          for row in range(model.rowCount(parent) - 1, -1, -1)
                          if not view.isRowHidden(row, parent)), QModelIndex())
            if not child.isValid():
                return last
            last = child
            if not view.isExpanded(child):
                return last
            parent = child

    def paintEvent(self, event) -> None:
        index = self._last_index()
        if not index.isValid():
            return
        header = self.view.header() if isinstance(self.view, QTreeView) else self.view.horizontalHeader()
        column = next((header.logicalIndex(visual) for visual in range(header.count())
                       if not header.isSectionHidden(header.logicalIndex(visual))), None)
        if column is None:
            return
        rect = self.view.visualRect(index.siblingAtColumn(column))
        if not rect.isValid() or not 0 <= rect.bottom() < self.height():
            return
        width = min(self.width(), header.length() - header.offset())
        painter = QPainter(self)
        painter.fillRect(QRect(0, rect.bottom(), width, 1), self.view.palette().color(QPalette.ColorRole.Mid))


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
        self.marker = None  # Kept for callers of the previous controller API.
        scrollbars.keep_room(view)
        self.header = view.header() if isinstance(view, QTreeView) else view.horizontalHeader()
        # Qt otherwise runs the vertical scrollbar beside the header as well as the rows.
        # A native scrollbar accessory reserves its header portion without moving the viewport.
        self.gutter_header = QWidget(view)
        self.gutter_header.setObjectName("table-gutter-header")
        self.gutter_header.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        view.addScrollBarWidget(self.gutter_header, Qt.AlignmentFlag.AlignTop)
        self.header.installEventFilter(self)
        self.last_row_line = LastRowLine(view)
        self.fades = fades.attach(view, table=True) if soft_edges else None
        self.frame = TableFrame(view)
        if self.fades is not None:
            self.fades.frame = self.frame
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
        self._follow_header()

    def _follow_header(self) -> None:
        self.gutter_header.setFixedHeight(0 if self.header.isHidden() else self.header.height())
        if hasattr(self, "last_row_line"):
            self.last_row_line.follow()
        if hasattr(self, "frame"):
            self.frame.follow()

    def set_compact(self, compact: bool) -> None:
        self.compact = bool(compact)
        self.refresh()

    def eventFilter(self, watched, event) -> bool:
        kind = event.type()
        if kind == QEvent.Type.PaletteChange and watched is self.view:
            wanted = self._original_sheet + table_sheet(QApplication.palette(), self.compact)
            if self.view.styleSheet() != wanted:
                QTimer.singleShot(0, self.view, self.refresh)
        elif kind in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.DevicePixelRatioChange):
            self._follow_header()
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
