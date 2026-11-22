"""Reactive QML projection of the existing design scales, colours and shipped fonts.

Each engine owns its theme. No Widgets palette, font or design scale is mutated.
Eight-digit CSS colours are converted to QColor's alpha-first order at this boundary.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

from PySide6.QtCore import QEasingCurve, QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPalette, QTextDocument

from meridiana.app.interface import north_sign, theme_colors
from meridiana.gui.style import design
from meridiana.gui.style.theme import FONTS, SystemAccent, _font_families


def _constants(cls):
    return {name: value for name, value in vars(cls).items() if name.isupper()}


def _qt_colors(value):
    if isinstance(value, dict):
        return {key: _qt_colors(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_qt_colors(item) for item in value]
    return theme_colors.qt_hex(value) if isinstance(value, str) and value.startswith('#') else value


class ThemeTokens(QObject):
    """The shared theme, configured atomically and notified once per real change."""

    changed = Signal()

    def __init__(self, options=None, parent=None):
        super().__init__(parent)
        # a QCoreApplication is not enough: QGuiApplication.palette() on one ends the process with an access violation
        # (07/11/2026: a Quick test after a module that had made a QCoreApplication, 10 times out of 10), a clear error
        if not isinstance(QGuiApplication.instance(), QGuiApplication):
            raise RuntimeError('ThemeTokens requires a QGuiApplication, not '
                               + type(QGuiApplication.instance()).__name__)
        self._options = dict(theme='light', accent='indigo', backgrounds='grey', font='plex',
                             textSize='medium', reducedMotion=False, phaseAnimations=False, density='normal')
        self._revision = 0
        self._veils, self._veil_colour = 0, QColor()           # R586 (c), veil()
        self._system = SystemAccent.of(QGuiApplication.instance())
        self._system.changed.connect(self._system_changed)
        self._build()
        if options:
            self.configure(options)
        QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_changed)
        QGuiApplication.instance().paletteChanged.connect(self._system_changed)

    def _build(self):
        o = self._options
        self._dark = (QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
                      if o['theme'] == 'system' else o['theme'] == 'dark')
        # Quick does not replace the application palette: on Windows it remains the
        # live platform palette. Linux uses the portal reader and its change signal.
        system_accent = (QGuiApplication.palette().color(QPalette.ColorRole.Highlight).name()
                         if sys.platform == 'win32' else self._system.value)
        seed = theme_colors.seed_for(o['accent'], system_accent)
        self._colors = _qt_colors(theme_colors.derive(seed, self._dark, o['backgrounds']).tokens)
        self._maps = {name.lower(): _constants(getattr(design, name))
                      for name in ('Space', 'Radius', 'Type', 'Size', 'Line', 'Motion', 'Layout', 'Bar', 'Icon',
                                   'Stack', 'Highlight', 'Annotation')}
        # the curves are names in design.Motion (it has no Qt): the Quick reads the numbers of its Easing.* (F4)
        for name in ('EASE', 'EASE_IN', 'EASE_SWING'):
            self._maps['motion'][name] = QEasingCurve.Type[getattr(design.Motion, name)].value
        # Read the current Widgets scale, subtract its offset and apply this engine's.
        delta = design.TEXT_SIZES[o['textSize']] - design.TEXT_SIZES[design.text_size()]
        for name in ('TINY', 'CAPTION', 'SMALL', 'BODY', 'TITLE', 'HEADING', 'DISPLAY', 'CONTROL', 'MICRO'):
            self._maps['type'][name] += delta
        self._maps['annotation']['LABEL_SIZE'] += delta
        self._maps['type']['SCALE'] = tuple(size + delta for size in design.Type.SCALE)
        self._text = {style.name: dict(size=style.size + delta, weight=style.weight,
                                      tone=style.tone, caps=style.caps) for style in design.Text.ALL}
        self._text['button'] = self._text['strong'].copy()
        if o['reducedMotion']:
            for name in ('FAST', 'QUICK', 'NORMAL', 'SLOW', 'CAREFUL', 'TYPING_MS', 'TYPING_MAX_MS'):
                self._maps['motion'][name] = 0
            for name in ('SETTLE', 'FADE'):
                self._maps['highlight'][name] = 0
        family, tight = _font_families(o['font'])
        self._family = family or QGuiApplication.font().family()
        self._bar_family = tight or self._family
        self._tokens = {k: v for k, v in self._colors.items() if isinstance(v, str)}
        self._tokens.update({'plan_' + k: v for k, v in self._colors['plan'].items()})
        self._tokens.update(body=self._text['body']['size'], title=self._text['title']['size'],
                            caption=self._text['caption']['size'], heading=self._text['heading']['size'],
                            control=design.Size.CONTROL, tab=design.Size.TAB, cardRadius=design.Radius.CARD,
                            radius=design.Radius.CONTROL, inset=design.Line.TEXT_INSET, gap=design.Space.M,
                            small=design.Space.XS, pad=design.Space.L, panelMin=design.Size.PANEL_MIN,
                            motion=self._maps['motion']['NORMAL'], hair=design.Line.HAIR, focus=design.Line.FOCUS)

    def _system_changed(self, *_args):
        if self._options['theme'] == 'system' or self._options['accent'] == 'system':
            before = self._colors
            self._build()
            if self._colors != before:
                self._revision += 1
                self.changed.emit()

    @Slot('QVariantMap')
    def configure(self, options):
        """Accept only known valid options; an invalid update leaves the theme intact."""
        options = dict(options)
        for old, new in (('text_size', 'textSize'), ('reduced_motion', 'reducedMotion'),
                         ('phase_animations', 'phaseAnimations')):
            if old in options:
                options[new] = options.pop(old)
        if 'dark' in options:
            if not isinstance(options['dark'], bool):
                raise ValueError('dark must be a boolean')
            options['theme'] = 'dark' if options.pop('dark') else 'light'
        unknown = options.keys() - self._options.keys()
        if unknown:
            raise ValueError(f'Unknown theme options: {sorted(unknown)}')
        next_options = self._options | options
        choices = dict(theme=('light', 'dark', 'system'), backgrounds=theme_colors.BACKGROUNDS,
                       font=FONTS, textSize=design.TEXT_SIZES,
                       density=design.Rows.DENSITIES)
        for name, allowed in choices.items():
            if next_options[name] not in allowed:
                raise ValueError(f'Invalid {name}: {next_options[name]!r}')
        accent = next_options['accent']
        if not isinstance(accent, str) or (accent not in theme_colors.PRESETS and accent != 'system'
                                          and re.fullmatch(r'#[0-9a-fA-F]{6}', accent) is None):
            raise ValueError(f'Invalid accent: {accent!r}')
        for name in ('reducedMotion', 'phaseAnimations'):
            if not isinstance(next_options[name], bool):
                raise ValueError(f'{name} must be a boolean')
        if next_options == self._options:
            return
        self._options = next_options
        self._build()
        self._revision += 1
        self.changed.emit()

    # R586 (c): the modal windows shown (Controls/ModalVeil.qml) and the colour of their veil; window_frame.FrameTheme
    # puts the same veil on the title bar while one is shown
    veiled = Signal()

    @Slot(bool, QColor)
    def veil(self, on, colour):
        self._veils = max(0, self._veils + (1 if on else -1))
        self._veil_colour = QColor(colour)
        self.veiled.emit()

    def veil_colour(self):
        """The veil over the window while a modal window is shown, None when there is none."""
        return self._veil_colour if self._veils > 0 else None

    @Slot(str, str, bool, result='QVariantMap')
    def measureText(self, text, style='body', condensed=False):
        """Single-line advance and font metrics in logical pixels, with the style's caps."""
        if style not in self._text:
            raise ValueError(f'Unknown text style: {style!r}')
        spec = self._text[style]
        font = QFont(self._bar_family if condensed else self._family)
        font.setPixelSize(spec['size'])
        font.setWeight(QFont.Weight(spec['weight']))
        if spec['caps']:
            font.setCapitalization(QFont.Capitalization.AllUppercase)
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + design.Type.LETTER_SPACING)
        metrics = QFontMetricsF(font)
        return dict(width=metrics.horizontalAdvance(text), height=metrics.height(),
                    ascent=metrics.ascent(), descent=metrics.descent())

    @Slot(str, float, str, bool, result='QVariantMap')
    def textBlockInk(self, text, width, style, condensed):
        """First/last line ink relative to the first baseline, using Qt's actual word wrapping.

        A descender on an intermediate line must not lower the last line's ink bounds.
        """
        from PySide6.QtGui import QPainterPath, QTextLayout, QTextOption
        spec = self._text[style]
        font = QFont(self._bar_family if condensed else self._family)
        font.setPixelSize(spec['size'])
        font.setWeight(QFont.Weight(spec['weight']))
        if spec['caps']:
            font.setCapitalization(QFont.Capitalization.AllUppercase)
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + design.Type.LETTER_SPACING)
        layout = QTextLayout(text.replace('\n', '\u2028'), font)
        option = QTextOption()
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(option)
        layout.beginLayout()
        units = text.encode('utf-16-le')  # QTextLine indexes UTF-16 units, not Python's Unicode code points.
        lines, y = [], 0.0
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(max(1.0, width))
            start = line.textStart()
            part = units[2 * start:2 * (start + line.textLength())].decode('utf-16-le').strip()
            path = QPainterPath()
            path.addText(0, y, font, part)
            lines.append(path.boundingRect())
            y += line.height()
        layout.endLayout()
        return dict(top=lines[0].top() if lines else 0.0, bottom=lines[-1].bottom() if lines else 0.0,
                    firstBottom=lines[0].bottom() if lines else 0.0)

    @Slot(str, result='QVariantMap')
    def tooltipLayout(self, text):
        """The Widgets' rich tooltip and QTextDocument metrics, only when its text changes; the same text in the
        same colours is laid out once (1.100 layouts entering Plant, 06/11/2026)."""
        key = (text, self._colors['text'], self._colors['card'])
        kept = getattr(self, '_tooltip_layouts', None)
        if kept is None:
            kept = self._tooltip_layouts = {}
        found = kept.get(key)
        if found is None:
            if len(kept) > 4096:
                kept.clear()
            found = kept[key] = self._tooltip_layout(text)
        return dict(found)

    def _tooltip_layout(self, text):
        import math
        from meridiana.gui.style.popups import TIP_WIDTH, tip_html
        # R615: the theme's text on the menus' ground (`tooltip_bg` is that ground, see-through: the softer inks are
        # mixed with it opaque)
        rich = tip_html(text, self._colors['text'], self._colors['card'])
        font = QFont(self._family)
        font.setPixelSize(self._text['body']['size'])
        document = QTextDocument()
        document.setDefaultFont(font)
        document.setDocumentMargin(0)
        document.setHtml(rich)
        width = min(TIP_WIDTH, math.ceil(document.idealWidth()) + 2 * design.Space.M)
        document.setTextWidth(max(1, width - 2 * design.Space.M))
        return dict(html=rich, width=width, height=math.ceil(document.size().height()) + 2 * design.Space.S)

    @Slot(str, str, result='QVariantMap')
    def countPill(self, level, text):
        from meridiana.gui.style.status_pill import size_hint, tints
        font = QFont(self._family)
        font.setPixelSize(self._maps['annotation']['LABEL_SIZE'])
        font.setWeight(QFont.Weight(self._maps['annotation']['WEIGHT']))
        colours = {key: [c.name() for c in pair] for key, pair in tints(level, self._colors, self._dark).items()}
        return colours | dict(width=size_hint(text, font, design.Size.CHIP, reserve='88').width())

    @Slot(str, float, int, result='QVariantMap')
    def glyphAxis(self, text, size, weight):
        """Where a sign's ink stands, from the font's outline, in pixels from the pen's origin on the baseline: `axis`
        the middle of its lowest separate piece (the dot of «?» or «!»), `top` and `bottom` its ink's edges (R596:
        HelpMark centres the «?» by its dot and its ink, not by its advance and its line box)."""
        from PySide6.QtGui import QPainterPath
        font = QFont(self._family)
        font.setPixelSize(max(1, round(size)))
        font.setWeight(QFont.Weight(weight))
        path = QPainterPath()
        path.addText(0, 0, font, text)
        pieces = [polygon.boundingRect() for polygon in path.toSubpathPolygons() if polygon.size() > 2]
        if not pieces:
            return dict(axis=QFontMetricsF(font).horizontalAdvance(text) / 2, top=0.0, bottom=0.0)
        lowest = max(pieces, key=lambda r: r.center().y())
        box = path.boundingRect()
        return dict(axis=lowest.center().x(), top=box.top(), bottom=box.bottom())

    disabledText = Property(str, lambda self: theme_colors.faded_text(self._colors), notify=changed)
    colors = Property('QVariantMap', lambda self: self._colors, notify=changed)
    status = Property('QVariantMap', lambda self: dict(theme_colors.STATUS), constant=True)
    options = Property('QVariantMap', lambda self: dict(self._options), notify=changed)
    space = Property('QVariantMap', lambda self: self._maps['space'], notify=changed)
    radius = Property('QVariantMap', lambda self: self._maps['radius'], notify=changed)
    type = Property('QVariantMap', lambda self: self._maps['type'], notify=changed)
    size = Property('QVariantMap', lambda self: self._maps['size'], notify=changed)
    line = Property('QVariantMap', lambda self: self._maps['line'], notify=changed)
    motion = Property('QVariantMap', lambda self: self._maps['motion'], notify=changed)
    layout = Property('QVariantMap', lambda self: self._maps['layout'], notify=changed)
    bar = Property('QVariantMap', lambda self: self._maps['bar'], notify=changed)
    icon = Property('QVariantMap', lambda self: self._maps['icon'], notify=changed)
    stack = Property('QVariantMap', lambda self: self._maps['stack'], notify=changed)     # R616: design.Stack
    highlight = Property('QVariantMap', lambda self: self._maps['highlight'], notify=changed)   # R617: design.Highlight
    annotation = Property('QVariantMap', lambda self: self._maps['annotation'], notify=changed)
    text = Property('QVariantMap', lambda self: self._text, notify=changed)
    # R643: the drawings of the signs shared with the report (app/interface/north_sign.py): one source, no Qt
    signs = Property('QVariantMap', lambda self: {'north': north_sign.as_map()}, constant=True)
    tokens =Property('QVariantMap', lambda self: self._tokens, notify=changed)
    fontFamily = Property(str, lambda self: self._family, notify=changed)
    barFontFamily = Property(str, lambda self: self._bar_family, notify=changed)
    dark = Property(bool, lambda self: self._dark, notify=changed)
    reducedMotion = Property(bool, lambda self: self._options['reducedMotion'], notify=changed)
    # Daniel 21/11/2026: the change of phase animated (the tab's marker sliding, the pages fading in and out) only
    # when asked in the settings («phase_animations», off by default) and never with less motion asked
    phaseAnimations = Property(bool, lambda self: self._options['phaseAnimations'], notify=changed)
    phaseMotion = Property(bool, lambda self: self._options['phaseAnimations'] and not self._options['reducedMotion'],
                           notify=changed)
    textSize = Property(str, lambda self: self._options['textSize'], notify=changed)
    # the density of the trees and lists (design.Rows), a choice of who uses the program (the kit, 20/11/2026)
    density = Property(str, lambda self: self._options['density'], notify=changed)
    rowAir = Property(float, lambda self: getattr(design.Rows, self._options['density'].upper()), notify=changed)
    revision = Property(int, lambda self: self._revision, notify=changed)


def install_theme(engine, theme=None) -> ThemeTokens:
    """Install before loading QML. Repeated installation keeps the engine's provider alive."""
    existing = getattr(engine, '_meridiana_theme_tokens', None)
    if existing is not None:
        if theme is not None and theme is not existing:
            if isinstance(theme, ThemeTokens):
                raise ValueError('This engine already owns a different theme')
            existing.configure(theme)
        return existing
    provider = theme if isinstance(theme, ThemeTokens) else ThemeTokens(theme, engine)
    owner = getattr(provider, '_installed_engine', None)
    if owner is not None and owner is not engine:
        raise ValueError('A theme provider belongs to one QML engine')
    provider._installed_engine = engine
    engine.addImportPath(str(Path(__file__).parents[1] / 'qml'))
    engine.rootContext().setContextProperty('themeTokens', provider)
    # Context properties do not take ownership; retain even an externally owned provider.
    engine._meridiana_theme_tokens = provider
    return provider
