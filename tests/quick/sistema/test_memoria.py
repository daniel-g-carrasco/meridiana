"""R548: the memory's three choices (Risparmia, Automatico, Usa tutto), what may be prepared ahead, and the two things
prepared ahead outside the report (test_report.py has its preview): the IFC model's true geometry read in a thread,
and the reading of an IFC file kept for the session."""
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import _setup
from meridiana import resources

GIB = resources.GIB
setUpModule = _setup.keep_global_state         # configure() writes MERIDIANA_MEMORY_MODE for the processes it starts


class Modes(unittest.TestCase):
    def tearDown(self):
        resources.configure("auto")

    def test_the_three_choices_and_what_each_may_spend(self):
        machine = (32 * GIB, 20 * GIB)
        with mock.patch.object(resources, "system_memory", lambda: machine), \
                mock.patch.object(resources, "memory_is_short", lambda: False):
            self.assertEqual(resources.Budget(mode="auto").bytes(), 18 * GIB)
            self.assertEqual(resources.Budget(mode="all").bytes(), 19 * GIB)
            self.assertEqual(resources.Budget(mode="save").bytes(), int(32 * GIB * resources.SAVE_SHARE))
            self.assertEqual(resources.Budget(mode="nonsense").mode, "auto")
            with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": ""}), \
                    mock.patch.object(resources, "on_battery", lambda: False):
                for mode, ahead in (("save", False), ("auto", True), ("all", True)):
                    resources.configure(mode)
                    self.assertEqual((resources.mode(), resources.preload()), (mode, ahead))
                    self.assertEqual(os.environ["MERIDIANA_MEMORY_MODE"], mode)   # what the year's process takes
                resources.configure("all")
                self.assertGreater(resources.cache_limit("shading"), 0.3 * 19 * GIB)
                resources.configure("auto")
                self.assertEqual(resources.cache_limit("shading"), int(18 * GIB * 0.25))
                with mock.patch.object(resources, "on_battery", lambda: True):
                    self.assertFalse(resources.preload())      # on battery only «Usa tutto» prepares ahead
                    resources.configure("all")
                    self.assertTrue(resources.preload())
        # a PC with little free: everything down to a quarter, nothing ahead
        with mock.patch.object(resources, "system_memory", lambda: (8 * GIB, 5 * GIB)), \
                mock.patch.object(resources, "memory_is_short", lambda: True), \
                mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": ""}):
            resources.configure("auto")
            self.assertEqual(resources.budget().bytes(), 3 * GIB // 4)
            self.assertFalse(resources.preload())

    def test_what_is_in_use_is_read(self):
        use = resources.in_use()
        self.assertGreater(use["window"], 0)
        self.assertGreaterEqual(use["helpers"], 0)
        self.assertGreater(use["total"], 0)


class Ahead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_the_ifc_models_geometry_read_ahead_is_given_once(self):
        import numpy as np
        from meridiana.quick.backend import scene_context
        path = Path(self.temp.name) / "ifc-test.npz"
        np.savez(path, vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 2]], "<f4"),
                 faces=np.array([[0, 1, 2]], "<u4"), centre=np.zeros(3), pieces=np.array([[0, 3, 0, 1]]),
                 colours=np.array([[0.5, 0.5, 0.5, 1.0]]), elements=np.zeros((0, 3), np.int64),
                 piece_of=np.zeros(0, np.int64))
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "0"}):
            self.assertFalse(scene_context.preload(str(path)))
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.assertTrue(scene_context.preload(str(path)))
            self.assertFalse(scene_context.preload(str(path)))       # once
            centre, pieces, info = scene_context._prepared(str(path))    # waited for, if still on its way
        self.assertEqual((len(pieces), info["triangles"]), (1, 1))
        self.assertEqual(pieces[0][0].size(), 36)                    # three float32 points, ready for Qt
        self.assertEqual(scene_context._READY, {})                   # given once: the memory is the 3D's now
        self.assertEqual(len(scene_context._prepared(str(path))[1]), 1)   # made now, as before
        # the 3D takes it as it took the mesh read on its thread
        from PySide6.QtCore import QObject
        parent = QObject()
        context = scene_context.IfcContext(parent)
        context._load(str(path))
        self.assertEqual((context.error, len(context._pieces), context.info["vertices"]), ("", 1, 3))
        self.assertEqual(list(context._pieces[0][3]), [1.0, 2.0, 0.0])     # the box in Qt's axes (z south)

    def _mesh(self):
        import numpy as np
        path = Path(self.temp.name) / "ifc-r27.npz"
        np.savez(path, vertices=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 2]], "<f4"),
                 faces=np.array([[0, 1, 2]], "<u4"), centre=np.zeros(3), pieces=np.array([[0, 3, 0, 1]]),
                 colours=np.array([[0.5, 0.5, 0.5, 1.0]]), elements=np.zeros((0, 3), np.int64),
                 piece_of=np.zeros(0, np.int64))
        return str(path)

    def test_r27_the_reading_ahead_stops_when_the_window_closes(self):
        # r27: in r25 the process of the window sometimes did not end after the IFC import (the large test IFC, Dell): the thread
        # reading ahead is now stopped and waited for when the window closes, and what it made let go.
        from meridiana.quick.backend import scene_context
        path = self._mesh()
        self.addCleanup(scene_context.shutdown)
        started = threading.Event()

        def endless(mesh, skip=(), check=None):
            started.set()
            pause = threading.Event()
            while True:
                check(0)
                pause.wait(0.01)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}), \
                mock.patch.object(scene_context, "prepared", endless):
            self.assertTrue(scene_context.preload(path))
            self.assertTrue(started.wait(5))
            thread = scene_context._THREADS[-1]
            self.assertTrue(scene_context.shutdown(timeout=3))
        self.assertFalse(thread.is_alive())
        self.assertEqual((scene_context._LOADING, scene_context._READY), ({}, {}))
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.assertTrue(scene_context.preload(path))          # the next window reads ahead again
            self.assertEqual(len(scene_context._prepared(path)[1]), 1)

    def test_r27_the_reading_ahead_always_says_it_ended(self):
        # an error of any kind: the 3D that waits for it is never left waiting
        from meridiana.quick.backend import scene_context
        path = self._mesh()
        self.addCleanup(scene_context.shutdown)

        def broken(mesh, skip=(), check=None):
            raise RuntimeError("broken on purpose")
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}), \
                mock.patch.object(scene_context, "prepared", broken), \
                mock.patch("meridiana.log.complain") as complained:
            self.assertTrue(scene_context.preload(path))
            scene_context._THREADS[-1].join(5)
        self.assertEqual((scene_context._LOADING, scene_context._READY), ({}, {}))
        self.assertTrue(complained.called)
        self.assertEqual(len(scene_context._prepared(path)[1]), 1)   # made now, as before

    def test_r27_nothing_read_ahead_for_the_model_the_3d_shows(self):
        # the same file imported again: in r25 its geometry was read ahead and never taken (0.4-0.5 GB on the large test IFC)
        from PySide6.QtCore import QObject
        from meridiana.quick.backend import scene_context
        path = self._mesh()
        self.addCleanup(scene_context.shutdown)
        parent = QObject()
        scene_context.IfcContext(parent)._load(path)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.assertFalse(scene_context.preload(path))
        scene_context.shown(None)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.assertTrue(scene_context.preload(path))

    def test_r27_what_the_3d_does_not_take_is_let_go(self):
        # the dialog reads ahead without the storeys left out, the 3D asks with them: in r25 the 0.4 GB made ahead for
        # the large test IFC stayed for the session, never given
        from PySide6.QtCore import QObject
        from meridiana.quick.backend import scene_context
        path = self._mesh()
        self.addCleanup(scene_context.shutdown)
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.assertTrue(scene_context.preload(path))
            scene_context._THREADS[-1].join(5)
        self.assertEqual(len(scene_context._READY), 1)
        parent = QObject()
        scene_context.IfcContext(parent)._load(path, (7,))      # a storey left out: another skip
        self.assertEqual(scene_context._READY, {})
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            self.assertFalse(scene_context.preload(path))       # the file is shown, whatever the skip

    def test_the_reading_of_an_ifc_file_kept_for_the_session(self):
        from meridiana.ui import ifc_import
        self.addCleanup(ifc_import._KEPT.clear)
        path = Path(self.temp.name) / "model.ifc"
        path.write_text("ISO-10303-21;", encoding="ascii")
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "1"}):
            first = ifc_import.IfcReading(str(path))
            first._keep({"buildings": [1, 2], "schema": "IFC4"})
            again = ifc_import.IfcReading(str(path))
            got = []
            again.done.connect(got.append)
            again.start()
            self.assertIsNone(again.process)                         # no worker
            self.assertTrue(_setup.wait_until(self.app, lambda: got, seconds=5))
            self.assertEqual((got[0]["buildings"], got[0]["from_memory"]), ([1, 2], True))
            got[0]["buildings"].append(3)                            # each asker has a copy of its own
            self.assertEqual(again._kept() and len(__import__("pickle").loads(again._kept())["buildings"]), 2)
            path.write_text("ISO-10303-21; changed", encoding="ascii")
            os.utime(path, ns=(time.time_ns(), path.stat().st_mtime_ns + 10**9))   # its time moved, as a save
            self.assertIsNone(ifc_import.IfcReading(str(path))._kept())   # the file changed: read again
        with mock.patch.dict(os.environ, {"MERIDIANA_PRELOAD": "0"}):
            ifc_import.IfcReading(str(path))._keep({"x": 1})
            self.assertIsNone(ifc_import.IfcReading(str(path))._kept())   # «Risparmia»: nothing kept


class Activity(unittest.TestCase):
    def test_r27_the_designer_back_after_a_quiet_is_told_once(self):
        from meridiana.quick.backend import activity
        seen = []

        class Listener:
            def back(self):
                seen.append(1)
        listener = Listener()
        activity.subscribe(listener.back)
        activity._last[0] = time.monotonic() - activity.IDLE_S - 1
        self.assertTrue(activity.idle())
        self.assertEqual(activity.wait_left_ms(), 0)
        activity.touch()
        activity.touch()                                # still at work: not told again
        self.assertEqual(seen, [1])
        self.assertFalse(activity.idle())
        self.assertGreater(activity.wait_left_ms(), 3000)
        del listener                                    # held weakly: gone with its object
        activity._last[0] = time.monotonic() - activity.IDLE_S - 1
        activity.touch()
        self.assertEqual(seen, [1])

    def test_r27_input_of_the_window_is_the_designer_at_work(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent, QWindow
        from meridiana.quick.backend import activity
        from meridiana.quick.backend.window_frame import AltTap
        _setup.qt_or_skip()
        window = QWindow()
        AltTap(window, window)
        activity._last[0] = time.monotonic() - 60
        hover = QMouseEvent(QEvent.Type.MouseMove, QPointF(5, 5), QPointF(5, 5), Qt.MouseButton.NoButton,
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.sendEvent(window, hover)       # a hover is not work
        self.assertTrue(activity.idle())
        press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(5, 5), Qt.MouseButton.LeftButton,
                            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        QCoreApplication.sendEvent(window, press)
        self.assertFalse(activity.idle())


if __name__ == "__main__":
    unittest.main()
