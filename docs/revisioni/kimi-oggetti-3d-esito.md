# Oggetti 3D procedurali, esito del 30/10/2026

## Che cosa ho fatto

[V] Ho creato `src/meridiana/props.py`, senza Qt e con la sola dipendenza numerica da numpy. Le funzioni pubbliche sono:

- `tree(kind, height, crown_diameter, trunk_height, length, rotation, colours)` per latifoglia, conifera, arbusto,
  siepe e palma;
- `obstacle(kind, width, depth, height, rotation, colours)` per camino, sfiato, lucernario piano e a cupola,
  macchina, antenna, parabola, serbatoio, vano scala, locale ascensore, passerella, apertura e ostacolo generico;
- `person(kind, width, depth, height, rotation, colours)` per adulto fermo, adulto che cammina, bambino e operaio;
- `car(kind, length, width, height, rotation, colours)` per utilitaria e SUV;
- `shadow_solid(kind, rotation, **dimensions)` per i volumi d'ombra semplificati.

Le mesh restituiscono posizioni, normali e colori come tre array `float32` di forma N x 3. Gli assi sono quelli di
`mesh.py`: x Est, y verticale, z Sud. Le misure sono in metri e l'origine è al centro del piede dell'oggetto. La
rotazione è antioraria nella pianta del modello. I colori si possono sostituire con tuple 0-1 o stringhe `#rrggbb`.

Le forme d'ombra sono liste di array di vertici in coordinate del modello, x Est, y Nord, z verticale. Sono pronte per
essere passate a `nearshade.Solid`, dopo la traslazione nel punto del progetto. Non usano la mesh decorativa.

[V] Non ho modificato file esistenti. La vista, la pianta, il modello, le ombre e le traduzioni restano fuori da
questo incarico.

## Triangoli per oggetto

I valori sono quelli delle chiamate predefinite e non cambiano con le misure. I budget sono costanti pubbliche in
`props.py`: 400 per albero, 200 per ostacolo, 300 per persona e 300 per auto.

| Gruppo | Tipo | Triangoli | Budget |
|---|---|---:|---:|
| Albero | `broadleaf` | 104 | 400 |
| Albero | `conifer` | 104 | 400 |
| Albero | `shrub` | 104 | 400 |
| Albero | `hedge` | 64 | 400 |
| Albero | `palm` | 120 | 400 |
| Ostacolo | `chimney` | 24 | 200 |
| Ostacolo | `vent` | 64 | 200 |
| Ostacolo | `skylight` | 24 | 200 |
| Ostacolo | `dome_skylight` | 60 | 200 |
| Ostacolo | `plant` | 56 | 200 |
| Ostacolo | `antenna` | 108 | 200 |
| Ostacolo | `dish` | 156 | 200 |
| Ostacolo | `tank` | 80 | 200 |
| Ostacolo | `stairwell` | 36 | 200 |
| Ostacolo | `elevator` | 36 | 200 |
| Ostacolo | `walkway` | 156 | 200 |
| Ostacolo | `opening` | 12 | 200 |
| Ostacolo | `other` | 12 | 200 |
| Persona | `adult` | 264 | 300 |
| Persona | `walking` | 264 | 300 |
| Persona | `child` | 264 | 300 |
| Persona | `worker` | 296 | 300 |
| Auto | `compact` | 228 | 300 |
| Auto | `suv` | 228 | 300 |

## Prove

[V] `tests/nucleo/test_props.py` contiene 24 prove. Per ogni tipo usa almeno due insiemi di misure e controlla:

- ingombro esterno uguale a quello richiesto, con tolleranza di 0,00002 m;
- array `float32`, valori finiti, normali unitarie e concordi con l'orientamento dei triangoli;
- assenza di triangoli degeneri e volume positivo di ogni componente solida, quindi normali rivolte all'esterno;
- rispetto del budget, risultato identico a ogni chiamata, rotazione e colori personalizzati;
- volumi d'ombra contenuti nell'ingombro decorativo;
- misure non valide rifiutate;
- appartenenza di ogni colore generato alla tavolozza dichiarata, in chiaro e in scuro, per tutti gli oggetti ruotati;
- presenza degli oggetti nelle due scene e ordine corretto delle dodici catture.

[V] Il comando mirato `python -m unittest nucleo.test_mesh nucleo.test_props` ha superato 47 prove, comprese quelle
preesistenti delle mesh. Una generazione di 500 latifoglie ha prodotto 52.000 triangoli in 2,10 s durante la suite,
circa 4,21 ms per albero, senza Qt.

[V] La galleria è stata aperta solo con `tools/real_session.sh`. Ha prodotto dodici immagini a 1600 x 962: due
scene, due temi e tre punti di vista. Le ho guardate tutte. Ho corretto l'ordine scena/tema nella coda, ravvicinato
la galleria e spostato persone, palma e auto per evitare occlusioni nella scena realistica. Alla fine di ogni prova
`findmnt /run/user/1000/doc` ha confermato che il montaggio del portale documenti era ancora presente.

[V] Le foto sono in `docs/revisioni/foto/oggetti-3d/`:

- `galleria-{chiaro,scuro}-{assonometrica,fronte,alto}.png`: tutti gli oggetti, griglia di 1 m, muro di 2 m e
  modulo verticale di 1,13 x 2,28 m;
- `realistica-{chiaro,scuro}-{assonometrica,fronte,alto}.png`: capannone con 20 moduli, pensilina con 6 moduli e
  due auto, alberi e quattro persone sul piazzale.

[V] Ruff è pulito sui tre file Python nuovi. La suite completa è descritta nella sezione finale.

## Come agganciare il modulo al programma

### Vista 3D e relazione

Il punto centrale è `mesh.project_scene` in `src/meridiana/mesh.py:466`. Oggi il ciclo di
`src/meridiana/mesh.py:484` disegna ogni esclusione con `prism_triangles`. Va sostituito, per i tipi che hanno un
modello, con il generatore di `props.py`, lasciando invariati parapetti e tipi senza modello.

Per ogni `ExclusionItem` si ricavano dal suo `ring` il centro `(cx, cy)` e le misure `width` e `depth` dagli estremi.
L'altezza è `obstacle_height()`. Per rispettare anche il caso di una falda inclinata si può usare la stessa quota di
`Project.obstacle_prisms` in `src/meridiana/model.py:1140`: base `z0 = min(roof_z(...))` e altezza geometrica
`z1 - z0`. Per un albero si usa `crown_diameter = max(width, depth)`, così la chioma copre l'ingombro dell'esclusione.

Le mesh sono locali. Dopo la chiamata si somma alle posizioni il vettore Qt `(cx, z0, -cy)`, senza cambiare normali e
colori. Il risultato entra in `parts` esattamente come oggi. In questo modo anche `ui/report_3d.py`, che usa
`mesh.project_scene`, riceve gli stessi oggetti senza una seconda implementazione.

Anche il ciclo di selezione in `src/meridiana/ui/window.py:2957` deve usare la stessa funzione di costruzione, con il
colore attenuato dell'oggetto selezionato. Conviene estrarre una sola funzione condivisa in `mesh.py` invece di
duplicare la mappatura. Gli ingombri di selezione di `viewaids.py:213` possono restare quelli del prisma originale.

### Ombre

Il punto è `obstacles_of` in `src/meridiana/energy/system.py:22`, in particolare la chiamata a
`nearshade.prism` di `src/meridiana/energy/system.py:36`. Per le esclusioni modellate si chiama
`props.shadow_solid(kind, ...)`, si trasla ogni array di `(cx, cy, z0)` e si costruisce
`nearshade.Solid(corners, name)`. Parapetti e edifici continuano a usare `nearshade.prism` e `nearshade.under`.

Le forme semplificate restano convesse e nei limiti esterni dell'oggetto. Il calcolo non eredita quindi il costo dei
triangoli decorativi. Le chiome hanno un poliedro e un prisma per il tronco; persone e auto hanno pochi prismi.

### Colori e tipi

`colours` accetta le chiavi `tree`, `trunk`, `obstacle`, `metal`, `glass`, `dark`, `person`, `skin`, `helmet`, `car`,
`tyre`, `light` e `rear`. Per il tema della scena bastano `tree = mesh.TREE` e `obstacle = mesh.OBSTACLE`; gli altri
valori predefiniti sono già in gamma 0-1.

I tipi di `model.EXCLUSION_KINDS` sono coperti direttamente, con `tree` da passare a `props.tree`. Le varianti nuove
`dome_skylight`, `antenna`, `dish`, `tank`, `stairwell` ed `elevator` sono disponibili per una futura scelta nel
modello, ma questo incarico non cambia il formato del progetto.

## Verifica finale

[V] Con il catalogo compilato, i gruppi `nucleo`, `calcoli` e `formati` hanno superato rispettivamente 948, 272 e 87
prove. Il gruppo `finestra` ha avuto un solo fallimento sotto carico nel test del dimensionamento
`PlantPhase.test_the_plant_phase_lends_the_plan_production_leads_to_it_and_its_inverters_and_inputs`.
Ripetuto da solo è passato. Le altre 182 prove del gruppo sono passate.

[V] Il gruppo `widget` ha superato tutte le 481 prove, ma il processo è terminato con un segfault nello smaltimento
di Qt. La ripetizione ha dato lo stesso esito: 481 prove verdi, poi segfault. È un problema della suite offscreen, non
una prova fallita sugli oggetti; non ho cambiato codice estraneo per inseguirlo.

[V] Ho riletto da solo tutto il diff e le prove, senza subagent. Non risultano difetti aperti nell'incarico.

## Seguito 1: tavolozza delle mesh ruotate

[V] La causa dei colori fuori tavolozza era in `_rotate_qt` di `props.py`: la matrice di rotazione veniva applicata a
posizioni, normali e anche colori. Ogni angolo mescolava quindi i canali RGB e poteva produrre valori negativi. La
galleria non passava colori sbagliati e i valori di `DEFAULT_COLOURS` erano già corretti.

[V] Prima della correzione, `galleria-chiaro-assonometrica.png` mostrava la palma giallo acido, la siepe giallo-verde,
il serbatoio ocra e la passerella gialla. Nella scena realistica la palma aveva lo stesso difetto. Dopo la correzione,
le stesse fotografie mostrano tutta la vegetazione nel verde di `mesh.TREE`, gli ostacoli nei grigi di
`mesh.OBSTACLE` e del metallo, i lucernari in azzurro-grigio e la passerella in grigio. Il casco dell'operaio resta
giallo. Ho confrontato e guardato tutte le dodici immagini nuove, chiare e scure, nei tre punti di vista.

[V] La nuova prova `Palettes.test_every_object_only_uses_colours_declared_by_the_light_or_dark_palette` genera tutti
i 24 tipi con rotazione di 37 gradi, con la tavolozza chiara predefinita e con una tavolozza scura dichiarata. Prima
falliva in tutti i 48 casi, con colori non dichiarati e anche componenti negative. Dopo la correzione passa. Il gruppo
`nucleo.test_props` supera tutte le 24 prove e Ruff è pulito sui tre file Python nuovi.

[V] Le dodici foto sono state rifatte con gli stessi nomi usando soltanto `tools/real_session.sh`. Al termine
`findmnt /run/user/1000/doc` ha confermato che il montaggio del portale documenti era ancora presente. Non sono
rimaste finestre o sessioni grafiche aperte.

[V] Nella verifica finale del seguito, Ruff su `src`, `tests` e `tools` è pulito. I gruppi `nucleo`, `calcoli` e
`formati` hanno superato rispettivamente 949, 272 e 87 prove. Il gruppo `widget` ha superato tutte le 481 prove,
poi il processo è terminato con lo stesso segfault nello smaltimento di Qt già riscontrato e documentato sopra.
Un primo tentativo del gruppo `finestra` è stato interrotto dal limite di 600 secondi senza aver riportato fallimenti.
La ripetizione verbosa, senza quel limite, ha superato tutte le 183 prove in 909,6 secondi. Anche `msgfmt --check` è
pulito; il suo artefatto `messages.mo` è stato eliminato.
