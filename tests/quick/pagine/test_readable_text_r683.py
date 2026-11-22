"""Complete readable text survives visual elision and Unicode."""
import _setup
from PySide6.QtCore import QObject, QPoint, Qt
from PySide6.QtTest import QTest
from quick.aiuti.text_scene import TextScene

class ReadablePages(TextScene):
    def test_bill_total_copies_label_band_value_and_unit(self):
        root, window = self.scene('BillsGrid', 'backend:({phaseId:"consumption",mode:"bills",billColumns:["F1"],bills:[],billTotals:({F1:123.5}),labels:({total:"Total"})})', module='local:Charts')
        pending = [root]
        total = None
        while pending:
            item = pending.pop()
            if item.property('copyText'):
                total = item
                break
            pending.extend(item.childItems())
        self.assertIsNotNone(total)
        total.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        expected = 'Total F1: ' + total.property('text') + ' kWh'
        self.assertEqual(self.app.clipboard().text(), expected)

    def test_elided_text_copies_full_content(self):
        root, window = self.scene('CopyLabel', 'elide: Text.ElideRight')
        root.setProperty('text', 'Long path C:/synthetic folder/project and \u00e8 \U0001f600' * 8)
        expected = root.property('text')
        QTest.mouseClick(window, Qt.RightButton, pos=QPoint(25, 12))
        self.assertTrue(_setup.wait_for(lambda: self.evaluate(root, 'textActions.menuActive'), 300))
        self.evaluate(root, 'textActions.execute("copy")')
        self.assertEqual(self.app.clipboard().text(), expected)

    def test_readable_selection_precedes_whole_block(self):
        root, window = self.scene('ReadableText')
        self.evaluate(root, 'select(0, 5); textActions.execute("copy")')
        self.assertEqual(self.app.clipboard().text(), 'Alpha')
        self.evaluate(root, 'textActions.execute("whole")')
        self.assertEqual(self.app.clipboard().text(), 'Alpha beta')

    def test_map_notice_copies_complete_message(self):
        root, window = self.scene('MapNotice', 'chooseText:"Choose"; closeText:"Close"; maps:({fallbackMessage:"Synthetic complete source message with path and details",retryText:"Retry",retryBackground:()=>{}})', module='local:Plan')
        words = root.findChild(QObject, 'mapNoticeText')
        words.forceActiveFocus()
        QTest.keyClick(window, Qt.Key_C, Qt.ControlModifier)
        self.assertEqual(self.app.clipboard().text(), 'Synthetic complete source message with path and details')
