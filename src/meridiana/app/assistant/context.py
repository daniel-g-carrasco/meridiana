"""What Meridio is told (study 14, 5.2 and 8): his instructions, who he is and how he answers, are in persona.py
(R106), the same at every round and for every provider; what changes, the phase open and the selection, goes with
the question (`question`). No Qt."""

from __future__ import annotations

from meridiana import i18n
from meridiana.i18n import _
from . import persona, privacy

LANGUAGES = persona.LANGUAGES

# R649 (Daniel 15/11/2026: with the program in English the local model answered in Italian, the language of what it
# read): the rule said again at the end of the instructions, where a small model keeps it best, and in the question's
# head (`question`)
ANSWER_IN = ("The language: answer only in {language}, whatever the language of what you read (the manual, a law, a "
             "standard, a document, the names in the project). Quote those words as they are, in quotation marks, "
             "and write everything else in {language}.")


def language() -> str:
    """The language of the program's catalogue in use (i18n.language): "it" or "en"."""
    code = i18n.language().lower()
    return code if code in LANGUAGES else "en"


def system(name: str = "Meridio", lang: str | None = None, *, profile_id: str = "it", cloud: bool = False) -> str:
    """Meridio's instructions (persona.py, R106), the same for every provider, in the program's language. The
    sentence on the placeholders of what is withheld goes only to a cloud model (study 50, 3.7): the only one that
    sees them, and to a small local model it read as leave to coin its own («[PHASE]»)."""
    lang = lang or language()
    text = persona.system(name, lang, profile_id=profile_id) + "\n\n" + ANSWER_IN.format(language=LANGUAGES[lang])
    return text + "\n\n" + privacy.INSTRUCTION if cloud else text


def question(text: str, place: str = "", selection: str = "") -> str:
    """The designer's question with where they are, in their words and language (study 50, 3.7): «(Sono in:
    Impianto. Selezionato: sottocampo Sud.)». No label without its value: a small model read «Phase:» and wrote
    «[PHASE]»."""
    where = []
    if place:
        where.append(_("I am in: {place}.").format(place=place))
    if selection:
        where.append(_("Selected: {selection}.").format(selection=selection))
    if where:
        # the program's language, said in it (in Italian «Rispondi in italiano.»): R649
        where.append(_("Answer in English."))
    return f"({' '.join(where)})\n{text}" if where else text


def kind_words() -> dict:
    """The kinds of the objects as the designer names them."""
    return {"building": _("Building").lower(), "subfield": _("Sub-field").lower(),
            "exclusion": _("Exclusion").lower()}


def selection_words(project, kind: str, oid: str) -> str:
    """What is selected, for the question's head: «sottocampo Sud»; nothing for the site."""
    if not kind or kind == "site":
        return ""
    from .tools import object_name
    return f"{kind_words().get(kind, kind)} {object_name(project, kind, oid)}"


def known_words(place: str = "") -> dict:
    """The words of the program a model may put in square brackets, with what they stand for (text.mend): the phases
    by their id, the kinds of the objects, and the place of the question («[PHASE]»)."""
    from meridiana.app.interface import phases
    known = {p.id: p.title for p in phases.phases()}
    known.update(kind_words())
    if place:
        known.update({"PHASE": place, "FASE": place})
    return known
