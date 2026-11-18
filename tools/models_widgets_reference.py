"""Capture the unchanged Widgets View3D on D3D11 for the Quick migration comparison."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'build/quick-foto/r12-vista3d/widgets-reference')
    parser.add_argument('--scale', type=float, default=float(os.environ.get('QT_SCALE_FACTOR', '1')))
    parser.add_argument('--quick-aligned', action='store_true',
                        help='Capture Quick with the exact camera from an existing Widgets reference JSON')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ['QT_SCALE_FACTOR'] = str(args.scale)
    os.environ['QT_QPA_PLATFORM'] = 'windows'
    os.environ['QSG_RHI_BACKEND'] = 'd3d11'
    sys.path.insert(0, str(ROOT / 'src'))

    # The reference only reads code and creates its own synthetic project.
    # Isolate all incidental settings/log paths from Daniel's installed app.
    with tempfile.TemporaryDirectory(prefix='widgets-reference-', dir=args.out) as isolated:
        for name in ('HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'XDG_CONFIG_HOME', 'XDG_CACHE_HOME'):
            os.environ[name] = isolated
        from PySide6.QtCore import QCoreApplication, QEvent, Qt
        from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
        from PySide6.QtWidgets import QApplication
        from meridiana import config, i18n, jobs, mesh, model, sun
        from meridiana.ui.theme import Theme
        from meridiana.ui.view3d import View3D

        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
        app = QApplication([])
        i18n.setup('it')
        cfg = config.Config(theme='light', accent='indigo', backgrounds='grey', font='plex')
        theme = Theme(cfg, app=app)
        project = model.Project(name='Native scene test')
        project.buildings.append(model.Building('b1', 'Capannone', [[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5))
        project.subfields.append(model.SubField('s1', 'Sud', [[1, 1], [39, 1], [39, 19], [1, 19]], building='b1',
                                               params={'tilt': 15.}, filled=True))
        results, _keys, _ = jobs.layout_of(project, {})
        building_mesh, module_table, _ = mesh.project_scene(project, results)
        assert len(module_table) == 128, len(module_table)
        if args.quick_aligned:
            return capture_aligned(app, project, results, _keys, args, isolated)
        view = View3D()
        view.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        errors = []
        view.failed.connect(errors.append)
        view.backend.reduced_motion = True
        view.resize(1366, 900)
        view.show()
        view.setFixedSize(1366, 900)

        def wait(seconds=0.4):
            until = time.perf_counter() + seconds
            while time.perf_counter() < until:
                app.processEvents()
                time.sleep(0.004)

        wait()
        view.show_scene(building_mesh, module_table, fit=True)
        when = datetime(2026, 6, 21, 12, tzinfo=ZoneInfo('Europe/Rome'))
        sunlight = sun.position(project.site.lat, project.site.lon, when)
        view.set_sun(sunlight.elevation, sunlight.bearing)
        view.set_navigation('autocad', 'turntable', 'cursor', True)
        wait(0.7)
        assert view.drawn(), 'QuickImage did not create a graphics device'
        assert view.quickWindow().rendererInterface().graphicsApi() == QSGRendererInterface.GraphicsApi.Direct3D11
        metadata = {'platform': app.platformName(), 'graphics': 'Direct3D11', 'logicalSize': [view.width(), view.height()],
                    'requestedScale': args.scale, 'devicePixelRatio': view.devicePixelRatioF(),
                    'moduleCount': len(module_table), 'vertices': len(building_mesh[0]),
                    'sun': {'when': when.isoformat(), 'elevation': sunlight.elevation, 'bearing': sunlight.bearing},
                    'camera': {'position': view.backend.camera.position.tolist(),
                               'rotation': view.backend.camera.rotation.tolist(),
                               'target': view.backend.camera.target.tolist(),
                               'fov': view.backend.camera.fov, 'ortho': view.backend.camera.ortho},
                    'captures': []}
        for mode in ('light', 'dark'):
            cfg.theme = mode
            theme.apply()
            view.cube.set_colours(theme.tokens)
            wait()
            image = view.grab().toImage()
            assert not image.isNull()
            name = f'1366x900-{mode}-s{args.scale:g}.png'
            assert image.save(str(args.out / name))
            metadata['captures'].append({'file': name, 'pixels': [image.width(), image.height()]})
        metadata['errors'] = errors
        assert not errors, errors
        (args.out / f'reference-s{args.scale:g}.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        print(json.dumps(metadata, indent=2))
        view.close()
        view.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    return 0


def capture_aligned(app, project, results, keys, args, cache):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtQml import QQmlEngine, QQmlExpression
    from PySide6.QtQuick import QSGRendererInterface
    from PySide6.QtQuickControls2 import QQuickStyle
    from meridiana.quick.backend.scene_host import SceneWindow
    from meridiana.session import ProjectSession

    QQuickStyle.setStyle('Basic')
    reference = json.loads((args.out / f'reference-s{args.scale:g}.json').read_text(encoding='utf-8'))
    session = ProjectSession(project)
    session.layout_done(session.generation, results, keys)
    host = SceneWindow(session, Path(cache), width=1366, height=900)
    host.window.show()

    def wait(seconds=0.5):
        until = time.perf_counter() + seconds
        while time.perf_counter() < until:
            app.processEvents()
            time.sleep(0.004)

    wait()
    host.view.setProperty('reducedMotion', True)
    expression = QQmlExpression(QQmlEngine.contextForObject(host.view), host.view,
                               'go(' + json.dumps(reference['camera']) + ', false); fitted=true')
    expression.evaluate()
    assert not expression.hasError(), expression.error().toString()
    assert host.window.rendererInterface().graphicsApi() == QSGRendererInterface.GraphicsApi.Direct3D11
    for mode in ('light', 'dark'):
        host.theme.configure({'theme': mode})
        wait()
        image = host.window.grabWindow()
        assert not image.isNull()
        assert image.save(str(args.out / f'quick-aligned-{mode}-s{args.scale:g}.png'))
    assert not host.warnings, host.warnings
    host.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    print(json.dumps({'alignedCamera': reference['camera'], 'scale': args.scale, 'warnings': []}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
