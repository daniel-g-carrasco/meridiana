"""R133, R390, R391, R395: the shared theme reaches live QML consumers."""
import unittest
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from meridiana import theme_colors
from meridiana.quick.backend.tokens import ThemeTokens, install_theme
from meridiana.ui import design


class ThemeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(['theme-test'])

    def assert_colors(self, actual, expected):
        self.assertEqual(set(actual), set(expected))
        for key, value in expected.items():
            if isinstance(value, dict):
                self.assert_colors(actual[key], value)
            elif isinstance(value, str) and value.startswith('#'):
                color = QColor(actual[key])
                self.assertTrue(color.isValid(), key)
                self.assertEqual(color.name(), value[:7], key)
                self.assertEqual(color.alpha(), int(value[7:9], 16) if len(value) == 9 else 255, key)
            else:
                self.assertEqual(actual[key], value, key)

    def test_provider_cannot_be_owned_by_two_engines(self):
        first, second = QQmlEngine(), QQmlEngine()
        provider = install_theme(first)
        with self.assertRaises(ValueError):
            install_theme(second, provider)

    def test_system_accent_follows_the_existing_platform_reader(self):
        from meridiana.ui.theme import SystemAccent
        system = SystemAccent.of(self.app)
        before = system.value
        try:
            system.value = '#2f6b4f'
            with patch('meridiana.quick.backend.tokens.sys.platform', 'linux'):
                provider = ThemeTokens({'accent': 'system'})
                self.assert_colors(provider.colors, theme_colors.derive(system.value, False, 'grey').tokens)
                system.value = '#5b4bb0'
                system.changed.emit(system.value)
                self.assert_colors(provider.colors, theme_colors.derive(system.value, False, 'grey').tokens)
        finally:
            system.value = before
            system.changed.emit(before)

    def test_windows_system_accent_follows_live_palette_without_changing_explicit_theme(self):
        from meridiana.ui.theme import SystemAccent
        SystemAccent.of(self.app)
        original = self.app.palette()
        try:
            with patch('meridiana.quick.backend.tokens.sys.platform', 'win32'):
                provider = ThemeTokens({'accent': 'system'})
                explicit = ThemeTokens({'accent': 'indigo'})
                explicit_before = explicit.colors.copy()
                notifications = []
                provider.changed.connect(lambda: notifications.append(provider.revision))
                for color in ('#982e7c', '#2f6b4f'):
                    palette = self.app.palette()
                    palette.setColor(QPalette.ColorRole.Highlight, QColor(color))
                    self.app.setPalette(palette)
                    self.app.processEvents()
                    self.assert_colors(provider.colors, theme_colors.derive(color, False, 'grey').tokens)
                    self.assertEqual(explicit.colors, explicit_before)
                self.assertEqual(len(notifications), 2)
        finally:
            self.app.setPalette(original)

    def test_every_palette_keeps_every_color_and_alpha(self):
        tokens = ThemeTokens()
        for accent, seed in theme_colors.PRESETS.items():
            for background in theme_colors.BACKGROUNDS:
                for dark in (False, True):
                    with self.subTest(accent=accent, backgrounds=background, dark=dark):
                        tokens.configure(dict(accent=accent, backgrounds=background, dark=dark))
                        self.assert_colors(tokens.colors, theme_colors.derive(seed, dark, background).tokens)

    def test_all_design_scales_and_sizes_without_changing_widgets(self):
        tokens = ThemeTokens()
        original = design.text_size()
        self.addCleanup(design.set_text_size, original)
        for choice in design.TEXT_SIZES:
            tokens.configure({'textSize': choice})
            self.assertEqual(design.text_size(), original)
            design.set_text_size(choice)
            for name in ('Space', 'Radius', 'Type', 'Size', 'Line', 'Motion', 'Layout', 'Bar', 'Icon'):
                expected = {k: v for k, v in vars(getattr(design, name)).items() if k.isupper()}
                if name == 'Motion':    # the curves are names in design, the Quick's Easing.* numbers in Theme (F4)
                    from PySide6.QtCore import QEasingCurve
                    expected |= {k: QEasingCurve.Type[expected[k]].value for k in ('EASE', 'EASE_IN', 'EASE_SWING')}
                self.assertEqual(getattr(tokens, name.lower()), expected)
            for style in design.Text.ALL:
                self.assertEqual(tokens.text[style.name], dict(size=style.size, weight=style.weight,
                                                              tone=style.tone, caps=style.caps))
            self.assertEqual(tokens.text['button'], tokens.text['strong'])
            design.set_text_size(original)

    def test_defaults_and_legacy_map(self):
        tokens = ThemeTokens()
        self.assertEqual(tokens.fontFamily, 'IBM Plex Sans')
        self.assertEqual(tokens.barFontFamily, 'IBM Plex Sans Condensed')
        self.assertEqual(tokens.textSize, 'medium')
        self.assertFalse(tokens.dark)
        self.assert_colors(tokens.colors, theme_colors.derive(theme_colors.PRESETS['indigo'], False, 'grey').tokens)
        from meridiana.quick.app import tokens as legacy_tokens
        self.assertEqual(tokens.tokens, legacy_tokens())

    def test_measurement_uses_chosen_font_style_caps_and_condensed(self):
        tokens = ThemeTokens()
        for family in ('inter', 'plex'):
            for size in design.TEXT_SIZES:
                tokens.configure({'font': family, 'textSize': size})
                for style in ('body', 'label', 'heading'):
                    for condensed in (False, True):
                        spec = tokens.text[style]
                        font = QFont(tokens.barFontFamily if condensed else tokens.fontFamily)
                        font.setPixelSize(spec['size'])
                        font.setWeight(QFont.Weight(spec['weight']))
                        if spec['caps']:
                            font.setCapitalization(QFont.Capitalization.AllUppercase)
                            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + design.Type.LETTER_SPACING)
                        metrics = QFontMetricsF(font)
                        result = tokens.measureText('Modellazione', style, condensed)
                        self.assertAlmostEqual(result['width'], metrics.horizontalAdvance('Modellazione'))
                        self.assertAlmostEqual(result['height'], metrics.height())
                        self.assertAlmostEqual(result['ascent'], metrics.ascent())
                        self.assertAlmostEqual(result['descent'], metrics.descent())

    def component(self, engine):
        component = QQmlComponent(engine)
        component.setData(b'''import QtQuick
import Meridiana.Theme
Rectangle {
    width: 400; height: 120; color: Theme.colors.window
    property string family: label.font.family
    property int bodySize: label.font.pixelSize
    property int duration: Theme.motion.NORMAL
    property real measured: Theme.measureText("Modellazione", "body", false).width
    property string barFamily: Theme.barFontFamily
    Text { id: label; text: "Modellazione"; font.family: Theme.fontFamily
           font.pixelSize: Theme.text.body.size; color: Theme.colors.text }
    function change() { Theme.configure({theme: "dark", font: "inter", textSize: "large", reducedMotion: true}) }
}''', QUrl())
        self.assertFalse(component.isError(), '\n'.join(e.toString() for e in component.errors()))
        root = component.create()
        self.assertIsInstance(root, QQuickItem, '\n'.join(e.toString() for e in component.errors()))
        root.setParent(engine)
        return root

    def test_qml_updates_live_and_engines_are_independent(self):
        first, second = QQmlEngine(), QQmlEngine()
        a, b = install_theme(first), install_theme(second)
        self.assertIs(install_theme(first), a)
        one, two = self.component(first), self.component(second)
        before_width = one.property('measured')
        from PySide6.QtCore import QMetaObject
        self.assertTrue(QMetaObject.invokeMethod(one, 'change'))
        self.app.processEvents()
        self.assertEqual(one.property('color'), QColor(a.colors['window']))
        self.assertEqual(one.property('bodySize'), a.text['body']['size'])
        self.assertEqual(one.property('family'), 'Inter')
        self.assertEqual(one.property('barFamily'), 'Inter')
        self.assertEqual(one.property('duration'), 0)
        self.assertNotEqual(one.property('measured'), before_width)
        self.assertTrue(a.dark)
        self.assertFalse(b.dark)
        self.assertEqual(two.property('family'), 'IBM Plex Sans')
        self.assertEqual(two.property('duration'), design.Motion.NORMAL)
        # Root consumers must die before their engine and its context provider.
        from shiboken6 import delete
        delete(one)
        delete(two)

    def test_reduced_motion_keeps_wait_and_typing_count(self):
        tokens = ThemeTokens()
        tokens.configure({'reducedMotion': True})
        for key in ('FAST', 'QUICK', 'NORMAL', 'SLOW', 'CAREFUL', 'TYPING_MS', 'TYPING_MAX_MS'):
            self.assertEqual(tokens.motion[key], 0)
        self.assertEqual(tokens.motion['DWELL'], design.Motion.DWELL)
        self.assertEqual(tokens.motion['TYPING_CHARS'], design.Motion.TYPING_CHARS)

    def test_invalid_configuration_is_atomic_and_noop_does_not_notify(self):
        tokens = ThemeTokens()
        changes = []
        tokens.changed.connect(lambda: changes.append(True))
        tokens.configure({'font': 'plex'})
        self.assertEqual(changes, [])
        with self.assertRaises(ValueError):
            tokens.configure({'dark': True, 'font': 'missing'})
        self.assertFalse(tokens.dark)
        self.assertEqual(changes, [])

    def test_rendered_theme_changes_in_a_real_quick_window(self):
        """R390/R391/R395: rendered background and font change without rebuilding the scene."""
        engine = QQmlEngine()
        warnings = []
        engine.warnings.connect(lambda errors: warnings.extend(e.toString() for e in errors))
        tokens = install_theme(engine)
        root = self.component(engine)
        window = QQuickWindow()
        root.setParentItem(window.contentItem())
        window.resize(1366, 900)
        root.setWidth(window.width())
        root.setHeight(window.height())
        window.show()
        self.assertTrue(QTest.qWaitForWindowExposed(window))
        folder = Path(__file__).resolve().parents[3] / 'build' / 'quick-foto' / 'tema'
        folder.mkdir(parents=True, exist_ok=True)
        try:
            for dark in (False, True):
                tokens.configure({'dark': dark, 'textSize': 'large' if dark else 'medium'})
                for width, height in ((1366, 900), (1600, 960), (1920, 1080)):
                    window.resize(width, height)
                    root.setWidth(width)
                    root.setHeight(height)
                    QTest.qWait(40)
                    shot = window.grabWindow()
                    self.assertFalse(shot.isNull())
                    ratio = window.effectiveDevicePixelRatio()
                    self.assertEqual(shot.pixelColor(int(200 * ratio), int(100 * ratio)),
                                     QColor(tokens.colors['window']))
                    name = f"{'dark' if dark else 'light'}-{width}x{height}-dpr{ratio:g}.png"
                    self.assertTrue(shot.save(str(folder / name)))
            self.assertEqual(warnings, [])
        finally:
            from shiboken6 import delete
            window.close()
            delete(root)
            delete(window)
