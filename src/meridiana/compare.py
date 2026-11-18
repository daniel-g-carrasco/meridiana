"""The variants of a project side by side: what each one gives, from the same computation as the window's
(production, balance, economics), in a few figures with the better one of each row marked.

No Qt here: the window computes each variant away from its thread and shows the table (ui/variants.py)."""

from __future__ import annotations

from .i18n import _, number


def rows() -> list[tuple[str, str, int, str]]:
    """(key, label, decimals, which is better: "high", "low" or "")."""
    return [
        ("kwp", _("Modules (kWp)"), 2, ""),
        ("kwac", _("Inverters (kW)"), 1, ""),
        ("modules", _("Modules laid"), 0, ""),
        ("kwh", _("Production (kWh/year)"), 0, "high"),
        ("yield", _("Specific yield (kWh/kWp)"), 0, "high"),
        ("pr", _("Performance ratio (%)"), 1, "high"),
        ("shading", _("Near shading, with its electrical effect (%)"), 1, "low"),
        ("self_ratio", _("Self-consumed share of the production (%)"), 1, "high"),
        ("self_sufficiency", _("Self-sufficiency (%)"), 1, "high"),
        ("export", _("Energy sold to the grid (kWh/year)"), 0, ""),
        ("battery", _("Storage (kWh usable)"), 1, ""),
        ("capex", _("Cost of the system (€)"), 0, "low"),
        ("npv", _("Net present value (€)"), 0, "high"),
        ("payback", _("Payback (years)"), 1, "low"),
        ("lcoe", _("Levelised cost of energy (€/kWh)"), 3, "low"),
    ]


def summary(out: dict) -> dict:
    """The figures of one variant from what the energy computation gave; {"error": why} without a production."""
    sim = out.get("sim")
    if sim is None:
        return {"error": out.get("error_sim") or _("not computed")}
    chain = {c.key: c.change for c in sim.chain}
    shading = -sum(float(chain.get(k) or 0.0) for k in ("near", "electrical"))
    k = getattr(out.get("econ"), "kpi", None) or {}

    def pct(key):
        return 100.0 * float(k[key]) if k.get(key) is not None else None

    return {"kwp": sim.p_stc_kw, "kwac": sim.p_ac_kw, "modules": sum(int(a.get("modules") or 0) for a in sim.arrays),
            "kwh": sim.energy_kwh, "yield": sim.specific_yield, "pr": 100.0 * sim.pr, "shading": shading,
            "self_ratio": pct("self_ratio"), "self_sufficiency": pct("self_sufficiency"), "export": k.get("export"),
            "battery": float(out.get("battery_kwh") or 0.0), "capex": k.get("capex"), "npv": k.get("npv"),
            "payback": k.get("payback"), "lcoe": k.get("lcoe")}


def best(summaries: list[dict], key: str, better: str) -> int | None:
    """Which variant is the better one on this row (None when the row has no better, or a tie)."""
    values = [(i, s.get(key)) for i, s in enumerate(summaries) if s.get(key) is not None and "error" not in s]
    if not better or len(values) < 2:
        return None
    pick = max if better == "high" else min
    i, v = pick(values, key=lambda x: x[1])
    return None if sum(1 for _i, w in values if abs(w - v) < 1e-9) > 1 else i


def cell(s: dict, key: str, decimals: int) -> str:
    v = s.get(key)
    if v is None:
        return "–"
    return number(float(v), decimals, grouping=True)


def table_text(names: list[str], summaries: list[dict]) -> str:
    """The table as tab-separated text, to paste into a spreadsheet or a document."""
    lines = ["\t".join(["", *names])]
    for key, label, decimals, _better in rows():
        lines.append("\t".join([label, *(cell(s, key, decimals) if "error" not in s else s["error"] for s in summaries)]))
    return "\n".join(lines) + "\n"
