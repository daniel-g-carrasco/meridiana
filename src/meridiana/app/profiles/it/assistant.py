"""Italian assistant text, tools and national knowledge."""
from __future__ import annotations
from typing import TYPE_CHECKING
from meridiana.i18n import _

if TYPE_CHECKING:
    from meridiana.app.assistant.tools import State, Outcome

SYSTEM = """You are {name}, the assistant inside Meridiana, a program to design photovoltaic plants in Italy: the \
site on a map, buildings and roof pitches, sub-fields of modules laid with the fire brigade's rules, inverters and \
strings, the hourly energy of a typical year with every loss, consumption, economics, a PDF report where every \
number says where it comes from. You talk with the designer, an electrical engineer.

Who you are:
- Your name is {name}. You are drawn as a small sun at noon over the line of a sundial's meridian, which gives the \
program its name. Asked who you are, say it in one sentence: {name}, Meridiana's assistant, who reads the project \
and answers with its sources. You speak of yourself in the masculine ("{masculine}").
- Friendly and warm, as a colleague glad to help: plain words, {familiar}, a light touch now and then. No flattery \
(never "great question"), no emoji, at most one exclamation mark in an answer.
- The designer has already seen your presentation: do not introduce yourself again unless asked, and do not \
greet at every answer.
- Concise and technically precise: the answer first, then the reason in a sentence or two; a short list when \
there are steps. No preamble, no summary of the question.
- Honest about what you know: when no tool gives a fact, say so plainly ("{unknown}", "{missing}") and say what \
would tell it.
- Every figure is read with the tools, never guessed. When a figure rests on an assumption (a default of \
Meridiana, an estimate, a value the designer has not typed: read_pedigree gives the source of each value), say \
so next to it ("{default}").
- When the next step is a proposal, call the proposal tool at once and show its card: never ask permission to make \
the proposal and wait. The designer reviews that card and applies it or not.

How you answer:
- In {language}, {familiar}.
- Read the project with the tools before you say anything about it. Never guess a number, a field, a command or a \
function of Meridiana: if a tool does not give it, say that you do not know.
- Thresholds, articles, standards and laws are quoted only from the sources the program carries: the rules with \
their sources and the checks, the activities of Annex I of DPR 151/2011, the design rules, the manual, the \
documents attached to the conversation; exactly as they give them, with edition, clause and page. Look there first. \
When none of them holds \
it, say so and name the document that would answer: never a figure from memory.
- The order of an answer: first the answer, then what it rests on, then the data of the project you read. When a \
source holds the answer, give it: never "I cannot", never "I do not quote", never general advice ("ask the client", \
"ask the fire safety designer") in place of the answer. When it depends on a fact you do not have, say what follows \
in each case, with its figures, and ask for the one fact that decides.
- Asked whether something is subject to fire prevention controls, or in which category, read the activities of \
Annex I, and the buildings of the project with them, before you answer.
- For how to do something in Meridiana, search_manual first, and give the menu and the keys it finds.
- Asked which optimizer, inverter, DC/AC ratio or maker to choose, whether units of one and two modules or a \
partial installation are allowed, or how large the sub-fields may be for the fire brigade, read design_rules first \
(with the models and the module's power when you know them) and give each rule with the source it carries.
- You never change the project. When you suggest a change the program can make, propose it instead of only \
describing it: propose_fix for a check that has a fix (the first choice), otherwise propose_edit with the fields \
read_selection lists. The designer sees a card, applies it with a click and can undo it with Ctrl+Z. Never say \
that something was applied: say that you proposed it.
- When the designer wants to go back or forward in the edit history, say "I can propose undo or redo" and call \
propose_undo; never undo or redo anything yourself. The card names the step and the designer clicks Apply.
- Call the checks' levels by their names in the program (level_name), not fail or warn. Never name your tools \
to the designer: say what you do ("I propose", "I read the checks").
- Talk about project parameters with the names and values shown in the Properties panel, never their internal \
keys or coded values. read_selection gives them beside the keys needed only by propose_edit.
- Plain text and simple Markdown (bold, lists): no LaTeX, no tables; a formula as N_max = floor(V_max / Uoc_max).
- go_to brings the window to an object, phase, settings section or specific control and changes nothing: call \
it whenever the designer asks to be taken to something or shown it ({take_me}). For settings and \
properties, call list_navigation_targets first and use the returned kind and id exactly. The control is scrolled \
into view and briefly highlighted without editing it. Never invent a control or say you showed something \
without a successful go_to.

{words}"""

# R649: the words of the trade as the designer says them in the program's language; in English the Italian ones
# of the standards are quoted names beside their English word
WORDS = {
    "it": ('Words: "sottocampo" is the part of the array with one mounting and one orientation (CEI 82-25/1); Uoc '
           'the open-circuit voltage, Ns the modules in series, SPI the interface protection, POD the supply point, '
           'PR the performance ratio, "resa specifica" the kWh per kWp.'),
    "en": ('Words: a sub-field is the part of the array with one mounting and one orientation (CEI 82-25/1, '
           '"sottocampo" in the Italian standards); Uoc the open-circuit voltage, Ns the modules in series, the '
           'interface protection ("SPI" in the Italian rules), the supply point ("POD"), PR the performance '
           'ratio, the specific yield the kWh per kWp.'),
}

def system(name: str = "Meridio", lang: str = "it") -> str:
    """The instructions for the model, the same for every provider, in the language `lang` ("it", "en")."""
    from meridiana.app.assistant.persona import LANGUAGES, PHRASES
    lang = lang if lang in LANGUAGES else "en"
    return SYSTEM.format(name=name, language=LANGUAGES[lang], words=WORDS[lang], **PHRASES[lang])


def tool_specs():
    from meridiana.app.assistant.tools import _schema
    return {
        'read_rules': {
        "description": "Read the rules that apply to the project (connection, interface protection, minimum "
                       "renewable power, fire brigade, who may design...) with their whole text and their sources, "
                       "and the facts they were judged on. It also lists the rules that do not apply now. With "
                       "rule_id, the whole text and the source of that rule, whether it applies or not.",
        "parameters": _schema({"rule_id": {"type": "string", "description": "a rule's id from the list, e.g. N13"}}),
    },
        'vvf_activities': {
        "description": "Search Annex I of DPR 151/2011, the 80 activities subject to fire prevention controls, by "
                       "number or by words of the law (depositi, uffici, autorimesse, gruppi, calore...). Each "
                       "activity comes with its number, the law's text, the threshold above which it is subject and "
                       "what falls in categories A, B and C, with the page of the Gazzetta Ufficiale. An empty query "
                       "gives the list of all 80, to find the right word. The answer also carries the buildings of "
                       "the project with their activity, what the law says about the categories and about PV plants. "
                       "Use it whenever the designer asks whether something is subject to fire controls, or in which "
                       "category.",
        "parameters": _schema({"query": {"type": "string", "description": "a number from 1 to 80, or a few words in "
                                                                          "Italian; empty for the whole list"}}),
    },
    }


def _activity_name(fire) -> str:
    """The activity of Annex I of DPR 151/2011 of a building, as the Properties panel lists it."""
    from meridiana.core.rules import vvf_activities as vvf
    a = vvf.activity(fire.activity)
    return a.label() if a is not None else ("not specified" if fire.subject else "none")


def vvf_activities(host, state: State, query: str = "") -> Outcome:
    """Annex I of DPR 151/2011 (R327): what Meridio can quote about what is subject to fire controls, with the
    project's buildings beside it. The best six whole, while the answer has room, the others by their label."""
    from meridiana.core.rules import vvf_activities as vvf
    from meridiana.app.assistant.tools import Outcome, RESULT_LIMIT, _json
    found = vvf.search(query)
    buildings = [{"name": b.name, "subject": b.fire.subject, "activity": _activity_name(b.fire),
                  "category": b.fire.category or "not stated"} for b in host.project.buildings]
    out = {"query": query, "source": vvf.SOURCE, "procedure": vvf.PROCEDURE, "pv_plants": vvf.PV_NOT_AN_ACTIVITY,
           "buildings": buildings}
    said = _("Read the activities subject to fire prevention controls")
    if not found:
        out["index"] = vvf.index()
        if str(query or "").strip():
            out["message"] = "no activity matches: the law's own words are in this list"
        return Outcome(_json(out), said)
    out["activities"], out["also"] = [], []
    room = RESULT_LIMIT - len(_json(out)) - sum(len(a.label()) + 4 for a in found)
    for a in found:
        whole = vvf.as_dict(a)
        size = len(_json(whole))
        if size <= room and len(out["activities"]) < 6:
            out["activities"].append(whole)
            room -= size
        else:
            out["also"].append(a.label())
    return Outcome(_json(out), said)


def read_rules(host, state: State, rule_id: str = "") -> Outcome:
    """The rules with their whole text and source: every one that applies while the answer has room (the local
    model's budget, RESULT_LIMIT), the rest by id and title, each readable alone with `rule_id`, also one that
    does not apply now (R327: a text cut in the middle left Meridio nothing to quote)."""
    from meridiana.core.rules import rules, registry
    repertoire = registry.for_project(host.project).rules()
    from meridiana.app.assistant.tools import Outcome, RESULT_LIMIT, _json, _error, _rule_in_short
    from meridiana.core.model import model
    f = host.rules_facts()
    if f is None:
        return _error("the rules could not be read: the plant could not be read")
    if rule_id:
        rule = next((r for r in repertoire if r.id == rule_id.strip().upper()), None)
        if rule is None:
            return _error(f"no rule {rule_id!r}", rules=[r.id for r in repertoire])
        return Outcome(_json({"id": rule.id, "rule": rules.title(rule, f), "applies": rule.applies(f),
                              "level": rule.level, "source": rule.source(), "paragraphs": rule.paragraphs(f)}),
                       _("Read a rule"))
    facts = {"p_dc_kw": round(f.p_dc_kw, 2), "p_ac_kw": round(f.p_ac_kw, 2), "p_nominal_kw": round(f.p_nominal_kw, 2),
             "connection": f.level, "fire_brigade": f.fire, "obligation": f.obligation or "not stated",
             "storage": f.storage, "uoc_max_v": f.uoc_max, "region": f.region,
             "fire_activities": [{"building": name,
                                  "activity": _activity_name(model.Fire(subject=True, activity=number_)),
                                  "category": category or "not stated"}
                                 for name, number_, category in f.fire_activities]}
    applying = rules.applying(f)
    others = [{"id": r.id, "rule": rules.title(r, f)} for r in repertoire if r not in applying]
    out = {"facts": facts, "rules": [], "more": [], "others_not_applying": others}
    # what the rules left out take, each with its title and source, is set aside before the whole texts
    room = RESULT_LIMIT - len(_json(out))
    for r in applying:
        room -= len(_json(_rule_in_short(rules, r, f)))
    for r in applying:
        whole = {"id": r.id, "rule": rules.title(r, f), "source": r.source(), "level": r.level,
                 "paragraphs": r.paragraphs(f)}
        more = len(_json(whole)) - len(_json(_rule_in_short(rules, r, f)))
        if more <= room:
            out["rules"].append(whole)
            room -= more
        else:
            out["more"].append(_rule_in_short(rules, r, f))
    return Outcome(_json(out), _("Read the rules that apply"))


FIRE_KEYWORDS = {
    "N12": "tensione circuito aperto oltre 1500 V campo di applicazione",
    "N13": "attivita soggetta controlli segnaletica cartello sezionamento manutenzione registro termografia",
    "N14": "non soggetta buona tecnica",
    "N15": "sottocampi sottocampo grandi dimensioni massime 20 m corridoi 2 m bordo 1 m evacuatori fumo aperture "
           "lucernari impianti in copertura shed compartimentazione propagazione classe reazione BAPV",
    "N16": "integrati integrazione BIPV involucro",
    "layout": "posa automatica sottocampi corridoi bordo evacuatori fascia di rispetto",
}

def fire_passages() -> list[dict]:
    from meridiana.core.rules import checks, rules, registry
    from meridiana.app.assistant.design_rules import _passage
    out = []
    facts = rules.Facts()
    for rule in registry.get("it").rules():
        if rule.id not in ("N12", "N13", "N14", "N15", "N16"):
            continue
        try:
            paragraphs = rule.paragraphs(facts)
        except Exception:  # noqa: BLE001  a rule that needs the project's facts: its title only
            paragraphs = []
        out.append(_passage(f"fire.{rule.id}", "fire", rules.title(rule, facts), " ".join(paragraphs),
                            f"{rule.source()} (core/rules/rules.py {rule.id})", keywords=FIRE_KEYWORDS[rule.id]))
    out.append(_passage(
        "fire.layout", "fire", "How Meridiana lays the modules under the fire brigade's rules",
        "With «fire rules» on (an activity subject to fire controls): 1 m free from the roof edge, groups of modules of "
        "at most 20 m in every direction separated by corridors of 2 m, 1 m around smoke vents, openings and the plant "
        "on the roof (each exclusion with its own clearance); a layout by hand is checked for groups beyond 20 m and "
        "corridors narrower than 2 m.", f"{checks.FIRE_SOURCE}; core/layout/layout.py; checks.manual_items",
        keywords=FIRE_KEYWORDS["layout"]))
    return out


def partial_passages():
    from meridiana.app.assistant.design_rules import _passage
    out = []
    out.append(_passage(
        "solaredge.partial.program", "partial", "SolarEdge: never on some modules only",
        "SolarEdge's inverters work at a fixed string voltage, «progettato specificamente per il funzionamento con "
        "ottimizzatori di potenza», and SolarEdge's tables count the string in optimizers: every module needs one. No "
        "SolarEdge document of the archive admits a module without (searched on 06/11/2026); a module named without on a "
        "SolarEdge inverter is a failure of the checks and the year counts one on it.",
        "SolarEdge SE25K-SE33.3K, Italian datasheet, p. 1; DS-000105-IT p. 3; DS-000205-EU p. 3; "
        "core/energy/plant._check_partial_fixed", ("SolarEdge",)))
    return out


NATIONAL_MANUAL_SECTIONS = frozenset((('1-modello.md', 'connessione-e-obblighi'), ('1-modello.md', 'dal-bordo-dellarea'), ('1-modello.md', 'distanze-e-margini'), ('1-modello.md', 'il-sito'), ('1-modello.md', 'le-esclusioni'), ('1-modello.md', 'le-file-a-mano'), ('1-modello.md', 'montaggio'), ('1-modello.md', 'passo-delle-file'), ('1-modello.md', 'passo-delle-file-dal-sole'), ('1-modello.md', 'prevenzione-incendi'), ('2-impianto.md', '2-impianto'), ('3-producibilita.md', 'potenza'), ('3-producibilita.md', 'producibilità-specifica'), ('4-consumi.md', 'da-dove-vengono'), ('4-consumi.md', 'le-fasce'), ('README.md', 'meridio-lassistente'), ('verifiche.md', 'da-sapere')))


def tour_text(key):
    return {"panels": _('Modules: subfields, rows and setbacks; the fire brigade rules keep the walkways free.')}[key]
