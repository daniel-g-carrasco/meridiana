"""The questions ready under Meridio's conversation (R108, 25/10/2026): after each answer, two or three that follow
from what was just said and from the state of the project, instead of the same three of the phase.

They are made here, by rules, on the PC, not asked of the model:
- they cost nothing and come at once: a structured tail asked of the model would add 40-60 tokens to every answer,
  five or six seconds with the local model at 9 tokens a second (study 14, 4.4), and a small model forgets the
  format or writes it in the middle;
- they work with the local model, with Claude and with no model at all, and nothing of the project leaves the PC
  to make them (the cloud sees a question only when the designer sends it, as any other, after the consent);
- they are tested: the same conversation gives the same questions.

What they follow, in this order: an offer to go somewhere at the end of the answer, a proposal just shown (never a
request for permission to propose, R197), the topics of the turn (the tools the model called and with what, the words of
the question and of the answer), the worst check still open, the phase; never a question already asked in the
conversation, never one that needs a result not computed yet. No Qt."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from ..i18n import _

N = 3                           # the rows under the conversation, numbered 1, 2, 3
CHECK_TEXT = 48                 # the characters of a check's text quoted in a question


@dataclass(frozen=True)
class Facts:
    """What the questions depend on in the project, read from the window (`facts_of`) or written by a test."""
    phase: str = ""
    worst: tuple = ()           # the texts of the checks still open, the most serious first (fail, then warn)
    year: bool = False          # the year of production computed
    strings: bool = False       # the plant has strings
    consumption: bool = False
    economics: bool = False
    subfields: int = 0
    variants: int = 1
    selected: str = ""          # the name of the sub-field or building selected, "" for none


def facts_of(host) -> Facts:
    """The facts of the window or of a test's host (assistant/tools.py lists what a host has)."""
    from . import tools
    items = list(host.checks() or [])
    worst = [it.text for level in ("fail", "warn") for it in items if it.level == level]
    energy = host.energy() or {}
    plant = host.plant() if hasattr(host, "plant") else None
    plant = plant if plant is not None else energy.get("plant")
    project = host.project
    kind, oid = (tuple(host.selection() or ()) + ("", ""))[:2]
    selected = tools.object_name(project, kind, oid) if kind in ("subfield", "building") and oid else ""
    return Facts(phase=host.phase(), worst=tuple(worst), year=energy.get("sim") is not None,
                 strings=bool(getattr(plant, "strings", None)), consumption=energy.get("load") is not None,
                 economics=energy.get("econ") is not None, subfields=len(project.subfields),
                 variants=len(getattr(project, "variants", []) or [1]), selected=selected)


# the topics, and the words that bring them (folded: lower case, no accents): a stem matches the start of a word,
# a stem ending with a space only the whole word («pr », not «prima»)

KEYWORDS = {
    "checks": ("verific", "problem", "errore", "errori", "avvis", "sistemar", "check", "warning", "issue"),
    "fire": ("vigili", "vvf", "antincend", "incend", "fire", "distanz", "varco", "varchi", "percors", "passagg",
             "compartiment", "camminament"),
    "shade": ("ombr", "shad", "ostacol", "obstacl"),
    "strings": ("string", "serie", "series", "uoc", "voc ", "tension", "voltag", "mppt", "temperatura minima"),
    "inverter": ("inverter", "dc/ac", "ottimizzator", "optimiz", "sovradimension"),
    "layout": ("dispos", "posa", "modul", "pannell", "fila", "file di", "layout", "falda", "tetto", "copertur",
               "sottocamp", "inclinaz", "tilt", "azimut", "orientam", "roof", "row ", "rows "),
    "production": ("producib", "produz", "produc", "kwh", "energia", "energy", "pvgis", "meteo", "irraggiam",
                   "weather"),
    "losses": ("perdit", "loss", "sporc", "soiling", "mismatch"),
    "pr": ("performance ratio", "pr ", "resa specifica", "specific yield", "kwh/kwp"),
    "assumptions": ("di serie", "default", "ipotes", "assum", "stima", "stimat", "estimat"),
    "consumption": ("consum", "carico", "carichi", "profilo", "curva", "autoconsum", "prelievo", "load"),
    "battery": ("batteri", "accumul", "storage"),
    "economics": ("econom", "investim", "rientro", "payback", "van ", "npv", "lcoe", "bollett", "costo", "costi",
                  "prezz", "conviene", "invest"),
    "rules": ("norma ", "norme ", "cei ", "spi ", "protezione di interfaccia", "connession", "allacc", "distribut",
              "regola", "regole", "legge", "decreto", "rule", "firmar"),
    "report": ("relazion", "report", "pdf", "cliente", "consegn", "tavol", "dxf", "ifc", "installator"),
    "variants": ("variant", "confront", "alternativ", "revision", "compare"),
    "howto": ("come faccio", "come si", "dove trovo", "dove si", "how do i", "menu", "tasto", "tasti",
              "scorciatoi", "shortcut"),
}
AREA_TOPICS = {"layout": "layout", "shade": "shade", "strings": "strings", "connection": "rules",
               "production": "production", "consumption": "consumption", "economics": "economics",
               "rules": "rules", "import": "checks", "defaults": "assumptions"}
SECTION_TOPICS = {"production": "production", "strings": "strings", "consumption": "consumption",
                  "economics": "economics"}
PHASE_TOPICS = {"model": ("layout", "fire", "shade"), "plant": ("strings", "inverter"),
                "production": ("production", "losses", "pr"), "consumption": ("consumption", "battery"),
                "economics": ("economics", "battery"), "report": ("report", "assumptions", "variants")}
RESULT_PHASES = ("production", "consumption", "economics", "report")
# An offer at the end of an answer. Only navigation gets a yes button: proposals are shown at once (R197).
OFFER = re.compile(r"\b(vuoi che|desideri che|posso (proporr|portart|preparar|mostrart)|te l[aeo] propong|"
                   r"ti propong|shall i|should i|do you want me|want me to)", re.IGNORECASE)
TAKE = re.compile(r"(portar|mostrar|take you|show you)", re.IGNORECASE)


def _always(_f: Facts) -> bool:
    return True


def _year(f: Facts) -> bool:
    return f.year


Pool = tuple[tuple[Callable[[Facts], str], Callable[[Facts], bool]], ...]


def pools() -> dict[str, Pool]:
    """Each topic's follow-ups, in the order they are offered, each with the condition that makes it sensible."""
    def short(f: Facts) -> str:
        return quote(f.worst[0]) if f.worst else ""
    return {
        "checks": (
            (lambda f: _("Which one do I fix first?"), lambda f: len(f.worst) >= 2),
            (lambda f: _("How do I fix «{check}»?").format(check=short(f)), lambda f: bool(f.worst)),
            (lambda f: _("Is there anything else to fix before the report?"), _always)),
        "fire": (
            (lambda f: _("Which fire brigade rule sets these distances?"), _always),
            (lambda f: _("Are the distances from the edges right for the fire brigade?"), _always),
            (lambda f: _("Can I gain modules and keep the passages free?"), _always)),
        "shade": (
            (lambda f: _("How much energy does the shade cost?"), _year),
            (lambda f: _("Which sub-field suffers most from the shade?"), lambda f: f.subfields > 1),
            (lambda f: _("What if I kept the modules out of the obstacles' shade?"), _always)),
        "strings": (
            (lambda f: _("How many modules in series at most, and why?"), _always),
            (lambda f: _("Does this string hold at -10 °C?"), lambda f: f.strings),
            (lambda f: _("Are the strings right for this inverter?"), lambda f: f.strings)),
        "inverter": (
            (lambda f: _("Is the DC/AC ratio reasonable here?"), _always),
            (lambda f: _("Would a smaller or a larger inverter be better?"), _always),
            (lambda f: _("Do power optimizers make sense here?"), _always)),
        "layout": (
            (lambda f: _("Is the layout of «{name}» right?").format(name=f.selected), lambda f: bool(f.selected)),
            (lambda f: _("Where can I gain power without shadows?"), _always),
            (lambda f: _("Would another tilt or row pitch give more energy?"), _year)),
        "production": (
            (lambda f: _("What is missing to compute the year?"), lambda f: not f.year),
            (lambda f: _("Which losses weigh most?"), _year),
            (lambda f: _("Is this specific yield plausible for the site?"), _year),
            (lambda f: _("How far is it from PVGIS?"), _year),
            (lambda f: _("Where do the weather data come from?"), _always)),
        "losses": (
            (lambda f: _("Which of these losses can I reduce?"), _year),
            (lambda f: _("Which values behind it are Meridiana's defaults?"), _year),
            (lambda f: _("Which losses weigh most?"), _year),
            (lambda f: _("Which losses does Meridiana count, and how?"), _always)),
        "pr": (
            (lambda f: _("Why is the performance ratio this one?"), _year),
            (lambda f: _("Which losses lower the PR most?"), _year),
            (lambda f: _("Which values behind it are Meridiana's defaults?"), _year)),
        "assumptions": (
            (lambda f: _("Where does this figure come from?"), _always),
            (lambda f: _("Which values are still at their default?"), _always),
            (lambda f: _("How do I put a value of mine instead of the default?"), _always)),
        "consumption": (
            (lambda f: _("Does this load profile look plausible?"), lambda f: f.consumption),
            (lambda f: _("How much of the production is used on site?"), lambda f: f.consumption and f.year),
            (lambda f: _("How do I import the real load curve?"), _always)),
        "battery": (
            (lambda f: _("Would a battery help here?"), _always),
            (lambda f: _("How big should the battery be?"), lambda f: f.consumption),
            (lambda f: _("What would change with a battery?"), lambda f: f.economics)),
        "economics": (
            (lambda f: _("What weighs most on the payback?"), lambda f: f.economics),
            (lambda f: _("Is the investment worth it?"), lambda f: f.economics),
            (lambda f: _("Which prices and costs are still at their default?"), _always)),
        "rules": (
            (lambda f: _("Which rules apply to this plant?"), _always),
            (lambda f: _("What is the source of this rule?"), _always),
            (lambda f: _("Who may sign this project?"), _always)),
        "report": (
            (lambda f: _("Is the report complete for the client?"), _always),
            (lambda f: _("Which values are still at their default?"), _always),
            (lambda f: _("What should the installer get with the drawings?"), _always)),
        "variants": (
            (lambda f: _("How do I compare the variants?"), _always),
            (lambda f: _("Which variant gives the most energy?"), lambda f: f.year and f.variants > 1),
            (lambda f: _("How do I try another layout without losing this one?"), _always)),
        "howto": (
            (lambda f: _("Is there a key for it?"), _always),
            (lambda f: _("Where is it in the menus?"), _always),
            (lambda f: _("Take me there"), _always)),
        "proposal": (
            (lambda f: _("Why exactly this change?"), _always),
            (lambda f: _("Is there another way?"), _always),
            (lambda f: _("How much does the energy change if I apply it?"), _year)),
    }


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").lower())
    return " ".join("".join(ch for ch in text if not unicodedata.combining(ch)).split())


def quote(text: str, limit: int = CHECK_TEXT) -> str:
    """A check's text short enough for a question: cut at a word, with «…»."""
    text = " ".join((text or "").split()).rstrip(".")
    if len(text) <= limit:
        return text
    cut = text[:limit + 1].rsplit(" ", 1)[0].rstrip(",;:")    # a word that ends at the limit stays
    return cut + "…"


def plain_question(content: str) -> str:
    """A question as the designer typed it, without the lines the window puts before it (where they are, what they
    did with the proposals: context.question, ui/assistant_chat.Chat._start)."""
    lines = (content or "").split("\n")
    while len(lines) > 1 and lines[0].startswith("(") and lines[0].endswith(")"):
        lines.pop(0)
    return "\n".join(lines).strip()


def last_turn(messages: list[dict]) -> tuple[str, str, list[dict], list[dict]]:
    """The last question, the words of its answer (every round), the tools called and their results."""
    start = max((n for n, m in enumerate(messages) if m["role"] == "user"), default=-1)
    if start < 0:
        return "", "", [], []
    question = plain_question(messages[start]["content"])
    said, calls, results = [], [], []
    for m in messages[start + 1:]:
        if m["role"] == "assistant":
            if (m.get("content") or "").strip():
                said.append(m["content"].strip())
            calls += m.get("calls") or []
        elif m["role"] == "tool":
            results.append(m)
    return question, "\n".join(said), calls, results


def text_topics(text: str) -> dict[str, int]:
    """The topics a text speaks of, each with how many of its words it has."""
    words = " " + re.sub(r"[^\w/°-]+", " ", fold(text)) + " "
    found = {}
    for topic, stems in KEYWORDS.items():
        n = sum(words.count(" " + stem) for stem in stems)
        if n:
            found[topic] = n
    return found


def tool_topics(calls: list[dict]) -> list[str]:
    """The topics of the tools the model called, in the order it called them."""
    out = []
    for c in calls:
        name, args = c.get("name", ""), c.get("arguments") or {}
        if name == "read_checks":
            out.append(AREA_TOPICS.get(args.get("area", ""), "checks"))
            out.append("checks")
        elif name in ("read_results", "read_pedigree"):
            section = args.get("section") or args.get("calculation") or ""
            if section in SECTION_TOPICS:
                out.append(SECTION_TOPICS[section])
            if name == "read_pedigree":
                out.append("assumptions")
        elif name == "read_rules":
            out.append("rules")
        elif name == "search_manual":
            out.append("howto")
        elif name == "go_to":
            kind, oid = args.get("kind", ""), args.get("id", "")
            if kind in ("subfield", "building"):
                out.append("layout")
            elif kind == "phase" and oid in PHASE_TOPICS:
                out.append(PHASE_TOPICS[oid][0])
    return out


def topics(messages: list[dict]) -> list[str]:
    """The topics of the last turn, the strongest first: the tools the model called (what it read is what the
    answer is about), then the words of the question (twice as much) and of the answer."""
    question, answer, calls, _results = last_turn(messages)
    score: dict[str, float] = {}
    for n, topic in enumerate(tool_topics(calls)):
        score[topic] = score.get(topic, 0) + 3 - n * 0.01
    for topic, n in text_topics(question).items():
        score[topic] = score.get(topic, 0) + 2 * n
    for topic, n in text_topics(answer).items():
        score[topic] = score.get(topic, 0) + n
    return sorted(score, key=lambda t: -score[t])


def offer(messages: list[dict]) -> str:
    """What the answer offers at its end: "take" (to bring the designer somewhere), "propose", or ""."""
    _question, answer, _calls, _results = last_turn(messages)
    tail = answer.strip()
    if not tail.endswith("?"):
        return ""
    last = re.split(r"(?<=[.!:])\s+|\n+", tail)[-1]
    if not OFFER.search(last):
        return ""
    return "take" if TAKE.search(last) else "propose"


def proposed(messages: list[dict]) -> bool:
    """Whether the last turn showed a proposal (a card the designer may apply)."""
    _question, _answer, calls, results = last_turn(messages)
    names = {c["id"]: c["name"] for c in calls}
    return any(names.get(r.get("id")) in ("propose_fix", "propose_edit") and not r.get("error") for r in results)


def asked_in(messages: list[dict]) -> set[str]:
    return {fold(plain_question(m["content"])) for m in messages if m["role"] == "user"}


def suggest(messages: list[dict], facts: Facts, n: int = N, phase_questions: tuple = ()) -> list[str]:
    """Up to `n` questions ready for now: what the last answer offers, what it was about, the worst check still
    open, the phase (`phase_questions` the last resort, phases.py's three)."""
    pool = pools()
    asked = asked_in(messages)
    chosen: list[str] = []

    def take(texts, most: int) -> None:
        added = 0
        for text in texts:
            if len(chosen) >= n or added >= most:
                return
            key = fold(text)
            if text and key not in asked and all(fold(c) != key for c in chosen):
                chosen.append(text)
                added += 1

    def of(topic: str) -> list[str]:
        return [ask(facts) for ask, sensible in pool.get(topic, ()) if sensible(facts)]

    kind = offer(messages)
    if kind == "take":
        take([_("Yes, take me there"), _("First tell me why")], 2)
    if proposed(messages):
        take(of("proposal"), 2)
    found = topics(messages)
    if found:
        take(of(found[0]), 2)
    open_check = [_("How do I fix «{check}»?").format(check=quote(facts.worst[0]))] if facts.worst else []
    if "checks" not in found[:1]:
        take(open_check, 1)
    for topic in found[1:3]:
        take(of(topic), 1)
    if not facts.year and facts.phase in RESULT_PHASES:
        take([_("What is missing to compute the year?")], 1)
    for topic in PHASE_TOPICS.get(facts.phase, ()):
        take(of(topic), 1)
    for topic in PHASE_TOPICS.get(facts.phase, ()):
        take(of(topic), n)
    if len(chosen) < 2:                     # a phase this module does not know: its three of phases.py
        take(list(phase_questions), n)
    return chosen
