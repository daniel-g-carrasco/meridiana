"""Stable guided-tour content and explicit offline assistant commands."""
from dataclasses import dataclass
import re
import unicodedata

from .i18n import _


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    text: str
    target: tuple[str, ...]


def steps() -> tuple[Step, ...]:
    return (
        Step("file", _("Your projects"), _("Start from File: create a project, open a saved one, or return to recent work. Save revisions before comparing design alternatives."), ("file",)),
        Step("model", _("Model and place modules"), _("Draw buildings and roofs, then define subfields and place modules. Edit, Draw, Layout and Precision collect the tools for each task."), ("phase", "model")),
        Step("views", _("Plan and 3D"), _("Use the view controls to switch between plan and 3D. In a narrow window one view is shown at a time. The compass and Home restore your bearings."), ("views",)),
        Step("properties", _("Select, inspect, change"), _("Select an object to see its properties. Changes can be undone; help explains the focused field. The site properties hold supply and connection data."), ("property", "site.voltage")),
        Step("plant", _("Inverters, strings and storage"), _("Choose the working inverter, inspect its MPPTs and connect strings. Propose and Complete keep manual choices; sizing checks electrical limits. Configure storage beside the inverters."), ("phase", "plant")),
        Step("checks", _("Checks and explanations"), _("Review errors, warnings and information. Open a group, read the explanation and follow its destination. A suggested fix is applied only when you choose it."), ("checks",)),
        Step("production", _("Production and losses"), _("Calculate the year and inspect losses, shadows and each inverter. Only connected modules contribute energy. Calculation details show assumptions and sources."), ("phase", "production")),
        Step("consumption", _("Consumption"), _("Enter a load profile or import measured consumption. Compare production with demand before evaluating storage or self-consumption."), ("phase", "consumption")),
        Step("economics", _("Balance and economics"), _("Review self-consumption, storage operation, costs and returns. Compare variants while keeping each design and its assumptions separate."), ("phase", "economics")),
        Step("report", _("Reports and exchange"), _("Choose the report purpose and detail, inspect the preview, then export. IFC preserves model information; the hourly CSV supports independent checking."), ("phase", "report")),
        Step("assistant", _("Ask Meridio"), _("Ask about the current project, request an explanation or say Show me to reach a setting. Attach a datasheet for review; proposed changes still need your confirmation."), ("assistant",)),
        Step("settings", _("Make the workspace yours"), _("Settings collect appearance, navigation, keyboard, maps, privacy and Meridio. You can restart this tour from Help or by asking Meridio."), ("settings", "appearance")),
    )


def local_command(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^\w\s]", "", text).strip()
    if re.fullmatch(r"(?:(?:avvia|mostra|riprendi|inizia|rifai) (?:la )?)?(?:visita guidata|tour)|(?:start|show|resume) (?:the )?(?:guided tour|tour)", text):
        return "tour"
    if re.fullmatch(r"(?:segnala|segnalare) (?:un |il )?(?:bug|problema|errore)|(?:report|submit) (?:a )?(?:bug|issue)", text):
        return "bug"
    return ""
