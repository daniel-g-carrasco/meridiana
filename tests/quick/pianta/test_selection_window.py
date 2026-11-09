"""R344 live selection pixels and measured 20,000-module preview without Python pointer traffic."""

import json
import os
import statistics
import time
import unittest
from pathlib import Path

os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

from PySide6.QtCore import QObject, QPoint, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QSignalSpy, QTest

from meridiana import model
from meridiana.quick.backend.plan import PlanController, qml_objects


class SelectionWindow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait(self, condition):
        end = time.monotonic() + 5
        while not condition() and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.001)
        self.assertTrue(condition())

    def test_live_twenty_thousand_modules_shift_pixels_and_local_frame_times(self):
        print('selection measurement pid', os.getpid(), flush=True)
        controller = PlanController(model.Project(), manage_layout=False)
        controller.setPhase('plant')
        rows = [dict(kind='module', oid='s1', key=str(i), rid=str(i//100),
                     points=[[i%100*3, i//100*2.5], [i%100*3+2, i//100*2.5],
                             [i%100*3+2, i//100*2.5+2], [i%100*3, i//100*2.5+2]]) for i in range(20000)]
        controller._modules = qml_objects(rows)
        engine = QQmlApplicationEngine()
        errors = []
        engine.warnings.connect(lambda values: errors.extend(x.toString() for x in values))
        controller.install(engine)
        engine.rootContext().setContextProperty('planBackend', controller)
        path = Path(__file__).resolve().parents[3] / 'src/meridiana/quick/qml/Meridiana/Plan/PlanWindow.qml'
        engine.load(QUrl.fromLocalFile(str(path)))
        self.assertTrue(engine.rootObjects(), errors)
        window = engine.rootObjects()[0]
        window.resize(1000, 740)
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        plan = window.findChild(QObject, 'plan')
        overlay = window.findChild(QObject, 'selectionOverlay')
        try:
            QTest.qWait(100)
            plan.setProperty('zoom', 1)
            plan.setProperty('panX', 100)
            plan.setProperty('panY', 80)
            controller.calls.clear()
            QTest.mouseMove(window, QPoint(101, 81))
            self.wait(lambda: overlay.property('hovered') is not None)
            QTest.mousePress(window, Qt.LeftButton, Qt.NoModifier, QPoint(80, 60))
            times, queries, paints, presented = [], [], [], []
            swaps = QSignalSpy(window.frameSwapped)
            for i in range(20):
                before = overlay.property('queryCount')
                before_swap = swaps.count()
                started = time.perf_counter()
                QTest.mouseMove(window, QPoint(440 + i % 3, 650 + i % 3))
                self.wait(lambda before=before: overlay.property('queryCount') > before)
                self.wait(lambda before_swap=before_swap: swaps.count() > before_swap)
                presented.append((time.perf_counter() - started) * 1000)
                image = window.grabWindow()
                times.append((time.perf_counter() - started) * 1000)
                queries.append(overlay.property('queryMilliseconds'))
                paints.append(overlay.property('paintMilliseconds'))
            self.assertEqual(overlay.property('candidateCount'), 20000)
            self.assertEqual(overlay.property('action'), 'add')
            self.assertEqual(controller.calls['pointer'], 0)
            self.assertEqual(controller.calls['sweep'], 0)
            folder = Path('build/quick-foto/pianta')
            folder.mkdir(parents=True, exist_ok=True)
            dpr = image.devicePixelRatio()
            image.save(str(folder / f'selection-add-20000-{dpr:g}x.png'))
            edge_times, edge_presented = [], []
            for i in range(10):
                before = overlay.property('queryCount')
                before_swap = swaps.count()
                started = time.perf_counter()
                QTest.mouseMove(window, QPoint(300 + i * 3, 650))
                self.wait(lambda before=before: overlay.property('queryCount') > before)
                self.wait(lambda before_swap=before_swap: swaps.count() > before_swap)
                edge_presented.append((time.perf_counter() - started) * 1000)
                window.grabWindow()
                edge_times.append((time.perf_counter() - started) * 1000)
            QTest.mouseMove(window, QPoint(440, 650))
            self.wait(lambda: overlay.property('candidateCount') == 20000)
            patched = window.grabWindow()
            # Patches must preserve the complete earlier mask, including cells outside the last dirty strip.
            for x, y in ((101, 81), (220, 330), (390, 570)):
                self.assertEqual(image.pixelColor(int(x*dpr), int(y*dpr)), patched.pixelColor(int(x*dpr), int(y*dpr)))
            before = overlay.property('queryCount')
            QTest.keyPress(window, Qt.Key_Control)   # R529: Ctrl takes away
            self.wait(lambda: overlay.property('queryCount') > before)
            self.assertEqual(overlay.property('action'), 'remove')
            removed = window.grabWindow()
            removed.save(str(folder / f'selection-remove-20000-{dpr:g}x.png'))
            self.assertNotEqual(image.pixelColor(int(101*dpr), int(81*dpr)),
                                removed.pixelColor(int(101*dpr), int(81*dpr)))
            QTest.keyRelease(window, Qt.Key_Control)
            QTest.mouseRelease(window, Qt.LeftButton, Qt.NoModifier, QPoint(440, 650))
            self.wait(lambda: overlay.property('candidateCount') == 0)
            self.assertEqual(controller.calls['sweep'], 1)
            report = dict(modules=20000, dpr=dpr, frames=20, renderer='Canvas mask + GPU outline',
                          event_grab_median_ms=statistics.median(times), event_grab_max_ms=max(times),
                          query_median_ms=statistics.median(queries), query_max_ms=max(queries),
                          paint_median_ms=statistics.median(paints), paint_max_ms=max(paints),
                          changing_edge_median_ms=statistics.median(edge_times), changing_edge_max_ms=max(edge_times),
                          frame_swapped_median_ms=statistics.median(presented), frame_swapped_max_ms=max(presented),
                          edge_swapped_median_ms=statistics.median(edge_presented), edge_swapped_max_ms=max(edge_presented),
                          python_pointer_calls=controller.calls['pointer'])
            (folder / f'selection-20000-{dpr:g}x.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report))
            self.assertFalse(errors, errors)
        finally:
            window.close()
            controller.close()
            engine.deleteLater()
            self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
