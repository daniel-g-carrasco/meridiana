"""Immutable plant context captured from computed results, independent of later project edits."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculationBasis:
    inverters: tuple[str, ...] = ()
    connected_modules: int = 0
    laid_modules: int = 0
    battery_count: int = 0
    battery_name: str = ""
    battery_kwh: float = 0.0
    supplied_kwh: float = 0.0

    @property
    def inverter_count(self) -> int:
        return len(self.inverters)


def basis_of(sim, *, battery=None, battery_units: int = 0, econ=None) -> CalculationBasis:
    """Capture the contributing subset and actual battery dispatch from the same computed year.

    Inverters come from the electrical network, not nominal sizing placeholders. Array connectivity is
    explicit even when zero. A battery is included only when the pipeline actually constructed its operating
    model; capacity is not evidence of energy supplied, which comes from the hourly balance instead.
    """
    inverters = tuple(str(item.get("name") or item.get("number", "")) for item in sim.inverters)
    connected = sum(int(a.get("connected_modules", 0)) for a in sim.arrays)
    laid = sum(int(a.get("modules", 0)) for a in sim.arrays)
    included = battery is not None and battery.usable_kwh > 0
    supplied = float(econ.hourly["given"].sum()) if included and econ is not None else 0.0
    return CalculationBasis(inverters, connected, laid, max(1, int(battery_units)) if included else 0,
                            str(battery.name) if included else "", float(battery.usable_kwh) if included else 0.0,
                            supplied)
