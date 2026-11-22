"""R586: every window of the program keeps its content inside its frame, moves with its title and veils the title bar.

Daniel 11/11/2026, «Importa un modello IFC»: (a) «i contenuti della finestra sbordano dalla sua finestra... correggere
per tutte le finestre»; (b) «non si possono spostare trascinandole con il cursore»; (c) «scuriscono correttamente tutto,
ma lasciano non scurita la barra del titolo». Measured on the program's own window (a child process, as R518):
- every window (each M.Dialog the program has made, the windows of File one by one, the IFC import with a model read),
  at three sizes of the main window down to a low one and at 1, 1.25 and 1.5 (the last with the large text): no item of
  the window drawn outside its frame (what is cut by the body's view is not drawn); the title and the buttons inside;
- a window dragged by its title far beyond the main window stops with a strip of its head inside (R628: it stopped
  whole at dialogEdge from the sides before), and opens again in the middle;
- the veil of a modal window reaches the theme, which gives the title bar the veiled colours (Windows 11's DWM and
  Qt's own decoration on Wayland: backend/window_frame.py).

    python -m unittest quick.shell.test_dialoghi_r586
    python tests/quick/shell/test_dialoghi_r586.py shot <folder> <label> [root]   (pictures for the comparison)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup

ROOT = Path(__file__).resolve().parents[3]

CHILD = r'''
import json, os, sys, tempfile
from pathlib import Path
os.environ.setdefault('QSG_RENDER_LOOP', 'basic')
import _setup
from PySide6.QtCore import QEvent, QMetaObject, QObject, QPointF, QRectF, Qt
from meridiana import i18n
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import mouse, pump
from quick.aiuti.differential import connected_fixture

app = _setup.qt_or_skip()
create_app()
i18n.setup('it')
project = connected_fixture()
results, keys, _laid = jobs.layout_of(project)
folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
theme = {'theme': 'light'}
if os.environ.get('R586_TEXT'):
    theme['textSize'] = os.environ['R586_TEXT']
host = QuickWindow(project, Path(folder.name), real_views=True, theme=theme)
host.bridge.accept_layout(host.bridge.session.generation, results, keys)
win = host.window
win.resize(1600, 960)
win.show()
sizes = json.loads(os.environ.get('R586_SIZES', '[[1600, 960], [1100, 640], [900, 440]]'))
shot = os.environ.get('R586_SHOT')
out = {'overflow': {}, 'seen': {}, 'drag': {}, 'scrolls': {}}
ctx = host.engine.rootContext()
part = ctx.contextProperty('filePart')
actions = ctx.contextProperty('plantActions')


def rect_of(obj):
    p = obj.mapToScene(QPointF(0, 0))
    return QRectF(p.x(), p.y(), obj.width(), obj.height())


def shown(obj):
    while obj is not None:
        if not obj.isVisible() or obj.opacity() <= 0:
            return False
        obj = obj.parentItem()
    return True


def walk(root):
    pending = [root]
    while pending:
        obj = pending.pop()
        yield obj
        pending.extend(obj.childItems())


def drawn(item, top):
    """The part of `item` that is drawn: its box cut by every ancestor that clips, up to the window's own item."""
    r = rect_of(item)
    up = item.parentItem()
    while up is not None and up is not top:
        if up.clip():
            r = r.intersected(rect_of(up))
        up = up.parentItem()
    return r


def safe_name(o):
    try:
        return o.objectName()
    except RuntimeError:
        return ''


def frame_of(dialog):
    background = dialog.property('background')
    return background, background.parentItem() if background is not None else None


def measure(name, dialog, where):
    background, top = frame_of(dialog)
    if background is None or not shown(top):
        out['seen'].setdefault(where, {})[name] = 'not shown'
        return
    frame = rect_of(background)
    out['seen'].setdefault(where, {})[name] = [round(frame.x()), round(frame.y()), round(frame.width()), round(frame.height())]
    bad = []
    for obj in walk(top):
        if obj is top or not shown(obj) or obj.width() <= 0 or obj.height() <= 0:
            continue
        if any(k in obj.metaObject().className() for k in ('Shadow', 'ShaderEffect')):
            continue                    # the shadow of a popup is drawn outside its frame on purpose
        r = drawn(obj, top)
        if r.isEmpty():
            continue
        past = max(frame.left() - r.left(), r.right() - frame.right(), frame.top() - r.top(), r.bottom() - frame.bottom())
        if past > 1:
            text = obj.property('text')
            bad.append([obj.metaObject().className().split('_')[0], safe_name(obj), text[:30] if isinstance(text, str) else '', round(past)])
    if bad:
        bad.sort(key=lambda b: -b[3])
        out['overflow'].setdefault(where, {})[name] = bad[:6] + ([len(bad)] if len(bad) > 6 else [])
    view = next((o for o in walk(top) if safe_name(o) == 'dialogView'), None)
    if view is not None and view.property('interactive'):
        out['scrolls'].setdefault(where, []).append(name)


def save(name):
    if shot:
        Path(shot).mkdir(parents=True, exist_ok=True)
        win.grabWindow().save(str(Path(shot) / (name + '.png')))


def file_dialogs():
    dialogs = ctx.contextProperty('filesDialogsBackend')
    kinds = ['ifc', 'new', 'site', 'registry', 'canopy', 'canopy-layout', 'template', 'pvsyst', 'shortcuts', 'update',
             'about', 'report_bug']
    every = [o for r in host.engine.rootObjects() for o in r.findChildren(QObject)]
    overlay = next(o for o in every if safe_name(o) == 'fileDialogOverlay')
    for kind in kinds:
        def opening(kind=kind):
            part.openDialog(kind)
            if kind == 'ifc':                # a model read, with its proposals of place (test_ifc_finestra.found)
                import time
                from quick.pagine.test_ifc_finestra import found
                dialogs._state['fileName'] = 'palazzetto.ifc'
                dialogs._ifc_done(dialogs._generation, found('Cantiere Asti'))
                start = time.time()
                while dialogs.busy and time.time() - start < 30:
                    pump(50)
        yield 'file-' + kind, overlay, opening, lambda: (dialogs.cancel(), part.dismissDialog())


def open_frame():
    """The frame of the window open now: the largest popup of the window's overlay with the common frame."""
    overlay = next(c for c in win.contentItem().childItems() if c.metaObject().className() == 'QQuickOverlay')
    frames = [f for p in overlay.childItems() if p.isVisible() for f in p.childItems() if safe_name(f) == 'dialogFrame']
    return max(frames, key=lambda f: f.width() * f.height()) if frames else None


class Opened:
    """A window found open by its frame (the plant's windows, made by their part: opened by the part's own action)."""
    def __init__(self):
        self.frame = None

    def property(self, name):
        return open_frame() if name == 'background' else None


def plant_dialogs():
    host.shell.trigger('phase_plant')
    pump(600)
    for kind in ('clear', 'sizing', 'storage', 'proposal', 'catalog'):
        yield 'plant-' + kind, Opened(), (lambda kind=kind: actions.open(kind)), actions.dismiss


def program_dialogs():
    every = [o for r in host.engine.rootObjects() for o in r.findChildren(QObject)]
    for o in every:
        try:
            if o.property('acceptOnReturn') is None:
                continue
        except RuntimeError:
            continue
        name = safe_name(o) or o.property('title') or 'dialog'
        if name in ('fileDialogOverlay', 'dxfOptions', 'fileCatalogDialog') or name.startswith('plant-'):
            continue                    # File's and the plant's windows above; DXF and the catalogue open only with their file
        if not o.property('title'):
            o.setProperty('title', 'Titolo di prova')
        yield name, o, (lambda o=o: QMetaObject.invokeMethod(o, 'open')), (lambda o=o: QMetaObject.invokeMethod(o, 'close'))


def dialog_rounds(where):
    names = {}

    def rounds():
        # each list made when its turn comes: the File's windows close the File page, and a part may make its windows
        # again (a Loader)
        yield from file_dialogs()
        yield from list(plant_dialogs())
        yield from list(program_dialogs())
    for name, dialog, opening, closing in rounds():
        n = names.get(name, 0)
        names[name] = n + 1
        key = name if n == 0 else f'{name}-{n}'
        try:
            opening()
            pump(600)
            measure(key, dialog, where)
            if shot and where == os.environ.get('R586_SHOT_SIZE') and key in os.environ.get('R586_SHOT_NAMES', '').split(','):
                save(f'contenuto-{key}')
            closing()
        except RuntimeError:            # a window made again by its page since the list was made (a Loader)
            out['seen'].setdefault(where, {})[key] = 'gone'
        pump(300)


def drag_title(dialog, dx, dy):
    _background, top = frame_of(dialog)
    title = next((o for o in walk(top) if safe_name(o) == 'dialogTitle' and shown(o)), None)
    if title is None:
        return None
    p = title.mapToScene(QPointF(title.width() / 2, title.height() / 2))
    mouse(app, win, QEvent.Type.MouseButtonPress, p, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    pump(30)
    steps = 30
    for i in range(1, steps + 1):
        q = QPointF(p.x() + dx * i / steps, p.y() + dy * i / steps)
        mouse(app, win, QEvent.Type.MouseMove, q, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
        pump(16)
    mouse(app, win, QEvent.Type.MouseButtonRelease, q, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    pump(200)
    return True


def drag_round():
    """A window carried by its title: a little (it moves by as much), then far past the main window (it stops with a
    strip of its head inside, R628), then opened again (in the middle)."""
    plan_backend = host.plan
    from meridiana.i18n import _
    every = [o for r in host.engine.rootObjects() for o in r.findChildren(QObject)]
    small = next(o for o in every if safe_name(o) == 'relayoutConfirmation')
    big = next(o for o in every if safe_name(o) == 'fileDialogOverlay')
    cases = [('relayout', small, lambda: plan_backend.relayoutRequested.emit(_('Lay again automatically'),
                  _('The rows by hand give way to the automatic layout, and the modules taken out by hand come back. '
                    'Undo brings them back. Go on?')),
              lambda: QMetaObject.invokeMethod(small, 'close')),
             ('file-ifc',) + next((d, o, c) for n, d, o, c in file_dialogs() if n == 'file-ifc')]
    for name, dialog, opening, closing in cases:
        opening()
        pump(600)
        background, top = frame_of(dialog)
        start = rect_of(background)
        found = dict(start=[start.x(), start.y(), start.width(), start.height()])
        if drag_title(dialog, -150, -60) is None:
            found['title'] = False
        else:
            moved = rect_of(background)
            found['moved'] = [moved.x() - start.x(), moved.y() - start.y()]
            if shot:
                save(f'trascina-{name}')
            drag_title(dialog, 4000, 3000)
            far = rect_of(background)
            found['far'] = [far.x(), far.y(), far.right(), far.bottom()]
            drag_title(dialog, -8000, -6000)
            near = rect_of(background)
            found['near'] = [near.x(), near.y(), near.right(), near.bottom()]
        closing()
        pump(300)
        opening()
        pump(600)
        again = rect_of(frame_of(dialog)[0])
        found['again'] = [again.x(), again.y()]
        if shot:
            save(f'velo-{name}')
            try:
                colours = host.frame_theme.colours()
            except AttributeError:
                from meridiana.gui.backend import window_frame
                colours = window_frame.frame_colours(host.theme.colors)
            found['caption'] = [colours['ground'].name(), colours['text'].name()]
        closing()
        pump(300)
        out['drag'][name] = found
    out['window'] = [win.width(), win.height()]


try:
    for phase in ('phase_model', 'phase_production', 'phase_consumption', 'phase_plant'):
        host.shell.trigger(phase)        # every part made, with its windows
        pump(800)
    for w, h in sizes:
        win.resize(w, h)
        pump(400)
        dialog_rounds(f'{w}x{h}')
    if os.environ.get('R586_DRAG', '1') == '1':
        w, h = sizes[-1]
        win.resize(w, h)
        pump(400)
        drag_round()
finally:
    host.close()
    pump(50)
    folder.cleanup()
print('R586 ' + json.dumps(out))
'''


def measure(scale, text='', sizes=None, shot=None, root=ROOT, extra=None):
    work = Path(tempfile.mkdtemp(prefix='meridiana-r586-'))
    screen = work / 'screen.json'
    screen.write_text('{"screens": [{"name": "R586", "x": 0, "y": 0, "width": 4000, "height": 2400, '
                      '"logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}', encoding='utf8')
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(Path(root) / 'tests'), str(Path(root) / 'src')]),
               QT_QPA_PLATFORM='offscreen:configfile=' + os.path.relpath(screen, root).replace(os.sep, '/'),
               QSG_RENDER_LOOP='basic', QT_SCALE_FACTOR=str(scale), PYTHONUTF8='1', MERIDIANA_PRELOAD='0',
               APPDATA=str(work / 'APPDATA'), LOCALAPPDATA=str(work / 'LOCALAPPDATA'))
    if text:
        env['R586_TEXT'] = text
    if sizes:
        env['R586_SIZES'] = json.dumps(sizes)
    if shot:
        env['R586_SHOT'] = str(shot)
    env.update(extra or {})
    try:
        done = subprocess.run([sys.executable, '-c', CHILD], cwd=root, env=env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', timeout=600)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    lines = [line for line in done.stdout.splitlines() if line.startswith('R586 ')]
    if not lines:
        raise AssertionError(done.stderr[-3000:])
    return json.loads(lines[-1][5:])


class Windows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from concurrent.futures import ThreadPoolExecutor
        runs = {1: '', 1.25: '', 1.5: 'large'}
        with ThreadPoolExecutor(3) as pool:
            done = {s: pool.submit(measure, s, t, extra={'R586_DRAG': '1' if s == 1 else '0'}) for s, t in runs.items()}
            cls.seen = {s: f.result() for s, f in done.items()}

    def test_r586_nothing_of_a_window_outside_its_frame(self):
        for scale, m in self.seen.items():
            with self.subTest(scale=scale):
                for where, found in m['seen'].items():
                    shown = [k for k, v in found.items() if isinstance(v, list)]
                    # every window of File, the IFC import with its model among them, and the program's own
                    self.assertGreaterEqual(len(shown), 30, (where, found))
                    self.assertIn('file-ifc', shown)
                self.assertEqual(m['overflow'], {}, m['overflow'])

    def test_r586_a_tall_window_scrolls_its_body_in_a_low_main_window(self):
        low = self.seen[1]['scrolls'].get('900x440', [])
        self.assertIn('file-ifc', low)
        self.assertNotIn('file-ifc', self.seen[1]['scrolls'].get('1600x960', []))

    def test_r586_the_title_carries_the_window_and_it_stays_inside(self):
        """R628 (Daniel 15/11/2026: «me lo fa spostare solo all'interno di un ristrettissimo range di movimento»): the
        window goes anywhere over the main window and past its sides, keeping a strip of its head inside on every side
        (ControlMetrics.dialogHold, 56) and its head never above the top; it opens again where it opened."""
        m = self.seen[1]
        width, height = m['window']
        hold = 56
        for name, found in m['drag'].items():
            with self.subTest(name=name, found=found):
                self.assertNotEqual(found.get('title'), False)
                # by as much as asked, or up to the top of the main window (the IFC import fills the low window)
                self.assertAlmostEqual(found['moved'][0], -150, delta=2)
                self.assertAlmostEqual(found['moved'][1], max(-60, -found['start'][1]), delta=2)
                x, y, right, bottom = found['far']
                tall = min(hold, bottom - y)
                self.assertAlmostEqual(x, width - hold, delta=1, msg='past the right side, a strip of the head inside')
                self.assertAlmostEqual(y, height - tall, delta=1, msg='past the bottom, a strip of the head inside')
                nx, ny, nright, _nbottom = found['near']
                self.assertAlmostEqual(nright, hold, delta=1, msg='past the left side, a strip of the head inside')
                self.assertAlmostEqual(ny, 0, delta=1, msg='the head never above the top')
                self.assertAlmostEqual(found['again'][0], found['start'][0], delta=1)
                self.assertAlmostEqual(found['again'][1], found['start'][1], delta=1)


class Sources(unittest.TestCase):
    """R586: one window for the program. Every window is the common M.Dialog (the File's ones through DialogWindow),
    and none places, sizes or frames itself: what it asks goes in implicitWidth/implicitHeight (homeX/homeY for a
    place of its own), its content is declared inside it."""

    QML = ROOT / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana'
    OPEN = re.compile(r'(?:^|[\s{;])(?:M|MC|Controls)\.Dialog\s*\{|(?:^|\s)DialogWindow\s*\{', re.M)
    OWN = re.compile(r'(?:^|[\s{;])(contentItem|anchors\.\w+|x|y|width|height)\s*:')

    def blocks(self, text):
        for m in self.OPEN.finditer(text):
            start = text.index('{', m.start())
            depth, top = 0, []
            for i in range(start, len(text)):
                c = text[i]
                if c == '{':
                    depth += 1
                    if depth == 1:
                        continue
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        break
                if depth == 1:
                    top.append(c)
            yield text.count('\n', 0, m.start()) + 1, ''.join(top)

    def test_r586_no_window_places_sizes_or_frames_itself(self):
        found, wrong = 0, []
        for path in self.QML.rglob('*.qml'):
            if path.name in ('Dialog.qml', 'Gallery.qml'):
                continue
            text = path.read_text(encoding='utf8')
            for line, top in self.blocks(text):
                found += 1
                own = sorted({m.group(1) for m in self.OWN.finditer(
                    '\n'.join(t.split('//')[0] for t in top.splitlines()))})
                if own:
                    wrong.append((path.relative_to(self.QML).as_posix(), line, own))
        self.assertGreaterEqual(found, 30)
        self.assertEqual(wrong, [])

    def test_r586_no_window_of_its_own(self):
        """The other modal frames of the program are gone into M.Dialog: no modal popup outside Controls."""
        own = [path.relative_to(self.QML).as_posix() for path in self.QML.rglob('*.qml')
               if path.parent.name != 'Controls' and re.search(r'^\s*modal:\s*true', path.read_text(encoding='utf8'), re.M)]
        self.assertEqual(own, [])


class TitleBarVeil(unittest.TestCase):
    """R586 (c): the veil of a modal window shown tells the theme; the frame's colours are then veiled."""

    def setUp(self):
        self.app = _setup.qt_or_skip()

    def test_r586_a_modal_window_veils_the_title_bar_where_the_program_colours_it(self):
        from PySide6.QtCore import QMetaObject, QObject
        from PySide6.QtGui import QColor, QGuiApplication, QPalette
        from PySide6.QtQml import QQmlApplicationEngine
        from meridiana.gui.backend import window_frame
        from meridiana.gui.backend.controls import install_controls
        engine = QQmlApplicationEngine()
        theme = install_controls(engine, {'theme': 'light'})
        engine.loadData(b'''import QtQuick
import Meridiana.Controls as M
Window { width: 600; height: 400; visible: true
    M.Dialog { objectName: "probe"; title: "Titolo"; acceptText: "OK"; M.Label { text: "Testo" } } }''')
        window = engine.rootObjects()[0]
        dialog = window.findChild(QObject, 'probe')
        keeper = window_frame.FrameTheme(theme)
        plain = keeper.colours()
        before = QGuiApplication.palette()
        sent = []
        try:
            with mock.patch.object(window_frame, 'draws_own_frame', return_value=True), \
                    mock.patch.object(window_frame, 'set_frame_colours', side_effect=lambda w, c: sent.append(c)), \
\
                    mock.patch.object(window_frame, 'set_dark_frame', return_value=True):
                self.assertIsNone(theme.veil_colour())
                QMetaObject.invokeMethod(dialog, 'open')
                _setup.wait_for(lambda: theme.veil_colour() is not None, 3000)
                veil = theme.veil_colour()
                self.assertIsNotNone(veil)
                self.assertGreater(veil.alpha(), 0)
                veiled = keeper.colours()
                self.assertEqual(veiled['ground'].name(), window_frame.veiled(plain['ground'], veil).name())
                self.assertNotEqual(veiled['ground'].name(), plain['ground'].name())
                # Wayland, Qt's own decoration: the application palette's Window (what it paints) is the veiled one
                self.assertEqual(QGuiApplication.palette().color(QPalette.ColorRole.Window).name(), veiled['ground'].name())
                # Windows 11: the colours sent to DWM for every window of the program
                keeper.frame(window)
                self.assertEqual(sent[-1]['ground'].name(), veiled['ground'].name())
                QMetaObject.invokeMethod(dialog, 'close')
                _setup.wait_for(lambda: theme.veil_colour() is None, 3000)
                self.assertIsNone(theme.veil_colour())
                self.assertEqual(QGuiApplication.palette().color(QPalette.ColorRole.Window).name(), plain['ground'].name())
                self.assertEqual(QColor(sent[-1]['ground']).name(), plain['ground'].name())
        finally:
            QGuiApplication.setPalette(before)
            window.close()
            engine.deleteLater()


def shots(folder, label, root=ROOT):
    """The pictures for the comparison: the low main window, the IFC import and a short question."""
    sizes = [[900, 440]]
    extra = {'R586_SHOT_SIZE': '900x440', 'R586_SHOT_NAMES': 'file-ifc,relayoutConfirmation'}
    found = measure(1, sizes=sizes, shot=Path(folder) / label, root=root, extra=extra)
    (Path(folder) / label / 'misure.json').write_text(json.dumps(found, indent=1), encoding='utf8')
    return found


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'shot':
        print(json.dumps(shots(sys.argv[2], sys.argv[3], Path(sys.argv[4]) if len(sys.argv) > 4 else ROOT), indent=1))
    else:
        unittest.main()
