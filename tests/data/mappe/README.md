# Capabilities recorded for the tests of the map sources (R36)

Documents that the servers gave on 25/10/2026 to a GetCapabilities (or a GetMap, for the error) asked with
Meridiana's User-Agent, for `tests/nucleo/test_capabilities.py` and the page Preferences > Maps. They are service
metadata, kept for the tests only; the licences of the imagery are in `docs/compiti/21-mappe.md`.

| File | Asked to | What was done |
|---|---|---|
| `wmts-pdok.xml` | `https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0?request=GetCapabilities&service=WMTS` | only the layers `Actueel_orthoHR` and `Actueel_ortho25` and the matrix sets `EPSG:3857` and `EPSG:28992` kept |
| `wmts-swisstopo.xml` | `https://wmts.geo.admin.ch/EPSG/3857/1.0.0/WMTSCapabilities.xml` | only the layer `ch.swisstopo.swissimage` and the set `3857_20` kept |
| `wmts-ign.xml` | `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetCapabilities&VERSION=1.0.0` | only `ORTHOIMAGERY.ORTHOPHOTOS`, `HR.ORTHOIMAGERY.ORTHOPHOTOS` and the sets `PM_0_19`, `PM_6_19` kept |
| `wmts-nrw.xml` | `https://www.wmts.nrw.de/geobasis/wmts_nw_dop/1.0.0/WMTSCapabilities.xml` | unchanged |
| `wms-wallonie.xml` | `https://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_LAST/MapServer/WMSServer?request=GetCapabilities&service=WMS` | unchanged |
| `wms-bayern-111.xml` | `https://geoservices.bayern.de/od/wms/dop/v1/dop20?SERVICE=WMS&REQUEST=GetCapabilities` (it answers in 1.1.1) | unchanged |
| `wms-errore.xml` | a GetMap of a layer that does not exist to `https://siat.provincia.tn.it/geoserver/stem/ecw-rgb-2015/wms` | unchanged |

The three WMTS files were cut with Python's ElementTree (the other layers and sets taken out, the namespaces kept):
a few tens of KB instead of 1,8 to 3 MB.
