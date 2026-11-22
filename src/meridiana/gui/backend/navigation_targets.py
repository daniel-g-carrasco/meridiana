"""The controls Meridio can show, by stable public IDs (assistant/tools.py: list_navigation_targets): the settings,
the site's properties and the phases. Who shows them is the window (the Widgets one found the widget of each with
ui/navigation_targets.py, until it goes)."""

from __future__ import annotations

from dataclasses import dataclass

from meridiana.app.interface import phases
from meridiana.i18n import _


@dataclass(frozen=True)
class Target:
    kind: str
    id: str
    section: str
    label: str
    field: str = ""         # a setting's field in its section's page (Settings/SettingField.qml, settingsRow_<field>)


def controls() -> tuple[Target, ...]:
    """Only controls that exist in this version."""
    T = Target
    return (
        T("setting", "navigation.mouse_style", "navigation", _("Mouse style"), "navigation"),
        T("setting", "navigation.orbit", "navigation", _("Orbit"), "orbit"),
        T("setting", "navigation.pivot", "navigation", _("Centre of the orbit"), "pivot"),
        T("setting", "appearance.theme", "appearance", _("Theme"), "theme"),
        T("setting", "appearance.text_size", "appearance", _("Size of the text"), "text_size"),
        T("setting", "appearance.font", "appearance", _("Font"), "font"),
        T("setting", "appearance.colour", "appearance", _("Colour"), "accent"),
        T("setting", "privacy.geocoding", "privacy", _("Find the site"), "network_geocoding"),
        T("setting", "privacy.pvgis", "privacy", _("Weather and PVGIS estimate"), "network_pvgis"),
        T("setting", "privacy.tiles", "privacy", _("Online map tiles"), "network_tiles"),
        T("setting", "assistant.visible", "assistant", _("Assistant"), "assistant"),
        T("setting", "assistant.docked", "assistant", _("Dock the conversation in the panels, as Project and Properties"), "assistant_docked"),
        T("setting", "assistant.voice", "assistant", _("Voice"), "assistant_voice"),
        T("setting", "assistant.local_model", "assistant", _("Local model"), "assistant_local_model"),
        T("setting", "report.profile", "report", _("Report profile"), "report_profile"),
        T("setting", "maps.background", "maps", _("Background"), "background"),
        T("property", "site.distributor", "site", _("Distributor")),
        T("property", "site.pod", "site", "POD"),
        T("property", "site.voltage", "site", _("Supply voltage")),
        T("property", "site.phases", "site", _("Phases")),
        T("property", "site.connection_level", "site", _("Connection level")),
        T("property", "site.available_power", "site", _("Available or contracted power")),
        T("property", "site.requested_power", "site", _("Power requested for the new plant")),
        T("property", "site.practice_code", "site", _("Connection practice code")),
    )


def field_of(target_id: str) -> str:
    """The field of the page of the Settings that shows the setting `target_id`, "" for none."""
    return next((t.field for t in controls() if t.kind == "setting" and t.id == target_id), "")


def sections() -> dict[str, str]:
    return {"appearance": _("Appearance"), "navigation": _("Navigation"), "keyboard": _("Keyboard"),
            "assistant": _("Assistant"), "report": _("Report"), "maps": _("Maps"), "privacy": _("Privacy")}


def catalogue() -> list[dict]:
    rows = [{"kind": "settings", "id": key, "label": label} for key, label in sections().items()]
    rows.extend({"kind": item.kind, "id": item.id, "label": item.label} for item in controls())
    rows.extend({"kind": "phase", "id": phase.id, "label": phase.title} for phase in phases.phases())
    return rows
