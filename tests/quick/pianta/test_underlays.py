"""Images in the background menu, with project undo and two-point collectors."""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage

from meridiana import model
from meridiana.quick.backend.plan import PlanController

APP = None


def setUpModule():
    global APP
    APP = QApplication.instance() or QApplication([])


class Images(unittest.TestCase):
    def test_import_transform_transparency_visibility_and_removal_are_undoable(self):
        c = PlanController(model.Project(), manage_layout=False)
        self.addCleanup(c.close)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'roof.png'
            image = QImage(100, 50, QImage.Format_RGB32)
            image.fill(0xffffff)
            self.assertTrue(image.save(str(path)))
            c.underlays.importImage(QUrl.fromLocalFile(str(path)), 20, 30, 40)
        self.assertFalse(c.error)
        u = c.session.project.underlays[0]
        self.assertEqual(u.centre(), (20, 30))
        self.assertEqual(u.scale, .4)
        c.underlays.action(u.id, 'opacity', .2)
        c.underlays.action(u.id, 'show', 0)
        self.assertEqual(c.underlays.images[0]['opacity'], .2)
        self.assertFalse(c.underlays.images[0]['visible'])
        c.underlays.action(u.id, 'move', 0)
        c.click(0, 0, 0)
        c.click(5, 8, 0)
        self.assertEqual(c.session.project.underlays[0].centre(), (25, 38))
        c.underlays.action(u.id, 'scale', 0)
        c.click(0, 0, 0)
        c.click(10, 0, 0)
        self.assertFalse(c.underlays.accept('nonsense'))
        self.assertTrue(c.underlays.accept('2000 cm'))
        self.assertEqual(c.session.project.underlays[0].scale, .8)
        c.underlays.action(u.id, 'rotate', 0)
        self.assertTrue(c.underlays.accept('90'))
        self.assertEqual(c.session.project.underlays[0].rotation, 90)
        final = c.session.project.to_json()
        c.underlays.action(u.id, 'remove', 0)
        self.assertFalse(c.underlays.images)
        c.session.undo.undo()
        self.assertEqual(c.session.project.to_json(), final)
