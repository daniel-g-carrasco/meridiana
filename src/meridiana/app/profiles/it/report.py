"""Italian report fragments and their exact existing references."""
from meridiana.i18n import _
from meridiana.app.report.blocks import para

_TEXTS = {'layout_azimuth': 'Azimuth from the south, positive towards the west (CEI 82-25); area as drawn, in plan.', 'layout_pitch': '{name}: rows {pitch} m apart, {gap} m free behind each, the sun above {angle}° clears them (limit angle, CEI 82-25/3, Fig. 1).', 'fields_azimuth': 'Azimuth from the south, positive towards the west (CEI 82-25).', 'strings_title': 'Strings (CEI 64-8/7)'}

def text(key):
    return _(_TEXTS[key])

def fragment(key, ctx):
    if key == "layout_sources":
        return [para(text('layout_azimuth'), "caption")]
    if key == "string_sources":
        return [para(text('fields_azimuth'), "caption")]
    if key in {"electrical_intro", "consumption_notes", "economics_notes", "scope"}:
        return []
    raise KeyError(key)


def chapters():
    from meridiana.app.report.reports import Chapter
    items = [
        Chapter("plant", _("Electrical system"), ("plant",),
                _("Inverters, strings by input, the voltages checked (CEI 64-8/7), DC/AC ratio")),
        Chapter("checks", _("Checks and standards"), ("checks",),
                _("Every check with its result and its source, the notes of the rules that apply")),
    ]
    return {c.id: c for c in items}
