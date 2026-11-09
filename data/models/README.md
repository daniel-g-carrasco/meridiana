# Modelli statici CC0 per la vista Quick

Verifica del 04/11/2026, R374 e R376. Le geometrie sono elementi visivi di contesto;
non modificano ingombri, ostacoli o ombre del calcolo energetico.

`catalog.json` contiene tutte le 34 mesh e i dati per la pagina Informazioni:
nome originale, autore, licenza, pagina della fonte, hash del file originale,
hash del file distribuito, dipendenze originali, triangoli, posa e istante.
`sources.json` descrive i 26 originali necessari a ripetere il bake.
`licenses/` conserva la dichiarazione CC0 della singola scheda, URL, data e hash
della pagina; `CC0-1.0.txt` contiene il testo della licenza.

- `active/`: 32 mesh disponibili, comprese 16 pose di otto persone e la City
  bicycle di Innerscene (scelta da Daniel il 05/11/2026, R374).
- `staged/`: Street Lamp 01 di Poly Haven e la bicicletta di Drummyfish. Restano
  fuori dal catalogo attivo: Daniel ha scelto gli altri (05/11/2026).
- Chase W. Power Lines e Poly by Google Bicycle sono esclusi. Anche i personaggi
  CC-BY del pacchetto Ultimate Modular Women sono esclusi.

Il nome del pacchetto non basta per stabilire la licenza. Le due Animated Woman
selezionate (`nIItLV9nxS`, `qJ2gsTUBHL`) hanno schede CC0 individuali; altre donne
dello stesso pacchetto sono CC-BY. Per Quaternius si usa la concessione CC0 della
singola scheda Poly Pizza verificata oggi, non una presunzione sull'intero sito.

## Ripetere la preparazione

Dal repository, con Python, numpy e Pillow:

```text
python tools/models_fetch.py --destination build/models-originals
python tools/models_bake.py --sources build/models-originals --output build/models-baked-new
python tools/models_preview.py --models build/models-baked-new --output build/models-preview-new
```

Il primo comando scarica solo i file pubblici del manifesto e controlla gli
hash. Il secondo è completamente offline: rifiuta licenze diverse da CC0,
controlla tutti gli hash prima di decodificare e non sovrascrive un catalogo.
Gli originali sono dati non fidati, mai eseguiti. La preparazione usa i lettori
del censimento R11, portati in `tools/models_gltf.py` e `tools/models_pose.py`.

I file distribuiti sono NPZ con tre array float32: `positions` N×3, `normals`
N×3, `colours` N×4 sRGB RGBA. Sono triangoli non indicizzati, Y verticale,
base a zero e riquadro centrato in X/Z. Le normali sono unitarie. L'altezza della
posa in piedi è 1; il cammino usa lo stesso fattore della posa in piedi. La scala
di ogni istanza dipende dall'oggetto del progetto. `default_height_m` è solo una
misura illustrativa per anteprime, non una dimensione certificata dell'asset.

Non c'è riduzione dei triangoli. Materiali e texture base-colour diventano colori
per vertice. Metallicità, rugosità, normal map e trasparenza non vengono conservate:
la resa resta quella del contesto a colori per vertice, non un materiale PBR.
Il formato runtime non contiene texture, scheletri o animazioni.

Il lettore offline supporta triangoli glTF 2/GLB, trasformazioni, accessor
interleaved e normalizzati, skin a quattro pesi, clip LINEAR/STEP e OBJ triangolati.
Rifiuta gli accessor sparse e le estensioni di compressione non implementate.
Non è un importatore generale per file scelti dall'utente.
