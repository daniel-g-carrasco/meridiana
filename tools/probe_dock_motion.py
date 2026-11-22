"""Record docking geometry on every rendered offscreen frame, without project data."""
import argparse
import json
import tempfile
import time
from pathlib import Path

import _setup  # noqa: F401
from PySide6.QtCore import QEvent, QPointF, Qt

from meridiana.core.model.model import Project
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import item, mouse, point, pump, wait_for


def rect(obj):
    return [round(v, 3) for v in (obj.x(), obj.y(), obj.width(), obj.height())]


def record(output, source=None, captures=None):
    app = create_app()
    if app.platformName() != 'offscreen':
        raise RuntimeError('Set QT_QPA_PLATFORM=offscreen before recording docking geometry')
    project = Project.load(source)[0] if source else connected_fixture()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as folder:
        host = QuickWindow(project, Path(folder), real_views=True,
                           theme={'theme': 'light', 'reducedMotion': False})
        host.bridge.configure_background(enabled=False)
        win = host.window
        win.show()
        win.resize(1896, 1028)
        pump(1600)
        wait_for(lambda: host.engine.incubationController().incubatingObjectCount() == 0, seconds=30)
        ws = item(win, 'workspace')
        if captures:
            captures.mkdir(parents=True, exist_ok=True)
        rows = []
        stage = 'initial'
        started = time.perf_counter()
        names = ('checksPanel', 'leftPanel', 'rightPanel', 'centralPanel',
                 'view3dHost', 'viewport3d', 'plan', 'dropZone', 'dropOutline', 'cardLift')

        def frame():
            objects = {name: item(win, name) for name in names}
            painted = {}
            for name, obj in objects.items():
                a = obj.mapToScene(QPointF())
                b = obj.mapToScene(QPointF(obj.width(), obj.height()))
                painted[name] = [round(v, 3) for v in (a.x(), a.y(), b.x()-a.x(), b.y()-a.y())]
            content = {}
            for name in ('plan', 'viewport3d'):
                obj = objects[name]
                natural = [obj.width(), obj.height()]
                content[name] = dict(natural=natural, ratios=[
                    painted[name][2+i]/max(1, natural[i]) for i in (0, 1)])
            picture = next(o for o in objects['cardLift'].childItems()
                           if 'ShaderEffectSource' in o.metaObject().className())
            source_item = picture.property('sourceItem')
            if source_item and source_item.width() and source_item.height():
                a = picture.mapToScene(QPointF())
                b = picture.mapToScene(QPointF(picture.width(), picture.height()))
                content['picture'] = dict(natural=[source_item.width(), source_item.height()],
                                          ratios=[(b.x()-a.x())/source_item.width(),
                                                  (b.y()-a.y())/source_item.height()])
            rows.append(dict(content=content, ms=round(1000*(time.perf_counter()-started), 2), stage=stage,
                             dragged=ws.property('draggedPanel'), candidate=ws.property('candidate'),
                             geometry={name: rect(obj) for name, obj in objects.items()},
                             shown={name: obj.isVisible() and obj.opacity() > 0 for name, obj in objects.items()},
                             painted=painted))
            win.requestUpdate()

        win.frameSwapped.connect(frame)
        for zone, x, y in [('floating', ws.width()/2, ws.height()/2),
                           ('left', 10, ws.height()/2), ('right', ws.width()-10, ws.height()/2),
                           ('bottom', ws.width()/2, ws.height()-10)]:
            stage = zone + ':press'
            start = point(item(win, 'checksTitleDrag'))
            end = point(ws, x, y)
            mouse(app, win, QEvent.Type.MouseButtonPress, start, Qt.LeftButton, Qt.LeftButton)
            stage = zone + ':carry'
            for step in range(1, 21):
                mouse(app, win, QEvent.Type.MouseMove, start+(end-start)*step/20, Qt.NoButton, Qt.LeftButton)
                pump(16)
            pump(800)
            stage = zone + ':release'
            mouse(app, win, QEvent.Type.MouseButtonRelease, end, Qt.LeftButton, Qt.NoButton)
            if captures:
                pump(100)
                win.grabWindow().save(str(captures/(zone+'-moving.png')))
                pump(800)
                win.grabWindow().save(str(captures/(zone+'-arrived.png')))
            else:
                pump(900)
        win.frameSwapped.disconnect(frame)
        output.write_bytes((json.dumps(rows)+'\r\n').encode('utf-8'))
        print('frames', len(rows), 'warnings', host.warnings)
        for zone in ('floating', 'left', 'right', 'bottom'):
            run = [r for r in rows if r['stage'].startswith(zone)]
            print(zone, 'first', run[0]['geometry']['checksPanel'], 'last', run[-1]['geometry']['checksPanel'])
        host.close()
        pump(100)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--captures', type=Path, help='Synthetic captures only; keep outside the repository')
    args = parser.parse_args()
    record(args.output, args.project, args.captures)
