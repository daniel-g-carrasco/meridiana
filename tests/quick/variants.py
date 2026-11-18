"""Render two existing accent choices without deciding the future product's look."""
import argparse
import tempfile
from pathlib import Path

from meridiana import checks, jobs, model, theme_colors
from meridiana.quick.app import QuickWindow, create_app, tokens
from meridiana.quick.sample import SAMPLE
from quick.gestures import pump


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    app = create_app()
    with tempfile.TemporaryDirectory() as temporary:
        project, _ = model.Project.load(SAMPLE)
        results, keys, _ = jobs.layout_of(project)
        host = QuickWindow(project, Path(temporary))
        host.bridge.accept_layout(0, results, keys)
        host.bridge._checks = [vars(row) for row in checks.gather(project, results, {})]
        host.bridge.checksChanged.emit()
        host.bridge.select('building', project.buildings[0].id, '')
        for accent in ('indigo', 'bronze'):
            target = args.out/('look-'+accent+'.png')
            if target.exists():
                raise FileExistsError(target)
            values = theme_colors.derive(theme_colors.PRESETS[accent], False, 'grey').tokens
            colors = {k: v for k, v in values.items() if isinstance(v, str)}
            colors.update({'plan_'+k: v for k, v in values['plan'].items()})
            colors = {k: '#'+v[7:9]+v[1:7] if len(v)==9 else v for k, v in colors.items()}
            host.engine.rootContext().setContextProperty('D', {**tokens(), **colors})
            host.window.show()
            pump(250)
            image = host.window.grabWindow()
            assert not image.isNull() and host.bridge.moduleCount == 778
            assert not host.warnings, host.warnings
            image.save(str(target))
        host.close()
        app.processEvents()


if __name__ == '__main__':
    main()
