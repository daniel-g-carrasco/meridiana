"""The File page (R40, R53; Daniel's choice of 24/10/2026, «ci sta mi piace»): what was in the menus, as a page of
its own over the window, as Office's and Revit's File (the target, docs/studio/19-grafica, bersaglio-file). The
menu bar is hidden and Alt shows it (ui/menubar.py); the page is reached from the «File» button at the left of
the phases' row, and Esc or «Back to the project» closes it.

On the left the list: Back, New, Open, Save, Save as, Save a revision, Import, Export, Catalogues, Settings with its
seven sections, Help and manual, Quit. The commands start at once (the page closes first); Open, Import, Export,
Catalogues, Settings and Help open their section on the right. Every button starts one of the window's commands or
shows one of these places."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget)

from ..i18n import _
from . import icons
from .design import Icon, Layout, Motion, Radius, Size, Space, Text, text_font

NAV_WIDTH = 250


class TileIcon(QLabel):
    """A File tile's fixed icon column; rasterise again when its palette changes."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self.setFixedSize(Icon.TILE, Icon.TILE)
        self._refresh()

    def _refresh(self) -> None:
        self.setPixmap(icons.icon(self.name).pixmap(QSize(Icon.TILE, Icon.TILE), self.devicePixelRatioF()))

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.ApplicationPaletteChange,
                            QEvent.Type.StyleChange):
            self._refresh()


class Tile(QFrame):
    """A thing to do: its icon, its name, what it does, the formats it takes, its button."""

    def __init__(self, icon: str, name: str, what: str, formats: tuple, button: str, slot: Callable):
        super().__init__()
        self.setObjectName("ftile")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        grid = QGridLayout(self)
        grid.setContentsMargins(Space.XL, Space.L, Space.XL, Space.L)
        grid.setHorizontalSpacing(Space.L)
        grid.setVerticalSpacing(Space.S)
        mark = TileIcon(icon)
        grid.addWidget(mark, 0, 0, 2, 1, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        title = QLabel(name)
        title.setObjectName("ftile-name")
        title.setFont(text_font(Text.TITLE))
        grid.addWidget(title, 0, 1)
        text = QLabel(what)
        text.setObjectName("ftile-text")
        text.setWordWrap(True)
        text.setFont(text_font(Text.DESCRIPTION))
        grid.addWidget(text, 1, 1)
        foot = QHBoxLayout()
        foot.setSpacing(Space.S)
        for f in formats:
            chip = QLabel(f)
            chip.setObjectName("ftile-format")
            chip.setFont(text_font(Text.CAPTION))
            foot.addWidget(chip)
        foot.addStretch(1)
        self.button = QPushButton(button)
        self.button.clicked.connect(slot)
        foot.addWidget(self.button)
        grid.setRowMinimumHeight(2, Space.XS)
        grid.addLayout(foot, 3, 1)
        grid.setColumnStretch(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)


class Section(QScrollArea):
    """A section of the page: its title, a line that says what it holds, its groups of tiles."""

    def __init__(self, title: str, lead: str):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        self.box = QVBoxLayout(body)
        self.box.setContentsMargins(Layout.PAGE[0], Layout.PAGE[1], Layout.PAGE[0], Layout.PAGE[1])
        self.box.setSpacing(0)
        self._groups: list[tuple[QGridLayout, list, int]] = []
        head = QLabel(title)
        head.setObjectName("fpage-title")
        head.setFont(text_font(Text.DISPLAY))
        self.box.addWidget(head)
        lead_label = QLabel(lead)
        lead_label.setObjectName("fpage-lead")
        lead_label.setWordWrap(True)
        lead_label.setMaximumWidth(760)
        lead_label.setFont(text_font(Text.DESCRIPTION))
        self.box.addWidget(lead_label)
        self.box.addSpacing(Space.S)
        self.setWidget(body)
        self.end = None

    def group(self, title: str, tiles: list) -> None:
        sec = QLabel(title.upper())
        sec.setObjectName("fpage-section")
        sec.setFont(text_font(Text.LABEL))
        self.box.addSpacing(Space.XL)
        self.box.addWidget(sec)
        self.box.addSpacing(Space.M)
        grid = QGridLayout()
        grid.setSpacing(Layout.GAP)
        self.box.addLayout(grid)
        self._groups.append((grid, tiles, 0))
        self._reflow()

    def _reflow(self) -> None:
        columns = max(1, min(3, (self.viewport().width() - 2 * Layout.PAGE[0]) // 280))
        for index, (grid, tiles, previous) in enumerate(self._groups):
            if columns == previous:
                continue
            while grid.count():
                grid.takeAt(0)
            for col in range(3):
                grid.setColumnStretch(col, int(col < columns))
            for i, tile in enumerate(tiles):
                grid.addWidget(tile, i // columns, i % columns)
            self._groups[index] = (grid, tiles, columns)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._reflow()

    def finish(self) -> None:
        self.box.addStretch(1)


class FilePage(QFrame):
    """The page, a card over the window's panels (the window places it, `place`)."""

    closed = Signal()

    def __init__(self, window):
        super().__init__(window)
        self.host = window
        self.setObjectName("file-page")
        # opaque, drawn whole by paintEvent: Qt then paints nothing of what lies under it, the views and the panels,
        # at its opening (R132: the first frame took 75-115 ms on the 4K screen, all of it hidden under the page)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        from .cards import default_tokens
        self.set_colours(default_tokens())
        row = QHBoxLayout(self)
        row.setContentsMargins(1, 1, 1, 1)
        row.setSpacing(0)
        self.nav = QFrame()
        self.nav.setObjectName("file-nav")
        self.nav.setFixedWidth(NAV_WIDTH)
        self.nav_box = QVBoxLayout(self.nav)
        self.nav_box.setContentsMargins(Space.M, Space.L, Space.M, Space.L)
        self.nav_box.setSpacing(Space.XXS)
        self.nav_scroll = QScrollArea()
        self.nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_scroll.setFixedWidth(NAV_WIDTH + 8)
        self.nav_scroll.setWidget(self.nav)
        row.addWidget(self.nav_scroll)
        self.body = QStackedWidget()
        row.addWidget(self.body, 1)
        self.nav_scopes: list[tuple[QWidget, bool]] = []
        self.items: dict[str, QToolButton] = {}
        self.sections: dict[str, QWidget] = {}
        self.hidden_with_me: list = []              # what stood over the panels (Meridio), back when it closes
        # R178: the shared entrance, with the alternatives kept for the visual comparison
        self.entrance = None
        self.entrance_kind = "slide"
        self.entrance_duration = Motion.NORMAL
        self._build()
        self.hide()
        window.installEventFilter(self)

    def set_colours(self, t: dict) -> None:
        self.colours = (t["window"], t["panel"], t["card_line"])
        self.update()

    def paintEvent(self, event) -> None:
        """The window's ground in the corners, the card with its line: every pixel, as WA_OpaquePaintEvent promises."""
        window, panel, line = self.colours
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(window))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        card = QPainterPath()
        card.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), Radius.CARD, Radius.CARD)
        p.fillPath(card, QColor(panel))
        p.setPen(QPen(QColor(line), 1.0))
        p.drawPath(card)

    def eventFilter(self, obj, event) -> bool:
        if self.isVisible() and event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest):
            QTimer.singleShot(0, self, self.place)          # after the layout pass: the bar above may have gone
        return False

    # the list on the left

    def _item(self, key: str, icon: str, text: str, keys: str = "", slot: Callable | None = None) -> QToolButton:
        b = QToolButton()
        b.setObjectName("file-item")
        b.setIcon(icons.icon(icon))
        b.setIconSize(QSize(Icon.LIST, Icon.LIST))
        b.setFont(text_font(Text.BODY))
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        # an en space after the icon: the sheet's tool button leaves it touching the word (the target: 10 px)
        b.setText("\u2002" + text)
        b.setAccessibleName(text)
        b.setProperty("keys", keys)
        if keys:                                    # the keys at the right end of the item, quiet
            inside = QHBoxLayout(b)
            inside.setContentsMargins(0, 0, Space.M, 0)
            inside.addStretch(1)
            k = QLabel(keys)
            k.setObjectName("file-keys")
            k.setFont(text_font(Text.SECONDARY))
            k.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            inside.addWidget(k)
        b.setCheckable(slot is None)
        b.setAutoRaise(True)
        b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        b.setFixedHeight(Size.NAV)
        if slot is not None:
            b.clicked.connect(slot)
        else:
            b.clicked.connect(lambda _c=False, k=key: self.show_section(k))
        self.nav_box.addWidget(b)
        self.items[key] = b
        self.nav_scopes.append((b, key.startswith("preferences:") or key == "settings_back"))
        return b

    def _rule(self) -> None:
        gap = QWidget()
        box = QVBoxLayout(gap)
        box.setContentsMargins(0, Space.S, 0, Space.S)
        line = QFrame()
        line.setObjectName("file-rule")
        line.setFixedHeight(1)
        box.addWidget(line)
        self.nav_box.addWidget(gap)
        self.nav_scopes.append((gap, False))

    def _nav_mode(self, settings: bool) -> None:
        for widget, is_settings in self.nav_scopes:
            widget.setVisible(is_settings == settings)

    def _command(self, cid: str) -> Callable:
        """A command of the window, started after the page has closed."""
        def run():
            self.close_page()
            self.host.commands[cid].trigger()
        return run

    def _keys(self, cid: str) -> str:
        a = self.host.commands.get(cid)
        return a.shortcut().toString(a.shortcut().SequenceFormat.NativeText) if a is not None else ""

    def _then(self, slot: Callable) -> Callable:
        def run():
            self.close_page()
            slot()
        return run

    def _build(self) -> None:
        w = self.host
        self._item("back", "arrow-left", _("Back to the project"), "Esc", self.close_page)
        self._rule()
        self._item("new", "file-plus", _("New"), self._keys("new"), self._command("new"))
        self._item("open", "folder-open", _("Open"), self._keys("open"))
        self._item("save", "save", _("Save and revisions"))
        self._item("registry", "library", _("Clients and jobs"))
        self._rule()
        self._item("import", "download", _("Import"))
        self._item("export", "upload", _("Export"))
        self._rule()
        self._item("catalogues", "library", _("Catalogues"))
        self._item("preferences", "settings", _("Settings"), self._keys("preferences"))
        self._item("settings_back", "arrow-left", _("Back to File"), slot=lambda: self.show_section("open"))
        for key, icon, title in (
                ("appearance", "eye", _("Appearance")), ("navigation", "select", _("Navigation")),
                ("keyboard", "keyboard", _("Keyboard")), ("assistant", "wand", _("Assistant")),
                ("report", "file-text", _("Report")), ("maps", "map", _("Maps")),
                ("privacy", "info", _("Privacy"))):
            self._item(f"preferences:{key}", icon, title)
        self._item("help", "circle-question-mark", _("Help and manual"), "F1")
        self.nav_box.addStretch(1)
        self._item("quit", "log-out", _("Quit"), self._keys("quit"), self._command("quit"))

        # New: the place first, with only local suggestions while typing
        from .new_project import NewProjectPage
        self.new_project = NewProjectPage(w.paths, w.cfg, registry=w.registry)
        self.new_project.created.connect(w._create_new)
        self.sections["new"] = self.new_project

        from .registry_page import RegistryPage
        self.registry_page = RegistryPage(w.registry, w)
        self.registry_page.changed.connect(w._refresh_index)
        self.sections["registry"] = self.registry_page

        # Open: the file, and the projects opened last
        opening = Section(_("Open"), _("A Meridiana project from a file, or one of the last ones."))
        opening.group(_("Project"), [Tile("folder-open", _("A project"), _("A .mer file with the project and its resources."),
                                          (".mer",), _("Choose the file…"), self._command("open"))])
        self.recent_box = QVBoxLayout()
        self.recent_box.setSpacing(0)
        sec = QLabel(_("Opened recently").upper())
        sec.setObjectName("fpage-section")
        sec.setFont(text_font(Text.LABEL))
        opening.box.addSpacing(Space.XL)
        opening.box.addWidget(sec)
        opening.box.addSpacing(Space.S)
        opening.box.addLayout(self.recent_box)
        opening.finish()
        self.sections["open"] = opening

        saving = Section(_("Save and revisions"), _("Keep the current project, create a copy or preserve a revision."))
        saving.group(_("Project"), [
            Tile("save", _("Save"), _("Update the current project file."), (), _("Save"), self._command("save")),
            Tile("copy-plus", _("Save as"), _("Choose another name or location for the project."), (".mer",),
                 _("Save as…"), self._command("save_as")),
            Tile("copy-plus", _("Save a revision"), _("Keep this version in a new numbered file next to the project."),
                 ("_R01", "_R02"), _("Save a revision"), self._command("save_revision"))])
        saving.finish()
        self.sections["save"] = saving

        # Import: what comes from other programs or from a file
        imports = Section(_("Import"), _("What comes from other programs or from a file. Meridiana reads it, tells "
                                         "you what it took and what it approximated, and you can undo it."))
        imports.group(_("Project"), [
            Tile("folder-open", _("PVsyst project"), _("The project and the variants next to it, as a new project: "
                                                       "Meridiana says what it approximated."), (".PRJ",),
                 _("Choose the file…"), self._command("import_pvsyst")),
            Tile("building", _("IFC model"), _("The buildings of an architect's model: outlines, roof planes, heights "
                                               "and what stands on the roofs."), (".ifc", ".ifczip"), _("Choose the file…"),
                 self._command("import_ifc")),
            Tile("image", _("Image under the drawing"), _("A site plan or an aerial photo, to scale on the plan."),
                 ("PNG", "JPEG", "PDF"), _("Choose the file…"), self._then(lambda: w._import_image())),
            Tile("cloud-download", _("Typical year and horizon"), _("From the European service PVGIS for the "
                                                                   "project's site; then they stay in the cache."),
                 ("PVGIS",), _("Fetch"), self._command("fetch_pvgis"))])
        imports.group(_("Catalogues and consumption"), [
            Tile("subfield", _("Module from PVsyst"), _("Into the modules' catalogue, with the parameters of the "
                                                        "one-diode model."), (".PAN",), _("Choose the file…"),
                 self._then(lambda: w._import_pvsyst("module"))),
            Tile("zap", _("Inverter from PVsyst"), _("Into the inverters' catalogue, with its efficiency curve."),
                 (".OND",), _("Choose the file…"), self._then(lambda: w._import_pvsyst("inverter"))),
            Tile("file-input", _("Load curve"), _("The consumption measured every 15 minutes or every hour, in "
                                                  "place of the profile."), ("CSV",), _("Choose the file…"),
                 self._command("import_curve"))])
        imports.finish()
        self.sections["import"] = imports

        # Export: what goes out of the project
        exports = Section(_("Export"), _("What leaves the project for the client, the authorities or a colleague."))
        exports.group(_("Documents"), [
            Tile("file-text", _("Report"), _("Production, strings, consumption and economics with every "
                                             "calculation."), ("PDF",), _("Export…"), self._command("export_report")),
            Tile("clipboard-copy", _("Notes for the report"), _("The paragraphs of the rules that apply, with their "
                                                                "sources, to paste into the technical report."),
                 (_("text"),), _("Copy"), self._command("copy_notes")),
            Tile("copy-plus", _("A revision"), _("A new file next to this one, with the suffix _R01, _R02...: the "
                                                 "previous one stays as it was."), (".mer",), _("Save"),
                 self._command("save_revision"))])
        exports.group(_("Models"), [
            Tile("export_ifc", _("IFC4 model"), _("Buildings, roofs, obstacles and every module with its string, "
                                                  "georeferenced: for the architect, the BIM coordinator, FreeCAD."),
                 (".ifc",), _("Export…"), self._command("export_ifc"))])
        exports.finish()
        self.sections["export"] = exports

        # Catalogues: modules, inverters, batteries
        from .catalog_dialog import CatalogDialog, kind_titles
        cats = Section(_("Catalogues"), _("The modules, the inverters and the batteries Meridiana knows, with their "
                                          "data sheets: look, filter, add your own."))
        what = {"module": ("subfield", _("Every module with its electrical data and its origin.")),
                "inverter": ("zap", _("Every inverter with its inputs, its window and its efficiency.")),
                "battery": ("battery-charging", _("The storage systems with their capacity and power."))}
        tiles = []
        for kind, title in kind_titles().items():
            icon, text = what.get(kind, ("library", ""))
            tiles.append(Tile(icon, title, text, (), _("Open…"),
                              self._then(lambda k=kind: CatalogDialog(k, w, browse=True).exec())))
        cats.group(_("Catalogues"), tiles)
        cats.finish()
        self.sections["catalogues"] = cats

        # Settings: the former dialog's pages, applied immediately and undoable while this page stays alive.
        from .preferences import Preferences
        settings = Section(_("Settings"), _("Every choice applies and is saved at once. Undo the last change or "
                                             "restore the defaults of one section."))
        self.settings = Preferences(w.cfg, w.bindings, w.theme, w)
        self.settings.changed.connect(w._apply_preferences)
        settings.box.addSpacing(Space.XL)
        self.settings.setMaximumWidth(860)
        settings.box.addWidget(self.settings, 1, Qt.AlignmentFlag.AlignLeft)
        self.sections["preferences"] = settings

        # Help
        helps = Section(_("Help and manual"), _("How Meridiana works and how it computes, inside the program."))
        helps.group(_("Help"), [
            Tile("book-open", _("Manual"), _("The manual, at the chapter of the phase open."), (), _("Open"),
                 self._command("manual")),
            Tile("keyboard", _("Keyboard shortcuts"), _("Every key of the window, with a search; change them in the "
                                                        "same place."), (), _("Open"), self._command("shortcuts")),
            Tile("info", _("About Meridiana"), _("The version, the licences, the data and where they come from."),
                 (), _("Open"), self._command("about"))])
        helps.finish()
        self.sections["help"] = helps

        for section in self.sections.values():
            self.body.addWidget(section)

    # showing

    def show_section(self, key: str) -> None:
        section, _, page = key.partition(":")
        if section not in self.sections:
            return
        self._nav_mode(section == "preferences")
        if key == "open":
            self._recent()
        elif key == "new":
            from .. import places
            self.new_project.reset()
            self.new_project.set_choices([*places.municipalities(), *places.recent(self.host.cfg.recent)])
        elif key == "registry":
            self.registry_page.refresh()
        elif section == "preferences":
            if self.body.currentWidget() is not self.sections["preferences"]:
                self.settings._populate()          # read the site on entering, not on every category change
            self.settings.show_page(page)
            page = self.settings.current_section()
            key = "preferences:" + page
        self.body.setCurrentWidget(self.sections[section])
        for k, b in self.items.items():
            if b.isCheckable():
                b.setChecked(k == key or (k == section and not page))

    def _recent(self) -> None:
        """The projects opened last, newest first, those still there."""
        while self.recent_box.count():
            item = self.recent_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        paths = [p for p in getattr(self.host.cfg, "recent", []) if isinstance(p, str) and p and Path(p).exists()]
        if not paths:
            none = QLabel(_("No project opened yet."))
            none.setObjectName("fpage-lead")
            self.recent_box.addWidget(none)
            return
        for p in paths:
            # the name and, quiet beside it, the folder, from the left as a list reads (a tool button centred them)
            b = QToolButton()
            b.setObjectName("recent-item")
            b.setAccessibleName(f"{Path(p).stem} {Path(p).parent}")
            b.setToolTip(p)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setFixedHeight(Size.NAV)
            b.setAutoRaise(True)
            inside = QHBoxLayout(b)
            inside.setContentsMargins(Space.M, 0, Space.M, 0)
            inside.setSpacing(Space.L)
            for text, style in ((Path(p).stem, Text.BODY), (str(Path(p).parent), Text.SECONDARY)):
                label = QLabel(text)
                label.setFont(text_font(style))
                label.setObjectName("recent-folder" if style is Text.SECONDARY else "recent-name")
                label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                inside.addWidget(label)
            inside.addStretch(1)
            b.clicked.connect(lambda _c=False, path=p: self._open_recent(path))
            self.recent_box.addWidget(b)

    def _open_recent(self, path: str) -> None:
        self.close_page()
        self.host.open_path(Path(path))

    def open_page(self, section: str = "open") -> None:
        self.place()
        self.show_section(section)
        assistant = getattr(self.host, "assistant", None)
        if assistant is not None and assistant.isVisible() and assistant.parentWidget() is self.host:
            assistant.hide()
            self.hidden_with_me = [assistant]
        from . import motion

        def present():
            self.show()
            self.raise_()
            current = next((item for item in self.items.values() if item.isChecked() and item.isVisible()), None)
            if current is not None:
                current.setFocus()

        self.entrance = motion.enter(self, present, self.entrance_kind, self.entrance_duration)
        if self.entrance is not None:
            self.entrance.animation.finished.connect(self._entered)
        QTimer.singleShot(0, self, self.place)

    def _entered(self) -> None:
        self.entrance = None

    def close_page(self) -> None:
        if self.isVisible():
            if self.entrance is not None:
                self.entrance.animation.stop()
                self.entrance.hide()
                self.entrance.deleteLater()
                self.entrance = None
            self.hide()
            for w in self.hidden_with_me:
                w.show()
            self.hidden_with_me = []
            self.closed.emit()

    def place(self) -> None:
        """Over the panels and the page of the phase: the window's arena, as far from its edges as the cards."""
        from .cards import EDGE, GAP, arena
        a = arena(self.host)
        self.setGeometry(a.adjusted(EDGE, GAP, -EDGE, -GAP))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_page()
            return
        super().keyPressEvent(event)
