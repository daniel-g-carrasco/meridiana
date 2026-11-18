"""Reactive QML projection of the existing design scales, colours and shipped fonts.

Each engine owns its theme. No Widgets palette, font or design scale is mutated.
Eight-digit CSS colours are converted to QColor's alpha-first order at this boundary.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

from PySide6.QtCore import QEasingCurve, QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QFont, QFontMetricsF, QGuiApplication, QPalette, QTextDocument

from meridiana import theme_colors
from meridiana.ui import design
from meridiana.ui.theme import FONTS, SystemAccent, _font_families


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
                             textSize='medium', reducedMotion=False)
        self._revision = 0
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
                      for name in ('Space', 'Radius', 'Type', 'Size', 'Line', 'Motion', 'Layout', 'Bar', 'Icon')}
        # the curves are names in design.Motion (it has no Qt): the Quick reads the numbers of its Easing.* (F4)
        for name in ('EASE', 'EASE_IN', 'EASE_SWING'):
            self._maps['motion'][name] = QEasingCurve.Type[getattr(design.Motion, name)].value
        # Read the current Widgets scale, subtract its offset and apply this engine's.
        delta = design.TEXT_SIZES[o['textSize']] - design.TEXT_SIZES[design.text_size()]
        for name in ('TINY', 'CAPTION', 'SMALL', 'BODY', 'TITLE', 'HEADING', 'DISPLAY', 'CONTROL', 'MICRO'):
            self._maps['type'][name] += delta
        self._maps['type']['SCALE'] = tuple(size + delta for size in design.Type.SCALE)
        self._text = {style.name: dict(size=style.size + delta, weight=style.weight,
                                      tone=style.tone, caps=style.caps) for style in design.Text.ALL}
        self._text['button'] = self._text['strong'].copy()
        if o['reducedMotion']:
            for name in ('FAST', 'QUICK', 'NORMAL', 'SLOW', 'CAREFUL', 'TYPING_MS', 'TYPING_MAX_MS'):
                self._maps['motion'][name] = 0
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
        for old, new in (('text_size', 'textSize'), ('reduced_motion', 'reducedMotion')):
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
                       font=FONTS, textSize=design.TEXT_SIZES)
        for name, allowed in choices.items():
            if next_options[name] not in allowed:
                raise ValueError(f'Invalid {name}: {next_options[name]!r}')
        accent = next_options['accent']
        if not isinstance(accent, str) or (accent not in theme_colors.PRESETS and accent != 'system'
                                          and re.fullmatch(r'#[0-9a-fA-F]{6}', accent) is None):
            raise ValueError(f'Invalid accent: {accent!r}')
        if not isinstance(next_options['reducedMotion'], bool):
            raise ValueError('reducedMotion must be a boolean')
        if next_options == self._options:
            return
        self._options = next_options
        self._build()
        self._revision += 1
        self.changed.emit()

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

    @Slot(str, result='QVariantMap')
    def tooltipLayout(self, text):
        """The Widgets' rich tooltip and QTextDocument metrics, only when its text changes; the same text in the
        same colours is laid out once (1.100 layouts entering Plant, 06/11/2026)."""
        key = (text, self._colors['tooltip_fg'], self._colors['tooltip_bg'])
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
        from meridiana.ui.popups import TIP_WIDTH, tip_html
        rich = tip_html(text, self._colors['tooltip_fg'], self._colors['tooltip_bg'])
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
        from meridiana.ui.status_pill import size_hint, tints
        font = QFont(self._family)
        font.setPixelSize(self._text['label']['size'])
        font.setWeight(QFont.Weight(self._text['label']['weight']))
        colours = {key: [c.name() for c in pair] for key, pair in tints(level, self._colors, self._dark).items()}
        return colours | dict(width=size_hint(text, font, design.Size.CHIP, reserve='88').width())

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
    text = Property('QVariantMap', lambda self: self._text, notify=changed)
    tokens = Property('QVariantMap', lambda self: self._tokens, notify=changed)
    fontFamily = Property(str, lambda self: self._family, notify=changed)
    barFontFamily = Property(str, lambda self: self._bar_family, notify=changed)
    dark = Property(bool, lambda self: self._dark, notify=changed)
    reducedMotion = Property(bool, lambda self: self._options['reducedMotion'], notify=changed)
    textSize = Property(str, lambda self: self._options['textSize'], notify=changed)
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
