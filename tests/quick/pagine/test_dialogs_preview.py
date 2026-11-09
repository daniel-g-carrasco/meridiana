"""The native Quick preview retains the Widgets geometry, projection and clickable measures."""
import unittest

from PySide6.QtGui import QImage, QPainter
import _setup
from meridiana.session import ProjectSession
from meridiana.quick.backend.dialogs import DialogsBackend
from meridiana.quick.backend.dialogs_preview import DialogPreview
from meridiana.ui.template_dialog import TemplateDialog
from meridiana.ui.canopy_dialog import CanopyDialog

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
        for kind, widget_class in [('template', TemplateDialog), ('canopy', CanopyDialog)]:
            with self.subTest(kind=kind):
                backend.open(kind)
                widget = widget_class()
                self.addCleanup(widget.deleteLater)
                old = widget.preview
                old.resize(400, 300)
                preview.textFont = old.font()
                self.assertEqual(old.faces, preview.faces)
                self.assertEqual(old.guides, preview.guides)
                self.assertEqual(old._pills, preview._pills)
                backend.highlightField('bay_width' if kind == 'canopy' else 'width')
                self.assertEqual({1, 3}, preview.highlight)
                backend.highlightField('')
                self.assertFalse(preview.highlight)
                self.assertEqual((old.azimuth, old.elevation), (preview.azimuth, preview.elevation))
                for point in preview._all_points():
                    self.assertEqual(old.project(point), preview.project(point))
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

