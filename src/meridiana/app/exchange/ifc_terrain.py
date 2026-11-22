"""The model's terrain, recognised (R575 D4): a photovoltaic design wants the building of an IFC, and a model's
terrain (Revit's toposolid, 180 x 179 m in one model, 230 x 325 m in another) became an obstacle «tree» 1.36 m above
the lawn, «buildings» kilometres wide, and filled the import's preview. It is never an obstacle nor a body, and it is
not drawn unless asked.

The rule (studio-r575, «La regola proposta per Meridiana»): terrain is an element with at least one of
- the class IfcGeographicElement of type TERRAIN or without a type (unless its name says it is a tree);
- a presentation layer starting with C-TOPO (the layer of Revit's toposolids in both models met);
- a name, object type or type name with «topografic», «toposolid», «terrain», «gelände», or «terreno» (not «piano
  terreno», the ground floor in Italian);
- a material «Terreno», «Terrain», «Earth».
The same Revit object comes out as IfcGeographicElement in IFC4 and as a proxy in IFC2X3: the class alone is not
enough. The rule of the shape (thin, flat, wider than the roofs) is not applied here. Without Qt."""

from __future__ import annotations

import re

LAYER_PREFIX = "C-TOPO"
NAME = re.compile(r"topogra(f|ph)ic|toposolid|terrain|gel(ä|ae)nde(?!r)")      # not «Geländer», a railing
GROUND_FLOOR = re.compile(r"piano[\s_-]*terreno")
MATERIAL = re.compile(r"\b(terreno|terrain|earth)\b")        # not «earthing», a conductor
TREE = re.compile(r"\b(albero|alberi|tree|trees|baum|bäume|boom|arbre|arbres|planting)\b")


def _text(values) -> str:
    return " ".join(str(v) for v in values if v).lower()


def is_terrain(cls: str, predefined: str | None = None, names=(), layers=(), materials=()) -> bool:
    """Whether an element is the model's terrain: `cls` its class (any case), `predefined` its PredefinedType (as
    «TERRAIN» or «.TERRAIN.»), `names` its name, object type and type name, `layers` its presentation layers,
    `materials` the names of its materials."""
    words = _text(names)
    if any(_is_layer(layer) for layer in layers):
        return True
    if NAME.search(words) or "terreno" in GROUND_FLOOR.sub("", words):
        return True
    if MATERIAL.search(_text(materials)):
        return True
    if str(cls or "").upper() == "IFCGEOGRAPHICELEMENT":
        kind = str(predefined or "").strip(".").upper()
        if kind == "TERRAIN":
            return True
        if kind in ("", "NOTDEFINED") and not TREE.search(words):
            return True
    return False


def _is_layer(name) -> bool:
    return str(name or "").strip().upper().startswith(LAYER_PREFIX)


def layered(f, memo: dict | None = None) -> set:
    """The ids of the entities of the file `f` from which `ifcopenshell.util.element.get_layers` reaches a terrain layer:
    the shape representations and geometric items such a layer is assigned to (the two kinds get_layers looks at), and
    everything that refers to them, step by step up to the products' representations. Empty when no layer of the file
    has a terrain's name, as in most models. Kept in `memo` (a reading's cache) under a key of its own when given."""
    key = ("terrain-layered",)
    if memo is not None and key in memo:
        return memo[key]
    stack = [x for layer in f.by_type("IfcPresentationLayerAssignment") if _is_layer(getattr(layer, "Name", None))
             for x in layer.AssignedItems or ()
             if x.is_a("IfcShapeRepresentation") or x.is_a("IfcGeometricRepresentationItem")]
    found: set = set()
    while stack:
        x = stack.pop()
        if x.id() not in found:
            found.add(x.id())
            stack.extend(f.get_inverse(x))
    if memo is not None:
        memo[key] = found
    return found


def of_entity(e, memo: dict | None = None) -> bool:
    """`is_terrain` of an IfcOpenShell entity (its layers, materials and type through ifcopenshell.util). Its layers are
    asked for only when they can change the answer: `get_layers` traverses the element's whole representation, a third
    of the reading of a 38 MB model (r33), and finds a terrain layer exactly when that representation is among the
    file's `layered` entities. `memo` keeps those for the file."""
    names = [getattr(e, "Name", None), getattr(e, "ObjectType", None)]
    layers, materials = [], []
    try:
        import ifcopenshell.util.element as util
        kind = util.get_type(e)
        if kind is not None:
            names.append(getattr(kind, "Name", None))
        if not is_terrain(e.is_a(), getattr(e, "PredefinedType", None), names):
            # the representations get_layers starts from, chosen as it does
            rep = getattr(e, "Representation", None)
            starts = [rep] if rep else list(getattr(e, "RepresentationMaps", None) or ())
            reached = layered(e.file, memo)
            if reached and any(r.id() in reached for r in starts):
                layers = [getattr(x, "Name", None) for x in util.get_layers(e.file, e) or []]
        materials = [getattr(m, "Name", None) for m in util.get_materials(e) or []]
    except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
        pass
    return is_terrain(e.is_a(), getattr(e, "PredefinedType", None), names, layers, materials)
