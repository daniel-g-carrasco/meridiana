"""Static presentation composition, independent of language and application state."""
from meridiana.gui.backend.profiles.it.profile import ItalianGuiProfile

from meridiana.gui.backend.profiles.generic.profile import GenericGuiProfile

_PROFILES = {"it": ItalianGuiProfile(), "generic": GenericGuiProfile()}

def get(profile_id):
    try:
        return _PROFILES[profile_id]
    except (KeyError, TypeError):
        raise ValueError(f"Unknown regulatory profile: {profile_id!r}") from None

def ids():
    return tuple(_PROFILES)
