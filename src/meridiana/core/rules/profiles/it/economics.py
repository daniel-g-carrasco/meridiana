"""Existing Italian tariffs and fiscal contributions, without revising any amount or source."""
from dataclasses import dataclass
import numpy as np
from meridiana.i18n import _
from meridiana.core.rules.types import PolicyFlows
from meridiana.core.energy.pedigree import Source, Step, Quantity, computed

NORTH = ("emilia-romagna", "emilia romagna", "friuli", "liguria", "lombardia", "piemonte", "trentino", "alto adige",
         "südtirol", "valle d'aosta", "vallée d'aoste", "veneto")


CENTRE = ("lazio", "marche", "toscana", "umbria", "abruzzo")


DM414 = "DM MASE 414/2023, Allegato 1 (in reference\\laws)"


GSE_RULES = "GSE, Regole operative CACER e TIAD, versione del 16/07/2025, §2.2.2.2.2, p. 45-46"


def zone_from_address(address: str) -> str:
    """The zone of DM 414/2023's correction for PV ("north", "centre", "other") from the site's address."""
    a = address.lower()
    if any(r in a for r in NORTH):
        return "north"
    if any(r in a for r in CENTRE):
        return "centre"
    return "other"


def tip(pz_eur_mwh, power_kw: float, zone: str, grant_pct: float = 0.0):
    """The premium tariff on the shared energy, €/MWh (DM MASE 414/2023, Allegato 1): a fixed part by size plus
    max(0, 180 - Pz), capped by size; then the correction for PV by zone (+10 North, +4 Centre); then the cut
    for a capital grant, F growing linearly to 0.50 for a grant of 40% of the investment."""
    base, cap = (60.0, 100.0) if power_kw > 600 else (70.0, 110.0) if power_kw > 200 else (80.0, 120.0)
    t = np.minimum(base + np.maximum(0.0, 180.0 - np.asarray(pz_eur_mwh, dtype=float)), cap)
    t = t + {"north": 10.0, "centre": 4.0}.get(zone, 0.0)
    f = min(max(grant_pct, 0.0), 40.0) / 40.0 * 0.5
    return t * (1.0 - f)


@dataclass(frozen=True)
class ItalianEconomyPolicy:
    regimes: tuple[str, ...] = ("ordinary", "community")

    def prices(self, settings):
        return {"F1": settings.buy_f1, "F2": settings.buy_f2, "F3": settings.buy_f3}

    def zone_from_address(self, address):
        return zone_from_address(address)

    def tip(self, pz_eur_mwh, power_kw, zone, grant_pct=0.0):
        return tip(pz_eur_mwh, power_kw, zone, grant_pct)

    def flows(self, s, self_by_band, export_y, p_stc_kw, address, capex):
        n_years = len(export_y)
        ys = range(1, n_years + 1)
        prices = self.prices(s)
        zone = s.zone or zone_from_address(address)
        tariff = float(tip(s.pz, p_stc_kw, zone, s.grant_pct)) / 1000.0 if s.community else 0.0
        esc = np.array([(1.0 + s.escalation / 100.0) ** (y - 1) for y in ys])
        saving = (self_by_band[0] * prices["F1"] + self_by_band[1] * prices["F2"] + self_by_band[2] * prices["F3"]) * esc
        sale = export_y * s.sell * esc
        if s.community:
            shared = export_y * s.shared_pct / 100.0
            incentive = np.where(np.array(ys) <= 20, shared * (tariff + s.trase), 0.0)
        else:
            incentive = np.zeros(n_years)
        deduction = np.array([capex * s.deduction_pct / 100.0 / 10.0 if y <= 10 else 0.0 for y in ys])
        return PolicyFlows(saving, sale, incentive, deduction, zone, tariff)

    def community_steps(self, s, year1, zone, tariff):
        if not s.community:
            return []
        computed_ = computed("")
        return [Step("community", _("Renewable energy community"),
                     r"TIP = \min\left(T_0 + \max(0;\ 180 - P_z),\ T_{max}\right) + \Delta_{zona},\quad "
                     r"I_1 = E_{cond}\,(TIP + CU_{Af,a})",
                     _("On the energy fed in that the community consumes in the same hour (shared energy) the GSE pays "
                       "the premium tariff, for 20 years, and gives back the transmission component (TRASE)."),
                     [Quantity(r"E_{cond}", _("shared energy, first year"), year1["export"] * s.shared_pct / 100.0, "kWh",
                               s.source("shared_pct"), 0),
                      Quantity(r"P_z", _("zonal price expected"), s.pz, "€/MWh", s.source("pz"), 0),
                      Quantity("", _("zone"), {"north": _("North (+10 €/MWh)"), "centre": _("Centre (+4 €/MWh)")}.get(
                          zone, _("South and islands")), "", Source("computed", _("from the site's address"))),
                      Quantity(r"CU_{Af,a}", "TRASE", s.trase, "€/kWh", s.source("trase"), 4)],
                     Quantity("TIP", _("premium tariff"), tariff * 1000.0, "€/MWh", computed_, 1),
                     f"{DM414}; {GSE_RULES}")]

    def pedigree(self, key):
        return {"community": Source("norm", "", f"{DM414}; {GSE_RULES}")}[key]

    def text(self, key):
        return {
            "sale_tile": _('Sale and incentives, first year'),
            "npv_explanation": _("Each year's cash flow: saving and sale (growing with the energy prices, shrinking with the "
                   "modules' degradation), incentives and tax deduction, less running costs and the inverter's "
                   "replacement; discounted to today."),
            'balance_explanation': _("Every hour the production first covers the consumption; what is left is fed into the grid, what is missing is taken from it. Hours in Italian local time, bands as ARERA's table."),
            'saving_formula': 'R_1 = \\sum_{F} E_{auto,F}\\, c_F',
            'saving_explanation': _("The energy self-consumed in each band is energy not bought at that band's price."),
            'sale_formula': 'V_1 = E_{imm}\\, p_{RID}',
            'sale_explanation': _('The energy fed into the grid, sold to the GSE by the dedicated withdrawal at the zonal price.'),

            "price_field:F1": "buy_f1", "price_field:F2": "buy_f2", "price_field:F3": "buy_f3",
            "price_label:F1": _("price F1"), "price_label:F2": _("price F2"), "price_label:F3": _("price F3"),
        }[key]
