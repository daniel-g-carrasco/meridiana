"""What the round on Daniel's Linux laptop found on 14/11/2026 (Niri, a desktop in English, the program in Italian):

D2, D3: the window wrote «21 Dec» and «85.20» because Qt's default locale was the desktop's whenever the program spoke
Italian; it is the window's language now, whatever the desktop (gui/application.create_app). (The consumption's note,
«un impianto da 358.6 kWp», is written in core with f"{p:.1f}" and frozen by the parity references of study 44: left as
it is, see docs/quick/stato/r34-armonia.md.)
D6: at every close, a dozen «ProgressBar.qml: Cannot read property 'height' of null»: the common bar read `parent`
while the window was taken apart.
"""
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, qInstallMessageHandler
from PySide6.QtQml import QQmlComponent, QQmlEngine

import _setup
from meridiana import i18n
from meridiana.gui.application import QuickWindow, create_app
from quick.aiuti.differential import connected_fixture
from quick.gestures import pump


class Language(unittest.TestCase):
    def setUp(self):
        self.addCleanup(i18n.setup, i18n.language())
        self.addCleanup(QLocale.setDefault, QLocale())
        _setup.qt_or_skip()

    def test_the_qml_writes_dates_and_numbers_in_the_windows_language_not_the_desktops(self):
        QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedKingdom))   # the desktop's
        create_app('it')
        engine = QQmlEngine()
        component = QQmlComponent(engine)
        component.setData(b'import QtQuick\nQtObject { property string day: new Date(2026, 11, 21).toLocaleDateString('
                          b'Qt.locale(), "d MMM"); property string figure: (85.2).toLocaleString(Qt.locale(), "f", 2) }',
                          'file:///lingua.qml')
        made = component.create()
        self.assertIsNotNone(made, component.errorString())
        self.assertEqual(made.property('figure'), '85,20')
        self.assertEqual(made.property('day'), QLocale(QLocale.Language.Italian).toString(QDate(2026, 12, 21), 'd MMM'))
        self.assertNotIn('Dec', made.property('day'))


class Closing(unittest.TestCase):
    def test_the_window_closes_without_errors_of_the_progress_bar(self):
        app = _setup.qt_or_skip()
        create_app()
        said = []
        previous = qInstallMessageHandler(lambda kind, context, message: said.append(message))
        self.addCleanup(qInstallMessageHandler, previous)
        folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(folder.cleanup)
        host = QuickWindow(connected_fixture(), Path(folder.name), real_views=True, theme={'theme': 'light'})
        host.window.resize(1400, 900)
        host.window.show()
        host.shell.trigger('phase_plant')
        pump(800)
        host.close()
        app.processEvents()
        pump(200)
        self.assertEqual([m for m in said if 'ProgressBar.qml' in m], [])


if __name__ == '__main__':
    unittest.main()
