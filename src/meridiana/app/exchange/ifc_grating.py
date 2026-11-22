"""Gratings recognised (R608, model m04; Daniel 14/11/2026: «la trattiamo come grigliati»): a walkway or a platform of
metal bars lets the sun and the eye through. Model m04's platforms are IfcSlab FLOOR «Floor:S_FL_SF_Gratings-40mm»
(1 398 m2 at 136 m, 1 186 m2 at 132 m): read as roofs, they cast the shadow of a solid slab and the 48 columns standing
on them came in as obstacles. A grating, wherever the reader meets it:
- is drawn in the 3D opaque, in its file's colour or else in COLOUR, a metal grey a little apart from the slabs'
  (`shown`, used by ifc_mesh), so that it casts its shadow there too: Qt Quick 3D takes none from a blended model (a
  twin drawn nowhere did not cast one either). Daniel 14/11/2026 (choice A): opaque with its shadow, as the
  calculation counts it; the see-through look comes back with the partial shadow;
- casts its shadow on the modules, the full one of a slab (ifc_shade, also with the import's option off: Daniel wants
  the shadow, and the engine has no partial one yet, so the energy is never overstated), and is no body of the solids
  (ifc_import.solid_raws);
- is never a roof, a terrace, nor a cover that makes the slab under it a floor, and what stands on it is not on a
  roof (ifc_read).

The rule, the only one: an element of CLASSES (a floor of bars is modelled as a slab, a plate, a covering, a part or a
proxy; never a beam or a column named after the grating it carries) whose name, description, object type, type name
or predefined type holds one of WORDS at the start of a word, or one of JOINED anywhere (German joins its words:
«Stahlgitterrost»), in any case. No geometric rule tells a grating from a thin roof slab without its name (studio
r35-ifc, m04). IFC's enumerations of the slabs, plates and coverings have no value for a grating [I]: a modeller
writes USERDEFINED and says it in the object type, which is read; a predefined type that says it is read too.
Without Qt."""

from __future__ import annotations

import re

COLOUR = (0.62, 0.65, 0.69)     # sRGB 0..1: a grating without a colour of its own, metal grey (a slab's is 0.72 grey)
CLASSES = ("IFCSLAB", "IFCSLABSTANDARDCASE", "IFCSLABELEMENTEDCASE", "IFCPLATE", "IFCPLATESTANDARDCASE",
           "IFCCOVERING", "IFCBUILDINGELEMENTPART", "IFCBUILDINGELEMENTPROXY")
# the words of the models met and of the languages of the program's users: English, Italian (with the trade name
# «tramex»), French, Spanish, Portuguese
WORDS = ("grating", "grigliat", "tramex", "trámex", "caillebotis", "rejilla", "grelha")
JOINED = ("gitterrost",)
_PATTERN = re.compile("(?<![a-zà-ÿ])(" + "|".join(map(re.escape, WORDS)) + ")|" + "|".join(map(re.escape, JOINED)))


def shown(colour) -> tuple:
    """The colour a grating is drawn in, (r, g, b, opacity): its file's colour (`colour`, (r, g, b[, opacity]) or None)
    or COLOUR, always opaque, so that the 3D draws its shadow."""
    rgb = tuple(colour[:3]) if colour is not None else COLOUR
    return rgb + (1.0,)


def is_grating(cls: str, predefined: str | None = None, names=()) -> bool:
    """Whether an element is a grating: `cls` its class (any case), `predefined` its PredefinedType (as «FLOOR» or
    «.FLOOR.»), `names` its name, description, object type and type name (None and "" ignored)."""
    if str(cls or "").upper() not in CLASSES:
        return False
    text = " ".join(str(v) for v in (*names, str(predefined or "").strip(".")) if v).lower()
    return bool(_PATTERN.search(text))


def of_entity(e, types: dict | None = None) -> bool:
    """`is_grating` of an IfcOpenShell entity; `types` (from `typed`) gives the name of its type without asking the
    file for it."""
    if e.is_a().upper() not in CLASSES:
        return False
    names = [getattr(e, "Name", None), getattr(e, "Description", None), getattr(e, "ObjectType", None)]
    names.append((types or {}).get(e.id()))
    return is_grating(e.is_a(), getattr(e, "PredefinedType", None), names)


def typed(f) -> dict:
    """{element id: the name of its type} of the file `f`, from its IfcRelDefinesByType: one pass over the relations,
    not one question for each element."""
    out: dict = {}
    for rel in f.by_type("IfcRelDefinesByType"):
        kind = getattr(rel, "RelatingType", None)
        name = getattr(kind, "Name", None) if kind is not None else None
        if not name:
            continue
        for e in rel.RelatedObjects or ():
            out[e.id()] = str(name)
    return out


def of_file(f) -> set:
    """The ids of the gratings of the file `f` (an IfcOpenShell file)."""
    types = typed(f)
    out = set()
    for cls in ("IfcSlab", "IfcPlate", "IfcCovering", "IfcBuildingElementPart", "IfcBuildingElementProxy"):
        try:
            elements = f.by_type(cls)
        except RuntimeError:                # a class the file's schema does not have (IfcBuildingElementPart in 2x3)
            continue
        out.update(e.id() for e in elements if of_entity(e, types))
    return out
