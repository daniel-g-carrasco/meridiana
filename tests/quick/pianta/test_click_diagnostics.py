"""Rejected clicks leave one private-data-free diagnostic; accepted clicks stay quiet."""
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QPointF, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow

from meridiana.app.platform import log
from meridiana.app.view.measure_tool import MeasureTool, Probe
from quick.gestures import click, pump

setUpModule = _setup.keep_global_state


class ClickDiagnostics(unittest.TestCase):
    def setUp(self):
        self.old = log.file()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(log.setup, self.old)
        self.path = Path(self.tmp.name) / "diagnostics.log"
        log.setup(self.path)

    def lines(self):
        return self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []

    def test_rejected_measure_points_are_logged_once(self):
        tool = MeasureTool()
        for probe, reason in [(None, "no-probe"), (Probe((float("nan"), 0, 0)), "non-finite"),
                              (Probe((float("inf"), 0, 0)), "non-finite")]:
            before = len(self.lines())
            tool.click(probe)
            self.assertEqual(len(self.lines()), before + 1)
            self.assertIn(reason, self.lines()[-1])
        tool.click(Probe((12345, 67890, 0)))
        before = len(self.lines())
        tool.click(Probe((12345, 67890, 0)))
        self.assertEqual(len(self.lines()), before + 1)
        self.assertIn("same-point", self.lines()[-1])
        self.assertNotIn("12345", " ".join(self.lines()))
        self.assertEqual(len(tool.points), 1)

    def test_height_same_point_has_one_diagnostic(self):
        tool = MeasureTool()
        tool.mode = "height"
        tool.click(Probe((0, 0, 0)))
        tool.click(Probe((0, 0, 0)))
        self.assertEqual(len(self.lines()), 1)
        self.assertIn("same-point", self.lines()[0])
        self.assertEqual(len(tool.points), 1)

    def test_accepted_clicks_and_moves_are_quiet(self):
        tool = MeasureTool()
        tool.click(Probe((0, 0, 0)))
        tool.move(None)
        tool.click(Probe((10, 4, 0)))
        self.assertEqual(len(tool.points), 2)
        self.assertEqual(self.lines(), [])

    def test_overlay_reports_without_changing_delivery(self):
        from meridiana.gui.backend.click_diagnostics import ClickDiagnostics as Observer
        app = _setup.qt_or_skip()
        engine = QQmlApplicationEngine()
        engine.loadData(b'''import QtQuick
Window { width: 300; height: 200
    Item { objectName: "plan"; anchors.fill: parent
        MouseArea { objectName: "planMouse"; anchors.fill: parent }
        MouseArea { objectName: "private-client-name"; x: 100; y: 20; width: 80; height: 80
            property int clicks: 0
            onClicked: clicks++
        }
    }
}''', QUrl("diagnostic.qml"))
        window = engine.rootObjects()[0]
        self.assertIsInstance(window, QQuickWindow)
        active = ["measure"]
        observer = Observer(window, lambda: active[0])
        window.show()
        pump(30)
        click(app, window, QPointF(130, 50))
        pump(20)
        from PySide6.QtCore import QObject
        overlay = window.findChild(QObject, "private-client-name")
        self.assertEqual(overlay.property("clicks"), 1)
        self.assertEqual(len(self.lines()), 1)
        self.assertIn("other-item", self.lines()[0])
        self.assertNotIn("private-client-name", self.lines()[0])
        click(app, window, QPointF(20, 150))
        pump(20)
        self.assertEqual(len(self.lines()), 1)
        for tool in ("building", "pitch", "exclusion", "square", "draw_string"):
            active[0] = tool
            before = len(self.lines())
            click(app, window, QPointF(130, 50))
            self.assertEqual(len(self.lines()), before + 1)
            self.assertIn("tool=" + tool, self.lines()[-1])
        active[0] = "select"
        before = len(self.lines())
        click(app, window, QPointF(130, 50))
        self.assertEqual(len(self.lines()), before)
        window.removeEventFilter(observer)
        window.close()
        engine.deleteLater()
        app.processEvents()
