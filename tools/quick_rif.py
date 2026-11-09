"""Capture the real Widgets application for Quick compatibility (R389).

Run with the project Python: ``python tools/quick_rif.py --matrix``. Each
fixture/scale has its own process, isolated settings and offline recorded
weather. The same window changes theme and size, retaining its calculated year.
Windows captures require Direct3D 11, never offscreen.
``--offscreen`` is an explicitly labelled diagnostic, not a native reference.
PNG files go to build/riferimento, deterministic gzip JSON to
docs/quick/compat/riferimento. Existing captures are never overwritten: select
another --run name. --list prints the matrix without opening any window.

Geometry uses logical pixels relative to the main client area. IDs are stable
QObject ancestry paths, not memory addresses. ``aliases`` exposes MainWindow
attribute names. Palette roles are Qt's effective widget palette, not guessed
pixel colours; stylesheet and custom-painted surfaces remain in the PNG.
"""
from __future__ import annotations

import argparse
import faulthandler
import gzip
import hashlib
import itertools
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RHO = ROOT / 'docs/quick/compat/fixtures/rho.meridiana'
SIZES = ((1366, 900), (1600, 960), (1920, 1080))
PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')
SETTINGS = ('appearance', 'navigation', 'assistant', 'report', 'maps', 'privacy', 'keyboard')
MENUS = ('file', 'edit', 'draw', 'view', 'catalogues', 'site', 'compute', 'variants', 'help')


def capture_matrix():
    return [dict(fixture=f, theme=t, scale=s, size=list(z))
            for f, t, s, z in itertools.product(('empty', 'rho'), ('light', 'dark'), (1, 2), SIZES)]


def state_names():
    return [*(f'phase-{p}' for p in PHASES), 'model-building', 'plant-subfield',
            'plant-inverters', 'plant-strings', 'plant-storage',
            *(f'file-{p}' for p in ('new', 'open', 'registry', 'save', 'export', 'catalogues', 'help')),
            *(f'settings-{p}' for p in SETTINGS), *(f'menu-{m}' for m in MENUS), 'meridio']


def write_canonical(path: Path, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(gzip.compress(data, compresslevel=9, mtime=0))


def capture_complete(run, name, states):
    """Resume only a complete case whose recorded PNG hashes still match."""
    manifest_path = ROOT / 'docs/quick/compat/riferimento' / run / name / 'manifest.json.gz'
    if not manifest_path.exists():
        return False
    saved = json.loads(gzip.decompress(manifest_path.read_bytes()))
    if {c['state'] for c in saved['captures']} != set(states):
        raise ValueError(f'Cannot resume a batch with different states: {name}')
    for capture in saved['captures']:
        snap = json.loads(gzip.decompress((ROOT / capture['json']).read_bytes()))
        photo = ROOT / capture['png']
        if hashlib.sha256(photo.read_bytes()).hexdigest() != snap['meta']['png_sha256']:
            raise ValueError(f'Damaged capture: {photo}')
    return True


def widget_snapshot(window, *, meta=None, popups=()):
    """Describe visible widgets, menu actions and model-view cells, including fonts."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QColor, QFontInfo, QPalette
    from PySide6.QtWidgets import QAbstractItemView, QComboBox, QListView, QMenu, QWidget

    aliases = {}
    for name, obj in vars(window).items():
        if isinstance(obj, QWidget):
            aliases.setdefault(id(obj), []).append(name)
    rows = []

    def text_of(widget):
        for prop in ('text', 'currentText', 'toPlainText', 'title', 'placeholderText'):
            attr = getattr(widget, prop, None)
            if isinstance(attr, str):
                return attr
            if callable(attr):
                try:
                    value = attr()
                except TypeError:
                    continue
                if isinstance(value, str):
                    return value
        return ''

    def walk(widget, path):
        if not widget.isVisible() or widget.width() <= 0 or widget.height() <= 0:
            return
        # isVisible alone includes children entirely outside a scroll viewport.
        if widget.visibleRegion().isEmpty():
            return
        point = window.mapFromGlobal(widget.mapToGlobal(QPoint()))
        font = widget.font()
        info = QFontInfo(font)
        margins = widget.contentsMargins()
        palette = widget.palette()
        row = {'id': path, 'class': widget.metaObject().className(), 'name': widget.objectName(),
               'aliases': sorted(aliases.get(id(widget), [])),
               'rect': [point.x(), point.y(), widget.width(), widget.height()],
               'text': text_of(widget), 'tooltip': widget.toolTip(),
               'font': {'family': info.family(), 'point_size': info.pointSizeF(), 'pixel_size': info.pixelSize(),
                        'weight': int(font.weight()), 'italic': font.italic()},
               'colors': {},
               'margins': [margins.left(), margins.top(), margins.right(), margins.bottom()],
               'enabled': widget.isEnabled()}
        row['colors'] = {name: palette.color(getattr(QPalette.ColorRole, name)).name(QColor.NameFormat.HexArgb)
                         for name in ('Window', 'WindowText', 'Base', 'AlternateBase', 'Text', 'Button',
                                      'ButtonText', 'Highlight', 'HighlightedText', 'ToolTipBase', 'ToolTipText')}
        layout = widget.layout()
        if layout is not None:
            lm = layout.contentsMargins()
            row['layout_margins'] = [lm.left(), lm.top(), lm.right(), lm.bottom()]
            row['spacing'] = layout.spacing()
        if isinstance(widget, QComboBox):
            row['choices'] = [widget.itemText(i) for i in range(widget.count())]
        if isinstance(widget, QMenu):
            row['actions'] = [{'text': a.text(), 'enabled': a.isEnabled(), 'checked': a.isChecked(),
                               'rect': list_rect(widget.actionGeometry(a)),
                               'shortcuts': [s.toString() for s in a.shortcuts()]} for a in widget.actions()
                              if a.isVisible()]
        if isinstance(widget, QAbstractItemView) and widget.model() is not None:
            cells = []
            model = widget.model()

            def cells_in(parent):
                for r in range(model.rowCount(parent)):
                    first = model.index(r, 0, parent)
                    columns = 1 if isinstance(widget, QListView) else model.columnCount(parent)
                    for c in range(columns):
                        index = model.index(r, c, parent)
                        rect = widget.visualRect(index)
                        if not rect.isEmpty() and widget.viewport().rect().intersects(rect):
                            cells.append({'row': r, 'column': c, 'text': str(index.data(Qt.ItemDataRole.DisplayRole) or ''),
                                          'rect': list_rect(rect)})
                    if hasattr(widget, 'isExpanded') and widget.isExpanded(first):
                        cells_in(first)

            cells_in(widget.rootIndex())
            row['cells'] = cells
        rows.append(row)
        counts = {}
        for child in widget.children():
            if not isinstance(child, QWidget) or child.isWindow():
                continue
            label = child.objectName() or child.metaObject().className()
            ordinal = counts.get(label, 0)
            counts[label] = ordinal + 1
            walk(child, f'{path}/{label}[{ordinal}]')

    walk(window, 'window')
    for i, popup in enumerate(popups):
        walk(popup, f'popup[{i}]')
    return {'schema': 1, 'meta': dict(meta or {}), 'widgets': rows}


def list_rect(rect):
    return [rect.x(), rect.y(), rect.width(), rect.height()]


def wait_for(app, predicate, *, seconds=30, description='condition'):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(.01)
    raise TimeoutError(f'Timed out waiting for {description}')


def settle(app, window):
    """Allow actual entrance animations and lazy chart paints to finish."""
    from PySide6.QtTest import QTest
    QTest.qWait(350)
    previous, same = None, 0
    deadline = time.monotonic() + 10
    while same < 4 and time.monotonic() < deadline:
        app.processEvents()
        value = [(w.objectName(), w.x(), w.y(), w.width(), w.height())
                 for w in window.findChildren(type(window.centralWidget())) if w.isVisible()]
        same = same + 1 if value == previous else 0
        previous = value
        QTest.qWait(30)
    if same < 4:
        raise TimeoutError('Widget geometry did not settle')


def recorded_weather(project, cache):
    """Both recorded PVGIS 5.3 products at Rho, no network or invented weather."""
    from meridiana.quick.sample import recorded_weather as tmy
    from meridiana.energy import meteo
    if not tmy(project, cache):
        raise ValueError('The recorded weather is only valid at Rho')
    raw = json.loads((ROOT / 'tests/calcoli/riferimenti/pvgis53-printhorizon-rho.json').read_text(encoding='utf-8'))
    rows = raw['outputs']['horizon_profile']
    horizon = {'fetched': '2026-10-21', 'azimuth': [float(r['A']) + 180 for r in rows],
               'elevation': [float(r['H_hor']) for r in rows]}
    path = meteo._cache_file(cache, 'horizon', project.site.lat, project.site.lon)
    path.write_text(json.dumps(horizon), encoding='utf-8')


def present(win, state):
    """Navigate existing Widgets pages, without replacing any rendering code."""
    from PySide6.QtCore import QPoint
    popups = []
    if win.file_page.isVisible():
        win.file_page.close_page()
    win.assistant.close_panel()
    if state.startswith('phase-'):
        win.show_phase(state[6:])
    elif state == 'model-building':
        win.show_phase('model')
        if win.project.buildings:
            win._select('building', win.project.buildings[0].id)
    elif state.startswith('plant-'):
        win.show_phase('plant')
        section = {'subfield': 'panels', 'inverters': 'inverter', 'strings': 'inverter', 'storage': 'storage'}[state[6:]]
        if state == 'plant-subfield' and win.project.subfields:
            win._select('subfield', win.project.subfields[0].id)
        win.plant_side.open(section, ms=0)
        win.plant_inspector.set_view('diagram' if state == 'plant-strings' else 'cards')
        if state == 'plant-strings':
            # Seven inverter cards put the string diagram below the viewport.
            # This state is about the diagram itself, not merely its selected mode.
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            win.plant_inspector.ensureWidgetVisible(win.plant_inspector.list)
    elif state.startswith('file-'):
        win.open_file_page(state[5:])
    elif state.startswith('settings-'):
        win.open_file_page('preferences:' + state[9:])
    elif state.startswith('menu-'):
        win.show_phase('model')
        index = MENUS.index(state[5:])
        menu = win.menuBar().actions()[index].menu()
        menu.popup(win.mapToGlobal(QPoint(20, 45)))
        popups.append(menu)
    elif state == 'meridio':
        win.show_phase('model')
        win.assistant.open_panel()
    else:
        raise ValueError(state)
    return popups


def worker(args):
    """One real application process per matrix entry, as in normal use."""
    for folder in ('tests', 'src'):
        sys.path.insert(0, str(ROOT / folder))
    case = f'{args.fixture}-{args.theme}-s{args.scale}-{args.size}'
    output = ROOT / 'build/riferimento' / args.run / case
    canon = ROOT / 'docs/quick/compat/riferimento' / args.run / case
    output.mkdir(parents=True, exist_ok=args.resume)
    suffix = '-' + str(time.time_ns()) if args.resume else ''
    trace = (output / f'trace{suffix}.log').open('x', encoding='utf-8')
    faulthandler.enable(file=trace)
    print(f'{case}: process {os.getpid()}, preparing real Widgets application', flush=True)
    isolated = output / ('isolated' + suffix)
    for variable, child in (('XDG_CONFIG_HOME', 'config'), ('XDG_STATE_HOME', 'state'),
                            ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'),
                            ('APPDATA', 'roaming'), ('LOCALAPPDATA', 'local')):
        os.environ[variable] = str(isolated / child)
    os.environ.update(QT_SCALE_FACTOR=str(args.scale), QSG_RHI_BACKEND='d3d11',
                      MERIDIANA_INSTANCE='off', PYTHON_KEYRING_BACKEND='keyring.backends.null.Keyring',
                      QML_DISABLE_DISK_CACHE='1', QT_DISABLE_SHADER_DISK_CACHE='1')
    if args.offscreen:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    else:
        os.environ.pop('QT_QPA_PLATFORM', None)
    from PySide6.QtCore import QLocale, QPoint
    from PySide6.QtGui import QPainter
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
    from PySide6.QtWidgets import QApplication
    if not args.offscreen:
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    from meridiana import config, i18n, model
    from meridiana.paths import Paths
    from meridiana.ui import qt_translations
    from meridiana.ui.window import MainWindow
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    i18n.setup('it')
    QLocale.setDefault(QLocale('it_IT'))
    qt_translations.install(app, 'it')
    paths = Paths.from_env()
    cfg = config.Config(theme=args.theme, font='plex', accent='indigo', backgrounds='grey',
                        language='it', background='none', network_tiles=False, network_pvgis=False,
                        network_geocoding=False, check_updates=False, assistant_animated=False,
                        assistant_voice=False, tour_status='done')
    if args.fixture == 'rho':
        project, notice = model.Project.load(args.rho)
        if notice:
            raise ValueError(notice)
        source = {'kind': 'rho', 'sha256': hashlib.sha256(args.rho.read_bytes()).hexdigest()}
        recorded_weather(project, paths.cache)
        if args.populated:
            # A separately named fixture state for full consumption/economics
            # charts. The byte-identical frozen Rho source remains untouched.
            project.consumption = {'annual_kwh': 400000.}
            project.economics = {'capex_total': 450000., 'battery': {
                'manufacturer': 'Fixture', 'model': 'AC200', 'usable_energy_kwh': 200.,
                'max_charge_power_w': 100000., 'max_discharge_power_w': 100000.,
                'round_trip_efficiency_pct': 90.}}
            source['fixture_edits'] = {'consumption': project.consumption, 'economics': project.economics}
    else:
        project = model.Project(name='Progetto vuoto')
        source = {'kind': 'empty'}
    input_file = isolated / 'fixture.mer'
    input_file.parent.mkdir(parents=True, exist_ok=True)
    project.save(input_file)
    win = MainWindow(paths, cfg)
    print(f'{case}: window constructed, opening fixture', flush=True)
    # A native desktop can be smaller than the requested logical size at 200%.
    # A fixed minimum prevents Windows from clamping that test window to its
    # work area; QWidget.grab and the D3D render target still cover the full size.
    win.setFixedSize(*map(int, args.size.split('x')))
    win.show()
    if win.open_path(input_file) is False:
        raise RuntimeError('Widgets refused its fixture')
    print(f'{case}: fixture opened, waiting for layouts', flush=True)
    wait_for(app, lambda: all(sf.id in win.results for sf in win.project.subfields if sf.filled),
             description='the real layout job')
    if args.fixture == 'rho':
        print(f'{case}: computing recorded year', flush=True)
        win._compute_energy(fetch=False)
        progress = [-1]

        def say_progress(_generation, done, total, what):
            percent = int(100 * done / total)
            if percent >= progress[0] + 5:
                progress[0] = percent
                print(f'{case}: year {percent}% {what}', flush=True)

        win.energy_job.signals.step.connect(say_progress)

        def year_ready():
            if win.energy.get('error_sim'):
                raise RuntimeError('Widgets energy calculation: ' + win.energy['error_sim'])
            return win.energy.get('sim') is not None

        wait_for(app, year_ready, seconds=1200,
                 description='the real energy year from recorded PVGIS weather')
        print(f'{case}: year ready, {win.energy["sim"].energy_kwh:.6f} kWh', flush=True)
    settle(app, win)
    api = win.view3d.quickWindow().rendererInterface().graphicsApi().name
    if not args.offscreen and (app.platformName() != 'windows' or api != 'Direct3D11' or not win.view3d.drawn()):
        raise RuntimeError(f'Not a real Windows D3D11 reference: {app.platformName()}, {api}')
    if (win.width(), win.height()) != tuple(map(int, args.size.split('x'))):
        raise RuntimeError(f'The window refused {args.size}: {win.width()}x{win.height()}')
    cases = list(itertools.product(('light', 'dark'), SIZES)) if args.batch else [
        (args.theme, tuple(map(int, args.size.split('x'))))]
    states = args.states.split(',') if args.states else state_names()
    for theme, size in cases:
        case = f'{args.fixture}-{theme}-s{args.scale}-{size[0]}x{size[1]}'
        if args.resume and capture_complete(args.run, case, states):
            print(f'Skipping verified complete case {case}', flush=True)
            continue
        output = ROOT / 'build/riferimento' / args.run / case
        canon = ROOT / 'docs/quick/compat/riferimento' / args.run / case
        output.mkdir(parents=True, exist_ok=True)
        if list(output.glob('*.png')) or canon.exists():
            raise FileExistsError(f'Capture already exists: {case}')
        win.cfg.theme = theme
        win.theme.applied = None
        win.theme.apply()
        win.setFixedSize(*size)
        win.file_page.close_page()
        win.show_phase('model')
        settle(app, win)
        if (win.width(), win.height()) != size:
            raise RuntimeError(f'The window refused {size}: {win.width()}x{win.height()}')
        commands = {key: {'text': a.text(), 'shortcuts': [s.toString() for s in a.shortcuts()]}
                    for key, a in sorted(win.commands.items())}
        states = args.states.split(',') if args.states else state_names()
        manifest = {'case': case, 'captures': [], 'commands': commands, 'source': source,
                    'platform': app.platformName(), 'graphics_api': api, 'offscreen': args.offscreen}
        for state in states:
            print(f'{case}/{state}: opening', flush=True)
            popups = present(win, state)
            print(f'{case}/{state}: settling', flush=True)
            settle(app, win)
            meta = {**manifest, 'captures': [], 'state': state, 'theme': theme, 'scale': args.scale,
                    'size': [win.width(), win.height()], 'device_pixel_ratio': win.devicePixelRatioF(),
                    'language': i18n.language(), 'font': win.cfg.font, 'accent': win.cfg.accent, 'backgrounds': win.cfg.backgrounds,
                    'fixture': args.fixture, 'year_computed': win.energy.get('sim') is not None,
                    'inverters': sum(x.get('count', 1) for x in win.project.energy.get('inverters', [])),
                    'strings': len(win.project.energy.get('strings', {}).get('runs', [])),
                    'module_count': sum(len(r.table) for r in win.results.values() if not isinstance(r, Exception))}
            snap = widget_snapshot(win, meta=meta, popups=popups)
            snap['scenario'] = f'{case}/{state}'
            picture = win.grab()
            if popups:
                painter = QPainter(picture)
                for popup in popups:
                    painter.drawPixmap(win.mapFromGlobal(popup.mapToGlobal(QPoint())), popup.grab())
                painter.end()
            photo = output / f'{state}.png'
            if not picture.save(str(photo)):
                raise OSError(f'Could not save {photo}')
            snap['meta']['png_sha256'] = hashlib.sha256(photo.read_bytes()).hexdigest()
            # The capture directory is an implementation detail, never a volatile golden value.
            raw = json.dumps(snap, ensure_ascii=False).replace(str(isolated).replace('\\', '\\\\'), '<isolated>')
            write_canonical(canon / f'{state}.json.gz', json.loads(raw))
            manifest['captures'].append({'state': state, 'widgets': len(snap['widgets']),
                                         'png': photo.relative_to(ROOT).as_posix(),
                                         'json': (canon / f'{state}.json.gz').relative_to(ROOT).as_posix()})
            for popup in popups:
                popup.close()
            print(f'{case}/{state}: {len(snap["widgets"])} visible widgets', flush=True)
        write_canonical(canon / 'manifest.json.gz', manifest)
    win.session.mark_saved()
    win.close()
    win.pool.waitForDone(30000)
    trace.close()
    # As tools/run_tests.py: Qt wrappers can hang during unordered interpreter
    # teardown after every capture has succeeded. Close the window and drain its
    # jobs first, then leave the dedicated worker without destroying wrappers.
    sys.stdout.flush()
    sys.stderr.flush()
    if sys.platform == 'win32':
        # The Windows CRT's _exit still unloads Qt DLLs. Their VSync static
        # teardown can fail after the closed window and completed captures.
        # Terminate only this dedicated, fully drained worker, bypassing DLL
        # detach. No pending write or calculation is discarded on this path.
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        kernel.TerminateProcess.argtypes = (ctypes.c_void_p, ctypes.c_uint)
        if not kernel.TerminateProcess(kernel.GetCurrentProcess(), 0):
            raise ctypes.WinError(ctypes.get_last_error())
    os._exit(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix', action='store_true')
    parser.add_argument('--resume', action='store_true', help='Skip complete validated batches; never overwrite partial captures')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--batch', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--fixture', choices=('empty', 'rho'), default='rho')
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--scale', type=int, choices=(1, 2), default=1)
    parser.add_argument('--size', choices=tuple(f'{w}x{h}' for w, h in SIZES), default='1600x960')
    parser.add_argument('--run', default='baseline-v1')
    parser.add_argument('--rho', type=Path, default=RHO)
    parser.add_argument('--populated', action='store_true', help='Supplementary Rho fixture with consumption, investment and storage')
    parser.add_argument('--states', help='Comma-separated subset for a diagnostic capture')
    parser.add_argument('--offscreen', action='store_true')
    args = parser.parse_args()
    if Path(args.run).name != args.run or args.run in ('.', '..'):
        parser.error('--run must be a directory name')
    if args.populated and (args.fixture != 'rho' or args.matrix):
        parser.error('--populated requires --fixture rho; use --batch for both themes and all sizes')
    if args.list:
        print(json.dumps({'matrix': capture_matrix(), 'states': state_names()}, indent=2))
        return 0
    if args.worker:
        return worker(args)
    cases = [dict(fixture=f, theme='light', scale=s, size=list(SIZES[0]))
             for f, s in itertools.product(('empty', 'rho'), (1, 2))] if args.matrix else [dict(fixture=args.fixture, theme=args.theme, scale=args.scale,
                                                      size=[int(s) for s in args.size.split('x')])]
    for case in cases:
        if args.resume:
            batch = list(itertools.product(('light', 'dark'), SIZES)) if args.matrix or args.batch else [
                (case['theme'], case['size'])]
            expected = args.states.split(',') if args.states else state_names()
            complete = all(capture_complete(args.run,
                           f'{case["fixture"]}-{theme}-s{case["scale"]}-{size[0]}x{size[1]}', expected)
                           for theme, size in batch)
            if complete:
                print(f'Skipping verified complete batch {case["fixture"]}, scale {case["scale"]}', flush=True)
                continue
        command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--fixture', case['fixture'],
                   '--theme', case['theme'], '--scale', str(case['scale']), '--size', 'x'.join(map(str, case['size'])),
                   '--run', args.run, '--rho', str(args.rho)]
        if args.matrix or args.batch:
            command += ['--batch']
        if args.resume:
            command += ['--resume']
        if args.populated:
            command += ['--populated']
        if args.states:
            command += ['--states', args.states]
        if args.offscreen:
            command += ['--offscreen']
        result = subprocess.run(command, cwd=ROOT, check=False, timeout=1800)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
