"""The main window: the project on the left, the plan and the 3D view in the middle, the properties of
what is selected on the right, the hints and the measures at the bottom. Beside the model, three pages:
production, consumption, balance and economics, computed by the energy job in a thread.

The work in hand is the session's (session.py, without Qt): every change goes through `session.edit`, a
snapshot of the project before and after on the undo stack, and the session says by topic what changed;
each view follows its topics (`_session_changed`). The layout of the sub-fields that changed and the energy
year run in threads and come back as results of the session. The views never decide anything: they draw the
project and report gestures.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from PySide6.QtCore import (QByteArray, QEvent, QObject, QPoint, QPointF, QRect, QRunnable, QSize, Qt, QThreadPool, QTimer,
                            Signal)
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (QApplication, QDialog, QDockWidget, QFileDialog, QHBoxLayout, QInputDialog,
                               QLabel, QMainWindow, QMenu, QMenuBar, QMessageBox, QSizePolicy, QSplitter, QTabBar,
                               QToolBar,
                               QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWhatsThis, QWidget)
from shapely.geometry import Polygon

from .. import assistant as assistant_core
from .. import (atomic, camera, catalog, checks, config, jobs, log, manual, mesh, model, move, phases, recovery, rules,
               shortcuts, sides, roofs, squaring, templates, theme_colors, tiles, underlay, view_colours, viewaids)
from ..energy import consumption as consumption_model
from ..energy import pipeline, system
from ..energy import plant as plant_model
from ..i18n import _, ngettext, number
from ..paths import Paths
from ..session import ProjectSession, set_path
from ..session import needs_layout as session_needs_layout
from . import charts, icons, tell, wheel
from .undo import UndoBridge
from .assistant import Assistant
from .assistant_chat import Chat, WindowHost
from .cards import CardDock, keep_gaps
from .design import Icon, Space, Text, set_text_all
from .sections import TAIL_ROLE, SectionDelegate, section
from .catalog_dialog import CatalogDialog
from .energy_pages import ConsumptionPage, EconomicsPage, EnergyPage
from .inspector import Inspector
from .marks import icon as mark_icon
from .report_page import ReportPage, ReportSide
from .phasebar import LOW_WINDOW, PhaseBar, Phases
from .plan import MOVABLE, PlanView
from .plant_page import PlantInspector, PlantPage, input_name, install_reference, legend_html
from .properties import Properties, field_label
from .checks_page import ChecksPage
from .sunbar import SunBar
from .theme import SystemAccent, Theme
from .view3d import View3D
from . import underlays
from .viewbar import ViewBar
from . import waiting
from .waiting import STALE_MARK

SUFFIX = ".meridiana"
# below this width (logical pixels: a column of niri, half a laptop screen) the panels share one side
NARROW = 1000
# the topics that never change the energy year (session.energy_key): no need to ask whether it is still good
NO_YEAR = {"project:text", "project:rules", "project:underlays", "project:report"}


class LayoutSignals(QObject):
    done = Signal(int, dict, float, dict)


class LayoutJob(QRunnable):
    """The layouts of the filled sub-fields, away from the window's thread. A sub-field whose inputs are those
    of a layout in hand (`known`: id -> (key, result)) keeps that result: a change lays out again only what
    it touched (study 15, 3.6)."""

    def __init__(self, generation: int, project: model.Project, known: dict | None = None):
        super().__init__()
        self.generation, self.project, self.known = generation, project, known or {}
        self.signals = LayoutSignals()
        self.laid: list = []                     # the sub-fields laid out this time, for the tests

    def run(self):
        t = time.perf_counter()
        results, keys, self.laid = jobs.layout_of(self.project, self.known)
        tell(self.signals.done, self.generation, results, time.perf_counter() - t, keys)


AUTOSAVE_MS = 120_000           # a copy of the unsaved changes every two minutes
ENERGY_PAUSE_MS = 500
RELAYOUT_PAUSE_MS = 150
PREVIEW_REPORT_MS = 700
WARM_UP_MS = 1500


class EnergySignals(QObject):
    done = Signal(int, object)
    step = Signal(int, int, int, str)          # generation, steps done, steps (pipeline.STEPS), what comes now


class EnergyJob(QRunnable):
    """Production, consumption, balance and economics of the project (energy/pipeline.py), away from the
    window's thread. The network is used only when the designer asked (fetch): otherwise only what is in the
    cache. Each step is told (`step`, the bar of PVGIS); `interrupt` (Cancel) stops it before the next one, so
    between two requests to PVGIS. A flag of the job and not QThread.requestInterruption: the pool's threads
    live on, and the request would stay on the thread for the next job."""

    def __init__(self, generation: int, snapshot: dict, results: dict, cache: Path, fetch: bool):
        super().__init__()
        self.generation, self.snapshot, self.results, self.cache, self.fetch = generation, snapshot, results, cache, fetch
        self.signals = EnergySignals()
        self.interrupted = False

    def interrupt(self) -> None:
        self.interrupted = True

    def _progress(self, done: int, total: int, what: str) -> None:
        if self.interrupted:
            raise pipeline.Interrupted()
        tell(self.signals.step, self.generation, done, total, what)

    def run(self):
        p = model.Project.from_json(self.snapshot, check=False)
        try:
            out = pipeline.compute_or_say(p, self.results, self.cache, self.fetch, self._progress)
        except pipeline.Interrupted:
            return                          # stopped by the designer: the window awaits this year no longer
        tell(self.signals.done, self.generation, out.as_dict())


def _pvlib_loaded() -> bool:
    """Whether pvlib's MPP function is loaded whole. Its name in sys.modules is not enough: while the year's job loads
    pvlib in its thread (a second and a half) the name is there already, and the strings laid here, in the window's
    thread, waited for the rest of the import: the window stood still 1.5 s at every project opened (R120)."""
    import sys
    for name in ("pvlib", "pvlib.pvsystem"):            # the package too: its submodule's import waits for it
        module = sys.modules.get(name)
        if module is None or getattr(getattr(module, "__spec__", None), "_initializing", False):
            return False
    return hasattr(sys.modules["pvlib.pvsystem"], "max_power_point")


class PlantJob(QRunnable):
    """The plant of the project (energy/plant.build): the strings on the modules laid and their checks, away from the
    window's thread (the first check loads the module's model: most of a second, once). A few milliseconds after
    each change of the strings: the live checks of task 16d, at the conditions of the last year computed (its hottest
    cell, its DC power for the overload) or at PVsyst's design ones before."""

    def __init__(self, generation: int, snapshot: dict, results: dict, year: tuple | None):
        super().__init__()
        self.generation, self.snapshot, self.results, self.year = generation, snapshot, results, year
        self.signals = EnergySignals()
        self.seconds = 0.0

    def run(self):
        t = time.perf_counter()
        try:
            p = model.Project.from_json(self.snapshot, check=False)
            t_cell, p_dc = self.year if self.year is not None else (None, None)
            out = plant_model.build(p, self.results, t_cell_max_year=t_cell, p_dc_hourly=p_dc)
        except Exception as error:      # noqa: BLE001  a thread's boundary: said, not lost
            log.complain("plant", error)
            out = error
        self.seconds = time.perf_counter() - t
        tell(self.signals.done, self.generation, out)


class IfcSignals(QObject):
    step = Signal(float, str)
    done = Signal(object)


class ExportIfcJob(QRunnable):
    """The project written as IFC4 (ifc_export.py) away from the window's thread: the layouts in hand (those missing laid
    here), the strings proposed or the designer's, then the file. Each step is told (the bar); `interrupt` (Cancel)
    stops it at the next one, and nothing is written."""

    def __init__(self, snapshot: dict, known: dict, path: Path, state: str = ""):
        super().__init__()
        self.snapshot, self.known, self.path, self.state = snapshot, known, path, state
        self.signals = IfcSignals()
        self.interrupted = False

    def interrupt(self) -> None:
        self.interrupted = True

    def _step(self, fraction: float, what: str) -> None:
        from .. import ifc_export
        if self.interrupted:
            raise ifc_export.Interrupted()
        tell(self.signals.step, fraction, what)

    def run(self):
        from .. import ifc_export
        try:
            p = model.Project.from_json(self.snapshot, check=False)
            results, _keys, _laid = jobs.layout_of(p, self.known)
            try:
                plant = plant_model.build(p, results, check=False)
                strings = {(sf, key): s.label for s in plant.strings for sf, key, _c in s.modules}
            except Exception as error:      # noqa: BLE001  the strings are a property: the model goes without them
                log.complain("ifc strings", error)
                strings = {}
            out = ifc_export.export(p, results, self.path, strings=strings, progress=self._step)
        except ifc_export.Interrupted:
            out = None
        except Exception as error:          # noqa: BLE001  a thread's boundary: said, not lost
            if not isinstance(error, OSError):
                log.complain("ifc export", error)
            out = error
        tell(self.signals.done, out)


def _session_attr(name: str) -> property:
    """An attribute of the window that lives in its session (project, results, selection...): the window's
    code and the tests read and write it where they always did."""
    return property(lambda self: getattr(self.session, name), lambda self, value: setattr(self.session, name, value))


class MainWindow(QMainWindow):
    # the truth of the work in hand is the session's (session.py); these names stay as the window's
    project = _session_attr("project")
    path = _session_attr("path")
    results = _session_attr("results")
    layout_keys = _session_attr("layout_keys")
    energy = _session_attr("energy")
    generation = _session_attr("generation")
    energy_generation = _session_attr("energy_generation")
    selection = _session_attr("selection")
    selected_module = _session_attr("selected_module")
    saved_state = _session_attr("saved_state")

    def __init__(self, paths: Paths, cfg: config.Config):
        super().__init__()
        self.paths, self.cfg = paths, cfg
        self.session = ProjectSession()
        self.session.subscribe(self._session_changed)
        self.module_index: list = []           # (sub-field id, module key) per row of the 3D table
        self.module_tables: dict = {}          # sub-field id -> its 3D table of the layout in hand (_show_3d)
        self.row_cache: tuple = (None, None)   # ((row, layout), outline and end) of the row the plan asked last
        self.hovered_3d = ("", "", "")         # what a click in 3D would select: kind, id, module key
        self.undo = UndoBridge(self.session.undo, self)
        self.undo.cleanChanged.connect(self._clean_changed)
        self.pool = QThreadPool.globalInstance()
        wheel.guard()                       # the wheel scrolls the forms; a field changes only with the keyboard
        self.theme = Theme(cfg, self)        # Fusion, the palette of the colour chosen, the font (study 13)

        self.plan = PlanView(paths.cache, self)
        self.view3d = View3D(self)
        # until the 3D view's first frame (about 1 s on Daniel's PC), its skeleton over it (study 16, F2)
        self.skeleton: waiting.Skeleton3D | None = waiting.Skeleton3D(self.view3d)
        self.skeleton.gone.connect(self._skeleton_gone)
        self.sunbar = SunBar(self)
        self.view3d_box = QWidget()
        box3d = QVBoxLayout(self.view3d_box)
        box3d.setContentsMargins(0, 0, 0, 0)
        box3d.setSpacing(0)
        box3d.addWidget(self.view3d, 1)
        box3d.addWidget(self.sunbar)
        self.split = QSplitter(Qt.Orientation.Horizontal)
        self.split.setHandleWidth(Space.S)          # the card between the two views, each rounded (24/10/2026)
        self.split.addWidget(self.plan)
        self.split.addWidget(self.view3d_box)
        self.energy_page = EnergyPage()
        self.consumption_page = ConsumptionPage()
        self.economics_page = EconomicsPage()
        # the row of the phases (phases.py; study 17, B4): the pages of today at their places, the Plant and the
        # Report after the actions (_build_phases), the bar of each phase under the row
        self.tabs = Phases()
        for pid, page in (("model", self.split), ("production", self.energy_page),
                          ("consumption", self.consumption_page), ("economics", self.economics_page)):
            self.tabs.add_phase(phases.by_id(pid), page)
        self.exports: dict = {}                    # deliverable id -> (file, when, the project's state key then)
        self.stale_shown = False                   # the year's values shown as to update (_show_stale)
        self.checks_page = ChecksPage(view=cfg.checks_view)
        self.checks_page.navigate.connect(self._navigate)
        self.checks_page.focusRequested.connect(self._focus_check)
        self.checks_page.fix.connect(self._fix)
        self.checks_page.previewAnswered.connect(self._fix_answered)
        self.fix_preview = None                     # the step of a fix shown and not yet kept (R126)
        self.fix_waiting = None                     # the check whose fix waits for Apply (not an edit)
        self.session.undo.listeners.append(self._undo_moved)
        self.checks_page.viewChanged.connect(self._checks_view_changed)
        self.checks_page.notes_text = self._report_notes
        self.setCentralWidget(self.tabs)
        self.gaps = keep_gaps(self.tabs)           # from the window's edges as the cards of the panels (A3)
        # the row of the phases and the card of the bar across the window, above the panels (the target of
        # 24/10/2026, docs/studio/19-grafica): the menu widget holds the menu bar and the phases' header
        self._menu_bar = QMenuBar()
        top = QWidget()
        top.setObjectName("top-area")
        top_box = QVBoxLayout(top)
        top_box.setContentsMargins(0, 0, 0, 0)
        top_box.setSpacing(0)
        top_box.addWidget(self._menu_bar)
        top_box.addWidget(self.tabs.header)
        self.top_box = top_box                     # the menu bar's place when it is always shown (ui/menubar.py)
        self.setMenuWidget(top)
        # the right column the whole height (Properties and Help), the checks under the tree and the views
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        # one assistant for the window, floating over the central area: the phases move it, never make it again
        # free over the whole window, between the phases' header and the status bar (Daniel, 24/10/2026: «Meridio
        # non è possibile spostarlo sulle schede che non sono quella centrale»); his first place on the views
        self.assistant = Assistant(self)
        self.assistant.reserved = self._assistant_reserved
        self.assistant.top = self._assistant_top
        self.assistant.bottom = lambda: self.statusBar().height() if self.statusBar().isVisible() else 0
        self.assistant.home = self._assistant_home
        self.assistant.follow(self.sunbar)
        self.assistant.follow(self.tabs)          # the card in the middle moves when the panels change
        self.assistant.follow(self.tabs.pages)    # the page moves when the bar changes height or the gaps settle
        self.assistant.avoid = self._assistant_avoid        # the bubble keeps off the selection on the plan (R33)
        self.assistant.set_animated(cfg.assistant_animated)
        self.assistant.set_style(cfg.assistant_style)
        self.assistant.set_bubble_size(cfg.assistant_width, cfg.assistant_height)
        self.assistant.bubbleResized.connect(self._assistant_resized)
        self.tabs.currentChanged.connect(self._tab_changed)
        for page in (self.energy_page, self.consumption_page, self.economics_page):
            page.edited.connect(self._energy_edited)
            page.computeRequested.connect(lambda: self._compute_energy(fetch=True))
        self.energy_page.fetchRequested.connect(lambda: self._compute_energy(fetch=True))
        self.energy_page.inverterRequested.connect(self._choose_inverter)
        self.economics_page.batteryRequested.connect(self._choose_battery)
        self.consumption_page.importRequested.connect(self._import_curve)
        self.autosave_timer = QTimer(self, interval=AUTOSAVE_MS)
        self.autosave_timer.timeout.connect(self._autosave)
        self.autosave_timer.start()
        self.energy_timer = QTimer(self, singleShot=True, interval=ENERGY_PAUSE_MS)
        self.energy_timer.timeout.connect(lambda: self._compute_energy(fetch=False))
        # the plant (task 16d): the strings and their checks again at each change, in a thread (_start_plant)
        self.plant_state = None                    # energy/plant.Plant of the project in hand
        self.plant_generation = 0
        self.plant_returned = 0                     # the generation of the last plant back (plant_pending)
        self.plant_job = None
        self.plant_timer = QTimer(self, singleShot=True, interval=0)
        self.plant_timer.timeout.connect(self._start_plant)
        self.split_home = None                      # the split's state while the Plant phase has the plan
        self.chosen_string = -1                     # the string chosen in the list or on the plan (Plant.strings)
        self.draft_target = None                    # {"unit", "mppt", "run"} of the string being drawn (R114)

        self.tree = QTreeWidget()
        self.tree.setObjectName("project-tree")
        self.tree.setHeaderHidden(True)
        # T2 (the target of 24/10/2026): the sections always open, no arrows and no indent
        self.tree.setIndentation(0)
        self.tree.setRootIsDecorated(False)
        self.tree.setItemsExpandable(False)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setMouseTracking(True)
        self.tree.setColumnCount(2)                 # the name, and the mark of the checks
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeMode.Stretch)
        self.tree.itemClicked.connect(self._tree_clicked)
        from .marks import MarkDelegate
        self.tree.setItemDelegateForColumn(0, SectionDelegate(self.tree, pills=True))   # the sections (T2)
        self.tree.setItemDelegateForColumn(1, MarkDelegate(self.tree))
        # the column of the marks as wide as a mark with a two-figure number: fixed, not measured again at every
        # setData (ResizeToContents asked 31.793 size hints for 124 rows at each redraw, study 18, A 7.2)
        self.tree.header().setSectionResizeMode(1, self.tree.header().ResizeMode.Fixed)
        self.tree.header().resizeSection(1, MarkDelegate.column_width(self.tree.fontMetrics()))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        left = CardDock(_("Project"), self)        # the panels as cards (study 17, A3; ui/cards.py)
        left.setObjectName("project")
        left.setWidget(self.tree)
        left.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left)
        self.props = Properties()
        self.props.edited.connect(self._edited)
        self.props.action.connect(self._action)
        right = CardDock(_("Properties"), self)
        right.setObjectName("properties")
        self.inspector = Inspector(self.props)     # the properties on the model, the figures on the results
        self.inspector.results.variantChosen.connect(self._switch_variant)
        for pid, page in (("production", self.energy_page), ("consumption", self.consumption_page),
                          ("economics", self.economics_page)):
            self.inspector.add_side(pid, page.side)
        right.setWidget(self.inspector)
        right.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right)
        self.docks = (left, right)
        self.project_auto_hidden = False
        self.project_was_visible = True
        # the help, a card of its own under the properties (design 3.6, E3; Daniel, 24/10/2026; ui/help_box.py)
        from .help_box import HelpBox
        self.help_box = HelpBox()
        self.help_dock = CardDock(_("Help"), self)
        self.help_dock.setObjectName("help")
        self.help_dock.setWidget(self.help_box)
        self.help_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                   QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.help_dock)
        self.splitDockWidget(right, self.help_dock, Qt.Orientation.Vertical)
        # the checks, below the views in every tab as VS Code's problems (Ctrl+J), no longer a tab of their own
        self.checks_dock = CardDock(_("Checks"), self)
        self.checks_dock.setObjectName("checks")
        self.checks_dock.setWidget(self.checks_page)
        self.checks_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                     QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.checks_dock)
        # the assistant docked in the panels when the designer wants it there (R17): the same conversation
        self.assistant_dock = CardDock(assistant_core.NAME, self)
        self.assistant_dock.setObjectName("assistant_dock")
        self.assistant_dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                                        QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.assistant_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea |
                                            Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.assistant_dock)
        self.assistant_dock.hide()
        self.assistant.set_dock(self.assistant_dock)
        self.assistant.set_docked(cfg.assistant_docked)
        self.assistant.dockRequested.connect(self._dock_assistant)

        self.hint = QLabel()
        self.coords = QLabel()
        self.busy = QLabel()                   # what is being computed in the background, while it is
        self.busy_wait = waiting.Delayed(self.busy, self)      # past the threshold only (study 16, F.6)
        # margins as the rest of the window (R14): from the window's sides and between what the bar says
        self.statusBar().setContentsMargins(Space.M, Space.XXS, Space.M, Space.XXS)
        self.statusBar().addWidget(self.hint, 1)
        self.measure_label = QLabel()          # the quick measure of the selection (study 15, 3.11)
        # what the status bar says never keeps the window from getting narrower (a column of niri): cut, not wider
        for label in (self.hint, self.coords, self.measure_label):
            label.setMinimumWidth(1)
            label.setContentsMargins(Space.S, 0, Space.S, 0)
            label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.statusBar().addPermanentWidget(self.busy)
        # the bars with their percentage and Cancel, only for PVGIS and the PDF report (study 16, F4; design 3.10)
        self.pvgis_progress = waiting.Progress()
        self.pvgis_progress.cancelled.connect(self._cancel_pvgis)
        self.report_progress = waiting.Progress()
        self.report_progress.cancelled.connect(self._cancel_report)
        # the IFC model read in its process, or written in a job (study 20): one at a time
        self.ifc_progress = waiting.Progress()
        self.ifc_progress.cancelled.connect(self._cancel_ifc)
        self.ifc_reading = None                # ui.ifc_import.IfcReading while a model is read
        self.ifc_job = None                    # ExportIfcJob while a model is written
        for progress in (self.pvgis_progress, self.report_progress, self.ifc_progress):
            self.statusBar().addPermanentWidget(progress)
        self.energy_job: EnergyJob | None = None
        self.report_run = None                 # (the report's steps, its file, the project's state key then)
        self.report_register = False           # the register of the calculations goes with the report being made
        self.preview_run = None                # (the preview's steps, its pages, its key) while it is made
        self.preview_key = None                # what the pages shown were made of
        self.preview_soon = QTimer(self)       # a pause after the last change before the preview is made again
        self.preview_soon.setSingleShot(True)
        self.preview_soon.setInterval(PREVIEW_REPORT_MS)
        self.preview_soon.timeout.connect(self._preview_report)
        self.count_buttons = {}                # how many checks to fix and to check, a click away (study 12, C3)
        for level in ("fail", "warn"):
            b = QToolButton()
            b.setAutoRaise(True)
            b.clicked.connect(lambda _c=False, lv=level: self._show_level(lv))
            b.hide()
            self.statusBar().addPermanentWidget(b)
            self.count_buttons[level] = b
        self.statusBar().addPermanentWidget(self.measure_label)
        self.statusBar().addPermanentWidget(self.coords)
        self.panel_slot = QWidget()                # the cards' buttons (R72), made once the actions are there
        QVBoxLayout(self.panel_slot).setContentsMargins(0, 0, 0, 0)
        self.statusBar().addPermanentWidget(self.panel_slot)
        self.assistant_button = QToolButton()      # the character small, its name: opens and closes it
        self.assistant_button.setAutoRaise(True)
        self.assistant_button.setCheckable(True)
        self.assistant_button.setText(assistant_core.NAME)
        self.assistant_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.assistant_button.setToolTip(_("The assistant (Ctrl+L): not connected yet"))
        self.assistant_button.clicked.connect(lambda _c=False: self.assistant.toggle())
        self.assistant.openedChanged.connect(self.assistant_button.setChecked)
        self.statusBar().addPermanentWidget(self.assistant_button)
        self._told_error = False
        self._tile_told = 0.0
        self.plan.loader.tileFailed.connect(self._tile_failed)
        self.plan.loader.offline = not cfg.network_tiles

        self.plan.polygonDrawn.connect(self._drawn)
        self.plan.wholePicked.connect(self._whole_pitch)
        self.plan.picked.connect(self._picked)
        self.plan.edgePicked.connect(self._edge_picked)
        self.plan.sideClicked.connect(self._side_clicked)
        self.plan.vertexMoved.connect(self._vertex_moved)
        self.plan.transformRequested.connect(self._transform)
        self.plan.toolLeft.connect(lambda: self._set_tool("select"))
        self.plan.moveModeChanged.connect(self._move_mode)
        self.plan.moduleClicked.connect(self._module_clicked)
        self.plan.markClicked.connect(self._mark_clicked)
        self.plan.pointsPicked.connect(self._points_picked)
        self.plan.stringPicked.connect(self._string_picked)
        self.plan.stringRedraw.connect(self._string_redraw_at)
        self.plan.stringEscape.connect(lambda: self._choose_string(-1))
        self.plan.stringMenu.connect(self._string_menu)
        self.plan.draftChanged.connect(self._draft_changed)
        self.plan.draftFinished.connect(self._draft_finished)
        self.plan.draftCancelled.connect(self._draft_cancelled)
        self.plan.menuRequested.connect(self._plan_menu)
        self.view3d.backend.menuRequested.connect(self._view3d_menu)
        self.plan.deleteRequested.connect(self._delete_key)
        self.plan.hint.connect(self.hint.setText)
        self.plan.cursorInfo.connect(self.coords.setText)
        # the layout by hand (task 16c)
        self.plan.rowDrawn.connect(self._row_drawn)
        self.plan.rowResized.connect(self._row_resized)
        self.plan.moduleDoubleClicked.connect(self._module_double_clicked)
        self.plan.row_preview = self._row_preview
        self.plan.row_info = self._row_info
        self.view3d.set_navigation(cfg.navigation, cfg.orbit, cfg.pivot, cfg.pivot_hint)
        system = SystemAccent.of(QApplication.instance())
        self.view3d.backend.reduced_motion = system.reduced_motion       # no animation when asked for less motion
        self.assistant.reduced_motion = system.reduced_motion
        system.motion.connect(self._motion)
        self.plan.set_navigation(cfg.navigation)
        self.view3d.modulePicked.connect(self._module_picked_3d)
        self.view3d.pointPicked.connect(self._point_picked_3d)
        self.view3d.hoverPicked.connect(self._hover_3d)
        # Move in the 3D view (task 16b): the gizmo dragged, the values typed next to it, the arrows, Esc
        self.view3d.backend.gizmoDone.connect(self._gizmo_done)
        self.view3d.gizmoTyped.connect(self._gizmo_typed)
        self.view3d.nudged.connect(self._gizmo_nudged)
        self.view3d.escaped.connect(self._escape_3d)
        self.sunbar.sunChanged.connect(self.view3d.set_sun)
        self.view3d.failed.connect(lambda why: self.hint.setText(
            _("The 3D view could not start ({why}); the plan works as usual.").format(why=why)))

        self._actions()
        from .panel_buttons import PanelButtons
        self.panel_buttons = PanelButtons([(self.docks[0], "panel-left", self.commands["panel_project"]),
                                           (self.checks_dock, "panel-bottom", self.commands["panel_checks"]),
                                           (self.docks[1], "panel-right", self.commands["panel_properties"]),
                                           (self.help_dock, "circle-question-mark", self.commands["panel_help"])])
        self.panel_slot.layout().addWidget(self.panel_buttons)
        set_text_all(self.statusBar(), Text.SECONDARY)     # its words and buttons the catalogue's secondary (R121)
        # the File page and the menu bar hidden until Alt (R40, R53; Daniel's choice of 24/10/2026)
        from .file_page import FilePage
        from .menubar import AltMenus
        self.file_page = FilePage(self)
        self.file_page.closed.connect(self._file_page_closed)
        self.tabs.header.file_button.clicked.connect(lambda _c=False: self.open_file_page())
        self.tabs.tabBar().tabBarClicked.connect(lambda _i: self.file_page.close_page())
        self.bars_before_file = False
        self.alt_menus = AltMenus(self, self._menu_bar, self.top_box)
        self.alt_menus.set_always(cfg.menu_bar)
        self.menu_bar_action.setChecked(cfg.menu_bar)
        from .style import quiet_menus
        quiet_menus(self._menu_bar)
        self._build_phases()
        from .style import pad_fields
        pad_fields(self)                        # the fields made once (pages, panels, sun bar): text off the edge
        self.help_box.attach(self)              # the help next to things: the phases, the keyboard (task 17d)
        # the steps of the gesture in hand, after each click and key on the plan (R43)
        self.guide_at = ("", -1)
        for w in (self.plan, self.plan.viewport()):
            w.installEventFilter(self)
        self.theme.changed.connect(self._theme_changed)
        self._theme_changed()                   # the palette is already there (Theme applies it at once)
        self.plan.set_veil(cfg.veil)
        self.plan.set_sources(cfg.map_sources)
        self.plan.set_source(cfg.background)
        self._fill_sources()
        # the layout starts after a short pause: a field's arrows clicked again and again lay the modules once
        self.relayout_timer = QTimer(self, singleShot=True, interval=RELAYOUT_PAUSE_MS)
        self.relayout_timer.timeout.connect(self._start_layout)
        self.shown_once = False
        self.update_job = None                   # the check for a newer version in hand (check_updates)
        self.narrow: bool | None = None
        self.auto_plan = False                 # "both" turned into "plan" by a narrow window
        self.before_clean = None               # the layout before «Only the drawing»
        # the first widths and heights of the target (docs/studio/19-grafica): tree 320, properties 380, checks 230
        # in a window of 1600 px; narrower in a smaller one (the first window takes 85 % of the screen)
        width = int(self.screen().availableGeometry().width() * 0.85)
        self.resizeDocks([self.docks[0], self.docks[1]], [max(240, min(320, round(width * 0.2))),
                                                          max(300, min(380, round(width * 0.24)))],
                         Qt.Orientation.Horizontal)
        self.resizeDocks([self.checks_dock], [230], Qt.Orientation.Vertical)
        self.factory_state = self.saveState()  # what «Restore the default layout» comes back to
        self.restored = self._restore_window()
        self._toolbar_style()                  # the side bar as the preferences say, not as the saved state had it
        if not self.restored:
            # first start: most of the screen, as a drawing program wants
            area = self.screen().availableGeometry()
            self.resize(int(area.width() * 0.85), int(area.height() * 0.85))
        self._show_all(fit=True)
        self.plan.set_tool("select")
        # Meridio answers (task 14): the conversation behind his bubble, «Ask Meridio» on the checks
        self.assistant_chat = Chat(self.assistant, WindowHost(self), cfg, self._save_config, self)
        self.checks_page.ask.connect(self.assistant_chat.ask_about)
        self._show_assistant(cfg.assistant)
        if self.shortcut_notes:
            self.hint.setText(self._shortcut_notice())
        self._title()

    def open_file_page(self, section: str = "open") -> None:
        """The File page over the window (ui/file_page.py), the bar of the phase put away under it; again, closed."""
        if self.file_page.isVisible():
            self.file_page.close_page()
            return
        # in one step, the window's painting held: the bar hidden and the page shown in the same frame (R98: for a
        # moment the phase's tools came back between the two)
        self.setUpdatesEnabled(False)
        try:
            self.bars_before_file = self.tabs.bars.isHidden()
            self.tabs.header.set_file_open(True)
            self.tabs.bars.hide()
            self.tabs.header.file_button.setChecked(True)
            self._settle_layouts()
            self.file_page.open_page(section)
        finally:
            self.setUpdatesEnabled(True)

    def _file_page_closed(self) -> None:
        self.setUpdatesEnabled(False)
        try:
            self.tabs.header.file_button.setChecked(False)
            self.tabs.header.set_file_open(False)
            if not self.bars_before_file:
                self.tabs.bars.show()
            self._settle_layouts()
        finally:
            self.setUpdatesEnabled(True)

    def _settle_layouts(self) -> None:
        """The layouts the bar's going or coming asked for, done now and not on the loop's next turns: the header
        shrank by the bar a frame later, and the File page, placed on the panels as they were, grew 56 px under the
        pointer, the «animation in jerks» of R132 (25/10/2026)."""
        for _round in range(3):
            QApplication.sendPostedEvents(None, QEvent.Type.LayoutRequest)
        if self.layout() is not None:
            self.layout().activate()
        self.gaps.apply()                           # the page's gaps now, not a turn later (8 px off for a frame)

    def _menu_bar_always(self, on: bool) -> None:
        self.cfg.menu_bar = bool(on)
        self.alt_menus.set_always(self.cfg.menu_bar)
        self._save_config()

    def childEvent(self, event) -> None:
        super().childEvent(event)
        # a tab bar of panels put together is made by Qt when they are, after the window is built (R109)
        if event.added() and not getattr(self, "_dock_tabs_pending", False):
            self._dock_tabs_pending = True
            QTimer.singleShot(0, self, self._dock_tabs)

    def _dock_tabs(self) -> None:
        """The tab bars of the panels put together (R109): the variants' segmented control, no base line under the
        cards."""
        self._dock_tabs_pending = False
        for bar in self.findChildren(QTabBar, options=Qt.FindChildOption.FindDirectChildrenOnly):
            if bar.objectName() != "dock-tabs":
                bar.setObjectName("dock-tabs")
                bar.setDrawBase(False)
                bar.setExpanding(False)
                bar.setElideMode(Qt.TextElideMode.ElideRight)
                bar.style().unpolish(bar)
                bar.style().polish(bar)

    def eventFilter(self, obj, event) -> bool:
        if obj in (getattr(self, "plan", None), getattr(getattr(self, "plan", None), "viewport", lambda: None)()) \
                and event.type() in (QEvent.Type.MouseButtonRelease, QEvent.Type.KeyRelease,
                                     QEvent.Type.MouseButtonDblClick):
            QTimer.singleShot(0, self, self._guide)
        return super().eventFilter(obj, event)

    def _guide(self, done: bool = False) -> None:
        """The help card on the step of the gesture in hand (R43; guides.py)."""
        import time

        from .. import guides
        plan = self.plan
        tool = plan.tool
        begun = bool(plan.row_start is not None or plan.gesture is not None or plan.measure)
        done = done or (not plan.chain and time.monotonic() - getattr(self, "last_drawn_at", -99.0) < 8.0)
        n = guides.step(tool, len(plan.chain), begun, done)
        if (tool, n) != self.guide_at:
            self.guide_at = (tool, n)
            self.help_box.show_guide(tool if tool in guides.guides() else "", n)

    def card_rects(self) -> list:
        """The cards on the window's floor, in its pixels: the docks docked, and the page of the phase."""
        from PySide6.QtCore import QPoint, QRectF
        out = [QRectF(d.card_rect().translated(d.pos()))
               for d in self.findChildren(CardDock, options=Qt.FindChildOption.FindDirectChildrenOnly)
               if d.isVisible() and not d.isFloating() and d.parentWidget() is self]
        page = self.tabs.pages.currentWidget()
        if page is not None and page.isVisible():
            out.append(QRectF(QRect(page.mapTo(self, QPoint(0, 0)), page.size())))
        return out

    def menuBar(self) -> QMenuBar:
        """The menu bar, inside the menu widget with the phases' header (QMainWindow's own would replace it)."""
        return self._menu_bar

    # actions and menus

    def _actions(self) -> None:
        """The menus, from the commands of shortcuts.py: each QAction is kept in self.commands under the command's
        id, with the keys of the settings (apply_shortcuts). The bars of the phases take the same actions
        (_build_phases)."""
        bar = self.menuBar()
        # the bar of the phase on the left side (study 17, B2), when the preferences want it there: the icons
        # alone, the groups as separators, filled again at each change of phase (_fill_side_bar)
        self.side_bar = QToolBar(_("Tools"))
        self.side_bar.setObjectName("tools")
        self.side_bar.setMovable(False)
        self.side_bar.setFloatable(False)
        self.side_bar.setIconSize(QSize(Icon.BAR, Icon.BAR))
        self.side_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.side_bar)
        self.side_bar.hide()
        known = {c.id: c for c in shortcuts.commands()}
        self.commands: dict[str, QAction] = {}
        self.tips: dict[str, str] = {}

        def act(menu, cid, slot, checkable=False, tip="", action=None):
            a = action or QAction(known[cid].text, self)
            a.setCheckable(checkable or a.isCheckable())
            if tip:
                self.tips[cid] = tip
            if slot is not None:
                a.triggered.connect(slot)
            menu.addAction(a)
            self.commands[cid] = a
            return a

        file = bar.addMenu(_("&File"))
        act(file, "new", self._new)
        act(file, "open", self._open)
        act(file, "save", self._save)
        act(file, "save_as", self._save_as)
        act(file, "save_revision", self._save_revision,
            tip=_("A new file next to this one, with the suffix _R01, _R02...: the previous one stays as it was"))
        act(file, "import_pvsyst", lambda: self._import_pvsyst_project(),
            tip=_("A PVsyst project (.PRJ) and the variants next to it, as a new project: what is approximated or "
                  "missing is said first"))
        act(file, "import_ifc", lambda: self._import_ifc(),
            tip=_("The buildings of an architect's model (.ifc, .ifczip): outlines, roof planes, heights and what stands "
                  "on the roofs, nothing more; one change, undone with Ctrl+Z"))
        file.addSeparator()
        act(file, "export_report", self._export_report,
            tip=_("Production, strings, consumption and economics with every calculation, as a PDF"))
        act(file, "export_csv", self._export_csv,
            tip=_("The typical year hour by hour, with the balance and a header that says each column's unit and "
                  "source: the register of the calculations, as a CSV file"))
        act(file, "export_ifc", lambda: self._export_ifc(),
            tip=_("The project as an IFC4 model, georeferenced: buildings, roofs, obstacles and every module with its "
                  "string, for the architect or the BIM coordinator"))
        act(file, "copy_notes", lambda: self.checks_page._copy(),
            tip=_("The paragraphs of the rules that apply, with their sources, to paste into the technical report"))
        file.addSeparator()
        act(file, "preferences", lambda: self._preferences())
        file.addSeparator()
        act(file, "quit", self.close)

        edit = bar.addMenu(_("&Edit"))
        act(edit, "undo", None, action=self.undo.createUndoAction(self, _("&Undo")))
        act(edit, "redo", None, action=self.undo.createRedoAction(self, _("&Redo")))
        edit.addSeparator()
        act(edit, "delete", self._delete_key)

        draw = bar.addMenu(_("&Draw"))
        group = QActionGroup(self)
        self.tool_actions = {}
        for tool, tip in (("select", _("Select objects and modules")), ("building", _("Draw a building outline")),
                          ("pitch", _("Draw a free roof pitch")), ("subfield", _("Draw an area for modules")),
                          ("exclusion", _("Draw a skylight, vent, plant or walkway")),
                          ("row", _("Draw a row of modules in a sub-field: two clicks, with its module and gaps")),
                          ("move", _("Move the selection by two points or a value typed; R inside Move turns it, "
                                     "Ctrl held at the click makes a copy")),
                          ("rotate", _("Turn the selection about its middle, in steps of 15°, or by an angle typed")),
                          ("measure", _("Measure a distance"))):
            slot = self._rotate_tool if tool == "rotate" else (lambda _c=False, t=tool: self._set_tool(t))
            a = act(draw, "tool_" + tool, slot, True, tip)
            a.setIcon(icons.icon(tool))
            group.addAction(a)
            self.tool_actions[tool] = a
        self.tool_actions["select"].setChecked(True)
        draw.addSeparator()
        self.rect_action = act(draw, "rectangle", self._rectangle_mode, True,
                               _("Two corners give a side, the third click the depth"))
        act(draw, "square", self._square, False,
            _("The corners of the selected outline within 13° of a right angle become right angles"))
        act(draw, "building_template", self._building_template, False,
            _("A rectangle, an L, a T, a U or a trapezoid with its measures, placed with a click on the plan"))
        draw.addSeparator()
        # the layout of the selected sub-field (the Layout group of the Model's bar; the same as in its properties)
        act(draw, "fill", lambda: self._fill_selected(True),
            tip=_("The modules laid in the selected sub-field with its parameters and the fire brigade rules"))
        act(draw, "empty", lambda: self._fill_selected(False),
            tip=_("The modules taken out of the selected sub-field; the outline stays"))
        act(draw, "refill", self._refill_selected,
            tip=_("The selected sub-field laid again from its parameters: its rows by hand are lost"))
        for cid in ("rectangle", "square", "building_template", "fill", "empty", "refill"):
            self.commands[cid].setIcon(icons.icon(cid))
        draw.addSeparator()
        # drawing aids as in AutoCAD, on F keys and on buttons of the status bar (an F key is never the only way)
        self.snaps_action = act(draw, "snaps", self._snaps, True,
                                _("The point goes to corners, middles and directions; Ctrl held lets it go free"))
        self.snaps_action.setChecked(True)
        self.ortho_action = act(draw, "ortho", self._ortho, True,
                                _("The sides go square to the first side drawn (East and North before it)"))
        self.snaps_action.setIcon(icons.icon("snaps"))
        self.ortho_action.setIcon(icons.icon("ortho"))

        view = bar.addMenu(_("&View"))
        mode = QActionGroup(self)
        self.view_actions = {}
        self.current_view = "both"
        # Ctrl+Shift+digit as Explorer's view styles; F2, F3 and F4 stay free for renaming, AutoCAD's snaps and
        # the laptop (on the Framework 13 the F keys are media keys without Fn): docs/studio/12a, 1.11
        for key, tip in (("plan", _("The plan alone; again, plan and 3D side by side")),
                         ("3d", _("The 3D view alone; again, plan and 3D side by side")),
                         ("both", _("Plan and 3D side by side"))):
            a = act(view, "view_" + key, lambda _c=False, k=key: self._view_toggle(k), True, tip)
            a.setIcon(icons.icon(key))
            mode.addAction(a)
            self.view_actions[key] = a
        self.view_actions["both"].setChecked(True)
        view.addSeparator()
        # the phases as places (design 2.1, C8): each one in the menu, and the two keys that go round
        phase_menu = view.addMenu(_("P&hases"))
        self.phase_actions: dict[str, QAction] = {}
        phase_group = QActionGroup(self)
        for phase in phases.phases():               # Ctrl+1 to Ctrl+6 (shortcuts.py)
            a = act(phase_menu, f"phase_{phase.id}", lambda _c=False, pid=phase.id: self.show_phase(pid), True)
            phase_group.addAction(a)
            self.phase_actions[phase.id] = a
        self.phase_actions["model"].setChecked(True)
        phase_menu.addSeparator()
        act(phase_menu, "next_phase", lambda: self.show_phase(phases.next(self.phase())),
            tip=_("The phase after this one; after the last, the first again"))
        act(phase_menu, "previous_phase", lambda: self.show_phase(phases.previous(self.phase())),
            tip=_("The phase before this one"))
        # the words under the icons of the bar of the phase (design C1): on by default, off by choice or by itself
        # in a low window (design 5.3)
        self.toolbar_text_action = act(view, "toolbar_text", lambda on: self._toolbar_style("text" if on else "icons"),
                                       True, _("The words under the icons of the bar of the phase; in a window lower "
                                               "than {px} px the icons stay alone").format(px=LOW_WINDOW))
        self.menu_bar_action = act(view, "menu_bar", self._menu_bar_always, True,
                                   _("The menus always above the phases; off, Alt shows them and they go again"))
        view.addSeparator()
        panels = view.addMenu(_("Pa&nels"))
        for dock, cid, tip in ((self.docks[0], "panel_project", _("The project's tree: show or hide it")),
                               (self.docks[1], "panel_properties", _("The properties of what is selected: show or "
                                                                     "hide them")),
                               (self.checks_dock, "panel_checks", _("The checks of the project: show or hide them")),
                               (self.help_dock, "panel_help", _("The help of the field in hand, under the "
                                                                "properties: show or hide it"))):
            act(panels, cid, None, tip=tip, action=dock.toggleViewAction())
        act(panels, "focus_checks", self._focus_checks,
            tip=_("The checks with the keyboard on them: the arrows go through them, the views follow"))
        act(panels, "fix_check", lambda: self.checks_page.apply_fix(),
            tip=_("«Fix» of the item in hand in the Checks panel, as VS Code's quick fix"))
        act(panels, "assistant", lambda: self.assistant.toggle(),
            tip=_("{name}, the assistant: open with the cursor in the field, or back to the character").format(
                name=assistant_core.NAME))
        panels.addSeparator()
        self.clean_action = act(panels, "clean_screen", self._clean_screen, True,
                                _("The panels and the bars out of the way; again, back as they were"))
        act(panels, "default_layout", self._default_layout, tip=_("The panels, the bars and the views as at the "
                                                                  "first start"))
        view.addSeparator()
        fit = act(view, "fit", self._fit, tip=_("The selection framed in both views; everything when nothing is "
                                               "selected"))
        fit.setIcon(icons.icon("fit"))
        for cid, factor, tip in (("zoom_in", 1.2, _("Both views closer; + and Ctrl++ do the same")),
                                 ("zoom_out", 1 / 1.2, _("Both views farther away; - and Ctrl+- do the same"))):
            action = act(view, cid, lambda _c=False, f=factor: self._zoom(f), tip=tip)
            action.setIcon(icons.icon(cid))
        for cid, slot, tip in (("view_align", self._align_view,
                                _("Choose a side of the selected outline; the plan turns parallel to it")),
                               ("view_north", self._north_view, _("The plan with true North up again"))):
            action = act(view, cid, slot, tip=tip)
            action.setIcon(icons.icon(cid))
        # W: in the Plant phase, which has lent the plan, the strings stay (study 16, D.6)
        strings = act(view, "strings", lambda on: self.plan.show_wiring(on or self.split_home is not None), True,
                      _("Each string as a line through its modules, in a colour of its own; always shown in the "
                        "Plant phase"))
        strings.setChecked(True)
        # the plan's background (R21, R36): the best source for the site, the sources that cover it with their terms,
        # none (made again each time the menu opens: the site may have moved), the others in the preferences, the
        # veil, the images imported; one menu, in View and in the plan's bar
        self.background_menu = QMenu(_("&Background"), self)
        self.background_menu.setToolTipsVisible(True)
        view.addMenu(self.background_menu)
        self.background_group = QActionGroup(self)
        self.source_actions: list = []
        self.other_sources_action = QAction(_("Other sources…"), self)
        self.other_sources_action.setToolTip(_("Every source with its area and its licence, the default choice and "
                                               "your own sources (WMS, WMTS, XYZ): Preferences > Maps"))
        self.other_sources_action.triggered.connect(lambda: self._preferences("maps"))
        self.background_menu.addAction(self.other_sources_action)
        # the imagery darkened under the drawing, so that the lines read on a light roof too (Daniel, 23/10/2026)
        veil = self.background_menu.addMenu(_("Darken the imagery"))
        self.veil_group = QActionGroup(self)
        for strength in view_colours.VEILS:
            a = QAction(_("{n} %").format(n=round(strength * 100)) if strength else _("Not darkened"), self,
                        checkable=True)
            a.setData(strength)
            a.triggered.connect(lambda _c=False, v=strength: self._veil(v))
            a.setChecked(abs(strength - self.cfg.veil) < 0.01)
            veil.addAction(a)
            self.veil_group.addAction(a)
        self.background_menu.addSeparator()
        self.import_image_action = QAction(_("Import an image…"), self)
        self.import_image_action.setToolTip(_("A PNG, a JPEG or the first page of a PDF, under the drawing: then in "
                                              "scale with two points"))
        self.import_image_action.triggered.connect(lambda: self._import_image())
        self.background_menu.addAction(self.import_image_action)
        self.underlay_entries: list = []        # the menus of the images, made again each time the menu opens
        self.background_menu.aboutToShow.connect(self._fill_sources)
        self.background_menu.aboutToShow.connect(self._fill_underlay_menu)
        self.background_action = QAction(icons.icon("background"), _("Background"), self)
        self.background_action.setToolTip(_("The plan's background: orthophoto, map or none, how dark, and the "
                                             "images imported"))
        self.background_action.setMenu(self.background_menu)
        # the commands of the views inside the views, in a bar of their own (R14, R27; ui/viewbar.py)
        views = [self.view_actions[k] for k in ("plan", "3d", "both")]
        zoom = [fit, self.commands["zoom_in"], self.commands["zoom_out"]]
        words = {fit: _("Fit"), self.commands["zoom_in"]: _("Zoom in"),
                 self.commands["zoom_out"]: _("Zoom out")}
        self.plan.viewbar = ViewBar(self.plan, [views, zoom, [self.snaps_action, self.ortho_action],
                                                [self.background_action]], keys=(self.snaps_action, self.ortho_action),
                                    words=words)
        self.view3d.viewbar = ViewBar(self.view3d, [views, zoom], words=words)
        self.view3d.viewbar.show_group(0, False)        # side by side at the start: the selector on the plan's bar
        catalogues = bar.addMenu(_("&Catalogues"))
        from .catalog_dialog import kind_titles

        def plain_action(menu, text, slot):
            a = QAction(text, self)
            a.triggered.connect(slot)
            menu.addAction(a)
            return a
        for kind, title in kind_titles().items():
            plain_action(catalogues, title + "…", lambda _c=False, k=kind: CatalogDialog(k, self, browse=True).exec())
        catalogues.addSeparator()
        plain_action(catalogues, _("Import a module from PVsyst (.PAN)…"), lambda: self._import_pvsyst("module"))
        plain_action(catalogues, _("Import an inverter from PVsyst (.OND)…"), lambda: self._import_pvsyst("inverter"))
        site = bar.addMenu(_("&Site"))
        plain_action(site, _("&Find the site…"), self._find_site)
        # the commands of the phases of the results (phases 2-5), each also here: a bar's button is never the
        # only way
        compute = bar.addMenu(_("Co&mpute"))
        act(compute, "compute", lambda: self._compute_energy(fetch=True),
            tip=_("Production, consumption, balance and economics of the variant in hand, with the weather in the "
                  "cache or fetched"))
        act(compute, "fetch_pvgis", lambda: self._compute_energy(fetch=True),
            tip=_("The typical year and the horizon of the site from PVGIS, then the computation"))
        compute.addSeparator()
        act(compute, "inverter_catalog", self._choose_inverter,
            tip=_("An inverter from the catalogue added to the plant of the variant in hand"))
        act(compute, "inverter_auto", self._size_inverters,
            tip=_("As many inverters as the DC/AC ratio asks, all like the first of the list; without one, Meridiana "
                  "sizes one at that ratio"))
        # the strings (task 16d; R114-R116): the designer's; Meridiana proposes them only when asked, with one of
        # PVsyst's strategies, or completes them for the modules left out; drawn by hand; all deleted
        self.strategy_menu = QMenu(_("Strategy"), self)
        self.strategy_menu.setToolTipsVisible(True)
        self.strategy_group = QActionGroup(self)
        self.strategy_actions = {}
        for key, name in plant_model.strategy_names().items():
            a = QAction(name, self, checkable=True)
            a.setToolTip(_("Propose the strings with this strategy, in place of those there are (asked first)"))
            a.triggered.connect(lambda _c=False, k=key: self._strings_propose(k))
            self.strategy_group.addAction(a)
            self.strategy_menu.addAction(a)
            self.strategy_actions[key] = a
        self.strategy_actions["serpentine"].setChecked(True)
        # a menu of the strategies and nothing else: a button whose own click proposed and whose arrow chose
        # was a click that did one thing or the other (a tool button of Qt runs its action instead of the menu)
        auto = act(compute, "strings_auto", None,
                   tip=_("Meridiana's strings in place of those there are, once (asked first, one undo step), with the "
                         "strategy chosen in its menu: back and forth, a row per string, U on two rows, a row per MPPT. "
                         "Nothing changes them afterwards"))
        auto.setMenu(self.strategy_menu)
        act(compute, "strings_complete", self._strings_complete,
            tip=_("Meridiana's strings for the modules in no string only, on the inputs without strings first: yours "
                  "stay as they are"))
        self.stringing_action = act(compute, "strings_manual", self._draw_string, True,
                                    tip=_("A new string on the input of the string chosen (the first free input when "
                                          "none is): click its modules on the plan in order or drag over them; "
                                          "Backspace takes back the last, Enter or a double click closes it, Esc gives "
                                          "it up"))
        act(compute, "strings_clear", self._strings_clear,
            tip=_("Every string deleted, after a question: the modules stay laid, in no string (one undo step)"))
        compute.addSeparator()
        act(compute, "import_curve", self._import_curve_file,
            tip=_("A measured load curve (CSV, 15 minutes or hourly) as the consumption"))
        act(compute, "consumption_base", self._consumption_base,
            tip=_("Where the consumption comes from: a year, the bands, the bills, a curve or a profile"))
        act(compute, "battery_catalog", self._choose_battery,
            tip=_("A battery from the catalogue for the balance"))
        variants = bar.addMenu(_("V&ariants"))
        act(variants, "new_variant", self._new_variant,
            tip=_("A copy of the variant in hand, to change without losing it: the site is shared"))
        rename_variant = plain_action(variants, _("&Rename the variant…"), self._rename_variant)
        delete_variant = plain_action(variants, _("&Delete a variant…"), self._delete_variant)
        variants.addSeparator()
        act(variants, "compare_variants", self._compare_variants,
            tip=_("Production, self-consumption and economics of every variant, side by side"))
        # the icons of the commands the bars of the phases show (ui/icons.NAMES, by the command's id)
        for cid in ("compute", "fetch_pvgis", "inverter_catalog", "inverter_auto", "import_curve", "consumption_base",
                    "battery_catalog", "copy_notes", "export_report", "export_csv", "save_revision", "compare_variants",
                    "strings_auto", "strings_complete", "strings_manual", "strings_clear", "import_ifc",
                    "export_ifc"):
            self.commands[cid].setIcon(icons.icon(cid))
        # «Variant» in the right corner of the row of the phases (design 2.1): it is of every phase
        corner = QWidget()
        corner_box = QVBoxLayout(corner)
        corner_box.setContentsMargins(0, 0, 0, 2)
        # the variants as a segmented control: one click from one to another, + for a new one (R73)
        from .variant_bar import VariantBar
        self.variant_bar = VariantBar(self.commands["new_variant"],
                                      [self.commands["new_variant"], rename_variant, delete_variant, None,
                                       self.commands["compare_variants"]])
        self.variant_bar.chosen.connect(self._switch_variant)
        corner_box.addWidget(self.variant_bar, 0, Qt.AlignmentFlag.AlignRight)
        self.tabs.setCornerWidget(corner)
        help_ = bar.addMenu(_("&Help"))
        # the help next to things (task 17d; design C7): F1 and Shift+F1 to the box at the foot of the right panel
        act(help_, "context_help", lambda: self.help_box.context_help(),
            tip=_("The help of the field with the keyboard, in the box at the foot of the right panel"))
        act(help_, "whats_this", lambda: QWhatsThis.enterWhatsThisMode(),
            tip=_("The pointer becomes a question mark: the next click explains what it touches"))
        act(help_, "manual", lambda: self.help_box.open_manual(),
            tip=_("The manual inside Meridiana, at the chapter of the phase open"))
        help_.addSeparator()
        act(help_, "shortcuts", self._show_shortcuts, tip=_("Every key of the window, with a search; change them in "
                                                            "the same place"))
        act(help_, "check_updates", lambda: self.check_updates(manual=True),
            tip=_("Whether a newer version is out, from the project's releases on GitHub"))
        act(help_, "about", self._about)
        keys, self.shortcut_notes = shortcuts.settle(self.cfg.shortcuts)
        self.apply_shortcuts(keys)
        for view_bar in (self.plan.viewbar, self.view3d.viewbar):
            for action, button in view_bar.buttons.items():
                if hasattr(button, "own_tip"):
                    button.own_tip = view_bar.tip(action)
                    button.setToolTip(button.own_tip)
        # every command on the window too: its keys work with the menu bar hidden (Alt shows it, ui/menubar.py);
        # an action's shortcut fires only from a widget on screen
        self.addActions([a for a in self.commands.values() if a not in self.actions()])

    def _build_phases(self) -> None:
        """The Plant page (task 16d) with its inspector and the reference in Production, the Report page (a shell
        until the report's task) and the bar of each phase, from phases.py with the window's actions; then the look
        the preferences ask for."""
        self.plant_page = PlantPage(self.commands)
        self.plant_inspector = PlantInspector(self.commands)
        self.inspector.add_plant(self.plant_inspector)
        self.plant_inspector.countChanged.connect(self._inverter_count)
        self.plant_inspector.removed.connect(self._inverter_removed)
        self.plant_inspector.edited.connect(lambda path, value: self._energy_edited("energy", path, value))
        self.plant_inspector.assigned.connect(self._assign_subfield)
        self.plant_inspector.stringChosen.connect(lambda i: self._choose_string(i, show=True))
        self.plant_inspector.list.newString.connect(self._new_string)
        self.plant_inspector.list.redraw.connect(self._redraw_string)
        self.plant_inspector.list.menuAsked.connect(self._string_list_menu)
        self.plant_inspector.optimizerAsked.connect(self._choose_optimizer)
        self.plant_inspector.optimizerCleared.connect(self._clear_optimizer)
        self.plant_inspector.perChosen.connect(self._optimizer_per)
        self.inverter_reference = install_reference(self.energy_page, lambda: self.show_phase("plant"))
        self.report_page = ReportPage(self.commands)
        self.report_side = ReportSide()
        self.report_side.changed.connect(self._report_edited)
        self.report_side.profilesAsked.connect(lambda: self._preferences("report"))
        self.inspector.deliverables.set_top(self.report_side)
        self.tabs.add_phase(phases.by_id("plant"), self.plant_page)
        self.tabs.add_phase(phases.by_id("report"), self.report_page)
        self.bars: dict[str, PhaseBar] = {}
        for phase in phases.phases():
            bar = PhaseBar(phase, self.commands)
            self.tabs.set_bar(self.tabs.index_of_phase(phase.id), bar)
            self.bars[phase.id] = bar
        # the Plant's strip at the right of its bar (R70)
        self.plant_holder = QWidget()
        holder_box = QHBoxLayout(self.plant_holder)
        holder_box.setContentsMargins(0, 0, Space.M, 0)
        self.bars["plant"].add_trailing(self.plant_holder)
        self.bars_text: bool | None = None
        self._toolbar_style()
        self._fill_side_bar()

    def phase(self) -> str:
        """The id of the phase open (phases.py)."""
        return self.tabs.phase_id() or "model"

    def show_phase(self, pid: str) -> None:
        index = self.tabs.index_of_phase(pid)
        if index >= 0:
            self.tabs.setCurrentIndex(index)

    def _theme_changed(self) -> None:
        """The theme's colours to what Qt's palette does not reach: the charts, the cube, the row and the bars of
        the phases and the assistant. The plan and the 3D view keep their own colours in both themes
        (view_colours, Daniel 23/10/2026)."""
        t = self.theme.tokens
        charts.set_theme(t, self.theme.dark, self.theme.family)
        self.view3d.cube.set_colours(t)
        if self.skeleton is not None:
            self.skeleton.set_colours(t)
        for bar in (self.plan.viewbar, self.view3d.viewbar):
            bar.set_colours(t)
        self.tabs.set_colours(t)
        self.checks_page.set_colours(t)
        self.assistant.set_colours(t)
        from . import sections
        sections.set_colours(t)                     # a section's name in the secondary text's tone (R136)
        if getattr(self, "file_page", None) is not None:
            self.file_page.set_colours(t)
        # the soft ends of what scrolls in the cards (Daniel, 24/10/2026): made once, in the panels' colour
        from . import fades
        fades.set_colour(t["panel"])
        if getattr(self, "panel_buttons", None) is not None:
            self.panel_buttons.set_colours(t)
        if getattr(self, "project", None) is not None and hasattr(self, "tree"):
            self._show_tree()                       # the icons in the kinds' colours of this theme (R67)
        from .cards import set_corner_colour
        set_corner_colour(t["panel"])               # the views' rounded corners on their card
        pages = (self.energy_page, self.consumption_page, self.economics_page)
        for area in (self.tree, self.checks_page.tree, self.props, self.inspector.results,
                     self.inspector.deliverables, getattr(self, "plant_inspector", None),
                     getattr(self.help_box.view, "scroll", None),
                     *[a for p in pages for a in (p.side, p.centre)]):
            fades.attach(area)
        self.assistant_button.setIcon(self.assistant.icon())
        # the strings (task 16d): a tint for each from the colour chosen, the traffic light in the colours of the
        # states, the same on the plan, in the list of the inspector and in the legend
        tints = theme_colors.string_tints(theme_colors.seed_for(self.cfg.accent, self.theme.system_accent))
        states = {"ok": theme_colors.STATUS["good"], "check": theme_colors.STATUS["warning"],
                  "fail": theme_colors.STATUS["critical"]}
        self.plan.string_tints, self.plan.string_states = tints, states
        self.plan.set_wiring(self.plan.wiring)
        if hasattr(self, "plant_page"):
            # on the light panels the warnings' yellow is 1.8:1: its ochre (study 13, 3.1)
            light = states if self.theme.dark else {**states, "check": theme_colors.WARNING_INK}
            self.plant_page.legend.setText(legend_html(tints, light))
            self.plant_page.key.set(tints, light)
            self.plant_inspector.states = light
            self.plant_inspector.clip_scale.set_colours(t, light)
            self.plant_inspector.colours = list(self.plan.string_colours)

    def apply_shortcuts(self, keys: dict) -> None:
        """The keys of each command (id -> list of keys as Qt writes them), shown in the tooltips too."""
        for cid, action in self.commands.items():
            seqs = [QKeySequence(k) for k in keys.get(cid, [])]
            action.setShortcuts(seqs)
            tip = self.tips.get(cid, "")
            # the name first, with its key: with the icons alone the tooltip is where the name is read (R19)
            action.setToolTip(self._tip_head(action, seqs) + (f"\n{tip}" if tip else ""))
            if tip:
                action.setStatusTip(tip)
        self.bindings = keys

    @staticmethod
    def _tip_head(action, seqs) -> str:
        """«Name (key)», or the name alone when the command has no key."""
        label = shortcuts.plain(action.text())
        shown = seqs[0].toString(QKeySequence.SequenceFormat.NativeText) if seqs else ""
        return f"{label} ({shown})" if shown else label

    def _toolbar_style(self, style: str | None = None, place: str | None = None) -> None:
        """The bar of the phase as the preferences want it (design C1 and 5.3): the words under the icons
        ("text") or the icons alone ("icons"); under the row of the phases, or on the left side with the icons
        alone and the groups as separators (study 17, B2). In a window lower than LOW_WINDOW px the words go by
        themselves (_fit_bars)."""
        if style is not None:
            self.cfg.toolbar = style
        if place is not None:
            self.cfg.toolbar_place = place
        if not hasattr(self, "bars"):
            return
        text = self.cfg.toolbar == "text"
        self.toolbar_text_action.setChecked(text)
        left = self.cfg.toolbar_place == "left"
        self.tabs.bars.setVisible(not left)
        self.plant_page.place_strip(None if left else self.plant_holder)
        self.side_bar.setVisible(left and not self.clean_action.isChecked())
        self.bars_text = None
        self._fit_bars()

    def _fit_bars(self) -> None:
        """The words under the icons when they are wanted and the window is tall enough (design 5.3)."""
        if not hasattr(self, "bars"):
            return
        text = self.cfg.toolbar == "text" and self.height() >= LOW_WINDOW
        if text == self.bars_text:
            return
        self.bars_text = text
        self.tabs.set_text(text)

    def _fill_side_bar(self) -> None:
        """The actions of the phase open in the side bar, the groups as separators."""
        self.side_bar.clear()
        bar = self.bars.get(self.phase())
        if bar is None:
            return
        for n, group in enumerate(bar.groups):
            if n:
                self.side_bar.addSeparator()
            for button in group.buttons.values():
                self.side_bar.addAction(button.defaultAction())

    def _fill_selected(self, fill: bool) -> None:
        """Lay the modules in the selected sub-field, or take them out (the Layout group of the Model's bar)."""
        oid = self._selected_subfield()
        if self.project_subfield(oid) is None:
            self.hint.setText(_("Select a sub-field first: the modules are laid in it."))
            return
        self._action("fill" if fill else "empty", "subfield", oid)

    def _refill_selected(self) -> None:
        """«Lay again automatically» on the selected sub-field (the Layout group of the Model's bar)."""
        oid = self._selected_subfield()
        if self.project_subfield(oid) is None:
            self.hint.setText(_("Select a sub-field first: the modules are laid in it."))
            return
        self._action("relayout", "subfield", oid)

    def _import_curve_file(self) -> None:
        """A load curve from a file (the consumption page's own dialog), on the Consumption phase."""
        self.show_phase("consumption")
        self.consumption_page._import()

    def _consumption_base(self) -> None:
        """Where the consumption comes from: the Consumption phase, the keyboard on the choice."""
        self.show_phase("consumption")
        checked = self.consumption_page.mode.checkedButton()
        if checked is not None:
            checked.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _snaps(self, on: bool) -> None:
        self.plan.snaps_on = on
        self.view3d.backend.gizmo_snaps = on                # the steps of the gizmo too (task 16b)
        self.hint.setText(_("Snaps on.") if on else _("Snaps off: the point goes where the pointer is."))

    def _ortho(self, on: bool) -> None:
        self.plan.ortho = on
        self.hint.setText(_("Ortho on: the sides go square.") if on else _("Ortho off."))

    def _focus_checks(self) -> None:
        """Ctrl+Shift+M, as VS Code's problems: the panel shown, the keyboard on its list."""
        self.checks_dock.show()
        self.checks_dock.raise_()
        self.checks_page.tree.setFocus(Qt.FocusReason.ShortcutFocusReason)
        if self.checks_page.tree.currentItem() is None and self.checks_page.tree.topLevelItemCount():
            self.checks_page.tree.setCurrentItem(self.checks_page.tree.topLevelItem(0))

    def _show_shortcuts(self) -> None:
        from .shortcuts_dialog import ShortcutsDialog
        dialog = ShortcutsDialog(self.bindings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._set_shortcuts(dialog.bindings)

    def _set_shortcuts(self, keys: dict) -> None:
        self.apply_shortcuts(keys)
        self.cfg.shortcuts = shortcuts.differences(keys, self.cfg.shortcuts)
        self._save_config()

    def _shortcut_notice(self) -> str:
        """What settling the keys of the settings did (shortcuts.settle), as the status bar says it at start."""
        names = {c.id: shortcuts.plain(c.text) for c in shortcuts.commands()}
        said = []
        for keys, mine, lost in self.shortcut_notes:
            native = QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)
            if lost:
                said.append(_("{keys} stays yours for «{mine}»; «{lost}», which has it by default in this version, "
                              "is left without it.").format(keys=native, mine=names[mine[0]],
                                                           lost="», «".join(names[c] for c in lost)))
            else:
                said.append(_("{keys} is the key of «{commands}»: none of them works with it until one changes.")
                            .format(keys=native, commands="», «".join(names[c] for c in mine)))
        return " ".join(said) + (" " + _("Preferences > Keyboard to change them.") if said else "")

    def _preferences(self, page: str = "", run=None) -> None:
        """Preferences: the appearance follows the choice while the dialog is open, and goes back as it was if
        it is cancelled. `run` stands in for exec() in the tests."""
        from .preferences import Preferences
        before = (self.cfg.theme, self.cfg.accent, self.cfg.backgrounds)
        dialog = Preferences(self.cfg, self.bindings, self.theme, self, page)
        dialog.appearance.settled.connect(self._appearance)
        accepted = (run or (lambda d: d.exec()))(dialog) == QDialog.DialogCode.Accepted
        if accepted:
            self._appearance(*dialog.appearance.choice())
            self._navigation(*dialog.navigation.choice())
            self._show_assistant(dialog.assistant.isChecked())
            self._dock_assistant(dialog.assistant_docked.isChecked())
            self._assistant_look(dialog.assistant_animated.isChecked(), dialog.assistant_style.currentData())
            self.assistant_chat.apply_preferences(dialog.meridio.choice())
            self._toolbar_style(dialog.appearance.toolbar.currentData(), dialog.appearance.place.currentData())
            self._set_shortcuts(dialog.keys.bindings)
            self._network(*dialog.privacy.choice())
            self.cfg.check_updates = dialog.privacy.updates.isChecked()
            self._maps(*dialog.maps.choice())
            self._report_profiles(*dialog.report.choice())
        else:
            self._appearance(*before)
        self._save_config()

    def _report_profiles(self, profiles: list, default: str) -> None:
        """The authors of the reports as the preferences wrote them; a logo chosen there is copied into the data
        folder (the file chosen may move or go), the copy's name kept."""
        import shutil
        import uuid
        folder = self.paths.data / "logos"
        kept = []
        for p in profiles:
            logo = p.get("logo") or ""
            if logo and Path(logo).is_absolute() and Path(logo).parent != folder:
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                    copy = folder / f"{uuid.uuid4().hex[:12]}{Path(logo).suffix.lower()}"
                    shutil.copyfile(logo, copy)
                    p = {**p, "logo": copy.name}
                except OSError as error:
                    self.tell(_("The logo could not be copied: {error}").format(error=error))
                    p = {**p, "logo": ""}
            elif logo and Path(logo).is_absolute():
                p = {**p, "logo": Path(logo).name}
            kept.append(p)
        self.cfg.report_profiles, self.cfg.report_profile = kept, default
        if self.phase() == "report":
            self._show_inspector()

    def _report_profile(self) -> dict | None:
        """The profile the project's report is signed with, its logo as a path."""
        from .. import reports
        p = reports.profile_for(self.project, self.cfg.report_profiles, self.cfg.report_profile)
        if p and p.get("logo"):
            p = {**p, "logo": str(self.paths.data / "logos" / p["logo"])}
        return p

    def _report_edited(self, key: str, value) -> None:
        """A choice of the Report phase: an edit of the project, undoable (its report is shared by the variants)."""
        from .. import reports
        if reports.settings(self.project).get(key) == value and key in (self.project.report or {}):
            return

        def change(p):
            p.report = {**(p.report or {}), key: value}
        self.edit(_("Change the report"), change)

    def _report_data(self) -> dict:
        """What the report is made of: the year, the checks, the strings as they are on the plan now (the live
        plant), the facts of the rules, the layouts of the sub-fields."""
        return {**self.energy, "checks": self.checks_page.items, "plant": self.plant_state or self.energy.get("plant"),
                "rules_facts": self._rules_facts(), "results": self.session.good_results()}

    def _preview_report(self) -> None:
        """The pages of the report, made a step at a time (report.preview_steps) while the Report phase is open:
        those shown stay until the new ones are ready; a preview half made for an older project is dropped."""
        if self.phase() != "report":
            return
        ready = bool(self.energy) and self.energy.get("sim") is not None
        if not ready:
            self.report_page.set_ready(False)
            return
        import json
        profile = self._report_profile()
        key = (self._state_key(), id(self.energy.get("sim")), id(self.plant_state), id(self.checks_page.items),
               json.dumps(profile, sort_keys=True))
        if key == self.preview_key or (self.preview_run is not None and self.preview_run[2] == key):
            return
        if self.preview_run is not None:
            self.preview_run[0].close()
        from . import report
        pages: list = []
        steps = report.preview_steps(model.Project.from_json(self.snapshot(), check=False), self._report_data(),
                                     1240, pages, profile)
        self.preview_run = (steps, pages, key)
        QTimer.singleShot(0, self, self._preview_step)

    def _preview_step(self) -> None:
        if self.preview_run is None:
            return
        steps, pages, key = self.preview_run
        try:
            fraction, what = next(steps)
        except StopIteration as done:
            self.preview_run = None
            self.preview_key = key
            self.report_page.show_pages(pages, done.value)
            return
        except Exception as error:                  # noqa: BLE001 (said in the page and kept in the log)
            self.preview_run = None
            log.complain("report", error)
            self.report_page.status.setText(_("The preview could not be made: {error}").format(error=error))
            return
        self.report_page.set_progress(fraction, what)
        QTimer.singleShot(0, self, self._preview_step)

    def _maps(self, background: str, custom: list) -> None:
        """Preferences > Maps applied: the default background and the designer's sources."""
        self.cfg.map_sources = custom
        self.plan.set_sources(custom)
        self.cfg.background = background
        self.plan.set_source(background)
        self._fill_sources()

    def _network(self, geocoding: bool, pvgis: bool, tiles: bool) -> None:
        """The three switches of the privacy page, applied: the map loader stops asking the servers."""
        self.cfg.network_geocoding, self.cfg.network_pvgis, self.cfg.network_tiles = geocoding, pvgis, tiles
        self.plan.loader.offline = not tiles
        if tiles:
            self.plan.tile_timer.start()

    def _motion(self, reduced: bool) -> None:
        self.view3d.backend.reduced_motion = reduced
        self.assistant.reduced_motion = reduced

    def _show_assistant(self, on: bool) -> None:
        """The switch of the preferences: the assistant, its item in the status bar and its key, or none of them."""
        self.cfg.assistant = on
        if not on:
            self.assistant.close_panel()
        self.assistant.setVisible(on and not self.assistant.docked)
        self.assistant_button.setVisible(on)
        self.checks_page.ask_on = on
        self.commands["assistant"].setVisible(on)
        self.commands["assistant"].setEnabled(on)

    def _dock_assistant(self, on: bool) -> None:
        """The assistant into the panels or floating over the views again, remembered."""
        self.cfg.assistant_docked = on
        self.assistant.set_docked(on)
        self._save_config()

    def _assistant_look(self, animated: bool, style: str) -> None:
        """Preferences > Assistant: Meridio animated or still, smooth or pixel (R34); the status bar's icon follows."""
        self.cfg.assistant_animated, self.cfg.assistant_style = animated, style
        self.assistant.set_animated(animated)
        self.assistant.set_style(style)
        self.assistant_button.setIcon(self.assistant.icon())

    def _assistant_resized(self, width: int, height: int) -> None:
        """The speech bubble resized by its grip: the size is remembered."""
        self.cfg.assistant_width, self.cfg.assistant_height = width, height

    def _assistant_top(self) -> int:
        """Where Meridio's room begins: under the menu bar and the phases' header."""
        top = self.menuWidget()
        return top.geometry().bottom() + 1 if top is not None and top.isVisible() else 0

    def _assistant_home(self) -> QRect:
        """The card in the middle (the page of the phase), in the window's pixels: Meridio's first place."""
        page = self.tabs.pages.currentWidget()
        if page is None or not self.tabs.isVisible():
            return QRect()
        return QRect(page.mapTo(self, QPoint(0, 0)), page.size())

    def _assistant_reserved(self) -> int:
        """The room Meridio leaves at the bottom of the card in the middle: the sun bar under the 3D view on the
        model, the plan's attribution on the plant (he stood on its last words, 24/10/2026)."""
        if self.phase() == "plant":
            label = getattr(self.plan, "attribution", None)
            if label is not None and label.isVisibleTo(self.plan) and self.plan.isVisibleTo(self.tabs):
                from .plan_overlays import MARGIN
                return label.height() + MARGIN
            return 0
        return self.sunbar.height() if self.view3d_box.isVisibleTo(self.tabs) else 0

    def _assistant_avoid(self) -> list[tuple[int, int, int, int]]:
        """What Meridio's bubble must not cover, in the window's coordinates: the selection drawn on the plan and
        the points being picked (design 3.9), when the plan is in view on the model."""
        if self.phase() != "model" or not self.plan.isVisibleTo(self.tabs):
            return []
        points = list(self.plan.rings.get(tuple(self.plan.selection), []))
        if self.plan.point_pick is not None and len(self.plan.point_pick) > 2:
            points += [tuple(p) for p in self.plan.point_pick[2] if len(p) >= 2]
        if not points:
            return []
        viewport = self.plan.viewport()
        corners = [viewport.mapTo(self, self.plan.mapFromScene(QPointF(x, y))) for x, y in points]
        xs, ys = [c.x() for c in corners], [c.y() for c in corners]
        view = QRect(viewport.mapTo(self, QPoint(0, 0)), viewport.size())
        rect = QRect(QPoint(min(xs), min(ys)), QPoint(max(xs), max(ys))).intersected(view)
        return [(rect.x(), rect.y(), rect.width(), rect.height())] if not rect.isEmpty() else []

    def _settle_assistant_dock(self) -> None:
        """After a layout is restored: the assistant's panel only when the assistant is docked and enabled."""
        if not (self.assistant.docked and self.cfg.assistant):
            self.assistant_dock.hide()

    def _navigation(self, style: str, orbit: str, pivot: str, hint: bool | None = None) -> None:
        self.cfg.navigation, self.cfg.orbit, self.cfg.pivot = style, orbit, pivot
        if hint is not None:
            self.cfg.pivot_hint = hint
        self.view3d.set_navigation(style, orbit, pivot, self.cfg.pivot_hint)
        self.plan.set_navigation(style)

    def _appearance(self, theme: str, accent: str, backgrounds: str) -> None:
        self.cfg.theme, self.cfg.accent, self.cfg.backgrounds = theme, accent, backgrounds
        self.theme.apply()

    def _escape_3d(self) -> None:
        if self.plan.tool == "move":
            self._set_tool("select")
        else:
            self.plan.selection_back()

    def _set_tool(self, tool: str) -> None:
        self.show_phase("model")                    # drawing happens on the model
        self.tool_actions[tool].setChecked(True)
        self.plan.set_tool(tool)
        self._show_gizmo()
        self._guide()                               # the help card on the first step of the tool (R43)
        # drawing needs the plan; Move works in the 3D view as well (task 16b)
        if tool not in ("select", "move") and not self.view_actions["plan"].isChecked() and self.split.sizes()[0] == 0:
            self._view_mode("both")

    def _rotate_tool(self, _checked=False) -> None:
        """Rotate, in the Edit group: Move turning the selection (R inside Move does the same; design 2.2)."""
        self._set_tool("move")
        self.tool_actions["rotate"].setChecked(True)
        self.plan.start_rotate()

    def _move_mode(self, mode: str) -> None:
        """R inside Move: the button of the bar follows, Move or Rotate."""
        if self.plan.tool == "move":
            self.tool_actions["rotate" if mode == "rotate" else "move"].setChecked(True)

    def _transform(self, kind: str, oid: str, what: dict) -> None:
        """Move and Rotate (task 16b), from the plan or from the 3D view, as one step (move.py): a copy is selected;
        a move refused says why and leaves the project as it was. The arrows of the keyboard join in one step."""
        p = self.project
        if kind == "row":                          # a row moves within its sub-field (task 16c, manual.py)
            sfid, _sep, rid = oid.partition("/")
            if what.get("copy"):
                self.hint.setText(_("Not moved: {why}").format(why=_("a row is copied with «Add a row at the back»")))
            elif what["mode"] == "rotate":
                self.hint.setText(_("Not moved: {why}").format(
                    why=_("a row turns with its sub-field; a module on its own turns with a double click")))
            else:
                self._row_edit(_("Move"), lambda r: manual.translate(p, sfid, rid, what["dx"], what["dy"], r), sfid,
                               ("nudge", kind, oid) if what.get("nudge") else None, said=_("Not moved: {why}"))
            return
        try:
            if what.get("copy"):
                change = (move.copy(p, kind, oid, about=(what["cx"], what["cy"]), degrees=what["degrees"])
                          if what["mode"] == "rotate" else move.copy(p, kind, oid, what["dx"], what["dy"]))
                made: list = []
                self.edit(_("Copy"), lambda q: made.append(change(q)))
                if made:
                    self._select(kind, made[0])
                return
            if what["mode"] == "rotate":
                self.edit(_("Rotate"), move.rotate(p, kind, oid, what["cx"], what["cy"], what["degrees"]))
            else:
                self.edit(_("Move"), move.translate(p, kind, oid, what["dx"], what["dy"]),
                          ("nudge", kind, oid) if what.get("nudge") else None)
        except ValueError as error:
            self.hint.setText(_("Not moved: {why}").format(why=error))
            return
        self.view3d.backend.selection_centre = self._centre_3d(kind, oid)

    def _show_gizmo(self) -> None:
        """The gizmo of Move in the 3D view (task 16b): with Move active and something to move selected, on its middle
        at its roof (move.centre, move.height), with the outline of what moves with it for the preview; else none
        (study 16, B8: only with the tool, so that it does not hide the small modules)."""
        kind, oid = self.selection
        backend = self.view3d.backend
        centre = move.centre(self.project, kind, oid) if self.plan.tool == "move" and kind in MOVABLE else None
        if centre is None:
            backend.set_gizmo(None)
            return
        backend.set_gizmo(mesh.to_qt(centre[0], centre[1], move.height(self.project, kind, oid, centre)))
        parts = [viewaids.outline(self.project, self.results, kind, oid)]
        if kind == "building":
            parts += [viewaids.outline(self.project, self.results, k, x.id) for k, items in
                      (("subfield", self.project.subfields), ("exclusion", self.project.exclusions))
                      for x in items if x.building == oid]
        self.view3d.set_preview(np.concatenate(parts) if parts else np.zeros((0, 2, 3)))

    def _gizmo_done(self, east: float, north: float, degrees: float, copy: bool) -> None:
        """A handle of the gizmo released: the move along it, or the turn about the middle (Ctrl held: a copy)."""
        kind, oid = self.selection
        if kind not in MOVABLE:
            return
        if abs(degrees) > 1e-12:
            cx, cy = move.centre(self.project, kind, oid)
            self._transform(kind, oid, {"mode": "rotate", "cx": cx, "cy": cy, "degrees": degrees, "copy": copy})
        else:
            self._transform(kind, oid, {"mode": "move", "dx": east, "dy": north, "copy": copy})

    def _gizmo_typed(self, east, north, degrees) -> None:
        """The values written next to the gizmo, as one step: the move East and North, then the turn about the middle
        where it has gone."""
        kind, oid = self.selection
        if kind not in MOVABLE:
            return
        p = self.project
        dx, dy, turn = east or 0.0, north or 0.0, degrees or 0.0
        try:
            changes = [move.translate(p, kind, oid, dx, dy)] if dx or dy else []
            if turn:
                cx, cy = move.centre(p, kind, oid)
                changes.append(move.rotate(p, kind, oid, cx + dx, cy + dy, turn))
            if not changes:
                return
            text = _("Move") if not turn else _("Rotate") if not (dx or dy) else _("Move and rotate")
            self.edit(text, lambda q: [change(q) for change in changes])
        except ValueError as error:
            self.hint.setText(_("Not moved: {why}").format(why=error))
            return
        self.view3d.backend.selection_centre = self._centre_3d(kind, oid)

    def _gizmo_nudged(self, dx: float, dy: float) -> None:
        kind, oid = self.selection
        if kind in MOVABLE:
            self._transform(kind, oid, {"mode": "move", "dx": dx, "dy": dy, "copy": False, "nudge": True})

    def _rectangle_mode(self, _checked=False) -> None:
        self.plan.toggle_rectangle()
        self.rect_action.setChecked(self.plan.rect_mode)

    def _square(self) -> None:
        kind, oid = self.selection
        p = self.project
        target = {"building": lambda: p.building(oid), "subfield": lambda: self.project_subfield(oid),
                  "exclusion": lambda: next((e for e in p.exclusions if e.id == oid), None)}.get(kind, lambda: None)()
        if target is None:
            self.hint.setText(_("Select a building, a sub-field or an exclusion to square it."))
            return
        attr = "footprint" if kind == "building" else "ring"
        ring, why = squaring.square([tuple(q) for q in getattr(target, attr)])
        if why == "not_squarish":
            self.hint.setText(_("No corner is near a right angle: nothing to square."))
            return
        if why == "square_enough":
            self.hint.setText(_("It is square already."))
            return
        new = [[round(x, 4), round(y, 4)] for x, y in ring]

        def put(pp):
            t = {"building": lambda: pp.building(oid),
                 "subfield": lambda: next((s for s in pp.subfields if s.id == oid), None),
                 "exclusion": lambda: next((e for e in pp.exclusions if e.id == oid), None)}[kind]()
            setattr(t, attr, new)
        self.edit(_("Square the corners"), put)
        self.hint.setText(_("Squared: Ctrl+Z puts it back as drawn."))

    def _view_mode(self, mode: str) -> None:
        self.auto_plan = False                      # a narrow window sets it again right after its own change
        self.current_view = mode
        self.view_actions[mode].setChecked(True)
        if self.split_home is None:                 # lent to the Plant phase, the plan stays shown there
            self.plan.setVisible(mode in ("plan", "both"))
        self.view3d_box.setVisible(mode in ("3d", "both"))
        if self.view3d.viewbar is not None:         # the selector of the views once: on the plan's bar when it is there
            self.view3d.viewbar.show_group(0, mode == "3d")
        self.assistant.reposition()                 # on the model it stands above the sun bar, when there is one

    def _view_toggle(self, mode: str) -> None:
        """The plan or the 3D alone; asked again, both side by side. Asked in the Plant phase, whose plan has no 3D
        beside it, the Model takes it back first."""
        if self.split_home is not None:
            self.show_phase("model")
        self._view_mode("both" if mode != "both" and self.current_view == mode else mode)

    def _clean_screen(self, on: bool) -> None:
        """Ctrl+0, as AutoCAD's clean screen: panels and bars go and the drawing takes the window; again, they
        come back as they were."""
        if on:
            self.before_clean = self.saveState()
            for dock in (*self.docks, self.checks_dock, self.assistant_dock):
                dock.hide()
            self.side_bar.hide()
            self.tabs.bars.hide()
        elif self.before_clean is not None:
            self.restoreState(self.before_clean)
            self.before_clean = None
            self._settle_assistant_dock()
            self._toolbar_style()                   # the bar of the phase back where the preferences put it

    def _default_layout(self) -> None:
        """Panels, bars and views as at the first start: the way back from any arrangement."""
        self.clean_action.setChecked(False)
        self.before_clean = None
        self.restoreState(self.factory_state)
        for dock in (*self.docks, self.checks_dock):
            dock.show()
        self._settle_assistant_dock()
        self._toolbar_style()
        self._view_mode("both")
        width = self.split.width()
        self.split.setSizes([int(width * 0.55), int(width * 0.45)])

    def _background(self, key: str) -> None:
        self.cfg.background = key
        self.plan.set_source(key)
        self._fill_sources()
        self._save_config()

    def _fill_sources(self) -> None:
        """The sources of the Background menu for the site in hand (R36): «Automatic» with the name of the best,
        the photos and the maps that cover the site with their attribution and licence, None. The choice that
        does not cover the site (made on a project elsewhere) shows as Automatic, and stays for the sites it covers."""
        for a in self.source_actions:
            self.background_menu.removeAction(a)
            self.background_group.removeAction(a)
            a.deleteLater()
        self.source_actions = []
        plan = self.plan
        lon, lat = plan.origin.lon, plan.origin.lat
        best = plan.sources.get(tiles.best(plan.sources, lon, lat))
        found = tiles.covering(plan.sources, lon, lat)
        entries = [(tiles.AUTO, _("Automatic: {name}").format(name=tiles.display_name(best)) if best else
                    _("Automatic"), _("The best source for the site of the project, chosen by Meridiana"))]
        entries += [(s.key, tiles.display_name(s), "\n".join(t for t in (s.credit(), tiles.display_licence(s)) if t))
                    for s in found]
        entries.append((tiles.NONE, _("None"), _("The plan alone, on its light ground")))
        listed = {k for k, _t, _tip in entries}
        checked = self.cfg.background if self.cfg.background in listed else tiles.AUTO
        first = self.background_menu.actions()[0] if self.background_menu.actions() else None
        photos = sum(1 for s in found if s.imagery == "photo")
        for i, (key, text, tip) in enumerate(entries):
            a = QAction(text, self, checkable=True)
            a.setData(key)
            a.setToolTip(tip)
            a.setChecked(key == checked)
            a.triggered.connect(lambda _c=False, k=key: self._background(k))
            self.background_group.addAction(a)
            self.background_menu.insertAction(first, a)
            self.source_actions.append(a)
            if i in (0, photos, len(entries) - 2, len(entries) - 1):     # Automatic | photos | maps | None |
                sep = QAction(self)
                sep.setSeparator(True)
                self.background_menu.insertAction(first, sep)
                self.source_actions.append(sep)

    def _veil(self, strength: float) -> None:
        self.cfg.veil = strength
        self.plan.set_veil(strength)
        self._save_config()

    # images under the drawing (R21; underlay.py, ui/underlays.py)

    def _import_image(self, path: str | None = None) -> None:
        if path is None:
            path, _filter = QFileDialog.getOpenFileName(self, _("Import an image under the drawing"),
                                                        self.cfg.last_folder or "", underlays.file_filter())
            if not path:
                return
        try:
            data, width, height = underlays.read_image(Path(path))
        except ValueError as error:
            QMessageBox.warning(self, _("Import an image"), str(error))
            return
        seen = self.plan.mapToScene(self.plan.viewport().rect()).boundingRect()
        centre = (seen.center().x(), -seen.center().y())
        uid = self.project.new_id("u")
        u = underlay.placed(uid, Path(path).name, data, width, height, centre, 0.8 * seen.width())
        self.edit(_("Import an image"), lambda p: p.underlays.append(u))
        self.hint.setText(_("The image is under the drawing: put it in scale with two points, from the Background "
                            "menu of the plan."))

    def _change_underlay(self, uid: str, text: str, change) -> None:
        """One step on an image: `change(underlay)` gives the new one (ValueError: nothing done, said)."""
        found = next((u for u in self.project.underlays if u.id == uid), None)
        if found is None:
            return
        try:
            new = change(found)
        except ValueError as error:
            self.hint.setText(str(error))
            return

        def apply(p):
            p.underlays = [new if u.id == uid else u for u in p.underlays]
        self.edit(text, apply)

    def _remove_underlay(self, uid: str) -> None:
        self.edit(_("Remove an image"), lambda p: setattr(p, "underlays", [u for u in p.underlays if u.id != uid]))

    def _rotate_underlay(self, uid: str, degrees: float | None = None) -> None:
        if degrees is None:
            degrees, ok = QInputDialog.getDouble(self, _("Rotate the image"),
                                                 _("Degrees, anticlockwise (negative: clockwise):"), 0.0, -360.0,
                                                 360.0, 2)
            if not ok:
                return
        self._change_underlay(uid, _("Rotate an image"), lambda u: u.rotated(degrees))

    def _ask_distance(self) -> float | None:
        """The true distance between the two points, typed with its unit («7,5 m», «750 cm»); None: given up."""
        from .. import quantity
        text, ok = QInputDialog.getText(self, _("In scale"), _("The true distance between the two points "
                                                               "(for example 7,5 m):"))
        if not ok:
            return None
        try:
            return quantity.parse(text, "length")
        except ValueError as error:
            self.hint.setText(str(error))
            return None

    def _building_template(self) -> None:
        """«Building from a template…» (task 16a): the shape and its measures in a dialog, then a click on the plan
        for its South-West corner."""
        from .template_dialog import TemplateDialog
        dialog = TemplateDialog(self)
        if dialog.exec() and dialog.outline() is not None:
            self.place_template(dialog.outline(), dialog.turn())

    def place_template(self, ring: list, turn: float = 0.0) -> None:
        """Wait for the click on the plan where the first corner of the template's outline goes."""
        self._template = (ring, turn)
        self.show_phase("model")
        self.plan.pick_points("template", [_("Click where the South-West corner of the building goes; Esc gives up")])

    def _template_placed(self, at) -> None:
        pending, self._template = getattr(self, "_template", None), None
        if pending is None:
            return
        ring, turn = pending
        bid = self.project.new_id("b")
        n = len(self.project.buildings) + 1
        footprint = templates.placed(ring, at, turn)

        def add(p):
            p.buildings.append(model.Building(id=bid, name=_("Building {n}").format(n=n), footprint=footprint,
                                              height=6.0))
        self.edit(_("Building from a template"), add)
        self._select("building", bid)
        self.hint.setText(_("The sides can be changed one by one in the Sides group."))

    def _points_picked(self, purpose: str, points: list) -> None:
        """Points clicked on the plan: where a template goes; two for an image, to put it in scale or to move it
        from one to the other."""
        what, _sep, uid = purpose.partition(":")
        if what == "template" and points:
            self._template_placed(tuple(map(float, points[0])))
            return
        if len(points) < 2:
            return
        a, b = (tuple(map(float, q)) for q in points[:2])
        if what == "scale":
            distance = self._ask_distance()
            if distance is not None:
                self._change_underlay(uid, _("Put an image in scale"), lambda u: u.scaled(a, b, distance))
        elif what == "move":
            self._change_underlay(uid, _("Move an image"), lambda u: u.moved(b[0] - a[0], b[1] - a[1]))

    def _fill_underlay_menu(self) -> None:
        """Each image of the project in the background menu: shown, its transparency, in scale, moved, turned,
        removed."""
        for entry in self.underlay_entries:
            self.background_menu.removeAction(entry.menuAction())
            entry.deleteLater()
        self.underlay_entries = []
        for n, u in enumerate(self.project.underlays, 1):
            sub = QMenu(u.name or _("Image {n}").format(n=n), self.background_menu)
            shown = sub.addAction(_("Show"))
            shown.setCheckable(True)
            shown.setChecked(u.visible)
            shown.triggered.connect(lambda on, i=u.id: self._change_underlay(
                i, _("Show or hide an image"), lambda x: replace(x, visible=on)))
            see = sub.addMenu(_("Transparency"))
            for t in (0.0, 0.2, 0.4, 0.6, 0.8):
                a = see.addAction(_("{n} %").format(n=round(t * 100)))
                a.setCheckable(True)
                a.setChecked(abs((1 - u.opacity) - t) < 0.01)
                a.triggered.connect(lambda _c=False, i=u.id, o=1 - t: self._change_underlay(
                    i, _("Transparency of an image"), lambda x: replace(x, opacity=o)))
            sub.addSeparator()
            sub.addAction(_("In scale with two points…")).triggered.connect(
                lambda _c=False, i=u.id: self.plan.pick_points("scale:" + i, [
                    _("In scale: click the first point of a length you know on the image; Esc gives up."),
                    _("Now the second point; then type how far apart they truly are.")]))
            sub.addAction(_("Move with two points…")).triggered.connect(
                lambda _c=False, i=u.id: self.plan.pick_points("move:" + i, [
                    _("Move: click a point of the image; Esc gives up."), _("Now where that point goes.")]))
            sub.addAction(_("Rotate…")).triggered.connect(lambda _c=False, i=u.id: self._rotate_underlay(i))
            sub.addSeparator()
            sub.addAction(_("Remove")).triggered.connect(lambda _c=False, i=u.id: self._remove_underlay(i))
            self.background_menu.addMenu(sub)
            self.underlay_entries.append(sub)

    def _fit(self) -> None:
        """F: the selection framed in both views (study 12, V9 and T3), everything when nothing is selected."""
        kind, oid = self.selection
        found = self._outline(kind, oid)
        if found is None:
            self.plan.fit()
            self.view3d.fit()
            self._show_3d()
            return
        from PySide6.QtCore import QRectF

        from .plan import polygon
        ring = found[1]
        self.plan.fit(polygon(ring).boundingRect() if ring else QRectF())
        xs, ys = [float(q[0]) for q in ring], [float(q[1]) for q in ring]
        centre = np.array(self._centre_3d(kind, oid))
        radius = max(max(xs) - min(xs), max(ys) - min(ys)) / 2 * 1.2 + 2.0
        self.view3d.backend.user_moved = True
        self.view3d.backend.frame(centre, radius, animate=True)

    def _zoom(self, factor: float) -> None:
        """Plus and minus, from the keys or either view's bar: both views about their centres."""
        self.plan.zoom_at(factor, self.plan.viewport().rect().center())
        backend = self.view3d.backend
        w, h = backend.size
        backend.touch_zoom(float(np.log(factor) / np.log(1.0 / camera.ZOOM_STEP)), w / 2, h / 2)

    def _align_view(self) -> None:
        kind, oid = self.selection
        found = self._outline(kind, oid)
        if found is None:
            self.tell(_("Select a building, a roof pitch, a sub-field or an exclusion, then align the view to one "
                        "of its sides."))
            return
        self.plan.pick_edge("align", kind, oid, found[1])

    def _north_view(self) -> None:
        self.plan._end_pick()
        self.plan.reset_rotation()
        self.hint.setText(_("North is up. The project's coordinates have not changed."))

    # the project as data

    def snapshot(self) -> dict:
        return self.session.snapshot()

    def edit(self, text: str, change, merge=None) -> None:
        """Apply `change(project)` as one undoable step (session.edit); with `merge`, a step that follows the
        same kind of change within a moment joins the last one. The views follow through _session_changed."""
        self.session.edit(text, change, merge)

    def _session_changed(self, topics: set) -> None:
        """What the session says changed, shown by topic (session.py lists them): each view follows the
        topics it reads, never everything (study 18, A 7.2). A name changed redraws the tree and the
        properties and nothing else: no layout, no year. Another project in the place of this one ("file")
        is shown by the caller, framed."""
        if "file" in topics:
            return
        if "restored" in topics:
            self.props.drop_typing()
        if self.plan.draft is not None and ("restored" in topics or "project:variants" in topics):
            # an undo, a redo or another variant under a string being drawn: given up, said
            self._end_draft()
            self.hint.setText(_("The string being drawn was given up: the project changed under it."))
        project = {t for t in topics if t.startswith("project:")}
        layouts = any(t.startswith("layout:") for t in topics)
        if project and session_needs_layout(topics):
            self._relayout()
        if project:
            self._title()
        if "project:site" in project:
            self.plan.set_origin(self.project.site.lat, self.project.site.lon)
        if (project - {"project:text", "project:rules", "project:fire"}) or layouts:
            self.plan.show_project(self.project, self.session.good_results())
        if "project:variants" in project:
            self._show_variants()
        if (project & {"project:text", "project:geometry", "project:subfields", "project:variants"}) or layouts:
            self._show_tree()
        if project or layouts or "selection" in topics:
            self._show_properties()
            self._show_measure()
            self._enable_layout_commands()
        if project and self.phase() == "report":
            self._show_inspector()                  # a deliverable made before the change is to make again
        if (project & {"project:geometry", "project:site", "project:subfields", "project:variants"}) or layouts:
            self._show_3d()
        elif "selection" in topics and self.shown_once:
            self._show_3d()                         # the selection tinted in 3D as well
        if (project & {"project:energy", "project:subfields", "project:site", "project:variants"}) or layouts:
            self._show_energy_forms()
        # the strings and their checks follow what they are made of: the inverters, the strings, the sub-fields and
        # their layouts, the year (task 16d)
        if (project & {"project:energy", "project:subfields", "project:variants"}) or layouts or "energy" in topics:
            self._plant_soon()
        elif "selection" in topics and self.phase() == "plant":
            self.plant_inspector.colours = list(self.plan.string_colours)
            self.plant_inspector.show_plant(self.project, self.plant_state, self.selection, self.chosen_string)
        if "checks" in topics:
            self._show_checks()
        if (project - NO_YEAR) or "energy" in topics:
            self._show_stale()

    def _show_stale(self) -> None:
        """The values of the year in hand greyed, and the mark after the titles of their phases and of the Checks,
        while the project is not the one they were computed for (session.energy_outdated: from the change itself,
        the layouts on their way counted); clean again when the new year comes, or when an undo goes back to the
        state computed (study 16, F1; design 3.12)."""
        stale = self.session.energy_outdated()
        if stale == self.stale_shown:
            return
        self.stale_shown = stale
        from .energy_pages import stale_tip
        for pid, page in (("production", self.energy_page), ("consumption", self.consumption_page),
                          ("economics", self.economics_page)):
            page.set_stale(stale)
            self.tabs.set_stale(pid, stale, stale_tip())
        self._checks_title()

    def _checks_title(self) -> None:
        """The Checks panel's title with its counts, and the mark of values to update: the checks of the strings and
        of the shadows read the year in hand."""
        self.checks_dock.setWindowTitle(self.checks_page.title(_("Checks")) + (STALE_MARK if self.stale_shown else ""))

    # variants

    def _show_variants(self) -> None:
        bar = getattr(self, "variant_bar", None)
        if bar is not None:
            bar.set_variants([(v["id"], v["name"]) for v in self.project.variants], self.project.variant)

    def _switch_variant(self, vid: str) -> None:
        if not vid or vid == self.project.variant:
            return
        name = next(v["name"] for v in self.project.variants if v["id"] == vid)
        self.energy = {}
        self.results = {}
        self.edit(_("Work on the variant {name}").format(name=name), lambda p: p.switch_variant(vid))

    def _new_variant(self) -> None:
        n = len(self.project.variants) + 1
        name, ok = QInputDialog.getText(self, _("New variant"), _("Name of the new variant (a copy of this one):"),
                                        text=_("Variant {n}").format(n=n))
        if not ok or not name.strip():
            return
        self.edit(_("New variant {name}").format(name=name.strip()), lambda p: p.add_variant(name.strip()))
        self.hint.setText(_("Working on the variant {name}: change what you want, the others stay as they were.").format(
            name=name.strip()))

    def _rename_variant(self) -> None:
        here = self.project.current_variant()
        name, ok = QInputDialog.getText(self, _("Rename the variant"), _("Name:"), text=here["name"])
        if not ok or not name.strip() or name.strip() == here["name"]:
            return

        def rename(p):
            p.current_variant()["name"] = name.strip()
        self.edit(_("Rename the variant"), rename)

    def _delete_variant(self) -> None:
        others = [v for v in self.project.variants if v["id"] != self.project.variant]
        if not others:
            QMessageBox.information(self, _("Delete a variant"), _("There is only the variant in hand: nothing to "
                                                                  "delete."))
            return
        names = [v["name"] for v in others]
        name, ok = QInputDialog.getItem(self, _("Delete a variant"), _("Which variant? (to delete the one in hand, "
                                                                      "switch to another first)"), names, 0, False)
        if not ok:
            return
        vid = others[names.index(name)]["id"]
        self.edit(_("Delete the variant {name}").format(name=name), lambda p: p.remove_variant(vid))

    def _variant_figures(self, snapshot: dict, vid: str) -> dict:
        """Lay out and compute one variant of the project, as the window does the one in hand (in a worker
        thread: nothing of the window is touched): its figures for the comparison."""
        return self.session.variant_figures(snapshot, vid, self.paths.cache)

    def _compare_variants(self) -> None:
        from .variants import VariantsDialog
        snapshot = self.snapshot()
        dialog = VariantsDialog([(v["id"], v["name"]) for v in self.project.variants],
                                lambda vid: self._variant_figures(snapshot, vid), self.project.variant, self, self.pool)
        self.compare_dialog = dialog
        dialog.show()

    # drawing and selection

    def _host(self, ring):
        """The building under the middle of what was drawn and what a sub-field keeps of the pitch there (the side
        of its eave on a gable or hip roof, model.Building.pitch_ref); None on the ground (move.host)."""
        return move.host(self.project, ring)

    def roof_ring_at(self, x: float, y: float) -> list | None:
        """The outline of the pitch under the point (x East, y North), or of the whole roof when it is flat; None
        off the buildings."""
        from shapely.geometry import Point
        here = Point(x, y)
        for b in self.project.buildings:
            if not Polygon(b.footprint).buffer(1e-6).contains(here):
                continue
            for pitch in b.pitches():
                if len(pitch.ring) >= 3 and Polygon(pitch.ring).buffer(1e-6).contains(here):
                    return [list(p) for p in pitch.ring]
            return [list(p) for p in b.footprint]
        return None

    def _whole_pitch(self, tool: str, x: float, y: float) -> None:
        """A double click of the Sub-field tool on a roof: the sub-field of that pitch, whole (R64)."""
        ring = self.roof_ring_at(x, y)
        if ring is None:
            self.hint.setText(_("Double-click a roof to take a pitch whole; on the ground, draw the area."))
            return
        self._drawn(tool, ring)

    def _subfields_on_pitches(self, bid: str) -> None:
        """«A sub-field on each pitch» of a building's menu (R64): one for each pitch with room, in one edit."""
        b = self.project.building(bid)
        if b is None:
            return
        rings = [[list(p) for p in pitch.ring] for pitch in b.pitches() if len(pitch.ring) >= 3
                 and Polygon(pitch.ring).area >= 0.5] or [[list(p) for p in b.footprint]]
        for ring in rings:
            self._drawn("subfield", ring)

    def _drawn(self, tool: str, ring: list) -> None:
        import time
        self.last_drawn_at = time.monotonic()      # the help card says what comes next for a moment (R43)
        ring = [[round(x, 4), round(y, 4)] for x, y in ring]
        if Polygon(ring).area < 0.5:
            self.hint.setText(_("Too small to keep: draw it again."))
            return
        if tool == "building":
            bid = self.project.new_id("b")
            n = len(self.project.buildings) + 1

            def add(p):
                p.buildings.append(model.Building(id=bid, name=_("Building {n}").format(n=n), footprint=ring, height=6.0))
            self.edit(_("Draw a building"), add)
            self._select("building", bid)
        elif tool == "subfield":
            b, pitch = self._host(ring)
            sid = self.project.new_id("s")
            n = len(self.project.subfields) + 1
            if b is None:
                mounting = "ground"
            else:
                index = b.pitch_index(pitch)
                mounting = "coplanar" if b.pitches()[index or 0].tilt > 0 else "tilted_anchored"

            def add(p):
                p.subfields.append(model.SubField(id=sid, name=_("Sub-field {n}").format(n=n), ring=ring,
                                                  building=b.id if b else None, pitch=pitch,
                                                  params={"mounting": mounting}))
            self.edit(_("Draw a sub-field"), add)
            self._select("subfield", sid)
        elif tool == "exclusion":
            b, _pitch = self._host(ring)
            eid = self.project.new_id("e")

            def add(p):
                p.exclusions.append(model.ExclusionItem(id=eid, ring=ring, kind="skylight", building=b.id if b else None))
            self.edit(_("Draw an exclusion"), add)
            self._select("exclusion", eid)
        elif tool == "pitch":
            b, _pitch = self._host(ring)
            if b is None:
                self.hint.setText(_("A pitch belongs to a building: draw it inside one."))
                return

            def add(p):
                bb = p.building(b.id)
                if bb.roof.type != "free":
                    bb.roof.type = "free"
                    bb.roof.free_pitches = []
                # the slope of a new pitched roof, 35 % (Daniel, 23/10/2026; roofs.COVERINGS)
                bb.roof.free_pitches.append({"ring": ring, "eave_side": 0, "eave": bb.height,
                                             "tilt": roofs.proposed_tilt(bb.roof.covering or roofs.DEFAULT_COVERING)})
            self.edit(_("Draw a pitch"), add)
            self._select("building", b.id)

    def _picked(self, kind: str, oid: str) -> None:
        if kind == "pitch":
            kind, oid = "building", oid.split(":")[0]
        self._select(kind or "site", oid)

    def _select(self, kind: str, oid: str) -> None:
        self.plan.set_selection(kind, oid)
        self.view3d.backend.selection_centre = self._centre_3d(kind, oid)
        self.plan.focus(None)
        # a row is about its sub-field in the checks and the tree (task 16c)
        self.checks_page.show_related(*(("subfield", oid.partition("/")[0]) if kind == "row" else (kind, oid)))
        self.session.select(kind, oid)              # the tree, the properties, the measure and the 3D follow
        self._tree_select()
        if kind == "row":
            sfid, _sep, rid = oid.partition("/")
            sf = self.project_subfield(sfid)
            self.hint.setText(_("Row {row} of {name}: click a module to select it, or Esc to select the sub-field.")
                              .format(row=rid, name=sf.name if sf is not None else sfid))

    def _show_measure(self) -> None:
        kind, oid = self.selection
        self.measure_label.setText(viewaids.measure_text(viewaids.measure(self.project, self.results, kind, oid)))

    def _centre_3d(self, kind: str, oid: str):
        """The middle of the selected object, in the 3D view's axes: the orbit's pivot when the preferences
        put it on the selection."""
        found = self._outline(kind, oid)
        if found is None:
            return None
        ring = found[1]
        x = sum(float(q[0]) for q in ring) / len(ring)
        y = sum(float(q[1]) for q in ring) / len(ring)
        b = self.project.building(oid if kind == "building" else
                                  getattr(self.project_subfield(oid), "building", None) if kind == "subfield" else None)
        return mesh.to_qt(x, y, b.height if b is not None else 0.0)

    def _module_clicked(self, sfid: str, key: str) -> None:
        self.hint.setText(_("Module {key} of {name}: a second click on the same row selects it; Esc selects the "
                            "sub-field; Delete takes the module out of the layout.").format(
            key=key, name=self.project_subfield(sfid).name if self.project_subfield(sfid) else sfid))
        self.session.select("subfield", sfid, (sfid, key))
        if not self.shown_once:
            self._show_3d()

    def _repeated_row(self, sfid: str, key: str) -> str:
        rid = self.plan.rid_of(sfid, key)
        if rid and self.selection == ("subfield", sfid) and self.selected_module[0] == sfid and \
                self.plan.rid_of(*self.selected_module) == rid:
            return rid
        return ""

    def _module_view_picked(self, sfid: str, key: str) -> None:
        rid = self._repeated_row(sfid, key)
        if rid:
            self.plan.selected_module = ("", "")
            self._select("row", f"{sfid}/{rid}")
            return
        self.plan.selected_module = (sfid, key)
        self.plan.set_selection("subfield", sfid)
        self._module_clicked(sfid, key)

    def _module_picked_3d(self, index: int) -> None:
        if 0 <= index < len(self.module_index):
            self._module_view_picked(*self.module_index[index])

    def _point_picked_3d(self, x: float, y: float) -> None:
        """A click in the 3D view on what is not a module: what lies at that point of the plan, as the plan would
        pick it (the selection is one for both views, study 12, T2); nothing there, the site."""
        import math as _math

        from .plan import to_scene
        if _math.isnan(x):
            self._select("site", "")
            return
        kind, oid, key = self.plan._pick(to_scene(x, y))
        if kind == "module":
            self._module_view_picked(oid, key)
            return
        self.plan.selected_module = ("", "")
        self.selected_module = ("", "")
        self._picked(kind, oid)

    def project_subfield(self, sfid):
        return next((s for s in self.project.subfields if s.id == sfid), None)

    def _tree_clicked(self, item, column) -> None:
        kind, oid = item.data(0, Qt.ItemDataRole.UserRole) or ("site", "")
        if kind != "group":                         # a section's header is not selected (study 17, T2)
            self._select(kind, oid)
        key = item.data(1, Qt.ItemDataRole.UserRole) if column == 1 else None
        if key:                                     # the mark: the checks of this object, in the panel (R30)
            self.checks_page.show_subset(tuple(key), item.text(0))
            self.checks_dock.show()
            self.checks_dock.raise_()
            self.checks_page.take_first()           # and to its first check (Daniel, 24/10/2026)

    def _delete_key(self) -> None:
        """Del, a key of the whole window: it deletes the selection only with Select. While a sub-field was
        being drawn on a building, it deleted the building with its sub-fields (review, 23/10/2026). In the Plant
        phase it deletes the string chosen and nothing else (R115)."""
        if self.phase() == "plant":
            if self.plan.draft is not None:
                self.hint.setText(_("While a string is drawn, Backspace takes back the last module and Esc gives the "
                                    "string up."))
            elif self.chosen_string >= 0:
                self._delete_string(self.chosen_string)
            else:
                self.hint.setText(_("Choose a string in the list on the right or click one of its modules: Del "
                                    "deletes it."))
            return
        if self.plan.tool != "select" or self.plan.chain:
            self.hint.setText(_("Del deletes with Select. While drawing, Backspace takes back the last point and "
                                "Esc the whole outline."))
            return
        self._delete()

    def _delete(self) -> None:
        kind, oid = self.selection
        module = getattr(self.plan, "selected_module", ("", ""))
        if module[0]:
            # a module on its own goes with its row, any other is taken out by hand (manual.delete_module)
            sfid, key = module
            self.plan.selected_module = ("", "")
            self._row_edit(_("Take a module out"), lambda r: manual.delete_module(self.project, sfid, key, r), sfid)
            return
        if kind == "row":
            sfid, _sep, rid = oid.partition("/")
            self._row_edit(_("Take the row away"), lambda r: manual.remove(self.project, sfid, rid, r), sfid)
            self._select("subfield", sfid)
            return
        if kind == "building":
            def drop(p):
                p.buildings = [b for b in p.buildings if b.id != oid]
                p.subfields = [s for s in p.subfields if s.building != oid]
                p.exclusions = [e for e in p.exclusions if e.building != oid]
            self.edit(_("Delete a building"), drop)
        elif kind == "subfield":
            self.edit(_("Delete a sub-field"), lambda p: setattr(p, "subfields", [s for s in p.subfields if s.id != oid]))
        elif kind == "exclusion":
            self.edit(_("Delete an exclusion"), lambda p: setattr(p, "exclusions", [e for e in p.exclusions if e.id != oid]))
        else:
            return
        self._select("site", "")

    # the layout by hand (task 16c): the gestures on the rows; manual.py makes the changes, the session applies them

    def _row_edit(self, text: str, make, sfid: str, merge=None, said: str = ""):
        """A change of manual.py on the rows of a sub-field as one step: `make(result)` gives it from the layout in
        hand. A sub-field automatic until now is by hand from here, and the bar says so as PVsyst warns; a change
        refused says why and leaves the project as it was. What the change answers (a new row's id) comes back."""
        sf = self.project_subfield(sfid)
        if sf is None:
            return None
        was_auto = not sf.manual
        made: list = []
        try:
            change = make(self.results.get(sfid))
            self.edit(text, lambda p: made.append(change(p)), merge)
        except ValueError as error:
            self.hint.setText((said or _("Not changed: {why}")).format(why=error))
            return None
        now = self.project_subfield(sfid)
        if was_auto and now is not None and now.manual:
            self.hint.setText(_("The rows are yours now: «Lay again automatically» makes them again."))
        return made[0] if made else None

    def _subfield_at(self, point) -> str:
        """The sub-field under a point of the plan: the one selected first, else the first drawn there."""
        from shapely.geometry import Point
        here = Point(float(point[0]), float(point[1]))
        mine = self._selected_subfield()
        for sf in sorted(self.project.subfields, key=lambda s: s.id != mine):
            if len(sf.ring) >= 3 and Polygon([tuple(map(float, q)) for q in sf.ring]).buffer(1e-6).contains(here):
                return sf.id
        return ""

    def _hand_rows(self, sf) -> list:
        """The rows of a sub-field without laying it: its own by hand, else those of its layout in hand."""
        if sf.manual:
            return sf.hand_rows()
        r = self.results.get(sf.id)
        return list(r.rows) if sf.filled and r is not None and not isinstance(r, Exception) else []

    def _row_preview(self, start, end):
        """What the plan draws while a row is drawn: its modules' corners, and whether they go beyond the edge band or
        onto an exclusion (drawn red, kept all the same)."""
        sf = self.project_subfield(self._subfield_at(start))
        if sf is None:
            return [], True
        try:
            row = manual.line_row(self.project, sf, start, end, self._hand_rows(sf))
            return manual.corners(self.project, sf, [row]), manual.trouble(self.project, sf, [row])
        except ValueError:
            return [], True

    def _row_drawn(self, start, end) -> None:
        """A row drawn with the Row tool: in the sub-field where it starts, which becomes by hand (and laid)."""
        sfid = self._subfield_at(start)
        if not sfid:
            self.hint.setText(_("A row is drawn in a sub-field: start it inside one."))
            return
        self._row_edit(_("Draw a row"), lambda r: manual.draw(self.project, sfid, start, end, r), sfid)

    def _row_info(self, oid: str) -> dict | None:
        """The outline of a row and the end of its front edge (the grip that lengthens it), for the plan; kept while
        the layout is the same."""
        sfid, _sep, rid = oid.partition("/")
        sf, r = self.project_subfield(sfid), self.results.get(sfid)
        if sf is None or r is None or isinstance(r, Exception):
            return None
        cached = self.row_cache
        if cached[0] is not None and cached[0][0] == oid and cached[0][1] is r:
            return cached[1]
        row = next((x for x in r.rows if x.id == rid), None)
        mine = [c for m in r.modules if m.rid == rid for c in m.corners]
        info = None
        if row is not None and row.places and mine:
            from shapely.geometry import MultiPoint
            box = MultiPoint(mine).minimum_rotated_rectangle
            size = manual.frame(self.project, sf, [row])[1]
            info = {"ring": [tuple(map(float, q)) for q in list(box.exterior.coords)[:-1]]
                    if box.geom_type == "Polygon" else None, "end": manual.end_point(row, size)}
        self.row_cache = ((oid, r), info)          # the layout itself, not its id: an id comes back after it goes
        return info

    def _row_resized(self, oid: str, x: float, y: float) -> None:
        sfid, _sep, rid = oid.partition("/")
        self._row_edit(_("Shorten or lengthen a row"), lambda r: manual.resize(self.project, sfid, rid, (x, y), r),
                       sfid)

    def _module_double_clicked(self, sfid: str, key: str) -> None:
        """A double click on a module: on its own it turns by 90° (Aurora); in a row of more, the row is selected, as
        the second of two clicks does."""
        r = self.results.get(sfid)
        rid = manual.row_of(r, key)
        row = next((x for x in getattr(r, "rows", None) or [] if x.id == rid), None)
        if row is None:
            return
        if row.count != 1:
            self.plan.selected_module = ("", "")
            self._select("row", f"{sfid}/{rid}")
            return
        self._row_edit(_("Turn the module"), lambda res: manual.turn(self.project, sfid, rid, res), sfid)

    def _relayout_subfield(self, sfid: str, ask: bool = True) -> None:
        """«Lay again automatically»: asked first when the rows are by hand (PVsyst warns before it rebuilds); not
        when it comes as a fix shown before it is kept (R126)."""
        sf = self.project_subfield(sfid)
        if sf is None:
            return
        if sf.manual and ask:
            answer = QMessageBox.question(self, _("Lay again automatically"),
                                          _("The rows by hand give way to the automatic layout, and the modules taken "
                                            "out by hand come back. Undo brings them back. Go on?"),
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.edit(_("Lay again automatically"), manual.relayout(self.project, sfid))

    def _row_actions(self, kind: str, oid: str, key: str) -> list:
        """What the right button offers on a module or a row (task 16c): take the row away, add one at the back,
        shorten or lengthen it, explode it, turn a module on its own, lay the sub-field again automatically."""
        sfid = oid.partition("/")[0] if kind == "row" else oid
        r = self.results.get(sfid)
        rid = oid.partition("/")[2] if kind == "row" else manual.row_of(r, key)
        row = next((x for x in getattr(r, "rows", None) or [] if x.id == rid), None)
        if row is None:
            return []
        out = [None]
        if kind != "row":
            out.append((_("Select the row"), lambda: (setattr(self.plan, "selected_module", ("", "")),
                                                     self._select("row", f"{sfid}/{rid}"))))
        out.append((_("Take the row away"), lambda: self._row_edit(
            _("Take the row away"), lambda res: manual.remove(self.project, sfid, rid, res), sfid)))
        out.append((_("Add a row at the back"), lambda: self._row_edit(
            _("Add a row at the back"), lambda res: manual.append(self.project, sfid, rid, res), sfid)))
        out.append((_("Shorten or lengthen…"), lambda: self._shorten_hint(sfid, rid)))
        if row.count > 1:
            out.append((_("Explode the row"), lambda: self._row_edit(
                _("Explode the row"), lambda res: manual.explode(self.project, sfid, rid, res), sfid)))
        else:
            out.append((_("Turn by 90°"), lambda: self._row_edit(
                _("Turn the module"), lambda res: manual.turn(self.project, sfid, rid, res), sfid)))
        out.append(None)
        return out

    def _shorten_hint(self, sfid: str, rid: str) -> None:
        """«Shorten or lengthen»: the row selected, its end a grip to drag."""
        self._set_tool("select")
        self.plan.selected_module = ("", "")
        self._select("row", f"{sfid}/{rid}")
        self.hint.setText(_("Drag the square at the end of the row: it takes or gives back places."))

    def _module_changed(self, sfid: str, module_id: str, text: str, before=None) -> None:
        """A new module for a sub-field: by hand, its rows adapted when the module's sides are within 2 cm of the old
        one's, else asked (adapt them, or lay the sub-field again automatically; Daniel, 23/10/2026). `before(p)`
        runs first in the same step (the module put in the project from the catalogue)."""
        adapt = True
        if manual.needs_asking(self._with(before), sfid, module_id):
            answer = self._ask_rows_module()
            if not answer:
                return
            adapt = answer == "adapt"

        def change(p):
            if before is not None:
                before(p)
            manual.change_module(p, sfid, module_id, adapt)(p)
        self.edit(text, change)

    def _ask_rows_module(self) -> str:
        """Asked when a new module is more than 2 cm from the old one on rows by hand: "adapt", "again" (lay the
        sub-field again automatically) or "" (nothing changes)."""
        box = QMessageBox(QMessageBox.Icon.Question, _("A module of other sizes"),
                          _("The new module differs by more than 2 cm from the one the rows by hand were drawn with. "
                            "Adapt the rows (the same places and modules, the gaps kept), or lay the sub-field again "
                            "automatically?"), parent=self)
        keep = box.addButton(_("Adapt the rows"), QMessageBox.ButtonRole.AcceptRole)
        again = box.addButton(_("Lay again automatically"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        return {id(keep): "adapt", id(again): "again"}.get(id(box.clickedButton()), "")

    def _with(self, before):
        """The project as `before(p)` would leave it (a copy), to ask about it."""
        if before is None:
            return self.project
        p = model.Project.from_json(self.snapshot(), check=False)
        before(p)
        return p

    # properties

    def _edited(self, kind: str, oid: str, changes: dict) -> None:
        sf = self.project_subfield(oid) if kind == "subfield" else None
        if sf is not None and sf.manual and set(changes) == {"module"} and changes["module"] != sf.module:
            # the rows by hand follow a new module, or are laid again (task 16c)
            self._module_changed(oid, changes["module"], _("Change {what}").format(what=field_label("module", kind)))
            return

        def apply(p):
            if kind == "project":
                for k, v in changes.items():
                    setattr(p, k, v)
                return
            target = {"building": p.building(oid), "subfield": next((s for s in p.subfields if s.id == oid), None),
                      "exclusion": next((e for e in p.exclusions if e.id == oid), None)}.get(kind)
            if target is None:
                return
            for path, value in changes.items():
                head, _dot, tail = path.partition(".")
                if not tail:
                    setattr(target, head, value)
                elif head == "params":
                    if value is None and tail == "azimuth":
                        target.params.pop("azimuth", None)
                    else:
                        target.params[tail] = value
                else:
                    setattr(getattr(target, head), tail, value)
        self.edit(_("Change {what}").format(what=", ".join(field_label(k, kind) for k in changes)), apply,
                  self._merge_key(("field", kind, oid), changes))

    @staticmethod
    def _merge_key(where: tuple, changes: dict):
        """The same number changed again (the arrows of a field): a key that joins those steps. A list, a
        choice or an outline is a step of its own."""
        if len(changes) != 1:
            return None
        (path, value), = changes.items()
        return (*where, path) if isinstance(value, (int, float)) and not isinstance(value, bool) else None

    def _action(self, what: str, kind: str, oid: str) -> None:
        if what.startswith("refused:"):
            self.hint.setText(_("Not changed: {why}").format(why=what.partition(":")[2]))
        elif what in ("pick_eave", "pick_gable") and self.project.building(oid) is not None:
            self.show_phase("model")
            self.plan.pick_edge(what[5:], "building", oid, self.project.building(oid).footprint)
        elif what == "site":
            self._find_site()
        elif what == "catalog_module":
            self._choose_module(oid)
        elif what in ("fill", "empty"):
            def set_filled(p):
                sf = next(s for s in p.subfields if s.id == oid)
                sf.filled = what == "fill"
                if what == "fill" and not sf.manual:      # by hand, the rows and what was taken out stay
                    sf.removed = []
            self.edit(_("Lay the modules") if what == "fill" else _("Take the modules out"), set_filled)
        elif what == "relayout":
            self._relayout_subfield(oid)
        elif what == "explode" and self.project_subfield(oid) is not None:
            self._row_edit(_("Explode the rows"), lambda r: manual.explode(self.project, oid, None, r), oid)

    def _edge_picked(self, purpose: str, kind: str, oid: str, side: int) -> None:
        """A side clicked on the plan: the eave of a mono-pitch roof; on a gable or hip roof, an eave that becomes
        a gable end or a gable end that becomes an eave (task 16a)."""
        if purpose == "align":
            found = self._outline(kind, oid)
            if found is not None:
                self.plan.align_to_side(found[1], side)
                self.hint.setText(_("The view is parallel to side {n}. «North up» brings it back; the project has "
                                    "not turned.").format(n=side + 1))
            return
        b = self.project.building(oid)
        if kind != "building" or b is None:
            return
        if purpose == "eave":
            self._edited("building", oid, {"roof.eave_side": side})
            self.hint.setText(_("Side {n} picked.").format(n=side + 1))
        elif purpose == "gable":
            edges = b.with_side(side)
            self._edited("building", oid, {"roof.edges": edges})
            self.hint.setText(_("Side {n} is a gable end now.").format(n=side + 1) if edges[side] == "gable" else
                              _("Side {n} is an eave now.").format(n=side + 1))

    def _outline(self, kind: str, oid: str) -> tuple[str, list] | None:
        if kind == "building" and self.project.building(oid) is not None:
            return "footprint", self.project.building(oid).footprint
        if kind == "pitch":
            bid, _sep, index = oid.partition(":")
            building = self.project.building(bid)
            pitches = building.pitches() if building is not None else []
            return ("ring", pitches[int(index)].ring) if index.isdigit() and int(index) < len(pitches) else None
        thing = (self.project_subfield(oid) if kind == "subfield" else
                 next((e for e in self.project.exclusions if e.id == oid), None) if kind == "exclusion" else None)
        return ("ring", thing.ring) if thing is not None else None

    def _side_clicked(self, kind: str, oid: str, side: int) -> None:
        """A double click on a side of the selected outline: its new length, the side stretched to it."""
        found = self._outline(kind, oid)
        if found is None:
            return
        path, ring = found
        now = sides.lengths(ring)[side]
        value, ok = QInputDialog.getDouble(self, _("Length of side {n}").format(n=side + 1),
                                           _("New length (m); what lies at the far end of the side moves with it:"),
                                           now, 0.1, 10000.0, 2)
        if not ok or abs(value - now) < 1e-6:
            return
        try:
            self._edited(kind, oid, {path: sides.stretch(ring, side, value)})
        except ValueError as error:
            self.hint.setText(_("Not changed: {why}").format(why=error))

    def _vertex_moved(self, kind: str, oid: str, vertex: int, x: float, y: float) -> None:
        """A corner of the selected outline dragged to (x, y): one undoable edit, refused if the outline would
        cross itself."""
        found = self._outline(kind, oid)
        if found is None:
            return
        path, ring = found
        moved = [list(map(float, q)) for q in ring]
        moved[vertex] = [round(x, 4), round(y, 4)]
        if not Polygon(moved).is_valid or Polygon(moved).area < 0.5:
            self.hint.setText(_("Not changed: {why}").format(why=_("the outline would cross itself or vanish")))
            return
        self._edited(kind, oid, {path: moved})

    def _find_site(self) -> None:
        if self.project.buildings or self.project.subfields:
            QMessageBox.information(self, _("Find the site"),
                                    _("The site can be moved only before anything is drawn: the drawing is measured "
                                      "from it. Start a new project for another site."))
            return
        from .site_dialog import SiteDialog
        dialog = SiteDialog(self.project.site, self, network=self.cfg.network_geocoding)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            site = dialog.result()
            self.edit(_("Move the site"), lambda p: setattr(p, "site", site))
            self.plan.set_origin(site.lat, site.lon)
            self.plan.fit()

    # drawing everything again

    def _relayout(self) -> None:
        """A layout asked for, after the short pause of the timer; the plan's arc from now, so that it shows only
        past the threshold from the change itself (study 16, F3)."""
        self.generation += 1
        self.relayout_timer.start()
        self.plan.set_laying(True)

    def _show_all(self, fit: bool = False) -> None:
        self.plan.set_origin(self.project.site.lat, self.project.site.lon)
        self._relayout()
        self.plan.show_project(self.project, {k: v for k, v in self.results.items() if not isinstance(v, Exception)})
        self._show_variants()
        self._show_tree()
        self._show_properties()
        self._show_measure()
        self._enable_layout_commands()
        self._title()
        self._show_energy_forms()
        if self.plan.draft is not None:
            self._end_draft()
        if hasattr(self, "plant_timer"):
            self.plant_state = None                 # another project: its plant comes with its layouts
            self._plant_soon()
        self._show_inspector()
        self._show_stale()
        self._show_skeleton()
        if fit:
            self.plan.fit()

    def _show_skeleton(self) -> None:
        """The buildings of the plan on the 3D's skeleton, while it is there."""
        if self.skeleton is not None:
            self.skeleton.set_buildings([(b.footprint, b.height) for b in self.project.buildings])

    def _skeleton_gone(self, why: str) -> None:
        self.skeleton = None

    def _enable_layout_commands(self) -> None:
        """«Lay the modules» and «Take the modules out» act on the selected sub-field: without one, greyed;
        «Lay again automatically» on one laid."""
        sf = self.project_subfield(self._selected_subfield())
        self.commands["fill"].setEnabled(sf is not None)
        self.commands["empty"].setEnabled(sf is not None and sf.filled)
        self.commands["refill"].setEnabled(sf is not None and sf.filled)

    def _selected_subfield(self) -> str:
        """The sub-field of the selection: the sub-field itself, or the one a row selected stands in."""
        kind, oid = self.selection
        if kind == "subfield":
            return oid
        if kind == "row":
            return oid.partition("/")[0]
        return ""

    def _start_layout(self) -> None:
        job = LayoutJob(self.generation, model.Project.from_json(self.snapshot(), check=False),
                        self.session.known_layouts())
        job.signals.done.connect(self._layout_done)
        self.layout_job = job                       # what it laid out, for the tests
        self.pool.start(job)

    def _layout_done(self, generation: int, results: dict, seconds: float, keys: dict) -> None:
        before = dict(self.session.results)
        if not self.session.layout_done(generation, results, keys):
            return                                  # a newer change is on its way
        # said only when a layout changed: a change that lays out nothing again (a string) keeps the bar's message
        laid = any(results.get(k) is not before.get(k) for k in set(results) | set(before))
        self.plan.set_laying(False)
        # the views of the sub-fields that changed followed the session's "layout:<id>"; the year is computed
        # again only when its inputs changed (the layouts, the energy settings: session.energy_key), or for
        # the first time when a page of the energy is in view
        if self.session.energy_stale() or (self.phase() != "model" and not self.energy):
            self.energy_timer.start()
        good = self.session.good_results()
        errors = [f"{k}: {v}" for k, v in results.items() if isinstance(v, Exception)]
        if errors:
            self.hint.setText(_("Some sub-fields could not be laid out: {what}").format(what="; ".join(errors)))
        elif good and laid:
            n = sum(r.count for r in good.values())
            self.statusBar().showMessage(ngettext("{n} module laid in {ms} ms", "{n} modules laid in {ms} ms", n).format(
                n=n, ms=round(seconds * 1000)), 4000)

    def _show_3d(self) -> None:
        """The scene of the 3D view in its own colours (view_colours, the same in both themes): what is selected
        tinted towards the selection's colour and outlined, as on the plan, so that the selection is one for both
        views (Daniel 23/10/2026, R29)."""
        self._show_skeleton()
        kind, oid = self.selection
        hot = view_colours.kind_colour("module" if self.selected_module[0] else kind)       # R67

        def tinted(colour, t):
            return view_colours.tinted(colour, t, hot)
        pos_all, nor_all, col_all = [], [], []
        for b in self.project.buildings:
            colours = None
            if kind == "building" and oid == b.id:
                colours = {"wall": tinted(mesh.WALL, 0.3), "roof": tinted(mesh.ROOF_PITCH, 0.45),
                           "roof_flat": tinted(mesh.ROOF_FLAT, 0.45)}
            try:
                pos, nor, col = mesh.building_triangles(b.footprint, b.pitches(), colours)
            except (ValueError, IndexError) as error:
                log.complain(f"mesh of {b.id}", error)
                continue
            pos_all.append(pos)
            nor_all.append(nor)
            col_all.append(col)
        for o in self.project.obstacle_prisms():
            colour = {"tree": mesh.TREE, "parapet": mesh.WALL}.get(o["kind"], mesh.OBSTACLE)
            if kind == "exclusion" and o["id"] == oid and o["kind"] != "parapet":
                colour = tinted(colour, 0.6)
            pos, nor, col = mesh.prism_triangles(o["ring"], o["z0"], o["z1"], colour)
            pos_all.append(pos)
            nor_all.append(nor)
            col_all.append(col)
        cat = (np.concatenate(pos_all) if pos_all else np.zeros((0, 3), np.float32),
               np.concatenate(nor_all) if nor_all else np.zeros((0, 3), np.float32),
               np.concatenate(col_all) if col_all else np.zeros((0, 3), np.float32))
        tables = []
        self.module_index = []
        selected = tuple(self.selected_module)
        kept = {}
        for sf in self.project.subfields:
            r = self.results.get(sf.id)
            if r is None or isinstance(r, Exception) or not sf.filled:
                continue
            along, across = jobs.module_sides(self.project, sf)
            entry = self.module_tables.get(sf.id)
            if entry is None or entry["result"] is not r or entry["size"] != (along, across):
                # the table of this layout once (made in the layout's thread, jobs.prepared, or here for a
                # layout that came another way), and its rows by module key: a selection changes the colours
                # only (task 18c, steps 7 and 8: 35-65 ms a click on 4,682 modules before)
                keys = r.keys if r.keys is not None else [pm.key for pm in r.modules]
                table = r.table if r.table is not None and len(r.table) == r.count else mesh.module_table(
                    r.modules, along, across)
                entry = {"result": r, "size": (along, across), "table": table,
                         "rows": {k: i for i, k in enumerate(keys)}, "index": [(sf.id, k) for k in keys]}
            kept[sf.id] = entry
            sel = {entry["rows"][selected[1]]} if selected[0] == sf.id and selected[1] in entry["rows"] else set()
            if kind == "row" and oid.partition("/")[0] == sf.id:          # a row selected: its modules (16c)
                rid = oid.partition("/")[2]
                sel = {i for i, m in enumerate(r.modules) if m.rid == rid}
            hot_field = kind == "subfield" and oid == sf.id and not selected[0]
            colour = tinted(mesh.MODULE, 0.35) if hot_field else mesh.MODULE
            tables.append(mesh.recoloured(entry["table"], colour, sel, mesh.rgb(hot)) if (hot_field or sel)
                          else entry["table"])
            self.module_index.extend(entry["index"])
        self.module_tables = kept
        table = np.concatenate(tables) if tables else np.zeros((0, 20), np.float32)
        self.sunbar.set_site(self.project.site.lat, self.project.site.lon, self.project.sun_window)
        pos = self.sunbar.position()
        if pos is not None:
            self.view3d.set_sun(pos.apparent, pos.bearing)
        self.view3d.show_scene(cat, table)
        self._outline_3d()
        self._show_gizmo()

    def _outline_3d(self) -> None:
        """The outline of the selection and of what is under the pointer in the 3D view (viewaids.outline)."""
        kind, oid = self.selection
        if self.selected_module[0]:
            select = viewaids.outline(self.project, self.results, "module", *self.selected_module)
        elif kind == "site":
            select = np.zeros((0, 2, 3))
        else:
            select = viewaids.outline(self.project, self.results, kind, oid)
        h = self.hovered_3d
        same = h[:2] == (kind, oid) if h[0] != "module" else tuple(h[1:]) == tuple(self.selected_module)
        hover = viewaids.outline(self.project, self.results, *h) if h[0] and not same else np.zeros((0, 2, 3))
        # the colours of the kinds (R67): the selection's and the lighter one of what is under the pointer
        self.view3d.set_outline(select, hover, view_colours.kind_colour("module" if self.selected_module[0] else kind),
                                view_colours.kind_colour(h[0] or "", hover=True))

    def _hover_3d(self, what: tuple) -> None:
        """What a click in the 3D view would select, outlined lighter: a module, its row on the second click,
        anything else as the plan would pick it at that point."""
        from .plan import to_scene
        found = ("", "", "")
        if what[0] == "module" and 0 <= what[1] < len(self.module_index):
            sfid, key = self.module_index[what[1]]
            rid = self._repeated_row(sfid, key)
            found = ("row", f"{sfid}/{rid}", "") if rid else ("module", sfid, key)
        elif what[0] == "point":
            kind, oid, key = self.plan._pick(to_scene(what[1], what[2]))
            if kind == "pitch":
                kind, oid = "building", oid.split(":")[0]
            found = (kind, oid, key)
        if found != self.hovered_3d:
            self.hovered_3d = found
            self._outline_3d()

    def _show_tree(self) -> None:
        """The project's tree: each object with the icon of its kind and its name (exclusions by kind and number,
        «Skylight 2»), the marks of the checks in the second column; the scroll and the selection stay through a
        rebuild, and the selection is the plan's and the 3D view's (study 12, N3)."""
        from .properties import exclusion_names
        scroll = self.tree.verticalScrollBar().value()
        self.tree.blockSignals(True)
        self.tree.clear()

        def item(parent, text, kind, oid, icon_name=""):
            it = QTreeWidgetItem(parent, [text, ""])
            it.setData(0, Qt.ItemDataRole.UserRole, (kind, oid))
            if icon_name:
                # the icon in its kind's colour, as the selection on the plan (R67)
                it.setIcon(0, icons.icon(icon_name, view_colours.kind_ink(kind, self.theme.dark)))
            return it

        root = item(self.tree, self.project.name, "site", "", "site")
        root.setToolTip(0, _("Site: {name}").format(name=self.project.name))

        def group(text, kind, n):
            # a section's header (study 17, T2): drawn by SectionDelegate, never selected; its marks gather
            # what is inside (_mark_tree, by the order of the sections)
            it = section(root, text, n)
            it.setData(0, Qt.ItemDataRole.UserRole, ("group", kind))
            return it

        bs = group(_("Buildings"), "building", len(self.project.buildings))
        for b in self.project.buildings:
            item(bs, b.name, "building", b.id, "building")
        ss = group(_("Sub-fields"), "subfield", len(self.project.subfields))
        for s in self.project.subfields:
            r = self.results.get(s.id)
            state = self.project.layout_state(s, self.layout_keys, self.results)
            count = f" · {r.count}" if state == "ok" else " · …" if state == "stale" else ""
            it = item(ss, s.name + count, "subfield", s.id, "subfield")
            if count:
                it.setData(0, TAIL_ROLE, count)            # the modules laid, drawn muted beside the name
            if state == "stale":
                it.setToolTip(0, _("To lay out again: it changed after its layout"))
            elif state == "error":
                # the mark of what is to fix, drawn: the «✘» of the name is not in Inter, and the first
                # character Qt looks for elsewhere costs it 1-2 s on Windows (review, 23/10/2026)
                it.setIcon(0, mark_icon("fail"))
                it.setToolTip(0, _("The layout failed: {why}").format(why=r))
        es = group(_("Exclusions"), "exclusion", len(self.project.exclusions))
        names, numbers = exclusion_names(), self.project.exclusion_numbers()
        for e in self.project.exclusions:
            it = item(es, f"{names.get(e.kind, e.kind)} {numbers[e.id]}", "exclusion", e.id, "exclusion")
            it.setToolTip(0, e.id)
        self.tree.expandAll()
        self._mark_tree()
        self._tree_select()
        self.tree.blockSignals(False)
        self.tree.verticalScrollBar().setValue(scroll)

    def _tree_select(self) -> None:
        """The tree shows what is selected in the views, without saying so back to them (a row: its sub-field)."""
        target = ("subfield", self._selected_subfield()) if self.selection[0] == "row" else tuple(self.selection)
        found = None
        it = self.tree.topLevelItem(0)
        stack = [it] if it is not None else []
        while stack:
            node = stack.pop()
            if tuple(node.data(0, Qt.ItemDataRole.UserRole) or ()) == target and target[0] != "site":
                found = node
                break
            stack.extend(node.child(i) for i in range(node.childCount()))
        blocked = self.tree.blockSignals(True)
        self.tree.setCurrentItem(found) if found is not None else self.tree.clearSelection()
        self.tree.blockSignals(blocked)

    def _show_properties(self) -> None:
        kind, oid = self.selection
        if kind == "row":                           # a row shows its sub-field's (task 16c)
            kind, oid = "subfield", self._selected_subfield()
        if kind == "building" and self.project.building(oid):
            self.props.show_building(self.project.building(oid))
        elif kind == "subfield" and self.project_subfield(oid):
            r, sf = self.results.get(oid), self.project_subfield(oid)
            state = self.project.layout_state(sf, self.layout_keys, self.results)
            self.props.show_subfield(self.project, sf, None if isinstance(r, Exception) else r, state,
                                     str(r) if isinstance(r, Exception) else "")
        elif kind == "exclusion" and any(e.id == oid for e in self.project.exclusions):
            self.props.show_exclusion(next(e for e in self.project.exclusions if e.id == oid))
        else:
            self.props.show_site(self.project, not (self.project.buildings or self.project.subfields))

    # energy

    def _show_energy_forms(self) -> None:
        good = {k: v for k, v in self.results.items() if not isinstance(v, Exception)}
        try:
            arrays = system.arrays_of(self.project, good)
        except (ValueError, KeyError) as error:
            log.complain("arrays", error)
            self.tell(_("The plant could not be read for the energy pages: {error}").format(error=error))
            arrays = []
        self.energy_page.show_project(self.project, arrays)
        if hasattr(self, "plant_page"):
            self.plant_page.show_inverter(system.describe(self.project.energy))
            self.inverter_reference.show_energy(self.project.energy)
        ctx = consumption_model.Context(p_stc_kw=sum(a.p_stc for a in arrays) / 1000.0)
        sim = (self.energy or {}).get("sim")
        if sim is not None and abs(sim.p_stc_kw - ctx.p_stc_kw) < 1e-6:
            ctx.production_kwh = sim.energy_kwh
        self.consumption_page.show_project(self.project, ctx)
        self.economics_page.show_project(self.project)

    def _tab_changed(self, index: int) -> None:
        """Another phase open: the year computed if a phase of the results asks for it and there is none, the
        inspector, the side bar, the menu's mark, «This phase» of the Checks and the assistant's place follow
        (phases.py)."""
        pid = self.phase()
        if pid == "plant":
            self._lend_plan()
        else:
            self._return_plan()
        if pid not in ("model", "plant"):
            charts.preload()                    # matplotlib in its thread, for the charts about to be shown
        if pid != "model" and not self.energy:
            self._compute_energy(fetch=False)
        self._show_inspector()
        if hasattr(self, "bars"):
            self._fill_side_bar()
            self.phase_actions[pid].setChecked(True)
        self.checks_page.set_phase(pid)             # what «This phase» keeps in the Checks panel
        self.assistant.set_tab(pid)
        self._phase_panels(pid)

    def _phase_panels(self, pid: str) -> None:
        """Project only where there is a drawing; when it returns, the two side panels get the same width."""
        project = self.docks[0]
        if pid not in ("model", "plant"):
            if project.isVisible():
                self.project_was_visible = True
                self.project_auto_hidden = True
                project.hide()
            elif not self.project_auto_hidden:
                self.project_was_visible = False
            return
        if self.project_auto_hidden:
            project.setVisible(self.project_was_visible)
            self.project_auto_hidden = False
        if project.isVisible() and self.docks[1].isVisible():
            width = max(project.width(), self.docks[1].width())
            self.resizeDocks([project, self.docks[1]], [width, width], Qt.Orientation.Horizontal)

    def _lend_plan(self) -> None:
        """The plan into the Plant page, with the strings always shown (study 16, D.6: W is always on there); the
        split of the model kept as it was, for the way back."""
        if not hasattr(self, "plant_page") or self.plant_page.plan is not None:
            return
        self.split_home = self.split.saveState()
        if self.plan.tool != "select":              # the Plant phase draws strings, not outlines
            self.tool_actions["select"].setChecked(True)
            self.plan.set_tool("select")
        self.plant_page.lend(self.plan)
        self.plan.show_wiring(True)
        self.plan.set_strings_mode(True)
        if self.plant_state is None:
            self._plant_soon()

    def _return_plan(self) -> None:
        """The plan back beside the 3D view, as the view mode and the split were; the strings as W says."""
        if not hasattr(self, "plant_page") or self.plant_page.plan is None:
            return
        self._end_draft()
        self.plan.set_strings_mode(False)
        self.chosen_string = -1
        self.plan.choose_string(-1)
        self.split.insertWidget(0, self.plan)
        if self.split_home is not None:
            self.split.restoreState(self.split_home)
        self.split_home = None
        self.plant_page.returned()
        self.plan.setVisible(self.current_view in ("plan", "both"))
        self.plan.show_wiring(self.commands["strings"].isChecked())

    def _show_inspector(self) -> None:
        """The right panel as the phase wants it (phases.Phase.inspector): the properties of what is selected, the
        inverters of the plant, the figures of the variant in hand, or the deliverables with their state."""
        if not hasattr(self, "inspector"):
            return
        phase = phases.by_id(self.phase())
        self.inspector.set_kind(phase.inspector, phase.id)
        title = {"results": _("Results"), "deliverables": _("Deliverables"),
                 "plant": _("Inverters")}.get(phase.inspector, _("Properties"))
        if phase.inspector == "results" and phase.id in self.inspector.sides:
            title = _("Data")                       # what is typed in the phase (the drafts of 24/10/2026)
        self.docks[1].setWindowTitle(title)
        if phase.inspector == "plant":
            self.plant_inspector.colours = list(self.plan.string_colours)
            self.plant_inspector.show_plant(self.project, self.plant_state, self.selection, self.chosen_string)
        if phase.inspector == "results":
            self.inspector.results.show_results(phase.title, [(v["id"], v["name"]) for v in self.project.variants],
                                                self.project.variant, self.energy)
        elif phase.inspector == "deliverables":
            ready = bool(self.energy) and self.energy.get("sim") is not None
            self.inspector.deliverables.show_deliverables(phases.deliverables(ready, self.exports, self._state_key()),
                                                          self.commands)
            data = self._report_data() if ready else {}
            from .report import _with_notes
            self.report_side.show_settings(self.project, _with_notes(data) if ready else data,
                                           self.cfg.report_profiles, self.cfg.report_profile,
                                           str(self.path.parent) if self.path else self.cfg.last_folder)
            self.report_page.set_ready(ready or bool(self.report_page.preview.images))
            if ready:
                self.preview_soon.start()

    def _compute_energy(self, fetch: bool) -> None:
        if fetch and not self.cfg.network_pvgis:
            self.tell(_("PVGIS is off in Preferences > Privacy: computing with the weather already in the cache."))
            fetch = False
        job = EnergyJob(self.session.energy_asked(), self.snapshot(), self.session.good_results(), self.paths.cache,
                        fetch)
        job.signals.done.connect(self._energy_done)
        job.signals.step.connect(self._energy_step)
        self.energy_job = job
        text = _("Computing…") if not fetch else _("Fetching the weather and computing…")
        self.energy_page.status.setText(text)
        # said where the designer is, not only on the production page: the window keeps answering meanwhile
        self.busy.setText(_("Production: {what}").format(what=text))
        self._computing(True, fetch)
        self.pool.start(job)

    def _computing(self, on: bool, fetch: bool = False) -> None:
        """The year on its way (on) or back (off): the arc on the energy pages and, in the status bar, the words or,
        when PVGIS is asked, the bar with its percentage and Cancel; all of it only past the threshold (study 16,
        F3 and F4; design 3.10, 3.12)."""
        if on and fetch:
            self.busy_wait.end()
            self.pvgis_progress.begin(_("PVGIS: {what}").format(what=_("the typical year")))
        elif on:
            self.pvgis_progress.end()
            self.busy_wait.begin()
        else:
            self.busy_wait.end()
            self.pvgis_progress.end()
        for page in (self.energy_page, self.consumption_page, self.economics_page):
            page.set_computing(on)

    def _energy_step(self, generation: int, done: int, total: int, what: str) -> None:
        """A step of the year awaited: the bar of PVGIS moves (pipeline.STEPS: the typical year, the horizon, the year
        hour by hour, PVGIS's estimate)."""
        if generation == self.energy_generation and self.pvgis_progress.running():
            self.pvgis_progress.set(done / total, _("PVGIS: {what} ({n} of {total})").format(
                what=what, n=done + 1, total=total))

    def _cancel_pvgis(self) -> None:
        """Cancel on the bar of PVGIS: the year asked for is awaited no longer (its generation passed) and its job stops
        before its next request; the project and the year in hand stay as they were."""
        if self.energy_job is not None:
            self.energy_job.interrupt()
        self.energy_generation += 1
        self._computing(False)
        said = _("PVGIS stopped: the values are those of the last computation.")
        self.energy_page.status.setText(said)
        self.statusBar().showMessage(said, 6000)

    def _energy_done(self, generation: int, out: dict) -> None:
        if not self.session.energy_done(generation, out):
            return
        self._computing(False)
        if out.get("meteo_text"):
            self.energy_page.show_meteo(out["meteo_text"])
        self.energy_page.show_results(out.get("sim"), out.get("pvgis"), out.get("error_sim", ""))
        self.energy_page.show_strings(out.get("strings") or {}, out.get("sim"))
        # the strings on the plan are the live plant's (_plant_done), which follows the year's "energy" topic
        if out.get("notes") and out.get("sim") is not None:
            self.energy_page.status.setText("\n".join([*out["sim"].notes, *out["notes"]]))
        if out.get("context") is not None:
            self.consumption_page.show_project(self.project, out["context"])
        self.consumption_page.show_results(out.get("load"), out.get("error_load", ""))
        self.economics_page.show_results(out.get("econ"), out.get("error_sim", "") if out.get("econ") is None else "")
        sim = out.get("sim")
        self.economics_page.show_sizing(out.get("sizing"), out.get("storage"), sim.p_stc_kw if sim is not None else 0.0,
                                        float(out.get("battery_kwh") or 0.0))
        self._show_inspector()                      # the checks followed the session's "checks"

    def _show_checks(self) -> None:
        good = {k: v for k, v in self.results.items() if not isinstance(v, Exception)}
        try:
            arrays = system.arrays_of(self.project, good)
            inverter = (system.combined(system.inverters_of(self.project, sum(a.p_stc for a in arrays)))
                        if arrays else None)
        except (ValueError, KeyError) as error:
            log.complain("checks", error)
            self.tell(_("The plant could not be read for the checks: {error}").format(error=error))
            arrays, inverter = [], None
        items = checks.gather(self.project, self.results, self.energy, inverter,
                              bool(system.inverter_entries(self.project.energy)))
        items += checks.plant_items(self.plant_state)          # the live ones (task 16d), not the year's
        items.sort(key=lambda i: checks.LEVELS.index(i.level))
        from .checks_page import object_names
        self.checks_page.show_items(items, checks.defaults_in_use(self.energy), object_names(self.project))
        self._checks_title()
        self._show_marks()

    def _checks_view_changed(self, view: str) -> None:
        """The view chosen in the head of the Checks panel, kept in the settings."""
        self.cfg.checks_view = view
        self._save_config()

    def _show_marks(self) -> None:
        """The checks on the views (study 12, C1, C3): a mark on each object they are about, in the plan and in 3D,
        on the tree rising to the groups, and the counts in the status bar."""
        items = self.checks_page.items
        plan_marks, marks_3d = [], []
        for (kind, oid), m in checks.marks(items).items():
            at = viewaids.anchor(self.project, kind, oid)
            if at is None:
                continue
            x, y, z = at
            plan_marks.append((x, y, m.level, m.count, (kind, oid)))
            marks_3d.append((mesh.to_qt(x, y, z + 0.6), m.level, m.count, (kind, oid)))
        self.plan.set_marks(plan_marks)
        self.view3d.marks.set_marks(marks_3d)
        self._mark_tree()
        n = checks.counts(items)
        from .checks_page import level_names
        from .marks import icon as mark_icon
        for level, b in self.count_buttons.items():
            if b.icon().isNull():                   # the mark drawn, as on the Checks' counts (R121)
                b.setIcon(mark_icon(level))
                b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setText(str(n[level]))
            b.setVisible(n[level] > 0)
            b.setToolTip(_("{n} {level}: a click leads to their section in the Checks panel").format(
                n=n[level], level=level_names()[level]))

    def _mark_tree(self) -> None:
        """The marks of the checks in the tree's second column (R30): drawn by MarkDelegate at the screen's density,
        what they count in the tooltip, a click to the checks of that object."""
        from .marks import MARK_ROLE
        items = self.checks_page.items
        marks = checks.tree_marks(items)
        groups = ("building", "subfield", "exclusion")      # the root's children, in their order

        def mark(it, key):
            m = marks.get(key)
            it.setData(1, MARK_ROLE, (m.level, m.count) if m else None)
            it.setData(1, Qt.ItemDataRole.UserRole, key if m else None)
            it.setToolTip(1, checks.mark_text(items, m, inside=key[0] in ("site", "group")) +
                          "\n" + _("A click: these checks in the panel below") if m else "")
        root = self.tree.topLevelItem(0)
        if root is None:
            return
        mark(root, ("site", ""))
        for g in range(root.childCount()):
            group = root.child(g)
            mark(group, ("group", groups[g] if g < len(groups) else ""))
            for c in range(group.childCount()):
                child = group.child(c)
                k, oid = child.data(0, Qt.ItemDataRole.UserRole) or ("", "")
                mark(child, (k, oid))

    # context menus (study 12, N4)

    def context_actions(self, kind: str, oid: str, key: str = "") -> list:
        """What the right button offers on an object: (text, what it does), the same in the plan, the 3D view and
        the tree; None for a separator."""
        out = [(_("Properties"), lambda: (self.docks[1].show(), self.docks[1].raise_())),
               (_("Frame it"), self._fit)]
        if kind == "row" or (kind == "subfield" and key):
            out += self._row_actions(kind, oid, key)
        if kind == "subfield":
            sf = self.project_subfield(oid)
            if key:
                out.append((_("Take this module out"), self._delete))
            if sf is not None and sf.manual:
                out.append((_("Lay again automatically"), lambda: self._action("relayout", "subfield", oid)))
            else:
                out.append((_("Lay again") if sf is not None and sf.filled else _("Lay the modules"),
                            lambda: self._action("fill", "subfield", oid)))
            if sf is not None and sf.filled:
                out.append((_("Explode the rows"), lambda: self._action("explode", "subfield", oid)))
                out.append((_("Take the modules out"), lambda: self._action("empty", "subfield", oid)))
        if kind == "building":                      # the roof whole, without drawing it (R64)
            out.append((_("A sub-field on each pitch"), lambda: self._subfields_on_pitches(oid)))
        if kind in ("building", "subfield", "exclusion"):
            out.append(None)
            if kind != "exclusion":
                out.append((_("Rename…"), lambda: self._rename(kind, oid)))
            out.append((_("Duplicate"), lambda: self._duplicate(kind, oid)))
            out.append((_("Square the corners"), self._square))
            out.append(None)
            out.append((_("Delete"), self._delete))
        return out

    def _popup(self, kind: str, oid: str, key: str, where) -> None:
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)
        for entry in self.context_actions(kind, oid, key):
            if entry is None:
                menu.addSeparator()
            else:
                menu.addAction(entry[0]).triggered.connect(lambda _c=False, f=entry[1]: f())
        self.context_menu = menu                    # kept, for the tests
        menu.popup(where)

    def _object_at_plan(self, kind: str, oid: str, key: str) -> tuple[str, str, str]:
        """Select what was clicked with the right button, as the left one would, and say what it is."""
        if kind == "module":
            self.plan.selected_module = (oid, key)
            self.plan.set_selection("subfield", oid)
            self._module_clicked(oid, key)
            return "subfield", oid, key
        if kind == "pitch":
            kind, oid = "building", oid.split(":")[0]
        self.plan.selected_module = self.selected_module = ("", "")
        self._select(kind or "site", oid)
        return kind or "site", oid, ""

    def _plan_menu(self, pos) -> None:
        if self.plan.drawing():                     # while drawing: the drawing's menu, «Close» first (R41)
            from PySide6.QtWidgets import QMenu
            menu = QMenu(self)
            close = menu.addAction(_("Close the outline"), self.plan.close_outline)
            close.setEnabled(len(self.plan.chain) >= 3)
            menu.addAction(_("Remove the last point (Backspace)"), self.plan.drop_last)
            menu.addSeparator()
            menu.addAction(_("Cancel the drawing (Esc)"), self.plan.cancel_outline)
            self.context_menu = menu
            menu.popup(self.plan.viewport().mapToGlobal(pos))
            return
        kind, oid, key = self.plan._pick(self.plan.mapToScene(pos))
        kind, oid, key = self._object_at_plan(kind, oid, key)
        self._popup(kind, oid, key, self.plan.viewport().mapToGlobal(pos))

    def _view3d_menu(self, x: float, y: float) -> None:
        from PySide6.QtCore import QPoint

        from .plan import to_scene
        hit, name, index = self.view3d.backend._press or (None, "", -1)
        if name == "modules" and 0 <= index < len(self.module_index):
            sfid, key = self.module_index[index]
            kind, oid, key = self._object_at_plan("module", sfid, key)
        elif hit is not None:
            kind, oid, key = self._object_at_plan(*self.plan._pick(to_scene(float(hit[0]), -float(hit[2]))))
        else:
            kind, oid, key = self._object_at_plan("", "", "")
        self._popup(kind, oid, key, self.view3d.mapToGlobal(QPoint(int(x), int(y))))

    def _tree_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if item is None:
            return
        kind, oid = item.data(0, Qt.ItemDataRole.UserRole) or ("site", "")
        if kind == "group":                         # a section's header has no object
            return
        self._select(kind, oid)
        self._popup(kind, oid, "", self.tree.viewport().mapToGlobal(pos))

    def _rename(self, kind: str, oid: str, name: str | None = None) -> None:
        thing = self.project.building(oid) if kind == "building" else self.project_subfield(oid)
        if thing is None:
            return
        if name is None:
            name, ok = QInputDialog.getText(self, _("Rename"), _("Name:"), text=thing.name)
            if not ok:
                return
        if name.strip() and name.strip() != thing.name:
            self._edited(kind, oid, {"name": name.strip()})

    def _duplicate(self, kind: str, oid: str) -> None:
        made = []
        self.edit(_("Duplicate"), lambda p: made.append(p.duplicate(kind, oid)))
        if made:
            self._select(kind, made[0])

    def _focus_check(self, target: tuple) -> None:
        """The eye of a check, or Enter on it (R127: «l'occhio non porta direttamente alla vista 2d / 3d dove si
        trova il problema»): its object selected and framed in the plan and in the 3D view, the rest dimmed
        (Navisworks, PVsyst), from the Model phase when the phase shown has no views; a phase's problem, that
        phase; the site, the site."""
        if len(target) >= 2 and target[0] in checks.OBJECTS:
            if self.phase() not in ("model", "plant"):
                self.show_phase("model")
            self._select(target[0], target[1])
            self.plan.focus(target)
            self.plan.frame_target(target)
            self._frame_3d(target[0], target[1])
        else:
            self.plan.focus(None)
            self._navigate(tuple(target))

    def _frame_3d(self, kind: str, oid: str) -> None:
        """An object framed in the 3D view: a sphere round its outline, at its height."""
        found, centre = self._outline(kind, oid), self._centre_3d(kind, oid)
        if found is None or centre is None or not len(found[1]):
            return
        ring = np.asarray([(float(q[0]), float(q[1])) for q in found[1]])
        radius = float(np.hypot(*(ring - ring.mean(axis=0)).T).max())
        self.view3d.backend.frame_part(centre, max(radius * 1.15, 4.0))

    def _mark_clicked(self, kind: str, oid: str) -> None:
        """A mark on the plan: its object selected and its items found in the panel of the checks."""
        self._select(kind, oid)
        self.checks_dock.show()
        self.checks_dock.raise_()

    def _show_level(self, level: str) -> None:
        """A count of the status bar: the section of that level in the Checks panel, with the keyboard on it."""
        self._focus_checks()
        self.checks_page.go_to(level)

    def _navigate(self, target: tuple) -> None:
        kind = target[0] if target else ""
        if kind == "phase":
            self.show_phase(target[1])
        elif kind in ("subfield", "building", "exclusion"):
            self.show_phase("model")
            self._select(kind, target[1])
        elif kind == "site":
            self.show_phase("model")
            self._select("site", "")

    def _fix(self, item) -> None:
        """«Fix…» on a check (R126: «"correggi" dovrebbe presentare le correzioni proposte prima di applicarle
        all'istante»): an edit is made at once as a preview, with the views on its place, and the Checks panel asks
        Keep or Take back (taken back, it leaves no redo); what is not an edit (a computation) waits for Apply."""
        fix = tuple(item.fix or ())
        if not fix:
            return
        self._end_fix_preview(True)                 # one shown before and still open is kept
        if fix[0] == "compute":
            self.fix_waiting = item
            self.checks_page.show_preview(item.fix_label, applied=False)
            return
        undo = self.session.undo
        top = undo.steps[undo.index - 1] if undo.can_undo() else None
        self._apply_fix(fix, ask=False)             # the preview is the question: no message box before it
        new = undo.steps[undo.index - 1] if undo.can_undo() else None
        if new is None or new is top or undo.can_redo():
            self.checks_page.end_preview()
            self.tell(_("The fix «{fix}» changed nothing.").format(fix=item.fix_label))
            return
        self.fix_preview = new
        self._focus_check(tuple(item.target))
        self.checks_page.show_preview(item.fix_label, applied=True)

    def _fix_answered(self, keep: bool) -> None:
        """Keep or Take back on a fix in preview; Apply or Cancel on one that waited."""
        if self.fix_waiting is not None:
            item, self.fix_waiting = self.fix_waiting, None
            self.checks_page.end_preview()
            if keep:
                self._apply_fix(tuple(item.fix), ask=True)
            return
        self._end_fix_preview(keep)

    def _end_fix_preview(self, keep: bool) -> None:
        step, self.fix_preview, self.fix_waiting = self.fix_preview, None, None
        if step is None:
            self.checks_page.end_preview()
            return
        undo = self.session.undo
        if not keep and undo.can_undo() and undo.steps[undo.index - 1] is step and not undo.can_redo():
            undo.take_back()
            self.checks_page.end_preview()
            self.tell(_("Fix taken back: the project is as it was."))
        else:
            self.checks_page.end_preview()
            self.tell(_("Fix kept: Ctrl+Z undoes it like any change."))

    def _undo_moved(self) -> None:
        """A fix in preview stays one while it is the last step done: anything done, undone or redone after it
        ends the preview, the fix kept (or undone by Ctrl+Z, like any step)."""
        step = self.fix_preview
        if step is None:
            return
        undo = self.session.undo
        if undo.can_undo() and undo.steps[undo.index - 1] is step and not undo.can_redo():
            return
        self.fix_preview = None
        self.checks_page.end_preview()
        self.tell(_("Fix kept: Ctrl+Z undoes it like any change.") if step in undo.steps[:undo.index] else
                  _("Fix undone."))

    def _apply_fix(self, fix: tuple, ask: bool = True) -> None:
        """Apply the fix of a check: an edit (undoable like any other) or what a button would do."""
        if fix[0] == "energy":
            self._energy_edited("energy", fix[1], fix[2])
        elif fix[0] == "edit":
            self._edited(fix[1], fix[2], dict(fix[3]))
        elif fix[0] == "action" and fix[1] == "relayout":
            self._relayout_subfield(fix[3], ask=ask)
        elif fix[0] == "action":
            self._action(fix[1], fix[2], fix[3])
        elif fix[0] == "compute":
            self._compute_energy(fetch=True)
        elif fix[0] == "command" and fix[1] in self.commands:
            self.commands[fix[1]].trigger()

    def _rules_facts(self) -> rules.Facts:
        good = {k: v for k, v in self.results.items() if not isinstance(v, Exception)}
        try:
            arrays = system.arrays_of(self.project, good)
            inverter = (system.combined(system.inverters_of(self.project, sum(a.p_stc for a in arrays)))
                        if arrays else None)
        except (ValueError, KeyError) as error:
            log.complain("rules", error)
            self.tell(_("The plant could not be read for the rules: {error}").format(error=error))
            inverter = None
        return rules.facts(self.project, self.results, self.energy, inverter)

    def _report_notes(self) -> str:
        """The notes of the rules that apply, as text for the technical report."""
        return rules.notes_text(self._rules_facts())

    def _energy_edited(self, section: str, path: str, value) -> None:
        self.edit(_("Change {what}").format(what=field_label(path.split(".")[-1])),
                  lambda p: set_path(getattr(p, section), path, value), self._merge_key((section,), {path: value}))

    def _export_report(self) -> None:
        if not self.energy or self.energy.get("sim") is None:
            QMessageBox.information(self, _("Export the report"), _("Compute the production first (the Production "
                                                                    "page): the report shows its results."))
            return
        if self.report_run is not None:
            self.tell(_("A report is being written: wait for it, or Cancel it in the status bar."))
            return
        from .. import reports
        from . import report
        left = [a for a in report.attachments(self.project) if a.problem]
        if left:
            lines = chr(10).join(f"• {a.title}: {a.problem}" for a in left)
            answer = QMessageBox.warning(
                self, _("Export the report"),
                ngettext("This attachment cannot go in the report:", "These attachments cannot go in the report:",
                         len(left)) + chr(10) + lines + chr(10) * 2 +
                ngettext("Export the report leaving it out?", "Export the report leaving them out?", len(left)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Yes:
                return
        start = str(Path(self.cfg.last_folder or Path.home()) / (self.project.name + ".pdf"))
        name, _f = QFileDialog.getSaveFileName(self, _("Export the report"), start, _("PDF files (*.pdf)"))
        if not name:
            return
        path = Path(name if name.lower().endswith(".pdf") else name + ".pdf")
        # the project as it is now (a copy: the designer goes on working while the report is written)
        project = model.Project.from_json(self.snapshot(), check=False)
        data, profile = self._report_data(), self._report_profile()
        steps = report.export_steps(project, data, path, profile)
        self.report_register = reports.settings(project)["register"]
        if self.report_register:
            steps = report.with_register(steps, project, data, path, profile)
        self.report_run = (steps, path, self._state_key())
        self.report_progress.begin(_("Report"))
        QTimer.singleShot(0, self, self._report_step)

    def _report_step(self) -> None:
        """One step of the report (an image, a page: report.export_steps), then the window's events, then the next:
        the bar moves and Cancel is heard between two steps (study 16, F4), never a modal window."""
        if self.report_run is None:
            return                                  # cancelled meanwhile
        steps, path, state = self.report_run
        try:
            fraction, what = next(steps)
        except StopIteration:
            self.report_run = None
            self.report_progress.end()
            self.exports["report"] = (path.name, time.strftime("%d/%m/%Y %H:%M"), state)
            if self.report_register:                # the hourly series went beside it (report.register_steps)
                from . import report
                self.exports["csv"] = (report.register_paths(path)[0].name, time.strftime("%d/%m/%Y %H:%M"), state)
            self._show_inspector()
            done = (_("Report and register of the calculations written: {file}") if self.report_register else
                    _("Report written: {file}"))
            self.statusBar().showMessage(done.format(file=path.name), 6000)
            return
        except Exception as error:                  # noqa: BLE001 (said to the designer and kept in the log)
            self.report_run = None
            self.report_progress.end()
            if not isinstance(error, OSError):
                log.complain("report", error)
            QMessageBox.warning(self, _("Export the report"), _("The report could not be written: {error}").format(
                error=error))
            return
        self.report_progress.set(fraction, _("Report: {what}").format(what=what))
        QTimer.singleShot(0, self, self._report_step)

    def _export_csv(self) -> None:
        """The register of the calculations on its own: the typical year hour by hour as a CSV file, its header
        saying each column's unit and source (energy/register.py)."""
        if not self.energy or self.energy.get("sim") is None:
            QMessageBox.information(self, _("Export the hourly series"), _("Compute the production first (the "
                                                                          "Production page): the series is its year."))
            return
        from . import report
        start = report.register_paths(Path(self.cfg.last_folder or Path.home()) / (self.project.name + ".pdf"))[0]
        name, _f = QFileDialog.getSaveFileName(self, _("Export the hourly series"), str(start),
                                               _("CSV files (*.csv)"))
        if not name:
            return
        path = Path(name if name.lower().endswith(".csv") else name + ".csv")
        try:
            report.write_register_csv(self.project, self._report_data(), path)
        except OSError as error:
            QMessageBox.warning(self, _("Export the hourly series"), _("{file} could not be written: {error}").format(
                file=path.name, error=error))
            return
        self.exports["csv"] = (path.name, time.strftime("%d/%m/%Y %H:%M"), self._state_key())
        self._show_inspector()
        self.statusBar().showMessage(_("Hourly series written: {file}").format(file=path.name), 6000)

    def _cancel_report(self) -> None:
        """Cancel on the bar of the report: its steps closed, the file half written taken away (report.export_steps);
        an older report under the same name stays as it was."""
        run, self.report_run = self.report_run, None
        if run is not None:
            run[0].close()
        self.report_progress.end()
        self.statusBar().showMessage(_("Report stopped: nothing written."), 6000)

    def _choose_inverter(self) -> None:
        dialog = CatalogDialog("inverters", self)
        if dialog.exec() == QDialog.DialogCode.Accepted and (rec := dialog.chosen()):
            self._add_inverter(rec, _("Add an inverter from the catalogue"))

    def _add_inverter(self, rec: dict, text: str) -> None:
        """An inverter added at the end of the plant's list (one unit; the same model again is one more of it). No
        string is made for it (R118): the strings stay where they are, the new inputs are free."""
        def add(entries):
            same = next((e for e in entries if e["record"] == rec), None)
            if same is not None:
                same["count"] += 1
            else:
                entries.append({"record": rec, "count": 1, "name": ""})
        self._entries_edit(text, add)
        self.tell(_("Inverter added: the strings stay as they are, its inputs are free. «+» on one of its inputs in "
                    "the list on the right draws a string there; «Complete» proposes strings for the modules in no "
                    "string."))

    def _size_inverters(self) -> None:
        """«Size it by itself»: the brand first, remembered in the project, then the model and how many at DC/AC."""
        good = self.session.good_results()
        p_stc = sum(a.p_stc for a in system.arrays_of(self.project, good)) if good else 0.0
        entries = system.inverter_entries(self.project.energy)
        ratio = float((self.project.energy or {}).get("dc_ac_ratio") or 1.1)
        makers = catalog.brands("inverters")
        if not makers:
            self.tell(_("There is no inverter in the catalogue to size."))
            return
        remembered = (self.project.energy or {}).get("inverter_maker", "")
        current = entries[0]["record"].get("manufacturer", "") if entries else ""
        wanted = remembered or current
        index = next((i for i, name in enumerate(makers) if name.casefold() == wanted.casefold()), 0)
        maker, ok = QInputDialog.getItem(self, _("Size the inverter by itself"), _("Manufacturer:"), makers, index,
                                         False)
        if not ok:
            return
        candidates = [r for r in catalog.load("inverters")
                      if str(r.get("manufacturer", "")).casefold() == maker.casefold()
                      and float(r.get("ac_power_nominal_w") or r.get("pac") or 0.0) > 0.0]
        if not candidates:
            self.tell(_("No inverter of {maker} in the catalogue has a nominal AC power.").format(maker=maker))
            return
        first = entries[0] if entries and current.casefold() == maker.casefold() else None
        options = []
        for candidate in candidates:
            count = system.sized_count(p_stc, ratio, candidate)
            pac = float(candidate.get("ac_power_nominal_w") or candidate.get("pac"))
            actual = p_stc / (count * pac)
            options.append((abs(actual - ratio), candidate.get("source") != "curated", candidate, count))
        if first is not None:
            rec = first["record"]
            n = system.sized_count(p_stc, ratio, rec)
        else:
            _error, _source, rec, n = min(options)

        def size(items):
            items[:] = [{**(first or {"record": rec, "name": ""}), "record": rec, "count": n}]
        self._entries_edit(_("Size the inverters by themselves"), size, {"inverter_maker": maker})
        actual = p_stc / (n * float(rec.get("ac_power_nominal_w") or rec.get("pac") or 1.0))
        self.tell(ngettext("Inverter sized: {n} x {maker} {model}, DC/AC {r}.",
                           "Inverters sized: {n} x {maker} {model}, DC/AC {r}.", n).format(
                               n=n, maker=maker, model=rec.get("model", ""), r=number(actual, 2)))

    # the plant (task 16d)

    def _year_conditions(self) -> tuple | None:
        """The hottest cell and the DC power of each hour of the last year computed, for the live checks; None
        before the first year. A year a little old serves: the strings do not change the cells' temperature."""
        sim = (self.energy or {}).get("sim")
        if sim is None:
            return None
        return max(a["t_cell_max"] for a in sim.arrays), sim.hourly.p_dc.to_numpy()

    def _plant_soon(self) -> None:
        """The strings laid again: at once when it costs a few milliseconds (the module's model already loaded), so
        that the checks and the plan come with the change and not a moment later; in a thread while pvlib is not
        loaded whole (the voltages at the cells' temperatures load it: a second and a half, which the window waited
        for at every project opened when no inverter seemed «to check», R120)."""
        if _pvlib_loaded():
            self.plant_timer.stop()
            self._start_plant(now=True)
        else:
            self.plant_timer.start()

    def _start_plant(self, now: bool = False) -> None:
        self.plant_generation += 1
        job = PlantJob(self.plant_generation, self.snapshot(), self.session.good_results(), self._year_conditions())
        job.signals.done.connect(self._plant_done)
        self.plant_job = job                        # what it took, for the tests
        if now:
            job.run()                               # here, in the window's thread: its signal comes at once
        else:
            self.pool.start(job)

    def plant_pending(self) -> bool:
        """Whether the strings are being laid again (a change on its way, or a job not back yet)."""
        return self.plant_timer.isActive() or self.plant_returned != self.plant_generation

    def _plant_done(self, generation: int, out) -> None:
        if generation != self.plant_generation:
            return                                  # a newer change is on its way
        self.plant_returned = generation
        if isinstance(out, Exception):
            self.tell(_("The strings could not be laid: {error}").format(error=out))
            return
        self.plant_state = out
        if not 0 <= self.chosen_string < len(out.strings):
            self.chosen_string = -1
        self.plan.chosen_string = self.chosen_string
        self.plan.set_wiring(out)
        self.plant_page.show_plant(out)
        self.plant_inspector.colours = list(self.plan.string_colours)
        if self.phase() == "plant":
            self.plant_inspector.show_plant(self.project, out, self.selection, self.chosen_string)
            self._show_chosen(self.chosen_string)
        self._show_string_commands()
        self._show_checks()
        if out.auto and self._layouts_settled():
            # a proposal of before format 14: written down as the designer's strings (the plant comes again)
            self._adopt_proposal(out)

    def _entries_edit(self, text: str, change, extra: dict | None = None) -> None:
        """An edit of the list of the inverters: `change(entries)` on the list as format 8 writes it. The strings stay
        on the inverters they were on, renumbered when the list moves them (plant.renumber; R118), in the same step."""
        def put(p):
            p.energy.update(extra or {})
            before = plant_model.unit_keys(p.energy)
            entries = system.inverter_entries(p.energy)
            for i, e in enumerate(entries):
                e["_was"] = i
            change(entries)
            moved = {e.pop("_was"): j for j, e in enumerate(entries) if "_was" in e}
            for e in entries:
                e.pop("_was", None)
            p.energy.pop("inverter", None)
            p.energy.pop("inverter_count", None)
            if entries:
                p.energy["inverters"] = entries
            else:
                p.energy.pop("inverters", None)
            s = p.energy.get("strings") if (p.energy.get("strings") or {}).__class__ is dict else None
            if s and s.get("runs"):
                p.energy["strings"] = {**s, "runs": plant_model.renumber(s["runs"], before,
                                                                         plant_model.unit_keys(p.energy), moved)}
        self.edit(text, put)

    def _choose_optimizer(self, entry: int) -> None:
        """The power optimizers of inverter `entry` from the catalogue (task 22): SolarEdge's shown first; two
        modules on each where the optimizer takes them (the commercial ones are made for it)."""
        dialog = CatalogDialog("optimizers", self)
        if not dialog.query.text() and not dialog.maker_name():
            dialog.query.setText("SolarEdge")
        if dialog.exec() != QDialog.DialogCode.Accepted or not (rec := dialog.chosen()):
            return

        def change(entries):
            if 0 <= entry < len(entries):
                entries[entry]["optimizer"] = rec
                entries[entry]["per_optimizer"] = 2 if (rec.get("modules_per_unit") or 1) >= 2 else 1
        self._entries_edit(_("Choose the power optimizers"), change)

    def _clear_optimizer(self, entry: int) -> None:
        def change(entries):
            if 0 <= entry < len(entries):
                entries[entry].pop("optimizer", None)
                entries[entry].pop("per_optimizer", None)
        self._entries_edit(_("Back to the optimizers Meridiana proposes"), change)

    def _optimizer_per(self, entry: int, per: int) -> None:
        def change(entries):
            if 0 <= entry < len(entries) and per in (1, 2):
                entries[entry]["per_optimizer"] = int(per)
        self._entries_edit(_("Change the modules on each optimizer"), change)

    def _inverter_count(self, entry: int, count: int) -> None:
        def change(entries):
            entries[entry]["count"] = max(1, int(count))
        self._entries_edit(_("Change how many inverters"), change)

    def _inverter_removed(self, entry: int) -> None:
        self._entries_edit(_("Take an inverter out"), lambda entries: entries.pop(entry))

    def _assign_subfield(self, sfid: str, inverter: int, mppt: int) -> None:
        """The inverter and the input a sub-field's strings go to (0: automatic)."""
        def put(p):
            sf = next((s for s in p.subfields if s.id == sfid), None)
            if sf is None:
                return
            for key, value in (("inverter", inverter), ("mppt", mppt if inverter else 0)):
                if value:
                    sf.params[key] = int(value)
                else:
                    sf.params.pop(key, None)
        self.edit(_("Send a sub-field's strings to an inverter"), put)

    # the strings (R114-R118, Daniel 25/10/2026): the designer's, made by Meridiana only when asked

    def _runs(self) -> list[dict]:
        """The designer's strings as the file keeps them (energy["strings"]["runs"])."""
        s = (self.project.energy or {}).get("strings") or {}
        return [dict(r, modules=list(r.get("modules") or [])) for r in s.get("runs") or [] if r.__class__ is dict]

    def _strings_put(self, text: str, runs: list[dict], extra: dict | None = None) -> None:
        """The strings `runs` as one undoable step (the empty ones left out), with `extra` keys of energy["strings"]
        (the strategy of a proposal)."""
        def put(p):
            s = dict(p.energy.get("strings") or {})
            s.update(extra or {})
            p.energy["strings"] = plant_model.touched(s, runs)
        self.edit(text, put)

    def _layouts_settled(self) -> bool:
        """Whether every sub-field to be laid has its layout of now (none on its way)."""
        if self.relayout_timer.isActive():
            return False
        return all(self.session.layout_state(sf) != "stale" for sf in self.project.subfields if sf.filled)

    def _adopt_proposal(self, plant) -> None:
        """A project of before format 14 (or a PVsyst import) had Meridiana's proposal for strings: written down as
        the designer's, as it is on the plan, without an undo step and without asking to save (session.amend), so that
        nothing changes under him and from now on nothing changes them by itself."""
        runs = plant_model.runs_of(plant)

        def put(p):
            p.energy["strings"] = plant_model.touched(p.energy.get("strings"), runs)
        self.session.amend(put)
        if runs:
            self.tell(ngettext("The string Meridiana proposed for this project is now yours, as it was: from now on "
                               "nothing changes it by itself.",
                               "The {n} strings Meridiana proposed for this project are now yours, as they were: from "
                               "now on nothing changes them by itself.", len(runs)).format(n=len(runs)))

    def _show_string_commands(self) -> None:
        """The strategy checked in the menu of «Propose»; «Complete» only with modules in no string, «Delete all» only
        with strings; «Draw» checked while a string is drawn."""
        s = (self.project.energy or {}).get("strings") or {}
        a = self.strategy_actions.get(s.get("strategy") or "serpentine")
        if a is not None:
            a.setChecked(True)
        plant = self.plant_state
        if "strings_complete" in self.commands:
            self.commands["strings_complete"].setEnabled(plant is None or bool(plant.left))
            self.commands["strings_clear"].setEnabled(bool(self._runs()) or (plant is not None and bool(plant.strings)))
        drawing = self.plan.draft is not None
        if self.stringing_action.isChecked() != drawing:
            self.stringing_action.setChecked(drawing)

    def _proposal(self, strategy: str = "", keep: list | None = None) -> list | None:
        """Meridiana's strings for the layouts of now (plant.propose); None, said, when there is nothing to propose
        on. The first proposal loads the module's model (most of a second): the pointer waits."""
        good = self.session.good_results()
        if not good:
            self.tell(_("Lay the modules first: the strings are proposed on the modules laid."))
            return None
        from PySide6.QtGui import QCursor
        year = self._year_conditions()
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        try:
            return plant_model.propose(self.project, good, strategy=strategy, keep=keep,
                                       t_cell_max_year=year[0] if year else None)
        except Exception as error:      # noqa: BLE001  a proposal that fails is said, the strings stay as they are
            log.complain("propose strings", error)
            self.tell(_("Meridiana could not propose the strings: {error}").format(error=error))
            return None
        finally:
            QApplication.restoreOverrideCursor()

    def _strings_propose(self, strategy: str = "") -> None:
        """«Propose the strings» (R114): Meridiana's strings in place of those there are, once, with `strategy` (the
        one chosen when ""): asked first when there are strings, one undo step; nothing changes them afterwards."""
        self._end_draft()
        s = (self.project.energy or {}).get("strings") or {}
        strategy = strategy if strategy in plant_model.strategy_names() else (s.get("strategy") or "serpentine")
        name = plant_model.strategy_names()[strategy]
        runs = self._runs()
        if runs:
            answer = QMessageBox.question(
                self, _("Propose the strings"),
                ngettext("The string there is is replaced by Meridiana's proposal ({strategy}). Undo brings it back. "
                         "Go on?",
                         "The {n} strings there are are replaced by Meridiana's proposal ({strategy}). Undo brings "
                         "them back. Go on?", len(runs)).format(n=len(runs), strategy=name.lower()),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                self._show_string_commands()
                return
        proposal = self._proposal(strategy)
        if proposal is None:
            self._show_string_commands()
            return
        if not proposal:
            notes = self.plant_state.notes if self.plant_state is not None else []
            self.tell(_("Meridiana finds no string to propose: {why}").format(
                why=notes[0] if notes else _("the inverter does not take these modules in series")))
            self._show_string_commands()
            return
        self.chosen_string = -1
        self._strings_put(_("Propose the strings: {strategy}").format(strategy=name.lower()), proposal,
                          {"strategy": strategy})
        self.tell(ngettext("{n} string proposed by Meridiana ({strategy}): yours now, nothing changes it by itself.",
                           "{n} strings proposed by Meridiana ({strategy}): yours now, nothing changes them by itself.",
                           len(proposal)).format(n=len(proposal), strategy=name.lower()))

    def _strings_complete(self) -> None:
        """«Complete the strings»: Meridiana's strings for the modules in no string only, on the inputs without strings
        first, then on those that take more; the designer's strings stay as they are (one undo step)."""
        self._end_draft()
        runs = self._runs()
        proposal = self._proposal(keep=runs)
        if proposal is None:
            return
        added = len(proposal) - len(runs)
        if added <= 0:
            self.tell(_("No string to add: the modules in no string are too few for a string, or the inputs take no "
                        "more. Draw one by hand, or add an inverter."))
            return
        self._strings_put(_("Complete the strings"), proposal)
        self.tell(ngettext("{n} string added for the modules that were in none; yours stayed as they were.",
                           "{n} strings added for the modules that were in none; yours stayed as they were.",
                           added).format(n=added))

    def _strings_clear(self) -> None:
        """«Delete all the strings»: asked first, one undo step; the modules stay laid, in no string."""
        self._end_draft()
        runs = self._runs()
        if not runs:
            self.tell(_("There is no string to delete."))
            return
        answer = QMessageBox.question(
            self, _("Delete all the strings"),
            ngettext("The string is deleted: its modules stay laid, in no string. Undo brings it back. Go on?",
                     "The {n} strings are deleted: their modules stay laid, in no string. Undo brings them back. Go on?",
                     len(runs)).format(n=len(runs)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.chosen_string = -1
        self._strings_put(_("Delete all the strings"), [])
        self.tell(_("Every string deleted: draw yours with «+» on an input of the list on the right, or «Draw»."))

    def _delete_string(self, index: int) -> None:
        """Del with a string chosen (R115): that string deleted, its modules in no string (one undo step)."""
        runs = self._runs()
        if not 0 <= index < len(runs):
            return
        name = plant_model.run_label(runs, index)
        n = len(runs[index]["modules"])
        self.chosen_string = -1
        self._strings_put(_("Delete string {name}").format(name=name), plant_model.delete_run(runs, index))
        self._show_chosen(-1)
        self.tell(ngettext("String {name} deleted: its module is in no string (Ctrl+Z brings it back).",
                           "String {name} deleted: its {n} modules are in no string (Ctrl+Z brings it back).",
                           n).format(name=name, n=n))

    def _show_chosen(self, index: int) -> None:
        """The string chosen, wider and numbered on the plan, selected in the list, with its checks in the inspector
        and its voltages in the strip of the bar (R57)."""
        self.plan.choose_string(index)
        self.plant_inspector.show_string(self.plant_state, index)
        self.plant_inspector.list.choose(index)
        plant = self.plant_state
        if plant is not None and 0 <= index < len(plant.strings):
            st = plant.strings[index]
            self.plant_page.show_string(f"{st.label}: {plant_model.voltages(st)}")
        elif self.plan.draft is None:
            self.plant_page.show_string("")

    def _choose_string(self, index: int, show: bool = False) -> None:
        """A string chosen (in the list, with a click on one of its modules), -1 none; with `show` brought into view
        on the plan (R115: chosen in the list, the plan goes to it)."""
        plant = self.plant_state
        if plant is None or not 0 <= index < len(plant.strings):
            index = -1
        self.chosen_string = index
        self._show_chosen(index)
        if index < 0:
            return
        if show:
            self.plan.show_string(index)
        self.hint.setText(_("String {name}: Del deletes it, a double click draws it again, the right button has the "
                            "rest").format(name=plant.strings[index].label))

    def _string_picked(self, sfid: str, key: str) -> None:
        """A click on a module of the plan in the Plant phase: its string chosen; a module in no string says how to
        put it in one."""
        plant = self.plant_state
        index = plant.string_of(sfid, key) if plant is not None else -1
        self._choose_string(index)
        if index < 0:
            self.hint.setText(_("This module is in no string: «+» on an input in the list on the right, or «Draw», then "
                                "click it."))

    def _end_draft(self) -> None:
        """A string being drawn given up without a word (another command, another phase)."""
        self.draft_target = None
        self.plan.end_draft()
        self._show_string_commands()

    def _start_draft(self, unit: int, mppt: int, first: list | None = None, run: int = -1) -> None:
        """A string drawn on input `mppt` of inverter `unit`: new (with `first` its first module), or string `run`
        drawn again from its modules."""
        if self.phase() != "plant":
            self.show_phase("plant")
        plant = self.plant_state
        if plant is None:
            self.tell(_("The strings are being laid: a moment."))
            return
        self.plan.end_draft()
        self.draft_target = {"unit": int(unit), "mppt": int(mppt), "run": int(run)}
        modules = [[sf, key] for sf, key, _c in plant.strings[run].modules] if 0 <= run < len(plant.strings) else []
        if first and not modules:
            modules = [list(first)]
        self.chosen_string = -1
        self.plan.choose_string(-1)
        self.plant_inspector.list.choose(-1)
        self.statusBar().clearMessage()             # what to do next is the bar's own words (the hint), not hidden
        self.plan.start_draft(modules, run, f"{unit}.{mppt}")
        self._show_string_commands()

    def _new_string(self, unit: int, mppt: int, first: list | None = None) -> None:
        """«+» on an input (R115): a new string drawn there, its modules clicked on the plan in order."""
        self._start_draft(unit, mppt, first)

    def _draw_string(self, checked: bool = True) -> None:
        """«Draw a string»: a new string on the input of the string chosen, or of the row chosen in the list, else on
        the first input without strings; off again, the string being drawn is given up."""
        if not checked:
            if self.plan.draft is not None:
                self.plan.cancel_draft()
            return
        target = self._input_for_new_string()
        if target is None:
            self.stringing_action.setChecked(False)
            self.tell(_("No inverter's input to draw a string on: add an inverter from the catalogue first."))
            return
        self._new_string(*target)

    def _input_for_new_string(self) -> tuple | None:
        """The input a new string goes to: that of the string chosen, else the first input without strings, else the
        first one."""
        plant = self.plant_state
        if plant is None or not plant.inputs:
            return None
        if 0 <= self.chosen_string < len(plant.strings):
            s = plant.strings[self.chosen_string]
            if (s.inverter, s.mppt) in plant.inputs:
                return s.inverter, s.mppt
        free = [slot for slot, i in sorted(plant.inputs.items()) if not i.strings]
        return free[0] if free else min(plant.inputs)

    def _redraw_string(self, index: int) -> None:
        """A string drawn again from its modules (a double click on it, in the list or on the plan): Backspace takes
        its last modules back, clicks add, Enter closes it as one undo step, Esc leaves it as it was."""
        plant = self.plant_state
        if plant is None or not 0 <= index < len(plant.strings) or plant.auto:
            return
        s = plant.strings[index]
        self._start_draft(s.inverter, s.mppt, run=index)

    def _string_redraw_at(self, sfid: str, key: str) -> None:
        plant = self.plant_state
        index = plant.string_of(sfid, key) if plant is not None else -1
        if index >= 0:
            self._redraw_string(index)

    def _draft_changed(self, modules: list) -> None:
        """The string being drawn changed: in the strip, its modules against what its input takes (live, from the
        input's range), in the bar what to do next."""
        target = self.draft_target or {}
        plant = self.plant_state
        unit, mppt = target.get("unit", 0), target.get("mppt", 0)
        n = len(modules)
        slot = plant.inputs.get((unit, mppt)) if plant is not None else None
        lo, hi = slot.series if slot is not None else (0, 0)
        # short: the strip has the room of a few words beside the legend
        what = (_("string {name} again").format(name=plant.strings[target["run"]].label)
                if plant is not None and 0 <= target.get("run", -1) < len(plant.strings) else
                _("new string {n}.{k}").format(n=unit, k=mppt))
        count = ngettext("{n} module", "{n} modules", n).format(n=n)
        if hi and not (plant.unit(unit) and plant.unit(unit).optimized):
            if n < lo:
                count += ", " + _("{k} short ({lo} to {hi})").format(k=lo - n, lo=lo, hi=hi)
            elif n > hi:
                count += ", " + _("{k} too many ({lo} to {hi})").format(k=n - hi, lo=lo, hi=hi)
            else:
                count += ", " + _("fine ({lo} to {hi})").format(lo=lo, hi=hi)
        self.plant_page.show_string(f"{what}: {count}")
        self.hint.setText(_("Click the modules in order (or drag over them); Backspace takes back the last, Enter or a "
                            "double click closes the string, Esc gives it up. A module of another string: Shift and "
                            "click moves it here."))

    def _draft_finished(self, modules: list) -> None:
        """Enter or a double click: the string drawn becomes one of the designer's, as one undo step; the modules
        moved from other strings are said (an emptied string goes)."""
        target, self.draft_target = self.draft_target, None
        self._show_string_commands()
        self.plant_page.show_string("")
        if target is None:
            return
        keys = [f"{sf}/{key}" for sf, key in modules]
        runs = self._runs()
        before = [list(r["modules"]) for r in runs]
        run = target["run"]
        if run >= 0 and run < len(runs):
            if not keys:
                self._delete_string(run)
                return
            if keys == runs[run]["modules"]:
                self._choose_string(run)
                return
            name = plant_model.run_label(runs, run)
            runs, robbed = plant_model.set_run(runs, run, keys)
            chosen, text = run, _("Draw string {name} again").format(name=name)
        else:
            if not keys:
                self.hint.setText(_("No module clicked: no string made."))
                return
            runs, chosen = plant_model.new_run(runs, target["unit"], target["mppt"], keys)
            robbed = [i for i, old in enumerate(before) if len(runs[i]["modules"]) < len(old)]
            text = _("New string on input {k} of inverter {n}").format(k=target["mppt"], n=target["unit"])
        names = ", ".join(plant_model.run_label([dict(r, modules=m) for r, m in zip(runs, before, strict=False)], i)
                          for i in robbed if i < len(before))
        kept = [i for i, r in enumerate(runs) if r.get("modules")]
        self.chosen_string = kept.index(chosen) if chosen in kept else -1
        self._strings_put(text, runs)
        self._show_chosen(self.chosen_string)
        if robbed:
            self.tell(_("Modules moved from string {names}").format(names=names), 8.0)
        else:
            self.tell(ngettext("String of {n} module made: Ctrl+Z takes it back.",
                               "String of {n} modules made: Ctrl+Z takes it back.", len(keys)).format(n=len(keys)), 6.0)

    def _draft_cancelled(self) -> None:
        self.draft_target = None
        self._show_string_commands()
        self.plant_page.show_string("")
        self._show_chosen(self.chosen_string)
        self.hint.setText(_("String given up: nothing changed."))

    def _string_menu(self, module: list, where) -> None:
        """The right button on the plan in the Plant phase. Drawing: close, take back the last, give up. On a module
        of a string (R57): skip it (the rest of the string stays), the string starts or ends there, the other way
        round, drawn again, deleted. On a module in no string: a new string from it."""
        from PySide6.QtWidgets import QMenu
        plant = self.plant_state
        menu = QMenu(self)
        if self.plan.draft is not None:
            close = menu.addAction(_("Close the string (Enter)"), self.plan.finish_draft)
            close.setEnabled(bool(self.plan.draft))
            back = menu.addAction(_("Take back the last module (Backspace)"), self.plan.draft_pop)
            back.setEnabled(bool(self.plan.draft))
            menu.addSeparator()
            menu.addAction(_("Give up the string (Esc)"), self.plan.cancel_draft)
            self.context_menu = menu
            menu.popup(where)
            return
        if plant is None or not module:
            return
        key = f"{module[0]}/{module[1]}"
        runs = self._runs()
        index = next((i for i, r in enumerate(runs) if key in r["modules"]), -1)
        if index < 0:
            menu.addAction(_("This module is in no string")).setEnabled(False)
            target = self._input_for_new_string()
            if target is not None:
                menu.addAction(_("New string from this module, on input {k} of inverter {n}").format(
                    k=target[1], n=target[0]), lambda: self._new_string(*target, first=module))
        else:
            self._choose_string(index)
            name = plant_model.run_label(runs, index)
            mods = runs[index]["modules"]
            at = mods.index(key)
            menu.addAction(_("Skip this module (the rest of {name} stays)").format(name=name),
                           lambda: self._runs_changed(*plant_model.remove_module(runs, key),
                                                      _("Take a module out of string {name}").format(name=name)))
            start = menu.addAction(_("String {name} starts here").format(name=name),
                                   lambda: self._runs_changed(*plant_model.cut_run(runs, key, "from"),
                                                              _("String {name} starts here").format(name=name)))
            start.setEnabled(at > 0)
            end = menu.addAction(_("String {name} ends here").format(name=name),
                                 lambda: self._runs_changed(*plant_model.cut_run(runs, key, "to"),
                                                            _("String {name} ends here").format(name=name)))
            end.setEnabled(at < len(mods) - 1)
            menu.addSeparator()
            self._string_actions(menu, index, name)
        self.context_menu = menu
        menu.popup(where)

    def _string_actions(self, menu, index: int, name: str) -> None:
        """What every menu of a string has: reversed, drawn again, moved to another input, deleted."""
        runs = self._runs()
        menu.addAction(_("Reverse string {name}").format(name=name),
                       lambda: self._runs_changed(plant_model.reversed_run(runs, index), index,
                                                  _("Reverse string {name}").format(name=name)))
        menu.addAction(_("Draw string {name} again (double click)").format(name=name),
                       lambda: self._redraw_string(index))
        plant = self.plant_state
        move = menu.addMenu(_("Move string {name} to").format(name=name))
        for (unit, mppt) in sorted(plant.inputs) if plant is not None else []:
            u = plant.unit(unit)
            a = move.addAction(f"{plant_model.unit_label(u)} · {input_name(u, mppt)}",
                               lambda _c=False, n=unit, m=mppt: self._move_string(index, n, m))
            a.setEnabled((runs[index].get("inverter"), runs[index].get("mppt")) != (unit, mppt))
        menu.addSeparator()
        menu.addAction(_("Delete string {name} (Del)").format(name=name), lambda: self._delete_string(index))

    def _string_list_menu(self, index: int, where) -> None:
        """The right button on a string of the list: brought into view, then its menu."""
        from PySide6.QtWidgets import QMenu
        runs = self._runs()
        if not 0 <= index < len(runs):
            return
        self._choose_string(index, show=True)
        name = plant_model.run_label(runs, index)
        menu = QMenu(self)
        self._string_actions(menu, index, name)
        self.context_menu = menu
        menu.popup(where)

    def _move_string(self, index: int, unit: int, mppt: int) -> None:
        runs = self._runs()
        if not 0 <= index < len(runs):
            return
        name = plant_model.run_label(runs, index)
        runs[index] = dict(runs[index], inverter=int(unit), mppt=int(mppt))
        moved = runs.pop(index)
        runs.append(moved)                          # last on its new input: its name follows
        self.chosen_string = len(runs) - 1
        self._strings_put(_("Move string {name} to input {k} of inverter {n}").format(name=name, k=mppt, n=unit), runs)

    def _runs_changed(self, runs: list, index: int, text: str) -> None:
        """Strings changed by a gesture of a menu: the one touched chosen."""
        kept = [i for i, r in enumerate(runs) if r.get("modules")]
        self.chosen_string = kept.index(index) if index in kept else -1
        self._strings_put(text, runs)
        self._show_chosen(self.chosen_string)

    def _choose_battery(self) -> None:
        dialog = CatalogDialog("batteries", self)
        if dialog.exec() == QDialog.DialogCode.Accepted and (rec := dialog.chosen()):
            self.edit(_("Choose the battery"), lambda p: set_path(p.economics, "battery", rec))

    def _choose_module(self, sfid: str) -> None:
        dialog = CatalogDialog("modules", self)
        if dialog.exec() != QDialog.DialogCode.Accepted or not (rec := dialog.chosen()):
            return
        mid = rec.get("id") or f"{rec.get('manufacturer')}:{rec.get('model')}"
        sf = self.project_subfield(sfid)
        if sf is not None and sf.manual:
            self._module_changed(sfid, mid, _("Choose the module"),
                                 lambda p: p.modules.__setitem__(mid, catalog.for_project(rec)))
            return

        def choose(p):
            p.modules[mid] = catalog.for_project(rec)
            sf = next((s for s in p.subfields if s.id == sfid), None)
            if sf is not None:
                sf.module = mid
        self.edit(_("Choose the module"), choose)

    def _import_pvsyst(self, kind: str, path: str = "") -> None:
        """A module (.PAN) or an inverter (.OND) of PVsyst: what was read is shown before it is used; the module
        goes to the project and to the selected sub-field, the inverter becomes the project's."""
        from ..catalog import panond
        title = _("Import a module from PVsyst") if kind == "module" else _("Import an inverter from PVsyst")
        if not path:
            pattern = _("PVsyst modules (*.pan *.PAN)") if kind == "module" else _("PVsyst inverters (*.ond *.OND)")
            path, _f = QFileDialog.getOpenFileName(self, title, self.cfg.last_folder, pattern)
            if not path:
                return
        try:
            rec, said = (panond.module if kind == "module" else panond.inverter)(Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, title, str(error))
            return
        name = f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip()
        answer = QMessageBox.question(self, title, _("Read from {file}: {name}.\n\n{what}.\n\nUse it?").format(
            file=Path(path).name, name=name, what=";\n".join(said)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        if kind == "inverter":
            self._add_inverter(rec, _("Import an inverter from PVsyst"))
            return
        mid = f"pan:{name}"
        sfid = self.selection[1] if self.selection[0] == "subfield" else ""

        def put(p):
            p.modules[mid] = catalog.for_project(rec)
            sf = next((x for x in p.subfields if x.id == sfid), None)
            if sf is not None:
                sf.module = mid
        self.edit(_("Import a module from PVsyst"), put)

    def _import_pvsyst_project(self, path: str = "", choose=None, confirm=None) -> bool:
        """A PVsyst project as a new Meridiana project: its variants chosen, what was read shown, the project
        created unsaved. `choose` and `confirm` stand in for the two dialogs in the tests."""
        from PySide6.QtGui import QGuiApplication

        from ..pvsyst import mapping, pvobject
        from ..pvsyst import project as pvproject
        from .pvsyst_import import ImportSummary, VariantsChoice
        title = _("Import a PVsyst project")
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, title, self.cfg.last_folder, _("PVsyst projects (*.prj *.PRJ)"))
            if not path:
                return False
        try:
            prj = pvproject.read_project(Path(path))
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, title, _("{file} could not be read: {error}").format(file=Path(path).name, error=error))
            return False
        if not prj.variants:
            QMessageBox.information(self, title, _("{file} has no variant next to it (<project>.VC0, .VC1...): export "
                                                   "the project from PVsyst with its variants.").format(file=Path(path).name))
            return False
        if choose is None:
            dialog = VariantsChoice(prj, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return False
            chosen = dialog.chosen()
        else:
            chosen = choose(prj)
        if not chosen:
            return False
        QGuiApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            variants = [pvproject.read_variant(prj.variants[k].path) for k in chosen]
            project, report = mapping.to_project(prj, variants)
        except (OSError, ValueError, pvobject.FormatError) as error:
            QGuiApplication.restoreOverrideCursor()
            QMessageBox.warning(self, title, _("The variants could not be read: {error}").format(error=error))
            return False
        QGuiApplication.restoreOverrideCursor()
        if confirm is None:
            if ImportSummary(prj.name, report, self).exec() != QDialog.DialogCode.Accepted:
                return False
        elif not confirm(report):
            return False
        if not self._keep_or_discard():
            return False
        self.session.take(project, None, saved=False)       # new and unsaved: closing asks
        self._title()
        self._drop_autosave()
        self.cfg.last_folder = str(Path(path).parent)
        self._select("site", "")
        self._show_all(fit=True)
        self.hint.setText(_("Imported from PVsyst: {n} variants. Save the project; what was approximated or is missing "
                            "stays among the checks.").format(n=len(variants)))
        return True

    # IFC (studies 15 and 20)

    def _ifc_missing(self, title: str) -> bool:
        """Without IfcOpenShell: said with what to install, True."""
        import importlib.util
        if importlib.util.find_spec("ifcopenshell") is not None:
            return False
        QMessageBox.information(self, title, _("The IFC models need IfcOpenShell (LGPL-3.0-or-later), which is not "
                                               "installed: «pip install ifcopenshell» in Meridiana's Python."))
        return True

    def _ifc_busy(self) -> bool:
        if self.ifc_reading is not None or self.ifc_job is not None:
            self.tell(_("An IFC model is being read or written: wait for it, or Cancel it in the status bar."))
            return True
        return False

    def _import_ifc(self, path: str = "", confirm=None, command=None) -> None:
        """An architect's model: read in a process of its own with its bar and Cancel (ui/ifc_import.py), then what was
        found shown before anything is added; the buildings come in as one change. `confirm(found)` stands in for the
        dialog in the tests (it gives the plan, or None), `command` for the worker."""
        title = _("Import an IFC model")
        if self._ifc_missing(title) or self._ifc_busy():
            return
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, title, self.cfg.last_folder,
                                                   _("IFC models (*.ifc *.IFC *.ifczip *.ifcZIP)"))
            if not path:
                return
        from .ifc_import import IfcReading
        reading = IfcReading(path, command=command, parent=self)
        reading.progress.connect(self._ifc_progress)
        reading.done.connect(lambda found: self._ifc_read(found, path, confirm))
        reading.failed.connect(lambda why: self._ifc_failed(title, why))
        self.ifc_reading = reading
        self.ifc_progress.begin(_("IFC: {file}").format(file=Path(path).name))
        reading.start()

    def _ifc_progress(self, fraction: float, what: str) -> None:
        text = _("IFC: {what}").format(what=self._ifc_step(what))
        if what in ("open", "again"):              # the parser says nothing until the file is open
            self.ifc_progress.unknown(text)
        else:
            self.ifc_progress.set(fraction, text)

    @staticmethod
    def _ifc_step(what: str) -> str:
        return {"open": _("opening the file"), "structure": _("the buildings and the storeys"), "roofs": _("the roofs"),
                "tessellate": _("the shapes"), "planes": _("the roof planes"), "obstacles": _("what stands on the roofs"),
                "again": _("a second try, with the simple shapes only"), "done": _("done")}.get(what, what)

    def _ifc_failed(self, title: str, why: str) -> None:
        self.ifc_reading = None
        self.ifc_progress.end()
        QMessageBox.warning(self, title, why)

    def _ifc_read(self, found: dict, path: str, confirm=None) -> None:
        from .. import ifc_import
        self.ifc_reading = None
        self.ifc_progress.end()
        self.cfg.last_folder = str(Path(path).parent)
        if confirm is None:
            from .ifc_import import IfcImportDialog
            dialog = IfcImportDialog(found, self.project, Path(path).name, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            plan = dialog.plan()
        else:
            plan = confirm(found)
        if plan is None or not plan.buildings:
            return
        added: list = []
        self.edit(_("Import an IFC model"), lambda p: added.extend(ifc_import.apply(p, plan)))
        if added:
            self._select("building", added[0])
        self._show_all(fit=True)
        self.hint.setText(ngettext("From {file}: {n} building, with its roof and what stands on it. Ctrl+Z takes it "
                                   "away.", "From {file}: {n} buildings, with their roofs and what stands on them. Ctrl+Z "
                                   "takes them away.", len(added)).format(file=Path(path).name, n=len(added)))

    def _export_ifc(self, path: str = "") -> None:
        title = _("Export the model as IFC4")
        if self._ifc_missing(title) or self._ifc_busy():
            return
        if not path:
            start = str(Path(self.cfg.last_folder or Path.home()) / (self.project.name + ".ifc"))
            path, _f = QFileDialog.getSaveFileName(self, title, start, _("IFC models (*.ifc)"))
            if not path:
                return
        target = Path(path if path.lower().endswith(".ifc") else path + ".ifc")
        # the project as it is written: later changes make it stale
        job = ExportIfcJob(self.snapshot(), self.session.known_layouts(), target, self._state_key())
        job.signals.step.connect(self._ifc_export_step)
        job.signals.done.connect(self._ifc_export_done)
        self.ifc_job = job
        self.ifc_progress.begin(_("IFC4: {file}").format(file=target.name))
        self.pool.start(job)

    def _ifc_export_step(self, fraction: float, what: str) -> None:
        self.ifc_progress.set(fraction, _("IFC4: {what}").format(what=what))

    def _ifc_export_done(self, out) -> None:
        if self.ifc_job is not None:
            self._ifc_exported(out, self.ifc_job.path, self.ifc_job.state)

    def _ifc_exported(self, out, target: Path, state: str = "") -> None:
        self.ifc_job = None
        self.ifc_progress.end()
        if out is None:
            self.statusBar().showMessage(_("IFC export stopped: nothing written."), 6000)
            return
        if isinstance(out, Exception):
            QMessageBox.warning(self, _("Export the model as IFC4"), _("The model could not be written: {error}").format(
                error=out))
            return
        self.cfg.last_folder = str(target.parent)
        self.exports["ifc"] = (target.name, time.strftime("%d/%m/%Y %H:%M"), state)
        self._show_inspector()
        self.statusBar().showMessage(ngettext("IFC4 written: {file}, {n} module", "IFC4 written: {file}, {n} modules",
                                              out["modules"]).format(file=target.name, n=out["modules"]), 8000)

    def _cancel_ifc(self) -> None:
        """Cancel on the bar: the reading's process killed, or the export stopped at its next step."""
        if self.ifc_reading is not None:
            self.ifc_reading.cancel()
            self.ifc_reading = None
            self.statusBar().showMessage(_("IFC reading stopped: nothing added."), 6000)
        if self.ifc_job is not None:
            self.ifc_job.interrupt()
        self.ifc_progress.end()

    def _import_curve(self, path: str, unit: str) -> None:
        try:
            rows = consumption_model.read_curve(Path(path), unit)
            hourly = consumption_model.to_hourly(rows)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, _("Import a load curve"), _("{file} could not be read: {error}").format(
                file=Path(path).name, error=error))
            return

        def put(p):
            p.consumption["measured"] = hourly
            p.consumption.pop("monthly_bands_kwh", None)
        self.edit(_("Import a load curve"), put)

    # files

    def _clean_changed(self, _clean: bool) -> None:
        # a method, not a lambda: Qt drops the connection when the window goes, a lambda would outlive it
        self._title()

    def _state_key(self) -> str:
        return self.session.state_key()

    def _title(self) -> None:
        name = self.path.name if self.path else self.project.name
        self.setWindowTitle(f"{name}{' *' if self._dirty() else ''} - Meridiana")

    def _mark_saved(self) -> None:
        self.session.mark_saved()
        self._title()
        self._drop_autosave()

    # autosave and recovery

    def tell(self, text: str, seconds: float = 15.0) -> None:
        """A line in the status bar, for what failed quietly until now: the designer reads it, nothing
        waits for a click (study 18, G 3.3)."""
        self.statusBar().showMessage(text, int(seconds * 1000))

    def tell_error(self, text: str) -> None:
        """An exception nobody caught (log.install_excepthook): the status bar says it every time, a dialog
        the first time, with where the detail is."""
        where = log.file()
        line = _("Meridiana ran into an error: {error}").format(error=text)
        if where is not None:
            line += " " + _("(the detail is in {file})").format(file=where)
        self.tell(line, 30.0)
        if not self._told_error:
            self._told_error = True
            QMessageBox.warning(self, _("An error"), line + "\n\n" + _(
                "The window goes on; if something looks wrong, save with a new name and reopen."))

    def _tile_failed(self, key: str, z: int, x: int, y: int, why: str) -> None:
        if time.monotonic() - self._tile_told < 60.0:      # one line a minute, not one per tile
            return
        self._tile_told = time.monotonic()
        source = self.plan.sources.get(key)
        self.tell(_("The map tiles of {source} are not loading: {why}").format(
            source=tiles.display_name(source) if source else key, why=why))

    def _autosave(self) -> None:
        try:
            self.session.autosave(self.paths.state)
        except OSError as error:
            log.complain("autosave", error)
            self.tell(_("The recovery copy could not be written: {error}").format(error=error))

    def _drop_autosave(self) -> None:
        self.session.drop_autosave(self.paths.state)

    def offer_recovery(self) -> bool:
        """A copy left by a session that stopped without saving: offered back, the newest first."""
        copies = recovery.pending(self.paths.state)
        if not copies:
            return False
        c = copies[0]
        name = Path(c["path"]).name if c["path"] else _("a new project")
        when = time.strftime("%d/%m/%Y %H:%M", time.localtime(c["saved"]))
        answer = QMessageBox.question(
            self, _("Recover the changes"),
            _("Meridiana stopped without saving {name}: a copy of {when} is there. Recover it?").format(
                name=name, when=when),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            c["file"].unlink(missing_ok=True)
            return False
        try:
            project = model.Project.from_json(c["project"])
        except Exception as error:             # noqa: BLE001  a copy written by hand or damaged: said, not a crash
            log.complain("recovery", error)
            QMessageBox.warning(self, _("Recover the changes"), _("The copy could not be read: {error}").format(error=error))
            return False
        self.session.take(project, Path(c["path"]) if c["path"] else None, saved=False)   # not saved yet
        self.session.autosaved = c["file"]
        self._select("site", "")
        self._show_all(fit=True)
        self._title()
        self.statusBar().showMessage(_("Recovered: save it to keep it"), 8000)
        return True

    def _save_revision(self) -> None:
        if self.path is None:
            self._save_as()
            return
        try:
            target = self.session.save_revision()
        except OSError as error:
            QMessageBox.warning(self, _("Save"), _("The project could not be saved: {error}").format(error=error))
            return
        self.cfg.last_project = str(target)
        self._save_config()
        self._mark_saved()
        self.statusBar().showMessage(_("New revision saved: {file}; the previous one stays as it was").format(
            file=target.name), 6000)

    def _dirty(self) -> bool:
        return self.session.dirty()

    def _keep_or_discard(self) -> bool:
        if not self._dirty():
            return True
        answer = QMessageBox.question(self, _("Unsaved changes"), _("Save the changes to the project first?"),
                                      QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard |
                                      QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Save:
            return self._save()
        return answer == QMessageBox.StandardButton.Discard

    def _new(self) -> None:
        if not self._keep_or_discard():
            return
        self.session.new()
        self._mark_saved()
        self._select("site", "")
        self._show_all(fit=True)

    def _open(self) -> None:
        if not self._keep_or_discard():
            return
        name, _f = QFileDialog.getOpenFileName(self, _("Open a project"), self.cfg.last_folder,
                                               _("Meridiana projects (*{suffix})").format(suffix=SUFFIX))
        if name:
            self.open_path(Path(name))

    def open_path(self, path: Path) -> None:
        try:
            notice = self.session.open(path)
        except Exception as error:             # noqa: BLE001  a damaged file is said, never a crash of the slot
            log.complain("open", error)
            QMessageBox.warning(self, _("Open a project"), _("{file} could not be opened: {error}").format(
                file=path.name, error=error))
            return
        self._mark_saved()
        self.cfg.last_folder, self.cfg.last_project = str(path.parent), str(path)
        self._save_config()
        self._select("site", "")
        self._show_all(fit=True)
        if notice:
            QMessageBox.information(self, _("Open a project"), notice)

    def _save(self) -> bool:
        if self.path is None:
            return self._save_as()
        try:
            self.session.save(self.path)
        except OSError as error:
            QMessageBox.warning(self, _("Save"), _("The project could not be saved: {error}").format(error=error))
            return False
        self._mark_saved()
        self.statusBar().showMessage(_("Saved {file}").format(file=self.path.name), 4000)
        return True

    def _save_as(self) -> bool:
        start = str(Path(self.cfg.last_folder or Path.home()) / (self.project.name + SUFFIX))
        name, _f = QFileDialog.getSaveFileName(self, _("Save the project"), start,
                                               _("Meridiana projects (*{suffix})").format(suffix=SUFFIX))
        if not name:
            return False
        path = Path(name if name.endswith(SUFFIX) else name + SUFFIX)
        self.path = path
        self.cfg.last_folder, self.cfg.last_project = str(path.parent), str(path)
        self._save_config()
        return self._save()

    RECENT = 8                                   # the projects the File page lists

    def _remember_recent(self, path) -> None:
        """`path` first among the projects opened last (the File page), once, at most RECENT."""
        here = str(path)
        older = [p for p in self.cfg.recent if isinstance(p, str) and p != here]
        self.cfg.recent = [here, *older][:self.RECENT]

    def _save_config(self) -> None:
        if self.cfg.last_project and (not self.cfg.recent or self.cfg.recent[0] != self.cfg.last_project):
            self._remember_recent(self.cfg.last_project)
        try:
            config.save(self.cfg, self.paths.config_file)
        except OSError as error:
            log.complain("settings", error)
            self.tell(_("The settings could not be saved: {error}").format(error=error))

    def _about(self) -> None:
        from .. import __version__
        QMessageBox.about(self, _("About Meridiana"), _(
            "<b>Meridiana</b> {version}<br>Photovoltaic design: map, building model, sun path, module layout and "
            "Italian standards.<br><br>GPL-3.0-or-later. Qt for Python (LGPL), Qt Quick 3D (GPL), shapely (BSD), "
            "numpy (BSD). Backgrounds: the map sources of Preferences > Maps, each named on the plan with its "
            "attribution (among them the national orthophoto of the Geoportale Nazionale, MASE, and © OpenStreetMap "
            "contributors); the outlines of their areas from Natural Earth (public domain).").format(version=__version__))

    # -- a newer version (updates.py, ui/update_dialog.py; task 18f) ------------------------------------------------

    def _daily_update_check(self) -> None:
        """A minute after the start, once a day, when Preferences > Privacy allows it (the Windows build only:
        updates.checks_by_itself); the installers of earlier updates are cleared first."""
        from datetime import date

        from .. import updates
        today = date.today().isoformat()
        if not updates.check_due(self.cfg.check_updates, self.cfg.last_update_check, today):
            return
        self.cfg.last_update_check = today
        self._save_config()
        updates.clean_downloads()
        self.check_updates(manual=False)

    def check_updates(self, manual: bool) -> None:
        """The latest release asked of GitHub in the pool; the answer in _update_answer."""
        from .update_dialog import CheckJob
        job = CheckJob(manual)
        job.signals.done.connect(self._update_answer)
        self.update_job = job                       # (the tests wait on it)
        if manual:
            self.tell(_("Checking for updates…"), 10)
        self.pool.start(job)

    def _update_answer(self, release, why: str, manual: bool) -> None:
        from .. import __version__, updates
        if release is None:
            if manual:
                self.tell(_("The check for updates failed: {error}").format(error=why))
            else:                                   # offline, at the start: not worth a word in the window
                log.complain("update check", updates.UpdateError(why))
            return
        if not updates.is_newer(release.version):
            if manual:
                self.tell(_("Meridiana {version} is the latest version.").format(version=__version__))
            return
        if manual or self.isActiveWindow():
            self.show_update(release)
        else:
            self.tell(_("Version {version} is available: Help > Check for updates.").format(version=release.version),
                      60)

    def show_update(self, release, run=None, **options):
        """The dialog of a newer version; `run` stands in for exec() in the tests, `options` for its installer and
        Setup."""
        from .update_dialog import UpdateDialog
        dialog = UpdateDialog(release, self, before_install=self._keep_or_discard, **options)
        (run or (lambda d: d.exec()))(dialog)
        return dialog

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.shown_once:
            self.shown_once = True
            QTimer.singleShot(0, self, self._first_layout)    # not called if the window is gone by then
            from .. import updates
            if updates.checks_by_itself():
                QTimer.singleShot(updates.CHECK_DELAY_MS, self, self._daily_update_check)

    def _first_layout(self) -> None:
        """The window as it was left, or at the first start plan and 3D side by side, the plan a little
        wider (the splitter otherwise gives the first widget everything)."""
        if not self.restored:
            width = self.split.width()
            self.split.setSizes([int(width * 0.55), int(width * 0.45)])
        self.plan.fit()
        self._show_3d()
        QTimer.singleShot(WARM_UP_MS, self, self._warm_up)

    def _warm_up(self) -> None:
        """What the first change of phase would otherwise wait for (R83), done while the window rests after the start:
        the charts' library loading in its thread (80 ms at the first Production otherwise) and a first picture of
        the phase's bar (the first grab of a window costs about 0,1 s, the next ones a few ms)."""
        charts.preload()
        from . import motion
        if self.tabs.bars.isVisible() and not motion.reduced():
            motion.picture(self.tabs.bars)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._adapt()
        self._fit_bars()

    def _adapt(self) -> None:
        """A narrow window (below NARROW) works as one column: the two panels share the right side as
        tabs and the view shows the plan; a wide one puts them back. It happens when the width crosses
        the line, so what the designer arranges in between stays. A tiling compositor decides the size
        after the window is shown, so this follows the resizes rather than the first show."""
        narrow = self.width() < NARROW
        if narrow == self.narrow:
            return
        first, self.narrow = self.narrow is None, narrow
        if first and self.restored:
            return                                  # the panels as the designer left them
        left, right = self.docks
        if narrow:
            self.tabifyDockWidget(right, left)
            right.raise_()
            if self.view_actions["both"].isChecked():
                self._view_mode("plan")
                self.auto_plan = True
        else:
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left)
            if self.auto_plan:
                self._view_mode("both")
                width = self.split.width()
                self.split.setSizes([int(width * 0.55), int(width * 0.45)])

    def _restore_window(self) -> bool:
        """Size, panels, the split between plan and 3D and the view mode as the designer left them; False
        when nothing was saved (the first start) or what was saved cannot be used."""
        try:
            data, _notice = atomic.read_json(self.paths.window_state_file)
            geometry, state, split = (QByteArray.fromBase64(data[k].encode("ascii")) for k in ("geometry", "state", "split"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return False
        if not self.restoreGeometry(geometry):
            return False
        self.restoreState(state)
        self._settle_assistant_dock()
        self.split.restoreState(split)
        self._view_mode(data.get("view") if data.get("view") in self.view_actions else "both")
        places = data.get("assistant") if isinstance(data.get("assistant"), dict) else {}
        self.assistant.places = {tab: a for tab in assistant_core.TABS
                                 if (a := assistant_core.valid_anchor(places.get(tab))) is not None}
        self.assistant.reposition()
        return True

    def _save_window(self) -> None:
        mode = next((k for k, a in self.view_actions.items() if a.isChecked()), "both")
        split = self.split_home if self.split_home is not None else self.split.saveState()   # the plan at home
        places = dict(self.assistant.places)
        data = {"geometry": bytes(self.saveGeometry().toBase64()).decode("ascii"),
                "state": bytes(self.saveState().toBase64()).decode("ascii"),
                "split": bytes(split.toBase64()).decode("ascii"), "view": mode,
                "assistant": {tab: list(a) for tab, a in places.items()}}
        try:
            atomic.write_json(self.paths.window_state_file, data, keep_backup=False)
        except OSError as error:
            log.complain("window state", error)
            self.tell(_("The window layout could not be saved: {error}").format(error=error))

    def closeEvent(self, event) -> None:
        if self._keep_or_discard():
            self._cancel_report()
            self.preview_soon.stop()
            if self.preview_run is not None:
                run, self.preview_run = self.preview_run, None
                run[0].close()
            self._cancel_ifc()
            self._drop_autosave()
            self._save_config()
            self._save_window()
            event.accept()
        else:
            event.ignore()
