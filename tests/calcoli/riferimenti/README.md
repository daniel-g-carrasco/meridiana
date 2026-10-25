# Answers of PVGIS 5.3, recorded

Real answers of PVGIS 5.3 (European Commission, Joint Research Centre, https://re.jrc.ec.europa.eu/pvg_tools/),
fetched once with the network on 24/10/2026 at 04:28 UTC from Daniel's PC with `curl`, and kept unchanged: the
tests of `meridiana.energy.meteo` and `meridiana.energy.pvgis` read them through pvlib's own parser, with no
network (`tests/calcoli/test_meteo.py`, class `PVGIS53`). They are never fetched again by the tests; if PVGIS changes
its answers, a new file is added next to these, with its date.

| File | Request | What it is |
|---|---|---|
| `pvgis53-tmy-rho.json.gz` | `https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=45.5226&lon=9.03&outputformat=json&usehorizon=0` | the typical year of Rho (MI), 8760 hours, PVGIS-SARAH3 and ERA5, months of 2005-2023; elevation 151 m, irradiance time offset 0.1767 h. The 1,262,661 bytes of the answer, compressed with gzip (level 9, no time stamp) |
| `pvgis53-printhorizon-rho.json` | `https://re.jrc.ec.europa.eu/api/v5_3/printhorizon?lat=45.5226&lon=9.03&outputformat=json` | the far horizon of the same site from the terrain model, 49 directions every 7.5 degrees (0 = South in PVGIS) |
| `pvgis53-pvcalc-rho.json` | `https://re.jrc.ec.europa.eu/api/v5_3/PVcalc?lat=45.52260&lon=9.03000&peakpower=10.000&loss=14.00&angle=15.0&aspect=0.0&mountingplace=free&pvtechchoice=crystSi2025&usehorizon=1&outputformat=json` | the production estimate of 10 kWp at 15 degrees facing South with 14 % of system losses: 13,220.71 kWh a year. The query is the one `pvgis.params_of` makes |
| `pvgis53-tmy-mare-400.json` | `https://re.jrc.ec.europa.eu/api/v5_3/tmy?lat=40.0&lon=-30.0&outputformat=json&usehorizon=0` | the answer with status 400 for a point in the Atlantic: `{"message":"Location over the sea. Please, select another location","status":400}` |

Not recorded, made up in the tests: the 403 "This url is blocked" that PVGIS 5.3 gave from Daniel's office on
22/10/2026 (its body was not kept), an answer cut short and one with a column missing.

PVGIS data are (c) European Union; the Commission's reuse policy allows them to be reused with the source said
(see also `ATTRIBUTIONS.md`).
