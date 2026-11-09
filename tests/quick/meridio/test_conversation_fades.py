"""R489, the fades of Meridio's conversation (Daniel, 07/11/2026, the third time: «la velatura all'interno del fumetto
di Meridio continua a non andare bene»): the text scrolled out of the box is cut at the box's edge with no veil. The
conversation's ScrollView never used EdgeFades; the fixes of R489 went into the component only."""
import os
import unittest
from pathlib import Path

from PySide6.QtCore import QObject, QPointF
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from shiboken6 import delete

from meridiana import config
from meridiana.quick.backend.assistant import build_page
from meridiana.quick.backend.assistant_chat import AssistantChat
from quick.meridio.support import Host, KeyStore, Voice


def _close(a: QColor, b: QColor, tolerance: int = 3) -> bool:
    return all(abs(x - y) <= tolerance for x, y in zip(a.getRgb()[:3], b.getRgb()[:3]))


class ConversationFades(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def scene(self):
        chat = AssistantChat(Host(), config.Config(assistant_introduced=True, assistant_local_model='fake'),
                             key_store=KeyStore(), voice=Voice())
        self.addCleanup(chat.close)
        engine, window, theme = build_page(chat=chat, options={'reducedMotion': True})
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        QTest.qWait(150)
        root = window.findChild(QObject, 'assistantLayer')

        def cleanup():
            window.close()
            errors = list(engine._assistant_diagnostics)
            delete(engine)
            self.assertEqual(errors, [])
        self.addCleanup(cleanup)
        chat.view.answer('\n\n'.join(f'Riga {n}: senza quel valore il controllo resta aperto anche dopo aver ridotto '
                                     'le stringhe. Inserisci il fusibile dalle proprietà del modulo.' for n in range(30)))
        QTest.qWait(200)
        return window, root, theme

    def test_text_scrolled_past_the_top_fades_into_the_box(self):
        window, root, theme = self.scene()
        scroll = root.findChild(QObject, 'conversationScroll')
        flick = scroll.property('contentItem')
        # half way: text above and below the view
        flick.setProperty('contentY', (flick.property('contentHeight') - flick.property('height')) / 2)
        QTest.qWait(120)
        image = window.grabWindow()
        out = os.environ.get('MERIDIANA_FADES_SHOT')
        if out:
            image.save(str(Path(out)))
        dpr = image.devicePixelRatio()
        ground = QColor(theme.colors['view'])
        top_left = flick.mapToItem(window.contentItem(), QPointF(0, 0))
        width, height = flick.property('width'), flick.property('height')
        box = scroll.mapToItem(window.contentItem(), QPointF(0, 0))
        x0, x1 = round(top_left.x() * dpr), round((top_left.x() + width) * dpr)

        def stray(y0, y1):
            """Pixels between rows y0 and y1 (logical) that are not the box's ground: text out of the view."""
            found = []
            for py in range(round(y0 * dpr), round(y1 * dpr)):
                for px in range(x0, x1):
                    c = image.pixelColor(px, py)
                    if not _close(c, ground, 10):
                        found.append((px, py, c.name()))
            return found
        # The padding between the view and the box's border holds no text, above and below (Daniel's photo: a line
        # cut in half by the border, outside the veil).
        above = stray(box.y() + 2, top_left.y())
        below = stray(top_left.y() + height, box.y() + scroll.property('height') - 2)
        self.assertEqual(above[:5], [], f'{len(above)} pixels of text above the view')
        self.assertEqual(below[:5], [], f'{len(below)} pixels of text below the view')

    def test_a_line_cut_by_the_edge_is_hidden_by_the_veil(self):
        """Daniel's photo: «a meno che 1,35 volte il fusibile...» cut in half by the top edge and still dark. Whatever
        the scrolling, the 8 pixels next to each edge show text at most faintly (a veil 12 px tall over lines 20 px
        tall left the cut half almost bare)."""
        window, root, theme = self.scene()
        scroll = root.findChild(QObject, 'conversationScroll')
        flick = scroll.property('contentItem')
        ground = QColor(theme.colors['view'])
        middle = (flick.property('contentHeight') - flick.property('height')) / 2
        worst = (0, None)
        for step in range(0, 24, 3):
            flick.setProperty('contentY', middle + step)
            QTest.qWait(60)
            image = window.grabWindow()
            dpr = image.devicePixelRatio()
            top_left = flick.mapToItem(window.contentItem(), QPointF(0, 0))
            x0, x1 = round(top_left.x() * dpr), round((top_left.x() + flick.property('width')) * dpr)
            top = round(top_left.y() * dpr)
            bottom = round((top_left.y() + flick.property('height')) * dpr)
            for py in list(range(top, top + round(8 * dpr))) + list(range(bottom - round(8 * dpr), bottom)):
                for px in range(x0, x1, 2):
                    c = image.pixelColor(px, py)
                    gap = max(abs(a - b) for a, b in zip(c.getRgb()[:3], ground.getRgb()[:3]))
                    if gap > worst[0]:
                        worst = (gap, (step, px, py, c.name()))
        self.assertLessEqual(worst[0], 70, f'text next to the edge too dark: {worst}')
        fades = [item for item in root.findChildren(QObject) if item.objectName() in ('topFade', 'bottomFade')]
        shown = [f for f in fades if f.property('visible') and _inside(f, scroll)]
        self.assertEqual(len(shown), 2, 'both veils over the conversation half way through it')


def _inside(item, ancestor) -> bool:
    parent = item.parentItem()
    while parent is not None:
        if parent == ancestor:
            return True
        parent = parent.parentItem()
    return False


if __name__ == '__main__':
    unittest.main()
