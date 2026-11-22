"""R625 (Daniel 15/11/2026, Linux, the Flatpak of r34-unita): the Balance page with nothing in the middle, and the
Inverter section of the Plant panel that turned its arrow and opened on nothing. Both were made in the background:
Workbench.qml warms the pages and panels of the other phases while hidden (asynchronous Loaders), and every Loader
inside them is then made a slice at a time too. When something such a making had made is destroyed between two
slices, Qt throws the whole object away («Object or context destroyed during incubation»): the Loader stays in Error,
with no item, for good (reproduced in the real window, offscreen and on Direct3D 11: the first start of Daniel's Rho,
the year computed, then the Plant phase and its Inverter section).

M.WholeLoader makes its item again, whole, when it is seen in that state. Here the failure is Qt's own, made on
purpose: an item whose first making loses one of its objects between two slices of a slow incubation."""
import tempfile
import unittest
from pathlib import Path

import _setup
from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression, QQmlIncubationController, qmlContext
from shiboken6 import delete

setUpModule = _setup.keep_global_state

# The item made in the background. Its last object's binding runs first when the making completes (Qt evaluates the
# bindings from the last made); it hands one object of the item to the killer, which destroys it at the next turn of
# events, between two slices: the 100 slow bindings before it are still to be evaluated, so the making is not over.
FLAKY = ("import QtQuick\nItem {\n    objectName: \"made\"\n    Item { id: victim }\n"
         + "".join("    Item { width: { let s = %d; for (let k = 0; k < 20000; k++) s += k; return s %% 7 } }\n" % i
                   for i in range(100))
         + "    Item { property var held: killer.take(victim) }\n}\n")


class Killer(QObject):
    def __init__(self):
        super().__init__()
        self.armed = True
        self.killed = 0

    @Slot(QObject, result=bool)
    def take(self, victim):
        if self.armed:
            self.armed = False
            self.killed += 1
            QTimer.singleShot(0, victim.deleteLater)
        return True


class SlowIncubation(QQmlIncubationController):
    """A making a slice of 1 ms every 10 ms, as a hidden page's is when the window draws no frame."""
    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.setInterval(10)
        self.timer.timeout.connect(lambda: self.incubatingObjectCount() and self.incubateFor(1))
        self.timer.start()


class WholeLoaderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def scene(self, source, *, asynchronous=True, kind="M.WholeLoader { shown: false; "):
        from meridiana.gui.backend.controls import install_controls
        folder = Path(tempfile.mkdtemp(prefix="r625-"))
        if source == "flaky":
            (folder / "Flaky.qml").write_text(FLAKY, encoding="utf-8")
        engine = QQmlEngine()
        install_controls(engine, dict(theme="light", reducedMotion=True))
        incubation = SlowIncubation()
        engine.setIncubationController(incubation)
        killer = Killer()
        engine.rootContext().setContextProperty("killer", killer)
        component = QQmlComponent(engine)
        component.setData(("import QtQuick\nimport Meridiana.Controls as M\n"
                           "M.WholeLoader { asynchronous: %s; shown: false; source: %r }\n"
                           % ("true" if asynchronous else "false", (folder / "Flaky.qml").as_uri()
                              if source == "flaky" else (folder / "Missing.qml").as_uri())).encode(), QUrl())
        self.assertFalse(component.isError(), "\n".join(e.toString() for e in component.errors()))
        loader = component.create()
        loader.setParent(engine)

        def cleanup():
            incubation.timer.stop()
            delete(loader)
            delete(engine)
        self.addCleanup(cleanup)
        return loader, killer

    def status(self, loader):
        # a Loader's status is an enum PySide cannot convert: read through QML
        value, _undefined = QQmlExpression(qmlContext(loader), loader, "status").evaluate()
        return int(value)

    def test_an_item_thrown_away_half_made_is_made_again_when_shown(self):
        loader, killer = self.scene("flaky")
        # Qt's own failure, as in the window: Error, no item (Loader.Error is 3)
        self.assertTrue(_setup.wait_until(self.app, lambda: self.status(loader) != 2, 30))
        self.assertEqual(killer.killed, 1)
        self.assertEqual(self.status(loader), 3)
        self.assertIsNone(loader.property("item"))
        # hidden, it is left as it is: nothing is made for a page nobody looks at
        _setup.turn_events(self.app, 100)
        self.assertEqual(loader.property("remade"), 0)
        # shown: made again, whole
        loader.setProperty("shown", True)
        self.assertTrue(_setup.wait_until(self.app, lambda: loader.property("item") is not None, 20),
                        (loader.property("remade"), self.status(loader), loader.property("active"), loader.property("source")))
        self.assertEqual(loader.property("item").objectName(), "made")
        self.assertEqual(loader.property("remade"), 1)
        self.assertEqual(self.status(loader), 1)

    def test_a_plain_loader_is_left_empty_by_the_same_failure(self):
        # what the pages and the sections had before: the same failure leaves the Loader empty, shown or not
        loader, killer = self.scene("flaky", kind="Loader { ")
        self.assertTrue(_setup.wait_until(self.app, lambda: self.status(loader) != 2, 30))
        self.assertEqual((killer.killed, self.status(loader)), (1, 3))
        loader.setProperty("visible", False)
        loader.setProperty("visible", True)
        _setup.turn_events(self.app, 500)
        self.assertIsNone(loader.property("item"))
        self.assertEqual(self.status(loader), 3)

    def test_an_item_that_cannot_be_made_is_tried_twice_not_for_ever(self):
        loader, _killer = self.scene("missing", asynchronous=False)
        self.assertEqual(self.status(loader), 3)
        loader.setProperty("shown", True)
        _setup.turn_events(self.app, 300)
        self.assertEqual(loader.property("remade"), 2)
        self.assertEqual(self.status(loader), 3)
        # shown again later: two more tries, never a loop
        loader.setProperty("shown", False)
        loader.setProperty("shown", True)
        _setup.turn_events(self.app, 300)
        self.assertEqual(loader.property("remade"), 4)


if __name__ == "__main__":
    unittest.main()
