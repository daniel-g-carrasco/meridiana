"""Market qualifications and their exact existing explanations."""
from dataclasses import replace
from meridiana.i18n import _


def rules(opt, inv, base, reason):
    from meridiana.core.energy.optimizers import COM, TOGGLE
    if reason == "country_limited_voltage" and base is not None:
        warning = ("toggle", _("S1200 on an SE33.3K: the string voltage at 850 V"),
                             _("SolarEdge allows it only with the fixed string voltage switched from 750 to 850 V in "
                               "SetApp, offered in Australia, Brazil, India, Israel, South Africa, Thailand and Taiwan: "
                               "ask SolarEdge for Italy, or use S1000 or S1400"),
                             f"{COM}, p. 3, note 11; {TOGGLE}, p. 1")
        return replace(base, warnings=(*base.warnings, warning)), ""
    return base, reason


def partial_fixed_check(x):
    from meridiana.core.energy import stringing
    return stringing.Check(
            "mlpe_partial", _("String {label}: optimizers on some modules only").format(label=x.label), False,
            _("SolarEdge's inverters work only with an optimizer on every module (fixed string voltage): the program "
              "counts one on each of the {n} modules").format(n=len(x.modules)), "fail",
            _("SolarEdge SE25K-SE33.3K, Italian datasheet, p. 1; DS-000105-IT p. 3; DS-000205-EU p. 3"))
