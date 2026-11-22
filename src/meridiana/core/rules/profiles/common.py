"""The initial values of the computations that do not depend on the country: one table, read by the defaults of every
profile (study 44, section 4; revision r30, finding 10). A value a country decides goes in that profile's own table;
one that is the same everywhere goes here, and no profile writes it again (tests/nucleo/test_predefiniti.py)."""

# the economic analysis: the years and the rates, when the inverter is replaced, the units of a battery, no limit to
# the energy fed in (-1), the degradation from the module's datasheet (negative)
ECONOMICS = {"inverter_year": 12, "years": 25, "discount": 4.0, "escalation": 2.0, "opex_escalation": 2.0,
             "degradation": -1.0, "battery_units": 1, "export_limit_kw": -1.0}

# the consumption: the kind of supply and the shape of the curve, guessed from the data given
CONSUMPTION = {"supply": "auto", "profile": "auto"}
