"""The plan as a DXF in the Qt Quick interface (R513): the options' dialog loads and gives the frame and the parts
chosen, FileActions writes the plan in the pool's job with its words, the shell's export takes the third filter."""
import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import _setup
from PySide6.QtCore import QCoreApplication, QObject
from PySide6.QtQml import QQmlApplicationEngine

from meridiana import dxf_export, i18n
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.files_actions import FileActions
from meridiana.session import ProjectSession


def item(root, name):
    """The item named `name` under `root`, through the visual tree (a popup's content lives on the overlay)."""
    if root.objectName() == name:
        return root
    for child in root.childItems():
        found = item(child, name)
        if found is not None:
            return found
    return None


class DxfQuickTest(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        if not dxf_export.available():
            raise unittest.SkipTest("ezdxf is not installed")
        from _fixtures import capannone
        self.owner = QObject()
        self.owner.session = ProjectSession(capannone())
        self.owner.root = SimpleNamespace(property=lambda _name: 'report')
        self.actions = FileActions(self.owner)
        self.addCleanup(self.actions.close)

    def test_the_options_dialog_gives_the_frame_and_the_parts(self):
        i18n.setup("it")
        engine = QQmlApplicationEngine()
        install_controls(engine, {"theme": os.getenv("MERIDIANA_DIALOG_THEME", "light")})
        engine.rootContext().setContextProperty("filesActions", self.actions)
        warnings = []
        engine.warnings.connect(lambda rows: warnings.extend(x.toString() for x in rows))
        engine.loadData(b"""import QtQuick
import QtQuick.Controls
import Meridiana.Dialogs
ApplicationWindow { width: 900; height: 700; visible: true
    property var got: []
    DxfOptions { id: options; objectName: "options"; onChosen: (url, frame, parts) => got = [url, frame, parts] }
    function ask() { options.show("file:///x.dxf", filesActions.dxfFrames(), filesActions.dxfParts, filesActions.labels) }
}""")
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        window.ask()
        QCoreApplication.processEvents()
        options = window.findChild(QObject, "options")
        self.assertTrue(options.property("opened") or options.property("visible"))
        self.assertEqual(options.property("title"), "Esporta la pianta in DXF")
        imported = item(window.contentItem(), "dxfFrame-imported")
        self.assertFalse(imported.property("enabled"))               # the buildings were drawn here
        item(window.contentItem(), "dxfFrame-utm").setProperty("checked", True)
        item(window.contentItem(), "dxfFrame-utm").toggled.emit()
        item(window.contentItem(), "dxfPart-dimensions").setProperty("checked", False)
        options.accept()
        QCoreApplication.processEvents()
        url, frame, parts = window.property("got").toVariant() if hasattr(window.property("got"), "toVariant") \
            else window.property("got")
        self.assertEqual((url, frame), ("file:///x.dxf", "utm"))
        self.assertEqual(set(parts), set(dxf_export.PARTS) - {"dimensions"})
        self.assertFalse([w for w in warnings if "DxfOptions" in w], warnings)
        engine.deleteLater()

    def test_file_actions_write_the_plan_in_a_job(self):
        labels = self.actions.labels
        self.assertIn("dxfPlan", labels)
        self.assertEqual([f["key"] for f in self.actions.dxfFrames()], list(dxf_export.FRAMES))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "pianta"
            self.actions.exportDxf(str(target), "local", ["modules", "strings"])
            self.assertTrue(self.actions.busy)
            end = time.monotonic() + 60
            while self.actions.busy and time.monotonic() < end:
                QCoreApplication.processEvents()
                time.sleep(0.01)
            self.assertFalse(self.actions.busy)
            written = target.with_suffix(".dxf")
            self.assertTrue(written.exists(), self.actions.status)
            self.assertIn("DXF", self.actions.status)
            self.assertEqual(dxf_export.audit(written), [])


if __name__ == "__main__":
    unittest.main()
