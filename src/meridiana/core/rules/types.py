"""Immutable values exchanged by regulatory services."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    import numpy as np


@dataclass(frozen=True)
class StandardRef:
    id: str
    edition: str | None
    status: Literal["as_implemented", "reference_only"]
    source: str


@dataclass(frozen=True)
class InputField:
    path: str
    kind: Literal["str", "bool", "int", "float", "dict", "list"]
    default: object
    choices: tuple[str, ...]
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class FirePolicy:
    enabled: bool
    edge: float
    group: float
    corridor: float
    roof_band: float
    source: str
    ballast_warning: str


@dataclass(frozen=True)
class PolicyFlows:
    saving: np.ndarray
    sale: np.ndarray
    incentive: np.ndarray
    deduction: np.ndarray
    zone: str
    tariff: float


@dataclass
class Facts:
    """What the rules look at, gathered from the project and the last computation."""

    p_dc_kw: float = 0.0
    p_ac_kw: float = 0.0
    inverters: int = 1
    level: str = "BT"
    level_auto: bool = True
    fire: bool | None = None

    fire_activities: list = field(default_factory=list)
    installs: set = field(default_factory=set)
    storage: bool = False
    uoc_max: float | None = None
    obligation: str = ""
    public: bool = False
    use: str = "other"
    permit_2027: bool = False
    region: str = ""
    footprint_m2: float = 0.0
    footprint_of: list = field(default_factory=list)

    contracted_kw: float = 0.0
    floor_m2: float = 0.0
    premises: str = ""
    risk: bool = False

    profile_id: str = "it"

    @property
    def p_nominal_kw(self) -> float:
        """The nominal power is limited by the smaller side of the plant."""
        return min(self.p_dc_kw, self.p_ac_kw) if self.p_ac_kw > 0 else self.p_dc_kw

    @property
    def subject(self) -> bool:
        return self.obligation in ("new", "renovation")


@dataclass
class Rule:
    id: str
    chapter: int
    applies: Callable[[Facts], bool]
    paragraphs: Callable[[Facts], list[str]]
    source: Callable[[], str]
    level: str = "info"


@dataclass
class Item:
    level: str
    area: str
    text: str
    source: str = ""
    target: tuple = ()
    fix: tuple = ()

    fix_label: str = ""
    detail: str = ""

    window_only: bool = False
    # R605: a message that says the same thing on several objects has a key (checks.SAME); the checks put two or more
    # of them in one item whose `members` are the (kind, id) of the objects it stands for
    same: str = ""
    members: tuple = ()


@dataclass(frozen=True)
class Band:
    """One row of the categories: the sub-item it is about ("" for the whole activity) and what falls in A, B, C
    ("" where the cell is empty)."""

    item: str
    a: str = ""
    b: str = ""
    c: str = ""

    def of(self, category: str) -> str:
        return {"A": self.a, "B": self.b, "C": self.c}.get(category, "")


@dataclass(frozen=True)
class Activity:
    number: int
    short: str
    text: str
    threshold: str
    bands: tuple[Band, ...]
    page: int

    def categories(self) -> tuple[str, ...]:
        """The categories this activity can fall in, in order."""
        return tuple(c for c in ("A", "B", "C") if any(b.of(c) for b in self.bands))

    def category_text(self, category: str) -> str:
        """What falls in `category`, sub-item by sub-item: «a) ...: fino a 10 m³»."""
        parts = []
        for b in self.bands:
            cell = b.of(category)
            if cell:
                parts.append(f"{b.item}: {cell}" if b.item else cell)
        return "; ".join(parts)

    def label(self) -> str:
        return f"{self.number}. {self.short}"
