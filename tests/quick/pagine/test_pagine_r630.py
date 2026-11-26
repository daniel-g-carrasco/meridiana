"""R630 (Daniel 15/11/2026): «il passaggio tra una pagina e l'altra di File e delle impostazioni è molto lento e
scattante, e la transizione poco smooth [...] non mi piace il titolo generico tra più pagine con scritto "Settings"».

1. A section's page is made once and kept: shown again, it is the same page, and nothing is made at the passage.
2. The passage between two sections stays under a threshold: the click itself (the backend told, the page shown)
   under CLICK_MS, the window's longest stand-still under BEAT_MS (tests/quick/aiuti/finestra_libera.py) where the
   frames are on the render thread, under SOFTWARE_BEAT_MS with Qt's software renderer (off screen), whose frames are
   on the window's thread. Before R630 a change of section of the Settings was 0.3-3 s of the window's thread
   (every binding of the page asked Python the fields of the section again, docs/quick/stato/r35-pagine-file.md).
3. The title of a page is the name of its entry in the column on the left, in File and in the Settings.
4. On a graphics API the pages not shown are made ahead between the frames (asynchronous incubation, which Qt does not
   run off screen with its software renderer): drawn by a QQuickRenderControl in a process of its own, with an
   incubation controller as Qt's, every page made ahead is there and comes when asked.

    python -m unittest quick.pagine.test_pagine_r630
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QObject

from quick.aiuti.finestra_libera import software_frames, window_stays_free
from quick.aiuti.tempi import check_timing, timed

setUpModule = _setup.keep_global_state

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

ROOT = Path(__file__).resolve().parents[3]
CLICK_MS = 50
BEAT_MS = 50
SOFTWARE_BEAT_MS = 100
NO_RHI = 3
FILE = ['open', 'save', 'export', 'catalogues', 'help']
SETTINGS = ['preferences:' + k for k in ('appearance', 'navigation', 'keyboard', 'assistant', 'report', 'maps',
                                          'performance', 'privacy')]


class NoJobs:
    """The window's guard without a jobs' center: the File page has none, only the beat is measured."""
    def reset_stats(self):
        self.reset = True

    def stats(self):
        return {'longest_call': (0.0, ''), 'calls': 0}


def kept(right):
    return {item.property('modelData'): item for item in right.childItems()
            if item.metaObject().className().startswith('QQuickLoader')}


def shown_named(root, name):
    """The items called `name` that are on show (visible with all their ancestors)."""
    found, pending = [], [root]
    while pending:
        item = pending.pop()
        if not item.isVisible():
            continue
        if item.objectName() == name:
            found.append(item)
        pending.extend(item.childItems())
    return found


class KeptPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        from meridiana.gui.backend.files_page import build_page
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.tmp.cleanup)
        self.host = build_page('file', folder=Path(self.tmp.name))
        self.addCleanup(self.host.close)
        self.window = self.host.window
        self.window.show()
        self.assertTrue(_setup.wait_until(self.app, self.window.isExposed))
        self.page = self.window.findChild(QObject, 'filePage')
        self.right = self.window.findChild(QObject, 'fileRight')

    def arrived(self):
        """How far in the page asked for is (before R630, the side's opacity: the same test can be run there)."""
        arrival = self.page.property('arrival')
        return self.right.opacity() if arrival is None else arrival

    def go(self, section):
        self.host.files.selectSection(section)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.page.property('displayedSection') == section
                                          and not self.page.property('changing') and self.arrived() == 1), section)

    def test_1_a_section_seen_again_is_the_same_page(self):
        def items(item):
            return 1 + sum(items(child) for child in item.childItems())
        for section in FILE + SETTINGS:
            self.go(section)
        loaders = kept(self.right)
        self.assertTrue(all(loaders[key].childItems() for key in FILE + SETTINGS), 'every page asked is made')
        # a page fills a part of itself after it is made (Meridio's page its list, on the CI's runner and in the WSL
        # 72 items later): the count is read once it holds still for half a second
        seen = [None, time.monotonic()]

        def still():
            now = {key: items(loaders[key]) for key in FILE + SETTINGS}
            if now != seen[0]:
                seen[0], seen[1] = now, time.monotonic()
            return time.monotonic() - seen[1] >= 0.5
        self.assertTrue(_setup.wait_until(self.app, still, 15), 'the pages kept changing')
        before = seen[0]
        for section in ['save', 'preferences:navigation', 'open', 'preferences:privacy']:
            self.go(section)
        # the same pages, nothing made or let go (on r34-unita the Settings had one page, made again at each section)
        self.assertEqual(before, {key: items(kept(self.right)[key]) for key in FILE + SETTINGS})

    @timed('no call of the window over its few ms')
    def test_2_the_passage_between_two_sections_stays_quick(self):
        for section in FILE + SETTINGS:              # every page made once (off screen they are made when asked)
            self.go(section)
        beat = SOFTWARE_BEAT_MS if software_frames(self.window) else BEAT_MS
        for ring in (SETTINGS + [SETTINGS[0]], FILE + ['open'], ['open', 'preferences:appearance', 'open']):
            self.go(ring[0])
            for section in ring[1:]:
                with window_stays_free(NoJobs(), beat_ms=beat):
                    start = time.perf_counter()
                    self.host.files.selectSection(section)
                    click = (time.perf_counter() - start) * 1000
                    # on r34-unita: 300-3 000 ms for a section of the Settings
                    check_timing(click < CLICK_MS, f'{section}: the click took {click:.0f} ms (limit {CLICK_MS} ms)')
                    self.go(section)
                shown = kept(self.right)[self.page.property('currentPage')]
                self.assertTrue(shown.isVisible() and shown.property('item') is not None, section)

    def test_3_the_title_is_the_name_of_the_entry(self):
        words = self.host.files.words
        for section in FILE + SETTINGS:
            self.go(section)
            titles = shown_named(self.right, 'settingsTitle' if section in SETTINGS else 'fileSectionTitle')
            self.assertEqual([words[section.replace('preferences:', '')]], [t.property('text') for t in titles], section)
            self.assertNotEqual(words['preferences'], titles[0].property('text'), section)


def made_ahead() -> int:
    """The process of the graphics API: the File page drawn by a QQuickRenderControl, frames and incubation as Qt's
    render loop does (a slice of a third of a frame after each frame); every page made ahead, then asked."""
    os.environ.update({'QT_QPA_PLATFORM': 'offscreen', 'QT_QUICK_BACKEND': 'rhi', 'QSG_RENDER_LOOP': 'basic'})
    from PySide6.QtCore import QSize, QTimer, QUrl
    from PySide6.QtGui import QGuiApplication, QRhiColorAttachment, QRhiTexture, QRhiTextureRenderTargetDescription
    from PySide6.QtQml import QQmlComponent, QQmlIncubationController
    from PySide6.QtQuick import QQuickRenderControl, QQuickRenderTarget, QQuickWindow
    from PySide6.QtQuickControls2 import QQuickStyle
    QQuickStyle.setStyle('Basic')
    _app = QGuiApplication.instance() or QGuiApplication([])     # kept for the whole run
    from PySide6.QtQml import QQmlEngine
    from meridiana import i18n
    from meridiana.app.platform import config
    from meridiana.app.platform.paths import Paths
    from meridiana.app.session import ProjectSession
    from meridiana.core.model import model
    from meridiana.data.registry import Registry
    from meridiana.gui.backend.controls import install_controls
    from meridiana.gui.backend.dialogs import DialogsBackend
    from meridiana.gui.backend.files import FilesBackend
    from meridiana.gui.backend.settings import SettingsBackend
    i18n.setup('it')
    out = {}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        paths = Paths(*(Path(folder) / p for p in ('config', 'state', 'data', 'cache')))
        paths.data.mkdir(parents=True, exist_ok=True)
        cfg = config.load(paths.config_file)
        session = ProjectSession(model.Project())
        engine = QQmlEngine()
        theme = install_controls(engine, {'theme': 'light'})
        registry = Registry(paths.data / 'registry.sqlite3')
        files = FilesBackend(session, cfg, paths, registry=registry)
        settings = SettingsBackend(cfg, paths.config_file, theme)
        dialogs = DialogsBackend(session, cfg, paths)
        dialogs.set_registry(registry)
        for name, value in dict(filesPageBackend=files, settingsPageBackend=settings, dialogsPageBackend=dialogs).items():
            engine.rootContext().setContextProperty(name, value)
        control = QQuickRenderControl()
        window = QQuickWindow(control)
        size = QSize(1366, 860)
        window.resize(size)
        if not control.initialize():
            return NO_RHI
        rhi = control.rhi()
        texture = rhi.newTexture(QRhiTexture.Format.RGBA8, size, 1, QRhiTexture.Flag.RenderTarget)
        texture.create()
        target = rhi.newTextureRenderTarget(QRhiTextureRenderTargetDescription(QRhiColorAttachment(texture)))
        passes = target.newCompatibleRenderPassDescriptor()
        target.setRenderPassDescriptor(passes)
        target.create()
        window.setRenderTarget(QQuickRenderTarget.fromRhiRenderTarget(target))

        class Incubation(QQmlIncubationController):
            pass
        incubation = Incubation()
        engine.setIncubationController(incubation)
        component = QQmlComponent(engine)
        component.setData(b'''import QtQuick
import Meridiana.Theme
FilePage { backend: filesPageBackend; settingsBackend: settingsPageBackend; dialogsBackend: dialogsPageBackend }''',
                          QUrl.fromLocalFile(str(ROOT / 'src/meridiana/gui/qml/Meridiana/File/R630Host.qml')))
        page = component.create()
        if page is None:
            raise RuntimeError('\n'.join(e.toString() for e in component.errors()))
        page.setParentItem(window.contentItem())
        page.setWidth(size.width())
        page.setHeight(size.height())

        def frame():
            control.polishItems()
            control.beginFrame()
            control.sync()
            control.render()
            control.endFrame()
            incubation.incubateFor(5)
        timer = QTimer()
        timer.setInterval(16)
        timer.timeout.connect(frame)
        timer.start()

        def turn(seconds, until=lambda: False):
            from PySide6.QtCore import QEventLoop
            end = time.perf_counter() + seconds
            while time.perf_counter() < end and not until():
                loop = QEventLoop()
                QTimer.singleShot(2, loop.quit)
                loop.exec()
        from PySide6.QtCore import QMetaObject
        QMetaObject.invokeMethod(page, 'enter')                 # File coming in, as WorkbenchFile does
        right = page.findChild(QObject, 'fileRight')
        turn(60, lambda: page.property('ahead') and incubation.incubatingObjectCount() == 0
             and all(loader.property('progress') == 1 for key, loader in kept(right).items() if key != 'dialogs'))
        out['api'] = str(window.rendererInterface().graphicsApi().name)
        out['asynchronous'] = {key: bool(loader.property('asynchronous')) for key, loader in kept(right).items()}
        out['ready'] = {key: loader.property('progress') == 1 and bool(loader.childItems())
                        for key, loader in kept(right).items()}
        out['passages'] = []
        for section in ['save', 'preferences:appearance', 'preferences:report', 'help', 'open']:
            start = time.perf_counter()
            files.selectSection(section)
            click = (time.perf_counter() - start) * 1000
            turn(3, lambda s=section: page.property('displayedSection') == s and page.property('arrival') == 1
                 and not page.property('changing'))
            shown = kept(right)[page.property('currentPage')]
            titles = shown_named(right, 'settingsTitle' if section.startswith('preferences') else 'fileSectionTitle')
            out['passages'].append(dict(section=section, click_ms=round(click, 1),
                                        displayed=page.property('displayedSection'), arrival=page.property('arrival'),
                                        visible=shown.isVisible(), titles=[t.property('text') for t in titles]))
        out['words'] = files.words
        timer.stop()
        # let go in Qt's order (gui/paper/report_3d.py): the target before the render control, the engine last
        import shiboken6
        window.setRenderTarget(QQuickRenderTarget())
        page.setParentItem(None)
        for thing in (target, passes, texture, page, window, control, component):
            if shiboken6.isValid(thing):
                shiboken6.delete(thing)
        for provider in (settings, dialogs, files):
            provider.close()
        shiboken6.delete(engine)
        registry.close()
    print('R630 ' + json.dumps(out, ensure_ascii=False), flush=True)
    return 0


class MadeAheadTest(unittest.TestCase):
    def test_4_on_a_graphics_api_the_pages_made_ahead_appear(self):
        env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(p) for p in (ROOT / 'src', ROOT / 'tests')),
                   QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='rhi', QSG_RENDER_LOOP='basic', PYTHONUTF8='1')
        done = subprocess.run([sys.executable, '-m', 'quick.pagine.test_pagine_r630', '--made-ahead'], cwd=ROOT,
                              env=env, capture_output=True, text=True, timeout=300)
        if done.returncode == NO_RHI:
            self.skipTest('Qt Quick has no RHI here: the pages are made as they are asked (software renderer)')
        self.assertEqual(0, done.returncode, done.stderr[-3000:])
        found = json.loads(next(line for line in done.stdout.splitlines() if line.startswith('R630 '))[5:])
        self.assertNotEqual('Software', found['api'])
        made = {k: v for k, v in found['ready'].items() if k != 'dialogs'}
        self.assertTrue(made and all(made.values()), f'pages not made ahead: {made}')
        words = found['words']
        for passage in found['passages']:
            section = passage['section']
            self.assertEqual((section, 1, True), (passage['displayed'], passage['arrival'], passage['visible']), passage)
            self.assertEqual([words[section.replace('preferences:', '')]], passage['titles'], passage)
            self.assertLess(passage['click_ms'], CLICK_MS, passage)


if __name__ == '__main__':
    if '--made-ahead' in sys.argv:
        raise SystemExit(made_ahead())
    unittest.main()
