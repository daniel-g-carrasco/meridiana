"""Separate Quick application. The existing Widgets entry point is untouched."""
import argparse
import os
from pathlib import Path

from PySide6.QtCore import Q_ARG, QCoreApplication, QEvent, QMetaObject, QPoint, QRect, Qt, QTimer, QUrl
from PySide6.QtGui import QFont, QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from meridiana import config, i18n, model, resources
from meridiana.paths import Paths
from meridiana.i18n import _
from meridiana.ui.design import Type
from meridiana.ui.theme import _font_families

from .backend.tokens import ThemeTokens, install_theme
from .backend.shell import ShellController, labels
from .backend.shell_compute import ShellBridge
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


def create_app(language='it'):
    """The application of the Quick window, speaking `language` ('' the desktop's: the program's own start, with the
    preference of Settings; the tests and the tools keep Italian)."""
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    os.environ['QT_DISABLE_SHADER_DISK_CACHE'] = '1'
    QQuickStyle.setStyle('Basic')
    # r23-unita (r22-flatpak: Niri saw the Quick window as «python3», without Meridiana's icon): the desktop file's
    # name is the Wayland app_id the compositor matches with io.github.daniel_g_carrasco.meridiana.desktop and its
    # icon, the application's name the X11 window class (WM_CLASS), as the Widgets window does (app.py)
    from meridiana import APP_ID, APP_NAME
    QGuiApplication.setApplicationName(APP_NAME)
    QGuiApplication.setDesktopFileName(APP_ID)
    app = QGuiApplication.instance() or QGuiApplication(['meridiana-quick'])
    # Read by Qt when the first Quick window is made, after this.
    os.environ.setdefault('QSG_RENDER_LOOP', render_loop(app.platformName(), os.environ.get('QT_QUICK_BACKEND', '')))
    i18n.setup(language)
    i18n.share_with_children()      # the computation's and the tasks' processes speak it too
    if i18n.language() != 'it':
        from PySide6.QtCore import QLocale
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedKingdom))
    from .translator import install
    install(app)                    # the QML's qsTr through po/it.po
    font = QFont(_font_families('plex')[0])
    font.setPixelSize(Type.BODY)
    app.setFont(font)
    return app


FRAME_WAIT_MS = 120   # R547: the longest wait for the frame that shows a change before the other views hear it
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
    def __init__(self, project, cache, *, large=False, theme=None, real_views=False, path=None):
        self.bridge = ShellBridge(project, cache)
        from .backend import scene_context
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
            self.cfg.extra['reduced_motion'] = options['reducedMotion']
        self.shell = ShellController(self.bridge)
        from .backend.parts import Parts
        self.parts = Parts(self.engine, self.bridge.session, cache, self)
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
        from meridiana.paths import shipped
        mascot = shipped('meridio', 'meridio.svg') or ROOT / 'data/meridio/meridio.svg'
        context.setContextProperty('mascotSource', QUrl.fromLocalFile(str(mascot)))
        from .backend.controls import install_controls
        install_controls(self.engine)
        source = Path(__file__).parent / 'qml/Meridiana/Shell/Workbench.qml'
        if real_views:
            self._real_views(context, cache, source.parent)
            self.parts.discover()
            self.engine.setInitialProperties(self.parts.initial_properties())
        from .backend.shell_tasks import ShellTasks
        self.tasks = ShellTasks(self)
        context.setContextProperty('shellTasks', self.tasks)
        from .backend.shell_motion import FileMotion
        self.file_motion = FileMotion(self)
        context.setContextProperty('motion', self.file_motion)          # R483: the phases' transition
        self.engine.load(QUrl.fromLocalFile(str(source)))
        if not self.engine.rootObjects():
            raise RuntimeError('QML did not create a window: ' + '\n'.join(self.warnings))
        self.window = self.engine.rootObjects()[0]
        # R547: a change of the modules drawn first, the rest of the views told after the frame (session.later)
        self.bridge.session.later = self._after_frame
        # R482, R481: the title bars in the theme; Alt read for the whole window (backend/window_frame.py)
        from .backend.window_frame import AltTap, FrameTheme
        self.frame_theme = FrameTheme(self.theme, self.window)
        self.alt_tap = AltTap(self.window, self.window)
        if self.window.metaObject().indexOfSignal('phaseChanged()') >= 0:
            from .backend import activity          # r27: a change of phase is the designer at work (activity.py)
            self.window.phaseChanged.connect(activity.touch)
        # R545: two fingers on a touchpad under Wayland at the pace of the other programs (backend/touchpad.py)
        from .backend.touchpad import TouchpadPace
        self.touchpad_pace = TouchpadPace(self.window)
        if self.touchpad_pace.active:
            self.touchpad_pace.follow(QGuiApplication.instance())
        # R556: two fingers on a touchpad under Windows taken as on Linux, not for a mouse wheel (backend/touchpad.py)
        from .backend.touchpad import WindowsTouchpad
        self.windows_touchpad = WindowsTouchpad(self.window)
        if self.windows_touchpad.active:
            self.windows_touchpad.follow(QGuiApplication.instance())
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
            from .backend.shell_actions import ShellActions
            self.actions = ShellActions(self)
        finally:
            self.shell.blockSignals(False)
        self.shell.catalogChanged.emit()
        self.shell.changed.emit()
        from .backend.shell_state import ShellState
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
        from .backend.parts import install_plan, install_scene
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
        if self.plan is not None:
            self._bind_tools()

    def keep_on_screen(self):
        keep_on_screen(self.window)

    def _shutdown(self):
        if self._closed:
            return
        self._closed = True
        if self.layout_state is not None:
            self.layout_state.save()
        self.bridge.close()
        self.tasks.close()
        self.parts.close()
        from .backend import scene_context
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
    if not stale or os.name != 'nt':
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
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleExW.argtypes = (wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.HMODULE))
    module = wintypes.HMODULE()
    for wrapper in stale:
        if id(wrapper) in static:
            continue
        # FROM_ADDRESS | UNCHANGED_REFCOUNT: is the address inside a loaded module (a static meta-object)?
        if kernel.GetModuleHandleExW(0x4 | 0x2, ctypes.c_void_p(shiboken6.getCppPointer(wrapper)[0]),
                                     ctypes.byref(module)):
            continue
        shiboken6.invalidate(wrapper)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path, nargs='?', default=None,
                        help='The project to open; without it the trial project, in memory (Ctrl+S asks where)')
    parser.add_argument('--large-text', action='store_true')
    parser.add_argument('--plan-renderer', choices=('canvas', 'shapes'), default='shapes')
    parser.add_argument('--profile', type=Path, default=ROOT / 'build/quick-runtime',
                        help='Separate Quick cache and preferences directory')
    args, _qt = parser.parse_known_args()      # R542: Qt's own options (-platform ...) as `meridiana` gets them
    cache = args.profile.resolve()
    # the language of Settings ('' the desktop's), read before the application: the QML is loaded in it
    preferences = Paths(*(cache / 'quick-profile' / name for name in ('config', 'state', 'data', 'cache')))
    app = create_app(language=config.load(preferences.config_file).language)
    from meridiana.app import windows_identity
    from meridiana import APP_ID
    windows_identity(APP_ID)        # the taskbar's identity and the mutex an update looks for (meridiana.iss)
    cache.mkdir(parents=True, exist_ok=True)
    # the sample of the checkout when there is one; elsewhere (the Windows package) an empty project
    project, notice = (model.Project.load(args.project or SAMPLE) if args.project or SAMPLE.is_file()
                       else (model.Project(), None))
    recorded_weather(project, cache)
    host = QuickWindow(project, cache, large=args.large_text, real_views=True,
                       path=args.project.resolve() if args.project else None)
    if notice:
        host.bridge._error = notice
        host.bridge.stateChanged.emit()
    host.window.show()
    QTimer.singleShot(0, host.bridge.recompute)
    code = app.exec()
    host.close()
    return code
