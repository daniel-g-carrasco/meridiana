"""The QML's qsTr() through Meridiana's gettext catalogue (po/it.po): no Qt .qm file to build. A text without an entry
comes back as it is, so the texts written in Italian in a few QML files stay as they are."""
from PySide6.QtCore import QTranslator

from .. import i18n


class GettextTranslator(QTranslator):
    def translate(self, context, source, disambiguation=None, n=-1):
        # what has no entry comes back as the source (an empty answer would be taken as the translation)
        return i18n._(source) if source else source

    def isEmpty(self):
        return False


def install(app) -> None:
    """Once per application, before the first QML is loaded."""
    if getattr(app, "_meridiana_translator", None) is None:
        translator = GettextTranslator(app)
        app.installTranslator(translator)
        app._meridiana_translator = translator
