"""A tooltip's text as the Quick shows it (R162, Daniel 25/10/2026: «una larghezza massima in cui il testo va in
colonna ... una bella formattazione ai contenuti come fanno programmi tipo VS Code»): «Name (key)» and the explanation
under it as the name semibold, the key muted beside it, the explanation in the tooltip's softer ink; one line as it is;
wrapped at TIP_WIDTH pixels when longer (gui/backend/tokens.py lays it out). The little windows of the Widgets
(menus, lists, Qt's own tooltip label) stay in ui/popups.py until that window goes."""

from __future__ import annotations

import html
import re

from PySide6 import QtGui
from PySide6.QtGui import QKeySequence

from meridiana.app.interface import theme_colors
from .design import Space, Type

TIP_WIDTH = 340                 # a tooltip's text wraps at this width (R162): some 45 characters of the text
TIP_SOFT, TIP_KEY = theme_colors.TIP_SOFT, theme_colors.TIP_KEY   # the explanation and the key (R615: in the theme)
_DEFAULT = theme_colors.derive(theme_colors.DEFAULT_SEED, False).tokens
# the tooltip's inks when none is given: the theme's text on the menus' ground (R615)
_STATE = {"tip": _DEFAULT["text"], "tip_bg": _DEFAULT["card"]}
_HEAD = re.compile(r"^(?P<name>.+?) \((?P<key>[^()]+)\)$")


def _is_key(text: str) -> bool:
    """Whether `text` is a key as the window writes it («Ctrl+1», «F1», «W»), not words in brackets: in the system's
    words (the Widgets wrote «Canc» with Qt's Italian catalogue) or in Qt's portable ones (the Quick writes «Del»
    in every language, shortcuts.py)."""
    for form in (QKeySequence.SequenceFormat.NativeText, QKeySequence.SequenceFormat.PortableText):
        seq = QKeySequence.fromString(text, form)
        if not seq.isEmpty() and seq.toString(form) == text:
            return True
    return False


def tip_html(text: str, ink: str | None = None, ground: str | None = None) -> str:
    """A tooltip's text as the label shows it: «Name (key)» on the first line and the explanation on the next ones
    as the name (semibold when an explanation follows), the key muted beside it, the explanation softer under it;
    a text already rich as it is."""
    if QtGui.Qt.mightBeRichText(text):                    # (QtGui's Qt: QtCore's has not this one)
        return text
    ink = ink or _STATE["tip"]
    ground = ground or _STATE["tip_bg"]
    lines = [line.strip() for line in text.split("\n")]
    head, body = lines[0], [line for line in lines[1:] if line]
    m = _HEAD.match(head)
    name, key = (m["name"], m["key"]) if m and _is_key(m["key"]) else (head, "")
    soft, muted = theme_colors.mix(ink, ground, TIP_SOFT), theme_colors.mix(ink, ground, TIP_KEY)
    weight = f"font-weight:{Type.SEMIBOLD};" if body else ""
    out = f'<p style="margin:0;{weight}">{html.escape(name)}'
    if key:
        out += f'&nbsp;&nbsp;<span style="color:{muted};font-weight:{Type.REGULAR}">{html.escape(key)}</span>'
    out += "</p>"
    for line in body:
        out += f'<p style="margin:0;margin-top:{Space.XS}px;color:{soft}">{html.escape(line)}</p>'
    return out
