"""Synthetic PDF text, asynchronous copy and generation invalidation."""
import tempfile
import unittest
from pathlib import Path
import _setup
from PySide6.QtCore import QThreadPool
from meridiana.gui.backend import report_pages

class ReportCopy(unittest.TestCase):
    def setUp(self):
        self.app = _setup.quick_app()
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'synthetic.pdf'
        stream = b'BT /F1 12 Tf 50 700 Td (Synthetic first page) Tj ET'
        objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
                   b'<< /Type /Pages /Kids [3 0 R 6 0 R] /Count 2 >>',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
                   b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
                   f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream',
                   b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /XObject << /Im1 7 0 R >> >> /Contents 8 0 R >>',
                   b'<< /Type /XObject /Subtype /Image /Width 1 /Height 1 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length 3 >>\nstream\n\xff\x00\x00\nendstream',
                   b'<< /Length 36 >>\nstream\nq 100 0 0 100 50 700 cm /Im1 Do Q\nendstream']
        data, offsets = b'%PDF-1.4\n', []
        for index, obj in enumerate(objects, 1):
            offsets.append(len(data))
            data += f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n'
        xref = len(data)
        data += b'xref\n0 9\n0000000000 65535 f \n' + b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
        data += f'trailer\n<< /Size 9 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
        self.path.write_bytes(data)
        self.rows = [dict(path=str(self.path), index=i, ratio=1.4) for i in range(2)]

    def test_text_page_and_image_page(self):
        keys = report_pages.publish(self.rows)
        self.assertIn('Synthetic first page', report_pages.extract_text(keys[0]['source']))
        self.assertEqual(report_pages.extract_text(keys[1]['source']), '')

    def test_async_read_does_not_copy_and_stale_copy_is_discarded(self):
        service = report_pages.PageText()
        self.addCleanup(service.deleteLater)
        keys = report_pages.publish(self.rows)
        self.app.clipboard().setText('sentinel')
        service.request(keys[0]['source'], False)
        self.assertTrue(_setup.wait_for(lambda: not service.busy, 5000))
        self.assertIn('Synthetic first page', service.text)
        self.assertEqual(self.app.clipboard().text(), 'sentinel')
        service.request(keys[0]['source'], True)
        newer = self.path.with_name('newer.pdf')
        newer.write_bytes(self.path.read_bytes().replace(b'Synthetic first page', b'Synthetic other page'))
        second = report_pages.publish([{**row, 'path': str(newer)} for row in self.rows])
        QThreadPool.globalInstance().waitForDone(5000)
        self.app.processEvents()
        self.assertEqual(self.app.clipboard().text(), 'sentinel')
        service.request(second[0]['source'], False)
        self.assertTrue(_setup.wait_for(lambda: not service.busy, 5000))
        self.assertIn('Synthetic other page', service.text)

    def test_cancel_never_changes_clipboard(self):
        service = report_pages.PageText()
        self.addCleanup(service.deleteLater)
        keys = report_pages.publish(self.rows)
        self.app.clipboard().setText('sentinel')
        service.request(keys[0]['source'], True)
        service.cancel()
        QThreadPool.globalInstance().waitForDone(5000)
        self.app.processEvents()
        self.assertEqual(self.app.clipboard().text(), 'sentinel')

    def test_current_copy_empty_page_and_error(self):
        service = report_pages.PageText()
        self.addCleanup(service.deleteLater)
        keys = report_pages.publish(self.rows)
        service.request(keys[0]['source'], True)
        self.assertTrue(_setup.wait_for(lambda: not service.busy, 5000))
        self.assertIn('Synthetic first page', self.app.clipboard().text())
        service.request(keys[1]['source'], True)
        self.assertTrue(_setup.wait_for(lambda: not service.busy, 5000))
        self.assertFalse(service.canCopy(keys[1]['source']))
        self.assertIn('Synthetic first page', self.app.clipboard().text())
        broken = self.path.with_name('broken.pdf')
        broken.write_bytes(b'Not a PDF')
        key = report_pages.publish([dict(path=str(broken), index=0, ratio=1.4)])[0]['source']
        service.request(key, True)
        self.assertTrue(_setup.wait_for(lambda: not service.busy, 5000))
        self.assertTrue(service.error)
        self.assertIn('Synthetic first page', self.app.clipboard().text())

    def test_old_worker_cannot_fill_new_generation_cache(self):
        import threading
        from unittest.mock import patch
        first = report_pages.publish(self.rows)[0]['source']
        started, release = threading.Event(), threading.Event()
        read = Path.read_bytes
        def delayed(path):
            data = read(path)
            if path == self.path and not release.is_set():
                started.set()
                release.wait(3)
            return data
        service = report_pages.PageText()
        self.addCleanup(service.deleteLater)
        self.addCleanup(release.set)
        with patch.object(Path, 'read_bytes', delayed):
            service.request(first, True)
            self.assertTrue(_setup.wait_for(started.is_set, 2000))
            self.path.write_bytes(read(self.path).replace(b'Synthetic first page', b'Synthetic other page'))
            second = report_pages.publish(self.rows)[0]['source']
            release.set()
            QThreadPool.globalInstance().waitForDone(5000)
            self.app.processEvents()
            service.request(second, False)
            self.assertTrue(_setup.wait_for(lambda: not service.busy, 5000))
            self.assertIn('Synthetic other page', service.text)
