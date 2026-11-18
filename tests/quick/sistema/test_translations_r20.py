"""The Quick in Italian: the texts of the census of 07/11/2026 have their entry, and the QML's qsTr goes through
po/it.po (StringLabels.qml: «No inverter», «Inv. %1» came out in English)."""
import unittest

import _setup
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from meridiana import i18n
from meridiana.quick.app import create_app


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

    def test_the_census_texts_are_in_italian(self):
        from meridiana.i18n import _, ngettext
        for text in ('Read the design rules: «{query}»', 'Power classes', 'Phasing out', 'column', 'W'):
            self.assertNotEqual(_(text), text, text)
        self.assertEqual(ngettext('{ok} check met', '{ok} checks met', 2).format(ok=2), '2 verifiche rispettate')


if __name__ == '__main__':
    unittest.main()
