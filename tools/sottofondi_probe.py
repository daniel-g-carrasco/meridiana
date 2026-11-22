"""sottofondi_probe.py (20/11/2026, study 56 point 4): the Qt Quick window offscreen with large underlays, and how
long the window's thread is held while they arrive, while their transparency changes, while the project is opened
again and while the plan zooms in and out.

    python tools/sottofondi_probe.py capannone|<project.meridiana> --out <file.json> [--side 4096] [--count 0]
                                     [--notches 12] [--rounds 2]

`capannone` is the tests' small project (what the underlays cost, not 2000 modules drawn in software); a file is
copied into a temporary profile (never the user's folders). `--count` underlays of `--side` px (a noisy JPEG, as an
orthophoto) are in the project from the start; then four arrive in the open window (64 px, `--side`, 64, `--side`:
the small ones are the control), their transparency changes twice, the project is opened again twice and the plan
zooms. A timer every 2 ms on the window's thread notes every gap above STALL ms. Offscreen the software renderer
draws on the window's thread (basic loop): a gap is decoding, Python or drawing. PROBE_PROFILE=1 prints the profile of
a large arrival and of a change of transparency (the window's thread)."""
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
STALL = 30


def picture(path: Path, side: int, seed: int) -> None:
    import numpy as np
    from PySide6.QtGui import QImage
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:side, 0:side]
    base = ((x * 255 // side)[..., None] * np.array([1, 0, 0]) + (y * 255 // side)[..., None] * np.array([0, 1, 0])
            + 60)
    noise = rng.integers(0, 90, (side, side, 3))
    rgb = np.clip(base + noise, 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb[..., 2], rgb[..., 1], rgb[..., 0], np.full((side, side), 255, np.uint8)]).copy()
    image = QImage(rgba.data, side, side, side * 4, QImage.Format.Format_ARGB32)
    image.copy().save(str(path), 'JPG', 90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--side', type=int, default=4096)
    ap.add_argument('--count', type=int, default=1)
    ap.add_argument('--notches', type=int, default=12)
    ap.add_argument('--rounds', type=int, default=2)
    args = ap.parse_args()
    args.out = args.out.resolve()
    work = Path(tempfile.mkdtemp(prefix='meridiana-sottofondi-'))
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
    sys.path.insert(0, str(ROOT / 'tests'))
    os.environ['PYTHONPATH'] = str(ROOT / 'src')
    from PySide6.QtCore import QEventLoop, QObject, QPointF, QTimer
    from meridiana.core.model import underlay
    from meridiana.core.model.model import Project
    from meridiana.gui import application

    app = application.create_app()

    def pump(ms=16):
        loop = QEventLoop()
        QTimer.singleShot(int(ms), loop.quit)
        loop.exec()

    from meridiana.gui.backend import underlays
    if str(args.project) == 'capannone':      # the tests' small project: what the underlays cost, not the modules
        from _fixtures import capannone
        project_file = work / 'capannone.meridiana'
        project = capannone('Capannone')
    else:
        project_file = work / args.project.name
        shutil.copy2(args.project, project_file)
        project, _notice = Project.load(project_file)
    for n in range(args.count):
        jpeg = work / f'orto-{n}.jpg'
        picture(jpeg, args.side, n)
        data, w, h = underlays.read_image(jpeg)
        project.underlays.append(underlay.placed(project.new_id('u'), jpeg.name, data, w, h, (40.0 * n, 0.0), 300))
    project.save(project_file)
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

    def note(step, ms, **extra):
        rows.append({'step': step, 'ms': round(ms, 1), 'worst': max(blocks, default=0),
                     'over_33': sum(1 for b in blocks if b > 33.4), 'blocks': sorted(blocks, reverse=True)[:6], **extra})
        print(rows[-1], flush=True)
        blocks.clear()
    cache = work / 'cache'
    cache.mkdir()
    t = time.perf_counter()
    project, _notice = Project.load(project_file)
    host = application.QuickWindow(project, cache, real_views=True, path=project_file)
    win = host.window
    beat[0] = time.perf_counter()
    blocks.clear()
    note('window built', (time.perf_counter() - t) * 1000)
    frames = []
    win.frameSwapped.connect(lambda: frames.append(time.perf_counter()))
    win.resize(1600, 960)
    t = time.perf_counter()
    win.show()
    while not frames and time.perf_counter() - t < 60:
        pump(10)
    note('first frame', ((frames[0] if frames else time.perf_counter()) - t) * 1000)
    pump(3000)
    note('rest 3 s', 3000)
    host.plan.configureMaps({'offline': True})
    t = time.perf_counter()
    win.showPhase('model')
    win.setProperty('viewMode', 'plan')
    plan = None
    while plan is None and time.perf_counter() - t < 60:
        pump(10)
        plan = win.findChild(QObject, 'plan')
    pump(3000)
    note('plan shown', (time.perf_counter() - t) * 1000, ready=underlays_ready(win))
    end = time.perf_counter() + 120
    while time.perf_counter() < end and (host.bridge._layout is not None or host.bridge.session.telling()):
        pump(50)
    pump(3000)
    note('plan settled', 0, ready=underlays_ready(win))
    for n, side in enumerate((64, args.side, 64, args.side)):
        jpeg = work / f'arrivo-{n}.jpg'
        picture(jpeg, side, 100 + n)
        data, w, h = underlays.read_image(jpeg)
        new = underlay.placed(host.bridge.session.project.new_id('u'), jpeg.name, data, w, h, (0.0, 20.0 * n), 200)
        beat[0] = time.perf_counter()
        blocks.clear()
        t = time.perf_counter()
        if os.environ.get('PROBE_PROFILE'):
            import cProfile
            import pstats
            prof = cProfile.Profile()
            prof.enable()
        host.bridge.session.edit('probe', lambda p, new=new: p.underlays.append(new))
        edit_ms = (time.perf_counter() - t) * 1000
        if os.environ.get('PROBE_PROFILE'):
            prof.disable()
            if side == args.side:
                pstats.Stats(prof).sort_stats('cumulative').print_stats(18)
        pump(2500)
        note(f'arrives {side} px ({n + 1})', (time.perf_counter() - t) * 1000, edit_ms=round(edit_ms, 1),
             ready=underlays_ready(win))
    print('decoded', [(k[:12], side, main) for k, side, main in getattr(underlays, 'decoded', [])], flush=True)
    uids = [u.id for u in host.bridge.session.project.underlays]
    for n, value in enumerate((0.5, 0.7)):
        t = time.perf_counter()
        if os.environ.get('PROBE_PROFILE') and n == 0:
            import cProfile
            import pstats
            prof = cProfile.Profile()
            prof.enable()
            host.plan.underlays.action(uids[-1], 'opacity', value)
            prof.disable()
            pstats.Stats(prof).sort_stats('tottime').print_stats(14)
        for uid in uids:
            host.plan.underlays.action(uid, 'opacity', value)
        pump(1500)
        note(f'transparency {n + 1}', (time.perf_counter() - t) * 1000, ready=underlays_ready(win))
    files = host.engine.rootContext().contextProperty('filesBackend')
    for n in range(2):
        t = time.perf_counter()
        files.openPath(str(project_file)) if files is not None else host.bridge.session.open(project_file)
        pump(4000)
        note(f'reopen {n + 1}', (time.perf_counter() - t) * 1000, ready=underlays_ready(win))
    from quick.gestures import wheel
    centre = QPointF(win.width() * 0.5, win.height() * 0.5)
    for r in range(args.rounds):
        for direction, dy in (('in', 120), ('out', -120)):
            t = time.perf_counter()
            wheel(app, win, centre, notches=args.notches, dy=dy)
            pump(600)
            note(f'zoom {direction} {r + 1}', (time.perf_counter() - t) * 1000, ready=underlays_ready(win))
    out = {'project': str(args.project), 'side': args.side, 'count': args.count, 'rows': rows,
           'worst_zoom': max((row['worst'] for row in rows if row['step'].startswith('zoom')), default=0),
           'worst_open': max((row['worst'] for row in rows if not row['step'].startswith('zoom')), default=0)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding='utf-8')
    print('worst open', out['worst_open'], 'worst zoom', out['worst_zoom'], flush=True)
    app.processEvents()
    os._exit(0)


def underlays_ready(win):
    """The underlay images in the window: (scheme of their source, width of the image loaded, visible), the
    `data:` URLs before point 4 and `image://underlay` after; found through the items (a Repeater's delegates are
    not the window's QObject children)."""
    found, todo = [], [win.contentItem()]
    while todo:
        item = todo.pop()
        todo.extend(item.childItems())
        if not item.metaObject().className().startswith('QQuickImage'):
            continue
        source = item.property('source').toString()
        if (source.startswith('data:') and not source.startswith('data:image/png;base64,iVBOR'))                 or source.startswith('image://underlay'):
            size = item.property('sourceSize')
            found.append((source[:28], size.width() if size else 0, item.isVisible()))
    return found

if __name__ == '__main__':
    main()
