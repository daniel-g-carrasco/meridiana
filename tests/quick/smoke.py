"""Offscreen smoke and visual evidence for the independent application."""
import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QEventLoop, QObject, QTimer

from meridiana import model
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.sample import SAMPLE, recorded_weather


def pump(milliseconds):
    loop = QEventLoop()
    QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('build/quick'))
    parser.add_argument('--large-text', action='store_true')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    app = create_app()
    print('Application created', flush=True)
    original = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='quick-smoke-') as d:
        p, _ = model.Project.load(SAMPLE)
        recorded_weather(p, Path(d))
        host = QuickWindow(p, Path(d), large=args.large_text)
        print('QML loaded', host.warnings[:3], flush=True)
        host.window.show()
        host.bridge.recompute()
        start = time.perf_counter()
        while host.bridge.busy and time.perf_counter()-start < 1200:
            pump(20)
        print('Worker ready', host.bridge.moduleCount, host.bridge.error, flush=True)
        result = {'modules': host.bridge.moduleCount, 'year': host.bridge.year.get('hours'),
                  'checks': len(host.bridge.checkRows), 'error': host.bridge.error,
                  'warnings': host.warnings, 'metrics': host.bridge.metrics,
                  'project_sha256': original}
        for phase in ('model', 'production'):
            host.window.setProperty('phase', phase)
            pump(300)
            image = host.window.grabWindow()
            if image.isNull():
                raise RuntimeError('Offscreen image is empty')
            image.save(str(args.out / (phase + '.png')))
        host.window.setProperty('phase', 'model')
        host.window.resize(900, 640)
        pump(300)
        plan = host.window.findChild(QObject, 'plan')
        plan.fit()
        host.window.grabWindow().save(str(args.out / 'narrow.png'))
        result['warnings'] = host.warnings
        print(json.dumps(result, ensure_ascii=False), flush=True)
        assert original == hashlib.sha256(SAMPLE.read_bytes()).hexdigest()
        assert result['modules'] == 778 and result['year'] == 8760
        assert not result['warnings'] and not result['error']
        (args.out / 'smoke.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        host.close()
        app.processEvents()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
