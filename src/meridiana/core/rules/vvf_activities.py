"""Compatibility facade for activity data supplied by a regulatory profile."""

from meridiana.core.rules import registry

from meridiana.core.rules.types import Activity, Band  # noqa: F401

SOURCE = registry.get("it").activity_data("SOURCE")

PROCEDURE = registry.get("it").activity_data("PROCEDURE")

PV_NOT_AN_ACTIVITY = registry.get("it").activity_data("PV_NOT_AN_ACTIVITY")

CATEGORIES = registry.get("it").activity_data("CATEGORIES")

ACTIVITIES = registry.get("it").activity_data("ACTIVITIES")

NOT_SPECIFIED = registry.get("it").activity_data("NOT_SPECIFIED")


def activity(number, *, profile_id: str = "it"):
    return registry.get(profile_id).activity_call("activity", number)


def search(query: str, *, profile_id: str = "it"):
    return registry.get(profile_id).activity_call("search", query)


def index(*, profile_id: str = "it"):
    return registry.get(profile_id).activity_call("index")


def shown(subject: bool, number: int, *, profile_id: str = "it"):
    return registry.get(profile_id).activity_call("shown", subject, number)


def chosen(value: int, category: str = "", *, profile_id: str = "it"):
    return registry.get(profile_id).activity_call("chosen", value, category)


def as_dict(a: Activity, *, profile_id: str = "it"):
    return registry.get(profile_id).activity_call("as_dict", a)
