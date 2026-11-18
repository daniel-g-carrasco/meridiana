"""«Show Meridio what I see» (R320): the phase's view attached as a picture, named after the phase, without Meridio's
bubble and without the dialogs. The 3D view does not draw offscreen (ui/quick_image.py): its picture is checked on a
real screen only."""

import unittest
from pathlib import Path

import _setup
from _fixtures import capannone
from _setup import wait_until

from meridiana.assistant import images

setUpModule = _setup.keep_global_state

OUT = Path(__file__).resolve().parents[2] / "build" / "claude-r07"


class ShowWhatISee(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()

    def setUp(self):
        _setup.window(self, capannone())
        self.win.assistant.reduced_motion = True
        self.app.processEvents()

    def test_the_button_attaches_the_phase_view_without_meridio_and_named_after_the_phase(self):
        win, a, chat = self.win, self.win.assistant, self.win.assistant_chat
        a.open_panel()
        self.app.processEvents()
        self.assertTrue(a.view_button.isVisibleTo(a.panel))
        self.assertTrue(a.view_button.toolTip())
        page = win.tabs.pages.currentWidget()
        # Meridio and his bubble are the window's, not the page's: a grab of the page cannot hold them
        for part in (a, a.bubble):
            self.assertFalse(page.isAncestorOf(part))
        from PySide6.QtCore import QPoint, QRect
        view = QRect(page.mapTo(win, QPoint(0, 0)), page.size())
        bubble = QRect(a.bubble.mapTo(win, QPoint(0, 0)), a.bubble.size())
        self.assertTrue(a.bubble.isVisible() and view.intersects(bubble),
                        "the bubble is over the view: the test means something")
        expected = page.grab().toImage()
        a.view_button.click()
        self.assertTrue(wait_until(self.app, lambda: not chat.attachment_jobs, 10))
        item = next(iter(chat.attachments.values()))
        self.assertIsInstance(item, images.Picture)
        self.assertTrue(item.captured)
        self.assertEqual(item.name, f"View: {chat.host.phase_title()}")
        self.assertEqual(item.original, (expected.width(), expected.height()))
        # the picture is the page as drawn, not the window with the bubble over it
        shown = chat.host.view_image()
        self.assertEqual(shown.size(), expected.size())
        # the page as it is now: a slow machine may still be finishing a fade of what was there when `expected` was taken
        self.assertTrue(wait_until(self.app, lambda: chat.host.view_image().convertToFormat(expected.format())
                                   == page.grab().toImage().convertToFormat(expected.format()), 5))
        OUT.mkdir(parents=True, exist_ok=True)
        shown.save(str(OUT / "OM-vista-catturata.png"))
        a.grab().save(str(OUT / "OM-pulsante-vista.png"))
        win.grab().save(str(OUT / "OM-finestra-con-meridio.png"))

    def test_another_phase_gives_its_own_view_and_name(self):
        win, chat = self.win, self.win.assistant_chat
        index = next(i for i in range(win.tabs.count()) if win.tabs.tabBar().isTabVisible(i) and i != 0)
        win.tabs.setCurrentIndex(index)
        self.app.processEvents()
        chat.show_view()
        self.assertTrue(wait_until(self.app, lambda: not chat.attachment_jobs, 10))
        item = next(iter(chat.attachments.values()))
        self.assertEqual(item.name, f"View: {chat.host.phase_title()}")
        self.assertNotEqual(chat.host.phase(), "model")


if __name__ == "__main__":
    unittest.main()
