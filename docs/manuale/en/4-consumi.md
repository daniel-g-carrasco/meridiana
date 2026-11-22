<a id="4-consumi"></a>

# 4. Consumption

Consumption determines how much production is used on site. The balance matches it with production hour by hour, so its shape is needed as well as its total.

<a id="da-dove-vengono"></a>

## Where it comes from

On the Consumption page choose the basis: a yearly total, the three bands F1, F2, F3, bills month by month, a measured curve (15-minute or hourly CSV, Compute > Import a load curve…) or a typical profile. Without data, Meridiana estimates consumption from the project and says so in Checks, under To know. The resulting balance is indicative.

<a id="i-risultati"></a>

## The results

<a id="consumo-allanno"></a>

### Consumption a year

A year's consumption, from what you entered. The other tiles describe its shape.

<a id="le-fasce"></a>

### The bands

Electricity time bands (`energy/bands.py`):

- F1: Monday to Friday, from 8 to 19;
- F2: Monday to Friday from 7 to 8 and from 19 to 23; Saturday from 7 to 23;
- F3: nights, Sundays and public holidays; Saturday hours outside F2.

A site using its energy in F1 overlaps better with daytime production. Band prices are on the [Balance](5-bilancio.md#prezzi) page.

<a id="la-forma-dei-consumi"></a>

### Shape of the consumption

The first figures an energy analysis looks at (`energy/consumption.py`, `figures`):

- the highest hour of the year;
- the base load: the power below which consumption almost never falls, taken as the 5th percentile of hours (consumption stays above it in 95% of hours);
- the load factor: mean consumption divided by the highest hour;
- the share of consumption between 8 and 18, when a plant produces most;
- the share on weekends and public holidays.

A site active during the day uses more production. One consuming at night or on weekends sends more to the grid, and storage can help there.
