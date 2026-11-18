"""The plan's short, step-specific instructions: one catalogue with the rest (po/it.po).

Where the plan's hint bar says a text more briefly than the Widgets, its entry has msgctxt "plan"; every other text
of the plan is the program's own entry.
"""
from ... import i18n

CONTEXT = "plan"


def _(message):
    translated = i18n.pgettext(CONTEXT, message)
    return i18n._(message) if translated == message else translated
