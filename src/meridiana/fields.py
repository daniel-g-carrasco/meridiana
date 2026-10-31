"""Names and values of project fields as the designer reads them, shared by the Properties panel and Meridio."""

from .i18n import _, number, pgettext


def mounting_names() -> dict:
    return {
        "coplanar": _("Coplanar on the pitch"),
        "integrated": _("Integrated in the roof (BIPV)"),
        "tilted_anchored": _("Tilted rows, anchored"),
        "tilted_ballasted": _("Tilted rows, ballasted"),
        "east_west": _("East-west pairs"),
        "ground": _("Ground-mounted rows"),
        "canopy": _("Canopy or carport"),
    }


def pitch_mode_names() -> dict:
    return {"sun": _("From the sun"), "value": _("Given pitch"), "gcr": _("Ground cover ratio")}


def field_label(path: str, kind: str = "") -> str:
    if kind == "exclusion" and path == "height":
        return _("height")
    if kind == "prop" and path in ("height", "width", "length", "rotation"):      # R269: a 3D object's measures
        return {"height": _("height"), "width": _("width"), "length": _("length"), "rotation": _("rotation")}[path]
    return {
        "name": _("name"), "height": _("eave height"), "roof.type": _("roof"), "roof.tilt": _("slope"), "roof.free_pitches": _("free pitches"),
        "roof.eave_side": _("eave side"), "fire.subject": _("fire control"),
        "fire.roof_fire_resistant": _("fire-resistant slab"), "module": _("module"),
        "params.mounting": _("mounting"), "params.portrait": _("orientation"), "params.stack": _("modules across"),
        "params.tilt": _("tilt"), "params.azimuth": _("azimuth"), "params.gap": _("gap between modules"),
        "params.edge": _("edge margin"), "params.shade_free": _("out of the shadows"),
        "params.flush_row_gap": _("gap between rows"), "params.table_modules": _("modules per table"),
        "params.table_gap": _("gap between tables"), "params.pitch_mode": _("row pitch"),
        "params.pitch": pgettext("rows", "Pitch"), "params.gcr": _("ground cover ratio"),
        "params.window": _("sun window"),
        "kind": _("kind"), "clearance": _("clearance"), "sun_window": _("sun window"), "parapet": _("parapet"),
        "use_near": _("shading of the obstacles"), "footprint": _("outline"), "ring": _("outline"),
        "roof.edges": _("eaves and gable ends"), "roof.ridge_height": _("ridge height"),
        "roof.covering": _("covering"), "rules": _("connection and obligations"), "reserved": _("reserved"),
    }.get(path, path)


def field_value(path: str, value) -> str:
    if path == "params.mounting":
        return mounting_names().get(value, str(value))
    if path == "params.pitch_mode":
        return pitch_mode_names().get(value, str(value))
    if path == "params.portrait":
        return _("Portrait") if value else _("Landscape")
    if isinstance(value, bool):
        return _("yes") if value else _("no")
    if value is None:
        return _("automatic")
    if isinstance(value, float):
        return number(value, 2)
    return str(value)
