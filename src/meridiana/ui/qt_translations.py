"""Qt's own words in the language of the window (Daniel, 23/10/2026, R26: the catalogue said «OK» and «Cancel»): the
standard buttons, the file dialogs, the context menus of the fields. Qt ships them as qtbase_<language>.qm in its
translations folder (QLibraryInfo); PySide6's wheel has them in PySide6/translations on Windows and in
PySide6/Qt/translations on Linux, and PyInstaller keeps the same places under its own folder (the run-time hook's
qt.conf points QLibraryInfo there; the Windows bundle's self-test checks it, task 18f)."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QLibraryInfo, QTranslator

from .. import log

_INSTALLED: list = []


def folders() -> list[str]:
    """Where qtbase_<language>.qm may be: Qt's own place first."""
    out = [QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)]
    try:
        import PySide6
        here = Path(PySide6.__file__).parent
        out += [str(here / "translations"), str(here / "Qt" / "translations")]
    except (ImportError, TypeError):
        pass
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
        out += [str(base / "PySide6" / "translations"), str(base / "PySide6" / "Qt" / "translations"),
                str(base / "share" / "qt" / "translations")]
    return [f for f in dict.fromkeys(out) if f]


def install(app, language: str) -> bool:
    """Qt's words in `language` ("it"); English, or a language Qt has no catalogue for, leaves Qt's own. True when
    a catalogue was loaded."""
    for old in _INSTALLED:
        app.removeTranslator(old)
    _INSTALLED.clear()
    if not language or language == "en":
        return False
    translator = QTranslator(app)
    for folder in folders():
        if translator.load(f"qtbase_{language}", folder):
            app.installTranslator(translator)
            _INSTALLED.append(translator)
            return True
    log.complain(f"Qt's translations for {language}", FileNotFoundError(", ".join(folders())))
    return False
