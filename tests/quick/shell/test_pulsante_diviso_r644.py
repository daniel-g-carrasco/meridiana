"""R644 (Daniel 15/11/2026, «Measure» on with only its first half lit: «non mi piace che quando attivo una qualsiasi
funzione di un pulsante strumenti che è suddiviso con il pulsante per richiamare il menù a comparsa, rimanga evidenziata
solo la prima metà»; of three variants drawn, «ci sta la 2»): a split button with its tool on is lit whole, in two tones
whose change is the divider, no hair. The tool's half in `press`, the arrow's half a step less; under the pointer the
tool's half darker still, the arrow's half over the tool's; with the menu open the arrow's more. In every state the two
halves differ, read on the pixels. One ground for every split button (Controls/SplitGround)."""
import os
import re
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtQml import QQmlEngine, QQmlExpression
from PySide6.QtGui import QColor

import _setup
from _fixtures import capannone
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import click, mouse, pump, wait_for

if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    os.environ.setdefault('QSG_RENDER_LOOP', 'basic')

QML = Path(__file__).resolve().parents[3] / 'src/meridiana/gui/qml/Meridiana'


def items(root):
    out, pending = [], [root]
    while pending:
        node = pending.pop()
        out.append(node)
        pending.extend(node.childItems())
    return out


def lift(colour, panel):
    """How far a tone stands from the bar's ground: the sum of the channels' differences."""
    return sum(abs(a - b) for a, b in zip(colour.getRgb()[:3], panel.getRgb()[:3], strict=True))


class SplitButtonOn(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _setup.qt_or_skip()
        create_app()
        cls.folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.host = QuickWindow(capannone(), Path(cls.folder.name), real_views=True, theme={'theme': 'light'})
        cls.win = cls.host.window
        cls.win.show()
        pump(80)
        cls.win.resize(1600, 900)
        pump(200)

    @classmethod
    def tearDownClass(cls):
        cls.host.close()
        cls.folder.cleanup()

    def find(self, name):
        return next((i for i in items(self.win.contentItem()) if i.objectName() == name and i.isVisible()), None)

    def colour(self, image, item, x, y):
        dpr = image.devicePixelRatio()
        p = item.mapToScene(QPointF(x, y))
        return image.pixelColor(int((p.x() + .5) * dpr), int((p.y() + .5) * dpr))

    def halves(self, button, split):
        """The colour of each half on screen near the top, where neither the icon, the word nor the arrow is, and the
        bar's ground just outside the button; and the column at the meeting of the halves."""
        pump(60)
        image = self.win.grabWindow()
        y = 3
        command = self.colour(image, button, split / 2, y)
        arrow = self.colour(image, button, split + (button.width() - split) / 2, y)
        panel = self.colour(image, button, button.width() / 2, -3)
        meeting = [self.colour(image, button, x, button.height() / 2 + dy) for x in (split - 1, split)
                   for dy in (-8, 8)]
        return command, arrow, panel, meeting

    def point(self, at):
        mouse(self.app, self.win, QEvent.Type.MouseMove, at, Qt.MouseButton.NoButton, Qt.MouseButton.NoButton)
        pump(120)

    def test_measure_on_has_two_tones_in_every_state(self):
        self.win.showPhase('model')
        pump(300)
        button = self.find('tool_tool_measure')
        self.assertIsNotNone(button, 'Measure is a split button of the bar')
        arrow_item = self.find('tool_tool_measureArrow')
        split = button.width() - arrow_item.width()
        self.point(QPointF(5, self.win.height() - 5))
        off_command, off_arrow, panel, _ = self.halves(button, split)
        self.assertEqual(off_command, off_arrow, 'off and away from the pointer: nothing lit')
        self.host.shell.trigger('tool_measure')
        wait_for(lambda: self.find('tool_tool_measureGround').property('on'), 5)
        self.addCleanup(lambda: self.host.shell.trigger('tool_select'))
        tones = {}
        # at rest: the tool's half in press, the arrow's a step less, both lit; no hair where they meet
        command, arrow, panel, meeting = self.halves(button, split)
        tones['rest'] = command, arrow
        self.assertGreater(lift(arrow, panel), 0, 'the arrow\'s half is lit too')
        self.assertGreater(lift(command, panel), lift(arrow, panel), 'the tool\'s half the stronger')
        self.assertTrue(all(c in (command, arrow) for c in meeting), f'no hair between the halves: {meeting}')
        self.assertFalse([i for i in items(button) if i.objectName() == 'splitDivider'], 'no divider item')
        # the pointer on the tool's half: it goes darker still, the arrow's stays
        self.point(button.mapToScene(QPointF(split / 2, 3)))
        command, arrow, panel, _ = self.halves(button, split)
        tones['tool'] = command, arrow
        self.assertGreater(lift(command, panel), lift(tones['rest'][0], panel))
        self.assertEqual(arrow, tones['rest'][1])
        # the pointer on the arrow's half: it rises over the tool's
        self.point(arrow_item.mapToScene(QPointF(arrow_item.width() / 2, arrow_item.height() / 2)))
        command, arrow, panel, _ = self.halves(button, split)
        tones['arrow'] = command, arrow
        self.assertEqual(command, tones['rest'][0])
        self.assertGreater(lift(arrow, panel), lift(command, panel), 'the arrow\'s half over the tool\'s')
        # the menu open: the arrow's half stronger still
        menu = next(o for o in button.findChildren(QObject) if o.objectName() == 'tool_tool_measureMenu')
        menu.open()
        wait_for(lambda: menu.property('visible'), 5)
        command, arrow, panel, _ = self.halves(button, split)
        tones['menu'] = command, arrow
        self.assertGreater(lift(arrow, panel), lift(tones['arrow'][1], panel))
        menu.close()
        pump(100)
        for state, (command, arrow) in tones.items():
            with self.subTest(state=state):
                self.assertNotEqual(command, arrow, 'the two halves differ: the change of tone is the divider')

    def test_one_ground_for_every_split_button(self):
        for name in ('Controls/SplitButton.qml', 'Shell/PhaseSplitButton.qml'):
            with self.subTest(name=name):
                text = (QML / name).read_text(encoding='utf-8')
                self.assertRegex(text, r'\bSplitGround\s*\{')
                self.assertNotIn('Theme.colors.press', text, 'the tones are the ground\'s, not written in each one')

    def test_compact_plan_buttons_share_the_ground_and_states(self):
        self.win.showPhase('model')
        self.host.shell.trigger('view_plan')
        pump(300)
        tokens = self.host.engine.rootContext().contextProperty('themeTokens')
        for theme, command in ((t, c) for t in ('light', 'dark') for c in ('background', 'sun_map')):
            tokens.configure({'theme': theme})
            pump(80)
            button = self.find('planView-' + command)
            self.assertIsNotNone(button)
            ground = next((i for i in items(button) if i.objectName() == button.objectName() + 'Ground'), None)
            self.assertIsNotNone(ground, 'the compact split uses the common ground')
            self.assertEqual(button.height(), 27)
            button.setProperty('checked', True)
            split = ground.property('split')
            self.point(QPointF(5, self.win.height()-5))
            rest = self.halves(button, split)
            self.assertNotEqual(rest[0], rest[1], 'active: both halves in distinct tones')
            self.point(button.mapToScene(QPointF(split/2, 3)))
            hovered = self.halves(button, split)
            self.assertNotEqual(hovered[0], rest[0])
            self.assertEqual(hovered[1], rest[1])
            self.point(button.mapToScene(QPointF(split+(button.width()-split)/2, 3)))
            arrow = self.halves(button, split)
            self.assertEqual(arrow[0], rest[0])
            self.assertNotEqual(arrow[1], rest[1])
            colours = tokens.property('colors')
            for name, key in (('splitCommandBase', 'press'), ('splitArrowBase', 'hover')):
                layer = next(i for i in items(ground) if i.objectName() == name)
                self.assertEqual(QColor(layer.property('color')), QColor(colours[key]))
            # Both pressed halves and an open menu use the common state machine.
            for x, down_name in ((split/2, 'commandDown'), (split+(button.width()-split)/2, 'arrowDown')):
                at = button.mapToScene(QPointF(x, button.height()/2))
                mouse(self.app, self.win, QEvent.MouseButtonPress, at, Qt.LeftButton, Qt.LeftButton)
                pump(50)
                self.assertTrue(ground.property(down_name))
                self.assertNotEqual(*self.halves(button, split)[:2])
                mouse(self.app, self.win, QEvent.MouseMove, QPointF(5, self.win.height()-5), Qt.NoButton, Qt.LeftButton)
                mouse(self.app, self.win, QEvent.MouseButtonRelease, QPointF(5, self.win.height()-5), Qt.LeftButton, Qt.NoButton)
            QQmlExpression(QQmlEngine.contextForObject(button), button, 'menu.open()').evaluate()
            pump(100)
            self.assertTrue(ground.property('menuOpen'))
            self.assertNotEqual(*self.halves(button, split)[:2])
            QQmlExpression(QQmlEngine.contextForObject(button), button, 'menu.close()').evaluate()
            button.setProperty('checked', False)
            pump(80)
        tokens.configure({'theme': 'light'})

    def test_no_hand_drawn_split_in_qml(self):
        for path in QML.rglob('*.qml'):
            text = path.read_text(encoding='utf-8')
            self.assertNotRegex(text, r'property\s+bool\s+arrow\s*:',
                                'unused hand-drawn arrow variants must not bypass SplitButton')
            self.assertNotRegex(text, r'(?:mouse|point|event)\.x\s*(?:>=|>)\s*[^\n;]*(?:arrow|split)',
                                'hit testing of split halves belongs to the common control')
            if 'arrowFrom' in text or 'property bool arrowed' in text or re.search(r'\bSplitButton\s*\{', text):
                with self.subTest(path=str(path.relative_to(QML))):
                    self.assertRegex(text, r'\bSplitButton\s*\{', 'split actions use the common component')
                    self.assertNotIn('ShapePath', text, 'the arrow comes from the common control')

    def test_compact_menu_gestures_keep_their_commands(self):
        self.win.showPhase('model')
        self.host.shell.trigger('view_plan')
        pump(300)
        for command in ('background', 'sun_map'):
            button = self.find('planView-' + command)
            ground = self.find(button.objectName() + 'Ground')
            self.assertIsNotNone(ground, 'the view action uses the shared split control')
            split = ground.property('split')
            previous = self.host.sun_map.sun.on
            for x in ((split/2, button.width()-4) if command == 'background' else (button.width()-4,)):
                pump(450)
                at = button.mapToScene(QPointF(x, button.height()/2))
                click(self.app, self.win, at)
                wait_for(lambda ground=ground: ground.property('menuOpen'), 5)
                self.assertEqual(self.host.sun_map.sun.on, previous, 'opening the panel toggles no solar map')
                if command == 'sun_map':
                    panel = self.find('sunMapPanel')
                    at_panel = panel.mapToScene(QPointF(0, 0))
                    at_button = button.mapToScene(QPointF(0, button.height()))
                    self.assertLess(abs(at_panel.y()-at_button.y()), 30, 'the panel is attached below its button')
                    self.assertLess(abs(at_panel.x()-at_button.x()), 30, 'the panel follows the whole button')
                click(self.app, self.win, at)
                wait_for(lambda ground=ground: not ground.property('menuOpen'), 5)
            if command == 'sun_map':
                at = button.mapToScene(QPointF(split/2, button.height()/2))
                click(self.app, self.win, at)
                self.assertNotEqual(self.host.sun_map.sun.on, previous, 'the command toggles the solar map')
                self.assertFalse(ground.property('menuOpen'))
                click(self.app, self.win, at)
                self.assertEqual(self.host.sun_map.sun.on, previous)


if __name__ == '__main__':
    unittest.main()
