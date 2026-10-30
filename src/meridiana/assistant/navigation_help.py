"""Navigation help derived from the active profile and current command bindings."""
from .. import navigation, shortcuts
from ..i18n import _


def snapshot(host):
    current = getattr(host, "navigation_settings", lambda: {})()
    if not current:
        return {"available": False}
    style = current["style"]
    bindings = current.get("bindings", {})
    rows = list(navigation.table(style))
    fit = bindings.get("fit", ())
    fit_text = _("Fit in the view toolbar")
    if fit:
        fit_text += ": " + ", ".join(fit)
    if navigation.STYLES[style].middle_double == "fit":
        fit_text += "; " + _("a double click of the middle button")
    rows[4] = (rows[4][0], fit_text)
    commands = [{"id": item.id, "label": item.text.replace("&", ""),
                 "keys": list(bindings.get(item.id, ()))} for item in shortcuts.commands()]
    return {**current, "available": True, "gestures": rows, "commands": commands,
            "touchpad": _("Two-finger scrolling pans; pinching zooms towards the pointer. Orbit is available in 3D only.")}


def explain(host):
    data = snapshot(host)
    if not data["available"]:
        return _("Open the project workspace to read its navigation settings.")
    lines = [_("Your navigation profile: {profile}").format(profile=data["style_name"])]
    lines.extend(f"{action}: {gesture}" for action, gesture in data["gestures"])
    orbit = {"turntable": _("Turntable: the vertical stays vertical"), "arcball": _("Arcball: free")}
    pivot = {"cursor": _("The point under the cursor"), "selection": _("The middle of the selection"),
             "centre": _("The middle of the view")}
    lines += [data["touchpad"], _("3D orbit: {orbit}; pivot: {pivot}").format(
        orbit=orbit.get(data.get("orbit"), data.get("orbit", "")),
        pivot=pivot.get(data.get("pivot"), data.get("pivot", "")))]
    return "\n\n".join(lines)
