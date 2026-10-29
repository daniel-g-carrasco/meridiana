"""Storage topology checks and an explicitly AC-referenced energy model.

Compatibility evidence is exact-model, never inferred from a brand or free text.
The hourly production is already AC: do not apply PV inverter efficiency again.
"""
from dataclasses import dataclass, field
from math import isfinite

from ..i18n import _


def positive(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None
    return number if isfinite(number) and number > 0 else None


def voltage_range(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    low, high = (positive(v) for v in value)
    return (low, high) if low and high and low < high else None


def battery_voltage(battery, inverter):
    ranges = battery.get("voltage_range_by_phases_v") or {}
    return voltage_range(ranges.get(str(inverter.get("phases")))) or voltage_range(battery.get("voltage_range_v"))


@dataclass
class StorageCheck:
    status: str
    messages: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    charge_kw: float | None = None
    discharge_kw: float | None = None
    missing_limits: list[str] = field(default_factory=list)


def check_storage(battery: dict, inverter: dict, coupling: str, units: int = 1) -> StorageCheck:
    """Check one complete battery system per unit, in parallel on one converter.

Missing ratings remain unknown. A compatible pairing does not assert that every
rating is available; messages enumerate missing electrical checks separately.
"""
    result = StorageCheck("unknown")
    failures = []
    count = positive(units)
    if count is None or count != int(count):
        return StorageCheck("incompatible", [_("Battery quantity must be a positive integer.")])
    if coupling not in ("ac", "dc"):
        return StorageCheck("incompatible", [_("Select AC or DC coupling.")])
    declared = battery.get("coupling")
    if declared and declared != coupling:
        failures.append(_("The battery system does not support the selected coupling."))
    maximum = positive(battery.get("max_parallel_units"))
    if maximum and maximum != int(maximum):
        failures.append(_("Battery quantity must be a positive integer."))
    if maximum and count > maximum:
        failures.append(_("Battery quantity exceeds the documented parallel limit."))
    if coupling == "ac":
        if count > 1 and maximum is None:
            result.missing_limits.append(_("Maximum compatible battery quantity is not documented."))
        result.status = "compatible" if declared == "ac" else "unknown"
        result.messages.append(_("AC storage has its own converter; PV inverter brand is independent."))
        if declared != "ac":
            result.messages.append(_("An integrated AC converter has not been documented for this battery."))
    else:
        if inverter.get("storage_limit_notes"):
            result.messages.append(str(inverter["storage_limit_notes"]))
        if inverter.get("type") not in (None, "hybrid", "battery"):
            failures.append(_("The selected inverter has no documented storage interface."))
        entries = inverter.get("storage_compatibility", [])
        exact = [r for r in entries if isinstance(r, dict)
                 and r.get("battery_manufacturer") == battery.get("manufacturer")
                 and r.get("battery_model") == battery.get("model") and r.get("source")]
        if exact:
            admitted = [r for r in exact if (positive(r.get("units_min")) or 1) <= count
                        and (positive(r.get("units_max")) is None or count <= positive(r.get("units_max")))]
            if not admitted:
                failures.append(_("Battery quantity is outside the documented compatible configuration."))
            else:
                result.status = "compatible"
                result.sources = [str(r["source"]) for r in admitted]
                bounded = []
                for row in admitted:
                    bounds = [positive(row.get(key)) for key in ("units_min", "units_max")]
                    if all(v is not None and v == int(v) for v in bounds) and bounds[0] <= count <= bounds[1]:
                        bounded.append(row)
                if not bounded:
                    result.missing_limits.append(_("Maximum compatible battery quantity is not documented."))
        else:
            result.messages.append(_("No exact-model compatibility evidence is available."))
        bv = battery_voltage(battery, inverter)
        iv = voltage_range(inverter.get("battery_voltage_range_v"))
        if bv and iv:
            if bv[0] < iv[0] or bv[1] > iv[1]:
                failures.append(_("Battery operating voltage is outside the inverter storage range."))
        else:
            result.missing_limits.append(_("Operating voltage range is missing; nominal voltage is not a substitute."))
        if not positive(inverter.get("battery_current_max_a")):
            result.missing_limits.append(_("Inverter storage current limit is unknown."))
    for direction in ("charge", "discharge"):
        power = positive(battery.get(f"max_{direction}_power_w"))
        if power:
            power *= count
        if coupling == "dc":
            # The legacy battery_power_max_w does not identify the direction.
            limit = positive(inverter.get(f"battery_{direction}_power_max_w"))
            if limit and power:
                power = min(power, limit)
            elif not limit:
                result.missing_limits.append(_("Inverter storage power limit is unknown."))
            current = positive(inverter.get("battery_current_max_a"))
            battery_current = positive(battery.get(f"max_{direction}_current_a"))
            bv = battery_voltage(battery, inverter)
            if bv and current and power:
                power = min(power, bv[0] * current)
            if bv and battery_current and power:
                power = min(power, bv[0] * battery_current * count)
        if power is None:
            result.messages.append(_("Battery power is missing; no power is inferred from capacity."))
        setattr(result, f"{direction}_kw", power / 1000 if power else None)
    if failures:
        result.status = "incompatible"
        result.messages = failures + result.messages
    result.messages = list(dict.fromkeys(result.messages + result.missing_limits))
    return result


def operating_battery(settings: dict):
    """Create a conservative AC-bus equivalent, without multiplying efficiencies.

Explicit topology uses usable energy, declared power and AC round-trip efficiency.
DC coupling is not a DC time-series simulation and cannot recover PV clipping.
"""
    from .economics import Battery
    rec = settings.get("battery") or {}
    if not rec:
        return None
    count = settings.get("battery_units", 1)
    check = check_storage(rec, settings.get("storage_inverter") or {}, settings.get("storage_coupling", "ac"), count)
    if check.status == "incompatible":
        raise ValueError("; ".join(check.messages))
    if check.status == "unknown":
        raise ValueError(_("Document the storage coupling and exact model compatibility before calculation."))
    if check.missing_limits:
        raise ValueError("; ".join(dict.fromkeys(check.missing_limits)))
    energy = positive(rec.get("usable_energy_kwh"))
    eta = positive(settings.get("storage_efficiency_pct"))
    if eta is None and rec.get("efficiency_basis") == "ac_round_trip":
        eta = positive(rec.get("round_trip_efficiency_pct"))
    if not energy or not check.charge_kw or not check.discharge_kw or not eta or eta > 100:
        raise ValueError(_("Storage requires usable energy, charge/discharge power and an explicit AC round-trip efficiency."))
    return Battery(energy * int(count), check.charge_kw, check.discharge_kw, eta / 100,
                   f"{rec.get('manufacturer', '')} {rec.get('model', '')}".strip())


def validate_connection(settings: dict, inverters: list):
    """Reject a dangling DC association after an inverter is removed or replaced."""
    if not settings.get("battery") or settings.get("storage_coupling") != "dc":
        return
    selected = settings.get("storage_inverter") or {}
    def identity(record):
        return (record.get("id"), record.get("manufacturer"), record.get("model"), record.get("source"))
    if not selected or not any(identity(entry.get("record", entry)) == identity(selected)
                               for entry in inverters):
        raise ValueError(_("The storage inverter was removed or replaced. Reconnect storage in Plant."))
