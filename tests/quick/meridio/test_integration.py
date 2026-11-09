"""The bottom Meridio command talks through the real workbench's session."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from shiboken6 import delete

from _fixtures import capannone_rho
import _setup
from _setup import wait_until
from meridiana.quick.app import QuickWindow, create_app
from quick.meridio.support import KeyStore, Provider, Voice


class IntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='r13-meridio-')
        self.addCleanup(temp.cleanup)
        with patch('meridiana.quick.backend.assistant_chat.keys', KeyStore()), \
                patch('meridiana.ui.voice.Voice', return_value=Voice()):
            self.host = QuickWindow(capannone_rho(), Path(temp.name), real_views=True,
                                    theme={'reducedMotion': True})
        self.window = self.host.window
        if self._testMethodName == 'test_first_frameless_exposure_keeps_character_at_home':
            self.window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(self.window))
        QTest.qWait(150)
        def close():
            self.host.close()
            delete(self.host.engine)
        self.addCleanup(close)

    def test_bottom_command_streams_and_edits_the_live_session_only_on_apply(self):
        self.assertIn('assistant', self.host.parts.controllers,
                      'Meridio must be installed by the real parts registry')
        chat = self.host.parts.controllers['assistant']
        chat.cfg.assistant_local_model = 'fake'
        chat.cfg.assistant_introduced = True
        fake = Provider(text='**Il progetto è quello aperto.**')
        chat.make_local = lambda: fake
        self.host.shell.trigger('assistant')
        layer = self.window.findChild(QObject, 'assistantLayer')
        # opened, and the question focused (that comes a turn later): waited for, not 100 ms fixed (r23-f8)
        _setup.wait_for(lambda: layer.property('opened') and bool(layer.findChild(QObject, 'assistantQuestion'))
                        and layer.findChild(QObject, 'assistantQuestion').hasActiveFocus(), 5000)
        self.assertTrue(layer.property('opened'))
        field = layer.findChild(QObject, 'assistantQuestion')
        self.assertTrue(field.hasActiveFocus(), 'Opening Meridio must focus the question, as in Widgets')
        for char in 'ciao':
            QTest.keyClick(self.window, char)
        QTest.keyClick(self.window, Qt.Key.Key_Return)
        self.assertTrue(wait_until(self.app, lambda: bool(fake.requests) and not chat.busy, 5))
        self.assertIs(chat.host.project, self.host.bridge.session.project)
        self.assertIn('progetto', chat.messages[-1]['bodyHtml'])
        from meridiana.assistant.tools import Proposal
        before = chat.host.project.name
        chat._show_proposal(Proposal('rename', 'Rename', 'site', '', [('name', before, 'R13')],
                                    change=lambda project: setattr(project, 'name', 'R13')))
        self.assertEqual(chat.host.project.name, before)
        chat.cardAction(chat.cards[-1]['id'], 'apply')
        self.assertEqual(self.host.bridge.session.project.name, 'R13')
        self.host.bridge.undo()
        self.assertEqual(chat.host.project.name, before)
        self.assertEqual(self.host.warnings, [])

    def test_properties_help_avoids_panel_and_escape_returns_position(self):
        self.assertIn('assistant', self.host.parts.controllers)
        layer = self.window.findChild(QObject, 'assistantLayer')
        self.assertTrue(wait_until(self.app, lambda: not layer.property('relocating'), 2))
        before = (layer.property('avatarX'), layer.property('avatarY'))
        from quick.gestures import item
        button = item(self.window, 'section-help:site')
        self.assertTrue(button.isVisible())
        p = button.mapToScene(QPointF(button.width()/2, button.height()/2))
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, pos=QPoint(round(p.x()), round(p.y())))
        _setup.wait_for(lambda: layer.property('page') == 'help' and layer.property('opened'), 5000)
        self.assertEqual(layer.property('page'), 'help')
        self.assertTrue(layer.property('opened'))
        QTest.keyClick(self.window, Qt.Key.Key_Escape)
        self.assertFalse(layer.property('opened'))
        self.assertTrue(wait_until(self.app, lambda: not layer.property('relocating'), 2))
        self.assertEqual((layer.property('avatarX'), layer.property('avatarY')), before)
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, pos=QPoint(round(p.x()), round(p.y())))
        QTest.qWait(100)
        close = self.window.findChild(QObject, 'assistantHelpClose')
        at = close.mapToScene(QPointF(close.width()/2, close.height()/2))
        QTest.mouseClick(self.window, Qt.MouseButton.LeftButton, pos=at.toPoint())
        self.assertTrue(wait_until(self.app, lambda: not layer.property('relocating'), 2))
        self.assertFalse(layer.property('opened'))
        self.assertEqual((layer.property('avatarX'), layer.property('avatarY')), before)
        self.assertEqual(self.host.warnings, [])

    def test_docked_conversation_is_a_real_panel_and_help_stays_there(self):
        self.host.shell.trigger('assistant')
        layer = self.window.findChild(QObject, 'assistantLayer')
        layer.setProperty('docked', True)
        QTest.qWait(80)
        panel = self.window.findChild(QObject, 'assistantDockPanel')
        self.assertIsNotNone(panel, 'Docking must use the workbench panel system')
        self.assertTrue(panel.isVisible())
        bubble = layer.findChild(QObject, 'assistantBubble')
        self.assertIs(bubble.parentItem(), panel.property('assistantSpace'))
        self.window.resize(1366, 900)
        _setup.wait_for(lambda: (bubble.x(), bubble.y()) == (0, 0) and bubble.width() <= bubble.parentItem().width() and bubble.height() <= bubble.parentItem().height(), 5000)
        self.assertEqual((bubble.x(), bubble.y()), (0, 0))
        self.assertLessEqual(bubble.width(), bubble.parentItem().width())
        self.assertLessEqual(bubble.height(), bubble.parentItem().height())
        before = (bubble.x(), bubble.y(), bubble.width(), bubble.height())
        panel.property('workspace').selectPanel('properties')
        _setup.wait_for(lambda: not panel.isVisible(), 5000)
        self.assertFalse(panel.isVisible())
        self.host.parts.controllers['assistant_help'].request('site')
        _setup.wait_for(lambda: panel.isVisible(), 5000)
        self.assertTrue(panel.isVisible(), 'Help must select its dock even if it was already open behind Properties')
        self.assertEqual((bubble.x(), bubble.y(), bubble.width(), bubble.height()), before)
        self.assertTrue(layer.property('docked'))
        self.assertEqual(self.host.warnings, [])

    def test_reexposed_window_keeps_character_at_its_home(self):
        # R500 (R155): placed once at his home; a window shown again and made larger leaves him where he is
        layer = self.window.findChild(QObject, 'assistantLayer')
        home = layer.property('homeRect')
        before = (layer.property('avatarX'), layer.property('avatarY'))
        self.assertAlmostEqual(before[0], home.x()+home.width()-58, delta=1)
        self.assertAlmostEqual(before[1], home.y()+home.height()-90, delta=1)
        self.window.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.window.show()
        self.window.resize(1600, 960)
        QTest.qWait(500)
        self.assertEqual((layer.property('avatarX'), layer.property('avatarY')), before)

    def test_first_frameless_exposure_keeps_character_at_home(self):
        layer = self.window.findChild(QObject, 'assistantLayer')
        QTest.qWait(500)
        home = layer.property('homeRect')
        self.assertAlmostEqual(layer.property('avatarX'), home.x()+home.width()-58, delta=1)
        self.assertAlmostEqual(layer.property('avatarY'), home.y()+home.height()-90, delta=1)
        layer.setProperty('bubbleHeight', 600)
        layer.open()
        QTest.qWait(100)
        self.assertGreaterEqual(layer.property('bubbleY'), home.y())

    def test_tour_remains_visible_in_file_and_visits_every_step_without_editing(self):
        before = self.host.bridge.session.project.to_json()
        self.host.shell.trigger('guided_tour')
        layer = self.window.findChild(QObject, 'assistantLayer')
        service = self.host.parts.controllers['assistant_help']
        for index in range(service.tourStep['total']):
            service.goToStep(index)
            QTest.qWait(60)
            self.assertTrue(layer.isVisible(), service.tourStep['id'])
            self.assertEqual(layer.property('page'), 'tour')
            self.assertIsNotNone(layer.property('highlightItem'), service.tourStep['id'])
        service.next()
        self.assertFalse(service.tourActive)
        self.assertTrue(self.window.property('fileOpen'))
        self.assertEqual(self.host.bridge.session.project.to_json(), before)

    def test_settings_and_navigation_use_the_live_profile_and_remember_phase_positions(self):
        chat = self.host.parts.controllers['assistant']
        settings = self.host.parts.controllers['settings']
        layer = self.window.findChild(QObject, 'assistantLayer')
        self.assertGreater(layer.property('homeRect').x(), 0)
        self.assertGreater(layer.property('homeRect').y(), 0)
        self.assertIs(chat.cfg, self.host.cfg)
        self.assertTrue(settings.setValue('assistant_style', 'pixel'))
        self.assertEqual(layer.property('characterStyle'), 'pixel')
        self.assertTrue(settings.setValue('assistant_animated', False))
        self.assertFalse(layer.property('animated'))
        layer.setProperty('avatarX', 120)       # where a drag leaves him, then saved (R500: for every phase)
        layer.setProperty('avatarY', 310)
        chat.host.placement(120, 310, 360, 600, False, layer.width(), layer.height(), False)
        self.assertTrue(chat.host.state_file.exists())
        self.assertEqual(len({tuple(place) for place in chat.host.places.values()}), 1)
        self.window.showPhase('production')
        QTest.qWait(80)
        self.assertEqual((layer.property('avatarX'), layer.property('avatarY')), (120, 310))
        self.window.showPhase('plant')
        QTest.qWait(80)
        self.window.showPhase('model')
        QTest.qWait(80)
        self.assertEqual((layer.property('avatarX'), layer.property('avatarY')), (120, 310))
        self.assertTrue(chat.host.local_assistant_command('Come mi muovo in 3D?'))
        self.assertIn('AutoCAD', chat.messages[-1]['text'])
        chat.requestPreferences()
        _setup.wait_for(lambda: bool(self.window.property('fileOpen')), 5000)
        self.assertTrue(self.window.property('fileOpen'))
        self.assertEqual(settings.section, 'assistant')
        self.assertEqual(self.host.warnings, [])

    def test_r320_show_view_is_the_real_phase_without_the_bubble(self):
        chat = self.host.parts.controllers['assistant']
        chat.cfg.assistant_local_model = 'fake'
        self.host.shell.trigger('assistant')
        QTest.qWait(80)
        picture = chat.host.view_image()
        self.assertFalse(picture.isNull())
        central = self.window.findChild(QObject, 'centralPanel')
        self.assertEqual(picture.width(), round(central.width()*picture.devicePixelRatio()))
        chat.showView()
        self.assertTrue(wait_until(self.app, lambda: bool(chat.attachments), 5))
        self.assertTrue(any(row.get('thumbnail') for row in chat.cards))
        self.assertTrue(self.window.findChild(QObject, 'assistantLayer').property('opened'))
