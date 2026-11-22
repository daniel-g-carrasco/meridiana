"""Annotations keep their world clipping while the camera moves (R695)."""
import json
import os
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QCoreApplication, QObject, QPoint, QPointF, Qt, QTimer
from PySide6.QtGui import QWheelEvent

from meridiana.app.view.measure_tool import Measure, Probe
from meridiana.core.model.model import Building, Project
from quick.vista3d._fidelity_support import data, js, settle
from quick.aiuti.avvisi import real

setUpModule = _setup.keep_global_state


def wheel(window, view, delta):
    at = view.mapToScene(QPointF(view.width() / 2, view.height() / 2))
    QCoreApplication.sendEvent(window, QWheelEvent(at, at, QPoint(), QPoint(0, delta),
                               Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False))


def visible_state(layer):
    pending, pills = [layer], []
    while pending:
        item = pending.pop()
        pending.extend(item.childItems())
        if item.objectName() == 'measurePill' and item.isVisible():
            pills.append(item)
    return dict(lines=bool(data(layer, 'paths(done,false).length')), pills=bool(pills),
                projected=data(layer, 'paths(done,false)'))


class AnnotationMotion(unittest.TestCase):
    def test_wheel_orbit_and_pan_keep_lines_and_pills_on_every_frame(self):
        from meridiana.gui.application import QuickWindow, create_app
        app = create_app()
        project = Project(name='Annotation motion')
        project.buildings.append(Building(id='b', name='Block', height=6, footprint=[[0, 0], [24, 0], [24, 12], [0, 12]]))
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        host = QuickWindow(project, Path(tmp.name), real_views=True, theme={'reducedMotion': True})
        self.addCleanup(host.close)
        host.window.resize(1100, 800)
        host.window.show()
        host.window.setProperty('viewMode', '3d')
        self.assertTrue(_setup.wait_until(app, lambda: host.window.findChild(QObject, 'viewport3d') is not None))
        view = host.window.findChild(QObject, 'viewport3d')
        self.assertTrue(_setup.wait_until(app, lambda: len(host.scene.triangles[0]) and not host.scene.drawing))
        js(view, 'userMoved=true; cameraState={position:[12,3,40],target:[12,3,-6],rotation:[1,0,0,0],fov:60,ortho:false}')
        host.measure.tool.measures[:] = [Measure(1, 'distance', (Probe((4, -5, 3)), Probe((20, -5, 3))))]
        host.measure._changed()
        layer = view.findChild(QObject, 'sceneMeasures')
        self.assertTrue(_setup.wait_until(app, lambda: visible_state(layer)['pills'], 30))
        settle(app, .3)
        js(view, 'orbitPoint=cameraState.target; depthPoint=cameraState.target')
        records = {}
        for kind in ('wheel', 'orbit', 'pan'):
            frames = []
            moves = 0
            def sample(frames=frames):
                frames.append(visible_state(layer))
            def move(kind=kind, frames=frames):
                nonlocal moves
                moves += 1
                if kind == 'wheel':
                    # A renderer may swap several frames per input: alternate the device steps, not frame parity.
                    wheel(host.window, view, 120 if moves % 2 else -120)
                elif kind == 'orbit':
                    js(view, 'actions([{kind:"orbit",phase:"move",dx:.3,dy:0}])')
                else:
                    js(view, 'actions([{kind:"pan",phase:"move",dx:.5,dy:0}])')
            timer = QTimer()
            timer.setInterval(30)
            timer.timeout.connect(move)
            host.window.frameSwapped.connect(sample)
            timer.start()
            settle(app, 1)
            timer.stop()
            host.window.frameSwapped.disconnect(sample)
            records[kind] = frames
        print('Motion frames:', {k: dict(total=len(v), missing=sum(not f['lines'] or not f['pills'] for f in v))
                                 for k, v in records.items()})
        if target := os.environ.get('MERIDIANA_ANNOTATION_TRACE'):
            with Path(target).open('x', encoding='utf-8', newline='\r\n') as stream:
                json.dump(records, stream, indent=2)
        for kind, frames in records.items():
            self.assertGreater(len(frames), 5, kind)
            self.assertTrue(all(f['lines'] and f['pills'] for f in frames),
                            (kind, sum(not f['lines'] or not f['pills'] for f in frames), len(frames)))
            self.assertTrue(any(f['projected'] != frames[0]['projected'] for f in frames[1:]), kind)
        self.assertTrue(_setup.wait_until(app, lambda: not view.property('sceneMeasure').property('annotationPending'), 30))
        # Same measurement, opposite camera: once at rest the building must
        # occlude it, and moving back must make it visible again.
        js(view, 'cameraState={position:[12,3,-40],target:[12,3,6],rotation:[0,0,1,0],fov:60,ortho:false}')
        self.assertTrue(_setup.wait_until(app, lambda: not visible_state(layer)['lines'], 30))
        self.assertFalse(visible_state(layer)['pills'])
        js(view, 'cameraState={position:[12,3,40],target:[12,3,-6],rotation:[1,0,0,0],fov:60,ortho:false}')
        self.assertTrue(_setup.wait_until(app, lambda: visible_state(layer)['lines'] and visible_state(layer)['pills'], 30))
        self.assertFalse(real(host.warnings), host.warnings)
        host.close()
