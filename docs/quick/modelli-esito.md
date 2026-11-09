# Modelli liberi per la vista Quick: esito R374 e R376

04/11/2026. [V] Preparati 26 originali CC0, da cui 34 mesh statiche complete:
31 attive e 3 in attesa di scelta. Nessuna riduzione QEM. Il Casual conserva
5.776 triangoli in entrambe le pose. Il codice dei Widgets e il calcolo delle
ombre non sono stati modificati.

## Scelta e licenze

[V] Le fonti del censimento R11 sono state riusate come originali, verificando
gli hash SHA256. Tutte le schede Poly Pizza sono state rilette e confrontate con
il campo `Licence` della singola risorsa; ogni risorsa scelta dichiara CC0 1.0.
Worker, due donne modulari, Business Man e Hoodie sono stati scaricati dai
collegamenti pubblici delle loro schede, senza eseguire i file.

[V] `data/models/licenses/` conserva una scheda per ciascun originale con autore,
licenza, URL, data e hash della pagina. Per Poly Haven sono presenti anche i
metadati API del singolo asset. Il testo CC0 è in `data/models/CC0-1.0.txt`.
`data/models/catalog.json` fornisce alla pagina Informazioni questi dati insieme
all'hash originale, all'hash distribuito, al numero di triangoli e alla posa.

[V] Due aggiunte dal pacchetto Ultimate Modular Women hanno licenza individuale
CC0: [donna con abito](https://poly.pizza/m/nIItLV9nxS) e
[donna casual](https://poly.pizza/m/qJ2gsTUBHL). Lo stesso pacchetto contiene
cinque personaggi CC-BY: non sono stati inclusi, neppure la lavoratrice.
Gli uomini modulari aggiuntivi sono
[Worker](https://poly.pizza/m/Yg2bQZO6Hj),
[Business Man](https://poly.pizza/m/JFrLIKqvCH) e
[Hoodie](https://poly.pizza/m/gKLBoRsyKe), tutti CC0 sulle rispettive schede.

[V] Roof Antenna, Water Tank, Propane Tank, Shipping Container di Davidlamic000,
Utility Box 01, Transmission Tower di iPoly3D, Street Light, Streetlight,
Car, Sports Car, SUV, Truck, Pickup Truck, Silo e Fence sono attivi.
Street Lamp 01 di Poly Haven e le biciclette Drummyfish/Innerscene sono in
`staged/`, con `active=false`: non è stata anticipata la scelta estetica.
Power Lines di Chase W. e Bicycle di Google non compaiono negli originali
distribuiti né nel catalogo.

## Pose e scala

| Persona | Triangoli per posa | In piedi | Cammino |
|---|---:|---|---|
| Casual Character | 5.776 | Idle_Neutral, 0 s | Walk, 0,2 s |
| Worker | 5.240 | Idle_Neutral, 0 s | Walk, 0,2 s |
| Donna modulare con abito | 6.108 | Idle_Neutral, 0 s | Walk, 0,2 s |
| Donna modulare casual | 6.424 | Idle_Neutral, 0 s | Walk, 0,2 s |
| Business Man | 6.634 | Idle_Neutral, 0 s | Walk, 0,2 s |
| Hoodie | 6.206 | Idle_Neutral, 0 s | Walk, 0,2 s |
| Man precedente | 1.852 | Man_Idle, 0 s | Man_Walk, 0,2 s |
| Woman Casual precedente | 2.776 | Female_Idle, 0 s | Female_Walk, 0,2 s |

[V] La verifica delle immagini ha trovato che Man_Standing e Female_Standing
iniziano seduti: sono clip che si alzano dalla sedia. Per questi due confronti
precedenti si usa Idle, verificata in piedi. Una prova geometrica ora impedisce
che il riferimento seduto ingrandisca la successiva posa in cammino.

[V] Ogni coppia usa la stessa scala, derivata dall'altezza in piedi. Tutte le
pose hanno uno spostamento massimo dalla mesh senza skin maggiore di 0,5 unità
native. Non sono copie della posa iniziale. Le normali applicano l'inversa
trasposta anche nelle trasformazioni pesate dello scheletro; una prova sintetica
con scala non uniforme verifica il risultato atteso.

## API e prestazioni

[V] `scene_assets.load_model(key)` restituisce posizione N×3, normale N×3 e colore
RGBA N×4, tutti numpy float32 non scrivibili. La cache restituisce gli stessi
array per le istanze successive. `catalog(active_only=True)` filtra le scelte
attive; `catalog()` include anche i tre elementi in attesa e i crediti.
I dati sono caricati senza Qt, immagini, rete o scheletro.

[V] L'asse verticale è Y, la base è zero e X/Z sono centrati. L'altezza è 1,
salvo il cammino che conserva la scala della posa in piedi. Gli oggetti
mantengono le proporzioni native. L'instancing GPU e la scala per gli ingombri
sono gestiti dalla scena Quick, non dal lettore.

[V] Le 34 mesh contengono 164.469 triangoli complessivi. I file NPZ occupano
circa 3,84 MB decimali. Il caricamento non espande materiali PBR: le texture
base-colour sono già campionate nei colori dei vertici. Metallicità, rugosità,
normal map e trasparenza non vengono conservate. Il container conserva sagoma
e colore; le scritte delle texture non hanno una riproduzione fedele ai vertici.

## Verifiche

[V] Nove prove in `tests/quick/vista3d/test_assets.py`: triangoli esatti,
pose diverse e scala condivisa, normali unitarie, limiti e valori finiti,
hash e licenze, esclusioni e attese, cache, round trip OBJ/NPZ, trasformazione
normali dello skin, rifiuto di materiali fuori cartella e di licenze non CC0.
Il bake completo offline è stato ripetuto in `build/models-repro-r03/`: tutti
i 34 hash e l'intero catalogo coincidono con i file distribuiti. Ruff F/E9/B
passa sui cinque strumenti, sul loader e sulle prove.

[V] L'anteprima software è prodotta dalle mesh effettivamente distribuite da
`tools/models_preview.py`, con colori per vertice, luce diffusa e profondità.
Le immagini sono in `build/models-preview-r02/`. Il foglio `catalog.png`
permette il confronto delle sagome; i singoli PNG mostrano ogni posa.
[V] Controllati visivamente tutti i 34 PNG individuali: pose, braccia, gambe,
sagoma degli oggetti, portello dell'Utility Box, traverse del traliccio e ruote.
Street Lamp 01 resta molto scuro, come nella prova R11, ed è ancora non attivo.
Non è un benchmark della GPU e non sostituisce le foto della scena Quick.

### Separazione dal calcolo energetico e riuso delle geometrie

[V] Due ulteriori prove in `tests/quick/vista3d/test_decorative_energy.py`,
eseguite con `QT_QPA_PLATFORM=offscreen`, passano in 43,398 s sulla macchina
condivisa. Usano una QApplication senza aprire superfici grafiche.

[V] La prova energetica usa la fixture del capannone, un campo ridotto a
7 moduli coplanari, un inverter e stringhe automatiche. Un serbatoio e un'antenna
sul tetto producono ombreggiamento non nullo; un'auto e una persona sono a terra.
Il meteo sintetico copre 8.760 ore e la produzione è verificata positiva.
Il primo tentativo con il tetto pieno è stato interrotto per costo eccessivo:
non se ne riporta un esito. Il campo ridotto verifica gli stessi invarianti.

[V] Dopo aver caricato tutto il catalogo, la prova disabilita i modelli
decorativi, li riabilita e applica override verso Utility Box, Transmission
Tower, Truck e una donna modulare in cammino. Il secondo `pipeline.compute`,
senza rete, restituisce gli stessi valori orari e mensili, senza tolleranza,
lo stesso totale annuale, potenze nominali, PR e dati di ogni campo. Gli array
di `props.shadow_solid` e `energy.system.prop_solids` restano identici.
Anche snapshot del progetto, chiave energetica e cronologia annullamenti
restano invariati.

[V] La seconda prova dispone 200 auto e 200 persone. La scena contiene due
oggetti `SceneGeometry` decorativi e due tabelle native da 200 istanze. Con la
condivisione indicizzata dei vertici identici, i buffer contengono 705.520 byte
di vertici e 106.800 byte di indici: 812.320 byte complessivi, contro 1.068.000
byte della precedente lista di triangoli. Il confronto esatto ricostruisce dai
buffer indicizzati ogni triangolo, normale e colore originali: Casual conserva
tutti i 5.776 triangoli. Si verificano due soli cache miss del lettore e gli
stessi oggetti geometrici dopo il secondo rebuild, senza nuovi caricamenti.
Questa è una verifica degli oggetti e dei buffer preparati per Quick 3D, non una
misura dell'allocazione o del tempo della GPU. Ruff F/E9/B passa anche sul nuovo
file di prove. Nessun difetto del backend è emerso in queste due prove.

### Catture native Direct3D 11

[V] Eseguiti quattro processi separati e sequenziali di
`tools/models_scene_benchmark.py`, dopo aver ricevuto la disponibilità della
GPU. Impostazioni: piattaforma `windows`, `QSG_RENDER_LOOP=threaded`,
`QT_SCALE_FACTOR=1` oppure `2`. Tutti i processi sono terminati con codice 0;
ogni `scene.json` riporta Direct3D 11, la scala richiesta e nessun warning QML.
[V] Le due catture a scala 2 sono state poi ripetute in altri due processi,
ancora sequenziali e terminati con codice 0, dopo la correzione del vincolo
minimo della finestra. La tabella identifica le otto immagini definitive.

| Cartella in `build/quick-foto/r12-vista3d/` | Contenuto | Tema e scala | Pixel effettivi per immagine |
|---|---|---|---|
| `gallery-s1-light` | 15 oggetti attivi | chiaro, 1 | 1600 × 960 |
| `humans-s1-light` | 16 pose di otto persone | chiaro, 1 | 1600 × 960 |
| `gallery-s2-dark-exact` | 15 oggetti attivi | scuro, 2 | 3200 × 1920 |
| `humans-s2-dark-exact` | 16 pose di otto persone | scuro, 2 | 3200 × 1920 |

[V] Controllate singolarmente tutte le otto immagini definitive `far.png` e
`near.png`, oltre alle quattro precedenti a scala 2 conservate per tracciabilità.
Le viste lontane contengono tutti gli oggetti previsti dal loro `scene.json`.
Le viste ravvicinate mostrano correttamente portelli, corrugazioni del container,
traliccio, lampioni, ruote, vestiti, caschi e le pose alternate degli arti.
Non emergono parti mancanti, pose iniziali non applicate o deformazioni dovute
alla condivisione indicizzata. I colori per vertice e le ombre della scena sono
presenti in entrambe le combinazioni di tema e scala.

[V] Il maggiore ingrandimento di `near.png` taglia intenzionalmente gli oggetti
periferici: nella galleria il pickup e l'auto esterna, nelle persone parte
dell'uomo in basso a sinistra a scala 2. Il confronto completo usa `far.png`.
L'antenna piccola resta poco leggibile nella vista di insieme per la sua altezza
illustrativa di 1,2 m; non è una geometria assente. Le proporzioni native della
fixture non hanno richiesto correzioni.

[V] Le prime cartelle `gallery-s2-dark` e `humans-s2-dark` contengono foto da
3004 × 1902 pixel, con finestra effettiva 1502 × 951 logici. Sono superate dalle
cartelle con suffisso `-exact`: il benchmark ora imposta il minimo 1600 × 960
prima di mostrare la finestra e verifica le dimensioni della cattura. Tutti e
quattro i nuovi PNG sono stati riletti e misurano esattamente 3200 × 1920 pixel,
con scala 2 dichiarata da Qt e nessun warning. Non sono immagini ridimensionate
dopo la cattura. Sagome, pose, colori e ombre restano corretti nelle nuove foto.

[V] Le tre alternative non attive restano fuori da queste gallerie native;
sono state controllate nelle immagini software precedenti. Le otto catture
verificano la resa sul backend nativo, non misurano FPS o latenza percepita
sul monitor fisico di Daniel.

[I] Le altezze `default_height_m` sono misure illustrative per anteprime, non
quote del produttore. Il progetto continua a stabilire gli ingombri. Per
l'integrazione nel selettore e le misure dei tempi con molti oggetti fa fede
il rapporto principale `docs/quick/stato/r12-vista3d.md`.
