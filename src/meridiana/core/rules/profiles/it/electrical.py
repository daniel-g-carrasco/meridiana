"""Existing Italian electrical factors, protections, sources and messages."""
from dataclasses import dataclass
from meridiana.i18n import _, number
from meridiana.core.energy.pedigree import Source
from .defaults import STRINGS

NORM = "CEI 64-8/7:2024-07"


@dataclass(frozen=True)
class ItalianElectricalPolicy:
    voc_fallback: float | None = STRINGS["voc_fallback"]
    voltage_fallback: float | None = STRINGS["voltage_fallback"]
    ki_default: float | None = STRINGS["ki_default"]
    allow_auto: bool = True
    source: str = NORM

    def parallel_cap(self, module, ki):
        return 2 if module.max_series_fuse is None or 1.1 * ki * module.isc > module.max_series_fuse else None

    def selv(self, uoc_max):
        from meridiana.core.energy.stringing import Check
        checks = []
        def add(key, label, ok, detail, level=""):
            checks.append(Check(key, label, bool(ok), detail, level))
        add("selv", _("SELV or PELV possible on the DC side (Uoc max up to 120 V)"), True,
                _("yes") if uoc_max <= 120 else _("no: the DC side needs double or reinforced insulation (712.412)"), "info")
        return checks

    def protection(self, parallel, isc_max, ocpr, input_index):
        from meridiana.core.energy.stringing import Check
        ns, k, i_mod_max_ocpr = parallel, input_index, ocpr
        name = _("input {k}").format(k=k + 1)
        checks = []
        def add(key, label, ok, detail, level=""):
            checks.append(Check(key, label, bool(ok), detail, level))
        if ns > 2:
            ocpr = i_mod_max_ocpr
            if ocpr:
                need = 1.35 * ocpr < (ns - 1) * isc_max
                detail = (_("protection needed: 1.35 x {o} A < ({n} - 1) x {i} A; rating between {a} A and {o} A").format(
                    o=number(ocpr, 0), n=ns, i=number(isc_max, 2), a=number(1.1 * isc_max, 1)) if need else
                    _("no protection needed: 1.35 x {o} A >= ({n} - 1) x {i} A").format(o=number(ocpr, 0), n=ns,
                                                                                    i=number(isc_max, 2)))
                add(f"fuse{k}", _("{name}: protection of the strings (712.431.101)").format(name=name), True, detail)
                if need and 1.1 * isc_max > ocpr:
                    add(f"fuserange{k}", _("{name}: a fuse rating exists").format(name=name), False,
                        _("1.1 x Isc max is above the module's maximum overcurrent protection: fewer strings"))
            else:
                add(f"fuse{k}", _("{name}: protection of the strings (712.431.101)").format(name=name), False,
                    _("the module's maximum series fuse is not known: enter it to check"))
        return checks

    def pedigree(self, key):
        return {
            "ki": Source("norm", "KI", f"{NORM}, B.2"),
            "temperature_missing": Source("norm", _("no minimum temperature: the standard's 1.2"), f"{NORM}, B.1"),
        }[key]

    def text(self, key):
        return {
            "check_source": "CEI 64-8/7:2024",
            'isc_formula': 'I_{SC\\,MAX} = K_I\\,I_{SC\\,STC},\\ K_I \\geq 1{,}25',
            'isc_explanation': _('The current a string can give, with the margin the standard asks for reflection and strong sun.'),

            "title": _("Strings: checks of CEI 64-8/7"),
            "uoc_reference": f"{NORM}, Allegato B, B.1, p. 109",
            "isc_reference": f"{NORM}, Allegato B, B.2, p. 109",
            "ki_label": _("factor of the standard"),
            "scope": "",
        }[key]
