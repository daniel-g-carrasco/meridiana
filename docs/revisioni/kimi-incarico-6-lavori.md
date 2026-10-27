# Incarico 6: lavori e verifiche

26/10/2026. R131, R149 e R173. Quattro commit funzionali, nell'ordine chiesto. Nessuna tessera è stata scaricata dai
server pubblici: le prove usano un server HTTP locale o immagini generate.

## Punto 1: ripiego visibile

Commit `cfa4f41`, «Keep the plan covered and show temporary map fallbacks (R131, point 1)».

- `TileLoader.tileFailed` arriva ora alla pianta. Tre tessere distinte fallite dopo i tentativi fanno riposare la fonte
  per 180 secondi. Nella vista di prova da 800 x 600, circa 15 tessere, la soglia misura il 20 % e impedisce sia il
  mosaico intermittente sia le richieste ripetute a ogni movimento. [V]
- Il ripiego sceglie un'altra foto per lo stesso sito, poi lo stradale. Sentinel-2 è ammesso solo lontano. Il mosaico
  precedente resta finché quello nuovo non copre la vista, così non ci sono lampi né mescolanze silenti. [V]
- La striscia dice la fonte guasta e quella in uso, con «Riprova» e «Scegli lo sfondo». Il comando apre il menu vero.
  `PlanView.choice`, e quindi la preferenza salvata, non cambia durante un guasto. [V]
- Rosso prima: tre prove fallivano perché mancavano `tiles.fallbacks`, `FAILOVER_COOLDOWN` e la conservazione delle
  tessere. Verde dopo: errori 503 su metà delle richieste, XML con stato 200 al posto dell'immagine, ripiego, pausa,
  nuovo tentativo e attribuzione. [V: `tests/widget/test_plan_background.py`]
- Fotografie: `foto/kimi6-ripiego-prima.png`, vuota e senza avviso sul commit iniziale;
  `foto/kimi6-ripiego-dopo.png`, coperta e con avviso. [V: immagini lette]

## Punto 2: due predefiniti

Commit `eb3d224`, «Switch Automatic between street maps and orthophotos (R149, point 2)».

- «Automatica» usa OpenStreetMap oltre 2 m/pixel dello schermo e la migliore ortofoto del sito da 2 m/pixel in giù.
  La soglia è geometrica e misurata sul compito: un tetto di 40 m occupa 20 pixel, sotto questa scala la foto serve al
  disegno. [V: scelta per metri per pixel nella prova]
- Una fonte scelta a mano non cambia con lo zoom. Le fonti personali non entrano da sole nell'automatico. Il passaggio
  conserva il mosaico precedente e l'attribuzione mostra sempre ciò che si vede. [V]
- Rosso prima: `tiles.automatic` non esisteva. Verde dopo: lontano OSM, vicino PCN nella fonte finta, ritorno, scelta
  manuale e attribuzioni. [V: `tests/widget/test_plan_background.py`]

## Punto 3: la pianta fino ai continenti

Commit `9d2e33f`, «Zoom the local plan out to the continents (R173, point 3)».

- La scala minima è 0,00004 px/m, cioè 25.000 m/pixel; la scena misura 40.000 km. Il piano resta `geo.Origin` e non
  disegna punti oltre 80° dal sito. La bussola resta legata alla rotazione e la scala scrive i km. [V]
- Le tessere z0-z6 sono spezzate fino a 8 x 8 celle. I punti globali dei bordi sono calcolati nello stesso modo, quindi
  le celle di due tessere vicine coincidono esattamente. [V: prova geometrica in `tests/nucleo/test_tiles.py`]
- Il progetto lontano resta un punto magenta di 14 pixel. Il tour tetto-Europa-tetto torna a 0,1 m/pixel. [V]
- Misura a 1600 x 1000, 50 ridisegni con immagini generate: prima 39 tessere e 4,878 ms, dopo 12 tessere e 1,811 ms per
  ridisegno, z4. Il tour della finestra arriva a 25.000 m/pixel con 4 tessere e scala 2.000 km. [V]
- Rosso prima: mancavano mesh, emisfero e segno del sito. Verde dopo: continuità, antipodo escluso, Europa nel limite di
  400 tessere, scala, bussola e ritorno. [V: `tests/nucleo/test_tiles.py`, `tests/widget/test_plan_aids.py`]

## Punto 4: mondo con stati, offline

Commit `d0f07ff`, «Draw the Natural Earth world offline (R149, point 4)».

- Scelto Natural Earth 1:110m, non 1:50m: serve ai continenti, non al disegno tecnico, e il GeoJSON compresso pesa
  209.310 byte, circa 204 KiB. Contiene 177 stati, nessun nome di clienti o persone di Meridiana. [V]
- Fonte e condizioni rilette il 26/10/2026: pubblico dominio, uso commerciale e redistribuzione consentiti. Indirizzi e
  data sono in `data/natural_earth/LICENSE.txt`. Flatpak e Windows includono il dato. [V:
  https://www.naturalearthdata.com/about/terms-of-use/]
- Meridiana disegna oceano, riempimenti sobri, confini, nomi italiani senza sovrapposizioni e graticola. Il livello sta
  sotto le tessere, oppure è da solo senza rete o con sfondo «Nessuno». [V: `src/meridiana/ui/world_map.py`]
- Roma, Parigi, Il Cairo e Londra cadono negli stati attesi. Il peso è verificato nella prova. [V:
  `tests/nucleo/test_worldmap.py`]
- Fotografia: `foto/kimi6-mondo-offline.png`, letta dopo il disegno. [V]

## Prova del programma e fotografie

Il tour usa `capannone()` e la `MainWindow`, non soltanto il widget. Tessere generate dentro il processo, rete mappe
spenta, eventi di rotella sul viewport, QTest per clic e tasti. PySide6 6.12 non espone `QTest.wheel`, quindi la rotella
è un `QWheelEvent` reale. Esito: PCN al tetto, OSM lontano, Natural Earth visibile, 25.000 m/pixel, 4 tessere, ritorno
a PCN e 0,1 m/pixel, ripiego OSM, «Riprova» su PCN e menu sfondo aperto. [V: `/tmp/kimi6-real/risultato.json` durante
la prova]

Fotografie lette: `kimi6-reale-tetto-chiaro.png`, `kimi6-reale-mondo-chiaro.png`,
`kimi6-reale-mondo-scuro.png`, `kimi6-reale-tetto-scuro.png`, `kimi6-reale-ripiego.png` e
`kimi6-reale-scegli-sfondo.png`. Hanno portato a due correzioni: «Nessuno» cancella il vecchio mosaico e la striscia
sta sotto la barra degli strumenti, con testo a capo. [V]

La sessione Wayland nascosta non è arrivata alla finestra. GNOME Shell è partito con monitor virtuale e GPU AMD, ma il
portale GTK è andato in timeout; anche una `QApplication` vuota restava bloccata prima della sua creazione, sia con il
bus ereditato sia con `dbus-run-session` e tema generico. I processi sono stati chiusi. Il tour completato è quindi
offscreen, non una prova Wayland riuscita. [V: log di GNOME e riproduzione con applicazione vuota]

## Suite e controlli

Suite finale dopo le correzioni delle fotografie: 794 nucleo, 175 calcoli, 59 formati, 317 widget, 132 finestra;
1.477 prove verdi, 5 saltate. Esterni: 6 saltate perché non richieste né abilitate. Ruff, `msgfmt --check`, catalogo
compilato e `git diff --check` verdi. Interprete verificato: `meridiana` caricato da `src` di questo checkout. [V]

## Da provare sullo schermo di Daniel

1. A Rho, con PCN che fallisce: il disegno resta coperto, leggere la striscia, provare «Riprova» e «Scegli lo sfondo».
2. In «Automatica», rotella dal tetto all'Europa e ritorno: OSM lontano, foto vicino, nessun lampo e attribuzione giusta.
3. Con rete spenta e poi con «Nessuno», il mondo Natural Earth, i nomi e il punto del sito; tornare al dettaglio.
4. Provare la sessione grafica reale sul portatile, qui bloccata dal portale GTK della sessione nascosta.

## Non fatto

- Nessuna richiesta ai server cartografici veri, per rispettare le regole d'uso. Il comportamento di rete è provato con
  il server locale; il PCN reale resta da provare sullo schermo di Daniel.
- Nessuna ortofoto 2006 aggiunta: non era necessaria al ripiego richiesto e non ne è stata verificata una nuova licenza.
- Nessun dato 1:50m incluso: la scala 1:110m basta ai continenti e mantiene il pacchetto a circa 204 KiB.
