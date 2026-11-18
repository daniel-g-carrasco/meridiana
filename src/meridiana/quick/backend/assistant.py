"""Install and preview the autonomous Meridio Quick components.

Shell integration uses install_assistant(engine, chat=..., help_service=...).
The standalone preview never constructs a provider or reads the user's settings.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import unquote

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

from meridiana import assistant as core
from meridiana.i18n import _, language, setup
from meridiana.quick.backend.assistant_help import AssistantHelp
from meridiana.quick.backend.controls import install_controls

PAGES = ('meridio', 'conversation', 'help', 'manual', 'tour', 'setup', 'local')
QML = Path(__file__).resolve().parent.parent / 'qml' / 'Meridiana' / 'Assistant'


class CharacterProvider(QQuickImageProvider):
    """The authoritative core SVG; no paint callback during a Quick drag."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.requests = 0

    def requestImage(self, identifier, size, requestedSize):
        self.requests += 1
        style, parts, ink, accent, thinking, blink, expression, step, gx, gy = (identifier.split('/') + [''] * 10)[:10]
        params = dict(thinking=thinking == '1', blink=blink == '1', expression=expression, parts=parts)
        params['gaze'] = (int(gx or '0'), int(gy or '0'))
        if style == 'pixel':
            params['step'] = int(step or '0')
        svg = (core.pixel_svg if style == 'pixel' else core.svg)(unquote(ink), unquote(accent), **params)
        dimensions = requestedSize if requestedSize.isValid() else QSize(46, 46)
        image = QImage(dimensions, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        QSvgRenderer(QByteArray(svg.encode('utf-8'))).render(painter, QRectF(0, 0, dimensions.width(), dimensions.height()))
        painter.end()
        size.setWidth(dimensions.width())
        size.setHeight(dimensions.height())
        return image


def labels():
    result = dict(name=core.NAME, close=_('Close'), dock=_('Dock in the panels'),
                floating=_('Float over the views'), attach=_('Attach documents or images'), more=_('More of Meridio'),
                view=_('Show Meridio what I see'), send=_('Send'), stop=_('Stop'),
                voice=_('Read aloud'), question=_('Ask Meridio'), newChat=_('New conversation'),
                setup=_('Give Meridio a model'), manual=_('Manual'), tour=_('Guided tour'),
                suggestions=_('Suggested questions'), local=_('On this PC'),
                preview=_('This preview is not connected to a model.'),
                greeting=_('Hello, I am Meridio.'), properties=_('Properties'),
                provider=_('Provider'), model=_('Model'), endpoint=_('Server URL'), apiKey=_('API key'),
                save=_('Save'), account=_('Open provider account'), cloud=_('In the cloud'),
                discover=_('Find local models'), probe=_('Test connection'), useModel=_('Use this model'),
                ram=_('RAM (GB)'), reserved=_('Reserved project: never to the cloud'), cancel=_('Cancel'),
                withdraw=_('Withdraw consent'), preferences=_('Settings'),
                appearance=_('Appearance'), animated=_('Meridio animated'), style=_('Drawing'),
                smooth=_('Smooth'), pixel=_('Pixel'), width=_('Width'), height=_('Height'))
    result.update(attachShort=_('Attach…'), suggestionsTitle=_('Suggestions'),
                  questionPlaceholder=_('Ask {name}…').format(name=core.NAME),
                  back=_('Back to the character (Esc)'), sendMessage=_('Send message'),
                  stopAnswer=_('Stop the answer'), suggestionsTip=_('Show or hide suggestions. Keys: 1, 2, 3.'),
                  setupIntro=_('I need a language model to answer you. Choose local or cloud and I will guide you. The spoken voice is a separate setting.'),
                  apiNotes=_('Create an API key in your provider account, then paste it here. A chat subscription '
                             'does not necessarily include API credit. Choose a model enabled for your account. '
                             'Qwen endpoints depend on region and workspace: copy the address from its console.'),
                  notNow=_('Not now'), pauseTour=_('Pause tour'), start=_('Start'))
    result.update(chooseMode=_('Choose local or cloud'),
                  localChoice=_('On this PC: private, uses RAM and disk'),
                  cloudChoice=_('Cloud: API account and usage charges'))
    # These new strings cannot update the shared po/ catalogue from this branch.
    # Keep source msgids for its maintainer, and an Italian fallback until integration.
    if language() == 'it':
        fallbacks = dict(floating='Flottante sulle viste', send='Invia', voice='Leggi ad alta voce',
                         preview='Questa anteprima non è collegata a un modello.', greeting='Ciao, sono Meridio.',
                         local='Su questo PC', cloud='Nel cloud', endpoint='Indirizzo del server',
                         account='Account e istruzioni API', discover='Cerca modelli locali',
                         probe='Prova il collegamento', useModel='Usa questo modello', withdraw='Revoca il consenso',
                         animated='Meridio animato', appearance='Aspetto', style='Disegno', smooth='Morbido',
                         width='Larghezza', height='Altezza', suggestions='Domande pronte')
        result.update(fallbacks)
    return result


def install_assistant(engine, *, chat=None, help_service=None, theme=None):
    tokens = install_controls(engine, theme)
    if not getattr(engine, '_assistant_images', None):
        engine._assistant_images = CharacterProvider()
        engine.addImageProvider('assistant', engine._assistant_images)
    service = help_service or AssistantHelp(engine)
    engine._assistant_help = service
    engine._assistant_chat = chat
    context = engine.rootContext()
    context.setContextProperty('assistantHelp', service)
    context.setContextProperty('assistantChat', chat)
    context.setContextProperty('assistantText', labels())
    return tokens, service


def build_page(page='meridio', *, options=None, width=1366, height=900, chat=None):
    if page not in PAGES:
        raise ValueError(f'Unknown assistant page: {page}')
    engine = QQmlApplicationEngine()
    diagnostics = []
    engine._assistant_diagnostics = diagnostics
    engine.warnings.connect(lambda errors: diagnostics.extend(error.toString() for error in errors))
    theme, service = install_assistant(engine, chat=chat, theme=options)
    engine.rootContext().setContextProperty('assistantPage', page)
    engine.load(QUrl.fromLocalFile(str(QML / 'Preview.qml')))
    if not engine.rootObjects():
        raise RuntimeError('Could not load the Meridio page: ' + '\n'.join(diagnostics))
    window = engine.rootObjects()[0]
    window.resize(width, height)
    if page == 'help':
        service.request('phase.production')
    elif page == 'manual':
        service.openManual('README.md')
    elif page == 'tour':
        service.startTour(False)
    return engine, window, theme


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('page', nargs='?', choices=PAGES, default='meridio')
    parser.add_argument('--theme', choices=('light', 'dark'), default='light')
    parser.add_argument('--shot', type=Path)
    parser.add_argument('--width', type=int, default=1366)
    parser.add_argument('--height', type=int, default=900)
    parser.add_argument('--large-text', action='store_true')
    args = parser.parse_args(argv)
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(['meridio-preview'])
    setup('it')
    engine, window, theme = build_page(args.page, width=args.width, height=args.height,
                                      options=dict(theme=args.theme, textSize='large' if args.large_text else 'medium'))
    if args.shot:
        def capture():
            args.shot.parent.mkdir(parents=True, exist_ok=True)
            picture = window.grabWindow()
            if picture.isNull() or not picture.save(str(args.shot)):
                raise RuntimeError(f'Could not save {args.shot}')
            print(f'{args.shot}: {window.rendererInterface().graphicsApi()}, DPR={window.effectiveDevicePixelRatio()}')
            app.quit()
        QTimer.singleShot(900, capture)
    result = app.exec()
    window.close()
    from shiboken6 import delete
    delete(engine)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
