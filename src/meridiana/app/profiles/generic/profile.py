"""App presentation of the minimal generic calculation scope."""
from dataclasses import dataclass
from copy import deepcopy
from meridiana.i18n import _
from meridiana.core.rules import registry


@dataclass(frozen=True)
class GenericAppProfile:
    national_manual_sections: frozenset
    help_ids: tuple[str, ...] = ()
    id: str = "generic"
    revision: int = 1

    def report_chapters(self, project):
        from meridiana.app.report.reports import Chapter
        return {"plant": Chapter("plant", _("Electrical system"), ("plant",), _("Inverters and their strings, the modules of each string")),
                "checks": Chapter("checks", _("Physical checks and scope"), ("checks",), _("Physical checks using declared data"))}

    def report_fragment(self, key, ctx):
        from meridiana.app.report.blocks import para
        if key == "scope": return [para(registry.get(self.id).text("scope"), "muted")]
        if key in {"layout_sources", "string_sources"}:
            return [para(self.report_text("layout_azimuth" if key == "layout_sources" else "fields_azimuth"), "caption")]
        if key in {"electrical_intro", "consumption_notes", "economics_notes"}: return []
        raise KeyError(key)

    def report_text(self, key):
        return {"layout_azimuth": _("Azimuth from the south, positive towards the west; area as drawn, in plan."),
                "layout_pitch": _("{name}: rows {pitch} m apart, {gap} m free behind each, the sun above {angle} degrees clears them (geometric limit angle)."),
                "fields_azimuth": _("Azimuth from the south, positive towards the west."),
                "strings_title": _("Physical string checks")}[key]

    def help_texts(self):
        from meridiana.app.interface.help import Help
        scope = registry.get(self.id).text("scope")
        general = {key: Help(_("Calculation scope"), _("Physical calculations and declared data."), scope) for key in self.help_ids}
        return {**general, "site.network": Help(_("Grid connection"), _("Use declared voltage and power."), scope),
                "consumption.bands": Help(_("Consumption"), _("One total, without national energy bands."), scope),
                "consumption.pod": Help(_("Supply identifier"), _("A free identifier, without a national format check."), scope),
                "phase.consumption": Help(_("Consumption"), _("Declared totals or an hourly curve."), scope),
                "phase.economics": Help(_("Economics"), _("Declared prices and costs, without national incentives."), scope)}

    def assistant_system(self, name, lang):
        from meridiana.app.assistant.persona import LANGUAGES
        language = LANGUAGES.get(lang, "English")
        return (f"You are {name}, Meridiana's assistant. Answer in {language}, clearly and concisely. "
                "Read figures with the tools and quote their actual sources. Propose changes for human review. "
                + registry.get(self.id).text("scope") + ". "
                "Only physical calculations and declared data are available. Never infer local obligations, "
                "regulatory conformity, national incentives or permission to build from them. "
                "Search the scoped manual for how to use the program. When data are missing, say so.")

    def assistant_passages(self): return ()
    def partial_passages(self): return []
    def design_keywords(self): return {}
    def design_topics(self): return {"optimizers by maker and family", "SolarEdge tables"}

    def assistant_tool_specs(self):
        from meridiana.app.assistant.tools import _schema
        return [{"name": "read_rules", "description": "Read the physical calculation scope. No national rules or authorisation checks are available.",
                 "parameters": _schema({"rule_id": {"type": "string", "description": "optional rule identifier"}})}]

    def catalog_context(self, records):
        return {"records": deepcopy(records), "market_scope": {key: "it" if isinstance(value, dict) and value.get("market_scope") == "it" else None for key, value in records.items()}}

    def manual_section_allowed(self, path, anchor):
        return (path, anchor) not in self.national_manual_sections

    def activity_name(self, fire): return ""

    def vvf_activities(self, host, state, query):
        raise ValueError(registry.get(self.id).text("scope"))

    def read_rules(self, host, state, rule_id):
        from meridiana.app.assistant.tools import Outcome, _json
        scope = registry.get(self.id).text("scope")
        data = {"scope": scope, "rules": []}
        if rule_id: data["error"] = _("No national rule is available in this profile")
        return Outcome(_json(data), scope, error=bool(rule_id))

    def building_summary(self, building): return {}
    def building_details(self, building): return {}

    def editable(self, kind, table):
        if kind == "building": return {key: value for key, value in table.items() if not key.startswith("fire.")}
        if kind in {"consumption", "economics"}:
            allowed = {field.path for field in registry.get(self.id).fields(kind)}
            return {key: value for key, value in table.items() if key in allowed}
        return table

    def tour_text(self, key):
        return {"panels": _("Modules: subfields, rows, geometric setbacks and explicitly drawn exclusions.")}[key]


    def time_header(self, rows, timezone, year):
        from meridiana.i18n import number
        return _("The typical year hour by hour, {n} rows, in the selected timezone {tz} of reference year {year}; UTC is its offset.").format(
            n=number(rows, 0, grouping=True), tz=timezone, year=year) + " " + registry.get(self.id).text("scope")

    def azimuth_convention(self):
        return "from south, positive towards west"
