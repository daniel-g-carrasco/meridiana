# Meridiana: documento di progetto

Stato al 20/11/2026 per la finestra, la struttura del codice, le prove e l'automazione; il resto della sezione 4 dal 09/11/2026.

App ID `io.github.daniel_g_carrasco.meridiana`. Repository `github.com/daniel-g-carrasco/meridiana`: Daniel ha deciso il 25/10/2026 di renderlo pubblico, dopo il controllo di ciò che contiene. Licenza GPL-3.0-or-later.

Legenda: **[V]** verificato con una prova o sulla fonte; **[I]** dedotto, da confermare. Le prove sono nell'appendice A.

## 0. In breve

**Cosa fa.** Progetta impianti fotovoltaici:
- trova il sito sulla mappa o sull'ortofoto;
- si ridisegnano gli edifici con i tetti e i sottocampi;
- si posano i moduli con le regole dei Vigili del Fuoco;
- calcola la producibilità oraria con tutte le perdite, come PVsyst, con PVGIS come secondo parere;
- verifica le stringhe secondo la CEI 64-8/7;
- confronta la produzione con i consumi del POD, ora per ora, anche con l'accumulo;
- fa i conti economici, CER comprese;
- produce una relazione in PDF in cui ogni numero dice da dove viene.

**Riferimenti.** PVsyst per le funzioni, Aurora per la modellazione e l'uso, PVGIS per i dati.

**Interfaccia.** Python 3.12+, Qt 6.12 con PySide6 6.12.0. La finestra è in Qt Quick (`src/meridiana/gui/`): pianta, 3D in Qt Quick 3D e grafici in QML; formule e figure della relazione con matplotlib. La vecchia finestra Qt Widgets (`ui/`) è stata tolta il 10/11/2026 (studio 43).

**Motori.** pvlib 0.16.1 (BSD-3) per i modelli fisici, shapely per la geometria della posa, PVGIS 5.3 per meteo e orizzonte.

## 1. Le decisioni prese e perché

| Data | Decisione | Perché |
|---|---|---|
| 10/11/2026 | La finestra è solo Qt Quick: la finestra Qt Widgets e le sue prove escono; il codice è a quattro strati (studio 43, sezione 2) | La finestra Quick fa quello che faceva la Widgets; le risposte della Widgets restano registrate per le prove (`tests/quick/aiuti/riferimenti.py`). Le righe sotto sulla finestra Widgets (QGraphicsView, pyqtgraph, R389) sono la storia di quella scelta. |
| 04/11/2026 | R389: prova Quick separata, nessun cambio al programma Widgets o al nucleo | [V] Pianta di Rho con 778 moduli, proprietà/annulla, Verifiche e anno orario, eventi e immagini offscreen; `revisioni/quick-prova-esito.md` e misuratore per la sera. [I] Raccomandato restare sui Widgets ottimizzati finché il confronto a schermo non giustifica una migrazione per percorsi. La decisione resta a Daniel; limiti e fallimenti sono nell’esito. |
| 21/10/2026 | Qt 6 + PySide6, 2D in QGraphicsView e 3D in Qt Quick 3D, senza motore web | Sono state provate trenta strade (`studio/01`). Qt Quick 3D va a 60 fps su Windows (Direct3D 11) e a 120 fps su niri (OpenGL), anche in Flatpak [V]. GTK su Windows non va oltre 18-29 fps [V]. |
| 21/10/2026 | Licenza GPL-3.0-or-later | Qt Quick 3D è GPLv3. Il programma è open source per scelta di Daniel. |
| 21/10/2026 | Ambito nazionale | Le norme regionali (Allegato H lombardo) sono moduli, non l'ambito. |
| 21/10/2026 | Il riferimento delle funzioni è PVsyst, non PVGIS | Daniel scriveva PVGIS intendendo PVsyst. PVGIS resta fonte di dati e secondo parere. |
| 21/10/2026 | La posa dei moduli parte solo a richiesta | Daniel: «il fatto che disegni già il fotovoltaico una volta fatto l'edificio non è il massimo». |
| 21/10/2026 | Sottocampi quanti se ne vuole, ognuno con montaggio, inclinazione e orientamento propri | Richiesta di Daniel, al posto di «dividere il campo». |
| 21/10/2026 | Valori predefiniti ben pensati, niente impostazioni obbligatorie prima di cominciare | Daniel: PVsyst «blocca» chiedendo troppo all'inizio. |
| 21/10/2026 | Pedigree di ogni calcolo: formula in LaTeX, valori con l'origine, norma con articolo e pagina | Richiesta di Daniel. Le formule le disegna matplotlib (mathtext), senza installare TeX. |
| 21/10/2026 | Modello del modulo: De Soto adattato alla scheda, temperatura dal γ della scheda | Il γ è misurato secondo IEC 61215 ed è il dato di cui il progettista si fida [I]. Il confronto con PVGIS è in `validazione-pvgis.md` [V]. |
| 21/10/2026 | Catalogo in due livelli: schede lette per Meridiana e lista CEC | La lista CEC ha 16.886 moduli, ma è del mercato USA. Le schede danno le marche europee e italiane con l'indirizzo della fonte. |
| 21/10/2026 | Su Linux, fuori da KDE e GNOME, il tema del portale | Su niri il tema generico di Qt ignora la preferenza scura [V]. |
| 22/10/2026 | Aspetto: la direzione Meridiana, con il colore a scelta | Daniel ha scelto Meridiana tra quattro direzioni (`studio/13`). Non è sicuro dei colori: se ne sceglie uno e il resto si ricava, con i contrasti e i colori degli stati protetti [V calcolo]. |
| 22/10/2026 | Si sviluppa anche nelle sessioni cloud di Claude Code | Daniel ha 250 USD di credito per le sessioni cloud, fino al 5/11/2026 08:59. Una sessione cloud vede solo il repository: le regole stanno nel `CLAUDE.md`, la macchina si prepara con `tools/cloud-setup.sh`, i commit senza firma di Claude (`.claude/settings.json`); lavora su un suo ramo e apre una richiesta di unione verso `lavoro`. |
| 22/10/2026 | Assistente: un personaggio che fluttua, uno solo per tutta la finestra | Richiesta di Daniel, sul modello di VS Code (`studio/14`, 7.3): si clicca per chiedere un parere, resta lo stesso tra le schede e si sposta dove non copre il lavoro. |
| 23/10/2026 | Posa a mano (studio 16, C.6, strada C4): file come oggetti, moduli con id stabili, «esplodi» in file di un posto; la posa automatica resta il primo gesto; un modulo nuovo entro 2 cm adatta le file a mano, altrimenti si chiede; i moduli esplosi restano nel loro sottocampo | Daniel: «Tutti i punti proposti vanno bene!». Il passo dal sole e le regole VVF sono il valore di Meridiana: la posa automatica propone, il progettista corregge; con le file a mano le regole diventano verifiche (il modello di Aurora: errori a colori senza bloccare). Fila sul tasto L, libero (progetto dell'interfaccia 2.2). |
| 23/10/2026 | Grafici della finestra con pyqtgraph (studio 17, D2), «Tabella» resta; la relazione PDF resta con matplotlib | Decisione di Daniel sul compito 17c: dipendenza nuova accettata (MIT, puro Python, vuole solo numpy, +14 MB). Nella prova su 8.760 valori orari [V, `studio/17-prove/grafici_prova.py`] pyqtgraph disegna in 24-32 ms e risponde al passaggio del mouse in 2-4 ms, matplotlib ridisegna in 150-190 ms (7-9 ms al passaggio solo col blitting); la vista web costa 111-126 MiB e un processo in più. Interazioni nell'ordine del progetto dell'interfaccia (5.2): valore al passaggio, legenda, zoom solo sugli orari, esportazione SVG e PNG. |
| 28/10/2026 | Dimensionamento R187 e ingressi R188: combinazioni valide di modelli della stessa marca, poi meno inverter, meno modelli e DC/AC più vicino; ogni MPPT con serie, parallelo, potenza e stato | Daniel chiede tutti i moduli in stringa e calcoli giusti. Una combinazione non si accetta se lascia moduli fuori o supera i limiti. Il formato 14 già rappresenta i paralleli e resta invariato [V, `revisioni/kimi-incarico-22-esito.md`]. |
| 29/10/2026 | Meridio cerca e apre progetti solo dall'indice locale; attività nel registro; cloud filtrato dal programma | R151 e decisioni di Daniel del 26/10: ricerca deterministica, ultima revisione valida per serie, apertura solo dopo percorso, revisione e conferma; attività locali senza sincronizzazione; Claude non riceve indice, nomi, percorsi o commesse e le domande sui riservati restano locali. [V: incarico 10, studio 20 §6] |

## 2. Architettura

Dal 10/11/2026 (studio 43) il programma è a quattro strati, come Neistar, in
`src/meridiana/`. Prima (dal 23/10/2026, compito 18b, studio 18 A §9) era a livelli in una cartella sola.

```
core/      i calcoli, Python puro senza Qt: geometry/, model/, layout/, rules/, energy/, compute/
data/      i formati e gli archivi: atomic, project_archive, registry, year_store, catalog/ (con i suoi JSON),
           tables/
app/       ciò che li unisce, ancora senza Qt: la sessione (session.py), i lavori come funzioni (jobs.py,
           pipeline.py), platform/ (percorsi, impostazioni, registro), project/, interface/, view/, maps/,
           exchange/ (IFC, DXF, PVsyst), report/, assistant/ (Meridio), gli aggiornamenti
gui/       la finestra Qt Quick: application.py, il QML in qml/, i ponti in backend/, la relazione su carta in
           paper/, style/; mostra la sessione e riporta i gesti
__init__.py, __main__.py, i18n.py    alla radice del pacchetto, nient'altro
```

Regole (studio 43, 1.2), controllate da `tests/nucleo/test_strati.py`:
- **chi importa chi**: `core` e `data` non si conoscono e non importano `app` né `gui`; `app` importa `core` e
  `data`; `gui` importa tutto; alla radice `__init__` e `i18n` nessuno strato, `__main__` solo `gui` e `app`
  dentro le funzioni;
- **Qt solo in `gui`** (`PySide6`, `shiboken6`), anche dentro una funzione; niente rete in `core` e `data`;
- **`gui` non calcola**: l'elenco dei moduli di `gui/` senza Qt è congelato, ciò che calcola scende in `core` o
  `app` con le sue prove;
- gli `__init__.py` degli strati non riesportano niente; import assoluti fra cartelle diverse
  (`from meridiana.core.geometry import geo`), relativi solo dentro la stessa cartella;
- le eccezioni di oggi sono l'elenco `DEBITI` della prova (i passi C7a-C7e dello studio): può solo accorciarsi;
- un modulo lanciato come processo (`-m meridiana...`) ha il nome in una costante (`WORKER`);
- `core/model/model.py` non importa `core/energy/` (la posa fuori ombra riceve la funzione d'ombra da chi la
  chiama); una vista si aggiorna per argomento (`project:geometry`, `project:text`, `layout:<id>`, `energy`,
  `selection`, `checks`...), mai «tutto».

Le tabelle sotto raccolgono i moduli per argomento, con il percorso sotto `src/meridiana/`.

**Sessione e lavori** (senza Qt):

| Modulo | Che cosa fa |
|---|---|
| `app/session.py` | `ProjectSession`: progetto e file, pose con le loro chiavi, anno energetico, generazioni, selezione, annulla a istantanee (`Undo`: fusione entro 2 s, limite di 200 passi, indice del salvato; `edit` rimette il progetto com'era se la modifica solleva), «modificato», copie di recupero; `topics_of` dice a che argomento appartiene una modifica, `energy_key` se l'anno in mano è ancora buono. |
| `app/jobs.py` | `layout_of(project, known)`: le pose dei sottocampi riempiti, tenute se la chiave non è cambiata; ogni posa porta i corner e le chiavi dei moduli come array (da `layout.compute`) e la tabella delle istanze 3D (`mesh.module_table`, fatta qui nel thread). |
| `app/pipeline.py` | `compute(project, results, cache, fetch) -> EnergyResult`: meteo, campi, consumi, anno orario, stringhe e seconda simulazione, conteggi fuori ombra, PVGIS, economia, dimensionamenti; `compute_or_say` dice gli errori nel risultato. |

**Nucleo**, Python puro senza Qt:

| Modulo | Che cosa fa |
|---|---|
| `core/model/model.py` | Il progetto e il file `.meridiana` (formato 10: ogni variante con il suo `design`, anche quella in mano; in memoria i campi del progetto sono la copia di lavoro; dall'8 gli inverter come elenco e le stringhe come oggetti, compito 16d; dal 9 `Roof.edges` gronda o testata per lato, `ridge_height` e `covering`, `SubField.pitch` come lato di gronda sui tetti a due falde e a padiglione, compito 16a; dal 10 `SubField.rows` e `manual`, le file a mano posate come sono, e i moduli con id stabili «fila:posto», compito 16c), validato alla lettura con il percorso della chiave, migrazioni 1→10 con un file d'esempio per versione (la 8→9 tiene i tetti dei rettangoli com'erano e avverte per le altre impronte; la 9→10 porta le chiavi «riga:posto» dei moduli tolti e delle stringhe a mano agli id degli stessi moduli, «f1:posto» per la prima fila, e dice quelle che non lo sono); `geometry_key` dell'edificio e `layout_key` del sottocampo (sottocampo, modulo, sito, finestra, geometria e soggezione VVF dell'edificio ospite, sue esclusioni; tutti gli edifici e gli ostacoli solo fuori ombra; non l'inverter e l'ingresso del sottocampo, `ELECTRICAL`); falde in cache finché la geometria non cambia. |
| `core/model/settings.py` | Lo schema tipizzato di `energy`, `consumption`, `economics`: `from_dict` dice le chiavi ignote con il percorso e rifiuta i tipi sbagliati; specchio dei dataclass di `energy/` (un test li tiene uguali). |
| `core/geometry/geo.py` | Coordinate locali (ENU su WGS84), azimut secondo la CEI 82-25/1, tile, coordinate scritte all'italiana. |
| `core/geometry/sun.py` | Posizione del sole (NOAA/Meeus, verificata contro la SPA di pvlib) e passo delle file (CEI 82-25/3, 6.2). |
| `core/geometry/roof_join.py` | Il tetto fatto a mano come superficie unica (R304, R303): le falde libere affiancate si incontrano esattamente sulla linea disegnata (`resolve`, pesi in testa al modulo), una falda con gli angoli fuori piano si piega lungo una diagonale in falde piane (`fold`), ogni angolo alla sua quota. Formato 23: `Roof.joined`. |
| `core/geometry/roof_vertices.py` | Gli angoli di un tetto uno per uno (R303): le maniglie, la quota scritta (`parse_height`: col segno relativa, senza assoluta) o trascinata, due angoli fatti coincidere (`weld`) e staccati (`detach`), il tetto generato che diventa a mano (`to_manual`). Senza Qt: la vista 3D li mostra, la finestra applica un passo di annulla per gesto. |
| `core/geometry/roofs.py` | Falde: tetto piano, a una falda, a due falde e a padiglione su qualsiasi impronta (dallo scheletro: una falda per lato di gronda, nell'ordine dei lati, con `side` e `name`; testate predefinite sui bracci, `default_gables`; quota del colmo che dà la pendenza; i colmi, `ridges`), falde libere; la pendenza proposta dalla copertura (`COVERINGS`, manuale ANDIL 2025 p. 7). |
| `core/geometry/skeleton.py` | Lo scheletro dritto (compito 16a): eventi di lato e di divisione con le frazioni, gli eventi dello stesso istante insieme, testate che non si muovono; le facce per lato con l'altezza; pulizia dei vertici allineati e dei lati nulli. Verificato contro CGAL sulle 306 piante di `studio/16-prove/scheletro-riferimento.json`. |
| `core/geometry/templates.py` | Gli edifici da modello: rettangolo, L, T, U, trapezio dalle quote, posati e ruotati. |
| `core/model/move.py` | Sposta e Ruota (compito 16b): `translate`, `rotate`, `copy` danno una modifica per `session.edit`; un edificio porta le falde libere, i sottocampi di tutte le varianti e le esclusioni che lo citano; un sottocampo ruota l'azimut esplicito e resta sulla sua falda o a terra, una falda libera sul suo edificio (rifiuti con il motivo); un'esclusione prende l'edificio sotto il suo centro (`host`, prima nella finestra); le file a mano si spostano e ruotano con il loro sottocampo ed edificio, una fila («row», compito 16c) si sposta dentro il sottocampo con `manual.translate` e non ruota. `Gesture`: il gesto in pianta (punto base, valori scritti, angolo a passi, modi), `nudge` le frecce. |
| `app/view/gizmo.py` | Il gizmo di Sposta e Ruota nel 3D (compito 16b): maniglie in assi Qt lunghe 120 px, la scelta sullo schermo entro 8 px, i trascinamenti lungo una freccia, sul piano e sull'anello, i passi (10 cm e 15°, 1 cm e 1° con Maiusc, 1 mm e 0,1° senza agganci). |
| `core/layout/layout.py` | Posa dei moduli nel sottocampo: montaggi, file, tavole, distanze, regole VVF. Dal compito 16c le file come oggetti (`Row`: id stabile, origine in pianta, azimut, posti, chiavi prese da una fila esplosa, girata di 90°): `compute` fa le file e i moduli vengono da `modules_of`; con le file date (a mano) non rifà niente e trova i gruppi VVF dai moduli a meno di 2 m (`clusters`); `extent` e `narrow_gaps` per le verifiche. |
| `core/layout/manual.py` | La posa a mano (compito 16c): le modifiche per `session.edit` sulle file di un sottocampo, che diventa «a mano» al primo gesto: fila disegnata da due punti con il modulo, gli spazi e le tavole del sottocampo, tolta, aggiunta in coda, accorciata o allungata, spostata dentro il sottocampo (rifiuto con il motivo), esplosa in file di un posto con le chiavi dei suoi moduli, modulo da solo girato di 90°, Canc, «Riposa in automatico»; modulo nuovo adattato entro 2 cm, altrimenti da chiedere; anteprima e «rossa» del gesto (`corners`, `trouble`). |
| `core/geometry/sides.py`, `core/geometry/snapping.py`, `core/geometry/squaring.py` | I lati di un contorno (lunghezze, allungamento); guide di disegno; squadratura dei contorni (port di iD, licenza ISC). |
| `core/geometry/mesh.py` | Geometria per la vista 3D: triangoli di edifici e falde, tabella delle istanze dei moduli, nastri dei contorni, i tre anelli del mirino del perno (`ring`, `rings`, `ring_bands`); le forme del gizmo di Sposta, lunghe un'unità (`lathe`, `arrow`, `annulus` di 48 lati, `square`). |
| `app/view/viewaids.py` | Barra di scala 1-2-5, che cosa c'è sotto il cursore con la sua quota, misura rapida della selezione, contorni per il 3D, ancore dei segni. |
| `core/rules/checks.py` | Le verifiche raccolte da ogni parte del progetto, con fonte, livello, oggetto e correzione; i segni per le viste. |
| `app/report/` | La relazione senza Qt (R314, studio 24, bozzetto V1 «Cornice»): i capitoli come dati JSON (`chapters.py`, `compose.py`, `blocks.py`), il registro dei calcoli con i codici R-0n0.nn (`register.py`), pianta in SVG, tappeto delle ore e formule (`figures.py`), l'aspetto in `template.typ`, la compilazione con Typst (pacchetto `typst`, Apache-2.0) in una cartella temporanea che è tutto ciò che Typst può leggere, con i caratteri del programma e nessun carattere di sistema (`engine.py`). |
| `core/rules/rules.py` | Le regole che si applicano all'impianto (connessione, obblighi, DM 37/08), come note per la relazione. |
| `core/rules/vvf_activities.py` | L'Allegato I del DPR 151/2011 come dati (R327): le 80 attività con testo, soglia e categorie A, B, C dalla GU n. 221 del 22/09/2011, la ricerca per numero o parole, la scelta coerente con l'interruttore dell'edificio. |
| `app/compare.py` | Le varianti a confronto: le cifre di ognuna dalla stessa catena, la migliore per riga. |
| `app/interface/help.py` | Gli aiuti accanto alle cose (studio 17, E; compito 17d): per ogni gruppo, campo e riquadro di risultato che ne ha bisogno, per ogni fase e livello delle verifiche, titolo, frase breve, testo, fonte (regola di `rules.py` o riferimento già in `checks.py`), àncora del manuale `docs/manuale` e passo di «Come è calcolato»; le àncore dei titoli come le fa GitHub. |
| `app/interface/quantity.py` | Valori scritti nei campi con unità e calcoli («2 m + 30 cm»), senza `eval`. |
| `app/interface/shortcuts.py` | I comandi della finestra e i loro tasti in un posto solo, i tasti da evitare, i conflitti. |
| `app/interface/phases.py` | Le sei fasi descritte una volta (studio 17, B4): numero, titolo, gruppi con i comandi (quelli dei compiti futuri segnati come previsti), ispettore, aree delle verifiche, domande di Meridio; `next` e `previous`; gli elaborati della Relazione con il loro stato. |
| `app/interface/navigation.py`, `app/view/camera.py` | Gli stili di navigazione come tabelle di dati, la macchina di stati del mouse per pianta e 3D (`orbit_keys` e `previews_orbit`: il tasto che trasforma la pressione successiva in un'orbita); la camera del 3D (orbita, perno e `keep_in_view`, `pixel_size`, zoom, viste, animazioni). |
| `app/view/navicube.py` | Il cubo di vista: le 26 parti, la vista da ogni parte, orientamento più vicino, frecce, bussola, che cosa si è cliccato. |
| `app/interface/theme_colors.py` | I colori del tema ricavati dal colore scelto, in OKLCH (`studio/13`, sezione 12). |
| `app/interface/view_colours.py` | I colori propri di pianta e 3D, uguali nei due temi (R16, R29). |
| `core/model/underlay.py` | Le immagini sotto il disegno: dove vanno i pixel, in scala con due punti, spostate, ruotate (R21). |
| `app/maps/tiles.py` | Le sorgenti di sfondo: quali tile servono a una vista, da quale fonte, a quale zoom. |
| `app/assistant/` | Meridio. `__init__.py`: il personaggio (i due disegni, liscio su griglia di 24 e pixel su griglia di 17, con sguardo, battito, smorfie e raggi; la macchina a stati dei movimenti `Mood`; ancore per scheda e posto del fumetto; domande pronte). Il modello (compito 14): `providers.py` un'interfaccia sola, compatibile con OpenAI verso `llama-server` (streaming SSE) e Claude con l'SDK ufficiale; `tools.py` gli strumenti (lettura, «portami lì», proposte con i campi ammessi); `conversation.py` il ciclo modello-strumenti con un tetto di 6 giri; `context.py` le istruzioni; `privacy.py` consenso, progetto riservato, segnaposto per nomi e indirizzi; `costs.py` token e prezzi datati; `keys.py` la chiave nel portachiavi; `text.py` il Markdown del modello in HTML e in frasi da leggere. |
| `data/catalog/` | Il catalogo dei componenti (`__init__.py`: ricerca e record; `panond.py`: i .PAN e .OND di PVsyst). |
| `app/exchange/ifc_export.py` | Il progetto come modello IFC4 (studio 15, 5.2; R91): sito con latitudine e longitudine ai milionesimi di secondo e IfcMapConversion su UTM WGS84, un piano per edificio con pareti, IfcRoof con un IfcSlab ROOF per falda, parapetti, ostacoli, un IfcSolarDeviceType per modulo e orientamento con la forma una volta sola, un IfcSolarDevice per modulo con il suo Pset (sottocampo, fila, inclinazione, azimut, potenza, stringa), un IfcGroup per sottocampo e per stringa; i moduli scritti come entità dirette, il file rinominato solo quando è intero. |
| `app/exchange/ifc_read.py`, `app/exchange/ifc_import.py`, `app/exchange/ifc_worker.py`, `core/compute/procmem.py` | La lettura di un IFC per il fotovoltaico (studio 20): `ifc_read` apre il file in modo pigro e legge solo coperture, solai o pareti degli edifici senza tetto e ciò che sta sopra, le forme semplici direttamente e il resto con l'iteratore di IfcOpenShell (un thread); `ifc_import` porta falde e ostacoli nel sistema del progetto (mappa UTM, latitudine del sito, TrueNorth) e li riconosce come tetti di Meridiana (piano, una falda, due falde, padiglione o falde libere); `ifc_worker` è il processo a parte che la finestra può fermare; `procmem` la memoria di un processo senza psutil. |
| `app/exchange/pvsyst/` | I file di PVsyst letti, mai scritti: `pvobject.py` il formato di testo, `records.py` i record orari in base 62, `project.py` progetto e varianti, `mapping.py` da PVsyst a un progetto Meridiana. |
| `core/energy/meteo.py`, `core/energy/pvgis.py` | Anno tipo, orizzonte e PVcalc di PVGIS, con cache. |
| `core/energy/components.py` | Modulo e inverter per il modello energetico. |
| `core/energy/simulate.py` | Simulazione oraria con la catena delle perdite. |
| `core/energy/nearshade.py` | Le ombre vicine della scena (ostacoli, parapetti, altri edifici) sui moduli, con l'effetto elettrico delle stringhe. |
| `core/energy/system.py` | Dal progetto al modello: campi, inverter (`inverters_of` un elenco, `combined` il lato AC dell'anno, `describe` in una riga), perdite; gli ostacoli di un sottocampo e le loro ombre come esclusioni (`shadow_exclusions`). |
| `core/energy/stringing.py` | Stringhe e verifiche CEI 64-8/7, la distribuzione di PVsyst sugli ingressi (`spread`, 3 + 3 + 4), sovraccarico e sbilanciamento degli ingressi (soglie di programma), assegnazione delle stringhe ai moduli posati. |
| `core/energy/plant.py` | L'impianto (compito 16d): gli inverter uno per uno con i loro ingressi, le stringhe proposte con le strategie di PVsyst o disegnate a mano (chiavi «sottocampo/fila:posto», dette perse quando la posa cambia), le verifiche per stringa, ingresso e inverter alle condizioni dell'anno o a quelle di progetto di PVsyst (60, 20, -10 °C), tenute per ingresso; le operazioni della stringatura a mano come dati. |
| `core/energy/bands.py` | Fasce ARERA. |
| `core/energy/consumption.py` | Consumi: profili, bollette, curve misurate. |
| `core/energy/economics.py` | Bilancio con accumulo, CER, flussi di cassa, dimensionamenti. |
| `core/energy/pedigree.py` | La provenienza di ogni numero. |

**Io** (file e impostazioni):

| Modulo | Che cosa fa |
|---|---|
| `data/atomic.py` | File scritti per intero o per niente, con la copia precedente in `.bak`; lettura dalla copia se il file è danneggiato, dicendolo. |
| `app/project/recovery.py` | Il salvataggio automatico: una copia delle modifiche non salvate ogni due minuti nella cartella di stato, offerta al riavvio; i nomi delle revisioni `_R01`. |
| `app/platform/config.py` | Le impostazioni dell'utente: campi tipizzati, migrazioni con `CONFIG_VERSION`. |
| `app/platform/paths.py` | Dove stanno i file del programma (config, stato, dati, cache). |
| `app/platform/log.py` | Gli errori detti e tenuti: stderr, il file nella cartella di stato, l'excepthook che li porta alla barra di stato. |
| `i18n.py`, `app/updates.py`, `app/minisign.py` | gettext; la versione nuova dalle release di GitHub con la firma verificata (quando controllare e il comando di Setup: sezione 4). |

**Servizi** (senza Qt):

| Modulo | Che cosa fa |
|---|---|
| `app/maps/geocoding.py` | Nominatim: la richiesta, la risposta letta, una richiesta al secondo; la rete la mette il dialogo. |

**Finestra**, in `src/meridiana/gui/` (Qt Quick): `application.py` crea l'applicazione e la `QuickWindow` (istanza
unica per profilo, copie di recupero, registro, la visita guidata al primo avvio); `backend/` ha le parti della finestra (`parts.py` le carica per nome:
pianta, 3D, Impianto, Proprietà, Verifiche, grafici, File, relazione, Meridio...), i lavori in `QRunnable` e i
processi del calcolo dell'anno (`shell_compute.py`) e della relazione (`report_worker.py`); `qml/Meridiana/` i
componenti e le pagine; `paper/` la relazione su carta; `style/` scale, tema, icone e simboli;
`package_check.py` il controllo di un pacchetto. Le regole della finestra sono in `docs/quick/regole.md`.

**Regola.** La finestra mostra e raccoglie i gesti; tutto ciò che calcola sta nel nucleo, con i suoi test; ogni modifica del progetto passa da `session.edit`.

**Che cosa restava del compito 18b** (studio 18 A §9.2, passo 4) è arrivato: `Roof` con i lati per falda e `ridge_height` e `SubField.pitch` come lato di gronda con il compito 16a (formato 9), `removed` e le stringhe a mano con l'id del modulo con le file del compito 16c (formato 10).

## 3. Rischi e domande aperte

| Rischio | Barriera |
|---|---|
| Un progetto perso o rovinato | Salvataggi atomici con la copia precedente (`.bak`); lettura dalla copia se il file è danneggiato, dicendolo, e validata con il percorso della chiave; annulla su ogni modifica, anche su una che fallisce; copia di recupero ogni due minuti, offerta al riavvio. |
| Numeri sbagliati presi per buoni | Pedigree su ogni passo; valori predefiniti marcati come tali e riepilogati nella relazione; confronto con PVGIS; test sui casi delle norme (Allegato B della CEI 64-8/7, tariffa del DM 414/2023). |
| Prezzi e tariffe che cambiano ogni anno | Nessun valore regolato viene inventato (la TRASE parte da zero finché il progettista non la inserisce). I prezzi sono valori indicativi da sostituire. |
| Dati dei cataloghi non aggiornati | Ogni record porta la fonte e la data. Un componente scelto viene copiato nel progetto. |
| PVGIS non raggiungibile | La cache; il calcolo funziona senza rete dopo il primo download. |

**Domande aperte per Daniel**
- I profili di consumo sintetici bastano, o servono profili misurati (RSE, ENEA, distributori)?
- Prezzo dell'energia immessa: valore medio o prezzi zonali orari del GME?
- Quando rendere pubblico il repository? Deciso il 25/10/2026: pubblico («vai pubblico»).

## 4. Rilascio e pacchetti

### Come si fa oggi (release 0.2.0, 09/11/2026)

La prima release pubblicata è la 0.2.0 (https://github.com/daniel-g-carrasco/meridiana/releases/tag/v0.2.0), con la finestra Qt Quick. Si fa da questo PC, non dal CI; i paragrafi dopo questa sezione sono la storia del 25/10 (finestra Widgets, zip portabile, release dal CI) e valgono solo dove questa non dice altro.

**Pubblicare** (solo quando Daniel la chiede: è un'azione pubblica).
1. Versione in tre posti, uguali (`tests/nucleo/test_release.py` lo controlla): `src/meridiana/__init__.py` (`__version__ = "0.2.1"`, tre numeri), `CHANGELOG.md` (`[Unreleased]` diventa `[0.2.1] - data`), `data/io.github.daniel_g_carrasco.meridiana.metainfo.xml` (un `<release version="0.2.1" date="...">` in cima).
2. Pacchetto: `powershell -ExecutionPolicy Bypass -File build-aux\windows\build.ps1 [-Python <python del venv>] [-Iscc <ISCC.exe>]`. Fa i cataloghi e l'icona, PyInstaller (`dist\Meridiana`), la prova del pacchetto e Inno Setup con la versione letta da `__init__.py`; esce `dist\meridiana-setup-v<versione>-windows-x64.exe`, il nome che l'aggiornamento del programma cerca in una release (`updates.installer_name`). Circa 6 minuti. Niente zip portabile.
3. Prova del pacchetto installato: `Meridiana.exe -m meridiana.gui.package_check PROGETTO USCITA [--language en]` (dai sorgenti `python -m meridiana.gui.package_check ...`): apre il progetto con un profilo suo, calcola l'anno, mostra ogni fase, File, Impostazioni e Meridio, scrive la relazione; `USCITA\check.json` dice cosa ha visto. Installazione silenziosa per utente: `meridiana-setup-...exe /VERYSILENT /CURRENTUSER`.
4. Firma con la chiave minisign comune alle app di Daniel (id `CEFFF9269F08F845`, in `%USERPROFILE%\.config\minisign-app-releases`; la metà pubblica è `updates.PUBLIC_KEY` e `docs/CODE_SIGNING.md`): `minisign -S -s <cartella della chiave>\minisign.key -m <installer>`, poi il file `.sha256` accanto.
5. Il commit pubblico: su GitHub va un commit solo, sopra il `main` pubblico, con il codice della versione; i documenti di lavoro dei giri (misure, stati, revisioni, schermate) restano nell'archivio privato e nessun nome di cliente o di commessa entra nel repository pubblico (controllo con `git grep` prima della spinta).
6. `gh release create vX.Y.Z --repo daniel-g-carrasco/meridiana --target <SHA completo del commit pubblico> --title "Meridiana X.Y.Z" --notes-file <note> <installer> <installer>.minisig <installer>.sha256`. Né `--prerelease` né `--draft`: l'aggiornamento chiede `releases/latest`, che le esclude. GitHub calcola da sé il `digest` SHA-256 di ogni file, ed è quello che l'aggiornamento confronta.

**L'aggiornamento nel programma installato** (`app/updates.py`, `gui/backend/update_check.py`, `gui/backend/dialogs.py`). Una volta al giorno, un minuto dopo l'avvio, solo nel programma per Windows e se Impostazioni > Privacy lo permette, chiede a GitHub l'ultima release; se è più nuova (`updates.is_newer`) lo dice nella barra di stato, e Aiuto > Cerca aggiornamenti mostra la versione, scarica l'installer, ne verifica dimensione, SHA-256 e firma minisign e solo allora avvia Setup, che chiude e riapre il programma. Firma sbagliata, file alterato o nessuna rete: un messaggio e nessuna installazione. Provato da capo a fondo il 09/11/2026 con una 0.2.1 servita da un server locale (variabili d'ambiente solo per le prove: cambiano da dove si scarica, non di cosa ci si fida).

**Le prove e l'automazione** (`tools/run_tests.py`, `.github/workflows/test.yml`). Le prove stanno in gruppi sotto `tests/`: `nucleo` (con la prova degli strati, `test_strati.py`), `calcoli`, `formati`, `profili`, `quick` (la finestra Qt Quick, in sottogruppi: `controlli`, `grafici`, `impianto`, `meridio`, `pagine`, `percorsi`, `pianta`, `proprieta`, `shell`, `sistema`, `vista3d`; gli aiuti comuni in `quick/aiuti/`) ed `esterni` (solo sul PC di Daniel). `python tools/run_tests.py tests/<gruppo>` ne lancia uno, `python tools/run_tests.py --all --parallel 4` tutti come processi separati, `python tools/quick_rif_tests.py` i sottogruppi Quick uno per processo. L'automazione `linux` gira a ogni push, offscreen su Ubuntu 24.04 con Python 3.12: `python -m ruff check --select F,E9,B .`, `python tools/compile_po.py --check` e poi la compilazione dei cataloghi, i gruppi `nucleo`, `calcoli` e `formati`, `desktop-file-validate` e `appstreamcli validate --no-net` sui file di `data/`, i sottogruppi Quick con `tools/quick_rif_tests.py`. Il pacchetto per Windows, la release e la firma sono in `.github/workflows/release.yml`, su un tag `v*` o a mano. Prima di una spinta gli stessi comandi passano in locale.

**Flatpak** (`build-aux/flatpak-quick/`): runtime KDE 6.11, Qt 6.12 costruito nel pacchetto (`python3-qt612.json`), ezdxf e le librerie della relazione modificabile come moduli; si costruisce da un archivio senza CRLF (`git -c core.autocrlf=false archive`) con `flatpak run org.flatpak.Builder --user --install --force-clean build-dir build-aux/flatpak-quick/io.github.daniel_g_carrasco.meridiana.yaml`. Non è ancora pubblicato in un repository.

### La storia: compito 18f del 25/10/2026

Dal rapporto `studio/18-prove/H-pacchetti.md`. Le misure sono del PC di Daniel (Windows 11, Python 3.12.6 di python.org) e del WSL openSUSE dello stesso PC per il Flatpak.

**Windows** (`build-aux/windows/`).
- Si costruisce con il Python 3.12 di python.org in un venv a parte (`.venv-build`, mai quello del programma): `pip install -r requirements.txt pyinstaller==6.22.3`, poi `python tools/compile_po.py` (con `msgfmt`, o dove manca con il compilatore dello stesso file, che dà lo stesso catalogo di GNU: [V] 2.541 voci uguali), `python tools/make_ico.py` (Qt disegna l'SVG: niente GTK), `pyinstaller --noconfirm build-aux/windows/meridiana.spec`, `ISCC.exe /DAppVersion=X.Y.Z build-aux\windows\meridiana.iss`.
- La spec (`meridiana.spec`): Qt dai tre wheel (Essentials, Addons, Pdf; niente WebEngine), Qt Quick 3D e i moduli QML della scena, QtMultimedia e QtTextToSpeech per la voce di Meridio, le traduzioni di Qt solo in italiano e inglese, matplotlib solo Agg, pvlib con le tre tabelle che legge a run time (Linke, altitudine, spettro; non le librerie CEC e Sandia né gli anni d'esempio), il manuale in `share/manuale`, i cataloghi in `share/locale`, la scena 3D e il catalogo prodotti accanto ai loro moduli, `kokoro_worker.py` come script. Lascia fuori 122 binari (61,9 MB: Qt 3D, Charts, Graphs, Location, Web*, tastiera virtuale, fisica e XR di Quick 3D, FFmpeg, l'OpenSSL di Qt, il debugger QML): una parte lasciata fuori torna da sola se un binario tenuto la importa (la spec legge le tabelle d'importazione con pefile) [V].
- Il manifest (`meridiana.manifest`) non dice nulla sul DPI: Qt si fa «per monitor V2» da sé (il `dpiAware=true` dell'app GTK avrebbe sfocato la finestra sul secondo schermo) [I fino alla prova sui due schermi].
- Inno Setup (`meridiana.iss`): per utente senza UAC, `.meridiana` associato (ProgID `Meridiana.Project`, attività spuntabile), `CloseApplications` per l'aggiornamento sopra il programma aperto, che riparte se c'era il suo mutex (`app.windows_identity`: lo stesso nome dell'AppId, che è anche l'AppUserModelID dei collegamenti).
- Misure del 25/10 [V]: build 4 min 41 s a PC tranquillo (fino a 9 min con il PC carico dalle altre sessioni), cartella `dist\Meridiana` 377 MB in 4.116 file (PySide6 157 MB, scipy 48 + 20, numpy 7 + 21, pvlib 17, matplotlib 15, pandas 13, Pillow 11); `Meridiana.exe --self-test` tutti i controlli superati in 11 s a PC tranquillo (17,5 s carico). Lo zip portabile come lo fa il CI (7-Zip, zip a livello 5) pesa 163 MB [V]; l'installer non è stato compilato (Inno Setup non c'è sul PC, sul runner `windows-2025` sì): un archivio LZMA2 solido al massimo, la sua stessa compressione, pesa 113 MB, quindi l'installer starà intorno ai 115 MB [I].

**`meridiana --self-test [RAPPORTO]`** (`ui/selftest.py`, fino al 10/11/2026; oggi il controllo di un pacchetto è `python -m meridiana.gui.package_check`, sopra): il programma si controlla da solo, offscreen (o sulla piattaforma di `MERIDIANA_SELF_TEST_PLATFORM`) e in una cartella temporanea (le variabili XDG, che `paths.py` rispetta anche su Windows; niente cache di Qt e di matplotlib nelle cartelle dell'utente); i file che un pacchetto deve portare, le librerie caricate tardi, le autorità TLS, le voci del sistema, poi la finestra con un capannone a Rho posato, in 3D, calcolato su un anno meteo sintetico messo in cache (nessuna rete), la relazione in PDF; esce con 0 se tutto passa. **Offscreen Qt Quick usa il suo renderer software, anche su Windows: la vista 3D non viene disegnata e l'instancing dei moduli non gira** [V 25/10: un cubo rosso in un QQuickWidget e in un QQuickView offscreen lascia la vista bianca, `graphicsApi` = Software, anche con `QSG_RHI_BACKEND=d3d11`]; il self-test lo dice (INFO) e il job Windows del CI lo lancia sul desktop del runner, dove Direct3D 11 disegna la scena. Vale anche per la suite: i test offscreen della 3D controllano la scena e le tabelle, non il disegno. Lo usano il CI, la prova del bundle e quella del Flatpak; `tests/finestra/test_self_test.py` lo lancia dai sorgenti con una home finta e controlla che lì non resti niente.

**Flatpak** (`build-aux/flatpak/`).
- Runtime `org.kde.Platform//6.11` con `io.qt.PySide.BaseApp//6.11` (PySide 6.11.2, numpy 2.3.5); le altre dipendenze da `python3-requirements.json`, wheel fissati per x86_64 e aarch64 scritti da flatpak-pip-generator da `requirements-flatpak.txt`: `TMPDIR=<cartella fuori da /tmp> python3 flatpak-pip-generator.py --runtime org.kde.Sdk//6.11 -r requirements-flatpak.txt --ignore-pkg numpy --prefer-wheels=scipy,pandas,matplotlib,pillow,fonttools,contourpy,kiwisolver,shapely,h5py,pydantic-core,pydantic_core,jiter,cryptography,cffi,charset-normalizer,charset_normalizer -o python3-requirements`, poi tolti a mano i sorgenti di numpy (li porta il BaseApp). Fuori kokoro-onnx: nel Flatpak Meridio parla con la voce del sistema.
- La pulizia è del manifest, non lo `cleanup-BaseApp.sh` del BaseApp: quello toglie QtPdf insieme a WebEngine (Meridiana importa i PDF come sottofondi con QtPdf) e disinstalla `packaging`, che serve a matplotlib [V lettura dello script].
- Permessi: rete (PVGIS, Nominatim, tasselli, GitHub), `home` (il `.bak` e le revisioni `_Rnn` sono file nuovi accanto al progetto), pulseaudio e `xdg-run/speech-dispatcher` per la voce, `org.freedesktop.secrets` per la chiave di Claude.
- Costruito nel WSL il 25/10 [V]: build riuscito, `.desktop` e metainfo validati, `meridiana --version` nel sandbox; 608 MB installati (senza PyOpenGL, tolto nella pulizia) più 297 MB di traduzioni del BaseApp che vanno nell'estensione `.Locale`; il self-test passa nel sandbox (28 s), offscreen e quindi senza disegnare la 3D: la scena 3D e l'instancing dei moduli su PySide 6.11.2 restano da provare sul portatile con la GPU [I]. Da una copia di lavoro su Windows: `git -c core.autocrlf=false archive HEAD` (con il CRLF `desktop-file-validate` rifiuta il `.desktop`).

**Il CI** (`.github/workflows/test.yml`). Linux offscreen a ogni push di ogni ramo con la cache di pip (non per `docs/studio` e `docs/compiti`; il manuale sì); una richiesta di unione solo da un fork; Windows sul tag `v*` o a mano (`workflow_dispatch`, casella «windows»): suite sul desktop del runner, bundle e suoi controlli, self-test del bundle, zip, installer, installazione silenziosa, associazione `.meridiana`, aggiornamento sopra il programma aperto; il job `release` sul tag firma e pubblica solo se esiste il segreto. Il repository pubblico non paga i minuti. Il file del 23/10 non era YAML valido (un nome di passo con «WebEngine: 132 MB»): tutti i run dal 23 al 25/10 sono falliti in 0 s; `test_release.WorkflowTest` lo impedisce [V gh run list].

**L'aggiornatore.** `updates.py` (nucleo) e `ui/update_dialog.py` (finestra): da solo una volta al giorno, un minuto dopo l'avvio, solo nel programma per Windows (`updates.checks_by_itself`) e se Preferenze > Riservatezza lo permette (`check_updates`, già nelle impostazioni: nessuna versione nuova); Aiuto > Cerca aggiornamenti ovunque. La finestra «È disponibile la versione…» mostra le note e il collegamento alla versione pubblicata con i file firmati; il programma installato scarica l'installer nel pool, lo controlla (dimensione, SHA-256 di GitHub, firma minisign con il nome del file), chiede di salvare il progetto e avvia Setup silenzioso (`/CURRENTUSER` se installato per utente); lo zip e i sorgenti aprono la pagina.

**Le chiavi e la procedura di una release** (solo quando Daniel la chiede).
1. Il segreto: la metà segreta della chiave minisign comune alle app di Daniel (id `CEFFF9269F08F845`, in `%USERPROFILE%\.config\minisign-app-releases`) come segreto `MINISIGN_SECRET_KEY` dell'ambiente GitHub `release` (Settings > Environments > release, con Daniel come revisore obbligatorio: il job aspetta il suo sì), per esempio `gh secret set MINISIGN_SECRET_KEY --env release --repo daniel-g-carrasco/meridiana < <file della chiave>`.
2. La versione in `src/meridiana/__init__.py`, `CHANGELOG.md` (`[Unreleased]` diventa `[0.2.0] - data`) e il metainfo (`<release version="0.2.0" date=...>`): `test_release` li vuole uguali. La prima release di Meridiana è la 0.2.0 (la 0.1.0 era lo scheletro del template, mai pubblicata).
3. Suite e lint; push; CI verde sullo SHA completo; tag `vX.Y.Z` su quel commit; i file della release (installer, zip, i due `.minisig`) controllati a mano con `minisign -Vm`.

**Trappole trovate in questo compito.**
- Il tool Bash di Claude dimezza le barre rovesciate anche negli heredoc: i file con `\` si scrivono con lo strumento Write.
- Lanciare il programma senza offscreen e senza cartelle temporanee usa le cartelle vere di Daniel: è successo una volta il 25/10 (vedi `compiti/18f-pacchetti.md`); il self-test ora si isola da sé.
- Qt scrive le sue cache (QML compilato, shader) in `%LOCALAPPDATA%\Meridiana\cache` qualunque cosa dicano le variabili XDG: il self-test le spegne (`QML_DISABLE_DISK_CACHE`, `QT_DISABLE_SHADER_DISK_CACHE`), la suite no.
- Nel programma congelato `sys.executable` è `Meridiana.exe`: dato come Python a `kokoro_worker.py` avrebbe aperto una seconda finestra. Ora il Python della voce è quello delle Preferenze o uno del PATH (mai l'alias dello Store), altrimenti parla la voce del sistema.
- Nel WSL `/tmp/.X11-unix` è un collegamento: bwrap rifiuta `--filesystem=/tmp` (flatpak-pip-generator) e serve `TMPDIR` altrove; `flatpak-builder --run` vuole `--state-dir=` con l'uguale e prende per sue le opzioni del comando (`sh -c 'meridiana --self-test'`).
- La copia di lavoro su Windows ha i fine riga CRLF (`core.autocrlf`): per costruire il Flatpak dalla copia di lavoro i file di testo vanno riportati a LF (la riga `#!` del lanciatore).
