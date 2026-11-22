"""The Quick in Italian: the texts of the census of 07/11/2026 have their entry, and the QML's qsTr goes through
po/it.po (StringLabels.qml: «No inverter», «Inv. %1» came out in English), by Qt's own translator and the .qm made
from it (R593: a translator in Python stopped the window)."""
import os
import subprocess
import sys
import unittest

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from meridiana import i18n
from meridiana.gui.application import create_app


def setUpModule():
    _setup.keep_global_state()


class ItalianQuick(unittest.TestCase):
    def setUp(self):
        self.addCleanup(i18n.setup, i18n.language())
        create_app()
        i18n.setup('it')

    def test_qstr_goes_through_the_catalogue_and_keeps_what_has_no_entry(self):
        engine = QQmlEngine()
        component = QQmlComponent(engine)
        component.setData(b'import QtQml\nQtObject { property string a: qsTr("No inverter"); '
                          b'property string b: qsTr("Inv. %1").arg(3); property string c: qsTr("Pianta") }',
                          QUrl('file:///qstr.qml'))
        obj = component.create()
        self.assertIsNotNone(obj, component.errorString())
        self.assertEqual((obj.property('a'), obj.property('b'), obj.property('c')), ('Nessun inverter', 'Inv. 3', 'Pianta'))

    def test_qstr_carries_the_context_and_the_plural(self):
        """R593: the same word in two ways by its context, and a plural with its number, from the QML."""
        engine = QQmlEngine()
        component = QQmlComponent(engine)
        component.setData(b'import QtQml\nQtObject { property string a: qsTr("Roof"); property string b: qsTr("Roof", "plan"); '
                          b'property string c: qsTr("{ok} check met", "{ok} checks met", 2).replace("{ok}", 2); '
                          b'property string d: qsTr("{ok} check met", "{ok} checks met", 1).replace("{ok}", 1); '
                          b'property string e: qsTr("%n thing", "%n things", 3); property string f: qsTr("Close", "none") }',
                          # «e» has no entry: Qt says the English singular (--check refuses a plural without its entry)
                          QUrl('file:///qstr_forms.qml'))
        obj = component.create()
        self.assertIsNotNone(obj, component.errorString())
        self.assertEqual([obj.property(k) for k in 'abcdef'],
                         ['Tetto', 'Copertura', '2 verifiche rispettate', '1 verifica rispettata', '3 thing', 'Chiudi'])

    def test_a_translation_asked_by_the_qml_loaders_thread_does_not_stop_the_window(self):
        """R593, 20/11/2026: the QML loader's thread translates its errors while the main thread waits for it in
        loadData. With the translator written in Python the process stopped at the first loadData, for good (seen with
        py-spy on Linux, reproduced on Windows); with Qt's own and the .qm the loads end."""
        child = (
            "import faulthandler\n"
            "faulthandler.dump_traceback_later(60, exit=True)\n"
            "from PySide6.QtCore import QByteArray, QUrl\n"
            "from PySide6.QtQml import QQmlApplicationEngine\n"
            "from meridiana.gui.application import create_app\n"
            "app = create_app('it')\n"
            "engine = QQmlApplicationEngine()\n"
            "for i in range(5):\n"
            "    source = 'import Not.There.Module%d 1.0' % i + chr(10) + 'import QtQml' + chr(10) + 'QtObject {}'\n"
            "    engine.loadData(QByteArray(source.encode()), QUrl('file:///stall%d.qml' % i))\n"
            "print('loaded', flush=True)\n")
        environment = dict(os.environ, PYTHONPATH=str(_setup.ROOT / 'src'), QT_QPA_PLATFORM='offscreen')
        run = subprocess.run([sys.executable, '-c', child], env=environment, capture_output=True, text=True,
                             timeout=180)
        self.assertIn('loaded', run.stdout, run.stdout + run.stderr[-3000:])

    def test_the_qml_says_its_language_when_it_changes(self):
        """i18n.setup() changes the language: Qt's translator takes that language's .qm (gui/application.py)."""
        engine = QQmlEngine()
        component = QQmlComponent(engine)
        component.setData(b'import QtQml\nQtObject { property string a: qsTr("Roof"); '
                          b'property string b: qsTr("{ok} check met", "{ok} checks met", 2) }', QUrl('file:///lang.qml'))
        i18n.setup('en')
        english = component.create()
        i18n.setup('it')
        italian = component.create()
        self.assertEqual([o.property(k) for o in (english, italian) for k in 'ab'],
                         ['Roof', '{ok} checks met', 'Tetto', '{ok} verifiche rispettate'])

    def test_the_bridge_in_english_has_both_forms_without_a_catalogue(self):
        import gettext
        from meridiana.gui.translator import message
        english = gettext.NullTranslations()
        self.assertEqual(message(english, '%n thing', '%n things', 1), '%n thing')
        self.assertEqual(message(english, '%n thing', '%n things', 2), '%n things')
        self.assertEqual(message(english, 'Roof', 'plan'), 'Roof')
        self.assertEqual(message(english, ''), '')

    def test_the_census_texts_are_in_italian(self):
        from meridiana.i18n import _, ngettext
        for text in ('Read the design rules: «{query}»', 'Power classes', 'Phasing out', 'column', 'W'):
            self.assertNotEqual(_(text), text, text)
        self.assertEqual(ngettext('{ok} check met', '{ok} checks met', 2).format(ok=2), '2 verifiche rispettate')


if __name__ == '__main__':
    unittest.main()
