"""Load every dialog page with the shared controls and exercise real Quick events."""

import os
import unittest
from pathlib import Path
from PySide6.QtCore import QObject, Qt
import _setup
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from meridiana.config import Config
from meridiana import i18n
from meridiana.session import ProjectSession
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.dialogs import DialogsBackend

setUpModule = _setup.keep_global_state


class DialogQuickTest(unittest.TestCase):
    def test_every_page_loads_and_cancel_button_has_real_gesture(self):
        self.app = _setup.qt_or_skip()
        i18n.setup("it")
        engine = QQmlApplicationEngine()
        install_controls(
            engine, {"theme": os.getenv("MERIDIANA_DIALOG_THEME", "light")}
        )
        backend = DialogsBackend(
            ProjectSession(), Config(network_tiles=False, network_geocoding=False)
        )
        engine.rootContext().setContextProperty("dialogBackend", backend)
        warnings = []
        engine.warnings.connect(
            lambda rows: warnings.extend(x.toString() for x in rows)
        )
        engine.loadData(b"""import QtQuick
import Meridiana.Dialogs
import Meridiana.Theme
Window { width:1100; height:800; visible:true; color:Theme.colors.window; DialogsPage {anchors.fill:parent;backend:dialogBackend} }""")
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        window.setWidth(int(os.getenv("MERIDIANA_DIALOG_WIDTH","1366")))
        window.setHeight(int(os.getenv("MERIDIANA_DIALOG_HEIGHT","900")))
        for kind in (
            "new",
            "site",
            "registry",
            "canopy",
            "canopy-layout",
            "template",
            "ifc",
            "pvsyst",
            "shortcuts",
            "update",
        ):
            backend.open(kind)
            if kind == 'ifc':
                from _fixtures import capannone
                from meridiana.ifc_import import Plan
                backend._planned_ifc(Plan(buildings=capannone().buildings, taken=['A building']))
                backend.changed.emit()
            QTest.qWait(70)
            self.assertTrue(window.findChild(QObject, "dialog_cancel"))
            if os.getenv("MERIDIANA_DIALOG_PHOTOS"):
                folder = Path("build/quick-foto/pagine")
                folder.mkdir(parents=True, exist_ok=True)
                self.assertTrue(
                    window.grabWindow().save(
                        str(
                            folder
                            / f"dialog-{kind}-{os.getenv('MERIDIANA_DIALOG_THEME', 'light')}-{os.getenv('QT_SCALE_FACTOR', '1')}.png"
                        )
                    )
                )

        def find(name):
            pending = [window.contentItem()]
            while pending:
                item = pending.pop()
                if item.objectName() == name:
                    return item
                pending.extend(item.childItems())
            return None

        def click(name):
            item = find(name)
            self.assertIsNotNone(item, name)
            QTest.mouseClick(
                window,
                Qt.MouseButton.LeftButton,
                pos=item.mapToScene(item.boundingRect().center()).toPoint(),
            )
            QTest.qWait(30)

        def type_text(name, text):
            item = find(name)
            self.assertIsNotNone(item, name)
            item.forceActiveFocus()
            QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
            for char in text:
                QTest.keyClick(window, char)
            QTest.keyClick(window, Qt.Key.Key_Return)
            QTest.qWait(30)

        # R150, R281: real keyboard and pointer input reaches the core.
        created = []
        backend.created.connect(created.append)
        backend.open("new")
        QTest.qWait(50)
        type_text("site_query", "45.52, 9.03")
        type_text("site_latitude", "45.5226; 9.0300")
        click("dialog_accept")
        self.assertEqual(created[0]["site"].lat, 45.5226)
        backend.open("site")
        QTest.qWait(50)
        type_text("site_query", "42.1, 12.5")
        click("dialog_accept")
        self.assertEqual(backend.session.project.site.lat, 42.1)
        backend.session.undo.undo()
        self.assertNotEqual(backend.session.project.site.lat, 42.1)
        placements = []
        backend.placementRequested.connect(
            lambda kind, data: placements.append((kind, data))
        )
        backend.open("canopy")
        QTest.qWait(50)
        type_text("dialog_stalls", "6")
        click("dialog_accept")
        self.assertEqual(placements[0][1].stalls, 6)
        backend.open("update")
        QTest.qWait(50)
        closed = []
        backend.closed.connect(lambda: closed.append(True))
        button = window.findChild(QObject, "dialog_cancel")
        point = button.mapToScene(button.boundingRect().center()).toPoint()
        QTest.mouseClick(
            window, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point
        )
        self.assertTrue(closed)
        self.assertFalse(warnings, "\n".join(warnings))
        window.close()
        engine.deleteLater()
        backend.deleteLater()
        QTest.qWait(30)


if __name__ == "__main__":
    unittest.main()
