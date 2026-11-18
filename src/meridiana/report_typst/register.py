"""The register of the calculations as the report prints it (R314, study 24): every step of a calculation and every row
of a table with a code («R-010.07»), so a number in the report leads to a precise line in the register. The codes are
given as the report is written, so they hold for that report, not across reports."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..i18n import _
from .blocks import plain


@dataclass
class Group:
    code: str
    title: str
    rows: list = field(default_factory=list)         # (code, what, value, where from)

    def add(self, what: str, value: str, where: str) -> str:
        code = f"{self.code}.{len(self.rows) + 1:02d}"
        self.rows.append((code, what, value, where))
        return code


class Register:
    """`active`: the report has the register as a chapter; otherwise a table says its source in words."""

    def __init__(self, active: bool, records: list):
        self.active = active
        self.groups: list[Group] = []
        self.steps: dict[str, tuple[str, str]] = {}        # the key of a step -> (its code, its title)
        for record in records:
            group = self.group(record.title)
            for step in record.steps:
                value = step.result.text() if step.result is not None else "–"
                where = step.reference or _("Parameters and methods")
                code = group.add(step.title, value, where)
                self.steps.setdefault(step.key, (code, step.title))

    def group(self, title: str) -> Group:
        for g in self.groups:
            if g.title == title:
                return g
        g = Group(f"R-{10 * (len(self.groups) + 1):03d}", title)
        self.groups.append(g)
        return g

    def step(self, key: str) -> tuple[str, str] | None:
        """The step with this key, or whose key ends with it (a step of the first array, «s1.0.poa» for «poa»)."""
        if key in self.steps:
            return self.steps[key]
        return next((v for k, v in self.steps.items() if k.endswith("." + key)), None)

    def code(self, where: str, group: str, what, value) -> str:
        """The code a row shows: `where` the key of a step, whose code it takes, or the words of its source, for a line
        of its own in `group`. "" when the report has no register."""
        if not self.active:
            return ""
        found = self.step(where) if where else None
        if found is not None:
            return found[0]
        return self.group(group).add(plain(what), plain(value), where or "")

    def words(self, where: str) -> str:
        """The source in words: a step by its title and code, else as it is."""
        found = self.step(where) if where else None
        if found is None:
            return where
        return f"{found[0]}, {found[1]}" if self.active else found[1]

    def row_where(self, where: str) -> str:
        return self.words(where)
