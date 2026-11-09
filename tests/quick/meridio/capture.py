"""Real Windows captures with an actual Widgets assistant beside the Quick port.

Run with PYTHONPATH=tests;src and QT_SCALE_FACTOR=1 or 2. No external model,
keyring, user configuration or project is read. --full includes MainWindow.
"""
import argparse
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import _setup
from PySide6.QtCore import QObject, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget
from shiboken6 import delete

from meridiana.config import Config
from meridiana.i18n import setup
from meridiana.quick.backend.assistant import build_page
from meridiana.quick.backend.assistant_chat import AssistantChat
from meridiana.ui.assistant import Assistant
from meridiana.ui.theme import Theme
from quick.meridio.support import Host, KeyStore, Provider, Voice

QUESTION = 'Come verifichi una stringa?'
ANSWER = ('**Le verifiche della stringa**\n\n'
          'Controllo tensione e corrente con gli stessi strumenti del progetto.\n\n'
          'N_max = floor(V_max / Voc_cold)\n\n'
          '- Tensione a freddo entro il limite dell’inverter.\n'
          '- Corrente e MPPT verificati nelle condizioni di progetto.\n\n'
          'Ogni risultato mantiene la propria fonte.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--theme', default='light', choices=('light', 'dark'))
    parser.add_argument('--page', default='conversation', choices=('conversation', 'help', 'manual', 'tour', 'setup', 'rich', 'table', 'provider'))
    parser.add_argument('--large', action='store_true')
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--docked', action='store_true')
    parser.add_argument('--out', type=Path, default=Path('build/quick-foto/meridio'))
    args = parser.parse_args()
    answer = ANSWER if args.page not in ('rich', 'table') else '**Confronto dei moduli**\n\n| Modulo | Potenza |\n| --- | --- |\n| A | 450 W |\n| B | 470 W |\n\nLa scheda allegata resta da verificare.'
    app = QApplication.instance() or QApplication(['meridio-capture'])
    setup('it')
    cfg = Config(theme=args.theme, accent='indigo', backgrounds='grey', font='plex',
                 text_size='large' if args.large else 'medium', background='none', network_pvgis=False,
                 assistant_introduced=True, assistant_local_model='test-model', assistant_animated=False)
    temporary = tempfile.TemporaryDirectory(prefix='meridio-photo-')
    options = dict(theme=args.theme, textSize=cfg.text_size, reducedMotion=True)
    host = None
    if args.full:
        from _fixtures import capannone_rho
        from meridiana import config, jobs
        from meridiana.quick.app import QuickWindow, create_app
        from meridiana.paths import Paths
        create_app()
        cache = Path(temporary.name)
        paths = Paths(*(cache / 'quick-profile' / name for name in ('config', 'state', 'data', 'cache')))
        config.save(cfg, paths.config_file)
        with patch('meridiana.quick.backend.assistant_chat.keys', KeyStore()), patch('meridiana.ui.voice.Voice', return_value=Voice()):
            host = QuickWindow(capannone_rho(), cache, real_views=True, theme=options)
        engine, quick = host.engine, host.window
        results, keys, _ = jobs.layout_of(host.bridge.session.project)
        host.bridge.accept_layout(host.bridge.session.generation, results, keys)
        chat = host.parts.controllers['assistant']
        quick.resize(args.width, args.height)
        quick.show()
        host.shell.trigger('assistant')
    else:
        chat = AssistantChat(Host(), cfg, key_store=KeyStore(), voice=Voice())
        engine, quick, _tokens = build_page('conversation' if args.page == 'rich' else args.page, options=options, width=args.width, height=args.height, chat=chat)
    fake = Provider(text=answer)
    chat.make_local = lambda: fake
    if not QTest.qWaitForWindowExposed(quick):
        raise RuntimeError('The Quick window was not exposed before the conversation')
    QTest.qWait(150)
    chat.ask(QUESTION)
    if not _setup.wait_until(app, lambda: not chat.busy, 5):
        raise RuntimeError('The fake provider did not finish')
    layer = quick.findChild(QObject, 'assistantLayer')
    if not args.full:
        layer.setProperty('avatarX', args.width - 100)
        layer.setProperty('avatarY', args.height - 90)
    layer.setProperty('bubbleWidth', 360)
    layer.setProperty('bubbleHeight', 600)
    case = unittest.TestCase()
    if args.full:
        from _fixtures import capannone_rho
        with patch('meridiana.ui.voice.Voice', return_value=Voice()), patch('meridiana.ui.assistant_chat.keys', KeyStore()):
            widgets = _setup.window(case, capannone_rho(), cfg=cfg, size=(args.width, args.height))
        avatar = widgets.assistant
        avatar.reduced_motion = True
        avatar.set_bubble_size(360, 600)
        old_chat = widgets.assistant_chat
        old_chat.keys = KeyStore()
        old_chat.make_local = lambda: Provider(text=answer)
        avatar.open_panel()
        avatar.ask(QUESTION)
        if not _setup.wait_until(app, lambda: old_chat.job is None, 5):
            raise RuntimeError('The Widgets fake provider did not finish')
        if args.page == 'help':
            host.parts.controllers['assistant_help'].request('site')
            from meridiana.ui.help_box import HelpView
            reference = HelpView()
            reference.show_help('site')
            avatar.add_card(reference)
        elif args.page in ('setup', 'provider'):
            chat.showSetup()
            old_chat.show_setup()
            if args.page == 'provider':
                chat.cardAction(chat.cards[-1]['id'], 'configure')
                QTest.qWait(50)
                mode = quick.findChild(QObject, 'assistantSetupMode')
                mode.setProperty('currentIndex', 2)
                mode.activated.emit(2)
                old_chat.setup_card.mode.setCurrentIndex(2)
        elif args.page == 'tour':
            host.parts.controllers['assistant_help'].startTour(False)
            widgets._start_tour()
    else:
        look = Theme(cfg, app=app)
        widgets = QWidget()
        widgets.setWindowTitle('Meridio Widgets')
        widgets.resize(args.width, args.height)
        widgets.setAutoFillBackground(True)
        avatar = Assistant(widgets)
        avatar.set_colours(look.tokens)
        avatar.reduced_motion = True
        avatar.set_animated(False)
        avatar.set_bubble_size(360, 600)
        widgets.show()
        avatar.move(args.width - 100, args.height - 90)
        avatar.show()
        avatar.open_panel()
        from meridiana.ui.assistant_chat import Chat
        with patch('meridiana.ui.voice.Voice', return_value=Voice()), patch('meridiana.ui.assistant_chat.keys.get', return_value=''):
            old_chat = Chat(avatar, Host(), cfg)
        old_chat.keys = KeyStore()
        old_chat.make_local = lambda: Provider(text=answer)
        avatar.ask(QUESTION)
        if not _setup.wait_until(app, lambda: old_chat.job is None, 5):
            raise RuntimeError('The Widgets fake provider did not finish')
        if args.page == 'help':
            from meridiana.ui.help_box import HelpView
            reference = HelpView()
            reference.show_help('phase.production')
            avatar.add_card(reference)
        elif args.page == 'setup':
            old_chat.show_setup()
    if args.page == 'rich':
        picture = QImage(240, 120, QImage.Format.Format_RGB32)
        picture.fill(QColor('#586aa6'))
        pen = QPainter(picture)
        pen.setPen(Qt.GlobalColor.white)
        pen.drawText(QRect(10, 10, 220, 100), Qt.AlignmentFlag.AlignCenter, 'Immagine sintetica di prova')
        pen.end()
        chat.add_image(picture, 'Prova.png')
        old_chat.add_image(picture, 'Prova.png')
        if not _setup.wait_until(app, lambda: bool(chat.attachments) and bool(old_chat.attachments), 5):
            raise RuntimeError('The synthetic image was not prepared')
    if args.docked:
        layer.setProperty('docked', True)
        avatar.set_docked(True)
    quick.setFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
    widgets.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
    quick.show(); widgets.show()
    quick.resize(args.width, args.height); widgets.resize(args.width, args.height)
    if not QTest.qWaitForWindowExposed(quick) or not QTest.qWaitForWindowExposed(widgets.windowHandle()):
        raise RuntimeError('The real windows were not exposed')
    QTest.qWait(350)
    widgets.activateWindow()
    QTest.qWait(80)
    wshot = widgets.grab().toImage()
    wb = (avatar.panel if args.docked else avatar.bubble).grab().toImage()
    quick.requestActivate()
    QTest.qWait(80)
    qshot = quick.grabWindow()
    if qshot.isNull() or wshot.isNull():
        raise RuntimeError('A real capture is empty')
    folder = args.out
    folder.mkdir(parents=True, exist_ok=True)
    dpr = quick.effectiveDevicePixelRatio()
    name = f'{args.page}-{args.theme}-{args.width}x{args.height}-dpr{dpr:g}' + ('-large' if args.large else '') + ('-full' if args.full else '') + ('-docked' if args.docked else '')
    qshot.save(str(folder / (name + '-quick.png')))
    wshot.save(str(folder / (name + '-widgets.png')))
    # Keep original captures, plus a compact contact sheet for visual review.
    qsmall, wsmall = [pic.scaledToWidth(900, Qt.TransformationMode.SmoothTransformation) for pic in (qshot, wshot)]
    qsmall.setDevicePixelRatio(1)
    wsmall.setDevicePixelRatio(1)
    pair = QImage(1800, max(qsmall.height(), wsmall.height()) + 32, QImage.Format.Format_RGB32)
    pair.fill(QColor('#dedede'))
    painter = QPainter(pair)
    painter.setPen(QColor('#111111'))
    painter.drawText(QRect(12, 0, 870, 30), Qt.AlignmentFlag.AlignVCenter, 'Quick: ' + name)
    painter.drawText(QRect(912, 0, 870, 30), Qt.AlignmentFlag.AlignVCenter, 'Widgets: riferimento reale')
    painter.drawImage(0, 32, qsmall); painter.drawImage(900, 32, wsmall)
    painter.end()
    pair.save(str(folder / (name + '-pair.png')))
    bubble = layer.findChild(QObject, 'assistantBubble')
    from PySide6.QtCore import QPointF
    origin = bubble.mapToScene(QPointF(0, 0))
    qb = qshot.copy(QRect(round(origin.x()*dpr), round(origin.y()*dpr), round(bubble.width()*dpr), round(bubble.height()*dpr)))
    for kind, picture in [('quick', qb), ('widgets', wb)]:
        picture.save(str(folder / (name + '-' + kind + '-bubble.png')))
        picture.scaledToWidth(round(picture.width()/picture.devicePixelRatio()*2)).save(str(folder / (name + '-' + kind + '-200.png')))
    metadata = dict(page=args.page, theme=args.theme, width=args.width, height=args.height, dpr=dpr,
                    api=str(quick.rendererInterface().graphicsApi()), fakeRequests=len(fake.requests),
                    qmlWarnings=host.warnings if host else engine._assistant_diagnostics, full=args.full)
    metadata['actualSizes'] = {'quick': [quick.width(), quick.height()], 'widgets': [widgets.width(), widgets.height()]}
    metadata['geometry'] = {key: layer.property(key) for key in ('width', 'height', 'avatarX', 'avatarY', 'bubbleX', 'bubbleY', 'actualWidth', 'actualHeight', 'tail', 'tailOffset')}
    (folder / (name + '.json')).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(metadata, ensure_ascii=False))
    if host:
        host.close()
    else:
        quick.close()
    delete(engine)
    chat.close()
    if args.full:
        case.doCleanups()
    else:
        old_chat._gone()
        widgets.close()
        delete(widgets)
    temporary.cleanup()


if __name__ == '__main__':
    main()
