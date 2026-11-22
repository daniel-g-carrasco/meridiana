"""memoria_finestra.py (20/11/2026, study 56): the Qt Quick window offscreen on a synthetic project, its time and the
process' memory (procmem) at each step: the window built, its first frame, every phase entered twice, then the same
project opened again --reopen times (what stays in memory after a reopening), and the views changed (plan alone,
3D alone, both). The year is not computed (no weather offline).

    python tools/memoria_finestra.py <project.meridiana> --out <file.json> [--disk-cache] [--reopen 3] [--screen]

--disk-cache keeps Qt's disk caches of the compiled QML and of the pipelines on, as the program's start does
(app/platform/qt_cache.py: in <profile>/quick-cache/qt-cache/<version>, never the user's folder; create_app turns them
off): run it twice on the same --profile to see the cache cold and warm. The profile is a temporary folder unless
--profile is given (never the user's). The project is copied there: the original is not opened."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASES = ['plant', 'production', 'consumption', 'economics', 'report', 'model']
STALL, QUIET_S = 30, .15
MIB = 1 << 20


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--profile', type=Path)
    ap.add_argument('--disk-cache', action='store_true')
    ap.add_argument('--reopen', type=int, default=3)
    ap.add_argument('--screen', action='store_true', help='a real screen and the graphics card (not offscreen)')
    args = ap.parse_args()
    args.out = args.out.resolve()
    work = args.profile or Path(tempfile.mkdtemp(prefix='meridiana-memoria-finestra-'))
    for name in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'APPDATA', 'LOCALAPPDATA'):
        os.environ[name] = str(work / 'env' / name.lower())
        Path(os.environ[name]).mkdir(parents=True, exist_ok=True)
    screens = work / 'offscreen.json'
    screens.write_text(json.dumps({'screens': [{'name': 'Offscreen', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080,
                                                'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': 1}]}))
    os.chdir(work)
    if not args.screen:
        os.environ['QT_QPA_PLATFORM'] = 'offscreen:configfile=offscreen.json'
        os.environ['QSG_RENDER_LOOP'] = 'basic'
    print('pid', os.getpid(), flush=True)      # for the GPU's counters (Get-Counter '\GPU Process Memory(pid_N*)\...')
    sys.path.insert(0, str(ROOT / 'src'))
    os.environ['PYTHONPATH'] = str(ROOT / 'src')     # the year's and the report's processes
    T0 = time.perf_counter()
    from meridiana.core.compute import procmem
    from meridiana.gui import application

    from PySide6.QtCore import QEventLoop, QMetaObject, QTimer, Q_ARG
    from meridiana.core.model.model import Project

    def pump(ms=16):
        loop = QEventLoop()
        QTimer.singleShot(int(ms), loop.quit)
        loop.exec()

    def wait_for(predicate, seconds):
        end = time.perf_counter() + seconds
        while not predicate():
            if time.perf_counter() > end:
                return False
            pump(10)
        return True

    rows = []

    def note(name, ms, **extra):
        rows.append({'step': name, 'ms': round(ms, 1), 'rss_mib': round((procmem.rss() or 0) / MIB, 1),
                     'tree_mib': round((procmem.rss(tree=True) or 0) / MIB, 1), **extra})
        print(rows[-1], flush=True)

    project_file = work / args.project.name
    shutil.copy2(args.project, project_file)
    cache = work / 'cache'
    cache.mkdir(exist_ok=True)
    beat, blocks = [time.perf_counter()], []

    def tick():
        now = time.perf_counter()
        if (now - beat[0]) * 1000 > STALL:
            blocks.append(round((now - beat[0]) * 1000, 1))
        beat[0] = now

    app = application.create_app()
    if args.disk_cache:                 # as the program's start (application.main): in the profile, never the user's
        from PySide6 import __version__ as qt_version
        from meridiana import __version__
        from meridiana.app.platform import qt_cache
        qt_cache.prepare(work / 'quick-cache', qt_cache.key_of(__version__, qt_version))
    note('app', (time.perf_counter() - T0) * 1000, qml_cache=os.environ.get('QML_DISK_CACHE_PATH', 'off'),
         shader_cache=os.environ.get('QT_DISABLE_SHADER_DISK_CACHE', ''))
    heart = QTimer()
    heart.setInterval(2)
    heart.timeout.connect(tick)
    heart.start()
    t = time.perf_counter()
    project, _notice = Project.load(project_file)
    host = application.QuickWindow(project, cache, real_views=True, path=project_file)
    win = host.window
    note('window built', (time.perf_counter() - t) * 1000)
    frames = []
    win.frameSwapped.connect(lambda: frames.append(time.perf_counter()))
    win.resize(1600, 960)
    t = time.perf_counter()
    win.show()
    wait_for(lambda: bool(frames), 60)
    note('first frame', ((frames[0] if frames else time.perf_counter()) - t) * 1000,
         api=str(win.rendererInterface().graphicsApi()))
    blocks.clear()
    pump(5000)
    note('rest 5 s', 5000, blocks=sorted(blocks, reverse=True)[:5])

    def enter(pid):
        begin = time.perf_counter()
        blocks.clear()
        QMetaObject.invokeMethod(win, 'showPhase', Q_ARG('QVariant', pid))
        last = time.perf_counter()
        while True:
            n = len(blocks)
            pump(10)
            if len(blocks) != n:
                last = time.perf_counter()
            elif time.perf_counter() - last >= QUIET_S:
                break
        return (time.perf_counter() - begin - QUIET_S) * 1000

    for visit in ('1a', '2a'):
        for pid in PHASES:
            ms = enter(pid)
            note(f'phase {pid} {visit}', ms, worst=max(blocks, default=0))
            pump(300)
    files = host.engine.rootContext().contextProperty('filesBackend')
    for i in range(args.reopen):
        blocks.clear()
        t = time.perf_counter()
        ok = files.openPath(str(project_file)) if files is not None else host.bridge.session.open(project_file)
        pump(10)
        wait_for(lambda t=t: not blocks or time.perf_counter() - t > 3, 10)
        pump(2000)
        note(f'reopen {i + 1}', (time.perf_counter() - t) * 1000, ok=bool(ok), worst=max(blocks, default=0))
    for mode in ('3d', 'plan', 'both', '3d', 'plan', 'both'):
        blocks.clear()
        t = time.perf_counter()
        win.setProperty('viewMode', mode) if win.property('viewMode') is not None else None
        pump(1500)
        note(f'view {mode}', (time.perf_counter() - t) * 1000, worst=max(blocks, default=0),
             set=win.property('viewMode'))
    out = {'project': args.project.name, 'disk_cache': args.disk_cache, 'rows': rows,
           'peak_mib': round((procmem.peak() or 0) / MIB, 1), 'warnings': host.warnings[:20],
           'total_s': round(time.perf_counter() - T0, 1)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('peak', out['peak_mib'], 'total', out['total_s'])
    app.processEvents()
    os._exit(0)


if __name__ == '__main__':
    main()
