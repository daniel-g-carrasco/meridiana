"""The catalogue with real key events: filters, selection and a reviewed record saved, as the Widgets did
(their answers recorded on 10/11/2026, quick/aiuti/riferimenti.py)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import _setup
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtQml import QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QSignalSpy, QTest

from quick.impianto.catalog_fixtures import APP, module, settle
from meridiana.data import catalog
from meridiana.gui.backend.catalog import CatalogBackend, PAGE_URL
from meridiana.gui.backend.controls import install_controls
from quick.aiuti import riferimenti

setUpModule = _setup.keep_global_state


class CatalogueParityTest(unittest.TestCase):
    def test_events_filters_selection_and_review_save_the_recorded_values(self):
        records = [module(n, pmax=400 + 10 * n, source='curated' if n < 4 else 'cec') for n in range(8)]
        haystacks = tuple(f"{r['manufacturer']} {r['model']}".casefold() for r in records)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(catalog, '_ordered', return_value=(tuple(records), haystacks)), \
                patch.object(catalog, 'load', return_value=tuple(records)), \
                patch.object(catalog, 'ready', return_value=True):
            backend = CatalogBackend(records={'modules': records}, safe_root=directory)
            engine = QQmlEngine()
            install_controls(engine)
            engine.rootContext().setContextProperty('catalogBackend', backend)
            view = QQuickView(engine, None)
            view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
            view.resize(1366, 900)
            view.setSource(PAGE_URL)
            self.assertEqual(view.status(), QQuickView.Status.Ready)
            view.show()
            settle(backend)
            QTest.qWait(50)
            search = view.rootObject().findChild(QQuickItem, 'catalogSearch')
            search.forceActiveFocus()
            for char in 'Example Panel':
                APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, char))
                APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, char))
            backend.setFilter('source', 'curated')
            backend.setFilter('low', 410)
            backend.setFilter('high', 430)
            backend.setFilter('family', 'topcon')
            backend.setFilter('efficiency_min', 20)
            settle(backend)
            quick_ids = [backend.model.record(i)['id'] for i in range(backend.model.rowCount())]
            self.assertEqual(quick_ids, ['1', '2', '3'])
            backend.select(1, False)
            chosen = QSignalSpy(backend.chosen)
            backend.choose()
            self.assertEqual(chosen.at(0)[1]['id'], '2')
            riferimenti.check(self, chosen.at(0)[1])
            backend.beginEdit(True)
            backend.setEditorField('model', 'Reviewed B')
            backend.setDestination(str(Path(directory) / 'catalogue.json'))
            self.assertTrue(backend.saveEditor(), backend.error)
            actual = json.loads((Path(directory) / 'catalogue.json').read_text(encoding='utf8'))[0]
            self.assertEqual(actual['model'], 'Reviewed B')
            riferimenti.check(self, actual)
            settle(backend)
            view.close()
            view.setSource(PAGE_URL.fromLocalFile(''))
            view.deleteLater()
            backend.deleteLater()
            engine.deleteLater()
            APP.processEvents()
