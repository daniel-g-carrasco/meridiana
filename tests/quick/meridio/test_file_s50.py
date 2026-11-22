"""Study 50, phase 0 (Daniel 15/11/2026: «Non amo neanche il fatto che meridio non sia presente nelle impostazioni e in
file: anche lì potrebbe dare una mano»).

Meridio was hidden while the File page (and the Settings, a mode of it) was open: one line of AssistantHost.qml, a
remedy of 03/11 (R347, R370) for his bubble caught in the picture of File's transition, a picture that is no longer
taken. With it, four buttons did nothing: the status bar's «Meridio», «Ask Meridio» in a help bubble, Meridio taking
the designer to a setting (he vanished), the highlight promised by `go_to` (on only in the tour). Here: he is there
over File and the Settings, the four work, docked he floats while File is open (D9), his words say where one is, his
questions ready are File's and the Settings', and the page's fade comes under him, not over him.
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QMetaObject, QObject, QPointF, Qt
from PySide6.QtGui import QColor

from _fixtures import capannone
from meridiana.app import jobs
from meridiana.gui.application import QuickWindow, create_app
from quick.gestures import click, item, point, pump, wait_for
from quick.meridio.support import KeyStore, Provider, Voice
from quick.aiuti.avvisi import real


def find(window, name):
    """An item by name from the window's own root: Meridio's stage is in Qt's overlay, beside the content."""
    top = window.contentItem()
    while top.parentItem() is not None:
        top = top.parentItem()
    pending = [top]
    while pending:
        node = pending.pop()
        if node.objectName() == name:
            return node
        pending.extend(node.childItems())
    raise AssertionError('Missing Quick item: ' + name)


class Base(unittest.TestCase):
    reduced = True

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(self.temp.cleanup)
        with patch('meridiana.gui.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.gui.backend.voice.Voice', return_value=Voice()):
            self.host = QuickWindow(capannone(), Path(self.temp.name), real_views=True,
                                    theme={'theme': 'light', 'reducedMotion': self.reduced})
        win = self.window = self.host.window
        win.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        win.show()
        win.resize(1600, 960)
        results, keys, _ = jobs.layout_of(self.host.bridge.session.project)
        self.host.bridge.accept_layout(self.host.bridge.session.generation, results, keys)
        pump(300)
        wait_for(lambda: self.window.findChild(QObject, 'assistantLayer') is not None, 10)
        self.layer = self.window.findChild(QObject, 'assistantLayer')
        self.chat = self.host.parts.controllers['assistant']
        self.chat.cfg.assistant_introduced = True
        self.addCleanup(self.close)

    def close(self):
        warnings = real(self.host.warnings)
        self.host.close()
        self.app.processEvents()
        self.assertEqual(warnings, [])

    def open_file(self, section='open'):
        self.host.parts.controllers['files'].selectSection(section)
        self.window.setProperty('fileOpen', True)
        wait_for(lambda: find(self.window, 'filePage').isVisible(), 5)
        pump(150)

    def bubble_shown(self):
        bubble = find(self.window, 'assistantBubble')
        return self.layer.isVisible() and bubble.isVisible() and bubble.property('opacity') > 0.99

    def assert_there(self, what):
        wait_for(lambda: self.layer.property('opened'), 5)
        pump(150)
        self.assertTrue(self.layer.isVisible(), f'{what}: his layer hidden over File')
        self.assertTrue(self.bubble_shown(), f'{what}: the conversation opened unseen')



class MeridioOverFileTest(Base):
    # -- the four buttons that did nothing (study 50, 2.3) --------------------------------------------------------
    def test_the_status_bar_button_opens_him_over_file(self):
        self.open_file()
        self.assertTrue(find(self.window, 'assistantCharacter').isVisible(), 'File open: the character hidden')
        click(self.app, self.window, point(item(self.window, 'statusMeridio')))
        self.assert_there('«Meridio» of the status bar')

    def test_ask_meridio_of_a_help_bubble_opens_him_over_the_settings(self):
        self.open_file('preferences:appearance')
        self.host.parts.controllers['help'].ask('phase.model')
        self.assert_there('«Ask Meridio»')
        self.assertTrue(self.chat.draft, 'the help\'s question is in his field')

    def test_taken_to_a_setting_he_stays_and_the_setting_is_lit(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        self.assertTrue(self.chat.host.go_to(['setting', 'appearance.theme']))
        wait_for(lambda: bool(self.window.property('fileOpen')), 5)
        self.assert_there('go_to a setting')
        lit = self.layer.property('highlightItem')
        self.assertIsNotNone(lit, 'no highlight on the setting')
        self.assertEqual(lit.objectName(), 'settingsRow_theme')
        self.assertTrue(lit.isVisible())
        spot = find(self.window, 'assistantSpotlight')
        wait_for(lambda: spot.isVisible() and spot.property('opacity') > 0.99, 5)

    def test_taken_to_a_section_the_section_s_entry_is_lit(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        self.assertTrue(self.chat.host.go_to(['settings', 'privacy']))
        wait_for(lambda: self.layer.property('highlightItem') is not None, 5)
        self.assertEqual(self.layer.property('highlightItem').objectName(), 'fileNav_privacy')
        self.assert_there('go_to a section')

    def test_the_highlight_of_go_to_is_on_outside_the_tour_too(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        self.assertFalse(self.layer.property('temporary'))
        self.chat.host.go_to(['phase', 'plant'])
        spot = find(self.window, 'assistantSpotlight')
        wait_for(lambda: spot.isVisible() and spot.property('opacity') > 0.99, 5)
        self.assertEqual(self.layer.property('highlightItem').objectName(), 'plantTab')
        # the conversation closed, the highlight goes with it
        QMetaObject.invokeMethod(self.layer, 'dismiss')
        wait_for(lambda: not spot.isVisible(), 5)

    # -- D9: docked, with File open he floats -------------------------------------------------------------------
    def test_docked_he_floats_while_file_is_open_and_is_the_tab_again_after(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.layer.property('opened'), 5)
        click(self.app, self.window, point(find(self.window, 'assistantDock')))
        dock = find(self.window, 'assistantDockPanel')
        wait_for(lambda: dock.isVisible(), 5)
        bubble = find(self.window, 'assistantBubble')
        self.open_file('preferences:assistant')
        self.assertTrue(self.bubble_shown(), 'docked, File open: the conversation nowhere')
        self.assertIsNot(bubble.parentItem(), dock.property('assistantSpace'))
        self.assertTrue(find(self.window, 'assistantCharacter').isVisible(), 'floating: the character beside it')
        self.assertTrue(self.layer.property('docked'), 'still docked: only shown floating')
        self.window.setProperty('fileOpen', False)
        wait_for(lambda: dock.isVisible(), 5)
        wait_for(lambda: bubble.parentItem() is dock.property('assistantSpace'), 5)
        self.assertFalse(find(self.window, 'assistantCharacter').isVisible())

    # -- where he is, in his words and in the question ----------------------------------------------------------
    def test_his_words_say_where_one_is(self):
        from meridiana.i18n import _
        self.open_file('preferences:appearance')
        place = self.chat.host.place_title()
        self.assertEqual(place, ', '.join((_('File'), _('Settings'), _('Appearance'))))
        self.assertIn(place, self.chat.property('contextLine'))
        self.host.parts.controllers['files'].selectSection('export')
        pump(50)
        self.assertEqual(self.chat.host.place_title(), ', '.join((_('File'), _('Export'))))
        self.window.setProperty('fileOpen', False)
        pump(50)
        self.assertEqual(self.chat.host.place_title(), self.chat.host.phase_title())
        self.assertEqual(self.chat.host.place(), self.chat.host.phase())

    def test_the_question_carries_the_place(self):
        fake = Provider(text='Ok.')
        self.chat.make_local = lambda: fake
        self.chat.cfg.assistant_local_model = 'fake'
        self.open_file('preferences:keyboard')
        self.chat.ask('Come cambio un tasto?')
        wait_for(lambda: bool(fake.requests) and not self.chat.busy, 5)
        sent = str(fake.requests[-1][1])
        self.assertIn(self.chat.host.place_title(), sent)

    # -- his surfaces keep the pointer over File too (R570) -----------------------------------------------------
    def test_a_click_on_him_over_a_file_entry_is_his(self):
        self.open_file()
        entry = find(self.window, 'fileNav_export')
        at = entry.mapToItem(self.layer, entry.width() / 2, entry.height() / 2)
        self.layer.setProperty('avatarX', at.x() - 23)
        self.layer.setProperty('avatarY', at.y() - 23)
        pump(100)
        files = self.host.parts.controllers['files']
        click(self.app, self.window, point(entry))
        pump(100)
        self.assertEqual(files.section, 'open', 'the click on Meridio went to the File entry under him')
        self.assertTrue(self.layer.property('opened'), 'a click on him opens him')


class MeridioThroughFileFadeTest(Base):
    """With motion on: the page's fade (fileTransition, the window's ground fading out over the new page) comes under
    him and his bubble, which stay as they are: they neither blink out nor fade in with the page (R347, R370)."""
    reduced = False

    def ink(self, image, item_, dx, dy):
        p = item_.mapToScene(QPointF(item_.width() * dx, item_.height() * dy))
        dpr = image.devicePixelRatio()
        return QColor(image.pixelColor(int((p.x() + 0.5) * dpr), int((p.y() + 0.5) * dpr)))

    def test_opening_and_closing_file_he_and_his_bubble_stay_drawn(self):
        self.host.shell.trigger('assistant')
        wait_for(lambda: self.bubble_shown(), 5)
        pump(400)
        bubble, character = find(self.window, 'assistantBubble'), find(self.window, 'assistantCharacter')
        veil = find(self.window, 'fileTransition')
        marks = [(character, .5, .5), (bubble, .5, .08), (bubble, .5, .5)]
        # he changes place with the page (on File's free side, test_fianco_file), and moved he wakes (his gaze, his
        # body: Character.wake): still, as with «Meridio animated» off, what he looks like at each frame of the fade
        # is compared with how he looks once it is over
        self.layer.setProperty('animated', False)
        pump(200)
        for opened in (True, False):
            self.window.setProperty('fileOpen', opened)
            frames = []
            for _ in range(60):
                pump(8)
                if not veil.isVisible():
                    continue
                frame = self.window.grabWindow()
                frames.append([self.ink(frame, *m) for m in marks])
            self.assertGreater(len(frames), 0, 'the fade was never seen: the test proves nothing')
            wait_for(lambda: not veil.isVisible(), 5)
            pump(200)
            after = self.window.grabWindow()
            expected = [self.ink(after, *m) for m in marks]
            for colours in frames:
                for (what, *_where), now, colour in zip(marks, colours, expected, strict=True):
                    self.assertLess(max(abs(now.red() - colour.red()), abs(now.green() - colour.green()),
                                        abs(now.blue() - colour.blue())), 24,
                                    f'File {"opening" if opened else "closing"}: {what.objectName()} faded with the page')


if __name__ == '__main__':
    unittest.main()
