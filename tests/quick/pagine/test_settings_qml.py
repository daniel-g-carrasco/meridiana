"""Native Quick settings gestures and rendered pages, R378/R392/R395."""
from pathlib import Path
import os
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QPoint, QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from meridiana.config import Config
from meridiana.quick.backend.settings import install_settings


HOST = '''import QtQuick
import Meridiana.Theme
import Meridiana.Settings
Rectangle {
    width: 1000; height: 850; color: Theme.colors.window
    SettingsPage { anchors.fill: parent; anchors.margins: 24; backend: settingsBackend }
}'''


class SettingsQuickTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from meridiana import i18n
        cls.old_language = i18n.language()
        i18n.setup('it')
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        from meridiana import i18n
        i18n.setup(cls.old_language)

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.view = QQuickView()
        self.cfg = Config(theme='light', accent='indigo', backgrounds='grey', font='plex')
        self.backend = install_settings(self.view.engine(), self.cfg, Path(self.tmp.name) / 'config.json')
        self.warnings = []
        self.view.engine().warnings.connect(lambda warnings: self.warnings.extend(w.toString() for w in warnings))
        source = Path(self.tmp.name) / 'SettingsHost.qml'
        source.write_text(HOST, encoding='utf8')
        self.view.setSource(QUrl.fromLocalFile(str(source)))
        self.view.setResizeMode(QQuickView.ResizeMode.SizeRootObjectToView)
        self.assertEqual(self.view.status(), QQuickView.Status.Ready, self.warnings)
        self.view.show()
        QTest.qWait(80)
        self.addCleanup(self.close_view)

    def close_view(self):
        self.backend.close()
        self.view.close()
        self.view.setSource(QUrl())
        self.view.deleteLater()
        self.app.processEvents()

    def item(self, name):
        # QML delegates are visual children but are not always QObject descendants.
        def find(item):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                result = find(child)
                if result:
                    return result
            return None
        found = find(self.view.rootObject())
        self.assertIsNotNone(found, name)
        return found

    def click(self, name):
        item = self.item(name)
        p = item.mapToScene(item.boundingRect().center())
        QTest.mouseClick(self.view, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                         QPoint(round(p.x()), round(p.y())))
        QTest.qWait(30)

    def test_real_checkbox_undo_and_reset_confirmation_no_extra_window(self):
        self.backend.section = 'privacy'
        QTest.qWait(30)  # let the new controls complete their first layout before clicking
        before = len(self.app.topLevelWindows())
        self.click('setting_network_geocoding')
        self.assertFalse(self.cfg.network_geocoding)
        self.click('settingsUndo')
        self.assertTrue(self.cfg.network_geocoding)
        self.click('setting_network_tiles')
        self.click('settingsReset')
        self.assertFalse(self.cfg.network_tiles)
        self.click('settingsConfirmReset')
        self.assertTrue(self.cfg.network_tiles)
        self.assertEqual(before, len(self.app.topLevelWindows()))

    def test_sections_render_and_use_theme_font(self):
        destination = Path('build/quick-foto/pagine')
        destination.mkdir(parents=True, exist_ok=True)
        for mode in ('light', 'dark'):
            self.backend.setValue('theme', mode)
            for category in self.backend.categories:
                self.backend.section = category['key']
                QTest.qWait(50)
                image = self.view.grabWindow()
                self.assertFalse(image.isNull())
                scale = os.environ.get('QT_SCALE_FACTOR', '1')
                suffix = '' if scale == '1' else f'-scale{scale}'
                image.save(str(destination / f'settings-{category["key"]}-{mode}{suffix}.png'))
                self.assertEqual(self.item('settingsUndo').property('font').family(), 'IBM Plex Sans')
        self.assertFalse(self.warnings, '\n'.join(self.warnings))

    def test_profile_form_stays_in_view_after_keyboard_category(self):
        self.backend.section = 'keyboard'
        QTest.qWait(30)
        self.backend.section = 'report'
        QTest.qWait(30)
        item = self.item('settingsAddProfile')
        point = item.mapToScene(item.boundingRect().center())
        self.assertLess(point.y(), 500)
        self.click('settingsAddProfile')
        self.assertEqual(1, len(self.cfg.report_profiles))

    def test_profile_typing_applies_after_pause_and_retains_focus(self):
        self.backend.section = 'report'
        QTest.qWait(30)
        self.click('settingsAddProfile')
        self.click('settingsProfile_name')
        QTest.keyClick(self.view, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(self.view, Qt.Key.Key_X)
        QTest.qWait(450)
        self.assertEqual('x', self.cfg.report_profiles[0]['name'])
        self.assertTrue(self.item('settingsProfile_name').hasActiveFocus())
        self.view.grabWindow().save('build/quick-foto/pagine/settings-report-edited-light.png')

    def test_narrow_layout_with_large_text_still_has_usable_footer(self):
        self.backend.setValue('text_size', 'large')
        self.view.resize(480, 760)
        self.backend.section = 'privacy'
        QTest.qWait(40)
        self.click('setting_network_tiles')
        self.assertFalse(self.cfg.network_tiles)
        self.click('settingsUndo')
        self.assertTrue(self.cfg.network_tiles)
        reset = self.item('settingsReset')
        self.assertLessEqual(reset.mapToScene(reset.boundingRect().bottomRight()).x(), 480)
        self.view.grabWindow().save('build/quick-foto/pagine/settings-privacy-narrow-large.png')

    def test_scroll_bar_never_lies_on_a_text_r501(self):
        # R501 (Daniel 06/11/2026, Assistant): the bar lay over the rows and the long lines ran under it, cut.
        def shown(item):
            if not item.isVisible() or item.opacity() <= 0:
                return
            yield item
            for child in item.childItems():
                yield from shown(child)

        for size in ('normal', 'large'):
            self.backend.setValue('text_size', size)
            for width in (640, 1000, 1500):
                for section in ('assistant', 'maps', 'privacy'):
                    with self.subTest(size=size, width=width, section=section):
                        self.view.resize(width, 760)
                        self.backend.section = section
                        QTest.qWait(120)
                        scroll, column = self.item('settingsScroll'), self.item('settingsColumn')
                        bars = [i for i in shown(scroll) if i.inherits('QQuickScrollBar')
                                and i.property('orientation') == Qt.Orientation.Vertical]
                        flick = scroll.property('contentItem')
                        needed = flick.property('contentHeight') > flick.height() + .5
                        self.assertEqual(bool(bars), needed, (section, width))   # the bar only when needed
                        edge = min([b.mapToScene(b.boundingRect().topLeft()).x() for b in bars]
                                   + [column.mapToScene(column.boundingRect().topRight()).x()])
                        texts = [t for t in shown(column) if t.inherits('QQuickText') and str(t.property('text') or '').strip()]
                        self.assertTrue(texts)
                        for text in texts:
                            painted = min(text.width(), text.property('contentWidth') or text.width())
                            right = text.mapToScene(text.boundingRect().topLeft()).x() + painted
                            self.assertLessEqual(right, edge + .5, (section, width, str(text.property('text'))[:40]))
        self.assertEqual(self.warnings, [])


if __name__ == '__main__':
    unittest.main()
