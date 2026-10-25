"""Where every number comes from. A calculation is a list of steps; each step says what it computes, the
formula (LaTeX, in the subset matplotlib's mathtext draws), the values that went in with their source, the
value that came out, and the reference: a standard with edition and clause, a published model, a data
set. The window shows the steps under "How it is computed" and the report prints them: a result that
cannot be shown this way is not given.

The sources are of six kinds, so the designer sees at a glance what to check:
- input: typed by the designer;
- default: chosen by Meridiana when nothing was typed, with the reason;
- data: a data set or a datasheet (PVGIS, a manufacturer, a catalogue), with its date;
- norm: a standard or a law, with edition, clause and page;
- model: a published physical model (Perez 1990, the PVsyst thermal model...);
- computed: the result of an earlier step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..i18n import number

KINDS = ("input", "default", "data", "norm", "model", "computed")


@dataclass(frozen=True)
class Source:
    kind: str
    label: str
    ref: str = ""

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"source kind {self.kind!r}")


@dataclass
class Quantity:
    symbol: str                 # LaTeX, without the dollars
    label: str
    value: float | int | str
    unit: str = ""
    source: Source | None = None
    decimals: int = 2

    def text(self) -> str:
        """The value as the window writes it, with its unit."""
        if isinstance(self.value, str):
            return self.value
        v = number(float(self.value), self.decimals)
        return f"{v} {self.unit}".strip()


@dataclass
class Step:
    key: str
    title: str
    formula: str                # LaTeX, without the dollars; "" when the step is a choice, not a formula
    explanation: str
    inputs: list[Quantity] = field(default_factory=list)
    result: Quantity | None = None
    reference: str = ""


@dataclass
class Record:
    """The steps of one calculation, in order."""
    title: str
    steps: list[Step] = field(default_factory=list)

    def add(self, step: Step) -> Quantity | None:
        self.steps.append(step)
        return step.result

    def find(self, key: str) -> Step | None:
        return next((s for s in self.steps if s.key == key), None)

    def merge(self, other: Record) -> None:
        self.steps.extend(other.steps)


def computed(label: str) -> Source:
    return Source("computed", label)
