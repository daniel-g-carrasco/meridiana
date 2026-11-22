"""Immutable identity and initial adapter for the existing Italian services."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItalianProfile:
    id: str = "it"
    revision: int = 1

    def calendar(self):
        from .calendar import ItalianCalendar
        return ItalianCalendar()

    def facts(self, project, results=None, energy=None, inverter=None):
        from . import rules

        return rules.facts(project, results, energy, inverter)

    def rules(self):
        from . import rules

        return tuple(rules.RULES)

    def minimum(self, facts):
        from . import rules

        return rules.minimum(facts)

    def design(self, facts):
        from . import rules

        return rules.design(facts)

    def title(self, rule, facts):
        from . import rules

        return rules.title(rule, facts)

    def in_document(self, rule, facts):
        from . import rules

        return rules.in_document(rule, facts)

    def chapter_names(self):
        from . import rules

        return rules.chapter_names()

    def auto_level(self, power_kw):
        from . import rules

        return rules.auto_level(power_kw)

    def region_of(self, address):
        from . import rules

        return rules.region_of(address)

    def technical_rule(self, network):
        return (
            ""
            if network.voltage_v <= 0
            else ("CEI 0-21" if network.voltage_v <= 1000 else "CEI 0-16")
        )

    def connection(self, p_kw, phases, chosen, level="BT", auto=True):
        from . import checks

        return checks.connection(p_kw, phases, chosen, level, auto)

    def rule_items(self, facts):
        from . import checks

        return checks.rule_items(facts)

    def activity(self, number):
        from . import vvf_activities

        return vvf_activities.activity(number)

    def activities(self, query=""):
        from . import vvf_activities

        return vvf_activities.search(query)

    def rule_call(self, name, *args):
        from . import rules

        return {
            "level_names": rules.level_names,
            "obligation_names": rules.obligation_names,
            "use_names": rules.use_names,
            "premises_names": rules.premises_names,
            "chapter_names": rules.chapter_names,
            "auto_level": rules.auto_level,
            "region_of": rules.region_of,
            "facts": rules.facts,
            "design": rules.design,
            "minimum": rules.minimum,
            "_n24": rules._n24,
            "_n02": rules._n02,
            "_n13_activities": rules._n13_activities,
            "_n02_tail": rules._n02_tail,
            "_n03": rules._n03,
            "title": rules.title,
            "applying": rules.applying,
            "in_document": rules.in_document,
            "notes": rules.notes,
            "notes_text": rules.notes_text,
        }[name](*args)

    def rule_data(self, name):
        from . import rules

        return {
            "LEVELS": rules.LEVELS,
            "OBLIGATIONS": rules.OBLIGATIONS,
            "USES": rules.USES,
            "PREMISES": rules.PREMISES,
            "MV_KW": rules.MV_KW,
            "HV_KW": rules.HV_KW,
            "C016_TAB4": rules.C016_TAB4,
            "DESIGN_KW": rules.DESIGN_KW,
            "DESIGN_M2": rules.DESIGN_M2,
            "RULES": rules.RULES,
        }[name]

    def check_call(self, name, *args):
        from . import checks

        return {
            "area_names": checks.area_names,
            "connection": checks.connection,
            "rule_items": checks.rule_items,
            "string_detail": checks.string_detail,
            "string_why": checks.string_why,
        }[name](*args)

    def activity_call(self, name, *args):
        from . import vvf_activities

        return {
            "_a": vvf_activities._a,
            "activity": vvf_activities.activity,
            "_fold": vvf_activities._fold,
            "_haystack": vvf_activities._haystack,
            "_stem": vvf_activities._stem,
            "search": vvf_activities.search,
            "index": vvf_activities.index,
            "shown": vvf_activities.shown,
            "chosen": vvf_activities.chosen,
            "as_dict": vvf_activities.as_dict,
        }[name](*args)

    def activity_data(self, name):
        from . import vvf_activities

        return {
            "SOURCE": vvf_activities.SOURCE,
            "PROCEDURE": vvf_activities.PROCEDURE,
            "PV_NOT_AN_ACTIVITY": vvf_activities.PV_NOT_AN_ACTIVITY,
            "CATEGORIES": vvf_activities.CATEGORIES,
            "ALL": vvf_activities.ALL,
            "ACTIVITIES": vvf_activities.ACTIVITIES,
            "_BY_NUMBER": vvf_activities._BY_NUMBER,
            "_STOP": vvf_activities._STOP,
            "NOT_SPECIFIED": vvf_activities.NOT_SPECIFIED,
        }[name]

    def validate_inputs(self, raw):
        for i, building in enumerate(raw.get("buildings") or []):
            if not isinstance(building, dict) or not isinstance(
                building.get("fire", {}), dict
            ):
                continue  # Structural errors are reported by the common model checker.
            fire = building.get("fire") or {}
            self.validate_fire(fire, f"buildings[{i}].fire")

    def validate_fire(self, fire, path):
        """Called after structural checks, in their original position in the model."""
        if type(fire.get("activity", 0)) is int and not 0 <= fire.get("activity", 0) <= 80:
            raise ValueError(f"{path}.activity: {fire['activity']!r} is not between 0 and 80")

    def layout_note(self, name, sfid, note):
        from . import checks

        return checks.layout_note(name, sfid, note)

    def standards(self):
        from . import sources

        return sources.references()


    def defaults(self, section):
        from .defaults import defaults
        return defaults(section)

    def fire(self, project, sf=None):
        from .fire import policy
        return policy(project, sf)

    def text(self, key):
        from .texts import BALLAST_WARNING
        from . import texts
        from .fire import FIRE_SOURCE
        if key == "fire_source":
            return FIRE_SOURCE
        return BALLAST_WARNING if key == "ballast_warning" else texts.text(key)


    def fire_group_items(self, placed, p, frame, size, result, sf, here, fix, label, name=""):
        from .fire import group_items
        return group_items(placed, p, frame, size, result, sf, here, fix, label, name)


    def electrical(self):
        from .electrical import ItalianElectricalPolicy
        return ItalianElectricalPolicy()

    def market_rules(self, opt, inv, base, reason):
        from .market import rules
        return rules(opt, inv, base, reason)

    def partial_fixed_check(self, string):
        from .market import partial_fixed_check
        return partial_fixed_check(string)

    def optimizer_parallel(self, family_id, declared):
        return dict(declared)


    def consumption(self):
        from .consumption import ItalianConsumptionPolicy
        return ItalianConsumptionPolicy()


    def economics(self):
        from .economics import ItalianEconomyPolicy
        return ItalianEconomyPolicy()


    def fields(self, section):
        from .fields import fields
        return fields(section)
