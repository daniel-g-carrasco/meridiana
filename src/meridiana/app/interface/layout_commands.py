"""The commands that lay the modules, said once for the bar, the menus and the panel (R564, Daniel 14/11/2026).

The bar of the Plant has one button for them, «Layout» (S), whose menu holds «Row of modules» (L), «Area with
automatic layout», «Fill» and «Empty». The same commands are in the menus of a sub-field (plan, 3D view, project
tree) and in its panel: their words, whether they can act and why not come from here, so that a menu never says a
command that the bar calls otherwise, and never offers one that does nothing.

- `entries(sf)`: what a sub-field offers, in order (fill or lay again automatically, explode, empty);
- `fill_state(sf)`: whether «Fill» can act on it, and why not (short, for the menus; whole, for the status bar);
- `fill_all(project, ids)`: «Fill» on several sub-fields in one change (the checks' row for the empty ones, R605);
- `canopy_entries(building)`:the canopy's own entries in the Plant (its title, «Modules on a canopy…»);
- `AREA`: the tool and its options of «Area with automatic layout», the sub-field of before R445.

No Qt here; the texts are those of shortcuts.py, the commands' catalogue."""

from __future__ import annotations

from collections.abc import Callable

from meridiana.app.interface import shortcuts
from meridiana.core.layout import manual
from meridiana.i18n import _

# «Area with automatic layout»: the sub-field tool drawing an area the automatic layout fills (margins, fire brigade
# rules, target power, shadows), as before R445; the plan's own «Layout» draws a sub-field that is its modules
AREA = ("subfield", {"fill": "area"})

# the action of each entry and the command of the catalogue whose words it uses
WORDS = {"fill": "fill", "relayout": "refill", "empty": "empty", "fill_area": "fill_area",
         "canopy_layout": "canopy_layout", "tool_subfield": "tool_subfield"}


def text(action: str) -> str:
    """The words of an action as the menus write them (the catalogue's, without the access key)."""
    if action == "explode":
        return _("Explode the rows")
    wanted = WORDS.get(action, action)
    found = next((c for c in shortcuts.commands() if c.id == wanted), None)
    return shortcuts.plain(found.text) if found else action


def fill_state(sf) -> tuple[bool, str, str]:
    """Whether «Fill» acts on the sub-field `sf`, with the short reason for a menu and the whole one for the status
    bar when it does not. It fills an empty sub-field, and gives back to one laid automatically the modules taken out
    by hand; a sub-field drawn with «Layout» is its modules from the start, so it is full (R445)."""
    if sf is None:
        return False, "", _("Select a sub-field first: the modules are laid in it.")
    if not sf.filled or (not sf.manual and sf.removed):
        return True, "", ""
    name = sf.name or sf.id
    if sf.manual:
        return False, _("already full"), _(
            "«{name}» is already full: its modules were laid as it was drawn.").format(name=name)
    return False, _("already full"), _("«{name}» is already full.").format(name=name)


def fill_all(project, sfids) -> Callable:
    """«Fill all» (R605, the row of the checks that stands for several sub-fields without modules): the bar's «Fill»
    (`manual.fill`) on each of `sfids` that `fill_state` says it fills, in one change for one step of the undo. A
    sub-field already full, or gone, is left as it is."""
    by_id = {sf.id: sf for sf in project.subfields}
    changes = [manual.fill(project, sfid) for sfid in dict.fromkeys(sfids)
               if sfid in by_id and fill_state(by_id[sfid])[0]]

    def change(p):
        for one in changes:
            one(p)
    return change


def entries(sf) -> list[dict]:
    """The layout's entries of a sub-field's menus, in order: `action` (fill, relayout, explode, empty), `text`,
    `enabled` and `note` (why not, beside the entry). A sub-field by hand and laid lays again automatically in place
    of «Fill»; explode and empty only once it is laid."""
    if sf is None:
        return []
    if sf.manual and sf.filled:
        out = [dict(action="relayout", text=text("relayout"), enabled=True, note="")]
    else:
        can, note, _whole = fill_state(sf)
        out = [dict(action="fill", text=text("fill"), enabled=can, note=note)]
    if sf.filled:
        out += [dict(action="explode", text=text("explode"), enabled=True, note=""),
                dict(action="empty", text=text("empty"), enabled=True, note="")]
    return out


def canopy_entries(building) -> list[dict]:
    """The entries a canopy gives its menus in the Plant (R564): its title, then the modules laid on it with the
    window of «Modules on a canopy», this canopy already chosen. Nothing for a building that is not a canopy."""
    if building is None or getattr(building, "canopy", None) is None:
        return []
    return [dict(action="", text=_("Canopy «{name}»").format(name=building.name or building.id), enabled=False,
                 note="", header=True),
            dict(action="canopy_layout", text=text("canopy_layout"), enabled=True, note="", header=False)]
