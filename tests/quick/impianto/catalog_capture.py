"""Run explicitly on the isolated Windows desktop; save native catalogue evidence."""
import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

os.environ.pop('QT_QPA_PLATFORM', None)

from PySide6.QtQml import QQmlEngine  # noqa: E402
from PySide6.QtCore import QSize, Qt  # noqa: E402
from PySide6.QtQuick import QQuickView  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from shiboken6 import delete  # noqa: E402

import _setup  # noqa: E402
from quick.impianto.catalog_fixtures import APP, settle  # noqa: E402
from meridiana import catalog, i18n  # noqa: E402
from meridiana.quick.backend.catalog import CatalogBackend, PAGE_URL  # noqa: E402
from meridiana.quick.backend.controls import install_controls  # noqa: E402
from meridiana.ui.catalog_dialog import CatalogDialog, forget_filters  # noqa: E402


def capture(scale):
    i18n.setup('it')
    records = [catalog.enrich_module(m) for row in catalog._read('modules_curated.json')
               if (m := catalog.normalise_module(row)) is not None]
    records.extend(catalog.enrich_module(r) for r in catalog._read('modules_cec.json.gz'))
    # The application order, independent of the actual personal catalogue.
    records.sort(key=lambda r: (r.get('source') != 'curated', str(r.get('manufacturer')).casefold(),
                               catalog.power_of(r, 'modules')))
    haystacks = tuple(f"{r['manufacturer']} {r['model']} {r.get('series', '')}".casefold() for r in records)
    target = Path('build/quick-foto/impianto')
    target.mkdir(parents=True, exist_ok=True)
    evidence = []
    for mode in ('light', 'dark'):
        for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
            engine = QQmlEngine()
            install_controls(engine, {'theme': mode, 'backgrounds': 'grey', 'font': 'plex', 'accent': 'indigo'})
            warnings = []
            engine.warnings.connect(lambda values, captured=warnings: captured.extend(v.toString() for v in values))
            backend = CatalogBackend(records={'modules': records})
            engine.rootContext().setContextProperty('catalogBackend', backend)
            view = QQuickView(engine, None)
            view.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            view.setMinimumSize(QSize(width, height))
            view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
            view.resize(width, height)
            view.setSource(PAGE_URL)
            assert view.status() == QQuickView.Status.Ready, view.errors()
            view.show()
            assert QTest.qWaitForWindowExposed(view)
            settle(backend)
            backend.select(0, False)
            QTest.qWait(120)
            filename = f'catalog-{mode}-{scale}-{width}x{height}.png'
            image = view.grabWindow()
            assert not image.isNull()
            assert [view.width(), view.height()] == [width, height]
            assert image.save(str(target / filename))
            if width == 1366:
                backend.beginEdit(True)
                QTest.qWait(100)
                assert view.grabWindow().save(str(target / f'catalog-editor-{mode}-{scale}.png'))
                backend.cancelEdit()
            assert not warnings, warnings
            evidence.append(dict(file=filename, rows=backend.model.rowCount(),
                                 requested=[width, height], logical=[view.width(), view.height()],
                                 pixels=[image.width(), image.height()], dpr=image.devicePixelRatio(),
                                 graphics_api=str(view.rendererInterface().graphicsApi()),
                                 platform=APP.platformName(), warnings=warnings))
            view.close()
            delete(view)
            delete(backend)
            delete(engine)
            forget_filters()
            with patch.object(catalog, '_ordered', return_value=(tuple(records), haystacks)), \
                    patch.object(catalog, 'load', return_value=tuple(records)), \
                    patch.object(catalog, 'ready', return_value=True):
                _setup.meridiana_look(mode, 'indigo')
                reference = CatalogDialog('modules')
                reference.setMinimumSize(width, height)
                reference.resize(width, height)
                reference.show()
                reference.table.selectRow(0)
                QTest.qWait(80)
                assert reference.grab().save(str(target / f'catalog-widgets-{mode}-{scale}-{width}x{height}.png'))
                reference.close()
                delete(reference)
    (target / f'catalog-evidence-{scale}.json').write_text(json.dumps(evidence, indent=2), encoding='utf8')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scale', required=True)
    capture(parser.parse_args().scale)
