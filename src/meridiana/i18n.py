"""GNU gettext set-up. Catalogues live in po/ and are compiled by
tools/compile_po.py (to locale/ in a checkout, to /app/share/locale in the
Flatpak, to share/locale in the Windows build). Source strings are English;
Italian is the first translation."""

from __future__ import annotations

import gettext
import os
import sys
from pathlib import Path

from . import TEXTDOMAIN

_translation: gettext.NullTranslations = gettext.NullTranslations()


def _locale_dirs():
    root = Path(__file__).resolve().parent.parent.parent
    yield root / "locale"                     # source checkout
    if getattr(sys, "frozen", False):          # the Windows build
        yield Path(getattr(sys, "_MEIPASS", "")) / "share" / "locale"
    for prefix in ("/app", "/usr/local", "/usr"):
        yield Path(prefix) / "share" / "locale"


def _system_languages() -> list[str]:
    """Windows sets none of the variables: the language of its interface
    ("it_IT"), as GTK reads it for its own strings."""
    if os.name != "nt":
        return []
    try:
        import ctypes
        import locale
        name = locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage())
    except (AttributeError, OSError):
        return []
    return [name] if name else []


def setup(language: str = "") -> None:
    """Load the catalogue for the desktop language, or for `language` (a
    preference: "it", "en"), if we have one."""
    global _translation
    languages = [language] if language else []
    if not languages:
        for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
            value = os.environ.get(var)
            if value:
                languages = [part.split(".")[0] for part in value.split(":") if part]
                break
        else:
            languages = _system_languages()
    _translation = gettext.NullTranslations()
    for directory in _locale_dirs():
        if gettext.find(TEXTDOMAIN, str(directory), languages=languages or None):
            _translation = gettext.translation(TEXTDOMAIN, str(directory), languages=languages or None)
            return


def translation_for(language: str) -> gettext.NullTranslations:
    """The catalogue of one language, whatever the desktop language is
    (English has no catalogue: the source strings are returned)."""
    for directory in _locale_dirs():
        if gettext.find(TEXTDOMAIN, str(directory), languages=[language]):
            return gettext.translation(TEXTDOMAIN, str(directory), languages=[language])
    return gettext.NullTranslations()


def _(message: str) -> str:
    return _translation.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    return _translation.ngettext(singular, plural, n)


def pgettext(context: str, message: str) -> str:
    return _translation.pgettext(context, message)


def language() -> str:
    """The language of the window: the one of the catalogue loaded, English without one."""
    return (_translation.info().get("language") or "en").split("_")[0]


def number(value: float, decimals: int = 2, sign: bool = False, grouping: bool = False) -> str:
    """A measure as the language of the window writes it: 3,58 in Italian, 3.58 in English; with grouping
    12.345,6 and 12,345.6. The spin boxes follow the same language (app.py sets Qt's default locale)."""
    text = f"{value:{'+' if sign else ''}{',' if grouping else ''}.{decimals}f}"
    return text.translate(str.maketrans(",.", ".,")) if language() == "it" else text


def count(n: int) -> str:
    """A number as the locale writes it (1.200 in Italian, 1,200 in
    English), for the texts that show counts."""
    try:
        return f"{n:n}"
    except ValueError:
        return str(n)
