"""Native uploaded geometry versus FileInstancing and a cosmetic module-edge shader.

These are measured alternatives, not the application renderer. The same input
polygons feed both, and Python only uploads data before the first native frame.
"""
import argparse
import json
import math
import os
from pathlib import Path
import statistics
import time

os.environ['QSG_RENDER_LOOP'] = 'threaded'
os.environ['QSG_RHI_BACKEND'] = 'd3d11'
os.environ['QML_DISABLE_DISK_CACHE'] = '1'
os.environ['QT_DISABLE_SHADER_DISK_CACHE'] = '1'

import numpy as np  # noqa: E402
from PySide6.QtCore import QByteArray, QPointF, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication, QVector3D  # noqa: E402
from PySide6.QtQml import QQmlApplicationEngine  # noqa: E402
from PySide6.QtQuick3D import QQuick3DGeometry  # noqa: E402
from quick.gestures import pump, wait_for  # noqa: E402
from meridiana import jobs, model  # noqa: E402
from meridiana.quick.backend.scene_geometry import instance_file  # noqa: E402
from meridiana.quick.backend.plan_scene import scene_of  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--technique', choices=('uploaded', 'instances'), required=True)
    parser.add_argument('--rho', action='store_true')
    parser.add_argument('--shader', action='store_true')
    parser.add_argument('--count', type=int, default=20000)
    args = parser.parse_args()
    app = QGuiApplication([])
    out = ROOT/'build/quick-foto/pianta/renderers'
    out.mkdir(parents=True, exist_ok=True)
    if args.rho:
        p = model.Project.load(ROOT/'docs/quick/compat/fixtures/rho.meridiana')[0]
        results, _keys, _count = jobs.layout_of(p)
        quads = np.asarray([m['points'] for m in scene_of(p, results)['modules']])
    else:
        columns = math.ceil(math.sqrt(args.count*.6))
        quads = np.asarray([[(i%columns*1.3+x, i//columns*2.5+y)
                            for x, y in ((0, 0), (1.13, 0), (1.13, 2.27), (0, 2.27))] for i in range(args.count)])
    quads[:, :, 1] *= -1
    low, high = quads.min(axis=(0, 1)), quads.max(axis=(0, 1))
    centre = (low+high)/2
    zoom = min(1300/(high[0]-low[0]+10), 820/(high[1]-low[1]+10))
    geometry = QQuick3DGeometry()
    indices = [0, 1, 2, 0, 2, 3]
    xy = quads[:, indices].reshape(-1, 2)
    uv = np.tile(np.asarray([(0, 0), (1, 0), (1, 1), (0, 0), (1, 1), (0, 1)]), (len(quads), 1))
    vertices = np.column_stack((xy, np.zeros(len(xy)), uv)).astype('<f4')
    geometry.setVertexData(QByteArray(vertices.tobytes()))
    geometry.setStride(20)
    geometry.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles)
    geometry.addAttribute(QQuick3DGeometry.Attribute.PositionSemantic, 0, QQuick3DGeometry.Attribute.F32Type)
    geometry.addAttribute(QQuick3DGeometry.Attribute.TexCoord0Semantic, 12, QQuick3DGeometry.Attribute.F32Type)
    geometry.setBounds(QVector3D(*map(float, low), 0), QVector3D(*map(float, high), 0))
    table = np.zeros((len(quads), 20), dtype='<f4')
    a, b = (quads[:, 1]-quads[:, 0])/100, (quads[:, 0]-quads[:, 3])/100
    table[:, 0], table[:, 1] = a[:, 0], b[:, 0]
    table[:, 4], table[:, 5] = a[:, 1], b[:, 1]
    table[:, 3], table[:, 7] = quads.mean(axis=1).T
    table[:, 10] = 1
    table[:, 12:16] = 1
    source = instance_file(out/'instances', table)
    engine = QQmlApplicationEngine()
    errors = []
    engine.warnings.connect(lambda es: errors.extend(e.toString() for e in es))
    ctx = engine.rootContext()
    for key, value in dict(probeInstances=args.technique=='instances', probeGeometry=geometry, probeShader=args.shader,
                           probeFile=QUrl.fromLocalFile(str(source)), probeZoom=float(zoom),
                           probeCentre=QPointF(*map(float, centre))).items():
        ctx.setContextProperty(key, value)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('NativeProbe.qml'))))
    if not engine.rootObjects():
        raise AssertionError(errors)
    window = engine.rootObjects()[0]
    wait_for(window.isExposed)
    pump(300)
    frames, cpu = [], []
    for i in range(10):
        tick = time.perf_counter()
        window.setProperty('cameraX', float(centre[0])+math.sin(i/8)*20)
        pump(1)
        cpu.append((time.perf_counter()-tick)*1000)
        image = window.grabWindow()
        frames.append((time.perf_counter()-tick)*1000)
    window.setProperty('cameraX', float(centre[0]))
    pump(30)
    image = window.grabWindow()
    image.save(str(out/(args.technique+'-probe.png')))
    absent = []
    for index in (0, len(quads)//2, len(quads)-1):
        x, y = quads[index].mean(axis=0)
        px, py = window.width()/2+(x-centre[0])*zoom, window.height()/2-(y-centre[1])*zoom
        if image.pixelColor(round(px), round(py)) == image.pixelColor(0, 0):
            absent.append(index)
    stem = ('rho-' if args.rho else '')+args.technique+('-shader' if args.shader else '')+'-'+str(len(quads))
    image.save(str(out/(stem+'.png')))
    result = dict(technique=args.technique, count=len(quads), cpu_ms=statistics.median(cpu),
                  readback_ms=statistics.median(frames), scope='sandbox GPU readback, not monitor', warnings=errors,
                  absent_samples=absent, shader=args.shader)
    (out/(stem+'.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(result, flush=True)
    assert not errors, errors
    assert not absent, f'Empty modules are not a performance result: {absent}'
    window.close(); engine.deleteLater(); app.processEvents()


if __name__ == '__main__':
    main()
