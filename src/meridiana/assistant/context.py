"""What Meridio is told (study 14, 5.2 and 8): his instructions, who he is and how he answers, are in persona.py
(R106), the same at every round and for every provider; what changes, the phase open and the selection, goes with
the question (`question`). No Qt."""

from __future__ import annotations

from .. import i18n
from . import persona

LANGUAGES = persona.LANGUAGES


def language() -> str:
    """The language of the program's catalogue in use (i18n.language): "it" or "en"."""
    code = i18n.language().lower()
    return code if code in LANGUAGES else "en"


def system(name: str = "Meridio", lang: str | None = None) -> str:
    """Meridio's instructions (persona.py, R106), the same for every provider, in the program's language."""
    return persona.system(name, lang or language())


def question(text: str, phase: str = "", selection: str = "") -> str:
    """The designer's question with where they are: «(Phase: Modello. Selected: sottocampo Sud.)»."""
    where = []
    if phase:
        where.append(f"Phase: {phase}.")
    if selection:
        where.append(f"Selected: {selection}.")
    return f"({' '.join(where)})\n{text}" if where else text
