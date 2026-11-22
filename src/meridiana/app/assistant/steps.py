"""What Meridio is doing while an answer comes (R667, Daniel 16/11/2026: «il caricamento della risposta di meridio
deve essere mostrato in modo carino direttamente in chat, nel punto in cui comparirà la risposta»): the short line of
his waiting sign, in the designer's words, never a tool's name. No Qt."""

from __future__ import annotations

from meridiana.i18n import _


def thinking() -> str:
    return _("Thinking…")


def words(tool: str) -> str:
    """The line for the tool he has just used (its answer is being read by the model): «Reading the checks…»."""
    said = {
        "read_checks": _("Reading the checks…"),
        "project_summary": _("Reading the project…"),
        "read_selection": _("Reading the selection…"),
        "read_results": _("Reading the results…"),
        "read_pedigree": _("Looking where the figures come from…"),
        "read_rules": _("Reading the rules…"),
        "vvf_activities": _("Reading the fire prevention activities…"),
        "design_rules": _("Reading the design rules…"),
        "search_manual": _("Searching the manual…"),
        "search_catalog": _("Searching the catalogue…"),
        "go_to": _("Finding the place…"),
        "list_navigation_targets": _("Looking through the settings…"),
        "read_navigation": _("Looking through the settings…"),
        "read_more": _("Reading on…"),
        "propose_fix": _("Preparing a proposal…"),
        "propose_edit": _("Preparing a proposal…"),
        "propose_undo": _("Preparing a proposal…"),
        "search_projects": _("Searching the projects…"),
        "project_revisions": _("Searching the projects…"),
        "similar_projects": _("Searching the projects…"),
        "prepare_open_project": _("Searching the projects…"),
        "list_tasks": _("Reading the tasks…"),
        "prepare_task": _("Reading the tasks…"),
    }
    return said.get(tool, thinking())
