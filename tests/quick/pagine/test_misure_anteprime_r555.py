"""R555 (12) (Daniel 09/11/2026: «la casella per scrivere una misura compare in basso a destra senza motivo: va scritta
dentro la pillola della misura già presente, e quelle pillole sono le stesse della pianta»): the measures of the
previews of the canopy and of the building from a template are the plan's sides' pills (M.LengthPill), and a click on
one opens the plan's field (M.OverlayField) in its place. Before: the pills were painted by the preview in a look of
their own, and the field was a text field 120 px wide at the bottom left, 198 px (template) and 304 px (canopy) from
the pill clicked."""
import unittest
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest

import _setup
from meridiana.app.session import ProjectSession
from meridiana.gui.backend import dialogs_preview
from meridiana.gui.backend.controls import install_controls
from meridiana.gui.backend.dialogs import DialogsBackend
from quick.gestures import pump, wait_for

setUpModule = _setup.keep_global_state
ROOT = Path(__file__).resolve().parents[3]
PREVIEW = ROOT / 'src' / 'meridiana' / 'gui' / 'qml' / 'Meridiana' / 'Dialogs' / 'GeometryPreview.qml'


class TheMeasuresAreThePlansPills(unittest.TestCase):
    def setUp(self):
        _setup.qt_or_skip()
        dialogs_preview.register()
        self.backend = DialogsBackend(ProjectSession())
        self.addCleanup(self.backend.close)
        self.view = QQuickView()
        self.addCleanup(self.view.close)
        install_controls(self.view.engine(), dict(theme='light', reducedMotion=True))
        self.view.resize(520, 380)
        component = QQmlComponent(self.view.engine(), QUrl.fromLocalFile(str(PREVIEW)))
        self.root = component.createWithInitialProperties({'backend': self.backend})
        self.assertIsNotNone(self.root, component.errorString())
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.view.setContent(QUrl(), component, self.root)
        self.view.show()
        self.drawing = next(c for c in self.root.childItems() if c.metaObject().className().startswith('DialogPreview'))

    def items(self, test):
        out, pending = [], [self.view.rootObject()]
        while pending:
            item = pending.pop()
            if test(item):
                out.append(item)
            pending.extend(item.childItems())
        return out

    def pill(self, key):
        found = self.items(lambda o: o.objectName() == f'previewPill_{key}')
        return found[0] if found else None

    def write(self, text):
        for ch in text:
            QTest.keyClick(self.view, ch)

    def field(self):
        return self.items(lambda o: o.objectName() == 'dialog_measure')[0]

    def test_each_measure_is_a_length_pill_where_the_preview_places_it(self):
        for kind in ('template', 'canopy'):
            with self.subTest(kind=kind):
                self.backend.open(kind)
                wait_for(lambda: len(self.drawing.property('pills')) == len(self.drawing._pills))
                pump(50)
                for record in self.drawing.property('pills'):
                    pill = self.pill(record['key'])
                    self.assertIsNotNone(pill, record['key'])
                    self.assertIn('LengthPill', pill.metaObject().className())
                    rect = self.drawing._rects[next(p.key for p in self.drawing._pills if str(p.key) == record['key'])]
                    self.assertEqual((pill.x(), pill.y(), pill.width(), pill.height()),
                                     (rect.x(), rect.y(), rect.width(), rect.height()))
                    # as tall as the plan's pill of a side: its line, the small type and its margins
                    self.assertAlmostEqual(pill.height(), pill.property('line'), delta=.01)
                    self.assertEqual(pill.property('badge'), record['badge'])

    def test_a_click_on_a_measure_opens_the_plans_field_in_its_place(self):
        for kind, key, unit, typed in (('template', '1', 'm', '24'), ('canopy', '1', 'm', '12'),
                                       ('canopy', 'tilt', '°', '6')):
            with self.subTest(kind=kind, key=key):
                self.backend.open(kind)
                wait_for(lambda key=key: self.pill(key) is not None)
                pump(50)
                pill = self.pill(key)
                box = QRectF(pill.x(), pill.y(), pill.width(), pill.height())
                at = pill.mapToScene(QPointF(pill.width() / 2, pill.height() / 2)).toPoint()
                QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, at)
                field = self.field()
                wait_for(field.isVisible)
                self.assertIn('OverlayField', field.metaObject().className())
                self.assertLessEqual(abs(field.x() - box.x()), 1, (kind, key))
                self.assertLessEqual(abs(field.y() - box.y()), 1, (kind, key))
                self.assertAlmostEqual(field.height(), box.height(), delta=.01)
                self.assertFalse(self.pill(key).isVisible(), 'the field stands in the pill\'s place')
                self.assertEqual(field.property('unit'), unit)
                self.assertEqual(field.property('badge'), '' if key == 'tilt' else key)
                before = dict(self.backend.state)
                self.write(typed)
                QTest.keyClick(self.view, Qt.Key.Key_Return)
                wait_for(lambda field=field: not field.isVisible())
                self.assertNotEqual(before, dict(self.backend.state), 'the measure written is applied')
                self.assertTrue(self.pill(key).isVisible())

    def test_escape_closes_the_field_and_changes_nothing(self):
        self.backend.open('template')
        wait_for(lambda: self.pill('2') is not None)
        pill = self.pill('2')
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         pill.mapToScene(QPointF(pill.width() / 2, pill.height() / 2)).toPoint())
        field = self.field()
        wait_for(field.isVisible)
        before = dict(self.backend.state)
        self.write('99')
        QTest.keyClick(self.view, Qt.Key.Key_Escape)
        wait_for(lambda: not field.isVisible())
        self.assertEqual(before, dict(self.backend.state))


if __name__ == '__main__':
    unittest.main()
