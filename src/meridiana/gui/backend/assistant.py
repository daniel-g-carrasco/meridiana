"""Install and preview the autonomous Meridio Quick components.

Shell integration uses install_assistant(engine, chat=..., help_service=...).
The standalone preview never constructs a provider or reads the user's settings.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PySide6.QtCore import Property, QObject, QPointF, QSize, Qt, QTimer, QUrl, Slot
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPolygonF
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider

from meridiana.app import assistant as core
from meridiana.app.assistant import figure
from meridiana.i18n import _, setup
from meridiana.gui.backend.assistant_help import AssistantHelp
from meridiana.gui.backend.controls import install_controls

PAGES = ('meridio', 'conversation', 'help', 'manual', 'tour', 'setup', 'local')
QML = Path(__file__).resolve().parent.parent / 'qml' / 'Meridiana' / 'Assistant'


def _points(points) -> list:
    return [QPointF(x, y) for x, y in points]


class FigureBridge(QObject):
    """Meridio's figure for Character.qml (R619): the outlines, poses and rhythm of app/assistant/figure.py once,
    and the eyes' outline when their cut changes (`requests` counts those: none while he only moves)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.requests = 0
        data = figure.window_data()
        data['outlines'] = [_points(figure.outline(key)) for key in figure.ORDER]
        data['stickers'] = [_points(figure.sticker_outline(key, True)) for key in figure.ORDER]
        data['stickersLarge'] = [_points(figure.sticker_outline(key, False)) for key in figure.ORDER]
        self._data = data

    data = Property('QVariantMap', lambda self: self._data, constant=True)

    @Slot('QVariantMap', bool, result='QVariantList')
    def eyes(self, values, small):
        self.requests += 1
        p = figure.pose(**{key: float(values.get(key) or 0.0) for key in figure.EYE_KEYS})
        return [{'outline': _points(eye['outline']), 'arch': _points(eye['arch']), 'archLine': eye['arch_line']}
                for eye in figure.eyes(p, bool(small))]


def paint_figure(painter, side: float, p: dict | None = None, place: tuple | None = None) -> None:
    """Meridio still, with QPainter: the same outlines in the same order as Character.qml (figure.projected)."""
    p = p or figure.POSES['rest']
    painter.setPen(Qt.PenStyle.NoPen)
    for layer, key, points in figure.projected(p, side, place):
        painter.setBrush(QColor(figure.colour(layer, key)))
        painter.drawPolygon(QPolygonF(_points(points)))
    for eye in figure.projected_eyes(p, side, place):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(figure.INK))
        painter.drawPolygon(QPolygonF(_points(eye['outline'])))
        if eye['arch']:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(figure.INK), eye['arch_line'], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawPolyline(QPolygonF(_points(eye['arch'])))


class FigureImages(QQuickImageProvider):
    """Meridio still as an icon (the status bar's button): image://assistant/sticker, filling the size asked."""

    def __init__(self):
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, identifier, size, requestedSize):
        dimensions = requestedSize if requestedSize.isValid() and not requestedSize.isEmpty() else QSize(18, 18)
        image = QImage(dimensions, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(dimensions.width(), dimensions.height())
        paint_figure(painter, side, place=figure.fitted(side))
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
                local=_('On this PC'),
                preview=_('This preview is not connected to a model.'),
                greeting=_('Hello, I am Meridio.'), properties=_('Properties'),
                provider=_('Provider'), model=_('Model'), endpoint=_('Server URL'), apiKey=_('API key'),
                save=_('Save'), account=_('Open provider account'), cloud=_('In the cloud'),
                discover=_('Find local models'), probe=_('Test connection'), useModel=_('Use this model'),
                ram=_('RAM (GB)'), reserved=_('Reserved project: never to the cloud'), cancel=_('Cancel'),
                withdraw=_('Withdraw consent'), preferences=_('Settings'),
                appearance=_('Appearance'), animated=_('Meridio animated'),
                width=_('Width'), height=_('Height'))
    result.update(attachShort=_('Attach…'),
                  questionPlaceholder=_('Ask {name}…').format(name=core.NAME),
                  back=_('Back to the character (Esc)'), sendMessage=_('Send message'),
                  stopAnswer=_('Stop the answer'),
                  setupIntro=_('I need a language model to answer you. Choose local or cloud and I will guide you. The spoken voice is a separate setting.'),
                  apiNotes=_('Create an API key in your provider account, then paste it here. A chat subscription '
                             'does not necessarily include API credit. Choose a model enabled for your account. '
                             'Qwen endpoints depend on region and workspace: copy the address from its console.'),
                  notNow=_('Not now'), pauseTour=_('Pause tour'), start=_('Start'))
    result.update(chooseMode=_('Choose local or cloud'),
                  localChoice=_('On this PC: private, uses RAM and disk'),
                  cloudChoice=_('Cloud: API account and usage charges'))
    return result


def install_assistant(engine, *, chat=None, help_service=None, theme=None):
    tokens = install_controls(engine, theme)
    if not getattr(engine, '_assistant_figure', None):
        engine._assistant_figure = FigureBridge(engine)
        engine._assistant_images = FigureImages()
        engine.addImageProvider('assistant', engine._assistant_images)
    service = help_service or AssistantHelp(engine)
    engine._assistant_help = service
    engine._assistant_chat = chat
    context = engine.rootContext()
    context.setContextProperty('assistantFigure', engine._assistant_figure)
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
