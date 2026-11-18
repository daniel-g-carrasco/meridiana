"""Real native Quick3D smoke/photograph probe. No physical mouse or user settings are touched."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from PySide6.QtCore import QTimer, QSize  # noqa: E402
from PySide6.QtGui import QFont, QGuiApplication  # noqa: E402
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface  # noqa: E402
from PySide6.QtQuickControls2 import QQuickStyle  # noqa: E402

from meridiana import i18n, jobs, model  # noqa: E402
from meridiana.session import ProjectSession  # noqa: E402
from meridiana.quick.backend.scene_host import SceneWindow  # noqa: E402


def fixture():
    p = model.Project(name='Prova 3D')
    p.buildings.append(model.Building('b1', 'Capannone', [[0, 0], [40, 0], [40, 20], [0, 20]], height=9.5))
    p.subfields.append(model.SubField('s1', 'Sud', [[1, 1], [39, 1], [39, 19], [1, 19]],
                                       building='b1', params={'tilt': 15.}, filled=True))
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'build/quick-foto/r12-vista3d')
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ['QML_DISABLE_DISK_CACHE'] = '1'
    os.environ['QT_DISABLE_SHADER_DISK_CACHE'] = '1'
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Direct3D11)
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication([])
    i18n.setup('it')
    font = QFont('IBM Plex Sans'); font.setPixelSize(13); app.setFont(font)
    session = ProjectSession(fixture())
    results, keys, _ = jobs.layout_of(session.project, {})
    session.layout_done(session.generation, results, keys)
    host = SceneWindow(session, args.out / 'instances', args.width, args.height, args.dark)
    host.window.setMinimumSize(QSize(args.width,args.height))
    started = time.perf_counter()
    host.window.show()
    result = {}

    def capture():
        image = host.window.grabWindow()
        scale = host.window.devicePixelRatio()
        stem = f'{args.width}x{args.height}-s{scale:g}-' + ('dark' if args.dark else 'light')
        saved = image.save(str(args.out / (stem + '.png')))
        result.update(platform=app.platformName(), backend=str(host.window.rendererInterface().graphicsApi()),
                      scale=scale, logical=[host.window.width(),host.window.height()], pixels=[image.width(), image.height()], modules=host.backend.moduleCount,
                      elapsed_ms=(time.perf_counter()-started)*1000, warnings=host.warnings, saved=saved)
        (args.out / (stem + '.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result))
        app.quit()

    QTimer.singleShot(1800, capture)
    app.exec()
    host.close()
    app.processEvents()
    return 1 if result.get('warnings') or not result.get('saved') else 0


if __name__ == '__main__':
    raise SystemExit(main())
