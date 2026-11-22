"""R614 (Daniel 14/11/2026: «Measure» with its arrow almost twice as wide as «Square», a lot of air between the word
and the arrow, «succede anche nella versione non compatta»): every button of the phases' bar with an arrow holds its
word in the middle, as a plain button does, with no more air than the plain buttons of its bar.

Before, the command's part was as wide as the longest word of its menu, «Remove all measurements» included (a
command run once, never on the face), measured in the wider face, with the word against the icon on the left."""
import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPointF

import _setup
from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import pump

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(node.childItems())
    return out


class TheButtonsWithAnArrow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), theme={'theme': 'light'})
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1900, 960)
        pump(200)

    @classmethod
    def tearDownClass(cls):
        cls.win.setProperty('toolbarMode', 'auto')
        cls.host.close()
        cls.folder.cleanup()

    def margins(self, button):
        """The air before what the command's part holds (the icon beside the word, the word under it) and after the
        word, up to the strip or the button's edge."""
        main = next((c for c in button.childItems() if c.property('mode') is not None), button)
        content = main.property('contentItem')
        word = next(c for c in content.childItems() if c.property('textStyle') is not None)
        x = word.mapToItem(main, QPointF(0, 0)).x()
        start = x
        if main.property('mode') == 'beside':
            start = min(c.mapToItem(main, QPointF(0, 0)).x() for c in content.childItems() if c.width() > 0)
        return start, main.width() - x - word.property('implicitWidth')

    def bar(self):
        bar = next(i for i in items(self.win.contentItem()) if i.objectName() == 'phaseToolbar')
        plain, split = [], {}
        for node in items(bar):
            name = node.objectName()
            if not name.startswith('tool_') or not node.isVisible() or name.endswith(('Arrow', 'Menu')):
                continue
            if node.property('stripWidth') is not None:
                split[name] = self.margins(node)
            elif node.property('mode') is not None:
                plain.append(self.margins(node))
        return plain, split

    def check(self, where):
        plain, split = self.bar()
        widest = max(max(p) for p in plain)
        for name, (left, right) in split.items():
            self.assertAlmostEqual(left, right, delta=1, msg=f'{where} {name}: the air before and after the word')
            self.assertLessEqual(max(left, right), widest + 1, f'{where} {name}: no more air than a plain button')
        return split

    def test_every_split_button_holds_its_word_as_a_plain_one(self):
        seen = set()
        for mode in ('under', 'beside'):
            self.win.setProperty('toolbarMode', mode)
            for phase in ('model', 'plant'):
                self.win.showPhase(phase)
                pump(120)
                header = next(i for i in items(self.win.contentItem()) if i.objectName() == 'phaseBar')
                self.assertEqual(header.property('barMode'), mode)
                seen |= set(self.check(f'{mode} {phase}'))
        self.assertIn('tool_tool_measure', seen)
        self.assertIn('tool_tool_subfield', seen)

    def test_a_mode_on_the_face_keeps_the_width_and_the_margins(self):
        """Ridge on the face of Pitch: the same width (the bar does not move), the word still in the middle."""
        self.win.setProperty('toolbarMode', 'beside')
        self.win.showPhase('model')
        pump(120)
        pitch = next(i for i in items(self.win.contentItem()) if i.objectName() == 'tool_tool_pitch' and i.isVisible())
        width, word = pitch.width(), pitch.property('text')
        header = next(i for i in items(self.win.contentItem()) if i.objectName() == 'phaseBar')
        header.setProperty('selectedTool', 'ridge')        # the tool in hand, as the plan says it (no plan view here)
        self.addCleanup(header.setProperty, 'selectedTool', 'select')
        pump(120)
        self.assertNotEqual(pitch.property('text'), word, 'the ridge is on the face')
        self.assertEqual(pitch.width(), width)
        self.check('beside model, ridge in hand')


if __name__ == '__main__':
    unittest.main()
