"""Explicit, static profile selection. No process-wide active profile."""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from meridiana.core.rules.contracts import RegulatoryProfile
from meridiana.core.rules.profiles.it.profile import ItalianProfile

from meridiana.core.rules.profiles.generic.profile import GenericProfile

_PROFILES = {"it": ItalianProfile(), "generic": GenericProfile()}


def get(profile_id: str) -> RegulatoryProfile:
    if not isinstance(profile_id, str) or profile_id not in _PROFILES:
        raise ValueError(f"regulatory_profile: {profile_id!r} is not a registered profile")
    return _PROFILES[profile_id]


def for_project(project) -> RegulatoryProfile:
    return get(project.regulatory_profile)


def validate_timezone(value: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"site.timezone: {value!r} is not text")
    if value:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError(f"site.timezone: {value!r} is not an IANA timezone") from None


def effective_timezone(project) -> str:
    profile = for_project(project)
    value = project.site.timezone
    validate_timezone(value)
    return value or profile.calendar().default_timezone


def identity(project) -> tuple[str, int, str]:
    profile = for_project(project)
    return profile.id, profile.revision, effective_timezone(project)


def legacy_default(section: str, key: str):
    """Compatibility for constructors without a project."""
    return get("it").defaults(section)[key]


def ids() -> tuple[str, ...]:
    return tuple(_PROFILES)
