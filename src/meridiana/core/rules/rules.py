"""Compatibility facade for the project-scoped rule registry."""

from meridiana.core.rules import registry
from meridiana.i18n import _

from meridiana.core.rules.types import Facts, Rule  # noqa: F401


LEVELS = registry.get("it").rule_data("LEVELS")

OBLIGATIONS = registry.get("it").rule_data("OBLIGATIONS")

USES = registry.get("it").rule_data("USES")

PREMISES = registry.get("it").rule_data("PREMISES")

MV_KW = registry.get("it").rule_data("MV_KW")

HV_KW = registry.get("it").rule_data("HV_KW")

C016_TAB4 = registry.get("it").rule_data("C016_TAB4")

DESIGN_KW = registry.get("it").rule_data("DESIGN_KW")

DESIGN_M2 = registry.get("it").rule_data("DESIGN_M2")

RULES = registry.get("it").rule_data("RULES")


def level_names(*, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("level_names")


def obligation_names(*, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("obligation_names")


def use_names(*, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("use_names")


def premises_names(*, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("premises_names")


def chapter_names(*, profile_id: str = "it"):
    return registry.get(profile_id).chapter_names()


def auto_level(p_kw: float, *, profile_id: str = "it"):
    return registry.get(profile_id).auto_level(p_kw)


def region_of(address: str, *, profile_id: str = "it"):
    return registry.get(profile_id).region_of(address)


def facts(
    project, results: dict | None = None, energy: dict | None = None, inverter=None
):
    return registry.for_project(project).facts(project, results, energy, inverter)


def design(f: Facts):
    return registry.get(f.profile_id).design(f)


def minimum(f: Facts):
    return registry.get(f.profile_id).minimum(f)


def _n24(f: Facts, *, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("_n24", f)


def _n02(f: Facts, *, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("_n02", f)


def _n13_activities(f: Facts, *, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("_n13_activities", f)


def _n02_tail(*, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("_n02_tail")


def _n03(f: Facts, *, profile_id: str = "it"):
    return registry.get(profile_id).rule_call("_n03", f)


def title(r: Rule, f: Facts):
    return registry.get(f.profile_id).title(r, f)


def applying(f: Facts) -> list[Rule]:
    """The rules that apply, in the order of the chapters."""
    return sorted(
        (r for r in registry.get(f.profile_id).rules() if r.applies(f)),
        key=lambda r: r.chapter,
    )


def in_document(r: Rule, f: Facts):
    return registry.get(f.profile_id).in_document(r, f)


def notes(f: Facts) -> list[tuple[str, list[tuple[Rule, list[str]]]]]:
    """The notes for the report: [(chapter title, [(rule, paragraphs)])] for the chapters with a rule that goes in a
    document, numbered as they come."""
    names = chapter_names(profile_id=f.profile_id)
    out: list = []
    last = None
    for r in applying(f):
        if not in_document(r, f):
            continue
        if r.chapter != last:
            last = r.chapter
            out.append((f"{len(out) + 1}. {names[r.chapter].split('. ', 1)[1]}", []))
        out[-1][1].append((r, r.paragraphs(f)))
    return out


def notes_text(f: Facts) -> str:
    """The notes as plain text, to paste into the technical report: the title of each chapter, a paragraph
    per block, the source of each rule after its paragraphs."""
    blocks = []
    for title, rules in notes(f):
        blocks.append(title.upper())
        for r, paragraphs in rules:
            blocks += paragraphs
            blocks.append(_("Source: {source}").format(source=r.source()))
    return "\n\n".join(blocks) + "\n"
