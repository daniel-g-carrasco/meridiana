"""The native Quick preview keeps the geometry, the projection and the clickable measures of the Widgets' preview
(recorded on 10/11/2026, quick/aiuti/riferimenti.py)."""
import unittest

from PySide6.QtGui import QImage, QPainter
import _setup
from meridiana.app.session import ProjectSession
from meridiana.gui.backend.dialogs import DialogsBackend
from meridiana.gui.backend.dialogs_preview import DialogPreview
from quick.aiuti import riferimenti

setUpModule = _setup.keep_global_state


class DialogPreviewTest(unittest.TestCase):
    def test_widgets_geometry_projection_and_pills_match_and_measure_edits(self):
        _setup.qt_or_skip()
        backend = DialogsBackend(ProjectSession())
        self.addCleanup(backend.close)
        preview = DialogPreview()
        preview.setWidth(400)
        preview.setHeight(300)
        preview.backend = backend
        for kind in ('template', 'canopy'):
            with self.subTest(kind=kind):
                backend.open(kind)
                riferimenti.check(self, {'faces': preview.faces, 'guides': preview.guides, 'pills': preview._pills,
                                         'view': (preview.azimuth, preview.elevation),
                                         'projected': [(q.x(), q.y()) for q in map(preview.project, preview._all_points())]},
                                  # the drawing stands in the room the hint under it leaves, and the hint wraps where
                                  # the font says (with FreeType a line more or less: the drawing 18 px apart)
                                  wrap_paths=('$.projected',))
                for q in map(preview.project, preview._all_points()):
                    self.assertTrue(0 <= q.x() <= preview.width() and 0 <= q.y() <= preview.height(), (q.x(), q.y()))
                backend.highlightField('bay_width' if kind == 'canopy' else 'width')
                self.assertEqual({1, 3}, preview.highlight)
                backend.highlightField('')
                self.assertFalse(preview.highlight)
                image = QImage(400, 300, QImage.Format.Format_ARGB32_Premultiplied)
                painter = QPainter(image)
                preview.paint(painter)
                painter.end()
                self.assertTrue(preview._rects)
                for key, rect in preview._rects.items():
                    self.assertEqual(key, preview.key_at(rect.center()))
                before = backend.state['ring']
                self.assertTrue(backend.editMeasure('1', '24 m'))
                self.assertNotEqual(before, backend.state['ring'])

