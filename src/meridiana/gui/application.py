"""The Qt Quick window and its start (main): the application, the settings of the profile, the single instance, the
project given on the command line, the recovery copies, the log of what goes wrong."""
import argparse
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import Q_ARG, QCoreApplication, QEvent, QMetaObject, QPoint, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from meridiana.app.platform import config, log, qt_cache
from meridiana import i18n
from meridiana.core.model import model
from meridiana.core.compute import resources
from meridiana.app.platform.paths import Paths
from meridiana.i18n import _
from meridiana.gui.style.design import Type
from meridiana.gui.style.theme import _font_families

from meridiana.gui.backend.tokens import ThemeTokens, install_theme
from meridiana.gui.backend.shell import ShellController, labels
from meridiana.gui.backend.shell_compute import ShellBridge
from .sample import ROOT, SAMPLE, recorded_weather


def tokens(large=False):
    """Compatibility snapshot for the prototype's measurement tools."""
    return ThemeTokens({'textSize': 'large' if large else 'medium'}).tokens


def render_loop(platform, backend=''):
    """The scene graph's render loop: threaded on a graphics API (native batched Shapes, no Python render-node
    callback), basic on the software renderer. Without a GPU (offscreen, minimal, QT_QUICK_BACKEND=software) Qt draws
    every Shape with a software render node that reads its item's window on the render thread: with the threaded
    loop, an item taken out of the scene meanwhile (the plan's labels and marks, made again at each zoom step) left
    window() null and Qt6Quick read address 0x8 (access violation in Impianto after about 10 notches, 06/11/2026).
    Qt's software renderer runs on the basic loop unless told otherwise."""
    software = platform in ('offscreen', 'minimal') or backend in ('software', 'softwarecontext')
    return 'basic' if software else 'threaded'


def _qml_language() -> None:
    """i18n.setup() changed the language: the QML's catalogue follows, from the main thread only (R593)."""
    app = QGuiApplication.instance()
    if app is not None and threading.current_thread() is threading.main_thread():
        from .translator import install
        install(app, i18n.qt_catalogue())


def create_app(language='it', arguments=()):
    """The application of the Quick window, speaking `language` ('' the desktop's: the program's own start, with the
    preference of Settings; the tests and the tools keep Italian). `arguments`: the command line after the program's
    name, for Qt to take its own options from (-platform offscreen: main)."""
    # Qt's disk caches off here (the tests, the tools, the package's check); the program's start turns them on in
    # its profile (main, app/platform/qt_cache.py, study 56)
    qt_cache.turn_off()
    QQuickStyle.setStyle('Basic')
    # r23-unita (r22-flatpak: Niri saw the Quick window as «python3», without Meridiana's icon): the desktop file's
    # name is the Wayland app_id the compositor matches with io.github.daniel_g_carrasco.meridiana.desktop and its
    # icon, the application's name the X11 window class (WM_CLASS), as the Widgets window does (app.py)
    from meridiana import APP_ID, APP_NAME
    QGuiApplication.setApplicationName(APP_NAME)
    QGuiApplication.setDesktopFileName(APP_ID)
    app = QGuiApplication.instance() or QGuiApplication(['meridiana-quick', *arguments])
    # Read by Qt when the first Quick window is made, after this.
    os.environ.setdefault('QSG_RENDER_LOOP', render_loop(app.platformName(), os.environ.get('QT_QUICK_BACKEND', '')))
    i18n.setup(language)
    i18n.share_with_children()      # the computation's and the tasks' processes speak it too
    # Qt's default locale is the window's language, whatever the desktop's (D2, D3, Linux 14/11/2026: a desktop in
    # English with the program in Italian wrote «21 Dec» and «85.20» through every Qt.locale() of the QML)
    from PySide6.QtCore import QLocale
    QLocale.setDefault(QLocale(QLocale.Language.Italian, QLocale.Country.Italy) if i18n.language() == 'it'
                       else QLocale(QLocale.Language.English, QLocale.Country.UnitedKingdom))
    from .translator import install
    install(app, i18n.qt_catalogue())   # the QML's qsTr through po/it.po, by Qt's own translator (no Python)
    i18n.on_change(_qml_language)
    font = QFont(_font_families('plex')[0])
    font.setPixelSize(Type.BODY)
    app.setFont(font)
    return app


FRAME_WAIT_MS = 120   # R547: the longest wait for the frame that shows a change before the other views hear it
HANDED_WAIT_MS = 500  # a project handed over while a dialog is open or a file is written: asked again after it
ERROR_MS = 30000      # an error nobody caught stays this long in the status bar
TOUR_DELAY_MS = 1200  # the first start: the tour offered once the window has settled (as r29)
TITLE_STRIP = 40      # logical px of the frame's top: what the hand needs to take the window back


def _shown(rect, area):
    """Logical px² of rect inside area."""
    part = rect.intersected(area)
    return max(0, part.width()) * max(0, part.height())


def screen_for(window):
    """The screen to keep the window on: the one whose useful area shows most of its title strip, the primary one when
    no screen shows it (R448: a position from another arrangement of screens, x -2887 on Daniel's PC, 05/11/2026)."""
    frame = window.frameGeometry()
    strip = QRect(frame.x(), frame.y(), frame.width(), min(frame.height(), TITLE_STRIP))
    screens = QGuiApplication.screens()
    best = max(screens, key=lambda s: _shown(strip, s.availableGeometry()), default=None)
    if best is None or not _shown(strip, best.availableGeometry()):
        return QGuiApplication.primaryScreen(), True
    return best, False


def keep_on_screen(window):
    """R430: the window inside the screen's useful area, the taskbar left out: the status bar stays in sight whatever
    screen, scale or size it comes to. A maximized window is the system's already. R448: a window that no screen
    shows comes back in the middle of the primary screen."""
    if not window.isVisible() or window.visibility() in (QWindow.Visibility.Maximized, QWindow.Visibility.FullScreen):
        return
    screen, lost = screen_for(window)
    if screen is None:
        return
    area, frame = screen.availableGeometry(), window.frameGeometry()
    extra_w, extra_h = frame.width() - window.width(), frame.height() - window.height()
    width, height = min(window.width(), area.width() - extra_w), min(window.height(), area.height() - extra_h)
    window.setMinimumWidth(min(window.minimumWidth(), width))
    window.setMinimumHeight(min(window.minimumHeight(), height))
    if (width, height) != (window.width(), window.height()):
        window.resize(width, height)
    if lost:
        if window.screen() is not screen:
            window.setScreen(screen)
        x = area.left() + (area.width() - width - extra_w) // 2
        y = area.top() + (area.height() - height - extra_h) // 2
    else:
        x = max(area.left(), min(frame.x(), area.left() + area.width() - width - extra_w))
        y = max(area.top(), min(frame.y(), area.top() + area.height() - height - extra_h))
    if (x, y) != (frame.x(), frame.y()):
        window.setFramePosition(QPoint(x, y))


def watch_placement(window):
    """R448: a move that leaves the window where no screen shows its title (the system placing it after the show, a
    screen gone) brings it back; a move the user makes with the title in sight is left alone."""
    timer = QTimer(window)
    timer.setSingleShot(True)
    timer.setInterval(250)

    def check():
        if window.isVisible() and screen_for(window)[1]:
            keep_on_screen(window)
    timer.timeout.connect(check)
    window.xChanged.connect(lambda _x: timer.start())
    window.yChanged.connect(lambda _y: timer.start())
    window.visibleChanged.connect(lambda _visible: timer.start())
    QGuiApplication.instance().screenRemoved.connect(lambda _screen: timer.start())
    return timer


class QuickWindow:
    def __init__(self, project, cache, *, large=False, theme=None, real_views=False, path=None, photo=None):
        self.bridge = ShellBridge(project, cache)
        if photo is not None:               # session.photo_of(project), made where it was read (main)
            self.bridge.session.keep_photo(photo)
        from meridiana.gui.backend import scene_context
        scene_context.preload_project(project)          # R548: the IFC model's geometry read while the QML is made
        self.plan = self.scene = None
        self.engine = QQmlApplicationEngine()
        self.theme = install_theme(self.engine, theme or {'textSize': 'large' if large else 'medium'})
        base = Path(cache) / 'quick-profile'
        self.paths = Paths(*(base / name for name in ('config', 'state', 'data', 'cache')))
        self.cfg = config.load(self.paths.config_file)
        resources.configure(self.cfg.memory_mode)
        if hasattr(self.bridge, 'configure_background'):         # R461
            self.bridge.configure_background(self.cfg.background_year, self.cfg.background_year_wait_s,
                                             self.cfg.background_year_workers, self.cfg.background_year_battery_factor)
        # Some parts save preferences during installation. Give all of them the
        # requested appearance before the first part can materialize the file.
        if not self.paths.config_file.exists() or theme is not None:
            options = self.theme.options
            for key in ('theme', 'accent', 'backgrounds', 'font'):
                setattr(self.cfg, key, options[key])
            self.cfg.text_size = options['textSize']
            self.cfg.density = options['density']
            self.cfg.extra['reduced_motion'] = options['reducedMotion']
            self.cfg.extra['phase_animations'] = options['phaseAnimations']
        self.shell = ShellController(self.bridge)
        from meridiana.gui.backend.parts import Parts
        self.parts = Parts(self.engine, self.bridge.session, cache, self)
        from meridiana.gui.backend import work           # R598: the heavy jobs and their one bar, in every workbench
        self.work = self.parts.install(work.install).controllers['work']
        from meridiana.gui.backend import plan_map       # the sun map (study 45), on the jobs' center just made
        self.sun_map = self.parts.install(plan_map.install).controllers['sunMap']
        self.warnings = []
        self.engine.warnings.connect(lambda errors: self.warnings.extend(e.toString() for e in errors))
        context = self.engine.rootContext()
        context.setContextProperty('backend', self.bridge)
        context.setContextProperty('shell', self.shell)
        context.setContextProperty('D', self.theme.tokens)
        self.theme.changed.connect(lambda: context.setContextProperty('D', self.theme.tokens))
        copy = {key: _(value) for key, value in {
            'title': 'Meridiana', 'model': 'Modelling', 'production': 'Production',
            'project': 'Project', 'properties': 'Properties', 'checks': 'Checks', 'name': 'Name',
            'height': 'Height (m)', 'undo': 'Undo', 'redo': 'Redo', 'rectangle': 'Rectangle',
            'select': 'Select', 'fit': 'Fit', 'calculate': 'Compute', 'all': 'All',
            'fail': 'Errors', 'warn': 'Warnings', 'ok': 'Passed', 'info': 'Information',
            'calculating': 'Computing…', 'cancel': 'Cancel', 'tools': 'Tools', 'ready': 'Ready', 'modules': 'modules',
            'readonly': 'Trial in memory: the original file is not written',
            'year': 'Daily production over the year', 'daily': 'Energy (kWh/day)',
            'help': 'Wheel: zoom · middle button: pan · click: select',
            'drawing': 'Drag to draw · Esc: select · handles: change the rectangle',
            'jan': 'January', 'dec': 'December', 'empty': 'Select a building or a sub-field',
            'meridio': 'Meridio', 'tipRectangle': 'Draw a rectangular building, then drag its handles.',
            'tipCalculate': 'Compute the year with the Python core and the recorded weather, offline.',
        }.items()}
        context.setContextProperty('L', copy | labels())
        from meridiana.app.platform.paths import shipped
        mascot = shipped('meridio', 'meridio.svg') or ROOT / 'data/meridio/meridio.svg'
        context.setContextProperty('mascotSource', QUrl.fromLocalFile(str(mascot)))
        from meridiana.gui.backend.controls import install_controls
        install_controls(self.engine)
        source = Path(__file__).parent / 'qml/Meridiana/Shell/Workbench.qml'
        if real_views:
            self._real_views(context, cache, source.parent)
            self.parts.discover()
            self.engine.setInitialProperties(self.parts.initial_properties())
        from meridiana.gui.backend.shell_tasks import ShellTasks
        self.tasks = ShellTasks(self)
        context.setContextProperty('shellTasks', self.tasks)
        from meridiana.gui.backend.shell_motion import FileMotion
        self.file_motion = FileMotion(self)
        context.setContextProperty('motion', self.file_motion)          # R483: the phases' transition
        self.engine.load(QUrl.fromLocalFile(str(source)))
        if not self.engine.rootObjects():
            raise RuntimeError('QML did not create a window: ' + '\n'.join(self.warnings))
        self.window = self.engine.rootObjects()[0]
        if self.plan is not None:
            from meridiana.gui.backend.click_diagnostics import ClickDiagnostics
            self.click_diagnostics = ClickDiagnostics(self.window, lambda: self.plan.tool)
        # R547: a change of the modules drawn first, the rest of the views told after the frame (session.later)
        self.bridge.session.later = self._after_frame
        # R598: the views told of a layout, and those told after the frame, one at a time on the jobs' turns
        self.bridge.session.pieces = self.work.center.piece
        # R482, R481: the title bars in the theme; Alt read for the whole window (backend/window_frame.py)
        from meridiana.gui.backend.window_frame import AltTap, FrameTheme
        self.frame_theme = FrameTheme(self.theme, self.window)
        self.alt_tap = AltTap(self.window, self.window)
        if self.window.metaObject().indexOfSignal('phaseChanged()') >= 0:
            from meridiana.gui.backend import activity          # r27: a change of phase is the designer at work (activity.py)
            self.window.phaseChanged.connect(activity.touch)
        # R545: two fingers on a touchpad under Wayland at the pace of the other programs (backend/touchpad.py)
        from meridiana.gui.backend.touchpad import TouchpadPace
        self.touchpad_pace = TouchpadPace(self.window)
        if self.touchpad_pace.active:
            self.touchpad_pace.follow(QGuiApplication.instance())
        # R556: two fingers on a touchpad under Windows taken as on Linux, not for a mouse wheel (backend/touchpad.py)
        from meridiana.gui.backend.touchpad import WindowsTouchpad
        self.windows_touchpad = WindowsTouchpad(self.window)
        if self.windows_touchpad.active:
            self.windows_touchpad.follow(QGuiApplication.instance())
        self.gesture_trace = None
        if os.environ.get('MERIDIANA_TRACE_GESTURES'):
            from meridiana.gui.backend.gesture_trace import install
            self.gesture_trace = install(self.window)
        if self.window.metaObject().indexOfMethod('altTapped()') >= 0:
            self.alt_tap.tapped.connect(lambda: QMetaObject.invokeMethod(self.window, 'altTapped'))
            self.alt_tap.pressed.connect(lambda x, y: QMetaObject.invokeMethod(
                self.window, 'pointerPressedAt', Q_ARG('QVariant', x), Q_ARG('QVariant', y)))
        if self.window.metaObject().indexOfMethod('setAltHeld(QVariant)') >= 0:
            self.alt_tap.held.connect(lambda down: QMetaObject.invokeMethod(
                self.window, 'setAltHeld', Q_ARG('QVariant', down)))
        self.window.screenChanged.connect(lambda _screen: self.keep_on_screen())
        self.window.visibleChanged.connect(lambda _visible: self.keep_on_screen())
        self._placement = watch_placement(self.window)
        self._closed = False
        self._before_full_screen = None     # R646: the window's state and place before F11, to go back to
        self._disposed = False
        self.layout_state = None
        self.shell.closeRequested.connect(self._shutdown)
        self.file_motion.bind()
        # Install one complete catalogue. Rebuilding every phase toolbar
        # for each of its 90 actions made startup and bindings quadratic.
        self.shell.blockSignals(True)
        try:
            self._bind_commands()
            self.parts.bind()
            self.tasks.bind()
            from meridiana.gui.backend.shell_actions import ShellActions
            self.actions = ShellActions(self)
        finally:
            self.shell.blockSignals(False)
        self.shell.catalogChanged.emit()
        self.shell.changed.emit()
        from meridiana.gui.backend.shell_state import ShellState
        self.layout_state = ShellState(self)
        self.layout_state.restore()
        self._adopt(path)

    def _adopt(self, path):
        """The file the project was read from (the launcher's argument): the title says it, Ctrl+S writes it and it
        enters the recent projects, as when it is opened from the File page (06/11/2026)."""
        session = self.bridge.session
        files = self.engine.rootContext().contextProperty('filesBackend')
        if path is not None:
            if files is not None:
                files.adopt(str(path))
            else:
                session.path = Path(path)
        if files is not None:
            files.stateChanged.connect(self._retitle)
        session.subscribe(lambda _topics: self._retitle())
        self._retitle()

    def _retitle(self):
        """As the Widgets window: «name *» while there is something to save, then « - Meridiana»."""
        if getattr(self, '_closed', False) or not hasattr(self, 'window'):
            return
        session = self.bridge.session
        dirty = session.dirty()
        if session.path is None:
            title = _('Meridiana')
        else:
            title = f"{session.path.name}{' *' if dirty else ''} - Meridiana"
        if self.window.title() != title:
            self.window.setTitle(title)
        # R537: the dot on File, from the same measure (a large project's state takes 50 ms: once per change)
        self.shell.set_project_dirty(dirty)           # Workbench.projectDirty binds it (R23 F6, studio 39)

    def _real_views(self, context, cache, shell):
        """The plan and the 3D of their branches on the shell's session; the Bridge keeps laying the modules out."""
        from meridiana.gui.backend.parts import install_plan, install_scene
        self.parts.install(install_plan)
        self.parts.install(install_scene)

    def _bind_tools(self):
        for command in self.shell.commands_known():
            if command.startswith('tool_'):
                self.shell.register_command(command, lambda cmd=command: self.actions.activate(cmd))

    def _bind_commands(self):
        for phase in self.shell.phases:
            self.shell.register_command('phase_' + phase['id'], lambda pid=phase['id']: self.window.showPhase(pid))
        for command in ('tool_select', 'tool_building', 'rectangle', 'fit', 'zoom_in', 'zoom_out',
                        'view_plan', 'view_3d', 'view_both', 'side_left', 'panel_project', 'panel_properties',
                        'panel_checks', 'default_layout', 'clean_screen', 'next_phase', 'previous_phase',
                        'preferences', 'assistant', 'context_help', 'menu_bar', 'toolbar_text', 'panel_help', 'focus_checks'):
            self.shell.register_command(command, lambda cmd=command: self.window.runCommand(cmd))
        self.shell.register_command('quit', self.window.close)
        self.shell.register_command('fullscreen', self.toggle_full_screen)
        if self.plan is not None:
            self._bind_tools()

    def toggle_full_screen(self):
        """R646: F11 (and View > Full screen) puts the window over the whole screen and takes it back as it was,
        maximized or at its place and size. The window has the system's frame: full screen hides it with the taskbar,
        and its buttons and its drag come back with it. Nothing of it is written in the profile (the window's state is
        not kept there), so a start is never full screen. Esc does not leave it: Esc is the tools'."""
        window = self.window
        if window.visibility() == QWindow.Visibility.FullScreen:
            before, geometry = self._before_full_screen or (QWindow.Visibility.Windowed, None)
            self._before_full_screen = None
            if before == QWindow.Visibility.Maximized:
                window.showMaximized()
            else:
                window.showNormal()
                if geometry is not None:
                    window.setGeometry(geometry)
        else:
            self._before_full_screen = (window.visibility(), window.geometry())
            window.showFullScreen()

    def keep_on_screen(self):
        keep_on_screen(self.window)

    def come_forward(self, token=''):
        """The window in front of the others, taken out of the taskbar when it was there; `token` is the Wayland
        activation token of the start that asks for it [I: not tried on Wayland]."""
        if token:
            os.environ['XDG_ACTIVATION_TOKEN'] = token
        if self.window.visibility() == QWindow.Visibility.Minimized:
            self.window.showNormal()
        self.window.raise_()
        self.window.requestActivate()

    def tell_error(self, text):
        """An exception nobody caught (log.install_excepthook, also from a thread): said in the status bar with where
        the detail is; the window goes on."""
        def say():
            if self._closed:
                return
            line = _('Meridiana ran into an error: {error}').format(error=text)
            if log.file() is not None:
                line += ' ' + _('(the detail is in {file})').format(file=log.file())
            self.shell.show_notice(line, ERROR_MS)
        if threading.current_thread() is threading.main_thread():
            say()
        else:
            QTimer.singleShot(0, self.window, say)

    def open_handed_over(self, files, token=''):
        """A later start handed over its project (main, single_instance.py): the window comes to the front and opens
        the first file as File > Open does, asking first about the unsaved changes (in the File page, where the
        question is); the project already open is only brought forward, not read again. While a dialog of the window
        is open, or a file is being written or read, the project waits."""
        if self._closed:
            return
        self.come_forward(token)
        files_backend = self.parts.controllers.get('files')
        if not files or files_backend is None:
            return
        part = self.parts.controllers.get('filePart')
        if files_backend.busy or (part is not None and part.dialogVisible):
            QTimer.singleShot(HANDED_WAIT_MS, self.window, lambda: self.open_handed_over(files))
            return
        from meridiana.app.project import recovery
        session, target = self.bridge.session, Path(files[0])
        state = self.paths.state
        if session.path is not None and recovery.slot(state, session.path) == recovery.slot(state, target):
            return                                  # the same file (recovery.slot compares the resolved paths)
        if session.dirty() and part is not None:
            part.show_file('open')                  # the question «save first?» stands in the File page
        files_backend.openChosen(str(target))

    def _shutdown(self):
        if self._closed:
            return
        self._closed = True
        if self.gesture_trace is not None:
            self.gesture_trace.close()
        if self.layout_state is not None:
            self.layout_state.save()
        self.bridge.close()
        self.tasks.close()
        self.parts.close()
        from meridiana.gui.backend import scene_context
        scene_context.shutdown()        # r27: the IFC geometry read ahead stopped and waited for, its memory let go

    def _after_frame(self, call):
        """R547: `call` once the window has drawn the frame after now (its next frameSwapped, taken on this thread),
        or after FRAME_WAIT_MS when no frame comes (a window hidden, minimised, or being taken apart)."""
        state = {'done': False}

        def go():
            if state['done']:
                return
            state['done'] = True
            try:
                self.window.frameSwapped.disconnect(go)
            except (RuntimeError, TypeError):
                pass
            if not self._disposed:
                call()
        self.window.frameSwapped.connect(go, Qt.ConnectionType.QueuedConnection)
        self.window.update()
        # the wait counts from the end of what is being done now (the change drawn at once), not from its start
        QTimer.singleShot(0, lambda: QTimer.singleShot(FRAME_WAIT_MS, go))

    def close(self):
        if self._disposed:          # once: after it the window and its engine are gone
            return
        self._disposed = True
        closing = self.parts.controllers.get('closing')
        if closing is not None:
            closing.forced = True       # taken apart by the program (its end, a test): nothing left to ask
        self.window.close()
        self._shutdown()
        self.engine.deleteLater()
        # Take the QML apart now, while the objects its bindings read are still alive. After exec() no loop runs
        # the deleteLater: the interpreter, ending, freed shell and backends first and every binding still reading
        # them said «Cannot read property ... of null», about 400 lines at each close (R451).
        QCoreApplication.sendPostedEvents(self.engine, QEvent.Type.DeferredDelete)
        forget_meta_objects()


def forget_meta_objects():
    """The QMetaObject wrappers PySide still holds, other than the classes' own (staticMetaObject), made invalid: their
    C++ meta-object belonged to a QML object, and goes with it. PySide never invalidates them, and keeps a wrapper for
    every address it has handed out: a new item born at that address came back from childItems() as the old
    QMetaObject (AttributeError: no objectName, inherits, childItems; charts_part.bind on r20-unita, three tests of
    quick.shell.test_interfaccia_r19 in the shell folder on 07/11/2026). A metaObject() asked again makes a new one.
    Nothing is read from them (their memory may be gone already): by identity and address only. Kept: those of a
    class (its staticMetaObject: PySide's in the libraries' own memory, ours in the class), and any meta-object inside
    a loaded library (a C++ class's static one, handed out by an object's metaObject(); invalidated, the class
    attribute would stay invalid: seen in the shell folder on 07/11/2026). Without a way to tell (not Windows), none."""
    import shiboken6
    stale = [w for w in shiboken6.getAllValidWrappers() if type(w) is QMetaObject]
    if not stale:
        return
    in_library = _library_address_test()
    if in_library is None:
        return
    static, pending, seen = set(), [shiboken6.Shiboken.Object], set()
    while pending:                      # every wrapper class, PySide's and ours
        kind = pending.pop()
        if kind in seen:
            continue
        seen.add(kind)
        if 'staticMetaObject' in kind.__dict__:
            static.add(id(kind.__dict__['staticMetaObject']))
        pending.extend(type.__subclasses__(kind))
    for wrapper in stale:
        if id(wrapper) in static:
            continue
        if in_library(shiboken6.getCppPointer(wrapper)[0]):
            continue
        shiboken6.invalidate(wrapper)


def _library_address_test():
    """A function that tells whether an address lies inside a loaded library (a static meta-object), or None where
    it cannot be told. Windows: GetModuleHandleExW. Linux and the other systems with dladdr (the same question to the
    dynamic loader): without it the stale wrappers stayed on Linux, and a test's item came back as a QMetaObject."""
    import ctypes
    if os.name == 'nt':
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetModuleHandleExW.argtypes = (wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.HMODULE))
        module = wintypes.HMODULE()
        # FROM_ADDRESS | UNCHANGED_REFCOUNT
        return lambda address: bool(kernel.GetModuleHandleExW(0x4 | 0x2, ctypes.c_void_p(address), ctypes.byref(module)))

    class DlInfo(ctypes.Structure):
        _fields_ = [('dli_fname', ctypes.c_char_p), ('dli_fbase', ctypes.c_void_p),
                    ('dli_sname', ctypes.c_char_p), ('dli_saddr', ctypes.c_void_p)]
    try:
        dladdr = ctypes.CDLL(None).dladdr
    except (OSError, AttributeError):
        return None
    dladdr.argtypes = (ctypes.c_void_p, ctypes.POINTER(DlInfo))
    dladdr.restype = ctypes.c_int
    info = DlInfo()
    return lambda address: bool(dladdr(ctypes.c_void_p(address), ctypes.byref(info)))


def arguments_parser():
    parser = argparse.ArgumentParser(prog='meridiana', description='Meridiana, the Qt Quick window.')
    parser.add_argument('project', type=Path, nargs='?', default=None,
                        help='The project to open; without it the trial project, in memory (Ctrl+S asks where)')
    parser.add_argument('--large-text', action='store_true')
    parser.add_argument('--plan-renderer', choices=('canvas', 'shapes'), default='shapes')
    parser.add_argument('--profile', type=Path, default=ROOT / 'build/quick-runtime',
                        help='Separate Quick cache and preferences directory')
    return parser


def main(argv=None):
    from meridiana import APP_ID, ENV_PREFIX
    from meridiana.gui import single_instance, startup
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = arguments_parser()
    args, _qt = parser.parse_known_args(argv)
    cache = args.profile.resolve()
    # the language of Settings ('' the desktop's), read before the application: the QML is loaded in it
    preferences = Paths(*(cache / 'quick-profile' / name for name in ('config', 'state', 'data', 'cache')))
    log.setup(preferences.log_file)     # what goes wrong kept in the profile: a package has no console
    log.keep_fatal(preferences.state / 'fatal.log')     # and a crash of the process itself, with its stacks
    log.install_excepthook()            # the window takes over the telling once it exists
    fresh = QGuiApplication.instance() is None
    app = create_app(language=config.load(preferences.config_file).language, arguments=argv)
    if fresh:
        # R542: Qt took its own options out (-platform offscreen, -style ...): the value of one is not a project
        args, _qt = parser.parse_known_args(app.arguments()[1:])
    # Qt's own words too (the buttons of its file dialog where the desktop gives none): «Cancel» stood in the
    # Italian window (R26). After the QML's translator: Qt asks the last one installed first
    from . import qt_translations
    qt_translations.install(app, i18n.language())
    startup.windows_identity(APP_ID)    # the taskbar's identity and the mutex an update looks for (meridiana.iss)
    # one window for every start (R07): a Meridiana already running on this profile takes the project, comes to the
    # front, and this start ends
    explicit = args.project.expanduser().resolve() if args.project else None
    channel = startup.instance_channel(profile=cache)
    if channel and single_instance.hand_over(channel, [str(explicit)] if explicit else [],
                                             os.environ.get('XDG_ACTIVATION_TOKEN', '')):
        return 0
    handed = []                         # what a later start hands over before the window can take it
    receiver = None
    if channel:                         # listened to before the window exists: a start meanwhile waits for it
        receiver = single_instance.Receiver(channel, app)
        receiver.listen()
        receiver.received.connect(lambda files, token: handed.append((files, token)))
    cache.mkdir(parents=True, exist_ok=True)
    if qt_cache.wanted():
        # the compiled QML and the graphics pipelines kept in the profile, for this version alone (study 56): after
        # the single instance, so a start that hands its project over touches nothing of the window running
        from PySide6 import __version__ as qt_version
        from meridiana import __version__
        qt_cache.prepare(cache, qt_cache.key_of(__version__, qt_version), complain=log.complain)
    # the project asked for, or the sample of the checkout when there is one; elsewhere (the Windows package) an
    # empty project. A file that is not a project, damaged or gone, is said in the window: never a start that ends
    # without one (the package has no console to say why)
    project = notice = failed = None
    source = explicit or (SAMPLE if SAMPLE.is_file() else None)
    if source is not None:
        try:
            project, notice = model.Project.load(source)
        except Exception as error:      # noqa: BLE001  whatever the file is: said, and the window opens
            log.complain(f'open {source}', error)
            failed = _('{file} could not be opened: {error}').format(file=source, error=error)
            explicit = None
    if project is None:
        project = model.Project()
    recorded_weather(project, cache)
    # what the window keeps (tiles, underlays, pages, models) gives memory back when the machine gets short (study 56)
    resources.watch(complain=log.complain)
    # the project as data for the heavy jobs, made here at the start and not on the window's thread when the first
    # one is asked (R598: 16-39 ms on model A turning on the sun map)
    from meridiana.app.session import photo_of
    host = QuickWindow(project, cache, large=args.large_text, real_views=True, path=explicit, photo=photo_of(project))
    log.tell_with(host.tell_error)
    copies = host.parts.controllers['recovery']
    copies.claim()                      # the recovery copies of this start are its own while it runs
    if notice:
        host.bridge._error = notice
        host.bridge.stateChanged.emit()
    host.window.show()
    host.parts.controllers['assistant'].windowReady()
    if failed:
        host.shell.show_notice(failed, 0, 'error-open')
    # a copy left by a start that stopped without saving, offered back: with a project asked for by name only its
    # own copy (the copies of the other projects wait for a start without one)
    offered = copies.offer(explicit)
    if receiver is not None:            # from now on straight to the window; what came meanwhile, in order
        receiver.received.disconnect()
        receiver.received.connect(host.open_handed_over)
        for files, token in handed:
            host.open_handed_over(files, token)
    QTimer.singleShot(0, host.bridge.recompute)
    shot = os.environ.get(f'{ENV_PREFIX}_SCREENSHOT')
    # the first start: Meridio offers the guided tour (r29: prepare_workspace and MainWindow._offer_tour). A copy to
    # recover, a project asked for or handed over is the work in hand and comes first; a run for a photograph never
    if not offered and explicit is None and not handed and not shot and host.cfg.tour_status == 'new':
        QTimer.singleShot(TOUR_DELAY_MS, host.parts.controllers['assistant_help'].offerTour)
    if shot:
        # a run for a photograph (the tests, the CI; never the single instance: startup.instance_channel): the window
        # written as a PNG after MERIDIANA_SCREENSHOT_DELAY seconds, then the end
        def take():
            from .capture import grab
            try:
                grab(host.window).save(shot)
            finally:
                app.quit()
        QTimer.singleShot(int(float(os.environ.get(f'{ENV_PREFIX}_SCREENSHOT_DELAY', '3')) * 1000), take)
    code = app.exec()
    log.tell_with(None)
    host.close()
    copies.release()
    if receiver is not None:
        receiver.server.close()
        receiver.deleteLater()
    return code
