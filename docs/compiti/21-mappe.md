# Compito 21: mappe e foto oltre l'Italia (R36)

Daniel, 23/10/2026: «Ci saranno API per altre mappe, per avere foto mondiali o almeno di paesi europei/occidentali, o
piante fatte meglio?». Lo studio delle licenze è in `docs/studio/18-prove/F-professionale-mappe.md`; la decisione
era «da fare come compito proprio: sorgenti WMS/WMTS/XYZ configurabili con alcune predefinite». Fatto il 25/10/2026
sul ramo `mappe` (da `grafica`, c99a6f5).

Marcatura: **[V]** verificato (letto sulla fonte, provato con una richiesta vera o con un test), **[I]** dedotto.

## 1. Come funziona

- **Le sorgenti sono dati** (`src/meridiana/tiles.py`, `Source`): tipo (`xyz`, `wmts`, `wms`), indirizzo, livello,
  stile, insieme di matrici WMTS con l'identificativo di ogni zoom, sistema del WMS, zoom minimo e massimo, area
  coperta, attribuzione, licenza con l'indirizzo dove è stata letta e la data, una piazza pubblica per la prova.
  Nessuna sorgente del programma vuole una chiave [V: test].
- **WMS a tasselli**: un GetMap di 256 × 256 pixel per ogni tassello, in EPSG:3857; dove il server non lo offre, in
  gradi (CRS:84, o EPSG:4326 con la latitudine prima in WMS 1.3.0 e la longitudine prima in 1.1.1). Gli angoli del
  tassello sono esatti; dentro il tassello, da zoom 10 in su, le righe si scostano da Mercatore meno di 0,2 pixel [I:
  calcolo dell'errore di interpolazione lineare].
- **Dove copre** (`src/meridiana/mapcoverage.py`, generato da `tools/map_coverage.py`): i contorni di Natural Earth
  1:10m (pubblico dominio) di paesi, province italiane, regioni belghe e Länder tedeschi, semplificati a circa 800 m,
  spinti circa 2 km sul mare ma mai sulla terra dei vicini (porti, lagune e moli restano dentro), con le isole minori
  (Capri, Procida, Ponza) assegnate al paese più vicino entro 30 km. Una sorgente è offerta fino a 3 km oltre il suo
  contorno. 56 KB per 33 aree [V].
- **La scelta**: «Automatico» prende la foto migliore che contiene il sito (un ordine scritto nelle sorgenti: l'ortofoto
  della regione o del Land prima di quella nazionale, quella nazionale prima di Sentinel-2 a 10 m); vicino a un
  confine vince la sorgente dell'area che contiene il sito, l'altra è offerta nel menu [V: test su Como, Ponte
  Chiasso, Lugano, Strasburgo, Kehl]. Il menu **Sfondo** della pianta elenca «Automatico: nome della migliore», le foto
  e le mappe che coprono il sito, «Nessuno» e «Altre sorgenti…» (Preferenze > Mappe). Una sorgente scelta che non
  copre il sito (scelta su un progetto francese e poi aperto uno italiano) lascia il posto alla migliore e torna sui
  siti che copre.
- **L'attribuzione** della sorgente in uso è sempre in basso a destra della pianta, mai dietro un interruttore (lo
  chiede la politica di OpenStreetMap); `{year}` diventa l'anno corrente per le sorgenti tedesche che chiedono l'anno
  del prelievo.
- **Preferenze > Mappe**: la sorgente da cui partire (fra quelle del sito), le sorgenti del sito e tutte quelle del
  programma come righe (`ui/rows.py`, niente tabelle nelle schede) con la licenza, e nel suggerimento l'attribuzione,
  l'indirizzo della licenza e la data di lettura; **le sorgenti del progettista**: un modello XYZ, oppure un WMS o un
  WMTS letti dalle loro capabilities (i livelli usabili elencati: WMS in EPSG:3857 o in gradi, WMTS sulla griglia di
  Google con qualsiasi nome delle matrici, anche quelli di NRW che partono da «00» allo zoom 5), il nome,
  l'attribuzione (senza, la sorgente non si usa e la pagina lo dice), la licenza e dove è stata letta, foto o mappa,
  zoom massimo. `{key}` nell'indirizzo vuol dire chiave: va nel portachiavi del sistema (servizio `meridiana-maps`),
  mai nelle impostazioni, nella cache o nei messaggi (mascherata). Le sorgenti del progettista non sono mai scelte da
  sole dall'«Automatico»: solo quando le sceglie lui.
- **Privacy**: l'interruttore «Mappa sotto la pianta» di Preferenze > Privacy resta il cancello di ogni sorgente; con
  l'interruttore spento la pagina Mappe non legge nemmeno le capabilities [V: test].
- **Cache**: una cartella per sorgente (`cache/tiles/<chiave>`; per le sorgenti del progettista la chiave più
  un'impronta dell'indirizzo, così un indirizzo cambiato non mescola i tasselli). Mai il prelievo anticipato: si
  chiedono solo i tasselli della vista.
- **Impostazioni versione 19** (`_v18_to_v19`): `map_sources` (le sorgenti del progettista, nessuna) e lo sfondo
  `"auto"`: il vecchio predefinito `"pcn"` diventa `"auto"` (in Italia resta l'ortofoto nazionale, o quella aperta
  della regione dove c'è), una sorgente scelta per nome resta. File congelato `tests/formati/file/config-v19.json`.

## 2. Le sorgenti del programma

Licenze lette sulle pagine ufficiali il 25/10/2026 (quattro ricerche parallele, poi riletti da me la pagina della
Regione FVG e il record SNIG del Portogallo; tutti gli indirizzi delle licenze rispondono 200 [V: curl, 25/10/2026]).
Prova: `python tools/try_map_sources.py`, User-Agent `Meridiana/0.1.0 (+https://github.com/daniel-g-carrasco/meridiana)`,
due tasselli contigui alla piazza indicata, zoom 18 (14 per Sentinel-2, 16 per USGS, 17 per OpenTopoMap); 25/10/2026
alle 01:29, **72 tasselli su 72 buoni** dopo il passaggio della Polonia al WMTS [V].

### Italia

| Sorgente | Servizio | Licenza (dove è letta) | Prova |
|---|---|---|---|
| Ortofoto nazionale 2012 (`pcn`, Geoportale Nazionale, AGEA, 50 cm) | WMS `http://wms.pcn.minambiente.it/ogc?map=/ms_ogc/WMS_v1.3/raster/ortofoto_colore_12.map` | nessun vincolo né costo dichiarato (capabilities, letto il 23/10/2026, studio 18 F) | Milano, piazza del Duomo: 200, JPEG 16-18 KB |
| Alto Adige 2023 (`it-bz`, 20 cm) | XYZ `https://geoservices.buergernetz.bz.it/mapproxy/root/wmts/p_bz-Orthoimagery:Aerial-2023-RGB/EPSG_3857/{z:02d}/{x}/{y}.png` | CC BY 4.0 (`https://geonetwork1.civis.bz.it/geonetwork/srv/api/records/p_bz:Orthoimagery:Aerial-2023-RGB`) | Bolzano, piazza Walther: 200, 15 KB |
| Trentino 2015 (`it-tn`, 20 cm) | WMS `https://siat.provincia.tn.it/geoserver/stem/ecw-rgb-2015/wms` | CC BY 2.5 IT (`https://pctrento.it/PORTALE/OFD2015/licenza_ofd_2015.pdf`) | Trento, piazza Duomo: 200, 12-14 KB |
| Toscana 2023 (`it-toscana`, 20 cm) | WMS `https://www502.regione.toscana.it/ows_ofc/com.rt.wms.RTmap/wms?map=owsofc_rt`, livello `rt_ofc.5k23.32bit` | CC BY 4.0 (record `r_toscan:66ca3807-…`); il `map=owsofc` con le AGEA 2016-2022 non è usato | Siena, piazza del Campo: 200, 18-22 KB |
| Friuli Venezia Giulia, true ortofoto 2017-2020 (`it-fvg`, 10 cm) | WMS `https://irdat-ortofoto.regione.fvg.it/geoserver/ows`, livello `ortofoto:trueorto_FVG_1720` | IODL 2.0: «licenziati con l'Italian Open Data Licence v2.0» (DGR 2626/2014, art. 7, sulla pagina regionale `…/conoscere-ambiente-territorio/FOGLIA4/`, letta da me) | Trieste, piazza Unità: 200, 15-19 KB |

### Europa

| Sorgente | Servizio | Licenza (dove è letta) | Prova |
|---|---|---|---|
| Francia, IGN (`fr-ign`, 20 cm) | WMTS a coppie `https://data.geopf.fr/wmts`, `ORTHOIMAGERY.ORTHOPHOTOS`, `PM_0_19` | Licence Ouverte Etalab 2.0; CGU `https://cartes.gouv.fr/cgu` (15/10/2024): gratuito anche commerciale, endpoint pubblico senza chiave, WMTS senza limite | Parigi, Hôtel-de-Ville: 200, 15-17 KB |
| Spagna, PNOA (`es-pnoa`) | WMTS `https://www.ign.es/wmts/pnoa-ma`, `GoogleMapsCompatible` | CC BY 4.0 scne.es (`https://www.ign.es/resources/licencia/Condiciones_licenciaUso_IGN.pdf`): attribuzione visibile a piè di mappa | Madrid, Plaza Mayor: 200, 17 KB |
| Portogallo, OrtoSat 2023 (`pt-dgt`, satellite Pléiades Neo, 30 cm, solo continente) | WMS `https://ortos.dgterritorio.gov.pt/wms/ortosat2023` | «Serviço de visualização sem restrições»; chi pubblica cita «Informação geográfica cedida pela Direção-Geral do Território» (record SNIG `b2a1ca02-…`, letto da me); i file sono a contratto Airbus: solo visualizzazione e cache [I] | Lisbona, Praça do Comércio: 200, 12-15 KB |
| Paesi Bassi, PDOK (`nl-pdok`, 8 cm) | XYZ `https://service.pdok.nl/hwh/luchtfotorgb/wmts/v1_0/Actueel_orthoHR/EPSG:3857/{z:02d}/{x}/{y}.jpeg` | CC BY 4.0, «Naamsvermelding verplicht, Beeldmateriaal.nl»; aziende e privati senza registrazione | Amsterdam, Dam: 200, 22-26 KB |
| Fiandre (`be-vlaanderen`, 15 cm, anche Bruxelles) | WMTS `https://geo.api.vlaanderen.be/OMWRGBMRVL/wmts` (percorso in maiuscolo), PNG | Modellicentie gratis hergebruik: «Bron: Luchtopnamen Digitaal Vlaanderen» | Anversa, Grote Markt: 200, PNG 80-86 KB |
| Vallonia (`be-wallonie`, 25 cm) | WMS `https://geoservices.wallonie.be/arcgis/services/IMAGERIE/ORTHO_LAST/MapServer/WMSServer` | CC BY 4.0; condizioni dei servizi SPW 03/08/2016: niente uso sproporzionato, menzioni mai nascoste | Liegi, Place du Marché: 200, 23-28 KB |
| Bruxelles, UrbIS (`be-bruxelles`, 2024) | WMTS `https://geoservices-grid.irisnet.be/geowebcache/service/wmts`, `EPSG:900913` | CC0 | Grand-Place: 200, 19 KB |
| Lussemburgo (`lu-act`, 2025) | XYZ `https://wmts1.geoportail.lu/opendata/wmts/ortho_latest/GLOBAL_WEBMERCATOR_4_V3/{z:02d}/{x}/{y}.jpeg` | CC0 | Place Guillaume II: 200, 26 KB |
| Svizzera, SWISSIMAGE (`ch-swisstopo`, 10-25 cm) | XYZ `https://wmts.geo.admin.ch/1.0.0/ch.swisstopo.swissimage/default/current/3857/{z}/{x}/{y}.jpeg` | dati liberi swisstopo, uso commerciale ammesso, «© swisstopo» (`…/terms-of-use-free-geodata-and-geoservices`); FSDI: senza registrazione, le applicazioni desktop sono fair use (1.200 richieste al minuto). Il contrasto del 2021 su opendata.swiss è risolto (oggi `terms_by`). Fuori dalla Svizzera il livello mostra SPOT 5 di Airbus: l'area è la sola Svizzera | Berna, Bundesplatz: 200, 20 KB |
| Austria, basemap.at (`at-basemap`, 29 cm, 15 cm in parte) | XYZ `https://mapsneu.wien.gv.at/basemap/bmaporthofoto30cm/normal/google3857/{z}/{y}/{x}.jpeg` | CC BY 4.0, «Datenquelle: basemap.at», anche commerciale, senza registrazione | Vienna, Stephansplatz: 200, 15-16 KB |
| Cechia, ČÚZK (`cz-cuzk`, 12,5 cm) | XYZ `https://ags.cuzk.gov.cz/arcgis1/rest/services/ORTOFOTO_WM/MapServer/WMTS/tile/1.0.0/ORTOFOTO_WM/default/default028mm/{z}/{y}/{x}` | dati CC BY 4.0; servizi aperti anche commerciali; a video «ČÚZK – on-line», in stampa «ČÚZK, anno» | Praga, Staroměstské náměstí: 200, 25-29 KB |
| Polonia, Geoportal (`pl-gugik`, 25 cm, città 10 cm) | WMTS `https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMTS/StandardResolution`, `EPSG:3857:{z}` | gratuita «per qualsiasi uso», anche da altri programmi; vietato il prelievo massivo | Varsavia, Plac Zamkowy: 200, 7 KB. **Il WMS ha risposto 404 a 6 richieste su 8** (con o senza stile): usato il WMTS, che GUGiK dice un po' più morbido agli zoom alti |
| Slovenia, GURS DOF025 (`si-gurs`, 25 cm) | WMS `https://ipi.eprostor.gov.si/wms-si-gurs-dts/wms` | CC BY 4.0, citazione con tipo di dato e data | Lubiana, Prešernov trg: 200, 15 KB |

### Germania (13 Länder aperti)

Licenze: dl-de/zero-2-0, dl-de/by-2-0 o CC BY 4.0, lette sulle pagine dei Länder; attribuzioni esatte nel codice.
Tutti WMS in EPSG:3857 salvo Baviera (XYZ) e Renania Settentrionale-Vestfalia (WMTS con le matrici da «00» allo zoom
5); prova: due tasselli 200 JPEG ciascuno, 12-31 KB, alla piazza del mercato della capitale [V].

| Land | Licenza | Nota |
|---|---|---|
| Renania Settentrionale-Vestfalia (`de-nw`) | dl-de/zero-2-0 | WMTS `EPSG_3857_16`, fino allo zoom 21 |
| Baviera (`de-by`) | CC BY 4.0 | WMTS di Bayernwolke; a scala piccola Sentinel-2 del BKG, nell'attribuzione |
| Assia (`de-he`) | § 18 HVGG, uso libero | |
| Sassonia (`de-sn`) | dl-de/by-2-0 | |
| Berlino (`de-be`) | dl-de/zero-2-0 | TrueDOP20 2025: l'anno è nell'indirizzo, da aggiornare |
| Brandeburgo (`de-bb`, anche Berlino) | dl-de/by-2-0 | AGNB n. 8: vietata la cache «automatica e ciclica» senza accordo; la cache dei tasselli guardati non lo è [I] |
| Amburgo (`de-hh`) | dl-de/by-2-0 | sempre `TIME=2024`: il 2022 è da satellite Airbus, licenza chiusa |
| Schleswig-Holstein (`de-sh`) | CC BY 4.0 | |
| Renania-Palatinato (`de-rp`) | dl-de/by-2-0 | |
| Turingia (`de-th`) | CC BY 4.0 | |
| Meclemburgo-Pomerania Anteriore (`de-mv`) | CC BY 4.0 | il WMS, non il WMTS (le sue capabilities hanno ancora un vecchio testo restrittivo) |
| Saarland (`de-sl`) | dl-de/by-2-0 | «freewms» aperto [I]; l'anno nell'indirizzo |
| Brema (`de-hb`, 10 cm) | CC BY 4.0 | l'anno nei nomi dei livelli |
| Germania, mappa basemap.de (`de-basemap`) | CC BY 4.0 | una mappa, non una foto |

### Mondo e mappe

| Sorgente | Licenza | Prova |
|---|---|---|
| Stati Uniti, USGS Imagery Only (`us-usgs`, NAIP 1 m) | pubblico dominio (`https://www.usgs.gov/faqs/what-are-terms-uselicensing-map-services-and-data-national-map`); zoom massimo 16 | New York, Washington Square: 200, 30-31 KB |
| Mondo, Sentinel-2 cloudless 2016 di EOX (`eox-2016`, 10 m) | **solo il 2016 è CC BY 4.0**; «Commercial apps may access the free 2016 endpoint under CC BY 4.0, provided traffic is reasonable»; gli anni 2018-2025 sono CC BY-NC-SA e vietati alle app commerciali (`https://cloudless.eox.at/documentation/faq`). Zoom 14 e poi ingrandito | Buenos Aires, Plaza de Mayo: 200, 6-14 KB |
| OpenStreetMap (`osm`) | ODbL; politica dei tasselli riletta (User-Agent proprio, cache, niente prelievo, niente uso offline) | Siena: 200, PNG 16-19 KB |
| OpenTopoMap (`opentopomap`) | CC-BY-SA 3.0; un server volontario ridotto dal 05/01/2026: uso leggero | Siena: 200, PNG 29 KB |

## 3. Lasciate fuori, e perché

- **Esri World Imagery**: senza account e token non è ammessa («If you do not have Esri software, you must purchase an
  ArcGIS Online subscription»; vietato raccogliere i tasselli e conservarli; clausole contro la combinazione con
  software GPL nel Master Agreement e nel Location Platform Agreement). Si può aggiungere come sorgente propria con la
  chiave di Daniel, sotto quei termini.
- **Google Maps** e **Bing / Azure Maps**: account e chiave obbligatori; Google vieta cache e prelievo; Bing per i
  conti gratuiti è chiuso e vieta gli indirizzi scritti a mano.
- **EOX Sentinel-2 2018-2025**: CC BY-NC-SA, vietati alle app commerciali (licenza a pagamento da 5.000 EUR l'anno).
  Il livello 2017 compare nelle capabilities come CC BY 4.0 ma le pagine non lo nominano: da chiedere a EOX.
- **Danimarca** (token, 403), **Norvegia** (riservata ai partner), **Svezia** (401, account Geotorget),
  **Finlandia** (chiave, solo fino allo zoom 16), **Regno Unito** e **Irlanda** (nessuna foto aerea nazionale aperta),
  **Liechtenstein** (il suo WMS è solo non commerciale; coperto in parte da swisstopo, licenza non confermata).
- **DOP20 nazionale del BKG**: solo per le amministrazioni.
- **Baden-Württemberg, Bassa Sassonia, Sassonia-Anhalt**: licenza aperta, ma il servizio non ha risposto nella notte
  del 25/10/2026 (errore del server, manutenzione, errore 500): da riprovare di giorno.
- **Emilia-Romagna 2022**: licenza non verificata. **Lombardia, Piemonte, Veneto** (AGEA): non ricaricabili (studio 18 F).
- **Portogallo Ortos2018**: solo PNG a palette via WMS 1.1.1.

## 4. Come è stato verificato

- Prove vere con `tools/try_map_sources.py` (sopra); le schermate sono in
  `%TEMP%\meridiana\per-daniel\mappe`.
- Test senza rete: `tests/nucleo/test_tiles.py` (indirizzi di ogni tipo, copertura e scelta su 18 luoghi di confine,
  coste e isole, sorgenti del progettista e loro errori), `tests/nucleo/test_capabilities.py` (capabilities vere
  registrate in `tests/data/mappe`: PDOK, NRW, swisstopo, IGN, Vallonia, Baviera 1.1.1, un errore),
  `tests/widget/test_tile_loader.py` (un server finto su 127.0.0.1: User-Agent, chiave solo nell'indirizzo e mascherata
  nei messaggi, cartella della cache propria, interruttore spento), `tests/widget/test_map_sources.py` (la pagina),
  `tests/finestra/test_background.py` (menu, cambio di sito, sorgente aggiunta nelle Preferenze e salvata),
  `tests/formati` (versione 19).

## 5. Cosa resta

- Il **catasto** dell'Agenzia delle Entrate come sovrapposizione trasparente (CC BY 4.0, ma senza EPSG:3857 né 4326:
  serve una riproiezione da EPSG:25832) ○.
- Riprovare Baden-Württemberg, Bassa Sassonia e Sassonia-Anhalt e aggiungerle se rispondono ○.
- I confini di Natural Earth sono precisi a qualche centinaio di metri: il centro di Gorizia cade in Slovenia, e lì
  l'automatico propone l'ortofoto slovena (il menu offre anche quella del FVG) ○.
- Il pulsante «Ricontrolla i termini» dello studio (rileggere Fees e AccessConstraints e avvisare se cambiano) ○.
- La relazione non disegna ancora lo sfondo: quando lo farà, la didascalia porterà l'attribuzione della sorgente ○.
- Gli indirizzi con l'anno (Berlino 2025, Saarland 2025, Brema 2025, Amburgo 2024) vanno aggiornati con i voli nuovi.

## 6. Da provare sul PC di Daniel

1. Un progetto a Rho: Sfondo > «Automatico: Italia: ortofoto 2012»; un progetto a Siena, Bolzano, Trento o Trieste:
   l'ortofoto della regione; l'attribuzione in basso a destra.
2. Trova il sito su Parigi, Berna o Amsterdam (progetto nuovo): l'automatico passa alla sorgente del paese.
3. Preferenze > Mappe: le righe con i suggerimenti, la scelta di partenza; aggiungere una sorgente propria (per
   esempio un WMS regionale dalle capabilities, o un XYZ con `{key}` e la chiave nel portachiavi), sceglierla nel
   menu Sfondo; Privacy con le mappe spente: niente richieste.
4. Le schermate a 2,5x sul secondo schermo e la lettura delle righe.
