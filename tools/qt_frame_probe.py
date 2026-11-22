"""Isolate Qt frames and QML creation, without project backends or workers.

Native-only reference, not a substitute for the real phase benchmark.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import statistics
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--backend', choices=('rhi', 'software'), default='rhi')
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Output exists: choose a new revision')
    os.environ.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND=args.backend,
                      QSG_RHI_BACKEND='d3d11', QSG_RENDER_LOOP='threaded' if args.backend == 'rhi' else 'basic',
                      QT_SCALE_FACTOR='1')
    profile = str(args.out.resolve().parent / (args.out.stem + '-profile'))
    for key in ('APPDATA', 'LOCALAPPDATA', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
        os.environ[key] = profile
    from PySide6.QtCore import QObject, Qt, qVersion
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    app = QGuiApplication([])
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda rows: warnings.extend(row.toString() for row in rows))
    engine.loadData(b'''import QtQuick
import QtQuick.Controls
Window {
    width: 1400; height: 900; x: -20000; y: -20000
    property int tick: 0
    color: tick % 2 ? "#fefefe" : "#ffffff"
    Loader {
        objectName: "probeLoader"
        active: false
        sourceComponent: Column {
            Repeater { model: 300; delegate: Label { text: "A native QML control"; width: 300; height: 24 } }
        }
    }
}''')
    if not engine.rootObjects():
        raise RuntimeError(warnings)
    win = engine.rootObjects()[0]
    assert isinstance(win, QQuickWindow)
    loader = win.findChild(QObject, 'probeLoader')
    frames, rendering, synchronizing = [], [], []
    starts = {}
    def stamp(name):
        starts[name] = time.perf_counter()
    def finish(name, rows):
        if name in starts:
            rows.append((time.perf_counter()-starts[name])*1000)
    win.beforeSynchronizing.connect(lambda: stamp('sync'), Qt.ConnectionType.DirectConnection)
    win.afterSynchronizing.connect(lambda: finish('sync', synchronizing), Qt.ConnectionType.DirectConnection)
    win.beforeRendering.connect(lambda: stamp('render'), Qt.ConnectionType.DirectConnection)
    win.afterRendering.connect(lambda: finish('render', rendering), Qt.ConnectionType.DirectConnection)
    win.frameSwapped.connect(lambda: frames.append(time.perf_counter()), Qt.ConnectionType.DirectConnection)
    win.show()
    def pump(ms):
        turns = []
        end = time.perf_counter()+ms/1000
        while time.perf_counter() < end:
            win.setProperty('tick', win.property('tick') + 1)
            win.requestUpdate()
            start = time.perf_counter()
            app.processEvents()
            turns.append((time.perf_counter()-start)*1000)
            time.sleep(.001)
        return turns
    pump(1000)
    frames.clear(); rendering.clear(); synchronizing.clear()
    turns = pump(2000)
    intervals = [(b-a)*1000 for a,b in zip(frames, frames[1:], strict=False)]
    idle = dict(frames=len(frames), median_frame_ms=statistics.median(intervals),
                max_frame_ms=max(intervals), max_event_ms=max(turns),
                max_sync_ms=max(synchronizing), max_render_ms=max(rendering))
    creation = []
    for asynchronous in (False, True):
        loader.setProperty('active', False)
        pump(200)
        loader.setProperty('asynchronous', asynchronous)
        start = time.perf_counter()
        loader.setProperty('active', True)
        activation = (time.perf_counter()-start)*1000
        turns = []
        end = start+2
        while loader.property('item') is None and time.perf_counter() < end:
            turns.extend(pump(5))
        creation.append(dict(asynchronous=asynchronous, finished=loader.property('item') is not None, activation_ms=activation,
                             ready_ms=(time.perf_counter()-start)*1000,
                             max_event_ms=max(turns, default=0)))
    result = dict(backend=args.backend, qt_version=qVersion(), graphics=str(win.rendererInterface().graphicsApi()),
                  date=time.strftime('%Y-%m-%dT%H:%M:%S'), idle=idle, creation=creation, warnings=warnings)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    win.close()
    app.processEvents()
    print(json.dumps(result))


if __name__ == '__main__':
    main()
