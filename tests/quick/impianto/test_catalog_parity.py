"""Functional parity against actual Widgets handlers, including reviewed records."""
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
from meridiana import catalog
from meridiana.quick.backend.catalog import CatalogBackend, PAGE_URL
from meridiana.quick.backend.controls import install_controls
from meridiana.ui.catalog_dialog import CatalogDialog, forget_filters
from meridiana.ui.catalog_editor import CatalogEditor

setUpModule = _setup.keep_global_state


class CatalogueParityTest(unittest.TestCase):
    def test_widgets_and_quick_events_filters_selection_and_review_save_same_values(self):
        records = [module(n, pmax=400 + 10 * n, source='curated' if n < 4 else 'cec') for n in range(8)]
        haystacks = tuple(f"{r['manufacturer']} {r['model']}".casefold() for r in records)
        forget_filters()
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(catalog, '_ordered', return_value=(tuple(records), haystacks)), \
                patch.object(catalog, 'load', return_value=tuple(records)), \
                patch.object(catalog, 'ready', return_value=True):
            widget = CatalogDialog('modules')
            widget.show()
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
            QTest.keyClicks(widget.query, 'Example Panel')
            for char in 'Example Panel':
                APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, char))
                APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, char))
            widget.origin.setCurrentIndex(widget.origin.findData('curated'))
            widget.low.setValue(410)
            widget.high.setValue(430)
            widget.family.setCurrentIndex(widget.family.findData('topcon'))
            widget.efficiency.setValue(20)
            backend.setFilter('source', 'curated')
            backend.setFilter('low', 410)
            backend.setFilter('high', 430)
            backend.setFilter('family', 'topcon')
            backend.setFilter('efficiency_min', 20)
            widget.timer.stop()
            widget._search()
            settle(backend)
            quick_ids = [backend.model.record(i)['id'] for i in range(backend.model.rowCount())]
            widget_ids = [widget.record_at(i)['id'] for i in range(widget.rows.rowCount())]
            self.assertEqual(quick_ids, widget_ids)
            self.assertEqual(quick_ids, ['1', '2', '3'])
            widget.table.selectRow(1)
            backend.select(1, False)
            chosen = QSignalSpy(backend.chosen)
            backend.choose()
            self.assertEqual(chosen.at(0)[1], widget.chosen())
            widget_editor = CatalogEditor('modules', record=widget.chosen())
            widget_editor.fields['model'].setText('Reviewed B')
            expected = widget_editor.record()
            backend.beginEdit(True)
            backend.setEditorField('model', 'Reviewed B')
            backend.setDestination(str(Path(directory) / 'catalogue.json'))
            self.assertTrue(backend.saveEditor(), backend.error)
            actual = json.loads((Path(directory) / 'catalogue.json').read_text(encoding='utf8'))[0]
            self.assertEqual(actual, expected)
            settle(backend)
            widget_editor.close()
            widget_editor.deleteLater()
            widget.close()
            widget.deleteLater()
            view.close()
            view.setSource(PAGE_URL.fromLocalFile(''))
            view.deleteLater()
            backend.deleteLater()
            engine.deleteLater()
            APP.processEvents()
