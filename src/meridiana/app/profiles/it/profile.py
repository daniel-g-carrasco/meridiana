"""Stateless Italian app services."""
from dataclasses import dataclass

@dataclass(frozen=True)
class ItalianAppProfile:
    id: str = "it"
    revision: int = 1

    def report_chapters(self, project):
        from .report import chapters
        return chapters()

    def report_fragment(self, key, ctx):
        from .report import fragment
        return fragment(key, ctx)

    def report_text(self, key):
        from .report import text
        return text(key)

    def help_texts(self):
        from .help import texts
        return texts()

    def assistant_system(self, name, lang):
        from .assistant import system
        return system(name, lang)

    def assistant_template(self):
        from .assistant import SYSTEM
        return SYSTEM

    def assistant_passages(self):
        from .assistant import fire_passages
        return tuple(fire_passages())

    def assistant_tool_specs(self):
        from .assistant import tool_specs
        return [{"name": name, **spec} for name, spec in tool_specs().items()]

    def catalog_context(self, records):
        from .catalog import context
        return context(records)

    def activity_name(self, fire):
        from .assistant import _activity_name
        return _activity_name(fire)

    def vvf_activities(self, host, state, query):
        from .assistant import vvf_activities
        return vvf_activities(host, state, query)

    def read_rules(self, host, state, rule_id):
        from .assistant import read_rules
        return read_rules(host, state, rule_id)

    def manual_section_allowed(self, path, anchor):
        return True


    def editable(self, kind, table):
        return table

    def building_summary(self, building):
        return {"fire_brigade": building.fire.subject, "fire_activity": self.activity_name(building.fire),
                "fire_category": building.fire.category}

    def building_details(self, building):
        from dataclasses import asdict
        return {"fire": asdict(building.fire) | {"activity_name": self.activity_name(building.fire)}}


    def partial_passages(self):
        from .assistant import partial_passages
        return partial_passages()



    def tour_text(self, key):
        from .assistant import tour_text
        return tour_text(key)


    def design_keywords(self):
        return {"fire": "vigili fuoco vvf antincendio prevenzione incendi dcprev fire brigade"}

    def design_topics(self):
        return {"optimizers by maker and family", "SolarEdge tables", "fire brigade sub-fields"}


    def time_header(self, rows, timezone, year):
        from meridiana.i18n import _, number
        return _("The typical year hour by hour, {n} rows: each the hour that starts at its time, in Italian local time "
                 "({tz}, summer time included) of the reference year {year}; «UTC» is its offset.").format(
                     n=number(rows, 0, grouping=True), tz=timezone, year=year)

    def azimuth_convention(self):
        return "CEI 82-25: da sud, positivo verso ovest"
