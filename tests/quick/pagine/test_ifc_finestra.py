"""The BIM import window of Quick: the project's site stays where it is unless the designer chooses otherwise, a place the file
cannot back is not offered, the whole import is one undo, a Revit file says what it is; and the common dialog has one margin
all round and the height of its content (R403). Models built by the tests, no client's data."""

import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import _setup
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest

from meridiana import i18n, model, rvt_read
from meridiana.config import Config
from meridiana.quick.backend.controls import install_controls
from meridiana.quick.backend.dialogs import DialogsBackend
from meridiana.session import ProjectSession

setUpModule = _setup.keep_global_state
HERE = {"lat": 46.0, "lon": 13.0, "address": "46.00000000, 13.00000000"}


def found(name="Default", conversion=None):
    """What the reader gives of a square building 20 x 10, its site 500 km from the project."""
    ring = [[100.0, 100.0], [120.0, 100.0], [120.0, 110.0], [100.0, 110.0]]
    return {"schema": "IFC2X3", "application": "Prova", "unit_m": 1.0, "true_north": 0.0, "map": conversion,
            "site": {"lat": 44.5, "lon": 7.0, "elevation": 0.0, "name": name, "placement": [0.0, 0.0, 0.0]},
            "sites": 1, "address": "", "obstacles": [], "counts": {}, "supports": [], "times": {"total": 1.0},
            "buildings": [{"name": "Palazzetto", "ifc": "x", "ground": 0.0, "source": "roof", "footprint": ring,
                           "pitches": [{"ring": ring, "normal": [0.0, 0.0, 1.0], "point": [110.0, 105.0, 8.0],
                                        "area": 200.0, "holes": 0, "owners": [1]}]}]}


class Backend(unittest.TestCase):
    def setUp(self):
        self.app = _setup.qt_or_skip()
        session = ProjectSession(model.Project(site=model.Site(**HERE)))
        self.backend = DialogsBackend(session, Config(network_tiles=False, network_geocoding=False))
        self.addCleanup(self.backend.deleteLater)
        self.backend.open("ifc")
        self.backend._state["fileName"] = "palazzetto.ifc"

    def read(self, data):
        self.backend._ifc_done(self.backend._generation, data)
        limit = 300
        while self.backend.busy and limit:
            QTest.qWait(10)
            limit -= 1

    def test_a_template_site_is_not_offered_and_the_project_stays_where_it_is(self):
        self.read(found())
        self.assertEqual(self.backend.state["how"], "hand")         # R454: by hand on the plan, by default
        self.assertEqual([o["value"] for f in self.backend.fields for o in f["options"]], ["hand", "origin"])
        self.assertIn("44", self.backend.state["ifcPlaceNote"])
        self.choose("origin")
        self.assertTrue(self.backend.state["valid"], self.backend.status)
        placed = []
        self.backend.modelPlaced.connect(lambda: placed.append(True))
        self.assertTrue(self.backend.accept())
        p = self.backend.session.project
        self.assertEqual((p.site.lat, p.site.lon, p.site.address), (HERE["lat"], HERE["lon"], HERE["address"]))
        xs = [x for b in p.buildings for x, _y in b.footprint]
        ys = [y for b in p.buildings for _x, y in b.footprint]
        self.assertAlmostEqual(min(xs) + max(xs), 0.0, places=2)
        self.assertAlmostEqual(min(ys) + max(ys), 0.0, places=2)
        self.assertEqual(placed, [True])
        self.assertEqual(self.backend.session.selection, ("building", p.buildings[0].id))

    def test_a_named_site_is_a_proposal_with_its_distance_and_the_undo_brings_the_site_back(self):
        self.read(found("Cantiere Asti"))
        self.assertEqual(self.backend.state["how"], "hand")
        options = {o["value"]: o["label"] for f in self.backend.fields for o in f["options"]}
        self.assertEqual(sorted(options), ["file", "hand", "origin", "site"])
        self.assertIn("km", options["site"])
        self.choose("site")
        self.assertTrue(self.backend.accept())
        session = self.backend.session
        self.assertAlmostEqual(session.project.site.lat, 44.5)
        session.undo.undo()
        self.assertEqual((session.project.site.lat, session.project.site.lon), (HERE["lat"], HERE["lon"]))
        self.assertEqual(session.project.buildings, [])

    def choose(self, how):
        self.backend.setValue("how", how)
        limit = 300
        while (self.backend.busy or not self.backend.state["valid"]) and limit:
            QTest.qWait(10)
            limit -= 1

    def test_by_hand_the_plan_places_it_and_nothing_is_added_yet(self):
        """R454: «Add» hands the model to the plan's Place mode (following the pointer); with buildings already drawn the
        middle of the plan and the file's place go there too, standing where they say until Enter."""
        asked = []
        self.backend.placementRequested.connect(lambda kind, data: asked.append((kind, data)))
        self.read(found("Cantiere Asti"))
        self.assertTrue(self.backend.state["valid"], self.backend.status)
        self.assertTrue(self.backend.accept())
        [(kind, data)] = asked
        self.assertEqual((kind, data["follow"], data["name"]), ("ifc", True, "palazzetto"))
        self.assertEqual(data["place"].site_name, "Cantiere Asti")
        self.assertEqual(self.backend.session.project.buildings, [])
        self.backend.session.project.buildings.append(model.Building(id="b1", name="Disegnato",
                                                                     footprint=[[0, 0], [9, 0], [9, 9], [0, 9]]))
        self.backend.open("ifc")
        self.backend._state["fileName"] = "palazzetto.ifc"
        self.read(found("Cantiere Asti"))
        self.choose("origin")
        self.assertTrue(self.backend.accept())
        self.assertEqual((asked[-1][0], asked[-1][1]["follow"]), ("ifc", False))
        self.assertEqual(len(self.backend.session.project.buildings), 1)

    def test_what_the_model_is_made_of_is_said(self):
        self.read(found())
        self.assertTrue(self.backend.state["ifcFacts"])
        titles = [row["title"] for row in self.backend.state["ifcLists"]]
        self.assertTrue(titles)

    def test_a_revit_file_says_its_version_and_what_to_do(self):
        info = {"size": 12_000_000, "streams": 12, "title": "", "preview": b"\x89PNG\r\n\x1a\nx", "format": "2026", "build": "",
                "central": ""}
        with mock.patch.object(rvt_read, "read", return_value=info), \
                mock.patch.object(rvt_read, "installed_revit", return_value=[2023]):
            self.backend.readFile("C:/prova/modello.rvt")
        got = self.backend.state["rvtInfo"]
        self.assertIn("2026", got["headline"])
        self.assertTrue(any("2023" in line and "2026" in line for line in got["lines"]))
        self.assertTrue(got["preview"].startswith("data:image/png;base64,"))
        self.assertFalse(self.backend.state["valid"])
        with mock.patch.object(rvt_read, "read", return_value={**info, "format": "2021"}), \
                mock.patch.object(rvt_read, "installed_revit", return_value=[2023]):
            self.backend.readFile("C:/prova/modello.rvt")
        self.assertTrue(any("Revit 2023" in line for line in self.backend.state["rvtInfo"]["lines"]))

    def test_what_is_not_a_revit_file_is_said(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "finto.rvt"
            path.write_bytes(b"not at all" * 100)
            self.backend.readFile(str(path))
        self.assertIn("Revit", self.backend.status)


class RevitFile(unittest.TestCase):
    """A compound file made by the test, with the streams a Revit file has."""

    @staticmethod
    def compound(streams: dict) -> bytes:
        sector = 512
        names = list(streams)
        body = bytearray()
        starts = {}
        sectors_of = {}
        for name in names:
            data = streams[name].ljust(4096, b"\0")     # above the cutoff: in the normal sectors
            starts[name] = len(body) // sector
            sectors_of[name] = (len(data) + sector - 1) // sector
            body += data + b"\0" * (-len(data) % sector)
        directory_start = len(body) // sector
        entries = bytearray()

        def entry(name, kind, start, size):
            raw = name.encode("utf-16-le") + b"\0\0"
            return raw.ljust(64, b"\0") + struct.pack("<HBB", len(raw), kind, 1) + b"\xff" * 12 + b"\0" * 36 + \
                struct.pack("<IQ", start, size)
        entries += entry("Root Entry", 5, 0xFFFFFFFE, 0)
        for name in names:
            entries += entry(name, 2, starts[name], len(streams[name].ljust(4096, b"\0")))
        entries += b"\0" * (-len(entries) % sector)
        body += entries
        count = len(body) // sector
        fat_start = count
        fat = []
        for name in names:
            for k in range(sectors_of[name]):
                fat.append(starts[name] + k + 1 if k + 1 < sectors_of[name] else 0xFFFFFFFE)
        for k in range(directory_start, count):
            fat.append(k + 1 if k + 1 < count else 0xFFFFFFFE)
        fat.append(0xFFFFFFFD)
        raw_fat = struct.pack(f"<{len(fat)}I", *fat)
        raw_fat += b"\xff" * (-len(raw_fat) % sector)
        head = bytearray(512)
        head[:8] = rvt_read.SIGNATURE
        struct.pack_into("<H", head, 30, 9)
        struct.pack_into("<H", head, 32, 6)
        struct.pack_into("<I", head, 44, 1)
        struct.pack_into("<I", head, 48, directory_start)
        struct.pack_into("<I", head, 56, 4096)
        struct.pack_into("<II", head, 60, 0xFFFFFFFE, 0)
        struct.pack_into("<II", head, 68, 0xFFFFFFFE, 0)
        difat = [fat_start] + [0xFFFFFFFF] * 108
        struct.pack_into("<109I", head, 76, *difat)
        return bytes(head) + bytes(body) + raw_fat

    def read(self, streams):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "m.rvt"
            path.write_bytes(self.compound(streams))
            return rvt_read.read(path)

    def test_the_version_of_a_recent_file_as_a_length_prefixed_string(self):
        info = b"\x0e\0\0\0\0\0\0\0\0\0\0\0\0\0\x04\0\0\0" + "2026".encode("utf-16-le") + b"\x12\0\0\0" + \
            "20260731_1210(x64)".encode("utf-16-le")
        got = self.read({"BasicFileInfo": info, "RevitPreview4.0": b"header" + rvt_read.PNG + b"pixels"})
        self.assertEqual(got["format"], "2026")
        self.assertEqual(got["build"], "20260731_1210(x64)")
        self.assertTrue(got["preview"].startswith(rvt_read.PNG))

    def test_the_version_of_an_old_file_as_a_line_of_text(self):
        got = self.read({"BasicFileInfo": "\r\nFormat: 2018\r\nBuild: 20180216_1515(x64)\r\n".encode("utf-16-le")})
        self.assertEqual(got["format"], "2018")
        self.assertEqual(got["preview"], b"")

    def test_an_ole_file_that_is_not_revit_and_a_file_that_is_not_ole(self):
        with self.assertRaises(rvt_read.RvtError):
            self.read({"WordDocument": b"nothing here"})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "m.rvt"
            path.write_bytes(b"no")
            with self.assertRaises(rvt_read.RvtError):
                rvt_read.read(path)

    def test_which_revit_opens_which_file(self):
        self.assertEqual(rvt_read.can_open("2021", [2023, 2025]), 2023)
        self.assertEqual(rvt_read.can_open("2023", [2023]), 2023)
        self.assertIsNone(rvt_read.can_open("2026", [2023]))
        self.assertIsNone(rvt_read.can_open("", [2023]))

    def test_the_folders_of_the_installed_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "Revit 2023").mkdir()
            (Path(folder) / "Revit 2023" / "Revit.exe").write_bytes(b"")
            (Path(folder) / "Revit 2024").mkdir()              # a folder left by an uninstaller, without the program
            (Path(folder) / "Navisworks Manage 2023").mkdir()
            self.assertEqual(rvt_read.installed_revit(folder), [2023])


class CommonDialog(unittest.TestCase):
    """R403: one margin all round, the content's height, no empty band in place of absent buttons."""

    def load(self, body: bytes):
        self.app = _setup.qt_or_skip()
        i18n.setup("it")
        engine = self.engine = QQmlApplicationEngine()
        self.addCleanup(engine.deleteLater)
        install_controls(engine, {"theme": "light"})
        engine.loadData(b"""import QtQuick
import Meridiana.Controls as M
Window { width: 1000; height: 800; visible: true
    """ + body + b" }\n")
        self.assertTrue(engine.rootObjects())
        self.window = engine.rootObjects()[0]
        for item in self.window.findChildren(QObject):
            if item.objectName() == "probe":
                self.probe = item
                return item
        self.fail("no dialog")

    def open(self, dialog):
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(dialog, "open", Qt.ConnectionType.DirectConnection)
        QTest.qWait(50)

    def test_the_height_is_the_contents_with_one_margin_and_a_title_and_buttons(self):
        d = self.load(b"""M.Dialog { objectName: "probe"; title: "Titolo"; acceptText: "OK"; rejectText: "No"; anchors.centerIn: parent
            Rectangle { implicitWidth: 100; implicitHeight: 120 } }""")
        self.open(d)
        self.assertEqual(d.property("height"), d.property("implicitHeight"))
        self.assertEqual(d.property("contentItem").height(), 120)
        self.assertEqual(d.property("leftPadding"), d.property("rightPadding"))
        self.assertLess(d.property("height") - 120, 120, "title, buttons and margins take less than the content here")

    def test_no_buttons_no_band_in_their_place(self):
        d = self.load(b"""M.Dialog { objectName: "probe"; anchors.centerIn: parent
            Rectangle { implicitWidth: 100; implicitHeight: 40 } }""")
        self.open(d)
        self.assertEqual(d.property("topPadding"), d.property("bottomPadding"))
        self.assertEqual(d.property("height"), 40 + d.property("topPadding") + d.property("bottomPadding"))

    def test_buttons_show_when_it_is_open(self):
        d = self.load(b"""M.Dialog { objectName: "probe"; acceptText: "OK"; anchors.centerIn: parent
            Rectangle { implicitWidth: 100; implicitHeight: 40 } }""")
        self.open(d)
        self.assertTrue(d.property("hasButtons"))
        self.assertGreater(d.property("height"), 40 + d.property("topPadding") + d.property("bottomPadding") + 20)


if __name__ == "__main__":
    unittest.main()

