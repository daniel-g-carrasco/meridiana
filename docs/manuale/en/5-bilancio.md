<a id="5-bilancio-ed-economia"></a>

# 5. Balance and economics

Production and consumption meet hour by hour over the typical year. What is used on site saves on the bill; the rest goes to the grid and is sold. Cash flows over the analysis years then give the net present value, internal rate of return and payback. How it is computed shows every step with its sources.

<a id="autoconsumo"></a>

## Self-consumption

Production used on site in the same hour, divided by total production; the rest goes to the grid. It is computed hour by hour, not from monthly totals, which would overestimate it. A battery stores part of the daytime surplus for the evening and increases it.

<a id="autosufficienza"></a>

## Self-sufficiency

Consumption covered by the system, directly or through the battery, divided by total consumption. With storage it rises; without it, night-time energy always comes from the grid. High self-consumption and low self-sufficiency indicate a system small for the consumption; the reverse indicates a large system selling a lot.

<a id="il-primo-anno"></a>

## The first year

- **Saving**: the energy self-consumed in each band multiplied by its price.
- **Sale and incentives**: energy fed in multiplied by its value (dedicated withdrawal), plus the energy community incentive if the plant belongs to one.
- **Bill**: the energy part of the bill, month by month, without and with the system.

<a id="valore-attuale-netto"></a>

## Net present value

The cash flows of each analysis year, discounted at the chosen rate, minus the investment. If positive, the system returns more than it costs at that rate. Defaults are 25 years and a rate of 4%, with energy prices growing by 2% a year (Meridiana defaults, `energy/economics.py`, `Settings`). The Size chart shows how it changes with the plant's power.

<a id="il-rendimento"></a>

## Return

- **Investment**: the turnkey cost per kWp (1,300 €/kWp by default) or the total offer, which takes precedence when present.
- **Internal rate of return**: the rate that brings net present value to zero.
- **Payback**: the year in which cumulative cash flow becomes positive.
- **Levelised cost of energy**: the cost of each kWh produced over the analysis years.

Operating costs (20 €/kWp a year) and inverter replacement (in year 12, 150 €/kW) are Meridiana defaults (`energy/economics.py`, `Settings`).

<a id="prezzi"></a>

## Prices

The prices of energy bought and sold and the costs start from indicative values: 0.25 €/kWh for each band, 0.10 €/kWh for energy fed in (Meridiana defaults, `energy/economics.py`, `Settings`). They are marked as defaults in How it is computed and Checks, and the report lists them at the end. Replace them with the bill's figures (all variable costs, including taxes) and the installer's offer: these figures affect the result most.
