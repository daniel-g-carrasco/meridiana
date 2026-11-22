<a id="3-producibilità"></a>

# 3. Production

Meridiana computes the typical year hour by hour, from the sun on the modules to the meter, with the site's weather. On the left are your choices (weather, arrays, inverters, strings, losses); on the right, results: tiles with figures, charts and How it is computed. Compute (F5) runs the calculation again; the panel on the right shows the current variant's figures.

<a id="collegamento-dei-moduli"></a>

## Module connection

Modules laid but not in a string do not contribute to the plant's production. Only modules connected through a string to an input of an inverter present in the plant count. Without connections, calculated energy is zero. Connecting or disconnecting modules makes previous results need recalculation: press F5 after the change. The power and number of modules laid remain geometric information about the project; they do not promise production. The PVGIS comparison estimate follows the connected modules.

<a id="il-meteo-del-sito"></a>

## The site's weather

<a id="pvgis"></a>

### PVGIS

PVGIS is the service of the European Commission's Joint Research Centre (JRC). It provides the site's typical weather year (hour by hour: irradiation, temperature, wind) and the far horizon, with mountains and hills that hide the low sun. Fetch the weather and horizon from PVGIS once; they stay in the cache. Without a network connection, Meridiana computes with what it already has. When you save, they also enter the project file, so it opens and computes on another PC without downloading them again. If you change the site, the previous place's weather is not used. Disable PVGIS network access in File > Settings > Privacy.

The PVGIS, second opinion tile shows PVGIS's estimate (PVcalc service) for the same plant: crystSi2025 technology, average over 2005-2023 (SARAH3 database), as the tile itself states. This is not Meridiana's calculation (a typical year versus an average of years, different losses). A difference of a few percentage points is normal; a large one needs attention.

<a id="i-risultati"></a>

## The results

<a id="energia-allanno"></a>

### Energy a year

The energy the system delivers at the meter in the site's typical year, after the whole chain of losses: shading, reflection, soiling, temperature, wiring, inverter. This is the report's figure. How it is computed shows every step, from the sun to the meter, with its source.

<a id="producibilità-specifica"></a>

### Specific yield

A year's energy divided by the modules' power (kWh/kWp): it compares plants of different sizes. In Italy it is often between 1,000 and 1,500 kWh/kWp, from north to south (an order of magnitude to confirm, not a standard's value). Well below that, check shading, orientation and tilt.

<a id="indice-di-prestazione"></a>

### Performance ratio

The performance ratio (PR): the energy at the meter divided by the energy the modules would deliver at nominal power with the irradiation on their plane. It is a measure of losses, not the site's sunshine. Between 75 and 85% is normal for a plant with little shade (an order of magnitude to confirm). Below that, look at the losses.

<a id="potenza"></a>

### Power

The sum of the modules' nameplate powers at standard test conditions (STC), in kWp; below, the inverters' AC power and DC/AC ratio. For connection rules, the plant's nominal power is the lower of the two (CEI 0-21:2026-07, 3.61, p. 16, cited in `rules.py`).

<a id="perdite"></a>

## Losses

Each item is a step in the chain from the sun to the meter. The chart From the sun to the meter: each step shows them in order; How it is computed gives each formula and source. Defaults (`energy/simulate.py`, `Losses`) are marked as such:

- Perez 1990 transposition model; ground reflectance (albedo) 0.20;
- shading of the far horizon and scene obstacles enabled;
- reflection on the glass, ASHRAE model with b0 = 0.05;
- soiling 2%; module quality 0%; mismatch 1%;
- light-induced degradation (LID) from the module's datasheet, otherwise 1%;
- DC wiring 1.5% at STC; AC wiring 1% at nominal AC power; unavailability 0%;
- cell temperature with the PVsyst thermal model; the electrical effect of shading on strings applied in full.

What the model does not calculate or only estimates (bifacial modules, spectral correction, snow, MV transformer, clipping per MPPT input) is listed at the bottom of How it is computed and in the report.

<a id="come-è-calcolato"></a>

## How it is computed

The How it is computed tab of every results page shows the calculation steps: the formula, explanation, input values with their source (yours, default, data, standard, model, computed), result and reference. The How it is computed › link in the help box opens the tab at the right step.
