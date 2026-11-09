"""Pan and zoom the Quick's plan over the orthophoto with the real cursor, and write down what the tiles do (R539-R541).

    python tools/quick_map_tour.py <out dir> [--tiles <a tiles folder to copy>] [--phases model,plant]
                                   [--rounds N] [--until HH:MM] [--profile-zoom]

What it writes in <out dir>:
- tiles.jsonl, one line per event of the tile loader, with the time from the start: asked (from disk or queued),
  sent (attempt), answered (ok or error, milliseconds, the server's words), retried, failed, read again by Qt
  after the memory let it go (reread), let go by the memory (evicted), the plan moved to another source (failover);
- samples.jsonl, every 250 ms: source on show, tiles wanted, loaded, missing, in flight, queued, in memory;
- gestures.jsonl, one line per gesture: frames (count, worst interval, intervals over 50 ms), blocks of the window's
  thread over 30 ms (count, worst, total), the share of the plan that is a hole (the bare background colour);
- PNG captures of the screen at chosen moments.

Safety as in tools/quick_real_cursor.py (RealHand): it stops if the cursor moves without it, clicks and turns the
wheel only over its own window, presses keys only when its window is in front, no input after --until.
Its profile is a temporary folder (cache, preferences, state): nothing is written in %APPDATA% or %LOCALAPPDATA%
of Meridiana; a tiles folder given with --tiles is copied, never written."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / 'tests'), os.environ.get('TOUR_SRC', str(ROOT / 'src')), str(ROOT / 'tools')]   # TOUR_SRC: another branch's src, for a before
RHO = Path.home() / 'dev/meridiana-prove/Prova capannone Rho.meridiana'
T0 = time.perf_counter()


def now():
    return round((time.perf_counter() - T0) * 1000, 1)


class Journal:
    def __init__(self, folder: Path):
        self.files = {name: (folder / f'{name}.jsonl').open('w', encoding='utf8')
                      for name in ('tiles', 'samples', 'gestures')}
        self.counts = {}

    def write(self, name, **row):
        row = {'t': now(), **row}
        self.files[name].write(json.dumps(row, default=str) + '\n')
        if name == 'tiles':
            self.counts[row['event']] = self.counts.get(row['event'], 0) + 1

    def close(self):
        for f in self.files.values():
            f.close()


def instrument(journal: Journal):
    """The loader's, the memory's and the plan's moments, written as they happen (no behaviour changed)."""
    from meridiana import resources
    from meridiana.quick.backend import plan_maps, plan_tiles
    L = plan_tiles.TileLoader
    sent_at = {}

    original_request = L.request

    def request(self, key, z, x, y, ahead=False):
        tile = (key, z, x, y)
        busy = tile in self.retrying or tile in self.in_flight.values() or tile in self.decoding or tile in self.queued
        path = self._path(*tile)
        on_disk = path.exists()
        original_request(self, key, z, x, y, ahead)
        if not busy:
            journal.write('tiles', event='asked', tile=tile, ahead=ahead, disk=on_disk,
                          renew=tile in self.renewing)
    L.request = request

    original_pump = L._pump

    def pump(self):
        before = set(self.in_flight)
        original_pump(self)
        for reply, tile in self.in_flight.items():
            if reply not in before:
                sent_at[tile] = time.perf_counter()
                journal.write('tiles', event='sent', tile=tile, attempt=self.attempts.get(tile, 0),
                              in_flight=len(self.in_flight))
    L._pump = pump

    original_done = L._done

    def done(self, reply):
        tile = self.in_flight.get(reply)
        if tile is not None:
            from PySide6.QtNetwork import QNetworkReply, QNetworkRequest
            error = reply.error()
            mime = str(reply.header(QNetworkRequest.KnownHeaders.ContentTypeHeader) or '')
            ms = round((time.perf_counter() - sent_at.pop(tile, time.perf_counter())) * 1000)
            ok = error == QNetworkReply.NetworkError.NoError and mime.startswith('image/')
            words = '' if ok else (reply.errorString() if error != QNetworkReply.NetworkError.NoError else
                                   bytes(reply.peek(300)).decode('utf8', 'replace'))
            sent_at_done.add(tile)
            journal.write('tiles', event='answered', tile=tile, ok=ok, ms=ms, mime=mime,
                          attempt=self.attempts.get(tile, 0), words=words[:200],
                          wanted=self.wanted is None or tile in self.wanted)
        original_done(self, reply)
    L._done = done

    def decode_run(self):
        """The decoder's steps written one by one: which one stays (R539)."""
        import threading
        from PySide6.QtGui import QImage
        journal.write('tiles', event='decode-begin', tile=self.tile, thread=threading.get_ident())
        image = QImage(str(self.path))
        journal.write('tiles', event='decode-image', tile=self.tile, null=image.isNull())
        self.signals.done.emit(self.tile, image)
        journal.write('tiles', event='decode-emitted', tile=self.tile)
    if os.environ.get('TOUR_DECODE_STEPS'):
        plan_tiles._Decode.run = decode_run

    original_retry = L._retry

    def retry(self, tile):
        journal.write('tiles', event='retried', tile=tile, attempt=self.attempts.get(tile, 0))
        original_retry(self, tile)
    L._retry = retry

    # No method of the loader that a worker's signal reaches is replaced: a replaced _decoded stopped the decoders
    # (07/11/2026, the first tours: the queued call never came and the next emit stayed). The loader's own signals
    # are heard instead.
    original_init = L.__init__

    def init(self, *a, **k):
        original_init(self, *a, **k)
        self.tileReady.connect(lambda key, z, x, y, image: journal.write(
            'tiles', event='ready', tile=(key, z, x, y), disk=(key, z, x, y) not in sent_at_done))
        self.tileFailed.connect(lambda key, z, x, y, why: journal.write(
            'tiles', event='gave-up', tile=(key, z, x, y), why=why[:200]))
    L.__init__ = init
    sent_at_done = set()

    original_failed = plan_maps.PlanMaps.failed

    def failed(self, tile, now=None):
        before = self.source
        moved = original_failed(self, tile, now)
        journal.write('tiles', event='failed', tile=tile, failures=len(self.failures))
        if moved:
            journal.write('tiles', event='failover', source_from=before, source_to=self.source)
        return moved
    plan_maps.PlanMaps.failed = failed

    original_reread = plan_tiles.MapImages.requestImage

    def request_image(self, identifier, size, requested_size):
        with self.lock:
            tile = self.by_id.get(identifier)
            in_memory = tile is not None and tile in self.cache._entries
        image = original_reread(self, identifier, size, requested_size)
        if not in_memory:
            journal.write('tiles', event='reread', tile=tile, null=image.isNull())
        return image
    plan_tiles.MapImages.requestImage = request_image

    original_trim = resources.Cache._trim

    def trim(self, limit):
        before = set(self._entries)
        original_trim(self, limit)
        gone = before - set(self._entries)
        for key in gone:
            if isinstance(key, tuple) and len(key) == 4:
                journal.write('tiles', event='evicted', tile=key, pinned=key in self.pinned, left=len(self._entries))
    resources.Cache._trim = trim


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    parser.add_argument('--tiles', type=Path, help='A tiles folder copied into the temporary profile (a warm cache)')
    parser.add_argument('--phases', default='model,plant')
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--until', default='23:59')
    parser.add_argument('--profile-zoom', action='store_true', help='cProfile over the zoom bursts')
    parser.add_argument('--only-zoom', action='store_true', help='Only the wheel bursts (fluidity), no pan tour')
    parser.add_argument('--hide', default='', help='objectNames hidden after each phase opens (what costs: ablation)')
    parser.add_argument('--no-frames', action='store_true', help='No hook on frameSwapped (it runs on the render thread)')
    parser.add_argument('--stacks-at', type=float, default=0, help='Seconds: the stacks of every thread written then')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='meridiana-mappa-'))
    profile = work / 'profile'
    for variable, child in (('XDG_CONFIG_HOME', 'config'), ('XDG_STATE_HOME', 'state'), ('XDG_DATA_HOME', 'data'),
                            ('XDG_CACHE_HOME', 'cache'), ('APPDATA', 'roaming'), ('LOCALAPPDATA', 'local')):
        os.environ[variable] = str(work / child)
    os.environ.update(MERIDIANA_INSTANCE='off', PYTHON_KEYRING_BACKEND='keyring.backends.null.Keyring',
                      PYTHONUTF8='1')
    profile.mkdir(parents=True)
    if args.tiles:
        shutil.copytree(args.tiles, profile / 'tiles')
    project_file = work / RHO.name
    shutil.copy2(RHO, project_file)
    journal = Journal(args.out)
    instrument(journal)

    from PySide6.QtCore import QObject, Qt, QTimer
    from meridiana import model
    from meridiana.quick.app import QuickWindow, create_app
    from meridiana.quick.sample import recorded_weather
    from quick_real_cursor import RealHand, Stop
    from quick.percorsi import modellazione
    app = create_app()
    project, notice = model.Project.load(project_file)
    recorded_weather(project, profile)
    host = QuickWindow(project, profile, real_views=True, path=project_file)
    window = host.window
    window.setFlags(window.flags() | Qt.WindowType.WindowStaysOnTopHint)
    window.resize(1600, 960)
    window.setPosition(60, 40)
    window.show()
    QTimer.singleShot(0, host.bridge.recompute)
    hand = RealHand(app, window, int(window.winId()), args.until)
    log = (args.out / 'tour.log').open('w', encoding='utf8')
    pilot = modellazione.Pilot('quick', app, host, window, hand, args.out, 'mappa', log)

    # the window's thread: a beat every 5 ms, a gap over 30 ms is a block; the frames: frameSwapped
    beat = [time.perf_counter()]
    blocks, frames = [], []

    def tick():
        t = time.perf_counter()
        gap = (t - beat[0]) * 1000
        if gap > 30:
            blocks.append((t, gap))
        beat[0] = t
    heart = QTimer()
    heart.setTimerType(Qt.TimerType.PreciseTimer)
    heart.timeout.connect(tick)
    heart.start(5)
    if not args.no_frames:
        window.frameSwapped.connect(lambda: frames.append(time.perf_counter()), Qt.ConnectionType.DirectConnection)
    if args.stacks_at:
        import faulthandler
        stacks = (args.out / 'stacks.txt').open('w')
        faulthandler.dump_traceback_later(args.stacks_at, repeat=False, file=stacks)
    import faulthandler
    faulthandler.enable(file=(args.out / 'crash.txt').open('w'), all_threads=True)

    def maps():
        return host.plan._maps if host.plan else None

    def sample():
        m = maps()
        if m is None:
            return
        s, ld = m.state, m.loader
        journal.write('samples', source=s.source, fallback_from=s.fallback_from, mpp=round(s.mpp, 4),
                      wanted=len(s.wanted), loaded=len(s.loaded), shown=sum(1 for t in s.loaded if t in s.wanted),
                      missing=len(s.wanted - s.loaded.keys()), old=sum(1 for t in s.loaded if t not in s.wanted),
                      in_flight=len(ld.in_flight), queued=len(ld.queue), retrying=len(ld.retrying),
                      memory=len(m.provider.cache), records=len(m._tiles))
    sampler = QTimer()
    sampler.timeout.connect(sample)
    sampler.start(250)

    plan_item = None

    def hole_share(image, veil):
        """The share of the plan's pixels in the bare background under the veil (R540's bands), with NumPy."""
        import numpy
        from PySide6.QtGui import QImage
        colour = numpy.array([round(c * (1 - veil)) for c in (0x33, 0x2f, 0x2b)])     # B, G, R in memory
        img = image.toImage().convertToFormat(QImage.Format.Format_RGB32)
        a = numpy.frombuffer(img.constBits(), numpy.uint8).reshape(img.height(), img.bytesPerLine())
        a = a[:, :img.width() * 4].reshape(img.height(), img.width(), 4)[::3, ::3, :3].astype(int)
        return round(float((numpy.abs(a - colour) <= 3).all(axis=2).mean()), 4)

    shots = [0]
    grabbing = []                       # (start, end) of every grab: not a block of the program

    def grab():
        """The screen under the plan, as the designer sees it (the grab only; measured apart)."""
        start = time.perf_counter()
        p = plan_item.mapToGlobal(0, 0)
        pixmap = window.screen().grabWindow(0, int(p.x()), int(p.y()), int(plan_item.width()),
                                            int(plan_item.height()))
        grabbing.append((start, time.perf_counter()))
        return pixmap

    def gesture(name, action, settle_ms=1500, shots_at=(150, 600, 1500)):
        frames.clear()
        blocks.clear()
        grabbing.clear()
        begin = time.perf_counter()
        action()
        acted = time.perf_counter()
        pixmaps = []
        waited = 0
        for at in shots_at:
            hand.spin(max(0, at - waited))
            waited = at
            pixmaps.append((at, grab()))
        hand.spin(max(0, settle_ms - waited))
        end = time.perf_counter()
        veil = maps().veil if maps() else 0

        def outside(a, b):
            return all(b <= g0 or a >= g1 for g0, g1 in grabbing)
        own = [(t, g) for t, g in blocks if outside(t - g / 1000, t)]
        span = [f for f in frames if f >= begin]
        pairs = [(a, b) for a, b in zip(span, span[1:]) if outside(a, b)]
        gaps = [(b - a) * 1000 for a, b in pairs]
        during = [(b - a) * 1000 for a, b in pairs if a <= acted]
        holes = []
        for at, pixmap in pixmaps:
            shots[0] += 1
            share = hole_share(pixmap, veil)
            holes.append(share)
            file = args.out / f'{shots[0]:03d}-{name}-{at}ms.png'
            if share > 0.002 or shots[0] % 4 == 1:
                pixmap.save(str(file))
            journal.write('gestures', capture=file.name, hole=share)
        row = dict(gesture=name, action_ms=round((acted - begin) * 1000), frames=len(span),
                   fps=round(len(span) / max(1e-3, end - begin - sum(g1 - g0 for g0, g1 in grabbing)), 1),
                   worst_frame_ms=round(max(gaps, default=0), 1), frames_over_50=sum(g > 50 for g in gaps),
                   frames_during=len(during), worst_during_ms=round(max(during, default=0), 1),
                   mean_during_ms=round(sum(during) / len(during), 1) if during else None,
                   blocks=len(own), worst_block_ms=round(max((g for _t, g in own), default=0), 1),
                   blocked_ms=round(sum(g for _t, g in own), 1),
                   blocks_during=sum(1 for t, _g in own if t <= acted + .05),
                   blocked_during_ms=round(sum(g for t, g in own if t <= acted + .05), 1), holes=holes,
                   source=maps().state.source if maps() else None)
        journal.write('gestures', **row)
        print(json.dumps(row), file=log, flush=True)
        return row

    code = 0
    profiler = None
    try:
        print(f'inizio {time.strftime("%H:%M:%S")} lavoro {work} cursore {hand.start} scala {window.devicePixelRatio()}'
              f' avviso {notice!r}', file=log, flush=True)
        hand.spin(2500)
        plan_item = window.findChild(QObject, 'plan')
        hand.click(*pilot.centre(plan_item))
        hand.spin(300)

        def wheel_burst(notches, gap_ms=70):
            cx, cy = pilot.centre(plan_item)
            sign = 1 if notches > 0 else -1
            hand.move(cx + 40, cy + 20)
            for _n in range(abs(notches)):
                from quick_real_cursor import INPUT, MOUSEINPUT, WHEEL
                import ctypes
                px, py = hand.position()
                if not hand.own(px, py):
                    raise Stop('rotella fuori dalla finestra di prova')
                i = INPUT(type=0)
                i.u.mi = MOUSEINPUT(0, 0, ctypes.c_ulong(120 * sign & 0xFFFFFFFF).value, WHEEL, 0, 0)
                hand._send(i)
                hand.spin(gap_ms)

        def pan(dx, dy):
            cx, cy = pilot.centre(plan_item)
            hand.drag(cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2, button='middle', steps=30)

        for phase in [p for p in args.phases.split(',') if p]:
            pilot.phase(phase)
            hand.spin(1500)
            hand.click(*pilot.centre(plan_item))
            hand.key('f')
            hand.spin(4000 if phase == 'model' else 2500)
            for name in [n for n in args.hide.split(',') if n]:
                for found in window.findChildren(QObject, name):
                    found.setProperty('visible', False)
                print(f'nascosto {name}: {len(window.findChildren(QObject, name))}', file=log, flush=True)
            gesture(f'{phase}-apertura', lambda: None, 500, (100,))
            if args.profile_zoom:
                import cProfile
                profiler = cProfile.Profile()
            for r in range(args.rounds):
                # a quick turn of the wheel (70 ms a notch) and a slow one (220 ms, each notch settles on its own)
                for notches, gap in ((5, 70), (-5, 70), (4, 220), (-4, 220)):
                    if profiler:
                        profiler.enable()
                    gesture(f'{phase}-r{r}-rotella{notches:+d}x{gap}', lambda n=notches, g=gap: wheel_burst(n, g),
                            1200, (100, 400, 1200))
                    if profiler:
                        profiler.disable()
                if args.only_zoom:
                    continue
                for dx, dy in ((600, 0), (0, 400), (-900, 0), (0, -500)):
                    gesture(f'{phase}-r{r}-pan{dx:+d},{dy:+d}', lambda a=dx, b=dy: pan(a, b))
                gesture(f'{phase}-r{r}-lontano', lambda: wheel_burst(-9, 90), 3000, (150, 800, 3000))
                for dx, dy in ((700, 300), (-700, -300)):
                    gesture(f'{phase}-r{r}-lontano-pan{dx:+d}', lambda a=dx, b=dy: pan(a, b), 2500, (150, 800, 2500))
                gesture(f'{phase}-r{r}-vicino', lambda: wheel_burst(9, 90), 3000, (150, 800, 3000))
                gesture(f'{phase}-r{r}-vicino-oltre', lambda: wheel_burst(4, 90), 2500, (150, 800, 2500))
                hand.key('f')
                hand.spin(1500)
            if profiler:
                profiler.dump_stats(str(args.out / f'zoom-{phase}.prof'))
                profiler = None
        hand.spin(3000)
    except Stop as stop:
        code = 3
        print(f'FERMATO: {stop}', file=log, flush=True)
    except Exception:
        code = 4
        print('ERRORE\n' + traceback.format_exc(), file=log, flush=True)
    finally:
        hand.restore()
        sample()
        print(f'fine {time.strftime("%H:%M:%S")} input {hand.inputs} eventi {journal.counts}', file=log, flush=True)
        print(f'fine codice {code} eventi {journal.counts} lavoro {work}', flush=True)
        journal.close()
        log.close()
        os._exit(code)


if __name__ == '__main__':
    main()
