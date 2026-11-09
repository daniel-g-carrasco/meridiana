"""Record logical and physical extents of the reported 200 percent grab failure."""
import json
import argparse
import tempfile
from pathlib import Path

from _fixtures import capannone
from meridiana import jobs
from meridiana.quick.app import QuickWindow, create_app
from quick.gestures import item, point, pump


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('build/quick-foto/clip'))
    args = parser.parse_args()
    app = create_app()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as cache:
        host = QuickWindow(capannone(), Path(cache))
        results, keys, _ = jobs.layout_of(host.bridge.session.project)
        host.bridge.accept_layout(0, results, keys)
        win = host.window
        win.show()
        pump(40)
        plan = item(win, 'plan')
        records = []

        def shot(name):
            image = win.grabWindow()
            pane = item(win, 'checksPartLoader')
            p = point(pane, 0, 0)
            record = dict(name=name, window=[win.width(), win.height()],
                          image=[image.width(), image.height()], dpr=image.devicePixelRatio(),
                          windowDpr=win.devicePixelRatio(), checks=[p.x(), p.y(), pane.width(), pane.height()],
                          backend=str(win.rendererInterface().graphicsApi()))
            image.save(str(out / f'{app.platformName()}-{name}.png'))
            records.append(record)

        shot('initial')
        plan.setProperty('panX', plan.property('panX') + 150)
        pump(40)
        win.resize(900, 640)
        pump(80)
        plan.fit()
        shot('resize-immediate')
        pump(100)
        shot('resize-settled')
        win.requestUpdate()
        pump(100)
        shot('request-update')
        print(json.dumps(records, indent=2))
        (out/'measurements.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        host.close()
        app.processEvents()


if __name__ == '__main__':
    main()
