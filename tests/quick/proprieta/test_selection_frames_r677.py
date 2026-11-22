"""Selection replaces a complete form, including the panel's held headings."""
import tempfile
import unittest
from pathlib import Path

import _setup
from _fixtures import mixed
from PySide6.QtQml import QJSValue

from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import pump

# Software rendering also builds the first sub-field's editors in this interval.
# Two isolated runs took 306-332 ms after the fix, over 1000 ms before it.
SELECTION_PANEL_FINISHED_MS = 500


def items(item):
    yield item
    for child in item.childItems():
        yield from items(child)


class SelectionFrames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()

    def test_selection_frames_are_whole_and_finish_promptly(self):
        import time

        with tempfile.TemporaryDirectory() as directory:
            host = QuickWindow(mixed(), Path(directory), real_views=True)
            try:
                win = host.window
                win.resize(1586, 904)
                win.show()
                pump(1500)
                win.showPhase('model')
                win.setProperty('viewMode', 'both')
                pump(300)
                backend = host.parts.controllers['properties']
                page = next(i for i in items(win.contentItem()) if i.objectName() == 'properties-page')
                forms = next(i for i in items(page) if i.objectName() == 'currentForm')
                held = next(i for i in items(page) if i.objectName() == 'heldHeads')
                session = host.bridge.session
                gestures = [('empty', lambda: session.select('site', '')),
                            ('building', lambda: host.plan.editor.select('building', 'b1')),
                            ('escape', lambda: host.plan.key('Escape')),
                            ('other', lambda: host.plan.editor.select('building', 'b9')),
                            ('third', lambda: host.plan.editor.select('building', 'b10')),
                            ('subfield', lambda: host.plan.editor.select('subfield', 's9')),
                            ('blank', lambda: host.plan.click(-1000, -1000)),
                            ('tree', lambda: host.parts.controllers['project_tree'].select('building', 'b1'))]
                problems = []
                for name, gesture in gestures:
                    frames = []
                    start = time.perf_counter()

                    def sample(frames=frames, start=start):
                        visible = [i for i in forms.childItems() if i.property('key') is not None
                                   and i.isVisible() and i.opacity() > .001]
                        keys = [i.property('key') for i in visible]
                        heads = held.property('shownHeads')
                        if isinstance(heads, QJSValue):
                            heads = heads.toVariant()
                        mixed_heads = []
                        for head in heads:
                            ancestor = head
                            while ancestor is not None and ancestor.parentItem() != forms:
                                ancestor = ancestor.parentItem()
                            if ancestor is None or ancestor.property('key') != page.property('shownForm'):
                                mixed_heads.append(head.property('title'))
                        expected_heads = [i for holder in visible for i in items(holder)
                                          if i.property('sectionControl') is True and i.isVisible()
                                          and i.width() > 0 and i.property('headKeeper') == held.parentItem()]
                        if set(heads) != set(expected_heads):
                            mixed_heads.append('incomplete heading set')
                        frames.append(((time.perf_counter() - start) * 1000, keys, mixed_heads))

                    win.afterAnimating.connect(sample)
                    gesture()
                    pump(700)
                    win.afterAnimating.disconnect(sample)
                    self.assertTrue(frames, name)
                    for ms, keys, wrong_heads in frames:
                        if len(keys) != 1 or wrong_heads:
                            problems.append((name, round(ms, 1), keys, wrong_heads))
                    unfinished = [ms for ms, keys, heads in frames
                                  if keys != [backend.currentForm] or heads]
                    ready = next((ms for ms, keys, heads in frames
                                  if ms > max(unfinished, default=-1)
                                  and keys == [backend.currentForm] and not heads), float('inf'))
                    if ready > SELECTION_PANEL_FINISHED_MS:
                        problems.append((name, 'late', round(ready, 1)))
                self.assertEqual(problems, [])
            finally:
                host.close()
                self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
