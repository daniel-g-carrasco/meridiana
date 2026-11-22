"""The QML's qsTr() through the app's own catalogue: po/<language>.po, compiled by tools/compile_po.py into Qt's .qm
beside gettext's .mo (locale/<language>/LC_MESSAGES/<domain>.qm) and read by the QTranslator of C++. po/ stays the
only source: the .qm is made from it, never written by hand. A text without an entry comes back as it is.

Never a translator written in Python (R593, 20/11/2026): Qt translates on its own threads too (the QML loader's,
for an error of the compiled cache, while the main thread waits for it in loadData). A translate() in Python there
waits for the interpreter's lock, which the waiting main thread holds: the program stops for good.

The three forms, the same catalogue as Python's _(), pgettext() and ngettext():

  qsTr("Roof")                          the entry «Roof»                       _("Roof")
  qsTr("Roof", "plan")                  the entry with msgctxt "plan"          pgettext("plan", "Roof")
                                        (without one, the plain entry)
  qsTr("%n module", "%n modules", n)    the plural entry; Qt writes n for %n   ngettext("%n module", "%n modules", n)

With a number the second argument is the English plural, not Qt's disambiguation: gettext needs both English forms;
English has a .qm of its plurals alone. A plural with a context is only in Python (npgettext). tools/compile_po.py
extracts the three forms; QT_TR_NOOP("...") and QT_TRANSLATE_NOOP("context", "...") mark a text the QML translates
later. No app is imported here: install() is given the .qm (i18n.qt_catalogue())."""
from pathlib import Path

from PySide6.QtCore import QTranslator


def message(catalogue, source: str, disambiguation: str = '', n: int = -1) -> str:
    """What qsTr(source, disambiguation, n) says through a gettext catalogue (gettext, pgettext, ngettext): for a
    text Python translates on the main thread in the QML's forms (the kit's Theme.tr)."""
    if not source:
        return source
    if n is not None and n >= 0 and disambiguation:
        return catalogue.ngettext(source, disambiguation, n)
    if disambiguation:
        translated = catalogue.pgettext(disambiguation, source)
        return translated if translated != source else catalogue.gettext(source)
    return catalogue.gettext(source)


def install(app, path) -> bool:
    """Qt's translator for the QML with the catalogue `path` (a .qm), in place of the one this function installed
    before: at start and when the language changes (then the engine's retranslate()). Without a file the QML says
    its source texts. True when a catalogue is in place."""
    old = getattr(app, '_qml_translator', None)
    if old is not None and path and getattr(app, '_qml_catalogue', None) == str(path):
        return True                 # the same catalogue: nothing to retranslate
    app._qml_catalogue = str(path) if path else None
    if old is not None:
        app.removeTranslator(old)
        old.deleteLater()
    app._qml_translator = None
    if not path or not Path(path).is_file():
        return False
    translator = QTranslator(app)
    if not translator.load(str(path)):
        translator.deleteLater()
        return False
    app.installTranslator(translator)
    app._qml_translator = translator
    return True
