"""fasi_probe.py (20/11/2026, study 56): what the window does when a phase is entered again, offscreen, on a synthetic
project in a temporary profile (never the user's folders): every phase entered `--visits` times in `--order`, the
longest gap of the window's thread and the time until it is quiet again; with --profile PHASE the window's thread is
profiled (cProfile) on the second entry into PHASE and the heaviest functions are printed.

    python tools/fasi_probe.py <project.meridiana> --out <file.json> [--visits 3] [--order plant,production]
                               [--sample] [--count] [--profile plant|sun] [--sun 24] [--replant 2] [--rebuild 2]
                               [--no-settle] [--disk-cache <folder>] [--hide <objectName,...>]

Before the visits the layout is laid and told (--no-settle: visited while it is on its way). --count: the emissions of
the result editors' and the plant's signals, every editor's refresh (whether its form changed, the items made), each
plant signal of _flush with the items made, the longest calls of the jobs' center, the items alive, and once what a
reading of the plant's lists costs. --replant N: the plant's dataChanged again on Impianto at rest, then its lists
emptied and given back (the delegates made again from compiled components), with the items by named part.
--rebuild N: the production form made again whole. --disk-cache: Qt's compiled QML kept in that folder, as the
program's start. --hide: those items made invisible (what a part costs is what its absence saves).

--sample: a thread that, while the window's beat is more than 200 ms late, notes the window thread's Python stack
every 50 ms (where the time goes; a frame that stays on an emit or on the event loop is C++ work: QML, layout,
drawing). --sun N steps the 3D's hour N times (as the slider) and the day N/4 times, plan and 3D both shown. Each row
says the production inspector's sections and fields (its form is made again when their shape changes)."""
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
STALL, QUIET_S = 30, .3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--visits', type=int, default=3)
    ap.add_argument('--order', default=','.join(PHASES))
    ap.add_argument('--profile', default='')
    ap.add_argument('--sun', type=int, default=0)
    ap.add_argument('--sample', action='store_true')
    ap.add_argument('--count', action='store_true')
    ap.add_argument('--hide', default='')
    ap.add_argument('--rebuild', type=int, default=0)
    ap.add_argument('--replant', type=int, default=0)
    ap.add_argument('--no-settle', action='store_true', help='visit while the layout is still on its way')
    ap.add_argument('--disk-cache', type=Path, help='a profile folder for the disk caches of Qt (cold, then warm)')
    args = ap.parse_args()
    args.out = args.out.resolve()
    work = Path(tempfile.mkdtemp(prefix='meridiana-fasi-'))
    for name in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'APPDATA', 'LOCALAPPDATA'):
        os.environ[name] = str(work / 'env' / name.lower())
        Path(os.environ[name]).mkdir(parents=True, exist_ok=True)
    (work / 'offscreen.json').write_text(json.dumps({'screens': [{
        'name': 'Offscreen', 'x': 0, 'y': 0, 'width': 1920, 'height': 1080, 'logicalDpi': 96, 'logicalBaseDpi': 96,
        'dpr': 1}]}))
    os.chdir(work)
    os.environ['QT_QPA_PLATFORM'] = 'offscreen:configfile=offscreen.json'
    os.environ['QSG_RENDER_LOOP'] = 'basic'
    os.environ['MERIDIANA_PRELOAD'] = '0'
    sys.path.insert(0, str(ROOT / 'src'))
    os.environ['PYTHONPATH'] = str(ROOT / 'src')
    from PySide6.QtCore import Q_ARG, QEventLoop, QMetaObject, QTimer
    from meridiana.core.compute import procmem
    from meridiana.core.model.model import Project
    from meridiana.gui import application
    app = application.create_app()
    if args.disk_cache:                 # as the program's start: Qt's compiled QML kept in the profile (study 56)
        from PySide6 import __version__ as qt_version
        from meridiana import __version__
        from meridiana.app.platform import qt_cache
        qt_cache.prepare(args.disk_cache, qt_cache.key_of(__version__, qt_version))

    def pump(ms=16):
        loop = QEventLoop()
        QTimer.singleShot(int(ms), loop.quit)
        loop.exec()

    project_file = work / args.project.name
    shutil.copy2(args.project, project_file)
    beat, blocks = [time.perf_counter()], []

    def tick():
        now = time.perf_counter()
        if (now - beat[0]) * 1000 > STALL:
            blocks.append(round((now - beat[0]) * 1000, 1))
        beat[0] = now
    heart = QTimer()
    heart.setInterval(2)
    heart.timeout.connect(tick)
    heart.start()
    rows = []
    samples = {}                    # the window's thread's Python stack while its beat is late, by place

    def sampler():
        import threading as th
        import traceback
        main = th.main_thread().ident
        while True:
            time.sleep(0.05)
            if time.perf_counter() - beat[0] > 0.2:
                frame = sys._current_frames().get(main)
                if frame is None:
                    continue
                stack = [f'{Path(f.filename).name}:{f.lineno} {f.name}' for f in traceback.extract_stack(frame)]
                key = ' < '.join(reversed(stack[-6:]))
                samples[key] = samples.get(key, 0) + 1
    if args.sample:
        import threading
        threading.Thread(target=sampler, daemon=True).start()

    def note(step, ms, **extra):
        rows.append({'step': step, 'ms': round(ms, 1), 'worst': max(blocks, default=0),
                     'rss_mib': round((procmem.rss() or 0) / (1 << 20)), **extra})
        print(rows[-1], flush=True)
        blocks.clear()

    def quiet(began):
        last = time.perf_counter()
        while time.perf_counter() - began < 120:
            n = len(blocks)
            pump(10)
            if len(blocks) != n:
                last = time.perf_counter()
            elif time.perf_counter() - last >= QUIET_S:
                break
        return (time.perf_counter() - began - QUIET_S) * 1000
    project, _notice = Project.load(project_file)
    host = application.QuickWindow(project, work / 'cache', real_views=True, path=project_file)
    win = host.window
    win.resize(1600, 960)
    win.show()
    pump(6000)
    # the layout of the project laid and told before the visits (as tools/plan_zoom_probe.py): a visit then measures
    # the phase, not a layout of 2000 modules arriving meanwhile
    host.bridge._ask_layout()
    end = time.perf_counter() + (0 if args.no_settle else 180)
    session = host.bridge.session
    while time.perf_counter() < end and not (host.bridge._layout is None and not session.telling()
                                             and session.layout_keys == session.expected_layout_keys()):
        pump(50)
    if not args.no_settle:
        quiet(time.perf_counter())
    blocks.clear()
    note('rest', 0, laid=session.layout_keys == session.expected_layout_keys())
    counts, refreshes, flushes = {}, [], []
    if args.count:
        # every emission of the editors' and the plant's signals, by name; every refresh of an editor timed, with the
        # time of its sectionsChanged (the form made again); the window's items alive, made and gone at each step
        from meridiana.gui.backend import charts_editor
        context = host.engine.rootContext()
        for name in ('productionEditor', 'consumptionEditor', 'economicsEditor'):
            editor = context.contextProperty(name)
            for signal in ('sectionsChanged', 'changed'):
                getattr(editor, signal).connect(lambda *_a, k=f'{name}.{signal}': counts.__setitem__(k, counts.get(k, 0) + 1))
        plant = context.contextProperty('plantBackend')
        for signal in (*plant._FAMILIES, 'changed', 'wiringChanged', 'selectionChanged', 'messageChanged'):
            getattr(plant, signal).connect(lambda *_a, k=f'plant.{signal}': counts.__setitem__(k, counts.get(k, 0) + 1))
        real_refresh = charts_editor.ResultEditor.refresh

        def timed_refresh(editor):
            shape = editor._shape
            items = alive() if editor.phase == 'production' else 0
            began = time.perf_counter()
            real_refresh(editor)
            took = round((time.perf_counter() - began) * 1000, 1)
            made = alive() - items if editor.phase == 'production' else 0
            refreshes.append((editor.phase, took, 'shape changed' if editor._shape != shape else 'same shape',
                              f'{made:+} items'))
        charts_editor.ResultEditor.refresh = timed_refresh
        # each of the plant's signals emitted by _flush timed, with the items made and gone meanwhile
        flushes.extend([])
        plant_type = type(plant)

        def timed_flush(backend):
            pending, backend._pending = backend._pending, set()
            if backend._closed or not pending:
                return
            for name in (*(n for n in backend._FAMILIES if n in pending), 'changed'):
                items = alive()
                began = time.perf_counter()
                getattr(backend, name).emit()
                flushes.append((name, round((time.perf_counter() - began) * 1000), f'{alive() - items:+} items'))
        plant_type._flush = timed_flush
        plant._notifier.timeout.disconnect()
        plant._notifier.timeout.connect(lambda: timed_flush(plant))

    def tally():
        """Items by the nearest ancestor that is a component of the program (its QML type: PlantInputCards...), the
        Delegates of a view counted with it."""
        out, todo = {}, [(win.contentItem(), 'root')]
        while todo:
            item, owner = todo.pop()
            kind = item.metaObject().className().split('_QML')[0]
            if kind.startswith(('Plant', 'Result', 'Chart', 'Production', 'Properties')):
                owner = kind
            out[owner] = out.get(owner, 0) + 1
            todo.extend((child, owner) for child in item.childItems())
        return out

    def alive():
        todo, n = [win.contentItem()], 0
        while todo:
            item = todo.pop()
            todo.extend(item.childItems())
            n += 1
        return n
    for name in [n for n in args.hide.split(',') if n]:
        from PySide6.QtCore import QObject as _Q
        item = win.findChild(_Q, name)
        if item is None:
            raise ValueError('no item named ' + name)
        item.setProperty('visible', False)     # what a part costs is what its absence saves
    center = host.work.center if getattr(host, 'work', None) is not None else None
    seen = {}
    for _visit in range(args.visits):
        for pid in args.order.split(','):
            seen[pid] = seen.get(pid, 0) + 1
            profiling = args.profile == pid and seen[pid] == 2
            if profiling:
                import cProfile
                prof = cProfile.Profile()
                prof.enable()
            before = alive() if args.count else 0
            counts.clear()
            refreshes.clear()
            flushes.clear()
            if center is not None:
                center.reset_stats()
            beat[0] = time.perf_counter()
            blocks.clear()
            t = time.perf_counter()
            QMetaObject.invokeMethod(win, 'showPhase', Q_ARG('QVariant', pid))
            ms = quiet(t)
            if profiling:
                prof.disable()
                import pstats
                print(f'--- profile of {pid}, visit 2', flush=True)
                pstats.Stats(prof).sort_stats('cumulative').print_stats(40)
            editor = host.engine.rootContext().contextProperty('productionEditor')
            shape = getattr(editor, '_shape', ()) if editor is not None else ()
            note(f'{pid} {seen[pid]}', ms, sections=len(shape), fields=sum(len(f) for _k, f in shape))
            if args.count:
                stats = center.stats() if center is not None else {'by_name': {}}
                heavy = sorted(stats['by_name'].items(), key=lambda kv: -kv[1])[:5]
                print('   signals', dict(sorted(counts.items())), flush=True)
                print('   refreshes', refreshes, flush=True)
                print('   plant flushes', [f for f in flushes if f[1] > 20 or f[2] != '+0 items'], flush=True)
                print('   longest calls', [(k, round(v * 1000)) for k, v in heavy], flush=True)
                print('   items', before, '->', alive(), flush=True)
            if args.sample and samples:
                for key, count in sorted(samples.items(), key=lambda kv: -kv[1])[:6]:
                    print(f'   {count * 50} ms  {key}', flush=True)
                samples.clear()
    if args.count:
        # what one reading of the plant's lists costs the QML: their size and their conversion to JavaScript
        plant = host.engine.rootContext().contextProperty('plantBackend')
        for key in ('strings', 'inputs', 'units'):
            value = plant._data.get(key) or []
            t = time.perf_counter()
            for _ in range(5):
                host.engine.toScriptValue(value)
            print(f'   plant.{key}: {len(value)} rows, {len(json.dumps(value, default=str)) // 1024} KB of JSON, '
                  f'{(time.perf_counter() - t) * 200:.1f} ms a conversion', flush=True)
    if args.replant:
        # the plant's dataChanged emitted again with the same data, on the page shown and at rest: what its QML costs
        QMetaObject.invokeMethod(win, 'showPhase', Q_ARG('QVariant', 'plant'))
        quiet(time.perf_counter())
        plant = host.engine.rootContext().contextProperty('plantBackend')
        for n in range(args.replant):
            before = alive()
            beat[0] = time.perf_counter()
            blocks.clear()
            t = time.perf_counter()
            plant.dataChanged.emit()
            took = (time.perf_counter() - t) * 1000
            settled = quiet(t)
            note(f'plant dataChanged {n + 1}', took, settled_ms=round(settled), items=f'{before} -> {alive()}')
        # the lists emptied, then given back: the delegates made again from components already compiled (the first
        # population of the page, without Qt's compiling)
        kept = {key: plant._data[key] for key in ('strings', 'inputs')}
        for label, data in (('emptied', {key: [] for key in kept}), ('given back', kept)):
            plant._data.update(data)
            before = alive()
            counted = tally()
            beat[0] = time.perf_counter()
            blocks.clear()
            t = time.perf_counter()
            plant.dataChanged.emit()
            took = (time.perf_counter() - t) * 1000
            settled = quiet(t)
            note(f'plant lists {label}', took, settled_ms=round(settled), items=f'{before} -> {alive()}')
            now = tally()
            grown = sorted(((k, now.get(k, 0) - counted.get(k, 0)) for k in set(now) | set(counted)),
                           key=lambda kv: -abs(kv[1]))
            print('   by part', [g for g in grown if g[1]][:10], flush=True)
    if args.rebuild:
        # the production inspector's form made again whole, as when its shape changes (the strings' fields arriving),
        # on the page shown: its time, the window's longest gap and the items made and gone
        QMetaObject.invokeMethod(win, 'showPhase', Q_ARG('QVariant', 'production'))
        quiet(time.perf_counter())
        editor = host.engine.rootContext().contextProperty('productionEditor')
        for n in range(args.rebuild):
            before = alive()
            editor._shape = ()
            beat[0] = time.perf_counter()
            blocks.clear()
            t = time.perf_counter()
            editor.refresh()
            took = (time.perf_counter() - t) * 1000
            settled = quiet(t)
            note(f'form made again {n + 1}', took, settled_ms=round(settled), items=f'{before} -> {alive()}')
    if args.sun:
        QMetaObject.invokeMethod(win, 'showPhase', Q_ARG('QVariant', 'model'))
        win.setProperty('viewMode', 'both')
        quiet(time.perf_counter())
        blocks.clear()
        scene = host.scene
        t = time.perf_counter()
        if args.profile == 'sun':
            import cProfile
            prof = cProfile.Profile()
            prof.enable()
        for _ in range(args.sun):
            scene.stepSun()
            pump(40)
        if args.profile == 'sun':
            prof.disable()
            import pstats
            print('--- profile of the sun steps', flush=True)
            pstats.Stats(prof).sort_stats('cumulative').print_stats(40)
        note(f'sun: {args.sun} steps of ten minutes', (time.perf_counter() - t) * 1000)
        t = time.perf_counter()
        for _ in range(max(1, args.sun // 4)):
            scene.shiftSunDay(1)
            pump(40)
        note(f'sun: {max(1, args.sun // 4)} days', (time.perf_counter() - t) * 1000)
    out = {'project': args.project.name, 'rows': rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding='utf-8')
    app.processEvents()
    os._exit(0)


if __name__ == '__main__':
    main()
