"""Existing profile-specific inputs, without presentation labels."""
from meridiana.core.rules.types import InputField
from .defaults import defaults
from . import rules, vvf_activities

def fields(section):
    if section == "site":
        values = {"rules.obligation": "", "rules.public": False, "rules.use": "other", "rules.permit_2027": False,
                  "rules.floor_m2": 0.0, "rules.premises": "", "rules.risk": False}
    elif section == "network":
        values = {"network.level": "", "network.connection": "", "network.practice_code": ""}
    elif section == "building":
        values = {"fire.subject": False, "fire.activity": 0, "fire.category": "", "fire.roof_fire_resistant": False}
    elif section in {"layout", "consumption", "economics"}:
        values = defaults(section)
        if section == "layout":
            values = {"params." + key: value for key, value in values.items()}
    else:
        raise KeyError(section)
    choices = {"rules.obligation": rules.OBLIGATIONS, "rules.use": rules.USES,
               "rules.premises": rules.PREMISES, "network.level": ("", *rules.LEVELS),
               "network.connection": ("", "existing", "new", "modification"),
               "fire.category": ("", *vvf_activities.CATEGORIES)}
    return tuple(InputField(path, type(value).__name__ if value is not None else "float", value, choices.get(path, ()), ())
                 for path, value in values.items())
