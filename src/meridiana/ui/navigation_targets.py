"""The controls Meridio can show. Stable public IDs map to explicit getters, never model-supplied attributes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .. import phases
from ..i18n import _


@dataclass(frozen=True)
class Target:
    kind: str
    id: str
    section: str
    label: str
    widget: Callable


def controls() -> tuple[Target, ...]:
    """Only controls that exist in this version; getters run after their page has been opened."""
    T = Target
    return (
        T("setting", "navigation.mouse_style", "navigation", _("Mouse style"),
          lambda w: w.file_page.settings.navigation.style),
        T("setting", "navigation.orbit", "navigation", _("Orbit"),
          lambda w: w.file_page.settings.navigation.orbit),
        T("setting", "navigation.pivot", "navigation", _("Centre of the orbit"),
          lambda w: w.file_page.settings.navigation.pivot),
        T("setting", "appearance.theme", "appearance", _("Theme"),
          lambda w: w.file_page.settings.appearance.mode),
        T("setting", "appearance.text_size", "appearance", _("Size of the text"),
          lambda w: w.file_page.settings.appearance.text_size),
        T("setting", "appearance.colour", "appearance", _("Colour"),
          lambda w: w.file_page.settings.appearance.colour),
        T("setting", "privacy.geocoding", "privacy", _("Find the site"),
          lambda w: w.file_page.settings.privacy.geocoding),
        T("setting", "privacy.pvgis", "privacy", _("Weather and PVGIS estimate"),
          lambda w: w.file_page.settings.privacy.pvgis),
        T("setting", "privacy.tiles", "privacy", _("Online map tiles"),
          lambda w: w.file_page.settings.privacy.tiles),
        T("setting", "assistant.visible", "assistant", _("Assistant"),
          lambda w: w.file_page.settings.assistant),
        T("setting", "assistant.docked", "assistant", _("Dock the conversation in the panels, as Project and Properties"),
          lambda w: w.file_page.settings.assistant_docked),
        T("setting", "assistant.voice", "assistant", _("Voice"),
          lambda w: w.file_page.settings.meridio.voice),
        T("setting", "assistant.local_model", "assistant", _("Local model"),
          lambda w: w.file_page.settings.meridio.model),
        T("setting", "report.profile", "report", _("Report profile"),
          lambda w: w.file_page.settings.report.default),
        T("setting", "maps.background", "maps", _("Background"),
          lambda w: w.file_page.settings.maps.default),
        T("property", "site.distributor", "site", _("Distributor"), lambda w: w.props.distributor),
        T("property", "site.pod", "site", "POD", lambda w: w.props.pod),
        T("property", "site.voltage", "site", _("Supply voltage"), lambda w: w.props.voltage),
        T("property", "site.phases", "site", _("Phases"), lambda w: w.props.phases),
        T("property", "site.connection_level", "site", _("Connection level"), lambda w: w.props.level),
        T("property", "site.available_power", "site", _("Available or contracted power"), lambda w: w.props.available),
        T("property", "site.requested_power", "site", _("Power requested for the new plant"), lambda w: w.props.requested),
        T("property", "site.practice_code", "site", _("Connection practice code"), lambda w: w.props.practice),
    )


def sections() -> dict[str, str]:
    return {"appearance": _("Appearance"), "navigation": _("Navigation"), "keyboard": _("Keyboard"),
            "assistant": _("Assistant"), "report": _("Report"), "maps": _("Maps"), "privacy": _("Privacy")}


def catalogue(win=None) -> list[dict]:
    rows = [{"kind": "settings", "id": key, "label": label} for key, label in sections().items()]
    rows.extend({"kind": item.kind, "id": item.id, "label": item.label} for item in controls())
    for phase in phases.phases():
        index = win.tabs.index_of_phase(phase.id) if win is not None else -1
        if win is None or (index >= 0 and win.tabs.tabBar().isTabVisible(index)):
            rows.append({"kind": "phase", "id": phase.id, "label": phase.title})
    return rows


def show(win, target: tuple) -> None:
    """Navigate first, then reveal the surviving control after the page's own transition has settled."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from . import motion, spotlight
    from .design import Motion

    kind = target[0]
    ident = target[1] if len(target) > 1 else ""
    if kind not in ("setting", "settings", "property", "phase", "site", "building", "subfield", "exclusion"):
        raise ValueError("the requested destination is not registered")
    generation = int(win.property("navigationHintGeneration") or 0) + 1
    win.setProperty("navigationHintGeneration", generation)
    region = None
    focus = QApplication.focusWidget()
    if kind in ("setting", "settings"):
        item = next((row for row in controls() if row.kind == kind and row.id == ident), None)
        section = item.section if item is not None else ident
        if section not in sections() or (kind == "setting" and item is None):
            raise ValueError("the requested setting is not registered")
        win._preferences(section)
        widget = (lambda: item.widget(win)) if item is not None else lambda: win.file_page.settings.pages.currentWidget()
    else:
        item = next((row for row in controls() if row.kind == kind and row.id == ident), None)
        if kind == "property" and item is None:
            raise ValueError("the requested property is not registered")
        phase = "model" if kind != "phase" else ident
        index = win.tabs.index_of_phase(phase)
        if index < 0 or not win.tabs.tabBar().isTabVisible(index):
            raise ValueError("the requested phase is hidden or unavailable")
        win.file_page.close_page()
        win._navigate(("site",) if kind == "property" else target)
        if kind == "phase":
            widget = win.tabs.tabBar
            region = lambda: win.tabs.tabBar().tabRect(index)
        else:
            win.docks[1].show()
            win.docks[1].raise_()
            widget = (lambda: item.widget(win)) if item is not None else win.props.viewport
    try:
        candidate = widget()
    except (AttributeError, RuntimeError):
        raise ValueError("the requested control is unavailable in this window") from None
    if candidate is None:
        raise ValueError("the requested control is unavailable in this window")
    # Opening a page must not move the keyboard out of the conversation or an unrelated visible field.
    try:
        if focus is not None and focus.isVisible():
            focus.setFocus()
    except RuntimeError:
        pass  # A settings page can be replaced while it is opened.

    def reveal():
        if win.property("navigationHintGeneration") != generation:
            return
        try:
            if candidate.isVisible():
                spotlight.reveal(candidate, region=region)
        except (AttributeError, RuntimeError):
            return  # Rebuilding or closing the window cancels a pending visual hint.

    delay = 0 if motion.reduced() else Motion.SLOW + 30
    motion.after_work(win, lambda: QTimer.singleShot(delay, win, reveal))
