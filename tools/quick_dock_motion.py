"""Frames and main-thread stalls while a card is carried over the workspace and docked (R504).

Synthetic Qt mouse events only: no system pointer moves. Offscreen by default (the numbers are then the main
thread's, not a monitor's); --on-screen on an idle machine that allows it gives real frame pacing.

    python tools/quick_dock_motion.py --out docs/studio/36-aggancio-schede/misure-prima.json [--on-screen]
"""
from __future__ import annotations
import argparse
import json
import os
import platform
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT/'tests'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--on-screen', action='store_true')
    parser.add_argument('--render-loop', choices=('threaded', 'basic'), default='threaded')
    parser.add_argument('--steps', type=int, default=60, help='pointer moves per gesture, one every 16 ms')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--real-views', action='store_true', help='the real plan and 3D view in the centre (R504: their size while a card is carried)')
    parser.add_argument('--wait-before', type=float, default=0, help='seconds of rest after the window is up (to maximise it on screen)')
    args = parser.parse_args()
    if not args.on_screen:
        os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ['QSG_RENDER_LOOP'] = args.render_loop
    from PySide6.QtCore import QEvent, QTimer, Qt
    from _fixtures import capannone
    from meridiana import jobs
    from meridiana.quick.app import QuickWindow, create_app
    from quick.gestures import item, mouse, point, pump, wait_for
    app = create_app()
    beat, gaps, frames = [time.perf_counter()], [], [0]

    def tick():
        now = time.perf_counter()
        gap = (now-beat[0])*1000
        if gap > 30:
            gaps.append(round(gap, 1))
        beat[0] = now

    heart = QTimer(); heart.setInterval(2); heart.timeout.connect(tick); heart.start()
    with tempfile.TemporaryDirectory(prefix='meridiana-dock-') as tmp:
        host = QuickWindow(capannone(), Path(tmp), real_views=args.real_views)
        win = host.window
        win.frameSwapped.connect(lambda: frames.__setitem__(0, frames[0]+1))
        if not args.on_screen:
            win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show(); win.resize(1600, 960)
        results, keys, _ = jobs.layout_of(host.bridge.session.project)
        host.bridge.accept_layout(0, results, keys)
        pump(300)
        if args.real_views:
            controller = host.engine.incubationController()
            wait_for(lambda: controller.incubatingObjectCount() == 0, seconds=10)
            pump(500)
        item(win, 'plan').fit()
        pump(300)
        if args.wait_before:
            pump(int(args.wait_before*1000))
        # Maximised on a screen of another size, the window may have been arranged (panels together, checks shut).
        win.runCommand('default_layout'); pump(600)
        workspace = item(win, 'workspace')
        print('window', win.width(), win.height(), 'workspace', workspace.width(), workspace.height(),
              {n: (item(win, n).property('zone'), item(win, n).isVisible()) for n in ('leftPanel', 'rightPanel', 'checksPanel')})
        w, h = workspace.width(), workspace.height()

        def carry(panel, x, y):
            start = point(item(win, panel+'TitleDrag'))
            end = point(workspace, x, y)
            mouse(app, win, QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
            for i in range(1, args.steps+1):
                mouse(app, win, QEvent.Type.MouseMove, start+(end-start)*(i/args.steps), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
                pump(16)
            try:
                wait_for(lambda: workspace.property('dragTarget') is not None, seconds=2)
            except AssertionError:
                title = item(win, panel+'TitleDrag')
                print('no drop zone answered:', panel, 'dragged', repr(workspace.property('draggedPanel')),
                      'candidate', repr(workspace.property('candidate')), 'title visible', title.isVisible(),
                      'start', start, 'end', end, 'lift', item(win, 'cardLift').x(), item(win, 'cardLift').y())
            pump(400)
            mouse(app, win, QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
            pump(450)

        def measure(label, action):
            gaps.clear(); frames[0] = 0
            started = time.perf_counter()
            action()
            elapsed = (time.perf_counter()-started)*1000
            return {'gesture': label, 'ms': round(elapsed, 1), 'frames': frames[0],
                    'fps': round(frames[0]/elapsed*1000, 1), 'stalls_over_30ms': len(gaps),
                    'worst_gap_ms': max(gaps) if gaps else 0}

        rows = []
        for _ in range(args.rounds):
            rows.append(measure('checks to the top of the left column', lambda: carry('checks', 100, 40)))
            rows.append(measure('project to the top of the right column', lambda: carry('project', w-100, 40)))
            rows.append(measure('checks to the bottom-left corner', lambda: carry('checks', 40, h-10)))
            rows.append(measure('properties across the centre, left as it floats', lambda: carry('properties', w/2, h/2)))
            win.runCommand('default_layout'); pump(500)
        summary = {}
        for row in rows:
            s = summary.setdefault(row['gesture'], {'fps': [], 'stalls': [], 'worst': []})
            s['fps'].append(row['fps']); s['stalls'].append(row['stalls_over_30ms']); s['worst'].append(row['worst_gap_ms'])
        out = {'platform': platform.platform(), 'qpa': app.platformName(), 'render_loop': args.render_loop,
               'on_screen': args.on_screen, 'real_views': args.real_views, 'steps': args.steps, 'rounds': args.rounds,
               'summary': {k: {'fps_median': sorted(v['fps'])[len(v['fps'])//2], 'stalls_total': sum(v['stalls']),
                               'worst_gap_ms': max(v['worst'])} for k, v in summary.items()},
               'rows': rows, 'warnings': host.warnings[:]}
        host.close(); app.processEvents()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in out['summary'].items():
        print(f"{k}: {v['fps_median']} fps, {v['stalls_total']} stalls >30 ms, worst {v['worst_gap_ms']} ms")


if __name__ == '__main__':
    main()
