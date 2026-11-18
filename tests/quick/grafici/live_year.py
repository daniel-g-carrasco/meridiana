"""Run F5 on the actual workbench and await the unmodified Rho pipeline."""
import argparse
import json
from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from meridiana import jobs, model
from meridiana.quick.app import QuickWindow, create_app
from meridiana.quick.sample import recorded_weather
from quick.gestures import key, pump, wait_for


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('project', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    original = args.project.read_bytes()
    project = model.Project.load(args.project)[0]
    app = create_app()
    with tempfile.TemporaryDirectory(dir=args.output) as temporary:
        cache = Path(temporary)
        assert recorded_weather(project, cache)
        host = QuickWindow(project, cache, real_views=True)
        try:
            host.plan.configureMaps({'source': 'none'})
            layouts, keys, _errors = jobs.layout_of(project)
            host.bridge.accept_layout(host.bridge.session.generation, layouts, keys)
            win = host.window
            win.resize(1600, 960)
            win.show()
            win.requestActivate()
            host.shell.trigger('phase_production')
            pump(500)
            assert not host.bridge.session.energy.get('sim')
            start = time.perf_counter()
            key(app, win, Qt.Key_F5)
            wait_for(lambda: host.bridge.busy, 10)
            print('F5 accepted by the actual window; waiting for its process.', flush=True)
            reported = 0
            while host.bridge.busy and time.perf_counter()-start < 600:
                pump(100)
                elapsed = int(time.perf_counter()-start)
                if elapsed//30 > reported:
                    reported = elapsed//30
                    print(f'Calculation running: {elapsed} s', flush=True)
            result = host.parts.controllers['results']
            wait_for(lambda: not host.bridge.busy and not result.busy, 30)
            year = host.bridge.session.energy
            assert year.get('sim') is not None, host.bridge.error
            assert len(year['sim'].hourly) == 8760
            assert year.get('load') is not None and year.get('econ') is not None
            assert not result.stale
            pages = {}
            for phase, shortcut in (('production', Qt.Key_3), ('consumption', Qt.Key_4), ('economics', Qt.Key_5)):
                key(app, win, shortcut, modifiers=Qt.ControlModifier)
                pump(900)
                assert win.property('phase') == phase
                page = getattr(result, phase)
                assert page['tabs'] and page['tiles'] and page['basis']
                pages[phase] = dict(tiles=page['tiles'], tabs=[tab['title'] for tab in page['tabs']], basis=page['basis'])
                assert win.grabWindow().save(str(args.output / f'{phase}.png'))
            assert not host.warnings, host.warnings
            payload = dict(seconds=time.perf_counter()-start, platform=app.platformName(),
                           graphics=str(win.rendererInterface().graphicsApi()), warnings=host.warnings,
                           hours=len(year['sim'].hourly), energy_kwh=year['sim'].energy_kwh,
                           metrics=host.bridge.metrics, pages=pages)
            (args.output / 'result.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf8')
            print(json.dumps({k:v for k,v in payload.items() if k not in ('pages', 'metrics')}, ensure_ascii=False), flush=True)
        finally:
            host.close()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
    assert args.project.read_bytes() == original, 'The reference project was changed'


if __name__ == '__main__':
    main()
