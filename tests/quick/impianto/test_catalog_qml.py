"""Native Qt Quick catalogue: real input and bounded live delegates (R394/R395)."""
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtQml import QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickView
from PySide6.QtTest import QTest

from quick.impianto.catalog_fixtures import APP, module, settle
from meridiana.quick.backend.catalog import CatalogBackend, PAGE_URL
from meridiana.quick.backend.controls import install_controls


def item(root, name):
    found = root.findChild(QQuickItem, name)
    if found is not None:
        return found
    pending = [root.window().contentItem()]
    while pending:
        current = pending.pop()
        if current.objectName() == name:
            return current
        pending.extend(current.childItems())
    return None


class CompareTest(unittest.TestCase):
    """R458 voce 7: «Compare selected products» of the Widgets catalogue, two to four products side by side."""
    def test_compare_widens_the_card_into_a_table_of_the_selected_products(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        engine = QQmlEngine()
        install_controls(engine)
        backend = CatalogBackend(records={'modules': [module(n) for n in range(6)]}, safe_root=temporary.name)
        engine.rootContext().setContextProperty('catalogBackend', backend)
        view = QQuickView(engine, None)
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.resize(1366, 900)
        view.setSource(PAGE_URL)
        self.assertEqual(view.status(), QQuickView.Status.Ready, [e.toString() for e in view.errors()])
        view.show()
        QTest.qWait(100)
        settle(backend)
        root = view.rootObject()
        button, card = item(root, 'catalogCompare'), item(root, 'catalogCard')
        self.assertEqual(button.property('text'), backend.texts['compareButton'])
        table = item(root, 'catalogList')
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=table.mapToScene(QPointF(100, 15)).toPoint())
        click = button.mapToScene(button.boundingRect().center()).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=click)
        QTest.qWait(30)
        self.assertFalse(root.property('comparing'))                        # one product: said how to choose more
        self.assertTrue(item(root, 'catalogCompareHint').isVisible())
        narrow = card.width()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier,
                         pos=table.mapToScene(QPointF(100, 45)).toPoint())
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier,
                         pos=table.mapToScene(QPointF(100, 75)).toPoint())
        self.assertEqual(backend.selectedCount, 3)
        click = button.mapToScene(button.boundingRect().center()).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=click)
        QTest.qWait(50)
        self.assertTrue(root.property('comparing'))
        self.assertGreater(card.width(), narrow * 1.5)
        header = item(root, 'catalogCompareHeader')
        names = sorted(c.property('text') for c in header.childItems() if c.property('text'))
        self.assertEqual(names, sorted(backend.selectedNames))
        self.assertEqual(button.property('text'), backend.texts['compareClose'])
        backend.clearSelection() if hasattr(backend, 'clearSelection') else backend.select(0, False)
        QTest.qWait(30)
        self.assertFalse(root.property('comparing'))                        # one product left: back to its card
        view.close()
        engine.deleteLater()


class ShowAllTest(unittest.TestCase):
    """R434, Daniel 06/11/2026: the catalogue opens on what is current and for Europe, «Show all (n)» beside the
    filters, in sight, and a click on it shows every product; «Clear» goes back."""
    def test_show_all_beside_the_filters_brings_every_product(self):
        from meridiana.quick.backend import catalog as quick_catalog
        quick_catalog._REMEMBERED.clear()
        self.addCleanup(quick_catalog._REMEMBERED.clear)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        engine = QQmlEngine()
        install_controls(engine)
        backend = CatalogBackend(safe_root=temporary.name)
        engine.rootContext().setContextProperty('catalogBackend', backend)
        view = QQuickView(engine, None)
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.resize(1366, 900)
        view.setSource(PAGE_URL)
        self.assertEqual(view.status(), QQuickView.Status.Ready, [e.toString() for e in view.errors()])
        view.show()
        QTest.qWait(100)
        backend.setKind('inverters')
        settle(backend)
        QTest.qWait(50)
        root = view.rootObject()
        button, state = item(root, 'catalogShowEverything'), item(root, 'catalogState')
        self.assertTrue(button.isVisible())
        self.assertGreater(backend.hiddenCount, 2000)
        self.assertEqual(button.property('text'), backend.showAllText)
        place, beside = button.mapToScene(QPointF(0, 0)), state.mapToScene(QPointF(0, 0))
        self.assertAlmostEqual(place.y(), beside.y(), delta=state.height())          # on the row of the filters
        self.assertLess(place.y(), view.height() / 4)                                 # at the top
        self.assertTrue(0 <= place.x() and place.x() + button.width() <= view.width())
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=button.mapToScene(button.boundingRect().center()).toPoint())
        settle(backend)
        QTest.qWait(50)
        self.assertEqual(len([r for row in backend.model.rows for r in row.get('members', [row])]), len(backend._all))
        self.assertFalse(button.isVisible())
        self.assertEqual(backend.filters['state'], '')
        backend.clearFilters()
        settle(backend)
        QTest.qWait(50)
        self.assertTrue(button.isVisible())
        view.close()
        engine.deleteLater()


class CatalogueQuickTest(unittest.TestCase):
    def test_native_search_end_selection_editor_and_live_theme(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        engine = QQmlEngine()
        theme = install_controls(engine)
        backend = CatalogBackend(records={'modules': [module(n) for n in range(17000)]}, safe_root=temporary.name)
        engine.rootContext().setContextProperty('catalogBackend', backend)
        view = QQuickView(engine, None)
        view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        view.resize(1366, 900)
        warnings = []
        engine.warnings.connect(lambda values: warnings.extend(v.toString() for v in values))
        view.setSource(PAGE_URL)
        self.assertEqual(view.status(), QQuickView.Status.Ready, [e.toString() for e in view.errors()])
        view.show()
        QTest.qWait(100)
        settle(backend)
        root = view.rootObject()
        search = item(root, 'catalogSearch')
        self.assertIsNotNone(search)
        point = search.mapToScene(search.boundingRect().center()).toPoint()
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=point)
        for character in 'Panel 16999':
            APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, character))
            APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, character))
        settle(backend)
        self.assertEqual(backend.model.rowCount(), 1)
        table = item(root, 'catalogList')
        QTest.mouseClick(view, Qt.MouseButton.LeftButton,
                         pos=table.mapToScene(QPointF(100, 15)).toPoint())
        self.assertEqual(backend.selectedRecord['model'], 'Panel 16999')
        backend.clearFilters()
        settle(backend)
        QTest.mouseClick(view, Qt.MouseButton.LeftButton,
                         pos=table.mapToScene(QPointF(100, 15)).toPoint())
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ControlModifier,
                         pos=table.mapToScene(QPointF(100, 45)).toPoint())
        self.assertEqual(backend.selectedCount, 2)
        table.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_End)
        QTest.qWait(80)
        self.assertEqual(backend.selectedRecord['model'], 'Panel 16999')
        live_rows = [child for child in table.childItems()[0].childItems()
                     if child.objectName() == 'catalogProductRow']
        self.assertGreater(len(live_rows), 1)
        self.assertLess(len(live_rows), 70)
        selected_row = next(row for row in live_rows if row.property('selected'))
        plain_row = next(row for row in live_rows if not row.property('selected') and
                         0 <= row.y() - table.property('contentY') < table.height())
        screenshot = view.grabWindow()
        dpr = screenshot.devicePixelRatio()
        def row_color(row):
            point = row.mapToScene(QPointF(2, row.height() / 2))
            return screenshot.pixelColor(int((point.x() + .5) * dpr), int((point.y() + .5) * dpr))
        self.assertNotEqual(row_color(selected_row), row_color(plain_row))
        backend.beginEdit(True)
        QTest.qWait(80)
        self.assertIsNotNone(root.findChild(QObject, 'catalogEditor'))
        theme.configure({'theme': 'dark', 'font': 'inter', 'textSize': 'large'})
        QTest.qWait(80)
        self.assertEqual(search.property('font').family(), theme.fontFamily)
        model_field = item(root, 'catalogField_model')
        self.assertIsNotNone(model_field)
        model_field.forceActiveFocus()
        QTest.keyClick(view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        for char in 'Edited via QML':
            APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyPress, 0, Qt.KeyboardModifier.NoModifier, char))
            APP.sendEvent(view, QKeyEvent(QEvent.Type.KeyRelease, 0, Qt.KeyboardModifier.NoModifier, char))
        destination = item(root, 'catalogDestination')
        path = Path(temporary.name) / 'qml-personal.json'
        destination.setProperty('text', str(path))
        save = item(root.findChild(QObject, 'catalogEditor'), 'dialogAccept')      # R21-F2: the window's own «Save»
        QTest.mouseClick(view, Qt.MouseButton.LeftButton, pos=save.mapToScene(save.boundingRect().center()).toPoint())
        settle(backend)
        self.assertFalse(backend.editing, backend.error)
        self.assertEqual(json.loads(path.read_text(encoding='utf8'))[0]['model'], 'Edited via QML')
        self.assertFalse(warnings, '\n'.join(warnings))
        self.assertFalse(view.grabWindow().isNull())
        view.close()
        view.setSource(PAGE_URL.fromLocalFile(''))
        view.deleteLater()
        backend.deleteLater()
        engine.deleteLater()
        APP.processEvents()
