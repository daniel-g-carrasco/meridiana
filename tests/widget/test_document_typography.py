"""Tables repeat their headings when a technical document spans pages."""
import unittest

import _setup

setUpModule = _setup.keep_global_state


class Documents(unittest.TestCase):
    def test_image_caption_stays_on_the_image_page(self):
        _setup.qt_or_skip()
        from PySide6.QtCore import QSizeF, QUrl
        from PySide6.QtGui import QImage, QTextDocument
        from meridiana.ui.document_layout import keep_together
        doc = QTextDocument()
        picture = QImage(200, 140, QImage.Format.Format_RGB32)
        picture.fill('white')
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl('plan'), picture)
        doc.setHtml('<p>' + 'Lead<br>' * 12 + 'Lead</p><p><img src="plan"></p><p>Caption</p>')
        doc.setPageSize(QSizeF(300, 300))
        doc.pageCount()
        first = doc.begin().next()
        last = first.next()
        self.assertEqual(keep_together(doc, [(first.position(), last.position())]), 1)
        layout = doc.documentLayout()
        self.assertEqual(int(layout.blockBoundingRect(first).top() // 300),
                         int(layout.blockBoundingRect(last).bottom() // 300))

    def test_data_table_has_a_repeating_heading_in_the_qt_document(self):
        _setup.qt_or_skip()
        from PySide6.QtGui import QTextDocument
        from meridiana.ui.report_chapters import table
        doc = QTextDocument()
        doc.setHtml(table([('String 1', 12), ('String 2', 14)], ['String', 'Modules'], right=(1,)))
        grid = doc.rootFrame().childFrames()[0]
        self.assertEqual(grid.format().headerRowCount(), 1)

    def test_purpose_presets_keep_technical_checks_visible(self):
        from meridiana import reports
        for key in ('client', 'electrical', 'energy'):
            self.assertIn('checks', reports.templates()[key].chapters)
