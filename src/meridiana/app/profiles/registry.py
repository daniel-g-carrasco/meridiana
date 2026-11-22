"""Static app-level regulatory composition."""
from meridiana.app.profiles.it.profile import ItalianAppProfile

from meridiana.app.profiles.generic.profile import GenericAppProfile
from meridiana.app.profiles.it.assistant import NATIONAL_MANUAL_SECTIONS
from meridiana.app.profiles.it.help import HELP_IDS

_PROFILES = {"it": ItalianAppProfile(), "generic": GenericAppProfile(national_manual_sections=NATIONAL_MANUAL_SECTIONS, help_ids=HELP_IDS)}

def get(profile_id):
    if not isinstance(profile_id, str) or profile_id not in _PROFILES:
        raise ValueError(f"Unknown regulatory profile: {profile_id!r}")
    return _PROFILES[profile_id]

def for_project(project):
    return get(project.regulatory_profile)

def ids():
    return tuple(_PROFILES)
