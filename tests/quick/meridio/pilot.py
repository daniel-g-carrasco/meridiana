"""Meridio journey on both real windows, with one synthetic provider and no OS input."""
from pathlib import Path
import sys
from unittest.mock import patch

from PySide6.QtCore import QObject, QPointF
from PySide6.QtQml import qmlEngine
from PySide6.QtTest import QTest

from quick.meridio.capture import ANSWER
from quick.meridio.support import KeyStore, Provider, Voice

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools'))
import quick_pilot as pilot  # noqa: E402

original_find, original_perform, original_run = pilot.find_target, pilot.perform, pilot.run
chat = None


def find_target(window, text, engine):
    names = {'provider': ('where_button', 'assistantProvider'), 'question': ('field', 'assistantQuestion'),
             'dock': ('dock_button', 'assistantDock'), 'close': ('close_button', 'assistantClose'),
             'suggestions': ('questions_title', 'assistantSuggestions'), 'view': ('view_button', 'assistantShowView')}
    if text in names:
        if engine == 'widgets':
            obj = getattr(window.assistant, names[text][0])
            return obj, QPointF(obj.rect().center())
        obj = window.findChild(QObject, names[text][1])
        if obj is None or not obj.isVisible():
            raise AssertionError('No visible assistant control: ' + text)
        return window, obj.mapToScene(QPointF(obj.width()/2, obj.height()/2))
    return original_find(window, text, engine)


def _perform(app, window, engine, step, last):
    global chat
    if chat is None:
        chat = window.assistant_chat if engine == 'widgets' else qmlEngine(window).rootContext().contextProperty('assistantChat')
        chat.cfg.assistant_introduced = True
        chat.cfg.assistant_local_model = 'test-model'
        chat.make_local = lambda: Provider(text=ANSWER)
        if engine == 'widgets':
            window.assistant.set_bubble_size(360, 600)
        else:
            layer = window.findChild(QObject, 'assistantLayer')
            layer.setProperty('bubbleWidth', 360)
            layer.setProperty('bubbleHeight', 600)
    if step['action'] == 'type':
        target, _ = find_target(window, 'question', engine)
        QTest.keyClicks(target, step['text']) if engine == 'widgets' else [QTest.keyClick(target, c) for c in step['text']]
        return last
    if step['action'] == 'key':
        from PySide6.QtGui import QKeySequence
        key = QKeySequence(step['key'])[0]
        target = (app.focusWidget() or window) if engine == 'widgets' else window
        QTest.keyClick(target, key.key(), key.keyboardModifiers())
        return last
    return original_perform(app, window, engine, step, last)


def perform(app, window, engine, step, last):
    last = _perform(app, window, engine, step, last)
    pilot.pump(step.get('wait', 400))
    avatar = window.assistant if engine == 'widgets' else window.findChild(QObject, 'assistantLayer')
    if engine == 'quick' and step.get('home'):
        center = QPointF(avatar.property('avatarX')+23, avatar.property('avatarY')+23)
        if not avatar.property('homeRect').contains(center):
            raise AssertionError(f'Meridio started outside the central panel: {center}')
    for key, expected in step.get('assistant', {}).items():
        actual = getattr(avatar, key) if engine == 'widgets' else avatar.property(key)
        if actual != expected:
            raise AssertionError(f'{engine} {step}: assistant.{key}={actual!r}, expected {expected!r}')
    return last


def run(args, journey):
    with patch('meridiana.ui.assistant_chat.keys', KeyStore()), \
            patch('meridiana.quick.backend.assistant_chat.keys', KeyStore()), \
            patch('meridiana.ui.voice.Voice', return_value=Voice()):
        original_run(args, journey)


pilot.find_target, pilot.perform, pilot.run = find_target, perform, run

if __name__ == '__main__':
    pilot.__file__ = __file__
    pilot.main()
