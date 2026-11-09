"""Native D3D11 images with the actual Widgets inspector beside the Quick page."""
import argparse
import json
import os
import time
from pathlib import Path

os.environ.pop('QT_QPA_PLATFORM', None)
os.environ['QSG_RHI_BACKEND'] = 'd3d11'

import _setup  # noqa: E402
from PySide6.QtCore import QSize, QRect  # noqa: E402
from PySide6.QtGui import QAction, QImage, QPainter, QColor  # noqa: E402
from PySide6.QtQml import QQmlEngine  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from shiboken6 import delete  # noqa: E402
from quick.parity.differential import connected_fixture  # noqa: E402
from quick.parity.realwindow import FrameRecorder, wait_frames  # noqa: E402
from meridiana import jobs, i18n, config  # noqa: E402
from meridiana.session import ProjectSession  # noqa: E402
from meridiana.quick.backend.plant import create_page, PAGE_URL  # noqa: E402
from meridiana.ui.plant_page import PlantInspector  # noqa: E402
from meridiana.ui.theme import Theme  # noqa: E402


def wait(app, backend):
    deadline = time.monotonic() + 60
    while backend.busy and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(.01)
    assert not backend.busy, backend.message
    QTest.qWait(100)


def capture(scale, revision):
    app = _setup.qt_or_skip()
    i18n.setup('it')
    out = Path('build/quick-foto/impianto') / revision
    out.mkdir(parents=True, exist_ok=True)
    project = connected_fixture()
    session = ProjectSession(project)
    session.results, session.layout_keys, _laid = jobs.layout_of(project)
    evidence = []
    for mode in ('light', 'dark'):
        cfg = config.Config(theme=mode, accent='indigo', backgrounds='grey', font='plex')
        theme = Theme(cfg)
        theme.apply()
        for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
            engine = QQmlEngine()
            backend = create_page(engine, session)
            engine._meridiana_theme.configure({'theme': mode}) if hasattr(engine, '_meridiana_theme') else None
            from meridiana.quick.backend.controls import install_controls
            install_controls(engine).configure({'theme': mode, 'font': 'plex', 'backgrounds': 'grey', 'accent': 'indigo'})
            warnings = []
            engine.warnings.connect(lambda errors, dest=warnings: dest.extend(e.toString() for e in errors))
            view = QQuickView(engine, None)
            view.setMinimumSize(QSize(width, height))
            view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
            view.resize(width, height)
            view.setSource(PAGE_URL)
            assert view.status() == QQuickView.Status.Ready, view.errors()
            view.show()
            QTest.qWaitForWindowExposed(view)
            wait(app, backend)
            backend.selectString(0)
            root = view.rootObject()
            root.setProperty('stringsView', 'table')
            QTest.qWait(120)
            image = view.grabWindow()
            assert not image.isNull()
            assert (view.width(), view.height()) == (width, height)
            name = f'plant-{mode}-s{scale}-{width}x{height}'
            target = out / (name + '.png')
            assert not target.exists(), target
            assert image.save(str(target))
            actions = {key: QAction(key) for key in ('inverter_catalog', 'inverter_auto', 'strings_auto', 'strings_manual', 'strings_clear')}
            reference = PlantInspector(actions)
            reference.show_plant(project, backend.state, chosen=0)
            reference.setMinimumSize(420, height)
            reference.resize(420, height)
            reference.show()
            QTest.qWait(100)
            old = reference.grab().toImage()
            assert old.save(str(out / (name + '-widgets.png')))
            # Both sources are native Qt captures; this only places them side by side.
            combined = QImage(image.width() + old.width(), max(image.height(), old.height()), QImage.Format.Format_RGB32)
            combined.fill(QColor(theme.tokens['window']))
            painter = QPainter(combined)
            image.setDevicePixelRatio(1)
            old.setDevicePixelRatio(1)
            painter.drawImage(0, 0, old)
            painter.drawImage(old.width(), 0, image)
            painter.end()
            assert combined.save(str(out / (name + '-beside.png')))
            if width == 1366:
                for state in ('cards', 'diagram'):
                    root.setProperty('stringsView', state)
                    QTest.qWait(100)
                    assert view.grabWindow().save(str(out / (name + '-' + state + '.png')))
                with FrameRecorder(view, names=('calculate', 'layout')) as frames:
                    wait_frames(frames, 2)
                    root.setProperty('section', 'storage')
                    wait_frames(frames, 4)
                    root.setProperty('section', 'strings')
                    wait_frames(frames, 6)
                frames.assert_valid(stable={'calculate': 1, 'layout': 1}, regions={'header': QRect(0, 0, width, 70)})
                frames.save(out / (name + '-frames'))
                root.setProperty('section', 'storage')
                QTest.qWait(80)
                assert view.grabWindow().save(str(out / (name + '-storage.png')))
            assert not warnings, warnings
            evidence.append(dict(file=name, theme=mode, requested=[width, height],
                                 actual=[view.width(), view.height()], pixels=[image.width(), image.height()],
                                 scale=scale, platform=app.platformName(),
                                 graphics_api=str(view.rendererInterface().graphicsApi()), warnings=warnings))
            backend.close()
            reference.close()
            delete(reference)
            view.close()
            delete(view)
            delete(engine)
    (out / f'evidence-s{scale}.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scale', type=int, required=True)
    parser.add_argument('--revision', default='R01')
    args = parser.parse_args()
    capture(args.scale, args.revision)
