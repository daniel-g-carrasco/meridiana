"""R374, R375, R376: the models of the catalogue (data/models/catalog.json) for the kinds of 3D object (props.KINDS):
which model each kind is drawn with in the 3D view, which models a kind can choose among (the people's variants, the
two lamps), the groups the picker shows (Shell/ObjectPicker.qml), the mix a «small family» draws from, and the
preview of each kind (data/models/previews, made by tools/model_previews.py). Nothing here touches the calculation:
the shadow is the kind's (props.casts_shadow), the model is only what is seen."""
from __future__ import annotations

from meridiana import model, props
from meridiana.i18n import _
from meridiana.paths import shipped

from . import scene_assets

# the model each kind is drawn with; a kind that is not here is drawn by props.py (the trees, the roof obstacles)
ASSET_FOR_KIND = {
    'compact': 'car', 'suv': 'suv', 'truck': 'truck', 'pickup': 'pickup_truck', 'sports_car': 'sports_car',
    'bicycle': 'bicycle_innerscene',
    'adult': 'casual_standing', 'walking': 'casual_walking', 'child': 'casual_standing', 'worker': 'worker_standing',
    'antenna': 'roof_antenna', 'tank': 'water_tank',
    'silo': 'silo', 'container': 'shipping_container', 'gas_tank': 'propane_tank', 'utility_box': 'utility_box',
    'lamp': 'streetlight', 'tower': 'transmission_tower', 'fence': 'fence',
}
# R376: the people, a standing and a walking pose each (Quaternius, CC0), chosen per object in the Properties
STANDING = ('casual_standing', 'man_standing', 'woman_standing', 'worker_standing', 'woman_dress_standing',
            'woman_modular_standing', 'business_man_standing', 'hoodie_standing')
WALKING = tuple(key.replace('_standing', '_walking') for key in STANDING)
ASSETS_FOR_KIND = {'adult': STANDING, 'child': STANDING, 'worker': STANDING, 'walking': WALKING,
                   'lamp': ('streetlight', 'street_light')}
# the picker's groups (Daniel 05/11/2026 on the sketches): the title is translated when read
GROUPS = [('Vehicles', props.CAR_KINDS), ('People', props.PERSON_KINDS),
          ('Plant and furniture', ('lamp', 'utility_box', 'gas_tank', 'tower', 'fence', 'antenna', 'dish', 'tank')),
          ('Containers', ('silo', 'container')), ('Trees', props.TREE_KINDS),
          ('Roof obstacles', tuple(k for k in props.OBSTACLE_KINDS if k not in ('opening', 'antenna', 'dish', 'tank')))]
# what a «small family» (ObjectPicker's third mode) mixes: the kinds, each with the models it may take
MIX = {'person': (('adult', STANDING), ('walking', WALKING)),
       'car': (('compact', ('car',)), ('suv', ('suv',)), ('pickup', ('pickup_truck',)), ('sports_car', ('sports_car',)))}


def active_keys() -> set:
    return {row['key'] for row in scene_assets.catalog(active_only=True)}


def asset_for(prop) -> str | None:
    """The model drawn for the object: its own `asset` when it is a model of the catalogue, else the kind's."""
    if prop.asset and prop.asset in active_keys():
        return prop.asset
    return ASSET_FOR_KIND.get(prop.kind)


def choices(kind: str) -> list[tuple[str, str]]:
    """The models an object of the kind can be drawn with, (key, name), the kind's own first; one or none when the
    kind has a single model."""
    keys = ASSETS_FOR_KIND.get(kind)
    if not keys:
        return []
    names = {row['key']: row['name'] for row in scene_assets.catalog(active_only=True)}
    seen = {}
    for key in keys:
        if key in names:
            seen.setdefault(names[key], []).append(key)
    out = []
    for key in keys:
        if key not in names:
            continue
        name = names[key]
        out.append((key, name if len(seen[name]) == 1 else f"{name} ({key.rsplit('_', 1)[0].split('_')[-1]})"))
    return out


def mix_for(kind: str) -> list[tuple[str, tuple]]:
    """The kinds and models a small family of this kind draws from: the people and the vehicles mix, the rest repeat
    the kind (a group of trees varies in size and turn only)."""
    return list(MIX.get(props.family(kind), ((kind, (ASSET_FOR_KIND.get(kind),)),)))


def preview_url(kind: str) -> str:
    path = shipped('models', 'previews', f'{kind}.png')
    return path.as_uri() if path is not None else ''


def groups() -> list[dict]:
    """The picker's groups: title, and for each kind its id, its name, its preview and whether it is drawn along a
    line (props.PATH_KINDS: the fence, the hedge, the walkway)."""
    names = model.prop_names()
    return [dict(title=_(title), kinds=[dict(id=k, text=names[k], preview=preview_url(k), line=k in props.PATH_KINDS)
                                         for k in kinds]) for title, kinds in GROUPS]
