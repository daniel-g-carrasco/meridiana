"""Stateless Italian inspector composition."""
from dataclasses import dataclass
from . import properties, charts

@dataclass(frozen=True)
class ItalianGuiProfile:
    id: str = "it"
    revision: int = 1

    def append_fields(self, section, schema, project, obj, session):
        getattr(properties, section)(schema, project, obj, session)

    def append_chart_fields(self, kind, editor):
        {"consumption": charts.consumption, "economics": charts.economics}[kind](editor.editor, editor.schema)

    def bill_columns(self, project):
        from meridiana.core.rules import registry
        return registry.get(self.id).calendar().codes

    def bill_row(self, row):
        return row

    def activity_note(self, fire):
        return properties.activity_note(fire)

    def fire_bands_notice(self, count):
        from meridiana.i18n import _
        return (_("{n} free bands of 1 m added as obstacles (DCPREV 14030 3.3.5.1): the modules on them are "
                  "set aside, red; take the band away to lay there.").format(n=count) if count else
                _("The bands are there already."))
