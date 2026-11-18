"""The groups the plan makes for its lights (hover, erase, sweep): of our own in the scene, never
QGraphicsScene.createItemGroup. The wrapper of a group that C++ made is not told when the scene deletes it, and a new
object born at the same address, a QAction of a menu, is then handed that old QGraphicsItemGroup: «'QGraphicsItemGroup'
object has no attribute 'setCheckable'» in the assistant's menu of a later test (02/11/2026)."""

import re
import unittest
from pathlib import Path

import _setup

setUpModule = _setup.keep_global_state


class TheGroups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def test_a_group_kept_by_python_does_not_outlive_its_scene_as_a_stale_wrapper(self):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtGui import QPainterPath
        from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QMenu

        from meridiana.ui.plan import group_items
        path = QPainterPath()
        path.addRect(0, 0, 1, 1)
        wrong = []
        for _n in range(60):
            scene = QGraphicsScene()
            view = QGraphicsView(scene)
            kept = group_items(scene, [scene.addPath(path), scene.addPath(path)])      # kept, like Plan.hover_item
            self.assertEqual(len(kept.childItems()), 2)
            view.deleteLater()
            scene.deleteLater()
            del view, scene
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            for _i in range(10):
                menu = QMenu()
                wrong += [type(menu.addAction("x")).__name__]
            del kept
        self.assertEqual([name for name in wrong if name != "QAction"], [])

    def test_the_plan_makes_no_group_in_c_plus_plus(self):
        source = (Path(__file__).resolve().parents[2] / "src" / "meridiana" / "ui" / "plan.py").read_text(
            encoding="utf-8")
        self.assertIsNone(re.search(r"\.createItemGroup\(", source.split("def group_items", 1)[1]))


if __name__ == "__main__":
    unittest.main()
