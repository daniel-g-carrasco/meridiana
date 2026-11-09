"""R377/R389: the complete inspectors in the actual workbench and C3 groups."""
import tempfile
import unittest
import os
from pathlib import Path

import _setup
from _fixtures import capannone
from PySide6.QtCore import QObject, QPointF, QCoreApplication, QEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana.quick.backend.controls import install_controls
from quick.gestures import pump, wait_for


def visual_items(window):
    """Repeater delegates belong to the visual tree, not QObject's ownership tree."""
    pending = [window.contentItem()]
    while pending:
        item = pending.pop()
        yield item
        pending.extend(item.childItems())


def form_ink(image, origin, width):
    """Count text, including the intermediate tones of the Widgets crossfade.

    Ignore title, card edges and lightly tinted fields: an empty page or empty
    cards must fail, while two half-opacity text layers still constitute content.
    """
    dpr, ink = image.devicePixelRatio(), 0
    background = image.pixelColor(int((origin.x()+18.5)*dpr), int((origin.y()+45.5)*dpr)).lightness()
    for y in range(55, 320, 2):
        for x in range(20, int(width) - 20, 2):
            colour = image.pixelColor(int((origin.x()+x+.5)*dpr), int((origin.y()+y+.5)*dpr))
            ink += abs(background - colour.lightness()) > 40
    return ink


class Fidelity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_c3_header_help_and_fold_leave_no_empty_card(self):
        engine = QQmlApplicationEngine()
        install_controls(engine)
        engine.loadData(b'''import QtQuick
import QtQuick.Window
import Meridiana.Controls as M
Window { visible: true; width: 380; height: 300
 M.Section { objectName: "group"; density: "form"; width: 350; title: "Building"; helpId: "building"
  Rectangle { width: parent.width; height: 100 }
 }
}''')
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        try:
            QTest.qWait(60)
            group = window.findChild(QObject, 'group')
            # R21-F3: the one help mark, the round icon of 20 px (it was a 16 px square with a «?» for text)
            help_button = group.findChild(QObject, 'section-help:building')
            self.assertLessEqual(help_button.property('width'), 20, 'The help mark must fit the C3 title band')
            self.assertEqual(group.property('radius'), 6, 'C3 is a framed control, not an unframed card')
            group.setProperty('collapsed', True)
            QTest.qWait(220)
            self.assertLessEqual(group.property('height'), 32)
        finally:
            window.close()
            from shiboken6 import delete
            delete(engine)

    def test_label_columns_use_widgets_wrapping_at_each_text_size(self):
        from PySide6.QtGui import QFont
        from PySide6.QtWidgets import QLabel
        from meridiana.quick.backend.properties import PropertyField
        for size in (10, 12, 15):
            font = QFont('IBM Plex Sans', size)
            for text in ('Name', 'Potenza del singolo modulo', 'Azimut dei moduli rispetto al nord',
                         'Distanza minima tra i moduli e il bordo del tetto'):
                with self.subTest(size=size, text=text):
                    label = QLabel(text)
                    label.setFont(font)
                    label.setWordWrap(len(text) > 28)
                    hint = PropertyField(dict(label=text), None).labelHint(font)
                    self.assertEqual(hint['width'], label.sizeHint().width())
                    self.assertEqual(hint['height'], label.sizeHint().height())
                    label.deleteLater()

    def test_frame_probe_rejects_blank_cards_and_accepts_crossfaded_text(self):
        from PySide6.QtGui import QColor, QFont, QImage, QPainter
        image = QImage(740, 700, QImage.Format.Format_RGB32)
        image.setDevicePixelRatio(2)
        image.fill(QColor('#fafafa'))
        painter = QPainter(image)
        painter.setPen(QColor('#dddddd'))
        painter.setBrush(QColor('#eeeeee'))
        for y in (60, 100, 140, 180, 220):
            painter.drawRoundedRect(25, y, 320, 28, 6, 6)
        painter.end()
        self.assertEqual(form_ink(image, QPointF(), 370), 0)
        painter = QPainter(image)
        font = QFont('Arial'); font.setPixelSize(14)
        painter.setFont(font)
        painter.setPen(QColor('#999999'))
        for y in (80, 120, 160, 200, 240):
            painter.drawText(35, y, 'Edificio, altezza e proprieta del tetto')
        painter.end()
        self.assertGreater(form_ink(image, QPointF(), 370), 100)

    def test_field_minimum_widths_follow_widgets_range_and_choice_metrics(self):
        from meridiana.config import Config
        from meridiana.ui.theme import Theme
        from meridiana.ui.properties import spin, combo
        from meridiana.quick.backend.properties import PropertyField
        from shiboken6 import delete
        look = Theme(Config(font='plex', theme='light'), app=self.app)
        self.addCleanup(delete, look)
        for lo, hi, unit, decimals in [(0, 1e9, 'kW', 2), (.5, 300, 'm', 2),
                                        (0, 50000, 'V', 0), (-180, 180, '°', 1)]:
            widget = spin(lo, hi, lo, ' ' + unit, decimals)
            widget.ensurePolished()
            data = dict(kind='number', minimum=lo, maximum=hi, unit=unit, decimals=decimals, special='')
            field = PropertyField(data, None)
            self.assertEqual(field.editorMinimum(widget.font()), widget.minimumSizeHint().width(), unit)
            delete(widget)
        widget = combo([(1, 'A choice')], 1)
        widget.ensurePolished()
        self.assertEqual(PropertyField(dict(kind='choice'), None).editorMinimum(widget.font()), widget.minimumSizeHint().width())
        delete(widget)

    def test_complete_pages_follow_selection_and_calculated_checks_in_workbench(self):
        from meridiana import jobs
        from meridiana.quick.app import QuickWindow
        with tempfile.TemporaryDirectory() as directory:
            host = QuickWindow(capannone(), Path(directory), real_views=True)
            try:
                host.window.show()
                # QTest.qWait can retain the GIL while native 3D waits for a
                # Python callback. Use the application's event loop, as the pilot.
                pump(100)
                for name in ('properties-page', 'checks-page', 'project-tree-page'):
                    page = next((item for item in visual_items(host.window) if item.objectName() == name), None)
                    self.assertIsNotNone(page, name + ' must actually load in the window: ' + '\n'.join(host.warnings))
                    self.assertGreater(page.width(), 100)
                    self.assertGreater(page.height(), 100)
                self.assertTrue(hasattr(host, 'parts'), 'The actual window must install the parts registry')
                self.assertIn('properties', host.parts.controllers)
                self.assertIn('checks', host.parts.controllers)
                self.assertIn('project_tree', host.parts.controllers)
                backend = host.parts.controllers['properties']
                self.assertIsNotNone(backend.field('network.voltage_v'))
                host.bridge.session.select('building', 'b1')
                self.assertEqual(backend.kind, 'building')
                self.assertIsNotNone(backend.field('fire.activity'))
                results, keys, _ = jobs.layout_of(host.bridge.session.project)
                self.assertTrue(host.bridge.accept_layout(host.bridge.session.generation, results, keys))
                self.assertEqual(host.bridge.session.results.keys(), results.keys())
                checks = host.parts.controllers['checks']
                self.assertTrue(_setup.wait_until(self.app, lambda: not checks.busy, seconds=15))
                self.assertTrue(checks.items)
                from meridiana.checks import Item
                # A positioned core check reaches the plan as well as the tree.
                checks.show_items([*checks.items, Item('warn', 'roof', 'Roof detail', target=('building', 'b1'))])
                self.assertTrue(host.plan.marks)
                inspectors = host.parts.controllers['inspectors']
                self.assertTrue(inspectors.marks3d)
                self.assertIsNotNone(host.window.findChild(QObject, 'check-scene-marks'))
                from meridiana import mesh, viewaids
                x, y, z = viewaids.anchor(host.bridge.session.project, 'building', 'b1')
                mark = next(m for m in inspectors.marks3d if m['kind'] == 'building' and m['oid'] == 'b1')
                self.assertEqual(mark['point'], list(mesh.to_qt(x, y, z + .6)))
                tree = host.parts.controllers['project_tree']
                self.assertTrue(any(r['markCount'] for r in tree.rows))
                host.window.showPhase('report')
                _setup.wait_until(self.app, lambda: checks.view == 'delivery', seconds=5)     # r21-f6c: the phase changes once the frame is photographed (a frame after the gesture)
                self.assertEqual(checks.view, 'delivery')
                host.window.showPhase('model')
                _setup.wait_until(self.app, lambda: checks.view == 'level', seconds=5)
                self.assertEqual(checks.view, 'level')
                help_service = host.parts.controllers['assistant_help']
                from PySide6.QtTest import QSignalSpy
                requested = QSignalSpy(help_service.changed)
                backend.help('building')
                self.assertEqual(requested.count(), 1)
                layer = host.window.findChild(QObject, 'assistantLayer')
                self.assertTrue(layer.property('opened'))
                layer.dismiss()
                inspectors = host.parts.controllers['inspectors']
                inspectors.highlight_side('building', 'b1', 0)
                overlay = host.window.findChild(QObject, 'property-side-highlight')
                self.assertIsNotNone(overlay)
                self.assertTrue(overlay.property('visible'))
                self.assertEqual(inspectors.sideSegment, [list(p) for p in host.bridge.session.project.building('b1').footprint[:2]])
                plan = host.window.findChild(QObject, 'plan')
                first = overlay.property('b')
                plan.setProperty('zoom', plan.property('zoom') * 1.5)
                self.assertNotEqual(overlay.property('b'), first, 'Highlight must follow the same projection as the plan')
                host.bridge.session.select('site', '')
                self.assertFalse(overlay.property('visible'))
                inspectors.action('site', 'site', '')
                files = host.parts.controllers['filePart']
                self.assertTrue(files.dialogVisible)
                self.assertEqual(host.parts.controllers['dialogs'].kind, 'site')
                files.dismissDialog()
                host.bridge.session.select('subfield', 's1')
                backend.actionRequested.emit('catalog_module', 'subfield', 's1')
                plant = host.parts.controllers['plantActions']
                self.assertEqual(plant.dialog, 'catalog')
                _setup.wait_until(self.app, lambda: host.window.property('phase') == 'plant', seconds=5)   # r21-f6c
                self.assertEqual(host.window.property('phase'), 'plant')
                plant.dismiss()
                for phase in ('production', 'consumption', 'economics', 'report', 'model'):
                    host.window.showPhase(phase)
                    _setup.wait_until(self.app, lambda: host.window.property('phase') == phase, seconds=5)   # r21-f6c
                    pump(40)
                    loaders = [item for item in visual_items(host.window) if item.objectName() == 'propertiesPartLoader']
                    loader = next(item for item in loaders if item.property('phaseId') == phase)
                    self.assertTrue(loader.property('visible'))
                    self.assertIsNotNone(loader.property('item'), phase + ' inspector must load')
                    if phase in ('production', 'consumption', 'economics'):
                        self.assertIs(loader.property('item').property('backend'), host.parts.controllers[phase + 'Editor'])
                self.assertFalse(host.warnings, host.warnings)
            finally:
                host.close()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                self.app.processEvents()

    @unittest.skipUnless(os.environ.get('MERIDIANA_QUICK_NATIVE') == '1', 'Native R377 frames are opt-in')
    def test_r377_actual_workbench_never_shows_an_empty_inspector(self):
        from meridiana.quick.app import QuickWindow, create_app
        from quick.parity.realwindow import FrameRecorder
        create_app()
        with tempfile.TemporaryDirectory() as directory:
            host = QuickWindow(capannone(), Path(directory), real_views=True)
            try:
                host.window.show()
                host.window.resize(1600, 960)
                pump(200)
                panel = host.window.findChild(QObject, 'rightPanel')
                origin = panel.mapToScene(QPointF())
                with FrameRecorder(host.window) as recorder:
                    for kind, oid in [('building', 'b1'), ('subfield', 's1'), ('site', '')]:
                        host.bridge.session.select(kind, oid)
                        next_count = len(recorder.frames) + 10
                        def ready(limit=next_count):
                            host.window.update()
                            return len(recorder.frames) >= limit
                        wait_for(ready, seconds=5)
                recorder.assert_valid()
                if os.environ.get('MERIDIANA_QUICK_CAPTURE'):
                    recorder.save(Path(os.environ['MERIDIANA_QUICK_CAPTURE']))
                self.assertGreaterEqual(len(recorder.frames), 30)
                for n, frame in enumerate(recorder.frames):
                    ink = form_ink(frame.image, origin, panel.width())
                    self.assertGreater(ink, 100, f'Empty inspector in actual frame {n}')
                self.assertFalse(host.warnings, host.warnings)
            finally:
                host.close()
                QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
                self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
