"""The single source of legacy service defaults."""
from copy import deepcopy

from meridiana.core.rules.profiles.common import CONSUMPTION as COMMON_CONSUMPTION, ECONOMICS as COMMON_ECONOMICS

STRINGS = {"voc_fallback": 1.2, "voltage_fallback": 1000.0, "ki_default": 1.25}

CONSUMPTION = {'pod': '', 'supply': COMMON_CONSUMPTION['supply'], 'contract_kw': 0.0, 'profile': COMMON_CONSUMPTION['profile'], 'annual_kwh': 0.0, 'bands_kwh': {}, 'monthly_kwh': [], 'monthly_bands_kwh': [], 'measured': []}

ECONOMICS = {'buy_f1': 0.25, 'buy_f2': 0.25, 'buy_f3': 0.25, 'sell': 0.1, 'pz': 110.0, 'capex_per_kwp': 1300.0, 'capex_total': 0.0, 'opex_per_kwp': 20.0, 'inverter_year': COMMON_ECONOMICS['inverter_year'], 'inverter_per_kw': 150.0, 'years': COMMON_ECONOMICS['years'], 'discount': COMMON_ECONOMICS['discount'], 'escalation': COMMON_ECONOMICS['escalation'], 'opex_escalation': COMMON_ECONOMICS['opex_escalation'], 'degradation': COMMON_ECONOMICS['degradation'], 'deduction_pct': 0.0, 'community': False, 'shared_pct': 60.0, 'zone': '', 'grant_pct': 0.0, 'trase': 0.0, 'battery': {}, 'battery_units': COMMON_ECONOMICS['battery_units'], 'storage_coupling': '', 'storage_inverter': {}, 'storage_efficiency_pct': None, 'battery_cost_per_kwh': 650.0, 'export_limit_kw': COMMON_ECONOMICS['export_limit_kw']}

LAYOUT = {"fire_edge": 1.0, "fire_group": 20.0, "fire_corridor": 2.0}


def defaults(section):
    return deepcopy({"layout": LAYOUT, "consumption": CONSUMPTION, "economics": ECONOMICS, "strings": STRINGS}[section])
