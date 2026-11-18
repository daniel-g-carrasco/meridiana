"""R389/R395: complete, lazy pedigree without the Widgets browser."""
import threading
import time
import unittest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QGuiApplication, QWheelEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from shiboken6 import delete

from meridiana import i18n
from meridiana.energy.pedigree import Quantity, Record, Source, Step, limits
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.properties_pedigree import PedigreeBackend


def sample_records():
    return [Record("Produzione", [Step(
        "energy", "Energia utile", r"E=P t", "Potenza per durata.",
        [Quantity("P", "Potenza", 1.5, "kW", Source("data", "Scheda", "2026"))],
        Quantity("E", "Energia", 3.0, "kWh"), "Modello di prova")])]


class PedigreeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["pedigree-test"])

    def wait(self, condition):
        deadline = time.monotonic() + 10
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(condition())

    def test_backend_imports_without_widgets(self):
        result = subprocess.run([sys.executable, "-c", "import sys; "
            "from meridiana.quick.backend.properties_pedigree import PedigreeBackend; "
            "assert 'PySide6.QtWidgets' not in sys.modules"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_formula_keeps_error_for_readable_fallback(self):
        backend = PedigreeBackend()
        completed = []
        backend.formulaReady.connect(lambda key, value: completed.append(value))
        backend.requestFormula(r"\notacommand", 14, "#222222", "IBM Plex Sans", 1)
        self.wait(lambda: bool(completed))
        self.assertEqual(completed[0]["source"], "")
        self.assertIn("notacommand", completed[0]["error"])

    def test_records_keep_every_quantity_source_reference_and_limit(self):
        backend = PedigreeBackend()
        backend.show_records(sample_records())
        quantities = [r for r in backend.rows if r["kind"] == "quantity"]
        self.assertEqual(len(quantities), 2)
        self.assertEqual(quantities[0]["sourceLabel"], "Scheda")
        self.assertEqual(quantities[0]["sourceRef"], "2026")
        self.assertEqual(quantities[0]["value"], "1.50 kW")
        self.assertTrue(quantities[1]["result"])
        self.assertEqual([r["text"] for r in backend.rows if r["kind"] == "reference"],
                         ["Reference: Modello di prova"])
        self.assertEqual([r["text"] for r in backend.rows if r["kind"] == "limit"], limits())
        backend.show_records([])
        self.assertEqual(backend.rows, [])

    def test_formula_is_requested_lazily_on_worker_and_cached(self):
        backend = PedigreeBackend()
        calls, completed = [], []
        main = threading.get_ident()

        def render(*args):
            calls.append(threading.get_ident())
            return {"source": "data:image/png;base64,abc", "width": 50, "height": 20, "error": ""}

        backend.formulaReady.connect(lambda key, result: completed.append((key, result)))
        with patch("meridiana.quick.backend.properties_pedigree.render_formula", render):
            backend.show_records(sample_records())
            self.assertEqual(calls, [])
            first = backend.requestFormula("E=P t", 14, "#222222", "IBM Plex Sans", 1)
            same = backend.requestFormula("E=P t", 14, "#222222", "IBM Plex Sans", 1)
            self.assertEqual(first["key"], same["key"])
            self.wait(lambda: len(completed) == 1)
            cached = backend.requestFormula("E=P t", 14, "#222222", "IBM Plex Sans", 1)
            self.assertEqual(cached["source"], completed[0][1]["source"])
            self.assertEqual(len(calls), 1)
            self.assertNotEqual(calls[0], main)

    def test_page_native_theme_narrow_layout_and_hidden_formulas(self):
        """R389/R395: virtual rows paint all information and lazy formula pixels."""
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        theme = install_controls(engine)
        backend = PedigreeBackend()
        original_language = i18n.language()
        i18n.setup("it")
        self.addCleanup(i18n.setup, original_language)
        backend.show_records(sample_records())
        path = Path("src/meridiana/quick/qml/Meridiana/Properties/PedigreePage.qml").resolve()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
        root = component.createWithInitialProperties({"backend": backend})
        self.assertIsNotNone(root, "\n".join(e.toString() for e in component.errors()))
        window = QQuickWindow()
        window.setFlags(Qt.WindowType.FramelessWindowHint)
        root.setParentItem(window.contentItem())
        root.setVisible(False)
        root.setWidth(1366)
        root.setHeight(900)
        window.resize(1366, 900)
        window.show()
        QTest.qWait(100)
        self.assertEqual(backend._jobs, {})
        self.assertEqual(backend._cache, {})
        root.setVisible(True)
        self.wait(lambda: len(backend._cache) == 3)
        self.assertTrue(all(r["source"] and not r["error"] for r in backend._cache.values()), backend._cache)
        folder = Path("build/quick-foto/proprieta")
        folder.mkdir(parents=True, exist_ok=True)
        try:
            for mode in ("light", "dark"):
                theme.configure({"theme": mode, "textSize": "large" if mode == "dark" else "medium"})
                for width, height in ((1366, 900), (1600, 960), (1920, 1080), (390, 750)):
                    root.setWidth(width)
                    root.setHeight(height)
                    window.resize(width, height)
                    self.wait(lambda: not backend._jobs)
                    QTest.qWait(120)
                    self.assertEqual((window.width(), window.height()), (width, height))
                    capture = window.grabWindow()
                    self.assertFalse(capture.isNull())
                    self.assertTrue(capture.save(str(folder / f"pedigree-{mode}-{width}-x{window.devicePixelRatio():g}.png")))
            # Real wheel events scroll the long list, rendering only entering formulas.
            backend.show_records([Record("Passaggi", [Step(str(i), f"Passaggio {i}",
                f"E={i} P", "Spiegazione della formula") for i in range(80)])])
            QTest.qWait(100)
            self.wait(lambda: not backend._jobs)
            previous = len(backend._cache)
            self.assertLess(previous, 30)
            view = root.findChild(type(root), "pedigreeList")
            self.assertIsNotNone(view)
            before_y = view.property("contentY")
            for _ in range(8):
                event = QWheelEvent(QPointF(150, 400), QPointF(150, 400), QPoint(), QPoint(0, -480),
                                    Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                                    Qt.ScrollPhase.NoScrollPhase, False)
                self.app.sendEvent(window, event)
                QTest.qWait(30)
            self.wait(lambda: len(backend._cache) > previous)
            self.wait(lambda: not backend._jobs)
            self.assertGreater(view.property("contentY"), before_y)
            self.assertGreater(len(backend._cache), previous)
            self.assertLess(len(backend._cache), 80)
            self.assertEqual(warnings, [])
        finally:
            window.hide()
            delete(root)
            delete(window)
            delete(engine)


if __name__ == "__main__":
    unittest.main()
