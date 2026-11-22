"""Offscreen resize evidence on the complete application, using synthetic Qt input."""
import argparse
import json
import tempfile
from pathlib import Path

import _setup  # noqa: F401
from PySide6.QtCore import QEvent, QPointF, Qt
from meridiana.core.model.model import Project
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import drag, item, mouse, point, pump

PHASES = ('model', 'plant', 'production', 'consumption', 'economics', 'report')
PANELS = {'left': 'leftPanel', 'right': 'rightPanel', 'bottom': 'checksPanel'}


def card_name(phase, side):
    """The card on that side in the phase: in Report the left one is the report's contents (r39)."""
    return 'contentsPanel' if side == 'left' and phase == 'report' else PANELS[side]


def hover(app, win, pos):
    mouse(app, win, QEvent.Type.MouseMove, pos, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
    pump(30)
    return win.cursor().shape().name


def window(folder, proof=True):
    app = create_app()
    source = Path(__file__).resolve().parents[1] / 'docs/quick/compat/fixtures/rho.meridiana'
    project = Project.load(source)[0] if proof else connected_fixture()
    host = QuickWindow(project, folder, real_views=True, theme={'theme': 'light', 'reducedMotion': True})
    host.bridge.configure_background(enabled=False)
    host.window.show()
    host.window.resize(1800, 1000)
    pump(1500)
    host.shell.trigger('default_layout')
    pump(300)
    print("WINDOW", host.window.width(), host.window.height(), flush=True)
    return app, host


def prepare(host, phase):
    host.shell.trigger('phase_' + phase)
    root = host.window
    ws = item(root, 'workspace')
    ws.setProperty('leftExtent', 300)
    ws.setProperty('rightExtent', 340)
    ws.setProperty('bottomExtent', 220)
    pump(900)
    return ws


def borders(app, host):
    win = host.window
    out = []
    for phase in PHASES:
        prepare(host, phase)
        for side in PANELS:
            card = item(win, card_name(phase, side))
            if not card.isVisible():
                out.append(dict(phase=phase, side=side, visible=False))
                continue
            before = card.height() if side == 'bottom' else card.width()
            pos = point(card, -4 if side == 'right' else card.width()+4 if side == 'left' else card.width()/2,
                        -4 if side == 'bottom' else card.height()/2)
            cursor = hover(app, win, pos)
            delta = QPointF(0, -60) if side == 'bottom' else QPointF(-60 if side == 'right' else 60, 0)
            drag(app, win, pos, pos+delta, steps=12, pause=8)
            pump(150)
            after = card.height() if side == 'bottom' else card.width()
            out.append(dict(phase=phase, side=side, visible=True, cursor=cursor,
                            before=before, after=after, delta=round(after-before, 2)))
    return out



def foreign_panels(app, host):
    """Try every handle's projected line inside every other visible card."""
    win = host.window
    out = []
    for phase in PHASES:
        ws = prepare(host, phase)
        for side in PANELS:
            handle = item(win, side + 'ResizeHandle')
            if not handle.isVisible():
                continue
            hpos = point(handle)
            for other in PANELS:
                if other == side:
                    continue
                card = item(win, card_name(phase, other))
                if not card.isVisible():
                    continue
                origin = point(card, 0, 0)
                # Clamp the projection into the card: also exercise the closest point when disjoint.
                for label, along in (('head', 20), ('body', card.height()/2)):
                    if side == 'bottom':
                        y = origin.y()+20 if label == 'head' else max(
                            origin.y()+4, min(hpos.y(), origin.y()+card.height()-4))
                        pos = QPointF(origin.x()+card.width()/2, y)
                    else:
                        pos = QPointF(max(origin.x()+4, min(hpos.x(), origin.x()+card.width()-4)),
                                      origin.y()+along)
                    before = [ws.property(k) for k in ('leftExtent', 'rightExtent', 'bottomExtent')]
                    cursor = hover(app, win, pos)
                    over = bool(handle.property('containsMouse'))
                    delta = QPointF(0, -60) if side == 'bottom' else QPointF(60, 0)
                    # A title may move its own card, but must never resize another panel.
                    mouse(app, win, QEvent.Type.MouseButtonPress, pos,
                          Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
                    grabbed = bool(handle.property('pressed'))
                    mouse(app, win, QEvent.Type.MouseMove, pos+delta,
                          Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
                    mouse(app, win, QEvent.Type.MouseButtonRelease, pos+delta,
                          Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
                    after = [ws.property(k) for k in ('leftExtent', 'rightExtent', 'bottomExtent')]
                    out.append(dict(phase=phase, handle=side, panel=other, location=label,
                                    cursor=cursor, contains=over, grabbed=grabbed,
                                    changed=before != after))
                    # Restore any title drag and every extent for the next independent observation.
                    # The restore command can undo itself for 15 s: make each sample a fresh reset.
                    ws.setProperty('previousLayout', None)
                    host.shell.trigger('default_layout')
                    pump(100)
                    prepare(host, phase)
    return out

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--foreign', action='store_true')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as temporary:
        app, host = window(Path(temporary))
        try:
            result = foreign_panels(app, host) if args.foreign else borders(app, host)
            Path(args.out).write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result))
        finally:
            host.close()
            pump(100)
