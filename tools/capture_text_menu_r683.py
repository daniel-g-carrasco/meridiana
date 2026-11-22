"""Synthetic offscreen text menus, including a dialog and the floating assistant."""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tests'), str(ROOT / 'src')]

import _setup
from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtTest import QTest

from meridiana import i18n
from meridiana.app.platform.config import Config
from meridiana.gui.backend.assistant import build_page
from meridiana.gui.backend.assistant_chat import AssistantChat
from quick.aiuti.text_scene import TextScene
from quick.meridio.support import Host, KeyStore, Provider, Voice


def save(window, path):
    if path.exists():
        raise FileExistsError(path)
    ratio = window.devicePixelRatio()
    result = window.contentItem().grabToImage()
    ready = []
    result.ready.connect(lambda: ready.append(True))
    if not _setup.wait_for(lambda: ready, 5000):
        raise RuntimeError('Offscreen capture timed out')
    if not result.saveToFile(str(path)):
        raise RuntimeError('Offscreen capture could not be saved')
    print(path.name, result.image().size(), 'DPR', ratio)


def background(engine, window):
    component = QQmlComponent(engine)
    component.setData(b'import QtQuick\nimport Meridiana.Theme\nRectangle { color: Theme.colors.window; z: -1000 }', QUrl())
    item = component.create()
    if item is None:
        raise RuntimeError(str(component.errors()))
    item.setParent(engine)
    item.setParentItem(window.contentItem())
    item.setWidth(window.width())
    item.setHeight(window.height())
    engine._capture_background = item, component


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('theme', choices=('light', 'dark'))
    args = parser.parse_args()
    if os.environ.get('QT_QPA_PLATFORM') != 'offscreen':
        raise RuntimeError('Use the offscreen platform')
    scale = os.environ.get('QT_SCALE_FACTOR', '1')
    i18n.setup('it')
    case = TextScene()
    try:
        root, window = case.scene('TextArea')
        engine = root.parent()
        engine._meridiana_theme_tokens.configure(dict(theme=args.theme, textSize='large', reducedMotion=True))
        i18n.setup('it')
        window.resize(900, 650)
        background(engine, window)
        root.setPosition(__import__('PySide6.QtCore', fromlist=['QPointF']).QPointF(580, 600))
        root.forceActiveFocus()
        case.evaluate(root, 'select(0, 5)')
        QTest.mouseClick(window, Qt.RightButton, pos=QPoint(605, 612))
        QTest.qWait(250)
        save(window, args.folder / f'edge-{args.theme}-{scale}.png')
    finally:
        case.doCleanups()

    case = TextScene()
    try:
        root, window = case.scene('TextArea', '''M.Dialog { id: form; title: "Synthetic form";
            implicitWidth: 450; rejectText: "Close"; acceptOnReturn: false
            M.TextField { id: field; width: parent.width; text: "Synthetic selected text" }
        }''')
        root.parent()._meridiana_theme_tokens.configure(dict(theme=args.theme, textSize='large', reducedMotion=True))
        root.setProperty('bare', True)
        root.setProperty('text', '')
        background(root.parent(), window)
        case.evaluate(root, 'form.open()')
        QTest.qWait(250)
        case.evaluate(root, 'field.forceActiveFocus(); field.select(0,9); field.handleTextKey({key: Qt.Key_F10, modifiers: Qt.ShiftModifier, accepted: false})')
        QTest.qWait(250)
        save(window, args.folder / f'dialog-{args.theme}-{scale}.png')
    finally:
        case.doCleanups()

    app = _setup.quick_app()
    chat = AssistantChat(Host(), Config(assistant_introduced=True, assistant_local_model='fake'),
                         key_store=KeyStore(), voice=Voice())
    provider = Provider()
    chat.make_local = lambda: provider
    engine, window, theme = build_page(chat=chat, options=dict(theme=args.theme, textSize='large', reducedMotion=True))
    try:
        chat.setMotion(False)
        chat.view.answer('A synthetic answer with **bold text**, accents and a list:\n\n- first value: 12.5 kW\n- second value: 8 kW')
        QTest.qWait(300)
        def find_message():
            pending = [window.contentItem()]
            while pending:
                item = pending.pop()
                if item.objectName() == 'conversationMessage':
                    return item
                pending.extend(item.childItems())
            return None
        _setup.wait_for(lambda: find_message() is not None, 3000)
        message = find_message()
        if message is None:
            raise RuntimeError('The synthetic assistant message is missing')
        case.evaluate(message, 'forceActiveFocus(); select(0, 11); handleTextKey({key: Qt.Key_F10, modifiers: Qt.ShiftModifier, accepted: false})')
        QTest.qWait(250)
        save(window, args.folder / f'meridio-{args.theme}-{scale}.png')
    finally:
        chat.close()
        window.close()
        engine.deleteLater()
        app.processEvents()


if __name__ == '__main__':
    main()
